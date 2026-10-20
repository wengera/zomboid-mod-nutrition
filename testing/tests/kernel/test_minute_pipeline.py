"""The slow minute's explicit pipeline (Plan 10 Task R2): NR_Server_Minute.lua.

The declared ORDER is the order that runs; the players' file keeps no minute hook list; a raising step does not
stop the steps after it; registering a name again replaces its function; the context is cleared per player run.

The Effects hand-off (the R0 reviews' M4): the golden trace cannot see a wrong body, dtM or ageH on the context, so
a recorder around the Effects minute (what the step hands it) pins them here on golden_trace's decorated player: ctx.body is record.body, ctx.dtM is 30
on the minute a player returns after 30 game minutes away, ctx.ageH is the world age, and a record forced lethal
on that minute takes ReduceGeneralHealth == the drain's rate x 30 minutes (K.drain, Plan 15 Task 4).
"""
import math

import pytest

from . import golden_trace
from .server_host import Host

ORDER = ["bus", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "writer", "store"]


def _order(M):
    return [M.ORDER[i] for i in range(1, len(M.ORDER) + 1)]


def test_the_declared_order_is_the_order_that_runs():
    h = Host()
    M = h.NR.server.minute
    order = _order(M)
    assert order == ORDER
    ran = h.rt.eval("{}")
    for name in order:
        M.register(name, h.rt.eval("function(t, n) return function() t[#t + 1] = n end end")(ran, name))
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    assert [ran[i] for i in range(1, len(ran) + 1)][-len(order):] == order


def test_every_adapter_registers_its_named_step():
    h = Host()
    S = h.NR.server
    same = h.rt.eval("rawequal")
    assert same(S.minute.steps["bus"], S.bus.flushEffects)
    assert same(S.minute.steps["reconcile"], S.reconcile.minute)
    assert same(S.minute.steps["kinetics"], S.kinetics.minute)
    assert same(S.minute.steps["metabolism"], S.metabolism.minute)
    assert same(S.minute.steps["nutrients"], S.nutrients.minute)
    assert same(S.minute.steps["effects"], S.effects.step)
    assert same(S.minute.steps["strength"], S.strength.minute)
    assert same(S.minute.steps["weight"], S.weight.minute)
    assert same(S.minute.steps["writer"], S.writer.step)
    assert same(S.minute.steps["store"], S.store.step)
    assert sorted(k for k in S.minute.steps.keys()) == sorted(ORDER)


def test_the_players_file_keeps_no_minute_hook_list():
    h = Host()
    assert h.NR.server.players.onMinute is None


def test_a_step_that_raises_does_not_stop_the_steps_after_it():
    h = Host()
    M = h.NR.server.minute
    M.register("kinetics", h.rt.eval("function() error('boom') end"))
    p = h.player("a"); h.online(p); h.minute(); h.tick(2)
    assert h.record("a").body is not None                 # metabolism still ran after the raising step
    assert M.stats.failures == 1
    assert any("minute: kinetics failed for a" in s for s in h.printed())


def test_registering_a_name_again_replaces_it_and_an_unknown_name_never_runs():
    h = Host()
    M = h.NR.server.minute
    ran = h.rt.eval("{}")
    rec = h.rt.eval("function(t, n) return function() t[#t + 1] = n end end")
    for name in ORDER:
        M.register(name, rec(ran, "old-" + name))
    M.register("strength", rec(ran, "new-strength"))
    M.register("training", rec(ran, "training"))
    M.run("a", None, h.rt.table())
    got = [ran[i] for i in range(1, len(ran) + 1)]
    assert "old-strength" not in got and "new-strength" in got
    assert "training" not in got
    assert len(got) == len(ORDER)


def test_the_context_is_cleared_at_the_start_of_each_run():
    h = Host()
    M = h.NR.server.minute
    seen = h.rt.eval("{}")
    for name in ORDER:
        M.register(name, h.rt.eval("function() end"))
    M.register("bus", h.rt.eval(
        "function(t) return function(u, p, r, ctx) t[#t + 1] = tostring(ctx.absorbed); ctx.absorbed = u end end")(seen))
    M.run("a", None, h.rt.table())
    M.run("b", None, h.rt.table())
    assert [seen[i] for i in range(1, len(seen) + 1)] == ["nil", "nil"]


