"""NR_Server_Intake.lua must load with no engine and expose the eat wrapper's pure helpers.

The file is a server/ file the kernel host does not load (the host loads NR_Core.lua and the
NR_Kernel*.lua files only), so this test loads it on top of the session host itself, the way
test_bench.py loads NR_Server_Bench.lua. Every Java global the file names (ISEatFoodAction, Events,
getGameTime) sits inside a function behind a nil check, so the load runs no engine code and the
file-scope install() finds no ISEatFoodAction and wraps nothing. The helpers below carry no Java and
are covered here by hand-computed values; the server path (wrapper, before-read, original, landing in
the store) is driven end to end through Lua stand-ins for the Java objects at the end of this file.
Neither proves the engine's real member names or behaviour, which the live runs do (Plan 2 Tasks
13-14).
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
    vec, source, missing, share, frac, _trace = I(h).assemble(before(h), -0.08, lookup(h))
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
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h))
    assert source == "baseline"
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_burnt_macros_divided_by_five(intake_host):
    h = intake_host
    vec, source, missing, share, frac, _trace = I(h).assemble(before(h, burnt=True), 0, lookup(h))
    assert close(macros(vec), [19, 5.026, 0.062, 0.094])


def test_assemble_craft_map(intake_host):
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 2})
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h))
    assert source == "craft"
    assert close(macros(vec), [200, 0, 10, 40])
    assert abs(vec["iron"] - 4) < TOL


def test_assemble_craft_map_zero_count_lands_no_seed(intake_host):
    # vanilla writes integer counts >= 1 (ISHandcraftAction.performRecipe); a 0 count is kept by
    # craftMap and contributes nothing through K.vector.craft, while the macros still track the item
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = I(h).craftMap(tbl(h, {"Base.MincedMeat": 0}))
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h))
    assert source == "craft"
    assert vec["iron"] == 0
    assert close(macros(vec), [200, 0, 10, 40])


def test_assemble_dish_wins_and_records_missing(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Salad", rawBefore=-0.3, instBase=-0.3, scriptHunger=-0.3, cal=190, carb=50.26, lip=0.62, pro=0.94)
    extra = h.rt.table()
    extra[1] = "Base.Apple"
    extra[2] = "Base.Apple"
    extra[3] = "Base.Unknown"
    b["extraTypes"] = extra
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 2})
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h))
    assert source == "dish"
    assert abs(vec["fibre"] - 8.8) < TOL
    assert list(as_dict(missing).values()) == ["Base.Unknown"]


def test_assemble_unknown_baseline_is_missing(intake_host):
    h = intake_host
    vec, source, missing, share, frac, _trace = I(h).assemble(before(h, fullType="Base.Nothing"), 0, lookup(h))
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
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h))
    assert abs(share - 0.5) < TOL and abs(frac - 1.0) < TOL
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert abs(vec["fibre"] - 2.2) < TOL


def test_assemble_nothing_eaten_lands_nothing(intake_host):
    h = intake_host
    vec, source, missing, share, frac, _trace = I(h).assemble(before(h), -0.16, lookup(h))
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
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h), 0)
    assert abs(share - 1.0) < TOL and abs(frac - 1.0) < TOL
    assert abs(vec["calories"] - 2) < TOL


def test_assemble_thirst_only_food_half(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Nothing", rawBefore=0, instBase=0, scriptHunger=0,
               cal=2, carb=0, lip=0, pro=0, thirstBefore=-0.1)
    vec, source, missing, share, frac, _trace = I(h).assemble(b, 0, lookup(h), -0.05)
    assert abs(share - 0.5) < TOL
    assert abs(vec["calories"] - 1) < TOL


# --- the drink wrapper's pure helpers: litresDrunk and fluidVector -------------------------------

def test_litres_drunk_half_can(intake_host):
    assert abs(I(intake_host).litresDrunk(0.3, 0.15) - 0.15) < TOL


def test_litres_drunk_no_op(intake_host):
    assert I(intake_host).litresDrunk(0.3, 0.3) == 0


def test_litres_drunk_never_negative(intake_host):
    assert I(intake_host).litresDrunk(0.15, 0.3) == 0


def test_litres_drunk_nil_is_zero(intake_host):
    assert I(intake_host).litresDrunk(None, 0.1) == 0
    assert I(intake_host).litresDrunk(0.3, None) == 0


def fluid_lookup(h):
    cola = tbl(h, {"calories": 400, "carbs": 104, "lipids": 0, "proteins": 0, "water": 890})
    water = tbl(h, {"calories": 0, "carbs": 0, "lipids": 0, "proteins": 0, "water": 1000})
    seeds = tbl(h, {"Cola": cola, "Water": water})
    return h.rt.eval(STUB)(seeds)


def mix(h, *pairs):
    return h.rt.table(*[h.rt.table(t, s) for t, s in pairs])


def test_fluid_vector_full_can_of_cola(intake_host):
    # Cola per litre 400 kcal, 104 g carbs x 0.3 L = the per-can 120 / 31.2 (#0634, #1892)
    h = intake_host
    vec, missing = I(h).fluidVector(fluid_lookup(h), mix(h, ("Cola", 1.0)), 0.3)
    assert abs(vec["calories"] - 120) < TOL
    assert abs(vec["carbs"] - 31.2) < TOL
    assert len(as_dict(missing)) == 0


def test_fluid_vector_half_cola_half_water(intake_host):
    h = intake_host
    vec, missing = I(h).fluidVector(fluid_lookup(h), mix(h, ("Cola", 0.5), ("Water", 0.5)), 0.4)
    assert abs(vec["calories"] - 80) < TOL
    assert abs(vec["water"] - (0.5 * 0.4 * 890 + 0.5 * 0.4 * 1000)) < TOL
    assert len(as_dict(missing)) == 0


def test_fluid_vector_unknown_fluid_is_missing(intake_host):
    h = intake_host
    vec, missing = I(h).fluidVector(fluid_lookup(h), mix(h, ("Cola", 0.5), ("Bleach", 0.5)), 0.4)
    assert list(as_dict(missing).values()) == ["Bleach"]
    assert abs(vec["calories"] - 80) < TOL
    assert abs(vec["water"] - 0.5 * 0.4 * 890) < TOL


def test_fluid_vector_empty_mix(intake_host):
    h = intake_host
    vec, missing = I(h).fluidVector(fluid_lookup(h), h.rt.table(), 0.3)
    assert all(v == 0 for v in as_dict(vec).values())
    assert len(as_dict(missing)) == 0


def test_drink_sentinel_is_a_global_of_its_own(intake_host):
    assert lua51.lua_type(intake_host.G.NR_IntakeDrink_Installed) == "table"
    assert intake_host.G.ISDrinkFluidAction is None


DRINK = r"""
function()
    local IN = NutritionRevamp.server.intake
    local calls = 0
    local cls = {}
    local vUpdate = function(self, delta) calls = calls + 1 return "orig" end
    cls.updateEat = vUpdate
    ISDrinkFluidAction = cls
    local first = IN.installDrink()
    local w = cls.updateEat
    local again = IN.installDrink()
    local same = cls.updateEat == w and w ~= vUpdate
    local before = IN.stats.passthrough
    local r = cls.updateEat({}, 0.5)
    local passed = IN.stats.passthrough - before
    IN.uninstallDrink()
    local restored = cls.updateEat == vUpdate
    ISDrinkFluidAction = nil
    local S = NR_IntakeDrink_Installed
    S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    return first, again, same, r, calls, passed, restored, IN.wrappedDrink
