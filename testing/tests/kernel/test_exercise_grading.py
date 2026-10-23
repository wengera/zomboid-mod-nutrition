"""Plan 11h Task 2 (C-2, spec docs/superpowers/specs/2026-10-13-exercise-grading-design.md@program-record-v19): each Fitness exercise
billed at its own MET.

- NR_Server_Fitness.lua wraps ISFitnessAction.serverStart and serverStop once (never `new`): the wrapper calls the
  original, then records the action's exeDataType per username at the start and clears it at the stop.
- K.energy.EXERCISE_MET holds the 2024 Compendium MET per vanilla exercise type (S1895-S1903); the adapter bills it (K.energy.exerciseMet)
  while the exercise flag is set, and the flat Fitness class (6.0) with no recorded or no known type, which
  NR_Server_Metabolism counts (MET.stats.exeFallbacks).
- W.vigorous reads a set minute as resistance-vigorous from the flag, before any MET test (S1508, S1509, S1301).
- Rule 6: the per-minute path adds no Java call (a stub counts every call the minute makes).
"""
import os
import re

import lupa.lua51 as lua51
import pytest

from .test_metabolism_shape import MET, PLAYER, cfg, fresh, met_host, minute, player  # noqa: F401  (met_host is a fixture)
from . import test_writer_shape as WS

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
SHARED = os.path.join(LUA, "shared")
SERVER = os.path.join(LUA, "server")
ENERGY = os.path.join(SHARED, "NR_Kernel_Energy.lua")
FITNESS = os.path.join(SERVER, "NR_Server_Fitness.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")

# The table and its rows (the Task 2 amendments' minted rows, Task 1, cbca565c): type -> (MET, row, the rows not chosen).
TABLE = {
    "squats": (3.0, "S1898", ("S1899",)),
    "pushups": (3.8, "S1896", ("S1895",)),
    "situp": (3.8, "S1896", ("S1895", "S1897")),
    "burpees": (7.5, "S1895", ("S1903",)),
    "barbellcurl": (3.5, "S1902", ("S1900",)),
    "dumbbellpress": (3.5, "S1902", ("S1900",)),
    "bicepscurl": (3.5, "S1902", ("S1900",)),
}


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _code(path):
    return "\n".join(line.split("--")[0] for line in _src(path).splitlines())


# --- the kernel: the table, the fallback, the bill ----------------------------------------------------------------

def test_the_table_holds_the_seven_vanilla_types_at_their_rows(host):
    t = host.py(host.K.energy.EXERCISE_MET)
    assert t == {k: v[0] for k, v in TABLE.items()}
    from .conftest import dial_line
    lines = _src(ENERGY).splitlines()
    for key, (met, row, others) in TABLE.items():
        # Plan 19: the kernel line resolves the row; the value and its provenance sit on the registry row
        assert 'K.energy.EXERCISE_MET.%s = K.dials.get("energy.EXERCISE_MET.%s")' % (key, key) in lines, key
        line = dial_line("energy.EXERCISE_MET.%s" % key)
        assert line.startswith("D['energy.EXERCISE_MET.%s'] = { value = %s," % (key, met)), key
        label = line.split(" } -- ", 1)[1]
        assert row in label and all(o in label for o in others), key
        assert "game choice" in label, key
    for key in ("barbellcurl", "dumbbellpress", "bicepscurl"):
        assert "approximate" in dial_line("energy.EXERCISE_MET.%s" % key)


@pytest.mark.parametrize("exe,met,known", [(k, v[0], True) for k, v in TABLE.items()] + [
    (None, 6.0, False),            # no recorded type: a reconnect mid-set, another mod's serverStart, the wrapper absent
    ("yoga", 6.0, False),          # a modded exercise
    (7, 6.0, False),               # never a string key
    ("", 6.0, False),
])
def test_exercise_met_bills_the_type_else_the_flat_fitness_class(host, exe, met, known):
    assert host.K.energy.exerciseMet(exe) == (met, known)


def test_the_fallback_is_the_compendium_fitness_class(host):
    E = host.K.energy
    assert E.COMPENDIUM.Fitness == 6.0
    assert E.exerciseMet(None)[0] == E.COMPENDIUM.Fitness