def test_kinetics_hands_the_absorbed_vector_and_meal_calcium_on_the_context():
    h = Host()
    M = h.NR.server.minute
    seen = h.rt.eval("{}")
    M.register("metabolism", h.rt.eval(
        "function(t) return function(u, p, r, ctx) t.absorbed = ctx.absorbed; t.mealCa = ctx.mealCa end end")(seen))
    p = h.player("a"); h.online(p)
    h.T.age = 100.0 + 1 / 60.0
    h.minute(); h.tick(2)                               # the first step: dtH 0, nothing handed
    assert seen.absorbed is None and seen.mealCa is None
    buf = h.record("a").stomach.buffer
    buf.calories = 400.0
    buf.calcium = 95.0
    h.T.age = 100.0 + 2 / 60.0
    h.minute(); h.tick(2)
    assert seen.absorbed is not None and seen.absorbed["calories"] > 0
    assert seen.mealCa == 95.0                          # the buffer's calcium before this minute's emptying
    assert h.NR.server.kinetics.lastAbsorbed is None and h.NR.server.kinetics.lastMealCa is None


# --- the Effects hand-off (the R0 reviews' M4) ------------------------------------------------------------

RECORDER = r"""
function(log)
    local EFF = NutritionRevamp.server.effects
    local orig = EFF.minute
    EFF.minute = function(username, player, record, body, dtM, ageH)
        if username ~= "g1" then return orig(username, player, record, body, dtM, ageH) end
        if log.forceLethal then record.fluids.dehydPct = 99 end
        local bd = player:getBodyDamage()
        local before = bd.st.reduced
        orig(username, player, record, body, dtM, ageH)
        log[#log + 1] = { bodyIsRecord = rawequal(body, record.body), dtM = dtM, ageH = ageH, age = NR_T.age,
                          reduced = bd.st.reduced - before, drain = record.drain.drainThisMinute,
                          state = record.drain.state, rate = record.drain.rate }
    end
end
"""


def _minute(h, age):
    h.T.age = age
    h.minute()
    h.tick(golden_trace.TICKS)


def test_the_effects_step_reads_this_minutes_body_dtm_and_age_after_a_30_minute_absence():
    # Plan 16 Task 2 (until then the return minute integrated the 30 minutes away): the store's resume freezes the
    # absence, so the return minute integrates nothing (Nutrients dtM 0, no Effects step) and the next minute steps one
    h = golden_trace.new_host()
    log = h.rt.eval("{}")
    h.rt.eval(RECORDER)(log)
    start = golden_trace.START_AGE
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.online(g1)
    for m in range(1, 4):                               # three minutes online
        _minute(h, start + m / 60.0)
    assert len(log) == 2                                # the first minute integrates no time (Nutrients dtM 0)
    for i in (1, 2):
        e = log[i]
        assert e.bodyIsRecord is True
        assert abs(e.dtM - 1.0) < 1e-9
        assert e.ageH == e.age
    h.online()                                          # g1 departs
    for m in range(4, 33):
        _minute(h, start + m / 60.0)
    assert len(log) == 2
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.online(g1)                                        # and returns, 30 game minutes after its last minute
    log.forceLethal = True
    _minute(h, start + 33 / 60.0)
    assert len(log) == 2                                # the return minute: nothing integrated
    _minute(h, start + 34 / 60.0)
    assert len(log) == 3
    e = log[3]
    assert e.bodyIsRecord is True
    assert abs(e.dtM - 1.0) < 1e-9
    assert e.ageH == start + 34 / 60.0 and e.ageH == e.age
    assert e.state == 6 and e.drain > 0                 # the dehydration state, its floor 0 past the death point
    assert e.reduced == e.drain                         # the whole of rate x dtM: health is far above the floor
    assert abs(e.drain - e.rate * 1 / 1440) < 1e-12 * e.rate


def test_the_effects_step_is_skipped_when_nutrients_did_not_reach_its_end():
    h = Host()
    S = h.NR.server
    calls = h.rt.eval("{ n = 0 }")
    S.effects.minute = h.rt.eval("function(c) return function() c.n = c.n + 1 end end")(calls)
    S.effects.step("a", None, h.rt.table(), h.rt.table())          # no stamps: no call
    assert calls.n == 0
    ctx = h.rt.table()
    ctx.body = h.rt.table()
    S.effects.step("a", None, h.rt.table(), ctx)
    assert calls.n == 1


