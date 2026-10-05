"""x141-body -- Plan 3 Task 18, acceptance 1 of the body model: the split at first sight, a timed fast
over accelerated game days (energy, partition, the weight slot on both sides, the direction flags),
the band crossing and its trait push, the weight re-assertion, the legacy macro mirror (on, then off
through the live sandbox option), the energy-state hunger floor, and the cost. ONE boot of profile
`x14-body` (PZTestKit + NutritionRevamp Mode 1 + LegacyMirror on + TKX_MetWatch) at DayLength 1 (a
game day is 15 wall minutes at speed 1, a game hour 37.5 s, a game minute 0.625 s). The run id
prefix is `x141b`. Copied from `x141_activity_gate.py` (provenance, wall-bracketed steps,
predictions/verdicts, `to_num`, the persist/step shape); each phase runs under its own try so one
phase's fault does not lose the others.

THE PREDICTED FAST (written before the run, from the committed kernels at 9768ce0; `predict()` below
is the same arithmetic and is re-run live from the first-sight record):
  Inputs: the fixture admin at 80 kg (every prior artifact reads 80), Strength 5, no build trait;
  idle and awake, so the server's metabolic rate reads 1.50 (x141a idle 300/300) -> class Default ->
  Compendium 1.3 MET -> activity 0.3 x w / 60 kcal per minute; not moving, so REE x the cold
  multiplier (taken as 1); AT starts 0 and steps only at a close under a deficit week (eb7 is all zero
  at the first close, so AT stays 0 through it). REE = 19.7 x LM + 413 (S0004). A day close pays the
  deficit from fat up to 69 kcal per kg fat (S0056) at RHO_FAT 9441 kcal/kg, the overflow from lean
  at RHO_LEAN 1816 kcal/kg with protection 1 (no strength dose, no protein: dStr 0, gProt 0).
  MALE 80 kg (bf 0.18): fm 14.400, lm 65.600; REE 1705.3 + activity 576.0 = 2281 kcal/d.
  First sight at world-age ~9 h (an assumption; the live prediction uses the real one), so the first
  close covers ~0.625 d:
     close  ee kcal   dFM      dLM      fm      lm      w
       1    1425.8  -0.1052  -0.2380  14.295  65.362  79.657
       2    2274.2  -0.1045  -0.7092  14.190  64.653  78.843
       3    2253.7  -0.1037  -0.7018  14.087  63.951  78.038
       4    2233.2  -0.1030  -0.6945  13.984  63.257  77.240
       5    2212.7  -0.1022  -0.6871  13.881  62.569  76.451
       6    2192.3  -0.1015  -0.6798  13.780  61.890  75.670
       7    2171.9  -0.1007  -0.6724  13.679  61.217  74.896  <- band normal -> underweight (w <= 75)
     a full fasting day costs ~0.81 kg (0.10 fat at the ceiling, 0.70 lean); three closes from first
     sight reach ~78.0 kg; the band crossing needs ~6.6 game days, the seventh close.
  FEMALE 80 kg (bf 0.28): fm 22.4, lm 57.6; ~0.48 kg/d; no crossing within nine closes.
  The fast therefore runs past three days until the band changes, nine closes, or a stop (below).
  Flags: mass7 starts all 80, so the trend (w - mass7[1]) / 7 is 0 until the first close and
  ~-0.049 kg/d after it -> decWeight true, incWeight/incWeightLot false (lot cannot rise in a fast:
  X25 #1291 is not exercised by this session).
  Energy state: eb24h <= -1500 from the second day -> E = 1.5 + 0.5 x fatDep ~ 1.51.

CONTROLS (not thumbs on the scale; none is an input of the body model): thirst and fatigue are
pinned to 0 at every sample (the unattended thirst drain kills, #0179; the fatigue pin keeps the
character awake and out of the Sleeping class); the health-from-food timer is written to 20000 every
few samples, because a level-4 HUNGRY moodle drains health at about 0.6 per game hour on this day
length (#0518 arithmetic) and the crossing sits at ~158 game hours: the timer's regeneration term
(#2385) keeps the subject alive. Health is read; a fast that reaches health 15 stops early.

SCHEDULE:
  A   first sight: the body record (witness.moddata of `admin.body`, raw; scalar strings beside it), the
      server's and the client's Nutrition weight, the client mirror before and after a re-request
      (`bench.global NutritionRevamp.client.requestMirror 1` on the client calls the mod's own
      request function once: the first-sight mirror is sent before the body exists).
  G1  cost at speed 1: `tick.rate 10` twice on the server; `bench.global NutritionRevamp.bench_fast
      100000` three times.
  D   re-assert at speed 1: `nutrition.set admin weight 120` on the server, then server/client reads
      for 90 s (dense for 10 s, then every 5 s).
  B/C the fast at RCON `settimespeed 5` (8 game minutes per wall second, the measured cadence ceiling
      on the 15-minute day, #1816): a cycle of server stats.get, the body read, the weight adapter's
      band counter, a client stats.get, the pins; at each day boundary a client-polled watch window
      from 0.4 game hours before to 10 s after the boundary with one server read inside it; the band
      watch (`trait.watch underweight`) armed before the boundary whose predicted close crosses 75 kg.
      Stops at the band change, nine closes, health < 15 or 45 wall minutes.
  F   speed 1: eat a lettuce then a bread (bulk 6.5 + 8.2 against FULL_BULK 8, so the fill sits at 1
      for about a game hour); server hunger beside the record's stomachFill and energyState.
  E1  mirror on, speed 1, after the eat: server nutrition.get beside the record's mirrorLast and the
      maps recomputed here from the record and the server's time of day.
  G2  cost again (post-fast).
  E0  `sandbox.set NR.LegacyMirror false` (the live server config); the mod polls options every slow
      minute (#2460); the mirror-write counter and the stores across an apple eat.

PREDICTIONS AND FALSIFIERS:
  A   fm + lm equals the server's weight read within 1e-3 and matches K.body.split(w, sex, build);
      l0 = the Strength level; the re-requested client mirror carries body_fm/lm/weight equal to the
      record's. Falsifier: a sum off by > 1e-3, or a mirror without the body keys.
  B   dayIndex advances >= 3; each closed day's eb7 slot < 0; fm and lm fall at every close; each
      close's dFM/dLM equals the partition law applied to the pre-close masses and the closed day's
      balance (eb7[7]) within 1e-6 kg; the trajectory sits within 10 % of the live prediction's
      per-close loss; server weight == fm + lm within 1e-3 at every same-day read; the client's
      weight equals it within 1e-3 at every read later than 2 s after the close; decWeight true on
      both sides after the first close. Falsifier: any of those reversed.
  C   at the close where w <= 75: weight.stats.bandChanges 0 -> 1, body.band "underweight", the trait
      on the server, the client sees it within 1 s of the boundary (the push, #2099); bandRepairs
      still 0 a slow minute later. `unmeasured` if no crossing.
  D   every server read after the set reads fm + lm (re-asserted within one slow minute); the
      first read is ~1.3 s (~2 game minutes) after the set. Falsifier: a server read of 120 later
      than 2 game minutes after the set.
  E1  the four stores equal mirrorLast at reads with no slow minute between (calories within 15 kcal
      across the read gap, the rest within 2 g / 2 units) and mirrorLast equals the maps of the record.
  E0  the option flips (SandboxVars.NR.LegacyMirror false, options.legacyMirror false) and
      mirrorWrites stops while weight.stats.minutes runs; the apple's vanilla eat additions persist.
      `unmeasured` if the live sandbox write does not reach SandboxVars.
  F   with fill 1, hunger == 0.15 x (E - 1) > 0 (the additive floor) to float precision. Falsifier:
      hunger 0 at fill 1 with E > 1.
  G   bench_fast within 25 % of 3.06 us (#2822) and tick rate within 5 % of 10.01 (#2823).

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
SESSION = ("Plan 3 acceptance 1: first-sight split, a timed fast over accelerated game days (energy, "
           "partition, weight both sides, flags), the band crossing and push, the weight re-assertion, "
           "the legacy mirror on and off, the energy-state hunger floor, cost; one boot of x14-body at "
           "DayLength 1")
ARTIFACT = "body.json"
USER = "admin"
ACCEPTANCE_RUN = "x141a-20261005-111005"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
BODY_KEY = f"{USER}.body"
WSTATS = "NutritionRevamp.server.weight.stats"
MSTATS = "NutritionRevamp.server.metabolism.stats"
HEALTH_HOP = "getBodyDamage.getOverallBodyHealth"
DEAD_HOP = "isDead"
RATE_HOP = "getBodyDamage.getThermoregulator.getMetabolicRate"
COLD_HOP = "getBodyDamage.getThermoregulator.getEnergyMultiplier"

SPEED = 5                      # settimespeed during the fast: 8 game-min per wall s on the 15-min day
DAY_WALL_S_AT1 = 900.0         # DayLength 1
MAX_CLOSES = 9
FAST_WALL_BUDGET_S = 45 * 60
HEALTH_FLOOR = 15.0
FOODTIMER = 20000
FOODTIMER_EVERY = 3
HEALTH_EVERY = 2
WATCH_LEAD_H = 0.4             # game hours before a boundary the watch starts
WATCH_AFTER_S = 10.0           # wall seconds after the boundary the watch runs
TRAIT_WATCH_S = 40
BAND_W = 75.0
D_SET = 120
D_DENSE_S, D_TOTAL_S, D_EVERY_S = 10.0, 90.0, 5.0
BENCH_N = 100000
TICK_S = 10
PLAN2_US, PLAN2_TPS = 3.06, 10.01
BULK = ("Base.Lettuce", "Base.Bread")
OFF_EAT = "Base.Apple"

# the kernel constants the prediction and the law checks recompute (committed values, 9768ce0)
REE_A, REE_B = 19.7, 413.0
FAT_CEIL, RHO_LEAN, RHO_FAT = 69.0, 1816.0, 9441.0
PROT_STR, PROT_P, PROT_FLOOR = 0.55, 0.15, 0.30
P_LO, P_HI = 0.8, 1.6
AT_MAX, AT_FULL_DEP, AT_TAU_ON, AT_TAU_OFF = 0.10, 0.5, 7.0, 14.0
IDLE_MET = 1.3
ANCHORS_W = (50, 60, 70, 80, 95, 105)
BF = {1: (0.06, 0.09, 0.13, 0.18, 0.27, 0.33), 2: (0.15, 0.19, 0.23, 0.28, 0.35, 0.40)}
BF_MIN, BF_MAX = {1: 0.04, 2: 0.12}, 0.55
BUILD_OFFSET = {"athletic": -0.04, "fit": -0.02, "outofshape": 0.02, "unfit": 0.04, "strong": -0.02,
                "stout": -0.01}

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
NR_RX = re.compile(r"\[NutritionRevamp\]")
LUAERR_LIMIT, NR_LIMIT = 40, 60


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


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "epoch_after": round(time.time(), 3), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def gv(side, name, tag):
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    return a.get("value") if a.get("resolved") else None


def chain_s(tag, hop):
    a = ack(step(tag, server, "witness.chain", f"{USER} {hop}"))
    return {"ok": a.get("ok"), "value": a.get("value"), "failedAt": a.get("failedAt")}


STAT_KEYS = ("weight", "incWeight", "incWeightLot", "decWeight", "hunger", "thirst", "fatigue", "calories",
             "proteins", "carbs", "lipids", "traitList", "worldAge", "wall", "mult", "asleep", "moving",
             "maxWeight", "foodTimer")


def sstats(tag):
    r = step(tag, server, "stats.get", USER)
    a = ack(r)
    d = {k: a.get(k) for k in STAT_KEYS}
    d["side"], d["wall_before"], d["wall_after"], d["epoch_before"] = "server", r["wall_before"], r["wall_after"], r["epoch_before"]
    return d


def cstats(tag):
    r = step(tag, client, "stats.get", "")
    a = ack(r)
    d = {k: a.get(k) for k in STAT_KEYS}
    d["side"], d["wall_before"], d["wall_after"], d["epoch_before"] = "client", r["wall_before"], r["wall_after"], r["epoch_before"]
    return d


def body_read(tag, extra=()):
    keys = [BODY_KEY, f"{USER}.stomachFill"] + list(extra)
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(keys))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    b = vals.get(BODY_KEY)
    rec = {"tag": tag, "wall_before": r["wall_before"], "wall_after": r["wall_after"],
           "worldAge": a.get("worldAge"), "body": b if isinstance(b, dict) else None,
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


def interp(w, sex):
    ys = BF[2] if sex == 2 else BF[1]
    bf = ys[0]
    for i in range(1, len(ANCHORS_W)):
        if w > ANCHORS_W[i - 1]:
            bf = ys[i - 1] + (ys[i] - ys[i - 1]) * (min(w, ANCHORS_W[i]) - ANCHORS_W[i - 1]) / (ANCHORS_W[i] - ANCHORS_W[i - 1])
    return bf


def split(w, sex, build):
    wc = min(max(w, 35.0), 200.0)
    off = sum(BUILD_OFFSET[k] for k in build)
    bf = min(max(interp(wc, sex) + off, BF_MIN.get(sex, 0.04)), BF_MAX)
    return wc * bf, wc - wc * bf, bf


def partition_deficit(fm, lm, eb, dstr=0.0, gprot=0.0):
    deficit = -eb
    from_fat = min(deficit, FAT_CEIL * fm)
    over = deficit - from_fat
    prot = min(max(1 - PROT_STR * dstr - PROT_P * gprot, PROT_FLOOR), 1)
    return -(from_fat + over * (1 - prot)) / RHO_FAT, -over / RHO_LEAN * prot


def predict(fm, lm, age0, closes=MAX_CLOSES, met=IDLE_MET, cold=1.0):
    """The a-priori fast from a first-sight record: the kernel's day arithmetic at the idle class."""
    fm_ref, at, eb7, rows = fm, 0.0, [0.0] * 7, []
    d0 = math.floor(age0 / 24)
    age = age0
    for k in range(closes):
        end = (d0 + k + 1) * 24.0
        frac = (end - age) / 24.0
        w = fm + lm
        ee = ((REE_A * lm + REE_B) * (1 - at) * cold + max(met - 1.0, 0) * w * 24) * frac
        dfm, dlm = partition_deficit(fm, lm, -ee)
        fm, lm = max(fm + dfm, 0.5), lm + dlm
        fm_ref = max(fm_ref, fm)
        tgt = AT_MAX * min(max(((fm_ref - fm) / fm_ref) / AT_FULL_DEP, 0), 1)
        at = at + (tgt - at) * (1 - math.exp(-1 / AT_TAU_ON)) if sum(eb7) < 0 else at * math.exp(-1 / AT_TAU_OFF)
        eb7 = eb7[1:] + [-ee]
        rows.append({"close": d0 + k + 1, "frac": round(frac, 4), "ee": round(ee, 2), "dFM": round(dfm, 5),
                     "dLM": round(dlm, 5), "fm": round(fm, 4), "lm": round(lm, 4), "w": round(fm + lm, 4),
                     "at": round(at, 6)})
        age = end
    return rows


