"""Slice 12, session 6 (`x126`): does a Kahlua nil call escape `pcall`, and does a raise in one
event handler kill the handlers registered BEHIND it? -- LIVE.

**This session exists because the library's most-cited platform rule has no committed evidence.**
"Kahlua's `tried to call nil` escapes `pcall` and kills the whole handler" is the stated reason
`TK.call` exists, the reason every experiment mod opens with its own six-line `tkxCall`, and the
reason `docs/modding/patterns.md` tells a mod author to index a member before calling it. The
whole rule rests on `exp01-20260909-235420`, a run with **no committed artifact**.

The Task 9 jar review traced the same claim the other way, on BOTH halves:

  * `BaseLib.pcall @0-@10 L313` -> `KahluaThread.pcall(I)I`, whose try (`@173-@186 L1755-L1757`,
    `@189-@213 L1758-L1760`) covers `call(I)I @80-@85`, which runs the closure's `luaMainloop`
    NESTED (`@155-@158 L162`). The whole dynamic extent looks protected -- so a raise from inside
    the called function, nil-call included, should be CAUGHT and returned as `false, <message>`.
  * `zombie/Lua/Event.trigger` calls each callback through `LuaCaller.protectedCallVoid`
    (`@89`, `@276`) with a per-iteration `catch (Throwable)` (`@194-@198 L41-L42`) and CONTINUES
    the loop (`@216-@219 L31`) -- so a raise in one handler should not stop the handlers behind
    it.

Bytecode is a reading of what the engine COULD do; a live probe is a reading of what it DOES. One
mod, one event, four handlers, both Lua states, three minutes.

**The probe** (`testing/experiments/TKX_PcallProbe`, a single `shared/` file so the server VM and
the client VM each run their own copy, giving two independent readings rather than one):

    H0  `TKX_P.before` ++            -- the event fires and the chain reaches this file
    H1  `pcall(TKX_DefinitelyNil)`   -- then ok/err are assigned and `tail` ++
    H2  `TKX_P.behind` ++            -- registered AFTER H1 on the SAME event
    H3  `pcall(error, "boom")`       -- the control: an ORDINARY error under pcall

Every field is a STRING. A `false` arriving through `lua.global` would be indistinguishable from a
walk that stopped, and `"unset"` vs `"false"` is the entire distinction H1 turns on: `"unset"` is
the value the table constructor put there, so it means *the assignment line never ran*.

**The three readings the run can produce, per side, stated before the run (P21):**

  (i)  `ok == "false"`, `err` a message naming the nil call, `tail >= 1`, `behind >= 1`
       => `pcall` CATCHES a Kahlua nil call. The standing rule is **WRONG**. The `tkxCall`
       guards stay as defensive practice (they also make intent explicit and cost nothing), but
       the doc has to rewrite the rule, and the H2 half of the question is then NOT answered by
       this run -- nothing raised past a pcall, so no handler behind one was ever tested.
  (ii) `ok == "unset"`, `err == "unset"`, `tail == "0"` => the raise ESCAPED `pcall` and aborted
       the handler body. The standing rule's first half holds. Its second half is then decided by
       `behind`: `>= 1` means the engine logged and CONTINUED (Event.trigger's per-callback
       catch, so "kills the whole handler" is right but "kills the chain" is wrong); `== 0` means
       the chain stopped, which is the doc's current sentence, whole.
  (iii) anything else -- recorded verbatim, graded against (i) like any other non-match.

`ctrl_ok == "false"` with `ctrl_err` containing `boom` is the CONTROL, and it is checked on each
side BEFORE that side's H1 reading is graded. It proves three things at once: `pcall` exists and
returns the two-value shape, the handler ran to completion, and the string fields survive the bus.
A side whose control does not hold reports `unmeasured`, whatever H1 says.

`before` is H0, registered FIRST, and it is the other control: if `before == "0"` the event never
fired on that side and NOTHING below it is a reading about pcall.

**Why the reads are strings and the waits are on a counter, not a clock.** `EveryOneMinute` at the
fixture's `DayLength 4` fires every 3.75 s real. The driver waits until the CLIENT's `before`
reaches 2 (poll every 2 s, cap 30 s) rather than sleeping a fixed time, so a slow boot lengthens
the wait instead of silently producing a zero reading.

Nothing here writes world state: no `additem`, no `nutrition.set`, no `moddata.set`, no
`item.set`, no `eat.action`, no `lua.reload`. There is nothing to restore.

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

PROFILE = "x12-pcall"
USER = "admin"
MODS = ("PZTestKit", "TKX_PcallProbe")
# Step 3's acceptance run: RESULT PASS, the single [[verify]] row ok=True with
# `{"type": "number", "resolved": true, "value": 1}`, 0 server errors, 0 faults, and
# `loading PZTestKit` / `loading TKX_PcallProbe` at server lines 93/94 and client lines 83/84 and
# again at 162/163 (the client runs TWO Lua states and prints engine load output once per state).
ACCEPTANCE_RUN = "run-20260911-044417"
ACCEPTANCE_LOADING_LINES = {"server": {"PZTestKit": 93, "TKX_PcallProbe": 94},
                            "client": {"PZTestKit": [83, 162], "TKX_PcallProbe": [84, 163]}}
# And the reading that sized the greps below: in that 5 s hold -- roughly 2-3 game minutes in
# world -- the server log and the client console carried ZERO hits for `TKX_DefinitelyNil`,
# `attempted to call`, `tried to call` and `ExceptionLogger`, and 6 / 8 hits for
# `TKX_PcallProbe` (the loader's two lines per state plus four `NoSuchFileException` paths for
# `media/AnimSets` and `media/actiongroups`, which every mod in this slice produces).
ACCEPTANCE_GREP_COUNTS = {"TKX_DefinitelyNil": {"server": 0, "client": 0},
                          "attempted to call": {"server": 0, "client": 0},
                          "tried to call": {"server": 0, "client": 0},
                          "ExceptionLogger": {"server": 0, "client": 0},
                          "TKX_PcallProbe": {"server": 6, "client": 8}}

# ---- timings -----------------------------------------------------------------------------------
DAY_LENGTH = 4           # the fixture's own (testing/fixtures/default/.../pzt_SandboxVars.lua:53)
GAME_MINUTE_S = 3.75     # DayLength 4 = a 90-minute game day: 5400 s / 1440 game minutes
WAIT_TARGET = 2          # `TKX_P.before` must reach this on the CLIENT before anything is read
WAIT_POLL_S = 2.0
WAIT_CAP_S = 30.0        # 8 game minutes' worth of headroom over the 7.5 s the target needs
SECOND_PASS_S = 12.0     # supplementary only -- see `second_pass` below

# ---- the eight readings, plus the two controls -------------------------------------------------
# Order is the order they are read in, and it is the order of the probe file: H0's counter first,
# then H1's three, then H2's, then H3's two. `side` leads because a reading whose side is "?" is
# a reading from a Lua state that never resolved which side it was on.
FIELDS = ("side", "before", "ok", "err", "tail", "behind", "ctrl_ok", "ctrl_err")
TABLE_GLOBAL = "TKX_P"
TABLE_KEYS_EXPECTED = 9   # side, before, ok, err, tail, behind, ctrl_ok, ctrl_err, version
CONTROL_GLOBAL = "TK.version"
# `TKX_P.version` is the profile's tier-(a) gate and is re-read here as the mod-side control:
# it is assigned in the table constructor on the file's first line, so a 1 says the file RAN,
# whatever the handlers did afterwards.
MOD_CONTROL_GLOBAL = "TKX_P.version"

# ---- what the strings are allowed to mean ------------------------------------------------------
UNSET = "unset"
# A message "naming the nil call" is not a fixed string -- Kahlua's own wording is what the run
# is there to record -- so the test is recorded as three separate booleans beside the verbatim
# text rather than as one regex that could quietly mis-grade a message nobody has seen yet.
NIL_RX = re.compile(r"\bnil\b", re.I)
CALL_RX = re.compile(r"call", re.I)
NAME_RX = re.compile(r"TKX_DefinitelyNil")
BOOM_RX = re.compile(r"boom")

# ---- greps -------------------------------------------------------------------------------------
# A limit is a BREAK, not a window: a result of exactly `limit` means SATURATION (amendment 6),
# and the saturation flag travels with every block. Client limits are >= 2x predicted because the
# client runs TWO Lua states and prints engine load output once per state. Predicted, from the
# acceptance run above: 8 client hits for `TKX_PcallProbe` and 0 for the four error patterns.
# The error patterns are OPEN reads -- outcome (ii) would print something on every fire, at one
# game minute per fire, for however long the session runs -- so they are sized for a traceback
# block per fire across a three-minute session rather than for the zero the acceptance run saw.
GREPS = (
    ("TKX_DefinitelyNil", re.compile(r"TKX_DefinitelyNil"), 80),
    ("attempted to call", re.compile(r"attempted to call", re.I), 80),
    ("tried to call", re.compile(r"tried to call", re.I), 80),
    ("ExceptionLogger", re.compile(r"ExceptionLogger"), 80),
    ("TKX_PcallProbe", re.compile(r"TKX_PcallProbe"), 120),
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_LUA_COMMIT_EXPECTED = "5d9633f"   # the brief's pin; the computed value is recorded beside

P21_PREDICTED = (
    "(i) pcall CATCHES the Kahlua nil call, on BOTH sides: TKX_P.ok == \"false\", TKX_P.err a "
    "message naming the nil call, TKX_P.tail >= 1 (the three lines after the pcall ran) and "
    "TKX_P.behind >= 1 (H2, registered behind H1 on the same event, also ran). That makes the "
    "library's standing rule -- 'a Kahlua nil call escapes pcall and kills the whole handler' -- "
    "WRONG on its first half, and leaves its second half UNTESTED by this run, because nothing "
    "raised past a pcall. The tkxCall/TK.call guards stay as defensive practice; the doc rewrites "
    "the rule. This is the jar's reading: KahluaThread.pcall's try covers the nested luaMainloop."
)
P21_FALSIFIER = (
    "(ii) ok == \"unset\" AND err == \"unset\" AND tail == \"0\" falsifies it: the raise escaped "
    "pcall and aborted the handler body, exactly as the standing rule says. `behind` then decides "
    "the SECOND half on its own -- behind >= 1 means Event.trigger logged and continued (the rule "
    "is right about the handler and wrong about the chain), behind == 0 means the chain died with "
    "the handler (the doc's current sentence stands whole). (iii) anything else is recorded "
    "verbatim and graded against (i) like any other non-match -- in particular ok == \"true\" "
    "would mean pcall returned SUCCESS on a nil call, which no reading of the jar predicts. "
    "A side whose H3 control fails (ctrl_ok != \"false\", or ctrl_err without `boom`), or whose "
    "H0 counter never left \"0\", is UNMEASURED and is not graded at all: the first says pcall "
    "itself did not behave on that side, the second says the event never fired there."
)

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x126")
path = os.path.join(run_dir, "platform-pcall.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
harness_lua_commit = git_say("log", "-1", "--format=%h", "--", LUA_DIR)
out = {
    "run_id": run_id,
    "session": "x126 -- slice 12 session 6: does a Kahlua nil call escape pcall, and does a "
               "raise kill the handlers behind it?",
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
    "acceptance_loading_lines": ACCEPTANCE_LOADING_LINES,
    "acceptance_grep_counts": ACCEPTANCE_GREP_COUNTS,
    "fixture_day_length": DAY_LENGTH,
    "game_minute_seconds": GAME_MINUTE_S,
    "why": "the standing rule (`Kahlua's 'tried to call nil' escapes pcall and kills the whole "
           "handler`) is the reason TK.call and every tkxCall guard exist, and it rests on "
           "exp01-20260909-235420, which has NO committed artifact. The Task 9 jar review reads "
           "the other way twice over: KahluaThread.pcall's try covers the nested luaMainloop, and "
           "Event.trigger calls each callback through LuaCaller.protectedCallVoid inside a "
           "per-iteration catch (Throwable) that continues the loop.",
    "probe": {
        "mod": "TKX_PcallProbe",
        "file": "testing/experiments/TKX_PcallProbe/42.20/media/lua/shared/TKX_PcallProbe.lua",
        "shared_why": "shared/ on purpose -- the server VM and the client VM each run their own "
                      "copy, so the session gets TWO independent readings of one question.",
        "handlers": {
            "H0": "TKX_P.before ++ -- the event fires and the chain reaches this file",
            "H1": "local ok, err = pcall(TKX_DefinitelyNil); then ok/err assigned and tail ++",
            "H2": "TKX_P.behind ++ -- registered AFTER H1 on the SAME event",
            "H3": "local ok, err = pcall(error, 'boom') -- the control",
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
        "lua_reload": "never sent -- re-running the probe file would reset TKX_P's counters and "
                      "re-register all four handlers on top of the live ones, which is not a "
                      "state any reading here should be taken in.",
    },
    "p21_predicted": P21_PREDICTED,
    "p21_falsifier": P21_FALSIFIER,
    "notes": [], "phases": {}, "verdicts": {},
}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


# The dormant `sent` branch's routing table, carried for shape parity with the sessions that use
# it. Every command in THIS driver (`lua.global` only) answers INLINE, so the branch never fires.
RESULT_DOC = {"witness.fields": "witness_fields", "witness.moddata": "witness_moddata"}


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). Every command used here answers INLINE, so it is
        DORMANT; a command absent from `RESULT_DOC` is recorded raw rather than blocked on.
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


# No `step()` helper here, and no `steps` list in `out`: x125 needed one because it sent
# SEQUENCED, state-touching commands (an RCON spawn, `item.get`, `items.count`) whose ordering
# against the world clock mattered. Every command in this driver is a read-only `lua.global`, and
# `probe()` already brackets each one with its own wall clock -- a second sequencing layer would
# record the same numbers twice under a different key.


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
    assumed: the fourth reply shape (`no _G on this build`) carries no `value` at all, and a
    `resolved: false` reply means THIS PATH did not resolve -- which for `TKX_P.ok` would be a
    finding about the table, not about pcall."""
    if not isinstance(reply, dict):
        return None
    if reply.get("resolved") is not True:
        return None
    return reply.get("value")


