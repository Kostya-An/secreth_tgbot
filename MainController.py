#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Julian Schrittwieser"
__forker__ = "Nie1iX"

import json
import logging as log
import random
import re
from random import randrange
import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram import Bot, Dispatcher, executor, filters

import Commands
from Constants.Cards import playerSets
from Constants.Config import TOKEN, STATS
from Boardgamebox.Game import Game
from Boardgamebox.Player import Player
import GamesController

import datetime
import os

# Enable logging

if not os.path.exists("logs"):
    os.mkdir("logs")

log.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                level=log.INFO,
                filename="logs/logging.log")

logger = log.getLogger(__name__)


policies_rus_to_en = {
    "либеральный" : "liberal",
    "фашистский" : "fascist",
}
policies_en_to_rus = {v: k for k, v in policies_rus_to_en.items()}

##
#
# Beginning of round
#
##
async def start_round(bot: Bot, game: Game):
    log.info("start_round called")
    if game.board.state.chosen_president is None:
        game.board.state.nominated_president = game.player_sequence[game.board.state.player_counter]
    else:
        game.board.state.nominated_president = game.board.state.chosen_president
        game.board.state.chosen_president = None
    await bot.send_message(game.chat_id,
        f"Следующий кандидат в Президенты — {game.board.state.nominated_president.name}."
        f"\n\n{game.board.state.nominated_president.name}, выбери Канцлера в ЛС!")
    await choose_chancellor(bot, game)
    # --> nominate_chosen_chancellor --> vote --> handle_voting --> count_votes --> voting_aftermath --> draw_policies
    # --> choose_policy --> pass_two_policies --> choose_policy --> enact_policy --> start_round


async def choose_chancellor(bot: Bot, game: Game):
    log.info("choose_chancellor called")
    strchat_id = str(game.chat_id)
    president_tg_id = 0
    chancellor_tg_id = 0
    buttons = []
    if game.board.state.president is not None:
        president_tg_id = game.board.state.president.tg_id
    if game.board.state.chancellor is not None:
        chancellor_tg_id = game.board.state.chancellor.tg_id
    for tg_id in game.playerlist:
        # If there are only five players left in the
        # game, only the last elected Chancellor is
        # ineligible to be Chancellor Candidate; the
        # last President may be nominated.
        if len(game.player_sequence) > 5:
            if tg_id != game.board.state.nominated_president.tg_id and game.playerlist[
                tg_id].is_dead == False and tg_id != president_tg_id and tg_id != chancellor_tg_id:
                name = game.playerlist[tg_id].name
                buttons.append(InlineKeyboardButton(name, callback_data=strchat_id + "_chan_" + str(tg_id)))
        else:
            if tg_id != game.board.state.nominated_president.tg_id and \
                game.playerlist[tg_id].is_dead == False and tg_id != chancellor_tg_id:
                name = game.playerlist[tg_id].name
                buttons.append(InlineKeyboardButton(name, callback_data=strchat_id + "_chan_" + str(tg_id)))

    chancellorMarkup = InlineKeyboardMarkup(row_width=2).add(*buttons)
    await bot.send_message(game.board.state.nominated_president.tg_id, game.board.print_board())
    await bot.send_message(game.board.state.nominated_president.tg_id, "Выбери своего Канцлера!",
        reply_markup=chancellorMarkup)


async def nominate_chosen_chancellor(callback: CallbackQuery):
    log.info("nominate_chosen_chancellor called")
    log.info(GamesController.games.keys())
    regex = re.search("(-[0-9]*)_chan_([0-9]*)", callback.data)
    chat_id = int(regex.group(1))
    chosen_tg_id = int(regex.group(2))
    try:
        game = GamesController.games.get(chat_id, None)
        log.info(game)
        log.info(game.board)
        game.board.state.nominated_chancellor = game.playerlist[chosen_tg_id]
        log.info("President %s (%d) nominated %s (%d)" % (
            game.board.state.nominated_president.name, game.board.state.nominated_president.tg_id,
            game.board.state.nominated_chancellor.name, game.board.state.nominated_chancellor.tg_id))
        await callback.bot.edit_message_text(f"Ты номинировал {game.board.state.nominated_chancellor.name} в Канцлеры!",
            callback.from_user.id, callback.message.message_id)
        await callback.bot.send_message(game.chat_id,
            f"Президент {game.board.state.nominated_president.name} номинировал "
            f"{game.board.state.nominated_chancellor.name} в Канцлеры. Объявляется голосование!")
        await vote(callback.bot, game)
    except AttributeError as e:
        log.error("nominate_chosen_chancellor: Game or board should not be None! Eror: " + str(e))
    except Exception as e:
        log.error("Unknown error: " + str(e))


