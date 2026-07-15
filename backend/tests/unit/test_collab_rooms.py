"""Unit tests for collaboration room registry fan-out."""

from uuid import uuid4

import pytest

from alphaedge.modules.collaboration.infrastructure.rooms import CollabRoomRegistry


class _FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.fail = False

    async def send_text(self, message: str) -> None:
        if self.fail:
            raise RuntimeError("closed")
        self.messages.append(message)


@pytest.mark.asyncio
async def test_broadcast_reaches_all_peers_in_room() -> None:
    rooms = CollabRoomRegistry()
    session_id = uuid4()
    a = _FakeWebSocket()
    b = _FakeWebSocket()

    await rooms.join(session_id, a)  # type: ignore[arg-type]
    await rooms.join(session_id, b)  # type: ignore[arg-type]
    assert await rooms.peer_count(session_id) == 2

    await rooms.broadcast(session_id, '{"type":"edit"}')
    assert a.messages == ['{"type":"edit"}']
    assert b.messages == ['{"type":"edit"}']


@pytest.mark.asyncio
async def test_leave_removes_peer_and_prunes_empty_room() -> None:
    rooms = CollabRoomRegistry()
    session_id = uuid4()
    a = _FakeWebSocket()

    await rooms.join(session_id, a)  # type: ignore[arg-type]
    await rooms.leave(session_id, a)  # type: ignore[arg-type]
    assert await rooms.peer_count(session_id) == 0


@pytest.mark.asyncio
async def test_broadcast_drops_dead_peers() -> None:
    rooms = CollabRoomRegistry()
    session_id = uuid4()
    live = _FakeWebSocket()
    dead = _FakeWebSocket()
    dead.fail = True

    await rooms.join(session_id, live)  # type: ignore[arg-type]
    await rooms.join(session_id, dead)  # type: ignore[arg-type]
    await rooms.broadcast(session_id, "ping")

    assert live.messages == ["ping"]
    assert await rooms.peer_count(session_id) == 1
