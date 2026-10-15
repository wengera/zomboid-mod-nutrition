"""The Nutrition Revamp player guide's series definitions (Plan 14 Tasks 3 and 4).

`tools/mod_guide_data.py` imports this module lazily and builds `docs/mod-guide/data.json` from it:

- `SERIES_DEFS` is a list of callables, each taking no argument and returning one series dict or a list of
  them, in the schema `mod_guide_data.validate_series` checks. Task 4 filled it from the source map's § 2
  (`docs/superpowers/research/2026-10-15-mod-guide/source-map.md`): artifacts, kernel replays at HEAD, the vanilla
  model (`tools/vanilla_model.py`), datasets and studies.
- `MAP_CHARTS` is the source map's charts table (§ 1, at 4e6300fa), copied as data: chart id -> section, title, x
  axis, y axis and the series ids it draws. `CHARTS` is that table less the `DROPPED` ids.
- `PENDING_LIVE` names the chart-listed ids that wait on the new live runs (x441-x447, Task 8); every other id a
  chart lists has a definition (ruling T3's reverse-coverage gate in `mod_guide_data.build`).
- `DROPPED` names each series the evidence does not support, with the reason (an old run's live dots that fail the
  admission test, ruling G8; a promise with no register row, G16).
- `VALIDATION` is the data file's validation block: the admission results Task 4 records (kind "admission": run,
  quantity, tolerance, max miss, admitted) and the vanilla model's block (spec § 3.3, Task 7).

The admission test (ruling G8): an old live point is drawn only if the HEAD replay of that run's own inputs (its
start.json, events.json, start-stats.json and player.json, the ring's own clock and activity: `admission`) matches its
ring within the run's own graded tolerance. A run that fails keeps its kernel line (its `proof_run` names it) and its
live dots are dropped. `ADMISSION_EXPECT` pins each run's outcome: a change under mod/ that flips one fails the build,
so the charts table and `DROPPED` are re-ruled rather than drift.

The replays run on the lupa host (`tools/replay_live.py`'s `ServerReplay` and its `run`); the long ones run in a
process pool (`MOD_GUIDE_JOBS` workers, 1 runs them in-process), each a deterministic job whose result is plain data.
World age 0 is 07:00 (the fixture's clock, `x36_gut_lib.HOUR_OFFSET`); the display defaults are the map's § 0: male,
no traits, sleep off (`sleep_allowed=False`) unless a series says sleep on, the item pass's macros for the guide's foods
(`data/food-nutrients.json` `.per_item`) with the game's own hunger value (`.vanilla.hunger` / 100).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import mod_guide_data as D  # noqa: E402
import vanilla_model as VM  # noqa: E402

SCRIPT = "tools/mod_guide_series.py"
TESTS = os.path.join(REPO, "testing", "tests")
FOOD_JSON = "data/food-nutrients.json"
FOOD_SCRIPT = "<install>/media/scripts/generated/items/food.txt"
GUIDE_FOODS = ("Base.Apple", "Base.Bread", "Base.CannedBologneseOpen", "Base.Burger", "Base.TunaTinOpen")
FOOD_LABELS = ("Apple", "Bread", "Bolognese", "Burger", "Tuna")
HOUR_OFFSET = 7.0                     # world age 0 is 07:00 on the fixture (x36_gut_lib.HOUR_OFFSET, #2890)
DAY_MIN = 1440
MIXED = {"p": 0.15, "c": 0.50, "f": 0.35}   # tools/replay_live.py MIXED
AUTODROP_G = 600.0                    # the map's water for a long replay: 600 g at 08, 12, 16 and 20
AUTODROP_MIN = (60, 300, 540, 780)    # 08:00, 12:00, 16:00, 20:00 from 07:00
TUNA_MIN = (60, 300, 540, 780)        # four tins at 08, 12, 16 and 20
REQUEST_MIN = (60, 360, 780)          # meals at the request at 08:00, 13:00 and 20:00 (the oracles' FAST_MEAL_H)

# the runs and their folders
RUN = {
    "x151r": "x151r-20261005-192030", "x151t": "x151t-20261005-183551", "x161b": "x161b-20261006-065751",
    "x161f": "x161f-20261006-055908", "x172b": "x172b-20261006-130714",
    "x271": "x271-20261010-135751", "x272": "x272-20261010-140932", "x276": "x276-20261010-143855",
    "x27g": "x27-grade-20261010", "x281": "x281-20261011-033356", "x282": "x282-20261011-034142",
    "x283": "x283-20261011-035042", "x284": "x284-20261011-040034", "x28g": "x28-grade-20261011",
    "x291": "x291-20261011-045658", "x29g": "x29-gate-20261011", "x301": "x301-20261011-085950",
    "x302": "x302-20261011-091000", "x30g": "x30-grade-20261011", "x341": "x341-20261011-163142",
    "x342": "x342-20261011-164251", "x343": "x343-20261011-165411", "x34r": "x34-regrade-20261011",
    "x361": "x361-20261012-200722", "x362": "x362-20261012-201625", "x363": "x363-20261012-202827",
    "x364": "x364-20261012-203308", "x36g": "x36-grade-20261012", "x37g": "x37-grade-20261013",
    "x401": "x401-20261013-152929", "x405": "x405-20261013-155742", "x434": "x434-20261015-053645",
    "x435": "x435-20261015-101839", "x436": "x436-20261015-094119", "scen": "scenario-20261004-190146",
}

MAP_CHARTS = {
    "H1": {"section": "At a glance", "title": "Hunger after one meal",
           "x": "game hours since the meal, 0–6", "y": "hunger, 0–1",
           "series": ["H1-v-model", "H1-v-live", "H1-m-kernel"]},
    "H2": {"section": "At a glance", "title": "Body mass on 1500 kcal a day",
           "x": "game days, 0–30", "y": "kg (or change from start)",
           "series": ["H2-v-model", "H2-v-live", "H2-m-fat", "H2-m-lean", "H2-m-total"]},
    "H3": {"section": "At a glance", "title": "Strength over a year of training",
           "x": "game days, 0–365", "y": "Strength level, 0–10",
           "series": ["H3-v-model-x1", "H3-v-model-x15", "H3-m-level", "H3-m-written"]},
    "H4": {"section": "At a glance", "title": "Five common foods, vanilla against the mod",
           "x": "food (Apple, Bread, Bolognese, Burger, Tuna)", "y": "kcal and grams per item",
           "series": ["H4-v-kcal", "H4-v-carb", "H4-v-fat", "H4-v-pro", "H4-m-kcal", "H4-m-carb", "H4-m-fat", "H4-m-pro"]},
    "S1a": {"section": "S1 Your first day", "title": "Hunger through a first day of four meals",
           "x": "game hours from 07:00, 0–24", "y": "hunger",
           "series": ["S1a-v-model", "S1a-v-live", "S1a-m-kernel"]},
    "S1b": {"section": "S1", "title": "When the hunger moodles arrive without food",
           "x": "game hours from a fresh start, 0–36", "y": "moodle level, 0–4",
           "series": ["S1b-v-model", "S1b-v-live", "S1b-m-kernel", "S1b-m-live"]},
    "S1c": {"section": "S1", "title": "Thirst without a drink",
           "x": "game hours, 0–24", "y": "thirst, 0–1",
           "series": ["S1c-v-model", "S1c-v-live", "S1c-m-kernel", "S1c-m-live"]},
    "S2a": {"section": "S2 Skipping meals", "title": "Hunger through a 36-hour fast and the refeed",
           "x": "game hours from the last meal, −12–60", "y": "hunger",
           "series": ["S2a-v-model", "S2a-v-live", "S2a-m-kernel", "S2a-m-live"]},
    "S2b": {"section": "S2", "title": "Eating after the fast",
           "x": "day after the fast (day 2, day 3)", "y": "intake ÷ the fed arm's",
           "series": ["S2b-m-kernel", "S2b-m-live", "S2b-study-1613", "S2b-study-1614"]},
    "S2c": {"section": "S2", "title": "Hunger as fat is lost",
           "x": "kg of fat lost", "y": "extra kcal a day eaten at the request",
           "series": ["S2c-v-model", "S2c-m-kernel", "S2c-study"]},
    "S2d": {"section": "S2", "title": "A long fast with water",
           "x": "game days, 0–90", "y": "health, kg",
           "series": ["S2d-v-model-health", "S2d-v-live-health", "S2d-v-model-weight", "S2d-v-live-weight", "S2d-m-mass", "S2d-m-drain"]},
    "S3a": {"section": "S3 Living on one food", "title": "Vitamin C on tinned tuna alone",
           "x": "game days, 0–60", "y": "vitamin C store (0–1) and grade",
           "series": ["S3a-m-pool", "S3a-m-grade", "S3a-study-0224", "S3a-study-0225"]},
    "S3b": {"section": "S3", "title": "Mood on one food",
           "x": "game days, 0–7", "y": "unhappiness, boredom (0–100)",
           "series": ["S3b-m-live-U", "S3b-m-live-B", "S3b-m-kernel-U", "S3b-v-live-U", "S3b-v-live-B"]},
    "S3c": {"section": "S3", "title": "What fixes it: an orange a day",
           "x": "game days, 40–80", "y": "vitamin C store",
           "series": ["S3c-m-pool", "S3c-study"]},
    "S4a": {"section": "S4 A year at the gym", "title": "Strength by diet",
           "x": "game days, 0–365", "y": "Strength level",
           "series": ["S4a-m-perfect", "S4a-m-lowprotein", "S4a-m-deficit", "S4a-v-model-x1", "S4a-v-model-x07"]},
    "S4b": {"section": "S4", "title": "Ten years toward the natural cap",
           "x": "game years, 0–10", "y": "Strength level",
           "series": ["S4b-m-level", "S4b-m-cap", "S4b-v-model", "S4b-study"]},
    "S4c": {"section": "S4", "title": "Stopping and starting again",
           "x": "game days, 0–910", "y": "Strength level",
           "series": ["S4c-m-kernel", "S4c-v-model", "S4c-study-0618", "S4c-study-0078"]},
    "S5a": {"section": "S5 Choosing your body", "title": "The starting body of each pick",
           "x": "pick (none, Strong+Obese, Weak+Overweight, Overly Lean, Weak+Gaunt, Feeble+Overly Lean)", "y": "kg; Strength level",
           "series": ["S5a-m-live-lean", "S5a-m-live-fat", "S5a-m-live-weight", "S5a-m-live-level", "S5a-v-model-weight", "S5a-v-model-level"]},
    "S5b": {"section": "S5", "title": "How each body drifts, untrained",
           "x": "game days, 0–90", "y": "Strength level; kg",
           "series": ["S5b-m-strong-level", "S5b-m-weak-level", "S5b-m-none-level", "S5b-m-gaunt-weight", "S5b-m-overfat-weight", "S5b-m-none-weight", "S5b-v-model-level"]},
    "S5c": {"section": "S5", "title": "A thin start is hungry",
           "x": "game days, 0–30", "y": "energy state (hunger drive)",
           "series": ["S5c-m-gaunt", "S5c-m-none", "S5c-m-live", "S5c-v-model"]},
    "S6a": {"section": "S6 Coffee, beer, no sleep", "title": "Caffeine and tolerance",
           "x": "game hours over day 1 and day 14", "y": "caffeine in the body (mg); fatigue",
           "series": ["S6a-m-day1", "S6a-m-day14", "S6a-v-model"]},
    "S6b": {"section": "S6", "title": "Four beers",
           "x": "game hours, 0–24", "y": "intoxication (0–100); blood alcohol %",
           "series": ["S6b-v-model", "S6b-v-live", "S6b-m-bac", "S6b-m-intox", "S6b-m-hangover"]},
    "S6c": {"section": "S6", "title": "A short night and the next day's hunger",
           "x": "game days, 0–4", "y": "sleep debt (h); hunger factor",
           "series": ["S6c-m-kernel", "S6c-m-live", "S6c-v-model", "S6c-study"]},
    "SN1": {"section": "Nutrients and foods", "title": "What the five foods carry",
           "x": "food", "y": "mg or g per item",
           "series": ["SN1-m-vitC", "SN1-m-fibre", "SN1-m-iron", "SN1-m-sodium"]},
    "SE1": {"section": "Eating and the stomach", "title": "A drink and a meal in the stomach",
           "x": "game minutes", "y": "grams; fill (0–1)",
           "series": ["SE1-m-live-liquid", "SE1-m-live-fill", "SE1-m-kernel-fill"]},
    "SH1": {"section": "Hunger", "title": "How long a meal holds hunger off",
           "x": "meal kcal", "y": "minutes to the hunger request",
           "series": ["SH1-m-kernel", "SH1-m-live", "SH1-study-1247", "SH1-study-1248"]},
    "SH2": {"section": "Hunger", "title": "Three meals against six",
           "x": "arm", "y": "mean hunger over 24 h (ratio)",
           "series": ["SH2-m-kernel", "SH2-m-live", "SH2-study"]},
    "ST1": {"section": "Thirst and salt", "title": "Ten hours at rest without a drink",
           "x": "game hours, 0–10", "y": "thirst",
           "series": ["ST1-v-model", "ST1-m-kernel", "ST1-m-live"]},
    "ST2": {"section": "Thirst and salt", "title": "Five days without salt",
           "x": "game days, 0–5", "y": "body sodium change (mmol/24 h); plasma sodium",
           "series": ["ST2-m-live-na", "ST2-m-live-plasma", "ST2-m-kernel"]},
    "SM1": {"section": "Monotony", "title": "Varying the diet lifts the mood",
           "x": "game hours after the last repeat", "y": "unhappiness",
           "series": ["SM1-m-live", "SM1-m-kernel"]},
    "SB1": {"section": "The body", "title": "Lean mass at a deficit and a surplus, trained or not",
           "x": "game days, 0–60", "y": "lean kg",
           "series": ["SB1-m-def-rest", "SB1-m-def-train", "SB1-m-sur-rest", "SB1-m-sur-train"]},
    "SB2": {"section": "The body", "title": "Which weight trait a body gets",
           "x": "example body (lean 90 kg, average, soft 85 kg)", "y": "trait band",
           "series": ["SB2-v-model", "SB2-m-kernel"]},
    "SX1": {"section": "Exercise and energy", "title": "Energy per hour by activity",
           "x": "activity", "y": "kcal per game hour at 80 kg",
           "series": ["SX1-v-model", "SX1-m-kernel", "SX1-m-live"]},
    "SX2": {"section": "Exercise and energy", "title": "Hunger after hard exercise",
           "x": "game minutes after the set", "y": "hunger",
           "series": ["SX2-v-model", "SX2-m-live", "SX2-m-kernel"]},
    "SS1": {"section": "Strength", "title": "A year's Strength by weekly sets",
           "x": "hard sets a week, 0–20", "y": "Strength level after a year",
           "series": ["SS1-m-kernel", "SS1-v-model"]},
    "SD1": {"section": "Deficiency and excess", "title": "Clinical scurvy and health",
           "x": "game days", "y": "health",
           "series": ["SD1-m-live", "SD1-m-kernel"]},
    "SD2": {"section": "Deficiency and excess", "title": "How long each nutrient lasts with none eaten",
           "x": "nutrient", "y": "days to Marginal, days to Clinical",
           "series": ["SD2-m-marginal", "SD2-m-clinical", "SD2-study"]},
    "SC1": {"section": "Caffeine, alcohol and sleep", "title": "Short nights build a sleep debt",
           "x": "night", "y": "hours slept; debt (h)",
           "series": ["SC1-m-live-booked", "SC1-m-live-debt", "SC1-m-kernel"]},
    "SV1": {"section": "What you see on screen", "title": "The Overfull moodle",
           "x": "grams in the stomach", "y": "moodle level, 0–4",
           "series": ["SV1-m-kernel", "SV1-m-live"]},
}

# ---- the series the evidence does not support, and the ones that wait on a live run -----------------------------------

# The vanilla-live gaps: x441-x447 (Task 5's drivers, Task 8's runs) fill them; S2d-v-live-weight is an existing run.
PENDING_LIVE = (
    "H1-v-live", "H2-v-live", "S1a-v-live", "S1b-v-live", "S1c-v-live", "S2a-v-live", "S2d-v-live-health",
    "S3b-v-live-U", "S3b-v-live-B", "S6b-v-live",
)

# Each dropped id and why. The admission results behind the G8 drops are in VALIDATION.
DROPPED = {
    "S1b-m-live": "G8: x364's HEAD replay misses its ring (HUNGER 0.00265 over 0.002, es 0.00505 over 0.005); the "
                  "kernel line keeps x364 as its proof run",
    "S1c-m-live": "G8: x364 fails the admission test on HUNGER and es (its THIRST alone lies within 0.0019)",
    "S2a-m-live": "G8: x364 fails the admission test",
    "S2b-m-live": "G8: x271 and x272 (the rows' fast) fail the admission test (pre-Plan 11g rings)",
    "SH2-m-live": "G8: x276 fails the admission test (a pre-Plan 11g ring); SH2-m-kernel replays its inputs at HEAD",
    "SM1-m-live": "G8: x343's HEAD replay misses its UNHAPPINESS by up to 1.74 against 0.051",
    "SX2-m-live": "G8: x291's HEAD replay misses its satiety.S by up to 0.087 against 1e-6",
    "ST1-m-live": "G8: x151t (the Plan 4 build) carries no ring and no event log to replay at HEAD, so no admission "
                  "test can run on it",
    "ST2-m-live-plasma": "G8: the HEAD replays of x281-x284 hold the sodium balance exactly but miss plasma sodium by "
                         "up to 0.072 mmol/L (the creation body's lean mass enters the concentration) against 0.01",
    "S2d-m-drain": "G16: no register row states the starvation drain's condition (K.effects.drain code 1)",
}

# The admission outcome each run is pinned to (a change that flips one fails the build: re-rule the charts).
ADMISSION_EXPECT = {
    "x271": False, "x272": False, "x276": False, "x281": True, "x282": True, "x283": True, "x284": True,
    "x281:plasma": False, "x282:plasma": False, "x283:plasma": False, "x284:plasma": False,
    "x291": False, "x301": True, "x302": True, "x341": True, "x342": True, "x343": False, "x361": True,
    "x363": True, "x364": False, "x37g": True, "x401": True, "x161b": True,
}

CHARTS = {cid: dict(c, series=[i for i in c["series"] if i not in DROPPED]) for cid, c in MAP_CHARTS.items()}

VALIDATION = []

JOBS_ENV = "MOD_GUIDE_JOBS"


# ---- lazy imports: the replay tool, the kernel tests' package, a kernel host -------------------------------------------

def _rl():
    import replay_live
    return replay_live


def _kt(name):
    """A module of testing/tests/kernel as the package pytest imports (kernel.<name>), its relative imports kept."""
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    import importlib
    return importlib.import_module("kernel." + name)


class KHost:
    """server_host.Host (the shared and server Lua at HEAD) with the kernel test host's call and table."""

    def __init__(self):
        _, server_host, _ = _rl()._lua()
        h = server_host.Host()
        self.rt, self.G, self.NR, self.K = h.rt, h.G, h.NR, h.K

    def call(self, path, *args):
        fn = self.K
        for seg in path.split("."):
            fn = fn[seg]
        return fn(*args)

    def table(self, d):
        """A Lua table of d, a nested dict made a nested table (the kernel test host's conversion)."""
        t = self.rt.table()
        for k, v in d.items():
            t[k] = self.table(v) if isinstance(v, dict) else v
        return t


