"""Plan 16 Task 6 (spec section 4.1): the server refuses an eat at Overfull 4 (NR_Server_IntakeGuard.lua).

The guard wraps ISEatFoodAction.serverStart (which vanilla does not define), complete and serverStop, never `new`.
At Overfull 4, in Mode 1, for a food whose hunger change is below 0, serverStart marks the action refused, calls
netAction:forceComplete() and sends the player Tooltip_CantEatMore as halo text; complete then answers false (the
Reject) and serverStop eats nothing, so nothing below either runs: no Eat, no intake capture. Below Overfull 4, for any
other item, on the client and on a raising check, every wrapper calls its original unchanged.

Each host here is the shared server host (server_host.Host: NR_Core, the shared files, then every server/ file in the
engine's sorted order) with a stand-in of vanilla's ISEatFoodAction laid BEFORE the files load, so the intake and the
guard wrap it at file load in their real order. The server's flow is driven by hand as the 42.21 jar runs it
(NetTimedAction.start calls serverStart, ActionManager.update's perform calls complete, ActionManager.remove's stop
calls serverStop). The stand-ins prove the Lua shape only; the live refusal is the plan's live session.
"""
import os

import lupa.lua51 as lua51

from .server_host import Host, LUA, SERVER, SHARED, _load, _shared_files

GUARD = os.path.join(SERVER, "NR_Server_IntakeGuard.lua")
INTAKE = os.path.join(SERVER, "NR_Server_Intake.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")

# vanilla's class, as shared/TimedActions/ISEatFoodAction.lua builds it (the parts the server runs): complete eats the
# action's percentage; serverStop eats by the netAction's progress (vanilla's ISEatFoodAction:serverStop); no
# serverStart. The character's Eat consumes the item's hunger (the share eaten) and is counted per call. Every Java
# member the guard or the intake calls on the character and the item counts in NR_E.java.
VANILLA = r"""
NR_E = { eats = 0, halo = {}, java = {}, vanillaComplete = 0, vanillaStop = 0, otherStart = 0 }
local function jcount(name) NR_E.java[name] = (NR_E.java[name] or 0) + 1 end
NR_E.jcount = jcount
ISEatFoodAction = {}
ISEatFoodAction.__index = ISEatFoodAction
function ISEatFoodAction:new(character, item, percentage)
    local o = setmetatable({}, self)
    o.character = character
    o.item = item
    o.percentage = percentage or 1
    return o
end
function ISEatFoodAction:complete()
    NR_E.vanillaComplete = NR_E.vanillaComplete + 1
    self.character:Eat(self.item, self.percentage)
    return true
end
function ISEatFoodAction:serverStop()
    NR_E.vanillaStop = NR_E.vanillaStop + 1
    local p = self.netAction and self.netAction:getProgress() or 0
    self.character:Eat(self.item, self.percentage * p)
end
ISEatFoodAction_vanillaNew = ISEatFoodAction.new
ISDrinkFluidAction = {}
ISDrinkFluidAction.__index = ISDrinkFluidAction
NR_E.drinkVanilla = function(self, delta) NR_E.drunk = (NR_E.drunk or 0) + 1; self.fc.amount = 0; return "orig" end
ISDrinkFluidAction.updateEat = NR_E.drinkVanilla
HaloTextHelper = { addBadText = function(p, t)
    if NR_E.haloRaises then error("stub: halo raised") end
    NR_E.halo[#NR_E.halo + 1] = t
end }
getText = function(k)
    if k == "Tooltip_CantEatMore" then return "Too full to eat more." end
    return k
end
function NR_E.char(name)
    local c = {}
    c.getUsername = function(s) jcount("getUsername"); return name end
    c.Eat = function(s, item, pct)
        NR_E.eats = NR_E.eats + 1
        item.hung = item.hung * (1 - pct)
    end
    return c
end
function NR_E.food(fullType, hung)
    local item = { hung = hung, base = hung }
    item.getHungChange = function(s) jcount("getHungChange"); return s.hung end
    item.getFullType = function(s) return fullType end
    item.getBaseHunger = function(s) return s.base end
    item.getCalories = function(s) return 95 end
    item.getCarbohydrates = function(s) return 25.13 end
    item.getLipids = function(s) return 0.31 end
    item.getProteins = function(s) return 0.47 end
    item.isCooked = function(s) return false end
    item.isBurnt = function(s) return false end
    item.isRotten = function(s) return false end
    item.isFrozen = function(s) return false end
    item.getThirstChangeUnmodified = function(s) return 0 end
    item.haveExtraItems = function(s) return false end
    item.getModData = function(s) return {} end
    item.getScriptItem = function(s)
        return { getHungerChange = function(x) return hung * 100 end, getThirstChange = function(x) return 0 end }
    end
    return item
end
function NR_E.net()
    local n = { forced = false }
    n.forceComplete = function(s) s.forced = true end
    n.getProgress = function(s) if s.forced then return 1 end return 0.5 end
    return n
end
-- the server's run of one eat: NetTimedAction.start (serverStart through the class), then perform (complete) or a stop
function NR_E.run(action, cancel)
    action.serverStart(action)
    if cancel then
        action.serverStop(action)
        return nil
    end
    return action.complete(action)
end
"""

