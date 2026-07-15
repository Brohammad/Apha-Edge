import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.collaboration.domain.entities import (
    CollabEvent,
    CollabSession,
    CollabSessionStatus,
)
from alphaedge.modules.collaboration.infrastructure.models import SQLAlchemyCollabRepository
from alphaedge.modules.collaboration.infrastructure.rooms import collab_rooms
from alphaedge.modules.strategy.infrastructure.models import SQLAlchemyStrategyRepository
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.presentation.envelope import success_response
from alphaedge.shared.presentation.ws_auth import authenticate_websocket

collaboration_router = APIRouter(prefix="/collaboration", tags=["Collaboration"])


class StartSessionRequest(BaseModel):
    strategy_id: str


async def _auth_ws(websocket: WebSocket) -> UUID | None:
    return await authenticate_websocket(websocket)


async def _user_may_join_session(session_id: UUID, user_id: UUID) -> CollabSession:
    async with async_session_factory() as session:
        repo = SQLAlchemyCollabRepository(session)
        collab = await repo.get_session(session_id)
        if not collab or collab.status != CollabSessionStatus.ACTIVE:
            raise NotFoundError("CollabSession", str(session_id))

        if collab.host_user_id == user_id:
            return collab

        strategy_repo = SQLAlchemyStrategyRepository(session)
        strategy = await strategy_repo.get_by_id(collab.strategy_id)
        if strategy and strategy.user_id == user_id:
            return collab

        raise AuthorizationError("You are not authorized to join this collaboration session")


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
):
    user_id = await _auth_ws(websocket)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    try:
        await _user_may_join_session(session_id, user_id)
    except (NotFoundError, AuthorizationError):
        await websocket.close(code=4403, reason="Forbidden")
        return

    async with async_session_factory() as session:
        repo = SQLAlchemyCollabRepository(session)
        await repo.save_event(
            CollabEvent.create(session_id, user_id, "join", {"user_id": str(user_id)})
        )
        await session.commit()

    subprotocol = websocket.headers.get("sec-websocket-protocol")
    await websocket.accept(subprotocol=subprotocol)
    await collab_rooms.join(session_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            event_type = str(msg.get("type", "edit"))
            if event_type not in ("cursor", "edit", "join", "leave"):
                await websocket.send_json({"type": "error", "message": "Unsupported event type"})
                continue
            payload = msg.get("payload") or {}
            if not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "message": "Payload must be an object"})
                continue

            async with async_session_factory() as session:
                repo = SQLAlchemyCollabRepository(session)
                await repo.save_event(CollabEvent.create(session_id, user_id, event_type, payload))
                await session.commit()

            broadcast = json.dumps(
                {"type": event_type, "user_id": str(user_id), "payload": payload}
            )
            await collab_rooms.broadcast(session_id, broadcast)
    except WebSocketDisconnect:
        async with async_session_factory() as session:
            repo = SQLAlchemyCollabRepository(session)
            await repo.save_event(
                CollabEvent.create(session_id, user_id, "leave", {"user_id": str(user_id)})
            )
            await session.commit()
    finally:
        await collab_rooms.leave(session_id, websocket)
