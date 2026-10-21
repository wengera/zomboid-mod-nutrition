"""x49b_prerun -- the pre-run prediction of Plan 18 Task 4's x494 (the live acceptance of the symptom layer): the HEAD
server replay (tools/replay_live.ServerReplay, the mod's own adapters on the lupa host, game_heal on, sleep off, the
90-minute day, Realistic pace with Multiply) of exactly the session's schedule FROM THE FIRST SIGHT (CLAUDE.md s5, Plan
15 Task 14b): a fresh record seen at x48_lib.FIRST_SIGHT's age with its HUNGER, THIRST and FATIGUE and NO typed weight,
so the stand-in's first sight lays the mod's own creation body (x48b_prerun's), the seed plate included. The
predictions are the effects in force at each arm's end (the endurance cap, the floors, the added-pain targets, vanilla's
PAIN target and the mid PAIN between writes) and the levels they give, the onset and the release, read off the replay's
own rows (row k: the state drain k left).

ONE COMMAND re-derives the prediction after a replay change:
    python testing/experiments/x49b_prerun.py --write          writes testing/experiments/x49b_prerun.json
    python testing/experiments/x49b_prerun.py --check          exits 1 when the committed file is not the HEAD replay's
    python testing/experiments/x49b_prerun.py                  prints the prediction
x49b_lib.preboot refuses a boot whose committed prediction differs from the replay re-derived at boot time.

The schedule mirrors x494_accept.py in game minutes at speed 1 (a game minute 3.75 wall s; the live phases before the
seed take game time the replay places at SEED_AT_M, x48_prerun's): at SEED_AT_M x484's seed (the meal pool 0, the
unfed clock to the age less STARVE_ONSET_H plus SEED_LEAD_H); ON, then P1 P1_AFTER_M after the onset drain (the progress to
P1_P, the floors seeded the minute after); the thiamine store P1_GM later (beriberi; BERI_POLL_M for its poll); P2
B_GM later (the progress to P2_P, its floors seeded the minute after); the snack P2_GM later; then L1_GM at speed 1 and
L2_GM at SPEED_FAST. The live run's own replay grades it; this file only predicts.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49b_lib as L                                                          # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x48_prerun as P48                                                      # noqa: E402
import replay_live as RL                                                      # noqa: E402

START = L48.FIRST_SIGHT["age"]
SEED_AT_M = P48.SEED_AT_M                # S, H and W at speed 1 (x484: 68 wall s, 18 game minutes)
P1_AFTER_M = 22                          # the onset poll at SPEED_FAST, the speed to 1, ON (~77 s) and the write
SEED_FLOORS_M = 1                        # the floors seeded the minute after the progress write's drain
BERI_POLL_M = 2                          # x48b_prerun's: the thiamine's poll at speed 1 until the grade reads 4
P1_GM = 13                               # P1: the poll, the seeds, ARM_SETTLE_S, P1_S of pairs, the reads (~48 s)
B_GM = 15                                # B after its poll: ARM_SETTLE_S, B_S of pairs, the reads (~57 s)
P2_GM = 14                               # P2: as P1 with P2_S (~53 s)
L1_GM = 5                                # the lapse's poll and L1_S at speed 1
L2_GM = 61                               # L2_S at SPEED_FAST (0.75 wall s a game minute)
KEYS = tuple(L.SESSIONS)
FIRST_SIGHT_PLAYER = {k: v for k, v in L48.FIRST_SIGHT["player"].items() if k != "weight"}   # no typed weight
EFFECTS = ("effects.enduranceCap", "effects.symCap", "effects.rowEndCap", "effects.stressFloor",
           "effects.unhappyFloor", "effects.stressTarget", "effects.unhappyTarget", "effects.pain.7",
           "effects.pain.13", "effects.pain.14", "moodLast.u", "drain.mask", "drain.recovering", "drain.pS",
           "drain.frac.1", "drain.frac.3", "drain.target", "health")


def backend():
    p = L.PROFILES["x49-accept"]
    return RL.ServerReplay(hour_offset=L48.HOUR_OFFSET, rng="half", sleep_allowed=False,
                           stats=dict(L48.FIRST_SIGHT["stats"]), player=dict(FIRST_SIGHT_PLAYER),
                           death_pace=p["pace"], health_combine=p["combine"], day_minutes=L.DAY_MIN, game_heal=True)


def run(events, minutes):
    return RL.run(backend(), RL.synthetic_ages(minutes, start_age=START), events, list(L.RING), start_age=START)


r6 = P48.r6
canonical = P48.canonical


def setp(k, path, value):
    return {"minute": k, "kind": "setpath", "path": path, "value": value}


def stat(k, name, value):
    return {"minute": k, "kind": "stat", "stat": name, "value": value}


def at(rows, k):
    return next(r for r in rows if r["k"] == k)


def levels(r):
    """The levels a row's effects give: Endurance of the cap, Stress and Unhappy of the floors, Pain of the mid PAIN."""
    return {"endurance": L.level_of("endurance", r.get("effects.enduranceCap")),
            "stress": L.level_of("stress", r.get("effects.stressFloor")),
            "unhappy": L.level_of("unhappy", r.get("effects.unhappyFloor")),
            "pain": L.level_of("pain", L.pain_mid(r))}


