from fastapi import WebSocket


class ConnectionManager:
    """
    Хранит активные WebSocket, сгруппированные по коду лобби.
    Отдельно ведёт host_ws (общий экран), отдельно player_ws.
    """

    def __init__(self) -> None:
        # code -> WebSocket хоста
        self._hosts: dict[str, WebSocket] = {}
        # code -> {player_id: WebSocket}
        self._players: dict[str, dict[str, WebSocket]] = {}

    # --- host ---

    async def connect_host(self, code: str, ws: WebSocket) -> None:
        await ws.accept()
        self._hosts[code] = ws

    def disconnect_host(self, code: str) -> None:
        self._hosts.pop(code, None)

    # --- player ---

    async def connect_player(self, code: str, player_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._players.setdefault(code, {})[player_id] = ws

    def disconnect_player(self, code: str, player_id: str) -> None:
        bucket = self._players.get(code)
        if bucket:
            bucket.pop(player_id, None)
            if not bucket:
                self._players.pop(code, None)

    # --- broadcast ---

    async def send_to_host(self, code: str, message: dict) -> None:
        ws = self._hosts.get(code)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                # соединение могло умереть — не роняем всё из-за одного
                self._hosts.pop(code, None)

    async def send_to_player(self, code: str, player_id: str, message: dict) -> None:
        ws = (self._players.get(code) or {}).get(player_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_to_players(self, code: str, message: dict) -> None:
        for ws in list((self._players.get(code) or {}).values()):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_all(self, code: str, message: dict) -> None:
        await self.send_to_host(code, message)
        await self.broadcast_to_players(code, message)


manager = ConnectionManager()