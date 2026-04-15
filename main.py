import os
import logging
import coc
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

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
ROLE_NAMES = {
    "leader": "👑 Лидер",
    "coLeader": "⭐ Со-лидер",
    "admin": "🔰 Старейшина",
    "member": "👤 Участник",
}

coc_client = coc.Client()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот клана @warfil_bot.\n\n"
        "Доступные команды:\n"
        "/team — список игроков клана\n"
        "/help — помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — начать\n"
        "/team — список игроков клана\n"
        "/help — помощь"
    )


async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю список игроков...")
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        members = sorted(clan.members, key=lambda m: (ROLE_ORDER.get(m.role.value, 9), -m.trophies))

        lines = [f"🏰 <b>{clan.name}</b> ({clan.tag})", f"👥 Участников: {clan.member_count}/50\n"]

        current_role = None
        for i, member in enumerate(members, 1):
            role_key = member.role.value
            role_label = ROLE_NAMES.get(role_key, "👤 Участник")
            if role_key != current_role:
                current_role = role_key
                lines.append(f"\n{role_label}:")
            lines.append(f"  {i}. {member.name} — 🏆 {member.trophies}")

        await msg.edit_text("\n".join(lines), parse_mode="HTML")
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
