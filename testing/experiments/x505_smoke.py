"""x505-smoke -- Plan 19 Task 9b (live): the close's smoke boot of the re-staged upload copy, x485's design (Plan 17
Task 7b, testing/experiments/x485_smoke.py) on the default fixture: the two drain options set off their defaults in the
server's options file read back on the server and admin; admin joins cleanly at 1.0.0; no mod error. It adds one graded
arm, T7_2: the live confirmation of ruling T7-2 (R3's item sync after the restore, back at 21f788a7) and of row #4148's
mechanism.

THE T7-2 ARM. x503 (Plan 19 Task 7) ate a quarter of a stale potato sated (I2C, vanilla's own part-eat: the mod inert)
and then another quarter Hungry (I2). Vanilla's part-eat ends with an item-stats packet that carries the remainder's
read-time UnhappyChange to the eater's client (#4147): after I2C the client held 13.75, the server's read-time value.
After I2 the client held 8.833333015441895, the alliesthesia-lowered field ((0.6 x 13.75 - 10) x 2/3 + 10) that
vanilla's packet carried before the mod's restore, while the server held 2.5 (read-time 12.5): the restore sent no sync
(Plan 19 Task 6 fix 1). 21f788a7 re-syncs the remainder after the restore. This session repeats x503's two potato eats
on the staged copy of mod/ at STAGED_FROM, so the prediction is the client equal to the server's read-time value after
the Hungry eat, as after the control.

One boot of profile x505-smoke (fixture default, admin -debug; PZTestKit and the STAGED upload copy release/
NutritionRevamp/Contents/mods/NutritionRevamp, staged from STAGED_FROM; Nutrition false, DayLength 4, sleep off, NR.Mode
1, NR.DeathPace PACE_SET, NR.HealthCombine COMBINE_SET), build 42.21.0, at the fixture's speed throughout. The plumbing
is testing/experiments/x50_lib.py's (x503's Allies session: its eat, its item reads on both sides, its Hungry seed, its
grades PRE and COUNTS), imported unchanged: x50_lib is frozen with x501-x504's runs, so this file names its own staged
commit, session, profile, phases and grades, and never reads x50_lib's STAGED_FROM, SESSIONS or prerun.

THE SESSION (one boot, under 10 wall minutes, in a foreground call): the server, admin attached, the verify rows; then
  S    x50_lib's start reads (players, sandbox, clock, nutrition, stats, the hedonics counters, Cooking, health) and the
       options read set `start` on the server and admin (a reading: it may precede the options poll's first minute);
  I    RCON additem of one Potato, confirmed by its server id;
  I2C  the vanilla control (x503's, unchanged): the potato aged stale (item.set age STALE_AGE_D: read-time = field +
       STALE_TERM), a quarter of it (EAT_F of the whole) eaten sated with no seed (no alliesthesia, no restore); before
       and after the eat the item on the server and on the client, then the server again (x50_lib.Sess.eat: the server
       read, SYNC_WAIT_S, the client read, the server read);
  T72  the Hungry eat (x503's I2): record.set satiety.M 0, HUNGER set to HUNGRY_SEED (Hungry, x503's seed; the writer
       never lowers an unfed HUNGER), one writer minute, then another quarter of the whole eaten Hungry; the same reads;
  O    the options read set `end` on the server and admin (graded);
  C    the hedonics counters; the clock restored to the value read at S (never a reply's echo).
No UNHAPPINESS seed (no delta is graded here); no ring.

THE READS. Every item read is witness.fields of x50_lib.FIELDS by the item's server id (getUnhappyChangeUnmodified, the
stored field; getUnhappyChange, the read-time value with its state terms; getHungChange). The client's stored field
after an eat is paired with the server's read-time value by a bracket (ruling T7-1, x50_lib.PAIR_SLACK_S): the field is
static between driven eats, so the two server reads around the client read, equal in field and read-time value inside
PAIR_SLACK_S, stand for the same wall second; a bracket whose server reads differ reads unmeasured. Every stat that
moves (HUNGER) is read on the server alone.

THE GRADES (pure; each has a failing case in testing/tests/test_x505.py; a grade on no valid sample is unmeasured):
  INI         (precondition) the seeded options file's NR block holds DeathPace = PACE_SET and HealthCombine =
              COMBINE_SET.
  OPT_SERVER, OPT_ADMIN  SandboxVars.NR.DeathPace PACE_SET and SandboxVars.NR.HealthCombine COMBINE_SET on that side
              in the read set `end` (admin's copy is the one the server sends at the join).
  MOD_READ    on the server in `end`: NutritionRevamp.server.options.deathPace and .healthCombine (the options poll)
              and NutritionRevamp.kernel.drain.OPT.pace and .combine read PACE_SET and COMBINE_SET.
  JOIN        every verify row ok (NutritionRevamp.version 1.0.0 on the server and admin), and the server's players at S
              a list holding admin.
  PRE         (precondition, x50_lib.grade_pre) HUNGER at the before-read at or under ALLIES_AT for I2C, over it for
              T72.
  CONTROL     (precondition: #4147 on this build) after I2C, on a valid bracket, the client's stored field equals the
              server's read-time value. Falsified when it does not (vanilla's packet absent or carrying another
              value); unmeasured when the control did not land, was not sated, its client read did not resolve, or its
              bracket moved.
  T7_2        after T72, on a valid bracket: the server's stored field is the field before x hung1 / hung0 (the restore:
              falsified when the remainder keeps the lowered field, which would make a client match trivial), and the
              client's stored field equals the server's read-time value. Falsified when it does not; the observation
              names x503's case, the client keeping the lowered field (field before - (rt before - ALLIES_F x rt
              before)) x hung1 / hung0 + the state term. Unmeasured when CONTROL is not as_predicted (the control's
              client read did not resolve, or vanilla's own packet is off), when T72 was not Hungry at its before-read
              or did not land, when lastIntake.allies is not ALLIES_F (no field was lowered), when the bracket moved,
              or when the lowered value and the restored remainder's read-time value are within TOL_FIELD (the arm
              could not tell them apart; checked before the restore, whose failure makes them agree on the server).
  COUNTS      (x50_lib.grade_counts_503) the allies counter rose by 1 (T72), restores by 1 (its remainder),
              alliesFailures by 0; the sated control adds neither.
  Z           (x50_lib.grade_z) no mod error line in the server log, admin never parked, no hedonics failure counter
              rose.

PREDICTIONS (predict(): the potato's script field POTATO_U, x503's live read, through vanilla's linear remainder scale;
no body enters them, so this session has no prerun replay and types no body: the default fixture's admin is a fresh
record, which lays the mod's own creation body at first sight; preboot checks the fixture fresh): the control's server
field 5 -> 3.75 (read-time 13.75) and its client 13.75; T72's server field 3.75 -> 2.5 (read-time 12.5) and its client
12.5, never 8.833333 (x503's lowered field).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
6. Takes no argument: a bare call boots the session; any argument is refused before anything else runs.

WALL: the body about 70.5 s measured on the latency-charged fake (test_x505's budget test), the boot 52-85 s; BUDGET_S 360.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402
import x47_lib as L47                                                         # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x49_lib as L49                                                         # noqa: E402
import x49b_lib as B                                                          # noqa: E402
import x50_lib as L                                                           # noqa: E402

KEY = "x505"
PREFIX = "x505"
PROFILE = "x505-smoke"
ARTIFACT = "smoke.json"
BUDGET_S = 360.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
DRIVER = "x505_smoke.py"

REPO = X.REPO
SRV = X.SRV
CLI = L.CLI
USER = L.USER
NR = L.NR
MOD_DIR = L.MOD_DIR
STAGE_ROOT = L.STAGE_ROOT                # release/NutritionRevamp, the upload copy
STAGE_MOD = L.STAGE_MOD
STAGED_FROM = "0b1b3f11"                 # mod/'s last commit (Plan 19 close fix wave), staged after it
STAGED_VERSION = "1.0.0"
MIN_FREE_GB = 12.0
FIXTURE = "default"
CLIENTS = [USER]
DAY_LENGTH = 4                           # x50's: a game minute 3.75 wall s at speed 1 (the eat and seed waits)
MODE = 1                                 # Hybrid: the mod writes HUNGER, which alliesthesia reads
PACE_SET = 2                             # off the declared default 3 and x50's 3
COMBINE_SET = 1                          # Worst; off the declared default 2 and x50's 2
PACE_DEFAULT, COMBINE_DEFAULT = 3, 2
PRIOR_SETS = {"x50": (3, 2), "x485": (1, 1), "x483": (2, 3)}   # the (DeathPace, HealthCombine) of earlier sessions
SERVER_TIMEOUT_S = 240                   # the profile's [server] timeout (x484's): bounds the slow-boot fallback
SANDBOX_REL = L47.SANDBOX_REL            # server/Server/pzt_SandboxVars.lua in the run dir

SERVER_PACE_G = "SandboxVars.NR.DeathPace"
SERVER_COMBINE_G = "SandboxVars.NR.HealthCombine"
MOD_PACE_G = "NutritionRevamp.server.options.deathPace"
MOD_COMBINE_G = "NutritionRevamp.server.options.healthCombine"
OPT_PACE_G = "NutritionRevamp.kernel.drain.OPT.pace"
OPT_COMBINE_G = "NutritionRevamp.kernel.drain.OPT.combine"
OPT_DAYMIN_G = "NutritionRevamp.kernel.drain.OPT.dayMin"
VERSION_G = "NutritionRevamp.version"
READ_PLAN = {SRV: (SERVER_PACE_G, SERVER_COMBINE_G, MOD_PACE_G, MOD_COMBINE_G, OPT_PACE_G, OPT_COMBINE_G, OPT_DAYMIN_G,
                   VERSION_G),
             CLI: (SERVER_PACE_G, SERVER_COMBINE_G, VERSION_G)}
GRADED_SET = "end"

# ---- the arm (x503's potato, x50_lib's constants)
POTATO = L.POTATO
EAT_F = L.POTATO_F / 2                   # each eat a quarter of the whole (eat.action's fraction of the whole)
POTATO_U = 5.0                           # the potato's stored UnhappyChange as x503 read it live (x503's I2C item0)
STALE_TERM = L.STALE_TERM
STALE_AGE_D = L.STALE_AGE_D
HUNGRY_SEED = L.HUNGRY_SEED
ALLIES_F = L.ALLIES_F
ALLIES_AT = L.ALLIES_AT
CONTROL, ARM = "I2C", "T72"              # the control keeps x503's arm name, so x50_lib.grade_pre reads it as sated
SPAWNS = ((POTATO, 1),)
TOL_FIELD = L.TOL_FIELD
REL_TOL = L.REL_TOL
PAIR_SLACK_S = L.PAIR_SLACK_S

# ---- the harness commands this session sends (each checked in the harness files before the boot)
HARNESS_FILES = L.HARNESS_FILES
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "stats.all", "stats.setany", "record.set", "nutrition.get", "players", "perk.xp", "item.get", "item.set",
        "health.get", "time.multiplier")),
    "PZTestKit_Client.lua": tuple(f'TK.register("{c}", function(' for c in ("eat.action",)),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in (
        "time.snapshot", "lua.read", "witness.fields", "lua.global")),
}


def predict():
    """The arm's predictions: vanilla's linear remainder scale of the potato's field, the stale term on the server's
    read-time value, alliesthesia's lowered field (x503's falsifying case)."""
    c0 = POTATO_U
    c1 = c0 * (1 - EAT_F)                                    # after the control: 3.75
    f2 = EAT_F / (1 - EAT_F)                                 # the Hungry eat's share of the remainder: 1/3
    t1 = c1 * (1 - f2)                                       # 2.5
    rt = c1 + STALE_TERM
    lowered = (c1 - (rt - ALLIES_F * rt)) * (1 - f2) + STALE_TERM
    r6 = (lambda v: round(v, 6))
    return {"control": {"server_field": [r6(c0), r6(c1)], "server_readtime_after": r6(c1 + STALE_TERM),
                        "client_after": r6(c1 + STALE_TERM)},
            "t72": {"server_field": [r6(c1), r6(t1)], "server_readtime_after": r6(t1 + STALE_TERM),
                    "client_after": r6(t1 + STALE_TERM), "client_lowered_x503": r6(lowered), "frac": r6(f2)},
            "counts": {"allies": 1, "restores": 1, "alliesFailures": 0}}


PREDICTED = predict()
SESSION = ("Plan 19 Task 9b x505: the close's smoke boot of the staged copy at " + STAGED_FROM + " (NR.DeathPace "
           f"{PACE_SET} and NR.HealthCombine {COMBINE_SET} read back on the server and admin; the clean 1.0.0 join; no "
           "mod error) and the T7-2 arm: a stale potato eaten sated (vanilla's control) then Hungry, the client's "
           "stored field against the server's read-time value; one boot of " + PROFILE)
PRED = {
    "INI": f"the seeded NR block holds DeathPace = {PACE_SET} and HealthCombine = {COMBINE_SET}",
    "OPT_SERVER": f"SandboxVars.NR.DeathPace {PACE_SET} and HealthCombine {COMBINE_SET} on the server",
    "OPT_ADMIN": f"{PACE_SET} and {COMBINE_SET} on admin",
    "MOD_READ": f"server options.deathPace {PACE_SET} and healthCombine {COMBINE_SET}, K.drain.OPT.pace {PACE_SET} and "
                f"combine {COMBINE_SET}",
    "JOIN": "every verify row ok (1.0.0 on the server and admin), players at S holding admin",
    "PRE": f"HUNGER at or under {ALLIES_AT} at the control, over it at T72",
    "CONTROL": f"after the sated eat the client's stored field {PREDICTED['control']['client_after']} = the server's "
               f"read-time value (field {PREDICTED['control']['server_field'][1]} + {STALE_TERM})",
    "T7_2": f"after the Hungry eat the server's field {PREDICTED['t72']['server_field'][1]} (restored) and the "
            f"client's stored field {PREDICTED['t72']['client_after']} = the server's read-time value, never "
            f"{PREDICTED['t72']['client_lowered_x503']} (the lowered field, x503)",
    "COUNTS": f"{PREDICTED['counts']}",
    "Z": "no mod error line, no hedonics failure counter rising, admin not parked",
}
CONSTANTS = {k: v for k, v in dict(globals()).items() if k.isupper() and k not in ("HERE", "REPO", "PRED", "SESSION")
             and isinstance(v, (int, float, str, bool, tuple, dict, list))}

num = X.num
g = G.g


# ================================================================ the options and the join (pure)
def grade_ini(seeded):
    """INI: the seeded file's NR block holds DeathPace = PACE_SET and HealthCombine = COMBINE_SET."""
    obs = {"seeded_nr_block": seeded}
    if not isinstance(seeded, dict):
        return "unmeasured", obs
    ok = L47.same_number(seeded.get("DeathPace"), PACE_SET) and L47.same_number(seeded.get("HealthCombine"),
                                                                                 COMBINE_SET)
    return ("as_predicted" if ok else "falsified"), obs


