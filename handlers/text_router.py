"""Единая точка входа для текстовых сообщений — без конфликта create/FIO."""

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from handlers.creator import on_create_message
from handlers.taker import on_fio_message

CREATE_TEXT_STEPS = frozenset(
    {"test_name", "question_count", "question_text", "question_options"}
)


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    step = context.user_data.get("create_step")

    if step in CREATE_TEXT_STEPS:
        await on_create_message(update, context)
        return

    if context.user_data.get("awaiting_fio_test_id"):
        await on_fio_message(update, context)
        return


def build_text_handler() -> MessageHandler:
    return MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message)
