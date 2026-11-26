from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .lobby import lobby_store
from .manager import manager
from .models import MIN_PLAYERS
from .game.generator import generate_game
from .game.models import CARD_FIELDS

app = FastAPI(title="Jackbox Lite")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


async def handle_player_message(code: str, player_id: str, msg: dict) -> None:
    """Обрабатывает сообщение от игрока по его типу."""
    mtype = msg.get("type")
    if mtype == "ping":
        await manager.send_to_player(code, player_id, {"type": "pong"})



async def handle_reveal_card(code: str, player_id: str, data: dict) -> None:
    lobby = lobby_store.get(code)
    if not lobby or not lobby.game:
        return
    game = lobby.game

    if game.phase != Phase.REVEAL or not game.reveal_round:
        await manager.send_to_player(code, player_id, {
            "type": "error", "data": {"reason": "reveal_not_allowed_phase"},
        })
        return

    r = game.reveal_round
    if r.finished or r.current_player_id != player_id:
        await manager.send_to_player(code, player_id, {
            "type": "error", "data": {"reason": "not_your_turn"},
        })
        return

    state = game.players[player_id]
    card_id = data.get("card_id")
    card = next((c for c in state.cards if c.id == card_id), None)
    if not card:
        await manager.send_to_player(code, player_id, {
            "type": "error", "data": {"reason": "card_not_owned"},
        })
        return

    if card_id in state.revealed_ids:
        return  # уже раскрыта, молча игнор

    # лимит на ЭТОТ ход
    revealed_this_turn = getattr(state, "_revealed_this_turn", set())
    if len(revealed_this_turn) >= r.reveal_limit:
        await manager.send_to_player(code, player_id, {
            "type": "error",
            "data": {"reason": "turn_reveal_limit", "limit": r.reveal_limit},
        })
        return

    state.revealed_ids.append(card_id)
    revealed_this_turn.add(card_id)
    state._revealed_this_turn = revealed_this_turn  # см. ниже про хранение
    game.revealed.setdefault(player_id, []).append(card_id)

    # подтверждение игроку
    await manager.send_to_player(code, player_id, {
        "type": "card_revealed",
        "data": {
            "card_id": card_id,
            "revealed_count": len(state.revealed_ids),
            "turn_limit": r.reveal_limit,
            "turn_revealed": len(revealed_this_turn),
        },
    })

    # всем — публичное событие
    await manager.broadcast_all(code, {
        "type": "player_revealed_card",
        "data": {
            "player_id": player_id,
            "player_name": lobby.players[player_id].name,
            "card": {
                "id": card.id, "field": card.field,
                "title": card.title, "description": card.description,
            },
        },
    })

