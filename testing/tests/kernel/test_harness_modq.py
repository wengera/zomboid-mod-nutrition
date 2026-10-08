"""The harness's ghost route into the mod's own queue (Plan 11 Task 19), offline: PZTestKit_Server.lua's H0 section
(from `TK.H0 = TK.H0 or {}` to the end of the file) loaded on the shared server host beside the real mod, with a
stub TK (register, call, side). It pins what the live smoke test (Plan 11b's first session) cannot cheaply show:
every ghost run is dry and store-skipped in every arm, both seams read nil outside a ghost run, ghost.load <N> mod
leaves the harness's own queue empty, ghost.modq on hands the ghosts to the mod's queue, every batch it opens is
closed with the sends restored, and ghost.modq off restores the queue's own functions. The harness is never a
kernel file, so the coverage gate is untouched."""
import os

from .server_host import Host, REPO

HARNESS = os.path.join(REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua", "server",
                       "PZTestKit_Server.lua")

ENV = r"""
NR_T.now = 5000000
getTimestampMs = function() NR_T.now = NR_T.now + 1; return NR_T.now end
NR_T.realSSC = function() end
sendServerCommand = NR_T.realSSC
"""

STUB_TK = r"""
TK = { side = "server", reg = {} }
TK.register = function(name, fn) TK.reg[name] = fn end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
"""


