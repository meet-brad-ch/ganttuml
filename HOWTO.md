# HOWTO — editing a ganttuml source

Recipes for the common edits. Everything lives in one JSON file — start by copying
`example.json` (minimal) or `example-advanced.json` (every feature). After any edit, regenerate:

```bash
./example.sh                         # generate output/example.puml + render PNG/SVG via the plantuml docker
./render.sh my.json                  # same, for any source (example.sh/example-advanced.sh wrap this)
python3 ganttuml.py --input my.json  # just generate the .puml + print the schedule (no render)
```
`ganttuml.py` only writes the `.puml`; the shell scripts run the `plantuml/plantuml` docker to render.
All artifacts are written to the **`output/`** subdirectory (kept out of git).

The generator never hard-codes dates — it emits dependencies and PlantUML computes the schedule.
Durations (`days`) count that person's working days only (weekends, holidays, and their PTO are
skipped); there is no weeks unit — express durations in days. Each person
does one task at a time; a task waits for the later of its lane-predecessor and its dependencies.

---

## Set the project start and output file
```jsonc
"project": { "title": "My Project", "start": "2026-06-18", "output": "myproject.puml" }
```
`start` is the calendar origin (`YYYY-MM-DD`); `output` is the `.puml` filename to write.
`title` renders as the centered chart title.

## Add a version / generated-date footer
Set `version` (any string) to stamp a bottom-centre footer; the generation date is added
automatically, so the chart always carries an "as of" date. Set `show_footer:false` to hide it.
```jsonc
"project": { "title": "My Project", "version": "1.2", "start": "2026-06-18", "output": "myproject.puml" }
```
Renders `Version 1.2  |  Generated <today>` at the bottom (just `Generated <today>` if no `version`).

## Add a person (developer / lane)
Add an object to `developers`. Order = top-to-bottom lane order. No `color` is needed — bars use a
uniform theme (MS-Project blue, red for the critical path).
```jsonc
"developers": [
  { "name": "Dave", "pto": [], "items": [] }
]
```

## Add a task (under a person)
Add to that developer's `items`. Every item needs a unique `id`, and every task **must** set `done`
(integer percent 0–100 — use `0` for not-started).
```jsonc
{ "type": "task", "id": "api_impl", "name": "Implement API", "days": 4, "done": 0 }
```
Consecutive tasks in one developer's `items` **auto-link** (each starts after the previous one ends)
— that's the one-task-at-a-time rule; you don't add anything for it.

## Make a task depend on another (incl. cross-person)
Add `depends_on` (one id, or a list). The task starts after the latest of its dependencies **and**
its lane-predecessor. Dependencies may point at any task/milestone id, in any lane.
```jsonc
{ "type": "task", "id": "ui_wire", "name": "Wire UI", "days": 5, "done": 0, "depends_on": "api_schema" }
{ "type": "task", "id": "qa_run",  "name": "Regression", "days": 4, "done": 0, "depends_on": ["ui_wire", "api_done"] }
```

## Add a milestone on a fixed date
```jsonc
{ "type": "milestone", "id": "rc1", "name": "RC1", "on": "2026-06-24" }
```

## Add a milestone that fires when item(s) finish
Use `depends_on` instead of `on`. With a list, the milestone lands at the **latest** end of all of
them (a roll-up / "when everything is done" marker).
```jsonc
{ "type": "milestone", "id": "api_done", "name": "API frozen", "depends_on": "api_impl" }
{ "type": "milestone", "id": "rc1_complete", "name": "RC1 integration complete",
  "depends_on": ["api_int", "ui_int", "db_int"] }
```

## Add a project-wide (global) milestone
For a cross-team gate not owned by any developer (release, roll-up), put it in the top-level
`global_milestones` array (same milestone fields). It renders in the trailing "Milestones" lane.
```jsonc
"global_milestones": [
  { "type": "milestone", "id": "release", "name": "v1.0 Release", "depends_on": "qa_run" }
]
```

## Group tasks into phases (summary bars)
Add a top-level `groups` array: each group renders as a **hollow summary bar with diamond
end-caps** (bold name centered in the bar) in a "Phases" band above the developer lanes, spanning
the first start → last end of its member items (which may belong to different developers).
Cosmetic only — grouping never changes the schedule. Each id may be in at most one group; tune
the outline with `"group_color"` in `project` (default `#3B3B3B`; a `fill/border` pair such as
`#DEEBF7/#2E75B6` gives a tinted bar instead).
```jsonc
"groups": [
  { "name": "Phase v1.0", "tasks": ["api_schema", "api_impl", "qa_run"] },
  { "name": "Phase v1.1", "tasks": ["api_v2_impl", "qa_v2_run"] }
]
```

## Add a person's PTO / vacation
Add the dates to that developer's `pto` list. Only that person is off; their tasks skip those days.
```jsonc
{ "name": "Alice", "pto": ["2026-06-19", "2026-06-26"], "items": [ ... ] }
```

## Add a company holiday (everyone off)
Add to `project.holidays`. `show_marker: true` also draws a labeled diamond on the timeline.
Set `enabled: false` to keep it documented but treated as a **normal working day**.
```jsonc
"holidays": [
  { "date": "2026-07-03", "label": "Independence Day", "show_marker": true },
  { "date": "2026-12-25", "label": "Christmas Day" },
  { "date": "2026-06-19", "label": "Juneteenth", "enabled": false }
]
```
(Weekends and holidays are greyed automatically; the shade is cosmetic and never affects timing.
Change it with `"weekend_color": "#EFEFEF"` in `project`.)

