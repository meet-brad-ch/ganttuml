---
name: ganttuml
description: Create and maintain a ganttuml project plan (JSON → PlantUML Gantt chart). Use when the user wants to create, edit, review, or troubleshoot a project plan, Gantt chart, or schedule — adding developers, tasks, milestones, dependencies, PTO, holidays, or phase groups, or checking the critical path, makespan, or task progress.
---

# ganttuml project-plan assistant

The project plan is one JSON file (e.g. `example.json`). `ganttuml.py` validates it, prints a
schedule report, and writes a PlantUML `.puml`; PlantUML computes all dates from the emitted
constraints. Never hand-place dates to sequence work — model the constraints (dependencies,
lane order, `start` floors) and let the schedule fall out.

## Read before writing JSON

- `README.md` — the full JSON schema (every field) and the complete validation list.
- `HOWTO.md` — copy-paste recipes for every common edit (add a person/task/milestone, PTO,
  holidays, phases, Jira links, critical path, …).
- `example.json` — minimal starter: copy it to begin a new plan.
- `example-advanced.json` — exercises every feature; consult it for exact syntax.

Read the README schema section before your first edit in a session; open HOWTO.md when the
user asks for a kind of change you haven't looked up yet.

## Edit loop

1. Make the JSON edit the user asked for.
2. Validate + reschedule (no docker needed):
   - Windows: `python ganttuml.py --input <plan>.json`
   - Linux/macOS: `python3 ganttuml.py --input <plan>.json`

   A relative `--input` resolves against the repo directory (where `ganttuml.py` lives),
   not the current working directory.
3. On error: the message is precise (JSON syntax caret + hint, the exact unknown key, the
   cycle path, …). Fix exactly what it names; rerun. Don't guess around it.
4. On success it writes `output/<project.output>` and prints the schedule report. Relay what
   changed to the user: per-item `start -> end` dates, the makespan, `[critical]` tags (when
   `show_critical` is on), and any "milestone lands on a closed day" note (a warning worth
   surfacing, not an error).
5. Render images only when the user asks for them: `./render.sh <plan>.json` (Bash + docker;
   on Windows run it from WSL or Git Bash, or run the `docker run … plantuml/plantuml`
   command from `render.sh` manually).

## Pitfalls

- Every task requires `done` (integer 0–100; use 0 for not started) and a globally unique `id`.
- Any unknown key anywhere is a fatal error. There is no `assignee`, `owner`, `priority`,
  `end`, `duration`, or `weeks`: assignment = which developer's `items` list the task sits
  in; duration = `days` (working days for that person). Keys starting with `_` are comments.
- Consecutive tasks in one developer's `items` auto-link (one task at a time). Don't add a
  `depends_on` just to sequence one person's own work — use it for real cross-item
  dependencies.
- Milestones take exactly one of `on` (fixed date) or `depends_on` (latest end of the deps),
  and never `days`/`done`/`start`. Cross-team gates belong in top-level `global_milestones`.
- Task `start` is a floor ("no earlier than") — a later dependency still wins; it can never
  pull a task earlier.
- `works_on` must name a day that is actually closed (weekend or enabled holiday) and must
  not overlap that person's `pto`.
- Colors are theme-level (`project.bar_color` etc.); a per-developer or per-item `color` is
  accepted but ignored.
- Item ids starting with `__group_` are reserved for the emitted phase bars.

## Maintenance moves

- Progress update: bump each task's `done` %; rerun to show the new picture.
- Slip analysis: set `project.show_critical: true` and walk the user through the red chain.
- New absence or holiday: add to that developer's `pto` or to `project.holidays`; rerun and
  report which end dates moved.
- Replan: bump `project.version` so the footer stamps the new version + generation date.
- Phases: top-level `groups` draw summary bars — cosmetic only, never affects the schedule.
