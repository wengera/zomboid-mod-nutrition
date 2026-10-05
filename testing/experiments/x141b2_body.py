"""x141b2-body -- Plan 3, the second acceptance boot on the FIXED mod tree (after the close fix wave
Parts A-C): the T18 arms that x141b-20261005-122603 could not measure, re-run under the design
precondition `Nutrition = false`, and the live smoke test of the three harness commands Part C landed
(`sandbox.var`, `globalmoddata.setpath`, `zombie.near`). ONE boot of profile `x14-body` (PZTestKit +
NutritionRevamp Mode 1 + LegacyMirror on + TKX_MetWatch; Nutrition = false; DayLength 1: a game day is
15 wall minutes at speed 1, a game minute 0.625 s). The run id prefix is `x141b2`. Copied from
`x141_body.py` (provenance, wall-bracketed steps, predictions/verdicts, `to_num`, the persist/step
shape, each phase under its own try); it samples far less often (x141b's artifact was 14 MB) and keeps
only the named keys of each stats.get reply.

THE SUBJECT: the fixture admin is FEMALE (x141b A: fm 22.4 / lm 57.6 = split(80, female)); first sight
lands at world age ~3.1 h (10:06; world age 0 is 07:00, #2890), so day 0 runs ~20.9 game hours and the
day closes at world ages 24, 48, ... (07:00).

THE PREDICTIONS (written before the run, from the committed kernels at ca9ab9f; the live values come off
the first-sight record):
  P   precondition: server SandboxVars.Nutrition reads false; NutritionRevamp.server.options.nutritionOn
      reads false; metabolism.stats.preconditionWarnings 0; the server log carries NO "expects
      SandboxVars.Nutrition = false" line and its boot self-report ends "nutritionOn=false"; the run's
      servertest SandboxVars.lua holds `Nutrition = false`.
  C   first-sight mirror: ~5 s after the body exists, WITHOUT the harness calling requestMirror, the
      client's NutritionRevamp.client.mirror.body_fm reads 22.4 (= the record's fm, 1e-6), body_weight
      80; metabolism.stats.firstSightMirrors 1. (The mod's own OnGameStart request also fires; the
      client's `received` count is recorded beside it.) Falsifier: body_fm 0 or absent.
  A0  flags on day 0 (trend (w - mass7[1]) / 7 = 0 exactly up to float rounding: mass7 is all 80): every
      server AND client sample reads incWeight, incWeightLot, decWeight all FALSE (vanilla updateWeight
      off; only the mod's minute write moves them). Falsifier: any true on day 0 (x141b read dec true).
  A1  flags fasting: close 1 at world age 24 pays ~0.87 d of deficit (REE 19.7*57.6+413 = 1547.7 x cold
      ~1.02 + idle 0.3*80*24 = 576 -> ~2150/d -> ~1870 kcal): fat at its ceiling 69*22.4 = 1546 kcal
      (-0.164 kg), lean the rest (-0.18 kg) -> w ~79.66, trend ~-0.049 < -0.02 -> decWeight TRUE on the
      server from the first slow minute after the close, the client within the packet (<= ~2 s); inc and
      lot false. Every sample's three flags equal K.body.flags(K.body.trend(mass7, w)) of the nearest
      record read. Falsifier: dec false on a side after the close (beyond 2 s), or a flag != the trend's.
  L   lot (X25 #1291), by the record-edit instrument: `globalmoddata.setpath NutritionRevamp.players
      admin.body.fm <fm + 1.6>` on day 1 -> w ~81.26, trend ~+0.18 > 0.10 -> incWeight and incWeightLot
      TRUE, decWeight false on the server at the next slow minute, the client agreeing within ~2 s.
      Falsifier: lot false on the server with the trend > 0.10, or the client never agreeing within 10 s.
      (DEVIATION from the amendments' feast arm: a feast's mass lands only at a day close and the trend
      reads against mass7[1] = 80, so no in-session feast reaches +0.7 kg over 80; the lot flag is the
      mod's write of its own trend, so the record edit drives the same write.)
  B   band crossing + push: after the lot read, the same setter puts fm = 75.10 - lm (w = 75.10, band
      normal, trend -0.70 -> dec true). Close 2 at world age 48 pays a full fasting day (~2150-2200 kcal):
      fat <= 69*~17.0 = ~1175 kcal (-0.124 kg), lean ~1000 kcal (-0.55 kg) -> w ~74.43 <= 75 -> band
      underweight: weight.stats.bandChanges 0 -> 1, pushes +1, UNDERWEIGHT on the server at the close
      minute and on the client within 2 s (sendSyncPlayerFields 2, #2099), bandRepairs still 0 the next
      minutes. Falsifier: bandChanges != 1, the trait absent on a side, client latency > 2 s, bandRepairs
      > 0. (DEVIATION: the amendments name `lm`; this edits `fm`, because lm feeds the Strength ceiling
      (x141c: the ceiling fell 5 -> 4 at lm 56.37) and a -5 kg lm edit would fire a Strength fall, its
      FEEBLE remap and its own push in the same minute as the band push. The fm edit raises fatDep
      instead -- read in E below, computed from the record.)
  E   energy-state floor: speed 1, NO food-timer write anywhere in the session; eat a lettuce then a bread
      (bulk 6.5 + 8.2 against FULL_BULK 8 -> fill 1). E = clamp(1 + 0.5*clamp(-eb24h/1500,-1,1) +
      0.5*fatDep) with eb24h ~-2150 (clamped term 1) and fatDep = (fmRef - fm)/fmRef ~(22.4-16.9)/22.4 =
      0.245 -> E ~1.62; at fill 1 the server's hunger reads 0.15*(E-1) ~0.093 > 0, and at every read
      hunger == clamp((1-fill)*E + 0.15*max(0,E-1), 0, 1) of the adjacent record read (1e-4).
      Falsifier: hunger 0, or the no-floor form, at fill 1 with E > 1; the eat refused (validStart false).
  M   mirror off: `sandbox.var NR.LegacyMirror false` replies ok true (before true, after false); the
      options poll reads false within a slow minute; weight.stats.mirrorWrites stops while
      weight.stats.minutes runs; a server `nutrition.set admin calories 500` holds at 500 (both sides)
      with the mirror off, where the same write with the mirror on is overwritten back to mirrorLast[1]
      within a slow minute. Falsifier: mirrorWrites rising with the option false, or 500 overwritten.
  F   the 24 h blend: at every fasting record read, mirrorLast[1] == clamp(ebDay + eb7[7] *
      clamp(1 - (lastAgeH - lastCloseAgeH)/24, 0, 1), -2200, 3700) within 0.5 kcal and energyState ==
      state(that eb24h, fatDep) within 1e-6; the clock form (weight 1 - hourOfDay/24, close at 07:00)
      differs by ~7/24 * eb7[7] ~ 600 kcal on day 1. Falsifier: the record matching the clock form.
  G   stack trace: `exercise.do pushups 20` (20 game minutes, 12.5 s wall: x141c found 2 game minutes
      shorter than one rep) -> training.stats.reps rises, and the server log holds ZERO lines matching
      "attempted index: type" or "non-table: Fitness" (x141c: one ~5-line trace per rep).
  Z   zombie.near 2 (smoke): ok true, spawned 2, every dist <= 1.5 tiles.
  H   no harness edit, no mod edit; the three new commands are graded on their replies (sandbox.var in
      M, globalmoddata.setpath in L/B, zombie.near in Z).

CONTROLS (not inputs of the body model): thirst and fatigue pinned to 0 every third cycle (#0179; the
fatigue pin keeps the subject awake and out of the Sleeping class). NO health-from-food timer write (x141b
F: a timer held FOOD_EATEN at 4 and refused every eat): the fast is ~2 days, the level-4 HUNGRY drain ~0.6
health per game hour (x141b) costs ~30 health; health is read and a reading under 15 stops the fast.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import json
import math
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x14-body"
SESSION = ("Plan 3 acceptance boot 2 on the fixed tree: the precondition Nutrition=false, the flags on "
           "day 0 / fasting / lot, the band crossing and push via the record edit, the first-sight mirror, "
           "the energy-state floor, the mirror off-switch, the 24 h blend, the per-rep stack trace; smoke "
           "test of sandbox.var, globalmoddata.setpath, zombie.near; one boot of x14-body at DayLength 1")
ARTIFACT = "body2.json"
USER = "admin"
PRIOR_RUN = "x141b-20261005-122603"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
BODY_KEY = f"{USER}.body"
WSTATS = "NutritionRevamp.server.weight.stats"
MSTATS = "NutritionRevamp.server.metabolism.stats"
SSTATS = "NutritionRevamp.server.strength.stats"
TSTATS = "NutritionRevamp.server.training.stats"
HEALTH_HOP = "getBodyDamage.getOverallBodyHealth"
DEAD_HOP = "isDead"

SPEED = 5
DAY_WALL_S_AT1 = 900.0
FAST_WALL_BUDGET_S = 22 * 60
HEALTH_FLOOR = 15.0
PIN_EVERY = 3
HEALTH_EVERY = 4
WSTATS_EVERY = 3
CYCLE_GAP_S = 1.0             # sleep between cycles at speed 5 (a cycle is ~1 s of reads)
WATCH_LEAD_H = 0.3
WATCH_AFTER_S = 8.0
TRAIT_WATCH_S = 40
DAY1_LOT_AT_H = 4.0           # hours after close 1 the lot arm starts
DAY2_AFTER_H = 3.0            # hours after close 2 the fast keeps sampling (blend at day 2)
LOT_DFM = 1.6
BAND_TARGET_W = 75.10
LOT_WATCH_S = 10.0
BAND_SET_WATCH_S = 6.0
BULK = ("Base.Lettuce", "Base.Bread")
CAL_PROBE = 500
PUSHUP_MIN = 20

FAT_CEIL, RHO_LEAN, RHO_FAT = 69.0, 1816.0, 9441.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
NR_RX = re.compile(r"\[NutritionRevamp\]|NutritionRevamp v")
PRECOND_RX = re.compile(r"expects SandboxVars\.Nutrition")
READTYPE_RX = re.compile(r"attempted index: type|non-table: Fitness")
LUAERR_LIMIT, NR_LIMIT = 40, 60

STAT_KEYS = ("weight", "incWeight", "incWeightLot", "decWeight", "hunger", "thirst", "fatigue", "calories",
             "proteins", "carbs", "lipids", "traitList", "worldAge", "wall", "mult", "asleep", "moving",
             "maxWeight", "foodTimer", "moodles", "endurance")


def to_num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:20]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30, keep=None):
    """One bus command, wall-bracketed. `keep` trims a dict reply to the named keys (the stats reads,
    to keep the artifact small); the full reply of every other command is kept."""
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    stored = val
    if keep is not None and isinstance(val, dict):
        stored = {k: val.get(k) for k in keep if k in val}
        if "error" in val:
            stored["error"] = val["error"]
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "epoch_after": round(time.time(), 3), "took": round(t_after - t_before, 3), "ack": stored}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row, val


def ack(r):
    a = r[1] if isinstance(r, tuple) else r.get("ack")
    return a if isinstance(a, dict) else {}


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def gv(side, name, tag):
    a = ack(step(tag, side, "lua.global", name))
    return a.get("value") if a.get("resolved") else None


def chain_s(tag, hop):
    a = ack(step(tag, server, "witness.chain", f"{USER} {hop}"))
    return {"ok": a.get("ok"), "value": a.get("value"), "failedAt": a.get("failedAt")}


def stats(side, tag):
    r, val = step(tag, side, "stats.get", USER if side is server else "", keep=STAT_KEYS)
    a = val if isinstance(val, dict) else {}
    d = {k: a.get(k) for k in STAT_KEYS}
    d["side"] = "server" if side is server else "client"
    d["wall_before"], d["wall_after"], d["epoch_before"] = r["wall_before"], r["wall_after"], r["epoch_before"]
    return d


def body_read(tag, extra=()):
    keys = [BODY_KEY, f"{USER}.stomachFill"] + list(extra)
    r, val = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(keys))
    a = val if isinstance(val, dict) else {}
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    b = vals.get(BODY_KEY)
    rec = {"tag": tag, "wall_before": r["wall_before"], "wall_after": r["wall_after"],
           "epoch_before": r["epoch_before"], "worldAge": a.get("worldAge"),
           "body": b if isinstance(b, dict) else None,
           "stomachFill": to_num(vals.get(f"{USER}.stomachFill")), "missing": a.get("missing")}
    for k in extra:
        rec[k] = vals.get(k)
    return rec


def bnum(b, k):
    return to_num((b or {}).get(k))


def ring(b, k, i):
    v = (b or {}).get(k)
    if isinstance(v, list) and len(v) >= i:
        return to_num(v[i - 1])
    if isinstance(v, dict):
        return to_num(v.get(str(i)))
    return None


def mass(b):
    fm, lm = bnum(b, "fm"), bnum(b, "lm")
    return None if fm is None or lm is None else fm + lm


def clamp(x, lo, hi):
    return min(max(x, lo), hi)


def flags_expected(b, w=None):
    """K.body.flags(K.body.trend(mass7, w)) of a record read (w defaults to fm + lm)."""
    m1 = ring(b, "mass7", 1)
    w = mass(b) if w is None else w
    if m1 is None or w is None:
        return None, None
    t = (w - m1) / 7
    return [t > 0.02, t > 0.10, t < -0.02], t


def blend_expect(b):
    """The record's own 24 h blend (hours since close) and the clock form, from one record read."""
    eb_day, y = bnum(b, "ebDay"), ring(b, "eb7", 7)
    age, close = bnum(b, "lastAgeH"), bnum(b, "lastCloseAgeH")
    fm, fmref = bnum(b, "fm"), bnum(b, "fmRef")
    if None in (eb_day, y, age, close, fm, fmref):
        return None
    hsc = age - close
    eb_h = eb_day + y * clamp(1 - hsc / 24, 0, 1)
    hod = (age % 24 + 7) % 24                       # world age 0 is 07:00 on this fixture (#2890)
    eb_c = eb_day + y * clamp(1 - hod / 24, 0, 1)
    fdep = clamp((fmref - fm) / fmref, 0, 1) if fmref > 0 else 0
    st = clamp(1 + 0.5 * clamp(-eb_h / 1500, -1, 1) + 0.5 * fdep, 0.5, 2.0)
    st_c = clamp(1 + 0.5 * clamp(-eb_c / 1500, -1, 1) + 0.5 * fdep, 0.5, 2.0)
    return {"hsc": hsc, "hod": hod, "eb24h_hsc": eb_h, "eb24h_clock": eb_c, "cal_hsc": clamp(eb_h, -2200, 3700),
            "cal_clock": clamp(eb_c, -2200, 3700), "state_hsc": st, "state_clock": st_c, "fatDep": fdep}


