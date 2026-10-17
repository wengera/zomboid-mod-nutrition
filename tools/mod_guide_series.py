"""The Nutrition Revamp player guide's series definitions (Plan 14 Tasks 3 and 4).

`tools/mod_guide_data.py` imports this module lazily and builds `docs/mod-guide/data.json` from it:

- `SERIES_DEFS` is a list of callables, each taking no argument and returning one series dict or a list of
  them, in the schema `mod_guide_data.validate_series` checks. Task 4 filled it from the source map's § 2
  (`docs/superpowers/research/2026-10-15-mod-guide/source-map.md`): artifacts, kernel replays at HEAD, the vanilla
  model (`tools/vanilla_model.py`), datasets and studies.
- `MAP_CHARTS` is the source map's charts table (§ 1, at 4e6300fa), copied as data: chart id -> section, title, x
  axis, y axis and the series ids it draws. `CHARTS` is that table less the `DROPPED` ids. Plan 15 Task 13 amended it
  for the game-feel changes: the Energy moodle's lines left S1b and M1's replay line left S1c (the moodle and the
  replay's proof are gone), S2d gained the mod's health with and without water, S6a and S6b their Realistic arms, SV1
  x453b's reading, and SH3 (the hunger writer's cadence, x452) is new.
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
AUTODROP_G = 500.0                    # water for every replay that drinks: 500 g every 2 h from 08:00 to 22:00, 4 L
AUTODROP_MIN = (60, 180, 300, 420, 540, 660, 780, 900)   # a day (review C-1: the map's 2.4 L sat below the mod's loss)
DEHYD_BOUND = 3.0                     # % body mass: the viability guard's bound (rule R-1), a game choice named here:
#                                       mild, inside the mod's dehydration fatigue bands (+0.06 at 2 %, +0.08 at 3 %,
#                                       NR_Data_Effects B5) and far under its 10 % lethal line. The fed replays read 1.2
#                                       to 1.8 %, the oracle arms 2.0 to 2.45; a fast's peak is the overnight dry window
#                                       (22:00 to 08:00) and creeps as the body shrinks (2.13 % by day 3, 2.7 % by day
#                                       24; 12 L a day lowers it only 0.2), so 3 % holds a fast to its death. A guard,
#                                       not a claim: the guide never calls these characters fully hydrated
# the plate the mod-side scenarios eat (rule R-1, review C-1): the guide's foods and an orange, whole vectors from the
# mod's table (replay_live's meal `plate`), so every meal carries real vitamins and minerals in their proportions
PLATE = ("Base.CannedBologneseOpen", "Base.Bread", "Base.Apple", "Base.Orange", "Base.Burger", "Base.TunaTinOpen")
# provisional rows a vanilla formula cites before their mint (concern 9, a guard): vmodel() leaves them out of a
# provenance and fails the build once one of them is in the register. Task 7's mint took T2.1-T2.4 to #3878-#3881.
UNMINTED = ()
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
    "x441": "x441-20261015-172803", "x442": "x442-20261015-173502", "x443a": "x443a-20261015-174228",
    "x443b": "x443b-20261015-174712", "x444": "x444-20261015-175242", "x445": "x445-20261015-175946",
    "x445b": "x445b-20261015-181249", "x446": "x446-20261015-180608", "x447r": "x447-regrade-20261015",
    # Plan 15 Task 11: the game-feel sessions, on the staged copy of mod/ at a97fec05 (the mod's tree at this build)
    "x452": "x452-20261017-071527", "x453b": "x453b-20261017-080807", "x454": "x454-20261017-073220",
    "x455": "x455-20261017-073633", "x456": "x456-20261017-074015", "x457": "x457-20261017-074403",
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
           "series": ["S1b-v-model", "S1b-v-live", "S1b-m-kernel"]},
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
    "S2d": {"section": "S2", "title": "A long fast, with water and without",
           "x": "game days (vanilla to day 4, the mod to its death)", "y": "health, kg",
           "series": ["S2d-v-model-health", "S2d-v-live-health", "S2d-v-model-weight", "S2d-v-live-weight", "S2d-m-mass",
                      "S2d-m-drain", "S2d-m-dry"]},
    "S3a": {"section": "S3 Living on one food", "title": "Vitamin C on tinned tuna alone",
           "x": "game days, 0–170 (to the self-experimenter's day 161)", "y": "vitamin C store (0–1) and grade",
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
           "x": "game hours over day 1 and day 14; game days for the tolerance",
           "y": "caffeine in the body (mg); tolerance (0–1); fatigue",
           "series": ["S6a-m-day1", "S6a-m-day14", "S6a-m-tolerance", "S6a-v-model", "S6a-m-offset",
                      "S6a-m-offset-real"]},
    "S6b": {"section": "S6", "title": "Four beers",
           "x": "game hours, 0–24", "y": "intoxication (0–100); blood alcohol %",
           "series": ["S6b-v-model", "S6b-v-live", "S6b-m-bac", "S6b-m-intox", "S6b-m-hangover", "S6b-m-intox-real"]},
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
    # Plan 15 Task 13: the calibrated hunger writer's cadence, each meal's return to Peckish and dinner's to Hungry
    "SH3": {"section": "Hunger", "title": "When hunger comes back after a meal",
           "x": "meal (lunch, dinner, breakfast)", "y": "game hours until Peckish, or Hungry",
           "series": ["SH3-v-model", "SH3-m-kernel", "SH3-m-live", "SH3-v-model-hungry", "SH3-m-kernel-hungry",
                      "SH3-m-live-hungry"]},
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
           "series": ["SV1-m-kernel", "SV1-m-live", "SV1-m-live-b"]},
}

# ---- the series the evidence does not support, and the ones that wait on a live run -----------------------------------

# The vanilla-live gaps: x441-x447 (Task 5's drivers, Task 8's runs) fill them; S2d-v-live-weight is an existing run.
PENDING_LIVE = ()          # Task 8 built every vanilla-live series from x441-x445b

# Each series the evidence does not support, and why. A live series fails when the admission of the quantity it draws
# fails (ADMISSIONS below, recorded in VALIDATION); `admissions()` checks that this table says exactly that.
DROPPED = {
    "S2a-m-live": "G8: x364's HEAD replay misses its HUNGER by 0.060 against 0.002 (the calibrated hunger writer, "
                  "Plan 15 Task 6, writes the curve of the model's hunger)",
    "S2b-m-live": "G8: x271 and x272 (the rows' fast) miss their HUNGER at HEAD (pre-Plan 11g rings)",
    "SH2-m-live": "G8: x276 misses its HUNGER at HEAD (a pre-Plan 11g ring); SH2-m-kernel replays its inputs at HEAD",
    "SM1-m-live": "G8: x343's HEAD replay misses its UNHAPPINESS by up to 1.74 against 0.051",
    "SX2-m-live": "G8: x291's HEAD replay misses its satiety.S by up to 0.087 against 1e-6",
    "ST1-m-live": "G8: x151t (the Plan 4 build) carries no ring and no event log to replay at HEAD, so no admission "
                  "test can run on it",
    "ST2-m-live-plasma": "G8: the HEAD replays of x281-x284 hold the sodium balance exactly but miss plasma sodium by "
                         "up to 1.44 mmol/L against 0.01",
    "SH1-m-live": "G8: x361's HEAD replay misses its HUNGER by 0.088 against 0.002 (the calibrated hunger writer, "
                  "Plan 15 Task 6); x452 measures the hunger cadence on this build (SH3)",
    "S1c-m-live": "G8: x446's HEAD replay misses its THIRST by 0.33 against 0.002 (the water base by lean mass, Plan 15 "
                  "Task 3)",
    "SD1-m-live": "G8: x161b read the Plan 5 scurvy drain, 100 health over 168 game hours; Plan 15 Task 4's engine "
                  "drains to a floor at its own rate (VALIDATION x161b:drain)",
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


def vmodel(*formulas, ids=None):
    """A vanilla-model provenance: the formulas and their register rows. A row the formulas cite that is not in the
    register is left out only when UNMINTED names it; any other missing row, or an UNMINTED id now in the register
    (Task 7 has minted it: drop it from UNMINTED and rebuild), fails the build."""
    ids = _register() if ids is None else ids
    minted = [u for u in UNMINTED if u in ids]
    if minted:
        raise D.ProvenanceError("UNMINTED ids now in the register: %s; drop them from UNMINTED and rebuild"
                                % ", ".join(minted))
    claims = []
    for f in formulas:
        for c in VM.FORMULAS[f]["claims"]:
            if c in ids:
                if c not in claims:
                    claims.append(c)
            elif c not in UNMINTED:
                raise D.ProvenanceError("%s cites %s, neither in the register nor in UNMINTED" % (f, c))
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


def autodrops(days, start_day=0):
    return [{"minute": d * DAY_MIN + m, "kind": "autodrop", "g": AUTODROP_G} for d in range(start_day, days)
            for m in AUTODROP_MIN]


def plate_meal(minute, size):
    return {"minute": minute, "kind": "meal", "size": size, "plate": list(PLATE)}


def request_meals(days):
    return [plate_meal(d * DAY_MIN + m, "request") for d in range(days) for m in REQUEST_MIN]


def sort_events(ev):
    return sorted(ev, key=lambda e: e["minute"])


# ---- the replays and the viability guard (rule R-1) -----------------------------------------------------------------------

GUARD = ("fluids.dehydPct", "drain.state", "drain.targetFloor")
HEALTH = "health"                     # the stand-in's overall health, 100 less ReduceGeneralHealth plus AddGeneralHealth
DEATH_HEALTH = 1e-6                   # health at or under it is the death (test_kernel_drain's fast deaths read the same)


def _guide_replay():
    """replay_live.ServerReplay whose rows also carry the stand-in's overall health (HEALTH): the mod's drain takes it
    through ReduceGeneralHealth and its heal toward a floor gives it back through AddGeneralHealth (Plan 15 Task 4),
    so the replay's health is 100 less the one plus the other, as test_kernel_drain's fast-death test reads it. The
    stand-in's AddGeneralHealth is given the game's spread, overall health rising by 5.05 / 17 of the argument with
    every part below 100 (#3898, K.drain.PART_SPREAD), so the health the mod reads back is the game's."""
    RL = _rl()

    class GuideReplay(RL.ServerReplay):
        sparse, every, calls = frozenset(), 1, 0

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.rt.execute("for _, bd in ipairs(NR_T.bodies) do bd.AddGeneralHealth = function(s, v) "
                            "s.st.added = s.st.added + v / NutritionRevamp.kernel.drain.PART_SPREAD end end")

        def row(self, paths):
            k, self.calls = self.calls, self.calls + 1
            if self.sparse and k % self.every != self.every - 1 and k != 0:
                paths = [p for p in paths if p not in self.sparse]
            out = super().row(paths)
            body = self.p.st.body
            out[HEALTH] = 100.0 - float(body.reduced) + float(body.added)
            return out
    return GuideReplay


def server_run(events, minutes, paths=(), player=None, perk=None, sleep_allowed=False, hour_offset=HOUR_OFFSET,
               start=None, stimulants=None, sparse=(), every=DAY_MIN):
    """The mod's server pipeline on the lupa host from a fresh record (first sight builds the creation body from the
    stand-in's traits), on a synthetic one-minute clock from world age 0; returns (rows, backend). Row k is the state
    drain k left, at age (k + 1) / 60. `perk` is the native Strength level vanilla's applyTraits left (the creation
    reads the muscle pick off it: CRE.inferMuscle); `stimulants` sets NR.StimulantRealism (1 Game, the default; 2
    Realistic), which the options poll reads each minute. Every row carries the guard's paths and the stand-in's health
    (viability); the `sparse` paths are read only on row 0 and every `every`-th row (k = every - 1, 2 every - 1, ...: the
    day closes day_ends picks), which keeps a long replay of many paths small. An event at or past the last minute is
    left out (a whole day's water on a shorter window)."""
    RL = _rl()
    be = _guide_replay()(start=start, player=player, hour_offset=hour_offset, rng="half", sleep_allowed=sleep_allowed)
    be.sparse, be.every = frozenset(sparse), int(every)
    if stimulants is not None:
        be.rt.execute("SandboxVars = { NR = { StimulantRealism = %d } }" % int(stimulants))
    if perk is not None:
        be.p.st.perk = perk
    events = [e for e in events if "minute" not in e or e["minute"] < minutes]     # a day's water past the window
    rows = RL.run(be, RL.synthetic_ages(minutes), sort_events(events), list(paths) + list(GUARD), start_age=0.0)
    return rows, be


def state_name(code, K=None):
    """The drain state's name off K.drain.states (Plan 15 Task 4: 1 starvation ... 7 iron)."""
    if K is None:
        K = KHost().K
    return str(K.drain.states[int(code)].name)


def viability(rows, K=None):
    """Rule R-1's reading of a replay (Plan 15 Task 13: a drain is damage to a floor, not a death clock): the largest
    fluids.dehydPct; the first drain (age h, state code) the mod's engine opened (drain.state, the code whose floor is
    lowest); the lowest health; and the death, the first row whose health is gone (at or under DEATH_HEALTH), with the
    state that drained it there. dmax_to_death is the largest deficit up to the death (the whole window without one)."""
    dmax = max((r.get("fluids.dehydPct") or 0.0) for r in rows)
    first = next(((r["age"], int(r["drain.state"])) for r in rows if r.get("drain.state")), None)
    dead = next((r for r in rows if r.get(HEALTH) is not None and r[HEALTH] <= DEATH_HEALTH), None)
    out = {"max_dehydPct": dmax, "drain": list(first) if first else None,
           "min_health": min((r[HEALTH] for r in rows if r.get(HEALTH) is not None), default=None),
           "death": [dead["age"], int(dead["drain.state"] or 0)] if dead else None,
           "death_age": dead["age"] if dead else None, "hours": rows[-1]["age"] if rows else 0.0}
    out["dmax_to_death"] = (max((r.get("fluids.dehydPct") or 0.0) for r in rows if r["age"] <= dead["age"])
                            if dead else dmax)
    if first is not None:
        out["drain_name"] = state_name(first[1], K)
    if dead is not None and dead["drain.state"]:
        out["death_name"] = state_name(dead["drain.state"], K)
    return out


def assert_viable(name, v, death=False, thirst=False, drain=False):
    """Rule R-1: a replay stays alive and under DEHYD_BOUND over its window, unless the series names the death (then
    its lines end at v["death_age"]) or the scenario is the thirst itself (no water by design: alive, any dehydration).
    A drain (damage to a floor, Plan 15) is named as well: a replay that opens one the series does not name fails, so a
    story that takes damage says so. death and drain: True (the series shows one), "allowed" (it may), False."""
    if v["death"] is not None and not death:
        raise D.ProvenanceError("%s: the replay's health is gone at %.2f h, drained by state %d (rule R-1)"
                                % (name, v["death"][0], v["death"][1]))
    if death is True and v["death"] is None:
        raise D.ProvenanceError("%s: the series names a death and the replay has none" % name)
    if v["drain"] is not None and not (drain or death):
        raise D.ProvenanceError("%s: the replay opens drain state %d at %.2f h, which the series does not name (rule R-1)"
                                % (name, v["drain"][1], v["drain"][0]))
    if drain is True and v["drain"] is None:
        raise D.ProvenanceError("%s: the series names a drain and the replay opens none" % name)
    if not thirst:
        if v["dmax_to_death"] > DEHYD_BOUND:
            raise D.ProvenanceError("%s: dehydration reaches %.2f %% over the bound %.1f %% (rule R-1)"
                                    % (name, v["dmax_to_death"], DEHYD_BOUND))
    return v


def until_death(points, v, scale=24.0):
    """Points up to the death (x in hours / scale), the last one at or before it."""
    if v["death_age"] is None:
        return points
    end = v["death_age"] / scale
    return [p for p in points if p[0] <= end + 1e-12]


def to_death(points, v, at_death, scale=24.0):
    """until_death's points with a last point at the death itself, the replay's own value at the death minute (the
    line ends at the death, not at the last daily sample before it)."""
    pts = until_death(points, v, scale)
    if v["death_age"] is not None and pts and pts[-1][0] < v["death_age"] / scale:
        pts.append([v["death_age"] / scale, at_death])
    return pts


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
    """Forget every computed job (a test that edits the Lua tree reruns them)."""
    _RESULTS.clear()


# rough CPU seconds, for the pool's order only
JOB_COST = {"j_s2d": 30, "j_s2d_dry": 3, "j_s3c": 28, "j_s3a": 21, "j_s5b_strong": 31, "j_s5b_weak": 31, "j_s5b_none": 31,
            "j_s5b_gaunt": 31, "j_s5b_overweight": 31, "j_h2": 11, "j_s2c": 9, "j_s2b": 6, "j_s3b": 5, "j_s6a": 5,
            "j_vanilla_s4b": 12, "j_s2a": 3, "j_sh1": 3}


# ---- the admission test (ruling G8, the I-3 ruling: per drawn quantity, a tolerance with a stated source) --------------

HUNGER_TOL = {"HUNGER": ("abs", 0.002)}
DEBT_TOL = {"acute.debtH": ("abs", 1e-6), "acute.winSleptH": ("abs", 1e-6)}
SRC_DEFAULT = "the run's own: replay_live.DEFAULT_TOL (HUNGER 0.002), the pre-registered 11f bound its grade used"
SRC_DEBT = "the run's own: x30_grade.TOL_MINE (acute.debtH, acute.winSleptH 1e-6)"
SRC_S = "the run's own: x29_grade.TOL_MINE (satiety.S 1e-6)"
SRC_FILL = "the run's own: x36_gut_lib.TOL_GRADE (stomachFill 0.002) and TOL_EXTRA (stomach.liquid 2 g)"
SRC_MOOD = "the run's own: x34_grade's live-against-replay bound, K.hybrid.FLOOR_EPS + REPLAY_TOL_EXTRA 1e-3"
SRC_THIRST = ("named here, a game choice (the run graded no THIRST, G7): HUNGER's 0.002, the same stat scale and the "
              "grade's own resolution")
SRC_SODIUM = "named here, a game choice (x28 graded no sodium bound): 1e-6 mmol, the record's own arithmetic"
SRC_PLASMA = "named here, a game choice (x28 graded no plasma bound): 0.01 mmol/L, the precision #3688 states it to"
SRC_M1 = "the run's own: x44_guide_lib.REPLAY_TOL (THIRST 0.002), its M1_replay_THIRST grade's bound"
SRC_X452 = "the run's own: x45g_lib's replay tolerance (HUNGER 0.002), its REPLAY_HUNGER grade's bound"

# (key, run, sleep_allowed, tolerance, its source, the live series it admits, the kernel series it proves, pinned)
ADMISSIONS = (
    # Plan 15 Task 13: the calibrated hunger writer (Task 6) moves every older ring's HUNGER, the water base (Task 3)
    # every older ring's THIRST and the mood floor's dead zone (Task 9) x342's UNHAPPINESS, so those runs fail at HEAD
    # and prove no kernel line; x452 (the mod's tree at this build, a97fec05) proves the hunger lines
    ("x361:HUNGER", "x361", False, HUNGER_TOL, SRC_DEFAULT, ["SH1-m-live"], [], False),
    ("x363:fill", "x363", False, {"stomachFill": ("abs", 0.002), "stomach.liquid": ("abs", 2.0)}, SRC_FILL,
     ["SE1-m-live-liquid", "SE1-m-live-fill"], ["SE1-m-kernel-fill"], True),
    ("x364:HUNGER", "x364", False, HUNGER_TOL, SRC_DEFAULT, ["S2a-m-live"], [], False),
    ("x446:THIRST", "x446", False, {"THIRST": ("abs", 0.002)}, SRC_M1, ["S1c-m-live"], [], False),
    ("x452:HUNGER", "x452", False, HUNGER_TOL, SRC_X452, ["SH3-m-live", "SH3-m-live-hungry"],
     ["H1-m-kernel", "S1a-m-kernel", "S2a-m-kernel", "SH1-m-kernel", "SH3-m-kernel", "SH3-m-kernel-hungry"], True),
    ("x271:HUNGER", "x271", False, HUNGER_TOL, SRC_DEFAULT, ["S2b-m-live"], [], False),
    ("x272:HUNGER", "x272", False, HUNGER_TOL, SRC_DEFAULT, ["S2b-m-live"], [], False),
    ("x276:HUNGER", "x276", False, HUNGER_TOL, SRC_DEFAULT, ["SH2-m-live"], ["SH2-m-kernel"], False),
    ("x281:na", "x281", False, {"fluids.na": ("abs", 1e-6)}, SRC_SODIUM, ["ST2-m-live-na"], ["ST2-m-kernel"], True),
    ("x282:na", "x282", False, {"fluids.na": ("abs", 1e-6)}, SRC_SODIUM, ["ST2-m-live-na"], ["ST2-m-kernel"], True),
    ("x283:na", "x283", False, {"fluids.na": ("abs", 1e-6)}, SRC_SODIUM, ["ST2-m-live-na"], ["ST2-m-kernel"], True),
    ("x284:na", "x284", False, {"fluids.na": ("abs", 1e-6)}, SRC_SODIUM, ["ST2-m-live-na"], ["ST2-m-kernel"], True),
    ("x281:plasma", "x281", False, {"fluids.naPlasma": ("abs", 0.01)}, SRC_PLASMA, ["ST2-m-live-plasma"], [], False),
    ("x282:plasma", "x282", False, {"fluids.naPlasma": ("abs", 0.01)}, SRC_PLASMA, ["ST2-m-live-plasma"], [], False),
    ("x283:plasma", "x283", False, {"fluids.naPlasma": ("abs", 0.01)}, SRC_PLASMA, ["ST2-m-live-plasma"], [], False),
    ("x284:plasma", "x284", False, {"fluids.naPlasma": ("abs", 0.01)}, SRC_PLASMA, ["ST2-m-live-plasma"], [], False),
    ("x291:S", "x291", False, {"satiety.S": ("abs", 1e-6)}, SRC_S, ["SX2-m-live"], ["SX2-m-kernel"], False),
    ("x301:sleep", "x301", True, DEBT_TOL, SRC_DEBT, ["S6c-m-live", "SC1-m-live-booked", "SC1-m-live-debt"],
     ["S6c-m-kernel", "SC1-m-kernel"], True),
    ("x302:sleep", "x302", True, DEBT_TOL, SRC_DEBT, ["S6c-m-live", "SC1-m-live-booked", "SC1-m-live-debt"],
     ["S6c-m-kernel", "SC1-m-kernel"], True),
    ("x341:mood", "x341", False, "mood", SRC_MOOD, ["S3b-m-live-U", "S3b-m-live-B"], [], True),
    ("x342:mood", "x342", False, "mood", SRC_MOOD, ["S3b-m-live-U", "S3b-m-live-B"], ["S3b-m-kernel-U"], False),
    ("x343:mood", "x343", False, "mood", SRC_MOOD, ["SM1-m-live"], ["SM1-m-kernel"], False),
)
# runs graded off the HEAD kernel directly (no ring to replay): key -> (the live series, the kernel series)
OTHER = {"x37g:met": (["SX1-m-live"], ["SX1-m-kernel"]), "x401:level": (["SV1-m-live"], ["SV1-m-kernel"]),
         "x453b:level": (["SV1-m-live-b"], ["SV1-m-kernel"]), "x161b:drain": (["SD1-m-live"], []),
         "x436:creation": (["S5a-m-live-lean", "S5a-m-live-fat", "S5a-m-live-weight", "S5a-m-live-level",
                            "S5c-m-live"], [])}
OTHER_EXPECT = {"x161b:drain": False}            # the run read the Plan 5 scurvy drain (Plan 15 Task 4's engine differs)
ADMISSION_EXPECT = {a[0]: a[7] for a in ADMISSIONS}
ADMISSION_EXPECT.update({k: OTHER_EXPECT.get(k, True) for k in OTHER})


def mood_tol(eps):
    """x34_grade's live-against-replay bound for UNHAPPINESS and the remembered target: FLOOR_EPS plus 1e-3."""
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


def replay_of(run, sleep_allowed, events=None):
    """The HEAD replay of run's own inputs (start, events, start stats, player) on its ring's clock and activity:
    (rows, ring)."""
    RL = _rl()
    d = os.path.join(REPO, "testing", "artifacts", RUN[run])
    ring, paths = _ring(d)
    rows, _ = RL.replay_live(ring, (_json(d, "events.json") or []) if events is None else events,
                             _json(d, "start.json"), paths=paths, user="admin", player=_json(d, "player.json"),
                             start_stats=_json(d, "start-stats.json"), sleep_allowed=sleep_allowed)
    return rows, ring


def admission(run, sleep_allowed, tol, keep=()):
    """The HEAD replay of run's own inputs against its ring, graded by replay_live.diff under tol. Returns (record,
    rows): record {run, quantity, tolerance, max_miss, n, admitted}; rows the replay rows' `keep` fields by s."""
    RL = _rl()
    rows, ring = replay_of(run, sleep_allowed)
    df = RL.diff(rows, ring, tol)
    rec = {"run": RUN[run], "quantity": sorted(tol), "tolerance": {f: [how, b] for f, (how, b) in sorted(tol.items())},
           "max_miss": {f: df["fields"][f]["max"] for f in sorted(tol)},
           "n": {f: df["fields"][f]["n"] for f in sorted(tol)}, "admitted": bool(df["ok"])}
    kept = {r["s"]: [r.get("age")] + [r.get(f) for f in keep] for r in rows} if keep else None
    return rec, kept


def _grade(key, run, sleep_allowed, tol, keep=()):
    if tol == "mood":
        tol = mood_tol(float(KHost().K.hybrid.FLOOR_EPS))
    return admission(run, sleep_allowed, dict(tol), keep)


def _jobs_of(keys, keep=None):
    out = {}
    for a in ADMISSIONS:
        if a[0] in keys:
            rec, kept = _grade(a[0], a[1], a[2], a[3], (keep or {}).get(a[0], ()))
            out[a[0]] = {"rec": rec, "rows": kept}
    return out


@job
def j_adm_x36():
    return _jobs_of({"x361:HUNGER", "x363:fill", "x364:HUNGER"}, {"x363:fill": ("stomachFill",)})


@job
def j_adm_x44():
    return _jobs_of({"x446:THIRST", "x452:HUNGER"}, {"x452:HUNGER": ("HUNGER",)})


@job
def j_adm_x27():
    return _jobs_of({"x271:HUNGER", "x272:HUNGER", "x276:HUNGER"})


@job
def j_adm_x28():
    return _jobs_of({k for k, *_ in ADMISSIONS if k.startswith("x28")})


@job
def j_adm_x29_x30():
    return _jobs_of({"x291:S", "x301:sleep", "x302:sleep"}, {"x301:sleep": ("acute.debtH",),
                                                            "x302:sleep": ("acute.debtH",)})


@job
def j_adm_x34():
    return _jobs_of({"x341:mood", "x342:mood", "x343:mood"}, {"x343:mood": ("UNHAPPINESS",)})


ADM_JOB = {}
for _a in ADMISSIONS:
    _r = _a[1]
    ADM_JOB[_a[0]] = ("j_adm_x44" if _r in ("x446", "x452") else
                      "j_adm_x36" if _r in ("x361", "x363", "x364") else
                      "j_adm_x27" if _r in ("x271", "x272", "x276") else
                      "j_adm_x28" if _r.startswith("x28") else
                      "j_adm_x29_x30" if _r in ("x291", "x301", "x302") else "j_adm_x34")


@job
def j_sh2():
    """SH2: the HEAD replay of x276's live events (six meals, S0_*) against its three-meal arm (x27_grade.row8's arm:
    the six S0_ eats replaced by three TKX.Mixed667 at 08:00 + 5 h k of day 0, world age 25 + 5k): the time-weighted
    mean HUNGER over the 24 h from world age 25 (x27_energy_lib.mean_over)."""
    d = os.path.join(REPO, "testing", "artifacts", RUN["x276"])
    ev = _json(d, "events.json")
    six, _ = replay_of("x276", False)
    t0 = 25.0
    base = [e for e in ev if not str(e.get("label", "")).startswith("S0_")]
    three_ev = [{"age": t0 + 5.0 * k, "kind": "eat", "food": "TKX.Mixed667", "label": "T6_%d" % k} for k in range(3)]
    three, _ = replay_of("x276", False, base + three_ev)
    return {"six": mean_over(six, t0, 1440), "three": mean_over(three, t0, 1440), "loads": True}


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


def _adm_x37():
    """x37's billed MET (SX1-m-live): every bill of x371's sets against the HEAD EXERCISE_MET of its type, exactly."""
    K = KHost().K
    types = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].type")
    billed = read("x37g", "grade.json", "sessions.x371.sets[*].bills[*].billed")
    miss = 0.0
    for t, b in zip(types, billed):                      # [*][*] reads flat, one leaf per bill
        miss = max(miss, abs(float(K.energy.EXERCISE_MET[t]) - b))
    q = "billed MET"
    return {"run": RUN["x37g"], "quantity": [q], "tolerance": {q: ["abs", 0.0]}, "max_miss": {q: miss},
            "n": {q: len(billed)}, "admitted": miss == 0.0 and len(types) == len(billed) > 0,
            "tolerance_source": "named here: exact, a table read (K.energy.EXERCISE_MET at HEAD)"}


