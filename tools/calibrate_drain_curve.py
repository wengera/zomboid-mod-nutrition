"""The health curve's severity-clock calibration (Plan 17 Task 1; spec docs/superpowers/specs/2026-10-19-health-combine-
design.md@program-record-v19 sections 1.2 and 4.1).

The curve f(tau) = 1 - ln(1 + a tau) / ln(1 + a T) opens at the slope a / ln(1 + a T) (`opening_slope`). On a severity
clock the clock is the progress p itself (T = 1: BMI progress p = (bmi0 - bmi) / (bmi0 - 12) for starvation, the deficit
progress (d - 4) / (15 - 4) for dehydration), so the opening slope in time is opening_slope(a, 1) x dp/dt. This tool
reads dp/dt off the replay host at each onset for the default creation body and solves a so that the opening slope
equals vanilla's own drain rate at the 90-minute day (r_hunger = 0.0396 x dayMinutes and r_thirst = 0.198 x dayMinutes
health per game hour, #0516, #0518, #2922):

- starvation: the guide's S2d fast with water (`mod_guide_series.j_s2d`'s events: the FRESH start at HUNGER 0, no food,
  the replay's water AUTODROP_G at AUTODROP_MIN each day, sleep off, the default body), read from the onset
  (record.drain.starving first true) to STARVE_WINDOW_H game hours past it;
- dehydration: the S2d no-water arm (`j_s2d_dry`'s events: FRESH only), read from the onset (record.drain.dehydrated
  first true, the 4 % line) to DEHYD_WINDOW_H game hours past it.

Both windows are game choices. The replay runs a shorter span than the guide's jobs (STARVE_RUN_DAYS and DRY_RUN_DAYS
in place of 90 and 8 days) through the same `mod_guide_series.server_run`; the replay is causal and the events it drops
fall after its span, so the rows it reads are the guide jobs' own rows. The rows are one per game minute (row k is the
state drain k left, at age (k + 1) / 60 h), so both reads are exact rows, with no interpolation.

Usage: python tools/calibrate_drain_curve.py --write   (writes ARTIFACT)
       python tools/calibrate_drain_curve.py --check   (exit 1 if an input's sha256 or a recomputed value differs)
       python tools/calibrate_drain_curve.py           (prints the computation)
"""
import argparse
import glob
import hashlib
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ARTIFACT = os.path.join(REPO, "testing", "artifacts", "calibrate-drain-20261019", "calibration.json")
DAY_MINUTES = 90                       # the server day length the calibration holds at (spec section 1.2)
R_HUNGER_PER_DAYMIN = 0.0396           # health per game hour per real minute of day: 3.3e-4 x 120 (#0516, #0518, #2922)
R_THIRST_PER_DAYMIN = 0.198            # health per game hour per real minute of day: 1.65e-3 x 120 (#0516, #0518, #2922)
STARVE_WINDOW_H = 24                   # game hours read past the starvation onset: game choice (Plan 17 Task 1)
DEHYD_WINDOW_H = 6                     # game hours read past the dehydration onset: game choice (Plan 17 Task 1)
STARVE_RUN_DAYS = 4                    # the with-water replay's span: the onset (about 34.5 h) plus the window fits
DRY_RUN_DAYS = 3                       # the dry replay's span: the onset (about 32.9 h) plus the window fits
BMI_DEATH = 12.0                       # kg/m2, starvation's death point (K.drain.BMI_DEATH, S2234), checked off the host
DEHYD_ONSET_PCT = 4.0                  # % body mass, dehydration's onset (K.drain.states[DEHYD].onset), checked off the host
DEHYD_KNEE_PCT = 15.0                  # % body mass, the end of dehydration's curve (spec section 1.1)
A_LO, A_HI, ITERS = 1e-9, 1e9, 200     # solve_a's bisection on log a

# the files the computation reads: the replay host loads every shared NR_*.lua and server NR_Server_*.lua
# (testing/tests/kernel/server_host.py), the stand-ins (golden_trace.py), the replay (replay_live.py), the guide's fast
# setup (mod_guide_series.py) and this tool; hashed with CRLF read as LF, so a checkout's line endings do not count
INPUT_GLOBS = (
    "mod/NutritionRevamp/common/media/lua/shared/NR_*.lua",
    "mod/NutritionRevamp/common/media/lua/server/NR_Server_*.lua",
    "testing/tests/kernel/server_host.py",
    "testing/tests/kernel/golden_trace.py",
    "tools/replay_live.py",
    "tools/mod_guide_series.py",
    "tools/calibrate_drain_curve.py",
)


# ---- the curve and its solver (pure) --------------------------------------------------------------------------------

def opening_slope(a, span):
    """The curve's opening slope, the fraction lost per clock unit at tau = 0: a / ln(1 + a span); 1 / span, the
    line's, at a <= 0."""
    if not (a > 0):
        return 1.0 / span
    return a / math.log1p(a * span)


