from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import database as db
from config import RESULTS_DELAY_OPTIONS, TIME_OPTIONS
from handlers.results_cmd import finish_test_and_send_results
from handlers.taker import start_test_from_link
from locales import t
from question_parser import (
    format_questions_preview,
    is_done_message,
    parse_questions_bulk,
)
from utils import split_message, test_deep_link


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
            ],
            [
                InlineKeyboardButton(t(lang, "time_20"), callback_data="time_20"),
                InlineKeyboardButton(t(lang, "time_30"), callback_data="time_30"),
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


def _questions_done_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t(lang, "btn_questions_done"), callback_data="questions_done"
                )
            ]
        ]
    )


def _lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "ru")


def _clear_create(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


def _clear_participant_wait(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_fio_test_id", None)


def _combined_questions_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    chunks = context.user_data.get("questions_chunks") or []
    return "\n\n".join(c for c in chunks if c.strip())


def _parse_error_hint(lang: str, code: str, kwargs: dict) -> str:
    return t(lang, code, **kwargs) + "\n\n" + t(lang, "questions_continue_hint")


async def _finalize_questions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    from_callback: bool = False,
) -> None:
    lang = _lang(context)
    combined = _combined_questions_text(context)
    result = parse_questions_bulk(combined, allow_incomplete_last=False)

    reply = (
        update.callback_query.message.reply_text
        if from_callback and update.callback_query
        else update.effective_message.reply_text
    )

    if result.error:
        await reply(_parse_error_hint(lang, result.error.code, result.error.kwargs))
        soft = parse_questions_bulk(combined, allow_incomplete_last=True)
        await reply(
            t(lang, "questions_waiting_more", count=len(soft.questions)),
            reply_markup=_questions_done_keyboard(lang),
        )
        return

    questions = result.questions
    try:
        test_id = await db.run_async(
            db.create_test,
            update.effective_user.id,
            context.user_data["test_name"],
            lang,
            len(questions),
            context.user_data.get("time_per_question"),
        )
        for q in questions:
            await db.run_async(
                db.add_question,
                test_id,
                q.number,
                q.text,
                q.options,
                q.correct_index,
            )
    except Exception:
        await reply(t(lang, "questions_save_error"))
        return

    context.user_data["test_id"] = test_id
    context.user_data["question_count"] = len(questions)
    context.user_data.pop("questions_chunks", None)
    context.user_data["create_step"] = "results_delay"

    preview = format_questions_preview(questions)
    accepted = t(lang, "questions_accepted", count=len(questions))
    for part in split_message(f"{accepted}\n\n{preview}"):
        await reply(part)
    await reply(
        t(lang, "choose_results_delay"),
        reply_markup=_delay_keyboard(lang),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args and context.args[0].startswith("test_"):
        await start_test_from_link(update, context)
        return

    _clear_create(context)
    _clear_participant_wait(context)
    context.user_data["create_step"] = "lang"
    await update.effective_message.reply_text(
        t("ru", "choose_lang"),
        reply_markup=_lang_keyboard(),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang") or await db.run_async(
        db.get_user_lang, update.effective_user.id
    )
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
        await db.run_async(db.set_user_lang, update.effective_user.id, lang)
        _clear_participant_wait(context)
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
        context.user_data["questions_chunks"] = []
        context.user_data["create_step"] = "questions_bulk"
        await query.message.reply_text(t(lang, "enter_questions_bulk"))
        return

    if data == "questions_done":
        if step != "questions_bulk":
            return
        await query.answer()
        await _finalize_questions(update, context, from_callback=True)
        return

    if data.startswith("delay_"):
        if step != "results_delay":
            return
        await query.answer()
        lang = _lang(context)
        delay_key = data.replace("delay_", "")
        delay_sec = RESULTS_DELAY_OPTIONS[delay_key]

        test_id = context.user_data["test_id"]
        await db.run_async(db.set_results_delay, test_id, delay_sec)
        await db.run_async(db.activate_test, test_id)

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
    if step not in ("test_name", "questions_bulk"):
        return

    lang = _lang(context)
    text = (update.message.text or "").strip()

    if step == "test_name":
        if not text:
            await update.message.reply_text(t(lang, "enter_test_name"))
            raise ApplicationHandlerStop
        context.user_data["test_name"] = text
        context.user_data["create_step"] = "time"
        await update.message.reply_text(
            t(lang, "choose_time"),
            reply_markup=_time_keyboard(lang),
        )
        raise ApplicationHandlerStop

    if step == "questions_bulk":
        if is_done_message(text):
            await _finalize_questions(update, context, from_callback=False)
            raise ApplicationHandlerStop

        chunks = context.user_data.setdefault("questions_chunks", [])
        chunks.append(text)
        combined = _combined_questions_text(context)
        result = parse_questions_bulk(combined, allow_incomplete_last=True)

        if result.error:
            # Откатываем последний кусок — он ломает уже собранное
            chunks.pop()
            await update.message.reply_text(
                _parse_error_hint(lang, result.error.code, result.error.kwargs)
            )
            count = len(
                parse_questions_bulk(
                    _combined_questions_text(context), allow_incomplete_last=True
                ).questions
            )
            await update.message.reply_text(
                t(lang, "questions_waiting_more", count=count),
                reply_markup=_questions_done_keyboard(lang),
            )
            raise ApplicationHandlerStop

        count = len(result.questions)
        if result.trailing_incomplete and count == 0:
            await update.message.reply_text(
                t(lang, "questions_chunk_partial"),
                reply_markup=_questions_done_keyboard(lang),
            )
        elif result.trailing_incomplete:
            await update.message.reply_text(
                t(lang, "questions_chunk_ok_partial", count=count),
                reply_markup=_questions_done_keyboard(lang),
            )
        else:
            await update.message.reply_text(
                t(lang, "questions_chunk_ok", count=count),
                reply_markup=_questions_done_keyboard(lang),
            )
        raise ApplicationHandlerStop


async def send_results_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await finish_test_and_send_results(context, context.job.data["test_id"])


def build_creator_handlers() -> list:
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("cancel", cmd_cancel),
        CallbackQueryHandler(
            on_create_callback, pattern="^(lang_|time_|delay_|questions_done)"
        ),
    ]
