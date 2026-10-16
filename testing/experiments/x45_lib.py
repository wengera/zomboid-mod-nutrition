"""x45_lib -- the session engine of Plan 15 Task 2's live spike (x451): can vanilla's shared severe-moodle constant
`BodyDamage.healthReductionFromSevereBadMoodles` be set to 0 from server Lua, which of vanilla's drains does that switch
off, and does the value survive a reload (the plan's option B, before Task 5 builds it; jar-checks.md Check 3).

Started from x44_guide_lib.py (frozen with x441-x447): its pre-boot checks, its staged-copy gate and its harness-marker
check are copied here and cut to this one session, on testing/experiments/xlib.py (the bus step, the wall budget, the
grade recorder, the abort/teardown/copy skeleton). The vanilla model, the replay and the ring are not used.

THE ROUTE. The constant is a field of each character's BodyDamage, set to 0.0165 in its constructor, with a public
getter and setter (#2355; jar `BodyDamage.<init> @91-@93 L79`); BodyDamage is an exposed class (the regeneration
setters are written the same way, #2354). The harness has no typed command for it; `witness.chain` walks
zero- or one-literal-argument calls from the player under pcall, so the driver writes the constant with
`witness.chain admin getBodyDamage.setHealthReductionFromSevereBadMoodles(<v>)` (the void return reads "nil") and reads
it with `witness.chain admin getBodyDamage.getHealthReductionFromSevereBadMoodles`. That is the route a mod's server
Lua takes: `player:getBodyDamage():setHealthReductionFromSevereBadMoodles(v)`. No harness change is needed.

THE MOD'S MINUTE WRITE. The mod writes HUNGER, THIRST and FATIGUE once a game minute and caps HUNGER at 0.69 and THIRST
at 0.83, under vanilla's level 4 (NR_Kernel_Hybrid.lua hungerCap, thirstCap), and it zeroed vanilla's rise rates at
boot (Mode 1). Its writer reads `NutritionRevamp.server.writer.mode` every minute (NR_Server_Writer.lua `inp.mode =
W.mode`) and writes none of the three when it is not 1. The driver sets that field to 2 with `lua.setpath` for the
spike, so a HUNGER and THIRST written above level 4 hold (the vanilla rates stay zeroed), and restores it from the value
it read before (CLAUDE.md s5). The mod's own cap therefore never meets the spike: it is switched off, not raced.
Why both HUNGER and THIRST: the THIRST-4 term is five times the HUNGRY-4 term, so the control reads cleanly in 20 s.

THE INSTRUMENTS. Overall health (health.get), the clock and the hunger and thirst moodles (stats.get), the SICK and
BLEEDING moodles (moodle.level), and the OnPlayerGetDamage tag counts of the harness listener (fall.probe <user> with
no height: it installs the listener once and replies the per-tag counts; the engine fires the event once per nonzero
term per tick, with the tags HUNGRY, THIRST, SICK, BLEEDING, HEAVYLOAD, #2357). A term multiplied by a zero constant is
zero and fires nothing, so a tag count that stands still names the term the constant carries.

THE PHASES (one boot of x45-mod, then a reuse boot of the same run folder for E):
  S  the start reads: the constant (expect 0.0165), the writer mode (expect 1), health, the auto-drink bracket; the
     food-heal timer set 0 (foodtimer.set) so the Well Fed heal adds nothing; the listener installed.
  A  the control: HUNGER 0.80 and THIRST 0.90 written (stats.set), the constant left alone. One window: health falls at
     red x M_H x (1/50 + 1/10) a game hour (#0516, #0518; M_H is the sum of the multiplier over a game hour, 1800 at
     DayLength 1: #0518's 17.82 THIRST-4 an hour at DayLength 4 is red/10 x 10800, scaled by 15/90). Then LW_A: five
     Nutrition.setWeight(30) calls (nutrition.set weight 30) bracketed by two health reads: each call clamps the weight
     to 35 and costs red x mult (#3881).
  B  the constant set to 0 (read back 0). One window: health holds, the HUNGRY and THIRST tags stand still. Then LW_B:
     the same five calls cost nothing.
  C1 the constant still 0; FOOD_SICKNESS written 95 (stats.setany) so SICK reads 4 with FOOD_SICKNESS above
     ZOMBIE_INFECTION (#2356, #3130). One window: health holds, the SICK tag stands still.
  C2 the constant still 0; four parts bleeding (bodypart.set bleedingTime 5 and bleeding true on parts 0-3) so BLEEDING
     reads 4 (Moodle.Update: the level is the count of bleeding parts, capped at 4). One window: health still falls,
     through the per-part wound term (#2364), which does not read the constant and fires the BLEEDING tag itself; the
     SICK, HUNGRY and THIRST tags stand still.
  D  the constant restored from the value S read. One window with every condition still on: health falls faster than
     in C2 by red x M_H x (the sum of the active terms' factors: HUNGRY 4 1/50, THIRST 4 1/10, SICK 4 1, BLEEDING 4 1),
     and the HUNGRY, THIRST and SICK tags count again.
  K  the cleanup and E's marker: the constant set to a marker 0.0042, the bleeding, FOOD_SICKNESS, HUNGER and THIRST
     cleared, the writer mode restored, a player modData marker written (moddata.set), health read.
  E  after the server's quit and a reuse boot of the same saved world: the constant read again. The jar finds no save
     or load of it ([J1.5]), so it should read the constructor's 0.0165, not the marker; the modData marker (or a health
     below 99 near K's) shows the character is the saved one.

THE GRADES (pure; each has a failing case in testing/tests/test_x45_lib.py; a grade on no valid window is unmeasured,
never as_predicted; every tolerance is named here, before the run):
  ROUTE  the setter call answers ok, the getter reads the value written (0 in B, the restore in D, the marker in K).
  A      the window's drain rate within A_TOL_REL of the prediction, HUNGRY and THIRST at level 4 at both ends.
  LW_A   the bracket's excess drop over the A slope within LW_A_BAND of 5 x red x mult.
  B      |health change| at most HOLD_TOL, the HUNGRY and THIRST tags unchanged, both moodles at 4 at both ends.
  LW_B   |excess| at most HOLD_TOL.
  C1     |health change| at most HOLD_TOL, the SICK tag unchanged, SICK at 4 at both ends.
  C2     health falls by at least BLEED_MIN_DROP, the BLEEDING tag counts, the SICK, HUNGRY and THIRST tags unchanged,
         BLEEDING at 4 at both ends.
  D      the D rate minus the C2 rate within D_TOL_REL of the prediction; the HUNGRY, THIRST and SICK tags count.
  E      the constant after the reload equals the default within CONST_EPS and is not the marker, and the character is
         the saved one.

FROZEN WITH ITS FIRST RUN: once x451 has run, this file is never edited (CLAUDE.md s5).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402

REPO = X.REPO
SRV = X.SRV
LIB_FILE = "x45_lib.py"
NR = "NutritionRevamp"
USER = "admin"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan15-x451"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "af2a2d20"                 # the commit the staged copy was made from (mod/ last touched at 2649c170)
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
MANIFEST_NAME = "MANIFEST.json"
MIN_FREE_GB = 12.0
MOD_DAY_LENGTH = 1

SESSIONS = {
    "S1": {"prefix": "x451", "profile": "x45-mod", "artifact": "capspike.json"},
}

# ---- the constant and its route (jar-checks.md Check 3; #2355, #2356)
CONST_DEFAULT = 0.0165
CONST_MARKER = 0.0042                    # K's value, distinct from 0 and the default, read again after the reload
CONST_EPS = 1e-6
GET_CHAIN = "getBodyDamage.getHealthReductionFromSevereBadMoodles"
SET_CHAIN = "getBodyDamage.setHealthReductionFromSevereBadMoodles({v})"
MODE_PATH = "NutritionRevamp.server.writer.mode"
MODE_SPIKE = 2

# ---- the drain arithmetic (#0516, #0518, #2356)
M_H = {1: 1800.0, 4: 10800.0}            # the multiplier's sum over a game hour by DayLength (#0518, scaled by real minutes)
K_HUNGRY = 1.0 / 50.0
K_THIRST = 1.0 / 10.0
K_SICK = 1.0
K_BLEEDING = 1.0

# ---- the writes
HUNGER_W = 0.80                          # HUNGRY 4 above 0.70 (#0495)
THIRST_W = 0.90                          # THIRST 4 above 0.84 (#0509)
FOOD_SICK_W = 95.0                       # SICK 4 above 0.90 on the hundredth scale (#3130)
BLEED_PARTS = (0, 1, 2, 3)               # Hand_L, Hand_R, ForeArm_L, ForeArm_R: four parts bleeding, BLEEDING 4
BLEED_TIME = 5.0
LW_WEIGHT = 30.0                         # under the 35 kg floor (#3881)
LW_CALLS = 5
CLEAR_HUNGER = 0.10
CLEAR_THIRST = 0.10
MODDATA_KEY = "x451mark"
MODDATA_VAL = "boot1"

# ---- the windows and the tolerances (named before the run)
SETTLE_S = 1.5
WIN_A_S = 20.0
WIN_B_S = 15.0
WIN_C1_S = 12.0
WIN_C2_S = 12.0
WIN_D_S = 8.0
A_TOL_REL = 0.10
D_TOL_REL = 0.15
HOLD_TOL = 0.02                          # health units over a hold window (A's drain is about 1.9 over 20 s)
BLEED_MIN_DROP = 0.1
LW_A_BAND = (0.5, 1.5)
SAVE_HEALTH_BAND = (-2.0, 10.0)          # E's health against K's: the regeneration across the reload adds a little
HEALTH_FLOOR = 30.0                      # a window that ends below it ends the drain phases
E_START_CAP_S = 330.0                    # E is skipped when boot 1 ended later than this (the session's wall budget)
POLL_S = 0.25

TAGS = ("HUNGRY", "THIRST", "SICK", "BLEEDING", "HEAVYLOAD", "POISON")

HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "witness.chain", "health.get", "stats.get", "stats.set", "stats.setany", "moodle.level", "fall.probe",
        "bodypart.set", "nutrition.set", "foodtimer.set", "lua.setpath", "moddata.set", "autodrink.probe",
        "players")),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("time.snapshot", "lua.read")),
}
ECHO_RX = re.compile(r"PZTK: ")
NEVER_RX = re.compile(r"(?!x)x")
LOG_RX = re.compile(r"NutritionRevamp|NR_|LuaError|STACK TRACE|lua error|attempted index|tried to call nil", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")


# ================================================================ small readers (pure)
def num(v):
    return X.num(v)


def const_of(reply):
    """The constant off a witness.chain getter reply: its value string as a float, else None."""
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        return None
    return num(reply.get("value"))


def counts_of(reply):
    """The fall.probe reply's tag counts as a dict (an empty Lua table may encode as a list)."""
    c = reply.get("counts") if isinstance(reply, dict) else None
    if isinstance(c, dict):
        return {str(k): num(v) or 0 for k, v in c.items()}
    return {}