def snap(r):
    out = {k: (r6(r.get(k)) if isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool) else r.get(k))
           for k in EFFECTS}
    out.update({"painTarget": r6(L.pain_sum(r)), "painMid": r6(L.pain_mid(r)), "levels": levels(r)})
    return out


def schedule():
    """The minutes of x494's acts and the events they make."""
    seed = P48.seed_events(SEED_AT_M)
    k_on = P48.onset_k(run(seed, SEED_AT_M + 30))
    k1 = k_on + P1_AFTER_M
    kb = k1 + P1_GM
    k2 = kb + BERI_POLL_M + B_GM
    kl = k2 + P2_GM
    end = kl + L1_GM + L2_GM
    return {"seed": SEED_AT_M, "onset": k_on, "p1": k1, "thiamine": kb, "p2": k2, "snack": kl, "end": end}, seed


def x494():
    m, seed = schedule()
    probe = run(seed + [setp(m["p1"], "drain.pS", L.P1_P)], m["p1"] + SEED_FLOORS_M + 1)
    f1 = at(probe, m["p1"])
    probe2 = run(seed + [setp(m["p1"], "drain.pS", L.P1_P), setp(m["p2"], "drain.pS", L.P2_P)],
                 m["p2"] + SEED_FLOORS_M + 1)
    f2 = at(probe2, m["p2"])
    ev = seed + [
        setp(m["p1"], "drain.pS", L.P1_P),
        stat(m["p1"] + SEED_FLOORS_M, "STRESS", f1["effects.stressFloor"]),
        stat(m["p1"] + SEED_FLOORS_M, "UNHAPPINESS", f1["effects.unhappyFloor"]),
        setp(m["thiamine"], "nutrients.thiamine.p", L.THIAMINE_P),
        setp(m["p2"], "drain.pS", L.P2_P),
        stat(m["p2"] + SEED_FLOORS_M, "STRESS", f2["effects.stressFloor"]),
        stat(m["p2"] + SEED_FLOORS_M, "UNHAPPINESS", f2["effects.unhappyFloor"]),
        setp(m["snack"], "satiety.M", L.SNACK_M)]
    rows = run(ev, m["end"] + 1)
    on = at(rows, m["onset"])
    lapse = next(r for r in rows if r["k"] >= m["snack"] and not L.has_bit(r.get("drain.mask"), L.MASK_STARVE))
    before = at(rows, lapse["k"] - 1)
    beri = next(r for r in rows if r["k"] >= m["thiamine"] and r.get("nutrients.thiamine.g") == 4)
    ends = {"P1": m["thiamine"] - 1, "B": m["p2"] - 1, "P2": m["snack"] - 1, "L1": m["snack"] + L1_GM,
            "L2": m["end"]}
    return {"minutes": m,
            "seed_age": r6(P48.age_of(m["seed"])),
            "onset_after_seed_h": r6(P48.age_of(m["onset"]) - P48.age_of(m["seed"])),
            "onset": {"painTarget": r6(L.pain_sum(on)), "painMid": r6(L.pain_mid(on)),
                      "window_s": [r6(x) for x in L.onset_window(L.pain_mid(on), "s")],
                      "window_c": [r6(x) for x in L.onset_window(L.pain_mid(on), "c")],
                      "enduranceCap": r6(on.get("effects.enduranceCap"))},
            "floors_seeded": {"P1": [r6(f1["effects.stressFloor"]), r6(f1["effects.unhappyFloor"])],
                              "P2": [r6(f2["effects.stressFloor"]), r6(f2["effects.unhappyFloor"])]},
            "beri_lag_m": beri["k"] - m["thiamine"],
            "arms": {name: snap(at(rows, k)) for name, k in ends.items()},
            "lapse": {"lag_m": lapse["k"] - m["snack"], "mask": lapse.get("drain.mask"),
                      "recovering": lapse.get("drain.recovering"), "pS": r6(lapse.get("drain.pS")),
                      "cap_before": r6(before.get("effects.enduranceCap")),
                      "cap_after": r6(lapse.get("effects.enduranceCap")),
                      "u_before": r6(before.get("moodLast.u")), "u_after": r6(lapse.get("moodLast.u")),
                      "stressFloor_after": r6(lapse.get("effects.stressFloor")),
                      "pain7_after": r6(lapse.get("effects.pain.7")),
                      "pain13_after": r6(lapse.get("effects.pain.13"))},
            "end": {"health": r6(rows[-1].get("health")), "target": r6(rows[-1].get("drain.target")),
                    "frac1": r6(rows[-1].get(L.F1)), "frac3": r6(rows[-1].get(L.F3))}}


FUNCS = {"x494": x494}


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
