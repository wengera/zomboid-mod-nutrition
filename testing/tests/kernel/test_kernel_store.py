"""The store kernel (NR_Kernel_Store.lua, K.store; Plan 8 Task 3, ruling 5).

The record's contract: VERSION, the closed INPUTS path list, the load that migrates a v1 record by keeping its
inputs over the kernel constructors' defaults (the derived fields dropped), inputsOnly (what a save holds) and
isInput. The classification tests walk every field each kernel constructor lays and require it to be either an
input or in this file's DERIVED list, so a new field cannot land unclassified.
"""
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")

ORDER = ["vitC", "iron", "vitB12", "calcium", "vitA"]

# The fields each constructor lays that the store drops at load (derived or a schema stamp the constructor
# re-lays), read off the owning steps (the kernel file's comments name them).
DERIVED = {
    "body": {"bv", "band", "delta", "dmod", "rmod", "energyState", "eb24h", "mirrorLast"},
    "nutrients": {"nv", "allReplete", "ironGrade", "anaemia", "vitDClinical"},
    "key": {"x"},
    "acute": {"av", "wd", "wdH", "bac", "g", "circ", "frozen", "iu", "iuSleep"},
    "fluids": {"fv", "dehydPct", "c", "naPlasma", "thirstTarget", "sweatLmin"},
    "effects": {"ev", "key", "mNut", "rNut", "stressTarget", "unhappyTarget", "panicTarget", "foodSickTarget",
                "poisonTarget", "healMul", "bleedMul", "infectMul", "coldMul", "tempOffset", "tempHeat", "speedMul",
                "fOffNut", "bruise", "drain", "nightVision", "shortSighted", "aimMul", "fOff", "solAddH", "solMul",
                "lethal", "intoxTarget", "tempTarget", "mAcc", "rRec"},
    "stomach": set(),
}


def S(h):
    return h.K.store


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def arr(h, items):
    return h.rt.table(*items)


def order(h):
    return arr(h, ORDER)


@pytest.fixture(autouse=True)
def _records_loaded(host):
    """Every test sees the data tables loaded, whatever ran before it: no test depends on another's side effect."""
    data = host.G.NutritionRevamp.data
    if data is None or data.records is None:
        for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua"):
            with open(os.path.join(SHARED, name), encoding="utf-8") as fh:
                host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@" + name)()


def recs(h):
    return h.G.NutritionRevamp.data.records


def v1(h):
    """A v1 record with every sub-table laid by its own constructor, then moved off the defaults."""
    rec = h.table({"username": "admin", "firstSeen": 10.0, "lastSeen": 30.5, "resets": 2, "dead": False,
                   "kineticsAge": 30.25, "stomachFill": 0.9, "junk": 7,
                   "lastIntake": {"source": "baseline", "fullType": "Base.Apple"},
                   "reconcile": {"count": 3, "baseline": {"calories": 100}}})
    body = h.call("body.new", 82.0, 1, h.table({}), 5, 1.1, 1.2, 24.0)
    body["tac"] = 1.3
    body["dmod"] = 0.7
    body["band"] = "stale"
    body["shownL"] = 4
    body["inDayClosed"] = 2100
    body["met"] = 3.5
    body["eb7"][7] = -250
    body["bandWeek"][7][1] = 45
    body["nHist"][14] = 0.4
    rec["body"] = body
    nut = h.call("nutrients.newState", h.table({"ORDER": {i + 1: k for i, k in enumerate(ORDER)}}))
    nut["epoch"] = 9
    nut["allReplete"] = False
    nut["lastAgeH"] = 30.0
    nut["lastDayIndex"] = 1
    nut["vitC"]["p"] = 0.12
    nut["vitC"]["g"] = 4
    nut["vitC"]["gl"] = 3
    nut["vitC"]["ah"] = 50
    nut["vitC"]["x"] = 2
    nut["iron"]["S"] = 400
    nut["iron"]["H"] = 2500
    nut["calcium"]["bone"] = 900
    nut["retired"] = h.table({"p": 0.5})
    rec["nutrients"] = nut
    a = h.call("acute.new", 24.0)
    a["caf"] = 120
    a["bac"] = 0.04
    a["cafTol"] = 0.6
    a["slowMet"] = True
    a["alc7"] = 0.2
    rec["acute"] = a
    f = h.call("fluids.new", 60, 1.1, 40)
    f["water"] = -500
    f["thirstTarget"] = 0.7
    f["dehydPct"] = 0.6
    f["autoDrop"] = 0.05
    f["viewPct"] = 0.5
    rec["fluids"] = f
    e = h.call("effects.new")
    e["dirty"] = True
    e["epoch"] = 7
    e["own"]["nv"] = True
    e["nvDays"] = 3
    e["pe"] = 2
    e["ea"] = 22
    e["lastDay"] = 1
    e["exSeen"] = 80
    e["mNut"] = 0.5
    e["intoxTarget"] = 0.3
    e["tempAdj"] = -0.2
    rec["effects"] = e
    st = h.call("stomach.new")
    st["buffer"]["calories"] = 300
    st["bulk"] = 4.0
    rec["stomach"] = st
    pool = h.call("vector.new")
    pool["iron"] = 1.5
    rec["pool"] = pool
    return rec


