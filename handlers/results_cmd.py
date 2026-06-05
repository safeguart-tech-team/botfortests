import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from locales import t
from utils import format_results, split_message

logger = logging.getLogger(__name__)


def _cancel_results_job(job_queue, test_id: int) -> None:
    if not job_queue:
        return
    for job in job_queue.get_jobs_by_name(f"results_{test_id}"):
        job.schedule_removal()


async def finish_test_and_send_results(
    context: ContextTypes.DEFAULT_TYPE,
    test_id: int,
    *,
    notify_early: bool = False,
) -> bool:
    test = db.get_test(test_id)
    if not test or test["status"] == "finished":
        return False

    participants = db.get_participants_ranked(test_id)
    message = format_results(
        test["lang"], test["name"], participants, test["question_count"]
    )
    for part in split_message(message):
        await context.bot.send_message(chat_id=test["creator_id"], text=part)

    db.finish_test(test_id)
    _cancel_results_job(context.job_queue, test_id)

    if notify_early:
        await context.bot.send_message(
            chat_id=test["creator_id"],
            text=t(test["lang"], "results_sent_early", name=test["name"]),
        )
    return True


async def send_progress_summary(
    context: ContextTypes.DEFAULT_TYPE,
    test_id: int,
    *,
    chat_id: int,
) -> None:
    test = db.get_test(test_id)
    if not test:
        return

    lang = test["lang"]
    started, finished = db.count_participants(test_id)
    in_progress = max(started - finished, 0)
    text = t(
        lang,
        "interim_stats_short",
        name=test["name"],
        finished=finished,
        in_progress=in_progress,
        total=test["question_count"],
    )
    await context.bot.send_message(chat_id=chat_id, text=text)


async def send_interim_results(
    context: ContextTypes.DEFAULT_TYPE,
    test_id: int,
    *,
    chat_id: int | None = None,
) -> bool:
    test = db.get_test(test_id)
    if not test or test["status"] != "active":
        return False

    lang = test["lang"]
    participants = db.get_participants_ranked(test_id)
    message = format_results(
        lang, test["name"], participants, test["question_count"], interim=True
    )

    started, finished = db.count_participants(test_id)
    in_progress = max(started - finished, 0)
    if in_progress > 0:
        message += "\n\n" + t(lang, "interim_in_progress", count=in_progress)

    target = chat_id if chat_id is not None else test["creator_id"]
    for part in split_message(message):
        await context.bot.send_message(chat_id=target, text=part)
    return True


async def _resolve_test_for_creator(
    update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str] | None
) -> int | None:
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)

    if args:
        try:
            test_id = int(args[0])
        except ValueError:
            await update.effective_message.reply_text(t(lang, "no_active_tests"))
            return None

        test = db.get_test(test_id)
        if not test or test["creator_id"] != user_id:
            await update.effective_message.reply_text(t(lang, "not_test_creator"))
            return None
        if test["status"] != "active":
            await update.effective_message.reply_text(t(lang, "test_not_active"))
            return None
        return test_id

    active = db.get_active_tests_by_creator(user_id)
    if not active:
        await update.effective_message.reply_text(t(lang, "no_active_tests"))
        return None

    if len(active) == 1:
        return active[0]["id"]

    return None


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)

    await update.message.reply_text(t(lang, "progress_wait"))

    test_id = await _resolve_test_for_creator(update, context, context.args)
    if test_id is None and not context.args:
        active = db.get_active_tests_by_creator(user_id)
        if len(active) > 1:
            buttons = [
                [InlineKeyboardButton(test["name"], callback_data=f"progress_{test['id']}")]
                for test in active
            ]
            await update.message.reply_text(
                t(lang, "choose_test_for_progress"),
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        return

    if test_id is None:
        return

    try:
        ok = await send_interim_results(context, test_id, chat_id=user_id)
        if not ok:
            await update.message.reply_text(t(lang, "test_not_active"))
    except Exception:
        logger.exception("Failed /progress for test %s", test_id)
        try:
            await send_progress_summary(context, test_id, chat_id=user_id)
            await update.message.reply_text(t(lang, "progress_fallback"))
        except Exception:
            logger.exception("Failed /progress fallback for test %s", test_id)
            await update.message.reply_text(t(lang, "progress_error"))


async def cmd_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)

    if context.args:
        try:
            test_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(t(lang, "no_active_tests"))
            return

        test = db.get_test(test_id)
        if not test or test["creator_id"] != user_id:
            await update.message.reply_text(t(lang, "not_test_creator"))
            return
        if test["status"] == "finished":
            await update.message.reply_text(t(lang, "test_already_finished"))
            return

        try:
            ok = await finish_test_and_send_results(context, test_id, notify_early=True)
        except Exception:
            logger.exception("Failed /results for test %s", test_id)
            await update.message.reply_text(t(lang, "results_send_error"))
            return
        if not ok:
            await update.message.reply_text(t(lang, "test_already_finished"))
        return

    active = db.get_active_tests_by_creator(user_id)
    if not active:
        await update.message.reply_text(t(lang, "no_active_tests"))
        return

    if len(active) == 1:
        try:
            await finish_test_and_send_results(
                context, active[0]["id"], notify_early=True
            )
        except Exception:
            logger.exception("Failed /results for test %s", active[0]["id"])
            await update.message.reply_text(t(lang, "results_send_error"))
        return

    buttons = [
        [InlineKeyboardButton(test["name"], callback_data=f"results_now_{test['id']}")]
        for test in active
    ]
    await update.message.reply_text(
        t(lang, "choose_test_for_results"),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def on_progress_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    test_id = int(query.data.replace("progress_", ""))

    test = db.get_test(test_id)
    if not test or test["creator_id"] != user_id:
        await query.edit_message_text(t(lang, "not_test_creator"))
        return
    if test["status"] != "active":
        await query.edit_message_text(t(lang, "test_not_active"))
        return

    ok = await send_interim_results(context, test_id, chat_id=user_id)
    if ok:
        await query.edit_message_text(t(lang, "interim_results_sent", name=test["name"]))
    else:
        await query.edit_message_text(t(lang, "test_not_active"))


async def on_results_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    test_id = int(query.data.replace("results_now_", ""))

    test = db.get_test(test_id)
    if not test or test["creator_id"] != user_id:
        await query.edit_message_text(t(lang, "not_test_creator"))
        return
    if test["status"] == "finished":
        await query.edit_message_text(t(lang, "test_already_finished"))
        return

    try:
        ok = await finish_test_and_send_results(context, test_id, notify_early=True)
    except Exception:
        logger.exception("Failed results_now for test %s", test_id)
        await query.edit_message_text(t(lang, "results_send_error"))
        return
    if ok:
        await query.edit_message_text(t(lang, "results_sent_early", name=test["name"]))
    else:
        await query.edit_message_text(t(lang, "test_already_finished"))


def build_results_handlers():
    return [
        CommandHandler("progress", cmd_progress),
        CommandHandler("results", cmd_results),
        CallbackQueryHandler(on_progress_pick, pattern="^progress_"),
        CallbackQueryHandler(on_results_now, pattern="^results_now_"),
    ]
