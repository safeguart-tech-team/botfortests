# TestBot — Telegram-бот для тестов на канале

Бот для создания тестов, публикации ссылки в канале и сбора результатов в личных сообщениях.

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Создать новый тест |
| `/results` | Досрочно получить результаты активного теста |
| `/cancel` | Отменить создание теста |

## Локальный запуск

1. Скопируйте `.env.example` в `.env` и укажите `BOT_TOKEN` от [@BotFather](https://t.me/BotFather).
2. Установите зависимости и запустите:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
python main.py
```

## Деплой на [Railway](https://railway.app)

1. Создайте проект на Railway и подключите репозиторий [botfortests](https://github.com/safeguart-tech-team/botfortests).
2. В **Variables** добавьте:
   - `BOT_TOKEN` — токен бота от BotFather
   - `DATABASE_PATH` — `/data/testbot.db` (если том смонтирован в `/data`)
3. В **Volumes** смонтируйте том в `/data`. Если `DATABASE_PATH` не задан, бот сам использует том через `RAILWAY_VOLUME_MOUNT_PATH`.
4. Railway автоматически запустит `python main.py` (см. `railway.toml` и `Procfile`).

> **Важно:** не запускайте бота одновременно локально и на Railway — будет конфликт polling.

## Переменные окружения

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `BOT_TOKEN` | Да | Токен Telegram-бота |
| `DATABASE_PATH` | Нет | Путь к SQLite (по умолчанию `./testbot.db`) |

## Структура проекта

```
main.py           — точка входа
config.py         — настройки
database.py       — SQLite
locales.py        — RU / UZ тексты
handlers/         — логика бота
```
