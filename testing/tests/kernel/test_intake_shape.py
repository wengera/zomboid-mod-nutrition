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


def test_assemble_craft_map_zero_count_lands_no_seed(intake_host):
    # vanilla writes integer counts >= 1 (ISHandcraftAction.performRecipe); a 0 count is kept by
    # craftMap and contributes nothing through K.vector.craft, while the macros still track the item
    h = intake_host
    b = before(h, fullType="Base.MeatPatty", rawBefore=-0.2, instBase=-0.2, scriptHunger=-0.2, cal=200, carb=0, lip=10, pro=40)
    b["craftMap"] = I(h).craftMap(tbl(h, {"Base.MincedMeat": 0}))
    vec, source, missing, share, frac = I(h).assemble(b, 0, lookup(h))
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
    # the live (already shrunk) item both times at Eat's own fraction
    h = intake_host
    b1 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=2, carb=0, lip=0, pro=0,
                thirstBefore=-0.1, scriptThirst=-0.1)
    v1, s1, m1, share1, frac1 = I(h).assemble(b1, 0, lookup(h), -0.05)
    b2 = before(h, rawBefore=0, instBase=0, scriptHunger=0, cal=1, carb=0, lip=0, pro=0,
                thirstBefore=-0.05, scriptThirst=-0.1)
    v2, s2, m2, share2, frac2 = I(h).assemble(b2, 0, lookup(h), 0)
    assert abs(share1 - 0.5) < TOL and abs(frac1 - 0.5) < TOL
    assert abs(share2 - 0.5) < TOL and abs(frac2 - 1.0) < TOL
    assert abs(v1["fibre"] + v2["fibre"] - 4.4) < TOL
    assert abs(v1["water"] + v2["water"] - 156) < TOL
    assert abs(v1["calories"] - 1) < TOL and abs(v2["calories"] - 1) < TOL


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
    assert abs(rec["stomach"]["bulk"] - expected_bulk) < TOL
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
