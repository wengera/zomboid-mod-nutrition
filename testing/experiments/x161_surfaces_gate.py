"""x161-surfaces -- Plan 5 Task 3, gate 1: the health, stat and body-part surfaces, live. ONE boot of
`x16-surfaces` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror at HEAD d2301d6 + TKX_StatWatch;
`Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game minute 0.625 s; `[server]`
SleepAllowed and SleepNeeded true). The run id prefix is `x161s`, the artifact `surfaces.json`. The mod
runs underneath: its handler writes the nine stats it owns (THIRST, STRESS, ANGER, HUNGER, FATIGUE,
IDLENESS, MORALE, FITNESS; ENDURANCE only asleep), so every arm here targets a stat or a surface the
handler does NOT own.

THE X IDS (platform briefing s 9): X75 POISON, X76 FOOD_SICKNESS and the SICK level, X77
ReduceGeneralHealth's reach to the client, X78 syncBodyPart, X79 the infection write, X80 the
regeneration constants, X81 TEMPERATURE forcing, X88 the panic and unhappiness deltas; X35's running arm
is the existing #2082.

WHERE STATE IS READ. Stats: `stats.all` on each side (the client's is its copy of the 1 Hz push); the
per-tick server series is TKX_StatWatch (armed by `globalmoddata.set TKX_StatWatch arm <s>`, read with
`witness.moddata global:TKX_StatWatch`; first_/last_/min_/max_ are full-precision numbers, raw_1..raw_60
the first 60 ticks at 3 decimals (TEMPERATURE and core at 2)). Health: `health.get` on each side.
Per-part fields: `bodypart.get` on each side, written with `bodypart.set` on the server. Every reply
carries the answering side's `wall` where the command returns one; the server and the client run on
one machine, so their `getTimestampMs` walls share a clock.

SCHEDULE (one boot, in this order, a mod-error check after each):
  S0   first sight: stats.all and stats.get both sides, health.get both, bodypart.get all both,
       regen.get, temp.core, the reduce-infection power, `foodtimer.set admin 0` (the FOOD_EATEN term
       would speed the poison decay and add 0.015 x mult to the regeneration accumulator), the ini.
  H    cost: `tick.rate 10` once on the server.
  X77  health.get both; `health.reduce admin 10`; client then server health.get alternately for 12 s;
       `health.add admin 10`; both sides once more after 3 s.
  X78  part 0 (Hand_L). StatWatch window 18 s with the BLEEDING counters at -1; `bodypart.set admin 0
       bleedingTime 20` WITHOUT sync; client/server bodypart.get 0 alternately for 10 s; then the same
       write WITH `sync`; reads for 4 s; clear (bleedingTime 0 sync, bleeding false).
  X79  part 1 (Hand_R; the list index checked by getType). scratchTime 10, infectedWound true,
       woundInfectionLevel 1. (a) 20 s of server reads: vanilla. (b) 20 s of the fold: each step reads
       the level L and writes L + 1.3 x (L - the last written value). (c) level 1 again, alcoholLevel 1
       through witness.chain's setter hop, 20 s of reads. Clear all four fields.
  X80  every part to health 100 (SetHealth), then part 0 to 70; regen.get; window A 30 s of server reads
       at the defaults; `regen.set admin 0.001 0.00065 0.0004 0.01`; part 0 back to 70; regen.get after
       ~3.2 s (5 game minutes); window B 30 s; regen.get; restore the defaults and part 0.
  X81  temp.core; StatWatch 12 s; once armed temp.core and `stats.setany admin TEMPERATURE <core+0.4>`;
       temp.core at +1, +3 and +8 s; the window read.
  X88  PANIC and UNHAPPINESS 0; `globalmoddata.set TKX_StatWatch delta 0.5` then arm 40 s; client and
       server stats.all pairs through the window; reads at +2, +10 and +25 s after it; both back to 0.
  X75  FOOD_SICKNESS 0, POISON 0, foodtimer 0. (a) window 60 s, POISON 8 written once armed, stats.all
       pairs every ~4 s. (b) FOOD_SICKNESS 10 and POISON 25, then a 10 s window with the POISON/SICK
       counters at -1 (SICK < 1 throughout). (c) counters at -1, a 60 s window, FOOD_SICKNESS 24 once
       armed; server health.get every ~1 s; at health <= 70 or 60 s after the write POISON 0 and
       FOOD_SICKNESS 0. Every part back to 100.
  X76  POISON 0. (a) FOOD_SICKNESS 30 and a 30 s window, pairs at its start and middle. (b) 60, pairs.
       (c) counters at -1, a 30 s window, 95 once armed; server health.get every ~1 s; at health <= 70
       or 30 s FOOD_SICKNESS 0. Every part back to 100.
  X35  ENDURANCE 0.6 on the server; StatWatch 60 s; `player.walk 20 0 run` re-issued each way every 20 s;
       client then server stats.all alternately for 60 s; player.stop.
  Z    errors, counters, a last health/regen/stats read.

PREDICTIONS (written before the run). M is the multiplier units per game hour at DayLength 1: #2951's
INTOXICATION decay 7.5599 per game hour over the 0.0042 x mult law gives M = 1799.98, so 1800, i.e. 48
per wall second at ~10 ticks per second and ~4.8 per tick. The driver also records its own mult and
ticks per second so M is recomputed from this run.
  X75 (#2361, #0520, #2358, #2359): POISON 8 decays at 0.001 x M = 1.8 per game hour (FOOD_EATEN 0);
      FOOD_SICKNESS rises at 0.001 x (2 + round(P/10)) x M = 5.4 per game hour while 5 <= P < 15; no
      POISON tag while P <= 10. At P ~24-25 and FOOD_SICKNESS 10-12 (SICK value < 0.25) the POISON tag
      never fires in (b). In (c) FOOD_SICKNESS crosses 25 about 5 s after the write (7.2 per game hour
      at round(P/10) = 2) and the POISON tag then fires every tick at 0.0035 x min(P/10, 3) x mult_tick
      (~0.041 per tick), overall health falling ~0.41 per wall second.
  X76 (#3018, #2369, #2356): FOOD_SICKNESS 30 at POISON 0 decays 0.0015 x M = 2.7 per game hour;
      the SICK value is FOOD_SICKNESS/100 + SICKNESS, so 30/60/95 sit at levels 1/2/4 on each side's
      copy; at 95 the SICK tag fires every tick at 0.0165 x mult_tick (~0.079), health ~0.79 per wall s.
  X77 (#2346, #0564): the server's overall health falls at once; the client's follows within one 1 Hz
      push if the player-stats packet's body-damage main fields carry it, and never if they do not.
  X78 (#2626, #2607, #2365): the client's bleedingTime stays at its old value for the 10 s no-sync
      arm and reads the written value within one hop after the sync; the server's falls 2e-5 x M =
      0.036 per game hour (unbandaged); BLEEDING fires per tick at 0.2857 x damageScaler x bt/10 x mult.
  X79 (BodyPart.DamageUpdate @1016-@1309 L307-L352): (a) +1e-5 x M = 0.018 per game hour; (b) the
      written total ~2.3 x (a), less the vanilla progress the read-to-write gap overwrites; (c) with
      alcohol > 0 the level falls 2e-4 x M = 0.36 per game hour and the vanilla rise does not run.
  X80 (#2353, #2354, #3020): tier 0 adds 0.002 x M = 3.6 health per game hour to the one damaged part;
      halved, 1.8; the slope ratio 0.5 +- 5 %; regen.get after 5 game minutes still 0.001 in session.
  X81 (#2373, #3024): the update after the single write lerps the core halfway: max_core ~ core + 0.2
      (+ one tick's heat delta). The held half is UNMEASURED this gate (no hold arm in the probe).
  X88 (#3013, #3014, #3016, #3033): the out-of-handler OnTick write survives each update (no updater
      overwrites either stat); per tick PANIC moves +0.5 - r with r = 0.06 x thirtyFPS (months 0) and
      UNHAPPINESS +0.5 until it saturates at 100; after the window PANIC falls and UNHAPPINESS does
      not (no passive decay); the client's copies equal a server value within one push.
  X35 (#2082, #0564): the client's ENDURANCE equals a server value at most one push old (lag <= ~1 s);
      the handler writes no awake endurance at d2301d6, so this reads VANILLA's awake write.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. No moodle level is read directly: no harness command reads the SICK, PANIC or UNHAPPY level
     (`stats.get`'s moodles map carries hungry, thirst, foodEaten, heavyLoad and endurance only), so each
     side's level is inferred from its stat copy (stats.all) and the #2369 thresholds.
  2. X79's treated window writes alcoholLevel through witness.chain's one-literal setter hop
     (`getBodyDamage.getBodyParts.get(1).setAlcoholLevel(1)`) because bodypart.set has no alcoholLevel
     setter; the list index is checked against the part's type first.
  3. X79's fold reads then writes in two bus calls about a second apart, not per game minute; the
     vanilla progress between the read and the write is overwritten and is accounted from each write
     reply's `before`.
  4. X81's held-target half is unmeasured (TKX_StatWatch has no hold arm, task-2 report).
  5. X88's delta is one value for both stats (the probe reads one `delta`), 0.5 per server tick,
     written out of the handler on OnTick, not in the handler path.
  6. X75's drain arm sets FOOD_SICKNESS to 24 so the SICK crossing lands inside the window; the SICK < 1
     control is its own 10 s window at FOOD_SICKNESS 10.
  7. X35 sets ENDURANCE 0.6 first so vanilla's awake regeneration moves the stat under the walk (the run
     flag never reaches the server, #0591/#2810).
  8. X80 damages one part through SetHealth with every other part at 100, so AddGeneralHealth's whole
     share lands on it.
  9. The StatWatch tag counters a window reads are written -1 before it, so -1 after it is "never fired".
 10. Health is restored between the lethal arms by SetHealth 100 on every part.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
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

PROFILE = "x16-surfaces"
SESSION = ("Plan 5 gate 1, the health, stat and body-part surfaces live: POISON (X75), FOOD_SICKNESS and the "
           "SICK level (X76), ReduceGeneralHealth's reach (X77), syncBodyPart (X78), the infection write (X79), "
           "the regeneration constants (X80), TEMPERATURE forcing (X81), panic and unhappiness deltas (X88), "
           "X35's running arm: one boot of x16-surfaces at DayLength 1")
ARTIFACT = "surfaces.json"
USER = "admin"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

SW = "TKX_StatWatch"
SW_FIELDS = ("poison", "food_sickness", "sickness", "panic", "unhappiness", "boredom", "stress",
             "temperature", "fatigue", "endurance", "intoxication", "core")
SW_TAGS = ("POISON", "SICK", "FALLDOWN", "BLEEDING", "HUNGRY", "THIRST", "HEAVYLOAD", "other")
SW_DONE_WAIT = 12.0
M_REF = 1800.0                 # #2951: 7.5599 / 0.0042
PART_BLEED, PART_INF, PART_REGEN = 0, 1, 0
BLEED_T, BLEED_NOSYNC_S, BLEED_SYNC_S = 20, 10.0, 4.0
INF_WIN_S, INF_K = 20.0, 1.3
REGEN_WIN_S = 30.0
REGEN_HALF = ("0.001", "0.00065", "0.0004", "0.01")
REGEN_DEF = ("0.002", "0.0013", "0.0008", "0.02")
TEMP_STEP = 0.4
X88_DELTA, X88_S = 0.5, 40
X75_A_S, X75_B_S, X75_C_S = 60, 10, 60
X76_A_S, X76_C_S = 30, 30
HEALTH_STOP = 70.0
HEALTH_GUARD = 55.0
X35_S = 60
TICK_S = 10

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE|NutritionRevamp.*(fail|error)")
LUAERR_LIMIT = 40
INI_RX = re.compile(r"^(SleepAllowed|SleepNeeded)=(.*)$")
MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|nutrients: .* failed")


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


def sleep_until(t):
    rest = t - wall()
    if rest > 0:
        time.sleep(rest)


# ---------------------------------------------------------------- reads and writes
def sall(tag, side):
    r = step(tag, side, "stats.all", USER if side is server else "")
    a = ack(r)
    st = a.get("stats") if isinstance(a.get("stats"), dict) else {}
    row = {"tag": tag, "side": "server" if side is server else "client", "wall": r["wall_before"],
           "wall_after": r["wall_after"], "sideWall": a.get("wall"), "worldAge": a.get("worldAge"),
           "mult": a.get("mult"), "stats": st}
    if not st:
        row["reply"] = r["ack"]
    out["stats_all"].append(row)
    return row


def sget(tag, side):
    r = step(tag, side, "stats.get", USER if side is server else "")
    a = ack(r)
    row = {"tag": tag, "side": "server" if side is server else "client", "wall": r["wall_before"],
           "sideWall": a.get("wall"), "worldAge": a.get("worldAge"), "mult": a.get("mult"),
           "moodles": a.get("moodles"), "foodTimer": a.get("foodTimer"), "asleep": a.get("asleep"),
           "moving": a.get("moving"), "running": a.get("running"), "hunger": a.get("hunger"),
           "thirst": a.get("thirst"), "endurance": a.get("endurance"), "fatigue": a.get("fatigue")}
    out["stats_get"].append(row)
    return row


def hget(tag, side):
    r = step(tag, side, "health.get", USER)
    a = ack(r)
    row = {"tag": tag, "side": "server" if side is server else "client", "wall": r["wall_before"],
           "wall_after": r["wall_after"], "overall": a.get("overall"), "health": a.get("health"),
           "parts": a.get("parts"), "ok": a.get("ok"), "reason": a.get("reason")}
    if not a:
        row["reply"] = r["ack"]
    out["health_reads"].append(row)
    return row


def bpget(tag, side, idx):
    r = step(tag, side, "bodypart.get", f"{USER} {idx}")
    a = ack(r)
    parts = a.get("parts") if isinstance(a.get("parts"), list) else []
    row = {"tag": tag, "side": "server" if side is server else "client", "wall": r["wall_before"],
           "wall_after": r["wall_after"], "idx": idx, "ok": a.get("ok"), "reason": a.get("reason"),
           "part": parts[0] if (parts and idx != "all") else None}
    if idx == "all":
        row["parts"] = parts
    if not a:
        row["reply"] = r["ack"]
    out["part_reads"].append(row)
    return row


def bpset(tag, idx, field, value, sync=False):
    args = f"{USER} {idx} {field} {value}" + (" sync" if sync else "")
    r = step(tag, server, "bodypart.set", args)
    a = ack(r)
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "idx": idx, "field": field,
           "value": value, "sync": sync, "ok": a.get("ok"), "before": a.get("before"), "after": a.get("after"),
           "synced": a.get("synced"), "mask": a.get("mask"), "reason": a.get("reason")}
    if not a:
        row["reply"] = r["ack"]
    out["part_writes"].append(row)
    return row


def setany(tag, stat, v):
    r = step(tag, server, "stats.setany", f"{USER} {stat} {v}")
    a = ack(r)
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "stat": stat,
           "ok": a.get("ok"), "requested": a.get("requested"), "before": a.get("before"), "after": a.get("after"),
           "reason": a.get("reason")}
    if not a:
        row["reply"] = r["ack"]
    out["stat_writes"].append(row)
    return row


def chain(tag, hop):
    r = step(tag, server, "witness.chain", f"{USER} {hop}")
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "ok": a.get("ok"), "value": a.get("value"),
            "failedAt": a.get("failedAt"), "error": a.get("error"), "reason": a.get("reason")}


def tcore(tag):
    r = step(tag, server, "temp.core", USER)
    a = ack(r)
    row = {"tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"]}
    for k in ("ok", "core", "setPoint", "heatDelta", "rateOfChange", "temperature", "reason"):
        row[k] = a.get(k)
    out["temp_reads"].append(row)
    return row


def regen_get(tag):
    a = ack(step(tag, server, "regen.get", USER))
    row = {"tag": tag, "wall": wall()}
    row.update({k: a.get(k) for k in ("ok", "standard", "reduced", "severe", "sleeping")})
    out["regen_reads"].append(row)
    return row


def regen_set(tag, vals):
    a = ack(step(tag, server, "regen.set", f"{USER} " + " ".join(vals)))
    row = {"tag": tag, "wall": wall(), "ok": a.get("ok"), "before": a.get("before"), "after": a.get("after"),
           "reason": a.get("reason")}
    out["regen_writes"].append(row)
    return row


def md_read(tag, scope, keys):
    vals, missing = {}, []
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        a = ack(step(f"{tag}_{j}", server, "witness.moddata", f"global:{scope} " + " ".join(ch)))
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
    return {"values": vals, "missing": missing, "wall": wall()}


def sw_status(tag):
    return ack(step(tag, server, "witness.moddata", f"global:{SW} status samples windowMs arm deltaUsed")).get(
        "values") or {}


def sw_reset_tags(tag, tags):
    for t in tags:
        step(f"{tag}_rd_{t}", server, "globalmoddata.set", f"{SW} dmg_{t} -1")
        step(f"{tag}_rs_{t}", server, "globalmoddata.set", f"{SW} dmgsum_{t} -1")
    return {"reset": list(tags), "to": -1, "wall": wall()}


def sw_arm(tag, seconds, delta=None):
    res = {"seconds": seconds, "delta": delta}
    if delta is not None:
        res["delta_set"] = ack(step(f"{tag}_delta", server, "globalmoddata.set", f"{SW} delta {delta}"))
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
    keys = ["samples", "windowMs", "status", "deltaUsed"]
    for f in SW_FIELDS:
        keys += [f"first_{f}", f"last_{f}", f"min_{f}", f"max_{f}", f"n_{f}", f"absent_{f}"]
    keys += [f"dmg_{t}" for t in SW_TAGS] + [f"dmgsum_{t}" for t in SW_TAGS]
    sc = md_read(f"{tag}_scal", SW, keys)
    raws = md_read(f"{tag}_raw", SW, [f"raw_{i}" for i in range(1, 61)])
    g = sc["values"]
    samples = to_num(g.get("samples"))
    raw_s, raw = [], []
    for i in range(1, 61):
        v = raws["values"].get(f"raw_{i}")
        if v is not None:
            raw_s.append(v)
            raw.append(parse_raw(v))
    flds = {f: {"first": to_num(g.get(f"first_{f}")), "last": to_num(g.get(f"last_{f}")),
                "min": to_num(g.get(f"min_{f}")), "max": to_num(g.get(f"max_{f}")),
                "n": to_num(g.get(f"n_{f}")), "absent": g.get(f"absent_{f}")} for f in SW_FIELDS}
    dmg = {t: {"count": to_num(g.get(f"dmg_{t}")), "sum": to_num(g.get(f"dmgsum_{t}"))} for t in SW_TAGS}
    res = {"done": done, "status": g.get("status"), "samples": samples, "windowMs": to_num(g.get("windowMs")),
           "deltaUsed": to_num(g.get("deltaUsed")), "fields": flds, "dmg": dmg, "raw_strings": raw_s, "raw": raw,
           "collected_wall": wall()}
    out["watches"].append({"tag": tag, "arm": arm, "result": res})
    return res


def all_parts_100(tag):
    rows = []
    for i in range(state.get("nparts") or 17):
        rows.append(bpset(f"{tag}_h100_{i}", i, "health", 100))
    return [{"idx": r["idx"], "ok": r["ok"], "before": r["before"], "after": r["after"], "reason": r["reason"]}
            for r in rows]


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


def overall(row):
    return to_num((row or {}).get("overall"))


# ---------------------------------------------------------------- phases
def phase_S0():
    S = out["phases"]["S0"] = {}
    S["stats_server"] = sall("S0_sall_s", server)["tag"]
    S["stats_client"] = sall("S0_sall_c", client)["tag"]
    S["get_server"] = sget("S0_sget_s", server)
    S["get_client"] = sget("S0_sget_c", client)
    S["health_server"] = hget("S0_h_s", server)["tag"]
    S["health_client"] = hget("S0_h_c", client)["tag"]
    ps = bpget("S0_parts_s", server, "all")
    pc = bpget("S0_parts_c", client, "all")
    state["nparts"] = len(ps.get("parts") or []) or 17
    S["nparts_server"] = len(ps.get("parts") or [])
    S["nparts_client"] = len(pc.get("parts") or [])
    S["regen"] = regen_get("S0_regen")
    S["temp"] = tcore("S0_temp")
    S["reduceInfectionPower"] = chain("S0_rip", "getReduceInfectionPower")
    S["infectionGrowthRate"] = chain("S0_igr", "getBodyDamage.getInfectionGrowthRate")
    S["foodtimer"] = ack(step("S0_foodtimer", server, "foodtimer.set", f"{USER} 0"))
    S["get_server_after_ft"] = sget("S0_sget_s2", server)
    S["ini"] = read_ini()
    S["mod_version"] = {"server": gv(server, "NutritionRevamp.version", "S0_ver_s"),
                        "client": gv(client, "NutritionRevamp.version", "S0_ver_c")}


def phase_H():
    out["phases"]["H"] = {"tick": tick_rate("H")}


def phase_X77():
    X = out["phases"]["X77"] = {"polls": []}
    X["pre_client"] = hget("X77_pre_c", client)["tag"]
    X["pre_server"] = hget("X77_pre_s", server)["tag"]
    r = step("X77_reduce", server, "health.reduce", f"{USER} 10")
    X["reduce"] = ack(r)
    X["reduce_wall"] = r["wall_after"]
    end = wall() + 12.0
    i = 0
    while wall() < end:
        c = hget(f"X77_p{i}_c", client)
        s = hget(f"X77_p{i}_s", server)
        X["polls"].append({"i": i, "c": c["tag"], "s": s["tag"], "c_overall": overall(c), "s_overall": overall(s),
                           "c_wall": c["wall"], "s_wall": s["wall"]})
        i += 1
        persist()
    a = step("X77_add", server, "health.add", f"{USER} 10")
    X["add"] = ack(a)
    X["add_wall"] = a["wall_after"]
    time.sleep(3.0)
    X["post_client"] = hget("X77_post_c", client)["tag"]
    X["post_server"] = hget("X77_post_s", server)["tag"]


def phase_X78():
    X = out["phases"]["X78"] = {"nosync": [], "sync": []}
    X["pre_server"] = bpget("X78_pre_s", server, PART_BLEED)["tag"]
    X["pre_client"] = bpget("X78_pre_c", client, PART_BLEED)["tag"]
    X["reset"] = sw_reset_tags("X78", ("BLEEDING",))
    X["arm"] = sw_arm("X78", 18)
    X["health_pre"] = hget("X78_h_pre", server)["tag"]
    w = bpset("X78_set_nosync", PART_BLEED, "bleedingTime", BLEED_T)
    X["write_nosync"] = w
    end = wall() + BLEED_NOSYNC_S
    i = 0
    while wall() < end:
        c = bpget(f"X78_n{i}_c", client, PART_BLEED)
        s = bpget(f"X78_n{i}_s", server, PART_BLEED)
        X["nosync"].append({"i": i, "c": c["tag"], "s": s["tag"]})
        i += 1
        persist()
    w2 = bpset("X78_set_sync", PART_BLEED, "bleedingTime", BLEED_T, sync=True)
    X["write_sync"] = w2
    end = wall() + BLEED_SYNC_S
    i = 0
    while wall() < end:
        c = bpget(f"X78_y{i}_c", client, PART_BLEED)
        s = bpget(f"X78_y{i}_s", server, PART_BLEED)
        X["sync"].append({"i": i, "c": c["tag"], "s": s["tag"]})
        i += 1
        persist()
    X["clear_time"] = bpset("X78_clear_t", PART_BLEED, "bleedingTime", 0, sync=True)
    X["clear_flag"] = bpset("X78_clear_f", PART_BLEED, "bleeding", "false")
    X["health_post"] = hget("X78_h_post", server)["tag"]
    X["watch"] = sw_collect("X78", X["arm"])
    X["post_server"] = bpget("X78_post_s", server, PART_BLEED)["tag"]
    X["post_client"] = bpget("X78_post_c", client, PART_BLEED)["tag"]


def inf_read(tag):
    s = bpget(tag, server, PART_INF)
    p = s.get("part") or {}
    return {"tag": tag, "wall": s["wall"], "wall_after": s["wall_after"], "level": to_num(p.get("woundInfectionLevel")),
            "infected": p.get("infectedWound"), "scratch": to_num(p.get("scratchTime")),
            "alcohol": to_num(p.get("alcoholLevel")), "health": to_num(p.get("health"))}


def phase_X79():
    X = out["phases"]["X79"] = {"a": [], "b": [], "c": []}
    X["type_check"] = chain("X79_type", f"getBodyDamage.getBodyParts.get({PART_INF}).getType")
    X["pre"] = inf_read("X79_pre")
    X["set_scratch"] = bpset("X79_scratch", PART_INF, "scratchTime", 10)
    X["set_infected"] = bpset("X79_infected", PART_INF, "infectedWound", "true")
    X["set_level"] = bpset("X79_level_a", PART_INF, "woundInfectionLevel", 1)
    end = wall() + INF_WIN_S
    i = 0
    while wall() < end:
        X["a"].append(inf_read(f"X79_a{i}"))
        i += 1
        time.sleep(0.5)
    persist()
    last_written = X["a"][-1]["level"] if X["a"] else None
    end = wall() + INF_WIN_S
    i = 0
    while wall() < end:
        r = inf_read(f"X79_b{i}")
        L = r["level"]
        row = {"read": r}
        if L is not None and last_written is not None:
            dv = L - last_written
            target = L + INF_K * dv
            w = bpset(f"X79_bw{i}", PART_INF, "woundInfectionLevel", repr(target))
            row.update({"dv": dv, "target": target, "write": {"wall": w["wall"], "wall_after": w["wall_after"],
                                                              "before": w["before"], "after": w["after"],
                                                              "ok": w["ok"]}})
            a_ = to_num(w["after"])
            last_written = a_ if a_ is not None else target
        X["b"].append(row)
        i += 1
        persist()
    X["b_end"] = inf_read("X79_b_end")
    X["set_level_c"] = bpset("X79_level_c", PART_INF, "woundInfectionLevel", 1)
    X["alcohol_set"] = chain("X79_alc", f"getBodyDamage.getBodyParts.get({PART_INF}).setAlcoholLevel(1)")
    X["alcohol_check"] = chain("X79_alc_chk", f"getBodyDamage.getBodyParts.get({PART_INF}).getAlcoholLevel")
    end = wall() + INF_WIN_S
    i = 0
    while wall() < end:
        X["c"].append(inf_read(f"X79_c{i}"))
        i += 1
        time.sleep(0.5)
    X["clear_alcohol"] = chain("X79_alc0", f"getBodyDamage.getBodyParts.get({PART_INF}).setAlcoholLevel(0)")
    X["clear_infected"] = bpset("X79_clr_inf", PART_INF, "infectedWound", "false")
    X["clear_level"] = bpset("X79_clr_lvl", PART_INF, "woundInfectionLevel", 0)
    X["clear_scratch"] = bpset("X79_clr_scr", PART_INF, "scratchTime", 0)
    X["post"] = inf_read("X79_post")


def regen_read(tag):
    s = bpget(tag, server, PART_REGEN)
    p = s.get("part") or {}
    return {"tag": tag, "wall": s["wall"], "wall_after": s["wall_after"], "health": to_num(p.get("health"))}


def phase_X80():
    X = out["phases"]["X80"] = {"A": [], "B": []}
    X["parts100"] = all_parts_100("X80")
    X["sget"] = sget("X80_sget", server)
    X["regen0"] = regen_get("X80_regen0")
    X["set70_A"] = bpset("X80_70A", PART_REGEN, "health", 70)
    end = wall() + REGEN_WIN_S
    i = 0
    while wall() < end:
        X["A"].append(regen_read(f"X80_A{i}"))
        i += 1
        time.sleep(0.4)
    persist()
    X["half"] = regen_set("X80_half", REGEN_HALF)
    X["set70_B"] = bpset("X80_70B", PART_REGEN, "health", 70)
    X["half_wall"] = wall()
    sleep_until(X["half_wall"] + 3.2)
    X["regen_5min"] = regen_get("X80_regen5")
    X["sget_B"] = sget("X80_sgetB", server)
    end = X["half_wall"] + REGEN_WIN_S
    i = 0
    while wall() < end:
        X["B"].append(regen_read(f"X80_B{i}"))
        i += 1
        time.sleep(0.4)
    X["regen_end"] = regen_get("X80_regen_end")
    X["restore"] = regen_set("X80_restore", REGEN_DEF)
    X["restore_part"] = bpset("X80_100", PART_REGEN, "health", 100)


def phase_X81():
    X = out["phases"]["X81"] = {}
    X["pre"] = tcore("X81_pre")
    X["arm"] = sw_arm("X81", 12)
    c = tcore("X81_at")
    X["at"] = c
    core = to_num(c.get("core"))
    if core is None:
        note("X81: no core read; the single write is skipped (unmeasured)")
        X["write"] = None
    else:
        X["target"] = core + TEMP_STEP
        X["write"] = setany("X81_write", "TEMPERATURE", repr(core + TEMP_STEP))
    base = wall()
    for dt in (1.0, 3.0, 8.0):
        sleep_until(base + dt)
        X[f"post_{int(dt)}s"] = tcore(f"X81_post{int(dt)}")
    X["watch"] = sw_collect("X81", X["arm"])


def phase_X88():
    X = out["phases"]["X88"] = {"pairs": [], "after": []}
    X["zero"] = [setany("X88_p0", "PANIC", 0), setany("X88_u0", "UNHAPPINESS", 0)]
    X["pre_s"] = sall("X88_pre_s", server)["tag"]
    X["pre_c"] = sall("X88_pre_c", client)["tag"]
    X["arm"] = sw_arm("X88", X88_S, delta=X88_DELTA)
    start = X["arm"].get("armed_seen_wall") or X["arm"]["arm_wall"]
    i = 0
    while wall() < start + X88_S:
        c = sall(f"X88_p{i}_c", client)
        s = sall(f"X88_p{i}_s", server)
        X["pairs"].append({"i": i, "c": c["tag"], "s": s["tag"]})
        i += 1
        persist()
        if wall() > start + 12:
            time.sleep(2.0)
    X["watch"] = sw_collect("X88", X["arm"])
    end_w = wall()
    for dt in (2.0, 10.0, 25.0):
        sleep_until(end_w + dt)
        s = sall(f"X88_after{int(dt)}_s", server)
        c = sall(f"X88_after{int(dt)}_c", client)
        X["after"].append({"dt": dt, "s": s["tag"], "c": c["tag"]})
    X["restore"] = [setany("X88_p0b", "PANIC", 0), setany("X88_u0b", "UNHAPPINESS", 0)]


def drain_watch(X, key, seconds_cap, zero_fn):
    """Server health every ~1 s until health <= HEALTH_STOP or the cap; then zero_fn()."""
    start = wall()
    X[key] = []
    stopped = None
    while wall() < start + seconds_cap:
        h = hget(f"{key}_{len(X[key])}", server)
        o = overall(h)
        X[key].append({"wall": h["wall"], "overall": o})
        persist()
        if o is not None and o <= HEALTH_STOP:
            stopped = {"why": "health", "wall": wall(), "overall": o}
            break
        time.sleep(0.5)
    if stopped is None:
        stopped = {"why": "cap", "wall": wall()}
    X[key + "_stop"] = stopped
    X[key + "_zero"] = zero_fn()
    X[key + "_after"] = hget(f"{key}_after", server)["tag"]


def phase_X75():
    X = out["phases"]["X75"] = {"a_pairs": []}
    X["zero"] = [setany("X75_fs0", "FOOD_SICKNESS", 0), setany("X75_p0", "POISON", 0)]
    X["foodtimer"] = ack(step("X75_ft", server, "foodtimer.set", f"{USER} 0"))
    X["sget"] = sget("X75_sget", server)
    X["h_pre"] = hget("X75_h_pre", server)["tag"]
    X["reset_a"] = sw_reset_tags("X75a", ("POISON", "SICK"))
    X["arm_a"] = sw_arm("X75a", X75_A_S)
    X["write_a"] = setany("X75_p8", "POISON", 8)
    start = X["write_a"]["wall"]
    i = 0
    while wall() < start + X75_A_S - 2:
        s = sall(f"X75a_{i}_s", server)
        c = sall(f"X75a_{i}_c", client)
        X["a_pairs"].append({"i": i, "s": s["tag"], "c": c["tag"]})
        i += 1
        persist()
        time.sleep(3.0)
    X["h_a"] = hget("X75_h_a", server)["tag"]
    X["watch_a"] = sw_collect("X75a", X["arm_a"])
    X["post_a_s"] = sall("X75a_post_s", server)["tag"]
    # (b) the SICK < 1 control
    X["write_b"] = [setany("X75_fs10", "FOOD_SICKNESS", 10), setany("X75_p25", "POISON", 25)]
    X["reset_b"] = sw_reset_tags("X75b", ("POISON", "SICK"))
    X["arm_b"] = sw_arm("X75b", X75_B_S)
    X["b_s"] = sall("X75b_s", server)["tag"]
    X["watch_b"] = sw_collect("X75b", X["arm_b"])
    X["post_b_s"] = sall("X75b_post_s", server)["tag"]
    X["h_b"] = hget("X75_h_b", server)["tag"]
    # (c) the drain
    X["reset_c"] = sw_reset_tags("X75c", ("POISON", "SICK"))
    X["arm_c"] = sw_arm("X75c", X75_C_S)
    X["write_c"] = setany("X75_fs24", "FOOD_SICKNESS", 24)
    X["c_s0"] = sall("X75c_s0", server)["tag"]
    drain_watch(X, "c_health", X75_C_S - 3,
                lambda: [setany("X75_p0c", "POISON", 0), setany("X75_fs0c", "FOOD_SICKNESS", 0)])
    X["c_s1"] = sall("X75c_s1", server)["tag"]
    X["c_c1"] = sall("X75c_c1", client)["tag"]
    X["watch_c"] = sw_collect("X75c", X["arm_c"])
    X["restore"] = all_parts_100("X75")
    X["h_end"] = hget("X75_h_end", server)["tag"]


def phase_X76():
    X = out["phases"]["X76"] = {"pairs": {}}
    X["zero_p"] = setany("X76_p0", "POISON", 0)
    X["write_30"] = setany("X76_fs30", "FOOD_SICKNESS", 30)
    X["arm_a"] = sw_arm("X76a", X76_A_S)
    X["pairs"]["30"] = [{"s": sall("X76_30_s0", server)["tag"], "c": sall("X76_30_c0", client)["tag"]}]
    sleep_until((X["arm_a"].get("armed_seen_wall") or X["arm_a"]["arm_wall"]) + X76_A_S / 2.0)
    X["pairs"]["30"].append({"s": sall("X76_30_s1", server)["tag"], "c": sall("X76_30_c1", client)["tag"]})
    X["watch_a"] = sw_collect("X76a", X["arm_a"])
    X["post_a_s"] = sall("X76a_post_s", server)["tag"]
    X["write_60"] = setany("X76_fs60", "FOOD_SICKNESS", 60)
    time.sleep(2.0)
    X["pairs"]["60"] = [{"s": sall(f"X76_60_s{k}", server)["tag"], "c": sall(f"X76_60_c{k}", client)["tag"]}
                        for k in range(2)]
    X["reset_c"] = sw_reset_tags("X76c", ("POISON", "SICK"))
    X["arm_c"] = sw_arm("X76c", X76_C_S)
    X["write_95"] = setany("X76_fs95", "FOOD_SICKNESS", 95)
    X["pairs"]["95"] = [{"s": sall("X76_95_s0", server)["tag"], "c": sall("X76_95_c0", client)["tag"]}]
    drain_watch(X, "c_health", X76_C_S - 4, lambda: [setany("X76_fs0", "FOOD_SICKNESS", 0)])
    X["pairs"]["0"] = [{"s": sall("X76_0_s", server)["tag"], "c": sall("X76_0_c", client)["tag"]}]
    X["watch_c"] = sw_collect("X76c", X["arm_c"])
    X["restore"] = all_parts_100("X76")
    X["h_end"] = hget("X76_h_end", server)["tag"]


def phase_X35():
    X = out["phases"]["X35"] = {"pairs": [], "walks": []}
    X["write"] = setany("X35_e06", "ENDURANCE", 0.6)
    X["arm"] = sw_arm("X35", X35_S)
    start = wall()
    dirs = [20, -20, 20]
    nxt = 0
    i = 0
    while wall() < start + X35_S - 2:
        if nxt < len(dirs) and wall() >= start + 20 * nxt:
            r = step(f"X35_walk{nxt}", client, "player.walk", f"{dirs[nxt]} 0 run")
            X["walks"].append({"wall": r["wall_before"], "ack": r["ack"]})
            nxt += 1
        c = sall(f"X35_{i}_c", client)
        s = sall(f"X35_{i}_s", server)
        X["pairs"].append({"i": i, "c": c["tag"], "s": s["tag"]})
        i += 1
        if i % 10 == 0:
            X.setdefault("moving", []).append(sget(f"X35_mv{i}", server))
            persist()
    X["stop"] = ack(step("X35_stop", client, "player.stop", ""))
    X["watch"] = sw_collect("X35", X["arm"])


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["nutrients_stats"] = {k: gv(server, f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                            for k in ("minutes", "errors", "players", "noBody", "days")}
    Z["lastError"] = gv(server, "NutritionRevamp.server.nutrients.lastError", "Z_lastError")
    Z["intake_lastError"] = gv(server, "NutritionRevamp.server.intake.lastError", "Z_in_lastError")
    Z["kinetics_lastError"] = gv(server, "NutritionRevamp.server.kinetics.lastError", "Z_kin_lastError")
    Z["health_s"] = hget("Z_h_s", server)["tag"]
    Z["health_c"] = hget("Z_h_c", client)["tag"]
    Z["regen"] = regen_get("Z_regen")
    Z["stats_s"] = sall("Z_s", server)["tag"]
    Z["stats_c"] = sall("Z_c", client)["tag"]


def mod_error(after):
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    le = gv(server, "NutritionRevamp.server.nutrients.lastError", f"chk_{after}_nle")
    ne = gv(server, "NutritionRevamp.server.nutrients.stats.errors", f"chk_{after}_nerr")
    if le is not None or (to_num(ne) or 0) > 0:
        why.append({"nutrients_lastError": le, "nutrients_errors": ne})
    if clients and "lua_error" in getattr(clients[0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    h = hget(f"chk_{after}_h", server)
    o = overall(h)
    if o is not None and o < HEALTH_GUARD:
        why.append({"health_guard": o})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "found": why, "health": o})
    return why


def body():
    for name, fn in (("S0", phase_S0), ("H", phase_H), ("X77", phase_X77), ("X78", phase_X78),
                     ("X79", phase_X79), ("X80", phase_X80), ("X81", phase_X81), ("X88", phase_X88),
                     ("X75", phase_X75), ("X76", phase_X76), ("X35", phase_X35), ("Z", phase_Z)):
        run_phase(name, fn)
        why = mod_error(name)
        if why:
            out["abort"] = {"after": name, "why": why}
            note(f"mod error or health guard after {name}: the arms stop here")
            persist()
            break


# ---------------------------------------------------------------- summaries (derived, never the grade)
def lsq(pts):
    """Least-squares slope of (x, y) points; None under 2 points."""
    pts = [(x, y) for x, y in pts if isinstance(x, (int, float)) and isinstance(y, (int, float))]
    n = len(pts)
    if n < 2:
        return None
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    return {"n": n, "slope": sum((x - mx) * (y - my) for x, y in pts) / sxx, "x0": pts[0][0], "x1": pts[-1][0],
            "y0": pts[0][1], "y1": pts[-1][1]}


def by_tag(rows):
    return {r["tag"]: r for r in rows}


def summarise():
    S = out["summaries"]
    P = out["phases"]
    sa = by_tag(out["stats_all"])
    srv_rows = [r for r in out["stats_all"] if r["side"] == "server"
                and isinstance(r.get("worldAge"), (int, float)) and isinstance(r.get("sideWall"), (int, float))]
    # game hours per wall second, the session's own clock
    if len(srv_rows) >= 2:
        a, b = srv_rows[0], srv_rows[-1]
        gh_per_s = (b["worldAge"] - a["worldAge"]) / ((b["sideWall"] - a["sideWall"]) / 1000.0)
        mults = [r["mult"] for r in srv_rows if isinstance(r.get("mult"), (int, float))]
        S["clock"] = {"game_h_per_wall_s": gh_per_s, "wall_s_per_game_h": 1.0 / gh_per_s if gh_per_s else None,
                      "mult_min": min(mults) if mults else None, "mult_max": max(mults) if mults else None,
                      "mult_mean": sum(mults) / len(mults) if mults else None, "n": len(srv_rows)}
        tps = (P.get("H") or {}).get("tick", {}).get("ticksPerSecond")
        if isinstance(tps, (int, float)) and mults:
            S["clock"]["M_run"] = (sum(mults) / len(mults)) * tps / gh_per_s
    gh = (S.get("clock") or {}).get("game_h_per_wall_s")

    def per_game_h(slope_per_s):
        return slope_per_s / gh if (slope_per_s is not None and gh) else None

    def stat_slope(tags, key):
        pts = []
        for t in tags:
            r = sa.get(t)
            if r and isinstance(r.get("worldAge"), (int, float)):
                v = (r.get("stats") or {}).get(key)
                if isinstance(v, (int, float)):
                    pts.append((r["worldAge"], v))
        return lsq(pts)

    def watch_slope(w, f):
        if not w:
            return None
        fl = (w.get("fields") or {}).get(f) or {}
        ms = w.get("windowMs")
        if fl.get("first") is None or fl.get("last") is None or not ms:
            return None
        per_s = (fl["last"] - fl["first"]) / (ms / 1000.0)
        return {"first": fl["first"], "last": fl["last"], "windowMs": ms, "per_wall_s": per_s,
                "per_game_h": per_game_h(per_s), "samples": w.get("samples")}

    try:
        X = P.get("X75") or {}
        S["X75"] = {
            "a_poison_watch": watch_slope(X.get("watch_a"), "poison"),
            "a_fs_watch": watch_slope(X.get("watch_a"), "food_sickness"),
            "a_poison_statsall": stat_slope([p["s"] for p in X.get("a_pairs", [])], "Poison"),
            "a_fs_statsall": stat_slope([p["s"] for p in X.get("a_pairs", [])], "FoodSickness"),
            "a_dmg": (X.get("watch_a") or {}).get("dmg"),
            "b_dmg": (X.get("watch_b") or {}).get("dmg"),
            "b_fs_max": (((X.get("watch_b") or {}).get("fields") or {}).get("food_sickness") or {}).get("max"),
            "c_dmg": (X.get("watch_c") or {}).get("dmg"),
            "c_health": lsq([(h["wall"], h["overall"]) for h in X.get("c_health", [])]),
            "c_stop": X.get("c_health_stop"),
            "pred_per_game_h": {"poison_decay": 0.001 * M_REF, "fs_rise_round1": 0.003 * M_REF,
                                "fs_rise_round2": 0.004 * M_REF},
        }
    except Exception as e:                     # noqa: BLE001
        S["X75_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X76") or {}
        S["X76"] = {"a_fs_watch": watch_slope(X.get("watch_a"), "food_sickness"),
                    "c_dmg": (X.get("watch_c") or {}).get("dmg"),
                    "c_health": lsq([(h["wall"], h["overall"]) for h in X.get("c_health", [])]),
                    "c_stop": X.get("c_health_stop"),
                    "pairs": {k: [{"s": (sa.get(p["s"]) or {}).get("stats", {}).get("FoodSickness"),
                                   "c": (sa.get(p["c"]) or {}).get("stats", {}).get("FoodSickness"),
                                   "s_sickness": (sa.get(p["s"]) or {}).get("stats", {}).get("Sickness"),
                                   "c_sickness": (sa.get(p["c"]) or {}).get("stats", {}).get("Sickness")}
                                  for p in v] for k, v in (X.get("pairs") or {}).items()},
                    "pred_per_game_h": {"fs_decay": -0.0015 * M_REF}}
    except Exception as e:                     # noqa: BLE001
        S["X76_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X78") or {}
        pr = by_tag(out["part_reads"])
        srv = [pr[t] for t in [p["s"] for p in X.get("nosync", [])] if t in pr]
        pts = [((r["wall"] + r["wall_after"]) / 2.0, to_num((r.get("part") or {}).get("bleedingTime"))) for r in srv]
        sl = lsq(pts)
        S["X78"] = {"server_nosync_slope": sl,
                    "server_nosync_per_game_h": per_game_h(sl["slope"]) if sl else None,
                    "client_nosync": [to_num(((pr.get(p["c"]) or {}).get("part") or {}).get("bleedingTime"))
                                      for p in X.get("nosync", [])],
                    "client_sync": [{"wall": (pr.get(p["c"]) or {}).get("wall"),
                                     "bt": to_num(((pr.get(p["c"]) or {}).get("part") or {}).get("bleedingTime"))}
                                    for p in X.get("sync", [])],
                    "dmg": (X.get("watch") or {}).get("dmg"),
                    "pred_per_game_h": -2e-5 * M_REF}
    except Exception as e:                     # noqa: BLE001
        S["X78_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X79") or {}
        a = lsq([((r["wall"] + r["wall_after"]) / 2.0, r["level"]) for r in X.get("a", [])])
        c = lsq([((r["wall"] + r["wall_after"]) / 2.0, r["level"]) for r in X.get("c", [])])
        b_rows = X.get("b", [])
        b_pts = [((row["read"]["wall"] + row["read"]["wall_after"]) / 2.0, row["read"]["level"]) for row in b_rows]
        if X.get("b_end"):
            b_pts.append(((X["b_end"]["wall"] + X["b_end"]["wall_after"]) / 2.0, X["b_end"]["level"]))
        b = lsq(b_pts)
        v_obs = sum(row.get("dv") or 0.0 for row in b_rows if "dv" in row)
        gap = sum((to_num(row["write"]["before"]) - row["read"]["level"]) for row in b_rows
                  if "write" in row and to_num(row["write"]["before"]) is not None and row["read"]["level"] is not None)
        S["X79"] = {"a": a, "a_per_game_h": per_game_h(a["slope"]) if a else None,
                    "b": b, "b_per_game_h": per_game_h(b["slope"]) if b else None,
                    "b_over_a": (b["slope"] / a["slope"]) if (a and b and a["slope"]) else None,
                    "b_vanilla_between_writes": v_obs, "b_overwritten_gap": gap,
                    "b_expected_ratio_given_gap": (2.3 * v_obs / (v_obs + gap)) if (v_obs + gap) else None,
                    "c": c, "c_per_game_h": per_game_h(c["slope"]) if c else None,
                    "pred_per_game_h": {"a": 1e-5 * M_REF, "c": -2e-4 * M_REF}}
    except Exception as e:                     # noqa: BLE001
        S["X79_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X80") or {}
        A = lsq([((r["wall"] + r["wall_after"]) / 2.0, r["health"]) for r in X.get("A", [])])
        B = lsq([((r["wall"] + r["wall_after"]) / 2.0, r["health"]) for r in X.get("B", [])])
        S["X80"] = {"A": A, "A_per_game_h": per_game_h(A["slope"]) if A else None,
                    "B": B, "B_per_game_h": per_game_h(B["slope"]) if B else None,
                    "ratio": (B["slope"] / A["slope"]) if (A and B and A["slope"]) else None,
                    "pred_per_game_h": {"A": 0.002 * M_REF, "B": 0.001 * M_REF}}
    except Exception as e:                     # noqa: BLE001
        S["X80_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X81") or {}
        w = X.get("watch") or {}
        core_at = to_num((X.get("at") or {}).get("core"))
        mx = ((w.get("fields") or {}).get("core") or {}).get("max")
        S["X81"] = {"core_at_write": core_at, "target": X.get("target"),
                    "max_core": mx, "max_temperature": ((w.get("fields") or {}).get("temperature") or {}).get("max"),
                    "max_core_minus_core_at": (mx - core_at) if (mx is not None and core_at is not None) else None,
                    "fraction_of_gap": ((mx - core_at) / TEMP_STEP) if (mx is not None and core_at is not None) else None,
                    "setPoint": (X.get("at") or {}).get("setPoint"), "held": "unmeasured (no hold arm)"}
    except Exception as e:                     # noqa: BLE001
        S["X81_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X88") or {}
        w = X.get("watch") or {}
        raw = w.get("raw") or []
        inc_p = [raw[k + 1].get("panic") - raw[k].get("panic") for k in range(len(raw) - 1)
                 if isinstance(raw[k].get("panic"), float) and isinstance(raw[k + 1].get("panic"), float)]
        inc_u = [raw[k + 1].get("unhappiness") - raw[k].get("unhappiness") for k in range(len(raw) - 1)
                 if isinstance(raw[k].get("unhappiness"), float) and isinstance(raw[k + 1].get("unhappiness"), float)]
        pairs = [{"s_panic": (sa.get(p["s"]) or {}).get("stats", {}).get("Panic"),
                  "c_panic": (sa.get(p["c"]) or {}).get("stats", {}).get("Panic"),
                  "s_unh": (sa.get(p["s"]) or {}).get("stats", {}).get("Unhappiness"),
                  "c_unh": (sa.get(p["c"]) or {}).get("stats", {}).get("Unhappiness"),
                  "c_wall": (sa.get(p["c"]) or {}).get("sideWall"), "s_wall": (sa.get(p["s"]) or {}).get("sideWall")}
                 for p in X.get("pairs", [])]
        after = [{"dt": a_["dt"], "s_panic": (sa.get(a_["s"]) or {}).get("stats", {}).get("Panic"),
                  "s_unh": (sa.get(a_["s"]) or {}).get("stats", {}).get("Unhappiness"),
                  "c_panic": (sa.get(a_["c"]) or {}).get("stats", {}).get("Panic"),
                  "c_unh": (sa.get(a_["c"]) or {}).get("stats", {}).get("Unhappiness")} for a_ in X.get("after", [])]
        S["X88"] = {"raw_inc_panic": inc_p, "raw_inc_unh": inc_u,
                    "raw_inc_panic_mean": (sum(inc_p) / len(inc_p)) if inc_p else None,
                    "raw_inc_unh_mean": (sum(inc_u) / len(inc_u)) if inc_u else None,
                    "fields": {k: (w.get("fields") or {}).get(k) for k in ("panic", "unhappiness", "boredom", "stress")},
                    "pairs": pairs, "after": after}
    except Exception as e:                     # noqa: BLE001
        S["X88_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X35") or {}
        rows_c, rows_s = [], []
        for p in X.get("pairs", []):
            c = sa.get(p["c"]) or {}
            s = sa.get(p["s"]) or {}
            if isinstance(c.get("sideWall"), (int, float)) and isinstance((c.get("stats") or {}).get("Endurance"), (int, float)):
                rows_c.append((c["sideWall"], c["stats"]["Endurance"]))
            if isinstance(s.get("sideWall"), (int, float)) and isinstance((s.get("stats") or {}).get("Endurance"), (int, float)):
                rows_s.append((s["sideWall"], s["stats"]["Endurance"]))
        rows_s.sort()
        lags = []
        for tw, cv in rows_c:
            prior = [(sw_, sv) for sw_, sv in rows_s if sw_ <= tw]
            hit = None
            # the latest server read at or before the client read whose value brackets the client value
            for k in range(len(rows_s) - 1):
                (w0, v0), (w1, v1) = rows_s[k], rows_s[k + 1]
                if w1 > tw:
                    break
                if (v0 - cv) * (v1 - cv) <= 0 and v1 != v0:
                    hit = w0 + (cv - v0) / (v1 - v0) * (w1 - w0)
            exact = [sw_ for sw_, sv in prior if sv == cv]
            lags.append({"client_wall": tw, "client": cv, "lag_ms_interp": (tw - hit) if hit is not None else None,
                         "lag_ms_exact": (tw - exact[-1]) if exact else None,
                         "server_prev": prior[-1][1] if prior else None})
        S["X35"] = {"lags": lags, "n_client": len(rows_c), "n_server": len(rows_s),
                    "server_series": lsq([(w_ / 1000.0, v) for w_, v in rows_s])}
    except Exception as e:                     # noqa: BLE001
        S["X35_error"] = f"{type(e).__name__}: {e}"
    try:
        X = P.get("X77") or {}
        S["X77"] = {"polls": X.get("polls"), "reduce": X.get("reduce"), "reduce_wall": X.get("reduce_wall")}
    except Exception as e:                     # noqa: BLE001
        S["X77_error"] = f"{type(e).__name__}: {e}"
    for ph in ("X75", "X76", "X77", "X78", "X79", "X80", "X81", "X88", "X35"):
        grade(ph, "see the PREDICTIONS block of the driver docstring", {"summary_key": ph}, "see_raw",
              "see the PREDICTIONS block")


prof = profile.load(PROFILE)
rec_fx = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x161s-dry-run", None) if DRY_RUN else new_run_dir("x161s")
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
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_StatWatch"),
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, tuple))
                  and k not in ("REPO", "LUA_DIR")},
    "deviations": [
        "No moodle level is read directly (no harness command reads SICK, PANIC or UNHAPPY levels); each side's "
        "level is inferred from its stat copy and the #2369 thresholds.",
        "X79's treated window writes alcoholLevel through witness.chain's setter hop on getBodyParts.get(1), "
        "the index checked by getType; bodypart.set has no alcoholLevel setter.",
        "X79's fold reads then writes in two bus calls about a second apart; the overwritten vanilla progress "
        "is accounted from each write reply's before.",
        "X81's held-target half is unmeasured: TKX_StatWatch has no hold arm.",
        "X88's delta is one value (0.5 per server tick) for PANIC and UNHAPPINESS, written out of the handler "
        "on OnTick by the probe.",
        "X75's drain arm sets FOOD_SICKNESS 24 so the SICK crossing lands in the window; the SICK < 1 control "
        "is its own 10 s window at FOOD_SICKNESS 10.",
        "X35 sets ENDURANCE 0.6 first so vanilla's awake regeneration moves the stat under the walk.",
        "X80 damages one part through SetHealth with every other part at 100.",
        "StatWatch tag counters a window reads are written -1 before it; -1 after it is never fired.",
        "Health is restored between the lethal arms by SetHealth 100 on every part.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["health reduced and restored", "body-part fields written and cleared",
                                        "stats written (POISON, FOOD_SICKNESS, TEMPERATURE, PANIC, UNHAPPINESS, "
                                        "ENDURANCE)", "the regeneration constants halved and restored",
                                        "foodtimer set 0", "a run walk"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "summaries": {}, "stats_all": [], "stats_get": [],
    "health_reads": [], "part_reads": [], "part_writes": [], "stat_writes": [], "temp_reads": [],
    "regen_reads": [], "regen_writes": [], "watches": [], "phase_errors": {}, "mod_error_checks": [],
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
        summarise()
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