def grade_values(read_sets, side, wants, tag=GRADED_SET):
    """Each path of `wants` ({path: value}) on one side in the read set `tag` (read_sets[tag][side] a lua.read reply):
    falsified on any answered value off, unmeasured unless every path answered, else as_predicted."""
    reply = g(read_sets, tag, side)
    got = G.vals(reply)
    obs = {"side": side, "set": tag, "values": {p: got.get(p) for p in wants}, "want": dict(wants),
           "error": g(reply, "error")}
    off = [p for p in wants if p in got and not L47.same_number(got.get(p), wants[p])]
    if off:
        return "falsified", dict(obs, off=off)
    if not isinstance(reply, dict) or any(p not in got for p in wants):
        return "unmeasured", obs
    return "as_predicted", obs


def grade_opt(read_sets, side):
    return grade_values(read_sets, side, {SERVER_PACE_G: PACE_SET, SERVER_COMBINE_G: COMBINE_SET})


def grade_mod_read(read_sets):
    return grade_values(read_sets, SRV, {MOD_PACE_G: PACE_SET, MOD_COMBINE_G: COMBINE_SET, OPT_PACE_G: PACE_SET,
                                         OPT_COMBINE_G: COMBINE_SET})


def grade_join(verify_rows, players):
    """JOIN: every verify row ok, a version row on the server and on the client, and players at S a list holding
    admin (the bus answers nobody online as {})."""
    rows = verify_rows if isinstance(verify_rows, list) else None
    lst = players if isinstance(players, list) else ([] if isinstance(players, dict) and not players else None)
    sides = sorted(str(r.get("side")) for r in rows or [] if isinstance(r, dict))
    obs = {"verify": [{k: r.get(k) for k in ("side", "cmd", "args", "ok")} for r in rows or [] if isinstance(r, dict)],
           "players": lst}
    if rows is None or lst is None:
        return "unmeasured", obs
    ok = bool(rows) and all(isinstance(r, dict) and r.get("ok") is True for r in rows) and \
        "server" in sides and any(s.startswith("client") for s in sides) and USER in lst
    return ("as_predicted" if ok else "falsified"), obs


