"""NR_Server_Creation, the OnNewGame creation handler (Plan 13 Task 17; spec section 3.2; rulings 13-16, 13-31; Task 10c).

The handler runs on server_host's Host (every server/ file in load order, OnServerStarted fired), so the wiring is the
real one: NR_Server_Players' OnNewGame fires P.onNewGame after store.reset, NR_Server_Creation validates the picks,
builds the body through CRE.newBody (the builder first sight shares) and writes the weight, the Strength level (NR_Server_Strength)
and the weight-band traits (NR_Server_Weight). The Java side is table-of-functions stand-ins, test_strength_shape.py's
pattern: a trait collection whose getKnownTraits answers the held traits in pick order; definitions with a cost, a free
flag, a one-way exclusion list (isMutuallyExclusive reads it one way, as the engine's does for a trait with no grants),
XP boosts and grants; a profession definition off the descriptor; LevelPerk and LoseLevel stepping the level with
vanilla's Strength band listener (XpUpdate.lua:200-217) applied at each step. Every collection edit, LevelPerk and
setWeight lands in one call log, so the order of the writes is read off it. A stub proves the wiring, the order and the
guards, not the engine's getters: Task 0's checks 4 and 5 and Task 21's live run read those.
"""
import pytest

from . import strength_level as sl
from .server_host import Host

H2 = 1.70 * 1.70
FAVG = 18.0 * H2   # the untrained average lean; the fat starts scale by F / FAVG (Task 10b)
LADDER = [1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500]

ENV = r"""
NR_C = { log = {}, defs = {}, profCost = 0, profGrants = {}, penalty = 1, grants = {}, profStrength = 0 }
local function list(items)
    return { items = items,
             size = function(s) return #s.items end,
             get = function(s, i) return s.items[i + 1] end,
             contains = function(s, x)
                 for _, v in ipairs(s.items) do if v == x then return true end end
                 return false
             end }
end
NR_C.list = list
CharacterTrait = {}
for _, n in ipairs({ "WEAK", "FEEBLE", "STOUT", "STRONG", "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT",
                     "EMACIATED", "WEIGHTGAIN", "WEIGHTLOSS", "ATHLETIC", "FIT", "OUT_OF_SHAPE", "UNFIT", "BRAVE",
                     "GYMNAST", "SPEEDDEMON", "AXEMAN", "LIGHTEATER" }) do
    CharacterTrait[n] = { name = n, getName = function(s) return s.name end }
end
local ladder = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 }
Perks = { Strength = { name = "Strength", getTotalXpForLevel = function(s, L) return ladder[L] end },
          Fitness = { name = "Fitness" }, Sprinting = { name = "Sprinting" } }
addXp = function(p, perk, amount) p.st.grants[#p.st.grants + 1] = amount end
transformIntoKahluaTable = function(m) return m end
-- a definition built from NR_C.defs[name]: { cost, free, excl = {names}, boosts = {perk name = n}, granted = {names} }
CharacterTraitDefinition = {}
CharacterTraitDefinition.getCharacterTraitDefinition = function(t)
    local spec = NR_C.defs[t.name]
    if spec == nil then return nil end
    local excl = {}
    for _, n in ipairs(spec.excl or {}) do excl[#excl + 1] = CharacterTrait[n] end
    local granted = {}
    for _, n in ipairs(spec.granted or {}) do granted[#granted + 1] = CharacterTrait[n] end
    local boosts = {}
    for k, v in pairs(spec.boosts or {}) do
        if k == "Sprinting" then boosts[Perks[k]] = { intValue = function(s) return v end }   -- a java Integer
        else boosts[Perks[k]] = v end
    end
    local def = { type = t }
    def.getType = function(s) return s.type end
    def.getCost = function(s) return spec.cost end
    def.isFree = function(s) return spec.free == true end
    def.getMutuallyExclusiveTraits = function(s) return list(excl) end
    def.isMutuallyExclusive = function(s, other) return list(excl):contains(other.type) end
    def.getXpBoosts = function(s) return boosts end
    def.getGrantedTraits = function(s) return list(granted) end
    return def
end
CharacterProfessionDefinition = {}
CharacterProfessionDefinition.getCharacterProfessionDefinition = function(prof)
    if NR_C.noProfession then return nil end
    local granted = {}
    for _, n in ipairs(NR_C.profGrants) do granted[#granted + 1] = CharacterTrait[n] end
    local boosts = {}
    if NR_C.profStrength ~= 0 then boosts[Perks.Strength] = NR_C.profStrength end
    if NR_C.profSprint then boosts[Perks.Sprinting] = NR_C.profSprint end
    return { getCost = function(s) return NR_C.profCost end, getGrantedTraits = function(s) return list(granted) end,
             getXpBoosts = function(s) return boosts end }
end
getSandboxOptions = function()
    return { getOptionByName = function(s, n)
        if n == "NegativeTraitsPenalty" then return { getValue = function(o) return NR_C.penalty end } end
        return nil
    end }
end
SandboxVars = { Nutrition = false, CharacterFreePoints = 0 }

-- vanilla's Strength band listener (XpUpdate.lua:200-217), run by the stand-in's LevelPerk and LoseLevel
local function remap(st, level)
    for _, n in ipairs({ "WEAK", "FEEBLE", "STOUT", "STRONG" }) do st.traits[n] = nil end
    local want = nil
    if level <= 1 then want = "WEAK" elseif level <= 4 then want = "FEEBLE"
    elseif level >= 9 then want = "STRONG" elseif level >= 6 then want = "STOUT" end
    if want ~= nil then st.traits[want] = true end
end

NR_C.decorate = function(p, cfg)
    local st = { traits = {}, order = {}, perk = { Strength = cfg.strength or 5, Fitness = 5, Sprinting = cfg.sprint or 0 },
                 xpSets = {}, grants = {}, levelWrites = {}, xp = 0 }
    p.st = st
    for _, n in ipairs(cfg.known) do st.traits[n] = true; st.order[#st.order + 1] = n end
    local log = NR_C.log
    local coll = {}
    coll.get = function(c, t) log[#log + 1] = "get:" .. t.name; return st.traits[t.name] == true end
    coll.add = function(c, t)
        log[#log + 1] = "add:" .. t.name
        if not st.traits[t.name] then st.order[#st.order + 1] = t.name end
        st.traits[t.name] = true
    end
    coll.remove = function(c, t)
        log[#log + 1] = "remove:" .. t.name
        st.traits[t.name] = nil
    end
    coll.getKnownTraits = function(c)
        local out = {}
        for _, n in ipairs(st.order) do if st.traits[n] then out[#out + 1] = CharacterTrait[n] end end
        return list(out)
    end
    p.getCharacterTraits = function(s) return coll end
    p.isFemale = function(s) return cfg.female == true end
    p.isAsleep = function(s) return cfg.asleep == true end
    p.getDescriptor = function(s)
        return { getCharacterProfession = function(d) return "prof:test" end }
    end
    p.getPerkLevel = function(s, perk) return st.perk[perk.name] end
    p.setPerkLevelDebug = function(s, perk, n)
        log[#log + 1] = "setPerkLevelDebug:" .. perk.name .. ":" .. n
        st.perk[perk.name] = n
        st.levelWrites[#st.levelWrites + 1] = perk.name .. ":" .. n
    end
    p.LevelPerk = function(s, perk)
        st.perk[perk.name] = math.min(10, st.perk[perk.name] + 1)
        log[#log + 1] = "LevelPerk:" .. perk.name .. ":" .. st.perk[perk.name]
        if perk == Perks.Strength then remap(st, st.perk.Strength) end
    end
    p.LoseLevel = function(s, perk)
        st.perk[perk.name] = math.max(0, st.perk[perk.name] - 1)
        log[#log + 1] = "LoseLevel:" .. perk.name .. ":" .. st.perk[perk.name]
        if perk == Perks.Strength then remap(st, st.perk.Strength) end
    end
    local xp = {}
    xp.getXP = function(x, perk) return st.xp end
    xp.setXPToLevel = function(x, perk, L)
        st.xpSets[#st.xpSets + 1] = perk.name .. ":" .. L
        if perk == Perks.Strength then st.xp = (L > 0) and ladder[L] or 0 end
    end
    xp.getMultiplier = function(x, perk) return 1.0 end
    p.getXp = function(s) return xp end
    local nut = p.nut
    nut.weight = cfg.weight or 80
    local set = nut.setWeight
    nut.setWeight = function(n, v) log[#log + 1] = "setWeight"; set(n, v) end
    return p
end
"""

