"""Tests for ganttuml.py — full statement coverage.

Run:  pytest                                  (tests only)
      pytest --cov=ganttuml --cov-report=term-missing   (with the 100% gate)

`datetime.date.today()` drives the footer and the today marker, so tests that
assert emitted output freeze "today" via the `frozen_today` fixture.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import ganttuml
from ganttuml import (
    Calendar,
    SourceError,
    _as_list,
    _date,
    _dates,
    _enabled_holidays,
    _json_error,
    _json_hint,
    _link_url,
    _topo_order,
    emit,
    load,
    report,
    schedule,
    validate,
)

GANTT_DIR = Path(ganttuml.__file__).resolve().parent
D = datetime.date
# 2026-06-22 is a Monday; 06-27/28 are Sat/Sun; 07-03 is a Friday.


def base(**project):
    """Minimal valid source; keyword args override/extend the project block."""
    src = {"project": {"start": "2026-06-22", "output": "t.puml"}, "developers": []}
    src["project"].update(project)
    return src


def dev(name="Alice", items=None, **kw):
    return {"name": name, "items": items if items is not None else [], **kw}


def task(iid, days=1, done=0, **kw):
    return {"type": "task", "id": iid, "name": iid.upper(), "days": days, "done": done, **kw}


def ms(iid, **kw):
    return {"type": "milestone", "id": iid, "name": iid.upper(), **kw}


class FrozenDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 2)


@pytest.fixture
def frozen_today(monkeypatch):
    monkeypatch.setattr(ganttuml.datetime, "date", FrozenDate)


def err(src) -> str:
    """validate() must raise; return the message."""
    with pytest.raises(SourceError) as ei:
        validate(src)
    return str(ei.value)


# --------------------------------------------------------------------------- JSON errors
def decode_error(doc: str) -> json.JSONDecodeError:
    try:
        json.loads(doc)
    except json.JSONDecodeError as e:
        return e
    raise AssertionError("document parsed unexpectedly")


@pytest.mark.parametrize("doc,fragment", [
    ('[1,]', "trailing comma"),
    ('{"a": nope}', "missing/invalid value"),
    ('{,}', "double quotes"),
    ('{"a": 1 "b": 2}', "missing comma"),
    ('{"a" 1}', "must be followed by ':'"),
    ('{"a": 1} x', "extra content"),
    ('{"a": "b', "closing double-quote"),
])
def test_json_hint_branches(doc, fragment):
    e = decode_error(doc)
    assert fragment in _json_hint(e, doc.split("\n"))


def test_json_hint_unknown_message_has_no_hint():
    e = json.JSONDecodeError("Invalid control character at", "{}", 0)
    assert _json_hint(e, ["{}"]) == ""


def test_json_hint_line_out_of_range():
    e = json.JSONDecodeError("Expecting value", "x", 0)
    assert _json_hint(e, []) == "missing/invalid value here " \
        "(a bare word needs quotes, or a stray comma/colon)."


def test_json_error_format_with_caret_and_hint():
    doc = '{\n  "a": 1,\n  "b": nope\n}'
    msg = _json_error(Path("f.json"), doc, decode_error(doc))
    assert "f.json is not valid JSON" in msg
    lines = msg.split("\n")
    marked = [i for i, ln in enumerate(lines) if ln.startswith("  -> ")]
    assert len(marked) == 1 and '"b": nope' in lines[marked[0]]
    assert lines[marked[0] + 1].endswith("^")     # caret under the offending column
    assert "hint:" in msg


def test_json_error_without_hint():
    e = json.JSONDecodeError("Invalid control character at", "{}", 0)
    assert "hint:" not in _json_error(Path("f.json"), "{}", e)


def test_load(tmp_path):
    with pytest.raises(SourceError, match="input file not found"):
        load(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    with pytest.raises(SourceError, match="is not valid JSON"):
        load(bad)
    good = tmp_path / "good.json"
    good.write_text('{"a": 1}')
    assert load(good) == {"a": 1}


# --------------------------------------------------------------------------- helpers
def test_date():
    assert _date("2026-06-22", "x") == D(2026, 6, 22)
    with pytest.raises(SourceError, match="x: invalid date 'nope'"):
        _date("nope", "x")
    with pytest.raises(SourceError, match="invalid date None"):
        _date(None, "x")


def test_as_list():
    assert _as_list(None) == []
    assert _as_list("a") == ["a"]
    assert _as_list(["a", "b"]) == ["a", "b"]


def test_dates_and_enabled_holidays():
    assert _dates(None, "x") == set()
    assert _dates(["2026-06-22"], "x") == {D(2026, 6, 22)}
    src = base(holidays=[{"date": "2026-07-03", "label": "H"},
                         {"date": "2026-06-19", "label": "J", "enabled": False}])
    assert _enabled_holidays(src) == {D(2026, 7, 3)}


def test_link_url():
    src = base(jira_base_url="https://x.example/")
    assert _link_url(src, {"url": "https://spec", "jira": "P-1"}) == "https://spec"
    assert _link_url(src, {"jira": "P-1"}) == "https://x.example/browse/P-1"
    assert _link_url(base(), {"jira": "P-1"}) is None
    assert _link_url(src, {}) is None


def test_topo_order_stable():
    assert _topo_order({"a": [], "b": ["c"], "c": ["a"]}) == ["a", "c", "b"]


# --------------------------------------------------------------------------- structure pass
def with_dev(d, **project):
    src = base(**project)
    src["developers"] = [d]
    return src


def with_item(it, **project):
    return with_dev(dev(items=[it]), **project)


STRUCTURE_CASES = [
    ([], "top level must be an object"),
    ({**base(), "extra": 1}, "top level: unknown key(s) 'extra'"),
    ({"project": [], "developers": []}, "project must be an object"),
    (base(weekend="#EEE"), "project: unknown key(s) 'weekend'"),
    (base(title=123), "project.title must be a string"),
    (base(version=1.0), "project.version must be a string"),
    (base(bar_color=5), "project.bar_color must be a string"),
    (base(show_today="yes"), "project.show_today must be true or false"),
    (base(holidays={}), "project.holidays must be a list"),
    (base(holidays=["2026-07-03"]), "project.holidays[0] must be an object"),
    (base(holidays=[{"date": "2026-07-03", "disabled": True}]),
     "project.holidays[0]: unknown key(s) 'disabled'"),
    (base(holidays=[{"label": "X"}]), "project.holidays[0]: needs a 'date' string"),
    (base(holidays=[{"date": 3}]), "project.holidays[0]: needs a 'date' string"),
    (base(holidays=[{"date": "2026-07-03", "label": 1}]), "'label' must be a string"),
    (base(holidays=[{"date": "2026-07-03", "show_marker": True}]),
     "'show_marker' requires a 'label'"),
    (base(holidays=[{"date": "2026-07-03", "label": "X", "show_marker": "y"}]),
     "'show_marker' must be true or false"),
    (base(holidays=[{"date": "2026-07-03", "label": "X", "enabled": "n"}]),
     "'enabled' must be true or false"),
    ({"project": base()["project"], "developers": {}}, "developers must be a list"),
    ({"project": base()["project"], "developers": ["x"]}, "developers entry must be an object"),
    (with_dev({"items": []}), "non-empty string 'name'"),
    (with_dev(dev(name="")), "non-empty string 'name'"),
    (with_dev(dev(name=7)), "non-empty string 'name'"),
    (with_dev(dev(workson=["2026-06-27"])), "developer Alice: unknown key(s) 'workson'"),
    (with_dev(dev(pto="2026-06-25")), "Alice.pto must be a list"),
    (with_dev(dev(pto=[1])), "Alice.pto entries must be YYYY-MM-DD strings"),
    (with_dev(dev(works_on=[None])), "Alice.works_on entries must be YYYY-MM-DD strings"),
    (with_dev({"name": "Alice", "items": "build"}), "Alice.items must be a list"),
    (with_dev({"name": "Alice", "items": ["x"]}), "Alice/item must be an object"),
    (with_item(task("t", depends_om="x")), "Alice/t: unknown key(s) 'depends_om'"),
    (with_item(task("t", on="2026-06-24")), "Alice/t: unknown key(s) 'on'"),
    (with_item(ms("m", on="2026-06-24", days=3)), "Alice/m: unknown key(s) 'days'"),
    (with_item({"type": "task", "id": "t", "days": 1, "done": 0}),
     "Alice/t: item needs a non-empty string 'name'"),
    (with_item({"type": "task", "id": "t", "name": "", "days": 1, "done": 0}),
     "non-empty string 'name'"),
    (with_item(task("t", depends_on=5)), "depends_on must be an id or a list of ids"),
    (with_item(task("t", depends_on=[5])), "depends_on must be an id or a list of ids"),
    (with_item(task("t", jira=5)), "Alice/t: 'jira' must be a string"),
    (with_item(task("t", url=5)), "Alice/t: 'url' must be a string"),
    ({**base(), "global_milestones": "x"}, "global_milestones must be a list"),
    ({**base(), "global_milestones": ["x"]}, "global/item must be an object"),
]


@pytest.mark.parametrize("src,fragment", STRUCTURE_CASES)
def test_structure_errors(src, fragment):
    assert fragment in err(src)


def test_underscore_keys_are_comments_everywhere():
    src = {
        "_comment": "top",
        "project": {**base()["project"], "_note": "p",
                    "holidays": [{"_c": 1, "date": "2026-07-03", "label": "X"}]},
        "developers": [{"_c": 1, **dev(items=[{**task("t"), "_why": "x"}])}],
        "global_milestones": [{**ms("m", depends_on="t"), "_c": 1}],
    }
    validate(src)  # must not raise


def test_color_is_tolerated_on_devs_and_items():
    src = with_dev(dev(color="#123456", items=[task("t", color="#654321"),
                                               ms("m", on="2026-06-24", color="#000000")]))
    validate(src)  # must not raise


# --------------------------------------------------------------------------- semantic validate
SEMANTIC_CASES = [
    ({}, "project.start is required"),
    ({"project": {"output": "x.puml"}, "developers": []}, "project.start is required"),
    (base(start="junk"), "project.start: invalid date"),
    (base(output="../evil.puml"), "must be a plain filename"),
    (base(output="/tmp/x.puml"), "must be a plain filename"),
    (base(output="a\\b.puml"), "must be a plain filename"),
    (base(holidays=[{"date": "bad", "label": "X"}]), "holiday: invalid date"),
    (base(holidays=[{"date": "2026-07-03", "label": "A"},
                    {"date": "2026-07-03", "label": "B"}]), "duplicate holiday date"),
    ({**base(), "developers": [dev(), dev()]}, "developer names must be unique"),
    (with_item({"type": "task", "name": "T", "days": 1, "done": 0}), "missing id"),
    (with_dev(dev(items=[task("t"), task("t")])), "duplicate id 't'"),
    (with_item({"type": "epic", "id": "t", "name": "T"}), "type must be 'task' or 'milestone'"),
    ({**base(), "global_milestones": [task("t")]}, "global_milestones may only contain"),
    (with_item(task("t", days=0)), "integer days >= 1"),
    (with_item({"type": "task", "id": "t", "name": "T", "done": 0}), "integer days >= 1"),
    (with_item({"type": "task", "id": "t", "name": "T", "days": 1}), "requires 'done'"),
    (with_item(task("t", done="50")), "integer percent 0–100"),
    (with_item(task("t", done=True)), "integer percent 0–100"),
    (with_item(task("t", done=101)), "integer percent 0–100"),
    (with_item(task("t", start="junk")), "t.start: invalid date"),
    (with_item(ms("m")), "exactly one of on/depends_on"),
    (with_dev(dev(items=[task("t"), ms("m", on="2026-06-24", depends_on="t")])),
     "exactly one of on/depends_on"),
    (with_item(ms("m", on="junk")), "m.on: invalid date"),
    (with_dev(dev(items=[task("t"), {**ms("m", depends_on="t"), "done": 5}])),
     "Alice/m: unknown key(s) 'done'"),
    (with_item({**ms("m", on="2026-06-24"), "start": "2026-06-25"}),
     "Alice/m: unknown key(s) 'start'"),
    (with_dev(dev(pto=["bad"], items=[task("t")])), "Alice pto: invalid date"),
    (with_dev(dev(works_on=["bad"])), "Alice works_on: invalid date"),
    (with_dev(dev(pto=["2026-06-27"], works_on=["2026-06-27"])),
     "in both works_on and pto"),
    (with_dev(dev(works_on=["2026-06-23"])), "already a working day"),
    (with_item(task("t", depends_on="t")), "cannot reference itself"),
    (with_item(task("t", depends_on="ghost")), "references unknown id 'ghost'"),
    (with_dev(dev(items=[task("a", depends_on="b"), ms("b", depends_on="a")])),
     "cyclic dependency:"),
]


@pytest.mark.parametrize("src,fragment", SEMANTIC_CASES)
def test_semantic_errors(src, fragment):
    assert fragment in err(src)


def test_cycle_message_shows_the_path():
    src = with_dev(dev(items=[task("a", depends_on="b"), ms("b", depends_on="a")]))
    msg = err(src)
    assert " -> " in msg and msg.count("a") >= 2


def test_disabled_holiday_is_a_working_day_for_works_on():
    holidays = [{"date": "2026-06-24", "label": "H", "enabled": False}]
    assert "already a working day" in err(
        with_dev(dev(works_on=["2026-06-24"]), holidays=holidays))
    validate(with_dev(dev(works_on=["2026-06-24"]),
                      holidays=[{"date": "2026-06-24", "label": "H"}]))  # enabled -> closed


def test_repo_examples_validate():
    validate(load(GANTT_DIR / "example.json"))
    validate(load(GANTT_DIR / "example-advanced.json"))


# --------------------------------------------------------------------------- calendar
def test_calendar_is_open():
    src = with_dev(dev(pto=["2026-06-24"], works_on=["2026-06-27"], items=[task("t")]),
                   holidays=[{"date": "2026-06-23", "label": "H"},
                             {"date": "2026-06-25", "label": "J", "enabled": False}])
    cal = Calendar(src)
    assert cal.is_open(D(2026, 6, 22), "Alice")          # plain Monday
    assert not cal.is_open(D(2026, 6, 23), "Alice")      # holiday
    assert not cal.is_open(D(2026, 6, 23), None)         # holiday closes for "nobody" too
    assert not cal.is_open(D(2026, 6, 24), "Alice")      # PTO
    assert cal.is_open(D(2026, 6, 24), "Bob")            # someone else's PTO
    assert cal.is_open(D(2026, 6, 25), "Alice")          # disabled holiday -> open
    assert not cal.is_open(D(2026, 6, 27), "Bob")        # Saturday
    assert cal.is_open(D(2026, 6, 27), "Alice")          # works_on Saturday
    assert not cal.is_open(D(2026, 6, 28), "Alice")      # Sunday stays closed


def test_calendar_rolling():
    cal = Calendar(base())
    assert cal.on_or_after(D(2026, 6, 27), None) == D(2026, 6, 29)  # Sat -> Mon
    assert cal.on_or_after(D(2026, 6, 22), None) == D(2026, 6, 22)  # already open
    assert cal.after(D(2026, 6, 26), None) == D(2026, 6, 29)        # Fri -> Mon


def test_calendar_over_constrained():
    pto = [str(D(2026, 6, 22) + datetime.timedelta(days=i)) for i in range(3700)]
    cal = Calendar(with_dev(dev(pto=pto)))
    with pytest.raises(SourceError, match="calendar over-constrained"):
        cal.on_or_after(D(2026, 6, 22), "Alice")


# --------------------------------------------------------------------------- schedule
def sched_of(src):
    validate(src)
    return schedule(src)


def test_lane_sequencing_and_weekend_skip():
    src = with_dev(dev(items=[task("a", days=5), task("b", days=2)]))
    s = sched_of(src)
    assert s["a"] == (D(2026, 6, 22), D(2026, 6, 26), "Alice", "task")
    assert s["b"] == (D(2026, 6, 29), D(2026, 6, 30), "Alice", "task")  # skips the weekend


def test_cross_lane_dependency_and_later_of():
    src = {**base(), "developers": [
        dev("A", [task("a", days=3)]),
        dev("B", [task("b1", days=1), task("b2", days=2, depends_on="a")]),
    ]}
    s = sched_of(src)
    # b2 waits for the later of lane-prev b1 (ends 06-22) and dep a (ends 06-24)
    assert s["b2"][0] == D(2026, 6, 25)


def test_start_floor_holds_and_loses():
    holds = with_dev(dev(items=[task("t", days=1, start="2026-07-01")]))
    assert sched_of(holds)["t"][0] == D(2026, 7, 1)
    loses = {**base(), "developers": [
        dev("A", [task("a", days=9)]),  # ends 2026-07-02
        dev("B", [task("b", days=1, depends_on="a", start="2026-06-24")]),
    ]}
    assert sched_of(loses)["b"][0] == D(2026, 7, 3)  # dependency wins over the floor


def test_start_floor_rolls_off_closed_day():
    src = with_dev(dev(items=[task("t", start="2026-06-27")]))  # Saturday floor
    assert sched_of(src)["t"][0] == D(2026, 6, 29)


def test_pto_is_skipped():
    src = with_dev(dev(pto=["2026-06-23"], items=[task("t", days=2)]))
    assert sched_of(src)["t"] == (D(2026, 6, 22), D(2026, 6, 24), "Alice", "task")


def test_works_on_dependency_boundary_regression():
    # The fixed divergence bug: Bob works Sat 06-27; T ends Fri 06-26; U must start Sat.
    src = {**base(), "developers": [
        dev("A", [task("t", days=5)]),
        dev("B", [task("u", days=2, depends_on="t")], works_on=["2026-06-27"]),
    ]}
    s = sched_of(src)
    assert s["u"] == (D(2026, 6, 27), D(2026, 6, 29), "B", "task")


def test_milestones_on_and_depends():
    src = {**base(), "developers": [
        dev("A", [task("a", days=2), ms("m_on", on="2026-06-24"), ms("m_dep", depends_on="a")]),
        dev("B", [task("b", days=4)]),
    ], "global_milestones": [ms("roll", depends_on=["a", "b"])]}
    s = sched_of(src)
    assert s["m_on"] == (D(2026, 6, 24), D(2026, 6, 24), "A", "milestone")
    assert s["m_dep"][0] == D(2026, 6, 23)             # a's end
    assert s["roll"][0] == D(2026, 6, 25)              # latest of a (06-23) and b (06-25)
    assert s["roll"][2] is None                        # global milestone has no resource


def test_milestone_between_tasks_keeps_lane_chain():
    src = with_dev(dev(items=[task("a", days=2), ms("m", depends_on="a"), task("b", days=1)]))
    assert sched_of(src)["b"][0] == D(2026, 6, 24)     # after a, milestone doesn't block


def test_backward_declaration_needs_extra_passes():
    src = {**base(), "developers": [
        dev("A", [ms("m", depends_on="b"), task("a", days=1, depends_on="b")]),
        dev("B", [task("b", days=2)]),
    ]}
    s = sched_of(src)
    assert s["b"][1] == D(2026, 6, 23)
    assert s["m"][0] == D(2026, 6, 23)
    assert s["a"][0] == D(2026, 6, 24)


def test_days_one_and_empty_project():
    assert sched_of(with_dev(dev(items=[task("t")])))["t"][0] == D(2026, 6, 22)
    assert sched_of(base()) == {}


def test_schedule_convergence_guard():
    # Bypasses validate() on purpose: an unresolvable milestone must fail loudly,
    # never silently vanish from the schedule.
    src = {**base(), "global_milestones": [ms("m", depends_on="ghost")]}
    with pytest.raises(SourceError, match="failed to converge"):
        schedule(src)


# --------------------------------------------------------------------------- critical path
def crit_of(src):
    validate(src)
    s = schedule(src)
    start = _date(src["project"]["start"], "project.start")
    return ganttuml._critical(src, s, Calendar(src), start)


def test_critical_simple_chain():
    src = with_dev(dev(items=[task("a", days=2), task("b", days=3)]))
    ids, edges = crit_of(src)
    assert ids == {"a", "b"} and edges == {("a", "b")}


def test_critical_tie_marks_both_paths():
    src = {**base(), "developers": [
        dev("A", [task("a", days=3)]),
        dev("B", [task("b", days=3)]),
    ]}
    ids, _edges = crit_of(src)
    assert ids == {"a", "b"}


def test_critical_anchors_end_chains():
    # An on-milestone at the makespan and a floored task both anchor without predecessors.
    src = {**base(), "developers": [
        dev("A", [task("a", days=1), ms("m", on="2026-07-10")]),
        dev("B", [task("b", days=1, start="2026-07-01")]),
    ]}
    ids, edges = crit_of(src)
    assert "m" in ids and not edges            # both chains end at fixed anchors
    src2 = with_dev(dev(items=[task("a", days=2), ms("m", depends_on="a")]))
    ids2, edges2 = crit_of(src2)
    assert ids2 == {"a", "m"} and ("a", "m") in edges2


def test_critical_empty_schedule():
    assert crit_of(base()) == (set(), set())


# --------------------------------------------------------------------------- emit
def test_emit_golden_advanced_example(frozen_today):
    src = load(GANTT_DIR / "example-advanced.json")
    validate(src)
    assert emit(src) == EXPECTED_ADVANCED


def test_emit_header_defaults_and_overrides(frozen_today):
    out = emit(base())
    assert "    BackGroundColor #DDDDDD" in out       # undone default
    assert "    LineColor #B0B7C3" in out             # arrow default
    assert "    BackGroundColor #DCE9F8" in out       # header default
    assert "title" not in out                         # no title key
    assert "footer Generated 2026-07-02" in out       # no version -> date only
    out2 = emit(base(title="X", version="9", undone_color="#111111",
                     arrow_color="#222222", header_color="#333333"))
    assert "title X" in out2 and "footer Version 9  |  Generated 2026-07-02" in out2
    assert "#111111" in out2 and "#222222" in out2 and "#333333" in out2
    assert "footer" not in emit(base(show_footer=False))


def test_emit_today_marker(frozen_today):
    long = with_dev(dev(items=[task("t", days=10)]))          # horizon past 07-02
    assert "2026-07-02 is colored in #4F9BFF40" in emit(long)
    assert "2026-07-02 is colored in" not in emit({**long, "project": {
        **long["project"], "show_today": False}})
    outside = base(start="2026-08-03")                        # today before the chart
    assert "4F9BFF" not in emit(outside)
    custom = {**long, "project": {**long["project"], "today_color": "#FF000080"}}
    assert "2026-07-02 is colored in #FF000080" in emit(custom)


def test_emit_no_shading_block_when_nothing_to_shade(frozen_today):
    out = emit(base(start="2020-01-01"))  # Wednesday, no items -> one-day horizon
    assert "Weekend/holiday shading" not in out


def test_emit_offdays_and_weekend_color(frozen_today):
    src = {**base(weekend_color="#ABCDEF"), "developers": [
        dev("A", [task("t", days=6)], pto=["2026-06-24"], works_on=["2026-06-27"]),
        dev("Onlymile", [ms("m", on="2026-06-24")]),
    ]}
    out = emit(src)
    assert "2026-06-27 is colored in #ABCDEF" in out
    assert "{A} is off on 2026-06-24" in out          # PTO
    assert "{A} is off on 2026-06-28" in out          # Sunday
    assert "{A} is off on 2026-06-27" not in out      # works_on Saturday
    assert "{Onlymile} is off on" not in out          # milestone-only lane


def test_emit_holiday_markers(frozen_today):
    src = with_dev(dev(items=[task("t", days=10)]),
                   holidays=[{"date": "2026-06-24", "label": "Shown", "show_marker": True},
                             {"date": "2026-06-25", "label": "NoMarker"},
                             {"date": "2026-06-26", "label": "Off", "show_marker": True,
                              "enabled": False}])
    out = emit(src)
    assert "[Shown] happens 2026-06-24" in out
    assert "NoMarker" not in out and "[Off]" not in out


def test_emit_links_and_done(frozen_today):
    src = with_item(task("t", days=2, done=60, jira="P-1", url="https://spec"),
                    jira_base_url="https://x.example")
    out = emit(src)
    assert "[t] links to [[https://spec]]" in out      # url wins over jira
    assert "[t] is 60% completed" in out
    src2 = with_item(task("t", jira="P-1"), jira_base_url="https://x.example")
    assert "[t] links to [[https://x.example/browse/P-1]]" in emit(src2)


def test_emit_start_floor_line(frozen_today):
    out = emit(with_item(task("t", start="2026-07-01")))
    assert "[t] starts 2026-07-01" in out


def test_emit_critical_marking_opt_in(frozen_today):
    src = with_dev(dev(items=[task("a", days=2), task("b", days=1)]))
    plain = emit(src)
    assert "-[#E8473F]->" not in plain and "is colored in #E8473F" not in plain
    red = emit({**src, "project": {**src["project"], "show_critical": True}})
    assert "[a] is colored in #E8473F" in red and "[a] -[#E8473F]-> [b]" in red
    themed = emit({**src, "project": {**src["project"], "show_critical": True,
                                      "critical_color": "#AA0000", "bar_color": "#0000AA"}})
    assert "[a] -[#AA0000]-> [b]" in themed


def test_emit_global_on_milestone_declared_before_positioning(frozen_today):
    src = {**base(), "developers": [dev("A", [task("a")])],
           "global_milestones": [ms("g", on="2026-06-24")]}
    out = emit(src)
    assert "[G] as [g] happens 2026-06-24" in out


def test_emit_dep_milestone_with_consumer_arrow(frozen_today):
    src = {**base(), "developers": [
        dev("A", [task("a", days=2), ms("m", depends_on="a")]),
        dev("B", [task("b", days=1, depends_on="m")]),
    ]}
    out = emit(src)
    ms_block = out.split("-- Milestones --")[1]
    assert "[M] as [m] happens at [a]'s end" in ms_block
    assert "[m] -> [b]" in ms_block                    # consumer arrow follows declaration


def test_emit_milestone_multi_dep_and_link(frozen_today):
    src = {**base(jira_base_url="https://x.example"), "developers": [
        dev("A", [task("a", days=1)]), dev("B", [task("b", days=2)]),
    ], "global_milestones": [ms("m", depends_on=["a", "b"], jira="P-9")]}
    out = emit(src)
    assert "[M] as [m] happens at [a]'s end" in out
    assert "[m] happens at [b]'s end" in out
    assert "[m] links to [[https://x.example/browse/P-9]]" in out


# --------------------------------------------------------------------------- report
def run_report(src, capsys):
    validate(src)
    report(src)
    return capsys.readouterr().out


def test_report_lines(frozen_today, capsys):
    src = {**base(show_critical=True), "developers": [
        dev("A", [task("a", days=9, done=40)]),
    ], "global_milestones": [ms("m", depends_on="a")]}
    out = run_report(src, capsys)
    assert "schedule:" in out
    assert "a (40%) [critical]" in out
    assert "milestone" in out
    assert "makespan: 2026-07-02" in out
    assert "today:    2026-07-02 (marked)" in out


def test_report_closed_day_milestone_note(frozen_today, capsys):
    src = {**base(), "global_milestones": [ms("m", on="2026-06-27")]}  # Saturday
    out = run_report(src, capsys)
    assert "lands on a closed day (2026-06-27)" in out


def test_report_today_outside_and_no_makespan(frozen_today, capsys):
    out = run_report(base(), capsys)   # no tasks: horizon = start = 06-22 < today
    assert "makespan" not in out
    assert "not marked" in out


# --------------------------------------------------------------------------- CLI / main
def test_main_ok(tmp_path, monkeypatch, capsys):
    src = with_item(task("t"))
    src["project"]["output"] = "pytest-main.puml"
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(src))
    monkeypatch.setattr(sys, "argv", ["ganttuml.py", "--input", str(f)])
    ganttuml.main()
    out = capsys.readouterr().out
    assert "wrote " in out and "pytest-main.puml" in out and "render to PNG/SVG" in out
    written = GANTT_DIR / "output" / "pytest-main.puml"
    assert written.exists()
    written.unlink()


def test_main_error_exits_cleanly(tmp_path, monkeypatch):
    f = tmp_path / "bad.json"
    f.write_text('{"project": {}}')
    monkeypatch.setattr(sys, "argv", ["ganttuml.py", "--input", str(f)])
    with pytest.raises(SystemExit) as ei:
        ganttuml.main()
    assert "error: project.start is required" in str(ei.value)


def test_main_default_input_is_example(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ganttuml.py"])
    ganttuml.main()
    assert "wrote " in capsys.readouterr().out


def test_cli_subprocess_no_traceback(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    r = subprocess.run([sys.executable, str(GANTT_DIR / "ganttuml.py"), "--input", str(bad)],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "error:" in r.stderr and "Traceback" not in r.stderr


# --------------------------------------------------------------------------- render.sh
def stub_env(tmp_path, **scripts):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in scripts.items():
        s = bin_dir / name
        s.write_text(f"#!/bin/sh\n{body}\n")
        s.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_render_sh_happy_path_with_docker_stub(tmp_path):
    env = stub_env(tmp_path, docker=f'echo "docker $@" >> "{tmp_path}/docker.log"')
    src = with_item(task("t"))
    src["project"]["output"] = "pytest-render.puml"
    f = tmp_path / "r.json"
    f.write_text(json.dumps(src))
    r = subprocess.run(["bash", str(GANTT_DIR / "render.sh"), str(f)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "rendered output/pytest-render.png and output/pytest-render.svg" in r.stdout
    log = (tmp_path / "docker.log").read_text()
    assert "-tpng /data/pytest-render.puml" in log and "-tsvg" in log
    (GANTT_DIR / "output" / "pytest-render.puml").unlink()


def test_render_sh_fails_fast_without_wrote_line(tmp_path):
    env = stub_env(tmp_path, python3='echo "no wrote line here"',
                   docker='echo should-not-run; exit 9')
    r = subprocess.run(["bash", str(GANTT_DIR / "render.sh"), "x.json"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "no 'wrote" in r.stderr and "should-not-run" not in r.stdout


# --------------------------------------------------------------------------- golden data
EXPECTED_ADVANCED = """\
@startgantt
<style>
ganttDiagram {
  undone {
    BackGroundColor #DDDDDD
  }
  arrow {
    LineColor #B0B7C3
  }
  timeline {
    BackGroundColor #DCE9F8
  }
}
</style>
title Q3 Feature Delivery
footer Version 1.0  |  Generated 2026-07-02
Project starts 2026-06-22
hide resources footbox
hide resources names

