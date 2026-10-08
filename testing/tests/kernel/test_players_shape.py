from .server_host import Host

CLOCK = r"""
NR_T.now = 1000000
getTimestampMs = function() return NR_T.now end
"""


def host(per_run_ms=None):
    h = Host(extra_env=CLOCK if per_run_ms is not None else "")
    if per_run_ms is not None:
        h.rt.execute("local P = NutritionRevamp.server.players; local w = P.work; "
                     "P.work = function(u, p) NR_T.now = NR_T.now + %d; return w(u, p) end" % per_run_ms)
    return h


def names(n):
    return ["p%02d" % i for i in range(n)]


def run_minute(h, ticks, minute):
    h.T.age = 100.0 + minute / 60
    h.minute()
    served = []
    for _ in range(ticks):
        d0 = h.NR.server.players.drained
        h.tick(1)
        served.append(h.NR.server.players.drained - d0)
    return served


def test_no_player_starves_when_players_outnumber_ticks():
    h = host(per_run_ms=2)
    h.online(*[h.player(u) for u in names(60)])
    for m in range(1, 6):
        run_minute(h, 6, m)                          # 6 ticks a game minute: DayLength 1 (#3346)
    assert all(h.record(u).lastSeen == 100.0 + 5 / 60 for u in names(60))


def test_a_tick_never_runs_more_than_its_cap():
    h = host(per_run_ms=2)
    h.online(*[h.player(u) for u in names(60)])
    for m in range(1, 4):
        served = run_minute(h, 6, m)
    assert max(served) <= h.NR.server.players.runCap


def test_under_a_fast_clock_everyone_runs_every_tick():
    h = host(per_run_ms=2)
    h.online(*[h.player(u) for u in names(20)])
    for m in range(1, 6):
        run_minute(h, 1, m)                          # one tick a minute event (#3348)
    assert all(h.record(u).lastSeen == 100.0 + 5 / 60 for u in names(20))


def test_unserved_players_are_carried_forward_and_never_doubled():
    h = host()                                       # no clock: the cap is floor(15 / 1.6) = 9 a tick
    h.online(*[h.player(u) for u in names(30)])
    run_minute(h, 1, 1)
    P = h.NR.server.players
    assert P.drained == 9
    pending = [P.queue[i] for i in range(P.queueHead, len(P.queue) + 1)]
    assert len(pending) == 21 and len(set(pending)) == 21
    h.T.age = 100.0 + 2 / 60
    h.minute()                                       # the next minute's merge, before any tick
    merged = [P.queue[i] for i in range(1, len(P.queue) + 1)]
    assert merged[:21] == pending                    # the unserved first, in their order
    assert len(merged) == 30 and len(set(merged)) == 30


def test_a_respawn_inside_a_minute_never_marks_the_new_record_dead():
    h = host()
    a, b = h.player("a"), h.player("b")
    h.online(a, b)
    run_minute(h, 25, 1)
    b.deadFlag = True
    run_minute(h, 25, 2)                             # b's dead body runs: the old record marked dead
    h.T.age = 100.0 + 3 / 60
    h.minute()                                       # b queued with its dead body
    nb = h.player("b")
    h.fire("OnNewGame", nb, None)                    # the respawn before the drain reaches b
    h.tick(3)                                        # the new object enters the list three ticks later (#3358)
    h.online(a, nb)
    h.tick(22)
    assert h.record("b").dead is not True
    run_minute(h, 25, 4)
    assert h.G.rawequal(h.NR.server.players.online["b"], nb)
    assert h.record("b").lastSeen == 100.0 + 4 / 60


def test_a_reconnect_between_two_minutes_fires_first_sight_again():
    h = host()
    seen = h.rt.eval("{}")
    P = h.NR.server.players
    P.onFirstSight[len(P.onFirstSight) + 1] = h.rt.eval("function(t) return function(u) t[#t + 1] = u end end")(seen)
    h.online(h.player("a"))
    run_minute(h, 2, 1)
    h.online(h.player("a"))                          # a new IsoPlayer under the same username (#3360)
    run_minute(h, 2, 2)
    assert [seen[i] for i in range(1, len(seen) + 1)].count("a") == 2


def test_resets_count_respawns_only():
    h = host()
    a = h.player("a")
    h.fire("OnNewGame", a, None)
    assert h.record("a").resets == 0                 # a first character
    h.online(a)
    run_minute(h, 2, 1)
    h.fire("OnNewGame", h.player("a"), None)
    assert h.record("a").resets == 1


def test_a_sixty_game_minute_step_integrates_and_stays_finite():
    h = host()
    h.online(h.player("a"))
    run_minute(h, 2, 1)
    run_minute(h, 2, 61)                             # one hour of game time between two runs
    import math
    r = h.record("a")
    assert r.lastSeen == 100.0 + 61 / 60
    for k in ("fm", "lm", "energyState"):
        assert math.isfinite(r.body[k]), k


def test_one_shot_tasks_run_once_inside_the_queue():
    h = host()
    h.online(h.player("a"))
    hits = h.rt.eval("{ n = 0 }")
    h.NR.server.players.task("t1", h.rt.eval("function(t) return function() t.n = t.n + 1 end end")(hits))
    run_minute(h, 3, 1)
    run_minute(h, 3, 2)
    assert hits.n == 1


def test_the_extra_seam_runs_its_names_every_minute():
    h = host()
    h.online(h.player("a"))
    runs = h.rt.eval("{ n = 0 }")
    h.NR.server.players.extra = h.rt.eval(
        "function(t) return { names = function() return { 'ghost1', 'ghost2' } end, "
        "run = function(name) t.n = t.n + 1 end } end")(runs)
    run_minute(h, 3, 1)
    run_minute(h, 3, 2)
    assert runs.n == 4


def test_a_respawn_reset_that_met_no_clock_stays_pending_and_runs_in_the_queue():
    # Task 3's residual: OnNewGame with no readable clock logged "the reset waits for a readable clock", and nothing
    # retried it; the next minute found the old record and the respawn's reset was lost.
    h = host()
    a = h.player("a")
    h.online(a)
    run_minute(h, 2, 1)
    a.deadFlag = True
    run_minute(h, 2, 2)                              # the dead body runs: the old record marked dead
    assert h.record("a").dead is True
    na = h.player("a")
    h.T.age = None                                   # no clock read at OnNewGame
    h.fire("OnNewGame", na, None)
    assert h.record("a").resets == 0                 # nothing reset yet
    h.online(na)
    h.T.age = 100.0 + 3 / 60
    h.minute()                                       # the clock reads at the minute event ...
    h.T.age = None
    h.tick(2)                                        # ... but not in the player's queue slot: still pending
    assert h.record("a").resets == 0
    run_minute(h, 2, 4)                              # the next queued run makes the reset, then the minute
    r = h.record("a")
    assert r.resets == 1
    assert r.dead is not True
    assert r.lastSeen == 100.0 + 4 / 60
    run_minute(h, 2, 5)
    assert h.record("a").resets == 1                 # reset once, never again
