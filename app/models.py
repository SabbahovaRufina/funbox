from dataclasses import dataclass, field
from typing import Optional
import uuid
from .game.models import GameSession


MAX_PLAYERS = 12
MIN_PLAYERS = 6
MAX_NAME_LENGTH = 12


@dataclass
class Player:
    """
    Игрок лобби — участник, подключающийся с телефона (не хост).

    Атрибуты:
        id:   уникальный идентификатор игрока (генерируется при добавлении в лобби);
        name: отображаемое имя, уникальное в пределах лобби.
    """
    id: str
    name: str

    def to_dict(self) -> dict:
        """Сериализует игрока в JSON-совместимый словарь для отправки клиенту."""
        return {"id": self.id, "name": self.name}


@dataclass
class Lobby:
    """
    Игровое лобби, объединяющее хоста и игроков по уникальному коду.

    Атрибуты:
        code:           уникальный код лобби (верхний регистр);
        host_connected: подключён ли хост;
        players:        игроки лобби, ``player_id -> Player``;
        started:        запущена ли игра.

    Содержит правила: сколько игроков можно принять (``can_accept_players``),
    когда можно стартовать (``can_start``), проверку имени (``has_name``,
    ``is_name_too_long``) и удаление опустевшего лобби (``is_empty``).
    """
    code: str
    host_connected: bool = False
    players: dict[str, Player] = field(default_factory=dict)  # player_id -> Player
    started: bool = False
    game: GameSession | None = None

    def add_player(self, name: str) -> Player:
        """Создаёт игрока и добавляет его в лобби. Возвращает созданного."""
        player = Player(id=str(uuid.uuid4()), name=name)
        self.players[player.id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        """Удаляет игрока из лобби по id. Если игрока нет — ничего не делает."""
        self.players.pop(player_id, None)

    def all_players(self) -> list[Player]:
        """Возвращает список всех игроков лобби."""
        return list(self.players.values())

    def is_empty(self) -> bool:
        """True, если нет подключённого хоста И нет игроков (лобби можно удалять)."""
        return not self.host_connected and not self.players

    def count_players(self) -> int:
        """Возвращает количество игроков в лобби."""
        return len(self.players)

    def is_full(self, limit: int = MAX_PLAYERS) -> bool:
        """True, если достигнут лимит игроков (лобби заполнено)."""
        return self.count_players() >= limit

    def can_accept_players(self) -> bool:
        """Можно ли принять нового игрока в лобби.
        True, если хост онлайн, есть места и игра ещё не началась."""
        return self.host_connected and not self.is_full() and not self.started

    def is_name_taken(self, name: str) -> bool:
        """True, если имя уже занято игроком в лобби. Сравнение регистронезависимое (casefold)."""
        return any(p.name.casefold() == name.casefold() for p in self.players.values())

    @staticmethod
    def is_name_too_long(name: str, limit: int = MAX_NAME_LENGTH) -> bool:
        """True, если длина имени превышает лимит."""
        return len(name) > limit

    def can_start(self, limit: int = MIN_PLAYERS) -> bool:
        """True, если игроков достаточно для старта игры."""
        return self.count_players() >= limit # нужны ли проверки онлайн ли хост, не начата ли игра

