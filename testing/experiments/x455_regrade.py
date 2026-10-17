"""x455_regrade -- a derived artifact (Plan 15 Task 11 live review, F1): x455's bleed graded absolutely, its committed
artifact re-read, never re-run.

x455's N window (four parts bleeding, not starving, the constant at its value) ran Well Fed: its stats.get reads carry the
food timer near 971 and FOOD_EATEN 1, so vanilla's food heal (getHealthFromFood x the multiplier a tick while the timer is
above 0, BodyDamage.Update L2271-L2273 through AddGeneralHealth L2330; the mod's healthFromFood 0.0087 x 90 / dayMin,
NR_Server_Effects.lua) ran beside the bleed. SB's drain switched the heal off (the timer 0, FOOD_EATEN 0). So N's 10.54 a
game hour is the bleed and wound net of that heal, and x455's S_BLEED (SB minus N) is not a comparison of two bleed terms.

This script grades SB alone: its rate against x451's wound term (C2, four parts at bleedingTime 5 with the constant at 0:
5.963110742769263 a game hour; the transfer to x455's same four parts is an inference) plus the whole constant's
BLEEDING-4 term red0 x M_H (BodyDamage.Update L2375-L2377: no divisor) plus the starvation drain 25 / 24, within the
original 15 %. N is restated as the Well Fed net, a reading beside its food timer and FOOD_EATEN levels.

`python testing/experiments/x455_regrade.py [<x455 artifact dir>] [--out <dir>]`; the default output is
testing/artifacts/x455-regrade-20261017/regrade.json. Frozen once its output is committed (CLAUDE.md s5).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUN = "x455-20261017-073633"
SRC = os.path.join(REPO, "testing", "artifacts", RUN, "bleed.json")
OUT = os.path.join(REPO, "testing", "artifacts", "x455-regrade-20261017")
WOUND_X451 = 5.963110742769263           # x451 C2's rate_per_gh (capspike.json verdicts.C2.observed.rate_per_gh)
M_H = 1800.0                             # the multiplier's sum a game hour at DayLength 1 (#0518, #2922)
STARVE_GH = 25.0 / 24.0                  # K.drain.STARVE_RATE a game hour (health above the floor)
TOL_REL = 0.15                           # x455's S_TOL_REL, unchanged


def num(v):
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def grade_sb(sb_rate, red0, levels, const):
    """SB absolutely: as_predicted when BLEEDING 4 at both ends, the constant 0 at both ends and the rate within TOL_REL
    of WOUND_X451 + red0 x M_H + STARVE_GH; unmeasured on a missing input."""
    obs = {"rate_per_gh": sb_rate, "red0": red0, "levels": levels, "const": const}
    if sb_rate is None or red0 is None or list(levels or []) != [4, 4] or None in (const or [None]):
        return "unmeasured", obs
    pred = WOUND_X451 + red0 * M_H + STARVE_GH
    obs.update({"predicted_per_gh": pred, "rel_err": (sb_rate - pred) / pred,
                "terms": {"wound_x451": WOUND_X451, "bleed4": red0 * M_H, "starve": STARVE_GH}})
    ok = abs(obs["rel_err"]) <= TOL_REL and all(abs(c) <= 1e-9 for c in const)
    return ("as_predicted" if ok else "falsified"), obs


def n_reading(d):
    """N restated: its rate beside the food timer and FOOD_EATEN at both ends (a reading, never a grade)."""
    w = d["checks"]["windows"]["N"]
    return {"rate_per_gh": num(d["verdicts"]["N_BLEED"]["observed"].get("rate_per_gh")),
            "foodTimer": [num(w["s0"].get("foodTimer")), num(w["s1"].get("foodTimer"))],
            "foodEaten": [w["s0"].get("moodles", {}).get("foodEaten"), w["s1"].get("moodles", {}).get("foodEaten")],
            "well_fed": all((num(w[k].get("foodTimer")) or 0) > 0 for k in ("s0", "s1")),
            "note": "the bleed and wound net of vanilla's food heal; not vanilla's bleed term"}


def regrade(d):
    S = d["verdicts"]["S_BLEED"]["observed"]
    sb = num((S.get("S") or {}).get("rate_per_gh"))
    red0 = num(d["checks"]["S"]["const"].get("value"))
    v, obs = grade_sb(sb, red0, S.get("levels"), S.get("const"))
    wsb = d["checks"]["windows"]["SB"]
    obs["SB_foodTimer"] = [num(wsb["s0"].get("foodTimer")), num(wsb["s1"].get("foodTimer"))]
    return {"verdicts": {"SB_ABS": {"verdict": v, "observed": obs,
                                    "falsifier": f"SB's rate off wound + red0 x M_H + starvation by more than {TOL_REL:.0%}"}},
            "readings": {"N": n_reading(d)}}


def main(argv):
    src = argv[0] if argv and not argv[0].startswith("--") else SRC
    out = OUT
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    raw = open(src, "rb").read()
    d = json.loads(raw.decode("utf-8"))
    res = regrade(d)
    res.update({"source": os.path.relpath(src, REPO).replace(os.sep, "/"), "source_sha256": hashlib.sha256(raw).hexdigest(),
                "script": "testing/experiments/x455_regrade.py", "kind": "derived artifact (analysis, not a live run)"})
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "regrade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(res["verdicts"], indent=1, sort_keys=True))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
