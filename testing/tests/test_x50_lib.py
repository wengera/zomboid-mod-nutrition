"""Offline tests of testing/experiments/x50_lib.py, x50_prerun.py and the four drivers x501_prep.py, x502_floor.py,
x503_allies.py and x504_class.py (Plan 19 Task 7, Phase A: never booted here): every grade with a failing case and its
unmeasured case; the pinned dials against the registry and the jar model of the dish; the prerun current at HEAD; the
pre-boot checks on the real repository, the real staged upload copy, the real profile and the real fixture; the drivers'
refusal (read statically: no driver is invoked) and predictions; and each session's body run against a fake world
behind a fake bus, once as predicted and once per defect flag that must move a named grade off as_predicted.

The fake world answers the harness's real reply shapes (docs/reference/harness-commands.md, the handlers' @reply
lines): `players` a list, {} when nobody is online; lua.read {ok, side, root, n, values, missing}; witness.fields {side,
subject, id, resolved, fields, missing, nils, worldAge, count} and its unresolved {..., resolved false, error};
witness.moddata {side, scope, arg, values, missing, ...}; inv.ids {ok, side, fullType, n, items}, items {} when none;
recipe.add {ok, queued, recipe, base, used, usable, maxTime}; item.rename {ok, item, before, after, synced}; eat.action
{queued, fraction, spawned "found", itemId, ...}; action.cancel {ok, before, after, ...}; stats.all {side, user,
worldAge, stats, missing}; record.set {ok, ..., before, after}; perk.set {perk, requested, side, before, after, route};
minute.ring, tick.ring and perf.local reading their documents through the bus's result files; ghost.* as their
@reply lines. Its model of the mod is the seats' arithmetic as the Task 6 code reads (R2 unprep, vanilla's add, the scale
and stamp, the syncs; R3 scale and restore; R1 the ring and the writer's floor; R4 the type-summed class), so a body
run checks the driver's reads, its pairing and its grades end to end; it is no oracle of the mod (the kernel and
adapter tests are)."""
import copy
import importlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
EXP = os.path.join(os.path.dirname(HERE), "experiments")
sys.path.insert(0, EXP)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import x50_lib as L                   # noqa: E402
import x50_prerun as PR               # noqa: E402
import x48_lib as L48                 # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
DRIVERS = {k: v["driver"] for k, v in L.SESSIONS.items()}
GRADES = {
    "x501": {"WRAP", "ANCHOR", "SCALE", "CLIENT", "COUNTS", "RENAME", "RELOG", "Z"},
    "x502": {"H1", "RING", "FLOOR_OF", "RISE", "LAST", "OFFLINE", "RELEASE", "REPLAY_hedonics.f", "REPLAY_moodLast.u",
             "Z"},
    "x503": {"RING", "PRE", "SATED", "HUNGRY", "RATIO", "REMAINDER", "CANCEL", "I2", "COUNTS", "Z"},
    "x504": {"RING", "CLASS_A", "CLASS_B", "DISH_EAT", "IDLE", "F", "SMOKE", "P99", "MAX", "STARVE", "S", "Z"},
}


# ================================================================ the pinned numbers
def test_the_pinned_dials_are_the_registrys():
    import dials as DL
    v = DL.values()
    assert len(L.PREP_KNOTS) == 3 and L.PREP_KNOTS[0][0] == 0.0 and L.PREP_KNOTS[2][0] == 10.0
    assert L.PREP_KNOTS[0][1] == v["hedonics.PREP_KNOTS.1.2"]
    assert L.PREP_KNOTS[1][0] == v["hedonics.PREP_KNOTS.2.1"]
    assert L.PREP_KNOTS[2][1] == v["hedonics.PREP_KNOTS.3.2"]
    assert [list(k) for k in L.FLOOR_KNOTS] == [[v["hedonics.FLOOR_KNOTS.1.1"], 0.0],
                                                [v["hedonics.FLOOR_KNOTS.2.1"], v["hedonics.FLOOR_KNOTS.2.2"]],
                                                [v["hedonics.FLOOR_KNOTS.3.1"], v["hedonics.FLOOR_KNOTS.3.2"]]]
    assert L.SHARE_MIN_KCAL == v["hedonics.SHARE_MIN_KCAL"] and L.ALLIES_F == v["hedonics.ALLIES_F"]
    assert L.CLASS_W == v["hedonics.CLASS_W"]
    assert v["hedonics.ALLIES_LEVEL"] == 2 and L.ALLIES_AT == v["hungerCurve.Y.4"]


def test_the_jar_model_of_the_dish():
    assert L.VANILLA_D == [-5.0, -10.0, -15.0, -17.0, -25.0, -30.0, -32.0]
    # the over-stuffing excess: a fourth type at Cooking 0 is free (L398-L399), never at 3 or 10
    assert L.vanilla_dish(L.DISH_ADDS + (L.LATE_ADD,), 0)[-1] == -25.0
    assert L.vanilla_dish(("Base.Carrots", "Base.Carrots", "Base.Carrots"), 3) == [-5.0, -5.0, 0.0]
    assert L.prep_scale(0) == 0.8 and L.prep_scale(3) == 1.0 and L.prep_scale(10) == 1.5
    assert abs(L.floor_of(0.631104) - 7.86624) < 1e-9 and L.floor_of(0.4) == 0.0 and L.floor_of(1.0) == 30.0


def test_the_prerun_is_current_and_reads_as_documented():
    for key in L.SESSIONS:
        pr = L.prerun_current(key, REPO, PR.compute)
        assert pr["ok"], (key, pr.get("diff"))
    p = L.load_prerun()
    assert [e["f"] for e in p["x502"]["eats"]] == [0.0, 0.0, 7.86624, 21.8604]
    assert p["x502"]["release"]["after"]["f"] == 0.0 and p["x502"]["offline"]["s_moved_h"] > 0.25
    assert p["x502"]["offline"]["before"]["f"] == p["x502"]["offline"]["after"]["f"]
    assert p["x501"]["rename_d10_potato"] == -45.0 and p["x501"]["compounded_d10_potato"] == -63.75
    assert p["x504"]["A"]["class"] == "savoury" and p["x504"]["A"]["heaviest_portion_class"] == "fatty"
    assert p["x504"]["B"]["class"] == "fatty"


# ================================================================ the pre-boot checks and the drivers
def test_the_profile_passes_its_checks():
    import tomllib
    text = open(os.path.join(REPO, "testing", "profiles", L.PROFILE + ".toml"), encoding="utf-8").read()
    c = L.profile_doc_checks(L.PROFILE, tomllib.loads(text), text)
    assert all(c.values()), c
    doc = tomllib.loads(text)
    doc["sandbox"]["NR"]["Mode"] = 2
    assert L.profile_doc_checks(L.PROFILE, doc, text)["nr_block"] is False
    doc = tomllib.loads(text)
    doc["mods"][1]["path"] = "mod/NutritionRevamp"
    assert L.profile_doc_checks(L.PROFILE, doc, text)["mod_staged"] is False


@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_preboot_on_the_repository_and_its_refusals(key):
    pre, ok = L.preboot(key, DRIVERS[key])
    if pre.get("no_prior_artifact") is False:
        pytest.skip("the session's artifact is committed: preboot refuses it by design")
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert ok, {k: v for k, v in pre.items() if v is not True}
    other = sorted(k for k in L.SESSIONS if k != key)[0]
    assert L.preboot(key, DRIVERS[other])[1] is False                     # a driver naming another session
    stale = L.preboot(key, DRIVERS[key], compute=lambda keys: {key: {"x": 1}})
    assert stale[1] is False and stale[0]["prerun_current"] is False


@pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, L.STAGE_ROOT)), reason="release/ (gitignored) not staged")
def test_the_staged_copy_is_the_pinned_commit():
    mg = L.staged_gate()
    assert mg["ok"], mg
    assert mg["staged_version"] == L.STAGED_VERSION


@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_the_driver_names_its_session_refuses_arguments_and_predicts_every_grade(key):
    name = DRIVERS[key]
    src = open(os.path.join(EXP, name), encoding="utf-8").read()
    assert f'KEY = "{key}"' in src and f'PREFIX = "{key}"' in src and f'PROFILE = "{L.PROFILE}"' in src
    assert name.startswith(key + "_")
    i_ref, i_main = src.index("L.parse_argv(sys.argv[1:]"), src.index("L.main(KEY")
    assert i_ref < i_main and "sys.exit(refusal)" in src[i_ref:i_main]
    assert L.parse_argv(["--help"], name) and L.parse_argv([], name) is None
    D = importlib.import_module(name[:-3])
    assert set(D.PRED) == GRADES[key] and all(D.PRED.values())
    assert D.BUDGET_S <= 470.0 and D.ARTIFACT == L.SESSIONS[key]["artifact"]


# ================================================================ the pure grades: x501
SAME = object()


