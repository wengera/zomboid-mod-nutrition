"""The food hedonics seats (Plan 19 Task 6; NR_Server_Hedonics.lua, the intake's and the writer's calls into it).

R1: an eat books its kcal into record.hedonics, a dish as not plain, and the writer minute composes the ring's floor
with monotony's UNHAPPINESS target. R2: the server wrapper of ISAddItemInRecipe.complete scales a dish's relief by the
chef's Cooking level after each add, restores the vanilla value before the next, and never compounds. R3: before
vanilla's eat a sad food's field is lowered while the HUNGER stat is over the threshold, and the remainder's field is
restored after it. R4: a dish's taste class is its ingredient TYPE of most summed kcal (ruling T6-1 as refined: the
adapter hands K.hedonics.dishClass one entry a type). Each test names the plausible wrong change it fails. Rule 6: the
Java calls an eat adds are counted on stubs.
"""
import re

import pytest

from .server_host import Host, SERVER
import os

ENV = r"""
CharacterStat = { HUNGER = "HUNGER", UNHAPPINESS = "UNHAPPINESS", BOREDOM = "BOREDOM" }
Perks = { Cooking = "Cooking" }
NR_T.synced = 0
sendItemStats = function(item) NR_T.synced = NR_T.synced + 1 end
-- vanilla's add-ingredient action, as the hedonics seat sees it: complete calls the recipe's addItem, which may make a
-- new dish (NR_T.newDish) and rewrites the dish's stored UnhappyChange by the add's term (NR_T.term, -5 an ingredient)
ISAddItemInRecipe = {}
ISAddItemInRecipe.complete = function(self)
    if NR_T.newDish ~= nil then
        self.baseItem = NR_T.newDish
        NR_T.newDish = nil
    end
    self.baseItem.u = self.baseItem.u + NR_T.term
    return true
end
-- a Food's mood fields: u the stored field, t the read-time state terms; every member call counted in NR_T.calls
NR_T.calls = 0
NR_T.item = function(u, terms, hung)
    local it = { u = u, t = terms or 0, hung = hung or -0.2, md = {}, inv = true }
    local function count() NR_T.calls = NR_T.calls + 1 end
    it.getUnhappyChange = function(s) count(); return s.u + s.t end
    it.getUnhappyChangeUnmodified = function(s) count(); return s.u end
    it.setUnhappyChange = function(s, v) count(); s.u = v end
    it.getHungChange = function(s) count(); return s.hung end
    it.getModData = function(s) count(); return s.md end
    it.getContainer = function(s) count(); if s.inv then return {} end return nil end
    it.fs = 0
    it.syncItemFields = function(s) s.fs = s.fs + 1 end                   -- the field sync, counted apart from calls
    return it
end
NR_T.eater = function(hunger, level)
    local stats = { get = function(s, k) NR_T.calls = NR_T.calls + 1; if k == "HUNGER" then return hunger end return 0 end }
    return { getStats = function(s) NR_T.calls = NR_T.calls + 1; return stats end,
             getPerkLevel = function(s, p) NR_T.calls = NR_T.calls + 1; if p == "Cooking" then return level end return 0 end,
             getUsername = function(s) return "admin" end }
end
"""
AGE = 1000.0


@pytest.fixture
def h():
    host = Host(ENV)
    host.T.age = AGE
    host.T.term = -5
    return host


def HD(h):
    return h.NR.server.hedonics


def dv(h, name):
    return h.K.hedonics[name]


# --- R4: a dish's class by ingredient type ----------------------------------------------------------------------------


def kcal(h, t):
    return h.NR.data.nutrients.get(t).calories


def test_a_dish_class_is_its_ingredient_type_of_most_summed_kcal(h):
    # ruling T6-1 as refined: three carrot portions (savoury) and one meat portion (BaconRashers, fatty) where the
    # carrots sum higher read the carrots' class. Mutation: a class by the heaviest single portion reads fatty here.
    car, meat = kcal(h, "Base.Carrots"), kcal(h, "Base.BaconRashers")
    assert h.NR.data.hedonics.get("Base.Carrots")[1] == "savoury"
    assert h.NR.data.hedonics.get("Base.BaconRashers")[1] == "fatty"
    assert car < meat < 3 * car                                          # one portion loses, three types summed win
    dish = h.rt.table("Base.Carrots", "Base.BaconRashers", "Base.Carrots", "Base.Carrots")
    assert HD(h).dishClass(dish) == "savoury"
    assert HD(h).dishClass(h.rt.table("Base.Carrots", "Base.BaconRashers")) == "fatty"
    assert HD(h).dishClass(h.rt.table("NRTest.Unknown", "Base.BaconRashers")) == "fatty"   # no class: counts for none
    assert HD(h).dishClass(h.rt.table()) is None


