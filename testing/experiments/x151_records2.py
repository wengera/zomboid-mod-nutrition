"""x151-records2 -- Plan 4 Task 17b, acceptance 3: the four arms x151r falsified, re-read live after the fix
wave (3338380 + the residual e178a22; mod/ clean). This is the fix wave's smoke test, a NEW run with its own
id, not a re-run of x151r. ONE boot, profile `x15-records` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror
OnsetSpeed 30 DeficienciesCanKill true ExcessEffectsOn true + TKX_ThirstWatch + TKX_SleepWatch +
TKX_BoozeWatch; `Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game minute 0.625 s;
`[server]` SleepAllowed and SleepNeeded true). The run id prefix is `x151r2`. Copied from `x151_records.py`
(provenance, wall-bracketed steps, the record reads, the RCON spawns resolved on the client, the persist /
step / phase shape, the coffee and beer containers, the held sleep, the cost block), trimmed to the arms.

WHERE STATE IS READ. The record is the server's global modData `NutritionRevamp.players`, keyed by
username, read with `witness.moddata global:NutritionRevamp.players` and dotted keys on one server tick:
`rec()` reads `admin.fluids`, `admin.acute` (now with gutAlc, gutCaf, boutH, gapH), `admin.stomach.buffer`,
`admin.pool` (Plan 2's cumulative absorbed vector, which the stomach step writes), `admin.nutrients.iron`
(S, H, p, p2) and `admin.kineticsAge` (the age of the stomach's last step) with the body and nutrient
scalars. Record edits go through `globalmoddata.setpath NutritionRevamp.players admin.<path> <value>`. The
transient server tables `NutritionRevamp.server.intake.pendingAlc.admin` / `.pendingCaf.admin` and
`NutritionRevamp.server.kinetics.lastMealCa.admin` are read with `lua.global` beside the record reads in C
and D (nil between slow minutes is the expected reading: they live for one minute).

SCHEDULE (t = wall seconds from first sight; the world age starts near 3.2 h and runs 1 h per 37.5 s):
  S0  first sight: rec, nut, options, sentinels, the server ini, stats pair.
  E0  glycogen at rest: rec every ~3 s for 30 s (about 0.8 game h).
  B1  bread: `foodtimer.set admin 0`; RCON `additem Base.Bread`; `eat.action Base.Bread 1`; rec every ~3 s
      until the intake `eats` counter moves, then 60 s. Every later rec until the hold carries the buffer
      and the pool, so the bread's iron window runs on through E, C and D.
  E   squats: rec; `exercise.do squats 20` (20 game minutes = 12.5 s wall); quick reads for 22 s; rec; then
      `admin.acute.glyc` set to 150 by record edit (below any target the subject's carbohydrate can set),
      so the refill at rest is read through C and D.
  C   coffee: RCON `additem Base.WaterBottle`; the server `fluid.fill admin Base.WaterBottle Coffee 0.25`
      (107 mg caffeine at 428 mg/L); the client `drink.action Base.WaterBottle 1`; rec, the intake
      `landed` counter and the pending reads every ~2 s for 150 s (4 game h).
  D   beer: RCON `additem Base.BeerCan` (prefilled 0.3 L Beer, 11.85 g ethanol); the client `drink.action
      Base.BeerCan 1`; rec, `landed`, the pending reads every ~1.5 s, the server `stats.all` (INTOXICATION)
      every second poll, for 110 s (about 2.9 game h).
  I   cost: three `bench.global NutritionRevamp.bench_fast 100000` (the FIRST is a warm-up and is
      discarded from the reading: stated before the run), two `tick.rate 10`.
  F   sleep: fluids.water set to 0; rec; `player.sleep.hold admin 120`; every ~3.5 s rec, the server
      stats.get (asleep) and fluids.water reset to 0 (the ~20x clock of a held sleep, ruling T5-1, would
      otherwise run the pool to a lethal deficit); cancel; rec at once and 10 s later.
  B2  steak (after the hold has emptied the bread from the buffer): RCON `additem Base.Steak`; the server
      `item.set admin Base.Steak cooked true` and the client `item.state Base.Steak cooked`; foodtimer 0;
      `eat.action Base.Steak 1`; rec every ~3 s until eats moves, then 60 s.
  P   post: rec every ~5 s for 60 s (hours awake accruing after the hold, the glycogen at rest).
  Z   the error and counter reads, nut.

PREDICTIONS (written before the run; the subject's sex, masses and slowMet are read live, and every
number is recomputed in `grade_all` through the mod's own kernel run offline in lupa at this commit):
  B'  iron under bread (ruling T17-1): the pool absorbs 0.18 x ironFactor(P, V) per mg emptied, with P and V
      the BUFFER's phytate and vitamin C before each minute's emptying. For the female 80 kg fixture
      subject x151r read, a whole loaf (400 mg phytate, 0 vitamin C) gives 0.046198939851640065 per mg in
      its first minute, easing as the loaf empties (0.0707 at 274.7 mg). Graded per read interval: the
      measured pool iron over the buffer iron that left, against the kernel's per-minute replay from the
      interval's first read (the replay's own absorbed over emptied). The per-share reading of x151r
      (0.179 per mg) is FALSIFIED if every bread interval reads near 0.18 x exp(-0.0034 P). The record
      engine's iron carries the calcium factor on the buffer calcium on top (bread 95 mg -> x0.8416667, so
      0.0388841 per mg in the first minute): measured as the record's absorbed iron, (dS + dH + L dtD)/eta,
      over the pool's, against K.interact.calciumIron(buffer calcium). The steak, after the hold empties
      the buffer, reads 0.18 x ironFactor(residual P, residual V) ~ 0.18 per mg.
  C'  coffee 0.25 L = 107 mg on the gut lane (ruling T17-2): the buffer and the pool gain 0 caffeine;
      acute.gutCaf takes the landed dose; the gut empties on a 0.5 h half-life; with the whole dose at t = 0
      the kernel peaks acute.caf at 82.94216766881858 mg at minute 111 (1.85 h) for a 5.0 h half-life
      (slowMet false; 9.7 h if true -- recomputed live). Graded: the replay from the first read after the
      last landing against every later read, and the measured peak against the t = 0 prediction (the sips
      spread the landing over a few game minutes, so the peak may come a few minutes later).
  D'  beer 11.85 g ethanol on the gut lane: acute.gutAlc takes the landed dose (buffer and pool 0); bac
      peaks 0.006244101253612088 % at minute 39 (0.65 h) with the dose at t = 0 for a female 80 kg subject
      (r 0.55), then falls at beta 0.015 %/h to 0; no hangover (peak < 0.05); body.alcDay 11.85 (the
      ingested total). Graded as C'.
  E'  glycogen (ruling T17-3): at rest (met < 3) and coldMult under the 1.05 dead band (x151r read
      1.007-1.010 indoors) the shiver draw is 0 and the store relaxes toward glycTarget(cho24) on tau 24 h,
      cho24 = blend24(carbDay, carb7[7], hours since the close)/w. The amendments say "rises toward the
      target"; the kernel says "moves toward the target": at first sight glyc is about 462 and the
      fixture's carbohydrate gives cho24 well under the 3 g/kg pivot, so the target is under 462 and the
      store is predicted to FALL at rest in E0, at (glyc - target)/24 per hour. The rise is read after the
      edit to 150: from 150 it rises toward the target at (target - glyc)/24 per hour. Graded per interval
      against the kernel's one-minute replay from the interval's first read (met and coldMult of that read;
      cho24 the mean of the two reads), with x151r's old shiver form 52 x clamp((coldMult - 1)/2.5) beside
      it as the contrast. Under squats the work term draws 51.5 x clamp((met - 3)/4.5) per hour on the
      minutes the server reads met > 3, as x151r measured.
  F'  the sleep bout (ruling T17-4): under the held sleep acute.boutH grows across the ~15 % isAsleep
      misses; once a bout reaches 1 h awakeH resets to 0; at every read boutH >= 1 implies awakeH == 0 and
      gapH < 10/60 h (a gap that long ends the bout and zeroes it); awakeH reads 0 at most reads of the hold
      with occasional short climbs (the fix report's concern 4: under the fast-forward a slow step spans
      several game minutes, so 3-4 missed steps can end a bout) -- NOT a strict 0; debtH and S fall as in
      x151r; acute.iu equals K.acute.iu offline on each read and falls with awakeH; acute.frozen false.
  I'  bench_fast (the second and third calls) within 25 % of #2888's 3.06-3.40 us; tick rate within 5 % of
      10.00-10.11.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Glycogen: the record edit of acute.glyc to 150 after the squats, so a refill at rest is readable (the
     fixture subject's store starts above its carbohydrate target and falls at rest).
  2. Coffee is 0.25 L (107 mg) in an RCON WaterBottle refilled server-side with Coffee and drunk by the
     client's drink.action; beer is the prefilled 0.3 L BeerCan (both as x151r).
  3. The steak is set cooked on both copies before the eat, and is eaten after the hold (the buffer empty
     of bread), not after one stomach half-time.
  4. fluids.water is reset to 0 by record edit before and throughout the held sleep.
  5. Squats run 20 game minutes (x151r's shape).
  6. The bench's first call is a warm-up, discarded (the fix-wave brief).

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
SESSION = ("Plan 4 acceptance 3, the four fixed arms live: iron under bread and steak on the meal context "
           "(B'), coffee and beer on the gut lane (C'/D'), glycogen at rest, under squats and refilling (E'), "
           "the sleep bout under a held sleep (F'), cost (I'): one boot of x15-records at DayLength 1")
ARTIFACT = "records2.json"
USER = "admin"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
ORDER = ("vitC", "thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline", "vitA", "vitD",
         "vitE", "vitK", "pantothenate", "biotin", "iron", "zinc", "copper", "magnesium", "calcium", "iodine",
         "selenium", "fibre", "efa", "sodium", "potassium", "caffeine", "ethanol")
BODY_KEYS = ("fm", "lm", "sex", "met", "coldMult", "dmod", "energyState", "lastCloseAgeH", "dayIndex", "alcDay",
             "carbDay", "carb7", "inDay")
NUT_SCALARS = ("epoch", "lastAgeH", "ironGrade", "lastDayIndex")
REC_KEYS = ([f"{USER}.fluids", f"{USER}.acute", f"{USER}.stomach.buffer", f"{USER}.pool", f"{USER}.stomachFill",
             f"{USER}.kineticsAge", f"{USER}.nutrients.iron"]
            + [f"{USER}.body.{k}" for k in BODY_KEYS] + [f"{USER}.nutrients.{k}" for k in NUT_SCALARS])
NUT_CALL1 = ([f"{USER}.nutrients.{k}" for k in ORDER[:14]]
             + [f"{USER}.nutrients.epoch", f"{USER}.nutrients.lastAgeH", f"{USER}.pool"])
NUT_CALL2 = ([f"{USER}.nutrients.{k}" for k in ORDER[14:]]
             + [f"{USER}.nutrients.epoch", f"{USER}.nutrients.lastAgeH"])
QUICK_KEYS = [f"{USER}.acute.glyc", f"{USER}.acute.g", f"{USER}.body.met", f"{USER}.body.coldMult",
              f"{USER}.nutrients.lastAgeH", f"{USER}.body.carbDay", f"{USER}.body.carb7",
              f"{USER}.body.lastCloseAgeH"]
INTAKE = "NutritionRevamp.server.intake.stats"
COUNTERS = ("sips", "landed", "worldSips", "failures", "eats", "cancels")
OPT_KEYS = ("mode", "onsetSpeed", "deficienciesCanKill", "excessEffectsOn", "balanceBonus", "nutritionOn")
PENDING = (("pendingAlc", "NutritionRevamp.server.intake.pendingAlc." + USER),
           ("pendingCaf", "NutritionRevamp.server.intake.pendingCaf." + USER),
           ("lastMealCa", "NutritionRevamp.server.kinetics.lastMealCa." + USER))
BOTTLE, BEER, BREAD, STEAK = "Base.WaterBottle", "Base.BeerCan", "Base.Bread", "Base.Steak"
COFFEE_L = 0.25
E0_S, E0_EVERY = 30, 3.0
C_POLL_S, C_POLL_EVERY = 150, 2.0
D_POLL_S, D_POLL_EVERY = 110, 1.5
EAT_WAIT_S, EAT_AFTER_S, EAT_POLL_EVERY = 60, 60, 3.0
EX_NAME, EX_MIN, EX_READ_S = "squats", 20, 22
GLYC_EDIT = 150
HOLD_S, HOLD_POLL_EVERY = 120, 3.5
P_S, P_EVERY = 60, 5.0
TICK_S = 10
BENCH_N = 100000
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6

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
    """One witness.moddata call: fluids, acute, the stomach buffer, the pool, the iron record as tables, the
    body and nutrient scalars and the stomach's step age -- one server tick."""
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(REC_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "worldAge": a.get("worldAge"),
           "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"), "error": a.get("error")}
    for name, key in (("fluids", "fluids"), ("acute", "acute"), ("buffer", "stomach.buffer"), ("pool", "pool"),
                      ("iron", "nutrients.iron")):
        v = vals.get(f"{USER}.{key}")
        row[name] = v if isinstance(v, dict) else None
    row["stomachFill"] = to_num(vals.get(f"{USER}.stomachFill"))
    row["kineticsAge"] = to_num(vals.get(f"{USER}.kineticsAge"))
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
    out["nut"].append(row)
    return row


