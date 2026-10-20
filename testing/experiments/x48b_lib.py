"""x48b_lib -- the session engine of Plan 17 Task 7's two live readings on the re-staged upload copy (the exact bytes
Angus uploads, staged from mod/'s final head for Plan 17), each one boot on a dedicated server, build 42.21.0:

  x483 options  the two new sandbox options, NR.DeathPace 2 (Shortened) and NR.HealthCombine 3 (Add), both off their
                declared defaults (3 and 2), set in the server's options file and read back on the server, admin and
                bob; the boot doubles as the clean 1.0.0 join (x471's design, Plan 16 Task 12).
  x484 line     the straight-line health drain of revision R1 (spec section 9) live at Realistic pace with Multiply, the
                guide's default line, graded against the HEAD replay of the run's own inputs (x481's seed and beriberi).

Built on testing/experiments/xlib.py (the session state, the wall budget, the grade recorder, the abort, teardown and
copy skeleton) and on the frozen libs of the two sessions it follows, imported unchanged (CLAUDE.md s5: a lib is frozen
with its first run):
  x47_lib.py   (x471's) its options-file reader, its lua.global read and option grade, its log readers, its join grade
               and its bob watch;
  x48_lib.py   (x481's) its Sess (the seed, the hold, the thiamine write, the ring and its pages, W's start.json, the
               clock and its restore, the replay of the run's own ring), its ring paths RING, its write placement and
               its pure grades OPT, ONSET, BERI_ON, H1; its fixture-fresh, harness-marker and prerun checks;
  x45g_lib.py  through both: the staged gate, the log patterns and the Z and RING grades.
Their own constants (STAGED_FROM, the stage paths, SESSIONS) are theirs and never read here for this task's sessions:
this file names its own staged copy, commit, sessions, profiles, schedule and tolerances.

THE STAGED COPY. Both profiles boot release/NutritionRevamp/Contents/mods/NutritionRevamp, the upload copy itself,
re-staged from mod/'s last commit before the boots (`python tools/release_pack.py stage mod/NutritionRevamp --out
release`); staged_gate checks it against release_pack.manifest() of mod/ at STAGED_FROM (a git archive) and refuses on
a mismatch, and preboot refuses when STAGED_FROM is not mod/'s last commit. mod/ is never booted (CLAUDE.md s5, x201).

THE SESSIONS (each one boot, under 10 wall minutes, in a foreground call):
  x483 options (x48-options; fixture two: admin -debug, role admin; bob release, role user; DayLength 1, sleep off,
               Nutrition false) the profile's [sandbox.NR] DeathPace = 2 and HealthCombine = 3 merged into the server's
               own options file (Server/pzt_SandboxVars.lua) at seed. admin attaches (session.attach_clients), then bob
               is started and watched by the driver (x47_lib.watch_bob: a never-ready bob is a reading, not a raise).
               Once bob is ready and READ_SETTLE_S has passed: the reads (`after_ready`) on the server, admin and bob,
               the verify rows, HOLD_S held, the reads again (`end`), the players read. After teardown the server's
               user and connections logs and bob's connections log are read and copied (x471's). The wall guard (F1):
               bob is started only by BUDGET_S - OBS_S - CLOSE_RESERVE_S; the server boot waits at most 240 s.
  x484 line    (x48-line; fixture default, admin -debug, DayLength 4 (the 90-minute day: x481's, so r_hunger(dayMin)
               is vanilla's 3.564 health a game hour), sleep off, Nutrition false, NR.DeathPace 3 and NR.HealthCombine
               2, the declared defaults written so the profile says what the run is) S, H (x48_lib.RING), W (start.json),
               A (at speed 1: record.set satiety.M 0, then drain.fedAgeH to the age less STARVE_ONSET_H plus SEED_LEAD_H;
               speed SPEED_FAST until the record reads starveAcute; x481's), O (HOLD_H at SPEED_FAST), B (at speed 1:
               record.set nutrients.thiamine.p THIAMINE_P, under the clinical rung; polled until the grade reads 4;
               x481's), P (POST_H at SPEED_FAST), C (the clock back to the trueMult read at S), R (the ring).

THE FIRST SIGHT (CLAUDE.md s5, Plan 15 Task 14b; the Task 4 finding). The default fixture's character has no store
record, so x484 starts on a fresh record, which lands its seed plate and lays the mod's own creation body (lm 52.02, fm
13.005: 65.025 kg, x481's live start.json). The prediction (testing/experiments/x48b_prerun.py, written to
x48b_prerun.json) is the HEAD replay of the session's schedule from x48_lib.FIRST_SIGHT's vanilla stats with NO typed
weight, so the stand-in's first sight lays that creation body (x48_prerun's typed 80 kg laid a body x481 never had);
preboot refuses a boot whose committed prediction is not the HEAD replay's.

THE GRADES (pure; each has a failing case in testing/tests/test_x48b_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  x483  INI        (precondition) the seeded options file's NR block holds DeathPace = PACE_SET and HealthCombine =
                   COMBINE_SET.
        OPT_SERVER, OPT_ADMIN, OPT_BOB  SandboxVars.NR.DeathPace reads PACE_SET and SandboxVars.NR.HealthCombine
                   COMBINE_SET on that side in every read set (a client's copy is the one the server sends at the join).
        MOD_READ   the mod's own reads, on the server: NutritionRevamp.server.options.deathPace PACE_SET and
                   .healthCombine COMBINE_SET (the options poll), and NutritionRevamp.kernel.drain.OPT.pace PACE_SET and
                   .combine COMBINE_SET (the players' minute writes them, EFF.writeDrainOptions), in every read set.
                   The clients' NutritionRevamp.server.options copies are a reading, never a grade: the poll is gated on
                   NR.isServer() (NR_Server_Options.pollDirect, its OnServerStarted listener), so a client's copy keeps
                   the declared defaults 3 and 2 (predicted in checks, readings.client_server_options).
        JOIN       x47_lib's: admin and bob ready; NutritionRevamp.version the staged version on the server, admin and
                   bob at the end; the players read at the end both users; the user log a `fully connected` line for
                   bob and no Anti-cheat line; no checksum-mismatch line in the server's logs.
        Z          x45g_lib's: no mod error line in the server log, admin not parked.
  x484  OPT, ONSET, H1, RING, Z  x48_lib's (pace 3, combine 2, dayMin 90).
        LINE       on the ring rows from the onset row to the thiamine write with starvation alone active (drain.mask 1):
                   frac.1 = 1 - pS and the target = 100 x frac.1 within EQ_TOL on every row, bRate the calibrated
                   K.drain.STARVE_DBMI (no record-day close inside the session), and the target's slope against the
                   drain's own age (the row before's, x48_lib's placement) within LINE_TOL_REL of the line's,
                   100 x STARVE_DBMI / (bmi0 - 12) health a game hour for the ring's bmi0 (spec section 9: starvation
                   linear on the smoothed BMI progress), over at least LINE_MIN_ROWS rows.
        RATE       (ruling R1-5) every row with starvation active: drain.rate at least r_hunger(dayMin) x 24 health a game
                   day, vanilla's level-4 rate at the day length (a deficiency has no floor); on the starvation rows (mask 1) within RATE_TOL_REL of the larger of
                   that floor and the line's own rate; on the starvation-and-beriberi rows (mask 5) within RATE_TOL_REL of
                   that plus beriberi's 100 x 24 / BERIBERI_DEATH_H (a deficiency has no vanilla floor); at least one row
                   of each.
        BERI_ON    x48_lib's: grade 4 and frac.3 near 1 within BERI_GM game minutes of the thiamine write.
        COMBINE    every ring row after the thiamine write carrying both fractions reads the target 100 x (frac.1 x
                   frac.3) within COMBINE_TOL (Multiply, the polled combine 2); unmeasured unless some row's Add fold
                   parts from the product by more than COMBINE_SEP x COMBINE_TOL (the run separates Multiply from Add,
                   which x481's 1e-4 tolerance did not), at least COMBINE_MIN_ROWS rows.
        TRACK      (review N3) every active row after the onset row reads |health - drain.target| <= TRACK_TOL: health
                   on its line each minute (the take clamps to health - target); REPLAY_TOL cannot see a trail under 0.002
                   on a line this slow (0.00072 a game minute); at least LINE_MIN_ROWS rows.
        REPLAY_health, REPLAY_drain.target  every ring row's health and target within x48_lib.REPLAY_TOL (0.002) of
                   the HEAD replay of the run's own inputs (the line).

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402
import x47_lib as L47                                                         # noqa: E402
import x48_lib as L48                                                         # noqa: E402

REPO = X.REPO
SRV = X.SRV
NR = G.NR
ADMIN, BOB = L47.ADMIN, L47.BOB
USER = L48.USER
LIB_FILE = "x48b_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "62de3d5a"                 # mod/'s last commit (Plan 17 Task 2b fix 1), final for Plan 17
STAGED_VERSION = "1.0.0"
PRERUN_FILE = "testing/experiments/x48b_prerun.json"
MIN_FREE_GB = 12.0

SESSIONS = {
    "x483": {"driver": "x483_options.py", "artifact": "options.json", "profile": "x48-options"},
    "x484": {"driver": "x484_line.py", "artifact": "line.json", "profile": "x48-line"},
}
PROFILES = {"x48-options": {"fixture": "two", "clients": [ADMIN, BOB], "day_length": 1, "pace": 2, "combine": 3},
            "x48-line": {"fixture": "default", "clients": [ADMIN], "day_length": 4, "pace": 3, "combine": 2}}

# ---- x483: the options
PACE_SET = 2                             # Shortened; the declared default 3 (media/sandbox-options.txt)
COMBINE_SET = 3                          # Add; the declared default 2
PACE_DEFAULT = 3
COMBINE_DEFAULT = 2
SERVER_PACE_G = "SandboxVars.NR.DeathPace"
SERVER_COMBINE_G = "SandboxVars.NR.HealthCombine"
MOD_PACE_G = "NutritionRevamp.server.options.deathPace"
MOD_COMBINE_G = "NutritionRevamp.server.options.healthCombine"
OPT_PACE_G = "NutritionRevamp.kernel.drain.OPT.pace"
OPT_COMBINE_G = "NutritionRevamp.kernel.drain.OPT.combine"
OPT_DAYMIN_G = "NutritionRevamp.kernel.drain.OPT.dayMin"
VERSION_G = L47.VERSION_G
READ_PLAN = {
    SRV: (SERVER_PACE_G, SERVER_COMBINE_G, MOD_PACE_G, MOD_COMBINE_G, OPT_PACE_G, OPT_COMBINE_G, OPT_DAYMIN_G,
          VERSION_G, "NutritionRevamp.server.options.readAt"),
    ADMIN: (SERVER_PACE_G, SERVER_COMBINE_G, VERSION_G, MOD_PACE_G, MOD_COMBINE_G),
    BOB: (SERVER_PACE_G, SERVER_COMBINE_G, VERSION_G, MOD_PACE_G, MOD_COMBINE_G),
}
READ_SETTLE_S = L47.READ_SETTLE_S        # after bob's ready, before the first read set (x471's 5 s)
HOLD_S = L47.HOLD_S                      # held between the two read sets (x471's 20 s)
OBS_S = L47.OBS_S                        # bob watched at most this long from its start (x471's 180 s)
SANDBOX_REL = L47.SANDBOX_REL
SERVER_TIMEOUT_S = 240                   # both profiles' [server] timeout: the slow-boot fallback's bound (F1)
CLOSE_RESERVE_S = 150.0                  # x483: wall s kept after bob's watch for the hold, the end reads, the players read, teardown and the copy

# ---- x484: the line (game hours at DayLength 4)
MOD_DAY_LENGTH = 4
DAY_MIN = L48.DAY_MIN
HOLD_H = 2.0                             # the onset to the thiamine write (the amendments' "about 2 game hours")
POST_H = 1.0                             # after the thiamine's grade read, at SPEED_FAST: Multiply's rows
SPEED_FAST = L48.SPEED_FAST              # a game hour 45 wall s at DayLength 4
K_STARVE_DBMI = L48.K_STARVE_DPDT * (L48.K_CAL_BMI0 - L48.K_BMI_DEATH)   # K.drain.STARVE_DBMI
K_BERIBERI_DEATH_H = L48.K_BERIBERI_DEATH_H
MASK_STARVE = 1                          # 2^(STARVATION - 1)
MASK_STARVE_BERI = 5                     # starvation and beriberi (code 3: 2^2)
CREATION_BODY = (52.02, 13.005)          # x481-20261020-070821 start.json body lm, fm (the fresh record's creation body)

# ---- the tolerances (named before any run)
EQ_TOL = 1e-9
LINE_TOL_REL = 0.01
LINE_MIN_ROWS = 30
RATE_TOL_REL = 0.01
COMBINE_TOL = 1e-9                       # on the 100 scale: the record's doubles read back exactly (x481: residual 0.0)
COMBINE_SEP = 10.0                       # the Add fold must part from the product by 10 x COMBINE_TOL on some row
COMBINE_MIN_ROWS = 20
TRACK_TOL = 5e-4                         # about 45 x x481's float32 health spread on its target (1.1e-5)
F1, F3 = L48.F1, L48.F3


def _const(v):
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return v.pattern if hasattr(v, "pattern") else v


CONSTANTS = {k: _const(v) for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and k not in ("HERE", "REPO") and isinstance(v, (int, float, str, bool, tuple, dict))}

num = X.num
g = L47.g
ring_age = L48.ring_age
first_index = L48.first_index


def load_prerun(path=None):
    return L48.load_prerun(path or os.path.join(REPO, PRERUN_FILE))


def r_hunger(day_min):
    return L48.r_hunger(day_min)


# ================================================================ x483: the options file and the reads (pure)
def grade_ini(seeded):
    """INI: the seeded file's NR block holds DeathPace = PACE_SET and HealthCombine = COMBINE_SET."""
    obs = {"seeded_nr_block": seeded}
    if not isinstance(seeded, dict):
        return "unmeasured", obs
    ok = L47.same_number(seeded.get("DeathPace"), PACE_SET) and L47.same_number(seeded.get("HealthCombine"),
                                                                                 COMBINE_SET)
    return ("as_predicted" if ok else "falsified"), obs