def _adm_x401():
    """x401's Overfull rows (SV1-m-live): K.view.fullnessLevel at HEAD of each row's server mass against the level
    the client showed, exactly."""
    K = KHost().K
    mass = read("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass")
    lv = read("x401", "accept.json", "verdicts.OF.observed.rows[*].levels")
    miss = max(abs(float(K.view.fullnessLevel(m)) - v) for m, v in zip(mass, lv))
    q = "Overfull level"
    return {"run": RUN["x401"], "quantity": [q], "tolerance": {q: ["abs", 0.0]}, "max_miss": {q: miss},
            "n": {q: len(mass)}, "admitted": miss == 0.0,
            "tolerance_source": "named here: exact, a level (K.view.fullnessLevel at HEAD)"}


def scurvy_line(h, step_h=6.0):
    """Clinical scurvy's health at HEAD (h a KHost), nothing else wrong, from full health at the clinical onset: the
    drain engine takes K.drain.rate a game day down to K.drain.floor on the hours at the clinical grade, never past it
    (K.drain.take), so health reads max(floor(t), 100 - rate x t) while the floor falls slower than the rate. Returns
    (points [[days, health]] every step_h hours and at each knot, rate a game day, the death hour)."""
    K = h.K
    code = int(K.drain.SCURVY)
    rate = float(K.drain.rate(code))
    death_h = float(K.drain.SCURVY_DEATH_H)
    inp = h.table({"lm": 52.02, "fm": 13.005, "bmi0": 0.0, "dehydPct": 0.0})
    kn = K.drain.states[code].knots
    hours = [float(kn[i][1]) for i in range(1, len(kn) + 1)]
    reach = (100.0 - float(K.drain.FIRST_FLOOR)) / rate * 24.0          # the drain reaches the first floor
    ts = sorted(set([i * step_h for i in range(int(death_h / step_h) + 1)] + hours + [reach, death_h]))
    pts = []
    for t in ts:
        f = float(K.drain.floor(code, t, inp))
        pts.append([t / 24.0, max(f, 100.0 - rate * t / 24.0)])
    return pts, rate, death_h


def _adm_x161b():
    """x161b's scurvy drain (SD1-m-live): the HEAD drain a game hour (K.drain.rate of scurvy over 24) against the run's
    own prediction from the drain it read (summaries.I.pred_per_game_h), within 1e-9. The run read the Plan 5 drain,
    100 health over 168 game hours; Plan 15 Task 4's engine drains 50 / 3 a game day to a floor, so it fails at HEAD."""
    K = KHost().K
    per_h = float(K.drain.rate(int(K.drain.SCURVY))) / 24.0
    pred = read("x161b", "body.json", "summaries.I.pred_per_game_h")
    miss = abs(per_h - pred)
    q = "scurvy drain a game hour"
    return {"run": RUN["x161b"], "quantity": [q], "tolerance": {q: ["abs", 1e-9]}, "max_miss": {q: miss},
            "n": {q: 1}, "admitted": miss <= 1e-9,
            "tolerance_source": "named here: 1e-9, the HEAD drain against the run's own prediction of it"}


PICK_NAME = {None: None, "strong": "STRONG", "weak": "WEAK", "feeble": "FEEBLE", "stout": "STOUT", "obese": "OBESE",
             "overweight": "OVERWEIGHT", "underweight": "UNDERWEIGHT", "veryunderweight": "VERY_UNDERWEIGHT"}


def _adm_x436():
    """x436's creation bodies (S5a-m-live, S5c-m-live), cases a-f: the HEAD K.body.create of each case's picks against
    the record's lean and fat, the level written at creation (K.strength.heldLevel of its level at T 1) against the
    client's, and the start energy state K.deficit.state(0, fatDep) against the server's within the run's 0.02."""
    h = KHost()
    K = h.K
    P = K.strength.DEFAULTS
    miss = {"lean and fat": 0.0, "level": 0.0, "es": 0.0}
    for c in "abcdef":
        body = read("x436", "creation.json", "verdicts.36_%s_body.observed.record.{lm,fm}" % c)
        musc = read("x436", "creation.json", "verdicts.36_%s_body.observed.expect.muscle" % c)
        wt = read("x436", "creation.json", "verdicts.36_%s_body.observed.expect.weightPick" % c)
        lv = read("x436", "creation.json", "verdicts.36_%s_xp.observed.client_level" % c)
        es = read("x436", "creation.json", "verdicts.36_%s_hunger.observed.es" % c)
        spec = K.body.create(PICK_NAME[musc], PICK_NAME[wt], P, 1, 0)
        miss["lean and fat"] = max(miss["lean and fat"], abs(float(spec.lm) - body[0]), abs(float(spec.fm) - body[1]))
        L = K.strength.level(spec.lm, spec.N0, 1, P)
        miss["level"] = max(miss["level"], abs(float(K.strength.heldLevel(L, None)[0]) - lv))
        dep = (float(spec.fmRef) - float(spec.fm)) / float(spec.fmRef)
        miss["es"] = max(miss["es"], abs(float(K.deficit.state(0, dep)) - es))
    tol = {"lean and fat": ["abs", 1e-9], "level": ["abs", 0.0], "es": ["abs", 0.02]}
    return {"run": RUN["x436"], "quantity": sorted(tol), "tolerance": tol, "max_miss": miss,
            "n": {q: 6 for q in tol}, "admitted": all(miss[q] <= tol[q][1] for q in tol),
            "tolerance_source": "the run's own: x436's verdicts (the record equal to the staged K.body.create, the "
                                "level equal, the energy state within its tol 0.02)"}


def _adm_x453b():
    """x453b's Overfull 4 (SV1-m-live-b): K.view.fullnessLevel at HEAD of the stomach mass the server read after the
    broccoli that crossed, against the level it read there, exactly (the run's own OF_REACH reads)."""
    K = KHost().K
    mass = read("x453b", "overfull.json", "verdicts.OF_REACH.observed.post_mass")
    lv = read("x453b", "overfull.json", "verdicts.OF_REACH.observed.post_levels")
    miss = max(abs(float(K.view.fullnessLevel(m)) - v) for m, v in zip(mass, lv))
    q = "Overfull level"
    return {"run": RUN["x453b"], "quantity": [q], "tolerance": {q: ["abs", 0.0]}, "max_miss": {q: miss},
            "n": {q: len(mass)}, "admitted": miss == 0.0 and len(mass) == len(lv) > 0,
            "tolerance_source": "named here: exact, a level (K.view.fullnessLevel at HEAD)"}


OTHER_FN = {"x37g:met": _adm_x37, "x401:level": _adm_x401, "x453b:level": _adm_x453b, "x161b:drain": _adm_x161b, "x436:creation": _adm_x436}


def adm(key):
    """The VALIDATION record of an admission key: the graded record with its tolerance source, the live series it
    admits (`draws`) and the kernel series it proves (`proves`), checked against ADMISSION_EXPECT."""
    if key in OTHER:
        rec = dict(OTHER_FN[key]())
        rec["draws"], rec["proves"] = list(OTHER[key][0]), list(OTHER[key][1])
    else:
        a = next(x for x in ADMISSIONS if x[0] == key)
        rec = dict(result(ADM_JOB[key])[key]["rec"])
        rec["tolerance_source"] = a[4]
        rec["draws"], rec["proves"] = list(a[5]), list(a[6])
    rec["kind"] = "admission"
    rec["key"] = key
    if rec["admitted"] != ADMISSION_EXPECT[key]:
        raise D.ProvenanceError("admission %s is %s at HEAD, pinned %s: re-rule its live series and DROPPED"
                                % (key, rec["admitted"], ADMISSION_EXPECT[key]))
    return rec


def adm_rows(key):
    return result(ADM_JOB[key])[key]["rows"]


def admitted(sid):
    """Whether every admission that draws the live series sid admits it (S3b's days are drawn per run)."""
    recs = [adm(k) for k in ADMISSION_EXPECT if sid in (OTHER[k][0] if k in OTHER else
                                                         next(a for a in ADMISSIONS if a[0] == k)[5])]
    return bool(recs) and all(r["admitted"] for r in recs)


def proofs_failing(sid):
    """The admission keys whose run proves the kernel series sid and fails at HEAD."""
    out = []
    for k in ADMISSION_EXPECT:
        proves = OTHER[k][1] if k in OTHER else next(a for a in ADMISSIONS if a[0] == k)[6]
        if sid in proves and not adm(k)["admitted"]:
            out.append(k)
    return out


def admissions():
    """Every admission record, ordered by key, for VALIDATION; DROPPED must name exactly the live series an
    admission rejects (S3b's days aside: drawn per run), plus the one dropped for another reason (ST1-m-live)."""
    recs = [adm(k) for k in sorted(ADMISSION_EXPECT)]
    rejected = {s for r in recs if not r["admitted"] for s in r["draws"]}
    rejected -= {"S3b-m-live-U", "S3b-m-live-B"}
    want = set(DROPPED) - {"ST1-m-live"}
    if rejected != want:
        raise D.ProvenanceError("DROPPED %s does not match the failed admissions %s" % (sorted(want), sorted(rejected)))
    return recs


VIAB = {}


def fill_validation():
    """VALIDATION: the admission records, each replay job's viability (rule R-1, kind "viability"), then the vanilla
    model against the vanilla runs (Task 7, kind "vanilla")."""
    viab = [dict(v, kind="viability", job=j) for j, v in sorted(VIAB.items())]
    VALIDATION[:] = ([v for v in VALIDATION if v.get("kind") not in ("admission", "viability", "vanilla")]
                     + admissions() + viab + vanilla_records())


def viable(name, sid_job, death=False, thirst=False, drain=False):
    """The viability of a job's replay, asserted (rule R-1) and kept for VALIDATION."""
    v = result(sid_job)["viab"]
    VIAB[sid_job] = dict(v, series_death=death, series_drain=drain, thirst_scenario=thirst, bound=DEHYD_BOUND)
    return assert_viable(name, v, death, thirst, drain)