# another mod's serverStart, laid before the files load: the guard chains it
OTHER_START = r"""
function ISEatFoodAction:serverStart()
    NR_E.otherStart = NR_E.otherStart + 1
end
"""


def host(extra=""):
    return Host(extra_env=VANILLA + extra)


def G(h):
    return h.NR.server.eatGuard


def same(h, a, b):
    return h.rt.eval("rawequal")(a, b)


def fill(h, name, grams):
    """The player's record, in memory, with grams of water in the stomach's buffer (Overfull 4 from 1100 g)."""
    rec = h.NR.server.store.get(name, h.T.age, None)
    st = h.K.stomach.new()
    st.buffer.water = grams
    rec.stomach = st
    return rec


def action(h, name="admin", fullType="Base.Apple", hung=-0.16, net=True):
    E = h.G.NR_E
    a = h.G.ISEatFoodAction.new(h.G.ISEatFoodAction, E.char(name), E.food(fullType, hung), 1)
    if net:
        a.netAction = E.net()
    return a


def mass(h, rec):
    return h.K.stomach.mass(rec.stomach)


# --- at Overfull 4 the eat is refused and nothing is consumed ----------------------------------------------------------

def test_at_overfull_4_the_eat_is_refused_and_the_item_is_unchanged():
    h = host()
    rec = fill(h, "admin", 1100)
    m0 = mass(h, rec)
    eats0 = h.NR.server.intake.stats.eats
    a = action(h)
    r = h.G.NR_E.run(a)
    assert r is False                                         # complete answers false: the Reject
    assert a.item.hung == -0.16                               # the item's hunger (its uses) untouched
    assert h.G.NR_E.eats == 0 and h.G.NR_E.vanillaComplete == 0
    assert a.nrRefused is True and a.netAction.forced is True
    assert list(h.G.NR_E.halo.values()) == ["Too full to eat more."]
    assert h.NR.server.intake.stats.eats == eats0             # the intake's capture never ran
    assert mass(h, rec) == m0
    st = G(h).stats
    assert st.checks == 1 and st.refused == 1 and st.held == 1 and st.failures == 0


def test_a_refused_eat_that_is_cancelled_consumes_nothing():
    # after the forceComplete the progress reads 1, so vanilla's serverStop would eat the WHOLE item: it never runs
    h = host()
    fill(h, "admin", 1300)
    a = action(h)
    h.G.NR_E.run(a, True)
    assert a.item.hung == -0.16 and h.G.NR_E.eats == 0 and h.G.NR_E.vanillaStop == 0
    assert G(h).stats.stopped == 1


