"""PZAgent_Hutch.lua (Plan 28 Task 1c, ruling P28-G): the client's hutch guard. A loaded fixture hutch's animal map is
cleared when it holds a null, so the client's chunk unload (IsoHutch.removeFromWorld, which calls removeFromUpdateLists
on every value with no null test) never meets one. The fakes: a global getHutch answering a hutch at its squares and
nil elsewhere, each call logged; a hutch with getAnimalInside and isSlave; a map with containsValue, values, clear and
size over a dict of slot -> animal (None stands for the client's put(slot, null))."""
from .conftest import lua_file, make_player, J

HEN = (10720, 10592)        # the hen hutch's chunk (1340, 1324): its tiles' origin
TURKEY = (10776, 10632)     # the turkey hutch's chunk (1347, 1329)
HEN_MASTER = (10723, 10594)
HEN_SLAVE = (10722, 10594)  # swept first (row 2, column 2): a slave tile is skipped
TURKEY_MASTER = (10779, 10635)


class Calls(list):
    """Every Java call the fakes answer, in order: (member, args...)."""


def make_map(calls, slots):
    d = dict(slots)
    m = J()
    m.d = d
    m.args = []

    def contains_value(s, v):
        calls.append(("containsValue", v))
        m.args.append(v)
        return v in d.values()

    def values(s):
        calls.append(("values",))
        return list(d.values())

    def clear(s):
        calls.append(("clear",))
        d.clear()

    def size(s):
        calls.append(("size",))
        return len(d)
    m.containsValue, m.values, m.clear, m.size = contains_value, values, clear, size
    return m


def make_hutch(calls, amap, slave=False):
    def inside(s):
        calls.append(("getAnimalInside",))
        return amap

    def is_slave(s):
        calls.append(("isSlave",))
        return slave
    return J(getAnimalInside=inside, isSlave=is_slave, map=amap)


class World:
    """The squares getHutch answers: (x, y) -> hutch; everything else nil."""
    def __init__(self, lua):
        self.calls = Calls()
        self.squares = {}
        self.printed = []
        g = lua.globals()
        g.getHutch = self.get_hutch
        g.print = lambda *a: self.printed.append(" ".join(str(x) for x in a))

    def get_hutch(self, x, y, z):
        self.calls.append(("getHutch", x, y, z))
        return self.squares.get((int(x), int(y)))

    def hen(self, slots=None):
        """The hen hutch loaded: a slave at HEN_SLAVE and the master at HEN_MASTER, the master's map answered."""
        amap = make_map(self.calls, slots if slots is not None else {0: "hen1", 1: "hen2"})
        self.squares[HEN_SLAVE] = make_hutch(self.calls, make_map(self.calls, {}), slave=True)
        self.squares[HEN_MASTER] = make_hutch(self.calls, amap)
        return amap

    def turkey(self, slots=None):
        amap = make_map(self.calls, slots if slots is not None else {0: "turkey1"})
        self.squares[TURKEY_MASTER] = make_hutch(self.calls, amap)
        return amap

    def unload(self, *squares):
        for s in squares:
            self.squares.pop(s, None)

    def guard_calls(self):
        return [c for c in self.calls if c[0] != "getHutch"]


def load(lua):
    lua.execute(open(lua_file("client/PZAgent_Hutch.lua"), encoding="utf-8").read())


def guard(lua, n=1):
    """n guard ticks, each with the next tick number (PZA.tick, Main's counter, kept here without Main)."""
    g = lua.globals()
    for _ in range(n):
        g.PZA.tick = (g.PZA.tick or 0) + 1
        lua.eval("PZA.hutch.guard(...)", g.PZA.tick)


def found(lua, name):
    """The master square the guard has found for the named hutch, or None."""
    for rec in lua.eval("PZA.hutch.HUTCHES").values():
        if rec["name"] == name:
            return (rec["x"], rec["y"]) if rec["x"] is not None else None
    raise KeyError(name)


def sweep(lua, w, names=("hen", "turkey")):
    """Ticks until every named hutch's master square is found (one sweep is 8 ticks, a row of 8 squares each), then
    clears the call log."""
    for _ in range(8):
        if all(found(lua, n) is not None for n in names):
            break
        guard(lua)
    assert all(found(lua, n) is not None for n in names)
    w.calls.clear()


def missing(lua):
    return list(lua.eval("PZA.hutch.missing").values())


def clears(w):
    return [p for p in w.printed if "cleared" in p]


