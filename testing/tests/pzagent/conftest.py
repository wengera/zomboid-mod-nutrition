"""The lupa host for PZAgent's Lua: Python stubs stand in for the Java globals (ruling P21-3)."""
import json
import os
import sys
import pytest
from lupa import LuaRuntime
import lupa.lua51 as lua51

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "testing"))
LUA = os.path.join(ROOT, "testing", "PZAgent", "PZAgent", "42", "media", "lua")


def lua_file(name):
    return os.path.join(LUA, name)


class FakeFS:
    """getFileWriter/getFileReader over a dict; append honoured when self.append_works."""
    def __init__(self):
        self.files = {}
        self.append_works = True
        self.opens = 0
        self.fail_next = False
        self.write_cost_ms = 0     # added to the lua fixture's clock by every write (a flush's own cost)
        self.clock = None

    def writer(self, name, create, append):
        self.opens += 1
        if self.fail_next:
            self.fail_next = False
            return None
        fs = self
        if not (append and fs.append_works):
            fs.files[name] = ""
        class W:
            def write(self, s):
                fs.files[name] = fs.files.get(name, "") + s
                if fs.write_cost_ms and fs.clock is not None:
                    fs.clock["ms"] += fs.write_cost_ms
            def close(self): pass
        return W()

    def reader(self, name, create):
        if name not in self.files:
            return None
        lines = iter(self.files[name].split("\n"))
        class R:
            def readLine(self):
                try:
                    return next(lines)
                except StopIteration:
                    return None
            def close(self): pass
        return R()


class J:
    """A Java-like object: methods from a dict; a missing member is a missing attribute (nil in Lua)."""
    def __init__(self, **m):
        for k, v in m.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return None

    def __getitem__(self, name):
        return self.__dict__.get(name)


STAT_NAMES = ("HUNGER", "THIRST", "FATIGUE", "ENDURANCE", "PANIC", "PAIN", "FOOD_SICKNESS", "WETNESS", "TEMPERATURE")
MOODLE_NAMES = ("HUNGRY", "THIRST", "TIRED", "ENDURANCE", "PANIC", "PAIN", "INJURED", "BLEEDING", "SICK", "WET", "STRESS", "UNHAPPY")


def make_player(x=10.0, y=20.0, z=0, hunger=0.3, health=100.0, items=(), moodle_levels=None, weapon=None):
    """`weapon` is the primary hand item; faceThisObject and DoAttack record into p.faced and p.attacks, and
    isAsleep answers p.asleep["v"] (Task 11's fight and sleep)."""
    vals = {"HUNGER": hunger, "THIRST": 0.2, "FATIGUE": 0.1, "ENDURANCE": 0.9, "PANIC": 0.0, "PAIN": 0.0,
            "FOOD_SICKNESS": 0.0, "WETNESS": 5.0, "TEMPERATURE": 37.0}
    stats = J(get=lambda s, stat: vals[stat])
    levels = moodle_levels or {}
    bd = J(getOverallBodyHealth=lambda s: health, getHealth=lambda s: health)
    inv = J(getItems=lambda s: J(size=lambda s2: len(items), get=lambda s2, i: J(getFullType=lambda s3, i=i: items[i])))
    faced, attacks, asleep = [], [], {"v": False}
    p = J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: z, getDir=lambda s: "N",
          isPlayerMoving=lambda s: False, IsRunning=lambda s: False, isSprinting=lambda s: False,
          getStats=lambda s: stats, getBodyDamage=lambda s: bd, getInventory=lambda s: inv,
          getPrimaryHandItem=lambda s: weapon, getMoodles=lambda s: J(getMoodleLevel=lambda s2, t: levels.get(t, 0)),
          faceThisObject=lambda s, o: faced.append(o), DoAttack=lambda s, f: attacks.append(f) or True,
          isAsleep=lambda s: asleep["v"], getPlayerNum=lambda s: 0)
    p.faced, p.attacks, p.asleep = faced, attacks, asleep
    return p


def make_zombie(zid, x, y, dead=False):
    return J(getOnlineID=lambda s: zid, getX=lambda s: x, getY=lambda s: y, isDead=lambda s: dead,
             getTarget=lambda s: None, isCrawling=lambda s: False)


def make_cell(zombies=(), squares=None):
    zl = J(size=lambda s: len(zombies), get=lambda s, i: zombies[i])
    sq = squares or {}
    return J(getZombieList=lambda s: zl, getGridSquare=lambda s, x, y, z: sq.get((int(x), int(y), int(z))))


def make_queue():
    q = J(queue=[], adds=[], cleared=0)

    def add(a):
        q.queue.append(a)
        q.adds.append(a)

    def clear(p=None):
        q.queue[:] = []
        q.cleared += 1
    q.add, q.clear = add, clear
    q.isPlayerDoingAction = lambda p=None: len(q.queue) > 0
    q.getTimedActionQueue = lambda p=None: J(queue=q.queue)
    return q


@pytest.fixture
def fs():
    return FakeFS()


@pytest.fixture
def lua(fs):
    """Every Lua test runs on the Lua 5.1 host: Kahlua is a 5.1 dialect (testing/tests/kernel/conftest.py
    does the same)."""
    return make_lua(fs)