def map_cal(eb):
    return min(max(eb, -2200), 3700)


def map_prot(p):
    if p <= 0.5:
        m = -400
    elif p < 0.8:
        m = -300 + 300 * (p - 0.5) / 0.3
    elif p <= 1.6:
        m = 150 * (p - 0.8) / 0.8
    else:
        m = 200
    return min(max(m, -500), 1000)


def mirror_expect(b, hod):
    rest = 1 - hod / 24
    w = mass(b)
    eb24 = bnum(b, "ebDay") + ring(b, "eb7", 7) * rest
    p24 = (bnum(b, "pDay") + ring(b, "p7", 7) * rest) / w
    c24 = bnum(b, "carbDay") + ring(b, "carb7", 7) * rest
    l24 = bnum(b, "lipDay") + ring(b, "lip7", 7) * rest
    return {"calories": map_cal(eb24), "proteins": map_prot(p24),
            "carbs": min(max(c24 - 300, -500), 1000), "lipids": min(max(l24 - 70, -500), 1000)}


def tick_rate(label):
    after = time.time()
    arm = ack(step(f"{label}_tick_arm", server, "tick.rate", str(TICK_S)))
    res = None
    if arm.get("armed"):
        try:
            res = server.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 20, after=after)
        except (RuntimeError, TimeoutError, OSError) as e:
            res = {"error": f"{type(e).__name__}: {e}"}
    return {"arm": arm, "result": res,
            "ticksPerSecond": res.get("ticksPerSecond") if isinstance(res, dict) else None,
            "worldMinutesPerSecond": res.get("worldMinutesPerSecond") if isinstance(res, dict) else None}


