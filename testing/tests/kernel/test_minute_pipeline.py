"""The slow minute's explicit pipeline (Plan 10 Task R2): NR_Server_Minute.lua.

The declared ORDER is the order that runs; the players' file keeps no minute hook list; a raising step does not
stop the steps after it; registering a name again replaces its function; the context is cleared per player run.

The Effects hand-off (the R0 reviews' M4): the golden trace cannot see a wrong body, dtM or ageH on the context, so
a recorder around the Effects minute (what the step hands it) pins them here on golden_trace's decorated player: ctx.body is record.body, ctx.dtM is 30
on the minute a player returns after 30 game minutes away, ctx.ageH is the world age, and a record forced lethal
on that minute takes ReduceGeneralHealth == E.drain x 30.
"""
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
                          reduced = bd.st.reduced - before, drain = record.effects.drain,
                          lethal = record.effects.lethal }
    end
end
"""


def _minute(h, age):
    h.T.age = age
    h.minute()
    h.tick(golden_trace.TICKS)


def test_the_effects_step_reads_this_minutes_body_dtm_and_age_after_a_30_minute_gap():
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
    assert len(log) == 3
    e = log[3]
    assert e.bodyIsRecord is True
    assert abs(e.dtM - 30.0) < 1e-9
    assert e.ageH == start + 33 / 60.0 and e.ageH == e.age
    assert e.lethal == 6 and e.drain > 0                # the dehydration rung
    assert e.reduced == e.drain * e.dtM
    assert abs(e.reduced - e.drain * 30) < 1e-9 * e.drain * 30


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
