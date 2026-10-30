"""The LLM goal source (Plan 23 Task 14, P23-11): `planner/llm.py`'s `LLMSource` over a fake `runner` standing in for
the `claude` CLI. No test calls the real CLI; the clock is injected and a slow call waits on an event, never a sleep."""
import json
import subprocess
import threading
from types import SimpleNamespace

import pytest

from agent.base.planner import llm as L
from agent.base.planner import view as V
from agent.base.planner.goals import EXAMPLES, GoalRunner, GoalSource, LootBuilding, Rest, ScriptedSource, Shelter
from agent.base.planner.llm import DEFAULT_CLI, SYSTEM, LLMSource
from agent.base.planner.survive import Survive
from agent.base.planner.view import render, view

from .test_night import house
from .test_policies import CRATE, Rig


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Fallback:
    NAME = "scripted"

    def __init__(self):
        self.views = []

    def propose(self, v):
        self.views.append(v)
        return Rest(30.0)


def envelope(text, is_error=False):
    return json.dumps({"type": "result", "subtype": "success", "is_error": is_error, "duration_ms": 900,
                       "result": text, "session_id": "s", "total_cost_usd": 0.01})


class Runner:
    """The fake `runner(argv, input, timeout, env)`: answers `stdout`/`returncode`, after `gate` is set when given,
    advancing the clock by `cost` seconds; `raises` is raised instead."""

    def __init__(self, clock, stdout="", returncode=0, gate=None, cost=1.0, raises=None):
        self.clock, self.stdout, self.returncode = clock, stdout, returncode
        self.gate, self.cost, self.raises = gate, cost, raises
        self.calls = []

    def __call__(self, argv, input, timeout, env):
        self.calls.append({"argv": list(argv), "input": input, "timeout": timeout, "env": env})
        if self.gate is not None:
            assert self.gate.wait(5.0)
        self.clock.t += self.cost
        if self.raises is not None:
            raise self.raises
        return SimpleNamespace(returncode=self.returncode, stdout=self.stdout, stderr="")


def a_view(**k):
    v = {key: None for key in V.KEYS}
    v.update(pos={"x": 100.5, "y": 200.5, "z": 0}, hour=9.0, health=100.0,
             needs={"hunger": 0.1, "thirst": 0.1, "fatigue": 0.1}, needs_wanted=[],
             load={"weight": 4.0, "max": 8.0, "level": 0}, inventory_by_use={"food": 0, "water": 0},
             buildings=[{"id": 3, "x": 112, "y": 200, "door": [112, 201], "dist": 12.5, "containers": 4,
                         "looted": False, "doors": 1, "visited": False, "shunned": False}],
             zombies_near={"6": 0, "12": 1, "25": 2}, events=[], want_shelter=False, scanned_here=True, stock_uses=[])
    v.update(k)
    return v


def make(tmp_path=None, answer='{"type": "LootBuilding", "building": 3}', **k):
    clock = Clock()
    runner = Runner(clock, stdout=envelope(answer), **k)
    log = str(tmp_path / "goals.log") if tmp_path is not None else None
    src = LLMSource(Fallback(), log_path=log, clock=clock, runner=runner)
    return src, runner, clock


def settle(src):
    assert src.join(5.0)


# ---------------------------------------------------------------- the seam and the prompt
def test_the_source_is_a_goal_source_named_llm_with_the_specs_defaults():
    src = LLMSource(Fallback())
    assert isinstance(src, GoalSource) and LLMSource.NAME == "llm"
    assert src.cli == DEFAULT_CLI and src.model == "sonnet"
    assert src.timeout_s == 20.0 and L.LLM_TIMEOUT_S == 20.0 and src.log_path is None and src.calls == []
    assert not any(a.startswith("--dangerously") for a in src.cli) and "--bare" not in src.cli


def test_the_default_cli_strips_claude_codes_context_by_its_own_flags():
    cli = list(DEFAULT_CLI)
    assert cli[:6] == ["claude", "-p", "--output-format", "json", "--model", "sonnet"]
    after = {f: cli[cli.index(f) + 1] for f in ("--system-prompt", "--tools", "--setting-sources")}
    assert after == {"--system-prompt": SYSTEM, "--tools": "", "--setting-sources": ""}
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in cli
    assert L.model_of(cli, "--system-prompt") == SYSTEM


