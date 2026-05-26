from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
from config import RESULTS_DELAY_OPTIONS, TIME_OPTIONS
from handlers.results_cmd import finish_test_and_send_results
from handlers.taker import start_test_from_link
from locales import t
from utils import option_label, test_deep_link


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
        ("delay_manual", "manual"),
        ("delay_10m", "10m"),
        ("delay_1h", "1h"),
        ("delay_5h", "5h"),
        ("delay_10h", "10h"),
        ("delay_15h", "15h"),
        ("delay_20h", "20h"),
    ]
    rows = [[InlineKeyboardButton(t(lang, "delay_manual"), callback_data="delay_manual")]]
    row = []
    for label_key, data_key in keys[1:]:
        row.append(InlineKeyboardButton(t(lang, label_key), callback_data=f"delay_{data_key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "ru")


def _clear_create(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


def _clear_fio_wait(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_fio_test_id", None)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args and context.args[0].startswith("test_"):
        await start_test_from_link(update, context)
        return

    _clear_create(context)
    context.user_data["create_step"] = "lang"
    await update.effective_message.reply_text(
        t("ru", "choose_lang"),
        reply_markup=_lang_keyboard(),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang") or db.get_user_lang(update.effective_user.id)
    _clear_create(context)
    await update.message.reply_text(t(lang, "cancelled"))


async def on_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    step = context.user_data.get("create_step")
    if not step:
        return

    data = query.data

    if data.startswith("lang_"):
        if step != "lang":
            return
        await query.answer()
        lang = "ru" if data == "lang_ru" else "uz"
        db.set_user_lang(update.effective_user.id, lang)
        _clear_fio_wait(context)
        context.user_data["lang"] = lang
        context.user_data["create_step"] = "test_name"
        await query.message.reply_text(t(lang, "enter_test_name"))
        return

    if data.startswith("time_"):
        if step != "time":
            return
        await query.answer()
        lang = _lang(context)
        key = data.replace("time_", "")
        context.user_data["time_per_question"] = TIME_OPTIONS[key]

        test_id = db.create_test(
            creator_id=update.effective_user.id,
            name=context.user_data["test_name"],
            lang=lang,
            question_count=context.user_data["question_count"],
            time_per_question=context.user_data["time_per_question"],
        )
        context.user_data["test_id"] = test_id
        context.user_data["create_step"] = "question_text"

        n = context.user_data["current_q"]
        total = context.user_data["question_count"]
        await query.message.reply_text(t(lang, "question_n", n=n, total=total))
        return

    if data.startswith("correct_"):
        if step != "correct":
            return
        await query.answer()
        lang = _lang(context)
        correct_index = int(data.replace("correct_", ""))

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
            context.user_data["create_step"] = "question_text"
            await query.message.reply_text(t(lang, "question_n", n=n + 1, total=total))
            return

        context.user_data["create_step"] = "results_delay"
        await query.message.reply_text(
            t(lang, "choose_results_delay"),
            reply_markup=_delay_keyboard(lang),
        )
        return

    if data.startswith("delay_"):
        if step != "results_delay":
            return
        await query.answer()
        lang = _lang(context)
        delay_key = data.replace("delay_", "")
        delay_sec = RESULTS_DELAY_OPTIONS[delay_key]

        test_id = context.user_data["test_id"]
        db.set_results_delay(test_id, delay_sec)
        db.activate_test(test_id)

        me = await context.bot.get_me()
        link = test_deep_link(me.username, test_id)
        name = context.user_data["test_name"]

        if delay_sec <= 0:
            ready_text = t(lang, "test_ready_manual", name=name)
        else:
            ready_text = t(lang, "test_ready", name=name)

        await query.message.reply_text(ready_text)
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=t(lang, "test_link_text", name=name, link=link),
        )

        if delay_sec > 0:
            context.job_queue.run_once(
                send_results_job,
                when=delay_sec,
                data={"test_id": test_id},
                name=f"results_{test_id}",
            )

        _clear_create(context)


async def on_create_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    step = context.user_data.get("create_step")
    if step not in ("test_name", "question_count", "question_text", "question_options"):
        return

    lang = _lang(context)
    text = (update.message.text or "").strip()

    if step == "test_name":
        if not text:
            await update.message.reply_text(t(lang, "enter_test_name"))
            raise ApplicationHandlerStop
        context.user_data["test_name"] = text
        context.user_data["create_step"] = "question_count"
        await update.message.reply_text(t(lang, "enter_question_count"))
        raise ApplicationHandlerStop

    if step == "question_count":
        try:
            count = int(text)
            if count < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t(lang, "invalid_number"))
            raise ApplicationHandlerStop

        context.user_data["question_count"] = count
        context.user_data["current_q"] = 1
        context.user_data["create_step"] = "time"
        await update.message.reply_text(
            t(lang, "choose_time"),
            reply_markup=_time_keyboard(lang),
        )
        raise ApplicationHandlerStop

    if step == "question_text":
        if not text:
            n = context.user_data["current_q"]
            total = context.user_data["question_count"]
            await update.message.reply_text(t(lang, "question_n", n=n, total=total))
            raise ApplicationHandlerStop

        context.user_data["current_question_text"] = text
        context.user_data["create_step"] = "question_options"
        await update.message.reply_text(t(lang, "enter_options"))
        raise ApplicationHandlerStop

    if step == "question_options":
        options = [line.strip() for line in text.split("\n") if line.strip()]
        if len(options) < 2:
            await update.message.reply_text(t(lang, "min_options"))
            raise ApplicationHandlerStop

        context.user_data["current_options"] = options
        context.user_data["create_step"] = "correct"
        options_text = "\n".join(f"{option_label(i)}. {opt}" for i, opt in enumerate(options))
        buttons = [
            [InlineKeyboardButton(option_label(i), callback_data=f"correct_{i}")]
            for i in range(len(options))
        ]
        await update.message.reply_text(
            f"{t(lang, 'choose_correct')}\n\n{options_text}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        raise ApplicationHandlerStop


async def send_results_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await finish_test_and_send_results(context, context.job.data["test_id"])


def build_creator_handlers() -> list:
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("cancel", cmd_cancel),
        CallbackQueryHandler(on_create_callback, pattern="^(lang_|time_|correct_|delay_)"),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            on_create_message,
            block=False,
        ),
    ]