def tag_deltas(c0, c1):
    return {t: (c1.get(t, 0) or 0) - (c0.get(t, 0) or 0) for t in TAGS}


def mid(row):
    """A kept reply's wall midpoint (xlib.Xs.keep writes wall and wall_after)."""
    a, b = num(row.get("wall")), num(row.get("wall_after"))
    if a is None or b is None:
        return None
    return (a + b) / 2.0


def window_rate(w):
    """The window's drain: the health change between its two reads and the drain rate a game hour, the wall span
    converted by the game hours a wall second its two stats.get reads give. Positive rate = health falling."""
    h0, h1 = num(g(w, "h0", "overall")), num(g(w, "h1", "overall"))
    t0, t1 = mid(w.get("h0") or {}), mid(w.get("h1") or {})
    a0, a1 = num(g(w, "s0", "worldAge")), num(g(w, "s1", "worldAge"))
    u0, u1 = mid(w.get("s0") or {}), mid(w.get("s1") or {})
    r = {"dh": None, "dwall": None, "gh_per_s": None, "game_h": None, "rate_per_gh": None}
    if None in (h0, h1, t0, t1):
        return r
    r["dh"] = h1 - h0
    r["dwall"] = t1 - t0
    if None in (a0, a1, u0, u1) or u1 <= u0:
        return r
    r["gh_per_s"] = (a1 - a0) / (u1 - u0)
    r["game_h"] = r["dwall"] * r["gh_per_s"]
    if r["game_h"] > 0:
        r["rate_per_gh"] = -r["dh"] / r["game_h"]
    return r


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def levels_hold(w, want):
    """Every named moodle at level 4 at both ends of the window. `want` holds stats.get names (hungry, thirst) and
    moodle.level names (SICK, BLEEDING). Returns (ok, the levels read)."""
    seen = {}
    ok = True
    for end in ("0", "1"):
        for m in want:
            if m in ("hungry", "thirst"):
                lv = num(g(w, "s" + end, "moodles", m))
            else:
                lv = num(g(w, "lv" + end, m, "level"))
            seen[m + end] = lv
            if lv != 4:
                ok = False
    return ok, seen


