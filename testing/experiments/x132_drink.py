"""x132-drink -- X13: does a server-side Lua wrapper of the drink action fire, on which side, and
does the mod's own drink wrapper (Plan 2 Task 9) land the intake? The first live run of the
intake engine.

The run id prefix is `x132d` (run id `x132d-<date>-<time>`): the register's run-id pattern
refuses a hyphen in the prefix.

Copied from `_template.py` (house shape; `x132_cost.py` is the Plan 2 sibling). Profile
`x13-drink` (PZTestKit, NutritionRevamp, TKX_DrinkHook in that `Mods=` order). One boot.

The mechanism (read before the run): `drink.action <fullType> [<percentage>]` (client) queues the
game's own `ISDrinkFluidAction`, which the server completes through `updateEat` -- once per
server `update()` (gated `not isClient()`), once per ~100 ms emulated anim event (gated
`isServer()`) and once from `complete` (`updateEat(1)`) (#0085, #2689). TKX_DrinkHook wraps
`updateEat` and `complete` in BOTH Lua states and bumps a per-side counter in that state's own
global modData `TKX_Drink` (`<method>_server` only when isServer(), `<method>_client` only when
isClient()). A client's global modData is its own table, so the `_client` keys are read off the
CLIENT and the `_server` keys off the SERVER; both sides are read at every tag, client first.
The mod's wrapper counts `NutritionRevamp.server.intake.stats.sips` once per server-side
`updateEat` call (`passthrough` on any other side) and lands each sip's litres in the record's
`stomach` (`lastIntake = {fullType, source = "fluid", litres, missing}`).

Mod load order: NutritionRevamp loads before TKX_DrinkHook, so at file load the probe's wrapper
goes OUTSIDE the mod's; at OnServerStarted the mod's install sees its wrapper still in the chain
(`S.class == cls`) and does not re-wrap, and the probe's sees itself outermost. Both therefore
see every call: the prediction `sips == updateEat_server` rests on that.

ITEMS. Every container is spawned SERVER-side by RCON `additem` (a client spawn is unknown to the
server, #0124) and, where the client action needs it, polled until it resolves on the client
before `drink.action` is sent (`drink.action`'s `findOrSpawn` would otherwise client-spawn one).
DEVIATION FROM THE BRIEF, decided before the run: P3 drinks `Base.JuiceBox` at 0.5, not a second
`Base.Pop2`. An emptied Pop2 stays a `Base.Pop2` with an empty container (exp05b-20260910-093307
`drinks.pop2_half.drink.candidates[0].empty = true`), and `findOrSpawn` takes
`getFirstTypeRecurse`, i.e. P1's emptied can, so a second Pop2 action would queue on the empty
can and fail `isValidStart`. No harness command removes an item. The JuiceBox is the other
seeded fluid (JuiceGrape), a fixed single-fluid container of 0.2 L that exp05b measured whole
(+80 kcal), so the half arm still tests the fraction and adds a second per-fluid seed.

PHASES (order P0, P1, P3, P2 -- P2 last so the FOOD_EATEN moodle gate of `isValidStart` sees the
fewest drinks before the last ACTION):

  P0  baselines after the P1 can is spawned: the probe counters (both sides), the mod's stats
      and record (server), the mirror (client), `nutrition.get` client then server, plus a second
      server calorie read ~6 s later for the calorie drift rate. Expected: the record exists with
      the stomach seeded full (`stomach.bulk` = K.stomach.FULL_BULK = 8.0 less whatever the
      kinetics minutes since first sight emptied; `stomachFill` near 1.0). A bulk of 0 or an
      absent record is a finding.
  P1  client `drink.action Base.Pop2` (full can, 0.3 L Cola). Poll `nutrition.get` client then
      server until the server's calories rose by ~120 (drift-corrected) or 20 s, settle, read
      everything again.
      Prediction: updateEat_server >= 1, updateEat_client == 0, complete_server == 1,
      complete_client == 0 (the eat-path result #0928 mirrored); sips >= 1 and sips ==
      updateEat_server; stomach.bulk rose by bulkOf(Cola x 0.3 L) = 3.87 after the kinetics
      decay correction; lastIntake.source == "fluid", fullType "Base.Pop2"; failures unchanged;
      calories +120 (#0634) through the timed action (#0148).
      Falsifiers: counters 0/0 with the calories risen (the Lua route is silent though the fluid
      path ran -- B7's negative); sips ~= updateEat_server (a composition fault between the two
      wraps); bulk unchanged with sips > 0 (the capture ran, the landing failed -- lastError).
  P3  client `drink.action Base.JuiceBox 0.5`: calories +40 (half of exp05b's 80); bulk rises by
      bulkOf(JuiceGrape x 0.1 L) = 1.265; lastIntake.fullType "Base.JuiceBox"; complete +1.
  P2  the control: a fresh Pop2 RCON-spawned, then server `drink admin Base.Pop2` (the shipped
      command: one direct DrinkFluid with the timed action taken OFF). Prediction: calories
      +120 while the probe counters, sips and landed do NOT move, the bulk does not rise, and
      lastIntake still names P3's JuiceBox.

THE BULK ARITHMETIC (from the committed seed `NR_Data_Nutrients.lua` and `NR_Kernel_Stomach.lua`):
bulkOf(v) = calories/100 + fibre*0.5 + water/100. Cola per litre {calories 400, fibre 0, water
890}; JuiceGrape per litre {calories 400, fibre 0.5, water 840}. Kinetics empties the bulk once
per game minute by exp(-ln2 * dtH / (HALF_TIME_H 2.0 * compositionScale)), the scale 1.0 for
every buffer this session builds (no lipids; JuiceGrape's fibre moves it by < 0.4 %). The
ingest-only delta is therefore bulkAfter - bulkBefore * decay(kineticsAge_after -
kineticsAge_before), and it lies in [pred * decay, pred] depending on when in the window the sips
landed.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_...`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
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

from _common import ask, doctor, git_dirty, git_say, hard_kill, num, save   # noqa: E402
from pzt import fixture as fx, profile                                      # noqa: E402
from pzt.paths import new_run_dir                                           # noqa: E402
from pzt.session import (Timeline, grep_file, make_client, make_server,    # noqa: E402
                         teardown, verify)

PROFILE = "x13-drink"
SESSION = ("X13: client drink.action Base.Pop2 (the real ISDrinkFluidAction) against "
           "TKX_DrinkHook's per-side updateEat/complete counters and the mod's own drink wrapper "
           "(stats.sips, the record's stomach.bulk, lastIntake); drink.action Base.JuiceBox 0.5; "
           "the shipped server drink admin Base.Pop2 as the control")
ARTIFACT = "drink.json"
USER = "admin"
# Task 12 landed the harness commands this session uses (2b8e702, 78328a4, 7128242, 7710d2d);
# this boot is their smoke test, so the acceptance run named is the last accepted boot.
ACCEPTANCE_RUN = "x132c-20261005-041640"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

# ---- the probe counters ------------------------------------------------------------------------
COUNTER_KEYS = ["updateEat_server", "updateEat_client", "complete_server", "complete_client"]
COUNTER_ARGS = "global:TKX_Drink " + " ".join(COUNTER_KEYS)
COUNTER_FIELD_COUNT = 4

# ---- the lua.global reads, per side ------------------------------------------------------------
REC = "NutritionRevamp.server.store.records." + USER
SERVER_GLOBALS = [
    "NutritionRevamp.version",                       # tier-(a) control
    "TK.version",                                    # the _G walk's own control
    "TKX_DrinkHook.updateEat", "TKX_DrinkHook.complete",
    "NutritionRevamp.server.intake.wrappedDrink",
    "NutritionRevamp.server.intake.stats.sips",
    "NutritionRevamp.server.intake.stats.landed",
    "NutritionRevamp.server.intake.stats.failures",
    "NutritionRevamp.server.intake.stats.passthrough",
    "NutritionRevamp.server.intake.lastError",
    "NutritionRevamp.server.kinetics.stats.minutes",
    REC + ".stomach.bulk",
    REC + ".kineticsAge",                            # read right beside the bulk: the decay window
    REC + ".stomachFill",
    REC + ".lastIntake.source",
    REC + ".lastIntake.litres",                      # the LAST sip's litres, not the total
    REC + ".lastIntake.fullType",
    REC + ".stomach.buffer.calories",
    REC + ".stomach.buffer.water",
]
CLIENT_GLOBALS = [
    "NutritionRevamp.version",
    "TK.version",
    "TKX_DrinkHook.updateEat", "TKX_DrinkHook.complete",
    "NutritionRevamp.server.intake.stats.sips",      # the server/ file also runs in the client VM
    "NutritionRevamp.server.intake.stats.passthrough",
    "NutritionRevamp.client.mirror.stomachFill",     # rider: expected STALE
    "NutritionRevamp.client.received",
]

# ---- the seed and kernel constants (committed NR_Data_Nutrients.lua / NR_Kernel_Stomach.lua) ----
COLA = {"calories": 400.0, "fibre": 0.0, "water": 890.0}        # per litre, SEED Cola
JUICE = {"calories": 400.0, "fibre": 0.5, "water": 840.0}       # per litre, SEED JuiceGrape
HALF_TIME_H = 2.0
FULL_BULK = 8.0


def bulk_of(seed, litres):
    return (seed["calories"] * litres) / 100 + (seed["fibre"] * litres) * 0.5 \
        + (seed["water"] * litres) / 100


POP2_LITRES, JUICE_LITRES = 0.3, 0.2
P1_PRED_BULK = bulk_of(COLA, POP2_LITRES)               # 3.87
P3_FRACTION = 0.5
P3_PRED_BULK = bulk_of(JUICE, JUICE_LITRES * P3_FRACTION)  # 1.265
P1_PRED_KCAL, P3_PRED_KCAL, P2_PRED_KCAL = 120.0, 40.0, 120.0   # #0634 / exp05b juicebox 80 x 0.5
KCAL_TOL = 5.0
BULK_TOL_FRAC, BULK_TOL_ABS = 0.03, 0.06

SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
POLL_S, POLL_MAX_S, SETTLE_S = 1.0, 20.0, 2.0
DRIFT_GAP_S = 6.0

# ---- console greps (compiled; limits >= 2x predicted; a client prints each block twice) --------
LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table")
INTAKE_RX = re.compile(r"intake:")
SYNC_RX = re.compile(r"SyncItemFields", re.IGNORECASE)
LUAERR_LIMIT, INTAKE_LIMIT, SYNC_LIMIT = 20, 60, 10


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


def counters(reply):
    """The four counters out of a witness.moddata reply (string values -> numbers; an absent
    key reads as 0 in the arithmetic and is listed in `missing`), plus the field-count check."""
    if not isinstance(reply, dict):
        return {"ok": False, "values": None, "missing": None, "count": None, "count_ok": False}
    vals = reply.get("values") or {}
    res = {k: (num(vals.get(k)) if vals.get(k) is not None else 0.0) for k in COUNTER_KEYS}
    count = reply.get("count")
    return {"ok": True, "values": res, "missing": reply.get("missing"), "count": count,
            "count_ok": count == COUNTER_FIELD_COUNT, "keys": reply.get("keys")}


def cal(reply):
    return num(reply.get("calories")) if isinstance(reply, dict) else None


def nutrition_pair(tag):
    """`nutrition.get` client FIRST, then server, each wall-bracketed."""
    cr = probe(c, "nutrition.get", "")
    sr = probe(server, "nutrition.get", USER)
    return {"tag": tag, "wall": wall(), "client": cr, "server": sr,
            "client_calories": cal(cr), "server_calories": cal(sr)}


def snapshot(tag):
    """Every read at one tag: the nutrition pair first (closest to the action), then the probe
    counters client then server, then the lua.global walks client then server."""
    snap = {"tag": tag, "wall_start": wall()}
    snap["nutrition"] = nutrition_pair(tag)
    cm = probe(c, "witness.moddata", COUNTER_ARGS)
    sm = probe(server, "witness.moddata", COUNTER_ARGS)
    snap["moddata"] = {"client": cm, "server": sm}
    snap["counters"] = {"client": counters(cm), "server": counters(sm)}
    for side_name in ("client", "server"):
        if not snap["counters"][side_name]["count_ok"]:
            out["field_count_failures"].append({"tag": tag, "side": side_name,
                                                "count": snap["counters"][side_name]["count"],
                                                "expected": COUNTER_FIELD_COUNT})
    snap["globals"] = {"client": {}, "server": {}}
    for name in CLIENT_GLOBALS:
        snap["globals"]["client"][name] = probe(c, "lua.global", name)
    for name in SERVER_GLOBALS:
        snap["globals"]["server"][name] = probe(server, "lua.global", name)
    snap["wall_end"] = wall()
    out["snapshots"][tag] = snap
    save(path, out, tl, server)
    return snap


def sval(snap, name, side="server"):
    return gv(snap["globals"][side].get(name))


def eff_counters(snap):
    """The per-side counters as graded: `_server` keys off the SERVER's table, `_client` keys
    off the CLIENT's (each Lua state writes only its own global modData)."""
    s = (snap["counters"]["server"].get("values") or {})
    cl = (snap["counters"]["client"].get("values") or {})
    return {"updateEat_server": s.get("updateEat_server"),
            "complete_server": s.get("complete_server"),
            "updateEat_client": cl.get("updateEat_client"),
            "complete_client": cl.get("complete_client"),
            "server_table_client_keys": {"updateEat_client": s.get("updateEat_client"),
                                         "complete_client": s.get("complete_client")},
            "client_table_server_keys": {"updateEat_server": cl.get("updateEat_server"),
                                         "complete_server": cl.get("complete_server")}}


