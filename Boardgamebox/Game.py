from random import shuffle

from Boardgamebox.Board import Board
from Boardgamebox.Player import Player

from typing import Dict, List

class Game(object):
    def __init__(self, chat_id, initiator):
        self.playerlist: Dict[int, Player] = {}
        self.player_sequence: List[Player] = []
        self.chat_id: int = chat_id
        self.board: Board = None
        self.initiator = initiator
        self.dateinitvote = None

    def add_player(self, tg_id, player):
        self.playerlist[tg_id] = player

    def get_hitler(self) -> Player:
        for tg_id in self.playerlist:
            if self.playerlist[tg_id].role == "Гитлер":
                return self.playerlist[tg_id]

    def get_fascists(self) -> List[Player]:
        fascists = []
        for tg_id in self.playerlist:
            if self.playerlist[tg_id].role == "Фашист":
                fascists.append(self.playerlist[tg_id])
        return fascists

    def shuffle_player_sequence(self):
        for tg_id in self.playerlist:
            self.player_sequence.append(self.playerlist[tg_id])
        shuffle(self.player_sequence)

    def remove_from_player_sequence(self, Player):
        for p in self.player_sequence:
            if p.tg_id == Player.tg_id:
                p.remove(Player)

    def print_roles(self) -> str:
        rtext = ""
        if self.board is None:
            #game was not started yet
            return rtext
        else:
            for p in self.playerlist:
                rtext += f"Секретная роль игрока {self.playerlist[p].name}"
                if self.playerlist[p].is_dead:
                    rtext += " (мёртв)"
                rtext += f" — {self.playerlist[p].role}\n"
            return rtext
