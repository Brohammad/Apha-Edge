import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.collaboration.domain.entities import (
    CollabEvent,
    CollabSession,
    CollabSessionStatus,
)
from alphaedge.modules.collaboration.infrastructure.models import SQLAlchemyCollabRepository
from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.strategy.infrastructure.models import SQLAlchemyStrategyRepository
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.presentation.envelope import success_response

collaboration_router = APIRouter(prefix="/collaboration", tags=["Collaboration"])


class StartSessionRequest(BaseModel):
    strategy_id: str


async def _auth_ws(token: str | None) -> UUID | None:
    if not token:
        return None
    try:
        payload = TokenService.decode_access_token(token)
        sub = payload.get("sub")
        if sub and isinstance(sub, str):
            return UUID(sub)
    except Exception:
        return None
    return None


@collaboration_router.post("/sessions", status_code=201)
async def start_session(
    body: StartSessionRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    strategy_repo = SQLAlchemyStrategyRepository(session)
    strategy = await strategy_repo.get_by_id(UUID(body.strategy_id))
    if not strategy or strategy.deleted_at is not None:
        raise NotFoundError("Strategy", body.strategy_id)
    if strategy.user_id != user_id:
        raise AuthorizationError("You do not own this strategy")

    repo = SQLAlchemyCollabRepository(session)
    collab = CollabSession.create(UUID(body.strategy_id), user_id)
    saved = await repo.save_session(collab)
    return success_response({"session_id": str(saved.id), "strategy_id": body.strategy_id})


@collaboration_router.websocket("/ws/{session_id}")
async def collab_websocket(
    websocket: WebSocket,
    session_id: UUID,
    token: str | None = Query(default=None),
):
    user_id = await _auth_ws(token)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    async with async_session_factory() as session:
        repo = SQLAlchemyCollabRepository(session)
        collab = await repo.get_session(session_id)
        if not collab or collab.status != CollabSessionStatus.ACTIVE:
            await websocket.close(code=4404, reason="Session not found")
            return
        await repo.save_event(
            CollabEvent.create(session_id, user_id, "join", {"user_id": str(user_id)})
        )
        await session.commit()

    await websocket.accept()
    peers: set[WebSocket] = {websocket}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            event_type = str(msg.get("type", "edit"))
            payload = msg.get("payload") or {}

            async with async_session_factory() as session:
                repo = SQLAlchemyCollabRepository(session)
                await repo.save_event(CollabEvent.create(session_id, user_id, event_type, payload))
                await session.commit()

            broadcast = json.dumps(
                {"type": event_type, "user_id": str(user_id), "payload": payload}
            )
            for peer in list(peers):
                try:
                    await peer.send_text(broadcast)
                except Exception:
                    peers.discard(peer)
    except WebSocketDisconnect:
        async with async_session_factory() as session:
            repo = SQLAlchemyCollabRepository(session)
            await repo.save_event(
                CollabEvent.create(session_id, user_id, "leave", {"user_id": str(user_id)})
            )
            await session.commit()
