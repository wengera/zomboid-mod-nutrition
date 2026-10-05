"""x151-records -- Plan 4 Task 17, acceptance 2: the records, caffeine, alcohol, glycogen, sleep debt and
refeeding live, the second boot of the Plan 4 build (HEAD carries the build at cac63cc; mod/ clean). ONE
boot, profile `x15-records` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror OnsetSpeed 30
DeficienciesCanKill true ExcessEffectsOn true + TKX_ThirstWatch + TKX_SleepWatch + TKX_BoozeWatch;
`Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game minute 0.625 s; `[server]`
SleepAllowed and SleepNeeded true). The run id prefix is `x151r`. Copied from `x151_thirst.py` (provenance,
wall-bracketed steps, the record reads, the mirror check, RCON spawns resolved on the client, the persist /
step / phase shape, the cost block) and `x151_sleep_gate.py` (the beer, the server fluid.fill twin, the held
sleep, the ini read).

WHERE STATE IS READ. The record is the server's global modData `NutritionRevamp.players`, keyed by
username, read with `witness.moddata global:NutritionRevamp.players` and dotted keys on one server tick:
`rec()` reads `admin.fluids`, `admin.acute`, `admin.stomach.buffer`, `admin.pool` (Plan 2's cumulative
absorbed vector, which the stomach step still writes) as whole tables plus the body and nutrient scalars;
`nut()` reads the 27 per-nutrient tables `admin.nutrients.<key>` (p, p2, g, gl, x, e24, S, H ...) with the
epoch, allReplete and lastAgeH and the pool, in two calls. Record edits go through `globalmoddata.setpath
NutritionRevamp.players admin.<path> <value>` (Task 16's setter). The client mirror is a request-time
snapshot (ruling T14-1): a client read is preceded by a fresh request and its answer.

SCHEDULE (t = wall seconds from first sight; the world age starts near 3.2 h and runs 1 h per 37.5 s):
  S0  first sight: rec, nut, options, sentinels, the server ini, stats pair, a mirror check.
  C   coffee: RCON `additem Base.WaterBottle` (both sides hold a prefilled bottle, so the client's drink
      action is valid); the server `fluid.fill admin Base.WaterBottle Coffee 0.25` turns the SERVER copy
      into 0.25 L Coffee (107 mg caffeine at the seed's 428 mg/L); the client `drink.action
      Base.WaterBottle 1`, which the server runs on its own copy (x151w B1, x151t C); rec every ~2 s, 40 s.
  D   beer: RCON `additem Base.BeerCan` (prefilled Beer 0.3 L, x151s); the client `drink.action
      Base.BeerCan 1`; rec and the server `stats.all` (INTOXICATION) every ~1.5 s for 45 s.
  B1  bread: `foodtimer.set admin 0`; RCON `additem Base.Bread`; `eat.action Base.Bread 1`; rec every
      ~3 s until the intake `eats` counter moves, then 60 s (the per-mg iron landing, bread window).
  E   glycogen: rec; `exercise.do squats 20` (20 game minutes = 12.5 s wall); quick reads (acute.glyc, g,
      bg, body.met, energyState, lastAgeH) as fast as the bus answers for 22 s; rec.
  B2  steak: RCON `additem Base.Steak`; the server `item.set admin Base.Steak cooked true` and the client
      `item.state Base.Steak cooked` (raw steak is DangerousUncooked); foodtimer 0; `eat.action Base.Steak
      1`; rec every ~3 s until eats moves, then 60 s (the steak window).
  AL  lettuce: foodtimer 0; RCON `additem Base.Lettuce`; `eat.action Base.Lettuce 1`; rec and nut every
      ~5 s until eats moves, then 60 s (vitamin C's landing on p).
  H   the excess dial: `sandbox.var NR.ExcessEffectsOn false` (the option read polled to false); nut;
      `admin.nutrients.vitC.e24` set to 2500 (above the 2000 mg UL); vitC read ~1 s for 6 s; `sandbox.var
      NR.ExcessEffectsOn true`; vitC read ~1 s until x == 1 (cap 10 s); e24 set back to 0; vitC read 5 s.
  I   cost: three `bench.global NutritionRevamp.bench_fast 100000`, two `tick.rate 10` (x151t H's shape).
  W1  rest: rec every ~8 s and nut every ~30 s until the world age is 1.0 h short of the next day boundary
      (24 h x (body.dayIndex + 1)); fluids.water set to 0 at its start (keeps the view under the 0.1
      auto-drink gate and the dehydration term out of iu and dmod).
  G   refeeding: `admin.acute.starvedDays` 11 and `admin.body.inDay` 0 by record edits (the closing day is
      then a low day: the closed kcal is what absorbs in the last game hour); rec every ~3 s until
      body.dayIndex advances (cap 120 s); then two recs.
  W2  rest until the world age reaches the boundary + 2.0 h; fluids.water 0; rec and nut (the "before").
  F   sleep: `player.sleep.hold admin 120`; every ~3.5 s rec, the server stats.get (asleep), nut, and
      fluids.water reset to 0 (the ~20x clock of a held sleep, ruling T5-1, would otherwise run the pool
      to a lethal deficit in two real minutes); cancel; rec at once and 10 s later.
  P   post: rec every ~10 s and nut every ~30 s until t = 1290 s (21.5 min of nutrient polls).
  Z   a mirror check, the error and counter reads.
  Between the arms, every wait loop also takes a nut read when ~30 s have passed (4 s inside the hold).

PREDICTIONS (written before the run; the subject's sex, masses and slowMet are read live, and every
mass-dependent number is recomputed in `grade_all` through the mod's own kernel run offline in lupa):
  A   vitamin C takes NO dial: its k = ln(1/0.15)/40 = 0.047428/d puts replete-to-clinical at 40 d, under
      K.nutrients.DIAL_SLOW_DAYS 90, so dialExp is 0 and kEff = k at any OnsetSpeed (Task 7's report: "vitC
      is still 0.15, since it takes no dial"). The amendments' crossings (grade 2 at 6.02 h, 3 at 13.5 h, 4 at
      32.0 h from k x 30) are therefore predicted NOT to occur: at zero intake vitC p after the session's
      ~92 game hours is exp(-0.047428 x 3.83) = 0.83, grade 1 throughout. The dialled records cross instead.
      The kernel's zero-intake times from a fresh record (female, 80 kg, dial 30; this driver's desk probe):
      folate g2 at 11.17 h, magnesium g2 21.95 h, vitD g2 27.73 h, iodine g2 28.55 h, vitK g2 33.00 h
      (undialled, k 0.259), magnesium g3 49.15 h, vitD g3 63.47 h, iodine g3 63.88 h, folate g3 72.0 h,
      vitK g3 73.87 h, fibre g2 84.0 h, magnesium g4 85.3 h -- shifted by the eaten foods, so the graded
      prediction is the kernel REPLAY from the first nut read with the live absorbed pool deltas (spread
      evenly over each interval's minutes, the adapter's factors() applied). nutrients.epoch increments
      exactly once per g or x change of any record (each increment attributed from the per-poll g and x);
      allReplete false from the first pool-kind crossing (folate). The Lettuce eat: vitC p follows the ZOH
      step p' = p e + (1 - e) (a/dtD)/R with R = 75 x 0.85 = 63.75 mg/d (female) or 90 x 0.85 = 76.5
      (male): about +0.0076 over the 10.2 mg absorbed (k x 10.2/63.75), less the decay.
  B   the per-mg absorbed iron landing, measured as the pool's absorbed iron over the iron that left the
      buffer in the same interval. The amendments predict Bread/Steak = exp(-0.0034 x 400) = 0.257 (a
      meal-level phytate factor). The kernel as wired applies K.stomach.ironFactor to EACH MINUTE's emptied
      vector (NR_Server_Kinetics: empty then absorb per minute), whose phytate is the minute's emptied
      fraction of the buffer (about 0.4 % at a ~2.9 h half-time: ~1.6 mg of the loaf's 400), so the factor
      is ~0.995 and the predicted landing is ~0.18 mg absorbed per mg emptied for BOTH foods: ratio ~0.99,
      the 0.257 falsified. The graded prediction is the kernel's per-interval 0.18 x ironFactor(f x buffer
      phytate, f x buffer vitC). iron.S rises by eta x absorbed (eta = 1 - 0.5 clamp(S/S0)) less the
      store-to-haemoglobin transfer (L[sex] per day once H < H0).
  C   buffer + pool caffeine = 107 mg after the drink (0.25 L x 428); acute.caf follows caf' = caf x
      2^(-dtH/thalf) + absorbed (thalf 5.0 h, or 9.7 h when acute.slowMet); its peak is below 107 (absorption
      over the stomach's 2 h half-time); the fitted half-life from consecutive reads with the absorbed
      increments removed equals thalf; cafEffect = caf/(3 w); body.dmod carries (1 - 0.1-scale x cafEffect x
      (1 - cafTol)) one minute late (the adapter's lag).
  D   buffer + pool ethanol = 11.85 g (0.3 L x 39.5 g/L); acute.alc follows alc' = max(0, alc + absorbed -
      0.015 x r x w x 10 x dtH), bac = alc/(10 r w), r = 0.68 male / 0.55 female; the Widmark ceiling
      11.85/(10 r w) (0.02693 % for a female 80 kg subject) is an upper bound the peak stays under;
      body.alcDay and acute.alcDayG = 11.85 at the minute after the last sip (the ingested producer, Plan 3's
      gate live); INTOXICATION on the server rises per sip as x151s measured (vanilla's write).
  E   glycogen falls only on minutes with body.met > 3: dGlyc = -51.5 x clamp((met - 3)/4.5, 0, 1.6) x dtH
      per minute; acute.g < 1 after; acute.bg 5.0 throughout (fed); body.energyState = clamp(1 + 0.5
      clamp(-eb24h/1500) + 0.5 fatDep + 0.3 (1 - g), 0.5, 2) with eb24h = ebDay + eb7[7] x clamp(1 -
      (ageH - lastCloseAgeH)/24) -- recomputed offline from the same read.
  F   with sleep allowed, acute.frozen false and awakeH = game hours since the record's first Nutrients
      minute (no sleep before the hold); S rises toward 1 on chi_w 18.2 h; acute.iu before the hold =
      K.acute.iu offline on the read's own acute and fluids (sleep term (awakeH - 16)/8 at ~22.8 h ~0.85, less
      the caffeine credit); the hold (~62 game h at the ~20x clock, x151s) closes 2-3 windows: the first
      window (opened at the record's creation) books only the asleep minutes before its close (debt += 7.5 -
      those), each later window books its asleep share (debt repaid by 0.5 x the excess over 7.5 h, floor 0);
      S decays on chi_s 4.2 h to its debt floor; the graded prediction is the kernel's sleepMinute replay over
      the hold with the per-poll asleep share -- both the all-asleep and the measured-share bounds reported.
  G   the close after the edits: kcalPerKg = inDayClosed/w < 5 -> a low day -> starvedDays 12 > 10 ->
      refeedRisk 2 (S0115), lowDay true, refeedDayN -1, refeedEvent false (no window: it opens only on a
      normal day after a low day while the risk is 2). The closes the hold runs through read their own
      inDayClosed: each replayed through K.acute.refeedDay / refeedEvent from the pre-close state (the roll
      unread: an event needs a window AND > 10 kcal/kg, not reachable on the empty stomach of a held sleep).
  H   with the dial off the vitC output x stays 0 while e24 = 2500 decays as e24 x exp(-dtD) (above the 2000
      UL); on -> x == 1 at the next minute and the epoch +1; e24 0 -> x 0 and the epoch +1.
  I   bench_fast within 25 % of #2888's 3.06-3.40 us; tick rate within 5 % of 10.00-10.11.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Arm A tests the kernel's prediction (no vitC crossing; the dialled records cross) rather than the
     amendments' vitC hours, which assumed the dial on vitC; both are written above and graded.
  2. Coffee is 0.25 L (107 mg, the brief's cup) in an RCON WaterBottle whose SERVER copy is refilled by the
     server fluid.fill twin and drunk by the client's drink.action: a Mugl spawned by RCON is empty on the
     client, so ISDrinkFluidAction:isValidStart refuses it there; the server `drink` command bypasses the
     mod's drink wrapper, so it cannot land caffeine.
  3. Beer is the prefilled 0.3 L BeerCan (11.85 g ethanol), not the brief's 0.5 L.
  4. The steak is set cooked on both copies before the eat (raw steak is DangerousUncooked).
  5. Squats run 20 game minutes, not 2 (2 game minutes are 1.25 s wall: one or two slow minutes).
  6. Arm G also sets body.inDay to 0 an hour before the close, so the closing day is a low day; with the
     fixture's eats the day's absorbed kcal is above 5 kcal/kg and the edit of starvedDays alone would be
     reset to 0 at the close (K.acute.refeedDay), testing nothing. The inDay edit also feeds Metabolism's
     closing-day reads (TAC's energy gate, the partition's day intake): a named world change.
  7. fluids.water is reset to 0 by record edit before the iu reads and throughout the held sleep.
  8. The sleep runs after the first day close and before the first sleep window's own close, ~22.8 game
     hours awake, not at 20.

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
import sys
import time
import shutil
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x15-records"
SESSION = ("Plan 4 acceptance 2, the records live: the nutrient records at OnsetSpeed 30 with the epoch (A), "
           "iron from bread and steak (B), coffee (C), beer (D), glycogen under squats (E), a held sleep (F), "
           "refeeding risk at a day close (G), the excess dial (H), cost (I): one boot of x15-records at DayLength 1")
ARTIFACT = "records.json"
USER = "admin"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
ORDER = ("vitC", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "vitA", "vitD",
         "vitE", "vitK", "pantothenate", "biotin", "iron", "zinc", "copper", "magnesium", "calcium", "iodine",
         "selenium", "fibre", "efa", "sodium", "potassium", "caffeine", "ethanol")
BODY_KEYS = ("fm", "lm", "sex", "met", "coldMult", "dmod", "rmod", "energyState", "ebDay", "eb7",
             "lastCloseAgeH", "fmRef", "dayIndex", "alcDay", "inDay", "inDayClosed", "tac", "pPrevKg")
NUT_SCALARS = ("epoch", "allReplete", "lastAgeH", "ironGrade", "lastDayIndex", "anaemia", "vitDClinical")
REC_KEYS = ([f"{USER}.fluids", f"{USER}.acute", f"{USER}.stomach.buffer", f"{USER}.pool", f"{USER}.stomachFill"]
            + [f"{USER}.body.{k}" for k in BODY_KEYS] + [f"{USER}.nutrients.{k}" for k in NUT_SCALARS])
NUT_CALL1 = ([f"{USER}.nutrients.{k}" for k in ORDER[:14]]
             + [f"{USER}.nutrients.epoch", f"{USER}.nutrients.lastAgeH", f"{USER}.nutrients.allReplete",
                f"{USER}.pool"])
NUT_CALL2 = ([f"{USER}.nutrients.{k}" for k in ORDER[14:]]
             + [f"{USER}.nutrients.epoch", f"{USER}.nutrients.lastAgeH"])
QUICK_KEYS = [f"{USER}.acute.glyc", f"{USER}.acute.g", f"{USER}.acute.bg", f"{USER}.body.met",
              f"{USER}.body.energyState", f"{USER}.nutrients.lastAgeH", f"{USER}.body.ebDay",
              f"{USER}.body.eb7", f"{USER}.body.lastCloseAgeH", f"{USER}.body.fm", f"{USER}.body.fmRef",
              f"{USER}.body.dmod", f"{USER}.body.rmod", f"{USER}.acute.caf", f"{USER}.acute.awakeH",
              f"{USER}.fluids.dehydPct", f"{USER}.body.tac", f"{USER}.body.lm", f"{USER}.body.sex"]
INTAKE = "NutritionRevamp.server.intake.stats"
COUNTERS = ("sips", "landed", "worldSips", "failures", "eats", "cancels")
OPT_KEYS = ("mode", "onsetSpeed", "deficienciesCanKill", "excessEffectsOn", "balanceBonus", "nutritionOn")
MIRROR_KEYS = ("nutrients_epoch", "fluids_dehydPct", "acute_caf", "acute_bac", "acute_g", "acute_bg",
               "acute_awakeH", "acute_debtH", "acute_iu", "acute_refeedRisk", "nut_vitC_g", "nut_folate_g",
               "nut_magnesium_g", "nut_vitD_g", "nut_iodine_g", "nut_vitK_g", "nut_iron_g", "lastSeen")
BOTTLE, BEER, BREAD, STEAK, LETTUCE = "Base.WaterBottle", "Base.BeerCan", "Base.Bread", "Base.Steak", "Base.Lettuce"
COFFEE_L = 0.25
C_POLL_S, C_POLL_EVERY = 40, 2.0
D_POLL_S, D_POLL_EVERY = 45, 1.5
EAT_WAIT_S, EAT_AFTER_S, EAT_POLL_EVERY = 60, 60, 3.0
EX_NAME, EX_MIN, EX_READ_S = "squats", 20, 22
H_E24, H_HOLD_S, H_ON_CAP_S, H_TAIL_S = 2500, 6, 10, 5
NUT_EVERY, NUT_EVERY_HOLD = 30.0, 4.0
W_REC_EVERY = 8.0
G_LEAD_H, G_CAP_S, G_POLL_EVERY = 1.0, 120, 3.0
F_AFTER_BOUNDARY_H = 2.0
HOLD_S, HOLD_POLL_EVERY = 120, 3.5
P_END_S, P_REC_EVERY = 1290, 10.0
TICK_S = 10
BENCH_N = 100000
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
MIRROR_WAIT_S = 6.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE|NutritionRevamp.*(fail|error)")
LUAERR_LIMIT = 40
INI_RX = re.compile(r"^(SleepAllowed|SleepNeeded)=(.*)$")


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
           "took": round(t_after - t_before, 3), "ack": val}
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
    a = ack(step(tag, side, "lua.global", name))
    if not a.get("resolved"):
        return None
    v = a.get("value")
    n = to_num(v)
    return n if n is not None else v


# ---------------------------------------------------------------- the record reads
def rec(tag):
    """One witness.moddata call: fluids, acute, the stomach buffer and the pool as tables, the body and
    nutrient scalars -- one server tick."""
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(REC_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "worldAge": a.get("worldAge"),
           "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"), "error": a.get("error")}
    for name, key in (("fluids", "fluids"), ("acute", "acute"), ("buffer", "stomach.buffer"), ("pool", "pool")):
        v = vals.get(f"{USER}.{key}")
        row[name] = v if isinstance(v, dict) else None
    row["stomachFill"] = to_num(vals.get(f"{USER}.stomachFill"))
    row["body"] = {k: vals.get(f"{USER}.body.{k}") for k in BODY_KEYS}
    row["nutrients"] = {k: vals.get(f"{USER}.nutrients.{k}") for k in NUT_SCALARS}
    out["records"].append(row)
    return row


def nut(tag):
    """The 27 per-nutrient tables with the epoch, lastAgeH and the pool, in two calls."""
    row = {"tag": tag, "wall": wall(), "keys": {}, "calls": []}
    for j, keys in enumerate((NUT_CALL1, NUT_CALL2)):
        r = step(f"{tag}_n{j}", server, "witness.moddata", f"global:{STORE} " + " ".join(keys))
        a = ack(r)
        vals = a.get("values") if isinstance(a.get("values"), dict) else {}
        row["calls"].append({"wall": r["wall_before"], "worldAge": a.get("worldAge"),
                             "epoch": vals.get(f"{USER}.nutrients.epoch"),
                             "lastAgeH": vals.get(f"{USER}.nutrients.lastAgeH"),
                             "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"), "error": a.get("error")})
        for k in ORDER:
            v = vals.get(f"{USER}.nutrients.{k}")
            if isinstance(v, dict):
                row["keys"][k] = v
        if j == 0:
            row["allReplete"] = vals.get(f"{USER}.nutrients.allReplete")
            pv = vals.get(f"{USER}.pool")
            row["pool"] = pv if isinstance(pv, dict) else None
    out["nut"].append(row)
    state["last_nut"] = wall()
    return row


def quick(tag):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(QUICK_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge")}
    for k in QUICK_KEYS:
        v = vals.get(k)
        row[k[len(USER) + 1:]] = v if isinstance(v, dict) else to_num(v)
    out["quick"].append(row)
    return row


STAT_KEYS = ("thirst", "hunger", "moodles", "moving", "asleep", "worldAge", "mult", "endurance", "fatigue")


def stats_pair(tag):
    rc = step(f"{tag}_sc", client, "stats.get", "")
    rs = step(f"{tag}_ss", server, "stats.get", USER)
    c_, s_ = ack(rc), ack(rs)
    p = {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "client": {k: c_.get(k) for k in STAT_KEYS}, "server": {k: s_.get(k) for k in STAT_KEYS}}
    out["stats_pairs"].append(p)
    return p


def srv_stats_all(tag):
    r = step(tag, server, "stats.all", USER)
    a = ack(r)
    st = a.get("stats") if isinstance(a.get("stats"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"), "mult": a.get("mult"),
           "intox": st.get("Intoxication"), "fatigue": st.get("Fatigue"), "hunger": st.get("Hunger"),
           "thirst": st.get("Thirst"), "endurance": st.get("Endurance")}
    if not st:
        row["reply"] = r["ack"]
    out["stats_all"].append(row)
    return row


def srv_stats_get(tag):
    a = ack(step(tag, server, "stats.get", USER))
    row = {"tag": tag, "wall": wall(), "asleep": a.get("asleep"), "fatigue": a.get("fatigue"),
           "hunger": a.get("hunger"), "thirst": a.get("thirst"), "worldAge": a.get("worldAge"), "mult": a.get("mult")}
    out["sleep_reads"].append(row)
    return row


def counters(tag):
    return {c: gv(server, f"{INTAKE}.{c}", f"{tag}_cnt_{c}") for c in COUNTERS}


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
    waited = wall()
    keys = {k: gv(client, f"NutritionRevamp.client.mirror.{k}", f"{tag}_m_{k}") for k in MIRROR_KEYS}
    srv = rec(f"{tag}_srv")
    row = {"tag": tag, "request": req, "received_before": before, "received_after": after,
           "answered": (to_num(after) or 0) > (to_num(before) or 0), "wall_answered": waited,
           "client": keys, "server_record_tag": srv["tag"]}
    out["mirror_checks"].append(row)
    return row


def setpath(tag, field, value):
    a = ack(step(tag, server, "globalmoddata.setpath", f"{STORE} {USER}.{field} {value}"))
    row = {"tag": tag, "field": field, "value": value, "wall": wall(), "ack": a}
    out["edits"].append(row)
    return row


def svar(tag, key, value, optkey):
    a = ack(step(tag, server, "sandbox.var", f"NR.{key} {value}"))
    row = {"tag": tag, "key": key, "value": value, "wall": wall(), "ack": a, "reads": []}
    want = (value == "true")
    end = wall() + 5.0
    while wall() < end:
        o = gv(server, f"NutritionRevamp.server.options.{optkey}", f"{tag}_opt")
        row["reads"].append({"wall": wall(), "value": o})
        if o is want or str(o).lower() == value:
            break
        time.sleep(0.4)
    out["edits"].append(row)
    return row


def spawn(full_type, why):
    """RCON additem, then poll the CLIENT until the instance resolves there (x132d's route)."""
    ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", client, "witness.fields", f"item {USER}/{full_type} getID"))
        res = seen.get("resolved")
        fields = seen.get("fields") or {}
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res, "id": fields.get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    sid = ack(step(f"spawn_{why}_srv", server, "witness.chain",
                   f"{USER} getInventory.getFirstTypeRecurse({full_type}).getID"))
    row["server_id"] = sid.get("value")
    out["spawns"].append(row)
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    persist()
    return row


def litres(tag, side, full_type):
    hop = f"getInventory.getFirstTypeRecurse({full_type}).getFluidContainer.getAmount"
    a = ack(step(tag, side, "witness.chain", hop if side is client else f"{USER} {hop}"))
    return {"tag": tag, "ok": a.get("ok"), "value": to_num(a.get("value")), "raw": a.get("value"),
            "failedAt": a.get("failedAt")}


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


def read_ini():
    vals = {"path": None, "values": {}, "error": None}
    try:
        vals["path"] = os.path.relpath(server.ini, REPO)
        with open(server.ini, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = INI_RX.match(line.strip())
                if m:
                    vals["values"][m.group(1)] = m.group(2)
    except Exception as e:                     # noqa: BLE001
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def run_phase(name, fn):
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    persist()


def fnum(r, sub, key):
    t = (r or {}).get(sub) or {}
    return to_num(t.get(key))


def since_first():
    return wall() - (state.get("first_wall") or 0)


def maybe_nut(tag, every=NUT_EVERY):
    if wall() - state.get("last_nut", -1e9) >= every:
        return nut(tag)["tag"]
    return None


def idle_until(key, cond, cap_s, rec_every=W_REC_EVERY, nut_every=NUT_EVERY):
    """rec every rec_every s and nut every nut_every s until cond(rec) or the wall cap."""
    rows = []
    end = wall() + cap_s
    i = 0
    while wall() < end:
        t_s = wall()
        r = rec(f"{key}_r{i}")
        rows.append(r["tag"])
        maybe_nut(f"{key}_nut{i}", nut_every)
        i += 1
        persist()
        if cond(r):
            break
        rest = rec_every - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    return rows


def eat(key, full_type):
    X = {"polls": []}
    X["foodtimer"] = ack(step(f"{key}_foodtimer", server, "foodtimer.set", f"{USER} 0"))
    X["counters_before"] = counters(f"{key}_before")
    X["before"] = rec(f"{key}_before")["tag"]
    time.sleep(0.5)
    r = step(f"{key}_eat", client, "eat.action", f"{full_type} 1")
    X["eat_wall"] = r["wall_before"]
    X["eat"] = {k: ack(r).get(k) for k in ("queued", "spawned", "itemId", "validStart", "maxTime", "moodleFoodEaten")}
    if not ack(r):
        X["eat"]["reply"] = r["ack"]
    e0 = to_num(X["counters_before"].get("eats"))
    landed_at = None
    end = wall() + EAT_WAIT_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"{key}_p{i}")["tag"]}
        e = gv(server, f"{INTAKE}.eats", f"{key}_p{i}_eats")
        p["eats"] = e
        nt = maybe_nut(f"{key}_p{i}_nut")
        if nt:
            p["nut"] = nt
        X["polls"].append(p)
        i += 1
        persist()
        if landed_at is None and e0 is not None and to_num(e) is not None and to_num(e) > e0:
            landed_at = wall()
            end = landed_at + EAT_AFTER_S
        rest = EAT_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    X["landed_wall"] = landed_at
    X["counters_after"] = counters(f"{key}_after")
    X["after"] = rec(f"{key}_after")["tag"]
    return X


