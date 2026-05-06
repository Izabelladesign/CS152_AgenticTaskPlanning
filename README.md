# CS152 Agentic Task Planning

A multi-agent course workload planner built with Flask.  
It helps students turn assignments into a feasible day-by-day schedule based on deadlines, difficulty, and daily-hour constraints.

## Features

- Account-based local workspaces (tasks, settings, latest schedule)
- Multi-agent scheduling pipeline:
  - `UserAgent` prepares environment/task objects
  - `ConstraintAgent` applies priority/feasibility rules
  - `SchedulerAgent` allocates work across days
  - `ValidatorAgent` checks constraint violations
- Rule log for explainable decisions (`URGENT`, `NEAR_DEADLINE`, etc.)
- Task CRUD with course/category support
- Schedule UI with per-day totals and per-task hour bars

## Project Structure

- `planner/app.py` - Flask app + API routes
- `planner/templates/index.html` - single-page UI
- `planner/agents/` - agent implementations
- `planner/persistence.py` - account/workspace file persistence
- `planner/data/` - local runtime data (ignored by git)

## Run Locally

From repo root:

```bash
pip install -r requirements.txt
python planner/app.py
```

Then open: `http://localhost:5000`

## Notes

- Workspace data is stored locally under `planner/data/`.
- Do not commit credentials or local user data.