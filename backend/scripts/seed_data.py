"""Seed default roles on startup."""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from alphaedge.modules.identity.domain.entities import RoleName
from alphaedge.modules.identity.infrastructure.models import RoleModel
from alphaedge.shared.infrastructure.database import async_session_factory


DEFAULT_ROLES = [
    (RoleName.ADMIN, "Full platform access"),
    (RoleName.TRADER, "Create strategies, run backtests, manage portfolios"),
    (RoleName.VIEWER, "Read-only access"),
    (RoleName.API_SERVICE, "Programmatic API access"),
]


async def seed_roles() -> None:
    async with async_session_factory() as session:
        for role_name, description in DEFAULT_ROLES:
            existing = await session.execute(
                select(RoleModel).where(RoleModel.name == role_name.value)
            )
            if existing.scalar_one_or_none() is None:
                session.add(
                    RoleModel(id=uuid4(), name=role_name.value, description=description)
                )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_roles())