def take_reads(ask, nodes, tag, read_sets, plan=None):
    """One read set: every side's reads (READ_PLAN), each a lua.global reply, at read_sets[tag][side][name]; a side
    whose read timed out is not asked again in this set (its later reads record `skipped`, unanswered like the timeout)."""
    rs = read_sets.setdefault(tag, {})
    for side, names in (plan or READ_PLAN).items():
        node = nodes.get(side)
        row = rs.setdefault(side, {})
        wedged = None
        for nm in names:
            if node is None:
                row[nm] = {"error": "no node"}
            elif wedged is not None:
                row[nm] = {"error": f"skipped: {wedged}"}
            else:
                try:
                    row[nm] = ask(node, "lua.global", nm, timeout=15)
                except Exception as e:             # noqa: BLE001 - recorded
                    row[nm] = {"error": f"{type(e).__name__}: {e}"}
                err = row[nm].get("error") if isinstance(row[nm], dict) else None
                if err and "Timeout" in str(err):
                    wedged = f"the side timed out on {nm} earlier in this set"
    return rs


def grade_pair(read_sets, side, pace_name, combine_name):
    """Both leaves on one side in every read set: falsified on any answered off value, unmeasured unless every read
    answered, else as_predicted."""
    vp, op = L47.grade_option(L47.collect(read_sets, side, pace_name), PACE_SET)
    vc, oc = L47.grade_option(L47.collect(read_sets, side, combine_name), COMBINE_SET)
    obs = {"side": side, pace_name: op, combine_name: oc}
    if "falsified" in (vp, vc):
        return "falsified", obs
    if "unmeasured" in (vp, vc) or not op["n"] or not oc["n"]:
        return "unmeasured", obs
    return "as_predicted", obs