def test_without_a_net_action_the_eat_is_still_refused_at_its_end():
    h = host()
    fill(h, "admin", 1100)
    a = action(h, net=False)
    assert h.G.NR_E.run(a) is False
    assert a.item.hung == -0.16 and h.G.NR_E.eats == 0
    assert G(h).stats.unforced == 1 and G(h).stats.failures == 0


def test_a_raising_halo_never_lets_the_eat_through():
    h = host()
    fill(h, "admin", 1100)
    h.G.NR_E.haloRaises = True
    a = action(h)
    assert h.G.NR_E.run(a) is False
    assert a.item.hung == -0.16 and a.netAction.forced is True
    assert G(h).stats.haloMissing == 1


def test_an_unresolved_key_shows_vanillas_english_text():
    h = host()
    h.rt.execute("getText = function(k) return k end")      # a server that resolves no Tooltip_ key
    assert G(h).text() == "Too full to eat more."
    h.rt.execute("getText = nil")
    assert G(h).text() == "Too full to eat more."


# --- below Overfull 4, and for every other case, the original runs unchanged ------------------------------------------

def test_below_overfull_4_the_original_runs_and_the_eat_lands():
    h = host()
    rec = fill(h, "admin", 1000)                              # Overfull 3
    assert h.K.view.overfullOf(rec) == 3
    eats0, landed0 = h.NR.server.intake.stats.eats, h.NR.server.intake.stats.landed
    a = action(h)
    assert h.G.NR_E.run(a) is True
    assert h.G.NR_E.eats == 1 and h.G.NR_E.vanillaComplete == 1 and a.item.hung == 0
    assert a.nrRefused is None and a.netAction.forced is False and len(h.G.NR_E.halo) == 0
    assert h.NR.server.intake.stats.eats == eats0 + 1 and h.NR.server.intake.stats.landed == landed0 + 1
    assert G(h).stats.refused == 0 and G(h).stats.held == 0


def test_below_overfull_4_a_cancel_runs_vanillas_stop():
    h = host()
    fill(h, "admin", 900)
    a = action(h)
    h.G.NR_E.run(a, True)
    assert h.G.NR_E.vanillaStop == 1 and abs(a.item.hung - (-0.08)) < 1e-9   # half eaten at progress 0.5
    assert G(h).stats.stopped == 0


def test_a_record_not_in_memory_refuses_nothing():
    h = host()
    a = action(h, name="stranger")
    assert h.G.NR_E.run(a) is True and h.G.NR_E.eats == 1
    assert h.NR.server.store.records["stranger"] is not None   # the intake's capture laid it, never the guard


def test_a_food_with_no_hunger_change_is_never_refused():
    # a cigarette or a tea with no food value: vanilla's menu offers it at FOOD_EATEN 3 (ISInventoryPaneContextMenu
    # .lua:468 counts getHungChange() < 0 only), so the guard lets it through
    h = host()
    fill(h, "admin", 1300)
    a = action(h, fullType="Base.Cigarettes", hung=0)
    assert h.G.NR_E.run(a) is True and h.G.NR_E.vanillaComplete == 1
    assert G(h).stats.refused == 0


def test_overlay_mode_refuses_nothing():
    h = host()
    fill(h, "admin", 1300)
    h.NR.server.writer.mode = 2
    a = action(h)
    assert h.G.NR_E.run(a) is True and h.G.NR_E.eats == 1
    assert G(h).stats.refused == 0


def test_the_client_passes_through():
    # serverStart runs only on the server; were it called on the client the wrapper would refuse nothing
    h = host()
    fill(h, "admin", 1300)
    h.T.server = False
    a = action(h)
    a.serverStart(a)
    assert a.nrRefused is None and G(h).stats.passthrough == 1 and G(h).stats.checks == 0


def test_another_mods_server_start_runs_below_4_and_not_on_a_refusal():
    h = host(OTHER_START)
    fill(h, "admin", 900)
    h.G.NR_E.run(action(h))
    assert h.G.NR_E.otherStart == 1
    fill(h, "admin", 1100)
    h.G.NR_E.run(action(h))
    assert h.G.NR_E.otherStart == 1                           # refused: the stated exception, the chain stops here


