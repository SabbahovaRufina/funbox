import random
from models import (
    Lobby, GameState, CardSet,
    PROFESSIONS, HOBBIES, FACTS, BAGGAGE, HEALTH, PHOBIAS,
    CATASTROPHES, NEEDED_ROLES,
)

GENDERS = ["мужчина", "женщина"]
AGES = list(range(18, 71))


def _sample_unique(pool: list, n: int) -> list:
    """Возвращает n уникальных элементов пула (пул не должен быть короче n)."""
    if n > len(pool):
        return random.choices(pool, k=n)  # fallback, если игроков больше пула
    return random.sample(pool, k=n)


def start_game(lobby: Lobby) -> GameState:
    players = lobby.all_players()
    n = len(players)

    professions = _sample_unique(PROFESSIONS, n)
    hobbies = _sample_unique(HOBBIES, n)
    facts = _sample_unique(FACTS, n)
    baggage = _sample_unique(BAGGAGE, n)
    health = _sample_unique(HEALTH, n)
    phobias = _sample_unique(PHOBIAS, n)

    cards: dict[str, CardSet] = {}
    for i, p in enumerate(players):
        bio = f"{random.choice(GENDERS)}, {random.choice(AGES)} лет"
        cards[p.id] = CardSet(
            profession=professions[i],
            bio=bio,
            hobby=hobbies[i],
            fact=facts[i],
            baggage=baggage[i],
            health=health[i],
            phobia=phobias[i],
        )

    game = GameState(
        catastrophe=random.choice(CATASTROPHES),
        needed_roles=list(NEEDED_ROLES),
        cards=cards,
    )
    lobby.game = game
    lobby.started = True
    return game