# ================================================================ the grades (pure; each has a failing case)
def grade_route(set_reply, get_reply, want):
    """The setter answered ok and the getter reads the value written."""
    got = const_of(get_reply)
    ok_set = isinstance(set_reply, dict) and set_reply.get("ok") is True
    obs = {"set_ok": ok_set, "set_value": g(set_reply, "value"), "read": got, "want": want}
    if got is None:
        return "unmeasured", obs
    return ("as_predicted" if ok_set and abs(got - want) <= CONST_EPS else "falsified"), obs


def grade_control(w, red, day_length):
    """A: the drain rate within A_TOL_REL of red x M_H x (1/50 + 1/10), HUNGRY and THIRST at 4 at both ends."""
    r = window_rate(w)
    ok_lv, lv = levels_hold(w, ("hungry", "thirst"))
    pred = None if red is None else red * M_H[day_length] * (K_HUNGRY + K_THIRST)
    obs = dict(r, levels=lv, predicted_rate_per_gh=pred)
    if not ok_lv or r["rate_per_gh"] is None or pred is None:
        return "unmeasured", obs
    obs["rel_err"] = (r["rate_per_gh"] - pred) / pred
    return ("as_predicted" if abs(obs["rel_err"]) <= A_TOL_REL else "falsified"), obs