def cost(label):
    G = {"tick": [tick_rate(f"{label}a"), tick_rate(f"{label}b")], "bench": []}
    for i in range(3):
        G["bench"].append(ack(step(f"{label}_bench{i}", server, "bench.global",
                                   f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60)))
    return G


def speed(n, tag):
    ok, rep = server.rcon(f"settimespeed {n}")
    row = {"wall": wall(), "n": n, "ok": ok, "reply": str(rep)[:200]}
    out["speed_changes"].append(row)
    tl.mark("speed", n=n, ok=ok)
    row["server_snap"] = ack(step(f"{tag}_snap_s", server, "time.snapshot", ""))
    row["client_snap"] = ack(step(f"{tag}_snap_c", client, "time.snapshot", ""))
    return row


def wstats(tag, fields=("bandChanges", "bandRepairs", "pushes", "pushMissing", "minutes", "weightWrites",
                        "mirrorWrites", "failures")):
    return {f: gv(server, f"{WSTATS}.{f}", f"{tag}_{f}") for f in fields}


def run_phase(name, fn):
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    persist()


# ---------------------------------------------------------------- phases
def phase_A():
    A = out["phases"]["A"] = {"waits": []}
    end = wall() + 60
    b = None
    while wall() < end:
        b = body_read("A_wait")
        A["waits"].append({"wall": b["wall_before"], "has_body": b["body"] is not None})
        if b["body"] is not None:
            break
        time.sleep(1.0)
    A["body_read"] = b
    A["scalars"] = ack(step("A_scalars", server, "witness.moddata",
                            f"global:{STORE} {BODY_KEY}.fm {BODY_KEY}.lm {BODY_KEY}.l0 {BODY_KEY}.traitCarry "
                            f"{BODY_KEY}.sex {BODY_KEY}.band {BODY_KEY}.dayIndex {BODY_KEY}.r"))
    A["server_nut"] = ack(step("A_nut_s", server, "nutrition.get", USER))
    A["client_nut"] = ack(step("A_nut_c", client, "nutrition.get", ""))
    A["server_stats"] = sstats("A_stats_s")
    A["perk"] = ack(step("A_perk", server, "perk.xp", f"{USER} Strength"))
    A["met_stats"] = {f: gv(server, f"{MSTATS}.{f}", f"A_met_{f}") for f in ("splits", "failures", "minutes", "days")}
    A["met_lastError"] = gv(server, "NutritionRevamp.server.metabolism.lastError", "A_met_err")
    A["wstats"] = wstats("A_w")
    A["rate"] = chain_s("A_rate", RATE_HOP)
    A["cold"] = chain_s("A_cold", COLD_HOP)
    mk = ("body_fm", "body_lm", "body_weight", "body_band", "body_energyState")
    A["mirror_before"] = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"A_mb_{k}") for k in mk}
    A["mirror_received_before"] = gv(client, "NutritionRevamp.client.received", "A_mrb")
    A["request"] = ack(step("A_request", client, "bench.global", "NutritionRevamp.client.requestMirror 1"))
    time.sleep(2.5)
    A["mirror_received_after"] = gv(client, "NutritionRevamp.client.received", "A_mra")
    A["mirror_after"] = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"A_ma_{k}") for k in mk}
    body = (b or {}).get("body")
    if body:
        out["prediction_live"] = predict(bnum(body, "fm"), bnum(body, "lm"), to_num(body.get("bornAge")) or 0.0)