def speed(n, tag):
    ok, rep = server.rcon(f"settimespeed {n}")
    row = {"wall": wall(), "n": n, "ok": ok, "reply": str(rep)[:200]}
    out["speed_changes"].append(row)
    tl.mark("speed", n=n, ok=ok)
    row["server_snap"] = ack(step(f"{tag}_snap_s", server, "time.snapshot", ""))
    return row


def wstats(tag, fields=("bandChanges", "bandRepairs", "pushes", "pushMissing", "minutes", "weightWrites",
                        "flagWrites", "mirrorWrites", "failures")):
    return {f: gv(server, f"{WSTATS}.{f}", f"{tag}_{f}") for f in fields}


def run_phase(name, fn):
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    persist()


def setpath(tag, leaf, value):
    return ack(step(tag, server, "globalmoddata.setpath", f"{STORE} {USER}.body.{leaf} {value!r}"))


def pins(n):
    return ack(step(f"pin{n}", server, "stats.set", f"{USER} thirst 0 fatigue 0"))


def pair(tag, i):
    return {"server": stats(server, f"{tag}_s{i}"), "client": stats(client, f"{tag}_c{i}")}


# ---------------------------------------------------------------- phases
def phase_C():
    """The first-sight mirror, read ~5 s after the body exists; no requestMirror call from here."""
    C = out["phases"]["C"] = {"waits": []}
    end = wall() + 60
    b = None
    while wall() < end:
        b = body_read("C_wait")
        C["waits"].append({"wall": b["wall_before"], "has_body": b["body"] is not None})
        if b["body"] is not None:
            break
        time.sleep(0.5)
    C["body_seen_wall"] = wall()
    C["body_read"] = b
    time.sleep(5.0)
    mk = ("body_fm", "body_lm", "body_weight", "body_band", "body_energyState", "body_tac")
    C["mirror"] = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"C_m_{k}") for k in mk}
    C["mirror_wall"] = wall()
    C["received"] = gv(client, "NutritionRevamp.client.received", "C_recv")
    C["firstSightMirrors"] = gv(server, f"{MSTATS}.firstSightMirrors", "C_fsm")
    C["met_stats"] = {f: gv(server, f"{MSTATS}.{f}", f"C_met_{f}") for f in ("splits", "failures", "minutes", "days", "badReads")}
    C["body_read2"] = body_read("C_body2")
    time.sleep(3.0)
    C["mirror2"] = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"C_m2_{k}") for k in ("body_fm", "body_weight")}
    C["received2"] = gv(client, "NutritionRevamp.client.received", "C_recv2")


