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

Plan 18 Task 3: the stand-in's parts answer the added pain, and between minutes the bench applies vanilla's server decay
of it (golden_trace's NR_T.decayPain, 0.9 at the 90-minute day; absent from a tree before Plan 18, where it is skipped),
so a symptom part is re-set every minute as live. BodyPartType (its static FromIndex) is counted with the engine
globals. The stats objects are counted too (the writer hoists them before the count, so until Plan 18 Task 3 the
bench missed every stat get and set; re-run both builds with this file). The player-minute's symptom members
(SYMPTOM_MEMBERS) and the stat sets by stat are printed per player-minute.

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
SYMPTOM_MEMBERS = ("FromIndex", "getBodyPart", "getAdditionalPain", "setAdditionalPain")
PAIN_DECAY_90 = 0.9   # vanilla's added-pain decay a game minute at the 90-minute day (0.01 x dayMin, Plan 18 Task 1 J3)
STAT_SETS = r"""
function(C, players)
    local out = {}
    for i = 1, #players do
        local p = players[i]
        local st = p:getStats()
        local o = st.set
        st.set = function(s, k, v)
            local kk = "set:" .. tostring(k)
            C.by[kk] = (C.by[kk] or 0) + 1
            return o(s, k, v)
        end
        out[#out + 1] = st
    end
    return out
end
"""


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
    stats = h.rt.eval(STAT_SETS)(C, h.rt.table(*players))
    # the stats objects counted too: the writer hoisted them before the count, so the players' wrap never reaches them
    extra = [so] + list(players) + [stats[i] for i in range(1, len(players) + 1)]
    if h.G.BodyPartType is not None:
        extra.append(h.G.BodyPartType)
    h.rt.eval(COUNT)(C, h.rt.table(*GLOBALS), h.rt.table(*extra))
    h.T.age = start + 5 / 60.0
    h.minute()
    h.tick(gt.TICKS)
    return h, C


def _decay(h):
    if h.T.decayPain is not None:
        h.T.decayPain(PAIN_DECAY_90)


def measure(gt, n, case, minutes=10):
    h, C = _host(gt, n, case)
    srv, ply, wall, day = 0, 0, [], 0
    by_srv, by_ply = {}, {}
    for m in range(6, 6 + minutes):
        _decay(h)
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
        snap = dict(C.by.items())
        d1 = C.by["getDayLengthMinutes"] or 0
        t0 = time.perf_counter()
        h.tick(gt.TICKS)
        wall.append((time.perf_counter() - t0) * 1000.0)
        ply += C.n - n1
        for k, v in C.by.items():
            d = v - snap.get(k, 0)
            if d:
                by_ply[k] = by_ply.get(k, 0) + d
        day += (C.by["getDayLengthMinutes"] or 0) - d1
    return (srv / minutes, ply / minutes, statistics.median(wall), {k: v / minutes for k, v in sorted(by_srv.items())},
            day / minutes, {k: v / minutes for k, v in sorted(by_ply.items())})


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
                srv, ply, w, by, day, byp = measure(gt, n, case)
                walls.append(w / n)
            print("%s, %d player(s): %.1f Java calls a server minute, %.1f a player-minute (%.1f day-length reads); host "
                  "%.3f ms a player-minute" % (case, n, srv, ply / n, day / n, statistics.median(walls)))
            print("    server minute by member: %s" % ", ".join("%s %g" % kv for kv in by.items()))
            sym = [(k, byp.get(k, 0) / n) for k in SYMPTOM_MEMBERS]
            sets = [(k[4:], v / n) for k, v in byp.items() if k.startswith("set:")]
            print("    player-minute symptom members: %s; stat sets: %s"
                  % (", ".join("%s %g" % kv for kv in sym), ", ".join("%s %g" % kv for kv in sets)))


if __name__ == "__main__":
    main()
