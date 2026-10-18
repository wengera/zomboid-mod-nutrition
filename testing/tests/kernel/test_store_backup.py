"""The record's backup on the character and the store's load rule (Plan 16 Task 3; spec section 1.4).

NR_Server_Backup keeps the store slot's own text, cut into parts, with its sum and the world age the store step ran at,
in the player's modData (NutritionRevamp.backup), written only from the store's save (F.save), never sent to the client
(fix 1, ruling M1). NR_Server_Store's load rule (S.pick) reads it at the read of a record not in memory: a missing or
unreadable store file restores from it, a store record whose latest stamp is past the world clock (a hard kill rolled
the world back under it) restores from it, and otherwise the store wins; a rejected backup beside a good store is
rewritten at the next store step. A copy ahead of the world is valid (fix 1, review H1: the engine saves the character,
its modData with it, every 180 real seconds apart from the world), and the resume moves a record past the world back
onto its clock. The hosts are test_store_file_shape.py's (the 42.21 file API over NR_T.files); the player stand-in
gains a modData table and the env a sendServerCommand that records each send (there must be none)."""
import json

import pytest

from .test_store_file_shape import ROOT, ADMIN, boot, run_minutes, files_of, newest, gen_of, opened_with, lst

SENDS = r"""
NR_T.sent = {}
sendServerCommand = function(p, module, command, args)
    NR_T.sent[#NR_T.sent + 1] = { p = p, module = module, command = command, args = args }
end
"""

MD = r"""
function(p, doc)
    p.md = {}
    if doc ~= nil then p.md.NutritionRevamp = { backup = doc } end
    p.getModData = function(s) return s.md end
    return p
end
"""

NAME = "admin"


def host(files=None, env=""):
    return boot(files=files, env=SENDS + env)


def mdplayer(h, doc=None):
    """The host's player stand-in with a modData table, holding doc as its backup when given."""
    return h.rt.eval(MD)(h.player(NAME), doc)


def doc_py(p):
    """The backup on p as a Python dict (n, parts, sum, age), or None."""
    root = p.md.NutritionRevamp
    d = root.backup if root is not None else None
    if d is None:
        return None
    return {"n": d.n, "parts": [d.parts[i] for i in range(1, int(d.n) + 1)], "sum": d.sum, "age": d.age}


def doc_lua(h, d):
    """A Python backup dict as a table of h's runtime."""
    return h.rt.table_from({"n": d["n"], "parts": h.rt.table(*d["parts"]), "sum": d["sum"], "age": d["age"]})


def text_of(d):
    return "".join(d["parts"])


def minute(h, m, dt_ms=61000):
    """Game minute m (age 100 + m/60) dt_ms real ms after the last, then the queue's ticks."""
    h.T.age = 100.0 + m / 60
    h.T.now = h.T.now + dt_ms
    h.minute()
    h.tick(25)


def step(h, age, dt_ms=1000):
    """One game minute at world age `age`, dt_ms real ms after the last (inside the save gap by default)."""
    h.T.age = age
    h.T.now = h.T.now + dt_ms
    h.minute()
    h.tick(25)


def encoded(h, r):
    """The record's inputs as the store encodes them: the byte-equality the restore is held to."""
    return h.K.json.encode(h.K.store.inputsOnly(r), h.NR.server.store.file.fmt)


def played(minutes=6):
    """admin online for `minutes` game minutes a real minute apart: every minute past the first phase saves."""
    h = host()
    p = mdplayer(h)
    h.online(p)
    for m in range(1, minutes + 1):
        minute(h, m)
    return h, p


def wine(h):
    h.NR.server.intake.land(h.record(NAME), NAME, h.K.vector.fluid(h.NR.data.fluids.get("Wine"), 0.25))


def test_the_backup_is_the_newest_slot_text_with_its_sum_and_age_and_is_never_sent():
    h, p = played()
    d = doc_py(p)
    files = files_of(h)
    top = newest(files, ROOT + ADMIN)
    assert text_of(d) == files[top]                                   # the store's own text: no second format
    assert d["n"] == len(d["parts"]) and all(len(s) <= h.NR.server.backup.PART for s in d["parts"])
    assert d["sum"] == h.NR.server.backup.sum(text_of(d), d["age"])
    assert d["age"] == h.record(NAME).lastSeen
    sent = [h.T.sent[i] for i in range(1, len(h.T.sent) + 1)]
    assert h.NR.server.backup.stats.writes > 0
    assert [s for s in sent if s.command == "backup"] == []         # fix 1, ruling M1: no client mirror