def pair(v, st, cv=None, cst=SAME, w=10.0):
    cv = v if cv is None else cv
    cst = st if cst is SAME else cst
    md = {} if st is None else {"NR_PrepS": st}
    cmd = {} if cst is None else {"NR_PrepS": cst}
    return {"s0": {"fields": {"getUnhappyChangeUnmodified": v}, "md": md, "wall": w, "resolved": True},
            "c": {"fields": {"getUnhappyChangeUnmodified": cv}, "md": cmd, "resolved": True},
            "s1": {"fields": {"getUnhappyChangeUnmodified": v}, "md": dict(md), "wall_after": w + 0.4,
                   "resolved": True}}


def dishes(scale_fn=lambda lv, k, v: v * L.prep_scale(lv), stamp_fn=lambda lv, k: L.prep_scale(lv)):
    D = {}
    for lv in L.LEVELS:
        D[f"D{lv}"] = {"adds": [{"add": f"{t}@{lv}", "completed": True,
                                 "read": pair(scale_fn(lv, k, L.VANILLA_D[k]), stamp_fn(lv, k))}
                                for k, t in enumerate(L.DISH_ADDS)], "ref": f"#{lv + 100}"}
    return D


def test_anchor_and_scale_read_the_model_and_fail_a_compounded_or_unstamped_dish():
    D = dishes()
    assert L.grade_anchor(D)[0] == "as_predicted" and L.grade_scale(D)[0] == "as_predicted"
    comp = dishes(scale_fn=lambda lv, k, v: v * L.prep_scale(lv) ** (k + 1))
    assert L.grade_scale(comp)[0] == "falsified"
    none = dishes(scale_fn=lambda lv, k, v: v)
    assert L.grade_scale(none)[0] == "falsified"
    nostamp = dishes(stamp_fn=lambda lv, k: None)
    assert L.grade_scale(nostamp)[0] == "falsified" and L.grade_anchor(nostamp)[0] == "falsified"
    off_model = dishes(scale_fn=lambda lv, k, v: (v - 1.0) * L.prep_scale(lv))
    assert L.grade_anchor(off_model)[0] == "falsified" and L.grade_scale(off_model)[0] == "as_predicted"
    assert L.grade_scale({})[0] == "unmeasured" and L.grade_anchor({})[0] == "unmeasured"


def test_client_needs_a_valid_pair_and_fails_an_unsynced_copy():
    D = dishes()
    assert L.grade_client(D)[0] == "as_predicted"
    D["D10"]["adds"][2]["read"] = pair(-22.5, 1.5, cv=-15.0)
    assert L.grade_client(D)[0] == "falsified"
    D = dishes()
    D["D0"]["adds"][1]["read"] = pair(-8.0, 0.8, cst=None)
    assert L.grade_client(D)[0] == "falsified"
    def spanning(span):
        r = pair(-5.0, 1.0, w=0.0)
        r["s1"]["wall_after"] = span
        return {f"D{lv}": {"adds": [{"read": r}]} for lv in L.LEVELS}
    assert L.grade_client(spanning(10.5))[0] == "unmeasured"              # past PAIR_SLACK_S: no valid pair
    assert not L.pair_ok(spanning(10.5)["D3"]["adds"][0]["read"])
    assert L.pair_ok(spanning(6.0)["D3"]["adds"][0]["read"])              # six bus steps, s0 = s1: valid (T7-1)
    assert L.grade_client(spanning(6.0))[0] == "as_predicted"
    moved = spanning(6.0)
    moved["D3"]["adds"][0]["read"]["s1"]["fields"]["getUnhappyChangeUnmodified"] = -10.0
    assert not L.pair_ok(moved["D3"]["adds"][0]["read"])                  # s0 != s1: the bracket refuses it
    server_only = {f"D{lv}": {"adds": [{"read": {"s0": pair(-5.0, 1.0)["s0"]}}]} for lv in L.LEVELS}
    assert L.grade_client(server_only) == ("unmeasured", {"pairs": 0, "invalid_pairs": 0, "off": []}, 0)


def test_wrap_and_counts():
    S = {"hstats": {"NutritionRevamp.server.hedonics.wrappedCook": True}}
    perks = [{"level": 3, "reply": {"after": 3}}]
    assert L.grade_wrap(S, perks)[0] == "as_predicted"
    assert L.grade_wrap({"hstats": {"NutritionRevamp.server.hedonics.wrappedCook": False}}, perks)[0] == "falsified"
    assert L.grade_wrap(S, [{"level": 10, "reply": {"after": 7}}])[0] == "falsified"
    assert L.grade_wrap({}, perks)[0] == "unmeasured"
    D = dishes()
    key = "NutritionRevamp.server.hedonics.stats."
    D["S"] = {"hstats": {key + k: 0 for k in ("cooks", "prepped", "unprepped", "cookFailures")}}
    D["C"] = {"hstats": {key + "cooks": 15, key + "prepped": 15, key + "unprepped": 8, key + "cookFailures": 0}}
    assert L.unprep_pred(D) == 8 and L.grade_counts_501(D)[0] == "as_predicted"
    D["C"]["hstats"][key + "unprepped"] = 0                               # the restore never ran: compounding
    assert L.grade_counts_501(D)[0] == "falsified"
    D["C"] = {}
    assert L.grade_counts_501(D)[0] == "unmeasured"


def test_rename_and_relog():
    rn = {"after": {"10": pair(-37.5, 1.5), "3": pair(-25.0, 1.0)},
          "adds": [{"add": f"{L.LATE_ADD}@3", "completed": True, "read": pair(-30.0, 1.0)},
                   {"add": f"{L.LATE_ADD}@10", "completed": True, "read": pair(-45.0, 1.5)}]}
    assert L.grade_rename({"RN": rn})[0] == "as_predicted"
    wiped = copy.deepcopy(rn)
    wiped["after"]["10"] = pair(-37.5, None)
    wiped["adds"][1]["read"] = pair(-63.75, 1.5)
    assert L.grade_rename({"RN": wiped})[0] == "falsified"
    assert L.grade_rename({"RN": {}})[0] == "unmeasured"
    late = copy.deepcopy(rn)
    late["adds"][1] = {"add": f"{L.LATE_ADD}@10", "completed": False}  # the Potato add never completed
    assert L.grade_rename({"RN": late})[0] == "unmeasured"
    late["after"]["10"] = pair(-37.5, None)                               # but the stamp read gone: the stamp half
    assert L.grade_rename({"RN": late})[0] == "falsified"
    late["after"]["10"]["s0"]["resolved"] = False                         # the dish itself unread: no stamp half
    assert L.grade_rename({"RN": late})[0] == "unmeasured"
    rl = {"before": {str(lv): pair(-25.0 * L.prep_scale(lv), L.prep_scale(lv)) for lv in L.LEVELS},
          "after": {str(lv): pair(-25.0 * L.prep_scale(lv), L.prep_scale(lv)) for lv in L.LEVELS},
          "adds": [{"add": f"{L.RELOG_ADD}@3", "completed": True, "read": pair(-32.0, 1.0)},
                   {"add": f"{L.RELOG_ADD}@10", "completed": True, "read": pair(-48.0, 1.5)}]}
    assert L.grade_relog({"RL": rl})[0] == "as_predicted"
    lost = copy.deepcopy(rl)
    lost["after"]["0"] = pair(-20.0, None)
    assert L.grade_relog({"RL": lost})[0] == "falsified"
    moved = copy.deepcopy(rl)
    moved["adds"][1]["read"] = pair(-51.0, 1.5)
    assert L.grade_relog({"RL": moved})[0] == "falsified"
    assert L.grade_relog({"RL": {}})[0] == "unmeasured"
    nopep = copy.deepcopy(rl)
    nopep["adds"][1] = {"add": f"{L.RELOG_ADD}@10", "completed": False}
    assert L.grade_relog({"RL": nopep})[0] == "unmeasured"
    nopep["after"]["10"] = pair(-37.5 * 1.5, 1.5)                         # a dish moved: the dish half alone
    assert L.grade_relog({"RL": nopep})[0] == "falsified"
    unstamped = copy.deepcopy(rl)                                          # no stamp before: D0's row skipped
    unstamped["before"]["0"] = pair(-20.0, None)
    unstamped["after"]["0"] = pair(-20.0, None)
    v, obs, n = L.grade_relog({"RL": unstamped})
    assert v == "as_predicted" and n == 2 and "0" not in [r["level"] for r in obs["dishes"]]


# ================================================================ the pure grades: x502
def ring_rec(p, a, f=None, s=2.75, i=1, u=None, extra=None):
    rec = {f"hedonics.p.{k + 1}": (p if k == 0 else 0.0) for k in range(L.RING_N)}
    rec.update({f"hedonics.a.{k + 1}": (a if k == 0 else 0.0) for k in range(L.RING_N)})
    ff = L.floor_of(L.share_of([p], [a])) if f is None else f
    rec.update({"hedonics.f": ff, "hedonics.s": s, "hedonics.i": i, "moodLast.u": ff + 9.25 if u is None else u})
    rec.update(extra or {})
    return rec