# The definitions: the restated blocks' costs and exclusions (NR_Traits_Body.txt), and a few vanilla-shaped others.
DEFS = {
    "WEAK": dict(cost=-10, excl=["FEEBLE", "STOUT", "STRONG"], boosts={"Strength": -5}),
    "FEEBLE": dict(cost=-6, excl=["STOUT", "STRONG", "WEAK"], boosts={"Strength": -2}),
    "STOUT": dict(cost=6, excl=["FEEBLE", "STRONG", "WEAK"], boosts={"Strength": 2}),
    "STRONG": dict(cost=10, excl=["FEEBLE", "STOUT", "WEAK"], boosts={"Strength": 4}),
    "OBESE": dict(cost=-10, excl=["ATHLETIC", "EMACIATED", "FIT", "LIGHTEATER", "VERY_UNDERWEIGHT", "UNDERWEIGHT",
                                  "OVERWEIGHT", "WEIGHTLOSS"]),
    "OVERWEIGHT": dict(cost=-6, excl=["ATHLETIC", "FIT", "EMACIATED", "VERY_UNDERWEIGHT", "UNDERWEIGHT", "OBESE",
                                      "WEIGHTLOSS"]),
    "UNDERWEIGHT": dict(cost=-6, excl=["OBESE", "VERY_UNDERWEIGHT", "OVERWEIGHT", "WEIGHTGAIN"]),
    "VERY_UNDERWEIGHT": dict(cost=-10, excl=["ATHLETIC", "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "WEIGHTGAIN",
                                             "WEIGHTLOSS"]),
    "WEIGHTGAIN": dict(cost=-2, excl=["WEIGHTLOSS", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED", "ATHLETIC", "FIT"]),
    "WEIGHTLOSS": dict(cost=-2, excl=["WEIGHTGAIN", "OVERWEIGHT", "OBESE", "VERY_UNDERWEIGHT"]),
    "ATHLETIC": dict(cost=10, excl=["FIT", "OUT_OF_SHAPE", "UNFIT", "OBESE", "OVERWEIGHT", "VERY_UNDERWEIGHT"]),
    "FIT": dict(cost=6, excl=["ATHLETIC", "OUT_OF_SHAPE", "UNFIT", "OBESE", "OVERWEIGHT"]),
    "BRAVE": dict(cost=4),
    "SPEEDDEMON": dict(cost=1),
    "GYMNAST": dict(cost=5, boosts={"Strength": 2, "Sprinting": 1}),
    "AXEMAN": dict(cost=0, free=True),
    "EMACIATED": dict(cost=0, free=True),
}


def _host(prof_cost=8, female=False, sex_specific=False, defs=DEFS, prof_strength=0):
    h = Host(extra_env=ENV)
    h.defs = defs
    h.G.NR_C.profStrength = prof_strength
    C = h.G.NR_C
    for name, spec in defs.items():
        t = h.rt.table()
        for k, v in spec.items():
            t[k] = h.rt.table(*v) if isinstance(v, list) else (h.rt.table_from(v) if isinstance(v, dict) else v)
        C.defs[name] = t
    C.profCost = prof_cost
    h.NR.server.options.sexSpecific = sex_specific
    return h


MUSCLE = ("WEAK", "FEEBLE", "STOUT", "STRONG")


def _band(level):
    """Vanilla's Strength band for a level (XpUpdate.lua:200-217)."""
    if level <= 1:
        return "WEAK"
    if level <= 4:
        return "FEEBLE"
    if level == 5:
        return None
    return "STOUT" if level <= 8 else "STRONG"


def _applied(h, known):
    """applyTraits' Strength (trait-levers 3.1): 5 + the held traits' and the profession's Strength boosts, clamped to
    [0, 10], climbed from 0 with LevelPerk, so from level 1 up the held muscle trait is the level's band, re-added last
    by vanilla's listener (fix 2: the band is the last entry of getKnownTraits)."""
    boost = sum(h.defs.get(n, {}).get("boosts", {}).get("Strength", 0) for n in known)
    level = max(0, min(10, 5 + boost + h.G.NR_C.profStrength))
    if level >= 1:
        band = _band(level)
        known = [n for n in known if n not in MUSCLE] + ([band] if band is not None else [])
    return level, known


def _player(h, known, name="a", **cfg):
    if "strength" not in cfg:
        cfg["strength"], known = _applied(h, known)
    p = h.player(name)
    c = h.rt.table()
    c.known = h.rt.table(*known)
    for k, v in cfg.items():
        c[k] = v
    return h.G.NR_C.decorate(p, c)


def _new_game(h, p):
    h.fire("OnNewGame", p, None)
    return h.record(p.getUsername(p))


def _held(p):
    return sorted(k for k, v in p.st.traits.items() if v)


def _log(h):
    return list(h.G.NR_C.log.values())


def _printed(h):
    return list(h.T.printed.values())


# --- the brief's tests -------------------------------------------------------------------------------------------

def test_strong_and_overweight_build_strongs_start_and_overweights_fat():
    h = _host()
    p = _player(h, ["STRONG", "OVERWEIGHT"], weight=95.0)   # applyWeightFromTraits wrote 95 kg (trait-levers 3.2)
    r = _new_game(h, p)
    b = r.body
    F, F0, Fc, Pk = sl.trait_start("STRONG")
    assert abs(F - 60.86) < 0.005
    for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(b[k] - v) < 1e-9, k
    assert b.N0 == sl.LEVEL_MODEL["N0"]["STRONG"]
    fm = 7.5 * H2 * F / FAVG                                  # 25.36 kg: Overweight's 29.4 % at Strong's lean
    assert abs(b.fm - fm) < 1e-9
    assert b.fatT == 1 and b.thinT == 0
    assert abs(p.nut.weight - (F + fm)) < 1e-9          # the weight is the body's, not vanilla's 95 kg
    assert h.NR.server.creation.stats.created == 1


def test_the_level_write_lands_nine_with_strong():
    h = _host()
    p = _player(h, ["STRONG", "OVERWEIGHT"])
    r = _new_game(h, p)
    assert p.st.perk.Strength == 9
    assert p.st.traits.STRONG is True
    assert not p.st.traits.STOUT
    assert r.body.wroteL == 9 and r.body.levelDue is True          # the first minute re-pins (Task 10c)
    assert p.st.traits.OVERWEIGHT is True


def test_new_game_leaves_the_level_due_and_the_next_minute_writes_it_once():
    # Task 10c (the creation re-pin): x433 read XP 10500 at a shown 3.83, the fraction lost at OnNewGame; the handler
    # leaves levelDue true so the first server minute writes the level again (ruling: cost if wrong, one extra write)
    h = _host()
    p = _player(h, ["FEEBLE"])
    r = _new_game(h, p)
    STR = h.NR.server.strength
    writes = STR.stats.levelWrites
    assert r.body.levelDue is True and writes == 1
    h.online(p)
    h.T.age = 100.0 + 1 / 60
    h.minute()
    h.tick(3)
    assert STR.stats.levelWrites == writes + 1
    assert r.body.levelDue is False and r.body.wroteL == 3
    h.T.age = 100.0 + 2 / 60
    h.minute()
    h.tick(3)
    assert STR.stats.levelWrites == writes + 1                      # once: the next minute writes nothing


def test_the_order_weight_then_level_then_the_weight_band_traits():
    h = _host(prof_cost=10)
    h.G.NR_C.profGrants = h.rt.table("EMACIATED")
    # Emaciated is read as Very Underweight: the trait write swaps it. A native 8 (an offset no muscle boost makes)
    # reads the held band, Strong, so the write steps 8 to 9 (a thin pick moves no level since Task 10c)
    p = _player(h, ["STRONG", "EMACIATED"], strength=8)
    _new_game(h, p)
    log = _log(h)
    i_weight = log.index("setWeight")
    levels = [i for i, e in enumerate(log) if e.startswith(("LevelPerk:Strength", "LoseLevel:Strength"))]
    band = [i for i, e in enumerate(log)
            if e.split(":")[0] in ("get", "add", "remove")
            and e.split(":")[1] in ("OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED")]
    assert levels, log
    assert i_weight < levels[0]
    assert band[-1] > levels[-1]                              # the trait write is last, so it is final
    assert "add:VERY_UNDERWEIGHT" in log and "remove:EMACIATED" in log
    assert _held(p) == ["STRONG", "VERY_UNDERWEIGHT"]               # a thin pick is fat-only: Strong keeps level 9


@pytest.mark.parametrize("muscle", ["WEAK", "FEEBLE"])
@pytest.mark.parametrize("thin", ["UNDERWEIGHT", "VERY_UNDERWEIGHT"])
@pytest.mark.parametrize("order", [0, 1])
def test_weak_and_feeble_are_kept_with_a_thin_pick_in_either_order(muscle, thin, order):
    # Task 10c (Angus, 2026-10-15: "Lift the exclusions"): nothing is stripped, and the body is the muscle pick's lean
    # with the thin pick's fat
    known = [muscle, thin] if order == 0 else [thin, muscle]
    h = _host(prof_cost=20)
    p = _player(h, known)
    r = _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0
    assert p.st.traits[muscle] is True and p.st.traits[thin] is True
    assert r.body.N0 == sl.LEVEL_MODEL["N0"][muscle]
    assert abs(r.body.lm - sl.trait_start(muscle)[0]) < 1e-9
    assert r.body.thinT == {"UNDERWEIGHT": 1, "VERY_UNDERWEIGHT": 2}[thin]
    assert r.body.fmRef > r.body.fm
    assert not any(" loses " in s for s in _printed(h))


def test_the_handler_adds_no_pair_of_its_own():
    # with no definition listing a pair, the handler strips nothing (ruling 13-46's kernel table is gone)
    defs = dict(DEFS)
    defs["WEAK"] = dict(cost=-10, boosts={"Strength": -5})
    defs["UNDERWEIGHT"] = dict(cost=-6)
    h = _host(defs=defs)
    p = _player(h, ["WEAK", "UNDERWEIGHT"])
    r = _new_game(h, p)
    assert r.body.N0 == sl.LEVEL_MODEL["N0"]["WEAK"]
    assert h.NR.server.creation.stats.stripped == 0


@pytest.mark.parametrize("known", [["OVERWEIGHT", "OBESE"], ["OBESE", "OVERWEIGHT"]])
def test_overweight_and_obese_lose_obese_the_costlier(known):
    h = _host()
    p = _player(h, known)
    r = _new_game(h, p)
    assert p.st.traits.OVERWEIGHT is True and not p.st.traits.OBESE
    assert r.body.fatT == 1


@pytest.mark.parametrize("known, lost", [
    (["ATHLETIC", "WEIGHTGAIN"], "ATHLETIC"),        # Athletic's list does not hold Weight Gain: the reverse read
    (["WEIGHTGAIN", "ATHLETIC"], "ATHLETIC"),        # Weight Gain's list holds Athletic: the forward read
    (["WEIGHTLOSS", "OBESE"], "OBESE"),              # the costlier (|-10| against |-2|) goes, either order (fix 3)
    (["OBESE", "WEIGHTLOSS"], "OBESE"),
])
def test_the_exclusion_check_runs_both_ways(known, lost):
    h = _host(prof_cost=10)
    p = _player(h, known)
    _new_game(h, p)
    kept = [n for n in known if n != lost]
    assert not p.st.traits[lost]
    assert all(p.st.traits[n] is True for n in kept)


def test_an_over_budget_list_loses_its_costliest_positive_picks_until_legal_each_logged():
    # profession 0: STRONG 10, BRAVE 4, SPEEDDEMON 1, OVERWEIGHT -6 -> remaining 0 - 15 + 6 = -9; stripping STRONG, the
    # costliest (fix 3), makes it 1: legal; the bad trait stays
    h = _host(prof_cost=0)
    p = _player(h, ["STRONG", "BRAVE", "SPEEDDEMON", "OVERWEIGHT"])
    _new_game(h, p)
    assert _held(p) == ["BRAVE", "OVERWEIGHT", "SPEEDDEMON"]
    lines = [s for s in _printed(h) if "over the point total" in s]
    assert [l.split(" loses ")[1].split(" ")[0] for l in lines] == ["STRONG"]
    assert h.NR.server.creation.stats.stripped == 1


def test_a_legal_list_keeps_everything():
    h = _host(prof_cost=0)
    p = _player(h, ["BRAVE", "SPEEDDEMON", "OVERWEIGHT"])    # 0 - 5 + 6 = 1
    _new_game(h, p)
    assert _held(p) == ["BRAVE", "OVERWEIGHT", "SPEEDDEMON"]
    assert h.NR.server.creation.stats.stripped == 0


def test_free_points_and_the_negative_trait_penalty_enter_the_total():
    h = _host(prof_cost=0)
    h.G.SandboxVars.CharacterFreePoints = 4
    p = _player(h, ["BRAVE", "SPEEDDEMON", "OVERWEIGHT", "WEIGHTGAIN"])   # 4 - 5 + 8 = 7: legal at penalty 1
    _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0
    for penalty, n in ((2, 0), (3, 1), (4, 1)):
        assert h.NR.server.creation.offset(penalty, 2) == n
    assert h.NR.server.creation.offset(4, 0) == 0
    h2 = _host(prof_cost=0)
    h2.G.NR_C.penalty = 4
    p2 = _player(h2, ["STRONG", "OVERWEIGHT", "WEIGHTLOSS"])    # 0 - 10 + 8 - (2 - 1) = -3: STRONG goes
    _new_game(h2, p2)
    assert not p2.st.traits.STRONG


def test_free_traits_are_never_stripped_and_cost_nothing():
    h = _host(prof_cost=0)
    h.G.NR_C.profGrants = h.rt.table("BRAVE", "AXEMAN")         # a profession grant, though not isFree
    p = _player(h, ["BRAVE", "AXEMAN", "SPEEDDEMON", "OVERWEIGHT"])   # 0 - 1 + 6 = 5: BRAVE costs nothing
    _new_game(h, p)
    assert _held(p) == ["AXEMAN", "BRAVE", "OVERWEIGHT", "SPEEDDEMON"]


def test_a_pick_a_free_trait_excludes_is_stripped():
    h = _host()
    h.G.NR_C.profGrants = h.rt.table("ATHLETIC")
    p = _player(h, ["OVERWEIGHT", "ATHLETIC"])
    _new_game(h, p)
    assert p.st.traits.ATHLETIC is True and not p.st.traits.OVERWEIGHT


def test_a_stripped_trait_with_a_strength_boost_has_its_levels_reverted():
    # GYMNAST (+2 Strength, +1 Sprinting as a java Integer) over budget: applyTraits left Strength 7, Sprinting 1
    h = _host(prof_cost=0)
    p = _player(h, ["GYMNAST"], strength=7, sprint=1)
    _new_game(h, p)
    assert not p.st.traits.GYMNAST
    writes = list(p.st.levelWrites.values())
    assert "Strength:5" in writes and "Sprinting:0" in writes
    assert "Sprinting:0" in list(p.st.xpSets.values())
    assert p.st.perk.Strength == 5 and p.st.perk.Sprinting == 0
    assert not any(e.startswith("LevelPerk") or e.startswith("LoseLevel") for e in _log(h))   # 5 is the body's level


def test_an_unreadable_profession_skips_the_point_check():
    h = _host(prof_cost=0)
    h.G.NR_C.noProfession = True
    p = _player(h, ["STRONG", "BRAVE"])
    _new_game(h, p)
    assert _held(p) == ["BRAVE", "STRONG"]
    assert h.NR.server.creation.stats.budgetUnread == 1


def test_a_respawns_new_game_builds_a_fresh_body():
    h = _host()
    p = _player(h, ["STRONG"])
    r = _new_game(h, p)
    r.body.lm = 70.0                                            # trained since
    p2 = _player(h, ["FEEBLE", "OBESE"])
    r2 = _new_game(h, p2)
    assert r2.resets == 1
    assert abs(r2.body.lm - sl.trait_start("FEEBLE")[0]) < 1e-9
    assert abs(r2.body.fm - 10.5 * H2 * sl.trait_start("FEEBLE")[0] / FAVG) < 1e-9
    assert p2.st.perk.Strength == 3 and p2.st.traits.FEEBLE is True
    assert h.NR.server.creation.stats.created == 2


def test_first_sight_after_new_game_finds_the_body_and_builds_none():
    h = _host()
    p = _player(h, ["STRONG", "OVERWEIGHT"])
    r = _new_game(h, p)
    body = r.body
    MET = h.NR.server.metabolism
    creates = MET.stats.creates
    h.online(p)
    h.T.age = 100.0 + 1 / 60
    h.minute()
    h.tick(3)
    assert h.rt.eval("rawequal")(h.record("a").body, body)
    assert MET.stats.creates == creates
    assert h.NR.server.creation.stats.created == 1


def test_a_pending_reset_builds_the_body_from_the_queue_slot():
    h = _host()
    p = _player(h, ["STOUT", "OVERWEIGHT"])
    h.T.age = None
    h.fire("OnNewGame", p, None)
    assert h.NR.server.creation.stats.created == 0
    h.online(p)
    h.T.age = 100.0 + 1 / 60
    h.minute()
    h.tick(3)
    r = h.record("a")
    assert r.resets == 0
    assert abs(r.body.lm - sl.trait_start("STOUT")[0]) < 1e-9
    assert h.NR.server.creation.stats.created == 1
    assert p.st.perk.Strength == 7


@pytest.mark.parametrize("female, specific, fmi", [(True, True, 11.0), (True, False, 7.5), (False, True, 7.5)])
def test_sex_specific_female_overweight_builds_the_female_band(female, specific, fmi):
    h = _host(sex_specific=specific)
    p = _player(h, ["OVERWEIGHT"], female=female)
    r = _new_game(h, p)
    assert abs(r.body.fm - fmi * H2) < 1e-9
    assert r.body.sex == (2 if female else 1)
    assert abs(p.nut.weight - (r.body.lm + r.body.fm)) < 1e-9


def test_a_sleeping_character_keeps_the_level_due():
    h = _host(prof_cost=10)
    p = _player(h, ["STRONG"], asleep=True)
    r = _new_game(h, p)
    assert r.body.levelDue is True and p.st.perk.Strength == 9      # applyTraits' level, the write waiting
    assert h.NR.server.creation.stats.failures == 0


def test_a_raising_write_is_counted_and_the_level_stays_due():
    h = _host()
    h.rt.execute("NutritionRevamp.server.strength.writeLevel = function() error('boom') end")
    p = _player(h, ["STRONG"])
    r = _new_game(h, p)
    assert h.NR.server.creation.stats.failures == 1
    assert "boom" in str(h.NR.server.creation.lastError)
    assert r.body.levelDue is True                              # the Strength minute writes it


# --- fix 1: the muscle pick inferred from the native level (the muscle blocks keep vanilla's Strength boost) ---------

def _picks(h, p):
    return h.NR.server.creation.picks(p)


def test_strong_with_no_profession_boost_climbs_to_nine_and_reads_strong():
    h = _host(prof_cost=10)
    p = _player(h, ["STRONG"])
    assert p.st.perk.Strength == 9 and p.st.traits.STRONG is True     # applyTraits' climb, vanilla's band
    assert _picks(h, p)[0] == "STRONG"
    r = _new_game(h, p)
    assert abs(r.body.lm - sl.trait_start("STRONG")[0]) < 1e-9
    assert r.body.N0 == sl.LEVEL_MODEL["N0"]["STRONG"]


def test_stout_with_a_profession_plus_two_holds_strongs_band_yet_reads_stout():
    # profession cost 6: STOUT (6) is legal, the held STRONG (10) would not be, so validation reads the inferred pick
    h = _host(prof_cost=6, prof_strength=2)
    p = _player(h, ["STOUT"])
    assert p.st.perk.Strength == 9 and p.st.traits.STRONG is True and not p.st.traits.STOUT
    assert _picks(h, p)[0] == "STOUT"
    r = _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0
    # Task 17b: the profession's +2 raises Stout's start like a small trait, 7 + 2 = 9, at Stout's N0
    assert abs(r.body.lm - sl.trait_start("STOUT", prof=2)[0]) < 1e-9
    assert r.body.N0 == sl.LEVEL_MODEL["N0"]["STOUT"]
    assert p.st.perk.Strength == 9 and p.st.traits.STRONG is True


def test_a_stripped_inferred_pick_removes_the_held_band_trait():
    h = _host(prof_cost=0, prof_strength=2)
    p = _player(h, ["STOUT"])                                          # holds STRONG; 0 - 6 < 0: the pick goes
    r = _new_game(h, p)
    assert any("loses STOUT" in l for l in _printed(h))
    log = _log(h)
    assert not any(e.startswith(("LevelPerk", "LoseLevel")) for e in log)
    assert r.body.N0 == 1.0                                            # reverted to 7: 7 - 5 - 2 = 0, no pick
    # Task 17b: the body is no pick under the profession's +2, level 7, the reverted level: no step is needed, and
    # fix 1 re-asserts the level's band after the write
    assert abs(r.body.lm - sl.trait_start("none", prof=2)[0]) < 1e-9
    assert p.st.perk.Strength == 7
    assert p.st.traits.STOUT is True and not p.st.traits.STRONG
    assert log.index("remove:STRONG") < log.index("add:STOUT")         # the strip removes the held band trait itself


def test_strong_with_a_profession_plus_two_is_clamped_at_ten_and_reads_the_held_band():
    h = _host(prof_cost=10, prof_strength=2)
    p = _player(h, ["STRONG"])
    assert p.st.perk.Strength == 10 and p.st.traits.STRONG is True
    assert _picks(h, p)[0] == "STRONG"
    r = _new_game(h, p)
    # Task 17b: 9 + 2 clamps to 10, so the native level 10 the climb reached stays
    assert abs(r.body.lm - sl.trait_start("STRONG", prof=2)[0]) < 1e-9
    assert sl.start_level("STRONG", 2) == 10
    assert p.st.perk.Strength == 10 and p.st.traits.STRONG is True


def test_weak_ends_at_native_one_after_the_write():
    h = _host()
    p = _player(h, ["WEAK"])
    assert p.st.perk.Strength == 0 and p.st.traits.WEAK is True       # level 0: no LevelPerk, no swap
    assert _picks(h, p)[0] == "WEAK"
    r = _new_game(h, p)
    assert r.body.N0 == sl.LEVEL_MODEL["N0"]["WEAK"]
    assert p.st.perk.Strength == 1 and p.st.traits.WEAK is True


def test_a_profession_band_with_no_pick_is_neither_validated_nor_built():
    h = _host(prof_cost=0, prof_strength=1)
    p = _player(h, [])
    assert p.st.perk.Strength == 6 and p.st.traits.STOUT is True       # vanilla's band from the profession alone
    assert _picks(h, p)[0] is None
    r = _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0                    # STOUT's cost 6 is never counted
    assert r.body.N0 == 1.0
    # Task 17b: no pick under the profession's +1 starts at 6, the native level and vanilla's Stout band kept
    assert abs(r.body.lm - sl.trait_start("none", prof=1)[0]) < 1e-9
    assert p.st.perk.Strength == 6 and p.st.traits.STOUT is True


def test_an_unmapped_offset_falls_back_to_the_held_band():
    h = _host()
    p = _player(h, ["STRONG"], strength=8)                             # 8 - 5 = 3: no muscle boost makes it
    p.st.traits.STOUT = True
    p.st.traits.STRONG = None
    assert _picks(h, p)[0] == "STOUT"


def test_a_clamped_level_never_maps_through_the_boost_table():
    # Stout with a profession +5 climbs to 12, clamped at 10: 10 - 5 - 5 = 0 would read "no pick"; the held band reads
    h = _host(prof_cost=10, prof_strength=5)
    p = _player(h, ["STOUT"])
    assert p.st.perk.Strength == 10
    assert _picks(h, p)[0] == "STRONG"


# --- fix 2: the reviewer's tests (scratch-verified, verbatim) ------------------------------------------------


def test_a_profession_trait_the_profession_does_not_grant_is_stripped():
    h = _host(prof_cost=8)
    p = _player(h, ["AXEMAN", "BRAVE"])                     # AXEMAN is a profession trait (isFree) that no grant names
    _new_game(h, p)
    assert not p.st.traits.AXEMAN and p.st.traits.BRAVE is True
    assert any("loses AXEMAN" in l for l in _printed(h))


def test_character_free_points_make_an_otherwise_over_budget_list_legal():
    h = _host(prof_cost=0)
    h.G.SandboxVars.CharacterFreePoints = 5
    p = _player(h, ["BRAVE", "SPEEDDEMON"])                 # 0 + 5 - 5 = 0: legal only with the free points
    _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0


def test_a_free_bad_trait_counts_in_the_negative_trait_offset():
    defs = dict(DEFS)
    defs["UNFIT"] = dict(cost=-10)
    h = _host(prof_cost=-1, defs=defs)
    h.G.NR_C.penalty = 4
    h.G.NR_C.profGrants = h.rt.table("UNFIT")
    # -1 - (4 + 1 - 6) - (2 - 1) = -1: BRAVE, the costliest, goes (fix 3); without the free UNFIT the offset is 0 and
    # nothing goes
    p = _player(h, ["UNFIT", "BRAVE", "SPEEDDEMON", "OVERWEIGHT"])
    _new_game(h, p)
    assert not p.st.traits.BRAVE and p.st.traits.SPEEDDEMON is True and p.st.traits.UNFIT is True


def test_a_strip_pushes_the_traits_once_and_a_legal_list_pushes_none():
    h = _host(prof_cost=0)
    p = _player(h, ["STRONG"])
    _new_game(h, p)
    s = h.NR.server.creation.stats
    assert s.pushes + s.pushMissing == 1
    h2 = _host(prof_cost=10)
    p2 = _player(h2, ["STRONG"])
    _new_game(h2, p2)
    s2 = h2.NR.server.creation.stats
    assert s2.pushes + s2.pushMissing == 0


def test_a_revert_from_a_clamped_level_stays_in_range():
    h = _host(prof_cost=0)
    p = _player(h, ["GYMNAST"], strength=7, sprint=0)        # Sprinting clamped at 0 by applyTraits
    _new_game(h, p)
    assert "Sprinting:0" in list(p.st.levelWrites.values())
    assert p.st.perk.Sprinting == 0


def test_an_inferred_pick_with_no_band_held_is_still_validated():
    defs = dict(DEFS)
    defs["BRAVE"] = dict(cost=4, excl=["FEEBLE"])           # a pair the definitions list (no mod pair exists)
    h = _host(prof_cost=10, prof_strength=2, defs=defs)
    p = _player(h, ["BRAVE", "FEEBLE"])                     # 5 - 2 + 2 = 5: no band held, FEEBLE inferred
    assert p.st.perk.Strength == 5
    _new_game(h, p)
    assert any("loses FEEBLE" in l and "excluded by BRAVE" in l for l in _printed(h))


def test_the_budget_never_strips_a_pick_of_cost_zero():
    defs = dict(DEFS)
    defs["LIGHTEATER"] = dict(cost=0)
    h = _host(prof_cost=0, defs=defs)
    p = _player(h, ["STRONG", "LIGHTEATER"])
    _new_game(h, p)
    assert p.st.traits.LIGHTEATER is True and not p.st.traits.STRONG


def test_a_level_clamped_at_zero_reads_the_held_band():
    h = _host(prof_cost=10, prof_strength=-3)
    p = _player(h, ["WEAK"])                                # 5 - 5 - 3 clamps to 0: 0 - 5 + 3 = -2 would read FEEBLE
    assert p.st.perk.Strength == 0
    assert _picks(h, p)[0] == "WEAK"


def test_a_trait_a_held_trait_grants_is_free():
    defs = dict(DEFS)
    defs["BRAVE"] = dict(cost=4, granted=["SPEEDDEMON"])
    h = _host(prof_cost=4, defs=defs)
    p = _player(h, ["BRAVE", "SPEEDDEMON"])                 # 4 - 4 = 0: SPEEDDEMON costs nothing as BRAVE's grant
    _new_game(h, p)
    assert h.NR.server.creation.stats.stripped == 0


def test_a_climbed_muscle_pick_follows_the_cost_order_of_an_excluded_pair():
    # Farmer +1: WEAK climbs to 1 and vanilla's listener re-adds it last; the list order is not read (fix 3): the
    # inferred WEAK (|-10|) is costlier than BRAVE (|4|, a pair the definitions list) and goes
    defs = dict(DEFS)
    defs["BRAVE"] = dict(cost=4, excl=["WEAK"])
    h = _host(prof_cost=10, prof_strength=1, defs=defs)
    p = _player(h, ["WEAK", "BRAVE"])
    _new_game(h, p)
    assert any("loses WEAK" in l and "excluded by BRAVE" in l for l in _printed(h))


# --- Task 17b: a profession's Strength boost starts the body like a small trait ------------------------------------


def _level(h, b):
    D = h.K.strength.DEFAULTS
    return h.K.strength.level(b.lm, b.N0, 1.0, D)


@pytest.mark.parametrize("prof", [0, 1, 2])
@pytest.mark.parametrize("muscle", (None,) + MUSCLE)
def test_creation_builds_the_reference_start_under_each_boost(muscle, prof):
    h = _host(prof_cost=10, prof_strength=prof)
    p = _player(h, [muscle] if muscle else [])
    r = _new_game(h, p)
    key = muscle or "none"
    F, F0, Fc, Pk = sl.trait_start(key, prof=prof)
    for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk)):
        assert abs(r.body[k] - v) < 1e-12, (key, prof, k)
    assert r.body.N0 == sl.LEVEL_MODEL["N0"][key]
    assert p.st.perk.Strength == sl.start_level(key, prof)
    assert any(("prof=" + str(prof)) in l for l in _printed(h))


