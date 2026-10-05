"""x151-water-gate -- Plan 4 Task 4, the water gate: the thermoregulator getters read server-side
(A, with the climate override), the drink -> pool landing (B), the auto-drink bracket (C), world
water through ISTakeWaterAction (D), the fluids multiplier under a walk (E) and one tick-rate read
(F). ONE boot, profile `x15-water` (PZTestKit + NutritionRevamp Mode 1 LegacyMirror +
TKX_ThirstWatch; `Nutrition = false`; DayLength 1, so a game hour is 37.5 s wall and a game minute
0.625 s). The run id prefix is `x151w`. Copied from `x141_activity_gate.py` (provenance, client-first
pairs, wall-bracketed steps, predictions/verdicts, `to_num`, the persist/step shape).

THE MOD ON THIS BOOT is HEAD's tree (Plan 3's handler and Task 2's 31-key vector): no thirst view
yet -- vanilla's thirst drain still runs in the fast kernel, the handler calls `autoDrink` on every
pass (NR_Server_Fast.lua `h.autoDrink(p)`), and `record.pool` is Plan 2's accumulator (no drain).
The record is read off the server's global modData `NutritionRevamp.players` (`admin.pool.water`,
`admin.stomach.buffer.water`, ...), the client's mirror through `lua.global
NutritionRevamp.client.mirror.pool_water`, the drink wrapper's counters through `lua.global
NutritionRevamp.server.intake.stats.*` on the server.

THE SERVER VIEW. `TKX_ThirstWatch`, armed per window with `globalmoddata.set TKX_ThirstWatch arm
<s>`, samples the first online player every server tick: thirst, fluidsMult, core, extAir,
bodyFluids, wetness -> flat keys first_/last_/min_/max_/n_<field>, absent_<field>, raw_1..raw_50
(the first 50 ticks), samples, windowMs, status. `finish` writes only what the window saw, so
before every window the driver resets n_<field> to 0 and absent_<field> to "reset" for all six
fields: a stale key cannot pass for this window's. Paired polls ride every window: client
`witness.chain` FIRST, then server `witness.chain admin`, of the thermoregulator getters
(getFluidsMultiplier, getCoreTemperature, getExternalAirTemperature, getBodyFluids,
getEnergyMultiplier -- the last is #0594's quantity).

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. B1 spawns `Base.CanteenMilitaryFull` by RCON `additem`, not `Base.WaterBottle` by
     `inventory.add`: (a) the WaterBottle script has `PickRandomFluid = true` over Water and
     CarbonatedWater, and the seed table (NR_Data_Nutrients.lua) carries no CarbonatedWater row, so a
     carbonated draw would land water 0 with `missing`; the canteen's only fluid is Water (0.9 L);
     (b) `inventory.add` is server-only (its comment: the add is not sent to the client), and
     `drink.action` is a CLIENT command whose `findOrSpawn` would then client-spawn a second copy;
     RCON `additem` reaches the client (x132d's route), and the client copy is polled until it
     resolves.
  2. B1/B2 shapes: `fluid.fill` has NO inventory search (it always AddItem's on the client), so the
     "server-spawned bottle found by fluid.fill" shape does not exist; B1 is the server-spawned
     pre-filled canteen and B2 the client `fluid.fill` of a `Base.Sportsbottle` (a different type,
     so `findOrSpawn`'s getFirstTypeRecurse cannot pick B1's emptied canteen). B2 runs LAST before F:
     a drink of an item the server never heard of may raise, and the -debug client parks on a raise.
  3. C runs three thirst levels: C1 0.09 (under the 0.1 gate: no sip predicted), C2 0.3 (the
     2 x thirst branch: 0.6 L of 0.9 L), C3 0.5 on the remaining 0.3 L (the container branch).
     The amendments' 0.5 alone cannot separate the two branches of min(amount, 2 x thirst).
  4. E has its own idle control window (E0) just before the walk, beside A's ambient window, because
     A's hot and cold windows move the core between A0 and E.
  5. The B poll runs 180 s WALL (4.8 game hours), not 3 game minutes (1.9 s): a pure-water buffer
     empties at a quarter of the 2 h half-time (K.stomach.compositionScale 0.25) = 0.5 game h =
     18.75 s wall, so 180 s is ~9.6 half-times.

SCHEDULE:
  S0  markers; autodrink.probe (the inventory's containers, the flag's default); autodrink.set
      false; server THIRST 0; the record, the mirror and the counters; one probe of every chain.
  A0  ambient: reset, arm 60 s, paired polls; collect.
  A+  climate.set 35; 10 s settle; window as A0.
  A-  climate.set -10; 10 s settle; window as A0. Then climate.set off.
  B1  RCON additem Base.CanteenMilitaryFull, resolved on the client; server THIRST 0.2; reads;
      drink.action Base.CanteenMilitaryFull 1; poll 180 s every ~5 s (record, mirror, counters,
      server probe, stats pair).
  C   RCON additem Base.CanteenMilitaryFull (server-visible); autodrink.set true;
      C1 THIRST 0.09: probes at once, +3 s, +6 s, +10 s.
      C2 arm 20 s, wait armed, THIRST 0.3, probes for 15 s; collect.
      C3 arm 20 s, wait armed, THIRST 0.5, probes for 15 s; collect.
      30 s settle; the record and counters; autodrink.set false.
  D   server THIRST 0.4; arm 60 s; water.take admin; poll 60 s (stats pair, probe, record); collect;
      player.stop. "no source" -> recorded, the window still collected (a THIRST drift control).
  E0  player.stop; reset; arm 45 s idle; paired polls; collect.
  E   player.walk +-20 0 re-issued when the client reads not moving; arm 60 s; paired polls; collect.
  B2  fluid.fill admin Base.Sportsbottle Water 1.0 (client); drink.action Base.Sportsbottle 1;
      poll 45 s (record, counters, both sides' container litres).
  F   tick.rate 10 on the server, the result doc.

PREDICTIONS AND FALSIFIERS (written before the run):

  A   (#2933/#2934, #0594) The four getters answer numbers on the SERVER for a connected player
      (n_<field> = samples, no absent_<field> = "absent"); the client chain answers too (Plan 1).
      extAir follows the climate override: A+ extAir > A0 extAir > A- extAir; core moves less;
      fluidsMult >= 1 hot, 1 or near it cold. bodyFluids = 1 - thirst at every sample.
      Falsifiers: an absent_ key on the server (not live); extAir flat across the three windows with
      climate.set ok=true (the override does not reach the body). climate.set ok=false -> the
      climate half is "unmeasured: no override", A0 alone stands.
  B   (#2689, Plan 2 chain) B1: the drink wrapper sees the drink (sips +>=1, lastIntake.fullType
      Base.CanteenMilitaryFull, litres 0.9), stomach.buffer.water +900 at the drink and pool.water
      +900 (+-2 %) by the end of the poll, half of it within ~19-40 s; the mirror's pool_water
      follows. Falsifier: pool flat with the canteen emptied on the server.
      B2: the server never has the client-spawned bottle: no sip, no landing (the server chain
      reads nil); "landed" would falsify the client-spawn caution.
  C   (#2769, #2770, #2927-#2929) C1: no sip (THIRST <= 0.1 returns before the search). C2: the
      server canteen 0.9 -> 0.3 L and THIRST 0.3 -> ~0.0 within a tick or two of the write (the
      2 x thirst branch, a drop d = litres / 2). C3: 0.3 -> 0 L, THIRST 0.5 -> ~0.35 (the container
      branch). The wrapper does NOT see it: sips unchanged, lastIntake unchanged, buffer and pool
      water not raised. Falsifiers: no litres move at C2/C3 (autoDrink does not fire under the
      handler's call -> the bracket has nothing to read); sips moving (the wrapper sees it).
  D   (#2690, #2930-#2932) If a source is within 10 tiles: the server's THIRST falls (DrinkFluid ran
      on the server's character -> the action's transfer runs server-side), by up to 0.4; the pool
      and sips do not move (the wrapper does not see it). "no source" -> unmeasured, stated.
  E   (#0591/#2877) fluidsMult while walking vs E0 idle: the server's metabolic class rarely leaves
      Default (x141a), so the prediction is fluidsMult unchanged within the A0/E0 spread; a rise is
      the reading Task 8's sweat term needs.
  F   ticks per second on the server (a context number for the per-tick windows, no regression check).

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import json
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

PROFILE = "x15-water"
SESSION = ("Plan 4 water gate: thermoregulator getters server-side under the climate override (A), "
           "drink -> pool landing (B), the auto-drink bracket (C), world water (D), fluids "
           "multiplier under a walk (E), tick rate (F): one boot of x15-water at DayLength 1")
ARTIFACT = "water_gate.json"
USER = "admin"
ACCEPTANCE_RUN = None   # Task 3's commands were not run live; this run is their smoke test

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

TH = "getBodyDamage.getThermoregulator"
HOPS = (("fluidsMult", TH + ".getFluidsMultiplier"),
        ("core", TH + ".getCoreTemperature"),
        ("extAir", TH + ".getExternalAirTemperature"),
        ("bodyFluids", TH + ".getBodyFluids"),
        ("energyMult", TH + ".getEnergyMultiplier"))
MOVING_HOP = "isPlayerMoving"
TW = "TKX_ThirstWatch"
TW_FIELDS = ("thirst", "fluidsMult", "core", "extAir", "bodyFluids", "wetness")
STORE = "NutritionRevamp.players"
REC_KEYS = [f"{USER}.pool.water", f"{USER}.stomach.buffer.water", f"{USER}.stomach.bulk",
            f"{USER}.stomachFill", f"{USER}.kineticsAge", f"{USER}.lastIntake.fullType",
            f"{USER}.lastIntake.source", f"{USER}.lastIntake.litres", f"{USER}.lastIntake.missing"]
INTAKE = "NutritionRevamp.server.intake.stats"
COUNTERS = ("sips", "landed", "failures", "eats", "passthrough")
MIRROR_WATER = "NutritionRevamp.client.mirror.pool_water"
CANTEEN = "Base.CanteenMilitaryFull"
SPORTS = "Base.Sportsbottle"
A_WINDOW_S = 60
CLIMATE_SETTLE_S = 10
HOT_C, COLD_C = 35, -10
B_POLL_S, B_POLL_EVERY = 180, 5.0
B2_POLL_S = 45
C_WINDOW_S = 20
C_PROBE_S = 15
C_SETTLE_S = 30
D_WINDOW_S = 60
E0_WINDOW_S = 45
E_WINDOW_S = 60
WALK_DX = 20
TICK_S = 10
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
DONE_WAIT_S = 15.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
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


def chain(tag, side, hop):
    args = hop if side is client else f"{USER} {hop}"
    r = step(tag, side, "witness.chain", args)
    a = ack(r)
    v = a.get("value")
    return {"tag": tag, "side": "client" if side is client else "server", "wall": r["wall_before"],
            "ok": a.get("ok"), "value": to_num(v), "raw": v, "failedAt": a.get("failedAt"),
            "error": a.get("error"), "reason": a.get("reason"),
            "reply": r["ack"] if not isinstance(r["ack"], dict) else None}


def stats_pair(tag):
    rc = step(f"{tag}_stats_client", client, "stats.get", "")
    rs = step(f"{tag}_stats_server", server, "stats.get", USER)
    keys = ("thirst", "hunger", "moving", "running", "endurance", "asleep", "worldAge", "mult")
    c_, s_ = ack(rc), ack(rs)
    p = {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "client": {k: c_.get(k) for k in keys}, "server": {k: s_.get(k) for k in keys}}
    out["stats_pairs"].append(p)
    return p


def md_read(tag, scope, keys, side=None):
    """witness.moddata global:<scope> in chunks of <= 30 keys; values merged (strings)."""
    side = side or server
    vals, missing, census = {}, [], None
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        r = step(f"{tag}_{j}", side, "witness.moddata", f"global:{scope} " + " ".join(ch))
        a = ack(r)
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
        if census is None and isinstance(a.get("keys"), list):
            census = a["keys"]
    return {"values": vals, "missing": missing, "census": census or [], "wall": wall()}


def record(tag):
    """The mod's record (server store), the drink wrapper's counters, the client mirror."""
    rd = md_read(f"{tag}_rec", STORE, REC_KEYS)
    v = rd["values"]
    rec = {"tag": tag, "wall": rd["wall"], "missing": rd["missing"]}
    for k in REC_KEYS:
        short = k[len(USER) + 1:]
        raw = v.get(k)
        n = to_num(raw)
        rec[short] = n if n is not None else raw
    cnt = {}
    for c in COUNTERS:
        a = ack(step(f"{tag}_cnt_{c}", server, "lua.global", f"{INTAKE}.{c}"))
        cnt[c] = to_num(a.get("value")) if a.get("resolved") else None
    rec["counters"] = cnt
    le = ack(step(f"{tag}_lastError", server, "lua.global", "NutritionRevamp.server.intake.lastError"))
    rec["lastError"] = le.get("value") if le.get("resolved") else None
    mw = ack(step(f"{tag}_mirror", client, "lua.global", MIRROR_WATER))
    rec["mirror_pool_water"] = to_num(mw.get("value")) if mw.get("resolved") else None
    out["records"].append(rec)
    return rec


def probe(tag):
    a = ack(step(tag, server, "autodrink.probe", USER))
    return {"tag": tag, "wall": wall(), "thirst": to_num(a.get("thirst")), "autoDrink": a.get("autoDrink"),
            "item": a.get("item"), "litres": to_num(a.get("litres")), "fluid": a.get("fluid"),
            "containers": a.get("containers"), "ok": a.get("ok"), "reason": a.get("reason")}


def set_thirst(tag, v):
    return ack(step(tag, server, "stats.setany", f"{USER} THIRST {v}"))


def tw_status(tag):
    r = step(tag, server, "witness.moddata", f"global:{TW} status samples windowMs arm")
    return (ack(r).get("values") or {})


def tw_reset(tag):
    done = []
    for f in TW_FIELDS:
        step(f"{tag}_rn_{f}", server, "globalmoddata.set", f"{TW} n_{f} 0")
        step(f"{tag}_ra_{f}", server, "globalmoddata.set", f"{TW} absent_{f} reset")
        done.append(f)
    return {"reset": done, "wall": wall()}


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
    sc = md_read(f"{tag}_scal", TW, keys)
    raws = md_read(f"{tag}_raw", TW, [f"raw_{i}" for i in range(1, 51)])
    raw = []
    for i in range(1, 51):
        v = raws["values"].get(f"raw_{i}")
        if v is not None:
            raw.append(parse_raw(v))
    samples = to_num(sc["values"].get("samples"))
    if samples is not None:
        raw = raw[:int(samples)]
    fields = {}
    for f in TW_FIELDS:
        g = sc["values"]
        fields[f] = {"first": to_num(g.get(f"first_{f}")), "last": to_num(g.get(f"last_{f}")),
                     "min": to_num(g.get(f"min_{f}")), "max": to_num(g.get(f"max_{f}")),
                     "n": to_num(g.get(f"n_{f}")), "absent": g.get(f"absent_{f}")}
    return {"done": done, "samples": samples, "windowMs": to_num(sc["values"].get("windowMs")),
            "status": sc["values"].get("status"), "fields": fields, "raw": raw}


def poll_thermo(i, tag, keep_moving=None):
    s = {"i": i, "wall": wall()}
    for name, hop in HOPS:
        s[f"client_{name}"] = chain(f"{tag}{i}_c{name}", client, hop)
    for name, hop in HOPS:
        s[f"server_{name}"] = chain(f"{tag}{i}_s{name}", server, hop)
    if keep_moving is not None:
        mv = chain(f"{tag}{i}_cmv", client, MOVING_HOP)
        s["client_moving"] = mv["raw"]
        if str(mv["raw"]).lower() != "true":
            s["reissue"] = keep_moving()
    return s


def thermo_window(P, key, seconds, start_fn=None, keep_moving=None):
    A = P[key] = {}
    A["pre"] = tw_reset(key)
    A["stats_start"] = stats_pair(f"{key}_start")
    A["start"] = start_fn() if start_fn else None
    A["start_wall"] = wall()
    A["arm"] = tw_arm(key, seconds)
    A["polls"] = []
    i = 0
    end = A["arm"]["arm_wall"] + seconds
    while wall() < end - 1.0:
        A["polls"].append(poll_thermo(i, key, keep_moving))
        i += 1
    A["stats_end"] = stats_pair(f"{key}_end")
    A["watch"] = tw_collect(key, A["arm"])
    persist()
    return A


def walker(key):
    state = {"dir": 1, "n": 0}
    issued = []

    def go():
        dx = WALK_DX * state["dir"]
        state["dir"] = -state["dir"]
        state["n"] += 1
        r = step(f"{key}_walk{state['n']}", client, "player.walk", f"{dx} 0")
        a = ack(r)
        rec = {"n": state["n"], "dx": dx, "wall": r["wall_before"], "queued": a.get("queued"),
               "error": a.get("error"), "clientMoving": a.get("clientMoving")}
        issued.append(rec)
        return rec
    return go, issued


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
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": fields.get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    out["spawns"].append(row)
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    persist()
    return row


def litres_chain(tag, side, full_type):
    return chain(tag, side, f"getInventory.getFirstTypeRecurse({full_type}).getFluidContainer.getAmount")


def poll_drink(P, key, seconds, every, full_type):
    polls = []
    end = wall() + seconds
    i = 0
    while wall() < end:
        t_start = wall()
        s = {"i": i, "wall": t_start}
        s["record"] = record(f"{key}_p{i}")
        s["probe"] = probe(f"{key}_p{i}_probe")
        s["client_litres"] = litres_chain(f"{key}_p{i}_cl", client, full_type)
        s["server_litres"] = litres_chain(f"{key}_p{i}_sl", server, full_type)
        if i % 4 == 0:
            s["stats"] = stats_pair(f"{key}_p{i}")
        polls.append(s)
        persist()
        i += 1
        rest = every - (wall() - t_start)
        if rest > 0:
            time.sleep(rest)
    return polls


def body():
    P = out["phases"]
    # ---------------- S0 setup ----------------
    S0 = P["S0"] = {}
    S0["tw_installed"] = ack(step("tw_installed", server, "lua.global", "TKX_ThirstWatch_Installed"))
    S0["drink_wrapped"] = ack(step("drink_wrapped", server, "lua.global", "NR_IntakeDrink_Installed"))
    S0["probe0"] = probe("s0_probe")
    S0["autodrink_off"] = ack(step("s0_ad_off", server, "autodrink.set", f"{USER} false"))
    S0["thirst0"] = set_thirst("s0_thirst0", 0)
    S0["record"] = record("s0")
    S0["stats"] = stats_pair("s0")
    S0["chains"] = {name: {"client": chain(f"s0_c_{name}", client, hop),
                           "server": chain(f"s0_s_{name}", server, hop)} for name, hop in HOPS}
    S0["tw_status0"] = tw_status("s0_tw")
    persist()

    # ---------------- A thermoregulator ----------------
    thermo_window(P, "A0", A_WINDOW_S)
    hot = ack(step("A_hot_set", server, "climate.set", str(HOT_C)))
    out["climate"].append({"set": HOT_C, "wall": wall(), "ack": hot})
    time.sleep(CLIMATE_SETTLE_S)
    thermo_window(P, "Ahot", A_WINDOW_S)
    cold = ack(step("A_cold_set", server, "climate.set", str(COLD_C)))
    out["climate"].append({"set": COLD_C, "wall": wall(), "ack": cold})
    time.sleep(CLIMATE_SETTLE_S)
    thermo_window(P, "Acold", A_WINDOW_S)
    off = ack(step("A_off", server, "climate.set", "off"))
    out["climate"].append({"set": "off", "wall": wall(), "ack": off})
    persist()

    # ---------------- B1 the drink -> pool landing ----------------
    B = P["B1"] = {}
    B["spawn"] = spawn(CANTEEN, "B1")
    B["thirst"] = set_thirst("B1_thirst", 0.2)
    B["before"] = record("B1_before")
    B["probe_before"] = probe("B1_probe_before")
    B["client_litres_before"] = litres_chain("B1_cl_before", client, CANTEEN)
    B["server_litres_before"] = litres_chain("B1_sl_before", server, CANTEEN)
    B["drink_wall"] = wall()
    B["drink"] = ack(step("B1_drink", client, "drink.action", f"{CANTEEN} 1"))
    B["polls"] = poll_drink(P, "B1", B_POLL_S, B_POLL_EVERY, CANTEEN)
    B["after"] = record("B1_after")
    persist()

    # ---------------- C the auto-drink bracket ----------------
    C = P["C"] = {}
    C["spawn"] = spawn(CANTEEN, "C")
    C["before"] = record("C_before")
    C["probe_spawned"] = probe("C_probe_spawned")
    C["autodrink_on"] = ack(step("C_ad_on", server, "autodrink.set", f"{USER} true"))
    # C1 under the gate
    C1 = C["C1"] = {"set": set_thirst("C1_set", 0.09), "set_wall": wall(), "probes": []}
    for k, d in enumerate((0, 3, 3, 4)):
        if d:
            time.sleep(d)
        C1["probes"].append(probe(f"C1_probe{k}"))
    persist()
    # C2 and C3: arm, wait armed, write THIRST, probe for C_PROBE_S
    for key, val in (("C2", 0.3), ("C3", 0.5)):
        X = C[key] = {}
        X["pre"] = tw_reset(key)
        X["arm"] = tw_arm(key, C_WINDOW_S)
        X["probe_before"] = probe(f"{key}_probe_before")
        X["set"] = set_thirst(f"{key}_set", val)
        X["set_wall"] = wall()
        X["probes"] = []
        end = wall() + C_PROBE_S
        while wall() < end:
            X["probes"].append(probe(f"{key}_probe{len(X['probes'])}"))
            time.sleep(1.0)
        X["stats"] = stats_pair(f"{key}_after")
        X["watch"] = tw_collect(key, X["arm"])
        persist()
    time.sleep(C_SETTLE_S)
    C["after"] = record("C_after")
    C["probe_after"] = probe("C_probe_after")
    C["autodrink_off"] = ack(step("C_ad_off", server, "autodrink.set", f"{USER} false"))
    persist()

    # ---------------- D world water ----------------
    D = P["D"] = {}
    D["thirst"] = set_thirst("D_thirst", 0.4)
    D["before"] = record("D_before")
    D["pre"] = tw_reset("D")
    D["arm"] = tw_arm("D", D_WINDOW_S)
    D["take"] = ack(step("D_take", client, "water.take", USER))
    D["take_wall"] = wall()
    D["polls"] = []
    end = D["arm"]["arm_wall"] + D_WINDOW_S
    i = 0
    while wall() < end - 1.0:
        D["polls"].append({"i": i, "wall": wall(), "stats": stats_pair(f"D_p{i}"),
                           "probe": probe(f"D_p{i}_probe")})
        if i % 3 == 0:
            D["polls"][-1]["record"] = record(f"D_p{i}")
        i += 1
        time.sleep(2.0)
    D["watch"] = tw_collect("D", D["arm"])
    D["after"] = record("D_after")
    D["stop"] = ack(step("D_stop", client, "player.stop", ""))
    persist()

    # ---------------- E fluids multiplier under a walk ----------------
    out["phases"]["E0_stop"] = ack(step("E0_stop", client, "player.stop", ""))
    thermo_window(P, "E0", E0_WINDOW_S)
    go, issued = walker("E")
    thermo_window(P, "E", E_WINDOW_S, start_fn=go, keep_moving=go)
    P["E"]["walks"] = issued
    P["E"]["stop_end"] = ack(step("E_stop_end", client, "player.stop", ""))
    persist()

    # ---------------- B2 the client-spawned container ----------------
    B2 = P["B2"] = {}
    B2["before"] = record("B2_before")
    B2["fill"] = ack(step("B2_fill", client, "fluid.fill", f"{USER} {SPORTS} Water 1.0"))
    B2["client_litres_before"] = litres_chain("B2_cl_before", client, SPORTS)
    B2["server_litres_before"] = litres_chain("B2_sl_before", server, SPORTS)
    B2["drink"] = ack(step("B2_drink", client, "drink.action", f"{SPORTS} 1"))
    B2["polls"] = poll_drink(P, "B2", B2_POLL_S, B_POLL_EVERY, SPORTS)
    B2["after"] = record("B2_after")
    persist()

    # ---------------- F tick rate ----------------
    F = P["F"] = {}
    t_epoch = time.time()
    F["arm"] = ack(step("F_tick", server, "tick.rate", str(TICK_S)))
    try:
        F["result"] = server.bus.wait_result("tick-rate", timeout=TICK_S + 20, after=t_epoch)
    except (RuntimeError, TimeoutError, OSError) as e:
        F["result"] = {"error": f"{type(e).__name__}: {e}"}
    persist()


# ---------------- grading ----------------

def series(polls, key):
    return [p[key]["value"] for p in polls if isinstance(p.get(key), dict) and p[key]["value"] is not None]


def win_summary(W):
    w = (W or {}).get("watch") or {}
    polls = (W or {}).get("polls") or []
    s = {"samples": w.get("samples"), "windowMs": w.get("windowMs"), "status": w.get("status"),
         "fields": w.get("fields")}
    for name, _ in HOPS:
        for side in ("client", "server"):
            v = series(polls, f"{side}_{name}")
            s[f"{side}_{name}"] = {"n": len(v), "min": min(v) if v else None, "max": max(v) if v else None,
                                   "first": v[0] if v else None, "last": v[-1] if v else None}
    return s


def grade_all():
    P = out["phases"]
    S = out["summaries"]
    for k in ("A0", "Ahot", "Acold", "E0", "E"):
        if k in P:
            S[k] = win_summary(P[k])
    # A
    srv_absent = {}
    for k in ("A0", "Ahot", "Acold"):
        f = ((S.get(k) or {}).get("fields") or {})
        srv_absent[k] = {fld: (f.get(fld) or {}).get("absent") for fld in TW_FIELDS}
    live = all(((S.get(k) or {}).get("fields") or {}).get(fld, {}).get("n") for k in ("A0",)
               for fld in ("fluidsMult", "core", "extAir", "bodyFluids"))
    ext = {k: ((S.get(k) or {}).get("fields") or {}).get("extAir") for k in ("A0", "Ahot", "Acold")}
    climate_ok = [c["ack"].get("ok") for c in out["climate"]]
    obs = {"absent": srv_absent, "extAir": ext, "climate_ok": climate_ok,
           "core": {k: ((S.get(k) or {}).get("fields") or {}).get("core") for k in ("A0", "Ahot", "Acold")},
           "fluidsMult": {k: ((S.get(k) or {}).get("fields") or {}).get("fluidsMult") for k in ("A0", "Ahot", "Acold")},
           "energyMult_server": {k: (S.get(k) or {}).get("server_energyMult") for k in ("A0", "Ahot", "Acold")}}
    try:
        moved = (ext["Ahot"]["last"] > ext["A0"]["last"] > ext["Acold"]["last"])
    except (TypeError, KeyError):
        moved = None
    obs["extAir_ordered"] = moved
    v = "unmeasured" if not live else ("as_predicted" if moved else ("falsified" if all(climate_ok) else "unmeasured"))
    grade("A", "getters numeric on the server; extAir hot > ambient > cold", obs, v,
          "an absent_ key on the server; extAir flat with climate.set ok")
    # B1
    B = P.get("B1") or {}
    b0 = (B.get("before") or {})
    b1 = (B.get("after") or {})
    d_pool = (to_num(b1.get("pool.water")) or 0) - (to_num(b0.get("pool.water")) or 0) if b0 and b1 else None
    d_sips = None
    try:
        d_sips = b1["counters"]["sips"] - b0["counters"]["sips"]
    except (KeyError, TypeError):
        pass
    litres0 = (B.get("probe_before") or {}).get("litres")
    obs = {"pool_water_delta": d_pool, "sips_delta": d_sips, "litres_before": litres0,
           "lastIntake_after": {k: b1.get(k) for k in ("lastIntake.fullType", "lastIntake.litres", "lastIntake.missing")},
           "mirror_after": b1.get("mirror_pool_water")}
    pred = (litres0 or 0) * 1000
    v = "unmeasured" if not d_sips else ("as_predicted" if d_pool is not None and abs(d_pool - pred) <= 0.02 * pred
                                          else "falsified")
    grade("B1", f"pool.water +{pred:.0f} (+-2%) and sips >= 1", obs, v, "pool flat with sips > 0")
    # C
    C = P.get("C") or {}
    obs = {}
    for key in ("C1", "C2", "C3"):
        X = C.get(key) or {}
        pr = X.get("probes") or []
        obs[key] = {"set": (X.get("set") or {}).get("after"),
                    "before": X.get("probe_before") if key != "C1" else None,
                    "probes": [(p["thirst"], p["litres"], p["item"]) for p in pr],
                    "watch_thirst": ((X.get("watch") or {}).get("fields") or {}).get("thirst")}
    try:
        obs["sips_delta"] = C["after"]["counters"]["sips"] - C["before"]["counters"]["sips"]
        obs["pool_delta"] = (to_num(C["after"].get("pool.water")) or 0) - (to_num(C["before"].get("pool.water")) or 0)
    except (KeyError, TypeError):
        pass
    grade("C", "C1 no sip; C2 0.6 L at THIRST 0.3; C3 0.3 L at 0.5; wrapper blind", obs, "see_raw",
          "no litres move at C2/C3; sips moving")
    # D
    D = P.get("D") or {}
    take = D.get("take") or {}
    obs = {"take": take, "watch_thirst": ((D.get("watch") or {}).get("fields") or {}).get("thirst"),
           "probe_thirst": [p["probe"]["thirst"] for p in D.get("polls") or []]}
    v = "unmeasured" if take.get("reason") == "no source" or not take.get("queued") else "see_raw"
    grade("D", "server THIRST falls; pool and sips flat", obs, v, "server THIRST flat with the action queued")
    # E
    obs = {"E0": (S.get("E0") or {}).get("server_fluidsMult"), "E": (S.get("E") or {}).get("server_fluidsMult"),
           "E0_watch": ((S.get("E0") or {}).get("fields") or {}).get("fluidsMult"),
           "E_watch": ((S.get("E") or {}).get("fields") or {}).get("fluidsMult"),
           "client_moving": [p.get("client_moving") for p in (P.get("E") or {}).get("polls") or []]}
    grade("E", "fluidsMult unchanged walking vs idle", obs, "see_raw", "a rise above the idle spread")
    # B2
    B2 = P.get("B2") or {}
    obs = {"fill": B2.get("fill"), "drink": B2.get("drink"),
           "server_litres_before": B2.get("server_litres_before")}
    try:
        obs["sips_delta"] = B2["after"]["counters"]["sips"] - B2["before"]["counters"]["sips"]
        obs["pool_delta"] = (to_num(B2["after"].get("pool.water")) or 0) - (to_num(B2["before"].get("pool.water")) or 0)
    except (KeyError, TypeError):
        pass
    grade("B2", "no sip, no landing (server has no copy)", obs, "see_raw", "a landing")
    F = P.get("F") or {}
    grade("F", "server ticks per second", F.get("result"), "see_raw", "none")


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x151w-dry-run", None) if DRY_RUN else new_run_dir("x151w")
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
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"A_WINDOW_S": A_WINDOW_S, "CLIMATE_SETTLE_S": CLIMATE_SETTLE_S, "HOT_C": HOT_C,
                  "COLD_C": COLD_C, "B_POLL_S": B_POLL_S, "B_POLL_EVERY": B_POLL_EVERY, "B2_POLL_S": B2_POLL_S,
                  "C_WINDOW_S": C_WINDOW_S, "C_PROBE_S": C_PROBE_S, "C_SETTLE_S": C_SETTLE_S,
                  "D_WINDOW_S": D_WINDOW_S, "E0_WINDOW_S": E0_WINDOW_S, "E_WINDOW_S": E_WINDOW_S,
                  "WALK_DX": WALK_DX, "TICK_S": TICK_S, "CANTEEN": CANTEEN, "SPORTS": SPORTS},
    "deviations": [
        "First live use of stats.setany, autodrink.set, autodrink.probe, climate.set, fluid.fill, water.take "
        "and TKX_ThirstWatch (Task 3, no acceptance run since): each command's reply is its smoke test.",
        "B1 drinks Base.CanteenMilitaryFull (Water only, 0.9 L) spawned by RCON additem, not Base.WaterBottle "
        "by inventory.add: WaterBottle picks Water or CarbonatedWater at random and the seed has no "
        "CarbonatedWater row; inventory.add is server-only and drink.action is a client command.",
        "fluid.fill has no inventory search; B2 is a client fluid.fill of Base.Sportsbottle, run last before F.",
        "C runs THIRST 0.09, 0.3 and 0.5 to separate the gate and both branches of min(amount, 2 x thirst).",
        "E has its own idle control E0 beside A0.",
        "The B1 poll is 180 s wall (4.8 game hours at DayLength 1), not 3 game minutes.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["two CanteenMilitaryFull (server-visible)", "a client-only Sportsbottle",
                                        "THIRST written several times", "the climate override cleared at A's end"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "summaries": {}, "stats_pairs": [],
    "records": [], "spawns": [], "climate": [],
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
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
                  "body_error": out.get("body_error")}, indent=1)[:7000])