async def vote(bot: Bot, game: Game):
    log.info("vote called")
    #When voting starts we start the counter to see later with the vote/calltovote command we can see who voted.
    game.dateinitvote = datetime.datetime.now()
    strchat_id = str(game.chat_id)
    buttons = [
        InlineKeyboardButton("Ja", callback_data=strchat_id + "_Ja"),
        InlineKeyboardButton("Nein", callback_data=strchat_id + "_Nein")
        ]
    voteMarkup = InlineKeyboardMarkup().add(*buttons)
    for tg_id in game.playerlist:
        if not game.playerlist[tg_id].is_dead:
            if game.playerlist[tg_id] is not game.board.state.nominated_president:
                # the nominated president already got the board before nominating a chancellor
                await bot.send_message(tg_id, game.board.print_board())
            await bot.send_message(tg_id,
                f"Хотите ли Вы избрать Президентом игрока <b>{game.board.state.nominated_president.name}</b> "
                f"и Канцлером игрока <b>{game.board.state.nominated_chancellor.name}</b>?",
                reply_markup=voteMarkup)


async def handle_voting(callback: CallbackQuery):
    log.info("handle_voting called: %s" % callback.data)
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = regex.group(2)
    try:
        game = GamesController.games[chat_id]
        tg_id = callback.from_user.id
        await callback.bot.edit_message_text("Спасибо за Ваш голос!", tg_id, callback.message.message_id)
        log.info("Player %s (%d) voted %s" % (callback.from_user.first_name, tg_id, answer))
        if tg_id not in game.board.state.last_votes:
            game.board.state.last_votes[tg_id] = answer
        if len(game.board.state.last_votes) == len(game.player_sequence):
            await count_votes(callback.bot, game)
    except:
        log.error("handle_voting: Game or board should not be None!")


async def count_votes(bot: Bot, game: Game):
    log.info("count_votes called")
    # Voted Ended
    game.dateinitvote = None
    voting_text = "Итоги голосования:\n\n"
    voting_success = False
    for player in game.player_sequence:
        if game.board.state.last_votes[player.tg_id] == "Ja":
            voting_text += f"{game.playerlist[player.tg_id].name} — Ja!\n"
        elif game.board.state.last_votes[player.tg_id] == "Nein":
            voting_text += f"{game.playerlist[player.tg_id].name} — Nein!\n"
    if list(game.board.state.last_votes.values()).count("Ja") > (
        len(game.player_sequence) / 2):  # because player_sequence doesnt include dead
        # VOTING WAS SUCCESSFUL
        log.info("Voting successful")
        voting_text += f"\nХайль, Президент {game.board.state.nominated_president.name}!" \
            f"\nХайль, Канцлер {game.board.state.nominated_chancellor.name}!"
        game.board.state.chancellor = game.board.state.nominated_chancellor
        game.board.state.president = game.board.state.nominated_president
        game.board.state.nominated_president = None
        game.board.state.nominated_chancellor = None
        voting_success = True
        await bot.send_message(game.chat_id, voting_text)
        await voting_aftermath(bot, game, voting_success)
    else:
        log.info("Voting failed")
        voting_text += "\nНароду не понравились эти кандидаты!"
        game.board.state.nominated_president = None
        game.board.state.nominated_chancellor = None
        game.board.state.failed_votes += 1
        await bot.send_message(game.chat_id, voting_text)
        if game.board.state.failed_votes == 3:
            await do_anarchy(bot, game)
        else:
            await voting_aftermath(bot, game, voting_success)


