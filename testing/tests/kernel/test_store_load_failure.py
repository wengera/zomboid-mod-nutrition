"""A failed load lays a fresh record (Plan 11d Task 9b fix round 1, ruling C9-10).

A slot file whose record K.store.load cannot build (a string where a mass sits, a malformed nutrients table) used to
leave the raw stored table in place for the whole sight: Nutrients raised every minute, THIRST and FATIGUE froze.
S.load (and S.recover) now lay a fresh record in place on any failed load, count it in store.stats.failures and log
the username, so the character runs the tested fresh-character path. A body whose fm, lm or lastAgeH is absent or
non-finite, or whose sex is a number other than 1 or 2, is not a failed load (Plan 12 A4): K.store.bodyBase heals the
field and the record is kept.

The host is the store's file stand-in (test_store_file_shape.FILES) with the writer's engine stand-ins
(test_writer_shape.ENV) and its stats player, so the writer runs; a corrupt slot is in place before OnServerStarted.
"""
import json

import pytest

from .server_host import Host
from .test_store_file_shape import ADMIN, FILES, ROOT, newest
from .test_writer_shape import ENV as WRITER_ENV, STATS

STEPS = ("kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "writer", "reconcile", "minute")

GOOD_BODY = {"fm": 16.0, "lm": 64.0, "sex": 1, "lastAgeH": 99.0}

CASES = {
    "body with a string fm": {"body": dict(GOOD_BODY, fm="x")},
    "malformed nutrients": {"body": dict(GOOD_BODY), "nutrients": {"iron": {"p": "x", "g": "x"}, "epoch": "x"}},
}

# Plan 12 A4: a saved body as K.body.new lays its identity fields, then one of the four the load heals made unreadable
FULL_BODY = dict(GOOD_BODY, l0=5, r=1.0, traitCarry=0.0)

HEALED = {
    "body without fm": {k: v for k, v in FULL_BODY.items() if k != "fm"},
    "body without lm": {k: v for k, v in FULL_BODY.items() if k != "lm"},
    "body without lastAgeH": {k: v for k, v in FULL_BODY.items() if k != "lastAgeH"},
    "body with sex 3": dict(FULL_BODY, sex=3),
}


def slot(rec):
    base = {"username": "admin", "firstSeen": 50.0, "lastSeen": 99.0, "resets": 2, "dead": False}
    base.update(rec)
    return json.dumps({"gen": 3, "rec": base, "done": True}, separators=(",", ":"))


def index():
    return json.dumps({"gen": 3, "players": {"admin": 990}, "done": True}, separators=(",", ":"))


def boot(rec):
    files = {ROOT + ADMIN + "a.json": slot(rec), ROOT + "index_a.json": index()}
    text = "NR_T = NR_T or {}\nNR_T.mode = 1\n" + WRITER_ENV + FILES
    for k, v in files.items():
        text = text + "\nNR_T.files[%r] = [==[%s]==]\n" % (k, v)
    h = Host(extra_env=text)
    h.fire("OnGameBoot")
    return h


def failures(h):
    out = {}
    for name in STEPS:
        mod = h.NR.server[name]
        if mod is not None and mod.stats is not None and mod.stats.failures is not None:
            out[name] = mod.stats.failures
    return out


@pytest.mark.parametrize("case", sorted(CASES))
def test_a_corrupt_slot_loads_as_a_fresh_character_and_runs_clean(case):
    h = boot(CASES[case])
    p = h.rt.eval("NR_T.statsPlayer")(h.player("admin"), h.rt.eval(STATS))
    h.online(p)
    f0 = failures(h)
    thirst0, fatigue0 = p.st.v.THIRST, p.st.v.FATIGUE
    for m in range(1, 31):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 61000
        h.minute()
        h.tick(25)
    assert failures(h) == f0, (case, failures(h), [s for s in h.printed() if "failed" in s])
    assert h.NR.server.store.stats.failures == 1, case
    assert any("store: load failed for admin" in s for s in h.printed()), case
    assert p.st.sets.THIRST is not None and p.st.v.THIRST != thirst0, case
    assert p.st.sets.FATIGUE is not None and p.st.v.FATIGUE != fatigue0, case
    rec = h.record("admin")
    assert rec.username == "admin" and rec.body is not None and rec.nutrients is not None
    files = {k: h.T.files[k] for k in h.T.files.keys()}
    saved = json.loads(files[newest(files, ROOT + ADMIN)])["rec"]
    b = saved["body"]
    assert all(isinstance(b[k], (int, float)) for k in ("fm", "lm", "sex", "lastAgeH")), (case, b)
    assert isinstance(saved["nutrients"]["epoch"], (int, float)), case
    assert saved["nutrients"]["iron"]["p"] == pytest.approx(saved["nutrients"]["iron"]["p"]), case
    assert all(not isinstance(v, str) for v in saved["nutrients"]["iron"].values()), case


@pytest.mark.parametrize("case", sorted(HEALED))
def test_an_unreadable_body_field_heals_and_the_record_is_kept(case):
    # the slot's record survives (its resets, first sight and nutrients), no load fails, and every step runs clean
    h = boot({"body": HEALED[case], "nutrients": {"epoch": 7}})
    p = h.rt.eval("NR_T.statsPlayer")(h.player("admin"), h.rt.eval(STATS))
    h.online(p)
    f0 = failures(h)
    thirst0 = p.st.v.THIRST
    for m in range(1, 31):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 61000
        h.minute()
        h.tick(25)
    assert failures(h) == f0, (case, failures(h), [s for s in h.printed() if "fail" in s or "non-finite" in s])
    assert h.NR.server.store.stats.failures == 0, case
    assert not any("load failed" in s for s in h.printed()), case
    rec = h.record("admin")
    assert rec.resets == 2 and rec.firstSeen == 50.0 and rec.nutrients.epoch >= 7, case
    b = rec.body
    assert b.sex in (1, 2) and all(isinstance(b[k], (int, float)) for k in ("fm", "lm", "lastAgeH")), case
    assert p.st.v.THIRST != thirst0, case


@pytest.mark.parametrize("case", sorted(CASES))
def test_a_corrupt_slot_found_by_the_recovery_lays_a_fresh_record_in_place(case):
    # the first read at first sight finds the slots locked, so S.get makes a fresh record; the save's preload then
    # reads the corrupt file and S.recover's load raises: the fresh record is laid again in the same table
    h = boot(CASES[case])
    h.T.readerNil = 2
    p = h.rt.eval("NR_T.statsPlayer")(h.player("admin"), h.rt.eval(STATS))
    h.online(p)
    f0 = failures(h)
    thirst0 = p.st.v.THIRST
    handle = None
    for m in range(1, 31):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 61000
        h.minute()
        h.tick(25)
        if handle is None and h.record("admin") is not None:
            handle = h.record("admin")
    assert failures(h) == f0, (case, failures(h), [s for s in h.printed() if "failed" in s])
    assert h.NR.server.store.stats.failures == 1, case
    assert any("store: load failed for admin (recovery)" in s for s in h.printed()), case
    assert h.G.rawequal(handle, h.record("admin"))
    assert p.st.v.THIRST != thirst0 and h.record("admin").body is not None
