"""NR_Server_Intake.lua must load with no engine and expose the eat wrapper's pure helpers.

The file is a server/ file the kernel host does not load (the host loads NR_Core.lua and the
NR_Kernel*.lua files only), so this test loads it on top of the session host itself, the way
test_bench.py loads NR_Server_Bench.lua. Every Java global the file names (ISEatFoodAction, Events,
getGameTime) sits inside a function behind a nil check, so the load runs no engine code and the
file-scope install() finds no ISEatFoodAction and wraps nothing. The wrapper bodies need the engine
and are proved live (Plan 2 Tasks 13-14); the helpers below carry no Java and are covered here by
hand-computed values.
"""
import os
import pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
INTAKE = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Intake.lua"
)
TOL = 1e-6


@pytest.fixture(scope="session")
def intake_host(host):
    with open(INTAKE, encoding="utf-8") as fh:
        src = fh.read()
    chunk = host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Server_Intake.lua")
    chunk()
    return host


def I(h):
    return h.G.NutritionRevamp.server.intake


def tbl(h, d):
    t = h.rt.table()
    for k, v in d.items():
        t[k] = v
    return t


def as_dict(t):
    return {k: v for k, v in t.items()}


# --- the file loads with no engine ---------------------------------------------------------------

def test_file_loads_and_exposes_the_intake_table(intake_host):
    assert lua51.lua_type(I(intake_host)) == "table"
    for name in ("install", "uninstall", "shareEaten", "sourceOf", "craftMap", "macrosEaten", "assemble"):
        assert lua51.lua_type(I(intake_host)[name]) == "function", name


def test_install_without_the_engine_wraps_nothing(intake_host):
    assert intake_host.G.ISEatFoodAction is None
    assert I(intake_host).install() is False
    assert I(intake_host).wrapped is False


def test_sentinels_are_globals_of_their_own(intake_host):
    assert lua51.lua_type(intake_host.G.NR_IntakeComplete_Installed) == "table"
    assert lua51.lua_type(intake_host.G.NR_IntakeServerStop_Installed) == "table"


# --- shareEaten: the drop in RAW hunger over the instance base hunger, clamped 0..1 ---------------

def test_share_whole_apple_eaten(intake_host):
    # the item consumed at fraction 1: Eat zeroes hungChange (#0058)
    assert abs(I(intake_host).shareEaten(-0.16, 0, -0.16) - 1.0) < TOL


def test_share_half_apple_eaten(intake_host):
    # -0.16 - (-0.08) = -0.08 over -0.16: the sign cancels
    assert abs(I(intake_host).shareEaten(-0.16, -0.08, -0.16) - 0.5) < TOL


def test_share_untouched(intake_host):
    # a cancel under vanilla's guards, or a no-op eat, leaves hungChange where it was
    assert abs(I(intake_host).shareEaten(-0.16, -0.16, -0.16) - 0.0) < TOL


def test_share_zero_base_hunger(intake_host):
    assert I(intake_host).shareEaten(-0.16, 0, 0) == 0


def test_share_clamped_to_one(intake_host):
    # a second partial eat of an item whose base hunger is the whole: never above 1
    assert abs(I(intake_host).shareEaten(-0.32, 0, -0.16) - 1.0) < TOL


def test_share_clamped_to_zero(intake_host):
    assert abs(I(intake_host).shareEaten(-0.08, -0.16, -0.16) - 0.0) < TOL


# --- sourceOf: dish > craft > baseline -----------------------------------------------------------

def test_source_dish_when_extra_items(intake_host):
    assert I(intake_host).sourceOf(True, False) == "dish"


def test_source_dish_wins_over_craft_map(intake_host):
    assert I(intake_host).sourceOf(True, True) == "dish"


def test_source_craft_when_map_only(intake_host):
    assert I(intake_host).sourceOf(False, True) == "craft"


def test_source_baseline_otherwise(intake_host):
    assert I(intake_host).sourceOf(False, False) == "baseline"


# --- craftMap: the consumed fullType -> count map the hand-craft action writes (#2667) ------------