# --- the constants and the path list ------------------------------------------------------------------


def test_version_is_four_and_inputs_are_dotted_strings(host):
    assert S(host).VERSION == 4
    paths = lst(S(host).INPUTS)
    assert len(paths) == len(set(paths)) and all(isinstance(p, str) and p for p in paths)
    assert len(lst(S(host).SEGS)) == len(paths)
    assert lst(S(host).split("nutrients.*.p")) == ["nutrients", "*", "p"]
    assert lst(S(host).split("v")) == ["v"]


def test_identity_fields_are_inputs(host):
    for p in ("v", "username", "firstSeen", "lastSeen", "resets", "dead"):
        assert S(host).isInput(p), p


def test_is_input_matches_a_star_and_anything_under_an_input(host):
    assert S(host).isInput("nutrients.vitC.p") and S(host).isInput("nutrients.iron.S")
    assert not S(host).isInput("nutrients.vitC.x")
    assert S(host).isInput("body.bandWeek.3") and S(host).isInput("body.bandWeek.3.1")
    assert S(host).isInput("stomach.buffer.calories") and S(host).isInput("pool.iron")
    assert not S(host).isInput("body") and not S(host).isInput("body.dmod") and not S(host).isInput("stomachFill")
    assert not S(host).isInput("lastIntake.source") and not S(host).isInput("reconcile.baseline.calories")
    assert S(host).isInput("reconcile.count") and S(host).isInput("effects.own.nv")


# --- the classification: every constructor field is an input or declared derived ----------------------


def is_input(h, path, value):
    # a table-valued field (a ring, the buffer) is an input when its slots are: path.<any> matches a `*` path
    if S(h).isInput(path):
        return True
    return isinstance(value, dict) and S(h).isInput(path + ".slot")


def classify(h, prefix, table, derived):
    unclassified = []
    for k, v in h.py(table).items():
        inp = is_input(h, prefix + "." + str(k), v)
        if not inp and k not in derived:
            unclassified.append(k)
        if inp and k in derived:
            unclassified.append(("both", k))
    return unclassified


def test_every_body_field_is_classified(host):
    body = host.call("body.new", 80.0, 2, host.table({}), 3, 1.0, 1.0, 48.0)
    assert classify(host, "body", body, DERIVED["body"]) == []


def test_the_adapter_body_fields_are_classified(host):
    # NR_Server_Metabolism stamps met and coldMult every minute (derived) and inDayClosed / pPrevKg at a close
    assert S(host).isInput("body.inDayClosed") and S(host).isInput("body.pPrevKg")
    assert not S(host).isInput("body.met") and not S(host).isInput("body.coldMult")


def test_every_nutrient_field_is_classified(host):
    state = host.call("nutrients.newState", host.table({"ORDER": {1: "vitC"}}))
    assert classify(host, "nutrients", state, DERIVED["nutrients"] | {"vitC"}) == []
    assert classify(host, "nutrients.vitC", state["vitC"], DERIVED["key"]) == []
    for k in ("S", "H", "bone"):
        assert S(host).isInput("nutrients.iron." + k)


