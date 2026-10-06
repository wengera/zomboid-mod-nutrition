"""x161f-fatigue -- Plan 5 Task 13, acceptance 1: fatigue, endurance, mood, aim and intoxication, LIVE. The
first boot of the whole Plan 5 build (mod at HEAD 4cd19f7, `git status --short mod/` empty). ONE boot of
profile `x16-fatigue` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror OnsetSpeed 30 Severity 1.0
DeficienciesCanKill true ExcessEffectsOn true BalanceBonus true + TKX_StatWatch + TKX_SleepWatch +
TKX_BoozeWatch + TKX_TraitProbe; `Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game
minute 0.625 s; `[server]` SleepAllowed and SleepNeeded true). The run id prefix is `x161f`; ONE artifact
`fatigue.json`. Shape: x161_seats_gate.py (step, stats.all, the StatWatch arm/collect, persist, run_phase,
mod_error) with x151_records2.py's record reads, setpath edits, RCON spawns, coffee and beer containers,
held sleep and the offline kernel in lupa.

WHERE STATE IS READ. The record is the server's global modData `NutritionRevamp.players`, keyed by
username, read with `witness.moddata global:NutritionRevamp.players` and dotted keys on one server tick:
`rec_light` (one call, 30 scalars: acute.S/circ/awakeH/debtH/caf/cafTol/bac/iuSleep/iu/boutH/frozen,
effects.fOff/mAcc/rRec/epoch/the four mood targets/intoxTarget/aimMul/speedMul/fOffNut/drain, nutrients
epoch/lastAgeH, body dmod/rmod, fluids dehydPct/water) and `rec_full` (three calls: the acute, fluids and
effects tables whole, the body scalars, the nutrient aggregates; then the 27 nutrient tables in two calls).
Record edits: `globalmoddata.setpath NutritionRevamp.players admin.<path> <value>`. The stats are read
live on both sides with `stats.all` (client first at every pair). The client mirror is a request-time
snapshot plus the Plan 5 effects push (Task 10): a client mirror read follows a fresh
`bench.global NutritionRevamp.client.requestMirror 1` and the `received` counter moving (ruling T14-1).
The fold's hoisted flag is flipped with `lua.setpath` (Task 12, d3554be; this run is its smoke test).

THE BACKGROUND FATIGUE SERIES (arm A's identity and arm B's crossings). `bg()` runs inside every poll
loop at most every BG_EVERY s: a client `stats.all`, then a server bracket `rec_light` -> `stats.all` ->
`rec_light`. A bracket whose two record reads carry the same `nutrients.lastAgeH` saw no slow minute
between them, so the server FATIGUE read between them was written from exactly that record's S, circ and
fOff: the identity is graded on those brackets only.

SCHEDULE (t = wall seconds from the session being ready; the world age starts near 3.1 h at about 10:08):
  S0  first sight: time.snapshot both sides, the options, the fast handler's flags (endFoldOn, intoxOwned,
      h.admin.endFoldOn, h.admin.intoxOwned, h.admin.effOn, registered), the effects/bus/nutrients
      counters, intox.reduction, the record (waiting up to 20 s for record.effects), stats.all both
      sides, health, a mirror check.
  A   a 19 s StatWatch window (30 game minutes; the damage tags reset to -1 first) with bg brackets every
      ~1.5 s; then the window collected.
  K   cost: three `bench.global NutritionRevamp.bench_fast 100000` (the FIRST a warm-up, discarded:
      stated before the run) and one `tick.rate 10`.
  D   ENDURANCE (X35's handler half, ruling 15's fold). D1 fold OFF (as shipped): ENDURANCE written 0.7,
      10 s of server stats.all at rest (the regeneration arm, vanilla's own); ENDURANCE 1, `exercise.do
      squats 20`, 16 s of pairs (the drain arm). D2 the flip: `lua.setpath
      NutritionRevamp.server.fast.endFoldOn true` and `... .h.admin.endFoldOn true`, both replies read;
      the same rest and squat windows with pairs (client first). D3 `fluids.water` set to -30 x w g
      (dehydPct 3.0) and held there each poll; after 3 s the record's dmod/rmod read; the same two windows.
      D4 water 0, both flags back to false, read back.
  E   STRESS: rec_full; `nutrients.thiamine.p` set to 0.01 (under the clinical rung: grade 4 sticks,
      unlike a `g` edit the minute's grading would undo); a 45 s StatWatch window with server stats.all
      every ~1.5 s; thiamine stays clinical through G and J.
  G   FOOD_SICKNESS: `nutrients.iron.ax 48` and `nutrients.iron.axr 2` (the acute flag holds rung 2 for 48
      game hours; an `x` edit the minute recomputes); a 105 s StatWatch window (100 s cap kept) with
      reads; POISON read throughout.
  J   the Severity dial: `sandbox.var NR.Severity 0`; 3 s; rec_full; 10 s of reads; `sandbox.var
      NR.Severity 1`; 3 s; rec_full.
  G2  `sandbox.var NR.ExcessEffectsOn false`; 3 s; rec_full; a 20 s StatWatch window (the vanilla decay
      with the floor gone); `iron.ax 0`, `iron.axr 0`; `ExcessEffectsOn true`; FOOD_SICKNESS written 0.
  E2  `nutrients.thiamine.p 1`; 25 s of reads (the target falls as the grade climbs back, the stress decays).
  H   INTOXICATION: RCON `additem Base.BeerCan`; client `drink.action Base.BeerCan 1`; a 70 s StatWatch
      window, rec_light and server stats.all every ~1.5 s, `intox.reduction` read before and after.
  BW  the awake run continues: bg every 3 s until the server FATIGUE reads >= 0.82 or 240 s pass.
  C   coffee: RCON `additem Base.WaterBottle`; server `fluid.fill admin Base.WaterBottle Coffee 0.25`
      (107 mg at 428 mg/L); client `drink.action Base.WaterBottle 1`; 60 s of rec_light + stats.all pairs.
  SL  held sleep: `fluids.water 0`; `player.sleep.hold admin 20`; every ~2 s rec_light, a server stats.get
      (asleep) and stats.all, water reset to 0 (the ~20x clock of a held sleep, ruling T5-1); cancel; reads.
  F   PANIC and UNHAPPINESS: `acute.awakeH 24`; a 60 s StatWatch window with reads; `acute.caf 440`; a 45 s
      window; `acute.awakeH 0`; a 25 s window.
  I   aim: `acute.awakeH 24` and `acute.caf 0`; 3 s; rec_full; a mirror check; client lua.global reads of
      NutritionRevamp.client.effects.stats (swings, reads, noMirror, notLocal, errors) and lastAimMul,
      lastDelay, lastWouldBe; `zombie.near 1`; `aim.probe admin 30`; `aim.fire 3`; wait for aim-probe.json;
      the client reads again; `acute.awakeH 0`.
  Z   the counters, lastErrors, health, stats both sides, intox.reduction, the flags.

PREDICTIONS (written before the run; every number marked LIVE is recomputed in `grade_all` through the
mod's own kernels run offline in lupa at this commit, from the live record, never from a hand value).
  A   record.effects exists within the first slow minutes with ev 1, epoch >= 1 and fOff, mAcc, rRec finite.
      FATIGUE identity: at every same-minute bracket the server's FATIGUE equals float32(out.fatigue) of
      K.fast.step run offline on the bench input with fOwned true, fFrozen false, fS = acute.S, fCirc =
      acute.circ, fOff = effects.fOff from that record (LIVE); falsifier any bracket off by more than one
      float32 ulp. The client's FATIGUE equals a server value read in the 2.5 s before it (the 1 Hz push),
      counted. HUNGER <= 0.69 and THIRST <= 0.83 at EVERY stats.all read of the session on both sides
      (ruling 14, the view caps in K.fast); `OnPlayerGetDamage HUNGRY` count 0 in every StatWatch window.
      nutrients.epoch and effects.epoch both rise over the session.
  K   bench_fast within 10 % of #3003 (3.24-3.47 us; the band's top 3.817 us) on runs 2 and 3; the bench
      input changed at 2ebef91 (the fold's regeneration arm and the owned writer), so a reading above the
      band names the region's growth, not noise.
  D   (rest) slope_on / slope_off = body.rmod read in the window (the fold's regeneration arm, LIVE: the
      kernel's K.fast.step fold on the off-window's mean per-read delta reproduces the ratio); in D3 the
      ratio is the dehydrated rmod (< the D2 value: K.aerobic.rmod's dehydration factor recomputed LIVE).
      (squats) drop_on / drop_off = body.dmod read (D2) and the dehydrated dmod (D3, > 1; K.aerobic.dmod's
      dehydration factor recomputed LIVE, heat level 0) -- a coarse two-window comparison (regularity rises
      between sets), graded within 15 %. X35: during the fold-on windows every client ENDURANCE copy equals
      a server value read before it (the handler's write is what the push carries); falsifier a client
      copy matching no server read while the server series moves.
  E   stressTarget 0.06 at the rebuild after the edit (LIVE compose: bgroupMax 4 -> 0.06; any other active
      row is in the replay); STRESS rises at (moodRiseStress - stressDecrease) = 2e-5 per game-second
      (0.072 per game hour) net of vanilla's decay, reaches float32(target) and holds there; falsifier a
      plateau below the target or a rise at the gross 5e-5.
  G   foodSickTarget 55 (LIVE compose: iron rung {1,3} 30 and {2,3} 55, max); FOOD_SICKNESS rises at
      25 per game hour gross less vanilla's 0.0015 x mult decay (X76: 2.7 per game hour) = 22.3 per game
      hour, reaches 55 and holds; POISON 0 at every read.
  J   Severity 0: stressTarget, panicTarget, foodSickTarget 0 and speedMul 1 at the next rebuild (LIVE
      compose at sev 0), drain unchanged; Severity 1 restores the set.
  G2  ExcessEffectsOn false: iron.x 0 at the output, foodSickTarget 0; FOOD_SICKNESS decays at vanilla's
      ~2.7 per game hour (X76).
  E2  thiamine p 1: the grade climbs 4 -> 1 one rung a minute (hysteresis), the target leaves 0.06 and the
      stat decays at 3e-5 per game-second (0.108 per game hour).
  H   intoxOwned true: at every same-minute bracket the server's INTOXICATION equals
      float32(K.effects.intoxTarget(acute.bac)) (LIVE); the StatWatch max sits at the record's peak target
      (100 x bac / 0.20, about 2.8 at the gut-lane peak for this subject, LIVE), not at vanilla's +6 jump
      (#3051-#3069: 0.3 L x 0.05 x 400); `intox.reduction` reads 0.
  B   the crossings of 0.6, 0.7 and 0.8 by the server FATIGUE series (linear interpolation in world age)
      against the same crossings of S_rep + circ_rep + fOff_live, where S_rep is K.acute.sleepMinute
      replayed offline from the first record read, step by step between the bg reads with the previous
      read's mAcc and the hour of day from the time offset (LIVE); I-B7's 07:00-wake crossings (14.305 /
      16.278 / 18.648 h awake) are the briefing's literal for a different waking hour and are reported only
      beside it: this subject is rested (S 0.17) at first sight near 10:08. Held sleep: between consecutive
      asleep reads S follows K.acute.sleepMinute(asleep, rRec read) (chi_s 4.2 / rRec) to the debt floor
      and FATIGUE follows S + circ + fOff.
  C   at every record read effects.fOff equals K.effects.fOff(debtH, caf, cafTol, fOffNut) (LIVE), and the
      caffeine offset fOff(caf 0) - fOff(caf) grows with acute.caf toward cafOffset(107, cafTol) = 0.1457 at
      cafTol 0; FATIGUE follows within the same minute.
  F   awakeH 24: iuSleep 1 + debtH / 10.5 (LIVE), panicTarget 14 and unhappyTarget 16.666666666666668 at
      debt 0 (LIVE compose); UNHAPPINESS rises at 22 per game hour (vanilla never decays it) to the target;
      PANIC by design rises at 24 per game hour -- but the per-tick rise 24/3600 x s (s ~9.6 game-s at 10
      ticks/s, ~0.064) is below vanilla's per-update ReducePanic measured at ~0.18 per tick (X88, gate 1),
      so the falsifier is a PANIC that hovers near one tick's rise; caf 440 (band 8 for ~40 game minutes;
      400 itself falls into band 7 within one game minute at the 5 h half-life) adds 15 to panicTarget;
      awakeH 0 drops the targets: UNHAPPINESS falls once by the target's fall (T1-2's release), PANIC is
      left to vanilla.
  I   aimMul = clamp(1 + 0.25 x band(iu) x 0.1) (LIVE; 1.25 at iu 1.0, caffeine 0); the client mirror's
      effects_aimMul equals the record's after a request; the stub logs, never writes: the aiming delay in
      aim-probe.json is not scaled by aimMul (X86's engine reset dominates); speedMul stamped, no speed write
      (a source fact, not read live).

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Arm D's drain is the squat set (`exercise.do squats`), not a run: no run has ever reached the server
     (#0591; x141a's server read neither flag), while x141a's squats drained the server's endurance
     1 -> 0.909; the regeneration arm at rest is the clean fold reading (the regen arm is rmod, not dmod).
  2. Arm D's dehydration is held through `fluids.water` (-30 x w g = 3.0 %): a `dehydPct` edit is
     recomputed from the water pool in the same minute (NR_Server_Nutrients) before Metabolism reads it.
  3. Arm E edits thiamine's store `p`, not its grade `g` (the minute regrades from p and would undo a g edit
     before the effects step reads it).
  4. Arm F's caffeine is 440 mg, not 400: 400 falls into band 7 (13.125) within one game minute.
  5. Arm I runs at awakeH 24 with caffeine 0 (the caffeine credit would cancel the sleep term) and last
     before Z, because the spawned zombie attacks and raises PANIC (vanilla's sightings).
  6. Moodle levels are inferred from the stat copies against #2369; no harness command reads the PANIC,
     UNHAPPY, SICK or TIRED moodles (stats.get's moodle table carries five others).
  7. The mod is not touched: HEAD's handler and adapters run underneath every arm.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import glob
import json
import math
import os
import re
import shutil
import struct
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

PROFILE = "x16-fatigue"
SESSION = ("Plan 5 acceptance 1, live: the FATIGUE writer and the view caps (A), the Tired crossings and a "
           "held sleep (B), coffee (C), the endurance fold (D, X35's handler half), the stress floor (E), "
           "panic and unhappiness (F), the FOOD_SICKNESS floor (G), INTOXICATION (H), aim and speed unapplied "
           "(I), the Severity dial (J), cost (K); one boot of x16-fatigue at DayLength 1")
ARTIFACT = "fatigue.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(MOD_LUA, "shared")
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"
SELFTEST = os.environ.get("X161F_SELFTEST") == "1"

STORE = "NutritionRevamp.players"
ORDER = ("vitC", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "vitA", "vitD",
         "vitE", "vitK", "pantothenate", "biotin", "iron", "zinc", "copper", "magnesium", "calcium", "iodine",
         "selenium", "fibre", "efa", "sodium", "potassium", "caffeine", "ethanol")
LIGHT = ("acute.S", "acute.circ", "acute.awakeH", "acute.debtH", "acute.caf", "acute.cafTol", "acute.bac",
         "acute.iuSleep", "acute.iu", "acute.boutH", "acute.frozen", "effects.fOff", "effects.mAcc", "effects.rRec",
         "effects.epoch", "effects.stressTarget", "effects.panicTarget", "effects.unhappyTarget",
         "effects.foodSickTarget", "effects.intoxTarget", "effects.aimMul", "effects.speedMul", "effects.fOffNut",
         "effects.drain", "nutrients.epoch", "nutrients.lastAgeH", "body.dmod", "body.rmod", "fluids.dehydPct",
         "fluids.water")
BODY_KEYS = ("fm", "lm", "sex", "met", "dmod", "rmod", "tac", "energyState", "dayIndex", "band1Day", "band2Day",
             "bornAge")
NUT_SCAL = ("epoch", "lastAgeH", "allReplete", "anaemia", "vitDClinical", "ironGrade")
FULL1 = ([f"{USER}.acute", f"{USER}.fluids", f"{USER}.effects", f"{USER}.dead"]
         + [f"{USER}.body.{k}" for k in BODY_KEYS] + [f"{USER}.nutrients.{k}" for k in NUT_SCAL])
NUT1 = [f"{USER}.nutrients.{k}" for k in ORDER[:14]]
NUT2 = [f"{USER}.nutrients.{k}" for k in ORDER[14:]]
OPT_KEYS = ("mode", "onsetSpeed", "deficienciesCanKill", "excessEffectsOn", "balanceBonus", "severity", "nutritionOn")
FAST = "NutritionRevamp.server.fast"
FLAG_PATHS = (f"{FAST}.endFoldOn", f"{FAST}.intoxOwned", f"{FAST}.h.{USER}.endFoldOn",
              f"{FAST}.h.{USER}.intoxOwned", f"{FAST}.h.{USER}.effOn", f"{FAST}.registered")
EFF_STATS = ("minutes", "errors", "rebuilds", "healed", "regenWrites", "traitAdds", "drainMinutes", "bruises")
BUS_STATS = ("marks", "pushes", "deferred", "failed")
NUT_STATS = ("minutes", "errors", "effectsErrors", "players")
CE_KEYS = ("stats.swings", "stats.reads", "stats.noMirror", "stats.notLocal", "stats.errors", "lastAimMul",
           "lastDelay", "lastWouldBe", "lastError")
MIRROR_KEYS = ("effects_epoch", "effects_aimMul", "effects_speedMul", "effects_stressTarget", "effects_panicTarget",
               "effects_unhappyTarget", "effects_foodSickTarget", "effects_intoxTarget", "effects_fOff", "effects_mAcc",
               "effects_rRec", "effects_drain", "acute_awakeH", "acute_caf", "acute_iu", "nutrients_epoch")
SW = "TKX_StatWatch"
SW_FIELDS = ("fatigue", "intoxication", "endurance", "stress", "panic", "unhappiness", "food_sickness", "poison",
             "sickness", "boredom", "temperature", "core")
SW_TAGS = ("POISON", "SICK", "FALLDOWN", "BLEEDING", "HUNGRY", "THIRST", "HEAVYLOAD", "other")
SW_DONE_WAIT = 12.0
BOTTLE, BEER = "Base.WaterBottle", "Base.BeerCan"
COFFEE_L = 0.25
BG_EVERY = 3.0
A_S = 19
D_REST_S, D_SQUAT_S, D_SQUAT_MIN, D_DEHYD_PCT = 10, 16, 20, 3.0
E_S, G_S, G2_S, E2_S, H_S = 45, 105, 20, 25, 70
F1_S, F2_S, F3_S = 60, 45, 25
F_CAF = 440
BW_CAP_S, BW_STOP_F = 240, 0.82
C_S, SL_S = 60, 20
AIM_S = 30
TICK_S = 10
BENCH_N = 100000
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
HEALTH_GUARD = 40.0
MIRROR_WAIT_S = 8.0
BAND_3003 = (3.24, 3.47)
HUNGER_CAP, THIRST_CAP = 0.69, 0.83

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE|NutritionRevamp.*(fail|error)")
LUAERR_LIMIT = 40
INI_RX = re.compile(r"^(SleepAllowed|SleepNeeded)=(.*)$")
MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|nutrients: .* failed|effects: .* failed")


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


def f32(x):
    try:
        return struct.unpack("f", struct.pack("f", x))[0]
    except (OverflowError, struct.error, TypeError):
        return None


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    if path is None:
        return
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
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def gv(side, name, tag):
    a = ack(step(tag, side, "lua.global", name))
    if not a.get("resolved"):
        return None
    v = a.get("value")
    n = to_num(v)
    return n if n is not None else v


# ---------------------------------------------------------------- reads and writes
def sall(tag, side, phase=None):
    r = step(tag, side, "stats.all", USER if side is server else "")
    a = ack(r)
    st = a.get("stats") if isinstance(a.get("stats"), dict) else {}
    row = {"tag": tag, "phase": phase or cur_phase["name"], "side": "server" if side is server else "client",
           "wall": r["wall_before"], "wall_after": r["wall_after"], "sideWall": a.get("wall"),
           "worldAge": a.get("worldAge"), "mult": a.get("mult"), "stats": st}
    if not st:
        row["reply"] = r["ack"]
    out["stats_all"].append(row)
    return row


def sget(tag):
    r = step(tag, server, "stats.get", USER)
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "worldAge": a.get("worldAge"),
           "asleep": a.get("asleep"), "moving": a.get("moving"), "running": a.get("running"),
           "fatigue": a.get("fatigue"), "endurance": a.get("endurance"), "hunger": a.get("hunger"),
           "thirst": a.get("thirst"), "moodles": a.get("moodles")}
    out["stats_get"].append(row)
    return row


def hget(tag, side):
    r = step(tag, side, "health.get", USER)
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "side": "server" if side is server else "client",
           "wall": r["wall_before"], "overall": a.get("overall"), "ok": a.get("ok")}
    out["health_reads"].append(row)
    return row


def setany(tag, stat, v):
    r = step(tag, server, "stats.setany", f"{USER} {stat} {v}")
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "wall_after": r["wall_after"],
           "stat": stat, "ok": a.get("ok"), "requested": a.get("requested"), "before": a.get("before"),
           "after": a.get("after"), "reason": a.get("reason")}
    out["stat_writes"].append(row)
    return row


def rec_light(tag):
    keys = [f"{USER}.{k}" for k in LIGHT]
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(keys))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "wall_after": r["wall_after"],
           "worldAge": a.get("worldAge"), "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"),
           "error": a.get("error")}
    for k in LIGHT:
        v = vals.get(f"{USER}.{k}")
        row[k] = v if isinstance(v, bool) else (to_num(v) if to_num(v) is not None else v)
    out["recs"].append(row)
    return row


def rec_full(tag):
    row = {"tag": tag, "phase": cur_phase["name"], "wall": wall(), "calls": []}
    merged = {}
    for j, keys in enumerate((FULL1, NUT1, NUT2)):
        r = step(f"{tag}_f{j}", server, "witness.moddata", f"global:{STORE} " + " ".join(keys))
        a = ack(r)
        vals = a.get("values") if isinstance(a.get("values"), dict) else {}
        row["calls"].append({"wall": r["wall_before"], "worldAge": a.get("worldAge"), "missing": a.get("missing"),
                             "truncatedAt": a.get("truncatedAt"), "error": a.get("error"),
                             "lastAgeH": vals.get(f"{USER}.nutrients.lastAgeH")})
        merged.update(vals)
    row["acute"] = merged.get(f"{USER}.acute")
    row["fluids"] = merged.get(f"{USER}.fluids")
    row["effects"] = merged.get(f"{USER}.effects")
    row["dead"] = merged.get(f"{USER}.dead")
    row["body"] = {k: merged.get(f"{USER}.body.{k}") for k in BODY_KEYS}
    row["nutrients"] = {k: merged.get(f"{USER}.nutrients.{k}") for k in NUT_SCAL}
    for k in ORDER:
        row["nutrients"][k] = merged.get(f"{USER}.nutrients.{k}")
    out["full"].append(row)
    return row


def setpath(tag, field, value):
    a = ack(step(tag, server, "globalmoddata.setpath", f"{STORE} {USER}.{field} {value}"))
    row = {"tag": tag, "phase": cur_phase["name"], "field": field, "value": value, "wall": wall(), "ack": a}
    out["edits"].append(row)
    return row


def luaset(tag, pth, value):
    a = ack(step(tag, server, "lua.setpath", f"{pth} {value}"))
    row = {"tag": tag, "phase": cur_phase["name"], "path": pth, "value": value, "wall": wall(), "ack": a}
    out["luasets"].append(row)
    return row


def sandbox(tag, key, value):
    a = ack(step(tag, server, "sandbox.var", f"{key} {value}"))
    row = {"tag": tag, "phase": cur_phase["name"], "key": key, "value": value, "wall": wall(), "ack": a}
    out["sandbox"].append(row)
    return row


def flags(tag):
    return {p: gv(server, p, f"{tag}_{p.split('.')[-1]}_{i}") for i, p in enumerate(FLAG_PATHS)}


def counters(tag):
    return {"effects": {k: gv(server, f"NutritionRevamp.server.effects.stats.{k}", f"{tag}_es_{k}") for k in EFF_STATS},
            "effects_lastError": gv(server, "NutritionRevamp.server.effects.lastError", f"{tag}_ele"),
            "bus": {k: gv(server, f"NutritionRevamp.server.bus.effects.stats.{k}", f"{tag}_bs_{k}") for k in BUS_STATS},
            "nutrients": {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"{tag}_ns_{k}") for k in NUT_STATS},
            "nutrients_lastError": gv(server, "NutritionRevamp.server.nutrients.lastError", f"{tag}_nle"),
            "fast": {k: gv(server, f"{FAST}.stats.{k}", f"{tag}_fs_{k}") for k in ("calls", "failures", "disabledAt")},
            "fast_lastError": gv(server, f"{FAST}.lastError", f"{tag}_fle")}


def options(tag):
    return {k: gv(server, f"NutritionRevamp.server.options.{k}", f"{tag}_opt_{k}") for k in OPT_KEYS}


def ce_read(tag):
    return {k: gv(client, f"NutritionRevamp.client.effects.{k}", f"{tag}_ce_{k.replace('.', '_')}") for k in CE_KEYS}


def mirror_check(tag):
    before = gv(client, "NutritionRevamp.client.received", f"{tag}_recv0")
    req = ack(step(f"{tag}_req", client, "bench.global", "NutritionRevamp.client.requestMirror 1"))
    after = before
    end = time.time() + MIRROR_WAIT_S
    while time.time() < end:
        time.sleep(0.5)
        after = gv(client, "NutritionRevamp.client.received", f"{tag}_recv")
        if to_num(after) is not None and to_num(before) is not None and to_num(after) > to_num(before):
            break
        if to_num(before) is None and to_num(after) is not None:
            break
    keys = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"{tag}_m_{k}") for k in MIRROR_KEYS}
    srv = rec_light(f"{tag}_srv")
    row = {"tag": tag, "phase": cur_phase["name"], "request": req, "received_before": before,
           "received_after": after, "answered": (to_num(after) or 0) > (to_num(before) or 0),
           "wall_answered": wall(), "client": keys, "server_rec": srv["tag"]}
    out["mirror_checks"].append(row)
    return row


def bracket(tag):
    """rec_light -> server stats.all -> rec_light: a same-minute bracket when both lastAgeH agree."""
    r1 = rec_light(f"{tag}_r1")
    s = sall(f"{tag}_s", server)
    r2 = rec_light(f"{tag}_r2")
    row = {"tag": tag, "phase": cur_phase["name"], "r1": r1["tag"], "s": s["tag"], "r2": r2["tag"],
           "same": (r1.get("nutrients.lastAgeH") is not None
                    and r1.get("nutrients.lastAgeH") == r2.get("nutrients.lastAgeH"))}
    out["brackets"].append(row)
    return row


def bg(force=False):
    if not force and wall() - bgstate["last"] < BG_EVERY:
        return None
    bgstate["last"] = wall()
    i = bgstate["n"]
    bgstate["n"] += 1
    c = sall(f"bg{i}_c", client)
    b = bracket(f"bg{i}")
    row = {"i": i, "phase": cur_phase["name"], "c": c["tag"], "bracket": b["tag"], "wall": wall()}
    out["bg"].append(row)
    return row


def poll(prefix, seconds, every=1.5, client_every=2, extra=None, light_every=0):
    """Server stats.all every `every` s (client first on every `client_every`-th), rec_light every
    `light_every`-th (0: never), bg() whenever due; `extra(i)` called each round."""
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        t_s = wall()
        row = {"i": i}
        if client_every and i % client_every == 0:
            row["c"] = sall(f"{prefix}_c{i}", client)["tag"]
        row["s"] = sall(f"{prefix}_s{i}", server)["tag"]
        if light_every and i % light_every == 0:
            row["r"] = rec_light(f"{prefix}_r{i}")["tag"]
        if extra is not None:
            try:
                extra(i, row)
            except Exception as e:             # noqa: BLE001
                row["extra_error"] = f"{type(e).__name__}: {e}"
        bg()
        rows.append(row)
        i += 1
        rest = every - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    return rows


def gset(tag, key, value):
    return ack(step(tag, server, "globalmoddata.set", f"{SW} {key} {value}"))


def md_read(tag, keys):
    vals, missing = {}, []
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        a = ack(step(f"{tag}_{j}", server, "witness.moddata", f"global:{SW} " + " ".join(ch)))
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
    return {"values": vals, "missing": missing, "wall": wall()}


def sw_status(tag):
    return ack(step(tag, server, "witness.moddata", f"global:{SW} status samples windowMs arm")).get("values") or {}


def sw_arm(tag, seconds):
    """Reset every damage-tag key to -1 (the probe never clears a previous window's keys: the T3 review's
    instrument note), then arm and wait for `armed`."""
    for t in SW_TAGS:
        gset(f"{tag}_rd_{t}", f"dmg_{t}", -1)
        gset(f"{tag}_rs_{t}", f"dmgsum_{t}", -1)
    res = {"seconds": seconds, "tags_reset_to": -1}
    r = step(f"{tag}_arm", server, "globalmoddata.set", f"{SW} arm {seconds}")
    res["arm_wall"] = r["wall_after"]
    res["armed_seen_wall"] = None
    end = wall() + 8.0
    while wall() < end:
        if sw_status(f"{tag}_armchk").get("status") == "armed":
            res["armed_seen_wall"] = wall()
            break
        time.sleep(0.25)
    return res


def parse_raw(s):
    d = {}
    for part in str(s).split(" "):
        if "=" in part:
            k, v = part.split("=", 1)
            n = to_num(v)
            d[k] = n if n is not None else v
    return d


def sw_collect(tag, arm):
    end = (arm.get("armed_seen_wall") or arm["arm_wall"]) + arm["seconds"] + SW_DONE_WAIT
    done = None
    while wall() < end:
        s = sw_status(f"{tag}_donechk")
        if s.get("status") == "done":
            done = s
            break
        time.sleep(1.0)
    keys = ["samples", "windowMs", "status"]
    for f in SW_FIELDS:
        keys += [f"first_{f}", f"last_{f}", f"min_{f}", f"max_{f}", f"n_{f}", f"absent_{f}"]
    keys += [f"dmg_{t}" for t in SW_TAGS] + [f"dmgsum_{t}" for t in SW_TAGS]
    sc = md_read(f"{tag}_scal", keys)
    raws = md_read(f"{tag}_raw", [f"raw_{i}" for i in range(1, 61)])
    g = sc["values"]
    raw_s = [raws["values"][f"raw_{i}"] for i in range(1, 61) if raws["values"].get(f"raw_{i}") is not None]
    flds = {f: {"first": to_num(g.get(f"first_{f}")), "last": to_num(g.get(f"last_{f}")),
                "min": to_num(g.get(f"min_{f}")), "max": to_num(g.get(f"max_{f}")),
                "n": to_num(g.get(f"n_{f}")), "absent": g.get(f"absent_{f}")} for f in SW_FIELDS}
    dmg = {t: {"count": to_num(g.get(f"dmg_{t}")), "sum": to_num(g.get(f"dmgsum_{t}"))} for t in SW_TAGS}
    res = {"done": done, "status": g.get("status"), "samples": to_num(g.get("samples")),
           "windowMs": to_num(g.get("windowMs")), "fields": flds, "dmg": dmg, "raw_strings": raw_s,
           "raw": [parse_raw(v) for v in raw_s], "collected_wall": wall()}
    out["watches"].append({"tag": tag, "phase": cur_phase["name"], "arm": arm, "result": res})
    return res


def wait_res(name, after, timeout):
    try:
        return client.bus.wait_result(name, timeout=timeout, after=after)
    except Exception as e:                     # noqa: BLE001 - recorded, not raised
        return {"error": f"{type(e).__name__}: {e}"}


def tick_rate(label):
    after = time.time()
    arm = ack(step(f"{label}_tick_arm", server, "tick.rate", str(TICK_S)))
    res = None
    if arm.get("armed"):
        try:
            res = server.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 20, after=after)
        except (RuntimeError, TimeoutError, OSError) as e:
            res = {"error": f"{type(e).__name__}: {e}"}
    return {"arm": arm, "result": res}


def read_ini(srv):
    vals = {"path": None, "values": {}, "error": None}
    try:
        vals["path"] = os.path.relpath(srv.ini, REPO)
        with open(srv.ini, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = INI_RX.match(line.strip())
                if m:
                    vals["values"][m.group(1)] = m.group(2)
    except Exception as e:                     # noqa: BLE001
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def spawn(full_type, why):
    ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200], "wall_rcon": wall(),
           "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", client, "witness.fields", f"item {USER}/{full_type} getID"))
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": seen.get("resolved"),
                                "id": (seen.get("fields") or {}).get("getID")})
        if seen.get("resolved"):
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    out["spawns"].append(row)
    return row


def litres(tag, side, full_type):
    args = f"getInventory.getFirstTypeRecurse({full_type}).getFluidContainer.getAmount"
    if side is server:
        args = f"{USER} {args}"
    a = ack(step(tag, side, "witness.chain", args))
    return to_num(a.get("value"))


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def mod_error(after):
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    le = gv(server, "NutritionRevamp.server.nutrients.lastError", f"chk_{after}_nle")
    ne = gv(server, "NutritionRevamp.server.nutrients.stats.errors", f"chk_{after}_nerr")
    ee = gv(server, "NutritionRevamp.server.nutrients.stats.effectsErrors", f"chk_{after}_neff")
    xe = gv(server, "NutritionRevamp.server.effects.stats.errors", f"chk_{after}_eerr")
    xl = gv(server, "NutritionRevamp.server.effects.lastError", f"chk_{after}_ele")
    fe = gv(server, f"{FAST}.stats.failures", f"chk_{after}_ffail")
    fd = gv(server, f"{FAST}.stats.disabledAt", f"chk_{after}_fdis")
    if (le is not None or (to_num(ne) or 0) > 0 or (to_num(ee) or 0) > 0 or (to_num(xe) or 0) > 0
            or xl is not None or (to_num(fe) or 0) > 0 or fd is not None):
        why.append({"nutrients_lastError": le, "nutrients_errors": ne, "effects_errors_nut": ee,
                    "effects_errors": xe, "effects_lastError": xl, "fast_failures": fe, "fast_disabledAt": fd})
    if clients and "lua_error" in getattr(clients[0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    h = hget(f"chk_{after}_h", server)
    o = to_num(h.get("overall"))
    if o is not None and o < HEALTH_GUARD:
        why.append({"health_guard": o})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why, "health": o})
    return why


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["time_server"] = ack(step("S0_time_s", server, "time.snapshot"))
    P["time_client"] = ack(step("S0_time_c", client, "time.snapshot"))
    P["options"] = options("S0")
    P["flags"] = flags("S0_flags")
    P["intox_reduction"] = ack(step("S0_intox", server, "intox.reduction", USER))
    P["version"] = {"server": gv(server, "NutritionRevamp.version", "S0_ver_s"),
                    "client": gv(client, "NutritionRevamp.version", "S0_ver_c")}
    waited = []
    end = wall() + 20.0
    first = None
    while wall() < end:
        r = rec_light(f"S0_wait{len(waited)}")
        waited.append(r["tag"])
        if r.get("effects.epoch") is not None and r.get("acute.S") is not None:
            first = r
            break
        time.sleep(1.0)
    P["wait_recs"] = waited
    P["first_effects_rec"] = first["tag"] if first else None
    P["full"] = rec_full("S0_full")["tag"]
    P["counters"] = counters("S0_cnt")
    P["stats_client"] = sall("S0_c", client)["tag"]
    P["stats_server"] = sall("S0_s", server)["tag"]
    P["health"] = hget("S0_h", server)["tag"]
    P["mirror"] = mirror_check("S0_mirror")["tag"]
    P["ce"] = ce_read("S0")
    bg(force=True)


def phase_A():
    P = out["phases"]["A"] = {}
    P["arm"] = sw_arm("A", A_S)
    rows = []
    end = P["arm"]["arm_wall"] + A_S
    while wall() < end:
        rows.append(bg(force=True))
        time.sleep(0.3)
    P["bgs"] = [r["i"] for r in rows if r]
    P["watch"] = sw_collect("A", P["arm"])
    P["full_after"] = rec_full("A_full")["tag"]


def phase_K():
    P = out["phases"]["K"] = {"bench": []}
    for i in range(3):
        a = ack(step(f"K_bench{i}", server, "bench.global", f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60))
        P["bench"].append({"i": i, "discarded": i == 0, "ack": a})
    P["tick"] = tick_rate("K")
    bg(force=True)


def endurance_window(prefix, write, seconds, squats):
    W = {"write": setany(f"{prefix}_w", "ENDURANCE", write)["tag"], "start": wall()}
    W["rec_start"] = rec_light(f"{prefix}_rs")["tag"]
    if squats:
        W["squats"] = ack(step(f"{prefix}_sq", client, "exercise.do", f"squats {D_SQUAT_MIN}"))
    W["polls"] = poll(prefix, seconds, every=0.5, client_every=1)
    W["rec_end"] = rec_light(f"{prefix}_re")["tag"]
    W["get_end"] = sget(f"{prefix}_ge")["tag"]
    W["end"] = wall()
    if squats:
        W["stop"] = ack(step(f"{prefix}_stop", client, "player.stop", ""))
        time.sleep(2.0)
    return W


def phase_D():
    P = out["phases"]["D"] = {}
    P["flags0"] = flags("D0_flags")
    P["full0"] = rec_full("D0_full")["tag"]
    # D1: the fold OFF (as shipped)
    P["D1_rest"] = endurance_window("D1r", 0.7, D_REST_S, False)
    P["D1_squat"] = endurance_window("D1q", 1, D_SQUAT_S, True)
    persist()
    # D2: the flip
    P["set_global"] = luaset("D2_set_g", f"{FAST}.endFoldOn", "true")
    P["set_handle"] = luaset("D2_set_h", f"{FAST}.h.{USER}.endFoldOn", "true")
    P["flags2"] = flags("D2_flags")
    P["D2_rest"] = endurance_window("D2r", 0.7, D_REST_S, False)
    P["D2_squat"] = endurance_window("D2q", 1, D_SQUAT_S, True)
    persist()
    # D3: dehydration 3 % held through the water pool
    full = rec_full("D3_pre")
    b = full.get("body") or {}
    w = (to_num(b.get("fm")) or 0) + (to_num(b.get("lm")) or 0)
    water = -D_DEHYD_PCT * w * 10 if w > 0 else -2400
    P["D3_w"], P["D3_water"] = w, water
    P["D3_set"] = setpath("D3_water", "fluids.water", water)
    time.sleep(3.0)
    P["D3_full"] = rec_full("D3_full")["tag"]

    P["D3_rest"] = endurance_window("D3r", 0.7, D_REST_S, False)
    setpath("D3_water2", "fluids.water", water)
    P["D3_squat"] = endurance_window("D3q", 1, D_SQUAT_S, True)
    P["D3_full_end"] = rec_full("D3_full_end")["tag"]
    # D4: restore
    P["D4_water"] = setpath("D4_water", "fluids.water", 0)
    P["unset_global"] = luaset("D4_unset_g", f"{FAST}.endFoldOn", "false")
    P["unset_handle"] = luaset("D4_unset_h", f"{FAST}.h.{USER}.endFoldOn", "false")
    P["flags4"] = flags("D4_flags")
    P["end_write"] = setany("D4_e1", "ENDURANCE", 1)["tag"]
    time.sleep(2.0)
    P["full4"] = rec_full("D4_full")["tag"]


def phase_E():
    P = out["phases"]["E"] = {}
    P["full_before"] = rec_full("E_before")["tag"]
    P["edit"] = setpath("E_thia", "nutrients.thiamine.p", 0.01)
    P["arm"] = sw_arm("E", E_S)
    time.sleep(1.5)
    P["full_after"] = rec_full("E_after")["tag"]
    P["polls"] = poll("E", E_S - 6, every=1.5, client_every=2, light_every=3)
    P["watch"] = sw_collect("E", P["arm"])


def phase_G():
    P = out["phases"]["G"] = {}
    P["edit_ax"] = setpath("G_ax", "nutrients.iron.ax", 48)
    P["edit_axr"] = setpath("G_axr", "nutrients.iron.axr", 2)
    P["arm"] = sw_arm("G", G_S)
    time.sleep(1.5)
    P["full_after"] = rec_full("G_after")["tag"]
    P["polls"] = poll("G", G_S - 8, every=1.5, client_every=2, light_every=4)
    P["watch"] = sw_collect("G", P["arm"])
    P["full_end"] = rec_full("G_end")["tag"]


def phase_J():
    P = out["phases"]["J"] = {}
    P["set0"] = sandbox("J_sev0", "NR.Severity", 0)
    time.sleep(3.0)
    P["opt0"] = options("J0")
    P["full0"] = rec_full("J_full0")["tag"]
    P["polls0"] = poll("J0", 10, every=1.5, client_every=2, light_every=3)
    P["set1"] = sandbox("J_sev1", "NR.Severity", 1)
    time.sleep(3.0)
    P["opt1"] = options("J1")
    P["full1"] = rec_full("J_full1")["tag"]


def phase_G2():
    P = out["phases"]["G2"] = {}
    P["set_off"] = sandbox("G2_exc0", "NR.ExcessEffectsOn", "false")
    time.sleep(3.0)
    P["full_off"] = rec_full("G2_full_off")["tag"]
    P["arm"] = sw_arm("G2", G2_S)
    P["polls"] = poll("G2", G2_S - 2, every=1.5, client_every=2, light_every=4)
    P["watch"] = sw_collect("G2", P["arm"])
    P["clear_ax"] = setpath("G2_ax0", "nutrients.iron.ax", 0)
    P["clear_axr"] = setpath("G2_axr0", "nutrients.iron.axr", 0)
    P["set_on"] = sandbox("G2_exc1", "NR.ExcessEffectsOn", "true")
    P["fs0"] = setany("G2_fs0", "FOOD_SICKNESS", 0)["tag"]
    time.sleep(2.0)
    P["full_end"] = rec_full("G2_full_end")["tag"]


def phase_E2():
    P = out["phases"]["E2"] = {}
    P["edit"] = setpath("E2_thia", "nutrients.thiamine.p", 1)
    P["polls"] = poll("E2", E2_S, every=1.5, client_every=2, light_every=2)
    P["full_end"] = rec_full("E2_full_end")["tag"]


def phase_H():
    P = out["phases"]["H"] = {}
    P["red_before"] = ack(step("H_red0", server, "intox.reduction", USER))
    P["spawn"] = spawn(BEER, "H")["resolved"]
    P["litres_before"] = litres("H_l0", server, BEER)
    P["arm"] = sw_arm("H", H_S)
    r = step("H_drink", client, "drink.action", f"{BEER} 1")
    P["drink_wall"], P["drink"] = r["wall_before"], r["ack"]

    def extra(i, row):
        if i % 8 == 0:
            row["litres"] = litres(f"H_l{i}", server, BEER)
    P["polls"] = poll("H", H_S - 3, every=1.5, client_every=2, light_every=1, extra=extra)
    P["watch"] = sw_collect("H", P["arm"])
    P["red_after"] = ack(step("H_red1", server, "intox.reduction", USER))
    P["full_end"] = rec_full("H_full_end")["tag"]


def phase_BW():
    P = out["phases"]["BW"] = {"bgs": []}
    end = wall() + BW_CAP_S
    reached = False
    while wall() < end:
        r = bg(force=True)
        if r:
            P["bgs"].append(r["i"])
            s = next((x for x in reversed(out["stats_all"]) if x["side"] == "server"), None)
            fv = to_num((s or {}).get("stats", {}).get("Fatigue"))
            if fv is not None and fv >= BW_STOP_F:
                reached = True
                break
        time.sleep(max(0.0, BG_EVERY - 1.5))
    P["reached"] = reached
    P["full_end"] = rec_full("BW_full_end")["tag"]


def phase_C():
    P = out["phases"]["C"] = {}
    P["spawn"] = spawn(BOTTLE, "C")["resolved"]
    P["fill"] = ack(step("C_fill", server, "fluid.fill", f"{USER} {BOTTLE} Coffee {COFFEE_L}"))
    P["litres_filled"] = litres("C_l0", server, BOTTLE)
    P["full_before"] = rec_full("C_before")["tag"]
    r = step("C_drink", client, "drink.action", f"{BOTTLE} 1")
    P["drink_wall"], P["drink"] = r["wall_before"], r["ack"]
    P["polls"] = poll("C", C_S, every=1.5, client_every=1, light_every=1)
    P["full_end"] = rec_full("C_full_end")["tag"]


def phase_SL():
    P = out["phases"]["SL"] = {"polls": []}
    P["water0"] = setpath("SL_water0", "fluids.water", 0)
    P["before"] = rec_light("SL_before")["tag"]
    P["get_before"] = sget("SL_get_before")["tag"]
    r = step("SL_hold", server, "player.sleep.hold", f"{USER} {SL_S}")
    P["hold_wall"], P["hold"] = r["wall_before"], r["ack"]
    end = P["hold_wall"] + SL_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "r": rec_light(f"SL_p{i}_r")["tag"], "g": sget(f"SL_p{i}_g")["tag"],
             "s": sall(f"SL_p{i}_s", server)["tag"], "water": setpath(f"SL_p{i}_w", "fluids.water", 0)["tag"]}
        P["polls"].append(p)
        i += 1
        rest = 2.0 - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    P["cancel"] = ack(step("SL_cancel", server, "player.sleep.hold", f"{USER} 0"))
    P["after"] = rec_light("SL_after")["tag"]
    P["get_after"] = sget("SL_get_after")["tag"]
    time.sleep(3.0)
    P["full_after"] = rec_full("SL_full_after")["tag"]
    P["pair_c"] = sall("SL_after_c", client)["tag"]
    P["pair_s"] = sall("SL_after_s", server)["tag"]


def phase_F():
    P = out["phases"]["F"] = {}
    P["full_before"] = rec_full("F_before")["tag"]
    P["edit1"] = setpath("F_awake24", "acute.awakeH", 24)
    P["arm1"] = sw_arm("F1", F1_S)
    time.sleep(1.5)
    P["full1"] = rec_full("F_full1")["tag"]
    P["polls1"] = poll("F1", F1_S - 6, every=1.5, client_every=2, light_every=3)
    P["watch1"] = sw_collect("F1", P["arm1"])
    P["edit2"] = setpath("F_caf", "acute.caf", F_CAF)
    P["arm2"] = sw_arm("F2", F2_S)
    time.sleep(1.5)
    P["full2"] = rec_full("F_full2")["tag"]
    P["polls2"] = poll("F2", F2_S - 6, every=1.5, client_every=2, light_every=3)
    P["watch2"] = sw_collect("F2", P["arm2"])
    P["edit3"] = setpath("F_awake0", "acute.awakeH", 0)
    P["arm3"] = sw_arm("F3", F3_S)
    time.sleep(1.5)
    P["full3"] = rec_full("F_full3")["tag"]
    P["polls3"] = poll("F3", F3_S - 4, every=1.0, client_every=2, light_every=3)
    P["watch3"] = sw_collect("F3", P["arm3"])


def phase_I():
    P = out["phases"]["I"] = {}
    P["edit_awake"] = setpath("I_awake24", "acute.awakeH", 24)
    P["edit_caf"] = setpath("I_caf0", "acute.caf", 0)
    time.sleep(3.0)
    P["full"] = rec_full("I_full")["tag"]
    P["mirror"] = mirror_check("I_mirror")["tag"]
    P["ce_before"] = ce_read("I_before")
    P["zombie"] = ack(step("I_zombie", server, "zombie.near", "1"))
    t_arm = time.time()
    P["probe"] = ack(step("I_probe", client, "aim.probe", f"{USER} {AIM_S}"))
    time.sleep(1.0)
    P["fire"] = ack(step("I_fire", client, "aim.fire", "3"))
    P["polls"] = poll("I", AIM_S - 3, every=2.0, client_every=2, light_every=3)
    P["result"] = wait_res("aim-probe", t_arm - 0.5, 15)
    P["ce_after"] = ce_read("I_after")
    P["mirror_after"] = mirror_check("I_mirror2")["tag"]
    P["reset_awake"] = setpath("I_awake0", "acute.awakeH", 0)
    P["health"] = hget("I_h", server)["tag"]


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["counters"] = counters("Z_cnt")
    P["flags"] = flags("Z_flags")
    P["options"] = options("Z")
    P["intox_reduction"] = ack(step("Z_intox", server, "intox.reduction", USER))
    P["full"] = rec_full("Z_full")["tag"]
    P["stats_c"] = sall("Z_c", client)["tag"]
    P["stats_s"] = sall("Z_s", server)["tag"]
    P["health_s"] = hget("Z_h_s", server)["tag"]
    P["health_c"] = hget("Z_h_c", client)["tag"]
    P["ce"] = ce_read("Z")


PHASES = (("S0", phase_S0), ("A", phase_A), ("K", phase_K), ("D", phase_D), ("E", phase_E), ("G", phase_G),
          ("J", phase_J), ("G2", phase_G2), ("E2", phase_E2), ("H", phase_H), ("BW", phase_BW), ("C", phase_C),
          ("SL", phase_SL), ("F", phase_F), ("I", phase_I), ("Z", phase_Z))


def body():
    for name, fn in PHASES:
        run_phase(name, fn)
        why = mod_error(name)
        if why and name != "Z":
            out["abort"] = {"after": name, "why": why}
            note(f"mod error or health guard after {name}: the arms stop here (a mod error is the primary reading)")
            persist()
            if name != "Z":
                run_phase("Z", phase_Z)
            break


# ---------------------------------------------------------------- the kernel offline (lupa)
REPLAY_LUA = r"""
local NR = NutritionRevamp
local K = NR.kernel
local R = {}
function R.compose(record, sev, bonusOn, asleep)
    local a, fl, nut, body = record.acute, record.fluids, record.nutrients, record.body
    local EL = record.effects or {}
    local b = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
    K.effects.bands(b, a, fl)
    local F = { anaemia = nut.anaemia == true, allReplete = nut.allReplete == true,
                vitDClinical = nut.vitDClinical == true, hang = a.hang == 1, refeedEvent = a.refeedEvent == true,
                frozen = a.frozen == true, bgroupMax = K.effects.bgroupMax(nut),
                coldCredit = K.effects.coldCredit(nut.vitC.g, nut.vitC.e24, body.band1Day or 0, body.band2Day or 0, a.coldH),
                boutVig = asleep and a.boutVig == true }
    local E = K.effects.new()
    local pe = EL.pe or 1
    local ea = EL.ea or 30
    local T = NR.data.effects
    K.effects.compose(E, T, nut, b, pe, ea, F, sev, bonusOn, T.VITD_EFFECTS)
    E.fOff = K.effects.fOff(a.debtH, a.caf, a.cafTol, E.fOffNut)
    E.intoxTarget = K.effects.intoxTarget(a.bac)
    E.bgroupMax = F.bgroupMax
    E.bands = b
    return E
