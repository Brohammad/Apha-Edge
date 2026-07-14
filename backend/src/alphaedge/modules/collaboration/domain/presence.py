"""Cursor presence and user avatars for collaboration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class CursorPresence:
    user_id: UUID
    display_name: str
    avatar_url: str
    x: float
    y: float
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_PRESENCE: dict[str, list[CursorPresence]] = {}


def update_presence(room_id: str, cursor: CursorPresence) -> list[CursorPresence]:
    room = _PRESENCE.setdefault(room_id, [])
    room = [c for c in room if c.user_id != cursor.user_id]
    room.append(cursor)
    _PRESENCE[room_id] = room[-20:]
    return _PRESENCE[room_id]
