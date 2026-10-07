r"""The golden trace of 1.0.0 (Plan 10 Task R0, ruling 3): the refactor's oracle.

run(host) drives six stand-in players g1..g6 through 240 slow minutes on server_host.Host, fully deterministic:
ZombRandFloat (the only random global the mod's Lua calls; `grep -rn 'ZombRand\|math.random' mod/` finds it in
NR_Server_Effects, NR_Server_Metabolism and NR_Server_Nutrients) and ZombRand are a seeded Park-Miller generator
in the env, and getTimestampMs stays absent (the bus's push gap is then the slow minute itself).

Each minute m = 1..240: the world age advances 1/60 h from 100.0; the minute's events apply; every EveryOneMinute
listener fires (h.minute()), then 25 OnTick frames (h.tick(25)); at every 30th minute a snapshot is taken.
Events: meals at minutes 10, 70 and 130 (IN.land with a fixed per-player vector from NR.data.nutrients.get);
g2 drinks 0.25 L of water at minute 60 (K.vector.fluid of NR.data.fluids.get("Water")); g3 dies at minute 100
(deadFlag) and at 101 OnNewGame fires for a new g3 object, which replaces the old one in the online list; g4
departs at 150 and returns as a new object at 180; at 200 the bus answers one "mirror.request" by g5.
A snapshot: every player's full store record, NR.server.<name>.stats for every adapter that has one (and the
bus's effects stats, under "bus.effects"), and the count of sendServerCommand calls by command name.

serialize(trace) is deterministic JSON: keys sorted, one value per line, every number written "%.17g" (a
non-finite one as a quoted string), a table key that is a number written the same way.

    python testing/tests/kernel/golden_trace.py --write    records golden/trace-1.0.0.json (never re-recorded in
                                                           Plan 10: ruling 3)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lupa.lua51 as lua51  # noqa: E402

import server_host  # noqa: E402

GOLDEN = os.path.join(HERE, "golden", "trace-1.0.0.json")
SEED = 20261007
START_AGE = 100.0
MINUTES = 240
TICKS = 25
SNAPSHOT_EVERY = 30
MEAL_MINUTES = (10, 70, 130)
NAMES = ("g1", "g2", "g3", "g4", "g5", "g6")

# Starting macros (calories, carbs, lipids, proteins), distinct per player.
MACROS = {
    "g1": (1000.0, 100.0, 40.0, 60.0),
    "g2": (1500.0, 180.0, 55.0, 75.0),
    "g3": (600.0, 60.0, 25.0, 40.0),
    "g4": (2200.0, 250.0, 90.0, 110.0),
    "g5": (800.0, 120.0, 30.0, 50.0),
    "g6": (1250.0, 140.0, 70.0, 95.0),
}
RESPAWN_G3 = (900.0, 110.0, 35.0, 55.0)
RETURN_G4 = (1700.0, 200.0, 70.0, 90.0)

# The fixed meal per player: a vanilla type read through the data loader (never the raw table).
MEALS = {
    "g1": "Base.Apple",
    "g2": "Base.Bread",
    "g3": "Base.TinnedBeans",
    "g4": "Base.Steak",
    "g5": "Base.Cheese",
    "g6": "Base.Banana",
}
DRINK_LITRES = 0.25

# The env addendum: a Park-Miller minimal standard generator (16807 * state < 2^46, exact in doubles), the
# sendServerCommand stand-in counting by command name.
RANDOM_ENV = r"""
NR_T.rng = %d
NR_T.sent = {}
local function nextU()
    NR_T.rng = math.fmod(16807 * NR_T.rng, 2147483647)
    return NR_T.rng / 2147483647
end
ZombRandFloat = function(lo, hi) return lo + (hi - lo) * nextU() end
ZombRand = function(a, b)
    if b == nil then return math.floor(a * nextU()) end
    return a + math.floor((b - a) * nextU())
end
sendServerCommand = function(player, module, command, args)
    local k = tostring(command)
    NR_T.sent[k] = (NR_T.sent[k] or 0) + 1
end
""" % SEED


def new_host():
    return server_host.Host(extra_env=RANDOM_ENV)


# --- the Lua value walk -------------------------------------------------------------------------------

class _Num:
    __slots__ = ("text",)

    def __init__(self, x):
        x = float(x)
        self.text = ("%.17g" % x) if math.isfinite(x) else json.dumps("%.17g" % x)


def _key(k):
    if isinstance(k, bool):
        return "<bool:%s>" % k
    if isinstance(k, (int, float)):
        return "%.17g" % float(k)
    if isinstance(k, str):
        return k
    if isinstance(k, bytes):
        return k.decode("utf-8")
    return "<%s>" % lua51.lua_type(k)


def walk(v, stack=()):
    """A Lua value as plain Python: a table a dict keyed by strings, a number a _Num."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, bytes):
        return v.decode("utf-8")
    if isinstance(v, (int, float)):
        return _Num(v)
    t = lua51.lua_type(v)
    if t == "table":
        if any(v is s for s in stack):
            raise ValueError("cycle in a walked table")
        out = {}
        for k, x in v.items():
            ks = _key(k)
            if ks in out:
                raise ValueError("key collision: %r" % ks)
            out[ks] = walk(x, stack + (v,))
        return out
    return "<%s>" % t