def diff(a, b):
    if a is None or b is None:
        return None
    return b - a


def decay(dt_h):
    if dt_h is None:
        return None
    return math.exp(-0.6931471805599453 * max(dt_h, 0.0) / (HALF_TIME_H * 1.0))


def bulk_read(pre, post, pred):
    b0, b1 = num(sval(pre, REC + ".stomach.bulk")), num(sval(post, REC + ".stomach.bulk"))
    k0, k1 = num(sval(pre, REC + ".kineticsAge")), num(sval(post, REC + ".kineticsAge"))
    dt = diff(k0, k1)
    d = decay(dt)
    corrected = (b1 - b0 * d) if (b0 is not None and b1 is not None and d is not None) else None
    lo = (pred * d) if (pred is not None and d is not None) else None
    tol = (BULK_TOL_FRAC * pred + BULK_TOL_ABS) if pred is not None else BULK_TOL_ABS
    within = None
    if corrected is not None and lo is not None:
        within = (lo - tol) <= corrected <= (pred + tol)
    return {"bulk_before": b0, "bulk_after": b1, "raw_delta": diff(b0, b1),
            "kineticsAge_before": k0, "kineticsAge_after": k1, "dt_h": dt, "decay": d,
            "ingest_delta_corrected": corrected, "predicted": pred,
            "accept_band": [None if lo is None else lo - tol, None if pred is None else pred + tol],
            "within": within}