def test_the_eat_taste_dish_against_plain_food(h):
    plain_b = h.rt.table()
    plain_b.fullType = "Base.Butter"
    plain_b.extraTypes = h.rt.table()
    assert tuple(HD(h).tasteOf(plain_b)) == (True, "fatty")
    dish = h.rt.table()
    dish.fullType = "Base.Butter"                                        # a dish is never plain, whatever its type
    dish.extraTypes = h.rt.table("Base.Carrots", "Base.Carrots", "Base.Carrots", "Base.BaconRashers")
    assert tuple(HD(h).tasteOf(dish)) == (False, "savoury")


# --- R1 and R4 through the intake's landing ---------------------------------------------------------------------------


EAT = r"""
function(user, fullType, cal, carb, lip, pro, extra)
    local NR = NutritionRevamp
    local IN = NR.server.intake
    local item = { getHungChange = function(s) return 0 end, getThirstChangeUnmodified = function(s) return 0 end }
    local b = { item = item, username = user, rawBefore = -0.2, fullType = fullType, instBase = -0.2, thirstBefore = 0,
                cal = cal, carb = carb, lip = lip, pro = pro, cooked = false, burnt = false, rotten = false,
                frozen = false, scriptHunger = -0.2, scriptThirst = 0, extraTypes = extra or {}, craftMap = nil }
    b.macros = { calories = cal, carbs = carb, lipids = lip, proteins = pro }
    local rec = NR.server.store.get(user, NR.worldAge())
    rec.stomach = rec.stomach or NR.kernel.stomach.new()
    rec.pool = rec.pool or NR.kernel.vector.new()
    IN.readAfterAndLand(b)
    return rec
end
"""


def eat(h, fullType, cal, carb, lip, pro, extra=None):
    return h.rt.eval(EAT)("admin", fullType, cal, carb, lip, pro, extra)


def ring_sums(rec):
    p = sum(rec.hedonics.p[k] for k in range(1, 25))
    a = sum(rec.hedonics.a[k] for k in range(1, 25))
    return p, a


def test_a_plain_eat_books_its_kcal_as_plain_and_its_class(h):
    rec = eat(h, "Base.Butter", 800.0, 0.0, 88.0, 1.0)
    p, a = ring_sums(rec)
    assert a > 0 and p == pytest.approx(a)                               # the landed kcal, all plain
    assert rec.lastIntake.plain is True and rec.lastIntake["class"] == "fatty" and rec.lastIntake.allies == 1
    assert rec.monotony.t["@fatty"].n == pytest.approx(rec.monotony.t["Base.Butter"].n * dv(h, "CLASS_W"))
    assert HD(h).stats.booked == 1 and HD(h).stats.plain == 1


def test_a_dish_books_as_not_plain_with_its_main_type_class(h):
    # mutation: a dish booked by its own type's plain flag (Butter's) fails here
    extra = h.rt.table("Base.Carrots", "Base.Carrots", "Base.Carrots", "Base.BaconRashers")
    rec = eat(h, "Base.Butter", 120.0, 12.0, 6.0, 4.0, extra)
    p, a = ring_sums(rec)
    assert a > 0 and p == 0
    assert rec.lastIntake.plain is False and rec.lastIntake["class"] == "savoury"
    assert rec.monotony.t["@savoury"] is not None and rec.monotony.t["@fatty"] is None


def test_a_corrupt_ring_is_healed_at_the_eat(h):
    rec = eat(h, "Base.Carrots", 25.0, 6.0, 0.1, 0.6)
    rec.hedonics.p = "garbage"
    eat(h, "Base.Carrots", 25.0, 6.0, 0.1, 0.6)
    assert HD(h).stats.healed == 1 and ring_sums(rec)[1] > 0


def test_a_failed_booking_is_counted_and_monotony_still_books(h):
    h.rt.execute("NutritionRevamp.server.hedonics.tasteOf = function() error('boom') end")
    rec = eat(h, "Base.Carrots", 25.0, 6.0, 0.1, 0.6)
    assert HD(h).stats.bookFailures == 1
    assert rec.monotony.t["Base.Carrots"] is not None and rec.monotony.t["@savoury"] is None