end
function R.fatigue(S, circ, fOff)
    local inp = NR.bench_fast_input()
    local out = K.fast.output()
    inp.fOwned = true
    inp.fFrozen = false
    inp.asleep = false
    inp.fS = S
    inp.fCirc = circ
    inp.fOff = fOff
    K.fast.step(inp, out, K.fast.defaults())
    return out.fatigue
end
function R.fold(endLast, endurance, dmod, rmod)
    local inp = NR.bench_fast_input()
    local out = K.fast.output()
    inp.asleep = false
    inp.endFold = true
    inp.endLast = endLast
    inp.endurance = endurance
    inp.dmod = dmod
    inp.rmod = rmod
    inp.unlimitedEndurance = false
    K.fast.step(inp, out, K.fast.defaults())
    return out.endurance
end
function R.sleepStep(acute, asleep, hour, ageH, dtH, mAcc, rRec)
    local a = {}
    for k, v in pairs(acute) do a[k] = v end
    K.acute.sleepMinute(a, asleep, hour, 1, ageH, dtH, false, mAcc, rRec)
    return a.S, a.circ, a.awakeH, a.debtH
end
function R.stepInPlace(a, asleep, hour, ageH, dtH, mAcc, rRec)
    K.acute.sleepMinute(a, asleep, hour, 1, ageH, dtH, false, mAcc, rRec)
    return a.S, a.circ, a.awakeH, a.debtH
