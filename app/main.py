from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

from .lobby import lobby_store
from .manager import manager
from .models import MIN_PLAYERS
from .game.generator import generate_game
from .game import reveal as reveal_mod
from .game.models import Phase

app = FastAPI(title="Jackbox Lite")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# реестр фоновых задач по коду лобби (чтобы не плодить дубли)
_reveal_tasks: dict[str, asyncio.Task] = {}
# локи на игру (по коду лобби) — защита от гонок reveal
_game_locks: dict[str, asyncio.Lock] = {}


def _game_lock(code: str) -> asyncio.Lock:
    return _game_locks.setdefault(code, asyncio.Lock())


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}


# --- HTTP ---

@app.post("/lobby")
async def create_lobby():
    """Хост создаёт лобби и получает код."""
    lobby = lobby_store.create()
    return {"code": lobby.code}


@app.get("/lobby/{code}/exists")
async def lobby_exists(code: str):
    """Проверяет, существует ли лобби с указанным кодом."""
    lobby = lobby_store.get(code)
    return {"exists": lobby is not None}


def _card_public(game, player_id: str, card_id: str) -> dict:
    st = game.players[player_id]
    for c in st.cards:
        if c.id == card_id:
            return {"id": c.id, "field": c.field,
                    "title": c.title, "description": c.description}
    return {"id": card_id}


async def _on_reveal_round_finished(code: str) -> None:
    lobby = lobby_store.get(code)
    if not lobby or not lobby.game:
        return
    game = lobby.game

    await manager.broadcast_all(code, {
        "type": "reveal_round_finished",
        "data": {
            "round_number": game.reveal_round.round_number,
            "rounds_done": game.reveal_rounds_done,
        },
    })

    # Дальше два варианта:
    #  A) авто-старт следующего круга (пока у кого-то есть нераскрытые карты)
    #  B) ждать команды хоста
    # Возьмём A с лимитом: пока есть у кого раскрывать — следующий круг.
    has_unrevealed = any(
        len(reveal_mod.revealed_for(game, pid)) < len(st.cards)
        for pid, st in game.players.items()
    )
    if has_unrevealed:
        rr = reveal_mod.start_reveal_round(game, duration=60)
        await manager.broadcast_all(code, {
            "type": "reveal_started",
            "data": {
                "round_number": rr.round_number,
                "reveal_limit": rr.reveal_limit,
                "order": rr.order,
                "current_player_id": reveal_mod.current_player_id(game),
                "deadline_in": rr.duration,
            },
        })
        _start_reveal_timeout_task(code)
    else:
        game.phase = Phase.VOTING
        await manager.broadcast_all(code, {
            "type": "phase_changed", "data": {"phase": "voting"},
        })


# --- WebSocket: хост ---

@app.websocket("/ws/host/{code}")
async def ws_host(websocket: WebSocket, code: str):
    """WebSocket хоста лобби: приём сообщений и очистка при отключении."""
    code = code.upper()
    lobby = lobby_store.get(code)
    if not lobby:
        await websocket.close(code=4004)
        return

    lobby.host_connected = True
    await manager.connect_host(code, websocket)

    # сообщаем хосту актуальный список игроков
    await manager.send_to_host(code, {
        "type": "players_update",
        "data": [p.to_dict() for p in lobby.all_players()],
    })

    try:
        while True:
            msg = await websocket.receive_json()
            await handle_host_message(code, msg)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_host(code)
        lobby = lobby_store.get(code)
        if lobby:
            lobby.host_connected = False
        lobby_store.delete_if_empty(code) # у меня еще где-то есть очистка лобби?

        if not lobby_store.get(code):
            t = _reveal_tasks.pop(code, None)
            if t and not t.done():
                t.cancel()
            _game_locks.pop(code, None)


async def handle_host_message(code: str, msg: dict) -> None:
    """Обрабатывает сообщение от хоста лобби по его типу."""
    lobby = lobby_store.get(code)
    if not lobby:
        return

    mtype = msg.get("type")

    if mtype == "start_game":
        if lobby.started:
            await manager.send_to_host(code, {"type": "error", "data": {"reason": "already_started"}})
            return
        if not lobby.can_start():
            await manager.send_to_host(code, {
                "type": "error",
                "data": {
                    "reason": "not_enough_players",
                    "need": MIN_PLAYERS,
                    "have": lobby.count_players(),
                },
            })
            return

        lobby.started = True
        lobby.game = generate_game(lobby)
        # 1) хосту — катастрофа
        await manager.send_to_host(code, {
            "type": "catastrophe",
            "data": {
                "title": lobby.game.catastrophe.title,
                "description": lobby.game.catastrophe.description,
                "capacity": lobby.game.capacity,
                "players_count": lobby.count_players(),
            },
        })

        # 2) каждому игроку — его карты
        for player_id, state in lobby.game.players.items():
            await manager.send_to_player(code, player_id, {
                "type": "your_cards",
                "data": {
                    "role_tag": state.role_tag,
                    "gender": state.gender,
                    "cards": [
                        {"id": c.id, "field": c.field, "title": c.title,
                         "description": c.description}
                        for c in state.cards
                    ],
                },
            })

        # 3) всем — сигнал, что игра началась
        await manager.broadcast_all(code, {"type": "game_started", "data": {}})

        # 4) стартуем первый круг reveal
        rr = reveal_mod.start_reveal_round(lobby.game, duration=60)
        await manager.broadcast_all(code, {
            "type": "reveal_started",
            "data": {
                "round_number": rr.round_number,
                "reveal_limit": rr.reveal_limit,
                "order": rr.order,
                "current_player_id": reveal_mod.current_player_id(lobby.game),
                "deadline_in": rr.duration,
            },
        })
        _start_reveal_timeout_task(code)

    elif mtype == "ping":
        await manager.send_to_host(code, {"type": "pong"})