def test_bill_class_names_the_class_only_on_a_flagged_minute(host):
    E = host.K.energy
    for cls, moving, falling in (("Default", False, True), ("HeavyWork", True, False), ("Walking5kmh", False, False)):
        assert E.billClass(cls, True, moving, falling) == "Fitness"
    assert E.billClass("UsingTools", False, False, False) == "UsingTools"
    assert E.billClass("UsingTools", False, False, True) == "Default"
    assert E.billClass("Sleeping", True, False, False) == "Sleeping"                 # asleep wins


def test_read_billed_returns_the_exercise_met_last_and_only_on_a_set_minute(mh):
    h = mh
    _fit(h, "burpees")
    p = player(h, rate=1.6, exe="flag", moving=False)
    got = list(MET(h).readBilled("admin", p))
    assert got[0] == "Fitness" and got[-1] == 7.5
    p = player(h, rate=3.1, exe=None, moving=False)
    got = list(MET(h).readBilled("admin", p))
    assert got[0] != "Fitness" and got[-1] is None


def test_activity_met_takes_the_exercise_met_over_the_class(host):
    E = host.K.energy
    assert E.activityMet("Fitness", False, 1, 0.0, 3.0) == 3.0
    assert E.activityMet("Fitness", True, 1, 30.0, 7.5) == 7.5        # no load floor on a set
    assert E.activityMet("Fitness", False, 1, 0.0, None) == 6.0       # the class's own bill
    assert E.activityMet("Fitness", False, 1, 0.0) == 6.0


def test_activity_met_returns_the_exercise_met_before_the_band_and_load_floors(host):
    E = host.K.energy
    assert E.BAND_MET[3] == 6.0
    assert E.activityMet("Fitness", False, 3, 0.0, 3.0) == 3.0         # the band for modifier 3 (6.0) never lifts a graded set


# --- the adapter: Metabolism bills the recorded type -------------------------------------------------------------

def _fit(h, exe_type):
    """The Fitness module's per-username record, as the wrapper leaves it: a stand-in typeOf over a plain table."""
    f = h.rt.eval("function(t) return { exeType = t, typeOf = function(u) return t[u] end } end")(h.rt.table())
    if exe_type is not None:
        f.exeType["admin"] = exe_type
    h.G.NutritionRevamp.server.fitness = f
    return f


@pytest.fixture
def mh(met_host):
    h = met_host
    saved = h.G.NutritionRevamp.server.fitness
    MET(h).prevRate = h.rt.table()
    MET(h).prevExe = h.rt.table()
    yield h
    h.G.NutritionRevamp.server.fitness = saved


@pytest.mark.parametrize("exe", sorted(TABLE))
def test_a_set_minute_bills_the_recorded_types_met(mh, exe):
    h = mh
    _fit(h, exe)
    p = player(h, rate=1.6, exe="flag", moving=False)
    record = fresh(h, p)
    f0 = MET(h).stats.exeFallbacks
    pipe = h.rt.table()
    minute(h, p, record, 100.0 + 1 / 60, pipe)
    body = record["body"]
    assert body["met"] == TABLE[exe][0]
    assert pipe["activityClass"] == "Fitness" and pipe["exercising"] is True
    assert MET(h).stats.exeFallbacks == f0
    assert body["epoc"] > 0


@pytest.mark.parametrize("exe", [None, "yoga"])
def test_a_set_minute_with_no_known_type_bills_six_and_counts(mh, exe):
    h = mh
    _fit(h, exe)
    p = player(h, rate=1.6, exe="flag", moving=False)
    record = fresh(h, p)                                   # the first minute is a set minute too: it counts
    f0 = MET(h).stats.exeFallbacks
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 6.0
    assert MET(h).stats.exeFallbacks == f0 + 1


def test_no_fitness_module_bills_six_and_counts(mh):
    h = mh
    h.G.NutritionRevamp.server.fitness = None
    p = player(h, rate=1.6, exe="flag", moving=False)
    record = fresh(h, p)
    f0 = MET(h).stats.exeFallbacks
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 6.0 and MET(h).stats.exeFallbacks == f0 + 1


def test_a_stale_type_never_bills_without_the_flag(mh):
    h = mh
    _fit(h, "burpees")
    p = player(h, rate=3.1, exe=None, moving=False)
    record = fresh(h, p)
    f0 = MET(h).stats.exeFallbacks
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["met"] == 3.8                    # Walking5kmh's Compendium bill, the rate's own class
    assert MET(h).stats.exeFallbacks == f0                 # not an exercise minute: nothing to fall back from


