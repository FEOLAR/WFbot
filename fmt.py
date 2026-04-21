"""
Единая система форматирования сообщений бота Warfil.
Оптимизировано под мобильный Telegram (ширина ~30 символов).
"""

DIV  = "━━━━━━━━━━━━━━━━━━━━"   # основной разделитель
DIVs = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─"  # тонкий разделитель
BULL = "▸"                       # буллет


def header(icon: str, title: str) -> str:
    """Строка-заголовок блока."""
    return f"{icon} <b>{title}</b>"


def clan_header(extra: str = "") -> str:
    """Стандартная шапка с именем клана."""
    base = "🏰 <b>WARFIL</b>"
    return f"{base}  ·  {extra}" if extra else base


def section(icon: str, title: str) -> str:
    return f"\n{icon} <b>{title}</b>"


def member_line(name: str, th: int | None = None, tg: str | None = None) -> str:
    th_part = f"ТХ{th}" if th else ""
    tg_part = f"  <i>@{tg}</i>" if tg else ""
    if th_part:
        return f"  {BULL} {th_part} · {name}{tg_part}"
    return f"  {BULL} {name}{tg_part}"


def ok(text: str) -> str:
    return f"✅ {text}"


def err(text: str) -> str:
    return f"❌ {text}"


def warn(text: str) -> str:
    return f"⚠️ {text}"


def footer() -> str:
    return f"\n{DIVs}\n🌐 <i>warfilcoc.ru</i>"