def test_a_strong_lumberjack_starts_at_ten():
    h = _host(prof_cost=10, prof_strength=1)
    p = _player(h, ["STRONG"])
    r = _new_game(h, p)
    assert abs(_level(h, r.body) - 10.0) < 1e-9
    assert p.st.perk.Strength == 10 and p.st.traits.STRONG is True


def test_a_farmer_with_no_pick_starts_at_six_holding_stout():
    h = _host(prof_cost=10, prof_strength=1)
    p = _player(h, [])
    r = _new_game(h, p)
    assert abs(_level(h, r.body) - 6.0) < 1e-9 and r.body.N0 == 1.0
    assert p.st.perk.Strength == 6 and p.st.traits.STOUT is True


def test_a_thin_pick_keeps_the_boosted_start():
    # Task 10c: the thin pick lowers only the fat, to 10 % of the boosted lean's body; fmRef is that lean's no-pick fat
    h = _host(prof_cost=10, prof_strength=2)
    p = _player(h, ["STOUT", "UNDERWEIGHT"])
    r = _new_game(h, p)
    F = sl.trait_start("STOUT", prof=2)[0]
    assert abs(r.body.lm - F) < 1e-12
    assert abs(r.body.fm - 0.10 * F / 0.90) < 1e-9
    assert abs(r.body.fmRef - 4.5 * H2 * F / FAVG) < 1e-9


