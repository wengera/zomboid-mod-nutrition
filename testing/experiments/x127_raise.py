"""Slice 12, session 7 (`x127`): what does an UNGUARDED Kahlua nil call do to the rest of its own
event handler and to the handlers registered BEHIND it, and does the NESTED `pcall` shape catch?
-- LIVE.

**This session exists because session 6 answered its question by not raising.**
`x126-20260911-045205` measured `pcall(TKX_DefinitelyNil)` -- the undefined global passed as
pcall's function ARGUMENT, which is the exact shape `TK.call` and every mod's `tkxCall` use -- and
found it CAUGHT on both Lua states, returning `false, "tried to call nil
java.lang.RuntimeException"`. The library's standing rule ("a Kahlua nil call escapes `pcall` and
kills the whole handler") is therefore wrong on its FIRST half. But because the pcall caught,
nothing ever raised, and two questions were left open by construction:

  1. Does an UNGUARDED nil call abort the rest of its own handler's body, and do the handlers
     registered AFTER it still run? The Task 9 jar review says `zombie/Lua/Event.trigger` calls
     each callback through `LuaCaller.protectedCallVoid` (`@89`, `@276`) inside a per-iteration
     `catch (Throwable)` (`@194-@198 L41-L42`) and CONTINUES the loop (`@216-@219 L31`) -- so the
     rule's SECOND half should be wrong about the chain and right about the handler body.
  2. Does `pcall(function() SomeNil() end)` catch too? There the raise comes from one frame
     deeper, inside the NESTED `luaMainloop` (`KahluaThread.call(I)I @155-@158 L162`), rather than
     from the argument slot. `KahluaThread.pcall(I)I`'s try (`@173-@186 L1755-L1757`,
     `@189-@213 L1758-L1760`) looks like it covers that too -- but that is a jar reading, and a
     jar reading of what the engine COULD do is not a reading of what it DOES.

One mod, one event, four handlers, both Lua states, both questions.

**The probe** (`testing/experiments/TKX_RaiseProbe`, a single `shared/` file so the server VM and
the client VM each run their own copy, giving two independent readings rather than one):

    H0  `TKX_R.before` ++                             -- the event fires and the chain reaches here
    H1  `pcall(function() TKX_DefinitelyNilToo() end)`-- the NESTED shape; then ok/err, then
                                                        `nested_tail` ++
    H2  `TKX_DefinitelyNilThree()` UNGUARDED, then `raw_tail` ++  -- if the raise aborts the body,
                                                        `raw_tail` never advances
    H3  `TKX_R.behind` ++                             -- registered AFTER the raising handler

Every field is a STRING. A `false` arriving through `lua.global` would be indistinguishable from a
walk that stopped, and `"unset"` vs `"false"` is the distinction H1 turns on: `"unset"` is the
value the table constructor put there, so it means *the assignment line never ran*. `raw_tail`
staying at `"0"` while `behind` advances is the whole of H2/H3.

**What the acceptance boot already showed, and why this driver is not shaped exactly like x126's.**
The Step-3 acceptance run (`run-20260911-050339`, `pzt run --profile x12-raise --hold 5`) did NOT
come back PASS. It came back

    RESULT: FAIL: 970 server error lines; lua errors on admin

and its timeline carries `TimeoutError: admin: not ready within 300s (seen: ['in_game',
'lua_error'], clicks: 126)`. The SERVER survived the raise and kept firing `EveryOneMinute` for the
whole 384 s (194 `tried to call nil` lines = two per fire, ~97 fires), printing one stack trace for
H1 (`TKX_RaiseProbe.lua:32`, `Object tried to call nil in pcall`) and one for H2
(`TKX_RaiseProbe.lua:37`, `Object tried to call nil in Add`) on every fire. The CLIENT printed
exactly ONE trace -- H1's -- at frame `f:1` of `IngameState`, 50 s after launch, and then stopped
logging entirely and never printed `PZTK: player admin at ...`, the line the orchestrator keys on
for `ready`. A healthy client at that same point (session 6's acceptance, `run-20260911-044417`)
goes on rendering and prints that line at `f:21`.

The brief anticipated this: "a raise in a mod handler must NOT fail the boot -- if it does, that is
a reading: record it and continue with the driver if the session still comes up". It half came up.
So this driver keeps x126's shape (provenance keys, wall-bracketed `probe()`, the dormant `sent`
branch, the re-ask-once guard, `grade()` over the fixed verdict vocabulary, try/except/finally with
the artifact written before AND after teardown) and adds exactly the robustness the acceptance boot
showed is needed -- all of it BEFORE the boot, never after:

  * `c.wait_ready()` is bounded (90 s, ~2.6x the 35 s a healthy client takes) and CAUGHT. A
    TimeoutError there is a reading, recorded with `c.seen`, not an abort.
  * `verify()` is caught for the same reason: it sends a client command with a 30 s timeout, and a
    frozen client would otherwise take the session down with it.
  * every client probe after the bus has been shown not to answer uses a 4 s timeout instead of
    20 s, so a dead client costs the session ~40 s per pass rather than ~200 s. The FIRST client
    probe still gets the full 20 s -- the short timeout is only ever used once the long one has
    already failed.
  * the wait falls back to the SERVER's own `TKX_R.before` when the client's never answers, so the
    server readings are still taken in a state where the event has fired at least twice.
  * `grep_numbered` now counts the WHOLE file and stores a bounded slice of it (head + tail),
    instead of x126's break-at-limit. The server log carries ~700 `TKX_RaiseProbe` frame lines in a
    session this length; a break-at-limit would have reported a count that was really a limit, and
    keeping all of them verbatim would have put a megabyte of stack frames in the artifact. Count
    is exact; storage is bounded and says so.
  * every grep hit is tagged `harness_echo` when the line is the harness echoing this driver's own
    bus reply (`PZTK: cmd #N ...`), and every block reports `engine_count = count - echo_count`.
    Session 6's report had to explain by hand that all four of its `tried to call` hits were echoes;
    here the split is measured.

Nothing here writes world state: no `additem`, no `nutrition.set`, no `moddata.set`, no `item.set`,
no `eat.action`, no `lua.reload`. There is nothing to restore.

Never raises through teardown; the artifact is written before and after teardown and copied
byte-for-byte into `testing/artifacts/<run-id>/`.
"""
import json
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, save        # noqa: E402
from pzt import fixture as fx, profile                                      # noqa: E402
from pzt.paths import new_run_dir                                           # noqa: E402
from pzt.session import (Timeline, make_client, make_server,               # noqa: E402
                         teardown, verify)

