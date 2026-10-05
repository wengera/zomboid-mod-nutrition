"""x132-eat -- X24 (does the script `OnEat` hook fire once per eat or once per PORTION) and X33 (does
a cancelled eat of an item under the `serverStop` guard apply NOTHING), with the mod's eat and
cancel wrappers (Plan 2 Task 8) read live for the first time. Session S-D, one boot.

The run id prefix is `x132e` (run id `x132e-<date>-<time>`): the register's run-id pattern refuses a
hyphen in the prefix.

Copied from `_template.py` (house shape; `x132_drink.py` is the Plan 2 sibling, whose counters()
bug is NOT reused here: `witness.moddata` answers every value as a STRING, so every counter is
parsed explicitly through `to_num` below and its parsed value is asserted present in the phase).
Profile `x13-eat` (PZTestKit, TKX_ItemOverride, TKX_Nutrient, TKX_EatHook, NutritionRevamp in that
`Mods=` order). The item setup is x121's (`x121_overrides.py` M5): every item is spawned SERVER-side
by RCON `additem` and polled until it resolves on the client before `eat.action` is sent, because
`eat.action`'s `findOrSpawn` falls back to a CLIENT spawn the server never hears of (#0124).

TWO DEVIATIONS FROM THE AMENDMENTS, decided before the run, both forced by the profile's own mods:

  1. X24 eats `Base.Banana`, not `Base.Apple`. The probe `TKX_OnEatProbe` is registered ONLY on
     `Base.Banana` (TKX_EatHook's `tkx_eat_hook.txt` restates `item Banana` with `OnEat =
     TKX_OnEatProbe`; its Apple is untouched), so an apple never fires the probe and X24 would be
     unmeasured on it. x121's M5 ate the same Banana. The Banana is not in the mod's seed table, so
     the mod lands it with `missing = {Base.Banana}`: its mod-nutrient keys are 0 and its macros
     are the live ones (the macros always track vanilla, `IN.assemble`), which is exactly the
     two-fractions reading (the buffer's calories are live x frac). Banana: HungerChange -16,
     Calories 105 -> a quarter is 26.25 kcal and the per-quarter bulk is 0.2625.
  2. In this profile `Base.Apple` is 400 kcal, not 95: `TKX_ItemOverride` restates `item Apple` with
     `Calories = 400.0` (x121 M2). The X33 control arm (6) eats an apple and its predictions use
     400 (live macros) beside the seed's fibre 4.4 and water 155.8 for the bulk.

     X33's two cancel arms (7, 8) use ONE Banana instance: arm 7 cancels a fresh Banana partway;
     arm 8 drives THAT leftover's hunger under the guard (`item.set ... hungChange -0.005`) and
     cancels again. One instance means `findOrSpawn` (client, `getFirstTypeRecurse`) and `item.set`
     / `item.get` (server, `getFirstTypeRecurse`) cannot pick different items, and the Banana's
     probe makes "OnEat did not fire" a reading in arm 8 with arm 7 as its control. If arm 7's
     stop lands too late and the Banana is consumed, arm 8 spawns a fresh one first.

THE FOOD TIMER. `ISEatFoodAction:isValidStart` refuses at FOOD_EATEN >= 3, i.e. a
healthFromFoodTimer above 2 x the standard 1600; JustAteFood adds |hungerChange x f| x 13000 when
hunger sits at its minimum (#0503), so a few apples' worth would block the later arms. The driver
writes `foodtimer.set admin 0` before every action (a named world change; nothing here measures the
timer) and records each ack's `validStart` / `moodleFoodEaten`.

PHASES (fixed order: X24 FIRST -- every X33 eat bumps the same cumulative counters; every counter
read is a DELTA against the immediately preceding read, never against zero):

  P0  spawn a Banana; baselines (all reads); the server calorie drift rate.
  Q1..Q4  `eat.action Base.Banana 0.25` x4 on the one instance. Each: poll the nutrition pair until
      the server calories rose ~26.25 (drift-corrected), read the client's hunger at once, settle
      ~1.5 s, then the snapshot (hunger both sides first). Predictions per quarter: kcal +26.25
      (the action completed); probe `TKX_eat_onEat_server` +1 (once per PORTION); `stats.eats` +1
      and == the probe's `completes` delta; `lastIntake.share` 0.25 every quarter; `lastIntake.frac`
      0.25, 0.333, 0.5, 1.0; the buffer's calories +26.25 each quarter (decay-corrected); the bulk
      +0.2625; `item.get` id constant, hungChange -0.12, -0.08, -0.04, then consumed.
  P5  a fresh Banana, `eat.action Base.Banana 1`: kcal +105, probe +1, share 1.0, buffer +105.
  A6  (X33 control 1, a completed eat) a fresh Apple, `eat.action Base.Apple 1`: kcal +400, eats +1,
      cancels +0, landed +1, share 1.0, bulk +7.758, buffer calories +400.
  A7  (X33 control 2, a cancelled normal eat) a fresh Banana, `eat.action Base.Banana 1`, client
      `player.stop` STOP_AFTER_S after the ack (~40 % of the ~5.5 s action, #1189): the cancel
      resolves through serverStop (#0111). Prediction: cancels +1, eats +0, landed +1, share = p
      in (0, 1), kcal +105 p, buffer +105 p, the Banana NOT consumed (hungChange -0.16 (1 - p)),
      the probe's OnEat +1 (serverStop -> eat -> Eat fires it) and its `completes` +0.
  A8  (X33 the guard) THE SAME Banana, server `item.set admin Base.Banana hungChange -0.005`
      (abs(getHungerChange() x 100) = 0.5 <= 1), confirmed by the reply, then `eat.action
      Base.Banana 1` and `player.stop` at the same offset. Prediction: kcal +0, the item NOT
      consumed (same id, hungChange -0.005, calories unchanged), OnEat +0, completes +0, cancels +1,
      landed +0, lastIntake unchanged (share stays A7's p; a landing would read 0.03125).

THE BUFFER AND BULK ARITHMETIC (committed NR_Kernel_Stomach.lua / NR_Kernel_Vector.lua /
NR_Server_Intake.lua): an eat lands vec into stomach.buffer and bulk += bulkOf(vec) = calories/100 +
fibre x 0.5 + water/100; the buffer's macros are the live macros x frac (frac = drop/rawBefore), its
seed keys the seed x share (share = drop/instBase). Kinetics empties buffer and bulk once per game
minute by f = 1 - exp(-ln2 x dtH / (2.0 x scale)), scale = clamp(1 + lipids/40 + fibre/15, 0.5, 3)
of the buffer. The ingest-only delta is after - before x (1 - f(dt)) and lies in
[pred x (1 - f), pred] depending on when inside the window the eat landed.

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

from _common import ask, doctor, git_dirty, git_say, hard_kill, save   # noqa: E402
from pzt import fixture as fx, profile                                 # noqa: E402
from pzt.paths import new_run_dir                                      # noqa: E402
from pzt.session import (Timeline, grep_file, make_client, make_server,   # noqa: E402
                         teardown, verify)

PROFILE = "x13-eat"
SESSION = ("X24 + X33 (S-D): eat.action Base.Banana 0.25 x4 on one instance then a whole Banana "
           "against TKX_EatHook's per-side OnEat counters and the mod's eat wrapper (stats.eats, "
           "lastIntake.share/frac, the stomach buffer); then a completed Apple, a cancelled Banana "
           "and the same Banana cancelled under the serverStop guard (hungChange -0.005)")
ARTIFACT = "eat.json"
USER = "admin"
# Task 13's run, the smoke test of the current harness (T12's commands ran there first).
ACCEPTANCE_RUN = "x132d-20261005-060046"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

# ---- the probe counters (player modData, one key per side) --------------------------------------
ONEAT_KEYS = ["TKX_eat_onEat_server", "TKX_eat_onEat_client"]
ONEAT_ARGS = f"player:{USER} " + " ".join(ONEAT_KEYS)
ONEAT_FIELD_COUNT = 2
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}

# ---- the mod's record, one atomic read of the store's global modData table ----------------------
STORE_TABLE = "NutritionRevamp.players"
REC_KEYS = [f"{USER}.stomach.bulk", f"{USER}.stomach.buffer.calories",
            f"{USER}.stomach.buffer.lipids", f"{USER}.stomach.buffer.fibre",
            f"{USER}.stomach.buffer.water", f"{USER}.kineticsAge", f"{USER}.stomachFill",
            f"{USER}.lastIntake.share", f"{USER}.lastIntake.frac", f"{USER}.lastIntake.source",
            f"{USER}.lastIntake.fullType", f"{USER}.lastIntake.missing.1"]
REC_ARGS = f"global:{STORE_TABLE} " + " ".join(REC_KEYS)
REC_FIELD_COUNT = len(REC_KEYS)

# ---- the lua.global reads, per side --------------------------------------------------------------
REC = "NutritionRevamp.server.store.records." + USER
INTAKE = "NutritionRevamp.server.intake"
SERVER_GLOBALS = [
    INTAKE + ".stats.eats", INTAKE + ".stats.cancels", INTAKE + ".stats.landed",
    INTAKE + ".stats.failures", INTAKE + ".lastError",
    REC + ".lastIntake.share", REC + ".lastIntake.frac", REC + ".stomach.buffer.calories",
    "TKX_EatHook.calls", "TKX_EatHook.completes", "TKX_EatHook.lastFraction",
    "TKX_EatHook.lastComplete",
]
CLIENT_GLOBALS = ["TKX_EatHook.calls", "TKX_EatHook.lastFraction"]
P0_SERVER_EXTRA = ["NutritionRevamp.version", "TK.version", "NutritionRevamp.server.options.mode",
                   INTAKE + ".wrappedComplete", INTAKE + ".wrappedServerStop",
                   "TKX_EatHook.wrapped", INTAKE + ".stats.passthrough"]
P0_CLIENT_EXTRA = ["NutritionRevamp.version", "TK.version", "TKX_EatHook.wrapped",
                   INTAKE + ".stats.passthrough"]

# ---- the item numbers (profile-resolved; see the docstring's deviations) -------------------------
BANANA = {"calories": 105.0, "lipids": 0.39, "hunger": -0.16}      # TKX_EatHook's restated Banana
APPLE_LIVE_KCAL = 400.0                                            # TKX_ItemOverride's Apple
APPLE_SEED = {"calories": 95.0, "fibre": 4.4, "water": 155.8, "lipids": 0.31}  # SEED Base.Apple
QUARTER_KCAL = BANANA["calories"] * 0.25                           # 26.25 every quarter
QUARTER_BULK = QUARTER_KCAL / 100                                  # 0.2625 (no seed: fibre/water 0)
WHOLE_BANANA_BULK = BANANA["calories"] / 100                       # 1.05
APPLE_BULK = APPLE_LIVE_KCAL / 100 + APPLE_SEED["fibre"] * 0.5 + APPLE_SEED["water"] / 100  # 7.758
QUARTER_FRACS = [0.25, 1 / 3, 0.5, 1.0]                            # frac = drop / rawBefore
QUARTER_HUNG_AFTER = [-0.12, -0.08, -0.04, None]                   # None = consumed
GUARD_HUNG = "-0.005"                                              # abs(x 100) = 0.5 <= 1
GUARD_SHARE_IF_LANDED = 0.005 / 0.16                               # 0.03125
HALF_TIME_H = 2.0
FULL_BULK = 8.0
KCAL_TOL = 3.0
SHARE_TOL = 0.01
BAND_FRAC, BAND_ABS = 0.03, 0.06

SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
POLL_S, POLL_MAX_S = 0.5, 20.0
HUNGER_LATER_S = 1.5               # the second hunger read ~1.5 s after the immediate one
STOP_AFTER_S = 2.0                 # ~40 % of the ~5.5 s real MP eat (#1189), from the ack's return
CANCEL_WATCH_S = 10.0              # after the stop: watch the stores for a late landing
DRIFT_GAP_S = 6.0

# ---- console greps (compiled; limits >= 2x predicted; a client prints each block twice) --------
LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table")
INTAKE_RX = re.compile(r"intake:")
SYNC_RX = re.compile(r"SyncItemFields", re.IGNORECASE)
LUAERR_LIMIT, INTAKE_LIMIT, SYNC_LIMIT = 20, 40, 10


def to_num(v):
    """A number from a number OR a numeric string (witness.moddata answers strings); None else."""
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


def probe(side, cmd, args, timeout=20):
    """One read with its own wall bracket; the re-ask-once guard (a non-table where a table
    belongs is re-asked ONCE and both readings kept)."""
    t = wall()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if not isinstance(val, dict):
        meta["reasked"] = True
        meta["first_reply"] = val
        val = ask(side, cmd, args, timeout=timeout)
        meta["wall_done"] = wall()
    if isinstance(val, dict):
        val = dict(val)
        val["_probe"] = meta
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def step(name, side, cmd, args, timeout=30):
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    save(path, out, tl, server)
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


def gv(reply):
    """The value of a lua.global reply, or None when it did not resolve to a scalar."""
    if isinstance(reply, dict) and reply.get("resolved") and "value" in reply:
        return reply.get("value")
    return None


def diff(a, b):
    if a is None or b is None:
        return None
    return b - a


def md_values(reply):
    return (reply.get("values") or {}) if isinstance(reply, dict) else {}


def check_count(tag, label, reply, expected):
    count = reply.get("count") if isinstance(reply, dict) else None
    if count != expected:
        out["field_count_failures"].append({"tag": tag, "read": label, "count": count,
                                            "expected": expected})
    return count == expected


def snapshot(tag, item_type):
    """Every read at one tag, closest-to-the-action first: hunger both sides (stats.get, client
    first), the mod's record (one atomic witness.moddata of the store table), the intake counters
    and the probe globals, the OnEat modData counters client then server, the server's item."""
    snap = {"tag": tag, "wall_start": wall(), "item_type": item_type}
    snap["stats"] = {"client": probe(c, "stats.get", ""), "server": probe(server, "stats.get", USER)}
    rec_reply = probe(server, "witness.moddata", REC_ARGS)
    snap["record"] = rec_reply
    check_count(tag, "record", rec_reply, REC_FIELD_COUNT)
    snap["globals"] = {"client": {}, "server": {}}
    for name in CLIENT_GLOBALS:
        snap["globals"]["client"][name] = probe(c, "lua.global", name)
    for name in SERVER_GLOBALS:
        snap["globals"]["server"][name] = probe(server, "lua.global", name)
    cm = probe(c, "witness.moddata", ONEAT_ARGS)
    sm = probe(server, "witness.moddata", ONEAT_ARGS)
    snap["oneat_moddata"] = {"client": cm, "server": sm}
    check_count(tag, "oneat_client", cm, ONEAT_FIELD_COUNT)
    check_count(tag, "oneat_server", sm, ONEAT_FIELD_COUNT)
    snap["item"] = probe(server, "item.get", f"{USER} {item_type}") if item_type else None
    snap["wall_end"] = wall()
    out["snapshots"][tag] = snap
    save(path, out, tl, server)
    return snap


