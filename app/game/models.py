from dataclasses import dataclass, field


@dataclass
class Role:
    """Роли в игре"""
    id: str
    title: str            # "Врач", "Инженер"
    description: str      # что делает в бункере
    task: str             # задачи роли в игре


CARD_FIELDS = ("profession", "health", "hobby", "phobia", "baggage", "fact", "special")

@dataclass
class PlayerCard:
    id: str                    # уникальный id карты (для "reveal")
    field: str                 # одно из CARD_FIELDS
    title: str                 # "Хирург"


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
    survival_years: int   # сколько надо продержаться


@dataclass
class GameSession:
    code: str
    catastrophe: Catastrophe
    capacity: int  # ← ключевое: мест в бункере
    roles: list[Role]  # длина == bunker_capacity
    player_cards: dict[str, PlayerCard]  # player_id -> карты
    chosen_roles: dict[str, list[str]]
    phase: str = "reveal"  # reveal -> discussion -> vote -> result