def make_lua(fs, runtime=lua51.LuaRuntime):
    """The stubbed host, Lua 5.1 by default, with Lua's collector stopped. Under lupa 2.8, on either runtime, a
    Lua collection can leave a Python object's wrapper resolving to a different object: a Lua function that
    calls p:getX() each call and W:new(p, sq) every 90th call, on plain Python objects, reads p as a function
    after 541 calls (seen here as a goto's p:getX() reading nil a tick after its third re-plan, and earlier as
    'J object is not callable' in the loot filters test); with collectgarbage('stop') it ran 50000 calls
    clean. The real client is Kahlua on the JVM, so the collector is no part of what these tests check."""
    L = runtime(unpack_returned_tuples=True)
    L.execute("collectgarbage('stop')")
    g = L.globals()
    g.getFileWriter = fs.writer
    g.getFileReader = fs.reader
    clock = {"ms": 1000}
    g.getTimestampMs = lambda: clock["ms"]
    g._clock = clock
    fs.clock = clock
    g.print = lambda *a: None
    L.execute(open(lua_file("shared/PZAgent_Core.lua"), encoding="utf-8").read())
    g.getCell = lambda: g._cell
    g._cell = make_cell()
    g.CharacterStat = J(**{n: n for n in STAT_NAMES})
    g.MoodleType = J(**{n: n for n in MOODLE_NAMES})
    g.instanceof = lambda o, cls: getattr(o, "_cls", None) == cls
    g.getGameTime = lambda: J(getHour=lambda s: 7, getMinutes=lambda s: 30, getWorldAgeHours=lambda s: 31.5)
    q = make_queue()
    g._queue = q
    g.ISTimedActionQueue = J(add=lambda a: q.add(a), getTimedActionQueue=lambda p: q.getTimedActionQueue(p),
                             isPlayerDoingAction=lambda p: q.isPlayerDoingAction(p), clear=lambda p: q.clear(p))
    g.ISWalkToTimedAction = J(new=lambda cls, p, sq: J(Type="ISWalkToTimedAction", sq=sq))
    # the four vanilla constructors Act's open/loot/eat/drink queue; each captures its arguments, and
    # g._valid["start"] is what an eat or drink action's isValidStart answers
    valid = {"start": True}
    g._valid = valid
    g.ISOpenCloseDoor = J(new=lambda cls, p, item: J(Type="ISOpenCloseDoor", character=p, item=item))
    g.ISOpenCloseWindow = J(new=lambda cls, p, obj: J(Type="ISOpenCloseWindow", character=p, object=obj))
    g.ISInventoryTransferAction = J(new=lambda cls, p, item, src, dest, time=None: J(
        Type="ISInventoryTransferAction", character=p, item=item, src=src, dest=dest))
    g.ISEatFoodAction = J(new=lambda cls, p, item, pct: J(Type="ISEatFoodAction", character=p, item=item, pct=pct,
                                                         isValidStart=lambda s: valid["start"]))
    g.ISDrinkFluidAction = J(new=lambda cls, p, item, pct: J(Type="ISDrinkFluidAction", character=p, item=item, pct=pct,
                                                            isValidStart=lambda s: valid["start"]))
    # the vanilla sleep entry Act calls, ISWorldObjectContextMenu.onConfirmSleep(this, button, player, bed), a Lua
    # function as in the game: each call lands in g._sleeps as (button.internal, player, bed), and with
    # g._sleep["raise"] set it raises a Lua error instead
    sleeps, sleep = [], {"raise": False}
    g._sleeps, g._sleep = sleeps, sleep
    g._sleepRec = lambda internal, player, bed: sleeps.append((internal, player, bed))
    L.execute("ISWorldObjectContextMenu = { onConfirmSleep = function(this, button, player, bed)"
              " if _sleep.raise then error('onConfirmSleep raised') end"
              " _sleepRec(button.internal, player, bed) end }")
    handlers = []
    g._handlers = handlers
    g.Events = J(OnTick=J(Add=lambda f: handlers.append(f)))
    return L


def write_agent_fixtures(root):
    """Throwaway `agent` (Zombies = 5) and `agent0` (Zombies = 6) fixture records under root, each with its server's
    SandboxVars file: the real fixtures are machine-local and gitignored, and the agent profiles name one or the other
    (agent-nozombies names agent0 since Stage A pass 2)."""
    for name, zombies in (("agent", 5), ("agent0", 6)):
        sv = root / name / "cache" / "server" / "Server"
        sv.mkdir(parents=True)
        (sv / "pzt_SandboxVars.lua").write_text("SandboxVars = {\n    Zombies = %d,\n    DayLength = 4,\n}\n" % zombies)
        (root / name / "fixture.json").write_text(json.dumps(
            {"name": name, "build": "42.21.0", "server": {"name": "pzt", "mods": ["PZTestKit"]},
             "clients": {"admin": {}}}))
    return root


@pytest.fixture
def agent_fixture(tmp_path, monkeypatch):
    """The throwaway agent fixtures (write_agent_fixtures), pzt.fixture pointed at them."""
    from pzt import fixture as fx
    root = write_agent_fixtures(tmp_path / "fixtures")
    monkeypatch.setattr(fx, "FIXTURES", str(root))
    return root