def grade_hold(w, want_levels, still_tags):
    """B and C1: the health change within HOLD_TOL and every named tag unchanged, the moodles at 4 at both ends."""
    r = window_rate(w)
    ok_lv, lv = levels_hold(w, want_levels)
    d = tag_deltas(counts_of(w.get("c0")), counts_of(w.get("c1")))
    obs = dict(r, levels=lv, tag_deltas=d, counts_read=bool(w.get("c0")) and bool(w.get("c1")))
    if not ok_lv or r["dh"] is None or not obs["counts_read"]:
        return "unmeasured", obs
    held = abs(r["dh"]) <= HOLD_TOL and all(d[t] == 0 for t in still_tags)
    return ("as_predicted" if held else "falsified"), obs


def grade_bleed(w, want_levels):
    """C2: health still falls (by BLEED_MIN_DROP or more) and the BLEEDING tag counts (the per-part term), while the
    SICK, HUNGRY and THIRST tags stand still."""
    r = window_rate(w)
    ok_lv, lv = levels_hold(w, want_levels)
    d = tag_deltas(counts_of(w.get("c0")), counts_of(w.get("c1")))
    obs = dict(r, levels=lv, tag_deltas=d)
    if not ok_lv or r["dh"] is None or not w.get("c0") or not w.get("c1"):
        return "unmeasured", obs
    ok = (r["dh"] <= -BLEED_MIN_DROP and d["BLEEDING"] > 0
          and d["SICK"] == 0 and d["HUNGRY"] == 0 and d["THIRST"] == 0)
    return ("as_predicted" if ok else "falsified"), obs


def active_factor(w):
    """The sum of the severe terms' factors active at the window's start (HUNGRY 4, THIRST 4, SICK 4, BLEEDING 4)."""
    k = 0.0
    if num(g(w, "s0", "moodles", "hungry")) == 4:
        k += K_HUNGRY
    if num(g(w, "s0", "moodles", "thirst")) == 4:
        k += K_THIRST
    if num(g(w, "lv0", "SICK", "level")) == 4:
        k += K_SICK
    if num(g(w, "lv0", "BLEEDING", "level")) == 4:
        k += K_BLEEDING
    return k


def grade_restore(wd, wc2, red, day_length):
    """D: the D rate minus the C2 rate within D_TOL_REL of red x M_H x the active factor; the HUNGRY, THIRST and SICK
    tags count again."""
    rd, rc = window_rate(wd), window_rate(wc2)
    d = tag_deltas(counts_of(wd.get("c0")), counts_of(wd.get("c1")))
    k = active_factor(wd)
    pred = None if red is None else red * M_H[day_length] * k
    obs = {"D": rd, "C2": rc, "active_factor": k, "predicted_excess_per_gh": pred, "tag_deltas": d}
    if rd["rate_per_gh"] is None or rc["rate_per_gh"] is None or not pred:
        return "unmeasured", obs
    obs["excess_per_gh"] = rd["rate_per_gh"] - rc["rate_per_gh"]
    obs["rel_err"] = (obs["excess_per_gh"] - pred) / pred
    ok = abs(obs["rel_err"]) <= D_TOL_REL and d["HUNGRY"] > 0 and d["THIRST"] > 0 and d["SICK"] > 0
    return ("as_predicted" if ok else "falsified"), obs


def lw_excess(br, slope_per_s):
    """A LOWWEIGHT bracket's drop beyond the window's drift: (h_before - h_after) - slope x the wall between them."""
    h0, h1 = num(g(br, "h0", "overall")), num(g(br, "h1", "overall"))
    t0, t1 = mid(br.get("h0") or {}), mid(br.get("h1") or {})
    if None in (h0, h1, t0, t1) or slope_per_s is None:
        return None
    return (h0 - h1) - slope_per_s * (t1 - t0)


def grade_lowweight(br, slope_per_s, red, expect_cost):
    """LW_A (expect_cost): the excess within LW_A_BAND of calls x red x mult (mult off the bracket's stats.get).
    LW_B: |excess| at most HOLD_TOL. A call whose weight did not read 35 after does not count."""
    ex = lw_excess(br, slope_per_s)
    mult = num(g(br, "s", "mult"))
    calls = [c for c in br.get("calls", []) if num(c.get("weight")) is not None and abs(num(c["weight"]) - 35.0) < 1e-6]
    obs = {"excess": ex, "slope_per_s": slope_per_s, "mult": mult, "calls_clamped": len(calls)}
    if ex is None or not calls:
        return "unmeasured", obs
    if not expect_cost:
        return ("as_predicted" if abs(ex) <= HOLD_TOL else "falsified"), obs
    if red is None or mult is None:
        return "unmeasured", obs
    pred = len(calls) * red * mult
    obs["predicted"] = pred
    obs["ratio"] = ex / pred if pred else None
    ok = obs["ratio"] is not None and LW_A_BAND[0] <= obs["ratio"] <= LW_A_BAND[1]
    return ("as_predicted" if ok else "falsified"), obs


