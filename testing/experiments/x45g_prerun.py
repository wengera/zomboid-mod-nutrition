"""x45g_prerun -- the pre-run predictions of x452-x457 (Plan 15 Task 11; review H1, the controller's ruling after Task
6c): the HEAD server replay (tools/replay_live.ServerReplay, the mod's own adapters on the lupa host, sleep off, the
responder constant at its middle) of exactly each live schedule, from a fresh record seen at world age START_AGE (the
fixture's first sight, x446's first ring row at 3.217 after 12 drains), the default body, HUNGER 0.2 at the start (the
fixture's, x446's stats.all). Run before any boot; its printed JSON is what the drivers' PRED and x45g_lib's cadence
bands carry. `python testing/experiments/x45g_prerun.py [x452 ...]`.

What the replay carries and what it does not: HUNGER, THIRST, the record (the meal pool, the stomach, the fluids, the
drain flags and clocks) and the applied basal scale; not health, the moodles' own levels or the severe-moodle constant,
whose predictions are the kernel arithmetic the drivers name (K.drain rates and floors, red x M_H).

Each schedule mirrors its driver: x452's meals at minutes 330, 690 and 1470 from 07:00 (lunch, dinner, breakfast; a
can and a banana each, x45g_lib.FOODS) and 0.5 L of water 150 minutes after each (x45g_lib.DRINK_L, DRINK_AFTER_H);
x453's seed at age SET_AGE to 960 g with 2000 kcal, then a Broccoli every 3 game minutes (an eat of about 3 wall s and
the 1.5-minute settle at the 0.2 multiplier) until the stomach reads Overfull 4; x454 and x455's satiety.M 0 and
drain.fedAgeH at SET_AGE; x454's can 6.6 game hours after the onset (B's drain and hold); x456's deficit set to 3.80 % at
SET_AGE; x457's four arms of 3.05 game hours (the settle and the window) from SET_AGE.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x45g_lib as L                                                          # noqa: E402
import replay_live as RL                                                      # noqa: E402

START_AGE = 3.0
SET_AGE = 4.2                    # about X's or A's start after S, H and (x452) W
STEP_M = 1.0


def backend():
    return RL.ServerReplay(hour_offset=L.HOUR_OFFSET, rng="half", sleep_allowed=False)


def k_of(age):
    """The step whose drain ends at or just after `age` (synthetic_ages: step k ends at START_AGE + (k + 1) / 60)."""
    return max(0, int(round((age - START_AGE) * 60.0)) - 1)


def eat(full, k, label=None):
    e = L.mod_eat_event(full, None, label)
    e.pop("s")
    e["minute"] = k
    return e


def run(events, minutes, paths, be=None):
    be = be or backend()
    ev = sorted((e for e in events if e["minute"] < minutes), key=lambda e: e["minute"])
    rows = RL.run(be, RL.synthetic_ages(minutes, start_age=START_AGE), ev, list(paths), start_age=START_AGE)
    return rows, be


def first(rows, a0, a1, fn):
    for r in rows:
        if a0 < r["age"] <= a1 and fn(r):
            return r
    return None


X452_MEALS = {"lunch": 330, "dinner": 690, "breakfast": 1470}


def x452_events():
    """x452's events as the driver lands them (re-review R1): the can EAT_CAN_GM and the banana EAT_BAN_GM game minutes
    after each meal's planned minute (x446's eat, x45g_lib), the water DRINK_AFTER_H after the planned minute."""
    ev = []
    for name, m in X452_MEALS.items():
        ev += [eat(L.BOLOGNESE, k_of((m + L.EAT_CAN_GM) / 60.0), name),
               eat(L.BANANA, k_of((m + L.EAT_BAN_GM) / 60.0), name)]
        ev.append({"minute": k_of((m + L.DRINK_AFTER_H * 60.0) / 60.0), "kind": "drink", "fluid": L.DRINK_FLUID,
                   "litres": L.DRINK_L, "label": name + "-drink"})
    return ev


def x452():
    meals = X452_MEALS
    ev = x452_events()
    end = (meals["breakfast"] + 300) / 60.0
    rows, _ = run(ev, k_of(end) + 2, ("satiety.M", "fluids.dehydPct", "drain.dehydrated") + L.STOMACH_PATHS)
    out = {"meals": {}, "schedule_minutes": meals, "drink_after_min": 150, "start_age": START_AGE,
           "eat_can_gm": L.EAT_CAN_GM, "eat_ban_gm": L.EAT_BAN_GM}
    names = list(meals)
    for i, name in enumerate(names):
        k = k_of((meals[name] + L.EAT_BAN_GM) / 60.0)        # the banana's minute: grade_x452 measures from it
        a0 = START_AGE + (k + 1) / 60.0
        a1 = meals[names[i + 1]] / 60.0 if i + 1 < len(names) else end
        h = [rows[j]["HUNGER"] for j in range(k, k + L.EAT0_ROWS)]
        pk = first(rows, a0, a1, lambda r: r["HUNGER"] > L.HUNGRY_AT[0])
        hu = first(rows, a0, a1, lambda r: r["HUNGER"] > L.HUNGRY_AT[1])
        wf = first(rows, a0, a1, lambda r: r["satiety.M"] < L.WELL_FED_M)
        out["meals"][name] = {"eat0_max": max(h), "peckish_h": None if pk is None else round(pk["age"] - a0, 3),
                              "hungry_h": None if hu is None else round(hu["age"] - a0, 3),
                              "well_fed_h": None if wf is None else round(wf["age"] - a0, 3),
                              "window_h": round(a1 - a0, 3)}
    out["max_dehydPct"] = round(max(r["fluids.dehydPct"] for r in rows), 3)
    out["dehydrated_rows"] = sum(1 for r in rows if r.get("drain.dehydrated") is True)
    out["max_THIRST"] = round(max(r["THIRST"] for r in rows), 4)
    out["start_dehydPct"] = round(rows[0]["fluids.dehydPct"], 4)
    masses = [L.stomach_mass(r) for r in rows]
    out["max_stomach_g"] = max(m for m in masses if m is not None)
    out["max_overfull"] = L.overfull_level(out["max_stomach_g"])
    return out


def x453():
    be = backend()
    k0 = k_of(SET_AGE)
    rows, be = run([], k0 + 1, L.STOMACH_PATHS, be)
    v = rows[-1]
    m0 = L.stomach_mass(v)
    ev = [{"minute": k0 + 1, "kind": "setpath", "path": "stomach.buffer.water",
           "value": v["stomach.buffer.water"] + (L.SEED_G - m0)},
          {"minute": k0 + 1, "kind": "setpath", "path": "stomach.buffer.calories", "value": L.SEED_KCAL}]
    eats, k, level = 0, k0 + 2, 0
    rows2 = []
    be2 = backend()
    while level < 4 and eats <= L.MAX_EATS:
        ev2 = ev + [eat(L.BROCCOLI, k0 + 2 + 3 * i) for i in range(eats)]
        rows2, _ = run(ev2, k0 + 3 + 3 * eats + 2, L.STOMACH_PATHS, backend())
        level = L.overfull_level(L.stomach_mass(rows2[-1]))
        if level < 4:
            eats += 1
    _ = (k, be2)
    return {"eats_to_overfull4": eats, "seed_mass_g": L.stomach_mass(rows2[k0 + 1]) if len(rows2) > k0 + 1 else None,
            "final_mass_g": L.stomach_mass(rows2[-1]), "eat_every_gm": 3}


def starve(can_after_h=None):
    k0 = k_of(SET_AGE)
    a = START_AGE + (k0 + 1) / 60.0
    ev = [{"minute": k0, "kind": "setpath", "path": "satiety.M", "value": 0.0},
          {"minute": k0, "kind": "setpath", "path": "drain.fedAgeH", "value": a - L.STARVE_ONSET_H + L.ONSET_LEAD_H}]
    end = a + L.ONSET_LEAD_H + 0.5
    if can_after_h is not None:
        kc = k_of(a + L.ONSET_LEAD_H + can_after_h)
        ev.append(eat(L.BOLOGNESE, kc, "recover"))
        end = a + L.ONSET_LEAD_H + can_after_h + 0.5
    rows, _ = run(ev, k_of(end), ("satiety.M", "drain.fedAgeH", "drain.starveAcute", "drain.starving",
                                  "drain.targetFloor", "drain.rate", "drain.active"))
    on = first(rows, a, end, lambda r: r.get("drain.starveAcute") is True)
    pre = [r["HUNGER"] for r in rows if a < r["age"] < (on["age"] if on else end)]
    out = {"set_age": round(a, 4), "onset_age": None if on is None else round(on["age"], 4),
           "onset_unfed_h": None if on is None else round(on["age"] - on["drain.fedAgeH"], 4),
           "hunger_pre_max": round(max(pre), 4) if pre else None,
           "hunger_at_onset": None if on is None else round(on["HUNGER"], 4),
           "floor_at_onset": None if on is None else on["drain.targetFloor"],
           "rate_at_onset": None if on is None else on["drain.rate"]}
    if can_after_h is not None and on is not None:
        ac = START_AGE + (k_of(a + L.ONSET_LEAD_H + can_after_h) + 1) / 60.0
        off = first(rows, ac - 1e-9, end, lambda r: r.get("drain.starveAcute") is False)
        out.update({"can_age": round(ac, 4), "off_after_gm": None if off is None else round((off["age"] - ac) * 60, 2),
                    "hunger_after_can": None if off is None else round(off["HUNGER"], 4),
                    "M_after_can": None if off is None else round(off["satiety.M"], 1)})
    return out


def x456():
    k0 = k_of(SET_AGE)
    paths = ("fluids.water", "fluids.dehydPct", "drain.dehydrated", "drain.targetFloor", "body.fm", "body.lm",
             "body.lx", "fluids.thirstTarget")
    rows0, _ = run([], k0 + 1, paths)
    v = rows0[-1]
    w = v["body.fm"] + v["body.lm"] + v["body.lx"]
    water = v["fluids.water"] - (L.DEHYD_SEED_PCT - v["fluids.dehydPct"]) * 10.0 * w
    ev = [{"minute": k0 + 1, "kind": "setpath", "path": "fluids.water", "value": water}]
    end = SET_AGE + 12.0
    rows, _ = run(ev, k_of(end), paths)
    a = START_AGE + (k0 + 2) / 60.0
    on = first(rows, a, end, lambda r: r.get("drain.dehydrated") is True)
    after = [r for r in rows if a + 2 / 60.0 < r["age"] <= end]
    pct = L.fit_slope([(r["age"], r["fluids.dehydPct"]) for r in after])
    loss = -L.fit_slope([(r["age"], r["fluids.water"]) for r in after])
    pre = [r["THIRST"] for r in rows if a < r["age"] < (on["age"] if on else end)]
    floor_reach = None
    if on is not None:
        h, t = 100.0, on["age"]
        for r in rows:
            if r["age"] <= on["age"]:
                continue
            h -= L.DEHYD_RATE / 1440.0 * (r["age"] - t) * 60.0
            t = r["age"]
            if h <= r["drain.targetFloor"]:
                floor_reach = (r["age"], r["drain.targetFloor"])
                break
    out = {"w": round(w, 3), "lm": v["body.lm"], "set_pct": L.DEHYD_SEED_PCT,
           "onset_age": None if on is None else round(on["age"], 4),
           "onset_pct": None if on is None else round(on["fluids.dehydPct"], 4),
           "thirst_at_onset": None if on is None else round(on["THIRST"], 4),
           "thirst_pre_max": round(max(pre), 4) if pre else None,
           "pct_per_gh": round(pct, 6), "loss_g_per_gh": round(loss, 3),
           "basal_pred_g_per_gh": round(L.basal_g_day(v["body.lm"]) / 24.0, 3)}
    if floor_reach is not None:
        drain_h = floor_reach[0] - on["age"]
        p = L.dehyd_pace(w, v["body.lm"], pct, drain_h, floor_reach[1], 100.0)
        out.update({"drain_h_to_floor": round(drain_h, 3), "floor_at_reach": round(floor_reach[1], 3),
                    "live_h_from_replay": round(p["live_h"], 3), "kernel_h": round(p["kernel_h"], 3)})
    return out


def x457():
    arms = (("BASE", None), ("HIGH", ("HIGH_THIRST", True)), ("OFF", ("HIGH_THIRST", False)),
            ("LOW", ("LOW_THIRST", True)))
    span = L.WIN_GH + L.ARM_SETTLE_GM / 60.0
    ev, bounds = [], {}
    for i, (name, ch) in enumerate(arms):
        a0 = SET_AGE + i * span
        if ch is not None:
            ev.append({"minute": k_of(a0), "kind": "trait", "trait": ch[0], "on": ch[1]})
        bounds[name] = (a0 + L.ARM_SETTLE_GM / 60.0, a0 + span)
    end = SET_AGE + len(arms) * span + 0.1
    be = backend()
    # the golden host's CharacterTrait carries no thirst traits (testing/tests/kernel/golden_trace.py): the two are
    # added here, on this replay's host only, as the live CharacterTrait has them
    be.rt.execute('CharacterTrait.HIGH_THIRST = "trait:HIGH_THIRST"; CharacterTrait.LOW_THIRST = "trait:LOW_THIRST"')
    rows, _ = run(ev, k_of(end), ("fluids.water", "body.lm", L.SCALE_G), be)
    out = {}
    for name, (s, e) in bounds.items():
        rs = [r for r in rows if s < r["age"] <= e]
        out[name] = {"scale": rs[len(rs) // 2].get(L.SCALE_G),
                     "loss_g_per_gh": round(-L.fit_slope([(r["age"], r["fluids.water"]) for r in rs]), 3)}
    base = out["BASE"]["loss_g_per_gh"]
    for name in ("HIGH", "OFF", "LOW"):
        out[name]["ratio"] = round(out[name]["loss_g_per_gh"] / base, 4)
    out["lm"] = rows[0]["body.lm"]
    return out


def main(argv):
    want = argv or ["x452", "x453", "x454", "x455", "x456", "x457"]
    res = {}
    for k in want:
        if k == "x452":
            res[k] = x452()
        elif k == "x453":
            res[k] = x453()
        elif k == "x454":
            res[k] = starve(can_after_h=6.6)
        elif k == "x455":
            res[k] = starve()
        elif k == "x456":
            res[k] = x456()
        elif k == "x457":
            res[k] = x457()
    print(json.dumps(res, indent=1, sort_keys=True, default=str))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
    _ = math