def test_an_unreadable_profession_builds_no_boost():
    h = _host(prof_cost=10, prof_strength=1)
    h.G.NR_C.noProfession = True
    p = _player(h, [])                                                 # native 6 from the climb, STOUT held
    r = _new_game(h, p)
    # no definition: the inference falls back to the held band (STOUT) and the boost reads 0
    assert abs(r.body.lm - sl.trait_start("STOUT")[0]) < 1e-12


def _first_sight(h, p):
    h.online(p)
    h.T.age = 100.0 + 1 / 60
    h.minute()
    h.tick(3)
    return h.record(p.getUsername(p))


@pytest.mark.parametrize("prof", [0, 1, 2])
@pytest.mark.parametrize("muscle", (None,) + MUSCLE)
@pytest.mark.parametrize("weight", (None, "OVERWEIGHT", "UNDERWEIGHT"))
def test_first_sight_of_vanillas_creation_state_builds_the_creation_body(muscle, weight, prof):
    # the character as applyTraits left it (native level and its band), seen first with no OnNewGame
    picks = [n for n in (muscle, weight) if n]
    h1 = _host(prof_cost=10, prof_strength=prof)
    created = _new_game(h1, _player(h1, picks)).body
    h2 = _host(prof_cost=10, prof_strength=prof)
    seen = _first_sight(h2, _player(h2, picks)).body
    assert h2.NR.server.metabolism.stats.creates == 1
    for k in ("lm", "F0", "Fc", "Pk", "N0", "fm", "fmRef", "fatT", "thinT"):
        assert abs(seen[k] - created[k]) < 1e-12, (muscle, weight, prof, k)