def solve_a(target, span):
    """The a whose opening slope over a clock of `span` is `target` (fraction per clock unit): bisection on log a over
    [A_LO, A_HI], ITERS steps. 0.0 (the line) when the target is at or under the line's slope 1 / span."""
    if target <= (1.0 / span) * (1 + 1e-12):
        return 0.0
    if target > opening_slope(A_HI, span):
        raise ValueError("target %r is past the bisection's bound a = %r" % (target, A_HI))
    lo, hi = math.log(A_LO), math.log(A_HI)
    for _ in range(ITERS):
        mid = 0.5 * (lo + hi)
        if opening_slope(math.exp(mid), span) < target:
            lo = mid
        else:
            hi = mid
    return math.exp(0.5 * (lo + hi))


def curve(tau, span, a):
    """The remaining fraction f(tau) = 1 - ln(1 + a tau) / ln(1 + a span), tau clamped to [0, span]; the line at
    a <= 0."""
    t = min(max(tau, 0.0), span)
    if not (a > 0):
        return 1.0 - t / span
    return 1.0 - math.log1p(a * t) / math.log1p(a * span)


def r_hunger(day_minutes):
    """Vanilla's hunger level-4 drain in health per game hour at a day of `day_minutes` real minutes."""
    return R_HUNGER_PER_DAYMIN * day_minutes


def r_thirst(day_minutes):
    """Vanilla's thirst level-4 drain in health per game hour at a day of `day_minutes` real minutes."""
    return R_THIRST_PER_DAYMIN * day_minutes


# ---- the inputs -------------------------------------------------------------------------------------------------------

def input_files(root=REPO):
    out = []
    for pat in INPUT_GLOBS:
        hits = sorted(glob.glob(os.path.join(root, *pat.split("/"))))
        if not hits:
            raise FileNotFoundError("no input matches %s under %s" % (pat, root))
        out += hits
    return out