PROFILE = "x12-raise"
USER = "admin"
MODS = ("PZTestKit", "TKX_RaiseProbe")

# ---- Step 3's acceptance run, recorded verbatim because it is itself the session's first reading
ACCEPTANCE_RUN = "run-20260911-050339"
ACCEPTANCE_RESULT = "FAIL: 970 server error lines; lua errors on admin"
ACCEPTANCE_READING = {
    "expected_by_the_brief": "PASS -- a raise in a mod handler must not fail the boot",
    "observed": ACCEPTANCE_RESULT,
    "faults": ["970 server error lines", "lua errors on admin"],
    "timeline_error": "TimeoutError: admin: not ready within 300s "
                      "(seen: ['in_game', 'lua_error'], clicks: 126)",
    "verify_rows_run": 0,
    "why_verify_is_empty": "`pzt run` raised at wait_ready, so the single tier-(a) gate "
                           "(client `lua.global TKX_R.version`) was never sent. That is NOT a "
                           "reading about the gate -- it is a reading about the client.",
    "server": "survived. server_stopped rc=0 after 384.7 s, 970 error lines, two engine stack "
              "traces per EveryOneMinute fire (H1 at TKX_RaiseProbe.lua:32, H2 at :37) for ~97 "
              "fires. The server's EveryOneMinute kept firing to the end.",
    "client": "froze. One trace only -- H1's, at frame f:1 of IngameState, 05:04:30, ~50 s after "
              "launch -- and then console.txt and the DebugLog both stop dead. `PZTK: player "
              "admin at ...` (the orchestrator's `ready` line) never printed. Session 6's "
              "acceptance client, at the identical point in the join, went on to frame f:21 and "
              "printed it.",
    "client_debug_caveat": "the harness runs the admin client with -debug (client.py: debug "
                           "defaults to True for the admin user). The client's dump comes from "
                           "KahluaUtil.fail(KahluaUtil.java:96) while the server's comes from "
                           ":100 -- two different call sites in the same method, so the client is "
                           "on a debug-only branch. Whether a NON-debug client freezes the same "
                           "way is NOT measured by this session and must not be claimed.",
}
ACCEPTANCE_LOADING_LINES = {"server": {"PZTestKit": 93, "TKX_RaiseProbe": 94},
                            "client": {"PZTestKit": [83, 162], "TKX_RaiseProbe": [84, 163]}}
# Full-file counts over that run's two logs (384 s of session, ~97 server fires, a client that
# stopped logging after one). These size the storage limits below; `count` in this driver is
# always exact, so a limit only ever bounds how many hits are KEPT.
ACCEPTANCE_GREP_COUNTS = {"TKX_DefinitelyNilThree": {"server": 0, "client": 0},
                          "TKX_DefinitelyNilToo": {"server": 0, "client": 0},
                          "tried to call nil": {"server": 194, "client": 1},
                          "attempted to call": {"server": 0, "client": 0},
                          "ExceptionLogger": {"server": 0, "client": 0},
                          "TKX_RaiseProbe": {"server": 879, "client": 12}}

# ---- timings -----------------------------------------------------------------------------------
DAY_LENGTH = 4           # the fixture's own (testing/fixtures/default/.../pzt_SandboxVars.lua:53)
GAME_MINUTE_S = 3.75     # DayLength 4 = a 90-minute game day: 5400 s / 1440 game minutes
CLIENT_READY_TIMEOUT_S = 90.0   # a healthy client takes ~35 s from launch; the frozen one took 50 s
WAIT_TARGET = 2          # `TKX_R.before` must reach this before anything is read
WAIT_POLL_S = 2.0
WAIT_CAP_S = 30.0        # 8 game minutes' worth of headroom over the 7.5 s the target needs
SECOND_PASS_S = 12.0     # supplementary only -- see `second_pass` below
PROBE_TIMEOUT_S = 20     # the normal bus timeout, and the one the FIRST client probe always gets
PROBE_TIMEOUT_DEAD_S = 4  # only after a probe on that side has already failed the full timeout

# ---- the seven readings, plus the controls -----------------------------------------------------
# Order is the order they are read in, and it is the order of the probe file: H0's counter first,
# then H1's three, then H2's, then H3's. `side` leads because a reading whose side is "?" is a
# reading from a Lua state that never resolved which side it was on.
FIELDS = ("side", "before", "nested_ok", "nested_err", "nested_tail", "raw_tail", "behind")
COUNTERS = ("before", "nested_tail", "raw_tail", "behind")
TABLE_GLOBAL = "TKX_R"
TABLE_KEYS_EXPECTED = 8   # side, before, nested_ok, nested_err, nested_tail, raw_tail, behind,
                          # version
CONTROL_GLOBAL = "TK.version"
# `TKX_R.version` is the profile's tier-(a) gate and is re-read here as the mod-side control: it is
# assigned in the table constructor on the file's first statement, so a 1 says the file RAN,
# whatever the handlers did afterwards -- including the one that raises.
MOD_CONTROL_GLOBAL = "TKX_R.version"

