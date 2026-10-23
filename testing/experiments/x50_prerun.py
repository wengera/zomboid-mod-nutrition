"""x50_prerun -- the pre-run predictions of Plan 19 Task 7's four hedonics sessions (x501-x504, testing/experiments/
x50_lib.py). x502's is the HEAD server replay (tools/replay_live.ServerReplay, the mod's own adapters on the lupa host,
game_heal on, sleep off, the 90-minute day, Realistic pace with Multiply) of exactly its schedule FROM THE FIRST SIGHT
(CLAUDE.md s5, Plan 15 Task 14b): a fresh record seen at x48_lib.FIRST_SIGHT's age with its HUNGER, THIRST and FATIGUE
and NO typed weight, so the stand-in's first sight lays the mod's own creation body and its seed plate. The others are
the lib's own arithmetic (the jar model of the dish, the dials, the hedonics and nutrients tables), written down here so
the session's predictions are fixed before the boot.

ONE COMMAND re-derives the predictions after a replay or table change:
    python testing/experiments/x50_prerun.py --write          writes testing/experiments/x50_prerun.json
    python testing/experiments/x50_prerun.py --check          exits 1 when the committed file is not the HEAD's
    python testing/experiments/x50_prerun.py                  prints the predictions
x50_lib.preboot refuses a boot whose committed prediction differs from the one re-derived at boot time.

x502's schedule in game minutes at speed 1 (a game minute 3.75 wall s): S, H and W take SEED_AT_M (x48_prerun's: W
waits up to a minute for the store's save); the spawns take SPAWN_M; each plain eat EAT_GAP_M (the eat, its landing,
one writer minute, the read); the relog OFF_M offline (quit, departure, OFFLINE_HOLD_S, relaunch, rejoin: about 90
wall s); then the peanut butter. Each eat's item is the stick as the live one will be: the item pass's whole-stick
calories and macros (NR_ItemPass_Food.txt) times what is left, its hunger -0.24 times what is left, its fraction a
tenth of the whole over what is left (vanilla's baseHunger rescale, #0014). The live run's own replay grades the run;
this file only predicts.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x50_lib as L                                                           # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x48_prerun as P48                                                      # noqa: E402
import replay_live as RL                                                      # noqa: E402

START = L48.FIRST_SIGHT["age"]
SEED_AT_M = P48.SEED_AT_M                # 20: S, H and W at speed 1
SPAWN_M = 2                              # two RCON spawns
EAT_GAP_M = 4                            # an eat (about 8 wall s), its writer minute and the read
OFF_M = 24                               # the relog's absence (about 90 wall s: quit, OFFLINE_HOLD_S, relaunch)
TAIL_M = 6
FIRST_SIGHT_PLAYER = {k: v for k, v in L48.FIRST_SIGHT["player"].items() if k != "weight"}   # no typed weight
ITEM = {L.BUTTER: {"cal": 3155.52, "carb": 0.26, "lip": 356.97, "pro": 3.74, "hunger": -0.24},
        L.PEANUT: {"cal": 2659.9, "carb": 99.23, "lip": 228.45, "pro": 98.79, "hunger": -0.25}}
RING = ("hedonics.f", "hedonics.s", "hedonics.i", "moodLast.u", "lastIntake.plain", "lastIntake.class",
        "lastIntake.allies") + L.SLOTS
NUTRIENTS = os.path.join(L.REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Nutrients.lua")
HEDONICS = os.path.join(L.REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Data_Hedonics.lua")
KEYS = tuple(L.SESSIONS)

r6 = P48.r6
canonical = P48.canonical


def age_of(k):
    return START + (k + 1) / 60.0


def backend():
    p = L.PROFILES[L.PROFILE]
    return RL.ServerReplay(hour_offset=L48.HOUR_OFFSET, rng="half", sleep_allowed=False,
                           stats=dict(L48.FIRST_SIGHT["stats"]), player=dict(FIRST_SIGHT_PLAYER),
                           death_pace=p["pace"], health_combine=p["combine"], day_minutes=L.DAY_MIN, game_heal=True)


def eat_event(k, full, left, whole_frac):
    it = ITEM[full]
    ev = {"minute": k, "kind": "eat", "fullType": full, "cal": it["cal"] * left, "carb": it["carb"] * left,
          "lip": it["lip"] * left, "pro": it["pro"] * left, "hunger": it["hunger"] * left,
          "frac": min(1.0, whole_frac / left)}
    if L.FOOD_TYPE.get(full) is not None:
        ev["foodType"] = L.FOOD_TYPE[full]
    return ev


def schedule():
    k = SEED_AT_M + SPAWN_M
    ev, ks, left = [], [], 1.0
    for _ in range(L.PLAIN_EATS):
        ev.append(eat_event(k, L.BUTTER, left, L.BUTTER_F))
        ks.append(k)
        left -= L.BUTTER_F
        k += EAT_GAP_M
    k_off = k
    k += OFF_M
    k_rel = k + 2
    ev.append(eat_event(k_rel, L.PEANUT, 1.0, L.PEANUT_F))
    return ev, ks, k_off, k_rel, k_rel + TAIL_M


def row_at(rows, k):
    return next(r for r in rows if r["k"] == k)


def snap(r):
    return {"f": r6(r.get("hedonics.f")), "share": r6(r.get("hedonics.share")), "u": r6(r.get("moodLast.u")),
            "s": r6(r.get("hedonics.s")), "i": r.get("hedonics.i"), "plain": r.get("lastIntake.plain"),
            "class": r.get("lastIntake.class"), "allies": r.get("lastIntake.allies")}


def x502():
    ev, ks, k_off, k_rel, end = schedule()
    rows = RL.run(backend(), RL.synthetic_ages(end, start_age=START), ev, list(RING), start_age=START,
                  offline=set(range(k_off + 1, k_off + OFF_M)))
    eats = [snap(row_at(rows, k + 1)) for k in ks]
    before, after = row_at(rows, k_off), row_at(rows, k_off + OFF_M + 1)
    rel0, rel1 = row_at(rows, k_rel - 1), row_at(rows, k_rel + 1)
    return {"minutes": {"eats": ks, "off": k_off, "off_m": OFF_M, "release": k_rel, "end": end},
            "eats": eats,
            "offline": {"before": snap(before), "after": snap(after),
                        "s_moved_h": r6(after.get("hedonics.s") - before.get("hedonics.s"))},
            "release": {"before": snap(rel0), "after": snap(rel1),
                        "u_fall": r6(rel0.get("moodLast.u") - rel1.get("moodLast.u")),
                        "f_fall": r6(rel0.get("hedonics.f") - rel1.get("hedonics.f"))}}


def x501():
    out = {"vanilla_d3": [r6(v) for v in L.VANILLA_D],
           "vanilla_by_level": {str(lv): [r6(v) for v in L.vanilla_dish(L.DISH_ADDS + (L.LATE_ADD, L.RELOG_ADD), lv)]
                                for lv in L.LEVELS},
           "scale": {str(lv): r6(L.prep_scale(lv)) for lv in L.LEVELS}}
    out["stored"] = {str(lv): [r6(v * L.prep_scale(lv)) for v in L.VANILLA_D[:len(L.DISH_ADDS)]] for lv in L.LEVELS}
    out["rename_d10_potato"] = r6(L.VANILLA_D[5] * L.prep_scale(10))
    out["relog_d10_pepper"] = r6(L.VANILLA_D[6] * L.prep_scale(10))
    out["compounded_d10_potato"] = r6((L.VANILLA_D[4] * L.prep_scale(10) - 5) * L.prep_scale(10))
    n = len(L.DISH_ADDS)
    out["counts"] = {"cooks": 3 * n + 4, "prepped": 3 * n + 4, "unprepped": 2 * (n - 1) + 2, "cookFailures": 0}
    return out


def x503():
    u = {L.BUTTER: 20.0, L.LARD: 30.0, L.POTATO: 5.0 + L.STALE_TERM}
    return {"sated_delta": [r6(u[L.BUTTER] * L.ALLIES_EAT_F * k) for k in (1.0, L.UTENSIL_SAD)],
            "hungry_delta": [r6(u[L.BUTTER] * L.ALLIES_EAT_F * L.ALLIES_F * k) for k in (1.0, L.UTENSIL_SAD)],
            "ratio": L.ALLIES_F, "lard_per_frac": [r6(u[L.LARD] * L.ALLIES_F * k) for k in (1.0, L.UTENSIL_SAD)],
            "potato_readtime": u[L.POTATO], "potato_field_after_control": r6(5.0 * (1 - L.POTATO_F / 2)),
            "potato_field_after": r6(5.0 * (1 - L.POTATO_F)),
            "potato_doubled_client": r6(5.0 * (1 - L.POTATO_F) + L.STALE_TERM),
            "counts": {"allies": 3, "restores": 3, "alliesFailures": 0}}


def table_row(path, full, rx):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if f'["{full}"]' in line:
                m = re.search(rx, line)
                return m.group(1) if m else None
    return None


def kcal(full):
    v = table_row(NUTRIENTS, full, r"calories = ([0-9.]+)")
    return None if v is None else float(v)


def klass(full):
    return table_row(HEDONICS, full, r'\{ (?:true|false), "([a-z]+)" \}')


def dish_class(adds):
    """H.dishClass: the class of the ingredient type of most summed kcal (the first on a tie)."""
    tot, order = {}, []
    for t in adds:
        if t not in tot:
            tot[t] = 0.0
            order.append(t)
        tot[t] += kcal(t) or 0.0
    best, top = None, 0.0
    for t in order:
        if tot[t] > top:
            best, top = t, tot[t]
    return {"class": klass(best) if best else None, "by_type": {t: r6(v) for t, v in tot.items()},
            "heaviest_portion_class": klass(max(adds, key=lambda t: kcal(t) or 0.0))}


def dish_eat(adds):
    """DISH_EAT: the dish's stored UnhappyChange at each Cooking level (vanilla's add x prepScale; the session sets
    Cooking to DISH_EAT_LEVEL, 10) and the delta of a whole eat, u x k for k in 1 and 1.25 (#0048)."""
    out = {}
    for lv in range(11):
        u = L.vanilla_dish(adds, lv)[-1] * L.prep_scale(lv)
        out[str(lv)] = {"u": r6(u), "delta": [r6(u * k) for k in (1.0, L.UTENSIL_GLAD)]}
    return out


def x504():
    return {"A": dish_class(L.DISH_A), "B": dish_class(L.DISH_B),
            "dish_eat": {"A": dish_eat(L.DISH_A), "B": dish_eat(L.DISH_B), "unhappy_seed": L.UNHAPPY_SEED},
            "rule6": {"rule_p99": L.RULE_P99, "rule_max": L.RULE_MAX, "x391d_p99_adds": list(L.X391D_P99_ADDS),
                      "x391d_longest": list(L.X391D_LONGEST)}}


FUNCS = {"x501": x501, "x502": x502, "x503": x503, "x504": x504}


def compute(keys=KEYS):
    return {k: FUNCS[k]() for k in keys}


def provenance():
    def say(*a):
        try:
            return subprocess.run(["git"] + list(a), cwd=L.REPO, capture_output=True, text=True).stdout.strip()
        except OSError:
            return None
    return {"first_sight": {"age": START, "stats": L48.FIRST_SIGHT["stats"], "player": FIRST_SIGHT_PLAYER},
            "seed_at_m": SEED_AT_M, "mod_commit": say("log", "-1", "--format=%h", "--", L.MOD_DIR),
            "tool": "tools/replay_live.py ServerReplay (game_heal on, rng half, sleep off, 90-minute day, Realistic, "
                    "Multiply, no typed weight: the mod's creation body)"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    keys = tuple(a.keys) or KEYS
    now = canonical(compute(keys))
    path = os.path.join(L.REPO, L.PRERUN_FILE)
    if a.check:
        have = L.load_prerun(path)
        stale = [k for k in keys if have.get(k) != now[k]]
        if stale:
            print("stale: " + ", ".join(stale) + f" (re-derive with python {L.PRERUN_FILE[:-5]}.py --write)")
            return 1
        print("in sync: " + L.PRERUN_FILE)
        return 0
    if a.write:
        doc = dict(L.load_prerun(path))
        doc.update(now)
        doc["_provenance"] = canonical(provenance())
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print("wrote " + L.PRERUN_FILE)
        return 0
    print(json.dumps(now, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