def test_every_acute_fluids_effects_and_stomach_field_is_classified(host):
    assert classify(host, "acute", host.call("acute.new", 0), DERIVED["acute"]) == []
    for k in ("alc7", "alcDayG", "lastFedAgeH", "lastB1", "lastB2"):
        assert S(host).isInput("acute." + k)
    assert classify(host, "fluids", host.call("fluids.new", 60, 1, 40), DERIVED["fluids"]) == []
    assert not S(host).isInput("fluids.viewPct") and not S(host).isInput("fluids.sweatActive")
    eff = host.call("effects.new")
    assert classify(host, "effects", eff, DERIVED["effects"] | {"own"}) == []
    assert classify(host, "effects.own", eff["own"], set()) == []
    assert classify(host, "stomach", host.call("stomach.new"), DERIVED["stomach"]) == []


def test_every_order_key_has_its_per_key_input_paths(host):
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua"):
        with open(os.path.join(SHARED, name), encoding="utf-8") as fh:
            host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(fh.read(), "@" + name)()
    data_order = lst(host.G.NutritionRevamp.data.records.ORDER)
    assert len(data_order) > 20
    for key in data_order:
        for f in ("p", "p2", "g", "gl", "ah", "e24", "dmg", "ext", "ax", "axr"):
            assert S(host).isInput("nutrients.%s.%s" % (key, f))
    loaded = host.py(S(host).load(host.table({"nutrients": {}}), host.G.NutritionRevamp.data.records.ORDER, recs(host)))
    assert set(k for k, v in loaded["nutrients"].items() if isinstance(v, dict)) == set(data_order)


# --- K.store.new --------------------------------------------------------------------------------------


def test_new_is_the_identity_record_at_version_four(host):
    assert host.py(S(host).new("bob", 12.5)) == {"v": 4, "username": "bob", "firstSeen": 12.5, "lastSeen": 12.5,
                                               "resets": 0, "dead": False}


# --- the load: a v1 record migrated ------------------------------------------------------------------


def test_load_of_a_v1_record_keeps_the_inputs_and_drops_the_derived(host):
    raw = v1(host)
    r = host.py(S(host).load(raw, order(host), recs(host)))
    assert r["v"] == 4
    assert (r["username"], r["firstSeen"], r["lastSeen"], r["resets"], r["dead"]) == ("admin", 10.0, 30.5, 2, False)
    assert "junk" not in r and "lastIntake" not in r
    assert r["reconcile"] == {"count": 3}
    assert r["kineticsAge"] == 30.25
    b = r["body"]
    assert b["tac"] == 1.3 and b["shownL"] == 4 and b["inDayClosed"] == 2100 and b["l0"] == 5
    assert b["eb7"][7] == -250 and b["bandWeek"][7] == {1: 45, 2: 0} and b["nHist"][14] == 0.4
    assert b["dmod"] == 1 and b["band"] == "normal" and "met" not in b       # rebuilt by K.body.new
    n = r["nutrients"]
    assert (n["vitC"]["p"], n["vitC"]["g"], n["vitC"]["gl"], n["vitC"]["ah"]) == (0.12, 4, 3, 50)
    assert n["vitC"]["x"] == 0 and n["allReplete"] is False                  # x derived; allReplete recomputed (vitC at grade 4)
    assert n["epoch"] == 9 and n["lastAgeH"] == 30.0 and n["lastDayIndex"] == 1
    assert n["iron"]["S"] == 400 and n["iron"]["H"] == 2500 and n["calcium"]["bone"] == 900
    assert "retired" not in n                                                # a key outside the order is dropped
    a = r["acute"]
    assert a["caf"] == 120 and a["cafTol"] == 0.6 and a["slowMet"] is True and a["alc7"] == 0.2
    assert a["bac"] == 0 and a["av"] == host.K.acute.AV
    f = r["fluids"]
    assert f["water"] == -500 and f["autoDrop"] == 0.05 and f["sweatK"] == 1.1 and f["naSweat"] == 40
    assert "thirstTarget" not in f and "viewPct" not in f
    e = r["effects"]
    assert e["dirty"] is True and e["epoch"] == 7 and e["own"] == {"nv": True, "ss": False}
    assert (e["nvDays"], e["pe"], e["ea"], e["lastDay"], e["exSeen"]) == (3, 2, 22, 1, 80)
    assert e["mNut"] == 1 and "intoxTarget" not in e and "tempAdj" not in e and e["key"]["ep"] == -1
    assert r["stomach"]["buffer"]["calories"] == 300 and "bulk" not in r["stomach"] and r["stomach"]["liquid"] == 0
    assert r["stomachFill"] == 0                                             # recomputed: energy alone has no mass
    assert r["pool"]["iron"] == 1.5 and r["pool"]["calories"] == 0