def phase_G(label):
    out["phases"][label] = cost(label)


def phase_D():
    D = out["phases"]["D"] = {"reads": []}
    D["w0"] = wstats("D_w0", ("weightWrites", "bandRepairs", "bandChanges", "minutes"))
    D["body0"] = body_read("D_body0")
    D["snap0"] = ack(step("D_snap0", server, "time.snapshot", ""))
    r = step("D_set", server, "nutrition.set", f"{USER} weight {D_SET}")
    D["set"] = {"ack": ack(r), "wall_before": r["wall_before"], "wall_after": r["wall_after"]}
    t_set = r["wall_after"]
    i = 0
    while wall() < t_set + D_TOTAL_S:
        s = sstats(f"D_s{i}")
        c = cstats(f"D_c{i}")
        D["reads"].append({"i": i, "server": s, "client": c})
        i += 1
        if wall() > t_set + D_DENSE_S:
            time.sleep(max(0.0, D_EVERY_S - 1.6))
    D["w1"] = wstats("D_w1", ("weightWrites", "bandRepairs", "bandChanges", "minutes"))
    D["body1"] = body_read("D_body1")


def pins(n):
    p = {"stats": ack(step(f"pin{n}", server, "stats.set", f"{USER} thirst 0 fatigue 0"))}
    if n % FOODTIMER_EVERY == 0:
        p["foodtimer"] = ack(step(f"ft{n}", server, "foodtimer.set", f"{USER} {FOODTIMER}"))
    return p


def phase_fast():
    F = out["phases"]["FAST"] = {"cycles": [], "watches": [], "closes": [], "bodies": [], "stop": None}
    F["pins0"] = pins(0)
    F["speed"] = speed(SPEED, "fast_on")
    start = wall()
    prev_s, last_body = None, None
    seen_days = []
    band_done = False
    n = 0
    armed_for = None
    cycle_ms = 10000.0

    def see(b):
        F["bodies"].append(b)
        day = to_num((b.get("body") or {}).get("dayIndex"))
        if day is not None and (not seen_days or day != seen_days[-1]):
            seen_days.append(day)
            F["closes"].append({"dayIndex": day, "wall": b["wall_before"], "worldAge": b["worldAge"],
                                "body": b.get("body")})

    while True:
        n += 1
        c_start = time.time()
        cyc = {"n": n}
        watched = False
        s = sstats(f"F{n}_s")
        cyc["server"] = s
        age = to_num(s.get("worldAge"))
        swall = to_num(s.get("wall"))
        # the game-hours-per-wall-ms slope off consecutive server reads (fallback the nominal)
        slope = SPEED * 24.0 / (DAY_WALL_S_AT1 * 1000.0)
        if prev_s is not None and age is not None and swall is not None:
            a0, w0 = to_num(prev_s.get("worldAge")), to_num(prev_s.get("wall"))
            if a0 is not None and w0 is not None and swall > w0 and age > a0:
                slope = (age - a0) / (swall - w0)
        cyc["slope_h_per_ms"] = slope
        prev_s = s
        if age is not None and swall is not None:
            nxt = (math.floor(age / 24) + 1) * 24.0
            b_epoch_ms = swall + (nxt - age) / slope
            to_b_ms = b_epoch_ms - time.time() * 1000.0
            if to_b_ms < cycle_ms * 1.3 + 2000.0:
                # ---- the boundary watch: the boundary falls before the next cycle's server read ----
                watched = True
                W = {"boundary_age": nxt, "server_pre": s, "client": [], "server_in": None,
                     "boundary_epoch_ms_est": b_epoch_ms, "slope_h_per_ms": slope}
                pred_w = None
                if last_body and last_body.get("body") and last_body.get("worldAge") is not None:
                    lb = last_body["body"]
                    eb_est = bnum(lb, "ebDay")
                    if eb_est is not None:
                        rem_h = nxt - to_num(last_body["worldAge"])
                        ee_rate = ((REE_A * bnum(lb, "lm") + REE_B) * (1 - (bnum(lb, "at") or 0))
                                   + (IDLE_MET - 1) * mass(lb) * 24) / 24.0
                        dfm, dlm = partition_deficit(bnum(lb, "fm"), bnum(lb, "lm"), eb_est - ee_rate * rem_h)
                        pred_w = mass(lb) + dfm + dlm
                W["pred_w_after"] = pred_w
                lead_ms = b_epoch_ms - WATCH_LEAD_H / slope - time.time() * 1000.0
                if lead_ms > 0:
                    time.sleep(lead_ms / 1000.0)
                if pred_w is not None and pred_w <= BAND_W + 0.3 and armed_for != nxt:
                    W["trait_watch_epoch"] = time.time()
                    W["trait_watch_arm"] = ack(step(f"W{n}_twatch", client, "trait.watch", f"underweight {TRAIT_WATCH_S}"))
                    armed_for = nxt
                server_done = False
                while time.time() * 1000.0 < b_epoch_ms + WATCH_AFTER_S * 1000.0:
                    W["client"].append(cstats(f"W{n}_c"))
                    if not server_done and time.time() * 1000.0 > b_epoch_ms + 300:
                        W["server_in"] = sstats(f"W{n}_s_in")
                        W["bandChanges_in"] = gv(server, f"{WSTATS}.bandChanges", f"W{n}_bc_in")
                        server_done = True
                W["server_post"] = sstats(f"W{n}_s_post")
                W["body_post"] = body_read(f"W{n}_body")
                see(W["body_post"])
                W["wstats_post"] = wstats(f"W{n}_w", ("bandChanges", "bandRepairs", "pushes", "pushMissing", "failures"))
                if "trait_watch_arm" in W:
                    try:
                        W["trait_watch"] = client.bus.wait_result("trait-watch", timeout=TRAIT_WATCH_S + 5,
                                                                  after=W["trait_watch_epoch"] - 0.5)
                    except Exception as e:      # noqa: BLE001
                        W["trait_watch"] = {"error": f"{type(e).__name__}: {e}"}
                F["watches"].append(W)
                last_body = W["body_post"]
                bc = to_num((W["wstats_post"] or {}).get("bandChanges")) or 0
                bb = (last_body.get("body") or {}).get("band")
                if bc >= 1 or (bb is not None and bb != "normal"):
                    # ---- the band follow-up: later slow minutes, the repair counter ----
                    time.sleep(3.0)
                    W["followup"] = {"wstats": wstats(f"W{n}_fw", ("bandChanges", "bandRepairs", "pushes")),
                                     "server": sstats(f"W{n}_fs"), "client": cstats(f"W{n}_fc")}
                    band_done = True
                persist()
        if not band_done:
            b = body_read(f"F{n}_body")
            cyc["body"] = b
            last_body = b
            see(b)
            cyc["client"] = cstats(f"F{n}_c")
            cyc["bandChanges"] = gv(server, f"{WSTATS}.bandChanges", f"F{n}_bc")
            if n % HEALTH_EVERY == 0:
                cyc["health"] = chain_s(f"F{n}_hp", HEALTH_HOP)
                cyc["dead"] = chain_s(f"F{n}_dead", DEAD_HOP)
            if n % 6 == 0:
                cyc["rate"] = chain_s(f"F{n}_rate", RATE_HOP)
                cyc["cold"] = chain_s(f"F{n}_cold", COLD_HOP)
            cyc["pins"] = pins(n)
            if not watched:
                cycle_ms = (time.time() - c_start) * 1000.0
        cyc["cycle_ms_est"] = cycle_ms
        cyc["watched"] = watched
        F["cycles"].append(cyc)
        if n % 5 == 0:
            persist()
        hp = to_num((cyc.get("health") or {}).get("value"))
        if band_done:
            F["stop"] = "band changed"
            break
        if len(seen_days) - 1 >= MAX_CLOSES:
            F["stop"] = f"{MAX_CLOSES} closes"
            break
        if hp is not None and hp < HEALTH_FLOOR:
            F["stop"] = f"health {hp}"
            break
        if str((cyc.get("dead") or {}).get("value")).lower() == "true":
            F["stop"] = "dead"
            break
        if wall() - start > FAST_WALL_BUDGET_S:
            F["stop"] = "wall budget"
            break
    F["seen_days"] = seen_days
    F["speed_off"] = speed(1, "fast_off")
    F["end_body"] = body_read("F_end_body")
    F["end_server"] = sstats("F_end_s")
    F["end_client"] = cstats("F_end_c")
    F["end_wstats"] = wstats("F_end_w")
    F["end_met"] = {f: gv(server, f"{MSTATS}.{f}", f"F_end_met_{f}") for f in ("days", "failures", "skippedDays", "badReads", "minutes")}
    F["end_health"] = chain_s("F_end_hp", HEALTH_HOP)


