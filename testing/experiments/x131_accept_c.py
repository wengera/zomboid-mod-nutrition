"""x131d -- the Plan 1 acceptance run C: the smoke test of the fix-wave commit 9a424d8.

Copied byte-for-byte from `x131_accept_b.py` (run x131b-20261004-175911, frozen) and changed only
where Plan 1 Task 10c says: the artifact name, SESSION, ACCEPTANCE_RUN, the run-id prefix
(`x131d`) and a new P1.9. Every phase of the b driver is kept. 9a424d8 makes the takeover handler
look its hoisted handles up in a Lua table keyed by the character object
(`NutritionRevamp.server.fast.byChar`) and fall back to the guarded username lookup only on a
miss; whether a Kahlua table keyed by an `IsoPlayer` returns the stored entry is read here, live.
Prediction and falsifier for the new phase, written before the run:

  P1.9  server `lua.global NutritionRevamp.server.fast.stats.byCharHits` and `...stats.calls`,
        read in the SANDWICH order hits_a, calls_a, (~10 s wall), calls_b, hits_b, so the hits
        window strictly contains the calls window: with no miss in between, dHits >= dCalls by
        construction. Prediction: byCharHits rises by the same count as calls minus at most one
        (the first-sight tick), i.e. dHits >= dCalls - 1; `failures` 0 and `disabledAt` nil (an
        unresolved walk) at both ends. Falsifier: byCharHits stays at 0 while calls rises (the
        keying misses every tick and the slow path runs -- a reading about Kahlua keying, not a
        defect of the run), or dHits < dCalls - 1 (some ticks miss), or a failure, or disabledAt
        set. Recorded beside it, not graded: calls - byCharHits at each end (the misses since
        boot, up to the read-gap ticks).

The b driver's docstring follows unchanged.

x131b -- the Plan 1 acceptance RE-RUN, after the store fix at 65d1e8d.

Copied byte-for-byte from `x131_accept.py` (run x131-20261004-175014, frozen) and changed only
where Plan 1 Task 10b says: the artifact name, SESSION, ACCEPTANCE_RUN, the trace regex (this
build prints a mod frame as `Lua((MOD:Nutrition Revamp)).call(NR_Core.lua:37)`, limit 40), P1.5
(the mirror's username / v / mode read field by field) and a new P1.8 (the store record and the
slow clock). Predictions and falsifiers for the changed and new phases, written before the run:

  P1.5  client `NutritionRevamp.client.received` >= 1, and `client.mirror.username` == "admin",
        `client.mirror.v` == 1, `client.mirror.mode` == 1. Falsifier: received 0 or unresolved,
        or any of the three fields unresolved or another value.
  P1.7  as before, and now the trace half can match: no frame line naming the mod on either side.
        Falsifier: any such line (the first run's fault would show here as ten fires).
  P1.8  server `NutritionRevamp.server.store.records.admin.v` resolved 1 (the store attached on
        OnInitGlobalModData and holds the record), and `NutritionRevamp.server.players.minutes`
        rising between two reads ~10 s wall apart (~150 game-s, so ~2 game minutes; the slow
        clock is ticking). Falsifier: the record unresolved or v not 1; the minute count flat.

The first driver's docstring follows unchanged.

x131 -- the Plan 1 acceptance run: the first live boot of NutritionRevamp under the harness.

Copied from `_template.py` (Plan 1 Task 10). One phase, P1, after `session_ready`, on the
`nr-accept` profile (PZTestKit + NutritionRevamp on the golden fixture, no sandbox override, so
the mod's Mode option is its default 1 = takeover). Its readings, each wall-bracketed:

  P1.1  `lua.global NutritionRevamp.version`, client then server -- the controls (the mod's
        files ran in both Lua states).
  P1.2  server `lua.global NutritionRevamp.server.fast.registered` (predict true) and
        `...fast.stats.failures` (predict 0).
  P1.3  server `stats.all admin` twice ~10 s apart, a `time.snapshot` beside each: hunger and
        thirst rise. Thirst prediction: +8.0e-6 per game-second elapsed (#0476), the elapsed
        read off the two `stats.all` worldAge values (same tick as the stats); falsifier: no
        change, or a change outside +-10 % of the prediction. Hunger is graded on its
        direction (falsifier: no rise); its ratio to 9.6e-6 x (1 - h) per game-second (#0470)
        is recorded, not graded. `field_count`: 24 stats and `missing` empty on each read.
  P1.4  server `lua.global NutritionRevamp.server.fast.stats.calls` twice ~10 s apart: rises.
  P1.5  client `lua.global NutritionRevamp.client.received`: >= 1 (the mirror arrived).
  P1.6  server `bench.global NutritionRevamp.kernel.fast.defaults 1000`: a first cost reading,
        recorded, not graded.
  P1.7  the server log and client console grepped for `[NutritionRevamp]` lines (limit 20, a
        BREAK not a window): exactly one server self-report `side=server mode=takeover log=2
        frameworks=none hook=true`, one `fast: takeover handler registered`, one client
        self-report `side=client`; and a Lua-trace grep for anything naming an `NR_` file.

What follows is the template's own docstring, kept as the house shape this driver obeys.

The driver template -- copy it, do not run it as it stands.

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

PROFILE = "nr-accept"
SESSION = ("Plan 1 acceptance run C, the smoke test of the fix-wave commit 9a424d8: the takeover "
           "handler finds its hoisted handles in fast.byChar, a Lua table keyed by the IsoPlayer, "
           "and every b-run phase still holds")
ARTIFACT = "accept-c.json"
USER = "admin"
# The acceptance run (`python testing/pzt run --profile <name>`) that smoke-tested the harness
# for this session: RESULT, its [[verify]] rows, its server error count and its client Lua error
# count are what say the bus was answering before any of the readings below were taken.
ACCEPTANCE_RUN = "x131b-20261004-175911"

# ---- P1 constants -------------------------------------------------------------------------
STAT_FIELD_COUNT = 24                 # TK.STAT_REGISTRY rows (character-stats.md#registry)
THIRST_PER_GAME_SECOND = 8.0e-6       # #0476: awake thirst, no damping term
HUNGER_PER_GAME_SECOND = 9.6e-6       # #0470: awake idle hunger, times (1 - hunger)
THIRST_BAND = 0.10                    # +-10 % of the prediction
WINDOW_S = 10.0                       # the requested wall window between paired reads
BENCH_N = 1000
# A limit is a BREAK, not a window: 20 is well over 2x the three lines predicted per side.
NR_RX = re.compile(re.escape("[NutritionRevamp]"))
SELF_REPORT_SERVER_RX = re.compile(r"NutritionRevamp v\S+ build \S+ side=server ")
SELF_REPORT_CLIENT_RX = re.compile(r"NutritionRevamp v\S+ build \S+ side=client ")
REGISTERED_RX = re.compile(re.escape("fast: takeover handler registered"))
# This build prints a mod stack frame as `Lua((MOD:Nutrition Revamp)).call(NR_Core.lua:37)` (the
# display name, with a space; run x131-20261004-175014's server log, lines 2001-2004). The trace
# regex matches that shape for this mod's display name, or any mod's frame naming an NR_ file.
# Checked against the first run's log before this run: 154 hits there.
TRACE_RX = re.compile(r"Lua\(\(MOD:Nutrition ?Revamp\)\)|Lua\(\(MOD:[^)]*\)\)\.\w+\((?:NR_|NutritionRevamp)")
LOG_LIMIT = 20
TRACE_LIMIT = 40                      # a BREAK, not a window
MINUTES_WINDOW_S = 10.0               # P1.8: the wall window between the two players.minutes reads
BYCHAR_WINDOW_S = 10.0                # P1.9: the wall window between calls_a and calls_b

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


def grep_numbered(path_, rx, limit=LOG_LIMIT):
    """`session.grep_file` with the LINE NUMBER kept (td3's helper): which lines arrived and in
    what order. `limit` is a BREAK, not a window: the scan stops at the limit-th hit."""
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:240]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


prof = profile.load(PROFILE)
# The fixture RECORD is gated too: `fixture.load` raises SystemExit when the fixture has no
# `cache/server` blob on this machine (fixture.py:65-67), and `testing/fixtures/*/cache/` is
# gitignored -- so an ungated read here would make the dry run, and its test, fail on a fresh
# clone. `rec` is consumed only inside the session below, which never runs under DRY_RUN.
rec = None if DRY_RUN else fx.load(prof.fixture)
# No run dir either: a dry run that boots nothing has nothing to write, and `new_run_dir` would
# leave an empty `testing/runs/template-<ts>/` behind on every test run. Both are used only
# after the dry-run branch has printed and exited.
run_id, run_dir = ("x131d-dry-run", None) if DRY_RUN else new_run_dir("x131d")
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

    # ================= P1 -- the acceptance readings =========================================
    # Every read goes through `step` (its own wall bracket); every verdict through `grade`, with
    # the prediction and the falsifier written beside the reading. Client first at the one
    # paired tag (the version controls).
    P1 = out["phases"]["P1"] = {
        "question": "does NutritionRevamp load in both Lua states, register its takeover handler "
                    "at OnServerStarted, and do hunger and thirst advance under that handler?",
    }

    def gv(r):
        """The `value` of a lua.global ack, or None (an unresolved walk, a table, an error)."""
        return r.get("value") if isinstance(r, dict) else None

    def answered(r):
        """A lua.global ack that came back as a walk result (resolved true OR false)."""
        return isinstance(r, dict) and "resolved" in r

    # ---- P1.1 the controls: the mod's version global on both sides, client first ----------
    r_vc = step("p1_1_version_client", c, "lua.global", "NutritionRevamp.version")
    r_vs = step("p1_1_version_server", server, "lua.global", "NutritionRevamp.version")
    vers = {"client": gv(r_vc["ack"]), "server": gv(r_vs["ack"])}
    P1["versions"] = vers
    if not answered(r_vc["ack"]) and not answered(r_vs["ack"]):
        v11 = "unmeasured"
    elif vers["client"] == "0.1.0" and vers["server"] == "0.1.0":
        v11 = "as_predicted"
    else:
        v11 = "falsified"
    grade("P1.1", predicted="NutritionRevamp.version == '0.1.0' on the client and on the server",
          observed=vers, verdict=v11,
          falsifier="either side unresolved or another value: the mod's shared files did not run there")

    # ---- P1.2 the takeover registered, no failures, the hoist complete ----------------------
    r_reg = step("p1_2_registered", server, "lua.global", "NutritionRevamp.server.fast.registered")
    r_f0 = step("p1_2_failures", server, "lua.global", "NutritionRevamp.server.fast.stats.failures")
    r_dis = step("p1_2_disabledAt", server, "lua.global", "NutritionRevamp.server.fast.stats.disabledAt")
    r_mis = step("p1_2_hoist_missing", server, "lua.global",
                 f"NutritionRevamp.server.fast.h.{USER}.missing")
    reg, f0 = gv(r_reg["ack"]), gv(r_f0["ack"])
    mis_ack = r_mis["ack"]
    mis_count = mis_ack.get("keyCount") if isinstance(mis_ack, dict) else None
    P1["takeover"] = {"registered": reg, "failures": f0,
                      "disabledAt": r_dis["ack"], "hoistMissing": mis_ack}
    if not answered(r_reg["ack"]) and not answered(r_f0["ack"]):
        v12 = "unmeasured"
    elif reg is True and f0 == 0:
        v12 = "as_predicted"
    else:
        v12 = "falsified"
    grade("P1.2", predicted="fast.registered == true (Mode default 1 = takeover) and "
                            "fast.stats.failures == 0",
          observed={"registered": reg, "failures": f0}, verdict=v12,
          falsifier="registered false or unresolved, or a failure count above zero")
    if not answered(mis_ack):
        v12b = "unmeasured"
    elif mis_ack.get("resolved") is True and mis_count == 0:
        v12b = "as_predicted"
    else:
        v12b = "falsified"
    grade("P1.2b", predicted=f"the hoist of {USER} exists and its missing-member list is empty "
                             "(keyCount 0)",
          observed={"hoistMissing": mis_ack, "disabledAt": r_dis["ack"]}, verdict=v12b,
          falsifier="no hoist for the player (resolved false), or a missing member listed")

    # ---- P1.3 / P1.4 the stats and the call count, two reads WINDOW_S apart -----------------
    def snap(tag):
        ts = step(f"p1_3_time_{tag}", server, "time.snapshot", "")
        st = step(f"p1_3_stats_{tag}", server, "stats.all", USER)
        ca = step(f"p1_4_calls_{tag}", server, "lua.global", "NutritionRevamp.server.fast.stats.calls")
        return ts, st, ca

    ts_a, st_a, ca_a = snap("a")
    target = st_a["wall_before"] + WINDOW_S
    while wall() < target:
        time.sleep(0.25)
    ts_b, st_b, ca_b = snap("b")
    fail_end = step("p1_4_failures_end", server, "lua.global",
                    "NutritionRevamp.server.fast.stats.failures")

    def stats_of(r):
        a = r["ack"]
        return a if isinstance(a, dict) and isinstance(a.get("stats"), dict) else None

    sa, sb = stats_of(st_a), stats_of(st_b)
    fc = {}
    for tag, s in (("a", sa), ("b", sb)):
        if s is None:
            fc[tag] = {"ok": False, "count": None, "missing": None}
        else:
            fc[tag] = {"ok": len(s["stats"]) == STAT_FIELD_COUNT and not s.get("missing"),
                       "count": len(s["stats"]), "missing": s.get("missing")}
    P1["field_count"] = {"expected": STAT_FIELD_COUNT, "reads": fc}

    move = {"window_requested_s": WINDOW_S,
            "window_measured_s": round(st_b["wall_before"] - st_a["wall_before"], 3),
            "time_snapshots": {"a": ts_a["ack"], "b": ts_b["ack"]}}
    if sa is not None and sb is not None and num(sa.get("worldAge")) is not None \
            and num(sb.get("worldAge")) is not None:
        gsec = (sb["worldAge"] - sa["worldAge"]) * 3600.0
        move["worldAge"] = {"a": sa["worldAge"], "b": sb["worldAge"]}
        move["gameSeconds"] = gsec
        move["mult"] = {"a": sa.get("mult"), "b": sb.get("mult")}
        th_a, th_b = num(sa["stats"].get("Thirst")), num(sb["stats"].get("Thirst"))
        hu_a, hu_b = num(sa["stats"].get("Hunger")), num(sb["stats"].get("Hunger"))
        if th_a is not None and th_b is not None:
            pred = THIRST_PER_GAME_SECOND * gsec
            move["thirst"] = {"a": th_a, "b": th_b, "delta": th_b - th_a, "predicted": pred,
                              "ratio": (th_b - th_a) / pred if pred else None}
        if hu_a is not None and hu_b is not None:
            pred_h = HUNGER_PER_GAME_SECOND * (1.0 - (hu_a + hu_b) / 2.0) * gsec
            move["hunger"] = {"a": hu_a, "b": hu_b, "delta": hu_b - hu_a,
                              "predicted_ungraded": pred_h,
                              "ratio_ungraded": (hu_b - hu_a) / pred_h if pred_h else None}
    P1["statsMove"] = move

    t = move.get("thirst")
    if t is None or not move.get("gameSeconds"):
        v13t = "unmeasured"
    elif t["a"] >= 1.0 or t["b"] >= 1.0:
        v13t = "trivial"           # clamped at the ceiling: the arm was not exercised
    elif t["delta"] > 0 and abs(t["ratio"] - 1.0) <= THIRST_BAND:
        v13t = "as_predicted"
    else:
        v13t = "falsified"
    grade("P1.3-thirst", predicted="thirst rises by 8.0e-6 x game-seconds elapsed (#0476), the "
                                   "elapsed read off the two stats.all worldAge values",
          observed=t, verdict=v13t,
          falsifier="no change, or a change outside +-10 % of the prediction")
    h = move.get("hunger")
    if h is None or not move.get("gameSeconds"):
        v13h = "unmeasured"
    elif h["a"] >= 1.0:
        v13h = "trivial"
    elif h["delta"] > 0:
        v13h = "as_predicted"
    else:
        v13h = "falsified"
    grade("P1.3-hunger", predicted="hunger rises between the two reads (direction graded; the "
                                   "ratio to 9.6e-6 x (1 - h) per game-second is recorded only)",
          observed=h, verdict=v13h, falsifier="no rise")
    v13f = "as_predicted" if fc["a"]["ok"] and fc["b"]["ok"] else (
        "unmeasured" if sa is None and sb is None else "falsified")
    grade("P1.3-field_count", predicted=f"{STAT_FIELD_COUNT} stats and an empty missing list on "
                                        "each stats.all", observed=fc, verdict=v13f,
          falsifier="a read with another count or a non-empty missing list")

    c_a, c_b = num(gv(ca_a["ack"])), num(gv(ca_b["ack"]))
    f_end = gv(fail_end["ack"])
    calls = {"a": c_a, "b": c_b, "failures_end": f_end,
             "window_measured_s": round(ca_b["wall_before"] - ca_a["wall_before"], 3)}
    if c_a is not None and c_b is not None:
        calls["delta"] = c_b - c_a
        w = calls["window_measured_s"]
        calls["per_wall_second"] = (c_b - c_a) / w if w else None
    P1["calls"] = calls
    if c_a is None or c_b is None:
        v14 = "unmeasured"
    elif c_b > c_a and f_end == 0:
        v14 = "as_predicted"
    else:
        v14 = "falsified"
    grade("P1.4", predicted="fast.stats.calls rises between two reads ~10 s apart and "
                            "failures still reads 0 after them",
          observed=calls, verdict=v14,
          falsifier="the count does not rise (the handler is not being called), or a failure")

    # ---- P1.5 the mirror arrived at the client --------------------------------------------
    r_rc = step("p1_5_received_client", c, "lua.global", "NutritionRevamp.client.received")
    r_mc = step("p1_5_mirror_client", c, "lua.global", "NutritionRevamp.client.mirror")
    r_mu = step("p1_5_mirror_username", c, "lua.global", "NutritionRevamp.client.mirror.username")
    r_mv = step("p1_5_mirror_v", c, "lua.global", "NutritionRevamp.client.mirror.v")
    r_mm = step("p1_5_mirror_mode", c, "lua.global", "NutritionRevamp.client.mirror.mode")
    rec_n = num(gv(r_rc["ack"]))
    m_user, m_v, m_mode = gv(r_mu["ack"]), num(gv(r_mv["ack"])), num(gv(r_mm["ack"]))
    P1["mirror"] = {"received": r_rc["ack"], "mirror": r_mc["ack"],
                    "fields": {"username": r_mu["ack"], "v": r_mv["ack"], "mode": r_mm["ack"]}}
    if not answered(r_rc["ack"]):
        v15 = "unmeasured"
    elif (rec_n is not None and rec_n >= 1 and m_user == USER and m_v == 1 and m_mode == 1):
        v15 = "as_predicted"
    else:
        v15 = "falsified"
    grade("P1.5", predicted="NutritionRevamp.client.received >= 1 (the mirror arrived at first "
                            "sight) and client.mirror resolved with username '" + USER + "', "
                            "v 1, mode 1",
          observed={"received": rec_n, "mirror": r_mc["ack"],
                    "username": m_user, "v": m_v, "mode": m_mode},
          verdict=v15, falsifier="received 0 or unresolved, or a mirror field unresolved or "
                                 "another value: no (or a wrong) mirror reached the client")

    # ---- P1.6 a first cost reading of one kernel function ----------------------------------
    r_b = step("p1_6_bench_server", server, "bench.global",
               f"NutritionRevamp.kernel.fast.defaults {BENCH_N}")
    P1["bench"] = r_b["ack"]
    b = r_b["ack"]
    if not isinstance(b, dict):
        v16 = "unmeasured"
    elif "usPerCall" in b and "error" not in b:
        v16 = "as_predicted"
    else:
        v16 = "falsified"
    grade("P1.6", predicted=f"bench.global answers usPerCall for {BENCH_N} calls with no error "
                            "(the number itself is recorded, not graded)",
          observed=b, verdict=v16, falsifier="an error reply or a raise inside the loop")

    # ---- P1.8 the store attached and holds the record; the slow clock ticks -------------------
    # (Graded here, before the P1.7 log grep, so the grep covers every read the run made.)
    r_sv = step("p1_8_store_record_v", server, "lua.global",
                f"NutritionRevamp.server.store.records.{USER}.v")
    r_sr = step("p1_8_store_records", server, "lua.global", "NutritionRevamp.server.store.records")
    r_pa = step("p1_8_minutes_a", server, "lua.global", "NutritionRevamp.server.players.minutes")
    target = r_pa["wall_before"] + MINUTES_WINDOW_S
    while wall() < target:
        time.sleep(0.25)
    r_pb = step("p1_8_minutes_b", server, "lua.global", "NutritionRevamp.server.players.minutes")
    s_v = num(gv(r_sv["ack"]))
    mn_a, mn_b = num(gv(r_pa["ack"])), num(gv(r_pb["ack"]))
    P1["store"] = {"record_v": r_sv["ack"], "records": r_sr["ack"],
                   "minutes": {"a": mn_a, "b": mn_b,
                               "window_requested_s": MINUTES_WINDOW_S,
                               "window_measured_s": round(r_pb["wall_before"] - r_pa["wall_before"], 3),
                               "serverWorldAge": {"a": r_pa.get("serverWorldAge"),
                                                  "b": r_pb.get("serverWorldAge")}}}
    if not answered(r_sv["ack"]) and mn_a is None and mn_b is None:
        v18 = "unmeasured"
    elif (answered(r_sv["ack"]) and r_sv["ack"].get("resolved") is True and s_v == 1
          and mn_a is not None
          and mn_b is not None and mn_b > mn_a):
        v18 = "as_predicted"
    else:
        v18 = "falsified"
    grade("P1.8", predicted="server.store.records." + USER + ".v resolves to 1 (the store attached "
                            "on OnInitGlobalModData and holds the record) and "
                            "server.players.minutes rises between two reads ~10 s wall apart",
          observed={"record_v": s_v, "record_v_ack": r_sv["ack"], "minutes": P1["store"]["minutes"]},
          verdict=v18, falsifier="the record unresolved or v not 1, or the minute count flat")

    # ---- P1.9 the character-keyed lookup hits (9a424d8) -------------------------------------
    # Sandwich order: hits_a, calls_a, wait, calls_b, hits_b -- the hits window contains the calls
    # window, so with no miss dHits >= dCalls by construction. (Before the P1.7 log grep.)
    FS = "NutritionRevamp.server.fast.stats."
    r_ha = step("p1_9_byCharHits_a", server, "lua.global", FS + "byCharHits")
    r_ca = step("p1_9_calls_a", server, "lua.global", FS + "calls")
    r_fa = step("p1_9_failures_a", server, "lua.global", FS + "failures")
    r_da = step("p1_9_disabledAt_a", server, "lua.global", FS + "disabledAt")
    target = r_ca["wall_before"] + BYCHAR_WINDOW_S
    while wall() < target:
        time.sleep(0.25)
    r_cb = step("p1_9_calls_b", server, "lua.global", FS + "calls")
    r_hb = step("p1_9_byCharHits_b", server, "lua.global", FS + "byCharHits")
    r_fb = step("p1_9_failures_b", server, "lua.global", FS + "failures")
    r_db = step("p1_9_disabledAt_b", server, "lua.global", FS + "disabledAt")
    h_a, h_b = num(gv(r_ha["ack"])), num(gv(r_hb["ack"]))
    k_a, k_b = num(gv(r_ca["ack"])), num(gv(r_cb["ack"]))
    fl_a, fl_b = gv(r_fa["ack"]), gv(r_fb["ack"])

    def unset(r):
        a = r["ack"]
        return answered(a) and a.get("resolved") is not True

    bc = {"order": "hits_a, calls_a, wait, calls_b, hits_b",
          "byCharHits": {"a": h_a, "b": h_b}, "calls": {"a": k_a, "b": k_b},
          "failures": {"a": fl_a, "b": fl_b},
          "disabledAt": {"a": r_da["ack"], "b": r_db["ack"]},
          "window_requested_s": BYCHAR_WINDOW_S,
          "calls_window_measured_s": round(r_cb["wall_before"] - r_ca["wall_before"], 3),
          "hits_window_measured_s": round(r_hb["wall_before"] - r_ha["wall_before"], 3)}
    if None not in (h_a, h_b, k_a, k_b):
        bc["dHits"], bc["dCalls"] = h_b - h_a, k_b - k_a
        bc["dHits_minus_dCalls"] = (h_b - h_a) - (k_b - k_a)
        bc["calls_minus_hits"] = {"a": k_a - h_a, "b": k_b - h_b}
    P1["byChar"] = bc
    if None in (h_a, h_b, k_a, k_b):
        v19 = "unmeasured"
    elif k_b <= k_a:
        v19 = "trivial"
    elif (h_b - h_a) >= (k_b - k_a) - 1 and fl_a == 0 and fl_b == 0 and unset(r_da) and unset(r_db):
        v19 = "as_predicted"
    else:
        v19 = "falsified"
    grade("P1.9", predicted="fast.stats.byCharHits rises by the same count as fast.stats.calls "
                            "minus at most one (dHits >= dCalls - 1 under the sandwich order); "
                            "failures 0 and disabledAt unresolved (nil) at both ends",
          observed=bc, verdict=v19,
          falsifier="byCharHits stays at 0 while calls rises (the IsoPlayer key misses every tick "
                    "and the slow path runs), dHits < dCalls - 1, a failure, or disabledAt set")

    # ---- P1.7 the logs: the self-reports, the registration line, any Lua trace -------------
    srv_nr = grep_numbered(server.log_path, NR_RX, LOG_LIMIT)
    cli_nr = grep_numbered(c.console, NR_RX, LOG_LIMIT)
    srv_tr = grep_numbered(server.log_path, TRACE_RX, TRACE_LIMIT)
    cli_tr = grep_numbered(c.console, TRACE_RX, TRACE_LIMIT)

    def texts(hits, rx):
        return [x["text"] for x in hits if "text" in x and rx.search(x["text"])]

    sr_srv = texts(srv_nr, SELF_REPORT_SERVER_RX)
    sr_cli = texts(cli_nr, SELF_REPORT_CLIENT_RX)
    regl = texts(srv_nr, REGISTERED_RX)
    P1["logs"] = {"limit": LOG_LIMIT, "trace_limit": TRACE_LIMIT,
                  "server_nr_lines": srv_nr, "client_nr_lines": cli_nr,
                  "server_trace_lines": srv_tr, "client_trace_lines": cli_tr,
                  "self_report_server": sr_srv, "self_report_client": sr_cli,
                  "registered_lines": regl,
                  "server_log": os.path.relpath(server.log_path, run_dir),
                  "client_console": os.path.relpath(c.console, run_dir)}
    want = "mode=takeover log=2 frameworks=none hook=true"
    if not srv_nr and not cli_nr:
        v17 = "unmeasured"
    elif (len(sr_srv) == 1 and want in sr_srv[0] and len(regl) == 1 and len(sr_cli) == 1
          and not srv_tr and not cli_tr):
        v17 = "as_predicted"
    else:
        v17 = "falsified"
    grade("P1.7", predicted="exactly one server self-report carrying '" + want + "', exactly one "
                            "'fast: takeover handler registered', exactly one client self-report, "
                            "and no Lua stack-frame line of this mod (or naming an NR_ file) on "
                            "either side",
          observed={"self_report_server": sr_srv, "registered_lines": regl,
                    "self_report_client": sr_cli,
                    "trace_lines": {"server": srv_tr, "client": cli_tr}},
          verdict=v17,
          falsifier="a missing or doubled line, another mode / hook value, or any trace line")

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "statsMove": out["phases"]["P1"].get("statsMove"),
        "calls": out["phases"]["P1"].get("calls"),
        "byChar": out["phases"]["P1"].get("byChar"),
        "bench_usPerCall": (out["phases"]["P1"].get("bench") or {}).get("usPerCall")
        if isinstance(out["phases"]["P1"].get("bench"), dict) else None,
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
