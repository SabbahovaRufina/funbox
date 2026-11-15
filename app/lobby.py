import random
import string
from typing import Optional
from models import Lobby


class LobbyStore:

    def __init__(self) -> None:
        self._lobbies: dict[str, Lobby] = {}

    def _generate_code(self) -> str:
        while True:
            code = "".join(random.choices(string.ascii_uppercase, k=4))
            if code not in self._lobbies:
                return code

    def create(self) -> Lobby:
        code = self._generate_code()
        lobby = Lobby(code=code)
        self._lobbies[code] = lobby
        return lobby

    def get(self, code: str) -> Optional[Lobby]:
        return self._lobbies.get(code.upper())

    def delete_if_empty(self, code: str) -> None:
        lobby = self._lobbies.get(code)
        if lobby and lobby.is_empty():
            del self._lobbies[code]


# Глобальный экземпляр. Пока один процесс — этого достаточно.
lobby_store = LobbyStore()