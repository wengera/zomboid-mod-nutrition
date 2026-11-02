"""The LLM goal source (Plan 23 Task 14, spec § 8, P23-11, P23-V): a model chooses the survivor's next goal through
the `claude` CLI, behind the goal layer's one seam (`GoalSource.propose(view) -> Goal`, `planner/goals.py`). The model
is a goal source and nothing more: the instincts above the goal branch still pre-empt whatever it chooses, and the
scripted source (`fallback`) stands in whenever the model is late, malformed or unsafe.

The contract:
- What the model sees: the system prompt `SYSTEM`, passed by `--system-prompt` and replacing Claude Code's own, and
  the user prompt `prompt(view) = render(view)` on stdin, nothing else. `SYSTEM` is rendered once at import from
  `schema/goals.json` by `planner/goal_prompt.py` (the game, the contract, one line per goal type with its fields,
  their types, enums and bounds, the strategy paragraph of the written guides' rules (Plan 24 Task 29), how the view's
  building line reads and the places a goal may name, then that the user message is the view);
  `render(view)` (`planner/view.py`) is the view's text, game state only (principle 8): no path, credential, log or
  planner internals beyond the view's own keys.
- What it may answer: one JSON object, one of the five goals of `goals.json`. Parsing: the CLI's stdout is its JSON
  envelope (`{"type": "result", "is_error": …, "result": "<text>", …}`); every balanced `{...}` of the `result`
  text that decodes as a JSON object (`objects`, in order: ruling P26-F, F7's call 8 answered two) is checked by
  `goals.validate` on the worker (`_parse -> (goals, text, errors, error)`: the objects that pass, in order, the
  `invalid: <reason>` of each that fails, and the error, None while one passed, else the first reason), then, when
  the answer is collected, each goal in order against the view of the ask that collects it (the current view, ruling
  P23-AC: a place that vanished since the call is refused), the first that passes being the answer and those passed
  over logged `skipped`: the refusal rule (P24-B 3, stated in `SYSTEM`), its error `invalid: <why>` with `why`
  one of `view.WHYS`: a LootBuilding or Shelter naming a building that view's render does not show (`view.shown_ids`,
  the BUILDINGS_SHOWN nearest) is `invalid: refused`; a LootBuilding of a shown building whose `looted` reads true is
  `invalid: looted already`; an ExploreToward whose square's centre lies farther than EXPLORE_MAX_TILES (60) from the
  `pos` of the view the model answered (the calling view's, kept with the call: Plan 25 Task 4, spec 2.2(c), F3's
  four refusals of a character that fled during the call; or with no `pos`) is `invalid: out of range` (all three
  were `invalid: unknown place` before P24-B); and
  (ruling P24-Y, Plan 24 Task 18: every walk has a building as its destination) an ExploreToward whose square's
  centre lies farther than the view's `woods_r` (`goals.WOODS_R`, 40, widened after REST_N rests in a row: Task 18
  fix 1, ruling 3) from every building the view lists (its `box`, else its listed squares), while it lists one, is
  `invalid: in the woods`; except (ruling P25-R, Plan 25 Task 10) an ExploreToward whose square's centre lies within
  WOODS_R of the view's `toward` building's listed square or door, accepted whatever its distance from `pos`
  (`_at_toward`: the walk the goal layer takes toward it in legs), or (ruling P26-5, Plan 26 Task 3) whose square is
  the view's `edge` square (`_at_edge`: the known buildings' unexplored edge, always accepted); a LootBuilding or
  Shelter of a building the view reads `blocked` (every exterior door marked stuck, ruling P24-Z) is `invalid:
  refused`; a Shelter of a shown building whose `shunned` reads true (its shelter failed within `night.SHUN_MIN`,
  ruling P25-G, Plan 25 Task 7: F4 answered Shelter for its one shunned building 67 times) is `invalid: shunned` (a
  LootBuilding of it stays valid: its window route exists).
- The refusal's meaning reaches the model (P24-B 3, F1's write-up: the one refused answer named a square past the
  bound and the model never learned why, #4277, #4279): a goal refused by that rule is kept as `refusal`
  `{type, args, end: "refused", why}` and laid over the `last_goal` of the next call's view (once; then cleared), so
  the model reads its own last answer's end rather than the stand-in's; a valid answer clears it. A valid answer the
  goal runner refuses as cooled reaches the next view the same way, `end` "cooled" (`GoalRunner._carried`, Plan 25
  Task 4, spec 2.2(b)).
- What happens on a failure: a cycle's first call whose every goal the refusal rule refused is re-asked once (ruling
  P26-H, below); every other failure, and a refused re-ask, takes the fallback's goal, and the call's row records why.
  `error` is None on success, else "timeout" (no answer within `timeout_s` on the injected clock, or
  `subprocess.TimeoutExpired`),
  "exit <code>" (a non-zero exit), "malformed" (stdout not an envelope, or no object in its text), "invalid: <reason>"
  (`validate`'s one-line reason, or the refusal rule's why), and two values beyond the amendments' list: "cli error" (an
  envelope with `is_error` true and exit 0: a refusal, a rate limit) and "spawn: <Type>: <reason>" (the CLI could not
  be run at all, e.g. not on PATH, or the runner raised).

The threading (ruling P23-AC): `propose(view)` never waits, and returns None (pending: the goal runner holds and asks
again next tick with a fresh view) while the model has not answered. With no call pending it starts one daemon worker
thread running the CLI with `timeout_s` and returns None. A later `propose` returns None while the call runs within
`timeout_s`, then collects it: a valid goal (checked against this ask's view) is returned, once, and no new call starts
on that propose; a failure (an error, or an answer landing past `timeout_s`) is recorded and the fallback's goal
returned, so the scripted source stands in only on a recorded failure, and the next ask starts a new call. A worker
still running past `timeout_s` is abandoned, recorded "timeout" and the fallback answers; its answer is ignored when it
lands, and no new call starts until its thread has ended (the subprocess's own timeout ends it): meanwhile the fallback
answers, the stand-in for the timeout already recorded. So at most one CLI call is ever in flight. The re-ask (ruling
P26-H, Plan 26 Task 3: F7's model answered building 2's loot 21 times, each refused `looted already`): a cycle's first
call whose every goal the refusal rule refused is recorded and one more call starts on that propose, in the same cycle,
its view the collecting one with the refusal laid over `last_goal` and its why as `reask_why` (`view.REASK_KEY`,
rendered as the prompt's last line, `Your last answer was refused: <why>. Answer a different goal.`), so `propose`
returns None and nothing stands in; `reask` reads True while it runs. Its answer is taken or refused for good: a
refusal, a failure or a timeout is the stand-in, and the next ask starts the next cycle. An answer with no valid goal
(`malformed`, `invalid: <reason>`) or a failed call is never re-asked. The goal runner's cooldown and the refusal's
carry are unchanged; the cost is one more call per refused cycle. `join(timeout)` waits for the pending and any
abandoned worker.

The record: `calls`, one row per collected call, `{wall, latency_s, ok, goal, error, skipped, cycle, reask,
prompt_bytes, answer_bytes, model}` (`wall` the call's start, `latency_s` to its answer or its abandonment, `goal` the
validated goal as `{"type", **args}` else None, `skipped` every object of the answer not taken, in the answer's order
(ruling P26-F), `[{goal, why}]`: each goal refused before the one taken (every one when none is taken: the row's
`error` and the carried refusal are then the first's), then each object `validate` failed wherever it stood (`goal`
None), `why` the error past its `invalid: `; a valid goal after the taken one is not listed, so `grade_f7` counts an
answer's objects through `objects(answer)`, never from `skipped`; `cycle`
the call's cycle (an int counted per first call, equal on a call and its re-ask) and `reask` whether it was the re-ask
(ruling P26-H); `prompt_bytes` the bytes the model reads, the argv's system prompt and the stdin prompt together,
`answer_bytes` the bytes of the answer's `result` text, 0 with none (P24-B 4), `model` read off the argv's `--model`);
`totals()` is the record's `llm` summary's byte keys, `{prompt_bytes_total, answer_bytes_total}` over `calls` (the
session's bytes, never a price: the cost estimate stays out of the record, P24-B 4), and `reasks_total`, the re-asks
among them (P26-H); each row is appended to `log_path` (the driver's `goals.log` beside `decision.log`) as one JSON line
with sorted keys, carrying also the `prompt` sent on stdin and the `answer` text (P23-11: the prompt and every answer
are logged; the system prompt is the constant `SYSTEM`). Rows are recorded on the planner's thread when a call is
collected. A write of `goals.log` that raises `OSError` is counted in `log_errors` and never raised into `propose` (the
planner's tick); the row stays in `calls`.

The per-call attribution: the class attribute `LLMSource.NAME` is "llm"; each `propose` sets the instance's `NAME` to
"llm" for the model's goal and while pending, and to the fallback's `NAME` ("scripted") for a stand-in, so
`GoalRunner`'s history rows and its `line()` (which read the source's NAME, and a goal is proposed only when none
runs) attribute each goal to its chooser.

The CLI (Claude Code 2.1.310 on this host, `claude --version`; every flag of `DEFAULT_CLI` read off `claude --help`
at that version, P23-V): `-p` with the view on stdin, `--output-format json`, `--model sonnet`, `--system-prompt
SYSTEM`, `--tools ""` (no tools: one turn by construction; `--max-turns` is not a flag at 2.1.310), `--setting-sources
""`, `--strict-mcp-config`, `--disable-slash-commands`, `--no-session-persistence`. `--bare` is not used: under it
auth is an API key only (OAuth and the keychain are never read), and no key is set or read here. No `--dangerously-*`
flag is passed. It runs under Angus's own login. The subprocess gets a copy of the environment with `CLAUDECODE`
removed, so a CLI started from inside a Claude Code session does not refuse to run nested. `runner(argv, input,
timeout, env)` returns an object with `returncode` and `stdout` (default `_run`: `subprocess.run`, the executable
resolved by `shutil.which`, text mode UTF-8, in an empty temporary directory of its own, `_cwd`); tests inject a fake.
The probes (2026-10-28, `.superpowers/sdd/2026-10-28-plan-23-survivor/t14-cli-probe*.txt`): the bare `claude -p
--output-format json --model sonnet` from the repository answered "hi" with the repository's state, 33486 tokens of
context created, $0.137 and 7360 ms; `DEFAULT_CLI` on a one-building view answered `{"type":"LootBuilding",
"building":3}` with 1320 tokens of context, $0.005464, `duration_ms` 1208 (2.67 s wall with the process start).
"""
import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
import time

