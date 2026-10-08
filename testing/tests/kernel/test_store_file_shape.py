"""The server-local store (Plan 11 Task 11; Decision 3): per-player slot files, the two index files, the migration
from global modData, the prune. The file API is a Lua stand-in over NR_T.files that follows the 42.21 jar (J2,
T1102.3, T1102.4): getFileWriter TRUNCATES the file at the call (FileOutputStream at open, not at close) and answers
nil for a name holding `..`; the text lands at close; writeln raises here, because on a Windows host it appends CRLF
(the store writes with one write); getFileReader raises unless createIfNull is false (true would create an empty
file). NR_T.swallow (a path prefix) lands only half the text at close, as a PrintWriter that swallowed an I/O error
would, and NR_T.readerNil answers nil for that many reads, as a locked file would. A file the test hands boot() is
in place before OnServerStarted fires, as a restart finds it."""
import json
import re

from .server_host import Host

FILES = r"""
NR_T.files = NR_T.files or {}
NR_T.opened = {}
NR_T.readerCreate = {}
NR_T.crashOn = nil
NR_T.now = 1000000
getTimestampMs = function() return NR_T.now end
getServerName = function() return NR_T.serverName or "srv" end
getFileWriter = function(name, create, append)
    if string.find(name, "..", 1, true) ~= nil then return nil end   -- hasRelativePath: nil, never a raise
    if NR_T.nilWriter then return nil end
    NR_T.opened[#NR_T.opened + 1] = name
    NR_T.files[name] = ""                                              -- truncated at the call (T1102.4)
    local buf = {}
    return { write = function(s, text)
                 if NR_T.crashOn == name then error("the host died between open and close") end
                 buf[#buf + 1] = text
             end,
             writeln = function(s, text) error("writeln appends the host's separator (CRLF on Windows)") end,
             close = function(s)
                 local text = table.concat(buf)
                 local sw = NR_T.swallow
                 if sw ~= nil and string.sub(name, 1, string.len(sw)) == sw then
                     text = string.sub(text, 1, math.floor(string.len(text) / 2))   -- the PrintWriter swallowed it
                 end
                 NR_T.files[name] = text
             end }
end
NR_T.readerNil = 0
getFileReader = function(name, create)
    NR_T.readerCreate[#NR_T.readerCreate + 1] = create
    if create ~= false then error("getFileReader must be called with createIfNull false") end
    if NR_T.readerNil > 0 then                                         -- a locked file: the reader answers nil
        NR_T.readerNil = NR_T.readerNil - 1
        return nil
    end
    local text = NR_T.files[name]
    if text == nil then return nil end
    local lines = {}
    for line in string.gmatch(text .. "\n", "(.-)\n") do lines[#lines + 1] = line end
    local i = 0
    return { readLine = function(s) i = i + 1; return lines[i] end, close = function(s) end }
end
"""

MODDATA = r"""
NR_T.removed = {}
ModData = { tables = { ["NutritionRevamp.players"] = NR_T.oldStore } }
ModData.exists = function(name) return ModData.tables[name] ~= nil end
ModData.get = function(name) return ModData.tables[name] end
ModData.remove = function(name) local t = ModData.tables[name]; ModData.tables[name] = nil; NR_T.removed[#NR_T.removed + 1] = name; return t end
ModData.getOrCreate = function(name) error("getOrCreate must never be called (the leak)") end
"""

OLD = "{ olduser = { v = 2, username = 'olduser', firstSeen = 50.0, lastSeen = 60.0, resets = 2, dead = false } }"
ROOT = "NutritionRevamp/srv/"
ADMIN = "p_00610064006d0069006e_"      # hexName("admin"): four hex digits a code unit
OLDUSER = "p_006f006c00640075007300650072_"
OLDP = "p_006f006c0064_"                   # hexName("old")


def boot(files=None, old_store=None, env=""):
    text = FILES + env
    for k, v in (files or {}).items():
        assert "]==]" not in v
        text = text + "\nNR_T.files[%r] = [==[%s]==]\n" % (k, v)      # in place before OnServerStarted
    if old_store is not None:
        text = text + "\nNR_T.oldStore = " + old_store + "\n" + MODDATA
    return Host(extra_env=text)


def run_minutes(h, n, start=1):
    for m in range(start, start + n):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 61000                    # one real minute a game minute: past the save gap
        h.minute(); h.tick(25)


