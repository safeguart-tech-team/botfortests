from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from locales import t
from utils import format_results


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

    db.finish_test(test_id)
    _cancel_results_job(context.job_queue, test_id)

    participants = db.get_participants_ranked(test_id)
    message = format_results(
        test["lang"], test["name"], participants, test["question_count"]
    )
    await context.bot.send_message(chat_id=test["creator_id"], text=message)

    if notify_early:
        await context.bot.send_message(
            chat_id=test["creator_id"],
            text=t(test["lang"], "results_sent_early", name=test["name"]),
        )
    return True


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

        ok = await finish_test_and_send_results(context, test_id, notify_early=True)
        if not ok:
            await update.message.reply_text(t(lang, "test_already_finished"))
        return

    active = db.get_active_tests_by_creator(user_id)
    if not active:
        await update.message.reply_text(t(lang, "no_active_tests"))
        return

    if len(active) == 1:
        await finish_test_and_send_results(context, active[0]["id"], notify_early=True)
        return

    buttons = [
        [InlineKeyboardButton(test["name"], callback_data=f"results_now_{test['id']}")]
        for test in active
    ]
    await update.message.reply_text(
        t(lang, "choose_test_for_results"),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


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

    ok = await finish_test_and_send_results(context, test_id, notify_early=True)
    if ok:
        await query.edit_message_text(t(lang, "results_sent_early", name=test["name"]))
    else:
        await query.edit_message_text(t(lang, "test_already_finished"))


def build_results_handlers():
    return [
        CommandHandler("results", cmd_results),
        CallbackQueryHandler(on_results_now, pattern="^results_now_"),
    ]
