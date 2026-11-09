"""The lupa host for PZAgent's Lua: Python stubs stand in for the Java globals (ruling P21-3)."""
import json
import math
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


def make_fluid(amount=0.5, poison=False, clean=True, water=True, tainted=False, capacity=1.0, can_add=True, cats=None,
               thirst=None, fluid="Water", sealed=False):
    """A fluid container whose amount is fc.st["amount"] (a drink lowers it). Plan 24 PZA/1.4.1 (P24-F): `water` is
    whether its primary fluid is water, so isWaterSource answers it while the container is not empty (the jar's
    FluidContainer.isWaterSource); isTainted answers `tainted`, getCapacity `capacity` and canAddFluid(fluid)
    `can_add` (each None makes the member absent). PZA/1.5: `cats` (a set of FluidCategory names, None for no
    isCategory member) answers isCategory while the container is not empty, `thirst` (None for no getProperties)
    getProperties():getThirstChange(), getFreeCapacity the capacity less the amount, and getPrimaryFluid a fluid
    whose getFluidTypeString is `fluid`. PZA/1.5.1: canPlayerEmpty answers not `sealed` (None makes it absent)."""
    st = {"amount": amount}
    fc = J(getAmount=lambda s: st["amount"], isEmpty=lambda s: st["amount"] <= 0, isPoisonous=lambda s: poison,
           isFilledWithCleanWater=lambda s: clean)
    if water is not None:
        fc.isWaterSource = lambda s: water and st["amount"] > 0
    if tainted is not None:
        fc.isTainted = lambda s: tainted
    if capacity is not None:
        fc.getCapacity = lambda s: capacity
    if can_add is not None:
        fc.canAddFluid = lambda s, f: can_add and f == "Water"
    if cats is not None:
        fc.isCategory = lambda s, c: st["amount"] > 0 and c in cats
    if thirst is not None:
        fc.getProperties = lambda s: J(getThirstChange=lambda s2: thirst if st["amount"] > 0 else 0.0)
    if capacity is not None:
        fc.getFreeCapacity = lambda s: max(0.0, capacity - st["amount"])
    fc.getPrimaryFluid = lambda s: J(getFluidTypeString=lambda s2: fluid) if st["amount"] > 0 else None
    if sealed is not None:
        fc.canPlayerEmpty = lambda s: not sealed
    fc.st = st
    return fc


def make_item(ft, iid, food=()):
    """An inventory item of full type ft and id iid: IsFood true for a name in FOODS or `food`, a fluid container for a
    name holding Bottle (clean water) or Bleach (poisonous), never a two-hand weapon, weight 1.0. PZA/1.5's care reads:
    isCanBandage for a Bandage or RippedSheets name, getItemAfterCleaning the name without Dirty for a Dirty one, blood
    0, never worn, the cotton rip tag on a Tshirt name."""
    is_food = ft in FOODS or ft in food
    fc = make_fluid() if "Bottle" in ft else make_fluid(poison=True, clean=False, water=False) if "Bleach" in ft else None
    return J(getFullType=lambda s: ft, getID=lambda s: iid, getWeight=lambda s: 1.0, IsFood=lambda s: is_food,
             getFluidContainer=lambda s: fc, isTwoHandWeapon=lambda s: False,
             getHungerChange=lambda s: -0.1 if is_food else 0.0,
             isCanBandage=lambda s: "Bandage" in ft or "RippedSheets" in ft,
             getItemAfterCleaning=lambda s: ft.replace("Dirty", "") if "Dirty" in ft else None,
             getBloodLevel=lambda s: 0.0, isWorn=lambda s: False,
             hasTag=lambda s, t: t == "RIP_CLOTHING_COTTON" and "Tshirt" in ft)


