"""The Plan 19 Task 7 harness commands, offline: PZTestKit_Client.lua's Plan 19 Task 7 block (inv.ids, recipe.add,
item.rename), from its marker line to the end of the file, in a bare Lua 5.1 runtime with a stub TK, a player whose
inventory holds Lua stand-in items, a stub findEvolvedRecipe (the file's own is a local defined above the block), and
vanilla's ISAddItemInRecipe and ISTimedActionQueue as recorders. They pin each command's reply shape (an empty item
list is {} on the bus, a Lua empty table), its refusals and what it leaves behind: recipe.add queues vanilla's action
on exactly the menu's four arguments and only after the usability check; item.rename makes vanilla's three calls,
syncItemFields last. The first live session that uses them (x501) is their smoke test. The harness is never a kernel
file, so the coverage gate is untouched."""
import os

import lupa.lua51 as lua51

from .server_host import REPO

CLIENT = os.path.join(REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua", "client", "PZTestKit_Client.lua")
MARK = "-- ---- Plan 19 Task 7: the evolved-recipe add, the item rename and the inventory ids (client)"

ENV = r"""
T = { queued = {}, synced = 0, usable = true, newArgs = nil }
local function item(id, full, name)
    local it = { id = id, full = full, name = name, custom = false }
    function it.getID(s) return s.id end
    function it.getFullType(s) return s.full end
    function it.getName(s) return s.name end
    function it.isCustomName(s) return s.custom end
    function it.setName(s, v) s.name = v end
    function it.setCustomName(s, v) s.custom = v end
    function it.syncItemFields(s) T.synced = T.synced + 1; T.syncOrder = { s.name, s.custom } end
    return it
end
local function jlist(t)
    return { size = function(s) return #t end, get = function(s, i) return t[i + 1] end }
end
T.items = { item(11, "Base.Pan", "Pan"), item(12, "Base.Carrots", "Carrots"),
            item(13, "Base.PanFriedVegetables", "Stir Fry"), item(14, "Base.PanFriedVegetables", "Stir Fry") }
T.inv = {}
function T.inv.getFirstTypeRecurse(s, full)
    for i = 1, #T.items do if T.items[i].full == full then return T.items[i] end end
    return nil
end
function T.inv.getAllTypeRecurse(s, full)
    local out = {}
    for i = 1, #T.items do if T.items[i].full == full then out[#out + 1] = T.items[i] end end
    return jlist(out)
end
function T.inv.getItemById(s, id)
    for i = 1, #T.items do if T.items[i].id == id then return T.items[i] end end
    return nil
end
function T.inv.getItems(s) return jlist(T.items) end
T.player = { getInventory = function(s) return T.inv end }
getPlayer = function() return T.player end
T.recipe = { isItemUsableInRecipe = function(s, p, base, usedId)
    T.usableArgs = { p, base, usedId }
    return T.usable
end }
findEvolvedRecipe = function(name)
    if name == "Stir fry" then return T.recipe, nil end
    return nil, "no evolved recipe '" .. tostring(name) .. "'"
end
ISAddItemInRecipe = {}
function ISAddItemInRecipe.new(self, character, recipe, baseItem, usedItem)
    T.newArgs = { character, recipe, baseItem, usedItem }
    return { maxTime = 100, character = character, recipe = recipe, baseItem = baseItem, usedItem = usedItem }
end
ISTimedActionQueue = { add = function(a) T.queued[#T.queued + 1] = a end }
TK = { side = "client", commands = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
"""


def section():
    with open(CLIENT, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    return src[src.index(MARK):]


class Client:
    def __init__(self):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(ENV)
        self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(section(), "x50_block")()
        g = self.rt.globals()
        self.T, self.TK = g.T, g.TK


def client():
    c = Client()
    return c, c


def cmd(c, name, *args):
    return c.TK.commands[name](c.rt.table(*args))


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def test_the_block_registers_its_three_commands():
    _, g = client()
    for name in ("inv.ids", "recipe.add", "item.rename"):
        assert g.TK.commands[name] is not None


def test_inv_ids_lists_every_item_of_the_type_with_its_identity_row():
    _, g = client()
    r = cmd(g, "inv.ids", "Base.PanFriedVegetables")
    assert r.ok is True and r.side == "client" and r.n == 2
    rows = lst(r["items"])
    assert [x.id for x in rows] == [13, 14]
    assert rows[0].fullType == "Base.PanFriedVegetables" and rows[0].name == "Stir Fry" and rows[0].custom is False


def test_inv_ids_answers_an_empty_table_for_none_and_usage_without_a_type():
    _, g = client()
    r = cmd(g, "inv.ids", "Base.Butter")
    assert r.ok is True and r.n == 0 and len(r["items"]) == 0      # {} on the bus
    assert cmd(g, "inv.ids").startswith("usage:")


def test_recipe_add_queues_vanillas_action_on_the_menus_four_arguments():
    _, g = client()
    r = cmd(g, "recipe.add", "Stir fry", "Base.Pan", "Base.Carrots")
    assert r.ok is True and r.queued is True and r.usable is True and r.maxTime == 100
    assert r.base.id == 11 and r.used.id == 12
    assert len(g.T.queued) == 1
    a = g.T.newArgs
    assert g.rt.eval("T.newArgs[1] == T.player and T.newArgs[2] == T.recipe") is True
    assert a[3].id == 11 and a[4].id == 12
    assert g.T.usableArgs[3] == 12                                  # the usability check by the ingredient's id


def test_recipe_add_takes_a_base_by_id():
    _, g = client()
    r = cmd(g, "recipe.add", "Stir fry", "#14", "Base.Carrots")
    assert r.ok is True and r.base.id == 14 and g.T.newArgs[3].id == 14


def test_recipe_add_queues_nothing_the_menu_would_not_offer():
    _, g = client()
    g.T.usable = False
    r = cmd(g, "recipe.add", "Stir fry", "Base.Pan", "Base.Carrots")
    assert r.ok is False and r.queued is False and r.usable is False and "menu" in r.reason
    assert len(g.T.queued) == 0


def test_recipe_add_refuses_an_unknown_recipe_item_or_usage():
    _, g = client()
    assert cmd(g, "recipe.add", "Soup", "Base.Pan", "Base.Carrots").reason.startswith("no evolved recipe")
    assert cmd(g, "recipe.add", "Stir fry", "#99", "Base.Carrots").reason == "no item #99"
    assert cmd(g, "recipe.add", "Stir fry", "Base.Pan", "Base.Salt").reason == "no item Base.Salt"
    assert cmd(g, "recipe.add", "Stir fry", "Base.Pan").startswith("usage:")
    assert len(g.T.queued) == 0


def test_item_rename_makes_vanillas_three_calls_sync_last():
    _, g = client()
    r = cmd(g, "item.rename", "#13", "NRx50a")
    assert r.ok is True and r.synced is True and r.item == 13
    assert r.before.name == "Stir Fry" and r.before.custom is False
    assert r.after.name == "NRx50a" and r.after.custom is True
    assert g.T.synced == 1 and lst(g.T.syncOrder) == ["NRx50a", True]   # the sync sends the new name and flag


def test_item_rename_refuses_a_long_name_a_missing_item_and_usage():
    _, g = client()
    assert cmd(g, "item.rename", "#13", "x" * 29).ok is False
    assert cmd(g, "item.rename", "#77", "NRx50a").reason == "no item #77"
    assert cmd(g, "item.rename", "#13").startswith("usage:")
    assert g.T.synced == 0