end
function R.circ(hour)
    return K.acute.CIRC_AMP * math.cos(2 * math.pi * (hour - K.acute.CIRC_PEAK_H) / 24)
end
function R.iuSleep(awakeH, debtH)
    return K.acute.iuSleep({ awakeH = awakeH, debtH = debtH })
end
function R.dmodRatio(tac, g, d1, d0, excessPct, ironGrade, awakeH, cafEffect, cafTol)
    local A = K.aerobic
    return A.dmod(tac, g, d1, 0, excessPct, ironGrade, awakeH, cafEffect, cafTol) / A.dmod(tac, g, d0, 0, excessPct, ironGrade, awakeH, cafEffect, cafTol)
end
function R.rmodHydr(d)
    local A = K.aerobic
    return K.max(A.HYDR_R_FLOOR, 1 - A.HYDR_R_K * K.max(0, d - A.HYDR_T1))
end
function R.dmodHydr(d)
    local A = K.aerobic
    return 1 + A.HYDR_K1 * K.max(0, d - A.HYDR_T1) + A.HYDR_K2 * K.max(0, d - A.HYDR_T2)
end
function R.consts()
    local c = K.fast.defaults()
    return c.moodRiseStress, c.stressDecrease, K.effects.CAF_OFF_MAX, K.effects.CAF_EC50, K.effects.CAF_TOL_BLUNT
