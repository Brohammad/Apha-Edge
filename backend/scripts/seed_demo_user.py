"""Create a pre-configured demo account for public demos and portfolio screenshots."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from alphaedge.modules.identity.application.commands import RegisterUserCommand
from alphaedge.modules.identity.application.handlers import RegisterUserHandler
from alphaedge.modules.identity.infrastructure.models import (
    RoleModel,
    SQLAlchemyRoleRepository,
    SQLAlchemyUserRepository,
    UserModel,
)
from alphaedge.shared.infrastructure.database import async_session_factory

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "DemoAlphaEdge1!"
DEMO_DISPLAY_NAME = "Demo User"


async def seed_demo_user() -> None:
    async with async_session_factory() as session:
        existing = await session.execute(select(UserModel).where(UserModel.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return

        user_repo = SQLAlchemyUserRepository(session)
        role_repo = SQLAlchemyRoleRepository(session)
        handler = RegisterUserHandler(user_repo, role_repo)
        await handler.handle(
            RegisterUserCommand(
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                display_name=DEMO_DISPLAY_NAME,
            )
        )
        # Demo account must work when APP_ENV=production (public HTTPS deploy).
        from sqlalchemy import update

        await session.execute(
            update(UserModel)
            .where(UserModel.email == DEMO_EMAIL)
            .values(email_verified=True, is_active=True)
        )
        await session.commit()
        print(f"Demo user created: {DEMO_EMAIL} (password in docs/DEMO_DEPLOY.md)")


async def main() -> None:
    async with async_session_factory() as session:
        roles = await session.execute(select(RoleModel))
        if roles.first() is None:
            raise RuntimeError("Run seed_data first — no roles in database")
    await seed_demo_user()


if __name__ == "__main__":
    asyncio.run(main())