def grade_mod_read(read_sets):
    """MOD_READ: the server's polled options and K.drain.OPT read PACE_SET and COMBINE_SET in every read set."""
    v1, o1 = grade_pair(read_sets, SRV, MOD_PACE_G, MOD_COMBINE_G)
    v2, o2 = grade_pair(read_sets, SRV, OPT_PACE_G, OPT_COMBINE_G)
    obs = {"options": o1, "opt": o2}
    if "falsified" in (v1, v2):
        return "falsified", obs
    if "unmeasured" in (v1, v2):
        return "unmeasured", obs
    return "as_predicted", obs


def client_copies(read_sets):
    """The reading: each client's NutritionRevamp.server.options copy at the end, beside the declared defaults it is
    predicted to keep (the poll is server-gated)."""
    out = {"predicted": {MOD_PACE_G: PACE_DEFAULT, MOD_COMBINE_G: COMBINE_DEFAULT}}
    for s in (ADMIN, BOB):
        out[s] = {n: L47.read_value(g(read_sets, "end", s, n))[1] for n in (MOD_PACE_G, MOD_COMBINE_G)}
    return out


def grade_x483(xs, out, read_sets):
    bob_started = g(out, "bob", "start_wall") is not None
    xs.grade("Z", *G.grade_z(out), "a mod error line in the server log, or admin parked in the debugger")
    xs.grade("INI", *grade_ini(out.get("sandbox_seeded")),
             "the seeded options file lacks NR.DeathPace = 2 or NR.HealthCombine = 3")
    for name, side in (("OPT_SERVER", SRV), ("OPT_ADMIN", ADMIN), ("OPT_BOB", BOB)):
        xs.grade(name, *grade_pair(read_sets, side, SERVER_PACE_G, SERVER_COMBINE_G),
                 f"SandboxVars.NR.DeathPace or HealthCombine reads another value on {side}")
    xs.grade("MOD_READ", *grade_mod_read(read_sets),
             "the server's polled options or K.drain.OPT read another value")
    jo = L47.join_obs(out, read_sets, bob_started)
    xs.grade("JOIN", *L47.grade_join(jo),
             "bob or admin not ready, a version or players read off, an Anti-cheat or mismatch line")
    out["readings"]["client_server_options"] = client_copies(read_sets)
    out["readings"]["server_opt_dayMin"] = L47.read_value(g(read_sets, "end", SRV, OPT_DAYMIN_G))[1]
    out["readings"]["server_readAt"] = L47.read_value(g(read_sets, "end", SRV,
                                                        "NutritionRevamp.server.options.readAt"))[1]


