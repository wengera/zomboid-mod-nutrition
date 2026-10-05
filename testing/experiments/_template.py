"""The driver template -- copy it, do not run it as it stands.

**What a driver is.** One Python script that boots a dedicated server and one client on a
throwaway copy of the golden fixture, asks the harness mod a fixed list of questions over the
command bus, and writes ONE artifact JSON that is the only thing any doc is allowed to cite. It
is an experiment record, not a program: the artifact has to be readable by someone who was not
there, so the driver writes down what it expected as well as what it got.

The house shape, every part of which is load-bearing:

  * **Provenance keys, first.** `run_id`, `session`, `user`, `profile` (`prof.report()` -- what
    was asked for AND what it resolved to), `mods`, `commit`, `harness_lua_commit`,
    `harness_lua_dirty` (+ `harness_lua_dirty_note`), `doctor_clean` (+ `doctor`) and
    `acceptance_run`. Together they say which build, which mods, which harness Lua and which
    smoke test the numbers below them came from. A reading whose provenance is missing is not
    citable, so this block is written BEFORE the session starts and never edited afterwards.
  * **Client-first paired reads.** The two sides of a snapshot are separate bus round trips ~1 s
    apart, so the sign of any cross-side comparison follows the READ ORDER rather than the game
    (`docs/decisions.md:158`). Read the CLIENT first at every tag, always in the same order, and
    a key seen on one side and not the other inside a push window reads as LATENCY rather than as
    a desync.
  * **Wall-bracketed steps with MEASURED offsets.** Every step records the wall clock before and
    after it, and every tag is named by what was measured, not by the sleep that was asked for
    (the slice-11 `td3` driver's `t+3s` tag actually landed at +7.6 s). A wait is chosen from a
    cadence that was read off the jar or measured, and both the requested and the measured wait
    go in the artifact.
  * **`field_count` asserts.** Every `witness.fields` reply carries a `count`; check it against
    the number of names that were SENT on every read rather than merely recording it, and roll
    the failures up into the summary. A reply whose count does not reconcile is a broken read,
    not a small number.
  * **Predictions, observations, verdicts.** Each phase states its prediction and its falsifier
    BEFORE the reading, then grades itself `as_predicted | falsified | trivial | unmeasured` and
    keeps all four beside each other in `out["verdicts"]`. `unmeasured` means the read never
    happened; `trivial` means it happened but the arm was never exercised; both are findings.
  * **try / except / finally.** The body runs inside a `try`; the `except` keeps the rows already
    collected and records the traceback; the `finally` ALWAYS saves the artifact, tears the
    session down, hard-kills whatever survived, saves again (so the committed artifact shows the
    teardown marks and any shutdown-phase server errors) and copies the file byte-for-byte into
    `testing/artifacts/<run-id>/`. Nothing in the driver may raise through teardown: no PZ
    process may outlive the script.
  * **`witness.moddata` values are STRINGS.** `_common.num` returns None on a string, so run a
    counter through `to_num` (below), never `num`, or every present counter grades as null (x132d).

**Starting a new driver.** Copy this file to `testing/experiments/xNNN_<topic>.py`, set `PROFILE`
to the profile the session runs under (`testing/profiles/<name>.toml`), write `SESSION` as the
one-line description that lands in the artifact, set `ARTIFACT` to `<topic>.json`, put the id of
the acceptance run that smoke-tested the harness for this session in `ACCEPTANCE_RUN`, then
replace the example phase `P1` with the real ones. Add the constants each phase needs (subjects,
expected field counts, exclusion sets, compiled regexes with limits >= 2x predicted) next to the
phase that uses them, and run `python testing/pzt doctor` before any boot.

`PZT_TEMPLATE_DRY_RUN=1` makes the module resolve its profile, fixture record, run dir and git
stamps, print the provenance block as one line of JSON and exit 0 WITHOUT starting a server or a
client. It is how `testing/tests/test_template.py` checks this file without a game; it is not a
mode a real driver needs to keep.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_…`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
"""
import json
import os
import re          # noqa: F401 - session.grep_file / grep_numbered take a COMPILED regex
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, num, save   # noqa: E402
from pzt import fixture as fx, profile                                      # noqa: E402
from pzt.paths import new_run_dir                                           # noqa: E402
from pzt.session import (Timeline, make_client, make_server,               # noqa: E402
                         teardown, verify)

PROFILE = "mod-under-test"
SESSION = "template -- describe the session in one line"
ARTIFACT = "template.json"
USER = "admin"
# The acceptance run (`python testing/pzt run --profile <name>`) that smoke-tested the harness
# for this session: RESULT, its [[verify]] rows, its server error count and its client Lua error
# count are what say the bus was answering before any of the readings below were taken.
ACCEPTANCE_RUN = "run-20260926-214408"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"

# No server, no client, no java: the provenance block only. See the module docstring.
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

