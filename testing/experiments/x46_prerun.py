"""x46_prerun -- the pre-run predictions of Plan 16 Task 9's sessions (x461a, x461b, x464, x465, x466, x467): the HEAD
server replay (tools/replay_live.ServerReplay, the mod's own adapters on the lupa host, the responder constant at its
middle) of exactly each session's schedule FROM THE FIRST SIGHT (CLAUDE.md s5, Plan 15 Task 14b): a fresh record seen at
x46_lib.FIRST_SIGHT's age with its HUNGER, THIRST and FATIGUE, so the seed plate the live fresh record lands is in the
replay too. Whole drinks are spread over their action's span at the profile's DayLength 1 and speed 1
(replay_live.spread_drinks, Plan 16 Task 7). x462, x463a and x463b predict equalities, not replayed numbers.

ONE COMMAND re-derives every prediction after a replay change (Task 7's fix round included):
    python testing/experiments/x46_prerun.py --write          writes testing/experiments/x46_prerun.json
    python testing/experiments/x46_prerun.py --check          exits 1 when the committed file is not the HEAD replay's
    python testing/experiments/x46_prerun.py [x461a ...]      prints the named sessions' predictions
The drivers read their bands from x46_prerun.json (x46_lib.PRERUN) and x46_lib.preboot refuses a boot whose session's
committed predictions differ from the replay re-derived at boot time.

The schedules (each mirrors its driver; the live phases before the first scheduled act take game time the replay
places at the act's own trigger, never at a guessed wall time):
  x461a  the seed plate empties (the first step whose stomach reads under EMPTY_G is the plate's start); the plate's
         four eats land PLATE_LAND_GM game minutes after it, the 0.5 L of Water starts at WATER_AT_GM and is spread.
  x461b  from the same start: 0.5 L of Water (spread), WATCH_M game minutes after the drink's span, 0.5 L of CowMilk
         (spread at MILK_MAX_TIME), WATCH_M after its span the run to the request (HUNGER over H_REQ), TKX.MilkSolid
         landing EAT_SOLID_GM after it.
  x464   sleep on: the nap from NAP_AT_H after the first sight, NAP_H asleep, AWAKE_H awake, the full sleep FULL_H, AWAKE_H.
  x465   sleep on: NIGHT_AT_H after the first sight, a night of NIGHT_H asleep stepped at NIGHT_DTM game minutes a step
         (x447's live fast-forward cadence, 3.2), one step of STALL_M (a stall past K.resume.STEP_M, so the carry runs),
         POST_H awake.
  x466   the stomach seeded at SEED_AT_H (calories first, then water to SEED_G): the game minutes it stays at Overfull 4.
  x467   x452's day (x45g_prerun's x452 events) from the first sight: the meals at minutes 330, 690 and 1470 from 07:00,
         the can and the banana EAT_CAN_GM and EAT_BAN_GM after each, 0.5 L of Water 150 minutes after each (spread).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x46_lib as L                                                           # noqa: E402
import x45g_lib as G                                                          # noqa: E402
import replay_live as RL                                                      # noqa: E402

START = L.FIRST_SIGHT["age"]
DAY_LENGTH = 1
EAT_SOLID_GM = 9
NAP_AT_H = 0.75                          # S, H (about 0.5 game h at speed 1) and TR (0.25)
NIGHT_AT_H = 0.7                         # S, H and PRE (0.2)
NIGHT_DTM = 3.2
STALL_M = 75.0
SEED_AT_H = 0.65                         # S, H and F before SEED
X467_MEALS = {"lunch": 330, "dinner": 690, "breakfast": 1470}
KEYS = L.PRERUN_KEYS


def backend(sleep=False):
    return RL.ServerReplay(hour_offset=L.HOUR_OFFSET, rng="half", sleep_allowed=sleep,
                           stats=dict(L.FIRST_SIGHT["stats"]))


def k_of(age):
    """The step whose drain ends at or just after `age` (step k ends at START + (k + 1) / 60)."""
    return max(0, int(round((age - START) * 60.0)) - 1)


def age_of(k):
    return START + (k + 1) / 60.0


def eat(full, k, label=None):
    e = L.eat_event(full, None, label)
    e.pop("s")
    e["minute"] = k
    return e


def drink(fluid, litres, k, label, max_time=None):
    e = {"minute": k, "kind": "drink", "fluid": fluid, "litres": litres, "label": label, "whole": True}
    if max_time is not None:
        e["maxTime"] = max_time
    return e


def run(events, minutes, paths, sleep=False, ages=None):
    ages = ages if ages is not None else RL.synthetic_ages(minutes, start_age=START)
    evs, spread = RL.spread_drinks(events, ages, start_age=START, day_length=DAY_LENGTH, speed=1.0)
    rows = RL.run(backend(sleep), ages, evs, list(paths), start_age=START)
    return rows, spread


def first_row(rows, a0, fn, a1=None):
    for r in rows:
        if r["age"] > a0 and (a1 is None or r["age"] <= a1) and fn(r):
            return r
    return None


def r6(x):
    return None if x is None else round(float(x), 6)


def span_m(fluid, litres, max_time=None):
    e = {"kind": "drink", "fluid": fluid, "litres": litres, "whole": True}
    if max_time is not None:
        e["maxTime"] = max_time
    return RL.drink_span_h(e, DAY_LENGTH, 1.0) * 60.0


def seed_kcal():
    """The first sight's seed plate (W.seedPlate's kcal, the writer's lastSeedKcal)."""
    be = backend()
    RL.run(be, RL.synthetic_ages(2, start_age=START), [], ("satiety.M",), start_age=START)
    v = be.NR.server.writer.lastSeedKcal
    return None if v is None else float(v)


