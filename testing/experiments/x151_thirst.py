"""x151-thirst -- Plan 4 Task 16, acceptance 1: thirst and water live, the first boot of the whole Plan 4
build (HEAD cac63cc: the record engine, the fluids pools, the thirst view, the auto-drink bracket, the
intake hooks with the world-water wrap, the Plan 3 stubs on live scalars, the mirror). ONE boot, profile
`x15-thirst` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror OnsetSpeed 1 DeficienciesCanKill true +
TKX_ThirstWatch; `Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game minute
0.625 s; the fixture's SleepAllowed/SleepNeeded false/false). The run id prefix is `x151t`. Copied from
`x151_water_gate.py` (provenance, wall-bracketed steps, the ThirstWatch window, RCON spawns resolved on the
client, the persist/step shape) and `x141_body.py` (tick rate and bench).

WHERE STATE IS READ. The record lives in the server's global modData `NutritionRevamp.players`, keyed by
username; every state quantity is read there with `witness.moddata global:NutritionRevamp.players` and
dotted keys, several in ONE call (one server tick): `admin.fluids` and `admin.acute` as whole tables,
`admin.stomach.buffer` as a table, and the scalars of `admin.body` and `admin.nutrients` by name. THIRST
(the stat) is read live on BOTH sides (`stats.get`). The client mirror is a request-time snapshot (Task 14,
ruling T14-1): every client mirror read is preceded by `bench.global NutritionRevamp.client.requestMirror 1`
on the client and a wait for `NutritionRevamp.client.received` to move, and the server is read right after
it for the comparison. Record edits go through `globalmoddata.setpath NutritionRevamp.players
admin.fluids.<field> <value>` (the record is global modData, so the global setter is the record setter).

SCHEDULE (arms A-I of the Task 16 amendments; the order differs, see DEVIATIONS):
  S0  first sight: the record read at once; the sentinels, the options, the probe (inventory containers).
  A   a 60 s ThirstWatch window from first sight with record + stats pairs every ~4 s; then a mirror check.
  H1  tick.rate 10 on the server (the quiet rate before the arms).
  B   rest, no drinking, until the record's lastAgeH reaches the fluids' creation + 10 game hours (wall cap
      440 s): a record read and a stats pair every ~8 s, a mirror check at the middle and the end; then a
      20 s ThirstWatch window with record reads (THIRST per tick against the stamped target).
  D   the auto-drink bracket: a 20 s window armed; the server `fluid.fill admin Base.CanteenMilitaryFull
      Water 0.9` (spawns a server-side canteen in one command, so autoDrink sees Water on its first tick);
      fast reads (autoDrop, the stomach buffer's water, the canteen's litres) for 25 s, then slower reads
      for 15 s; then the canteen emptied (`fluid.fill ... Water 0`).
  C   a 1 L water drink: `fluids.water` set to -400 g by setpath (the view under the 0.1 auto-drink gate,
      so autoDrink cannot take the bottle first); RCON `additem Base.WaterBottle` resolved on the client;
      the server `fluid.fill admin Base.WaterBottle Water 1.0`; the client `drink.action Base.WaterBottle
      1`; record reads every ~3 s for 150 s (the landing, then the surplus clearance).
  F   sodium: RCON `additem Base.Pop2` (0.3 L Cola, 40 mg/L sodium in the seed); `drink.action Base.Pop2 1`;
      record reads every ~4 s for 150 s (fluids.na against the basal draw and the stomach's sodium).
  F2  the plasma-sodium edges by record edits: (a) `fluids.water` 8000 -> c, naPlasma, thirstTarget for
      ~6 s; (b) `fluids.na` -1000 with `fluids.water` at -2.2 % of mass -> the hypotonic cap (<= 0.11) for
      ~6 s; then na restored to its pre-F2 value.
  E   the kill cap: `sandbox.var NR.DeficienciesCanKill false`; `fluids.water` at -9 % of mass -> the view
      <= 0.83 for ~6 s; `sandbox.var NR.DeficienciesCanKill true` -> the cap lifts for ~6 s; then
      `fluids.water` at -2.5 % of mass (THIRST for arm I).
  I   world water: a 45 s window armed; `water.take admin`; record, stats and the intake counters for 45 s;
      `player.stop`.
  G   sweat: `player.walk +-20 0` re-issued while the client reads not moving, 60 s; record reads (body.met,
      fluids.sweatLmin/sweat6h/loss6h/sweatActive) every ~3 s; `player.stop`; one read 8 s later.
  H   cost: three `bench.global NutritionRevamp.bench_fast 100000` and two `tick.rate 10` (x141b's shape).
  Z   a last mirror check and record read.

PREDICTIONS (written before the run; the subject's sex, lean and fat mass are read live, so every number
below that depends on mass is recomputed in `grade_all` through the mod's own kernel run offline in lupa):
  A   fluids.water and thirstTarget at their creation values (0 and 0) less the minutes of basal loss since
      creation: water = -AI[sex]/1440 g per game minute exactly (no absorbed water: the seeded stomach has
      no water); THIRST on the server equals the stamped thirstTarget at every tick of the window (vanilla's
      drain overwritten), so its slope is the view's (the basal loss's), not x151w's drained 0.0459 per 60 s
      (#2945's baseline window, `phases.A0.watch.fields.thirst` of x151w); the client THIRST follows within
      the 1 Hz packet. nutrients.epoch, allReplete and acute.frozen as read (frozen true expected: the
      fixture's sleep options false/false, ruling 13).
  B   at creation + 10 h: water -AI/1440 x 600 g; dehydPct, c, naPlasma and thirstTarget as the kernel
      gives them for this subject (80 kg male: dehydPct 1.92708, c 1.0116424, thirst 0.31421 -- the Task 11
      fix-1 hand values); THIRST on both sides = the view; the THIRST moodle 1 above 0.12 and 2 above 0.25
      (#0509); dmod up and rmod down with dehydPct (Task 13), the carry delta down (eAcute), acute.iu up
      from 1 % deficit.
  D   one sip: the canteen falls by 2 x THIRST litres (#2939), autoDrop = the THIRST drop (litres / 2) within
      a tick, the stomach buffer's water up by 2 x drop x 1000 g at the next slow minute and autoDrop back
      to 0; no second sip while autoDrop is pending; a later sip only once the view (pool + stomach water)
      is above 0.1 again.
  C   the stomach buffer's water +1000 g across the sips (the wrapper's landings), viewPct falling at once
      (T1-1) while dehydPct falls as the water absorbs (pure water: a 0.5 game-hour half-time = 18.75 s
      wall); the pool's surplus cleared at 320 g/h (S0521) on top of the basal loss once the buffer is empty;
      THIRST = the view.
  F   the stomach buffer's sodium +12 mg (0.3 L x 40 mg/L) at the drink; fluids.na = the basal-only draw
      plus the absorbed sodium / 23 (exact accounting); c and naPlasma move with the cola's 267 g water.
  F2  (a) +8 L: c and naPlasma = the kernel's conc for this subject (about 122 mmol/L for 65.6 kg lean),
      thirstTarget 0 (no volume or osmotic drive: the cap is not what holds it); (b) na -1000 at a 2.2 %
      deficit: naPlasma < 135 and thirstTarget = 0.11 (the volume term alone would be above 0.25).
  E   off: thirstTarget = 0.83 at a 9 % deficit; on: 1.0.
  I   if a source is within 10 tiles: the buffer's water up by at most 2 x THIRST litres x 1000 (the
      action's planned litres, #2930, Task 12 fix-1's cap), worldSips > 0, the view falling.
  G   body.met while walking (#2875: the server's rate approaches Walking5kmh); sweat litres > 0 iff
      body.met > 3 (sweatLh = clamp((met - 3)/5, 0, 1.5) x thermoFluids x sweatK); sweatActive needs the
      6 h sweat share above 0.5 -- not reachable in 60 s from a rested EMA (predicted false).
  H   bench_fast within 25 % of #2888's 3.06-3.40 us; tick rate within 5 % of 10.00-10.11.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Order A, B, D, C, F, F2, E, I, G, H: autoDrink fires on any non-empty container once THIRST > 0.1
     (#2770) and B ends near 0.3, so the bracket arm (D) runs first on a server-only canteen, and C drinks
     from a pool set to -400 g by record edit so the bottle cannot be auto-drunk before the drink action.
  2. D's container is a server-side canteen made by the server `fluid.fill` (Water 0.9 L), not a WaterBottle
     by `inventory.add`: one command spawns and fills it (the WaterBottle script picks Water or
     CarbonatedWater at random and the CarbonatedWater fluid has no seed row).
  3. C's bottle is RCON-spawned (both sides hold it, x151w B1's route) and refilled to Water 1.0 L by the
     server twin; the client's copy is not refilled (the twin's comment), and the drink is the client's
     drink action, which the server runs on its own copy (x151w B1).
  4. The view is a function of the record, so the thirst levels are set by record edits (`fluids.water`,
     `fluids.na`), never by `stats.setany` (the view overwrites a write within a tick).
  5. The hypotonic cap is tested on a sodium edit at a 2.2 % deficit as well as the +8 L edit: at +8 L the
     volume and osmotic drives are 0, so thirstTarget 0 does not test the cap.
  6. H's bench runs after the arms (x141b ran one cost block before and one after its fast clock); one
     tick-rate window (H1) runs before them.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import glob
import json
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

PROFILE = "x15-thirst"
SESSION = ("Plan 4 acceptance 1, thirst and water live: first sight (A), ten game hours at rest (B), the "
           "auto-drink bracket (D), a 1 L drink (C), sodium and the plasma-sodium edges (F, F2), the kill cap "
           "(E), world water (I), sweat on a walk (G), cost (H): one boot of x15-thirst at DayLength 1")
ARTIFACT = "thirst.json"
USER = "admin"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STORE = "NutritionRevamp.players"
TW = "TKX_ThirstWatch"
TW_FIELDS = ("thirst", "fluidsMult", "core", "extAir", "bodyFluids", "wetness")
BODY_KEYS = ("fm", "lm", "sex", "met", "coldMult", "dmod", "rmod", "delta", "traitCarry", "dayIndex", "tac")
NUT_KEYS = ("epoch", "allReplete", "lastAgeH", "ironGrade", "vitDClinical", "lastDayIndex")
REC_KEYS = ([f"{USER}.fluids", f"{USER}.acute", f"{USER}.stomach.buffer", f"{USER}.stomach.bulk",
             f"{USER}.stomachFill", f"{USER}.firstSeen"]
            + [f"{USER}.body.{k}" for k in BODY_KEYS] + [f"{USER}.nutrients.{k}" for k in NUT_KEYS])
QUICK_KEYS = [f"{USER}.fluids.autoDrop", f"{USER}.fluids.water", f"{USER}.fluids.viewPct",
              f"{USER}.fluids.thirstTarget", f"{USER}.stomach.buffer.water", f"{USER}.nutrients.lastAgeH"]
INTAKE = "NutritionRevamp.server.intake.stats"
COUNTERS = ("sips", "landed", "worldSips", "failures", "eats", "cancels")
MIRROR_KEYS = ("nutrients_epoch", "fluids_dehydPct", "fluids_naPlasma", "fluids_thirstTarget", "acute_caf",
               "acute_bac", "acute_g", "acute_bg", "acute_awakeH", "acute_debtH", "acute_iu",
               "acute_refeedRisk", "stomachFill", "lastSeen")
CANTEEN = "Base.CanteenMilitaryFull"
BOTTLE = "Base.WaterBottle"
COLA = "Base.Pop2"
A_WINDOW_S = 60
A_POLL_EVERY = 4.0
B_HOURS = 10.0
B_WALL_CAP_S = 440
B_POLL_EVERY = 8.0
B_TW_S = 20
D_TW_S = 20
D_FAST_S, D_SLOW_S = 25, 15
C_START_WATER = -400
C_POLL_S, C_POLL_EVERY = 150, 3.0
F_POLL_S, F_POLL_EVERY = 150, 4.0
F2_HOLD_S = 6
F2_WATER = 8000
F2_NA = -1000
F2_DEFICIT = 0.022
E_DEFICIT = 0.09
I_DEFICIT = 0.025
E_HOLD_S = 6
I_WINDOW_S = 45
G_WALK_S, G_POLL_EVERY = 60, 3.0
WALK_DX = 20
TICK_S = 10
BENCH_N = 100000
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
DONE_WAIT_S = 15.0
MIRROR_WAIT_S = 6.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE|NutritionRevamp.*(fail|error)")
LUAERR_LIMIT = 40


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


# ---------------------------------------------------------------- the record, the stats, the mirror
def rec(tag):
    """One witness.moddata call: the fluids and acute tables, the stomach buffer, the body and nutrient
    scalars -- all read on one server tick."""
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(REC_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "worldAge": a.get("worldAge"),
           "missing": a.get("missing"), "truncatedAt": a.get("truncatedAt"), "error": a.get("error")}
    fl = vals.get(f"{USER}.fluids")
    row["fluids"] = fl if isinstance(fl, dict) else None
    ac = vals.get(f"{USER}.acute")
    row["acute"] = ac if isinstance(ac, dict) else None
    bu = vals.get(f"{USER}.stomach.buffer")
    row["buffer"] = bu if isinstance(bu, dict) else None
    row["bulk"] = to_num(vals.get(f"{USER}.stomach.bulk"))
    row["stomachFill"] = to_num(vals.get(f"{USER}.stomachFill"))
    row["firstSeen"] = to_num(vals.get(f"{USER}.firstSeen"))
    row["body"] = {k: vals.get(f"{USER}.body.{k}") for k in BODY_KEYS}
    row["nutrients"] = {k: vals.get(f"{USER}.nutrients.{k}") for k in NUT_KEYS}
    out["records"].append(row)
    return row


def quick(tag):
    r = step(tag, server, "witness.moddata", f"global:{STORE} " + " ".join(QUICK_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    return {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
            "autoDrop": to_num(vals.get(QUICK_KEYS[0])), "water": to_num(vals.get(QUICK_KEYS[1])),
            "viewPct": to_num(vals.get(QUICK_KEYS[2])), "thirstTarget": to_num(vals.get(QUICK_KEYS[3])),
            "bufferWater": to_num(vals.get(QUICK_KEYS[4])), "lastAgeH": to_num(vals.get(QUICK_KEYS[5]))}


STAT_KEYS = ("thirst", "hunger", "moodles", "moving", "running", "asleep", "worldAge", "mult", "endurance")


def stats_pair(tag):
    rc = step(f"{tag}_sc", client, "stats.get", "")
    rs = step(f"{tag}_ss", server, "stats.get", USER)
    c_, s_ = ack(rc), ack(rs)
    p = {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "client": {k: c_.get(k) for k in STAT_KEYS}, "server": {k: s_.get(k) for k in STAT_KEYS}}
    out["stats_pairs"].append(p)
    return p


def counters(tag):
    return {c: gv(server, f"{INTAKE}.{c}", f"{tag}_cnt_{c}") for c in COUNTERS}


def probe(tag):
    a = ack(step(tag, server, "autodrink.probe", USER))
    return {"tag": tag, "wall": wall(), "thirst": to_num(a.get("thirst")), "autoDrink": a.get("autoDrink"),
            "item": a.get("item"), "litres": to_num(a.get("litres")), "fluid": a.get("fluid"),
            "containers": a.get("containers"), "ok": a.get("ok"), "reason": a.get("reason")}


def mirror_check(tag):
    """A fresh client request, the wait for its answer, the client's keys, then the server record."""
    before = gv(client, "NutritionRevamp.client.received", f"{tag}_recv0")
    req = ack(step(f"{tag}_req", client, "bench.global", "NutritionRevamp.client.requestMirror 1"))
    after, waited = before, 0.0
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


