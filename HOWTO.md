# HOWTO — editing a ganttuml source

Recipes for the common edits. Everything lives in one JSON file. Start with a copy of
`example.json` (minimal) or `example-advanced.json` (every feature). After each edit,
regenerate:

```bash
./example.sh                         # generate output/example.puml + render PNG/SVG via the plantuml docker
./render.sh my.json                  # same, for any source (example.sh/example-advanced.sh wrap this)
python3 ganttuml.py --input my.json  # just generate the .puml + print the schedule (no render)
```

`ganttuml.py` writes only the `.puml`. The shell scripts run the `plantuml/plantuml` docker
to render. All artifacts go to the **`output/`** subdirectory (kept out of git).

The generator never hard-codes dates. It emits dependencies, and PlantUML computes the
schedule. A duration (`days`) counts only that developer's working days. Weekends, holidays,
and that developer's PTO do not count. There is no weeks unit — give durations in days. Each
developer does one task at a time. A task waits for the later of its lane predecessor and its
dependencies.

---

## Set the project start and output file
```jsonc
"project": { "title": "My Project", "start": "2026-06-18", "output": "myproject.puml" }
```
`start` is the calendar origin (`YYYY-MM-DD`). `output` is the `.puml` filename to write.
`title` renders as the centered chart title.

## Add a version / generated-date footer
Set `version` (any string) to stamp a bottom-centre footer. The generation date is added
automatically, so the chart always carries an "as of" date. Set `show_footer: false` to hide
the footer.
```jsonc
"project": { "title": "My Project", "version": "1.2", "start": "2026-06-18", "output": "myproject.puml" }
```
This renders `Version 1.2  |  Generated <today>` at the bottom (just `Generated <today>`
without a `version`).

## Add a developer (lane)
Add an object to `developers`. The list order is the top-to-bottom lane order. No `color` is
necessary. Bars use a uniform theme: MS-Project blue, and red for the critical path.
```jsonc
"developers": [
  { "name": "Dave", "pto": [], "items": [] }
]
```

## Add a task (under a developer)
Add the task to that developer's `items`. Give every item a unique `id`. Set `done` on every
task (an integer percent 0–100). Use `0` for a task that has not started.
```jsonc
{ "type": "task", "id": "api_impl", "name": "Implement API", "days": 4, "done": 0 }
```
Consecutive tasks in one developer's `items` **auto-link**. Each task starts after the
previous one ends. That is the one-task-at-a-time rule. You add nothing to get it.

## Make a task depend on another task (incl. cross-developer)
Add `depends_on` with one id or a list of ids. The task starts after the latest of its
dependencies **and** its lane predecessor. A dependency may point at any task or milestone
id, in any lane.
```jsonc
{ "type": "task", "id": "ui_wire", "name": "Wire UI", "days": 5, "done": 0, "depends_on": "api_schema" }
{ "type": "task", "id": "qa_run",  "name": "Regression", "days": 4, "done": 0, "depends_on": ["ui_wire", "api_done"] }
```

## Add a milestone on a fixed date
```jsonc
{ "type": "milestone", "id": "rc1", "name": "RC1", "on": "2026-06-24" }
```

## Add a milestone that fires when items finish
Use `depends_on` instead of `on`. With a list, the milestone lands at the **latest** end of
all listed items. That gives a roll-up ("when everything is done") marker.
```jsonc
{ "type": "milestone", "id": "api_done", "name": "API frozen", "depends_on": "api_impl" }
{ "type": "milestone", "id": "rc1_complete", "name": "RC1 integration complete",
  "depends_on": ["api_int", "ui_int", "db_int"] }
```

## Add a project-wide (global) milestone
Put a cross-team gate that no developer owns (release, roll-up) in the top-level
`global_milestones` array. The fields equal the in-lane milestone fields. It renders in the
trailing "Milestones" lane.
```jsonc
"global_milestones": [
  { "type": "milestone", "id": "release", "name": "v1.0 Release", "depends_on": "qa_run" }
]
```

## Group tasks into phases (summary bars)
Add a top-level `groups` array. Each group renders as a **hollow summary bar with diamond
end-caps** in a "Phases" band above the developer lanes. The bold group name is centered in
the bar. The bar spans from the first start to the last end of its member items. The members
may belong to different developers. Groups are cosmetic only — they never change the
schedule. Each id may be in at most one group. Set `"group_color"` in `project` to tune the
outline (default `#3B3B3B`). A `fill/border` pair such as `#DEEBF7/#2E75B6` gives a tinted
bar instead.
```jsonc
"groups": [
  { "name": "Phase v1.0", "tasks": ["api_schema", "api_impl", "qa_run"] },
  { "name": "Phase v1.1", "tasks": ["api_v2_impl", "qa_v2_run"] }
]
```

## Add a developer's PTO / vacation
Add the dates to that developer's `pto` list. Only that developer is off. Their tasks skip
those days.
```jsonc
{ "name": "Alice", "pto": ["2026-06-19", "2026-06-26"], "items": [ ... ] }
```

## Add a company holiday (everyone off)
Add the holiday to `project.holidays`. `show_marker: true` also draws a labeled diamond on
the timeline. Set `enabled: false` to keep the holiday documented but treated as a **normal
working day**.
```jsonc
"holidays": [
  { "date": "2026-07-03", "label": "Independence Day", "show_marker": true },
  { "date": "2026-12-25", "label": "Christmas Day" },
  { "date": "2026-06-19", "label": "Juneteenth", "enabled": false }
]
```
Weekends and holidays are greyed automatically. The shade is cosmetic and never affects
timing. Change it with `"weekend_color": "#EFEFEF"` in `project`.

