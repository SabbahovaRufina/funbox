import random
from app.models import Lobby
from models import GameSession, Catastrophe, Role, PlayerCard, PlayerState, CARD_FIELDS
from content import content
import math

MAX_REVEALED_CARDS = 3
MAX_CLAIMED_ROLES = 3

def _make_unique_cards(used_ids: set[str]) -> list[PlayerCard]:
    """Рандомайзер карт игрока"""
    cards = []
    for field in CARD_FIELDS:
        pool = getattr(content, field)
        candidates = [it for it in pool if f"{field}:{it['id']}" not in used_ids]
        item = random.choice(candidates)
        cid = f"{field}:{item['id']}"
        used_ids.add(cid)
        cards.append(PlayerCard(id=cid, field=field, title=item["title"]))
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