def test_system_names_every_goal_type_its_fields_and_the_contract():
    for t, args in EXAMPLES.items():
        assert t in SYSTEM
        for f in args:
            assert f in SYSTEM
    assert "Project Zomboid" in SYSTEM
    assert "Answer with one JSON object and nothing else" in SYSTEM
    assert "water|food" in SYSTEM and "0 to 120" in SYSTEM
    assert SYSTEM.endswith("The user message is the view: one `key: value` line per key.\n")
    assert "within 60 tiles of pos" in SYSTEM


def test_the_model_reads_system_by_the_argv_and_the_rendered_view_on_stdin(tmp_path):
    src, runner, _ = make()
    v = a_view()
    src.propose(v)
    settle(src)
    c = runner.calls[0]
    assert c["input"] == render(v) == L.prompt(v)
    assert c["argv"] == list(DEFAULT_CLI) and c["timeout"] == 20.0
    src.propose(v)
    assert src.calls[0]["prompt_bytes"] == len((SYSTEM + render(v)).encode("utf-8"))


def test_the_prompts_view_section_carries_only_the_views_keys(tmp_path):
    r = Rig(tmp_path)
    r.scan(house(1, 110))
    r.frame(x=100.0, y=201.5)
    sv = Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock)
    v = view(r.world, sv)
    section = L.prompt(v)
    assert section == render(v)
    keys = [ln.split(": ", 1)[0] for ln in section.splitlines()]
    assert keys == list(V.KEYS) and set(keys) == set(v)


def test_the_cli_runs_in_a_clean_environment_without_claudecode(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    src, runner, _ = make()
    src.propose(a_view())
    settle(src)
    env = runner.calls[0]["env"]
    assert "CLAUDECODE" not in env and env is not L.os.environ
    assert L.os.environ.get("CLAUDECODE") == "1"


# ---------------------------------------------------------------- the threading
def test_a_good_goal_is_applied_on_the_next_propose_once():
    """P23-AC: the first ask starts the call and answers None (pending), never the fallback's goal."""
    src, runner, _ = make()
    v = a_view()
    assert src.propose(v) is None and src.NAME == "llm"             # pending: nothing stands in
    assert src.fallback.views == []
    settle(src)
    g = src.propose(v)
    assert isinstance(g, LootBuilding) and g.building == 3 and src.NAME == "llm"
    row = src.calls[0]
    assert row["ok"] is True and row["error"] is None and row["model"] == "sonnet"
    assert row["goal"] == {"type": "LootBuilding", "building": 3} and row["latency_s"] == 1.0
    assert row["wall"] == 1000.0
    assert len(runner.calls) == 1                                    # applying the goal starts no call
    assert src.propose(v) is None                                    # applied once; the next ask starts a call
    settle(src)
    assert len(runner.calls) == 2 and src.fallback.views == []


def test_one_call_in_flight_at_most():
    gate = threading.Event()
    src, runner, clock = make(gate=gate)
    v = a_view()
    for _ in range(5):
        assert src.propose(v) is None                                # pending within timeout_s
        clock.t += 1.0
    gate.set()
    settle(src)
    assert len(runner.calls) == 1 and src.calls == []
    assert isinstance(src.propose(v), LootBuilding)


def test_a_call_past_timeout_s_is_abandoned_logged_timeout_and_its_late_answer_ignored():
    gate = threading.Event()
    src, runner, clock = make(gate=gate, cost=0.0)
    v = a_view()
    assert src.propose(v) is None
    clock.t += 20.0
    assert src.propose(v) is None and src.calls == []                # at timeout_s: still pending
    clock.t += 0.5
    assert isinstance(src.propose(v), Rest) and src.NAME == "scripted"   # past it: the fallback stands in
    assert src.calls[0]["error"] == "timeout" and src.calls[0]["ok"] is False and src.calls[0]["goal"] is None
    assert src.calls[0]["latency_s"] == 20.5
    assert isinstance(src.propose(v), Rest) and len(runner.calls) == 1   # no second call while it still runs
    gate.set()
    settle(src)
    assert src.propose(v) is None and len(src.calls) == 1            # the late answer never applied
    settle(src)
    assert len(runner.calls) == 2                                    # the abandoned call ended: the next starts


def test_a_call_that_returns_after_timeout_s_reads_timeout():
    src, runner, _ = make(cost=25.0)
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest)
    assert src.calls[0]["error"] == "timeout" and src.calls[0]["latency_s"] == 25.0


def test_the_subprocess_timeout_reads_timeout():
    src, _, _ = make(raises=subprocess.TimeoutExpired(["claude"], 20.0))
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "timeout"


