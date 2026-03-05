from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def ticket_actions_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Закрыть тикет", callback_data=f"close_ticket:{ticket_id}"
                ),
                InlineKeyboardButton(
                    text="Передать другому админу",
                    callback_data=f"transfer_ticket:{ticket_id}",
                ),
            ]
        ]
    )