def quick(tag):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(QUICK_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge")}
    for k in QUICK_KEYS:
        v = vals.get(k)
        row[k[len(USER) + 1:]] = v if isinstance(v, (dict, list)) else to_num(v)
    out["quick"].append(row)
    return row


def pending(tag):
    row = {"tag": tag, "wall": wall()}
    for name, g in PENDING:
        row[name] = gv(server, g, f"{tag}_{name}")
    out["pending"].append(row)
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


def setpath(tag, field, value):
    a = ack(step(tag, server, "globalmoddata.setpath", f"{STORE} {USER}.{field} {value}"))
    row = {"tag": tag, "field": field, "value": value, "wall": wall(), "ack": a}
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


def poll_loop(key, seconds, every, extra=None):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"{key}_p{i}")["tag"]}
        if extra is not None:
            extra(p, i)
        rows.append(p)
        i += 1
        persist()
        rest = every - (wall() - t_s)
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
    S0["sentinels"] = {n: gv(server, n, f"s0_{n}") for n in ("NR_IntakeDrink_Installed", "NR_IntakeWorld_Installed")}
    S0["options"] = options("s0")
    S0["nutrients_server"] = {k: gv(server, f"NutritionRevamp.server.nutrients.{k}", f"s0_nut_{k}")
                              for k in ("lastError", "sleepDisabled")}
    S0["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"s0_ns_{k}")
                             for k in ("minutes", "errors", "players", "noBody", "healed", "days")}
    S0["counters"] = counters("s0")
    S0["stats"] = stats_pair("s0")
    S0["time"] = ack(step("s0_time", server, "time.snapshot", ""))
    persist()