# ---- provenance and series builders -------------------------------------------------------------------------------------

def _chart(sid):
    return sid.split("-")[0]


def series(sid, label, x, y, badge, points, prov, note=None):
    s = {"id": sid, "chart": _chart(sid), "label": label, "units": {"x": x, "y": y}, "badge": badge,
         "points": [[a, b] for a, b in points], "provenance": prov}
    if note:
        s["note"] = note
    return s


def kernel(inputs, proof):
    return {"kind": "kernel", "script": SCRIPT, "inputs": inputs, "proof_run": RUN[proof]}


def artifact(run, file, path):
    return {"kind": "artifact", "run": RUN[run], "file": file, "path": path}


def study(sid):
    return {"kind": "study", "science": sid}


def dataset(file, key):
    p = {"kind": "dataset", "file": file, "key": key}
    if file.startswith(D.INSTALL_PREFIX):
        p["build"] = D.INSTALL_BUILD
    return p


_REG = {}


def _register():
    if not _REG:
        _REG["ids"] = D._register_ids(D.REPO, D.CLAIMS_REL)
    return _REG["ids"]


def vmodel(*formulas):
    """A vanilla-model provenance: the formulas and their register rows (a row a later task mints, such as T2.1, is
    left out until it is in the register)."""
    ids = _register()
    claims = []
    for f in formulas:
        for c in VM.FORMULAS[f]["claims"]:
            if c in ids and c not in claims:
                claims.append(c)
    return {"kind": "vanilla-model", "formulas": list(formulas), "claims": claims}


def read(run, file, path):
    return D.read_artifact(RUN[run], file, path)


# ---- the guide's foods ---------------------------------------------------------------------------------------------------

_FOODS = {}


def food(pz):
    """The item-pass record of a guide food in data/food-nutrients.json."""
    if not _FOODS:
        with open(os.path.join(REPO, *FOOD_JSON.split("/")), encoding="utf-8") as fh:
            for it in json.load(fh)["items"]:
                _FOODS[it["pz_id"]] = it
    return _FOODS[pz]


def food_type(pz):
    module, item = pz.split(".")
    try:
        return D.read_dataset(FOOD_SCRIPT, "%s.%s.FoodType" % (module, item))
    except D.ProvenanceError:
        return None


ITEM_PASS = "mod/NutritionRevamp/common/media/scripts/NR_ItemPass_Food.txt"


def eat(minute, pz):
    """An eat of a whole guide food as the game's item reads it: the item pass's macros from its script
    (NR_ItemPass_Food.txt, generated from data/food-nutrients.json's .per_item and written to two decimals) as the
    float getters return them (replay_live.float32, as study_foods reads a script), and the game's own hunger value
    (.vanilla.hunger / 100, which the pass leaves); the chain takes the rest from the mod's table, the vector #3182
    measured landing live."""
    f32 = _rl().float32
    module, item = pz.split(".")
    mac = [f32(D.read_dataset(ITEM_PASS, "%s.%s.%s" % (module, item, k)))
           for k in ("Calories", "Carbohydrates", "Lipids", "Proteins")]
    r = food(pz)
    ev = {"minute": minute, "kind": "eat", "fullType": pz, "cal": mac[0], "carb": mac[1], "lip": mac[2],
          "pro": mac[3], "hunger": r["vanilla"]["hunger"] / 100.0}
    ft = food_type(pz)
    if ft is not None:
        ev["foodType"] = ft
    return ev


def autodrops(days):
    return [{"minute": d * DAY_MIN + m, "kind": "autodrop", "g": AUTODROP_G} for d in range(days) for m in AUTODROP_MIN]


def request_meals(days):
    return [{"minute": d * DAY_MIN + m, "kind": "meal", "size": "request", "comp": MIXED}
            for d in range(days) for m in REQUEST_MIN]


def sort_events(ev):
    return sorted(ev, key=lambda e: e["minute"])


# ---- the replays ---------------------------------------------------------------------------------------------------------

def server_run(events, minutes, paths=(), player=None, perk=None, sleep_allowed=False, hour_offset=HOUR_OFFSET,
               start=None):
    """The mod's server pipeline on the lupa host from a fresh record (first sight builds the creation body from the
    stand-in's traits), on a synthetic one-minute clock from world age 0; returns (rows, backend). Row k is the state
    drain k left, at age (k + 1) / 60. `perk` is the native Strength level vanilla's applyTraits left (the creation
    reads the muscle pick off it: CRE.inferMuscle)."""
    RL = _rl()
    be = RL.ServerReplay(start=start, player=player, hour_offset=hour_offset, rng="half", sleep_allowed=sleep_allowed)
    if perk is not None:
        be.p.st.perk = perk
    rows = RL.run(be, RL.synthetic_ages(minutes), sort_events(events), list(paths), start_age=0.0)
    return rows, be


def pick(rows, ks, *fields):
    """[[k, age, field values...]] at row indices ks (rows past the end skipped)."""
    out = []
    for k in ks:
        if 0 <= k < len(rows):
            r = rows[k]
            out.append([k, r["age"]] + [r.get(f) for f in fields])
    return out


def day_ends(days):
    """Row indices at each world-day boundary (07:00): 0 (the first sight) and k = 1440 d - 1 for d >= 1."""
    return [0] + [d * DAY_MIN - 1 for d in range(1, days + 1)]


# ---- the job pool -------------------------------------------------------------------------------------------------------

_JOBS = {}
_RESULTS = {}


def job(fn):
    _JOBS[fn.__name__] = fn
    return fn


def run_job(name):
    return _JOBS[name]()


def jobs_n():
    v = os.environ.get(JOBS_ENV)
    if v:
        return max(1, int(v))
    return max(1, min(12, (os.cpu_count() or 2) - 1))


def compute(names=None):
    """Run the named jobs (all registered ones not yet run when None), in a process pool when jobs_n() > 1."""
    todo = [n for n in (names or sorted(_JOBS)) if n not in _RESULTS]
    if not todo:
        return
    n = min(jobs_n(), len(todo))
    if n <= 1:
        for name in todo:
            _RESULTS[name] = run_job(name)
        return
    from concurrent.futures import ProcessPoolExecutor
    order = sorted(todo, key=lambda x: -JOB_COST.get(x, 1))     # the longest first, so the pool's tail is short
    with ProcessPoolExecutor(max_workers=n) as ex:
        for name, res in zip(order, ex.map(run_job, order)):
            _RESULTS[name] = res


def result(name):
    if name not in _RESULTS:
        compute()
    return _RESULTS[name]


def reset():
    """Forget every computed job and host (a test that edits the Lua tree reruns them)."""
    _RESULTS.clear()


# rough CPU seconds, for the pool's order only
JOB_COST = {"j_s2d": 30, "j_s3c": 28, "j_s3a": 21, "j_s5b_strong": 31, "j_s5b_weak": 31, "j_s5b_none": 31,
            "j_s5b_gaunt": 31, "j_s5b_overweight": 31, "j_h2": 11, "j_s2c": 9, "j_s2b": 6, "j_s3b": 5, "j_s6a": 5,
            "j_vanilla_s4b": 12, "j_s2a": 3, "j_sh1": 3}


# ---- the admission test (ruling G8) ------------------------------------------------------------------------------------

DEFAULT_TOL = {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005)}      # replay_live.DEFAULT_TOL's two
FILL_TOL = {"stomachFill": ("abs", 0.002), "stomach.liquid": ("abs", 2.0)}         # x36_gut_lib TOL_GRADE, TOL_EXTRA
DEBT_TOL = {"acute.debtH": ("abs", 1e-6), "acute.winSleptH": ("abs", 1e-6)}        # x30_grade.TOL_MINE
S_TOL = {"satiety.S": ("abs", 1e-6)}                                               # x29_grade.TOL_MINE
THIRST_TOL = {"THIRST": ("abs", 0.002)}        # named here (G7: THIRST was never graded): HUNGER's bound
SODIUM_TOL = {"fluids.na": ("abs", 1e-6)}      # named here: x28 graded no sodium bound; the balance is exact
PLASMA_TOL = {"fluids.naPlasma": ("abs", 0.01)}   # named here: the 0.01 mmol/L #3688 states plasma sodium to


def mood_tol(eps):
    """x34_grade's live-against-replay bound for UNHAPPINESS and the remembered targets: FLOOR_EPS plus 1e-3."""
    b = eps + 1e-3
    return {"UNHAPPINESS": ("abs", b), "moodLast.b": ("abs", b)}


def _ring(run_dir):
    import glob
    import re
    pages = sorted(glob.glob(os.path.join(run_dir, "minute-ring-admin-*.json")),
                   key=lambda p: int(re.findall(r"-(\d+)\.json$", p)[0]))
    ring, paths = _rl().load_ring(pages)
    return [r for r in ring if r.get("age") is not None], paths


