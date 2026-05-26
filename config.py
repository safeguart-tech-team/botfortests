import os
import re
from pathlib import Path

from dotenv import load_dotenv

_base = Path(__file__).parent

INVALID_TOKENS = {
    "",
    "your_bot_token_from_botfather",
    "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "ваш_токен_от_BotFather",
}

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


def is_valid_bot_token(token: str) -> bool:
    token = (token or "").strip()
    if token in INVALID_TOKENS:
        return False
    return bool(TOKEN_RE.match(token))


def _load_token() -> str:
    load_dotenv(_base / ".env")
    token = os.getenv("BOT_TOKEN", "").strip()
    if is_valid_bot_token(token):
        return token

    load_dotenv(_base / ".env.example")
    token = os.getenv("BOT_TOKEN", "").strip()
    if is_valid_bot_token(token):
        return token

    return token


BOT_TOKEN = _load_token()


def _resolve_db_path() -> Path:
    explicit = os.getenv("DATABASE_PATH", "").strip()
    if explicit:
        return Path(explicit)

    # Railway автоматически задаёт путь смонтированного тома
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if volume_mount:
        return Path(volume_mount) / "testbot.db"

    return _base / "testbot.db"


DB_PATH = _resolve_db_path()

TIME_OPTIONS = {
    "none": None,
    "10": 10,
    "15": 15,
    "20": 20,
}

RESULTS_DELAY_OPTIONS = {
    "10m": 10 * 60,
    "1h": 60 * 60,
    "5h": 5 * 60 * 60,
    "10h": 10 * 60 * 60,
    "15h": 15 * 60 * 60,
    "20h": 20 * 60 * 60,
}
