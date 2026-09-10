"""Slice 01 measured matrix: what one eat actually transfers, per item and per state.

Extends the smoke test (`s01_eat_smoke.py`) from four spot checks into the full grid the
plan needs as **M** rows:

  1. 5 items x 5 states, `eat <type> 1.0` -- the intake arithmetic of IsoGameCharacter.Eat;
  2. fractions 0.25 / 0.5 on a fresh apple -- is the transfer proportional;
  3. the real MP path (`eat.action` on a server-spawned apple) with a client poll and the
     server's own view through `witness.nutrition`;
  4. the `Nutrition` sandbox option flipped at runtime, against a same-time-speed control;
  5. the `Nutrition` setter clamps the slice-04 predictions depend on.

Two facts from task 3 shape the whole script:
  * the SERVER owns Nutrition -- a client write is discarded inside a second -- so every
    authoritative read is `nutrition.get admin` on the SERVER bus, and the only client
    number trusted without a wait is `eat`'s synchronous `delta` (the same Java arithmetic
    the server runs);
  * hunger/thirst are clamped to [0,1] and the fixture character is satiated, so an eat's
    hunger relief is otherwise discarded and dHunger/dThirst measure nothing. Every eat is
    preceded by a `stats.set` prime, over whichever side a probe shows is authoritative,
    and each row carries its own `before.hunger` as proof the prime held.

Items are spawned SERVER-side (RCON `additem`) so the mirrored action can find them and so
the client-spawn NPE (task 3, concern 1) stays out of the log; `spawned` on every row says
whether that worked.

Everything lands in <run_dir>/eat-matrix.json. ~6 minutes, one session; run it with the
machine idle (`python testing/pzt doctor` first).
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
from _common import ask, hard_kill, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

SPAWN_WAIT = 2.5        # RCON additem -> item visible in the client's inventory
MIRROR_WAIT = 2.5       # server write -> 1 Hz PlayerStatsPacket -> client
POLL_SECONDS = 12       # eat.action landing window (the smoke test saw it at 5.5 s)
MEAL_KCAL = 10.0        # a one-second step this big is food arriving, not metabolism
DRAIN_SECONDS = 20      # each half of the sandbox toggle test, at settimespeed 30
PRIME = "hunger 0.9 thirst 0.9"   # headroom so the [0,1] clamp does not eat the relief

# `cookable`/`rots` are the *expectation* from media/scripts/generated/items/food.txt, not a
# skip list: every cell is still attempted and `state_applied` records whether the flag
# actually stuck. A cell whose flag does not stick is an n/a row with a measured reason
# (and eating it anyway keeps the inventory clean for the next cell).
ITEMS = [
    {"type": "Base.Apple", "cookable": False, "rots": True,
     "script": "HungerChange -16, ThirstChange -7, 95 kcal, C25.13/L0.31/P0.47, DaysFresh 5"},
    {"type": "Base.Steak", "cookable": True, "rots": True,
     "script": "HungerChange -40, 220 kcal, C0/L9.35/P31.62, DaysFresh 2, cook 50/burn 70"},
    {"type": "Base.Bread", "cookable": False, "rots": True,
     "script": "HungerChange -30, 532 kcal, C99/L6.66/P17.7, DaysFresh 3, Packaged"},
    {"type": "Base.Carrots", "cookable": True, "rots": True,
     "script": "HungerChange -8, ThirstChange -4, 25 kcal, C6/L0.15/P0.6, cook 10/burn 30"},
    # the drink row: ThirstChange and NO HungerChange, chosen from food.txt (the only such
    # family is HotDrink*; `Base.HotDrink` is the plain one, ReplaceOnUse Base.Mugl).
    {"type": "Base.HotDrink", "cookable": True, "rots": False,
     "script": "ThirstChange -20, NO HungerChange, no macros, cook 10/burn 50, ReplaceOnUse Base.Mugl"},
]
STATES = ["fresh", "cooked", "burnt", "rotten", "frozen"]
DELTA_KEYS = ["hunger", "thirst", "calories", "carbs", "lipids", "proteins", "weight"]


def num(d, key):
    """The numeric value at `key`, or None -- every read here can also be an error dict."""
    if isinstance(d, dict) and isinstance(d.get(key), (int, float)):
        return d[key]
    return None


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp01")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
out = {"run_id": run_id, "items": ITEMS, "states": STATES, "prime": PRIME}
stats_route = "client"          # decided by the probe below
try:
    server.start()
    c, _ = make_client(run_dir, "admin", server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")

    def prime():
        """Put hunger/thirst back where an eat's relief is visible, over the side that owns
        them. `stats_route` is decided once, by the probe below."""
        if stats_route == "server":
            r = ask(server, "stats.set", "admin " + PRIME, timeout=30)
            time.sleep(MIRROR_WAIT)
            return r
        return ask(c, "stats.set", PRIME)

    def witness(tag):
        """The server's own numbers, pushed to the client and compared there (S6 channel)."""
        t = time.time()
        sent = ask(c, "witness.nutrition")
        try:
            res = c.bus.wait_result("witness_nutrition", timeout=15, after=t)
        except (RuntimeError, TimeoutError) as e:
            res = {"error": f"{type(e).__name__}: {e}"}
        return {"tag": tag, "sent": sent, "result": res}

    # ---- 0. who owns hunger/thirst? ------------------------------------------
    # The nutrition.set pair settled Nutrition; stats are a separate Java object, so ask
    # again rather than assume. Distinct values (0.9 client / 0.4 server) so the read-back
    # says which write is showing.
    sp = {"before": ask(c, "nutrition.get")}
    sp["client_set_0.9"] = ask(c, "stats.set", "hunger 0.9 thirst 0.9")
    sp["server_immediately"] = ask(server, "nutrition.get", "admin", timeout=30)
    time.sleep(3)
    sp["client_after_3s"] = ask(c, "nutrition.get")
    sp["server_after_3s"] = ask(server, "nutrition.get", "admin", timeout=30)
    sp["server_set_0.4"] = ask(server, "stats.set", "admin hunger 0.4 thirst 0.4", timeout=30)
    time.sleep(3)
    sp["client_after_server_set"] = ask(c, "nutrition.get")
    h_client, h_server = num(sp["client_after_3s"], "hunger"), num(sp["client_after_server_set"], "hunger")
    sp["client_write_survives_3s"] = h_client is not None and h_client > 0.7
    sp["server_write_reaches_client"] = h_server is not None and 0.2 < h_server < 0.6
    if sp["client_write_survives_3s"]:
        stats_route = "client"          # cheapest: no mirror wait before each eat
    elif sp["server_write_reaches_client"]:
        stats_route = "server"
    else:
        stats_route = "client"          # best effort; each row's before.hunger shows if it held
        sp["note"] = "neither write held for 3 s; priming on the client immediately before each eat"
    sp["route_used"] = stats_route
    out["probe_stats_authority"] = sp
    tl.mark("stats_authority", route=stats_route,
            client=sp["client_write_survives_3s"], server=sp["server_write_reaches_client"])

    out["time_at_start"] = ask(server, "time.snapshot", timeout=30)
    out["players"] = ask(server, "players", timeout=30)
    out["item_scripts"] = {it["type"]: ask(c, "item.script", it["type"]) for it in ITEMS}

    # ---- 1/2. the grid -------------------------------------------------------
    def cell(item, state, fraction):
        """One measured row: server-spawn a fresh copy, apply the state, prime, eat."""
        row = {"item": item["type"], "state": state, "fraction": fraction,
               "expected_applicable": (state in ("fresh", "rotten", "frozen")
                                       or item["cookable"]) and (state != "rotten" or item["rots"])}
        ok_rcon, reply = server.rcon(f'additem "admin" "{item["type"]}" 1')
        row["rcon_additem"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        st = ask(c, "item.state", f'{item["type"]} {state}')
        row["item_state_cmd"] = st
        # `item.state fresh` is only setAge(0) -- nothing to read back -- so it counts as
        # applied by definition; every other state has to show its flag true afterwards.
        row["state_applied"] = True if state == "fresh" else (isinstance(st, dict)
                                                              and st.get(state) is True)
        row["prime_result"] = prime()
        eaten = ask(c, "eat", f'{item["type"]} {fraction}')
        for key in ("delta", "before", "after", "itemBefore", "itemAfter", "spawned"):
            if isinstance(eaten, dict) and key in eaten:
                row[key] = eaten[key]
        if not isinstance(eaten, dict):
            row["eat_error"] = eaten
        if not row["state_applied"]:
            row["na_reason"] = (f"'{state}' did not stick on {item['type']}"
                                + ("" if row["expected_applicable"] else
                                   " (expected: IsCookable/DaysFresh absent in the script)"))
        # Leave nothing behind: a leftover of the same type would be what the next cell's
        # getFirstTypeRecurse finds, and the row after it would silently measure the wrong item.
        if row.get("itemAfter") != "consumed":
            row["flush"] = ask(c, "eat", f'{item["type"]} 1.0')
            if isinstance(row["flush"], dict) and row["flush"].get("itemAfter") != "consumed":
                row["flush_warning"] = "type still present after the flush eat"
        return row

    NAN_RESET = {"calories": 1000.0, "carbs": 100.0, "lipids": 20.0, "proteins": 50.0,
                 "weight": 80.0}

    def nan_guard(tag):
        """A drink whose script has no HungerChange makes Eat's fraction arithmetic a 0/0,
        and one NaN in a store would make every later probe meaningless (TK.json writes NaN
        as null). Check the authoritative side after each item and reset anything that is no
        longer a number, so a bad cell costs one row and not the rest of the run."""
        snap = ask(server, "nutrition.get", "admin", timeout=30)
        bad = [k for k in list(NAN_RESET) + ["hunger", "thirst"] if num(snap, k) is None]
        g = {"tag": tag, "server": snap, "non_numeric": bad}
        if bad:
            g["reset"] = {k: (ask(server, "nutrition.set", f"admin {k} {NAN_RESET[k]}", timeout=30)
                              if k in NAN_RESET
                              else ask(server, "stats.set", f"admin {k} 0.5", timeout=30))
                          for k in bad}
            tl.mark("nan_guard_reset", tag=tag, fields=",".join(bad))
        return g

    rows, guards = [], []
    for item in ITEMS:
        for state in STATES:
            r = cell(item, state, 1.0)
            rows.append(r)
            tl.mark("cell", item=item["type"], state=state, applied=r["state_applied"],
                    kcal=round(num(r.get("delta"), "calories") or 0.0, 2))
        guards.append(nan_guard("after " + item["type"]))
    # proportionality: fresh apple at two fractions, a new copy each time
    for fraction in (0.25, 0.5):
        r = cell(ITEMS[0], "fresh", fraction)
        rows.append(r)
        tl.mark("cell", item=ITEMS[0]["type"], state="fresh", fraction=fraction,
                kcal=round(num(r.get("delta"), "calories") or 0.0, 2))
    guards.append(nan_guard("after fractions"))
    out["rows"], out["nan_guards"] = rows, guards
    tl.mark("matrix_done", rows=len(rows))

    # ---- 3. the real MP path on a server-spawned apple ------------------------
    errors_before = len(server.errors)
    probe = {"server_errors_before": errors_before}
    ok_rcon, reply = server.rcon('additem "admin" "Base.Apple" 1')
    probe["rcon_additem"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
    time.sleep(SPAWN_WAIT)
    probe["prime_result"] = prime()
    probe["witness_before"] = witness("before")
    probe["queued"] = ask(c, "eat.action", "Base.Apple 1.0")
    t0 = time.time()
    tl.mark("eat_action_queued")
    base = probe["queued"].get("before") if isinstance(probe["queued"], dict) else None
    samples, first_meal = [], None
    while time.time() - t0 < POLL_SECONDS:
        snap = ask(c, "nutrition.get")
        row = {"t": round(time.time() - t0, 1), "snap": snap}
        if num(snap, "calories") is not None and num(base, "calories") is not None:
            row["dCalories"] = round(snap["calories"] - base["calories"], 3)
            row["stepCalories"] = round(row["dCalories"] - (samples[-1].get("dCalories", 0.0)
                                                            if samples else 0.0), 3)
            if first_meal is None and row["stepCalories"] > MEAL_KCAL:
                first_meal = row
        samples.append(row)
        time.sleep(max(0.0, 1.0 - (time.time() - t0) % 1.0))
    probe["poll"] = samples
    probe["first_meal_change"] = first_meal      # the eat landing on the client
    probe["witness_immediately"] = witness("immediately_after_poll")
    time.sleep(5)
    probe["witness_after_5s"] = witness("after_5s")
    probe["server_after"] = ask(server, "nutrition.get", "admin", timeout=30)
    probe["server_errors_after"] = len(server.errors)
    probe["new_server_errors"] = server.errors[errors_before:][:10]
    out["probe_real_path"] = probe
    tl.mark("real_path_done", first_meal_t=(first_meal or {}).get("t"),
            new_errors=probe["server_errors_after"] - errors_before)

    # ---- 4. the Nutrition sandbox option at runtime ---------------------------
    # Two equal windows at the SAME time speed: the first with the option untouched is the
    # control, so any difference in the second is the flip and not the clock.
    sb = {"read_before": ask(c, "sandbox.set", "Nutrition")}
    ok_rcon, reply = server.rcon("settimespeed 30")
    sb["settimespeed_30"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
    sb["control_t0"] = ask(server, "nutrition.get", "admin", timeout=30)
    sb["control_time_t0"] = ask(server, "time.snapshot", timeout=30)
    time.sleep(DRAIN_SECONDS)
    sb["control_t20"] = ask(server, "nutrition.get", "admin", timeout=30)
    sb["control_time_t20"] = ask(server, "time.snapshot", timeout=30)
    sb["flip_false"] = ask(c, "sandbox.set", "Nutrition false")
    sb["flipped_t0"] = ask(server, "nutrition.get", "admin", timeout=30)
    time.sleep(DRAIN_SECONDS)
    sb["flipped_t20"] = ask(server, "nutrition.get", "admin", timeout=30)
    sb["flipped_time_t20"] = ask(server, "time.snapshot", timeout=30)
    sb["restore_true"] = ask(c, "sandbox.set", "Nutrition true")
    ok_rcon, reply = server.rcon("settimespeed 1")
    sb["settimespeed_1"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
    for tag, a, b in (("control", "control_t0", "control_t20"), ("flipped", "flipped_t0", "flipped_t20")):
        ca, cb = num(sb[a], "calories"), num(sb[b], "calories")
        sb[f"{tag}_dCalories"] = round(cb - ca, 3) if ca is not None and cb is not None else None
    out["probe_sandbox"] = sb
    tl.mark("sandbox_done", control=sb["control_dCalories"], flipped=sb["flipped_dCalories"])

    # ---- 5. the setter clamps slice 04 has to predict against ------------------
    # Run last: it scrambles the stores. The server's nutrition.set returns the snapshot
    # taken right after the write, so the read-back and the clamp are the same ack.
    cl = {"before": ask(server, "nutrition.get", "admin", timeout=30)}
    for field in ("calories", "carbs", "lipids", "proteins"):
        cl[f"{field}_set_9999"] = ask(server, "nutrition.set", f"admin {field} 9999", timeout=30)
        cl[f"{field}_set_-9999"] = ask(server, "nutrition.set", f"admin {field} -9999", timeout=30)
    for field in ("calories", "carbs", "lipids", "proteins"):
        was = num(cl["before"], field)
        if was is not None:
            cl[f"restore_{field}"] = ask(server, "nutrition.set", f"admin {field} {was}", timeout=30)
    cl["after_restore"] = ask(server, "nutrition.get", "admin", timeout=30)
    out["probe_clamps"] = cl
    tl.mark("clamps_done")

    # ---- report-ready summary --------------------------------------------------
    out["summary"] = [
        {"item": r["item"], "state": r["state"], "fraction": r["fraction"],
         "applied": r["state_applied"], "spawned": r.get("spawned"),
         "beforeHunger": num(r.get("before"), "hunger"), "beforeThirst": num(r.get("before"), "thirst"),
         **{f"d{k[0].upper()}{k[1:]}": (round(num(r.get("delta"), k), 4)
                                        if num(r.get("delta"), k) is not None else None)
            for k in DELTA_KEYS},
         "itemCalories": num(r.get("itemBefore"), "calories"),
         "itemHungChange": num(r.get("itemBefore"), "hungChange"),
         "note": r.get("na_reason") or ("leftover: " + str(r.get("flush_warning"))
                                        if r.get("flush_warning") else "")}
        for r in out.get("rows", [])
    ]
    out["log_grep"] = {}
except Exception as e:                   # noqa: BLE001 - a six-minute experiment must keep the
    out["error"] = f"{type(e).__name__}: {e}"   # rows it already has; the traceback is recorded
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # settimespeed is a WORLD change and must not outlive the run, whatever went wrong above.
    try:
        ok_rcon, reply = server.rcon("settimespeed 1")
        out["settimespeed_restored"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
        tl.mark("settimespeed_restored", ok=ok_rcon)
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        out["settimespeed_restored"] = f"{type(e).__name__}: {e}"
    path = os.path.join(run_dir, "eat-matrix.json")
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        # The plan asks for the EatFood / SyncItemFields lines from THIS run's server log;
        # after teardown the file is complete and the reader thread has stopped.
        try:
            log = os.path.join(run_dir, "server-stdout.log")
            hits = {"EatFood": [], "SyncItemFields": [], "Nutrition": []}
            with open(log, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    for key in hits:
                        if key in line and len(hits[key]) < 12:
                            hits[key].append(f"{i}: {line.rstrip()[:220]}")
            out["log_grep"] = hits
        except Exception as e:                   # noqa: BLE001 - teardown path, never raise
            out["log_grep"] = {"error": f"{type(e).__name__}: {e}"}
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:6000])