# --- R1: the writer's floor -------------------------------------------------------------------------------------------


MONO = r"""
function(rec, ageH, seen)
    local W = NutritionRevamp.server.writer
    local h = { stats = { get = function(s, k) return 0 end }, monoSeen = seen }
    local inp = {}
    W.monotony(h, rec, inp, {}, ageH)
    return inp.unhappyTarget, inp.boredTarget
end
"""


def full_ring(h, kcal_plain, kcal_all, age=AGE):
    K = h.K
    ring = K.hedonics.new(age)
    K.hedonics.book(ring, age, kcal_all - kcal_plain, False)
    K.hedonics.book(ring, age, kcal_plain, True)
    rec = h.rt.table()
    rec.hedonics = ring
    return rec


def test_the_writer_composes_the_plain_floor_into_unhappiness(h):
    # mutation: the floor left out of W.monotony (or added to BOREDOM) fails here
    rec = full_ring(h, 3000.0, 3000.0)
    u, b = h.rt.eval(MONO)(rec, AGE + 0.5, False)
    want = h.K.hedonics.floorOf(1.0)
    assert want > 0
    assert u == pytest.approx(want) and b == 0
    assert rec.hedonics.f == pytest.approx(want)                         # kept on the ring for the minute ring
    rec2 = full_ring(h, 0.0, 3000.0)
    assert h.rt.eval(MONO)(rec2, AGE + 0.5, False)[0] == 0


def test_the_floor_releases_as_the_ring_rotates_and_never_offline(h):
    # mutation: a rotate that never moves holds the floor for ever and fails here
    rec = full_ring(h, 3000.0, 3000.0)
    assert h.rt.eval(MONO)(rec, AGE + 23.5, True)[0] == pytest.approx(h.K.hedonics.floorOf(1.0))
    assert h.rt.eval(MONO)(rec, AGE + 24.5, True)[0] == 0               # the 24 online hours rolled off
    rec3 = full_ring(h, 3000.0, 3000.0)
    rec3.lastSeen = AGE
    h.K.resume.resume(rec3, AGE + 100.0)                                 # an absence: the stamp moves, no slot rolls off
    assert h.rt.eval(MONO)(rec3, AGE + 100.5, True)[0] == pytest.approx(h.K.hedonics.floorOf(1.0))


def test_the_writer_heals_a_corrupt_ring_at_first_sight_only(h):
    rec = full_ring(h, 3000.0, 3000.0)
    rec.hedonics.i = 99
    g0 = h.NR.server.writer.stats.guarded
    assert h.rt.eval(MONO)(rec, AGE + 0.5, False)[0] == 0                # reset to a fresh ring
    assert h.NR.server.writer.stats.guarded == g0 + 1 and rec.hedonics.i == 1
    assert h.rt.eval(MONO)(h.rt.table(), AGE + 0.5, False)[0] == 0       # no ring: no floor


# --- R3: around vanilla's eat -----------------------------------------------------------------------------------------


def snapshot(h, item, hunger):
    b = h.rt.table()
    b.item = item
    b.player = h.T.eater(hunger, 0)
    b.rawBefore = item.hung
    return b


def vanilla_eat(item, frac):
    """vanilla's Eat on the field: what it applies (read-time value x frac) and the remainder's scale (multiplyFoodValues)."""
    applied = (item.u + item.t) * frac
    item.u = item.u * (1 - frac)
    item.hung = item.hung * (1 - frac)
    return applied


def at(h):
    return h.K.hungerCurve.THRESHOLDS[int(dv(h, "ALLIES_LEVEL"))]


def test_a_hungry_eater_feels_a_sad_food_at_allies_f_and_the_remainder_keeps_its_own(h):
    # mutation: the restore skipped (the remainder keeps the lowered field) fails here
    item = h.T.item(20.0, 10.0)                                          # +20 base, +10 stale: +30 read
    b = snapshot(h, item, at(h) + 0.1)
    HD(h).alliesBefore(b)
    applied = vanilla_eat(item, 0.25)
    HD(h).alliesAfter(b)
    assert applied == pytest.approx(30.0 * 0.25 * dv(h, "ALLIES_F"))
    assert item.u == pytest.approx(20.0 * 0.75)
    assert b.allies.scale == pytest.approx(dv(h, "ALLIES_F")) and h.T.synced == 1


