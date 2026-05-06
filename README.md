# Multi-Agent Rule-Based Task Planning System

A CS152 project by **Izabella Doser** and **Arianna Gonzalez** - San Jose State University.

This is a web-based academic task planner that uses a multi-agent architecture to generate feasible study schedules from user-defined tasks, deadlines, and constraints. The system is designed to demonstrate three programming paradigms - imperative, functional, and logic - within a single cohesive architecture.

---

## How to Run

**1. Clone or unzip the repository**
```bash
git clone https://github.com/Izabelladesign/CS152_AgenticTaskPlanning.git
cd CS152_AgenticTaskPlanning-main
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Start the server**
```bash
python planner/app.py
```

**4. Open in your browser**
```
http://127.0.0.1:5000
```

> Note: Use `127.0.0.1` instead of `localhost` to avoid a Chrome port-blocking issue on port 5000.

---

## Project Structure

```
CS152_AgenticTaskPlanning-main/
├── requirements.txt
└── planner/
    ├── app.py               # Flask server and agent orchestration (imperative)
    ├── taskdata.py          # Frozen Task dataclass (functional)
    ├── persistence.py       # User accounts and workspace storage
    ├── agents/
    │   ├── user_agent.py        # Parses input and builds environment
    │   ├── constraint_agent.py  # IF-THEN rule interpreter (logic)
    │   ├── scheduler_agent.py   # Permutation search + recursive backtracking
    │   └── validator_agent.py   # Schedule conflict and violation checks
    └── templates/
        └── index.html       # Web UI
```

---

## System Architecture

The system runs four agents in sequence on every schedule request:

### 1. User Agent
Parses raw task inputs from the web UI and builds an `env` dictionary containing `start_date` and `max_hours_per_day`. Converts each task into a typed `Task` object passed downstream.

### 2. Constraint Agent
Runs a forward-chaining IF-THEN rule interpreter over every task. Rules either flag tasks as impossible (not enough time before the deadline) or adjust priority scores based on urgency, difficulty, and duration. The 6 built-in rules are:

| Rule | Condition | Effect |
|------|-----------|--------|
| IMPOSSIBLE | Task can't fit before deadline | Mark impossible, priority = -∞ |
| HIGH_DIFFICULTY | Difficulty ≥ 4 | +difficulty priority boost |
| URGENT | Due within 3 days | +5 priority |
| NEAR_DEADLINE | Due within 4–7 days | +2 priority |
| LONG_TASK | Duration ≥ 10 hours | +1.5 priority |
| EASY_SHORT | Difficulty ≤ 2 and duration ≤ 1.5h | -1 priority |

### 3. Scheduler Agent
Sorts feasible tasks by priority (highest first) then assigns them to calendar days within their deadline window. Uses two strategies:

- **Exhaustive permutation search** (≤ 8 tasks): tries every ordering to find one where all tasks fit within the daily cap
- **Recursive backtracking** (> 8 tasks or if permutation search fails): places tasks one at a time, saves state, and backtracks if a task can't be placed

Tasks that cannot fit in any configuration are moved to an unscheduled list.

### 4. Validator Agent
Checks the final schedule for:
- Daily hour cap violations
- Work scheduled before the start date
- Tasks placed after their deadline
- Tasks with incorrect total hour allocation

Results are returned alongside the schedule as a validation report.

---

## Programming Paradigms

This project explicitly demonstrates three paradigms:

**Imperative** - `app.py` orchestrates agents sequentially with mutable state. The scheduler's `hours_used` dictionary is updated in place as tasks are assigned to days.

**Functional** - `taskdata.py` defines `Task` as a frozen dataclass. Methods like `adjust_priority()` and `mark_impossible()` use `dataclasses.replace()` to return new Task objects rather than mutating the original. Priority scoring is handled through pure functions with no side effects.

**Logic** - `constraint_agent.py` implements a declarative rule interpreter. Each `Rule` is a data structure with a `condition` callable and an `action` callable. The `evaluate()` loop acts as a forward-chaining interpreter, firing rules whose conditions are satisfied - modeled after logic programming principles.

---

## Features

- Create, edit, and delete tasks with name, due date, estimated hours, difficulty, and course
- Configurable start date and max hours per day
- Automatic priority scoring and constraint evaluation
- Calendar-style schedule output
- Unscheduled task list for impossible or unfit tasks
- Full per-agent rule log showing exactly what fired and why
- Persistent user accounts and workspaces

---

## Dependencies

- Python 3.9+
- Flask ≥ 3.0
