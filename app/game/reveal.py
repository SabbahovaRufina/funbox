import time
import random
import asyncio
from dataclasses import dataclass, field

from .models import GameSession, RevealRound, Phase


# --- утилиты ---

def current_player_id(game: GameSession) -> str | None:
    """Кто сейчас должен раскрывать карты."""
    r = game.reveal_round
    if not r or r.finished:
        return None
    if 0 <= r.current_index < len(r.order):
        return r.order[r.current_index]
    return None


def revealed_for(game: GameSession, player_id: str) -> list[str]:
    return game.revealed.setdefault(player_id, [])


def remaining_for_player(game: GameSession, player_id: str) -> int:
    """Сколько ещё карт можно раскрыть текущему игроку в этом ходе."""
    r = game.reveal_round
    if not r:
        return 0
    return max(0, r.reveal_limit - len(revealed_for(game, player_id)))


def is_cards_available(game: GameSession, player_id: str, card_id: str) -> bool:
    st = game.players.get(player_id)
    if not st:
        return False
    if card_id not in {c.id for c in st.cards}:
        return False
    if card_id in revealed_for(game, player_id):
        return False
    return True


# --- старт круга ---

def start_reveal_round(game: GameSession, duration: int = 60) -> RevealRound:
    game.reveal_rounds_done += 1
    round_number = game.reveal_rounds_done
    reveal_limit = 3 if round_number == 1 else 1

    order = list(game.players.keys())
    random.shuffle(order)

    rr = RevealRound(
        order=order,
        duration=duration,
        reveal_limit=reveal_limit,
        round_number=round_number,
        deadline=time.monotonic() + duration,
    )
    game.reveal_round = rr
    game.phase = Phase.REVEAL
    return rr


def remaining(game: GameSession) -> float:
    r = game.reveal_round
    if not r or r.deadline is None:
        return 0.0
    return max(0.0, r.deadline - time.monotonic())


def advance(game: GameSession) -> str:
    """'next' | 'finished' | 'none'"""
    r = game.reveal_round
    if not r or r.finished:
        return "none"

    r.current_index += 1
    if r.current_index >= len(r.order):
        r.finished = True
        r.deadline = None
        return "finished"

    r.deadline = time.monotonic() + r.duration
    return "next"


# --- применение выбора игрока ---

@dataclass
class RevealResult:
    ok: bool
    reason: str = ""
    revealed: list[str] = field(default_factory=list)   # что реально раскрылось
    auto: bool = False                                   # был ли автовыбор
    round_finished: bool = False
    next_player_id: str | None = None


def apply_reveal(
    game: GameSession,
    player_id: str,
    card_ids: list[str],
    auto: bool = False,
) -> RevealResult:
    """
    Применяет раскрытие карт игроком. Идемпотентно-безопасно:
    лишние/невалидные card_ids отбрасываются, добираются случайные до лимита,
    если auto=True (или если после валидных ничего не осталось и ход завершается).
    """
    r = game.reveal_round
    if not r or r.finished:
        return RevealResult(ok=False, reason="no_active_round")

    if current_player_id(game) != player_id:
        return RevealResult(ok=False, reason="not_your_turn")

    st = game.players.get(player_id)
    if not st:
        return RevealResult(ok=False, reason="unknown_player")

    already = revealed_for(game, player_id)
    limit_left = max(0, r.reveal_limit - len(already))

    # отбираем валидные карты из запроса, без дублей
    picked: list[str] = []
    for cid in card_ids:
        if cid in picked:
            continue
        if is_cards_available(game, player_id, cid):
            picked.append(cid)
        if len(picked) >= limit_left:
            break

    # если auto — добираем случайными до лимита
    if auto:
        unopened = [c.id for c in st.cards if c.id not in already and c.id not in picked]
        random.shuffle(unopened)
        need = limit_left - len(picked)
        picked.extend(unopened[:need])
        already.extend(picked)
    else:
        already.extend(picked)

    revealed_now = picked  # что реально добавили в этом вызове

    # ход считается завершённым, когда игрок раскрыл свой лимит
    # (или auto=True — тогда точно завершаем)
    turn_done = auto or len(already) >= r.reveal_limit

    if not turn_done:
        # игрок ещё может раскрывать в этом ходе
        return RevealResult(ok=True, revealed=revealed_now, auto=auto)

    # --- завершаем ход ---
    step = advance(game)
    if step == "finished":
        return RevealResult(
            ok=True, revealed=revealed_now, auto=auto,
            round_finished=True, next_player_id=None,
        )

    return RevealResult(
        ok=True, revealed=revealed_now, auto=auto,
        round_finished=False, next_player_id=current_player_id(game),
    )


# --- авто-таймаут ---

async def run_reveal_timeout(
    game: GameSession,
    code: str,
    on_event,   # async callable(code, event_dict)
    lock: asyncio.Lock,
) -> None:
    """
    Фоновая задача: ждёт до дедлайна текущего хода, затем делает автовыбор
    и продвигает игру. Если дедлайн сдвинулся (игрок успел) — пересчитывает.
    Завершается, когда круг finished.
    """
    while True:
        r = game.reveal_round
        if not r or r.finished or r.deadline is None:
            return

        # ждём до дедлайна (или чуть дольше, чтобы не крутиться вхолостую)
        wait_for = max(0.0, r.deadline - time.monotonic())
        await asyncio.sleep(wait_for + 0.05)

        async with lock:
            r = game.reveal_round
            if not r or r.finished:
                return
            # если дедлайн сдвинулся — продолжаем ждать
            if r.deadline is not None and time.monotonic() < r.deadline - 0.01:
                continue

            pid = current_player_id(game)
            if pid is None:
                return

            # автовыбор: добираем до лимита случайными
            result = apply_reveal(game, pid, card_ids=[], auto=True)

            await on_event(code, {
                "type": "reveal_timeout",
                "data": {
                    "player_id": pid,
                    "revealed": result.revealed,
                    "round_finished": result.round_finished,
                    "next_player_id": result.next_player_id,
                },
            })
            # дальше цикл сам увидит новый дедлайн (next) или finished