def test_first_sight_reads_the_professions_boost():
    h = _host(prof_cost=10, prof_strength=2)
    p = _player(h, ["STOUT"])
    b = _first_sight(h, p).body
    assert abs(b.lm - sl.trait_start("STOUT", prof=2)[0]) < 1e-12


def test_first_sight_with_an_unreadable_profession_reads_no_boost():
    h = _host(prof_cost=10, prof_strength=2)
    h.G.NR_C.noProfession = True
    p = _player(h, ["STOUT"], strength=5)
    b = _first_sight(h, p).body
    assert abs(b.lm - sl.trait_start("STOUT")[0]) < 1e-12


# --- Task 17b fix 1: the band re-asserted after the level write; a profession's other boosts ---------------------


@pytest.mark.parametrize("prof", [1, 2])
def test_a_stripped_muscle_pick_under_a_boost_ends_holding_its_levels_band(prof):
    # profession cost 0 with no free points: the Stout pick (cost 6) is stripped over the point total
    h = _host(prof_cost=0, prof_strength=prof)
    p = _player(h, ["STOUT"])
    _new_game(h, p)
    assert not p.st.traits.STRONG
    n = p.st.perk.Strength
    assert n == sl.start_level("none", prof)
    want = _band(n)
    for b in MUSCLE:
        assert bool(p.st.traits[b]) == (b == want), (prof, n, b)


