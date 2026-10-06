"""x161b-body -- Plan 5 Task 14, acceptance 2: traits, healing, bleeding, infection, cold, thermal, toxicity,
drains, the PANIC hold and the thirst cap, LIVE. The second boot of the Plan 5 build (mod at HEAD 9288c31, the
PANIC floor a HOLD since Task 9 fix-1; `git status --short mod/` empty). ONE boot of profile `x16-body`
(PZTestKit + NutritionRevamp Mode 1 LegacyMirror OnsetSpeed 30 Severity 1.0 DeficienciesCanKill true
ExcessEffectsOn true BalanceBonus true + TKX_StatWatch + TKX_SleepWatch + TKX_BoozeWatch + TKX_TraitProbe;
`Nutrition = false`; DayLength 1, so a game hour is about 37.5 s wall and a game minute 0.625 s; `[server]`
SleepAllowed and SleepNeeded true). The run id prefix is `x161b`; ONE artifact `body.json`. Shape: x161_fatigue.py
(step, stats.all, the StatWatch arm/collect, rec reads, setpath edits, persist, run_phase, mod_error, the offline
kernel in lupa) with x161_seats_gate.py's trait reads (stats.get traitList, trait.watch, trait.add.push,
sight.range).

WHERE STATE IS READ. The record is the server's global modData `NutritionRevamp.players` keyed by username, read
with `witness.moddata global:NutritionRevamp.players` (at most 32 dotted keys a call): `rec` (one call, 31 keys:
the effects stamps the arms read, the grades, the drain, the day) and `rec2` (`rec` plus a second call: the
nutrient stores p/p2/H/S, retEma, fluids, the close fields); `rec_full` (three calls: the acute, fluids and
effects tables whole, the body scalars, the 27 nutrient tables). Record edits: `globalmoddata.setpath
NutritionRevamp.players admin.<path> <value>`. Traits: `stats.get` traitList on both sides. Body parts:
`bodypart.get` (server; the client twin for E's copy). Health: `health.get`. The regeneration constants:
`regen.get`. The core: `temp.core`. catchACold: `witness.chain getBodyDamage.getCatchACold` (and the
thermoregulator's `getCatchAColdDelta`). The client mirror is read after a fresh request (ruling T14-1).
A slope per game hour is taken against the wall clock and converted by the window's own clock (the world age the
`rec` reads carry).

SCHEDULE (t = wall seconds from the session being ready; the world age starts near 3.1 h at about 10:10, so the
first real day close -- world age 24 -- falls about 780 s after first sight):
  S0  first sight: time both sides, the options, the fast flags, the counters, the record (waiting for
      record.effects), rec_full, stats both sides, traits both sides, bodypart.get all, health, regen.get,
      temp.core, catchACold, sight.range, a mirror check; the arm-C setup edits `acute.starvedDays 6` and
      `acute.bmi 16.5` (they wait for the close).
  J   cost: three `bench.global NutritionRevamp.bench_fast 100000` (the FIRST a warm-up, discarded) and one
      `tick.rate 10` (the second reading after x161f's).
  F   cold (before the close: the closed-day energy band is 0 until then): climate.set -10 and WETNESS 100;
      F0 25 s at debt 0 (coldMul 1, the fold idle); F1 `acute.debtH 10` (band 2) 25 s; then debt 0, climate
      off, WETNESS 0. catchACold and its delta every round.
  A   night vision: client trait.watch nightvision; `acute.retEma` = 1.1 x the record's requirement for the
      subject's sex, then `effects.nvDays 13.95`; poll until own.nv and the server list (cap 100 s); the
      trait-watch result; a mirror check. A2 `trait.set NIGHT_VISION remove` (server, no push): 8 s of server
      polls. A3 `nutrients.vitA.p 0.2` (grade 2): poll to the withdrawal both sides. A4 foreign:
      `trait.add.push NIGHT_VISION` with own.nv false and grade 2: 8 s of polls (about 13 slow minutes); then
      removed and pushed by the driver. A5 carotene-only: `vitA.p 0.95`, `retEma 0`, `nvDays 5`: 10 s of reads.
  B   Short Sighted: sight.range; client trait.watch shortsighted; `vitA.p 0.03` (clinical); poll to the add;
      sight.range; `sandbox.var NR.Severity 0.5` -> poll to the removal; `NR.Severity 1` -> poll to the re-add;
      `vitA.p 0.1` (grade 3) -> poll to the removal; sight.range; `vitA.p 0.95`.
  G   thermal: G0 temp.core 10 s; G1 `nutrients.iron.H` = 0.5 x H0 (H0 = the record's hbShare x totalPerKg[sex] x
      w), a 30 s StatWatch window and temp.core with rec every round for 25 s; G2 squats 20 under the target
      (StatWatch 25 s); G3 `iron.H` back to its value before, squats again (the control); stop; 10 s of rest.
  K   the PANIC hold: rec_full; a 60 s StatWatch window armed; `acute.awakeH 24`; 50 s of server stats.all
      (client every 2nd, rec every 3rd); collect; a 20 s window armed; `acute.awakeH 0`; 15 s; collect.
  L   the thirst cap: `fluids.water` = -7 % of w (the view's tVol 0.92 > 0.83; under the 10 % severe edge);
      a 60 s StatWatch window (the THIRST damage tag); server stats.all every round (client every 2nd), water
      re-set every 5th; collect; water 0.
  H   toxicity rung 3: health, regen.get, rec_full; FOOD_SICKNESS written 80 (so the 85 hold is reachable in
      the window); a 45 s StatWatch window; `nutrients.iron.ax 48` and `iron.axr 3`; 40 s of health.get + rec +
      server stats.all; regen.get mid-window; collect. H1 `sandbox.var NR.DeficienciesCanKill false`; 3 s;
      regen.get; 20 s of health + rec. H2 the dial back to true; `iron.ax 0`, `iron.axr 0`; FOOD_SICKNESS 0.
  W   wait for the day close (body.dayIndex >= 1, effects.lastDay moved; cap 360 s).
  C   healing: rec_full (pe expected 3 from starvedDays 6 -> 7 at a low day); the fallback ONLY if pe != 3:
      `effects.pe 3` and `effects.key.ep -1` (forces the rebuild); `vitC.p 0.3` (grade 3) -> healMul 0.68;
      regen.get; C1 ForeArm_L scratchTime 10, 40 s of bodypart.get + rec; regen.get. C2 `vitC.p 0.95`,
      `effects.pe 1`, `effects.key.ep -1` -> healMul 1; regen.get; ForeArm_L scratchTime 10 again; 40 s; clear.
  D0  the bleed control at bleedMul 1: Hand_L bleeding true + bleedingTime 20; 30 s of bodypart.get + rec +
      health; clear.
  I   scurvy: `vitC.p 0.1` -> grade 4 (poll); `vitC.ah 800`; 30 s of health.get + rec; regen.get; a mirror check
      (effects_lethal, effects_drain); `vitC.ah 0`; reads.
  D1  the bleed at vitC 4 (bleedMul 1.25): Hand_L bleeding true + bleedingTime 20; 30 s; clear.
  BR  the bruise roll: `acute.starvedDays 10` (pe 4 at the next close); the bruise counter; bodypart.get all;
      `player.sleep.hold admin 120`; every ~2 s rec + water 0, bodypart.get all every 3rd round; stop at 48 game
      hours or the hold's end; cancel; the counter; bodypart.get all; every bleeding part cleared.
  E   infection: `vitC.p 0.95`; rec_full (pe expected 4; the fallback edit as C's); E1 Hand_R scratchTime 10 +
      infectedWound true; 40 s of bodypart.get + rec (client bodypart.get every 4th round); E2 `effects.pe 1`,
      `effects.key.ep -1` -> infectMul 1; 40 s; clear.
  Z   the counters, flags, options, rec_full, stats both sides, health both sides, regen.get, traits.

PREDICTIONS (written before the run; every number marked LIVE is recomputed in `grade_all` through the mod's own
kernels run offline in lupa at this commit, from the live record after the edit, never from a hand value).
  A   K.effects.nvMinute: with vitA grade 1, zinc grade < 3 and retEma >= R[sex] (LIVE; 700 for a female) the
      counter grows dtD per slow minute, so 13.95 reaches 14 after 0.05 game days (72 game minutes, about 45 s)
      and own.nv turns true at that minute with NIGHT_VISION on the server list; the client's trait-watch first
      sight lands within one push (#2099: 17 to 32 ms; bounded here by the server poll interval: the push wall
      is not stamped). An external removal is re-added by the next slow minute (reasserts +1). vitA grade 2 ->
      own.nv false and the trait gone both sides at the next minute. A foreign NIGHT_VISION (own.nv false) is
      never removed. Carotene-only (retEma 0): nvDays falls by dtD per minute from min(nvDays, 11) and never
      grows.
  B   K.effects.ssWant(4, 1) true -> SHORT_SIGHTED both sides, sight.range's maxSightChar 2 (#3051-#3069: 6 -> 2);
      Severity 0.5 -> removed at the next minute; Severity 1 -> re-added; grade 3 -> removed.
  G   K.effects.compose: iron grade 4 -> tempOffset -0.2 (LIVE), tempTarget = setPoint - 0.2 (36.8 at a set point
      of 37); the handler writes TEMPERATURE = tempTarget only while the stat reads above it; the core's steady
      offset under the target is the X81 calibration reading (stated as the number read; if the core already
      sits below 36.8 at rest, no write fires and the offset read is the regulator's own).
  F   coldMul 1 at debt 0 and 2.5 at debt band 2 (LIVE compose; vitC replete; the energy band 0 before the
      close); the fold scales a catchACold rise by coldMul at each slow minute and passes the fall unscaled; if
      catchACold never rises the fold's reading is unmeasured.
  K   the PANIC target at awakeH 24 (LIVE compose: 14 at debt 0); PANIC on the server equals float32(target) at
      the first per-tick sample after the rebuild and stays within one update's decay of it (the sawtooth's
      max - min about 0.18 or less, trait-scaled); the client's copy equals the target within a push; at
      awakeH 0 the target falls to 0 and PANIC decays at vanilla's per-update rate (X88, about 0.18 per tick).
  L   fluids.thirstTarget > 0.83 on the record (LIVE: K.fluids.thirstTarget of the view) while THIRST reads
      <= float32(0.83) at every server and client read; the THIRST damage tag count 0 (-1, the reset sentinel,
      means it never fired).
  H   iron.x 3 -> foodSickTarget 85 (LIVE compose), drain 100/1440 = 0.06944444444444445 per game minute and
      lethal 7 (LIVE K.effects.drain); the regeneration constants read 0 (the drain zeroes them); overall health
      falls about 4.1667 per game hour (one ReduceGeneralHealth(d x dtM) per slow minute, #3040's 10 -> 10);
      FOOD_SICKNESS rises from 80 to 85 and holds; SICK and POISON damage tags 0; POISON 0 at every sample. With
      DeficienciesCanKill false: drain 0, lethal 0, health flat or rising, the constants back at healMul x the
      defaults.
  C   pe 3 at the close (LIVE K.effects.peGrade of the closed record's bmi and starvedDays); vitC grade 3 ->
      healMul 0.8 x 0.85 = 0.68 (LIVE compose); regen.get the four defaults x 0.68; the scratch timer's fall over
      the C1 window / its fall over the C2 window (healMul 1) = 0.68; regen.get x 1 after.
  D   vitC grade 4 -> bleedMul 1.25 (LIVE); the bleed timer's fall in D1 / D0 = 1 / 1.25 = 0.8.
  I   vitC grade 4 and ah >= 720 -> drain 100/10080 = 0.00992063492063492 per game minute, lethal 2 (LIVE), on the
      record and on the mirror; health falls about 0.5952 per game hour.
  BR  bruise = 1/2880 per game minute at vitC 4 (LIVE); the expected count over the window's game minutes / 2880
      (about 1 over two game days; P(>= 1 per day) = 0.39352200042286156, I-F4); n = 1: the count is stated.
  E   pe 4 -> infectMul 2.3 (LIVE); the infection level's rise in E1 / its rise in E2 (infectMul 1) = 2.3 (the
      mod's single-minute fold; #3044's bus fold reached 1.18 because it overwrote); the client's copy after
      the fold's syncBodyPart within one hop.
  J   bench_fast within 10 % of #3003 (3.24-3.47 us; the band's top 3.817 us) on runs 2 and 3.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Arms C and E: the protein-energy grade rides the day close's starvedDays, not the bmi edit. NR_Server_Nutrients'
     close runs K.acute.refeedDay before the effects close reads the record, and refeedDay recomputes acute.bmi
     from the mass (w / 1.75^2) and adds one to starvedDays on a low day. The bmi edit is still made, and its
     overwrite is read. starvedDays 6 -> 7 gives pe 3, and 10 -> 11 gives pe 4. The fallback edit (effects.pe with
     effects.key.ep -1 to force the rebuild) applies only if the close misses. The C2 and E2 controls reset pe
     the same way, because no further close is available for them.
  2. Arm E's pe 4 comes from the closes that the bruise sleep crosses.
  3. Arm D's bruise count runs inside a held sleep (the ~20x clock of #2840 / x161f), which covers two game days
     in about 100 s. The 0.035657 per game hour bleed rate (#3042) is re-read as a same-session control, D0, at
     bleedMul 1.
  4. The healing, bleeding and infection windows are 30 to 40 s (about 50 to 64 game minutes), not 5 game
     minutes, for resolution.
  5. Arm H first writes FOOD_SICKNESS 80, so the 85 hold is reachable inside the window, because the floor rises
     25 per game hour.
  6. Arm L reads THIRST through server and client stats.all. TKX_StatWatch has no THIRST field and the profile
     carries no ThirstWatch, so the StatWatch counts the THIRST damage tag only.
  7. Arm F wets the subject (WETNESS 100) and cools the climate (-10) so that catchACold has a chance to rise. A
     control window at coldMul 1 comes first.
  8. Arm G adds a squat set with the target and one without it, to put the core on the target's far side.
  9. Iron's clinical grade is made through nutrients.iron.H, because the minute recomputes p2 = H / H0. vitA and
     vitC grades are made through p, because the minute regrades from p and a g edit would be undone. Night
     vision's grade-1 vitamin A and zinc are the subject's own state, read and not edited.
 10. The night-vision latency is bounded by the server poll interval, because the mod's push wall is not stamped.
 11. Cost runs first, as in x161f.
 12. Moodle levels are inferred from the stat copies against #2369.
 13. The mod at HEAD runs underneath every arm, and mod/ is untouched.

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

PROFILE = "x16-body"
SESSION = ("Plan 5 acceptance 2, live: night vision (A), Short Sighted (B), healing (C), bleeding and the bruise "
           "(D, BR), infection (E), cold (F), thermal and the X81 calibration (G), toxicity rung 3 and its drain "
           "(H), the scurvy drain (I), cost (J), the PANIC hold (K), the thirst cap (L); one boot of x16-body at "
           "DayLength 1")
ARTIFACT = "body.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(MOD_LUA, "shared")
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"
SELFTEST = os.environ.get("X161B_SELFTEST") == "1"

STORE = "NutritionRevamp.players"
ORDER = ("vitC", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "vitA", "vitD",
         "vitE", "vitK", "pantothenate", "biotin", "iron", "zinc", "copper", "magnesium", "calcium", "iodine",
         "selenium", "fibre", "efa", "sodium", "potassium", "caffeine", "ethanol")
MINI = ("effects.epoch", "effects.pe", "effects.healMul", "effects.bleedMul", "effects.infectMul", "effects.coldMul",
        "effects.drain", "effects.lethal", "effects.bruise", "effects.tempTarget", "effects.tempOffset",
        "effects.foodSickTarget", "effects.panicTarget", "effects.nvDays", "effects.own.nv", "effects.own.ss",
        "nutrients.lastAgeH", "nutrients.epoch", "nutrients.vitA.g", "nutrients.vitC.g", "nutrients.vitC.ah",
        "nutrients.iron.g", "nutrients.iron.x", "acute.debtH", "acute.awakeH", "acute.retEma", "body.dayIndex",
        "fluids.dehydPct", "fluids.thirstTarget", "effects.lastDay", "effects.key.ep")
MORE = ("nutrients.vitA.p", "nutrients.vitA.p2", "nutrients.vitC.p", "nutrients.zinc.g", "nutrients.iron.p2",
        "nutrients.iron.H", "nutrients.iron.S", "nutrients.iron.ax", "nutrients.iron.axr", "nutrients.riboflavin.g",
        "nutrients.anaemia", "fluids.viewPct", "fluids.water", "fluids.naPlasma", "effects.stressTarget",
        "effects.unhappyTarget", "effects.tempAdj", "effects.ea", "effects.nightVision", "acute.starvedDays",
        "acute.bmi", "acute.coldH", "acute.iuSleep", "acute.caf", "nutrients.lastDayIndex", "body.inDayClosed",
        "body.exKcalDay", "effects.exSeen", "body.sex", "body.fm", "body.lm")
BODY_KEYS = ("fm", "lm", "sex", "met", "dmod", "rmod", "tac", "energyState", "dayIndex", "band1Day", "band2Day",
             "bornAge", "inDayClosed", "exKcalDay")
NUT_SCAL = ("epoch", "lastAgeH", "allReplete", "anaemia", "vitDClinical", "ironGrade", "lastDayIndex")
FULL1 = ([f"{USER}.acute", f"{USER}.fluids", f"{USER}.effects", f"{USER}.dead"]
         + [f"{USER}.body.{k}" for k in BODY_KEYS] + [f"{USER}.nutrients.{k}" for k in NUT_SCAL])
NUT1 = [f"{USER}.nutrients.{k}" for k in ORDER[:14]]
NUT2 = [f"{USER}.nutrients.{k}" for k in ORDER[14:]]
OPT_KEYS = ("mode", "onsetSpeed", "deficienciesCanKill", "excessEffectsOn", "balanceBonus", "severity", "nutritionOn")
FAST = "NutritionRevamp.server.fast"
FLAG_PATHS = (f"{FAST}.endFoldOn", f"{FAST}.intoxOwned", f"{FAST}.h.{USER}.endFoldOn",
              f"{FAST}.h.{USER}.intoxOwned", f"{FAST}.h.{USER}.effOn", f"{FAST}.registered")
EFF_STATS = ("minutes", "errors", "healed", "rebuilds", "closes", "traitAdds", "traitRemoves", "reasserts", "pushes",
             "pushMissing", "regenWrites", "partWrites", "infectSyncs", "coldWrites", "drainMinutes", "bruises",
             "skippedDead")
BUS_STATS = ("marks", "pushes", "deferred", "failed")
NUT_STATS = ("minutes", "errors", "effectsErrors", "players", "days")
MIRROR_KEYS = ("effects_epoch", "effects_healMul", "effects_bleedMul", "effects_infectMul", "effects_coldMul",
               "effects_tempTarget", "effects_drain", "effects_lethal", "effects_panicTarget", "effects_foodSickTarget",
               "effects_nv", "effects_ss", "nutrients_epoch")
SW = "TKX_StatWatch"
SW_FIELDS = ("fatigue", "intoxication", "endurance", "stress", "panic", "unhappiness", "food_sickness", "poison",
             "sickness", "boredom", "temperature", "core")
SW_TAGS = ("POISON", "SICK", "FALLDOWN", "BLEEDING", "HUNGRY", "THIRST", "HEAVYLOAD", "other")
SW_DONE_WAIT = 12.0
PART_NAMES = {"Hand_L": 0, "Hand_R": 1, "ForeArm_L": 2, "ForeArm_R": 3}
NV_EDIT_DAYS = 13.95
RET_MUL = 1.1
VITA_R_FALLBACK = {1: 900.0, 2: 700.0}
H0_FALLBACK = {"hbShare": 2.0 / 3.0, "totalPerKg": {1: 50.0, 2: 40.0}}
F_CLIMATE, F_WET, F_DEBT, F_S = -10, 100, 10, 25
A_GRANT_CAP, A_REM_S, A_FOREIGN_S, A_CAR_S = 100, 8, 8, 10
B_CAP = 10
G_BASE_S, G1_S, G2_S, G3_S, G_REST_S, G_SW_S = 10, 25, 20, 20, 10, 30
K1_S, K2_S = 60, 20
L_S, L_DEHYD_PCT = 60, 7.0
H_S, H1_S, H_FS0 = 40, 20, 80
W_CAP = 360
C_S, D_S, I_S, E_S = 40, 30, 30, 40
BR_HOLD_S, BR_GAME_H = 120, 48.0
SCRATCH, BLEED_T, INFECT_SCRATCH = 10, 20, 10
VIT_C3, VIT_C4, VIT_REPLETE = 0.3, 0.1, 0.95
VITA_G2, VITA_G4, VITA_G3 = 0.2, 0.03, 0.1
SQUATS = 20
TICK_S = 10
BENCH_N = 100000
HEALTH_GUARD = 40.0
MIRROR_WAIT_S = 8.0
BAND_3003 = (3.24, 3.47)
HUNGER_CAP, THIRST_CAP = 0.69, 0.83
PE_C, PE_E = 3, 4

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


def to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.lower() in ("true", "false"):
        return v.lower() == "true"
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


def sget(tag, side):
    r = step(tag, side, "stats.get", USER if side is server else "")
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "side": "server" if side is server else "client",
           "wall": r["wall_before"], "wall_after": r["wall_after"], "sideWall": a.get("wall"),
           "worldAge": a.get("worldAge"), "asleep": a.get("asleep"), "traitList": a.get("traitList"),
           "fatigue": a.get("fatigue"), "hunger": a.get("hunger"), "thirst": a.get("thirst"),
           "moodles": a.get("moodles")}
    if not a:
        row["reply"] = r["ack"]
    out["stats_get"].append(row)
    return row


def has(row, name):
    tl_ = row.get("traitList")
    if isinstance(tl_, list):
        return name in [str(x).lower() for x in tl_]
    if isinstance(tl_, dict):
        return name in [str(x).lower() for x in tl_.values()]
    return None


def hget(tag, side=None):
    side = side or server
    r = step(tag, side, "health.get", USER)
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "side": "server" if side is server else "client",
           "wall": r["wall_before"], "wall_after": r["wall_after"], "overall": a.get("overall"),
           "health": a.get("health"), "parts": a.get("parts"), "ok": a.get("ok")}
    out["health_reads"].append(row)
    return row


def regen(tag):
    r = step(tag, server, "regen.get", USER)
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "ack": a}
    out["regen_reads"].append(row)
    return row


def tcore(tag):
    r = step(tag, server, "temp.core", USER)
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "wall_after": r["wall_after"],
           "core": a.get("core"), "setPoint": a.get("setPoint"), "temperature": a.get("temperature"),
           "heatDelta": a.get("heatDelta"), "rateOfChange": a.get("rateOfChange"), "ok": a.get("ok")}
    out["temps"].append(row)
    return row


def chain(tag, args):
    r = step(tag, server, "witness.chain", f"{USER} {args}")
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "args": args, "value": a.get("value"),
           "ok": a.get("ok"), "failedAt": a.get("failedAt")}
    out["chains"].append(row)
    return row


def bpget(tag, idx, side=None):
    side = side or server
    r = step(tag, side, "bodypart.get", f"{USER} {idx}")
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "side": "server" if side is server else "client",
           "wall": r["wall_before"], "wall_after": r["wall_after"], "which": idx, "parts": a.get("parts"),
           "ok": a.get("ok"), "reason": a.get("reason")}
    out["part_reads"].append(row)
    return row


def bpset(tag, idx, field, value, sync=False):
    a = ack(step(tag, server, "bodypart.set", f"{USER} {idx} {field} {value}" + (" sync" if sync else "")))
    row = {"tag": tag, "phase": cur_phase["name"], "wall": wall(), "part": idx, "field": field, "value": value, "ack": a}
    out["part_writes"].append(row)
    return row


def setany(tag, stat, v):
    r = step(tag, server, "stats.setany", f"{USER} {stat} {v}")
    a = ack(r)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "wall_after": r["wall_after"],
           "stat": stat, "ok": a.get("ok"), "requested": a.get("requested"), "before": a.get("before"),
           "after": a.get("after"), "reason": a.get("reason")}
    out["stat_writes"].append(row)
    return row


def _md(tag, keys):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(f"{USER}.{k}" for k in keys))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    return r, a, vals


def rec(tag, more=False):
    r, a, vals = _md(tag, MINI)
    row = {"tag": tag, "phase": cur_phase["name"], "wall": r["wall_before"], "wall_after": r["wall_after"],
           "worldAge": a.get("worldAge"), "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"),
           "error": a.get("error")}
    keys = list(MINI)
    if more:
        r2, a2, vals2 = _md(tag + "_m", MORE)
        vals = dict(vals)
        vals.update(vals2)
        row["worldAge2"] = a2.get("worldAge")
        row["missing2"] = a2.get("missing")
        keys += list(MORE)
    for k in keys:
        v = vals.get(f"{USER}.{k}")
        b = to_bool(v)
        row[k] = b if b is not None else (to_num(v) if to_num(v) is not None else v)
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


def sandbox(tag, key, value):
    a = ack(step(tag, server, "sandbox.var", f"{key} {value}"))
    row = {"tag": tag, "phase": cur_phase["name"], "key": key, "value": value, "wall": wall(), "ack": a}
    out["sandbox"].append(row)
    return row


def flags(tag):
    return {p: gv(server, p, f"{tag}_{p.split('.')[-1]}_{i}") for i, p in enumerate(FLAG_PATHS)}


def eff_stats(tag, keys=EFF_STATS):
    return {k: gv(server, f"NutritionRevamp.server.effects.stats.{k}", f"{tag}_es_{k}") for k in keys}


def counters(tag):
    return {"effects": eff_stats(tag),
            "effects_lastError": gv(server, "NutritionRevamp.server.effects.lastError", f"{tag}_ele"),
            "bus": {k: gv(server, f"NutritionRevamp.server.bus.effects.stats.{k}", f"{tag}_bs_{k}") for k in BUS_STATS},
            "nutrients": {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"{tag}_ns_{k}") for k in NUT_STATS},
            "nutrients_lastError": gv(server, "NutritionRevamp.server.nutrients.lastError", f"{tag}_nle"),
            "fast": {k: gv(server, f"{FAST}.stats.{k}", f"{tag}_fs_{k}") for k in ("calls", "failures", "disabledAt")},
            "fast_lastError": gv(server, f"{FAST}.lastError", f"{tag}_fle")}


def options(tag):
    return {k: gv(server, f"NutritionRevamp.server.options.{k}", f"{tag}_opt_{k}") for k in OPT_KEYS}


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
    srv = rec(f"{tag}_srv")
    row = {"tag": tag, "phase": cur_phase["name"], "request": req, "received_before": before,
           "received_after": after, "answered": (to_num(after) or 0) > (to_num(before) or 0),
           "wall_answered": wall(), "client": keys, "server_rec": srv["tag"]}
    out["mirror_checks"].append(row)
    return row


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


def wait_res(side, name, after, timeout):
    try:
        return side.bus.wait_result(name, timeout=timeout, after=after)
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


def until(tag, cond, cap, every=0.6, more=False, extra=None):
    """rec() every `every` s until cond(row) or cap s; returns (rows, met)."""
    rows = []
    end = wall() + cap
    i = 0
    while wall() < end:
        t_s = wall()
        r = rec(f"{tag}_{i}", more=more)
        x = extra(i) if extra is not None else None
        rows.append({"r": r["tag"], "x": x})
        i += 1
        try:
            if cond(r, x):
                return rows, True
        except Exception:                      # noqa: BLE001
            pass
        rest = every - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    return rows, False


def part_index(name):
    return state["parts"].get(name, PART_NAMES[name])


def clear_bleeding(tag):
    r = bpget(f"{tag}_all", "all")
    cleared = []
    for p in r.get("parts") or []:
        if not isinstance(p, dict):
            continue
        b = to_bool(p.get("bleeding"))
        bt = to_num(p.get("bleedingTime")) or 0
        if b or bt > 0:
            i = int(to_num(p.get("index")) or 0)
            bpset(f"{tag}_b{i}", i, "bleeding", "false")
            bpset(f"{tag}_t{i}", i, "bleedingTime", 0)
            cleared.append(i)
    return cleared


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["time_server"] = ack(step("S0_time_s", server, "time.snapshot"))
    P["time_client"] = ack(step("S0_time_c", client, "time.snapshot"))
    P["options"] = options("S0")
    P["flags"] = flags("S0_flags")
    P["version"] = {"server": gv(server, "NutritionRevamp.version", "S0_ver_s"),
                    "client": gv(client, "NutritionRevamp.version", "S0_ver_c")}
    waited = []
    end = wall() + 20.0
    first = None
    while wall() < end:
        r = rec(f"S0_wait{len(waited)}", more=True)
        waited.append(r["tag"])
        if r.get("effects.epoch") is not None and r.get("body.sex") is not None:
            first = r
            break
        time.sleep(1.0)
    P["wait_recs"] = waited
    P["first_effects_rec"] = first["tag"] if first else None
    P["full"] = rec_full("S0_full")["tag"]
    P["counters"] = counters("S0_cnt")
    P["stats_client"] = sall("S0_c", client)["tag"]
    P["stats_server"] = sall("S0_s", server)["tag"]
    P["traits_s"] = sget("S0_tr_s", server)["tag"]
    P["traits_c"] = sget("S0_tr_c", client)["tag"]
    parts = bpget("S0_parts", "all")
    for p in parts.get("parts") or []:
        if isinstance(p, dict) and p.get("name") in PART_NAMES:
            state["parts"][p["name"]] = int(to_num(p.get("index")) or PART_NAMES[p["name"]])
    P["part_index"] = dict(state["parts"])
    P["health"] = hget("S0_h")["tag"]
    P["regen"] = regen("S0_regen")["tag"]
    P["temp"] = tcore("S0_temp")["tag"]
    P["cold"] = chain("S0_cold", "getBodyDamage.getCatchACold")["tag"]
    P["sight"] = ack(step("S0_sight", client, "sight.range"))
    P["mirror"] = mirror_check("S0_mirror")["tag"]
    # the arm-C setup: these wait for the real close (deviation 1)
    P["edit_starved"] = setpath("S0_starved", "acute.starvedDays", 6)
    P["edit_bmi"] = setpath("S0_bmi", "acute.bmi", 16.5)
    P["after_edit"] = rec("S0_after", more=True)["tag"]


def phase_J():
    P = out["phases"]["J"] = {"bench": []}
    for i in range(3):
        a = ack(step(f"J_bench{i}", server, "bench.global", f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60))
        P["bench"].append({"i": i, "discarded": i == 0, "ack": a})
    P["tick"] = tick_rate("J")


def cold_window(prefix, seconds):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        c = chain(f"{prefix}_c{i}", "getBodyDamage.getCatchACold")
        d = chain(f"{prefix}_d{i}", "getBodyDamage.getThermoregulator.getCatchAColdDelta")
        r = rec(f"{prefix}_r{i}")
        rows.append({"i": i, "c": c["tag"], "d": d["tag"], "r": r["tag"]})
        i += 1
    return rows


def phase_F():
    P = out["phases"]["F"] = {}
    P["full0"] = rec_full("F_full0")["tag"]
    P["coldWrites0"] = gv(server, "NutritionRevamp.server.effects.stats.coldWrites", "F_cw0")
    P["climate"] = ack(step("F_climate", server, "climate.set", str(F_CLIMATE)))
    P["wet"] = setany("F_wet", "WETNESS", F_WET)["tag"]
    P["F0"] = cold_window("F0", F_S)
    P["temp0"] = tcore("F_temp0")["tag"]
    P["edit_debt"] = setpath("F_debt", "acute.debtH", F_DEBT)
    time.sleep(1.5)
    P["full1"] = rec_full("F_full1")["tag"]
    P["F1"] = cold_window("F1", F_S)
    P["coldWrites1"] = gv(server, "NutritionRevamp.server.effects.stats.coldWrites", "F_cw1")
    P["temp1"] = tcore("F_temp1")["tag"]
    P["edit_debt0"] = setpath("F_debt0", "acute.debtH", 0)
    P["climate_off"] = ack(step("F_climate_off", server, "climate.set", "off"))
    P["wet0"] = setany("F_wet0", "WETNESS", 0)["tag"]
    time.sleep(1.5)
    P["after"] = rec("F_after", more=True)["tag"]
    P["cold_after"] = chain("F_cold_after", "getBodyDamage.getCatchACold")["tag"]


def phase_A():
    P = out["phases"]["A"] = {}
    r0 = rec("A0", more=True)
    sex = int(to_num(r0.get("body.sex")) or 2)
    R = None
    try:
        R = float(KK.NR.data.records.REC.vitA.R[sex])
    except Exception:                          # noqa: BLE001
        R = VITA_R_FALLBACK.get(sex, 700.0)
    P["sex"], P["R"], P["retEma_write"] = sex, R, R * RET_MUL
    P["pre_s"] = sget("A0_s", server)["tag"]
    P["pre_c"] = sget("A0_c", client)["tag"]
    P["es0"] = eff_stats("A0", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    t_arm = time.time()
    P["watch"] = ack(step("A_watch", client, "trait.watch", f"nightvision {A_GRANT_CAP + 30}"))
    P["edit_ret"] = setpath("A_ret", "acute.retEma", R * RET_MUL)
    P["edit_nv"] = setpath("A_nv", "effects.nvDays", NV_EDIT_DAYS)
    P["edit_wall"] = wall()

    def srv(i):
        s = sget(f"A1_s{i}", server)
        return {"s": s["tag"], "has": has(s, "nightvision"), "wall": s["wall"]}
    rows, met = until("A1", lambda r, x: r.get("effects.own.nv") is True and x and x.get("has"), A_GRANT_CAP,
                      every=0.8, extra=srv)
    P["grant_polls"], P["granted"] = rows, met
    P["watch_result"] = wait_res(client, "trait-watch", t_arm - 0.5, 15)
    P["after_c"] = sget("A1_c", client)["tag"]
    P["es1"] = eff_stats("A1", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    P["mirror"] = mirror_check("A_mirror")["tag"]
    persist()
    # A2: an external removal (no push)
    P["remove"] = ack(step("A2_remove", server, "trait.set", f"{USER} NIGHT_VISION remove"))
    P["remove_wall"] = wall()
    polls = []
    end = wall() + A_REM_S
    i = 0
    while wall() < end:
        s = sget(f"A2_s{i}", server)
        polls.append({"s": s["tag"], "has": has(s, "nightvision"), "wall": s["wall"]})
        i += 1
    P["remove_polls"] = polls
    P["remove_c"] = sget("A2_c", client)["tag"]
    P["es2"] = eff_stats("A2", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    # A3: grade 2 -> withdrawn
    P["edit_g2"] = setpath("A3_g2", "nutrients.vitA.p", VITA_G2)
    rows, met = until("A3", lambda r, x: r.get("effects.own.nv") is False and x and x.get("has") is False, 12,
                      every=0.6, extra=srv)
    P["withdraw_polls"], P["withdrawn"] = rows, met
    cpolls = []
    end = wall() + 6.0
    i = 0
    while wall() < end:
        c = sget(f"A3_c{i}", client)
        cpolls.append({"c": c["tag"], "has": has(c, "nightvision"), "wall": c["wall"]})
        i += 1
        if cpolls[-1]["has"] is False:
            break
    P["withdraw_client"] = cpolls
    P["es3"] = eff_stats("A3", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    persist()
    # A4: a foreign NIGHT_VISION
    P["foreign"] = ack(step("A4_add", server, "trait.add.push", f"{USER} NIGHT_VISION"))
    rows, _ = until("A4", lambda r, x: False, A_FOREIGN_S, every=0.6, extra=srv)
    P["foreign_polls"] = rows
    P["foreign_c"] = sget("A4_c", client)["tag"]
    P["es4"] = eff_stats("A4", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    P["foreign_rm"] = ack(step("A4_rm", server, "trait.set", f"{USER} NIGHT_VISION remove"))
    P["foreign_push"] = ack(step("A4_push", server, "trait.push", USER))
    # A5: carotene-only
    P["edit_p"] = setpath("A5_p", "nutrients.vitA.p", VIT_REPLETE)
    P["edit_ret0"] = setpath("A5_ret0", "acute.retEma", 0)
    P["edit_nv5"] = setpath("A5_nv5", "effects.nvDays", 5)
    rows, _ = until("A5", lambda r, x: False, A_CAR_S, every=0.8)
    P["carotene_polls"] = rows
    P["end_s"] = sget("A5_s", server)["tag"]


def phase_B():
    P = out["phases"]["B"] = {}
    P["base"] = ack(step("B0_sight", client, "sight.range"))

    def srv(i):
        s = sget(f"B_s{cur_sub['n']}_{i}", server)
        return {"s": s["tag"], "has": has(s, "shortsighted"), "wall": s["wall"]}
    t_arm = time.time()
    P["watch"] = ack(step("B_watch", client, "trait.watch", "shortsighted 40"))
    cur_sub["n"] = 1
    P["edit_g4"] = setpath("B1_g4", "nutrients.vitA.p", VITA_G4)
    rows, met = until("B1", lambda r, x: r.get("effects.own.ss") is True and x and x.get("has"), B_CAP, every=0.6,
                      extra=srv)
    P["add_polls"], P["added"] = rows, met
    P["watch_result"] = wait_res(client, "trait-watch", t_arm - 0.5, 15)
    time.sleep(1.0)
    P["sight_ss"] = ack(step("B1_sight", client, "sight.range"))
    P["c1"] = sget("B1_c", client)["tag"]
    cur_sub["n"] = 2
    P["sev05"] = sandbox("B2_sev", "NR.Severity", 0.5)
    rows, met = until("B2", lambda r, x: r.get("effects.own.ss") is False and x and x.get("has") is False, B_CAP,
                      every=0.6, extra=srv)
    P["sev05_polls"], P["sev05_removed"] = rows, met
    time.sleep(1.0)
    P["c2"] = sget("B2_c", client)["tag"]
    P["sight_sev05"] = ack(step("B2_sight", client, "sight.range"))
    cur_sub["n"] = 3
    P["sev1"] = sandbox("B3_sev", "NR.Severity", 1)
    rows, met = until("B3", lambda r, x: r.get("effects.own.ss") is True and x and x.get("has"), B_CAP, every=0.6,
                      extra=srv)
    P["sev1_polls"], P["sev1_added"] = rows, met
    time.sleep(1.0)
    P["c3"] = sget("B3_c", client)["tag"]
    cur_sub["n"] = 4
    P["edit_g3"] = setpath("B4_g3", "nutrients.vitA.p", VITA_G3)
    rows, met = until("B4", lambda r, x: r.get("effects.own.ss") is False and x and x.get("has") is False, B_CAP,
                      every=0.6, extra=srv)
    P["g3_polls"], P["g3_removed"] = rows, met
    time.sleep(1.0)
    P["c4"] = sget("B4_c", client)["tag"]
    P["sight_g3"] = ack(step("B4_sight", client, "sight.range"))
    P["edit_rep"] = setpath("B5_rep", "nutrients.vitA.p", VIT_REPLETE)
    P["es"] = eff_stats("B", ("traitAdds", "traitRemoves", "reasserts", "pushes"))
    P["opt"] = options("B")


def temp_window(prefix, seconds):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        t = tcore(f"{prefix}_t{i}")
        r = rec(f"{prefix}_r{i}") if i % 2 == 0 else None
        rows.append({"i": i, "t": t["tag"], "r": r["tag"] if r else None})
        i += 1
    return rows


def phase_G():
    P = out["phases"]["G"] = {}
    P["G0"] = temp_window("G0", G_BASE_S)
    r = rec("G1_pre", more=True)
    sex = int(to_num(r.get("body.sex")) or 2)
    w = (to_num(r.get("body.fm")) or 0) + (to_num(r.get("body.lm")) or 0)
    try:
        two = KK.NR.data.records.REC.iron.two
        hb, tpk = float(two.hbShare), float(two.totalPerKg[sex])
    except Exception:                          # noqa: BLE001
        hb, tpk = H0_FALLBACK["hbShare"], H0_FALLBACK["totalPerKg"][sex]
    H0 = hb * tpk * w
    Hb = to_num(r.get("nutrients.iron.H"))
    P["H0"], P["H_before"], P["w"], P["sex"] = H0, Hb, w, sex
    P["edit_H"] = setpath("G1_H", "nutrients.iron.H", 0.5 * H0)
    P["arm1"] = sw_arm("G1", G_SW_S)
    P["G1"] = temp_window("G1", G1_S)
    P["sq1"] = ack(step("G2_sq", client, "exercise.do", f"squats {SQUATS}"))
    P["G2"] = temp_window("G2", G2_S)
    P["watch1"] = sw_collect("G1", P["arm1"])
    P["stop1"] = ack(step("G2_stop", client, "player.stop", ""))
    P["edit_H_back"] = setpath("G3_H", "nutrients.iron.H", Hb if Hb is not None else H0)
    P["arm3"] = sw_arm("G3", G_SW_S)
    P["sq3"] = ack(step("G3_sq", client, "exercise.do", f"squats {SQUATS}"))
    P["G3"] = temp_window("G3", G3_S)
    P["stop3"] = ack(step("G3_stop", client, "player.stop", ""))
    P["G4"] = temp_window("G4", G_REST_S)
    P["watch3"] = sw_collect("G3", P["arm3"])
    P["end"] = rec("G_end", more=True)["tag"]


def poll(prefix, seconds, every=1.0, client_every=2, rec_every=3, extra=None):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        t_s = wall()
        row = {"i": i}
        if client_every and i % client_every == 0:
            row["c"] = sall(f"{prefix}_c{i}", client)["tag"]
        row["s"] = sall(f"{prefix}_s{i}", server)["tag"]
        if rec_every and i % rec_every == 0:
            row["r"] = rec(f"{prefix}_r{i}")["tag"]
        if extra is not None:
            try:
                extra(i, row)
            except Exception as e:             # noqa: BLE001
                row["extra_error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
        i += 1
        rest = every - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    return rows


def phase_K():
    P = out["phases"]["K"] = {}
    P["full0"] = rec_full("K_full0")["tag"]
    P["arm1"] = sw_arm("K1", K1_S)
    P["edit_awake"] = setpath("K1_awake", "acute.awakeH", 24)
    P["polls1"] = poll("K1", K1_S - 10, every=0.6, client_every=2, rec_every=3)
    P["full1"] = rec_full("K_full1")["tag"]
    P["watch1"] = sw_collect("K1", P["arm1"])
    P["arm2"] = sw_arm("K2", K2_S)
    P["edit_awake0"] = setpath("K2_awake0", "acute.awakeH", 0)
    P["polls2"] = poll("K2", K2_S - 5, every=0.6, client_every=2, rec_every=3)
    P["watch2"] = sw_collect("K2", P["arm2"])
    P["full2"] = rec_full("K_full2")["tag"]


def phase_L():
    P = out["phases"]["L"] = {}
    r = rec("L0", more=True)
    w = (to_num(r.get("body.fm")) or 0) + (to_num(r.get("body.lm")) or 0)
    water = -L_DEHYD_PCT * w * 10 if w > 0 else -5600
    P["w"], P["water"] = w, water
    P["arm"] = sw_arm("L", L_S)
    P["edit"] = setpath("L_water", "fluids.water", water)

    def extra(i, row):
        if i % 5 == 4:
            row["w"] = setpath(f"L_w{i}", "fluids.water", water)["tag"]
    P["polls"] = poll("L", L_S - 5, every=0.6, client_every=2, rec_every=4, extra=extra)
    P["watch"] = sw_collect("L", P["arm"])
    P["full"] = rec_full("L_full")["tag"]
    P["edit0"] = setpath("L_water0", "fluids.water", 0)
    time.sleep(2.0)
    P["after"] = rec("L_after", more=True)["tag"]


def phase_H():
    P = out["phases"]["H"] = {}
    P["h0"] = hget("H0_h")["tag"]
    P["regen0"] = regen("H0_regen")["tag"]
    P["full0"] = rec_full("H_full0")["tag"]
    P["fs80"] = setany("H_fs80", "FOOD_SICKNESS", H_FS0)["tag"]
    P["arm"] = sw_arm("H", H_S + 5)
    P["edit_ax"] = setpath("H_ax", "nutrients.iron.ax", 48)
    P["edit_axr"] = setpath("H_axr", "nutrients.iron.axr", 3)
    P["edit_wall"] = wall()

    def extra(i, row):
        row["h"] = hget(f"H_h{i}")["tag"]
        if i == 6:
            row["regen"] = regen(f"H_regen{i}")["tag"]
    P["polls"] = poll("H", H_S, every=1.5, client_every=4, rec_every=1, extra=extra)
    P["watch"] = sw_collect("H", P["arm"])
    P["full1"] = rec_full("H_full1")["tag"]
    # H1: the dial off
    P["kill0"] = sandbox("H1_kill0", "NR.DeficienciesCanKill", "false")
    time.sleep(3.0)
    P["opt1"] = options("H1")
    P["regen1"] = regen("H1_regen")["tag"]

    def extra1(i, row):
        row["h"] = hget(f"H1_h{i}")["tag"]
    P["polls1"] = poll("H1", H1_S, every=1.5, client_every=0, rec_every=1, extra=extra1)
    P["full2"] = rec_full("H_full2")["tag"]
    # H2: restore
    P["kill1"] = sandbox("H2_kill1", "NR.DeficienciesCanKill", "true")
    P["ax0"] = setpath("H2_ax0", "nutrients.iron.ax", 0)
    P["axr0"] = setpath("H2_axr0", "nutrients.iron.axr", 0)
    time.sleep(2.0)
    P["fs0"] = setany("H2_fs0", "FOOD_SICKNESS", 0)["tag"]
    P["end"] = rec("H2_end", more=True)["tag"]
    P["regen2"] = regen("H2_regen")["tag"]
    P["h2"] = hget("H2_h")["tag"]


def phase_W():
    P = out["phases"]["W"] = {}
    rows, met = until("W", lambda r, x: (to_num(r.get("body.dayIndex")) or 0) >= 1
                      and (to_num(r.get("effects.lastDay")) or 0) >= 1, W_CAP, every=3.0, more=True)
    P["polls"], P["closed"] = rows, met
    time.sleep(1.5)
    P["full"] = rec_full("W_full")["tag"]
    P["es"] = eff_stats("W", ("closes", "rebuilds"))


def rebuild_pe(tag, pe):
    a = setpath(f"{tag}_pe", "effects.pe", pe)
    b = setpath(f"{tag}_ep", "effects.key.ep", -1)
    return {"pe": a["tag"], "ep": b["tag"]}


def part_window(prefix, idx, seconds, health=False, client_every=0):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        b = bpget(f"{prefix}_b{i}", idx)
        r = rec(f"{prefix}_r{i}")
        row = {"i": i, "b": b["tag"], "r": r["tag"]}
        if health:
            row["h"] = hget(f"{prefix}_h{i}")["tag"]
        if client_every and i % client_every == 0:
            row["c"] = bpget(f"{prefix}_c{i}", idx, client)["tag"]
        rows.append(row)
        i += 1
    return rows


def phase_C():
    P = out["phases"]["C"] = {}
    P["full0"] = rec_full("C_full0")["tag"]
    r = rec("C0", more=True)
    P["pe_at_close"] = r.get("effects.pe")
    P["fallback"] = None
    if to_num(r.get("effects.pe")) != PE_C:
        P["fallback"] = rebuild_pe("C0_fb", PE_C)
        note(f"arm C: pe read {r.get('effects.pe')} after the close, not {PE_C}: the fallback edit (deviation 1)")
    P["edit_c3"] = setpath("C0_c3", "nutrients.vitC.p", VIT_C3)
    rows, met = until("C0w", lambda r_, x: to_num(r_.get("nutrients.vitC.g")) == 3
                      and to_num(r_.get("effects.healMul")) is not None and to_num(r_.get("effects.healMul")) < 1, 8)
    P["c3_polls"], P["c3_met"] = rows, met
    P["full1"] = rec_full("C_full1")["tag"]
    P["regen1"] = regen("C1_regen")["tag"]
    idx = part_index("ForeArm_L")
    P["idx"] = idx
    P["scratch1"] = bpset("C1_scr", idx, "scratchTime", SCRATCH)["tag"]
    P["C1"] = part_window("C1", idx, C_S)
    P["regen1b"] = regen("C1_regen_b")["tag"]
    P["es1"] = eff_stats("C1", ("partWrites", "regenWrites", "rebuilds"))
    # C2: healMul 1
    P["edit_rep"] = setpath("C2_rep", "nutrients.vitC.p", VIT_REPLETE)
    P["reset"] = rebuild_pe("C2", 1)
    rows, met = until("C2w", lambda r_, x: to_num(r_.get("effects.healMul")) == 1, 8)
    P["rep_polls"], P["rep_met"] = rows, met
    P["full2"] = rec_full("C_full2")["tag"]
    P["regen2"] = regen("C2_regen")["tag"]
    P["scratch2"] = bpset("C2_scr", idx, "scratchTime", SCRATCH)["tag"]
    P["C2"] = part_window("C2", idx, C_S)
    P["es2"] = eff_stats("C2", ("partWrites", "regenWrites", "rebuilds"))
    P["clear"] = bpset("C2_clr", idx, "scratchTime", 0)["tag"]


def bleed_window(tag):
    idx = part_index("Hand_L")
    W = {"idx": idx}
    W["full"] = rec_full(f"{tag}_full")["tag"]
    W["h0"] = hget(f"{tag}_h0")["tag"]
    W["set_b"] = bpset(f"{tag}_b", idx, "bleeding", "true")["tag"]
    W["set_t"] = bpset(f"{tag}_t", idx, "bleedingTime", BLEED_T)["tag"]
    W["polls"] = part_window(tag, idx, D_S)
    W["h1"] = hget(f"{tag}_h1")["tag"]
    W["es"] = eff_stats(tag, ("partWrites", "bruises"))
    W["clr_b"] = bpset(f"{tag}_cb", idx, "bleeding", "false")["tag"]
    W["clr_t"] = bpset(f"{tag}_ct", idx, "bleedingTime", 0)["tag"]
    return W


def phase_D0():
    out["phases"]["D0"] = bleed_window("D0")


def phase_I():
    P = out["phases"]["I"] = {}
    P["edit_c4"] = setpath("I_c4", "nutrients.vitC.p", VIT_C4)
    rows, met = until("I0", lambda r, x: to_num(r.get("nutrients.vitC.g")) == 4, 8)
    P["c4_polls"], P["c4_met"] = rows, met
    P["h0"] = hget("I_h0")["tag"]
    P["edit_ah"] = setpath("I_ah", "nutrients.vitC.ah", 800)
    P["edit_wall"] = wall()

    def extra(i, row):
        row["h"] = hget(f"I_h{i}")["tag"]
        if i == 5:
            row["regen"] = regen(f"I_regen{i}")["tag"]
    P["polls"] = poll("I", I_S, every=1.5, client_every=0, rec_every=1, extra=extra)
    P["full"] = rec_full("I_full")["tag"]
    P["mirror"] = mirror_check("I_mirror")["tag"]
    P["edit_ah0"] = setpath("I_ah0", "nutrients.vitC.ah", 0)
    time.sleep(2.0)
    P["after"] = rec("I_after", more=True)["tag"]
    P["regen_after"] = regen("I_regen_after")["tag"]


def phase_D1():
    out["phases"]["D1"] = bleed_window("D1")


def phase_BR():
    P = out["phases"]["BR"] = {}
    P["edit_starved"] = setpath("BR_starved", "acute.starvedDays", 10)
    P["es0"] = eff_stats("BR0", ("bruises", "minutes", "closes", "partWrites"))
    P["parts0"] = bpget("BR_parts0", "all")["tag"]
    r0 = rec("BR_r0", more=True)
    P["age0"] = r0.get("worldAge")
    P["water0"] = setpath("BR_w0", "fluids.water", 0)["tag"]
    r = step("BR_hold", server, "player.sleep.hold", f"{USER} {BR_HOLD_S}")
    P["hold_wall"], P["hold"] = r["wall_before"], r["ack"]
    polls = []
    end = P["hold_wall"] + BR_HOLD_S
    i = 0
    a0 = to_num(P["age0"])
    while wall() < end:
        t_s = wall()
        rr = rec(f"BR_p{i}")
        p = {"i": i, "r": rr["tag"], "w": setpath(f"BR_w{i}", "fluids.water", 0)["tag"]}
        if i % 3 == 2:
            p["parts"] = bpget(f"BR_parts{i}", "all")["tag"]
        if i % 5 == 0:
            p["g"] = sget(f"BR_g{i}", server)["tag"]
        polls.append(p)
        i += 1
        wa = to_num(rr.get("worldAge"))
        if a0 is not None and wa is not None and wa - a0 >= BR_GAME_H:
            break
        rest = 2.0 - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    P["polls"] = polls
    P["cancel"] = ack(step("BR_cancel", server, "player.sleep.hold", f"{USER} 0"))
    P["cancel_wall"] = wall()
    P["es1"] = eff_stats("BR1", ("bruises", "minutes", "closes", "partWrites"))
    P["end"] = rec("BR_end", more=True)["tag"]
    P["parts1"] = bpget("BR_parts1", "all")["tag"]
    P["get_after"] = sget("BR_get_after", server)["tag"]
    P["cleared"] = clear_bleeding("BR_clr")
    P["water1"] = setpath("BR_w_end", "fluids.water", 0)["tag"]
    time.sleep(3.0)
    P["full"] = rec_full("BR_full")["tag"]


def phase_E():
    P = out["phases"]["E"] = {}
    P["edit_rep"] = setpath("E0_rep", "nutrients.vitC.p", VIT_REPLETE)
    rows, met = until("E0w", lambda r, x: to_num(r.get("nutrients.vitC.g")) == 1, 8)
    P["rep_polls"], P["rep_met"] = rows, met
    P["full0"] = rec_full("E_full0")["tag"]
    r = rec("E0", more=True)
    P["pe_read"] = r.get("effects.pe")
    P["fallback"] = None
    if to_num(r.get("effects.pe")) != PE_E:
        P["fallback"] = rebuild_pe("E0_fb", PE_E)
        note(f"arm E: pe read {r.get('effects.pe')} after the sleep's closes, not {PE_E}: the fallback edit (deviation 1)")
        until("E0fb", lambda r_, x: to_num(r_.get("effects.infectMul")) is not None and to_num(r_.get("effects.infectMul")) > 1, 8)
    P["full1"] = rec_full("E_full1")["tag"]
    idx = part_index("Hand_R")
    P["idx"] = idx
    P["scr"] = bpset("E1_scr", idx, "scratchTime", INFECT_SCRATCH)["tag"]
    P["inf"] = bpset("E1_inf", idx, "infectedWound", "true")["tag"]
    P["E1"] = part_window("E1", idx, E_S, client_every=4)
    P["E1_pair_s"] = bpget("E1_pair_s", idx)["tag"]
    P["E1_pair_c"] = bpget("E1_pair_c", idx, client)["tag"]
    P["es1"] = eff_stats("E1", ("partWrites", "infectSyncs", "rebuilds"))
    P["reset"] = rebuild_pe("E2", 1)
    rows, met = until("E2w", lambda r_, x: to_num(r_.get("effects.infectMul")) == 1, 8)
    P["reset_polls"], P["reset_met"] = rows, met
    P["E2"] = part_window("E2", idx, E_S, client_every=4)
    P["es2"] = eff_stats("E2", ("partWrites", "infectSyncs", "rebuilds"))
    P["clr_inf"] = bpset("E2_cinf", idx, "infectedWound", "false")["tag"]
    P["clr_lvl"] = bpset("E2_clvl", idx, "woundInfectionLevel", 0)["tag"]
    P["clr_scr"] = bpset("E2_cscr", idx, "scratchTime", 0)["tag"]


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["counters"] = counters("Z_cnt")
    P["flags"] = flags("Z_flags")
    P["options"] = options("Z")
    P["full"] = rec_full("Z_full")["tag"]
    P["stats_c"] = sall("Z_c", client)["tag"]
    P["stats_s"] = sall("Z_s", server)["tag"]
    P["health_s"] = hget("Z_h_s", server)["tag"]
    P["health_c"] = hget("Z_h_c", client)["tag"]
    P["regen"] = regen("Z_regen")["tag"]
    P["traits_s"] = sget("Z_tr_s", server)["tag"]
    P["traits_c"] = sget("Z_tr_c", client)["tag"]


PHASES = (("S0", phase_S0), ("J", phase_J), ("F", phase_F), ("A", phase_A), ("B", phase_B), ("G", phase_G),
          ("K", phase_K), ("L", phase_L), ("H", phase_H), ("W", phase_W), ("C", phase_C), ("D0", phase_D0),
          ("I", phase_I), ("D1", phase_D1), ("BR", phase_BR), ("E", phase_E), ("Z", phase_Z))


def body():
    for name, fn in PHASES:
        run_phase(name, fn)
        why = mod_error(name)
        if why and name != "Z":
            out["abort"] = {"after": name, "why": why}
            note(f"mod error or health guard after {name}: the arms stop here (a mod error is the primary reading)")
            persist()
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
    local w = (body.fm or 0) + (body.lm or 0)
    local E2 = { }
    local d = K.effects.drain(E2, nut, fl, a, pe, w > 0 and (body.fm or 0) / w or 0, body.sex or 2, record.canKill ~= false)
    E.drainReplay = d
    E.lethalReplay = E2.lethal
    E.ssWant = K.effects.ssWant(nut.vitA.g, sev)
    return E
end
function R.peGrade(bmi, starved)
    return K.effects.peGrade(bmi, starved, nil)
end
function R.drainRate(code)
    return K.effects.DRAIN_RATE[code]
end
function R.nvStep(nvDays, vitAg, zincG, ironG, riboG, retOk, dtD)
    local E = { nvDays = nvDays }
    local want = K.effects.nvMinute(E, vitAg, zincG, ironG, riboG, retOk, dtD)
    return want, E.nvDays
end
function R.thirst(dehydPct, c, na, canKill)
    return K.fluids.thirstTarget(dehydPct, c, na, canKill)
end
function R.vitAR(sex)
    return NR.data.records.REC.vitA.R[sex]
end
function R.consts()
    return K.effects.NV_GRANT, K.effects.NV_REGRANT, NR.data.effects.BRUISE_T0, K.effects.SCURVY_H
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


def rows_by(lst, key="tag"):
    return {r[key]: r for r in lst}


def slope_xy(pts):
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx <= 0:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx


def clock(rec_tags):
    """Game hours per wall second over a window's rec reads (world age against wall)."""
    RL = rows_by(out["recs"])
    pts = [(RL[t]["wall"], to_num(RL[t].get("worldAge"))) for t in rec_tags if t in RL and to_num(RL[t].get("worldAge")) is not None]
    return slope_xy(pts), len(pts)