# ================================================================ x484: the grades (pure)
def line_span(rows, i_on, i_end=None):
    """The starvation-alone rows from the onset row to i_end (excluded), each with the row before it."""
    if i_on is None:
        return []
    out = []
    for i in range(max(i_on, 1), len(rows) if i_end is None else min(i_end, len(rows))):
        r = rows[i]
        if r.get("drain.active") is True and same_mask(r, MASK_STARVE) and num(r.get(F1)) is not None \
                and num(r.get("drain.target")) is not None and ring_age(rows[i - 1]) is not None:
            out.append((rows[i - 1], r))
    return out


def same_mask(r, m):
    v = num(r.get("drain.mask"))
    return v is not None and abs(v - m) < 0.5


def grade_line(rows, i_on, i_end=None):
    """LINE: frac.1 = 1 - pS and target = 100 x frac.1 on each starvation row, bRate the calibrated STARVE_DBMI, and the
    target's slope against the drain's age within LINE_TOL_REL of 100 x STARVE_DBMI / (bmi0 - 12) a game hour."""
    span = line_span(rows, i_on, i_end)
    if len(span) < LINE_MIN_ROWS:
        return "unmeasured", {"why": f"{len(span)} starvation row(s), under {LINE_MIN_ROWS}"}
    bmi0 = num(span[0][1].get("drain.bmi0"))
    if bmi0 is None or not bmi0 > L48.K_BMI_DEATH:
        return "unmeasured", {"why": "no onset BMI over the death BMI", "bmi0": bmi0}
    off = []
    for prev, r in span:
        f1, t, ps, br = num(r.get(F1)), num(r.get("drain.target")), num(r.get("drain.pS")), num(r.get("drain.bRate"))
        bad = []
        if ps is None or abs(f1 - (1.0 - ps)) > EQ_TOL:
            bad.append("frac.1 != 1 - pS")
        if abs(t - 100.0 * f1) > EQ_TOL * 100.0:
            bad.append("target != 100 x frac.1")
        if br is None or abs(br - K_STARVE_DBMI) > EQ_TOL * K_STARVE_DBMI:
            bad.append("bRate != STARVE_DBMI")
        if not L48.same(r.get("drain.bmi0"), bmi0):
            bad.append("bmi0 moved")
        if bad:
            off.append({"s": r.get("s"), "why": bad, "frac1": f1, "pS": ps, "target": t, "bRate": br})
    slope = G.fit_slope([(ring_age(prev), num(r["drain.target"])) for prev, r in span])
    want = -100.0 * K_STARVE_DBMI / (bmi0 - L48.K_BMI_DEATH)
    rel = abs(slope - want) / abs(want) if slope is not None else math.inf
    obs = {"n": len(span), "s0": span[0][1].get("s"), "s1": span[-1][1].get("s"), "bmi0": bmi0, "slope_h": slope,
           "want_h": want, "rel": rel, "tol_rel": LINE_TOL_REL, "line_rate_day": -want * 24.0,
           "n_off": len(off), "off": off[:10], "target0": num(span[0][1]["drain.target"]),
           "target1": num(span[-1][1]["drain.target"])}
    return ("as_predicted" if rel <= LINE_TOL_REL and not off else "falsified"), obs