def empty_step(paths=()):
    """The first step whose stomach reads under EMPTY_G after the first sight's seed plate."""
    rows, _ = run([], int(L.EMPTY_CAP_H * 60) + 120, tuple(G.STOMACH_PATHS) + tuple(paths))
    r = first_row(rows, START + 0.5, lambda x: L.mass_of(x) < L.EMPTY_G)
    if r is None:
        raise RuntimeError("the seed plate never empties under EMPTY_G inside the cap")
    return r["k"], rows


def x461a():
    k0, rows0 = empty_step()
    e0 = k0 + 1
    ev = [eat(full, e0 + gm, "plate") for full, gm in zip(L.PLATE, L.PLATE_LAND_GM)]
    ev.append(drink(L.WATER, L.DRINK_L, e0 + L.WATER_AT_GM, "plate-water"))
    end = e0 + int((L.PLATE_WATCH_H + L.TAIL_H) * 60) + L.WATER_AT_GM + 30
    rows, spread = run(ev, end, tuple(G.STOMACH_PATHS) + ("stomachFill", "satiety.M"))
    a0 = rows[e0 + L.PLATE_LAND_GM[0]]["age"]
    of = L.overfull_minutes(rows, a0)
    return {"seed_kcal": r6(seed_kcal()), "empty_age": r6(age_of(k0)), "plate_start_age": r6(age_of(e0)),
            "of_m3": r6(of["m3"]), "of_m4": r6(of["m4"]), "of_peak": r6(of["peak"]),
            "water_span_m": r6(span_m(L.WATER, L.DRINK_L)), "spread": spread}


def x461b():
    k0, _ = empty_step()
    e0 = k0 + 1
    ws = span_m(L.WATER, L.DRINK_L)
    ms = span_m(L.COWMILK, L.DRINK_L, L.MILK_MAX_TIME)
    km = e0 + int(round(ws + 2 + L.WATCH_M))
    ks = km + int(round(ms + 2 + L.WATCH_M))
    ev = [drink(L.WATER, L.DRINK_L, e0, "WA"), drink(L.COWMILK, L.DRINK_L, km, "MI", L.MILK_MAX_TIME)]
    paths = tuple(G.STOMACH_PATHS) + ("stomachFill", "satiety.M")
    rows, _ = run(ev, ks + int(L.REQ_CAP_H * 60), paths)
    req = first_row(rows, age_of(ks), lambda r: r["HUNGER"] >= L.H_REQ)
    if req is None:
        raise RuntimeError("no request inside the cap after the milk")
    kr = req["k"] + EAT_SOLID_GM
    ev.append(eat(L.MILKSOLID, kr, "SO"))
    rows, spread = run(ev, kr + int(L.WATCH_M) + 30, paths)
    w = L.liquid_course(rows, age_of(e0) - 1e-9, age_of(km) - 1e-9)
    m = L.liquid_course(rows, age_of(km) - 1e-9, age_of(ks))
    return {"start_age": r6(age_of(e0)), "milk_age": r6(age_of(km)), "so_age": r6(age_of(ks)),
            "w_peak": r6(w["peak"]), "w_half_m": r6(w["half_m"]), "m_peak": r6(m["peak"]),
            "request_h_after_so": r6(req["age"] - age_of(ks)), "water_span_m": r6(ws), "milk_span_m": r6(ms),
            "spread": spread}