async def voting_aftermath(bot: Bot, game: Game, voting_success):
    log.info("voting_aftermath called")
    game.board.state.last_votes = {}
    if voting_success:
        if game.board.state.fascist_track >= 3 and game.board.state.chancellor.role == "Гитлер":
            # fascists win, because Hitler was elected as chancellor after 3 fascist policies
            game.board.state.game_endcode = -2
            await end_game(bot, game, game.board.state.game_endcode)
        elif game.board.state.fascist_track >= 3 and game.board.state.chancellor.role != "Гитлер" \
            and game.board.state.chancellor not in game.board.state.not_hitlers:
            game.board.state.not_hitlers.append(game.board.state.chancellor)
            await draw_policies(bot, game)
        else:
            # voting was successful and Hitler was not nominated as chancellor after 3 fascist policies
            await draw_policies(bot, game)
    else:
        await bot.send_message(game.chat_id, game.board.print_board())
        await start_next_round(bot, game)


async def draw_policies(bot: Bot, game: Game):
    log.info("draw_policies called")
    strchat_id = str(game.chat_id)
    game.board.state.veto_refused = False
    # shuffle discard pile with rest if rest < 3
    await shuffle_policy_pile(bot, game)
    buttons = []
    for _ in range(3):
        game.board.state.drawn_policies.append(game.board.policies.pop(0))
    for policy in game.board.state.drawn_policies:
        buttons.append(InlineKeyboardButton(policy, callback_data=strchat_id + "_" + policies_rus_to_en.get(policy)))
    choosePolicyMarkup = InlineKeyboardMarkup().add(*buttons)
    await bot.send_message(game.board.state.president.tg_id,
        "Вы взяли из стопки следующие 3 закона. Какой из них Вы хотите сбросить?",
        reply_markup=choosePolicyMarkup)


async def choose_policy(callback: CallbackQuery):
    log.info("choose_policy called")
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = policies_en_to_rus.get(regex.group(2))
    try:
        game = GamesController.games[chat_id]
        strchat_id = str(game.chat_id)
        tg_id = callback.from_user.id
        if len(game.board.state.drawn_policies) == 3:
            log.info("Player %s (%d) discarded %s" % (callback.from_user.first_name, tg_id, answer))
            await callback.bot.edit_message_text(
                f"{answer.capitalize()} закон сброшен!",
                tg_id,
                callback.message.message_id)
            # remove policy from drawn cards and add to discard pile, pass the other two policies
            for i in range(3):
                if game.board.state.drawn_policies[i] == answer:
                    game.board.discards.append(game.board.state.drawn_policies.pop(i))
                    break
            await pass_two_policies(callback.bot, game)
        elif len(game.board.state.drawn_policies) == 2:
            if answer == "veto":
                log.info("Player %s (%d) suggested a veto" % (callback.from_user.first_name, tg_id))
                await callback.bot.edit_message_text(
                    f"Вы предложили Президенту {game.board.state.president.name} наложить вето",
                    tg_id,
                    callback.message.message_id)
                await callback.bot.send_message(game.chat_id,
                    "Chancellor %s suggested a Veto to President %s." % (
                    game.board.state.chancellor.name, game.board.state.president.name))

                buttons = [
                    InlineKeyboardButton("Вето! (принять предложение)", callback_data=strchat_id + "_yesveto"),
                    InlineKeyboardButton("Нет вето! (отклонить предложение)", callback_data=strchat_id + "_noveto")
                    ]

                vetoMarkup = InlineKeyboardMarkup().add(*buttons)
                await callback.bot.send_message(game.board.state.president.tg_id,
                    f"Канцлер {game.board.state.chancellor.name} предложил Вам использовать право вето. "
                    "Вы хотите наложить вето на эти карты (сбросить их)?",
                    reply_markup=vetoMarkup)
            else:
                log.info("Player %s (%d) chose a %s policy" % (callback.from_user.first_name, tg_id, answer))
                await callback.bot.edit_message_text(
                    f"{answer.capitalize()} закон принят!",
                    tg_id,
                    callback.message.message_id)
                # remove policy from drawn cards and enact, discard the other card
                for i in range(2):
                    if game.board.state.drawn_policies[i] == answer:
                        game.board.state.drawn_policies.pop(i)
                        break
                game.board.discards.append(game.board.state.drawn_policies.pop(0))
                assert len(game.board.state.drawn_policies) == 0
                await enact_policy(callback.bot, game, answer, False)
        else:
            log.error("choose_policy: drawn_policies should be 3 or 2, but was " + str(
                len(game.board.state.drawn_policies)))
    except:
        log.error("choose_policy: Game or board should not be None!")