def _json(run_dir, name):
    p = os.path.join(run_dir, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def admission(run, sleep_allowed, tol, keep=()):
    """The HEAD replay of run's own inputs against its ring, graded by replay_live.diff under tol. Returns (record,
    rows): record {kind, run, quantity, tolerance, max_miss, n, admitted}; rows the replay rows' `keep` fields by s."""
    RL = _rl()
    d = os.path.join(REPO, "testing", "artifacts", RUN[run])
    ring, paths = _ring(d)
    rows, _ = RL.replay_live(ring, _json(d, "events.json") or [], _json(d, "start.json"), paths=paths, user="admin",
                             player=_json(d, "player.json"), start_stats=_json(d, "start-stats.json"),
                             sleep_allowed=sleep_allowed)
    df = RL.diff(rows, ring, tol)
    rec = {"kind": "admission", "run": RUN[run], "quantity": sorted(tol),
           "tolerance": {f: [how, b] for f, (how, b) in sorted(tol.items())},
           "max_miss": {f: df["fields"][f]["max"] for f in sorted(tol)},
           "n": {f: df["fields"][f]["n"] for f in sorted(tol)}, "admitted": bool(df["ok"])}
    kept = {r["s"]: [r.get("age")] + [r.get(f) for f in keep] for r in rows} if keep else None
    return rec, kept


@job
def j_adm_x36():
    out = {}
    for run in ("x361", "x363", "x364"):
        tol = dict(DEFAULT_TOL)
        if run == "x363":
            tol.update(FILL_TOL)
        if run == "x364":
            tol.update(THIRST_TOL)
        rec, kept = admission(run, False, tol, keep=("stomachFill",) if run == "x363" else ())
        out[run] = {"rec": rec, "rows": kept}
    return out


@job
def j_adm_x27():
    out = {}
    for run in ("x271", "x272"):
        out[run] = {"rec": admission(run, False, dict(DEFAULT_TOL))[0]}
    return out


@job
def j_sh2():
    """x276 (SH2): the admission test, and the HEAD replay of its live events (six meals, S0_*) against its three-meal
    arm (x27_grade.row8's arm: the six S0_ eats replaced by three TKX.Mixed667 at 08:00 + 5 h k of day 0, world age
    25 + 5k): the time-weighted mean HUNGER over the 24 h from world age 25 (x27_energy_lib.mean_over)."""
    RL = _rl()
    rec, _ = admission("x276", False, dict(DEFAULT_TOL))
    d = os.path.join(REPO, "testing", "artifacts", RUN["x276"])
    ring, paths = _ring(d)
    ev = _json(d, "events.json")
    kw = dict(paths=paths, user="admin", player=_json(d, "player.json"), start_stats=_json(d, "start-stats.json"),
              sleep_allowed=False)
    six, _ = RL.replay_live(ring, ev, _json(d, "start.json"), **kw)
    t0 = 25.0
    base = [e for e in ev if not str(e.get("label", "")).startswith("S0_")]
    three_ev = [{"age": t0 + 5.0 * k, "kind": "eat", "food": "TKX.Mixed667", "label": "T6_%d" % k} for k in range(3)]
    three, _ = RL.replay_live(ring, base + three_ev, _json(d, "start.json"), **kw)
    return {"rec": rec, "six": mean_over(six, t0, 1440), "three": mean_over(three, t0, 1440),
            "loads": True}


def mean_over(rows, after_age, minutes, field="HUNGER"):
    """x27_energy_lib.mean_over: the time-weighted mean over (after_age, after_age + minutes], each row's value held
    over its dtM before it."""
    t1 = after_age + minutes / 60.0
    acc = span = 0.0
    prev = after_age
    for r in rows:
        a0 = r.get("age")
        if not isinstance(a0, (int, float)) or a0 <= after_age + 1e-12 or not isinstance(r.get(field), (int, float)):
            continue
        a = min(a0, t1)
        acc += r[field] * (a - prev)
        span += a - prev
        prev = a
        if a0 >= t1:
            break
    return acc / span if span > 0 else None


@job
def j_adm_x28():
    """x281-x284 (ST2), graded twice: the record's sodium balance (ST2-m-live-na) and plasma sodium (-plasma)."""
    out = {}
    for run in ("x281", "x282", "x283", "x284"):
        out[run] = {"rec": admission(run, False, dict(SODIUM_TOL))[0]}
        out[run + ":plasma"] = {"rec": admission(run, False, dict(PLASMA_TOL))[0]}
    return out


@job
def j_adm_x29():
    return {"x291": {"rec": admission("x291", False, dict(S_TOL))[0]}}


@job
def j_adm_x30():
    out = {}
    for run in ("x301", "x302"):
        rec, kept = admission(run, True, dict(DEBT_TOL), keep=("acute.debtH",))
        out[run] = {"rec": rec, "rows": kept}
    return out


@job
def j_adm_x34():
    K = KHost().K
    tol = mood_tol(float(K.hybrid.FLOOR_EPS))
    out = {}
    for run in ("x341", "x342", "x343"):
        rec, kept = admission(run, False, tol, keep=("UNHAPPINESS",) if run == "x343" else ())
        out[run] = {"rec": rec, "rows": kept}
    return out


def adm(run):
    """The admission record of a run, and a check against ADMISSION_EXPECT."""
    src = {"x361": "j_adm_x36", "x363": "j_adm_x36", "x364": "j_adm_x36", "x271": "j_adm_x27", "x272": "j_adm_x27",
           "x276": "j_sh2", "x281": "j_adm_x28", "x282": "j_adm_x28", "x283": "j_adm_x28", "x284": "j_adm_x28",
           "x281:plasma": "j_adm_x28", "x282:plasma": "j_adm_x28", "x283:plasma": "j_adm_x28",
           "x284:plasma": "j_adm_x28",
           "x291": "j_adm_x29", "x301": "j_adm_x30", "x302": "j_adm_x30", "x341": "j_adm_x34", "x342": "j_adm_x34",
           "x343": "j_adm_x34"}
    if run in src:
        r = result(src[run])
        rec = r["rec"] if run == "x276" else r[run]["rec"]
    else:
        rec = OTHER_ADMISSIONS[run]()
    if rec["admitted"] != ADMISSION_EXPECT[run]:
        raise D.ProvenanceError("admission of %s is %s at HEAD, pinned %s: re-rule its live series and DROPPED"
                                % (run, rec["admitted"], ADMISSION_EXPECT[run]))
    return rec


def _adm_x37():
    """x37's billed MET (SX1-m-live): every bill of x371's sets against the HEAD EXERCISE_MET of its type, exactly."""
    K = KHost().K
    types = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].type")
    billed = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].billed")
    miss = 0.0
    for t, b in zip(types, billed):                      # [*][*] reads flat, one leaf per bill
        miss = max(miss, abs(float(K.energy.EXERCISE_MET[t]) - b))
    return {"kind": "admission", "run": RUN["x37g"], "quantity": ["billed MET (K.energy.EXERCISE_MET at HEAD)"],
            "tolerance": {"billed MET": ["abs", 0.0]}, "max_miss": {"billed MET": miss},
            "n": {"billed MET": len(billed)}, "admitted": miss == 0.0 and len(types) == len(billed) > 0}


def _adm_x401():
    """x401's Overfull rows (SV1-m-live): K.view.fullnessLevel at HEAD of each row's server mass against the level
    the client showed, exactly."""
    K = KHost().K
    mass = read("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass")
    lv = read("x401", "accept.json", "verdicts.OF.observed.rows[*].levels")
    miss = max(abs(float(K.view.fullnessLevel(m)) - v) for m, v in zip(mass, lv))
    return {"kind": "admission", "run": RUN["x401"], "quantity": ["Overfull level (K.view.fullnessLevel at HEAD)"],
            "tolerance": {"level": ["abs", 0.0]}, "max_miss": {"level": miss}, "n": {"level": len(mass)},
            "admitted": miss == 0.0}


def scurvy_drain(h):
    """K.effects.drain at HEAD (h a KHost) for clinical vitamin C held past SCURVY_H, nothing else wrong: (drain a
    game minute, code). The stand-in tables carry the fields the function reads."""
    K = h.K
    t = h.table
    nut = t({"vitC": t({"g": 4, "ah": float(K.effects.SCURVY_H)}), "thiamine": t({"g": 1, "ah": 0}),
             "niacin": t({"g": 1, "ah": 0}), "iron": t({"x": 0})})
    E = t({})
    K.effects.drain(E, nut, t({"naPlasma": 140.0, "dehydPct": 0.0}), t({"bmi": 0.0}), 0, 0.2, 1, True)
    return float(E["drain"]), int(E["lethal"])


def _adm_x161b():
    """x161b's scurvy drain (SD1-m-live): the HEAD drain a game hour against the run's own prediction from the
    drain it read (summaries.I.pred_per_game_h), within 1e-9."""
    d, code = scurvy_drain(KHost())
    pred = read("x161b", "body.json", "summaries.I.pred_per_game_h")
    miss = abs(-d * 60.0 - pred)
    return {"kind": "admission", "run": RUN["x161b"], "quantity": ["scurvy drain a game hour (K.effects.drain at HEAD)"],
            "tolerance": {"drain": ["abs", 1e-9]}, "max_miss": {"drain": miss}, "n": {"drain": 1},
            "admitted": miss <= 1e-9 and code == 2}


OTHER_ADMISSIONS = {"x37g": _adm_x37, "x401": _adm_x401, "x161b": _adm_x161b}


def admissions():
    """Every admission record, ordered by its ADMISSION_EXPECT key (run, then a second quantity's suffix), for
    VALIDATION."""
    return [adm(r) for r in sorted(ADMISSION_EXPECT)]


def fill_validation():
    VALIDATION[:] = [v for v in VALIDATION if v.get("kind") != "admission"] + admissions()


# ======================================================================================================================
# The jobs (the replays and the long vanilla runs)
# ======================================================================================================================

def _ks(start, stop, step):
    return list(range(start, stop, step))


@job
def j_h1():
    """H1: a fresh record from 07:00 with no food until the written HUNGER first reaches 0.25 (replay_live
    request_minute), then a whole Base.CannedBologneseOpen at that minute, 6 h after."""
    RL = _rl()
    rows, _ = server_run([], DAY_MIN)
    m = int(round(RL.request_minute(rows, 0.0)))
    rows, _ = server_run([eat(m, "Base.CannedBologneseOpen")], m + 361, ("satiety.M", "body.energyState"))
    pts = pick(rows, [m - 1] + _ks(m, m + 361, 10), "HUNGER")
    return {"request_minute": m, "points": [[age - m / 60.0, h] for _, age, h in pts]}


@job
def j_h2():
    """H2: 30 days of three 500 kcal mixed meals at 07, 12 and 18 and 600 g of water at 08, 12, 16 and 20."""
    ev = [{"minute": d * DAY_MIN + m, "kind": "meal", "size": 500.0, "comp": MIXED} for d in range(30)
          for m in (0, 300, 660)] + autodrops(30)
    rows, _ = server_run(ev, 30 * DAY_MIN, ("body.fm", "body.lm", "body.lx"))
    return {"days": pick(rows, day_ends(30), "body.fm", "body.lm", "body.lx")}


@job
def j_s1a():
    rows, _ = server_run([eat(m, "Base.TunaTinOpen") for m in TUNA_MIN], DAY_MIN)
    return {"points": [[age, h] for _, age, h in pick(rows, [0] + _ks(9, DAY_MIN, 10), "HUNGER")]}


SIG = "_G.NutritionRevamp.server.bus.lastSig.admin"