def test_a_long_text_is_cut_into_parts_under_the_string_limit():
    h = host()
    B = h.NR.server.backup
    text = "x" * (2 * B.PART + 17)
    d = B.doc(text, 101.5)
    assert d.n == 3 and len(d.parts[1]) == B.PART and len(d.parts[3]) == 17
    assert "".join(d.parts[i] for i in range(1, 4)) == text
    assert B.sum(text, 101.5) != B.sum(text, 101.5 + 1 / 3600) and B.sum(text, 1.0) != B.sum("y" + text[1:], 1.0)
    assert 0 <= B.sum(text, 101.5) < B.MOD


def test_the_backup_is_written_only_at_the_store_save():
    # Rule 6: the copy follows the store's save cadence (a real minute, or a dirty mark), never the game minute
    h = host()
    p = mdplayer(h)
    h.online(p)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval("function(B, C) local w = B.write; B.write = function(...) C.n = C.n + 1; return w(...) end end")(
        h.NR.server.backup, C)
    slots = lambda: len(opened_with(h, ROOT + ADMIN))
    for m in range(1, 31):
        minute(h, m, 1000)                                            # 30 game minutes in 30 real seconds
    assert slots() <= 1 and C.n == slots()
    for m in range(31, 36):
        minute(h, m, 61000)                                           # five saves, one a real minute
    assert C.n == slots() and C.n >= 5
    n = C.n
    wine(h)                                                           # a landed drink marks the slot dirty
    minute(h, 36, 1000)
    assert C.n == slots() == n + 1
    h.online()                                                        # the departure's flush has no player
    minute(h, 37, 1000)
    minute(h, 38, 1000)
    assert slots() == n + 2 and C.n == n + 1


def test_a_deleted_store_restores_byte_equal_from_the_backup():
    h, p = played()
    d = doc_py(p)
    age = h.record(NAME).lastSeen + 2.0                               # the return, two game hours on
    ha = host(files=files_of(h))                                      # the store's own load, for the reference
    ra = ha.NR.server.store.get(NAME, age, mdplayer(ha, doc_lua(ha, d)))
    hb = host()                                                       # the folder deleted
    pb = mdplayer(hb, doc_lua(hb, d))
    rb = hb.NR.server.store.get(NAME, age, pb)
    assert hb.NR.server.backup.stats.restored == 1 and ha.NR.server.backup.stats.restored == 0
    assert encoded(hb, rb) == encoded(ha, ra)
    assert hb.NR.server.store.stats.resumes == 1 and rb.lastSeen == age
    # the restore reaches the store at the next step (the return minute runs nothing), past the backup's generation
    hb.online(pb)
    step(hb, age + 1 / 60)
    step(hb, age + 2 / 60)
    files = files_of(hb)
    top = newest(files, ROOT + ADMIN)
    assert top is not None and gen_of(files[top]) > gen_of(text_of(d))


def test_a_store_ahead_of_the_world_restores_the_backup_and_lands_no_food_twice():
    h, p = played()
    saved = doc_py(p)                                                 # the world's last save holds this copy
    world = h.T.age
    assert h.record(NAME).acute.gutAlc == 0
    wine(h)                                                           # landed after that save
    for m in range(7, 13):
        minute(h, m)                                                  # the store saves the wine, then runs on
    files = files_of(h)
    ahead = json.loads(files[newest(files, ROOT + ADMIN)])
    assert ahead["rec"]["acute"]["gutAlc"] > 0 and ahead["rec"]["lastSeen"] > world + 5 / 60
    # the hard kill: the world back at its save, the store file not
    back = world + 1 / 60
    h2 = host(files=files, env="\nNR_T.now = %d\n" % (h.T.now + 120000))
    q = mdplayer(h2, doc_lua(h2, saved))
    h2.online(q)
    h2.T.age = back
    h2.minute()
    h2.tick(25)
    S, B = h2.NR.server.store, h2.NR.server.backup
    assert B.stats.restored == 1 and S.stats.resumes == 1
    r = h2.record(NAME)
    hr = host()                                                       # the reference: the copy restored alone
    rr = hr.NR.server.store.get(NAME, back, mdplayer(hr, doc_lua(hr, saved)))
    assert encoded(h2, r) == encoded(hr, rr)
    assert r.acute.gutAlc == 0                                        # the wine is not landed again
    assert r.lastSeen == back and r.nutrients.lastAgeH == back        # no stretch integrated twice
    step(h2, back + 1 / 60, 61000)                                   # the first step back: one online minute
    assert h2.NR.server.players.stalls == 0 and h2.record(NAME).nutrients.lastAgeH == back + 1 / 60
    # the restore's write outranks the ahead file: a restart with no backup now loads the restored record
    h3 = host(files=files_of(h2))
    rec3 = h3.NR.server.store.file.load(NAME)
    assert rec3.acute.gutAlc == 0 and rec3.lastSeen < ahead["rec"]["lastSeen"]