# ---- what the strings are allowed to mean ------------------------------------------------------
UNSET = "unset"
# A message is not a fixed string -- Kahlua's own wording is what the run is there to record -- so
# the test is recorded as separate booleans beside the verbatim text rather than as one regex that
# could quietly mis-grade a message nobody has seen yet.
NIL_RX = re.compile(r"\bnil\b", re.I)
CALL_RX = re.compile(r"call", re.I)
NAME_RX = re.compile(r"TKX_DefinitelyNilToo")

# ---- greps -------------------------------------------------------------------------------------
# `count` is a full-file count, ALWAYS exact. `keep` bounds only how many hits are stored verbatim
# (head), with the last `KEEP_TAIL` kept as well so the end of the session is visible even when the
# head fills up; `complete` says whether every hit is present. Client keeps are >= 2x the
# acceptance-run count plus headroom (amendment 6) and comfortably above it for the open-ended
# error patterns; the server log is read once.
#
# The first six are the brief's. The four after them are EXTRA, added because the acceptance boot
# showed the engine prints a DIFFERENT trace for each handler, and the line number is the only
# thing that separates them: `:32` is H1's `pcall(function() ... end)` and `:37` is H2's unguarded
# call, in THIS file with THIS header (the file's own two lines are recorded in `probe.lines` so a
# reader can check the pin rather than trust it).
KEEP_TAIL = 8
GREPS = (
    # name, regex, keep_client, keep_server, brief
    ("TKX_DefinitelyNilThree", re.compile(r"TKX_DefinitelyNilThree"), 40, 40, True),
    ("TKX_DefinitelyNilToo", re.compile(r"TKX_DefinitelyNilToo"), 40, 40, True),
    ("tried to call nil", re.compile(r"tried to call nil", re.I), 80, 60, True),
    ("attempted to call", re.compile(r"attempted to call", re.I), 40, 40, True),
    ("ExceptionLogger", re.compile(r"ExceptionLogger"), 40, 40, True),
    ("TKX_RaiseProbe", re.compile(r"TKX_RaiseProbe"), 60, 40, True),
    ("H1 frame .lua:32", re.compile(r"TKX_RaiseProbe\.lua:32"), 40, 40, False),
    ("H2 frame .lua:37", re.compile(r"TKX_RaiseProbe\.lua:37"), 40, 40, False),
    ("nil in pcall", re.compile(r"Object tried to call nil in pcall"), 40, 40, False),
    ("nil in Add", re.compile(r"Object tried to call nil in Add"), 40, 40, False),
)
# The harness echoes every bus reply into the same log it is grepped from ("PZTK: cmd #4 lua.global
# -> {...}"), so a reading whose VALUE contains `tried to call nil` shows up as a hit that the
# engine never printed. Session 6 had to explain that by hand; here it is measured per block.
ECHO_RX = re.compile(r"PZTK: cmd\b")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
PROBE_FILE = "testing/experiments/TKX_RaiseProbe/42.20/media/lua/shared/TKX_RaiseProbe.lua"
HARNESS_LUA_COMMIT_EXPECTED = "5d9633f"   # the brief's pin; the computed value is recorded beside