def files_of(h):
    return {k: h.T.files[k] for k in h.T.files.keys()}


def removed(h):
    return [h.T.removed[i] for i in range(1, len(h.T.removed) + 1)]


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def gen_of(text):
    m = re.search(r'"gen":(\d+)', text or "")
    return int(m.group(1)) if m and '"done":true' in text else None


def newest(files, prefix):
    """The path of the newest complete file of a pair (slots or index), by its gen."""
    paths = [k for k in files if k.startswith(prefix) and gen_of(files[k]) is not None]
    return max(paths, key=lambda k: gen_of(files[k])) if paths else None


def index_text(h):
    files = files_of(h)
    return files[newest(files, ROOT + "index_")]


def py(v):
    if hasattr(v, "items"):
        return {k: py(x) for k, x in v.items()}
    return v


def test_a_record_is_written_to_two_slots_and_read_back_after_a_restart():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 3)
    saved = files_of(h)
    slots = [k for k in saved if k.startswith(ROOT + ADMIN)]
    assert sorted(slots) == [ROOT + ADMIN + "a.json", ROOT + ADMIN + "b.json"]
    fm = h.record("admin").body.fm
    h2 = boot(files=saved)                           # a restart: a fresh Lua state over the same files
    h2.online(h2.player("admin"))
    run_minutes(h2, 1, start=10)
    assert abs(h2.record("admin").body.fm - fm) < 0.01
    assert h2.NR.server.store.stats.created == 0


def test_a_torn_newest_slot_falls_back_to_the_other():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 3)
    saved = files_of(h)
    top = newest(saved, ROOT + ADMIN)
    saved[top] = saved[top][: len(saved[top]) // 2]
    h2 = boot(files=saved)
    h2.online(h2.player("admin"))
    run_minutes(h2, 1, start=10)
    assert h2.NR.server.store.stats.created == 0
    assert h2.NR.server.store.file.stats.readFailures >= 1


def test_a_crash_between_open_and_close_loses_only_the_slot_being_written():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 1)
    F = h.NR.server.store.file
    r = h.record("admin")
    for _ in range(3):                               # gens 2, 3, 4 on top of the minute's gen 1
        assert F.save("admin", r)
    before = files_of(h)
    top = newest(before, ROOT + ADMIN)
    other = ROOT + ADMIN + ("a.json" if top.endswith("b.json") else "b.json")
    h.T.crashOn = other
    w0 = F.stats.writeFailures
    at = F.at["admin"]
    assert not F.save("admin", r)                   # the host dies between getFileWriter and close
    assert F.stats.writeFailures == w0 + 1
    assert h.T.files[other] == "" and h.T.files[top] == before[top]
    assert F.at["admin"] == at                      # a failed write moves nothing
    h.T.crashOn = None
    assert F.save("admin", h.record("admin")) and h.T.files[top] == before[top]
    assert F.stats.repaired == 0                    # no repair stood in for the rule
    h.T.files[other] = ""                           # back to the crash's files for the restart below
    h2 = boot(files=files_of(h))
    assert h2.NR.server.store.file.load("admin") is not None
    assert h2.NR.server.store.file.gen["admin"] == gen_of(before[top])


def test_the_writer_never_opens_the_slot_that_holds_the_newest_complete_record():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 1)
    F = h.NR.server.store.file
    r = h.record("admin")
    for k in range(8):
        top = newest(files_of(h), ROOT + ADMIN)
        n = len(h.T.opened)
        h.T.crashOn = ROOT + ADMIN + "b.json" if k in (2, 3, 5) else None   # failures between successes
        F.save("admin", r)
        opened = lst(h.T.opened)[n:]
        assert opened and top not in opened, (k, top, opened)
    h.T.crashOn = None
    assert newest(files_of(h), ROOT + ADMIN) is not None


def test_the_global_store_migrates_to_files_and_is_removed():
    h = boot(old_store=OLD)
    assert removed(h) == ["NutritionRevamp.players"]
    assert any(k.startswith(ROOT + OLDUSER) for k in files_of(h))
    assert h.NR.server.store.file.stats.migrated == 1
    r = h.NR.server.store.get("olduser", 100.0)
    assert r.resets == 2 and r.v == 3 and r.satiety is None


