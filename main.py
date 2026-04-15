import os
import logging
from datetime import datetime
from collections import defaultdict
import coc
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import storage
import image_builder

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
COC_EMAIL = os.environ["COC_EMAIL"]
COC_PASSWORD = os.environ["COC_PASSWORD"]
CLAN_TAG = "#2R02GGRUJ"

ROLE_ORDER = {
    "leader": 0,
    "coLeader": 1,
    "admin": 2,
    "member": 3,
}

coc_client = coc.Client()


def format_last_seen(last_seen_str: str | None) -> str:
    if not last_seen_str:
        return ""
    try:
        dt = datetime.fromisoformat(last_seen_str)
        now = datetime.now()
        diff = now - dt
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return " • 🟢 только что"
        elif minutes < 60:
            return f" • 🕐 {minutes} мин. назад"
        elif minutes < 1440:
            hours = minutes // 60
            return f" • 🕐 {hours} ч. назад"
        else:
            days = minutes // 1440
            return f" • 💤 {days} дн. назад"
    except Exception:
        return ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот клана @warfil_bot.\n\n"
        "Доступные команды:\n"
        "/team — активность игроков клана\n"
        "/help — помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — начать\n"
        "/team — активность игроков клана\n"
        "    🏹 пожертвования · 🏛️ вклад в столицу · ⭐ звёзды войны\n"
        "/help — помощь"
    )


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Укажи своё имя в игре.\n"
            "Пример: /register WarriorKing"
        )
        return

    coc_name = " ".join(context.args)
    user_id = update.effective_user.id
    storage.register_player(user_id, coc_name)
    storage.update_last_seen(user_id)
    await update.message.reply_text(
        f"✅ Готово! Ты зарегистрирован как <b>{coc_name}</b>.\n"
        "Теперь пиши /online чтобы отметиться активным.",
        parse_mode="HTML"
    )


async def online_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    coc_name = storage.update_last_seen(user_id)
    if coc_name:
        await update.message.reply_text(
            f"✅ <b>{coc_name}</b>, твоя активность отмечена!",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "Ты ещё не зарегистрирован.\n"
            "Используй /register <имя в игре> чтобы привязать аккаунт."
        )


async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю список клана...")
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        members_sorted = sorted(
            clan.members,
            key=lambda m: (ROLE_ORDER.get(m.role.value, 9), m.name.lower())
        )

        # Group members by role (store full member objects)
        groups: dict[str, list] = defaultdict(list)
        for member in members_sorted:
            groups[member.role.value].append(member)

        image_buf = image_builder.build_team_image(clan.name, clan.member_count, groups)
        await msg.delete()
        await update.message.reply_photo(
            photo=image_buf,
            caption=f"🏰 <b>{clan.name}</b> · {clan.member_count}/50",
            parse_mode="HTML"
        )

    except coc.NotFound:
        await msg.edit_text("❌ Клан не найден. Проверь тег клана.")
    except Exception as e:
        logger.error(f"Ошибка при получении данных клана: {e}")
        await msg.edit_text("❌ Не удалось загрузить данные. Попробуй позже.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)


async def post_init(application):
    await coc_client.login(COC_EMAIL, COC_PASSWORD)
    logger.info("CoC клиент авторизован")


async def post_shutdown(application):
    await coc_client.close()


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("team", team_command))
    app.add_handler(CommandHandler("register", register_command))
    app.add_handler(CommandHandler("online", online_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
