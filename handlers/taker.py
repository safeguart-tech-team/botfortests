import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, ContextTypes

import database as db
from locales import t
from utils import display_name

logger = logging.getLogger(__name__)

_active_sessions: dict[int, dict] = {}


def _options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"ans_{i}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)


def _question_text(session: dict, *, is_first: bool, remaining: int | None) -> str:
    idx = session["index"]
    q = session["questions"][idx]
    lang = session["lang"]
    test = session["test"]
    total = len(session["questions"])

    if is_first:
        header = t(lang, "start_test", name=test["name"], total=total)
    else:
        header = t(lang, "question_header", n=idx + 1, total=total)

    text = f"{header}\n\n{q['text']}"
    if remaining is not None:
        text += f"\n\n{t(lang, 'time_left', sec=remaining)}"
    return text


def _cancel_countdown(session: dict) -> None:
    task = session.get("countdown_task")
    if task and not task.done():
        task.cancel()
    session["countdown_task"] = None


def _clear_user_session(user_id: int) -> None:
    session = _active_sessions.pop(user_id, None)
    if session:
        _cancel_countdown(session)


async def _edit_question_message(
    context: ContextTypes.DEFAULT_TYPE,
    session: dict,
    *,
    is_first: bool,
    remaining: int | None,
) -> None:
    text = _question_text(session, is_first=is_first, remaining=remaining)
    markup = _options_keyboard(session["questions"][session["index"]]["options"])
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
    user = update.effective_user
    user_id = user.id

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

    for q in questions:
        if not q.get("text") or not q.get("options"):
            await query.answer()
            await query.message.reply_text(t(lang, "questions_missing"))
            return

    await query.answer()

    _clear_user_session(user_id)
    db.reset_incomplete_participation(test_id, user_id)

    try:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass

        participant_id = db.create_participant(test_id, user_id, display_name(user))
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
        logger.exception("Failed to start test %s for user %s", test_id, user_id)
        _clear_user_session(user_id)
        db.reset_incomplete_participation(test_id, user_id)
        await query.message.reply_text(t(lang, "test_start_error"))


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
    markup = _options_keyboard(session["questions"][session["index"]]["options"])
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


def build_taker_handlers() -> list[CallbackQueryHandler]:
    return [CallbackQueryHandler(on_taker_callback, pattern="^(begin_|ans_)")]
