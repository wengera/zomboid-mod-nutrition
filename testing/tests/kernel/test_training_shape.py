"""NR_Server_Training, driven through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so each test builds a bare Lua 5.1 runtime
with NR_Core.lua and every NR_Kernel*.lua, an Events stub that records the handlers each Add receives,
a store stand-in whose records the test owns, and registry stand-ins for Perks. NR.call indexes
obj[name] and calls it with obj first, so a Lua table of function fields stands in for a Java object.
A stub proves the wiring, the filters and the guards, not the engine's real getters, which the live
acceptance runs read.
"""
import glob
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
TRAINING = os.path.join(SERVER, "NR_Server_Training.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9

SETUP = r"""
NR_ADDED = { OnServerStarted = {}, AddXP = {}, OnWeaponHitXp = {}, OnWeaponHitTree = {} }
local function ev(name)
    return { Add = function(fn) local t = NR_ADDED[name]; t[#t + 1] = fn end }
end
Events = { OnServerStarted = ev("OnServerStarted"), AddXP = ev("AddXP"), OnWeaponHitXp = ev("OnWeaponHitXp"),
           OnWeaponHitTree = ev("OnWeaponHitTree") }
NR_SERVER = true
isServer = function() return NR_SERVER end
Perks = { Strength = { name = "Strength" }, Fitness = { name = "Fitness" }, Axe = { name = "Axe" } }
NR_RECORDS = {
    admin = { body = { vStr = 0, vHyp = 0, vStrHigh = 0 } },
    nobody = {},
}
NutritionRevamp.server.store = { records = NR_RECORDS, attach = function() return NR_RECORDS end }

function NR_PLAYER(name, exe)
    local p = { exe = exe }
    p.getUsername = function(self) return name end
    p.getFitness = function(self)
        return { getCurrentExe = function(s) return self.exe end }
    end
    p.getLastHitCount = function(self) return self.hits end
    return p
end

function NR_WEAPON(w)
    return { getWeight = function(self) return w end }
end
"""


def _load(rt, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


class Host:
    def __init__(self, start=True):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        _load(self.rt, CORE)
        for path in sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua"))):
            _load(self.rt, path)
        self.rt.execute(SETUP)
        self.G = self.rt.globals()
        self.G.NutritionRevamp.log.level = 0
        _load(self.rt, TRAINING)
        if start:
            self.start()

    def start(self):
        self.rt.execute("for i = 1, #NR_ADDED.OnServerStarted do NR_ADDED.OnServerStarted[i]() end")

    @property
    def TRN(self):
        return self.G.NutritionRevamp.server.training

    @property
    def body(self):
        return self.G.NR_RECORDS["admin"]["body"]

    def handler(self, event):
        return self.G.NR_ADDED[event][1]

    def player(self, name="admin", exe=None):
        return self.G.NR_PLAYER(name, exe)

    def xp(self, p, perk, amount):
        self.handler("AddXP")(p, self.G.Perks[perk], amount)

    def stats(self):
        s = self.TRN.stats
        return {k: s[k] for k in ("reps", "paired", "repsFitnessOnly", "hits", "trees", "ignored", "failures")}

    def banked(self):
        b = self.body
        return (b["vStr"], b["vHyp"], b["vStrHigh"])


@pytest.fixture
def h():
    return Host()


def close(a, b):
    return all(abs(x - y) < TOL for x, y in zip(a, b))


# --- the wiring -----------------------------------------------------------------------------------------

def test_wired_once_at_server_start():
    host = Host(start=False)
    assert len(host.G.NR_ADDED["OnServerStarted"]) == 1
    assert len(host.G.NR_ADDED["AddXP"]) == 0          # nothing at load
    host.start()
    host.start()                                       # a second start wires nothing twice
    for ev in ("AddXP", "OnWeaponHitXp", "OnWeaponHitTree"):
        assert len(host.G.NR_ADDED[ev]) == 1
    assert host.TRN.wired is True


def test_not_wired_off_the_server():
    host = Host(start=False)
    host.G.NR_SERVER = False
    host.start()
    for ev in ("AddXP", "OnWeaponHitXp", "OnWeaponHitTree"):
        assert len(host.G.NR_ADDED[ev]) == 0
    assert host.TRN.wired is False


# --- the reps (ruling T13-2: anchored on the Strength event) ---------------------------------------------

def test_squats_strength_zero_then_fitness_is_one_legs_rep(h):
    p = h.player(exe="squats")
    h.xp(p, "Strength", 0)                             # fired first (Fitness.incStats L351), 0 for legs
    h.xp(p, "Fitness", 4)                              # the same rep's partner (L352): banks nothing
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))
    s = h.stats()
    assert s["reps"] == 1 and s["paired"] == 1 and s["repsFitnessOnly"] == 0 and s["failures"] == 0
    assert h.TRN.pairOpen["admin"] is None


