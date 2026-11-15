from dataclasses import dataclass, field
from typing import Optional
import uuid


MAX_PLAYERS = 10
MIN_PLAYERS = 4
MAX_NAME_LENGTH = 12


@dataclass
class Player:
    """Игрок (телефон). Не хост."""
    id: str
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@dataclass
class Lobby:
    code: str
    host_connected: bool = False
    players: dict[str, Player] = field(default_factory=dict)  # player_id -> Player
    started: bool = False

    def add_player(self, name: str) -> Player:
        player = Player(id=str(uuid.uuid4()), name=name)
        self.players[player.id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        self.players.pop(player_id, None)

    def all_players(self) -> list[Player]:
        return list(self.players.values())

    def is_empty(self) -> bool:
        return not self.host_connected and not self.players

    def count_players(self) -> int:
        return len(self.players)

    def is_full(self, limit: int = MAX_PLAYERS) -> bool:
        return self.count_players() >= limit

    def can_accept_players(self) -> bool:
        return self.host_connected and not self.is_full() and not self.started

    def has_name(self, name: str) -> bool:
        return any(p.name.casefold() == name.casefold() for p in self.players.values())

    @staticmethod
    def is_name_too_long(name: str, limit: int = MAX_NAME_LENGTH) -> bool:
        return len(name) > limit

    def can_start(self, limit: int = MIN_PLAYERS) -> bool:
        return self.count_players() >= limit