P22_PREDICTED = (
    "P22, per side, two halves of one question. H1 (the NESTED pcall shape): TKX_R.nested_ok == "
    "\"false\", TKX_R.nested_err a message, TKX_R.nested_tail >= \"1\" -- the nested shape CATCHES "
    "too, i.e. the whole dynamic extent of pcall is protected, which is the Task 9 jar reading "
    "(KahluaThread.pcall's try covers the nested luaMainloop, not merely the argument slot). "
    "H2/H3 (the UNGUARDED raise): TKX_R.raw_tail == \"0\" with TKX_R.behind >= \"1\" and "
    "advancing -- an unguarded nil call aborts the rest of THAT handler's body and the engine runs "
    "the handlers registered behind it, which is Event.trigger's per-callback catch (Throwable) "
    "confirmed live. Both halves must land for the side's P22 verdict to be as_predicted."
)
P22_FALSIFIER = (
    "H1 is falsified by nested_ok == \"unset\" / nested_tail == \"0\": the nested shape does NOT "
    "catch, a raise from inside the nested luaMainloop escapes, and the message is recorded "
    "verbatim. Anything else (nested_ok == \"true\", or ok assigned while the tail did not "
    "advance) is h1_other and graded falsified like any other non-match. H2/H3 is falsified by "
    "raw_tail >= \"1\", which would mean the unguarded nil call did not raise AT ALL (unexpected, "
    "recorded verbatim), or by behind == \"0\" while before advances, which would mean the raise "
    "kills the chain behind it and the library's old sentence was right after all. A side is "
    "UNMEASURED -- not graded -- when a field did not resolve or H0's counter never left \"0\": "
    "the first says the bus or the _G walk did not answer on that side, the second says the event "
    "never fired there, and an H1/H2 reading taken under either says nothing about the rule."
)

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x127")
path = os.path.join(run_dir, "platform-raise.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
harness_lua_commit = git_say("log", "-1", "--format=%h", "--", LUA_DIR)


def probe_lines():
    """The two pinned lines of the probe file, read from disk at run time. The greps pin H1 to
    `:32` and H2 to `:37`; recording what is actually on those lines makes the pin checkable."""
    try:
        with open(os.path.join(REPO, PROBE_FILE), encoding="utf-8") as fh:
            src = fh.read().splitlines()
        return {"32": src[31].strip(), "37": src[36].strip(), "line_count": len(src)}
    except (OSError, IndexError) as e:            # noqa: BLE001 - provenance, never fatal
        return {"error": f"{type(e).__name__}: {e}"}


out = {
    "run_id": run_id,
    "session": "x127 -- slice 12 session 7: what does an UNGUARDED Kahlua nil call do to the rest "
               "of its handler and to the handlers behind it, and does the nested pcall shape "
               "catch?",
    "user": USER,
    "profile": prof.report(),
    "mods": list(MODS),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": harness_lua_commit,
    "harness_lua_commit_expected": HARNESS_LUA_COMMIT_EXPECTED,
    "harness_lua_commit_matches": harness_lua_commit == HARNESS_LUA_COMMIT_EXPECTED,
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "acceptance_result": ACCEPTANCE_RESULT,
    "acceptance_reading": ACCEPTANCE_READING,
    "acceptance_loading_lines": ACCEPTANCE_LOADING_LINES,
    "acceptance_grep_counts": ACCEPTANCE_GREP_COUNTS,
    "fixture_day_length": DAY_LENGTH,
    "game_minute_seconds": GAME_MINUTE_S,
    "why": "session 6 (x126-20260911-045205) found pcall(<nil>) CATCHES on both sides, which "
           "falsifies the first half of the library's standing rule -- but because it caught, "
           "nothing raised, so (1) 'kills the whole handler / the chain' was never tested and "
           "(2) the nested shape pcall(function() SomeNil() end), where the raise comes from "
           "inside the nested luaMainloop rather than from the argument slot, was never tested "
           "either. The jar says Event.trigger's per-callback catch (Throwable) continues the "
           "loop and KahluaThread.pcall's try covers the nested call; both are readings of what "
           "the engine COULD do.",
    "probe": {
        "mod": "TKX_RaiseProbe",
        "file": PROBE_FILE,
        "lines": probe_lines(),
        "shared_why": "shared/ on purpose -- the server VM and the client VM each run their own "
                      "copy, so the session gets TWO independent readings of one question.",
        "handlers": {
            "H0": "TKX_R.before ++ -- the event fires and the chain reaches this file",
            "H1": "local ok, err = pcall(function() TKX_DefinitelyNilToo() end); then nested_ok / "
                  "nested_err assigned and nested_tail ++  (file line 32)",
            "H2": "TKX_DefinitelyNilThree() UNGUARDED, then raw_tail ++  (file line 37) -- if the "
                  "raise aborts the body, raw_tail never advances",
            "H3": "TKX_R.behind ++ -- registered AFTER the raising handler",
        },
        "strings_why": "every field is a STRING: a `false` arriving through lua.global would be "
                       "indistinguishable from a walk that stopped, and \"unset\" vs \"false\" is "
                       "the whole of H1 -- \"unset\" is what the table constructor put there, so "
                       "it means the assignment line never ran.",
    },
    "scope_exclusions": {
        "applies_here": False,
        "why": "no modData census is taken this session -- every reading is a lua.global on one "
               "table this run's own mod defines. The per-scope exclusion sets (pass-1 precedent, "
               "docs/decisions.md:133) are recorded as inapplicable rather than silently omitted.",
    },
    "world_changes": {
        "restored": "nothing needs restoring -- this session writes NO state. No additem, no "
                    "nutrition.set, no moddata.set, no item.set, no eat.action.",
        "left_in_place": [],
        "lua_reload": "never sent -- re-running the probe file would reset TKX_R's counters and "
                      "re-register all four handlers on top of the live ones, which is not a "
                      "state any reading here should be taken in.",
    },
    "p22_predicted": P22_PREDICTED,
    "p22_falsifier": P22_FALSIFIER,
    "notes": [], "phases": {}, "verdicts": {},
}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


# The dormant `sent` branch's routing table, carried for shape parity with the sessions that use
# it. Every command in THIS driver (`lua.global` only) answers INLINE, so the branch never fires.
RESULT_DOC = {"witness.fields": "witness_fields", "witness.moddata": "witness_moddata"}

# Set to True the first time a probe on that side comes back as an `ask` error dict. Until then
# every probe gets the full timeout; after it, the short one. Recorded in the artifact.
bus_dead = {"client": False, "server": False}


def probe(side, cmd, args, side_name, timeout=None):
    """One read, with its own wall bracket, recorded whatever comes back.

    Three guards. Two are inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). Every command used here answers INLINE, so it is
        DORMANT; a command absent from `RESULT_DOC` is recorded raw rather than blocked on.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A string
        where a table belongs is re-asked ONCE and BOTH readings are kept. An `ask` ERROR is a
        dict, so a dead bus does NOT trip this guard and is never re-asked.
    The third is this session's own, and it exists because the acceptance boot froze the client:
      * once a probe on a side has come back as an `ask` error at the full 20 s timeout, every
        later probe on that side uses 4 s. A frozen client then costs ~40 s per pass instead of
        ~200 s, and the fact that it was demoted travels in the row (`short_timeout: true`).
    """
    if timeout is None:
        timeout = PROBE_TIMEOUT_DEAD_S if bus_dead.get(side_name) else PROBE_TIMEOUT_S
    t, t_epoch = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall(), "timeout": timeout,
            "short_timeout": timeout != PROBE_TIMEOUT_S}
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
        if val.get("error") and not bus_dead.get(side_name):
            bus_dead[side_name] = True
            note(f"{side_name}: bus did not answer `{cmd} {args}` within {timeout}s "
                 f"({val['error']}). Every later probe on this side uses "
                 f"{PROBE_TIMEOUT_DEAD_S}s.")
        val = dict(val)
        val["_probe"] = meta
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


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


def sval(reply):
    """The scalar `value` out of a `lua.global` reply, or None. `resolved` is checked rather than
    assumed: the fourth reply shape (`no _G on this build`) carries no `value` at all, an `ask`
    error dict carries neither, and a `resolved: false` reply means THIS PATH did not resolve --
    which for `TKX_R.nested_ok` would be a finding about the table, not about pcall."""
    if not isinstance(reply, dict):
        return None
    if reply.get("resolved") is not True:
        return None
    return reply.get("value")


