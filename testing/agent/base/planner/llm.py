"""The LLM goal source (Plan 23 Task 14, spec § 8, P23-11): a model chooses the survivor's next goal through the
`claude` CLI, behind the goal layer's one seam (`GoalSource.propose(view) -> Goal`, `planner/goals.py`). The model is
a goal source and nothing more: the instincts above the goal branch still pre-empt whatever it chooses, and the
scripted source (`fallback`) stands in whenever the model is late, malformed or unsafe.

The contract:
- What the model sees: `prompt(view) = SYSTEM + render(view)`. `SYSTEM` is rendered once at import from
  `schema/goals.json` (the game, the contract, one line per goal type with its fields, their types, enums and bounds,
  how the view's building line reads, then "The view:"); `render(view)` (`planner/view.py`) is the view's text, game
  state only (principle 8): no path, credential, log or planner internals beyond the view's own keys.
- What it may answer: one JSON object, one of the five goals of `goals.json`. Parsing: the CLI's stdout is its JSON
  envelope (`{"type": "result", "is_error": …, "result": "<text>", …}`); the `result` text's first balanced `{...}`
  that decodes as JSON (`first_object`) is the goal, checked by `goals.validate`; a LootBuilding or Shelter naming a
  building the view the call was given does not list is refused (`invalid: unknown place`). An ExploreToward square
  is not place-checked: the view lists no squares beyond `pos` and `edge`, and exploring past them is its purpose.
- What happens on every failure: the fallback's goal is returned, and the call's row records why. `error` is None on
  success, else "timeout" (no answer within `timeout_s` on the injected clock, or `subprocess.TimeoutExpired`),
  "exit <code>" (a non-zero exit), "cli error" (an envelope with `is_error` true: a refusal, a rate limit),
  "malformed" (stdout not an envelope, or no object in its text), "invalid: <reason>" (`validate`'s one-line reason,
  or "unknown place"), "spawn: <reason>" (the CLI could not be run at all, e.g. not on PATH).

The threading: `propose(view)` never waits. With no call pending (and no abandoned call still running) it starts one
daemon worker thread running the CLI with `timeout_s`, and returns the fallback's goal on this call. A later `propose`
collects the finished worker: a valid goal is returned (once) and no new call starts on that propose; a failure is
recorded and a new call starts. A worker still running past `timeout_s` is abandoned and recorded "timeout"; its
answer is ignored when it lands, and no new call starts until its thread has ended (the subprocess's own timeout
ends it), so at most one CLI call is ever in flight. `join(timeout)` waits for the pending worker (tests, shutdown).

The record: `calls`, one row per collected call, `{wall, latency_s, ok, goal, error, prompt_bytes, model}` (`wall` the
call's start, `latency_s` to its answer or its abandonment, `goal` the validated goal as `{"type", **args}` else None,
`model` read off the argv's `--model`); each row is appended to `log_path` (the driver's `goals.log` beside
`decision.log`) as one JSON line with sorted keys, carrying also the `prompt` sent and the `answer` text (P23-11: the
prompt and every answer are logged). Rows are recorded on the planner's thread when a call is collected.

The goal's attribution: `LLMSource.NAME` is "llm"; each `propose` sets the instance's `NAME` to "llm" for the model's
goal and to the fallback's `NAME` ("scripted") for a stand-in, so `GoalRunner`'s history rows (which read the
source's NAME when a goal closes) attribute each goal to its chooser.

The CLI (Claude Code 2.1.310 on this host, `claude --version`, the shape read against it): `claude -p --output-format
json --model <model>` with the prompt on stdin (a prompt of at most ARGV_PROMPT_MAX bytes goes on the argv instead,
after the flags), printing one JSON object to stdout. It runs under Angus's own login: no API key is set or read, no
`--dangerously-*` flag is passed. The subprocess gets a copy of the environment with `CLAUDECODE` removed, so a CLI
started from inside a Claude Code session does not refuse to run nested. `runner(argv, input, timeout, env)` returns
an object with `returncode` and `stdout` (default: `subprocess.run`, the executable resolved by `shutil.which` so a
`.cmd` shim on Windows resolves, text mode UTF-8, run in an empty temporary directory of its own (`_cwd`) so the
CLI loads no repository's CLAUDE.md or git status into the model's context: the hand probe of 2026-10-28, run from
the repository, answered with the repository's state, 33486 tokens of context created for a two-byte prompt); tests
inject a fake.
"""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time

from agent.base.planner.goals import SCHEMA_PATH, validate
from agent.base.planner.view import render

LLM_TIMEOUT_S = 20.0          # P23-11: a call answering later than this is a fallback
ARGV_PROMPT_MAX = 1024        # bytes: a longer prompt goes on stdin
CLI = ("claude", "-p", "--output-format", "json", "--model", "sonnet")
PLACE_GOALS = ("LootBuilding", "Shelter")   # goals naming a building the view must list