def test_pushups_strength_then_fitness_zero_is_one_arms_rep(h):
    p = h.player(exe="pushups")
    h.xp(p, "Strength", 4)
    h.xp(p, "Fitness", 0)
    assert close(h.banked(), (0.10 * 0.8, 0.10, 0.0))
    s = h.stats()
    assert s["reps"] == 1 and s["paired"] == 1


def test_pushups_with_the_fitness_event_dropped_count_every_rep(h):
    p = h.player(exe="pushups")
    h.xp(p, "Strength", 4)                             # the weight gate (#2647) drops the Fitness partner
    h.xp(p, "Strength", 4)                             # the next rep counts with the pair still open
    assert close(h.banked(), (2 * 0.10 * 0.8, 2 * 0.10, 0.0))
    s = h.stats()
    assert s["reps"] == 2 and s["paired"] == 0
    assert h.TRN.pairOpen["admin"] is True


def test_strength_capped_counts_the_rep_on_fitness(h):
    h.xp(h.player(exe=h.rt.table()), "Fitness", 4)     # no Strength event: Strength XP at its level-10 total
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))
    s = h.stats()
    assert s["reps"] == 1 and s["repsFitnessOnly"] == 1 and s["paired"] == 0


def test_fitness_only_rep_uses_the_readable_key(h):
    h.xp(h.player(exe="bicepscurl"), "Fitness", 0)
    assert close(h.banked(), (0.10 * 0.8, 0.10, 0.0))
    assert h.stats()["repsFitnessOnly"] == 1


def test_a_non_string_exercise_is_never_indexed(h):
    # run x141c: FitnessExercise.type is unreadable and the index attempt logged a stack trace per rep;
    # any non-string exercise goes straight to the inference path, its fields never read
    h.rt.execute("""
        NR_TEST_INDEXED = 0
        NR_TEST_EXE = setmetatable({}, { __index = function(t, k)
            NR_TEST_INDEXED = NR_TEST_INDEXED + 1
            return "burpees"
        end })
    """)
    p = h.player(exe=h.G.NR_TEST_EXE)
    h.xp(p, "Strength", 4)                             # inferred: Strength above 0 is arms
    h.xp(p, "Fitness", 3)
    assert close(h.banked(), (0.10 * 0.8, 0.10, 0.0))
    assert h.stats()["reps"] == 1 and h.stats()["paired"] == 1
    assert h.stats()["failures"] == 0
    assert h.G.NR_TEST_INDEXED == 0


def test_no_index_attempt_in_the_source():
    with open(TRAINING, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    assert "exe.type" not in code and "readType" not in code


def test_unreadable_exercise_with_strength_above_zero_is_arms(h):
    p = h.player(exe=h.rt.table())
    h.xp(p, "Strength", 7)                             # dumbbell press: 4 x 1.8 -> 7 Strength
    h.xp(p, "Fitness", 0)
    assert close(h.banked(), (0.10 * 0.8, 0.10, 0.0))
    assert h.stats()["reps"] == 1


def test_unreadable_exercise_with_strength_zero_is_legs(h):
    p = h.player(exe=h.rt.table())
    h.xp(p, "Strength", 0)
    h.xp(p, "Fitness", 4)
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))
    assert h.stats()["reps"] == 1


def test_unknown_exercise_key_reads_legs(h):
    h.xp(h.player(exe="jumpingjacks"), "Strength", 4)
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))


def test_strength_without_exercise_is_ignored_and_clears_the_pair(h):
    h.xp(h.player(exe="pushups"), "Strength", 4)       # a rep; its Fitness partner dropped
    assert h.TRN.pairOpen["admin"] is True
    h.xp(h.player(exe=None), "Strength", 6)            # a knockback or load grant
    assert h.TRN.pairOpen["admin"] is None
    assert close(h.banked(), (0.10 * 0.8, 0.10, 0.0))
    s = h.stats()
    assert s["ignored"] == 1 and s["reps"] == 1
    h.xp(h.player(exe="squats"), "Fitness", 4)         # no open pair now: a Fitness-only rep
    assert h.stats()["repsFitnessOnly"] == 1


def test_fitness_without_exercise_is_ignored(h):
    h.xp(h.player(exe=None), "Fitness", 4)
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats()["ignored"] == 1


def test_rust_is_ignored(h):
    h.xp(h.player(exe="squats"), "Strength", -1)
    h.xp(h.player(exe="squats"), "Fitness", -1)
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats()["ignored"] == 2 and h.stats()["reps"] == 0


def test_other_perks_are_not_counted(h):
    h.xp(h.player(exe="squats"), "Axe", 10)
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats() == {"reps": 0, "paired": 0, "repsFitnessOnly": 0, "hits": 0, "trees": 0, "ignored": 0,
                         "failures": 0}


