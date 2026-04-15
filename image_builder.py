import io
import os
import httpx
from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG_COLOR = (18, 18, 30)
ROLE_COLORS = {
    "leader":   (255, 200, 50),
    "coLeader": (180, 100, 255),
    "admin":    (80, 200, 120),
    "member":   (80, 150, 255),
}
ROLE_NAMES = {
    "leader":   "👑 ЛИДЕР",
    "coLeader": "🔱 СОРУКОВОДИТЕЛИ",
    "admin":    "🌿 СТАРЕЙШИНЫ",
    "member":   "🔹 УЧАСТНИКИ",
}

TH_IMAGE_CACHE: dict[int, Image.Image] = {}


async def _download_image(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def preload_th_images(bot, sticker_set_name: str = "TownhallsJora"):
    global TH_IMAGE_CACHE
    if TH_IMAGE_CACHE:
        return
    ss = await bot.get_sticker_set(sticker_set_name)
    for th_level, sticker in enumerate(ss.stickers, start=1):
        if th_level > 17:
            break
        file = await bot.get_file(sticker.file_id)
        data = await _download_image(file.file_path)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img = img.resize((72, 72), Image.LANCZOS)
        TH_IMAGE_CACHE[th_level] = img


def get_th_image(level: int) -> Image.Image | None:
    return TH_IMAGE_CACHE.get(level)


def build_team_image(clan_name: str, member_count: int, groups: dict) -> io.BytesIO:
    ROLE_ORDER = ["leader", "coLeader", "admin", "member"]
    IMG_WIDTH = 580
    PAD = 16
    TH_SIZE = 72
    ROW_H = 80
    ROLE_H = 44
    HEADER_H = 70

    # Calculate total height
    total_rows = sum(len(groups.get(r, [])) for r in ROLE_ORDER)
    total_roles = sum(1 for r in ROLE_ORDER if groups.get(r))
    total_h = HEADER_H + PAD + total_roles * ROLE_H + total_rows * ROW_H + PAD * 2

    img = Image.new("RGBA", (IMG_WIDTH, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype(FONT_BOLD, 26)
        font_role = ImageFont.truetype(FONT_BOLD, 18)
        font_name = ImageFont.truetype(FONT_REGULAR, 20)
        font_sub = ImageFont.truetype(FONT_REGULAR, 14)
    except Exception:
        font_big = font_role = font_name = font_sub = ImageFont.load_default()

    # Header
    draw.rectangle([0, 0, IMG_WIDTH, HEADER_H], fill=(28, 28, 48))
    draw.text((PAD, 12), clan_name, font=font_big, fill=(255, 215, 50))
    draw.text((PAD, 44), f"👥 {member_count}/50 участников", font=font_sub, fill=(180, 180, 200))

    y = HEADER_H + PAD

    for role_key in ROLE_ORDER:
        members = groups.get(role_key)
        if not members:
            continue

        role_color = ROLE_COLORS.get(role_key, (180, 180, 180))
        role_label = ROLE_NAMES.get(role_key, role_key)

        # Role header bar
        draw.rectangle([0, y, IMG_WIDTH, y + ROLE_H], fill=(30, 30, 50))
        draw.rectangle([0, y, 4, y + ROLE_H], fill=role_color)
        draw.text((PAD + 6, y + 12), role_label, font=font_role, fill=role_color)
        y += ROLE_H

        for member in members:
            th_level = member.town_hall
            th_img = get_th_image(th_level)

            # Row background (alternating subtle)
            row_bg = (22, 22, 38) if members.index(member) % 2 == 0 else (26, 26, 42)
            draw.rectangle([0, y, IMG_WIDTH, y + ROW_H], fill=row_bg)

            # TH image
            if th_img:
                img.paste(th_img, (PAD, y + (ROW_H - TH_SIZE) // 2), th_img)

            # Player name
            name_x = PAD + TH_SIZE + 12
            draw.text((name_x, y + 18), member.name, font=font_name, fill=(230, 230, 240))
            draw.text((name_x, y + 44), f"ТХ{th_level}", font=font_sub, fill=(120, 120, 160))

            y += ROW_H

    # Bottom padding
    draw.rectangle([0, total_h - 4, IMG_WIDTH, total_h], fill=(28, 28, 48))

    buf = io.BytesIO()
    img = img.convert("RGB")
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
