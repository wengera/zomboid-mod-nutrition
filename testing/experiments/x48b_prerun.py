"""x48b_prerun -- the pre-run prediction of Plan 17 Task 7's x484 (the straight-line health drain at Realistic pace with
Multiply): the HEAD server replay (tools/replay_live.ServerReplay, the mod's own adapters on the lupa host, the responder
constant at its middle, game_heal on, sleep off, the 90-minute day) of exactly the session's schedule FROM THE FIRST
SIGHT (CLAUDE.md s5, Plan 15 Task 14b): a fresh record seen at x48_lib.FIRST_SIGHT's age with its HUNGER, THIRST and
FATIGUE, and NO typed weight, so the stand-in's first sight lays the mod's own creation body (lm 52.02, fm 13.005, the
65.025 kg of x481's live start.json), never x48_prerun's typed 80 kg (the Task 4 finding). The seed plate the live fresh
record lands is in the replay too. The predictions are the grades' observed values on the replay's own rows, read the
way the lib reads a ring (x48_prerun.ring_like: ring row j holds the state drain j - 1 left).

ONE COMMAND re-derives the prediction after a replay change:
    python testing/experiments/x48b_prerun.py --write          writes testing/experiments/x48b_prerun.json
    python testing/experiments/x48b_prerun.py --check          exits 1 when the committed file is not the HEAD replay's
    python testing/experiments/x48b_prerun.py                  prints the prediction
x48b_lib.preboot refuses an x484 boot whose committed prediction differs from the replay re-derived at boot time.

The schedule mirrors x484_line.py: at SEED_AT_M (x48_prerun's: S, H and W at speed 1 take game time the replay places
there, never at a guessed wall time) the meal pool 0 and the unfed clock to the age less STARVE_ONSET_H plus SEED_LEAD_H;
the thiamine store to THIAMINE_P HOLD_H after the onset drain; then POST_H, plus BERI_POLL_M minutes for the grade's
poll at speed 1 before P.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x48b_lib as L                                                          # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x48_prerun as P48                                                      # noqa: E402
import replay_live as RL                                                      # noqa: E402

START = L48.FIRST_SIGHT["age"]
SEED_AT_M = P48.SEED_AT_M
BERI_POLL_M = 2                          # the B poll at speed 1 until the grade reads 4 (two minute events)
KEYS = ("x484",)
FIRST_SIGHT_PLAYER = {k: v for k, v in L48.FIRST_SIGHT["player"].items() if k != "weight"}   # no typed weight


def backend(pace, combine):
    return RL.ServerReplay(hour_offset=L48.HOUR_OFFSET, rng="half", sleep_allowed=False,
                           stats=dict(L48.FIRST_SIGHT["stats"]), player=dict(FIRST_SIGHT_PLAYER),
                           death_pace=pace, health_combine=combine, day_minutes=L.DAY_MIN, game_heal=True)


def run(pace, combine, events, minutes):
    rows = RL.run(backend(pace, combine), RL.synthetic_ages(minutes, start_age=START), events, list(L48.RING),
                  start_age=START)
    for r in rows:
        r["s"] = r["k"] + 2                       # replay row k is compared with ring row k + 1 (ring_like's s k + 2)
    return rows


r6 = P48.r6
pick = P48.pick


def x484():
    seed = P48.seed_events(SEED_AT_M)
    pace, combine = L.PROFILES["x48-line"]["pace"], L.PROFILES["x48-line"]["combine"]
    probe = run(pace, combine, seed, SEED_AT_M + 30)
    k_on = P48.onset_k(probe)
    k_b = k_on + int(round(L.HOLD_H * 60))
    end = k_b + BERI_POLL_M + int(round(L.POST_H * 60))
    thi = [{"minute": k_b, "kind": "setpath", "path": "nutrients.thiamine.p", "value": L48.THIAMINE_P}]
    rows = run(pace, combine, seed + thi, end)
    ring = P48.ring_like(rows)
    seed_age = P48.age_of(SEED_AT_M)
    i_on = L48.onset_index(ring, seed_age)
    a_b = P48.age_of(k_b) - 0.5 / 60.0                                  # the write between drains k_b - 1 and k_b
    i_b = L48.first_index(ring, lambda r: r["age"] > a_b)
    _, onset = L48.grade_onset(ring, seed_age)
    _, line = L.grade_line(ring, i_on, i_b)
    _, rate = L.grade_rate(ring)
    _, beri = L48.grade_beri(ring, a_b)
    _, comb = L.grade_combine(ring, a_b)
    first, last = ring[0], ring[-1]
    gap = max(abs((r.get("health") or 0.0) - (r.get("drain.target") or 0.0)) for r in ring[i_on:])
    return {"seed_age": r6(seed_age), "onset_after_seed_h": r6(onset.get("after_seed_h")),
            "body": {"lm": r6(first.get("body.lm")), "fm": r6(first.get("body.fm")),
                     "kg": r6((first.get("body.lm") or 0.0) + (first.get("body.fm") or 0.0))},
            "line": pick(line, ("n", "bmi0", "slope_h", "want_h", "rel", "line_rate_day", "n_off", "target0",
                                "target1")),
            "rate": pick(rate, ("n_starve", "n_starve_beri", "floor_day", "beri_day", "n_under", "n_off")),
            "beri": pick(beri, ("lag_gm", "frac3")),
            "combine": pick(comb, ("n", "n_off", "sep_add_max", "sep_worst_max")),
            "health_gap_max": r6(gap),
            "end": {"health": r6(last.get("health")), "target": r6(last.get("drain.target")),
                    "frac1": r6(last.get(L.F1)), "frac3": r6(last.get(L.F3)), "rate": r6(last.get("drain.rate"))},
            "minutes": {"seed": SEED_AT_M, "onset": k_on, "thiamine": k_b, "end": end}}


FUNCS = {"x484": x484}


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
            "tool": "tools/replay_live.py ServerReplay (game_heal on, rng half, sleep off, 90-minute day, no typed "
                    "weight: the mod's creation body)"}


canonical = P48.canonical


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
