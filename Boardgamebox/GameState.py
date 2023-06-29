from dataclasses import dataclass, field

from Boardgamebox.Player import Player

@dataclass
class GameState:
    """Storage object for game state"""
    liberal_track: int = 0
    fascist_track: int = 0
    failed_votes: int = 0
    president: Player = None
    nominated_president: Player = None
    nominated_chancellor: Player = None
    chosen_president: Player = None
    chancellor: Player = None
    dead: int = 0
    last_votes: dict = field(default_factory=dict)
    game_endcode: int = 0
    drawn_policies: list = field(default_factory=list)
    player_counter: int = 0
    veto_refused: bool = False
    not_hitlers: list = field(default_factory=list)