def test_load_of_a_record_with_no_version_and_with_v1_is_the_same(host):
    raw = v1(host)
    a = host.py(S(host).load(raw, order(host), recs(host)))
    raw["v"] = 1
    b = host.py(S(host).load(raw, order(host), recs(host)))
    assert a == b and a["v"] == 4


def test_load_copies_deep(host):
    raw = v1(host)
    r = S(host).load(raw, order(host), recs(host))
    r["body"]["bandWeek"][7][1] = 999
    r["stomach"]["buffer"]["calories"] = 1
    assert raw["body"]["bandWeek"][7][1] == 45 and raw["stomach"]["buffer"]["calories"] == 300


def test_a_missing_input_keeps_the_constructor_default(host):
    raw = host.table({"username": "admin", "firstSeen": 5.0,
                      "acute": {"caf": 30}, "nutrients": {"iron": {"p": 0.5}}, "fluids": {"water": 10},
                      "effects": {"dirty": True}, "stomach": {"bulk": 2.0}, "pool": {"iron": 1}})
    r = host.py(S(host).load(raw, order(host), recs(host)))
    assert r["lastSeen"] == 5.0 and r["resets"] == 0 and r["dead"] is False
    assert r["acute"]["caf"] == 30 and r["acute"]["cafTol"] == 0
    assert r["acute"]["winStartH"] == 5.0                                    # stamped with the first sight
    assert r["nutrients"]["iron"]["p"] == 0.5 and r["nutrients"]["iron"]["g"] == 1
    assert r["nutrients"]["vitC"] == {"p": 1, "p2": 1, "g": 1, "gl": 1, "ah": 0, "x": 0, "e24": 0, "dmg": 0,
                                      "ext": 0, "ax": 0, "axr": 0}
    assert r["fluids"]["water"] == 10 and r["fluids"]["sweatK"] == 1
    assert r["effects"]["epoch"] == 0 and r["effects"]["own"] == {"nv": False, "ss": False}
    assert r["stomach"]["buffer"]["calories"] == 0 and r["stomachFill"] == 0 and r["stomach"]["liquid"] == 0
    assert "body" not in r and "kineticsAge" not in r and "reconcile" not in r


def test_load_with_no_clock_stamps_the_acute_clocks_at_zero(host):
    r = host.py(S(host).load(host.table({"acute": {}}), order(host), recs(host)))
    assert r["acute"]["winStartH"] == 0 and r["acute"]["mass90ageH"] == 0


def test_load_with_no_order_lays_the_stored_keys(host):
    raw = host.table({"nutrients": {"epoch": 3, "zinc": {"p": 0.3, "g": 2}}})
    n = host.py(S(host).load(raw, None, recs(host)))["nutrients"]
    assert n["zinc"]["p"] == 0.3 and n["zinc"]["g"] == 2 and n["epoch"] == 3
    assert set(k for k, v in n.items() if isinstance(v, dict)) == {"zinc"}


def test_an_unusable_body_is_dropped(host):
    for body in ({"lm": 60, "sex": 1, "lastAgeH": 1}, {"fm": 20, "sex": 1, "lastAgeH": 1},
                 {"fm": 20, "lm": 60, "lastAgeH": 1}, {"fm": 20, "lm": 60, "sex": 1}):
        r = host.py(S(host).load(host.table({"body": body}), order(host), recs(host)))
        assert "body" not in r, body