def test_a_raising_effects_minute_is_counted_on_the_nutrients_stats_and_logged():
    h = Host()
    S = h.NR.server
    S.effects.minute = h.rt.eval("function() error('effects boom') end")
    before = S.nutrients.stats.effectsErrors
    ctx = h.rt.table()
    ctx.body = h.rt.table()
    S.effects.step("a", None, h.rt.table(), ctx)
    assert S.nutrients.stats.effectsErrors == before + 1
    assert S.minute.stats.failures == 0                 # its own guard caught it
    assert any("nutrients: the effects step failed for a" in s for s in h.printed())


def test_nutrients_stamps_the_effects_inputs_last():
    h = Host()
    M = h.NR.server.minute
    seen = h.rt.eval("{}")
    M.register("effects", h.rt.eval(
        "function(t) return function(u, p, r, ctx) t[#t + 1] = { body = rawequal(ctx.body, r.body), dtM = ctx.dtM,"
        " ageH = ctx.ageH } end end")(seen))
    p = h.player("a"); h.online(p)
    for m in range(1, 4):
        h.T.age = 100.0 + m / 60.0
        h.minute(); h.tick(2)
    got = [seen[i] for i in range(1, len(seen) + 1)]
    stamped = [e for e in got if e.dtM is not None]
    assert stamped, "no minute stamped the effects inputs"
    for e in stamped:
        assert e.body is True and abs(e.dtM - 1.0) < 1e-9



# --- Rule 6: the Java calls of a player-minute (Plan 11g close, the whole-pass review's finding 10) -----------------
# The meal pool's clearance (KIN.mealTrait) read the traits handle and the stats-decrease multiplier afresh every
# player-minute, two Java calls the P-model writer did not make (it read its hoisted h.traits and eng.sd); the lupa
# bench stubs Java and could not see them. Counted on golden_trace's decorated player over ten steady minutes, the
# P-model build (0f14044f) made 4 getCharacterTraits, 15 trait gets and 1 getStatsDecreaseMultiplier a player-minute;
# Kinetics now caches the traits handle per player object and hands its one multiplier read to the writer on ctx.
P_MODEL_CALLS = {"getCharacterTraits": 4, "traitGet": 15, "sd": 1}

COUNT = r"""
function(p, C)
    local orig = p.getCharacterTraits
    p.getCharacterTraits = function(s)
        C.getCharacterTraits = C.getCharacterTraits + 1
        local coll = orig(s)
        if C.wrapped[coll] == nil then
            local g = coll.get
            coll.get = function(c, t) C.traitGet = C.traitGet + 1; return g(c, t) end
            C.wrapped[coll] = true
        end
        return coll
    end
    getSandboxOptions = function()
        return { getStatsDecreaseMultiplier = function(s) C.sd = C.sd + 1; return 1 end }
    end
    NutritionRevamp.so = nil
end
"""


def test_a_player_minute_makes_no_more_trait_or_sandbox_calls_than_the_p_model_writer():
    h = golden_trace.new_host()
    C = h.rt.eval("{ getCharacterTraits = 0, traitGet = 0, sd = 0, wrapped = {} }")
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.rt.eval(COUNT)(g1, C)
    h.online(g1)
    start = golden_trace.START_AGE
    for m in range(1, 4):                               # the first sight: the hoists and the seed
        _minute(h, start + m / 60.0)
    assert h.record("g1").satiety.M > 0                 # the clearance runs: M is seeded and finite
    base = {k: C[k] for k in P_MODEL_CALLS}
    n = 10
    for m in range(4, 4 + n):
        _minute(h, start + m / 60.0)
    per = {k: (C[k] - base[k]) / n for k in P_MODEL_CALLS}
    for k, v in P_MODEL_CALLS.items():
        assert per[k] <= v, (k, per)
    assert per["sd"] == 1                               # one read a player-minute, shared by Kinetics and the writer


