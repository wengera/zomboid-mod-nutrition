"""NR_Server_Creation, the OnNewGame creation handler (Plan 13 Task 17; spec section 3.2; rulings 13-16, 13-31, 13-46).

The handler runs on server_host's Host (every server/ file in load order, OnServerStarted fired), so the wiring is the
real one: NR_Server_Players' OnNewGame fires P.onNewGame after store.reset, NR_Server_Creation validates the picks,
builds the body through NR_Server_Metabolism's builder and writes the weight, the Strength level (NR_Server_Strength)
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
LADDER = [1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500]

ENV = r"""
NR_C = { log = {}, defs = {}, profCost = 0, profGrants = {}, penalty = 1, grants = {} }
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
    return { getCost = function(s) return NR_C.profCost end, getGrantedTraits = function(s) return list(granted) end }
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
    "WEAK": dict(cost=-10, excl=["FEEBLE", "STOUT", "STRONG", "UNDERWEIGHT", "VERY_UNDERWEIGHT"]),
    "FEEBLE": dict(cost=-6, excl=["STOUT", "STRONG", "WEAK", "UNDERWEIGHT", "VERY_UNDERWEIGHT"]),
    "STOUT": dict(cost=6, excl=["FEEBLE", "STRONG", "WEAK"]),
    "STRONG": dict(cost=10, excl=["FEEBLE", "STOUT", "WEAK"]),
    "OBESE": dict(cost=-10, excl=["ATHLETIC", "EMACIATED", "FIT", "LIGHTEATER", "VERY_UNDERWEIGHT", "UNDERWEIGHT",
                                  "OVERWEIGHT", "WEIGHTLOSS"]),
    "OVERWEIGHT": dict(cost=-6, excl=["ATHLETIC", "FIT", "EMACIATED", "VERY_UNDERWEIGHT", "UNDERWEIGHT", "OBESE",
                                      "WEIGHTLOSS"]),
    "UNDERWEIGHT": dict(cost=-6, excl=["OBESE", "VERY_UNDERWEIGHT", "OVERWEIGHT", "WEAK", "FEEBLE", "WEIGHTGAIN"]),
    "VERY_UNDERWEIGHT": dict(cost=-10, excl=["ATHLETIC", "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "WEAK", "FEEBLE",
                                             "WEIGHTGAIN", "WEIGHTLOSS"]),
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


def _host(prof_cost=8, female=False, sex_specific=False, defs=DEFS):
    h = Host(extra_env=ENV)
    C = h.G.NR_C
    for name, spec in defs.items():
        t = h.rt.table()
        for k, v in spec.items():
            t[k] = h.rt.table(*v) if isinstance(v, list) else (h.rt.table_from(v) if isinstance(v, dict) else v)
        C.defs[name] = t
    C.profCost = prof_cost
    h.NR.server.options.sexSpecific = sex_specific
    return h


def _player(h, known, name="a", **cfg):
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
    assert abs(b.fm - 21.675) < 1e-9
    assert b.fatT == 1 and b.thinT == 0
    assert abs(p.nut.weight - (F + 21.675)) < 1e-9          # the weight is the body's, not vanilla's 95 kg
    assert h.NR.server.creation.stats.created == 1


def test_the_level_write_lands_nine_with_strong():
    h = _host()
    p = _player(h, ["STRONG", "OVERWEIGHT"])
    r = _new_game(h, p)
    assert p.st.perk.Strength == 9
    assert p.st.traits.STRONG is True
    assert not p.st.traits.STOUT
    assert r.body.wroteL == 9 and r.body.levelDue is False
    assert p.st.traits.OVERWEIGHT is True


def test_the_order_weight_then_level_then_the_weight_band_traits():
    h = _host(prof_cost=10)
    p = _player(h, ["STRONG", "EMACIATED"])                  # Emaciated is read as Very Underweight: the trait write swaps it
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
    assert _held(p) == ["FEEBLE", "VERY_UNDERWEIGHT"]               # Strong thinned to level 3.83: Feeble's band


