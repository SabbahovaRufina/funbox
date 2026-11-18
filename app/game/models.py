from dataclasses import dataclass, field


@dataclass
class Role:
    """Роли в игре"""
    id: str
    title: str            # "Врач", "Инженер"
    description: str      # что делает в бункере
    task: str             # задачи роли в игре
    tags: list[str]


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
    cards: list[PlayerCard]         # все карты игрока
    revealed_ids: list[str]         # до 3 выбранных
    role_ids: list[str]             # до 3 претензий
    ready: bool = False             # подтвердил выбор карт и ролей


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