def part_series(rows, field):
    PR = rows_by(out["part_reads"])
    pts = []
    for r in rows:
        b = PR.get(r.get("b"))
        if not b or not b.get("parts"):
            continue
        p = b["parts"][0] if isinstance(b["parts"], list) else None
        v = to_num((p or {}).get(field))
        if v is not None:
            pts.append((b["wall"], v))
    return pts


def window_rate(rows, field):
    pts = part_series(rows, field)
    gh, n = clock([r.get("r") for r in rows])
    s = slope_xy(pts)
    return {"n": len(pts), "first": pts[0][1] if pts else None, "last": pts[-1][1] if pts else None,
            "wall_span": (pts[-1][0] - pts[0][0]) if pts else None, "per_wall_s": s, "game_h_per_wall_s": gh,
            "per_game_h": (s / gh) if (s is not None and gh) else None,
            "change": (pts[-1][1] - pts[0][1]) if pts else None}


def health_rate(rows):
    HR = rows_by(out["health_reads"])
    pts = []
    for r in rows:
        h = HR.get(r.get("h"))
        if h and to_num(h.get("overall")) is not None:
            pts.append((h["wall"], to_num(h["overall"])))
    gh, n = clock([r.get("r") for r in rows if r.get("r")])
    s = slope_xy(pts)
    return {"n": len(pts), "first": pts[0][1] if pts else None, "last": pts[-1][1] if pts else None,
            "per_wall_s": s, "game_h_per_wall_s": gh, "per_game_h": (s / gh) if (s is not None and gh) else None}


