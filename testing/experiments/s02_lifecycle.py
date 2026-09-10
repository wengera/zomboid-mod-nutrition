"""Slice 02 measured lifecycle: aging, freezing, cooking, evolved recipes, MP ownership.

All the **M** steps of tasks 2-5 in one live session (ledger ruling, 2026-09-10): one boot
instead of four, seven phases, each saved to disk the moment it finishes so a wedge in a
later phase cannot cost the earlier numbers.

Two facts from the code map (`docs/superpowers/plans/02-notes.md`) shape every phase:

  * **The SERVER owns item aging.** `Food.update @38-@46 L369-370` gates `updateAge` on
    `GameServer.server`, and `age` / `offAge` / `offAgeMax` / `freezingTime` are in **no**
    packet -- `ItemStatsPacket` carries the nutrition/cooking block and nothing else (Q8).
    So an age reading on the client measures the client's stale copy and nothing more; the
    real readings are taken on the server bus (`item.get` / `item.set` / `item.age.tick`).
    Phase (a) probes the client on purpose -- it isolates the *local getters'* arithmetic --
    and phases (b), (c) and (g) turn the client's staleness into the measurement.
  * **The write-only flags.** `setRotten(true)` is inert (`isRotten()` reads `age`) and
    `setFrozen(true)` is undone by the next `updateFreezing`; rot is forced with
    `setAge(offAgeMax + 1)` and freezing with `freeze()` (Q2). Neither is offered by the
    new harness commands, so a phase cannot accidentally measure a dead field.

Phases:
  (a) client arithmetic  -- `item.age` at 0 / offAge-0.1 / offAge+0.1 / offAgeMax+0.1
  (b) server-side aging  -- does an `item.set ... age` (and then a synced `updateAge(true)`)
                            reach the client?
  (c) accelerated day    -- `settimespeed 30`, one game day, server age vs client age
  (d) freeze             -- `freeze()` then a game hour: the x0 age rate and the thaw rate
  (e) cooking transition -- `cookingTime` past `minutesToCook` / `minutesToBurn` + `update()`
  (f) evolved recipe     -- Salad from a Bowl + Lettuce + Tomato at Cooking 0 and Cooking 10
  (g) MP ownership       -- server `calories` (in the packet) vs server `age` (not in it)

Items are spawned SERVER-side (RCON `additem`) throughout: a client-spawned item is invisible
to the server and makes it log a `SyncItemFields` NPE (slice 01, `findOrSpawn`).

Everything lands in <run_dir>/lifecycle.json. ~12 minutes, one session; run it with the
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
SYNC_WAIT = 2.0         # server sendItemStats -> ItemStatsPacket applied on the client
TIME_SPEED = 30         # the accelerated-clock multiplier, restored to 1 in `finally`
DAY_CAP = 420           # wall-clock ceiling on the one-game-day wait (phase c)
HOUR_CAP = 150          # wall-clock ceiling on the one-game-hour wait (phase d)
SAMPLE_EVERY = 5        # seconds between time.snapshot samples inside a wait

STEAK = "Base.Steak"    # DaysFresh 2 / DaysTotallyRotten 4, IsCookable, cook 50 / burn 70
APPLE = "Base.Apple"    # DaysFresh 5 / DaysTotallyRotten 8, not cookable
BOWL = "Base.Bowl"      # evolvedrecipe Salad: BaseItem, no MinimumWater, not Cookable
# `use` is the hunger *points* from each item's own `EvolvedRecipe = ...:<use>` key in
# media/scripts/generated/items/food.txt; EvolvedRecipe.addItem divides it by 100 (Q5).
INGREDIENTS = [{"type": "Base.Lettuce", "use": 5}, {"type": "Base.Tomato", "use": 6}]
COOK_LEVELS = [0, 10]


def num(d, key):
    """The numeric value at `key`, or None -- every read here can also be an error dict."""
    if isinstance(d, dict) and isinstance(d.get(key), (int, float)) and not isinstance(d.get(key), bool):
        return d[key]
    return None


def sub(d, key):
    return d[key] if isinstance(d, dict) and isinstance(d.get(key), dict) else {}


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp02")
path = os.path.join(run_dir, "lifecycle.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
out = {"run_id": run_id, "phases": {}, "time_speed": TIME_SPEED,
       "items": {"steak": STEAK, "apple": APPLE, "bowl": BOWL, "ingredients": INGREDIENTS}}
cooking_before = None
try:
    server.start()
    c, _ = make_client(run_dir, "admin", server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")

    # ---- helpers -------------------------------------------------------------
    def spawn(*types):
        """Server-side spawn, one RCON per item, one settle wait for the batch."""
        res = {}
        for t in types:
            ok, reply = server.rcon(f'additem "admin" "{t}" 1')
            res[t] = str(reply) if ok else f"rcon failed: {reply}"
        time.sleep(SPAWN_WAIT)
        return res

    def witness(fulltype, tag):
        """The server's own item state, pushed to the client and diffed there (S6 channel).
        `stateDiff` in the result is the direct reading of what ItemStatsPacket carries."""
        t = time.time()
        sent = ask(c, "witness.item", fulltype)
        try:
            res = c.bus.wait_result("witness_item", timeout=15, after=t)
        except (RuntimeError, TimeoutError) as e:
            res = {"error": f"{type(e).__name__}: {e}"}
        return {"tag": tag, "sent": sent, "result": res}

    def srv(cmd, args):
        return ask(server, cmd, args, timeout=30)

    def timespeed(mult):
        ok, reply = server.rcon(f"settimespeed {mult}")
        return str(reply) if ok else f"rcon failed: {reply}"

    def wait_game_hours(hours, cap, tag, every=SAMPLE_EVERY):
        """Block until the SERVER's world clock has advanced `hours`, or `cap` seconds pass.
        Driven by the measured clock rather than a wall-clock guess: the wall time a game day
        costs depends on the world's minutes-per-day, which this harness does not pin.
        `every` is the sampling granularity, and therefore the worst-case overshoot: phase (d)
        needs a fine one, because a steak fully thaws (freezingTime 100 -> 0) after 1.5 game
        hours and the x0 age rate it is there to measure would go with it."""
        start = srv("time.snapshot", "")
        w0 = num(start, "worldAge")
        samples, t0, reached = [{"t": 0.0, "snap": start}], time.time(), False
        while time.time() - t0 < cap:
            time.sleep(every)
            snap = srv("time.snapshot", "")
            samples.append({"t": round(time.time() - t0, 1), "snap": snap})
            w = num(snap, "worldAge")
            if w0 is not None and w is not None and w - w0 >= hours:
                reached = True
                break
        w1 = num(samples[-1]["snap"], "worldAge")
        return {"tag": tag, "requestedHours": hours, "reachedTarget": reached,
                "wallSeconds": round(time.time() - t0, 1),
                "worldAgeStart": w0, "worldAgeEnd": w1,
                "dWorldHours": (w1 - w0) if (w0 is not None and w1 is not None) else None,
                "samples": samples}

    def run_phase(key, label, fn):
        tl.mark("phase_start", step=key)
        try:
            res = fn()
        except Exception as e:                       # noqa: BLE001 - one phase must not cost the rest
            res = {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-2000:]}
            tl.mark("phase_error", step=key, detail=str(e)[:120])
            print(res["traceback"])
        if not isinstance(res, dict):
            res = {"result": res}
        res["label"] = label
        out["phases"][key] = res
        save(path, out, tl, server)                  # incremental: evidence survives a later wedge
        tl.mark("phase_done", step=key)
        return res

    # ---- session context -----------------------------------------------------
    out["time_at_start"] = srv("time.snapshot", "")
    out["players"] = srv("players", "")
    # The rot-rate constants the deltas have to be read against (Q2: age += hours*rotSpeed/24;
    # FoodRotSpeed 3 = 1.0). `sandbox.set <name>` with no value only reports.
    out["sandbox"] = {k: ask(c, "sandbox.set", k)
                      for k in ("FoodRotSpeed", "FridgeFactor", "DaysForRottenFoodRemoval",
                                "ElecShutModifier")}
    out["item_scripts"] = {t: ask(c, "item.script", t)
                           for t in [STEAK, APPLE] + [i["type"] for i in INGREDIENTS]}
    # Which perk API answers -- and the level to put back in `finally`. Setting Cooking to 0
    # is also exactly the precondition phase (f) round 1 needs.
    out["probe_perk_api"] = ask(c, "perk.set", "Cooking 0")
    cooking_before = out["probe_perk_api"].get("before") if isinstance(out["probe_perk_api"], dict) else None
    tl.mark("perk_api", route=(out["probe_perk_api"].get("route")
                               if isinstance(out["probe_perk_api"], dict) else "error"),
            before=cooking_before)

    # ---- (a) client-side arithmetic ------------------------------------------
    # The five Food getters as a pure function of age. Nothing here is aging: `item.age` is a
    # bare setAge on the client's copy, and Q3 predicts hungChange scales (1 / 1.3 / 2.2) while
    # the four macros do NOT move at all.
    def phase_a():
        r = {"spawn": spawn(STEAK)}
        r["baseline"] = ask(c, "item.state", STEAK)          # read-only: no state argument
        off = num(r["baseline"], "offAge")
        off_max = num(r["baseline"], "offAgeMax")
        if off is None or off_max is None:
            r["error"] = "offAge/offAgeMax absent from itemState; cannot pick the four ages"
            return r
        r["offAge"], r["offAgeMax"] = off, off_max
        r["ages"] = [0.0, round(off - 0.1, 3), round(off + 0.1, 3), round(off_max + 0.1, 3)]
        r["rows"] = [ask(c, "item.age", f"{STEAK} {a}") for a in r["ages"]]
        return r

    pa = run_phase("a_client_arithmetic", "client getters vs age (no aging involved)", phase_a)

    # ---- (b) does a server-side age reach the client? -------------------------
    # Both sides are pinned to a KNOWN, DIFFERENT value first, so "the client did not move" is
    # falsifiable rather than a coincidence of two equal numbers.
    def phase_b():
        r = {"client_reset_to_0": ask(c, "item.age", f"{STEAK} 0")}
        r["server_set_age_3.25"] = srv("item.set", f"admin {STEAK} age 3.25")
        time.sleep(SYNC_WAIT)
        r["witness_after_set"] = witness(STEAK, "after server item.set age=3.25")
        r["client_read_after_set"] = ask(c, "item.state", STEAK)
        # updateAge(true): the `true` is the SYNC gate -- it is what makes the server call
        # sendItemStats. If age travelled at all, it would travel here.
        r["server_age_tick"] = srv("item.age.tick", f"admin {STEAK}")
        time.sleep(SYNC_WAIT)
        r["witness_after_tick"] = witness(STEAK, "after server item.age.tick")
        r["client_read_after_tick"] = ask(c, "item.state", STEAK)
        return r

    pb = run_phase("b_server_age_visibility", "server item.set age / age.tick -> client?", phase_b)

    # ---- (c) one accelerated game day ----------------------------------------
    def phase_c():
        r = {"server_reset_age_0": srv("item.set", f"admin {STEAK} age 0"),
             "client_reset_age_0": ask(c, "item.age", f"{STEAK} 0")}
        r["settimespeed_30"] = timespeed(TIME_SPEED)
        r["wait"] = wait_game_hours(24.0, DAY_CAP, "one game day")
        r["settimespeed_1"] = timespeed(1)
        r["server_after"] = srv("item.get", f"admin {STEAK}")
        r["client_after"] = ask(c, "item.state", STEAK)
        r["witness_after"] = witness(STEAK, "after one game day")
        dh = r["wait"]["dWorldHours"]
        rot = num(sub(out["sandbox"], "FoodRotSpeed"), "before")
        r["serverDAge"] = num(r["server_after"], "age")
        r["clientDAge"] = num(r["client_after"], "age")
        # Q2's formula: age += dHours * getFoodRotSpeed() / 24. The sandbox option is an ENUM
        # (3 = 1.0x), so the multiplier is only applied when the enum is the default 3.
        r["expectedDAgeAtRotSpeed1"] = round(dh / 24.0, 4) if dh is not None else None
        r["foodRotSpeedOption"] = rot
        return r

    pc = run_phase("c_accelerated_day", "settimespeed 30, one game day: server vs client age",
                   phase_c)

    # ---- (d) frozen: the x0 age rate -----------------------------------------
    def phase_d():
        r = {"server_reset_age_0": srv("item.set", f"admin {STEAK} age 0")}
        r["freeze"] = srv("item.freeze", f"admin {STEAK}")
        r["before"] = srv("item.get", f"admin {STEAK}")
        r["settimespeed_30"] = timespeed(TIME_SPEED)
        r["wait"] = wait_game_hours(1.0, HOUR_CAP, "one game hour frozen", every=1.0)
        r["settimespeed_1"] = timespeed(1)
        r["after"] = srv("item.get", f"admin {STEAK}")
        a0, a1 = num(r["before"], "age"), num(r["after"], "age")
        f0, f1 = num(r["before"], "freezingTime"), num(r["after"], "freezingTime")
        dh = r["wait"]["dWorldHours"]
        r["dAge"] = round(a1 - a0, 6) if (a0 is not None and a1 is not None) else None
        r["dFreezingTime"] = round(f1 - f0, 3) if (f0 is not None and f1 is not None) else None
        # updateFreezing: freezingTime -= dH / 1.5 * 100 outside a powered freezer (Q2)
        r["expectedDFreezingTime"] = round(-dh / 1.5 * 100.0, 3) if dh is not None else None
        r["expectedDAge"] = 0.0
        return r

    pd = run_phase("d_frozen", "freeze() then one game hour: the x0 age rate", phase_d)

    # ---- (e) the cooking transition without an appliance ----------------------
    # Q4 precondition 4: cookingTime past the threshold + item:update(), with heat > 1.6 and a
    # game minute that differs from lastCookMinute (Food.update runs its cooking block at most
    # once per game minute) -- hence the explicit lastCookMinute reset before each attempt.
    def prime_cook(cooking_time):
        return {"thaw": srv("item.set", f"admin {STEAK} freezingTime 0"),
                "age": srv("item.set", f"admin {STEAK} age 0"),
                "heat": srv("item.set", f"admin {STEAK} heat 2.0"),
                "lastCookMinute": srv("item.set", f"admin {STEAK} lastCookMinute -1"),
                "cookingTime": srv("item.set", f"admin {STEAK} cookingTime {cooking_time}")}

    def phase_e():
        r = {"state_before": srv("item.get", f"admin {STEAK}")}
        mtc = num(r["state_before"], "minutesToCook")
        mtb = num(r["state_before"], "minutesToBurn")
        if mtc is None or mtb is None:
            r["error"] = "minutesToCook/minutesToBurn absent from itemState"
            return r
        r["minutesToCook"], r["minutesToBurn"] = mtc, mtb
        r["cook_prime"] = prime_cook(mtc + 1)
        r["cook_update"] = srv("item.update", f"admin {STEAK}")
        r["cooked"] = r["cook_update"].get("cooked") if isinstance(r["cook_update"], dict) else None
        if r["cooked"] is not True:
            # One retry: the only plausible miss is heat having been slammed to ambient by
            # updateAge's >=20-game-minute branch inside update() itself.
            r["cook_prime_retry"] = prime_cook(mtc + 1)
            r["cook_update_retry"] = srv("item.update", f"admin {STEAK}")
            r["cooked"] = (r["cook_update_retry"].get("cooked")
                           if isinstance(r["cook_update_retry"], dict) else None)
        r["burn_prime"] = {"heat": srv("item.set", f"admin {STEAK} heat 2.0"),
                           "lastCookMinute": srv("item.set", f"admin {STEAK} lastCookMinute -1"),
                           "cookingTime": srv("item.set", f"admin {STEAK} cookingTime {mtb + 1}")}
        r["burn_update"] = srv("item.update", f"admin {STEAK}")
        r["burnt"] = r["burn_update"].get("burnt") if isinstance(r["burn_update"], dict) else None
        r["state_after"] = srv("item.get", f"admin {STEAK}")
        r["witness_after"] = witness(STEAK, "after the cook/burn transitions")
        # Cool the steak once the readings are taken. A burnt item left above the 1.6 heat gate
        # keeps running Food.update's cooking block and firing sendItemStats every game minute,
        # which is a background packet emitter for the rest of the session -- and in the
        # shakedown run (exp02-20260910-025434) phase (g)'s apple came back on the CLIENT with
        # a cookingTime of 71.18 it had never been given on either side, tracking the steak's.
        # Unexplained, so it is removed as a confound rather than reasoned away.
        r["cooldown"] = srv("item.set", f"admin {STEAK} heat 1.0")
        return r

    pe = run_phase("e_cooking", "cookingTime + item:update(): cooked then burnt", phase_e)

    # ---- (f) the evolved-recipe summation -------------------------------------
    # Q5: dish macros = SUM(ing.macro * (1 + cookLvl/15) * share), share = min(|hunger *
    # (1 - 0.03*cookLvl) / ing.hungChange|, 1). Cooking level is the single largest nutrition
    # lever in the game, so each round pins it first and records the route that answered.
    def salad_round(level):
        row = {"level": level, "spawn": spawn(BOWL, *[i["type"] for i in INGREDIENTS])}
        # SERVER first, then the client: a client-only perk write is overwritten by the
        # server's copy inside a second (measured in the shakedown run exp02-20260910-025434,
        # where round 2 asked for Cooking 10, read back 10, and then ran the summation at 0).
        row["perk_server"] = srv("perk.set", f"admin Cooking {level}")
        row["perk_client"] = ask(c, "perk.set", f"Cooking {level}")
        time.sleep(SYNC_WAIT)
        # A second client call is the read-back: its `before` is the level that SURVIVED the
        # wait, which is the number the summation will actually use.
        row["perk_verify"] = ask(c, "perk.set", f"Cooking {level}")
        row["levelHeld"] = (row["perk_verify"].get("before") == level
                            if isinstance(row["perk_verify"], dict) else None)
        args = " ".join(["Salad", BOWL] + [i["type"] for i in INGREDIENTS])
        row["recipe"] = ask(c, "recipe.evolved", args, timeout=30)
        return row

    def phase_f():
        r = {"rounds": []}
        for i, level in enumerate(COOK_LEVELS):
            r["rounds"].append(salad_round(level))
            if i < len(COOK_LEVELS) - 1:
                # A part-used ingredient survives addItem (UseAndSync only fires when the
                # ingredient is spent), and getFirstTypeRecurse would hand the NEXT round that
                # leftover instead of the fresh copy. Eat it: it is a server-spawned item, so
                # the direct Eat path is the same one slice 01 used without server errors.
                # The Bowl and the Salad are deliberately left alone -- the Salad is a
                # client-only item (addItem's Remove/AddItem pair does not leave the client in
                # MP), and eating one would trip the SyncItemFields NPE.
                r.setdefault("flush_between_rounds", []).append(
                    {"afterLevel": level,
                     "eaten": {ing["type"]: ask(c, "eat", f'{ing["type"]} 1.0')
                               for ing in INGREDIENTS}})
        return r

    pf = run_phase("f_evolved_recipe", "Salad = Bowl + Lettuce + Tomato at Cooking 0 and 10",
                   phase_f)

    # ---- (g) MP ownership: which fields the packet carries ---------------------
    def phase_g():
        r = {"spawn": spawn(APPLE)}
        r["witness_baseline"] = witness(APPLE, "baseline")
        r["server_set_calories_999"] = srv("item.set", f"admin {APPLE} calories 999")
        time.sleep(SYNC_WAIT)
        r["witness_after_calories"] = witness(APPLE, "after server calories=999")
        r["client_read_after_calories"] = ask(c, "item.state", APPLE)
        r["server_set_age_3.5"] = srv("item.set", f"admin {APPLE} age 3.5")
        time.sleep(SYNC_WAIT)
        r["witness_after_age"] = witness(APPLE, "after server age=3.5")
        r["client_read_after_age"] = ask(c, "item.state", APPLE)
        cal = num(r["client_read_after_calories"], "calories")
        age = num(r["client_read_after_age"], "age")
        r["caloriesArrived"] = (cal is not None and abs(cal - 999.0) < 0.5)
        r["ageArrived"] = (age is not None and abs(age - 3.5) < 0.001)
        r["clientCalories"], r["clientAge"] = cal, age
        return r

    pg = run_phase("g_mp_ownership", "server item.set calories vs age -> client", phase_g)

    # ---- report-ready summary --------------------------------------------------
    summary = {}
    summary["a_rows"] = [
        {"age": num(row, "age"), "fresh": row.get("fresh") if isinstance(row, dict) else None,
         "rotten": row.get("rotten") if isinstance(row, dict) else None,
         "hungChange": num(row, "hungChange"), "hungerChange": num(row, "hungerChange"),
         "baseHunger": num(row, "baseHunger"),
         "calories": num(row, "calories"), "carbs": num(row, "carbs"),
         "lipids": num(row, "lipids"), "proteins": num(row, "proteins"),
         "thirstChange": num(row, "thirstChange")}
        for row in pa.get("rows", [])]
    summary["b"] = {
        "serverAgeSet": num(pb.get("server_set_age_3.25"), "age"),
        "clientAgeAfterSet": num(pb.get("client_read_after_set"), "age"),
        "serverAgeAfterTick": num(pb.get("server_age_tick"), "age"),
        "clientAgeAfterTick": num(pb.get("client_read_after_tick"), "age"),
        "stateDiffAfterSet": sub(sub(pb.get("witness_after_set"), "result"), "stateDiff"),
        "stateDiffAfterTick": sub(sub(pb.get("witness_after_tick"), "result"), "stateDiff")}
    summary["c"] = {"dWorldHours": sub(pc, "wait").get("dWorldHours"),
                    "reachedTarget": sub(pc, "wait").get("reachedTarget"),
                    "wallSeconds": sub(pc, "wait").get("wallSeconds"),
                    "serverAge": pc.get("serverDAge"), "clientAge": pc.get("clientDAge"),
                    "expectedAtRotSpeed1": pc.get("expectedDAgeAtRotSpeed1")}
    summary["d"] = {k: pd.get(k) for k in ("dAge", "expectedDAge", "dFreezingTime",
                                           "expectedDFreezingTime")}
    summary["d"]["frozenAfter"] = pd.get("after", {}).get("frozen") if isinstance(pd.get("after"), dict) else None
    summary["d"]["dWorldHours"] = sub(pd, "wait").get("dWorldHours")
    summary["e"] = {"minutesToCook": pe.get("minutesToCook"), "minutesToBurn": pe.get("minutesToBurn"),
                    "cooked": pe.get("cooked"), "burnt": pe.get("burnt"),
                    "heatAfter": num(pe.get("state_after"), "heat"),
                    "cookingTimeAfter": num(pe.get("state_after"), "cookingTime"),
                    "hungChangeAfter": num(pe.get("state_after"), "hungChange"),
                    "caloriesAfter": num(pe.get("state_after"), "calories")}
    # (f) the summation, predicted from the ingredients this run actually consumed.
    f_rows = []
    for row in pf.get("rounds", []):
        level = row["level"]
        recipe = row.get("recipe")
        # The level the summation ACTUALLY ran at, not the one that was asked for: `perk.set`
        # can report success and still be overwritten before the recipe call.
        seen = recipe.get("cookingLevel") if isinstance(recipe, dict) else None
        entry = {"level": level, "levelHeld": row.get("levelHeld"),
                 "perkRouteServer": row.get("perk_server", {}).get("route")
                 if isinstance(row.get("perk_server"), dict) else None,
                 "perkRouteClient": row.get("perk_client", {}).get("route")
                 if isinstance(row.get("perk_client"), dict) else None,
                 "cookingLevelSeen": seen,
                 "ingredients": [], "result": None, "predicted": None}
        if isinstance(recipe, dict) and isinstance(recipe.get("ingredients"), list):
            # Predict against the level the recipe SAW, so a failed pin shows up as a matching
            # prediction at the wrong level rather than as a mismatch at the intended one.
            level = seen if isinstance(seen, (int, float)) else level
            entry["predictedAtLevel"] = level
            skill_bonus = 1.0 + level / 15.0
            pred = {"calories": 0.0, "carbs": 0.0, "lipids": 0.0, "proteins": 0.0}
            for ing_row, spec in zip(recipe["ingredients"], INGREDIENTS):
                before = sub(ing_row, "before")
                hung = num(before, "hungChange")
                hunger = spec["use"] / 100.0
                share = None
                if hung not in (None, 0.0):
                    share = min(abs(hunger * (1.0 - 0.03 * level) / hung), 1.0)
                    for k in pred:
                        m = num(before, k)
                        if m is not None:
                            pred[k] += m * skill_bonus * share
                entry["ingredients"].append(
                    {"type": ing_row.get("type"), "use": spec["use"], "share": share,
                     "consumed": ing_row.get("consumed"), "usable": ing_row.get("usable"),
                     "canBeUseCount": ing_row.get("canBeUseCount"),
                     "before": {k: num(before, k) for k in
                                ("hungChange", "calories", "carbs", "lipids", "proteins")},
                     "after": ({k: num(sub(ing_row, "after"), k) for k in
                                ("hungChange", "calories", "carbs", "lipids", "proteins")}
                               if isinstance(ing_row.get("after"), dict) else ing_row.get("after")),
                     "error": ing_row.get("error")})
            res = sub(recipe, "result")
            entry["result"] = {k: num(res, k) for k in
                               ("hungChange", "baseHunger", "calories", "carbs", "lipids",
                                "proteins", "thirstChange")}
            entry["result"]["fullType"] = res.get("fullType")
            entry["predicted"] = {k: round(v, 4) for k, v in pred.items()}
            entry["skillBonus"] = round(skill_bonus, 4)
        elif isinstance(recipe, dict):
            entry["error"] = recipe.get("error")
        else:
            entry["error"] = recipe
        f_rows.append(entry)
    summary["f"] = f_rows
    summary["g"] = {k: pg.get(k) for k in ("caloriesArrived", "ageArrived", "clientCalories",
                                           "clientAge")}
    summary["g"]["serverCalories"] = num(pg.get("server_set_calories_999"), "calories")
    summary["g"]["serverAge"] = num(pg.get("server_set_age_3.5"), "age")
    summary["g"]["stateDiffAfterAge"] = sub(sub(pg.get("witness_after_age"), "result"), "stateDiff")
    out["summary"] = summary
except Exception as e:                   # noqa: BLE001 - a long experiment must keep the phases
    out["error"] = f"{type(e).__name__}: {e}"   # it already has; the traceback is recorded
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
    # Cooking level is a CHARACTER change. The session runs against a copy of the fixture world
    # restored into this run dir, so nothing here can leak into testing/fixtures/ -- but the
    # standing rule is to put back what a probe moved, and phase (f) leaves it at 10.
    try:
        if clients and cooking_before is not None:
            # Both sides, in the same order phase (f) sets them: restoring only the client
            # would leave the server's copy at 10 and the two disagreeing.
            out["cooking_restored"] = {
                "server": ask(server, "perk.set", f"admin Cooking {cooking_before}", timeout=15),
                "client": ask(clients[0], "perk.set", f"Cooking {cooking_before}", timeout=15)}
        else:
            out["cooking_restored"] = f"not restored (before={cooking_before})"
        tl.mark("cooking_restored", to=cooking_before)
    except Exception as e:                       # noqa: BLE001 - teardown path, never raise
        out["cooking_restored"] = f"{type(e).__name__}: {e}"
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        # Case-insensitive by rule (slice 01: a case-sensitive grep produced a false negative
        # in exactly the flattering direction). These four are the lines that would show the
        # server actually running the aging/cooking code under test.
        try:
            log = os.path.join(run_dir, "server-stdout.log")
            hits = {"updateAge": [], "SyncItemFields": [], "EvolvedRecipe": [], "ItemStats": []}
            needles = [(key, key.lower()) for key in hits]
            with open(log, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    low = line.lower()
                    for key, needle in needles:
                        if needle in low and len(hits[key]) < 12:
                            hits[key].append(f"{i}: {line.rstrip()[:220]}")
            out["log_grep"] = hits
        except Exception as e:                   # noqa: BLE001 - teardown path, never raise
            out["log_grep"] = {"error": f"{type(e).__name__}: {e}"}
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:8000])
