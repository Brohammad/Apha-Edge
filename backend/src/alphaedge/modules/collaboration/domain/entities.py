from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from alphaedge.shared.domain.exceptions import ValidationError


class CollabSessionStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class CollabSession:
    id: UUID
    strategy_id: UUID
    host_user_id: UUID
    status: CollabSessionStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(strategy_id: UUID, host_user_id: UUID) -> "CollabSession":
        return CollabSession(
            id=uuid4(),
            strategy_id=strategy_id,
            host_user_id=host_user_id,
            status=CollabSessionStatus.ACTIVE,
        )


@dataclass
class CollabEvent:
    id: UUID
    session_id: UUID
    user_id: UUID
    event_type: str
    payload: dict[str, object]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        session_id: UUID,
        user_id: UUID,
        event_type: str,
        payload: dict[str, object],
    ) -> "CollabEvent":
        if event_type not in ("cursor", "edit", "join", "leave"):
            raise ValidationError(f"Unsupported collab event type: {event_type}")
        return CollabEvent(
            id=uuid4(),
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            payload=payload,
        )
