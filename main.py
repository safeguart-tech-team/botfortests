import logging
import sys

from telegram.error import InvalidToken
from telegram.ext import Application
from telegram.request import HTTPXRequest

from config import BOT_TOKEN, is_valid_bot_token
from database import get_active_tests_past_deadline, init_db, run_async
from handlers.creator import build_creator_handlers
from handlers.results_cmd import build_results_handlers, finish_test_and_send_results
from handlers.taker import build_taker_handlers
from handlers.text_router import build_text_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Параллельная обработка апдейтов при 100+ участниках
CONCURRENT_UPDATES = 128
HTTP_POOL_SIZE = 64


async def on_error(update: object, context) -> None:
    logger.error("Ошибка при обработке сообщения:", exc_info=context.error)

_TOKEN_HELP = """
Ошибка: токен бота не настроен или неверный.

1. Откройте @BotFather в Telegram → /mybots → ваш бот → API Token
2. Скопируйте токен (формат: 123456789:AAHxxxxxxxx...)
3. Откройте файл .env в папке TestBot
4. Вставьте токен в строку:
   BOT_TOKEN=сюда_ваш_токен
5. Сохраните файл и снова запустите: .venv\\Scripts\\python main.py

Не используйте пример из .env.example — нужен ваш настоящий токен.
"""


async def check_missed_deadlines(context) -> None:
    due = await run_async(get_active_tests_past_deadline)
    for test in due:
        try:
            await finish_test_and_send_results(context, test["id"])
        except Exception:
            logger.exception("Auto-finish failed for test %s", test["id"])


def main() -> None:
    if not is_valid_bot_token(BOT_TOKEN):
        print(_TOKEN_HELP, file=sys.stderr)
        sys.exit(1)

    from config import DB_PATH
    from database import ensure_db_directory

    ensure_db_directory()
    init_db()
    logger.info("Database path: %s", DB_PATH)

    request = HTTPXRequest(
        connection_pool_size=HTTP_POOL_SIZE,
        pool_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=20.0,
    )
    get_updates_request = HTTPXRequest(
        connection_pool_size=8,
        pool_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=20.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .concurrent_updates(CONCURRENT_UPDATES)
        .build()
    )
    app.add_error_handler(on_error)

    app.add_handler(build_text_handler())
    for handler in build_creator_handlers():
        app.add_handler(handler)
    for handler in build_results_handlers():
        app.add_handler(handler)
    for handler in build_taker_handlers():
        app.add_handler(handler)

    app.job_queue.run_repeating(check_missed_deadlines, interval=60, first=10)

    logger.info(
        "Bot started (concurrent_updates=%s, http_pool=%s)...",
        CONCURRENT_UPDATES,
        HTTP_POOL_SIZE,
    )
    try:
        app.run_polling(allowed_updates=["message", "callback_query"])
    except InvalidToken:
        print(_TOKEN_HELP, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