# Plan 15 Task 3 fix 1: the thirst traits' two gets (Nutrients' basal scale) are paid for by sharing each trait flag
# across the minute (NR.read.trait): the writer's sleep traits reuse needFactor's gets. Trait gets a player-minute on
# golden_trace's g1 with the HIGH_THIRST and LOW_THIRST sentinels added, counted as above; read at c4d9349e (before
# Task 3) for no trait, High Thirst and Needs More Sleep: 11, 11 and 10. Pinned at this build's counts, each at most one
# over the build before.
HEAD_TRAIT_GETS = {(): 11, ("HIGH_THIRST",): 11, ("NEEDS_MORE_SLEEP",): 10}   # read at c4d9349e
TRAIT_GETS = {(): 11, ("HIGH_THIRST",): 10, ("NEEDS_MORE_SLEEP",): 11}


@pytest.mark.parametrize("traits", sorted(TRAIT_GETS))
def test_a_player_minute_shares_each_trait_flag(traits):
    h = golden_trace.new_host()
    h.rt.eval("function() CharacterTrait.HIGH_THIRST = 'trait:HIGH_THIRST'; "
              "CharacterTrait.LOW_THIRST = 'trait:LOW_THIRST' end")()
    C = h.rt.eval("{ getCharacterTraits = 0, traitGet = 0, sd = 0, wrapped = {} }")
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.rt.eval(COUNT)(g1, C)
    coll = g1.getCharacterTraits(g1)
    for t in traits:
        coll.add(coll, h.rt.eval("function(n) return CharacterTrait[n] end")(t))
    h.online(g1)
    start = golden_trace.START_AGE
    for m in range(1, 4):                               # the first sight and the writer's hoist
        _minute(h, start + m / 60.0)
    base = {k: C[k] for k in P_MODEL_CALLS}
    n = 10
    for m in range(4, 4 + n):
        _minute(h, start + m / 60.0)
    per = {k: (C[k] - base[k]) / n for k in P_MODEL_CALLS}
    assert per == {"getCharacterTraits": 1, "traitGet": TRAIT_GETS[traits], "sd": 1}, (traits, per)
    assert TRAIT_GETS[traits] <= HEAD_TRAIT_GETS[traits] + 1


def test_the_shared_trait_flag_is_read_once_a_minute_and_afresh_with_no_context():
    h = Host()
    C = h.rt.eval("{ n = 0, coll = 0 }")
    p = h.rt.eval("function(C) local coll = { get = function(s, t) C.n = C.n + 1; return t == 'A' end }"
                  " return { getCharacterTraits = function(s) C.coll = C.coll + 1; return coll end } end")(C)
    R = h.NR.read
    ctx = h.rt.table()
    assert R.trait(ctx, p, "A") is True and R.trait(ctx, p, "A") is True
    assert R.trait(ctx, p, "B") is False and R.trait(ctx, p, "B") is False
    assert (C.n, C.coll) == (2, 1)                      # one get per trait, one collection read
    assert R.trait(ctx, p, None) is False and C.n == 2  # an absent trait id reads false, no get
    fresh = h.rt.table()
    assert R.trait(fresh, p, "A") is True and C.n == 3  # a new minute empties the flags
    assert R.trait(None, p, "A") is True and R.trait(None, p, "A") is True
    assert C.n == 5                                     # no context: every call reads


# --- Rule 6: the player-minute's shared engine reads (Plan 12 S R1) ------------------------------------------------
# The minute's steps run in one call, so a member several of them read answers the same: NR.read keeps the first read
# on the pipeline's context. Before, a player-minute read isAsleep 4 times, getCharacterTraits 4, getBodyDamage and
# getThermoregulator 3, getNutrition 2, the clock's getTimeOfDay 4 and the world age 6 (P.work's and five steps').
# Counted inside P.work (the player-minute: its age read, then the pipeline) on golden_trace's decorated player over
# ten steady minutes (the writer's per-object hoists done). Plan 16 Task 4: the hour of day is read once a server minute
# at the players' minute (NR.read.hoist), outside every player's work, so a player-minute reads it 0 times.
SHARED_READS = ("isAsleep", "getCharacterTraits", "getBodyDamage", "getThermoregulator", "getNutrition",
                "getTimeOfDay", "getWorldAgeHours")

