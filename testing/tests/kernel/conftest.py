"""The lupa host for the mod's pure kernel (spec § 4.10 tier 2).

Loads NR_Core.lua and every NR_Kernel*.lua under a Lua 5.1 runtime with a line hook that records
every executed (chunk, line). The executable-line set is debug.getinfo(f, "L").activelines over
the chunk function of each kernel file and every function reachable from NutritionRevamp.kernel;
test_zz_coverage.py asserts the two sets agree per file. A kernel function that is not a field of
the kernel table is invisible to that enumeration, which is why tools/hotpath_lint.py forbids one.
"""
import glob, os, pytest
import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
CORE = os.path.join(SHARED, "NR_Core.lua")


def kernel_files():
    return sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua")))


COLLECTOR = r"""
NR_COV = NR_COV or {}
debug.sethook(function(ev, line)
    local info = debug.getinfo(2, "S")
    if info == nil then return end
    local f = NR_COV[info.source]
    if f == nil then f = {}; NR_COV[info.source] = f end
    f[line] = true
end, "l")
"""

ACTIVE = r"""
-- active lines of every function reachable from the kernel table plus the given chunk functions
function NR_ACTIVE(chunks)
    local out = {}
    local function add(f)
        local info = debug.getinfo(f, "SL")
        if info == nil or info.activelines == nil then return end
        local t = out[info.source]
        if t == nil then t = {}; out[info.source] = t end
        for line in pairs(info.activelines) do t[line] = true end
    end
    for _, f in ipairs(chunks) do add(f) end
    local seen = {}
    local function walk(tbl)
        if seen[tbl] then return end
        seen[tbl] = true
        for _, v in pairs(tbl) do
            if type(v) == "function" then add(v) elseif type(v) == "table" then walk(v) end
        end
    end
    walk(NutritionRevamp.kernel)
    return out
end
"""


class LuaHost:
    def __init__(self):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(COLLECTOR)
        self.chunks = []
        for path in [CORE] + kernel_files():
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            chunk = self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))
            self.chunks.append(chunk)
            chunk()
        self.rt.execute(ACTIVE)
        self.G = self.rt.globals()
        self.K = self.G.NutritionRevamp.kernel

    def call(self, path, *args):
        fn = self.K
        for seg in path.split("."):
            fn = fn[seg]
        return fn(*args)

    def table(self, d):
        t = self.rt.table()
        for k, v in d.items():
            t[k] = self.table(v) if isinstance(v, dict) else v
        return t

    def py(self, t):
        if lua51.lua_type(t) != "table":
            return t
        return {k: self.py(v) for k, v in t.items()}

    def executed(self):
        return {src: set(lines.keys()) for src, lines in self.G.NR_COV.items()}

    def active(self):
        chunks = self.rt.table(*self.chunks)
        return {src: set(lines.keys()) for src, lines in self.G.NR_ACTIVE(chunks).items()}


@pytest.fixture(scope="session")
def host():
    return LuaHost()