def test_a_store_ahead_with_no_valid_backup_is_kept_moved_back_onto_the_world_and_logged():
    # fix 1 (review H1): the kept store moves back by world - latest, so no stamp is in the future (until fix 1 it was
    # kept ahead, every step clamped to 0 and re-stamped backwards and the heals fired); the monotony table, the
    # unfed clock and the nicotine anchor survive with no heal
    h, p = played()
    world = h.T.age
    rec = h.record(NAME)
    rec.monotony = h.rt.table_from({"t": h.rt.table_from({"Base.Bread": h.rt.table_from({"n": 2.0, "last": world})})})
    rec.satiety.nicH = world - 1.0
    for m in range(7, 10):
        minute(h, m)
    files = files_of(h)
    ahead = json.loads(files[newest(files, ROOT + ADMIN)])["rec"]
    assert ahead["lastSeen"] > world and "fedAgeH" in ahead["drain"]
    h2 = host(files=files)
    q = mdplayer(h2)                                                  # no copy on the character
    r = h2.NR.server.store.get(NAME, world, q)
    B, S = h2.NR.server.backup, h2.NR.server.store
    assert B.stats.restored == 0 and B.stats.aheadKept == 1 and B.stats.rejected.absent == 1
    assert len([x for x in h2.printed() if "past the world clock" in x and "no valid backup" in x]) == 1
    assert h2.K.resume.latest(r) == world and S.stats.rewound == 1 and S.stats.resumes == 0
    gap = world - ahead["lastSeen"]
    assert r.lastSeen == world and r.monotony.t["Base.Bread"].n == 2.0
    assert r.monotony.t["Base.Bread"].last == pytest.approx(world + gap, abs=1e-9)
    assert r.satiety.nicH == pytest.approx(ahead["satiety"]["nicH"] + gap, abs=1e-9)
    assert r.drain.fedAgeH == pytest.approx(ahead["drain"]["fedAgeH"] + gap, abs=1e-9)
    h2.online(q)
    step(h2, world + 1 / 60)                                          # the return minute runs nothing
    step(h2, world + 2 / 60)
    r = h2.record(NAME)
    assert r.monotony.t["Base.Bread"].n == 2.0 and h2.NR.server.players.stalls == 0
    assert r.nutrients.lastAgeH == world + 2 / 60