# ================================================================ the T7-2 arm (pure)
def bracket(e):
    """The client read after an eat bracketed by two equal server reads inside PAIR_SLACK_S (ruling T7-1): (ok, why)."""
    s0, s1 = g(e, "item1") or {}, g(e, "sitem1b") or {}
    w0, w1 = num(s0.get("wall")), num(s1.get("wall_after"))
    f0, f1 = num(g(s0, "fields", "getUnhappyChangeUnmodified")), num(g(s1, "fields", "getUnhappyChangeUnmodified"))
    r0, r1 = num(g(s0, "fields", "getUnhappyChange")), num(g(s1, "fields", "getUnhappyChange"))
    if None in (w0, w1, f0, f1, r0, r1):
        return False, "a bracketing server read unread"
    if w1 - w0 > PAIR_SLACK_S:
        return False, f"the bracket spans {w1 - w0:.2f} s, over {PAIR_SLACK_S} s"
    if abs(f0 - f1) > TOL_FIELD or abs(r0 - r1) > TOL_FIELD:
        return False, "the bracketing server reads differ"
    return True, None


def arm_reads(e):
    return {"server_field": [num(g(e, "item0", "fields", "getUnhappyChangeUnmodified")),
                             num(g(e, "item1", "fields", "getUnhappyChangeUnmodified"))],
            "server_readtime": [num(g(e, "item0", "fields", "getUnhappyChange")),
                                num(g(e, "item1", "fields", "getUnhappyChange"))],
            "server_hung": [num(g(e, "item0", "fields", "getHungChange")),
                            num(g(e, "item1", "fields", "getHungChange"))],
            "client_field": [num(g(e, "citem0", "fields", "getUnhappyChangeUnmodified")),
                             num(g(e, "citem1", "fields", "getUnhappyChangeUnmodified"))],
            "client_resolved": g(e, "citem1", "resolved"), "landed": e.get("landed"), "frac": e.get("frac"),
            "hunger_before": num(g(e, "stats0", "Hunger")), "allies": num(g(e, "rec1", "lastIntake.allies"))}


