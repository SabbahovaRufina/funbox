from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from lobby import lobby_store
from manager import manager
from models import MIN_PLAYERS

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
    lobby = lobby_store.get(code)
    return {"exists": lobby is not None}


# --- WebSocket: хост ---

@app.websocket("/ws/host/{code}")
async def ws_host(websocket: WebSocket, code: str):
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
        lobby_store.delete_if_empty(code)


async def handle_host_message(code: str, msg: dict) -> None:
    lobby = lobby_store.get(code)
    if not lobby:
        return

    mtype = msg.get("type")

    if mtype == "start_game":
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
        await manager.broadcast_all(code, {
            "type": "game_started",
            "data": {},
        })

    elif mtype == "ping":
        await manager.send_to_host(code, {"type": "pong"})


# --- WebSocket: игрок ---

@app.websocket("/ws/player/{code}")
async def ws_player(websocket: WebSocket, code: str, name: str = "Player"):
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

    if lobby.has_name(name):
        await websocket.close(code=4002)   # имя занято
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
        manager.disconnect_player(code, player.id)
        lobby = lobby_store.get(code)
        if lobby:
            lobby.remove_player(player.id)
            await manager.send_to_host(code, {
                "type": "players_update",
                "data": [p.to_dict() for p in lobby.all_players()],
            })
        lobby_store.delete_if_empty(code)


async def handle_player_message(code: str, player_id: str, msg: dict) -> None:
    mtype = msg.get("type")
    if mtype == "ping":
        await manager.send_to_player(code, player_id, {"type": "pong"})
    # Здесь позже: ответы игрока в игре