' ---- Weekend/holiday shading + today marker (cosmetic; no scheduling effect) ----
2026-06-27 is colored in #EFEFEF
2026-06-28 is colored in #EFEFEF
2026-07-03 is colored in #EFEFEF
2026-07-04 is colored in #EFEFEF
2026-07-05 is colored in #EFEFEF
2026-07-11 is colored in #EFEFEF
2026-07-12 is colored in #EFEFEF
2026-07-02 is colored in #4F9BFF40

' ---- Per-person off: weekends + holidays + PTO (minus works_on) ----
{Alice} is off on 2026-06-25
{Alice} is off on 2026-06-27
{Alice} is off on 2026-06-28
{Alice} is off on 2026-07-03
{Alice} is off on 2026-07-04
{Alice} is off on 2026-07-05
{Alice} is off on 2026-07-11
{Alice} is off on 2026-07-12
{Bob} is off on 2026-06-27
{Bob} is off on 2026-07-03
{Bob} is off on 2026-07-04
{Bob} is off on 2026-07-05
{Bob} is off on 2026-07-11
{Bob} is off on 2026-07-12
{Carol} is off on 2026-06-27
{Carol} is off on 2026-06-28
{Carol} is off on 2026-07-03
{Carol} is off on 2026-07-04
{Carol} is off on 2026-07-05
{Carol} is off on 2026-07-06
{Carol} is off on 2026-07-07
{Carol} is off on 2026-07-11
{Carol} is off on 2026-07-12