def make_weapon(max_range=1.25, range_mod=1.0, cond=10, wid=900, two_hands=False, min_range=None):
    """A held melee weapon: getMaxRange(chr) and getRangeMod(chr) answer max_range and range_mod (None makes the
    member absent); getMinRange() answers min_range, absent by default (PZA/1.10: the melee fake's bat sets the bat's
    0.61, weapon.txt:6703)."""
    w = J(_cls="HandWeapon", getFullType=lambda s: "Base.BaseballBat", getCondition=lambda s: cond,
          getID=lambda s: wid, isTwoHandWeapon=lambda s: two_hands)
    if max_range is not None:
        w.getMaxRange = lambda s, chr: max_range
    if range_mod is not None:
        w.getRangeMod = lambda s, chr: range_mod
    if min_range is not None:
        w.getMinRange = lambda s: min_range
    return w


def make_player(x=10.0, y=20.0, z=0, hunger=0.3, health=100.0, items=(), moodle_levels=None, weapon=None,
                weight=4.5, max_weight=8, part_health=None, square="sq", wounds=(0, 0, 0), food=(),
                zombies_near=(0, 0, 0), traits=(), worn=()):
    """`weapon` is the primary hand item; faceThisObject and DoAttack record into p.faced and p.attacks, and
    isAsleep answers p.asleep["v"] (Task 11's fight and sleep).
    Plan 22 probe: the motor setters (setForceRun, setForceSprint, setAutoWalk, setAutoWalkDirection, setRunning,
    setSprinting) record (name, value) into p.sets and the latest value into p.motor, which isForceRun, isForceSprint and
    isAutoWalk read; getMaxWeight answers max_weight, the inventory's getCapacityWeight weight, getCurrentSquare square;
    the body damage's getNumPartsBleeding/Scratched/Bitten answer wounds, HasInjury any(wounds), and getBodyParts lists
    one part per part_health entry (17 parts at 100 by default; PZA/1.5: each unwounded, unbandaged, not bleeding,
    its bandage life 0 and so isBandageDirty true, as the jar's BodyPart reads an unbandaged part; PZA/1.7.2: not
    scratched, cut or bitten, so its wound reads false)."""
    vals = {"HUNGER": hunger, "THIRST": 0.2, "FATIGUE": 0.1, "ENDURANCE": 0.9, "PANIC": 0.0, "PAIN": 0.0,
            "FOOD_SICKNESS": 0.0, "WETNESS": 5.0, "TEMPERATURE": 37.0}
    stats = J(get=lambda s, stat: vals[stat])
    levels = moodle_levels or {}
    parts = [J(getHealth=lambda s, h=h: h, bandaged=lambda s: False, bleeding=lambda s: False,
               getBleedingTime=lambda s: 0.0, getBandageLife=lambda s: 0.0, isBandageDirty=lambda s: True,
               deepWounded=lambda s: False, isInfectedWound=lambda s: False, scratched=lambda s: False,
               isCut=lambda s: False, bitten=lambda s: False)
             for h in (part_health if part_health is not None else [100.0] * 17)]
    bd = J(getOverallBodyHealth=lambda s: health, getHealth=lambda s: health,
           getNumPartsBleeding=lambda s: wounds[0], getNumPartsScratched=lambda s: wounds[1],
           getNumPartsBitten=lambda s: wounds[2], HasInjury=lambda s: any(wounds),
           getBodyParts=lambda s: J(size=lambda s2: len(parts), get=lambda s2, i: parts[i]))
    # PZA/1.7 (Task 9 fix 11): BodyDamage.getBodyPart(BodyPartType) answers a rested arm part (no pain, no strain)
    arm = J(getPain=lambda s: 0.0, getStiffness=lambda s: 0.0)
    bd.getBodyPart = lambda s, t: arm
    held = [make_item(ft, 1000 + i, food=food) for i, ft in enumerate(items)]
    inv = J(getItems=lambda s: J(size=lambda s2: len(held), get=lambda s2, i: held[i]),
            getCapacityWeight=lambda s: weight,
            getItemById=lambda s, iid: next((it for it in held if it.getID(it) == iid), None))
    for it in held:                                     # PZA/1.5.1: the main inventory is each item's container
        it.getContainer = lambda s: inv
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
    # Plan 24 PZA/1.4 (ruling P24-C): the combat reads answer p.combat, which a test sets: getSurroundingAttackingZombies
    # its "attackers", getHitReaction its "hitReaction" ("" when none, as the jar's field reads), hasHitReaction whether
    # that is non-empty (the jar's hasHitReaction), isDeathDragDown its "dragDown"
    combat = {"attackers": 0, "hitReaction": "", "dragDown": False}
    p.combat = combat
    p.getSurroundingAttackingZombies = lambda s: combat["attackers"]
    p.getHitReaction = lambda s: combat["hitReaction"]
    p.hasHitReaction = lambda s: combat["hitReaction"] not in ("", None)
    p.isDeathDragDown = lambda s: combat["dragDown"]
    # Plan 24 PZA/1.5 (ruling P24-G): the stance's members record into p.aim: setForceAim(v) sets "force" and
    # nullifyAiming clears it (each call also appended to p.aim["calls"]); isForceAim and isAiming answer "force" (a
    # test sets "aiming" to make isAiming differ); setForwardDirection(x, y) records into "faced"; getVariableString(k)
    # answers p.variables[k] ("" when unset)
    aim = {"force": False, "aiming": None, "calls": [], "faced": []}
    p.aim = aim

    def set_force(s, v):
        aim["force"] = v
        aim["calls"].append(("setForceAim", v))

    def nullify(s):
        aim["force"] = False
        aim["calls"].append(("nullifyAiming", None))
    p.setForceAim, p.nullifyAiming = set_force, nullify
    p.isForceAim = lambda s: aim["force"]
    p.isAiming = lambda s: aim["force"] if aim["aiming"] is None else aim["aiming"]
    p.setForwardDirection = lambda s, fx, fy: aim["faced"].append((fx, fy))
    p.getVariableString = lambda s, k: variables.get(k, "")
    # PZA/1.6 (Task 9 fix 9): getWornItems() lists p.worn, a mutable list of (location, item) pairs (`worn`, empty by
    # default), each as a WornItem whose getLocation() and getItem() answer them; getWornItem(loc) the item worn at loc
    wl = list(worn)
    p.worn = wl
    p.getWornItems = lambda s: J(size=lambda s2: len(wl), get=lambda s2, i: J(getLocation=lambda s3: wl[i][0],
                                                                             getItem=lambda s3: wl[i][1]))
    p.getWornItem = lambda s, loc: next((it for l, it in wl if l == loc), None)
    # PZA/1.9 (Plan 30 Task 1): the sneak flag is one stored field (the jar read's #4654): isSneaking answers
    # p.sneak["on"] and setSneaking(v) writes it, appending v to p.sneak["sets"]; getPerkLevel(perk) answers
    # p.perks.get(perk, 0); isBehind(z) answers whether z.behind is True (a test sets it on the zombie)
    sneak = {"on": False, "sets": []}
    p.sneak = sneak

    def set_sneaking(s, v):
        sneak["on"] = v
        sneak["sets"].append(v)
    p.setSneaking, p.isSneaking = set_sneaking, lambda s: sneak["on"]
    perks = {}
    p.perks = perks
    p.getPerkLevel = lambda s, perk: perks.get(perk, 0)
    p.isBehind = lambda s, z: getattr(z, "behind", None) is True
    # PZA/1.10 (Plan 31 Task 2): getLookAngleRadians and getAnimAngleRadians answer p.angles["look"] and ["body"]
    angles = {"look": 0.0, "body": 0.0}
    p.angles = angles
    p.getLookAngleRadians, p.getAnimAngleRadians = (lambda s: angles["look"]), (lambda s: angles["body"])
    # PZA/1.11 (Plan 32 Task 1): the facing ring. getDirectionAngleRadians answers p.angles["fwd"], getTwist
    # p.angles["twist"] (degrees), getAimVector(v) sets v's x and y to p.aim["vec"] and returns v (the jar's
    # getAimVector(Vector2) fills the vector it is given; (1, 0) by default, a zero vector when a test sets (0, 0)).
    # The probe's writers record (name, value) into p.aim["calls"] beside setForceAim and nullifyAiming:
    # setTargetAndCurrentDirection(x, y) (the value (x, y); it also sets fwd, body and look to atan2(y, x), the snap),
    # setBlockMovement, setIsAiming (it also sets p.aim["aiming"], which isAiming answers), setIgnoreAimingInput and
    # setTurnDelta (it also sets p.aim["turn"], which getTurnDelta answers, 1.0 at first); faceLocationF(x, y) appends
    # (x, y) to p.faced
    angles.update(fwd=0.0, twist=0.0)
    aim.update(vec=(1.0, 0.0), turn=1.0)
    p.getDirectionAngleRadians, p.getTwist = (lambda s: angles["fwd"]), (lambda s: angles["twist"])

    def get_aim_vector(s, v):
        v.x, v.y = aim["vec"]
        return v
    p.getAimVector = get_aim_vector

    def ring_setter(name, key=None):
        def f(s, *v):
            aim["calls"].append((name, v[0] if len(v) == 1 else tuple(v)))
            if key is not None:
                aim[key] = v[0]
        return f

    def snap(s, fx, fy):
        aim["calls"].append(("setTargetAndCurrentDirection", (fx, fy)))
        a = math.atan2(fy, fx)
        angles.update(fwd=a, body=a, look=a)
    p.setTargetAndCurrentDirection = snap
    p.setBlockMovement, p.setIsAiming = ring_setter("setBlockMovement"), ring_setter("setIsAiming", "aiming")
    p.setIgnoreAimingInput, p.setTurnDelta = ring_setter("setIgnoreAimingInput"), ring_setter("setTurnDelta", "turn")
    p.getTurnDelta = lambda s: aim["turn"]
    p.faceLocationF = lambda s, fx, fy: faced.append((fx, fy)) or True   # PZA/1.11: a point faced, into p.faced
    return p


