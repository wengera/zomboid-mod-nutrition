"""x151-sleep-gate -- Plan 4 Task 5, the sleep and alcohol gate: TWO boots, serial, one driver.
Boot 1 is profile `x15-sleep` (SleepAllowed = false, SleepNeeded = false); boot 2 is profile
`x15-sleep-on` (both true). Both carry PZTestKit + NutritionRevamp (Mode 1, LegacyMirror) +
TKX_SleepWatch + TKX_BoozeWatch, `Nutrition = false`, DayLength 1 (a game hour is 37.5 s wall,
a game minute 0.625 s). Boot 1 runs to completion and is torn down; the driver then polls
`pzt doctor` until the game Java is gone before boot 2 starts (one live session at a time). The
run id prefix is `x151s`; ONE artifact `sleep_gate.json` carries `boot1` and `boot2` blocks.
Copied from `x151_water_gate.py` (provenance, wall-bracketed steps, the RCON spawn resolved on the
client, `to_num`, the persist/step shape, the log greps).

THE MOD ON THESE BOOTS is HEAD's tree (Plan 3's handler, the 31-key vector, Task 7's records and
Task 8's NR_Kernel_Fluids, which the handler does not yet call). The handler (NR_Server_Fast.lua)
reads FATIGUE back on every update, steps the awake/asleep fatigue model (NR_Kernel_Fast.lua) and
writes it; vanilla's fatigue reset runs BEFORE the hook on a server unless SleepAllowed and
SleepNeeded are both true (#2723, #2793). INTOXICATION is not touched by the mod: the vanilla
decay (`BodyDamage.Update`, before the hook, server only; #2918) and the drink's
JustDrankBoozeFluid add (#2923, #2925) are the only writers.

THE SERVER VIEWS. `TKX_SleepWatch` (fat, fatUpd, dUpd, asleep and a `resets` count of ticks whose
fatigue fell by more than 0.1 from the tick before) and `TKX_BoozeWatch` (intox), each armed per
window with `globalmoddata.set TKX_<X>Watch arm <s>`, sample the first online player every server
tick and write flat keys at the window's end (first_/last_/min_/max_/n_<field>, hist_*, raw_1..50
for the first 50 ticks, samples, windowMs, status; SleepWatch also `resets`). Before every window
the driver resets n_<field> to 0, absent_<field> to "reset" and (SleepWatch) resets to -1, so a
stale key cannot pass for this window's. Beside every window: server `stats.all admin` at ~1 Hz
(the 24 CharacterStats with worldAge, mult and the server wall).

TWO HARNESS ADDITIONS (commit 839dfdb, before this run; this run is their smoke test):
  `fluid.fill` (server twin) fills the first server-inventory item of a type -- the RCON copy both
  sides hold -- with a named fluid, server-side only; the coffee is then drunk with the server
  `drink` command (one DrinkFluid call, the shipped action minus the timed action). The client
  `fluid.fill` spawns a container the server never has (x151w B2 raised in the server's
  ISDrinkFluidAction.new), so the amendments' client fill + drink.action could not reach the server.
  `pill.take.held` queues ISTakePillAction on the first pill of a type already in the client's
  inventory (the RCON copy) instead of spawning one client-only, as `pill.take` does.

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. Beer is `Base.BeerCan` spawned by RCON `additem` (both sides hold it): its script fills it
     with Beer 1.0 x 0.3 L (normal.txt:6094-6119), so no `fluid.fill` is needed and the 0.5 L of the
     amendments does not fit (capacity 0.3). drink.action drinks it; if the server's can still
     holds its litres 25 s after the queue (a sealed can refused, or the client copy unresolved),
     the server `drink admin Base.BeerCan 1` fallback runs and the route is recorded.
  2. Coffee goes into `Base.Mugl` (capacity 0.2 L, normal.txt:3872-3891), so 0.2 L, not 0.25 L, by
     the server `fluid.fill` twin, drunk by the server `drink` command (above).
  3. The pill is `Base.PillsVitamins` (the caffeine-pill icon and model, fatigueChange -4.0,
     drainable.txt:1474), spawned by RCON and taken by `pill.take.held` (above). D also runs on
     boot 2 (D'), where a fatigue write is not reset, so the pill's own fatigue step is visible.
  4. A writes FATIGUE 0.5 three times in one 30 s window (at ~0.5, ~10 and ~20 s after the arm),
     so the probe's reset count has three chances and a count of 3 is the reading.
  5. After B2 the driver writes INTOXICATION 0, so C and D run below the pill's INTOXICATION > 10
     halving branch (jar BodyDamage.JustTookPill @255-@296 L564-L567).
  6. Boot 2 runs A', C', D' and then E LAST (a held sleep can leave the player asleep).

SCHEDULE:
  boot 1 (x15-sleep):
    S0  markers; the server ini values as written (pre-start) and as read after ready; stats.all;
        the intake counters and the record's caffeine/ethanol/water keys.
    A   reset+arm SleepWatch 30 s; FATIGUE 0.5 x3 (stats.setany on the SERVER) each followed at once
        by a server stats.get; stats.all ~1 Hz; collect.
    B   RCON additem Base.BeerCan, resolved on the client; stats.all (HUNGER for the 1.1/1.25 ladder);
        reset+arm BoozeWatch 120 s; drink.action Base.BeerCan 1; poll ~1 Hz: stats.all and the server
        can's litres (fallback at 25 s, above); collect; the counters and record.
    B2  reset+arm BoozeWatch 60 s; INTOXICATION 40 (server); stats.all ~1 Hz; collect; then
        INTOXICATION 0.
    C   RCON additem Base.Mugl; server fluid.fill admin Base.Mugl Coffee 0.2; reset+arm SleepWatch
        20 s; server drink admin Base.Mugl 1 (its before/after carry FATIGUE); stats.all ~1 Hz; collect.
    D   RCON additem Base.PillsVitamins, resolved on the client; counters, record, the server pill's
        uses; reset+arm SleepWatch 20 s; pill.take.held admin Base.PillsVitamins; poll ~1 Hz
        stats.all and the server pill's uses for 18 s; collect; counters and record after.
  boot 2 (x15-sleep-on): S0 as boot 1;
    A'  reset+arm SleepWatch 60 s; FATIGUE 0.5 once; stats.all ~1 Hz; collect.
    C'  as C.   D'  as D.
    E   reset+arm SleepWatch 120 s; player.sleep.hold admin 120; server stats.get every ~2 s
        (asleep, fatigue); collect; player.sleep.hold admin 0.

PREDICTIONS AND FALSIFIERS (written before the run):
  A   (#2723, #2793) boot 1: stats.setany replies after = 0.5 (the write lands); FATIGUE is ~0 (the
      reset plus one update's accrual) at the next server read and the probe's resets count is 3
      (one per write) or the probe never sees 0.5 (max_fat < 0.5: the reset ran inside the same
      tick, before OnTick). Falsifier: FATIGUE still >= 0.4 a second after a write.
  A'  boot 2: the write holds (FATIGUE >= 0.5 at every later read, rising by the awake accrual);
      resets 0. Falsifier: a reset (FATIGUE back near 0) -> the ini override did not reach the
      server, or the reset has another gate.
  B   (#2918, #2922, #2923, #2925, #2926) the can's 0.3 L x alcohol 0.05 x 400 = 6 INTOXICATION
      at HUNGER <= 0.6 (x1.25 at 0.6-0.8, x1.1 above 0.8), added per sip across the drink, the
      decay running beside it; after the last sip INTOXICATION falls 0.0042 x mult per tick.
      Falsifier: no rise with the can's litres gone on the server.
  B2  INTOXICATION 40 falls by 0.0042 x getMultiplier per server tick; at DayLength 1 (a game hour
      37.5 s) that is 0.504 x 15 = 7.56 per game hour, 0.2016 per wall second. Falsifier: a slope
      off by more than 10 % from 0.0042 x the mult the stats.all reads report.
  C   (#2723; Coffee fatigueChange -10.0 per litre, fluids_Beverages.txt:391; the fluid getters
      divide by 100, #0629) the drink writes FATIGUE -0.02 x the share drunk; on boot 1 the value
      the drink reply reads after is the write, and the next update erases it (FATIGUE back at the
      reset value). C': the step survives (FATIGUE 0.02 lower at the next reads, then accruing).
  D   (ISTakePillAction.complete -> BodyDamage.JustTookPill, lua/shared/TimedActions/
      ISTakePillAction.lua:64-68) the server pill loses one use (5 -> 4 uses, 1.0 -> 0.8); NO mod
      counter moves (eats, sips, landed, cancels, passthrough) and the record's caffeine pool and
      lastIntake do not change: the pill path is not a seat the mod wraps. Boot 1: any FATIGUE
      step is erased; D': FATIGUE falls by the pill's fatigueChange (-0.04 if the script value is
      divided by 100, -4 clamped to 0 if not). Falsifier: a counter moves.
  E   (#2840, #2899) the held flag reads true at most server reads; with sleep allowed FATIGUE
      falls while asleep (the handler's asleep branch). If the hold never reads asleep, the share
      is recorded and the arm is unmeasured.
  ini A boot-2 ini that does not read SleepAllowed=true and SleepNeeded=true makes every boot-2
      arm "unmeasured: the override did not reach the ini".

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

PROFILES = ("x15-sleep", "x15-sleep-on")
SESSION = ("Plan 4 sleep and alcohol gate: the fatigue reset (A), beer intoxication rise and decay "
           "(B, B2), the coffee fatigue write (C), the caffeine pill seat (D) on x15-sleep; the write "
           "held (A'), coffee (C'), pill (D') and a held sleep (E) on x15-sleep-on; two serial boots "
           "at DayLength 1")
ARTIFACT = "sleep_gate.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

SW, BW = "TKX_SleepWatch", "TKX_BoozeWatch"
SW_FIELDS = ("fat", "fatUpd", "dUpd", "asleep")
BW_FIELDS = ("intox",)
STORE = "NutritionRevamp.players"
REC_KEYS = [f"{USER}.pool.caffeine", f"{USER}.pool.ethanol", f"{USER}.pool.water",
            f"{USER}.stomach.buffer.caffeine", f"{USER}.stomach.buffer.ethanol",
            f"{USER}.stomach.buffer.water", f"{USER}.lastIntake.fullType", f"{USER}.lastIntake.source",
            f"{USER}.lastIntake.litres", f"{USER}.lastIntake.missing", f"{USER}.kineticsAge"]
INTAKE = "NutritionRevamp.server.intake.stats"
COUNTERS = ("eats", "cancels", "sips", "landed", "failures", "passthrough", "unreadableAfter")
BEER, MUG, PILL = "Base.BeerCan", "Base.Mugl", "Base.PillsVitamins"
COFFEE_L = 0.2
A_WINDOW_S, A_WRITES = 30, (0.5, 10.0, 20.0)
B_WINDOW_S, B_FALLBACK_S = 120, 25.0
B2_WINDOW_S, B2_INTOX = 60, 40
C_WINDOW_S, D_WINDOW_S, D_POLL_S = 20, 20, 18.0
A2_WINDOW_S = 60
E_WINDOW_S, E_POLL_EVERY = 120, 2.0
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
DONE_WAIT_S = 15.0
DOCTOR_WAIT_S = 120

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
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
    row = {"step": f"{cur['tag']}_{name}", "cmd": cmd, "args": args,
           "side": "server" if side is cur["server"] else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=row["step"], cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def S():
    return cur["server"]


def C():
    return cur["client"]


def stats_all(tag):
    r = step(tag, S(), "stats.all", USER)
    a = ack(r)
    st = a.get("stats") if isinstance(a.get("stats"), dict) else {}
    row = {"tag": tag, "wall": r["wall_before"], "srv_wall": a.get("wall"), "worldAge": a.get("worldAge"),
           "mult": a.get("mult"), "fatigue": st.get("Fatigue"), "intox": st.get("Intoxication"),
           "hunger": st.get("Hunger"), "thirst": st.get("Thirst"), "stress": st.get("Stress"),
           "endurance": st.get("Endurance")}
    if not st:
        row["reply"] = r["ack"]
    return row


def stats_get(tag):
    a = ack(step(tag, S(), "stats.get", USER))
    return {"tag": tag, "wall": wall(), "fatigue": a.get("fatigue"), "asleep": a.get("asleep"),
            "endurance": a.get("endurance"), "worldAge": a.get("worldAge"), "srv_wall": a.get("wall")}


def setany(tag, stat, v):
    a = ack(step(tag, S(), "stats.setany", f"{USER} {stat} {v}"))
    return {"wall": wall(), "ok": a.get("ok"), "requested": a.get("requested"), "before": a.get("before"),
            "after": a.get("after"), "reason": a.get("reason")}


def md_read(tag, scope, keys):
    vals, missing = {}, []
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        a = ack(step(f"{tag}_{j}", S(), "witness.moddata", f"global:{scope} " + " ".join(ch)))
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
    return {"values": vals, "missing": missing, "wall": wall()}


def record(tag):
    rd = md_read(f"{tag}_rec", STORE, REC_KEYS)
    rec = {"tag": tag, "wall": rd["wall"], "missing": rd["missing"]}
    for k in REC_KEYS:
        raw = rd["values"].get(k)
        n = to_num(raw)
        rec[k[len(USER) + 1:]] = n if n is not None else raw
    cnt = {}
    for c in COUNTERS:
        a = ack(step(f"{tag}_cnt_{c}", S(), "lua.global", f"{INTAKE}.{c}"))
        cnt[c] = to_num(a.get("value")) if a.get("resolved") else None
    rec["counters"] = cnt
    le = ack(step(f"{tag}_lastError", S(), "lua.global", "NutritionRevamp.server.intake.lastError"))
    rec["lastError"] = le.get("value") if le.get("resolved") else None
    return rec


def chain_srv(tag, hop):
    a = ack(step(tag, S(), "witness.chain", f"{USER} {hop}"))
    return {"tag": tag, "wall": wall(), "ok": a.get("ok"), "value": to_num(a.get("value")),
            "raw": a.get("value"), "failedAt": a.get("failedAt"), "error": a.get("error")}


def litres_srv(tag, full_type):
    return chain_srv(tag, f"getInventory.getFirstTypeRecurse({full_type}).getFluidContainer.getAmount")


def uses_srv(tag, full_type):
    return chain_srv(tag, f"getInventory.getFirstTypeRecurse({full_type}).getCurrentUsesFloat")


def w_status(tag, table):
    return ack(step(tag, S(), "witness.moddata", f"global:{table} status samples windowMs arm resets")).get("values") or {}


def w_reset(tag, table, fields):
    for f in fields:
        step(f"{tag}_rn_{f}", S(), "globalmoddata.set", f"{table} n_{f} 0")
        step(f"{tag}_ra_{f}", S(), "globalmoddata.set", f"{table} absent_{f} reset")
    if table == SW:
        step(f"{tag}_rr", S(), "globalmoddata.set", f"{table} resets -1")
    return {"reset": list(fields), "wall": wall()}


def w_arm(tag, table, seconds):
    r = step(f"{tag}_arm", S(), "globalmoddata.set", f"{table} arm {seconds}")
    arm_wall = r["wall_after"]
    armed_seen = None
    end = wall() + 8.0
    while wall() < end:
        if w_status(f"{tag}_armchk", table).get("status") == "armed":
            armed_seen = wall()
            break
        time.sleep(0.3)
    return {"table": table, "arm_wall": arm_wall, "armed_seen_wall": armed_seen, "seconds": seconds}


def parse_raw(s):
    d = {}
    parts = str(s).split(" ")
    for part in parts:
        if "=" in part:
            k, v = part.split("=", 1)
            n = to_num(v)
            d[k] = n if n is not None else v
        elif part == "RESET":
            d["RESET"] = True
    return d


def w_collect(tag, arm, fields):
    table = arm["table"]
    end = arm["arm_wall"] + arm["seconds"] + DONE_WAIT_S
    done = None
    while wall() < end:
        s = w_status(f"{tag}_donechk", table)
        if s.get("status") == "done":
            done = s
            break
        time.sleep(1.0)
    keys = ["samples", "windowMs", "status", "resets"]
    for f in fields:
        keys += [f"first_{f}", f"last_{f}", f"min_{f}", f"max_{f}", f"n_{f}", f"absent_{f}"]
    sc = md_read(f"{tag}_scal", table, keys)
    raws = md_read(f"{tag}_raw", table, [f"raw_{i}" for i in range(1, 51)])
    samples = to_num(sc["values"].get("samples"))
    raw = []
    for i in range(1, 51):
        v = raws["values"].get(f"raw_{i}")
        if v is not None:
            raw.append(parse_raw(v))
    if samples is not None:
        raw = raw[:int(samples)]
    hist = {}
    if table == SW:
        hk = [f"hist_asleep_{b}" for b in ("true", "false")]
        hist = md_read(f"{tag}_hist", table, hk)["values"]
    g = sc["values"]
    flds = {f: {"first": to_num(g.get(f"first_{f}")), "last": to_num(g.get(f"last_{f}")),
                "min": to_num(g.get(f"min_{f}")), "max": to_num(g.get(f"max_{f}")),
                "n": to_num(g.get(f"n_{f}")), "absent": g.get(f"absent_{f}")} for f in fields}
    return {"done": done, "samples": samples, "windowMs": to_num(g.get("windowMs")), "status": g.get("status"),
            "resets": to_num(g.get("resets")), "fields": flds, "hist": hist, "raw": raw}


def spawn(full_type, why):
    ok, reply = S().rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", C(), "witness.fields", f"item {USER}/{full_type} getID"))
        fields = seen.get("fields") or {}
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": seen.get("resolved"),
                                "id": fields.get("getID")})
        if seen.get("resolved"):
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    row["server_has"] = chain_srv(f"spawn_{why}_srv", f"getInventory.getFirstTypeRecurse({full_type}).getID")
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    persist()
    return row


def poll_stats(key, until, every=1.0, extra=None):
    polls = []
    i = 0
    while wall() < until:
        t_start = wall()
        s = stats_all(f"{key}_p{i}")
        if extra is not None:
            s["extra"] = extra(i)
        polls.append(s)
        i += 1
        rest = every - (wall() - t_start)
        if rest > 0:
            time.sleep(rest)
    return polls


def read_ini(server):
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


# ---------------- arms ----------------

def s0(B):
    X = B["S0"] = {}
    X["markers"] = {k: ack(step(f"s0_{k}", S(), "lua.global", k)).get("value")
                    for k in ("TKX_SleepWatch_Installed", "TKX_BoozeWatch_Installed", "NR_IntakeDrink_Installed")}
    X["stats"] = stats_all("s0_stats")
    X["record"] = record("s0")
    persist()


def arm_A(B, key, writes, seconds):
    A = B[key] = {}
    A["pre"] = w_reset(key, SW, SW_FIELDS)
    A["stats_before"] = stats_all(f"{key}_before")
    A["arm"] = w_arm(key, SW, seconds)
    base = A["arm"]["armed_seen_wall"] or wall()
    A["writes"] = []
    A["polls"] = []
    for k, dt in enumerate(writes):
        while wall() < base + dt:
            A["polls"].append(stats_all(f"{key}_p{len(A['polls'])}"))
            time.sleep(max(0.0, min(1.0, base + dt - wall())))
        w = setany(f"{key}_w{k}", "FATIGUE", 0.5)
        w["next"] = stats_get(f"{key}_w{k}_next")
        A["writes"].append(w)
    A["polls"] += poll_stats(f"{key}_tail", A["arm"]["arm_wall"] + seconds - 0.5)
    A["watch"] = w_collect(key, A["arm"], SW_FIELDS)
    A["stats_after"] = stats_all(f"{key}_after")
    persist()


def arm_B(B):
    X = B["B"] = {}
    X["spawn"] = spawn(BEER, "B")
    X["record_before"] = record("B_before")
    X["stats_before"] = stats_all("B_stats_before")
    X["litres_before"] = litres_srv("B_l_before", BEER)
    X["pre"] = w_reset("B", BW, BW_FIELDS)
    X["arm"] = w_arm("B", BW, B_WINDOW_S)
    X["drink_wall"] = wall()
    X["drink"] = ack(step("B_drink", C(), "drink.action", f"{BEER} 1"))
    X["fallback"] = None
    state = {"fell": False}

    def extra(i):
        lv = litres_srv(f"B_l{i}", BEER)
        if lv["value"] is not None and X["litres_before"]["value"] is not None \
                and lv["value"] < X["litres_before"]["value"] - 1e-6:
            state["fell"] = True
        if X["fallback"] is None and not state["fell"] and wall() > X["drink_wall"] + B_FALLBACK_S:
            X["fallback"] = {"wall": wall(), "ack": ack(step("B_fallback_drink", S(), "drink", f"{USER} {BEER} 1"))}
        return {"litres": lv["value"], "raw": lv["raw"]}
    X["polls"] = poll_stats("B", X["arm"]["arm_wall"] + B_WINDOW_S - 0.5, 1.0, extra)
    X["watch"] = w_collect("B", X["arm"], BW_FIELDS)
    X["record_after"] = record("B_after")
    persist()
    # B2: the decay alone
    Y = B["B2"] = {}
    Y["pre"] = w_reset("B2", BW, BW_FIELDS)
    Y["arm"] = w_arm("B2", BW, B2_WINDOW_S)
    Y["set"] = setany("B2_set", "INTOXICATION", B2_INTOX)
    Y["polls"] = poll_stats("B2", Y["arm"]["arm_wall"] + B2_WINDOW_S - 0.5)
    Y["watch"] = w_collect("B2", Y["arm"], BW_FIELDS)
    Y["zero"] = setany("B2_zero", "INTOXICATION", 0)
    persist()


def arm_C(B, key):
    X = B[key] = {}
    X["spawn"] = spawn(MUG, key)
    X["fill"] = ack(step(f"{key}_fill", S(), "fluid.fill", f"{USER} {MUG} Coffee {COFFEE_L}"))
    X["pre"] = w_reset(key, SW, SW_FIELDS)
    X["stats_before"] = stats_all(f"{key}_before")
    X["arm"] = w_arm(key, SW, C_WINDOW_S)
    time.sleep(1.0)
    r = step(f"{key}_drink", S(), "drink", f"{USER} {MUG} 1")
    a = ack(r)
    X["drink_wall"] = r["wall_before"]
    X["drink"] = {k: a.get(k) for k in ("selectedFullType", "primaryFluid", "route", "drinkFluidReturned",
                                         "before", "after", "delta", "predictedStats", "error", "selected")}
    if not a:
        X["drink"]["reply"] = r["ack"]
    X["next"] = stats_get(f"{key}_next")
    X["polls"] = poll_stats(key, X["arm"]["arm_wall"] + C_WINDOW_S - 0.5)
    X["watch"] = w_collect(key, X["arm"], SW_FIELDS)
    X["litres_after"] = litres_srv(f"{key}_l_after", MUG)
    persist()


def arm_D(B, key):
    X = B[key] = {}
    X["spawn"] = spawn(PILL, key)
    X["record_before"] = record(f"{key}_before")
    X["uses_before"] = uses_srv(f"{key}_u_before", PILL)
    X["stats_before"] = stats_all(f"{key}_stats_before")
    X["pre"] = w_reset(key, SW, SW_FIELDS)
    X["arm"] = w_arm(key, SW, D_WINDOW_S)
    X["take_wall"] = wall()
    X["take"] = ack(step(f"{key}_take", C(), "pill.take.held", f"{USER} {PILL}"))
    X["polls"] = poll_stats(key, wall() + D_POLL_S, 1.0, lambda i: uses_srv(f"{key}_u{i}", PILL)["value"])
    X["watch"] = w_collect(key, X["arm"], SW_FIELDS)
    X["record_after"] = record(f"{key}_after")
    X["uses_after"] = uses_srv(f"{key}_u_after", PILL)
    persist()


def arm_E(B):
    X = B["E"] = {}
    X["pre"] = w_reset("E", SW, SW_FIELDS)
    X["stats_before"] = stats_all("E_before")
    X["arm"] = w_arm("E", SW, E_WINDOW_S)
    X["hold"] = ack(step("E_hold", S(), "player.sleep.hold", f"{USER} {E_WINDOW_S}"))
    X["polls"] = []
    i = 0
    end = X["arm"]["arm_wall"] + E_WINDOW_S - 0.5
    while wall() < end:
        t_start = wall()
        X["polls"].append(stats_get(f"E_p{i}"))
        i += 1
        rest = E_POLL_EVERY - (wall() - t_start)
        if rest > 0:
            time.sleep(rest)
    X["watch"] = w_collect("E", X["arm"], SW_FIELDS)
    X["cancel"] = ack(step("E_cancel", S(), "player.sleep.hold", f"{USER} 0"))
    X["stats_after"] = stats_all("E_after")
    persist()


def body1(B):
    s0(B)
    arm_A(B, "A", A_WRITES, A_WINDOW_S)
    arm_B(B)
    arm_C(B, "C")
    arm_D(B, "D")


def body2(B):
    s0(B)
    arm_A(B, "A2", (0.5,), A2_WINDOW_S)
    arm_C(B, "C2")
    arm_D(B, "D2")
    arm_E(B)


def wait_doctor(B):
    rows = []
    end = time.time() + DOCTOR_WAIT_S
    clean = False
    while time.time() < end:
        ok, text = doctor()
        rows.append({"wall": wall(), "clean": ok, "text": text.strip().splitlines()[-6:]})
        if ok:
            clean = True
            break
        time.sleep(5.0)
    B["doctor_after"] = rows
    return clean


def run_boot(tag, prof, run_dir_b, body_fn):
    B = out[tag] = {"profile": prof.report(), "mods": list(prof.mods), "ini_requested": dict(prof.ini or {}),
                    "run_dir": os.path.relpath(run_dir_b, REPO)}
    cur.update({"tag": tag, "server": None, "client": None})
    clients = []
    server = None
    try:
        server = make_server(run_dir_b, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini)
        cur["server"] = server
        B["ini_seeded"] = read_ini(server)
        server.start(timeout=prof.server_timeout)
        client, _ = make_client(run_dir_b, USER, server, rec)
        cur["client"] = client
        client.start()
        clients.append(client)
        client.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", boot=tag)
        B["session_ready_wall"] = wall()
        B["build"] = server.build
        B["ini_after_ready"] = read_ini(server)
        B["verify"] = verify(prof, server, clients, tl)
        B["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                               "client": sorted(set(client.mods_not_found))}
        persist()
        try:
            body_fn(B)
        except Exception as e:                 # noqa: BLE001 - keep the rows already collected
            B["body_error"], B["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
            tl.mark("error", boot=tag, detail=str(e)[:200])
        persist()
    except Exception as e:                     # noqa: BLE001
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", boot=tag, detail=str(e)[:200])
    finally:
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                B["server_errors"] = server.errors[:20]
                B["server_error_count"] = len(server.errors)
                B["ini_after_stop"] = read_ini(server)
                B["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                             "limits": {"luaerr": LUAERR_LIMIT}}
                if clients:
                    B["logs"]["client_luaerr"] = grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)
            B["wall_end"] = wall()
            persist()
    return B


# ---------------- summaries (the grading is done from the raw, after the run) ----------------

def slope(polls, key):
    pts = [(p.get("srv_wall"), p.get(key), p.get("worldAge"), p.get("mult")) for p in polls
           if isinstance(p.get("srv_wall"), (int, float)) and isinstance(p.get(key), (int, float))]
    if len(pts) < 2:
        return None
    (w0, v0, a0, _), (w1, v1, a1, _) = pts[0], pts[-1]
    mults = [m for _, _, _, m in pts if isinstance(m, (int, float))]
    res = {"n": len(pts), "first": v0, "last": v1, "srv_wall_span_ms": w1 - w0,
           "per_wall_s": (v1 - v0) / ((w1 - w0) / 1000.0) if w1 != w0 else None,
           "mult_min": min(mults) if mults else None, "mult_max": max(mults) if mults else None}
    if isinstance(a0, (int, float)) and isinstance(a1, (int, float)) and a1 != a0:
        res["worldAge_span_h"] = a1 - a0
        res["per_game_h"] = (v1 - v0) / (a1 - a0)
    return res


def summarise():
    sm = out["summaries"]
    b1, b2 = out.get("boot1") or {}, out.get("boot2") or {}
    sm["ini"] = {"boot1": (b1.get("ini_after_ready") or {}).get("values"),
                 "boot2": (b2.get("ini_after_ready") or {}).get("values"),
                 "boot2_seeded": (b2.get("ini_seeded") or {}).get("values")}
    for bt, keys in (("boot1", ("A", "C", "D")), ("boot2", ("A2", "C2", "D2", "E"))):
        bb = out.get(bt) or {}
        for k in keys:
            X = bb.get(k) or {}
            w = X.get("watch") or {}
            sm[f"{bt}.{k}"] = {"resets": w.get("resets"), "samples": w.get("samples"),
                               "fat": (w.get("fields") or {}).get("fat"), "hist": w.get("hist"),
                               "fatigue_slope": slope(X.get("polls") or [], "fatigue")}
    for k in ("B", "B2"):
        X = b1.get(k) or {}
        w = X.get("watch") or {}
        sm[f"boot1.{k}"] = {"samples": w.get("samples"), "intox": (w.get("fields") or {}).get("intox"),
                            "intox_slope": slope(X.get("polls") or [], "intox")}


prof1, prof2 = profile.load(PROFILES[0]), profile.load(PROFILES[1])
rec = None if DRY_RUN else fx.load(prof1.fixture)
run_id, run_dir = ("x151s-dry-run", None) if DRY_RUN else new_run_dir("x151s")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
cur = {"tag": "pre", "server": None, "client": None}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profiles": list(PROFILES),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commits": {m: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/{m}") for m in (SW, BW)},
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {"BEER": BEER, "MUG": MUG, "PILL": PILL, "COFFEE_L": COFFEE_L, "A_WINDOW_S": A_WINDOW_S,
                  "A_WRITES": list(A_WRITES), "B_WINDOW_S": B_WINDOW_S, "B_FALLBACK_S": B_FALLBACK_S,
                  "B2_WINDOW_S": B2_WINDOW_S, "B2_INTOX": B2_INTOX, "C_WINDOW_S": C_WINDOW_S,
                  "D_WINDOW_S": D_WINDOW_S, "D_POLL_S": D_POLL_S, "A2_WINDOW_S": A2_WINDOW_S,
                  "E_WINDOW_S": E_WINDOW_S, "E_POLL_EVERY": E_POLL_EVERY},
    "deviations": [
        "First live use of fluid.fill (server twin) and pill.take.held (commit 839dfdb), and of TKX_SleepWatch "
        "and TKX_BoozeWatch: each reply is its smoke test.",
        "Beer is Base.BeerCan spawned by RCON (prefilled Beer 0.3 L), not fluid.fill 0.5 L (capacity 0.3); "
        "server drink fallback at 25 s if the server can's litres have not moved.",
        "Coffee 0.2 L in Base.Mugl (capacity 0.2) by the server fluid.fill twin, drunk by the server drink command.",
        "The pill is RCON-spawned and taken with pill.take.held; D also runs on boot 2 (D2).",
        "A writes FATIGUE 0.5 three times in one 30 s window; INTOXICATION is zeroed after B2.",
        "Boot 2 runs A2, C2, D2, then E last.",
    ],
    "world_changes": {"restored": "the golden fixture restored into each boot's run dir",
                      "left_in_place": ["a BeerCan, a Mugl and a PillsVitamins per boot", "FATIGUE and INTOXICATION written"]},
    "steps": [], "notes": [], "summaries": {},
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    run_boot("boot1", prof1, run_dir, body1)
    if wait_doctor(out["boot1"]):
        run_boot("boot2", prof2, os.path.join(run_dir, "boot2"), body2)
    else:
        out["boot2"] = {"error": "doctor did not come back clean after boot 1; boot 2 not started (one session at a time)"}
    try:
        summarise()
    except Exception as e:                     # noqa: BLE001
        out["summary_error"] = f"{type(e).__name__}: {e}"
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summaries": out.get("summaries"), "error": out.get("error"),
                  "boot1_error": (out.get("boot1") or {}).get("body_error"),
                  "boot2_error": (out.get("boot2") or {}).get("body_error")}, indent=1, default=str)[:9000])