def svar(tag, value):
    a = ack(step(tag, server, "sandbox.var", f"NR.DeficienciesCanKill {value}"))
    row = {"tag": tag, "value": value, "wall": wall(), "ack": a,
           "options_kill": None}
    time.sleep(1.5)
    row["options_kill"] = gv(server, "NutritionRevamp.server.options.deficienciesCanKill", f"{tag}_opt")
    out["edits"].append(row)
    return row


# ---------------------------------------------------------------- the ThirstWatch window
def tw_status(tag):
    r = step(tag, server, "witness.moddata", f"global:{TW} status samples windowMs arm")
    return (ack(r).get("values") or {})


def tw_reset(tag):
    for f in TW_FIELDS:
        step(f"{tag}_rn_{f}", server, "globalmoddata.set", f"{TW} n_{f} 0")
        step(f"{tag}_ra_{f}", server, "globalmoddata.set", f"{TW} absent_{f} reset")
    return {"reset": list(TW_FIELDS), "wall": wall()}


def tw_arm(tag, seconds):
    r = step(f"{tag}_arm", server, "globalmoddata.set", f"{TW} arm {seconds}")
    arm_wall = r["wall_after"]
    armed_seen = None
    end = wall() + 8.0
    while wall() < end:
        s = tw_status(f"{tag}_armchk")
        if s.get("status") == "armed":
            armed_seen = wall()
            break
        time.sleep(0.3)
    return {"arm_wall": arm_wall, "armed_seen_wall": armed_seen, "seconds": seconds}


