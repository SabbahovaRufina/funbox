from dataclasses import dataclass, field
from enum import Enum
import time


@dataclass
class Role:
    """Роли в игре"""
    id: str
    title: str            # "Врач", "Инженер"
    # description: str      # что делает в бункере
    # task: str             # задачи роли в игре


CARD_FIELDS = ("profession", "bio", "health", "hobby", "phobia", "baggage", "fact", "special")

@dataclass
class PlayerCard:
    id: str                    # уникальный id карты (для "reveal")
    field: str                 # одно из CARD_FIELDS
    title: str                 # "Хирург"
    description: str = ""


@dataclass
class PlayerState:
    player_id: str
    role_tag: str                    # СКРЫТО от клиента; для механик
    gender: str
    cards: list[PlayerCard]
    revealed_ids: list[str] = field(default_factory=list)   # до 3, раскрыто
    role_ids: list[str] = field(default_factory=list)       # до 3, претензии
    ready: bool = False


@dataclass
class Catastrophe:
    title: str            # "Ядерная зима"
    description: str
    role_tags: list[str]


@dataclass
class Phase(str, Enum):
    SETUP = "setup"           # генерация катастрофы и раздача карт
    REVEAL = "reveal"         # раскрытие карт и таймер
    VOTING = "voting"         # голосование за изгнание
    FINISHED = "finished"     # игра окончена


@dataclass
class Vote:
    voter_id: str
    target_id: str | None


@dataclass
class RevealRound:
    """Раунд поочерёдного раскрытия карт."""
    order: list[str]                    # player_id в порядке хода
    current_index: int = 0
    deadline: float | None = None       # time.monotonic() + duration
    duration: int = 60                  # секунд на игрока
    reveal_limit: int = 3               # сколько карт можно раскрыть в этот ход
    finished: bool = False
    round_number: int = 1               # 1-й круг → 3 карты, дальше → 1


@dataclass
class GameSession:
    code: str
    catastrophe: Catastrophe
    capacity: int
    roles: list[Role]
    players: dict[str, PlayerState]
    phase: Phase = field(default_factory=lambda: Phase.SETUP)

    # голосование
    votes: dict[str, Vote] = field(default_factory=dict)  # voter_id -> Vote
    voting_round: int = 1
    eliminated: list[str] = field(default_factory=list)  # id изгнанных

    # раскрытие карт
    revealed: dict[str, list[str]] = field(default_factory=dict)  # player_id -> [card_id]

    reveal_round: RevealRound | None = None
    reveal_rounds_done: int = 0  # сколько кругов reveal уже прошло

