from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy import Select, desc, select

from database import get_session
from keyboards import ticket_actions_keyboard
from models import Ticket, User

user_router = Router()


async def get_or_create_user(external_user_id: int) -> User:
    async with get_session() as session:
        user = await session.scalar(select(User).where(User.user_id == external_user_id))
        if user is None:
            user = User(user_id=external_user_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def get_last_ticket(user_id: int) -> Ticket | None:
    async with get_session() as session:
        stmt: Select[tuple[Ticket]] = (
            select(Ticket).where(Ticket.user_id == user_id).order_by(desc(Ticket.id)).limit(1)
        )
        return await session.scalar(stmt)


async def create_ticket(user_id: int, thread_id: int) -> Ticket:
    async with get_session() as session:
        ticket = Ticket(user_id=user_id, status="open", thread_id=thread_id)
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket


async def reopen_ticket(ticket_id: int) -> None:
    async with get_session() as session:
        ticket = await session.get(Ticket, ticket_id)
        if ticket is None:
            return
        ticket.status = "open"
        await session.commit()


@user_router.message(F.chat.type == "private", F.text)
async def handle_user_text(message: Message, bot: Bot, admin_chat_id: int) -> None:
    user = await get_or_create_user(message.from_user.id)

    if user.blocked:
        await message.answer("Вы заблокированы и не можете отправлять сообщения в поддержку.")
        return

    ticket = await get_last_ticket(user.id)

    if ticket is None:
        topic = await bot.create_forum_topic(
            chat_id=admin_chat_id,
            name=f"#1 | Аноним",
        )
        ticket = await create_ticket(user.id, topic.message_thread_id)
        await bot.send_message(
            chat_id=admin_chat_id,
            message_thread_id=ticket.thread_id,
            text=(
                f"Создан новый тикет #{ticket.id}.\n"
                "Пользователь анонимен. Отвечайте reply на сообщения в этой теме."
            ),
        )
    elif ticket.status == "closed":
        await reopen_ticket(ticket.id)
        await bot.send_message(
            chat_id=admin_chat_id,
            message_thread_id=ticket.thread_id,
            text=f"Тикет #{ticket.id} переоткрыт пользователем.",
        )

    # Fix topic title to reflect real ticket number
    await bot.edit_forum_topic(
        chat_id=admin_chat_id,
        message_thread_id=ticket.thread_id,
        name=f"#{ticket.id} | Аноним",
    )

    await bot.send_message(
        chat_id=admin_chat_id,
        message_thread_id=ticket.thread_id,
        text=message.text,
        reply_markup=ticket_actions_keyboard(ticket.id),
    )

    await message.answer("Ваше сообщение отправлено в поддержку.")


@user_router.message(F.chat.type == "private", ~F.text)
async def handle_unsupported_content(message: Message) -> None:
    await message.answer("Поддерживается только текст.")