def test_a_body_builds_at_its_sex_and_keeps_an_odd_one(host):
    r = host.py(S(host).load(host.table({"body": {"fm": 20.0, "lm": 50.0, "sex": 2, "lastAgeH": 50.0}}), None, recs(host)))
    assert r["body"]["sex"] == 2 and r["body"]["fm"] == 20.0 and r["body"]["dayIndex"] == 2
    r = host.py(S(host).load(host.table({"body": {"fm": 20.0, "lm": 50.0, "sex": 3, "lastAgeH": 1.0}}), None, recs(host)))
    assert r["body"]["sex"] == 3 and r["body"]["dmod"] == 1


def test_load_of_a_non_table_is_nil(host):
    assert S(host).load(None, order(host), recs(host)) is None
    assert S(host).load(5, order(host), recs(host)) is None


# --- inputsOnly: what a save holds, and the round trip ------------------------------------------------


def test_inputs_only_holds_no_derived_field(host):
    raw = v1(host)
    out = host.py(S(host).inputsOnly(raw))
    assert "v" not in out                                                    # a v1 record carries none
    assert "junk" not in out and "stomachFill" not in out and "lastIntake" not in out
    assert "dmod" not in out["body"] and "band" not in out["body"] and out["body"]["tac"] == 1.3
    assert "x" not in out["nutrients"]["vitC"] and out["nutrients"]["vitC"]["g"] == 4
    assert out["nutrients"]["retired"] == {"p": 0.5}                         # the save keeps what the record holds
    assert "allReplete" not in out["nutrients"] and out["nutrients"]["epoch"] == 9
    assert out["effects"] == {"dirty": True, "epoch": 7, "own": {"nv": True, "ss": False}, "nvDays": 3, "pe": 2,
                              "ea": 22, "lastDay": 1, "exSeen": 80}
    assert out["reconcile"] == {"count": 3}
    assert raw["body"]["dmod"] == 0.7                                        # the record itself is untouched


def test_inputs_only_copies_deep(host):
    raw = v1(host)
    out = S(host).inputsOnly(raw)
    out["body"]["bandWeek"][7][1] = 1
    assert raw["body"]["bandWeek"][7][1] == 45


def test_a_v3_record_round_trips_through_load_and_inputs_only(host):
    r1 = S(host).load(v1(host), order(host), recs(host))
    saved = S(host).inputsOnly(r1)
    r2 = S(host).load(saved, order(host), recs(host))
    assert host.py(S(host).inputsOnly(r2)) == host.py(saved)
    assert host.py(r2) == host.py(r1)
    assert host.py(saved)["v"] == 4


# --- the fix round: the four recomputed fields, the containers, the stomach and close defaults -------------


def test_load_recomputes_the_iron_grade_and_all_replete_through_the_nutrients_kernel(host):
    raw = v1(host)
    raw["nutrients"]["iron"]["g"] = 3
    r = S(host).load(raw, order(host), recs(host))
    n = r["nutrients"]
    assert n["ironGrade"] == host.K.nutrients.gradeOf(n, "iron") == 3
    assert n["allReplete"] == host.K.nutrients.allRepleteOf(n, host.G.NutritionRevamp.data.records) is False
    raw2 = host.table({"nutrients": {"iron": {"g": 1}}})
    n2 = S(host).load(raw2, order(host), recs(host))["nutrients"]
    assert n2["ironGrade"] == 1 and n2["allReplete"] is True


def test_load_reads_the_records_argument_never_the_global(host):
    other = host.table({"ORDER": host.table({}), "REC": host.table({})})
    raw = v1(host)
    raw["nutrients"]["iron"]["g"] = 3
    assert S(host).load(raw, order(host), recs(host))["nutrients"]["allReplete"] is False
    assert S(host).load(raw, order(host), other)["nutrients"]["allReplete"] is True       # the argument's records, not the global's
    n = host.table({"iron": {"g": 3}})
    S(host).recomputeReplete(n, other)
    assert n["allReplete"] is True
    m = host.table({"iron": {"g": 3}})
    S(host).recomputeReplete(m, None)
    assert m["allReplete"] is None