# --- the rim guard: a raising check never breaks eating ---------------------------------------------------------------

def test_a_raising_check_runs_the_original_and_is_counted():
    h = host()
    fill(h, "admin", 1300)
    h.rt.execute("NutritionRevamp.server.eatGuard.refuses = function() error('boom') end")
    a = action(h)
    assert h.G.NR_E.run(a) is True and h.G.NR_E.eats == 1
    assert G(h).stats.failures == 1 and "boom" in G(h).lastError
    assert a.nrRefused is None


def test_a_raising_record_read_runs_the_original():
    h = host()
    rec = fill(h, "admin", 1300)
    rec.stomach = h.rt.eval("setmetatable({}, { __index = function() error('bad stomach') end })")
    a = action(h)
    assert h.G.NR_E.run(a) is True and h.G.NR_E.vanillaComplete == 1
    assert G(h).stats.failures == 1


def test_a_broken_action_never_blocks_the_original():
    h = host()
    a = h.G.ISEatFoodAction.new(h.G.ISEatFoodAction, h.G.NR_E.char("admin"), h.G.NR_E.food("Base.Apple", -0.16), 1)
    a.character = None
    a.serverStart(a)
    assert G(h).stats.refused == 0 and G(h).stats.failures == 0


# --- drinks are untouched --------------------------------------------------------------------------------------------

DRINK = r"""
function()
    local fluid = { getFluidTypeString = function(self) return "Water" end }
    local sample = {
        size = function(self) return 1 end,
        getFluid = function(self, i) return fluid end,
        getPercentage = function(self, i) return 1.0 end,
        release = function(self) end,
    }
    local fc = { amount = 0.3 }
    fc.getAmount = function(self) return self.amount end
    fc.createFluidSample = function(self) return sample end
    local item = { getFullType = function(self) return "Base.WaterBottle" end }
    local a = { item = item, fluidContainer = fc, fc = fc, character = NR_E.char("admin") }
    return ISDrinkFluidAction.updateEat(a, 1)
end
"""


def test_a_drink_at_overfull_4_still_lands():
    h = host()
    rec = fill(h, "admin", 1300)
    liquid0 = rec.stomach.liquid
    sips0 = h.NR.server.intake.stats.sips
    assert h.rt.eval(DRINK)() == "orig" and h.G.NR_E.drunk == 1
    assert h.NR.server.intake.stats.sips == sips0 + 1
    assert rec.stomach.liquid > liquid0                       # the water reached the liquid lane
    assert G(h).stats.checks == 0
    # the guard wraps nothing on the drink: the drink's chain is the intake's wrapper over vanilla's
    assert same(h, h.G.ISDrinkFluidAction.updateEat, h.G.NR_IntakeDrink_Installed.wrapper)
    assert same(h, h.G.NR_IntakeDrink_Installed.orig, h.G.NR_E.drinkVanilla)


# --- the install: outside the intake, never `new`, idempotent across a reload -----------------------------------------

def test_the_guard_wraps_outside_the_intakes_capture():
    h = host()
    cls = h.G.ISEatFoodAction
    assert G(h).wrappedStart is True and G(h).wrappedComplete is True and G(h).wrappedStop is True
    assert G(h).outer is True
    assert same(h, cls.complete, h.G.NR_EatGuardComplete_Installed.wrapper)
    assert same(h, h.G.NR_EatGuardComplete_Installed.orig, h.G.NR_IntakeComplete_Installed.wrapper)
    assert same(h, cls.serverStop, h.G.NR_EatGuardStop_Installed.wrapper)
    assert same(h, h.G.NR_EatGuardStop_Installed.orig, h.G.NR_IntakeServerStop_Installed.wrapper)
    assert h.G.NR_EatGuardStart_Installed.orig is None        # vanilla defines no serverStart