def test_floor_of_and_rise():
    eats = [{"tag": f"E{k}", "rec": ring_rec(315.552 * k, 315.552 * k), "landed": True, "food": L.BUTTER}
            for k in range(1, 5)]
    reads = [{"tag": e["tag"], "rec": e["rec"]} for e in eats]
    assert L.grade_floor_of(reads)[0] == "as_predicted"
    bad = copy.deepcopy(reads)
    bad[3]["rec"]["hedonics.f"] = 0.0
    assert L.grade_floor_of(bad)[0] == "falsified"
    assert L.grade_floor_of([{"rec": {}}])[0] == "unmeasured"
    zero = [{"tag": "E1", "rec": ring_rec(100.0, 100.0)}, {"tag": "E2", "rec": ring_rec(0.0, 0.0)}]
    assert zero[0]["rec"]["hedonics.f"] == 0.0
    assert L.grade_floor_of(zero)[0] == "unmeasured"                       # f 0 = floorOf: no floor to read
    v, obs, n = L.grade_floor_of(reads + zero)                            # E1, E2 (shares 0.21, 0.42) at the foot
    assert v == "as_predicted" and n == 2 and obs["rows_up"] == 2
    pred = [0.0, 0.0, 7.86624, 21.8604]
    assert L.grade_rise(eats, pred)[0] == "as_predicted"
    flat = copy.deepcopy(eats)
    for e in flat:
        e["rec"]["hedonics.f"] = 0.0
    assert L.grade_rise(flat, pred)[0] == "falsified"
    under = copy.deepcopy(eats)
    under[3]["rec"]["moodLast.u"] = 5.0                                   # the floor not composed
    assert L.grade_rise(under, pred)[0] == "falsified"
    assert L.grade_rise(eats[:2], pred)[0] == "unmeasured"


def test_last_intake():
    ok = {"landed": True, "food": L.BUTTER, "rec": {"lastIntake.fullType": L.BUTTER, "lastIntake.plain": True,
                                                    "lastIntake.class": "fatty", "lastIntake.allies": 1}}
    pb = {"landed": True, "food": L.PEANUT, "rec": {"lastIntake.fullType": L.PEANUT, "lastIntake.plain": False,
                                                    "lastIntake.class": "fatty", "lastIntake.allies": 1}}
    assert L.grade_last([ok, pb])[0] == "as_predicted"
    wrong = copy.deepcopy(ok)
    wrong["rec"]["lastIntake.plain"] = False
    assert L.grade_last([wrong, pb])[0] == "falsified"
    assert L.grade_last([{"landed": False, "food": L.BUTTER}])[0] == "unmeasured"


def test_offline_needs_the_ring_unmoved_and_its_stamp_moved_by_the_absence():
    rl = {"quit_age": 3.30, "depart_age": 3.32, "launch_age": 3.42, "back_age": 3.60}
    b = {"rec": ring_rec(1262.2, 1262.2, s=2.7567), "age": 3.30}
    a = {"rec": ring_rec(1262.2, 1262.2, s=2.7567 + 0.27), "age": 3.63}
    assert L.grade_offline({"before": b, "after": a, "relog": rl})[0] == "as_predicted"
    frozen = {"rec": ring_rec(1262.2, 1262.2, s=2.7567), "age": 3.63}     # the resume missing: s never moved
    assert L.grade_offline({"before": b, "after": frozen, "relog": rl})[0] == "falsified"
    rolled = {"rec": ring_rec(1262.2, 1262.2, s=2.7567 + 0.27, i=2), "age": 3.63}
    assert L.grade_offline({"before": b, "after": rolled, "relog": rl})[0] == "falsified"
    moved_u = {"rec": ring_rec(1262.2, 1262.2, s=2.7567 + 0.27, u=40.0), "age": 3.63}
    assert L.grade_offline({"before": b, "after": moved_u, "relog": rl})[0] == "falsified"
    short = dict(rl, launch_age=3.36)                                     # 2.4 game minutes offline
    assert L.grade_offline({"before": b, "after": a, "relog": short})[0] == "unmeasured"
    late = {"rec": ring_rec(1262.2, 1262.2, s=2.35), "age": 3.30}         # 0.95 h into the slot
    assert L.grade_offline({"before": late, "after": a, "relog": rl})[0] == "unmeasured"
    assert L.grade_offline({})[0] == "unmeasured"
    empty = {"rec": ring_rec(0.0, 0.0, s=2.7567), "age": 3.30}            # an empty ring: nothing to keep
    empty_after = {"rec": ring_rec(0.0, 0.0, s=2.7567 + 0.27), "age": 3.63}
    assert L.grade_offline({"before": empty, "after": empty_after, "relog": rl})[0] == "unmeasured"
    nofloor = {"rec": ring_rec(100.0, 100.0, s=2.7567), "age": 3.30}       # kcal but f 0
    nofloor_after = {"rec": ring_rec(100.0, 100.0, s=2.7567 + 0.27), "age": 3.63}
    assert L.grade_offline({"before": nofloor, "after": nofloor_after, "relog": rl})[0] == "unmeasured"


def test_release():
    before = {"rec": ring_rec(1262.2, 1262.2)}
    after = {"rec": ring_rec(1262.2, 2592.2), "landed": True}
    assert L.grade_release(after, before)[0] == "as_predicted"
    stuck = {"rec": ring_rec(1262.2, 2592.2, f=21.86, u=31.1), "landed": True}
    assert L.grade_release(stuck, before)[0] == "falsified"
    held = {"rec": ring_rec(1262.2, 2592.2, u=31.1), "landed": True}     # f fell but the target kept it
    assert L.grade_release(held, before)[0] == "falsified"
    assert L.grade_release({"landed": False}, before)[0] == "unmeasured"


def test_eat_events_place_each_eat_at_its_ring_row():
    rows = [{"s": 10, L.EATS_G: 0}, {"s": 11, L.EATS_G: 1}, {"s": 12, L.EATS_G: 1}, {"s": 13, L.EATS_G: 2}]
    eats = [{"tag": "E1", "food": L.BUTTER, "landed": True, "frac": 0.1,
             "item0": {"calories": 3155.52, "carbs": 0.26, "lipids": 356.97, "proteins": 3.74, "hungChange": -0.24}},
            {"tag": "REL", "food": L.PEANUT, "landed": True, "frac": 0.5,
             "item0": {"calories": 2659.9, "carbs": 99.23, "lipids": 228.45, "proteins": 98.79, "hungChange": -0.25}}]
    ev, notes = L.eat_events(rows, eats)
    assert [e["s"] for e in ev] == [11, 13] and not notes
    assert ev[0]["cal"] == 3155.52 and ev[0]["frac"] == 0.1 and "foodType" not in ev[0]
    assert ev[1]["foodType"] == "NoExplicit" and ev[1]["hunger"] == -0.25
    ev, notes = L.eat_events(rows[:2], eats)
    assert len(ev) == 1 and notes


def test_the_replay_grade_fails_a_field_off_the_replay(tmp_path, monkeypatch):
    import replay_live as RL
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"left_in_place": []}}
    xs = X.Xs(out, node=lambda s: s, ask=lambda *a, **k: {}, clock=lambda: 0.0, sleep=lambda s: None)
    S = L.Floor(xs, "x502", run_dir=str(tmp_path), prerun={})
    (tmp_path / "start.json").write_text(json.dumps({"rec": {}}), encoding="utf-8")
    monkeypatch.setattr(RL, "replay_live", lambda *a, **k: ([{"s": 1}], None))
    for over, want in ((0, "as_predicted"), (3, "falsified")):
        monkeypatch.setattr(RL, "diff", lambda rep, rows, tol, o=over: {
            "fields": {f: {"n": 5, "max": 0.0, "over": o, "worst_s": None} for f in tol}, "findings": []})
        S.grade_replay([{"s": 1, L.EATS_G: 0}])
        assert out["verdicts"]["REPLAY_hedonics.f"]["verdict"] == want
    S.grade_replay([])
    assert out["verdicts"]["REPLAY_moodLast.u"]["verdict"] == "unmeasured"


# ================================================================ the pure grades: x503
def an_eat(arm, d, u_rt=20.0, f=0.3, allies=1, f0=20.0, f1=None, h0=-0.24, h1=None, landed=True, t_fall=0.0):
    h1 = h0 * (1 - f) if h1 is None else h1
    f1 = f0 * (1 - f) if f1 is None else f1
    return {"arm": arm, "landed": landed, "frac": f,
            "stats0": {"Unhappiness": 60.0, "Hunger": 0.002 if arm == "R3S" else 0.32},
            "stats1": {"Unhappiness": 60.0 + d - t_fall},
            "rec0": {"moodLast.u": 20.0}, "rec1": {"moodLast.u": 20.0 - t_fall, "lastIntake.allies": allies},
            "item0": {"fields": {"getUnhappyChange": u_rt, "getUnhappyChangeUnmodified": f0, "getHungChange": h0}},
            "item1": {"fields": {"getUnhappyChangeUnmodified": f1, "getHungChange": h1}, "resolved": True}}


