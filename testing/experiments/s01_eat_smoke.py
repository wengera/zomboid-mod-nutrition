"""Slice 01 smoke test: the eating pipeline against a live MP session.

Boots the `default` fixture (server + admin client), then:
  1. direct `p:Eat(item, fraction, false)` on the client for apple 1.0 / apple 0.5 /
     cooked steak / rotten bread -- measures the intake arithmetic;
  2. the real MP path (`ISEatFoodAction` queued on the client, completed on the server)
     and how long the result takes to reach the client;
  3. two authority probes: a client-side nutrition.set and a server-side one.

Everything lands in <run_dir>/eat-smoke.json. Run it with the whole machine idle
(`python testing/pzt doctor` first): only one PZ session may be up at a time.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
from pzt import fixture as fx
from pzt.bus import parse_ack
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

POLL_SECONDS = 12
ANY_CHANGE_KCAL = 0.5      # above the read noise
MEAL_KCAL = 10.0           # a one-second step this big is food arriving, not metabolism


def ask(side, cmd, args="", timeout=20):
    """One bus command. A dead or wedged side is recorded, not raised: the remaining
    probes are still worth collecting."""
    try:
        return parse_ack(side.send(cmd, args, timeout=timeout))[1]
    except (RuntimeError, TimeoutError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp01")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
out = {"run_id": run_id}
try:
    server.start()
    c, _ = make_client(run_dir, "admin", server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")

    # ---- 1. direct Eat: the arithmetic ---------------------------------------
    for cmd, args in [("nutrition.get", ""), ("item.script", "Base.Apple"), ("eat", "Base.Apple 1.0"),
                      ("eat", "Base.Apple 0.5"), ("item.state", "Base.Steak cooked"), ("eat", "Base.Steak 1.0"),
                      ("item.state", "Base.Bread rotten"), ("eat", "Base.Bread 1.0")]:
        out[f"{cmd} {args}".strip()] = ask(c, cmd, args)
        tl.mark("cmd", cmd=cmd, args=args)

    # Did any of that reach the server? (S6 says client-side mutations do not.)
    out["direct_eat_visibility"] = {
        "client": ask(c, "nutrition.get"),
        "server": ask(server, "nutrition.get", "admin", timeout=30),
    }
    tl.mark("direct_eat_visibility")

    # ---- 2. the real MP path: ISEatFoodAction, completed server-side ---------
    # The apple has to exist on the SERVER for the mirrored NetTimedAction to find it, and
    # client-side AddItem is invisible there (spike S6) -- so spawn it over RCON.
    # First finish the half apple left over from `eat Base.Apple 0.5` so the only apple in
    # the inventory is the server's (and record what a part-eaten item is worth).
    out["eat Base.Apple 1.0 (leftover half)"] = ask(c, "eat", "Base.Apple 1.0")
    ok_rcon, reply = server.rcon('additem "admin" "Base.Apple" 1')
    probe = {"rcon_additem": reply if ok_rcon else f"rcon failed: {reply}"}
    tl.mark("rcon_additem", ok=ok_rcon, reply=str(reply)[:80])
    time.sleep(3)                                    # let the item reach the client inventory
    probe["queued"] = ask(c, "eat.action", "Base.Apple 1.0")
    t0 = time.time()
    tl.mark("eat_action_queued")
    base = probe["queued"].get("before") if isinstance(probe["queued"], dict) else None
    # Calories drift down ~0.26/s from metabolism even when nothing is eaten, so "changed"
    # needs two thresholds: ANY movement, and movement big enough to be the meal itself.
    samples, first_change, first_meal = [], None, None
    while time.time() - t0 < POLL_SECONDS:
        snap = ask(c, "nutrition.get")
        row = {"t": round(time.time() - t0, 1), "snap": snap}
        if isinstance(snap, dict) and isinstance(base, dict):
            row["dCalories"] = round(snap.get("calories", 0) - base.get("calories", 0), 3)
            row["stepCalories"] = round(row["dCalories"] - (samples[-1].get("dCalories", 0.0)
                                                            if samples else 0.0), 3)
            if first_change is None and abs(row["dCalories"]) > ANY_CHANGE_KCAL:
                first_change = row
            if first_meal is None and row["stepCalories"] > MEAL_KCAL:
                first_meal = row
        samples.append(row)
        time.sleep(max(0.0, 1.0 - (time.time() - t0) % 1.0))
    probe["poll"] = samples
    probe["first_change"] = first_change              # any movement (metabolic drain counts)
    probe["first_meal_change"] = first_meal           # the eat landing on the client
    probe["server_after"] = ask(server, "nutrition.get", "admin", timeout=30)
    out["probe_a_eat_action"] = probe
    tl.mark("probe_a_done", first_change_t=(first_change or {}).get("t"),
            first_meal_t=(first_meal or {}).get("t"))

    # ---- 3a. authority check A: does a client-side write survive? ------------
    a = {"before": ask(c, "nutrition.get")}
    a["client_set_3000"] = ask(c, "nutrition.set", "calories 3000")
    a["server_immediately"] = ask(server, "nutrition.get", "admin", timeout=30)
    time.sleep(3)
    a["client_after_3s"] = ask(c, "nutrition.get")
    a["server_after_3s"] = ask(server, "nutrition.get", "admin", timeout=30)
    out["probe_b_client_set"] = a
    tl.mark("probe_b_done")

    # ---- 3b. authority check B: does a server-side write reach the client? ---
    b = {"client_before": ask(c, "nutrition.get"),
         "server_before": ask(server, "nutrition.get", "admin", timeout=30)}
    b["server_set_2500"] = ask(server, "nutrition.set", "admin calories 2500", timeout=30)
    time.sleep(3)
    b["client_after_3s"] = ask(c, "nutrition.get")
    b["server_after_3s"] = ask(server, "nutrition.get", "admin", timeout=30)
    out["probe_c_server_set"] = b
    tl.mark("probe_c_done")
except (RuntimeError, TimeoutError) as e:
    out["error"] = f"{type(e).__name__}: {e}"
    tl.mark("error", detail=str(e)[:200])
finally:
    out["timeline"] = tl.items
    out["server_errors"] = server.errors[:20]
    path = os.path.join(run_dir, "eat-smoke.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {path}")
    try:
        teardown(tl, server, clients)
    finally:
        for cl in clients:
            cl.kill()
        server.kill()
print(json.dumps(out, indent=1)[:4000])
