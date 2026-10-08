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
    h.record("a").body.energyState = 1.8                # across the first energy rung
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