def parse_raw(s):
    d = {}
    for part in str(s).split(" "):
        if "=" in part:
            k, v = part.split("=", 1)
            n = to_num(v)
            d[k] = n if n is not None else v
    return d


def tw_collect(tag, arm):
    end = arm["arm_wall"] + arm["seconds"] + DONE_WAIT_S
    done = None
    while wall() < end:
        s = tw_status(f"{tag}_donechk")
        if s.get("status") == "done":
            done = s
            break
        time.sleep(1.0)
    keys = ["samples", "windowMs", "status"]
    for f in TW_FIELDS:
        keys += [f"first_{f}", f"last_{f}", f"min_{f}", f"max_{f}", f"n_{f}", f"absent_{f}"]
    vals = {}
    for j in range(0, len(keys), 30):
        r = step(f"{tag}_scal{j}", server, "witness.moddata", f"global:{TW} " + " ".join(keys[j:j + 30]))
        vals.update(ack(r).get("values") or {})
    raws = {}
    for j in range(1, 51, 25):
        r = step(f"{tag}_raw{j}", server, "witness.moddata",
                 f"global:{TW} " + " ".join(f"raw_{i}" for i in range(j, j + 25)))
        raws.update(ack(r).get("values") or {})
    raw = [parse_raw(raws[f"raw_{i}"]) for i in range(1, 51) if raws.get(f"raw_{i}") is not None]
    samples = to_num(vals.get("samples"))
    if samples is not None:
        raw = raw[:int(samples)]
    fields = {f: {"first": to_num(vals.get(f"first_{f}")), "last": to_num(vals.get(f"last_{f}")),
                  "min": to_num(vals.get(f"min_{f}")), "max": to_num(vals.get(f"max_{f}")),
                  "n": to_num(vals.get(f"n_{f}")), "absent": vals.get(f"absent_{f}")} for f in TW_FIELDS}
    return {"done": done, "samples": samples, "windowMs": to_num(vals.get("windowMs")),
            "status": vals.get("status"), "fields": fields, "raw": raw}