def phase_P():
    P = out["phases"]["P"] = {}
    P["sv_nutrition_server"] = ack(step("P_sv_s", server, "lua.global", "SandboxVars.Nutrition"))
    P["sv_nutrition_client"] = ack(step("P_sv_c", client, "lua.global", "SandboxVars.Nutrition"))
    P["nutritionOn"] = ack(step("P_on", server, "lua.global", "NutritionRevamp.server.options.nutritionOn"))
    P["preconditionWarnings"] = gv(server, f"{MSTATS}.preconditionWarnings", "P_warn")
    P["legacyMirror"] = gv(server, "NutritionRevamp.server.options.legacyMirror", "P_lm")
    P["sv_legacy"] = gv(server, "SandboxVars.NR.LegacyMirror", "P_svlm")
    P["nut_server"] = ack(step("P_nut_s", server, "nutrition.get", USER))
    P["strength0"] = {f: gv(server, f"{SSTATS}.{f}", f"P_str_{f}") for f in ("writes", "pushes", "bandRepairs")}
    P["perk"] = ack(step("P_perk", server, "perk.xp", f"{USER} Strength"))


def watch_boundary(F, tag, nxt, b_epoch_ms, slope, arm_trait):
    W = {"boundary_age": nxt, "boundary_epoch_ms_est": b_epoch_ms, "slope_h_per_ms": slope, "reads": []}
    lead_ms = b_epoch_ms - WATCH_LEAD_H / slope - time.time() * 1000.0
    if lead_ms > 0:
        time.sleep(lead_ms / 1000.0)
    W["str_pre"] = {f: gv(server, f"{SSTATS}.{f}", f"{tag}_strpre_{f}") for f in ("writes", "pushes")}
    W["w_pre"] = wstats(f"{tag}_wpre", ("bandChanges", "bandRepairs", "pushes"))
    if arm_trait:
        W["trait_watch_epoch"] = time.time()
        W["trait_watch_arm"] = ack(step(f"{tag}_twatch", client, "trait.watch", f"underweight {TRAIT_WATCH_S}"))
    i = 0
    while time.time() * 1000.0 < b_epoch_ms + WATCH_AFTER_S * 1000.0:
        W["reads"].append(pair(tag, i))
        i += 1
    W["body_post"] = body_read(f"{tag}_body")
    W["w_post"] = wstats(f"{tag}_wpost", ("bandChanges", "bandRepairs", "pushes", "pushMissing", "failures", "minutes"))
    W["str_post"] = {f: gv(server, f"{SSTATS}.{f}", f"{tag}_strpost_{f}") for f in ("writes", "pushes")}
    if arm_trait:
        try:
            W["trait_watch"] = client.bus.wait_result("trait-watch", timeout=TRAIT_WATCH_S + 5,
                                                      after=W["trait_watch_epoch"] - 0.5)
        except Exception as e:      # noqa: BLE001
            W["trait_watch"] = {"error": f"{type(e).__name__}: {e}"}
        time.sleep(3.0)
        W["followup"] = {"w": wstats(f"{tag}_fw", ("bandChanges", "bandRepairs", "pushes", "minutes")),
                         "pair": pair(f"{tag}_fu", 0), "body": body_read(f"{tag}_fbody")}
        time.sleep(3.0)
        W["followup2"] = {"w": wstats(f"{tag}_fw2", ("bandChanges", "bandRepairs", "pushes", "minutes")),
                          "pair": pair(f"{tag}_fu2", 0)}
    F["watches"].append(W)
    persist()
    return W