# --- WebSocket: игрок ---

@app.websocket("/ws/player/{code}")
async def ws_player(websocket: WebSocket, code: str, name: str = "Player"):
    """WebSocket игрока: вход в лобби, приём сообщений, очистка при выходе."""
    code = code.upper()
    lobby = lobby_store.get(code)
    name = name.strip()
    if not lobby:
        await websocket.close(code=4004)
        return

    if not name:
        await websocket.close(code=4001)   # пустое имя
        return

    if lobby.is_name_too_long(name):
        await websocket.close(code=4005)  # слишком длинное имя
        return

    if lobby.is_name_taken(name):
        await websocket.close(code=4002)  # имя занято
        return

    if not lobby.can_accept_players():
        await websocket.close(4003)
        return

    player = lobby.add_player(name=name)
    await manager.connect_player(code, player.id, websocket)

    # игроку — его id
    await manager.send_to_player(code, player.id, {
        "type": "welcome",
        "data": {"player_id": player.id, "name": player.name},
    })

    # хосту — обновлённый список
    await manager.send_to_host(code, {
        "type": "players_update",
        "data": [p.to_dict() for p in lobby.all_players()],
    })

    try:
        while True:
            msg = await websocket.receive_json()
            await handle_player_message(code, player.id, msg)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_player(code, player.id)
        lobby = lobby_store.get(code)          # свежая ссылка
        if lobby:
            lobby.remove_player(player.id)
            await manager.send_to_host(code, {
                "type": "players_update",
                "data": [p.to_dict() for p in lobby.all_players()],
            })
        lobby_store.delete_if_empty(code)

        if not lobby_store.get(code):
            t = _reveal_tasks.pop(code, None)
            if t and not t.done():
                t.cancel()
            _game_locks.pop(code, None)


async def handle_player_message(code: str, player_id: str, msg: dict) -> None:
    mtype = msg.get("type")

    if mtype == "ping":
        await manager.send_to_player(code, player_id, {"type": "pong"})
        return

    if mtype == "reveal_cards":
        lobby = lobby_store.get(code)
        if not lobby or not lobby.game:
            return
        game = lobby.game
        if game.phase != Phase.REVEAL:
            await manager.send_to_player(code, player_id, {
                "type": "error", "data": {"reason": "wrong_phase"},
            })
            return

        card_ids = msg.get("data", {}).get("card_ids", [])
        if not isinstance(card_ids, list):
            card_ids = []

        async with _game_lock(code):
            result = reveal_mod.apply_reveal(game, player_id, card_ids)

        if not result.ok:
            await manager.send_to_player(code, player_id, {
                "type": "error", "data": {"reason": result.reason},
            })
            return

        # подтверждение игроку
        await manager.send_to_player(code, player_id, {
            "type": "reveal_ack",
            "data": {"revealed": result.revealed},
        })

        # всем — что раскрыто (хосту нужно для экрана)
        await manager.broadcast_all(code, {
            "type": "cards_revealed",
            "data": {
                "player_id": player_id,
                "cards": [
                    _card_public(game, player_id, cid)
                    for cid in result.revealed
                ],
            },
        })

        if result.round_finished:
            await _on_reveal_round_finished(code)
        elif result.next_player_id:
            await manager.broadcast_all(code, {
                "type": "reveal_turn",
                "data": {
                    "current_player_id": result.next_player_id,
                    "deadline_in": game.reveal_round.duration
                    if game.reveal_round else 0,
                },
            })
            # таймаут-таск сам подхватит новый дедлайн (цикл в run_reveal_timeout)


def _start_reveal_timeout_task(code: str) -> None:
    old = _reveal_tasks.pop(code, None)
    if old and not old.done():
        old.cancel()

    async def on_event(c: str, evt: dict) -> None:
        await manager.broadcast_all(c, evt)
        # если ход перешёл — сообщим всем, чей ход
        if "next_player_id" in evt["data"] and evt["data"]["next_player_id"]:
            lobby = lobby_store.get(c)
            if lobby and lobby.game:
                await manager.broadcast_all(c, {
                    "type": "reveal_turn",
                    "data": {
                        "current_player_id": evt["data"]["next_player_id"],
                        "deadline_in": lobby.game.reveal_round.duration
                        if lobby.game.reveal_round else 0,
                    },
                })

    lobby = lobby_store.get(code)
    if not lobby or not lobby.game:
        return

    task = asyncio.create_task(
        reveal_mod.run_reveal_timeout(
            lobby.game, code, on_event, _game_lock(code)
        )
    )
    _reveal_tasks[code] = task