def sleep_events(k_on, k_off, label):
    return [{"minute": k_on, "kind": "sleep", "asleep": True, "label": label},
            {"minute": k_off, "kind": "sleep", "asleep": False, "label": label}]


def x464():
    kn = k_of(START + NAP_AT_H)
    kn1 = kn + int(L.NAP_H * 60)
    kf = kn1 + int(L.AWAKE_H * 60)
    kf1 = kf + int(L.FULL_H * 60)
    end = kf1 + int(L.AWAKE_H * 60) + 2
    ev = sleep_events(kn, kn1, "nap") + sleep_events(kf, kf1, "full")
    rows, _ = run(ev, end, L.CLOCK_RING, sleep=True)
    a_n, a_f = age_of(kn) - 1e-9, age_of(kf) - 1e-9
    nap = L.bout_close(rows, a_n, age_of(kf - 1))
    full = L.bout_close(rows, a_f, age_of(end - 1))
    t = rows[k_of(START + 0.3)]
    nc, fc = nap["close"], full["close"]
    wake = full["last_asleep"]["age"]
    return {"seed_off_h": r6(L.wrapdiff(t["acute.bodyHour"], L.world_hour(t["age"]))),
            "nap_bout_h": r6(nap["bout_h"]), "full_bout_h": r6(full["bout_h"]),
            "nap_close_off_h": r6(L.wrapdiff(nc["acute.bodyHour"], L.world_hour(nc["age"]))),
            "full_close_body": r6(fc["acute.bodyHour"]),
            "full_close_reset_off_h": r6(L.wrapdiff(fc["acute.bodyHour"], L.WAKE_H + (fc["age"] - wake))),
            "full_close_world_off_h": r6(L.wrapdiff(fc["acute.bodyHour"], L.world_hour(fc["age"])))}


