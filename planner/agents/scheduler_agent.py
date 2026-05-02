import copy
from collections import defaultdict
from datetime import date, timedelta
from itertools import permutations
from typing import Dict, List, Tuple

from taskdata import Task

Schedule = Dict[date, List[Tuple[Task, float]]]

# Exhaustive permutation search for small instances (avoids brittle order dependence).
_PERM_SOLVER_MAX_TASKS = 8


class SchedulerAgent:
    def __init__(self, env: dict):
        self.max_hours: float = env["max_hours_per_day"]
        self.start_date: date = env["start_date"]
        self.schedule: Schedule = defaultdict(list)
        self.hours_used: Dict[date, float] = defaultdict(float)
        self.unscheduled: List[Task] = []
        self.log: List[str] = []

    def run(self, tasks: List[Task]) -> Schedule:
        self.log = ["── Scheduler Agent ──────────────────────────────────"]
        self.schedule = defaultdict(list)
        self.hours_used = defaultdict(float)
        self.unscheduled = []

        impossible = [t for t in tasks if t.impossible]
        feasible = sorted(
            [t for t in tasks if not t.impossible],
            key=lambda t: t.priority,
            reverse=True,
        )

        self.unscheduled.extend(impossible)
        for t in impossible:
            self.log.append(f"  [SKIP] '{t.name}' marked impossible → unscheduled")

        if not feasible:
            self.log.append("  No feasible tasks left to assign.")
            self._log_daily_cap_summary()
            self.log.append("─────────────────────────────────────────────────────")
            return dict(self.schedule)

        used_perm = False
        if len(feasible) <= _PERM_SOLVER_MAX_TASKS:
            total_perm = self._factorial(len(feasible))
            self.log.append(
                f"  [SOLVER] Exhaustive permutation search "
                f"({len(feasible)} tasks, {total_perm} orderings vs daily cap)."
            )
            for pi, perm in enumerate(permutations(feasible)):
                self.schedule = defaultdict(list)
                self.hours_used = defaultdict(float)
                if self._assign_all_ordered(perm):
                    self.log.append(f"  [SOLVER] Full schedule found at permutation #{pi + 1}.")
                    self._log_placement_trace()
                    self._log_daily_cap_summary()
                    self.log.append("─────────────────────────────────────────────────────")
                    return dict(self.schedule)
            self.log.append(
                "  [SOLVER] No permutation fits every task entirely; greedy partial placement."
            )
            self.log.append("  [HEURISTIC] Greedy placement with per-task success/fail trace.")
        else:
            self.log.append(
                f"  [HEURISTIC] Priority-ordered greedy "
                f"({len(feasible)} tasks > perm cap {_PERM_SOLVER_MAX_TASKS})."
            )

        self.schedule = defaultdict(list)
        self.hours_used = defaultdict(float)
        self.unscheduled.clear()
        self.unscheduled.extend(impossible)
        self._schedule_recursive(feasible)
        self._log_placement_trace()
        self._log_daily_cap_summary()
        self.log.append("─────────────────────────────────────────────────────")
        return dict(self.schedule)

    @staticmethod
    def _factorial(n: int) -> int:
        out = 1
        for i in range(2, n + 1):
            out *= i
        return out

    def _assign_all_ordered(self, ordered: Tuple[Task, ...]) -> bool:
        """Try to place every task in order; restores nothing (caller owns empty schedule)."""
        for t in ordered:
            if not self._assign(t):
                return False
        return True

    def _schedule_recursive(self, tasks: List[Task]) -> bool:
        if not tasks:
            return True
        task, *rest = tasks
        saved_schedule = copy.deepcopy(self.schedule)
        saved_hours = copy.copy(self.hours_used)
        if self._assign(task):
            self.log.append(f"  [PLACED] '{task.name}' ({task.duration:.2f}h across window)")
            return self._schedule_recursive(rest)

        avail = sum(
            max(0.0, self.max_hours - saved_hours[d])
            for d in self._window(self.start_date, task.deadline)
        )
        self.schedule = saved_schedule
        self.hours_used = saved_hours
        self.unscheduled.append(task)
        self.log.append(
            f"  [FAIL] '{task.name}' ({task.duration:.2f}h) does not fit before "
            f"{task.deadline.isoformat()} with ~{avail:.2f}h free in window vs "
            f"{self.max_hours:.2f}h/day max → unscheduled"
        )
        return self._schedule_recursive(rest)

    def _assign(self, task: Task) -> bool:
        days = self._window(self.start_date, task.deadline)
        remaining = task.duration
        proposed: List[Tuple[date, float]] = []
        for day in days:
            if remaining <= 0:
                break
            capacity = self.max_hours - self.hours_used[day]
            if capacity <= 0:
                continue
            chunk = min(capacity, remaining)
            proposed.append((day, chunk))
            remaining -= chunk
        if remaining > 1e-9:
            return False
        for day, hours in proposed:
            self.schedule[day].append((task, hours))
            self.hours_used[day] += hours
        return True

    def _log_placement_trace(self) -> None:
        if not self.schedule:
            self.log.append("  [TRACE] No day-level assignments.")
            return
        self.log.append("  [TRACE] Final placement by calendar day:")
        for d in sorted(self.schedule):
            used = sum(h for _, h in self.schedule[d])
            cap_note = ""
            if used > self.max_hours + 1e-9:
                cap_note = " *(validator should flag over-cap)*"
            elif abs(used - self.max_hours) < 1e-9:
                cap_note = " (at daily max)"
            self.log.append(
                f"    {d.isoformat()} → {used:.2f}/{self.max_hours:.2f}h{cap_note}"
            )
            for task, hours in self.schedule[d]:
                self.log.append(f"      · {hours:.2f}h  {task.name}")

    def _log_daily_cap_summary(self) -> None:
        if not self.schedule:
            return
        overloaded = [
            (d, sum(h for _, h in slots))
            for d, slots in self.schedule.items()
            if sum(h for _, h in slots) - self.max_hours > 1e-9
        ]
        if overloaded:
            for d, total in overloaded:
                self.log.append(
                    f"  [WARN] Daily load {total:.2f}h exceeds cap {self.max_hours:.2f}h "
                    f"on {d.isoformat()}"
                )

    @staticmethod
    def _window(start: date, end: date) -> List[date]:
        days: List[date] = []
        cur = start
        while cur <= end:
            days.append(cur)
            cur += timedelta(days=1)
        return days