def grade_rate(rows):
    """RATE (R1-5): every row with starvation active at least vanilla's level-4 rate a day; the starvation rows at the larger of
    that and the line's own; the starvation-and-beriberi rows at that plus beriberi's line."""
    under, off, n1, n5, n = [], [], 0, 0, 0
    beri = 100.0 * 24.0 / K_BERIBERI_DEATH_H
    for r in rows:
        rate, dm = num(r.get("drain.rate")), num(r.get(L48.OPT_DAYMIN))
        if r.get("drain.active") is not True or rate is None or dm is None:
            continue
        n += 1
        floor = r_hunger(dm) * 24.0
        if int(round(num(r.get("drain.mask")) or 0)) & MASK_STARVE and rate < floor * (1.0 - EQ_TOL):
            under.append({"s": r.get("s"), "rate": rate, "floor": floor})
        bmi0 = num(r.get("drain.bmi0"))
        line = 100.0 * 24.0 * K_STARVE_DBMI / (bmi0 - L48.K_BMI_DEATH) if bmi0 and bmi0 > L48.K_BMI_DEATH else 0.0
        want = None
        if same_mask(r, MASK_STARVE):
            n1 += 1
            want = max(floor, line)
        elif same_mask(r, MASK_STARVE_BERI):
            n5 += 1
            want = max(floor, line) + beri
        if want is not None and abs(rate - want) > RATE_TOL_REL * want:
            off.append({"s": r.get("s"), "rate": rate, "want": want, "mask": r.get("drain.mask")})
    obs = {"n": n, "n_starve": n1, "n_starve_beri": n5, "floor_day": r_hunger(DAY_MIN) * 24.0,
           "beri_day": beri, "under": under[:10], "n_under": len(under), "off": off[:10], "n_off": len(off),
           "tol_rel": RATE_TOL_REL}
    if under or off:
        return "falsified", obs
    if not n1 or not n5:
        return "unmeasured", dict(obs, why="no starvation row or no starvation-and-beriberi row")
    return "as_predicted", obs


def grade_track(rows, i_on):
    """TRACK: every active row after the onset row has |health - drain.target| <= TRACK_TOL."""
    if i_on is None:
        return "unmeasured", {"why": "no onset row"}
    pts = [(r.get("s"), num(r.get("health")), num(r.get("drain.target"))) for r in rows[i_on + 1:]
           if r.get("drain.active") is True]
    pts = [(s, h, t) for s, h, t in pts if h is not None and t is not None]
    if len(pts) < LINE_MIN_ROWS:
        return "unmeasured", {"why": f"{len(pts)} active row(s) with health and a target, under {LINE_MIN_ROWS}"}
    gaps = [(abs(h - t), s, h, t) for s, h, t in pts]
    worst = max(gaps)
    off = [{"s": s, "health": h, "target": t, "gap": d} for d, s, h, t in gaps if d > TRACK_TOL]
    obs = {"n": len(pts), "max_gap": worst[0], "worst_s": worst[1], "tol": TRACK_TOL, "n_off": len(off),
           "off": off[:10]}
    return ("falsified" if off else "as_predicted"), obs