def allies_eats(k=1.0, scale=0.6):
    return [an_eat("R3S", 20 * 0.3 * k), an_eat("R3H", 20 * 0.3 * scale * k, allies=scale, f0=14.0, h0=-0.168),
            an_eat("R3C", 30 * 0.3 * scale * k, u_rt=30.0, f=0.3, allies=scale, f0=30.0)]


def test_sated_hungry_ratio_and_cancel():
    for k in (1.0, L.UTENSIL_SAD):
        eats = allies_eats(k)
        for fn in (L.grade_sated, L.grade_hungry, L.grade_ratio, L.grade_cancel):
            assert fn(eats)[0] == "as_predicted", (fn.__name__, k, fn(eats))
    none = allies_eats(scale=1.0)
    for e in none[1:]:
        e["rec1"]["lastIntake.allies"] = 0.6                              # the flag set but no scale applied
    assert L.grade_hungry(none)[0] == "falsified" and L.grade_ratio(none)[0] == "falsified"
    assert L.grade_cancel(none)[0] == "falsified"
    eats = allies_eats()
    eats[0]["rec1"]["lastIntake.allies"] = 0.6
    assert L.grade_sated(eats)[0] == "falsified"
    fell = allies_eats()
    fell[1] = an_eat("R3H", 3.6, allies=0.6, f0=14.0, h0=-0.168, t_fall=1.5)   # the writer released 1.5 meanwhile
    assert L.grade_hungry(fell)[0] == "as_predicted"
    assert L.grade_sated([an_eat("R3S", 6.0, landed=False)])[0] == "unmeasured"
    whole = allies_eats()
    whole[2]["frac"] = 1.0
    assert L.grade_cancel(whole)[0] == "unmeasured"
    # each arm gated on its own before-read HUNGER: a seed that did not hold reads unmeasured, never falsified
    for arm, h, fn in (("R3H", 0.2, L.grade_hungry), ("R3H", None, L.grade_hungry), ("R3C", 0.25, L.grade_cancel),
                       ("R3S", 0.3, L.grade_sated), ("R3S", 0.3, L.grade_ratio), ("R3H", 0.1, L.grade_ratio)):
        e = allies_eats(scale=1.0)                                          # every scale off: falsified if graded
        L.arm_eat(e, arm)["stats0"]["Hunger"] = h
        v, obs, n = fn(e)
        assert v == "unmeasured" and n == 0, (arm, h, fn.__name__, v)
    sated = allies_eats()
    sated[0]["stats0"]["Hunger"] = 0.25                                   # at ALLIES_AT: still sated
    assert L.grade_sated(sated)[0] == "as_predicted"


def test_pre_and_remainder():
    eats = allies_eats()
    assert L.grade_pre(eats)[0] == "as_predicted"
    eats[1]["stats0"]["Hunger"] = 0.2
    assert L.grade_pre(eats)[0] == "falsified"
    eats = allies_eats()
    assert L.grade_remainder(eats)[0] == "as_predicted"
    eats[1]["item1"]["fields"]["getUnhappyChangeUnmodified"] = (14.0 - 2.4) * 0.7   # the lowered field kept
    assert L.grade_remainder(eats)[0] == "falsified"
    assert L.grade_remainder([])[0] == "unmeasured"


def i2c_eat(c_f1=5.0):
    """The vanilla control: the stale potato, a quarter eaten sated (5 -> 3.75; read-time 13.75)."""
    return {"arm": "I2C", "landed": True, "frac": 0.25, "stats0": {"Hunger": 0.002},
            "item0": {"fields": {"getUnhappyChangeUnmodified": 5.0, "getUnhappyChange": 15.0}},
            "item1": {"fields": {"getUnhappyChangeUnmodified": 3.75, "getUnhappyChange": 13.75}, "resolved": True},
            "citem0": {"fields": {"getUnhappyChangeUnmodified": 5.0}},
            "citem1": {"fields": {"getUnhappyChangeUnmodified": c_f1}}}


def i2_eat(c_f1, s_rt0=13.75, hunger=0.32):
    return {"arm": "I2", "landed": True, "frac": 1.0 / 3.0, "stats0": {"Hunger": hunger},
            "item0": {"fields": {"getUnhappyChangeUnmodified": 3.75, "getUnhappyChange": s_rt0}},
            "item1": {"fields": {"getUnhappyChangeUnmodified": 2.5, "getUnhappyChange": 12.5}, "resolved": True},
            "citem0": {"fields": {"getUnhappyChangeUnmodified": 5.0}},
            "citem1": {"fields": {"getUnhappyChangeUnmodified": c_f1}}}


def test_i2_reads_the_client_copy_undoubled():
    c = i2c_eat()
    assert L.grade_i2([c, i2_eat(2.5)])[0] == "as_predicted"
    assert L.grade_i2([c, i2_eat(5.0)])[0] == "as_predicted"              # the client kept its own
    assert L.grade_i2([c, i2_eat(12.5)])[0] == "falsified"                # the read-time value written in
    assert L.grade_i2([c, i2_eat(7.0)])[0] == "falsified"
    assert L.grade_i2([c, i2_eat(2.5, s_rt0=3.75)])[0] == "unmeasured"     # no stale term
    assert L.grade_i2([c, i2_eat(12.5, hunger=0.2)])[0] == "unmeasured"     # not Hungry: never falsified
    # the control: vanilla's own eat doubles the client's copy, so a doubled I2 is vanilla's, not the mod's
    v, obs, n = L.grade_i2([i2c_eat(13.75), i2_eat(12.5)])
    assert v == "unmeasured" and "I2C" in obs["why"] and obs["doubled_c"] is True
    assert L.grade_i2([i2_eat(12.5)])[0] == "unmeasured"                   # the control unread


def test_counts_503():
    key = "NutritionRevamp.server.hedonics.stats."
    D = {"eats": allies_eats() + [i2c_eat()],                             # the sated control adds no ally
         "S": {"hstats": {key + "allies": 0, key + "restores": 0, key + "alliesFailures": 0}},
         "C": {"hstats": {key + "allies": 2, key + "restores": 2, key + "alliesFailures": 0}}}
    assert L.grade_counts_503(D)[0] == "as_predicted"
    D["C"]["hstats"][key + "restores"] = 0
    assert L.grade_counts_503(D)[0] == "falsified"
    D["C"] = {}
    assert L.grade_counts_503(D)[0] == "unmeasured"


# ================================================================ the pure grades: x504
def test_class():
    keys = ("savoury", "fatty", "staple", "sweet")

    def P(cls, rose):
        r0 = {f"monotony.t.[@{k}].n": 0.0 for k in keys}
        r1 = dict(r0, **{f"monotony.t.[@{rose}].n": 0.03, "lastIntake.class": cls})
        return {"rec0": r0, "rec1": r1, "eat": {"landed": True}}
    assert L.grade_class({"A": P("savoury", "savoury")}, "A", "savoury", "savoury", flat=("fatty",))[0] == \
        "as_predicted"
    assert L.grade_class({"A": P("fatty", "fatty")}, "A", "savoury", "savoury", flat=("fatty",))[0] == "falsified"
    assert L.grade_class({"A": {"eat": {"landed": False}}}, "A", "savoury", "savoury")[0] == "unmeasured"
    unread = P("savoury", "savoury")
    del unread["rec1"]["monotony.t.[@savoury].n"]                        # the count unread: never a falsification
    assert L.grade_class({"A": unread}, "A", "savoury", "savoury", flat=("fatty",))[0] == "unmeasured"


def dish_eat(u, d, landed=True):
    return {"eat": {"landed": landed, "frac": 1.0, "stats0": {"Unhappiness": 60.0},
                    "stats1": {"Unhappiness": 60.0 + d}, "rec0": {"moodLast.u": 0.0}, "rec1": {"moodLast.u": 0.0},
                    "item0": {"fields": {"getUnhappyChange": u}}}}


def test_dish_eat():
    for k in (1.0, L.UTENSIL_GLAD):
        D = {"A": dish_eat(-4.666667, -4.666667 * k), "B": dish_eat(-9.333333, -9.333333 * k)}
        v, obs, n = L.grade_dish_eat(D)
        assert v == "as_predicted" and n == 2 and obs["k"] == k
    unscaled = {"A": dish_eat(-4.666667, -5.0), "B": dish_eat(-9.333333, -10.0)}     # the eat read vanilla's value
    assert L.grade_dish_eat(unscaled)[0] == "falsified"
    mixed = {"A": dish_eat(-4.666667, -4.666667), "B": dish_eat(-9.333333, -9.333333 * 1.25)}
    assert L.grade_dish_eat(mixed)[0] == "falsified"                       # one k for both dishes
    assert L.grade_dish_eat({"A": dish_eat(0.0, 0.0), "B": dish_eat(-9.3, -9.3, landed=False)})[0] == "unmeasured"
    assert L.grade_dish_eat({})[0] == "unmeasured"