def test_the_exercise_kcal_and_the_pool_follow_the_billed_met(mh):
    h = mh
    out = {}
    for exe in ("squats", None, "burpees"):
        _fit(h, exe)
        MET(h).prevRate = h.rt.table()
        MET(h).prevExe = h.rt.table()
        p = player(h, rate=1.6, exe="flag", moving=False)
        record = fresh(h, p)
        body = record["body"]
        ex0 = body["exKcalDay"]
        minute(h, p, record, 100.0 + 1 / 60)
        out[exe] = body["exKcalDay"] - ex0
        w = body["fm"] + body["lm"]
        met = TABLE[exe][0] if exe else 6.0
        assert out[exe] == pytest.approx((met - 1.3) * w / 60, rel=1e-9)
    assert out["squats"] < out[None] < out["burpees"]


def test_the_training_sample_still_banks_the_engine_rate(mh):
    # two MET tables, never mixed: the sample banks the rate's ENGINE class, not the exercise's Compendium bill
    h = mh
    _fit(h, "burpees")
    p = player(h, rate=3.1, exe="flag", moving=False)
    record = fresh(h, p)
    body = record["body"]
    m0 = body["metMinDay"]
    minute(h, p, record, 100.0 + 1 / 60)
    w = body["fm"] + body["lm"]
    assert body["met"] == 7.5
    assert body["metMinDay"] - m0 == pytest.approx((3.1 - 1.5) * w / 80, rel=1e-9)


# --- Rule 6: no added per-minute Java call --------------------------------------------------------------------------

# Every member the minute calls on the player, or on anything a member returns, and every call of the clock global,
# counted through a proxy: a table member that is a function is wrapped to count and to proxy its first return.
COUNTING = r"""
function(p, counter)
    local function wrap(obj)
        if type(obj) ~= "table" then return obj end
        local proxy = {}
        setmetatable(proxy, { __index = function(t, k)
            local v = obj[k]
            if type(v) ~= "function" then return v end
            return function(self, ...)
                counter.n = counter.n + 1
                return wrap(v(obj, ...))
            end
        end })
        return proxy
    end
    local gt = getGameTime
    counter.restore = gt
    getGameTime = function()
        counter.n = counter.n + 1
        return wrap(gt())
    end
    return wrap(p)
end
"""

# The Java calls one flagged minute made at cbca565c (before this task), counted by this proxy on the same stand-in:
# 32 then, 31 since the hyperthermia moodle read, which fed only the drain coefficient, went with it (Plan 12 3a), 29
# since Metabolism's unused hour of day (getGameTime and getTimeOfDay) went (Plan 16 Task 4).
JAVA_CALLS_PER_SET_MINUTE = 29


def _count(h, exe_type):
    _fit(h, exe_type)
    MET(h).prevRate = h.rt.table()
    MET(h).prevExe = h.rt.table()
    raw = h.rt.eval(PLAYER)(cfg(h, rate=1.6, exe="flag", moving=False))
    record = fresh(h, raw)
    counter = h.rt.table()
    counter.n = 0
    p = h.rt.eval(COUNTING)(raw, counter)
    try:
        minute(h, p, record, 100.0 + 1 / 60)
    finally:
        h.G.getGameTime = counter.restore
    assert record["body"]["met"] == (TABLE[exe_type][0] if exe_type else 6.0)
    return counter.n


def test_a_set_minute_makes_no_added_java_call(mh):
    known = _count(mh, "burpees")
    unknown = _count(mh, None)
    assert known == unknown == JAVA_CALLS_PER_SET_MINUTE


def test_the_type_read_names_no_java():
    # the per-minute read is a Lua table lookup on the module the wrapper fills; no getter is named for it
    code = _code(os.path.join(SERVER, "NR_Server_Metabolism.lua"))

    def body(name):
        fn = code[code.index("function MET.%s(" % name):]
        return fn[:fn.index("\nend\n")]
    assert "MET.exeTypeOf(username, exercising)" in body("readBilled")
    fn = body("exeTypeOf")
    assert "F.typeOf(username)" in fn
    assert "getFitness" not in fn and "NR.call" not in fn and "NR.obj" not in fn


