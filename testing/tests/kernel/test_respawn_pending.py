"""A respawn's reset clears the dead character's pending gut doses and ingested sum (Plan 12, S B8): the new
character's first Nutrients minute never inherits a drink landed in the death minute."""
from .server_host import Host


def setup(h):
    p = h.player("admin")
    h.online(p)
    for m in range(1, 4):
        h.T.age = 100.0 + m / 60
        h.minute(); h.tick(25)
    IN = h.NR.server.intake
    IN.pendingAlc["admin"] = 10.0
    IN.pendingCaf["admin"] = 50.0
    IN.lastIngested["admin"] = h.rt.table_from({"ethanol": 10.0})
    IN.pendingAlc["bob"] = 3.0                                  # another player's dose is left alone
    return p, IN


def test_a_respawn_clears_the_pending_doses_and_the_ingested_sum():
    h = Host()
    p, IN = setup(h)
    h.fire("OnNewGame", p, None)
    assert h.record("admin").resets == 1
    assert IN.pendingAlc["admin"] is None and IN.pendingCaf["admin"] is None
    assert IN.lastIngested["admin"] is None
    assert IN.pendingAlc["bob"] == 3.0


def test_a_deferred_reset_clears_them_when_it_is_made():
    h = Host()
    p, IN = setup(h)
    h.T.age = None                                              # no clock at OnNewGame: the reset waits
    h.fire("OnNewGame", p, None)
    assert IN.pendingAlc["admin"] == 10.0
    h.T.age = 100.1
    assert h.NR.server.players.makeReset("admin") is True
    assert IN.pendingAlc["admin"] is None and IN.lastIngested["admin"] is None