def test_r3_leaves_a_happy_food_and_a_sated_eater(h):
    # mutation: the happy side scaled, or the Hungry gate dropped, fails here
    for u, hunger in ((-10.0, 0.9), (20.0, at(h))):
        item = h.T.item(u)
        b = snapshot(h, item, hunger)
        HD(h).alliesBefore(b)
        assert item.u == u and b.allies is None
    assert HD(h).stats.allies == 0


def test_a_written_zero_field_restores_by_the_hunger_ratio(h):
    # the field R3 writes is 0 exactly when the field is the part R3 takes off: vanilla's remainder scale then reads
    # off the raw hunger (mutation: restoring the whole field there fails here)
    f = dv(h, "ALLIES_F")
    take = 20.0 * (1 - f)
    item = h.T.item(take, 20.0 - take)                                   # read +20
    b = snapshot(h, item, 0.9)
    HD(h).alliesBefore(b)
    assert b.allies.written == 0
    vanilla_eat(item, 0.5)
    HD(h).alliesAfter(b)
    assert item.u == pytest.approx(take * 0.5) and h.T.synced == 1
    item2 = h.T.item(0.0, 20.0)                                          # a rotten +20 on a 0 base field
    item2.inv = False                                                    # finished: restored
    b2 = snapshot(h, item2, 0.9)
    HD(h).alliesBefore(b2)
    assert b2.allies.written == pytest.approx(-take)                     # under 0 across the state term
    vanilla_eat(item2, 1.0)
    HD(h).alliesAfter(b2)
    assert item2.u == pytest.approx(0.0) and h.T.synced == 1                    # finished: not synced


def test_r3_syncs_the_restored_item_after_a_hungry_eat_of_a_sad_food(h):
    # x503: vanilla's part-eat sends the lowered read-time value; the client keeps it until a sync after the restore
    # (mutation: the sync line removed from H.restore fails here)
    item = h.T.item(20.0, 10.0)
    b = snapshot(h, item, 0.9)
    HD(h).alliesBefore(b)
    vanilla_eat(item, 0.25)
    h.T.synced = 0
    HD(h).alliesAfter(b)
    assert h.T.synced == 1
    src = open(os.path.join(SERVER, "NR_Server_Hedonics.lua"), encoding="utf-8").read()
    assert 'if NR.obj(b.item, "getContainer") ~= nil then H.sync(b.item) end' in src


def test_the_intake_seats_r3_on_an_eat_and_a_cancel_never_a_drink(h):
    h.rt.execute("""
        NR_T.seen = {}
        local H = NutritionRevamp.server.hedonics
        H.alliesBefore = function(b) NR_T.seen[#NR_T.seen + 1] = 'before' end
        H.alliesAfter = function(b) NR_T.seen[#NR_T.seen + 1] = 'after' end
    """)
    IN = h.NR.server.intake
    for kind in ("eat", "cancel", "drink", "world"):
        IN.hedonicsBefore(h.rt.table(), kind)
        IN.hedonicsAfter(h.rt.table(), kind)
    assert list(h.T.seen.values()) == ["before", "after", "before", "after"]
    src = open(os.path.join(SERVER, "NR_Server_Intake.lua"), encoding="utf-8").read()
    assert "IN.hedonicsBefore(b, kind)" in src and "IN.hedonicsAfter(b, kind)" in src


def test_rule_6_an_eat_of_a_food_that_is_not_sad_adds_one_java_call(h):
    for u in (0.0, -10.0):
        item = h.T.item(u)
        b = snapshot(h, item, 0.9)
        h.T.calls = 0
        HD(h).alliesBefore(b)
        HD(h).alliesAfter(b)
        assert h.T.calls == 1                                            # getUnhappyChange
    item = h.T.item(20.0)
    b = snapshot(h, item, 0.1)
    h.T.calls = 0
    HD(h).alliesBefore(b)
    HD(h).alliesAfter(b)
    assert h.T.calls == 3                                                # a sad food, sated: + getStats, get
    item = h.T.item(20.0)
    b = snapshot(h, item, 0.9)
    h.T.calls = 0
    HD(h).alliesBefore(b)
    HD(h).alliesAfter(b)
    assert h.T.calls == 8 and h.T.synced == 1                            # a sad food, Hungry: + getContainer, one item sync


# --- R2: the add-ingredient seat --------------------------------------------------------------------------------------


def same(h, a, b):
    return h.rt.eval("function(a, b) return rawequal(a, b) end")(a, b)