async def pass_two_policies(bot: Bot, game: Game):
    log.info("pass_two_policies called")
    strchat_id = str(game.chat_id)
    buttons = []
    for policy in game.board.state.drawn_policies:
        buttons.append(InlineKeyboardButton(policy, callback_data=strchat_id + "_" + policies_rus_to_en.get(policy)))
    if game.board.state.fascist_track == 5 and not game.board.state.veto_refused:
        buttons.append(InlineKeyboardButton("Veto", callback_data=strchat_id + "_veto"))
        choosePolicyMarkup = InlineKeyboardMarkup().add(*buttons)
        await bot.send_message(game.chat_id,
            f"Президент {game.board.state.president.name} передал два закона "
            f"Кацлеру {game.board.state.chancellor.name}.")
        await bot.send_message(game.board.state.chancellor.tg_id,
            f"Президент {game.board.state.president.name} передал Вам следующие два закона. " +
            "Какой из них Вы хотите принять? Также Вы можете предложить "
            "Президенту воспользоваться правом вето.",
            reply_markup=choosePolicyMarkup)
    elif game.board.state.veto_refused:
        choosePolicyMarkup = InlineKeyboardMarkup().add(*buttons)
        await bot.send_message(game.board.state.chancellor.tg_id,
            "Президент {game.board.state.president.name} отклонил предложение воспользоваться правом вето. "
            "Теперь вам остаётся только выбирать. Какой из законов Вы хотите принять?",
            reply_markup=choosePolicyMarkup)
    elif game.board.state.fascist_track < 5:
        choosePolicyMarkup = InlineKeyboardMarkup().add(*buttons)
        await bot.send_message(game.board.state.chancellor.tg_id,
            "Президент {game.board.state.president.name} передал Вам следующие два закона. "
            "Какой из них Вы хотите принять?",
            reply_markup=choosePolicyMarkup)


async def enact_policy(bot: Bot, game: Game, policy, anarchy):
    log.info("enact_policy called")
    if policy == "либеральный":
        game.board.state.liberal_track += 1
    elif policy == "фашистский":
        game.board.state.fascist_track += 1
    game.board.state.failed_votes = 0  # reset counter
    if not anarchy:
        await bot.send_message(game.chat_id,
            f"Президент {game.board.state.president.name} и Канцлер "
            f"{game.board.state.chancellor.name} приняли {policy} закон!")
    else:
        await bot.send_message(game.chat_id,
            f"Был принят самый верхний закон в стопке — {policy}.")
    await asyncio.sleep(3)
    await bot.send_message(game.chat_id, game.board.print_board())
    # end of round
    if game.board.state.liberal_track == 5:
        game.board.state.game_endcode = 1
        await end_game(bot, game, game.board.state.game_endcode)  # liberals win with 5 liberal policies
    if game.board.state.fascist_track == 6:
        game.board.state.game_endcode = -1
        await end_game(bot, game, game.board.state.game_endcode)  # fascists win with 6 fascist policies
    await asyncio.sleep(3)
    # End of legislative session, shuffle if necessary
    await shuffle_policy_pile(bot, game)
    if not anarchy:
        if policy == "фашистский":
            action = game.board.fascist_track_actions[game.board.state.fascist_track - 1]
            if action is None and game.board.state.fascist_track == 6:
                pass
            elif action == None:
                await start_next_round(bot, game)
            elif action == "policy":
                await bot.send_message(game.chat_id,
                    "Президентское право использовано: Просмотр законов "
                    u"\U0001F52E"
                    f"\nПрезидент {game.board.state.president.name} теперь знает следующие "
                    "три закона в стопке. "
                    "Он может поделиться полученными результатами "
                    "(или солгать о них!) на своё усмотрение.")
                await action_policy(bot, game)
            elif action == "kill":
                await bot.send_message(game.chat_id,
                    "Президентское право использовано: Уничтожение "
                    u"\U0001F5E1"
                    f"\nПрезидент {game.board.state.president.name} убивает одного игрока. "
                    "Вы можете обсудить решение, но в любом случае "
                    "последнее слово за Президентом.")
                await action_kill(bot, game)
            elif action == "inspect":
                await bot.send_message(game.chat_id,
                    "Президентское право использовано: Исследование лояльности "
                    u"\U0001F50E"
                    f"\nПрезидент {game.board.state.president.name} узнаёт партийную "
                    "принадлежность одного игрока "
                    "Он может поделиться полученными результатами "
                    "(или солгать о них!) на своё усмотрение.")
                await action_inspect(bot, game)
            elif action == "choose":
                await bot.send_message(game.chat_id,
                    "Президентское право использовано: Внеочередные выборы "
                    u"\U0001F454"
                    f"\nПрезидент {game.board.state.president.name} выбирает следующего кандидата "
                    "в президенты. После возвращается обычный порядок.")
                await action_choose(bot, game)
        else:
            await start_next_round(bot, game)
    else:
        await start_next_round(bot, game)


