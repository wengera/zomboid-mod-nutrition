"""x131-swtraits -- X42: does SomewhatTraitsCore's adaptive-metabolism calorie write reach the
server's calorie store under a co-boot, what is the per-write step, and at what cadence:
Plan 1 Task 15.

The run id prefix is `x131s` (run id `x131s-<date>-<time>`): the register's run-id pattern
refuses a hyphen in the prefix.

Copied from `x131_traits.py` (the template's house shape). ONE live session, ONE boot, profile
`x13-swtraits` (PZTestKit + SomewhatTraits + SomewhatTraitsCore from workshop 3498347699, live
`42.15/` trees, + TKX_TraitProbe; the fixture's own sandbox, DayLength = 4, a 90-minute day).

The subject (SomewhatTraitsCore `42.15/media/lua/server/SWTraitsCore_server.lua`, read
2026-10-04, file dated 2026-08-12): a selector `OnTick` handler clears its `player` upvalue on
every tick and, once `getTimestampMs()` has passed `timestamp + 5000 / players`, picks one
player (`:31-56`); `SWAdaptiveMetabolism` (`:74-89`), registered after it on `OnTick`, runs in
that same tick and, if the player holds `SWTraits:SWAdaptiveMetabolism`, does
`setCalories(calories + 60 / dayLength * 0.5)` while weight < 77 and calories < 3600, and the
subtraction while weight > 83 and calories > -2100 (x5 while running or sprinting).
`dayLength` is `getSandboxOptions():getDayLengthMinutes()` read at file scope (`:14`).

Six arms of ARM_S seconds, the player idle, in three weight-matched pairs, each trait-held arm
read only against the trait-absent arm at its own weight (vanilla's idle burn scales with
weight / 80, so slopes are never compared across weights):

  W75  server `nutrition.set admin weight 75`, `calories 1000`, read back; (a) trait absent;
       then `moddata.set admin TKX_grant SWTraits:SWAdaptiveMetabolism`, server `stats.get`
       polled until `traitList` holds it; `calories 1000` again; (b) trait held; then
       `TKX_grant -SWTraits:SWAdaptiveMetabolism` and the list polled until it is gone.
  W85  the same with weight 85: (c) absent, (d) held.
  W80  the same with weight 80: (e) absent, (f) held.

Each arm polls server `stats.get admin` back to back, at least POLL_S apart, for ARM_S
seconds; every reply carries the server's own `wall` (getTimestampMs at the snapshot),
`worldAge`, `calories`, `weight`, `running`, `sprinting` and `traitList`, so the series is
stamped by the server and the irregular bus pickup (0.26-2.02 s, Task 14) does not skew it.
The amendments name `nutrition.get admin`; `stats.get admin` is the same Nutrition read plus
the server's wall stamp and the trait list, in one tick, which is what the step timing needs.

Reading. Per arm: the least-squares slope of calories on server wall (kcal/s). Per held arm:
each interval's residual `dCal - slope_control * dt` against its twin's slope; an interval
whose residual exceeds STEP_FLOOR (or 4 x the control's residual spread, whichever is larger)
in magnitude holds a write; the step is that residual; the cadence is the spacing of the
step-bearing intervals' end stamps (each step lies inside its interval, so a spacing is good
to one poll interval either side, so each spacing is graded as the bracket
[next.t0 - prev.t1, next.t1 - prev.t0] holding 4.9-5.6 s, and the mean cadence is
(last step - first step) / (steps - 1)).

PREDICTIONS AND FALSIFIERS (written before the run):

  dayLength: `getDayLengthMinutes()` is 90 at DayLength 4, so the predicted step is
      60 / 90 * 0.5 = 0.3333 kcal per write, idle.
  (b) vs (a), weight 75: the held slope sits above the control's by about 0.3333 / 5 =
      0.067 kcal/s; positive steps of 0.333 +/- 0.05 kcal about 5 s apart (5.0-5.5 s,
      one write per 5 s for one player, plus a tick). Falsifier: (b)'s slope inside (a)'s
      noise with no steps -- the write does not reach the store under the co-boot.
  (d) vs (c), weight 85: the mirror image, negative steps of 0.333 about 5 s apart.
      Falsifier: (d) matching (c).
  (f) vs (e), weight 80: inside the 77-83 dead band, no steps; the slopes match within noise.
      Falsifier: steps or a slope offset of the size above -- the handler writes inside its band.
  Controls (a), (c), (e): vanilla's idle drain alone, smooth, no step of 0.333 size (the
      trait is absent and the handler returns at `:76`).
  A grant that never shows in the server's `traitList` makes its pair `unmeasured`; a player
      found running or sprinting in a held arm voids the x1 step prediction for that sample.

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
import statistics
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

PROFILE = "x13-swtraits"
SESSION = ("X42: SomewhatTraitsCore SWAdaptiveMetabolism calorie write under a co-boot -- six "
           "60 s idle arms in weight-matched pairs (75, 85, 80; trait absent then held via "
           "TKX_grant), server stats.get polled for the calorie series on the server's wall")
ARTIFACT = "swtraits.json"
USER = "admin"
ACCEPTANCE_RUN = "x131b-20261004-175911"

TRAIT_ID = "SWTraits:SWAdaptiveMetabolism"
TRAIT_MATCH = "adaptivemetabolism"   # list names are the id's path, case-folded (T14.3)
ARM_S = 60.0
POLL_S = 1.0
GRANT_WAIT_S = 15.0
CAL_START = 1000
STEP_PRED = 60.0 / 90.0 * 0.5
STEP_FLOOR = 0.15
PAIRS = [("W75", 75, "a", "b"), ("W85", 85, "c", "d"), ("W80", 80, "e", "f")]
FIELD_COUNT = 9

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"


def wall():
    return round(time.time() - t0, 3)


def ms():
    return int(time.time() * 1000)


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), ms()
    val = ask(side, cmd, args, timeout=timeout)
    t_after, e_after = wall(), ms()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": e_before,
           "epoch_ms_after": e_after, "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    save(path, out, tl, server)
    return row


def holds(lst):
    if not isinstance(lst, list):
        return False if lst in ({}, None) else None
    return any(TRAIT_MATCH in str(n).lower() for n in lst)


def snap(tag):
    t_b, e_b = wall(), ms()
    val = ask(server, "stats.get", USER)
    t_a, e_a = wall(), ms()
    row = {"tag": tag, "wall_before": t_b, "wall_after": t_a,
           "epoch_ms_before": e_b, "epoch_ms_after": e_a}
    if isinstance(val, dict):
        for k in ("calories", "weight", "worldAge", "wall", "running", "sprinting", "moving",
                  "asleep", "hunger"):
            row[k] = val.get(k)
        row["traitList"] = val.get("traitList")
        traits = val.get("traits")
        row["field_count"] = len(traits) if isinstance(traits, dict) else None
        row["held"] = holds(val.get("traitList"))
    else:
        row["reply"] = val
    return row


def nset(tag, field, value):
    r = step(tag, server, "nutrition.set", f"{USER} {field} {value}")
    back = step(tag + "_readback", server, "nutrition.get", USER)
    return {"set": r, "readback": back["ack"]}


def wait_trait(tag, want):
    rows, t_s = [], time.time()
    while time.time() - t_s < GRANT_WAIT_S:
        r = snap(tag)
        rows.append(r)
        if r.get("held") is want:
            return {"ok": True, "rows": rows}
        time.sleep(0.5)
    return {"ok": False, "rows": rows}


def arm(label):
    rows, t_s = [], time.time()
    while time.time() - t_s < ARM_S:
        t_i = time.time()
        r = snap(f"arm_{label}")
        rows.append(r)
        left = POLL_S - (time.time() - t_i)
        if left > 0:
            time.sleep(left)
    return rows


def series(rows):
    pts = []
    for r in rows:
        w, c = num(r.get("wall")), num(r.get("calories"))
        if w is not None and c is not None:
            pts.append((w / 1000.0, c))
    pts.sort()
    return pts


def slope(pts):
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def residuals(pts, s):
    out_r = []
    for i in range(1, len(pts)):
        dt = pts[i][0] - pts[i - 1][0]
        dc = pts[i][1] - pts[i - 1][1]
        if dt <= 0:
            continue
        out_r.append({"t0": pts[i - 1][0], "t1": pts[i][0], "dt": round(dt, 3),
                      "dcal": dc, "resid": dc - s * dt})
    return out_r


def steps_of(res, floor):
    st = [r for r in res if abs(r["resid"]) > floor]
    spacing = [{"mid": round(st[i]["t1"] - st[i - 1]["t1"], 3),
                "lo": round(st[i]["t0"] - st[i - 1]["t1"], 3),
                "hi": round(st[i]["t1"] - st[i - 1]["t0"], 3)} for i in range(1, len(st))]
    return st, spacing


def spread(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"n": len(v), "min": min(v), "median": statistics.median(v), "max": max(v)}


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x131s-dry-run", None) if DRY_RUN else new_run_dir("x131s")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, clients, t0 = Timeline(), [], time.time()
server = None if DRY_RUN else make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                                          mod_skip=prof.skip, sandbox=prof.sandbox or None)
c = None

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
    "subject_tree": {"workshop_item": "3498347699", "mods": ["SomewhatTraits/42.15",
                     "SomewhatTraitsCore/42.15"], "read_on": "2026-10-04",
                     "server_file": "SomewhatTraitsCore/42.15/media/lua/server/SWTraitsCore_server.lua",
                     "server_file_mtime": "2026-08-12 00:01"},
    "constants": {"ARM_S": ARM_S, "POLL_S": POLL_S, "GRANT_WAIT_S": GRANT_WAIT_S,
                  "CAL_START": CAL_START, "STEP_PRED": STEP_PRED, "STEP_FLOOR": STEP_FLOOR,
                  "PAIRS": PAIRS, "TRAIT_ID": TRAIT_ID},
    "world_changes": {"restored": "the trait is removed after each held arm",
                      "left_in_place": ["weight 80", "calories near 1000"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "arms": {},
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
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    out["phases"]["T0"] = {
        "server": snap("t0"),
        "registry": step("t0_reg", server, "lua.global",
                         "SWTraits.traits.SWAdaptiveMetabolism")["ack"],
        "rl_of": step("t0_rl_of", server, "lua.global", "ResourceLocation.of")["ack"],
    }
    save(path, out, tl, server)

    for pair, weight, absent, held in PAIRS:
        ph = {"weight": weight}
        ph["weight_set"] = nset(f"{pair}_weight", "weight", weight)
        ph["cal_set_absent"] = nset(f"{pair}_cal_absent", "calories", CAL_START)
        ph["pre_absent"] = snap(f"{pair}_pre_absent")
        out["arms"][absent] = {"pair": pair, "weight": weight, "trait": False,
                               "rows": arm(absent)}
        save(path, out, tl, server)
        ph["grant"] = step(f"{pair}_grant", server, "moddata.set",
                           f"{USER} TKX_grant {TRAIT_ID}")
        ph["grant_wait"] = wait_trait(f"{pair}_grant_wait", True)
        ph["cal_set_held"] = nset(f"{pair}_cal_held", "calories", CAL_START)
        out["arms"][held] = {"pair": pair, "weight": weight, "trait": True,
                             "granted": ph["grant_wait"]["ok"], "rows": arm(held)}
        ph["remove"] = step(f"{pair}_remove", server, "moddata.set",
                            f"{USER} TKX_grant -{TRAIT_ID}")
        ph["remove_wait"] = wait_trait(f"{pair}_remove_wait", False)
        out["phases"][pair] = ph
        save(path, out, tl, server)

    out["phases"]["probe_counts"] = {
        "grants": step("grants", server, "lua.global", "TKX_TraitProbe.grants")["ack"],
        "removes": step("removes", server, "lua.global", "TKX_TraitProbe.removes")["ack"],
        "lastId": step("lastid", server, "lua.global", "TKX_TraitProbe.lastId")["ack"],
    }

    # ---- grading ---------------------------------------------------------------------------
    summ = {}
    for pair, weight, absent, held in PAIRS:
        pa, ph_ = series(out["arms"][absent]["rows"]), series(out["arms"][held]["rows"])
        sa, sh = slope(pa), slope(ph_)
        ra = residuals(pa, sa) if sa is not None else []
        sd = statistics.pstdev([r["resid"] for r in ra]) if len(ra) > 2 else None
        floor = max(STEP_FLOOR, 4 * sd) if sd is not None else STEP_FLOOR
        rh = residuals(ph_, sa) if sa is not None else []
        st_h, sp_h = steps_of(rh, floor)
        st_a, _ = steps_of(ra, floor)
        held_flags = [r.get("held") for r in out["arms"][held]["rows"]]
        absent_flags = [r.get("held") for r in out["arms"][absent]["rows"]]
        moving = [bool(r.get("running")) or bool(r.get("sprinting"))
                  for r in out["arms"][held]["rows"]]
        summ[pair] = {
            "weight": weight, "n_absent": len(pa), "n_held": len(ph_),
            "slope_absent": sa, "slope_held": sh,
            "slope_diff": (sh - sa) if (sa is not None and sh is not None) else None,
            "control_resid_sd": sd, "step_floor_used": floor,
            "control_steps": len(st_a),
            "held_steps": [{"t1": s["t1"], "dt": s["dt"], "resid": s["resid"]} for s in st_h],
            "step_sizes": spread([s["resid"] for s in st_h]),
            "step_spacing_s": sp_h, "step_spacing": spread([x["mid"] for x in sp_h]),
            "cadence_mean_s": (round((st_h[-1]["t1"] - st_h[0]["t1"]) / (len(st_h) - 1), 3)
                               if len(st_h) > 1 else None),
            "held_all_rows": all(x is True for x in held_flags),
            "absent_no_rows": all(x is False for x in absent_flags),
            "running_or_sprinting_in_held": any(moving),
            "held_residuals": rh, "absent_residuals": ra,
        }
    out["phases"]["summary"] = summ

    for pair, weight, absent, held in PAIRS:
        s = summ[pair]
        if not out["arms"][held]["granted"] or not s["held_all_rows"] or s["slope_absent"] is None:
            v = "unmeasured"
        elif weight == 80:
            v = "as_predicted" if not s["held_steps"] else "falsified"
        else:
            sign = 1 if weight < 77 else -1
            sizes = [x["resid"] * sign for x in s["held_steps"]]
            ok_size = bool(sizes) and all(abs(x - STEP_PRED) <= 0.05 for x in sizes)
            ok_cad = (bool(s["step_spacing_s"])
                      and all(x["lo"] <= 5.6 and x["hi"] >= 4.9 for x in s["step_spacing_s"]))
            if not s["held_steps"]:
                v = "falsified"
            elif ok_size and ok_cad:
                v = "as_predicted"
            else:
                v = "falsified"
        grade(pair,
              predicted=("no steps, slope equals the control's (dead band)" if weight == 80 else
                         ("+" if weight < 77 else "-") + "0.3333 kcal steps about 5 s apart"),
              observed={k: s[k] for k in ("slope_absent", "slope_held", "slope_diff",
                                          "step_sizes", "step_spacing", "cadence_mean_s",
                                          "control_steps",
                                          "step_floor_used", "running_or_sprinting_in_held")},
              verdict=v,
              falsifier=("steps or a slope offset inside the band" if weight == 80 else
                         "held slope inside the control's noise with no steps"))

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "slopes": {p: (summ[p]["slope_absent"], summ[p]["slope_held"]) for p in summ},
        "steps": {p: summ[p]["step_sizes"] for p in summ},
        "spacing": {p: summ[p]["step_spacing"] for p in summ},
        "cadence_mean_s": {p: summ[p]["cadence_mean_s"] for p in summ},
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
        save(path, out, tl, server)
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