def test_the_file_order_puts_the_guard_after_the_intake():
    # LuaManager.LoadDirBase sorts a mod's files case-insensitively (#0850): the guard's name is load-bearing
    names = sorted((n for n in os.listdir(SERVER) if n.endswith(".lua")), key=str.lower)
    assert names.index("NR_Server_IntakeGuard.lua") == names.index("NR_Server_Intake.lua") + 1


def test_new_is_never_wrapped():
    h = host()
    assert same(h, h.G.ISEatFoodAction.new, h.G.ISEatFoodAction_vanillaNew)
    with open(GUARD, encoding="utf-8") as fh:
        code = "\n".join(l.split("--", 1)[0] for l in fh.read().splitlines())
    assert '"new"' not in code and ".new =" not in code and "ISEatFoodAction.new" not in code


def test_the_install_is_idempotent_across_a_reload():
    h = host()
    cls = h.G.ISEatFoodAction
    w = (cls.serverStart, cls.complete, cls.serverStop)
    G(h).install()
    h.fire("OnServerStarted")
    # a reloadlua of the two files, then a whole reload (NR_Core re-creates NutritionRevamp, #0943)
    _load(h.rt, INTAKE)
    _load(h.rt, GUARD)
    h.fire("OnServerStarted")
    for p in _shared_files():
        _load(h.rt, p)
    for p in sorted(n for n in os.listdir(SERVER) if n.startswith("NR_Server_") and n.endswith(".lua")):
        _load(h.rt, os.path.join(SERVER, p))
    h.NR = h.G.NutritionRevamp
    h.NR.server.store.records = h.rt.table()
    h.fire("OnServerStarted")
    assert all(same(h, a, b) for a, b in zip(w, (cls.serverStart, cls.complete, cls.serverStop)))
    assert same(h, cls.new, h.G.ISEatFoodAction_vanillaNew)
    a = action(h, name="fresh")
    assert h.G.NR_E.run(a) is True
    assert h.G.NR_E.vanillaComplete == 1 and h.G.NR_E.eats == 1   # one original call: no wrapper wraps a wrapper
    assert h.NR.server.eatGuard.outer is True


def test_without_the_class_the_install_wraps_nothing():
    h = Host()
    assert h.G.ISEatFoodAction is None
    assert G(h).install() is False and G(h).outer is False


def test_install_wrap_over_an_absent_method_installs_once():
    h = host()
    S = h.rt.table()
    cls = h.rt.table()
    make = h.rt.eval("function(S, kind) return function(self) return 'w' end end")
    assert h.NR.installWrap(S, cls, "serverStart", make, None, "t", True) is True
    w = cls.serverStart
    assert w is not None and S.orig is None
    assert h.NR.installWrap(S, cls, "serverStart", make, None, "t", True) is True
    assert same(h, cls.serverStart, w)
    assert h.NR.installWrap(h.rt.table(), h.rt.table(), "serverStart", make, None, "t") is False


# --- Rule 6: the eat start's Java calls --------------------------------------------------------------------------------

def test_an_eat_start_makes_one_java_call_below_4_and_two_at_4():
    h = host()
    fill(h, "admin", 1000)
    a = action(h)
    h.G.NR_E.java = h.rt.table()
    a.serverStart(a)
    assert dict(h.G.NR_E.java.items()) == {"getUsername": 1}
    fill(h, "admin", 1100)
    a = action(h)
    h.G.NR_E.java = h.rt.table()
    a.serverStart(a)
    assert dict(h.G.NR_E.java.items()) == {"getUsername": 1, "getHungChange": 1}
    assert a.netAction.forced is True                         # plus forceComplete, getText and the halo on a refusal


def test_the_limitations_name_the_refusals_bounds():
    h = host()
    text = " ".join(G(h).limitations.values())
    for phrase in ("Overfull 4", "Mode 1", "hunger change", "Overlay", "language", "queue",
                   "without calling the saved original"):
        assert phrase in text, phrase