def ring_doc(n=600, busy=2.0, end=100.0, minute_add=0.0, t0=1000):
    fr = {k: [] for k in ("frame", "start", "stop", "busy", "period", "endPeriod", "minute", "runs", "ghostMs")}
    for i in range(n):
        m = 1 if i % 37 == 0 else 0
        b = busy + (minute_add if m else 0.0)
        for k, v in (("frame", i), ("start", t0 + 100 * i), ("stop", t0 + 100 * i + b), ("busy", b), ("period", 100.0),
                     ("endPeriod", end + (minute_add if m else 0.0)), ("minute", m), ("runs", 0), ("ghostMs", 0)):
            fr[k].append(v)
    return {"frames_list": fr}


def perf_doc(n=60, mx=110.0, t0=1000):
    return {"samples_list": {"wall": [t0 + 1000 * i for i in range(n)], "max": [mx] * n}}


def test_rule6_grades():
    idle = L.arm_summary({"ring_doc": ring_doc(), "perf_doc": perf_doc(), "drop_windows": []})
    load = L.arm_summary({"ring_doc": ring_doc(minute_add=8.0), "perf_doc": perf_doc(mx=118.0), "drop_windows": []})
    stats = {"runs": 900, "starvedEvents": 0, "failures": 0, "storeGhostKeys": 0, "neverRun": 0}
    ok = L.grade_rule6(idle, load, stats, {"ok": True}, {"ok": True, "ghosts": 59})
    assert {k: v[0] for k, v in ok.items()} == {k: "as_predicted" for k in ok}
    heavy = L.arm_summary({"ring_doc": ring_doc(end=100.0, minute_add=40.0), "perf_doc": perf_doc(mx=150.0),
                           "drop_windows": []})
    r = L.grade_rule6(idle, heavy, dict(stats, starvedEvents=2, failures=1), {"ok": True}, {"ok": True, "ghosts": 3})
    assert r["MAX"][0] == "falsified" and r["STARVE"][0] == "falsified" and r["S"][0] == "falsified"
    assert r["SMOKE"][0] == "falsified"
    hot = L.arm_summary({"ring_doc": ring_doc(end=125.0), "perf_doc": perf_doc(), "drop_windows": []})
    assert L.grade_rule6(idle, hot, stats, {"ok": True}, {"ok": True, "ghosts": 59})["P99"][0] == "falsified"
    busy_idle = L.arm_summary({"ring_doc": ring_doc(busy=12.0, n=100), "perf_doc": perf_doc(), "drop_windows": []})
    r = L.grade_rule6(busy_idle, load, stats, {"ok": True}, {"ok": True, "ghosts": 59})
    assert r["IDLE"][0] == "falsified" and r["F"][0] == "falsified"
    empty = L.grade_rule6({}, {}, None, None, None)
    assert empty["P99"][0] == "unmeasured" and empty["STARVE"][0] == "unmeasured" and empty["IDLE"][0] == "unmeasured"
    # a frame overlapping a bus step inside the window is dropped
    s = L.arm_summary({"ring_doc": ring_doc(n=10), "perf_doc": perf_doc(n=3), "drop_windows": [[1000, 1250]]})
    assert s["frames"] == 7


def test_z_fails_a_hedonics_failure_counter_rising():
    key = "NutritionRevamp.server.hedonics.stats."
    out = {"logs": {"mod_error": []}, "admin_lua_error": False}
    D = {"S": {"hstats": {key + k: 0 for k in L.FAIL_KEYS}}, "C": {"hstats": {key + k: 0 for k in L.FAIL_KEYS}}}
    assert L.grade_z(out, D)[0] == "as_predicted"
    D["C"]["hstats"][key + "cookFailures"] = 1
    assert L.grade_z(out, D)[0] == "falsified"
    assert L.grade_z({"logs": {"mod_error": ["NR_Server_Hedonics.lua: failed: x"]}, "admin_lua_error": False},
                     {})[0] == "falsified"


# ================================================================ the fake world
GM_S = 3.75                                   # a game minute at speed 1, DayLength 4
KCAL = {"Base.Carrots": 25.71, "Base.BaconRashers": 40.09}
SPICE = dict(L.SPICE_N)
ITEMS = {"Base.Butter": dict(cal=3155.52, carbs=0.26, lipids=356.97, proteins=3.74, hung=-0.24, u=20.0, state=0.0),
         "Base.PeanutButter": dict(cal=2659.9, carbs=99.23, lipids=228.45, proteins=98.79, hung=-0.25, u=-15.0,
                                   state=0.0),
         "Base.Lard": dict(cal=4095.08, carbs=0.0, lipids=454.0, proteins=0.0, hung=-0.24, u=30.0, state=0.0),
         "Base.Potato": dict(cal=69.97, carbs=15.93, lipids=0.1, proteins=1.7, hung=-0.18, u=5.0, state=0.0)}


