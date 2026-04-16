import json
import os
from datetime import datetime

DATA_FILE        = "players.json"
LINKS_FILE       = "links.json"
NOTIFY_CHAT_FILE = "notify_chat.json"


# ── Internal helpers ────────────────────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_links() -> dict:
    """links.json: {coc_name_lower: tg_username}"""
    if not os.path.exists(LINKS_FILE):
        return {}
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_links(data: dict):
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Self-registration (player-facing) ───────────────────────────────────────

def register_player(telegram_id: int, coc_name: str, telegram_username: str | None = None):
    data = _load()
    key = str(telegram_id)
    existing_last_seen = data.get(key, {}).get("last_seen")
    data[key] = {
        "coc_name": coc_name,
        "telegram_username": telegram_username,
        "last_seen": existing_last_seen,
    }
    _save(data)


def update_last_seen(telegram_id: int):
    data = _load()
    key = str(telegram_id)
    if key in data:
        data[key]["last_seen"] = datetime.now().isoformat()
        _save(data)
        return data[key]["coc_name"]
    return None


def get_last_seen_map() -> dict[str, str]:
    """Returns {coc_name_lower: last_seen_str}"""
    data = _load()
    result = {}
    for entry in data.values():
        name = entry.get("coc_name", "")
        last_seen = entry.get("last_seen")
        if name:
            result[name.lower()] = last_seen
    return result


def get_player_by_telegram(telegram_id: int) -> dict | None:
    data = _load()
    return data.get(str(telegram_id))


# ── Admin-managed links ──────────────────────────────────────────────────────

def link_player(coc_name: str, tg_username: str):
    """Link a CoC player name to a Telegram username (admin action)."""
    links = _load_links()
    links[coc_name.lower()] = tg_username.lstrip("@")
    _save_links(links)


def unlink_player(coc_name: str) -> bool:
    """Remove link for a CoC player. Returns True if it existed."""
    links = _load_links()
    key = coc_name.lower()
    if key in links:
        del links[key]
        _save_links(links)
        return True
    return False


def get_all_links() -> dict[str, str]:
    """Returns {coc_name_lower: tg_username} from admin links."""
    return _load_links()


# ── Combined map (used by /team) ─────────────────────────────────────────────

def get_tg_username_map() -> dict[str, str]:
    """Merged {coc_name_lower: tg_username} from both self-registration and admin links.
    Admin links take priority."""
    # Self-registered players
    data = _load()
    result = {}
    for entry in data.values():
        name = entry.get("coc_name", "")
        username = entry.get("telegram_username")
        if name and username:
            result[name.lower()] = username

    # Admin links override / supplement
    result.update(_load_links())
    return result


# ── War notification chat ─────────────────────────────────────────────────────

def save_notify_chat(chat_id: int):
    with open(NOTIFY_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump({"chat_id": chat_id}, f)


def get_notify_chat() -> int | None:
    if not os.path.exists(NOTIFY_CHAT_FILE):
        return None
    with open(NOTIFY_CHAT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("chat_id")


# ── War state persistence (for transition detection across restarts) ───────────

WAR_STATE_FILE = "war_state.json"


def save_war_state(state: str):
    with open(WAR_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"state": state}, f)


def get_war_state() -> str | None:
    if not os.path.exists(WAR_STATE_FILE):
        return None
    try:
        with open(WAR_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("state")
    except (json.JSONDecodeError, KeyError):
        return None
