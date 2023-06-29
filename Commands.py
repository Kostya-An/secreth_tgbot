import json
import logging as log

import datetime
import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ParseMode
from aiogram import types, Bot
bot: Bot

import MainController
import GamesController
from Constants.Config import STATS
from Boardgamebox.Board import Board
from Boardgamebox.Game import Game
from Boardgamebox.Player import Player
from Constants.Config import ADMIN

# Enable logging

if not os.path.exists("logs"):
    os.mkdir("logs")

log.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                level=log.INFO,
                filename="logs/logging.log")

logger = log.getLogger(__name__)

commands = [  # command description used in the "help" command
    "/help - Информация о доступных командах",
    "/start - Краткая информация об игре \"Тайный Гитлер\"",
    "/symbols - Пояснение всех возможных на доске символов",
    "/rules - Ссылка на перевод официальных правил \"Тайного Гитлера\"",
    "/newgame - Создать новую игру",
    "/join - Присоединиться к существующей игре",
    "/startgame - Запуск существующей игры",
    "/cancelgame - Отмена существующей игры, все данные игры будут потеряны",
    "/board - Вывод текущей доски с фашистскими и либеральными актами, указом Президента и счётчиком выборов",
    "/votes - Текущий статус голосования",
    "/calltovote - Призвать (пингануть) игроков проголосовать"
]

symbols = [
    u"\u25FB\uFE0F" + " Пустое поле",
    u"\u2716\uFE0F" + " Закрытое поле",  # X
    u"\U0001F52E" + " Президентское право: Просмотр законов",  # crystal
    u"\U0001F50E" + " Президентское право: Исследование лояльности",  # inspection glass
    u"\U0001F5E1" + " Президентское право: Уничтожение",  # knife
    u"\U0001F454" + " Президентское право: Внеочередные выборы",  # tie
    u"\U0001F54A" + " Победа либералов",  # dove
    u"\u2620" + " Победа фашистов"  # skull
]

async def command_symbols(message: types.Message):
    symbol_text = "На доске могут быть следующие символы:\n"
    for i in symbols:
        symbol_text += i + "\n"
    await message.reply(symbol_text, reply=False)

async def command_board(message: types.Message):
    chat_id = message.chat.id
    if chat_id in GamesController.games.keys():
        if GamesController.games[chat_id].board:
            await message.reply(GamesController.games[chat_id].board.print_board())
        else:
            await message.reply("В этом чате нет запущенной игры. Пожалуйста, начните игру, используя /startgame")
    else:
        await message.reply("В этом чате нет созданной игры. Создайте новую игру, используя /newgame")


async def command_start(message: types.Message):
    chat_id = message.chat.id
    await message.bot.send_message(chat_id,
        "\"Тайный Гитлер\" — это игра на социальную дедукцию для 5-10 человек о поиске и остановке Тайного Гитлера."
        " Большинство игроков — либералы. Если они научатся доверять друг другу, у них будет достаточно "
        "голосов, чтобы контролировать стол и выиграть. Но некоторые игроки — фашисты. Они скажут все, что угодно "
        "чтобы быть избранным, принять свою политическую повестку и обвинить других в последствиях. Либералы должны "
        "работать вместе, чтобы узнать правду, прежде чем фашисты изберут своего хладнокровного лидера и победят.\" "
        "\n       — официальное описание \"Тайного Гитлера\"\n\nДобавь бота в группу и напиши /newgame, чтобы начать игру!")

async def command_rules(message: types.Message):
    rulesMarkup = InlineKeyboardMarkup(row_width=1)
    rulesMarkup.insert(InlineKeyboardButton("Вариант 1", url="https://tesera.ru/images/items/903267/Secret%20Hitler%20Rules%20(Public%20File).pdf"))
    rulesMarkup.insert(InlineKeyboardButton("Вариант 2", url="https://tesera.ru/images/items/1978031/Правила.pdf")) 
    await message.reply("Читать официальные правила \"Тайного Гитлера\" (два перевода на выбор):", reply_markup=rulesMarkup)


# pings the bot
async def command_ping(message: types.Message):
    chat_id = message.chat.id
    await message.reply("pong - v0.4.1rus")