def harness_section():
    with open(HARNESS, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    i = src.index("TK.H0 = TK.H0 or {}\n")
    return src[i:]


def boot():
    h = Host(extra_env=ENV)
    h.online(h.player("admin"))
    h.minute()
    h.tick(10)                                                     # the carrier's record exists
    assert h.record("admin") is not None
    h.rt.execute(STUB_TK)
    h.rt.eval("function(src) return assert(loadstring(src, '@PZTestKit_Server.lua')) end")(harness_section())()
    h.H0 = h.G.TK.H0
    h.reg = h.G.TK.reg
    return h


def same(h, a, b):
    """Lua identity (lupa's == compares the Python wrappers)."""
    return h.rt.eval("rawequal")(a, b)


def cmd(h, name, *args):
    return h.reg[name](h.rt.table(*args))


def ghost_names(h):
    G = h.H0.g
    return [G.ghosts[i].name for i in range(1, len(G.ghosts) + 1)]


def test_ghost_load_mod_and_modq_on_run_every_ghost_in_the_mods_queue_dry_and_store_skipped():
    h = boot()
    W, S, P = h.NR.server.writer, h.NR.server.store, h.NR.server.players
    r = cmd(h, "ghost.load", "4", "mod")
    assert r.ok is True and r.ghosts == 3
    q = cmd(h, "ghost.modq", "on")
    assert q.ok is True and q.on is True and q.ghosts == 3
    assert P.extra is not None
    dry0 = W.stats.dry
    h.minute()
    h.tick(20)
    G = h.H0.g
    assert G.runs == 3 and G.failures == 0                         # every ghost ran once, from the mod's queue
    assert all(G.ghosts[i].okRuns == 1 for i in range(1, 4))
    assert W.stats.dry - dry0 == 3                                 # each ghost minute's writer step ran dry
    assert W.dry is None and S.skip is None                        # both seams nil outside a ghost run
    for name in ghost_names(h):
        assert S.file.lastWrite[name] is None and S.file.index[name] is None   # no store step for a ghost
    assert S.file.lastWrite["admin"] is not None                   # the real player's store step ran
    assert G.qt == 0                                               # the harness's own queue stays empty
    assert h.H0.modOpen is False                                   # the drain's end closed the batch
    assert same(h, h.G.sendServerCommand, h.T.realSSC)                   # the sends restored
    assert G.suppressed >= 0 and G.ms >= 0
    h.minute()
    assert G.starvedEvents == 0                                    # every ghost ran within its period


def test_a_batch_opened_by_a_ghost_closes_before_a_real_player_runs():
    h = boot()
    P = h.NR.server.players
    cmd(h, "ghost.load", "4", "mod")
    cmd(h, "ghost.modq", "on")
    seen = h.rt.eval("""function(P, H0)
        local seen = {}
        local base = P.runOneBase
        P.runOneBase = function(name)
            seen[#seen + 1] = name .. (H0.modOpen and ":open" or ":closed")
                .. ((sendServerCommand == NR_T.realSSC) and ":real" or ":stub")
            return base(name)
        end
        return seen
    end""")(P, h.H0)
    h.minute()
    names = ghost_names(h)
    P.queue = h.rt.table(names[0], "admin", names[1], names[2])   # a ghost run just before the real player's
    P.queueHead = 1
    P.runCap = 10
    P.budgetMs = 1000
    h.tick(20)
    log = [seen[i] for i in range(1, len(seen) + 1)]
    assert log[:2] == [names[0] + ":closed:real", "admin:closed:real"]   # the ghost's batch closed before admin
    assert h.H0.g.runs == 3 and h.H0.g.suppressed >= 0
    assert "admin:closed:real" in log                              # a real player's sends are never suppressed
    assert not any(e.startswith("admin:open") for e in log)


def test_ghost_modq_off_restores_the_queues_own_functions():
    h = boot()
    P = h.NR.server.players
    run0, drain0 = P.runOne, P.drain
    cmd(h, "ghost.load", "4", "mod")
    cmd(h, "ghost.modq", "on")
    assert not same(h, P.runOne, run0) and not same(h, P.drain, drain0)
    off = cmd(h, "ghost.modq", "off")
    assert off.ok is True and off.on is False
    assert same(h, P.runOne, run0) and same(h, P.drain, drain0) and P.extra is None
    assert P.runOneBase is None and P.drainBase is None


def test_ghost_modq_refuses_a_load_under_another_scheduler():
    h = boot()
    cmd(h, "ghost.load", "4", "burst")
    r = cmd(h, "ghost.modq", "on")
    assert r.ok is False and "ghost.load <N> mod" in r.reason
    assert cmd(h, "ghost.modq", "sideways") == "usage: ghost.modq <on|off>"


def test_every_other_scheduler_runs_its_ghosts_dry_and_store_skipped():
    h = boot()
    W, S = h.NR.server.writer, h.NR.server.store
    cmd(h, "ghost.load", "4", "burst")
    dry0 = W.stats.dry
    h.minute()
    h.tick(5)
    assert h.H0.g.runs == 3 and W.stats.dry - dry0 == 3
    assert W.dry is None and S.skip is None
    for name in ghost_names(h):
        assert S.file.lastWrite[name] is None


def test_feed_points_a_ghosts_engine_reads_at_its_carriers_writer_inputs():
    h = boot()
    W = h.NR.server.writer
    W.inp["admin"] = h.rt.table_from({"endurance": 0.5})
    r = cmd(h, "ghost.load", "4", "burst", "feed")
    assert r.ok is True
    for name in ghost_names(h):
        assert same(h, W.inp[name], W.inp["admin"])                      # the same table, the carrier's
    cmd(h, "ghost.stop")
    for name in ghost_names(h):
        assert W.inp[name] is None                                 # ghost.stop clears what the feed left


def test_a_raising_ghost_run_still_restores_both_seams():
    h = boot()
    W, S = h.NR.server.writer, h.NR.server.store
    cmd(h, "ghost.load", "4", "burst")
    h.minute()
    h.tick(5)
    G = h.H0.g
    assert G.failures == 0
    G.failures = 0
    h.rt.eval("""function(NR)
        NR.server.minute.runReal = NR.server.minute.run
        NR.server.minute.run = function() error("boom") end
    end""")(h.NR)
    h.H0.runOne(G.ghosts[1])
    assert G.failures == 1 and "boom" in G.lastError
    assert W.dry is None and S.skip is None                        # restored on the raising path too


def test_modrun_idles_after_ghost_stop_without_modq_off_and_a_burst_load():
    h = boot()
    P = h.NR.server.players
    cmd(h, "ghost.load", "4", "mod")
    cmd(h, "ghost.modq", "on")
    stale = h.rt.eval("function(P) return P.extra.run end")(P)
    cmd(h, "ghost.stop")                                           # modq never turned off: P.extra stays
    assert P.extra is not None
    cmd(h, "ghost.load", "4", "burst")                             # a new load with the same ghost names
    G = h.H0.g
    h.minute()
    h.tick(5)                                                      # the store's skip seam fills G.byName
    assert G.byName is not None
    runs0 = G.runs
    for name in ghost_names(h):
        stale(name)                                                # the mod's queue draining a stale name
    assert G.runs == runs0                                         # the burst load's ghosts ran nothing from it
    assert h.H0.modOpen is False