from agent.base.planner.goal_prompt import system
from agent.base.planner.goal_runner import validate
from agent.base.planner.goals import WOODS_R
from agent.base.planner.view import REASK_KEY, render, shown_ids

LLM_TIMEOUT_S = 20.0          # P23-11: a call answering later than this is a fallback
EXPLORE_MAX_TILES = 60.0      # P23-V: a model's ExploreToward farther than this from the view's pos is refused
PLACE_GOALS = ("LootBuilding", "Shelter")   # goals naming a building the view must list
INVALID = "invalid: "         # the prefix of a validation or refusal error, before its why

__all__ = ["LLMSource", "SYSTEM", "DEFAULT_CLI", "prompt", "objects", "first_object", "model_of", "place_error",
           "LLM_TIMEOUT_S", "EXPLORE_MAX_TILES", "PLACE_GOALS"]


# ---------------------------------------------------------------- the system prompt
SYSTEM = system(EXPLORE_MAX_TILES)   # `planner/goal_prompt.py` (Task 29: lifted out of this module)

# The CLI call (P23-V): the goal contract as the whole system prompt, nothing else of Claude Code's context. Read
# against `claude --help` at 2.1.310; the prompt (the rendered view) goes on stdin.
DEFAULT_CLI = (
    "claude",
    "-p",                                   # print mode: one answer, then exit (no interactive session or trust dialog)
    "--output-format", "json",              # one JSON envelope on stdout (its `result` is the text)
    "--model", "sonnet",                    # P23-11's model
    "--system-prompt", SYSTEM,              # replaces Claude Code's default system prompt (its tools' prose, env, git)
    "--tools", "",                          # no built-in tools: the model can only answer, so one turn by construction
    "--setting-sources", "",                # no user, project or local settings: no hooks, no CLAUDE.md, no memory
    "--strict-mcp-config",                  # no MCP servers (none passed by --mcp-config)
    "--disable-slash-commands",             # no skills or commands
    "--no-session-persistence",             # no session saved to disk
)


