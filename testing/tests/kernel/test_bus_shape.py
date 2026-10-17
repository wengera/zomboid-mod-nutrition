"""The bus adapter's shape (NR_Server_Bus.lua; Plan 11a Task 4): the mirror build inside the guard, one mirror
request answered per player per REQUEST_GAP_MS, a push on a live class change and each player's push phase."""
from .server_host import Host

SEND = r"""
NR_T.sent = {}
sendServerCommand = function(p, module, cmd, m) NR_T.sent[#NR_T.sent + 1] = cmd end
getTimestampMs = function() return NR_T.now end
NR_T.now = 1000000
"""


def online(h, name="a"):
    p = h.player(name)
    h.online(p)
    h.minute(); h.tick(25)
    return p


def test_a_mirror_build_that_raises_is_caught_and_counted():
    h = Host(extra_env=SEND)
    p = online(h)
    h.K.mirror.build = h.rt.eval("function() error('corrupt') end")
    assert h.NR.server.bus.sendMirror(p, h.record("a")) is False
    assert h.NR.server.bus.build.failed == 1


def test_mirror_requests_inside_the_gap_are_denied():
    h = Host(extra_env=SEND)
    p = online(h)
    n0 = len(h.T.sent)
    for _ in range(5):
        h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 1
    assert h.NR.server.bus.requests.stats.denied == 4
    h.T.now = h.T.now + 4999                             # still inside the 5 s window: denied, nothing sent
    h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 1
    assert h.NR.server.bus.requests.stats.denied == 5
    h.T.now = h.T.now + 2                                # 5001 after the first answer
    h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 2


def test_a_class_change_marks_the_player_for_a_push():
    h = Host(extra_env=SEND)
    online(h)
    B = h.NR.server.bus
    for _ in range(3):                                   # settle: the signature recorded, the offset spent
        h.T.now = h.T.now + 60001
        h.T.age = h.T.age + 1 / 60
        h.minute(); h.tick(25)
    n0 = B.effects.stats.pushes
    h.record("a").acute.caf = 600.0                     # across the stimulant rungs (Plan 15 Task 9: no energy class)
    h.T.now = h.T.now + 60001
    h.T.age = h.T.age + 1 / 60
    h.minute(); h.tick(25)
    h.T.now = h.T.now + 60001
    h.T.age = h.T.age + 1 / 60
    h.minute(); h.tick(25)                               # the mark made in one minute goes out with the next flush
    assert B.effects.stats.pushes >= n0 + 1


def test_two_players_first_seen_together_push_at_different_wall_times():
    h = Host(extra_env=SEND)
    a, b = h.player("admin"), h.player("bob")            # offsets 8475 and 37717 ms inside the 60 s gap
    h.online(a, b)
    B = h.NR.server.bus
    first = {}
    for k in range(200):
        h.T.now = h.T.now + 1000                         # one real second a game minute
        h.T.age = h.T.age + 1 / 60
        for u in ("admin", "bob"):
            if h.record(u) is not None and h.record(u).effects is not None:
                h.record(u).effects.dirty = True         # keep both marked so the gap alone decides
        h.minute(); h.tick(25)
        for u in ("admin", "bob"):
            last = B.effects.last[u]
            if last is not None and u not in first and last > 1000000:
                first[u] = last
    assert "admin" in first and "bob" in first and abs(first["admin"] - first["bob"]) >= 20000


def _settle(h):
    for _ in range(3):
        h.T.now = h.T.now + 60001
        h.T.age = h.T.age + 1 / 60
        h.minute(); h.tick(25)


def test_an_overfull_level_change_marks_a_push_at_the_next_flush():
    h = Host(extra_env=SEND)
    online(h)
    B = h.NR.server.bus
    _settle(h)
    n0 = B.effects.stats.pushes
    h.record("a").stomach.liquid = 1200
    h.T.now = h.T.now + 60001
    h.T.age = h.T.age + 1 / 60
    h.minute(); h.tick(25)
    assert B.effects.stats.pushes >= n0 + 1


def test_a_level_that_changes_every_five_seconds_pushes_at_most_once_per_gap():
    h = Host(extra_env=SEND)
    online(h)
    B = h.NR.server.bus
    _settle(h)
    n0, d0, t0 = B.effects.stats.pushes, B.effects.stats.deferred, h.T.now
    for k in range(24):                                   # two real minutes, a level flip every 5 s
        h.record("a").stomach.liquid = 1200 if k % 2 == 0 else 100
        h.T.now = h.T.now + 5000
        h.T.age = h.T.age + 1 / 60
        h.minute(); h.tick(25)
    assert B.effects.stats.pushes - n0 <= (h.T.now - t0) // B.PUSH_GAP_MS + 1
    assert B.effects.stats.deferred > d0