def grade_combine(rows, after_age, combine=2):
    """COMBINE: every row after the write with both fractions reads 100 x (frac.1 x frac.3) within COMBINE_TOL and the
    polled combine; measured only when the Add fold parts from the product by COMBINE_SEP x COMBINE_TOL on some row."""
    if after_age is None:
        return "unmeasured", {"why": "no thiamine write"}
    both = [r for r in rows if (ring_age(r) or -1) > after_age and num(r.get(F1)) is not None
            and num(r.get(F3)) is not None and same_mask(r, MASK_STARVE_BERI)]
    n_other = sum(1 for r in rows if (ring_age(r) or -1) > after_age and num(r.get(F1)) is not None
                  and num(r.get(F3)) is not None and not same_mask(r, MASK_STARVE_BERI))
    if len(both) < COMBINE_MIN_ROWS:
        return "unmeasured", {"why": f"{len(both)} row(s) with both fractions, under {COMBINE_MIN_ROWS}"}
    bad, sep_add, sep_worst = [], 0.0, 0.0
    for r in both:
        f1, f3 = num(r[F1]), num(r[F3])
        want = 100.0 * max(0.0, f1 * f3)
        t = num(r.get("drain.target"))
        sep_add = max(sep_add, abs(100.0 * max(0.0, f1 - (1.0 - f3)) - want))
        sep_worst = max(sep_worst, abs(100.0 * min(f1, f3) - want))
        if t is None or abs(t - want) > COMBINE_TOL or not L48.same(r.get(L48.OPT_COMBINE), combine):
            bad.append({"s": r.get("s"), "target": t, "want": want, "combine": r.get(L48.OPT_COMBINE)})
    obs = {"n": len(both), "n_other_mask": n_other, "n_off": len(bad), "off": bad[:10], "sep_add_max": sep_add,
           "sep_worst_max": sep_worst,
           "tol": COMBINE_TOL, "sep_needed": COMBINE_SEP * COMBINE_TOL}
    if bad:
        return "falsified", obs
    if sep_add <= COMBINE_SEP * COMBINE_TOL:
        return "unmeasured", dict(obs, why="the Add fold never parts from the product: Multiply and Add inseparable")
    return "as_predicted", obs


# ================================================================ the pre-boot checks (offline; tested)
def profile_doc_checks(name, doc, text=""):
    """A profile's TOML against PROFILES[name]: its header naming its own file, its fixture and clients, sleep off,
    PZTestKit and the staged upload copy, Nutrition false, its day length, the [sandbox.NR] block of DeathPace and
    HealthCombine alone at the session's values, a version verify row on every side it attaches, no client override."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = sorted(v.get("side") for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version")
    want_sides = sorted(["server", "client"] + (["client:bob"] if BOB in spec["clients"] else []))
    return {"known_profile": True,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture": doc.get("fixture") == spec["fixture"],
            "clients": doc.get("clients", [ADMIN]) == spec["clients"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths.get(NR) == STAGE_MOD,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == spec["day_length"],
            "nr_block": sb.get("NR") == {"DeathPace": spec["pace"], "HealthCombine": spec["combine"]},
            "verify_version": vr == want_sides,
            "no_override": "client_overrides" not in doc,
            "server_timeout": srv.get("timeout") == SERVER_TIMEOUT_S}


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def preboot(key, driver_file, repo=REPO, compute=None):
    """The driver's file names its session (CLAUDE.md s5); no artifact of the prefix committed; the profile's TOML;
    STAGED_FROM mod/'s last commit; x484 also the harness markers, the fixture fresh and the prerun current.
    Returns (checks, ok)."""
    import tomllib
    import glob
    s = SESSIONS.get(key) or {}
    c = {"key": key in SESSIONS, "driver_file": os.path.basename(driver_file) == s.get("driver"),
         "driver_prefix": os.path.basename(driver_file).startswith(key + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", key + "-*"))
    head = mod_head(repo)
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", s.get("profile", "?") + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(s.get("profile"), tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    skip = ("profile_checks", "harness_found", "fixture", "prerun")
    if key == "x484":
        found, ok = L48.harness_markers_ok(repo)
        c["harness_markers"] = ok
        c["harness_found"] = found
        fr = L48.fixture_fresh(repo)
        c["fixture"] = fr
        c["fixture_fresh"] = fr["fresh"]
        if compute is None:
            import x48b_prerun as PR
            compute = PR.compute
        pr = L48.prerun_current(key, repo, compute, committed=load_prerun(os.path.join(repo, PRERUN_FILE)))
        c["prerun"] = pr
        c["prerun_current"] = pr["ok"]
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO):
    """x45g_lib's gate at this lib's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