# ---------------------------------------------------------------- phases
def phase_S0():
    S0 = out["phases"]["S0"] = {}
    r = rec("S0_first")
    state["first_wall"] = r["wall"]
    S0["first"] = r["tag"]
    S0["nut"] = nut("S0_nut")["tag"]
    S0["ini"] = read_ini()
    S0["sentinels"] = {n: gv(server, n, f"s0_{n}") for n in ("TKX_ThirstWatch_Installed", "TKX_SleepWatch_Installed",
                                                               "TKX_BoozeWatch_Installed", "NR_IntakeDrink_Installed",
                                                               "NR_IntakeWorld_Installed")}
    S0["options"] = options("s0")
    S0["nutrients_server"] = {k: gv(server, f"NutritionRevamp.server.nutrients.{k}", f"s0_nut_{k}")
                              for k in ("lastError", "sleepDisabled")}
    S0["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"s0_ns_{k}")
                             for k in ("minutes", "errors", "players", "noBody", "healed", "days")}
    S0["counters"] = counters("s0")
    S0["stats"] = stats_pair("s0")
    S0["time"] = ack(step("s0_time", server, "time.snapshot", ""))
    S0["mirror"] = mirror_check("S0_mirror")
    persist()


def phase_C():
    C = out["phases"]["C"] = {"polls": []}
    C["spawn"] = spawn(BOTTLE, "C")
    C["client_litres_spawned"] = litres("C_cl_spawned", client, BOTTLE)
    C["fill"] = ack(step("C_fill", server, "fluid.fill", f"{USER} {BOTTLE} Coffee {COFFEE_L}"))
    C["server_litres_filled"] = litres("C_sl_filled", server, BOTTLE)
    C["counters_before"] = counters("C_before")
    C["before"] = rec("C_before")["tag"]
    r = step("C_drink", client, "drink.action", f"{BOTTLE} 1")
    C["drink_wall"] = r["wall_before"]
    C["drink"] = r["ack"]
    end = wall() + C_POLL_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"C_p{i}")["tag"]}
        if i % 5 == 0:
            p["server_litres"] = litres(f"C_p{i}_sl", server, BOTTLE)
            p["counters"] = counters(f"C_p{i}")
        nt = maybe_nut(f"C_p{i}_nut")
        if nt:
            p["nut"] = nt
        C["polls"].append(p)
        i += 1
        persist()
        rest = C_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    C["counters_after"] = counters("C_after")
    C["after"] = rec("C_after")["tag"]
    persist()


