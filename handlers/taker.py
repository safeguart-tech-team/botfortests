import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationHandlerStop,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
from locales import t
from utils import option_label

logger = logging.getLogger(__name__)

_active_sessions: dict[int, dict] = {}
FIO_MIN_LEN = 5
FIO_MIN_WORDS = 2
FIO_MAX_LEN = 120


def _options_list_text(lang: str, options: list[str]) -> str:
    lines = [t(lang, "answer_options")]
    for i, opt in enumerate(options):
        lines.append(f"{option_label(i)}. {opt}")
    return "\n".join(lines)


def _options_keyboard(option_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(option_label(i), callback_data=f"ans_{i}")]
        for i in range(option_count)
    ]
    return InlineKeyboardMarkup(buttons)


def _question_text(session: dict, *, is_first: bool, remaining: int | None) -> str:
    idx = session["index"]
    q = session["questions"][idx]
    lang = session["lang"]
    test = session["test"]
    total = len(session["questions"])
    options = q["options"]

    if is_first:
        header = t(lang, "start_test", name=test["name"], total=total)
    else:
        header = t(lang, "question_header", n=idx + 1, total=total)

    parts = [header, "", q["text"], "", _options_list_text(lang, options)]
    if remaining is not None:
        parts.append("")
        parts.append(t(lang, "time_left", sec=remaining))
    return "\n".join(parts)


def _is_valid_fio(text: str) -> bool:
    text = text.strip()
    if len(text) < FIO_MIN_LEN or len(text) > FIO_MAX_LEN:
        return False
    words = [w for w in re.split(r"\s+", text) if w]
    return len(words) >= FIO_MIN_WORDS


def _cancel_countdown(session: dict) -> None:
    task = session.get("countdown_task")
    if task and not task.done():
        task.cancel()
    session["countdown_task"] = None


def _clear_user_session(user_id: int) -> None:
    session = _active_sessions.pop(user_id, None)
    if session:
        _cancel_countdown(session)


def _clear_fio_wait(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_fio_test_id", None)


async def _edit_question_message(
    context: ContextTypes.DEFAULT_TYPE,
    session: dict,
    *,
    is_first: bool,
    remaining: int | None,
) -> None:
    text = _question_text(session, is_first=is_first, remaining=remaining)
    q = session["questions"][session["index"]]
    markup = _options_keyboard(len(q["options"]))
    try:
        await context.bot.edit_message_text(
            chat_id=session["chat_id"],
            message_id=session["message_id"],
            text=text,
            reply_markup=markup,
        )
    except BadRequest as err:
        if "message is not modified" not in str(err).lower():
            raise


async def start_test_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    args = context.args
    if not args or not args[0].startswith("test_"):
        return False

    try:
        test_id = int(args[0].replace("test_", ""))
    except ValueError:
        return False

    user = update.effective_user
    test = db.get_test(test_id)
    lang = test["lang"] if test else db.get_user_lang(user.id)

    if not test or test["status"] != "active":
        await update.message.reply_text(t(lang, "test_not_found"))
        return True

    if db.has_completed_participation(test_id, user.id):
        await update.message.reply_text(t(lang, "already_participated"))
        return True

    questions = db.get_questions(test_id)
    if not questions:
        await update.message.reply_text(t(lang, "questions_missing"))
        return True

    _clear_fio_wait(context)
    total = len(questions)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(lang, "btn_start"), callback_data=f"begin_{test_id}")]]
    )
    await update.message.reply_text(
        t(lang, "test_invite", name=test["name"], total=total),
        reply_markup=keyboard,
    )
    return True


async def on_begin_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id

    try:
        test_id = int(query.data.replace("begin_", ""))
    except ValueError:
        await query.answer()
        return

    test = db.get_test(test_id)
    lang = test["lang"] if test else db.get_user_lang(user_id)

    if not test or test["status"] != "active":
        await query.answer()
        await query.message.reply_text(t(lang, "test_not_found"))
        return

    if db.has_completed_participation(test_id, user_id):
        await query.answer()
        await query.message.reply_text(t(lang, "already_participated"))
        return

    questions = db.get_questions(test_id)
    if not questions:
        await query.answer()
        await query.message.reply_text(t(lang, "questions_missing"))
        return

    await query.answer()

    _clear_user_session(user_id)
    db.reset_incomplete_participation(test_id, user_id)

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass

    context.user_data["awaiting_fio_test_id"] = test_id
    await query.message.reply_text(t(lang, "enter_full_name"))