class FakeBus:
    def __init__(self, results_dir):
        self.results_dir = results_dir

    def wait_result(self, name, timeout=30, after=None):
        with open(os.path.join(self.results_dir, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)


class FakeServer:
    def __init__(self, world, results_dir):
        self.w = world
        self.errors = []
        self.bus = FakeBus(results_dir)

    def rcon(self, cmd):
        return self.w.rcon(cmd)


class FakeClient:
    def __init__(self, world, user="admin"):
        self.w = world
        self.username = user
        self.seen = {}
        self.alive = True
        self.console = os.devnull

    def quit(self, timeout=None):
        self.alive = False
        self.w.logout()
        return 0


def rget(d, path):
    """lua.read's grammar over nested dicts and lists: [a.b] one literal key, a numeric segment the 1-based index."""
    segs, i = [], 0
    while i < len(path):
        if path[i] == "[":
            j = path.index("]", i)
            segs.append(path[i + 1:j])
            i = j + 2
        else:
            j = path.find(".", i)
            j = len(path) if j < 0 else j
            segs.append(path[i:j])
            i = j + 1
    cur = d
    for s in segs:
        if isinstance(cur, list) and s.isdigit():
            k = int(s) - 1
            cur = cur[k] if 0 <= k < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(s)
        else:
            return None
    return cur


class World:
    """The dedicated server, admin's client and the mod's hedonics seats as the Task 6 code reads them, stepped one
    game minute every GM_S wall seconds. `flags` are defects."""

    def __init__(self, results_dir, flags=(), latency=True):
        self.dir = results_dir
        self.f = set(flags)
        self.t, self.age, self.speed, self.next_min = 0.0, L48.FIRST_SIGHT["age"], 1, GM_S
        self.online, self.next_id = True, 1000
        self.items, self.pending, self.ring_rows, self.ring_paths, self.s = {}, [], [], None, 0
        self.stats = {"Unhappiness": 0.0, "Hunger": 0.002, "Boredom": 0.0}
        self.rec = {"satiety": {"M": 500.0, "t": self.age}, "moodLast": {"u": 0.0}, "lastSeen": self.age,
                    "monotony": {"t": {}}, "firstSeen": self.age,
                    "body": {"sex": 1, "fm": 14.0, "lm": 51.0, "lx": 0.0}}
        self.cooking, self.writes, self.lastWrite = 2, 0, 1
        self.latency = latency
        self.h = {k: 0 for k in L.HSTATS}
        self.intake = {"eats": 0, "landed": 0}
        self.ghosts, self.load = 0, False
        self.offline_from = None

    # -- the clock
    def clock(self):
        return self.t

    def sleep(self, dt):
        end = self.t + max(dt, 0.01)
        while True:
            due = min([p[0] for p in self.pending] + [self.next_min])
            if due > end:
                break
            self.t = due
            if due == self.next_min:
                self.minute()
                self.next_min += GM_S / self.speed
            else:
                for p in [p for p in self.pending if p[0] <= self.t]:
                    self.pending.remove(p)
                    p[1]()
        self.t = end

    def minute(self):
        self.age += 1.0 / 60.0
        if not self.online:
            self.ring_row(False)
            return
        self.rec["lastSeen"] = self.age
        self.writes += 1
        if self.writes % 8 == 0:
            self.lastWrite += 1
        ring = self.rec.get("hedonics")
        u_mono = 0.0
        f = 0.0
        if ring is not None:
            self.rotate(ring)
            f = 0.0 if "no_floor" in self.f else L.floor_of(L.share_of(ring["p"], ring["a"]))
            if "no_release" in self.f and ring.get("f", 0) > f:
                f = ring["f"]
            ring["f"] = f
        u = min(u_mono + f, L.UNHAPPY_HI)
        prev = self.rec["moodLast"]["u"]
        if u < prev:
            self.stats["Unhappiness"] = max(0.0, self.stats["Unhappiness"] - (prev - u))
        elif self.stats["Unhappiness"] < u:
            self.stats["Unhappiness"] = min(u, self.stats["Unhappiness"] + 22.0 / 60.0)
        self.rec["moodLast"]["u"] = u
        if self.rec["satiety"]["M"] > 3.8:
            self.stats["Hunger"] = max(0.0, self.stats["Hunger"] - 0.002)
        self.ring_row(True)

    def rotate(self, ring):
        d = int(self.age - ring["s"])
        for _ in range(min(d, L.RING_N)):
            ring["i"] = ring["i"] % L.RING_N + 1
            ring["p"][ring["i"] - 1] = 0.0
            ring["a"][ring["i"] - 1] = 0.0
        ring["s"] += d

    def ring_row(self, on):
        if self.ring_paths is None:
            return
        self.s += 1
        row = {"s": self.s, "ev": self.s, "drained": self.s, "age": self.age, "dtM": 1.0, "on": on,
               "HUNGER": self.stats["Hunger"], "UNHAPPINESS": self.stats["Unhappiness"]}
        for p in self.ring_paths:
            row[p] = self.gread(p[3:]) if p.startswith("_G.") else rget(self.rec, p)
        self.ring_rows.append(row)

    # -- the session's own events
    def logout(self):
        self.online = False
        self.offline_from = self.rec["lastSeen"]

    def login(self):
        gap = self.age - self.offline_from
        if "offline_moves" not in self.f:
            if self.rec.get("hedonics") is not None:
                self.rec["hedonics"]["s"] += gap
        if "relog_drops" in self.f:
            for it in self.items.values():
                it["md"].pop("NR_PrepS", None)
        if "relog_new_ids" in self.f:                   # the save reloads every item under a new id
            moved = {}
            for it in self.items.values():
                self.next_id += 1
                it["id"] = self.next_id
                moved[it["id"]] = it
            self.items = moved
        for it in self.items.values():
            it["c_u"], it["c_md"] = it["u"], dict(it["md"])
        self.online = True

    def new_item(self, full):
        self.next_id += 1
        it = {"id": self.next_id, "type": full, "name": full.split(".")[-1], "custom": False, "md": {}, "c_md": {},
              "u": 0.0, "state": 0.0, "hung": -0.1, "base": -0.1, "cal": 0.0, "carbs": 0.0, "lipids": 0.0,
              "proteins": 0.0, "extra": [], "spices": [], "age": 0.0}
        if full in ITEMS:
            v = ITEMS[full]
            it.update(u=v["u"], state=v["state"], hung=v["hung"], base=v["hung"], cal=v["cal"], carbs=v["carbs"],
                      lipids=v["lipids"], proteins=v["proteins"])
        it["c_u"] = it["u"]
        self.items[it["id"]] = it
        return it

    def first(self, full):
        for it in self.items.values():
            if it["type"] == full:
                return it
        return None

    def by_ref(self, ref):
        ref = ref.split("/")[-1]
        if ref.startswith("#"):
            return self.items.get(int(ref[1:]))
        return self.first(ref)

    # -- R2: the add-ingredient seat (the mod's), vanilla's add between its halves
    def complete_add(self, base_id, ing_id):
        self.h["cooks"] += 1
        base, ing = self.items[base_id], self.items.get(ing_id)
        if base["type"] == L.PAN:
            del self.items[base_id]
            base = self.new_item(L.DISH)
            base["u"] = 0.0
        md = base["md"]
        if "NR_PrepS" in md and "compound" not in self.f:
            if base["u"] < 0 and md["NR_PrepS"] != 1.0:
                base["u"] = base["u"] / md["NR_PrepS"]
                self.h["unprepped"] += 1
            md.pop("NR_PrepS")
        t = ing["type"]
        if t in SPICE:
            base["u"] -= 2.0 * SPICE[t]
            base["spices"].append(t)
        else:
            d = sum(1 for e in base["extra"] if e == t)
            if len(base["extra"]) - 2 > self.cooking:
                d += len(base["extra"]) - 2 - 3 * self.cooking
            base["u"] = min(25.0, base["u"] - (5 - 5 * d))
            base["extra"].append(t)
            del self.items[ing_id]
        base["cal"] += KCAL.get(t, 10.0)
        base["hung"] = base["base"] = -0.3
        base["c_u"] = base["u"]                         # vanilla's own sendItemStats (#2658): the field, no modData
        if base["u"] < 0 and "no_seat" not in self.f:
            s = L.prep_scale(self.cooking)
            base["u"] *= s
            md["NR_PrepS"] = s
            self.h["prepped"] += 1
            if "no_client_sync" not in self.f:
                base["c_u"], base["c_md"] = base["u"], dict(md)

    def complete_rename(self, item_id):
        it = self.items[item_id]
        it["md"] = {} if "rename_wipes" in self.f else dict(it["c_md"])

    # -- R3, R1, R4 at the eat (the mod's), vanilla's eat between
    def complete_eat(self, item_id, asked, progress=1.0):
        it = self.items.get(item_id)
        if it is None:
            return
        f = min(1.0, asked * it["base"] / it["hung"]) * progress
        if f <= 0:
            return
        u_rt = it["u"] + it["state"]
        hungry = self.stats["Hunger"] > L.ALLIES_AT
        scaled = u_rt * L.ALLIES_F if (u_rt > 0 and hungry and "no_allies" not in self.f) else u_rt
        field = it["u"]
        written = field - (u_rt - scaled)
        felt = scaled
        if "dish_eat_unscaled" in self.f and it["type"] == L.DISH and it["md"].get("NR_PrepS"):
            felt = it["u"] / it["md"]["NR_PrepS"] + it["state"]       # the eat reading vanilla's unscaled value
        self.stats["Unhappiness"] = min(100.0, max(0.0, self.stats["Unhappiness"] + felt * f))
        kcal = it["cal"] * f
        for k in ("cal", "carbs", "lipids", "proteins", "hung"):
            it[k] *= (1 - f)
        it["u"] = written * (1 - f)
        if scaled < u_rt:
            self.h["allies"] += 1
            if "no_restore" not in self.f and f < 1:
                it["u"] = field * (1 - f)
                self.h["restores"] += 1
        if "doubled" in self.f and scaled < u_rt:          # the mod's Hungry eat sends the read-time value
            it["c_u"] = it["u"] + it["state"]
        if "vanilla_doubles" in self.f:                    # vanilla's own eat path does, on every eat
            it["c_u"] = it["u"] + it["state"]
        if it["type"] == L.DISH:
            plain = False
            if "class_portion" in self.f:
                cls = "fatty" if L.BACON in it["extra"] else "savoury"
            else:
                tot = {}
                for t in it["extra"]:
                    tot[t] = tot.get(t, 0.0) + KCAL[t]
                best = max(tot, key=lambda t: tot[t])
                cls = "fatty" if best == L.BACON else "savoury"
        else:
            plain, cls = L.PLAIN_OF[it["type"]], L.CLASS_OF[it["type"]]
        if f >= 1 - 1e-9:
            del self.items[item_id]
        ring = self.rec.setdefault("hedonics", {"s": self.age, "i": 1, "p": [0.0] * L.RING_N,
                                                "a": [0.0] * L.RING_N, "f": 0.0})
        self.rotate(ring)
        ring["a"][ring["i"] - 1] += kcal
        if plain:
            ring["p"][ring["i"] - 1] += kcal
        mt = self.rec["monotony"]["t"]
        w = min(1.0, kcal / 400.0)
        mt.setdefault(it["type"], {"n": 0.0})["n"] += w
        mt.setdefault("@" + cls, {"n": 0.0})["n"] += w * L.CLASS_W
        self.rec["lastIntake"] = {"fullType": it["type"], "plain": plain, "class": cls,
                                  "allies": (scaled / u_rt) if scaled < u_rt else 1, "frac": f}
        self.rec["satiety"]["M"] += kcal
        self.intake["eats"] += 1
        self.intake["landed"] += 1
        self.h["booked"] += 1

    # -- the bus
    def gread(self, path):
        if path.startswith("NutritionRevamp.server.hedonics.stats."):
            return self.h.get(path.rsplit(".", 1)[-1])
        table = {"NutritionRevamp.server.hedonics.wrappedCook": "no_wrap" not in self.f,
                 "NutritionRevamp.server.hedonics.lastError": None,
                 "NutritionRevamp.server.intake.stats.eats": self.intake["eats"],
                 "NutritionRevamp.server.intake.stats.landed": self.intake["landed"],
                 "NutritionRevamp.server.writer.stats.writes": self.writes,
                 "NutritionRevamp.server.store.file.lastWrite.admin": self.lastWrite,
                 "NutritionRevamp.server.players.online.admin": self.online,
                 "SandboxVars.Nutrition": False, "SandboxVars.DayLength": 4, "SandboxVars.NR.Mode": 1,
                 "SandboxVars.NR.DeathPace": 3, "SandboxVars.NR.HealthCombine": 2, "SandboxVars.SleepAllowed": False,
                 "NutritionRevamp.version": "1.0.0", "NutritionRevamp.kernel.drain.OPT.pace": 3,
                 "NutritionRevamp.kernel.drain.OPT.combine": 2, "NutritionRevamp.kernel.drain.OPT.dayMin": 90}
        return table.get(path)

    def rcon(self, cmd):
        parts = cmd.replace('"', "").split()
        if parts[0] == "additem":
            for _ in range(int(parts[3])):
                self.new_item(parts[2])
            return True, "Item added"
        if parts[0] == "settimespeed":
            self.speed = int(parts[1])
            return True, "ok"
        return False, "unknown"

    def fields(self, it, side):
        u = it["u"] if side == "server" else it["c_u"]
        return {"getUnhappyChangeUnmodified": u, "getUnhappyChange": u + it["state"], "getBoredomChange": 0.0,
                "getName": it["name"], "isCustomName": it["custom"], "getHungChange": it["hung"],
                "getCalories": it["cal"]}

    def row_of(self, it):
        return {"id": it["id"], "fullType": it["type"], "name": it["name"], "custom": it["custom"]}

    def write_doc(self, name, doc):
        with open(os.path.join(self.dir, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def ask(self, node, cmd, args="", timeout=30):
        """The bus: the answer, then the step's wall (F1: the median `took` of x494 and x495, 1.25 s a server step and
        0.35 s a client step), so a body run spends the wall a live one does."""
        v = self.answer(node, cmd, args)
        if self.latency:
            self.sleep(1.25 if node == "server" else 0.35)
        return v

    def answer(self, node, cmd, args=""):
        side = "server" if node == "server" else "client"
        a = args.split() if isinstance(args, str) else []
        if side == "client" and not self.online:
            return {"error": "TimeoutError: the client is gone"}
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return ["admin"] if self.online else {}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 7, "minutes": 0, "mult": float(self.speed),
                    "trueMult": float(self.speed), "wall": self.t}
        if cmd == "lua.read":
            root, paths = a[0], a[1:]
            src = (lambda p: self.gread(p)) if root == "_G" else (lambda p: rget(self.rec, p))
            v = {p: src(p) for p in paths}
            return {"ok": True, "side": side, "root": root, "n": len(paths),
                    "values": {p: x for p, x in v.items() if x is not None},
                    "missing": {p: "nil" for p, x in v.items() if x is None}}
        if cmd == "lua.global":
            return {"side": side, "name": a[0], "resolved": True, "type": "string",
                    "value": json.dumps({"gen": 1, "rec": copy.deepcopy(self.rec)})}
        if cmd == "stats.all":
            return {"side": side, "user": "admin", "worldAge": self.age, "mult": 1.0, "wall": self.t,
                    "stats": dict(self.stats), "missing": {}}
        if cmd == "nutrition.get":
            return {"calories": 800.0, "carbs": 0.0, "lipids": 0.0, "proteins": 0.0, "weight": 65.0, "hunger":
                    self.stats["Hunger"], "thirst": 0.0}
        if cmd == "perk.xp":
            return {"perk": "Cooking", "user": "admin", "side": side, "xp": 0.0, "level": 2, "serverWorldAge": self.age}
        if cmd == "perk.set":
            before, self.cooking = self.cooking, int(a[2])
            return {"perk": a[1], "requested": int(a[2]), "side": side, "before": before, "after": self.cooking,
                    "route": "setPerkLevelDebug"}
        if cmd == "health.get":
            return {"ok": True, "side": side, "overall": 100.0, "health": 100.0, "parts": {}}
        if cmd == "item.get":
            it = self.first(a[1])
            if it is None:
                return f"no item {a[1]}"
            return {"fullType": it["type"], "id": it["id"], "calories": it["cal"], "carbs": it["carbs"],
                    "lipids": it["lipids"], "proteins": it["proteins"], "hungChange": it["hung"],
                    "baseHunger": it["base"], "age": it["age"], "fresh": it["state"] == 0}
        if cmd == "item.set":
            it = self.first(a[1])
            it["age"] = float(a[3])
            it["state"] = L.STALE_TERM
            return {"fullType": it["type"], "id": it["id"], "field": a[2], "requested": float(a[3]), "sync": True}
        if cmd == "witness.fields":
            it = self.by_ref(a[1])
            if it is None:
                return {"side": side, "subject": "item", "id": a[1], "resolved": False, "worldAge": self.age,
                        "error": f"no item {a[1]}"}
            return {"side": side, "subject": "item", "id": a[1], "resolved": f"admin/{it['type']} #{it['id']}",
                    "fields": self.fields(it, side), "missing": {}, "nils": {}, "worldAge": self.age, "count": 7}
        if cmd == "witness.moddata":
            it = self.by_ref(a[0].split(":", 1)[1])
            if it is None:
                return {"side": side, "scope": "item", "values": {}, "missing": a[1:], "resolved": False,
                        "error": "no item"}
            md = it["md"] if side == "server" else it["c_md"]
            return {"side": side, "scope": "item", "arg": a[0], "values": {k: md[k] for k in a[1:] if k in md},
                    "missing": [k for k in a[1:] if k not in md] or {}, "worldAge": self.age, "resolved": True,
                    "keys": sorted(f"{k}:number" for k in md) or {}, "keyCount": len(md), "count": len(a) - 1}
        if cmd == "inv.ids":
            rows = [self.row_of(it) for it in self.items.values() if it["type"] == a[0]]
            return {"ok": True, "side": side, "fullType": a[0], "n": len(rows), "items": rows or {}}
        if cmd == "recipe.add":
            base, used = self.by_ref(a[1]), self.by_ref(a[2])
            if base is None or used is None:
                return {"ok": False, "queued": False, "recipe": a[0].replace("_", " "), "reason": "no item"}
            bid, uid = base["id"], used["id"]
            self.pending.append((self.t + 1.7, lambda: self.complete_add(bid, uid)))
            return {"ok": True, "queued": True, "recipe": a[0].replace("_", " "), "base": self.row_of(base),
                    "used": self.row_of(used), "usable": True, "maxTime": 100 - 2.5 * self.cooking}
        if cmd == "item.rename":
            it = self.by_ref(a[0])
            before = self.row_of(it)
            it["name"], it["custom"] = a[1], True
            iid = it["id"]
            self.pending.append((self.t + 0.3, lambda: self.complete_rename(iid)))
            return {"ok": True, "item": iid, "before": before, "after": self.row_of(it), "synced": True}
        if cmd == "eat.action":
            it = self.first(a[0])
            iid, frac = it["id"], float(a[1])
            self.eating = {"id": iid, "frac": frac, "t0": self.t, "dur": 4.0}
            self.pending.append((self.t + 4.0, lambda: self.finish_eat(iid, frac)))
            return {"queued": True, "fraction": frac, "spawned": "found", "itemId": iid, "validStart": True,
                    "maxTime": 232.0, "moodleFoodEaten": 0, "before": {}}
        if cmd == "action.cancel":
            e = getattr(self, "eating", None)
            if e is None:
                return {"ok": True, "before": 0, "after": 0, "started": False, "stopped": True, "cleared": True}
            self.pending = [p for p in self.pending if p[0] != e["t0"] + e["dur"]]
            prog = (self.t - e["t0"]) / e["dur"]
            self.eating = None
            self.pending.append((self.t + 0.2, lambda: self.complete_eat(e["id"], e["frac"], prog)))
            return {"ok": True, "before": 1, "after": 0, "current": "ISEatFoodAction", "started": True,
                    "adding": False, "stopped": True, "javaBefore": 1, "javaAfter": 0, "cleared": True}
        if cmd == "stats.setany":
            name = {"UNHAPPINESS": "Unhappiness", "HUNGER": "Hunger"}[a[1]]
            before = self.stats[name]
            self.stats[name] = float(a[2])
            return {"ok": True, "stat": a[1], "side": side, "requested": float(a[2]), "before": before,
                    "after": self.stats[name]}
        if cmd == "record.set":
            path, val = a[1], float(a[2])
            head, key = path.rsplit(".", 1)
            tgt = rget(self.rec, head)
            before = tgt.get(key)
            tgt[key] = val
            return {"ok": True, "side": side, "user": "admin", "path": path, "key": key, "keyType": "string",
                    "before": before, "beforeType": "number", "after": val, "afterType": "number"}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring_paths = a[2:]
                return {"ok": True, "side": side, "user": "admin", "armed": True, "cap": 4320, "paths": a[2:]}
            if a[1] == "read":
                frm = int(a[2]) if len(a) > 2 else 1
                name = f"minute-ring-admin-{frm}"
                self.write_doc(name, {"rows_list": self.ring_rows})
                return {"ok": True, "side": side, "user": "admin", "from": frm, "rows": len(self.ring_rows),
                        "next": None, "more": False, "errors": 0, "result": name}
            return {"ok": True, "side": side, "user": "admin", "stopped": True, "errors": 0}
        if cmd == "ghost.load":
            self.ghosts, self.load = int(a[0]) - 1, True
            return {"ok": True, "side": side, "N": int(a[0]), "ghosts": self.ghosts, "online": 1, "scheduler": "mod"}
        if cmd == "ghost.modq":
            return {"ok": True, "side": side, "on": a[0] == "on", "ghosts": self.ghosts}
        if cmd == "ghost.stats":
            if a and a[0] == "reset":
                return {"ok": True, "side": side, "reset": True, "before": {}}
            return {"ok": True, "side": side, "active": self.load, "runs": 900, "failures": 0, "starvedEvents": 0,
                    "storeGhostKeys": 0, "neverRun": 0, "minuteEventsSince": 16}
        if cmd == "ghost.stop":
            self.load = False
            return {"ok": True, "side": side, "stopped": True, "cleared": self.ghosts, "stats": {}}
        if cmd == "tick.ring":
            if a[0] == "read":
                add = (40.0 if "heavy_load" in self.f else 8.0) if self.load else 0.0
                self.write_doc(f"tick-ring-{a[1]}", ring_doc(minute_add=add, t0=int(self.t * 1000) - 60000))
                return {"ok": True, "side": side, "tag": a[1], "frames": 600, "result": f"tick-ring-{a[1]}"}
            return {"ok": True, "side": side, "armed": True, "cap": int(a[0]), "hooks": True}
        if cmd == "perf.local":
            if a[0] == "read":
                mx = (160.0 if "heavy_load" in self.f else 118.0) if self.load else 110.0
                self.write_doc(f"perf-local-{a[1]}", perf_doc(mx=mx, t0=int(self.t * 1000) - 60000))
                return {"ok": True, "side": side, "tag": a[1], "samples": 60, "result": f"perf-local-{a[1]}"}
            return {"ok": True, "side": side, "armed": True, "cap": int(a[0]), "present": True}
        raise AssertionError(f"the fake bus has no {cmd} on {side}")

    def finish_eat(self, iid, frac):
        self.eating = None
        self.complete_eat(iid, frac)


def body_run(tmp_path, key, flags=(), monkeypatch=None, wall=None):
    w = World(str(tmp_path), flags)
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"left_in_place": []}}
    clients = {"admin": FakeClient(w)}
    xs = X.Xs(out, node=lambda s: s, clients=clients, ask=w.ask, budget_s=10000.0, clock=w.clock, sleep=w.sleep,
              spawn_wait_s=0.5)
    xs.server = FakeServer(w, str(tmp_path))
    xs.path = os.path.join(str(tmp_path), "out.json")

    def launch(S, user, sub):
        w.sleep(40.0)                                   # x463b: a relaunch to ready 34-63 s
        w.login()
        clients[user] = FakeClient(w)
        return {"restored": True, "ready_took": 3.0, "wall": S.xs.wall()}
    S = L.KINDS[key](xs, key, run_dir=str(tmp_path), prerun=L.load_prerun().get(key), launch=launch)
    if key == "x502" and monkeypatch is not None:
        def no_replay(self, rows):
            for f in L.REPLAY_TOL:
                self.xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the fake world has no replay"}, "")
        monkeypatch.setattr(L.Floor, "grade_replay", no_replay)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    if wall is not None:
        wall["end"] = max(pw.get("end", 0.0) for pw in out["phase_walls"].values())
    S.grade_all()
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out


