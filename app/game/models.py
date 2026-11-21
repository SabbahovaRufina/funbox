from dataclasses import dataclass, field


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
class GameSession:
    code: str
    catastrophe: Catastrophe
    capacity: int
    roles: list[Role]
    players: dict[str, PlayerState]
    phase: str = "setup"