def test_the_migration_run_twice_changes_nothing_the_second_time():
    h = boot(old_store=OLD)
    before = files_of(h)
    h.G.ModData.tables["NutritionRevamp.players"] = h.rt.eval(OLD)   # the table back, as after a crash
    assert h.NR.server.store.file.migrate() == 0
    after = files_of(h)
    assert {k: v for k, v in after.items() if "index_" not in k} == {k: v for k, v in before.items() if "index_" not in k}
    assert h.NR.server.store.file.stats.migrated == 1 and h.NR.server.store.file.stats.kept == 1


def test_a_crash_before_the_world_save_never_overwrites_newer_slot_files():
    h = boot(old_store=OLD)
    r = h.NR.server.store.get("olduser", 100.0)
    r.resets = 7                                     # play moved the record on; its slot holds it
    assert h.NR.server.store.file.save("olduser", r)
    saved = files_of(h)
    h2 = boot(files=saved, old_store=OLD)            # the world rolled back: the stale global table is back
    slots = sorted(k for k in saved if k.startswith(ROOT + OLDUSER))
    assert {k: h2.T.files[k] for k in slots} == {k: saved[k] for k in slots}
    assert h2.NR.server.store.file.stats.migrated == 0 and h2.NR.server.store.file.stats.kept == 1
    assert h2.NR.server.store.get("olduser", 100.0).resets == 7
    assert removed(h2) == ["NutritionRevamp.players"]


def test_nothing_is_ever_created_under_a_global_modData_name():
    h = boot(old_store="{}")
    h.online(h.player("admin"))
    run_minutes(h, 2)                                # getOrCreate raises if anything calls it
    assert h.G.rawequal(h.NR.server.store.attach(), h.NR.server.store.records)


def test_a_departure_flush_writes_the_slot_and_the_index_follows():
    h = boot()
    h.online(h.player("old"), h.player("live"))
    run_minutes(h, 2)
    h.online(h.player("live"))
    n = len(h.T.opened)
    run_minutes(h, 1, start=3)                       # old departs: its flush rides the queue
    assert ROOT + OLDP + "a.json" in lst(h.T.opened)[n:] or ROOT + OLDP + "b.json" in lst(h.T.opened)[n:]
    run_minutes(h, 4, start=4)                       # the debounced store.index task writes the index
    assert '"old":' in index_text(h)


def test_the_store_tasks_carry_a_dot_so_no_username_can_equal_one():
    # ServerWorldDatabase.isValidUserName refuses a name holding "." (L776), and authClient refuses an invalid name
    # (@61-@84 L1041-L1044, 42.21): a task named like a user would merge into that user's queue entry and never run.
    h = boot()
    h.online(h.player("old"))
    run_minutes(h, 1)
    h.online()
    h.minute()                                       # old departs: the flush is queued as a task
    names = list(h.NR.server.players.tasks.keys())
    assert names == ["store.flush." + "006f006c0064"]
    assert all("." in n for n in names)
    h.T.now = h.T.now + 3600001
    h.minute()                                       # the hourly prune rides the queue as a task too
    assert "store.prune" in list(h.NR.server.players.tasks.keys())


def test_prune_empties_offline_records_past_the_keep_in_real_days():
    h = boot()
    h.online(h.player("old"), h.player("live"))
    run_minutes(h, 2)
    h.online(h.player("live"))
    run_minutes(h, 1, start=3)
    S = h.NR.server.store
    h.T.now = h.T.now + 31 * 86400000
    assert S.prune(h.T.now, 30) == 1
    assert S.records["old"] is None and S.records["live"] is not None
    assert h.T.files[ROOT + OLDP + "a.json"] == ""                # emptied, not deleted: no Lua delete (J2)
    assert S.file.load("old") is None
    assert '"old":' not in index_text(h)
    assert S.prune(h.T.now, 0) == 0


def test_the_hourly_prune_runs_from_its_queue_slot():
    h = boot()
    h.online(h.player("old"), h.player("live"))
    run_minutes(h, 2)
    h.online(h.player("live"))
    run_minutes(h, 1, start=3)
    h.T.now = h.T.now + 31 * 86400000
    run_minutes(h, 2, start=4)                       # the minute queues the prune; the next minute's drain runs it
    assert h.NR.server.store.file.stats.pruned == 1 and h.NR.server.store.records["old"] is None


