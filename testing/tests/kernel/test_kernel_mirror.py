import pytest


def rec(host, **kw):
    r = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False}
    r.update(kw)
    return host.table(r)


def test_mirror_is_flat_scalars_only(host):
    m = host.py(host.call("mirror.build", rec(host), host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    expect = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False,
              "mode": 1, "version": "0.1.0", "build": "42.20.4", "stomachFill": 1}      # Plan 2: the fill, full by default
    expect.update({"pool_" + k: 0 for k in ("calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate")})
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


POOL_KEYS = ("calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate")


def test_mirror_carries_the_stomach_fill_and_the_pool_scalars(host):
    pool = host.table({k: 0.0 for k in POOL_KEYS})
    pool["calories"] = 512.5
    pool["iron"] = 1.25
    r = rec(host, stomachFill=0.375, pool=pool, stomach=host.table({"bulk": 3.0, "buffer": host.table({})}))
    m = host.py(host.call("mirror.build", r, host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    assert m["stomachFill"] == 0.375
    assert m["pool_calories"] == 512.5 and m["pool_iron"] == 1.25 and m["pool_vitC"] == 0.0
    assert {"pool_" + k for k in POOL_KEYS} <= set(m)
    assert "pool" not in m and "stomach" not in m
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_of_a_record_with_no_stomach_or_pool_reads_full_and_zero(host):
    m = host.py(host.call("mirror.build", rec(host), host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    assert m["stomachFill"] == 1
    for k in POOL_KEYS:
        assert m["pool_" + k] == 0


def test_mirror_pool_key_missing_from_the_record_reads_zero(host):
    r = rec(host, pool=host.table({"calories": 10.0}))
    m = host.py(host.call("mirror.build", r, host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    assert m["pool_calories"] == 10.0 and m["pool_iron"] == 0
