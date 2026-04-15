import io
import os
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

TH_IMAGES_DIR = "th_images"

BG_COLOR = (15, 15, 25)
HEADER_BG = (24, 24, 40)
ROLE_COLORS = {
    "leader":   (255, 200, 50),
    "coLeader": (180, 100, 255),
    "admin":    (80, 200, 120),
    "member":   (100, 160, 255),
}
ROLE_NAMES = {
    "leader":   "👑  ЛИДЕР",
    "coLeader": "🔱  СОРУКОВОДИТЕЛИ",
    "admin":    "🌿  СТАРЕЙШИНЫ",
    "member":   "🔹  УЧАСТНИКИ",
}
ROLE_ORDER = ["leader", "coLeader", "admin", "member"]

_th_cache: dict[int, Image.Image] = {}


def _load_th_image(level: int, size: int) -> Image.Image | None:
    if level in _th_cache:
        return _th_cache[level]
    path = os.path.join(TH_IMAGES_DIR, f"th{level}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    _th_cache[level] = img
    return img


def build_team_image(clan_name: str, member_count: int, groups: dict) -> io.BytesIO:
    IMG_W = 600
    PAD = 18
    TH_SIZE = 64
    ROW_H = 78
    ROLE_H = 40
    HEADER_H = 72

    total_members = sum(len(groups.get(r, [])) for r in ROLE_ORDER)
    total_role_bars = sum(1 for r in ROLE_ORDER if groups.get(r))
    total_h = HEADER_H + total_role_bars * ROLE_H + total_members * ROW_H + PAD

    img = Image.new("RGB", (IMG_W, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(FONT_BOLD, 24)
        f_sub = ImageFont.truetype(FONT_REGULAR, 13)
        f_role = ImageFont.truetype(FONT_BOLD, 15)
        f_name = ImageFont.truetype(FONT_BOLD, 18)
        f_th = ImageFont.truetype(FONT_REGULAR, 13)
    except Exception:
        f_title = f_sub = f_role = f_name = f_th = ImageFont.load_default()

    # ── Header ──────────────────────────────────────────────
    draw.rectangle([0, 0, IMG_W, HEADER_H], fill=HEADER_BG)
    # gold accent bar on left
    draw.rectangle([0, 0, 5, HEADER_H], fill=(255, 200, 50))
    draw.text((PAD + 8, 13), clan_name, font=f_title, fill=(255, 215, 50))
    draw.text((PAD + 8, 46), f"Участники клана: {member_count}/50", font=f_sub, fill=(150, 150, 180))

    y = HEADER_H

    for role_key in ROLE_ORDER:
        members = groups.get(role_key)
        if not members:
            continue

        color = ROLE_COLORS[role_key]
        label = ROLE_NAMES[role_key]

        # ── Role bar ────────────────────────────────────────
        draw.rectangle([0, y, IMG_W, y + ROLE_H], fill=(22, 22, 36))
        draw.rectangle([0, y, 4, y + ROLE_H], fill=color)
        draw.text((PAD + 8, y + 12), label, font=f_role, fill=color)
        y += ROLE_H

        for idx, member in enumerate(members):
            th_level = member.town_hall
            row_bg = (18, 18, 30) if idx % 2 == 0 else (21, 21, 34)
            draw.rectangle([0, y, IMG_W, y + ROW_H], fill=row_bg)

            # TH image
            th_img = _load_th_image(th_level, TH_SIZE)
            th_x = PAD
            th_y = y + (ROW_H - TH_SIZE) // 2
            if th_img:
                img.paste(th_img, (th_x, th_y), th_img)
            else:
                draw.text((th_x + 4, th_y + 20), f"TH{th_level}", font=f_th, fill=(180, 180, 180))

            # Player name
            name_x = PAD + TH_SIZE + 14
            name_y = y + (ROW_H // 2) - 16
            draw.text((name_x, name_y), member.name, font=f_name, fill=(230, 230, 240))
            draw.text((name_x, name_y + 26), f"Ратуша {th_level}", font=f_th, fill=(110, 110, 150))

            # Thin separator line
            draw.line([(PAD, y + ROW_H - 1), (IMG_W - PAD, y + ROW_H - 1)], fill=(28, 28, 45), width=1)

            y += ROW_H

    # ── Footer line ─────────────────────────────────────────
    draw.rectangle([0, total_h - 3, IMG_W, total_h], fill=(255, 200, 50))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