def test_a_crash_mid_index_write_keeps_the_previous_index_and_the_prune_clock():
    h = boot()
    h.online(h.player("old"), h.player("live"))
    run_minutes(h, 2)
    h.online(h.player("live"))
    run_minutes(h, 5, start=3)                       # old's departure, then the debounced index write holding it
    F = h.NR.server.store.file
    before = files_of(h)
    top = newest(before, ROOT + "index_")
    other = ROOT + ("index_a.json" if top.endswith("b.json") else "index_b.json")
    h.T.crashOn = other
    assert not F.writeIndex()                        # the host dies mid-index-write
    assert h.T.files[other] == "" and h.T.files[top] == before[top]
    h.T.crashOn = None
    h2 = boot(files=files_of(h))                     # a restart: the stamps survive in the other index file
    h2.T.now = h.T.now + 31 * 86400000
    assert h2.NR.server.store.prune(h2.T.now, 30) == 2           # old and live, both offline after the restart
    assert h2.NR.server.store.file.load("old") is None and h2.NR.server.store.file.load("live") is None


def test_a_save_is_written_at_most_once_a_real_minute():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 1)
    w0 = h.NR.server.store.file.stats.writes
    for m in range(2, 6):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 1000                     # one real second a game minute
        h.minute(); h.tick(25)
    assert h.NR.server.store.file.stats.writes == w0


def test_a_returning_player_after_a_prune_gets_a_fresh_record():
    h = boot()
    h.online(h.player("bob"))
    run_minutes(h, 2)
    h.online()
    run_minutes(h, 1, start=3)
    h.T.now = h.T.now + 31 * 86400000
    h.NR.server.store.prune(h.T.now, 30)
    h.online(h.player("bob"))
    run_minutes(h, 1, start=5)
    assert h.record("bob").firstSeen == 100.0 + 5 / 60 and h.record("bob").resets == 0


def test_the_reader_is_always_called_with_create_false():
    h = boot(old_store=OLD)
    h.online(h.player("admin"))
    run_minutes(h, 2)
    flags = lst(h.T.readerCreate)
    assert flags and all(f is False for f in flags)


def test_a_server_name_holding_dot_dot_still_writes():
    h = boot(env='\nNR_T.serverName = "../up"\n')
    h.online(h.player("admin"))
    run_minutes(h, 2)
    F = h.NR.server.store.file
    assert F.root == "NutritionRevamp/___up/"
    assert F.stats.writes >= 1 and F.stats.writeFailures == 0


def test_a_nil_writer_is_counted_every_time_and_logged_once():
    h = boot(env="\nNR_T.nilWriter = true\n")
    h.online(h.player("admin"))
    run_minutes(h, 3)
    F = h.NR.server.store.file
    assert F.stats.writes == 0 and F.stats.writeFailures >= 3
    assert len([p for p in h.printed() if "getFileWriter answered nil" in p]) == 1


def test_an_unreadable_slot_is_a_read_failure_and_never_raises():
    deep = "[" * 30000 + "]" * 30000                # deep nesting overflows the decoder's stack
    files = {ROOT + ADMIN + "a.json": deep, ROOT + ADMIN + "b.json": "5"}
    h = boot(files=files)
    F = h.NR.server.store.file
    assert F.load("admin") is None
    assert F.stats.readFailures == 2


def test_an_exact_formatter_round_trips_the_record_exactly():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 3)
    S = h.NR.server.store
    S.file.fmt = h.rt.eval('function(x) return string.format("%.17g", x) end')
    assert S.file.save("admin", S.records["admin"])
    want = py(h.K.store.inputsOnly(S.records["admin"]))
    h2 = boot(files=files_of(h))
    raw = h2.NR.server.store.file.load("admin")
    assert py(h2.K.store.inputsOnly(raw)) == want


def test_the_keep_is_read_from_the_sandbox_option():
    h = boot(env="\nSandboxVars = { NR = { RecordKeepDays = 7 } }\n")
    assert h.NR.server.options.recordKeepDays == 7
    h.G.SandboxVars.NR.RecordKeepDays = 5000                      # out of range reads the default
    h.NR.server.readOptions("poll")
    assert h.NR.server.options.recordKeepDays == 30