# prints statistics, only ADMIN
async def command_stats(message: types.Message):
    if message.from_user.id == ADMIN:
        if not os.path.exists(STATS):
            stats = {}
            stats["cancelled"] = 0
            stats["fascwin_hitler"] = 0
            stats["fascwin_policies"] = 0
            stats["libwin_policies"] = 0
            stats["libwin_kill"] = 0
            stats["groups"] = []
            with open(STATS, "w") as f:
                json.dump(stats, f, indent=4)
                print("stats file created")
        with open(STATS, "r") as f:
            stats: dict = json.load(f)
        stattext = "+++ Statistics +++\n" + \
            f"Liberal Wins (policies): {str(stats.get('libwin_policies'))}\n" + \
            f"Liberal Wins (killed Hitler): {str(stats.get('libwin_kill'))}\n" + \
            f"Fascist Wins (policies): {str(stats.get('fascwin_policies'))}\n" + \
            f"Fascist Wins (Hitler chancellor): {str(stats.get('fascwin_hitler'))}\n" + \
            f"Games cancelled: {str(stats.get('cancelled'))}\n\n" + \
            f"Total amount of groups: {str(len(stats.get('groups')))}\n" + \
            "Games running right now: "
        await message.reply(stattext)


# help page
async def command_help(message: types.Message):
    help_text = "Доступны следующие команды:\n"
    for i in commands:
        help_text += i + "\n"
    await message.reply(help_text, reply=False)


async def command_newgame(message: types.Message):
    chat_id = message.chat.id
    game = GamesController.games.get(chat_id, None)
    groupType = message.chat.type
    if groupType not in ["group", "supergroup"]:
        await message.reply("Для начала требуется добавить бота в группу и написать там /newgame!")
    elif game:
        await message.reply("В настоящее время идет игра. Если вы хотите завершить её, введите /cancelgame!") # не нравится перевод
    else:
        GamesController.games[chat_id] = Game(chat_id, message.from_user.id)
        with open(STATS, "r") as f:
            stats: dict = json.load(f)
        if chat_id not in stats.get("groups"):
            stats.get("groups").append(chat_id)
            with open(STATS, "w") as f:
                json.dump(stats, f, indent=4)
        await message.reply(
            "Новая игра создана!\nНажмите /join, чтобы присоединиться к игре.\nДля начала "
            "игры создатель лобби (или админ чата) должен отправить /startgame!",
            reply=False)


async def command_join(message: types.Message):
    groupName = message.chat.title
    chat_id = message.chat.id
    groupType = message.chat.type
    game: Game = GamesController.games.get(chat_id, None)
    fname = message.from_user.first_name

    if groupType not in ["group", "supergroup"]:
        await message.reply("Для начала требуется добавить бота в группу и написать там /newgame!")
    elif not game:
        await message.reply("В этом чате нет созданного лобби. Чтобы создать его, используй /newgame")
        # добавить создание игры в таком случае
    elif game.board:
        await message.reply("Игра уже началась. Пожалуйста, дождитесь следующей!")
    elif message.from_user.id in game.playerlist:
        await message.bot.send_message(game.chat_id, f"Ты уже в лобби, {fname}!")
    elif len(game.playerlist) >= 10:
        await message.bot.send_message(game.chat_id, "Вы достигли максимального количества игроков. Начните игру, используя /startgame!")
    else:
        tg_id = message.from_user.id
        player = Player(fname, tg_id)
        try:
            await message.bot.send_message(tg_id, f"Ты присоединился к игре в {groupName}. Скоро я сообщу твою секретную роль.")
            game.add_player(tg_id, player)
        except Exception:
            await message.bot.send_message(game.chat_id,
                             f"{fname}, я не могу отправить тебе сообщение в ЛС. Запусти чат с @secrethitler_russian_bot, используя \"Start\".\nПосле этого снова отправь /join.")
        else:
            log.info(f"{fname} ({tg_id}) joined a game in {game.chat_id}")
            if len(game.playerlist) > 4:
                await message.bot.send_message(game.chat_id, f"{fname} присоединился к игре. Отправьте /startgame, если это был последний игрок и вы хотите начать игру с {len(game.playerlist)} игроками!")
            elif len(game.playerlist) == 1:
                await message.bot.send_message(game.chat_id, f"{fname} присоединился к игре. В лобби только {len(game.playerlist)} игрок. Для начала игры требуется 5-10 игроков.")
            else:
                await message.bot.send_message(game.chat_id, f"{fname} присоединился к игре. В лобби только {len(game.playerlist)} игроков. Для начала игры требуется 5-10 игроков.")