def as_int(v):
    """The string counters (`before`, `tail`, `behind`) as ints. They are STRINGS by design, so
    `num()` alone would answer None for every one of them; a value that is not a whole number in
    string form answers None rather than raising, and None is then read as 'not a counter'."""
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


def grep_numbered(path_, rx, limit):
    """`session.grep_file` with the LINE NUMBER kept: which lines arrived, and in what order, is
    the evidence here, and order is unreadable without the numbers."""
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:300]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def greps(c, when):
    """Every pattern over BOTH logs, with the saturation test written down rather than left to
    the reader: `limit` is a BREAK, so a result of exactly `limit` is saturation, never a census.

    The engine's own error line for H1 -- if it prints one -- IS a reading, which is why every
    hit keeps its line number and its verbatim text instead of being counted."""
    blocks = {}
    for name, rx, limit in GREPS:
        s = grep_numbered(server.log_path, rx, limit)
        k = grep_numbered(c.console, rx, limit)
        blocks[name] = {
            "pattern": rx.pattern, "limit": limit, "when": when,
            "server": {"count": len(s), "saturated": len(s) >= limit, "hits": s},
            "client": {"count": len(k), "saturated": len(k) >= limit, "hits": k},
            "acceptance_counts": ACCEPTANCE_GREP_COUNTS.get(name),
            "client_rule": "a client console runs TWO Lua states and prints engine load output "
                           "once per state, so a load-time count is expected at 2x the "
                           "server's; a RUNTIME error count is not, because only the in-session "
                           "state runs EveryOneMinute.",
        }
    return blocks