def test_a_missing_cli_reads_spawn_and_falls_back():
    src, _, _ = make(raises=FileNotFoundError("claude"))
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest)
    assert src.calls[0]["error"].startswith("spawn: ") and src.calls[0]["ok"] is False


# ---------------------------------------------------------------- the parsing
@pytest.mark.parametrize("answer, error", [
    ("I would loot the nearest house.", "malformed"),
    ('{"type": "LootBuilding", "building": 3', "malformed"),
    ('{"type": "LootBuilding", "building": {"id": 3}', "malformed"),   # triage #16: never the nested object
    ("[1, 2]", "malformed"),
])
def test_a_malformed_answer_falls_back_and_logs_malformed(answer, error):
    src, _, _ = make(answer=answer)
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest)
    assert src.calls[0]["error"] == error and src.calls[0]["goal"] is None


def test_stdout_that_is_no_envelope_is_malformed():
    clock = Clock()
    for out in ("not json", "[]", json.dumps({"type": "result", "result": 7})):
        runner = Runner(clock, stdout=out)
        src = LLMSource(Fallback(), clock=clock, runner=runner)
        src.propose(a_view())
        settle(src)
        assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "malformed"


def test_the_first_balanced_object_in_prose_is_taken():
    src, _, _ = make(answer='Sure. {"type": "Shelter", "building": 3} and then {"type": "Rest", "seconds": 5}')
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    assert isinstance(g, Shelter) and g.building == 3


def test_a_brace_inside_a_string_does_not_end_the_object():
    src, _, _ = make(answer='```json\n{"type": "Stock", "kind": "water"}\n``` {not json}')
    src.propose(a_view())
    settle(src)
    assert src.propose(a_view()).TYPE == "Stock"


def test_a_non_zero_exit_falls_back_and_logs_its_code():
    src, _, _ = make(returncode=1)
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "exit 1"


def test_an_is_error_envelope_falls_back():
    clock = Clock()
    runner = Runner(clock, stdout=envelope("rate limited", is_error=True))
    src = LLMSource(Fallback(), clock=clock, runner=runner)
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "cli error"


def test_a_goal_outside_the_schema_is_invalid_with_its_reason():
    src, _, _ = make(answer='{"type": "Rest", "seconds": 500}')
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest)
    assert src.calls[0]["error"] == "invalid: Rest.seconds: 500 above the maximum 120"


@pytest.mark.parametrize("answer", ['{"type": "LootBuilding", "building": 99}', '{"type": "Shelter", "building": 4}'])
def test_a_building_the_view_does_not_list_is_refused(answer):
    """P24-B 3: a building the view does not list reads `invalid: refused` (was `invalid: unknown place`)."""
    src, _, _ = make(answer=answer)
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    assert isinstance(g, Rest) and src.calls[0]["error"] == "invalid: refused"


def test_the_place_is_read_against_the_current_view():
    """P23-AC: the answer is applied on a later tick, so its place is checked against the view of the ask that
    collects it: a building gone from the view is invalid, one that appeared since the call is valid."""
    src, _, _ = make()
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view(buildings=[])), Rest) and src.calls[0]["error"] == "invalid: refused"
    src2, _, _ = make()
    src2.propose(a_view(buildings=[]))
    settle(src2)
    g = src2.propose(a_view())
    assert isinstance(g, LootBuilding) and src2.calls[0]["error"] is None


@pytest.mark.parametrize("answer, ok", [
    ('{"type": "ExploreToward", "x": 160, "y": 200}', True),      # centre 160.5: 60.0 tiles from pos
    ('{"type": "ExploreToward", "x": 161, "y": 200}', False),     # 61.0
    ('{"type": "ExploreToward", "x": 142, "y": 242}', True),      # hypot(42, 42) = 59.4
    ('{"type": "ExploreToward", "x": 143, "y": 243}', False),     # hypot(43, 43) = 60.8
    ('{"type": "ExploreToward", "x": 40, "y": 200}', True),       # 60.0 the other way
])
def test_an_explore_farther_than_explore_max_tiles_from_pos_is_out_of_range(answer, ok):
    """P24-B 3: `invalid: out of range` (was `invalid: unknown place`). Named change, ruling P24-Y (Task 18): read on
    a view listing no building (with one listed, a square 40 tiles past it is `in the woods`, below)."""
    assert L.EXPLORE_MAX_TILES == 60.0
    src, _, _ = make(answer=answer)
    src.propose(a_view(buildings=[]))
    settle(src)
    g = src.propose(a_view(buildings=[]))
    if ok:
        assert g.TYPE == "ExploreToward" and src.calls[0]["error"] is None
    else:
        assert isinstance(g, Rest) and src.calls[0]["error"] == "invalid: out of range"


