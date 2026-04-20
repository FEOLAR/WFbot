import io
import asyncio
import httpx
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H = 1280, 720

# Palette
C_WHITE   = (255, 255, 255, 255)
C_GRAY    = (170, 170, 170, 255)
C_DARK    = (12,  16,  30,  255)
C_GOLD    = (255, 200,  50, 255)
C_GREEN   = ( 80, 200, 100, 255)
C_RED     = (220,  70,  70, 255)
C_ORANGE  = (240, 155,  50, 255)
C_BLUE    = ( 80, 160, 230, 255)
C_PURPLE  = (150,  80, 220, 255)
C_PANEL   = (  0,  10,  30, 175)
C_PANEL2  = (  0,  10,  30, 210)

TH_COLORS = {
    18: (220, 170, 40),
    17: (180, 100, 220),
    16: (80,  160, 230),
    15: (80,  200, 100),
    14: (240, 155,  50),
    13: (200,  80,  80),
    12: (140, 140, 140),
    11: (100, 100, 100),
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def _panel(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color=C_PANEL, r=14):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=color)


def _bar(draw, x, y, w, h, fill_ratio, bg=(50, 50, 70, 200), fg=None):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    if fill_ratio > 0 and fg:
        fw = max(h, int(w * fill_ratio))
        draw.rounded_rectangle([x, y, x + fw, y + h], radius=h // 2, fill=fg)


def _txt(draw, x, y, text, size=16, bold=False, color=C_WHITE, anchor="la"):
    draw.text((x, y), text, font=_font(size, bold), fill=color, anchor=anchor)


async def _dl_image(url: str, size: tuple | None = None) -> Image.Image | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            if size:
                img = img.resize(size, Image.LANCZOS)
            return img
    except Exception:
        return None


async def build_card(clan, raids=None, background_path: str | None = None) -> io.BytesIO:
    # ── Background ──────────────────────────────────────────────────────────
    if background_path:
        try:
            bg = Image.open(background_path).convert("RGBA").resize((W, H), Image.LANCZOS)
        except Exception:
            bg = Image.new("RGBA", (W, H), C_DARK)
    else:
        bg = Image.new("RGBA", (W, H), C_DARK)
        # Subtle gradient-like dark overlay
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for i in range(H):
            alpha = int(60 * (1 - i / H))
            gd.line([(0, i), (W, i)], fill=(20, 10, 40, alpha))
        bg = Image.alpha_composite(bg, grad)

    # Semi-transparent overlay to darken background for readability
    overlay = Image.new("RGBA", (W, H), (0, 5, 20, 140))
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg, "RGBA")

    # ────────────────────────────────────────────────────────────────────────
    # LEFT COLUMN  (x: 15 → 410)
    # ────────────────────────────────────────────────────────────────────────
    LX = 15

    # ── Clan badge ──────────────────────────────────────────────────────────
    BADGE_SZ = 100
    badge_img = None
    if clan.badge and clan.badge.large:
        badge_img = await _dl_image(clan.badge.large, size=(BADGE_SZ, BADGE_SZ))
    if badge_img:
        bg.paste(badge_img, (LX, 15), badge_img)

    # Clan level circle on top of badge
    lv_x, lv_y = LX + BADGE_SZ // 2, 15 + BADGE_SZ - 14
    draw.ellipse([lv_x - 16, lv_y - 14, lv_x + 16, lv_y + 14], fill=(60, 20, 100, 230))
    _txt(draw, lv_x, lv_y, str(clan.level), size=14, bold=True, color=C_GOLD, anchor="mm")

    # Clan name + tag + type
    nx = LX + BADGE_SZ + 14
    _txt(draw, nx, 18,  clan.name,  size=30, bold=True, color=C_WHITE)
    _txt(draw, nx, 55,  f"#{clan.tag.lstrip('#')}  ·  {clan.type or 'open'}",
         size=14, color=C_GRAY)
    desc = clan.description or ""
    desc_short = desc[:70] + ("..." if len(desc) > 70 else "")
    _txt(draw, nx, 76,  desc_short, size=12, color=(160, 160, 160, 220))

    # ── Members + donations ──────────────────────────────────────────────────
    _panel(draw, LX, 130, 400, 190)
    _txt(draw, LX + 14, 140, "Участники",  size=12, color=C_GRAY)
    _txt(draw, LX + 14, 158, str(clan.member_count), size=26, bold=True, color=C_WHITE)
    _txt(draw, LX + 90, 140, "Пожертвования (отдано / получено)", size=12, color=C_GRAY)
    members_list = list(clan.members or [])
    total_given    = sum(m.donations for m in members_list)
    total_received = sum(m.received  for m in members_list)
    _txt(draw, LX + 90, 158,
         f"{total_given:,} / {total_received:,}".replace(",", " "),
         size=20, bold=True, color=C_GOLD)

    # ── TH distribution ─────────────────────────────────────────────────────
    ths = Counter(m.town_hall for m in members_list)
    _panel(draw, LX, 200, 400, 560)
    _txt(draw, LX + 14, 208, "Состав по ратушам", size=13, bold=True, color=C_GOLD)

    y_th = 232
    bar_w = 215
    max_count = max(ths.values()) if ths else 1
    total_m = clan.member_count or 1

    for th in sorted(ths.keys(), reverse=True):
        count = ths[th]
        pct   = count / total_m * 100
        ratio = count / max_count
        fg    = TH_COLORS.get(th, (120, 120, 120)) + (220,)

        _txt(draw, LX + 14, y_th, f"TH{th}", size=13, bold=True, color=C_WHITE)
        _bar(draw, LX + 70, y_th + 3, bar_w, 14, ratio, fg=fg)
        _txt(draw, LX + 294, y_th, f"{count} / {pct:.0f}%", size=12, color=C_GRAY)
        y_th += 34

    # ── Required trophies ───────────────────────────────────────────────────
    _panel(draw, LX, 570, 400, 710)
    _txt(draw, LX + 14, 578, "Требования · Мин. трофеев", size=12, color=C_GRAY)
    _txt(draw, LX + 14, 598, str(clan.required_trophies or 0),
         size=28, bold=True, color=C_GOLD)
    _txt(draw, LX + 150, 578, "Мин. трофеев BB", size=12, color=C_GRAY)
    _txt(draw, LX + 150, 598,
         str(getattr(clan, "required_builder_base_trophies", 0) or 0),
         size=28, bold=True, color=C_BLUE)

    # ────────────────────────────────────────────────────────────────────────
    # MIDDLE COLUMN  (x: 420 → 700)
    # ────────────────────────────────────────────────────────────────────────
    MX = 420

    # ── War Frequency ───────────────────────────────────────────────────────
    _panel(draw, MX, 15, 700, 90)
    _txt(draw, MX + 14, 22, "War Frequency", size=12, color=C_GRAY)
    freq = str(clan.war_frequency or "always")
    fc = C_GREEN if freq == "always" else C_ORANGE if freq == "moreThanOncePerWeek" else C_RED
    _txt(draw, MX + 14, 42, freq, size=20, bold=True, color=fc)

    # ── War Stats ───────────────────────────────────────────────────────────
    wins   = clan.war_wins   or 0
    losses = clan.war_losses or 0
    ties   = clan.war_ties   or 0
    total_wars = wins + losses + ties

    _panel(draw, MX, 100, 700, 350)
    _txt(draw, MX + 14, 108, "War Stats", size=12, color=C_GRAY)

    _txt(draw, MX + 14, 130, str(wins),   size=44, bold=True, color=C_GREEN)
    _txt(draw, MX + 120, 130, str(losses), size=44, bold=True, color=C_RED)
    _txt(draw, MX + 14,  178, "побед",     size=12, color=C_GRAY)
    _txt(draw, MX + 120, 178, "поражений", size=12, color=C_GRAY)
    if ties:
        _txt(draw, MX + 220, 130, str(ties),   size=28, bold=True, color=C_ORANGE)
        _txt(draw, MX + 220, 165, "ничьих",    size=12, color=C_GRAY)

    # Win rate bar
    if total_wars:
        wr = wins / total_wars
        _txt(draw, MX + 14, 200, f"Винрейт: {wr*100:.1f}%", size=13, color=C_GRAY)
        _bar(draw, MX + 14, 220, 262, 14, wr,
             bg=(180, 60, 60, 160), fg=(80, 200, 100, 220))

    # Recent war dots (last 10 simplified)
    dot_x = MX + 14
    dot_y = 246
    remaining = 10
    for color, cnt in [(C_GREEN, wins), (C_ORANGE, ties), (C_RED, losses)]:
        for _ in range(min(cnt, remaining)):
            draw.ellipse([dot_x, dot_y, dot_x + 14, dot_y + 14], fill=color)
            dot_x += 18
            remaining -= 1
            if remaining <= 0:
                break
        if remaining <= 0:
            break

    # ── CWL League ──────────────────────────────────────────────────────────
    _panel(draw, MX, 360, 700, 460)
    _txt(draw, MX + 14, 368, "Clan War League", size=12, color=C_GRAY)
    cwl_name = str(clan.war_league or "—")
    _txt(draw, MX + 14, 390, cwl_name, size=18, bold=True, color=C_PURPLE)

    # ── Capital League ──────────────────────────────────────────────────────
    _panel(draw, MX, 470, 700, 570)
    _txt(draw, MX + 14, 478, "Capital League", size=12, color=C_GRAY)
    cap_lg = str(getattr(clan, "capital_league", None) or "—")
    _txt(draw, MX + 14, 498, cap_lg, size=18, bold=True, color=C_GOLD)

    # ── Description ─────────────────────────────────────────────────────────
    _panel(draw, MX, 580, 700, 710)
    _txt(draw, MX + 14, 588, "Описание клана", size=12, color=C_GRAY)
    desc_lines = []
    words = (clan.description or "Без описания").split()
    line = ""
    for w in words:
        if len(line + " " + w) <= 32:
            line = (line + " " + w).strip()
        else:
            desc_lines.append(line)
            line = w
        if len(desc_lines) >= 4:
            break
    if line and len(desc_lines) < 4:
        desc_lines.append(line)
    for i, dl in enumerate(desc_lines[:4]):
        _txt(draw, MX + 14, 608 + i * 22, dl, size=13, color=C_WHITE)

    # ────────────────────────────────────────────────────────────────────────
    # RIGHT COLUMN  (x: 715 → 1265)
    # ────────────────────────────────────────────────────────────────────────
    RX = 715

    # ── Raids League + loot ─────────────────────────────────────────────────
    _panel(draw, RX, 15, RX + 260, 165)
    _txt(draw, RX + 14, 22, "Raids League", size=12, color=C_GRAY)
    _txt(draw, RX + 14, 42, cap_lg, size=16, bold=True, color=C_GOLD)
    # Latest raid loot
    if raids:
        loot = getattr(raids[0], "total_loot", 0) or 0
        _txt(draw, RX + 14, 76, "Последний рейд:", size=12, color=C_GRAY)
        _txt(draw, RX + 14, 96, f"{loot:,}".replace(",", " ") + " зол.", size=18, bold=True, color=C_WHITE)

    # ── Capital Peak ────────────────────────────────────────────────────────
    _panel(draw, RX + 275, 15, RX + 550, 165)
    _txt(draw, RX + 289, 22, "Capital Peak", size=12, color=C_GRAY)
    cap_hal = getattr(getattr(clan, "clan_capital", None), "capital_hall_level", None)
    _txt(draw, RX + 289, 42, f"Ур. {cap_hal}" if cap_hal else "Данные недоступны",
         size=16, bold=True, color=C_WHITE)

    # Members in raids
    if raids and raids[0]:
        r0_members = list(getattr(raids[0], "members", None) or [])
        _txt(draw, RX + 289, 76, f"Участников: {len(r0_members)}", size=13, color=C_GRAY)

    # ── Raids Results ───────────────────────────────────────────────────────
    _panel(draw, RX, 175, RX + 550, 420)
    _txt(draw, RX + 14, 182, "Raids Results", size=13, bold=True, color=C_GOLD)

    if raids:
        y_r = 208
        for i, r in enumerate(raids[:4]):
            try:
                start = r.start_time.time.strftime("%d.%m.%Y")
            except Exception:
                start = "—"
            loot   = getattr(r, "total_loot", 0) or 0
            r_mems = list(getattr(r, "members", None) or [])
            _txt(draw, RX + 14, y_r,
                 f"{start}   {loot:,}".replace(",", " ") + f"   ({len(r_mems)} уч.)",
                 size=15, bold=(i == 0), color=C_WHITE if i == 0 else C_GRAY)
            y_r += 40
    else:
        _txt(draw, RX + 14, 210, "Нет данных по рейдам", size=14, color=C_GRAY)

    # ── War log note ────────────────────────────────────────────────────────
    _panel(draw, RX, 430, RX + 550, 560)
    _txt(draw, RX + 14, 438, "Клановые войны — итого", size=12, color=C_GRAY)
    _txt(draw, RX + 14, 460,
         f"Победы: {wins}   Поражения: {losses}   Ничьи: {ties}",
         size=15, bold=True, color=C_WHITE)
    if total_wars:
        _txt(draw, RX + 14, 490,
             f"Всего войн: {total_wars}   Винрейт: {wins/total_wars*100:.1f}%",
             size=14, color=C_GRAY)

    # ── Bottom watermark ────────────────────────────────────────────────────
    _panel(draw, RX, 570, RX + 550, 710)
    _txt(draw, RX + 14, 580, "Warfil Bot  ·  warfilcoc.ru", size=14, color=C_GRAY)
    _txt(draw, RX + 14, 605,
         f"Обновлено: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}",
         size=13, color=(120, 120, 120, 200))

    # ── Convert & return ────────────────────────────────────────────────────
    final = bg.convert("RGB")
    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
