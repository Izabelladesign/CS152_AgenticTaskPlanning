from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Tuple

from taskdata import Task

Schedule = Dict[date, List[Tuple[Task, float]]]


class ValidatorAgent:
    def __init__(self, env: dict):
        self.env = env
        self.log: List[str] = []

    def validate(self, schedule: Schedule, tasks: List[Task], unscheduled: List[Task]) -> dict:
        self.log = ["── Validator Agent ────────────────────────────────"]
        errors: List[str] = []
        warnings: List[str] = []

        scheduled_hours = defaultdict(float)
        task_hours = defaultdict(float)

        for day, slots in schedule.items():
            if day < self.env["start_date"]:
                errors.append(f"Schedule contains work before start date: {day.isoformat()}")
            day_total = sum(hours for _, hours in slots)
            scheduled_hours[day] = day_total
            if day_total - self.env["max_hours_per_day"] > 1e-9:
                errors.append(
                    f"Daily limit exceeded on {day.isoformat()}: {day_total:.2f}h > {self.env['max_hours_per_day']:.2f}h"
                )

            for task, hours in slots:
                if hours <= 0:
                    errors.append(f"Non-positive allocation for '{task.name}' on {day.isoformat()}")
                if day > task.deadline:
                    errors.append(f"'{task.name}' scheduled after deadline on {day.isoformat()}")
                task_hours[task.name] += hours

        for task in tasks:
            allocated = task_hours[task.name]
            if task.impossible:
                if task.name not in {u.name for u in unscheduled}:
                    warnings.append(f"Impossible task '{task.name}' should remain unscheduled")
                continue

            if abs(allocated - task.duration) > 1e-9:
                if task.name in {u.name for u in unscheduled}:
                    warnings.append(
                        f"'{task.name}' was left unscheduled with {allocated:.2f}/{task.duration:.2f}h allocated"
                    )
                else:
                    errors.append(
                        f"'{task.name}' allocated {allocated:.2f}h but needs {task.duration:.2f}h"
                    )

        if not errors:
            self.log.append("  [PASS] No schedule conflicts or boundary violations found")
        else:
            for err in errors:
                self.log.append(f"  [ERROR] {err}")

        for warning in warnings:
            self.log.append(f"  [WARN]  {warning}")

        self.log.append("─────────────────────────────────────────────────────")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "scheduled_hours_by_day": {d.isoformat(): round(h, 2) for d, h in sorted(scheduled_hours.items())},
        }