def test_load_recomputes_the_glucose_state_through_the_acute_kernel(host):
    raw = host.table({"acute": {"glyc": 231.0, "bg": 4.5}})
    a = S(host).load(raw, order(host), recs(host))["acute"]
    assert a["g"] == host.K.acute.glycG(a) == 0.5


def test_load_recomputes_dehyd_pct_through_the_fluids_kernel(host):
    raw = host.table({"fluids": {"water": -1640.0}, "body": {"fm": 20.0, "lm": 62.0, "sex": 1, "lastAgeH": 5.0}})
    r = S(host).load(raw, order(host), recs(host))
    want = host.K.fluids.dehydPct(r["fluids"], r["body"]["fm"] + r["body"]["lm"], 0)
    assert r["fluids"]["dehydPct"] == want == 2.0
    assert S(host).load(host.table({"fluids": {"water": -1640.0}}), order(host), recs(host))["fluids"]["dehydPct"] == 0


def test_the_minute_and_the_load_agree_on_all_replete(host):
    st = host.call("nutrients.newState", host.G.NutritionRevamp.data.records)
    st["vitC"]["g"] = 2
    assert host.K.nutrients.allRepleteOf(st, host.G.NutritionRevamp.data.records) is False
    st["vitC"]["g"] = 1
    assert host.K.nutrients.allRepleteOf(st, host.G.NutritionRevamp.data.records) is True


def test_is_input_is_true_for_a_container_whose_every_slot_is_persisted(host):
    for p in ("body.eb7", "body.mass7", "body.p7", "body.carb7", "body.lip7", "body.bandWeek", "body.nHist",
              "stomach.buffer", "pool", "nutrients.vitC.p"):
        assert S(host).isInput(p), p
    for p in ("body", "nutrients", "stomach", "acute", "body.dmod", "nutrients.vitC.x", "fluids", "reconcile.baseline"):
        assert not S(host).isInput(p), p


def test_a_stored_stomach_loads_its_buffer_and_liquid_and_its_fill_from_satiety_mass(host):
    # amendment 2: F = satietyMass / CAPACITY_MAX_G; 365 g of food water reads 365 / 730 = 0.5, and 1825 g drunk reads
    # LIQUID_WEIGHT x 1825 = 365 g, 0.5 too; 3650 g drunk reads 730 g, full
    r = host.py(S(host).load(host.table({"stomach": {"buffer": {"water": 365}}}), order(host), recs(host)))
    assert r["stomach"]["liquid"] == 0 and r["stomachFill"] == 0.5
    r = host.py(S(host).load(host.table({"stomach": {"liquid": 1825}}), order(host), recs(host)))
    assert r["stomach"]["liquid"] == 1825 and abs(r["stomachFill"] - 0.5) < 1e-12
    r = host.py(S(host).load(host.table({"stomach": {"liquid": 3650}}), order(host), recs(host)))
    assert r["stomachFill"] == 1
    r = host.py(S(host).load(host.table({"stomach": {"bulk": 8}}), order(host), recs(host)))     # a v3 stomach
    assert "bulk" not in r["stomach"] and r["stomachFill"] == 0


def test_a_loaded_body_with_no_closed_day_stamp_reads_the_resting_expenditure(host):
    raw = host.table({"body": {"fm": 20.0, "lm": 62.0, "sex": 1, "lastAgeH": 5.0}, "nutrients": {}})
    b = S(host).load(raw, order(host), recs(host))["body"]
    assert b["inDayClosed"] == host.K.energy.ree(62.0) and b["inDayClosed"] > 0
    raw["body"]["inDayClosed"] = 1800
    assert S(host).load(raw, order(host), recs(host))["body"]["inDayClosed"] == 1800


# --- fillInPlace (Plan 8 Task 4, ruling T4-1): the load laid into the record's own table ----------------