COUNT_SHARED = r"""
function(p, C)
    local function counted(t, name)
        local f = t[name]
        t[name] = function(...)
            if C.on then C[name] = C[name] + 1 end
            return f(...)
        end
    end
    local P = NutritionRevamp.server.players
    local work = P.work
    P.work = function(...)
        C.on = true
        work(...)
        C.on = false
    end
    counted(p, "isAsleep")
    counted(p, "getCharacterTraits")
    counted(p, "getNutrition")
    local bd = p:getBodyDamage()
    counted(bd, "getThermoregulator")
    counted(p, "getBodyDamage")
    local gt = getGameTime
    getGameTime = function()
        local t = gt()
        counted(t, "getTimeOfDay")
        counted(t, "getWorldAgeHours")
        return t
    end
end
"""


def test_a_player_minute_reads_each_shared_engine_member_once():
    h = golden_trace.new_host()
    C = h.rt.eval("{ " + ", ".join("%s = 0" % k for k in SHARED_READS) + " }")
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.rt.eval(COUNT_SHARED)(g1, C)
    h.online(g1)
    start = golden_trace.START_AGE
    for m in range(1, 4):                               # the first sight and the writer's hoist
        _minute(h, start + m / 60.0)
    base = {k: C[k] for k in SHARED_READS}
    runs0 = h.NR.server.minute.stats.runs
    n = 10
    for m in range(4, 4 + n):
        _minute(h, start + m / 60.0)
    assert h.NR.server.minute.stats.runs - runs0 == n
    per = {k: (C[k] - base[k]) / n for k in SHARED_READS}
    assert per == {k: (0 if k == "getTimeOfDay" else 1) for k in SHARED_READS}, per


# Plan 16 Task 4: the hour read is hoisted to the server minute. Counted everywhere (not only inside P.work) with three
# players online: one getTimeOfDay a server minute whatever the player count; at the build before it was one a
# player-minute (each player's pipeline read and kept its own).
COUNT_HOUR = r"""
function(C)
    local gt = getGameTime
    getGameTime = function()
        local t = gt()
        local f = t.getTimeOfDay
        t.getTimeOfDay = function(...) C.n = C.n + 1; return f(...) end
        return t
    end
end
"""


def test_a_stalled_night_whose_carry_runs_after_the_wake_books_it_asleep():
    # Plan 16 Task 4 fix 1 (the controller's ruling F2): a 7 h stall seen asleep latches the asleep flag for every one of
    # its sub-steps, so the 3 h the next minute carries are booked asleep though the player has woken by then; the bout
    # then closes once, 10 minutes into the real waking, and resets the body clock to 07:00 once
    h = golden_trace.new_host()
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    F = h.rt.eval("{ v = false, reads = 0 }")
    h.rt.eval("function(p, F) p.isAsleep = function(s) F.reads = F.reads + 1; return F.v end end")(g1, F)
    h.online(g1)
    start = golden_trace.START_AGE
    for m in range(1, 4):
        _minute(h, start + m / 60.0)
    F.v = True
    t = start + 4 / 60.0
    _minute(h, t)
    a = h.record("g1")["acute"]
    assert a["boutH"] > 0
    t += 7.0
    _minute(h, t)                                       # the stall: 4 of its 8 sub-steps run, asleep
    r = h.record("g1")
    assert r["carryAsleep"] is True and a["boutH"] == pytest.approx(4.0 + 1 / 60, abs=0.02)
    F.v = False                                         # the player wakes before the carry runs
    t += 1 / 60.0
    _minute(h, t)                                       # the carry: the rest, read through the latch
    assert r["carryAsleep"] is None
    assert a["boutH"] == pytest.approx(7.0 + 2 / 60, abs=0.02) and a["gapH"] == 0
    hours = []
    n = 0
    while a["boutH"] > 0 and n < 30:
        t += 1 / 60.0
        n += 1
        _minute(h, t)
        hours.append(a["bodyHour"])
    assert a["boutH"] == 0 and n in (10, 11)
    assert hours[-1] == pytest.approx(7.0 + n / 60)     # one reset, at the close
    assert all(abs(x - 7.0) > 0.5 for x in hours[:-1])  # none before it