def wait_landing(tag, bulk0, timeout=60.0):
    end = wall() + timeout
    polls = []
    while wall() < end:
        b = body_read(f"{tag}_land", extra=(f"{USER}.stomach.bulk",))
        bulk = to_num(b.get(f"{USER}.stomach.bulk"))
        polls.append({"wall": b["wall_before"], "bulk": bulk, "fill": b["stomachFill"]})
        if bulk is not None and bulk0 is not None and bulk > bulk0 + 0.5:
            return {"landed": True, "polls": polls, "body": b}
        time.sleep(0.5)
    return {"landed": False, "polls": polls}


def phase_F():
    P = out["phases"]["F"] = {"eats": [], "reads": []}
    P["pins"] = pins(0)
    P["pre"] = {"server": sstats("Fh_pre_s"), "body": body_read("Fh_pre_body", extra=(f"{USER}.stomach.bulk",))}
    bulk0 = to_num(P["pre"]["body"].get(f"{USER}.stomach.bulk"))
    for item in BULK:
        e = {"item": item, "ack": ack(step(f"Fh_eat_{item}", client, "eat.action", f"{item} 1"))}
        e["landing"] = wait_landing(f"Fh_{item}", bulk0)
        lb = (e["landing"].get("body") or {})
        bulk0 = to_num(lb.get(f"{USER}.stomach.bulk")) if lb else bulk0
        P["eats"].append(e)
    for i in range(4):
        s = sstats(f"Fh_s{i}")
        b = body_read(f"Fh_b{i}", extra=(f"{USER}.stomach.bulk",))
        P["reads"].append({"server": s, "body": b})


def phase_E1():
    E = out["phases"]["E1"] = {"reads": []}
    E["wstats0"] = wstats("E1_w0", ("mirrorWrites", "minutes"))
    for i in range(6):
        snap = ack(step(f"E1_snap{i}", server, "time.snapshot", ""))
        nut = ack(step(f"E1_nut{i}", server, "nutrition.get", USER))
        b = body_read(f"E1_body{i}")
        cn = ack(step(f"E1_cnut{i}", client, "nutrition.get", ""))
        E["reads"].append({"snap": snap, "nut": nut, "body": b, "client_nut": cn})
        time.sleep(1.5)
    E["wstats1"] = wstats("E1_w1", ("mirrorWrites", "minutes"))


def phase_E0():
    E = out["phases"]["E0"] = {"reads": []}
    E["sv_before"] = gv(server, "SandboxVars.NR.LegacyMirror", "E0_sv0")
    E["opt_before"] = gv(server, "NutritionRevamp.server.options.legacyMirror", "E0_opt0")
    E["set"] = ack(step("E0_set", server, "sandbox.set", "NR.LegacyMirror false"))
    E["sv_after"] = gv(server, "SandboxVars.NR.LegacyMirror", "E0_sv1")
    time.sleep(3.0)
    E["opt_after"] = gv(server, "NutritionRevamp.server.options.legacyMirror", "E0_opt1")
    E["opt_readAt"] = gv(server, "NutritionRevamp.server.options.readAt", "E0_readAt")
    E["wstats0"] = wstats("E0_w0", ("mirrorWrites", "minutes"))
    E["nut0"] = ack(step("E0_nut0", server, "nutrition.get", USER))
    E["body0"] = body_read("E0_body0")
    E["eat"] = ack(step("E0_eat", client, "eat.action", f"{OFF_EAT} 1"))
    end = wall() + 25
    i = 0
    while wall() < end:
        E["reads"].append({"nut": ack(step(f"E0_nut{i + 1}", server, "nutrition.get", USER)),
                           "wall": wall()})
        i += 1
        time.sleep(1.0)
    E["wstats1"] = wstats("E0_w1", ("mirrorWrites", "minutes"))
    E["body1"] = body_read("E0_body1")


