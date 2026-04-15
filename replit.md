# warfil_bot — Telegram Bot

## Описание
Telegram-бот @warfil_bot на Python с использованием библиотеки python-telegram-bot.

## Структура
- `main.py` — основной файл бота

## Конфигурация
- `TELEGRAM_BOT_TOKEN` — токен бота (хранится в секретах Replit)

## Команды бота
- `/start` — приветственное сообщение
- `/help` — список команд
- Любое текстовое сообщение — бот повторяет его обратно (echo)

## Запуск
Воркфлоу "Start application" запускает `python main.py`

## Зависимости
- python-telegram-bot==22.7