def input_hashes(root=REPO):
    """{repo-relative path: sha256 of its bytes with CRLF read as LF}."""
    out = {}
    for p in input_files(root):
        with open(p, "rb") as fh:
            data = fh.read().replace(b"\r\n", b"\n")
        out[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(data).hexdigest()
    return out


def combined(hashes):
    """One sha256 over the sorted (path, sha256) lines."""
    h = hashlib.sha256()
    for k in sorted(hashes):
        h.update(("%s %s\n" % (k, hashes[k])).encode("utf-8"))
    return h.hexdigest()


# ---- the replay reads -------------------------------------------------------------------------------------------------

def _onset(rows, flag):
    k = next((i for i, r in enumerate(rows) if r.get(flag)), None)
    if k is None:
        raise RuntimeError("the replay never sets %s" % flag)
    return k


def read_starvation():
    """The S2d fast with water from its starvation onset: the onset row, bmi0 (record.drain.bmi0 there) and the BMI
    STARVE_WINDOW_H later, K.drain.bmi of body.lm and body.fm (the BMI the drain reads)."""
    import mod_guide_series as S
    days = STARVE_RUN_DAYS
    rows, be = S.server_run([S.FRESH] + S.autodrops(days), days * S.DAY_MIN,
                            ("body.fm", "body.lm", "drain.bmi0", "drain.starving"))
    K = be.K
    if float(K.drain.BMI_DEATH) != BMI_DEATH:
        raise RuntimeError("K.drain.BMI_DEATH is %r, not the calibration's %r" % (K.drain.BMI_DEATH, BMI_DEATH))
    k0 = _onset(rows, "drain.starving")
    k1 = k0 + STARVE_WINDOW_H * 60
    if k1 >= len(rows):
        raise RuntimeError("the window runs past the replay's %d rows" % len(rows))
    bmi0 = float(rows[k0]["drain.bmi0"])
    bmi1 = float(K.drain.bmi(rows[k1]["body.lm"], rows[k1]["body.fm"]))
    if not rows[k1].get("drain.starving") or float(rows[k1]["drain.bmi0"]) != bmi0:
        raise RuntimeError("the starvation state did not hold over the window")
    p1 = (bmi0 - bmi1) / (bmi0 - BMI_DEATH)
    return {"run_days": days, "onset_row": k0, "onset_age_h": rows[k0]["age"], "end_row": k1,
            "end_age_h": rows[k1]["age"], "bmi0": bmi0, "bmi_end": bmi1, "bmi_death": BMI_DEATH, "p_end": p1,
            "dpdt_per_h": p1 / STARVE_WINDOW_H}


def read_dehydration():
    """The S2d no-water arm from its dehydration onset: the deficit fluids.dehydPct at the onset row and
    DEHYD_WINDOW_H later."""
    import mod_guide_series as S
    days = DRY_RUN_DAYS
    rows, be = S.server_run([S.FRESH], days * S.DAY_MIN, ("drain.dehydrated",))
    K = be.K
    onset = float(K.drain.states[K.drain.DEHYD].onset)
    if onset != DEHYD_ONSET_PCT:
        raise RuntimeError("the dehydration onset is %r, not the calibration's %r" % (onset, DEHYD_ONSET_PCT))
    k0 = _onset(rows, "drain.dehydrated")
    k1 = k0 + DEHYD_WINDOW_H * 60
    if k1 >= len(rows):
        raise RuntimeError("the window runs past the replay's %d rows" % len(rows))
    d0, d1 = float(rows[k0]["fluids.dehydPct"]), float(rows[k1]["fluids.dehydPct"])
    p1 = (d1 - DEHYD_ONSET_PCT) / (DEHYD_KNEE_PCT - DEHYD_ONSET_PCT)
    return {"run_days": days, "onset_row": k0, "onset_age_h": rows[k0]["age"], "end_row": k1,
            "end_age_h": rows[k1]["age"], "d_onset": d0, "d_end": d1, "d_from": DEHYD_ONSET_PCT,
            "d_to": DEHYD_KNEE_PCT, "p_end": p1, "dpdt_per_h": p1 / DEHYD_WINDOW_H}


# ---- the calibration --------------------------------------------------------------------------------------------------

def calibrate(starve_dpdt, dehyd_dpdt, day_minutes=DAY_MINUTES):
    """The a values from the two progress rates: opening_slope(a, 1) = r / 100 / (dp/dt), each clock the progress
    (T = 1); with the opening slope each a gives back, in health per game hour."""
    rh, rt = r_hunger(day_minutes), r_thirst(day_minutes)
    a_s = solve_a(rh / 100.0 / starve_dpdt, 1.0)
    a_d = solve_a(rt / 100.0 / dehyd_dpdt, 1.0)
    return {"r_hunger_90": rh, "r_thirst_90": rt, "a_starve": a_s, "a_dehyd": a_d,
            "opening_health_per_h": {"starve": 100.0 * opening_slope(a_s, 1.0) * starve_dpdt,
                                     "dehyd": 100.0 * opening_slope(a_d, 1.0) * dehyd_dpdt}}


def compute(root=REPO):
    """The artifact's content less tool_commit."""
    st, dh = read_starvation(), read_dehydration()
    cal = calibrate(st["dpdt_per_h"], dh["dpdt_per_h"])
    hashes = input_hashes(root)
    return {"tool": "tools/calibrate_drain_curve.py", "day_minutes": DAY_MINUTES,
            "r_hunger_90": cal["r_hunger_90"], "r_thirst_90": cal["r_thirst_90"],
            "window_h": {"starve": STARVE_WINDOW_H, "dehyd": DEHYD_WINDOW_H},
            "starve_dpdt_per_h": st["dpdt_per_h"], "dehyd_dpdt_per_h": dh["dpdt_per_h"],
            "a_starve": cal["a_starve"], "a_dehyd": cal["a_dehyd"],
            "opening_health_per_h": cal["opening_health_per_h"],
            "starve": st, "dehyd": dh, "inputs": hashes, "inputs_sha256": combined(hashes)}


def head_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short=8", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def dumps(obj):
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


def write(path=ARTIFACT):
    out = compute()
    out["tool_commit"] = head_commit()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps(out))
    return out


def check(path=ARTIFACT, root=REPO):
    """The findings, empty when in sync: each input whose sha256 differs (checked first, with no replay), then each
    top-level value a recomputation changes (tool_commit, the HEAD the artifact was written on, is not compared)."""
    with open(path, encoding="utf-8") as fh:
        art = json.load(fh)
    now = input_hashes(root)
    was = art.get("inputs", {})
    bad = ["input %s: sha256 %s, the artifact's %s" % (k, now.get(k), was.get(k))
           for k in sorted(set(now) | set(was)) if now.get(k) != was.get(k)]
    if bad:
        return bad
    out = json.loads(dumps(compute(root)))
    keys = (set(out) | set(art)) - {"tool_commit"}
    return ["value %s: %r, the artifact's %r" % (k, out.get(k), art.get(k))
            for k in sorted(keys) if out.get(k) != art.get(k)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="write the artifact")
    g.add_argument("--check", action="store_true", help="exit 1 when a recomputation differs from the artifact")
    a = ap.parse_args(argv)
    if a.check:
        bad = check()
        for b in bad:
            print("calibrate_drain_curve: " + b)
        print("calibrate_drain_curve: %s" % ("in sync" if not bad else "%d finding(s)" % len(bad)))
        return 1 if bad else 0
    out = write() if a.write else compute()
    print(dumps({k: out[k] for k in ("a_starve", "a_dehyd", "starve_dpdt_per_h", "dehyd_dpdt_per_h",
                                     "opening_health_per_h", "inputs_sha256")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
