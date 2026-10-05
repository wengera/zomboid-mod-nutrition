"""x132-cost -- the Plan 2 entry gate: the design's § 6 cost budget.

The budget: the takeover handler costs no more per player per tick than the seven vanilla
updaters it replaces. This driver reads it two ways in ONE live session of TWO serial boots of
the same golden fixture.

The run id prefix is `x132c` (run id `x132c-<date>-<time>`): the register's run-id pattern (a
lowercase alphanumeric prefix, then eight and six digits) refuses a hyphen in the prefix.

Copied from `_template.py` (house shape). Phases:

  P1  takeover boot, server `bench.global NutritionRevamp.bench_fast 100000`: the per-call wall
      cost (`usPerCall`) of one WHOLE fast-kernel step through the mod's entry point
      `NutritionRevamp.bench_fast` (committed c3ef044 / 61052e4; Task 2). This is the headline.
      `bench_fast` fills ONE representative STEADY-STATE AWAKE tick with every trait/flag false,
      so the step takes its cheapest awake branch (the asleep arm, the stress-from-
      wounds/infection/hemophobia arms and the idle-increment arms are not exercised; the
      not-deaf sound-stress arm and all seven stat writes DO run). The reading is therefore a
      representative FLOOR of the typical per-tick handler cost, not a worst case: a bitten,
      sleeping or idle player's tick is a different (still cheap, branchy-arithmetic) path.

  P2  takeover boot, server `bench.global NutritionRevamp.kernel.fast.step 100000`: a METHOD
      NOTE, not a measurement. `bench.global` calls a resolved global N times with NO arguments,
      and `kernel.fast.step(inp, out, c)` needs a filled input/output/constants triple, so the
      call raises inside the loop and the ack carries `error` with `calls` at or near 0. This is
      exactly why Task 2 exposed the zero-argument `bench_fast` as the step's proxy (P1); the
      error reply is RECORDED as the reason `kernel.fast.step` cannot be benched directly, graded
      `trivial`, never treated as a failure.

  P3  tick.rate 10 on the takeover boot (ticks/s and world-min/s), then the SECOND boot under
      `nr-overlay`, tick.rate 10 as the control. Overlay runs vanilla's seven updaters; takeover
      runs the mod's handler INSTEAD of them, so takeover-vs-overlay tick rate is the in-context
      "no more per tick than the seven updaters it replaces" comparison -- there is no direct
      bench of the Java updaters, this is the proxy.

  ENTRY GATE  from P1 and P3: if the per-call cost is within budget AND takeover tracks overlay,
      the plan proceeds as written (takeover stays the shipped default). If not, the overlay-
      default finding is written plainly -- it does not change any other task (the engine is
      built either way); it changes only the shipped mode and the § 6 claim, which Task 11 and
      Task 17 then read. The plan is NOT altered.

PREDICTIONS AND FALSIFIERS (written before the run):

  P1: `usPerCall` is a few µs -- the step is arithmetic over ~24 stats with no allocation (the
      tables are reused), and Plan 1 benched the `defaults()` table constructor at ~2 µs
      (`x131d-20261004-205257`, artifacts register). Falsifier: `usPerCall` above ~50 µs (the
      step is doing per-call work it should not).
  P3: the takeover tick rate sits within a few percent of overlay's, because the handler replaces
      the seven updaters rather than adding to them. Falsifier: takeover tick rate below 90 % of
      overlay's (the handler's per-player cost is material).

What follows is the template's own rule, kept as the house shape this driver obeys.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_...`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
"""
import json
import os
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, num           # noqa: E402
from pzt import fixture as fx, profile                                         # noqa: E402
from pzt.paths import new_run_dir                                             # noqa: E402
from pzt.session import (Timeline, make_client, make_server,                  # noqa: E402
                         teardown, verify)