end
"""


def test_drink_install_is_idempotent_and_always_calls_the_original(intake_host):
    first, again, same, r, calls, passed, restored, wrapped = intake_host.rt.eval(DRINK)()
    assert first is True and again is True and same is True
    assert r == "orig" and calls == 1
    assert passed == 1
    assert restored is True
    assert wrapped is False


# --- fix-2: the thirst-only share against the TYPE's script thirst ---------------------------------

def test_fraction_thirst_only_half_against_script_thirst(intake_host):
    frac, share = I(intake_host).fractionOf(0, 0, 0, -0.1, -0.05, -0.1)
    assert abs(frac - 0.5) < TOL and abs(share - 0.5) < TOL


def test_fraction_thirst_only_rest_against_script_thirst(intake_host):
    # the second eat of a half-drunk item: all of what was LEFT (1.0), half of the WHOLE (0.5)
    frac, share = I(intake_host).fractionOf(0, 0, 0, -0.05, 0, -0.1)
    assert abs(frac - 1.0) < TOL and abs(share - 0.5) < TOL


def test_fraction_thirst_only_unknown_script_thirst_falls_back(intake_host):
    # the whole is unknown: share falls back to frac (the named limitation)
    frac, share = I(intake_host).fractionOf(0, 0, 0, -0.05, 0, 0)
    assert abs(frac - 1.0) < TOL and abs(share - 1.0) < TOL


def test_assemble_thirst_only_two_eats_land_the_baseline_once(intake_host):
    # half, then the rest: the whole-instance seed lands 1.0x in total (not 1.5x), the macros land
    # the live (already shrunk) item both times at Eat's own fraction. Plan 11 Task 6: the vector follows the
    # calories Eat delivered, so the instance carries the table's 95 kcal
    h = intake_host
    b1 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=95, carb=0, lip=0, pro=0,
                thirstBefore=-0.1, scriptThirst=-0.1)
    v1, s1, m1, share1, frac1, _t1 = I(h).assemble(b1, 0, lookup(h), -0.05)
    b2 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=47.5, carb=0, lip=0, pro=0,
                thirstBefore=-0.05, scriptThirst=-0.1)
    v2, s2, m2, share2, frac2, _t2 = I(h).assemble(b2, 0, lookup(h), 0)
    assert abs(share1 - 0.5) < TOL and abs(frac1 - 0.5) < TOL
    assert abs(share2 - 0.5) < TOL and abs(frac2 - 1.0) < TOL
    assert abs(v1["fibre"] + v2["fibre"] - 4.4) < TOL
    assert abs(v1["water"] + v2["water"] - 156) < TOL
    assert abs(v1["calories"] - 47.5) < TOL and abs(v2["calories"] - 47.5) < TOL


# --- fix-2: the server path end to end through stand-in Java objects -------------------------------
# NR.call indexes obj[name] and calls it with obj first, so a Lua table of function fields stands in
# for a Java object. The store attaches offline once its records table is pre-set.

STORE = os.path.join(
    REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Store.lua"
)

SERVER_SETUP = r"""
function(nutrients, fluids)
    local NR = NutritionRevamp
    local saved = { isServer = NR.isServer, data = NR.data, getGameTime = getGameTime }
    NR.isServer = function() return true end
    NR.server.store.records = {}
    NR.data = { nutrients = { get = nutrients }, fluids = { get = fluids } }
    getGameTime = function()
        return { getWorldAgeHours = function(self) return 12.5 end }
    end
    return saved
end
"""

SERVER_TEARDOWN = r"""
function(saved)
    local NR = NutritionRevamp
    NR.isServer, NR.data, getGameTime = saved.isServer, saved.data, saved.getGameTime
    NR.server.store.records = nil
    ISEatFoodAction, ISDrinkFluidAction = nil, nil
    for _, S in ipairs({NR_IntakeComplete_Installed, NR_IntakeServerStop_Installed, NR_IntakeDrink_Installed}) do
        S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    end
end
"""

EAT_STUBS = r"""
function(raising)
    local IN = NutritionRevamp.server.intake
    local hung, thirst = -0.16, 0
    local item = {}
    if raising then
        item.getHungChange = function(self) error("stub: getHungChange raised") end
    else
        item.getHungChange = function(self) return hung end
    end
    item.getFullType = function(self) return "Base.Apple" end
    item.getBaseHunger = function(self) return -0.16 end
    item.getCalories = function(self) return 95 end
    item.getCarbohydrates = function(self) return 25.13 end
    item.getLipids = function(self) return 0.31 end
    item.getProteins = function(self) return 0.47 end
    item.isCooked = function(self) return false end
    item.isBurnt = function(self) return false end
    item.isRotten = function(self) return false end
    item.isFrozen = function(self) return false end
    item.getThirstChangeUnmodified = function(self) return thirst end
    item.haveExtraItems = function(self) return false end
    item.getModData = function(self) return {} end
    item.getScriptItem = function(self)
        return { getHungerChange = function(s) return -16 end, getThirstChange = function(s) return 0 end }
    end
    local char = { getUsername = function(self) return "admin" end }
    local calls = 0
    local cls = {}
    cls.complete = function(self) calls = calls + 1 hung = 0 return true end
    cls.serverStop = function(self) end
    ISEatFoodAction = cls
    local before = { eats = IN.stats.eats, landed = IN.stats.landed, failures = IN.stats.failures }
    IN.install()
    local r = cls.complete({ item = item, character = char })
    local rec = NutritionRevamp.server.store.records.admin
    return r, calls, before, rec, IN.lastError
end
"""

DRINK_STUBS = r"""
function()
    local IN = NutritionRevamp.server.intake
    local amount = 0.3
    local released = 0
    local fluid = { getFluidTypeString = function(self) return "Cola" end }
    local sample = {
        size = function(self) return 1 end,
        getFluid = function(self, i) return fluid end,
        getPercentage = function(self, i) return 1.0 end,
        release = function(self) released = released + 1 end,
    }
    local fc = {
        getAmount = function(self) return amount end,
        createFluidSample = function(self) return sample end,
    }
    local item = { getFullType = function(self) return "Base.Pop" end }
    local char = { getUsername = function(self) return "admin" end }
    local calls = 0
    local cls = {}
    cls.updateEat = function(self, delta) calls = calls + 1 amount = 0 return "orig" end
    ISDrinkFluidAction = cls
    local before = { sips = IN.stats.sips, landed = IN.stats.landed }
    IN.installDrink()
    local r = cls.updateEat({ item = item, fluidContainer = fc, character = char }, 1)
    local rec = NutritionRevamp.server.store.records.admin
    local expected = IN.fluidVector(NutritionRevamp.data.fluids.get, { { "Cola", 1.0 } }, 0.3)
    return r, calls, before, rec, NutritionRevamp.kernel.stomach.bulkOf(expected), released
