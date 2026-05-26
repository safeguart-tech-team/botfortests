from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from config import RESULTS_DELAY_OPTIONS, TIME_OPTIONS
from handlers.taker import start_test_from_link
from locales import t
from handlers.results_cmd import finish_test_and_send_results
from utils import test_deep_link

(
    LANG,
    TEST_NAME,
    QUESTION_COUNT,
    TIME_PER_Q,
    QUESTION_TEXT,
    QUESTION_OPTIONS,
    CORRECT_ANSWER,
    RESULTS_DELAY,
) = range(8)


def _lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            ]
        ]
    )


def _time_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t(lang, "time_none"), callback_data="time_none")],
            [
                InlineKeyboardButton(t(lang, "time_10"), callback_data="time_10"),
                InlineKeyboardButton(t(lang, "time_15"), callback_data="time_15"),
                InlineKeyboardButton(t(lang, "time_20"), callback_data="time_20"),
            ],
        ]
    )


def _delay_keyboard(lang: str) -> InlineKeyboardMarkup:
    keys = [
        ("delay_10m", "10m"),
        ("delay_1h", "1h"),
        ("delay_5h", "5h"),
        ("delay_10h", "10h"),
        ("delay_15h", "15h"),
        ("delay_20h", "20h"),
    ]
    rows = []
    row = []
    for label_key, data_key in keys:
        row.append(InlineKeyboardButton(t(lang, label_key), callback_data=f"delay_{data_key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args and context.args[0].startswith("test_"):
        await start_test_from_link(update, context)
        return ConversationHandler.END

    await update.effective_message.reply_text(
        t("ru", "choose_lang"),
        reply_markup=_lang_keyboard(),
    )
    return LANG


async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_entry(update, context)


async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = "ru" if query.data == "lang_ru" else "uz"
    user_id = update.effective_user.id
    db.set_user_lang(user_id, lang)
    context.user_data.clear()
    context.user_data["lang"] = lang

    await query.edit_message_text(t(lang, "enter_test_name"))
    return TEST_NAME


async def receive_test_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["lang"]
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(t(lang, "enter_test_name"))
        return TEST_NAME
    context.user_data["test_name"] = name
    await update.message.reply_text(t(lang, "enter_question_count"))
    return QUESTION_COUNT


async def receive_question_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["lang"]
    try:
        count = int(update.message.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(t(lang, "invalid_number"))
        return QUESTION_COUNT

    context.user_data["question_count"] = count
    context.user_data["current_q"] = 1

    await update.message.reply_text(
        t(lang, "choose_time"),
        reply_markup=_time_keyboard(lang),
    )
    return TIME_PER_Q


async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data["lang"]
    key = query.data.replace("time_", "")
    context.user_data["time_per_question"] = TIME_OPTIONS[key]

    test_id = db.create_test(
        creator_id=update.effective_user.id,
        name=context.user_data["test_name"],
        lang=lang,
        question_count=context.user_data["question_count"],
        time_per_question=context.user_data["time_per_question"],
    )
    context.user_data["test_id"] = test_id

    n = context.user_data["current_q"]
    total = context.user_data["question_count"]
    await query.edit_message_text(t(lang, "question_n", n=n, total=total))
    return QUESTION_TEXT


async def receive_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["lang"]
    text = update.message.text.strip()
    if not text:
        n = context.user_data["current_q"]
        total = context.user_data["question_count"]
        await update.message.reply_text(t(lang, "question_n", n=n, total=total))
        return QUESTION_TEXT

    context.user_data["current_question_text"] = text
    await update.message.reply_text(t(lang, "enter_options"))
    return QUESTION_OPTIONS


async def receive_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["lang"]
    options = [line.strip() for line in update.message.text.strip().split("\n") if line.strip()]
    if len(options) < 2:
        await update.message.reply_text(t(lang, "min_options"))
        return QUESTION_OPTIONS

    context.user_data["current_options"] = options
    buttons = [
        [InlineKeyboardButton(f"{i + 1}. {opt}", callback_data=f"correct_{i}")]
        for i, opt in enumerate(options)
    ]
    await update.message.reply_text(
        t(lang, "choose_correct"),
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CORRECT_ANSWER


async def choose_correct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data["lang"]
    correct_index = int(query.data.replace("correct_", ""))

    n = context.user_data["current_q"]
    db.add_question(
        test_id=context.user_data["test_id"],
        number=n,
        text=context.user_data["current_question_text"],
        options=context.user_data["current_options"],
        correct_index=correct_index,
    )

    total = context.user_data["question_count"]
    if n < total:
        context.user_data["current_q"] = n + 1
        await query.edit_message_text(t(lang, "question_n", n=n + 1, total=total))
        return QUESTION_TEXT

    await query.edit_message_text(
        t(lang, "choose_results_delay"),
        reply_markup=_delay_keyboard(lang),
    )
    return RESULTS_DELAY


async def choose_delay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data["lang"]
    delay_key = query.data.replace("delay_", "")
    delay_sec = RESULTS_DELAY_OPTIONS[delay_key]

    test_id = context.user_data["test_id"]
    db.set_results_delay(test_id, delay_sec)
    db.activate_test(test_id)

    me = await context.bot.get_me()
    link = test_deep_link(me.username, test_id)
    name = context.user_data["test_name"]

    link_message = t(lang, "test_link_text", name=name, link=link)
    await query.edit_message_text(t(lang, "test_ready", name=name))
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=link_message,
    )

    context.job_queue.run_once(
        send_results_job,
        when=delay_sec,
        data={"test_id": test_id},
        name=f"results_{test_id}",
    )

    context.user_data.clear()
    return ConversationHandler.END


async def send_results_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await finish_test_and_send_results(context, context.job.data["test_id"])


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang") or db.get_user_lang(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text(t(lang, "cancelled"))
    return ConversationHandler.END


def build_creator_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_entry)],
        states={
            LANG: [CallbackQueryHandler(choose_lang, pattern="^lang_")],
            TEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_test_name)],
            QUESTION_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question_count)
            ],
            TIME_PER_Q: [CallbackQueryHandler(choose_time, pattern="^time_")],
            QUESTION_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question_text)
            ],
            QUESTION_OPTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_options)
            ],
            CORRECT_ANSWER: [
                CallbackQueryHandler(choose_correct, pattern="^correct_")
            ],
            RESULTS_DELAY: [CallbackQueryHandler(choose_delay, pattern="^delay_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