def _emit(v, ind, parts):
    if isinstance(v, _Num):
        parts.append(v.text)
    elif v is None or isinstance(v, (bool, str)):
        parts.append(json.dumps(v))
    elif isinstance(v, (int, float)):
        parts.append(_Num(v).text)
    elif isinstance(v, list):
        if not v:
            parts.append("[]")
            return
        parts.append("[\n")
        for i, x in enumerate(v):
            parts.append(" " * (ind + 1))
            _emit(x, ind + 1, parts)
            parts.append(",\n" if i < len(v) - 1 else "\n")
        parts.append(" " * ind + "]")
    elif isinstance(v, dict):
        if not v:
            parts.append("{}")
            return
        parts.append("{\n")
        keys = sorted(v)
        for i, k in enumerate(keys):
            parts.append(" " * (ind + 1) + json.dumps(k) + ": ")
            _emit(v[k], ind + 1, parts)
            parts.append(",\n" if i < len(keys) - 1 else "\n")
        parts.append(" " * ind + "}")
    else:
        raise TypeError("unserialisable: %r" % (v,))


def serialize(trace):
    parts = []
    _emit(trace, 0, parts)
    parts.append("\n")
    return "".join(parts)


# --- the scenario --------------------------------------------------------------------------------------

def _stats(h):
    srv = h.NR.server
    out = {}
    for name, mod in srv.items():
        if lua51.lua_type(mod) != "table":
            continue
        st = mod["stats"]
        if lua51.lua_type(st) == "table":
            out[_key(name)] = walk(st)
    bus = srv["bus"]
    if bus is not None and bus["effects"] is not None and bus["effects"]["stats"] is not None:
        out["bus.effects"] = walk(bus["effects"]["stats"])
    return out


def _snapshot(h, minute):
    recs = h.NR.server.store.records
    return {
        "minute": minute,
        "age": _Num(h.T.age),
        "records": {n: walk(recs[n]) for n in NAMES},
        "stats": _stats(h),
        "sent": walk(h.T.sent),
    }


def _meal(h, name):
    rec = h.record(name)
    if rec is None or rec["stomach"] is None:
        raise AssertionError("no record or stomach for %s at a meal" % name)
    vec = h.NR.data.nutrients.get(MEALS[name])
    if vec is None:
        raise AssertionError("no data entry for %s" % MEALS[name])
    h.NR.server.intake.land(rec, name, vec)


def _drink(h, name):
    rec = h.record(name)
    if rec is None or rec["stomach"] is None:
        raise AssertionError("no record or stomach for %s at the drink" % name)
    water = h.NR.data.fluids.get("Water")
    vec = h.K.vector.fluid(water, DRINK_LITRES)
    h.NR.server.intake.land(rec, name, vec)


def run(host):
    h = host
    players = {n: h.player(n, *MACROS[n]) for n in NAMES}
    order = list(NAMES)

    def publish():
        h.online(*[players[n] for n in order])

    publish()
    h.T.age = START_AGE
    snapshots = []
    for m in range(1, MINUTES + 1):
        h.T.age = START_AGE + m / 60.0
        if m in MEAL_MINUTES:
            for n in order:
                _meal(h, n)
        if m == 60:
            _drink(h, "g2")
        if m == 100:
            players["g3"].deadFlag = True
        if m == 101:
            players["g3"] = h.player("g3", *RESPAWN_G3)
            publish()
            h.fire("OnNewGame", players["g3"], None)
        if m == 150:
            order.remove("g4")
            publish()
        if m == 180:
            players["g4"] = h.player("g4", *RETURN_G4)
            order.insert(3, "g4")
            publish()
        if m == 200:
            h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", players["g5"], None)
        h.minute()
        h.tick(TICKS)
        if m % SNAPSHOT_EVERY == 0:
            snapshots.append(_snapshot(h, m))
    return {"snapshots": snapshots, "printed_count": len(h.printed())}


def main(argv):
    text = serialize(run(new_host()))
    if "--write" in argv:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s (%d bytes)" % (GOLDEN, len(text.encode("utf-8"))))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
