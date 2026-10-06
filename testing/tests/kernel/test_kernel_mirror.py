import pytest


def rec(host, **kw):
    r = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False}
    r.update(kw)
    return host.table(r)


BODY_ABSENT = {"body_" + k: 0 for k in ("fm", "lm", "weight", "energyState", "tac", "dmod", "rmod", "shownL",
                                          "delta", "ebDay", "eeDay", "inDay", "dStr", "dHyp")}
BODY_ABSENT["body_band"] = ""


PLAN4_SCALARS = ("nutrients_epoch", "fluids_dehydPct", "fluids_naPlasma", "fluids_thirstTarget", "acute_caf",
                 "acute_bac", "acute_g", "acute_bg", "acute_awakeH", "acute_debtH", "acute_iu", "acute_refeedRisk")
PLAN4_ABSENT = {k: 0 for k in PLAN4_SCALARS}
EFFECT_NUMBERS = ("epoch", "aimMul", "speedMul", "intoxTarget", "tempTarget", "healMul", "bleedMul", "infectMul",
                  "coldMul", "drain", "lethal", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget",
                  "fOff", "mAcc", "rRec")
PLAN5_ABSENT = {"effects_" + k: 0 for k in EFFECT_NUMBERS}
PLAN5_ABSENT["effects_nv"] = False
PLAN5_ABSENT["effects_ss"] = False
META = {"mode": 1, "version": "0.1.0", "build": "42.20.4"}