def sval(snap, name, side="server"):
    return gv(snap["globals"][side].get(name))


def rnum(snap, key):
    """A record field off the atomic moddata read, parsed from its string."""
    return to_num(md_values(snap["record"]).get(f"{USER}.{key}"))


def rstr(snap, key):
    v = md_values(snap["record"]).get(f"{USER}.{key}")
    return v if isinstance(v, str) else None


def md_counter(reply, key):
    """One OnEat counter off a witness.moddata reply: its STRING value parsed; a key the reply
    lists in `missing` is 0 (never written yet); a broken reply (no table) is None."""
    if not isinstance(reply, dict) or not isinstance(reply.get("values"), dict):
        return None
    v = reply["values"].get(key)
    if v is None:
        return 0.0 if key in (reply.get("missing") or []) else None
    return to_num(v)


def counters(snap):
    """The OnEat counters as graded: `_server` off the SERVER's table, `_client` off the CLIENT's
    (each side writes its own copy of the player's modData), parsed from strings; plus the
    probe's numeric globals."""
    s = md_values(snap["oneat_moddata"]["server"])
    cl = md_values(snap["oneat_moddata"]["client"])
    return {"onEat_server": md_counter(snap["oneat_moddata"]["server"], "TKX_eat_onEat_server"),
            "onEat_client": md_counter(snap["oneat_moddata"]["client"], "TKX_eat_onEat_client"),
            "server_table_client_key": s.get("TKX_eat_onEat_client"),
            "client_table_server_key": cl.get("TKX_eat_onEat_server"),
            "calls_server": to_num(sval(snap, "TKX_EatHook.calls")),
            "calls_client": to_num(sval(snap, "TKX_EatHook.calls", "client")),
            "completes_server": to_num(sval(snap, "TKX_EatHook.completes")),
            "lastFraction_server": to_num(sval(snap, "TKX_EatHook.lastFraction")),
            "lastFraction_client": to_num(sval(snap, "TKX_EatHook.lastFraction", "client")),
            "lastComplete_server": sval(snap, "TKX_EatHook.lastComplete"),
            "eats": to_num(sval(snap, INTAKE + ".stats.eats")),
            "cancels": to_num(sval(snap, INTAKE + ".stats.cancels")),
            "landed": to_num(sval(snap, INTAKE + ".stats.landed")),
            "failures": to_num(sval(snap, INTAKE + ".stats.failures"))}