def prompt(view):
    """The user prompt, on stdin: the rendered view alone (`SYSTEM` goes by `--system-prompt`)."""
    return render(view)


# ---------------------------------------------------------------- the parsing
def objects(text):
    """Every balanced `{...}` in `text` that decodes as a JSON object, in order (ruling P26-F: F7's call 8 answered two,
    and the second was the one to take). A `{` that does not close (a truncated answer) ends the search: the object
    nested inside it is never returned for it (whole-pass triage #16), and the objects before it stand."""
    dec = json.JSONDecoder()
    found = []
    i = text.find("{")
    while i >= 0:
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            if _closes(text, i):
                i = text.find("{", i + 1)          # prose braces (`{not json}`): balanced, so look on past them
                continue
            break
        if isinstance(obj, dict):
            found.append(obj)
        i = text.find("{", end)
    return found


def first_object(text):
    """The first of `objects(text)`, else None."""
    found = objects(text)
    return found[0] if found else None


def _closes(text, i):
    """Whether the `{` at `i` has a matching `}` (strings honoured) later in `text`."""
    depth, quoted, esc = 0, False, False
    for ch in text[i:]:
        if quoted:
            esc, quoted = (not esc and ch == "\\"), not (ch == '"' and not esc)
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return True
    return False


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def model_of(cli, flag="--model"):
    """The argv's `--model` value (or `flag`'s), else None."""
    cli = list(cli)
    for i, a in enumerate(cli[:-1]):
        if a == flag:
            return cli[i + 1]
    return None