def test_the_boot_prune_reads_the_option():
    h = boot()
    h.online(h.player("old"))
    run_minutes(h, 2)
    h.online()
    run_minutes(h, 5, start=3)                       # the departure, then the debounced index write
    saved = files_of(h)
    h2 = boot(files=saved, env="\nSandboxVars = { NR = { RecordKeepDays = 1 } }\nNR_T.now = %d\n" % (h.T.now + 2 * 86400000))
    assert h2.NR.server.store.file.stats.pruned == 1 and h2.NR.server.store.file.load("old") is None


# --- Task 11 fix 1: every guard pinned, and the hazards closed -----------------------------------------------------

def slot_doc(gen, resets, **over):
    """A slot file's text: { gen, rec, done } on one line, the record marked by its resets count; a None drops a key."""
    d = {"gen": gen, "done": True, "rec": {"v": 3, "username": "admin", "firstSeen": 50, "lastSeen": 60,
                                           "resets": resets, "dead": False}}
    d.update(over)
    return json.dumps({k: v for k, v in d.items() if v is not None}, separators=(",", ":"))


def index_doc(gen, players):
    return json.dumps({"v": 1, "gen": gen, "players": players, "done": True}, separators=(",", ":"))


def opened_with(h, prefix, n=0):
    return [p for p in lst(h.T.opened)[n:] if p.startswith(prefix)]


def until_saved(h, name, n=5, start=1):
    """Minutes until the player's slot is first written (the boot's save phase may hold the first minute)."""
    for m in range(start, start + n):
        run_minutes(h, 1, start=m)
        if opened_with(h, ROOT + "p_" + h.K.store.hexName(name) + "_"):
            return
    raise AssertionError("no save of " + name)


def test_a_restart_over_a_newer_a_file_writes_b_first_for_the_slots_and_the_index():
    files = {ROOT + ADMIN + "a.json": slot_doc(3, 4), ROOT + ADMIN + "b.json": slot_doc(2, 1),
             ROOT + "index_a.json": index_doc(3, {"admin": 990}), ROOT + "index_b.json": index_doc(2, {"admin": 900})}
    h = boot(files=files)
    assert opened_with(h, ROOT + "index_")[:1] == [ROOT + "index_b.json"]     # the boot prune's index write
    h.online(h.player("admin"))
    until_saved(h, "admin")
    assert h.record("admin").resets == 4                                        # the newest copy was loaded
    assert opened_with(h, ROOT + ADMIN)[:1] == [ROOT + ADMIN + "b.json"]


def test_a_failed_index_write_never_moves_the_index_onto_its_newest_file():
    h = boot()
    F = h.NR.server.store.file
    assert F.writeIndex()
    top = ROOT + "index_" + F.indexAt + ".json"
    other = ROOT + ("index_a.json" if top.endswith("b.json") else "index_b.json")
    at = F.indexAt
    h.T.crashOn = other
    assert not F.writeIndex()
    assert F.indexAt == at                                                      # a failed write moves nothing
    h.T.crashOn = None
    n = len(h.T.opened)
    assert F.writeIndex()
    assert opened_with(h, ROOT + "index_", n) == [other]
    assert F.stats.repaired == 0                                                # no repair stood in for the rule


def test_a_slot_missing_done_gen_or_its_body_is_a_read_failure_and_the_other_wins():
    for bad in (slot_doc(2, 9, done=None), slot_doc(None, 9), slot_doc(2, 9, rec=5)):
        h = boot(files={ROOT + ADMIN + "a.json": bad, ROOT + ADMIN + "b.json": slot_doc(1, 3)})
        F = h.NR.server.store.file
        raw = F.load("admin")                                                   # never raises
        assert raw is not None and raw.resets == 3, bad
        assert F.at["admin"] == "b" and F.gen["admin"] == 1 and F.stats.readFailures == 1, bad


OLD2 = ("{ olduser = { v = 2, username = 'olduser', firstSeen = 50.0, lastSeen = 60.0, resets = 2, dead = false },"
        "  ok = { v = 2, username = 'ok', firstSeen = 51.0, lastSeen = 61.0, resets = 1, dead = false } }")


def test_a_migration_whose_writer_is_nil_keeps_the_global_table():
    h = boot(old_store=OLD2, env="\nNR_T.nilWriter = true\n")
    assert removed(h) == []
    assert h.NR.server.store.file.stats.migrated == 0
    assert any("did not read back" in p for p in h.printed())


