"""In-process collaboration room registry for WebSocket fan-out.

A single API process is the current demo/prod topology. Rooms are keyed by
session id so every peer in the same session receives broadcasts. Multi-process
deployments would need Redis pub/sub — not required until we scale API replicas.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import WebSocket


class CollabRoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def join(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(session_id, set()).add(websocket)

    async def leave(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._rooms.get(session_id)
            if not peers:
                return
            peers.discard(websocket)
            if not peers:
                del self._rooms[session_id]

    async def peer_count(self, session_id: UUID) -> int:
        async with self._lock:
            return len(self._rooms.get(session_id, ()))

    async def broadcast(self, session_id: UUID, message: str) -> None:
        async with self._lock:
            peers = list(self._rooms.get(session_id, ()))
        dead: list[WebSocket] = []
        for peer in peers:
            try:
                await peer.send_text(message)
            except Exception:
                dead.append(peer)
        if dead:
            async with self._lock:
                room = self._rooms.get(session_id)
                if not room:
                    return
                for peer in dead:
                    room.discard(peer)
                if not room:
                    del self._rooms[session_id]


collab_rooms = CollabRoomRegistry()