# --- the writer: every Fitness minute is vigorous whatever its MET ---------------------------------------------------

@pytest.mark.parametrize("met", [3.0, 3.5, 3.8, 6.0, 7.5])
def test_every_set_minute_is_resistance_vigorous_whatever_its_met(met):
    # S1508, S1509, S1301: resistance work suppresses hunger regardless of load: 30 min take S to the resistance
    # weight 0.5 x (1 - 2^-1) = 0.25, whatever the set bills
    h = WS.boot()
    p = WS.player(h)
    rec = WS.record(h)
    rec.body.met = met
    WS.kind_step(h, p, rec, 1, "Fitness", True)
    WS.kind_step(h, p, rec, 31, "Fitness", True)
    assert rec.satiety.S == pytest.approx(0.25)


def test_an_asleep_minute_with_the_flag_is_not_vigorous():
    h = WS.boot()
    W = h.NR.server.writer
    rec = WS.record(h)
    rec.body.met = 0.8
    ctx = h.rt.table()
    ctx.exercising = True
    ctx.activityClass = "Sleeping"
    assert W.vigorous(W.h, WS.player(h), rec, ctx) == (False, None)


def test_the_flag_answers_before_the_met_test():
    h = WS.boot()
    W = h.NR.server.writer
    rec = WS.record(h)
    rec.body.met = float("nan")                              # even an unreadable bill: the flag names the set
    ctx = h.rt.table()
    ctx.exercising = True
    ctx.activityClass = "Fitness"
    assert W.vigorous(W.h, WS.player(h), rec, ctx) == (True, "resistance")


@pytest.mark.parametrize("cls,met,want", [("Walking5kmh", 3.8, (False, None)), ("HeavyWork", 6.0, (True, "aerobic")),
                                          ("DiggingSpade", 5.0, (False, None)), ("Fitness", 3.0, (False, None))])
def test_without_the_flag_the_bar_stays(cls, met, want):
    # the 6.0 bar stays for aerobic work; a Fitness class stamp without the flag is not a set
    h = WS.boot()
    W = h.NR.server.writer
    rec = WS.record(h)
    rec.body.met = met
    ctx = h.rt.table()
    ctx.exercising = False
    ctx.activityClass = cls
    assert W.vigorous(W.h, WS.player(h), rec, ctx) == want


# --- the wrapper: NR_Server_Fitness.lua --------------------------------------------------------------------------------

FIT_ENV = r"""
NR_FT = { adds = { OnServerStarted = {} }, server = true, printed = {}, calls = { start = 0, stop = 0, new = 0 } }
Events = { OnServerStarted = { Add = function(fn) local l = NR_FT.adds.OnServerStarted; l[#l + 1] = fn end } }
isServer = function() return NR_FT.server end
isClient = function() return false end
print = function(s) NR_FT.printed[#NR_FT.printed + 1] = tostring(s) end
"""

# vanilla's class table, as shared/TimedActions/ISFitnessAction.lua builds it: new(character, exercise, timeToExe,
# exeData, exeDataType) sets o.exeDataType; serverStart sets the current exercise; serverStop clears it
VANILLA = r"""
ISFitnessAction = {}
ISFitnessAction.__index = ISFitnessAction
function ISFitnessAction:new(character, exercise, timeToExe, exeData, exeDataType)
    NR_FT.calls.new = NR_FT.calls.new + 1
    local o = setmetatable({}, self)
    o.character = character
    o.exeDataType = exeDataType
    return o
end
function ISFitnessAction:serverStart()
    NR_FT.calls.start = NR_FT.calls.start + 1
    NR_FT.current = self.exeDataType
    if NR_FT.raiseStart then error("vanilla raised") end
end
function ISFitnessAction:serverStop()
    NR_FT.calls.stop = NR_FT.calls.stop + 1
    NR_FT.current = nil
end
function NR_FT.char(name)
    return { getUsername = function(s) return name end }
end
"""


def same(h, a, b):
    return h.rt.eval("rawequal")(a, b)


def _lua_load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