def test_a_jar_shaped_hard_kill_restores_the_characters_copy_with_no_double_integration_and_no_re_eat():
    # fix 1 (review H1, scratch r5): the world saved at W0, play runs on 3 game hours with a wine, the engine's 180 s
    # player save takes the copy after the wine, the store runs on 3 more saves, then the kill: the world is back at W0
    # (hours before the copy), the character back at its snapshot (copy and inventory together). The copy, ahead of the
    # world, is the right record: restored, moved back onto the clock, the wine in it once and never landed again.
    h, p = played()
    w0 = h.T.age                                                      # the world's last save
    for m in range(7, 120):
        minute(h, m)
    wine(h)
    for m in range(120, 176):
        minute(h, m)
    snap = doc_py(p)                                                  # the character's 180 s snapshot
    for m in range(176, 179):
        minute(h, m)
    files = files_of(h)
    ahead = json.loads(files[newest(files, ROOT + ADMIN)])["rec"]
    copy = json.loads(text_of(snap))["rec"]
    assert copy["acute"]["gutAlc"] > 0 and snap["age"] > w0 + 2.5 and ahead["lastSeen"] > snap["age"]
    back = w0 + 1 / 60
    h2 = host(files=files, env="\nNR_T.now = %d\n" % (h.T.now + 120000))
    q = mdplayer(h2, doc_lua(h2, snap))
    h2.online(q)
    step(h2, back, 61000)
    S, B = h2.NR.server.store, h2.NR.server.backup
    assert B.stats.restored == 1 and B.stats.aheadKept == 0 and S.stats.rewound == 1
    r = h2.record(NAME)
    assert h2.K.resume.latest(r) == back and r.lastSeen == back and r.nutrients.lastAgeH == back
    hr = host()                                                       # the reference: the copy restored alone
    rr = hr.NR.server.store.get(NAME, back, mdplayer(hr, doc_lua(hr, snap)))
    assert encoded(h2, r) == encoded(hr, rr)                         # the copy's wine, once; nothing re-landed
    assert r.acute.gutAlc == pytest.approx(copy["acute"]["gutAlc"], rel=1e-12)
    step(h2, back + 1 / 60, 61000)                                   # the first step back: one online minute
    r = h2.record(NAME)
    assert h2.NR.server.players.stalls == 0 and r.nutrients.lastAgeH == back + 1 / 60
    h3 = host(files=files_of(h2))                                     # the restore's write outranks the ahead file
    assert h3.NR.server.store.file.load(NAME).lastSeen < back + 1


def test_a_store_whose_latest_stamp_is_the_world_age_exactly_is_not_ahead():
    # review L1 (pick-latest-ge): a latest stamp equal to the world age is the store's own, never a rollback
    h, p = played()
    d = doc_py(p)
    files = files_of(h)
    h2 = host(files=files)
    latest = h2.K.resume.latest(h2.NR.server.store.file.load(NAME))
    h3 = host(files=files)
    h3.NR.server.store.get(NAME, latest, mdplayer(h3, doc_lua(h3, d)))
    assert h3.NR.server.backup.stats.restored == 0 and h3.NR.server.backup.stats.aheadKept == 0


def test_a_store_that_cannot_write_still_leaves_the_copy():
    # review L1 (write-after-file): the copy is written before the file, whether or not the file write holds
    h = host(env="\nNR_T.nilWriter = true\n")
    p = mdplayer(h)
    h.online(p)
    for m in range(1, 4):
        minute(h, m)
    assert h.NR.server.store.file.stats.writes == 0 and h.NR.server.store.file.stats.writeFailures >= 1
    d = doc_py(p)
    assert d is not None and json.loads(text_of(d))["rec"]["username"] == NAME


def test_a_restore_over_slots_unread_at_the_touch_outranks_a_newer_departure_flush():
    # review L1 (restore-no-plus1): the copy holds gen g; the departure's flush wrote g + 1 with no copy; at the next
    # boot both slots go unread at the touch, so the copy restores, and its first write must outrank g + 1
    h, p = played()
    d = doc_py(p)
    g = gen_of(text_of(d))
    h.online()
    minute(h, 7, 1000)
    minute(h, 8, 1000)                                                # the flush runs from its queue slot
    files = files_of(h)
    G = gen_of(files[newest(files, ROOT + ADMIN)])
    assert G == g + 1
    h2 = host(files=files)
    q = mdplayer(h2, doc_lua(h2, d))
    h2.T.readerNil = 2                                                # both slot reads answer nil at the touch
    age = h.T.age + 1.0
    h2.NR.server.store.get(NAME, age, q)
    assert h2.NR.server.backup.stats.restored == 1
    h2.online(q)
    step(h2, age + 1 / 60)
    step(h2, age + 2 / 60)
    files2 = files_of(h2)
    assert gen_of(files2[newest(files2, ROOT + ADMIN)]) > G