def _parse(stdout):
    """(goals, answer text, errors, error) from the CLI's stdout (the module docstring), before the place check:
    `goals` every object of the text `validate` passes, in order; `errors` the `invalid: <reason>` of each object it
    fails; `error` None while a goal passed, else the first object's `invalid: <reason>`, `malformed` or `cli error`."""
    try:
        env = json.loads(stdout)
    except (ValueError, TypeError):
        return [], None, [], "malformed"
    if not isinstance(env, dict):
        return [], None, [], "malformed"
    text = env.get("result")
    if env.get("is_error"):
        return [], text if isinstance(text, str) else None, [], "cli error"
    if not isinstance(text, str):
        return [], None, [], "malformed"
    found = objects(text)
    if not found:
        return [], text, [], "malformed"
    goals, errors = [], []
    for obj in found:
        try:
            goals.append(validate(obj))
        except ValueError as e:
            errors.append("invalid: %s" % e)
    return goals, text, errors, (None if goals else errors[0])


def _goal_row(goal):
    """A goal as the record writes it: `{"type", **args}`, else None."""
    return dict({"type": goal.TYPE}, **goal.args()) if goal is not None else None


def _why(error):
    """An `invalid: <why>` error's why."""
    return error[len(INVALID):] if error.startswith(INVALID) else error


def place_error(goal, view, origin=None):
    """`invalid: <why>` when `goal` breaks the refusal rule against `view` (the module docstring), else None; the
    range is measured from `origin` (the calling view's `pos`, Plan 25 Task 4) when given, else from `view`'s."""
    if goal.TYPE == "ExploreToward":
        if _at_toward(goal, view) or _at_edge(goal, view):
            return None   # P25-R: the walk toward the view's `toward` building, which the goal layer takes in legs;
            # P26-5: the square of the view's `edge`, the unexplored edge the scripted source walks to
        pos = (origin if origin is not None else view.get("pos")) or {}
        px, py = pos.get("x"), pos.get("y")
        if not _num(px) or not _num(py) or math.hypot(goal.x + 0.5 - px, goal.y + 0.5 - py) > EXPLORE_MAX_TILES:
            return "invalid: out of range"
        listed = [b for b in view.get("buildings") or () if isinstance(b, dict)]
        r = view.get("woods_r") if _num(view.get("woods_r")) else WOODS_R
        if listed and not any(_near(b, goal.x + 0.5, goal.y + 0.5, r) for b in listed):
            return "invalid: in the woods"
    if goal.TYPE in PLACE_GOALS:
        if goal.building not in shown_ids(view):
            return "invalid: refused"
        b = next(b for b in view["buildings"] if isinstance(b, dict) and b.get("id") == goal.building)
        if b.get("blocked") is True:
            return "invalid: refused"
        if goal.TYPE == "LootBuilding" and b.get("looted") is True:
            return "invalid: looted already"
        if goal.TYPE == "Shelter" and b.get("shunned") is True:   # P25-G: its shelter failed within SHUN_MIN
            return "invalid: shunned"
    return None


def _at_toward(goal, view):
    """Ruling P25-R (F5: 9 of 25 explore answers pointed back toward building 2 from 128.85070726484017 to
    222.78699804374799 tiles and were refused): the ExploreToward's square centre lies within WOODS_R of the view's
    `toward` building's listed square or door (`view._toward`'s `square` and `door`), whatever its distance from
    `pos`: the walk toward it the goal layer takes in legs anyway."""
    t = view.get("toward")
    if not isinstance(t, dict):
        return False
    x, y = goal.x + 0.5, goal.y + 0.5
    pts = [p for p in (t.get("square"), t.get("door")) if isinstance(p, (list, tuple)) and len(p) >= 2]
    return any(_num(p[0]) and _num(p[1]) and math.hypot(p[0] + 0.5 - x, p[1] + 0.5 - y) <= WOODS_R for p in pts)


