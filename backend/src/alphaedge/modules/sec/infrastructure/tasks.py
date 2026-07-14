"""Insider activity monitoring Celery tasks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from alphaedge.modules.sec.domain.form4_parser import Form4Parser
from alphaedge.shared.infrastructure.celery_app import celery_app


@dataclass(frozen=True)
class InsiderSignal:
    issuer: str
    owner: str
    action: str
    shares: Decimal
    signal_strength: str


def generate_insider_signals(xml_filings: list[str]) -> list[InsiderSignal]:
    signals: list[InsiderSignal] = []
    for xml in xml_filings:
        for tx in Form4Parser.parse(xml):
            if tx.acquired_disposed == "D" and tx.shares > Decimal("10000"):
                strength = "high"
            elif tx.shares > Decimal("1000"):
                strength = "medium"
            else:
                strength = "low"
            signals.append(
                InsiderSignal(
                    issuer=tx.issuer,
                    owner=tx.reporting_owner,
                    action="sell" if tx.acquired_disposed == "D" else "buy",
                    shares=tx.shares,
                    signal_strength=strength,
                )
            )
    return signals


@celery_app.task(name="sec.monitor_insider_activity")
def monitor_insider_activity(cik: str) -> dict:
    """Poll EDGAR submissions and emit insider signals (skeleton)."""
    # Live polling requires async bridge; returns structure for integration tests.
    return {
        "cik": cik,
        "signals": [],
        "status": "scheduled",
    }