def grade_persist(e):
    """E: after the reload the constant reads the default (not the marker), on the saved character (the modData marker,
    or a health under 99 within SAVE_HEALTH_BAND of K's)."""
    got = const_of(e.get("const"))
    md = g(e, "moddata", "value")
    marker = isinstance(md, dict) and md.get(MODDATA_KEY) == MODDATA_VAL
    hk, he = num(e.get("health_k")), num(g(e, "health", "overall"))
    by_health = (hk is not None and he is not None and he < 99.0
                 and SAVE_HEALTH_BAND[0] <= he - hk <= SAVE_HEALTH_BAND[1])
    obs = {"const_after": got, "marker_written": num(g(e, "marker_read")), "moddata_marker": marker,
           "health_k": hk, "health_after": he, "same_by_health": by_health}
    if got is None or not (marker or by_health):
        return "unmeasured", obs
    return ("as_predicted" if abs(got - CONST_DEFAULT) <= CONST_EPS else "falsified"), obs


# ================================================================ the pre-boot checks (offline; tested)
def harness_markers_ok(repo=REPO):
    found = {}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        found[fname] = {mk: (mk in text) for mk in HARNESS_MARKERS[fname]}
    return found, all(all(d.values()) for d in found.values())


def profile_doc_checks(name, doc, text=""):
    """The profile's TOML against the session: the fixture, the one admin client, PZTestKit and the staged copy, Nutrition
    false, DayLength 1, sleep off, two version verify rows, and its header line naming its own file."""
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = [m.get("path") for m in doc.get("mods") or [] if m.get("id") == NR]
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    ver = doc.get("verify") or []
    return {"named_profile": name == SESSIONS["S1"]["profile"],
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture_default": doc.get("fixture") == "default",
            "one_admin_client": doc.get("clients", ["admin"]) == ["admin"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths == [STAGE_MOD],
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == MOD_DAY_LENGTH,
            "verify_version": sum(1 for v in ver if v.get("args") == f"{NR}.version") >= 2}


def preboot(profile_name, prefix, driver_file, repo=REPO):
    """The driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact of the prefix committed; the
    profile's TOML; the harness markers in the repository. Returns (checks, ok)."""
    import tomllib
    spec = SESSIONS["S1"]
    c = {"prefix": prefix == spec["prefix"], "profile": profile_name == spec["profile"],
         "driver_file": os.path.basename(driver_file).startswith(prefix + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", prefix + "-*"))
    try:
        with open(os.path.join(repo, "testing", "profiles", profile_name + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(profile_name, tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    found, ok = harness_markers_ok(repo)
    c["harness_markers"] = ok
    c["harness_found"] = found
    good = all(v is True for k, v in c.items() if k not in ("profile_checks", "harness_found")) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD):
    """The staged copy against release_pack.manifest() of mod/ at the pinned commit (a git archive into a scratch
    folder), not the live tree: the mod lane may commit beside this live task (the ledger's T2/T3 ruling). The staged
    MANIFEST and the staged tree must both equal it; the staged NR_Core.lua's version is read for the verify rows."""
    import release_pack as RP
    M = {"commit": commit, "staged_manifest": f"{stage_root}/{MANIFEST_NAME}", "staged_mod": stage_mod}
    try:
        M["commit_full"] = subprocess.run(["git", "rev-parse", commit], cwd=repo, capture_output=True,
                                          text=True).stdout.strip()
        M["mod_commit"] = subprocess.run(["git", "log", "-1", "--format=%h", commit, "--", MOD_DIR], cwd=repo,
                                         capture_output=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            arch = subprocess.run(["git", "archive", "--format=tar", commit, MOD_DIR], cwd=repo, capture_output=True)
            if arch.returncode != 0:
                raise OSError(arch.stderr.decode("utf-8", "replace")[:300])
            import io
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
                tf.extractall(tmp, filter="data")
            pinned = RP.manifest(os.path.join(tmp, *MOD_DIR.split("/")))
        mpath = os.path.join(repo, stage_root, MANIFEST_NAME)
        M["staged_manifest_sha256"] = X.sha256_file(mpath)
        with open(mpath, encoding="utf-8") as fh:
            staged = json.load(fh)
        booted = RP.manifest(os.path.join(repo, stage_mod))
        M["files"] = len(pinned)
        M["staged_equals_commit"] = staged == pinned
        M["staged_tree_equals_commit"] = booted == pinned
        if staged != pinned:
            M["diff_staged_vs_commit"] = RP.diff(staged, pinned)
        if booted != pinned:
            M["diff_tree_vs_commit"] = RP.diff(booted, pinned)
        with open(os.path.join(repo, stage_mod, *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        M["staged_version"] = m.group(1) if m else None
    except (OSError, ValueError, KeyError) as e:
        M["error"] = f"{type(e).__name__}: {e}"
    M["ok"] = (M.get("staged_equals_commit") is True and M.get("staged_tree_equals_commit") is True
               and "error" not in M)
    return M


# ================================================================ the session
class Sess:
    """The spike's phases over an xlib.Xs; every wait goes through xs.clock and xs.sleep, so the tests run it fast."""

    def __init__(self, xs, day_length=MOD_DAY_LENGTH):
        self.xs = xs
        self.out = xs.out
        self.dl = day_length
        self.R = self.out.setdefault("readings", {})
        self.W = self.out.setdefault("windows", {})
        self.red0 = None
        self.mode0 = None
        self.low = False                       # a window ended under HEALTH_FLOOR: the drain phases stop

    # -- plumbing
    def k(self, tag, cmd, args="", side=SRV):
        return self.xs.keep(self.xs.step(tag, side, cmd, args))

    def sleep_until(self, t_end):
        while self.xs.clock() < t_end:
            self.xs.check()
            self.xs.sleep(min(POLL_S, max(0.0, t_end - self.xs.clock())))

    def get_const(self, tag):
        return self.k(tag, "witness.chain", f"{USER} {GET_CHAIN}")

    def set_const(self, tag, v):
        s = self.k(tag + "_set", "witness.chain", f"{USER} {SET_CHAIN.format(v=repr(float(v)))}")
        r = self.get_const(tag + "_get")
        self.R.setdefault("const_writes", []).append({"tag": tag, "want": v, "set": s, "get": r})
        return s, r

    def levels(self, tag, names):
        return {m: self.k(f"{tag}_{m}", "moodle.level", f"{USER} {m}") for m in names}

    def window(self, name, hold_s, moodles=()):
        """h0 health, s0 stats, c0 tag counts, the named moodles; the hold; the moodles, c1, s1, h1."""
        w = {"hold_s": hold_s}
        w["h0"] = self.k(name + "_h0", "health.get", USER)
        t_end = self.xs.clock() + hold_s
        w["s0"] = self.k(name + "_s0", "stats.get", USER)
        w["c0"] = self.k(name + "_c0", "fall.probe", USER)
        w["lv0"] = self.levels(name + "_lv0", moodles)
        self.sleep_until(t_end)
        w["lv1"] = self.levels(name + "_lv1", moodles)
        w["c1"] = self.k(name + "_c1", "fall.probe", USER)
        w["s1"] = self.k(name + "_s1", "stats.get", USER)
        w["h1"] = self.k(name + "_h1", "health.get", USER)
        self.W[name] = w
        h1 = num(g(w, "h1", "overall"))
        if h1 is not None and h1 < HEALTH_FLOOR:
            self.low = True
            self.xs.note(f"window {name} ended at health {h1}, under {HEALTH_FLOOR}: the drain phases stop")
        return w

    def lowweight(self, name):
        """Five Nutrition.setWeight(30) calls bracketed by two health reads and one stats.get for the multiplier."""
        br = {"h0": self.k(name + "_h0", "health.get", USER)}
        br["s"] = self.k(name + "_s", "stats.get", USER)
        br["calls"] = [self.k(f"{name}_w{i}", "nutrition.set", f"{USER} weight {LW_WEIGHT:g}") for i in range(LW_CALLS)]
        br["h1"] = self.k(name + "_h1", "health.get", USER)
        self.W[name] = br
        return br

    def stop_if_low(self):
        if self.low:
            raise X.Budget("health under the floor: the drain phases stop")

    # -- the phases
    def phase_S(self):
        self.R["players"] = self.k("S_players", "players")
        self.R["clock0"] = self.xs.snap("S_clock")
        c = self.get_const("S_const")
        self.R["const_start"] = c
        self.red0 = const_of(c)
        m = self.k("S_mode", "lua.read", f"_G {MODE_PATH} SandboxVars.DayLength SandboxVars.Nutrition")
        self.R["mode_read"] = m
        self.mode0 = g(m, "values", MODE_PATH)
        self.R["health0"] = self.k("S_health", "health.get", USER)
        self.R["autodrink"] = self.k("S_autodrink", "autodrink.probe", USER)
        self.R["foodtimer"] = self.k("S_foodtimer", "foodtimer.set", f"{USER} 0")
        self.R["hook"] = self.k("S_hook", "fall.probe", USER)
        if self.red0 is None or abs(self.red0 - CONST_DEFAULT) > CONST_EPS:
            self.xs.note(f"the constant read {self.red0} at S, not {CONST_DEFAULT}")
        if self.mode0 != 1:
            raise RuntimeError(f"the writer mode read {self.mode0!r}, not 1: the session is not the one asked for")
        self.R["mode_set"] = self.k("S_mode_set", "lua.setpath", f"{MODE_PATH} {MODE_SPIKE}")

    def phase_A(self):
        self.R["A_write"] = self.k("A_write", "stats.set", f"{USER} hunger {HUNGER_W} thirst {THIRST_W}")
        self.xs.sleep(SETTLE_S)
        self.window("A", WIN_A_S)
        self.stop_if_low()
        self.lowweight("LW_A")

    def phase_B(self):
        self.set_const("B_const", 0.0)
        self.xs.sleep(SETTLE_S)
        self.window("B", WIN_B_S)
        self.lowweight("LW_B")

    def phase_C1(self):
        self.R["C1_write"] = self.k("C1_write", "stats.setany", f"{USER} FOOD_SICKNESS {FOOD_SICK_W:g}")
        self.xs.sleep(SETTLE_S)
        self.window("C1", WIN_C1_S, ("SICK",))

    def phase_C2(self):
        rows = []
        for i in BLEED_PARTS:
            rows.append(self.k(f"C2_bt{i}", "bodypart.set", f"{USER} {i} bleedingTime {BLEED_TIME:g}"))
            rows.append(self.k(f"C2_bl{i}", "bodypart.set", f"{USER} {i} bleeding true"))
        self.R["C2_writes"] = rows
        self.xs.sleep(SETTLE_S)
        self.window("C2", WIN_C2_S, ("SICK", "BLEEDING"))
        self.stop_if_low()

    def phase_D(self):
        self.set_const("D_const", self.red0 if self.red0 is not None else CONST_DEFAULT)
        self.window("D", WIN_D_S, ("SICK", "BLEEDING"))

    def phase_K(self):
        """The cleanup, every write fenced: E's constant marker first (it cuts the drains to a quarter at once), the
        bleeding, the sickness, hunger and thirst cleared, the writer mode restored from S's read, the modData marker."""
        self.set_const("K_const", CONST_MARKER)
        rows = []
        for i in BLEED_PARTS:
            rows.append(self.k(f"K_bt{i}", "bodypart.set", f"{USER} {i} bleedingTime 0"))
            rows.append(self.k(f"K_bl{i}", "bodypart.set", f"{USER} {i} bleeding false"))
        self.R["K_bleed"] = rows
        self.R["K_sick"] = self.k("K_sick", "stats.setany", f"{USER} FOOD_SICKNESS 0")
        self.R["K_stats"] = self.k("K_stats", "stats.set", f"{USER} hunger {CLEAR_HUNGER} thirst {CLEAR_THIRST}")
        mode = self.mode0 if self.mode0 is not None else 1
        self.R["K_mode"] = self.k("K_mode", "lua.setpath", f"{MODE_PATH} {mode}")
        self.R["K_moddata"] = self.k("K_moddata", "moddata.set", f"{USER} {MODDATA_KEY} {MODDATA_VAL}")
        self.R["K_const_final"] = self.get_const("K_const_final")
        self.R["K_health"] = self.k("K_health", "health.get", USER)
        self.R["clock1"] = self.xs.snap("K_clock")

    def phases(self):
        return [("S", self.phase_S), ("A", self.phase_A), ("B", self.phase_B), ("C1", self.phase_C1),
                ("C2", self.phase_C2), ("D", self.phase_D), ("K", self.phase_K)]

    def body_run(self):
        """Each phase through xs.run_phase; once a phase stopped on the budget or the health floor, or the bus died,
        only K (the cleanup) still runs."""
        for name, fn in self.phases():
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            stopped = self.out.get("budget_stop") or self.xs.bus_dead or self.out["phase_errors"]
            if stopped and name != "K":
                self.out.setdefault("skipped_phases", []).append(name)
                self.xs.note(f"phase {name} skipped: an earlier phase stopped")
                continue
            self.xs.run_phase(name, fn)

    def phase_E(self):
        """After the reuse boot: the constant, the modData, health and the stats read once."""
        e = self.out.setdefault("E", {})
        e["const"] = self.get_const("E_const")
        e["moddata"] = self.k("E_moddata", "witness.chain", f"{USER} getModData")
        e["health"] = self.k("E_health", "health.get", USER)
        e["stats"] = self.k("E_stats", "stats.get", USER)
        e["health_k"] = num(g(self.R, "K_health", "overall"))
        e["marker_read"] = const_of(self.R.get("K_const_final"))
        return e

    # -- the grades
    def grade_all(self):
        xs, W, R = self.xs, self.W, self.R
        writes = {r["tag"]: r for r in R.get("const_writes", [])}
        falsifier = "the setter does not answer ok or the getter does not read the value written"
        for tag, want in (("B_const", 0.0), ("D_const", self.red0 if self.red0 is not None else CONST_DEFAULT),
                          ("K_const", CONST_MARKER)):
            r = writes.get(tag)
            if r is None:
                xs.grade("ROUTE_" + tag, "unmeasured", {"why": "not written"}, falsifier)
                continue
            v, obs = grade_route(r["set"], r["get"], want)
            xs.grade("ROUTE_" + tag, v, obs, falsifier)
        if "A" in W:
            v, obs = grade_control(W["A"], self.red0, self.dl)
            xs.grade("A", v, obs, f"the rate off the prediction by more than {A_TOL_REL:.0%}, or a moodle off 4")
        slope_a = None
        ra = window_rate(W["A"]) if "A" in W else None
        if ra and ra["dh"] is not None and ra["dwall"]:
            slope_a = -ra["dh"] / ra["dwall"]
        if "LW_A" in W:
            v, obs = grade_lowweight(W["LW_A"], slope_a, self.red0, True)
            xs.grade("LW_A", v, obs, f"the excess drop outside {LW_A_BAND} x calls x red x mult")
        if "B" in W:
            v, obs = grade_hold(W["B"], ("hungry", "thirst"), ("HUNGRY", "THIRST"))
            xs.grade("B", v, obs, f"health moved more than {HOLD_TOL} or a HUNGRY or THIRST tag fired")
        if "LW_B" in W:
            v, obs = grade_lowweight(W["LW_B"], 0.0, 0.0, False)
            xs.grade("LW_B", v, obs, f"the bracket's drop larger than {HOLD_TOL}")
        if "C1" in W:
            v, obs = grade_hold(W["C1"], ("hungry", "thirst", "SICK"), ("SICK", "HUNGRY", "THIRST"))
            xs.grade("C1", v, obs, f"health moved more than {HOLD_TOL} or a SICK tag fired at SICK 4")
        if "C2" in W:
            v, obs = grade_bleed(W["C2"], ("hungry", "thirst", "SICK", "BLEEDING"))
            xs.grade("C2", v, obs, "health held, no BLEEDING tag, or a SICK, HUNGRY or THIRST tag fired")
        if "D" in W and "C2" in W:
            v, obs = grade_restore(W["D"], W["C2"], self.red0, self.dl)
            xs.grade("D", v, obs, f"the excess over C2 off the prediction by more than {D_TOL_REL:.0%}, or a tag silent")
        if "E" in self.out:
            v, obs = grade_persist(self.out["E"])
            xs.grade("E", v, obs, "the constant reads the marker (or anything but the default) after the reload")
        v, obs = grade_z(self.out)
        xs.grade("Z", v, obs, "a mod error line in a server log, or admin parked in the debugger")


def grade_z(out):
    """Z: no mod error line in either server log and admin never parked; unmeasured when the logs were not read."""
    logs = out.get("logs")
    if not isinstance(logs, dict) or "mod_error" not in logs:
        return "unmeasured", {"why": "the logs were not read"}
    errs = {k: v for k, v in logs["mod_error"].items() if v}
    parked = out.get("admin_lua_error")
    obs = {"mod_error": errs, "admin_lua_error": parked}
    return ("as_predicted" if not errs and parked is False else "falsified"), obs


# ================================================================ the driver's main
def main(profile_name, prefix, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    pre, ok = preboot(profile_name, prefix, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str))
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=USER)
    xs.path = os.path.join(run_dir, artifact)
    S = Sess(xs)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session": session_text, "driver": driver_file, "lib": LIB_FILE, "user": USER,
        "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern)) and k not in ("REPO",)},
        "predictions": pred, "meta": {"budget_s": budget_s},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the pinned commit or the verify rows: {mg!r}; not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
        xs.copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    logs = []
    try:
        # ---- boot 1
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, okm):
            return out
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
            return out
        S.body_run()
        # ---- the reuse boot for E (the same run folder; boot 1's clients and log kept beside it)
        k_done = "K" in out["phase_walls"] and "K" not in out["phase_errors"]
        if not k_done or xs.bus_dead or out.get("abort"):
            out["E_skipped"] = "K did not complete cleanly"
        elif xs.wall() > E_START_CAP_S:
            out["E_skipped"] = f"boot 1 ended at wall {xs.wall()} s, past {E_START_CAP_S} s"
        else:
            xs.cur_phase = "E"
            out["phase_walls"]["E"] = {"start": xs.wall()}
            teardown(tl, server, [c for c in started if c.alive])
            out["boot1_teardown_wall"] = xs.wall()
            log1 = os.path.join(run_dir, "server-stdout-boot1.log")
            os.replace(server.log_path, log1)
            logs.append(log1)
            os.replace(os.path.join(run_dir, "clients"), os.path.join(run_dir, "clients-boot1"))
            clients.clear()
            server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                                 sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog, reuse=True)
            holder["server"] = server
            xs.server = server
            server.start(timeout=prof.server_timeout)
            tl.mark("server_started", boot=2)
            clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
            out["boot2_ready_wall"] = xs.wall()
            out["verify_boot2"] = verify(prof, server, clients, tl)
            xs.mem("ready2")
            S.phase_E()
            out["phase_walls"]["E"]["end"] = xs.wall()
            xs.persist()
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern}}
            paths = list(logs) + ([server.log_path] if server is not None else [])
            for p in paths:
                lines, skipped = X.grep_noecho(p, LOG_RX, 300, ECHO_RX, NEVER_RX)
                L.setdefault("server", {})[os.path.basename(p)] = lines
                L.setdefault("mod_error", {})[os.path.basename(p)] = [ln for ln in lines if MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", []).append({"user": getattr(c, "username", "?"), "lines": lines})

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
        print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                          "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                          "budget_stop": out.get("budget_stop"), "E_skipped": out.get("E_skipped"),
                          "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                          "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                          "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                          "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