def _at_edge(goal, view):
    """Ruling P26-5 (F7: the all-looted views read `toward` null on 29 of 33, and the answers taken there were the
    view's `edge`): the ExploreToward's square is the view's `edge` `[x, y]`, accepted as `toward`'s is."""
    e = view.get("edge")
    return isinstance(e, (list, tuple)) and len(e) >= 2 and e[0] == goal.x and e[1] == goal.y


def _near(b, x, y, r=WOODS_R):
    """The point (x, y) lies within `r` (the view's `woods_r`, else WOODS_R: Task 18 fix 1, ruling 3) of the listed
    building `b`: its `box` (P24-Y) when the view carries one, else its listed room square or door."""
    box = b.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4 and all(_num(v) for v in box):
        dx = max(box[0] - x, 0.0, x - (box[2] + 1))
        dy = max(box[1] - y, 0.0, y - (box[3] + 1))
        return math.hypot(dx, dy) <= r
    pts = [(b.get("x"), b.get("y"))] + ([tuple(b["door"][:2])] if b.get("door") else [])
    return any(_num(p[0]) and _num(p[1]) and math.hypot(p[0] + 0.5 - x, p[1] + 0.5 - y) <= r for p in pts)


_CWD = []


def _cwd():
    """An empty directory of its own, made once per process: the CLI's working directory."""
    if not _CWD:
        _CWD.append(tempfile.mkdtemp(prefix="llm-goal-"))
    return _CWD[0]


