"""
app.py — Multi-Agent Task Planner (no external integrations)

Run (from repo root):
    pip install -r requirements.txt
    python planner/app.py

Or from this folder:
    pip install -r ../requirements.txt
    python app.py

Open: http://localhost:5000
Accounts and workspaces are persisted under planner/data/
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from flask import Flask, jsonify, render_template, request, session

sys.path.insert(0, str(Path(__file__).parent))

from taskdata import Task
from agents.user_agent import UserAgent
from agents.constraint_agent import ConstraintAgent
from agents.scheduler_agent import SchedulerAgent
from agents.validator_agent import ValidatorAgent
from persistence import (
    authenticate,
    display_name,
    flask_secret_key,
    load_workspace,
    normalize_username,
    register_user,
    save_workspace,
)

app = Flask(__name__)
app.secret_key = flask_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=60)


def _require_login(handler: Callable) -> Callable:
    @wraps(handler)
    def wrapped(*args: Any, **kwargs: Any):
        uid = session.get("uid")
        if not uid:
            return jsonify({"error": "Sign in required."}), 401
        return handler(*args, **kwargs)

    return wrapped


def _uid_workspace() -> Tuple[str, Dict[str, Any]]:
    uid = session.get("uid") or ""
    return uid, load_workspace(uid)


def _validate(body: dict) -> str:
    if not (body.get("name") or "").strip():
        return "Name is required."
    if not body.get("due_date"):
        return "Due date is required."
    try:
        date.fromisoformat(body["due_date"])
        h = float(body.get("estimated_hours", 2))
        assert h > 0
        d = int(body.get("difficulty", 3))
        assert 1 <= d <= 5
    except Exception:
        return "Invalid hours or difficulty."
    return ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session", methods=["GET"])
def session_info():
    if not session.get("uid"):
        return jsonify({"logged_in": False})
    key = session.get("username_key") or ""
    return jsonify(
        {"logged_in": True, "username": display_name(key) or key or "User"}
    )


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required."}), 400
    user = body.get("username") or ""
    pw = body.get("password") or ""
    uid, err = register_user(user, pw)
    if err:
        return jsonify({"error": err}), 400
    session.permanent = True
    session["uid"] = uid
    session["username_key"] = normalize_username(user)
    key = session.get("username_key") or ""
    label = display_name(key)
    return jsonify({"ok": True, "username": label or key or "User"})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required."}), 400
    uid, key, err = authenticate(body.get("username") or "", body.get("password") or "")
    if err or not uid:
        return jsonify({"error": err or "Invalid username or password."}), 401
    session.permanent = True
    session["uid"] = uid
    session["username_key"] = key
    uname = display_name(key)
    return jsonify({"ok": True, "username": uname or key or "User"})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/workspace", methods=["GET"])
@_require_login
def workspace_get():
    _, ws = _uid_workspace()
    return jsonify(ws)


@app.route("/api/tasks", methods=["GET"])
@_require_login
def get_tasks():
    _, ws = _uid_workspace()
    return jsonify(ws["tasks"])


@app.route("/api/tasks", methods=["POST"])
@_require_login
def add_task():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required."}), 400
    err = _validate(body)
    if err:
        return jsonify({"error": err}), 400

    uid, ws = _uid_workspace()
    task = {
        "id": str(uuid.uuid4()),
        "name": body["name"].strip(),
        "due_date": body["due_date"],
        "estimated_hours": float(body.get("estimated_hours", 2)),
        "difficulty": int(body.get("difficulty", 3)),
        "course": body.get("course", "").strip(),
    }
    ws["tasks"].append(task)
    ws["schedule"] = None
    save_workspace(uid, ws)
    return jsonify(task), 201


@app.route("/api/tasks/<tid>", methods=["DELETE"])
@_require_login
def delete_task(tid):
    uid, ws = _uid_workspace()
    ws["tasks"] = [t for t in ws["tasks"] if t["id"] != tid]
    ws["schedule"] = None
    save_workspace(uid, ws)
    return jsonify({"ok": True})


@app.route("/api/tasks/<tid>", methods=["PATCH"])
@_require_login
def update_task(tid):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required."}), 400
    err = _validate(body)
    if err:
        return jsonify({"error": err}), 400

    uid, ws = _uid_workspace()
    target = None
    for t in ws["tasks"]:
        if t.get("id") == tid:
            target = t
            break
    if target is None:
        return jsonify({"error": "Task not found."}), 404

    target["name"] = body["name"].strip()
    target["due_date"] = body["due_date"]
    target["estimated_hours"] = float(body.get("estimated_hours", target.get("estimated_hours", 2)))
    target["difficulty"] = int(body.get("difficulty", target.get("difficulty", 3)))
    target["course"] = (body.get("course", "") or "").strip()
    ws["schedule"] = None
    save_workspace(uid, ws)
    return jsonify(target)


@app.route("/api/tasks", methods=["DELETE"])
@_require_login
def clear_tasks():
    uid, ws = _uid_workspace()
    ws["tasks"] = []
    ws["schedule"] = None
    save_workspace(uid, ws)
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["PATCH"])
@_require_login
def patch_settings():
    """Optional: persist constraint fields between sessions."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required."}), 400
    uid, ws = _uid_workspace()
    settings = ws.setdefault("settings", {})
    if "start_date" in body and isinstance(body["start_date"], str):
        try:
            date.fromisoformat(body["start_date"])
            settings["start_date"] = body["start_date"].strip()
        except ValueError:
            return jsonify({"error": "Invalid start_date."}), 400
    if body.get("max_hours_per_day") is not None:
        try:
            mh = float(body["max_hours_per_day"])
            if mh <= 0:
                raise ValueError
            settings["max_hours_per_day"] = mh
        except (TypeError, ValueError):
            return jsonify({"error": "max_hours_per_day must be > 0."}), 400
    if body.get("task_sort_by") is not None:
        sb = str(body["task_sort_by"]).strip()
        allowed = {"due_date", "name", "estimated_hours", "difficulty", "course"}
        if sb not in allowed:
            return jsonify({"error": "Invalid task_sort_by."}), 400
        settings["task_sort_by"] = sb
    if body.get("task_sort_order") is not None:
        so = str(body["task_sort_order"]).strip()
        if so not in {"asc", "desc"}:
            return jsonify({"error": "Invalid task_sort_order."}), 400
        settings["task_sort_order"] = so
    save_workspace(uid, ws)
    return jsonify(settings)