def grade_all():
    sm = out["summaries"]
    try:
        KK2 = Kernel()
        R = KK2.R
        sm["kernel_loaded"] = True
    except Exception as e:                     # noqa: BLE001
        sm["kernel_loaded"] = f"{type(e).__name__}: {e}"
        return
    RL = rows_by(out["recs"])
    SA = rows_by(out["stats_all"])
    SG = rows_by(out["stats_get"])
    P = out["phases"]
    opts = (P.get("S0") or {}).get("options") or {}
    bonus0 = opts.get("balanceBonus") is not False
    # ---- the composer replay at every full read (sev and canKill from the sandbox edits before it)
    comp = []
    for f in out["full"]:
        rec_ = record_of(f)
        if rec_ is None:
            comp.append({"tag": f["tag"], "skipped": "a table missing"})
            continue
        sev, kill = 1.0, True
        for s_ in out["sandbox"]:
            if s_["wall"] <= f["wall"] - 1.0:
                if s_["key"] == "NR.Severity":
                    sev = to_num(s_["value"])
                if s_["key"] == "NR.DeficienciesCanKill":
                    kill = str(s_["value"]).lower() == "true"
        rec_["canKill"] = kill
        try:
            E = KK2.to_py(R.compose(KK2.table(rec_), sev, bonus0, False))
        except Exception as e:                 # noqa: BLE001
            comp.append({"tag": f["tag"], "error": f"{type(e).__name__}: {e}"})
            continue
        live = rec_["effects"]
        row = {"tag": f["tag"], "phase": f.get("phase"), "sev": sev, "canKill": kill,
               "bands": [E["bands"].get(i) for i in range(1, 13)], "mismatch": {}}
        for k in ("healMul", "bleedMul", "infectMul", "coldMul", "tempOffset", "bruise", "foodSickTarget",
                  "panicTarget", "unhappyTarget", "stressTarget", "shortSighted"):
            row[k] = {"replay": E.get(k), "live": live.get(k)}
            lv = live.get(k)
            if isinstance(lv, (int, float)) and isinstance(E.get(k), (int, float)) and abs(lv - E[k]) > 1e-12:
                row["mismatch"][k] = (E[k], lv)
        row["drain"] = {"replay": E.get("drainReplay"), "live": live.get("drain")}
        row["lethal"] = {"replay": E.get("lethalReplay"), "live": live.get("lethal")}
        if isinstance(live.get("drain"), (int, float)) and abs(live["drain"] - (E.get("drainReplay") or 0)) > 1e-12:
            row["mismatch"]["drain"] = (E.get("drainReplay"), live.get("drain"))
        row["pe"], row["ea"] = live.get("pe"), live.get("ea")
        a = rec_["acute"]
        row["pe_replay_from_acute"] = R.peGrade(a.get("bmi") or 0, a.get("starvedDays") or 0)
        row["grades"] = {k: (rec_["nutrients"].get(k) or {}).get("g") for k in ("vitA", "vitC", "zinc", "iron", "riboflavin")}
        row["iron_x"] = (rec_["nutrients"].get("iron") or {}).get("x")
        row["vitC_ah"] = (rec_["nutrients"].get("vitC") or {}).get("ah")
        row["acute"] = {k: a.get(k) for k in ("bmi", "starvedDays", "debtH", "awakeH", "iuSleep", "retEma")}
        row["epoch"] = live.get("epoch")
        comp.append(row)
    sm["compose"] = comp
    sm["compose_mismatch_tags"] = [c["tag"] for c in comp if c.get("mismatch")]
    nvg, nvr, bt0, sch = R.consts()
    sm["constants"] = {"NV_GRANT": nvg, "NV_REGRANT": nvr, "BRUISE_T0": bt0, "SCURVY_H": sch,
                       "drain_iron": R.drainRate(7), "drain_scurvy": R.drainRate(2)}
    # ---- J cost
    Jp = P.get("J") or {}
    us = [to_num((b.get("ack") or {}).get("usPerCall")) for b in Jp.get("bench", [])]
    sm["J"] = {"us_per_call": us, "kept": us[1:], "band_3003": BAND_3003, "band_top_10pct": BAND_3003[1] * 1.1,
               "within_10pct": all(u is not None and u <= BAND_3003[1] * 1.1 for u in us[1:]) if len(us) == 3 else None,
               "tick": ((Jp.get("tick") or {}).get("result") or {})}
    # ---- A night vision
    A = sm["A"] = {}
    Ap = P.get("A") or {}
    gp = Ap.get("grant_polls") or []
    first_own = next((RL[x["r"]] for x in gp if RL.get(x["r"], {}).get("effects.own.nv") is True), None)
    first_srv = next((x["x"] for x in gp if (x.get("x") or {}).get("has")), None)
    A["edit_wall"] = Ap.get("edit_wall")
    A["first_own_nv"] = {"tag": first_own["tag"], "wall": first_own["wall"], "worldAge": first_own.get("worldAge"),
                         "nvDays": first_own.get("effects.nvDays")} if first_own else None
    A["first_server_has"] = first_srv
    last_not = None
    for x in gp:
        if (x.get("x") or {}).get("has") is False:
            last_not = x["x"]
    A["last_server_not"] = last_not
    edit_rec = next((RL[x["r"]] for x in gp if x.get("r") in RL), None)
    A["first_rec_after_edit"] = {"worldAge": edit_rec.get("worldAge"), "nvDays": edit_rec.get("effects.nvDays"),
                                 "retEma": edit_rec.get("acute.retEma"), "vitA_g": edit_rec.get("nutrients.vitA.g")} if edit_rec else None
    if edit_rec and to_num(edit_rec.get("effects.nvDays")) is not None:
        A["pred_grant_game_h_after_first_rec"] = (14 - to_num(edit_rec["effects.nvDays"])) * 24
    A["watch_result"] = Ap.get("watch_result")
    A["es"] = {k: Ap.get(k) for k in ("es0", "es1", "es2", "es3", "es4")}
    A["remove_polls"] = Ap.get("remove_polls")
    A["withdraw_client"] = Ap.get("withdraw_client")
    fp = Ap.get("foreign_polls") or []
    A["foreign"] = {"n": len(fp), "server_has_all": all((x.get("x") or {}).get("has") for x in fp) if fp else None,
                    "own_nv": [RL.get(x["r"], {}).get("effects.own.nv") for x in fp]}
    cp = Ap.get("carotene_polls") or []
    A["carotene_nvDays"] = [(RL.get(x["r"], {}).get("worldAge"), RL.get(x["r"], {}).get("effects.nvDays")) for x in cp]
    # ---- B
    Bp = P.get("B") or {}
    sm["B"] = {k: Bp.get(k) for k in ("base", "sight_ss", "sight_sev05", "sight_g3", "added", "sev05_removed",
                                         "sev1_added", "g3_removed", "watch_result", "es")}
    # ---- F cold
    F = sm["F"] = {}
    Fp = P.get("F") or {}
    CH = rows_by(out["chains"])
    for w_ in ("F0", "F1"):
        rows = Fp.get(w_) or []
        pts = [(CH[r["c"]]["wall"], to_num(CH[r["c"]]["value"])) for r in rows if r["c"] in CH and to_num(CH[r["c"]]["value"]) is not None]
        ds = [to_num(CH[r["d"]]["value"]) for r in rows if r["d"] in CH]
        F[w_] = {"n": len(pts), "first": pts[0][1] if pts else None, "last": pts[-1][1] if pts else None,
                 "max": max((p[1] for p in pts), default=None), "delta_max": max((d for d in ds if d is not None), default=None),
                 "coldMul": [RL.get(r["r"], {}).get("effects.coldMul") for r in rows][:3],
                 "per_wall_s": slope_xy(pts)}
    F["coldWrites"] = (Fp.get("coldWrites0"), Fp.get("coldWrites1"))
    # ---- G thermal
    G = sm["G"] = {}
    Gp = P.get("G") or {}
    TC = rows_by(out["temps"])
    for w_ in ("G0", "G1", "G2", "G3", "G4"):
        rows = Gp.get(w_) or []
        cs = [(TC[r["t"]]["wall"], to_num(TC[r["t"]]["core"]), to_num(TC[r["t"]]["setPoint"]), to_num(TC[r["t"]]["temperature"]))
              for r in rows if r["t"] in TC and to_num(TC[r["t"]]["core"]) is not None]
        tt = [RL.get(r["r"], {}).get("effects.tempTarget") for r in rows if r.get("r")]
        G[w_] = {"n": len(cs), "core_first": cs[0][1] if cs else None, "core_last": cs[-1][1] if cs else None,
                 "core_min": min((c[1] for c in cs), default=None), "core_max": max((c[1] for c in cs), default=None),
                 "setPoint": sorted({c[2] for c in cs if c[2] is not None}),
                 "offset_last5_mean": (sum(c[1] - c[2] for c in cs[-5:]) / len(cs[-5:])) if len(cs) >= 5 and all(c[2] is not None for c in cs[-5:]) else None,
                 "tempTarget": tt[:3]}
    G["watches"] = {w["tag"]: {f: (w["result"].get("fields") or {}).get(f) for f in ("core", "temperature")}
                    for w in out["watches"] if w["tag"] in ("G1", "G3")}
    # ---- K panic hold
    K = sm["K"] = {}
    for w in out["watches"]:
        if w["tag"] in ("K1", "K2"):
            K[w["tag"]] = {"panic": (w["result"].get("fields") or {}).get("panic"),
                           "unhappiness": (w["result"].get("fields") or {}).get("unhappiness"),
                           "raw_panic": [r.get("panic") for r in w["result"].get("raw", [])],
                           "samples": w["result"].get("samples")}
    K["targets"] = [(r["tag"], r.get("effects.panicTarget")) for r in out["recs"] if r.get("phase") == "K"][:40]
    # ---- L thirst
    L = sm["L"] = {}
    for side in ("server", "client"):
        vals = [to_num((r.get("stats") or {}).get("Thirst")) for r in out["stats_all"] if r.get("phase") == "L" and r["side"] == side]
        vals = [v for v in vals if v is not None]
        L[side] = {"n": len(vals), "max": max(vals, default=None), "over_cap": sum(1 for v in vals if v > f32(THIRST_CAP) + 1e-9)}
    L["thirstTarget"] = [r.get("fluids.thirstTarget") for r in out["recs"] if r.get("phase") == "L"]
    L["watch_dmg"] = next(((w["result"].get("dmg") or {}) for w in out["watches"] if w["tag"] == "L"), None)
    # ---- H toxicity
    H = sm["H"] = {}
    Hp = P.get("H") or {}
    H["health"] = health_rate(Hp.get("polls") or [])
    H["health_off"] = health_rate(Hp.get("polls1") or [])
    H["pred_per_game_h"] = -R.drainRate(7) * 60
    H["recs"] = [(RL[p["r"]].get("worldAge"), RL[p["r"]].get("effects.drain"), RL[p["r"]].get("effects.lethal"),
                  RL[p["r"]].get("effects.foodSickTarget"), RL[p["r"]].get("nutrients.iron.x")) for p in (Hp.get("polls") or []) if p.get("r") in RL][:8]
    H["watch"] = next(({f: (w["result"].get("fields") or {}).get(f) for f in ("food_sickness", "poison", "sickness")}
                       | {"dmg": w["result"].get("dmg")} for w in out["watches"] if w["tag"] == "H"), None)
    # ---- C healing
    C = sm["C"] = {}
    Cp = P.get("C") or {}
    C["pe_at_close"], C["fallback"] = Cp.get("pe_at_close"), Cp.get("fallback")
    C["C1"] = window_rate(Cp.get("C1") or [], "scratchTime")
    C["C2"] = window_rate(Cp.get("C2") or [], "scratchTime")
    try:
        C["ratio"] = C["C1"]["per_game_h"] / C["C2"]["per_game_h"]
    except (TypeError, ZeroDivisionError):
        C["ratio"] = None
    # ---- D bleeding
    D = sm["D"] = {}
    for k_ in ("D0", "D1"):
        D[k_] = window_rate((P.get(k_) or {}).get("polls") or [], "bleedingTime")
    try:
        D["ratio"] = D["D1"]["per_game_h"] / D["D0"]["per_game_h"]
    except (TypeError, ZeroDivisionError):
        D["ratio"] = None
    # ---- I scurvy
    I = sm["I"] = {}
    Ip = P.get("I") or {}
    I["health"] = health_rate(Ip.get("polls") or [])
    I["pred_per_game_h"] = -R.drainRate(2) * 60
    I["mirror"] = next((m for m in out["mirror_checks"] if m["tag"] == "I_mirror"), None)
    # ---- BR bruise
    BR = sm["BR"] = {}
    Bp2 = P.get("BR") or {}
    b0 = to_num((Bp2.get("es0") or {}).get("bruises"))
    b1 = to_num((Bp2.get("es1") or {}).get("bruises"))
    m0 = to_num((Bp2.get("es0") or {}).get("minutes"))
    m1 = to_num((Bp2.get("es1") or {}).get("minutes"))
    endr = RL.get(Bp2.get("end") or "") or {}
    BR["bruises"] = (b1 - b0) if (b0 is not None and b1 is not None) else None
    BR["effects_minutes"] = (m1 - m0) if (m0 is not None and m1 is not None) else None
    a0, a1 = to_num(Bp2.get("age0")), to_num(endr.get("worldAge"))
    BR["game_h"] = (a1 - a0) if (a0 is not None and a1 is not None) else None
    BR["expected"] = (BR["game_h"] * 60 / 2880) if BR["game_h"] else None
    BR["p_ge1_per_day"] = 1 - math.exp(-1440 / 2880)
    # ---- E infection
    E_ = sm["E"] = {}
    Ep = P.get("E") or {}
    E_["pe_read"], E_["fallback"] = Ep.get("pe_read"), Ep.get("fallback")
    E_["E1"] = window_rate(Ep.get("E1") or [], "woundInfectionLevel")
    E_["E2"] = window_rate(Ep.get("E2") or [], "woundInfectionLevel")
    try:
        E_["ratio"] = E_["E1"]["per_game_h"] / E_["E2"]["per_game_h"]
    except (TypeError, ZeroDivisionError):
        E_["ratio"] = None
    # ---- the caps over the whole session
    caps = {}
    for side in ("server", "client"):
        hs = [to_num((r.get("stats") or {}).get("Hunger")) for r in out["stats_all"] if r["side"] == side]
        ts = [to_num((r.get("stats") or {}).get("Thirst")) for r in out["stats_all"] if r["side"] == side]
        hs, ts = [v for v in hs if v is not None], [v for v in ts if v is not None]
        caps[side] = {"n": len(hs), "hunger_max": max(hs, default=None), "thirst_max": max(ts, default=None)}
    sm["caps"] = caps


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
    KK_ = Kernel()
    R = KK_.R
    acute = KK_.to_py(KK_.K.acute.new(3.1))
    fluids = KK_.to_py(KK_.K.fluids.new(60, 1, 40))
    nut = {k: KK_.to_py(KK_.K.nutrients.newKey()) for k in ORDER}
    nut.update({"epoch": 3, "allReplete": True, "anaemia": False, "vitDClinical": False, "ironGrade": 1})
    rec_ = {"acute": acute, "fluids": fluids, "nutrients": nut, "body": {"band1Day": 0, "band2Day": 0, "fm": 22.4, "lm": 57.6, "sex": 2},
            "effects": KK_.to_py(KK_.K.effects.new())}

    def comp(**kw):
        return KK_.to_py(R.compose(KK_.table(rec_), kw.get("sev", 1.0), True, False))
    print("replete:", {k: comp()[k] for k in ("healMul", "bleedMul", "infectMul", "coldMul", "tempOffset", "bruise", "drainReplay")})
    rec_["effects"]["pe"] = 3
    rec_["nutrients"]["vitC"]["g"] = 3
    print("pe3 vitC3 healMul:", comp()["healMul"])
    rec_["effects"]["pe"] = 4
    rec_["nutrients"]["vitC"]["g"] = 1
    print("pe4 infectMul:", comp()["infectMul"])
    rec_["effects"]["pe"] = 1
    rec_["nutrients"]["vitC"]["g"] = 4
    print("vitC4:", {k: comp()[k] for k in ("healMul", "bleedMul", "bruise", "coldMul")})
    rec_["nutrients"]["vitC"]["ah"] = 800
    e = comp()
    print("scurvy drain:", e["drainReplay"], e["lethalReplay"])
    rec_["nutrients"]["vitC"]["g"] = 1
    rec_["nutrients"]["vitC"]["ah"] = 0
    rec_["nutrients"]["iron"]["x"] = 3
    e = comp()
    print("iron x3:", e["foodSickTarget"], e["drainReplay"], e["lethalReplay"])
    rec_["nutrients"]["iron"]["x"] = 0
    rec_["nutrients"]["iron"]["g"] = 4
    print("iron g4 tempOffset:", comp()["tempOffset"])
    rec_["nutrients"]["iron"]["g"] = 1
    rec_["acute"]["debtH"] = 10
    print("debt 10 coldMul:", comp()["coldMul"])
    rec_["acute"]["debtH"] = 0
    rec_["nutrients"]["vitA"]["g"] = 4
    print("vitA4 ss:", comp()["ssWant"], comp(sev=0.5)["ssWant"])
    rec_["acute"]["awakeH"] = 24
    rec_["acute"]["iuSleep"] = KK_.K.acute.iuSleep(KK_.table({"awakeH": 24, "debtH": 0}))
    print("awake 24 panic:", comp()["panicTarget"])
    print("peGrade(25.9, 7):", R.peGrade(25.9, 7), "peGrade(25.9, 11):", R.peGrade(25.9, 11))
    print("nv step:", R.nvStep(13.95, 1, 1, 1, 1, True, 1 / 1440), "vitA R:", R.vitAR(2), R.vitAR(1))
    print("thirst 7%:", R.thirst(7.0, 1.0, 140, True), "consts:", R.consts())