async def command_startgame(message: types.Message):
    log.info("command_startgame called")
    chat_id = message.chat.id
    game: Game = GamesController.games.get(chat_id, None)
    player = await message.bot.get_chat_member(chat_id, message.from_user.id)
    if not game:
        await message.reply("В этом чате нет созданного лобби. Чтобы создать его, используй /newgame")
    elif game.board:
        await message.reply("Игра уже идёт!")
    elif message.from_user.id != game.initiator and player.status not in ("administrator", "creator"):
        await message.bot.send_message(game.chat_id, "Только создатель лобби или админ чата может запустить игру")
    elif len(game.playerlist) < 5:
        await message.bot.send_message(game.chat_id, "Недостаточно игроков (мин. 5, макс. 10). Присоединись к игре, используя /join")
    else:
        player_number = len(game.playerlist)
        await MainController.inform_players(message.bot, game, game.chat_id, player_number)
        await MainController.inform_fascists(message.bot, game, player_number)
        game.board = Board(player_number, game)
        log.info(game.board)
        log.info(f"len(games) Command_startgame: {str(len(GamesController.games))}")
        game.shuffle_player_sequence()
        game.board.state.player_counter = 0
        await message.bot.send_message(game.chat_id, game.board.print_board())
        group_name = message.chat.title
        await message.bot.send_message(ADMIN, "Game of Secret Hitler started in group %s (%d)" % (group_name, chat_id))
        await MainController.start_round(message.bot, game)

async def command_cancelgame(message: types.Message):
    log.info("command_cancelgame called")
    chat_id = message.chat.id
    if chat_id in GamesController.games.keys():
        game: Game = GamesController.games[chat_id]
        player = await message.bot.get_chat_member(chat_id, message.from_user.id)
        if message.from_user.id == game.initiator or player.status in ("administrator", "creator"):
            await MainController.end_game(message.bot, game, 99)
        else:
            await message.reply("Только создатель лобби или админ чата может отменить игру(лобби)")
    else:
        await message.reply("В этом чате нет созданного лобби. Чтобы создать его, используй /newgame")


async def command_votes(message: types.Message):
    try:
        #Send message of executing command
        chat_id = message.chat.id
        #await message.reply("Looking for history...")
        #Check if there is a current game
        if chat_id in GamesController.games.keys():
            game: Game = GamesController.games.get(chat_id, None)
            if not game.dateinitvote:
                # If date of init vote is null, then the voting didnt start
                await message.reply("Голосование ещё не началось.", reply=False)
            else:
                #If there is a time, compare it and send history of votes.
                start = game.dateinitvote
                stop = datetime.datetime.now()
                elapsed = stop - start
                if elapsed > datetime.timedelta(minutes=1):
                    history_text = "Vote history for President %s and Chancellor %s:\n\n" % (game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name)
                    for player in game.player_sequence:
                        # If the player is in the last_votes (He voted), mark him as he registered a vote
                        if player.tg_id in game.board.state.last_votes:
                            history_text += "%s проголосовал.\n" % (game.playerlist[player.tg_id].name)
                        else:
                            history_text += "%s НЕ проголосовал.\n" % (game.playerlist[player.tg_id].name)
                    await message.reply(history_text, reply=False)
                else:
                    await message.reply("Должно пройти пять минут, чтобы видеть полученные голоса", reply=False)
        else:
            await message.reply("В этом чате нет созданного лобби. Чтобы создать его, используй /newgame", reply=False)
    except Exception as e:
        await message.reply(str(e))


async def command_calltovote(message: types.Message):
    try:
        #Send message of executing command
        chat_id = message.chat.id
        #await message.reply("Looking for history...")
        #Check if there is a current game
        if chat_id in GamesController.games.keys():
            game: Game = GamesController.games.get(chat_id, None)
            if not game.dateinitvote:
                # If date of init vote is null, then the voting didnt start
                await message.reply("Голосование ещё не началось.", reply=False)
            else:
                #If there is a time, compare it and send history of votes.
                start = game.dateinitvote
                stop = datetime.datetime.now()
                elapsed = stop - start
                if elapsed > datetime.timedelta(minutes=1):
                    # Only remember to vote to players that are still in the game
                    history_text = ""
                    for player in game.player_sequence:
                        player: Player
                        # If the player is not in last_votes send him reminder
                        if player.tg_id not in game.board.state.last_votes:
                            history_text += "Пора голосовать, [%s](tg://user?id=%d)!\n" % (game.playerlist[player.tg_id].name, player.tg_id)
                    await message.reply(text=history_text, parse_mode=ParseMode.MARKDOWN, reply=False)
                else:
                    await message.reply("Должно пройти пять минут, чтобы пингануть игроков для голосования", reply=False)
        else:
            await message.reply("В этом чате нет созданного лобби. Чтобы создать его, используй /newgame", reply=False)
    except Exception as e:
        await message.reply(str(e))
