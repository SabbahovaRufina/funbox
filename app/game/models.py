from dataclasses import dataclass, field


@dataclass
class CardSet:
    profession: str
    bio: str
    hobby: str
    fact: str
    baggage: str
    health: str
    phobia: str

    def to_dict(self) -> dict:
        return {
            "profession": self.profession,
            "bio": self.bio,
            "hobby": self.hobby,
            "fact": self.fact,
            "baggage": self.baggage,
            "health": self.health,
            "phobia": self.phobia,
        }


@dataclass
class GameState:
    catastrophe: str
    needed_roles: list[str]
    cards: dict[str, CardSet]      # player_id -> CardSet
    round: int = 0