def test_fill_in_place_keeps_the_table_and_drops_the_derived_fields(host):
    rec = v1(host)
    same = S(host).fillInPlace(rec, rec, order(host), recs(host))
    assert host.G.rawequal(same, rec)
    assert rec["v"] == 4 and rec["username"] == "admin" and rec["resets"] == 2
    assert rec["junk"] is None and rec["lastIntake"] is None
    assert rec["reconcile"]["count"] == 3 and rec["reconcile"]["baseline"] is None
    assert rec["body"]["band"] != "stale" and rec["body"]["inDayClosed"] == 2100


def test_fill_in_place_from_another_raw_clears_every_old_key(host):
    target = host.table({"username": "old", "stale": 1, "body": {"fm": 1}})
    raw = host.table({"username": "admin", "firstSeen": 3.0})
    out = S(host).fillInPlace(target, raw, order(host), recs(host))
    assert host.G.rawequal(out, target)
    assert target["username"] == "admin" and target["stale"] is None and target["body"] is None
    assert target["v"] == 4 and target["firstSeen"] == 3.0


def test_fill_in_place_of_a_non_table_raw_leaves_the_target(host):
    target = host.table({"username": "admin", "junk": 1})
    assert S(host).fillInPlace(target, 5, order(host), recs(host)) is None
    assert target["junk"] == 1


# --- Plan 11 Task 11: v3, the satiety field, the file names, the prune list ------------------------------------

def test_a_new_record_has_no_satiety_for_the_writer_to_seed(host):
    assert S(host).new("a", 1.0).satiety is None


def test_the_pool_its_activity_state_and_its_mark_are_inputs_and_the_v3_fields_are_not(host):
    for p in ("satiety.P", "satiety.S", "satiety.L", "satiety.v", "stomach.liquid", "body.exKcalPrev"):
        assert S(host).isInput(p), p
    assert not S(host).isInput("satiety") and not S(host).isInput("satietyStepped")
    assert not S(host).isInput("stomach.bulk")


def test_a_v3_scalar_and_its_mark_are_dropped_on_load(host):
    raw = host.rt.eval("{ v = 3, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = 0.4, satietyStepped = true }")
    rec = S(host).load(raw, None, None)
    assert rec.v == 4 and rec.satiety is None and rec.satietyStepped is None


def test_a_loaded_record_without_satiety_keeps_it_unset(host):
    raw = host.rt.eval("{ v = 2, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false }")
    rec = S(host).load(raw, None, None)
    assert rec.v == 4 and rec.satiety is None


def test_a_loaded_v4_record_keeps_its_pool_and_activity_state(host):
    raw = host.rt.eval("{ v = 4, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = { P = 88, S = 0.3, L = 120, v = 4, junk = 1 } }")
    rec = S(host).load(raw, None, None)
    assert rec.satiety.P == 88 and rec.satiety.S == 0.3 and rec.satiety.L == 120 and rec.satiety.v == 4
    assert rec.satiety.junk is None


def test_a_loaded_body_keeps_its_closed_days_exercise_bank(host):
    raw = host.table({"body": {"fm": 20.0, "lm": 62.0, "sex": 1, "lastAgeH": 5.0, "exKcalPrev": 640.0}})
    assert S(host).load(raw, order(host), recs(host))["body"]["exKcalPrev"] == 640.0


def test_names_are_file_safe(host):
    assert S(host).safeName("My Server!") == "My_Server_"
    assert S(host).safeName("") == "default"
    assert S(host).safeName("../up") == "___up"
    assert S(host).safeName("srv-2_b") == "srv-2_b"


def test_hex_name_is_four_digits_a_code_unit(host):
    assert S(host).hexName("Ab") == "00410062"
    assert S(host).hexName("") == ""
    assert S(host).hex4(0) == "0000" and S(host).hex4(65535) == "ffff" and S(host).hex4(0x1234) == "1234"