def lot_and_band(F):
    """Day 1 at speed 1: the lot arm (fm + LOT_DFM), then the band set-up (fm = BAND_TARGET_W - lm)."""
    L = F["lot"] = {}
    L["speed"] = speed(1, "lot_on")
    b0 = body_read("L_body0")
    L["body0"] = b0
    fm0, lm0 = bnum(b0["body"], "fm"), bnum(b0["body"], "lm")
    L["pre"] = pair("L_pre", 0)
    L["flagWrites0"] = gv(server, f"{WSTATS}.flagWrites", "L_fw0")
    L["set_lot"] = setpath("L_set", "fm", round(fm0 + LOT_DFM, 6))
    L["set_wall"] = wall()
    L["set_epoch"] = time.time()
    L["reads"] = []
    i = 0
    while wall() < L["set_wall"] + LOT_WATCH_S:
        L["reads"].append(pair("L", i))
        i += 1
    L["body_lot"] = body_read("L_body1")
    # the band set-up off the same record
    lm1 = bnum(L["body_lot"]["body"], "lm") or lm0
    L["band_fm"] = round(BAND_TARGET_W - lm1, 6)
    L["set_band"] = setpath("B_set", "fm", L["band_fm"])
    L["band_set_wall"] = wall()
    L["band_reads"] = []
    i = 0
    while wall() < L["band_set_wall"] + BAND_SET_WATCH_S:
        L["band_reads"].append(pair("Bs", i))
        i += 1
    L["body_band"] = body_read("B_body1")
    L["flagWrites1"] = gv(server, f"{WSTATS}.flagWrites", "L_fw1")
    L["speed_back"] = speed(SPEED, "lot_off")


def phase_fast():
    F = out["phases"]["FAST"] = {"cycles": [], "watches": [], "stop": None, "closes_seen": []}
    F["pins0"] = pins(0)
    F["speed"] = speed(SPEED, "fast_on")
    start = wall()
    prev_s = None
    n = 0
    close1_age, close2_age = None, None
    lot_done = False
    while True:
        n += 1
        cyc = {"n": n}
        s = stats(server, f"F{n}_s")
        cyc["server"] = s
        age, swall = to_num(s.get("worldAge")), to_num(s.get("wall"))
        slope = SPEED * 24.0 / (DAY_WALL_S_AT1 * 1000.0)
        if prev_s is not None and age is not None and swall is not None:
            a0, w0 = to_num(prev_s.get("worldAge")), to_num(prev_s.get("wall"))
            if a0 is not None and w0 is not None and swall > w0 and age > a0:
                slope = (age - a0) / (swall - w0)
        prev_s = s
        cyc["slope_h_per_ms"] = slope
        cyc["client"] = stats(client, f"F{n}_c")
        b = body_read(f"F{n}_body")
        cyc["body"] = b
        if n % WSTATS_EVERY == 0:
            cyc["w"] = wstats(f"F{n}_w", ("bandChanges", "bandRepairs", "pushes", "flagWrites", "mirrorWrites", "minutes"))
        if n % PIN_EVERY == 0:
            cyc["pins"] = pins(n)
        if n % HEALTH_EVERY == 0:
            cyc["health"] = chain_s(f"F{n}_hp", HEALTH_HOP)
            cyc["dead"] = chain_s(f"F{n}_dead", DEAD_HOP)
        F["cycles"].append(cyc)
        if n % 5 == 0:
            persist()
        hp = to_num((cyc.get("health") or {}).get("value"))
        if hp is not None and hp < HEALTH_FLOOR:
            F["stop"] = f"health {hp}"
            break
        if str((cyc.get("dead") or {}).get("value")).lower() == "true":
            F["stop"] = "dead"
            break
        if wall() - start > FAST_WALL_BUDGET_S:
            F["stop"] = "wall budget"
            break
        age = to_num(s.get("worldAge"))
        if age is None:
            time.sleep(CYCLE_GAP_S)
            continue
        if close2_age is not None and age >= close2_age + DAY2_AFTER_H:
            F["stop"] = "day 2 sampled"
            break
        nxt = (math.floor(age / 24) + 1) * 24.0
        if close1_age is not None and not lot_done and age >= close1_age + DAY1_LOT_AT_H:
            lot_and_band(F)
            lot_done = True
            prev_s = None
            continue
        b_epoch_ms = swall + (nxt - age) / slope
        to_b_ms = b_epoch_ms - time.time() * 1000.0
        if to_b_ms < 4000.0 + WATCH_LEAD_H / slope:
            if close1_age is None:
                watch_boundary(F, "W1", nxt, b_epoch_ms, slope, arm_trait=False)
                close1_age = nxt
                F["closes_seen"].append(nxt)
            elif lot_done and close2_age is None:
                watch_boundary(F, "W2", nxt, b_epoch_ms, slope, arm_trait=True)
                close2_age = nxt
                F["closes_seen"].append(nxt)
            else:
                note(f"boundary {nxt} reached out of plan (lot_done={lot_done}); watched without the trait")
                watch_boundary(F, f"Wx{n}", nxt, b_epoch_ms, slope, arm_trait=False)
                F["closes_seen"].append(nxt)
            prev_s = None
            continue
        time.sleep(CYCLE_GAP_S)
    F["speed_off"] = speed(1, "fast_off")
    F["end_body"] = body_read("F_end_body")
    F["end_pair"] = pair("F_end", 0)
    F["end_w"] = wstats("F_end_w")
    F["end_met"] = {f: gv(server, f"{MSTATS}.{f}", f"F_end_met_{f}") for f in ("days", "failures", "skippedDays", "badReads", "minutes", "firstSightMirrors")}
    F["end_str"] = {f: gv(server, f"{SSTATS}.{f}", f"F_end_str_{f}") for f in ("writes", "pushes", "bandRepairs")}
    F["end_health"] = chain_s("F_end_hp", HEALTH_HOP)


