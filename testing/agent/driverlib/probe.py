"""The `claude -p` live probe every LLM driver carries, lifted into the library (Plan 31 Task 4).

`claude_available`, `probe_argv` and `claude_answers` are copied, bodies and docstrings unchanged, from the frozen
driver `testing/agent/drivers/f_goals_16.py` lines 92 to 163 (its pre-boot section); that driver is never edited
(CLAUDE.md section 5, Freezing) and its own copy keeps running its own tests. The ruling they serve (CLAUDE.md
section 5, Writing a driver): a driver whose session calls the `claude` CLI makes one real `-p` call in its pre-boot
checks, `CLAUDECODE` stripped from the probe's environment, the exit code and a stderr snippet on failure, since a
rate-limited account answers every call with exit 1 (F6) and `claude --version` does not touch the limit.

The constants the three functions read are the driver's, copied with them: `LLM_TIMEOUT_S` (a probe answering later
than the goal source's own limit refuses the boot), `CLAUDE_VERSION_TIMEOUT_S`, `PROBE_SYSTEM`, `ERR_SNIPPET` and
`PROBE_INPUT`. `L` is the goal source's module (`planner/llm.py`: `DEFAULT_CLI`, `_cwd`), so the probe runs the
LLMSource's own argv in the directory its worker gives the CLI. A caller's pre-boot stores `claude_available`'s dict
and `claude_answers`'s (only when the CLI answers `--version`) and refuses the boot on an ok False. Nothing here
calls the CLI unless a caller does: tests inject `run` and `which`.
"""
import json
import os
import shutil
import subprocess
import time

from agent.base.planner import llm as L

LLM_TIMEOUT_S = 20.0                 # P23-11: a call answering later than this is a fallback
CLAUDE_VERSION_TIMEOUT_S = 30
PROBE_SYSTEM = "Reply with the single word ok."     # the probe's whole system prompt
ERR_SNIPPET = 200                                   # characters of stderr and of stdout a refusal records
PROBE_INPUT = "ping"                                # a non-empty stdin: `-p` refuses an empty prompt


def claude_available(which=shutil.which, run=subprocess.run):
    """{found, path, version, error, ok}: the `claude` CLI on PATH and `claude --version` answering (exit 0, a
    non-empty stdout), read once; the executable resolved as the LLMSource's own runner resolves it."""
    path = which("claude")
    r = {"found": path is not None, "path": path, "version": None, "error": None, "ok": False}
    if path is None:
        r["error"] = "claude not on PATH"
        return r
    try:
        proc = run([path, "--version"], capture_output=True, text=True, timeout=CLAUDE_VERSION_TIMEOUT_S)
    except Exception as e:                               # noqa: BLE001 - a CLI that cannot answer refuses the boot
        r["error"] = "%s: %s" % (type(e).__name__, e)
        return r
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        r["error"] = "exit %s" % proc.returncode
    elif not out:
        r["error"] = "no version on stdout"
    else:
        r["version"], r["ok"] = out, True
    return r


def probe_argv(cli=L.DEFAULT_CLI):
    """`cli` (the LLMSource's own argv) with only the value after `--system-prompt` swapped for PROBE_SYSTEM."""
    argv = list(cli)
    argv[argv.index("--system-prompt") + 1] = PROBE_SYSTEM
    return argv


def claude_answers(cli=L.DEFAULT_CLI, run=subprocess.run, which=shutil.which):
    """{ok, exit, answer, latency_s, error}: one live `-p` call through the goal source's own argv (probe_argv) with
    PROBE_INPUT on stdin, within LLM_TIMEOUT_S, read once; ok only on exit 0 with a non-empty `result` text in the JSON
    envelope (an `is_error` envelope is not ok). The executable resolves through `which` as the LLMSource's runner
    resolves it, and the call runs in the environment the goal source's worker gives the CLI (`CLAUDECODE` removed: a
    CLI started from inside a Claude Code session refuses to run nested). A non-zero exit names its cause: the first
    ERR_SNIPPET characters of stderr and of stdout beside `exit N`."""
    r = {"ok": False, "exit": None, "answer": None, "latency_s": None, "error": None}
    argv = probe_argv(cli)
    exe = which(argv[0]) or argv[0]
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)                          # as llm.py's worker does
    t0 = time.monotonic()
    try:
        proc = run([exe] + argv[1:], input=PROBE_INPUT, timeout=LLM_TIMEOUT_S, cwd=L._cwd(), env=env,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception as e:                               # noqa: BLE001 - a CLI that cannot answer refuses the boot
        r["latency_s"] = round(time.monotonic() - t0, 3)
        r["error"] = "%s: %s" % (type(e).__name__, e)
        return r
    r["latency_s"] = round(time.monotonic() - t0, 3)
    r["exit"] = proc.returncode
    if proc.returncode != 0:
        r["error"] = "exit %s" % proc.returncode + "".join(
            "; %s: %s" % (name, str(text).strip()[:ERR_SNIPPET])
            for name, text in (("stderr", proc.stderr or ""), ("stdout", proc.stdout or "")) if str(text).strip())
        return r
    try:
        body = json.loads(proc.stdout or "")
    except ValueError:
        r["error"] = "stdout is not JSON"
        return r
    text = body.get("result") if isinstance(body, dict) else None
    if isinstance(text, str):
        r["answer"] = text
    if isinstance(body, dict) and body.get("is_error"):
        r["error"] = "cli error"
    elif not isinstance(text, str) or not text.strip():
        r["error"] = "no result text"
    else:
        r["ok"] = True
    return r
