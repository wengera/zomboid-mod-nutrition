"""The sandbox re-resolve wired into both options readers (Plan 19 Task 2; ruling T1-1): the server's per-minute poll
(NR.server.readOptions) and the client's start (NR_Client_Options' OnGameStart closure) pass SandboxVars.NR to
K.dials.apply, so a dial whose row names an option follows it on both sides, and a patch on the field survives a poll
that read nothing new. The shipped registry names no option yet (W1), so each test lays one on a fresh host.
"""
import os

import lupa.lua51 as lua51

from . import server_host

OPT_ROW = r"""
NutritionRevamp.data.dials['monotony.SLOPE'].opt = 'MonotonyScaleTest'
NutritionRevamp.kernel.dials.OPT_IDS = NutritionRevamp.kernel.dials.optIds(NutritionRevamp.data.dials)
"""


def test_the_server_poll_writes_a_changed_option_into_the_kernel_field():
    h = server_host.Host()
    h.rt.execute(OPT_ROW)
    K, NR = h.K, h.NR
    NR.server.readOptions("poll")                               # no SandboxVars: the registry value stands
    assert K.monotony.SLOPE == 4.3
    h.rt.execute("SandboxVars = { NR = { MonotonyScaleTest = 6.0 } }")
    NR.server.readOptions("poll")
    assert K.monotony.SLOPE == 6.0 and NR.server.options.dialSeen["monotony.SLOPE"] == 6.0
    K.monotony.SLOPE = 1.25                                     # a replay or fit patch
    NR.server.readOptions("poll")
    assert K.monotony.SLOPE == 1.25                             # an unchanged read never rewrites it
    h.rt.execute("SandboxVars.NR.MonotonyScaleTest = 99")       # out of range: the double clamps to the row's max
    NR.server.readOptions("poll")
    assert K.monotony.SLOPE == 20


def test_the_shipped_poll_writes_nothing():
    h = server_host.Host()
    h.rt.execute("SandboxVars = { NR = { MonotonyScaleTest = 6.0 } }")
    h.NR.server.readOptions("poll")
    assert h.K.monotony.SLOPE == 4.3 and len(list(h.NR.server.options.dialSeen.items())) == 0


def test_the_client_start_applies_the_option():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(server_host.ENV + "\nisClient = function() return true end\nisServer = function() return false end\n")
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in server_host._shared_files():
        with open(path, encoding="utf-8") as fh:
            load(fh.read(), "@" + os.path.basename(path))()
    rt.execute(OPT_ROW)
    rt.execute("SandboxVars = { NR = { MonotonyScaleTest = 7.5 } }")
    with open(os.path.join(server_host.LUA, "client", "NR_Client_Options.lua"), encoding="utf-8") as fh:
        load(fh.read(), "@NR_Client_Options.lua")()
    g = rt.globals()
    for fn in g.NR_T.adds["OnGameStart"].values():
        fn()
    assert g.NutritionRevamp.kernel.monotony.SLOPE == 7.5
    assert g.NutritionRevamp.client.options.dialSeen["monotony.SLOPE"] == 7.5
