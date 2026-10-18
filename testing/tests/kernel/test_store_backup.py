"""The record's backup on the character and the store's load rule (Plan 16 Task 3; spec section 1.4).

NR_Server_Backup keeps the store slot's own text, cut into parts, with its sum and the world age the store step ran at,
in the player's modData (NutritionRevamp.backup), written only from the store's save (F.save) and sent to the owning
client. NR_Server_Store's load rule (S.pick) reads it at the read of a record not in memory: a missing or unreadable
store file restores from it, a store record whose latest stamp is past the world clock (a hard kill rolled the world
back under it) restores from it, and otherwise the store wins; a rejected backup beside a good store is rewritten at
the next store step. The hosts are test_store_file_shape.py's (the 42.21 file API over NR_T.files); the player
stand-in gains a modData table and the env a sendServerCommand that records each send."""
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


def test_the_backup_is_the_newest_slot_text_with_its_sum_and_age_and_reaches_the_client():
    h, p = played()
    d = doc_py(p)
    files = files_of(h)
    top = newest(files, ROOT + ADMIN)
    assert text_of(d) == files[top]                                   # the store's own text: no second format
    assert d["n"] == len(d["parts"]) and all(len(s) <= h.NR.server.backup.PART for s in d["parts"])
    assert d["sum"] == h.NR.server.backup.sum(text_of(d), d["age"])
    assert d["age"] == h.record(NAME).lastSeen
    sent = [h.T.sent[i] for i in range(1, len(h.T.sent) + 1)]
    backups = [s for s in sent if s.command == "backup"]
    assert backups and all(s.module == "NutritionRevamp" and h.G.rawequal(s.p, p) for s in backups)
    assert h.G.rawequal(backups[-1].args, p.md.NutritionRevamp.backup)
    assert h.NR.server.backup.stats.sends == len(backups) == h.NR.server.backup.stats.writes


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


def test_a_store_ahead_with_no_valid_backup_is_kept_and_logged():
    h, p = played()
    world = h.T.age
    for m in range(7, 10):
        minute(h, m)
    h2 = host(files=files_of(h))
    q = mdplayer(h2)                                                  # no copy on the character
    r = h2.NR.server.store.get(NAME, world, q)
    B = h2.NR.server.backup
    assert B.stats.restored == 0 and B.stats.aheadKept == 1 and B.stats.rejected.absent == 1
    assert r.lastSeen > world
    assert len([x for x in h2.printed() if "past the world clock" in x and "no valid backup" in x]) == 1


def tampered(kind, d, B):
    d = dict(d, parts=list(d["parts"]))
    if kind == "edited":
        s = d["parts"][0]
        i = s.index('"resets":') + len('"resets":')
        d["parts"][0] = s[:i] + "7" + s[i + 1:]
    elif kind == "truncated":
        d["n"] = d["n"] + 1
    elif kind == "ahead":
        d["age"] = d["age"] + 50.0
        d["sum"] = B.sum(text_of(d), d["age"])
    elif kind == "other user":
        t = text_of(d).replace('"username":"admin"', '"username":"bob"')
        d["parts"] = [t]
        d["n"] = 1
        d["sum"] = B.sum(t, d["age"])
    return d


@pytest.mark.parametrize("kind,why", [("wiped", "absent"), ("edited", "sum"), ("truncated", "garbled"),
                                      ("ahead", "ahead"), ("other user", "garbled")])
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
    rec, gen, at = B.read(q, NAME, age + 2 / 60)
    assert rec is not None and gen == gen_of(text_of(d)) + 1 and at == age + 2 / 60


def test_a_good_backup_beside_a_good_store_reads_the_store_and_marks_nothing():
    h, p = played()
    h2 = host(files=files_of(h))
    q = mdplayer(h2, doc_lua(h2, doc_py(p)))
    h2.NR.server.store.get(NAME, h.T.age + 1.0, q)
    B = h2.NR.server.backup
    assert B.stats.reads == 1 and B.stats.restored == 0 and B.stats.aheadKept == 0
    assert sum(B.stats.rejected[k] for k in ("absent", "garbled", "sum", "ahead")) == 0
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