def test_craft_map_keeps_full_types_only(intake_host):
    h = intake_host
    md = tbl(h, {"Base.MincedMeat": 40, "customName": "x", "NR_flag": 1})
    out = I(h).craftMap(md)
    assert lua51.lua_type(out) == "table"
    assert as_dict(out) == {"Base.MincedMeat": 40}


def test_craft_map_drops_vanilla_keys_and_non_numbers(intake_host):
    h = intake_host
    md = tbl(h, {"Tooltip": 3, "Base.Salt": "two", "NR_Base.Thing": 2, "Base.Onion": 1, "Base.Carrots": 2})
    assert as_dict(I(h).craftMap(md)) == {"Base.Onion": 1, "Base.Carrots": 2}


def test_craft_map_vanilla_only_is_nil(intake_host):
    h = intake_host
    assert I(h).craftMap(tbl(h, {"customName": "x"})) is None


def test_craft_map_empty_is_nil(intake_host):
    h = intake_host
    assert I(h).craftMap(h.rt.table()) is None


def test_craft_map_nil_is_nil(intake_host):
    assert I(intake_host).craftMap(None) is None


# --- macrosEaten: what Eat delivered, x share, /5 burnt (#0019) -----------------------------------

def macros(t):
    return [t["calories"], t["carbs"], t["lipids"], t["proteins"]]


def close(a, b):
    return all(abs(x - y) < TOL for x, y in zip(a, b))


def test_macros_apple_whole_not_burnt(intake_host):
    out = I(intake_host).macrosEaten(95, 25.13, 0.31, 0.47, 1, False)
    assert close(macros(out), [95, 25.13, 0.31, 0.47])


def test_macros_apple_whole_burnt(intake_host):
    out = I(intake_host).macrosEaten(95, 25.13, 0.31, 0.47, 1, True)
    assert close(macros(out), [19, 5.026, 0.062, 0.094])


def test_macros_apple_half_not_burnt(intake_host):
    out = I(intake_host).macrosEaten(95, 25.13, 0.31, 0.47, 0.5, False)
    assert close(macros(out), [47.5, 12.565, 0.155, 0.235])


# --- assemble: the source chosen, the kernel's arithmetic, the macros overwritten ----------------

STUB = r"""
function(seeds)
    return function(fullType)
        local s = seeds[fullType]
        if s == nil then return nil end
        local v = {}
        for k, x in pairs(s) do v[k] = x end
        return v
    end
end
"""


def lookup(h):
    apple = tbl(h, {"calories": 95, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47, "fibre": 4.4, "water": 156})
    meat = tbl(h, {"calories": 100, "carbs": 0, "lipids": 5, "proteins": 20, "iron": 2})
    seeds = tbl(h, {"Base.Apple": apple, "Base.MincedMeat": meat})
    return h.rt.eval(STUB)(seeds)


def before(h, **kw):
    d = {"fullType": "Base.Apple", "rawBefore": -0.16, "instBase": -0.16, "scriptHunger": -0.16,
         "cal": 95, "carb": 25.13, "lip": 0.31, "pro": 0.47,
         "cooked": False, "burnt": False, "rotten": False, "frozen": False}
    d.update(kw)
    t = tbl(h, d)
    t["extraTypes"] = h.rt.table()
    return t


def test_assemble_baseline_half_apple(intake_host):
    h = intake_host
    vec, source, missing, share, frac = I(h).assemble(before(h), -0.08, lookup(h))
    assert abs(share - 0.5) < TOL and abs(frac - 0.5) < TOL
    assert source == "baseline"
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL
    assert abs(vec["water"] - 78) < TOL
    assert len(as_dict(missing)) == 0


def test_assemble_baseline_instance_scale(intake_host):
    # a split output at 1/2 of the script hunger: the mod nutrients halve, the macros track the live item
    h = intake_host
    b = before(h, rawBefore=-0.08, instBase=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235)
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h))
    assert source == "baseline"
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_burnt_macros_divided_by_five(intake_host):
    h = intake_host
    vec, source, missing, share, frac = I(h).assemble(before(h, burnt=True), 0, lookup(h))
    assert close(macros(vec), [19, 5.026, 0.062, 0.094])


