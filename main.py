import os
import logging
from datetime import datetime
from collections import defaultdict
import coc
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand, MenuButtonCommands
)
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
        f"👋 Привет, <b>{name}</b>!\n\n"
        "🏰 <b>Добро пожаловать в бот клана Warfil</b>\n\n"
        "Я официальный бот клана <b>Warfil</b> в Clash of Clans.\n"
        "Вот что я умею:\n\n"
        "📋 <b>Список клана</b> — участники с уровнем ратуши и ролью\n"
        "📊 <b>Статистика</b> — активность и показатели игроков\n"
        "📝 <b>Анкеты</b> — заявки на вступление с сайта клана\n"
        "🔗 <b>Привязка аккаунтов</b> — CoC-ники с Telegram\n"
        "🔔 <b>Уведомления</b> — события в клане\n\n"
        "⬇️ Используй меню ниже для быстрого доступа к командам."
    )

    # Inline buttons (links)
    inline_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Сайт клана", url=CLAN_WEBSITE),
            InlineKeyboardButton("💬 Беседа клана", url=TG_GROUP_LINK),
        ]
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=inline_kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Команды бота Warfil</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📋 /team\n"
        "   Список всех участников клана с уровнем ратуши\n\n"
        "⚔️ /kv\n"
        "   Кто ещё не атаковал в текущей клановой войне\n\n"
        "🔗 /register &lt;ник в CoC&gt;\n"
        "   Привязать свой Telegram к нику в игре\n"
        "   <i>Пример: /register WarriorKing</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛡 <b>Команды администратора</b>\n\n"
        "🔗 /link @telegram НикВCoC\n"
        "   Привязать игрока к Telegram\n"
        "   <i>Пример: /link @feolar Fanon</i>\n\n"
        "❌ /unlink НикВCoC\n"
        "   Убрать привязку игрока\n\n"
        "📋 /links\n"
        "   Список всех привязок\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, parse_mode="HTML")


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


async def kv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю данные войны...")
    try:
        war = await coc_client.get_current_war(CLAN_TAG)

        if war is None or war.state == "notInWar":
            await msg.edit_text("🏳️ Клан сейчас не в клановой войне.")
            return

        if war.state == "preparation":
            end_time = war.start_time.time.strftime("%d.%m в %H:%M") if war.start_time else "скоро"
            await msg.edit_text(f"⚙️ Идёт подготовка к войне. Бой начнётся {end_time} (UTC).")
            return

        attacks_per_member = war.attacks_per_member or 2

        # Collect members who still have attacks left
        pending = []
        for member in war.clan.members:
            used = len(member.attacks) if member.attacks else 0
            remaining = attacks_per_member - used
            if remaining > 0:
                pending.append((member, used, remaining))

        # Sort: 0 attacks used first (most urgent), then 1 used
        pending.sort(key=lambda x: x[1])

        state_label = "⚔️ Война идёт" if war.state == "inWar" else "🏁 Война завершена"

        # Clan stars
        our_stars = war.clan.stars
        their_stars = war.opponent.stars
        stars_line = f"⭐ {our_stars}  vs  {their_stars} ⭐"

        # Time remaining
        time_str = ""
        if war.state == "inWar" and war.end_time:
            now = datetime.utcnow()
            diff = war.end_time.time - now
            total_sec = max(int(diff.total_seconds()), 0)
            h, m = divmod(total_sec // 60, 60)
            time_str = f"\n⏱ До конца войны: <b>{h}ч {m}мин</b>"

        lines = [
            f"<b>{state_label}</b>",
            f"🏰 <b>{war.clan.name}</b>  ⚔️  <b>{war.opponent.name}</b>",
            f"👥 {war.team_size} vs {war.team_size}   {stars_line}" + time_str,
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        if not pending:
            lines.append("✅ <b>Все игроки использовали свои атаки!</b>")
        else:
            # Split into groups: 0 attacks used and 1 attack used
            zero_used = [(m, r) for m, u, r in pending if u == 0]
            one_used  = [(m, r) for m, u, r in pending if u == 1]

            lines.append(f"⏳ <b>Не атаковали — {len(pending)} чел.</b>")

            tg_map = storage.get_tg_username_map()

            if zero_used:
                lines.append("")
                lines.append(f"🔴 <b>Нет атак ({len(zero_used)}):</b>")
                for member, _ in zero_used:
                    tg = tg_map.get(member.name.lower())
                    tg_str = f"  <i>@{tg}</i>" if tg else ""
                    lines.append(f"  • {member.name}{tg_str}")

            if one_used:
                lines.append("")
                lines.append(f"🟡 <b>Осталась 1 атака ({len(one_used)}):</b>")
                for member, _ in one_used:
                    tg = tg_map.get(member.name.lower())
                    tg_str = f"  <i>@{tg}</i>" if tg else ""
                    lines.append(f"  • {member.name}{tg_str}")

            lines.append("━━━━━━━━━━━━━━━━━━━━")

        await msg.edit_text("\n".join(lines), parse_mode="HTML")

    except coc.PrivateWarLog:
        await msg.edit_text("🔒 Журнал войны клана закрыт. Невозможно получить данные.")
    except coc.NotFound:
        await msg.edit_text("❌ Клан не найден.")
    except Exception as e:
        logger.error(f"Ошибка /kv: {e}")
        await msg.edit_text("❌ Не удалось загрузить данные войны. Попробуй позже.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Route reply-keyboard button presses to the right commands
    if text == "📋 Список клана":
        await team_command(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    elif text == "🔗 Привязать аккаунт":
        await update.message.reply_text(
            "Чтобы привязать свой аккаунт, напиши:\n"
            "/register &lt;твой ник в CoC&gt;\n\n"
            "<i>Пример: /register WarriorKing</i>",
            parse_mode="HTML"
        )
    else:
        pass  # ignore other text messages


async def post_init(application):
    await coc_client.login(COC_EMAIL, COC_PASSWORD)
    logger.info("CoC клиент авторизован")

    # Register bot commands (shown in Telegram command menu)
    await application.bot.set_my_commands([
        BotCommand("start",    "🏰 Главное меню"),
        BotCommand("team",     "📋 Список участников клана"),
        BotCommand("kv",       "⚔️ Атаки в клановой войне"),
        BotCommand("register", "🔗 Привязать свой аккаунт CoC"),
        BotCommand("help",     "❓ Помощь по командам"),
        BotCommand("link",     "🛡 [Адм] Привязать игрока к Telegram"),
        BotCommand("unlink",   "🛡 [Адм] Убрать привязку игрока"),
        BotCommand("links",    "🛡 [Адм] Список всех привязок"),
    ])
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Команды бота зарегистрированы")


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
    app.add_handler(CommandHandler("kv", kv_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("unlink", unlink_command))
    app.add_handler(CommandHandler("links", links_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