def tampered(kind, d, B):
    d = dict(d, parts=list(d["parts"]))
    if kind == "edited":
        s = d["parts"][0]
        i = s.index('"resets":') + len('"resets":')
        d["parts"][0] = s[:i] + "7" + s[i + 1:]
    elif kind == "truncated":
        d["n"] = d["n"] + 1
    elif kind == "unfinished":
        t = text_of(d).replace('"done":true', '"done":false')
        d["parts"] = [t]
        d["n"] = 1
        d["sum"] = B.sum(t, d["age"])
    elif kind == "too many parts":
        t = text_of(d)
        k = len(t) // 65 + 1
        d["parts"] = [t[i * k:(i + 1) * k] for i in range(65)]
        d["n"] = 65
        assert "".join(d["parts"]) == t and all(d["parts"])
    elif kind == "other user":
        t = text_of(d).replace('"username":"admin"', '"username":"bob"')
        d["parts"] = [t]
        d["n"] = 1
        d["sum"] = B.sum(t, d["age"])
    return d


@pytest.mark.parametrize("kind,why", [("wiped", "absent"), ("edited", "sum"), ("truncated", "garbled"),
                                      ("unfinished", "garbled"), ("too many parts", "garbled"),
                                      ("other user", "garbled")])
def test_a_wiped_or_edited_backup_is_rejected_the_store_kept_and_the_backup_rewritten(kind, why):
    h, p = played()
    d = doc_py(p)
    h2 = host(files=files_of(h))
    B = h2.NR.server.backup
    q = mdplayer(h2, None if kind == "wiped" else doc_lua(h2, tampered(kind, d, B)))
    age = h.T.age + 1.0
    r = h2.NR.server.store.get(NAME, age, q)
    assert B.stats.restored == 0 and B.stats.rejected[why] == 1
    assert r.resets == 0 and h2.NR.server.store.stats.loads == 1      # the store's record
    assert h2.NR.server.store.file.dirty[NAME] is True                # rewritten at the next store step
    assert len([x for x in h2.printed() if "backup rejected (" + why + ")" in x]) == 1
    h2.online(q)
    step(h2, age + 1 / 60)                                            # the return minute runs nothing
    step(h2, age + 2 / 60)                                            # the dirty mark saves at once
    rec, gen, at = B.read(q, NAME)
    assert rec is not None and gen == gen_of(text_of(d)) + 1 and at == age + 2 / 60


def test_a_good_backup_beside_a_good_store_reads_the_store_and_marks_nothing():
    h, p = played()
    h2 = host(files=files_of(h))
    q = mdplayer(h2, doc_lua(h2, doc_py(p)))
    h2.NR.server.store.get(NAME, h.T.age + 1.0, q)
    B = h2.NR.server.backup
    assert B.stats.reads == 1 and B.stats.restored == 0 and B.stats.aheadKept == 0
    assert sum(B.stats.rejected[k] for k in ("absent", "garbled", "sum")) == 0
    assert h2.NR.server.store.file.dirty[NAME] is None


def test_a_player_with_no_moddata_reads_the_store_alone():
    h, p = played()
    h2 = host(files=files_of(h))
    h2.NR.server.store.get(NAME, h.T.age + 1.0, h2.player(NAME))      # the stand-in with no getModData
    B = h2.NR.server.backup
    assert B.stats.reads == 0 and h2.NR.server.store.file.dirty[NAME] is None
    assert B.write(h2.player(NAME), "{}", 1.0) is False and B.write(mdplayer(h2), "{}", float("nan")) is False


def test_neither_a_store_nor_a_backup_makes_a_fresh_record():
    h = host()
    q = mdplayer(h)
    r = h.NR.server.store.get(NAME, 100.0, q)
    assert h.NR.server.store.fresh[NAME] is True and h.NR.server.store.stats.created == 1 and r.firstSeen == 100.0
    assert h.NR.server.backup.stats.restored == 0


def test_a_respawns_fresh_record_replaces_the_backup():
    h, p = played()
    old = doc_py(p)
    assert json.loads(text_of(old))["rec"]["resets"] == 0
    q = mdplayer(h, doc_lua(h, old))                                  # the new character, holding the old copy
    h.T.age = h.T.age + 1 / 60
    h.fire("OnNewGame", q, None)
    h.online(q)
    minute(h, 8, 1000)                                                # the reset's dirty mark saves at once
    d = json.loads(text_of(doc_py(q)))
    assert d["rec"]["resets"] == 1 and d["rec"]["firstSeen"] == pytest.approx(100.0 + 7 / 60, abs=1e-9)
    assert json.loads(files_of(h)[newest(files_of(h), ROOT + ADMIN)]) == d