# Kahlua's string.byte answers UTF-16 code units (J2, T1102.8); lupa's answers bytes. The stand-in below makes
# string.byte and string.len read a name's code units from a table, as Kahlua's do, for the two names that
# collided under two hex digits a unit: U+0123 then "A" and U+0012 then U+0341 both wrote "12341".
UNITS = r"""
function(units)
    local saved = { byte = string.byte, len = string.len }
    string.byte = function(s, i) return units[s][i] end
    string.len = function(s) return #units[s] end
    return saved
end
"""


def test_two_names_that_collided_under_two_digits_now_differ(host):
    units = host.rt.eval("{ p1 = { 0x123, 0x41 }, p2 = { 0x12, 0x341 } }")
    saved = host.rt.eval(UNITS)(units)
    try:
        a = S(host).hexName("p1")
        b = S(host).hexName("p2")
    finally:
        host.G.string.byte = saved.byte
        host.G.string.len = saved.len
    assert (a, b) == ("01230041", "00120341")


def test_expired_lists_the_offline_entries_past_the_keep(host):
    index = host.rt.eval("{ old = 100, recent = 9000, online = 100, odd = 'x' }")
    online = host.rt.eval("{ online = true }")
    out = S(host).expired(index, 10000, 5000, online)
    assert [out[i] for i in range(1, len(out) + 1)] == ["old"]
    assert len(S(host).expired(index, 10000, 0, online)) == 0
    two = S(host).expired(host.rt.eval("{ b = 1, a = 2 }"), 10000, 5000, host.rt.eval("{}"))
    assert [two[i] for i in range(1, len(two) + 1)] == ["a", "b"]


def test_newest_names_the_slot_with_the_larger_gen(host):
    a = host.rt.eval("{ gen = 3 }")
    b = host.rt.eval("{ gen = 4 }")
    assert S(host).newest(a, b) == "b" and S(host).newest(b, a) == "a"
    assert S(host).newest(a, None) == "a" and S(host).newest(None, b) == "b"
    assert S(host).newest(None, None) is None and S(host).newest(a, a) == "a"


def test_due_is_true_with_no_last_stamp_or_a_full_gap(host):
    assert S(host).due(None, 5, 60000)
    assert S(host).due(1000, 61000, 60000) and not S(host).due(1000, 60999, 60000)


def test_seconds_and_keep_seconds(host):
    assert S(host).seconds(1999) == 1 and S(host).keepSeconds(30) == 2592000


def test_expired_keeps_an_entry_at_exactly_the_keep(host):
    index = host.rt.eval("{ edge = 5000, past = 4999 }")
    out = S(host).expired(index, 10000, 5000, host.rt.eval("{}"))
    assert [out[i] for i in range(1, len(out) + 1)] == ["past"]


def test_newest_reads_a_file_with_no_numeric_gen_as_absent(host):
    good = host.rt.eval("{ gen = 1 }")
    for bad in ("{}", "{ gen = 'x' }"):
        assert S(host).newest(host.rt.eval(bad), good) == "b"
        assert S(host).newest(good, host.rt.eval(bad)) == "a"
        assert S(host).newest(host.rt.eval(bad), host.rt.eval(bad)) is None


def test_the_save_phase_is_inside_the_gap_differs_by_name_and_seeds_the_first_write(host):
    a = S(host).savePhase("admin", 60000)
    b = S(host).savePhase("bob", 60000)
    assert 0 <= a < 60000 and 0 <= b < 60000 and abs(a - b) >= 20000
    assert S(host).savePhase("admin", 60000) == a
    assert S(host).savePhase("", 60000) == 30000
    last = S(host).firstLast("admin", 1000000, 60000)
    assert last == 1000000 - 60000 + a
    assert not S(host).due(last, 1000000 + a - 1, 60000) and S(host).due(last, 1000000 + a, 60000)


def test_the_writers_step_stamp_is_an_input(host):
    # Plan 11c close (ruling C-1): the writer's last step age, read across a restart
    assert S(host).isInput("satiety.t")
    raw = host.rt.eval("{ v = 4, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = { P = 6, S = 0, L = 0, v = 4, t = 101.5 } }")
    rec = S(host).load(raw, None, None)
    assert rec.satiety.t == 101.5 and S(host).inputsOnly(rec).satiety.t == 101.5