def make_vector2(x, y):
    """A Vector2 as the Lua reads it: x and y fields, getLength and getDirection (atan2(y, x), the jar's
    Vector2.getDirection) read live, so a getAimVector that refills it is read afresh (PZA/1.11)."""
    return J(_cls="Vector2", x=x, y=y, getLength=lambda s: math.hypot(s.x, s.y),
             getDirection=lambda s: math.atan2(s.y, s.x))


def make_zombie(zid, x, y, dead=False, health=1.0):
    return J(getOnlineID=lambda s: zid, getX=lambda s: x, getY=lambda s: y, isDead=lambda s: dead,
             getTarget=lambda s: None, isCrawling=lambda s: False, getHealth=lambda s: health,
             isOnFloor=lambda s: False,                                       # PZA/1.7: a standing zombie
             isTargetLocationKnown=lambda s: False, getRealState=lambda s: "idle",   # PZA/1.9: an unaware one
             getAnimAngleRadians=lambda s: 0.0, isFallOnFront=lambda s: False)       # PZA/1.10: facing +x


def make_cell(zombies=(), squares=None):
    zl = J(size=lambda s: len(zombies), get=lambda s, i: zombies[i])
    sq = squares or {}
    return J(getZombieList=lambda s: zl, getGridSquare=lambda s, x, y, z: sq.get((int(x), int(y), int(z))),
             getChunkMap=lambda s, i: J(getWidthInTiles=lambda s2: 104))      # PZA/1.7: the 1280 x 720 grid


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
    q.hasActionType = lambda p, t: any(getattr(a, "Type", None) == t for a in q.queue)
    q.getTimedActionQueue = lambda p=None: J(queue=q.queue)
    q.hasAction = lambda a: any(x is a for x in q.queue)      # PZA/1.5.1: vanilla's hasAction(action), the climb's
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
    g.Perks = J(Sneak="Sneak", Strength="Strength")      # PZA/1.9: me.sneakLevel's getPerkLevel(Perks.Sneak); Plan
                                                         # 31 Task 15a: the melee's knock_p reads Perks.Strength
    g.IsoFlagType = J(HoppableN="HoppableN", HoppableW="HoppableW",   # PZA/1.4: the square's has(flag) reads
                      TallHoppableN="TallHoppableN", TallHoppableW="TallHoppableW")
    g.IsoDirections = J(N="N", S="S", E="E", W="W")                  # PZA/1.5: the climb's facing
    g.FluidCategory = J(Beverage="Beverage", Hazardous="Hazardous", Alcoholic="Alcoholic")   # PZA/1.5: W.drinkable
    g.Fluid = J(Water="Water")                                       # PZA/1.4.1: canAddFluid(Fluid.Water)
    g.instanceof = lambda o, cls: getattr(o, "_cls", None) == cls
    g.getGameTime = lambda: J(getHour=lambda s: 7, getMinutes=lambda s: 30, getWorldAgeHours=lambda s: 31.5,
                                getTimeOfDay=lambda s: 8.0)
    q = make_queue()
    g._queue = q
    g.ISTimedActionQueue = J(add=lambda a: q.add(a), getTimedActionQueue=lambda p: q.getTimedActionQueue(p),
                             isPlayerDoingAction=lambda p: q.isPlayerDoingAction(p), clear=lambda p: q.clear(p),
                             hasActionType=lambda p, t: q.hasActionType(p, t), hasAction=lambda a: q.hasAction(a))
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
    # PZA/1.3 (P23-AO): OnPlayerDeath keeps its handlers in g._deathHandlers
    death_handlers = []
    g._deathHandlers = death_handlers
    g.Events = J(OnTick=J(Add=lambda f: handlers.append(f)), OnPlayerUpdate=J(Add=lambda f: upd_handlers.append(f)),
                 OnPlayerGetDamage=J(Add=lambda f: damage_handlers.append(f)),
                 OnPlayerDeath=J(Add=lambda f: death_handlers.append(f)))
    g.Vector2 = J(new=lambda x, y: make_vector2(x, y))
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
    # PZA/1.5: ISClimbOverFence:new(character, item, direction) records into g._climbs
    climbs = []
    g._climbs = climbs
    g.ISClimbOverFence = J(new=lambda cls, p, fence, d: climbs.append((p, fence, d)) or J(
        Type="ISClimbOverFence", character=p, item=fence, direction=d))
    # PZA/1.5's care skills: ISApplyBandage:new(character, otherPlayer, item, bodyPart, doIt) records into
    # g._bandages; ISWashClothing:new(character, sink, item, blood, dirt, noSoap) into g._washes;
    # ISInventoryPaneContextMenu.OnNewCraft(item, recipe, playerNum, all) into g._crafts, queueing an ISHandcraftAction
    # while g._craft["queue"] (vanilla's canPerformCurrentRecipe passed); getScriptManager():getCraftRecipe(name) answers
    # a recipe J whose name is name; ItemTag carries the three rip tags
    bandages, washes, crafts, craft = [], [], [], {"queue": True}
    g._bandages, g._washes, g._crafts, g._craft = bandages, washes, crafts, craft
    g.ISApplyBandage = J(new=lambda cls, p, other, item, part, doit: bandages.append((p, other, item, part, doit)) or J(
        Type="ISApplyBandage", item=item, part=part, doIt=doit))
    g.ISWashClothing = J(new=lambda cls, p, src, item, blood, dirt, nosoap: washes.append(
        (p, src, item, blood, dirt, nosoap)) or J(Type="ISWashClothing", item=item))

    def on_new_craft(item, recipe, num, all_):
        crafts.append((item, recipe, num, all_))
        if craft["queue"]:
            q.add(J(Type="ISHandcraftAction", item=item))
    g.ISInventoryPaneContextMenu = J(OnNewCraft=on_new_craft)
    # PZA/1.5's fill: ISTakeWaterAction:new(character, item, waterObject, waterTaintedCL) records into g._takes
    takes = []
    g._takes = takes
    g.ISTakeWaterAction = J(new=lambda cls, p, item, src, tainted: takes.append((p, item, src, tainted)) or J(
        Type="ISTakeWaterAction", item=item))
    g.getScriptManager = lambda: J(getCraftRecipe=lambda s, n: J(name=n))
    # PZA/1.6's wear: ISWearClothing:new(character, item, time) records into g._wears
    wears = []
    g._wears = wears
    g.ISWearClothing = J(new=lambda cls, p, item, t=None: wears.append((p, item, t)) or J(
        Type="ISWearClothing", item=item))
    # PZA/1.6's window: ISClimbThroughWindow:new(character, item, time) and ISSmashWindow:new(character, window)
    # record into g._windows as ("climb", p, item, time) and ("smash", p, window)
    windows = []
    g._windows = windows
    g.ISClimbThroughWindow = J(new=lambda cls, p, item, t=None: windows.append(("climb", p, item, t)) or J(
        Type="ISClimbThroughWindow", item=item))
    g.ISSmashWindow = J(new=lambda cls, p, w, part=None: windows.append(("smash", p, w)) or J(
        Type="ISSmashWindow", window=w))
    # PZA/1.7: the arm parts' BodyPartType constants (names stand for the enum values)
    g.BodyPartType = J(Hand_L="Hand_L", Hand_R="Hand_R", ForeArm_L="ForeArm_L", ForeArm_R="ForeArm_R",
                       UpperArm_L="UpperArm_L", UpperArm_R="UpperArm_R")
    g.ItemTag = J(RIP_CLOTHING_COTTON="RIP_CLOTHING_COTTON", RIP_CLOTHING_DENIM="RIP_CLOTHING_DENIM",
                  RIP_CLOTHING_LEATHER="RIP_CLOTHING_LEATHER")
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