end
"""


@pytest.fixture
def server_host(intake_host):
    h = intake_host
    with open(STORE, encoding="utf-8") as fh:
        src = fh.read()
    h.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Server_Store.lua")()
    saved = h.rt.eval(SERVER_SETUP)(lookup(h), fluid_lookup(h))
    try:
        yield h
    finally:
        h.rt.eval(SERVER_TEARDOWN)(saved)


def test_server_path_eat_lands_in_the_stomach(server_host):
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(EAT_STUBS)(False)
    stats = I(h).stats
    assert r is True and calls == 1
    assert rec is not None, err
    assert rec["stomach"]["bulk"] > 0
    assert stats.eats == before_stats["eats"] + 1
    assert stats.landed == before_stats["landed"] + 1
    assert stats.failures == before_stats["failures"]
    assert rec["lastIntake"]["source"] == "baseline"
    assert abs(rec["lastIntake"]["share"] - 1.0) < TOL
    assert rec["firstSeen"] == 12.5


def test_server_path_drink_lands_the_cola(server_host):
    h = server_host
    r, calls, before_stats, rec, expected_bulk, released = h.rt.eval(DRINK_STUBS)()
    stats = I(h).stats
    assert r == "orig" and calls == 1
    assert rec is not None, I(h).lastError
    assert expected_bulk > 0
    # a fresh record's stomach is seeded FULL on creation (the Task 11 game choice, mirrored in the
    # intake landing), so the landed bulk is the seed plus the meal
    full_bulk = h.K.stomach.FULL_BULK
    assert abs(rec["stomach"]["bulk"] - (full_bulk + expected_bulk)) < TOL
    assert stats.sips == before_stats["sips"] + 1
    assert stats.landed == before_stats["landed"] + 1
    assert rec["lastIntake"]["source"] == "fluid"
    assert abs(rec["lastIntake"]["litres"] - 0.3) < TOL
    assert released == 1


def test_server_path_raising_capture_still_runs_the_original(server_host):
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(EAT_STUBS)(True)
    stats = I(h).stats
    assert r is True and calls == 1
    assert stats.failures == before_stats["failures"] + 1
    assert err is not None and "getHungChange raised" in str(err)
    assert stats.landed == before_stats["landed"]
    assert rec is None


# --- fix-3: a finished item reads NaN (#2832); nothing non-finite lands (#2833) -------------------

NAN = float("nan")
INF = float("inf")


@pytest.mark.parametrize("x,ok", [(1.0, True), (0, True), (-0.16, True), (NAN, False), (INF, False),
                                  (-INF, False), (None, False), ("1", False)])
def test_is_finite(intake_host, x, ok):
    assert I(intake_host).isFinite(x) is ok


def test_after_reading_nan_is_finished(intake_host):
    assert I(intake_host).afterReading(-0.04, NAN) == 0


@pytest.mark.parametrize("after", [None, INF, "x"])
def test_after_reading_unreadable_is_finished(intake_host, after):
    assert I(intake_host).afterReading(-0.04, after) == 0


def test_after_reading_finite_passes_through(intake_host):
    assert abs(I(intake_host).afterReading(-0.16, -0.08) - (-0.08)) < TOL


def test_after_reading_non_numeric_before_passes_through(intake_host):
    assert I(intake_host).afterReading(None, None) is None


def test_first_non_finite_names_the_key(intake_host):
    h = intake_host
    v = h.K.vector.new()
    assert I(h).firstNonFinite(v) is None
    v["iron"] = NAN
    assert I(h).firstNonFinite(v) == "iron"


def test_assemble_nan_share_lands_nothing(intake_host):
    h = intake_host
    vec, source, missing, share, frac, _trace = I(h).assemble(before(h), NAN, lookup(h))
    assert vec is None


NAN_EAT_STUBS = r"""
function(mode)
    local IN = NutritionRevamp.server.intake
    local hung = -0.16
    local cal = 95
    if mode == "finish" then hung = -0.04 cal = 95 * 0.25 end
    local item = {}
    item.getHungChange = function(self) return hung end
    item.getFullType = function(self) return "Base.Apple" end
    item.getBaseHunger = function(self) return -0.16 end
    if mode == "nancal" then
        item.getCalories = function(self) return 0 / 0 end
    else
        item.getCalories = function(self) return cal end
    end
    item.getCarbohydrates = function(self) return 25.13 end
    item.getLipids = function(self) return 0.31 end
    item.getProteins = function(self) return 0.47 end
    item.isCooked = function(self) return false end
    item.isBurnt = function(self) return false end
    item.isRotten = function(self) return false end
    item.isFrozen = function(self) return false end
    item.getThirstChangeUnmodified = function(self) return 0 end
    item.haveExtraItems = function(self) return false end
    item.getModData = function(self) return {} end
    item.getScriptItem = function(self)
        return { getHungerChange = function(s) return -16 end, getThirstChange = function(s) return 0 end }
    end
    local char = { getUsername = function(self) return "admin" end }
    local calls = 0
    local cls = {}
    -- vanilla Eat at fraction 1: hungChange 0, then consumeHunger(0) divides 0 by 0 (#2832)
    cls.complete = function(self)
        calls = calls + 1
        if mode == "finish" then hung = 0 / 0 else hung = 0 end
        return true
    end
    cls.serverStop = function(self) end
    ISEatFoodAction = cls
    local before = { eats = IN.stats.eats, landed = IN.stats.landed, failures = IN.stats.failures }
    IN.lastError = nil
    IN.install()
    local r = cls.complete({ item = item, character = char })
    local rec = NutritionRevamp.server.store.records.admin
    return r, calls, before, rec, IN.lastError
end
"""


def test_server_path_finishing_eat_reading_nan_lands_the_remainder(server_host):
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(NAN_EAT_STUBS)("finish")
    stats = I(h).stats
    assert r is True and calls == 1
    assert rec is not None, err
    assert stats.landed == before_stats["landed"] + 1
    assert stats.failures == before_stats["failures"]
    li = rec["lastIntake"]
    assert abs(li["share"] - 0.25) < TOL
    assert abs(li["frac"] - 1.0) < TOL
    buf = rec["stomach"]["buffer"]
    assert abs(buf["calories"] - 23.75) < TOL      # the live (shrunk) calories x frac 1
    assert abs(buf["fibre"] - 1.1) < TOL           # the whole-instance seed x share 0.25
    assert abs(buf["water"] - 39.0) < TOL
    for k in h.K.vector.KEYS.values():
        assert buf[k] == buf[k], k
        assert rec["pool"][k] == rec["pool"][k], k
    full = h.K.stomach.FULL_BULK
    assert abs(rec["stomach"]["bulk"] - (full + 0.2375 + 0.55 + 0.39)) < TOL


def test_server_path_nan_calories_rejected_nothing_landed(server_host):
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(NAN_EAT_STUBS)("nancal")
    stats = I(h).stats
    assert r is True and calls == 1                 # the original still ran, once
    assert stats.landed == before_stats["landed"]
    assert stats.failures == before_stats["failures"] + 1
    assert err == "non-finite intake rejected: calories"
    assert rec is None


# --- close fix wave (f): an UNREADABLE after-read is treated as finished but counted and named ----

UNREADABLE_EAT_STUBS = r"""
function()
    local IN = NutritionRevamp.server.intake
    local hung = -0.04
    local after = false
    local item = {}
    -- readable before the original, nil only after it (an unreadable after-read, not the NaN)
    item.getHungChange = function(self) if after then return nil end return hung end
    item.getFullType = function(self) return "Base.Apple" end
    item.getBaseHunger = function(self) return -0.16 end
    item.getCalories = function(self) return 95 * 0.25 end
    item.getCarbohydrates = function(self) return 25.13 end
    item.getLipids = function(self) return 0.31 end
    item.getProteins = function(self) return 0.47 end
    item.isCooked = function(self) return false end
    item.isBurnt = function(self) return false end
    item.isRotten = function(self) return false end
    item.isFrozen = function(self) return false end
    item.getThirstChangeUnmodified = function(self) return 0 end
    item.haveExtraItems = function(self) return false end
    item.getModData = function(self) return {} end
    item.getScriptItem = function(self)
        return { getHungerChange = function(s) return -16 end, getThirstChange = function(s) return 0 end }
    end
    local char = { getUsername = function(self) return "admin" end }
    local calls = 0
    local cls = {}
    cls.complete = function(self)
        calls = calls + 1
        after = true
        return true
    end
    cls.serverStop = function(self) end
    ISEatFoodAction = cls
    local before = { landed = IN.stats.landed, failures = IN.stats.failures, unreadable = IN.stats.unreadableAfter }
    IN.lastError = nil
    IN.install()
    local r = cls.complete({ item = item, character = char })
    local rec = NutritionRevamp.server.store.records.admin
    return r, calls, before, rec, IN.lastError
end
"""


def test_is_unreadable_after(intake_host):
    IN = I(intake_host)
    assert IN.isUnreadableAfter(-0.04, None) is True
    assert IN.isUnreadableAfter(-0.04, "x") is True
    assert IN.isUnreadableAfter(-0.04, NAN) is False     # the known vanilla 0/0 (#2832): silent
    assert IN.isUnreadableAfter(-0.04, INF) is False
    assert IN.isUnreadableAfter(-0.04, 0) is False
    assert IN.isUnreadableAfter(None, None) is False     # no numeric before: passed through, not counted


def test_server_path_unreadable_after_lands_the_remainder_and_is_counted(server_host):
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(UNREADABLE_EAT_STUBS)()
    stats = I(h).stats
    assert r is True and calls == 1
    assert rec is not None, err
    assert stats.landed == before_stats["landed"] + 1
    assert stats.failures == before_stats["failures"]
    assert stats.unreadableAfter == before_stats["unreadable"] + 1
    assert err == "after-read unreadable; treated as finished: Base.Apple"
    li = rec["lastIntake"]
    assert abs(li["share"] - 0.25) < TOL                  # the whole remainder: -0.04 of -0.16
    assert abs(li["frac"] - 1.0) < TOL


RAISING_AFTER_EAT_STUBS = UNREADABLE_EAT_STUBS.replace(
    "if after then return nil end return hung end",
    "if after then error(\"getHungChange raised\") end return hung end",
)


def test_server_path_raising_after_read_is_a_failure_not_unreadable(server_host):
    # a RAISING after-read is not the unreadable (nil) case: read() is a plain call inside
    # readAfterAndLand, so the raise reaches guardAfter's pcall -> nothing lands, failures +1,
    # unreadableAfter unchanged, lastError the raise
    h = server_host
    r, calls, before_stats, rec, err = h.rt.eval(RAISING_AFTER_EAT_STUBS)()
    assert r is True and calls == 1                     # the original still ran and its value passed
    assert rec is None
    assert I(h).stats.failures == before_stats["failures"] + 1
    assert I(h).stats.landed == before_stats["landed"]
    assert I(h).stats.unreadableAfter == before_stats["unreadable"]
    assert "getHungChange raised" in err


def test_server_path_nan_after_read_is_not_counted_unreadable(server_host):
    h = server_host
    u0 = I(h).stats.unreadableAfter
    r, calls, before_stats, rec, err = h.rt.eval(NAN_EAT_STUBS)("finish")
    assert rec is not None, err
    assert I(h).stats.unreadableAfter == u0
    assert err is None


# --- Plan 4 Task 12: the acute test, the B12 ceiling, the per-minute ingested sum ----------------

SHARED_DIR = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
RECORDS_FILE = os.path.join(SHARED_DIR, "NR_Data_Records.lua")


@pytest.fixture
def rec_host(intake_host):
    h = intake_host
    with open(RECORDS_FILE, encoding="utf-8") as fh:
        src = fh.read()
    h.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@NR_Data_Records.lua")()
    I(h).lastIngested = h.rt.table()
    try:
        yield h
    finally:
        I(h).lastIngested = h.rt.table()


def _records(h):
    return h.G.NutritionRevamp.data.records


def _record(h, fill=0.8, fm=16.0, lm=64.0):
    body = tbl(h, {"fm": fm, "lm": lm})
    return tbl(h, {"body": body, "stomachFill": fill})


def _vec(h, **kw):
    v = h.K.vector.new()
    for k, val in kw.items():
        v[k] = val
    return v


def test_acute_flags_a_1600_mg_iron_eat_at_80_kg(rec_host):
    h = rec_host
    record = _record(h)
    n = I(h).acuteAtEat(record, _vec(h, iron=1600.0), _records(h))
    assert n == 1
    st = record["nutrients"]["iron"]
    assert st["ax"] == 48 and st["axr"] == 2


def test_acute_below_the_threshold_flags_nothing(rec_host):
    h = rec_host
    record = _record(h)
    assert I(h).acuteAtEat(record, _vec(h, iron=1500.0), _records(h)) == 0
    assert record["nutrients"]["iron"]["ax"] == 0


def test_acute_empty_stomach_multiplies_the_dose(rec_host):
    h = rec_host
    # 1100 mg / 80 kg = 13.75 mg/kg; x1.5 on a stomach below 0.2 = 20.6 -> rung 2
    record = _record(h, fill=0.1)
    assert I(h).acuteAtEat(record, _vec(h, iron=1100.0), _records(h)) == 1
    assert record["nutrients"]["iron"]["axr"] == 2
    # 3300 mg = 41.25 mg/kg x 1.5 = 61.9 -> rung 3
    record = _record(h, fill=0.1)
    I(h).acuteAtEat(record, _vec(h, iron=3300.0), _records(h))
    assert record["nutrients"]["iron"]["axr"] == 3


def test_acute_preformed_retinol_reads_the_vitA_record(rec_host):
    h = rec_host
    record = _record(h)
    assert I(h).acuteAtEat(record, _vec(h, retinol=90000.0, carotene=1e6), _records(h)) == 1
    assert record["nutrients"]["vitA"]["axr"] == 2 and record["nutrients"]["vitA"]["ax"] == 48


def test_acute_keeps_a_live_higher_rung(rec_host):
    h = rec_host
    record = _record(h)
    I(h).acuteAtEat(record, _vec(h, iron=5000.0), _records(h))          # 62.5 mg/kg -> rung 3
    record["nutrients"]["iron"]["ax"] = 10
    I(h).acuteAtEat(record, _vec(h, iron=1600.0), _records(h))          # rung 2 while 3 is live
    st = record["nutrients"]["iron"]
    assert st["axr"] == 3 and st["ax"] == 48


def test_acute_without_a_body_or_records_tests_nothing(rec_host):
    h = rec_host
    assert I(h).acuteAtEat(tbl(h, {}), _vec(h, iron=1e6), _records(h)) == 0
    assert I(h).acuteAtEat(_record(h, fm=0.0, lm=0.0), _vec(h, iron=1e6), _records(h)) == 0
    saved = h.G.NutritionRevamp.data.records
    h.G.NutritionRevamp.data.records = None
    try:
        assert I(h).acuteAtEat(_record(h), _vec(h, iron=1e6)) == 0
    finally:
        h.G.NutritionRevamp.data.records = saved


def test_acute_nan_fill_reads_full(rec_host):
    h = rec_host
    record = _record(h, fill=float("nan"))
    assert I(h).acuteAtEat(record, _vec(h, iron=1100.0), _records(h)) == 0   # 13.75 mg/kg, no x1.5


def test_land_caps_b12_and_sums_the_ingested_amount(rec_host):
    h = rec_host
    record = _record(h)
    record["stomach"] = h.K.stomach.new()
    vec = _vec(h, vitB12=25.0, iron=1600.0)
    I(h).land(record, "u", vec)
    assert abs(vec["vitB12"] - 2.252) < 1e-12                          # min(12.5, 2) + 0.012 x 21
    assert abs(record["stomach"]["buffer"]["vitB12"] - 2.252) < 1e-12
    assert I(h).lastIngested["u"]["vitB12"] == 25.0                     # the ingested amount, pre-ceiling
    assert record["nutrients"]["iron"]["axr"] == 2                      # the landing ran the acute test


def test_land_survives_a_raising_acute_test(rec_host):
    h = rec_host
    record = _record(h)
    record["stomach"] = h.K.stomach.new()
    record["body"]["fm"] = "x"                                          # (fm or 0) + lm raises
    f0 = I(h).stats.acuteFailures
    I(h).land(record, "u", _vec(h, water=500.0))
    assert I(h).stats.acuteFailures == f0 + 1
    assert record["stomach"]["buffer"]["water"] == 500.0
    I(h).lastError = None


def test_land_diverts_ethanol_and_caffeine_to_the_gut_lane(rec_host):
    # ruling T17-2: the landing sends ethanol and caffeine to the pending gut sums, never the stomach;
    # the ingested sum (the excess ladder, alcDay) keeps them
    h = rec_host
    record = _record(h)
    record["stomach"] = h.K.stomach.new()
    IN = I(h)
    IN.lastIngested["g"] = None
    IN.pendingAlc["g"] = None
    IN.pendingCaf["g"] = None
    try:
        IN.land(record, "g", _vec(h, ethanol=10.0, caffeine=50.0, water=300.0))
        assert record["stomach"]["buffer"]["ethanol"] == 0
        assert record["stomach"]["buffer"]["caffeine"] == 0
        assert record["stomach"]["buffer"]["water"] == 300.0
        assert IN.pendingAlc["g"] == 10.0 and IN.pendingCaf["g"] == 50.0
        assert IN.lastIngested["g"]["ethanol"] == 10.0 and IN.lastIngested["g"]["caffeine"] == 50.0
        IN.land(record, "g", _vec(h, ethanol=2.0))         # a second landing in the minute adds
        assert IN.pendingAlc["g"] == 12.0 and IN.pendingCaf["g"] == 50.0
    finally:
        IN.lastIngested["g"] = None
        IN.pendingAlc["g"] = None
        IN.pendingCaf["g"] = None


def test_limitations_name_the_gut_lane_window(intake_host):
    lims = list(I(intake_host).limitations.values())
    assert "a landed vector's ethanol and caffeine wait in a transient server table until the next slow minute moves them to record.acute: a server stop in that minute loses them (the ingested day totals keep them)" in lims


def test_last_ingested_sums_two_eats_and_clears(rec_host):
    h = rec_host
    s1 = I(h).addIngested("u", _vec(h, calories=100.0, ethanol=14.0))
    s2 = I(h).addIngested("u", _vec(h, calories=50.0, iron=2.0))
    same = h.rt.eval("function(a, b) return rawequal(a, b) end")
    assert same(s1, s2)                                                 # one table per username per minute
    got = I(h).lastIngested["u"]
    assert got["calories"] == 150.0 and got["ethanol"] == 14.0 and got["iron"] == 2.0
    keys = list(h.K.vector.KEYS.values())
    assert set(keys) <= set(as_dict(got))
    I(h).lastIngested["u"] = None                                       # the adapter's read-and-clear
    s3 = I(h).addIngested("u", _vec(h, calories=10.0))
    assert not same(s3, s1) and I(h).lastIngested["u"]["calories"] == 10.0


def test_last_ingested_is_the_name_the_nutrients_adapter_reads():
    src = open(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server",
                            "NR_Server_Nutrients.lua"), encoding="utf-8").read()
    assert "intake.lastIngested[username]" in src
    assert "intake.lastIngested[username] = nil" in src


# --- the world-water wrapper: ISTakeWaterAction.transferFluid ----------------------------------

def test_world_sentinel_is_a_global_of_its_own(intake_host):
    assert lua51.lua_type(intake_host.G.NR_IntakeWorld_Installed) == "table"
    assert intake_host.G.ISTakeWaterAction is None
    assert I(intake_host).installWorld() is False


WORLD = r"""
function()
    local IN = NutritionRevamp.server.intake
    local calls = 0
    local cls = {}
    local vTransfer = function(self, amount) calls = calls + 1 return "orig" end
    cls.transferFluid = vTransfer
    ISTakeWaterAction = cls
    local first = IN.installWorld()
    local w = cls.transferFluid
    local again = IN.installWorld()
    local same = cls.transferFluid == w and w ~= vTransfer
    local before = IN.stats.passthrough
    local r = cls.transferFluid({}, 0.5)
    local passed = IN.stats.passthrough - before
    IN.uninstallWorld()
    local restored = cls.transferFluid == vTransfer
    ISTakeWaterAction = nil
    local S = NR_IntakeWorld_Installed
    S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    return first, again, same, r, calls, passed, restored, IN.wrappedWorld
end
"""


def test_world_install_is_idempotent_and_always_calls_the_original(intake_host):
    first, again, same, r, calls, passed, restored, wrapped = intake_host.rt.eval(WORLD)()
    assert first is True and again is True and same is True
    assert r == "orig" and calls == 1
    assert passed == 1
    assert restored is True
    assert wrapped is False


WORLD_STUBS = r"""
function(amount, avail, withItem)
    local IN = NutritionRevamp.server.intake
    local source = { getFluidAmount = function(self) return avail end }
    local char = { getUsername = function(self) return "admin" end }
    local calls, seen = 0, nil
    local cls = {}
    cls.transferFluid = function(self, a) calls = calls + 1 seen = a avail = avail - math.min(a, avail) return nil end
    ISTakeWaterAction = cls
    local before = { worldSips = IN.stats.worldSips, landed = IN.stats.landed }
    IN.installWorld()
    local action = { character = char, waterObject = source }
    if withItem then action.item = {} end
    cls.transferFluid(action, amount)
    local rec = NutritionRevamp.server.store.records.admin
    ISTakeWaterAction = nil
    local S = NR_IntakeWorld_Installed
    S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    return calls, seen, before, rec
end
"""


def test_world_water_step_lands_its_litres(server_host):
    h = server_host
    I(h).lastIngested = h.rt.table()
    calls, seen, before_stats, rec = h.rt.eval(WORLD_STUBS)(0.25, 3.0, False)
    assert calls == 1 and seen == 0.25                                 # the original ran with its argument
    assert rec is not None, I(h).lastError
    assert I(h).stats.worldSips == before_stats["worldSips"] + 1
    assert I(h).stats.landed == before_stats["landed"] + 1
    assert rec["lastIntake"]["source"] == "world"
    assert abs(rec["lastIntake"]["litres"] - 0.25) < TOL
    assert abs(rec["stomach"]["buffer"]["water"] - 250.0) < TOL         # the stub's Water seed: 1000 g per litre
    assert abs(I(h).lastIngested["admin"]["water"] - 250.0) < TOL
    I(h).lastIngested = h.rt.table()


def test_world_water_step_is_clamped_to_the_source(server_host):
    h = server_host
    calls, seen, before_stats, rec = h.rt.eval(WORLD_STUBS)(0.8, 0.3, False)
    assert calls == 1
    assert abs(rec["lastIntake"]["litres"] - 0.3) < TOL
    I(h).lastIngested = h.rt.table()


@pytest.mark.parametrize("amount,avail,with_item", [(0.25, 3.0, True), (0.0, 3.0, False), (0.25, 0.0, False)])
def test_world_water_fill_or_empty_lands_nothing(server_host, amount, avail, with_item):
    h = server_host
    calls, seen, before_stats, rec = h.rt.eval(WORLD_STUBS)(amount, avail, with_item)
    assert calls == 1                                                   # the original always runs
    assert rec is None
    assert I(h).stats.landed == before_stats["landed"]


def test_world_water_uses_the_water_seed_when_the_data_has_it(server_host):
    h = server_host
    water_seed = h.rt.eval("function() local v = NutritionRevamp.kernel.vector.new() v.water = 1000 v.sodium = 10 return v end")()
    h.G.NutritionRevamp.data.fluids.get = h.rt.eval("function(seed) return function(t) if t == 'Water' then return seed end return nil end end")(water_seed)
    calls, seen, before_stats, rec = h.rt.eval(WORLD_STUBS)(0.5, 3.0, False)
    assert abs(rec["stomach"]["buffer"]["water"] - 500.0) < TOL
    assert abs(rec["stomach"]["buffer"]["sodium"] - 5.0) < TOL
    I(h).lastIngested = h.rt.table()


CAP_STUBS = r"""
function(waterUnit, steps, step)
    local IN = NutritionRevamp.server.intake
    local source = { getFluidAmount = function(self) return 9.0 end }
    local char = { getUsername = function(self) return "admin" end }
    local cls = {}
    cls.transferFluid = function(self, a) return nil end
    ISTakeWaterAction = cls
    IN.installWorld()
    local action = { character = char, waterObject = source, waterUnit = waterUnit }
    local per = {}
    for i = 1, steps do
        local rec0 = NutritionRevamp.server.store.records.admin
        local before = (rec0 ~= nil and rec0.lastIntake ~= nil and rec0.lastIntake.litres) or 0
        local landedBefore = IN.stats.landed
        cls.transferFluid(action, step)
        per[i] = (IN.stats.landed - landedBefore)
    end
    local nr = action.nrLanded or 0
    ISTakeWaterAction = nil
    local S = NR_IntakeWorld_Installed
    S.wrapper, S.class, S.orig, S.off = nil, nil, nil, nil
    return nr, per[1], per[2], per[3]
end
"""


def test_world_water_is_capped_at_the_actions_planned_litres(server_host):
    h = server_host
    nr, p1, p2, p3 = h.rt.eval(CAP_STUBS)(0.8, 3, 0.5)
    assert abs(nr - 0.8) < TOL                                          # 0.5 + 0.3, then nothing
    assert (p1, p2, p3) == (1, 1, 0)                                    # the third step lands nothing
    I(h).lastIngested = h.rt.table()


def test_world_water_without_a_waterunit_is_uncapped(server_host):
    h = server_host
    nr, p1, p2, p3 = h.rt.eval(CAP_STUBS)(None, 3, 0.5)
    assert abs(nr - 1.5) < TOL and (p1, p2, p3) == (1, 1, 1)
    I(h).lastIngested = h.rt.table()


def test_limitations_name_the_world_water_window(intake_host):
    lims = list(I(intake_host).limitations.values())
    assert "a world-water drink lands at most the action's planned litres (waterUnit, sized from THIRST at its start); while the view holds THIRST, vanilla's updateUse re-transfers its cumulative target, so the SOURCE can lose more than was landed until the slow clock lands the water" in lims


# --- Plan 6 Task 10: the chain declared -> table -> inferred -> missing (rulings 13-14) -------------

TEMPLATES = {
    "Fruits": {"n": 3, "density": {"fibre": 0.04, "water": 1.5, "vitC": 0.1}},
    "_default": {"n": 9, "density": {"fibre": 0.01, "water": 0.5, "iron": 0.005}},
}

INFO_STUB = r"""
function(infos)
    return function(fullType) return infos[fullType] end
end
"""


def templates(h):
    return h.table(TEMPLATES)


def info_of(h, infos):
    return h.rt.eval(INFO_STUB)(h.table(infos))


def trace_list(trace, name):
    return list(as_dict(trace[name]).values())


def test_source_declared_and_inferred_follow_dish_and_craft(intake_host):
    IN = I(intake_host)
    assert IN.sourceOf(False, False, "declared") == "declared"
    assert IN.sourceOf(False, False, "inferred") == "inferred"
    assert IN.sourceOf(False, False, "table") == "baseline"
    assert IN.sourceOf(False, False, "missing") == "baseline"
    assert IN.sourceOf(True, False, "declared") == "dish"
    assert IN.sourceOf(False, True, "inferred") == "craft"


def test_chain_one_declared_wins_over_the_table_and_takes_the_items_macros(intake_host):
    h = intake_host
    info = h.table({"declared": "fibre:12;vitC:3;calories:999",
                    "macros": {"calories": 95, "carbs": 25.13, "lipids": 0.31, "proteins": 0.47}})
    vec, step, note = I(h).chainOne("Base.Apple", lookup(h), templates(h), info)
    assert step == "declared"
    assert vec["fibre"] == 12 and vec["vitC"] == 3
    assert vec["calories"] == 95 and vec["carbs"] == 25.13          # the script block owns the macros
    assert vec["water"] == 0                                         # the table's 156 g not consulted
    assert len(as_dict(note)) == 0


def test_chain_one_malformed_declared_falls_through_to_the_table_with_its_reason(intake_host):
    h = intake_host
    info = h.table({"declared": "fibre:lots", "macros": {"calories": 95}})
    vec, step, note = I(h).chainOne("Base.Apple", lookup(h), templates(h), info)
    assert step == "table"
    assert abs(vec["fibre"] - 4.4) < TOL
    assert isinstance(note, str) and "fibre:lots" in note


def test_chain_one_table_wins_over_inference(intake_host):
    h = intake_host
    info = h.table({"foodType": "Fruits", "macros": {"calories": 95, "carbs": 25.13}})
    vec, step, note = I(h).chainOne("Base.Apple", lookup(h), templates(h), info)
    assert step == "table"
    assert abs(vec["water"] - 156) < TOL
    assert note is None


def test_chain_one_untabled_with_macros_and_a_type_infers(intake_host):
    h = intake_host
    info = h.table({"foodType": "Fruits", "macros": {"calories": 50, "carbs": 12, "lipids": 0, "proteins": 1}})
    vec, step, note = I(h).chainOne("Base.Kiwi", lookup(h), templates(h), info)
    assert step == "inferred"
    assert abs(vec["fibre"] - 2.0) < TOL and abs(vec["vitC"] - 5.0) < TOL
    assert vec["calories"] == 50 and vec["carbs"] == 12


def test_chain_one_nothing_to_go_on_is_missing(intake_host):
    h = intake_host
    for info in (None, h.table({"foodType": "Fruits", "macros": {"calories": 0}}), h.table({"foodType": "Fruits"})):
        vec, step, note = I(h).chainOne("Base.Kiwi", lookup(h), templates(h), info)
        assert vec is None and step == "missing"
    info = h.table({"foodType": "Fruits", "macros": {"calories": 50}})
    vec, step, note = I(h).chainOne("Base.Kiwi", lookup(h), None, info)      # no templates loaded
    assert vec is None and step == "missing"


def test_chain_one_reports_unknown_declared_keys(intake_host):
    h = intake_host
    info = h.table({"declared": "fibre:2;vitZ:1", "macros": {"calories": 10}})
    vec, step, note = I(h).chainOne("Base.Kiwi", lookup(h), templates(h), info)
    assert step == "declared"
    assert list(as_dict(note).values()) == ["vitZ"]


def test_assemble_declared_item_wins_over_the_table(intake_host):
    h = intake_host
    b = before(h)
    b["declared"] = "fibre:12;vitC:3"
    vec, source, missing, share, frac, trace = I(h).assemble(b, -0.08, lookup(h), None, templates(h))
    assert source == "declared"
    assert abs(vec["fibre"] - 6.0) < TOL and abs(vec["vitC"] - 1.5) < TOL
    assert vec["water"] == 0
    assert close(macros(vec), [47.5, 12.565, 0.155, 0.235])
    assert len(as_dict(missing)) == 0
    assert trace_list(trace, "declared") == ["Base.Apple"]


def test_assemble_a_table_hit_wins_over_inference(intake_host):
    h = intake_host
    b = before(h, foodType="Fruits")
    vec, source, missing, share, frac, trace = I(h).assemble(b, -0.08, lookup(h), None, templates(h))
    assert source == "baseline"
    assert abs(vec["fibre"] - 2.2) < TOL
    assert trace_list(trace, "inferred") == []


def test_assemble_an_untabled_item_with_macros_and_a_type_infers(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Kiwi", foodType="Fruits", cal=50, carb=12, lip=0.4, pro=1)
    vec, source, missing, share, frac, trace = I(h).assemble(b, -0.08, lookup(h), None, templates(h))
    assert source == "inferred"
    assert abs(frac - 0.5) < TOL
    assert abs(vec["fibre"] - 0.04 * 50 * 0.5) < TOL
    assert abs(vec["vitC"] - 0.1 * 50 * 0.5) < TOL
    assert close(macros(vec), [25, 6, 0.2, 0.5])
    assert len(as_dict(missing)) == 0
    assert trace_list(trace, "inferred") == ["Base.Kiwi"]


def test_assemble_an_inferred_item_reads_the_live_macros_at_frac(intake_host):
    # the second half of a part-eaten untabled item: the live macros are already halved, so the
    # inferred vector takes Eat's own fraction of what was LEFT (1.0), never the whole-instance share
    h = intake_host
    b = before(h, fullType="Base.Kiwi", rawBefore=-0.08, cal=25, carb=6, lip=0.2, pro=0.5)
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h), None, templates(h))
    assert source == "inferred"
    assert abs(share - 0.5) < TOL and abs(frac - 1.0) < TOL
    assert abs(vec["iron"] - 0.005 * 25) < TOL                       # `_default`: no FoodType
    assert close(macros(vec), [25, 6, 0.2, 0.5])


def test_assemble_untabled_without_templates_is_missing_as_before(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Kiwi", foodType="Fruits")
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h))
    assert source == "baseline"
    assert list(as_dict(missing).values()) == ["Base.Kiwi"]
    assert vec["fibre"] == 0


def test_assemble_a_malformed_declared_item_falls_through_and_is_traced(intake_host):
    h = intake_host
    b = before(h)
    b["declared"] = "fibre=12"
    vec, source, missing, share, frac, trace = I(h).assemble(b, -0.08, lookup(h), None, templates(h))
    assert source == "baseline"
    assert abs(vec["fibre"] - 2.2) < TOL
    bad = trace_list(trace, "malformed")
    assert len(bad) == 1 and bad[0].startswith("Base.Apple: ")


def test_assemble_a_craft_map_with_one_untabled_input_infers_it(intake_host):
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 1, "Base.Kiwi": 2})
    info = info_of(h, {"Base.Kiwi": {"foodType": "Fruits",
                                      "macros": {"calories": 50, "carbs": 12, "lipids": 0, "proteins": 1}}})
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h), None, templates(h), info)
    assert source == "craft"
    assert abs(vec["iron"] - 2) < TOL                                # the tabled input
    assert abs(vec["fibre"] - 2 * 0.04 * 50) < TOL                   # two inferred Kiwis
    assert len(as_dict(missing)) == 0
    assert trace_list(trace, "inferred") == ["Base.Kiwi"]
    assert close(macros(vec), [200, 0, 10, 40])


def test_assemble_a_craft_input_declared_wins_over_its_table_entry(intake_host):
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = tbl(h, {"Base.MincedMeat": 1})
    info = info_of(h, {"Base.MincedMeat": {"declared": "iron:7", "macros": {"calories": 200}}})
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h), None, templates(h), info)
    assert abs(vec["iron"] - 7) < TOL
    assert trace_list(trace, "declared") == ["Base.MincedMeat"]


def test_assemble_a_craft_input_with_nothing_to_go_on_stays_missing(intake_host):
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = tbl(h, {"Base.Nothing": 1})
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h), None, templates(h), info_of(h, {}))
    assert list(as_dict(missing).values()) == ["Base.Nothing"]


def test_assemble_a_dish_ingredient_goes_through_the_chain(intake_host):
    h = intake_host
    b = before(h, fullType="Base.Salad", rawBefore=-0.3, instBase=-0.3, scriptHunger=-0.3, cal=145, carb=37.13, lip=0.31, pro=1.47)
    extra = h.rt.table()
    extra[1] = "Base.Apple"
    extra[2] = "Base.Kiwi"
    b["extraTypes"] = extra
    info = info_of(h, {"Base.Kiwi": {"foodType": "Fruits",
                                      "macros": {"calories": 50, "carbs": 12, "lipids": 0, "proteins": 1}}})
    vec, source, missing, share, frac, trace = I(h).assemble(b, 0, lookup(h), None, templates(h), info)
    assert source == "dish"
    # scratch macro total: apple 120.91 + kiwi 63 = 183.91 = the dish's own, so scale 1
    assert abs(vec["fibre"] - 6.4) < 1e-6
    assert len(as_dict(missing)) == 0
    assert trace_list(trace, "inferred") == ["Base.Kiwi"]


def test_declared_of_reads_the_string_key_only(intake_host):
    h = intake_host
    IN = I(h)
    assert IN.declaredOf(tbl(h, {"NR_Nutrients": "fibre:1"})) == "fibre:1"
    assert IN.declaredOf(tbl(h, {"NR_Nutrients": 3.0})) is None       # a Double: not the contract
    assert IN.declaredOf(tbl(h, {})) is None
    assert IN.declaredOf(None) is None


def test_limitations_name_the_inference_and_the_declared_contract(intake_host):
    lims = list(I(intake_host).limitations.values())
    assert ("a food outside the table takes a vector inferred from its FoodType's per-kcal medians over the "
            "pass's own mapped records (NR_Data_Infer.lua; a judgement); a declared NR_Nutrients script key "
            "(unrecognised by the loader, landing in default modData — #1281) takes precedence and its "
            "macros are the item's own") in lims


CHAIN_EAT = r"""
function(fullType, md, foodType, cal, infer)
    local IN = NutritionRevamp.server.intake
    NutritionRevamp.data.infer = infer
    local hung = -0.16
    local item = {}
    item.getHungChange = function(self) return hung end
    item.getFullType = function(self) return fullType end
    item.getBaseHunger = function(self) return -0.16 end
    item.getCalories = function(self) return cal end
    item.getCarbohydrates = function(self) return 10 end
    item.getLipids = function(self) return 1 end
    item.getProteins = function(self) return 2 end
    item.getFoodType = function(self) return foodType end
    item.isCooked = function(self) return false end
    item.isBurnt = function(self) return false end
    item.isRotten = function(self) return false end
    item.isFrozen = function(self) return false end
    item.getThirstChangeUnmodified = function(self) return 0 end
    item.haveExtraItems = function(self) return false end
    item.getModData = function(self) return md end
    item.getScriptItem = function(self)
        return { getHungerChange = function(s) return -16 end, getThirstChange = function(s) return 0 end }
    end
    local char = { getUsername = function(self) return "admin" end }
    local b = IN.readBefore({ item = item, character = char })
    hung = 0
    local vec = IN.readAfterAndLand(b)
    local rec = NutritionRevamp.server.store.records.admin
    NutritionRevamp.data.infer = nil
    return b, vec, rec, IN.lastError
end
"""


def test_read_before_captures_declared_food_type_and_macros(server_host):
    h = server_host
    md = tbl(h, {"NR_Nutrients": "fibre:9"})
    b, vec, rec, err = h.rt.eval(CHAIN_EAT)("Base.Kiwi", md, "Fruits", 50, None)
    assert b["declared"] == "fibre:9"
    assert b["foodType"] == "Fruits"
    assert macros(b["macros"]) == [50, 10, 1, 2]


def test_server_path_declared_item_lands_its_declared_vector(server_host):
    h = server_host
    md = tbl(h, {"NR_Nutrients": "fibre:9;vitC:2"})
    b, vec, rec, err = h.rt.eval(CHAIN_EAT)("Base.Apple", md, "Fruits", 95, templates(h))
    assert rec is not None, err
    assert rec["lastIntake"]["source"] == "declared"
    assert abs(vec["fibre"] - 9) < TOL
    assert list(as_dict(rec["lastIntake"]["declared"]).values()) == ["Base.Apple"]


def test_server_path_untabled_item_infers_from_the_loaded_templates(server_host):
    h = server_host
    b, vec, rec, err = h.rt.eval(CHAIN_EAT)("Base.Kiwi", h.rt.table(), "Fruits", 50, templates(h))
    assert rec is not None, err
    assert rec["lastIntake"]["source"] == "inferred"
    assert abs(vec["fibre"] - 2.0) < TOL
    assert list(as_dict(rec["lastIntake"]["inferred"]).values()) == ["Base.Kiwi"]


def test_server_path_malformed_declared_is_counted_and_named(server_host):
    h = server_host
    before_n = I(h).stats.declaredMalformed
    md = tbl(h, {"NR_Nutrients": "fibre:-3"})
    b, vec, rec, err = h.rt.eval(CHAIN_EAT)("Base.Apple", md, "Fruits", 95, None)
    assert rec["lastIntake"]["source"] == "baseline"
    assert I(h).stats.declaredMalformed == before_n + 1
    assert "NR_Nutrients" in str(err) and "Base.Apple" in str(err)


TYPE_INFO = r"""
function()
    local IN = NutritionRevamp.server.intake
    local made = 0
    local saved = instanceItem
    instanceItem = function(fullType)
        made = made + 1
        if fullType == "Base.Rock" then return {} end
        if fullType == "Base.Raise" then error("stub: no such item") end
        if fullType == "Base.BadGetter" then
            return { getCalories = function(self) error("stub: getter raised") end }
        end
        return {
            getCalories = function(self) return 50 end,
            getCarbohydrates = function(self) return 12 end,
            getLipids = function(self) return 0 end,
            getProteins = function(self) return 1 end,
            getFoodType = function(self) return "Fruits" end,
            getModData = function(self) return { NR_Nutrients = "fibre:3" } end,
        }
    end
    IN.typeInfoCache = {}
    local a = IN.typeInfo("Base.Kiwi")
    local a2 = IN.typeInfo("Base.Kiwi")
    local rock = IN.typeInfo("Base.Rock")
    local rock2 = IN.typeInfo("Base.Rock")
    local raised = IN.typeInfo("Base.Raise")
    local bad = IN.typeInfo("Base.BadGetter")
    local bad2 = IN.typeInfo("Base.BadGetter")
    instanceItem = nil
    local absent = IN.typeInfo("Base.Other")
    instanceItem = saved
    IN.typeInfoCache = {}
    return a, a2, rock, rock2, raised, absent, made, bad, bad2
end
"""


def test_type_info_reads_a_fresh_instance_once_per_type(intake_host):
    h = intake_host
    a, a2, rock, rock2, raised, absent, made, bad, bad2 = h.rt.eval(TYPE_INFO)()
    assert bad is None and bad2 is None                  # a raising getter on the fresh instance caches false (the Task 10 review)
    assert a["declared"] == "fibre:3" and a["foodType"] == "Fruits"
    assert macros(a["macros"]) == [50, 12, 0, 1]
    assert h.rt.eval("function(x, y) return rawequal(x, y) end")(a, a2)     # the cached table
    assert rock is None and rock2 is None                # not a Food: no calories getter
    assert raised is None and absent is None
    assert made == 4                                     # Kiwi, Rock, Raise and BadGetter, each once