def test_mirror_is_flat_scalars_only(host):
    m = host.py(host.call("mirror.build", rec(host), host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    expect = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False,
              "mode": 1, "version": "0.1.0", "build": "42.20.4", "stomachFill": 1}      # Plan 2: the fill, full by default
    expect.update(BODY_ABSENT)
    expect.update(PLAN4_ABSENT)
    expect.update(PLAN5_ABSENT)
    assert m == expect
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_copies_rather_than_aliases_the_record(host):
    r = rec(host)
    m = host.call("mirror.build", r, host.table({"mode": 2, "version": "x", "build": "y"}))
    m["lastSeen"] = 99
    assert r["lastSeen"] == 2.25


def test_mirror_meta_is_required(host):
    with pytest.raises(Exception):
        host.call("mirror.build", rec(host), None)


def test_mirror_carries_the_stomach_fill_and_no_pool_keys(host):
    pool = host.table({"calories": 512.5, "iron": 1.25})
    r = rec(host, stomachFill=0.375, pool=pool, stomach=host.table({"bulk": 3.0, "buffer": host.table({})}))
    m = host.py(host.call("mirror.build", r, host.table(META)))
    assert m["stomachFill"] == 0.375
    assert not [k for k in m if k.startswith("pool")]
    assert "stomach" not in m
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_of_a_record_with_no_stomach_reads_full(host):
    m = host.py(host.call("mirror.build", rec(host), host.table(META)))
    assert m["stomachFill"] == 1


def test_mirror_without_an_order_has_no_nut_keys_and_zero_plan4_scalars(host):
    m = host.py(host.call("mirror.build", rec(host), host.table(META)))
    assert not [k for k in m if k.startswith("nut_")]
    for k, v in PLAN4_ABSENT.items():
        assert m[k] == v and isinstance(m[k], (int, float))


def test_mirror_order_with_no_nutrients_reads_zero_grades(host):
    m = host.py(host.call("mirror.build", rec(host), host.table(META), host.table({1: "iron", 2: "zinc"})))
    assert m["nut_iron_g"] == 0 and m["nut_zinc_g"] == 0 and m["nutrients_epoch"] == 0


def test_mirror_plan4_scalars_from_present_sub_tables(host):
    r = rec(host,
            nutrients=host.table({"epoch": 7, "iron": host.table({"g": 0.5}), "zinc": host.table({})}),
            fluids=host.table({"dehydPct": 1.5, "naPlasma": 140.0, "thirstTarget": 0.4}),
            acute=host.table({"caf": 1.0, "bac": 0.02, "g": 0.9, "bg": 5.0, "awakeH": 12.0, "debtH": 3.0,
                              "iu": 0.25, "refeedRisk": 1}))
    m = host.py(host.call("mirror.build", r, host.table(META), host.table({1: "iron", 2: "zinc", 3: "iodine"})))
    assert m["nutrients_epoch"] == 7 and m["nut_iron_g"] == 0.5
    assert m["nut_zinc_g"] == 0 and m["nut_iodine_g"] == 0
    assert m["fluids_dehydPct"] == 1.5 and m["fluids_naPlasma"] == 140.0 and m["fluids_thirstTarget"] == 0.4
    assert m["acute_caf"] == 1.0 and m["acute_bac"] == 0.02 and m["acute_g"] == 0.9 and m["acute_bg"] == 5.0
    assert m["acute_awakeH"] == 12.0 and m["acute_debtH"] == 3.0 and m["acute_iu"] == 0.25
    assert m["acute_refeedRisk"] == 1
    assert "nutrients" not in m and "fluids" not in m and "acute" not in m
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_empty_plan4_sub_tables_read_zero(host):
    r = rec(host, nutrients=host.table({}), fluids=host.table({}), acute=host.table({}))
    m = host.py(host.call("mirror.build", r, host.table(META)))
    for k, v in PLAN4_ABSENT.items():
        assert m[k] == v


def test_mirror_body_scalars_from_a_present_body(host):
    body = host.table({"fm": 20.0, "lm": 60.0, "band": "normal", "energyState": 1.25, "tac": 0.9, "dmod": 1.1,
                       "rmod": 0.8, "shownL": 5, "delta": 2, "ebDay": -300.0, "eeDay": 2400.0, "inDay": 2100.0,
                       "vStr": 4.0, "vHyp": 10.0, "vStrHigh": 0.0, "nHist": host.table({})})
    m = host.py(host.call("mirror.build", rec(host, body=body), host.table({"mode": 1, "version": "v", "build": "b"})))
    assert m["body_fm"] == 20.0 and m["body_lm"] == 60.0 and m["body_weight"] == 80.0
    assert m["body_band"] == "normal" and m["body_energyState"] == 1.25 and m["body_tac"] == 0.9
    assert m["body_dmod"] == 1.1 and m["body_rmod"] == 0.8 and m["body_shownL"] == 5 and m["body_delta"] == 2
    assert m["body_ebDay"] == -300.0 and m["body_eeDay"] == 2400.0 and m["body_inDay"] == 2100.0
    assert m["body_dStr"] == 0.5 and m["body_dHyp"] == 0.5
    assert "body" not in m
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_of_a_pre_plan5_record_reads_zero_effects(host):
    m = host.py(host.call("mirror.build", rec(host), host.table(META)))
    for k, v in PLAN5_ABSENT.items():
        assert m[k] == v and type(m[k]) is type(v)
    assert len([k for k in m if k.startswith("effects_")]) == 20


def test_mirror_carries_the_effects_set(host):
    vals = {k: i + 0.5 for i, k in enumerate(EFFECT_NUMBERS)}
    eff = host.table(dict(vals, own=host.table({"nv": True, "ss": False}), key=host.table({"ep": 3}), mNut=2.0))
    m = host.py(host.call("mirror.build", rec(host, effects=eff), host.table(META)))
    for k, v in vals.items():
        assert m["effects_" + k] == v
    assert m["effects_nv"] is True and m["effects_ss"] is False
    assert sorted(k for k in m if k.startswith("effects_")) == sorted(PLAN5_ABSENT)
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_effects_missing_fields_and_own_read_zero(host):
    eff = host.table({"aimMul": 0.9, "speedMul": "x"})
    m = host.py(host.call("mirror.build", rec(host, effects=eff), host.table(META)))
    assert m["effects_aimMul"] == 0.9 and m["effects_speedMul"] == 0 and m["effects_healMul"] == 0
    assert m["effects_nv"] is False and m["effects_ss"] is False
