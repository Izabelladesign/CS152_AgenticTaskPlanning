from dataclasses import dataclass, replace
from datetime import date

@dataclass
class Task:
    name:       str
    deadline:   date
    duration:   float
    difficulty: int
    course:     str = ""
    priority:   float = 0.0
    impossible: bool  = False

    def days_until(self, from_date: date) -> int:
        return (self.deadline - from_date).days

    def is_feasible(self, from_date: date, max_hours: float) -> bool:
        return max(0, self.days_until(from_date)) * max_hours >= self.duration

    def adjust_priority(self, delta: float) -> "Task":
        return replace(self, priority=self.priority + delta)

    def mark_impossible(self) -> "Task":
        return replace(self, impossible=True, priority=float("-inf"))