def spawn(full_type, why, client_resolve=True):
    """RCON additem, then (when the client action needs the item) poll the CLIENT until the
    instance resolves there."""
    ok, reply = server.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        if not client_resolve:
            row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": None,
                                    "note": "server-side use only; no client resolve needed"})
            break
        seen = probe(c, "witness.fields", f"item {USER}/{full_type} getID")
        res = seen.get("resolved") if isinstance(seen, dict) else None
        fields = (seen.get("fields") or {}) if isinstance(seen, dict) else {}
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": fields.get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"]) \
        if client_resolve else None
    row["server_item_get"] = probe(server, "item.get", f"{USER} {full_type}")
    out["spawns"].append(row)
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    save(path, out, tl, server)
    return row


def drift_rate():
    p0 = out["phases"].get("P0", {}).get("drift") or {}
    return p0.get("kcal_per_s")


def action_phase(label, full_type, arg, pred_kcal):
    """Queue drink.action on the client, poll the nutrition pair until the server's calories
    rose to the prediction (drift-corrected) or POLL_MAX_S, then settle."""
    ph = {"label": label, "fullType": full_type, "arg": arg}
    ack = step(f"{label}_drink_action", c, "drink.action", f"{full_type} {arg}".strip())
    ph["ack"] = ack["ack"]
    ph["queued_wall"] = ack["wall_after"]
    a = ack["ack"] if isinstance(ack["ack"], dict) else {}
    ph["spawned"] = a.get("spawned")
    ph["filledRatioBefore"] = a.get("filledRatioBefore")
    base_srv = out["phases"][label + "_pre"]["server_calories"]
    base_cli = out["phases"][label + "_pre"]["client_calories"]
    rate = drift_rate() or 0.0
    t_base = out["phases"][label + "_pre"]["wall"]
    ph["polls"] = []
    first_srv, first_cli = None, None
    while True:
        time.sleep(POLL_S)
        p = nutrition_pair(f"{label}_poll")
        el = p["wall"] - t_base
        ds = diff(base_srv, p["server_calories"])
        dc = diff(base_cli, p["client_calories"])
        ds_corr = None if ds is None else ds - rate * el
        dc_corr = None if dc is None else dc - rate * el
        row = {"wall": p["wall"], "since_queue": round(p["wall"] - ph["queued_wall"], 3),
               "server_calories": p["server_calories"], "client_calories": p["client_calories"],
               "server_delta_corr": ds_corr, "client_delta_corr": dc_corr}
        ph["polls"].append(row)
        if first_srv is None and ds_corr is not None and ds_corr > 1.0:
            first_srv = row["since_queue"]
        if first_cli is None and dc_corr is not None and dc_corr > 1.0:
            first_cli = row["since_queue"]
        done_srv = ds_corr is not None and ds_corr >= pred_kcal - 2.0
        done_cli = dc_corr is not None and dc_corr >= pred_kcal - 2.0
        if (done_srv and done_cli) or (p["wall"] - ph["queued_wall"]) >= POLL_MAX_S:
            break
    ph["first_server_move_since_queue_s"] = first_srv
    ph["first_client_move_since_queue_s"] = first_cli
    time.sleep(SETTLE_S)
    ph["settle_s"] = SETTLE_S
    save(path, out, tl, server)
    return ph


