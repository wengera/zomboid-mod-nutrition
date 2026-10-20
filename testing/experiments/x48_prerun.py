"""x48_prerun -- the pre-run predictions of Plan 17 Task 4's sessions (x481, x482): the HEAD server replay
(tools/replay_live.ServerReplay, the mod's own adapters on the lupa host, the responder constant at its middle, game_heal
on, sleep off, the 90-minute day) of exactly each session's schedule FROM THE FIRST SIGHT (CLAUDE.md s5, Plan 15 Task
14b): a fresh record seen at x48_lib.FIRST_SIGHT's age with its HUNGER, THIRST and FATIGUE and the fixture's body, so the
seed plate the live fresh record lands is in the replay too. Each session's predictions are its grades' observed values
on the replay's own rows, read the way the lib reads a ring (ring_like: ring row j holds the state drain j - 1 left).

ONE COMMAND re-derives every prediction after a replay change:
    python testing/experiments/x48_prerun.py --write          writes testing/experiments/x48_prerun.json
    python testing/experiments/x48_prerun.py --check          exits 1 when the committed file is not the HEAD replay's
    python testing/experiments/x48_prerun.py [x481 ...]       prints the named sessions' predictions
x48_lib.preboot refuses a boot whose session's committed predictions differ from the replay re-derived at boot time.

The schedules (each mirrors its driver; the live phases before the seed take game time the replay places at
SEED_AT_M, never at a guessed wall time; the later acts are placed from the replay's own onset):
  x481  Realistic, Multiply. At SEED_AT_M the meal pool 0 and the unfed clock to the age less STARVE_ONSET_H plus
        SEED_LEAD_H; the thiamine store to THIAMINE_P HOLD_H after the onset drain; NR.DeathPace SWITCH_PACE (a setpath
        of _G.SandboxVars.NR.DeathPace, which the options poll reads) SWITCH_AFTER_H after the thiamine; then
        FOLLOW_WATCH_GM and POST_H.
  x482  Vanilla, Add. The same seed; to the death and DEATH_TAIL_M minutes past it.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x48_lib as L                                                           # noqa: E402
import replay_live as RL                                                      # noqa: E402

START = L.FIRST_SIGHT["age"]
SEED_AT_M = 20                           # S, H and W at speed 1 (a game minute 3.75 wall s; W waits up to 60 s)
DEATH_TAIL_M = 30
KEYS = tuple(L.SESSIONS)


def backend(pace, combine):
    return RL.ServerReplay(hour_offset=L.HOUR_OFFSET, rng="half", sleep_allowed=False,
                           stats=dict(L.FIRST_SIGHT["stats"]), player=dict(L.FIRST_SIGHT["player"]),
                           death_pace=pace, health_combine=combine, day_minutes=L.DAY_MIN, game_heal=True)


def age_of(k):
    return START + (k + 1) / 60.0


def run(pace, combine, events, minutes):
    rows = RL.run(backend(pace, combine), RL.synthetic_ages(minutes, start_age=START), events, list(L.RING),
                  start_age=START)
    for r in rows:
        r["s"] = r["k"] + 2                       # replay row k is compared with ring row k + 1 (ring_like's s k + 2)
    return rows


def ring_like(rows):
    """The replay rows as a ring would read them: ring row j (s j + 1) holds the state drain j - 1 left, at age j."""
    out = []
    for j in range(1, len(rows)):
        r = {k: v for k, v in rows[j - 1].items() if k not in ("age", "dtM", "hour", "min", "k", "s", "events",
                                                                "ringEvents")}
        r.update({"s": j + 1, "age": rows[j]["age"], "on": True})
        out.append(r)
    return out


def seed_events(k):
    return [{"minute": k, "kind": "setpath", "path": "satiety.M", "value": 0},
            {"minute": k, "kind": "setpath", "path": "drain.fedAgeH",
             "value": age_of(k) - L.STARVE_ONSET_H + L.SEED_LEAD_H}]


def onset_k(rows):
    return next(r["k"] for r in rows if r.get("drain.starveAcute") is True and r.get("drain.active") is True)


def r6(x):
    return None if x is None else round(float(x), 6)


def pick(d, keys):
    return {k: (r6(d.get(k)) if isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool) else d.get(k))
            for k in keys}


def x481():
    seed = seed_events(SEED_AT_M)
    probe = run(3, 2, seed, SEED_AT_M + 30)
    k_on = onset_k(probe)
    k_b = k_on + int(round(L.HOLD_H * 60))
    k_sw = k_b + int(round(L.SWITCH_AFTER_H * 60))
    end = k_sw + int(round(L.FOLLOW_WATCH_GM)) + int(round(L.POST_H * 60))
    thi = [{"minute": k_b, "kind": "setpath", "path": "nutrients.thiamine.p", "value": L.THIAMINE_P}]
    sw = [{"minute": k_sw, "kind": "setpath", "path": "_G.SandboxVars.NR.DeathPace", "value": L.SWITCH_PACE}]
    on = run(3, 2, seed + thi + sw, end)
    off = run(3, 2, seed + thi, end)
    ring = ring_like(on)
    seed_age = age_of(SEED_AT_M)
    i_on = L.onset_index(ring, seed_age)
    a_b, a_sw = age_of(k_b) - 0.5 / 60.0, age_of(k_sw) - 0.5 / 60.0     # the writes between drains k - 1 and k
    i_b = L.first_index(ring, lambda r: r["age"] > a_b)
    _, onset = L.grade_onset(ring, seed_age)
    _, rate = L.grade_open_rate(ring, i_on, i_b)
    op = L.open_pred(ring, i_on)
    _, beri = L.grade_beri(ring, a_b)
    _, comb = L.grade_combine(ring)
    _, fol = L.grade_follow(ring, on, off, a_sw)
    _, cap = L.grade_cap(ring, a_sw)
    last = ring[-1]
    return {"seed_age": r6(seed_age), "onset_after_seed_h": r6(onset.get("after_seed_h")),
            "open": pick(op, ("live", "pred", "slope0", "bmi0", "rate_day", "body_ratio", "rows")),
            "open_rate": pick(rate, ("rate_first", "want", "worst_rel")),
            "beri": pick(beri, ("lag_gm", "frac3")), "combine_rows": comb.get("n"),
            "follow": pick(fol, ("lag_gm", "target", "arm_on", "arm_off")),
            "cap": pick(cap, ("n", "slope_h", "want_h", "rate_day")),
            "end": {"health": r6(last.get("health")), "target": r6(last.get("drain.target")),
                    "frac1": r6(last.get(L.F1)), "frac3": r6(last.get(L.F3))},
            "minutes": {"seed": SEED_AT_M, "onset": k_on, "thiamine": k_b, "switch": k_sw, "end": end}}


def x482():
    seed = seed_events(SEED_AT_M)
    minutes = SEED_AT_M + int(round((100.0 / L.r_hunger(L.DAY_MIN) + 1.0) * 60)) + DEATH_TAIL_M
    rows = run(1, 3, seed, minutes)
    ring = ring_like(rows)
    seed_age = age_of(SEED_AT_M)
    i_on = L.onset_index(ring, seed_age)
    death = L.death_replay(rows)
    _, slope = L.grade_slope(ring)
    on_age = ring[i_on - 1]["age"]
    rd = L.x442_reading(death, seed_age, on_age)
    return {"seed_age": r6(seed_age), "onset_after_seed_h": r6(on_age - seed_age),
            "death_after_seed_h": r6(None if death is None else death - seed_age),
            "death_after_onset_h": r6(None if death is None else death - on_age),
            "slope": pick(slope, ("slope_h", "want_h", "rel", "n")),
            "x442": pick(rd, ("diff_after_write_h", "diff_after_onset_h", "x442_after_write_h", "x442_after_level4_h"))}


FUNCS = {"x481": x481, "x482": x482}


def compute(keys=KEYS):
    return {k: FUNCS[k]() for k in keys}


def provenance():
    def say(*a):
        try:
            return subprocess.run(["git"] + list(a), cwd=L.REPO, capture_output=True, text=True).stdout.strip()
        except OSError:
            return None
    return {"first_sight": L.FIRST_SIGHT, "seed_at_m": SEED_AT_M, "mod_commit": say("log", "-1", "--format=%h", "--",
                                                                                   L.MOD_DIR),
            "tool": "tools/replay_live.py ServerReplay (game_heal on, rng half, sleep off, 90-minute day)"}


def canonical(d):
    return json.loads(json.dumps(d, sort_keys=True, default=str))


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
