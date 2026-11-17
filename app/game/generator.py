import random
from app.models import Lobby
from models import GameSession, Catastrophe, Role, PlayerCard, PlayerState, CARD_FIELDS
from content import content
import math

MAX_REVEALED_CARDS = 3
MAX_CLAIMED_ROLES = 3

def _make_cards() -> list[PlayerCard]:
    """Рандомайзер карт игрока"""
    cards = []
    for field in CARD_FIELDS:
        item = random.choice(getattr(content, field))   # content.profession -> list[dict]
        cards.append(PlayerCard(
            id=f"{field}:{item['id']}",
            field=field,
            title=item["title"],
        ))
    return cards

def generate_game(lobby: Lobby) -> GameSession:
    total = lobby.count_players()
    cat_raw = random.choice(content.catastrophes)
    cat = Catastrophe(**cat_raw)

    capacity = math.floor(total / 2)
    role_pool = random.sample(content.roles, k=min(capacity, len(content.roles)))
    role_pool = [Role(**r) for r in role_pool]

    players: dict[str, PlayerState] = {}
    for p in lobby.all_players():
        players[p.id] = PlayerState(
            player_id=p.id,
            cards=_make_cards(),
            revealed_ids=[],
            role_ids=[],
        )

    return GameSession(
        code=lobby.code,
        catastrophe=cat,
        capacity=capacity,
        roles=role_pool,              # ровно capacity штук
        # player_cards=,
        # chosen_roles=,
        phase="setup",                # setup -> discussion -> ...
    )