def phase_E0():
    E = out["phases"]["E0"] = {}
    E["polls"] = poll_loop("E0", E0_S, E0_EVERY)
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
    E["edit"] = setpath("E_glyc", "acute.glyc", GLYC_EDIT)
    E["post_edit"] = rec("E_post_edit")["tag"]
    persist()


def phase_C():
    C = out["phases"]["C"] = {}
    C["spawn"] = spawn(BOTTLE, "C")
    C["client_litres_spawned"] = litres("C_cl_spawned", client, BOTTLE)
    C["fill"] = ack(step("C_fill", server, "fluid.fill", f"{USER} {BOTTLE} Coffee {COFFEE_L}"))
    C["server_litres_filled"] = litres("C_sl_filled", server, BOTTLE)
    C["counters_before"] = counters("C_before")
    C["before"] = rec("C_before")["tag"]
    r = step("C_drink", client, "drink.action", f"{BOTTLE} 1")
    C["drink_wall"] = r["wall_before"]
    C["drink"] = r["ack"]

    def extra(p, i):
        p["landed"] = gv(server, f"{INTAKE}.landed", f"C_p{i}_landed")
        p["pending"] = pending(f"C_p{i}_pd")["tag"]
        if i % 5 == 0:
            p["server_litres"] = litres(f"C_p{i}_sl", server, BOTTLE)
    C["polls"] = poll_loop("C", C_POLL_S, C_POLL_EVERY, extra)
    C["counters_after"] = counters("C_after")
    C["after"] = rec("C_after")["tag"]
    persist()


