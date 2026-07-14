"""Leaderboards and author verification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeaderboardEntry:
    author_id: str
    author_name: str
    total_return: float
    verified: bool


def build_leaderboard(rows: list[dict], *, verified_only: bool = False) -> list[LeaderboardEntry]:
    entries = [
        LeaderboardEntry(
            author_id=r["author_id"],
            author_name=r["author_name"],
            total_return=float(r.get("total_return", 0)),
            verified=bool(r.get("verified", False)),
        )
        for r in rows
    ]
    if verified_only:
        entries = [e for e in entries if e.verified]
    return sorted(entries, key=lambda e: e.total_return, reverse=True)
