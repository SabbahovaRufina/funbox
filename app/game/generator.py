import random
from app.models import Lobby
from app.game.models import GameSession, Catastrophe, Role, PlayerCard, PlayerState, CARD_FIELDS
from app.game.content import profession, HEALTH, BIO, HOBBY, PHOBIA, BAGGAGE, FACT, SPECIAL, CATASTROPHES, ROLES
from app.game.models import Phase
import math


FIELD_POOLS = {
    "profession": profession,
    "health": HEALTH,
    "bio": BIO,
    "hobby": HOBBY,
    "phobia": PHOBIA,
    "baggage": BAGGAGE,
    "fact": FACT,
    "special": SPECIAL,
}


def _pick_card(field: str, role_tag: str, gender: str, used_ids: set[str], rng: random.Random, strict_tag: bool=False):
    pool = FIELD_POOLS[field]

    if role_tag == "neutral":
        allowed_tags = {"neutral"}
    elif strict_tag:
        allowed_tags = {role_tag}          # без neutral
    else:
        allowed_tags = {role_tag, "neutral"}

    candidates = [
        item for item in pool
        if item["gender"] in (gender, "neutral") # совпадение по гендеру или neutral
        and (set(item["tags"]) & allowed_tags) # совпадение по ролям в allowed_tags
        and f"{field}:{item['id']}" not in used_ids # уникально среди игроков в лобби
    ]

    if not candidates:
        candidates = [
            item for item in pool
            if item["gender"] in (gender, "neutral")
            and (set(item["tags"]) & allowed_tags)
        ]

    if not candidates:
        candidates = [
            item for item in pool
            if item["gender"] in (gender, "neutral")
        ]

    item = rng.choice(candidates)
    used_ids.add(f"{field}:{item['id']}")
    return item


def _make_cards(role_tag: str, gender: str, used_ids: set[str], rng: random.Random) -> list[PlayerCard]:
    """
    Генерирует полный набор карт для одного игрока.
    """
    cards = []
    for field in FIELD_POOLS:
        item = _pick_card(
            field, role_tag, gender, used_ids, rng,
            strict_tag=(field == "profession")
        )

        cards.append(PlayerCard(
            id=f"{field}:{item['id']}",
            field=field,
            title=item["title"],
            description=item.get("description", "")
        ))

    return cards


def _make_gender_list(total: int, rng: random.Random) -> list[str]:
    """
    Генерирует список полов для игроков.
    Мужчин: ceil(total / 2)
    Женщин: floor(total / 2)
    Возвращает перемешанный список (чтобы порядок был случайным).
    """
    males_count = math.ceil(total / 2)
    females_count = total - males_count
    genders = ["male"] * males_count + ["female"] * females_count
    rng.shuffle(genders)

    return genders


def _assign_role_tags(cat: Catastrophe, total: int, rng: random.Random) -> list[str]:
    """
    Раздает скрытые теги ролей для генерации карт.
    Идет строго по порядку тегов катастрофы (от важных к менее важным).
    На каждый тег выделяется РОВНО по 2 человека.
    Если на очередной тег не хватает 2 человек — этот тег и все последующие пропускаются,
    а оставшиеся игроки получают "neutral".
    """
    assigned = []

    for tag in cat.role_tags:
        if tag == "neutral":
            continue
        if len(assigned) + 2 <= total:
            assigned.extend([tag, tag])
        else:
            break
    while len(assigned) < total:
        assigned.append("neutral")
    rng.shuffle(assigned)

    return assigned


def generate_game(lobby: Lobby) -> GameSession:
    rng = random.Random()
    total = lobby.count_players()

    cat = Catastrophe(**rng.choice(CATASTROPHES))

    capacity = math.floor(total / 2)
    important_tags = cat.role_tags[:capacity]
    roles_dict = {r["id"]: r for r in ROLES}
    role_pool = [
        Role(**roles_dict[tag])
        for tag in important_tags
        if tag in roles_dict
    ]

    genders = _make_gender_list(total, rng)
    role_tags = _assign_role_tags(cat, total, rng)

    used_ids: set[str] = set()
    players: dict[str, PlayerState] = {}
    for i, p in enumerate(lobby.all_players()):
        players[p.id] = PlayerState(
            player_id=p.id,
            role_tag=role_tags[i],
            gender=genders[i],
            cards=_make_cards(role_tags[i], genders[i], used_ids, rng),
        )

    return GameSession(
        code=lobby.code,
        catastrophe=cat,
        capacity=capacity,
        roles=role_pool,
        players=players,
        phase=Phase.SETUP,
    )