class FitHost:
    def __init__(self, vanilla=True, start=True):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(FIT_ENV)
        if vanilla:
            self.rt.execute(VANILLA)
        _lua_load(self.rt, CORE)
        self.G = self.rt.globals()
        self.G.NutritionRevamp.server.players = self.rt.eval("{ onFirstSight = {}, onDeparture = {} }")
        self.vanilla_new = self.G.ISFitnessAction.new if vanilla else None
        _lua_load(self.rt, FITNESS)
        if start:
            self.start()

    def start(self):
        self.rt.execute("for i = 1, #NR_FT.adds.OnServerStarted do NR_FT.adds.OnServerStarted[i]() end")

    def reload(self):
        # a reloadlua: NR_Core re-creates NutritionRevamp by plain assignment (#0943), then the file runs again
        players = self.G.NutritionRevamp.server.players
        _lua_load(self.rt, CORE)
        self.G.NutritionRevamp.server.players = players
        _lua_load(self.rt, FITNESS)

    @property
    def FIT(self):
        return self.G.NutritionRevamp.server.fitness

    def action(self, name, exe):
        return self.G.ISFitnessAction.new(self.G.ISFitnessAction, self.G.NR_FT.char(name), "ex", 10, None, exe)


def test_the_wrapper_calls_the_original_and_records_then_clears():
    h = FitHost()
    a = h.action("admin", "burpees")
    a.serverStart(a)                                         # the server: NetTimedAction.start through the class table
    assert h.G.NR_FT.calls.start == 1 and h.G.NR_FT.current == "burpees"
    assert h.FIT.exeType["admin"] == "burpees" and h.FIT.typeOf("admin") == "burpees"
    a.serverStop(a)
    assert h.G.NR_FT.calls.stop == 1 and h.G.NR_FT.current is None
    assert h.FIT.exeType["admin"] is None
    assert h.FIT.stats.starts == 1 and h.FIT.stats.stops == 1 and h.FIT.stats.failures == 0


def test_new_is_never_wrapped():
    # a varargs `new` would send the client no arguments (NetTimedAction.set reads new's parameter names): never touched
    h = FitHost()
    assert same(h, h.G.ISFitnessAction.new, h.vanilla_new)
    assert h.FIT.wrappedStart is True and h.FIT.wrappedStop is True
    code = _code(FITNESS)
    assert '"new"' not in code and ".new =" not in code and "ISFitnessAction.new" not in code


def test_no_record_until_server_start():
    # the action built (new) but not started records nothing: the record is serverStart's, never new's
    h = FitHost()
    h.action("admin", "squats")
    assert h.G.NR_FT.calls.new == 1 and h.FIT.exeType["admin"] is None


def test_a_non_string_type_records_nothing():
    # an open set first: an untyped start clears the earlier record, never keeps it
    h = FitHost()
    a = h.action("admin", "burpees")
    a.serverStart(a)
    assert h.FIT.exeType["admin"] == "burpees"
    for bad in (None, 7, h.rt.table()):
        h.FIT.exeType["admin"] = "burpees"
        a = h.action("admin", bad)
        a.serverStart(a)
        assert h.FIT.exeType["admin"] is None
    assert h.FIT.stats.untyped == 3 and h.G.NR_FT.calls.start == 4


def test_a_raising_original_raises_and_records_nothing():
    h = FitHost()
    h.G.NR_FT.raiseStart = True
    a = h.action("admin", "burpees")
    with pytest.raises(lua51.LuaError):
        a.serverStart(a)
    assert h.G.NR_FT.calls.start == 1 and h.FIT.exeType["admin"] is None


def test_a_raising_record_never_blocks_the_original():
    h = FitHost()
    h.rt.execute("NutritionRevamp.server.fitness.mark = function() error('boom') end")
    a = h.action("admin", "squats")
    a.serverStart(a)
    assert h.G.NR_FT.calls.start == 1 and h.G.NR_FT.current == "squats"
    assert h.FIT.stats.failures == 1
    assert "boom" in h.FIT.lastError


def test_a_broken_action_never_blocks_the_original():
    h = FitHost()
    a = h.G.ISFitnessAction.new(h.G.ISFitnessAction, None, "ex", 10, None, "squats")   # no character
    a.serverStart(a)
    a.serverStop(a)
    assert h.G.NR_FT.calls.start == 1 and h.G.NR_FT.calls.stop == 1
    assert h.FIT.stats.failures == 0 and h.FIT.stats.starts == 0