def wait_landing(tag, bulk0, timeout=60.0):
    end = wall() + timeout
    polls = []
    while wall() < end:
        b = body_read(f"{tag}_land", extra=(f"{USER}.stomach.bulk",))
        bulk = to_num(b.get(f"{USER}.stomach.bulk"))
        polls.append({"wall": b["wall_before"], "bulk": bulk, "fill": b["stomachFill"]})
        if bulk is not None and bulk0 is not None and bulk > bulk0 + 0.5:
            return {"landed": True, "polls": polls, "body": b, "wall": b["wall_after"]}
        time.sleep(0.4)
    return {"landed": False, "polls": polls}


def phase_E():
    E = out["phases"]["E"] = {"eats": [], "reads": []}
    E["pins"] = pins(900)
    E["foodtimer_read"] = stats(server, "E_pre_s")
    E["pre_body"] = body_read("E_pre_body", extra=(f"{USER}.stomach.bulk",))
    bulk0 = to_num(E["pre_body"].get(f"{USER}.stomach.bulk"))
    for item in BULK:
        e = {"item": item, "ack": ack(step(f"E_eat_{item}", client, "eat.action", f"{item} 1"))}
        e["landing"] = wait_landing(f"E_{item}", bulk0)
        lb = e["landing"].get("body") or {}
        if lb:
            bulk0 = to_num(lb.get(f"{USER}.stomach.bulk"))
        e["after"] = []
        for i in range(3):
            e["after"].append({"server": stats(server, f"E_{item}_s{i}"),
                               "body": body_read(f"E_{item}_b{i}", extra=(f"{USER}.stomach.bulk",))})
        E["eats"].append(e)
    for i in range(6):
        E["reads"].append({"body_a": body_read(f"E_ba{i}", extra=(f"{USER}.stomach.bulk",)),
                           "server": stats(server, f"E_s{i}"),
                           "body_b": body_read(f"E_bb{i}", extra=(f"{USER}.stomach.bulk",))})
        time.sleep(1.0)


def phase_M():
    M = out["phases"]["M"] = {}
    M["w0"] = wstats("M_w0", ("mirrorWrites", "minutes"))
    M["opt0"] = gv(server, "NutritionRevamp.server.options.legacyMirror", "M_opt0")
    # the discriminator with the mirror ON: an outside calories write is overwritten within a slow minute
    M["on_set"] = ack(step("M_on_set", server, "nutrition.set", f"{USER} calories {CAL_PROBE}"))
    M["on_set_wall"] = wall()
    M["on_reads"] = []
    while wall() < M["on_set_wall"] + 4.0:
        M["on_reads"].append({"wall": wall(), "server": ack(step("M_on_nut", server, "nutrition.get", USER))})
        time.sleep(0.3)
    M["on_body"] = body_read("M_on_body")
    M["w1"] = wstats("M_w1", ("mirrorWrites", "minutes"))
    # the flip
    M["var"] = ack(step("M_var", server, "sandbox.var", "NR.LegacyMirror false"))
    M["var_wall"] = wall()
    M["sv_after"] = gv(server, "SandboxVars.NR.LegacyMirror", "M_sv1")
    time.sleep(3.0)
    M["opt1"] = gv(server, "NutritionRevamp.server.options.legacyMirror", "M_opt1")
    M["readAt"] = gv(server, "NutritionRevamp.server.options.readAt", "M_readAt")
    M["w2"] = wstats("M_w2", ("mirrorWrites", "minutes"))
    M["off_set"] = ack(step("M_off_set", server, "nutrition.set", f"{USER} calories {CAL_PROBE}"))
    M["off_set_wall"] = wall()
    M["off_reads"] = []
    while wall() < M["off_set_wall"] + 15.0:
        M["off_reads"].append({"wall": wall(), "server": ack(step("M_off_nut", server, "nutrition.get", USER)),
                               "client": ack(step("M_off_cnut", client, "nutrition.get", ""))})
        time.sleep(1.0)
    M["w3"] = wstats("M_w3", ("mirrorWrites", "minutes"))
    M["off_body"] = body_read("M_off_body")


def phase_G():
    G = out["phases"]["G"] = {}
    G["t0"] = {f: gv(server, f"{TSTATS}.{f}", f"G_t0_{f}") for f in ("reps", "paired", "repsFitnessOnly", "ignored", "failures")}
    G["log_lines_before"] = count_log(READTYPE_RX)
    G["ex"] = ack(step("G_ex", client, "exercise.do", f"pushups {PUSHUP_MIN}"))
    time.sleep(PUSHUP_MIN * 0.625 + 6.0)
    G["t1"] = {f: gv(server, f"{TSTATS}.{f}", f"G_t1_{f}") for f in ("reps", "paired", "repsFitnessOnly", "ignored", "failures")}
    G["log_lines_after"] = count_log(READTYPE_RX)


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["reply"] = ack(step("Z_near", server, "zombie.near", "2"))
    time.sleep(3.0)
    Z["after"] = stats(server, "Z_s")