-- Holidays --
[Independence Day (obs)] happens 2026-07-03

-- Alice --
[Design API schema] as [api_schema] on {Alice} requires 3 days
[api_schema] is colored in #8ABBED
[api_schema] is 100% completed
[api_schema] links to [[https://your-company.atlassian.net/browse/PROJ-101]]
[Design review] as [design_review] happens 2026-06-24
[Implement API] as [api_impl] on {Alice} requires 4 days
[api_impl] is colored in #8ABBED
[api_impl] is 50% completed

-- Bob --
[Scaffold UI] as [ui_scaffold] on {Bob} requires 2 days
[ui_scaffold] is colored in #8ABBED
[ui_scaffold] is 100% completed
[ui_scaffold] links to [[https://example.com/ui-spec]]
[Wire UI to API] as [ui_wire] on {Bob} requires 5 days
[ui_wire] is colored in #8ABBED
[ui_wire] is 30% completed
[UI polish] as [ui_polish] on {Bob} requires 2 days
[ui_polish] is colored in #8ABBED
[ui_polish] is 0% completed

-- Carol --
[Write test plan] as [qa_plan] on {Carol} requires 2 days
[qa_plan] starts 2026-07-01
[qa_plan] is colored in #E8473F
[qa_plan] is 60% completed
[Run regression suite] as [qa_run] on {Carol} requires 4 days
[qa_run] is colored in #E8473F
[qa_run] is 0% completed
[qa_run] links to [[https://your-company.atlassian.net/browse/PROJ-131]]

' ---- dependencies (sources declared above) ----
[api_schema] -> [api_impl]
[api_schema] -> [ui_wire]
[ui_scaffold] -> [ui_wire]
[ui_wire] -> [ui_polish]
[ui_wire] -> [qa_run]
[qa_plan] -[#E8473F]-> [qa_run]

-- Milestones --
[API frozen] as [api_done] happens at [api_impl]'s end
[api_done] -> [qa_run]
[v1.0 Release] as [release] happens at [qa_run]'s end
[release] happens at [ui_polish]'s end
[release] is colored in #E8473F

@endgantt
"""