def cdelta(a, b):
    ca, cb = counters(a), counters(b)
    return {k: diff(ca[k], cb[k]) for k in ("onEat_server", "onEat_client", "calls_server",
                                             "calls_client", "completes_server", "eats", "cancels",
                                             "landed", "failures")}


def drift_rate():
    return (out["phases"].get("P0", {}).get("drift") or {}).get("kcal_per_s")


def scal(snap, side="server"):
    st = snap["stats"][side]
    return to_num(st.get("calories")) if isinstance(st, dict) else None


def kcal_read(pre, post):
    """The calorie delta between two snapshots' stats.get reads, raw and drift-corrected."""
    a, b = scal(pre), scal(post)
    ca, cb = scal(pre, "client"), scal(post, "client")
    ta = (pre["stats"]["server"].get("_probe") or {}).get("wall") \
        if isinstance(pre["stats"]["server"], dict) else None
    tb = (post["stats"]["server"].get("_probe") or {}).get("wall") \
        if isinstance(post["stats"]["server"], dict) else None
    el = diff(ta, tb)
    rate = drift_rate() or 0.0
    raw, craw = diff(a, b), diff(ca, cb)
    return {"server_before": a, "server_after": b, "server_raw": raw,
            "server_corrected": None if raw is None or el is None else raw - rate * el,
            "client_raw": craw,
            "client_corrected": None if craw is None or el is None else craw - rate * el,
            "elapsed_s": el, "drift_kcal_per_s": rate}


def comp_scale(cal, lip, fib, wat):
    if cal is None or lip is None or fib is None:
        return 1.0
    if cal == 0 and fib == 0 and (wat or 0) > 0:
        return 0.25
    return min(max(1 + lip / 40 + fib / 15, 0.5), 3.0)


def keep(dt_h, scale):
    """1 - f: the share kinetics leaves over dt_h hours at this composition scale."""
    if dt_h is None:
        return None
    return math.exp(-0.6931471805599453 * max(dt_h, 0.0) / (HALF_TIME_H * scale))


def decay_read(pre, post, key, pred):
    """The ingest-only delta of a record field (stomach.bulk or stomach.buffer.calories) between
    two snapshots, corrected for the kinetics emptying over the kineticsAge window."""
    v0, v1 = rnum(pre, key), rnum(post, key)
    k0, k1 = rnum(pre, "kineticsAge"), rnum(post, "kineticsAge")
    dt = diff(k0, k1)
    s0 = comp_scale(rnum(pre, "stomach.buffer.calories"), rnum(pre, "stomach.buffer.lipids"),
                    rnum(pre, "stomach.buffer.fibre"), rnum(pre, "stomach.buffer.water"))
    s1 = comp_scale(rnum(post, "stomach.buffer.calories"), rnum(post, "stomach.buffer.lipids"),
                    rnum(post, "stomach.buffer.fibre"), rnum(post, "stomach.buffer.water"))
    kp0, kp1 = keep(dt, s0), keep(dt, s1)
    corr = None
    lo = hi = None
    if v0 is not None and v1 is not None and kp0 is not None:
        c0, c1 = v1 - v0 * kp0, v1 - v0 * kp1
        corr = (c0 + c1) / 2
        kmin = min(kp0, kp1)
        tol = BAND_FRAC * abs(pred) + BAND_ABS
        lo = min(c0, c1) - 0.0
        hi = max(c0, c1)
        within = (pred * kmin - tol) <= hi and lo <= (pred + tol)
    else:
        within = None
    return {"key": key, "before": v0, "after": v1, "raw_delta": diff(v0, v1),
            "kineticsAge_before": k0, "kineticsAge_after": k1, "dt_h": dt,
            "scale_before": s0, "scale_after": s1, "keep": [kp0, kp1],
            "ingest_delta_corrected": corr, "corrected_range": [lo, hi], "predicted": pred,
            "accept_band": None if kp0 is None else
            [pred * min(kp0, kp1) - (BAND_FRAC * abs(pred) + BAND_ABS),
             pred + (BAND_FRAC * abs(pred) + BAND_ABS)],
            "within": within}


