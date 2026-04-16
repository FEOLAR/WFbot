import json
import os

WAR_HISTORY_FILE = "war_history.json"
CWL_HISTORY_FILE = "cwl_history.json"

MAX_WAR_ENTRIES = 5


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Clan War (KV) history ─────────────────────────────────────────────────────

def save_war_result(end_time: str, opponent: str, result: str,
                    our_stars: int, their_stars: int,
                    team_size: int, attacks_per_member: int,
                    members: list[dict]):
    """Save a finished KV result. Keeps last MAX_WAR_ENTRIES entries."""
    history = _load_json(WAR_HISTORY_FILE) or []
    history.insert(0, {
        "end_time": end_time,
        "opponent": opponent,
        "result": result,
        "our_stars": our_stars,
        "their_stars": their_stars,
        "team_size": team_size,
        "attacks_per_member": attacks_per_member,
        "members": members,
    })
    history = history[:MAX_WAR_ENTRIES]
    _save_json(WAR_HISTORY_FILE, history)


def get_war_history() -> list[dict]:
    return _load_json(WAR_HISTORY_FILE) or []


# ── CWL history ───────────────────────────────────────────────────────────────

def save_cwl_round(season: str, round_num: int, opponent: str,
                   our_stars: int, their_stars: int,
                   members: list[dict]):
    """Append a finished CWL round to the current season's history."""
    data = _load_json(CWL_HISTORY_FILE) or {"season": season, "rounds": []}

    if data.get("season") != season:
        data = {"season": season, "rounds": []}

    data["rounds"].append({
        "round": round_num,
        "opponent": opponent,
        "our_stars": our_stars,
        "their_stars": their_stars,
        "members": members,
    })
    _save_json(CWL_HISTORY_FILE, data)


def get_cwl_history() -> dict:
    return _load_json(CWL_HISTORY_FILE) or {"season": None, "rounds": []}
