"""The LLM goal source (Plan 23 Task 14, spec § 8, P23-11, P23-V): a model chooses the survivor's next goal through
the `claude` CLI, behind the goal layer's one seam (`GoalSource.propose(view) -> Goal`, `planner/goals.py`). The model
is a goal source and nothing more: the instincts above the goal branch still pre-empt whatever it chooses, and the
scripted source (`fallback`) stands in whenever the model is late, malformed or unsafe.

The contract:
- What the model sees: the system prompt `SYSTEM`, passed by `--system-prompt` and replacing Claude Code's own, and
  the user prompt `prompt(view) = render(view)` on stdin, nothing else. `SYSTEM` is rendered once at import from
  `schema/goals.json` (the game, the contract, one line per goal type with its fields, their types, enums and bounds,
  how the view's building line reads and the places a goal may name, then that the user message is the view);
  `render(view)` (`planner/view.py`) is the view's text, game state only (principle 8): no path, credential, log or
  planner internals beyond the view's own keys.
- What it may answer: one JSON object, one of the five goals of `goals.json`. Parsing: the CLI's stdout is its JSON
  envelope (`{"type": "result", "is_error": …, "result": "<text>", …}`); the `result` text's first balanced `{...}`
  that decodes as JSON (`first_object`) is the goal, checked by `goals.validate` on the worker, then, when the answer
  is collected, against the view of the ask that collects it (the current view, ruling P23-AC: a place that vanished
  since the call is refused): the refusal rule (P24-B 3, stated in `SYSTEM`), its error `invalid: <why>` with `why`
  one of `view.WHYS`: a LootBuilding or Shelter naming a building that view's render does not show (`view.shown_ids`,
  the BUILDINGS_SHOWN nearest) is `invalid: refused`; a LootBuilding of a shown building whose `looted` reads true is
  `invalid: looted already`; an ExploreToward whose square's centre lies farther than EXPLORE_MAX_TILES (60) from its
  `pos` (or with no `pos`) is `invalid: out of range` (all three were `invalid: unknown place` before P24-B).
- The refusal's meaning reaches the model (P24-B 3, F1's write-up: the one refused answer named a square past the
  bound and the model never learned why, #4277, #4279): a goal refused by that rule is kept as `refusal`
  `{type, args, end: "refused", why}` and laid over the `last_goal` of the next call's view (once; then cleared), so
  the model reads its own last answer's end rather than the stand-in's; a valid answer clears it.
- What happens on every failure: the fallback's goal is returned, and the call's row records why. `error` is None on
  success, else "timeout" (no answer within `timeout_s` on the injected clock, or `subprocess.TimeoutExpired`),
  "exit <code>" (a non-zero exit), "malformed" (stdout not an envelope, or no object in its text), "invalid: <reason>"
  (`validate`'s one-line reason, or the refusal rule's why), and two values beyond the amendments' list: "cli error" (an
  envelope with `is_error` true and exit 0: a refusal, a rate limit) and "spawn: <Type>: <reason>" (the CLI could not
  be run at all, e.g. not on PATH, or the runner raised).

The threading (ruling P23-AC): `propose(view)` never waits, and returns None (pending: the goal runner holds and asks
again next tick with a fresh view) while the model has not answered. With no call pending it starts one daemon
worker thread running the CLI with `timeout_s` and returns None. A later `propose` returns None while the call runs
within `timeout_s`, then collects it: a valid goal (checked against this ask's view) is returned, once, and no new call
starts on that propose; a failure (an error, or an answer landing past `timeout_s`) is recorded and the fallback's
goal returned, so the scripted source stands in only on a recorded failure, and the next ask starts a new call. A
worker still running past `timeout_s` is abandoned, recorded "timeout" and the fallback answers; its answer is ignored
when it lands, and no new call starts until its thread has ended (the subprocess's own timeout ends it): meanwhile
the fallback answers, the stand-in for the timeout already recorded. So at most one CLI call is ever in flight.
`join(timeout)` waits for the pending and any abandoned worker.

The record: `calls`, one row per collected call, `{wall, latency_s, ok, goal, error, prompt_bytes, answer_bytes,
model}` (`wall` the call's start, `latency_s` to its answer or its abandonment, `goal` the validated goal as
`{"type", **args}` else None, `prompt_bytes` the bytes the model reads, the argv's system prompt and the stdin prompt
together, `answer_bytes` the bytes of the answer's `result` text, 0 with none (P24-B 4), `model` read off the argv's
`--model`); `totals()` is the record's `llm` summary's byte keys, `{prompt_bytes_total, answer_bytes_total}` over
`calls` (the session's bytes, never a price: the cost estimate stays out of the record, P24-B 4); each row is
appended to `log_path` (the driver's `goals.log` beside `decision.log`) as one JSON line with sorted keys, carrying
also the `prompt` sent on stdin and the `answer` text (P23-11: the prompt and every answer are logged; the system
prompt is the constant `SYSTEM`). Rows are recorded on the planner's thread when a call is collected. A write of
`goals.log` that raises `OSError` is counted in `log_errors` and never raised into `propose` (the planner's tick); the
row stays in `calls`.

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

from agent.base.planner.goals import SCHEMA_PATH, validate
from agent.base.planner.view import WHYS, render, shown_ids

LLM_TIMEOUT_S = 20.0          # P23-11: a call answering later than this is a fallback
EXPLORE_MAX_TILES = 60.0      # P23-V: a model's ExploreToward farther than this from the view's pos is refused
PLACE_GOALS = ("LootBuilding", "Shelter")   # goals naming a building the view must list

__all__ = ["LLMSource", "SYSTEM", "DEFAULT_CLI", "prompt", "first_object", "model_of", "place_error", "LLM_TIMEOUT_S",
           "EXPLORE_MAX_TILES", "PLACE_GOALS"]


# ---------------------------------------------------------------- the system prompt
def _field_text(name, spec):
    kind = spec.get("type", "value")
    if "enum" in spec:
        kind = "%s, one of %s" % (kind, "|".join(spec["enum"]))
    if "minimum" in spec and "maximum" in spec:
        kind = "%s, %s to %s" % (kind, spec["minimum"], spec["maximum"])
    return "%s (%s): %s" % (name, kind, spec.get("description", ""))


def _system():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        entries = json.load(f)["oneOf"]
    names = [e["properties"]["type"]["const"] for e in entries]
    lines = [
        "You play Project Zomboid: a survivor in a zombie apocalypse, driven by a program. The program's instincts "
        "answer threats, hunger, thirst, the load and the night on their own; you choose the survivor's next goal "
        "from the view. Answer with one JSON object and nothing else: {\"type\": <one of %s>, ...that type's "
        "fields}." % ", ".join(names),
        "The goal types:",
    ]
    for e in entries:
        t = e["properties"]["type"]["const"]
        fields = "; ".join(_field_text(k, v) for k, v in e["properties"].items() if k != "type")
        lines.append("- %s: %s Fields: %s" % (t, e.get("description", ""), fields))
    lines.append("Squares are x, y tiles; north is -y. pos is your position. In the view, each building reads "
                 "`id @x,y door x,y dist cN flags`: @x,y its nearest room square, door its exterior door square "
                 "(- none), dist in tiles, N its containers, flags L looted (nothing left to take), v visited, "
                 "s shunned, - none.")
    lines.append("The refusal rule: name a building only by an id the view lists; an ExploreToward square within "
                 "%g tiles of pos; a LootBuilding only a building listed without the L flag. An answer breaking "
                 "it is refused and the program chooses instead." % EXPLORE_MAX_TILES)
    lines.append("met is the ground where zombies were met in the last minutes: dense the centre of the densest "
                 "group, n how many, bearing and dist from pos. Zombies there are still about: prefer ground away "
                 "from met.dense, and never explore toward its bearing.")
    lines.append("last_goal is how the last goal ended: end done, failed, superseded or refused, and why, one of: "
                 "%s." % ", ".join(WHYS))
    lines.append("The user message is the view: one `key: value` line per key.")
    return "\n".join(lines) + "\n"


SYSTEM = _system()

# The CLI call (P23-V): the goal contract as the whole system prompt, nothing else of Claude Code's context. Read
# against `claude --help` at 2.1.310; the prompt (the rendered view) goes on stdin.
DEFAULT_CLI = (
    "claude",
    "-p",                                   # print mode: one answer, then exit (no interactive session, no trust dialog)
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
def first_object(text):
    """The first balanced `{...}` in `text` that decodes as a JSON object, else None. A `{` that does not close (a
    truncated answer) ends the search: the object nested inside it is never returned for it (whole-pass triage #16)."""
    dec = json.JSONDecoder()
    i = text.find("{")
    while i >= 0:
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            if _closes(text, i):
                i = text.find("{", i + 1)          # prose braces (`{not json}`): balanced, so look on past them
                continue
            return None
        if isinstance(obj, dict):
            return obj
        i = text.find("{", end)
    return None


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
    """(goal, answer text, error) from the CLI's stdout (the module docstring), before the place check."""
    try:
        env = json.loads(stdout)
    except (ValueError, TypeError):
        return None, None, "malformed"
    if not isinstance(env, dict):
        return None, None, "malformed"
    text = env.get("result")
    if env.get("is_error"):
        return None, text if isinstance(text, str) else None, "cli error"
    if not isinstance(text, str):
        return None, None, "malformed"
    obj = first_object(text)
    if obj is None:
        return None, text, "malformed"
    try:
        goal = validate(obj)
    except ValueError as e:
        return None, text, "invalid: %s" % e
    return goal, text, None


def place_error(goal, view):
    """`invalid: <why>` when `goal` breaks the refusal rule against `view` (the module docstring), else None."""
    if goal.TYPE == "ExploreToward":
        pos = view.get("pos") or {}
        px, py = pos.get("x"), pos.get("y")
        if not _num(px) or not _num(py) or math.hypot(goal.x + 0.5 - px, goal.y + 0.5 - py) > EXPLORE_MAX_TILES:
            return "invalid: out of range"
    if goal.TYPE in PLACE_GOALS:
        if goal.building not in shown_ids(view):
            return "invalid: refused"
        b = next(b for b in view["buildings"] if isinstance(b, dict) and b.get("id") == goal.building)
        if goal.TYPE == "LootBuilding" and b.get("looted") is True:
            return "invalid: looted already"
    return None


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
        """The record's `llm` summary's byte keys over `calls` (P24-B 4)."""
        return {"prompt_bytes_total": sum(c["prompt_bytes"] for c in self.calls),
                "answer_bytes_total": sum(c["answer_bytes"] for c in self.calls)}

    def _start(self, view):
        if self.refusal is not None:       # the model reads its own last answer's end, once (P24-B 3)
            view, self.refusal = dict(view, last_goal=self.refusal), None
        text = prompt(view)
        p = {"wall": self.clock(), "prompt": text, "done": threading.Event(), "end": None, "goal": None,
             "answer": None, "error": None}
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
                p["goal"], p["answer"], p["error"] = _parse(proc.stdout)
        except subprocess.TimeoutExpired:
            p["error"] = "timeout"
        except Exception as e:             # the CLI missing, a runner fault: the fallback stands in
            p["error"] = "spawn: %s: %s" % (type(e).__name__, e)
        p["end"] = self.clock()
        p["done"].set()

    def _collect(self, view):
        """("pending", None) while the call runs within timeout_s; else the call is recorded and ("ok", goal) when it
        answered a valid goal in time whose place `view` holds, ("failed", None) otherwise."""
        p = self._pending
        if not p["done"].is_set():
            now = self.clock()
            if now - p["wall"] <= self.timeout_s:
                return "pending", None
            self._abandoned, self._pending = p["thread"], None
            self._record(p, now - p["wall"], None, "timeout")
            return "failed", None
        self._pending = None
        latency = p["end"] - p["wall"]
        if latency > self.timeout_s:
            self._record(p, latency, None, "timeout")
            return "failed", None
        goal, error = p["goal"], p["error"]
        if goal is not None and error is None:
            error = place_error(goal, view)
            if error is not None:
                self.refusal = {"type": goal.TYPE, "args": goal.args(), "end": "refused",
                                "why": error[len("invalid: "):]}
                goal = None
            else:
                self.refusal = None
        self._record(p, latency, goal, error)
        return ("ok", goal) if goal is not None else ("failed", None)

    def _record(self, p, latency, goal, error):
        row = {"wall": p["wall"], "latency_s": latency, "ok": goal is not None and error is None,
               "goal": dict({"type": goal.TYPE}, **goal.args()) if goal is not None else None, "error": error,
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
