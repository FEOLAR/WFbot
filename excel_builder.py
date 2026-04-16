import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

GREEN  = "FF92D050"
RED    = "FFFF0000"
ORANGE = "FFFFC000"
BLUE   = "FF4472C4"
GRAY   = "FFD9D9D9"
DARK   = "FF1F3864"
WHITE  = "FFFFFFFF"
YELLOW = "FFFFFF00"


def _hdr_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)


def _cell_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)


def _thin_border():
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)


def _header_cell(ws, row, col, value, bg=DARK, fg=WHITE, bold=True, wrap=True):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(bold=bold, color=fg, size=10)
    c.fill = _hdr_fill(bg)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=wrap)
    c.border = _thin_border()
    return c


def _data_cell(ws, row, col, value, bg=None, bold=False, align="center"):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(bold=bold, size=10)
    c.alignment = Alignment(horizontal=align, vertical="center")
    c.border = _thin_border()
    if bg:
        c.fill = _cell_fill(bg)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 1: КВ (last 5 regular wars)
# ─────────────────────────────────────────────────────────────────────────────

def build_kv_sheet(ws, war_history: list[dict]):
    ws.title = "КВ (Клановые войны)"

    wars = war_history[:5]
    n_wars = len(wars)

    # Row 1: Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2 + n_wars * 2)
    _header_cell(ws, 1, 1, "⚔ КЛАНОВЫЕ ВОЙНЫ — последние 5 КВ", bg=DARK)

    # Row 2: war headers (opponent | date)
    _header_cell(ws, 2, 1, "Игрок", bg=BLUE)
    _header_cell(ws, 2, 2, "TH", bg=BLUE)
    for i, war in enumerate(wars):
        col = 3 + i * 2
        result_emoji = {"win": "🏆", "lose": "❌", "tie": "🤝"}.get(war.get("result", ""), "")
        end = war.get("end_time", "")[:10]
        opp = war.get("opponent", "—")
        label = f"{result_emoji} vs {opp}\n{end}\n⭐{war['our_stars']} vs {war['their_stars']}"
        _header_cell(ws, 2, col,     label, bg=BLUE)
        _header_cell(ws, 2, col + 1, f"Атак\n({war.get('attacks_per_member', 2)})", bg=BLUE)

    # Gather all unique player names across wars
    all_players: dict[str, dict] = {}
    for war in wars:
        for m in war.get("members", []):
            name = m["name"]
            if name not in all_players:
                all_players[name] = {}

    row = 3
    for player_name, _ in sorted(all_players.items()):
        _data_cell(ws, row, 1, player_name, align="left")
        _data_cell(ws, row, 2, "—")  # TH level placeholder

        for i, war in enumerate(wars):
            col = 3 + i * 2
            members = {m["name"]: m for m in war.get("members", [])}
            apm = war.get("attacks_per_member", 2)
            if player_name in members:
                used = members[player_name]["attacks_used"]
                total = members[player_name]["attacks_max"]
                cell_val = f"{used}/{total}"
                if used == total:
                    bg = GREEN
                elif used == 0:
                    bg = RED
                else:
                    bg = ORANGE
                _data_cell(ws, row, col,     cell_val, bg=bg)
                _data_cell(ws, row, col + 1, "")
            else:
                _data_cell(ws, row, col,     "н/д",   bg=GRAY)
                _data_cell(ws, row, col + 1, "")
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 5
    for i in range(n_wars):
        ws.column_dimensions[get_column_letter(3 + i * 2)].width = 22
        ws.column_dimensions[get_column_letter(4 + i * 2)].width = 8

    ws.row_dimensions[2].height = 50
    ws.freeze_panes = "A3"


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 2: ЛВК (last CWL season rounds)
# ─────────────────────────────────────────────────────────────────────────────

