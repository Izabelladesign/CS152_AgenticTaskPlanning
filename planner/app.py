"""
app.py — Multi-Agent Task Planner (no external integrations)

Run:
    pip install flask
    python app.py

Open: http://localhost:5000
"""

import os, uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

import sys; sys.path.insert(0, str(Path(__file__).parent))

from taskdata import Task
from agents.constraint_agent import ConstraintAgent
from agents.scheduler_agent  import SchedulerAgent

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
    err  = _validate(body)
    if err:
        return jsonify({"error": err}), 400
    task = {
        "id":              str(uuid.uuid4()),
        "name":            body["name"].strip(),
        "due_date":        body["due_date"],
        "estimated_hours": float(body.get("estimated_hours", 2)),
        "difficulty":      int(body.get("difficulty", 3)),
        "course":          body.get("course", "").strip(),
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
        max_hours  = float(body.get("max_hours", 6))
        start_date = date.fromisoformat(body.get("start_date", date.today().isoformat()))
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400

    env = {"max_hours_per_day": max_hours, "start_date": start_date}

    task_objs: List[Task] = []
    for t in state["tasks"]:
        try:
            task_objs.append(Task(
                name=t["name"],
                deadline=date.fromisoformat(t["due_date"]),
                duration=float(t["estimated_hours"]),
                difficulty=int(t["difficulty"]),
                course=t.get("course", ""),
            ))
        except Exception as e:
            return jsonify({"error": f"Bad task '{t.get('name')}': {e}"}), 400

    ca = ConstraintAgent(env)
    evaluated = ca.evaluate(task_objs)

    sa = SchedulerAgent(env)
    raw = sa.run(evaluated)

    days = []
    for d in sorted(raw):
        slots = raw[d]
        days.append({
            "date":  d.isoformat(),
            "label": d.strftime("%A, %b %d").replace(" 0", " "),
            "total": round(sum(h for _, h in slots), 2),
            "slots": [{"name": t.name, "hours": round(h, 2)} for t, h in slots],
        })

    result = {
        "days":        days,
        "unscheduled": [t.name for t in sa.unscheduled],
        "log":         ca.log,
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
        h = float(body.get("estimated_hours", 2)); assert h > 0
        d = int(body.get("difficulty", 3));        assert 1 <= d <= 5
    except Exception:
        return "Invalid hours or difficulty."
    return ""


if __name__ == "__main__":
    print("\n  Task Planner → http://localhost:5000\n")
    app.run(debug=True, port=5000)