def test_assemble_craft_map(intake_host):
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 2})
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h))
    assert source == "craft"
    assert close(macros(vec), [200, 0, 10, 40])
    assert abs(vec["iron"] - 4) < TOL


def test_assemble_dish_wins_and_records_missing(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Salad", rawBefore=-0.3, instBase=-0.3, scriptHunger=-0.3, cal=190, carb=50.26, lip=0.62, pro=0.94)
    extra = h.rt.table()
    extra[1] = "Base.Apple"
    extra[2] = "Base.Apple"
    extra[3] = "Base.Unknown"
    b["extraTypes"] = extra
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 2})
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h))
    assert source == "dish"
    assert abs(vec["fibre"] - 8.8) < TOL
    assert list(as_dict(missing).values()) == ["Base.Unknown"]


def test_assemble_unknown_baseline_is_missing(intake_host):
    h = intake_host
    vec, source, missing, share, frac = I(h).assemble(before(h, fullType="Base.Nothing"), 0, lookup(h))
    assert source == "baseline"
    assert list(as_dict(missing).values()) == ["Base.Nothing"]
    assert vec["fibre"] == 0
    assert abs(vec["calories"] - 95) < TOL


def test_assemble_second_half_of_a_part_eaten_apple(intake_host):
    # the live item was already shrunk by a first half eat (multiplyFoodValues): the macros are read
    # live and take Eat's own fraction of what was LEFT (1.0); the whole-instance seed takes the share
    # of the WHOLE (0.5) -- both deliver the second half of an apple
    h = intake_host
    b = before(h, rawBefore=-0.08, cal=47.5, carb=12.565, lip=0.155, pro=0.235)
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h))
    assert abs(share - 0.5) < TOL and abs(frac - 1.0) < TOL
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_nothing_eaten_lands_nothing(intake_host):
    h = intake_host
    vec, source, missing, share, frac = I(h).assemble(before(h), -0.16, lookup(h))
    assert vec is None
    assert share == 0


# --- install with a stand-in class: idempotent, composes, always calls the original ---------------

COMPOSE = r"""
function()
    local IN = NutritionRevamp.server.intake
    local calls = {}
    local cls = {}
    function cls.complete(self) calls[#calls + 1] = "vanilla" return true end
    function cls.serverStop(self) calls[#calls + 1] = "stop" end
    ISEatFoodAction = cls
    local first = IN.install()
    local w = cls.complete
    local again = IN.install()
    local same = cls.complete == w
    -- a sentinel-free corpus wrap (QualityCooking's shape) loads after the mod
    local saved = cls.complete
    cls.complete = function(self) calls[#calls + 1] = "qc" return saved(self) end
    local qc = cls.complete
    IN.install()
    local notRewrapped = cls.complete == qc
    -- no isServer global on this host: the wrapper is a pass-through that still runs the chain
    local r = cls.complete({})
    local order = table.concat(calls, " ")
    IN.uninstall()
    local passOff = NR_IntakeComplete_Installed.off
    ISEatFoodAction = nil
    NR_IntakeComplete_Installed.wrapper, NR_IntakeComplete_Installed.class = nil, nil
    NR_IntakeComplete_Installed.orig, NR_IntakeComplete_Installed.off = nil, nil
    NR_IntakeServerStop_Installed.wrapper, NR_IntakeServerStop_Installed.class = nil, nil
    NR_IntakeServerStop_Installed.orig, NR_IntakeServerStop_Installed.off = nil, nil
    IN.install()
    return first, again, same, notRewrapped, r, order, passOff
end
"""


def test_install_is_idempotent_and_composes(intake_host):
    before_pass = I(intake_host).stats.passthrough
    first, again, same, not_rewrapped, r, order, pass_off = intake_host.rt.eval(COMPOSE)()
    # one call through the chain, no isServer: it ran THROUGH the mod wrapper as a pass-through
    assert I(intake_host).stats.passthrough == before_pass + 1
    assert first is True and again is True
    assert same is True
    assert not_rewrapped is True
    assert r is True
    assert order == "qc vanilla"
    assert pass_off is True


RESET = r"""
function()
    ISEatFoodAction = nil
    for _, S in ipairs({NR_IntakeComplete_Installed, NR_IntakeServerStop_Installed}) do
        S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    end
end
"""


