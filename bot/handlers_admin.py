from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from database import get_session
from models import Ticket, User

admin_router = Router()


async def get_ticket_by_thread(thread_id: int | None) -> Ticket | None:
    if thread_id is None:
        return None
    async with get_session() as session:
        return await session.scalar(select(Ticket).where(Ticket.thread_id == thread_id))


@admin_router.message(Command("stats"))
async def show_stats(message: Message, admin_chat_id: int, owner_id: int) -> None:
    if message.chat.id != admin_chat_id or message.from_user.id != owner_id:
        return

    async with get_session() as session:
        users_count = await session.scalar(select(func.count()).select_from(User))
        open_tickets = await session.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status == "open")
        )
        closed_tickets = await session.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status == "closed")
        )
        blocked_users = await session.scalar(
            select(func.count()).select_from(User).where(User.blocked.is_(True))
        )

    await message.answer(
        "Статистика:\n"
        f"- Пользователей: {users_count}\n"
        f"- Открытых тикетов: {open_tickets}\n"
        f"- Закрытых тикетов: {closed_tickets}\n"
        f"- Заблокированных: {blocked_users}"
    )


@admin_router.message(Command("ban"))
async def ban_user(message: Message, admin_chat_id: int) -> None:
    if message.chat.id != admin_chat_id:
        return
    if not message.reply_to_message:
        await message.answer("Используйте /ban в reply на сообщение пользователя в теме тикета.")
        return

    ticket = await get_ticket_by_thread(message.message_thread_id)
    if ticket is None:
        await message.answer("Не удалось определить тикет.")
        return

    async with get_session() as session:
        user = await session.get(User, ticket.user_id)
        if user is None:
            await message.answer("Пользователь не найден.")
            return
        user.blocked = True
        await session.commit()

    await message.answer("Пользователь заблокирован.")


@admin_router.callback_query(F.data.startswith("close_ticket:"))
async def close_ticket(callback: CallbackQuery, admin_chat_id: int) -> None:
    if callback.message.chat.id != admin_chat_id:
        await callback.answer()
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    async with get_session() as session:
        ticket = await session.get(Ticket, ticket_id)
        if ticket is None:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        ticket.status = "closed"
        await session.commit()

    await callback.message.answer(f"Тикет #{ticket_id} закрыт.")
    await callback.answer("Закрыто")


@admin_router.callback_query(F.data.startswith("transfer_ticket:"))
async def transfer_ticket(callback: CallbackQuery, admin_chat_id: int) -> None:
    if callback.message.chat.id != admin_chat_id:
        await callback.answer()
        return

    await callback.message.answer("Тикет передан другому администратору")
    await callback.answer("Передано")


@admin_router.message(F.chat.type.in_({"supergroup", "group"}), F.reply_to_message, F.text)
async def reply_to_user(message: Message, admin_chat_id: int, bot) -> None:
    if message.chat.id != admin_chat_id:
        return
    if message.text.startswith("/"):
        return

    ticket = await get_ticket_by_thread(message.message_thread_id)
    if ticket is None or ticket.status != "open":
        return

    async with get_session() as session:
        user = await session.get(User, ticket.user_id)
        if user is None:
            return

    await bot.send_message(chat_id=user.user_id, text=message.text)