def test_a_migration_whose_write_never_lands_keeps_the_global_table_and_counts_only_the_good():
    h = boot(old_store=OLD2, env='\nNR_T.swallow = "%s"\n' % (ROOT + OLDUSER))
    assert removed(h) == []
    assert h.NR.server.store.file.stats.migrated == 1                          # ok, never olduser
    assert any("1 record(s) did not read back" in p for p in h.printed())


def test_the_save_opens_the_file_that_does_not_hold_the_newest_copy_whatever_its_gen():
    h = boot(files={ROOT + ADMIN + "a.json": slot_doc(2, 4)})                 # an even gen, by hand, in a
    F = h.NR.server.store.file
    n = len(h.T.opened)
    assert F.save("admin", h.rt.eval("{ v = 3, username = 'admin', resets = 4 }"))
    assert opened_with(h, ROOT + ADMIN, n) == [ROOT + ADMIN + "b.json"]


def test_a_save_with_no_gen_in_memory_reads_the_files_first_and_writes_max_plus_one():
    h = boot(files={ROOT + ADMIN + "a.json": slot_doc(5, 4), ROOT + ADMIN + "b.json": slot_doc(4, 3)})
    S = h.NR.server.store
    S.attach()["admin"] = h.rt.eval("{ v = 3, username = 'admin', resets = 4 }")   # in memory, never loaded
    assert S.file.gen["admin"] is None
    assert S.file.save("admin", S.records["admin"])
    assert gen_of(h.T.files[ROOT + ADMIN + "b.json"]) == 6
    assert gen_of(h.T.files[ROOT + ADMIN + "a.json"]) == 5


def test_two_swallowed_saves_never_cost_the_newest_copy():
    h = boot()
    h.online(h.player("admin"))
    until_saved(h, "admin")
    F = h.NR.server.store.file
    r = h.record("admin")
    assert F.save("admin", r)
    good = files_of(h)
    top = newest(good, ROOT + ADMIN)
    g = gen_of(good[top])
    h.T.swallow = ROOT + ADMIN
    F.save("admin", r)
    F.save("admin", r)                                                          # both land torn
    assert h.T.files[top] == good[top]                                          # the newest copy never opened
    assert F.stats.repaired >= 1
    crashed = boot(files=files_of(h))                                           # a crash now: the newest survives
    assert crashed.NR.server.store.file.load("admin") is not None
    assert crashed.NR.server.store.file.gen["admin"] == g
    h.T.swallow = None
    assert F.save("admin", r)
    h2 = boot(files=files_of(h))
    h2.online(h2.player("admin"))
    run_minutes(h2, 1, start=10)
    assert h2.NR.server.store.stats.created == 0 and h2.NR.server.store.file.gen["admin"] > g
    assert len([p for p in h.printed() if "did not read back as written" in p]) == 1   # once per player


def test_two_swallowed_index_writes_never_cost_the_newest_index():
    h = boot()
    F = h.NR.server.store.file
    F.index["bob"] = 999
    assert F.writeIndex()
    good = index_text(h)
    top = newest(files_of(h), ROOT + "index_")
    h.T.swallow = ROOT + "index_"
    F.writeIndex()
    F.writeIndex()
    assert h.T.files[top] == good
    h.T.swallow = None
    h2 = boot(files=files_of(h))
    assert h2.NR.server.store.file.index["bob"] == 999


def test_ten_departures_inside_one_minute_write_the_index_once():
    names = ["u%d" % i for i in range(10)]
    h = boot()
    h.online(*[h.player(n) for n in names])
    run_minutes(h, 7)                                                           # every first save indexed
    h.online()
    n = len(h.T.opened)
    run_minutes(h, 8, start=8)                                                  # all ten depart in minute 8
    assert len(opened_with(h, ROOT + "index_", n)) == 1
    stamps = json.loads(index_text(h))["players"]
    assert all(stamps[u] == h.NR.server.store.file.index[u] for u in names)    # the departures' own stamps
    assert len(opened_with(h, ROOT + "p_", n)) >= 10                            # each departure wrote its slot


def test_a_first_time_player_reaches_the_index_without_a_departure():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 7)                                                           # past the index gap; never departs
    h2 = boot(files=files_of(h))                                                # the host is killed
    assert h2.NR.server.store.file.index["admin"] is not None


