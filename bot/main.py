from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine

import database
from handlers_admin import admin_router
from handlers_user import user_router
from models import Base


async def create_tables(db_engine: AsyncEngine) -> None:
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main() -> None:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    owner_id = os.getenv("OWNER_ID", "0")

    if not token or not admin_chat_id:
        raise RuntimeError("BOT_TOKEN and ADMIN_CHAT_ID are required in .env")

    database.init_db("sqlite+aiosqlite:///support_bot.sqlite3")
    await create_tables(database.engine)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp["admin_chat_id"] = int(admin_chat_id)
    dp["owner_id"] = int(owner_id)

    dp.include_router(admin_router)
    dp.include_router(user_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
