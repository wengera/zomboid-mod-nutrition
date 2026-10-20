"""The drain options bench (Plan 17 Task 3, spec section 3; Rule 6): a server minute's Java calls and a player-minute's
host time, against the build before.

Loads the golden trace's host (testing/tests/kernel/golden_trace.py) from a tree (this checkout by default, or --root, a
`git archive` of the build before), puts n golden players online (g1, g2, ...; 1 and 2 by default), plays them five
minutes and then counts, over 10 more minutes, every call into an engine stand-in: the players (test_minute_pipeline's
counting stub) and the engine globals the mod calls (GLOBALS, with every table they answer, the sandbox options object
included), split by phase: the server minute (every EveryOneMinute listener: the options poll, the players' minute and
its hoisted reads) and the queue's drain (the OnTick frames that run each player's pipeline). The sandbox stand-in
answers getDayLengthMinutes 90, so the day length's read is counted. Two cases: steady (g1 as the golden trace plays
it) and drain (each player's body water set 12 % short, so the dehydration state drains every minute). The host time
is the median over 7 fresh hosts of the queue's drain a minute, per player.

    python tools/bench_drain.py [--root <tree>]
"""
import argparse
import os
import statistics
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GLOBALS = ("getGameTime", "getOnlinePlayers", "getSandboxOptions", "getServerOptions", "sendServerCommand",
           "sendSyncPlayerFields", "syncBodyPart", "ZombRandFloat", "ZombRand", "addXp", "instanceItem",
           "getTimestampMs")

COUNT = r"""
function(C, names, extra)
    local seen = {}
    local function wrap(t)
        if type(t) ~= "table" or seen[t] then return t end
        seen[t] = true
        local keys = {}
        for k, v in pairs(t) do
            if type(v) == "function" then keys[#keys + 1] = k end
        end
        for i = 1, #keys do
            local k = keys[i]
            local f = t[k]
            t[k] = function(...)
                C.n = C.n + 1
                C.by[k] = (C.by[k] or 0) + 1
                return wrap(f(...))
            end
        end
        return t
    end
    for i = 1, #names do
        local f = _G[names[i]]
        if type(f) == "function" then
            local k = names[i]
            _G[k] = function(...)
                C.n = C.n + 1
                C.by[k] = (C.by[k] or 0) + 1
                return wrap(f(...))
            end
        end
    end
    for i = 1, #extra do wrap(extra[i]) end
end
"""
DAY = r"""
function()
    local so = NutritionRevamp.sandbox()
    so.getDayLengthMinutes = function(s) return 90 end
    return so
end
"""
NAMES = ("g1", "g2", "g3", "g4")


def _load(root):
    for p in (os.path.join(root, "testing", "tests", "kernel"), os.path.join(root, "testing", "tests")):
        sys.path.insert(0, p)
    import golden_trace  # noqa: E402
    return golden_trace


def _host(gt, n, case):
    h = gt.new_host()
    so = h.rt.eval(DAY)()
    players = [gt._new_player(h, NAMES[i], gt.MACROS[NAMES[i]]) for i in range(n)]
    h.online(*players)
    start = gt.START_AGE
    for m in range(1, 5):
        h.T.age = start + m / 60.0
        h.minute()
        h.tick(gt.TICKS)
    if case == "drain":
        for i in range(n):
            b = h.record(NAMES[i])["body"]
            h.record(NAMES[i])["fluids"]["water"] = -0.12 * (b["fm"] + b["lm"] + b["lx"]) * 1000.0
    C = h.rt.eval("{ n = 0, by = {} }")
    h.rt.eval(COUNT)(C, h.rt.table(*GLOBALS), h.rt.table(so, *players))
    h.T.age = start + 5 / 60.0
    h.minute()
    h.tick(gt.TICKS)
    return h, C


def measure(gt, n, case, minutes=10):
    h, C = _host(gt, n, case)
    srv, ply, wall, day = 0, 0, [], 0
    by_srv = {}
    for m in range(6, 6 + minutes):
        h.T.age = gt.START_AGE + m / 60.0
        n0 = C.n
        snap = dict(C.by.items())
        h.minute()
        srv += C.n - n0
        for k, v in C.by.items():
            d = v - snap.get(k, 0)
            if d:
                by_srv[k] = by_srv.get(k, 0) + d
        n1 = C.n
        d1 = C.by["getDayLengthMinutes"] or 0
        t0 = time.perf_counter()
        h.tick(gt.TICKS)
        wall.append((time.perf_counter() - t0) * 1000.0)
        ply += C.n - n1
        day += (C.by["getDayLengthMinutes"] or 0) - d1
    return (srv / minutes, ply / minutes, statistics.median(wall), {k: v / minutes for k, v in sorted(by_srv.items())},
            day / minutes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=REPO, help="the tree whose mod and host to load (a git archive of a build)")
    ap.add_argument("--players", type=int, nargs="*", default=[1, 2])
    a = ap.parse_args(argv)
    gt = _load(os.path.abspath(a.root))
    for case in ("steady", "drain"):
        for n in a.players:
            walls = []
            for _ in range(7):
                srv, ply, w, by, day = measure(gt, n, case)
                walls.append(w / n)
            print("%s, %d player(s): %.1f Java calls a server minute, %.1f a player-minute (%.1f day-length reads); host "
                  "%.3f ms a player-minute" % (case, n, srv, ply / n, day / n, statistics.median(walls)))
            print("    server minute by member: %s" % ", ".join("%s %g" % kv for kv in by.items()))


if __name__ == "__main__":
    main()