# ================================================================ x484: the session
class Sess(L48.Sess):
    """x484's phases over an xlib.Xs, on x48_lib.Sess (x481's seed, hold and thiamine) with this lib's schedule."""

    def __init__(self, xs, key, run_dir=None, prerun=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.prof = PROFILES[self.spec["profile"]]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages, self.eats, self.pairs, self.points, self.consts, self.drinks = [], [], [], [], [], []
        self.sets = self.out.setdefault("sets", [])
        self.sandbox = self.out.setdefault("sandbox_writes", [])
        self.polls = self.out.setdefault("death_polls", [])
        self.red0 = None
        self.dead = False
        self.P = prerun if prerun is not None else load_prerun().get(key, {})
        self.out["lib_x48b"] = LIB_FILE
        self.out["constants_x48b"] = dict(CONSTANTS)
        self.out["constants_x48_phases"] = {k: L48.CONSTANTS[k] for k in (
            "STARVE_ONSET_H", "SEED_LEAD_H", "THIAMINE_P", "SPEED_FAST", "ONSET_CAP_S", "BERI_CAP_S", "POLL_S",
            "REPLAY_TOL", "RING", "H1_NIL_OK", "BERI_GM", "BERI_F0_TOL", "ONSET_SLACK_H", "DAY_MIN")}
        self.out["prerun_x48b"] = self.P

    def phase_O(self):
        a = self.D["A"].get("onset_polled_age") or self.age("O_a0") or 0.0
        self.D["O"] = {"end": self.run_until(a + HOLD_H, SPEED_FAST, "O_hold")}

    def phase_P(self):
        a = self.age("P_a0") or 0.0
        self.D["P"] = {"end": self.run_until(a + POST_H, SPEED_FAST, "P_post")}

    def phases(self):
        return [("S", self.phase_S48), ("H", self.phase_H), ("W", self.phase_W48), ("A", self.phase_A),
                ("O", self.phase_O), ("B", self.phase_B), ("P", self.phase_P), ("C", self.restore_clock),
                ("R", self.phase_R)]

    def closing_names(self):
        return ("C", "R")

    def grade_x484(self, rows, arms):
        i_on = L48.onset_index(rows, num(g(self.D, "A", "seed_age")))
        a_p = num(g(self.D, "B", "set_p", "age"))
        i_b = first_index(rows, lambda r: (ring_age(r) or -1) > a_p) if a_p is not None else None
        self._g("LINE", grade_line(rows, i_on, i_b),
                "a starvation row off the line (frac.1, target or bRate), or the target's slope off the line's by "
                "more than LINE_TOL_REL")
        self._g("RATE", grade_rate(rows), "an active row's rate under vanilla's level-4 rate, or off its sum")
        self._g("TRACK", grade_track(rows, i_on), "an active row's health more than TRACK_TOL off its target")
        self._g("BERI_ON", L48.grade_beri(rows, a_p), "no clinical grade and beriberi fraction within BERI_GM")
        self._g("COMBINE", grade_combine(rows, a_p, self.prof["combine"]), "a target off 100 x (f1 x f3)")


# ================================================================ the boots
def _provenance(out, git_say, git_dirty):
    out.update({
        "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", G.LUA_DIR),
        "harness_lua_dirty": git_dirty(G.LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "lib_x47_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x47_lib.py"),
        "lib_x48_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x48_lib.py"),
        "lib_x45g_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x45g_lib.py"),
        "prerun_commit": git_say("log", "-1", "--format=%h", "--", PRERUN_FILE),
        "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
    })


def _gates(xs, out, prof, run_dir, lint_paths, lint_list):
    """The refusals before the boot: doctor, a dirty harness, the staged gate and its verify rows, free memory, the
    layout lint (each refuses the session, CLAUDE.md s5)."""
    if not out["doctor_clean"]:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    mg["version_is_release"] = mg.get("staged_version") == STAGED_VERSION
    if not (mg["ok"] and mg["verify_rows_match"] and mg["version_is_release"]):
        xs.refuse(f"the staged copy does not match the pinned commit, the verify rows or {STAGED_VERSION}: {mg!r}; "
                  "not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(lint_list)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")


def _summary(out, run_id, run_dir):
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"), "stop_reason": out.get("stop_reason"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


def main(key, driver_file, session_text, pred, budget_s):
    """One boot of the session's profile; x483 by main_options, x484 by main_line."""
    pre, ok = preboot(key, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    return (main_options if key == "x483" else main_line)(key, driver_file, session_text, pred, budget_s, pre)


def _start(key, driver_file, session_text, pred, budget_s, pre, user):
    from _common import ask, doctor, git_dirty, git_say            # noqa: E402
    from pzt import fixture as fx, profile                         # noqa: E402
    from pzt.bus import resolve_side                               # noqa: E402
    from pzt.paths import new_run_dir                              # noqa: E402
    from pzt.session import Timeline                               # noqa: E402
    s = SESSIONS[key]
    prof = profile.load(s["profile"])
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(key)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=user)
    xs.path = os.path.join(run_dir, s["artifact"])
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "session": session_text, "driver": os.path.basename(driver_file),
        "lib": LIB_FILE, "user": user, "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": pred, "constants": CONSTANTS, "meta": {"budget_s": budget_s},
    })
    _provenance(out, git_say, git_dirty)
    return s, prof, rec_fx, run_id, run_dir, tl, clients, started, holder, out, xs