async def on_fio_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    test_id = context.user_data.get("awaiting_fio_test_id")
    if not test_id:
        return

    user_id = update.effective_user.id
    test = db.get_test(test_id)
    lang = test["lang"] if test else db.get_user_lang(user_id)

    if not test or test["status"] != "active":
        _clear_fio_wait(context)
        await update.message.reply_text(t(lang, "test_not_found"))
        raise ApplicationHandlerStop

    if db.has_completed_participation(test_id, user_id):
        _clear_fio_wait(context)
        await update.message.reply_text(t(lang, "already_participated"))
        raise ApplicationHandlerStop

    fio = (update.message.text or "").strip()
    if not _is_valid_fio(fio):
        await update.message.reply_text(t(lang, "invalid_full_name"))
        raise ApplicationHandlerStop

    questions = db.get_questions(test_id)
    if not questions:
        _clear_fio_wait(context)
        await update.message.reply_text(t(lang, "questions_missing"))
        raise ApplicationHandlerStop

    _clear_fio_wait(context)
    _clear_user_session(user_id)
    db.reset_incomplete_participation(test_id, user_id)

    try:
        participant_id = db.create_participant(test_id, user_id, fio)
        session = {
            "test_id": test_id,
            "participant_id": participant_id,
            "lang": lang,
            "questions": questions,
            "index": 0,
            "test": test,
            "countdown_task": None,
            "message_id": None,
            "chat_id": update.effective_chat.id,
            "user_id": user_id,
        }
        _active_sessions[user_id] = session
        await _send_question(update, context, session, is_first=True)
    except Exception:
        logger.exception("Failed to start test %s for user %s after FIO", test_id, user_id)
        _clear_user_session(user_id)
        db.reset_incomplete_participation(test_id, user_id)
        await update.message.reply_text(t(lang, "test_start_error"))

    raise ApplicationHandlerStop


async def _send_question(
    update: Update | None,
    context: ContextTypes.DEFAULT_TYPE,
    session: dict,
    *,
    is_first: bool = False,
    edit_in_place: bool = False,
) -> None:
    time_limit = session["test"].get("time_per_question")
    if time_limit is not None and time_limit <= 0:
        time_limit = None
    remaining = time_limit if time_limit else None

    text = _question_text(session, is_first=is_first, remaining=remaining)
    q = session["questions"][session["index"]]
    markup = _options_keyboard(len(q["options"]))
    chat_id = session["chat_id"]

    _cancel_countdown(session)

    if update and update.callback_query and edit_in_place:
        msg = await update.callback_query.message.edit_text(text, reply_markup=markup)
    elif update and update.callback_query:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    elif update and update.message:
        msg = await update.message.reply_text(text, reply_markup=markup)
    else:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

    session["message_id"] = msg.message_id
    session["current_is_first"] = is_first

    if time_limit:
        session["countdown_task"] = asyncio.create_task(
            _countdown_and_timeout(context, session["user_id"], time_limit)
        )


async def _countdown_and_timeout(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    seconds: int,
) -> None:
    try:
        for remaining in range(seconds - 1, -1, -1):
            await asyncio.sleep(1)

            session = _active_sessions.get(user_id)
            if not session:
                return

            if remaining > 0:
                await _edit_question_message(
                    context,
                    session,
                    is_first=session.get("current_is_first", False),
                    remaining=remaining,
                )
            else:
                await _handle_timeout(context, user_id, session)
                return
    except asyncio.CancelledError:
        return


async def _handle_timeout(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    session: dict,
) -> None:
    _cancel_countdown(session)

    idx = session["index"]
    q = session["questions"][idx]
    lang = session["lang"]

    db.save_answer(session["participant_id"], q["id"], None, False)

    try:
        await context.bot.edit_message_text(
            chat_id=session["chat_id"],
            message_id=session["message_id"],
            text=t(lang, "time_up"),
        )
    except BadRequest:
        pass

    session["index"] += 1
    if session["index"] >= len(session["questions"]):
        await _finish_test(context, user_id, session)
    else:
        await _send_question(None, context, session)


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    session = _active_sessions.get(user_id)

    if not session or not query.data.startswith("ans_"):
        return

    _cancel_countdown(session)

    test = db.get_test(session["test_id"])
    if not test or test["status"] != "active":
        await query.answer()
        lang = session["lang"]
        name = test["name"] if test else ""
        await query.message.reply_text(t(lang, "test_finished", name=name))
        _clear_user_session(user_id)
        return

    await query.answer()

    selected = int(query.data.replace("ans_", ""))
    idx = session["index"]
    q = session["questions"][idx]
    is_correct = selected == q["correct_index"]

    db.save_answer(session["participant_id"], q["id"], selected, is_correct)

    session["index"] += 1
    if session["index"] >= len(session["questions"]):
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        await _finish_test(context, user_id, session)
    else:
        await _send_question(
            update,
            context,
            session,
            is_first=False,
            edit_in_place=True,
        )


async def _finish_test(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    session: dict,
) -> None:
    _cancel_countdown(session)
    lang = session["lang"]
    db.finish_participant(session["participant_id"])
    _active_sessions.pop(user_id, None)

    await context.bot.send_message(
        chat_id=session["chat_id"],
        text=t(lang, "test_complete_participant"),
    )


async def on_taker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.callback_query.data
    if data.startswith("begin_"):
        await on_begin_test(update, context)
    elif data.startswith("ans_"):
        await on_answer(update, context)


def build_taker_handlers() -> list:
    return [
        CallbackQueryHandler(on_taker_callback, pattern="^(begin_|ans_)"),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            on_fio_message,
            block=False,
        ),
    ]