PROFILE = "nr-takeover"           # the first boot
OVERLAY_PROFILE = "nr-overlay"    # the second boot (the control)
SESSION = ("Plan 2 entry gate (§ 6 cost budget): server bench.global NutritionRevamp.bench_fast "
           "100000 (per-call µs of the whole fast step, a steady-state awake floor), the "
           "kernel.fast.step no-arg method note, and tick.rate 10 on a takeover boot beside an "
           "overlay boot of the same fixture")
ARTIFACT = "cost.json"
USER = "admin"
# This session lands NO harness change, so no acceptance smoke test is owed; the Plan 1 close
# acceptance run is named as the harness's last green smoke test.
ACCEPTANCE_RUN = "x131d-20261004-205257"

BENCH_N = 100000          # bench.global's cap; usPerCall = ms * 1000 / n
TICK_SECONDS = 10         # the OnTick wall window tick.rate arms
BUDGET_US = 50.0          # P1 falsifier / entry-gate budget: usPerCall above this is work it should not do
TRACK_FLOOR = 0.90        # entry gate: takeover tick rate must be >= 90 % of overlay's

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def save_art():
    """Write the artifact, tolerant of there being no live server (between boots / teardown).

    Mirrors `_common.save` but reads the errors off whichever server is currently booted
    (`cur['server']`), because this driver manages two servers serially rather than one. Never
    raises: it runs on the teardown path and a failed write must not skip the kills that follow."""
    try:
        out["timeline"] = list(tl.items)
        srv = cur.get("server")
        if srv is not None:
            out["live_server_errors"] = srv.errors[:20]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    """One SEQUENCED bus call: the ack and both wall clocks bracketing it."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    save_art()
    return row


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    """The prediction, the falsifier, the reading and the verdict, beside each other. `verdict`
    is one of as_predicted / falsified / trivial / unmeasured."""
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    save_art()
    return row


def tick_rate(side, label, seconds=TICK_SECONDS):
    """Arm tick.rate for a wall window, then wait for its asynchronous result document.

    `tick.rate <seconds>` answers at once with {side, armed, seconds, result, file}; the file-
    scope OnTick counter writes `tick-rate.json` when the window closes, carrying ticksPerSecond
    and worldMinutesPerSecond (PZTestKit_Core.lua:1123). `wait_result` filters on `after` (wall
    mtime) so the second boot's document cannot be mistaken for the first's."""
    after = time.time()
    arm_row = step(f"{label}_tick_arm", side, "tick.rate", str(seconds))
    arm = arm_row["ack"]
    result = None
    if isinstance(arm, dict) and arm.get("armed"):
        name = arm.get("result") or "tick-rate"
        try:
            result = side.bus.wait_result(name, timeout=seconds + 20, after=after)
        except (RuntimeError, TimeoutError, OSError) as e:
            result = {"error": f"{type(e).__name__}: {e}"}
    out_row = {"arm": arm, "result": result,
               "ticksPerSecond": result.get("ticksPerSecond") if isinstance(result, dict) else None,
               "worldMinutesPerSecond": result.get("worldMinutesPerSecond")
               if isinstance(result, dict) else None}
    save_art()
    return out_row


prof = profile.load(PROFILE)
prof2 = profile.load(OVERLAY_PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x132c-dry-run", None) if DRY_RUN else new_run_dir("x132c")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
servers, cur = {}, {}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),               # the takeover boot (the primary)
    "profile_overlay": prof2.report(),      # the overlay boot (the control)
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"BENCH_N": BENCH_N, "TICK_SECONDS": TICK_SECONDS, "BUDGET_US": BUDGET_US,
                  "TRACK_FLOOR": TRACK_FLOOR},
    "world_changes": {"restored": "two boots, each a fresh fixture restore; no world write "
                                  "(bench and tick-rate reads only)", "left_in_place": []},
    "boots": {}, "steps": [], "notes": [], "phases": {}, "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)


def boot(label, prof_x, body):
    """One fresh server + client on `prof_x`, run `body(server, c, B)`, torn down in its own
    finally. `servers[label]` keeps the handle for the outer safety hard-kill."""
    B = out["boots"][label] = {"profile": prof_x.report(), "reuse": False}
    cur.clear()
    cur.update({"label": label})
    tl.mark("boot", label=label)
    clients = []
    server = None
    base = os.path.join(run_dir, label)
    try:
        os.makedirs(base, exist_ok=True)
        server = make_server(base, rec, mods=prof_x.mods, mod_sources=prof_x.sources,
                             mod_skip=prof_x.skip, sandbox=prof_x.sandbox or None)
        server.log_path = os.path.join(run_dir, f"server-stdout-{label}.log")
        servers[label] = server
        cur["server"] = server
        server.start(timeout=prof_x.server_timeout)
        tl.mark("server_started", label=label)
        c, restored = make_client(os.path.join(run_dir, f"c-{label}"), USER, server, rec)
        cur["client"] = c
        c.start()
        clients.append(c)
        c.wait_ready(timeout=prof_x.client_timeout)
        tl.mark("session_ready", label=label)
        B["build"] = server.build
        B["session_ready_wall"] = wall()
        B["verify"] = verify(prof_x, server, clients, tl)
        B["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                               "client": sorted(set(c.mods_not_found))}
        body(server, c, B)
    except Exception as e:                       # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        save_art()
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                   # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
                B["server_error_count"] = len(server.errors)
                B["server_errors"] = server.errors[:20]
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            B["wall_end"] = wall()
            cur.clear()
            save_art()


def takeover_body(server, c, B):
    # ---- P1: the headline per-call cost of the whole fast step ------------------------------
    r1 = step("p1_bench_fast", server, "bench.global", f"NutritionRevamp.bench_fast {BENCH_N}")
    b1 = r1["ack"]
    B["bench_fast"] = b1
    us = b1.get("usPerCall") if isinstance(b1, dict) else None
    out["phases"]["P1"] = {
        "question": "per-call wall cost of one whole fast-kernel step through NutritionRevamp."
                    "bench_fast (a representative steady-state AWAKE-tick floor, not a worst case)",
        "ack": b1, "usPerCall": us}
    if not isinstance(b1, dict) or us is None or "error" in b1:
        v1 = "unmeasured"
    elif us <= BUDGET_US:
        v1 = "as_predicted"
    else:
        v1 = "falsified"
    grade("P1", predicted=f"usPerCall a few µs (arithmetic over ~24 stats, no allocation; Plan 1 "
                          f"benched defaults() at ~2 µs)", observed={"usPerCall": us, "ack": b1},
          verdict=v1, falsifier=f"usPerCall above ~{BUDGET_US} µs")

    # ---- P2: kernel.fast.step is not benchable without arguments (a method note) ------------
    r2 = step("p2_bench_step", server, "bench.global", f"NutritionRevamp.kernel.fast.step {BENCH_N}")
    b2 = r2["ack"]
    B["bench_step_attempt"] = b2
    out["phases"]["P2"] = {
        "question": "can kernel.fast.step be benched directly? (no -- it needs inp/out/c args "
                    "bench.global cannot pass; bench_fast is its proxy, P1)",
        "ack": b2}
    v2 = "trivial"      # expected: an error reply (nil-arg raise), recorded as the method note
    grade("P2", predicted="an error/resolve-only reply: kernel.fast.step(inp,out,c) raises when "
                          "called with no args, so bench_fast (P1) is the step's proxy",
          observed={"ack": b2, "note": "kernel.fast.step is not directly benchable without a "
                                       "filled input; this is a method note, not a failure"},
          verdict=v2, falsifier="(none -- a trivial reading by construction)")

    # ---- P3a: the takeover tick rate -------------------------------------------------------
    tr = tick_rate(server, "p3a_takeover")
    B["tick_rate"] = tr
    out["phases"]["P3_takeover"] = tr


def overlay_body(server, c, B):
    # ---- P3b: the overlay tick rate (the control) ------------------------------------------
    tr = tick_rate(server, "p3b_overlay")
    B["tick_rate"] = tr
    out["phases"]["P3_overlay"] = tr


try:
    boot("takeover", prof, takeover_body)
    boot("overlay", prof2, overlay_body)

    # ---- P3 grade: takeover vs overlay tick rate -------------------------------------------
    take = out["phases"].get("P3_takeover") or {}
    over = out["phases"].get("P3_overlay") or {}
    take_tps = num(take.get("ticksPerSecond"))
    over_tps = num(over.get("ticksPerSecond"))
    take_wms = num(take.get("worldMinutesPerSecond"))
    over_wms = num(over.get("worldMinutesPerSecond"))
    ratio = (take_tps / over_tps) if (take_tps is not None and over_tps not in (None, 0)) else None
    out["phases"]["P3"] = {
        "takeover": {"ticksPerSecond": take_tps, "worldMinutesPerSecond": take_wms},
        "overlay": {"ticksPerSecond": over_tps, "worldMinutesPerSecond": over_wms},
        "takeover_over_overlay": ratio}
    if take_tps is None or over_tps is None:
        v3 = "unmeasured"
    elif ratio is not None and ratio >= TRACK_FLOOR:
        v3 = "as_predicted"
    else:
        v3 = "falsified"
    grade("P3", predicted="takeover tick rate within a few percent of overlay's (the handler "
                          "replaces the seven updaters, it does not add to them)",
          observed=out["phases"]["P3"], verdict=v3,
          falsifier=f"takeover tick rate below {int(TRACK_FLOOR * 100)} % of overlay's")

    # ---- ENTRY GATE: the § 6 verdict -------------------------------------------------------
    us = out["phases"].get("P1", {}).get("usPerCall")
    within_budget = us is not None and us <= BUDGET_US
    tracks = ratio is not None and ratio >= TRACK_FLOOR
    if us is None or take_tps is None or over_tps is None:
        gate = "unmeasured"
        gv = "unmeasured"
    elif within_budget and tracks:
        gate = "proceed"
        gv = "as_predicted"
    else:
        gate = "overlay-default finding"
        gv = "falsified"
    grade("ENTRY_GATE",
          predicted="proceed: usPerCall within budget AND takeover tracks overlay, so takeover "
                    "stays the shipped default and the plan runs as written",
          observed={"usPerCall": us, "within_budget": within_budget,
                    "takeover_tps": take_tps, "overlay_tps": over_tps,
                    "ratio": ratio, "tracks": tracks},
          verdict=gv,
          falsifier="overlay-default finding: cost above budget OR takeover below "
                    f"{int(TRACK_FLOOR * 100)} % of overlay -- changes only the shipped mode and "
                    "the § 6 claim (Task 11, Task 17), never the plan's other tasks",
          extra={"gate": gate})

    out["summary"] = {
        "verify_ok": {k: [v.get("ok") for v in b.get("verify", [])] for k, b in out["boots"].items()},
        "mods_not_found": {k: b.get("mods_not_found") for k, b in out["boots"].items()},
        "boot_errors": {k: b.get("error") for k, b in out["boots"].items()},
        "server_error_count": {k: b.get("server_error_count") for k, b in out["boots"].items()},
        "client_lua_error": {k: b.get("client_lua_error") for k, b in out["boots"].items()},
        "usPerCall": us,
        "takeover_tps": take_tps, "overlay_tps": over_tps,
        "takeover_over_overlay": ratio,
        "entry_gate": gate,
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                           # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    cur.clear()
    save_art()
    for srv in servers.values():
        try:
            hard_kill(srv, [])
        except Exception:                        # noqa: BLE001 - teardown path, never raise
            pass
    save_art()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                        # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