def x465():
    k0 = k_of(START + NIGHT_AT_H)
    ages = RL.synthetic_ages(k0 + 1, start_age=START)
    a = ages[-1]
    n = int(L.NIGHT_H * 60 / NIGHT_DTM)
    for i in range(n):
        a += (STALL_M if i == n // 2 else NIGHT_DTM) / 60.0
        ages.append(a)
    k1 = len(ages) - 1
    for _ in range(int(L.POST_H * 60)):
        a += 1.0 / 60.0
        ages.append(a)
    ev = sleep_events(k0, k1, "night")
    rows, _ = run(ev, None, L.NIGHT_RING, sleep=True, ages=ages)
    book = L.night_booking(rows, ages[k0 - 1] - 1e-9, ages[-1], lag=0)
    last = rows[-1]
    return {"booked_h": r6(book["booked_h"]), "asleep_h": r6(book["asleep_h"]),
            "miss_h": r6(abs(book["booked_h"] - book["asleep_h"])), "stalls": book["stalls"],
            "substeps": book["substeps"], "lag_gm": r6((last["age"] - last["lastSeen"]) * 60.0),
            "night_dtm": NIGHT_DTM, "stall_m": STALL_M}


def x466():
    k0 = k_of(START + SEED_AT_H)
    paths = tuple(G.STOMACH_PATHS)
    rows, _ = run([], k0 + 1, paths)
    v = rows[-1]
    m0 = L.mass_of(v)
    ev = [{"minute": k0 + 1, "kind": "setpath", "path": "stomach.buffer.calories",
           "value": max(v["stomach.buffer.calories"], L.SEED_KCAL)},
          {"minute": k0 + 1, "kind": "setpath", "path": "stomach.buffer.water",
           "value": v["stomach.buffer.water"] + (L.SEED_G - m0)}]
    rows, _ = run(ev, k0 + 120, paths)
    after = [r for r in rows if r["k"] > k0]
    lv = [G.overfull_level(L.mass_of(r)) for r in after]
    m4 = 0
    for x in lv:
        if x < 4:
            break
        m4 += 1
    return {"seed_age": r6(age_of(k0 + 1)), "seed_level": lv[0], "level4_minutes": m4,
            "mass_after_seed": r6(L.mass_of(after[0]))}


def x467():
    ev = []
    for name, m in X467_MEALS.items():
        ev += [eat(G.BOLOGNESE, k_of((m + G.EAT_CAN_GM) / 60.0), name),
               eat(G.BANANA, k_of((m + G.EAT_BAN_GM) / 60.0), name)]
        ev.append(drink(G.DRINK_FLUID, G.DRINK_L, k_of((m + G.DRINK_AFTER_H * 60.0) / 60.0), name + "-drink"))
    end = (X467_MEALS["breakfast"] + 300) / 60.0
    rows, spread = run(ev, k_of(end) + 2, ("satiety.M", "fluids.dehydPct", "drain.dehydrated") + G.STOMACH_PATHS)
    out = {"cad_p": {}, "meals": {}}
    names = list(X467_MEALS)
    for i, name in enumerate(names):
        k = k_of((X467_MEALS[name] + G.EAT_BAN_GM) / 60.0)
        a0 = age_of(k)
        a1 = X467_MEALS[names[i + 1]] / 60.0 if i + 1 < len(names) else end
        h = [rows[j]["HUNGER"] for j in range(k, k + G.EAT0_ROWS)]
        pk = first_row(rows, a0, lambda r: r["HUNGER"] > G.HUNGRY_AT[0], a1)
        hu = first_row(rows, a0, lambda r: r["HUNGER"] > G.HUNGRY_AT[1], a1)
        wf = first_row(rows, a0, lambda r: r["satiety.M"] < G.WELL_FED_M, a1)
        out["cad_p"][name] = None if pk is None else round(pk["age"] - a0, 3)
        out["meals"][name] = {"eat0_max": r6(max(h)), "hungry_h": None if hu is None else round(hu["age"] - a0, 3),
                              "well_fed_h": None if wf is None else round(wf["age"] - a0, 3),
                              "window_h": round(a1 - a0, 3)}
    out["cad_h"] = out["meals"]["dinner"]["hungry_h"]
    out["max_dehydPct"] = r6(max(r["fluids.dehydPct"] for r in rows))
    out["dehydrated_rows"] = sum(1 for r in rows if r.get("drain.dehydrated") is True)
    out["max_THIRST"] = r6(max(r["THIRST"] for r in rows))
    out["max_stomach_g"] = r6(max(L.mass_of(r) for r in rows))
    out["seed_kcal"] = r6(seed_kcal())
    out["M_first_row"] = r6(rows[0]["satiety.M"])
    out["spread"] = spread
    return out


FNS = {"x461a": x461a, "x461b": x461b, "x464": x464, "x465": x465, "x466": x466, "x467": x467}


def compute(keys=KEYS):
    return {k: FNS[k]() for k in keys}


def provenance():
    def last(path):
        try:
            return subprocess.run(["git", "log", "-1", "--format=%h", "--", path], cwd=L.REPO, capture_output=True,
                                  text=True).stdout.strip() or None
        except OSError:
            return None
    return {"first_sight": L.FIRST_SIGHT, "tool": "tools/replay_live.py ServerReplay, rng half",
            "mod_commit": last(L.MOD_DIR), "replay_tool_commit": last("tools/replay_live.py"),
            "replay_tool_dirty": subprocess.run(["git", "diff", "--quiet", "--", "tools/replay_live.py"],
                                                cwd=L.REPO).returncode != 0}


def canonical(res):
    return json.loads(json.dumps(res, sort_keys=True, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    keys = a.keys or list(KEYS)
    res = canonical(compute(keys))
    path = os.path.join(L.REPO, L.PRERUN_FILE)
    if a.write:
        doc = L.load_prerun(path) if a.keys else {}
        doc.update(res)
        doc["_provenance"] = provenance()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(f"wrote {L.PRERUN_FILE}: {sorted(k for k in doc if not k.startswith('_'))}")
        return 0
    if a.check:
        have = L.load_prerun(path)
        bad = [k for k in keys if have.get(k) != res[k]]
        print(json.dumps({"stale": bad}, indent=1))
        return 1 if bad else 0
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