def main_options(key, driver_file, session_text, pred, budget_s, pre):
    """x483: x47_lib.main's x471 path at this lib's options, reads and staged copy."""
    from _common import ask, hard_kill                             # noqa: E402
    from pzt import profile                                        # noqa: E402
    from pzt.harness import lint_paths                             # noqa: E402
    from pzt.session import attach_clients, make_client, make_server, override_kw, teardown, verify   # noqa: E402

    s, prof, rec_fx, run_id, run_dir, tl, clients, started, holder, out, xs = _start(
        key, driver_file, session_text, pred, budget_s, pre, ADMIN)
    _gates(xs, out, prof, run_dir, lint_paths, profile.lint_sources(prof, prof.sources))
    server, bob = None, None
    read_sets = out.setdefault("read_sets", {})
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        sbp = os.path.join(run_dir, *SANDBOX_REL)
        out["sandbox_seeded"] = L47.sandbox_nr_block(L47.read_text(sbp))
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        out["build"] = server.build
        tl.mark("server_started", pid=server.proc.pid)
        out["sandbox_after_start"] = L47.sandbox_nr_block(L47.read_text(sbp))
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[ADMIN], started=started))
        out["admin_ready_wall"] = xs.wall()
        if xs.wall() > budget_s - OBS_S - CLOSE_RESERVE_S:
            out["budget_stop"] = {"phase": "bob", "wall": xs.wall(),
                                  "why": f"admin ready at {xs.wall()} s: bob's {OBS_S} s watch would end past the budget"}
            raise RuntimeError("bob not started: " + out["budget_stop"]["why"])
        bob, restored = make_client(run_dir, BOB, server, rec_fx, safemode=prof.safemode, launcher=prof.launcher,
                                    **override_kw(prof, BOB, server))
        started.append(bob)
        out["bob_restored"] = restored
        out["bob_debug"] = bob.debug
        out["bob_mod_source"] = os.path.relpath(bob.mod_sources.get(NR, ""), REPO).replace(os.sep, "/")
        out["deployed"] = L47.deployed_copies(run_dir, "common/media/lua/server/NR_Server_Options.lua")
        xs.mem("before_bob")
        xs.persist()

        def on_ready():
            clients[BOB] = bob
            time.sleep(READ_SETTLE_S)
            take_reads(ask, {SRV: server, ADMIN: clients.get(ADMIN), BOB: bob}, "after_ready", read_sets)
            out["verify"] = verify(prof, server, clients, tl)
            xs.persist()
            return HOLD_S

        xs.cur_phase = "bob"
        ready = L47.watch_bob(xs, bob, on_ready, OBS_S)
        if ready and bob.alive:
            take_reads(ask, {SRV: server, ADMIN: clients.get(ADMIN), BOB: bob}, "end", read_sets)
        out["players_end"] = ask(server, "players", "", timeout=15)
        out["admin_tk_at_end"] = ask(clients.get(ADMIN), "lua.global", "TK.version", timeout=15)
        xs.mem("end")
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)
        log_copies = {}

        def read_logs():
            L = out["logs"] = {"patterns": {"log": L47.LOG_RX.pattern, "mismatch": L47.MISMATCH_RX.pattern}}
            if server is None:
                return
            outs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
            L["server"], L["server_echo_excluded"] = L47.grep_lines(outs, L47.LOG_RX)
            L["mod_error"] = [ln for ln in L["server"] if L47.MOD_ERR_RX.search(ln)][:40]
            L["server_mismatch"], _ = L47.grep_lines(outs, L47.MISMATCH_RX)
            files = L47.find_logs(run_dir)
            L["files"] = {k: (os.path.relpath(v, run_dir).replace(os.sep, "/") if v else None) for k, v in files.items()}
            L["user"] = L47.user_log_facts(L47.read_text(files["server_user"]) if files["server_user"] else None)
            L["bob_connections"] = L47.conn_facts(L47.read_text(files["bob_connections"])
                                                  if files["bob_connections"] else None)
            for k, v in files.items():
                if v:
                    log_copies[("bob-" if k.startswith("bob") else "server-") + os.path.basename(v)] = v
            for c in every:
                lines, _ = X.grep_noecho(c.console, L47.LOG_RX, 80, L47.ECHO_RX, L47.NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines
                L.setdefault("client_mismatch", {})[getattr(c, "username", "?")] = \
                    X.grep_noecho(c.console, L47.MISMATCH_RX, 40, L47.ECHO_RX, L47.NEVER_RX)[0]
            out["log_copies"] = {k: {"from": os.path.relpath(v, run_dir).replace(os.sep, "/"),
                                     "sha256": X.sha256_file(v)} for k, v in log_copies.items()}

        xs.finish(teardown, hard_kill, every, read_logs=read_logs,
                  grade_all=lambda: grade_x483(xs, out, read_sets))
        xs.mem("after")
        xs.persist()
        dest = xs.copy_artifacts(REPO, run_id, run_dir, s["artifact"])
        if dest:
            for nm, src in log_copies.items():
                try:
                    shutil.copyfile(src, os.path.join(dest, nm))
                except OSError as e:
                    print(f"could not copy {nm}: {type(e).__name__}: {e}")
    _summary(out, run_id, run_dir)
    return out


def main_line(key, driver_file, session_text, pred, budget_s, pre):
    """x484: x48_lib.main at this lib's session, staged copy and checks."""
    from _common import hard_kill                                  # noqa: E402
    from pzt.harness import lint_paths                             # noqa: E402
    from pzt.session import attach_clients, make_server, teardown, verify   # noqa: E402

    s, prof, rec_fx, run_id, run_dir, tl, clients, started, holder, out, xs = _start(
        key, driver_file, session_text, pred, budget_s, pre, USER)
    S = Sess(xs, key, run_dir=run_dir)
    _gates(xs, out, prof, run_dir, lint_paths, prof.sources)
    server = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        tl.mark("server_started", pid=server.proc.pid)
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(L48.HARNESS_MARKERS), L48.HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, okm):
            pass
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            S.body_run(S.phases())
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": L48.LOG_RX.pattern}}
            if server is not None:
                logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
                L["server"], L["server_echo_excluded"] = [], 0
                for lp in logs:
                    hits, skipped = X.grep_noecho(lp, L48.LOG_RX, 300, G.ECHO_RX, G.NEVER_RX)
                    L["server"] += hits
                    L["server_echo_excluded"] += skipped
                L["mod_error"] = [ln for ln in L["server"] if L48.MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, L48.LOG_RX, 80, G.ECHO_RX, G.NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, s["artifact"])
    _summary(out, run_id, run_dir)
    return out