def test_the_hour_fallback_is_the_world_age_from_seven():
    # Plan 16 Task 4: GameTime.getWorldAgeHours counts from 07:00 of day one (nightsSurvived x 24 + timeOfDay - 7), so
    # with no readable clock the hour is (ageH + 7) mod 24 (it read ageH mod 24 before, 7 h off); 7 with no age
    h = Host()
    R = h.NR.read
    saved = h.G.getGameTime
    try:
        h.G.getGameTime = None
        assert R.hour(None, 100.0) == 11.0 and R.hour(None, 17.5) == 0.5 and R.hour(None, None) == 7
        h.G.getGameTime = h.rt.eval("function() error('no clock') end")
        assert R.hour(None, 100.25) == 11.25
        h.G.getGameTime = h.rt.eval("function() return { getTimeOfDay = function(s) return 0 / 0 end } end")
        assert R.hour(None, 41.0) == 0.0                # a non-finite read falls back too
        assert R.hoist(41.0) == 0.0 and R.minuteHour == 0.0
    finally:
        h.G.getGameTime = saved


def test_the_hour_of_day_is_read_once_a_server_minute():
    h = golden_trace.new_host()
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(COUNT_HOUR)(C)
    ps = [golden_trace._new_player(h, g, golden_trace.MACROS[g]) for g in ("g1", "g2", "g3")]
    h.online(*ps)
    start = golden_trace.START_AGE
    for m in range(1, 4):
        _minute(h, start + m / 60.0)
    n0, runs0 = C.n, h.NR.server.minute.stats.runs
    n = 10
    for m in range(4, 4 + n):
        _minute(h, start + m / 60.0)
    assert h.NR.server.minute.stats.runs - runs0 == 3 * n
    assert C.n - n0 == n
    assert h.NR.read.minuteHour == pytest.approx(math.fmod(start + (3 + n) / 60.0 + 7, 24))


def test_the_shared_reads_keep_a_nil_answer_and_read_afresh_with_no_context():
    h = Host()
    C = h.rt.eval("{ n = 0 }")
    p = h.rt.eval("function(C) return { getNutrition = function(s) C.n = C.n + 1; return nil end } end")(C)
    R = h.NR.read
    ctx = h.rt.table()
    assert R.nutrition(ctx, p) is None and R.nutrition(ctx, p) is None
    assert C.n == 1                                     # a nil answer is kept, not read again
    assert R.nutrition(None, p) is None and R.nutrition(None, p) is None
    assert C.n == 3                                     # no context: every call reads

def test_two_players_in_one_drain_each_read_their_own_engine_answers():
    # the context is the pipeline's one table: each player's minute reads its own isAsleep, once, and shares it with
    # its later steps; the next player's minute never sees the previous one's answer
    h = Host()
    M = h.NR.server.minute
    for name in ORDER:
        M.register(name, h.rt.eval("function() end"))
    seen = h.rt.eval("{}")
    reader = h.rt.eval("function(t) return function(u, p, r, ctx)"
                       " t[#t + 1] = u .. '=' .. tostring(NutritionRevamp.read.asleep(ctx, p)) end end")(seen)
    M.register("nutrients", reader)
    M.register("effects", reader)
    C = h.rt.eval("{ a = 0, b = 0 }")
    mk = h.rt.eval("function(C, name, v) return { isAsleep = function(s) C[name] = C[name] + 1; return v end } end")
    pa, pb = mk(C, "a", True), mk(C, "b", False)
    for u, p in (("a", pa), ("b", pb), ("a", pa)):
        M.run(u, p, h.rt.table(), 100.0)
    assert [seen[i] for i in range(1, len(seen) + 1)] == ["a=true", "a=true", "b=false", "b=false", "a=true", "a=true"]
    assert (C.a, C.b) == (2, 1)                         # one read a player-minute