def test_a_stripped_strength_giver_leaves_no_stale_band():
    # Gymnast (+2 Strength, cost 5) over the point total: applyTraits climbed to 7 (STOUT); the revert writes 5
    h = _host(prof_cost=0)
    p = _player(h, ["GYMNAST"])
    assert p.st.perk.Strength == 7 and p.st.traits.STOUT is True
    _new_game(h, p)
    assert p.st.perk.Strength == 5
    assert not any(p.st.traits[b] for b in MUSCLE)


def test_a_professions_other_boosts_are_not_its_strength_boost():
    # a profession with Strength +1 and Sprinting +3: only the Strength boost raises the start (and the inference)
    h = _host(prof_cost=10, prof_strength=1)
    h.G.NR_C.profSprint = 3
    p = _player(h, ["STOUT"])
    assert p.st.perk.Strength == 8
    r = _new_game(h, p)
    assert abs(r.body.lm - sl.trait_start("STOUT", prof=1)[0]) < 1e-12
    assert r.body.N0 == sl.LEVEL_MODEL["N0"]["STOUT"]
    assert p.st.perk.Strength == 8
    h2 = _host(prof_cost=10, prof_strength=1)
    h2.G.NR_C.profSprint = 3
    seen = _first_sight(h2, _player(h2, ["STOUT"])).body
    assert abs(seen.lm - r.body.lm) < 1e-12


