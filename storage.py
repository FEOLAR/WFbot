import json
import os
from datetime import datetime

DATA_FILE = "players.json"


def _load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def get_tg_username_map() -> dict[str, str]:
    """Returns {coc_name_lower: telegram_username} for players who linked their account."""
    data = _load()
    result = {}
    for entry in data.values():
        name = entry.get("coc_name", "")
        username = entry.get("telegram_username")
        if name and username:
            result[name.lower()] = username
    return result


def get_player_by_telegram(telegram_id: int) -> dict | None:
    data = _load()
    return data.get(str(telegram_id))