def phase_D():
    D = out["phases"]["D"] = {"polls": []}
    D["spawn"] = spawn(BEER, "D")
    D["server_litres"] = litres("D_sl", server, BEER)
    D["counters_before"] = counters("D_before")
    D["before"] = rec("D_before")["tag"]
    D["intox_before"] = srv_stats_all("D_sa_before")["tag"]
    r = step("D_drink", client, "drink.action", f"{BEER} 1")
    D["drink_wall"] = r["wall_before"]
    D["drink"] = r["ack"]
    end = wall() + D_POLL_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"D_p{i}")["tag"], "sa": srv_stats_all(f"D_p{i}_sa")["tag"]}
        if i % 6 == 0:
            p["server_litres"] = litres(f"D_p{i}_sl", server, BEER)
            p["counters"] = counters(f"D_p{i}")
        nt = maybe_nut(f"D_p{i}_nut")
        if nt:
            p["nut"] = nt
        D["polls"].append(p)
        i += 1
        persist()
        rest = D_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    D["counters_after"] = counters("D_after")
    D["after"] = rec("D_after")["tag"]
    persist()


def phase_B1():
    B = out["phases"]["B1"] = {}
    B["spawn"] = spawn(BREAD, "B1")
    B.update(eat("B1", BREAD))
    persist()