# ---------------------------------------------------------------- spawns, walks, cost
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


def mass(r):
    fm, lm = fnum(r, "body", "fm"), fnum(r, "body", "lm")
    return None if fm is None or lm is None else fm + lm


# ---------------------------------------------------------------- phases
def phase_S0_A():
    P = out["phases"]
    S0 = P["S0"] = {}
    S0["first"] = rec("A_first")
    S0["sentinels"] = {n: gv(server, n, f"s0_{n}") for n in ("TKX_ThirstWatch_Installed", "NR_IntakeDrink_Installed",
                                                               "NR_IntakeWorld_Installed")}
    S0["options"] = {k: gv(server, f"NutritionRevamp.server.options.{k}", f"s0_opt_{k}")
                     for k in ("mode", "onsetSpeed", "deficienciesCanKill", "excessEffectsOn", "balanceBonus", "nutritionOn")}
    S0["nutrients_server"] = {k: gv(server, f"NutritionRevamp.server.nutrients.{k}", f"s0_nut_{k}")
                              for k in ("lastError", "sleepDisabled")}
    S0["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"s0_ns_{k}")
                             for k in ("minutes", "errors", "players", "noBody", "heals")}
    S0["probe0"] = probe("s0_probe")
    S0["counters"] = counters("s0")
    S0["stats"] = stats_pair("s0")
    persist()
    A = P["A"] = {"polls": []}
    A["pre"] = tw_reset("A")
    A["arm"] = tw_arm("A", A_WINDOW_S)
    end = A["arm"]["arm_wall"] + A_WINDOW_S
    i = 0
    while wall() < end - 1.0:
        t_s = wall()
        A["polls"].append({"i": i, "rec": rec(f"A_p{i}")["tag"], "stats": stats_pair(f"A_p{i}")})
        i += 1
        rest = A_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    A["watch"] = tw_collect("A", A["arm"])
    A["mirror"] = mirror_check("A_mirror")
    A["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"A_ns_{k}")
                            for k in ("minutes", "errors", "players", "noBody", "heals")}
    A["lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "A_lastError")
    persist()


def phase_H1():
    out["phases"]["H1"] = {"tick": tick_rate("H1")}


def created_age():
    first = (out["phases"].get("S0") or {}).get("first") or {}
    return fnum(first, "acute", "mass90ageH")


def phase_B():
    B = out["phases"]["B"] = {"polls": [], "mirror": []}
    c0 = created_age()
    B["created"] = c0
    t_start = wall()
    i = 0
    last = None
    while wall() - t_start < B_WALL_CAP_S:
        t_s = wall()
        r = rec(f"B_p{i}")
        last = r
        B["polls"].append({"i": i, "rec": r["tag"], "stats": stats_pair(f"B_p{i}")})
        if i == 18:
            B["mirror"].append(mirror_check("B_mirror_mid"))
        i += 1
        persist()
        la = fnum(r, "nutrients", "lastAgeH")
        if c0 is not None and la is not None and la >= c0 + B_HOURS:
            break
        rest = B_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    B["end_rec"] = last["tag"] if last else None
    B["mirror"].append(mirror_check("B_mirror_end"))
    B["tw_pre"] = tw_reset("Btw")
    B["tw_arm"] = tw_arm("Btw", B_TW_S)
    B["tw_recs"] = []
    end = B["tw_arm"]["arm_wall"] + B_TW_S
    while wall() < end - 1.0:
        B["tw_recs"].append(quick(f"Btw_q{len(B['tw_recs'])}"))
        time.sleep(1.5)
    B["tw_stats"] = stats_pair("Btw_end")
    B["watch"] = tw_collect("Btw", B["tw_arm"])
    persist()


def phase_D():
    D = out["phases"]["D"] = {"fast": [], "slow": []}
    D["before"] = rec("D_before")["tag"]
    D["probe_before"] = probe("D_probe_before")
    D["counters_before"] = counters("D_before")
    D["pre"] = tw_reset("D")
    D["arm"] = tw_arm("D", D_TW_S)
    D["fill_wall"] = wall()
    D["fill"] = ack(step("D_fill", server, "fluid.fill", f"{USER} {CANTEEN} Water 0.9"))
    end = wall() + D_FAST_S
    i = 0
    while wall() < end:
        q = quick(f"D_q{i}")
        q["probe"] = probe(f"D_q{i}_probe")
        D["fast"].append(q)
        i += 1
    D["watch"] = tw_collect("D", D["arm"])
    end = wall() + D_SLOW_S
    i = 0
    while wall() < end:
        q = quick(f"D_s{i}")
        q["probe"] = probe(f"D_s{i}_probe")
        D["slow"].append(q)
        i += 1
        time.sleep(1.5)
    D["after"] = rec("D_after")["tag"]
    D["counters_after"] = counters("D_after")
    D["stats_after"] = stats_pair("D_after")
    D["empty"] = ack(step("D_empty", server, "fluid.fill", f"{USER} {CANTEEN} Water 0"))
    D["probe_empty"] = probe("D_probe_empty")
    persist()


def phase_C():
    C = out["phases"]["C"] = {"polls": []}
    C["before_edit"] = rec("C_before_edit")["tag"]
    C["edit"] = setpath("C_water", "fluids.water", C_START_WATER)
    time.sleep(2.0)
    C["after_edit"] = rec("C_after_edit")["tag"]
    C["stats_after_edit"] = stats_pair("C_after_edit")
    C["spawn"] = spawn(BOTTLE, "C")
    C["probe_spawned"] = probe("C_probe_spawned")
    C["server_litres_spawned"] = litres("C_sl_spawned", server, BOTTLE)
    C["fill"] = ack(step("C_fill", server, "fluid.fill", f"{USER} {BOTTLE} Water 1.0"))
    C["server_litres_filled"] = litres("C_sl_filled", server, BOTTLE)
    C["client_litres_filled"] = litres("C_cl_filled", client, BOTTLE)
    C["counters_before"] = counters("C_before")
    C["before"] = rec("C_before")["tag"]
    C["drink_wall"] = wall()
    C["drink"] = ack(step("C_drink", client, "drink.action", f"{BOTTLE} 1"))
    end = wall() + C_POLL_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"C_p{i}")["tag"]}
        if i % 3 == 0:
            p["stats"] = stats_pair(f"C_p{i}")
        if i % 5 == 0:
            p["server_litres"] = litres(f"C_p{i}_sl", server, BOTTLE)
            p["counters"] = counters(f"C_p{i}")
        C["polls"].append(p)
        i += 1
        persist()
        rest = C_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    C["after"] = rec("C_after")["tag"]
    C["counters_after"] = counters("C_after")
    C["probe_after"] = probe("C_probe_after")
    C["mirror"] = mirror_check("C_mirror")
    persist()


