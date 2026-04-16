#!/usr/bin/env python3
"""
seed_admin.py  —  Run this ONCE to create the first admin user.

Usage (from the backend/ directory):
    python seed_admin.py
    python seed_admin.py --username admin --email admin@example.com --password secret

The script reads DATABASE_URL from .env / environment, creates the tables
if they don't exist, then inserts the admin user.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Make sure local packages resolve
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from database.connection import AsyncSessionLocal, create_tables
from models.user import User
from services.auth_service import hash_password


async def seed(username: str, email: str, password: str) -> None:
    await create_tables()

    async with AsyncSessionLocal() as db:
        # Check duplicate
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"⚠️  User '{username}' already exists — nothing changed.")
            return

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅  Admin user '{username}' created successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed initial admin user")
    parser.add_argument("--username", default="admin",          help="Admin username (default: admin)")
    parser.add_argument("--email",    default="admin@admin.com", help="Admin email")
    parser.add_argument("--password", default=None,             help="Admin password (prompted if omitted)")
    args = parser.parse_args()

    if args.password is None:
        import getpass
        args.password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if args.password != confirm:
            print("❌  Passwords do not match.")
            sys.exit(1)

    if len(args.password) < 6:
        print("❌  Password must be at least 6 characters.")
        sys.exit(1)

    asyncio.run(seed(args.username, args.email, args.password))


if __name__ == "__main__":
    main()