def test_the_engine_reads_leave_the_context_at_the_end_of_the_minute():
    h = Host()
    M = h.NR.server.minute
    for name in ORDER:
        M.register(name, h.rt.eval("function() end"))
    M.register("effects", h.rt.eval("function(u, p, r, ctx) NutritionRevamp.read.asleep(ctx, p);"
                                     " NutritionRevamp.read.nutrition(ctx, p); ctx.kept = 1 end"))
    p = h.rt.eval("{ isAsleep = function() return true end, getNutrition = function() return {} end }")
    M.run("a", p, h.rt.table(), 100.0)
    keys = [h.NR.read.KEYS[i] for i in range(1, len(h.NR.read.KEYS) + 1)]
    assert len(keys) == 9 and all(M.ctx[k] is None for k in keys)       # eFlags since Plan 15 Task 3 fix 1, eDayMin since Task 6
    assert M.ctx.kept == 1                              # a step's own hand-off stays until the next run clears it


# --- Rule 6: the drain-and-floor engine's engine calls (Plan 15 Task 4) ----------------------------------------------
# Every method of golden_trace's decorated g1 and of every table one returns is counted over ten minutes, steady and with
# a drain running (a 12 % water deficit: a drain at the build before, whose dehydration rung started at 10 %, and here,
# whose dehydration state starts at 6 %). Read at 1398d765, the build before: 67 steady and 69 draining
# (ReduceGeneralHealth). Here the steady minute is unchanged; a draining minute adds the overall-health read the floor
# needs and one stat write (the 4-6 % band's apathy row writes UNHAPPINESS, Plan 15 Task 4's effect order).
# Plan 15 Task 5 (option B): the 12 % deficit is Parched, so the writer holds the severe-moodle constant at 0 and
# re-applies its other terms each minute: three moodle levels (SICK, BLEEDING, HEAVY_LOAD) a minute while the constant
# is 0 (read at eb3ef7b2, the build before, with the same stand-in: 71); the constant itself is written only when its
# wanted value changes, so neither case pays a write a steady minute.
# Plan 15 Task 6 (Task 5's review L4): the re-applied terms also read the day length off the sandbox object, which the
# player's count does not see; counted here on the sandbox stand-in (SANDBOX_DAY): one read a minute the constant was 0,
# shared with Effects' heal toward a floor (NR.read.dayMin), none on a steady minute. The calibrated curve reads no Java.
# Plan 15 Task 8 (the food-timer bridge): g1's seeded meal pool (912 weighted kcal) reads sated, so the steady minute
# writes the health-from-food timer once (vanilla drains it between writes); an unfed minute (the pool set to 1 weighted
# kcal) writes it only on the change to 0 and then makes no call, and a draining minute holds it at 0 with none. Read
# at 56a25b9d, the build before, with the same stand-in: 67 steady, 67 unfed, 74 draining. Fix 1 (review I1): the sated
# minute sizes its value from the day length, one shared sandbox read (none unfed, the drain's one shared).
ENGINE_COUNT = r"""
function(p, C)
    local seen = {}
    local function wrap(t)
        if type(t) ~= "table" or seen[t] then return t end
        seen[t] = true
        local names = {}
        for k, v in pairs(t) do
            if type(v) == "function" then names[#names + 1] = k end
        end
        for i = 1, #names do
            local k = names[i]
            local f = t[k]
            t[k] = function(...)
                C.n = C.n + 1
                C.by[k] = (C.by[k] or 0) + 1
                return wrap(f(...))
            end
        end
        return t
    end
    wrap(p)
end
"""
SANDBOX_DAY = r"""
function(C)
    local so = NutritionRevamp.sandbox()
    so.getDayLengthMinutes = function(s) C.day = C.day + 1; return 90 end
end
"""
HEAD_ENGINE_CALLS = {"steady": 67, "drain": 69}   # read at 1398d765
ENGINE_CALLS = {"steady": 68, "unfed": 67, "drain": 74}
DAY_READS = {"steady": 1, "unfed": 1, "drain": 1}  # the sandbox's getDayLengthMinutes a minute: since Plan 17 Task 3 the
# players' minute's one hoisted read (NR.read.hoist), seeded on every player's context, whatever the case (until then a
# player-minute's read, by Effects' heal or the sated bridge: steady 1, unfed 0, drain 1; Plan 15 Task 6, Task 8 fix 1)
TASK4_ENGINE_CALLS = {"steady": 67, "drain": 71}  # read at eb3ef7b2 (Plan 15 Task 4b), before option B
TASK7_ENGINE_CALLS = {"steady": 67, "unfed": 67, "drain": 74}   # read at 56a25b9d (Plan 15 Task 7), before the bridge
TIMER_WRITES = {"steady": 1, "unfed": 0, "drain": 0}             # setHealthFromFoodTimer a player-minute (Task 8)


