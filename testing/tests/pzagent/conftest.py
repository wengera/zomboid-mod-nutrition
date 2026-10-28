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
        self.writers = []          # every writer opened, in order; each one's closed flag is set by its close

    def writer(self, name, create, append):
        self.opens += 1
        if self.fail_next:
            self.fail_next = False
            return None
        fs = self
        if not (append and fs.append_works):
            fs.files[name] = ""
        class W:
            closed = False
            def write(self, s):
                fs.files[name] = fs.files.get(name, "") + s
                if fs.write_cost_ms and fs.clock is not None:
                    fs.clock["ms"] += fs.write_cost_ms
            def close(self):
                self.closed = True
        w = W()
        fs.writers.append(w)
        return w

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
MOODLE_NAMES = ("HUNGRY", "THIRST", "TIRED", "ENDURANCE", "PANIC", "PAIN", "INJURED", "BLEEDING", "SICK", "WET", "STRESS", "UNHAPPY",
                "HEAVY_LOAD")


FOODS = ("Base.Bread", "Base.Apple", "Base.CannedBeans", "Base.Crisps")


def make_fluid(amount=0.5, poison=False, clean=True):
    """A fluid container whose amount is fc.st["amount"] (a drink lowers it)."""
    st = {"amount": amount}
    fc = J(getAmount=lambda s: st["amount"], isEmpty=lambda s: st["amount"] <= 0, isPoisonous=lambda s: poison,
           isFilledWithCleanWater=lambda s: clean)
    fc.st = st
    return fc


def make_item(ft, iid, food=()):
    """An inventory item of full type ft and id iid: IsFood true for a name in FOODS or `food`, a fluid container for a
    name holding Bottle (clean water) or Bleach (poisonous), never a two-hand weapon, weight 1.0."""
    is_food = ft in FOODS or ft in food
    fc = make_fluid() if "Bottle" in ft else make_fluid(poison=True, clean=False) if "Bleach" in ft else None
    return J(getFullType=lambda s: ft, getID=lambda s: iid, getWeight=lambda s: 1.0, IsFood=lambda s: is_food,
             getFluidContainer=lambda s: fc, isTwoHandWeapon=lambda s: False,
             getHungerChange=lambda s: -0.1 if is_food else 0.0)


def make_weapon(max_range=1.25, range_mod=1.0, cond=10, wid=900, two_hands=False):
    """A held melee weapon: getMaxRange(chr) and getRangeMod(chr) answer max_range and range_mod (None makes the
    member absent)."""
    w = J(_cls="HandWeapon", getFullType=lambda s: "Base.BaseballBat", getCondition=lambda s: cond,
          getID=lambda s: wid, isTwoHandWeapon=lambda s: two_hands)
    if max_range is not None:
        w.getMaxRange = lambda s, chr: max_range
    if range_mod is not None:
        w.getRangeMod = lambda s, chr: range_mod
    return w