def phase_F():
    F = out["phases"]["F"] = {"polls": []}
    F["spawn"] = spawn(COLA, "F")
    F["server_litres"] = litres("F_sl", server, COLA)
    F["counters_before"] = counters("F_before")
    F["before"] = rec("F_before")["tag"]
    F["drink_wall"] = wall()
    F["drink"] = ack(step("F_drink", client, "drink.action", f"{COLA} 1"))
    end = wall() + F_POLL_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"F_p{i}")["tag"]}
        if i % 5 == 0:
            p["counters"] = counters(f"F_p{i}")
            p["server_litres"] = litres(f"F_p{i}_sl", server, COLA)
        F["polls"].append(p)
        i += 1
        persist()
        rest = F_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    F["after"] = rec("F_after")["tag"]
    F["counters_after"] = counters("F_after")
    F["probe_after"] = probe("F_probe_after")
    persist()


def hold(key, seconds, every=0.6):
    rows = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        r = rec(f"{key}_h{i}")
        rows.append(r["tag"])
        i += 1
        time.sleep(every)
    return rows


def phase_F2():
    F2 = out["phases"]["F2"] = {}
    pre = rec("F2_pre")
    F2["pre"] = pre["tag"]
    w = mass(pre)
    na0 = fnum(pre, "fluids", "na")
    F2["mass"] = w
    F2["na_pre"] = na0
    F2["a_edit"] = setpath("F2a_water", "fluids.water", F2_WATER)
    F2["a_holds"] = hold("F2a", F2_HOLD_S)
    F2["a_stats"] = stats_pair("F2a_end")
    wv = round(-F2_DEFICIT * w * 1000, 3) if w else -1600
    F2["b_edit_na"] = setpath("F2b_na", "fluids.na", F2_NA)
    F2["b_edit_water"] = setpath("F2b_water", "fluids.water", wv)
    F2["b_holds"] = hold("F2b", F2_HOLD_S)
    F2["b_stats"] = stats_pair("F2b_end")
    if na0 is not None:
        F2["restore_na"] = setpath("F2_restore_na", "fluids.na", na0)
    persist()


def phase_E():
    E = out["phases"]["E"] = {}
    pre = rec("E_pre")
    E["pre"] = pre["tag"]
    w = mass(pre) or 80.0
    E["mass"] = w
    E["probe_pre"] = probe("E_probe_pre")
    E["off"] = svar("E_off", "false")
    E["edit"] = setpath("E_water", "fluids.water", round(-E_DEFICIT * w * 1000, 3))
    E["off_holds"] = hold("E_off", E_HOLD_S)
    E["off_stats"] = stats_pair("E_off_end")
    E["on"] = svar("E_on", "true")
    E["on_holds"] = hold("E_on", E_HOLD_S)
    E["on_stats"] = stats_pair("E_on_end")
    E["restore"] = setpath("E_restore", "fluids.water", round(-I_DEFICIT * w * 1000, 3))
    time.sleep(2.0)
    E["after"] = rec("E_after")["tag"]
    persist()


