"""Platform kill switch and exposure dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass
class KillSwitchState:
    enabled: bool = False
    reason: str = ""
    triggered_at: datetime | None = None
    triggered_by: str | None = None


_STATE = KillSwitchState()


def get_kill_switch() -> KillSwitchState:
    return _STATE


def activate_kill_switch(reason: str, *, actor: str = "system") -> KillSwitchState:
    _STATE.enabled = True
    _STATE.reason = reason
    _STATE.triggered_at = datetime.now(UTC)
    _STATE.triggered_by = actor
    return _STATE


def deactivate_kill_switch() -> KillSwitchState:
    _STATE.enabled = False
    _STATE.reason = ""
    _STATE.triggered_at = None
    _STATE.triggered_by = None
    return _STATE


def exposure_summary(*, gross: Decimal, net: Decimal, equity: Decimal) -> dict[str, str]:
    return {
        "gross_exposure": str(gross),
        "net_exposure": str(net),
        "equity": str(equity),
        "gross_leverage": str(gross / equity) if equity > 0 else "0",
    }