@app.route("/api/schedule", methods=["POST"])
@_require_login
def schedule():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required (use application/json)."}), 400

    uid, ws = _uid_workspace()
    if not ws["tasks"]:
        return jsonify({"error": "Add at least one task first."}), 400

    try:
        ua = UserAgent(ws["tasks"], body)
        env, task_objs = ua.build()

        ca = ConstraintAgent(env)
        evaluated = ca.evaluate(task_objs)

        sa = SchedulerAgent(env)
        raw = sa.run(evaluated)

        va = ValidatorAgent(env)
        validation = va.validate(raw, evaluated, sa.unscheduled)

    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Scheduling failed: {str(e)}"}), 500

    days = []
    for d in sorted(raw):
        slots = raw[d]
        days.append({
            "date": d.isoformat(),
            "label": d.strftime("%A, %b %d").replace(" 0", " "),
            "total": round(sum(h for _, h in slots), 2),
            "slots": [
                {"name": t.name, "course": t.course, "hours": round(h, 2)}
                for t, h in slots
            ],
        })

    result = {
        "days": days,
        "unscheduled": [t.name for t in sa.unscheduled],
        "validation": validation,
        "log": ua.log + ca.log + sa.log + va.log,
    }

    mh = float(body.get("max_hours", ws.get("settings", {}).get("max_hours_per_day", 6)))
    try:
        start_d = date.fromisoformat(str(body.get("start_date") or ws.get("settings", {}).get("start_date", date.today().isoformat())))
    except ValueError:
        start_d = date.today()
    if start_d < date.today():
        start_d = date.today()

    ws["schedule"] = result
    st = ws.setdefault("settings", {})
    st["max_hours_per_day"] = mh
    st["start_date"] = start_d.isoformat()
    save_workspace(uid, ws)

    return jsonify(result)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print("\n  Task Planner → http://localhost:{}\n".format(port))
    app.run(debug=True, host=host, port=port)