ALWAYS_UNMEASURED = {"x502": {"REPLAY_hedonics.f", "REPLAY_moodLast.u"}}


@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_the_body_run_reads_as_predicted_on_a_correct_world(tmp_path, monkeypatch, key):
    v, out = body_run(tmp_path, key, monkeypatch=monkeypatch)
    assert set(v) == GRADES[key]
    off = {k: x for k, x in v.items() if x != "as_predicted" and k not in ALWAYS_UNMEASURED.get(key, set())}
    assert not off, (off, {k: out["verdicts"][k]["observed"] for k in off})


# each defect with every grade it moves: the first named is the defect's own; the rest are its true cascade (a stamp
# lost to a rename makes the next add compound, so RENAME, RELOG and COUNTS all read it)
DEFECTS = [
    ("x501", "no_seat", {"ANCHOR", "SCALE", "COUNTS", "RENAME", "RELOG"}),
    ("x501", "compound", {"SCALE", "COUNTS", "RENAME", "RELOG"}),
    ("x501", "no_client_sync", {"CLIENT", "RENAME", "RELOG", "COUNTS"}),
    ("x501", "rename_wipes", {"RENAME", "RELOG", "COUNTS"}),
    ("x501", "relog_drops", {"RELOG", "COUNTS"}),
    ("x501", "no_wrap", {"WRAP"}),
    ("x502", "no_floor", {"RISE", "FLOOR_OF", "RELEASE", "OFFLINE"}),   # OFFLINE: no floor to keep, unmeasured
    ("x502", "offline_moves", {"OFFLINE"}),
    ("x502", "no_release", {"RELEASE", "FLOOR_OF"}),
    ("x503", "no_allies", {"HUNGRY", "RATIO", "CANCEL", "COUNTS"}),
    ("x503", "no_restore", {"REMAINDER", "COUNTS"}),
    ("x503", "doubled", {"I2"}),
    ("x503", "vanilla_doubles", {"I2"}),
    ("x504", "class_portion", {"CLASS_A"}),
    ("x504", "dish_eat_unscaled", {"DISH_EAT"}),
    ("x504", "heavy_load", {"P99", "MAX"}),
]


