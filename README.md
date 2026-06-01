# TestBot — Telegram-бот для тестов на канале

Бот для создания тестов, публикации ссылки в канале и сбора результатов в личных сообщениях.

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Создать новый тест |
| `/progress` | Промежуточные результаты (тест не закрывается) |
| `/results` | Завершить тест и получить финальные результаты |
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

Репозиторий: https://github.com/safeguart-tech-team/botfortests

### 1. Новый проект

1. Войдите на [railway.app](https://railway.app).
2. **New Project** → **Deploy from GitHub repo**.
3. Выберите репозиторий `safeguart-tech-team/botfortests` (ветка `main`).
4. Если GitHub не подключён — сначала **Connect GitHub** в настройках Railway.

### 2. Переменные (Variables)

Откройте сервис → вкладка **Variables** → **Add variables**:

| Переменная | Значение |
|------------|----------|
| `BOT_TOKEN` | токен от [@BotFather](https://t.me/BotFather) |
| `DATABASE_PATH` | `/data/testbot.db` |

### 3. Volume (чтобы тесты не пропадали)

1. На схеме проекта: **правый клик** по пустому месту → **Add Volume** (или `Ctrl+K` → Volume).
2. Подключите Volume к сервису бота.
3. **Mount path:** `/data`

### 4. Deploy

1. **Deploy** / **Redeploy** — дождитесь статуса **Active** (зелёный).
2. В **Logs** должно быть: `Bot started, connecting to Telegram...` и `Database path: /data/testbot.db`.
3. Не должно быть `409 Conflict` (значит бот запущен ещё где-то локально).

### 5. Проверка

В Telegram: `/start` у бота — должен ответить выбором языка.

> **Важно:** не запускайте `python main.py` на компьютере, пока бот работает на Railway.

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
