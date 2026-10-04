import pytest


def rec(host, **kw):
    r = {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False}
    r.update(kw)
    return host.table(r)


def test_mirror_is_flat_scalars_only(host):
    m = host.py(host.call("mirror.build", rec(host), host.table({"mode": 1, "version": "0.1.0", "build": "42.20.4"})))
    assert m == {"v": 1, "username": "admin", "firstSeen": 1.5, "lastSeen": 2.25, "resets": 0, "dead": False,
                 "mode": 1, "version": "0.1.0", "build": "42.20.4"}
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


def test_mirror_copies_rather_than_aliases_the_record(host):
    r = rec(host)
    m = host.call("mirror.build", r, host.table({"mode": 2, "version": "x", "build": "y"}))
    m["lastSeen"] = 99
    assert r["lastSeen"] == 2.25


def test_mirror_meta_is_required(host):
    with pytest.raises(Exception):
        host.call("mirror.build", rec(host), None)