@job
def j_s1b():
    rows, _ = server_run([], 36 * 60, (SIG,))
    return {"points": [[age, int(s // 1000) % 10] for _, age, s in pick(rows, [0] + _ks(9, 36 * 60, 10), SIG)]}


@job
def j_s1c():
    rows, _ = server_run([], DAY_MIN, ("fluids.thirstTarget",))
    return {"points": [[age, t] for _, age, t in pick(rows, [0] + _ks(9, DAY_MIN, 10), "THIRST")]}


@job
def j_s2a():
    """S2a: test_replay_live_oracle.fast_plans()'s fast arm (three warm maintenance days, day 0 at maintenance, day 1
    skipped, days 2-3 at the request) on the default body, sleep off, on the oracle's clock (minute 0 is 00:00)."""
    O = _kt("test_replay_live_oracle")
    M = _kt("test_satiety_meal_studies")
    _, fast, days = O.fast_plans()
    ev = [{"minute": m, "kind": "meal", "size": k} for m, k in sorted(fast.items())]
    rows, _ = server_run(ev, days * DAY_MIN, ("body.energyState",), hour_offset=0.0)
    last = M.at_hour(0, 20)
    ks = [k for k in range(len(rows)) if -12 * 60 <= k + 1 - last <= 60 * 60 and (k + 1 - last) % 10 == 0]
    return {"last_meal_minute": last, "points": [[(k + 1 - last) / 60.0, h] for k, _, h in pick(rows, ks, "HUNGER")]}


@job
def j_s2b():
    E = _kt("test_replay_live_energy")
    r = E.fast_server()
    return {"r2": r["r2"], "r3": r["r3"]}


@job
def j_s2c():
    E = _kt("test_replay_live_energy")
    h = KHost()
    f = E.fat_loss_server(h)
    fm_ref = h.call("body.create", None, None, h.K.strength.DEFAULTS, 1)["fm"]
    return {"base": f["base"], "low": f["low"], "low_kg": fm_ref * E.S1254_LOW, "kg": list(f["kg"]),
            "intake": list(f["intake"]), "slope": f["slope"]}


@job
def j_s2d():
    rows, _ = server_run(autodrops(90), 90 * DAY_MIN, ("body.fm", "body.lm", "body.lx"))
    return {"days": pick(rows, day_ends(90), "body.fm", "body.lm", "body.lx"),
            "hunger_max": max(r["HUNGER"] for r in rows)}


def _nutrient_keys():
    K = KHost()
    order = K.NR.data.records.ORDER
    return [order[i] for i in range(1, len(order) + 1)]


def _tuna_days(days):
    return [eat(d * DAY_MIN + m, "Base.TunaTinOpen") for d in range(days) for m in TUNA_MIN] + autodrops(days)


def _grades(days, ev):
    keys = _nutrient_keys()
    paths = ["nutrients.%s.p" % k for k in keys] + ["nutrients.%s.g" % k for k in keys]
    rows, _ = server_run(ev, days * DAY_MIN, paths)
    ends = day_ends(days)
    out = {"vitC_p": pick(rows, ends, "nutrients.vitC.p"), "vitC_g": pick(rows, ends, "nutrients.vitC.g")}
    first2 = {}
    for k in keys:
        for _, age, g in pick(rows, ends, "nutrients.%s.g" % k):
            if isinstance(g, (int, float)) and g >= 2:
                first2[k] = age / 24.0
                break
    out["first_grade2_day"] = first2
    return out


@job
def j_s3a():
    """S3a: four Base.TunaTinOpen a day at 08, 12, 16 and 20 and the long replay's water, 60 days."""
    return _grades(60, _tuna_days(60))


ORANGE_MIN = 180                       # 10:00


@job
def j_s3c():
    """S3c: S3a's diet to day 80 with one Base.Orange a day at 10:00 from day 45."""
    ev = _tuna_days(80) + [eat(d * DAY_MIN + ORANGE_MIN, "Base.Orange") for d in range(45, 80)]
    return _grades(80, ev)


VARIED = ("Base.Bread", "Base.CannedBologneseOpen", "Base.Burger", "Base.Apple", "Base.Orange", "Base.TunaTinOpen")


@job
def j_s3b():
    """S3b: four Base.TunaTinOpen a day for 7 days, then 7 days of four foods a day rotating through VARIED."""
    ev = [eat(d * DAY_MIN + m, "Base.TunaTinOpen") for d in range(7) for m in TUNA_MIN]
    ev += [eat(d * DAY_MIN + m, VARIED[(d * 4 + i) % len(VARIED)]) for d in range(7, 14)
           for i, m in enumerate(TUNA_MIN)]
    rows, _ = server_run(ev + autodrops(14), 14 * DAY_MIN)
    return {"points": [[age / 24.0, u] for _, age, u in pick(rows, [0] + _ks(119, 14 * DAY_MIN, 120), "UNHAPPINESS")]}


# S5b's bodies: the stand-in's traits and the native Strength level vanilla's applyTraits left (JT1: Strong 9, Weak 0,
# none 5), which the creation reads the muscle pick off (CRE.inferMuscle; at 0 it falls back to the held band trait)
S5B = {"strong": (["STRONG"], 9), "weak": (["WEAK"], 0), "none": ([], 5), "gaunt": (["VERY_UNDERWEIGHT"], 5),
       "overweight": (["OVERWEIGHT"], 5)}


def _s5b(name):
    traits, perk = S5B[name]
    ev = request_meals(90) + autodrops(90)
    rows, be = server_run(ev, 90 * DAY_MIN, ("body.fm", "body.lm", "body.lx", "body.N0", "body.T", "body.wroteL",
                                             "body.energyState"), player={"traits": traits, "female": False},
                          perk=perk)
    K = be.K
    P = K.strength.DEFAULTS
    days = []
    for k, age, fm, lm, lx, n0, T, wrote, es in pick(rows, day_ends(90), "body.fm", "body.lm", "body.lx", "body.N0",
                                                      "body.T", "body.wroteL", "body.energyState"):
        days.append([age / 24.0, fm, lm, lx, float(K.strength.level(lm, n0, T, P)), wrote, es])
    return {"days": days}


@job
def j_s5b_strong():
    return _s5b("strong")


@job
def j_s5b_weak():
    return _s5b("weak")


@job
def j_s5b_none():
    return _s5b("none")


@job
def j_s5b_gaunt():
    return _s5b("gaunt")


@job
def j_s5b_overweight():
    return _s5b("overweight")


COFFEE_MIN = (60, 300, 540)            # 08:00, 12:00, 16:00


@job
def j_s6a():
    ev = [{"minute": d * DAY_MIN + m, "kind": "drink", "fluid": "Coffee", "litres": 0.25} for d in range(14)
          for m in COFFEE_MIN]
    rows, _ = server_run(ev, 14 * DAY_MIN, ("acute.caf", "effects.fOff", "acute.cafTol"))
    out = {}
    for name, d in (("day1", 0), ("day14", 13)):
        ks = [d * DAY_MIN + k for k in [0] + _ks(9, DAY_MIN, 10)]
        out[name] = [[age - 24.0 * d, c, f] for _, age, c, f in pick(rows, ks, "acute.caf", "effects.fOff")]
    out["tol14"] = rows[14 * DAY_MIN - 1]["acute.cafTol"]
    return out


BEER_MIN = (60, 80, 100, 120)          # four 0.3 L beers from 08:00, one every 20 minutes


@job
def j_s6b():
    ev = [{"minute": m, "kind": "drink", "fluid": "Beer", "litres": 0.3} for m in BEER_MIN]
    rows, _ = server_run(ev, DAY_MIN, ("acute.bac", "effects.intoxTarget", "acute.hang", "acute.hangH"))
    pts = pick(rows, [0] + _ks(9, DAY_MIN, 10), "acute.bac", "effects.intoxTarget", "acute.hang")
    return {"points": [p for p in pts if None not in p]}     # the first drain's record carries no effects yet


SHORT_NIGHT = 1                        # the night after day 1 runs 03:00-07:00


def _s6c_sleep(days):
    ev = []
    for d in range(days):
        start = d * DAY_MIN + (20 * 60 if d == SHORT_NIGHT else 16 * 60)     # 23:00, or 03:00 for the short night
        ev.append({"minute": start, "kind": "sleep", "asleep": True})
        ev.append({"minute": (d + 1) * DAY_MIN, "kind": "sleep", "asleep": False})
    return ev


@job
def j_s6c():
    """S6c: sleep on; nights 23:00-07:00 except the night after day 1 (03:00-07:00); meals at the request."""
    days = 4
    ev = _s6c_sleep(days) + request_meals(days) + autodrops(days)
    rows, be = server_run([e for e in ev if e["minute"] < days * DAY_MIN], days * DAY_MIN, ("acute.debtH",),
                          sleep_allowed=True)
    K = be.K
    return {"points": [[age / 24.0, float(K.satiety.sleepFactor(d)), d]
                       for _, age, d in pick(rows, [0] + _ks(59, days * DAY_MIN, 60), "acute.debtH")]}


EXE_PATH = "_G.NutritionRevamp.server.fitness.exeType.admin"
SET_START, SET_MIN = 120, 30           # a burpee set from 09:00 for 30 minutes


@job
def j_sx2():
    ev = [{"minute": SET_START, "kind": "activity", "exercising": True},
          {"minute": SET_START, "kind": "setpath", "path": EXE_PATH, "value": "burpees"},
          {"minute": SET_START + SET_MIN, "kind": "activity", "exercising": False},
          {"minute": SET_START + SET_MIN, "kind": "setpath", "path": EXE_PATH, "value": None}]
    end = SET_START + SET_MIN + 121
    rows, _ = server_run(ev, end, ("satiety.S", "body.met"))
    mets = sorted({r["body.met"] for r in rows[SET_START:SET_START + SET_MIN]})
    after = [[k + 1 - (SET_START + SET_MIN), h, s] for k, _, h, s in
             pick(rows, _ks(SET_START + SET_MIN - 1, end, 5), "HUNGER", "satiety.S")]
    return {"set_mets": mets, "start_hunger": rows[SET_START - 1]["HUNGER"], "points": after}


@job
def j_sh1():
    M = _kt("test_satiety_meal_studies")
    return {"minutes": list(M.callahan(KHost()))}


@job
def j_st2():
    S = _kt("test_sodium_balance")
    days, _ = S.simulate(5, 0.0)
    out, prev = [], 0.0
    for i, d in enumerate(days):
        out.append([i + 1, d["na_end"] - prev])
        prev = d["na_end"]
    return {"points": out}


# the long vanilla runs (the 10-minute rust pass makes ten years about half a million segments)

def sets_events(days, per_week=20.0, start_day=0.0):
    """One push-up set to exhaustion every 168 / per_week game hours over [start_day, days) (the source map's 20 sets
    a week spread evenly: 1043 sets a year from hour 0, 412,980 XP at the year's end at factor 1)."""
    if per_week <= 0:
        return []
    step = 168.0 / per_week
    out, t = [], start_day * 24.0
    while t <= days * 24.0 + 1e-9:
        out.append({"t_h": t, "kind": "exercise", "mode": "pushups"})
        t += step
    return out


def vanilla_strength(days, factor, events, start_level=5):
    sim = VM.simulate({"hours": days * 24.0, "dt_min": DAY_MIN, "events": events,
                       "start": {"strength_level": start_level}, "settings": {"protein_factor": factor}})
    return [[t / 24.0, lv, xp] for (t, lv), (_, xp) in zip(sim["strength_level"], sim["strength_xp"])]


@job
def j_vanilla_s4b():
    """Ten years at 20 sets a week, the protein factor pinned at 1.5: every 7th day, the first day at level 10 and
    the first day after it below 10 (rust returning once a capped set's XP is discarded), off the daily points."""
    days = vanilla_strength(3650, 1.5, sets_events(3650))
    reach = next(d for d, lv, _ in days if lv >= 10)
    dip = next((d for d, lv, _ in days if d > reach and lv < 10), None)
    return {"days": days[::7], "reach": reach, "dip": dip}


@job
def j_vanilla_s4c():
    ev = sets_events(365 - 1e-6) + sets_events(910, start_day=730)
    return {"days": vanilla_strength(910, 1.0, ev)}


# ======================================================================================================================
# The Strength day (K.strength.day once a game day on server_host.Host, the call pattern of test_strength_day._days)
# ======================================================================================================================

TDEE = 2600.0                          # the strength oracles' TDEE
PERFECT = (20.0, 2.0, 260.0)           # the README's perfect training: S 20, p 2.0, E +10 % of TDEE


def strength_days(schedule, muscle=None, weight=None, every=1):
    """The no-pick (or a pick's) creation body stepped by K.strength.day through schedule [(days, S, p, E)] at TDEE,
    ts 1, no alcohol, P = K.strength.DEFAULTS: [[day, L, written, lm, lx, fm, cap level]] at day 0 and every `every`
    days (the last day always). L is K.strength.level(lm, N0, T, P); written is K.strength.heldLevel(L, the level
    last written), the creation's own write first (levelDue)."""
    h = KHost()
    K = h.K
    P = K.strength.DEFAULTS
    body = K.body.new(K.body.create(muscle, weight, P, 1, 0), 1, 0)
    total = sum(n for n, *_ in schedule)

    def row(day, L, w):
        cap = float(K.strength.level(body.Fc, body.N0, P.Tmax, P))
        return [day, float(L), int(w), float(body.lm), float(body.lx), float(body.fm), cap]

    L = K.strength.level(body.lm, body.N0, body.T, P)
    wrote = K.strength.heldLevel(L, None)[0]
    out = [row(0, L, wrote)]
    day = 0
    for n, S, p, E in schedule:
        for _ in range(n):
            K.strength.day(body, S, p, E, TDEE, 0.0, P, 1.0)
            day += 1
            L = K.strength.level(body.lm, body.N0, body.T, P)
            wrote = K.strength.heldLevel(L, wrote)[0]
            if day % every == 0 or day == total:
                out.append(row(day, L, wrote))
    return out


def s_inputs(schedule, **kw):
    d = {"function": "strength_days", "schedule": [list(x) for x in schedule], "tdee": TDEE, "ts": 1.0,
         "P": "K.strength.DEFAULTS"}
    d.update(kw)
    return d


# ======================================================================================================================
# The series
# ======================================================================================================================

H = "game hours"
DAYS = "game days"
HUNGER = "hunger (0-1)"


def every_n(pts, n):
    return pts[::n] + ([pts[-1]] if (len(pts) - 1) % n else [])


# ---- H1 --------------------------------------------------------------------------------------------------------------

def s_h1():
    r = VM.simulate({"hours": 6.0, "dt_min": 10.0, "start": {"hunger": 0.25},
                     "events": [{"t_h": 0.0, "kind": "eat", "hunger_script": -24.0}]})
    b = VM.simulate({"hours": 1.0, "dt_min": 1.0, "start": {"hunger": 0.10},
                     "events": [{"t_h": 0.0, "kind": "eat", "hunger_script": -24.0}]})
    freeze = next(t for t, x in b["food_timer"] if t > 0 and x <= 0.0) * 60.0
    k = result("j_h1")
    return [
        series("H1-v-model", "Vanilla, from the game's code", H, HUNGER, "vanilla-model", r["hunger"],
               vmodel("VM1", "VM3", "VM4"),
               "HUNGER 0.25 at the eat of a whole Base.CannedBologneseOpen (-0.24, not cooked); after it HUNGER reads "
               "0.01, above its minimum, so the food-eaten timer is not filled and hunger rises at once. The second "
               "arm (an eat at 0.10, hunger to 0, timer 3120) freezes hunger for %.1f game minutes." % freeze),
        series("H1-m-kernel", "Nutrition Revamp, simulated by the mod's code", H, HUNGER, "kernel", k["points"],
               kernel({"replay": "fresh record from 07:00, no food until the written HUNGER first reaches 0.25, then a "
                                 "whole Base.CannedBologneseOpen", "request_minute": k["request_minute"],
                       "eat": eat(0, "Base.CannedBologneseOpen"), "sleep_allowed": False}, "x361"),
               "The mod's replay from the request (x = 0 the read at the request, before the eat). x361's live meal "
               "was a 650 kcal mixed TKX.Mixed650, not this one: its points are drawn on SH1."),
    ]


# ---- H2 --------------------------------------------------------------------------------------------------------------

def _mixed_eat(t_h, kcal):
    return {"t_h": t_h, "kind": "eat", "hunger_change": 0.0, "calories": kcal, "proteins": kcal * MIXED["p"] / 4,
            "carbs": kcal * MIXED["c"] / 4, "lipids": kcal * MIXED["f"] / 9}


def s_h2():
    ev = [_mixed_eat(24.0 * d + h, 500.0) for d in range(30) for h in (0.0, 5.0, 11.0)]
    r = VM.simulate({"hours": 720.0, "dt_min": DAY_MIN, "start": {"weight_kg": 80.0, "calories": 0.0}, "events": ev})
    days = result("j_h2")["days"]
    inp = {"replay": "30 days: meal events size 500 MIXED at 07, 12, 18; autodrop 600 g at 08, 12, 16, 20",
           "read": "each 07:00 day close", "sleep_allowed": False}
    note = "From the mod's no-trait creation body (lean 52.02 kg, fat 13.005 kg), sleep off."
    return [
        series("H2-v-model", "Vanilla, from the game's code", DAYS, "kg", "vanilla-model",
               [[t / 24.0, w] for t, w in r["weight_kg"]], vmodel("VM6", "VM7", "VM8"),
               "80 kg, calorie store 0, three 500 kcal mixed meals at 07, 12 and 18 (15/50/35 %% energy), awake idle "
               "all day: the idle day burns %.1f kcal at 80 kg, so the store climbs past the 1000 kcal gain threshold."
               % (VM.burn_rate() * 86400)),
        series("H2-m-fat", "Fat mass, simulated by the mod's code", DAYS, "kg", "kernel",
               [[a / 24.0, fm] for _, a, fm, lm, lx in days], kernel(dict(inp, path="body.fm"), "x434"), note),
        series("H2-m-lean", "Lean mass, simulated by the mod's code", DAYS, "kg", "kernel",
               [[a / 24.0, lm + lx] for _, a, fm, lm, lx in days], kernel(dict(inp, path="body.lm + body.lx"), "x434"),
               note),
        series("H2-m-total", "Body mass, simulated by the mod's code", DAYS, "kg", "kernel",
               [[a / 24.0, fm + lm + lx] for _, a, fm, lm, lx in days],
               kernel(dict(inp, path="body.fm + body.lm + body.lx"), "x435"),
               note + " The weight the mod writes (README, The body)."),
    ]


# ---- H3, S4, SS1, SB1 ------------------------------------------------------------------------------------------------

LEVEL = "Strength level"


def _vs(days, factor, per_week=20.0):
    return vanilla_strength(days, factor, sets_events(days, per_week))


def s_h3():
    sched = [(365,) + PERFECT]
    d = strength_days(sched)
    x1, x15 = _vs(365, 1.0), _vs(365, 1.5)
    reach = next((day for day, lv, _ in x15 if lv >= 10), None)
    inp = s_inputs(sched)
    return [
        series("H3-v-model-x1", "Vanilla, protein factor 1", DAYS, LEVEL, "vanilla-model",
               [[day, lv] for day, lv, _ in x1], vmodel("VM11", "VM12"),
               "20 push-up sets a week, one every 8.4 game hours from the first hour, 360 XP a set at the protein "
               "factor pinned at 1: level 9 at the year's end (%d XP). A pure extrapolation of one measured set."
               % round(x1[-1][2])),
        series("H3-v-model-x15", "Vanilla, protein factor 1.5", DAYS, LEVEL, "vanilla-model",
               [[day, lv] for day, lv, _ in x15], vmodel("VM11", "VM12"),
               "The same sets with the protein factor pinned at 1.5 (a protein store between 50 and 300, #2112, "
               "code only): level 10 on day %d." % reach),
        series("H3-m-level", "Nutrition Revamp, the body's level", DAYS, LEVEL, "kernel",
               [[r[0], r[1]] for r in d], kernel(inp, "x435"),
               "The no-pick creation body, 20 hard sets a week, 2.0 g/kg protein, +260 kcal a day."),
        series("H3-m-written", "Nutrition Revamp, the level shown", DAYS, LEVEL, "kernel",
               [[r[0], r[2]] for r in d], kernel(dict(inp, read="K.strength.heldLevel"), "x435"),
               "The perk the player sees (K.strength.heldLevel: rises at the whole number, #3871)."),
    ]


def s_s4a():
    out = []
    for sid, label, sched in (("S4a-m-perfect", "Perfect: 20 sets, 2.0 g/kg, +260 kcal", [(365, 20.0, 2.0, 260.0)]),
                              ("S4a-m-lowprotein", "Low protein: 0.8 g/kg", [(365, 20.0, 0.8, 260.0)]),
                              ("S4a-m-deficit", "A deficit: -500 kcal", [(365, 20.0, 2.0, -500.0)])):
        d = strength_days(sched)
        out.append(series(sid, label, DAYS, LEVEL, "kernel", [[r[0], r[1]] for r in d],
                          kernel(s_inputs(sched), "x434" if "deficit" in sid else "x435")))
    for sid, label, f in (("S4a-v-model-x1", "Vanilla, protein factor 1", 1.0),
                          ("S4a-v-model-x07", "Vanilla, protein factor 0.7", 0.7)):
        v = _vs(365, f)
        out.append(series(sid, label, DAYS, LEVEL, "vanilla-model", [[day, lv] for day, lv, _ in v],
                          vmodel("VM11", "VM12"),
                          "20 sets a week, the protein factor pinned at %s%s." % (
                              f, " (a protein store below -300, #2112)" if f == 0.7 else "")))
    return out


def s_s4b():
    sched = [(3650,) + PERFECT]
    d = strength_days(sched, every=7)
    j = result("j_vanilla_s4b")
    v, dip = j["days"], j["dip"]
    h = KHost()
    K = h.K
    P = K.strength.DEFAULTS
    nat = float(K.strength.level(P.ffmiNaturalRaw * K.HEIGHT_M * K.HEIGHT_M, 1.0, P.Tmax, P))
    return [
        series("S4b-m-level", "Nutrition Revamp, perfect training", "game years", LEVEL, "kernel",
               [[r[0] / 365.0, r[1]] for r in d], kernel(s_inputs(sched, every=7), "x435")),
        series("S4b-m-cap", "The body's natural cap", "game years", LEVEL, "kernel",
               [[r[0] / 365.0, r[6]] for r in d],
               kernel(s_inputs(sched, every=7, read="K.strength.level(body.Fc, body.N0, P.Tmax, P)"), "x435")),
        series("S4b-v-model", "Vanilla, protein factor 1.5", "game years", LEVEL, "vanilla-model",
               [[day / 365.0, lv] for day, lv, _ in v], vmodel("VM11", "VM12"),
               "20 sets a week at the protein factor pinned at 1.5: level 10 on day %.0f, then capped (#2109). Once "
               "capped a set's XP is discarded, so the rust timer is no longer pushed back: from day %.0f rust takes "
               "XP and the level dips from 10 to 9 between sets (code only, no live reading)." % (j["reach"], dip)),
        series("S4b-study", "Kouri 1995's natural limit", "game years", LEVEL, "study", [[0.0, nat], [10.0, nat]],
               study("S1915"),
               "Kouri's FFMI 25 kg/m2, normalised to 1.80 m, is %.2f at the mod's %.2f m (FFMI - 6.3 x (1.80 - "
               "height), K.strength.DEFAULTS.ffmiNaturalRaw); that lean mass shown as a level by K.strength.level at "
               "T = Tmax." % (float(P.ffmiNaturalRaw), float(K.HEIGHT_M))),
    ]


def s_s4c():
    sched = [(365,) + PERFECT, (365, 0.0, 1.2, 0.0), (180,) + PERFECT]
    d = strength_days(sched, every=5)
    v = result("j_vanilla_s4c")["days"]
    P = KHost().K.strength.DEFAULTS
    R = float(P.R)

    def lvl(S):
        return 5 + 5 * (S - 1) / (R - 1)

    L365 = next(r[1] for r in d if r[0] == 365)
    S365 = 1 + (L365 - 5) * (R - 1) / 5
    return [
        series("S4c-m-kernel", "Nutrition Revamp", DAYS, LEVEL, "kernel", [[r[0], r[1]] for r in d],
               kernel(s_inputs(sched, every=5), "x435"),
               "365 days of perfect training, 365 days without (0 sets, 1.2 g/kg, balance), 180 days of perfect "
               "training. The detraining and regain arms were never closed live (G14)."),
        series("S4c-v-model", "Vanilla", DAYS, LEVEL, "vanilla-model", every_n([[x[0], x[1]] for x in v], 5),
               vmodel("VM11", "VM12"),
               "20 sets a week at the protein factor 1 for a year, none for a year, then again. Rust takes 1 XP a "
               "1200-unit bucket once its timer passes 20 000: the first step comes 48.6 days after the last set and "
               "the level does not move in the year (code only, no live reading)."),
        series("S4c-study-0618", "Detraining for 12 weeks, and the regain", DAYS, LEVEL, "study",
               [[365 + 84, lvl(0.95 * S365)], [365 + 84, lvl(0.85 * S365)], [730 + 56, L365]], study("S0618"),
               "S0618's -5 to -15 % strength after 12 weeks of detraining, from the mod's day-365 strength on the "
               "level scale (K.strength.level is linear in strength), and its under-8-week return to the trained "
               "level on retraining, which the mod's fast regain rests on."),
        series("S4c-study-0078", "Strength after 20 weeks of detraining", DAYS, LEVEL, "study",
               [[365 + 140, 5.0]], study("S0078"),
               "S0078: after 20 weeks of detraining strength stayed above the untrained baseline (drawn as level 5) "
               "while muscle size returned to it; on retraining, trained and untrained legs responded alike (no "
               "muscle-memory advantage)."),
    ]


def s_ss1():
    sets = (0.0, 3.0, 6.0, 10.0, 15.0, 20.0)
    m, v = [], []
    for S in sets:
        d = strength_days([(365, S, 1.6, 260.0)], every=365)
        m.append([S, d[-1][1]])
        vs = _vs(365, 1.0, S) if S > 0 else vanilla_strength(365, 1.0, [])
        v.append([S, vs[-1][1]])
    return [
        series("SS1-m-kernel", "Nutrition Revamp", "hard sets a week", "Strength level after a year", "kernel", m,
               kernel(s_inputs([(365, "S", 1.6, 260.0)], sets=list(sets)), "x435"),
               "1.6 g/kg protein, +260 kcal a day; the body's continuous level."),
        series("SS1-v-model", "Vanilla", "hard sets a week", "Strength level after a year", "vanilla-model", v,
               vmodel("VM11", "VM12"),
               "Push-up sets at the protein factor pinned at 1; with no sets, rust takes level 5 to 4 in the year."),
    ]


def s_sb1():
    out = []
    for sid, label, sched, proof in (
            ("SB1-m-def-rest", "Deficit, untrained", [(60, 0.0, 1.2, -500.0)], "x434"),
            ("SB1-m-def-train", "Deficit, trained", [(60, 12.0, 2.0, -500.0)], "x434"),
            ("SB1-m-sur-rest", "Surplus, untrained", [(60, 0.0, 1.2, 500.0)], "x435"),
            ("SB1-m-sur-train", "Surplus, trained", [(60, 12.0, 2.0, 500.0)], "x435")):
        d = strength_days(sched)
        out.append(series(sid, label, DAYS, "lean kg", "kernel", [[r[0], r[3] + r[4]] for r in d],
                          kernel(s_inputs(sched, read="body.lm + body.lx"), proof),
                          "The no-pick creation body's lean mass, labile lean included."))
    return out


# ---- H4, SN1 ---------------------------------------------------------------------------------------------------------

def s_h4():
    out = []
    items = ",".join(p.split(".")[1] for p in GUIDE_FOODS)
    ids = ",".join(GUIDE_FOODS)
    for tag, field, label, unit in (("kcal", "Calories", "kcal", "kcal per item"),
                                    ("carb", "Carbohydrates", "carbohydrate", "g per item"),
                                    ("fat", "Lipids", "fat", "g per item"), ("pro", "Proteins", "protein", "g per item")):
        key = "Base.{%s}.%s" % (items, field)
        vals = D.read_dataset(FOOD_SCRIPT, key)
        out.append(series("H4-v-" + tag, "Vanilla " + label, "food", unit, "vanilla-model",
                          list(zip(FOOD_LABELS, vals)), dataset(FOOD_SCRIPT, key),
                          "The game's own item scripts (42.21)."))
    for tag, field, label, unit in (("kcal", "calories", "kcal", "kcal per item"), ("carb", "carbs", "carbohydrate",
                                                                                   "g per item"),
                                    ("fat", "lipids", "fat", "g per item"), ("pro", "proteins", "protein", "g per item")):
        key = "items[pz_id={%s}].per_item.%s" % (ids, field)
        vals = D.read_dataset(FOOD_JSON, key)
        out.append(series("H4-m-" + tag, "Nutrition Revamp " + label, "food", unit, "kernel",
                          list(zip(FOOD_LABELS, vals)), dataset(FOOD_JSON, key),
                          "The item pass's values (NR_ItemPass_Food.txt, generated by tools/food_nutrients.py); a whole "
                          "Apple and Bread landed this vector live (x172b, #3182, #3183)."))
    return out


def s_sn1():
    out = []
    ids = ",".join(GUIDE_FOODS)
    for tag, field, label, unit in (("vitC", "vitC", "vitamin C", "mg per item"), ("fibre", "fibre", "fibre",
                                                                                    "g per item"),
                                    ("iron", "iron", "iron", "mg per item"), ("sodium", "sodium", "sodium",
                                                                               "mg per item")):
        key = "items[pz_id={%s}].per_item.%s" % (ids, field)
        out.append(series("SN1-m-" + tag, "Nutrition Revamp " + label, "food", unit, "kernel",
                          list(zip(FOOD_LABELS, D.read_dataset(FOOD_JSON, key))), dataset(FOOD_JSON, key),
                          "Vanilla carries none of these."))
    return out


# ---- S1 --------------------------------------------------------------------------------------------------------------

def s_s1a():
    ev = [{"t_h": h, "kind": "eat", "hunger_script": -18.0} for h in (1.0, 5.0, 9.0, 13.0)]
    r = VM.simulate({"hours": 24.0, "dt_min": 10.0, "start": {"hunger": 0.0}, "events": ev})
    k = result("j_s1a")
    return [
        series("S1a-v-model", "Vanilla, from the game's code", "game hours from 07:00", HUNGER, "vanilla-model",
               r["hunger"], vmodel("VM1", "VM3", "VM4"),
               "HUNGER 0 at 07:00, a Base.TunaTinOpen (-0.18) at 08, 12, 16 and 20."),
        series("S1a-m-kernel", "Nutrition Revamp, simulated by the mod's code", "game hours from 07:00", HUNGER,
               "kernel", k["points"],
               kernel({"replay": "fresh record from 07:00, a whole Base.TunaTinOpen at 08, 12, 16, 20",
                       "eat": eat(0, "Base.TunaTinOpen"), "sleep_allowed": False}, "x362")),
    ]


def s_s1b():
    r = VM.simulate({"hours": 36.0, "dt_min": 10.0, "start": {"hunger": 0.0}})
    k = result("j_s1b")
    return [
        series("S1b-v-model", "Vanilla Hungry moodle", "game hours from a fresh start", "moodle level (0-4)",
               "vanilla-model", r["hungry_level"], vmodel("VM1", "VM5"),
               "From HUNGER 0, no food: levels at %s game hours." % ", ".join(
                   "%.2f" % VM.hours_to_hunger(t) for t in VM.HUNGRY_THRESHOLDS)),
        series("S1b-m-kernel", "Nutrition Revamp energy moodle", "game hours from a fresh start", "moodle level (0-4)",
               "kernel", k["points"],
               kernel({"replay": "fresh record from 07:00, no food, 36 h", "path": SIG,
                       "read": "the thousands digit (test_replay_live_energy.long_fast_levels)",
                       "sleep_allowed": False}, "x405"),
               "The level the server pushes (the bus signature's energy digit)."),
    ]


def s_s1c():
    r = VM.simulate({"hours": 24.0, "dt_min": 10.0, "start": {"thirst": 0.0}})
    k = result("j_s1c")
    return [
        series("S1c-v-model", "Vanilla, from the game's code", H, "thirst (0-1)", "vanilla-model", r["thirst"],
               vmodel("VM5"), "Linear from 0 at 8.0e-6 a game-second."),
        series("S1c-m-kernel", "Nutrition Revamp, simulated by the mod's code", H, "thirst (0-1)", "kernel",
               k["points"], kernel({"replay": "fresh record from 07:00, no drink, 24 h", "path": "THIRST",
                                    "sleep_allowed": False}, "x151t"),
               "Proof x151t is the Plan 4 build (G7); M1 grades THIRST at HEAD."),
    ]


# ---- S2 --------------------------------------------------------------------------------------------------------------

def s_s2a():
    meals = [0.0, 5.0, 11.0]
    ev = [{"t_h": h, "kind": "eat", "hunger_script": -24.0} for h in meals + [13.0]]
    ev += [{"t_h": 13.0 + h, "kind": "eat", "hunger_script": -24.0} for h in (36.0, 40.0, 46.0)]
    r = VM.simulate({"hours": 13.0 + 60.0, "dt_min": 10.0, "start": {"hunger": 0.0}, "events": ev})
    k = result("j_s2a")
    return [
        series("S2a-v-model", "Vanilla, from the game's code", "game hours from the last meal", HUNGER,
               "vanilla-model", [[t - 13.0, x] for t, x in r["hunger"]], vmodel("VM1", "VM3", "VM4"),
               "A Base.CannedBologneseOpen at 07, 12 and 18 and a last at 20:00 that takes HUNGER to 0 (the timer "
               "filled), no food for 36 h, then the same meals at 08, 12 and 18."),
        series("S2a-m-kernel", "Nutrition Revamp, simulated by the mod's code", "game hours from the last meal",
               HUNGER, "kernel", k["points"],
               kernel({"replay": "test_replay_live_oracle.fast_plans() fast arm on the default body",
                       "clock": "minute 0 is 00:00", "sleep_allowed": False}, "x364"),
               "Three warm days at maintenance, day 0 at maintenance, day 1 without food, days 2-3 at the request; "
               "x364's live points fail the admission test (VALIDATION)."),
    ]


def s_s2b():
    k = result("j_s2b")
    return [
        series("S2b-m-kernel", "Nutrition Revamp, simulated by the mod's code", "day after the fast",
               "intake / the fed arm's", "kernel", [["day 2", k["r2"]], ["day 3", k["r3"]]],
               kernel({"replay": "test_replay_live_energy.fast_server()", "body": "the oracle's 70 kg man (MAN)",
                       "sleep": "23:00-07:00, the oracle's protocol"}, "x27g"),
               "Sleep on, 23:00-07:00 (the oracle's protocol); the oracle's 70 kg man, the body its bands were fitted on."),
        series("S2b-study-1613", "Johnstone 2002", "day after the fast", "intake / the fed arm's", "study",
               [["day 2", 12.2 / 10.2]], study("S1613"), "12.2 against 10.2 MJ on the day after a 36 h fast."),
        series("S2b-study-1614", "Clayton 2016", "day after the fast", "intake / the fed arm's", "study",
               [["day 2", 1.07], ["day 3", 1.0]], study("S1614"),
               "7 % more on day 2 and no difference on day 3 after a day at 25 % of requirements."),
    ]


def s_s2c():
    k = result("j_s2c")
    xs = [0.0, k["low_kg"]] + k["kg"]
    ys = [0.0, k["low"] - k["base"]] + [y - k["base"] for y in k["intake"]]
    DO = _kt("deficit_oracles")
    per = DO.S1254_KCAL_PER_KG
    return [
        series("S2c-v-model", "Vanilla, from the game's code", "kg of fat lost", "extra kcal a day", "vanilla-model",
               [[0.0, 0.0], [max(xs), 0.0]], vmodel("VM14"), "No hunger term reads a body store."),
        series("S2c-m-kernel", "Nutrition Revamp, simulated by the mod's code", "kg of fat lost", "extra kcal a day",
               "kernel", list(zip(xs, ys)),
               kernel({"replay": "test_replay_live_energy.fat_loss_server()", "depletions": [0.0, 0.05, 0.25, 0.4,
                                                                                               0.55],
                       "sleep": "23:00-07:00, the oracle's protocol"}, "x436"),
               "The no-trait body's fat set lower; intake at the request over days 2-4 less the full body's; sleep on, "
               "the oracle's protocol."),
        series("S2c-study", "Polidori 2016", "kg of fat lost", "extra kcal a day", "study",
               [[x, per * x] for x in (0.0, max(xs))], study("S1254"),
               "About 100 kcal a day per kg of weight lost, 125 per kg of fat (S2208, S2206; "
               "deficit_oracles.S1254_KCAL_PER_KG); the oracle's band is a factor of 1.5 either way."),
    ]


def s_s2d():
    rh = VM.simulate({"hours": 72.0, "dt_min": 60.0, "start": {"hunger": 0.0},
                      "events": [{"t_h": float(h), "kind": "drink", "fluid": "water", "litres": 0.25}
                                 for h in range(4, 72, 4)]})
    health = []
    for t, x in rh["health"]:
        health.append([t, x])
        if x <= 0:
            break
    rw = VM.simulate({"hours": 90 * 24.0, "dt_min": DAY_MIN, "start": {}})
    samples = read("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].weight")
    ages = read("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].worldAge")
    k = result("j_s2d")
    fine = VM.simulate({"hours": 72.0, "dt_min": 1.0, "start": {"hunger": 0.0},
                        "events": [{"t_h": float(h), "kind": "drink", "fluid": "water", "litres": 0.25}
                                   for h in range(4, 72, 4)]})
    death = next((t for t, x in fine["health"] if x <= 0), None)
    return [
        series("S2d-v-model-health", "Vanilla health", "game hours from the last meal", "health", "vanilla-model",
               health, vmodel("VM1", "VM5", "VM10"),
               "HUNGER from 0, no food, water every 4 h; level 4 at 34.84 h, then -3.564 health a game hour at "
               "DayLength 4 with no regeneration: death at %.1f h." % death),
        series("S2d-v-model-weight", "Vanilla weight", DAYS, "kg", "vanilla-model",
               [[t / 24.0, w] for t, w in rw["weight_kg"]], vmodel("VM6", "VM7", "VM8"),
               "A fresh 80 kg character (calorie store 800), no food: the store falls to its -2200 floor, then the "
               "loss runs at 0.646 kg a game day; no weight floor is modelled. It reads as if hunger were held (the "
               "live control pinned it): unheld, the character dies of hunger in %.1f game hours (S2d-v-model-health)."
               % death),
        series("S2d-v-live-weight", "Vanilla weight, measured", DAYS, "kg", "vanilla-live",
               [[(a - ages[0]) / 24.0, w] for a, w in zip(ages, samples)],
               artifact("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].weight"),
               "Build 42.20.4, vanilla Nutrition on, hunger pinned (a control, #0500); x from test.samples[*].worldAge."),
        series("S2d-m-mass", "Nutrition Revamp body mass", DAYS, "kg", "kernel",
               [[a / 24.0, fm + lm + lx] for _, a, fm, lm, lx in k["days"]],
               kernel({"replay": "90 days, no food, autodrop 600 g at 08, 12, 16, 20",
                       "path": "body.fm + body.lm + body.lx", "sleep_allowed": False}, "x434"),
               "The mod's no-trait creation body; its HUNGER never passed %.4f in the replay (#3074, #3123)."
               % k["hunger_max"]),
    ]


# ---- S3 --------------------------------------------------------------------------------------------------------------

VITC_CLINICAL = 0.15                   # NR_Data_Records vitC ladder[3]


def s_s3a():
    k = result("j_s3a")
    firsts = sorted((d, n) for n, d in k["first_grade2_day"].items() if n != "vitC")[:2]
    inp = {"replay": "60 days, four Base.TunaTinOpen a day at 08, 12, 16, 20, autodrop 600 g at 08, 12, 16, 20",
           "eat": eat(0, "Base.TunaTinOpen"), "sleep_allowed": False}
    others = "; ".join("%s marginal from day %.0f" % (n, d) for d, n in firsts) or "no other record marginal"
    return [
        series("S3a-m-pool", "Vitamin C store", DAYS, "vitamin C store (0-1)", "kernel",
               [[a / 24.0, p] for _, a, p in k["vitC_p"]], kernel(dict(inp, path="nutrients.vitC.p"), "x151r"),
               "Proof x151r (the Plan 4 build, OnsetSpeed 30: G11); vitamin C is never scaled by OnsetSpeed. The "
               "first other records to reach grade 2 on this diet: %s." % others),
        series("S3a-m-grade", "Vitamin C grade", DAYS, "grade (1 replete - 4 clinical)", "kernel",
               [[a / 24.0, g] for _, a, g in k["vitC_g"]], kernel(dict(inp, path="nutrients.vitC.g"), "x151r")),
        series("S3a-study-0224", "Padayatty 2016: one self-experimenter", DAYS, "vitamin C store (0-1)", "study",
               [[161.0, VITC_CLINICAL]], study("S0224"),
               "161 days to scurvy signs, drawn at the clinical store 0.15."),
        series("S3a-study-0225", "Hodges 1971 (controlled series)", DAYS, "vitamin C store (0-1)", "study",
               [[40.0, VITC_CLINICAL]], study("S0225"),
               "About 40 days to scurvy signs, drawn at the clinical store 0.15."),
    ]


def s_s3b():
    u = read("x34r", "rows.json", "row13.days.days.{0,1,2,3,4}.server_U")
    b = read("x34r", "rows.json", "row13.days.days.{0,1,2,3,4}.moodLast_b")
    for r in ("x341", "x342", "x343"):
        adm(r)
    k = result("j_s3b")
    note = ("Days 0-4 from x341 and x342, which pass the admission test; x343's days 5-6 fail it and are not drawn. "
            "The eats were TKX.Mono450.")
    return [
        series("S3b-m-live-U", "Unhappiness, measured", DAYS, "unhappiness (0-100)", "live",
               list(enumerate(u)), artifact("x34r", "rows.json", "row13.days.days.{0,1,2,3,4}.server_U"), note),
        series("S3b-m-live-B", "Boredom target, measured", DAYS, "boredom (0-100)", "live",
               list(enumerate(b)), artifact("x34r", "rows.json", "row13.days.days.{0,1,2,3,4}.moodLast_b"),
               note + " BOREDOM itself is reset-bounded by the driver, so the remembered target is plotted."),
        series("S3b-m-kernel-U", "Unhappiness, simulated by the mod's code", DAYS, "unhappiness (0-100)", "kernel",
               k["points"],
               kernel({"replay": "7 days of four Base.TunaTinOpen a day, then 7 days of four foods a day rotating "
                                 "through " + ", ".join(VARIED), "path": "UNHAPPINESS", "sleep_allowed": False},
                      "x343"), "Proof: the x34 chain (#3683)."),
    ]


def s_s3c():
    k = result("j_s3c")
    return [
        series("S3c-m-pool", "Vitamin C store", DAYS, "vitamin C store (0-1)", "kernel",
               [[a / 24.0, p] for _, a, p in k["vitC_p"] if a / 24.0 >= 40.0 - 1e-9],
               kernel({"replay": "S3a's diet to day 80, one Base.Orange a day at 10:00 from day 45",
                       "orange": eat(0, "Base.Orange"), "path": "nutrients.vitC.p", "sleep_allowed": False}, "x151r")),
        series("S3c-study", "Ververs 2019", DAYS, "vitamin C store (0-1)", "study", [[52.0, VITC_CLINICAL]],
               study("S0229"), "Symptoms improved within one week of treatment (day 45 + 7)."),
    ]


# ---- S5 --------------------------------------------------------------------------------------------------------------

PICKS = ("none", "Strong + Obese", "Weak + Overweight", "Overly Lean", "Weak + Gaunt", "Feeble + Overly Lean")
PICK_V = ((None, None), ("STRONG", "OBESE"), ("WEAK", "OVERWEIGHT"), (None, "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"),
          ("FEEBLE", "UNDERWEIGHT"))
CASES = "{a,b,c,d,e,f}"


def s_s5a():
    out = []
    for sid, label, unit, path in (
            ("S5a-m-live-lean", "Lean mass, measured", "kg", "verdicts.36_%s_body.observed.record.lm" % CASES),
            ("S5a-m-live-fat", "Fat mass, measured", "kg", "verdicts.36_%s_body.observed.record.fm" % CASES),
            ("S5a-m-live-weight", "Body mass, measured", "kg", "verdicts.36_%s_body.observed.derived.mass" % CASES),
            ("S5a-m-live-level", "Strength level, measured", LEVEL,
             "verdicts.36_%s_xp.observed.client_level" % CASES)):
        vals = read("x436", "creation.json", path)
        out.append(series(sid, label, "pick", unit, "live", list(zip(PICKS, vals)),
                          artifact("x436", "creation.json", path), "x436 cases a-f (#3872)."))
    out.append(series("S5a-v-model-weight", "Vanilla weight", "pick", "kg", "vanilla-model",
                      [[p, VM.creation_weight(w)] for p, (_, w) in zip(PICKS, PICK_V)], vmodel("VM9"),
                      "The creation weights by the weight pick; none 80."))
    out.append(series("S5a-v-model-level", "Vanilla Strength level", "pick", LEVEL, "vanilla-model",
                      [[p, VM.start_strength_level(m)] for p, (m, _) in zip(PICKS, PICK_V)], vmodel("VM13", "JT1"),
                      "Seed 5 plus the muscle trait's boost, clamped to [0, 10]: Weak starts at 0; the mod's Weak 1 "
                      "is the mod's own floor."))
    return out


def s_s5b():
    out = []
    inp = {"replay": "90 days from the creation body, meals at the request at 08, 13, 20, autodrop 600 g at 08, 12, "
                     "16, 20", "sleep_allowed": False}
    for name, sid, label in (("strong", "S5b-m-strong-level", "Strong"), ("weak", "S5b-m-weak-level", "Weak"),
                             ("none", "S5b-m-none-level", "No pick")):
        d = result("j_s5b_" + name)["days"]
        traits, perk = S5B[name]
        out.append(series(sid, label + ", the level shown", DAYS, LEVEL, "kernel", [[x[0], x[5]] for x in d],
                          kernel(dict(inp, traits=traits, native_strength=perk, path="body.wroteL"), "x436"),
                          "The written Strength level at each day close (the trait ids are K.strength.MUSCLE_TRAITS')."))
    for name, sid, label in (("gaunt", "S5b-m-gaunt-weight", "Gaunt"), ("overweight", "S5b-m-overfat-weight",
                                                                        "Overfat"),
                             ("none", "S5b-m-none-weight", "No pick")):
        d = result("j_s5b_" + name)["days"]
        traits, perk = S5B[name]
        out.append(series(sid, label + ", body mass", DAYS, "kg", "kernel", [[x[0], x[1] + x[2] + x[3]] for x in d],
                          kernel(dict(inp, traits=traits, native_strength=perk, path="body.fm + body.lm + body.lx"),
                                 "x436"),
                          "Gaunt is VERY_UNDERWEIGHT and Overfat OVERWEIGHT (K.traits.WEIGHT_TRAITS)."))
    v = VM.simulate({"hours": 90 * 24.0, "dt_min": DAY_MIN, "start": {"strength_level": 5}})
    fine = VM.simulate({"hours": 50 * 24.0, "dt_min": 10.0, "start": {"strength_level": 5}})
    first = next((t / 24.0 for t, lv in fine["strength_level"] if lv < 5), None)
    out.append(series("S5b-v-model-level", "Vanilla, no pick", DAYS, LEVEL, "vanilla-model",
                      [[t / 24.0, lv] for t, lv in v["strength_level"]], vmodel("VM11", "VM12", "VM13"),
                      "No XP: a fresh character's rust timer climbs from -50 000 and its first rust step takes level 5 "
                      "to 4 at day %.1f (code only, no live reading)." % first))
    return out


def s_s5c():
    g = result("j_s5b_gaunt")["days"][:31]
    n = result("j_s5b_none")["days"][:31]
    es = read("x436", "creation.json", "verdicts.36_{d,e,f}_hunger.observed.es")
    inp = {"replay": "S5b's", "path": "body.energyState", "sleep_allowed": False}
    return [
        series("S5c-m-gaunt", "Gaunt", DAYS, "energy state", "kernel", [[x[0], x[6]] for x in g],
               kernel(dict(inp, traits=S5B["gaunt"][0]), "x436")),
        series("S5c-m-none", "No pick", DAYS, "energy state", "kernel", [[x[0], x[6]] for x in n],
               kernel(dict(inp, traits=[]), "x436")),
        series("S5c-m-live", "Thin starts, measured at creation", DAYS, "energy state", "live",
               [[0.0, v] for v in es], artifact("x436", "creation.json", "verdicts.36_{d,e,f}_hunger.observed.es"),
               "Overly Lean, Weak + Gaunt and Feeble + Overly Lean after creation (#3874)."),
        series("S5c-v-model", "Vanilla", DAYS, "energy state", "vanilla-model", [[0.0, 1.0], [30.0, 1.0]],
               vmodel("VM14"), "Hunger reads no weight or fat: a flat 1."),
    ]


# ---- S6 --------------------------------------------------------------------------------------------------------------

def s_s6a():
    k = result("j_s6a")
    cup = VM.fatigue_change(0.25)
    inp = {"replay": "0.25 L Coffee at 08, 12, 16 every day for 14 days", "sleep_allowed": False}
    return [
        series("S6a-m-day1", "Caffeine on day 1", "game hours from 07:00", "caffeine (mg)", "kernel",
               [[x, c] for x, c, f in k["day1"]], kernel(dict(inp, path="acute.caf", day=1), "x161f"),
               "Proof x151r (the 5.0 h half-life, #2982) and x161f (#3077), the Plan 4-5 builds (G10); M2 reads it "
               "at HEAD."),
        series("S6a-m-day14", "Caffeine on day 14", "game hours from 07:00", "caffeine (mg)", "kernel",
               [[x, c] for x, c, f in k["day14"]], kernel(dict(inp, path="acute.caf", day=14), "x161f"),
               "The tolerance (tau 7 days) reads %.3f by day 14; the 5 h half-life and the tolerance are game choices "
               "on open rows (S0851, S1123), so no study is drawn." % k["tol14"]),
        series("S6a-v-model", "Vanilla FATIGUE per cup", "game hours from 07:00", "fatigue change", "vanilla-model",
               [[1.0, cup], [5.0, cup], [9.0, cup]], vmodel("VM15"),
               "-0.025 a 0.25 L cup, the same on day 14. It holds only with sleep allowed and needed: under the "
               "display default (sleep off) vanilla resets FATIGUE every update (#3009)."),
    ]


def s_s6b():
    ev = [{"t_h": m / 60.0, "kind": "drink", "fluid": "beer", "litres": 0.3} for m in BEER_MIN]
    r = VM.simulate({"hours": 24.0, "dt_min": 10.0, "start": {}, "events": ev})
    k = result("j_s6b")["points"]
    inp = {"replay": "four 0.3 L Beer at 08:00, 08:20, 08:40, 09:00", "sleep_allowed": False}
    return [
        series("S6b-v-model", "Vanilla intoxication", H, "intoxication (0-100)", "vanilla-model", r["intoxication"],
               vmodel("VM16"), "400 x alcohol x the hunger factor a drink; decay 45.36 a game hour at DayLength 4."),
        series("S6b-m-bac", "Blood alcohol", H, "blood alcohol (%)", "kernel", [[a, b] for _, a, b, i, hg in k],
               kernel(dict(inp, path="acute.bac"), "x161f")),
        series("S6b-m-intox", "Intoxication the mod writes", H, "intoxication (0-100)", "kernel",
               [[a, i] for _, a, b, i, hg in k], kernel(dict(inp, path="effects.intoxTarget"), "x161f"),
               "The writer's target (#3086)."),
        series("S6b-m-hangover", "Hangover", H, "hangover (0 or 1)", "kernel", [[a, hg] for _, a, b, i, hg in k],
               kernel(dict(inp, path="acute.hang"), "x161f"),
               "No live reading of a hangover exists yet (G10, G17); M2 reads it."),
    ]


def s_s6c():
    k = result("j_s6c")["points"]
    debt = read("x30g", "rows.json", "row11.closes[*].debt_after")
    ages = read("x30g", "rows.json", "row11.closes[*].age_after")
    for r in ("x301", "x302"):
        adm(r)
    return [
        series("S6c-m-kernel", "Nutrition Revamp hunger factor", DAYS, "hunger factor", "kernel",
               [[d, f] for d, f, _ in k],
               kernel({"replay": "sleep on: nights 23:00-07:00, the night after day 1 03:00-07:00; meals at the "
                                 "request", "path": "acute.debtH", "read": "K.satiety.sleepFactor(acute.debtH)",
                       "sleep_allowed": True}, "x30g")),
        series("S6c-m-live", "Sleep debt, measured", DAYS, "sleep debt (h)", "live",
               [[a / 24.0, d] for a, d in zip(ages, debt)], artifact("x30g", "rows.json", "row11.closes[*].debt_after"),
               "Sleep on. x301 and x302's debts at each window close; they pass the admission test on the sleep "
               "kernel; x from row11.closes[*].age_after."),
        series("S6c-v-model", "Vanilla", DAYS, "hunger factor", "vanilla-model", [[0.0, 1.0], [4.0, 1.0]],
               vmodel("VM14"), "No sleep term reads hunger: a flat 1."),
        series("S6c-study", "Brondel 2010", DAYS, "intake / the rested day's", "study",
               [[1.0 + 17.0 / 24.0, 1.22], [2.0 + 16.0 / 24.0, 1.22]], study("S1566"),
               "22 % more energy eaten on the day after one 4 h night, drawn over that day."),
    ]


# ---- systems ---------------------------------------------------------------------------------------------------------

def s_se1():
    adm("x363")
    liq = read("x363", "minute-ring-admin-1.json", 'rows_list[*]["stomach.liquid"]')
    fill = read("x363", "minute-ring-admin-1.json", "rows_list[*].stomachFill")
    ages = read("x363", "minute-ring-admin-1.json", "rows_list[*].age")
    ss = read("x363", "minute-ring-admin-1.json", "rows_list[*].s")
    a0 = ages[0]
    rep = result("j_adm_x36")["x363"]["rows"]
    kern = [[(rep[s][0] - a0) * 60.0, rep[s][1]] for s in sorted(rep, key=float)
            if rep[s][1] is not None and rep[s][0] is not None]
    note = "x363 (mod 7093079b) passes the admission test; minutes from the ring's first row (page 1)."
    return [
        series("SE1-m-live-liquid", "Liquid in the stomach, measured", "game minutes", "grams", "live",
               [[(a - a0) * 60.0, x] for a, x in zip(ages, liq) if x is not None][::5],
               artifact("x363", "minute-ring-admin-1.json", 'rows_list[*]["stomach.liquid"]'), note),
        series("SE1-m-live-fill", "Stomach fill, measured", "game minutes", "fill (0-1)", "live",
               [[(a - a0) * 60.0, x] for a, x in zip(ages, fill) if x is not None][::5],
               artifact("x363", "minute-ring-admin-1.json", "rows_list[*].stomachFill"), note),
        series("SE1-m-kernel-fill", "Stomach fill, simulated", "game minutes", "fill (0-1)", "kernel", kern[::5],
               kernel({"replay": "x363's events.json from its start.json at HEAD", "path": "stomachFill",
                       "sleep_allowed": False}, "x363"), "Ring s %s to %s." % (ss[0], ss[-1])),
    ]


def s_sh1():
    k = result("j_sh1")["minutes"]
    kc = (190.0, 400.0, 825.0)
    adm("x361")
    live = read("x36g", "grade.json", "sessions.x361.readings.readings.{C650_request_vs_anchor,C400_held_vs_180}.live_min")
    return [
        series("SH1-m-kernel", "Nutrition Revamp, simulated", "meal kcal", "minutes to the hunger request", "kernel",
               list(zip(kc, k)), kernel({"replay": "test_satiety_meal_studies.callahan()",
                                         "preloads_kcal": list(kc), "clock": "09:00"}, "x361"),
               "Callahan's liquid preloads at 09:00, from the request."),
        series("SH1-m-live", "Measured", "meal kcal", "minutes to the hunger request", "live",
               [[650.0, live[0]], [400.0, live[1]]],
               artifact("x36g", "grade.json",
                        "sessions.x361.readings.readings.{C650_request_vs_anchor,C400_held_vs_180}.live_min"),
               "x361: a 650 kcal mixed meal at the request (minutes to the next request) and a 400 kcal one (minutes "
               "held below the request); x361 passes the admission test."),
        series("SH1-study-1247", "Callahan 2004", "meal kcal", "minutes to the hunger request", "study",
               [[190.0, 247.0], [400.0, 286.0], [825.0, 321.0]], study("S1247"),
               "Preloads of 7.5, 16 and 33 % of daily energy, drawn at the replay's 190, 400 and 825 kcal."),
        series("SH1-study-1248", "Cummings 2004", "meal kcal", "minutes to the hunger request", "study",
               [[650.0, 320.0], [650.0, 425.0]], study("S1248"),
               "320-425 min from a scheduled lunch to a freely requested dinner; the lunch's energy is not given, so "
               "the range is drawn at the 650 kcal meal #3700's 240-300 min anchor reads."),
    ]


def s_sh2():
    k = result("j_sh2")
    adm("x276")
    return [
        series("SH2-m-kernel", "Nutrition Revamp, simulated", "arm", "mean hunger over 24 h / three meals'", "kernel",
               [["three meals", 1.0], ["six meals", k["six"] / k["three"]]],
               kernel({"replay": "x276's events.json from its start.json at HEAD (six meals) against its three-meal "
                                 "arm (x27_grade.row8)", "window": "world age 25 to 49"}, "x276"),
               "x276's start record loads at HEAD; its own live means fail the admission test and are not drawn."),
        series("SH2-study", "Ohkawara 2013", "arm", "mean hunger over 24 h / three meals'", "study",
               [["three meals", 1.0], ["six meals", 41850.0 / 36612.0]], study("S1608"),
               "Hunger AUC 41850 on six meals against 36612 on three."),
    ]


def s_st1():
    r = VM.simulate({"hours": 10.0, "dt_min": 10.0, "start": {"thirst": 0.0}})
    k = [p for p in result("j_s1c")["points"] if p[0] <= 10.0 + 1e-9]
    return [
        series("ST1-v-model", "Vanilla, from the game's code", H, "thirst (0-1)", "vanilla-model", r["thirst"],
               vmodel("VM5")),
        series("ST1-m-kernel", "Nutrition Revamp, simulated", H, "thirst (0-1)", "kernel", k,
               kernel({"replay": "fresh record from 07:00 at rest, no drink, the first 10 h", "path": "THIRST",
                       "sleep_allowed": False}, "x151t"), "Proof as S1c (G7)."),
    ]


def s_st2():
    path = "sodium.by_day.{1,2,3,4,5}.na_change_per_24h"
    na = read("x28g", "rows.json", path)
    for r in ("x281", "x282", "x283", "x284"):
        adm(r)
    return [
        series("ST2-m-live-na", "Body sodium, measured", DAYS, "mmol a day", "live", list(zip(range(1, 6), na)),
               artifact("x28g", "rows.json", path),
               "x281-x284 pass the admission test on the record's sodium balance (exact at HEAD)."),
        series("ST2-m-kernel", "Nutrition Revamp, simulated", DAYS, "mmol a day", "kernel", result("j_st2")["points"],
               kernel({"function": "test_sodium_balance.simulate(days=5, na_day=0)",
                       "body": "the 80 kg reference man"}, "x28g")),
    ]


def s_sm1():
    adm("x343")
    rows = result("j_adm_x34")["x343"]["rows"]
    a0 = read("x34r", "rows.json", "row13.release.from_age")
    a1 = read("x34r", "rows.json", "row13.release.to_age")
    pts = [[(v[0] - a0), v[1]] for s, v in sorted(rows.items(), key=lambda kv: float(kv[0]))
           if v[0] is not None and a0 <= v[0] <= a1 and v[1] is not None]
    return [
        series("SM1-m-kernel", "Nutrition Revamp, simulated", "game hours after the last repeat", "unhappiness",
               "kernel", every_n(pts, 30),
               kernel({"replay": "x343's events.json from its start.json at HEAD", "path": "UNHAPPINESS",
                       "window": "row13.release from_age to to_age", "sleep_allowed": False}, "x343"),
               "x343's own ring fails the admission test at HEAD (VALIDATION), so the live line is not drawn."),
    ]


def _band_y(name):
    return {"EMACIATED": -3, "VERY_UNDERWEIGHT": -2, "UNDERWEIGHT": -1, None: 0, "OVERWEIGHT": 1, "OBESE": 2}[name]


SB2_BODIES = (("lean 90 kg", 76.5, 13.5), ("average 80 kg", 64.0, 16.0), ("soft 85 kg", 59.5, 25.5))


def s_sb2():
    h = KHost()
    K = h.K
    m = []
    for name, lm, fm in SB2_BODIES:
        b = h.table({"lm": lm, "fm": fm, "fatT": 0, "thinT": 0})
        K.traits.axes(b, 1)
        m.append([name, -int(b.thinT) if b.thinT > 0 else int(b.fatT)])
    note = ("Lean 90 kg: 76.5 kg lean, 13.5 kg fat (15 %); average 80 kg: 64 and 16 (20 %, the no-pick share); soft "
            "85 kg: 59.5 and 25.5 (30 %). The y scale: -3 Emaciated, -2 Very Underweight, -1 Underweight, 0 none, "
            "1 Overweight, 2 Obese.")
    return [
        series("SB2-v-model", "Vanilla, by weight", "example body", "trait band", "vanilla-model",
               [[n, _band_y(VM.weight_band(lm + fm))] for n, lm, fm in SB2_BODIES], vmodel("VM9"), note),
        series("SB2-m-kernel", "Nutrition Revamp, by fat and lean", "example body", "trait band", "kernel", m,
               kernel({"function": "K.traits.axes(body, 1)", "bodies": [list(b) for b in SB2_BODIES]}, "x436"),
               note + " The fat axis is scaled by lean (#3856)."),
    ]


SX1_V = (("asleep", "asleep", 1.0), ("idle", "idle", 1.0), ("walking", "walking", 1.0), ("running", "running", 1.0),
         ("sprinting", "sprinting", 1.0), ("Fitness", "idle", VM.FITNESS_MOD), ("reading", "idle", 0.5))
SX1_M = (("asleep", "COMPENDIUM", "Sleeping"), ("idle", "COMPENDIUM", "Default"),
         ("walking", "COMPENDIUM", "Walking5kmh"), ("running", "COMPENDIUM", "Running10kmh"),
         ("sprinting", "COMPENDIUM", "Running15kmh"), ("reading", "BAND_MET", 0.5),
         ("squats", "EXERCISE_MET", "squats"), ("push-ups", "EXERCISE_MET", "pushups"),
         ("sit-ups", "EXERCISE_MET", "situp"), ("burpees", "EXERCISE_MET", "burpees"))
EXE_LABEL = {"squats": "squats", "pushups": "push-ups", "situp": "sit-ups", "burpees": "burpees"}


def s_sx1():
    K = KHost().K
    v = [[n, VM.burn_rate(state, 80.0, mod) * 3600.0] for n, state, mod in SX1_V]
    m = [[n, float(K.energy[t][key]) * 80.0] for n, t, key in SX1_M]
    adm("x37g")
    types = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].type")
    billed = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].billed")
    seen = {}
    for t, b in zip(types, billed):
        seen.setdefault(t, b)
    return [
        series("SX1-v-model", "Vanilla", "activity", "kcal per game hour at 80 kg", "vanilla-model", v, vmodel("VM6"),
               "Fitness and reading are idle under the action's calories modifier (3 and 0.5)."),
        series("SX1-m-kernel", "Nutrition Revamp", "activity", "kcal per game hour at 80 kg", "kernel", m,
               kernel({"tables": "K.energy.COMPENDIUM, BAND_MET, EXERCISE_MET", "classes": [list(x) for x in SX1_M],
                       "kg": 80.0}, "x37g"),
               "MET x 80 kg (1 kcal per kg an hour a MET), a stated derivation: the bill per class."),
        series("SX1-m-live", "Billed live", "activity", "kcal per game hour at 80 kg", "live",
               [[EXE_LABEL.get(t, t), b * 80.0] for t, b in seen.items()],
               artifact("x37g", "grade.json", "sessions.x371.sets[*].bills[*].billed"),
               "x371's billed MET per exercise x 80 kg (#3730); every bill equals the HEAD table (VALIDATION)."),
    ]


def s_sx2():
    k = result("j_sx2")
    if k["set_mets"] != [7.5]:
        raise D.ProvenanceError("SX2's burpee set billed %r, not 7.5 MET" % (k["set_mets"],))
    h0 = k["start_hunger"]
    r = VM.simulate({"hours": 2.5, "dt_min": 5.0, "start": {"hunger": h0},
                     "events": [{"t_h": 0.0, "kind": "exercise", "mode": "action", "calories_modifier":
                                 VM.FITNESS_MOD, "duration_min": float(SET_MIN)}]})
    v = [[t * 60.0 - SET_MIN, x] for t, x in r["hunger"] if t * 60.0 >= SET_MIN - 1e-9]
    return [
        series("SX2-v-model", "Vanilla", "game minutes after the set", HUNGER, "vanilla-model", v,
               vmodel("VM1", "VM2"),
               "From the mod's HUNGER at the set's start (%.4f): vanilla's exercising branch is running or a swing, "
               "not a Fitness set, so hunger rises at the idle rate after it." % h0),
        series("SX2-m-kernel", "Nutrition Revamp", "game minutes after the set", HUNGER, "kernel",
               [[x, hh] for x, hh, s in k["points"]],
               kernel({"replay": "fresh record from 07:00; a 30-minute burpee set from 09:00 (an activity event "
                                 "exercising, a setpath of %s to burpees), then rest" % EXE_PATH, "path": "HUNGER",
                       "billed_met": k["set_mets"], "sleep_allowed": False}, "x29g"),
               "The set billed 7.5 MET a minute (K.energy.EXERCISE_MET.burpees)."),
    ]


def s_sd1():
    h = KHost()
    d, code = scurvy_drain(h)
    per_h = d * 60.0
    days = 100.0 / per_h / 24.0
    adm("x161b")
    live = read("x161b", "body.json", "summaries.I.health.per_game_h")
    return [
        series("SD1-m-kernel", "Nutrition Revamp", DAYS, "health", "kernel",
               [[x, max(0.0, 100.0 - per_h * 24.0 * x)] for x in [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, days]],
               kernel({"function": "K.effects.drain", "state": "vitC grade 4 held SCURVY_H, nothing else",
                       "drain_per_minute": d, "code": code}, "x161b"),
               "%.4f health a game hour from 100: death %.1f game days into the drain; the 168 game hours are a game "
               "choice (S1168 open)." % (per_h, days)),
        series("SD1-m-live", "Measured rate", DAYS, "health", "live",
               [[0.0, 100.0], [100.0 / -live / 24.0, 0.0]],
               artifact("x161b", "body.json", "summaries.I.health.per_game_h"),
               "x161b's measured -0.5985 health a game hour over 18 reads, drawn from 100 (an extrapolation of the "
               "rate). The HEAD drain equals the run's prediction (VALIDATION)."),
    ]


def sd2_days():
    """Days from replete to grade 2 and to grade 4 at zero intake, OnsetSpeed 1, for each pool record."""
    h = KHost()
    K = h.K
    recs = h.NR.data.records
    out = []
    for i in range(1, len(recs.ORDER) + 1):
        key = recs.ORDER[i]
        rec = recs.REC[key]
        if rec.kind != "pool" or rec.k is None:
            continue
        s = K.nutrients.newKey()
        ladder = K.nutrients.ladderOf(rec)
        d2 = d4 = None
        for day in range(1, 3651):
            K.nutrients.stepPool(s, rec, 0, 1.0, K.nutrients.kEff(rec, rec.k, 1), 1.0)
            g = K.nutrients.grade(s.p, ladder)
            if d2 is None and g >= 2:
                d2 = day
            if g >= 4:
                d4 = day
                break
        out.append([key, d2, d4])
    return out


def s_sd2():
    rows = sd2_days()
    inp = {"function": "K.nutrients.stepPool and K.nutrients.grade a day from p = 1 at zero intake, dial 1",
           "records": "NR.data.records, kind pool"}
    return [
        series("SD2-m-marginal", "Days to Marginal", "nutrient", "days", "kernel",
               [[k, d2] for k, d2, d4 in rows if d2 is not None], kernel(inp, "x151r"),
               "The pool records at OnsetSpeed 1; a record of another kind is not stepped this way."),
        series("SD2-m-clinical", "Days to Clinical", "nutrient", "days", "kernel",
               [[k, d4] for k, d2, d4 in rows if d4 is not None], kernel(inp, "x151r")),
        series("SD2-study", "Hodges 1971", "nutrient", "days", "study", [["vitC", 40.0]], study("S0225"),
               "Vitamin C is the record whose rate is calibrated on an onset study (scurvy at about 40 days); the "
               "other records rest on half-lives or game choices."),
    ]


def s_sc1():
    for r in ("x301", "x302"):
        adm(r)
    labels = read("x30g", "rows.json", "row11.nights[*].label")
    booked = read("x30g", "rows.json", "row11.nights[*].booked_h")
    debt = read("x30g", "rows.json", "row11.closes[*].debt_after")
    sess = read("x30g", "rows.json", "row11.closes[*].session")
    s_after = read("x30g", "rows.json", "row11.closes[*].s_after")
    rep = result("j_adm_x30")
    kern = []
    for lab, se, s in zip(labels, sess, s_after):
        rows = rep[se]["rows"]
        v = rows.get(s)
        if v is None:
            v = rows.get(float(s))
        kern.append([lab, v[1]])
    return [
        series("SC1-m-live-booked", "Hours slept, measured", "night", "hours", "live", list(zip(labels, booked)),
               artifact("x30g", "rows.json", "row11.nights[*].booked_h"),
               "Sleep on; x301 and x302 pass the admission test on the sleep kernel (#3677)."),
        series("SC1-m-live-debt", "Debt after the night, measured", "night", "debt (h)", "live",
               list(zip(labels, debt)), artifact("x30g", "rows.json", "row11.closes[*].debt_after")),
        series("SC1-m-kernel", "Debt, simulated", "night", "debt (h)", "kernel", kern,
               kernel({"replay": "x301 and x302's events.json from their start.json at HEAD", "path": "acute.debtH",
                       "read": "at each close's s_after", "sleep_allowed": True}, "x30g")),
    ]


def s_sv1():
    K = KHost().K
    m = [[g, int(K.view.fullnessLevel(float(g)))] for g in range(0, 1201, 10)]
    adm("x401")
    mass = read("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass")
    lv = read("x401", "accept.json", "verdicts.OF.observed.rows[*].levels")
    return [
        series("SV1-m-kernel", "Nutrition Revamp", "grams in the stomach", "moodle level (0-4)", "kernel", m,
               kernel({"function": "K.view.fullnessLevel(mass)", "grams": [0, 1200, 10]}, "x401")),
        series("SV1-m-live", "Measured", "grams in the stomach", "moodle level (0-4)", "live",
               list(zip(mass, lv)), artifact("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass"),
               "x401's rows with the level the client showed (verdicts.OF.observed.rows[*].levels; #3778); each "
               "equals K.view.fullnessLevel at HEAD (VALIDATION)."),
    ]


def s_validation():
    """No series: fills VALIDATION with the admission records (the build reads the list after every definition)."""
    fill_validation()
    return []


SERIES_DEFS = [s_h1, s_h2, s_h3, s_h4, s_s1a, s_s1b, s_s1c, s_s2a, s_s2b, s_s2c, s_s2d, s_s3a, s_s3b, s_s3c, s_s4a,
               s_s4b, s_s4c, s_s5a, s_s5b, s_s5c, s_s6a, s_s6b, s_s6c, s_sn1, s_se1, s_sh1, s_sh2, s_st1, s_st2,
               s_sm1, s_sb1, s_sb2, s_sx1, s_sx2, s_ss1, s_sd1, s_sd2, s_sc1, s_sv1, s_validation]