# ---- the melee reflex's kinematic fake (PZA/1.8, Plan 28 Task 7a; the architecture review's section 4.1) -------------
WALK_SPEED = 2.0          # tiles a second: the walk (#4197), the player's auto-walk speed in the fake
TICK_MS = 17              # one client tick on the fake clock (about 60 Hz)
ZOMBIE_STOP_R = 0.45      # tiles: a chasing zombie stops closing here (the fake keeps the two bodies apart)
TURN_RATE = 3.6           # radians a second: the body's turn toward the written facing walking (#4689: 206 degrees)
BAT_MIN_R = 0.61          # tiles: the bat's MinRange (weapon.txt:6703), the fake bat's getMinRange


def zdist(w):
    """The planar distance from the player to the zombie in the world w."""
    return math.hypot(w["zx"] - w["px"], w["zy"] - w["py"])


def make_mover(px=10.0, py=20.0, zx=12.0, zy=20.0, zid=7, zspeed=0.0, chasing=True, weapon="bat", attack_ticks=20,
               windup_ticks=None, hit_ticks=30, bite_r=0.9, dist_member=True, look=None, turn=TURN_RATE,
               combat_speed=1.0, zangle=0.0, front=False, snap=True):
    """A player and one zombie whose positions and states live in the dict w, moved by step_world once a client tick
    (before the OnTick that runs the runner, as the engine's update precedes OnTick): the zombie closes on the player at
    w["zspeed"] tiles a second while w["chasing"] (its getTarget answers the player then, None otherwise) and it neither
    lies nor is knocked down, stopping at ZOMBIE_STOP_R; the player moves along its auto-walk at WALK_SPEED, the
    direction read back from setAutoWalkDirection's input-space vector through the inverse of K.inputVector
    (updateMovementFromInput's x = iy + ix, y = iy - ix, normalised). DoAttack records {tick, shove (the setDoShove
    flag then), d, aiming (the force-aim then)} into w["presses"] (and p.attacks), starts an attack that reads
    isAttackStarted true for w["attack_ticks"] ticks, and calls w["on_attack"](w, shove) when set (a test's knockdown or
    health fall; none by default: a miss). A scripted zombie attack: with w["windup"] a tick count, a chasing standing
    zombie within w["bite_r"] (#4290's 0.9) for that many ticks in a row sets the player's hit reaction ("Bite") for
    w["hit_ticks"] ticks, counted in w["bites"]. The zombie's isDead, getHealth, isOnFloor and isKnockedDown answer
    w["zdead"], w["zhp"], w["floor"] and w["knocked"], which a test toggles. dist_member gives the player the engine's
    DistToProper (the planar distance, T91.3); False leaves it absent (the four position reads).
    PZA/1.10 (Plan 31 Task 2): the look. faceThisObject(o) and faceLocationF(x, y) write the facing (w["face_to"], the
    bearing from the player to o or to (x, y), atan2's convention), and step_world turns w["look"] toward it at
    w["turn"] radians a second (#4689's 206 degrees walking by default; 0 never turns), so the face written on a tick
    is read by getLookAngleRadians (and getAnimAngleRadians) on the next, as the engine's update follows OnTick
    (#4590); w["look"] starts on the zombie unless look is given. getCombatSpeed answers w["cs"]; the bat answers
    getMinRange BAT_MIN_R; the zombie's getAnimAngleRadians and isFallOnFront answer w["zangle"] and w["front"].
    PZA/1.11 (Plan 32 Task 4): setTargetAndCurrentDirection(x, y), the snap, sets the look and the written facing at
    once; with snap False (w["snap"]) it writes the facing only and the look turns toward it at w["turn"] as after a
    faceThisObject (an engine whose snap the test holds back: the look held off with turn 0)."""
    w = {"px": px, "py": py, "zx": zx, "zy": zy, "zspeed": zspeed, "chasing": chasing, "zdead": False, "zhp": 1.0,
         "knocked": False, "floor": False, "attack": 0, "attack_ticks": attack_ticks, "windup": windup_ticks,
         "wound": 0, "hit": 0, "hit_ticks": hit_ticks, "bite_r": bite_r, "bites": 0, "on_attack": None,
         "presses": [], "tick": 0, "shove": False, "walk": None,
         "look": math.atan2(zy - py, zx - px) if look is None else look, "face_to": None, "turn": turn,
         "cs": combat_speed, "zangle": zangle, "front": front, "snap": snap}
    p = make_player(weapon=make_weapon(min_range=BAT_MIN_R) if weapon == "bat" else weapon)
    p.getX, p.getY = (lambda s: w["px"]), (lambda s: w["py"])
    if dist_member:
        p.DistToProper = lambda s, o: math.hypot(o.getX(o) - w["px"], o.getY(o) - w["py"])

    def do_attack(s, f):
        p.attacks.append(f)
        w["presses"].append({"tick": w["tick"], "shove": w["shove"], "d": zdist(w), "aiming": p.aim["force"]})
        w["attack"] = w["attack_ticks"]
        if w["on_attack"] is not None:
            w["on_attack"](w, w["shove"])
        return True

    def set_shove(s, v):
        w["shove"] = v
        p.sets.append(("setDoShove", v))

    def set_dir(s, v):
        p.sets.append(("setAutoWalkDirection", v))
        wx, wy = v.y + v.x, v.y - v.x
        n = math.hypot(wx, wy)
        w["walk"] = (wx / n, wy / n) if n > 0 else None
    p.DoAttack, p.setDoShove, p.setAutoWalkDirection = do_attack, set_shove, set_dir
    p.isAttackStarted = lambda s: w["attack"] > 0

    def face_obj(s, o):
        p.faced.append(o)
        w["face_to"] = math.atan2(o.getY(o) - w["py"], o.getX(o) - w["px"])

    def face_at(s, x, y):
        p.faced.append((x, y))
        w["face_to"] = math.atan2(y - w["py"], x - w["px"])
        return True
    p.faceThisObject, p.faceLocationF = face_obj, face_at
    p.getLookAngleRadians = p.getAnimAngleRadians = lambda s: w["look"]
    # PZA/1.11: the forward direction is the facing last written (w["face_to"]), else the look; the snap
    # (setTargetAndCurrentDirection) sets the look and the written facing at once
    p.getDirectionAngleRadians = lambda s: w["face_to"] if w["face_to"] is not None else w["look"]

    def snap_to(s, fx, fy):
        p.aim["calls"].append(("setTargetAndCurrentDirection", (fx, fy)))
        w["face_to"] = math.atan2(fy, fx)
        if w["snap"]:
            w["look"] = w["face_to"]
    p.setTargetAndCurrentDirection = snap_to
    p.getCombatSpeed = lambda s: w["cs"]
    z = J(getOnlineID=lambda s: zid, getX=lambda s: w["zx"], getY=lambda s: w["zy"], isDead=lambda s: w["zdead"],
          getTarget=lambda s: p if w["chasing"] else None, isCrawling=lambda s: False, getHealth=lambda s: w["zhp"],
          isOnFloor=lambda s: w["floor"], isKnockedDown=lambda s: w["knocked"],
          isTargetLocationKnown=lambda s: w["chasing"], getRealState=lambda s: "idle",   # PZA/1.9
          getAnimAngleRadians=lambda s: w["zangle"], isFallOnFront=lambda s: w["front"])   # PZA/1.10
    return p, z, w