def phase_E():
    E = out["phases"]["E"] = {"quick": []}
    E["before"] = rec("E_before")["tag"]
    E["stats_before"] = stats_pair("E_before")
    r = step("E_ex", client, "exercise.do", f"{EX_NAME} {EX_MIN}")
    E["ex_wall"] = r["wall_before"]
    E["ex"] = r["ack"]
    end = wall() + EX_READ_S
    i = 0
    while wall() < end:
        E["quick"].append(quick(f"E_q{i}")["tag"])
        i += 1
    E["stats_after"] = stats_pair("E_after")
    E["after"] = rec("E_after")["tag"]
    E["nut"] = nut("E_nut")["tag"]
    persist()


def phase_B2():
    B = out["phases"]["B2"] = {}
    B["spawn"] = spawn(STEAK, "B2")
    B["cook_server"] = ack(step("B2_cook_srv", server, "item.set", f"{USER} {STEAK} cooked true"))
    cs = ack(step("B2_cook_cli", client, "item.state", f"{STEAK} cooked"))
    B["cook_client"] = {k: cs.get(k) for k in ("cooked", "id", "spawned", "calories")}
    B.update(eat("B2", STEAK))
    persist()


def phase_AL():
    A = out["phases"]["AL"] = {}
    A["spawn"] = spawn(LETTUCE, "AL")
    A["nut_before"] = nut("AL_nut_before")["tag"]
    A.update(eat("AL", LETTUCE))
    A["nut_after"] = nut("AL_nut_after")["tag"]
    persist()