def as_int(v):
    """The string counters as ints. They are STRINGS by design, so `num()` alone would answer None
    for every one of them; a value that is not a whole number in string form answers None rather
    than raising, and None is then read as 'not a counter'."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v == int(v) else None
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            return None
    return None


def grep_numbered(path_, rx, keep):
    """Full-file count with BOUNDED storage, and the harness's own echo lines split out.

    x126 broke at the limit, so a count equal to the limit meant saturation rather than a census.
    That does not survive this session: the server log carries hundreds of `TKX_RaiseProbe.lua:NN`
    stack frames, so a break-at-limit would have reported a limit dressed as a count, and keeping
    every hit verbatim would have put a megabyte of frames in the artifact. Here `count` is exact
    over the whole file, `kept` is the first `keep` hits, `kept_tail` is the last KEEP_TAIL, and
    `complete` says whether the two together are everything.

    `harness_echo` marks a hit that is the harness echoing THIS driver's own bus reply
    (`PZTK: cmd #N lua.global -> {...}`) rather than anything the engine printed -- the exact
    confusion session 6's report had to resolve by hand for its `tried to call` hits."""
    kept, tail, count, echo, lines = [], [], 0, 0, 0
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                lines = n
                if rx.search(line):
                    count += 1
                    is_echo = bool(ECHO_RX.search(line))
                    if is_echo:
                        echo += 1
                    row = {"line": n, "text": line.strip()[:300], "harness_echo": is_echo}
                    if len(kept) < keep:
                        kept.append(row)
                    else:
                        tail.append(row)
                        if len(tail) > KEEP_TAIL:
                            tail.pop(0)
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return {"error": f"{type(e).__name__}: {e}", "count": None, "kept": [], "kept_tail": [],
                "echo_count": None, "engine_count": None, "complete": False, "keep": keep,
                "scanned_lines": 0}
    return {"count": count, "echo_count": echo, "engine_count": count - echo,
            "kept": kept, "kept_tail": tail, "keep": keep,
            "complete": count <= keep, "scanned_lines": lines, "error": None}


def greps(c, when):
    """Every pattern over BOTH logs. `count` is exact; `keep` bounds storage only.

    The engine's own error line for an unguarded raise IS a reading, which is why every kept hit
    holds its line number and its verbatim text instead of being counted away -- and why the
    `harness_echo` flag travels with it, so a hit that is only this driver reading a string back
    through the bus can never be mistaken for the engine printing one."""
    blocks = {}
    for name, rx, keep_c, keep_s, from_brief in GREPS:
        s = grep_numbered(server.log_path, rx, keep_s)
        k = grep_numbered(c.console, rx, keep_c) if c is not None else {
            "error": "no client attached", "count": None}
        blocks[name] = {
            "pattern": rx.pattern, "when": when, "from_brief": from_brief,
            "server": s, "client": k,
            "acceptance_counts": ACCEPTANCE_GREP_COUNTS.get(name),
            "client_rule": "a client console runs TWO Lua states and prints engine load output "
                           "once per state, so a load-time count is expected at 2x the server's; "
                           "a RUNTIME error count is not, because only the in-session state runs "
                           "EveryOneMinute.",
        }
    return blocks


def read_side(side, side_name):
    """The seven fields, then the table's `keyCount`, then the two controls -- one `lua.global`
    each, every reply kept whole beside the value lifted out of it."""
    replies, values = {}, {}
    for f in FIELDS:
        r = probe(side, "lua.global", TABLE_GLOBAL + "." + f, side_name)
        replies[f] = r
        values[f] = sval(r)
    tbl = probe(side, "lua.global", TABLE_GLOBAL, side_name)
    mod_ctrl = probe(side, "lua.global", MOD_CONTROL_GLOBAL, side_name)
    harness_ctrl = probe(side, "lua.global", CONTROL_GLOBAL, side_name)
    row = {
        "side_asked": side_name,
        "values": values,
        "replies": replies,
        "table": {"reply": tbl,
                  "keyCount": tbl.get("keyCount") if isinstance(tbl, dict) else None,
                  "keyCount_expected": TABLE_KEYS_EXPECTED,
                  "type": tbl.get("type") if isinstance(tbl, dict) else None,
                  "resolved": tbl.get("resolved") if isinstance(tbl, dict) else None},
        "mod_control": {"global": MOD_CONTROL_GLOBAL, "reply": mod_ctrl,
                        "value": sval(mod_ctrl),
                        "why": "assigned in the table constructor on the file's first statement, "
                               "so a 1 says the file RAN whatever the handlers did afterwards."},
        "harness_control": {"global": CONTROL_GLOBAL, "reply": harness_ctrl,
                            "value": sval(harness_ctrl),
                            "why": "a resolved=false here means the _G walk itself is broken on "
                                   "this side and every reading above it is suspect -- it does "
                                   "NOT mean a mod global is absent. An `error` here instead "
                                   "means the bus did not answer at all."},
        "counters": {k: as_int(values.get(k)) for k in COUNTERS},
        "bus_dead_at_read": bus_dead.get(side_name),
        "wall": wall(),
    }
    row["table"]["keyCount_ok"] = row["table"]["keyCount"] == TABLE_KEYS_EXPECTED
    return row