def step_world(w, p):
    """One client tick of the fake engine (make_mover's): the attack and the hit reaction count down, the player walks
    its auto-walk, the zombie closes, and the zombie's scripted attack winds up."""
    w["tick"] += 1
    dt = TICK_MS / 1000.0
    if w["face_to"] is not None and w["turn"] > 0:   # PZA/1.10: the body turns toward the written facing
        off = (w["face_to"] - w["look"] + math.pi) % (2 * math.pi) - math.pi
        stepr = w["turn"] * dt
        w["look"] += off if abs(off) <= stepr else math.copysign(stepr, off)
    if w["attack"] > 0:
        w["attack"] -= 1
    if w["hit"] > 0:
        w["hit"] -= 1
        if w["hit"] == 0:
            p.combat["hitReaction"] = ""
    if p.motor["autoWalk"] and w["walk"] is not None:
        w["px"] += w["walk"][0] * WALK_SPEED * dt
        w["py"] += w["walk"][1] * WALK_SPEED * dt
    d = zdist(w)
    standing = not w["floor"] and not w["knocked"] and not w["zdead"]
    if w["chasing"] and standing and d > ZOMBIE_STOP_R and w["zspeed"] > 0:
        step = min(w["zspeed"] * dt, d - ZOMBIE_STOP_R)
        w["zx"] += (w["px"] - w["zx"]) / d * step
        w["zy"] += (w["py"] - w["zy"]) / d * step
    if w["windup"] is not None and w["chasing"] and standing and w["hit"] == 0 and zdist(w) < w["bite_r"]:
        w["wound"] += 1
        if w["wound"] >= w["windup"]:
            p.combat["hitReaction"] = "Bite"
            w["hit"], w["wound"] = w["hit_ticks"], 0
            w["bites"] += 1
    else:
        w["wound"] = 0
