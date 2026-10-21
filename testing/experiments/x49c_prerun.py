"""x49c_prerun -- the pre-run prediction of Plan 18 Task 4's x495 (the release after a snack): the HEAD server replay
(x49b_prerun's backend: ServerReplay from x48_lib.FIRST_SIGHT, no typed weight, game_heal on, sleep off, the 90-minute
day, Realistic, Multiply) of x495's schedule in game minutes at speed 1: at SEED_AT_M x484's seed; the progress to P1_P
P1_AFTER_M after the onset drain and its floors seeded the minute after; the thiamine store P1_SEED_GM later; the snack
BERI_POLL_M + PRE_GM after it; then L1_GM at speed 1 and L2_GM at SPEED_FAST. The predictions are the effects at the
pre-lapse arm's end, the lapse and the effects, health and target at the end, read off the replay's rows.

    python testing/experiments/x49c_prerun.py --write | --check | (print)
x49c_lib.preboot refuses a boot whose committed prediction differs from the replay re-derived at boot time.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x49c_lib as L                                                          # noqa: E402
import x49b_lib as B                                                          # noqa: E402
import x49b_prerun as PB                                                      # noqa: E402
import x48_prerun as P48                                                      # noqa: E402

SEED_AT_M = P48.SEED_AT_M
P1_AFTER_M = 2                           # the onset poll at SPEED_FAST, the speed to 1 and the progress write
SEED_FLOORS_M = PB.SEED_FLOORS_M
P1_SEED_GM = 6                           # the seed's poll, the floors' reads and the two setany (about 23 s)
BERI_POLL_M = PB.BERI_POLL_M
PRE_GM = 28                              # ARM_SETTLE_S, PRE_S of pairs, the reads (about 106 s)
L1_GM = 6                                # the lapse's poll and L1_S at speed 1
L2_GM = int(round(L.L2_GM))              # L2_S at SPEED_FAST
KEYS = tuple(L.SESSIONS)

r6 = P48.r6
canonical = P48.canonical
setp, stat, at, snap = PB.setp, PB.stat, PB.at, PB.snap


def schedule():
    seed = P48.seed_events(SEED_AT_M)
    k_on = P48.onset_k(PB.run(seed, SEED_AT_M + 30))
    k1 = k_on + P1_AFTER_M
    kb = k1 + P1_SEED_GM
    kl = kb + BERI_POLL_M + PRE_GM
    end = kl + L1_GM + L2_GM
    return {"seed": SEED_AT_M, "onset": k_on, "p1": k1, "thiamine": kb, "snack": kl, "end": end}, seed


def x495():
    m, seed = schedule()
    probe = PB.run(seed + [setp(m["p1"], "drain.pS", B.P1_P)], m["p1"] + SEED_FLOORS_M + 1)
    f1 = at(probe, m["p1"])
    ev = seed + [setp(m["p1"], "drain.pS", B.P1_P),
                 stat(m["p1"] + SEED_FLOORS_M, "STRESS", f1["effects.stressFloor"]),
                 stat(m["p1"] + SEED_FLOORS_M, "UNHAPPINESS", f1["effects.unhappyFloor"]),
                 setp(m["thiamine"], "nutrients.thiamine.p", B.THIAMINE_P),
                 setp(m["snack"], "satiety.M", L.SNACK_M)]
    rows = PB.run(ev, m["end"] + 1)
    lapse = next(r for r in rows if r["k"] >= m["snack"] and not B.has_bit(r.get("drain.mask"), B.MASK_STARVE))
    before = at(rows, lapse["k"] - 1)
    heal_at = next((r["k"] for r in rows if r["k"] > lapse["k"]
                    and abs((r.get("drain.target") or 0) - (r.get("health") or 0)) <= B.REL_HEAL_TOL), None)
    return {"minutes": m, "floors_seeded": [r6(f1["effects.stressFloor"]), r6(f1["effects.unhappyFloor"])],
            "pre": snap(at(rows, m["snack"] - 1)), "end": snap(rows[-1]),
            "lapse": {"lag_m": lapse["k"] - m["snack"], "mask": lapse.get("drain.mask"),
                      "recovering": lapse.get("drain.recovering"), "cap_before": r6(before.get("effects.enduranceCap")),
                      "cap_after": r6(lapse.get("effects.enduranceCap")), "u_before": r6(before.get("moodLast.u")),
                      "u_after": r6(lapse.get("moodLast.u")), "health": r6(lapse.get("health")),
                      "target": r6(lapse.get("drain.target"))},
            "heal_at_target_after_lapse_m": None if heal_at is None else heal_at - lapse["k"],
            "l2_gm": L2_GM, "wall": {k: r6(v) for k, v in L.predicted_wall().items()}}


FUNCS = {"x495": x495}


def compute(keys=KEYS):
    return {k: FUNCS[k]() for k in keys}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    now = canonical(compute())
    path = os.path.join(L.REPO, L.PRERUN_FILE)
    if a.check:
        have = L.load_prerun(path)
        stale = [k for k in KEYS if have.get(k) != now[k]]
        print(("stale: " + ", ".join(stale)) if stale else "in sync: " + L.PRERUN_FILE)
        return 1 if stale else 0
    if a.write:
        doc = dict(L.load_prerun(path))
        doc.update(now)
        doc["_provenance"] = canonical(dict(PB.provenance(), tool_x49c="x49c_prerun.py on x49b_prerun's backend"))
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print("wrote " + L.PRERUN_FILE)
        return 0
    print(json.dumps(now, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