def test_exercise_class_table_matches_the_install():
    host = Host(start=False)
    t = host.TRN.EXERCISE_CLASS
    assert dict(t.items()) == {"squats": "legs", "pushups": "arms", "situp": "abs", "burpees": "legs",
                               "barbellcurl": "arms", "dumbbellpress": "arms", "bicepscurl": "arms"}


# --- the hits and the trees ------------------------------------------------------------------------------

def test_a_heavy_weapon_hit_event_banks_one_hit(h):
    p = h.player()
    p["hits"] = 2                                    # a two-target swing: this is one of its two events
    h.handler("OnWeaponHitXp")(p, h.G.NR_WEAPON(3), None, 1.0, 1)
    assert close(h.banked(), (0.05, 0.05, 0.05))
    assert h.stats()["hits"] == 1


def test_light_weapon_hit_with_no_hit_count(h):
    h.handler("OnWeaponHitXp")(h.player(), h.G.NR_WEAPON(1.5), None, 1.0, 1)
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))


def test_weapon_without_weight_reads_moderate(h):
    h.handler("OnWeaponHitXp")(h.player(), h.rt.table(), None, 1.0, 1)
    assert close(h.banked(), (0.05 * 0.8, 0.05, 0.0))


def test_tree_hit(h):
    h.handler("OnWeaponHitTree")(h.player(), h.G.NR_WEAPON(3))
    assert close(h.banked(), (0.07, 0.07, 0.07))
    assert h.stats()["trees"] == 1


def test_raising_getter_counts_a_failure_and_banks_nothing(h):
    weapon = h.rt.eval("{ getWeight = function(self) error('boom') end }")
    h.handler("OnWeaponHitXp")(h.player(), weapon, None, 1.0, 1)   # never raises into the dispatch
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats()["failures"] == 1 and h.stats()["hits"] == 0
    assert "boom" in str(h.TRN.lastError)


def test_zombie_owner_does_nothing(h):
    zombie = h.rt.table()                              # no getUsername
    h.handler("OnWeaponHitXp")(zombie, h.G.NR_WEAPON(3), None, 1.0, 1)
    h.handler("OnWeaponHitTree")(zombie, h.G.NR_WEAPON(3))
    h.handler("OnWeaponHitXp")(None, h.G.NR_WEAPON(3), None, 1.0, 1)
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats() == {"reps": 0, "paired": 0, "repsFitnessOnly": 0, "hits": 0, "trees": 0, "ignored": 0,
                         "failures": 0}


def test_no_record_or_no_body_never_creates(h):
    h.handler("OnWeaponHitTree")(h.player(name="stranger"), h.G.NR_WEAPON(3))
    h.handler("OnWeaponHitTree")(h.player(name="nobody"), h.G.NR_WEAPON(3))
    h.xp(h.player(name="stranger", exe="squats"), "Fitness", 4)
    assert h.G.NR_RECORDS["stranger"] is None
    assert h.G.NR_RECORDS["nobody"]["body"] is None
    assert h.stats() == {"reps": 0, "paired": 0, "repsFitnessOnly": 0, "hits": 0, "trees": 0, "ignored": 0,
                         "failures": 0}


def test_limitations_name_the_rep_and_the_climb():
    lim = list(Host(start=False).TRN.limitations.values())
    assert "a climb or vault has no Lua event and is sampled per minute from the character's state" in lim
    assert ("a rep is counted on the Strength XP event (unconditional, 0 for a legs exercise); vanilla's "
            "Fitness-XP gate (#2647) cannot drop it; a character whose Strength XP sits at the level-10 total "
            "fires no Strength event, and its reps are counted on the Fitness event instead; a Fitness-only rep "
            "after a stale open pair is read as the partner") in lim
    assert not any("Task 12" in x for x in lim)


# --- Plan 11 Task 5: the server fires OnWeaponHitXp once per target, and a ranged hit banks nothing -------------

RANGED = "function(w) return { getWeight = function(self) return w end, isRanged = function(self) return true end } end"


def test_a_three_target_swing_banks_three_hits_not_nine(h):
    p = h.player()
    p["hits"] = 3                                    # getLastHitCount() answers 3 during the swing
    for _ in range(3):                               # the server fires the event once per target (WeaponHit.process)
        h.handler("OnWeaponHitXp")(p, h.G.NR_WEAPON(3), None, 1.0, 1)
    assert close(h.banked(), (0.15, 0.15, 0.15))     # 3 x S_HIT 0.05, high class; 1.0.0 banked 3 x 3 x 0.05
    assert h.stats()["hits"] == 3


def test_a_ranged_hit_banks_nothing(h):
    p = h.player()
    p["hits"] = 1
    h.handler("OnWeaponHitXp")(p, h.rt.eval(RANGED)(3), None, 1.0, 1)
    assert close(h.banked(), (0.0, 0.0, 0.0))
    assert h.stats()["hits"] == 0
