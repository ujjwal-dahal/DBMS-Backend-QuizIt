from fastapi import WebSocket
from typing import Optional


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.room_users: dict[str, set[str]] = {}
        self.websocket_to_guest: dict[WebSocket, tuple[str, str]] = {}
        self.user_to_websocket: dict[int, WebSocket] = {}

    async def connect(
        self, websocket: WebSocket, room_code: str, guest_name: str, user_id: int
    ):
        await websocket.accept()

        self.active_connections.setdefault(room_code, []).append(websocket)
        self.room_users.setdefault(room_code, set()).add(guest_name)
        self.websocket_to_guest[websocket] = (guest_name, room_code)
        self.user_to_websocket[user_id] = websocket

        await self.broadcast_user_list(room_code)

    def disconnect(self, websocket: WebSocket):
        guest_info = self.websocket_to_guest.pop(websocket, None)
        if not guest_info:
            return

        guest_name, room_code = guest_info

        if room_code in self.active_connections:
            try:
                self.active_connections[room_code].remove(websocket)
            except ValueError:
                pass

        still_connected = any(
            name == guest_name and room == room_code
            for ws, (name, room) in self.websocket_to_guest.items()
        )
        if not still_connected:
            self.room_users.get(room_code, set()).discard(guest_name)

        to_remove = [
            uid for uid, ws in self.user_to_websocket.items() if ws == websocket
        ]
        for uid in to_remove:
            del self.user_to_websocket[uid]

    async def broadcast_user_list(self, room_code: str):
        users = list(self.room_users.get(room_code, []))
        await self.broadcast("user_list", room_code, data=users)

    async def broadcast(
        self, message_type: str, room_code: str, data: Optional[dict] = None
    ):
        payload = {"type": message_type, "data": data or {}}
        connections = self.active_connections.get(room_code, [])
        to_remove = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                # Remove dead connections
                to_remove.append(connection)
        for connection in to_remove:
            self.disconnect(connection)

    async def send_personal_dashboard(self, user_id: int, dashboard_data: list):
        websocket = self.user_to_websocket.get(user_id)
        if websocket:
            try:
                await websocket.send_json({"type": "dashboard", "data": dashboard_data})
            except Exception:
                self.disconnect(websocket)

    async def send_leaderboard(self, room_code: str, leaderboard_data: list):
        await self.broadcast("leaderboard", room_code, data=leaderboard_data)
