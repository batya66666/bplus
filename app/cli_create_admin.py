from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.db import async_session
from app.models.core import User
from app.models.enums import Role
from app.security.passwords import hash_password


async def main():
    email = os.environ.get("ADMIN_EMAIL", "admin@local")
    password = os.environ.get("ADMIN_PASSWORD", "admin12345")
    full_name = os.environ.get("ADMIN_NAME", "System Admin")

    async with async_session() as session:
        exists = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if exists:
            print("Admin already exists:", email)
            return

        u = User(
            email=email,
            full_name=full_name,
            role=Role.ADMIN.value,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(u)
        await session.commit()
        print("Created admin:", email, "password:", password)


if __name__ == "__main__":
    asyncio.run(main())