def grade_control(eats):
    """CONTROL: after the sated eat, on a valid bracket, the client's stored field = the server's read-time value."""
    e = L.arm_eat(eats, CONTROL)
    obs = arm_reads(e)
    if not e.get("landed"):
        return "unmeasured", dict(obs, why="the control did not land"), 0
    if L.hungry_at(e) is not False:
        return "unmeasured", dict(obs, why="the control was not sated at its before-read"), 0
    c1, rt1 = obs["client_field"][1], obs["server_readtime"][1]
    if obs["client_resolved"] is not True or c1 is None:
        return "unmeasured", dict(obs, why="the control's client read did not resolve"), 0
    ok, why = bracket(e)
    if not ok:
        return "unmeasured", dict(obs, why=why), 0
    return ("as_predicted" if abs(c1 - rt1) <= TOL_FIELD else "falsified"), obs, 1


def lowered_client(f0, rt0, h0, h1):
    """x503's case: the alliesthesia-lowered field (f0 - (rt0 - ALLIES_F x rt0)) scaled by vanilla to the remainder,
    plus the state term, as vanilla's in-Eat item-stats packet writes it on the client."""
    return (f0 - (rt0 - ALLIES_F * rt0)) * h1 / h0 + (rt0 - f0)


def grade_t72(eats):
    """T7_2: after the Hungry eat, on a valid bracket, the server's remainder restored and the client's stored field =
    the server's read-time value."""
    e = L.arm_eat(eats, ARM)
    obs = arm_reads(e)
    vc, oc, _ = grade_control(eats)
    obs["control"] = vc
    if vc != "as_predicted":
        return "unmeasured", dict(obs, why=f"the control reads {vc} ({oc.get('why') or 'vanilla packet off'}): no "
                                           "reference"), 0
    if L.hungry_at(e) is not True:
        return "unmeasured", dict(obs, why="the arm was not Hungry at its before-read (the seed did not hold)"), 0
    (f0, f1), (rt0, rt1), (h0, h1) = obs["server_field"], obs["server_readtime"], obs["server_hung"]
    c1 = obs["client_field"][1]
    if not e.get("landed") or None in (f0, f1, rt0, rt1, h0, h1) or not h0:
        return "unmeasured", dict(obs, why="the arm did not land or a server read is missing"), 0
    if obs["client_resolved"] is not True or c1 is None:
        return "unmeasured", dict(obs, why="the arm's client read did not resolve"), 0
    if obs["allies"] is None or abs(obs["allies"] - ALLIES_F) > 1e-9:
        return "unmeasured", dict(obs, why="lastIntake.allies is not ALLIES_F: no field was lowered"), 0
    ok, why = bracket(e)
    if not ok:
        return "unmeasured", dict(obs, why=why), 0
    restored = f0 * h1 / h0
    restored_rt = restored + (rt0 - f0)
    low = lowered_client(f0, rt0, h0, h1)
    obs.update(restored_want=restored, restored_readtime=restored_rt, lowered=low,
               keeps_lowered=abs(c1 - low) <= TOL_FIELD)
    if abs(low - restored_rt) <= TOL_FIELD:
        return "unmeasured", dict(obs, why="the lowered and read-time values agree: the arm cannot tell them"), 0
    if abs(f1 - restored) > REL_TOL * max(1.0, abs(restored)):
        return "falsified", dict(obs, why="the server's remainder keeps the lowered field (the restore missing)"), 1
    return ("as_predicted" if abs(c1 - rt1) <= TOL_FIELD else "falsified"), obs, 1