def vitc_read(tag):
    r = step(tag, server, "witness.moddata",
             f"global:{STORE} {USER}.nutrients.vitC {USER}.nutrients.epoch {USER}.nutrients.lastAgeH")
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    v = vals.get(f"{USER}.nutrients.vitC")
    row = {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
           "vitC": v if isinstance(v, dict) else None, "epoch": vals.get(f"{USER}.nutrients.epoch"),
           "lastAgeH": vals.get(f"{USER}.nutrients.lastAgeH")}
    out["vitc_reads"].append(row)
    return row


def phase_H():
    H = out["phases"]["H"] = {"off_reads": [], "on_reads": [], "tail_reads": []}
    H["off"] = svar("H_off", "ExcessEffectsOn", "false", "excessEffectsOn")
    H["pre"] = vitc_read("H_pre")["tag"]
    H["edit"] = setpath("H_e24", "nutrients.vitC.e24", H_E24)
    end = wall() + H_HOLD_S
    i = 0
    while wall() < end:
        H["off_reads"].append(vitc_read(f"H_off{i}")["tag"])
        i += 1
        time.sleep(0.8)
    H["on"] = svar("H_on", "ExcessEffectsOn", "true", "excessEffectsOn")
    end = wall() + H_ON_CAP_S
    i = 0
    while wall() < end:
        v = vitc_read(f"H_on{i}")
        H["on_reads"].append(v["tag"])
        i += 1
        if v["vitC"] is not None and to_num(v["vitC"].get("x")) == 1:
            break
        time.sleep(0.8)
    H["clear"] = setpath("H_clear", "nutrients.vitC.e24", 0)
    end = wall() + H_TAIL_S
    i = 0
    while wall() < end:
        H["tail_reads"].append(vitc_read(f"H_tail{i}")["tag"])
        i += 1
        time.sleep(0.8)
    H["nut"] = nut("H_nut")["tag"]
    persist()


def phase_I():
    I = out["phases"]["I"] = {"bench": [], "tick": []}
    for i in range(3):
        I["bench"].append(ack(step(f"I_bench{i}", server, "bench.global",
                                   f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60)))
    I["tick"] = [tick_rate("Ia"), tick_rate("Ib")]
    persist()


def boundary(r):
    di = to_num((r.get("body") or {}).get("dayIndex"))
    return None if di is None else 24.0 * (di + 1)


def phase_W1():
    W = out["phases"]["W1"] = {}
    W["water"] = setpath("W1_water", "fluids.water", 0)
    r0 = rec("W1_start")
    W["start"] = r0["tag"]
    b = boundary(r0)
    W["boundary"] = b
    target = (b - G_LEAD_H) if b is not None else None
    W["target_age"] = target

    def cond(r):
        wa = to_num(r.get("worldAge"))
        return target is None or (wa is not None and wa >= target)
    W["rows"] = idle_until("W1", cond, 900)
    persist()


def phase_G():
    G = out["phases"]["G"] = {"polls": []}
    pre = rec("G_pre")
    G["pre"] = pre["tag"]
    di0 = to_num((pre.get("body") or {}).get("dayIndex"))
    G["dayIndex_pre"] = di0
    G["water"] = setpath("G_water", "fluids.water", 0)
    G["edit_starved"] = setpath("G_starved", "acute.starvedDays", 11)
    G["edit_inday"] = setpath("G_inday", "body.inDay", 0)
    G["post_edit"] = rec("G_post_edit")["tag"]

    def cond(r):
        di = to_num((r.get("body") or {}).get("dayIndex"))
        return di is not None and di0 is not None and di > di0
    G["polls"] = idle_until("G", cond, G_CAP_S, G_POLL_EVERY)
    G["closed"] = rec("G_closed")["tag"]
    time.sleep(3.0)
    G["closed2"] = rec("G_closed2")["tag"]
    G["nut"] = nut("G_nut")["tag"]
    persist()


def phase_W2():
    W = out["phases"]["W2"] = {}
    r0 = rec("W2_start")
    di = to_num((r0.get("body") or {}).get("dayIndex"))
    target = 24.0 * di + F_AFTER_BOUNDARY_H if di is not None else None
    W["target_age"] = target

    def cond(r):
        wa = to_num(r.get("worldAge"))
        return target is None or (wa is not None and wa >= target - 0.25)
    W["rows"] = idle_until("W2", cond, 300)
    W["water"] = setpath("W2_water", "fluids.water", 0)
    time.sleep(3.0)
    persist()


def phase_F():
    F = out["phases"]["F"] = {"polls": []}
    F["before"] = rec("F_before")["tag"]
    F["nut_before"] = nut("F_nut_before")["tag"]
    F["stats_before"] = stats_pair("F_before")
    F["sa_before"] = srv_stats_get("F_sg_before")["tag"]
    r = step("F_hold", server, "player.sleep.hold", f"{USER} {HOLD_S}")
    F["hold_wall"] = r["wall_before"]
    F["hold"] = r["ack"]
    end = F["hold_wall"] + HOLD_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"F_p{i}")["tag"], "sg": srv_stats_get(f"F_p{i}_sg")["tag"]}
        nt = maybe_nut(f"F_p{i}_nut", NUT_EVERY_HOLD)
        if nt:
            p["nut"] = nt
        p["water"] = setpath(f"F_p{i}_water", "fluids.water", 0)["wall"]
        F["polls"].append(p)
        i += 1
        persist()
        rest = HOLD_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    F["cancel"] = ack(step("F_cancel", server, "player.sleep.hold", f"{USER} 0"))
    F["after"] = rec("F_after")["tag"]
    F["sg_after"] = srv_stats_get("F_sg_after")["tag"]
    F["nut_after"] = nut("F_nut_after")["tag"]
    time.sleep(10.0)
    F["after2"] = rec("F_after2")["tag"]
    F["stats_after"] = stats_pair("F_after")
    persist()