def test_a_failed_first_read_never_resets_the_record():
    h = boot()
    h.online(h.player("admin"))
    until_saved(h, "admin")
    r = h.record("admin")
    r.resets = 6
    assert h.NR.server.store.file.save("admin", r)
    h2 = boot(files=files_of(h))
    h2.T.readerNil = 2                                                          # both slots locked at first sight
    h2.online(h2.player("admin"))
    run_minutes(h2, 4, start=10)
    assert h2.NR.server.store.stats.created == 1                                # the failed read made a fresh one
    assert h2.record("admin").resets == 6                                       # the file's record came back
    assert any("admin recovered from file after a failed first read" in p for p in h2.printed())
    h3 = boot(files=files_of(h2))
    assert h3.NR.server.store.file.load("admin").resets == 6


def test_two_players_first_saves_after_a_boot_fall_at_least_20_s_apart():
    h = boot()
    h.online(h.player("admin"), h.player("bob"))
    first = {}
    for m in range(1, 150):
        h.T.age = 100.0 + m / 60
        h.T.now = h.T.now + 1000                                                # one real second a game minute
        h.minute(); h.tick(25)
        for u in ("admin", "bob"):
            if u not in first and opened_with(h, ROOT + "p_" + h.K.store.hexName(u) + "_"):
                first[u] = h.T.now
    assert set(first) == {"admin", "bob"}
    assert abs(first["admin"] - first["bob"]) >= 20000


def test_a_dirty_index_is_written_at_most_once_every_five_real_minutes():
    names = ["u%d" % i for i in range(12)]
    h = boot()
    h.online(*[h.player(n) for n in names])
    run_minutes(h, 7)                                                           # every first save indexed
    n = len(h.T.opened)
    for k in range(len(names)):                                                 # one departure a real minute
        h.online(*[h.player(x) for x in names[k + 1:]])
        run_minutes(h, 1, start=8 + k)
    assert 1 <= len(opened_with(h, ROOT + "index_", n)) <= 3                    # twelve dirty minutes, 732 s


def test_a_reset_after_a_failed_first_read_is_saved_not_recovered_over():
    h = boot()
    h.online(h.player("admin"))
    until_saved(h, "admin")
    h.record("admin").resets = 6
    assert h.NR.server.store.file.save("admin", h.record("admin"))
    h2 = boot(files=files_of(h))
    h2.T.readerNil = 2
    S = h2.NR.server.store
    S.get("admin", 100.0)                                                       # fresh: both slots read nil
    r = S.reset("admin", 101.0)                                                 # then a new character
    assert S.file.save("admin", r)
    assert h2.NR.server.store.file.load("admin").firstSeen == 101.0


def test_a_load_after_a_swallowed_save_never_aims_the_repair_at_the_newest_copy():
    h = boot()
    h.online(h.player("admin"))
    until_saved(h, "admin")
    F = h.NR.server.store.file
    r = h.record("admin")
    assert F.save("admin", r)
    top = newest(files_of(h), ROOT + ADMIN)
    good = h.T.files[top]
    h.T.swallow = ROOT + ADMIN
    F.save("admin", r)                                                          # torn in the other file
    h.T.swallow = None
    assert F.load("admin") is not None                                          # the load re-aims at the newest
    n = len(h.T.opened)
    assert F.save("admin", r)
    assert top not in opened_with(h, ROOT + ADMIN, n) and h.T.files[top] == good


def test_an_index_read_after_a_swallowed_write_never_aims_the_repair_at_the_newest_index():
    h = boot()
    F = h.NR.server.store.file
    assert F.writeIndex()
    top = newest(files_of(h), ROOT + "index_")
    h.T.swallow = ROOT + "index_"
    F.writeIndex()
    h.T.swallow = None
    F.readIndex()
    n = len(h.T.opened)
    assert F.writeIndex()
    assert top not in opened_with(h, ROOT + "index_", n)


def test_a_clean_index_is_not_written_again():
    h = boot()
    h.online(h.player("admin"))
    run_minutes(h, 7)                                                           # the first save's index write
    n = len(h.T.opened)
    run_minutes(h, 15, start=8)                                                 # saves move stamps, nothing dirties
    assert opened_with(h, ROOT + "index_", n) == []