def make_player(x=10.0, y=20.0, z=0, hunger=0.3, health=100.0, items=(), moodle_levels=None, weapon=None,
                weight=4.5, max_weight=8, part_health=None, square="sq", wounds=(0, 0, 0), food=(),
                zombies_near=(0, 0, 0), traits=()):
    """`weapon` is the primary hand item; faceThisObject and DoAttack record into p.faced and p.attacks, and
    isAsleep answers p.asleep["v"] (Task 11's fight and sleep).
    Plan 22 probe: the motor setters (setForceRun, setForceSprint, setAutoWalk, setAutoWalkDirection, setRunning,
    setSprinting) record (name, value) into p.sets and the latest value into p.motor, which isForceRun, isForceSprint and
    isAutoWalk read; getMaxWeight answers max_weight, the inventory's getCapacityWeight weight, getCurrentSquare square;
    the body damage's getNumPartsBleeding/Scratched/Bitten answer wounds, HasInjury any(wounds), and getBodyParts lists
    one part per part_health entry (17 parts at 100 by default)."""
    vals = {"HUNGER": hunger, "THIRST": 0.2, "FATIGUE": 0.1, "ENDURANCE": 0.9, "PANIC": 0.0, "PAIN": 0.0,
            "FOOD_SICKNESS": 0.0, "WETNESS": 5.0, "TEMPERATURE": 37.0}
    stats = J(get=lambda s, stat: vals[stat])
    levels = moodle_levels or {}
    parts = [J(getHealth=lambda s, h=h: h) for h in (part_health if part_health is not None else [100.0] * 17)]
    bd = J(getOverallBodyHealth=lambda s: health, getHealth=lambda s: health,
           getNumPartsBleeding=lambda s: wounds[0], getNumPartsScratched=lambda s: wounds[1],
           getNumPartsBitten=lambda s: wounds[2], HasInjury=lambda s: any(wounds),
           getBodyParts=lambda s: J(size=lambda s2: len(parts), get=lambda s2, i: parts[i]))
    held = [make_item(ft, 1000 + i, food=food) for i, ft in enumerate(items)]
    inv = J(getItems=lambda s: J(size=lambda s2: len(held), get=lambda s2, i: held[i]),
            getCapacityWeight=lambda s: weight,
            getItemById=lambda s, iid: next((it for it in held if it.getID(it) == iid), None))
    faced, attacks, asleep = [], [], {"v": False}
    p = J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: z, getDir=lambda s: "N",
          isPlayerMoving=lambda s: False, IsRunning=lambda s: False, isSprinting=lambda s: False,
          getStats=lambda s: stats, getBodyDamage=lambda s: bd, getInventory=lambda s: inv,
          getPrimaryHandItem=lambda s: weapon, getMoodles=lambda s: J(getMoodleLevel=lambda s2, t: levels.get(t, 0)),
          faceThisObject=lambda s, o: faced.append(o), DoAttack=lambda s, f: attacks.append(f) or True,
          isAsleep=lambda s: asleep["v"], getPlayerNum=lambda s: 0)
    p.faced, p.attacks, p.asleep = faced, attacks, asleep
    # Plan 22 Task 4: items are make_item objects (ids 1000 + i) in the mutable list p.held, which the inventory's
    # getItems and getItemById read; isAttackStarted and getMeleeDelay read p.attack["started"] and p.attack["delay"]
    p.held = held
    attack = {"started": False, "delay": 0.0}
    p.attack = attack
    p.isAttackStarted, p.getMeleeDelay = lambda s: attack["started"], lambda s: attack["delay"]
    sets, motor = [], {"forceRun": False, "forceSprint": False, "autoWalk": False}

    def setter(name, key=None):
        def f(s, v):
            sets.append((name, v))
            if key is not None:
                motor[key] = v
        return f
    p.setForceRun, p.setForceSprint = setter("setForceRun", "forceRun"), setter("setForceSprint", "forceSprint")
    p.setAutoWalk, p.setAutoWalkDirection = setter("setAutoWalk", "autoWalk"), setter("setAutoWalkDirection")
    p.setRunning, p.setSprinting = setter("setRunning"), setter("setSprinting")
    p.isForceRun, p.isForceSprint = lambda s: motor["forceRun"], lambda s: motor["forceSprint"]
    p.isAutoWalk = lambda s: motor["autoWalk"]
    p.getMaxWeight, p.getCurrentSquare = lambda s: max_weight, lambda s: square
    p.sets, p.motor = sets, motor
    # Plan 23 Task 8 (sleep): the stats answer the three zombie counts of `zombies_near` (visible, chasing, very close),
    # hasTrait answers membership of `traits`, and the five sleep setters (setBed, setBedType, setForceWakeUpTime,
    # setAsleepTime, setAsleep) record (name, value) into p.sleep in call order, setAsleep also writing p.asleep["v"]
    zc = list(zombies_near)
    p.zombies_near = zc
    stats.getNumVisibleZombies = lambda s: zc[0]
    stats.getNumChasingZombies = lambda s: zc[1]
    stats.getNumVeryCloseZombies = lambda s: zc[2]
    p.stat_values = vals
    trait_set = set(traits)
    p.hasTrait = lambda s, t: t in trait_set
    sleep = []
    p.sleep = sleep

    def sleep_setter(name):
        def f(s, v):
            sleep.append((name, v))
            if name == "setAsleep":
                asleep["v"] = v
        return f
    for name in ("setBed", "setBedType", "setForceWakeUpTime", "setAsleepTime", "setAsleep"):
        setattr(p, name, sleep_setter(name))
    # Task 8 fix 1: the animation variables, setVariable(name, value) recording into p.variables, and
    # getVariableBoolean(name) answering false for a name never set (the jar's IAnimationVariableSource default)
    variables = {}
    p.variables = variables
    p.setVariable = lambda s, k, v: variables.__setitem__(k, v)
    p.getVariableBoolean = lambda s, k: variables.get(k, False) is True
    return p


def make_zombie(zid, x, y, dead=False, health=1.0):
    return J(getOnlineID=lambda s: zid, getX=lambda s: x, getY=lambda s: y, isDead=lambda s: dead,
             getTarget=lambda s: None, isCrawling=lambda s: False, getHealth=lambda s: health)


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
    L.execute(open(lua_file("shared/PZAgent_Schema.lua"), encoding="utf-8").read())
    g.getCell = lambda: g._cell
    g._cell = make_cell()
    g.CharacterStat = J(**{n: n for n in STAT_NAMES})
    g.MoodleType = J(**{n: n for n in MOODLE_NAMES})
    g.instanceof = lambda o, cls: getattr(o, "_cls", None) == cls
    g.getGameTime = lambda: J(getHour=lambda s: 7, getMinutes=lambda s: 30, getWorldAgeHours=lambda s: 31.5,
                                getTimeOfDay=lambda s: 8.0)
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
    # Plan 22 probe: OnPlayerUpdate and OnPlayerGetDamage keep their handlers in g._updHandlers and g._damageHandlers,
    # a Vector2 whose new records (x, y), a core whose toggle-to-run is g._core.toggle (setToggleToRun records into
    # g._core.toggles), and ISDropWorldItemAction's 8-argument new
    upd_handlers, damage_handlers = [], []
    g._updHandlers, g._damageHandlers = upd_handlers, damage_handlers
    g.Events = J(OnTick=J(Add=lambda f: handlers.append(f)), OnPlayerUpdate=J(Add=lambda f: upd_handlers.append(f)),
                 OnPlayerGetDamage=J(Add=lambda f: damage_handlers.append(f)))
    g.Vector2 = J(new=lambda x, y: J(_cls="Vector2", x=x, y=y))
    core = J(toggle=False, toggles=[])

    def set_toggle(s, v):
        core.toggles.append(v)
        core.toggle = v
    core.isToggleToRun, core.setToggleToRun = lambda s: core.toggle, set_toggle
    g._core = core
    g.getCore = lambda: core
    g.ISDropWorldItemAction = J(new=lambda cls, p, item, sq, xo, yo, zo, rot, multi: J(
        Type="ISDropWorldItemAction", character=p, item=item, args=(sq, xo, yo, zo, rot, multi)))
    # Plan 22 Task 4: ISEquipWeaponAction:new(character, item, time, isPrimary, twoHands) records its five arguments
    # into g._equips
    equips = []
    g._equips = equips
    g.ISEquipWeaponAction = J(new=lambda cls, p, item, t, primary, two: equips.append((p, item, t, primary, two)) or J(
        Type="ISEquipWeaponAction", character=p, item=item))
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