def spawn(full_type, why):
    """RCON additem, then poll the CLIENT until the instance resolves there (x121's route)."""
    ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{full_type} getID")
        res = seen.get("resolved") if isinstance(seen, dict) else None
        fields = (seen.get("fields") or {}) if isinstance(seen, dict) else {}
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": fields.get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    row["server_item_get"] = probe(server, "item.get", f"{USER} {full_type}")
    out["spawns"].append(row)
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    save(path, out, tl, server)
    return row


def nutrition_pair():
    cr = probe(c, "nutrition.get", "")
    sr = probe(server, "nutrition.get", USER)
    return {"wall": wall(), "client_calories": to_num(cr.get("calories"))
            if isinstance(cr, dict) else None,
            "server_calories": to_num(sr.get("calories")) if isinstance(sr, dict) else None,
            "client_hunger": to_num(cr.get("hunger")) if isinstance(cr, dict) else None,
            "server_hunger": to_num(sr.get("hunger")) if isinstance(sr, dict) else None}


def eat_phase(label, pre, full_type, arg, pred_kcal, stop=False):
    """Prime the food timer, queue eat.action on the client, then either poll the nutrition pair
    until the server's calories rose to the prediction (a completed eat) or, for a cancel, send
    the client's player.stop STOP_AFTER_S after the ack and watch the stores CANCEL_WATCH_S. The
    client's hunger is read the moment the poll ends; the snapshot follows ~1.5 s later."""
    ph = {"label": label, "fullType": full_type, "arg": arg, "stop": stop}
    ph["foodtimer"] = step(f"{label}_foodtimer", server, "foodtimer.set", f"{USER} 0")["ack"]
    time.sleep(1.0)
    ack = step(f"{label}_eat_action", c, "eat.action", f"{full_type} {arg}")
    a = ack["ack"] if isinstance(ack["ack"], dict) else {}
    ph["ack"] = ack["ack"]
    ph["queued_wall"] = ack["wall_after"]
    for k in ("spawned", "itemId", "validStart", "maxTime", "moodleFoodEaten"):
        ph[k] = a.get(k)
    base_srv = scal(pre)
    base_cli = scal(pre, "client")
    t_base = (pre["stats"]["server"].get("_probe") or {}).get("wall") \
        if isinstance(pre["stats"]["server"], dict) else None
    rate = drift_rate() or 0.0
    ph["polls"] = []
    if stop:
        while wall() - ph["queued_wall"] < STOP_AFTER_S:
            time.sleep(0.05)
        st = step(f"{label}_player_stop", c, "player.stop", "")
        ph["stop_ack"] = st["ack"]
        ph["stop_sent_since_queue_s"] = round(st["wall_before"] - ph["queued_wall"], 3)
        ph["stop_acked_since_queue_s"] = round(st["wall_after"] - ph["queued_wall"], 3)
    first_srv = first_cli = None
    while True:
        time.sleep(POLL_S)
        p = nutrition_pair()
        el = None if t_base is None else p["wall"] - t_base
        ds, dc = diff(base_srv, p["server_calories"]), diff(base_cli, p["client_calories"])
        ds_c = None if ds is None or el is None else ds - rate * el
        dc_c = None if dc is None or el is None else dc - rate * el
        row = dict(p, since_queue=round(p["wall"] - ph["queued_wall"], 3),
                   server_delta_corr=ds_c, client_delta_corr=dc_c)
        ph["polls"].append(row)
        if first_srv is None and ds_c is not None and ds_c > 1.0:
            first_srv = row["since_queue"]
        if first_cli is None and dc_c is not None and dc_c > 1.0:
            first_cli = row["since_queue"]
        since = p["wall"] - ph["queued_wall"]
        if stop:
            if since >= STOP_AFTER_S + CANCEL_WATCH_S:
                break
        else:
            done_s = ds_c is not None and ds_c >= pred_kcal - KCAL_TOL
            done_c = dc_c is not None and dc_c >= pred_kcal - KCAL_TOL
            if (done_s and done_c) or since >= POLL_MAX_S:
                break
    ph["first_server_move_since_queue_s"] = first_srv
    ph["first_client_move_since_queue_s"] = first_cli
    t_h = wall()
    ph["hunger_immediate_client"] = probe(c, "stats.get", "")
    ph["hunger_immediate_wall"] = t_h
    while wall() - t_h < HUNGER_LATER_S:
        time.sleep(0.05)
    save(path, out, tl, server)
    return ph


def hunger_of(reply):
    return to_num(reply.get("hunger")) if isinstance(reply, dict) else None


def hunger_obs(ph, post):
    return {"client_immediate": hunger_of(ph.get("hunger_immediate_client")),
            "client_later": hunger_of(post["stats"]["client"]),
            "server_later": hunger_of(post["stats"]["server"]),
            "stomachFill_after": rnum(post, "stomachFill"),
            "predicted_server_later_from_fill": None if rnum(post, "stomachFill") is None
            else max(0.0, min(1.0, 1 - rnum(post, "stomachFill")))}


