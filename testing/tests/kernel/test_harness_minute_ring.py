"""The harness's lua.read (H1) and minute.ring (H2), offline (Plan 11f Task 1): PZTestKit_Core.lua's Plan 11f block
and PZTestKit_Server.lua's Plan 11f block, each from its marker line to the end of its file, loaded on the shared
server host beside the real mod with a stub TK (side, register, commands, call, now, result). It pins what the live
smoke test (Plan 11f Task 3's first session) cannot cheaply show: a numeric segment reaches a ring slot, a bracketed
segment reaches a key holding dots, every absence is named, `record:<user>` never creates a record, a ring row carries
the clock, dtM, the six stats and the record paths, the bound overwrites and counts, a read pages and clamps, and the
bench target leaves the rings untouched. The harness is never a kernel file, so the coverage gate is untouched."""
import os

from .server_host import Host, REPO

LUA = os.path.join(REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua")
CORE = os.path.join(LUA, "shared", "PZTestKit_Core.lua")
SERVER = os.path.join(LUA, "server", "PZTestKit_Server.lua")

ENV = r"""
NR_T.now = 5000000
getTimestampMs = function() NR_T.now = NR_T.now + 1; return NR_T.now end
CharacterStat = { HUNGER = "E_HUNGER", THIRST = "E_THIRST", FATIGUE = "E_FATIGUE", BOREDOM = "E_BOREDOM",
                  UNHAPPINESS = "E_UNHAPPINESS", NICOTINE_WITHDRAWAL = "E_NICOTINE_WITHDRAWAL" }
"""

STUB_TK = r"""
TK = { side = "server", commands = {}, results = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.now = function() return getTimestampMs() end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
TK.result = function(name, tbl) TK.results[name] = tbl; return true end
"""

# the clock with an hour and minute (the host's own getGameTime has neither), and a player whose stats answer
CLOCK = r"""
getGameTime = function()
    return { getWorldAgeHours = function(s) return NR_T.age end,
             getTimeOfDay = function(s) return math.fmod(NR_T.age, 24) end,
             getHour = function(s) return math.floor(math.fmod(NR_T.age, 24)) end,
             getMinutes = function(s) return math.floor(math.fmod(NR_T.age * 60, 60) + 0.5) end }
end
"""

STATS = r"""
function(p)
    local vals = { E_HUNGER = 0.25, E_THIRST = 0.1, E_FATIGUE = 0.3, E_BOREDOM = 0.0, E_UNHAPPINESS = 12.5,
                   E_NICOTINE_WITHDRAWAL = 0.4 }
    p.statVals = vals
    p.getStats = function(s) return { get = function(st, enum) return vals[enum] end } end
end
"""


def section(path, marker):
    with open(path, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    return src[src.index(marker):]


def load(h, src, name):
    h.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


def boot():
    h = Host(extra_env=ENV)
    p = h.player("admin")
    h.rt.eval(STATS)(p)
    h.p = p
    h.online(p)
    h.minute()
    h.tick(10)                                                     # the record exists
    assert h.record("admin") is not None
    h.rt.execute(STUB_TK)
    h.rt.execute(CLOCK)
    load(h, section(CORE, "-- ==== Plan 11f Task 1 additions (H1)"), "@PZTestKit_Core.lua")
    load(h, section(SERVER, "-- ==== Plan 11f Task 1 additions (H2)"), "@PZTestKit_Server.lua")
    h.TK = h.G.TK
    return h


def cmd(h, name, *args):
    return h.TK.commands[name](h.rt.table(*args))


def d(t):
    return {k: v for k, v in t.items()} if t is not None else None


# ---- H1 lua.read -----------------------------------------------------------------------------------------------

def test_lua_read_reaches_a_ring_slot_by_number_and_a_dotted_key_by_brackets():
    h = boot()
    r = h.record("admin")
    r.body.trail.kcal[3] = 123.5
    r.monotony = h.rt.eval("{ t = { ['Base.Bread'] = { n = 2, last = 101.25 } } }")
    out = cmd(h, "lua.read", "record:admin", "body.trail.kcal.3", "monotony.t.[Base.Bread].n",
              "monotony.t.[Base.Bread].last", "body.energyState", "body.trail.kcal")
    assert out.ok is True and out.side == "server" and out.root == "record:admin" and out.n == 5
    v = d(out["values"])
    assert v["body.trail.kcal.3"] == 123.5
    assert v["monotony.t.[Base.Bread].n"] == 2 and v["monotony.t.[Base.Bread].last"] == 101.25
    assert v["body.energyState"] == r.body.energyState
    assert d(out["tables"]) == {"body.trail.kcal": 25}                 # a table answers its key count
    assert d(out["missing"]) == {} and d(out["types"]) == {}


def test_lua_read_names_every_absence_and_never_takes_truthiness_for_presence():
    h = boot()
    r = h.record("admin")
    r.satiety.flag = False
    out = cmd(h, "lua.read", "record:admin", "satiety.nope", "nope.deeper", "satiety.L.x", "satiety.flag",
              "a..b", "[unclosed", "satiety.")
    m = d(out["missing"])
    assert m["satiety.nope"] == "nil"                              # the parent exists, the key does not
    assert m["nope.deeper"] == "nil at nope"                       # a parent is absent
    assert m["satiety.L.x"].endswith(" at x")                      # a scalar cannot be entered
    assert m["a..b"].startswith("bad path: empty segment")
    assert m["[unclosed"].startswith("bad path: unclosed [")
    assert m["satiety."].startswith("bad path: trailing .")
    assert d(out["values"]) == {"satiety.flag": False}                # false is a value, not an absence


def test_lua_read_record_root_never_creates_a_record_and_other_roots_walk_the_globals():
    h = boot()
    out = cmd(h, "lua.read", "record:ghost", "satiety.L")
    assert out.ok is False and out.error == "no record"
    assert h.record("ghost") is None                               # S.get was never called
    g = cmd(h, "lua.read", "NutritionRevamp.server.minute.stats", "runs", "failures")
    assert g.ok is True and d(g["values"])["runs"] == h.NR.server.minute.stats.runs
    mix = cmd(h, "lua.read", "record:admin", "body.met", "_G.NutritionRevamp.server.minute.stats.runs")
    assert d(mix["values"])["_G.NutritionRevamp.server.minute.stats.runs"] == h.NR.server.minute.stats.runs
    assert cmd(h, "lua.read", "_G", "TK.READ_MAX")["values"]["TK.READ_MAX"] == 64
    bad = cmd(h, "lua.read", "No.Such.Root", "x")
    assert bad.ok is False and bad.error == "root nil at No"
    assert isinstance(cmd(h, "lua.read", "record:admin"), str)     # no path: the usage string


def test_lua_read_a_numeric_string_key_wins_over_the_number_key():
    h = boot()
    t = h.rt.eval("{ ['3'] = 'string key', [3] = 'number key', [4] = 'only number' }")
    h.G.NR_T.mixed = t
    out = cmd(h, "lua.read", "NR_T.mixed", "3", "4", "[4]")
    assert d(out["values"]) == {"3": "string key", "4": "only number"}
    assert d(out["missing"]) == {"[4]": "nil"}                        # a bracketed segment is a string key only


# ---- H2 minute.ring --------------------------------------------------------------------------------------------

def test_minute_ring_rows_carry_the_clock_dtM_the_six_stats_and_the_record_paths():
    h = boot()
    s = cmd(h, "minute.ring", "admin", "start", "body.energyState", "satiety.L", "body.trail.kcal.1", "no.such")
    assert s.ok is True and s.armed is True and s.cap == 4320 and s.online is True
    assert d(s.probe["missing"]) == {"no.such": "nil at no"}         # the start's probe names what does not resolve
    for _ in range(3):
        h.T.age = h.T.age + 1 / 60
        h.minute()
        h.tick(5)
    h.T.age = h.T.age + 5 / 60                                      # a fast clock's larger step
    h.minute()
    rd = cmd(h, "minute.ring", "admin", "read")
    assert rd.ok is True and rd.rows == 4 and rd["from"] == 1
    assert rd.next == 5 and rd.more is False and rd.recorded == 4 and rd.overwritten == 0 and rd.errors == 0
    assert rd.result == "minute-ring-admin-1"
    doc = h.TK.results[rd.result]
    rows = [doc.rows_list[i] for i in range(1, 5)]
    assert [r.s for r in rows] == [1, 2, 3, 4]
    assert rows[0].dtM is None                                     # no previous row
    assert abs(rows[1].dtM - 1.0) < 1e-6 and abs(rows[3].dtM - 5.0) < 1e-6
    r0 = rows[0]
    assert r0.on is True and r0.HUNGER == 0.25 and r0.THIRST == 0.1 and r0.FATIGUE == 0.3
    assert r0.BOREDOM == 0.0 and r0.UNHAPPINESS == 12.5 and r0.NICOTINE_WITHDRAWAL == 0.4
    assert r0.hour is not None and r0.min is not None and r0.age is not None
    assert r0["body.energyState"] is not None and r0["satiety.L"] is not None
    assert r0["body.trail.kcal.1"] is not None
    assert r0["no.such"] is None                                   # absent from the row
    assert r0.norec is None


def test_minute_ring_samples_inside_the_event_before_the_queue_drains():
    h = boot()
    cmd(h, "minute.ring", "admin", "start", "_G.NutritionRevamp.server.minute.stats.runs")
    runs0 = h.NR.server.minute.stats.runs
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # the row is taken here, before this minute's run
    h.tick(10)
    assert h.NR.server.minute.stats.runs == runs0 + 1
    doc = h.TK.results[cmd(h, "minute.ring", "admin", "read").result]
    assert doc.rows_list[1]["_G.NutritionRevamp.server.minute.stats.runs"] == runs0


def test_minute_ring_bound_overwrites_and_counts_and_a_read_pages_and_clamps():
    h = boot()
    h.TK.MR.CAP = 5
    h.TK.MR.PAGE = 2
    cmd(h, "minute.ring", "admin", "start", "body.met")
    for _ in range(8):
        h.T.age = h.T.age + 1 / 60
        h.minute()
    rd = cmd(h, "minute.ring", "admin", "read", "1")
    assert rd.recorded == 8 and rd.overwritten == 3 and rd.oldest == 4 and rd.newest == 8
    assert rd["from"] == 4 and rd.skipped == 3 and rd.rows == 2 and rd.next == 6 and rd.more is True
    doc = h.TK.results[rd.result]
    assert [doc.rows_list[i].s for i in (1, 2)] == [4, 5]
    rd2 = cmd(h, "minute.ring", "admin", "read", str(rd.next))
    assert rd2.rows == 2 and rd2.next == 8 and rd2.more is True
    rd3 = cmd(h, "minute.ring", "admin", "read", "8")
    assert rd3.rows == 1 and rd3.next == 9 and rd3.more is False
    rd4 = cmd(h, "minute.ring", "admin", "read", "9")
    assert rd4.rows == 0 and rd4.more is False
    st = cmd(h, "minute.ring", "admin", "stop")
    assert st.stopped is True and st.recorded == 8 and st.overwritten == 3
    assert cmd(h, "minute.ring", "admin", "read").ok is False


def test_minute_ring_an_offline_user_and_a_missing_record_are_rows_not_raises():
    h = boot()
    cmd(h, "minute.ring", "nobody", "start", "satiety.L")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    rd = cmd(h, "minute.ring", "nobody", "read")
    row = h.TK.results[rd.result].rows_list[1]
    assert row.on is False and row.norec is True and row.HUNGER is None and row["satiety.L"] is None
    assert rd.errors == 0


def test_minute_ring_refuses_a_bad_path_and_a_bad_verb():
    h = boot()
    bad = cmd(h, "minute.ring", "admin", "start", "a..b")
    assert bad.ok is False and bad.error.startswith("bad path a..b")
    assert h.TK.MR.rings["admin"] is None
    assert isinstance(cmd(h, "minute.ring", "admin", "wobble"), str)
    cmd(h, "minute.ring", "admin", "start")
    assert isinstance(cmd(h, "minute.ring", "admin", "read", "0"), str)


def test_bench_row_samples_every_watched_user_and_leaves_the_rings_untouched():
    h = boot()
    paths = ["body.energyState", "body.met", "satiety.L", "body.trail.kcal.1", "body.trail.ee.1",
             "body.trail.ex.1", "body.trail.p.1", "body.trail.carb.1", "body.trail.lip.1", "stomachFill"]
    cmd(h, "minute.ring", "admin", "start", *paths)
    R = h.TK.MR.rings["admin"]
    scratch = h.TK.MR.benchRow()
    assert len(scratch) == 1 and scratch[1]["body.met"] is not None
    assert R.count == 0
    # an offline reading of the per-row cost on PUC Lua 5.1 (lupa), not Kahlua: printed, never asserted
    n = 20000
    sec = h.rt.eval("function(fn, n) local t0 = os.clock(); for _i = 1, n do fn() end; return os.clock() - t0 end")(
        h.TK.MR.benchRow, n)
    us = sec * 1e6 / n
    print("minute.ring per-row cost offline (lupa, 10 paths): %.2f us" % us)


def test_minute_ring_a_raise_in_one_ring_drops_only_that_ring_row_and_the_gap_shows_in_ev():
    h = boot()
    p2 = h.player("second")
    h.rt.eval(STATS)(p2)
    h.online(h.p, p2)
    cmd(h, "minute.ring", "admin", "start", "body.met")
    cmd(h, "minute.ring", "second", "start", "body.met")
    ok = h.p.getStats
    h.p.getStats = h.rt.eval("function(s) return { get = function() error('boom') end } end")
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # admin raises, second lands
    h.p.getStats = ok
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # both land
    a = cmd(h, "minute.ring", "admin", "read")
    b = cmd(h, "minute.ring", "second", "read")
    assert a.errors == 1 and a.lastError is not None and "boom" in a.lastError
    assert b.errors == 0 and b.lastError is None
    assert a.rows == 1 and b.rows == 2
    arow = h.TK.results[a.result].rows_list[1]
    brows = [h.TK.results[b.result].rows_list[i] for i in (1, 2)]
    assert [r.ev for r in brows] == [1, 2] and arow.ev == 2          # the gap in ev: admin missed event 1
    assert arow.dtM is None                                          # lastAge never advanced: first row of the ring
    assert brows[0].drained == h.NR.server.players.drained
    st = cmd(h, "minute.ring", "admin", "stop")
    assert st.errors == 1 and st.lastError is not None


# ---- C-17: the raw engine metabolic rate and the server's exercise flag on every row (Plan 11f) ------------------

RATE = r"""
function(p, mode)
    p.getBodyDamage = function(s)
        return { getThermoregulator = function(b)
            return { getMetabolicRate = function(t)
                if mode == "raise" then error("no rate") end
                return 4.75
            end }
        end }
    end
    p.getFitness = function(s)
        return { getCurrentExe = function(f) if mode == "exe" then return {} end return nil end }
    end
end
"""


def test_minute_ring_rows_carry_the_raw_engine_rate_and_the_exercise_flag():
    h = boot()
    h.rt.eval(RATE)(h.p, "exe")
    cmd(h, "minute.ring", "admin", "start")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    row = h.TK.results[cmd(h, "minute.ring", "admin", "read").result].rows_list[1]
    assert row.rate == 4.75 and row.exe is True
    h.rt.eval(RATE)(h.p, "idle")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    row2 = h.TK.results[cmd(h, "minute.ring", "admin", "read").result].rows_list[2]
    assert row2.rate == 4.75 and row2.exe is False                  # no current exercise: false, not absent


def test_minute_ring_an_unreachable_or_raising_rate_leaves_the_field_absent_and_the_row_lands():
    h = boot()
    cmd(h, "minute.ring", "admin", "start")
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # the stand-in player has no thermoregulator
    h.rt.eval(RATE)(h.p, "raise")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    rd = cmd(h, "minute.ring", "admin", "read")
    rows = h.TK.results[rd.result].rows_list
    assert rd.rows == 2 and rd.errors == 0
    assert rows[1].rate is None and rows[1].exe is None and rows[1].HUNGER == 0.25
    assert rows[2].rate is None and rows[2].exe is False and rows[2].HUNGER == 0.25


# ---- C-17 fix 1: the movement flag on every row ----------------------------------------------------------------------

def test_minute_ring_rows_carry_the_movement_flag_as_the_mod_reads_it():
    h = boot()
    cmd(h, "minute.ring", "admin", "start")
    h.p.isPlayerMoving = lambda s: True
    h.T.age = h.T.age + 1 / 60
    h.minute()
    h.p.isPlayerMoving = lambda s: False
    h.T.age = h.T.age + 1 / 60
    h.minute()
    h.p.isPlayerMoving = lambda s: "yes"                          # only true counts, as NR.flag reads it
    h.T.age = h.T.age + 1 / 60
    h.minute()
    rows = h.TK.results[cmd(h, "minute.ring", "admin", "read").result].rows_list
    assert rows[1].moving is True and rows[2].moving is False and rows[3].moving is False
    assert rows[1].HUNGER == 0.25                                  # the earlier fields are untouched


def test_minute_ring_an_unreachable_or_raising_movement_leaves_the_field_absent_and_the_row_lands():
    h = boot()
    cmd(h, "minute.ring", "admin", "start")
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # the stand-in player has no isPlayerMoving
    def boom(s):
        raise RuntimeError("no movement")
    h.p.isPlayerMoving = boom
    h.T.age = h.T.age + 1 / 60
    h.minute()
    rd = cmd(h, "minute.ring", "admin", "read")
    rows = h.TK.results[rd.result].rows_list
    assert rd.rows == 2 and rd.errors == 0
    assert rows[1].moving is None and rows[2].moving is None and rows[2].HUNGER == 0.25


# ---- Plan 16 Task 8: the record's cold multiplier on every row -------------------------------------------------------

def test_minute_ring_rows_carry_the_records_cold_multiplier():
    h = boot()
    cmd(h, "minute.ring", "admin", "start", "body.coldMult")
    rec = h.record("admin")
    rec.body.coldMult = 2.5                                        # stamped by the mod; the row reads the record as held
    h.T.age = h.T.age + 1 / 60
    h.minute()
    row = h.TK.results[cmd(h, "minute.ring", "admin", "read").result].rows_list[1]
    assert row.cold == 2.5 and row["body.coldMult"] == 2.5          # the fixed field equals the path read
    assert row.HUNGER == 0.25 and row.on is True                    # the earlier fields are untouched


def test_minute_ring_a_missing_or_non_number_cold_leaves_the_field_absent_and_the_row_lands():
    h = boot()
    cmd(h, "minute.ring", "admin", "start")
    cmd(h, "minute.ring", "nobody", "start")
    h.record("admin").body.coldMult = "warm"
    h.T.age = h.T.age + 1 / 60
    h.minute()
    ra = cmd(h, "minute.ring", "admin", "read")
    rn = cmd(h, "minute.ring", "nobody", "read")
    row = h.TK.results[ra.result].rows_list[1]
    nob = h.TK.results[rn.result].rows_list[1]
    assert row.cold is None and row.HUNGER == 0.25 and ra.errors == 0
    assert nob.cold is None and nob.norec is True and rn.errors == 0
    assert h.TK.MR.sampleBaseCold is not None                       # installed once, over the movement wrap
    assert h.TK.MR.sampleBaseCold != h.TK.MR.sample


# ---- Plan 17 Task 4: the overall health and the dead flag on every row ------------------------------------------------

HEALTH = r"""
function(p, mode)
    if mode == "raise" then
        p.getBodyDamage = function(s) error("no body") end
        return
    end
    if mode == "text" then
        p.getBodyDamage = function(s) return { getOverallBodyHealth = function(b) return "full" end } end
        return
    end
    p.hp = mode
    p.getBodyDamage = function(s) return { getOverallBodyHealth = function(b) return s.hp end } end
end
"""


def test_minute_ring_rows_carry_the_overall_health_and_the_dead_flag():
    h = boot()
    h.rt.eval(HEALTH)(h.p, 61.25)
    cmd(h, "minute.ring", "admin", "start", "body.coldMult")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    h.rt.eval(HEALTH)(h.p, 0.0)
    h.p.deadFlag = True
    h.T.age = h.T.age + 1 / 60
    h.minute()
    rows = h.TK.results[cmd(h, "minute.ring", "admin", "read").result].rows_list
    assert rows[1].health == 61.25 and rows[1].dead is False        # alive: false, not absent
    assert rows[2].health == 0.0 and rows[2].dead is True
    assert rows[1].HUNGER == 0.25 and rows[1].cold is not None       # the earlier fields and wraps are untouched


def test_minute_ring_an_unreachable_raising_or_non_number_health_leaves_the_field_absent_and_the_row_lands():
    h = boot()
    cmd(h, "minute.ring", "admin", "start")
    cmd(h, "minute.ring", "nobody", "start")
    h.T.age = h.T.age + 1 / 60
    h.minute()                                                     # the stand-in player has no body damage
    h.rt.eval(HEALTH)(h.p, "raise")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    h.rt.eval(HEALTH)(h.p, "text")
    h.T.age = h.T.age + 1 / 60
    h.minute()
    ra = cmd(h, "minute.ring", "admin", "read")
    rn = cmd(h, "minute.ring", "nobody", "read")
    rows = h.TK.results[ra.result].rows_list
    nob = h.TK.results[rn.result].rows_list[1]
    assert ra.rows == 3 and ra.errors == 0
    assert all(rows[i].health is None and rows[i].HUNGER == 0.25 for i in (1, 2, 3))
    assert rows[1].dead is False                                   # isDead answers though the body does not
    assert nob.health is None and nob.dead is None and nob.norec is True and rn.errors == 0
    assert h.TK.MR.sampleBaseHealth is not None                    # installed once, over the cold wrap
    assert h.TK.MR.sampleBaseHealth != h.TK.MR.sample