# ================================================================ the pre-boot checks (offline; tested)
def profile_doc_checks(doc, text=""):
    """The profile's TOML: its header naming its own file, fixture default with admin alone, sleep off, PZTestKit and
    the staged upload copy, Nutrition false, DayLength 4, the [sandbox.NR] block of Mode, DeathPace and HealthCombine
    alone at MODE, PACE_SET and COMBINE_SET, a version verify row on the server and the client, no client override, the
    240 s boot wait."""
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = sorted(v.get("side") for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version"
                and v.get("expect") == f'"value": "{STAGED_VERSION}"')
    return {"header_names_file": text.startswith(f"# testing/profiles/{PROFILE}.toml"),
            "fixture": doc.get("fixture") == FIXTURE,
            "clients": doc.get("clients", [USER]) == CLIENTS,
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths.get(NR) == STAGE_MOD,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == DAY_LENGTH,
            "nr_block": sb.get("NR") == {"Mode": MODE, "DeathPace": PACE_SET, "HealthCombine": COMBINE_SET},
            "verify_version": vr == ["client", "server"],
            "no_override": "client_overrides" not in doc,
            "server_timeout": srv.get("timeout") == SERVER_TIMEOUT_S}


def values_distinct():
    """The set pair off the declared defaults and off every earlier session's pair, so neither a default nor a stale
    options file can pass."""
    return PACE_SET != PACE_DEFAULT and COMBINE_SET != COMBINE_DEFAULT and \
        (PACE_SET, COMBINE_SET) not in PRIOR_SETS.values()