# ---- the table and the sweep ----------------------------------------------------------------------------------------

def test_the_table_holds_the_two_fixture_hutches_chunk_origins(lua):
    load(lua)
    rows = [(r["name"], r["x0"], r["y0"]) for r in lua.eval("PZA.hutch.HUTCHES").values()]
    assert rows == [("hen", HEN[0], HEN[1]), ("turkey", TURKEY[0], TURKEY[1])]
    assert lua.eval("PZA.hutch.CHUNK") == 8


def row(origin, r):
    """The getHutch calls of one sweep tick over row r of the chunk at origin."""
    return [("getHutch", origin[0] + i, origin[1] + r, 0) for i in range(8)]


def test_the_sweep_reads_a_row_of_eight_squares_a_hutch_a_tick_and_skips_a_slave_tile(lua):
    load(lua)
    w = World(lua)
    w.hen()
    guard(lua)
    assert w.calls == row(HEN, 0) + row(TURKEY, 0)
    guard(lua, 2)                                                # the master is on row 2: found on the third tick
    assert found(lua, "hen") == HEN_MASTER
    hen_row2 = [c for c in w.calls[32:] if c[0] != "getHutch" or c[1] < TURKEY[0]]
    assert hen_row2 == row(HEN, 2)[:3] + [("isSlave",)] + [row(HEN, 2)[3], ("isSlave",)]   # stops at the master
    assert ("isSlave",) in w.calls                               # the slave tile was asked and passed over
    assert found(lua, "turkey") is None                         # its chunk is not loaded: still sweeping
    assert any("found the hen hutch at 10723,10594" in p for p in w.printed)


def test_the_sweep_covers_the_chunks_64_squares_in_eight_ticks_and_wraps(lua):
    load(lua)
    w = World(lua)
    guard(lua, 9)
    hen = [(c[1], c[2]) for c in w.calls if c[0] == "getHutch" and c[1] < TURKEY[0]]
    assert len(hen) == 72 and len(set(hen[:64])) == 64 and hen[64:] == [(x, y) for _, x, y, _ in row(HEN, 0)]
    assert {x for x, _ in hen} == set(range(HEN[0], HEN[0] + 8))
    assert {y for _, y in hen} == set(range(HEN[1], HEN[1] + 8))


# ---- the guard -------------------------------------------------------------------------------------------------------

def test_a_tick_with_a_null_value_clears_the_map_once_and_logs_the_clear(lua):
    load(lua)
    w = World(lua)
    amap = w.hen()
    w.turkey()
    sweep(lua, w)
    amap.d[2] = None                                             # the client's put(old slot, null)
    guard(lua)
    assert amap.d == {}
    assert w.guard_calls().count(("clear",)) == 1
    assert lua.eval("PZA.hutch.clears") == 1
    tick = lua.globals().PZA.tick
    assert clears(w) == ["[PZAgent] hutch guard: cleared the hen hutch at 10723,10594 (tick %d, 3 entries, clear 1, "
                         "0 unlogged since the last line)" % tick]
    guard(lua, 3)                                                # cleared: nothing more to clear
    assert w.guard_calls().count(("clear",)) == 1 and lua.eval("PZA.hutch.clears") == 1


def test_nil_crosses_to_contains_value_as_none(lua):
    load(lua)
    w = World(lua)
    amap = w.hen()
    sweep(lua, w, ("hen",))
    guard(lua)
    assert amap.args == [None]


def test_a_tick_with_no_null_clears_nothing(lua):
    load(lua)
    w = World(lua)
    amap = w.hen()
    w.turkey()
    sweep(lua, w)
    guard(lua, 5)
    assert amap.d == {0: "hen1", 1: "hen2"}
    assert ("clear",) not in w.calls and clears(w) == [] and lua.eval("PZA.hutch.clears") == 0


def test_no_hutch_loaded_reads_nothing_beyond_get_hutch(lua):
    load(lua)
    w = World(lua)
    w.hen()
    w.turkey()
    sweep(lua, w)
    guard(lua)
    w.unload(HEN_MASTER, HEN_SLAVE, TURKEY_MASTER)
    w.calls.clear()
    guard(lua, 3)
    assert w.calls == [("getHutch", HEN_MASTER[0], HEN_MASTER[1], 0),
                       ("getHutch", TURKEY_MASTER[0], TURKEY_MASTER[1], 0)] * 3
    assert lua.eval("PZA.hutch.HUTCHES[1].obj") is None          # an unloaded hutch is not held