# --- fix 3: the strip order reads costs and names, never the list order (x422: the server's order is not the client's) --

ILLEGAL = ["OBESE", "OVERWEIGHT", "WEIGHTLOSS", "ATHLETIC", "FIT", "BRAVE", "SPEEDDEMON"]


@pytest.mark.parametrize("known", [ILLEGAL, list(reversed(ILLEGAL)), ILLEGAL[3:] + ILLEGAL[:3]])
def test_one_pick_set_in_any_known_order_strips_the_same_traits(known):
    h = _host(prof_cost=0)
    p = _player(h, known)
    _new_game(h, p)
    lost = sorted(l.split(" loses ")[1].split(" ")[0] for l in _printed(h) if " loses " in l)
    # in CRE.before's order: ATHLETIC (10, before OBESE by name) excludes OBESE; OBESE excludes OVERWEIGHT; FIT (6,
    # before OVERWEIGHT by name) excludes OVERWEIGHT; OVERWEIGHT excludes WEIGHTLOSS; then 0 - (4 + 1) + 2 = -3 strips
    # BRAVE, the costliest positive, and 0 - 1 + 2 = 1 is legal
    assert lost == ["ATHLETIC", "BRAVE", "FIT", "OBESE", "OVERWEIGHT"]
    assert _held(p) == ["SPEEDDEMON", "WEIGHTLOSS"]


def test_a_cost_tie_strips_the_name_first_in_alphabetical_order():
    defs = dict(DEFS)
    defs["BRAVE"] = dict(cost=3, excl=["SPEEDDEMON"])
    defs["SPEEDDEMON"] = dict(cost=3)
    for known in (["BRAVE", "SPEEDDEMON"], ["SPEEDDEMON", "BRAVE"]):
        h = _host(prof_cost=10, defs=defs)
        p = _player(h, known)
        _new_game(h, p)
        assert not p.st.traits.BRAVE and p.st.traits.SPEEDDEMON is True
