from dataclasses import dataclass
from datetime import date
from typing import Callable, List

@dataclass
class Rule:
    name:        str
    description: str
    condition:   Callable
    action:      Callable

class ConstraintAgent:
    def __init__(self, env: dict):
        self.env   = env
        self.log:  List[str] = []
        self.rules: List[Rule] = self._build_rules()

    def evaluate(self, tasks) -> list:
        self.log = ["── Constraint Agent ─────────────────────────────────"]
        result = []
        for task in tasks:
            current = task
            fired   = False
            for rule in self.rules:
                if rule.condition(current, self.env):
                    current, self.env, msg = rule.action(current, self.env)
                    self.log.append(f"  [FIRED] {rule.name} → {msg}")
                    fired = True
            if not fired:
                self.log.append(f"  [PASS]  No rules fired for '{task.name}'")
            result.append(current)
        self.log.append("─────────────────────────────────────────────────────")
        return result

    def _build_rules(self) -> List[Rule]:
        rules = []

        def impossible_cond(task, env):
            return not task.is_feasible(env["start_date"], env["max_hours_per_day"])
        def impossible_action(task, env):
            avail = max(0, task.days_until(env["start_date"])) * env["max_hours_per_day"]
            msg = f"'{task.name}' needs {task.duration}h but only {avail:.1f}h available → IMPOSSIBLE"
            return task.mark_impossible(), env, msg
        rules.append(Rule("IMPOSSIBLE", "Flag tasks that cannot fit before deadline.", impossible_cond, impossible_action))

        def hard_cond(task, env):
            return not task.impossible and task.difficulty >= 4
        def hard_action(task, env):
            boost = float(task.difficulty)
            return task.adjust_priority(boost), env, f"'{task.name}' difficulty={task.difficulty} → +{boost:.0f} priority"
        rules.append(Rule("HIGH_DIFFICULTY", "Boost priority for difficult tasks.", hard_cond, hard_action))

        def urgent_cond(task, env):
            return not task.impossible and 0 <= task.days_until(env["start_date"]) <= 3
        def urgent_action(task, env):
            days = task.days_until(env["start_date"])
            return task.adjust_priority(5.0), env, f"'{task.name}' due in {days}d → +5 priority"
        rules.append(Rule("URGENT", "Boost priority for tasks due within 3 days.", urgent_cond, urgent_action))

        def near_cond(task, env):
            return not task.impossible and 3 < task.days_until(env["start_date"]) <= 7
        def near_action(task, env):
            days = task.days_until(env["start_date"])
            return task.adjust_priority(2.0), env, f"'{task.name}' due in {days}d → +2 priority"
        rules.append(Rule("NEAR_DEADLINE", "Moderate boost for tasks due within 7 days.", near_cond, near_action))

        def long_cond(task, env):
            return not task.impossible and task.duration >= 10.0
        def long_action(task, env):
            return task.adjust_priority(1.5), env, f"'{task.name}' is {task.duration}h long → +1.5"
        rules.append(Rule("LONG_TASK", "Nudge long tasks to start early.", long_cond, long_action))

        def easy_cond(task, env):
            return not task.impossible and task.difficulty <= 2 and task.duration <= 1.5
        def easy_action(task, env):
            return task.adjust_priority(-1.0), env, f"'{task.name}' is easy & short → -1 priority"
        rules.append(Rule("EASY_SHORT", "Deprioritise easy short tasks.", easy_cond, easy_action))

        return rules