def test_a_reloaded_hutch_is_read_again_and_its_null_cleared(lua):
    load(lua)
    w = World(lua)
    first = w.hen()
    sweep(lua, w, ("hen",))
    guard(lua)
    w.unload(HEN_MASTER, HEN_SLAVE)
    guard(lua)
    second = w.hen({0: "hen1", 3: None})                         # the chunk reloaded: a new hutch object
    w.calls.clear()
    guard(lua)
    assert ("getAnimalInside",) in w.calls and second.d == {} and first.d == {0: "hen1", 1: "hen2"}
    assert lua.eval("PZA.hutch.clears") == 1


def test_a_new_hutch_object_on_the_next_tick_is_read_by_its_identity_alone(lua):
    """No nil tick between the two objects (a reload within one tick), so only the identity check sees the change."""
    load(lua)
    w = World(lua)
    first = w.hen()
    sweep(lua, w, ("hen",))
    guard(lua)
    second = w.hen({0: "hen1", 4: None})                         # replaced in place: getHutch never answered nil
    w.calls.clear()
    guard(lua)
    assert ("getAnimalInside",) in w.calls and second.d == {} and first.d == {0: "hen1", 1: "hen2"}
    assert lua.eval("PZA.hutch.clears") == 1


def test_the_turkey_hutchs_square_the_same(lua):
    load(lua)
    w = World(lua)
    amap = w.turkey({0: "turkey1", 1: None})
    sweep(lua, w, ("turkey",))
    assert found(lua, "turkey") == TURKEY_MASTER
    guard(lua)
    assert amap.d == {}
    assert clears(w)[0].startswith("[PZAgent] hutch guard: cleared the turkey hutch at 10779,10635 (tick ")


def test_the_per_tick_cost_is_two_java_calls_a_loaded_hutch_with_no_null(lua):
    load(lua)
    w = World(lua)
    w.hen()
    w.turkey()
    sweep(lua, w)
    guard(lua)                                                   # the first read of each hutch takes its map
    w.calls.clear()
    guard(lua)
    assert len(w.calls) <= 2 + 2
    assert w.calls == [("getHutch", HEN_MASTER[0], HEN_MASTER[1], 0), ("containsValue", None),
                       ("getHutch", TURKEY_MASTER[0], TURKEY_MASTER[1], 0), ("containsValue", None)]


def test_the_sweeps_budget_is_eight_get_hutch_calls_a_hutch_a_tick(lua):
    load(lua)
    w = World(lua)
    for _ in range(8):
        w.calls.clear()
        guard(lua)
        assert len(w.calls) == 8 + 8                             # nothing loaded: one row of each chunk
    w.hen()
    w.calls.clear()
    guard(lua, 3)                                                # rows 0, 1 and 2: the hen found on row 2
    assert len([c for c in w.calls if c[0] == "getHutch"]) <= 3 * (8 + 8)


# ---- the clear log, rate-limited -------------------------------------------------------------------------------------

def test_the_clear_log_is_one_line_a_hutch_per_hutch_log_s_while_every_clear_counts(lua):
    """A hen in a nest box: every packet rewrites the null, so the guard clears once a packet; the console takes one
    line a hutch per HUTCH_LOG_S and the next line counts the clears left unlogged."""
    load(lua)
    g = lua.globals()
    w = World(lua)
    amap = w.hen()
    tmap = w.turkey()
    sweep(lua, w)
    assert lua.eval("PZA.hutch.HUTCH_LOG_S") == 10
    for _ in range(5):                                           # five packets' nulls inside one second
        amap.d[2] = None
        guard(lua)
        g._clock["ms"] += 200
    tmap.d[1] = None
    guard(lua)
    assert lua.eval("PZA.hutch.clears") == 6
    lines = clears(w)
    assert len(lines) == 2 and "the hen hutch" in lines[0] and "the turkey hutch" in lines[1]
    g._clock["ms"] += 10000
    amap.d[2] = None
    guard(lua)
    lines = clears(w)
    assert len(lines) == 3 and "clear 7, 4 unlogged since the last line" in lines[2]
    g._clock["ms"] += 10000                                      # the controller's residual (review-t1c fix 1): the
    amap.d[2] = None                                             # unlogged count resets after a line
    guard(lua)
    lines = clears(w)
    assert len(lines) == 4 and "clear 8, 0 unlogged since the last line" in lines[3]


# ---- absent members --------------------------------------------------------------------------------------------------