# the replay job behind each kernel series drawn off a multi-minute server replay (rule R-1's test reads it)
SERIES_JOB = {
    "H1-m-kernel": "j_h1", "H2-m-fat": "j_h2", "H2-m-lean": "j_h2", "H2-m-total": "j_h2", "S1a-m-kernel": "j_s1a",
    "S1b-m-kernel": "j_s1b", "S1c-m-kernel": "j_s1c", "ST1-m-kernel": "j_s1c", "S2a-m-kernel": "j_s2a",
    "S2b-m-kernel": "j_s2b", "S2c-m-kernel": "j_s2c", "S2d-m-mass": "j_s2d", "S3a-m-pool": "j_s3a",
    "S3a-m-grade": "j_s3a", "S3c-m-pool": "j_s3c", "S3b-m-kernel-U": "j_s3b", "S5b-m-strong-level": "j_s5b_strong",
    "S5b-m-weak-level": "j_s5b_weak", "S5b-m-none-level": "j_s5b_none", "S5b-m-gaunt-weight": "j_s5b_gaunt",
    "S5b-m-overfat-weight": "j_s5b_overweight", "S5b-m-none-weight": "j_s5b_none", "S5c-m-gaunt": "j_s5b_gaunt",
    "S5c-m-none": "j_s5b_none", "S6a-m-day1": "j_s6a", "S6a-m-day14": "j_s6a", "S6a-m-tolerance": "j_s6a", "S6b-m-bac": "j_s6b",
    "S6b-m-intox": "j_s6b", "S6b-m-hangover": "j_s6b", "S6c-m-kernel": "j_s6c", "SX2-m-kernel": "j_sx2",
    "S2d-m-drain": "j_s2d", "S2d-m-dry": "j_s2d_dry", "S6a-m-offset": "j_s6a", "S6a-m-offset-real": "j_s6a_real",
    "S6b-m-intox-real": "j_s6b_real",
}


def proofs_passing(sid):
    """The admission keys whose run proves the kernel series sid and passes at HEAD."""
    out = []
    for k in ADMISSION_EXPECT:
        proves = OTHER[k][1] if k in OTHER else next(a for a in ADMISSIONS if a[0] == k)[6]
        if sid in proves and adm(k)["admitted"]:
            out.append(k)
    return out


def proof_note(sid):
    """m-7: a kernel series whose proof runs fail the admission test at HEAD, and none passes, says so (an admitted
    record that also proves it leaves the note empty: Task 11 M13)."""
    bad = proofs_failing(sid)
    if not bad or proofs_passing(sid):
        return ""
    return ("Its proof run%s fail%s the admission test at HEAD (VALIDATION %s); no passing proof run exists for it."
            % ("s" if len(bad) > 1 else "", "" if len(bad) > 1 else "s", ", ".join(bad)))


# ======================================================================================================================
# The jobs (the replays and the long vanilla runs)
# ======================================================================================================================

def _ks(start, stop, step):
    return list(range(start, stop, step))


def worse(v):
    """A viability's severity key: a death, then a drain, then the largest deficit (a job of several arms keeps its
    worst)."""
    return (v["death"] is not None, v["drain"] is not None, v["max_dehydPct"])


def _done(rows, be, out):
    out["viab"] = viability(rows, be.K)
    return out


@job
def j_h1():
    """H1: a fresh record from 07:00 with water and no food until the written HUNGER first reaches 0.25 (replay_live
    request_minute), then a whole Base.CannedBologneseOpen at that minute, 6 h after."""
    RL = _rl()
    rows, _ = server_run(autodrops(1), DAY_MIN)
    m = int(round(RL.request_minute(rows, 0.0)))
    ev = [e for e in autodrops(1) if e["minute"] < m + 361] + [eat(m, "Base.CannedBologneseOpen")]
    rows, be = server_run(ev, m + 361, ("satiety.M", "body.energyState"))
    pts = pick(rows, [m - 1] + _ks(m, m + 361, 10), "HUNGER")
    return _done(rows, be, {"request_minute": m, "points": [[age - m / 60.0, h] for _, age, h in pts]})


@job
def j_h2():
    """H2: 30 days of three 500 kcal plate meals at 07, 12 and 18 and the replay's water."""
    ev = [plate_meal(d * DAY_MIN + m, 500.0) for d in range(30) for m in (0, 300, 660)] + autodrops(30)
    rows, be = server_run(ev, 30 * DAY_MIN, ("body.fm", "body.lm", "body.lx"))
    return _done(rows, be, {"days": pick(rows, day_ends(30), "body.fm", "body.lm", "body.lx")})


@job
def j_s1a():
    """S1a: from HUNGER 0 at 07:00 (FRESH, vanilla's start), a whole Base.TunaTinOpen at 08, 12, 16 and 20, water."""
    rows, be = server_run([FRESH] + [eat(m, "Base.TunaTinOpen") for m in TUNA_MIN] + autodrops(1), DAY_MIN)
    return _done(rows, be, {"points": [[age, h] for _, age, h in pick(rows, [0] + _ks(9, DAY_MIN, 10), "HUNGER")]})


# The stand-in's HUNGER is 0.2 at first sight (replay_live's stand-in default), and the mod seeds its meal pool from the
# HUNGER it finds (#3913); S1a and S1b start from HUNGER 0 like the vanilla lines beside them, set before the first drain
FRESH = {"minute": 0, "kind": "stat", "stat": "HUNGER", "value": 0.0}


def hungry_level(h):
    """Vanilla's Hungry moodle level of a HUNGER value (#0508, strict greater-than, #0507): the mod writes HUNGER and
    the game shows its own moodle (Plan 15 Task 9 removed the mod's Energy moodle)."""
    return VM.moodle_level(h, VM.HUNGRY_THRESHOLDS)


@job
def j_s1b():
    """S1b: a fresh record from HUNGER 0 at 07:00 (FRESH) with the replay's water and no food, 36 h: vanilla's Hungry
    level of the written
    HUNGER every 10 minutes, with each step's own minute (the level the minute's HUNGER reads) kept."""
    rows, be = server_run([FRESH] + autodrops(2), 36 * 60)
    seed = be.NR.server.writer.lastSeedKcal
    lv = [(k, r["age"], hungry_level(r["HUNGER"])) for k, r in enumerate(rows)]
    steps = [(a, l) for (_, a, l), (_, _, p) in zip(lv[1:], lv) if l != p]
    pts = [[a, l] for k, a, l in lv if k == 0 or k % 10 == 9] + [[a, l] for a, l in steps]
    return _done(rows, be, {"points": sorted(pts), "steps": [[a, l] for a, l in steps],
                            "first": lv[0][2], "seed_kcal": None if seed is None else float(seed)})


@job
def j_s1c():
    """S1c and ST1: thirst without a drink, by design (the guard holds it alive, any dehydration)."""
    rows, be = server_run([], DAY_MIN, ("fluids.thirstTarget",))
    return _done(rows, be, {"points": [[age, t] for _, age, t in pick(rows, [0] + _ks(9, DAY_MIN, 10), "THIRST")]})


def fast_events(plan, days):
    """An oracle meal plan {minute: size} as plate meals, with the replay's water every day."""
    ev = [plate_meal(m, k) for m, k in sorted(plan.items())]
    ev += [{"minute": d * DAY_MIN + 8 * 60 + m, "kind": "autodrop", "g": AUTODROP_G} for d in range(days)
           for m in AUTODROP_MIN]
    return ev


@job
def j_s2a():
    """S2a: test_replay_live_oracle.fast_plans()'s fast arm (three warm maintenance days, day 0 at maintenance, day 1
    skipped, days 2-3 at the request) as plate meals with water, on the default body, sleep off, on the oracle's clock
    (minute 0 is 00:00; water every 2 h from 09:00)."""
    O = _kt("test_replay_live_oracle")
    M = _kt("test_satiety_meal_studies")
    _, fast, days = O.fast_plans()
    rows, be = server_run(fast_events(fast, days), days * DAY_MIN, ("body.energyState",), hour_offset=0.0)
    last = M.at_hour(0, 20)
    ks = [k for k in range(len(rows)) if -12 * 60 <= k + 1 - last <= 60 * 60 and (k + 1 - last) % 10 == 0]
    return _done(rows, be, {"last_meal_minute": last,
                            "points": [[(k + 1 - last) / 60.0, h] for k, _, h in pick(rows, ks, "HUNGER")]})


def _oracle_arm(plan, days, extra=(), player=None):
    """An energy-oracle arm on the server path as the oracles run it (asleep 23:00-07:00, test_replay_live_oracle's
    sleep_events, sleep on), its meals plates and the replay's water added: (rows, backend)."""
    O = _kt("test_replay_live_oracle")
    ev = O.sleep_events(days) + fast_events(plan, days) + list(extra)
    return server_run(ev, days * DAY_MIN, player=player, hour_offset=0.0, sleep_allowed=True)


@job
def j_s2b():
    """S2b: test_replay_live_energy.fast_server()'s two arms (fed, and the 36 h fast) on its 70 kg man, as plates
    with water: the day-2 and day-3 intake ratios."""
    RL = _rl()
    O = _kt("test_replay_live_oracle")
    M = _kt("test_satiety_meal_studies")
    fed, fast, days = O.fast_plans()
    man = {"weight": 70.0, "female": False}
    rf, bf = _oracle_arm(fed, days, player=man)
    rx, bx = _oracle_arm(fast, days, player=man)
    W = M.FAST_WARM_DAYS
    i_fed, i_fast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    vf, vx = viability(rf, bf.K), viability(rx, bx.K)
    worst = max((vf, vx), key=worse)
    return {"r2": i_fast[W + 2] / i_fed[W + 2], "r3": i_fast[W + 3] / i_fed[W + 3], "viab": worst}


S1254_DEP = (0.0, 0.05, 0.25, 0.40, 0.55)


@job
def j_s2c():
    """S2c: test_replay_live_energy.fat_loss_intake()'s protocol (the no-trait body's fat set fmRef x (1 - dep) at
    minute 2, day 0 at maintenance, days 1-4 at the request, sleep 23:00-07:00) as plates with water: the mean intake
    over days 2-4 at each depletion and the kg of fat lost."""
    RL = _rl()
    E = _kt("test_replay_live_energy")
    M = _kt("test_satiety_meal_studies")
    h = KHost()
    fm_ref = h.call("body.create", None, None, h.K.strength.DEFAULTS, 1)["fm"]
    days = E.S1254_DAYS
    out, worst = [], None
    for dep in S1254_DEP:
        plan = {int(d * 1440 + hh * 60): ("maint" if d == 0 else "request") for d in range(days)
                for hh in M.FAST_MEAL_H}
        extra = [{"minute": 2, "kind": "setpath", "path": "body.fm", "value": fm_ref * (1 - dep)}]
        rows, be = _oracle_arm(plan, days, extra, player={"female": False})
        by = RL.intake_by_day(be.eats)
        out.append([fm_ref * dep, sum(by[d] for d in E.S1254_READ) / len(E.S1254_READ)])
        v = viability(rows, be.K)
        if worst is None or worse(v) > worse(worst):
            worst = v
    return {"points": out, "viab": worst}


def health_ks(rows, fine_h=5 * 24, fine=60, coarse=360):
    """Row indices for a health line: every `fine` minutes for the first fine_h hours (the drain to the first floor),
    then every `coarse`, and the last row."""
    n = len(rows)
    ks = list(range(fine - 1, min(n, fine_h * 60), fine)) + list(range(fine_h * 60 + coarse - 1, n, coarse))
    return [0] + ks + ([n - 1] if ks and ks[-1] != n - 1 else [])


def drain_states(rows):
    """The drain states the replay opened, in order of first opening: [[age h, code]]."""
    out, seen = [], set()
    for r in rows:
        c = r.get("drain.state")
        if c and c not in seen:
            seen.add(c)
            out.append([r["age"], int(c)])
    return out


@job
def j_s2d():
    """S2d: from HUNGER 0 (FRESH), no food, the replay's water, 90 days (the lines end at the death, rule R-1): body
    mass at each day close,
    and health (the drain to its floors) hourly for five days, then every six hours."""
    rows, be = server_run([FRESH] + autodrops(90), 90 * DAY_MIN,
                          ("body.fm", "body.lm", "body.lx", "acute.bmi", "drain.bmi0"))
    days = pick(rows, day_ends(90), "body.fm", "body.lm", "body.lx", "acute.bmi")
    health = [[a / 24.0, hp] for _, a, hp in pick(rows, health_ks(rows), HEALTH)]
    out = {"days": days, "health": health, "hunger_max": max(r["HUNGER"] for r in rows), "states": drain_states(rows),
           "floor_age": floor_age(rows, be.K), "bmi0": max(r.get("drain.bmi0") or 0.0 for r in rows)}
    return _done(rows, be, out)


def floor_age(rows, K):
    """The age the drain first brings health to its first floor (K.drain.FIRST_FLOOR, within K.drain.HEAL_EPS)."""
    f = float(K.drain.FIRST_FLOOR) + float(K.drain.HEAL_EPS)
    return next((r["age"] for r in rows if r.get(HEALTH) is not None and r[HEALTH] <= f), None)


@job
def j_s2d_dry():
    """S2d's no-water arm: no food and no water from a fresh record at HUNGER 0 (FRESH) at 07:00, 8 days (the line
    ends at the death):
    health hourly, and the body-water deficit."""
    rows, be = server_run([FRESH], 8 * DAY_MIN, ("drain.dehydrated", "drain.starving"))
    ks = health_ks(rows, fine_h=8 * 24)
    pts = pick(rows, ks, HEALTH, "fluids.dehydPct")
    return _done(rows, be, {"health": [[a / 24.0, hp] for _, a, hp, d in pts],
                            "deficit": [[a / 24.0, d] for _, a, hp, d in pts], "states": drain_states(rows),
                            "floor_age": floor_age(rows, be.K),
                            "dehyd_age": next((r["age"] for r in rows if r.get("drain.dehydrated")), None),
                            "starve_age": next((r["age"] for r in rows if r.get("drain.starving")), None)})


def _nutrient_keys():
    K = KHost()
    order = K.NR.data.records.ORDER
    return [order[i] for i in range(1, len(order) + 1)]


def _tuna_days(days):
    return [eat(d * DAY_MIN + m, "Base.TunaTinOpen") for d in range(days) for m in TUNA_MIN] + autodrops(days)


def _grades(days, ev):
    keys = _nutrient_keys()
    paths = ["nutrients.%s.p" % k for k in keys] + ["nutrients.%s.g" % k for k in keys]
    dense = ("nutrients.vitC.p", "nutrients.vitC.g", "nutrients.thiamine.g")      # read every minute (the death row)
    rows, be = server_run(ev, days * DAY_MIN, paths, sparse=[p for p in paths if p not in dense])
    ends = day_ends(days)
    out = {"vitC_p": pick(rows, ends, "nutrients.vitC.p"), "vitC_g": pick(rows, ends, "nutrients.vitC.g")}
    gs = [(r["age"], r.get("nutrients.vitC.g")) for r in rows]
    out["vitC_g_steps"] = [[a, g] for (a, g), (_, p) in zip(gs[1:], gs) if g != p]   # the grade read every row
    first2 = {}
    for k in keys:
        for _, age, g in pick(rows, ends, "nutrients.%s.g" % k):
            if isinstance(g, (int, float)) and g >= 2:
                first2[k] = age / 24.0
                break
    out["first_grade2_day"] = first2
    out["states"] = drain_states(rows)
    out["floor_age"] = floor_age(rows, be.K)
    out["drain_last"] = next((r["age"] for r in reversed(rows) if r.get("drain.state")), None)
    out["thiamine_clinical"] = next((r["age"] for r in rows if r.get("nutrients.thiamine.g") == 4), None)
    out = _done(rows, be, out)
    da = out["viab"]["death_age"]
    if da is not None:                                    # the row at the death minute (row k ends at (k + 1) / 60)
        k = int(round(da * 60.0)) - 1
        if 0 <= k < len(rows):
            out["at_death"] = {"age": rows[k]["age"], "vitC_p": rows[k]["nutrients.vitC.p"],
                               "vitC_g": rows[k]["nutrients.vitC.g"]}
    out["viab"]["thiamine_g_max"] = max(int(r["nutrients.thiamine.g"]) for r in rows
                                       if isinstance(r.get("nutrients.thiamine.g"), (int, float)))
    return out


S3A_DAYS = 135


@job
def j_s3a():
    """S3a: four Base.TunaTinOpen a day at 08, 12, 16 and 20 and the replay's water, 135 days (to the scurvy death at
    day 130: the clinical grade at day 40 and K.drain.SCURVY_DEATH_H after it, Plan 15 Task 4b)."""
    return _grades(S3A_DAYS, _tuna_days(S3A_DAYS))


ORANGE_MIN = 180                       # 10:00


@job
def j_s3c():
    """S3c: S3a's diet to day 80 with one Base.Orange a day at 10:00 from day 45."""
    ev = _tuna_days(80) + [eat(d * DAY_MIN + ORANGE_MIN, "Base.Orange") for d in range(45, 80)]
    return _grades(80, ev)


VARIED = ("Base.Bread", "Base.CannedBologneseOpen", "Base.Burger", "Base.Apple", "Base.Orange", "Base.TunaTinOpen")


@job
def j_s3b():
    """S3b: four Base.TunaTinOpen a day for 7 days, then 7 days of four foods a day rotating through VARIED, water."""
    ev = [eat(d * DAY_MIN + m, "Base.TunaTinOpen") for d in range(7) for m in TUNA_MIN]
    ev += [eat(d * DAY_MIN + m, VARIED[(d * 4 + i) % len(VARIED)]) for d in range(7, 14)
           for i, m in enumerate(TUNA_MIN)]
    rows, be = server_run(ev + autodrops(14), 14 * DAY_MIN)
    return _done(rows, be, {"points": [[age / 24.0, u] for _, age, u in
                                       pick(rows, [0] + _ks(119, 14 * DAY_MIN, 120), "UNHAPPINESS")]})


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
    return _done(rows, be, {"days": days})


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
def j_s6a_real():
    """S6a's first day under NR.StimulantRealism Realistic (2): the fatigue offset its caffeine gives."""
    ev = [{"minute": m, "kind": "drink", "fluid": "Coffee", "litres": 0.25} for m in COFFEE_MIN] + request_meals(1)
    rows, be = server_run(ev + autodrops(1), DAY_MIN, ("acute.caf", "effects.fOff"), stimulants=2)
    if int(be.K.acute.C.MODE) != 2:
        raise D.ProvenanceError("S6a's Realistic arm ran stimulant set %s" % be.K.acute.C.MODE)
    ks = [0] + _ks(9, DAY_MIN, 10)
    return _done(rows, be, {"day1": [[age, c, f] for _, age, c, f in pick(rows, ks, "acute.caf", "effects.fOff")]})


@job
def j_s6a():
    """S6a: 0.25 L of Coffee at 08, 12 and 16 every day for 14 days, plate meals at the request and the water."""
    ev = [{"minute": d * DAY_MIN + m, "kind": "drink", "fluid": "Coffee", "litres": 0.25} for d in range(14)
          for m in COFFEE_MIN] + request_meals(14) + autodrops(14)
    rows, be = server_run(ev, 14 * DAY_MIN, ("acute.caf", "effects.fOff", "acute.cafTol"))
    out = {}
    for name, d in (("day1", 0), ("day14", 13)):
        ks = [d * DAY_MIN + k for k in [0] + _ks(9, DAY_MIN, 10)]
        out[name] = [[age - 24.0 * d, c, f] for _, age, c, f in pick(rows, ks, "acute.caf", "effects.fOff")]
    out["tol14"] = rows[14 * DAY_MIN - 1]["acute.cafTol"]
    out["tol"] = [[age / 24.0, t] for _, age, t in pick(rows, day_ends(14), "acute.cafTol")]
    return _done(rows, be, out)


BEER_MIN = (60, 80, 100, 120)          # four 0.3 L beers from 08:00, one every 20 minutes