def phase_P():
    P = out["phases"]["P"] = {}

    def cond(r):
        return since_first() >= P_END_S
    P["rows"] = idle_until("P", cond, 600, P_REC_EVERY)
    persist()


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["mirror"] = mirror_check("Z_mirror")
    Z["nut"] = nut("Z_nut")["tag"]
    Z["options"] = options("Z")
    Z["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                            for k in ("minutes", "errors", "players", "noBody", "healed", "days", "skippedDays")}
    Z["lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "Z_lastError")
    Z["intake_lastError"] = gv(server, "NutritionRevamp.server.intake.lastError", "Z_in_lastError")
    Z["counters"] = counters("Z")
    Z["stats"] = stats_pair("Z")


MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|nutrients: .* failed")


def mod_error(after):
    """A NutritionRevamp error in the server's error lines, a mod lastError or error count, or a parked
    client stops the arms; the evidence is what the run returns."""
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    le = gv(server, "NutritionRevamp.server.nutrients.lastError", f"chk_{after}_nle")
    ne = gv(server, "NutritionRevamp.server.nutrients.stats.errors", f"chk_{after}_nerr")
    ie = gv(server, "NutritionRevamp.server.intake.lastError", f"chk_{after}_ile")
    if le is not None or (to_num(ne) or 0) > 0:
        why.append({"nutrients_lastError": le, "nutrients_errors": ne})
    if ie is not None:
        why.append({"intake_lastError": ie})
    if clients and "lua_error" in getattr(clients[0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why})
    return why


def body():
    for name, fn in (("S0", phase_S0), ("C", phase_C), ("D", phase_D), ("B1", phase_B1), ("E", phase_E),
                     ("B2", phase_B2), ("AL", phase_AL), ("H", phase_H), ("I", phase_I), ("W1", phase_W1),
                     ("G", phase_G), ("W2", phase_W2), ("F", phase_F), ("P", phase_P), ("Z", phase_Z)):
        run_phase(name, fn)
        why = mod_error(name)
        if why:
            out["abort"] = {"after": name, "why": why}
            note(f"mod error after {name}: the arms stop here (a mod error is the primary reading)")
            persist()
            break


# ---------------------------------------------------------------- the kernel offline (lupa)
class Kernel:
    def __init__(self):
        import lupa.lua51 as lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        files = ([os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
                 + sorted(glob.glob(os.path.join(SHARED, "NR_Data*.lua"))))
        loader = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")
        for p in files:
            with open(p, encoding="utf-8") as fh:
                loader(fh.read(), "@" + os.path.basename(p))()
        self.NR = self.rt.globals().NutritionRevamp
        self.K = self.NR.kernel
        self.recs = self.NR.data.records

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.table(v)
            else:
                t[k] = v
        return t

    def plain(self, t):
        return {k: (self.plain(v) if self.rt.eval("type")(v) == "table" else v) for k, v in t.items()}


def numtab(d):
    """A record sub-table as read (strings) -> numbers and booleans."""
    outd = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            outd[k] = numtab(v)
            continue
        n = to_num(v)
        if n is not None:
            outd[k] = n
        elif isinstance(v, bool):
            outd[k] = v
        elif str(v).lower() in ("true", "false"):
            outd[k] = str(v).lower() == "true"
    return outd


def recs_by_tag():
    return {r["tag"]: r for r in out["records"]}


def nut_age(n):
    for c in n.get("calls") or []:
        a = to_num(c.get("lastAgeH"))
        if a is not None:
            return a
    return None


def grade_all():
    P, R, S = out["phases"], recs_by_tag(), out["summaries"]
    try:
        KK = Kernel()
        K = KK.K
        S["kernel_loaded"] = True
    except Exception as e:                     # noqa: BLE001
        KK = K = None
        S["kernel_loaded"] = f"{type(e).__name__}: {e}"
    first = R.get((P.get("S0") or {}).get("first")) or {}
    sex = int(fnum(first, "body", "sex") or 1)
    lm, fm = fnum(first, "body", "lm"), fnum(first, "body", "fm")
    w = (lm + fm) if lm is not None and fm is not None else None
    ac0 = numtab(first.get("acute"))
    S["subject"] = {"sex": sex, "lm": lm, "fm": fm, "w": w, "slowMet": ac0.get("slowMet"),
                    "first_worldAge": first.get("worldAge")}
    if K is None or w is None:
        return
    thalf = 9.7 if ac0.get("slowMet") else 5.0

    # A: the kernel replay of the records from the first nut read
    try:
        NUTS = [n for n in out["nut"] if len(n.get("keys") or {}) == len(ORDER) and nut_age(n) is not None]
        NUTS.sort(key=nut_age)
        rows = []
        if NUTS:
            n0 = NUTS[0]
            st = KK.table({"nv": 1, "epoch": to_num(n0["calls"][0].get("epoch")) or 0, "allReplete": True,
                           "ironGrade": 1, "anaemia": False, "vitDClinical": False})
            for k in ORDER:
                st[k] = KK.table(numtab(n0["keys"][k]))
            ctx = KK.table({"sex": sex, "w": w, "lm": lm, "eeMJ": K.energy.ree(lm) * 4.184 / 1000,
                            "pDay": 0.8 * w, "alcGkg": 0, "dial": to_num((out["phases"]["S0"].get("options") or {}).get("onsetSpeed")) or 1,
                            "excessOn": True, "riboGrade": 1, "rawEggDay": False, "e24Zn": 0})
            ctx.two = K.interact.two
            kmul = KK.rt.table()
            ctx.kMul = kmul
            prev_age, prev_pool = nut_age(n0), numtab(n0.get("pool"))
            prev_g = {k: to_num(n0["keys"][k].get("g")) for k in ORDER}
            obs_prev_g = dict(prev_g)
            obs_prev_x = {k: to_num(n0["keys"][k].get("x")) for k in ORDER}
            obs_prev_epoch = to_num(n0["calls"][0].get("epoch"))
            pred_cross = []
            # body scalars by age for pPrevKg and alcDay
            body_by_age = sorted(((fnum(r, "nutrients", "lastAgeH"), r) for r in out["records"]
                                  if fnum(r, "nutrients", "lastAgeH") is not None), key=lambda t: t[0])
            for n in NUTS[1:]:
                age = nut_age(n)
                pool = numtab(n.get("pool"))
                mins = int(round((age - prev_age) * 60))
                if mins <= 0:
                    continue
                d = {k: max(0.0, (pool.get(k, 0) - prev_pool.get(k, 0))) / mins for k in pool}
                br = None
                for a_, r_ in body_by_age:
                    if a_ <= age:
                        br = r_
                if br is not None:
                    ppk = fnum(br, "body", "pPrevKg")
                    if ppk is not None:
                        ctx.pDay = ppk * w
                    ad = fnum(br, "body", "alcDay")
                    if ad is not None:
                        ctx.alcGkg = ad / w
                        kmul.thiamine = K.interact.thiamineAlcoholK(1, ad / w)
                for m in range(mins):
                    ab = dict(d)
                    ab["iron"] = ab.get("iron", 0) * K.interact.calciumIron(ab.get("calcium", 0))
                    cafMg, cafCa = K.interact.caffeineLossMg(ab.get("caffeine", 0), lm)
                    alcMg = K.interact.alcoholLossMg(ab.get("ethanol", 0))
                    ab["magnesium"] = max(0.0, ab.get("magnesium", 0) - cafMg - alcMg)
                    ab["calcium"] = max(0.0, ab.get("calcium", 0) - cafCa)
                    pA = st.vitA.p
                    off = KK.recs.REC.vitA.two.caroteneOff if KK.recs.REC.vitA.two is not None else None
                    ab["vitA"] = ab.get("retinol", 0) + K.interact.CAROTENE_RAE * K.interact.caroteneOn(pA, off) * ab.get("carotene", 0)
                    ing = KK.table({"vitA": 0})
                    K.nutrients.minute(st, KK.recs, KK.table(ab), ing, ctx, 1)
                    for k in ORDER:
                        g = st[k].g
                        if g != prev_g[k]:
                            pred_cross.append({"key": k, "from": prev_g[k], "to": g, "ageH": prev_age + (m + 1) / 60.0,
                                               "p": st[k].p})
                            prev_g[k] = g
                obs = {k: {"p": to_num(n["keys"][k].get("p")), "g": to_num(n["keys"][k].get("g")),
                           "x": to_num(n["keys"][k].get("x"))} for k in ORDER}
                changes = [k for k in ORDER if obs[k]["g"] != obs_prev_g[k]] + \
                          [k + ".x" for k in ORDER if obs[k]["x"] != obs_prev_x[k]]
                ep = to_num(n["calls"][0].get("epoch"))
                ep2 = to_num(n["calls"][1].get("epoch")) if len(n["calls"]) > 1 else None
                rows.append({"tag": n["tag"], "ageH": age, "epoch": ep, "epoch_call2": ep2,
                             "d_epoch": None if ep is None or obs_prev_epoch is None else ep - obs_prev_epoch,
                             "changes": changes, "allReplete": n.get("allReplete"),
                             "vitC_obs": obs["vitC"]["p"], "vitC_pred": st.vitC.p,
                             "obs_g": {k: obs[k]["g"] for k in ORDER if obs[k]["g"] != 1},
                             "pred_g": {k: st[k].g for k in ORDER if st[k].g != 1},
                             "p_obs": {k: obs[k]["p"] for k in ("folate", "magnesium", "vitD", "iodine", "vitK", "fibre", "vitA", "vitB12", "thiamine")},
                             "p_pred": {k: st[k].p for k in ("folate", "magnesium", "vitD", "iodine", "vitK", "fibre", "vitA", "vitB12", "thiamine")}})
                # resync the replay to the observed state (each interval is predicted from the last read)
                for k in ORDER:
                    st[k] = KK.table(numtab(n["keys"][k]))
                prev_g = {k: obs[k]["g"] for k in ORDER}
                obs_prev_g = {k: obs[k]["g"] for k in ORDER}
                obs_prev_x = {k: obs[k]["x"] for k in ORDER}
                obs_prev_epoch = ep2 if ep2 is not None else ep
                prev_age, prev_pool = age, pool
            S["A"] = {"intervals": rows, "pred_crossings": pred_cross}
    except Exception as e:                     # noqa: BLE001
        S["A_error"] = f"{type(e).__name__}: {e}"
        S["A_tb"] = traceback.format_exc()[-2000:]

    # B: per-interval absorbed iron over emptied iron, with the kernel per-minute factor
    try:
        blk = {}
        for key in ("B1", "B2"):
            X = P.get(key) or {}
            tags = [p["rec"] for p in X.get("polls") or []]
            rows = []
            prev = None
            for t in tags:
                r = R.get(t)
                if not r or not r.get("buffer") or not r.get("pool"):
                    continue
                if prev is not None:
                    b0, b1 = numtab(prev["buffer"]), numtab(r["buffer"])
                    p0, p1 = numtab(prev["pool"]), numtab(r["pool"])
                    emptied = b0.get("iron", 0) - b1.get("iron", 0)
                    absorbed = p1.get("iron", 0) - p0.get("iron", 0)
                    a0, a1 = fnum(prev, "nutrients", "lastAgeH"), fnum(r, "nutrients", "lastAgeH")
                    kf = None
                    if a0 is not None and a1 is not None:
                        f1 = K.stomach.emptyFraction(K.stomach.HALF_TIME_H, K.stomach.compositionScale(KK.table(b0)), 1 / 60.0)
                        kf = 0.18 * K.stomach.ironFactor(f1 * b0.get("phytate", 0), f1 * b0.get("vitC", 0))
                    rows.append({"t0": prev["tag"], "t1": t, "age0": a0, "age1": a1, "emptiedIron": emptied,
                                 "absorbedIron": absorbed,
                                 "perMg": absorbed / emptied if emptied > 1e-9 else None, "kernelPerMg": kf,
                                 "bufferPhytate0": b0.get("phytate"), "bufferIron0": b0.get("iron"),
                                 "ironS0": None, "ironS1": None})
                prev = r
            blk[key] = rows
        S["B"] = blk
        S["B"]["meal_level_ratio_amendments"] = math.exp(-0.0034 * 400)
    except Exception as e:                     # noqa: BLE001
        S["B_error"] = f"{type(e).__name__}: {e}"

    # C and D: the caffeine and alcohol replays on the record reads in time order
    try:
        allr = sorted([r for r in out["records"] if r.get("acute") and r.get("pool")
                       and fnum(r, "nutrients", "lastAgeH") is not None], key=lambda r: fnum(r, "nutrients", "lastAgeH"))
        rr = KK.rt.eval("function(x) return x end")
        caf, alc = [], []
        r_w = (0.68, 0.55)[sex - 1]
        prev = None
        for r in allr:
            ac, po = numtab(r["acute"]), numtab(r["pool"])
            a = fnum(r, "nutrients", "lastAgeH")
            bu = numtab(r.get("buffer"))
            row_c = {"tag": r["tag"], "ageH": a, "caf": ac.get("caf"), "poolCaf": po.get("caffeine"),
                     "bufCaf": bu.get("caffeine"), "cafTol": ac.get("cafTol"), "dmod": fnum(r, "body", "dmod")}
            row_a = {"tag": r["tag"], "ageH": a, "alc": ac.get("alc"), "bac": ac.get("bac"), "alcPeak": ac.get("alcPeak"),
                     "poolEth": po.get("ethanol"), "bufEth": bu.get("ethanol"), "alcDay": fnum(r, "body", "alcDay"),
                     "alcDayG": ac.get("alcDayG")}
            if prev is not None:
                pa, pp = numtab(prev["acute"]), numtab(prev["pool"])
                dh = a - fnum(prev, "nutrients", "lastAgeH")
                if dh > 0 and pa.get("caf") is not None:
                    dose = po.get("caffeine", 0) - pp.get("caffeine", 0)
                    row_c["pred"] = pa["caf"] * 2 ** (-dh / thalf) + dose
                    rem = (ac.get("caf") or 0) - dose
                    if dose < 1e-9 and rem > 0 and pa["caf"] > 0 and rem < pa["caf"]:
                        row_c["thalf_fit"] = dh * math.log(2) / math.log(pa["caf"] / rem)
                if dh > 0 and pa.get("alc") is not None:
                    dose = po.get("ethanol", 0) - pp.get("ethanol", 0)
                    row_a["pred"] = max(0.0, pa["alc"] + dose - 0.015 * r_w * w * 10 * dh)
            row_c["cafEffect_kernel"] = K.acute.cafEffect(KK.table({"caf": ac.get("caf") or 0}), w)
            caf.append(row_c)
            alc.append(row_a)
            prev = r
        S["C"] = {"thalf": thalf, "series": caf, "total_expected": COFFEE_L * 428}
        S["D"] = {"r": r_w, "widmark_ceiling_pct": 0.3 * 39.5 / (10 * r_w * w), "series": alc,
                  "stats_all": [s for s in out["stats_all"]]}
        del rr
    except Exception as e:                     # noqa: BLE001
        S["CD_error"] = f"{type(e).__name__}: {e}"
        S["CD_tb"] = traceback.format_exc()[-2000:]

    # E: glycogen per quick read; energyState recomputed offline
    try:
        Q = [q for q in out["quick"]]
        rows = []
        prev = None
        for q in Q:
            row = {"tag": q["tag"], "ageH": q.get("nutrients.lastAgeH"), "met": q.get("body.met"),
                   "glyc": q.get("acute.glyc"), "g": q.get("acute.g"), "bg": q.get("acute.bg"),
                   "energyState": q.get("body.energyState")}
            eb7 = q.get("body.eb7")
            if isinstance(eb7, dict) and None not in (q.get("body.ebDay"), q.get("body.lastCloseAgeH"), q.get("body.fm"),
                                                      q.get("body.fmRef"), q.get("acute.g"), row["ageH"]):
                y = to_num(eb7.get("7"))
                eb24 = q["body.ebDay"] + (y or 0) * min(1, max(0, 1 - (row["ageH"] - q["body.lastCloseAgeH"]) / 24))
                fd = min(1, max(0, (q["body.fmRef"] - q["body.fm"]) / q["body.fmRef"])) if q["body.fmRef"] > 0 else 0
                row["energyState_kernel"] = K.energy.state(eb24, fd, q["acute.g"])
                row["glyc_term"] = 0.3 * (1 - q["acute.g"])
            if prev is not None and row["ageH"] is not None and prev["ageH"] is not None and row["glyc"] is not None:
                dh = row["ageH"] - prev["ageH"]
                if dh > 0 and row["met"] is not None:
                    row["dGlyc"] = row["glyc"] - prev["glyc"]
                    row["dGlyc_kernel_at_met"] = -51.5 * min(1.6, max(0.0, (row["met"] - 3) / 4.5)) * dh
            rows.append(row)
            prev = row
        S["E"] = {"series": rows}
    except Exception as e:                     # noqa: BLE001
        S["E_error"] = f"{type(e).__name__}: {e}"

    # F: iu offline on each record read; the sleep replay over the hold
    try:
        iu_rows = []
        for r in sorted([r for r in out["records"] if r.get("acute") and r.get("fluids")], key=lambda r: r["wall"]):
            ac, fl = numtab(r["acute"]), numtab(r["fluids"])
            t = KK.table(ac)
            ig = fnum(r, "nutrients", "ironGrade") or 1
            iu_k = K.acute.iu(t, fl.get("dehydPct", 0), int(ig))
            iu_rows.append({"tag": r["tag"], "ageH": fnum(r, "nutrients", "lastAgeH"), "iu": ac.get("iu"),
                            "iu_kernel": iu_k, "awakeH": ac.get("awakeH"), "debtH": ac.get("debtH"),
                            "S": ac.get("S"), "frozen": ac.get("frozen"), "sleptH": ac.get("sleptH"),
                            "winStartH": ac.get("winStartH"), "winSleptH": ac.get("winSleptH"),
                            "iuSleep": K.acute.iuSleep(KK.table(ac))})
        S["F_iu"] = iu_rows
        Fp = P.get("F") or {}
        before = R.get(Fp.get("before"))
        after = R.get(Fp.get("after"))
        if before and after:
            reads = [x for x in out["sleep_reads"] if x["tag"].startswith("F_p")]
            share = (sum(1 for x in reads if str(x.get("asleep")).lower() == "true") / len(reads)) if reads else None
            a_b, a_a = fnum(before, "nutrients", "lastAgeH"), fnum(after, "nutrients", "lastAgeH")
            preds = {}
            for label, sh in (("all_asleep", 1.0), ("measured_share", share)):
                if sh is None:
                    continue
                t = KK.table(numtab(before["acute"]))
                mins = int(round((a_a - a_b) * 60))
                acc = 0.0
                for m in range(mins):
                    acc += sh
                    asleep = acc >= 1.0
                    if asleep:
                        acc -= 1.0
                    age = a_b + (m + 1) / 60.0
                    K.acute.sleepMinute(t, asleep, (age % 24), 1, age, 1 / 60.0, False)
                preds[label] = {"debtH": t.debtH, "S": t.S, "awakeH": t.awakeH, "sleptH": t.sleptH,
                                "winStartH": t.winStartH, "winSleptH": t.winSleptH, "share": sh}
            S["F"] = {"ageH_before": a_b, "ageH_after": a_a, "asleep_share_reads": share, "n_reads": len(reads),
                      "pred": preds, "after": {k: numtab(after["acute"]).get(k) for k in
                                               ("debtH", "S", "awakeH", "sleptH", "winStartH", "winSleptH", "frozen", "iu")}}
    except Exception as e:                     # noqa: BLE001
        S["F_error"] = f"{type(e).__name__}: {e}"
        S["F_tb"] = traceback.format_exc()[-2000:]

    # G: each observed day close replayed through refeedDay / refeedEvent from the read before it
    try:
        allr = sorted([r for r in out["records"] if r.get("acute") and fnum(r, "body", "dayIndex") is not None],
                      key=lambda r: r["wall"])
        closes = []
        for a_, b_ in zip(allr, allr[1:]):
            d0, d1 = fnum(a_, "body", "dayIndex"), fnum(b_, "body", "dayIndex")
            if d1 > d0:
                pa, pb = numtab(a_["acute"]), numtab(b_["acute"])
                kc = fnum(b_, "body", "inDayClosed")
                wb = (fnum(b_, "body", "fm") or 0) + (fnum(b_, "body", "lm") or 0)
                t = KK.table(pa)
                if kc is not None and wb > 0 and d1 - d0 == 1:
                    K.acute.refeedDay(t, kc / wb, wb, fnum(b_, "nutrients", "lastAgeH") or 0, False, False, False)
                    K.acute.refeedEvent(t, kc / wb, 0.99)
                closes.append({"before": a_["tag"], "after": b_["tag"], "dayIndex": [d0, d1], "inDayClosed": kc, "w": wb,
                               "kcalPerKg": (kc / wb) if kc is not None and wb > 0 else None,
                               "obs": {k: pb.get(k) for k in ("starvedDays", "refeedRisk", "lowDay", "refeedDayN", "refeedEvent", "bmi", "alc7", "alcDayG")},
                               "pre": {k: pa.get(k) for k in ("starvedDays", "refeedRisk", "lowDay", "refeedDayN", "refeedEvent", "bmi")},
                               "pred_noEvent": {k: t[k] for k in ("starvedDays", "refeedRisk", "lowDay", "refeedDayN", "bmi")}})
        S["G"] = {"closes": closes}
    except Exception as e:                     # noqa: BLE001
        S["G_error"] = f"{type(e).__name__}: {e}"

    # H
    H = P.get("H") or {}
    vr = {v["tag"]: v for v in out["vitc_reads"]}
    S["H"] = {"reads": [{"tag": t, "wall": vr[t]["wall"], "lastAgeH": vr[t]["lastAgeH"], "epoch": vr[t]["epoch"],
                         "x": (vr[t]["vitC"] or {}).get("x"), "e24": (vr[t]["vitC"] or {}).get("e24")}
                        for t in [H.get("pre")] + (H.get("off_reads") or []) + (H.get("on_reads") or []) + (H.get("tail_reads") or [])
                        if t in vr]}
    # I
    I = P.get("I") or {}
    S["I"] = {"usPerCall": [to_num(b.get("usPerCall")) for b in I.get("bench") or []],
              "ticksPerSecond": [t.get("ticksPerSecond") for t in (I.get("tick") or [])]}
    for ph in ("A", "B", "C", "D", "E", "F", "G", "H", "I"):
        grade(ph, "see the PREDICTIONS block of the driver docstring", {"summary_key": ph}, "see_raw",
              "see the PREDICTIONS block")


prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x151r-dry-run", None) if DRY_RUN else new_run_dir("x151r")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
state = {}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "ini_requested": dict(prof.ini or {}),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {k: v for k, v in globals().items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
                  and isinstance(v, (int, float, str)) and k not in ("REPO", "SHARED", "LUA_DIR")},
    "deviations": [
        "Arm A tests the kernel prediction (vitamin C takes no dial, so no vitC crossing; the dialled records "
        "cross) beside the amendments' vitC hours, which assumed the dial on vitC.",
        "Coffee is 0.25 L (107 mg) in an RCON WaterBottle whose server copy is refilled with Coffee by the server "
        "fluid.fill twin and drunk by the client's drink.action (an RCON Mugl is empty on the client; the server "
        "drink command bypasses the mod's drink wrapper).",
        "Beer is the prefilled 0.3 L BeerCan (11.85 g ethanol), not 0.5 L.",
        "The steak is set cooked on both copies before the eat (raw steak is DangerousUncooked).",
        "Squats run 20 game minutes, not 2.",
        "Arm G also sets body.inDay to 0 an hour before the close so the closing day is a low day.",
        "fluids.water is reset to 0 by record edit before the iu reads and throughout the held sleep.",
        "The sleep runs after the first day close, about 22.8 game hours awake, not at 20.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["an RCON WaterBottle (server copy drunk)", "an RCON BeerCan (drunk)",
                                        "bread, steak and lettuce eaten", "foodtimer set 0 before each eat",
                                        "the record edited (fluids.water, acute.starvedDays, body.inDay, "
                                        "nutrients.vitC.e24)", "NR.ExcessEffectsOn toggled off and back on",
                                        "a 120 s held sleep"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "summaries": {}, "stats_pairs": [],
    "records": [], "nut": [], "quick": [], "stats_all": [], "sleep_reads": [], "vitc_reads": [],
    "spawns": [], "edits": [], "mirror_checks": [], "phase_errors": {}, "mod_error_checks": [],
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
    out["ini_seeded"] = read_ini()
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec_fx)
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["ini_after_ready"] = read_ini()
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out.get("mods_not_found"),
        "phase_errors": sorted(out["phase_errors"]),
        "abort": out.get("abort"),
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
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
            out["ini_after_stop"] = read_ini()
            out["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                           "limits": {"luaerr": LUAERR_LIMIT}}
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
                  "body_error": out.get("body_error"), "grade_error": out.get("grade_error")}, indent=1)[:7000])