def item_of(snap):
    it = snap.get("item")
    if not isinstance(it, dict) or "id" not in it:
        return {"present": False, "reply": it if not isinstance(it, dict) else
                {k: it.get(k) for k in ("error",) if k in it}}
    return {"present": True, "id": it.get("id"), "hungChange": to_num(it.get("hungChange")),
            "hungerChange": to_num(it.get("hungerChange")),
            "baseHunger": to_num(it.get("baseHunger")), "calories": to_num(it.get("calories"))}


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x132e-dry-run", None) if DRY_RUN else new_run_dir("x132e")
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
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_EatHook"),
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "vanilla_player_keys": sorted(VANILLA_PLAYER_KEYS),
    "constants": {"BANANA": BANANA, "APPLE_LIVE_KCAL": APPLE_LIVE_KCAL, "APPLE_SEED": APPLE_SEED,
                  "QUARTER_KCAL": QUARTER_KCAL, "QUARTER_BULK": QUARTER_BULK,
                  "WHOLE_BANANA_BULK": WHOLE_BANANA_BULK, "APPLE_BULK": APPLE_BULK,
                  "QUARTER_FRACS": QUARTER_FRACS, "QUARTER_HUNG_AFTER": QUARTER_HUNG_AFTER,
                  "GUARD_HUNG": GUARD_HUNG, "GUARD_SHARE_IF_LANDED": GUARD_SHARE_IF_LANDED,
                  "HALF_TIME_H": HALF_TIME_H, "FULL_BULK": FULL_BULK, "KCAL_TOL": KCAL_TOL,
                  "SHARE_TOL": SHARE_TOL, "BAND_FRAC": BAND_FRAC, "BAND_ABS": BAND_ABS,
                  "POLL_S": POLL_S, "POLL_MAX_S": POLL_MAX_S, "HUNGER_LATER_S": HUNGER_LATER_S,
                  "STOP_AFTER_S": STOP_AFTER_S, "CANCEL_WATCH_S": CANCEL_WATCH_S,
                  "ONEAT_FIELD_COUNT": ONEAT_FIELD_COUNT, "REC_FIELD_COUNT": REC_FIELD_COUNT},
    "deviations": [
        "X24 eats Base.Banana, not Base.Apple: TKX_OnEatProbe is registered only on the Banana "
        "(TKX_EatHook tkx_eat_hook.txt), so an apple cannot fire the probe; x121 M5 ate the same "
        "Banana. Decided before the run.",
        "Base.Apple is 400 kcal in this profile (TKX_ItemOverride restates it), not 95: arm A6's "
        "calorie and buffer predictions use 400; its bulk uses 400/100 + the seed's fibre and "
        "water. Decided before the run.",
        "X33's cancel arms A7 and A8 use one Banana instance (A8 drives A7's leftover under the "
        "guard), so the client's findOrSpawn and the server's item.set/item.get cannot pick "
        "different items, and the Banana's probe makes OnEat a reading on the cancel arms.",
        "foodtimer.set admin 0 before every action (isValidStart refuses at FOOD_EATEN >= 3).",
    ],
    "world_changes": {"restored": "the run's own copy of the fixture; nothing written back to the "
                                  "golden fixture",
                      "left_in_place": ["RCON-spawned Base.Banana x3 and Base.Apple x1 in admin's "
                                        "inventory in this run's copy (eaten, part-eaten or "
                                        "guard-set)",
                                        "healthFromFoodTimer zeroed before every action",
                                        "the record's stomach, pool and lastIntake",
                                        "the player modData keys TKX_eat_onEat_server/_client"]},
    "steps": [], "notes": [], "spawns": [], "snapshots": {}, "phases": {}, "verdicts": {},
    "field_count_failures": [],
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)

