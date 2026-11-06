"""The tactician's model source (Plan 31 Task 11, variant T; the proposal § 2 and § 5): the triggered `claude -p` call,
one in flight, the rest coalesced, the answer validated late against the view of the moment it lands. It generalises
`llm.LLMSource`'s threading (one daemon worker, an injected clock and runner, the timeout's abandonment) to a call the
caller starts on a trigger rather than on every goal ask.

- The CLI (`cli(model)`): `llm.DEFAULT_CLI` (every flag read off `claude --help` at 2.1.310 there; no tools, no settings,
  no MCP, no session saved, Angus's own login, no API key read) with its `--system-prompt` the tactician's
  (`plays.SYSTEM`) and its `--model` the configuration's (`sonnet`, the default's, or `haiku`); the prompt on stdin is
  the rendered view (`tview.render`).
- `call(argv, prompt, runner, timeout_s, clock)`: one synchronous call (the bench's, and the worker's body): `{wall,
  latency_s, returncode, error, text, answer, limited}`, `answer` the first JSON object of the envelope's `result` text
  (`llm.objects`), `error` None, `exit <code>`, `timeout`, `malformed`, `cli error` or `spawn: <Type>: <reason>`,
  `limited` True when the call reads as the account's limit (a non-zero exit, or an error envelope whose text names
  `429` or a rate or usage limit: the bench stops at the first).
- `TacticianSource(cli, timeout_s, clock, runner)`: `ask(view, trigger)` starts a call when none is in flight (True),
  else marks the flight dirty and counts it coalesced (False); `poll(view_now)` returns None while the call runs within
  `timeout_s`, else the collected result `{trigger, view, answer, play, refused_why, latency_s, model, coalesced,
  error}` with the answer validated against `view_now` (`plays.validate`: a target that died since is refused
  `unknown_label`), once; a call past `timeout_s` is abandoned (`error` "timeout", its late answer ignored) and no new
  call starts until its thread ends; `dirty` tells the caller to ask again at once. The record of every collected call
  is kept in `calls`."""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time

from agent.base.planner.llm import DEFAULT_CLI, model_of, objects
from agent.base.planner.tactician import plays as P
from agent.base.planner.tactician.tview import render

TACTIC_TIMEOUT_S = 15.0   # wall seconds a call may take before it is abandoned (a first guess for the trials: the
                          # proposal's median notice-to-contact 9.6 to 21.3 s, desk reads, with sonnet's p99 7.3 s)
LIMIT_WORDS = ("429", "rate limit", "rate_limit", "usage limit")   # an output naming one is the account's limit


def cli(model="sonnet", system=None):
    """The tactician's argv (the module docstring)."""
    argv = list(DEFAULT_CLI)
    argv[argv.index("--model") + 1] = model
    argv[argv.index("--system-prompt") + 1] = P.SYSTEM if system is None else system
    return tuple(argv)


_CWD = []


def _cwd():
    if not _CWD:
        _CWD.append(tempfile.mkdtemp(prefix="tactician-"))
    return _CWD[0]