def read_side(side, side_name):
    """The eight fields, then the table's `keyCount`, then the two controls -- one `lua.global`
    each, every reply kept whole beside the value lifted out of it."""
    replies, values = {}, {}
    for f in FIELDS:
        r = probe(side, "lua.global", TABLE_GLOBAL + "." + f)
        replies[f] = r
        values[f] = sval(r)
    tbl = probe(side, "lua.global", TABLE_GLOBAL)
    mod_ctrl = probe(side, "lua.global", MOD_CONTROL_GLOBAL)
    harness_ctrl = probe(side, "lua.global", CONTROL_GLOBAL)
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
                        "why": "assigned in the table constructor on the file's first line, so a "
                               "1 says the file RAN whatever the handlers did afterwards."},
        "harness_control": {"global": CONTROL_GLOBAL, "reply": harness_ctrl,
                            "value": sval(harness_ctrl),
                            "why": "a resolved=false here means the _G walk itself is broken on "
                                   "this side and every reading above it is suspect -- it does "
                                   "NOT mean a mod global is absent."},
        "counters": {"before": as_int(values.get("before")),
                     "tail": as_int(values.get("tail")),
                     "behind": as_int(values.get("behind"))},
        "wall": wall(),
    }
    row["table"]["keyCount_ok"] = row["table"]["keyCount"] == TABLE_KEYS_EXPECTED
    return row