try:
    server.start(timeout=prof.server_timeout)
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ================= P0 -- baselines ======================================================
    out["phases"]["P0_preexisting"] = {"banana": probe(server, "item.get", f"{USER} Base.Banana"),
                                       "apple": probe(server, "item.get", f"{USER} Base.Apple")}
    sp0 = spawn("Base.Banana", "X24: the one instance eaten a quarter at a time; RCON first -- "
                               "eat.action's findOrSpawn would client-spawn one (#0124)")
    extras = {"client": {n: probe(c, "lua.global", n) for n in P0_CLIENT_EXTRA},
              "server": {n: probe(server, "lua.global", n) for n in P0_SERVER_EXTRA}}
    s0 = snapshot("P0", "Base.Banana")
    d0 = probe(server, "nutrition.get", USER)
    t_d0 = wall()
    time.sleep(DRIFT_GAP_S)
    d1 = probe(server, "nutrition.get", USER)
    t_d1 = wall()
    dk = diff(to_num(d0.get("calories")) if isinstance(d0, dict) else None,
              to_num(d1.get("calories")) if isinstance(d1, dict) else None)
    c0 = counters(s0)
    out["phases"]["P0"] = {
        "drift": {"first": d0, "second": d1, "wall": [t_d0, t_d1],
                  "kcal_per_s": (dk / (t_d1 - t_d0)) if dk is not None and t_d1 > t_d0 else None},
        "extras": {s: {n: gv(r) for n, r in v.items()} for s, v in extras.items()},
        "counters": c0, "item": item_of(s0),
        "record": {k: md_values(s0["record"]).get(f"{USER}.{k}") for k in
                   ("stomach.bulk", "stomach.buffer.calories", "kineticsAge", "stomachFill",
                    "lastIntake.share")},
        "oneat_server_census_nonvanilla": sorted(
            k for k in ((s0["oneat_moddata"]["server"] or {}).get("keys") or [])
            if k.split(":")[0] not in VANILLA_PLAYER_KEYS)
        if isinstance(s0["oneat_moddata"]["server"], dict) else None,
    }
    b0 = rnum(s0, "stomach.bulk")
    wrapped = out["phases"]["P0"]["extras"]["server"]
    grade("P0", predicted="the record exists, its stomach seeded full (bulk just under 8.0); the "
                          "mod's complete and serverStop wraps installed; the probe's wrap "
                          "installed; every OnEat counter absent (0); the Banana present server-side",
          observed=out["phases"]["P0"],
          verdict=("unmeasured" if b0 is None else
                   ("as_predicted" if (5.0 <= b0 <= FULL_BULK + 1e-6
                                       and wrapped.get(INTAKE + ".wrappedComplete") is True
                                       and wrapped.get(INTAKE + ".wrappedServerStop") is True
                                       and (c0["onEat_server"] or 0) == 0
                                       and item_of(s0)["present"]) else "falsified")),
          falsifier="no record, an unseeded stomach, a wrap not installed or a counter already up")

    # ================= X24 -- four quarters on one Banana, then a whole one =================
    prev = s0
    quarters = []
    banana_id = item_of(s0).get("id")
    for i in range(4):
        label = f"Q{i + 1}"
        if not sp0["resolved"]:
            quarters.append({"label": label, "skipped": "the RCON Banana never resolved"})
            continue
        ph = eat_phase(label, prev, "Base.Banana", "0.25", QUARTER_KCAL)
        post = snapshot(f"{label}_post", "Base.Banana")
        ph["kcal"] = kcal_read(prev, post)
        ph["delta"] = cdelta(prev, post)
        ph["counters_after"] = counters(post)
        ph["share"] = to_num(sval(post, REC + ".lastIntake.share"))
        ph["frac"] = to_num(sval(post, REC + ".lastIntake.frac"))
        ph["share_md"] = rnum(post, "lastIntake.share")
        ph["frac_md"] = rnum(post, "lastIntake.frac")
        ph["lastIntake"] = {"fullType": rstr(post, "lastIntake.fullType"),
                            "source": rstr(post, "lastIntake.source"),
                            "missing1": rstr(post, "lastIntake.missing.1")}
        ph["buffer"] = decay_read(prev, post, "stomach.buffer.calories", QUARTER_KCAL)
        ph["bulk"] = decay_read(prev, post, "stomach.bulk", QUARTER_BULK)
        ph["item"] = item_of(post)
        ph["hunger"] = hunger_obs(ph, post)
        out["phases"][label] = ph
        quarters.append(ph)
        prev = post

    def qgrade(ph, i):
        d = ph.get("delta") or {}
        k = (ph.get("kcal") or {}).get("server_corrected")
        completed = k is not None and abs(k - QUARTER_KCAL) <= KCAL_TOL
        hung_ok = (ph["item"]["present"] is False) if QUARTER_HUNG_AFTER[i] is None else \
            (ph["item"]["present"] and ph["item"]["id"] == banana_id
             and close(ph["item"]["hungChange"], QUARTER_HUNG_AFTER[i], 0.002))
        obs = {"kcal": ph.get("kcal"), "delta": d, "share": ph.get("share"),
               "frac": ph.get("frac"), "share_md": ph.get("share_md"), "frac_md": ph.get("frac_md"),
               "buffer": ph.get("buffer"), "bulk": ph.get("bulk"), "item": ph.get("item"),
               "item_as_predicted": hung_ok, "completed": completed,
               "lastIntake": ph.get("lastIntake"), "hunger": ph.get("hunger"),
               "lastFraction": {"server": ph["counters_after"]["lastFraction_server"],
                                "client": ph["counters_after"]["lastFraction_client"]},
               "ack": {k2: ph.get(k2) for k2 in ("validStart", "maxTime", "moodleFoodEaten",
                                                 "itemId", "spawned")}}
        if not completed or d.get("onEat_server") is None:
            v = "unmeasured"
        elif (d["onEat_server"] == 1 and d.get("eats") == 1 and d.get("completes_server") == 1
              and close(ph.get("share"), 0.25, SHARE_TOL)
              and close(ph.get("frac"), QUARTER_FRACS[i], SHARE_TOL)
              and ph["buffer"]["within"] and hung_ok):
            v = "as_predicted"
        else:
            v = "falsified"
        grade(ph["label"], predicted=f"kcal +{QUARTER_KCAL} (completed); onEat_server +1; "
                                     f"stats.eats +1 == completes +1; share 0.25; frac "
                                     f"{QUARTER_FRACS[i]:.4f}; buffer calories +{QUARTER_KCAL} "
                                     "(decay-corrected); item id constant, hungChange "
                                     f"{QUARTER_HUNG_AFTER[i]}",
              observed=obs, verdict=v,
              falsifier="onEat_server +0 on a completed quarter (once per eat); share drifting "
                        "with frac; buffer deltas shrinking; eats != completes")
        return v

    qv = [qgrade(ph, i) if "skipped" not in ph else "unmeasured" for i, ph in enumerate(quarters)]

    # ---- P5: a fresh whole Banana ----
    sp5 = spawn("Base.Banana", "P5: a fresh whole Banana (Q4 consumed the first)")
    if sp5["resolved"]:
        ph5 = eat_phase("P5", prev, "Base.Banana", "1", BANANA["calories"])
        s5 = snapshot("P5_post", "Base.Banana")
        ph5.update({"kcal": kcal_read(prev, s5), "delta": cdelta(prev, s5),
                    "counters_after": counters(s5),
                    "share": to_num(sval(s5, REC + ".lastIntake.share")),
                    "frac": to_num(sval(s5, REC + ".lastIntake.frac")),
                    "buffer": decay_read(prev, s5, "stomach.buffer.calories", BANANA["calories"]),
                    "bulk": decay_read(prev, s5, "stomach.bulk", WHOLE_BANANA_BULK),
                    "item": item_of(s5), "hunger": hunger_obs(ph5, s5)})
        prev = s5
    else:
        ph5 = {"skipped": "the RCON Banana never resolved client-side"}
    out["phases"]["P5"] = ph5
    if "skipped" in ph5:
        v5 = "unmeasured"
    else:
        k5 = ph5["kcal"]["server_corrected"]
        d5 = ph5["delta"]
        if k5 is None or abs(k5 - BANANA["calories"]) > KCAL_TOL or d5.get("onEat_server") is None:
            v5 = "unmeasured"
        elif (d5["onEat_server"] == 1 and d5.get("eats") == 1 and close(ph5["share"], 1.0, SHARE_TOL)
              and ph5["buffer"]["within"] and not ph5["item"]["present"]):
            v5 = "as_predicted"
        else:
            v5 = "falsified"
    grade("P5", predicted="a whole Banana: kcal +105, onEat_server +1, eats +1, share 1.0, buffer "
                          "+105, the Banana consumed",
          observed=ph5, verdict=v5, falsifier="any of those off")

    # ---- X24 verdict ----
    done = [ph for ph in quarters if "skipped" not in ph and ph.get("kcal")
            and ph["kcal"]["server_corrected"] is not None
            and abs(ph["kcal"]["server_corrected"] - QUARTER_KCAL) <= KCAL_TOL]
    on_q = [(ph.get("delta") or {}).get("onEat_server") for ph in quarters]
    oncl_q = [(ph.get("delta") or {}).get("onEat_client") for ph in quarters]
    eats_q = [(ph.get("delta") or {}).get("eats") for ph in quarters]
    comp_q = [(ph.get("delta") or {}).get("completes_server") for ph in quarters]
    share_q = [ph.get("share") for ph in quarters]
    frac_q = [ph.get("frac") for ph in quarters]
    buf_q = [(ph.get("buffer") or {}).get("ingest_delta_corrected") for ph in quarters]
    bufraw_q = [(ph.get("buffer") or {}).get("raw_delta") for ph in quarters]
    kcal_q = [(ph.get("kcal") or {}).get("server_corrected") for ph in quarters]
    x24obs = {"quarters_completed": len(done), "onEat_server_deltas": on_q,
              "onEat_client_deltas": oncl_q, "eats_deltas": eats_q, "completes_deltas": comp_q,
              "kcal_corrected": kcal_q, "share_series": share_q, "frac_series": frac_q,
              "buffer_corrected_deltas": buf_q, "buffer_raw_deltas": bufraw_q,
              "whole": {"onEat_server": (ph5.get("delta") or {}).get("onEat_server"),
                        "onEat_client": (ph5.get("delta") or {}).get("onEat_client"),
                        "eats": (ph5.get("delta") or {}).get("eats"),
                        "kcal": (ph5.get("kcal") or {}).get("server_corrected"),
                        "share": ph5.get("share")}}
    if len(done) < 4 or any(v is None for v in on_q):
        x24, x24v = "unmeasured: fewer than four quarters proven complete", "unmeasured"
    elif all(v == 1 for v in on_q):
        x24, x24v = "once per PORTION: 4 server OnEat calls for four completed quarters", \
            "as_predicted"
    elif sum(on_q) == 1:
        x24, x24v = "once per EAT: one server OnEat call across four completed quarters", \
            "falsified"
    else:
        x24, x24v = f"neither: server OnEat deltas {on_q}", "falsified"
    x24obs["summary"] = x24
    grade("X24", predicted="OnEat fires once per PORTION: onEat_server +1 on each of four "
                           "completed quarters (4/4), and +1 on the whole Banana",
          observed=x24obs, verdict=x24v,
          falsifier="1/1 after four completed quarters (once per eat)")

    # ---- the two fractions, live ----
    shares_const = all(close(s, 0.25, SHARE_TOL) for s in share_q)
    fracs_ok = all(close(f, e, SHARE_TOL) for f, e in zip(frac_q, QUARTER_FRACS))
    bufs_ok = all((ph.get("buffer") or {}).get("within") for ph in quarters)
    share_drift = all(close(s, e, SHARE_TOL) for s, e in zip(share_q, QUARTER_FRACS))
    buf_shrink = all(b is not None for b in buf_q) and \
        all(close(b, QUARTER_KCAL * 0.25 / e, 1.5) for b, e in zip(buf_q, QUARTER_FRACS))
    if len(done) < 4 or any(s is None for s in share_q) or any(b is None for b in buf_q):
        tfv = "unmeasured"
    elif shares_const and fracs_ok and bufs_ok:
        tfv = "as_predicted"
    else:
        tfv = "falsified"
    grade("TWO_FRACTIONS", predicted="lastIntake.share 0.25 after every quarter (share of the WHOLE) "
                                     "with frac 0.25, 0.333, 0.5, 1.0 (share of what is LEFT) and "
                                     "the buffer's calories +26.25 each quarter (live macros x "
                                     "frac): ruling T8-1 read live",
          observed={"share_series": share_q, "frac_series": frac_q,
                    "buffer_corrected_deltas": buf_q, "buffer_within": [
                        (ph.get("buffer") or {}).get("within") for ph in quarters],
                    "bulk_corrected_deltas": [(ph.get("bulk") or {}).get("ingest_delta_corrected")
                                              for ph in quarters],
                    "share_drifted_like_frac": share_drift, "buffer_shrank": buf_shrink},
          verdict=tfv,
          falsifier="share 0.25 -> 0.33 -> 0.5 -> 1.0 (the wrapper used frac for the whole); "
                    "buffer deltas 26.25 -> 8.75... shrinking (the macros used share)")

    # ================= X33 -- three arms that must differ ==================================
    # ---- A6: a completed Apple (control 1) ----
    sp6 = spawn("Base.Apple", "A6: the completed-eat control")
    if sp6["resolved"]:
        ph6 = eat_phase("A6", prev, "Base.Apple", "1", APPLE_LIVE_KCAL)
        s6 = snapshot("A6_post", "Base.Apple")
        ph6.update({"kcal": kcal_read(prev, s6), "delta": cdelta(prev, s6),
                    "counters_after": counters(s6),
                    "share": to_num(sval(s6, REC + ".lastIntake.share")),
                    "frac": to_num(sval(s6, REC + ".lastIntake.frac")),
                    "lastIntake": {"fullType": rstr(s6, "lastIntake.fullType"),
                                   "source": rstr(s6, "lastIntake.source")},
                    "buffer": decay_read(prev, s6, "stomach.buffer.calories", APPLE_LIVE_KCAL),
                    "bulk": decay_read(prev, s6, "stomach.bulk", APPLE_BULK),
                    "item": item_of(s6), "hunger": hunger_obs(ph6, s6)})
        prev = s6
    else:
        ph6 = {"skipped": "the RCON Apple never resolved client-side"}
    out["phases"]["A6"] = ph6
    if "skipped" in ph6 or ph6["kcal"]["server_corrected"] is None:
        v6 = "unmeasured"
    else:
        d6 = ph6["delta"]
        if (close(ph6["kcal"]["server_corrected"], APPLE_LIVE_KCAL, KCAL_TOL * 2)
                and d6.get("eats") == 1 and d6.get("cancels") == 0 and d6.get("landed") == 1
                and close(ph6["share"], 1.0, SHARE_TOL) and ph6["bulk"]["within"]
                and ph6["buffer"]["within"] and not ph6["item"]["present"]):
            v6 = "as_predicted"
        else:
            v6 = "falsified"
    grade("A6_completed", predicted=f"a completed Apple: kcal +{APPLE_LIVE_KCAL:.0f}; eats +1, "
                                    "cancels +0, landed +1; share 1.0; bulk "
                                    f"+{APPLE_BULK:.3f}; buffer calories +400; consumed",
          observed=ph6, verdict=v6, falsifier="the stores not moving fully, or a cancel counted")

    # ---- A7: a cancelled Banana (control 2) ----
    sp7 = spawn("Base.Banana", "A7: the cancelled normal eat; A8 reuses its leftover")
    if sp7["resolved"]:
        ph7 = eat_phase("A7", prev, "Base.Banana", "1", BANANA["calories"], stop=True)
        s7 = snapshot("A7_post", "Base.Banana")
        p7 = to_num(sval(s7, REC + ".lastIntake.share"))
        ph7.update({"kcal": kcal_read(prev, s7), "delta": cdelta(prev, s7),
                    "counters_after": counters(s7), "share": p7,
                    "frac": to_num(sval(s7, REC + ".lastIntake.frac")),
                    "lastIntake": {"fullType": rstr(s7, "lastIntake.fullType"),
                                   "source": rstr(s7, "lastIntake.source")},
                    "buffer": decay_read(prev, s7, "stomach.buffer.calories",
                                         BANANA["calories"] * (p7 or 0.0)),
                    "bulk": decay_read(prev, s7, "stomach.bulk",
                                       BANANA["calories"] * (p7 or 0.0) / 100),
                    "item": item_of(s7), "hunger": hunger_obs(ph7, s7)})
        prev = s7
    else:
        ph7 = {"skipped": "the RCON Banana never resolved client-side"}
        p7 = None
    out["phases"]["A7"] = ph7
    if "skipped" in ph7:
        v7 = "unmeasured"
    else:
        d7 = ph7["delta"]
        k7 = ph7["kcal"]["server_corrected"]
        it7 = ph7["item"]
        if d7.get("cancels") != 1 or d7.get("eats") != 0:
            v7 = "unmeasured"     # the stop never reached serverStop, or the eat completed first
        elif (p7 is not None and 0.0 < p7 < 1.0 and k7 is not None
              and abs(k7 - BANANA["calories"] * p7) <= KCAL_TOL and d7.get("landed") == 1
              and it7["present"] and close(it7["hungChange"], BANANA["hunger"] * (1 - p7), 0.003)
              and ph7["buffer"]["within"]):
            v7 = "as_predicted"
        else:
            v7 = "falsified"
    grade("A7_cancelled", predicted="cancels +1, eats +0, landed +1; share = p in (0, 1); kcal "
                                    "+105 p; buffer +105 p; the Banana not consumed (hungChange "
                                    "-0.16 (1 - p)); onEat_server +1 (serverStop -> eat -> Eat); "
                                    "completes +0",
          observed=ph7, verdict=v7,
          falsifier="cancels +1 with the stores flat (the cancel landed nothing on a normal item: "
                    "arm 8 would then read nothing)")

    # ---- A8: the same Banana under the guard ----
    pre8 = prev
    have = item_of(prev)
    ph8 = {}
    if not have["present"]:
        sp8 = spawn("Base.Banana", "A8: A7 consumed its Banana, so a fresh one for the guard arm")
        ph8["fresh_spawn"] = sp8
        pre8 = snapshot("A8_pre", "Base.Banana")
        prev = pre8
    st = step("A8_item_set", server, "item.set", f"{USER} Base.Banana hungChange {GUARD_HUNG}")
    ph8["item_set"] = st["ack"]
    time.sleep(1.5)
    ph8["item_confirm"] = probe(server, "item.get", f"{USER} Base.Banana")
    conf = ph8["item_confirm"] if isinstance(ph8["item_confirm"], dict) else {}
    hc = to_num(conf.get("hungerChange"))
    ph8["guard_value"] = None if hc is None else abs(hc * 100)
    ph8["guard_armed"] = ph8["guard_value"] is not None and ph8["guard_value"] <= 1
    ph8["id_before"] = conf.get("id")
    ph8["calories_before"] = to_num(conf.get("calories"))
    if ph8["guard_armed"]:
        ph8.update(eat_phase("A8", pre8, "Base.Banana", "1", 0.0, stop=True))
        s8 = snapshot("A8_post", "Base.Banana")
        ph8.update({"kcal": kcal_read(pre8, s8), "delta": cdelta(pre8, s8),
                    "counters_after": counters(s8),
                    "share": to_num(sval(s8, REC + ".lastIntake.share")),
                    "share_before": to_num(sval(pre8, REC + ".lastIntake.share")),
                    "frac": to_num(sval(s8, REC + ".lastIntake.frac")),
                    "lastIntake": {"fullType": rstr(s8, "lastIntake.fullType"),
                                   "source": rstr(s8, "lastIntake.source")},
                    "buffer": decay_read(pre8, s8, "stomach.buffer.calories", 0.0),
                    "bulk": decay_read(pre8, s8, "stomach.bulk", 0.0),
                    "item": item_of(s8), "hunger": hunger_obs(ph8, s8)})
    else:
        ph8["skipped"] = "item.set did not put the Banana under the guard; no eat sent"
    out["phases"]["A8"] = ph8
    if "skipped" in ph8:
        v8 = "unmeasured"
    else:
        d8 = ph8["delta"]
        k8 = ph8["kcal"]["server_corrected"]
        it8 = ph8["item"]
        if d8.get("cancels") != 1 or d8.get("eats") != 0:
            v8 = "unmeasured"     # the stop never reached serverStop, or the eat completed first
        elif (k8 is not None and abs(k8) <= KCAL_TOL and d8.get("landed") == 0
              and d8.get("onEat_server") == 0 and d8.get("completes_server") == 0
              and it8["present"] and it8["id"] == ph8["id_before"]
              and close(it8["hungChange"], float(GUARD_HUNG), 0.0005)
              and close(it8["calories"], ph8["calories_before"], 0.01)
              and ph8["share"] == ph8["share_before"]):
            v8 = "as_predicted"
        else:
            v8 = "falsified"
    grade("A8_guard", predicted="cancels +1 but nothing applied: kcal +0; landed +0; onEat_server "
                                "+0; completes +0; the same Banana still there with hungChange "
                                "-0.005 and its calories unchanged; lastIntake.share unchanged "
                                "(a landing would read 0.03125)",
          observed=ph8, verdict=v8,
          falsifier="any store moving, the item consumed or rescaled, or OnEat firing under the "
                    "guard")

    # ---- X33 verdict ----
    if "unmeasured" in (v6, v7, v8):
        x33, x33v = f"unmeasured: arms A6 {v6}, A7 {v7}, A8 {v8}", "unmeasured"
    elif v6 == v7 == v8 == "as_predicted":
        x33, x33v = ("the three arms differ as predicted: a completed eat moves the stores fully, a "
                     "cancelled normal eat by its progress, a cancelled eat under the guard by "
                     "nothing (no stats, no nutrition, no rescale, no consumption, no OnEat)"), \
            "as_predicted"
    else:
        x33, x33v = f"mixed: A6 {v6}, A7 {v7}, A8 {v8}", "falsified"
    grade("X33", predicted="three arms that differ: A6 full, A7 by progress, A8 nothing",
          observed={"A6": v6, "A7": v7, "A8": v8, "summary": x33,
                    "A7_share": ph7.get("share"), "A8_share_before_after":
                    [ph8.get("share_before"), ph8.get("share")]},
          verdict=x33v, falsifier="A8 moving any store, or A7 flat (no control)")
    out["notes_for_plan6"] = (
        "X33 design hazard: an item pass that rewrites HungerChange must never land a value with "
        "abs(state-modified hunger x 100) <= 1 (a script HungerChange between -1 and 1, or one a "
        "state divisor brings there: rotten /2.2, burnt /3): a cancelled eat of such an item "
        "applies nothing (no stats, no nutrition, no leftover scaling, no consumption, no OnEat), "
        "and the mod's cancel wrapper lands nothing for it either. A8 is the live reading.")

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "x24": x24, "x24_obs": x24obs, "x33": x33,
        "A7_share": ph7.get("share"), "A7_kcal": (ph7.get("kcal") or {}).get("server_corrected"),
        "A8_kcal": (ph8.get("kcal") or {}).get("server_corrected"),
        "field_count_failures": len(out["field_count_failures"]),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
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
        greps = {}
        for name, rx, lim in (("lua_errors", LUAERR_RX, LUAERR_LIMIT),
                              ("intake_lines", INTAKE_RX, INTAKE_LIMIT),
                              ("syncitemfields", SYNC_RX, SYNC_LIMIT)):
            sh = grep_file(server.log_path, rx, limit=lim)
            ch = grep_file(clients[0].console, rx, limit=lim) if clients else []
            greps[name] = {"limit": lim,
                           "server": {"count": len(sh), "saturated": len(sh) >= lim, "lines": sh},
                           "client": {"count": len(ch), "saturated": len(ch) >= lim, "lines": ch}}
        out["greps"] = greps
        out["greps_reading"] = ("server = the server stdout log; client = console.txt, which "
                                "prints each mod's block twice (two Lua states). The intake "
                                "lines are the mod's own NR.log at its configured level, so an "
                                "absent line is the log level, not an absent landing.")
        save(path, out, tl, server)
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
