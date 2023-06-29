from typing import Dict

from Boardgamebox.Game import Game

games: Dict[int, Game]

def init():
    global games
    games = {}