def reset_sentinels(h):
    h.rt.eval(RESET)()


UNINSTALL = r"""
function()
    local IN = NutritionRevamp.server.intake
    local cls = {}
    local vComplete = function(self) return true end
    local vStop = function(self) end
    cls.complete, cls.serverStop = vComplete, vStop
    ISEatFoodAction = cls
    IN.install()
    local wrapped = cls.complete ~= vComplete and cls.serverStop ~= vStop
    IN.uninstall()
    return wrapped, cls.complete == vComplete, cls.serverStop == vStop, IN.wrapped
end
"""


def test_uninstall_outermost_restores_the_originals(intake_host):
    h = intake_host
    reset_sentinels(h)
    try:
        wrapped, complete_restored, stop_restored, still = h.rt.eval(UNINSTALL)()
        assert wrapped is True
        assert complete_restored is True
        assert stop_restored is True
        assert still is False
    finally:
        reset_sentinels(h)


RELOAD = r"""
function()
    local IN = NutritionRevamp.server.intake
    local old = {}
    old.complete = function(self) return "old" end
    old.serverStop = function(self) end
    ISEatFoodAction = old
    IN.install()
    local oldWrapped = old.complete
    -- a reload of the vanilla file: a FRESH class table with fresh vanilla stubs
    local new = {}
    local vNew = function(self) return "new" end
    new.complete = vNew
    new.serverStop = function(self) end
    ISEatFoodAction = new
    IN.install()
    local C = NR_IntakeComplete_Installed
    return new.complete == C.wrapper, new.complete ~= vNew, C.orig == vNew, C.class == new,
        old.complete == oldWrapped, new.complete({}), IN.wrapped
end
"""


def test_reload_of_the_class_table_rewraps(intake_host):
    h = intake_host
    reset_sentinels(h)
    try:
        is_ours, replaced, orig_new, class_new, old_untouched, r, wrapped = h.rt.eval(RELOAD)()
        assert is_ours is True and replaced is True
        assert orig_new is True and class_new is True
        assert old_untouched is True
        assert r == "new"
        assert wrapped is True
    finally:
        reset_sentinels(h)


# --- fractionOf: the hunger fraction, or the thirst fraction for a thirst-only Food (#0014) ------

def test_fraction_thirst_only_whole(intake_host):
    frac, share = I(intake_host).fractionOf(0, 0, 0, -0.1, 0)
    assert abs(frac - 1.0) < TOL and abs(share - 1.0) < TOL


def test_fraction_thirst_only_half(intake_host):
    frac, share = I(intake_host).fractionOf(0, 0, 0, -0.1, -0.05)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_thirst_only_nil_base(intake_host):
    frac, share = I(intake_host).fractionOf(0, 0, None, -0.1, -0.05)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_hunger_ignores_thirst(intake_host):
    # a part-eaten apple: share of the whole 0.5, Eat's own fraction of what was left 1.0
    frac, share = I(intake_host).fractionOf(-0.08, 0, -0.16, -0.1, -0.1)
    assert abs(frac - 1.0) < TOL and abs(share - 0.5) < TOL


def test_fraction_hunger_half_apple(intake_host):
    frac, share = I(intake_host).fractionOf(-0.16, -0.08, -0.16, None, None)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_both_zero_is_zero(intake_host):
    frac, share = I(intake_host).fractionOf(0, 0, 0, 0, 0)
    assert frac == 0 and share == 0


def test_assemble_thirst_only_food_lands_its_calories(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Nothing", rawBefore=0, instBase=0, scriptHunger=0,
               cal=2, carb=0, lip=0, pro=0, thirstBefore=-0.1)
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h), 0)
    assert abs(share - 1.0) < TOL and abs(frac - 1.0) < TOL
    assert abs(vec["calories"] - 2) < TOL


def test_assemble_thirst_only_food_half(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Nothing", rawBefore=0, instBase=0, scriptHunger=0,
               cal=2, carb=0, lip=0, pro=0, thirstBefore=-0.1)
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h), -0.05)
    assert abs(share - 0.5) < TOL
    assert abs(vec["calories"] - 1) < TOL
