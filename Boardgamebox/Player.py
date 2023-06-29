from dataclasses import dataclass, field

@dataclass
class Player:
    name: str
    tg_id: int
    role: str = None
    party: str = None
    is_dead: bool = False
    inspected_players: dict = field(default_factory=dict)