@pytest.mark.parametrize("case", sorted(ENGINE_CALLS))
def test_the_drain_adds_only_its_health_read_to_a_player_minute(case):
    h = golden_trace.new_host()
    C = h.rt.eval("{ n = 0, by = {} }")
    g1 = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    h.rt.eval(ENGINE_COUNT)(g1, C)
    D = h.rt.eval("{ day = 0 }")
    h.rt.eval(SANDBOX_DAY)(D)
    h.online(g1)
    start = golden_trace.START_AGE
    for m in range(1, 4):
        _minute(h, start + m / 60.0)
    rec = h.record("g1")
    if case == "drain":
        b = rec["body"]
        rec["fluids"]["water"] = -0.12 * (b["fm"] + b["lm"] + b["lx"]) * 1000.0
    if case == "unfed":
        rec["satiety"]["M"] = 1.0
    if case != "unfed":
        # Plan 16 Task 4: the host's clock now reads the engine's 07:00 origin, so g1's first-sight seed reads another
        # circadian hour and seeds an unfed pool (56 weighted kcal); the sated pool the steady case counts (912, the
        # seed under the old clock) is set by hand, as the unfed case sets its own
        rec["satiety"]["M"] = 912.0
    _minute(h, start + 4 / 60.0)
    base, health0, day0 = C.n, C.by["getOverallBodyHealth"] or 0, D.day
    timer0 = C.by["setHealthFromFoodTimer"] or 0
    n = 10
    for m in range(5, 5 + n):
        _minute(h, start + m / 60.0)
    assert (C.n - base) / n == ENGINE_CALLS[case]
    assert (D.day - day0) / n == DAY_READS[case]
    assert ((C.by["getOverallBodyHealth"] or 0) - health0) / n == (1 if case == "drain" else 0)
    assert rec["drain"]["active"] is (case == "drain")
    assert ((C.by["setHealthFromFoodTimer"] or 0) - timer0) / n == TIMER_WRITES[case]
    assert ENGINE_CALLS[case] == TASK7_ENGINE_CALLS[case] + TIMER_WRITES[case]
    if case in TASK4_ENGINE_CALLS:
        assert TASK7_ENGINE_CALLS[case] <= TASK4_ENGINE_CALLS[case] + (3 if case == "drain" else 0)
        assert TASK4_ENGINE_CALLS[case] <= HEAD_ENGINE_CALLS[case] + 2
    assert (C.by["setHealthReductionFromSevereBadMoodles"] or 0) == (2 if case == "drain" else 1)   # first sight, then once at Parched


def test_the_day_length_is_read_once_a_player_minute():
    # Plan 15 Task 6 (Task 5's review L4): NR.read.dayMin keeps the minute's read on ctx, so Effects' heal and the
    # writer's re-applied terms share one; with no ctx every call reads, and an unreadable sandbox reads the default
    h = Host()
    C = h.rt.eval("{ day = 0 }")
    h.rt.eval("function(C) NutritionRevamp.so = { getDayLengthMinutes = function(s) C.day = C.day + 1; return 60 end } end")(C)
    R = h.NR.read
    ctx = h.rt.table()
    assert R.dayMin(ctx, 90) == 60 and R.dayMin(ctx, 90) == 60 and C.day == 1
    assert R.dayMin(None, 90) == 60 and C.day == 2
    h.NR.so = h.rt.table()
    assert R.dayMin(h.rt.table(), 90) == 90 and R.dayMin(None, 90) == 90


def test_a_moodle_level_is_floored_and_clamped_to_0_4():
    # Plan 15 Task 6 fix 1 (review L2): NR.read.moodleLevel, the one copy Effects and the writer read
    h = Host()
    R = h.NR.read
    m = h.rt.eval("function(v) return { getMoodleLevel = function(s, t) return v end } end")
    assert [R.moodleLevel(m(v), "T") for v in (5, -1, 2.7)] == [4, 0, 2]
    assert R.moodleLevel(None, "T") == 0 and R.moodleLevel(m(3), None) == 0