def test_weak_and_underweight_lose_the_later_pick():
    h = _host()
    p = _player(h, ["WEAK", "UNDERWEIGHT"])
    r = _new_game(h, p)
    assert not p.st.traits.UNDERWEIGHT and p.st.traits.WEAK is True
    assert r.body.thinT == 0 and r.body.N0 == sl.LEVEL_MODEL["N0"]["WEAK"]
    assert any("loses UNDERWEIGHT" in s and "excluded by WEAK" in s for s in _printed(h))
    h2 = _host()
    p2 = _player(h2, ["UNDERWEIGHT", "WEAK"])
    r2 = _new_game(h2, p2)
    assert not p2.st.traits.WEAK and p2.st.traits.UNDERWEIGHT is True
    assert r2.body.thinT == 1 and r2.body.N0 == 1.0


def test_the_kernel_pairs_hold_when_no_definition_lists_them():
    defs = dict(DEFS)
    defs["WEAK"] = dict(cost=-10)
    defs["UNDERWEIGHT"] = dict(cost=-6)
    h = _host(defs=defs)
    p = _player(h, ["WEAK", "UNDERWEIGHT"])
    r = _new_game(h, p)
    assert r.body.thinT == 0                                    # built without the thin pick
    assert any("loses UNDERWEIGHT" in s and "excluded by WEAK" in s for s in _printed(h))


def test_overweight_and_obese_lose_the_later():
    h = _host()
    p = _player(h, ["OVERWEIGHT", "OBESE"])
    r = _new_game(h, p)
    assert p.st.traits.OVERWEIGHT is True and not p.st.traits.OBESE
    assert r.body.fatT == 1


@pytest.mark.parametrize("known, lost", [
    (["ATHLETIC", "WEIGHTGAIN"], "WEIGHTGAIN"),      # Athletic's list does not hold Weight Gain: the reverse read
    (["WEIGHTGAIN", "ATHLETIC"], "ATHLETIC"),        # Weight Gain's list holds Athletic: the forward read
    (["WEIGHTLOSS", "OBESE"], "OBESE"),
    (["OBESE", "WEIGHTLOSS"], "WEIGHTLOSS"),
])
def test_the_exclusion_check_runs_both_ways(known, lost):
    h = _host(prof_cost=10)
    p = _player(h, known)
    _new_game(h, p)
    kept = [n for n in known if n != lost]
    assert not p.st.traits[lost]
    assert all(p.st.traits[n] is True for n in kept)


def test_an_over_budget_list_loses_its_last_positive_picks_until_legal_each_logged():
    # profession 0: STRONG 10, BRAVE 4, SPEEDDEMON 1, OVERWEIGHT -6 -> remaining 0 - 15 + 6 = -9; stripping SPEEDDEMON
    # (-8) then BRAVE (-4) then STRONG (+6) makes it legal; the bad trait at the end stays
    h = _host(prof_cost=0)
    p = _player(h, ["STRONG", "BRAVE", "SPEEDDEMON", "OVERWEIGHT"])
    _new_game(h, p)
    assert _held(p) == ["OVERWEIGHT"]
    lines = [s for s in _printed(h) if "over the point total" in s]
    assert [l.split(" loses ")[1].split(" ")[0] for l in lines] == ["SPEEDDEMON", "BRAVE", "STRONG"]
    assert h.NR.server.creation.stats.stripped == 3


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
    h.G.NR_C.profGrants = h.rt.table("BRAVE")                   # a profession grant, though not isFree
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
    p2 = _player(h, ["FEEBLE", "OBESE"], strength=5)
    r2 = _new_game(h, p2)
    assert r2.resets == 1
    assert abs(r2.body.lm - sl.trait_start("FEEBLE")[0]) < 1e-9
    assert abs(r2.body.fm - 12.5 * H2) < 1e-9
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
    h = _host()
    p = _player(h, ["STRONG"], asleep=True)
    r = _new_game(h, p)
    assert r.body.levelDue is True and p.st.perk.Strength == 5
    assert h.NR.server.creation.stats.failures == 0


def test_a_raising_write_is_counted_and_the_level_stays_due():
    h = _host()
    h.rt.execute("NutritionRevamp.server.strength.writeLevel = function() error('boom') end")
    p = _player(h, ["STRONG"])
    r = _new_game(h, p)
    assert h.NR.server.creation.stats.failures == 1
    assert "boom" in str(h.NR.server.creation.lastError)
    assert r.body.levelDue is True                              # the Strength minute writes it