def add(h, dish, level, new=None):
    action = h.rt.table()
    action.baseItem = dish
    action.character = h.T.eater(0.0, level)
    h.T.newDish = new
    ok = h.G.ISAddItemInRecipe.complete(action)
    return action, ok


def test_the_add_seat_is_wrapped_once_and_calls_the_original(h):
    assert HD(h).wrappedCook is True
    w = h.G.ISAddItemInRecipe.complete
    HD(h).install()
    assert same(h, h.G.ISAddItemInRecipe.complete, w)
    dish = h.T.item(0.0)
    action, ok = add(h, dish, 3)
    assert ok is True and HD(h).stats.cooks == 1


def test_a_chef_scales_the_relief_once_never_compounded(h):
    # mutation: no restore before the next add (the scale compounds over the adds) fails here
    q10 = h.K.hedonics.prepScale(10)
    pot = h.T.item(3.0)                                                  # the base (a pot of water)
    dish = h.T.item(0.0)
    action, _ = add(h, pot, 10, new=dish)                                # phase A: a new dish, -5
    assert same(h, action.baseItem, dish)
    assert dish.u == pytest.approx(-5 * q10) and dish.md.NR_PrepS == pytest.approx(q10)
    add(h, dish, 10)
    add(h, dish, 10)
    assert dish.u == pytest.approx(-15 * q10)
    add(h, dish, 0)                                                      # the last add's chef sets the whole dish
    assert dish.u == pytest.approx(-20 * h.K.hedonics.prepScale(0))
    assert HD(h).stats.prepped == 4 and h.T.synced == 4
    assert dish.fs == 4 and pot.fs == 0                                  # the dish's fields synced at each stamp change


def test_an_add_that_clears_a_stamp_without_restamping_syncs_the_fields(h):
    dish = h.T.item(0.0)
    add(h, dish, 10)
    assert dish.fs == 1
    h.T.term = 5                                                         # the next add makes the dish sad: no restamp
    add(h, dish, 10)
    assert dish.md.NR_PrepS is None and dish.fs == 2
    add(h, dish, 10)                                                     # no stamp to clear, none made: no sync
    assert dish.fs == 2


def test_a_state_term_never_enters_the_prepared_field(h):
    # mutation: prepDish reading the read-time getUnhappyChange bakes the cold dish's +2 into the field
    q10 = h.K.hedonics.prepScale(10)
    dish = h.T.item(0.0, 2.0)
    add(h, dish, 10)
    assert dish.u == pytest.approx(-5 * q10)


def test_a_part_eaten_dish_restores_exactly(h):
    q10 = h.K.hedonics.prepScale(10)
    dish = h.T.item(0.0)
    add(h, dish, 10)
    add(h, dish, 10)                                                     # vanilla -10, stored -10 q10
    dish.u = dish.u * 0.5                                                # half eaten: vanilla scales the field
    add(h, dish, 10)                                                     # vanilla -5 then -5 more
    assert dish.u == pytest.approx(-10 * q10)


def test_a_sad_or_neutral_dish_stays_vanilla(h):
    # mutation: the sad side scaled by skill fails here
    h.T.term = 5
    dish = h.T.item(10.0)
    add(h, dish, 10)
    assert dish.u == 15 and dish.md.NR_PrepS is None
    assert HD(h).stats.prepped == 0


def test_the_client_passes_through(h):
    h.T.server = False
    dish = h.T.item(0.0)
    add(h, dish, 10)
    assert dish.u == -5 and HD(h).stats.passthrough == 1 and HD(h).stats.cooks == 0


def test_a_raising_dish_never_blocks_the_add(h):
    dish = h.T.item(0.0)
    h.rt.execute("NR_T.boom = function() error('boom') end")
    dish.setUnhappyChange = h.T.boom
    action, ok = add(h, dish, 10)
    assert ok is True and dish.u == -5 and HD(h).stats.cookFailures == 1


def test_the_file_states_its_seats_and_rule_6():
    src = open(os.path.join(SERVER, "NR_Server_Hedonics.lua"), encoding="utf-8").read()
    assert "ISAddItemInRecipe.complete" in src and "OnCooked was not" in src
    assert re.search(r"^\s*--\s*@fastpath", src, re.M) is None and "OnTick" not in src and "EveryOneMinute" not in src
    assert "ISAddItemInRecipe.new" in src                                # named only as the method never wrapped
