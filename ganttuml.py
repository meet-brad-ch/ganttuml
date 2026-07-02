#!/usr/bin/env python3
"""ganttuml — developer-oriented PlantUML Gantt generator.

Describe developers and their ordered tasks/milestones in a JSON file; get a
PlantUML `.puml` (render to PNG/SVG with the plantuml docker — see ./example.sh). Tasks
under a developer auto-link in order (one task
at a time); add `depends_on` (one id or a list) for extra links — tasks and
milestones alike. Every item has an `id` used for linking. The calendar is "all
open": weekends + holidays are modeled as per-person off-days (so one developer can
work a normally-closed day via `works_on`) and shaded purely cosmetically. Optional
per-item Jira link becomes a clickable hyperlink in the SVG.

Scheduling is left entirely to PlantUML: definitions are emitted grouped by
developer (the visual lanes), then every dependency/positioning statement is
emitted in DEPENDENCY (topological) order so that each `->` source is already
declared and each milestone's `happens at` snapshots an already-positioned target.
PlantUML's evaluation rules require this ordering (see
https://plantuml.com/gantt-diagram). The Python schedule() is used only for the
textual report, never for placement.

  python3 ganttuml.py                 # validate + write output/example.puml + print schedule
  python3 ganttuml.py --input my.json # use a different source
  # rendering is done by the shell scripts via the plantuml docker, e.g. ./example.sh

See README.md for the JSON schema.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONE = datetime.timedelta(days=1)


class SourceError(Exception):
    """Raised on invalid input; reported to the user without a traceback."""


# --------------------------------------------------------------------------- load
def load(path: Path) -> dict:
    try:
        text = path.read_text()
    except FileNotFoundError:
        raise SourceError(f"input file not found: {path}") from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SourceError(_json_error(path, text, e)) from e


def _json_error(path: Path, text: str, e: json.JSONDecodeError) -> str:
    """Rich JSON parse error: the message, the offending line with a caret at the
    column, a few lines of context, and a hint for the common mistakes.

    Intentionally elaborate: the input is hand-edited JSON, so the usual mistakes
    (trailing commas, unquoted keys) deserve a pinpointed, actionable message."""
    lines = text.split("\n")
    out = [f"{path} is not valid JSON: {e.msg}",
           f"  at line {e.lineno}, column {e.colno} (char {e.pos})", ""]
    lo, hi = max(1, e.lineno - 2), min(len(lines), e.lineno + 2)
    width = len(str(hi))
    for n in range(lo, hi + 1):
        prefix = f"  {'->' if n == e.lineno else '  '} {n:>{width}} | "
        out.append(prefix + lines[n - 1])
        if n == e.lineno:
            out.append(" " * len(prefix) + " " * (e.colno - 1) + "^")
    hint = _json_hint(e, lines)
    if hint:
        out += ["", "  hint: " + hint]
    return "\n".join(out)


def _json_hint(e: json.JSONDecodeError, lines: list[str]) -> str:
    cur = lines[e.lineno - 1] if 0 <= e.lineno - 1 < len(lines) else ""
    after = cur[e.colno - 1:].lstrip()
    msg = e.msg
    if msg.startswith("Expecting value") and after[:1] in ("]", "}"):
        return (f"trailing comma — JSON forbids a ',' before '{after[:1]}'; "
                f"remove the comma at the end of line {e.lineno - 1}.")
    if msg.startswith("Expecting value"):
        return "missing/invalid value here (a bare word needs quotes, or a stray comma/colon)."
    if msg.startswith("Expecting property name"):
        return "trailing comma before '}', or a key that isn't wrapped in \"double quotes\"."
    if msg.startswith("Expecting ',' delimiter"):
        return "missing comma between two items, or an unterminated string/array/object just above."
    if msg.startswith("Expecting ':' delimiter"):
        return "an object key must be followed by ':' — check this key/value pair."
    if "Extra data" in msg:
        return "extra content after the top-level object — a duplicated block or an unbalanced ]/}."
    if "Unterminated string" in msg:
        return "a string is missing its closing double-quote on this line."
    return ""


def _date(s: str, what: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        raise SourceError(f"{what}: invalid date {s!r} (expected YYYY-MM-DD)") from None


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _enabled_holidays(src: dict) -> set[datetime.date]:
    """Dates of holidays that actually close the calendar (`enabled: false` ones don't)."""
    return {_date(h["date"], "holiday")
            for h in src["project"].get("holidays", []) if h.get("enabled", True)}


def _dates(values, what) -> set[datetime.date]:
    """Parse an optional list of YYYY-MM-DD strings into a date set (`what` labels errors)."""
    return {_date(x, what) for x in values or []}


def all_items(src: dict):
    """Yield (item, developer_or_None) for every task/milestone in the file."""
    for dev in src.get("developers", []):
        for it in dev.get("items", []):
            yield it, dev
    for ms in src.get("global_milestones", []):
        yield ms, None


# --------------------------------------------------------------------------- dependency graph
def _dep_graph(src: dict):
    """Return (item_by_id, edges). edges[id] is the ordered, de-duped list
    of ids that `id` depends on: its `depends_on` plus, for a task, the previous task
    in the same lane (the implicit one-task-at-a-time auto-link)."""
    item_by_id: dict[str, dict] = {}
    edges: dict[str, list[str]] = {}
    for it, _dev in all_items(src):
        iid = it["id"]
        item_by_id[iid] = it
        edges[iid] = []

    def add(owner, dep):
        if dep not in edges[owner]:
            edges[owner].append(dep)

    for dev in src.get("developers", []):
        prev_task = None
        for it in dev.get("items", []):
            iid = it["id"]
            for dep in _as_list(it.get("depends_on")):
                add(iid, dep)
            if it["type"] == "task":
                if prev_task is not None:
                    add(iid, prev_task)
                prev_task = iid
    for ms in src.get("global_milestones", []):
        for dep in _as_list(ms.get("depends_on")):
            add(ms["id"], dep)
    return item_by_id, edges


def _topo_order(edges: dict[str, list[str]]) -> list[str]:
    """Ids ordered so every id appears after all ids it depends on. Iteration follows
    declaration order, so independent items keep their declared order (stable output)."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(n):
        if n in seen:
            return
        seen.add(n)
        for dep in edges.get(n, ()):
            visit(dep)
        order.append(n)

    for n in edges:
        visit(n)
    return order


# --------------------------------------------------------------------------- validate
# Allowed keys per object level. Any other key is rejected — fail fast on typos — except
# keys starting with "_" (the JSON comment convention) and `color`, which is documented
# as accepted-but-ignored (bars always use the uniform theme).
_TOP_KEYS = {"project", "developers", "global_milestones"}
_PROJECT_KEYS = {"title", "start", "output", "version", "show_footer", "show_today",
                 "show_critical", "weekend_color", "today_color", "undone_color",
                 "bar_color", "critical_color", "arrow_color", "header_color",
                 "jira_base_url", "holidays"}
_DEV_KEYS = {"name", "pto", "works_on", "items", "color"}
_TASK_KEYS = {"type", "id", "name", "days", "done", "depends_on", "start", "jira", "url", "color"}
_MILESTONE_KEYS = {"type", "id", "name", "on", "depends_on", "jira", "url", "color"}
_HOLIDAY_KEYS = {"date", "label", "show_marker", "enabled"}

_PROJECT_STR_KEYS = ("title", "start", "output", "version", "jira_base_url", "weekend_color",
                     "today_color", "undone_color", "bar_color", "critical_color",
                     "arrow_color", "header_color")
_PROJECT_BOOL_KEYS = ("show_footer", "show_today", "show_critical")


def _check_obj(v, where: str) -> None:
    if not isinstance(v, dict):
        raise SourceError(f"{where} must be an object, got {type(v).__name__}")


def _check_list(v, where: str) -> None:
    if v is not None and not isinstance(v, list):
        raise SourceError(f"{where} must be a list, got {type(v).__name__}")


def _check_keys(obj: dict, allowed: set, where: str) -> None:
    unknown = sorted(k for k in obj if k not in allowed and not k.startswith("_"))
    if unknown:
        raise SourceError(f"{where}: unknown key(s) {', '.join(map(repr, unknown))} "
                          "(keys starting with '_' are treated as comments)")


def _check_structure(src) -> None:
    """Shape pass — container types, string fields, required subkeys, and unknown-key
    rejection. Runs before the semantic checks so they can index into dicts safely."""
    _check_obj(src, "top level")
    _check_keys(src, _TOP_KEYS, "top level")
    if "project" in src:
        p = src["project"]
        _check_obj(p, "project")
        _check_keys(p, _PROJECT_KEYS, "project")
        for k in _PROJECT_STR_KEYS:
            if k in p and not isinstance(p[k], str):
                raise SourceError(f"project.{k} must be a string")
        for k in _PROJECT_BOOL_KEYS:
            if k in p and not isinstance(p[k], bool):
                raise SourceError(f"project.{k} must be true or false")
        _check_list(p.get("holidays"), "project.holidays")
        for i, h in enumerate(p.get("holidays") or []):
            where = f"project.holidays[{i}]"
            _check_obj(h, where)
            _check_keys(h, _HOLIDAY_KEYS, where)
            if not isinstance(h.get("date"), str):
                raise SourceError(f"{where}: needs a 'date' string (YYYY-MM-DD)")
            if "label" in h and not isinstance(h["label"], str):
                raise SourceError(f"{where}: 'label' must be a string")
            if h.get("show_marker") and "label" not in h:
                raise SourceError(f"{where}: 'show_marker' requires a 'label'")
            for k in ("show_marker", "enabled"):
                if k in h and not isinstance(h[k], bool):
                    raise SourceError(f"{where}: '{k}' must be true or false")
    _check_list(src.get("developers"), "developers")
    for d in src.get("developers") or []:
        _check_obj(d, "developers entry")
        name = d.get("name")
        if not isinstance(name, str) or not name:
            raise SourceError("every developer needs a non-empty string 'name'")
        _check_keys(d, _DEV_KEYS, f"developer {name}")
        for k in ("pto", "works_on"):
            _check_list(d.get(k), f"{name}.{k}")
            if not all(isinstance(x, str) for x in d.get(k) or []):
                raise SourceError(f"{name}.{k} entries must be YYYY-MM-DD strings")
        _check_list(d.get("items"), f"{name}.items")
        for it in d.get("items") or []:
            _check_item(it, f"{name}/")
    _check_list(src.get("global_milestones"), "global_milestones")
    for ms in src.get("global_milestones") or []:
        _check_item(ms, "global/")


def _check_item(it, where: str) -> None:
    _check_obj(it, f"{where}item")
    iid = it.get("id", "?")
    if it.get("type") == "task":
        _check_keys(it, _TASK_KEYS, f"{where}{iid}")
    elif it.get("type") == "milestone":
        _check_keys(it, _MILESTONE_KEYS, f"{where}{iid}")
    # a bad or missing `type` is reported by the semantic pass in validate()
    if not isinstance(it.get("name"), str) or not it.get("name"):
        raise SourceError(f"{where}{iid}: item needs a non-empty string 'name'")
    dep = it.get("depends_on")
    if dep is not None and not isinstance(dep, str) and not (
            isinstance(dep, list) and all(isinstance(x, str) for x in dep)):
        raise SourceError(f"{where}{iid}: depends_on must be an id or a list of ids")
    for k in ("jira", "url"):
        if k in it and not isinstance(it[k], str):
            raise SourceError(f"{where}{iid}: '{k}' must be a string")


def validate(src: dict) -> None:
    _check_structure(src)
    if "project" not in src or "start" not in src["project"]:
        raise SourceError("project.start is required")
    _date(src["project"]["start"], "project.start")
    out_name = src["project"].get("output", "example.puml")
    if Path(out_name).name != out_name or "\\" in out_name:  # keep writes inside output/
        raise SourceError(f"project.output must be a plain filename, got {out_name!r}")
    seen_hol: set[datetime.date] = set()
    for h in src["project"].get("holidays", []):  # checks disabled holidays' dates too
        hd = _date(h["date"], "holiday")
        if hd in seen_hol:
            raise SourceError(f"duplicate holiday date {h['date']}")
        seen_hol.add(hd)

    names = [d["name"] for d in src.get("developers", [])]  # non-empty per _check_structure
    if len(names) != len(set(names)):
        raise SourceError(f"developer names must be unique: {names}")
    # Bars use a uniform theme color (MS-Project blue) + red for the critical path; any
    # per-developer/per-item `color` is ignored (see emit()), so no color is required.

    ids: dict[str, str] = {}
    for it, dev in all_items(src):
        where = f"{dev['name']}/" if dev else "global/"
        iid = it.get("id")
        if not iid:
            raise SourceError(f"{where}{it.get('name','?')}: missing id")
        if iid in ids:
            raise SourceError(f"duplicate id {iid!r} (in {ids[iid]} and {where})")
        ids[iid] = where
        typ = it.get("type")
        if typ not in ("task", "milestone"):
            raise SourceError(f"{iid}: type must be 'task' or 'milestone', got {typ!r}")
        if dev is None and typ != "milestone":  # emit/schedule have no lane for a global task
            raise SourceError(f"{iid}: global_milestones may only contain milestones")
        if typ == "task":
            if not isinstance(it.get("days"), int) or it["days"] < 1:
                raise SourceError(f"{iid}: task needs integer days >= 1")
            if "done" not in it:
                raise SourceError(f"{iid}: task requires 'done' (integer percent 0–100)")
            dn = it["done"]
            if isinstance(dn, bool) or not isinstance(dn, int) or not 0 <= dn <= 100:
                raise SourceError(f"{iid}: 'done' must be an integer percent 0–100")
            if "start" in it:  # optional floor ("no earlier than"); must parse
                _date(it["start"], f"{iid}.start")
        else:
            anchors = [k for k in ("on", "depends_on") if it.get(k)]
            if len(anchors) != 1:
                raise SourceError(f"{iid}: milestone needs exactly one of on/depends_on")
            if it.get("on"):
                _date(it["on"], f"{iid}.on")
            # `done`/`start` on a milestone are rejected by the unknown-key structure pass
        for d in dev.get("pto", []) if dev else []:
            _date(d, f"{dev['name']} pto")

    # works_on: dates a developer works despite a normal closure. Must parse, must not
    # also be PTO, and must actually BE a closed day — a no-op works_on is almost
    # always a typo'd date, so it fails fast.
    hols = _enabled_holidays(src)
    for d in src.get("developers", []):
        name = d.get("name", "?")
        works = _dates(d.get("works_on"), f"{name} works_on")
        ptos = _dates(d.get("pto"), f"{name} pto")
        clash = works & ptos
        if clash:
            raise SourceError(f"{name}: date(s) in both works_on and pto: "
                              f"{', '.join(sorted(map(str, clash)))}")
        for wd in works:
            if not (wd.weekday() >= 5 or wd in hols):
                raise SourceError(f"{name}: works_on {wd} is already a working day "
                                  "(remove it or fix the date)")

    # dependency references must exist + be acyclic (the only link mechanism is
    # `depends_on` plus the implicit per-lane task auto-link).
    _, edges = _dep_graph(src)
    for iid, deps in edges.items():
        for d in deps:
            _require_id(d, ids, iid, "depends_on")
    _check_acyclic(edges)


def _require_id(ref: str, ids: dict, owner: str, field: str) -> None:
    if ref == owner:
        raise SourceError(f"{owner}: {field} cannot reference itself")
    if ref not in ids:
        raise SourceError(f"{owner}: {field} references unknown id {ref!r}")


def _check_acyclic(edges: dict[str, list[str]]) -> None:
    white, gray, black = 0, 1, 2  # DFS states: unvisited / in progress / done
    color = {n: white for n in edges}

    def dfs(n, stack):
        color[n] = gray
        for m in edges[n]:
            if color[m] == gray:
                cyc = stack[stack.index(m):] + [m]
                raise SourceError("cyclic dependency: " + " -> ".join(cyc))
            if color[m] == white:
                dfs(m, stack + [m])
        color[n] = black

    for n in edges:
        if color[n] == white:
            dfs(n, [n])


# ------------------------------------------------------- calendar / schedule (report only)
class Calendar:
    def __init__(self, src: dict):
        self.holidays = _enabled_holidays(src)
        self.pto = {d["name"]: _dates(d.get("pto"), "pto")
                    for d in src.get("developers", [])}
        # works_on: dates a developer works despite being a normally-closed day.
        self.works_on = {d["name"]: _dates(d.get("works_on"), "works_on")
                         for d in src.get("developers", [])}

    def is_open(self, d: datetime.date, dev) -> bool:
        if dev and d in self.works_on.get(dev, set()):
            return True  # this person works a normally-closed day
        if d.weekday() >= 5:
            return False  # Saturday/Sunday — always closed
        if d in self.holidays:
            return False
        return not (dev and d in self.pto.get(dev, set()))

    def on_or_after(self, d, dev):
        for _ in range(3660):  # ~10y guard against an all-closed calendar
            if self.is_open(d, dev):
                return d
            d += ONE
        raise SourceError("no working day found within 10 years — calendar over-constrained")

    def after(self, d, dev):
        return self.on_or_after(d + ONE, dev)


def schedule(src: dict) -> dict[str, tuple]:
    """Mirror the emitted constraints to report dates + lint. NOT used to place bars
    (PlantUML does that from the dependency-ordered statements). Iterates to a fixpoint
    so cross-lane chains resolve regardless of order."""
    cal = Calendar(src)
    start = _date(src["project"]["start"], "project.start")
    res: dict[str, tuple] = {}  # id -> (start, end, dev_name, type)

    def place_task(it, dev_name, lower):
        s = cal.on_or_after(lower, dev_name)
        e = s
        for _ in range(it["days"] - 1):
            e = cal.after(e, dev_name)
        res[it["id"]] = (s, e, dev_name, "task")

    def lowers_from_deps(it, dev_name):
        # Bound = the next day the CONSUMING task's resource can work after the dep ends.
        # PlantUML's `->` places the target on ITS resource's next open day, which may be
        # a works_on weekend that the nobody-specific (None) calendar would skip.
        return [cal.after(res[dep][1], dev_name)
                for dep in _as_list(it.get("depends_on")) if dep in res]

    n_items = (sum(len(d.get("items", [])) for d in src.get("developers", []))
               + len(src.get("global_milestones", [])))
    # Every pass re-places all items in declaration order, so only a dependency declared
    # AFTER its consumer costs an extra pass; a chain has < n_items such edges, so
    # n_items + 1 passes always suffice (the snapshot equality check exits earlier).
    converged = False
    for _ in range(n_items + 1):
        snapshot = dict(res)
        for dev in src.get("developers", []):
            prev_end = None
            for it in dev.get("items", []):
                if it["type"] == "task":
                    lows = [start]
                    if prev_end is not None:
                        lows.append(cal.after(prev_end, dev["name"]))
                    lows += lowers_from_deps(it, dev["name"])
                    if it.get("start"):  # floor: task can't begin before this date
                        lows.append(_date(it["start"], f"{it['id']}.start"))
                    place_task(it, dev["name"], max(lows))
                    prev_end = res[it["id"]][1]
                else:
                    _place_milestone(it, dev["name"], res)
        for ms in src.get("global_milestones", []):
            _place_milestone(ms, None, res)
        if res == snapshot:
            converged = True
            break
    if not converged or len(res) != n_items:  # impossible for validated input; never silent
        raise SourceError("internal: schedule failed to converge — please report this input")
    return res


def _place_milestone(ms, dev_name, res):
    if ms.get("on"):
        d = _date(ms["on"], f"{ms['id']}.on")
    else:  # depends_on -> latest end among dependencies
        ends = [res[i][1] for i in _as_list(ms.get("depends_on")) if i in res]
        if not ends:
            return
        d = max(ends)
    res[ms["id"]] = (d, d, dev_name, "milestone")


def _critical(src: dict, sched: dict, cal, start: datetime.date):
    """Resource-constrained critical path. Returns (crit_ids, crit_edges).

    Walks back from the makespan (latest end) through each item's *binding* predecessors
    — the ones whose end actually sets the item's start — using the same constraints
    schedule() applies: depends_on, the one-task-at-a-time lane auto-link, and start
    floors. Floors/project-start/on-dates are fixed anchors that end a chain. Ties seed
    multiple paths. Binding is compared on the raw max (pre on_or_after rounding), so the
    red set is never under-marked (at worst slightly generous)."""
    item_by_id = {it["id"]: it for it, _dev in all_items(src)}
    lane_prev: dict[str, str] = {}  # task id -> previous TASK id in the same lane
    for dev in src.get("developers", []):
        prev = None
        for it in dev.get("items", []):
            if it["type"] == "task":
                if prev is not None:
                    lane_prev[it["id"]] = prev
                prev = it["id"]

    def binding_preds(iid):
        # every id here is in sched: seeds come from sched and preds are membership-filtered
        _s, _e, dev, typ = sched[iid]
        it = item_by_id[iid]
        if typ == "milestone":
            if it.get("on"):
                return []  # fixed anchor
            # non-empty post-validation: a depends_on milestone has >= 1 dep, all placed
            deps = [d for d in _as_list(it.get("depends_on")) if d in sched]
            hi = max(sched[d][1] for d in deps)
            return [d for d in deps if sched[d][1] == hi]
        contrib: dict[str, datetime.date] = {}
        lp = lane_prev.get(iid)
        if lp and lp in sched:
            contrib[lp] = cal.after(sched[lp][1], dev)
        for d in _as_list(it.get("depends_on")):
            if d in sched:
                contrib[d] = cal.after(sched[d][1], dev)  # same rule as lowers_from_deps
        floors = [start]
        if it.get("start"):
            floors.append(_date(it["start"], f"{iid}.start"))
        hi = max(list(contrib.values()) + floors)
        return [pid for pid, dt in contrib.items() if dt == hi]

    ends = [e for (_s, e, _d, _t) in sched.values()]
    if not ends:
        return set(), set()
    makespan = max(ends)
    crit = {iid for iid, (_s, e, _d, _t) in sched.items() if e == makespan}
    crit_edges: set[tuple[str, str]] = set()
    stack = list(crit)
    while stack:
        cur = stack.pop()
        for pr in binding_preds(cur):
            crit_edges.add((pr, cur))
            if pr not in crit:
                crit.add(pr)
                stack.append(pr)
    return crit, crit_edges


# --------------------------------------------------------------------------- emit
def _closed_days(src: dict, start: datetime.date, end: datetime.date) -> list[datetime.date]:
    """Dates in [start, end] that are closed-by-default — weekends (Sat/Sun) plus enabled
    holidays. Drives cosmetic shading and per-person off-days in the all-open model."""
    holidays = _enabled_holidays(src)
    days, d = [], start
    while d <= end:
        if d.weekday() >= 5 or d in holidays:
            days.append(d)
        d += ONE
    return days


def _link_url(src: dict, it: dict):
    if it.get("url"):
        return it["url"]
    base = src["project"].get("jira_base_url")
    if it.get("jira") and base:
        return f"{base.rstrip('/')}/browse/{it['jira']}"
    return None


def emit(src: dict) -> str:
    p = src["project"]
    item_by_id, edges = _dep_graph(src)
    out: list[str] = []
    w = out.append

    # MS-Project-style theme: uniform blue bars (no per-lane colors), the critical path in
    # red (bars/diamonds/links), grey link arrows, a light-blue timeline header. The undone
    # part of a % done bar is shown by its fill (PlantUML hardcodes the bar border to 1px and
    # ignores <style> line thickness).
    bar_color = p.get("bar_color", "#8ABBED")
    crit_color = p.get("critical_color", "#E8473F")

    start = _date(p["start"], "project.start")
    cal = Calendar(src)
    sched = schedule(src)
    if p.get("show_critical", False):  # opt-in red critical-path marking (default off)
        crit_ids, crit_edges = _critical(src, sched, cal, start)
    else:
        crit_ids, crit_edges = set(), set()

    _emit_header(w, p)
    _emit_calendar(w, src, p, sched, start)
    _emit_definitions(w, src, crit_ids, bar_color, crit_color)
    _emit_positioning(w, src, item_by_id, edges, crit_ids, crit_edges, crit_color)

    w("@endgantt")
    return "\n".join(out) + "\n"


def _emit_header(w, p):
    """@startgantt, the <style> theme block, title/footer, and display options."""
    w("@startgantt")
    w("<style>")
    w("ganttDiagram {")
    w("  undone {")
    w(f"    BackGroundColor {p.get('undone_color', '#DDDDDD')}")
    w("  }")
    w("  arrow {")
    w(f"    LineColor {p.get('arrow_color', '#B0B7C3')}")
    w("  }")
    w("  timeline {")
    w(f"    BackGroundColor {p.get('header_color', '#DCE9F8')}")
    w("  }")
    w("}")
    w("</style>")
    if p.get("title"):
        w(f"title {p['title']}")
    if p.get("show_footer", True):  # bottom-centre stamp: optional version + generation date
        foot = []
        if p.get("version"):
            foot.append(f"Version {p['version']}")
        foot.append(f"Generated {datetime.date.today()}")
        w(f"footer {'  |  '.join(foot)}")
    w(f"Project starts {p['start']}")
    w("hide resources footbox")
    w("hide resources names")  # drop the {Resource} suffix; the lane label already names them
    w("")


def _emit_calendar(w, src, p, sched, start):
    """Cosmetic day bands + per-person off-days + holiday markers.

    Calendar is ALL-OPEN: no global closures. Weekends + holidays become per-person
    off-days (so one developer can work a normally-closed day via works_on), shaded
    cosmetically (day coloring is visual-only; PlantUML has no native per-resource
    "open" directive)."""
    ends = [e for (_s, e, _d, _t) in sched.values()]
    horizon = max(ends) if ends else start
    closed = _closed_days(src, start, horizon)
    closed_set = set(closed)

    today = datetime.date.today()
    mark_today = p.get("show_today", True) and start <= today <= horizon
    shade_days = [d for d in closed if not (mark_today and d == today)]
    if shade_days or mark_today:
        w("' ---- Weekend/holiday shading + today marker (cosmetic; no scheduling effect) ----")
        color = p.get("weekend_color", "#EFEFEF")
        for d in shade_days:
            w(f"{d} is colored in {color}")
        if mark_today:
            w(f"{today} is colored in {p.get('today_color', '#4F9BFF40')}")
        w("")

    off_by_dev = []
    for d in src.get("developers", []):
        if not any(it["type"] == "task" for it in d.get("items", [])):
            continue  # milestone-only resources never work -> off-days are noise
        works = _dates(d.get("works_on"), f"{d['name']} works_on")
        ptos = _dates(d.get("pto"), f"{d['name']} pto")
        off = sorted((closed_set - works) | ptos)
        if off:
            off_by_dev.append((d["name"], off))
    if off_by_dev:
        w("' ---- Per-person off: weekends + holidays + PTO (minus works_on) ----")
        for name, off in off_by_dev:
            for d in off:
                w(f"{{{name}}} is off on {d}")
        w("")

    markers = [h for h in p.get("holidays", [])
               if h.get("show_marker") and h.get("enabled", True)]
    if markers:
        w("-- Holidays --")
        for h in markers:
            w(f"[{h['label']}] happens {h['date']}")
        w("")


def _emit_definitions(w, src, crit_ids, bar_color, crit_color):
    """Phase 1: DEFINITIONS (these create the rows; grouped by developer lane).

    Tasks have no constraint yet -> they default to project start; on-milestones carry
    their own absolute date. depends_on-milestones are declared in Phase 2."""
    for dev in src.get("developers", []):
        w(f"-- {dev['name']} --")
        for it in dev.get("items", []):
            if it["type"] == "task":
                color = crit_color if it["id"] in crit_ids else bar_color
                _emit_task_def(w, src, it, dev["name"], color)
            elif it.get("on"):
                _emit_milestone(w, src, it, it["id"] in crit_ids, crit_color)
        w("")

    gms = src.get("global_milestones", [])
    g_on = [m for m in gms if m.get("on")]
    if g_on:  # absolute global milestones are sources -> declare before Phase 2
        w("-- Milestones --")
        for ms in g_on:
            _emit_milestone(w, src, ms, ms["id"] in crit_ids, crit_color)
        w("")


def _emit_positioning(w, src, item_by_id, edges, crit_ids, crit_edges, crit_color):
    """Phase 2: POSITIONING in dependency (topological) order.

    PlantUML rules: `->` needs its source already declared; `happens at` snapshots
    the target's current position; multiple incoming arrows -> the latest wins.
    Emit task `->` whose source is already declared (Phase-1 task/on-milestone), then
    each depends_on-milestone (topo order) followed by the arrows it itself sources ->
    every reference resolves and every snapshot is taken after its target is positioned."""
    order = _topo_order(edges)
    dep_ms_ids = {iid for iid, it in item_by_id.items()
                  if it["type"] == "milestone" and not it.get("on")}

    def arrow(s, t):  # critical links drawn red, the rest the themed grey
        if (s, t) in crit_edges:
            w(f"[{s}] -[{crit_color}]-> [{t}]")
        else:
            w(f"[{s}] -> [{t}]")

    # task arrows whose source is already declared (Phase-1 task or on-milestone)
    pre = []
    for iid in order:
        if item_by_id[iid]["type"] == "task":
            pre.extend((s, iid) for s in edges[iid] if s not in dep_ms_ids)
    if pre:
        w("' ---- dependencies (sources declared above) ----")
        for s, t in pre:
            arrow(s, t)
        w("")

    ms_consumers: dict[str, list[str]] = {m: [] for m in dep_ms_ids}
    for iid in order:
        if item_by_id[iid]["type"] == "task":
            for s in edges[iid]:
                if s in dep_ms_ids:
                    ms_consumers[s].append(iid)

    dep_ms_order = [iid for iid in order if iid in dep_ms_ids]
    if dep_ms_order:
        w("-- Milestones --")
        for iid in dep_ms_order:
            _emit_milestone(w, src, item_by_id[iid], iid in crit_ids, crit_color)
            for tid in ms_consumers[iid]:  # arrows this milestone is the source of
                arrow(iid, tid)
        w("")


def _emit_task_def(w, src, it, dev_name, color):
    iid, name = it["id"], it["name"]
    w(f"[{name}] as [{iid}] on {{{dev_name}}} requires {it['days']} days")
    if it.get("start"):  # "no earlier than" floor; PlantUML max-combines it with the ->
        w(f"[{iid}] starts {it['start']}")  # arrows, so a later dependency still wins
    w(f"[{iid}] is colored in {color}")  # uniform theme blue, or red if on the critical path
    if "done" in it:  # completion: filled = colored, remainder = undone-fill (see <style>)
        w(f"[{iid}] is {it['done']}% completed")
    url = _link_url(src, it)
    if url:
        w(f"[{iid}] links to [[{url}]]")


def _emit_milestone(w, src, ms, critical=False, crit_color="#E8473F"):
    iid, name = ms["id"], ms["name"]
    if ms.get("on"):
        w(f"[{name}] as [{iid}] happens {ms['on']}")
    else:  # depends_on -> repeated `happens at`; PlantUML places it at the latest end
        deps = _as_list(ms.get("depends_on"))
        w(f"[{name}] as [{iid}] happens at [{deps[0]}]'s end")
        for dep in deps[1:]:
            w(f"[{iid}] happens at [{dep}]'s end")
    if critical:  # critical-path milestones are red; the rest keep the default black diamond
        w(f"[{iid}] is colored in {crit_color}")
    url = _link_url(src, ms)
    if url:
        w(f"[{iid}] links to [[{url}]]")


# --------------------------------------------------------------------------- report
# Rendering is intentionally NOT done here: ganttuml.py only generates the .puml. The shell
# scripts run the plantuml/plantuml docker to produce PNG/SVG (e.g. ./example.sh).
def report(src: dict) -> None:
    cal = Calendar(src)
    sched = schedule(src)
    start = _date(src["project"]["start"], "project.start")
    if src["project"].get("show_critical", False):
        crit_ids, _crit_edges = _critical(src, sched, cal, start)
    else:
        crit_ids = set()
    items = {it["id"]: it for it, _dev in all_items(src)}
    print("schedule:")
    for iid, (s, e, dev, typ) in sorted(sched.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        tag = "milestone" if typ == "milestone" else f"{s} -> {e}"
        done = items.get(iid, {}).get("done")
        pct = f" ({done}%)" if done is not None else ""
        crit = " [critical]" if iid in crit_ids else ""
        print(f"  {s}  {tag:24} {dev or '-':8} {iid}{pct}{crit}")
        if typ == "milestone" and not cal.is_open(s, dev):
            print(f"      ! note: milestone {iid} lands on a closed day ({s})")
    tasks = [v for v in sched.values() if v[3] == "task"]
    if tasks:
        print(f"makespan: {max(tasks, key=lambda v: v[1])[1]}")
    ends = [e for (_s, e, _d, _t) in sched.values()]
    horizon = max(ends) if ends else start
    today = datetime.date.today()
    if src["project"].get("show_today", True) and start <= today <= horizon:
        print(f"today:    {today} (marked)")
    else:
        print(f"today:    {today} (outside {start}..{horizon} — not marked)")


# --------------------------------------------------------------------------- cli
def main() -> None:
    ap = argparse.ArgumentParser(description="ganttuml — developer Gantt generator")
    ap.add_argument("--input", default="example.json", help="source JSON (default example.json)")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = HERE / in_path
    try:
        src = load(in_path)
        validate(src)
    except SourceError as e:
        sys.exit(f"error: {e}")

    out_dir = HERE / "output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / src["project"].get("output", "example.puml")
    out.write_text(emit(src))
    print(f"wrote {out}")
    report(src)
    print("(render to PNG/SVG with the plantuml docker, e.g. ./example.sh)")


if __name__ == "__main__":
    main()
