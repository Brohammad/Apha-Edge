"""Strategy version diff and inline comments."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class VersionDiff:
    old_version_id: UUID
    new_version_id: UUID
    unified_diff: str


@dataclass
class InlineComment:
    id: UUID
    version_id: UUID
    author_id: UUID
    line: int
    body: str
    created_at: datetime = datetime.now(UTC)


def diff_versions(old_source: str, new_source: str, *, old_id: UUID, new_id: UUID) -> VersionDiff:
    diff = difflib.unified_diff(
        old_source.splitlines(),
        new_source.splitlines(),
        fromfile="old",
        tofile="new",
        lineterm="",
    )
    return VersionDiff(old_version_id=old_id, new_version_id=new_id, unified_diff="\n".join(diff))


def add_comment(version_id: UUID, author_id: UUID, line: int, body: str) -> InlineComment:
    return InlineComment(id=uuid4(), version_id=version_id, author_id=author_id, line=line, body=body)
