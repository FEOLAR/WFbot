import os
import logging
from datetime import datetime
from collections import defaultdict
import coc
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
COC_EMAIL = os.environ["COC_EMAIL"]
COC_PASSWORD = os.environ["COC_PASSWORD"]
CLAN_TAG       = "#2R02GGRUJ"
CLAN_WEBSITE   = "https://www.warfilcoc.ru"
TG_GROUP_LINK  = "https://t.me/warfil_clan"   # ← замени на реальную ссылку беседы

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
    user = update.effective_user
    name = user.first_name or "боец"

    text = (
        f"👋 Привет, {name}!\n\n"
        "🏰 <b>Добро пожаловать в бот клана Warfil</b>\n\n"
        "Я официальный бот клана <b>Warfil</b> в Clash of Clans. Вот что я умею:\n\n"
        "📋 <b>Список клана</b> — показываю всех участников с уровнем ратуши и ролью\n"
        "📊 <b>Статистика</b> — слежу за активностью и показателями игроков\n"
        "📝 <b>Анкеты</b> — принимаю заявки на вступление с сайта клана\n"
        "🔗 <b>Привязка аккаунтов</b> — связываю CoC-ники с Telegram\n"
        "🔔 <b>Уведомления</b> — слежу за событиями в клане\n\n"
        "Используй /help чтобы увидеть все доступные команды."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Сайт клана", url=CLAN_WEBSITE),
            InlineKeyboardButton("💬 Беседа клана", url=TG_GROUP_LINK),
        ]
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/team — список участников клана\n"
        "/register <ник в игре> — привязать свой Telegram к нику в CoC\n"
        "    Пример: /register WarriorKing\n"
        "    После этого твой @username появится рядом с именем в /team\n\n"
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
    tg_username = update.effective_user.username
    storage.register_player(user_id, coc_name, tg_username)
    storage.update_last_seen(user_id)
    linked = f" (@{tg_username})" if tg_username else ""
    await update.message.reply_text(
        f"✅ Готово! Ты зарегистрирован как <b>{coc_name}</b>{linked}.\n"
        "Теперь ты будешь виден в /team со своим Telegram-ником.",
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

        ROLE_HEADERS = {
            "leader":   "👑 <b>Лидер</b>",
            "coLeader": "🔱 <b>Соруководители</b>",
            "admin":    "🌿 <b>Старейшины</b>",
            "member":   "🔹 <b>Участники</b>",
        }

        tg_map = storage.get_tg_username_map()

        lines = [
            f"🏰 <b>{clan.name}</b>  ·  👥 {clan.member_count}/50",
            "─────────────────────",
        ]

        for role_key in ["leader", "coLeader", "admin", "member"]:
            members = groups.get(role_key)
            if not members:
                continue
            lines.append("")
            lines.append(ROLE_HEADERS[role_key])
            for m in members:
                tg = tg_map.get(m.name.lower())
                tg_str = f"  <i>@{tg}</i>" if tg else ""
                lines.append(f"  ТХ{m.town_hall} │ {m.name}{tg_str}")

        await msg.edit_text("\n".join(lines), parse_mode="HTML")

    except coc.NotFound:
        await msg.edit_text("❌ Клан не найден. Проверь тег клана.")
    except Exception as e:
        logger.error(f"Ошибка при получении данных клана: {e}")
        await msg.edit_text("❌ Не удалось загрузить данные. Попробуй позже.")


async def _is_admin(update: Update) -> bool:
    """True if the sender is a group admin/creator, or if used in a private chat."""
    chat = update.effective_chat
    if chat.type == "private":
        return True
    member = await chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /link @tg_username Ник в CoC"""
    if not await _is_admin(update):
        await update.message.reply_text("❌ Только администраторы могут использовать эту команду.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /link @telegram НикВCoC\n"
            "Примеры:\n"
            "  /link @feolar Fanon\n"
            "  /link @feolar fil\n\n"
            "Один @telegram можно привязать к нескольким никам."
        )
        return

    tg_username = context.args[0].lstrip("@")
    coc_name = " ".join(context.args[1:])

    storage.link_player(coc_name, tg_username)
    await update.message.reply_text(
        f"✅ <b>{coc_name}</b> привязан к @{tg_username}",
        parse_mode="HTML"
    )


async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /unlink Ник в CoC"""
    if not await _is_admin(update):
        await update.message.reply_text("❌ Только администраторы могут использовать эту команду.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /unlink НикВCoC\nПример: /unlink Fanon")
        return

    coc_name = " ".join(context.args)
    removed = storage.unlink_player(coc_name)
    if removed:
        await update.message.reply_text(f"✅ Привязка для <b>{coc_name}</b> удалена.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ Привязка для <b>{coc_name}</b> не найдена.", parse_mode="HTML")


async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all current links (admin only)."""
    if not await _is_admin(update):
        await update.message.reply_text("❌ Только администраторы могут использовать эту команду.")
        return

    all_links = storage.get_all_links()
    if not all_links:
        await update.message.reply_text("Привязок пока нет. Используй /link @telegram НикВCoC")
        return

    lines = ["📋 <b>Текущие привязки:</b>", ""]
    for coc_name, tg_user in sorted(all_links.items(), key=lambda x: x[1]):
        lines.append(f"  {coc_name} → @{tg_user}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


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
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("unlink", unlink_command))
    app.add_handler(CommandHandler("links", links_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