def staged_gate(repo=REPO):
    """x45g_lib's gate at this session's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


def preboot(driver_file, repo=REPO):
    """The driver's file names its session (CLAUDE.md s5); no artifact of the prefix committed; STAGED_FROM mod/'s last
    commit; the profile's TOML; the values distinct; the harness markers; the fixture fresh. Returns (checks, ok)."""
    import glob
    import tomllib
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", KEY + "-*"))
    head = L.mod_head(repo)
    c["mod_head"] = head
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", PROFILE + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    c["values_distinct"] = values_distinct()
    c["harness_found"], c["harness_markers"] = L49.markers_ok(HARNESS_FILES, HARNESS_MARKERS, repo)
    fr = L48.fixture_fresh(repo)
    c["fixture"] = fr
    c["fixture_fresh"] = fr["fresh"]
    skip = ("profile_checks", "mod_head", "harness_found", "fixture")
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def parse_argv(argv, driver_file):
    """x49_lib's: a driver takes no argument; the refusal text, or None for a bare call."""
    return L49.parse_argv(argv, driver_file)


# ================================================================ the session
class Smoke(L.Allies):
    """x505's phases on x50_lib's Allies plumbing (its eat, item reads, Hungry seed), at this session's own key, spec
    and profile (x50_lib.Sess.__init__ reads its own SESSIONS, so this one sets the same fields itself)."""

    def __init__(self, xs, run_dir=None):
        self.xs = xs
        self.out = xs.out
        self.key = KEY
        self.spec = {"driver": DRIVER, "artifact": ARTIFACT, "profile": PROFILE, "budget_s": BUDGET_S}
        self.prof = {"fixture": FIXTURE, "clients": CLIENTS, "day_length": DAY_LENGTH, "mode": MODE,
                     "pace": PACE_SET, "combine": COMBINE_SET}
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages, self.eats, self.pairs, self.points, self.consts, self.drinks = [], [], [], [], [], []
        self.sets = self.out.setdefault("sets", [])
        self.red0 = None
        self.launch = None
        self.P = PREDICTED
        self.read_sets = self.out.setdefault("read_sets", {})
        self.out["lib_x50"] = L.LIB_FILE

    def read_set(self, tag):
        """The options read set `tag`: one lua.read of READ_PLAN's paths on each side, the reply kept whole."""
        rs = self.read_sets.setdefault(tag, {})
        for side, paths in READ_PLAN.items():
            rs[side] = self.lread(f"{tag}_opts_{side}", side, "_G", paths)
        return rs

    def phase_S(self):
        self.common_S()
        self.read_set("start")

    def phase_I(self):
        self.spawn_all(SPAWNS)

    def phase_T72(self):
        self.arm(ARM, POTATO, EAT_F, hungry=True, client_item=True, unhappy=False)

    def phase_O(self):
        self.read_set(GRADED_SET)

    def phases(self):
        return [("S", self.phase_S), ("I", self.phase_I), (CONTROL, self.phase_I2C), (ARM, self.phase_T72),
                ("O", self.phase_O), ("C", self.phase_C)]

    def closing_names(self):
        return ("O", "C")

    def grade_all(self):
        D, out = self.D, self.out
        D["eats"] = self.eats
        self.xs.grade("INI", *grade_ini(out.get("sandbox_seeded")),
                      f"the seeded options file lacks NR.DeathPace = {PACE_SET} or NR.HealthCombine = {COMBINE_SET}")
        self.xs.grade("OPT_SERVER", *grade_opt(self.read_sets, SRV),
                      "SandboxVars.NR.DeathPace or HealthCombine reads another value on the server")
        self.xs.grade("OPT_ADMIN", *grade_opt(self.read_sets, CLI),
                      "SandboxVars.NR.DeathPace or HealthCombine reads another value on admin")
        self.xs.grade("MOD_READ", *grade_mod_read(self.read_sets),
                      "the server's polled options or K.drain.OPT read another value")
        self.xs.grade("JOIN", *grade_join(out.get("verify"), g(D, "S", "players")),
                      "a verify row failed, or admin not on the server's players at S")
        self.grade_set("PRE", L.grade_pre(self.eats), "HUNGER on the wrong side of Hungry at an arm's eat")
        self.grade_set("CONTROL", grade_control(self.eats),
                       "after vanilla's sated part-eat the client's stored field is not the server's read-time value")
        self.grade_set("T7_2", grade_t72(self.eats),
                       "after the Hungry eat the client's stored field is not the server's read-time value (x503: "
                       "the lowered field kept), or the server's remainder keeps the lowered field")
        self.grade_set("COUNTS", L.grade_counts_503(D), "the allies or restores counter off the Hungry eat")
        self.grade_common()
        out["verdict_summary"] = {k: v.get("verdict") for k, v in out["verdicts"].items()}


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    """One boot of x505-smoke (x50_lib.main's shape at this session's staged copy, profile, checks and phases)."""
    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, verify   # noqa: E402

    prof = profile.load(PROFILE)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=PRED, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    S = Smoke(xs, run_dir=run_dir)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": KEY, "session": SESSION, "driver": _ME, "lib": L.LIB_FILE, "user": USER,
        "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": PRED, "predicted": PREDICTED, "constants": CONSTANTS, "constants_x50": L.CONSTANTS,
        "meta": {"budget_s": budget_s},
        "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", L.LUA_DIR),
        "harness_lua_dirty": git_dirty(L.LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + L.LIB_FILE),
        "driver_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + _ME),
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    mg["version_is_release"] = mg.get("staged_version") == STAGED_VERSION
    if not (mg["ok"] and mg["verify_rows_match"] and mg["version_is_release"]):
        xs.refuse(f"the staged copy does not match {STAGED_FROM}, the verify rows or {STAGED_VERSION}: {mg!r}; "
                  "not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(profile.lint_sources(prof, prof.sources))
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
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
        tl.mark("server_started", pid=server.proc.pid)
        out["sandbox_after_start"] = L47.sandbox_nr_block(L47.read_text(sbp))
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[USER], started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
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
            Lg = out["logs"] = {"patterns": {"log": L.LOG_RX.pattern, "mod_error": L.MOD_ERR_RX.pattern}}
            if server is not None:
                logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
                Lg["server"], Lg["server_echo_excluded"] = [], 0
                for lp in logs:
                    hits_, skipped = X.grep_noecho(lp, L.LOG_RX, 300, L.ECHO_RX, L.NEVER_RX)
                    Lg["server"] += hits_
                    Lg["server_echo_excluded"] += skipped
                Lg["mod_error"] = [ln for ln in Lg["server"] if L.MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, L.LOG_RX, 80, L.ECHO_RX, L.NEVER_RX)
                Lg.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    B._summary(out, run_id, run_dir)
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