def test_get_hutch_absent_is_named_once_and_the_guard_stands_down(lua):
    load(lua)
    w = World(lua)
    lua.globals().getHutch = None
    guard(lua, 3)
    assert missing(lua) == ["getHutch"]
    assert [p for p in w.printed if "stood down" in p] == ["[PZAgent] hutch guard: stood down, getHutch absent"]
    lua.globals().getHutch = w.get_hutch                         # back: the guard stays down
    w.hen({0: None})
    guard(lua, 70)
    assert w.calls == [] and missing(lua) == ["getHutch"]


def test_get_animal_inside_absent_is_named_once_and_the_guard_stands_down(lua):
    load(lua)
    w = World(lua)
    w.hen()
    w.squares[HEN_MASTER].getAnimalInside = None
    sweep(lua, w, ("hen",))
    guard(lua, 3)
    assert missing(lua) == ["getAnimalInside"]
    assert [p for p in w.printed if "stood down" in p] == ["[PZAgent] hutch guard: stood down, getAnimalInside absent"]
    w.calls.clear()
    guard(lua, 3)
    assert w.calls == []


def test_the_tick_that_stands_down_reads_no_further_hutch(lua):
    load(lua)
    w = World(lua)
    w.hen()
    w.turkey()
    sweep(lua, w)
    guard(lua)
    w.unload(HEN_MASTER, HEN_SLAVE)
    w.hen()                                                      # reloaded: a new hutch, its map member absent
    w.squares[HEN_MASTER].getAnimalInside = None
    w.calls.clear()
    guard(lua)
    assert w.calls == [("getHutch", HEN_MASTER[0], HEN_MASTER[1], 0)] and missing(lua) == ["getAnimalInside"]


def test_contains_value_absent_is_named_once_and_the_guard_stands_down(lua):
    load(lua)
    w = World(lua)
    amap = w.hen({0: None})
    amap.containsValue = None
    sweep(lua, w, ("hen",))
    guard(lua, 3)
    assert missing(lua) == ["containsValue"] and amap.d == {0: None}
    w.calls.clear()
    guard(lua, 3)
    assert w.calls == []


# ---- Main's tick -----------------------------------------------------------------------------------------------------

def load_client(lua):
    """The client files in the game's load order (by name: Hutch, Link, Main, Map, ...)."""
    for f in ("shared/PZAgent_World.lua", "client/PZAgent_Hutch.lua", "client/PZAgent_Link.lua",
              "client/PZAgent_Main.lua", "client/PZAgent_Map.lua", "client/PZAgent_Motor.lua",
              "client/PZAgent_Sense.lua", "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua",
              "client/PZAgent_Stance.lua", "client/PZAgent_Tend.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def test_mains_tick_runs_the_guard_once_a_tick_after_the_init_tick(lua):
    load_client(lua)
    g = lua.globals()
    w = World(lua)
    amap = w.hen()
    player = make_player()
    g.getPlayer = lambda: player
    g._handlers[0]()                                             # the init tick: no guard
    assert w.calls == []
    for _ in range(8):
        g._handlers[0]()
    assert found(lua, "hen") == HEN_MASTER
    amap.d[5] = None
    g._handlers[0]()
    assert amap.d == {} and lua.eval("PZA.hutch.clears") == 1
    w.calls.clear()
    g._handlers[0]()
    hen = [("getHutch", HEN_MASTER[0], HEN_MASTER[1], 0)]
    assert [c for c in w.calls if c[0] == "getHutch"] == hen + row(TURKEY, 1)


def test_a_guard_raise_stands_it_down_and_the_tick_goes_on(lua):
    load_client(lua)
    g = lua.globals()
    w = World(lua)

    def raising(x, y, z):
        w.calls.append(("getHutch", x, y, z))
        raise RuntimeError("hutch read raised")
    g.getHutch = raising
    player = make_player()
    g.getPlayer = lambda: player
    for _ in range(8):
        g._handlers[0]()
    assert len(w.calls) == 1                                     # raised once, then stood down
    assert lua.eval("PZA.hutch.off") is True and lua.eval("PZA.hutch.errors") == 1
    assert "raise:hutch" in missing(lua)
    assert [p for p in w.printed if "stood down" in p] == ["[PZAgent] hutch guard: stood down, raise:hutch"]
    assert g.PZA.errors == 1
    assert lua.eval("PZA.main.prev") is not None                 # the frame was still read and emitted