def test_the_client_passes_through_and_records_nothing():
    h = FitHost()
    h.G.NR_FT.server = False
    a = h.action("admin", "burpees")
    a.serverStart(a)
    assert h.G.NR_FT.calls.start == 1 and h.FIT.exeType["admin"] is None
    assert h.FIT.stats.passthrough == 1


def test_the_wrapper_installs_once_with_no_double_wrap_on_a_reload():
    h = FitHost()
    w_start, w_stop = h.G.ISFitnessAction.serverStart, h.G.ISFitnessAction.serverStop
    h.FIT.install()
    h.start()
    assert same(h, h.G.ISFitnessAction.serverStart, w_start) and same(h, h.G.ISFitnessAction.serverStop, w_stop)
    h.reload()
    h.start()
    assert same(h, h.G.ISFitnessAction.serverStart, w_start) and same(h, h.G.ISFitnessAction.serverStop, w_stop)
    assert same(h, h.G.ISFitnessAction.new, h.vanilla_new)
    a = h.action("admin", "situp")
    a.serverStart(a)
    assert h.G.NR_FT.calls.start == 1                        # the original ran once: no wrapper wraps a wrapper
    assert h.FIT.exeType["admin"] == "situp"                 # the reloaded module records (the logic is read per call)
    assert h.FIT.wrappedStart is True and h.FIT.wrappedStop is True


def test_another_mods_later_wrap_keeps_ours_in_the_chain():
    h = FitHost()
    h.rt.execute("""
        local prev = ISFitnessAction.serverStart
        ISFitnessAction.serverStart = function(self) NR_FT.other = true; return prev(self) end
    """)
    h.start()                                                 # ours is still below: never re-wrapped
    a = h.action("admin", "pushups")
    a.serverStart(a)
    assert h.G.NR_FT.other is True and h.G.NR_FT.calls.start == 1 and h.FIT.exeType["admin"] == "pushups"


def test_an_absent_class_installs_nothing_and_logs_a_limitation():
    h = FitHost(vanilla=False)
    assert h.G.ISFitnessAction is None
    assert h.FIT.wrappedStart is False and h.FIT.wrappedStop is False
    lim = list(h.FIT.limitations.values())
    assert sum(1 for x in lim if "ISFitnessAction was absent" in x and "6.0" in x) == 1
    assert any("ISFitnessAction" in x for x in h.G.NR_FT.printed.values())
    h.start()                                                 # a second start adds no second line
    assert len(list(h.FIT.limitations.values())) == len(lim)


def test_departure_forgets_the_type():
    h = FitHost()
    a = h.action("admin", "burpees")
    a.serverStart(a)
    dep = list(h.G.NutritionRevamp.server.players.onDeparture.values())
    assert len(dep) == 1 and same(h, dep[0], h.FIT.forget)
    assert len(list(h.G.NutritionRevamp.server.players.onFirstSight.values())) == 0
    h.start()
    assert len(list(h.G.NutritionRevamp.server.players.onDeparture.values())) == 1   # wired once
    h.FIT.forget("admin")
    assert h.FIT.exeType["admin"] is None


def test_forget_reads_the_module_at_call_time_and_is_safe_without_it():
    h = FitHost()
    a = h.action("admin", "burpees")
    a.serverStart(a)
    forget = h.FIT.forget
    saved = h.G.NutritionRevamp.server.fitness
    h.G.NutritionRevamp.server.fitness = None
    forget("admin")                                          # no module: nothing raised
    h.G.NutritionRevamp.server.fitness = saved
    assert h.FIT.exeType["admin"] == "burpees"
    forget("admin")
    assert h.FIT.exeType["admin"] is None


def test_not_wired_off_the_server():
    h = FitHost(start=False)
    h.G.NR_FT.server = False
    h.start()
    assert len(list(h.G.NutritionRevamp.server.players.onDeparture.values())) == 0


def test_the_file_loads_with_no_engine():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    _lua_load(rt, CORE)
    _lua_load(rt, FITNESS)
    assert rt.globals().NutritionRevamp.server.fitness.wrappedStart is False


def test_the_shared_host_loads_it():
    from .server_host import Host
    h = Host()
    assert h.NR.server.fitness is not None and h.NR.server.fitness.wrappedStart is False