BOOT_S = 85.0                                 # the session ready 52-85 s after the launch in x491-x495
WALL_MARGIN_S = 60.0


@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_the_body_fits_its_budget_at_live_bus_latency(tmp_path, monkeypatch, key):
    """F2: on the latency-charged fake, the last phase's end plus the boot leaves WALL_MARGIN_S of the budget."""
    wall = {}
    body_run(tmp_path, key, monkeypatch=monkeypatch, wall=wall)
    margin = L.SESSIONS[key]["budget_s"] - (wall["end"] + BOOT_S)
    print(f"{key}: body {wall['end']:.1f} s, boot {BOOT_S} s, budget {L.SESSIONS[key]['budget_s']} s, "
          f"margin {margin:.1f} s")
    assert margin >= WALL_MARGIN_S, (key, wall["end"], margin)


def test_the_vanilla_control_moves_i2_to_unmeasured_never_falsified(tmp_path, monkeypatch):
    v, out = body_run(tmp_path, "x503", ("vanilla_doubles",), monkeypatch=monkeypatch)
    assert v["I2"] == "unmeasured" and "I2C" in out["verdicts"]["I2"]["observed"]["why"]
    v, out = body_run(tmp_path, "x503", ("doubled",), monkeypatch=monkeypatch)
    assert v["I2"] == "falsified" and out["verdicts"]["I2"]["observed"]["doubled_c"] is False


def test_x501_records_the_ids_guard_and_pairs_only_the_last_add(tmp_path, monkeypatch):
    v, out = body_run(tmp_path, "x501", monkeypatch=monkeypatch)
    D3 = out["checks"]["D3"]
    assert D3["ids_agree"] is True and D3["server_id"] == int(D3["ref"][1:])
    for lv in L.LEVELS:
        adds = out["checks"][f"D{lv}"]["adds"]
        assert [("c" in a["read"]) for a in adds] == [False] * (len(L.DISH_ADDS) - 1) + [True]
    assert out["verdicts"]["CLIENT"]["observed"]["pairs"] == 3


def test_the_relog_follows_a_dish_whose_id_moved(tmp_path, monkeypatch):
    v, out = body_run(tmp_path, "x501", ("relog_new_ids",), monkeypatch=monkeypatch)
    assert v["RELOG"] == "as_predicted" and v["COUNTS"] == "as_predicted"
    assert set(out["checks"]["RL"]["ids_changed"]) == {"0", "3", "10"}


def test_h1_and_ring_fail_their_cases():
    ok = L48.grade_h1({"ok": True, "missing": {"hedonics.f": "nil"}}, {"ok": True}, L.H1_NIL_OK)
    assert ok[0] == "as_predicted"
    bad = L48.grade_h1({"ok": True, "missing": {"satiety.M": "nil"}}, {"ok": True}, L.H1_NIL_OK)
    assert bad[0] == "falsified"
    import x45g_lib as G
    assert G.grade_ring([{"file": "p.json", "reply": {"errors": 0}}])[0] == "as_predicted"
    assert G.grade_ring([{"file": None, "reply": {"errors": 0}}])[0] == "falsified"
    assert G.grade_ring([])[0] == "unmeasured"


@pytest.mark.parametrize("key,flag,moved", DEFECTS)
def test_each_defect_moves_its_grade_off_as_predicted(tmp_path, monkeypatch, key, flag, moved):
    v, out = body_run(tmp_path, key, (flag,), monkeypatch=monkeypatch)
    off = {k for k, x in v.items() if x != "as_predicted" and k not in ALWAYS_UNMEASURED.get(key, set())}
    assert moved <= off, (flag, v)
    assert off <= moved, (flag, {k: v[k] for k in off - moved})