def count_log(rx):
    try:
        n = 0
        with open(server.log_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if rx.search(line):
                    n += 1
        return n
    except Exception as e:                     # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def sandbox_file():
    try:
        with open(server.sandbox_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        keep = [ln for ln in lines if re.match(r"^ {4}Nutrition = ", ln) or re.match(r"^ {4}DayLength = ", ln)]
        nr, inside = [], False
        for ln in lines:
            if re.match(r"^ {4}NR = \{", ln):
                inside = True
            if inside:
                nr.append(ln)
                if ln.strip() == "},":
                    inside = False
        return {"path": os.path.relpath(server.sandbox_path, REPO), "top": keep, "NR": nr}
    except Exception as e:                     # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- grading
def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def nearest_body(bodies, epoch):
    best = None
    for rb in bodies:
        if rb.get("body") is None:
            continue
        if best is None or abs(rb["epoch_before"] - epoch) < abs(best["epoch_before"] - epoch):
            best = rb
    return best


def grade_all():
    P = out["phases"]
    # ---- P ----
    Pp = P.get("P") or {}
    logs = out.get("logs") or {}
    obs = {"sv_server": (Pp.get("sv_nutrition_server") or {}).get("value"),
           "sv_client": (Pp.get("sv_nutrition_client") or {}).get("value"),
           "nutritionOn": (Pp.get("nutritionOn") or {}).get("value"),
           "preconditionWarnings": Pp.get("preconditionWarnings"), "precondition_log_lines": logs.get("precondition_lines"),
           "self_report": [x for x in (logs.get("server_nr") or []) if "nutritionOn" in str(x)],
           "sandbox_file": out.get("sandbox_file")}
    ok = (obs["sv_server"] is False and obs["nutritionOn"] is False and to_num(obs["preconditionWarnings"]) == 0
          and obs["precondition_log_lines"] == 0)
    grade("P", "Nutrition false on the server; nutritionOn false; 0 warnings; no warning line", obs,
          "as_predicted" if ok else "falsified", "any warning, nutritionOn true, or the option not false")
    # ---- C ----
    C = P.get("C") or {}
    b = (C.get("body_read") or {}).get("body") or {}
    m = C.get("mirror") or {}
    obs = {"mirror": m, "received": C.get("received"), "firstSightMirrors": C.get("firstSightMirrors"),
           "record_fm": bnum(b, "fm"), "record_w": mass(b), "mirror2": C.get("mirror2"), "received2": C.get("received2"),
           "body_seen_wall": C.get("body_seen_wall"), "mirror_wall": C.get("mirror_wall")}
    if not b:
        v = "unmeasured"
    else:
        v = "as_predicted" if (near(to_num(m.get("body_fm")), bnum(b, "fm"), 1e-6) and to_num(m.get("body_fm")) not in (None, 0.0)
                               and to_num(C.get("firstSightMirrors")) == 1) else "falsified"
    grade("C", "client mirror body_fm == record fm (non-zero) ~5 s after first sight with no harness re-request; "
               "firstSightMirrors 1", obs, v, "body_fm 0/absent")
    # ---- A0 / A1 flags ----
    F = P.get("FAST") or {}
    bodies = [c["body"] for c in F.get("cycles") or [] if c.get("body")]
    for W in F.get("watches") or []:
        bodies.append(W.get("body_post") or {})
    L = F.get("lot") or {}
    for k in ("body0", "body_lot", "body_band"):
        if L.get(k):
            bodies.append(L[k])
    close1 = (F.get("closes_seen") or [None])[0]
    day0, day1, mism = [], [], []
    lot_epoch = L.get("set_epoch")
    for c in F.get("cycles") or []:
        for side in ("server", "client"):
            s = c.get(side) or {}
            fl = [s.get("incWeight"), s.get("incWeightLot"), s.get("decWeight")]
            age_s = to_num((c.get("server") or {}).get("worldAge"))
            row = {"n": c["n"], "side": side, "age": age_s, "flags": fl}
            if close1 is not None and age_s is not None and age_s < close1:
                day0.append(row)
            elif close1 is not None and age_s is not None and age_s >= close1 and (lot_epoch is None or c["server"]["epoch_before"] < lot_epoch):
                day1.append(row)
        rb = c.get("body") or {}
        if rb.get("body"):
            exp, tr = flags_expected(rb["body"])
            s = c.get("server") or {}
            got = [s.get("incWeight"), s.get("incWeightLot"), s.get("decWeight")]
            if exp is not None and got != exp:
                mism.append({"n": c["n"], "server": got, "expected": exp, "trend": tr})
    obs = {"day0_samples": len(day0), "day0_any_true": [r for r in day0 if any(x is True for x in r["flags"])][:10],
           "day0_non_bool": [r for r in day0 if any(not isinstance(x, bool) for x in r["flags"])][:5]}
    v = "unmeasured" if not day0 else ("as_predicted" if not obs["day0_any_true"] and not obs["day0_non_bool"] else "falsified")
    grade("A0", "all three flags false on both sides at every day-0 sample", obs, v, "any flag true on day 0")
    W1 = next((W for W in F.get("watches") or [] if W.get("boundary_age") == close1), None)
    first_dec = {"server": None, "client": None}
    if W1:
        for r in W1.get("reads") or []:
            for side in ("server", "client"):
                s = r[side]
                if first_dec[side] is None and s.get("decWeight") is True:
                    first_dec[side] = s.get("wall")
    lat = {k: (to_num(v_) - W1["boundary_epoch_ms_est"]) if (W1 and v_ is not None) else None for k, v_ in first_dec.items()}
    d1_bad = [r for r in day1 if r["flags"] != [False, False, True]]
    obs = {"close1_age": close1, "first_dec_wall": first_dec, "first_dec_ms_after_boundary_est": lat,
           "day1_samples": len(day1), "day1_not_dec_only": d1_bad[:10], "server_vs_trend_mismatch": mism[:20],
           "server_vs_trend_mismatch_n": len(mism),
           "close1_body": (W1 or {}).get("body_post", {}).get("body") and {k: (W1["body_post"]["body"]).get(k) for k in ("fm", "lm", "fmRef", "at", "dayIndex", "mass7", "eb7")}}
    if not day1:
        v = "unmeasured"
    else:
        v = "as_predicted" if (not d1_bad and first_dec["server"] is not None and first_dec["client"] is not None) else "falsified"
    grade("A1", "dec true (inc, lot false) on both sides after close 1; server flags == the trend's at every sample",
          obs, v, "dec false on a side after the close, or a flag off the trend")
    # ---- L ----
    obs = {"set": L.get("set_lot"), "flagWrites": [L.get("flagWrites0"), L.get("flagWrites1")]}
    first = {"server": None, "client": None}
    for r in L.get("reads") or []:
        for side in ("server", "client"):
            s = r[side]
            if first[side] is None and s.get("incWeightLot") is True:
                first[side] = to_num(s.get("wall"))
    obs["first_lot_wall"] = first
    obs["first_lot_ms_after_set"] = {k: (v_ - L["set_epoch"] * 1000.0) if v_ is not None else None for k, v_ in first.items()} if L.get("set_epoch") else None
    lb = (L.get("body_lot") or {}).get("body")
    if lb:
        obs["expected_after_set"], obs["trend_after_set"] = flags_expected(lb)
    obs["reads_flags"] = [{"s": [r["server"].get(k) for k in ("incWeight", "incWeightLot", "decWeight")] + [r["server"].get("weight")],
                           "c": [r["client"].get(k) for k in ("incWeight", "incWeightLot", "decWeight")] + [r["client"].get("weight")]}
                          for r in L.get("reads") or []]
    if not (L.get("set_lot") or {}).get("ok"):
        v = "unmeasured"
    else:
        v = "as_predicted" if (first["server"] is not None and first["client"] is not None) else "falsified"
    grade("L", "lot true on the server after the fm edit, the client agreeing within 10 s (X25 #1291)", obs, v,
          "lot false on the server with trend > 0.10, or the client never agreeing")
    # ---- B ----
    W2 = next((W for W in F.get("watches") or [] if "followup" in W), None)
    if W2 is None:
        grade("B", "band crossing at close 2, bandChanges 1, the trait on both sides within 2 s, bandRepairs 0",
              {"note": "no close-2 watch", "stop": F.get("stop"), "set_band": L.get("set_band")}, "unmeasured", "no crossing")
    else:
        fs, fc = None, None
        for r in W2.get("reads") or []:
            if fs is None and "UNDERWEIGHT" in [str(x).upper() for x in (r["server"].get("traitList") or [])]:
                fs = to_num(r["server"].get("wall"))
            if fc is None and "UNDERWEIGHT" in [str(x).upper() for x in (r["client"].get("traitList") or [])]:
                fc = to_num(r["client"].get("wall"))
        tw = W2.get("trait_watch") or {}
        tws = to_num(tw.get("firstSeenWall")) if tw.get("found") else None
        fu, fu2 = W2.get("followup") or {}, W2.get("followup2") or {}
        bc = to_num((fu.get("w") or {}).get("bandChanges"))
        br2 = to_num((fu2.get("w") or {}).get("bandRepairs"))
        lat_c = (tws - fs) if (tws is not None and fs is not None) else None
        obs = {"w_pre": W2.get("w_pre"), "w_post": W2.get("w_post"), "followup_w": fu.get("w"), "followup2_w": fu2.get("w"),
               "str_pre": W2.get("str_pre"), "str_post": W2.get("str_post"),
               "band_post": ((W2.get("body_post") or {}).get("body") or {}).get("band"),
               "w_post_mass": mass((W2.get("body_post") or {}).get("body")),
               "server_first_seen_wall": fs, "client_poll_first_seen_wall": fc, "trait_watch": tw,
               "client_tick_minus_server_read_ms": lat_c,
               "client_poll_minus_server_read_ms": (fc - fs) if (fc is not None and fs is not None) else None,
               "boundary_epoch_ms_est": W2.get("boundary_epoch_ms_est"),
               "server_traits_fu2": (fu2.get("pair") or {}).get("server", {}).get("traitList"),
               "client_traits_fu2": (fu2.get("pair") or {}).get("client", {}).get("traitList")}
        ok = (bc == 1 and br2 == 0 and fs is not None and (tws is not None or fc is not None)
              and ((fc - fs) if fc is not None else (tws - fs)) <= 2000)
        grade("B", "band crossing at close 2: bandChanges 1, UNDERWEIGHT both sides, client <= 2 s after the server's "
                   "first read of it, bandRepairs 0 next minutes", obs, "as_predicted" if ok else "falsified",
              "bandChanges != 1, the trait absent on a side, latency > 2 s, bandRepairs > 0")
    # ---- E floor ----
    Eh = P.get("E") or {}
    rows = []
    reads = []
    for e in Eh.get("eats") or []:
        for r in e.get("after") or []:
            reads.append((r["server"], r["body"], r["body"]))
    for r in Eh.get("reads") or []:
        reads.append((r["server"], r["body_a"], r["body_b"]))
    for s, ba, bb in reads:
        h = to_num(s.get("hunger"))
        cands = []
        for rb in (ba, bb):
            es = bnum(rb.get("body"), "energyState")
            fill = rb.get("stomachFill")
            if es is None or fill is None:
                continue
            cands.append({"E": es, "fill": fill, "expected": clamp((1 - fill) * es + 0.15 * max(0.0, es - 1), 0, 1),
                          "no_floor": clamp((1 - fill) * es, 0, 1), "floor": 0.15 * max(0.0, es - 1)})
        match = any(near(h, c["expected"], 1e-4) for c in cands)
        rows.append({"hunger": h, "cands": cands, "match": match,
                     "match_no_floor": any(near(h, c["no_floor"], 1e-4) for c in cands)})
    full = [r for r in rows if r["cands"] and all(c["fill"] >= 1.0 for c in r["cands"])]
    obs = {"rows": rows, "eats": [{"item": e["item"], "ack": e["ack"], "landed": e["landing"].get("landed")} for e in Eh.get("eats") or []],
           "foodTimer_pre": (Eh.get("foodtimer_read") or {}).get("foodTimer")}
    if not full:
        v = "unmeasured"
    else:
        v = "as_predicted" if all(r["hunger"] is not None and r["hunger"] > 0 and r["match"] for r in full) else "falsified"
    grade("E", "at fill 1 hunger == 0.15(E-1) > 0 (and the full form at every read)", obs, v,
          "hunger 0 or the no-floor form at fill 1 with E > 1")
    # ---- M ----
    M = P.get("M") or {}
    w2, w3 = M.get("w2") or {}, M.get("w3") or {}
    on_cal = [to_num(r["server"].get("calories")) for r in M.get("on_reads") or []]
    off_cal = [to_num(r["server"].get("calories")) for r in M.get("off_reads") or []]
    off_ccal = [to_num((r.get("client") or {}).get("calories")) for r in M.get("off_reads") or []]
    obs = {"var": M.get("var"), "sv_after": M.get("sv_after"), "opt0": M.get("opt0"), "opt1": M.get("opt1"),
           "readAt": M.get("readAt"), "w0": M.get("w0"), "w1": M.get("w1"), "w2": w2, "w3": w3,
           "on_calories": on_cal, "off_calories": off_cal, "off_client_calories": off_ccal,
           "on_mirrorLast": ((M.get("on_body") or {}).get("body") or {}).get("mirrorLast")}
    mw2, mw3, mn2, mn3 = (to_num(w2.get("mirrorWrites")), to_num(w3.get("mirrorWrites")),
                          to_num(w2.get("minutes")), to_num(w3.get("minutes")))
    on_overwritten = bool(on_cal) and on_cal[-1] is not None and abs(on_cal[-1] - CAL_PROBE) > 1
    off_held = bool(off_cal) and all(near(c, CAL_PROBE, 1e-3) for c in off_cal)
    if not (M.get("var") or {}).get("ok") or M.get("opt1") is not False:
        v = "unmeasured"
    else:
        v = "as_predicted" if (mw2 == mw3 and mn3 is not None and mn2 is not None and mn3 > mn2 and on_overwritten and off_held) else "falsified"
    grade("M", "sandbox.var flips the option; mirrorWrites stops while minutes run; a calories write holds off, is "
               "overwritten on", obs, v, "mirrorWrites rising with the option false, or the write overwritten off")
    # ---- F blend ----
    rows, worst_h, worst_s, clock_match = [], 0.0, 0.0, 0
    for rb in bodies:
        bd = rb.get("body")
        if not bd:
            continue
        ex = blend_expect(bd)
        ml = bd.get("mirrorLast")
        cal = to_num(ml[0]) if isinstance(ml, list) and ml else None
        es = bnum(bd, "energyState")
        if ex is None or cal is None or es is None:
            continue
        dh, dc = abs(cal - ex["cal_hsc"]), abs(cal - ex["cal_clock"])
        worst_h = max(worst_h, dh)
        worst_s = max(worst_s, abs(es - ex["state_hsc"]))
        if dc < 0.5 and abs(ex["cal_hsc"] - ex["cal_clock"]) > 5:
            clock_match += 1
        rows.append({"tag": rb.get("tag"), "worldAge": rb.get("worldAge"), "hsc": ex["hsc"], "hod": ex["hod"],
                     "cal": cal, "cal_hsc": ex["cal_hsc"], "cal_clock": ex["cal_clock"], "E": es,
                     "E_hsc": ex["state_hsc"], "E_clock": ex["state_clock"]})
    disc = [r for r in rows if abs(r["cal_hsc"] - r["cal_clock"]) > 5]
    obs = {"n": len(rows), "n_discriminating": len(disc), "max_abs_cal_vs_hsc": worst_h, "max_abs_E_vs_hsc": worst_s,
           "clock_matches": clock_match, "sample": rows[::max(1, len(rows) // 25)]}
    if not disc:
        v = "unmeasured"
    else:
        v = "as_predicted" if (worst_h <= 0.5 and worst_s <= 1e-6 and clock_match == 0) else "falsified"
    grade("F", "mirrorLast[1] and energyState follow hours since close (0.5 kcal, 1e-6), not the clock", obs, v,
          "a read matching the clock form, or off the hsc form")
    # ---- G ----
    G = P.get("G") or {}
    r0, r1 = to_num((G.get("t0") or {}).get("reps")), to_num((G.get("t1") or {}).get("reps"))
    total = (out.get("logs") or {}).get("readtype_lines")
    obs = {"t0": G.get("t0"), "t1": G.get("t1"), "ex": G.get("ex"), "log_before": G.get("log_lines_before"),
           "log_after": G.get("log_lines_after"), "log_total_at_end": total}
    if r0 is None or r1 is None or r1 <= r0:
        v = "unmeasured"
    else:
        v = "as_predicted" if total == 0 else "falsified"
    grade("G", "reps rise and zero readType trace lines in the server log", obs, v, "any trace line")
    # ---- Z ----
    Z = P.get("Z") or {}
    rp = Z.get("reply") or {}
    dists = [to_num(x) for x in (rp.get("dists") or [])] if isinstance(rp.get("dists"), list) else []
    obs = {"reply": rp}
    v = "unmeasured" if not rp else ("as_predicted" if (rp.get("ok") and to_num(rp.get("spawned")) == 2 and dists
                                                         and all(d is not None and d <= 1.5 for d in dists)) else "falsified")
    grade("Z", "zombie.near 2: ok, spawned 2, every dist <= 1.5", obs, v, "fewer spawned or further")


def body():
    run_phase("C", phase_C)
    run_phase("P", phase_P)
    run_phase("FAST", phase_fast)
    try:
        if out["phases"].get("FAST", {}).get("speed_off") is None:
            out["speed_restore_after_fast"] = speed(1, "fast_restore")
    except Exception as e:                     # noqa: BLE001
        note(f"speed restore after the fast raised: {e}")
    run_phase("E", phase_E)
    run_phase("M", phase_M)
    run_phase("G", phase_G)
    run_phase("Z", phase_Z)


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x141b2-dry-run", None) if DRY_RUN else new_run_dir("x141b2")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_MetWatch"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "prior_run": PRIOR_RUN,
    "dry_run": DRY_RUN,
    "constants": {"SPEED": SPEED, "FAST_WALL_BUDGET_S": FAST_WALL_BUDGET_S, "HEALTH_FLOOR": HEALTH_FLOOR,
                  "PIN_EVERY": PIN_EVERY, "WATCH_LEAD_H": WATCH_LEAD_H, "WATCH_AFTER_S": WATCH_AFTER_S,
                  "TRAIT_WATCH_S": TRAIT_WATCH_S, "DAY1_LOT_AT_H": DAY1_LOT_AT_H, "DAY2_AFTER_H": DAY2_AFTER_H,
                  "LOT_DFM": LOT_DFM, "BAND_TARGET_W": BAND_TARGET_W, "BULK": list(BULK), "CAL_PROBE": CAL_PROBE,
                  "PUSHUP_MIN": PUSHUP_MIN},
    "deviations": [
        "Lot arm by the record edit (fm + 1.6 kg on day 1), not a feast: a feast's mass lands only at a day close "
        "and the trend reads against mass7[1] = 80, so no in-session feast reaches the +0.7 kg the lot flag needs.",
        "Band set-up edits fm, not lm (the amendments name lm): lm feeds the Strength ceiling, and a -5 kg lm edit "
        "would fire a Strength fall, its FEEBLE remap and its push in the band's minute; fatDep rises instead "
        "(read off the record in the floor arm).",
        "exercise.do pushups 20 game minutes, not 1 (x141c: 2 game minutes at DayLength 1 is shorter than one rep).",
        "Controls: thirst and fatigue pinned to 0 every third fast cycle; no food-timer write anywhere.",
        "Speed through RCON settimespeed (#1870). The flags are sampled (~every 2-3 s at speed 5), not read at "
        "every slow minute.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["the admin body record's fm edited twice", "a lettuce and a bread eaten",
                                        "SandboxVars.NR.LegacyMirror false on the server",
                                        "two zombies spawned beside the admin", "settimespeed returned to 1"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "phase_errors": {}, "speed_changes": [],
}

if DRY_RUN:
    print(json.dumps(out)[:3000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None)
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec)
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(client.mods_not_found))}
    persist()
    body()
    persist()
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    try:
        if server is not None:
            ok_r, rep_r = server.rcon("settimespeed 1")
            out["settimespeed_restored"] = str(rep_r) if ok_r else f"rcon failed: {rep_r}"
    except Exception as e:                     # noqa: BLE001
        out["settimespeed_restored"] = f"{type(e).__name__}: {e}"
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        if server is not None:
            out["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                           "server_nr": grep_file(server.log_path, NR_RX, NR_LIMIT),
                           "precondition_lines": count_log(PRECOND_RX),
                           "readtype_lines": count_log(READTYPE_RX),
                           "limits": {"luaerr": LUAERR_LIMIT, "nr": NR_LIMIT}}
            if clients:
                out["logs"].update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)})
            out["sandbox_file"] = sandbox_file()
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["grade_error"] = f"{type(e).__name__}: {e}"
            out["grade_tb"] = traceback.format_exc()[-2000:]
        out["summary"] = {
            "verify_ok": [v.get("ok") for v in out.get("verify", [])],
            "mods_not_found": out.get("mods_not_found"),
            "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
            "phase_errors": list(out["phase_errors"]),
        }
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error"),
                  "phase_errors": out.get("phase_errors")}, indent=1)[:7000])
