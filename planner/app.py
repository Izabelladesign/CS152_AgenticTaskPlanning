"""
app.py — Multi-Agent Task Planner (no external integrations)

Run:
    pip install flask
    python app.py

Open: http://localhost:5000
"""

import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).parent))

from taskdata import Task
from agents.user_agent import UserAgent
from agents.constraint_agent import ConstraintAgent
from agents.scheduler_agent import SchedulerAgent
from agents.validator_agent import ValidatorAgent

app = Flask(__name__)
app.secret_key = os.urandom(32)

# In-memory state
state: Dict[str, Any] = {"tasks": [], "schedule": None}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks")
def get_tasks():
    return jsonify(state["tasks"])


@app.route("/api/tasks", methods=["POST"])
def add_task():
    body = request.get_json(force=True)
    err = _validate(body)
    if err:
        return jsonify({"error": err}), 400

    task = {
        "id": str(uuid.uuid4()),
        "name": body["name"].strip(),
        "due_date": body["due_date"],
        "estimated_hours": float(body.get("estimated_hours", 2)),
        "difficulty": int(body.get("difficulty", 3)),
        "course": body.get("course", "").strip(),
    }
    state["tasks"].append(task)
    return jsonify(task), 201


@app.route("/api/tasks/<tid>", methods=["DELETE"])
def delete_task(tid):
    state["tasks"] = [t for t in state["tasks"] if t["id"] != tid]
    return jsonify({"ok": True})


@app.route("/api/tasks", methods=["DELETE"])
def clear_tasks():
    state["tasks"] = []
    return jsonify({"ok": True})


@app.route("/api/schedule", methods=["POST"])
def schedule():
    body = request.get_json(force=True)

    if not state["tasks"]:
        return jsonify({"error": "Add at least one task first."}), 400

    try:
        ua = UserAgent(state["tasks"], body)
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
            "slots": [{"name": t.name, "hours": round(h, 2)} for t, h in slots],
        })

    result = {
        "days": days,
        "unscheduled": [t.name for t in sa.unscheduled],
        "validation": validation,
        "log": ua.log + ca.log + va.log,
    }

    state["schedule"] = result
    return jsonify(result)


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


if __name__ == "__main__":
    print("\n  Task Planner → http://localhost:5000\n")
    app.run(debug=True, port=5000)