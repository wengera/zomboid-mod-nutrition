"""x141-clamp -- Plan 3 Task 19, acceptance 2 of the body model: the Strength clamp (a vanilla level-up
held at the ceiling, an admin level write re-asserted, the rise hysteresis, the lean-driven fall), the
band remap and its push, the LevelPerk crossing (X39's open arm, #2084), the carry delta, the training
events (reps, hits), the TAC step and the parity of the two endurance coefficients, and the asleep
regeneration x rmod. ONE boot of profile `x14-clamp` (PZTestKit + NutritionRevamp Mode 1 + TKX_XpEvents,
`Nutrition = false`, DayLength 1: a game day is 15 wall minutes at speed 1, a game hour 37.5 s, a game
minute 0.625 s). The run id prefix is `x141c`. Copied from `x141_body.py` (provenance, wall-bracketed
steps, predictions/verdicts, `to_num`, the persist/step shape); each phase runs under its own try.

THE INSTRUMENT. The amendments name a direct record edit (`lm = 0.9 lm0`, `rmod = 2`) as this session's
instrument. NO harness route can write it: `globalmoddata.set` writes one TOP-LEVEL key of a global
table (`t[key] = value`, PZTestKit_Server.lua:1449), so `admin.body.lm` would become a new top-level
key, not the record's field; there is no eval command (`lua.global` only reads; `bench.global` calls a
function with no arguments; `lua.reload` re-runs a file). So, as the amendments' fallback says, the
model's state is driven by its own inputs instead:
  * the CEILING by TIME: a fast at RCON `settimespeed 5` until the record's lean ratio pulls the ceiling
    below the shown level (the x141b fast showed the record's shownL go 5 -> 4 at its fourth close);
  * the TARGET by XP: the policy's target is min(XP-implied, ceiling), so server `xp.grant`s move the
    XP-implied level across the ceiling. The XP grants are the test's input (the mod never grants);
  * rmod by the model's own day close: a fasting close sets the protein gate low (0.85) and moves tac,
    so rmod goes 1 -> ~0.848 with no edit; the two sleep holds run at those two values.
  The lean-driven RISE (lm restored) cannot be driven in one session and is unmeasured as such; the
  rise hysteresis is measured on the XP axis (the same `K.strength.policy` code path).

THE PREDICTIONS (written before the run from the committed kernels at 3fa45b3; the subject is the
default fixture's admin, FEMALE, 80 kg -> fm 22.4 / lm 57.6, l0 5, traitCarry 1, x141b):
  P0 parity: at first sight tac, dmod and rmod read exactly "1": tac^-0.8 = tac^1.2 = 1 at tac 1; the
     excess-fat term is 0 (fm 22.4 = FM_NORMAL_80[2]); gProt(pPrevKg 0.8 = P_LOW) = 1; the other inputs
     are neutral stubs.
  C  carry: bf = 0.28 < FAT_KNEE 0.30, hoursAwake 0 -> eAcute 0 -> delta = traitCarry x 1 = 1.0;
     getMaxWeightDelta reads 1.0 == body.delta; `carry.set admin 2.0` is re-asserted to 1.0 at the next
     slow minute (<= 0.625 s + the poll), carryWrites +1.
  X  crossing: the fixture starts at Strength XP 37500 (level 5's total, #2867 run); the grant lifts it
     to 67600 (level 6 total 67500 + 100; the raw amount is divided by vanilla's protein multiplier,
     0.7 while the mirrored store is below -300, #2112) -> vanilla's LevelPerk crossing puts the Java
     level at 6 in the grant's tick (levelAfter 6) and fires the LevelPerk event once (lastLevel 6,
     gained true); the ceiling is 5 (lm = lm0, fSlow 1) so the clamp writes 5 within one slow minute
     (writes +1), XP stays 67600 at every sample, STOUT is absent on both sides after that minute, and
     the client's level reads 5 within ~2 s and holds through 30 s of samples and an `xp.sync`.
     STOUT on the client in between (the trait watch) says whether vanilla's LevelPerk remap pushed.
  R  re-assert: `perk.level admin Strength 3` (debug write) -> the next slow minute writes 5 back
     (writes +1); no trait change at 5, so no push.
  U  rise hysteresis on the XP axis (speed 1): the grant to 17600 (level 3) -> vanilla's LoseLevel loop
     puts Java at 3 in the grant's tick; the policy follows down at once (desired = min(.., 3)), the
     record's shownL 3, lastFallAge stamped at the drop; Java already 3, so the mod writes nothing and
     runs no remap (the remap runs only after a write) -> FEEBLE appears only if vanilla's LevelPerk
     listener remaps on a LoseLevel. riseHeldH accrues from the next minute (ceiling 5 >= 3 + 1).
     At drop + 2 h the grant back to 67600 -> Java 6 (LevelPerk loop) -> the next minute writes 3 back
     (riseHeldH ~2 < 6) with the remap at 3 (FEEBLE; STOUT removed if vanilla added it) and one push.
     The first rise comes when riseHeldH reaches 6 h, counted from the DROP, not the restore: shownL 4
     at drop + 6 h (+1 to 2 game minutes), then riseHeldH restarts and shownL 5 another 6 h later; the
     rise to 4 changes no trait (FEEBLE 2-4), the rise to 5 removes FEEBLE with one push.
  F  the lean-driven fall (speed 5): fasting closes move lean by the partition law and cumDef by the
     day's deficit; the ceiling floor(5 + 10 log2(lm/lm0 x fSlow) + 0.5) from the committed kernels:
         close   lm(kernel a-priori)  cumDef   ceiling-x  | x141b measured lm  x
           1        57.600            1513     5.456      |   57.418         5.400
           2        57.257            3526     5.312      |   57.078         5.257
           3        56.915            5337     5.172      |   56.737         5.119
           4        56.571            6964     5.038      |   56.397         4.986  <- x141b fell here
           5        56.228            8427     4.907 <- 4 |   56.057         4.856
     (a-priori: REE 19.7 LM + 413 x cold 1.022 + idle 0.3 kcal/kg/h; x141b's first close cost more
     lean than the a-priori, so the fall lands at close 4 or 5.) Prediction: at the FIRST close whose
     post-close record gives ceiling < 5, the record's lastFallAge is stamped within one game minute of
     the boundary, shownL 4, the Java level 4 (XP 67600 unchanged), FEEBLE added on the server with one
     push, the client's trait watch sees FEEBLE within ~1 s of the boundary estimate, and 30 s of
     samples plus an `xp.sync` leave 4. No fall at a close whose ceiling is still 5. The one-level-per-
     hour pacing needs a two-level ceiling drop, which lean cannot make in a session: unmeasured.
  T  TAC: the first fasting close takes tac 1 -> 1 - 0.2/84 = 0.997619 (target 1 is not above tac 1,
     hardDays 0 -> the loss branch); each later fasting close gains (1 - tac)/15 x gnut, gnut = gIron 1
     x gProt(0) 0.85 x min(gEnergy 0.5, gSleep 1) = 0.425 -> +6.7e-5 a day. rmod = tac^1.2 x 0.85
     (~0.8476), dmod = tac^-0.8 (~1.0019). `tac > 1` is NOT expected: the run flag never reaches the
     server (x141a) and a fasting week holds target 1. After the training set the next close's target
     is 1 + 0.25 min(1, m1/240) with m1 the week's band-1 minutes (the set's exercising minutes), so
     tac' = tac + (target - tac)/15 x 0.425, still below 1 for any m1 <= 240.
  H  asleep regen x rmod: two 60 s `player.sleep.hold`s from endurance 0.05 with fatigue pinned 0,
     H1 at first sight (rmod 1), H2 after the fall (rmod ~0.848). Per update the asleep arm adds
     3.1e-5 x endRegen x recoveryMod x M x f x rmod (f = 2, or 2 x D when every player sleeps), the
     ~15 % awake share (#2840) vanilla's standing regen 3.1e-5 x endRegen x recoveryMod x M; neither
     recoveryMod (Fitness level, weight traits) nor the mix changes between the holds. The slope ratio
     H2/H1 lies between rmod (all asleep) and (1.7 rmod + 0.15)/1.85 (the #2840 mix at f = 2):
     [0.848, 0.860]. Falsifier: a ratio outside [0.80, 0.90] (1.0 means rmod is not applied).
  D  training (speed 1; the exercise length is GAME minutes and the rep pace is the animation's,
     ~3 wall s a rep in x141a, so `squats 40` ~ 25 s ~ 8 reps and `pushups 20` ~ 12 s ~ 4 reps; the
     amendments' 2 game minutes is 1.25 wall s here, too short for one rep): reps delta == the Strength
     AddXP count delta (ruling T13-2); squats paired with a Fitness event each; vStr +0.04 and vHyp
     +0.05 a squat rep, +0.08 / +0.10 a push-up rep (moderate class), less the 7-day decay; the push-up
     Fitness event at amount 0 is reported (fires or not). Melee: `stats.hits` delta ==
     the OnWeaponHitXp count delta.

CONTROLS (not inputs of the body model): thirst and fatigue pinned to 0 every few samples; the health-
from-food timer written to 20000 during the fast (x141b: a level-4 HUNGRY drain); endurance written to
0.05 before each hold and to 1 after it and before the training set. No eat in this session.

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

PROFILE = "x14-clamp"
SESSION = ("Plan 3 acceptance 2: the Strength clamp (crossing held, admin write re-asserted, rise "
           "hysteresis on the XP axis, lean-driven fall), remap and push, LevelPerk crossing, carry, "
           "training events, TAC and the coefficients' parity, asleep regen x rmod; one boot of x14-clamp")
ARTIFACT = "clamp.json"
USER = "admin"
PRIOR_RUNS = ["x141b-20261005-122603", "x141s-20261005-105131", "x141a-20261005-111005"]

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
B = f"{USER}.body"
SCALARS = ("dayIndex", "fm", "lm", "lm0", "l0", "shownL", "riseHeldH", "lastFallAge", "strAgeH", "cumDef",
           "n", "nPeak", "tPeakD", "tDisuse", "tac", "dmod", "rmod", "delta", "traitCarry", "band1Day",
           "band2Day", "vStr", "vHyp", "vStrHigh", "pPrevKg", "lastAgeH", "energyState", "sex")
SCAL_FAST = ("dayIndex", "lm", "shownL", "riseHeldH", "lastFallAge", "cumDef", "tac", "rmod", "dmod")
STR_STATS = ("minutes", "writes", "pushes", "pushMissing", "carryWrites", "failures", "badReads",
             "ladderFallbacks")
TRN_STATS = ("reps", "paired", "repsFitnessOnly", "hits", "trees", "ignored", "failures")
EV_KEYS = ("addxp_Strength_count", "addxp_Strength_lastAmount", "addxp_Strength_lastLevel",
           "addxp_Fitness_count", "addxp_Fitness_lastAmount", "addxp_Fitness_lastLevel",
           "levelperk_count", "levelperk_lastPerk", "levelperk_lastLevel", "levelperk_lastGained",
           "hitxp_count", "hitxp_lastHitCount", "hittree_count")
COMPACT = ("traitList", "endurance", "fatigue", "thirst", "hunger", "asleep", "worldAge", "wall", "weight",
           "proteins", "maxWeight", "foodTimer", "moving")
LVL_HOP = "getPerkLevel(Perks.Strength)"
XP_HOP = "getXp.getXP(Perks.Strength)"
HEALTH_HOP = "getBodyDamage.getOverallBodyHealth"
DEAD_HOP = "isDead"
EXE_HOP = "getFitness.getCurrentExe"

XP_L6 = 67600.0                # level 6's total 67500 + 100
XP_L3 = 17600.0                # level 3: 10500 <= x < 19500
RESTORE_AFTER_H = 2.0          # game hours after the drop the XP goes back up
RISE_HOLD_H = 6.0              # K.strength.RISE_HOLD_H
U_MAX_H = 13.6                 # the rise arm's game-hour budget after the drop
U_WALL_MAX_S = 10 * 60
CARRY_SET = 2.0
CARRY_READS_S = 12.0
HOLD_S = 60
HOLD_E0 = 0.05
X_SAMPLE_S, X_SYNC_AT_S = 30.0, 15.0
FAST_SPEED = 5
DAY_WALL_S_AT1 = 900.0
FAST_MAX_CLOSES = 7
FAST_WALL_BUDGET_S = 22 * 60
FALL_HOLD_S, FALL_SYNC_AT_S = 30.0, 12.0
HEALTH_FLOOR = 15.0
FOODTIMER = 20000
SQUAT_MIN, PUSHUP_MIN = 40, 20
MELEE_SWINGS, ZOMBIE_WAIT_S, ZOMBIE_POLL_S = 5, 25.0, 2.0
TAC_WALL_MAX_S = 5 * 60

# committed kernel constants the predictions and checks recompute (3fa45b3)
LEVELS_PER_DOUBLING, L_MAX = 10, 10
MEM_RETAIN, MEM_TAU, CUMDEF_FULL, E_ENERGY_MAX = 0.80, 300.0, 50000.0, -0.10
DISUSE_K, DISUSE_T, F_MIN, F_MAX = -0.325, 22.0, 0.55, 1.25
TAC_MIN, TAC_MAX, TAU_GAIN, TAU_LOSS, VOL_WEEK_FULL = 0.80, 1.25, 15.0, 84.0, 240.0
EXP_D, EXP_R, G_PROT_LOW = -0.8, 1.2, 0.85
W_STR_MOD, S_REP_LEGS, S_REP_ARMS = 0.8, 0.05, 0.10

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
NR_RX = re.compile(r"\[NutritionRevamp\]")
LUAERR_LIMIT, NR_LIMIT = 40, 80


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
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    stored = val
    if keep is not None and isinstance(val, dict):
        stored = {k: val.get(k) for k in keep}
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "epoch_after": round(time.time(), 3), "took": round(t_after - t_before, 3), "ack": stored}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    ret = dict(row)
    ret["full"] = val
    return ret


def ack(r):
    return r["full"] if isinstance(r.get("full"), dict) else {}


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


def chain_c(tag, hop):
    r = step(tag, client, "witness.chain", hop)
    a = ack(r)
    return {"wall": r["wall_before"], "epoch": r["epoch_before"], "ok": a.get("ok"), "value": to_num(a.get("value")),
            "raw": a.get("value"), "failedAt": a.get("failedAt")}


def scal(tag, keys=SCALARS):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(f"{B}.{k}" for k in keys),
             keep=("values", "missing", "worldAge"))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    raw = {k: vals.get(f"{B}.{k}") for k in keys}
    return {"tag": tag, "wall": r["wall_before"], "epoch": r["epoch_before"], "worldAge": a.get("worldAge"),
            "raw": raw, "num": {k: to_num(v) for k, v in raw.items()}}


def body_full(tag):
    r = step(tag, server, "witness.moddata", f"global:{STORE} {B}", keep=("values", "missing", "worldAge"))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    b = vals.get(B)
    return {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
            "body": b if isinstance(b, dict) else None}


def perk(tag):
    r = step(tag, server, "perk.xp", f"{USER} Strength")
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "epoch": (r["epoch_before"] + r["epoch_after"]) / 2.0,
            "xp": to_num(a.get("xp")), "level": to_num(a.get("level")), "age": to_num(a.get("serverWorldAge"))}


def sstats(tag):
    r = step(tag, server, "stats.get", USER, keep=COMPACT)
    a = ack(r)
    d = {k: a.get(k) for k in COMPACT}
    d.update({"side": "server", "wall_before": r["wall_before"], "epoch": r["epoch_before"]})
    return d


def cstats(tag):
    r = step(tag, client, "stats.get", "", keep=COMPACT)
    a = ack(r)
    d = {k: a.get(k) for k in COMPACT}
    d.update({"side": "client", "wall_before": r["wall_before"], "epoch": r["epoch_before"]})
    return d


def tnames(tlist):
    if isinstance(tlist, dict):
        tlist = list(tlist.values())
    if not isinstance(tlist, list):
        return []
    return sorted(str(x).lower().split(":")[-1].split(".")[-1] for x in tlist)


def band_traits(tlist):
    return [t for t in tnames(tlist) if t in ("weak", "feeble", "stout", "strong")]


def tpair(tag):
    c = cstats(f"{tag}_c")
    s = sstats(f"{tag}_s")
    p = {"tag": tag, "client": band_traits(c.get("traitList")), "server": band_traits(s.get("traitList")),
         "client_all": tnames(c.get("traitList")), "server_all": tnames(s.get("traitList")),
         "client_epoch": c["epoch"], "server_epoch": s["epoch"], "server_age": s.get("worldAge")}
    out["trait_pairs"].append(p)
    return p


def strstats(tag, fields=STR_STATS):
    return {f: to_num(gv(server, f"NutritionRevamp.server.strength.stats.{f}", f"{tag}_{f}")) for f in fields}


def trnstats(tag, fields=TRN_STATS):
    return {f: to_num(gv(server, f"NutritionRevamp.server.training.stats.{f}", f"{tag}_{f}")) for f in fields}


def events(tag):
    r = step(tag, server, "witness.moddata", "global:TKX_XpEvents " + " ".join(EV_KEYS),
             keep=("values", "missing"))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    e = {"tag": tag, "wall": r["wall_before"], "values": vals}
    out["events"].append(e)
    return e


def ev(e, k):
    return to_num((e or {}).get("values", {}).get(k)) or 0.0


def pins(tag, foodtimer=False, endurance=None):
    args = f"{USER} thirst 0 fatigue 0"
    if endurance is not None:
        args += f" endurance {endurance}"
    p = {"stats": ack(step(f"{tag}_pin", server, "stats.set", args, keep=("applied",))).get("applied")}
    if foodtimer:
        p["foodtimer"] = ack(step(f"{tag}_ft", server, "foodtimer.set", f"{USER} {FOODTIMER}")).get("after")
    return p


def protein_mult(p):
    if p is None:
        return 1.0, "unread"
    if 50 < p < 300:
        return 1.5, "x1.5 (50 < proteins < 300)"
    if p < -300:
        return 0.7, "x0.7 (proteins < -300)"
    return 1.0, "x1"


def grant_to(tag, target):
    before = perk(f"{tag}_pre")
    nut = ack(step(f"{tag}_nut", server, "nutrition.get", USER, keep=("proteins", "weight")))
    prot = to_num(nut.get("proteins"))
    mult, why = protein_mult(prot)
    raw = (target - (before["xp"] or 0.0)) / mult
    r = step(f"{tag}_grant", server, "xp.grant", f"{USER} Strength {raw:.4f}")
    a = ack(r)
    return {"tag": tag, "target": target, "xp_before": before["xp"], "level_before": before["level"],
            "proteins": prot, "mult": mult, "mult_rule": why, "raw": raw, "ack": a,
            "xpAfter": to_num(a.get("xpAfter")), "levelAfter": to_num(a.get("levelAfter")),
            "wall": r["wall_before"], "epoch": r["epoch_after"], "age_pre": before["age"]}


def speed(n, tag):
    ok, rep = server.rcon(f"settimespeed {n}")
    row = {"wall": wall(), "n": n, "ok": ok, "reply": str(rep)[:200]}
    out["speed_changes"].append(row)
    tl.mark("speed", n=n, ok=ok)
    row["server_snap"] = ack(step(f"{tag}_snap_s", server, "time.snapshot", ""))
    return row


def arm_watch(tag, trait, seconds):
    e = time.time()
    a = ack(step(f"{tag}_twatch", client, "trait.watch", f"{trait} {seconds}"))
    return {"trait": trait, "seconds": seconds, "epoch": e, "arm": a}


def collect_watch(w, timeout):
    if not w or not (w.get("arm") or {}).get("armed"):
        return {"error": "not armed"}
    try:
        return client.bus.wait_result("trait-watch", timeout=timeout, after=w["epoch"] - 0.5)
    except Exception as e:                     # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def run_phase(name, fn):
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    persist()


# ---------------------------------------------------------------- kernel arithmetic (checks)
def fslow(b):
    n, npk, tpk, cd, td, day = (b.get(k) for k in ("n", "nPeak", "tPeakD", "cumDef", "tDisuse", "dayIndex"))
    if None in (n, npk, tpk, cd, td, day):
        return None
    floor_f = 1 + npk * MEM_RETAIN * math.exp(-(day - tpk) / MEM_TAU)
    v = max(1 + n, floor_f) + E_ENERGY_MAX * min(max(cd / CUMDEF_FULL, 0), 1) + DISUSE_K * math.log(1 + td / DISUSE_T)
    return min(max(v, F_MIN), F_MAX)


def ceiling_x(b):
    f = fslow(b)
    l0, lm, lm0 = b.get("l0"), b.get("lm"), b.get("lm0")
    if f is None or None in (l0, lm, lm0) or lm0 <= 0:
        return None, None
    x = l0 + LEVELS_PER_DOUBLING * math.log(lm / lm0 * f) / math.log(2) + 0.5
    return x, min(max(math.floor(x), 0), L_MAX)


def tac_step(tac, m1, hard, gprot, genergy, gsleep=1.0):
    svol = min(max(m1 / VOL_WEEK_FULL, 0), 1)
    target = 1 + (TAC_MAX - 1) * svol
    gnut = 1.0 * gprot * min(genergy, gsleep)
    if target > tac:
        tac = tac + (target - tac) / TAU_GAIN * gnut
    elif hard < 2:
        tac = tac - (tac - TAC_MIN) / TAU_LOSS
    return min(max(tac, TAC_MIN), TAC_MAX), target, gnut


# ---------------------------------------------------------------- phases
def phase_P0():
    P = out["phases"]["P0"] = {"waits": []}
    end = wall() + 60
    s = None
    while wall() < end:
        s = scal("P0_wait", ("dayIndex", "shownL"))
        P["waits"].append({"wall": s["wall"], "has": s["num"]["dayIndex"] is not None})
        if s["num"]["dayIndex"] is not None:
            break
        time.sleep(1.0)
    time.sleep(1.5)                           # a couple of slow minutes after first sight
    P["body"] = body_full("P0_body")
    P["scal"] = scal("P0_scal")
    P["perk"] = perk("P0_perk")
    P["client_level"] = chain_c("P0_clvl", LVL_HOP)
    P["client_xp"] = chain_c("P0_cxp", XP_HOP)
    P["traits"] = tpair("P0_tp")
    P["str"] = strstats("P0_str")
    P["trn"] = trnstats("P0_trn")
    P["events"] = events("P0_ev")
    P["nut"] = ack(step("P0_nut", server, "nutrition.get", USER, keep=("proteins", "weight", "calories")))
    P["met_failures"] = gv(server, "NutritionRevamp.server.metabolism.stats.failures", "P0_metf")
    P["str_lastError"] = gv(server, "NutritionRevamp.server.strength.lastError", "P0_strerr")
    P["str_limitations_n"] = ack(step("P0_strlim", server, "lua.global", "NutritionRevamp.server.strength.limitations"))
    P["beyondten"] = ack(step("P0_b10", server, "lua.global", "BeyondTen"))
    P["ladder"] = {L: gv(server, f"NutritionRevamp.server.strength.totals.{L}", f"P0_tot{L}") for L in (4, 5, 6)}


def phase_C():
    C = out["phases"]["C"] = {"reads": []}
    C["str0"] = strstats("C_str0", ("carryWrites", "minutes"))
    C["scal0"] = scal("C_scal0", ("delta", "traitCarry", "fm", "lm"))
    C["server0"] = ack(step("C_wf_s0", server, "witness.fields", f"player {USER} getMaxWeightDelta,getMaxWeight"))
    C["client0"] = ack(step("C_wf_c0", client, "witness.fields", f"player {USER} getMaxWeightDelta,getMaxWeight"))
    r = step("C_set", server, "carry.set", f"{USER} {CARRY_SET}")
    C["set"] = {"ack": ack(r), "wall": r["wall_after"], "epoch": r["epoch_after"]}
    t_set = r["wall_after"]
    i = 0
    while wall() < t_set + CARRY_READS_S:
        rr = step(f"C_wf{i}", server, "witness.fields", f"player {USER} getMaxWeightDelta,getMaxWeight")
        C["reads"].append({"i": i, "wall": rr["wall_before"], "dt": round(rr["wall_before"] - t_set, 3),
                           "fields": ack(rr).get("fields"), "worldAge": ack(rr).get("worldAge")})
        i += 1
        time.sleep(0.4 if i < 10 else 1.5)
    C["str1"] = strstats("C_str1", ("carryWrites", "minutes"))
    C["client1"] = ack(step("C_wf_c1", client, "witness.fields", f"player {USER} getMaxWeightDelta,getMaxWeight"))
    C["scal1"] = scal("C_scal1", ("delta", "traitCarry"))


def hold(label):
    H = out["phases"][label] = {"reads": []}
    H["pin"] = pins(f"{label}_p", endurance=HOLD_E0)
    H["scal0"] = scal(f"{label}_scal0", ("rmod", "tac", "dmod", "dayIndex", "pPrevKg"))
    H["pre"] = sstats(f"{label}_pre")
    r = step(f"{label}_hold", server, "player.sleep.hold", f"{USER} {HOLD_S}")
    H["hold"] = {"ack": ack(r), "wall": r["wall_after"], "epoch": r["epoch_after"]}
    t_h = r["wall_after"]
    i = 0
    while wall() < t_h + HOLD_S + 2.0:
        H["reads"].append(sstats(f"{label}_r{i}"))
        i += 1
        if wall() > t_h + 15.0:
            time.sleep(1.5)
    H["scal1"] = scal(f"{label}_scal1", ("rmod", "tac", "dmod", "dayIndex", "pPrevKg"))
    H["post_pin"] = pins(f"{label}_pp", endurance=1)
    awake = None
    for j in range(10):
        s = sstats(f"{label}_wake{j}")
        if s.get("asleep") is False:
            awake = s
            break
        time.sleep(1.0)
    if awake is None:
        H["force_wake"] = ack(step(f"{label}_wakeset", server, "player.sleep", f"{USER} false"))
        awake = sstats(f"{label}_wake_after")
    H["awake"] = awake


def phase_X():
    X = out["phases"]["X"] = {"samples": []}
    X["ev0"] = events("X_ev0")
    X["str0"] = strstats("X_str0", ("writes", "pushes", "pushMissing"))
    X["tp0"] = tpair("X_tp0")
    X["watch"] = arm_watch("X", "stout", 40)
    X["grant"] = grant_to("X_g", XP_L6)
    t_g = X["grant"]["wall"]
    X["right_after"] = {"perk": perk("X_ra_perk"), "server": sstats("X_ra_s")}
    synced = False
    i = 0
    while wall() < t_g + X_SAMPLE_S:
        smp = {"i": i, "perk": perk(f"X_p{i}"), "client_level": chain_c(f"X_cl{i}", LVL_HOP)}
        if i % 3 == 0:
            smp["traits"] = tpair(f"X_tp{i}")
            smp["str"] = strstats(f"X_s{i}", ("writes", "pushes"))
        X["samples"].append(smp)
        if not synced and wall() > t_g + X_SYNC_AT_S:
            X["sync"] = {"wall": wall(), "ack": ack(step("X_sync", client, "xp.sync", ""))}
            synced = True
        i += 1
        time.sleep(1.0)
    X["ev1"] = events("X_ev1")
    X["str1"] = strstats("X_str1", ("writes", "pushes", "pushMissing", "failures"))
    X["scal1"] = scal("X_scal1", ("shownL", "riseHeldH", "lastFallAge", "lm", "lm0", "l0"))
    X["client_xp"] = chain_c("X_cxp", XP_HOP)
    X["watch_result"] = collect_watch(X["watch"], 45)


def phase_R():
    R = out["phases"]["R"] = {"reads": []}
    R["str0"] = strstats("R_str0", ("writes", "pushes"))
    r = step("R_write", server, "perk.level", f"{USER} Strength 3")
    R["write"] = {"ack": ack(r), "wall": r["wall_after"]}
    t_w = r["wall_after"]
    i = 0
    while wall() < t_w + 8.0:
        R["reads"].append(perk(f"R_p{i}"))
        i += 1
        time.sleep(0.2)
    R["client_level"] = chain_c("R_cl", LVL_HOP)
    R["str1"] = strstats("R_str1", ("writes", "pushes"))
    R["tp"] = tpair("R_tp")


def phase_U():
    U = out["phases"]["U"] = {"polls": []}
    U["ev0"] = events("U_ev0")
    U["str0"] = strstats("U_str0", ("writes", "pushes"))
    U["watch_feeble"] = arm_watch("U", "feeble", 30)
    U["drop"] = grant_to("U_drop", XP_L3)
    a_drop = perk("U_drop_post")
    U["drop_post"] = a_drop
    U["tp_drop"] = tpair("U_tp_drop")
    U["ev_drop"] = events("U_ev_drop")
    age_drop = a_drop["age"]
    restored = False
    t_start = wall()
    last_shown = None
    i = 0
    while wall() < t_start + U_WALL_MAX_S:
        p = perk(f"U_p{i}")
        s = scal(f"U_s{i}", ("shownL", "riseHeldH", "lastFallAge", "dayIndex", "strAgeH"))
        poll = {"i": i, "perk": p, "scal": s["num"], "scal_wall": s["wall"]}
        if i % 2 == 0:
            poll["client_level"] = chain_c(f"U_cl{i}", LVL_HOP)
        shown = s["num"].get("shownL")
        if shown is not None and shown != last_shown:
            poll["change"] = {"from": last_shown, "to": shown}
            poll["traits"] = tpair(f"U_tpc{i}")
            poll["str"] = strstats(f"U_strc{i}", ("writes", "pushes"))
            last_shown = shown
        elif i % 12 == 0:
            poll["traits"] = tpair(f"U_tp{i}")
            poll["str"] = strstats(f"U_str{i}", ("writes", "pushes"))
        U["polls"].append(poll)
        age = p["age"]
        if not restored and age is not None and age_drop is not None and age >= age_drop + RESTORE_AFTER_H:
            U["watch_result_drop"] = collect_watch(U["watch_feeble"], 2)
            U["watch_stout"] = arm_watch("U_r", "stout", 20)
            U["restore"] = grant_to("U_restore", XP_L6)
            U["restore_post"] = {"perk": perk("U_restore_post"), "server": sstats("U_restore_s")}
            restored = True
            for j in range(6):
                q = perk(f"U_rq{j}")
                qs = scal(f"U_rqs{j}", ("shownL", "riseHeldH"))
                U["polls"].append({"i": f"r{j}", "perk": q, "scal": qs["num"], "scal_wall": qs["wall"]})
                time.sleep(0.3)
            U["tp_restore"] = tpair("U_tp_restore")
            U["str_restore"] = strstats("U_str_restore", ("writes", "pushes"))
            U["ev_restore"] = events("U_ev_restore")
        if i % 20 == 0:
            pins(f"U_{i}")
        if age is not None and age_drop is not None and age > age_drop + U_MAX_H:
            break
        if restored and last_shown == 5 and age is not None and age_drop is not None and age > age_drop + 12.3:
            break
        i += 1
        time.sleep(0.6)
    U["watch_result_stout"] = collect_watch(U.get("watch_stout"), 25)
    U["end"] = {"perk": perk("U_end_perk"), "scal": scal("U_end_scal"), "tp": tpair("U_end_tp"),
                "str": strstats("U_end_str"), "ev": events("U_end_ev"), "client_level": chain_c("U_end_cl", LVL_HOP)}
    U["age_drop"] = age_drop


def phase_F():
    F = out["phases"]["F"] = {"cycles": [], "closes": [], "stop": None}
    F["pins0"] = pins("F0", foodtimer=True)
    F["body0"] = body_full("F_body0")
    F["speed"] = speed(FAST_SPEED, "F_on")
    start = wall()
    seen_day = None
    watch = None
    fell = None
    n = 0
    while True:
        n += 1
        cyc = {"n": n}
        p = perk(f"F{n}_p")
        s = scal(f"F{n}_s", SCAL_FAST)
        cyc["perk"], cyc["scal"], cyc["scal_wall"], cyc["scal_age"] = p, s["num"], s["wall"], s["worldAge"]
        day = s["num"].get("dayIndex")
        if day is not None and day != seen_day:
            bf = body_full(f"F{n}_body")
            F["closes"].append({"n": n, "dayIndex": day, "wall": s["wall"], "epoch": s["epoch"],
                                "age": p["age"], "scal_age": s["worldAge"], "body": bf["body"]})
            seen_day = day
            if watch is None and day >= 2:
                watch = arm_watch(f"F{n}", "feeble", 600)
                F["watch"] = watch
        if n % 2 == 0:
            cyc["client_level"] = chain_c(f"F{n}_cl", LVL_HOP)
        if n % 3 == 0:
            cyc["str"] = strstats(f"F{n}_str", ("writes", "pushes"))
            cyc["pins"] = pins(f"F{n}", foodtimer=(n % 9 == 0))
        if n % 6 == 0:
            cyc["health"] = chain_s(f"F{n}_hp", HEALTH_HOP)
            cyc["dead"] = chain_s(f"F{n}_dead", DEAD_HOP)
        F["cycles"].append(cyc)
        if n % 10 == 0:
            persist()
        if p["level"] is not None and p["level"] <= 4 and fell is None:
            fell = {"n": n, "perk": p, "wall": p["wall"], "epoch": p["epoch"]}
            F["fell"] = fell
            F["fall_body"] = body_full("F_fall_body")
            F["fall_tp"] = tpair("F_fall_tp")
            F["fall_str"] = strstats("F_fall_str", ("writes", "pushes", "pushMissing", "failures"))
            F["fall_cl"] = chain_c("F_fall_cl", LVL_HOP)
            break
        hp = to_num((cyc.get("health") or {}).get("value"))
        if hp is not None and hp < HEALTH_FLOOR:
            F["stop"] = f"health {hp}"
            break
        if str((cyc.get("dead") or {}).get("value")).lower() == "true":
            F["stop"] = "dead"
            break
        if day is not None and F["closes"] and day - F["closes"][0]["dayIndex"] >= FAST_MAX_CLOSES:
            F["stop"] = f"{FAST_MAX_CLOSES} closes"
            break
        if wall() - start > FAST_WALL_BUDGET_S:
            F["stop"] = "wall budget"
            break
        time.sleep(0.4)
    F["speed_off"] = speed(1, "F_off")
    if fell is not None:
        F["stop"] = "fell"
        hold_s = {"samples": []}
        t_f = wall()
        synced = False
        i = 0
        while wall() < t_f + FALL_HOLD_S:
            smp = {"perk": perk(f"FH_p{i}"), "client_level": chain_c(f"FH_cl{i}", LVL_HOP)}
            if i % 4 == 0:
                smp["traits"] = tpair(f"FH_tp{i}")
            hold_s["samples"].append(smp)
            if not synced and wall() > t_f + FALL_SYNC_AT_S:
                hold_s["sync"] = {"wall": wall(), "ack": ack(step("FH_sync", client, "xp.sync", ""))}
                synced = True
            i += 1
            time.sleep(1.5)
        hold_s["str"] = strstats("FH_str", ("writes", "pushes", "pushMissing", "failures"))
        hold_s["scal"] = scal("FH_scal")
        F["hold"] = hold_s
    F["watch_result"] = collect_watch(watch, 5)
    F["end"] = {"perk": perk("F_end_perk"), "scal": scal("F_end_scal"), "health": chain_s("F_end_hp", HEALTH_HOP),
                "client_xp": chain_c("F_end_cxp", XP_HOP), "met_failures": gv(server, "NutritionRevamp.server.metabolism.stats.failures", "F_end_metf")}


def phase_D():
    D = out["phases"]["D"] = {}
    D["pins"] = pins("D0", endurance=1)
    D["ev0"] = events("D_ev0")
    D["trn0"] = trnstats("D_trn0")
    D["scal0"] = scal("D_scal0", ("vStr", "vHyp", "vStrHigh", "band1Day", "band2Day", "dayIndex"))
    for name, mins in (("squats", SQUAT_MIN), ("pushups", PUSHUP_MIN)):
        E = D[name] = {"exe": []}
        r = step(f"D_{name}", client, "exercise.do", f"{name} {mins}")
        E["ack"] = ack(r)
        E["wall"] = r["wall_after"]
        dur = mins * DAY_WALL_S_AT1 / 1440.0
        end = r["wall_after"] + dur + 6.0
        k = 0
        while wall() < end:
            E["exe"].append({"wall": wall(), "server": chain_s(f"D_{name}_exe{k}", EXE_HOP)})
            k += 1
            time.sleep(2.0)
        E["ev1"] = events(f"D_{name}_ev1")
        E["trn1"] = trnstats(f"D_{name}_trn1")
        E["scal1"] = scal(f"D_{name}_scal1", ("vStr", "vHyp", "vStrHigh", "band1Day", "band2Day", "dayIndex"))
        E["exe_after"] = chain_s(f"D_{name}_exe_after", EXE_HOP)
        E["pins"] = pins(f"D_{name}_pp", endurance=1)


def phase_T():
    T = out["phases"]["T"] = {"polls": []}
    T["pre"] = scal("T_pre")
    T["pre_body"] = body_full("T_pre_body")
    day0 = T["pre"]["num"].get("dayIndex")
    T["speed"] = speed(FAST_SPEED, "T_on")
    t_s = wall()
    last = None
    while wall() < t_s + TAC_WALL_MAX_S:
        s = scal("T_poll", ("dayIndex", "tac", "band1Day", "band2Day", "rmod", "dmod"))
        T["polls"].append({"wall": s["wall"], "num": s["num"], "raw": s["raw"]})
        if s["num"].get("dayIndex") is not None and day0 is not None and s["num"]["dayIndex"] > day0:
            break
        last = s
        time.sleep(1.0)
    T["last_pre"] = last
    T["post"] = scal("T_post")
    T["post_body"] = body_full("T_post_body")
    T["speed_off"] = speed(1, "T_off")


def phase_M():
    M = out["phases"]["M"] = {"rcon": [], "attempts": []}
    M["ev0"] = events("M_ev0")
    M["trn0"] = trnstats("M_trn0")
    M["exe0"] = chain_s("M_exe0", EXE_HOP)
    ok, rep = server.rcon(f"createhorde 1 {USER}")
    M["rcon"].append({"wall": wall(), "ok": ok, "reply": str(rep)[:300]})
    started = None
    t_start = wall()
    second = False
    while started is None and wall() < t_start + 2 * ZOMBIE_WAIT_S:
        if not second and wall() > t_start + ZOMBIE_WAIT_S:
            ok, rep = server.rcon(f"createhorde 1 {USER}")
            M["rcon"].append({"wall": wall(), "ok": ok, "reply": str(rep)[:300]})
            second = True
        e = time.time()
        a = ack(step("M_attack", client, "attack.melee", str(MELEE_SWINGS)))
        M["attempts"].append({"wall": wall(), "ok": a.get("ok"), "reason": a.get("reason"), "weapon": a.get("weapon")})
        if a.get("ok") is True:
            started = e
            break
        time.sleep(ZOMBIE_POLL_S)
    if started is not None:
        try:
            M["result"] = client.bus.wait_result("attack-melee", timeout=40, after=started)
        except Exception as ex:                # noqa: BLE001
            M["result"] = {"error": f"{type(ex).__name__}: {ex}"}
        time.sleep(2.0)
    else:
        note("no zombie came within 2 tiles; the hit arm is unmeasured")
    M["ev1"] = events("M_ev1")
    M["trn1"] = trnstats("M_trn1")
    M["scal1"] = scal("M_scal1", ("vStr", "vHyp", "vStrHigh"))


# ---------------------------------------------------------------- grading
def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def grade_all():
    P = out["phases"]
    P0 = P.get("P0") or {}
    raw = ((P0.get("scal") or {}).get("raw")) or {}
    num = ((P0.get("scal") or {}).get("num")) or {}
    obs = {"tac": raw.get("tac"), "dmod": raw.get("dmod"), "rmod": raw.get("rmod"), "l0": raw.get("l0"),
           "shownL": raw.get("shownL"), "sex": raw.get("sex"), "fm": raw.get("fm"), "lm": raw.get("lm"),
           "pPrevKg": raw.get("pPrevKg")}
    if raw.get("tac") is None:
        v = "unmeasured"
    else:
        v = "as_predicted" if all(num.get(k) == 1.0 for k in ("tac", "dmod", "rmod")) else "falsified"
    grade("parity", "tac, dmod and rmod read exactly 1 at first sight", obs, v, "any of the three not exactly 1")
    # ---- C ----
    C = P.get("C") or {}
    reads = C.get("reads") or []
    d0 = to_num(((C.get("server0") or {}).get("fields") or {}).get("getMaxWeightDelta"))
    bd = to_num(((C.get("scal0") or {}).get("num") or {}).get("delta"))
    tc = to_num(((C.get("scal0") or {}).get("num") or {}).get("traitCarry"))
    first_back = next((r for r in reads if near(to_num((r.get("fields") or {}).get("getMaxWeightDelta")), bd, 1e-3)), None)
    cw0 = to_num((C.get("str0") or {}).get("carryWrites"))
    cw1 = to_num((C.get("str1") or {}).get("carryWrites"))
    obs = {"delta_live0": d0, "body_delta": bd, "traitCarry": tc, "set": (C.get("set") or {}).get("ack"),
           "first_back_dt": first_back.get("dt") if first_back else None, "carryWrites": [cw0, cw1],
           "reads": [(r["dt"], (r.get("fields") or {}).get("getMaxWeightDelta")) for r in reads],
           "client0": C.get("client0"), "client1": C.get("client1")}
    if d0 is None or bd is None:
        v = "unmeasured"
    elif near(d0, bd, 1e-3) and near(bd, (tc or 0) * 1.0, 1e-9) and first_back is not None and first_back["dt"] <= 2.5:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("carry", "delta == traitCarry x (1 + 0) == 1.0; carry.set 2.0 re-asserted at the next slow minute",
          obs, v, "a live delta off body.delta, or 2.0 still read > 2.5 s after the set")
    # ---- X ----
    X = P.get("X") or {}
    g = X.get("grant") or {}
    samples = X.get("samples") or []
    lv = [s["perk"]["level"] for s in samples if s.get("perk")]
    xs = [s["perk"]["xp"] for s in samples if s.get("perk")]
    cl = [s["client_level"]["value"] for s in samples if s.get("client_level")]
    tps = [s["traits"] for s in samples if s.get("traits")]
    e0, e1 = X.get("ev0"), X.get("ev1")
    obs = {"grant": {k: g.get(k) for k in ("xp_before", "level_before", "proteins", "mult", "raw", "xpAfter", "levelAfter")},
           "right_after": (X.get("right_after") or {}).get("perk"),
           "right_after_traits": band_traits(((X.get("right_after") or {}).get("server") or {}).get("traitList")),
           "server_levels": lv, "xp": xs, "client_levels": cl,
           "traits": [(t["server"], t["client"]) for t in tps],
           "levelperk": [ev(e0, "levelperk_count"), ev(e1, "levelperk_count")],
           "levelperk_last": {k: (e1 or {}).get("values", {}).get(k) for k in ("levelperk_lastPerk", "levelperk_lastLevel", "levelperk_lastGained")},
           "str": [X.get("str0"), X.get("str1")], "sync": X.get("sync"), "stout_watch": X.get("watch_result"),
           "scal1": (X.get("scal1") or {}).get("raw")}
    if not lv:
        v = "unmeasured"
    else:
        ok = (g.get("levelAfter") == 6 and all(x == 5 for x in lv[1:]) and lv[0] in (5, 6)
              and all(near(x, XP_L6, 1.0) for x in xs)
              and all("stout" not in t["server"] and "stout" not in t["client"] for t in tps)
              and cl and cl[-1] == 5)
        v = "as_predicted" if ok else "falsified"
    grade("X-clamp", "Java 6 after the grant; the clamp writes 5 within a slow minute; 5 at every sample both "
                     "sides through xp.sync; XP 67600; STOUT absent after the write", obs, v,
          "a level 6 read after the first sample, XP moved, or STOUT present after the write")
    lp = ev(e1, "levelperk_count") - ev(e0, "levelperk_count")
    grade("X39-LevelPerk", "the crossing fires LevelPerk once (Strength, level 6, gained)",
          {"delta": lp, "last": obs["levelperk_last"]},
          "unmeasured" if e0 is None or e1 is None else ("as_predicted" if lp >= 1 else "falsified"),
          "no LevelPerk count move across a real addXp crossing")
    # ---- R ----
    R = P.get("R") or {}
    rr = R.get("reads") or []
    first5 = next((r for r in rr if r.get("level") == 5), None)
    obs = {"write": (R.get("write") or {}).get("ack"),
           "reads": [(round(r["wall"] - (R.get("write") or {}).get("wall", 0), 3), r["level"], r["xp"], r["age"]) for r in rr],
           "first5_dt": round(first5["wall"] - R["write"]["wall"], 3) if first5 else None,
           "str": [R.get("str0"), R.get("str1")], "client_level": R.get("client_level"), "tp": R.get("tp")}
    if not rr:
        v = "unmeasured"
    else:
        v = "as_predicted" if (first5 is not None and all(r["level"] == 5 for r in rr[rr.index(first5):])
                               and first5["wall"] - R["write"]["wall"] <= 2.0) else "falsified"
    grade("R-reassert", "an admin debug write of 3 is re-asserted to 5 within one slow minute", obs, v,
          "level 3 held beyond 2 s, or no write back")
    # ---- U ----
    U = P.get("U") or {}
    age_drop = U.get("age_drop")
    polls = [p for p in U.get("polls") or [] if isinstance(p.get("i"), int)]
    trans = []
    prev = None
    for p in polls:
        sh = p["scal"].get("shownL")
        if prev is not None and sh is not None and sh != prev["scal"].get("shownL"):
            trans.append({"from": prev["scal"].get("shownL"), "to": sh,
                          "age_lo": prev["perk"]["age"], "age_hi": p["perk"]["age"],
                          "h_after_drop_lo": (prev["perk"]["age"] - age_drop) if age_drop is not None and prev["perk"]["age"] is not None else None,
                          "h_after_drop_hi": (p["perk"]["age"] - age_drop) if age_drop is not None and p["perk"]["age"] is not None else None,
                          "java_level": p["perk"]["level"]})
        if sh is not None:
            prev = p
    rest = U.get("restore") or {}
    obs = {"drop": {k: (U.get("drop") or {}).get(k) for k in ("xp_before", "proteins", "mult", "raw", "xpAfter", "levelAfter")},
           "drop_post": U.get("drop_post"), "tp_drop": U.get("tp_drop"), "feeble_watch_drop": U.get("watch_result_drop"),
           "ev_drop": (U.get("ev_drop") or {}).get("values"),
           "restore": {k: rest.get(k) for k in ("xp_before", "proteins", "mult", "raw", "xpAfter", "levelAfter", "age_pre")},
           "restore_post": (U.get("restore_post") or {}).get("perk"), "tp_restore": U.get("tp_restore"),
           "str_restore": U.get("str_restore"), "stout_watch_restore": U.get("watch_result_stout"),
           "transitions": trans, "end": {k: (U.get("end") or {}).get(k) for k in ("perk", "tp", "str")}, "age_drop": age_drop}
    ups = [t for t in trans if t["to"] is not None and t["from"] is not None and t["to"] > t["from"]]
    if len(ups) < 1 or age_drop is None:
        v = "unmeasured"
    else:
        ok1 = ups[0]["to"] == 4 and ups[0]["h_after_drop_hi"] >= RISE_HOLD_H and ups[0]["h_after_drop_lo"] <= RISE_HOLD_H + 0.1
        ok2 = len(ups) >= 2 and ups[1]["to"] == 5 and (ups[1]["age_hi"] - ups[0]["age_lo"]) >= RISE_HOLD_H and (ups[1]["age_lo"] - ups[0]["age_hi"]) <= RISE_HOLD_H + 0.1
        v = "as_predicted" if (ok1 and ok2) else "falsified"
    grade("U-rise", "after the XP drop to level 3 and the restore at +2 h, the shown level stays 3, rises to 4 at "
                    "drop + 6 h and to 5 six hours later", obs, v, "a rise before 6 h, or a two-level step")
    # ---- F ----
    F = P.get("F") or {}
    closes = F.get("closes") or []
    rows = []
    for c in closes:
        b = c.get("body") or {}
        bn = {k: to_num(b.get(k)) for k in ("l0", "lm", "lm0", "n", "nPeak", "tPeakD", "cumDef", "tDisuse", "dayIndex",
                                           "shownL", "lastFallAge", "tac", "rmod", "dmod", "fm")}
        x, ce = ceiling_x(bn)
        rows.append({"dayIndex": bn["dayIndex"], "age": c.get("age"), "lm": bn["lm"], "cumDef": bn["cumDef"],
                     "ceiling_x": x, "ceiling": ce, "shownL": bn["shownL"], "lastFallAge": bn["lastFallAge"],
                     "tac": b.get("tac"), "rmod": b.get("rmod"), "dmod": b.get("dmod"), "fm": bn["fm"]})
    fb = (F.get("fall_body") or {}).get("body") or {}
    fbn = {k: to_num(fb.get(k)) for k in ("l0", "lm", "lm0", "n", "nPeak", "tPeakD", "cumDef", "tDisuse", "dayIndex",
                                         "shownL", "lastFallAge")}
    fx_, fce = ceiling_x(fbn) if fb else (None, None)
    hold_s = (F.get("hold") or {}).get("samples") or []
    wr = F.get("watch_result") or {}
    obs = {"closes": rows, "fell": F.get("fell"), "fall_body_ceiling": [fx_, fce], "fall_body": fbn,
           "fall_delay_game_min": ((fbn["lastFallAge"] - 24 * fbn["dayIndex"]) * 60) if fbn.get("lastFallAge") is not None and fbn.get("dayIndex") is not None else None,
           "fall_tp": F.get("fall_tp"), "fall_str": F.get("fall_str"), "feeble_watch": wr,
           "hold_levels": [(s["perk"]["level"], s["client_level"]["value"]) for s in hold_s],
           "hold_xp": [s["perk"]["xp"] for s in hold_s],
           "hold_traits": [(s["traits"]["server"], s["traits"]["client"]) for s in hold_s if s.get("traits")],
           "hold_str": (F.get("hold") or {}).get("str"), "stop": F.get("stop")}
    if F.get("fell") is None:
        v = "unmeasured"
    else:
        ok = (fce is not None and fce == 4 and fbn.get("shownL") == 4 and obs["fall_delay_game_min"] is not None
              and 0 <= obs["fall_delay_game_min"] <= 1.5 and all(a == 4 for a, _ in obs["hold_levels"])
              and all(near(x, XP_L6, 1.0) for x in obs["hold_xp"])
              and all("feeble" in s_ and "feeble" in c_ for s_, c_ in obs["hold_traits"]))
        v = "as_predicted" if ok else "falsified"
    grade("F-fall", "at the first close whose record ceiling is 4 the level falls 5 -> 4 within one game minute; "
                    "FEEBLE both sides; 4 held 30 s through xp.sync; XP unchanged", obs, v,
          "a fall at a ceiling-5 close, a delay > 1 game minute, a level back to 5, or FEEBLE missing")
    # ---- T (tac across the fast) ----
    tac_rows = []
    prev_tac = None
    for r in rows:
        t = to_num(r["tac"])
        if prev_tac is not None and t is not None:
            tac_rows.append({"dayIndex": r["dayIndex"], "tac_prev": prev_tac, "tac": t, "dtac": t - prev_tac})
        prev_tac = t
    obs = {"fast_tac": tac_rows, "fast_rmod": [r["rmod"] for r in rows], "fast_dmod": [r["dmod"] for r in rows]}
    T = P.get("T") or {}
    tb_pre = ((T.get("pre_body") or {}).get("body")) or {}
    tb_post = ((T.get("post_body") or {}).get("body")) or {}
    v = "unmeasured"
    if tb_pre and tb_post:
        ring = tb_post.get("bandWeek")
        m1, hard = None, None
        try:
            rl = ring if isinstance(ring, list) else [ring[str(i)] for i in range(1, 8)]
            rl = [r if isinstance(r, list) else [r.get("1"), r.get("2")] for r in rl]
            m1 = sum(to_num(r[0]) or 0 for r in rl)
            hard = sum(1 for r in rl if (to_num(r[1]) or 0) >= 10)
        except Exception as e:                 # noqa: BLE001
            obs["ring_error"] = str(e)
        tac_pre = to_num(tb_pre.get("tac"))
        ppk = to_num(tb_post.get("pPrevKg"))
        gp = G_PROT_LOW if (ppk is not None and ppk < 0.8) else 1.0
        if m1 is not None and tac_pre is not None:
            pred, target, gnut = tac_step(tac_pre, m1, hard, gp, 0.5)
            obs.update({"tac_pre": tac_pre, "tac_post": to_num(tb_post.get("tac")), "m1": m1, "hardDays": hard,
                        "pPrevKg": ppk, "target": target, "gnut": gnut, "tac_pred": pred,
                        "rmod_post": tb_post.get("rmod"), "dmod_post": tb_post.get("dmod")})
            v = "as_predicted" if near(to_num(tb_post.get("tac")), pred, 1e-9) else "falsified"
    grade("T-tac", "tac steps by tacDay: 1 -> 0.997619 at the first fasting close, +(1-tac)/15 x 0.425 after; after "
                   "the training day by (target - tac)/15 x 0.425 with target 1 + 0.25 m1/240", obs, v,
          "a post-close tac off the tacDay arithmetic by > 1e-9 (gEnergy assumed 0.5: a fasting day)")
    # ---- H ----
    def slope(H):
        rd = [r for r in (H or {}).get("reads") or [] if r.get("asleep") is True]
        pts = [(to_num(r.get("worldAge")), to_num(r.get("endurance"))) for r in rd]
        pts = [(a, e) for a, e in pts if a is not None and e is not None and e < 0.95]
        if len(pts) < 3:
            return None, len(pts)
        n_ = len(pts)
        ma = sum(a for a, _ in pts) / n_
        me = sum(e for _, e in pts) / n_
        sxx = sum((a - ma) ** 2 for a, _ in pts)
        if sxx <= 0:
            return None, n_
        return sum((a - ma) * (e - me) for a, e in pts) / sxx, n_
    s1, n1 = slope(P.get("H1"))
    s2, n2 = slope(P.get("H2"))
    r1 = to_num((((P.get("H1") or {}).get("scal1") or {}).get("num") or {}).get("rmod"))
    r2 = to_num((((P.get("H2") or {}).get("scal1") or {}).get("num") or {}).get("rmod"))
    ratio = (s2 / s1) if (s1 and s2) else None
    lo = min(r2, (1.7 * r2 + 0.15) / 1.85) if r2 is not None else None
    hi = max(r2, (1.7 * r2 + 0.15) / 1.85) if r2 is not None else None
    obs = {"slope_H1_per_h": s1, "n1": n1, "slope_H2_per_h": s2, "n2": n2, "rmod_H1": r1, "rmod_H2": r2,
           "ratio": ratio, "band": [lo, hi]}
    if ratio is None or r1 is None or r2 is None:
        v = "unmeasured"
    else:
        v = "as_predicted" if (0.80 <= ratio <= 0.90 and r1 == 1.0) else "falsified"
    grade("H-rmod", "H2/H1 endurance slope ratio in [rmod, (1.7 rmod + 0.15)/1.85] ~ [0.848, 0.860]", obs, v,
          "a ratio outside [0.80, 0.90]")
    # ---- D ----
    D = P.get("D") or {}
    rows_d = {}
    prev_ev, prev_trn, prev_sc = D.get("ev0"), D.get("trn0"), (D.get("scal0") or {}).get("num") or {}
    for name in ("squats", "pushups"):
        E = D.get(name) or {}
        e1, t1, sc1 = E.get("ev1"), E.get("trn1") or {}, (E.get("scal1") or {}).get("num") or {}
        d_str = ev(e1, "addxp_Strength_count") - ev(prev_ev, "addxp_Strength_count")
        d_fit = ev(e1, "addxp_Fitness_count") - ev(prev_ev, "addxp_Fitness_count")
        d_reps = (t1.get("reps") or 0) - ((prev_trn or {}).get("reps") or 0)
        rows_d[name] = {"strength_events": d_str, "fitness_events": d_fit, "reps": d_reps,
                        "paired": (t1.get("paired") or 0) - ((prev_trn or {}).get("paired") or 0),
                        "ignored": (t1.get("ignored") or 0) - ((prev_trn or {}).get("ignored") or 0),
                        "repsFitnessOnly": (t1.get("repsFitnessOnly") or 0) - ((prev_trn or {}).get("repsFitnessOnly") or 0),
                        "dvStr": (sc1.get("vStr") or 0) - (prev_sc.get("vStr") or 0),
                        "dvHyp": (sc1.get("vHyp") or 0) - (prev_sc.get("vHyp") or 0),
                        "last_str_amount": (e1 or {}).get("values", {}).get("addxp_Strength_lastAmount"),
                        "last_fit_amount": (e1 or {}).get("values", {}).get("addxp_Fitness_lastAmount"),
                        "exe_after": E.get("exe_after")}
        prev_ev, prev_trn, prev_sc = e1, t1, sc1
    sq = rows_d.get("squats") or {}
    v = "unmeasured" if not sq.get("strength_events") else (
        "as_predicted" if (sq["reps"] == sq["strength_events"] and near(sq["dvStr"], 0.04 * sq["reps"], 0.002 * max(1, sq["reps"]))
                           and near(sq["dvHyp"], 0.05 * sq["reps"], 0.002 * max(1, sq["reps"]))) else "falsified")
    grade("D-reps", "squats: reps == Strength events; dvStr 0.04, dvHyp 0.05 a rep; push-ups reported", rows_d, v,
          "reps off the Strength event count, or vStr/vHyp steps off the class")
    M = P.get("M") or {}
    dh = ev(M.get("ev1"), "hitxp_count") - ev(M.get("ev0"), "hitxp_count")
    dhits = ((M.get("trn1") or {}).get("hits") or 0) - ((M.get("trn0") or {}).get("hits") or 0)
    obs = {"hitxp_delta": dh, "stats_hits_delta": dhits, "attempts": M.get("attempts"), "result": M.get("result"),
           "trn0": M.get("trn0"), "trn1": M.get("trn1"), "ev0": (M.get("ev0") or {}).get("values"),
           "ev1": (M.get("ev1") or {}).get("values")}
    v = "unmeasured" if dh == 0 and dhits == 0 else ("as_predicted" if dh == dhits else "falsified")
    grade("D-hits", "stats.hits delta == OnWeaponHitXp count delta", obs, v, "the two counts differ")


def body():
    run_phase("P0", phase_P0)
    run_phase("C", phase_C)
    run_phase("H1", lambda: hold("H1"))
    run_phase("X", phase_X)
    run_phase("R", phase_R)
    run_phase("U", phase_U)
    run_phase("F", phase_F)
    try:
        if not (out["phases"].get("F") or {}).get("speed_off"):
            out["speed_restore_after_F"] = speed(1, "F_restore")
    except Exception as e:                     # noqa: BLE001
        note(f"speed restore after F raised: {e}")
    run_phase("H2", lambda: hold("H2"))
    run_phase("D", phase_D)
    run_phase("T", phase_T)
    try:
        if not (out["phases"].get("T") or {}).get("speed_off"):
            out["speed_restore_after_T"] = speed(1, "T_restore")
    except Exception as e:                     # noqa: BLE001
        note(f"speed restore after T raised: {e}")
    run_phase("M", phase_M)


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x141c-dry-run", None) if DRY_RUN else new_run_dir("x141c")
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
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_XpEvents"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "prior_runs": PRIOR_RUNS,
    "dry_run": DRY_RUN,
    "constants": {"XP_L6": XP_L6, "XP_L3": XP_L3, "RESTORE_AFTER_H": RESTORE_AFTER_H, "U_MAX_H": U_MAX_H,
                  "CARRY_SET": CARRY_SET, "HOLD_S": HOLD_S, "HOLD_E0": HOLD_E0, "FAST_SPEED": FAST_SPEED,
                  "FAST_MAX_CLOSES": FAST_MAX_CLOSES, "FAST_WALL_BUDGET_S": FAST_WALL_BUDGET_S,
                  "FOODTIMER": FOODTIMER, "SQUAT_MIN": SQUAT_MIN, "PUSHUP_MIN": PUSHUP_MIN,
                  "MELEE_SWINGS": MELEE_SWINGS},
    "deviations": [
        "No record edit: no harness command writes a nested global-modData key (globalmoddata.set writes one "
        "top-level key) and there is no eval command; the ceiling is driven by a timed fast, the target by "
        "server XP grants, rmod by the model's own fasting close (amendments' fallback).",
        "The lean-driven rise (lm restored) is unmeasured in-session; the rise hysteresis is measured on the XP "
        "axis through the same K.strength.policy.",
        "XP grants are divided by vanilla's protein multiplier read off the server store just before each grant "
        "(#2112): the grants are the test's input, the mod never grants.",
        "exercise.do lengths are 40 and 20 GAME minutes (25 s and 12.5 s wall at DayLength 1), not 2: the rep "
        "pace is the animation's (~3 wall s a rep, x141a).",
        "BeyondTen is not loaded in x14-clamp: the T1-1 branch is tested offline only.",
        "Controls: thirst and fatigue pinned 0; the food timer written 20000 during the fast; endurance written "
        "0.05 before each hold and 1 after it and before the training set.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["Strength XP granted and removed by xp.grant", "a zombie spawned by RCON",
                                        "settimespeed returned to 1"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "phase_errors": {}, "speed_changes": [],
    "trait_pairs": [], "events": [],
}

if DRY_RUN:
    print(json.dumps(out)[:3000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)


def _strip_full():
    for r in out["steps"]:
        r.pop("full", None)


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
    _strip_full()
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
        _strip_full()
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