def phase_I():
    I = out["phases"]["I"] = {"polls": []}
    I["before"] = rec("I_before")["tag"]
    I["stats_before"] = stats_pair("I_before")
    I["counters_before"] = counters("I_before")
    I["probe_before"] = probe("I_probe_before")
    I["pre"] = tw_reset("I")
    I["arm"] = tw_arm("I", I_WINDOW_S)
    I["take_wall"] = wall()
    I["take"] = ack(step("I_take", client, "water.take", USER))
    end = I["arm"]["arm_wall"] + I_WINDOW_S
    i = 0
    while wall() < end - 1.0:
        p = {"i": i, "rec": rec(f"I_p{i}")["tag"], "stats": stats_pair(f"I_p{i}")}
        if i % 3 == 0:
            p["counters"] = counters(f"I_p{i}")
        I["polls"].append(p)
        i += 1
        time.sleep(1.5)
    I["watch"] = tw_collect("I", I["arm"])
    I["after"] = rec("I_after")["tag"]
    I["counters_after"] = counters("I_after")
    I["stop"] = ack(step("I_stop", client, "player.stop", ""))
    persist()


def phase_G():
    G = out["phases"]["G"] = {"polls": [], "walks": []}
    G["stop0"] = ack(step("G_stop0", client, "player.stop", ""))
    G["before"] = rec("G_before")["tag"]
    state = {"dir": 1, "n": 0}

    def go():
        dx = WALK_DX * state["dir"]
        state["dir"] = -state["dir"]
        state["n"] += 1
        a = ack(step(f"G_walk{state['n']}", client, "player.walk", f"{dx} 0"))
        G["walks"].append({"n": state["n"], "dx": dx, "wall": wall(), "queued": a.get("queued"),
                           "error": a.get("error"), "clientMoving": a.get("clientMoving")})
    go()
    G["walk_start"] = wall()
    end = wall() + G_WALK_S
    i = 0
    while wall() < end:
        t_s = wall()
        p = {"i": i, "rec": rec(f"G_p{i}")["tag"]}
        mv = ack(step(f"G_p{i}_mv", client, "witness.chain", "isPlayerMoving"))
        p["client_moving"] = mv.get("value")
        if str(mv.get("value")).lower() != "true":
            go()
        if i % 4 == 0:
            p["stats"] = stats_pair(f"G_p{i}")
        G["polls"].append(p)
        i += 1
        rest = G_POLL_EVERY - (wall() - t_s)
        if rest > 0:
            time.sleep(rest)
    G["stop"] = ack(step("G_stop", client, "player.stop", ""))
    time.sleep(8.0)
    G["after"] = rec("G_after")["tag"]
    persist()


def phase_H():
    H = out["phases"]["H"] = {"bench": [], "tick": []}
    for i in range(3):
        H["bench"].append(ack(step(f"H_bench{i}", server, "bench.global",
                                   f"NutritionRevamp.bench_fast {BENCH_N}", timeout=60)))
    H["tick"] = [tick_rate("Ha"), tick_rate("Hb")]
    persist()


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["mirror"] = mirror_check("Z_mirror")
    Z["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                            for k in ("minutes", "errors", "players", "noBody", "heals")}
    Z["lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "Z_lastError")
    Z["intake_lastError"] = gv(server, "NutritionRevamp.server.intake.lastError", "Z_in_lastError")
    Z["counters"] = counters("Z")


MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|nutrients: .* failed")


def mod_error(after):
    """The first-boot rule: a NutritionRevamp error in the server's error lines, a mod lastError or error
    count, or a parked client stops the arms; the evidence is what the run returns."""
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
    for name, fn in (("S0_A", phase_S0_A), ("H1", phase_H1), ("B", phase_B), ("D", phase_D), ("C", phase_C),
                     ("F", phase_F), ("F2", phase_F2), ("E", phase_E), ("I", phase_I), ("G", phase_G),
                     ("H", phase_H), ("Z", phase_Z)):
        run_phase(name, fn)
        why = mod_error(name)
        if why:
            out["abort"] = {"after": name, "why": why}
            note(f"mod error after {name}: the arms stop here (first-boot rule)")
            persist()
            break


# ---------------------------------------------------------------- the kernel offline (lupa)
class Kernel:
    def __init__(self):
        import lupa.lua51 as lua51
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        files = [os.path.join(SHARED, "NR_Core.lua")] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))
        loader = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")
        for p in files:
            with open(p, encoding="utf-8") as fh:
                loader(fh.read(), "@" + os.path.basename(p))()
        self.K = self.rt.globals().NutritionRevamp.kernel
        self.F = self.K.fluids

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = v
        return t

    def view(self, water, na, k, lm, w, pendingG=0.0, canKill=True):
        f = self.table({"water": water, "na": na, "k": k})
        dehyd = self.F.dehydPct(f, w, 0)
        view = self.F.dehydPct(f, w, pendingG)
        c = self.F.conc(f, lm)
        nap = self.F.naPlasma(c)
        return {"dehydPct": dehyd, "viewPct": view, "c": c, "naPlasma": nap,
                "thirstTarget": self.F.thirstTarget(view, c, nap, canKill)}

    def rest(self, sex, lm, w, minutes):
        """Basal loss alone over `minutes` from a fresh record.fluids (MET 1, no cold, no ethanol)."""
        ai = self.F.AI[int(sex)]
        water = -ai / 1440 * minutes
        na = -(ai / 1440 * minutes) / 1000 * self.F.BASAL_NA_FRAC * self.F.OSM_REF
        r = self.view(water, na, 0.0, lm, w)
        r.update({"water": water, "na": na, "minutes": minutes, "basalGPerMin": ai / 1440,
                  "basalNaPerMin": ai / 1440 / 1000 * self.F.BASAL_NA_FRAC * self.F.OSM_REF})
        return r

    def sweat_lh(self, met, thermo, sweatK):
        return self.F.sweatLh(met, thermo, sweatK)


# ---------------------------------------------------------------- grading
def recs_by_tag():
    return {r["tag"]: r for r in out["records"]}


def series(tags, R, sub, key):
    return [(R[t]["wall"], fnum(R[t], sub, key)) for t in tags if t in R]