async def choose_veto(callback: CallbackQuery):
    log.info("choose_veto called")
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = regex.group(2)
    try:
        game = GamesController.games[chat_id]
        tg_id = callback.from_user.id
        if answer == "yesveto":
            log.info("Player %s (%d) accepted the veto" % (callback.from_user.first_name, tg_id))
            await callback.bot.edit_message_text("Вы приняли вето!", tg_id, callback.message.message_id)
            await callback.bot.send_message(game.chat_id,
                "Президент {game.board.state.president.name} принял вето Канцлера "
                f"{game.board.state.chancellor.name}. Не был принят ни один закон, "
                "но это считается несостоявшимися выборами.") # TODO: проверить, действительно ли в оригинале "выборы"
            game.board.discards += game.board.state.drawn_policies
            game.board.state.drawn_policies = []
            game.board.state.failed_votes += 1
            if game.board.state.failed_votes == 3:
                await do_anarchy(callback.bot, game)
            else:
                await callback.bot.send_message(game.chat_id, game.board.print_board())
                await start_next_round(callback.bot, game)
        elif answer == "noveto":
            log.info("Player %s (%d) declined the veto" % (callback.from_user.first_name, tg_id))
            game.board.state.veto_refused = True
            await callback.bot.edit_message_text("Вы отклонили вето!", tg_id, callback.message.message_id)
            await callback.bot.send_message(game.chat_id,
                f"Президент {game.board.state.president.name} отклонил вето Канцлера "
                f"{game.board.state.chancellor.name}. Канцлер обязан выбрать один из законов!")
            await pass_two_policies(callback.bot, game)
        else:
            log.error("choose_veto: Callback data can either be \"veto\" or \"noveto\", but not %s" % answer)
    except:
        log.error("choose_veto: Game or board should not be None!")


async def do_anarchy(bot: Bot, game: Game):
    log.info("do_anarchy called")
    await bot.send_message(game.chat_id, game.board.print_board())
    await bot.send_message(game.chat_id, "АНАРХИЯ!!")
    game.board.state.president = None
    game.board.state.chancellor = None
    top_policy = game.board.policies.pop(0)
    game.board.state.last_votes = {}
    await enact_policy(bot, game, top_policy, True)


async def action_policy(bot: Bot, game: Game):
    log.info("action_policy called")
    topPolicies = ""
    # shuffle discard pile with rest if rest < 3
    await shuffle_policy_pile(bot, game)
    for i in range(3):
        topPolicies += f"- {game.board.policies[i].capitalize()}\n"
    await bot.send_message(game.board.state.president.tg_id,
        "Верхние три закона в стопке (сверху самый первый):\n"
        + topPolicies +
        "\nВы можете поведать правду или солгать о них.")
    await start_next_round(bot, game)


async def action_kill(bot: Bot, game: Game):
    log.info("action_kill called")
    strchat_id = str(game.chat_id)
    buttons = []
    for tg_id in game.playerlist:
        if tg_id != game.board.state.president.tg_id and game.playerlist[tg_id].is_dead == False:
            name = game.playerlist[tg_id].name
            buttons.append(InlineKeyboardButton(name, callback_data=strchat_id + "_kill_" + str(tg_id)))
    killMarkup = InlineKeyboardMarkup().add(*buttons)
    await bot.send_message(game.board.state.president.tg_id, game.board.print_board())
    await bot.send_message(game.board.state.president.tg_id,
        "Выберите, какого игрока вы хотите убить. Вы можете обсудить своё решение с другими. Выбирайте мудро!",
        reply_markup=killMarkup)