def phase_D():
    D = out["phases"]["D"] = {}
    D["spawn"] = spawn(BEER, "D")
    D["server_litres"] = litres("D_sl", server, BEER)
    D["counters_before"] = counters("D_before")
    D["before"] = rec("D_before")["tag"]
    D["intox_before"] = srv_stats_all("D_sa_before")["tag"]
    r = step("D_drink", client, "drink.action", f"{BEER} 1")
    D["drink_wall"] = r["wall_before"]
    D["drink"] = r["ack"]

    def extra(p, i):
        p["landed"] = gv(server, f"{INTAKE}.landed", f"D_p{i}_landed")
        p["pending"] = pending(f"D_p{i}_pd")["tag"]
        if i % 2 == 0:
            p["sa"] = srv_stats_all(f"D_p{i}_sa")["tag"]
        if i % 6 == 0:
            p["server_litres"] = litres(f"D_p{i}_sl", server, BEER)
    D["polls"] = poll_loop("D", D_POLL_S, D_POLL_EVERY, extra)
    D["counters_after"] = counters("D_after")
    D["after"] = rec("D_after")["tag"]
    persist()


def phase_I():
    I = out["phases"]["I"] = {"bench": [], "tick": []}
    for i in range(3):
        I["bench"].append(ack(step(f"I_bench{i}", server, "bench.global",
                                   f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60)))
    I["tick"] = [tick_rate("Ia"), tick_rate("Ib")]
    persist()


def phase_F():
    F = out["phases"]["F"] = {"polls": []}
    F["water0"] = setpath("F_water0", "fluids.water", 0)
    time.sleep(1.5)
    F["before"] = rec("F_before")["tag"]
    F["stats_before"] = stats_pair("F_before")
    F["sg_before"] = srv_stats_get("F_sg_before")["tag"]
    r = step("F_hold", server, "player.sleep.hold", f"{USER} {HOLD_S}")
    F["hold_wall"] = r["wall_before"]
    F["hold"] = r["ack"]
    end = F["hold_wall"] + HOLD_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"F_p{i}")["tag"], "sg": srv_stats_get(f"F_p{i}_sg")["tag"]}
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
    time.sleep(10.0)
    F["after2"] = rec("F_after2")["tag"]
    F["stats_after"] = stats_pair("F_after")
    persist()


def phase_B2():
    B = out["phases"]["B2"] = {}
    B["spawn"] = spawn(STEAK, "B2")
    B["cook_server"] = ack(step("B2_cook_srv", server, "item.set", f"{USER} {STEAK} cooked true"))
    cs = ack(step("B2_cook_cli", client, "item.state", f"{STEAK} cooked"))
    B["cook_client"] = {k: cs.get(k) for k in ("cooked", "id", "spawned", "calories")}
    B.update(eat("B2", STEAK))
    persist()