# The dormant `sent` branch's routing table, emptied for the template (slice-11 driver note:
# td3's map covered only two of the five commands `probe` carries, so a fire on any other blocked
# on the wrong result document). Add a row -- `"<command>": "<result doc>"` -- only for a command
# whose ack really is `sent`; anything absent here is recorded raw rather than waited on.
RESULT_DOC = {}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def to_num(v):
    """Read a `witness.moddata` value: it arrives as a STRING, which `num` turns into None."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). Every command used here answers INLINE, so it is
        DORMANT; `RESULT_DOC` is the widened routing table (slice-11 driver note) and a command
        absent from it is recorded raw rather than blocked on.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A string
        where a table belongs is re-asked ONCE and BOTH readings are kept.
    """
    t, t_epoch = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if isinstance(val, str) and val.strip().startswith("sent"):
        name = RESULT_DOC.get(cmd)
        out["notes"].append({"dormant_sent_branch": cmd, "routed_to": name})
        if name is None:
            meta["route"] = "unmapped -- ack kept raw rather than waiting on a result doc"
        else:
            try:
                val = side.bus.wait_result(name, timeout=20, after=t_epoch)
            except (RuntimeError, TimeoutError, OSError) as e:
                val = {"error": f"{type(e).__name__}: {e}", "ack": val}
            meta["route"] = "result-doc"
    elif not isinstance(val, dict):
        meta["reasked"] = True
        meta["first_reply"] = val
        val = ask(side, cmd, args, timeout=timeout)
        meta["wall_done"] = wall()
    if isinstance(val, dict):
        val = dict(val)
        val["_probe"] = meta
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def step(name, side, cmd, args, timeout=30):
    """One SEQUENCED bus call: the ack, both wall clocks bracketing it, and the ack's own
    `serverWorldAge` / `gameMinute` lifted out where the reply carries them, so a game-minute
    rollover between two steps is measured rather than assumed."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": getattr(side, "username", "server"),
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if isinstance(val, dict):
        row["serverWorldAge"] = val.get("serverWorldAge")
        row["gameMinute"] = val.get("gameMinute")
        swa = num(val.get("serverWorldAge"))
        row["worldAgeMinutes"] = round(swa * 60.0, 4) if swa is not None else None
    else:
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    save(path, out, tl, server)
    return row


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    """The prediction, the falsifier, the reading and the verdict, in one place and beside each
    other. `verdict` is one of as_predicted / falsified / trivial / unmeasured -- a reading that
    comes back trivial or unmeasured is RECORDED as such and never re-run into a prettier one."""
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    # `name=`, NOT `phase=`: Timeline.mark's first POSITIONAL parameter is called `phase`
    # (session.py:31), so a `phase=` keyword here is a TypeError, not a detail field.
    tl.mark("verdict", name=phase, verdict=verdict)
    save(path, out, tl, server)
    return row


prof = profile.load(PROFILE)
# The fixture RECORD is gated too: `fixture.load` raises SystemExit when the fixture has no
# `cache/server` blob on this machine (fixture.py:65-67), and `testing/fixtures/*/cache/` is
# gitignored -- so an ungated read here would make the dry run, and its test, fail on a fresh
# clone. `rec` is consumed only inside the session below, which never runs under DRY_RUN.
rec = None if DRY_RUN else fx.load(prof.fixture)
# No run dir either: a dry run that boots nothing has nothing to write, and `new_run_dir` would
# leave an empty `testing/runs/template-<ts>/` behind on every test run. Both are used only
# after the dry-run branch has printed and exited.
run_id, run_dir = ("template-dry-run", None) if DRY_RUN else new_run_dir("template")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, clients, t0 = Timeline(), [], time.time()
server = None if DRY_RUN else make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                                          mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "world_changes": {"restored": "", "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)

try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact. `pzt run`
    # checks this and the artifact never recorded it, so "no mod failed to load" was unsayable.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ================= P1 -- the example phase. DELETE IT and write the real ones =======
    # It measures nothing: `ping` returns the string "pong" and exists so the shape below is a
    # working one -- a paired read taken CLIENT FIRST, both sides through `step` so each carries
    # its own wall bracket, then one `grade` whose verdict is computed from the reading.
    pings = {"client": step("p1_ping_client", c, "ping", ""),     # CLIENT FIRST at every tag
             "server": step("p1_ping_server", server, "ping", "")}
    answered = {s: (r["ack"] == "pong") for s, r in pings.items()}
    out["phases"]["P1"] = {
        "question": "is the bus answering on both sides? (the shape, not a measurement)",
        "acks": {s: r["ack"] for s, r in pings.items()},
        "walls": {s: {"before": r["wall_before"], "after": r["wall_after"], "took": r["took"]}
                  for s, r in pings.items()},
    }
    if not any(answered.values()):
        p1v = "unmeasured"        # neither side answered: nothing was read, so nothing is graded
    elif all(answered.values()):
        p1v = "as_predicted"
    else:
        p1v = "falsified"
    grade("P1", predicted="ok on both sides",
          observed={"answered": answered, "acks": out["phases"]["P1"]["acks"],
                    "walls": out["phases"]["P1"]["walls"]},
          verdict=p1v, falsifier="a side that does not answer")

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    save(path, out, tl, server)
    try:
        teardown(tl, server, clients)
    finally:
        hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["server_error_count"] = len(server.errors)
        out["client_lua_error"] = "lua_error" in getattr(clients[0], "seen", ()) if clients else None
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
