"""Admin kill-switch control plane."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from alphaedge.dependencies import AuthContext, require_admin
from alphaedge.modules.risk.domain.kill_switch import (
    activate_kill_switch,
    deactivate_kill_switch,
    get_kill_switch,
)
from alphaedge.shared.infrastructure.audit import record_audit
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.presentation.envelope import success_response

kill_switch_router = APIRouter(prefix="/admin/kill-switch", tags=["Risk", "Admin"])


class ActivateKillSwitchRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _state_payload() -> dict:
    state = get_kill_switch()
    return {
        "enabled": state.enabled,
        "reason": state.reason,
        "triggered_at": state.triggered_at.isoformat() if state.triggered_at else None,
        "triggered_by": state.triggered_by,
    }


@kill_switch_router.get("")
async def get_status(
    request: Request,
    _auth: AuthContext = Depends(require_admin),
):
    return success_response(
        _state_payload(),
        request_id=getattr(request.state, "request_id", ""),
    )


@kill_switch_router.post("/activate")
async def activate(
    body: ActivateKillSwitchRequest,
    request: Request,
    auth: AuthContext = Depends(require_admin),
):
    actor = str(auth.user_id)
    activate_kill_switch(body.reason, actor=actor)
    async with async_session_factory() as session:
        await record_audit(
            session,
            user_id=auth.user_id,
            action="kill_switch.activate",
            resource_type="kill_switch",
            changes={"reason": body.reason},
            request=request,
        )
        await session.commit()
    return success_response(
        _state_payload(),
        request_id=getattr(request.state, "request_id", ""),
    )


@kill_switch_router.post("/deactivate")
async def deactivate(
    request: Request,
    auth: AuthContext = Depends(require_admin),
):
    deactivate_kill_switch(actor=str(auth.user_id))
    async with async_session_factory() as session:
        await record_audit(
            session,
            user_id=auth.user_id,
            action="kill_switch.deactivate",
            resource_type="kill_switch",
            request=request,
        )
        await session.commit()
    return success_response(
        _state_payload(),
        request_id=getattr(request.state, "request_id", ""),
    )