def _run(argv, input, timeout, env):
    exe = shutil.which(argv[0]) or argv[0]
    return subprocess.run([exe] + list(argv[1:]), input=input, timeout=timeout, env=env, cwd=_cwd(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- the source
class LLMSource:
    """The model's goal source (the module docstring)."""
    NAME = "llm"

    def __init__(self, fallback, cli=DEFAULT_CLI, timeout_s=LLM_TIMEOUT_S, log_path=None, clock=time.time, runner=None):
        self.fallback = fallback
        self.cli = tuple(cli)
        self.timeout_s = timeout_s
        self.log_path = log_path
        self.clock = clock
        self.runner = runner if runner is not None else _run
        self.model = model_of(self.cli)
        self.calls = []            # one row per collected call (the module docstring)
        self.log_errors = 0        # goals.log writes that raised OSError (never raised into propose)
        self._pending = None       # the call in flight: {thread, wall, prompt, done, end, goal, answer, error}
        self._abandoned = None     # the thread of a call abandoned past timeout_s, until it ends
        self.refusal = None        # the model's last answer refused by the rule, for the next prompt's last_goal
        self.reask = False         # P26-H: True while the second call of a cycle (the re-ask) runs
        self._cycle = 0            # P26-H: the cycle of the latest call, counted per first call

    # -- the seam -----------------------------------------------------------------------------------------------
    def propose(self, view):
        """The model's goal, None while its call is pending, or the fallback's on a recorded failure (P23-AC)."""
        if self._pending is None:
            if self._busy():               # a timed-out call still running: its recorded timeout stands in
                return self._stand_in(view)
            self._start(view)
            self.NAME = LLMSource.NAME
            return None
        state, goal = self._collect(view)
        if state == "pending":
            self.NAME = LLMSource.NAME
            return None
        if state == "ok":
            self.NAME = LLMSource.NAME
            return goal
        return self._stand_in(view)

    def _stand_in(self, view):
        self.NAME = getattr(self.fallback, "NAME", None)
        return self.fallback.propose(view)

    def join(self, timeout=None):
        """Wait for the pending call's worker and any abandoned one; True when neither is still running."""
        threads = [t for t in (self._abandoned, self._pending and self._pending["thread"]) if t is not None]
        for t in threads:
            t.join(timeout)
        return not any(t.is_alive() for t in threads)

    def _system(self):
        """The argv's `--system-prompt` text, else ''."""
        return model_of(self.cli, "--system-prompt") or ""

    # -- the call -----------------------------------------------------------------------------------------------
    def _busy(self):
        if self._abandoned is not None and not self._abandoned.is_alive():
            self._abandoned = None
        return self._abandoned is not None

    def totals(self):
        """The record's `llm` summary's byte keys over `calls` (P24-B 4) and its re-asks (P26-H)."""
        return {"prompt_bytes_total": sum(c["prompt_bytes"] for c in self.calls),
                "answer_bytes_total": sum(c["answer_bytes"] for c in self.calls),
                "reasks_total": sum(1 for c in self.calls if c["reask"])}

    def _start(self, view, reask_why=None):
        """One call on `view`: a cycle's first, or (`reask_why`, ruling P26-H) its re-ask, whose view carries the
        refusal's why for the prompt's tail line."""
        if self.refusal is not None:       # the model reads its own last answer's end, once (P24-B 3)
            view, self.refusal = dict(view, last_goal=self.refusal), None
        self.reask = reask_why is not None
        if self.reask:
            view = dict(view, **{REASK_KEY: reask_why})
        else:
            self._cycle += 1
        text = prompt(view)
        p = {"wall": self.clock(), "prompt": text, "done": threading.Event(), "end": None, "goals": [], "errors": [],
             "answer": None, "error": None, "pos": dict(view.get("pos") or {}),   # the range's origin (Task 4)
             "cycle": self._cycle, "reask": self.reask}
        p["thread"] = threading.Thread(target=self._work, args=(p,), name="llm-goal", daemon=True)
        self._pending = p
        p["thread"].start()

    def _work(self, p):
        """The worker: one CLI call, its answer parsed; never raises."""
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        try:
            proc = self.runner(list(self.cli), p["prompt"], self.timeout_s, env)
            if proc.returncode != 0:
                p["error"] = "exit %s" % proc.returncode
            else:
                p["goals"], p["answer"], p["errors"], p["error"] = _parse(proc.stdout)
        except subprocess.TimeoutExpired:
            p["error"] = "timeout"
        except Exception as e:             # the CLI missing, a runner fault: the fallback stands in
            p["error"] = "spawn: %s: %s" % (type(e).__name__, e)
        p["end"] = self.clock()
        p["done"].set()

    def _collect(self, view):
        """("pending", None) while the call runs within timeout_s; else the call is recorded and ("ok", goal) when it
        answered in time a valid goal whose place `view` holds (the first such, ruling P26-F); ("pending", None) when
        a cycle's first call had every goal refused and its re-ask starts (ruling P26-H); ("failed", None) otherwise."""
        p = self._pending
        if not p["done"].is_set():
            now = self.clock()
            if now - p["wall"] <= self.timeout_s:
                return "pending", None
            self._abandoned, self._pending, self.reask = p["thread"], None, False
            self._record(p, now - p["wall"], None, "timeout")
            return "failed", None
        self._pending, self.reask = None, False
        latency = p["end"] - p["wall"]
        if latency > self.timeout_s:
            self._record(p, latency, None, "timeout")
            return "failed", None
        goal, refused = self._first_placed(p["goals"], view, p["pos"])
        skipped = ([{"goal": _goal_row(g), "why": _why(e)} for g, e in refused]
                   + [{"goal": None, "why": _why(e)} for e in p["errors"]])
        if goal is not None:
            error, self.refusal = None, None
        elif refused:
            g, error = refused[0]
            self.refusal = {"type": g.TYPE, "args": g.args(), "end": "refused", "why": _why(error)}
        else:
            error = p["error"]
        self._record(p, latency, goal, error, skipped)
        if goal is None and refused and not p["reask"]:   # P26-H: every goal refused, asked once more this cycle
            self._start(view, reask_why=self.refusal["why"])
            return "pending", None
        return ("ok", goal) if goal is not None else ("failed", None)

    @staticmethod
    def _first_placed(goals, view, origin):
        """(the first of `goals` whose place `view` holds, else None; [(goal, error)] of those refused before it, or
        of every one when none holds), each checked in order by `place_error` (ruling P26-F)."""
        refused = []
        for g in goals:
            error = place_error(g, view, origin)
            if error is None:
                return g, refused
            refused.append((g, error))
        return None, refused

    def _record(self, p, latency, goal, error, skipped=()):
        row = {"wall": p["wall"], "latency_s": latency, "ok": goal is not None and error is None,
               "goal": _goal_row(goal), "error": error, "skipped": list(skipped), "cycle": p["cycle"],
               "reask": p["reask"],
               "prompt_bytes": len((self._system() + p["prompt"]).encode("utf-8")),
               "answer_bytes": len(p["answer"].encode("utf-8")) if isinstance(p["answer"], str) else 0,
               "model": self.model}
        self.calls.append(row)
        if self.log_path:
            line = dict(row, prompt=p["prompt"], answer=p["answer"])
            try:
                with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(line, sort_keys=True) + "\n")
            except OSError:
                self.log_errors += 1