# ---------------------------------------------------------------- grading
def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def grade_all():
    P = out["phases"]
    # ---- A ----
    A = P.get("A") or {}
    b = ((A.get("body_read") or {}).get("body")) or {}
    obs = {}
    v = "unmeasured"
    if b:
        w_s = to_num((A.get("server_nut") or {}).get("weight"))
        sex = int(bnum(b, "sex") or 1)
        tl_ = [str(x).lower() for x in ((A.get("server_stats") or {}).get("traitList") or [])]
        build = [k for k in BUILD_OFFSET if k in tl_]
        fm_e, lm_e, bf = split(w_s if w_s is not None else 80.0, sex, build)
        ma = A.get("mirror_after") or {}
        obs = {"fm": bnum(b, "fm"), "lm": bnum(b, "lm"), "sum": mass(b), "server_weight": w_s,
               "client_weight": to_num((A.get("client_nut") or {}).get("weight")), "sex": sex, "build": build,
               "split_expected": [fm_e, lm_e, bf], "l0": bnum(b, "l0"), "perk_level": (A.get("perk") or {}).get("level"),
               "traitCarry": bnum(b, "traitCarry"), "band": b.get("band"), "dayIndex": bnum(b, "dayIndex"),
               "bornAge": bnum(b, "bornAge"), "r": bnum(b, "r"), "scalars_strings": (A.get("scalars") or {}).get("values"),
               "mirror_before": A.get("mirror_before"), "mirror_after": ma}
        ok_sum = near(mass(b), w_s, 1e-3)
        ok_split = near(bnum(b, "fm"), fm_e, 1e-6) and near(bnum(b, "lm"), lm_e, 1e-6)
        ok_mirror = near(to_num(ma.get("body_weight")), mass(b), 1e-6) and near(to_num(ma.get("body_fm")), bnum(b, "fm"), 1e-6)
        obs.update({"ok_sum": ok_sum, "ok_split": ok_split, "ok_mirror": ok_mirror})
        v = "as_predicted" if (ok_sum and ok_split and ok_mirror) else "falsified"
    grade("A", "fm+lm = server weight (1e-3), = K.body.split; the re-requested client mirror carries body_fm/lm/weight",
          obs, v, "a sum off by > 1e-3, a split mismatch, or a mirror without the body keys")
    # ---- B ----
    F = P.get("FAST") or {}
    closes = F.get("closes") or []
    pre = {}
    for rd in F.get("bodies") or []:
        bd = rd.get("body")
        if bd:
            pre[bnum(bd, "dayIndex")] = bd       # the LAST read of each day (masses are constant within a day)
    law, traj = [], []
    for c in closes[1:]:
        d = bnum(c["body"], "dayIndex")
        prev = pre.get(d - 1)
        if not prev:
            continue
        eb = ring(c["body"], "eb7", 7)
        dfm_e, dlm_e = partition_deficit(bnum(prev, "fm"), bnum(prev, "lm"), eb) if eb is not None and eb < 0 else (None, None)
        dfm, dlm = bnum(c["body"], "fm") - bnum(prev, "fm"), bnum(c["body"], "lm") - bnum(prev, "lm")
        law.append({"dayIndex": d, "eb_closed": eb, "dFM": dfm, "dLM": dlm, "dFM_law": dfm_e, "dLM_law": dlm_e,
                    "ok": near(dfm, dfm_e, 1e-6) and near(dlm, dlm_e, 1e-6), "fm": bnum(c["body"], "fm"),
                    "lm": bnum(c["body"], "lm"), "w": mass(c["body"]), "at": bnum(c["body"], "at"),
                    "energyState": bnum(c["body"], "energyState"), "eeDay_prev_day": eb})
    pl = out.get("prediction_live") or []
    for row in law:
        pr = next((p for p in pl if p["close"] == row["dayIndex"]), None)
        if pr:
            dw_o, dw_p = row["dFM"] + row["dLM"], pr["dFM"] + pr["dLM"]
            traj.append({"dayIndex": row["dayIndex"], "dw_obs": dw_o, "dw_pred": dw_p, "w_obs": row["w"], "w_pred": pr["w"],
                         "rel": (dw_o - dw_p) / dw_p if dw_p else None})
    same_day, cl_ok, flags = [], [], []
    for cyc in F.get("cycles") or []:
        s, bd, c = cyc.get("server") or {}, (cyc.get("body") or {}), cyc.get("client") or {}
        body = bd.get("body")
        if not body:
            continue
        sa, ba = to_num(s.get("worldAge")), to_num(bd.get("worldAge"))
        if sa is not None and ba is not None and math.floor(sa / 24) == math.floor(ba / 24):
            same_day.append({"n": cyc["n"], "server_weight": to_num(s.get("weight")), "fm_lm": mass(body),
                             "ok": near(to_num(s.get("weight")), mass(body), 1e-3)})
            cl_ok.append({"n": cyc["n"], "client_weight": to_num(c.get("weight")), "fm_lm": mass(body),
                          "ok": near(to_num(c.get("weight")), mass(body), 1e-3)})
        flags.append({"n": cyc["n"], "dayIndex": bnum(body, "dayIndex"),
                      "server": [s.get("incWeight"), s.get("incWeightLot"), s.get("decWeight")],
                      "client": [c.get("incWeight"), c.get("incWeightLot"), c.get("decWeight")]})
    first_day = bnum(closes[0]["body"], "dayIndex") if closes else None
    after = [f for f in flags if first_day is not None and f["dayIndex"] is not None and f["dayIndex"] > first_day]
    dec_ok = bool(after) and all(f["server"][2] is True and f["client"][2] is True for f in after)
    lot_seen = any(f["server"][1] is True or f["client"][1] is True for f in flags)
    obs = {"closes": len(closes) - 1 if closes else 0, "law": law, "trajectory": traj,
           "eb7_negative": all((r["eb_closed"] or 0) < 0 for r in law) if law else None,
           "masses_fell": all(r["dFM"] < 0 and r["dLM"] < 0 for r in law) if law else None,
           "server_weight_same_day_ok": [x["ok"] for x in same_day].count(True), "server_weight_n": len(same_day),
           "client_weight_same_day_ok": [x["ok"] for x in cl_ok].count(True), "client_weight_n": len(cl_ok),
           "server_weight_bad": [x for x in same_day if not x["ok"]][:10],
           "client_weight_bad": [x for x in cl_ok if not x["ok"]][:10],
           "dec_after_first_close_both": dec_ok, "lot_ever_true": lot_seen, "stop": F.get("stop")}
    if not law:
        v = "unmeasured"
    elif (len(closes) - 1 >= 3 and obs["eb7_negative"] and obs["masses_fell"] and all(r["ok"] for r in law)
          and all(abs(t["rel"]) <= 0.10 for t in traj if t["rel"] is not None) and dec_ok
          and obs["server_weight_same_day_ok"] == obs["server_weight_n"]):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("B", ">=3 closes; eb7<0; fm,lm fall; partition law exact (1e-6); per-close loss within 10% of the live "
               "prediction; server weight == fm+lm (1e-3); dec true both sides after the first close",
          obs, v, "any of the predicted relations reversed")
    # ---- watches: the client cadence of a server weight write ----
    cad = []
    for W in F.get("watches") or []:
        pre_w = to_num((W.get("server_pre") or {}).get("weight"))
        post_w = to_num((W.get("server_post") or {}).get("weight"))
        first = None
        for c in W.get("client") or []:
            cw = to_num(c.get("weight"))
            if post_w is not None and pre_w is not None and abs(post_w - pre_w) > 1e-3 and near(cw, post_w, 1e-3):
                first = c
                break
        lat = (to_num(first.get("wall")) - W["boundary_epoch_ms_est"]) if first and first.get("wall") is not None else None
        cad.append({"boundary_age": W["boundary_age"], "server_pre": pre_w, "server_post": post_w,
                    "client_first_new_wall": first.get("wall") if first else None, "latency_ms_from_boundary_est": lat,
                    "client_flags_at_first": [first.get("incWeight"), first.get("incWeightLot"), first.get("decWeight")] if first else None,
                    "n_client_reads": len(W.get("client") or [])})
    out["cadence"] = cad
    # ---- C ----
    band_w = next((W for W in F.get("watches") or [] if "followup" in W), None)
    if band_w is None:
        grade("C", "bandChanges 0->1 at the crossing close, the trait both sides, client within 1 s; bandRepairs 0",
              {"note": "no band change during the fast", "stop": F.get("stop")}, "unmeasured", "no crossing")
    else:
        fu = band_w["followup"]
        tw = band_w.get("trait_watch") or {}
        lat = None
        if tw.get("found") and tw.get("firstSeenWall") is not None:
            lat = to_num(tw["firstSeenWall"]) - band_w["boundary_epoch_ms_est"]
        s_tl = [str(x).lower() for x in ((fu.get("server") or {}).get("traitList") or [])]
        c_tl = [str(x).lower() for x in ((fu.get("client") or {}).get("traitList") or [])]
        first_c = next((c for c in band_w.get("client") or []
                        if "underweight" in [str(x).lower() for x in (c.get("traitList") or [])]), None)
        obs = {"bandChanges_in": band_w.get("bandChanges_in"), "wstats_post": band_w.get("wstats_post"), "followup_wstats": fu.get("wstats"),
               "band_post": ((band_w.get("body_post") or {}).get("body") or {}).get("band"),
               "server_traits": s_tl, "client_traits": c_tl, "trait_watch": tw, "latency_ms_trait_watch": lat,
               "client_poll_first_seen_wall": first_c.get("wall") if first_c else None,
               "latency_ms_client_poll": (to_num(first_c.get("wall")) - band_w["boundary_epoch_ms_est"]) if first_c else None,
               "w_post": mass((band_w.get("body_post") or {}).get("body"))}
        bc = to_num((fu.get("wstats") or {}).get("bandChanges"))
        br = to_num((fu.get("wstats") or {}).get("bandRepairs"))
        ok = (bc == 1 and br == 0 and "underweight" in s_tl and "underweight" in c_tl
              and lat is not None and lat <= 1000)
        grade("C", "bandChanges 0->1 at the crossing close, the trait both sides, client within 1 s of the boundary "
                   "estimate (push #2099); bandRepairs 0",
              obs, "as_predicted" if ok else "falsified", "bandChanges != 1, the trait absent on a side, latency > 1 s")
    # ---- D ----
    D = P.get("D") or {}
    w_exp = mass((D.get("body0") or {}).get("body"))
    age0 = to_num((D.get("snap0") or {}).get("worldAge"))
    rows = []
    for r in D.get("reads") or []:
        s, c = r["server"], r["client"]
        rows.append({"i": r["i"], "server_weight": to_num(s.get("weight")), "server_age_min": (to_num(s.get("worldAge")) - age0) * 60 if age0 is not None and s.get("worldAge") is not None else None,
                     "client_weight": to_num(c.get("weight")), "server_wall": s.get("wall"), "client_wall": c.get("wall")})
    set_ack = (D.get("set") or {}).get("ack") or {}
    late120 = [x for x in rows if x["server_weight"] is not None and abs(x["server_weight"] - D_SET) < 1e-3
               and (x["server_age_min"] or 0) > 2.0]
    all_ok = bool(rows) and all(near(x["server_weight"], w_exp, 1e-3) for x in rows)
    obs = {"set_reply_weight": set_ack.get("weight"), "fm_lm": w_exp, "reads": rows, "late_120": late120,
           "client_ever_120": any(near(x["client_weight"], D_SET, 1e-3) for x in rows),
           "w0": D.get("w0"), "w1": D.get("w1")}
    if not rows or set_ack.get("weight") is None:
        v = "unmeasured"
    elif all_ok and not late120:
        v = "as_predicted"
    elif late120:
        v = "falsified"
    else:
        v = "trivial"
    grade("D", "every server read after the set reads fm+lm (re-asserted within one slow minute)", obs, v,
          "a server read of 120 more than 2 game minutes after the set")
    # ---- F ----
    Fh = P.get("F") or {}
    rows = []
    for r in Fh.get("reads") or []:
        s, bd = r["server"], r["body"]
        e = bnum(bd.get("body"), "energyState")
        fill = bd.get("stomachFill")
        h = to_num(s.get("hunger"))
        exp_floor = 0.15 * max(0.0, e - 1) if e is not None else None
        exp_full = None if (e is None or fill is None) else min(max((1 - fill) * e + 0.15 * max(0.0, e - 1), 0), 1)
        exp_noflo = None if (e is None or fill is None) else min(max((1 - fill) * e, 0), 1)
        rows.append({"hunger": h, "energyState": e, "fill": fill, "expected": exp_full, "expected_no_floor": exp_noflo,
                     "floor": exp_floor, "match": near(h, exp_full, 1e-4), "match_no_floor": near(h, exp_noflo, 1e-4)})
    full = [x for x in rows if x["fill"] is not None and x["fill"] >= 1.0]
    obs = {"reads": rows, "eats": [{"item": e["item"], "landed": e["landing"].get("landed"), "ack": e["ack"]} for e in Fh.get("eats") or []]}
    if not full:
        v = "unmeasured"
    elif all(x["hunger"] is not None and x["hunger"] > 0 and x["match"] for x in full):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("F", "at fill 1 hunger == 0.15(E-1) > 0", obs, v, "hunger 0 (or the no-floor form) at fill 1 with E > 1")
    # ---- E1 ----
    E = P.get("E1") or {}
    rows = []
    for r in E.get("reads") or []:
        bd = (r.get("body") or {}).get("body") or {}
        ml = bd.get("mirrorLast")
        snap, nut = r.get("snap") or {}, r.get("nut") or {}
        hod = None
        if snap.get("hour") is not None:
            hod = to_num(snap.get("hour")) + (to_num(snap.get("minutes")) or 0) / 60.0
        exp = mirror_expect(bd, hod) if (bd and hod is not None) else None
        mlv = [to_num(x) for x in ml] if isinstance(ml, list) else None
        rows.append({"store": {k: to_num(nut.get(k)) for k in ("calories", "proteins", "carbs", "lipids")},
                     "client_store": {k: to_num((r.get("client_nut") or {}).get(k)) for k in ("calories", "proteins", "carbs", "lipids")},
                     "mirrorLast": mlv, "expected_from_record": exp, "hod": hod})
    ok = []
    for x in rows:
        m = x["mirrorLast"]
        s = x["store"]
        if m and len(m) == 4:
            ok.append(near(s["calories"], m[0], 15) and near(s["proteins"], m[1], 2) and near(s["carbs"], m[2], 2)
                      and near(s["lipids"], m[3], 2))
    obs = {"reads": rows, "store_vs_mirrorLast_ok": ok, "wstats0": E.get("wstats0"), "wstats1": E.get("wstats1")}
    v = "unmeasured" if not ok else ("as_predicted" if all(ok) else "falsified")
    grade("E1", "stores == mirrorLast (cal 15, others 2) with the mirror on; mirrorLast == the record's maps", obs, v,
          "a store away from mirrorLast beyond the read-gap tolerance")
    # ---- E0 ----
    E = P.get("E0") or {}
    w0, w1 = E.get("wstats0") or {}, E.get("wstats1") or {}
    mw0, mw1 = to_num(w0.get("mirrorWrites")), to_num(w1.get("mirrorWrites"))
    mn0, mn1 = to_num(w0.get("minutes")), to_num(w1.get("minutes"))
    obs = {"sv_before": E.get("sv_before"), "sv_after": E.get("sv_after"), "opt_before": E.get("opt_before"),
           "opt_after": E.get("opt_after"), "set": E.get("set"), "mirrorWrites": [mw0, mw1], "minutes": [mn0, mn1],
           "nut0": E.get("nut0"), "reads": E.get("reads")}
    if E.get("opt_after") is not False:
        v = "unmeasured"
    elif mw0 is not None and mw1 is not None and mn1 is not None and mn0 is not None and mw1 == mw0 and mn1 > mn0:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("E0", "the live option flip stops mirrorWrites while the minute runs", obs, v,
          "mirrorWrites still rising with options.legacyMirror false; unmeasured if the flip never reached the options")
    # ---- G ----
    obs = {}
    for lab in ("G1", "G2"):
        G = P.get(lab) or {}
        us = [to_num(b.get("usPerCall")) for b in G.get("bench") or []]
        tps = [to_num(t.get("ticksPerSecond")) for t in G.get("tick") or []]
        obs[lab] = {"usPerCall": us, "ticksPerSecond": tps}
    us = [u for lab in obs for u in obs[lab]["usPerCall"] if u is not None]
    tps = [t for lab in obs for t in obs[lab]["ticksPerSecond"] if t is not None]
    obs["plan2"] = {"usPerCall": PLAN2_US, "ticksPerSecond": PLAN2_TPS}
    if not us or not tps:
        v = "unmeasured"
    elif all(abs(u - PLAN2_US) / PLAN2_US <= 0.25 for u in us) and all(abs(t - PLAN2_TPS) / PLAN2_TPS <= 0.05 for t in tps):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("G", "bench_fast within 25 % of 3.06 us; tick rate within 5 % of 10.01", obs, v, "outside either band")


