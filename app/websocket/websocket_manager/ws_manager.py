from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.room_users: dict[str, set[str]] = {}
        self.websocket_to_guest: dict[WebSocket, tuple[str, str]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, guest_name: str):
        await websocket.accept()

        # Initialize room if not exists
        self.active_connections.setdefault(room_code, [])
        self.active_connections[room_code].append(websocket)

        self.room_users.setdefault(room_code, set())
        self.room_users[room_code].add(guest_name)

        # Save mapping
        self.websocket_to_guest[websocket] = (guest_name, room_code)

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
                pass  # websocket not found in list

        # Remove guest_name **only if** no other sockets with same guest_name in this room
        still_connected = [
            ws
            for ws, (name, room) in self.websocket_to_guest.items()
            if name == guest_name and room == room_code
        ]
        if not still_connected:
            self.room_users.get(room_code, set()).discard(guest_name)

    async def broadcast_user_list(self, room_code: str):
        users = list(self.room_users.get(room_code, []))
        await self.broadcast("user_list", room_code, data=users)

    async def broadcast(self, message_type: str, room_code: str, data=None):
        payload = {"type": message_type, "data": data or {}}
        for connection in self.active_connections.get(room_code, []):
            try:
                await connection.send_json(payload)
            except Exception:
                pass  # optionally log or remove broken socket