## Make ONE person work a weekend / holiday
Add the dates to that developer's `works_on` list. Only that person works them; everyone else stays
off and the day stays greyed. (There is no team-wide "everyone works" switch — model a shared
working day by adding it to each person's `works_on`.)
```jsonc
{ "name": "Bob", "works_on": ["2026-06-28"], "items": [ ... ] }
```
(A `works_on` date that isn't actually a weekend/holiday is an **error** — a no-op entry is
almost always a typo'd date. A date can't be in both `works_on` and `pto`.)

## Hold a task until a start date
Give the task an optional `start` (`YYYY-MM-DD`). It's a **floor** ("start no earlier than"):
the task begins on the **later** of its `start` date, its dependencies, and its lane-predecessor —
so a dependency that finishes after `start` still wins, and `start` never pulls a task before its
inputs are ready. Handy for a new joiner who can't begin until their start date.
```jsonc
{ "type": "task", "id": "api_v2_int", "name": "...", "days": 3,
  "done": 0, "depends_on": "api_v2", "start": "2026-07-01" }
```
`start` is **task-only** (milestones pin an absolute date with `on`) and optional. If it lands on a
weekend/holiday/PTO day it rolls forward to that person's next working day.

## Colors (automatic — MS-Project theme)
There are **no per-lane or per-item colors** — any `color` field is ignored. Bars are a uniform blue
(`#8ABBED`); milestones are black diamonds; link arrows are light grey.

**Highlight the critical path (opt-in).** Set `show_critical: true` (default `false`) to draw the
**critical path** in **red** (`#E8473F`): its bars, milestone diamonds, and link arrows. It's the
zero-slack chain to the finish date, computed over `depends_on` **plus** the one-task-at-a-time lane
order and `start` floors (resource-constrained), so it always reaches the real makespan. When on, the
schedule report also tags those items `[critical]`.
```jsonc
"project": { "show_critical": true,
             "bar_color": "#8ABBED", "critical_color": "#E8473F",
             "arrow_color": "#B0B7C3", "header_color": "#DCE9F8" }
```

## Set % complete on a task
`done` (integer 0–100) is **required on every task**. The bar fills that fraction in the bar's theme
color; the remainder is filled with `undone_color` (default light gray `#DDDDDD`). Milestones can't
have `done`.
```jsonc
{ "type": "task", "id": "t", "name": "Integrate X", "days": 4, "done": 60 }
```
`done: 0` is a full gray bar (the colored 1px outline shows blue, or red if critical); `done: 100` is
fully the bar color. Recolor the remainder with `"undone_color"` in `project`. (PlantUML hardcodes the
bar outline to 1px and ignores style line thickness, so the remaining part is shown by its fill, not a
thick border — which is why the critical path is also marked via red arrows and diamonds.)

## The today marker (vertical line)
A full-height vertical band is drawn on **today's** date automatically (whenever today falls inside
the chart's date range). No field needed. Tune it in `project`:
```jsonc
"project": { "today_color": "#4F9BFF40", "show_today": true }
```
The default `#4F9BFF40` is a translucent blue: the last two hex digits are the alpha (opacity) —
lower = more see-through (`#4F9BFF26` is fainter, `#4F9BFF` fully solid). Set `"show_today": false`
to hide it. (It's cosmetic — today still counts as a normal/closed day for scheduling.)

## Link an item to Jira (or any URL)
Becomes a clickable hyperlink in the SVG. Either set a project base + per-item key, or a full URL.
```jsonc
"project": { "jira_base_url": "https://your-company.atlassian.net" }
// item:
{ "type": "task", "id": "t", "name": "...", "days": 3, "jira": "PROJ-131" }   // -> .../browse/PROJ-131
{ "type": "task", "id": "u", "name": "...", "days": 3, "url": "https://example.com/spec" }  // full link wins
```

## Comment / annotate the JSON
JSON has no comment syntax, so ganttuml treats any key starting with `_` as a comment and
ignores it — at every level. Any *other* unknown key is an error (fail fast on typos like
`depends_om`).
```jsonc
{ "_comment": "phase 1 = API work",
  "type": "task", "id": "api_impl", "name": "Implement API", "days": 4, "done": 0 }
```

## Read the schedule report
`ganttuml.py` prints each item's computed `start -> end` (and milestone dates), the project `makespan`,
and flags any milestone that lands on a closed day — handy to sanity-check before opening the chart.

## Errors the generator will stop on
Any **unknown key** at any level (typo protection; `_`-prefixed keys are comments — see above);
a field of the wrong type (e.g. `pto` that isn't a list); duplicate `id`s; a `depends_on` that
references an unknown id or itself; a cyclic dependency; an unparseable date; a missing item
`name`; empty/duplicate developer names; a task with `days < 1`; a milestone that doesn't have
exactly one of `on` / `depends_on`; a `works_on` date that isn't actually a closed day (almost
always a typo); a date in both `works_on` and `pto` for one developer; a non-milestone in
`global_milestones`; a duplicate holiday date; a holiday missing `date` (or `show_marker` without
a `label`); a group naming an unknown id, an id in two groups, or a duplicate group name;
an item id starting with `__group_` (reserved for the emitted phase bars);
a `project.output` that isn't a plain filename; or a calendar so over-constrained
that no working day exists within 10 years.

See **README.md** for the full schema and the
[PlantUML Gantt docs](https://plantuml.com/gantt-diagram) for how PlantUML itself behaves.
