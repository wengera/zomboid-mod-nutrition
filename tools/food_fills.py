"""The tooltip's fill hours (Plan 15 Task 9; spec docs/superpowers/specs/2026-10-16-game-feel-design.md section 4,
decisions item 4: "replace vanilla's tooltip hunger line with a true one: about how long a food fills you, and its kcal").

    python tools/food_fills.py --check     exit 1 when the generated file differs from a fresh replay
    python tools/food_fills.py --write     regenerate it

The generated file is mod/NutritionRevamp/common/media/lua/shared/NR_Data_Fills.lua (NR.data.fills): per item type, the
game hours the item eaten alone holds the satiety model's own hunger, h_model, under Peckish, and the item's kcal. The
client's tooltip reads it per item type (NR_Client_Tooltip.lua); nothing is simulated per frame or per hover. A
generated file is never edited by hand.

The replay (FILL_LUA) composes the shared kernel the server runs, without the server adapters (the full server replay,
tools/replay_live.py ServerReplay, runs the whole pipeline at about 0.1 s a minute, too slow for every food):
- the default body at energy balance (energy state 1) and a neutral hour (the circadian factor 1, no exercise,
  nicotine or sleep-debt factor), so the hours are the item's own and not the clock's;
- h_model is K.satiety.target(K.satiety.fullness(stomach), M, 1), the writer's h_model with those factors at 1
  (NR_Server_Writer W.satiety); each minute the stomach drains and the meal pool clears on one-minute substeps
  (K.satiety.drain, as Kinetics runs it before the writer);
- the eat: K.stomach.ingest with the item's plate volume per gram (NR.data.volume.get, Plan 15 Task 7) and the meal
  pool fed with the item's weighted kcal (K.satiety.mealFeed, as NR_Server_Intake's IN.feed);
- the chosen reading (Task 9 amendments section 6: "until h_model returns to its pre-meal value, or to Peckish"; both at
  once here): the item is eaten at Peckish, the moment a satisfying meal has worn off. The pre-meal state is the
  calibration's own: the guide's plate (tools/fit_hunger_curve PLATE, the six foods summed and scaled to MEAL_KCAL, a
  third of 2,000 kcal) eaten on an empty stomach and replayed until h_model first passes the Peckish h_model,
  K.hungerCurve.inverse(0.15) (the curve maps it to HUNGER level 1, #0508). From that state the item is eaten, and its
  fill is the minutes until h_model is again over the Peckish h_model, in hours, held at CAP_H. So "fills you for about
  N h" reads: eaten when peckish, this food keeps the Peckish moodle off for N hours.
- an evolved recipe's result type (data/evolved-recipes.json resultItem) is left out: its instances carry the dish's
  own ingredients, which the type's table vector is not, so the tooltip keeps vanilla's hunger line for it.

The types are the keys of NR_Data_Nutrients.lua's per-item table (NUTRIENTS), the vectors the server lands.
"""
import argparse
import difflib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
NUTRIENTS_LUA = os.path.join(SHARED, "NR_Data_Nutrients.lua")
OUT_LUA = os.path.join(SHARED, "NR_Data_Fills.lua")
EVOLVED_JSON = os.path.join(REPO, "data", "evolved-recipes.json")
for _p in (TOOLS, KERNEL_TESTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fit_hunger_curve import MEAL_KCAL, PLATE  # noqa: E402

CAP_H = 24                 # the replay's horizon in game hours (K.view.FILL_CAP_H reads the same)
CAP_MIN = CAP_H * 60
BASE_CAP_MIN = 24 * 60     # the pre-meal replay's horizon: the plate must wear off to Peckish inside it

FILL_LUA = r"""
NR_FILL = {}
local function copy(t)
    if type(t) ~= "table" then return t end
    local o = {}
    for k, v in pairs(t) do o[k] = copy(v) end
    return o
end
local function hModel(st, M)
    local K = NutritionRevamp.kernel
    return K.satiety.target(K.satiety.fullness(st), M, 1)
end
-- The pre-meal state: the plate (its foods' vectors summed, scaled to kcal) on an empty stomach, replayed to the first
-- minute h_model passes the Peckish h_model. Returns the minutes it took, or nil when it never wears off in capMin.
function NR_FILL.base(plate, kcal, capMin)
    local NR = NutritionRevamp
    local K = NR.kernel
    NR_FILL.h0 = K.hungerCurve.inverse(K.hungerCurve.THRESHOLDS[1])
    local tot = 0
    for i = 1, #plate do tot = tot + NR.data.nutrients.get(plate[i]).calories end
    local v = K.vector.new()
    for i = 1, #plate do K.vector.add(v, NR.data.nutrients.get(plate[i]), kcal / tot) end
    local st = K.stomach.new()
    local pool = { M = 0, trait = 1 }
    K.stomach.ingest(st, v, nil)
    pool.M = K.satiety.mealFeed(pool.M, v)
    for m = 1, capMin do
        K.satiety.drain(st, 1, pool)
        if hModel(st, pool.M) > NR_FILL.h0 then
            NR_FILL.st = st
            NR_FILL.M = pool.M
            return m
        end
    end
    return nil
end
-- One item from the pre-meal state: the minutes until h_model is over the Peckish h_model again (capMin when never),
-- and the item's kcal; nil for a type the table does not carry.
function NR_FILL.minutes(fullType, capMin)
    local NR = NutritionRevamp
    local K = NR.kernel
    local src = NR.data.nutrients.get(fullType)
    if src == nil then return nil end
    local st = copy(NR_FILL.st)
    local pool = { M = NR_FILL.M, trait = 1 }
    K.stomach.ingest(st, src, NR.data.volume.get(fullType))
    pool.M = K.satiety.mealFeed(pool.M, src)
    for m = 1, capMin do
        K.satiety.drain(st, 1, pool)
        if hModel(st, pool.M) > NR_FILL.h0 then
            return m, src.calories
        end
    end
    return capMin, src.calories
end
"""


def runtime():
    """A Lua 5.1 runtime with NR_Core and every shared file loaded (the client's and the server's shared code)."""
    import lupa.lua51 as lua51
    import server_host
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(server_host.ENV)
    for p in server_host._shared_files():
        if os.path.basename(p) == os.path.basename(OUT_LUA):
            continue                                  # the output is never an input
        server_host._load(rt, p)
    rt.execute(FILL_LUA)
    return rt


def table_types(path=NUTRIENTS_LUA):
    """The keys of the per-item table NUTRIENTS (between `local NUTRIENTS = {` and its closing `}`), in file order."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("local NUTRIENTS = {")
    end = text.index("\n}\n", start)
    return re.findall(r'^\s*\["([^"]+)"\] = \{', text[start:end], re.M)


def evolved_results(path=EVOLVED_JSON):
    """The full types an evolved recipe makes (resultItem), whose instances carry their own ingredients."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = set()
    for r in doc["recipes"]:
        ft = r.get("resultItem")
        if isinstance(ft, str) and ft:
            out.add(ft if "." in ft else "Base." + ft)
    return out


def compute(rt=None):
    """{fullType: (hours, kcal)} for every table type that is not an evolved result, and the pre-meal minutes."""
    rt = rt or runtime()
    F = rt.globals().NR_FILL
    base = F.base(rt.table(*PLATE), float(MEAL_KCAL), BASE_CAP_MIN)
    if base is None:
        raise SystemExit("food_fills: the plate never wears off to Peckish in %d minutes" % BASE_CAP_MIN)
    skip = evolved_results()
    out = {}
    for ft in table_types():
        if ft in skip:
            continue
        r = F.minutes(ft, CAP_MIN)
        if r is None:
            continue
        m, kcal = r
        out[ft] = (round(m / 60.0, 2), float(kcal))
    return out, base


def num(x):
    """A number as the Lua file writes it: the shortest repr, never an exponent."""
    s = repr(float(x))
    if "e" in s or "E" in s:
        s = "%.6f" % float(x)
    return s


def render(fills, base):
    lines = [
        "-- NR_Data_Fills.lua -- not a kernel file: the tooltip's fill hours per item type and their loader (Plan 15 Task 9).",
        "-- GENERATED by tools/food_fills.py from NR_Data_Nutrients.lua and the shared kernel; do not edit -- regenerate with --write.",
        "-- Each entry is { hours, kcal }: the game hours the item eaten alone at Peckish keeps the satiety model's h_model",
        "-- under the Peckish h_model (the default body at energy balance, a neutral hour), held at %d, and the item's kcal" % CAP_H,
        "-- (its table entry's calories; the tooltip shows the line only while the item's own kcal matches it). The pre-meal",
        "-- state is the guide's plate of %s kcal worn off to Peckish (%d minutes). An evolved recipe's result" % (num(MEAL_KCAL), base),
        "-- type is left out. A reader goes through the loaders, never the table.",
        "local NR = NutritionRevamp",
        "NR.data = NR.data or {}",
        "NR.data.fills = {}",
        "",
        "local FILLS = {",
    ]
    for ft in sorted(fills):
        h, kcal = fills[ft]
        lines.append('    ["%s"] = { %s, %s },' % (ft, num(h), num(kcal)))
    lines += [
        "}",
        "",
        "-- The fill hours and the kcal of a type, or nil.",
        "function NR.data.fills.get(fullType)",
        "    local e = FILLS[fullType]",
        "    if e == nil then",
        "        return nil",
        "    end",
        "    return e[1], e[2]",
        "end",
        "",
        "-- Every type the table carries, sorted, built once (the tooltip's hunger-line hide walks it once per option change).",
        "local TYPES = nil",
        "function NR.data.fills.types()",
        "    if TYPES == nil then",
        "        TYPES = {}",
        "        for k, _ in pairs(FILLS) do",
        "            TYPES[#TYPES + 1] = k",
        "        end",
        "        table.sort(TYPES)",
        "    end",
        "    return TYPES",
        "end",
        "",
    ]
    return "\n".join(lines)


def generate():
    fills, base = compute()
    return render(fills, base)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when NR_Data_Fills.lua differs from a fresh replay")
    ap.add_argument("--write", action="store_true", help="regenerate NR_Data_Fills.lua")
    a = ap.parse_args(argv)
    if a.check == a.write:
        ap.error("give exactly one of --check and --write")
    text = generate()
    if a.write:
        with open(OUT_LUA, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("food_fills: wrote %s" % os.path.relpath(OUT_LUA, REPO))
        return 0
    try:
        with open(OUT_LUA, encoding="utf-8", newline="") as fh:
            cur = fh.read()
    except OSError:
        cur = ""
    if cur == text:
        print("food_fills: in sync")
        return 0
    diff = difflib.unified_diff(cur.splitlines(), text.splitlines(), "committed", "fresh", lineterm="", n=0)
    for i, line in enumerate(diff):
        if i >= 40:
            print("...")
            break
        print(line)
    print("food_fills: out of sync; regenerate with --write")
    return 1


if __name__ == "__main__":
    sys.exit(main())
