from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.collaboration.domain.entities import (
    CollabEvent,
    CollabSession,
    CollabSessionStatus,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CollabSessionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "strategy_collab_sessions"

    strategy_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    host_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(default=CollabSessionStatus.ACTIVE.value)


class CollabEventModel(Base):
    __tablename__ = "strategy_collab_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SQLAlchemyCollabRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_session(self, session_entity: CollabSession) -> CollabSession:
        model = CollabSessionModel(
            id=session_entity.id,
            strategy_id=session_entity.strategy_id,
            host_user_id=session_entity.host_user_id,
            status=session_entity.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        return session_entity

    async def get_session(self, session_id: UUID) -> CollabSession | None:
        model = await self._session.get(CollabSessionModel, session_id)
        if not model:
            return None
        return CollabSession(
            id=model.id,
            strategy_id=model.strategy_id,
            host_user_id=model.host_user_id,
            status=CollabSessionStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save_event(self, event: CollabEvent) -> CollabEvent:
        model = CollabEventModel(
            id=event.id,
            session_id=event.session_id,
            user_id=event.user_id,
            event_type=event.event_type,
            payload=event.payload,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return event

    async def list_events(self, session_id: UUID, *, limit: int = 50) -> list[CollabEvent]:
        stmt = (
            select(CollabEventModel)
            .where(CollabEventModel.session_id == session_id)
            .order_by(CollabEventModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            CollabEvent(
                id=m.id,
                session_id=m.session_id,
                user_id=m.user_id,
                event_type=m.event_type,
                payload=m.payload,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]