if SELFTEST:
    selftest()
    sys.exit(0)

prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x161b-dry-run", None) if DRY_RUN else new_run_dir("x161b")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}
cur_sub = {"n": 0}
state = {"parts": {}}
try:
    KK = Kernel()
except Exception as e:                         # noqa: BLE001 - the run falls back to the hand constants
    KK = None
    print(f"kernel not loaded at start: {type(e).__name__}: {e}")

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
    "kernel_at_start": KK is not None,
    "constants": {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, tuple))
                  and k not in ("REPO", "LUA_DIR", "MOD_LUA", "SHARED", "REPLAY_LUA", "PHASES")},
    "deviations": [
        "Arms C and E: pe rides the day close's starvedDays (Nutrients' refeedDay recomputes acute.bmi from the mass "
        "before the effects close reads it); the bmi edit is made and its overwrite read; the fallback edit "
        "(effects.pe with effects.key.ep -1) only if the close misses; the C2 and E2 controls reset pe that way.",
        "Arm E's pe 4 comes from the closes the bruise sleep crosses (starvedDays 10 -> 11).",
        "Arm D's bruise count runs inside a held sleep (two game days in about 100 s); the bleed rate's control D0 "
        "at bleedMul 1 is read in the same session.",
        "The healing, bleeding and infection windows are 30-40 s (about 50-64 game minutes), not 5 game minutes.",
        "Arm H writes FOOD_SICKNESS 80 first so the 85 hold is reachable in the window.",
        "Arm L reads THIRST through stats.all on both sides (no THIRST field in TKX_StatWatch; no ThirstWatch in "
        "the profile); the StatWatch counts the THIRST damage tag.",
        "Arm F wets the subject (WETNESS 100) and cools the climate (-10); a coldMul 1 control window first.",
        "Arm G adds a squat set with the target and one without it.",
        "Iron's clinical grade through nutrients.iron.H (p2 = H / H0 recomputed each minute); vitA and vitC grades "
        "through p; NV's grade-1 vitamin A and zinc are the subject's own, read not edited.",
        "The NV latency is bounded by the server poll interval (the mod's push wall is not stamped).",
        "Cost first, as x161f.",
        "Moodle levels are inferred from the stat copies against #2369.",
        "The mod at HEAD runs underneath every arm; mod/ untouched.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["record edits (starvedDays, bmi, debtH, retEma, nvDays, vitA/vitC p, iron H/ax/axr, "
                                        "vitC ah, awakeH, water, effects.pe/key.ep)", "traits added and removed",
                                        "Severity and DeficienciesCanKill flipped and restored", "climate set and cleared",
                                        "WETNESS and FOOD_SICKNESS written", "wounds, bleeding and infection written and cleared",
                                        "a held sleep of about two game days"]},
    "steps": [], "notes": [], "summaries": {}, "stats_all": [], "stats_get": [], "health_reads": [],
    "regen_reads": [], "temps": [], "chains": [], "part_reads": [], "part_writes": [],
    "stat_writes": [], "watches": [], "recs": [], "full": [], "edits": [], "sandbox": [],
    "mirror_checks": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "mod_error_checks": [],
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

print(json.dumps({"summaries": {k: out["summaries"].get(k) for k in ("J", "A", "C", "D", "E", "H", "I", "BR", "L")},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error")}, indent=1, default=str)[:12000])
