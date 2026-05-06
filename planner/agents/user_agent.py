from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

from taskdata import Task


class UserAgent:
    def __init__(self, raw_tasks: List[Dict[str, Any]], settings: Dict[str, Any]):
        self.raw_tasks = raw_tasks
        self.settings = settings
        self.env: Dict[str, Any] = {}
        self.log: List[str] = []

    def build(self) -> Tuple[Dict[str, Any], List[Task]]:
        self.log = ["── User Agent ───────────────────────────────────────"]
        self.env = self._build_env()
        tasks = [self._to_task(t) for t in self.raw_tasks]
        self.log.append(f"  Loaded {len(tasks)} task(s) into the planning environment")
        self.log.append(
            f"  start_date={self.env['start_date'].isoformat()}, max_hours_per_day={self.env['max_hours_per_day']:.2f}"
        )
        self.log.append("─────────────────────────────────────────────────────")
        return self.env, tasks

    def _build_env(self) -> Dict[str, Any]:
        today = date.today()
        start_date = date.fromisoformat(self.settings.get("start_date", today.isoformat()))
        # Prevent stale persisted settings from scheduling into already-passed days.
        if start_date < today:
            start_date = today
        max_hours = float(self.settings.get("max_hours", 6))
        if max_hours <= 0:
            raise ValueError("Max hours per day must be greater than 0.")
        return {
            "start_date": start_date,
            "max_hours_per_day": max_hours,
            "task_count": len(self.raw_tasks),
        }

    @staticmethod
    def _to_task(task: Dict[str, Any]) -> Task:
        return Task(
            name=task["name"],
            deadline=date.fromisoformat(task["due_date"]),
            duration=float(task["estimated_hours"]),
            difficulty=int(task["difficulty"]),
            course=task.get("course", ""),
        )