def classify(row):
    """Which of P21's branches this side's reading lands on, with every gate it had to pass named
    beside it. Nothing here re-reads: the branch is computed from the values already recorded."""
    v, ctr = row["values"], row["counters"]
    ok, err = v.get("ok"), v.get("err")
    ctrl_ok, ctrl_err = v.get("ctrl_ok"), v.get("ctrl_err")
    before, tail, behind = ctr["before"], ctr["tail"], ctr["behind"]

    readable = all(v.get(f) is not None for f in FIELDS) and \
        None not in (before, tail, behind)
    event_fired = bool(before is not None and before >= 1)
    control_ok = bool(isinstance(ctrl_ok, str) and ctrl_ok == "false"
                      and isinstance(ctrl_err, str) and BOOM_RX.search(ctrl_err))

    err_text = err if isinstance(err, str) else ""
    err_flags = {"verbatim": err,
                 "mentions_nil": bool(NIL_RX.search(err_text)),
                 "mentions_call": bool(CALL_RX.search(err_text)),
                 "names_the_global": bool(NAME_RX.search(err_text)),
                 "is_unset": err == UNSET}

    if not readable or not event_fired or not control_ok:
        branch = "unmeasured"
    elif ok == "false" and tail >= 1:
        branch = "i_pcall_catches"
    elif ok == UNSET and err == UNSET and tail == 0:
        branch = "ii_escapes_chain_continues" if behind >= 1 else "ii_escapes_chain_dies"
    else:
        branch = "iii_other"

    verdict = {"i_pcall_catches": "as_predicted", "unmeasured": "unmeasured"}.get(
        branch, "falsified")
    # (i) predicts `behind >= 1` too, but `behind` is NOT a gate on branch (i): under (i) nothing
    # raised past a pcall, so H2 tests nothing about raises and a low `behind` would be a fact
    # about the chain's timing, not about the rule. It is recorded, and flagged if it disagrees.
    means = {
        "i_pcall_catches":
            "pcall CAUGHT the Kahlua nil call on this side. The standing rule's FIRST half is "
            "wrong: `tried to call nil` does not escape pcall. Its SECOND half ('kills the whole "
            "handler') is UNTESTED by this run, because nothing raised past a pcall for a later "
            "handler to survive -- `behind` advancing here only says the chain ran normally.",
        "ii_escapes_chain_continues":
            "the raise ESCAPED pcall and aborted the handler body (ok/err never assigned, tail "
            "never advanced) -- but the handler registered BEHIND it still ran. The standing "
            "rule is right about pcall and about the handler, and WRONG about the chain: "
            "Event.trigger's per-callback catch (Throwable) logged and continued.",
        "ii_escapes_chain_dies":
            "the raise ESCAPED pcall, aborted the handler body AND stopped the chain -- the "
            "handler registered behind H1 never ran. The doc's current sentence stands whole.",
        "iii_other":
            "neither branch. Recorded verbatim; graded against (i) like any other non-match.",
        "unmeasured":
            "not graded. Either a field did not resolve, or H0's counter never left 0 (the event "
            "never fired on this side), or H3's control did not hold (pcall itself did not "
            "behave here) -- and an H1 reading taken under any of those says nothing about the "
            "rule.",
    }[branch]
    return {
        "branch": branch, "verdict": verdict, "means": means,
        "gates": {"readable": readable, "event_fired": event_fired,
                  "h3_control_ok": control_ok,
                  "h3_control": {"ctrl_ok": ctrl_ok, "ctrl_err": ctrl_err,
                                 "ctrl_ok_expected": "false",
                                 "ctrl_err_contains_boom": bool(
                                     isinstance(ctrl_err, str) and BOOM_RX.search(ctrl_err))},
                  "table_keyCount_ok": row["table"]["keyCount_ok"],
                  "mod_control_value": row["mod_control"]["value"],
                  "harness_control_value": row["harness_control"]["value"]},
        "readings": {"side_reported": v.get("side"), "ok": ok, "err": err_flags,
                     "before": before, "tail": tail, "behind": behind},
        "behind_note": ("behind advanced" if (behind or 0) >= 1 else
                        "behind did NOT advance -- under branch (i) that is a fact about the "
                        "chain, not about raises, and it disagrees with (i)'s stated shape"),
        "behind_agrees_with_prediction": bool((behind or 0) >= 1),
    }


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
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}
    mods_dir = os.path.join(server.cache, "mods")
    try:
        listing = sorted(os.listdir(mods_dir))
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        listing = [f"error: {type(e).__name__}: {e}"]
    out["mods_dir"] = {"path": os.path.relpath(mods_dir, REPO), "listing": listing,
                       "probe_folder_present": "TKX_PcallProbe" in listing}
    save(path, out, tl, server)

    # ================= the wait: a counter, not a clock =================================
    # `EveryOneMinute` at DayLength 4 fires every 3.75 s real, so `before` needs ~7.5 s to reach
    # 2 -- but the client has usually been in world for far longer than that by the time
    # `session_ready` lands, so the first poll normally answers straight away. A slow boot
    # lengthens the wait instead of silently producing a zero reading.
    polls, waited, target_met = [], 0.0, False
    t_wait0 = wall()
    while True:
        r = probe(c, "lua.global", TABLE_GLOBAL + ".before")
        n = as_int(sval(r))
        polls.append({"wall": wall(), "value": sval(r), "int": n,
                      "resolved": r.get("resolved") if isinstance(r, dict) else None})
        if n is not None and n >= WAIT_TARGET:
            target_met = True
            break
        waited = wall() - t_wait0
        if waited >= WAIT_CAP_S:
            break
        time.sleep(WAIT_POLL_S)
    out["wait"] = {
        "global": TABLE_GLOBAL + ".before", "side": "client", "target": WAIT_TARGET,
        "poll_every_s": WAIT_POLL_S, "cap_s": WAIT_CAP_S,
        "polls": polls, "target_met": target_met,
        "waited_s": round(wall() - t_wait0, 3),
        "why": "H0 is registered FIRST on the event, so `before` reaching 2 proves the event has "
               "fired at least twice AND that the chain reaches this file -- which is the only "
               "state in which H1's reading means anything.",
        "cadence": f"DayLength {DAY_LENGTH} -> {GAME_MINUTE_S} s per game minute",
    }
    if not target_met:
        note("TKX_P.before never reached 2 on the client inside the 30 s cap -- every reading "
             "below is UNMEASURED for the client side by construction, and the server side is "
             "graded on its own H0 counter.")
    tl.mark("wait_done", target_met=str(target_met))
    save(path, out, tl, server)

    # ================= the reads: CLIENT FIRST, then the server ========================
    # Client first, always: the read ORDER is what fixes the sign of any cross-side comparison,
    # and these two Lua states are running the same file independently.
    reads = {"client": read_side(c, "client")}
    tl.mark("read_client")
    reads["server"] = read_side(server, "server")
    tl.mark("read_server")
    out["phases"]["reads"] = {
        "question": "does a Kahlua nil call escape pcall, and does a raise in one handler kill "
                    "the handlers registered behind it?",
        "order": "client first, then server",
        "fields": list(FIELDS),
        "client": reads["client"], "server": reads["server"],
    }
    save(path, out, tl, server)

    # ================= the log, read at the same moment as the values ==================
    out["greps"] = greps(c, "after the graded reads")
    save(path, out, tl, server)

    # ================= P21, graded per side ============================================
    cls = {s: classify(reads[s]) for s in ("client", "server")}
    out["phases"]["classification"] = cls
    for side_name in ("client", "server"):
        k = cls[side_name]
        grade(
            "P21_" + side_name,
            P21_PREDICTED,
            {"side": side_name,
             "side_reported_by_probe": reads[side_name]["values"].get("side"),
             "values": reads[side_name]["values"],
             "counters": reads[side_name]["counters"],
             "branch": k["branch"],
             "means": k["means"],
             "gates": k["gates"],
             "err": k["readings"]["err"],
             "behind_note": k["behind_note"],
             "table_keyCount": reads[side_name]["table"]["keyCount"],
             "engine_log": {
                 name: {"server": out["greps"][name]["server"]["count"],
                        "client": out["greps"][name]["client"]["count"]}
                 for name, _, _ in GREPS},
             },
            k["verdict"],
            P21_FALSIFIER,
            {"branch": k["branch"], "behind_agrees_with_prediction":
                k["behind_agrees_with_prediction"]})

    # ================= supplementary: do the counters keep advancing? ==================
    # NOT part of P21's grading -- P21 is graded on the reads above and nothing here can change
    # it. It is here because a single snapshot cannot tell a counter that advances once from a
    # counter that advances every fire, and "tail advanced by as many as before did" is the
    # cheapest possible corroboration of whichever branch the snapshot landed on.
    time.sleep(SECOND_PASS_S)
    second = {"client": read_side(c, "client"), "server": read_side(server, "server")}
    deltas = {}
    for side_name in ("client", "server"):
        a, b = reads[side_name]["counters"], second[side_name]["counters"]
        deltas[side_name] = {k2: (None if (a[k2] is None or b[k2] is None) else b[k2] - a[k2])
                             for k2 in ("before", "tail", "behind")}
        deltas[side_name]["branch_first_pass"] = cls[side_name]["branch"]
        deltas[side_name]["branch_second_pass"] = classify(second[side_name])["branch"]
        deltas[side_name]["branches_agree"] = \
            deltas[side_name]["branch_first_pass"] == deltas[side_name]["branch_second_pass"]
    out["second_pass"] = {
        "gap_s": SECOND_PASS_S,
        "game_minutes_in_gap": round(SECOND_PASS_S / GAME_MINUTE_S, 2),
        "why": "supplementary corroboration, never a graded reading: a single snapshot cannot "
               "separate a counter that advanced once from one that advances every fire. A "
               "branch that DISAGREES between the two passes is itself the finding and is "
               "flagged here rather than averaged away.",
        "reads": second, "deltas": deltas,
    }
    for side_name in ("client", "server"):
        if not deltas[side_name]["branches_agree"]:
            note(f"{side_name}: the P21 branch CHANGED between the graded read and the "
                 f"supplementary read ({deltas[side_name]['branch_first_pass']} -> "
                 f"{deltas[side_name]['branch_second_pass']}). The graded verdict stands on the "
                 "first pass, as the brief specifies; this disagreement is the finding.")
    save(path, out, tl, server)

    # The final log read: everything the engine printed across the whole session, including
    # whatever the second pass's extra game minutes produced.
    out["greps_final"] = greps(c, "end of session, after the supplementary read")

    # ================= the readings, stated as a summary ==============================
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "wait_target_met": out["wait"]["target_met"],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "branch": {s: cls[s]["branch"] for s in ("client", "server")},
        "sides_agree": cls["client"]["branch"] == cls["server"]["branch"],
        "values": {s: reads[s]["values"] for s in ("client", "server")},
        "counters": {s: reads[s]["counters"] for s in ("client", "server")},
        "table_keyCount": {s: reads[s]["table"]["keyCount"] for s in ("client", "server")},
        "mod_control": {s: reads[s]["mod_control"]["value"] for s in ("client", "server")},
        "harness_control": {s: reads[s]["harness_control"]["value"]
                            for s in ("client", "server")},
        "second_pass_deltas": deltas,
        "grep_counts": {name: {"server": out["greps_final"][name]["server"]["count"],
                               "client": out["greps_final"][name]["client"]["count"],
                               "saturated": [s for s in ("server", "client")
                                             if out["greps_final"][name][s]["saturated"]]}
                        for name, _, _ in GREPS},
        "means": {s: cls[s]["means"] for s in ("client", "server")},
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
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-pcall.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
