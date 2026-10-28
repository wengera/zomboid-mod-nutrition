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
             buildings=[{"id": 3, "dist": 12.5, "containers": 4, "looted": 1, "doors": 1, "visited": False,
                         "shunned": False}],
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
    src, runner, _ = make()
    v = a_view()
    g = src.propose(v)
    assert isinstance(g, Rest) and src.NAME == "scripted"            # the fallback stands in while pending
    settle(src)
    g = src.propose(v)
    assert isinstance(g, LootBuilding) and g.building == 3 and src.NAME == "llm"
    row = src.calls[0]
    assert row["ok"] is True and row["error"] is None and row["model"] == "sonnet"
    assert row["goal"] == {"type": "LootBuilding", "building": 3} and row["latency_s"] == 1.0
    assert row["wall"] == 1000.0
    assert len(runner.calls) == 1                                    # applying the goal starts no call
    g = src.propose(v)
    assert isinstance(g, Rest) and len(runner.calls) == 2           # applied once; the next call starts


def test_one_call_in_flight_at_most():
    gate = threading.Event()
    src, runner, clock = make(gate=gate)
    v = a_view()
    for _ in range(5):
        assert isinstance(src.propose(v), Rest)
        clock.t += 1.0
    gate.set()
    settle(src)
    assert len(runner.calls) == 1 and src.calls == []
    assert isinstance(src.propose(v), LootBuilding)


def test_a_call_past_timeout_s_is_abandoned_logged_timeout_and_its_late_answer_ignored():
    gate = threading.Event()
    src, runner, clock = make(gate=gate, cost=0.0)
    v = a_view()
    src.propose(v)
    clock.t += 20.0
    assert isinstance(src.propose(v), Rest) and src.calls == []      # at timeout_s: still pending
    clock.t += 0.5
    assert isinstance(src.propose(v), Rest)
    assert src.calls[0]["error"] == "timeout" and src.calls[0]["ok"] is False and src.calls[0]["goal"] is None
    assert src.calls[0]["latency_s"] == 20.5
    assert isinstance(src.propose(v), Rest) and len(runner.calls) == 1   # no second call while it still runs
    gate.set()
    settle(src)
    g = src.propose(v)
    assert isinstance(g, Rest) and len(src.calls) == 1               # the late answer never applied
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
def test_a_building_the_view_does_not_list_is_an_unknown_place(answer):
    src, _, _ = make(answer=answer)
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    assert isinstance(g, Rest) and src.calls[0]["error"] == "invalid: unknown place"


def test_the_place_is_read_against_the_view_the_call_was_given():
    src, _, _ = make()
    src.propose(a_view(buildings=[]))
    settle(src)
    assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "invalid: unknown place"


@pytest.mark.parametrize("answer, ok", [
    ('{"type": "ExploreToward", "x": 160, "y": 200}', True),      # centre 160.5: 60.0 tiles from pos
    ('{"type": "ExploreToward", "x": 161, "y": 200}', False),     # 61.0
    ('{"type": "ExploreToward", "x": 142, "y": 242}', True),      # hypot(42, 42) = 59.4
    ('{"type": "ExploreToward", "x": 143, "y": 243}', False),     # hypot(43, 43) = 60.8
    ('{"type": "ExploreToward", "x": 40, "y": 200}', True),       # 60.0 the other way
])
def test_an_explore_farther_than_explore_max_tiles_from_pos_is_an_unknown_place(answer, ok):
    assert L.EXPLORE_MAX_TILES == 60.0
    src, _, _ = make(answer=answer)
    src.propose(a_view())
    settle(src)
    g = src.propose(a_view())
    if ok:
        assert g.TYPE == "ExploreToward" and src.calls[0]["error"] is None
    else:
        assert isinstance(g, Rest) and src.calls[0]["error"] == "invalid: unknown place"


def test_an_explore_with_no_pos_in_the_view_is_an_unknown_place():
    src, _, _ = make(answer='{"type": "ExploreToward", "x": 100, "y": 200}')
    src.propose(a_view(pos={"x": None, "y": None, "z": None}))
    settle(src)
    assert isinstance(src.propose(a_view()), Rest) and src.calls[0]["error"] == "invalid: unknown place"


# ---------------------------------------------------------------- the record
def test_each_call_is_one_sorted_json_line_in_goals_log(tmp_path):
    src, _, _ = make(tmp_path)
    v = a_view()
    for _ in range(2):
        src.propose(v)                                               # starts a call; the fallback answers
        settle(src)
        assert isinstance(src.propose(v), LootBuilding)              # collects it
    lines = (tmp_path / "goals.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 == len(src.calls)
    for ln, row in zip(lines, src.calls):
        obj = json.loads(ln)
        assert list(obj) == sorted(obj)
        assert set(row) == {"wall", "latency_s", "ok", "goal", "error", "prompt_bytes", "model"}
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
    assert gr.current.TYPE == "Rest" and gr.current.seconds == 30.0      # the scripted source's rest
    settle(src)
    clock.t += 31.0
    gr.tick(r.world, r.acts, view=a_view(buildings=[]))
    assert gr.history[-1]["source"] == "scripted"
    assert gr.current.seconds == 1 and gr.line()["source"] == "llm"


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