def kcal_read(pre, post):
    """The server calorie delta between two snapshots, raw and drift-corrected."""
    a, b = pre["nutrition"]["server_calories"], post["nutrition"]["server_calories"]
    ca, cb = pre["nutrition"]["client_calories"], post["nutrition"]["client_calories"]
    el = post["nutrition"]["wall"] - pre["nutrition"]["wall"]
    rate = drift_rate() or 0.0
    raw = diff(a, b)
    craw = diff(ca, cb)
    return {"server_before": a, "server_after": b, "server_raw": raw,
            "server_corrected": None if raw is None else raw - rate * el,
            "client_raw": craw, "client_corrected": None if craw is None else craw - rate * el,
            "elapsed_s": round(el, 3), "drift_kcal_per_s": rate}


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x132d-dry-run", None) if DRY_RUN else new_run_dir("x132d")
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
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_DrinkHook"),
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"COLA_per_litre": COLA, "JUICE_per_litre": JUICE, "HALF_TIME_H": HALF_TIME_H,
                  "FULL_BULK": FULL_BULK, "P1_PRED_BULK": P1_PRED_BULK,
                  "P3_PRED_BULK": P3_PRED_BULK, "P1_PRED_KCAL": P1_PRED_KCAL,
                  "P3_PRED_KCAL": P3_PRED_KCAL, "P2_PRED_KCAL": P2_PRED_KCAL,
                  "KCAL_TOL": KCAL_TOL, "BULK_TOL_FRAC": BULK_TOL_FRAC,
                  "BULK_TOL_ABS": BULK_TOL_ABS, "POLL_S": POLL_S, "POLL_MAX_S": POLL_MAX_S,
                  "SETTLE_S": SETTLE_S, "COUNTER_FIELD_COUNT": COUNTER_FIELD_COUNT},
    "deviation": ("P3 drinks Base.JuiceBox 0.5 rather than a second Base.Pop2 0.5: an emptied "
                  "Pop2 stays a Base.Pop2 (exp05b), drink.action's findOrSpawn takes the first "
                  "one (P1's empty can), and no harness command removes an item. Decided before "
                  "the run."),
    "world_changes": {"restored": "the run's own copy of the fixture (fx.restore_server); "
                                  "nothing written back to the golden fixture",
                      "left_in_place": ["RCON-spawned Base.Pop2 x2 and Base.JuiceBox x1 in "
                                        "admin's inventory in this run's copy",
                                        "the record's stomach and lastIntake in this run's copy"]},
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
    sp1 = spawn("Base.Pop2", "P1: RCON first -- drink.action's findOrSpawn falls back to a "
                             "CLIENT spawn the server never hears of (#0124)")
    s0 = snapshot("P0")
    d0 = probe(server, "nutrition.get", USER)
    t_d0 = wall()
    time.sleep(DRIFT_GAP_S)
    d1 = probe(server, "nutrition.get", USER)
    t_d1 = wall()
    dk = diff(cal(d0), cal(d1))
    out["phases"]["P0"] = {
        "drift": {"first": cal(d0), "second": cal(d1), "wall": [t_d0, t_d1],
                  "kcal_per_s": (dk / (t_d1 - t_d0)) if dk is not None and t_d1 > t_d0 else None},
        "record_bulk": sval(s0, REC + ".stomach.bulk"),
        "record_fill": sval(s0, REC + ".stomachFill"),
        "kineticsAge": sval(s0, REC + ".kineticsAge"),
        "wrappedDrink": sval(s0, "NutritionRevamp.server.intake.wrappedDrink"),
        "counters": eff_counters(s0),
        "version": {"client": sval(s0, "NutritionRevamp.version", "client"),
                    "server": sval(s0, "NutritionRevamp.version")},
    }
    b0 = num(out["phases"]["P0"]["record_bulk"])
    grade("P0", predicted="the admin record exists with its stomach seeded full: bulk at or just "
                          "under FULL_BULK 8.0 (kinetics minutes since first sight empty it on "
                          "the 2 h half-time), stomachFill near 1.0; the drink wrapper installed; "
                          "every probe counter absent or 0",
          observed=out["phases"]["P0"],
          verdict=("unmeasured" if b0 is None else
                   ("as_predicted" if 6.0 <= b0 <= FULL_BULK + 1e-6 else "falsified")),
          falsifier="bulk 0 or absent (the seed did not run), or a counter already above 0")

    # ================= P1 -- the Lua route, a full Pop2 =====================================
    out["phases"]["P1_pre"] = {"server_calories": s0["nutrition"]["server_calories"],
                               "client_calories": s0["nutrition"]["client_calories"],
                               "wall": s0["nutrition"]["wall"]}
    if not sp1["resolved"]:
        out["phases"]["P1"] = {"skipped": "the RCON Pop2 never resolved client-side; drink.action "
                                          "was NOT sent (it would client-spawn one)"}
        note("P1 skipped -- spawn never reached the client")
    else:
        out["phases"]["P1"] = action_phase("P1", "Base.Pop2", "1.0", P1_PRED_KCAL)
    s1 = snapshot("P1_post")

    # ================= P3 -- a JuiceBox at half (the deviation; see the docstring) ==========
    sp3 = spawn("Base.JuiceBox", "P3: the half arm on a second seeded fluid")
    s3pre = snapshot("P3_pre")
    out["phases"]["P3_pre"] = {"server_calories": s3pre["nutrition"]["server_calories"],
                               "client_calories": s3pre["nutrition"]["client_calories"],
                               "wall": s3pre["nutrition"]["wall"]}
    if not sp3["resolved"]:
        out["phases"]["P3"] = {"skipped": "the RCON JuiceBox never resolved client-side"}
        note("P3 skipped -- spawn never reached the client")
    else:
        out["phases"]["P3"] = action_phase("P3", "Base.JuiceBox", str(P3_FRACTION), P3_PRED_KCAL)
    s3 = snapshot("P3_post")

    # ================= P2 -- the control: the shipped server drink ==========================
    sp2 = spawn("Base.Pop2", "P2: a full can for the server drink (picks the fullest)",
                client_resolve=False)
    s2pre = snapshot("P2_pre")
    dr = step("P2_drink", server, "drink", f"{USER} Base.Pop2 1.0")
    out["phases"]["P2"] = {"ack": dr["ack"]}
    time.sleep(SETTLE_S)
    s2 = snapshot("P2_post")

    # ================= grading ==============================================================
    c0, c1, c3p, c3, c2p, c2 = (eff_counters(x) for x in (s0, s1, s3pre, s3, s2pre, s2))

    def cdelta(a, b):
        return {k: diff(a.get(k), b.get(k)) for k in
                ("updateEat_server", "updateEat_client", "complete_server", "complete_client")}

    def sdelta(a, b, name, side="server"):
        return diff(num(sval(a, name, side)), num(sval(b, name, side)))

    SIPS = "NutritionRevamp.server.intake.stats.sips"
    LANDED = "NutritionRevamp.server.intake.stats.landed"
    FAIL = "NutritionRevamp.server.intake.stats.failures"
    PASS = "NutritionRevamp.server.intake.stats.passthrough"

    # ---- P1a: per-side counters ----
    k1 = kcal_read(s0, s1)
    cd1 = cdelta(c0, c1)
    moved1 = k1["server_corrected"] is not None and k1["server_corrected"] > 1.0
    obs1a = {"counter_delta": cd1, "counters_after": c1, "kcal": k1,
             "lua_counters": {sd: {"updateEat": sdelta(s0, s1, "TKX_DrinkHook.updateEat", sd),
                                   "complete": sdelta(s0, s1, "TKX_DrinkHook.complete", sd)}
                              for sd in ("client", "server")}}
    if not moved1 and not ((cd1["updateEat_server"] or 0) > 0):
        v1a = "unmeasured"
    elif ((cd1["updateEat_server"] or 0) >= 1 and (cd1["updateEat_client"] or 0) == 0
          and (cd1["complete_server"] or 0) == 1 and (cd1["complete_client"] or 0) == 0):
        v1a = "as_predicted"
    else:
        v1a = "falsified"
    grade("P1a_sides", predicted="updateEat_server >= 1, updateEat_client == 0, complete_server "
                                 "== 1, complete_client == 0 (the eat path's server-only result "
                                 "#0928, mirrored on the drink path)",
          observed=obs1a, verdict=v1a,
          falsifier="counters 0/0 with the calories risen (the Lua route is silent though the "
                    "fluid path ran: B7's negative), or a client-side fire")

    # ---- P1b: the mod sees every sip ----
    sips1 = sdelta(s0, s1, SIPS)
    landed1 = sdelta(s0, s1, LANDED)
    pass1c = sdelta(s0, s1, PASS, "client")
    obs1b = {"sips_delta": sips1, "updateEat_server_delta": cd1["updateEat_server"],
             "landed_delta": landed1, "client_passthrough_delta": pass1c,
             "client_sips_delta": sdelta(s0, s1, SIPS, "client")}
    if sips1 is None or cd1["updateEat_server"] is None:
        v1b = "unmeasured"
    elif sips1 >= 1 and sips1 == cd1["updateEat_server"]:
        v1b = "as_predicted"
    else:
        v1b = "falsified"
    grade("P1b_sips", predicted="stats.sips >= 1 and == the probe's updateEat_server (both wraps "
                                "see every call; the probe outermost)",
          observed=obs1b, verdict=v1b,
          falsifier="sips ~= updateEat_server: a composition fault between the two wraps")

    # ---- P1c: the landing ----
    br1 = bulk_read(s0, s1, P1_PRED_BULK)
    fail1 = sdelta(s0, s1, FAIL)
    obs1c = {"bulk": br1, "failures_delta": fail1,
             "lastIntake": {"source": sval(s1, REC + ".lastIntake.source"),
                            "fullType": sval(s1, REC + ".lastIntake.fullType"),
                            "litres_last_sip": sval(s1, REC + ".lastIntake.litres")},
             "lastError": s1["globals"]["server"].get("NutritionRevamp.server.intake.lastError"),
             "stomachFill_after": sval(s1, REC + ".stomachFill"),
             "buffer_after": {"calories": sval(s1, REC + ".stomach.buffer.calories"),
                              "water": sval(s1, REC + ".stomach.buffer.water")}}
    if br1["within"] is None:
        v1c = "unmeasured"
    elif (br1["within"] and obs1c["lastIntake"]["source"] == "fluid"
          and obs1c["lastIntake"]["fullType"] == "Base.Pop2" and (fail1 or 0) == 0):
        v1c = "as_predicted"
    else:
        v1c = "falsified"
    grade("P1c_landing", predicted=f"stomach.bulk ingest delta (decay-corrected) in "
                                   f"[{P1_PRED_BULK:.3f} x decay, {P1_PRED_BULK:.3f}]; "
                                   "lastIntake.source fluid, fullType Base.Pop2; failures +0",
          observed=obs1c, verdict=v1c,
          falsifier="bulk unchanged with sips > 0 (the capture ran, the landing failed: "
                    "lastError), or a failure counted")

    # ---- P1d: the timed-action route delivers the whole can (#0148) ----
    v1d = ("unmeasured" if k1["server_corrected"] is None else
           ("as_predicted" if abs(k1["server_corrected"] - P1_PRED_KCAL) <= KCAL_TOL
            else "falsified"))
    grade("P1d_calories", predicted="server calories +120 (drift-corrected) through the timed "
                                    "action, the per-sip DrinkFluid calls summing to the whole "
                                    "can (#0634 measured the direct call)",
          observed=k1, verdict=v1d,
          falsifier="a delta off 120 by more than the tolerance: the incremental route does not "
                    "sum to the container")

    # ---- P1e: client arrival (rider for #0671) ----
    p1 = out["phases"].get("P1") or {}
    obs1e = {"first_server_move_since_queue_s": p1.get("first_server_move_since_queue_s"),
             "first_client_move_since_queue_s": p1.get("first_client_move_since_queue_s"),
             "client_kcal_corrected": k1["client_corrected"], "poll_s": POLL_S}
    fs, fc_ = obs1e["first_server_move_since_queue_s"], obs1e["first_client_move_since_queue_s"]
    if fs is None or fc_ is None:
        v1e = "unmeasured"
    elif (k1["client_corrected"] is not None
          and abs(k1["client_corrected"] - P1_PRED_KCAL) <= KCAL_TOL and fc_ - fs <= 2.5):
        v1e = "as_predicted"
    else:
        v1e = "falsified"
    grade("P1e_client_arrival", predicted="the client's calories arrive within one stats-packet "
                                          "period of the server's (poll granularity ~1 s, so a "
                                          "lag <= 2.5 s) and total +120 (#0649)",
          observed=obs1e, verdict=v1e,
          falsifier="the client never shows the calories, or lags the server by more than 2.5 s")

    # ---- P1f: the mirror rider ----
    m0 = sval(s0, "NutritionRevamp.client.mirror.stomachFill", "client")
    m1 = sval(s1, "NutritionRevamp.client.mirror.stomachFill", "client")
    grade("P1f_mirror", predicted="the client mirror's stomachFill is STALE (sent at first sight "
                                  "and on request, not per sip): unchanged",
          observed={"before": m0, "after": m1,
                    "received_before": sval(s0, "NutritionRevamp.client.received", "client"),
                    "received_after": sval(s1, "NutritionRevamp.client.received", "client")},
          verdict=("unmeasured" if m0 is None and m1 is None else
                   ("trivial" if m0 == m1 else "falsified")),
          falsifier="the mirror moved with the drink (it would mean a per-intake push)")

    # ---- P3: the half arm ----
    k3 = kcal_read(s3pre, s3)
    cd3 = cdelta(c3p, c3)
    br3 = bulk_read(s3pre, s3, P3_PRED_BULK)
    sips3 = sdelta(s3pre, s3, SIPS)
    obs3 = {"kcal": k3, "counter_delta": cd3, "bulk": br3, "sips_delta": sips3,
            "landed_delta": sdelta(s3pre, s3, LANDED), "failures_delta": sdelta(s3pre, s3, FAIL),
            "lastIntake": {"source": sval(s3, REC + ".lastIntake.source"),
                           "fullType": sval(s3, REC + ".lastIntake.fullType"),
                           "litres_last_sip": sval(s3, REC + ".lastIntake.litres")},
            "phase": out["phases"].get("P3")}
    if k3["server_corrected"] is None or br3["within"] is None:
        v3 = "unmeasured"
    elif not (k3["server_corrected"] > 1.0):
        v3 = "unmeasured"      # the action never delivered: nothing about the half was read
    elif (abs(k3["server_corrected"] - P3_PRED_KCAL) <= KCAL_TOL and br3["within"]
          and obs3["lastIntake"]["fullType"] == "Base.JuiceBox"
          and (cd3["complete_server"] or 0) == 1 and sips3 == cd3["updateEat_server"]):
        v3 = "as_predicted"
    else:
        v3 = "falsified"
    grade("P3_half", predicted=f"JuiceBox at 0.5: calories +{P3_PRED_KCAL:.0f}; bulk ingest delta "
                               f"in [{P3_PRED_BULK:.3f} x decay, {P3_PRED_BULK:.3f}]; lastIntake "
                               "Base.JuiceBox; complete_server +1; sips == updateEat_server",
          observed=obs3, verdict=v3,
          falsifier="calories or bulk off the half, or the sip counts disagree")

    # ---- P2: the control ----
    k2 = kcal_read(s2pre, s2)
    cd2 = cdelta(c2p, c2)
    br2 = bulk_read(s2pre, s2, 0.0)
    sips2 = sdelta(s2pre, s2, SIPS)
    ack2 = dr["ack"] if isinstance(dr["ack"], dict) else {}
    ack_delta = (ack2.get("delta") or {}) if isinstance(ack2.get("delta"), dict) else {}
    obs2 = {"kcal": k2, "ack_delta_calories": ack_delta.get("calories"),
            "ack_selected": ack2.get("selected"), "counter_delta": cd2, "sips_delta": sips2,
            "landed_delta": sdelta(s2pre, s2, LANDED), "bulk": br2,
            "lastIntake_fullType_after": sval(s2, REC + ".lastIntake.fullType")}
    ackc = num(ack_delta.get("calories"))
    quiet = all((cd2[k] or 0) == 0 for k in cd2) and (sips2 or 0) == 0 \
        and (obs2["landed_delta"] or 0) == 0
    bulk_flat = br2["ingest_delta_corrected"] is not None and \
        abs(br2["ingest_delta_corrected"]) <= BULK_TOL_ABS
    if ackc is None:
        v2 = "unmeasured"
    elif abs(ackc - P2_PRED_KCAL) <= KCAL_TOL and quiet and bulk_flat \
            and obs2["lastIntake_fullType_after"] == "Base.JuiceBox":
        v2 = "as_predicted"
    else:
        v2 = "falsified"
    grade("P2_control", predicted="the shipped server drink moves calories +120 while the probe "
                                  "counters, sips and landed stay put, the bulk does not rise and "
                                  "lastIntake still names P3's JuiceBox",
          observed=obs2, verdict=v2,
          falsifier="a counter or sips moving on the direct DrinkFluid call (the wrapper would "
                    "see more than the action route), or the stores not moving (no control)")

    # ---- X13 ----
    if v1a == "as_predicted" and v2 == "as_predicted":
        x13, xv = "settled CAN: the drink action's updateEat and complete fire server-side only", \
            "as_predicted"
    elif v1a == "falsified" and v2 == "as_predicted" and (cd1["updateEat_server"] or 0) == 0:
        x13, xv = "B7 negative: the Lua route is silent though the fluid path ran", "falsified"
    elif v1a == "unmeasured":
        x13, xv = "unmeasured: the P1 drink never delivered", "unmeasured"
    else:
        x13, xv = "mixed: see P1a and P2", "falsified"
    grade("X13", predicted="P1's server counters fire and the client's do not, with P2 as the "
                           "control -> B7 UNKNOWN -> CAN",
          observed={"P1a": v1a, "P2": v2, "P1b": v1b, "P1c": v1c, "summary": x13},
          verdict=xv, falsifier="0/0 against a moving control, or a client fire")

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "counters_P1_delta": cd1, "sips_P1_delta": sips1, "landed_P1_delta": landed1,
        "bulk_P1": br1, "bulk_P3": br3, "kcal_P1": k1["server_corrected"],
        "kcal_P3": k3["server_corrected"], "kcal_P2_ack": ackc,
        "counters_after_all": c2,
        "sips_total": num(sval(s2, SIPS)),
        "field_count_failures": len(out["field_count_failures"]),
        "x13": x13,
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