def test_a_new_drain_state_and_trend_word_mark_a_push():
    # Plan 15 Task 9: the signature carries the set of active drain states (from the hundred-thousands) and the weight
    # trend word (the ten-thousands), so a new drain line or trend word reaches the panel at the next flush
    h = Host(extra_env=SEND)
    online(h)
    B = h.NR.server.bus
    _settle(h)
    r = h.record("a")
    assert (B.lastSig["a"] // 10000) % 10 == 1                       # a fresh ring holds the creation mass: steady
    r.drain.active = True                                            # the bus is first in ORDER: it reads this state
    r.drain.mask = 33
    h.minute(); h.tick(25)
    assert B.lastSig["a"] // 100000 == 33 and B.effects.dirty["a"] is True
    r.drain.active = False
    r.body.mass7[1] = r.body.fm + r.body.lm + r.body.lx + 7 * 0.2    # 0.2 kg a day lost over the week
    h.minute(); h.tick(25)
    assert (B.lastSig["a"] // 10000) % 10 == 0 and B.lastSig["a"] // 100000 == 0


MIRRORS = r"""
NR_T.mirrors = {}
local send = sendServerCommand
sendServerCommand = function(p, module, cmd, m) NR_T.mirrors[#NR_T.mirrors + 1] = m; send(p, module, cmd, m) end
"""


def test_every_mirror_carries_the_drain_set_and_the_trend_and_no_energy_level():
    # Plan 15 Task 9: the energy class is gone, so no mirror carries body_energyLevel; each carries drain_mask (the
    # active drain states) and body_trend (the 7-day mass slope, kg a day) for the panel's lines
    h = Host(extra_env=SEND + MIRRORS)
    p = online(h)
    B = h.NR.server.bus
    _settle(h)
    last = lambda: h.T.mirrors[len(h.T.mirrors)]
    r = h.record("a")
    assert B.sendMirror(p, r) is True
    assert last().body_energyLevel is None and last().drain_mask == 0 and last().body_trend == 0
    r.drain.active = True
    r.drain.mask = 4
    r.body.mass7[1] = r.body.fm + r.body.lm + r.body.lx - 7 * 0.1
    assert B.sendMirror(p, r) is True
    assert last().drain_mask == 4 and abs(last().body_trend - 0.1) < 1e-9


def test_the_signatures_hundreds_digit_is_the_level_of_the_mirrors_stomach_mass():
    h = Host(extra_env=SEND)
    online(h)
    B = h.NR.server.bus
    _settle(h)
    r = h.record("a")
    g = h.K.stomach.mass(r.stomach)
    r.stomach.liquid = r.stomach.liquid + (1099.6 - g)
    h.minute(); h.tick(25)
    mass = h.K.mirror.stomachMass(r)
    assert h.K.view.fullnessLevel(mass) == 4
    assert (B.lastSig["a"] // 100) % 10 == 4


def test_the_mirror_reports_the_running_mode_not_the_polled_option():
    # Plan 12 (S B7): the writer's mode is fixed at OnGameBoot; an NR.Mode changed mid-run is polled every minute
    # but not run, so the mirror (as the self-report already does) names the mode the server runs.
    h = Host(extra_env=SEND)
    online(h)
    W, O = h.NR.server.writer, h.NR.server.options
    running = W.mode
    O.mode = 2 if running == 1 else 1                    # the operator changed the option mid-run
    assert h.NR.server.bus.meta()["mode"] == running
    assert "mode=" + h.NR.modeName(running) in h.NR.selfReport("server")


def test_a_mirror_request_for_a_dead_record_is_not_answered():
    h = Host(extra_env=SEND)
    p = online(h)
    n0 = len(h.T.sent)
    h.record("a").dead = True
    h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) == n0                           # the dead character is not brought back to the client
    h.record("a").dead = False
    h.T.now = h.T.now + 5001
    h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", p, None)
    assert len(h.T.sent) - n0 == 1


def test_the_mirror_reads_its_level_at_the_servers_strength_table():
    # Plan 13 Task 18 (ruling 13-19): body_level moves with NR.StrengthYearsToLevel10, so sendMirror passes
    # NR.server.options.strength, else the mirror reads K.strength.DEFAULTS
    h = Host(extra_env=SEND + MIRRORS)
    p = online(h)
    B = h.NR.server.bus
    _settle(h)
    last = lambda: h.T.mirrors[len(h.T.mirrors)]
    h.NR.server.options = None
    assert B.sendMirror(p, h.record("a")) is True
    body = h.record("a").body
    body.N0 = 2.0                                        # S above 1, where R moves the level
    assert B.sendMirror(p, h.record("a")) is True
    assert last().body_level == h.K.strength.level(body.lm, body.N0, body.T, h.K.strength.DEFAULTS)
    P = h.K.strength.params(h.rt.table(StrengthYearsToLevel10=2.0))[0]
    h.NR.server.options = h.rt.table(strength=P)
    assert B.sendMirror(p, h.record("a")) is True
    assert last().body_level == h.K.strength.level(body.lm, body.N0, body.T, P)
    assert last().body_level != h.K.strength.level(body.lm, body.N0, body.T, h.K.strength.DEFAULTS)
    assert last().body_sets == body.S
