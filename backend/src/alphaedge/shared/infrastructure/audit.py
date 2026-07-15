"""Append-only audit trail for security-sensitive mutations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.shared.infrastructure.audit_models import AuditLogModel


async def record_audit(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    changes: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    ip_address: str | None = None
    request_id: str | None = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if settings_trust_proxy(request):
            forwarded = request.headers.get("X-Forwarded-For")
            ip_address = forwarded.split(",")[0].strip() if forwarded else None
        if not ip_address:
            client = request.scope.get("client")
            ip_address = client[0] if client else None

    session.add(
        AuditLogModel(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            request_id=request_id,
        )
    )


def settings_trust_proxy(request: Request) -> bool:
    from alphaedge.config import settings

    return settings.trust_proxy_headers