__all__ = ["LLMSource", "SYSTEM", "prompt", "first_object", "model_of", "LLM_TIMEOUT_S", "ARGV_PROMPT_MAX", "CLI"]


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
        "from the view below. Answer with one JSON object and nothing else: {\"type\": <one of %s>, ...that type's "
        "fields}." % ", ".join(names),
        "The goal types:",
    ]
    for e in entries:
        t = e["properties"]["type"]["const"]
        fields = "; ".join(_field_text(k, v) for k, v in e["properties"].items() if k != "type")
        lines.append("- %s: %s Fields: %s" % (t, e.get("description", ""), fields))
    lines.append("In the view, each building reads `id dist containers/looted/doors flags` (dist in tiles; flags v "
                 "visited, s shunned, - neither); name a building only by an id the view lists.")
    lines.append("The view:")
    return "\n".join(lines) + "\n"


SYSTEM = _system()


def prompt(view):
    """The bytes the model reads (the module docstring)."""
    return SYSTEM + render(view)


# ---------------------------------------------------------------- the parsing
def first_object(text):
    """The first balanced `{...}` in `text` that decodes as a JSON object, else None."""
    dec = json.JSONDecoder()
    i = text.find("{")
    while i >= 0:
        try:
            obj, _ = dec.raw_decode(text, i)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            return obj
        i = text.find("{", i + 1)
    return None


def model_of(cli):
    """The argv's `--model` value, else None."""
    cli = list(cli)
    for i, a in enumerate(cli[:-1]):
        if a == "--model":
            return cli[i + 1]
    return None


def _parse(stdout, view):
    """(goal, answer text, error) from the CLI's stdout (the module docstring)."""
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
    if goal.TYPE in PLACE_GOALS:
        ids = {b.get("id") for b in (view.get("buildings") or ()) if isinstance(b, dict)}
        if goal.building not in ids:
            return None, text, "invalid: unknown place"
    return goal, text, None


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

    def __init__(self, fallback, cli=CLI, timeout_s=LLM_TIMEOUT_S, log_path=None, clock=time.time, runner=None):
        self.fallback = fallback
        self.cli = tuple(cli)
        self.timeout_s = timeout_s
        self.log_path = log_path
        self.clock = clock
        self.runner = runner if runner is not None else _run
        self.model = model_of(self.cli)
        self.calls = []            # one row per collected call (the module docstring)
        self._pending = None       # the call in flight: {thread, wall, view, prompt, done, end, goal, answer, error}
        self._abandoned = None     # the thread of a call abandoned past timeout_s, until it ends

    # -- the seam -----------------------------------------------------------------------------------------------
    def propose(self, view):
        goal = self._collect()
        if goal is not None:
            self.NAME = LLMSource.NAME
            return goal
        if self._pending is None and not self._busy():
            self._start(view)
        self.NAME = getattr(self.fallback, "NAME", None)
        return self.fallback.propose(view)

    def join(self, timeout=None):
        """Wait for the pending call's worker and any abandoned one; True when neither is still running."""
        threads = [t for t in (self._abandoned, self._pending and self._pending["thread"]) if t is not None]
        for t in threads:
            t.join(timeout)
        return not any(t.is_alive() for t in threads)

    # -- the call -----------------------------------------------------------------------------------------------
    def _busy(self):
        if self._abandoned is not None and not self._abandoned.is_alive():
            self._abandoned = None
        return self._abandoned is not None

    def _start(self, view):
        text = prompt(view)
        p = {"wall": self.clock(), "view": view, "prompt": text, "done": threading.Event(), "end": None,
             "goal": None, "answer": None, "error": None}
        p["thread"] = threading.Thread(target=self._work, args=(p,), name="llm-goal", daemon=True)
        self._pending = p
        p["thread"].start()

    def _work(self, p):
        """The worker: one CLI call, its answer parsed; never raises."""
        text = p["prompt"]
        if len(text.encode("utf-8")) <= ARGV_PROMPT_MAX:
            argv, stdin = list(self.cli) + [text], None
        else:
            argv, stdin = list(self.cli), text
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        try:
            proc = self.runner(argv, stdin, self.timeout_s, env)
            if proc.returncode != 0:
                p["error"] = "exit %s" % proc.returncode
            else:
                p["goal"], p["answer"], p["error"] = _parse(proc.stdout, p["view"])
        except subprocess.TimeoutExpired:
            p["error"] = "timeout"
        except Exception as e:             # the CLI missing, a runner fault: the fallback stands in
            p["error"] = "spawn: %s: %s" % (type(e).__name__, e)
        p["end"] = self.clock()
        p["done"].set()

    def _collect(self):
        """The pending call's goal when it answered in time (recording its row), else None."""
        p = self._pending
        if p is None:
            return None
        if not p["done"].is_set():
            now = self.clock()
            if now - p["wall"] <= self.timeout_s:
                return None
            self._abandoned, self._pending = p["thread"], None
            self._record(p, now - p["wall"], None, "timeout")
            return None
        self._pending = None
        latency = p["end"] - p["wall"]
        if latency > self.timeout_s:
            self._record(p, latency, None, "timeout")
            return None
        self._record(p, latency, p["goal"], p["error"])
        return p["goal"]

    def _record(self, p, latency, goal, error):
        row = {"wall": p["wall"], "latency_s": latency, "ok": goal is not None and error is None,
               "goal": dict({"type": goal.TYPE}, **goal.args()) if goal is not None else None, "error": error,
               "prompt_bytes": len(p["prompt"].encode("utf-8")), "model": self.model}
        self.calls.append(row)
        if self.log_path:
            line = dict(row, prompt=p["prompt"], answer=p["answer"])
            with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(line, sort_keys=True) + "\n")