def build_cwl_sheet(ws, cwl_history: dict):
    ws.title = "ЛВК (Лига войн клана)"

    season = cwl_history.get("season") or "—"
    rounds = cwl_history.get("rounds", [])
    n_rounds = len(rounds)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2 + n_rounds)
    _header_cell(ws, 1, 1, f"🏆 ЛИГА ВОЙН КЛАНА — сезон {season}", bg=DARK)

    _header_cell(ws, 2, 1, "Игрок", bg=BLUE)
    _header_cell(ws, 2, 2, "Всего атак", bg=BLUE)
    for i, rnd in enumerate(rounds):
        col = 3 + i
        opp = rnd.get("opponent", "—")
        label = f"Раунд {rnd['round']}\nvs {opp}\n⭐{rnd['our_stars']}:{rnd['their_stars']}"
        _header_cell(ws, 2, col, label, bg=BLUE)

    all_players: dict[str, list] = {}
    for rnd in rounds:
        for m in rnd.get("members", []):
            name = m["name"]
            if name not in all_players:
                all_players[name] = [False] * n_rounds

    for i, rnd in enumerate(rounds):
        for m in rnd.get("members", []):
            name = m["name"]
            if name in all_players:
                all_players[name][i] = m.get("attacked", False)

    row = 3
    for player_name in sorted(all_players.keys()):
        attacks = all_players[player_name]
        total = sum(1 for a in attacks if a)
        _data_cell(ws, row, 1, player_name, align="left")
        _data_cell(ws, row, 2, f"{total}/{n_rounds}",
                   bg=GREEN if total == n_rounds else (RED if total == 0 else ORANGE),
                   bold=True)
        for i, attacked in enumerate(attacks):
            col = 3 + i
            _data_cell(ws, row, col, "✅" if attacked else "❌",
                       bg=GREEN if attacked else RED)
        row += 1

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 12
    for i in range(n_rounds):
        ws.column_dimensions[get_column_letter(3 + i)].width = 18
    ws.row_dimensions[2].height = 50
    ws.freeze_panes = "A3"


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 3: Рейды столицы (last 2 raids, live from API)
# ─────────────────────────────────────────────────────────────────────────────

def build_raids_sheet(ws, raids: list):
    ws.title = "Рейды столицы"

    n = len(raids)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2 + n * 2)
    _header_cell(ws, 1, 1, "🏛 РЕЙДЫ СТОЛИЦЫ — последние 2 рейда", bg=DARK)

    _header_cell(ws, 2, 1, "Игрок", bg=BLUE)
    _header_cell(ws, 2, 2, "Лимит атак", bg=BLUE)

    for i, raid in enumerate(raids):
        col = 3 + i * 2
        start = raid.start_time.time.strftime("%d.%m.%Y") if raid.start_time else "—"
        loot = f"{raid.total_loot:,}".replace(",", " ")
        label = f"Рейд {i + 1}\n{start}\n💰 {loot}"
        _header_cell(ws, 2, col,     label, bg=BLUE)
        _header_cell(ws, 2, col + 1, "Золото", bg=BLUE)

    all_members: dict[str, dict] = {}
    for raid in raids:
        for m in raid.members:
            if m.name not in all_members:
                all_members[m.name] = {}

    row = 3
    for player_name in sorted(all_members.keys()):
        _data_cell(ws, row, 1, player_name, align="left")
        _data_cell(ws, row, 2, "—")

        for i, raid in enumerate(raids):
            col = 3 + i * 2
            member_map = {m.name: m for m in raid.members}
            if player_name in member_map:
                m = member_map[player_name]
                used = m.attack_count
                limit = m.attack_limit + m.bonus_attack_limit
                gold = m.capital_resources_looted
                used_pct = used / limit if limit else 0
                bg = GREEN if used == limit else (RED if used == 0 else ORANGE)
                _data_cell(ws, row, col,     f"{used}/{limit}", bg=bg)
                _data_cell(ws, row, col + 1, f"{gold:,}".replace(",", " "))
            else:
                _data_cell(ws, row, col,     "н/д", bg=GRAY)
                _data_cell(ws, row, col + 1, "—")
        row += 1

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 12
    for i in range(n):
        ws.column_dimensions[get_column_letter(3 + i * 2)].width = 14
        ws.column_dimensions[get_column_letter(4 + i * 2)].width = 14
    ws.row_dimensions[2].height = 50
    ws.freeze_panes = "A3"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_excel(war_history: list[dict], cwl_history: dict, raids: list) -> io.BytesIO:
    wb = openpyxl.Workbook()

    ws_kv = wb.active
    build_kv_sheet(ws_kv, war_history)

    ws_cwl = wb.create_sheet()
    build_cwl_sheet(ws_cwl, cwl_history)

    ws_raids = wb.create_sheet()
    build_raids_sheet(ws_raids, raids)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
