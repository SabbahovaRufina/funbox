import time, random
from .models import GameSession, RevealRound, Phase


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