def stats_series(polls):
    rows = []
    for p in polls:
        s = p.get("stats")
        if not s:
            continue
        rows.append({"tag": s["tag"], "server_thirst": to_num(s["server"].get("thirst")),
                     "client_thirst": to_num(s["client"].get("thirst")),
                     "server_moodle_thirst": (s["server"].get("moodles") or {}).get("thirst"),
                     "client_moodle_thirst": (s["client"].get("moodles") or {}).get("thirst"),
                     "server_wall": s["server_wall"], "client_wall": s["client_wall"]})
    return rows


def grade_all():
    P, R, S = out["phases"], recs_by_tag(), out["summaries"]
    try:
        K = Kernel()
        S["kernel_loaded"] = True
    except Exception as e:                     # noqa: BLE001
        K = None
        S["kernel_loaded"] = f"{type(e).__name__}: {e}"
    first = (P.get("S0") or {}).get("first") or {}
    sex, lm, fm = fnum(first, "body", "sex"), fnum(first, "body", "lm"), fnum(first, "body", "fm")
    w = (lm + fm) if lm is not None and fm is not None else None
    c0 = created_age()
    S["subject"] = {"sex": sex, "lm": lm, "fm": fm, "w": w, "created": c0,
                    "firstSeen": first.get("firstSeen"), "first_lastAgeH": fnum(first, "nutrients", "lastAgeH")}

    def pred_at(r):
        la = fnum(r, "nutrients", "lastAgeH")
        if K is None or None in (sex, lm, w, c0, la):
            return None
        return K.rest(sex, lm, w, (la - c0) * 60)

    def cmp(r):
        p = pred_at(r)
        if p is None:
            return None
        fl = r.get("fluids") or {}
        return {"tag": r["tag"], "minutes": p["minutes"],
                "water": [to_num(fl.get("water")), p["water"]], "na": [to_num(fl.get("na")), p["na"]],
                "dehydPct": [to_num(fl.get("dehydPct")), p["dehydPct"]], "c": [to_num(fl.get("c")), p["c"]],
                "naPlasma": [to_num(fl.get("naPlasma")), p["naPlasma"]],
                "thirstTarget": [to_num(fl.get("thirstTarget")), p["thirstTarget"]]}

    # A
    A = P.get("A") or {}
    a_rows = [cmp(R[p["rec"]]) for p in A.get("polls") or [] if p["rec"] in R]
    S["A"] = {"first": cmp(first) if first else None, "polls": a_rows,
              "first_fluids": first.get("fluids"), "epoch": fnum(first, "nutrients", "epoch"),
              "allReplete": (first.get("nutrients") or {}).get("allReplete"),
              "frozen": (first.get("acute") or {}).get("frozen"),
              "thirst_pairs": stats_series(A.get("polls") or []),
              "watch_thirst": ((A.get("watch") or {}).get("fields") or {}).get("thirst"),
              "targets": series([p["rec"] for p in A.get("polls") or []], R, "fluids", "thirstTarget")}
    grade("A", "water = -AI/1440 x minutes since creation; THIRST = thirstTarget on the server at every tick; "
               "frozen true", S["A"], "see_raw", "THIRST off the target by more than one slow stamp")
    # B
    B = P.get("B") or {}
    b_tags = [p["rec"] for p in B.get("polls") or []]
    S["B"] = {"cmp": [cmp(R[t]) for t in b_tags if t in R],
              "thirst_pairs": stats_series(B.get("polls") or []),
              "body": [(R[t]["wall"], {k: R[t]["body"].get(k) for k in ("dmod", "rmod", "delta", "traitCarry", "met",
                                                                         "coldMult")},
                        fnum(R[t], "acute", "iu"), fnum(R[t], "fluids", "dehydPct")) for t in b_tags if t in R],
              "watch_thirst": ((B.get("watch") or {}).get("fields") or {}).get("thirst"),
              "tw_targets": [(q["wall"], q["thirstTarget"]) for q in B.get("tw_recs") or []]}
    if K is not None and sex is not None:
        S["B"]["hand_80kg_male"] = K.rest(1, 65.6, 80.0, 600)
    grade("B", "the kernel's rest prediction for this subject at every poll; THIRST = view both sides; moodle 1 "
               "then 2", {"last": S["B"]["cmp"][-1] if S["B"]["cmp"] else None}, "see_raw",
          "water off -AI/1440 x minutes; THIRST off the view")
    # D
    D = P.get("D") or {}
    S["D"] = {"fill": D.get("fill"),
              "fast": [(q["wall"], q["autoDrop"], q["bufferWater"], q["water"], q["viewPct"], q["thirstTarget"],
                        (q.get("probe") or {}).get("litres"), (q.get("probe") or {}).get("thirst"), q["lastAgeH"])
                       for q in D.get("fast") or []],
              "slow": [(q["wall"], q["autoDrop"], q["bufferWater"], q["water"], q["viewPct"], q["thirstTarget"],
                        (q.get("probe") or {}).get("litres"), (q.get("probe") or {}).get("thirst"), q["lastAgeH"])
                       for q in D.get("slow") or []],
              "watch_thirst": ((D.get("watch") or {}).get("fields") or {}).get("thirst"),
              "counters": [D.get("counters_before"), D.get("counters_after")]}
    grade("D", "a sip of 2 x THIRST litres; autoDrop = litres/2; buffer +2 x drop x 1000 g at the next slow "
               "minute; no sip while pending", {"n_fast": len(S["D"]["fast"])}, "see_raw",
          "litres move with autoDrop never > 0; a second sip while autoDrop > 0")
    # C, F, I: the landing series
    for key in ("C", "F", "I"):
        X = P.get(key) or {}
        tags = [p["rec"] for p in X.get("polls") or []]
        rows = []
        for t in tags:
            r = R.get(t)
            if not r:
                continue
            fl, bu = r.get("fluids") or {}, r.get("buffer") or {}
            rows.append({"wall": r["wall"], "lastAgeH": fnum(r, "nutrients", "lastAgeH"),
                         "water": to_num(fl.get("water")), "bufferWater": to_num(bu.get("water")),
                         "na": to_num(fl.get("na")), "bufferSodium": to_num(bu.get("sodium")),
                         "k": to_num(fl.get("k")), "dehydPct": to_num(fl.get("dehydPct")),
                         "viewPct": to_num(fl.get("viewPct")), "thirstTarget": to_num(fl.get("thirstTarget")),
                         "c": to_num(fl.get("c")), "naPlasma": to_num(fl.get("naPlasma"))})
        S[key] = {"series": rows, "thirst_pairs": stats_series(X.get("polls") or []),
                  "counters": [X.get("counters_before"), X.get("counters_after")]}
    grade("C", "buffer +1000 g; viewPct falls at once; dehydPct as absorbed; surplus cleared at 320 g/h",
          {"n": len(S["C"]["series"])}, "see_raw", "no landing")
    grade("F", "buffer sodium +12 mg; fluids.na = basal draw + absorbed/23", {"n": len(S["F"]["series"])},
          "see_raw", "no landing")
    grade("I", "buffer water up by at most 2 x THIRST litres; worldSips > 0", {"take": (P.get("I") or {}).get("take")},
          "see_raw", "no landing with the action queued")
    # F2, E: the edits
    for key, holds in (("F2", ("a_holds", "b_holds")), ("E", ("off_holds", "on_holds"))):
        X = P.get(key) or {}
        blk = {}
        for h in holds:
            rows = []
            for t in X.get(h) or []:
                r = R.get(t)
                if not r:
                    continue
                fl = r.get("fluids") or {}
                row = {"wall": r["wall"], "water": to_num(fl.get("water")), "na": to_num(fl.get("na")),
                       "k": to_num(fl.get("k")), "viewPct": to_num(fl.get("viewPct")), "c": to_num(fl.get("c")),
                       "naPlasma": to_num(fl.get("naPlasma")), "thirstTarget": to_num(fl.get("thirstTarget"))}
                if K is not None and lm is not None and w is not None and None not in (row["water"], row["na"], row["k"]):
                    bw = to_num((r.get("buffer") or {}).get("water")) or 0.0
                    row["kernel"] = K.view(row["water"], row["na"], row["k"], lm, w, bw, key != "E" or h == "on_holds")
                rows.append(row)
            blk[h] = rows
        S[key] = blk
    grade("F2", "+8 L: naPlasma per conc, thirstTarget 0; na -1000 at 2.2 %: naPlasma < 135, thirstTarget 0.11",
          {"n": {h: len(v) for h, v in S["F2"].items()}}, "see_raw", "a target above 0.11 under 135 mmol/L")
    grade("E", "off: 0.83 at 9 %; on: 1.0", {"n": {h: len(v) for h, v in S["E"].items()}}, "see_raw",
          "a target above 0.83 with the dial off")
    # G
    G = P.get("G") or {}
    rows = []
    for p in G.get("polls") or []:
        r = R.get(p["rec"])
        if not r:
            continue
        fl = r.get("fluids") or {}
        met = to_num(r["body"].get("met"))
        rows.append({"wall": r["wall"], "met": met, "client_moving": p.get("client_moving"),
                     "sweatLmin": to_num(fl.get("sweatLmin")), "sweat6h": to_num(fl.get("sweat6h")),
                     "loss6h": to_num(fl.get("loss6h")), "sweatActive": fl.get("sweatActive"),
                     "sweatK": to_num(fl.get("sweatK")),
                     "kernel_sweatLh": (K.sweat_lh(met, 1.0, to_num(fl.get("sweatK")) or 1.0)
                                        if K is not None and met is not None else None)})
    S["G"] = {"series": rows, "walks": G.get("walks")}
    grade("G", "sweat > 0 iff body.met > 3; sweatActive false in 60 s", {"n": len(rows)}, "see_raw", "none")
    # H
    H = P.get("H") or {}
    us = [to_num(b.get("usPerCall")) for b in H.get("bench") or []]
    tps = [t.get("ticksPerSecond") for t in (H.get("tick") or [])] + [((P.get("H1") or {}).get("tick") or {}).get("ticksPerSecond")]
    S["H"] = {"usPerCall": us, "ticksPerSecond": tps}
    grade("H", "bench_fast within 25 % of 3.06-3.40 us; tick rate within 5 % of 10.00-10.11", S["H"], "see_raw", "outside")


prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x151t-dry-run", None) if DRY_RUN else new_run_dir("x151t")
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
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_ThirstWatch"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {k: v for k, v in globals().items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
                  and isinstance(v, (int, float, str)) and k not in ("REPO", "SHARED", "LUA_DIR")},
    "deviations": [
        "Order A, B, D, C, F, F2, E, I, G, H: autoDrink drinks any non-empty container once THIRST > 0.1, so the "
        "bracket arm (D) runs first and C drinks from a pool set to -400 g by record edit.",
        "D's container is a server-only CanteenMilitaryFull made and filled (Water 0.9 L) by the server fluid.fill "
        "in one command, not a WaterBottle by inventory.add.",
        "C's WaterBottle is RCON-spawned (both sides hold it), refilled to Water 1.0 L by the server twin, and "
        "drunk by the client's drink.action, which the server runs on its own copy.",
        "Thirst levels are set by record edits (globalmoddata.setpath on NutritionRevamp.players admin.fluids.*), "
        "never by stats.setany.",
        "The hypotonic cap is also tested on a sodium edit (na -1000 at a 2.2 % deficit): at +8 L thirstTarget 0 "
        "does not test the cap.",
        "One tick-rate window before the arms (H1); the bench and two tick-rate windows after them (H).",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["a server-only canteen (emptied)", "an RCON WaterBottle", "an RCON Pop2",
                                        "the record's fluids edited (C, F2, E)", "the character walked (I, G)"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "summaries": {}, "stats_pairs": [],
    "records": [], "spawns": [], "edits": [], "mirror_checks": [], "phase_errors": {}, "mod_error_checks": [],
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
                         sandbox=prof.sandbox or None)
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec_fx)
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
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
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