def _s6b(stimulants):
    ev = [{"minute": m, "kind": "drink", "fluid": "Beer", "litres": 0.3} for m in BEER_MIN] + autodrops(1)
    rows, be = server_run(ev, DAY_MIN, ("acute.bac", "effects.intoxTarget", "acute.hang", "acute.hangH"),
                          stimulants=stimulants)
    if int(be.K.acute.C.MODE) != stimulants:
        raise D.ProvenanceError("S6b ran stimulant set %s, not %s" % (be.K.acute.C.MODE, stimulants))
    pts = pick(rows, [0] + _ks(9, DAY_MIN, 10), "acute.bac", "effects.intoxTarget", "acute.hang")
    hang = [r for r in rows if r.get("acute.hang") == 1]
    return _done(rows, be, {"points": [p for p in pts if None not in p],   # the first drain carries no effects yet
                            "peak": max(r.get("effects.intoxTarget") or 0.0 for r in rows),
                            "hang_h": (hang[-1]["age"] - hang[0]["age"] + 1 / 60.0) if hang else 0.0})


@job
def j_s6b():
    """S6b: four 0.3 L beers from 08:00, 20 minutes apart, under NR.StimulantRealism Game (1, the default)."""
    return _s6b(1)


@job
def j_s6b_real():
    """S6b's four beers under NR.StimulantRealism Realistic (2)."""
    return _s6b(2)


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
    """S6c: sleep on; nights 23:00-07:00 except the night after day 1 (03:00-07:00); plate meals at the request."""
    days = 4
    ev = _s6c_sleep(days) + request_meals(days) + autodrops(days)
    rows, be = server_run([e for e in ev if e["minute"] < days * DAY_MIN], days * DAY_MIN, ("acute.debtH",),
                          sleep_allowed=True)
    K = be.K
    return _done(rows, be, {"points": [[age / 24.0, float(K.satiety.sleepFactor(d)), d]
                                       for _, age, d in pick(rows, [0] + _ks(59, days * DAY_MIN, 60), "acute.debtH")]})


EXE_PATH = "_G.NutritionRevamp.server.fitness.exeType.admin"
SET_START, SET_MIN = 120, 30           # a burpee set from 09:00 for 30 minutes


@job
def j_sx2():
    ev = [{"minute": SET_START, "kind": "activity", "exercising": True},
          {"minute": SET_START, "kind": "setpath", "path": EXE_PATH, "value": "burpees"},
          {"minute": SET_START + SET_MIN, "kind": "activity", "exercising": False},
          {"minute": SET_START + SET_MIN, "kind": "setpath", "path": EXE_PATH, "value": None}]
    end = SET_START + SET_MIN + 121
    ev += [e for e in autodrops(1) if e["minute"] < end]
    rows, be = server_run(ev, end, ("satiety.S", "body.met"))
    mets = sorted({r["body.met"] for r in rows[SET_START:SET_START + SET_MIN]})
    after = [[k + 1 - (SET_START + SET_MIN), h, s] for k, _, h, s in
             pick(rows, _ks(SET_START + SET_MIN - 1, end, 5), "HUNGER", "satiety.S")]
    return _done(rows, be, {"set_mets": mets, "start_hunger": rows[SET_START - 1]["HUNGER"], "points": after})


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
    """Ten years at 20 sets a week, the protein factor pinned at 1.5: each week's lowest daily level (m-4: the weekly
    sampling hid the rust dip), the first day at level 10 and the first day after it below 10."""
    days = vanilla_strength(3650, 1.5, sets_events(3650))
    reach = next(d for d, lv, _ in days if lv >= 10)
    dip = next((d for d, lv, _ in days if d > reach and lv < 10), None)
    weekly = [[days[i][0], min(x[1] for x in days[i:i + 7])] for i in range(0, len(days), 7)]
    return {"weekly_min": weekly, "reach": reach, "dip": dip}


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

# ---- the vanilla-live and M1 series' reads (Task 8) ---------------------------------------------------------------------

RING_PAGES = {"x441": "1", "x442": "1,721,1441,2161", "x443a": "1,721", "x443b": "1,721", "x446": "1,721,1441",
              "x452": "1,721,1441"}


def ring_file(run):
    p = RING_PAGES[run]
    return "minute-ring-admin-%s.json" % (("{%s}" % p) if "," in p else p)


def ring_path(field):
    """A ring leaf: a dotted key in bracket form (a ring row's keys are flat dotted strings)."""
    return 'rows_list[*]["%s"]' % field if "." in field else "rows_list[*].%s" % field


def ring_read(run, field):
    """[(s, age, value)] of a ring field read through read() (the do-not-cite guard), rows de-duplicated by s across
    the pages, rows without the field left out."""
    f = ring_file(run)
    s, a, v = (read(run, f, ring_path(k)) for k in ("s", "age", field))
    if not len(s) == len(a) == len(v):
        raise D.ProvenanceError("%s's ring pages give %d s, %d age and %d %s" % (run, len(s), len(a), len(v), field))
    out, seen = [], set()
    for si, ai, vi in zip(s, a, v):
        if si in seen or not isinstance(ai, (int, float)) or not isinstance(vi, (int, float)):
            continue
        seen.add(si)
        out.append((si, ai, vi))
    return sorted(out)


def thin(rows, n, keep=()):
    """Every n-th row, the last row and any row whose age is in keep (a level change)."""
    out = [r for i, r in enumerate(rows) if i % n == 0 or i == len(rows) - 1 or r[1] in keep]
    return out


def level_rows(rows, level):
    """The rows' levels, with the ages where the level changes (so a thinned line keeps every step)."""
    lv = [(s, a, level(v)) for s, a, v in rows]
    changes = {lv[i][1] for i in range(1, len(lv)) if lv[i][2] != lv[i - 1][2]}
    changes |= {lv[i - 1][1] for i in range(1, len(lv)) if lv[i][2] != lv[i - 1][2]}
    return lv, changes


def x442_place():
    """V1b's model-equivalent placement: (the write's landing age, HUNGER at the first ring row after it, the hours a
    fresh character takes from HUNGER 0 to that value at the idle rate, VM1)."""
    w = read("x442", "starve.json", "writes[0].ages[1]")
    h = next(v for s, a, v in ring_read("x442", "HUNGER") if a >= w)
    return w, h, VM.hours_to_hunger(h)


H = "game hours"
DAYS = "game days"
HUNGER = "hunger (0-1)"


def every_n(pts, n):
    return pts[::n] + ([pts[-1]] if (len(pts) - 1) % n else [])


# ---- H1 --------------------------------------------------------------------------------------------------------------

def s_h1():
    r = VM.simulate({"hours": 6.0, "dt_min": 10.0, "start": {"hunger": 0.25},
                     "events": [{"t_h": 0.0, "kind": "eat", "hunger_script": -24.0}]})
    freeze = 0.24 * VM.FOOD_TIMER_PER_HUNGER / VM.food_timer_decay_per_s(90.0) / 60.0
    k = result("j_h1")
    viable("H1-m-kernel", "j_h1")
    return [
        series("H1-v-model", "Vanilla, from the game's code", H, HUNGER, "vanilla-model",
               [[0.0, 0.25]] + list(r["hunger"]), vmodel("VM1", "VM3", "VM4"),
               "HUNGER 0.25 at the eat of a whole Base.CannedBologneseOpen (-0.24, not cooked), drawn at x = 0 before "
               "the eat, as the mod's line is; after it HUNGER reads "
               "0.01, above its minimum, so the food-eaten timer is not filled and hunger rises at once. The second "
               "arm (an eat at 0.10, hunger to 0, timer 3120) freezes hunger for %.1f game minutes." % freeze),
        h1_live(),
        series("H1-m-kernel", "Nutrition Revamp, simulated by the mod's code", H, HUNGER, "kernel", k["points"],
               kernel({"replay": "fresh record from 07:00 with the replay's water, no food until the written HUNGER "
                                 "first reaches 0.25, then a whole Base.CannedBologneseOpen",
                       "request_minute": k["request_minute"], "water": [AUTODROP_G, list(AUTODROP_MIN)],
                       "eat": eat(k["request_minute"], "Base.CannedBologneseOpen"), "sleep_allowed": False}, "x452"),
               "The mod's replay from the request (x = 0 the read at the request, before the eat): the HUNGER it "
               "writes is the calibrated curve of its model's hunger (#3904), so a meal reads near empty. Proof x452, "
               "the same writer live on a three-meal day of cans (SH3, VALIDATION x452:HUNGER)."),
    ]


def h1_live():
    """V1a arm A: the ring's HUNGER from the can's landing to 6 h after it."""
    vcheck("H1-v-live")
    t0 = read("x441", "meal.json", "eats[0].landed_age")
    rows = [r for r in ring_read("x441", "HUNGER") if t0 <= r[1] <= t0 + 6.0 + 1e-9]
    return series("H1-v-live", "Vanilla, measured", H, HUNGER, "vanilla-live",
                  [[a - t0, v] for _, a, v in thin(rows, 10)],
                  artifact("x441", ring_file("x441"), "rows_list[*].HUNGER"),
                  "x441 arm A (build 42.21): a whole Base.CannedBologneseOpen at HUNGER 0.25, landed at world age "
                  "%.4f (eats[0].landed_age), x from it; every tenth ring row. The model re-run from the run's own "
                  "start matches every row within %.2g (VALIDATION x441:HUNGER arm A)."
                  % (t0, abs(vval("x441:HUNGER arm A")["miss"])))


# ---- H2 --------------------------------------------------------------------------------------------------------------

def h2_live():
    """V2 (x443a, x443b): the hourly weight reads over the 36 h, x in days from x443a's anchor."""
    vcheck("H2-v-live")
    anchor = read("x443a", "tuna-a.json", "checks.X.anchor")
    pts = []
    for run, f in (("x443a", "tuna-a.json"), ("x443b", "tuna-b.json")):
        pts += [[(a - anchor) / 24.0, w] for a, w in zip(read(run, f, "reads.nutrition[*].age"),
                                                        read(run, f, "reads.nutrition[*].weight"))]
    return series("H2-v-live", "Vanilla weight, measured", DAYS, "kg", "vanilla-live", pts,
                  artifact("x443a", "tuna-a.json", "reads.nutrition[*].weight"),
                  "x443a and x443b (build 42.21), one character over 36 game hours: the store written to 3000 kcal at "
                  "80 kg, then four Base.TunaTinOpen a day (also read: x443b-20261015-174712 `tuna-b.json` "
                  "`reads.nutrition[*].weight`, continuing it after a 0.28 h gap no session graded). It checks the store's arithmetic and the gain rate, not the "
                  "30-day line: weight %.3f to %.3f kg; the model matches every read within %.1g kg (VALIDATION "
                  "x443a:weight, x443b:weight)." % (pts[0][1], pts[-1][1], max(abs(vval("x443a:weight")["miss"]),
                                                                              abs(vval("x443b:weight")["miss"]))))


def burn_gap_per_h():
    """x442's calorie gap a game hour: the store's worst miss over the hours from the run's a0."""
    r = vval("x442:calorie store")
    return -r["miss"] / (r["at_age"] - read("x442", "starve.json", "model_inputs.a0"))


def plate_macros():
    """The plate's macros per kcal off the item pass's records (.per_item): {carbs, lipids, proteins} g a kcal."""
    tot = {"calories": 0.0, "carbs": 0.0, "lipids": 0.0, "proteins": 0.0}
    for pz in PLATE:
        for k in tot:
            tot[k] += food(pz)["per_item"][k]
    return {k: tot[k] / tot["calories"] for k in ("carbs", "lipids", "proteins")}


def _plate_eat(t_h, kcal):
    m = plate_macros()
    return {"t_h": t_h, "kind": "eat", "hunger_change": 0.0, "calories": kcal, "proteins": kcal * m["proteins"],
            "carbs": kcal * m["carbs"], "lipids": kcal * m["lipids"]}


WATER_NOTE = "water %.0f g every 2 game hours from 08:00 to 22:00" % AUTODROP_G
PLATE_NOTE = ("Meals are plates of the guide's foods and an orange (%s), every vector from the mod's table; %s."
              % (", ".join(p.split(".")[1] for p in PLATE), WATER_NOTE))


def s_h2():
    ev = [_plate_eat(24.0 * d + h, 500.0) for d in range(30) for h in (0.0, 5.0, 11.0)]
    r = VM.simulate({"hours": 720.0, "dt_min": DAY_MIN, "start": {"weight_kg": 80.0, "calories": 0.0}, "events": ev})
    days = result("j_h2")["days"]
    viable("H2", "j_h2")
    inp = {"replay": "30 days: plate meals of 500 kcal at 07, 12, 18 and the replay's water", "plate": list(PLATE),
           "water": [AUTODROP_G, list(AUTODROP_MIN)], "read": "each 07:00 day close", "sleep_allowed": False}
    note = "From the mod's no-trait creation body (lean 52.02 kg, fat 13.005 kg), sleep off. " + PLATE_NOTE
    return [
        series("H2-v-model", "Vanilla, from the game's code", DAYS, "kg", "vanilla-model",
               [[t / 24.0, w] for t, w in r["weight_kg"]], vmodel("VM6", "VM7", "VM8"),
               "80 kg, calorie store 0, three 500 kcal meals of the same plate's macros at 07, 12 and 18, awake idle "
               "all day: the idle day burns %.1f kcal at 80 kg, so the store climbs past the 1000 kcal gain threshold. "
               "The idle burn takes the thermoregulator's energy multiplier as 1 (#0464); live, a starving vanilla "
               "character's store fell %.2f kcal a game hour faster (x442, VALIDATION x442:calorie store), a gap the "
               "model does not explain."
               % (VM.burn_rate() * 86400, burn_gap_per_h())),
        h2_live(),
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
    v, dip = j["weekly_min"], j["dip"]
    h = KHost()
    K = h.K
    P = K.strength.DEFAULTS
    nat = float(K.strength.level(P.ffmiNaturalRaw * K.HEIGHT_M * K.HEIGHT_M, 1.0, P.Tmax, P))
    return [
        series("S4b-m-level", "Nutrition Revamp, perfect training", "game years", LEVEL, "kernel",
               [[r[0] / 365.0, r[1]] for r in d], kernel(s_inputs(sched, every=7), "x435"),
               "The body's continuous level, which passes 10; the perk shown stops at 10."),
        series("S4b-m-cap", "The body's natural cap", "game years", LEVEL, "kernel",
               [[r[0] / 365.0, r[6]] for r in d],
               kernel(s_inputs(sched, every=7, read="K.strength.level(body.Fc, body.N0, P.Tmax, P)"), "x435"),
               "The continuous level at the cap, above 10; the perk shown stops at 10."),
        series("S4b-v-model", "Vanilla, protein factor 1.5", "game years", LEVEL, "vanilla-model",
               [[day / 365.0, lv] for day, lv in v], vmodel("VM11", "VM12"),
               "20 sets a week at the protein factor pinned at 1.5: level 10 on day %.0f, then capped (#2109). Once "
               "capped a set's XP is discarded, so the rust timer is no longer pushed back: from day %.0f rust takes "
               "XP and the level dips from 10 to 9 between sets (code only, no live reading). Each point is its "
               "week's lowest daily level." % (j["reach"], dip)),
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
    L785 = next(r[1] for r in d if r[0] == 785)
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
               "S0618 (older men, 12 weeks trained, then 12 weeks detrained): -5 to -15 %% strength after the 12 "
               "weeks, drawn from the mod's day-365 strength on the level scale (K.strength.level is linear in "
               "strength), and the trained level back within 8 weeks of retraining. The mod regains more slowly: "
               "about %.1f after 8 weeks of retraining against %.2f trained, %.2f by day 910. Its detraining runs 52 weeks, "
               "so the timescales are not comparable." % (L785, L365, d[-1][1])),
        series("S4c-study-0078", "Strength after 20 weeks of detraining", DAYS, LEVEL, "study",
               [[365 + 140, 5.0], [365 + 140, L365]], study("S0078"),
               "S0078 (9 men, 10 women): after 20 weeks of detraining strength stayed above the untrained baseline "
               "while muscle size returned to it, by an amount the row does not give: drawn as the range from the "
               "baseline (level 5) to the trained level, never a value. On retraining, trained and untrained legs "
               "responded alike (no muscle-memory advantage)."),
    ]


