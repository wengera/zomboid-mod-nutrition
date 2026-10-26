"""The lupa host for PZAgent's Lua: Python stubs stand in for the Java globals (ruling P21-3)."""
import os
import sys
import pytest
from lupa import LuaRuntime

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

    def writer(self, name, create, append):
        self.opens += 1
        if self.fail_next:
            self.fail_next = False
            return None
        fs = self
        if not (append and fs.append_works):
            fs.files[name] = ""
        class W:
            def write(self, s): fs.files[name] = fs.files.get(name, "") + s
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


def make_player(x=10.0, y=20.0, z=0, hunger=0.3, health=100.0, items=()):
    stats = J(getHunger=lambda s: hunger, getThirst=lambda s: 0.2, getFatigue=lambda s: 0.1,
              getEndurance=lambda s: 0.9, getPanic=lambda s: 0.0, getPain=lambda s: 0.0)
    bd = J(getOverallBodyHealth=lambda s: health, getHealth=lambda s: health)
    inv = J(getItems=lambda s: J(size=lambda s2: len(items), get=lambda s2, i: J(getFullType=lambda s3, i=i: items[i])))
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: z, getDir=lambda s: "N",
             isPlayerMoving=lambda s: False, IsRunning=lambda s: False, isSprinting=lambda s: False,
             getStats=lambda s: stats, getBodyDamage=lambda s: bd, getInventory=lambda s: inv,
             getPrimaryHandItem=lambda s: None, getMoodles=lambda s: J(getMoodleLevel=lambda s2, t: 0))


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
    L = LuaRuntime(unpack_returned_tuples=True)
    g = L.globals()
    g.getFileWriter = fs.writer
    g.getFileReader = fs.reader
    clock = {"ms": 1000}
    g.getTimestampMs = lambda: clock["ms"]
    g._clock = clock
    g.print = lambda *a: None
    L.execute(open(lua_file("shared/PZAgent_Core.lua"), encoding="utf-8").read())
    g.getCell = lambda: g._cell
    g._cell = make_cell()
    g.getGameTime = lambda: J(getHour=lambda s: 7, getMinutes=lambda s: 30, getWorldAgeHours=lambda s: 31.5)
    q = make_queue()
    g._queue = q
    g.ISTimedActionQueue = J(add=lambda a: q.add(a), getTimedActionQueue=lambda p: q.getTimedActionQueue(p),
                             isPlayerDoingAction=lambda p: q.isPlayerDoingAction(p), clear=lambda p: q.clear(p))
    g.ISWalkToTimedAction = J(new=lambda cls, p, sq: J(Type="ISWalkToTimedAction", sq=sq))
    handlers = []
    g._handlers = handlers
    g.Events = J(OnTick=J(Add=lambda f: handlers.append(f)))
    return L