def classify(row):
    """Which branch each half of P22 lands on for this side, with every gate named beside it.
    Nothing here re-reads: the branches are computed from the values already recorded."""
    v, ctr = row["values"], row["counters"]
    nested_ok, nested_err = v.get("nested_ok"), v.get("nested_err")
    before, nested_tail = ctr["before"], ctr["nested_tail"]
    raw_tail, behind = ctr["raw_tail"], ctr["behind"]

    readable = all(v.get(f) is not None for f in FIELDS) and \
        all(ctr[k] is not None for k in COUNTERS)
    event_fired = bool(before is not None and before >= 1)
    gated = readable and event_fired

    err_text = nested_err if isinstance(nested_err, str) else ""
    err_flags = {"verbatim": nested_err,
                 "mentions_nil": bool(NIL_RX.search(err_text)),
                 "mentions_call": bool(CALL_RX.search(err_text)),
                 "names_the_global": bool(NAME_RX.search(err_text)),
                 "is_unset": nested_err == UNSET}

    if not gated:
        h1 = h2 = "unmeasured"
    else:
        if nested_ok == "false" and nested_err != UNSET and nested_tail >= 1:
            h1 = "h1_nested_catches"
        elif nested_ok == UNSET and nested_tail == 0:
            h1 = "h1_nested_escapes"
        else:
            h1 = "h1_other"
        if raw_tail >= 1:
            h2 = "h2_no_raise"
        elif behind >= 1:
            h2 = "h2_aborts_body_chain_continues"
        else:
            h2 = "h2_aborts_body_chain_dies"

    h1_verdict = {"h1_nested_catches": "as_predicted", "unmeasured": "unmeasured"}.get(
        h1, "falsified")
    h2_verdict = {"h2_aborts_body_chain_continues": "as_predicted",
                  "unmeasured": "unmeasured"}.get(h2, "falsified")
    if h1_verdict == "unmeasured" or h2_verdict == "unmeasured":
        verdict = "unmeasured"
    elif h1_verdict == "as_predicted" and h2_verdict == "as_predicted":
        verdict = "as_predicted"
    else:
        verdict = "falsified"

    means = {
        "h1_nested_catches":
            "pcall(function() SomeNil() end) CAUGHT the raise on this side: ok came back false, "
            "err carries a message and the three lines after the pcall ran. The whole dynamic "
            "extent of pcall is protected, not just the argument slot -- KahluaThread.pcall's try "
            "covers the nested luaMainloop, exactly as the jar reads. A doc sentence of the form "
            "'wrapping your handler body in pcall catches nil calls inside it' is now MEASURED.",
        "h1_nested_escapes":
            "the nested shape did NOT catch: nested_ok and nested_err are still the constructor's "
            "\"unset\" and nested_tail never advanced, so a raise from inside the nested "
            "luaMainloop escapes pcall. Session 6's catch would then be specific to the argument "
            "slot, and `tkxCall`'s shape would be the ONLY one that protects.",
        "h1_other":
            "neither branch for H1. Recorded verbatim and graded falsified like any other "
            "non-match -- in particular nested_ok == \"true\" would mean pcall returned SUCCESS "
            "on a nil call, which no reading of the jar predicts.",
        "h2_aborts_body_chain_continues":
            "the unguarded raise aborted the REST of its own handler's body (raw_tail never "
            "advanced past the nil call) and the engine ran the handler registered BEHIND it "
            "anyway (behind advanced). Event.trigger's per-callback catch (Throwable) is "
            "confirmed live: the standing rule is right about the handler body and WRONG about "
            "the chain.",
        "h2_no_raise":
            "raw_tail advanced, so the unguarded nil call did not raise at all on this side. "
            "Unexpected under every reading of the jar; recorded verbatim.",
        "h2_aborts_body_chain_dies":
            "the unguarded raise aborted the body AND the handler registered behind it never "
            "ran, while the event kept firing. The library's old sentence -- the raise kills the "
            "chain -- would be right after all.",
        "unmeasured":
            "not graded. Either a field did not resolve (the bus or the _G walk did not answer on "
            "this side) or H0's counter never left \"0\" (the event never fired here), and a "
            "reading taken under either says nothing about the rule.",
    }
    return {
        "h1_branch": h1, "h1_verdict": h1_verdict, "h1_means": means[h1],
        "h2_branch": h2, "h2_verdict": h2_verdict, "h2_means": means[h2],
        "verdict": verdict,
        "gates": {"readable": readable, "event_fired": event_fired,
                  "table_keyCount_ok": row["table"]["keyCount_ok"],
                  "table_keyCount": row["table"]["keyCount"],
                  "mod_control_value": row["mod_control"]["value"],
                  "harness_control_value": row["harness_control"]["value"],
                  "bus_dead_at_read": row.get("bus_dead_at_read")},
        "readings": {"side_reported": v.get("side"), "nested_ok": nested_ok, "err": err_flags,
                     "before": before, "nested_tail": nested_tail,
                     "raw_tail": raw_tail, "behind": behind},
    }