def s_ss1():
    sets = (0.0, 3.0, 6.0, 10.0, 15.0, 20.0)
    m, v = [], []
    for S in sets:
        d = strength_days([(365, S, 1.6, 260.0)], every=365)
        m.append([S, d[-1][1]])
    for n in range(21):                                   # carry 4: vanilla's level at every whole set count
        S = float(n)
        vs = _vs(365, 1.0, S) if S > 0 else vanilla_strength(365, 1.0, [])
        v.append([S, vs[-1][1]])
    return [
        series("SS1-m-kernel", "Nutrition Revamp", "hard sets a week", "Strength level after a year", "kernel", m,
               kernel(s_inputs([(365, "S", 1.6, 260.0)], sets=list(sets)), "x435"),
               "1.6 g/kg protein, +260 kcal a day; the body's continuous level. The protein gate is full from "
               "%.1f g/kg (K.strength.PROTEIN_FULL), so 2.0 g/kg gives the same year (H3)."
               % float(KHost().K.strength.PROTEIN_FULL)),
        series("SS1-v-model", "Vanilla", "hard sets a week", "Strength level after a year", "vanilla-model", v,
               vmodel("VM11", "VM12"),
               "Push-up sets at the protein factor pinned at 1, a point at every whole set count; with no sets, rust "
               "takes level 5 to 4 in the year."),
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
    viable("S1a-m-kernel", "j_s1a")
    return [
        series("S1a-v-model", "Vanilla, from the game's code", "game hours from 07:00", HUNGER, "vanilla-model",
               r["hunger"], vmodel("VM1", "VM3", "VM4"),
               "HUNGER 0 at 07:00, a Base.TunaTinOpen (-0.18) at 08, 12, 16 and 20."),
        s1a_live(),
        series("S1a-m-kernel", "Nutrition Revamp, simulated by the mod's code", "game hours from 07:00", HUNGER,
               "kernel", k["points"],
               kernel({"start": FRESH, "replay": "fresh record from HUNGER 0 at 07:00, a whole Base.TunaTinOpen at 08, 12, 16, 20 and the "
                                 "replay's water", "eat": eat(0, "Base.TunaTinOpen"),
                       "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}, "x452")),
    ]


def s1a_live():
    """V2's first 24 h of tins (x443a, then x443b), x placed so the first tin sits at 08:00 as the model's."""
    vcheck("S1a-v-live")
    t0 = read("x443a", "tuna-a.json", "eats[0].landed_age")
    rows = [r for run in ("x443a", "x443b") for r in ring_read(run, "HUNGER") if t0 - 1.0 <= r[1] <= t0 + 23.0]
    return series("S1a-v-live", "Vanilla, measured", "game hours from 07:00", HUNGER, "vanilla-live",
                  [[a - t0 + 1.0, v] for _, a, v in thin(rows, 10)],
                  artifact("x443a", ring_file("x443a"), "rows_list[*].HUNGER"),
                  "Build 42.21: x443a's four Base.TunaTinOpen at the anchor plus 0, 4, 8 and 12 game hours, then "
                  "x443b's ring (also read: x443b-20261015-174712 `%s` `rows_list[*].HUNGER`) after a 0.28 h gap, "
                  "with no tin in the drawn 24 h; x moved so the first tin (world age %.4f) sits "
                  "at 08:00 like the model's; its store was written to 3000 kcal first, which hunger does not read "
                  "(#0501). The model matches every row within %.1g (VALIDATION x443a:HUNGER, x443b:HUNGER)."
                  % (ring_file("x443b"), t0, max(abs(vval("x443a:HUNGER")["miss"]), abs(vval("x443b:HUNGER")["miss"]))))


def s_s1b():
    r = VM.simulate({"hours": 36.0, "dt_min": 10.0, "start": {"hunger": 0.0}})
    k = result("j_s1b")
    v = viable("S1b-m-kernel", "j_s1b", drain=True)
    steps = [VM.hours_to_hunger(t) for t in VM.HUNGRY_THRESHOLDS]
    K = KHost().K
    onset = float(K.drain.STARVE_ONSET_H)
    return [
        series("S1b-v-model", "Vanilla Hungry moodle", "game hours from a fresh start", "moodle level (0-4)",
               "vanilla-model", with_steps(r["hungry_level"], steps), vmodel("VM1", "VM5"),
               "From HUNGER 0, no food: levels at %s game hours (each step a point of its own beside the "
               "10-minute points)." % ", ".join("%.2f" % t for t in steps)),
        s1b_live_v(),
        series("S1b-m-kernel", "Nutrition Revamp, the Hungry moodle", "game hours from a fresh start",
               "moodle level (0-4)", "kernel", k["points"],
               kernel({"replay": "fresh record from HUNGER 0 at 07:00, no food, the replay's water, 36 h",
                       "start": FRESH, "path": "HUNGER",
                       "read": "vanilla's Hungry level of the written HUNGER (#0508)",
                       "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}, "x454"),
               "The game's own Hungry moodle read off the HUNGER the mod writes (the mod's Energy moodle is gone), a "
               "fresh HEAD record from HUNGER 0 at 07:00 as vanilla's line starts: the mod seeds its meal pool from "
               "the HUNGER it finds (#3913), and an empty stomach cannot write so low a hunger, so the writer lands "
               "its seed plate first, the curve fit's plate of the guide's foods sized to the least kcal whose first "
               "write is within the dead zone of it (W.seedPlate, Plan 15 Task 13 fix 1): here %.1f kcal. It starts at "
               "level %d. The levels step at %s game hours; level 4, "
               "Starving, comes at %.2f h, when the starvation state opens after %g hours with the meal pool empty "
               "(K.drain.STARVE_ONSET_H) and the hunger cap lifts. The live x454, its unfed clock set near the onset, "
               "showed Starving within 3 game minutes of the state opening (#3937)."
               % (k["seed_kcal"], k["first"], ", ".join("%.2f" % a for a, _ in k["steps"]), v["drain"][0], onset)),
    ]


def with_steps(points, steps):
    """A level series' points with a point at each exact step age (the level it steps to), so the data holds the
    step where the note puts it."""
    out = [list(p) for p in points]
    for t in steps:
        lv = next(v for x, v in points if x > t)
        out.append([t, lv])
    return sorted(out, key=lambda p: (p[0], p[1]))


def s1b_live_v():
    """V1b (x442): the ring's HUNGRY level from its 0.60 start, placed at the hours a fresh character takes to 0.60."""
    vcheck("S1b-v-live")
    w, h, t_eq = x442_place()
    rows = [r for r in ring_read("x442", "HUNGER") if r[1] >= w and r[1] - w + t_eq <= 36.0 + 1e-9]
    lv, changes = level_rows(rows, lambda x: VM.moodle_level(x, VM.HUNGRY_THRESHOLDS))
    return series("S1b-v-live", "Vanilla Hungry moodle, measured", "game hours from a fresh start",
                  "moodle level (0-4)", "vanilla-live", [[a - w + t_eq, l] for _, a, l in thin(lv, 30, changes)],
                  artifact("x442", ring_file("x442"), "rows_list[*].HUNGER"),
                  "x442 (build 42.21): HUNGER written to %.4f (the ring's first row after the write) and no food; "
                  "its level is counted off HUNGER at the game's thresholds (#0508) and placed at %.2f h, the hours a "
                  "fresh character takes to reach it (VM1). Level 4 came %.2f game h after the write; the model's "
                  "crossing is within %.4f h (VALIDATION x442:HUNGRY 4 crossing (game h))."
                  % (h, t_eq, vval("x442:HUNGRY 4 crossing (game h)")["live"] - w,
                     abs(vval("x442:HUNGRY 4 crossing (game h)")["miss"])))


def s_s1c():
    r = VM.simulate({"hours": 24.0, "dt_min": 10.0, "start": {"thirst": 0.0}})
    k = result("j_s1c")
    v = viable("S1c-m-kernel", "j_s1c", thirst=True)
    adm("x446:THIRST")
    return [
        series("S1c-v-model", "Vanilla, from the game's code", H, "thirst (0-1)", "vanilla-model", r["thirst"],
               vmodel("VM5"), "Linear from 0 at 8.0e-6 a game-second."),
        series("S1c-m-kernel", "Nutrition Revamp, simulated by the mod's code", H, "thirst (0-1)", "kernel",
               k["points"], kernel({"replay": "fresh record from 07:00, no drink, 24 h", "path": "THIRST",
                                    "sleep_allowed": False}, "x457"),
               "No drink by design: the guard holds the replay alive, at any dehydration (it reaches %.2f %% of body "
               "mass). A fresh HEAD record from 07:00 on the water base by lean mass, 2000 g a day at rest for the "
               "no-trait body (#3909). Proof x457, whose ring's water loss the server's basal scale predicted with and "
               "without the thirst traits (#3942); the older rings, x364 and x446, ran the earlier water base and fail "
               "at HEAD (VALIDATION x446:THIRST)." % v["max_dehydPct"]),
        s1c_live_v(),
    ]


def s1c_live_v():
    """V1a (x441): the ring's THIRST from the write of THIRST 0 (A_set) on, 8 h with no drink."""
    vcheck("S1c-v-live")
    a0, sc = vinputs("x441")
    w = a0 + next(e["t_h"] for e in sc["events"] if e.get("label") == "A_set")
    rows = [r for r in ring_read("x441", "THIRST") if r[1] >= w]
    return series("S1c-v-live", "Vanilla, measured", H, "thirst (0-1)", "vanilla-live",
                  [[a - w, v] for _, a, v in thin(rows, 10)],
                  artifact("x441", ring_file("x441"), "rows_list[*].THIRST"),
                  "x441 (build 42.21): THIRST written to 0 at world age %.4f (writes[0]), then no drink for %.1f game "
                  "hours (two cans of bolognese, which carry no thirst change, were eaten in it); x from the write. "
                  "The model matches every row within %.2g (VALIDATION x441:THIRST)."
                  % (w, rows[-1][1] - w, abs(vval("x441:THIRST")["miss"])))


# ---- S2 --------------------------------------------------------------------------------------------------------------

def s_s2a():
    meals = [0.0, 5.0, 11.0]
    ev = [{"t_h": h, "kind": "eat", "hunger_script": -24.0} for h in meals + [13.0]]
    ev += [{"t_h": 13.0 + h, "kind": "eat", "hunger_script": -24.0} for h in (36.0, 40.0, 46.0)]
    r = VM.simulate({"hours": 13.0 + 60.0, "dt_min": 10.0, "start": {"hunger": 0.0}, "events": ev})
    k = result("j_s2a")
    v = viable("S2a-m-kernel", "j_s2a", drain=True)
    last_h = k["last_meal_minute"] / 60.0
    return [
        series("S2a-v-model", "Vanilla, from the game's code", "game hours from the last meal", HUNGER,
               "vanilla-model", [[t - 13.0, x] for t, x in r["hunger"]], vmodel("VM1", "VM3", "VM4"),
               "A Base.CannedBologneseOpen at 07, 12 and 18 and a last at 20:00 that takes HUNGER to 0 (the timer "
               "filled), no food for 36 h, then the same meals at 08, 12 and 18."),
        s2a_live(r),
        series("S2a-m-kernel", "Nutrition Revamp, simulated by the mod's code", "game hours from the last meal",
               HUNGER, "kernel", k["points"],
               kernel({"replay": "test_replay_live_oracle.fast_plans() fast arm on the default body, its meals plates",
                       "plate": list(PLATE), "water": [AUTODROP_G, "every 2 h, 09:00-23:00"], "clock": "minute 0 is 00:00",
                       "sleep_allowed": False}, "x452"),
               "Three warm days at maintenance, day 0 at maintenance, day 1 without food, days 2-3 at the request. "
               "The day without food opens the starvation state %.2f h after the last meal, when the meal pool has "
               "been empty for %g hours (K.drain.STARVE_ONSET_H, #3902): HUNGER lifts to Starving and health drains "
               "toward the first floor until the next meal ends the state, %.2f health in all. "
               % (v["drain"][0] - last_h, float(KHost().K.drain.STARVE_ONSET_H), 100.0 - v["min_health"])
               + PLATE_NOTE.replace("08:00 to 22:00", "09:00 to 23:00") + " " + proof_note("S2a-m-kernel")),
    ]


def s2a_live(r):
    """V1b (x442) placed on the S2a model's fast: from where the model's rising HUNGER first reaches the run's start."""
    vcheck("S2a-v-live")
    w, h, _ = x442_place()
    pts = [(t - 13.0, x) for t, x in r["hunger"] if t >= 13.0]
    x_star = next(x0 + (x1 - x0) * (h - y0) / (y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]) if y0 < h <= y1)
    rows = [q for q in ring_read("x442", "HUNGER") if q[1] >= w and x_star + q[1] - w <= 36.0 + 1e-9]
    return series("S2a-v-live", "Vanilla, measured", "game hours from the last meal", HUNGER, "vanilla-live",
                  [[x_star + a - w, v] for _, a, v in thin(rows, 10)],
                  artifact("x442", ring_file("x442"), "rows_list[*].HUNGER"),
                  "x442 (build 42.21): HUNGER written to %.4f and no food; placed at %.2f h, where the model's fast "
                  "first reaches it, and drawn to the fast's end. The model matches every row within %.2g "
                  "(VALIDATION x442:HUNGER)." % (h, x_star, abs(vval("x442:HUNGER")["miss"])))


def s_s2b():
    k = result("j_s2b")
    v = viable("S2b-m-kernel", "j_s2b", drain=True)
    return [
        series("S2b-m-kernel", "Nutrition Revamp, simulated by the mod's code", "day after the fast",
               "intake / the fed arm's", "kernel", [["day 2", k["r2"]], ["day 3", k["r3"]]],
               kernel({"replay": "test_replay_live_energy.fast_server()'s two arms, its meals plates, with water",
                       "plate": list(PLATE), "water": [AUTODROP_G, "every 2 h, 09:00-23:00"],
                       "body": "the oracle's 70 kg man (MAN)", "sleep": "23:00-07:00, the oracle's protocol"}, "x27g"),
               "Sleep on, 23:00-07:00 (the oracle's protocol); the oracle's 70 kg man, the body its bands were fitted "
               "on; its meals plates of real foods with water (rule R-1). The proof run's fast (x271, x272) fails the "
               "admission test at HEAD (VALIDATION). The fast arm's skipped day opens the starvation state briefly "
               "before its next meal (%.2f health, #3902)." % (100.0 - v["min_health"])),
        series("S2b-study-1613", "Johnstone 2002", "day after the fast", "intake / the fed arm's", "study",
               [["day 2", 12.2 / 10.2]], study("S1613"), "12.2 against 10.2 MJ on the day after a 36 h fast."),
        series("S2b-study-1614", "Clayton 2016", "day after the fast", "intake / the fed arm's", "study",
               [["day 2", 1.07], ["day 3", 1.0]], study("S1614"),
               "7 % more on day 2 and no difference on day 3 after a day at 25 % of requirements."),
    ]


def s_s2c():
    k = result("j_s2c")
    viable("S2c-m-kernel", "j_s2c")
    base = k["points"][0][1]
    xs = [x for x, _ in k["points"]]
    DO = _kt("deficit_oracles")
    per = DO.S1254_KCAL_PER_KG
    return [
        series("S2c-v-model", "Vanilla, from the game's code", "kg of fat lost", "extra kcal a day", "vanilla-model",
               [[0.0, 0.0], [max(xs), 0.0]], vmodel("VM14"), "No hunger term reads a body store."),
        series("S2c-m-kernel", "Nutrition Revamp, simulated by the mod's code", "kg of fat lost", "extra kcal a day",
               "kernel", [[x, y - base] for x, y in k["points"]],
               kernel({"replay": "test_replay_live_energy.fat_loss_intake()'s protocol, its meals plates, with water",
                       "depletions": list(S1254_DEP), "plate": list(PLATE), "water": [AUTODROP_G, "every 2 h, 09:00-23:00"],
                       "sleep": "23:00-07:00, the oracle's protocol"}, "x436"),
               "The no-trait body's fat set lower; intake at the request over days 2-4 less the full body's; sleep on, "
               "the oracle's protocol; plates of real foods with water (rule R-1)."),
        series("S2c-study", "Polidori 2016", "kg of fat lost", "extra kcal a day", "study",
               [[x, per * x] for x in (0.0, max(xs))], study("S1254"),
               "About 100 kcal a day per kg of weight lost, 125 per kg of fat (S2208, S2206; "
               "deficit_oracles.S1254_KCAL_PER_KG); the oracle's band is a factor of 1.5 either way."),
    ]


def s2d_live_health(model_death):
    """V1b (x442): the quarter-hourly health reads, placed at the hours a fresh character takes to the run's start."""
    vcheck("S2d-v-live-health")
    w, h, t_eq = x442_place()
    hp = [(a, v) for a, v in zip(read("x442", "starve.json", "reads.health[*].age"),
                                 read("x442", "starve.json", "reads.health[*].overall"))
          if isinstance(v, (int, float)) and a >= w]
    dead = next(a for a, v in hp if v <= 0.0)
    return series("S2d-v-live-health", "Vanilla health, measured", DAYS, "health", "vanilla-live",
                  [[(a - w + t_eq) / 24.0, v] for a, v in hp if a <= dead],
                  artifact("x442", "starve.json", "reads.health[*].overall"),
                  "x442 (build 42.21): HUNGER written to %.4f, thirst held at 0, no food; health read every quarter "
                  "hour, placed at %.2f h, the hours a fresh character takes to that hunger. Health read 0 %.2f game h "
                  "after the write (its previous read was a quarter hour earlier): day %.2f on this axis, the model's "
                  "%.2f." % (h, t_eq, dead - w, (dead - w + t_eq) / 24.0, model_death / 24.0))


def _vanilla_fast():
    """S2d's vanilla run: HUNGER from 0, no food, 0.25 L of water every 4 h, a fresh 80 kg character (store 800),
    1-minute steps to its death (VM10; the weight floor, #3881, is not reached first)."""
    ev = [{"t_h": float(h), "kind": "drink", "fluid": "water", "litres": 0.25} for h in range(4, 72, 4)]
    sim = VM.simulate({"hours": 72.0, "dt_min": 1.0, "start": {"hunger": 0.0}, "events": ev})
    death = next(t for t, x in sim["health"] if x <= 0)
    return sim, death


def s_s2d():
    sim, death = _vanilla_fast()
    hourly = [[t / 24.0, x] for t, x in sim["health"][::60] if t < death] + [[death / 24.0, 0.0]]
    weight = [[t / 24.0, w] for t, w in sim["weight_kg"][::1440] if t < death]
    weight.append([death / 24.0, next(w for t, w in sim["weight_kg"] if t >= death)])
    samples = read("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].weight")
    ages = read("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].worldAge")
    store0 = read("scen", "scenario-nutrition_3day_fast.json", "test.samples[0].calories")
    k = result("j_s2d")
    v = viable("S2d-m-mass", "j_s2d", death=True)
    kd = result("j_s2d_dry")
    vd = viable("S2d-m-dry", "j_s2d_dry", death=True, thirst=True)
    K = KHost().K
    mass = until_death([[a / 24.0, fm + lm + lx] for _, a, fm, lm, lx, bmi in k["days"]], v)
    mass.append([v["death_age"] / 24.0, mass[-1][1]])
    hp = until_death(k["health"], v) + [[v["death_age"] / 24.0, 0.0]]
    hd = until_death(kd["health"], vd) + [[vd["death_age"] / 24.0, 0.0]]
    first = float(K.drain.FIRST_FLOOR)
    water = {"water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False, "start": FRESH}
    return [
        series("S2d-v-model-health", "Vanilla health", DAYS, "health", "vanilla-model", hourly,
               vmodel("VM1", "VM5", "VM10"),
               "HUNGER from 0, no food, water every 4 h; level 4 at 34.84 h, then -3.564 health a game hour at "
               "DayLength 4 with no regeneration: death at %.2f game days (%.1f h); the line ends there." % (
                   death / 24.0, death)),
        series("S2d-v-model-weight", "Vanilla weight", DAYS, "kg", "vanilla-model", weight,
               vmodel("VM6", "VM7", "VM8"),
               "A fresh 80 kg character (calorie store 800), no food: the store falls toward its -2200 floor and the "
               "weight with it, until the hunger death at %.2f game days ends the line (S2d-v-model-health). Below "
               "35 kg the game clamps the weight and drains health (Nutrition.setWeight, #3881); a fast never "
               "reaches it before the hunger death. Live, a starving character's store fell %.2f kcal a game hour "
               "faster than the model's (x442): the one term the model leaves out that can raise the idle burn is the "
               "thermoregulator's energy multiplier, taken as 1 here (#0464, never below 1); the run read no thermal "
               "total, so that cause is unmeasured."
               % (death / 24.0, burn_gap_per_h())),
        s2d_live_health(death),
        series("S2d-v-live-weight", "Vanilla weight, measured", DAYS, "kg", "vanilla-live",
               [[(a - ages[0]) / 24.0, w] for a, w in zip(ages, samples)],
               artifact("scen", "scenario-nutrition_3day_fast.json", "test.samples[*].weight"),
               "Build 42.20.4, vanilla Nutrition on, hunger pinned (a control, #0500), so this character did not die; "
               "its calorie store started at %g (test.samples[0].calories), the model's at 800; x from "
               "test.samples[*].worldAge." % store0),
        series("S2d-m-mass", "Nutrition Revamp body mass", DAYS, "kg", "kernel", mass,
               kernel(dict(water, replay="90 days, no food, the replay's water", path="body.fm + body.lm + body.lx"),
                      "x434"),
               "The mod's no-trait creation body with water and no food. Its fatal state is %s: health is gone at "
               "day %.2f, where the line ends (S2d-m-drain). Its HUNGER reached %.2f: the cap lifts when the "
               "starvation state opens (#3906)." % (v["death_name"], v["death_age"] / 24.0, k["hunger_max"])),
        series("S2d-m-drain", "Nutrition Revamp health, with water", DAYS, "health", "kernel", hp,
               kernel(dict(water, replay="90 days, no food, the replay's water", path="the stand-in's overall health",
                           read="100 less ReduceGeneralHealth plus AddGeneralHealth (#3898's spread)"), "x454"),
               "The same fast's health. The starvation state opens after %g unfed hours (K.drain.STARVE_ONSET_H), at "
               "%.2f h, when Starving shows; health drains %g a game day (K.drain.STARVE_RATE, a game choice) to the "
               "first floor of %g, reached on day %.2f, then follows the floor as the body's BMI falls from %.2f at "
               "the onset: %g at BMI %g (K.drain.BMI_KNEE), and 0 at BMI %g, the death point (S2234). The fatal state "
               "is %s: health is gone at day %.2f, where the line ends. The live x454, its unfed clock set near the "
               "onset, drained %.4g a game day to the first floor and held it (#3938)."
               % (float(K.drain.STARVE_ONSET_H), v["drain"][0], float(K.drain.STARVE_RATE), first,
                  k["floor_age"] / 24.0, k["bmi0"], float(K.drain.SLEEP_FLOOR), float(K.drain.BMI_KNEE),
                  float(K.drain.BMI_DEATH), v["death_name"], v["death_age"] / 24.0,
                  read("x454", "starve.json", "verdicts.DRAIN_RATE.observed.rate_per_day"))),
        series("S2d-m-dry", "Nutrition Revamp health, without water", DAYS, "health", "kernel", hd,
               kernel({"replay": "8 days, no food and no water, a fresh record from 07:00", "sleep_allowed": False,
                       "start": FRESH,
                       "path": "the stand-in's overall health",
                       "read": "100 less ReduceGeneralHealth plus AddGeneralHealth (#3898's spread)"}, "x456"),
               "No food and no water from a fresh record at 07:00 (HUNGER 0). The dehydration state opens at a %g %% "
               "body-water deficit, at %.2f h, when Parched shows, and the starvation state at %.2f h; the first floor "
               "of %g is reached at %.2f h. The dehydration floor deepens with the deficit, %g at 15 %% and 0 at the death "
               "point of 17 %% (a game choice inside 15-19 %%, K.drain.DEHYD_KNOTS). The fatal state is %s: health is "
               "gone at day %.2f (%.1f h), where the line ends. The live x456, its deficit set near the onset, "
               "drained %.4g a game day to the floor and held it (#3940, #3941)."
               % (float(K.drain.DEHYD_KNOTS[1][1]), kd["dehyd_age"], kd["starve_age"], first, kd["floor_age"],
                  float(K.drain.SLEEP_FLOOR), vd["death_name"], vd["death_age"] / 24.0, vd["death_age"],
                  read("x456", "water.json", "verdicts.DEHYD_DRAIN.observed.rate_per_day"))),
    ]


# ---- S3 --------------------------------------------------------------------------------------------------------------

VITC_CLINICAL = 0.15                   # NR_Data_Records vitC ladder[3]
PADAYATTY = "Padayatty 2016 (Hodges 1971's controlled series)"
BY_CONSTRUCTION = ("The mod's vitamin C rate k is fitted to this 40 days (NR_Data_Records: K.nutrients.calib(0.15, 40)), "
                   "so the kernel agrees with it by construction.")


def death_note(v, floor_age=None):
    """The drain and the death of a diet's replay (Plan 15: a drain is damage to a floor; health is gone only at the
    state's death point)."""
    if v["drain"] is None:
        return "The replay stays alive and hydrated over the window and opens no drain (rule R-1)."
    opened = "Its drain opens with %s on day %.2f" % (v["drain_name"], v["drain"][0] / 24.0)
    if floor_age is not None:
        opened += ", health reaching the first floor on day %.2f" % (floor_age / 24.0)
    if v["death"] is None:
        return opened + "; health holds at or above its floor and the replay stays alive over the window (rule R-1)."
    return ("%s. This diet kills: its fatal state is %s, and health is gone at day %.2f, where the lines end (rule "
            "R-1)." % (opened, v["death_name"], v["death_age"] / 24.0))


def s_s3a():
    k = result("j_s3a")
    v = viable("S3a", "j_s3a", death=True)
    firsts = sorted((d, n) for n, d in k["first_grade2_day"].items() if n != "vitC")[:2]
    inp = {"replay": "%d days, four Base.TunaTinOpen a day at 08, 12, 16, 20 and the replay's water" % S3A_DAYS,
           "eat": eat(0, "Base.TunaTinOpen"), "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}
    others = "; ".join("%s marginal from day %.0f" % (n, d) for d, n in firsts) or "no other record marginal"
    return [
        series("S3a-m-pool", "Vitamin C store", DAYS, "vitamin C store (0-1)", "kernel",
               to_death([[a / 24.0, p] for _, a, p in k["vitC_p"]], v, k["at_death"]["vitC_p"]),
               kernel(dict(inp, path="nutrients.vitC.p"), "x151r"),
               "Proof x151r (the Plan 4 build, OnsetSpeed 30: G11); vitamin C is never scaled by OnsetSpeed. The "
               "first other records to reach grade 2 on this diet: %s. %s" % (others, death_note(v, k["floor_age"]))),
        series("S3a-m-grade", "Vitamin C grade", DAYS, "grade (1 replete - 4 clinical)", "kernel",
               to_death(sorted([[a / 24.0, g] for _, a, g in k["vitC_g"]]
                               + [[a / 24.0, g] for a, g in k["vitC_g_steps"]]), v, k["at_death"]["vitC_g"]),
               kernel(dict(inp, path="nutrients.vitC.g"), "x151r"), death_note(v, k["floor_age"])),
        series("S3a-study-0224", "Padayatty 2016: one self-experimenter", DAYS, "vitamin C store (0-1)", "study",
               [[161.0, VITC_CLINICAL]], study("S0224"),
               "161 days to scurvy signs, drawn at the clinical store 0.15."),
        series("S3a-study-0225", PADAYATTY, DAYS, "vitamin C store (0-1)", "study",
               [[40.0, VITC_CLINICAL]], study("S0225"),
               "About 40 days to scurvy signs, drawn at the clinical store 0.15. " + BY_CONSTRUCTION),
    ]


def s_s3b():
    sessions = read("x34r", "rows.json", "row13.days.days.{0,1,2,3,4,5,6}.session")
    ok = {r: adm(r + ":mood")["admitted"] for r in ("x341", "x342", "x343")}
    days = [d for d, r in enumerate(sessions) if ok.get(r)]
    if not days or days != list(range(len(days))):
        raise D.ProvenanceError("S3b draws the leading days of the admitted runs: %r" % (days,))
    alt = "{%s}" % ",".join(str(d) for d in days)
    u = read("x34r", "rows.json", "row13.days.days.%s.server_U" % alt)
    b = read("x34r", "rows.json", "row13.days.days.%s.moodLast_b" % alt)
    k = result("j_s3b")
    viable("S3b-m-kernel-U", "j_s3b")
    drawn = sorted({sessions[d] for d in days})
    note = ("Days %d-%d from %s, which pass%s the admission test; the later days' runs (%s) fail it at HEAD and are not "
            "drawn (the mood floor's dead zone, Plan 15 Task 9, moves x342's UNHAPPINESS by up to %.2f). The eats were "
            "TKX.Mono450." % (days[0], days[-1], " and ".join(drawn), "" if len(drawn) > 1 else "es",
                              ", ".join(r for r in ("x341", "x342", "x343") if not ok[r]),
                              adm("x342:mood")["max_miss"]["UNHAPPINESS"]))
    alt_u = "row13.days.days.%s.server_U" % alt
    alt_b = "row13.days.days.%s.moodLast_b" % alt
    return [
        series("S3b-m-live-U", "Unhappiness, measured", DAYS, "unhappiness (0-100)", "live",
               list(enumerate(u)), artifact("x34r", "rows.json", alt_u), note),
        series("S3b-m-live-B", "Boredom target, measured", DAYS, "boredom (0-100)", "live",
               list(enumerate(b)), artifact("x34r", "rows.json", alt_b),
               note + " BOREDOM itself is reset-bounded by the driver, so the remembered target is plotted."),
        s3b_live("S3b-v-live-U", "UNHAPPINESS", "Vanilla unhappiness, measured", "unhappiness (0-100)"),
        s3b_live("S3b-v-live-B", "BOREDOM", "Vanilla boredom, measured", "boredom (0-100)"),
        series("S3b-m-kernel-U", "Unhappiness, simulated by the mod's code", DAYS, "unhappiness (0-100)", "kernel",
               k["points"],
               kernel({"replay": "7 days of four Base.TunaTinOpen a day, then 7 days of four foods a day rotating "
                                 "through " + ", ".join(VARIED) + ", with the replay's water", "path": "UNHAPPINESS",
                       "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}, "x342"),
               ("The x34 chain, #3683. " + proof_note("S3b-m-kernel-U")).strip()),
    ]


def s3b_live(sid, field, label, unit):
    """V2 (x443a, x443b): the ring's mood stat over the 36 h of tuna, x in days from the first tin."""
    t0 = read("x443a", "tuna-a.json", "eats[0].landed_age")
    rows = [r for run in ("x443a", "x443b") for r in ring_read(run, field) if r[1] >= t0]
    vals = [v for _, _, v in rows]
    return series(sid, label, DAYS, unit, "vanilla-live", [[(a - t0) / 24.0, v] for _, a, v in thin(rows, 30)],
                  artifact("x443a", ring_file("x443a"), "rows_list[*].%s" % field),
                  "x443a, then x443b's ring (also read: x443b-20261015-174712 `%s` `rows_list[*].%s`) after a "
                  "0.28 h gap (build 42.21): seven Base.TunaTinOpen over 36 game "
                  "hours, standing idle; %s read %.4g to %.4g. The rise is the idle character's, not the food's: the "
                  "game's Base.TunaTinOpen script carries no boredom or unhappiness change, and vanilla has no "
                  "monotony term. The vanilla model has no mood, so the line is ungraded."
                  % (ring_file("x443b"), field, field, min(vals), max(vals)))


def s_s3c():
    k = result("j_s3c")
    v = viable("S3c", "j_s3c", drain=True)
    kc = int(KHost().K.drain.CLINICAL)
    return [
        series("S3c-m-pool", "Vitamin C store", DAYS, "vitamin C store (0-1)", "kernel",
               until_death([[a / 24.0, p] for _, a, p in k["vitC_p"] if a / 24.0 >= 40.0 - 1e-9], v),
               kernel({"replay": "S3a's diet to day 80, one Base.Orange a day at 10:00 from day 45",
                       "orange": eat(0, "Base.Orange"), "water": [AUTODROP_G, list(AUTODROP_MIN)],
                       "path": "nutrients.vitC.p", "sleep_allowed": False}, "x151r"),
               "Vitamin C turns Clinical (grade %d) on day %.2f, which opens the scurvy drain; the orange from day 45 "
               "lifts it, and the drain's last minute is on day %.2f, so the floor never deepens toward S3a's death. "
               "The thiamine grade stays at %d at worst. %s"
               % (kc, v["drain"][0] / 24.0, k["drain_last"] / 24.0, v["thiamine_g_max"],
                  death_note(v, k["floor_age"]))),
        series("S3c-study", "Ververs 2019", DAYS, "vitamin C store (0-1)", "study",
               [[45.0, VITC_CLINICAL], [52.0, VITC_CLINICAL]], study("S0229"),
               "Symptoms improved within one week of treatment: drawn as the week from the first orange (day 45 to "
               "52), not a value; the study gives no store."),
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
    for name in S5B:
        viable("S5b-" + name, "j_s5b_" + name)
    inp = {"replay": "90 days from the creation body, plate meals at the request at 08, 13, 20 and the replay's water",
           "plate": list(PLATE), "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}
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
                      with_steps([[t / 24.0, lv] for t, lv in v["strength_level"]], [first]),
                      vmodel("VM11", "VM12", "VM13"),
                      "No XP: a fresh character's rust timer climbs from -50 000 and its first rust step takes level 5 "
                      "to 4 at day %.1f, a point of its own beside the daily points (code only, no live reading)."
                      % first))
    return out


def s_s5c():
    g = result("j_s5b_gaunt")["days"][:31]
    n = result("j_s5b_none")["days"][:31]
    es = read("x436", "creation.json", "verdicts.36_{d,e,f}_hunger.observed.es")
    viable("S5c-gaunt", "j_s5b_gaunt")
    viable("S5c-none", "j_s5b_none")
    inp = {"replay": "S5b's", "path": "body.energyState", "plate": list(PLATE), "sleep_allowed": False}
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
    kr = result("j_s6a_real")
    viable("S6a", "j_s6a")
    viable("S6a-m-offset-real", "j_s6a_real")
    cup = VM.fatigue_change(0.25)
    inp = {"replay": "0.25 L Coffee at 08, 12, 16 every day for 14 days, plate meals at the request and the replay's "
                     "water", "plate": list(PLATE), "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False}
    return [
        series("S6a-m-day1", "Caffeine on day 1", "game hours from 07:00", "caffeine (mg)", "kernel",
               [[x, c] for x, c, f in k["day1"]], kernel(dict(inp, path="acute.caf", day=1), "x161f"),
               "Proof x151r (the 5.0 h half-life, #2982) and x161f (#3077), the Plan 4-5 builds (G10); M2 reads it "
               "at HEAD."),
        series("S6a-m-day14", "Caffeine on day 14", "game hours from 07:00", "caffeine (mg)", "kernel",
               [[x, c] for x, c, f in k["day14"]], kernel(dict(inp, path="acute.caf", day=14), "x161f"),
               "The tolerance (tau 7 days) reads %.3f by day 14; the 5 h half-life and the tolerance are game choices "
               "on open rows (S0851, S1123), so no study is drawn." % k["tol14"]),
        series("S6a-m-tolerance", "Caffeine tolerance", DAYS, "tolerance (0-1)", "kernel", k["tol"],
               kernel(dict(inp, path="acute.cafTol", read="each 07:00 day close"), "x161f"),
               "The same replay's tolerance at each day close: it relaxes, tau 7 days, toward the 7-day mean of the "
               "daily caffeine absorbed over %d mg a day (K.acute.CAF_TOL_REF, CAF_MEAN_H), reading %.3f on day 14; a game choice on open rows (S0851, "
               "S1123), so no study is drawn." % (int(float(KHost().K.acute.CAF_TOL_REF)), k["tol"][-1][1])),
        series("S6a-v-model", "Vanilla FATIGUE per cup", "game hours from 07:00", "fatigue change", "vanilla-model",
               [[1.0, cup], [5.0, cup], [9.0, cup]], vmodel("VM15"),
               "-0.025 a 0.25 L cup, the same on day 14. It holds only with sleep allowed and needed: under the "
               "display default (sleep off) vanilla resets FATIGUE every update (#3009)."),
        series("S6a-m-offset", "Fatigue relief, Game (the default)", "game hours from 07:00", "fatigue change",
               "kernel", [[x, f] for x, c, f in k["day1"] if f is not None],
               kernel(dict(inp, path="effects.fOff", day=1, stimulants="Game (NR.StimulantRealism 1, the default)"),
                      "x161f"),
               "The fatigue offset the day-1 caffeine gives under the default Game strengths (#3921): its largest "
               "relief %.4f, against vanilla's %.4f a cup. The timing is the same in both modes; only the size "
               "differs (a game choice, open S1124)." % (min(f for x, c, f in k["day1"] if f is not None), cup)),
        series("S6a-m-offset-real", "Fatigue relief, Realistic", "game hours from 07:00", "fatigue change", "kernel",
               [[x, f] for x, c, f in kr["day1"] if f is not None],
               kernel(dict(inp, replay="day 1 of the same schedule", path="effects.fOff", day=1,
                           stimulants="Realistic (NR.StimulantRealism 2)"), "x161f"),
               "The same day under the Realistic strengths, the pharmacological sizes Plan 14 shipped (#3921): its "
               "largest relief %.4f." % min(f for x, c, f in kr["day1"] if f is not None)),
    ]


def s_s6b():
    ev = [{"t_h": m / 60.0, "kind": "drink", "fluid": "beer", "litres": 0.3} for m in BEER_MIN]
    r = VM.simulate({"hours": 24.0, "dt_min": 1.0, "start": {}, "events": ev})
    g = result("j_s6b")
    k = g["points"]
    real = result("j_s6b_real")
    viable("S6b", "j_s6b")
    viable("S6b-m-intox-real", "j_s6b_real")
    inp = {"replay": "four 0.3 L Beer at 08:00, 08:20, 08:40, 09:00, with the replay's water",
           "water": [AUTODROP_G, list(AUTODROP_MIN)], "sleep_allowed": False,
           "stimulants": "Game (NR.StimulantRealism 1, the default)"}
    return [
        series("S6b-v-model", "Vanilla intoxication", H, "intoxication (0-100)", "vanilla-model", r["intoxication"],
               vmodel("VM16"),
               "400 x alcohol x the hunger factor a drink, each beer's 6 added at once; decay 45.36 a game hour at "
               "DayLength 4, so a beer is gone in about 8 game minutes (1-minute output). Live the game adds a can "
               "over its drink, so the decay starts at the first sip and a can peaks lower (x445b: %.2f against 6); "
               "spread over each can's live span the model lands every peak and the zero (VALIDATION x445b)."
               % vval("x445b:INTOXICATION peak, can 1")["live"]),
        s6b_live(),
        series("S6b-m-bac", "Blood alcohol", H, "blood alcohol (%)", "kernel", [[a, b] for _, a, b, i, hg in k],
               kernel(dict(inp, path="acute.bac"), "x161f")),
        series("S6b-m-intox", "Intoxication the mod writes, Game (the default)", H, "intoxication (0-100)", "kernel",
               [[a, i] for _, a, b, i, hg in k], kernel(dict(inp, path="effects.intoxTarget"), "x161f"),
               "The writer's target (#3086) under the default Game strengths (#3921): it peaks at %.2f. The blood "
               "alcohol and its clearance are the same in both modes." % g["peak"]),
        series("S6b-m-hangover", "Hangover, Game (the default)", H, "hangover (0 or 1)", "kernel",
               [[a, hg] for _, a, b, i, hg in k], kernel(dict(inp, path="acute.hang"), "x447r"),
               "Under Game the hangover lasts %.2f game hours; Realistic's lasts %.2f (#3921). A live session read the "
               "hangover start where the mod's code puts it: x447's ring and the HEAD replay of its own drinks both "
               "first at world age %.4f (x447-regrade-20261015, the proof run, the six drinks drunk live put back; "
               "#3891)." % (g["hang_h"], real["hang_h"],
                            read("x447r", "regrade.json", "verdicts.M2r_hangover.observed.live_age"))),
        series("S6b-m-intox-real", "Intoxication the mod writes, Realistic", H, "intoxication (0-100)", "kernel",
               [[a, i] for _, a, b, i, hg in real["points"]],
               kernel(dict(inp, path="effects.intoxTarget", stimulants="Realistic (NR.StimulantRealism 2)"), "x161f"),
               "The same four beers under the Realistic strengths, the pharmacological sizes Plan 14 shipped (#3921): "
               "it peaks at %.2f." % real["peak"]),
    ]


def s6b_live():
    """V4b (x445b): INTOXICATION's polls over four back-to-back beers, x placed so the first sip sits at 08:00."""
    vcheck("S6b-v-live")
    t0 = read("x445b", "beers.json", "drinks[0].before.worldAge")
    ages, vals = read("x445b", "beers.json", "checks.B.polls[*].age"), read("x445b", "beers.json", "checks.B.polls[*].intox")
    return series("S6b-v-live", "Vanilla intoxication, measured", H, "intoxication (0-100)", "vanilla-live",
                  [[a - t0 + 1.0, v] for a, v in zip(ages, vals)],
                  artifact("x445b", "beers.json", "checks.B.polls[*].intox"),
                  "x445b (build 42.21, DayLength 4, sleep on): four 0.3 L beers back to back, not 20 minutes apart as "
                  "the model's; x moved so the last read before the first sip (world age %.4f) sits at 08:00. "
                  "INTOXICATION peaked at %s after cans 1 to 4 (each can's dose stacking on what was left of the last); "
                  "the decay ran %.2f a game hour against the model's 45.36 (VALIDATION x445b)."
                  % (t0, ", ".join("%.2f" % vval("x445b:INTOXICATION peak, can %d" % i)["live"] for i in range(1, 5)),
                     -vval("x445b:INTOXICATION decay a game hour")["live"]))


def s_s6c():
    k = result("j_s6c")["points"]
    viable("S6c-m-kernel", "j_s6c")
    debt = read("x30g", "rows.json", "row11.closes[*].debt_after")
    ages = read("x30g", "rows.json", "row11.closes[*].age_after")
    for r in ("x301", "x302"):
        adm(r + ":sleep")
    last = k[-1]
    return [
        series("S6c-m-kernel", "Nutrition Revamp hunger factor", DAYS, "hunger factor", "kernel",
               [[d, f] for d, f, _ in k],
               kernel({"replay": "sleep on: nights 23:00-07:00, the night after day 1 03:00-07:00; plate meals at "
                                 "the request and the replay's water", "plate": list(PLATE),
                       "water": [AUTODROP_G, list(AUTODROP_MIN)], "path": "acute.debtH",
                       "read": "K.satiety.sleepFactor(acute.debtH)", "sleep_allowed": True}, "x30g"),
               "The debt is repaid slowly (K.acute.REPAY): it still reads %.2f h at day 4, so the factor holds at %.2f "
               "for days after the one short night, where S1566 measured the next day alone." % (last[2], last[1])),
        series("S6c-m-live", "Sleep debt, measured", DAYS, "sleep debt (h)", "live",
               [[a / 24.0, d] for a, d in zip(ages, debt)], artifact("x30g", "rows.json", "row11.closes[*].debt_after"),
               "Sleep on. x301 and x302's debts at each window close; they pass the admission test on the sleep "
               "kernel; x from row11.closes[*].age_after."),
        series("S6c-v-model", "Vanilla", DAYS, "hunger factor", "vanilla-model", [[0.0, 1.0], [4.0, 1.0]],
               vmodel("VM14"), "No sleep term reads hunger: a flat 1."),
        series("S6c-study", "Brondel 2010", DAYS, "intake / the rested day's", "study",
               [[2.0, 1.22], [2.0 + 16.0 / 24.0, 1.22]], study("S1566"),
               "22 % more energy eaten on the day after one 4 h night, drawn over that waking day (07:00 to 23:00 "
               "after the 03:00-07:00 night)."),
    ]


# ---- systems ---------------------------------------------------------------------------------------------------------

def s_se1():
    adm("x363:fill")
    liq = read("x363", "minute-ring-admin-1.json", 'rows_list[*]["stomach.liquid"]')
    fill = read("x363", "minute-ring-admin-1.json", "rows_list[*].stomachFill")
    ages = read("x363", "minute-ring-admin-1.json", "rows_list[*].age")
    ss = read("x363", "minute-ring-admin-1.json", "rows_list[*].s")
    a0 = ages[0]
    rep = adm_rows("x363:fill")
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
    adm("x361:HUNGER")
    return [
        series("SH1-m-kernel", "Nutrition Revamp, simulated", "meal kcal", "minutes to the hunger request", "kernel",
               list(zip(kc, k)), kernel({"replay": "test_satiety_meal_studies.callahan()",
                                         "preloads_kcal": list(kc), "clock": "09:00"}, "x452"),
               "Callahan's liquid preloads at 09:00, from the request, on the model's own hunger (h_model), the value "
               "the study oracles read; the game is shown its calibrated curve of it (#3904), whose cadence SH3 draws. "
               "x361's live interval ran an earlier writer and fails at HEAD (VALIDATION x361:HUNGER)."),
        series("SH1-study-1247", "Callahan 2004", "meal kcal", "minutes to the hunger request", "study",
               [[190.0, 247.0], [400.0, 286.0], [825.0, 321.0]], study("S1247"),
               "Preloads of 7.5, 16 and 33 % of daily energy, drawn at the replay's 190, 400 and 825 kcal."),
        series("SH1-study-1248", "Cummings 2004", "meal kcal", "minutes to the hunger request", "study",
               [[650.0, 320.0], [650.0, 425.0]], study("S1248"),
               "320-425 min from a scheduled lunch to a freely requested dinner; the lunch's energy is not given, so "
               "the range is drawn at the 650 kcal meal #3700's 240-300 min anchor reads."),
    ]


SH3_MEALS = ("lunch", "dinner", "breakfast")
PECKISH, HUNGRY_T = VM.HUNGRY_THRESHOLDS[0], VM.HUNGRY_THRESHOLDS[1]      # 0.15 and 0.25 (#0508, strictly over)
X452_MEAL = ("Base.CannedBologneseOpen", "Base.Banana")                   # x452's meal: a can and a banana


def first_over(pts, a0, a1, thr):
    """Hours from a0 to the first (age, value) in (a0, a1] with value strictly over thr (x45g_lib.first_return's rule);
    None when none."""
    return next((a - a0 for a, v in pts if a0 < a <= a1 and isinstance(v, (int, float)) and v > thr), None)


def sh3_vanilla(meal_ages, h0, tail_h=12.0):
    """vanilla_model on x452's meals, each a whole can and a banana at the run's own meal ages (their HungerChange
    and Calories off the game's script), from the ring's HUNGER h0 before lunch: each meal's Peckish and Hungry
    returns, the last meal's window running tail_h hours past it."""
    ev = []
    for t in meal_ages:
        for full in X452_MEAL:
            m, it = full.split(".")
            ev.append({"kind": "eat", "t_h": t - meal_ages[0],
                       "hunger_script": float(D.read_dataset(FOOD_SCRIPT, "%s.%s.HungerChange" % (m, it))),
                       "calories": float(D.read_dataset(FOOD_SCRIPT, "%s.%s.Calories" % (m, it)))})
    hours = meal_ages[-1] - meal_ages[0] + tail_h
    H = VM.simulate({"hours": hours, "dt_min": 1.0, "start": {"hunger": h0}, "events": ev})["hunger"]
    out = []
    for i, t in enumerate(meal_ages):
        s0 = t - meal_ages[0]
        e = (meal_ages[i + 1] - meal_ages[0]) if i + 1 < len(meal_ages) else hours
        out.append((first_over(H, s0, e, PECKISH), first_over(H, s0, e, HUNGRY_T)))
    return out


def s_sh3():
    """SH3: x452's three-meal day (Plan 15 Task 11): each meal's return to Peckish and dinner's to Hungry, measured live,
    in the HEAD replay of the run's own inputs, and in the vanilla model on the same meals."""
    rec = adm("x452:HUNGER")
    f = "day.json"
    ages = read("x452", f, "verdicts.CAD_FEEL_P.observed.windows[*].meal_age")
    labels = read("x452", f, "verdicts.CAD_FEEL_P.observed.windows[*].label")
    live_p = read("x452", f, "verdicts.CAD_FEEL_P.observed.windows[*].ret")
    live_h = read("x452", f, "verdicts.CAD_FEEL_H.observed.windows[*].ret")
    if tuple(labels) != SH3_MEALS:
        raise D.ProvenanceError("x452's windows are %r, not %r" % (labels, SH3_MEALS))
    rows = adm_rows("x452:HUNGER")
    pts = sorted((v[0], v[1]) for v in rows.values() if v[0] is not None)
    end = pts[-1][0]
    ends = list(ages[1:]) + [end]
    ker = [(first_over(pts, a, e, PECKISH), first_over(pts, a, e, HUNGRY_T)) for a, e in zip(ages, ends)]
    h0 = [v for _, a, v in ring_read("x452", "HUNGER") if a <= ages[0]][-1]
    van = sh3_vanilla(list(ages), h0)
    inp = {"replay": "x452's own inputs at HEAD (start.json, events.json, player.json, its ring's clock)",
           "meals": "a whole Base.CannedBologneseOpen and a Base.Banana at 12:30, 18:30 and 07:30",
           "read": "hours from each can's landing row to the first row with HUNGER over 0.15 (Peckish) or 0.25 "
                   "(Hungry), inside the meal's window"}
    common = ("Each meal a whole can of bolognese and a banana, then half a litre of water 2.5 h after it (x452, the "
              "mod at this build, DayLength 1, sleep off).")
    return [
        series("SH3-v-model", "Vanilla, from the game's code: Peckish", "meal", "game hours", "vanilla-model",
               [[m, p] for m, (p, _) in zip(SH3_MEALS, van) if p is not None], vmodel("VM1", "VM3", "VM4"),
               "The vanilla model at the default day length (DayLength 4; the run played DayLength 1) on the same meals at "
               "the run's own meal times, from the ring's HUNGER at lunch's "
               "landing row (%.4f); each can and banana take their script HungerChange off at once and fill the food "
               "timer, which holds hunger still until it runs out. The breakfast window runs 12 h past it. Hungry "
               "after dinner at %.2f h (SH3-v-model-hungry). The mod's meals wear off sooner than vanilla's; in the "
               "curve's fit, on three 667 kcal meals a day, dinner wore off soonest (#3944), from the evening's "
               "circadian rise in hunger (S1273), a stated bend." % (h0, van[1][1])),
        series("SH3-m-kernel", "Nutrition Revamp, simulated: Peckish", "meal", "game hours", "kernel",
               [[m, p] for m, (p, _) in zip(SH3_MEALS, ker) if p is not None], kernel(inp, "x452"),
               "The HEAD replay of x452's own inputs, which reproduces the run's HUNGER within %.2g (VALIDATION "
               "x452:HUNGER). %s" % (rec["max_miss"]["HUNGER"], common)),
        series("SH3-m-live", "Nutrition Revamp, measured: Peckish", "meal", "game hours", "live",
               list(zip(SH3_MEALS, live_p)),
               artifact("x452", f, "verdicts.CAD_FEEL_P.observed.windows[*].ret"),
               "x452's Peckish returns (#3933), read off the ring's HUNGER from each can's landing row. %s" % common),
        series("SH3-v-model-hungry", "Vanilla, from the game's code: Hungry", "meal", "game hours", "vanilla-model",
               [["dinner", van[1][1]]], vmodel("VM1", "VM3", "VM4"),
               "Dinner's return to Hungry (HUNGER over 0.25) in the same vanilla model run (SH3-v-model)."),
        series("SH3-m-kernel-hungry", "Nutrition Revamp, simulated: Hungry", "meal", "game hours", "kernel",
               [["dinner", ker[1][1]]], kernel(dict(inp, meal="dinner, to the next morning's breakfast"), "x452"),
               "Dinner's return to Hungry in the HEAD replay of x452 (SH3-m-kernel); the lunch and breakfast windows "
               "end before Hungry."),
        series("SH3-m-live-hungry", "Nutrition Revamp, measured: Hungry", "meal", "game hours", "live",
               [["dinner", live_h[0]]], artifact("x452", f, "verdicts.CAD_FEEL_H.observed.windows[*].ret"),
               "x452's dinner, Hungry %.2f game hours after the can (#3933). %s" % (live_h[0], common)),
    ]


def s_sh2():
    k = result("j_sh2")
    adm("x276:HUNGER")
    return [
        series("SH2-m-kernel", "Nutrition Revamp, simulated", "arm", "mean hunger over 24 h / three meals'", "kernel",
               [["three meals", 1.0], ["six meals", k["six"] / k["three"]]],
               kernel({"replay": "x276's events.json from its start.json at HEAD (six meals) against its three-meal "
                                 "arm (x27_grade.row8)", "window": "world age 25 to 49"}, "x276"),
               "x276's start record loads at HEAD; its own live means fail the admission test and are not drawn. "
               + proof_note("SH2-m-kernel")),
        series("SH2-study", "Ohkawara 2013", "arm", "mean hunger over 24 h / three meals'", "study",
               [["three meals", 1.0], ["six meals", 41850.0 / 36612.0]], study("S1608"),
               "Hunger AUC 41850 on six meals against 36612 on three."),
    ]


def s_st1():
    r = VM.simulate({"hours": 10.0, "dt_min": 10.0, "start": {"thirst": 0.0}})
    k = [p for p in result("j_s1c")["points"] if p[0] <= 10.0 + 1e-9]
    viable("ST1-m-kernel", "j_s1c", thirst=True)
    return [
        series("ST1-v-model", "Vanilla, from the game's code", H, "thirst (0-1)", "vanilla-model", r["thirst"],
               vmodel("VM5")),
        series("ST1-m-kernel", "Nutrition Revamp, simulated", H, "thirst (0-1)", "kernel", k,
               kernel({"replay": "fresh record from 07:00 at rest, no drink, the first 10 h", "path": "THIRST",
                       "sleep_allowed": False}, "x364"),
               "No drink by design (alive, any dehydration: rule R-1); proof x364 as S1c (VALIDATION x364:THIRST)."),
    ]


def s_st2():
    path = "sodium.by_day.{1,2,3,4,5}.na_change_per_24h"
    na = read("x28g", "rows.json", path)
    for r in ("x281", "x282", "x283", "x284"):
        adm(r + ":na")
    return [
        series("ST2-m-live-na", "Body sodium, measured", DAYS, "mmol a day", "live", list(zip(range(1, 6), na)),
               artifact("x28g", "rows.json", path),
               "x281-x284 pass the admission test on the record's sodium balance (exact at HEAD)."),
        series("ST2-m-kernel", "Nutrition Revamp, simulated", DAYS, "mmol a day", "kernel", result("j_st2")["points"],
               kernel({"function": "test_sodium_balance.simulate(days=5, na_day=0)",
                       "body": "the 80 kg reference man"}, "x28g")),
    ]


def s_sm1():
    adm("x343:mood")
    rows = adm_rows("x343:mood")
    a0 = read("x34r", "rows.json", "row13.release.from_age")
    a1 = read("x34r", "rows.json", "row13.release.to_age")
    pts = [[(v[0] - a0), v[1]] for s, v in sorted(rows.items(), key=lambda kv: float(kv[0]))
           if v[0] is not None and a0 <= v[0] <= a1 and v[1] is not None]
    return [
        series("SM1-m-kernel", "Nutrition Revamp, simulated", "game hours after the last repeat", "unhappiness",
               "kernel", every_n(pts, 30),
               kernel({"replay": "x343's events.json from its start.json at HEAD", "path": "UNHAPPINESS",
                       "window": "row13.release from_age to to_age", "sleep_allowed": False}, "x343"),
               "The replay of x343's own inputs at HEAD; x343's ring fails the admission test there (VALIDATION "
               "x343:mood), so its live line is not drawn and no passing proof run exists for this one."),
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
            "85 kg: 59.5 and 25.5 (30 %). The y scale: -3 Emaciated, -2 Very Underweight (vanilla) / Gaunt (mod), "
            "-1 Underweight / Overly Lean, 0 none, 1 Overweight / Overfat, 2 Obese.")
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
    adm("x37g:met")
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
    viable("SX2-m-kernel", "j_sx2")
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
                                 "exercising, a setpath of %s to burpees), then rest, with the replay's water"
                                 % EXE_PATH, "path": "HUNGER", "water": [AUTODROP_G, list(AUTODROP_MIN)],
                       "billed_met": k["set_mets"], "sleep_allowed": False}, "x29g"),
               "The set billed 7.5 MET a minute (K.energy.EXERCISE_MET.burpees). " + proof_note("SX2-m-kernel")),
    ]


def s_sd1():
    h = KHost()
    K = h.K
    pts, rate, death_h = scurvy_line(h)
    adm("x161b:drain")
    first = float(K.drain.FIRST_FLOOR)
    return [
        series("SD1-m-kernel", "Nutrition Revamp", DAYS, "health", "kernel", pts,
               kernel({"function": "K.drain.floor and K.drain.rate", "state": "scurvy (K.drain.SCURVY), vitamin C at "
                       "the clinical grade from day 0, nothing else wrong", "from": "full health at the onset"}, "x454"),
               "Days from the clinical grade: health drains %.4g a game day (K.drain.rate, a game choice) to the first "
               "floor of %g, reached on day %.2f; the floor holds for %g game hours (K.drain.DEF_HOLD_H), deepens to %g "
               "two days before the death point and reaches 0 at %g game hours, day %.0f, where the line ends: the "
               "death at a time the studies leave open (S1168), a game choice. The drain engine is the one x454 and "
               "x456 read live for starvation and dehydration (#3938, #3941); scurvy's own drain has no live reading "
               "on this build (x161b read the Plan 5 drain, VALIDATION x161b:drain)."
               % (rate, first, (100.0 - first) / rate, float(K.drain.DEF_HOLD_H), float(K.drain.SLEEP_FLOOR), death_h,
                  death_h / 24.0)),
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


def sd2_left():
    """The records sd2_days does not step (another kind, or no rate)."""
    recs = KHost().NR.data.records
    out = []
    for i in range(1, len(recs.ORDER) + 1):
        rec = recs.REC[recs.ORDER[i]]
        if rec.kind != "pool" or rec.k is None:
            out.append("%s (%s)" % (recs.ORDER[i], rec.kind))
    return out


def s_sd2():
    rows = sd2_days()
    left = ", ".join(sd2_left())
    inp = {"function": "K.nutrients.stepPool and K.nutrients.grade a day from p = 1 at zero intake, dial 1",
           "records": "NR.data.records, kind pool"}
    return [
        series("SD2-m-marginal", "Days to Marginal", "nutrient", "days", "kernel",
               [[k, d2] for k, d2, d4 in rows if d2 is not None], kernel(inp, "x151r"),
               "The pool records at OnsetSpeed 1. Left out, being of another kind: %s." % left),
        series("SD2-m-clinical", "Days to Clinical", "nutrient", "days", "kernel",
               [[k, d4] for k, d2, d4 in rows if d4 is not None], kernel(inp, "x151r"),
               "Left out, being of another kind: %s." % left),
        series("SD2-study", PADAYATTY, "nutrient", "days", "study", [["vitC", 40.0]], study("S0225"),
               "Vitamin C is the record whose rate is calibrated on an onset study (scurvy at about 40 days); the "
               "other records rest on half-lives or game choices. " + BY_CONSTRUCTION),
    ]


def s_sc1():
    for r in ("x301", "x302"):
        adm(r + ":sleep")
    labels = read("x30g", "rows.json", "row11.nights[*].label")
    booked = read("x30g", "rows.json", "row11.nights[*].booked_h")
    debt = read("x30g", "rows.json", "row11.closes[*].debt_after")
    sess = read("x30g", "rows.json", "row11.closes[*].session")
    s_after = read("x30g", "rows.json", "row11.closes[*].s_after")
    kern = []
    for lab, se, s in zip(labels, sess, s_after):
        rows = adm_rows(se + ":sleep")
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
    m = [[g, int(K.view.fullnessLevel(float(g)))] for g in range(0, 2501, 10)]
    adm("x401:level")
    adm("x453b:level")
    mass = read("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass")
    lv = read("x401", "accept.json", "verdicts.OF.observed.rows[*].levels")
    mb = read("x453b", "overfull.json", "verdicts.OF_REACH.observed.post_mass")
    lb = read("x453b", "overfull.json", "verdicts.OF_REACH.observed.post_levels")
    return [
        series("SV1-m-kernel", "Nutrition Revamp", "grams in the stomach", "moodle level (0-4)", "kernel", m,
               kernel({"function": "K.view.fullnessLevel(mass)", "grams": [0, 2500, 10]}, "x453b"),
               "The stomach's whole mass, both lanes (#3915). The physical capacities stay on mass; a food's plate "
               "volume moves only how much it fills you (#3910). At level 3 the mod caps endurance and at level 4 it "
               "refuses eating through the game's own gate and brings nausea (#3914, #3935)."),
        series("SV1-m-live", "Measured", "grams in the stomach", "moodle level (0-4)", "live",
               list(zip(mass, lv)), artifact("x401", "accept.json", "verdicts.OF.observed.rows[*].server_mass"),
               "x401's rows with the level the client showed (verdicts.OF.observed.rows[*].levels; #3778); each "
               "equals K.view.fullnessLevel at HEAD (VALIDATION)."),
        series("SV1-m-live-b", "Measured, this build", "grams in the stomach", "moodle level (0-4)", "live",
               list(zip(mb, lb)), artifact("x453b", "overfull.json", "verdicts.OF_REACH.observed.post_mass"),
               "x453b (the mod at this build): one broccoli took the stomach to Overfull 4 (verdicts.OF_REACH."
               "observed.post_levels; #3935); the level equals K.view.fullnessLevel at HEAD (VALIDATION "
               "x453b:level)."),
    ]


# ======================================================================================================================
# Task 7: the vanilla model (tools/vanilla_model.py at HEAD) against the vanilla runs x441-x445b, quantity by quantity
# ======================================================================================================================
# Each record (kind "vanilla"): the run, the quantity, the model's value and the live value at the worst point, the miss
# (live less model), the relative miss, the tolerance with its source (the run's own, x44_guide_lib's named constants,
# set before any run), whether every compared point is within it, and the cause of a miss: a jar read where one
# explains it (the model is then fixed from the read, never fitted to the run), else the chart's stated limitation.
# The model re-runs from each run's own `model_inputs` (its start state, settings and events) through the run's own
# chain (x44_guide_lib.model_chain); the live values are read off the artifact through read() (the do-not-cite guard).

VRUN_FILE = {"x441": "meal.json", "x442": "starve.json", "x443a": "tuna-a.json", "x443b": "tuna-b.json",
             "x444": "strength.json", "x445": "drinks.json", "x445b": "beers.json"}
SRC_LIB = "the run's own: x44_guide_lib.%s, named before the run"
CAUSE_PLACEMENT = ("the eat's placement: the run puts the model's eat at the landing poll and the engine's fill lands "
                   "about 8 game seconds later (24 units at 3 a game-second); the fill itself, 0.24 x 13000 = 3120, is "
                   "the game's (#0054). No jar term moves it, so the chart states it.")
CAUSE_FLOOR = ("the game's timer has no floor: BodyDamage.Update takes the multiplier off it only while it is above 0 "
               "(#0529), so its last step leaves it a little under 0 (-2.40 live) where the model floors it at 0; the "
               "moodle reads it against 0 either way (#0511).")
CAUSE_BURN = ("the idle burn's thermoregulator term: updateCalories multiplies the idle and asleep burn by the "
              "thermoregulator's energy multiplier (#0187, #0455), which is 1 plus 0.05 and 0.10 times the squared "
              "primary and secondary totals on the cold side (#0464); the model takes it as 1, and a value 1.2 % above "
              "1 would account for the gap; unmeasured: the run read no thermal total, and x441 and x443a/b show the "
              "same sign at about a third of the rate. The model is not fitted to it: the vanilla weight and store "
              "lines state it as a candidate.")
CAUSE_SPREAD = ("the drink's spread: the drink action calls DrinkFluid a step at a time for the part not yet drunk "
                "(#0085, #2925), so the alcohol enters over the drink and the decay (#2922) runs from the first sip. "
                "The model now spreads a drink with a duration over it (VM16); with each can spread over its live span "
                "the zero and the peaks land on the live reads. Each can's drink is taken to end at its live peak "
                "poll and to start between the run's last read before it and its first rising poll (inputs read off "
                "the run, not a fitted constant); the peaks test the height at that time, and the zero, which depends "
                "only on the first sip and the dose, is the timing test.")
CAUSE_FREEZE = ("row resolution: the first ring row above FREEZE_EPS (0.0005) sits a row past the live unfreeze (s391 "
                "reads 0.000414 at 8.8668); the live timer's own zero, 8.8545, is the model's 8.8524 within 8 game "
                "seconds, the placement above.")


def _lib():
    p = os.path.join(REPO, "testing", "experiments")
    if p not in sys.path:
        sys.path.insert(0, p)
    import x44_guide_lib
    return x44_guide_lib


def vinputs(run):
    """(a0, scenario) of a vanilla run's own model inputs."""
    mi = read(run, VRUN_FILE[run], "model_inputs")
    return mi["a0"], json.loads(json.dumps(mi["scenario"]))


def vchain(run, events=None):
    """(a0, scenario, model): the run's own model chain at HEAD, its events replaced when given."""
    a0, sc = vinputs(run)
    if events is not None:
        sc["events"] = events
    return a0, sc, _lib().model_chain(sc)


def vrec(run, quantity, model, live, tol, src, n=1, at=None, within=None, cause=None, draws=(), miss=None, how="abs"):
    """A vanilla validation record; miss is live less model unless given."""
    if miss is None:
        miss = live - model
    if within is None:
        within = abs(miss) <= tol
    rel = abs(miss) / abs(live) if isinstance(live, (int, float)) and live else None
    return {"kind": "vanilla", "key": "%s:%s" % (run, quantity), "run": RUN[run], "quantity": quantity,
            "model": model, "live": live, "miss": miss, "rel_miss": rel, "n": n, "at_age": at,
            "tolerance": [how, tol], "tolerance_source": src, "within": bool(within), "cause": cause,
            "draws": list(draws)}


def vring(run):
    return _ring(os.path.join(REPO, "testing", "artifacts", RUN[run]))[0]


def v_curve(run, field, series, window, a0, model, skip, tol, src, draws=(), cause=None):
    """A ring field against the model in a window, rows within EVENT_SKIP_H of an event skipped (the run's grade)."""
    L = _lib()
    worst, n, ok = None, 0, True
    for r in vring(run):
        a, v = r.get("age"), r.get(field)
        if not isinstance(v, (int, float)) or a < window[0] - 1e-9 or a > window[1] + 1e-9:
            continue
        if L.near_event(a, skip):
            continue
        m = L.series_at(model[series], a - a0)
        if m is None:
            continue
        n += 1
        ok = ok and abs(v - m) <= tol
        if worst is None or abs(v - m) > abs(worst[1] - worst[2]):
            worst = (a, v, m)
    return vrec(run, field, worst[2], worst[1], tol, src, n=n, at=worst[0], within=ok, cause=cause, draws=draws)


def v_reads(run, quantity, pairs, series, a0, model, tol, src, rel_burn=None, draws=(), cause=None, level=None):
    """Scalar reads [(age, live)] against the model at each read's age; rel_burn adds that share of the idle burn over
    the hours since a0 (the run's CAL_TOL_REL); level maps the model's value to a moodle level first."""
    L = _lib()
    worst, n, ok, wt = None, 0, True, tol
    for a, v in pairs:
        m = L.series_at(model[series], a - a0)
        if m is None or not isinstance(v, (int, float)):
            continue
        if level is not None:
            m = level(m)
        t = tol + (rel_burn * VM.burn_rate() * 3600.0 * max(0.0, a - a0) if rel_burn else 0.0)
        n += 1
        ok = ok and abs(v - m) <= t
        if worst is None or abs(v - m) > abs(worst[1] - worst[2]):
            worst, wt = (a, v, m), t
    return vrec(run, quantity, worst[2], worst[1], wt, src, n=n, at=worst[0], within=ok, cause=cause, draws=draws)


def _skip(a0, sc):
    return [a0 + e["t_h"] for e in sc["events"]]


def _levels(run, file, path):
    return list(zip(read(run, file, path + "[*].age"), read(run, file, path + "[*].level")))


def v_x441():
    L = _lib()
    run, f = "x441", "meal.json"
    a0, sc, m = vchain(run)
    skip = _skip(a0, sc)
    out = []
    for arm in ("A", "B"):
        w = read(run, f, "verdicts.V1a_%s_hunger.observed.window" % arm)
        out.append(dict(v_curve(run, "HUNGER", "hunger", w, a0, m, skip, L.HUNGER_TOL, SRC_LIB % "HUNGER_TOL",
                                draws=["H1-v-live"] if arm == "A" else []), key="x441:HUNGER arm " + arm,
                        quantity="HUNGER arm " + arm))
    w = read(run, f, "verdicts.V1a_thirst.observed.window")
    out.append(v_curve(run, "THIRST", "thirst", w, a0, m, skip, L.THIRST_TOL, SRC_LIB % "THIRST_TOL",
                       draws=["S1c-v-live"]))
    ages, timers, arms = (read(run, f, "reads.timer[*].%s" % k) for k in ("age", "foodTimer", "arm"))
    b = [(a, t) for a, t, arm in zip(ages, timers, arms) if arm == "B"]
    out.append(v_reads(run, "food timer", b, "food_timer", a0, m, L.TIMER_TOL, SRC_LIB % "TIMER_TOL",
                       cause=CAUSE_PLACEMENT + " " + CAUSE_FLOOR))
    out.append(v_reads(run, "FOOD_EATEN level", _levels(run, f, "reads.food_eaten"), "food_timer", a0, m, 0.0,
                       "named here: exact, a level", level=VM.food_eaten_level))
    eat_b = a0 + next(e["t_h"] for e in sc["events"] if e.get("label") == "B_eat")
    tz = L.first_at_or_below(m["food_timer"], 0.0, after=eat_b - a0 + 1e-6) + a0
    live = next(r["age"] for r in vring(run) if r["age"] > eat_b and r.get("HUNGER", 0) > L.FREEZE_EPS)
    out.append(vrec(run, "freeze end (game h)", tz, live, L.FREEZE_TOL_H, SRC_LIB % "FREEZE_TOL_H", at=live,
                    cause=CAUSE_FREEZE))
    cal = list(zip(read(run, f, "reads.nutrition[*].age"), read(run, f, "reads.nutrition[*].calories")))
    out.append(v_reads(run, "calorie store", cal, "calories_store", a0, m, L.CAL_TOL, SRC_LIB % "CAL_TOL + CAL_TOL_REL",
                       rel_burn=L.CAL_TOL_REL))
    return out


def vstart_of(run):
    """The x442 placement: (the write's landing age, HUNGER at the first ring row after it, the model-equivalent hours
    from HUNGER 0 to it at the idle rate)."""
    w = read(run, "starve.json", "writes[0].ages[1]")
    h = next(r["HUNGER"] for r in vring(run) if r["age"] >= w)
    return w, h, VM.hours_to_hunger(h)


def v_x442():
    L = _lib()
    run, f = "x442", "starve.json"
    a0, sc, m = vchain(run)
    skip = _skip(a0, sc)
    w = read(run, f, "verdicts.V1b_hunger.observed.window")
    out = [v_curve(run, "HUNGER", "hunger", w, a0, m, skip, L.HUNGER_TOL, SRC_LIB % "HUNGER_TOL",
                   draws=["S1b-v-live", "S2a-v-live"])]
    wr = read(run, f, "writes[0].ages[1]")
    t = L.first_cross(m["hunger"], 0.70, after=wr - a0) + a0
    live = next(r["age"] for r in vring(run) if r["age"] >= wr and r["HUNGER"] > 0.70)
    out.append(vrec(run, "HUNGRY 4 crossing (game h)", t, live, L.LEVEL_TOL_H, SRC_LIB % "LEVEL_TOL_H", at=live,
                    draws=["S1b-v-live"]))
    out.append(v_reads(run, "HUNGRY level", _levels(run, f, "reads.hungry"), "hunger", a0, m, 0.0,
                       "named here: exact, a level", level=lambda h: VM.moodle_level(h, VM.HUNGRY_THRESHOLDS)))
    hp = [(a, h) for a, h in zip(read(run, f, "reads.health[*].age"), read(run, f, "reads.health[*].overall"))
          if isinstance(h, (int, float))]
    out.append(v_reads(run, "health", hp, "health", a0, m, L.HEALTH_TOL, SRC_LIB % "HEALTH_TOL",
                       draws=["S2d-v-live-health"]))
    td = L.first_at_or_below(m["health"], 0.0) + a0
    dead = next(a for a, h in hp if h <= 0.0)
    out.append(vrec(run, "health 0 (game h)", td, dead, L.DEATH_TOL_H, SRC_LIB % "DEATH_TOL_H", at=dead,
                    draws=["S2d-v-live-health"],
                    cause="a quarter-hourly read: the live zero lies between the previous read (38.6275) and this one"))
    na, nc, nw = (read(run, f, "reads.nutrition[*].%s" % k) for k in ("age", "calories", "weight"))
    out.append(v_reads(run, "calorie store", list(zip(na, nc)), "calories_store", a0, m, L.CAL_TOL,
                       SRC_LIB % "CAL_TOL + CAL_TOL_REL", rel_burn=L.CAL_TOL_REL, cause=CAUSE_BURN))
    out.append(v_reads(run, "weight", list(zip(na, nw)), "weight_kg", a0, m, L.WEIGHT_TOL, SRC_LIB % "WEIGHT_TOL"))
    return out


def v_x443(run, f, tag):
    L = _lib()
    a0, sc, m = vchain(run)
    w = read(run, f, "verdicts.%s_hunger.observed.window" % tag)
    out = [v_curve(run, "HUNGER", "hunger", w, a0, m, _skip(a0, sc), L.HUNGER_TOL, SRC_LIB % "HUNGER_TOL",
                   draws=["S1a-v-live"])]
    na, nc, nw = (read(run, f, "reads.nutrition[*].%s" % k) for k in ("age", "calories", "weight"))
    out.append(v_reads(run, "weight", list(zip(na, nw)), "weight_kg", a0, m, L.WEIGHT_TOL, SRC_LIB % "WEIGHT_TOL",
                       draws=["H2-v-live"]))
    out.append(v_reads(run, "calorie store", list(zip(na, nc)), "calories_store", a0, m, L.CAL_TOL,
                       SRC_LIB % "CAL_TOL + CAL_TOL_REL", rel_burn=L.CAL_TOL_REL))
    return out


def v_x444():
    L = _lib()
    run, f = "x444", "strength.json"
    a0, sc, m = vchain(run)
    out = []
    for arm in ("A", "B", "C"):
        mk = L.mark_of(m, arm)
        factor = VM.protein_factor(mk["writes"]["proteins"])
        out.append(vrec(run, "push-up set XP, arm %s (factor %g)" % (arm, factor), L.model_set_delta(m, arm),
                        read(run, f, "verdicts.V3_%s.observed.delta" % arm), L.REP_TOL * VM.XP_PER_REP * factor,
                        SRC_LIB % "REP_TOL x 6 x the factor"))
    out.append(vrec(run, "Strength XP after the 29700 grant", L.mark_of(m, "B_grant")["writes"]["strength_xp"],
                    read(run, f, "verdicts.V3_B_grant.observed.xpAfter"), L.XP_TOL, SRC_LIB % "XP_TOL"))
    out.append(vrec(run, "Strength level after set B", L.mark_of(m, "B")["post"]["strength_level"],
                    read(run, f, "verdicts.V3_B_level.observed.level"), 0.0, "named here: exact, a level"))
    return out


def v_x445():
    L = _lib()
    run, f = "x445", "drinks.json"
    a0, sc, m = vchain(run)
    t0, t1 = (read(run, f, "checks.A.coffee.%s.worldAge" % k) for k in ("before", "after"))
    pred = L.series_at(m["fatigue"], t1 - a0) - L.series_at(m["fatigue"], t0 - a0)
    return [vrec(run, "FATIGUE change of a 0.25 L coffee", pred, read(run, f, "verdicts.V4_A_coffee.observed.delta"),
                 L.FATIGUE_TOL, SRC_LIB % "FATIGUE_TOL")]


BEER_DT_MIN = 1.0 / 60.0


def beer_spans(run="x445b", f="beers.json"):
    """Each can's live span off its polls: (the last read before its first sip, the first poll that rose above it,
    the peak poll's age and value). The first sip lies between the first two; the drink ends by the peak."""
    out = []
    for i in range(4):
        b = read(run, f, "drinks[%d].before" % i)
        polls = list(zip(read(run, f, "drinks[%d].polls[*].age" % i), read(run, f, "drinks[%d].polls[*].value" % i)))
        rose = next(a for a, v in polls if v > b["value"] + 1e-9)
        pa, pv = max(polls, key=lambda p: p[1])
        out.append((b["worldAge"], rose, pa, pv))
    return out


def spread_events(sc, a0, spans, early, run="x445b", f="beers.json"):
    """The run's events with each can spread over its live span, from its earliest (early) or latest first sip."""
    ev = [e for e in sc["events"] if e["kind"] != "drink"]
    for i, (b, rose, pa, _) in enumerate(spans):
        t0 = b if early else rose
        ev.append({"t_h": t0 - a0, "kind": "drink", "fluid": "beer", "litres": read(run, f, "drinks[%d].drunk" % i),
                   "duration_min": (pa - t0) * 60.0, "label": "B_beer%d" % (i + 1)})
    return ev


def v_x445b():
    L = _lib()
    run, f = "x445b", "beers.json"
    a0, sc = vinputs(run)
    spans = beer_spans()
    fine = dict(sc, dt_min=BEER_DT_MIN)                     # the peak sits between minute points: read it at 1 s
    m_lo = L.model_chain(dict(fine, events=spread_events(sc, a0, spans, True)))     # first sip at its earliest
    m_hi = L.model_chain(dict(fine, events=spread_events(sc, a0, spans, False)))    # first sip at its latest
    m_inst = L.model_chain(sc)
    polls = list(zip(read(run, f, "checks.B.polls[*].age"), read(run, f, "checks.B.polls[*].intox")))
    last = read(run, f, "drinks[3].event_age")
    fit_from = read(run, f, "checks.B.cans[3].settle_age")          # the run's own V4_B_decay fit start
    pts = [(a, v) for a, v in polls if a > fit_from + L.EVENT_SKIP_H and v > L.INTOX_FIT_MIN]
    live = L.fit_slope(pts)
    pred = -VM.intoxication_decay_per_hour(90.0)
    out = [vrec(run, "INTOXICATION decay a game hour", pred, live, L.INTOX_DECAY_REL * abs(pred),
                SRC_LIB % "INTOX_DECAY_REL (5 % of the model's)", n=len(pts), draws=["S6b-v-live"])]
    zl = next(a for a, v in polls if a > last and v <= 0.0)
    z_lo, z_hi = (L.first_at_or_below(mm["intoxication"], 0.0, after=spans[3][2] - a0) + a0 for mm in (m_lo, m_hi))
    z_inst = L.first_at_or_below(m_inst["intoxication"], 0.0, after=last - a0 + 1e-6) + a0
    rec = vrec(run, "INTOXICATION zero (game h)", z_hi, zl, L.INTOX_ZERO_TOL_H, SRC_LIB % "INTOX_ZERO_TOL_H", at=zl,
               draws=["S6b-v-live"], cause=CAUSE_SPREAD)
    rec.update(model_bracket=[z_lo, z_hi], model_instant=z_inst, miss_instant=zl - z_inst)
    out.append(rec)
    for i, (b, rose, pa, pv) in enumerate(spans):
        lo, hi = (L.series_at(mm["intoxication"], pa - a0) for mm in (m_lo, m_hi))
        within = lo - 1e-9 <= pv <= hi + 1e-9
        miss = 0.0 if within else (pv - hi if pv > hi else pv - lo)
        r = vrec(run, "INTOXICATION peak, can %d" % (i + 1), hi, pv, 0.0,
                 "named here: inside the model's bracket, the first sip anywhere between the run's last read before "
                 "it and the first poll that rose", at=pa, within=within, miss=miss, how="bracket",
                 cause=CAUSE_SPREAD, draws=["S6b-v-live"])
        ea = read(run, f, "drinks[%d].event_age" % i)
        inst = max(v for t, v in m_inst["intoxication"] if ea - a0 - 0.02 <= t <= pa - a0 + 0.02)
        r.update(model_bracket=[lo, hi], model_instant=inst)
        out.append(r)
    return out


@job
def j_vanilla_validation():
    return (v_x441() + v_x442() + v_x443("x443a", "tuna-a.json", "V2a") + v_x443("x443b", "tuna-b.json", "V2b")
            + v_x444() + v_x445() + v_x445b())


def vanilla_records():
    return result("j_vanilla_validation")


def vval(key):
    return next(r for r in vanilla_records() if r["key"] == key)


def vcheck(sid):
    """A vanilla-live series is drawn only when every validation record that draws it is within its tolerance (the
    vanilla twin of rule R-2)."""
    recs = [r for r in vanilla_records() if sid in r["draws"]]
    bad = [r["key"] for r in recs if not r["within"]]
    if bad:
        raise D.ProvenanceError("%s: the vanilla model misses %s outside the tolerance" % (sid, ", ".join(bad)))
    return [r["key"] for r in recs]


def s_validation():
    """No series: fills VALIDATION with the admission and viability records (the build reads the list after every
    definition, so this one runs last)."""
    fill_validation()
    return []


SERIES_DEFS = [s_h1, s_h2, s_h3, s_h4, s_s1a, s_s1b, s_s1c, s_s2a, s_s2b, s_s2c, s_s2d, s_s3a, s_s3b, s_s3c, s_s4a,
               s_s4b, s_s4c, s_s5a, s_s5b, s_s5c, s_s6a, s_s6b, s_s6c, s_sn1, s_se1, s_sh1, s_sh2, s_st1, s_st2,
               s_sm1, s_sb1, s_sb2, s_sx1, s_sx2, s_ss1, s_sd1, s_sd2, s_sc1, s_sv1, s_sh3, s_validation]
