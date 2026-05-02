"""
File-backed accounts and per-user task/schedule workspaces.

Stored under planner/data/ (ignored by git). Passwords hashed via werkzeug.security.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from werkzeug.security import check_password_hash, generate_password_hash

DATA_DIR = Path(__file__).resolve().parent / "data"
USERDATA_DIR = DATA_DIR / "userdata"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
SECRET_FILE = DATA_DIR / ".session_secret"

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")

Workspace = Dict[str, Any]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USERDATA_DIR.mkdir(parents=True, exist_ok=True)


def flask_secret_key() -> str:
    """Stable secret across restarts so session cookies survive dev server reloads."""
    env = os.environ.get("FLASK_SECRET_KEY")
    if env:
        return env
    ensure_dirs()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    from secrets import token_hex

    key = token_hex(32)
    SECRET_FILE.write_text(key + "\n", encoding="utf-8")
    return key


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, data: Any) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_accounts() -> Dict[str, Any]:
    ensure_dirs()
    raw = _read_json(ACCOUNTS_FILE, {})
    raw.setdefault("users", {})
    return raw


def save_accounts(acc: Dict[str, Any]) -> None:
    _atomic_write_json(ACCOUNTS_FILE, acc)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> Tuple[bool, str]:
    s = username.strip()
    if not _USERNAME_RE.fullmatch(s):
        return False, "Username must be 3–32 characters (letters, numbers, underscores)."
    return True, ""


def userdata_path(uid: str) -> Path:
    return USERDATA_DIR / f"{uid}.json"


def default_workspace() -> Workspace:
    return {"tasks": [], "schedule": None, "settings": {}}


def load_workspace(uid: str) -> Workspace:
    ensure_dirs()
    p = userdata_path(uid)
    empty = default_workspace()
    if not p.exists():
        _atomic_write_json(p, empty)
        return dict(empty)
    data = _read_json(p, {})
    merged: Workspace = dict(empty)
    merged["tasks"] = data.get("tasks") if isinstance(data.get("tasks"), list) else []
    merged["schedule"] = data.get("schedule")
    settings = data.get("settings")
    merged["settings"] = settings if isinstance(settings, dict) else {}
    return merged


def save_workspace(uid: str, ws: Workspace) -> None:
    _atomic_write_json(userdata_path(uid), ws)


def register_user(username: str, password: str) -> Tuple[Optional[str], str]:
    """Returns (user_id, error_message). user_id is set when error is empty."""
    ok, msg = validate_username(username)
    if not ok:
        return None, msg
    if len(password) < 6:
        return None, "Password must be at least 6 characters."
    key = normalize_username(username)
    acc = load_accounts()
    users = acc["users"]
    if key in users:
        return None, "That username is already taken."
    uid = str(uuid.uuid4())
    users[key] = {
        "uid": uid,
        "password_hash": generate_password_hash(password),
        "display": username.strip(),
    }
    save_accounts(acc)
    save_workspace(uid, default_workspace())
    return uid, ""


def authenticate(username: str, password: str) -> Tuple[Optional[str], str, str]:
    """Returns (uid, username_key, error). uid is None on failure."""
    key = normalize_username(username)
    if not key:
        return None, "", "Invalid username or password."
    acc = load_accounts()
    row = acc.get("users", {}).get(key)
    if not row or not check_password_hash(row["password_hash"], password):
        return None, "", "Invalid username or password."
    uid = row.get("uid")
    if not uid:
        uid = str(uuid.uuid4())
        row["uid"] = uid
        save_accounts(acc)
        if not userdata_path(uid).exists():
            save_workspace(uid, default_workspace())
    return uid, key, ""


def display_name(username_key: str) -> Optional[str]:
    acc = load_accounts()
    row = acc.get("users", {}).get(username_key)
    if not row:
        return None
    return row.get("display") or username_key