end
return R
"""


class Kernel:
    def __init__(self):
        import lupa.lua51 as lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        files = ([os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
                 + sorted(glob.glob(os.path.join(SHARED, "NR_Data*.lua")))
                 + [os.path.join(MOD_LUA, "server", "NR_Server_Bench.lua")])
        loader = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")
        for p in files:
            with open(p, encoding="utf-8") as fh:
                loader(fh.read(), "@" + os.path.basename(p))()
        self.NR = self.rt.globals().NutritionRevamp
        self.K = self.NR.kernel
        self.R = loader(REPLAY_LUA, "@replay")()

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.table(v)
            elif isinstance(v, list):
                t[k] = self.table({i + 1: x for i, x in enumerate(v)})
            else:
                t[k] = v
        return t

    def to_py(self, t):
        d = {}
        for k, v in t.items():
            if hasattr(v, "items"):
                d[k] = self.to_py(v)
            else:
                d[k] = v
        return d


def numtab(d):
    """A record sub-table as read -> numbers and booleans (strings parsed)."""
    outd = {}
    if isinstance(d, list):
        return [to_num(x) for x in d]
    for k, v in (d or {}).items():
        if isinstance(v, (dict, list)):
            outd[k] = numtab(v)
            continue
        if isinstance(v, bool):
            outd[k] = v
            continue
        n = to_num(v)
        if n is not None:
            outd[k] = n
        elif str(v).lower() in ("true", "false"):
            outd[k] = str(v).lower() == "true"
    return outd


def record_of(full):
    """A rec_full row -> the record dict the replay takes (acute, fluids, nutrients with aggregates, body,
    effects); None when a table is missing."""
    a, fl, ef = numtab(full.get("acute")), numtab(full.get("fluids")), numtab(full.get("effects"))
    nut = {}
    for k, v in (full.get("nutrients") or {}).items():
        if isinstance(v, dict):
            nut[k] = numtab(v)
        elif isinstance(v, bool):
            nut[k] = v
        elif to_num(v) is not None:
            nut[k] = to_num(v)
        elif str(v).lower() in ("true", "false"):
            nut[k] = str(v).lower() == "true"
    body = {k: to_num(v) for k, v in (full.get("body") or {}).items() if to_num(v) is not None}
    if not a or not fl or not nut or any(k not in nut for k in ORDER):
        return None
    return {"acute": a, "fluids": fl, "nutrients": nut, "body": body, "effects": ef}


def rows_by(tag_list, key="tag"):
    return {r[key]: r for r in tag_list}


def series(phase_names, stat, side="server"):
    """(worldAge, value, wall, tag) from stats.all rows of these phases on one side."""
    pts = []
    for r in out["stats_all"]:
        if r["side"] != side or (phase_names and r.get("phase") not in phase_names):
            continue
        v, wa = to_num((r.get("stats") or {}).get(stat)), to_num(r.get("worldAge"))
        if v is not None and wa is not None:
            pts.append((wa, v, r["wall"], r["tag"]))
    return pts


def slope(pts):
    """Least-squares slope of value on worldAge (per game hour) and the n."""
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx <= 0:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx


def tag_pts(tags, stat):
    S = rows_by(out["stats_all"])
    pts = []
    for t in tags:
        r = S.get(t)
        if not r:
            continue
        v, wa = to_num((r.get("stats") or {}).get(stat)), to_num(r.get("worldAge"))
        if v is not None and wa is not None:
            pts.append((wa, v, r["wall"], t))
    return pts


def crossings(pts, levels):
    res = {}
    for lv in levels:
        res[str(lv)] = None
        for (x0, y0, *_), (x1, y1, *_) in zip(pts, pts[1:]):
            if y0 < lv <= y1 and x1 > x0:
                res[str(lv)] = x0 + (lv - y0) * (x1 - x0) / (y1 - y0)
                break
    return res


def client_match(phase_names, stat, lookback=2.5):
    """Each client read: does its value equal (exactly) a server read of the same stat in the lookback
    window before it? (counts and the lags)."""
    srv = series(phase_names, stat, "server")
    cli = series(phase_names, stat, "client")
    hits, misses, lags = 0, 0, []
    for wa, v, w, t in cli:
        cand = [(w - sw) for (_, sv, sw, _) in srv if sv == v and 0 <= w - sw <= lookback]
        if cand:
            hits += 1
            lags.append(round(min(cand), 3))
        else:
            misses += 1
    return {"client_reads": len(cli), "exact_match_to_earlier_server": hits, "no_match": misses,
            "lags_s": lags[:40]}


def grade_all():
    sm = out["summaries"]
    try:
        KK = Kernel()
        R = KK.R
        sm["kernel_loaded"] = True
    except Exception as e:                     # noqa: BLE001
        sm["kernel_loaded"] = f"{type(e).__name__}: {e}"
        return
    RL = rows_by(out["recs"])
    FL = rows_by(out["full"])
    SA = rows_by(out["stats_all"])
    P = out["phases"]
    opts = (P.get("S0") or {}).get("options") or {}
    sev0 = to_num(opts.get("severity")) or 1.0
    bonus0 = opts.get("balanceBonus") is not False
    # ---- A: first sight, the identity, the caps, the epochs
    A = sm["A"] = {}
    fr = RL.get((P.get("S0") or {}).get("first_effects_rec") or "") or {}
    f0 = FL.get((P.get("S0") or {}).get("full") or "") or {}
    ef0 = numtab(f0.get("effects"))
    A["first_effects"] = {"ev": ef0.get("ev"), "epoch": ef0.get("epoch"), "fOff": ef0.get("fOff"),
                          "mAcc": ef0.get("mAcc"), "rRec": ef0.get("rRec"), "wall": fr.get("wall"),
                          "worldAge": fr.get("worldAge")}
    ident = []
    for b in out["brackets"]:
        r1, r2, s = RL.get(b["r1"]), RL.get(b["r2"]), SA.get(b["s"])
        if not (r1 and r2 and s):
            continue
        S_, c_, o_ = r1.get("acute.S"), r1.get("acute.circ"), r1.get("effects.fOff")
        fv = to_num((s.get("stats") or {}).get("Fatigue"))
        if None in (S_, c_, o_, fv) or not all(isinstance(x, float) for x in (S_, c_, o_)):
            continue
        pred = R.fatigue(S_, c_, o_)
        row = {"tag": b["tag"], "phase": b["phase"], "same": b["same"], "S": S_, "circ": c_, "fOff": o_,
               "pred": pred, "pred_f32": f32(pred), "read": fv, "diff": fv - f32(pred), "worldAge": s.get("worldAge"),
               "frozen": r1.get("acute.frozen"), "boutH": r1.get("acute.boutH")}
        ident.append(row)
    same = [r for r in ident if r["same"]]
    A["identity"] = {"brackets": len(ident), "same_minute": len(same),
                     "same_exact": sum(1 for r in same if r["diff"] == 0),
                     "same_max_abs_diff": max((abs(r["diff"]) for r in same), default=None),
                     "cross_minute_max_abs_diff": max((abs(r["diff"]) for r in ident if not r["same"]), default=None),
                     "first": same[:3], "off": [r for r in same if r["diff"] != 0][:10]}
    out["identity_rows"] = ident
    A["fatigue_client"] = client_match(None, "Fatigue")
    caps = {}
    for side in ("server", "client"):
        hs = [p[1] for p in series(None, "Hunger", side)]
        ts = [p[1] for p in series(None, "Thirst", side)]
        caps[side] = {"n": len(hs), "hunger_max": max(hs, default=None), "thirst_max": max(ts, default=None),
                      "hunger_over_cap": sum(1 for v in hs if v > f32(HUNGER_CAP) + 1e-9),
                      "thirst_over_cap": sum(1 for v in ts if v > f32(THIRST_CAP) + 1e-9)}
    A["caps"] = caps
    A["hungry_tags"] = {w["tag"]: (w["result"].get("dmg") or {}).get("HUNGRY") for w in out["watches"]}
    eps = [(r.get("nutrients.epoch"), r.get("effects.epoch")) for r in out["recs"]
           if r.get("nutrients.epoch") is not None and r.get("effects.epoch") is not None]
    A["epochs"] = {"first": eps[0] if eps else None, "last": eps[-1] if eps else None, "n": len(eps)}
    # ---- composer replays at every full read
    comp = []
    for f in out["full"]:
        rec = record_of(f)
        if rec is None:
            comp.append({"tag": f["tag"], "skipped": "a table missing"})
            continue
        ph = f.get("phase")
        sev = sev0
        for s_ in out["sandbox"]:
            if s_["key"] == "NR.Severity" and s_["wall"] <= f["wall"] - 1.0:
                sev = to_num(s_["value"])
        try:
            E = KK.to_py(R.compose(KK.table(rec), sev, bonus0, False))
        except Exception as e:                 # noqa: BLE001
            comp.append({"tag": f["tag"], "error": f"{type(e).__name__}: {e}"})
            continue
        live = rec["effects"]
        row = {"tag": f["tag"], "phase": ph, "sev": sev, "bands": [E["bands"].get(i) for i in range(1, 13)],
               "bgroupMax": E.get("bgroupMax"), "mismatch": {}}
        for k in ("stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget", "aimMul", "speedMul",
                  "fOffNut", "mNut", "rNut", "healMul", "tempOffset", "fOff", "intoxTarget"):
            row[k] = {"replay": E.get(k), "live": live.get(k)}
            lv = live.get(k)
            if lv is not None and E.get(k) is not None and abs(lv - E[k]) > 1e-12:
                row["mismatch"][k] = (E[k], lv)
        row["live_epoch"] = live.get("epoch")
        row["nut_epoch"] = rec["nutrients"].get("epoch")
        row["thiamine"] = {k: rec["nutrients"]["thiamine"].get(k) for k in ("p", "g", "x", "ah")}
        row["iron"] = {k: rec["nutrients"]["iron"].get(k) for k in ("p", "g", "x", "ax", "axr")}
        row["dehydPct"] = rec["fluids"].get("dehydPct")
        row["awakeH"], row["debtH"], row["caf"], row["iuSleep"], row["iu"] = (
            rec["acute"].get("awakeH"), rec["acute"].get("debtH"), rec["acute"].get("caf"),
            rec["acute"].get("iuSleep"), rec["acute"].get("iu"))
        comp.append(row)
    sm["compose"] = comp
    sm["compose_mismatch_tags"] = [c["tag"] for c in comp if c.get("mismatch")]
    rise_s, dec_s, cmax, cec50, cblunt = R.consts()
    sm["constants"] = {"moodRiseStress": rise_s, "stressDecrease": dec_s, "CAF_OFF_MAX": cmax, "CAF_EC50": cec50,
                       "CAF_TOL_BLUNT": cblunt, "moodRisePanic": 24 / 3600, "moodRiseUnhappy": 22 / 3600,
                       "moodRiseSick": 25 / 3600}
    # ---- K
    Kp = P.get("K") or {}
    us = [to_num((b.get("ack") or {}).get("usPerCall")) for b in Kp.get("bench", [])]
    sm["K"] = {"us_per_call": us, "kept": us[1:], "band_3003": BAND_3003, "band_top_10pct": BAND_3003[1] * 1.1,
               "within_10pct": all(u is not None and u <= BAND_3003[1] * 1.1 for u in us[1:]) if len(us) == 3 else None,
               "tick": ((Kp.get("tick") or {}).get("result") or {})}
    # ---- D
    D = sm["D"] = {}
    Dp = P.get("D") or {}

    def wslope(win, stat="Endurance"):
        if not win:
            return {"missing": True}
        tags = [p.get("s") for p in win.get("polls", [])]
        pts = tag_pts(tags, stat)
        return {"slope_per_h": slope(pts), "n": len(pts), "first": pts[0][1] if pts else None,
                "last": pts[-1][1] if pts else None, "min": min((p[1] for p in pts), default=None),
                "drop": (pts[0][1] - min(p[1] for p in pts)) if pts else None,
                "worldAge_span": (pts[-1][0] - pts[0][0]) if pts else None}
    for k in ("D1_rest", "D1_squat", "D2_rest", "D2_squat", "D3_rest", "D3_squat"):
        D[k] = wslope(Dp.get(k))
        win = Dp.get(k) or {}
        for end_ in ("rec_start", "rec_end"):
            r = RL.get(win.get(end_) or "") or {}
            D[k][end_] = {"dmod": r.get("body.dmod"), "rmod": r.get("body.rmod"), "dehydPct": r.get("fluids.dehydPct")}
    D["luasets"] = [{"path": x["path"], "ack": x["ack"]} for x in out["luasets"]]

    def ratio(a, b, key):
        try:
            return (D[a][key] / D[b][key]) if D[a].get(key) and D[b].get(key) else None
        except (KeyError, TypeError, ZeroDivisionError, AttributeError):
            return None
    D["rest_ratio_D2"] = ratio("D2_rest", "D1_rest", "slope_per_h")
    D["rest_ratio_D3"] = ratio("D3_rest", "D1_rest", "slope_per_h")
    D["squat_ratio_D2"] = ratio("D2_squat", "D1_squat", "drop")
    D["squat_ratio_D3"] = ratio("D3_squat", "D1_squat", "drop")
    try:
        f3 = record_of(FL.get(Dp.get("D3_full") or "") or {}) or {}
        b3, a3 = f3.get("body", {}), f3.get("acute", {})
        D["kernel_hydr"] = {"dehydPct": (f3.get("fluids") or {}).get("dehydPct"),
                            "dmod_factor": R.dmodHydr((f3.get("fluids") or {}).get("dehydPct") or 0),
                            "rmod_factor": R.rmodHydr((f3.get("fluids") or {}).get("dehydPct") or 0),
                            "live_dmod": b3.get("dmod"), "live_rmod": b3.get("rmod"), "awakeH": a3.get("awakeH")}
        r1 = D["D1_rest"]
        if r1 and r1.get("slope_per_h") is not None:
            rmod2 = (D["D2_rest"].get("rec_start") or {}).get("rmod") or 1.0
            per_read = r1["slope_per_h"] * 0.0005
            D["kernel_fold_rest"] = {"vanilla_delta": per_read, "rmod": rmod2,
                                     "fold": R.fold(0.7, 0.7 + per_read, 1.0, rmod2) - 0.7}
    except Exception as e:                     # noqa: BLE001
        D["kernel_error"] = f"{type(e).__name__}: {e}"
    on_phase_tags = [p.get("s") for k in ("D2_rest", "D2_squat", "D3_rest", "D3_squat") for p in (Dp.get(k) or {}).get("polls", [])]
    D["x35_client_match_fold_on"] = client_match(["D"], "Endurance", 2.5)
    D["x35_fold_on_server_reads"] = len([t for t in on_phase_tags if t])
    # ---- stat floors
    def floor_stats(phases, stat, target_key):
        pts = series(phases, stat)
        return {"n": len(pts), "first": pts[0][1] if pts else None, "last": pts[-1][1] if pts else None,
                "max": max((p[1] for p in pts), default=None), "min": min((p[1] for p in pts), default=None),
                "slope_per_h_all": slope(pts)}
    E = sm["E"] = {"stress": floor_stats(["E"], "Stress", "stressTarget")}
    ep = series(["E"], "Stress")
    if ep:
        tgt = None
        for c in comp:
            if c["tag"] == (P.get("E") or {}).get("full_after"):
                tgt = (c.get("stressTarget") or {}).get("live")
        E["target_live"] = tgt
        rising = [p for p in ep if tgt is not None and p[1] < f32(tgt) - 1e-6 and p[1] > 0]
        E["rise_slope_per_h"] = slope(rising)
        E["rise_n"] = len(rising)
        E["at_target_reads"] = sum(1 for p in ep if tgt is not None and p[1] == f32(tgt))
        E["pred_net_per_h"] = (rise_s - dec_s) * 3600
        E["pred_gross_per_h"] = rise_s * 3600
    G = sm["G"] = {"food_sickness": floor_stats(["G"], "FoodSickness", "foodSickTarget"),
                   "poison_max": max((p[1] for p in series(None, "Poison")), default=None)}
    gp = series(["G"], "FoodSickness")
    if gp:
        rising = [p for p in gp if 0 < p[1] < 54.9]
        G["rise_slope_per_h"] = slope(rising)
        G["rise_n"] = len(rising)
        G["at_55_reads"] = sum(1 for p in gp if p[1] == 55)
        G["pred_gross_per_h"] = 25.0
    G2 = sm["G2"] = {"food_sickness": floor_stats(["G2"], "FoodSickness", "foodSickTarget")}
    sm["J"] = {"compose": [c for c in comp if c.get("phase") == "J"],
               "stress": floor_stats(["J"], "Stress", None), "food_sickness": floor_stats(["J"], "FoodSickness", None)}
    sm["E2"] = {"stress": floor_stats(["E2"], "Stress", None),
                "decay_slope_per_h": slope([p for p in series(["E2"], "Stress") if p[1] > 0]),
                "pred_decay_per_h": -dec_s * 3600}
    F = sm["F"] = {}
    for stat in ("Panic", "Unhappiness"):
        pts = series(["F"], stat)
        F[stat] = {"n": len(pts), "max": max((p[1] for p in pts), default=None),
                   "first": pts[0][1] if pts else None, "last": pts[-1][1] if pts else None}
    F["watches"] = {w["tag"]: {f: (w["result"].get("fields") or {}).get(f) for f in ("panic", "unhappiness", "stress")}
                    for w in out["watches"] if w["tag"] in ("F1", "F2", "F3")}
    F["raw_panic_F1"] = [r.get("panic") for r in (next((w["result"] for w in out["watches"] if w["tag"] == "F1"), {}) or {}).get("raw", [])][:60]
    uh = [p for p in series(["F"], "Unhappiness")]
    F["unhappy_rise_slope_per_h"] = slope([p for p in uh if 0 < p[1] < 16.5])
    F["pred_unhappy_per_h"] = 22.0
    F["pred_panic_per_h"] = 24.0
    try:
        F["iuSleep_kernel_24_debt0"] = R.iuSleep(24, 0)
    except Exception as e:                     # noqa: BLE001
        F["kernel_error"] = f"{type(e).__name__}: {e}"
    # ---- H
    H = sm["H"] = {}
    hid = []
    for r in out["recs"]:
        if r.get("phase") != "H" or r.get("acute.bac") is None:
            continue
        hid.append({"tag": r["tag"], "bac": r.get("acute.bac"), "intoxTarget": r.get("effects.intoxTarget"),
                    "kernel": KK.K.effects.intoxTarget(r.get("acute.bac")), "worldAge": r.get("worldAge"),
                    "wall": r["wall"]})
    H["rec_targets"] = hid
    H["target_kernel_mismatch"] = sum(1 for h in hid if h["intoxTarget"] is not None and abs(h["intoxTarget"] - h["kernel"]) > 1e-12)
    H["peak_target"] = max((h["intoxTarget"] for h in hid if h["intoxTarget"] is not None), default=None)
    # pair each server read with the rec_light read right before it in the same poll round
    pairs_ = []
    hp = (P.get("H") or {}).get("polls", [])
    for p in hp:
        s, r = SA.get(p.get("s")), RL.get(p.get("r") or "")
        if s and r:
            iv = to_num((s.get("stats") or {}).get("Intoxication"))
            pairs_.append({"s": p["s"], "r": p["r"], "read": iv, "target": r.get("effects.intoxTarget"),
                           "eq_f32": (iv == f32(r.get("effects.intoxTarget"))) if (iv is not None and r.get("effects.intoxTarget") is not None) else None,
                           "lastAgeH": r.get("nutrients.lastAgeH")})
    H["pairs"] = pairs_
    H["pairs_eq"] = sum(1 for x in pairs_ if x["eq_f32"])
    H["watch"] = next(((w["result"].get("fields") or {}).get("intoxication") for w in out["watches"] if w["tag"] == "H"), None)
    H["reduction"] = {"before": (P.get("H") or {}).get("red_before"), "after": (P.get("H") or {}).get("red_after")}
    # ---- B: crossings and the replay
    B = sm["B"] = {}
    ts = (P.get("S0") or {}).get("time_server") or {}
    try:
        off = (to_num(ts.get("hour")) + to_num(ts.get("minutes")) / 60.0) - to_num(ts.get("worldAge"))
    except TypeError:
        off = None
    B["hour_offset"] = off
    c_start = (out["phase_walls"].get("C") or {}).get("start")
    pre = [r for r in out["recs"] if c_start is None or r["wall"] < c_start]
    pre = [r for r in pre if isinstance(r.get("acute.S"), float) and r.get("nutrients.lastAgeH") is not None]
    pre.sort(key=lambda r: r["nutrients.lastAgeH"])
    srv_f = [p for p in series(None, "Fatigue") if c_start is None or p[2] < c_start]
    srv_f.sort()
    B["measured_crossings_worldAge"] = crossings(srv_f, (0.6, 0.7, 0.8))
    B["n_server_fatigue"] = len(srv_f)
    if pre and off is not None:
        first = FL.get((P.get("S0") or {}).get("full") or "") or {}
        a0 = numtab(first.get("acute"))
        age0 = to_num(((first.get("calls") or [{}])[0]).get("lastAgeH"))
        if a0 and age0 is not None:
            la = KK.table(a0)
            ageH = age0
            rep = []
            one = []
            prev = None
            for r in pre:
                ag = r["nutrients.lastAgeH"]
                if ag <= ageH:
                    continue
                mAcc = (prev or {}).get("effects.mAcc") or 1.0
                hour = (ag + off) % 24
                S_, circ_, aw_, debt_ = R.stepInPlace(la, False, hour, ag, ag - ageH, mAcc, None)
                ageH = ag
                fo = r.get("effects.fOff")
                rep.append({"tag": r["tag"], "ageH": ag, "S_rep": S_, "S_live": r.get("acute.S"),
                            "circ_rep": circ_, "circ_live": r.get("acute.circ"),
                            "F_rep": (S_ + circ_ + fo) if fo is not None else None})
                if prev is not None and isinstance(prev.get("acute.S"), float):
                    ap = {"S": prev["acute.S"], "debtH": prev.get("acute.debtH") or 0, "awakeH": prev.get("acute.awakeH") or 0,
                          "boutH": prev.get("acute.boutH") or 0, "gapH": 0, "sleptH": 0, "winStartH": ag,
                          "winSleptH": 0, "lastVigAgeH": -1e9}
                    S1, _, _, _ = R.sleepStep(KK.table(ap), False, hour, ag, ag - prev["nutrients.lastAgeH"],
                                              prev.get("effects.mAcc") or 1.0, None)
                    if prev["nutrients.lastAgeH"] < ag and not prev.get("acute.boutH"):
                        one.append({"tag": r["tag"], "dtH": ag - prev["nutrients.lastAgeH"], "S_pred": S1,
                                    "S_live": r.get("acute.S"), "diff": r.get("acute.S") - S1})
                prev = r
            B["replay_n"] = len(rep)
            B["replay_S_max_abs_diff"] = max((abs(x["S_rep"] - x["S_live"]) for x in rep), default=None)
            B["replay_circ_max_abs_diff"] = max((abs(x["circ_rep"] - x["circ_live"]) for x in rep if x["circ_live"] is not None), default=None)
            B["replay_tail"] = rep[-3:]
            B["predicted_crossings_worldAge"] = crossings([(x["ageH"], x["F_rep"]) for x in rep if x["F_rep"] is not None], (0.6, 0.7, 0.8))
            B["one_interval"] = {"n": len(one), "max_abs_diff": max((abs(x["diff"]) for x in one), default=None),
                                 "worst": sorted(one, key=lambda x: -abs(x["diff"]))[:5]}
            out["replay_rows"] = rep
            B["first_sight"] = {"ageH": age0, "S": a0.get("S"), "awakeH": a0.get("awakeH"), "debtH": a0.get("debtH")}
    B["I_B7_literal_07h"] = {"0.6": 14.305, "0.7": 16.278, "0.8": 18.648, "note": "hours awake from a 07:00 wake"}
    # held sleep
    SLp = P.get("SL") or {}
    sl = []
    prev = None
    for p in SLp.get("polls", []):
        r = RL.get(p.get("r")) or {}
        g = next((x for x in out["stats_get"] if x["tag"] == p.get("g")), {})
        if prev is not None and isinstance(prev.get("acute.S"), float) and isinstance(r.get("acute.S"), float):
            dt = (r.get("nutrients.lastAgeH") or 0) - (prev.get("nutrients.lastAgeH") or 0)
            if dt > 0:
                ap = {"S": prev["acute.S"], "debtH": prev.get("acute.debtH") or 0, "awakeH": prev.get("acute.awakeH") or 0,
                      "boutH": max(prev.get("acute.boutH") or 0, 1e-9), "gapH": 0, "sleptH": 0,
                      "winStartH": r.get("nutrients.lastAgeH") or 0,
                      "winSleptH": 0, "lastVigAgeH": -1e9}
                S1, _, _, _ = R.sleepStep(KK.table(ap), True, ((r.get("nutrients.lastAgeH") or 0) + (off or 0)) % 24,
                                          r.get("nutrients.lastAgeH"), dt, None, prev.get("effects.rRec") or 1.0)
                sl.append({"tag": p.get("r"), "dtH": dt, "S_prev": prev["acute.S"], "S_live": r["acute.S"], "S_pred": S1,
                           "rRec": prev.get("effects.rRec"), "boutH": r.get("acute.boutH"), "asleep": g.get("asleep"),
                           "ratio_live": (r["acute.S"] / prev["acute.S"]) if prev["acute.S"] else None,
                           "ratio_pred": math.exp(-dt * (prev.get("effects.rRec") or 1.0) / 4.2)})
        prev = r
    B["sleep"] = sl
    # ---- C
    C = sm["C"] = {}
    crow = []
    for r in out["recs"]:
        if r.get("phase") != "C":
            continue
        if None in (r.get("acute.debtH"), r.get("acute.caf"), r.get("acute.cafTol"), r.get("effects.fOffNut")):
            continue
        k = KK.K.effects.fOff(r["acute.debtH"], r["acute.caf"], r["acute.cafTol"], r["effects.fOffNut"])
        k0 = KK.K.effects.fOff(r["acute.debtH"], 0, r["acute.cafTol"], r["effects.fOffNut"])
        crow.append({"tag": r["tag"], "caf": r["acute.caf"], "fOff_live": r.get("effects.fOff"), "fOff_kernel": k,
                     "cafOffset": k0 - k, "worldAge": r.get("worldAge")})
    C["rows"] = crow
    C["fOff_mismatch"] = sum(1 for x in crow if x["fOff_live"] is not None and abs(x["fOff_live"] - x["fOff_kernel"]) > 1e-12)
    C["caf_max"] = max((x["caf"] for x in crow), default=None)
    C["cafOffset_max"] = max((x["cafOffset"] for x in crow), default=None)
    C["cafOffset_107_tol0"] = KK.K.effects.fOff(0, 0, 0, 0) - KK.K.effects.fOff(0, 107, 0, 0)
    # ---- I
    I = sm["I"] = {}
    Ip = P.get("I") or {}
    I["mirror"] = next((m for m in out["mirror_checks"] if m["tag"] == "I_mirror"), None)
    I["compose"] = next((c for c in comp if c["tag"] == Ip.get("full")), None)
    I["ce_before"], I["ce_after"] = Ip.get("ce_before"), Ip.get("ce_after")
    res = Ip.get("result") or {}
    I["probe_reply"] = Ip.get("probe")
    I["result_keys"] = sorted(res.keys()) if isinstance(res, dict) else None


def wait_doctor():
    rows = []
    end = time.time() + 180
    while time.time() < end:
        ok, text = doctor()
        rows.append({"wall": wall(), "clean": ok, "text": text.strip().splitlines()[-6:]})
        if ok:
            break
        time.sleep(5.0)
    return rows


def selftest():
    """Offline: load the kernels and exercise the replay glue on records the kernel itself makes."""
    KK = Kernel()
    R = KK.R
    acute = KK.to_py(KK.K.acute.new(3.1))
    fluids = KK.to_py(KK.K.fluids.new(60, 1, 40))
    nut = {k: KK.to_py(KK.K.nutrients.newKey()) for k in ORDER}
    nut.update({"epoch": 3, "allReplete": True, "anaemia": False, "vitDClinical": False, "ironGrade": 1})
    rec = {"acute": acute, "fluids": fluids, "nutrients": nut, "body": {"band1Day": 0, "band2Day": 0},
           "effects": KK.to_py(KK.K.effects.new())}
    E = KK.to_py(R.compose(KK.table(rec), 1.0, True, False))
    print("compose replete:", {k: E[k] for k in ("stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget", "aimMul", "fOff")})
    rec["nutrients"]["thiamine"]["g"] = 4
    print("thiamine 4:", KK.to_py(R.compose(KK.table(rec), 1.0, True, False))["stressTarget"])
    rec["nutrients"]["thiamine"]["g"] = 1
    rec["nutrients"]["iron"]["x"] = 2
    print("iron x2:", KK.to_py(R.compose(KK.table(rec), 1.0, True, False))["foodSickTarget"])
    print("iron x2 sev0:", KK.to_py(R.compose(KK.table(rec), 0.0, True, False))["foodSickTarget"])
    rec["nutrients"]["iron"]["x"] = 0
    rec["acute"]["awakeH"] = 24
    rec["acute"]["iuSleep"] = R.iuSleep(24, 0)
    E = KK.to_py(R.compose(KK.table(rec), 1.0, True, False))
    print("awake 24:", E["panicTarget"], E["unhappyTarget"], "iuSleep", rec["acute"]["iuSleep"])
    rec["acute"]["caf"] = 440
    print("caf 440:", KK.to_py(R.compose(KK.table(rec), 1.0, True, False))["panicTarget"])
    rec["acute"]["caf"] = 0
    rec["acute"]["iu"] = 1.0
    print("aim iu 1:", KK.to_py(R.compose(KK.table(rec), 1.0, True, False))["aimMul"])
    print("fatigue I-B1 parts:", R.fatigue(0.5, 0.08485281374238571, 0.03 - 0.14571984435797664))
    print("fold I-C1:", R.fold(0.8, 0.799, 1.5, 0.8), R.fold(0.8, 0.8005, 1.5, 0.8))
    print("sleepStep:", R.sleepStep(KK.table(acute), False, 11.0, 4.1, 1.0, 1.0, None))
    print("iuSleep 24:", R.iuSleep(24, 0), "hydr 3:", R.dmodHydr(3.0), R.rmodHydr(3.0))
    print("intox 0.014:", KK.K.effects.intoxTarget(0.014), "consts:", R.consts())


if SELFTEST:
    selftest()
    sys.exit(0)

prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x161f-dry-run", None) if DRY_RUN else new_run_dir("x161f")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}
bgstate = {"last": -1e9, "n": 0}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": PROFILE,
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_commits": {m: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/{m}")
                      for m in ("TKX_StatWatch", "TKX_SleepWatch", "TKX_BoozeWatch", "TKX_TraitProbe")},
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, tuple))
                  and k not in ("REPO", "LUA_DIR", "MOD_LUA", "SHARED", "REPLAY_LUA", "PHASES")},
    "deviations": [
        "Arm D's drain is a squat set (exercise.do squats), not a run: no run has reached the server (#0591); the "
        "regeneration arm at rest is the clean fold reading.",
        "Arm D's dehydration is held through fluids.water (-30 x w g = 3.0 %), not a dehydPct edit (recomputed from "
        "the pool each minute).",
        "Arm E edits thiamine's store p (0.01), not its grade g (the minute regrades from p).",
        "Arm F's caffeine is 440 mg, not 400 (400 falls into band 7 within one game minute).",
        "Arm I runs at awakeH 24 with caffeine 0, last before Z (the zombie raises PANIC).",
        "Moodle levels are inferred from the stat copies against #2369 (no reader for PANIC/UNHAPPY/SICK/TIRED).",
        "The mod at HEAD runs underneath every arm; mod/ untouched.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["a BeerCan and a WaterBottle", "ENDURANCE, FOOD_SICKNESS written",
                                        "record edits: water, thiamine p, iron ax/axr, awakeH, caf",
                                        "the fold flag flipped and restored", "Severity and ExcessEffectsOn flipped "
                                        "and restored", "a held sleep", "a zombie spawned"]},
    "steps": [], "notes": [], "summaries": {}, "stats_all": [], "stats_get": [], "health_reads": [],
    "stat_writes": [], "watches": [], "recs": [], "full": [], "edits": [], "luasets": [], "sandbox": [],
    "brackets": [], "bg": [], "mirror_checks": [], "spawns": [], "phases": {}, "phase_errors": {},
    "phase_walls": {}, "mod_error_checks": [],
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["ini_seeded"] = read_ini(server)
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec_fx)
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["ini_after_ready"] = read_ini(server)
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)), "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        if server is not None:
            out["server_errors"] = server.errors[:20]
            out["server_error_count"] = len(server.errors)
            out["ini_after_stop"] = read_ini(server)
            out["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                           "limits": {"luaerr": LUAERR_LIMIT}}
            if clients:
                out["logs"]["client_luaerr"] = grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)
        out["doctor_after"] = wait_doctor()
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summaries": {k: out["summaries"].get(k) for k in ("A", "K", "D", "E", "G", "H")},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error")}, indent=1, default=str)[:9000])