async def choose_kill(callback: CallbackQuery):
    log.info("choose_kill called")
    regex = re.search("(-[0-9]*)_kill_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[chat_id]
        chosen = game.playerlist[answer]
        chosen.is_dead = True
        if game.player_sequence.index(chosen) <= game.board.state.player_counter:
            game.board.state.player_counter -= 1
        game.player_sequence.remove(chosen)
        game.board.state.dead += 1
        log.info("Player %s (%d) killed %s (%d)" % (
            callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.tg_id))
        await callback.bot.edit_message_text(
            f"Вы убили игрока {chosen.name}!",
            callback.from_user.id,
            callback.message.message_id)
        if chosen.role == "Гитлер":
            await callback.bot.send_message(game.chat_id,
                f"Президент {game.board.state.president.name} убил игрока {chosen.name}, бывшего Гитлером!")
            await end_game(callback.bot, game, 2)
        else:
            await callback.bot.send_message(game.chat_id,
                f"Президент {game.board.state.president.name} убил игрока {chosen.name}, который не был "
                f"Гитлером. {chosen.name}, ты мёртв, и тебе больше нельзя говорить!")
            await callback.bot.send_message(game.chat_id, game.board.print_board())
            await start_next_round(callback.bot, game)
    except:
        log.error("choose_kill: Game or board should not be None!")


async def action_choose(bot: Bot, game: Game):
    log.info("action_choose called")
    strchat_id = str(game.chat_id)
    buttons = []

    for tg_id in game.playerlist:
        if tg_id != game.board.state.president.tg_id and game.playerlist[tg_id].is_dead == False:
            name = game.playerlist[tg_id].name
            buttons.append(InlineKeyboardButton(name, callback_data=strchat_id + "_choo_" + str(tg_id)))

    inspectMarkup = InlineKeyboardMarkup().add(*buttons)
    await bot.send_message(game.board.state.president.tg_id, game.board.print_board())
    await bot.send_message(game.board.state.president.tg_id,
        "Выберите следующего кандидата в Президенты. После этого вернётся обычный порядок.",
        reply_markup=inspectMarkup)


async def choose_choose(callback: CallbackQuery):
    log.info("choose_choose called")
    regex = re.search("(-[0-9]*)_choo_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[chat_id]
        chosen = game.playerlist[answer]
        game.board.state.chosen_president = chosen
        log.info(
            "Player %s (%d) chose %s (%d) as next president" % (
            callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.tg_id))
        await callback.bot.edit_message_text(
            f"Вы выбрали {chosen.name} следующим кандидатом в Президенты!",
            callback.from_user.id,
            callback.message.message_id)
        await callback.bot.send_message(game.chat_id,
            f"Президент {game.board.state.president.name} выбрал {chosen.name} следующим кандидатом в Президенты!")
        await start_next_round(callback.bot, game)
    except:
        log.error("choose_choose: Game or board should not be None!")


async def action_inspect(bot: Bot, game: Game):
    log.info("action_inspect called")
    strchat_id = str(game.chat_id)
    buttons = []
    for tg_id in game.playerlist:
        if tg_id != game.board.state.president.tg_id and game.playerlist[tg_id].is_dead == False:
            name = game.playerlist[tg_id].name
            buttons.append(InlineKeyboardButton(name, callback_data=strchat_id + "_insp_" + str(tg_id)))
    inspectMarkup = InlineKeyboardMarkup().add(*buttons)
    await bot.send_message(game.board.state.president.tg_id, game.board.print_board())
    await bot.send_message(game.board.state.president.tg_id,
        "Вы можете увидеть партийную принадлежность одного из игроков. Чью Вы хотите знать?",
        reply_markup=inspectMarkup)


async def choose_inspect(callback: CallbackQuery):
    log.info("choose_inspect called")
    regex = re.search("(-[0-9]*)_insp_(.*)", callback.data)
    chat_id = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[chat_id]
        chosen = game.playerlist[answer]
        log.info(
            "Player %s (%d) inspects %s (%d)'s party membership (%s)" % (
            callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.tg_id,
            chosen.party))
        await callback.bot.edit_message_text(
            f"Партийная принадлежность игрока {chosen.name} — {chosen.party}",
            callback.from_user.id,
            callback.message.message_id)
        await callback.bot.send_message(game.chat_id,
            f"Президент {game.board.state.president.name} узнал партийную принадлежность игрока {chosen.name}.")
        await start_next_round(callback.bot, game)
    except:
        log.error("choose_inspect: Game or board should not be None!")


async def start_next_round(bot: Bot, game: Game):
    log.info("start_next_round called")
    # start next round if there is no winner (or /cancel)
    if game.board.state.game_endcode == 0:
        # start new round
        await asyncio.sleep(5)
        # if there is no special elected president in between
        if game.board.state.chosen_president is None:
            await increment_player_counter(game)
        await start_round(bot, game)


##
#
# End of round
#
##

async def end_game(bot: Bot, game: Game, game_endcode):
    log.info("end_game called")
    ##
    # game_endcode:
    #   -2  fascists win by electing Hitler as chancellor
    #   -1  fascists win with 6 fascist policies
    #   0   not ended
    #   1   liberals win with 5 liberal policies
    #   2   liberals win by killing Hitler
    #   99  game cancelled
    #
    with open(STATS, "r") as f:
        stats = json.load(f)

    if game_endcode == 99:
        if GamesController.games[game.chat_id].board is not None:
            await bot.send_message(game.chat_id, f"Игра отменена!\n\n{game.print_roles()}")
            # await bot.send_message(ADMIN, "Game of Secret Hitler canceled in group %d" % game.chat_id)
            stats["cancelled"] = stats["cancelled"] + 1
        else:
            await bot.send_message(game.chat_id, "Игра отменена!")
    else:
        if game_endcode == -2:
            await bot.send_message(game.chat_id,
                f"Конец игры! Фашисты победили, избрав Гитлера Канцлером!n\n{game.print_roles()}")
            stats["fascwin_hitler"] = stats["fascwin_hitler"] + 1
        if game_endcode == -1:
            await bot.send_message(game.chat_id,
                f"Конец игры! Фашисты победили, приняв 6 фашистских законов!\n\n{game.print_roles()}")
            stats["fascwin_policies"] = stats["fascwin_policies"] + 1
        if game_endcode == 1:
            await bot.send_message(game.chat_id,
                f"Конец игры! Либералы победили, приняв 5 либеральных законов!\n\n{game.print_roles()}")
            stats["libwin_policies"] = stats["libwin_policies"] + 1
        if game_endcode == 2:
            await bot.send_message(game.chat_id,
                f"Конец игры! Либералы победили, убив Гитлера!\n\n{game.print_roles()}")
            stats["libwin_kill"] = stats["libwin_kill"] + 1

        # await bot.send_message(ADMIN, "Game of Secret Hitler ended in group %d" % game.chat_id)

    with open(STATS, "w") as f:
        json.dump(stats, f, indent=4)
    del GamesController.games[game.chat_id]


async def inform_players(bot: Bot, game: Game, chat_id, player_number):
    log.info("inform_players called")
    await bot.send_message(chat_id,
        f"Начинаем игру с {player_number} игроками!\n{await print_player_info(player_number)}\n"
        "Зайдите в ЛС и посмотрите свою секретную роль!")
    available_roles = list(playerSets[player_number]["roles"])  # copy not reference because we need it again later
    for tg_id in game.playerlist:
        random_index = randrange(len(available_roles))
        role = available_roles.pop(random_index)
        party = await get_membership(role)
        game.playerlist[tg_id].role = role
        game.playerlist[tg_id].party = party
        await bot.send_message(tg_id, f"Твоя секретная роль — {role}\nТвоя партия — {party}")


async def print_player_info(player_number):
    if player_number == 5:
        return "В игре 3 либерала, 1 фашист и Гитлер. Гитлер знает, кто является фашистом."
    elif player_number == 6:
        return "В игре 4 либерала, 1 фашист и Гитлер. Гитлер знает, кто является фашистом."
    elif player_number == 7:
        return "В игре 4 либерала, 2 фашиста и Гитлер. Гитлер не знает, кто является фашистом."
    elif player_number == 8:
        return "В игре 5 либералов, 2 фашиста и Гитлер. Гитлер не знает, кто является фашистом."
    elif player_number == 9:
        return "В игре 5 либералов, 3 фашиста и Гитлер. Гитлер не знает, кто является фашистом."
    elif player_number == 10:
        return "В игре 6 либералов, 3 фашиста и Гитлер. Гитлер не знает, кто является фашистом."


async def inform_fascists(bot: Bot, game: Game, player_number):
    log.info("inform_fascists called")
    for tg_id in game.playerlist:
        role = game.playerlist[tg_id].role
        if role == "Фашист":
            fascists = game.get_fascists()
            if player_number > 6:
                fstring = "Ваши товарищи-фашисты: "
                for f in fascists:
                    if f.tg_id != tg_id:
                        fstring += f.name + ", "
                fstring = fstring[:-2]
                await bot.send_message(tg_id, fstring)
            hitler = game.get_hitler()
            await bot.send_message(tg_id, f"Гитлер — {hitler.name}")
        elif role == "Гитлер":
            if player_number <= 6:
                fascists = game.get_fascists()
                await bot.send_message(tg_id, f"Твой товарищ-фашист: {fascists[0].name}")
        elif role == "Либерал":
            pass
        else:
            log.error("inform_fascists: can\"t handle the role %s" % role)


async def get_membership(role):
    log.info("get_membership called")
    if role == "Фашист" or role == "Гитлер":
        return "фашистская"
    elif role == "Либерал":
        return "либеральная"
    else:
        return None


async def increment_player_counter(game: Game):
    log.info("increment_player_counter called")
    if game.board.state.player_counter < len(game.player_sequence) - 1:
        game.board.state.player_counter += 1
    else:
        game.board.state.player_counter = 0


async def shuffle_policy_pile(bot: Bot, game: Game):
    log.info("shuffle_policy_pile called")
    if len(game.board.policies) < 3:
        game.board.discards += game.board.policies
        game.board.policies = random.sample(game.board.discards, len(game.board.discards))
        game.board.discards = []
        await bot.send_message(game.chat_id,
            "В стопке законов не хватило карт, поэтому их остаток был перемешан со стопкой сброса!")


async def error(update, error):
    logger.warning("Update '%s' caused error '%s'" % (update, error))


async def main():
    GamesController.init() # Call only once

    bot = Bot(TOKEN)

    # Get the dispatcher to register handlers
    dp = Dispatcher(bot)

    # on different commands - answer in Telegram
    dp.register_message_handler(Commands.command_start, commands=["start"])
    dp.register_message_handler(Commands.command_help, commands=["help"])
    dp.register_message_handler(Commands.command_board, commands=["board"])
    dp.register_message_handler(Commands.command_rules, commands=["rules"])
    dp.register_message_handler(Commands.command_ping, commands=["ping"])
    dp.register_message_handler(Commands.command_symbols, commands=["symbols"])
    dp.register_message_handler(Commands.command_stats, commands=["stats"])
    dp.register_message_handler(Commands.command_newgame, commands=["newgame"])
    dp.register_message_handler(Commands.command_startgame, commands=["startgame"])
    dp.register_message_handler(Commands.command_cancelgame, commands=["cancelgame"])
    dp.register_message_handler(Commands.command_join, commands=["join"])
    dp.register_message_handler(Commands.command_votes, commands=["votes"])
    dp.register_message_handler(Commands.command_calltovote, commands=["calltovote"])

    dp.register_callback_query_handler(nominate_chosen_chancellor, filters.Regexp("(-[0-9]*)_chan_(.*)"))
    dp.register_callback_query_handler(choose_inspect, filters.Regexp("(-[0-9]*)_insp_(.*)", ))
    dp.register_callback_query_handler(choose_choose, filters.Regexp("(-[0-9]*)_choo_(.*)"))
    dp.register_callback_query_handler(choose_kill, filters.Regexp("(-[0-9]*)_kill_(.*)"))
    dp.register_callback_query_handler(choose_veto, filters.Regexp("(-[0-9]*)_(yesveto|noveto)"))
    dp.register_callback_query_handler(choose_policy, filters.Regexp("(-[0-9]*)_(liberal|fascist|veto)"))
    dp.register_callback_query_handler(handle_voting, filters.Regexp("(-[0-9]*)_(Ja|Nein)"))

    # log all errors
    dp.register_errors_handler(error)

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    try:
        await dp.skip_updates()
        print("Bot started!")
        await dp.start_polling()
    except KeyboardInterrupt:
        print("Bot stopped!")

if __name__ == "__main__":
    asyncio.run(main())
