# ganttuml

[![CI](https://github.com/meet-brad-ch/ganttuml/actions/workflows/ci.yml/badge.svg)](https://github.com/meet-brad-ch/ganttuml/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ganttuml?label=pypi)](https://pypi.org/project/ganttuml/)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![Runtime dependencies](https://img.shields.io/badge/runtime%20dependencies-none-brightgreen)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

JSON in, Gantt out. You describe developers and their ordered tasks and milestones in one
JSON file. ganttuml turns that file into a rendered PlantUML Gantt chart (PNG + SVG).

- **One Python file.** The tool uses only the standard library. It has zero dependencies.
- **Runs locally.** Your plan data stays on your machine. The tool never contacts a server.
- **Tested.** The test suite has 100% coverage. CI enforces that gate on each push.
- **General purpose.** No Jira is required. An optional per-item Jira link becomes a clickable
  hyperlink in the SVG.

![Demo: four plan edits and their rendered schedules](https://raw.githubusercontent.com/meet-brad-ch/ganttuml/main/docs/demo.gif)

[**▶ Open the advanced example live**](https://www.plantuml.com/plantuml/svg/fLbjRzis4FxkNq6Ws9fcS6p9JknqHT6yD6s73KtRRVqG10OZqR4MYNH9AcdQzR_lIBsHaaWbc8C04Pz7kkVkUCUpyaf8pEKrfbAEDabCKCJIFAD8BrihXCRMTPnpB1D6Ho-4l4_9ov5-o6c2hpdEqFSHGZcD6INwJuIESNJpXZDOEs4fu-Z9gVu0zWD-CUVihcJ-db1ISewdnukJMScHIKRInFF0azU7PqjD_Z5wCIbLoKIc17sOeJE2PSu9EeM7t19-Frep9Wb7VnCkm0qKx4qH-XUXDuGIy8p4A9o61-FfSZmBHkUS_KCYMOH5bCZ1E0oBa70YMCuZ8f1ww1NxsbwcE2DYD7gAnl11dmcvWN1EDYnDOdoFn0R72Rr6lo39r7M6-GqesucOo8XCebyHPKX46nBdgUAHzHh4FDCF6zLQ5YWHAZcCW_Q4eYUlpzHFGrXw2OlnT3P4c0yHzWS8GJ1428S8Yo72a9l1uG0X7F8YF70GgWIV4pxUmhw2RSNMw-VehaYuW0oNELT_dl_v7kra2Sq5kcFyHgmOBNFw_IXD8l93MO7x4JocJkA-3rpumAKJLAdtWNCVkEy1Wy07XZvmuGDzhWI77Z2S-a2Vsj2dDlG58JmOVJzcLww4zK95HbpGt0tjEo6L2nSKkY6tGfK55tJeX4AtGcUW5hv0gNrzWZbBNG5sW-uxY_YxmRaFtFU11pvmuG5L_jnWw0DzDWElJL-4L9ATOEWB0YHw15toRTKAeUDTlACnsKAF93I2CneEmHrs9PvTeWtUmh8myt9nmh8jflVeKvvbS4u2kyi3lvIDymqMfB207lRPtTNte5iO27PtBn4Mw6ArkeP9OxkQNdOd08HfZ7Hphqs3HEEErb5nfZ-J9xDZzGEoMYP4snSzPbXud8XjgW87CHKmMI0rFDawxHiUAO7qXDFqYJnM0XcMyBZC1EtC1AtCm4PPTZC35M_UyRYm1A9dDveFV4XcWalxXaTAwCcCvHDvh8J1pAWYqaURhg5J8f9hYexEt-bvDCE5FhnDLjKrcAtEGaw-v0aCmMY6L9sFB5xBxFBe-FZrQOSIJAS_0I_RfWH6SXk6MVX6mCYCBYusKcx5yyda7kRjSLIqXpqiKon4WkaU9N9o1N4GP7B-yVrlus0QN5xMtd1ocv2xmfDOBwsgfKubpg5JAJ4PeLA5eV4_WUL-x-U6zmNButjDsBSTLo4dy2s9WoOQwwy1FuC9oHCY6X4RpA630ZYS1uFgaMEpR4bb-5GvwXr1lag85NoNCWJTXgiYfCE23Af7aCso1JMPgJHPGXwMePhe5r5pR0ddS7B5x8uYIQ8DYicLB2IeorLnsISWB0KOD8Tvcs4PLwKAGv8kr4yHNgzP6gE_oXZagcwAjKA27gSw0YoQGqARqwvH2-yfKl8LA-uUt3B9ax7OaaXLusSG0d8LjyuSFEeEbliKxpUA2ufRROtFRA5WR0ipYDZKngfBRu0gajkWmMXLSHGHQ4bNIPh8UxI5zbJkq22uNnMNRjC6oRKtBKQhMZ6_GHcB2PBGFadjSWphQhdFygnnkg6vtROuhTAaad2gNnZXDFcc_wWb9C6IzfcVD-OBYjjqZTjcZJrbjuHS5x5hRnb-rootRPFItM24hndFi1fhPLvqqcgp0JIqrJJ5iz4glDC8zF1Tj08YKRv57uvW5hfDEAEgGnOYlk0Lh1KQocczewBYE4GOSBiFVEQ91AU9a0Wc4bgRB2u6R1QazamN65Zx5SnolfYTsVY1BUXZhWxxQwvAK4r7EUYhLV7S8MhUYD8SjzqAjgrMmFyOLsPwN3dA9Skm96uVSC7GjJNWYabrUzHYzULNrrKtoL0K3yfppNEBC2dTX6hxJKHC0SwKpYpx0rar67QLbI_xwk-jC8cXdUgDRqoY5AkduIjsIyhtUjRuEdvf38xcy5S1pUpLcSKgIZCDTQOZWs9Og2SN1JUpH5TPTMosZlCEL7I-ShayzwmpKEkepoNhZ2hlge-DrY5ImhgrzwWtEgzn1FGXTOEkPAgksRGkjLfrZPPFPUqQNMLyKUwDopQkDqa7DYgeKr4TShNJkwgRVMYNHDyZD4kT0NyaATGbe-KB43MZhpdxHcWp5gl_q3HVSx0qjkHJeV_dOz0iZ-4yKHjjpDRhkkRKWhus7rZUKJrElLT17qbAuAjySIElBZntzNBieZ0C1Bq683OT6sMuMcOwp6hJ3F6QYkfZzlUOqIiW5l-1-my0)
— the public PlantUML server renders the bundled example in your browser. You install nothing.
This link is the one place where a server appears. The tool itself runs offline.

**New here?** Read **[HOWTO.md](HOWTO.md)** for step-by-step recipes: add a developer, a task,
a milestone, PTO, a holiday, a working Saturday, or a Jira link. This file is the reference and
the schema.

## Requirements
- **Python 3.7+** — `ganttuml.py` uses only the standard library. No pip installs are necessary.
- **Docker** — necessary only to render PNG/SVG with the
  [`plantuml/plantuml`](https://hub.docker.com/r/plantuml/plantuml) image. The `.puml`
  generation and the schedule report need only Python.
- **OS** — `ganttuml.py` runs where Python runs: Linux, macOS, and Windows. The render scripts
  (`render.sh`, `example*.sh`) are Bash scripts. Run them on Linux, macOS, or WSL on Windows.
  As an alternative, run the `docker run … plantuml/plantuml` command from `render.sh` manually.

## Usage
Install from PyPI (optional): `pip install ganttuml` provides the tool as the `ganttuml`
command. A repo clone works the same without installation.

`ganttuml.py` generates the `.puml` file and prints the schedule. It does not render images.
The shell scripts render PNG and SVG. They run the `plantuml/plantuml` docker directly
(`ganttuml.py` never starts docker).

```bash
python3 ganttuml.py --input my.json # validate + write output/<output>.puml + print schedule (no render)
./render.sh my.json                 # generate + render PNG & SVG via the plantuml docker
./example.sh                        # thin wrapper -> render.sh example.json (minimal starter)
./example-advanced.sh               # thin wrapper -> render.sh example-advanced.json (every feature)
```

- `render.sh <source.json>` is the reusable entry point for generate + render. The per-project
  `*.sh` files are one-line wrappers around it.
- Bare `python3 ganttuml.py` (or bare `ganttuml`) defaults to `--input example.json`.
- A relative `--input` path resolves against your current directory. When the file is not
  there but exists next to `ganttuml.py` (the repo), that copy is used — so the bundled
  examples work from any directory.
- The output filename comes from `project.output`. All artifacts go to the **`output/`**
  subdirectory of your current directory: the `.puml`, plus `.png`/`.svg`/`.cmapx` after
  a render.

## Claude Code skill
The repo ships a [Claude Code](https://claude.com/claude-code) skill at
`.claude/skills/ganttuml/`. Clone the repo and open it in Claude Code. Then request plan
changes in plain language, for example "add a task for Bob after the API work". The skill
teaches Claude the edit, validate, and report loop, and points it at these docs. Type
`/ganttuml` to invoke the skill explicitly.

## How scheduling works
- **Developers are lanes.** Each developer's `items` run in the listed order. Each task
  **auto-links** after the previous task in that lane. One developer does one task at a time.
- **Dependencies.** `depends_on` adds cross-task and cross-developer links by `id`. A task
  keeps BOTH its auto-link and its dependencies. PlantUML starts the task after whichever
  link ends latest. A developer is never double-booked.
- **Start floor.** A task's optional `start` date is one more lower bound. The task begins on
  the latest of three dates: its `start` date, its dependencies, and its lane predecessor.
  ganttuml emits it as `[id] starts <date>`, and PlantUML max-combines that statement with the
  `->` arrows. A `start` floor can hold a task back. It can never pull a task earlier.
- **Appearance (MS-Project theme).** All bars use one uniform blue (`#8ABBED`). There are
  **no per-lane or per-item colors** — the tool ignores any `color` field. The **critical
  path** is the zero-slack chain that drives the finish date. ganttuml computes it over
  `depends_on` **plus** the lane auto-links and the `start` floors (resource-constrained).
  Set `project.show_critical: true` (default `false`) to draw that chain in **red**
  (`#E8473F`): its bars, milestone diamonds, and link arrows. When on, the schedule report
  also tags those items `[critical]`. Tune the colors with `project.bar_color` /
  `critical_color` (see Top-level keys).
- **Calendar (all-open model).** Weekends (Sat/Sun) and holidays are always non-working.
  ganttuml leaves PlantUML's calendar fully open. It emits closures as **per-developer
  off-days** (`{dev} is off on <date>`). The grey day shading (`<date> is colored in`) is
  cosmetic only and does NOT affect scheduling. `requires N days` counts only that
  developer's open days. This model lets one developer work a normally-closed day:
  - `pto` (per developer) — that developer is off on those dates.
  - `works_on` (per developer) — that developer **works** those normally-closed dates
    (weekend or holiday). Nobody else does, and the day stays grey.

  PlantUML has no per-resource "open" directive. Per-developer availability must therefore
  use off-days.
- **PlantUML does all the scheduling.** `ganttuml.py` emits definitions grouped by developer
  (the rows). It then emits every `->` / `happens at` statement in **dependency
  (topological) order**. Each arrow's source is then already declared. Each milestone's
  `happens at` snapshots an already-positioned target. PlantUML's evaluation rules require
  this order (see the [PlantUML Gantt docs](https://plantuml.com/gantt-diagram)). The order
  also lets a milestone be both a dependency and a dependency *source*. `ganttuml.py`
  computes the same schedule in Python for one purpose only: to print per-item dates plus
  the makespan, and to flag a milestone on a closed day.

## JSON schema
```jsonc
{
  "project": {
    "title": "Q3 Feature Delivery",
    "start": "2026-06-22",            // YYYY-MM-DD
    "output": "example.puml",
    "weekend_color": "#EFEFEF",        // optional; shade for greyed weekend/holiday columns
    "jira_base_url": "https://your-company.atlassian.net",   // optional; for per-item `jira` links
    "holidays": [
      {"date": "2026-07-03", "label": "Independence Day", "show_marker": true},
      {"date": "2026-06-19", "label": "Juneteenth", "enabled": false}  // disabled -> treated as a normal working day
    ]
  },
  "developers": [
    {
      "name": "Alice", "pto": ["2026-06-25"], "works_on": ["2026-06-28"],
      "items": [
        {"type": "task", "id": "api_schema", "name": "Design API schema", "days": 3, "done": 100, "jira": "PROJ-101"},
        {"type": "task", "id": "api_impl", "name": "Implement API", "days": 4, "done": 50},
        {"type": "milestone", "id": "api_done", "name": "API frozen", "depends_on": "api_impl"}
      ]
    }
  ],
  "global_milestones": [
    {"type": "milestone", "id": "release", "name": "v1.0 Release", "depends_on": "qa_run"}
  ],
  "groups": [
    {"name": "Phase v1.0", "tasks": ["api_schema", "api_impl"]}   // optional summary bars
  ]
}
```

### Top-level keys

**`project`** — settings and calendar:
- `start` (`YYYY-MM-DD`) — the calendar origin. This is the only required key in the file.
- `title` — optional. A centered chart title.
- `output` — the `.puml` filename. It must be a plain name without directories. The file
  always goes under `output/`. Default `example.puml`.
- `version` — optional free string. It appears in a bottom-centre **footer** as
  `Version <x>  |  Generated <today>`. The date is the generation date, and the footer always
  stamps it. Set `show_footer: false` to drop the footer.
- `show_today` (default `true`) — draw a band on today's column. `today_color` (default
  `#4F9BFF40`, a translucent blue) sets its color. The last two hex digits are the alpha
  (opacity). A lower value is more transparent.
- `weekend_color` (default `#EFEFEF`) — the shade for the greyed weekend and holiday columns.
- `undone_color` (default `#DDDDDD`) — the fill for the remaining (undone) part of a
  `% done` bar. PlantUML hardcodes the bar border to 1px. Visibility therefore comes from
  this fill, not from a thicker outline.
- Theme colors, all optional: `bar_color` (default `#8ABBED` — the uniform MS-Project blue
  for every non-critical bar), `critical_color` (default `#E8473F` — the red for
  critical-path bars, diamonds, and links), `arrow_color` (default `#B0B7C3` — non-critical
  link arrows), `header_color` (default `#DCE9F8` — the timeline header band), and
  `group_color` (default `#3B3B3B` — the outline of the hollow phase bars, where a
  `fill/border` pair gives a tinted bar).
- `show_critical` (default `false`) — opt in to the red critical-path marking.
- `jira_base_url` — the base URL for per-item `jira` keys.
- `holidays[]` — each entry is `{date, label, show_marker?, enabled?}`. `enabled: false`
  keeps the holiday documented but treats it as a normal working day. Weekends (Sat/Sun) are
  always non-working.

**`developers`** — an ordered list. The order is the top-to-bottom lane order. Each
developer has:
- `name` — non-empty and unique.
- `pto` — optional. Dates when this developer is off.
- `works_on` — optional. Dates when this developer **works** despite a weekend or holiday.
- `items` — the tasks and milestones, in lane order.
- A `color` field is accepted but **ignored**. Bars use the uniform theme (see "Appearance"
  above).

**`global_milestones`** — a separate, project-level milestone array. No developer owns these
milestones. Use it for release gates and roll-ups, for example "RC1 complete". The fields
equal the in-lane milestone fields. These milestones render in the trailing "Milestones"
lane with no resource. Put a cross-team marker that `depends_on` many tasks here.

**`groups`** — optional MS-Project-style **phases**. Each group is `{name, tasks}`: a unique
name and a non-empty list of item ids. The ids may span developers. An id belongs to at most
one group. A group renders as a **hollow summary bar with diamond end-caps** in a leading
"Phases" band. The bar spans from the first start to the last end of its members. The bold
group name is centered in the bar. Groups are purely cosmetic. They never affect scheduling,
links, or the critical path. (PlantUML has no native summary tasks. ganttuml draws the band
from the computed schedule.) `project.group_color` (default `#3B3B3B`) sets the outline
color. A `fill/border` pair such as `#DEEBF7/#2E75B6` gives a tinted bar instead of a hollow
one.

### Item fields

**task** — `type: "task"`, plus:
- `id` — unique across the file.
- `name` — the bar label.
- `days` — an integer >= 1. The duration in working days.
- `done` — **required**. An integer percent 0–100. That fraction of the bar fills in the
  theme color. The remainder fills with `undone_color` (default light gray).
- `depends_on` — optional. One id or a list of ids.
- `start` (`YYYY-MM-DD`) — optional **floor**: the task starts no earlier than this date. A
  later dependency or lane predecessor still wins. Task-only — milestones use `on`.
- `jira` — optional issue key. `url` — optional full link, which overrides `jira`.
- The bar color is automatic: theme blue, or red on the critical path. A `color` field is
  ignored.

**milestone** — `type: "milestone"`, `id`, `name`, and exactly one of:
- `on` — an absolute `YYYY-MM-DD` date.
- `depends_on` — one id or a list. The milestone sits at the **latest end** of those items
  (via repeated `happens at`).

Optional: `jira`, `url`. Diamonds are black, or red on the critical path (a `color` field is
ignored). A milestone lives inside a developer's `items` or in `global_milestones`. A
`depends_on` milestone renders in the trailing "Milestones" lane without a resource.

### Jira / URL links
An item with `url` links to that address verbatim. An item with `jira` links to
`{base}/browse/{jira}` when `project.jira_base_url` is set. ganttuml emits the link as
`links to [[...]]`. The link is clickable in the SVG. PlantUML also writes a `.cmapx` image
map for the PNG.

## Validation
`ganttuml.py` fails fast on any invalid input and exits non-zero. Nothing is silently
ignored. Each of these is an error:
- an unknown key at any level — this catches typos such as `depends_om` (keys that start
  with `_` are comments, e.g. `"_comment": "..."`)
- a field of the wrong type, for example a `pto` that is not a list, a holiday that is not
  an object, or a non-string `title`
- a duplicate id, an unknown or self-referencing `depends_on` id, or a cyclic dependency
- an unparseable date
- a missing or empty item `name` or developer `name`, or a duplicate developer name
- a bad `type`, or `days < 1`
- a task without `done`, a `done` that is not an integer 0–100, or `done` on a milestone
- a milestone without exactly one of `on` / `depends_on`
- a `works_on` date that is not actually a closed day (a no-op is almost always a typo)
- a date listed in both `works_on` and `pto`
- a non-milestone entry in `global_milestones`
- a duplicate holiday date, a holiday without `date`, or `show_marker` without a `label`
- a group that names an unknown id, an id in two groups, or a duplicate group name
- an item id that starts with `__group_` (reserved for the emitted phase bars)
- a `project.output` that is not a plain filename
- a calendar so over-constrained that no working day exists within 10 years

The schedule report also flags any milestone that lands on a closed day.

## Examples
- **`example.json`** — a minimal starter: two developers, a dependency, a milestone. Copy
  this file to begin your own chart. Its render:

  ![Minimal example Gantt chart](https://raw.githubusercontent.com/meet-brad-ch/ganttuml/main/docs/example.png)

- **`example-advanced.json`** — exercises **every** feature except `show_footer: false`.
  It contains:
  - both milestone modes (`on` and `depends_on`, single and list)
  - `jira` + `url` links (one item carries both — `url` wins)
  - an ignored `color` field, PTO, and `works_on`
  - a disabled holiday and a `start` floor
  - phase groups and the critical path
  - every appearance option, set explicitly

  Its render (see also the live link at the top of this file):

  ![Advanced example Gantt chart](https://raw.githubusercontent.com/meet-brad-ch/ganttuml/main/docs/example-advanced.png)

## Development
The tool itself has **no runtime dependencies**. The test suite uses pytest (dev-only):
```bash
pip install pytest pytest-cov
pytest                                              # run the tests
pytest --cov=ganttuml --cov-report=term-missing    # with the 100% coverage gate
```
- Coverage is enforced at **100%** (configured in `pyproject.toml`). The same file holds the
  ruff lint settings (line length 100).
- CI (GitHub Actions, `.github/workflows/ci.yml`) runs ruff and the test suite with the
  coverage gate on every push and pull request, on Python 3.10 and 3.12.
- A published GitHub release triggers `.github/workflows/publish.yml`. That workflow
  builds the package and uploads it to PyPI via trusted publishing (no stored tokens).
- **Tested with:** Ubuntu 22.04 LTS, Python 3.10, pytest 8, and
  [`plantuml/plantuml:1.2026.6`](https://hub.docker.com/r/plantuml/plantuml/tags).
  `render.sh` pins this image by tag **and** digest, so renders are reproducible. To
  upgrade, or to switch to `latest`, edit the `plantuml_image` variable at the top of
  `render.sh` (instructions inline).

## Architecture
`ganttuml.py` is a single file organized as a one-way pipeline: **load → validate →
schedule → emit → report**. The parsed JSON flows through the pipeline as plain dicts. The
code never mutates it. Each stage is a pure function over that data. `Calendar` —
per-developer availability (weekends, holidays, `pto`, `works_on`) — is the one stateful
concept and the one class. The emitter writes the `.puml` statements in two phases:
definitions first, then dependency-ordered positioning. PlantUML evaluates its input
sequentially, so the emission order itself carries the scheduling semantics. The runtime
uses only the Python standard library.

## License
MIT — see [LICENSE](LICENSE).