def run(argv, input, timeout, env):
    """The real runner: the CLI in an empty directory of its own (`llm._run`'s)."""
    exe = shutil.which(argv[0]) or argv[0]
    return subprocess.run([exe] + list(argv[1:]), input=input, timeout=timeout, env=env, cwd=_cwd(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _limited(text):
    """An error envelope's text names the account's limit (LIMIT_WORDS)."""
    t = (text or "").lower()
    return any(w in t for w in LIMIT_WORDS)


def parse(stdout):
    """(the answer's first object or None, the result text or None, error or None) of a CLI envelope."""
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
    found = objects(text)
    return (found[0], text, None) if found else (None, text, "malformed")


def call(argv, prompt, runner=run, timeout_s=TACTIC_TIMEOUT_S, clock=time.time):
    """One synchronous call (the module docstring)."""
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    t0 = clock()
    out = {"wall": t0, "latency_s": None, "returncode": None, "error": None, "text": None, "answer": None,
           "limited": False, "stderr": None}
    try:
        proc = runner(list(argv), prompt, timeout_s, env)
        out["returncode"] = proc.returncode
        stderr = getattr(proc, "stderr", None)
        out["stderr"] = stderr[:400] if isinstance(stderr, str) else None
        out["limited"] = proc.returncode != 0   # an exit 1 is the account's limit until read otherwise
        if proc.returncode != 0:
            out["error"] = "exit %s" % proc.returncode
        else:
            out["answer"], out["text"], out["error"] = parse(proc.stdout)
            if out["error"] == "cli error":   # only an error envelope's text is read for the limit's words (a
                out["limited"] = _limited(out["text"] or "")   # successful envelope's token counts may read 429)
    except subprocess.TimeoutExpired:
        out["error"] = "timeout"
    except Exception as e:   # the CLI missing, a runner fault: the caller's fallback answers
        out["error"] = "spawn: %s: %s" % (type(e).__name__, e)
    out["latency_s"] = clock() - t0
    return out


def judge(answer, view):
    """(Play or None, refused why or None) of a call's answer against `view`."""
    if answer is None:
        return None, "malformed"
    try:
        return P.validate(answer, view), None
    except P.Refused as e:
        return None, e.why


class TacticianSource:
    """The triggered call (the module docstring)."""
    NAME = "model"

    def __init__(self, argv=None, timeout_s=TACTIC_TIMEOUT_S, clock=time.time, runner=None):
        self.argv = tuple(argv) if argv is not None else cli()
        self.model = model_of(self.argv)
        self.timeout_s = timeout_s
        self.clock = clock
        self.runner = runner if runner is not None else run
        self.calls = []          # every collected call's result
        self.dirty = False       # a trigger fired while the call was out
        self.coalesced = 0       # triggers coalesced into the flight in progress
        self._pending = None     # {thread, view, trigger, wall, done, out, coalesced}
        self._abandoned = None   # the thread of a call abandoned past timeout_s, until it ends

    def busy(self):
        """A call is out, or an abandoned one still runs."""
        if self._abandoned is not None and not self._abandoned.is_alive():
            self._abandoned = None
        return self._pending is not None or self._abandoned is not None

    def ask(self, view, trigger):
        """Start a call on `view` (True), or coalesce `trigger` into the one out (False)."""
        if self.busy():
            self.dirty = True
            self.coalesced += 1
            return False
        p = {"view": view, "trigger": trigger, "wall": self.clock(), "done": threading.Event(), "out": None,
             "coalesced": self.coalesced}
        self.coalesced, self.dirty = 0, False
        p["thread"] = threading.Thread(target=self._work, args=(p,), name="tactician", daemon=True)
        self._pending = p
        p["thread"].start()
        return True

    def _work(self, p):
        p["out"] = call(self.argv, render(p["view"]), self.runner, self.timeout_s, self.clock)
        p["done"].set()

    def poll(self, view_now):
        """None while the call runs within timeout_s (or none is out); else its result, once (the module
        docstring)."""
        p = self._pending
        if p is None:
            return None
        if not p["done"].is_set():
            if self.clock() - p["wall"] <= self.timeout_s:
                return None
            self._abandoned, self._pending = p["thread"], None
            return self._result(p, {"answer": None, "error": "timeout", "latency_s": self.clock() - p["wall"]},
                                view_now)
        self._pending = None
        return self._result(p, p["out"], view_now)

    def _result(self, p, out, view_now):
        play, why = (None, None)
        if out.get("error") is None:
            play, why = judge(out.get("answer"), view_now)
        else:
            why = "timeout" if out["error"] == "timeout" else ("cli_error" if out["error"] == "cli error" else (
                "malformed" if out["error"] == "malformed" else "exit"))
        r = {"trigger": p["trigger"], "view": p["view"], "answer": out.get("answer"),
             "play": play.row() if play is not None else None, "refused_why": why, "latency_s": out.get("latency_s"),
             "model": self.model, "coalesced": p["coalesced"], "error": out.get("error"), "_play": play}
        self.calls.append({k: v for k, v in r.items() if k not in ("view", "_play")})
        return r

    def join(self, timeout=None):
        """Wait for the call out and any abandoned one; True when neither still runs."""
        ts = [t for t in (self._abandoned, self._pending and self._pending["thread"]) if t is not None]
        for t in ts:
            t.join(timeout)
        return not any(t.is_alive() for t in ts)