try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    # BOUNDED and CAUGHT. The acceptance boot's client reached `in_game`, printed one Kahlua stack
    # trace at frame f:1 of IngameState and then stopped logging for 300 s; `PZTK: player <user>
    # at ...`, the orchestrator's `ready` line, never came. That is a reading about the engine,
    # not a reason to throw the session away -- the server half is still fully readable.
    ready = {"timeout_s": CLIENT_READY_TIMEOUT_S}
    try:
        ready["value"] = c.wait_ready(timeout=CLIENT_READY_TIMEOUT_S)
        ready["ok"] = True
    except (TimeoutError, RuntimeError) as e:     # noqa: BLE001 - the reading, not an abort
        ready["ok"] = False
        ready["error"] = f"{type(e).__name__}: {e}"
        note("client never reached `ready` (PZTK: player <user> at ...) inside "
             f"{CLIENT_READY_TIMEOUT_S}s: {ready['error']}. The session continues -- the server "
             "side is read normally and the client side is read for as long as its bus answers.")
    ready["seen"] = sorted(getattr(c, "seen", {}) or {})
    ready["client_alive"] = c.alive
    ready["wall"] = wall()
    out["client_ready"] = ready
    tl.mark("session_ready", client_ready=str(ready["ok"]))
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    # CAUGHT for the same reason: `verify` sends a client command with a 30 s timeout and lets the
    # exception out, which on a frozen client would take the session down after it had already
    # been paid for.
    try:
        out["verify"] = verify(prof, server, clients, tl)
        out["verify_error"] = None
    except (RuntimeError, TimeoutError, OSError) as e:   # noqa: BLE001 - recorded, not raised
        out["verify"] = []
        out["verify_error"] = f"{type(e).__name__}: {e}"
        note(f"the profile's tier-(a) gate could not be sent: {out['verify_error']}")
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}
    mods_dir = os.path.join(server.cache, "mods")
    try:
        listing = sorted(os.listdir(mods_dir))
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        listing = [f"error: {type(e).__name__}: {e}"]
    out["mods_dir"] = {"path": os.path.relpath(mods_dir, REPO), "listing": listing,
                       "probe_folder_present": "TKX_RaiseProbe" in listing}
    save(path, out, tl, server)

    # ================= the wait: a counter, not a clock =================================
    # `EveryOneMinute` at DayLength 4 fires every 3.75 s real, so `before` needs ~7.5 s to reach 2.
    # The CLIENT is polled first, as the brief specifies. If the client's bus never answers the
    # target, the SERVER's own counter is polled instead -- the server readings still have to be
    # taken in a state where the event has fired at least twice, and the client's silence is the
    # client's reading, not a reason to read the server too early.
    def wait_on(side, side_name):
        polls, target_met = [], False
        t_wait0 = wall()
        while True:
            r = probe(side, "lua.global", TABLE_GLOBAL + ".before", side_name)
            n = as_int(sval(r))
            polls.append({"wall": wall(), "value": sval(r), "int": n,
                          "resolved": r.get("resolved") if isinstance(r, dict) else None,
                          "error": r.get("error") if isinstance(r, dict) else None})
            if n is not None and n >= WAIT_TARGET:
                target_met = True
                break
            if wall() - t_wait0 >= WAIT_CAP_S:
                break
            time.sleep(WAIT_POLL_S)
        return {"side": side_name, "polls": polls, "target_met": target_met,
                "waited_s": round(wall() - t_wait0, 3)}

    wait_client = wait_on(c, "client")
    wait_server = None
    if not wait_client["target_met"]:
        note("TKX_R.before never reached 2 on the client inside the 30 s cap. Falling back to the "
             "SERVER's own counter so the server readings are still taken after at least two "
             "fires; the client side is graded on its own H0 counter, as always.")
        wait_server = wait_on(server, "server")
    out["wait"] = {
        "global": TABLE_GLOBAL + ".before", "target": WAIT_TARGET,
        "poll_every_s": WAIT_POLL_S, "cap_s": WAIT_CAP_S,
        "client": wait_client, "server_fallback": wait_server,
        "why": "H0 is registered FIRST on the event, so `before` reaching 2 proves the event has "
               "fired at least twice AND that the chain reaches this file -- which is the only "
               "state in which the H1 and H2 readings mean anything.",
        "cadence": f"DayLength {DAY_LENGTH} -> {GAME_MINUTE_S} s per game minute",
    }
    tl.mark("wait_done", client=str(wait_client["target_met"]),
            server=str(wait_server["target_met"] if wait_server else "not needed"))
    save(path, out, tl, server)

    # ================= the reads: CLIENT FIRST, then the server ========================
    # Client first, always: the read ORDER is what fixes the sign of any cross-side comparison,
    # and these two Lua states are running the same file independently.
    reads = {"client": read_side(c, "client")}
    tl.mark("read_client")
    reads["server"] = read_side(server, "server")
    tl.mark("read_server")
    out["phases"]["reads"] = {
        "question": "does an unguarded Kahlua nil call abort the rest of its handler's body and "
                    "kill the handlers registered behind it, and does pcall(function() Nil() end) "
                    "catch?",
        "order": "client first, then server",
        "fields": list(FIELDS),
        "client": reads["client"], "server": reads["server"],
    }
    save(path, out, tl, server)

    # ================= the log, read at the same moment as the values ==================
    out["greps"] = greps(c, "after the graded reads")
    save(path, out, tl, server)

    # ================= P22, graded per side ============================================
    cls = {s: classify(reads[s]) for s in ("client", "server")}
    out["phases"]["classification"] = cls
    for side_name in ("client", "server"):
        k = cls[side_name]
        grade(
            "P22_" + side_name,
            P22_PREDICTED,
            {"side": side_name,
             "side_reported_by_probe": reads[side_name]["values"].get("side"),
             "values": reads[side_name]["values"],
             "counters": reads[side_name]["counters"],
             "h1_branch": k["h1_branch"], "h1_verdict": k["h1_verdict"], "h1_means": k["h1_means"],
             "h2_branch": k["h2_branch"], "h2_verdict": k["h2_verdict"], "h2_means": k["h2_means"],
             "gates": k["gates"],
             "nested_err": k["readings"]["err"],
             "table_keyCount": reads[side_name]["table"]["keyCount"],
             "engine_log": {
                 name: {"server": out["greps"][name]["server"].get("engine_count"),
                        "client": out["greps"][name]["client"].get("engine_count")}
                 for name, _, _, _, _ in GREPS},
             },
            k["verdict"],
            P22_FALSIFIER,
            {"h1_branch": k["h1_branch"], "h2_branch": k["h2_branch"]})

    # ================= did the engine LOG the unguarded raise? =========================
    # Session 6's reading was that a CAUGHT nil call is silent in the log. H2's raise is not
    # caught by anything the mod wrote, so whether the engine prints it -- and in what words -- is
    # the log signature a mod author would have to grep for. `engine_count` excludes the harness's
    # own `PZTK: cmd` echo lines, so a hit here is the engine's own.
    def first_engine_hit(name, side_name):
        blk = out["greps"].get(name, {}).get(side_name, {})
        for row in list(blk.get("kept") or []) + list(blk.get("kept_tail") or []):
            if not row.get("harness_echo"):
                return row
        return None

    out["phases"]["engine_log_signature"] = {
        "question": "did the engine LOG the unguarded raise, and in what words?",
        "excludes": "every line matching `PZTK: cmd` -- the harness echoing this driver's own bus "
                    "replies back into the same log it is grepped from. Counts below are "
                    "engine_count = count - echo_count.",
        "per_side": {
            side_name: {
                "h2_frame_lines": out["greps"]["H2 frame .lua:37"][side_name].get("engine_count"),
                "h2_first_hit": first_engine_hit("H2 frame .lua:37", side_name),
                "h2_message_lines": out["greps"]["nil in Add"][side_name].get("engine_count"),
                "h2_message_first_hit": first_engine_hit("nil in Add", side_name),
                "h1_frame_lines": out["greps"]["H1 frame .lua:32"][side_name].get("engine_count"),
                "h1_first_hit": first_engine_hit("H1 frame .lua:32", side_name),
                "h1_message_lines": out["greps"]["nil in pcall"][side_name].get("engine_count"),
                "h1_message_first_hit": first_engine_hit("nil in pcall", side_name),
                "names_the_global": {
                    "TKX_DefinitelyNilThree":
                        out["greps"]["TKX_DefinitelyNilThree"][side_name].get("engine_count"),
                    "TKX_DefinitelyNilToo":
                        out["greps"]["TKX_DefinitelyNilToo"][side_name].get("engine_count")},
            } for side_name in ("server", "client")
        },
    }
    save(path, out, tl, server)

    # ================= supplementary: do the counters keep advancing? ==================
    # NOT part of P22's grading -- P22 is graded on the reads above and nothing here can change
    # it. It is here because a single snapshot cannot tell a counter that advances once from a
    # counter that advances every fire, and "behind advanced by as many as before did, while
    # raw_tail did not move at all" is the cheapest possible corroboration of whichever branch the
    # snapshot landed on.
    time.sleep(SECOND_PASS_S)
    second = {"client": read_side(c, "client"), "server": read_side(server, "server")}
    deltas = {}
    for side_name in ("client", "server"):
        a, b = reads[side_name]["counters"], second[side_name]["counters"]
        deltas[side_name] = {k2: (None if (a[k2] is None or b[k2] is None) else b[k2] - a[k2])
                             for k2 in COUNTERS}
        k2nd = classify(second[side_name])
        deltas[side_name]["h1_first_pass"] = cls[side_name]["h1_branch"]
        deltas[side_name]["h1_second_pass"] = k2nd["h1_branch"]
        deltas[side_name]["h2_first_pass"] = cls[side_name]["h2_branch"]
        deltas[side_name]["h2_second_pass"] = k2nd["h2_branch"]
        deltas[side_name]["branches_agree"] = (
            deltas[side_name]["h1_first_pass"] == deltas[side_name]["h1_second_pass"]
            and deltas[side_name]["h2_first_pass"] == deltas[side_name]["h2_second_pass"])
    out["second_pass"] = {
        "gap_s": SECOND_PASS_S,
        "game_minutes_in_gap": round(SECOND_PASS_S / GAME_MINUTE_S, 2),
        "why": "supplementary corroboration, never a graded reading: a single snapshot cannot "
               "separate a counter that advanced once from one that advances every fire. A branch "
               "that DISAGREES between the two passes is itself the finding and is flagged here "
               "rather than averaged away.",
        "reads": second, "deltas": deltas,
    }
    for side_name in ("client", "server"):
        if not deltas[side_name]["branches_agree"]:
            note(f"{side_name}: a P22 branch CHANGED between the graded read and the "
                 f"supplementary read (h1 {deltas[side_name]['h1_first_pass']} -> "
                 f"{deltas[side_name]['h1_second_pass']}, h2 "
                 f"{deltas[side_name]['h2_first_pass']} -> "
                 f"{deltas[side_name]['h2_second_pass']}). The graded verdict stands on the first "
                 "pass, as the brief specifies; this disagreement is the finding.")
    save(path, out, tl, server)

    # The final log read: everything the engine printed across the whole session, including
    # whatever the second pass's extra game minutes produced.
    out["greps_final"] = greps(c, "end of session, after the supplementary read")

    # ================= the readings, stated as a summary ==============================
    out["summary"] = {
        "acceptance_result": ACCEPTANCE_RESULT,
        "client_ready": out["client_ready"]["ok"],
        "client_seen": out["client_ready"]["seen"],
        "client_bus_answered": not bus_dead["client"],
        "server_bus_answered": not bus_dead["server"],
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "wait_target_met": {"client": wait_client["target_met"],
                            "server_fallback": wait_server["target_met"] if wait_server else None},
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "h1_branch": {s: cls[s]["h1_branch"] for s in ("client", "server")},
        "h2_branch": {s: cls[s]["h2_branch"] for s in ("client", "server")},
        "sides_agree": (cls["client"]["h1_branch"] == cls["server"]["h1_branch"]
                        and cls["client"]["h2_branch"] == cls["server"]["h2_branch"]),
        "values": {s: reads[s]["values"] for s in ("client", "server")},
        "counters": {s: reads[s]["counters"] for s in ("client", "server")},
        "table_keyCount": {s: reads[s]["table"]["keyCount"] for s in ("client", "server")},
        "mod_control": {s: reads[s]["mod_control"]["value"] for s in ("client", "server")},
        "harness_control": {s: reads[s]["harness_control"]["value"]
                            for s in ("client", "server")},
        "second_pass_deltas": deltas,
        "grep_counts": {name: {"server": out["greps_final"][name]["server"].get("count"),
                               "server_engine":
                                   out["greps_final"][name]["server"].get("engine_count"),
                               "client": out["greps_final"][name]["client"].get("count"),
                               "client_engine":
                                   out["greps_final"][name]["client"].get("engine_count"),
                               "complete": [s for s in ("server", "client")
                                            if out["greps_final"][name][s].get("complete")]}
                        for name, _, _, _, _ in GREPS},
        "h1_means": {s: cls[s]["h1_means"] for s in ("client", "server")},
        "h2_means": {s: cls[s]["h2_means"] for s in ("client", "server")},
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
        out["bus_dead"] = dict(bus_dead)
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-raise.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