def test_an_explore_with_no_pos_in_the_view_is_out_of_range():
    src, _, _ = make(answer='{"type": "ExploreToward", "x": 100, "y": 200}')
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view(pos={"x": None, "y": None, "z": None})), Rest)
    assert src.calls[0]["error"] == "invalid: out of range"


# ---------------------------------------------------------------- the record
def test_each_call_is_one_sorted_json_line_in_goals_log(tmp_path):
    src, _, _ = make(tmp_path)
    v = a_view()
    for _ in range(2):
        assert src.propose(v) is None                                # starts a call: pending
        settle(src)
        assert isinstance(src.propose(v), LootBuilding)              # collects it
    lines = (tmp_path / "goals.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 == len(src.calls)
    for ln, row in zip(lines, src.calls):
        obj = json.loads(ln)
        assert list(obj) == sorted(obj)
        assert set(row) == {"wall", "latency_s", "ok", "goal", "error", "prompt_bytes", "answer_bytes", "model"}
        assert {k: obj[k] for k in row} == row
        assert obj["prompt"] == render(v) and obj["answer"] == '{"type": "LootBuilding", "building": 3}'


def test_the_model_is_read_off_the_argv():
    clock = Clock()
    runner = Runner(clock, stdout=envelope('{"type": "Rest", "seconds": 10}'))
    src = LLMSource(Fallback(), cli=("claude", "-p", "--output-format", "json", "--model", "opus"), clock=clock,
                    runner=runner)
    src.propose(a_view())
    settle(src)
    src.propose(a_view())
    assert src.calls[0]["model"] == "opus"
    assert L.model_of(("claude", "-p")) is None


def test_the_runners_history_attributes_each_goal_to_its_chooser(tmp_path):
    r = Rig(tmp_path)
    r.frame()
    clock = Clock()
    runner = Runner(clock, stdout=envelope('{"type": "Rest", "seconds": 1}'), cost=0.0)
    src = LLMSource(ScriptedSource(), clock=clock, runner=runner)
    gr = GoalRunner(src, clock=clock)
    gr.tick(r.world, r.acts, view=a_view(buildings=[]))
    assert gr.current is None and gr.line() == {"pending": "llm"}       # P23-AC: pending, no stand-in
    settle(src)
    gr.tick(r.world, r.acts, view=a_view(buildings=[]))
    assert gr.current.seconds == 1 and gr.line()["source"] == "llm"
    runner.returncode = 1                                                # the next call fails
    clock.t += 2.0
    gr.tick(r.world, r.acts, view=a_view(buildings=[]))                  # the rest ends; the next call starts
    assert gr.history[-1]["source"] == "llm" and gr.current is None
    settle(src)
    gr.tick(r.world, r.acts, view=a_view(buildings=[]))
    assert gr.current.TYPE == "Rest" and gr.current.seconds == 30.0      # the scripted source's rest stands in
    assert gr.line()["source"] == "scripted" and src.calls[-1]["error"] == "exit 1"


def test_the_default_runner_runs_the_resolved_cli_in_an_empty_directory_of_its_own(monkeypatch):
    seen = {}

    def fake_run(argv, **k):
        seen.update(k, argv=argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(L.subprocess, "run", fake_run)
    monkeypatch.setattr(L.shutil, "which", lambda name: "/bin/" + name)
    L._run(["claude", "-p"], "text", 20.0, {"A": "1"})
    assert seen["argv"] == ["/bin/claude", "-p"] and seen["input"] == "text" and seen["timeout"] == 20.0
    assert seen["env"] == {"A": "1"} and seen["capture_output"] is True and seen["encoding"] == "utf-8"
    assert L.os.path.isdir(seen["cwd"]) and L.os.listdir(seen["cwd"]) == [] and seen["cwd"] == L._cwd()


# ---------------------------------------------------------------- fix wave P (P23-AC, the goals.log guard)
def test_only_a_real_failure_is_a_fallback_row():
    """Every stand-in follows a call row that failed: a run of good calls records no failure and never asks the
    fallback."""
    src, _, _ = make()
    v = a_view()
    goals = []
    for _ in range(6):
        goals.append(src.propose(v))
        settle(src)
    assert [g is None for g in goals] == [True, False, True, False, True, False]
    assert all(isinstance(g, LootBuilding) for g in goals[1::2])
    assert [c["ok"] for c in src.calls] == [True, True, True] and src.fallback.views == []


def test_a_goals_log_write_error_is_counted_never_raised(tmp_path):
    """The deferred must-fix (T14): an OSError writing goals.log never reaches propose (the planner's tick)."""
    clock = Clock()
    runner = Runner(clock, stdout=envelope('{"type": "LootBuilding", "building": 3}'))
    src = LLMSource(Fallback(), log_path=str(tmp_path), clock=clock, runner=runner)   # a directory: open() fails
    assert src.log_errors == 0
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    assert isinstance(g, LootBuilding) and src.log_errors == 1 and len(src.calls) == 1


# ---------------------------------------------------------------- P24-B: the refusal meanings, the rules, the bytes
def test_system_carries_the_refusal_rule_the_met_ground_and_the_meanings():
    assert "within 60 tiles of pos" in SYSTEM
    assert "LootBuilding only a building listed without the L flag" in SYSTEM
    assert "met.dense" in SYSTEM and "prefer ground away from met.dense" in SYSTEM
    for why in V.WHYS:
        assert why in SYSTEM, why
    assert "@x,y" in SYSTEM and "door" in SYSTEM


@pytest.mark.parametrize("answer, buildings, why", [
    ('{"type": "LootBuilding", "building": 99}', None, "refused"),
    ('{"type": "Shelter", "building": 4}', None, "refused"),
    ('{"type": "ExploreToward", "x": 170, "y": 200}', None, "out of range"),
    ('{"type": "LootBuilding", "building": 3}',
     [{"id": 3, "x": 112, "y": 200, "door": None, "dist": 12.5, "containers": 4, "looted": True, "doors": 0,
       "visited": True, "shunned": False}], "looted already"),
])
def test_a_refused_answer_is_the_next_prompts_last_goal_with_its_meaning(answer, buildings, why):
    k = {} if buildings is None else {"buildings": buildings}
    src, runner, _ = make(answer=answer)
    src.propose(a_view(**k))
    settle(src)
    assert isinstance(src.propose(a_view(**k)), Rest)                # the stand-in
    assert src.calls[0]["error"] == "invalid: " + why and src.calls[0]["ok"] is False
    obj = json.loads(answer)
    assert src.refusal == {"type": obj.pop("type"), "args": obj, "end": "refused", "why": why}
    src.propose(a_view(**k))                                         # the next call: the refusal in its prompt
    settle(src)
    line = next(ln for ln in runner.calls[1]["input"].splitlines() if ln.startswith("last_goal:"))
    assert json.loads(line.split(": ", 1)[1]) == {"type": json.loads(answer)["type"], "args": obj, "end": "refused",
                                                  "why": why}
    assert src.refusal is None                                       # shown once


def test_a_building_beyond_the_shown_six_is_refused():
    bs = [{"id": i, "x": 110 + i, "y": 200, "door": None, "dist": float(i), "containers": 1, "looted": False,
           "doors": 0, "visited": False, "shunned": False} for i in range(1, 9)]
    src, _, _ = make(answer='{"type": "LootBuilding", "building": 7}')
    src.propose(a_view(buildings=bs))
    settle(src)
    assert isinstance(src.propose(a_view(buildings=bs)), Rest) and src.calls[0]["error"] == "invalid: refused"
    src, _, _ = make(answer='{"type": "LootBuilding", "building": 6}')
    src.propose(a_view(buildings=bs))
    settle(src)
    assert isinstance(src.propose(a_view(buildings=bs)), LootBuilding)


def test_a_good_answer_clears_a_held_refusal_and_the_runners_row_shows():
    src, runner, _ = make()
    src.refusal = {"type": "LootBuilding", "args": {"building": 9}, "end": "refused", "why": "refused"}
    src.propose(a_view())
    settle(src)
    assert '"why":"refused"' in runner.calls[0]["input"]
    assert isinstance(src.propose(a_view()), LootBuilding) and src.refusal is None


def test_each_row_records_its_answer_bytes_and_the_totals_sum_them():
    answer = '{"type": "LootBuilding", "building": 3}'
    src, _, _ = make(answer=answer)
    v = a_view()
    for _ in range(2):
        src.propose(v)
        settle(src)
        src.propose(v)
    assert [c["answer_bytes"] for c in src.calls] == [len(answer.encode("utf-8"))] * 2
    assert src.totals() == {"prompt_bytes_total": sum(c["prompt_bytes"] for c in src.calls),
                            "answer_bytes_total": 2 * len(answer.encode("utf-8"))}
    src2, _, _ = make(returncode=1)
    src2.propose(v)
    settle(src2)
    src2.propose(v)
    assert src2.calls[0]["answer_bytes"] == 0 and src2.totals()["answer_bytes_total"] == 0
    assert LLMSource(Fallback()).totals() == {"prompt_bytes_total": 0, "answer_bytes_total": 0}



# ---------------------------------------------------------------- Task 3 fix 1: a looted shelter, the prompt's reads
def test_a_shelter_of_a_shown_looted_building_is_accepted():
    looted = [{"id": 3, "x": 112, "y": 200, "door": [112, 201], "dist": 12.5, "containers": 4, "looted": True,
               "doors": 1, "visited": True, "shunned": False}]
    src, _, _ = make(answer='{"type": "Shelter", "building": 3}')
    src.propose(a_view(buildings=looted))
    settle(src)
    g = src.propose(a_view(buildings=looted))
    assert isinstance(g, Shelter) and g.building == 3 and src.calls[0]["error"] is None and src.refusal is None


def test_system_explains_attackers_hit_reaction_and_the_met_rules_threshold():
    assert "attackers is how many zombies are attacking you now" in SYSTEM
    assert "hit_reaction names the hit you are reeling from" in SYSTEM
    assert "never explore toward its bearing while met.n is 3 or more" in SYSTEM


# ---------------------------------------------------------------- Task 29: the guides' strategy lines, the wants
# Each strategy line's own fragment, pinned here apart from the schema (a line dropped from `goals.json` fails).
STRATEGY_PINS = (
    "Prefer the nearest building listed without L over farther ones",
    "Want water and a vessel first",
    "choose Shelter in a listed building",
    "Avoid a building listed with zombies beside it",
    "Keep the load light",
)


def test_system_carries_the_five_strategy_lines_once_each_in_the_guides_order():
    starts = [SYSTEM.index(p) for p in STRATEGY_PINS]
    assert starts == sorted(starts)
    for p in STRATEGY_PINS:
        assert SYSTEM.count(p) == 1, p
    for e in L.strategy():
        assert SYSTEM.count(e["text"]) == 1, e["text"]
    assert len(L.strategy()) == len(STRATEGY_PINS)
    assert SYSTEM.index("Strategy") > SYSTEM.index("- Rest:")          # its own paragraph after the goal types


def test_system_names_no_path_credential_or_planner_internal():
    """Principle 8: the model reads game state only."""
    import re
    low = SYSTEM.lower()
    for bad in (".py", ".json", ".lua", "\\", "c:", "/users", "planner", "survive", "policies", "loothouse",
                "api key", "apikey", "token", "password", "credential", "secret", "oauth", "anthropic_"):
        assert bad not in low, bad
    assert not re.search(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b", SYSTEM)         # no constant's name (TIRED_T, DANGER_R)
    assert "/" not in SYSTEM.replace("w/o", "")


def test_system_explains_the_wants_and_the_new_view_keys():
    assert "want (string, one of weapon|bag)" in SYSTEM
    assert "z:N" in SYSTEM and "tired is true" in SYSTEM and "night is true" in SYSTEM
    assert "then clothing, food, bandages and weapons" not in SYSTEM   # the old want order gave way to the strategy's


@pytest.mark.parametrize("want", ["weapon", "bag"])
def test_the_model_may_answer_a_loot_with_a_weapon_or_bag_want(want):
    src, _, _ = make(answer='{"type": "LootBuilding", "building": 3, "want": "%s"}' % want)
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    assert isinstance(g, LootBuilding) and g.want == want and g.args() == {"building": 3, "want": want}
    assert src.calls[0]["error"] is None and src.calls[0]["goal"] == {"type": "LootBuilding", "building": 3,
                                                                       "want": want}


def test_a_gun_want_is_refused_with_validates_one_line_reason():
    src, _, _ = make(answer='{"type": "LootBuilding", "building": 3, "want": "gun"}')
    src.propose(a_view())
    settle(src)
    assert isinstance(src.propose(a_view()), Rest)
    err = src.calls[0]["error"]
    assert err.startswith("invalid: LootBuilding.want: 'gun' not in") and "\n" not in err
