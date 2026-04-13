import copy
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Tuple
from taskdata import Task

Schedule = Dict[date, List[Tuple[Task, float]]]

class SchedulerAgent:
    def __init__(self, env: dict):
        self.max_hours:   float             = env["max_hours_per_day"]
        self.start_date:  date              = env["start_date"]
        self.schedule:    Schedule          = defaultdict(list)
        self.hours_used:  Dict[date, float] = defaultdict(float)
        self.unscheduled: List[Task]        = []

    def run(self, tasks: List[Task]) -> Schedule:
        self.schedule    = defaultdict(list)
        self.hours_used  = defaultdict(float)
        self.unscheduled = []
        impossible = [t for t in tasks if t.impossible]
        feasible   = sorted([t for t in tasks if not t.impossible], key=lambda t: t.priority, reverse=True)
        self.unscheduled.extend(impossible)
        self._schedule_recursive(feasible)
        return dict(self.schedule)

    def _schedule_recursive(self, tasks: List[Task]) -> bool:
        if not tasks:
            return True
        task, *rest = tasks
        saved_schedule  = copy.deepcopy(self.schedule)
        saved_hours     = copy.copy(self.hours_used)
        if self._assign(task):
            return self._schedule_recursive(rest)
        else:
            self.schedule   = saved_schedule
            self.hours_used = saved_hours
            self.unscheduled.append(task)
            return self._schedule_recursive(rest)

    def _assign(self, task: Task) -> bool:
        days      = self._window(self.start_date, task.deadline)
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

    @staticmethod
    def _window(start: date, end: date) -> List[date]:
        days, cur = [], start
        while cur <= end:
            days.append(cur)
            cur += timedelta(days=1)
        return days