def phase_P():
    P = out["phases"]["P"] = {}
    P["polls"] = poll_loop("P", P_S, P_EVERY)
    persist()


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["nut"] = nut("Z_nut")["tag"]
    Z["options"] = options("Z")
    Z["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                            for k in ("minutes", "errors", "players", "noBody", "healed", "days", "skippedDays",
                                      "badAge")}
    Z["lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "Z_lastError")
    Z["intake_lastError"] = gv(server, "NutritionRevamp.server.intake.lastError", "Z_in_lastError")
    Z["kinetics_lastError"] = gv(server, "NutritionRevamp.server.kinetics.lastError", "Z_kin_lastError")
    Z["kinetics_stats"] = {k: gv(server, f"NutritionRevamp.server.kinetics.stats.{k}", f"Z_ks_{k}")
                           for k in ("minutes", "players", "failures")}
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
    ke = gv(server, "NutritionRevamp.server.kinetics.lastError", f"chk_{after}_kle")
    if le is not None or (to_num(ne) or 0) > 0:
        why.append({"nutrients_lastError": le, "nutrients_errors": ne})
    if ie is not None:
        why.append({"intake_lastError": ie})
    if ke is not None:
        why.append({"kinetics_lastError": ke})
    if clients and "lua_error" in getattr(clients[0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why})
    return why


def body():
    for name, fn in (("S0", phase_S0), ("E0", phase_E0), ("B1", phase_B1), ("E", phase_E), ("C", phase_C),
                     ("D", phase_D), ("I", phase_I), ("F", phase_F), ("B2", phase_B2), ("P", phase_P),
                     ("Z", phase_Z)):
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


def ring7(v):
    """carb7 / eb7 as read: a list (JSON array) or a dict keyed "1".."7"; the 7th entry."""
    if isinstance(v, list) and len(v) >= 7:
        return to_num(v[6])
    if isinstance(v, dict):
        return to_num(v.get("7"))
    return None


def cho24_of(body_, ageH, w, K):
    cd = to_num(body_.get("carbDay"))
    c7 = ring7(body_.get("carb7"))
    lc = to_num(body_.get("lastCloseAgeH"))
    if None in (cd, c7, lc) or ageH is None or not w:
        return None
    return K.body.blend24(cd, c7, ageH - lc) / w


def recs_by_tag():
    return {r["tag"]: r for r in out["records"]}


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
    order = sorted([r for r in out["records"] if fnum(r, "nutrients", "lastAgeH") is not None],
                   key=lambda r: (fnum(r, "nutrients", "lastAgeH"), r["wall"]))
    hold_wall = (P.get("F") or {}).get("hold_wall")

    # the t = 0 predictions for the live subject (the whole dose in the gut at once)
    try:
        a = K.acute.new(0)
        a.slowMet = bool(ac0.get("slowMet"))
        a.gutAlc, a.gutCaf = 11.85, COFFEE_L * 428
        bac_pk, caf_pk = (0, 0), (0, 0)
        for m in range(1, 601):
            al, ca = K.acute.absorbGut(a, 1 / 60.0)
            K.acute.caffeine(a, ca, w, 1 / 60.0)
            K.acute.alcohol(a, al, w, sex, 1 / 60.0)
            if a.bac > bac_pk[0]:
                bac_pk = (a.bac, m)
            if a.caf > caf_pk[0]:
                caf_pk = (a.caf, m)
        S["t0_predictions"] = {"bac_peak_pct": bac_pk[0], "bac_peak_min": bac_pk[1],
                               "caf_peak_mg": caf_pk[0], "caf_peak_min": caf_pk[1],
                               "iron_first_minute_per_mg_400": 0.18 * K.stomach.ironFactor(400, 0),
                               "calciumIron_95": K.interact.calciumIron(95),
                               "gut_first_30min_g": 11.85 * (1 - math.exp(-math.log(2) * 0.5 / K.acute.GUT_T_HALF))}
    except Exception as e:                     # noqa: BLE001
        S["t0_error"] = f"{type(e).__name__}: {e}"

    # B': per read interval, measured pool iron over buffer iron emptied vs the kernel's per-minute replay
    try:
        two = KK.recs.REC.iron.two
        L = KK.recs.REC.iron.L[sex]
        S0i = two.storeShare * two.totalPerKg[sex] * w
        ks = sorted([r for r in out["records"] if r.get("buffer") and r.get("pool") and r.get("kineticsAge") is not None],
                    key=lambda r: (r["kineticsAge"], r["wall"]))
        rows = []
        for r0, r1 in zip(ks, ks[1:]):
            k0, k1 = r0["kineticsAge"], r1["kineticsAge"]
            if k1 <= k0:
                continue
            b0, b1 = numtab(r0["buffer"]), numtab(r1["buffer"])
            p0, p1 = numtab(r0["pool"]), numtab(r1["pool"])
            if b0.get("iron", 0) <= 1e-9 or b1.get("iron", 0) >= b0.get("iron", 0):
                continue                       # nothing buffered, or a landing inside the interval
            if b1.get("calories", 0) > b0.get("calories", 0) + 1e-6 or b1.get("water", 0) > b0.get("water", 0) + 1e-6:
                landed = True                  # a drink or a meal landed inside the interval
            else:
                landed = False
            emptied = b0["iron"] - b1["iron"]
            absorbed = p1.get("iron", 0) - p0.get("iron", 0)
            n = max(1, int(round((k1 - k0) * 60)))
            dt = (k1 - k0) / n
            stom = KK.table({"buffer": b0, "bulk": 0})
            se, sa, ca_sum = 0.0, 0.0, 0.0
            for _ in range(n):
                ctx = K.stomach.context(stom)
                em = K.stomach.empty(stom, dt)
                ab = K.stomach.absorb(em, ctx)
                se += em.iron
                sa += ab.iron
                ca_sum += ab.iron * K.interact.calciumIron(ctx.calcium)
            f1 = K.stomach.emptyFraction(K.stomach.HALF_TIME_H, K.stomach.compositionScale(KK.table(b0)), 1 / 60.0)
            row = {"t0": r0["tag"], "t1": r1["tag"], "k0": k0, "k1": k1, "minutes": n, "landed_inside": landed,
                   "bufPhytate0": b0.get("phytate"), "bufPhytate1": b1.get("phytate"), "bufVitC0": b0.get("vitC"),
                   "bufCalcium0": b0.get("calcium"), "emptiedIron": emptied, "absorbedIron": absorbed,
                   "perMg": absorbed / emptied, "kernelPerMg": sa / se if se > 0 else None,
                   "kernelEmptiedIron": se, "kernelAbsorbedIron": sa,
                   "firstMinutePerMg": 0.18 * K.stomach.ironFactor(b0.get("phytate", 0), b0.get("vitC", 0)),
                   "perSharePerMg_x151r_form": 0.18 * K.stomach.ironFactor(f1 * b0.get("phytate", 0), f1 * b0.get("vitC", 0)),
                   "wall0": r0["wall"], "before_hold": hold_wall is None or r1["wall"] < hold_wall}
            i0, i1 = numtab(r0.get("iron")), numtab(r1.get("iron"))
            a0, a1 = fnum(r0, "nutrients", "lastAgeH"), fnum(r1, "nutrients", "lastAgeH")
            if None not in (i0.get("S"), i1.get("S"), i0.get("H"), i1.get("H"), a0, a1) and absorbed > 0:
                eta = 1 - two.etaK * min(1.0, max(0.0, i0["S"] / S0i))
                a_rec = (i1["S"] + i1["H"] - i0["S"] - i0["H"] + L * (a1 - a0) / 24.0) / eta
                row.update({"recordAbsorbedIron": a_rec, "recordOverPool": a_rec / absorbed,
                            "kernelCalciumFactor": ca_sum / sa if sa > 0 else None,
                            "calciumIron_buf0": K.interact.calciumIron(b0.get("calcium", 0)),
                            "nutAge0": a0, "nutAge1": a1})
            rows.append(row)
        S["B"] = {"intervals": rows, "L": L, "S0": S0i, "etaK": two.etaK}
    except Exception as e:                     # noqa: BLE001
        S["B_error"] = f"{type(e).__name__}: {e}"
        S["B_tb"] = traceback.format_exc()[-2000:]

    # C' and D': the gut lane, caf and bac series, the replay from the first read after the last landing
    try:
        series = []
        for r in order:
            ac, po, bu = numtab(r.get("acute")), numtab(r.get("pool")), numtab(r.get("buffer"))
            series.append({"tag": r["tag"], "ageH": fnum(r, "nutrients", "lastAgeH"), "wall": r["wall"],
                           "gutCaf": ac.get("gutCaf"), "gutAlc": ac.get("gutAlc"), "caf": ac.get("caf"),
                           "alc": ac.get("alc"), "bac": ac.get("bac"), "alcPeak": ac.get("alcPeak"),
                           "hang": ac.get("hang"), "hangH": ac.get("hangH"), "bufCaf": bu.get("caffeine"),
                           "bufEth": bu.get("ethanol"), "poolCaf": po.get("caffeine"), "poolEth": po.get("ethanol"),
                           "alcDay": fnum(r, "body", "alcDay"), "alcDayG": ac.get("alcDayG")})
        S["CD_series"] = series
        bt = {s["tag"]: s for s in series}
        for key, gut, val in (("C", "gutCaf", "caf"), ("D", "gutAlc", "bac")):
            X = P.get(key) or {}
            polls = X.get("polls") or []
            final = to_num((X.get("counters_after") or {}).get("landed"))
            start = None
            for p in polls:
                if final is not None and to_num(p.get("landed")) == final and p["rec"] in bt:
                    start = p["rec"]
                    break
            blk = {"start": start, "landed_final": final}
            if start is not None:
                r0 = R[start]
                a0d = numtab(r0["acute"])
                a0d.setdefault("gutAlc", 0)
                a0d.setdefault("gutCaf", 0)
                a = KK.table(a0d)
                age = fnum(r0, "nutrients", "lastAgeH")
                blk["start_ageH"] = age
                blk["start_state"] = {k: bt[start][k] for k in ("gutCaf", "gutAlc", "caf", "alc", "bac")}
                later = [s for s in series if s["ageH"] is not None and s["ageH"] > age]
                cmp_rows = []
                pk = (getattr(a, val), age)
                for s in later:
                    n = int(round((s["ageH"] - age) * 60))
                    for _ in range(n):
                        al, ca = K.acute.absorbGut(a, 1 / 60.0)
                        K.acute.caffeine(a, ca, w, 1 / 60.0)
                        K.acute.alcohol(a, al, w, sex, 1 / 60.0)
                        age += 1 / 60.0
                        if getattr(a, val) > pk[0]:
                            pk = (getattr(a, val), age)
                    cmp_rows.append({"tag": s["tag"], "ageH": s["ageH"], "obs_" + val: s[val], "pred_" + val: getattr(a, val),
                                     "obs_" + gut: s[gut], "pred_" + gut: getattr(a, gut)})
                    if len(cmp_rows) >= 400:
                        break
                blk["replay"] = cmp_rows
                blk["replay_peak"] = {"value": pk[0], "ageH": pk[1]}
            # the measured peak inside the phase window and its age; the drink's age
            dr = R.get(X.get("before"))
            blk["before_ageH"] = fnum(dr, "nutrients", "lastAgeH") if dr else None
            win = [bt[p["rec"]] for p in polls if p["rec"] in bt]
            vals = [(s[val], s["ageH"], s["tag"]) for s in win if s[val] is not None]
            if vals:
                m = max(vals, key=lambda t: t[0])
                blk["measured_peak"] = {"value": m[0], "ageH": m[1], "tag": m[2]}
            # the gut's half-life between consecutive reads after the start (no landing inside)
            fits = []
            if start is not None:
                after = [s for s in win if s["ageH"] is not None and s["ageH"] >= blk["start_ageH"]]
                for s0, s1 in zip(after, after[1:]):
                    g0, g1 = s0[gut], s1[gut]
                    dh = s1["ageH"] - s0["ageH"]
                    if g0 and g1 and dh > 0 and 0 < g1 < g0:
                        fits.append({"t0": s0["tag"], "t1": s1["tag"], "dh": dh, "thalf": dh * math.log(2) / math.log(g0 / g1)})
            blk["gut_thalf_fits"] = fits
            S[key] = blk
    except Exception as e:                     # noqa: BLE001
        S["CD_error"] = f"{type(e).__name__}: {e}"
        S["CD_tb"] = traceback.format_exc()[-2000:]

    # E': glycogen per interval vs the one-minute replay (fix form), the old shiver form beside it
    try:
        rows = []
        for r0, r1 in zip(order, order[1:]):
            ac0_, ac1_ = numtab(r0.get("acute")), numtab(r1.get("acute"))
            a0, a1 = fnum(r0, "nutrients", "lastAgeH"), fnum(r1, "nutrients", "lastAgeH")
            met, cm = fnum(r0, "body", "met"), fnum(r0, "body", "coldMult")
            if None in (ac0_.get("glyc"), ac1_.get("glyc"), a0, a1, met, cm) or a1 <= a0:
                continue
            if hold_wall is not None and r0["wall"] >= hold_wall and r1["wall"] <= hold_wall + HOLD_S + 15:
                inhold = True
            else:
                inhold = False
            c0 = cho24_of(r0.get("body") or {}, a0, w, K)
            c1 = cho24_of(r1.get("body") or {}, a1, w, K)
            cho = (c0 + c1) / 2 if c0 is not None and c1 is not None else c0
            n = int(round((a1 - a0) * 60))
            if n <= 0 or cho is None:
                continue
            t = KK.table({"glyc": ac0_["glyc"], "g": ac0_.get("g", 1)})
            for _ in range(n):
                K.acute.glycogen(t, met, cm, cho, (a1 - a0) / n)
            old_shiver = 52 * min(1.0, max(0.0, (cm - 1) / 2.5))
            rows.append({"t0": r0["tag"], "t1": r1["tag"], "age0": a0, "age1": a1, "met": met, "coldMult": cm,
                         "cho24": cho, "target": K.acute.glycTarget(cho), "glyc0": ac0_["glyc"], "glyc1": ac1_["glyc"],
                         "dGlyc": ac1_["glyc"] - ac0_["glyc"], "pred_glyc1": t.glyc,
                         "pred_dGlyc": t.glyc - ac0_["glyc"],
                         "old_shiver_draw_per_h": old_shiver, "old_shiver_draw": old_shiver * (a1 - a0),
                         "inHold": inhold, "wall0": r0["wall"]})
        S["E"] = {"intervals": rows}
        Q = out["quick"]
        qrows = []
        for q0, q1 in zip(Q, Q[1:]):
            a0, a1 = q0.get("nutrients.lastAgeH"), q1.get("nutrients.lastAgeH")
            if None in (a0, a1, q0.get("acute.glyc"), q1.get("acute.glyc"), q1.get("body.met")) or a1 <= a0:
                continue
            met = q1["body.met"]
            qrows.append({"t0": q0["tag"], "t1": q1["tag"], "age1": a1, "met": met, "coldMult": q1.get("body.coldMult"),
                          "dGlyc": q1["acute.glyc"] - q0["acute.glyc"],
                          "workTerm": -51.5 * min(1.6, max(0.0, (met - 3) / 4.5)) * (a1 - a0)})
        S["E_quick"] = qrows
    except Exception as e:                     # noqa: BLE001
        S["E_error"] = f"{type(e).__name__}: {e}"
        S["E_tb"] = traceback.format_exc()[-2000:]

    # F': the bout invariants and iu offline on every read
    try:
        rows = []
        for r in sorted([r for r in out["records"] if r.get("acute") and r.get("fluids")], key=lambda r: r["wall"]):
            ac, fl = numtab(r["acute"]), numtab(r["fluids"])
            ig = fnum(r, "nutrients", "ironGrade") or 1
            iu_k = K.acute.iu(KK.table(ac), fl.get("dehydPct", 0), int(ig))
            bh, aw, gp = ac.get("boutH"), ac.get("awakeH"), ac.get("gapH")
            rows.append({"tag": r["tag"], "wall": r["wall"], "ageH": fnum(r, "nutrients", "lastAgeH"),
                         "awakeH": aw, "boutH": bh, "gapH": gp, "sleptH": ac.get("sleptH"), "debtH": ac.get("debtH"),
                         "S": ac.get("S"), "frozen": ac.get("frozen"), "winStartH": ac.get("winStartH"),
                         "winSleptH": ac.get("winSleptH"), "iu": ac.get("iu"), "iu_kernel": iu_k,
                         "inv_bout_awake0": (None if bh is None or aw is None else (bh < 1 or aw == 0)),
                         "inv_gap_lt_10min": (None if gp is None else gp < 10 / 60.0)})
        reads = [x for x in out["sleep_reads"] if x["tag"].startswith("F_p")]
        share = (sum(1 for x in reads if str(x.get("asleep")).lower() == "true") / len(reads)) if reads else None
        S["F"] = {"rows": rows, "asleep_share_reads": share, "n_sleep_reads": len(reads)}
    except Exception as e:                     # noqa: BLE001
        S["F_error"] = f"{type(e).__name__}: {e}"
        S["F_tb"] = traceback.format_exc()[-2000:]

    # I'
    I = P.get("I") or {}
    us = [to_num(b.get("usPerCall")) for b in I.get("bench") or []]
    S["I"] = {"usPerCall_all": us, "warmup_discarded": us[:1], "usPerCall_read": us[1:],
              "ticksPerSecond": [t.get("ticksPerSecond") for t in (I.get("tick") or [])]}
    for ph in ("B", "C", "D", "E", "F", "I"):
        grade(ph, "see the PREDICTIONS block of the driver docstring", {"summary_key": ph}, "see_raw",
              "see the PREDICTIONS block")


prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x151r2-dry-run", None) if DRY_RUN else new_run_dir("x151r2")
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
        "acute.glyc is set to 150 by record edit after the squats, so a refill at rest is readable (the "
        "fixture subject's store starts above its carbohydrate target and falls at rest).",
        "Coffee is 0.25 L (107 mg) in an RCON WaterBottle refilled server-side with Coffee and drunk by the "
        "client's drink.action; beer is the prefilled 0.3 L BeerCan (as x151r).",
        "The steak is set cooked on both copies and eaten after the held sleep, the buffer empty of bread.",
        "fluids.water is reset to 0 by record edit before and throughout the held sleep.",
        "Squats run 20 game minutes.",
        "The first bench_fast call is a warm-up and is discarded from the reading.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["bread and steak eaten", "an RCON WaterBottle (server copy drunk)",
                                        "an RCON BeerCan (drunk)", "foodtimer set 0 before each eat",
                                        "the record edited (acute.glyc, fluids.water)", "a 120 s held sleep"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "summaries": {}, "stats_pairs": [],
    "records": [], "nut": [], "quick": [], "pending": [], "stats_all": [], "sleep_reads": [],
    "spawns": [], "edits": [], "phase_errors": {}, "mod_error_checks": [],
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