## Make ONE developer work a weekend / holiday
Add the dates to that developer's `works_on` list. Only that developer works them. Everyone
else stays off, and the day stays greyed. There is no team-wide "everyone works" switch.
Model a shared working day by adding the date to each developer's `works_on`.
```jsonc
{ "name": "Bob", "works_on": ["2026-06-28"], "items": [ ... ] }
```
A `works_on` date that is not actually a weekend or holiday is an **error**. A no-op entry
is almost always a typo'd date. A date cannot be in both `works_on` and `pto`.

## Hold a task until a start date
Give the task an optional `start` date (`YYYY-MM-DD`). It is a **floor** ("start no earlier
than"). The task begins on the **latest** of its `start` date, its dependencies, and its
lane predecessor. A dependency that finishes after `start` still wins. A `start` never pulls
a task before its inputs are ready. This is handy for a new joiner with a fixed start date.
```jsonc
{ "type": "task", "id": "api_v2_int", "name": "...", "days": 3,
  "done": 0, "depends_on": "api_v2", "start": "2026-07-01" }
```
`start` is **task-only** and optional (milestones pin an absolute date with `on`). If it
lands on a weekend, holiday, or PTO day, it rolls forward to that developer's next working
day.

## Colors (automatic — MS-Project theme)
There are **no per-lane or per-item colors**. The tool ignores any `color` field. Bars are a
uniform blue (`#8ABBED`). Milestones are black diamonds. Link arrows are light grey.

**Highlight the critical path (opt-in).** Set `show_critical: true` (default `false`) to
draw the **critical path** in **red** (`#E8473F`): its bars, milestone diamonds, and link
arrows. The critical path is the zero-slack chain to the finish date. ganttuml computes it
over `depends_on` **plus** the one-task-at-a-time lane order and the `start` floors
(resource-constrained), so it always reaches the real makespan. When on, the schedule report
also tags those items `[critical]`.
```jsonc
"project": { "show_critical": true,
             "bar_color": "#8ABBED", "critical_color": "#E8473F",
             "arrow_color": "#B0B7C3", "header_color": "#DCE9F8" }
```

## Set % complete on a task
Set `done` (an integer 0–100) on **every task** — it is required. The bar fills that
fraction in the bar's theme color. The remainder fills with `undone_color` (default light
gray `#DDDDDD`). A milestone cannot have `done`.
```jsonc
{ "type": "task", "id": "t", "name": "Integrate X", "days": 4, "done": 60 }
```
`done: 0` gives a full gray bar (the 1px outline shows blue, or red when critical).
`done: 100` gives a bar fully in the bar color. Recolor the remainder with `"undone_color"`
in `project`. PlantUML hardcodes the bar outline to 1px and ignores style line thickness.
The remaining part therefore shows through its fill, not a thick border. That is also why
the critical path is additionally marked with red arrows and diamonds.

## The today marker (vertical line)
A full-height vertical band is drawn on **today's** date automatically, whenever today falls
inside the chart's date range. No field is necessary. Tune it in `project`:
```jsonc
"project": { "today_color": "#4F9BFF40", "show_today": true }
```
The default `#4F9BFF40` is a translucent blue. The last two hex digits are the alpha
(opacity). A lower value is more see-through (`#4F9BFF26` is fainter, `#4F9BFF` is fully
solid). Set `"show_today": false` to hide the band. The band is cosmetic — today still
counts as a normal or closed day for scheduling.

## Link an item to Jira (or any URL)
The link becomes a clickable hyperlink in the SVG. Either set a project base plus a per-item
key, or set a full URL.
```jsonc
"project": { "jira_base_url": "https://your-company.atlassian.net" }
// item:
{ "type": "task", "id": "t", "name": "...", "days": 3, "jira": "PROJ-131" }   // -> .../browse/PROJ-131
{ "type": "task", "id": "u", "name": "...", "days": 3, "url": "https://example.com/spec" }  // full link wins
```

## Comment / annotate the JSON
JSON has no comment syntax. ganttuml therefore treats any key that starts with `_` as a
comment and ignores it — at every level. Any *other* unknown key is an error (fail fast on
typos such as `depends_om`).
```jsonc
{ "_comment": "phase 1 = API work",
  "type": "task", "id": "api_impl", "name": "Implement API", "days": 4, "done": 0 }
```

## Read the schedule report
`ganttuml.py` prints each item's computed `start -> end` dates (and each milestone date),
the project `makespan`, and a flag for any milestone that lands on a closed day. Use the
report to sanity-check the plan before you open the chart.

## Errors the generator will stop on
Each of these is an error:
- an **unknown key** at any level (typo protection — `_`-prefixed keys are comments, see
  above)
- a field of the wrong type, for example a `pto` that is not a list
- a duplicate `id`
- a `depends_on` that references an unknown id or itself
- a cyclic dependency
- an unparseable date
- a missing item `name`, or an empty or duplicate developer name
- a task with `days < 1`
- a milestone without exactly one of `on` / `depends_on`
- a `works_on` date that is not actually a closed day (almost always a typo)
- a date in both `works_on` and `pto` for one developer
- a non-milestone in `global_milestones`
- a duplicate holiday date, a holiday without `date`, or `show_marker` without a `label`
- a group that names an unknown id, an id in two groups, or a duplicate group name
- an item id that starts with `__group_` (reserved for the emitted phase bars)
- a `project.output` that is not a plain filename
- a calendar so over-constrained that no working day exists within 10 years

See **README.md** for the full schema and the
[PlantUML Gantt docs](https://plantuml.com/gantt-diagram) for how PlantUML itself behaves.