def body():
    run_phase("A", phase_A)
    run_phase("G1", lambda: phase_G("G1"))
    run_phase("D", phase_D)
    run_phase("FAST", phase_fast)
    try:
        if out["phases"].get("FAST", {}).get("speed_off") is None:
            out["speed_restore_after_fast"] = speed(1, "fast_restore")
    except Exception as e:                     # noqa: BLE001
        note(f"speed restore after the fast raised: {e}")
    run_phase("F", phase_F)
    run_phase("E1", phase_E1)
    run_phase("G2", lambda: phase_G("G2"))
    run_phase("E0", phase_E0)


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x141b-dry-run", None) if DRY_RUN else new_run_dir("x141b")
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
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"SPEED": SPEED, "MAX_CLOSES": MAX_CLOSES, "FAST_WALL_BUDGET_S": FAST_WALL_BUDGET_S,
                  "HEALTH_FLOOR": HEALTH_FLOOR, "FOODTIMER": FOODTIMER, "WATCH_LEAD_H": WATCH_LEAD_H,
                  "WATCH_AFTER_S": WATCH_AFTER_S, "TRAIT_WATCH_S": TRAIT_WATCH_S, "BAND_W": BAND_W, "D_SET": D_SET,
                  "BENCH_N": BENCH_N, "TICK_S": TICK_S, "PLAN2_US": PLAN2_US, "PLAN2_TPS": PLAN2_TPS,
                  "BULK": list(BULK), "OFF_EAT": OFF_EAT, "IDLE_MET": IDLE_MET},
    "prediction_apriori": {"male80": predict(14.4, 65.6, 9.0), "female80": predict(22.4, 57.6, 9.0)},
    "deviations": [
        "Controls during the fast: thirst and fatigue pinned to 0 every cycle; the health-from-food timer written to "
        f"{FOODTIMER} every {FOODTIMER_EVERY} cycles so the level-4 HUNGRY drain cannot kill the subject before the band "
        "crossing (~158 game hours); none of the three is an input of the body model.",
        "The client mirror is re-requested by calling the mod's own NutritionRevamp.client.requestMirror once through "
        "bench.global on the client (the first-sight mirror is sent before record.body exists).",
        "Speed through RCON settimespeed (the broadcast command, #1870), not time.multiplier.",
        "The band watch's boundary wall is ESTIMATED from the server's (worldAge, wall) pairs; the close runs at the "
        "first slow minute after the boundary (<= one game minute, 0.125 s wall at speed 5).",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["a lettuce, a bread and an apple eaten", "settimespeed returned to 1",
                                        "NR.LegacyMirror false in the live server config"]},
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
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out.get("mods_not_found"),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "phase_errors": list(out["phase_errors"]),
    }
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
                           "limits": {"luaerr": LUAERR_LIMIT, "nr": NR_LIMIT}}
            if clients:
                out["logs"].update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)})
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
