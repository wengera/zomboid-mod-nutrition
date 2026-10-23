"""x50_lib -- the session engine of Plan 19 Task 7, the live check of the food hedonics (spec
docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md section B.5; the seats are
mod/NutritionRevamp/common/media/lua/server/NR_Server_Hedonics.lua, the kernel NR_Kernel_Hedonics.lua). Four sessions,
each one boot of profile x50-hedonics under 10 wall minutes in a foreground call, build 42.21.0:
  x501 prep    R2, preparation quality: real ingredient adds on the dedicated server at Cooking 3, 0 and 10; a rename
               of a stamped dish then an add (task-6-review I1); a relog then an add.
  x502 floor   R1, the plain-energy floor: four plain eats of butter raise hedonics.f and the UNHAPPINESS target; a relog
               with the clock running moves nothing; a non-plain eat releases the floor. Graded against the HEAD replay.
  x503 allies  R3, alliesthesia: butter eaten sated and Hungry, a cancelled Hungry eat of lard, a stale potato eaten
               Hungry (task-6-review I2: the client's copy not doubled).
  x504 class   R4, the taste class of a dish by type-summed kcal; Rule 6: the frame timer under a 60-record load.

Built on testing/experiments/xlib.py and on the frozen libs of the sessions it follows, imported unchanged (CLAUDE.md
s5: a lib is frozen with its first run): x45g_lib.py's Sess plumbing (the bus step, the poll, the clock and its restore,
the ring and its pages, W's start.json, the replay-field grade, the staged gate), x48_lib.py's first sight and fixture
read, x49_lib.py's argument refusal and client relaunch, x49b_lib.py's bounded teardown. x49b_lib.py (x494's) is the
shape this file starts from (its preboot, gates and main); its constants are x494's and are never read here: this file
names its own staged copy, commit, sessions, profile, ring, schedule and tolerances.

THE STAGED COPY. The profile boots release/NutritionRevamp/Contents/mods/NutritionRevamp, staged from mod/'s last commit
(`python tools/release_pack.py stage mod/NutritionRevamp --out release`); staged_gate checks it against
release_pack.manifest() of mod/ at STAGED_FROM and refuses on a mismatch, and preboot refuses when STAGED_FROM is not
mod/'s last commit. mod/ is never booted (CLAUDE.md s5, x201).

THE PROFILE (testing/profiles/x50-hedonics.toml): fixture default, admin -debug, PZTestKit and the staged copy, Nutrition
false (ruling T18-1), DayLength 4 (a game minute 3.75 wall s at speed 1; 37.5 server ticks a game minute, x391d's
spacing), sleep off, [sandbox.NR] Mode 1 (the mod writes HUNGER, which R3 reads), DeathPace 3 and HealthCombine 2 (the
declared defaults, written so the profile says what the run is). Every session runs at speed 1 throughout.

THE DIALS AND THE JAR, pinned before the run (a test reads each dial off NR_Data_Dials.lua; the jar lines were read on
42.21 for this file):
  PREP_KNOTS ((0, 0.8), (3, 1), (10, 1.5)): the relief scale at a Cooking level (K.hedonics.prepScale);
  FLOOR_KNOTS ((0.5, 0), (0.75, 15), (0.95, 30)) and SHARE_MIN_KCAL 1500: the floor of a plain share;
  ALLIES_F 0.6 above HUNGER 0.25 (ALLIES_LEVEL 2, Hungry); CLASS_W 0.1;
  vanilla's eat: UNHAPPINESS += getUnhappyChange() x f, times 0.75 with a utensil when positive (#0048);
  vanilla's add (EvolvedRecipe.addItem @1182-@1196 L406, read for this file): a non-spice ingredient sets the dish's
  UnhappyChange to its unmodified value less (5 - 5 x d), d its earlier copies of the same type plus, when the extra
  items before it less 2 exceed the Cooking level c, (that excess less 3c) (@1102-@1140 L398-L399; the item is appended
  after, @1766); a spice sets it to the unmodified value less 2 x its :N (#4121). The Stir fry below reads -5, -10,
  -15 for three types, -17 after Salt (:1), -25 after Butter (:4), -30 after Potato (a fourth type: at Cooking 0 its
  over-stuffing excess 1 > 0 makes it 0, so -25 there; never driven at 0), -32 after Pepper (:1).

THE FIRST SIGHT (CLAUDE.md s5). The default fixture's admin has no store record (preboot checks it), so each session
starts on a fresh record, which lands its seed plate and lays the mod's own creation body. x502's prediction
(x50_prerun.py) is the HEAD replay of its schedule from x48_lib.FIRST_SIGHT with no typed weight; preboot refuses a boot
whose committed prediction is not the HEAD replay's.

THE SESSIONS (the arms in order; every add and eat at speed 1):
  x501  S   the reads; the wrap installed (hedonics.wrappedCook), the hedonics counters, admin's Cooking level and XP.
        I   RCON additem of the ingredients (PAN x3, Carrots x3, Cabbage x3, Onion x3, Potato x2, Salt, Butter, Pepper),
            each confirmed by its server id.
        D3, D0, D10  for each Cooking level (3 first: the anchor, whose scale is 1, so its stored value is vanilla's):
            perk.set Cooking; five adds on a Pan through recipe.add (vanilla's ISAddItemInRecipe from the client, which
            the server completes): Carrots, Cabbage, Onion, Salt, Butter. Each add is polled on the server's hedonics
            cooks counter (and the first on the new dish's id in the client's inventory), then read on the server
            (its dish fields and its NR_PrepS stamp); each dish's last add is read as a pair: the server's, the
            client's, the server's again (inside PAIR_SLACK_S, the two server reads equal: ruling T7-1). After D3's
            first add the server's item.get of the dish records ids_agree (the server's id against the client's).
        RN  item.rename of the D3 and D10 dishes (vanilla's rename: setName, setCustomName, syncItemFields from the
            client); the server's stamp read after; then Potato added to D3 at Cooking 3 and to D10 at Cooking 10.
        RL  the relog: admin quits, the players list polled until admin leaves, admin relaunched; every dish found
            again in the client's inventory (D3 and D10 by their names, D0 as the one not renamed: an id the relog
            moved is followed and recorded) and read on both sides; then Pepper added to D3 at Cooking 3 and to D10
            at Cooking 10.
        C   Cooking back to the level read at S (never the reply's echo); the counters; the clock restored.
  x502  S, H (the minute ring), W (the store's next save as start.json, the replay's start); E1..E4 four eats of butter
        at a tenth of the stick each (BUTTER_F), each landed, then one writer minute, then the ring record read (its
        24 plain and all slots, f, s, i, moodLast.u, lastIntake); OFF the relog with the clock running at speed 1 (the
        record read before the quit and after the rejoin); REL an eat of half a jar of peanut butter (not plain), then
        one writer minute and the read; C, R (the ring's pages).
  x503  S, H; R3S butter (ALLIES_EAT_F) eaten sated with UNHAPPINESS seeded at UNHAPPY_SEED (above the writer's 59, so
        the writer never raises it); I2C the vanilla control: a potato aged stale (item.set age STALE_AGE_D), a quarter
        of it (POTATO_F / 2) eaten sated with no seed (no alliesthesia, no restore); R3H the same butter eat Hungry
        (record.set satiety.M 0, then HUNGER set to HUNGRY_SEED; the writer never lowers an unfed HUNGER, so it holds);
        I2 another quarter of the stale potato eaten Hungry; R3C lard, Hungry, its eat cancelled through action.cancel
        part way (vanilla's serverStop eats the progress), last because its part is the largest intake (every eat's
        validStart and FOOD_EATEN level are kept: a refused eat lands nothing and its grades read unmeasured); each eat
        read before and after: UNHAPPINESS, HUNGER and moodLast.u on the server, the item's fields on the server,
        lastIntake; I2C and I2 also the item on the client before and after. C, R.
  x504  S, H; I spawns; A (Cooking set to DISH_EAT_LEVEL 10 first; restored at C from S's read) Pan + Carrots x3 + BaconRashers (each add
        read on the server alone), UNHAPPINESS seeded at UNHAPPY_SEED, eaten whole; B Pan + Carrots + BaconRashers, the
        same; each eat's lastIntake, UNHAPPINESS, moodLast.u, the dish's fields and the monotony class keys read;
        IDLE the frame timer (perf.local and tick.ring) over ARM_WALL_S with no load; LOAD ghost.load 60 mod feed and
        ghost.modq on (59 ghost records beside admin on the mod's own queue), settle, ghost.stats reset, the same
        window, ghost.stats, ghost.modq off, ghost.stop; C, R.

THE GRADES (pure; each has a failing case in testing/tests/test_x50_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  every session
    Z         no mod error line in the server log (the hedonics seats log `failed:` on a caught fault), admin never
              parked, and no hedonics failure counter rose (cookFailures, alliesFailures, bookFailures).
  x501
    WRAP      (precondition) hedonics.wrappedCook true on the server at S; every perk.set read back at its level.
    ANCHOR    the D3 dish after each add reads the jar model's vanilla value (VANILLA_D) within TOL_FIELD and stamp
              1 (prepScale(3)); a falsification here names the model, not the seat (SCALE reads the anchor live).
    SCALE     D0 and D10 after each of their five adds: the server's stored UnhappyChange = the anchor's value after
              the same add x prepScale(level) within TOL_FIELD, and NR_PrepS = prepScale(level) within TOL_STAMP.
              Falsifier: an unscaled dish (the seat not reached), a compounded one (prepScale^k), or no stamp.
    CLIENT    after each dish's last add (the only add of a dish read on the client), a valid pair (server, client,
              server inside PAIR_SLACK_S, both server reads equal: ruling T7-1): the client's stored UnhappyChange
              equals the server's, and its NR_PrepS the server's (the R2 syncs; I1).
    COUNTS    the server's cooks counter rose by the adds that completed, prepped by the reliefs made, unprepped by the
              adds on a stamped dish whose scale is not 1 (UNPREP_PRED), cookFailures by 0.
    RENAME    (I1) after the rename of D10 the server's NR_PrepS still reads prepScale(10) (the client's sync carried
              it back), and the Potato add then reads D3's post-Potato value x prepScale(10). Falsifier: the stamp gone
              (the next add compounds: (V5 x 1.5 - 5) x 1.5) or wrong. D3's rename is a reading. Unmeasured when a
              Potato add did not complete, unless D10's stamp was read off or gone (the stamp half alone).
    RELOG     after the relog, every dish's server stamp and stored value are as before it, on both sides; the Pepper
              add then reads D3's post-Pepper value x prepScale(10) on D10. Falsifier: a stamp lost or a value moved.
              D0's and D10's rows count only with a stamp before the relog; unmeasured when a Pepper add did not
              complete, unless a dish moved (the dish half alone).
  x502
    FLOOR_OF  on every record read after a landed eat, hedonics.f = floorOf(share) of the ring's own slots (the 24
              plain and all sums, share = plain / max(all, SHARE_MIN_KCAL)) within F_TOL; unmeasured unless a read's
              floorOf stands above 0 (a ring at the curve's foot passes on a zero change), those reads the samples.
    RISE      hedonics.f after E1..E4 never falls, ends above 0, and each is the prerun's within PRED_F_TOL; the
              composed target moodLast.u after E4 at or over f.
    LAST      lastIntake after each eat: plain true, class fatty and allies 1 for butter; plain false, class fatty for
              peanut butter (the hedonics table's).
    OFFLINE   across the relog: the ring's 24 plain and all slots and i identical, f identical, moodLast.u within
              U_GAP_TOL; and the ring's hour stamp s moved forward by the absence (the resume, K.resume: the online
              clock froze): s1 - s0 within [(launch - depart) - SLACK_H, (back - quit) + SLACK_H], quit the age read
              just before the quit, depart the age read once admin is off the players list, launch the age read just
              before the relaunch (no touch can come before it; no step after the departure), back the age read once
              admin is on it again (the resume's gap, the touch less the last step, lies between). Unmeasured when
              launch - depart - SLACK_H is under GAP_MIN_H (an absence too short to tell a moved stamp from a frozen
              one), or when the ring's position plus the online bits ((a0 - s0) mod 1 + (depart - a0) + (a1 - back) +
              SLACK_H) reaches an hour (an online rotation could fall in the gap), or when the ring before held no
              floor (f 0) or no kcal (an unmoved empty ring passes on a zero change).
    RELEASE   after REL, f reads 0 (the share under the curve's foot), and moodLast.u fell by f's fall within
              U_FALL_TOL (the floor leaves the composed target at once).
    REPLAY_<f>  hedonics.f and moodLast.u on every ring row within REPLAY_TOL of the HEAD replay of the run's own
              inputs (the eats at the ring rows whose eats counter rose, each at its live item's calories, macros and
              hunger and its live fraction; the relog's rows offline).
  x503
    PRE       (precondition) the server's HUNGER at each eat's before-read: at or under ALLIES_AT for R3S and I2C (the
              sated arms, SATED_ARMS), over it for R3H, I2 and R3C. SATED, HUNGRY, RATIO, CANCEL and I2 each read
              unmeasured when their own arm's before-read HUNGER is on the wrong side (a seed that did not hold is the
              driver's, never the mod's).
    SATED     lastIntake.allies 1, and the UNHAPPINESS delta (corrected by the writer's fall of moodLast.u, if any) =
              u x f x k within D_TOL, u the read-time getUnhappyChange before, f the eaten fraction (1 - hung1 / hung0),
              k vanilla's utensil factor, 1 or 0.75 (the nearer; reported).
    HUNGRY    lastIntake.allies ALLIES_F, and the delta = u x f x ALLIES_F x k within D_TOL, k SATED's.
    RATIO     the two deltas over their u x f: HUNGRY's / SATED's = ALLIES_F within RATIO_TOL (the utensil cancels).
    REMAINDER every eat whose item remains: the server's stored field after = the field before x hung1 / hung0 within
              REL_TOL (vanilla's linear scale on the original field). Falsifier: the restore missing (the remainder
              keeps the lowered field) or wrong.
    CANCEL    R3C's cancel landed a part (0 < f < 1); lastIntake.allies ALLIES_F; its delta = u x f x ALLIES_F x k
              within D_TOL; unmeasured when the cancel landed nothing (the progress 0) or the whole.
    I2        the stale potato (the server's read-time value less its field = STALE_TERM) eaten Hungry: the client's
              stored field after is not the server's read-time value (the doubled state term an item-stats packet
              would write) and is the server's field after or the client's own field before, within TOL_FIELD;
              unmeasured when the stale term is not read on the server, and when the vanilla control I2C (the same
              stale potato eaten sated: no alliesthesia, no restore) is unread or its client field after equals its
              server read-time value after (vanilla's own eat path doubles the state term: not the mod's).
    COUNTS    the server's allies counter rose by the Hungry eats (3), restores by those whose item remained (3);
              the sated control I2C adds neither.
  x504
    CLASS_A   dish A (three Carrots, one BaconRashers): lastIntake.class savoury; the record's monotony @savoury count
              rose and @fatty did not. Falsifier: fatty (the class of the heaviest portion) or none.
    CLASS_B   dish B (one Carrots, one BaconRashers): lastIntake.class fatty; @fatty rose. CLASS_A and CLASS_B read
              unmeasured when the rising class count is unread after the eat.
    DISH_EAT  each dish eaten whole after UNHAPPINESS is seeded at UNHAPPY_SEED: the delta (eat_delta) = u x f x k
              within D_TOL, u the read-time getUnhappyChange before the eat (the dish's stored, scaled relief:
              negative), k one of 1 and UTENSIL_GLAD for both dishes (a negative value with a utensil, #0048). B.5's
              butter cooked into a dish, on the eat side: x501 grades the stored value at three Cooking levels; the
              dishes are made at DISH_EAT_LEVEL 10 (scale 1.5), where the unscaled deltas fit no k, and a dish whose
              Cooking did not hold reads unmeasured. Falsifier: no k fits (the eat reading an unscaled or moved value).
    IDLE, F, SMOKE, P99, MAX, STARVE, S  x391d's pre-registered Rule 6 grades (Plan 10c ruling 2) for the one LOAD arm
              against the session's IDLE arm: idle busy p99 <= IDLE_BUSY_P99_MAX and period p50 in IDLE_PERIOD_BAND;
              each arm >= MIN_FRAMES kept frames and >= MIN_MINUTE_FRAMES minute frames; the load and the queue on with
              N - 1 ghosts and runs > 0; the end-to-end period's p99 adds <= RULE_P99 ms over idle; the perf windows'
              max adds <= RULE_MAX ms; starvedEvents 0; failures 0, storeGhostKeys 0, neverRun 0. The ghost runs are
              dry (the writer step skipped, W.dry), so the writer's R1 term runs only in admin's real minute; the
              reading
              against x391d's mod draws at the same spacing (#3744: +7 to +10 ms at the p99, longest windows 120-123 ms)
              is a reading of the build as a whole, never a grade of Task 6 alone (its writer term was benched at 0.8 us
              a player-minute).

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x49_lib as L49                                                         # noqa: E402
import x49b_lib as B                                                          # noqa: E402

REPO = X.REPO
SRV = X.SRV
CLI = "client"
USER = "admin"
NR = G.NR
LIB_FILE = "x50_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "3760ae05"                 # mod/'s last commit (Plan 19 Task 6 fix 1: the hedonics adapter syncs)
STAGED_VERSION = "1.0.0"
PRERUN_FILE = "testing/experiments/x50_prerun.json"
MIN_FREE_GB = 12.0
PROFILE = "x50-hedonics"
SESSIONS = {
    "x501": {"driver": "x501_prep.py", "artifact": "prep.json", "profile": PROFILE, "budget_s": 470.0},
    "x502": {"driver": "x502_floor.py", "artifact": "floor.json", "profile": PROFILE, "budget_s": 470.0},
    "x503": {"driver": "x503_allies.py", "artifact": "allies.json", "profile": PROFILE, "budget_s": 400.0},
    "x504": {"driver": "x504_class.py", "artifact": "class.json", "profile": PROFILE, "budget_s": 470.0},
}
PROFILES = {PROFILE: {"fixture": "default", "clients": [USER], "day_length": 4, "mode": 1, "pace": 3, "combine": 2}}
SERVER_TIMEOUT_S = 240                   # the profile's [server] timeout (x484's): bounds the slow-boot fallback
DAY_MIN = 90.0                           # DayLength 4

# ---- the dials (NR_Data_Dials.lua at STAGED_FROM; test_x50_lib reads each off the registry)
PREP_KNOTS = ((0.0, 0.8), (3.0, 1.0), (10.0, 1.5))
FLOOR_KNOTS = ((0.5, 0.0), (0.75, 15.0), (0.95, 30.0))
SHARE_MIN_KCAL = 1500.0
ALLIES_F = 0.6
ALLIES_AT = 0.25                         # K.hungerCurve.THRESHOLDS[ALLIES_LEVEL 2]: Hungry, a strict greater-than
CLASS_W = 0.1
RING_N = 24
UTENSIL_SAD = 0.75                       # vanilla's utensil factor on a positive unhappyChange x f (#0048)
UTENSIL_GLAD = 1.25                      # and on a negative one (#0048; jar BodyDamage.JustAteFood @398-@406 L638-L640)
UNHAPPY_HI = 59.0                        # the writer's UNHAPPINESS target ceiling (W.unhappyHi)

# ---- the jar model of a Stir fry's UnhappyChange (EvolvedRecipe.addItem L398-L409, useSpice #4121)
RECIPE = "Stir_fry"                      # recipe.add reads underscores as spaces: the evolved recipe Stir fry
PAN = "Base.Pan"
DISH = "Base.PanFriedVegetables"
SPICE_N = {"Base.Salt": 1, "Base.Butter": 4, "Base.Pepper": 1}     # the Stir fry's :N of each spice (food.txt)
DISH_ADDS = ("Base.Carrots", "Base.Cabbage", "Base.Onion", "Base.Salt", "Base.Butter")
LATE_ADD = "Base.Potato"                 # RN: the fourth non-spice type
RELOG_ADD = "Base.Pepper"                # RL: a third spice
LEVELS = (3, 0, 10)                      # the anchor first
ANCHOR = 3
SPAWNS_501 = ((PAN, 3), ("Base.Carrots", 3), ("Base.Cabbage", 3), ("Base.Onion", 3), (LATE_ADD, 2), ("Base.Salt", 1),
              ("Base.Butter", 1), (RELOG_ADD, 1))
RENAMED = {3: "NRx50d3", 10: "NRx50d10"}


def interp(knots, x):
    """K.interp: linear between the knots, held at the ends."""
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


def prep_scale(level):
    return interp(PREP_KNOTS, level)


def floor_of(share):
    return interp(FLOOR_KNOTS, share)


def share_of(p, a):
    """K.hedonics.share over slot lists p and a."""
    return sum(p) / max(sum(a), SHARE_MIN_KCAL)


def vanilla_dish(adds, level):
    """The jar model's stored UnhappyChange after each add of `adds` (full types, the first on a Pan) at Cooking
    `level`: a list, one value an add."""
    u, extra, out = 0.0, [], []
    for t in adds:
        if t in SPICE_N:
            u = u - 2.0 * SPICE_N[t]
        else:
            d = sum(1 for e in extra if e == t)
            if len(extra) - 2 > level:
                d = d + (len(extra) - 2) - 3 * level
            u = min(25.0, u - (5 - 5 * d))
            extra.append(t)
        out.append(u)
    return out


VANILLA_D = vanilla_dish(DISH_ADDS + (LATE_ADD, RELOG_ADD), ANCHOR)     # -5 -10 -15 -17 -25 -30 -32

# ---- x502: the plain eats (game minutes at DayLength 4)
BUTTER = "Base.Butter"
PEANUT = "Base.PeanutButter"
BUTTER_F = 0.1                           # each plain eat a tenth of the stick (eat.action's fraction of the whole)
PLAIN_EATS = 4
PEANUT_F = 0.5
FOOD_TYPE = {BUTTER: None, PEANUT: "NoExplicit", "Base.Lard": "NoExplicit", "Base.Potato": "Vegetables"}
CLASS_OF = {BUTTER: "fatty", PEANUT: "fatty", "Base.Lard": "fatty", "Base.Potato": "staple"}
PLAIN_OF = {BUTTER: True, PEANUT: False, "Base.Lard": True, "Base.Potato": False}
SLOTS = tuple(f"hedonics.p.{k}" for k in range(1, RING_N + 1)) + tuple(f"hedonics.a.{k}" for k in range(1, RING_N + 1))
HED_READ = ("hedonics.f", "hedonics.s", "hedonics.i", "moodLast.u", "lastIntake.fullType", "lastIntake.plain",
            "lastIntake.class", "lastIntake.allies", "lastIntake.frac", "lastSeen") + SLOTS
EATS_G = "_G.NutritionRevamp.server.intake.stats.eats"
LANDED_G = "_G.NutritionRevamp.server.intake.stats.landed"
WRITES_G = "_G.NutritionRevamp.server.writer.stats.writes"
RING_502 = ("hedonics.f", "hedonics.s", "hedonics.i", "hedonics.p.1", "hedonics.p.2", "hedonics.p.3",
            "hedonics.a.1", "hedonics.a.2", "hedonics.a.3", "moodLast.u", "moodLast.b", "satiety.M",
            "lastIntake.fullType", "lastIntake.plain", "lastIntake.class", "lastIntake.allies", "lastIntake.frac",
            "monotony.t.[Base.Butter].n", "monotony.t.[Base.PeanutButter].n", "monotony.t.[@fatty].n", EATS_G, LANDED_G)
REPLAY_TOL = {"hedonics.f": ("abs", 1e-4), "moodLast.u": ("abs", 1e-3)}
H1_NIL_OK = ("hedonics.f", "hedonics.s", "hedonics.i", "hedonics.p.1", "hedonics.p.2", "hedonics.p.3",
             "hedonics.a.1", "hedonics.a.2", "hedonics.a.3", "lastIntake.fullType", "lastIntake.plain",
             "lastIntake.class", "lastIntake.allies", "lastIntake.frac", "monotony.t.[Base.Butter].n",
             "monotony.t.[Base.PeanutButter].n", "monotony.t.[@fatty].n", "moodLast.u", "moodLast.b")

# ---- x503: alliesthesia
ALLIES_EAT_F = 0.3                       # each butter eat three tenths of the stick: 6 sated (4.5 with a utensil)
LARD = "Base.Lard"
POTATO = "Base.Potato"
POTATO_F = 0.5                           # the potato's two eats, I2C then I2, a quarter of the whole each
SATED_ARMS = ("R3S", "I2C")              # the arms eaten sated (HUNGER at or under ALLIES_AT)
STALE_AGE_D = 30.0                       # Potato DaysFresh 28, DaysTotallyRotten 280: stale (food.txt)
STALE_TERM = 10.0                        # stale adds 10 to the read-time UnhappyChange (#0042)
HUNGRY_SEED = 0.32                       # between Hungry (0.25) and Very Hungry (0.45)
UNHAPPY_SEED = 60.0                      # over the writer's 59: the writer never raises the stat
CANCEL_FRAC = 0.4                        # the cancel at this share of the action's maxTime (ticks at 60 a second)
SPAWNS_503 = ((BUTTER, 1), (LARD, 1), (POTATO, 1))
RING_503 = ("moodLast.u", "moodLast.b", "satiety.M", "hedonics.f", "lastIntake.fullType", "lastIntake.allies",
            "lastIntake.frac", EATS_G, LANDED_G)

# ---- x504: the taste class and Rule 6
BACON = "Base.BaconRashers"
DISH_A = ("Base.Carrots", "Base.Carrots", "Base.Carrots", BACON)
DISH_B = ("Base.Carrots", BACON)
SPAWNS_504 = ((PAN, 2), ("Base.Carrots", 4), (BACON, 2))
CLASS_KEYS = ("monotony.t.[@savoury].n", "monotony.t.[@fatty].n", "monotony.t.[@staple].n", "monotony.t.[@sweet].n",
              "monotony.t.[Base.PanFriedVegetables].n", "lastIntake.fullType", "lastIntake.class", "lastIntake.plain")
RING_504 = ("moodLast.u", "satiety.M", "hedonics.f", "lastIntake.class") + CLASS_KEYS[:5] + (EATS_G, LANDED_G)
N_LOAD = 60
REALS = 1
RING_FRAMES = 1500
PERF_N = 400
ARM_WALL_S = 60.0                        # about 600 frames at the ten-tick lock, 16 minute events at 37.5 a minute
SETTLE_S = 5.0
MIN_FRAMES = 500
MIN_MINUTE_FRAMES = 12
IDLE_BUSY_P99_MAX = 10.0
IDLE_PERIOD_BAND = (99.0, 101.0)
RULE_P99 = 20.0                          # Plan 10c ruling 2: adds at most 20 ms at the end-to-end p99
RULE_MAX = 25.0                          # and at most 25 ms at the perf windows' max
X391D_P99_ADDS = (7.0, 10.0, 8.0)        # #3744: x391d's three mod draws at N = 60, 37 ticks a game minute
X391D_LONGEST = (120.0, 123.0, 121.0)

# ---- waits (wall seconds) and tolerances (named before any run)
POLL_S = 0.25
ADD_CAP_S = 15.0                         # an add's completion on the server (maxTime 100 - 2.5 x level ticks)
ID_CAP_S = 8.0                           # the new dish in the client's inventory after the first add
SYNC_WAIT_S = 1.0                        # the R2 seat's item-stats packet and syncItemFields after the counter rose
RENAME_WAIT_S = 1.5                      # the rename's syncItemFields reaching the server
EAT_CAP_S = 30.0
WRITE_CAP_S = 9.0                        # one writer minute at speed 1 (3.75 wall s) and slack
DEPART_CAP_S = 40.0
REJOIN_CAP_S = 60.0
QUIT_TIMEOUT_S = 30
RELOG_HOLD_S = 5.0   # x501's relog: RELOG reads no clock across the gap, and the depart poll already saw admin leave
DISH_EAT_LEVEL = 10   # x504's dishes made at Cooking 10 (prepScale 1.5): at 0 (0.8 = 1/UTENSIL_GLAD) an unscaled eat without a utensil reads as a scaled one with it, at 3 (scale 1) the two are one value
OFFLINE_HOLD_S = 30.0                    # wall held offline after the departure (the clock runs): 0.133 game h
PAIR_SLACK_S = 10.0                      # a bracket of two equal server reads around the client read: six bus steps at
                                         # the 0.25-2 s server latency of x491-x495; the field moves only at a driven
                                         # add or rename. Ruling T7-1 (Plan 19 Task 7 fix 1): a pair of reads of a field
                                         # that does not move between them (a dish's stored UnhappyChange, a stamp, an
                                         # id) may span up to PAIR_SLACK_S wall seconds, provided the server reads
                                         # bracket the client read with equal values (s0 = s1); CLAUDE.md s5's
                                         # same-wall-second rule still binds every stat that moves (HUNGER, UNHAPPINESS,
                                         # a floor's rise) -- why: that rule exists because stats rise between reads,
                                         # and a static field cannot -- cost if wrong: a mid-pair write would go unseen,
                                         # but the bracket catches it.
TOL_FIELD = 1e-3                         # UnhappyChange is a Java float; every predicted value is exact in binary32
TOL_STAMP = 1e-9
F_TOL = 1e-4
PRED_F_TOL = 0.05                        # the prerun's f against the live one (the live kcal is the live item's)
U_GAP_TOL = 0.5
U_FALL_TOL = 0.5
SLACK_H = 2.0 / 60.0                     # two game minutes: a minute event's step either side of the reads
GAP_MIN_H = 0.05                         # three game minutes: the least absence that tells a moved stamp from a frozen one
D_TOL = 0.3                              # vanilla's own rise over an eat's bracket (#3016: 0.09 a game minute at Stress
                                         # 2) and the stat's float steps
RATIO_TOL = 0.08
REL_TOL = 2e-3
OPT_PACE = "_G.NutritionRevamp.kernel.drain.OPT.pace"
OPT_COMBINE = "_G.NutritionRevamp.kernel.drain.OPT.combine"
OPT_DAYMIN = "_G.NutritionRevamp.kernel.drain.OPT.dayMin"

# ---- the harness and the logs
LUA_DIR = G.LUA_DIR
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "minute.ring", "stats.all", "stats.setany", "record.set", "nutrition.get", "players", "perk.set",
        "item.get", "item.set", "ghost.load", "ghost.modq", "ghost.stats", "ghost.stop", "tick.ring", "perf.local",
        "health.get")),
    "PZTestKit_Client.lua": tuple(f'TK.register("{c}", function(' for c in (
        "inv.ids", "recipe.add", "item.rename", "eat.action", "action.cancel")),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in (
        "time.snapshot", "lua.read", "lua.global", "witness.fields", "witness.moddata")),
}
ECHO_RX = G.ECHO_RX
NEVER_RX = G.NEVER_RX
LOG_RX = re.compile(r"NutritionRevamp|NR_|hedonics|LuaError|STACK TRACE|lua error|attempted index|tried to call nil",
                    re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|failed:|STACK TRACE|attempted index|tried to call nil")
HSTATS = ("cooks", "prepped", "unprepped", "cookFailures", "passthrough", "allies", "restores", "alliesFailures",
          "booked", "plain", "healed", "bookFailures")
HSTATS_G = tuple(f"NutritionRevamp.server.hedonics.stats.{k}" for k in HSTATS) + (
    "NutritionRevamp.server.hedonics.wrappedCook", "NutritionRevamp.server.hedonics.lastError")
FAIL_KEYS = ("cookFailures", "alliesFailures", "bookFailures")
FIELDS = ("getUnhappyChangeUnmodified", "getUnhappyChange", "getBoredomChange", "getName", "isCustomName",
          "getHungChange", "getCalories")

CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple, dict, list)) and k not in ("REPO", "HERE")}
CONSTANTS["LOG_RX"], CONSTANTS["MOD_ERR_RX"] = LOG_RX.pattern, MOD_ERR_RX.pattern

num = X.num
g = G.g
vals = G.vals


def near(a, b, tol):
    a, b = num(a), num(b)
    return a is not None and b is not None and abs(a - b) <= tol


def load_prerun(path=None):
    try:
        with open(path or os.path.join(REPO, PRERUN_FILE), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


# ================================================================ x501: preparation quality (pure)
def stamp_of(read, side):
    return num(g(read, side, "md", "NR_PrepS"))


def field_of(read, side, getter="getUnhappyChangeUnmodified"):
    return num(g(read, side, "fields", getter))


def pair_ok(read):
    """A valid pair: server, client, server inside PAIR_SLACK_S of wall, the two server fields and stamps equal."""
    if not isinstance(read, dict):
        return False
    w0, w1 = num(g(read, "s0", "wall")), num(g(read, "s1", "wall_after"))
    if w0 is None or w1 is None or w1 - w0 > PAIR_SLACK_S:
        return False
    f0, f1 = field_of(read, "s0"), field_of(read, "s1")
    return f0 is not None and f1 is not None and abs(f0 - f1) <= TOL_FIELD and \
        stamp_of(read, "s0") == stamp_of(read, "s1")


def dish_adds(D, level):
    return [a for a in (g(D, f"D{level}", "adds") or []) if isinstance(a, dict)]


def grade_wrap(S, perks):
    """WRAP: hedonics.wrappedCook true at S; every perk.set read back at its level."""
    w = g(S, "hstats", "NutritionRevamp.server.hedonics.wrappedCook")
    bad = [p for p in perks if num(g(p, "reply", "after")) != num(p.get("level"))]
    obs = {"wrappedCook": w, "perks": [(p.get("level"), g(p, "reply", "after")) for p in perks], "off": bad}
    if w is None or not perks:
        return "unmeasured", obs, 0
    return ("as_predicted" if w is True and not bad else "falsified"), obs, len(perks)


def grade_anchor(D, model=VANILLA_D):
    """ANCHOR: the Cooking-3 dish after each add reads the jar model's value and stamp prepScale(3)."""
    rows, bad = [], []
    for k, a in enumerate(dish_adds(D, ANCHOR)):
        v, st = field_of(a.get("read"), "s0"), stamp_of(a.get("read"), "s0")
        if v is None or k >= len(model):
            continue
        row = {"k": k, "add": a.get("add"), "v": v, "want": model[k], "stamp": st}
        rows.append(row)
        if abs(v - model[k]) > TOL_FIELD or st is None or abs(st - prep_scale(ANCHOR)) > TOL_STAMP:
            bad.append(row)
    if not rows:
        return "unmeasured", {"why": "no anchor read"}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad}, len(rows)


def anchor_values(D):
    """The Cooking-3 dish's server value after each of its adds, by add index (None where unread)."""
    return [field_of(a.get("read"), "s0") for a in dish_adds(D, ANCHOR)]


def grade_scale(D, levels=(0, 10)):
    """SCALE: each scaled dish after each of its five adds = the anchor's value after the same add x prepScale, and its
    stamp prepScale."""
    anc = anchor_values(D)
    rows, bad = [], []
    for lv in levels:
        s = prep_scale(lv)
        for k, a in enumerate(dish_adds(D, lv)[:len(DISH_ADDS)]):
            v, st = field_of(a.get("read"), "s0"), stamp_of(a.get("read"), "s0")
            if v is None or k >= len(anc) or anc[k] is None:
                continue
            row = {"level": lv, "k": k, "add": a.get("add"), "v": v, "want": anc[k] * s, "stamp": st, "scale": s}
            rows.append(row)
            if abs(v - anc[k] * s) > TOL_FIELD or st is None or abs(st - s) > TOL_STAMP:
                bad.append(row)
    if not rows:
        return "unmeasured", {"why": "no scaled-dish read beside an anchor read"}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad}, len(rows)


def grade_client(D, levels=LEVELS):
    """CLIENT: every valid pair's client field and stamp equal the server's (only the reads that hold a client read:
    a dish's earlier adds are read on the server alone)."""
    used, bad, invalid = [], [], 0
    for lv in levels:
        for a in dish_adds(D, lv):
            r = a.get("read")
            if not isinstance(r, dict) or "c" not in r:
                continue
            if not pair_ok(r):
                invalid += 1
                continue
            row = {"level": lv, "add": a.get("add"), "s": field_of(r, "s0"), "c": field_of(r, "c"),
                   "s_stamp": stamp_of(r, "s0"), "c_stamp": stamp_of(r, "c")}
            used.append(row)
            if row["c"] is None or abs(row["c"] - row["s"]) > TOL_FIELD or row["c_stamp"] != row["s_stamp"]:
                bad.append(row)
    obs = {"pairs": len(used), "invalid_pairs": invalid, "off": bad}
    if not used:
        return "unmeasured", obs, 0
    return ("falsified" if bad else "as_predicted"), obs, len(used)


def unprep_pred(D):
    """The adds on a stamped dish whose stamp is not 1 (each restores before vanilla's add): every add after a dish's
    first at a level whose scale is not 1, in the order they ran."""
    n = 0
    for lv in LEVELS:
        if prep_scale(lv) != 1.0:
            n += max(0, len([a for a in dish_adds(D, lv) if a.get("completed")]) - 1)
    for a in (g(D, "RN", "adds") or []) + (g(D, "RL", "adds") or []):
        if a.get("completed") and prep_scale(a.get("level")) != 1.0:
            n += 1
    return n


def all_adds(D):
    out = []
    for lv in LEVELS:
        out += dish_adds(D, lv)
    return out + list(g(D, "RN", "adds") or []) + list(g(D, "RL", "adds") or [])


def grade_counts_501(D):
    """COUNTS: cooks rose by the completed adds, prepped by the reliefs (every completed add here), unprepped by
    unprep_pred, cookFailures by 0."""
    s0, s1 = g(D, "S", "hstats") or {}, g(D, "C", "hstats") or {}
    key = "NutritionRevamp.server.hedonics.stats."
    d = {k: (num(s1.get(key + k)) - num(s0.get(key + k))) if None not in (num(s1.get(key + k)), num(s0.get(key + k)))
         else None for k in ("cooks", "prepped", "unprepped", "cookFailures")}
    done = sum(1 for a in all_adds(D) if a.get("completed"))
    want = {"cooks": done, "prepped": done, "unprepped": unprep_pred(D), "cookFailures": 0}
    obs = {"delta": d, "want": want}
    if any(v is None for v in d.values()) or done == 0:
        return "unmeasured", obs, 0
    return ("as_predicted" if d == want else "falsified"), obs, done


def add_row(P, add):
    for a in P.get("adds") or []:
        if a.get("add") == add:
            return a
    return {}


def grade_rename(D):
    """RENAME (I1): D10's stamp after its rename prepScale(10); its Potato add = the anchor's post-Potato value x
    prepScale(10)."""
    rn = g(D, "RN") or {}
    st = stamp_of(g(rn, "after", "10"), "s0")
    anc = field_of(add_row(rn, f"{LATE_ADD}@3").get("read"), "s0")
    v = field_of(add_row(rn, f"{LATE_ADD}@10").get("read"), "s0")
    s = prep_scale(10)
    obs = {"stamp_after_rename": st, "anchor_potato": anc, "d10_potato": v, "want": None if anc is None else anc * s,
           "d3_stamp_after_rename": stamp_of(g(rn, "after", "3"), "s0")}
    read = g(rn, "after", "10", "s0", "resolved") is True        # D10 read after the rename (its stamp, or none)
    d10 = dish_adds(D, 10)
    pre = stamp_of(d10[len(DISH_ADDS) - 1].get("read"), "s0") if len(d10) >= len(DISH_ADDS) else None
    if pre is None:
        return "unmeasured", dict(obs, why="D10 carried no stamp before the rename (SCALE's reading, not the rename's)"), 0
    if not read and st is None and v is None:
        return "unmeasured", dict(obs, why="no read after the rename"), 0
    if not (add_row(rn, f"{LATE_ADD}@3").get("completed") and add_row(rn, f"{LATE_ADD}@10").get("completed")):
        if read and (st is None or abs(st - s) > TOL_STAMP):     # the stamp half alone: off (or gone) when read
            return "falsified", dict(obs, why="a Potato add did not complete; the stamp read off or gone"), 1
        return "unmeasured", dict(obs, why="a Potato add did not complete"), 0
    ok = anc is not None and v is not None and abs(v - anc * s) <= TOL_FIELD and \
        (not read or (st is not None and abs(st - s) <= TOL_STAMP))
    return ("as_predicted" if ok else "falsified"), obs, 1


def grade_relog(D):
    """RELOG: each dish's server and client stamp and stored value after the relog as before it; D10's Pepper add = the
    anchor's post-Pepper value x prepScale(10)."""
    rl = g(D, "RL") or {}
    before, after = rl.get("before") or {}, rl.get("after") or {}
    rows, bad = [], []
    for lv in (str(x) for x in LEVELS):
        b, a = before.get(lv), after.get(lv)
        if not pair_ok(b) or not pair_ok(a):
            continue
        if lv != str(ANCHOR) and stamp_of(b, "s0") is None:      # no stamp before: the relog cannot show it kept
            continue
        row = {"level": lv, "before": [field_of(b, "s0"), stamp_of(b, "s0")],
               "after": [field_of(a, "s0"), stamp_of(a, "s0")], "client_after": [field_of(a, "c"), stamp_of(a, "c")]}
        rows.append(row)
        if abs(row["after"][0] - row["before"][0]) > TOL_FIELD or row["after"][1] != row["before"][1] or \
                row["client_after"][0] is None or abs(row["client_after"][0] - row["after"][0]) > TOL_FIELD or \
                row["client_after"][1] != row["after"][1]:
            bad.append(row)
    anc = field_of(add_row(rl, f"{RELOG_ADD}@3").get("read"), "s0")
    v = field_of(add_row(rl, f"{RELOG_ADD}@10").get("read"), "s0")
    obs = {"dishes": rows, "off": bad, "anchor_pepper": anc, "d10_pepper": v,
           "want": None if anc is None else anc * prep_scale(10)}
    if not rows:
        return "unmeasured", dict(obs, why="no valid pair before and after the relog"), 0
    if not (add_row(rl, f"{RELOG_ADD}@3").get("completed") and add_row(rl, f"{RELOG_ADD}@10").get("completed")):
        if bad:                                                   # the dish half alone: off when read
            return "falsified", dict(obs, why="a Pepper add did not complete; a dish moved"), len(rows)
        return "unmeasured", dict(obs, why="a Pepper add did not complete"), 0
    if anc is None or v is None or abs(v - anc * prep_scale(10)) > TOL_FIELD:
        bad.append({"pepper": [v, anc]})
    return ("falsified" if bad else "as_predicted"), obs, len(rows)


# ================================================================ x502: the plain-energy floor (pure)
def slots(rec):
    p = [num(rec.get(f"hedonics.p.{k}")) for k in range(1, RING_N + 1)]
    a = [num(rec.get(f"hedonics.a.{k}")) for k in range(1, RING_N + 1)]
    return p, a


def ring_ok(rec):
    p, a = slots(rec or {})
    return all(x is not None for x in p + a) and num((rec or {}).get("hedonics.f")) is not None


def grade_floor_of(reads):
    """FLOOR_OF: each record read's f = floorOf(share) of its own slots."""
    rows, bad = [], []
    for r in reads:
        rec = r.get("rec") or {}
        if not ring_ok(rec):
            continue
        p, a = slots(rec)
        sh = share_of(p, a)
        row = {"tag": r.get("tag"), "f": num(rec["hedonics.f"]), "share": sh, "want": floor_of(sh)}
        rows.append(row)
        if abs(row["f"] - row["want"]) > F_TOL:
            bad.append(row)
    n_up = sum(1 for r in rows if r["want"] > 0)
    if not rows or n_up == 0:
        return "unmeasured", {"why": "no ring read whose share stands above the curve's foot", "rows": rows}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad, "rows_up": n_up}, n_up


def grade_rise(eats, pred_f):
    """RISE: f after the plain eats never falls, ends over 0, each within PRED_F_TOL of the prerun's; the last read's
    moodLast.u at or over its f."""
    fs = [num(g(e, "rec", "hedonics.f")) for e in eats]
    us = [num(g(e, "rec", "moodLast.u")) for e in eats]
    obs = {"f": fs, "pred_f": list(pred_f or []), "u_last": us[-1] if us else None}
    if len(fs) < PLAIN_EATS or any(f is None for f in fs):
        return "unmeasured", dict(obs, why="an eat not read"), len([f for f in fs if f is not None])
    ok = all(b >= a - F_TOL for a, b in zip(fs, fs[1:])) and fs[-1] > 0
    ok = ok and pred_f is not None and len(pred_f) == len(fs) and all(abs(f - q) <= PRED_F_TOL
                                                                      for f, q in zip(fs, pred_f))
    ok = ok and us[-1] is not None and us[-1] >= fs[-1] - F_TOL
    return ("as_predicted" if ok else "falsified"), obs, len(fs)


def grade_last(eats):
    """LAST: each eat's lastIntake: plain, class and allies per the hedonics table (allies 1: no eat here is Hungry)."""
    rows, bad = [], []
    for e in eats:
        rec, full = e.get("rec") or {}, e.get("food")
        if not e.get("landed") or full not in CLASS_OF:
            continue
        row = {"tag": e.get("tag"), "fullType": rec.get("lastIntake.fullType"), "plain": rec.get("lastIntake.plain"),
               "class": rec.get("lastIntake.class"), "allies": rec.get("lastIntake.allies"),
               "want": [full, PLAIN_OF[full], CLASS_OF[full], 1]}
        rows.append(row)
        if [row["fullType"], row["plain"], row["class"], num(row["allies"])] != row["want"]:
            bad.append(row)
    if not rows:
        return "unmeasured", {"why": "no landed eat read"}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad}, len(rows)


def grade_offline(off):
    """OFFLINE: across the relog the slots and i identical, f identical, moodLast.u within U_GAP_TOL, and s moved by
    the absence (between the departure-to-relaunch span and the quit-to-return span, SLACK_H either side)."""
    b, a, rl = (off or {}).get("before") or {}, (off or {}).get("after") or {}, (off or {}).get("relog") or {}
    rb, ra = b.get("rec") or {}, a.get("rec") or {}
    a0, a1 = num(b.get("age")), num(a.get("age"))
    q, dep, back = num(rl.get("quit_age")), num(rl.get("depart_age")), num(rl.get("back_age"))
    lau = num(rl.get("launch_age"))
    obs = {"a0": a0, "a1": a1, "quit": q, "depart": dep, "launch": lau, "back": back, "s0": num(rb.get("hedonics.s")),
           "s1": num(ra.get("hedonics.s")), "i0": rb.get("hedonics.i"), "i1": ra.get("hedonics.i"),
           "f0": num(rb.get("hedonics.f")), "f1": num(ra.get("hedonics.f")), "u0": num(rb.get("moodLast.u")),
           "u1": num(ra.get("moodLast.u"))}
    if not ring_ok(rb) or not ring_ok(ra) or None in (a0, a1, q, dep, lau, back, obs["s0"], obs["s1"]):
        return "unmeasured", dict(obs, why="a ring read or a relog age missing"), 0
    if not obs["f0"] > 0 or sum(slots(rb)[1]) == 0:
        return "unmeasured", dict(obs, why="no floor or no kcal in the ring before the relog: nothing to keep"), 0
    if lau - dep - SLACK_H < GAP_MIN_H:
        return "unmeasured", dict(obs, why="the absence too short to tell a moved stamp from a frozen one"), 0
    if (a0 - obs["s0"]) % 1.0 + (dep - a0) + (a1 - back) + SLACK_H >= 1.0:
        return "unmeasured", dict(obs, why="an online hour boundary could fall in the gap's online bits"), 0
    same_slots = slots(rb) == slots(ra) and obs["i0"] == obs["i1"]
    ds = obs["s1"] - obs["s0"]
    obs.update({"ds": ds, "band": [lau - dep - SLACK_H, back - q + SLACK_H], "same_slots": same_slots})
    ok = (same_slots and abs(obs["f1"] - obs["f0"]) <= F_TOL and obs["u0"] is not None and obs["u1"] is not None
          and abs(obs["u1"] - obs["u0"]) <= U_GAP_TOL and obs["band"][0] <= ds <= obs["band"][1])
    return ("as_predicted" if ok else "falsified"), obs, 1


def grade_release(rel, before):
    """RELEASE: f 0 after the non-plain eat; moodLast.u fell by f's fall within U_FALL_TOL."""
    rb, ra = (before or {}).get("rec") or {}, (rel or {}).get("rec") or {}
    f0, f1 = num(rb.get("hedonics.f")), num(ra.get("hedonics.f"))
    u0, u1 = num(rb.get("moodLast.u")), num(ra.get("moodLast.u"))
    obs = {"f0": f0, "f1": f1, "u0": u0, "u1": u1, "landed": (rel or {}).get("landed")}
    if None in (f0, f1, u0, u1) or not (rel or {}).get("landed"):
        return "unmeasured", obs, 0
    if not f0 > 0:
        return "unmeasured", dict(obs, why="no floor stood before the release"), 0
    ok = abs(f1) <= F_TOL and abs((u0 - u1) - (f0 - f1)) <= U_FALL_TOL
    return ("as_predicted" if ok else "falsified"), obs, 1


def eat_events(rows, eats):
    """Each landed eat (in order) at the first ring row whose eats count rose, at its live item's calories, macros and
    hunger (the server's item.get before it) and its live fraction (1 - hung1 / hung0)."""
    events, notes = [], []
    queue = [e for e in eats if e.get("landed")]
    qi, prev = 0, None
    for r in rows:
        if prev is not None:
            a, b = num(prev.get(EATS_G)), num(r.get(EATS_G))
            if a is not None and b is not None and b > a:
                for _ in range(int(round(b - a))):
                    if qi >= len(queue):
                        notes.append(f"eats rose at s {r['s']} with no landed eat left")
                        continue
                    e = queue[qi]
                    i0, frac = e.get("item0") or {}, e.get("frac")
                    ev = {"s": r["s"], "kind": "eat", "fullType": e.get("food"), "cal": num(i0.get("calories")),
                          "carb": num(i0.get("carbs")), "lip": num(i0.get("lipids")),
                          "pro": num(i0.get("proteins")), "hunger": num(i0.get("hungChange")), "frac": frac,
                          "label": e.get("tag")}
                    if FOOD_TYPE.get(e.get("food")) is not None:
                        ev["foodType"] = FOOD_TYPE[e.get("food")]
                    if None in (ev["cal"], ev["hunger"], frac):
                        notes.append(f"eat {e.get('tag')}: its item or fraction unread; no event")
                    else:
                        events.append(ev)
                    qi += 1
        prev = r
    if qi < len(queue):
        notes.append(f"{len(queue) - qi} landed eat(s) never seen in the ring")
    return events, notes


# ================================================================ x503: alliesthesia (pure)
def eat_delta(e):
    """The eat's UNHAPPINESS delta, corrected by the writer's fall of the remembered target (the release lowers the
    stat by the fall), and its u x f."""
    u0, u1 = num(g(e, "stats0", "Unhappiness")), num(g(e, "stats1", "Unhappiness"))
    t0, t1 = num(g(e, "rec0", "moodLast.u")), num(g(e, "rec1", "moodLast.u"))
    if None in (u0, u1):
        return None, None
    fall = max(0.0, (t0 or 0.0) - (t1 or 0.0)) if None not in (t0, t1) else 0.0
    uf = None
    u_rt, f = num(g(e, "item0", "fields", "getUnhappyChange")), num(e.get("frac"))
    if u_rt is not None and f is not None:
        uf = u_rt * f
    return (u1 - u0) + fall, uf


def nearest_k(d, uf):
    if d is None or uf is None or uf == 0:
        return None
    return min((1.0, UTENSIL_SAD), key=lambda k: abs(d - uf * k))


def grade_pre(eats):
    """PRE: HUNGER at each before-read: R3S and I2C at or under ALLIES_AT, the Hungry arms over it."""
    rows, bad = [], []
    for e in eats:
        h = num(g(e, "stats0", "Hunger"))
        if h is None or e.get("arm") is None:
            continue
        hungry = e.get("arm") not in SATED_ARMS
        row = {"arm": e.get("arm"), "hunger": h, "hungry_wanted": hungry}
        rows.append(row)
        if (h > ALLIES_AT) != hungry:
            bad.append(row)
    if not rows:
        return "unmeasured", {"why": "no HUNGER read"}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad}, len(rows)


def arm_eat(eats, arm):
    for e in eats:
        if e.get("arm") == arm:
            return e
    return {}


def hungry_at(e):
    """True when the arm's before-read HUNGER is over ALLIES_AT (Hungry), False at or under it, None unread."""
    h = num(g(e, "stats0", "Hunger"))
    return None if h is None else h > ALLIES_AT


def grade_sated(eats):
    e = arm_eat(eats, "R3S")
    d, uf = eat_delta(e)
    k = nearest_k(d, uf)
    allies = num(g(e, "rec1", "lastIntake.allies"))
    obs = {"delta": d, "uf": uf, "k": k, "allies": allies, "frac": e.get("frac")}
    if hungry_at(e) is not False:
        return "unmeasured", dict(obs, why="the arm was not sated at its before-read"), 0
    if not e.get("landed") or d is None or uf is None or not uf > 0:
        return "unmeasured", obs, 0
    ok = allies == 1 and abs(d - uf * k) <= D_TOL
    return ("as_predicted" if ok else "falsified"), obs, 1


def grade_hungry(eats, arm="R3H"):
    e, s = arm_eat(eats, arm), arm_eat(eats, "R3S")
    d, uf = eat_delta(e)
    ks = nearest_k(*eat_delta(s))
    allies = num(g(e, "rec1", "lastIntake.allies"))
    obs = {"delta": d, "uf": uf, "k_sated": ks, "allies": allies, "frac": e.get("frac")}
    if hungry_at(e) is not True:
        return "unmeasured", dict(obs, why="the arm was not Hungry at its before-read"), 0
    if not e.get("landed") or d is None or uf is None or not uf > 0:
        return "unmeasured", obs, 0
    cands = (ks,) if ks is not None else (1.0, UTENSIL_SAD)
    ok = allies is not None and abs(allies - ALLIES_F) <= 1e-9 and \
        any(abs(d - uf * ALLIES_F * k) <= D_TOL for k in cands)
    return ("as_predicted" if ok else "falsified"), obs, 1


def grade_ratio(eats):
    ds, ufs = eat_delta(arm_eat(eats, "R3S"))
    dh, ufh = eat_delta(arm_eat(eats, "R3H"))
    obs = {"sated": [ds, ufs], "hungry": [dh, ufh]}
    if hungry_at(arm_eat(eats, "R3S")) is not False or hungry_at(arm_eat(eats, "R3H")) is not True:
        return "unmeasured", dict(obs, why="an arm on the wrong side of Hungry at its before-read"), 0
    if None in (ds, ufs, dh, ufh) or not ufs > 0 or not ufh > 0 or not ds > 0:
        return "unmeasured", obs, 0
    r = (dh / ufh) / (ds / ufs)
    obs["ratio"] = r
    return ("as_predicted" if abs(r - ALLIES_F) <= RATIO_TOL else "falsified"), obs, 1


def grade_remainder(eats):
    """REMAINDER: the field after = the field before x hung1 / hung0 for each eat whose item remains."""
    rows, bad = [], []
    for e in eats:
        f0 = num(g(e, "item0", "fields", "getUnhappyChangeUnmodified"))
        f1 = num(g(e, "item1", "fields", "getUnhappyChangeUnmodified"))
        h0, h1 = num(g(e, "item0", "fields", "getHungChange")), num(g(e, "item1", "fields", "getHungChange"))
        if not e.get("landed") or None in (f0, f1, h0, h1) or h0 == 0 or g(e, "item1", "resolved") is False:
            continue
        want = f0 * h1 / h0
        row = {"arm": e.get("arm"), "f0": f0, "f1": f1, "want": want}
        rows.append(row)
        if abs(f1 - want) > REL_TOL * max(1.0, abs(want)):
            bad.append(row)
    if not rows:
        return "unmeasured", {"why": "no remaining item read"}, 0
    return ("falsified" if bad else "as_predicted"), {"rows": rows, "off": bad}, len(rows)


def grade_cancel(eats):
    e = arm_eat(eats, "R3C")
    f = num(e.get("frac"))
    obs = {"frac": f, "landed": e.get("landed"), "cancel": e.get("cancel")}
    if not e.get("landed") or f is None or not 0 < f < 1:
        return "unmeasured", dict(obs, why="the cancel landed no part, or the whole"), 0
    v, o2, n = grade_hungry(eats, "R3C")
    obs.update(o2)
    return v, obs, n


def control_doubles(eats):
    """The vanilla control I2C (the same stale potato eaten sated: no alliesthesia, no restore): True when its client
    field after equals its server read-time value after within TOL_FIELD (vanilla's own eat path doubles the state
    term), False when not, None when the control is unread."""
    c = arm_eat(eats, "I2C")
    c_f1 = num(g(c, "citem1", "fields", "getUnhappyChangeUnmodified"))
    s_rt1 = num(g(c, "item1", "fields", "getUnhappyChange"))
    if not c.get("landed") or None in (c_f1, s_rt1):
        return None
    return abs(c_f1 - s_rt1) <= TOL_FIELD


def grade_i2(eats):
    """I2: the stale potato eaten Hungry: the client's stored field after is not the server's read-time value, and is
    the server's field after or the client's own before. Unmeasured when the vanilla control I2C doubles too (or is
    unread): a doubled field is then vanilla's, not the mod's."""
    e = arm_eat(eats, "I2")
    s_f1 = num(g(e, "item1", "fields", "getUnhappyChangeUnmodified"))
    s_rt1 = num(g(e, "item1", "fields", "getUnhappyChange"))
    s_f0 = num(g(e, "item0", "fields", "getUnhappyChangeUnmodified"))
    s_rt0 = num(g(e, "item0", "fields", "getUnhappyChange"))
    c_f0 = num(g(e, "citem0", "fields", "getUnhappyChangeUnmodified"))
    c_f1 = num(g(e, "citem1", "fields", "getUnhappyChangeUnmodified"))
    doubled_c = control_doubles(eats)
    obs = {"server_field": [s_f0, s_f1], "server_readtime": [s_rt0, s_rt1], "client_field": [c_f0, c_f1],
           "doubled_c": doubled_c}
    if hungry_at(e) is not True:
        return "unmeasured", dict(obs, why="the arm was not Hungry at its before-read"), 0
    if doubled_c is None:
        return "unmeasured", dict(obs, why="the vanilla control I2C unread"), 0
    if doubled_c:
        return "unmeasured", dict(obs, why="vanilla's eat path doubles the state term (I2C)"), 0
    if not e.get("landed") or None in (s_f0, s_rt0, s_f1, s_rt1, c_f1):
        return "unmeasured", dict(obs, why="an item read missing"), 0
    if abs((s_rt0 - s_f0) - STALE_TERM) > TOL_FIELD:
        return "unmeasured", dict(obs, why="the stale term is not read on the server"), 0
    doubled = abs(c_f1 - s_rt1) <= TOL_FIELD
    ok = not doubled and (abs(c_f1 - s_f1) <= TOL_FIELD or (c_f0 is not None and abs(c_f1 - c_f0) <= TOL_FIELD))
    return ("as_predicted" if ok else "falsified"), dict(obs, doubled=doubled), 1


def grade_counts_503(D):
    s0, s1 = g(D, "S", "hstats") or {}, g(D, "C", "hstats") or {}
    key = "NutritionRevamp.server.hedonics.stats."
    d = {k: (num(s1.get(key + k)) - num(s0.get(key + k))) if None not in (num(s1.get(key + k)), num(s0.get(key + k)))
         else None for k in ("allies", "restores", "alliesFailures")}
    eats = D.get("eats") or []
    hungry = [e for e in eats if e.get("landed") and e.get("arm") not in SATED_ARMS]
    remain = [e for e in hungry if g(e, "item1", "resolved") not in (False, None)]
    want = {"allies": len(hungry), "restores": len(remain), "alliesFailures": 0}
    obs = {"delta": d, "want": want}
    if any(v is None for v in d.values()) or not hungry:
        return "unmeasured", obs, 0
    return ("as_predicted" if d == want else "falsified"), obs, len(hungry)


# ================================================================ x504: the taste class and Rule 6 (pure)
def grade_class(D, label, want, rose, flat=()):
    P = g(D, label) or {}
    r0, r1 = P.get("rec0") or {}, P.get("rec1") or {}
    cls = r1.get("lastIntake.class")
    n0 = {k: num(r0.get(k)) or 0.0 for k in CLASS_KEYS[:4]}
    n1 = {k: num(r1.get(k)) or 0.0 for k in CLASS_KEYS[:4]}
    obs = {"class": cls, "n0": n0, "n1": n1, "landed": g(P, "eat", "landed")}
    key = f"monotony.t.[@{rose}].n"
    if not g(P, "eat", "landed") or "lastIntake.class" not in r1 and cls is None:
        return "unmeasured", obs, 0
    if num(r1.get(key)) is None:
        return "unmeasured", dict(obs, why=f"{key} unread after the eat"), 0
    ok = cls == want and n1[key] > n0[key] and all(n1[f"monotony.t.[@{k}].n"] <= n0[f"monotony.t.[@{k}].n"] + 1e-9
                                                   for k in flat)
    return ("as_predicted" if ok else "falsified"), obs, 1


def grade_dish_eat(D, labels=("A", "B")):
    """DISH_EAT: each dish eaten (UNHAPPINESS seeded at UNHAPPY_SEED first): the UNHAPPINESS delta (eat_delta) = u x f
    x k within D_TOL, u the read-time getUnhappyChange before the eat (negative: the dish's scaled relief), f the eaten
    fraction, k one of 1 and UTENSIL_GLAD (the same for every dish: a negative value eaten with a utensil is x1.25,
    #0048); the dishes are made at DISH_EAT_LEVEL, a dish whose Cooking did not hold reads unmeasured.
    Falsifier: the eat reading an unscaled or otherwise moved value (no k fits)."""
    rows = []
    for lb in labels:
        if num(g(D, lb, "perk", "reply", "after")) != DISH_EAT_LEVEL:     # the Cooking level did not hold: unmeasured
            continue
        e = g(D, lb, "eat") or {}
        d, uf = eat_delta(e)
        if not e.get("landed") or d is None or uf is None or not uf < 0:
            continue
        rows.append({"dish": lb, "delta": d, "uf": uf, "frac": e.get("frac")})
    if not rows:
        return "unmeasured", {"why": "no dish eat with a negative u read"}, 0
    fits = [k for k in (1.0, UTENSIL_GLAD) if all(abs(r["delta"] - r["uf"] * k) <= D_TOL for r in rows)]
    obs = {"rows": rows, "k": fits[0] if fits else None}
    return ("as_predicted" if fits else "falsified"), obs, len(rows)


def pct(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = max(1, min(len(s), math.ceil(round(p * len(s), 9))))
    return s[k - 1]


def summ(xs):
    xs = [x for x in xs if x is not None]
    return {"n": len(xs), "p50": pct(xs, 0.5), "p99": pct(xs, 0.99), "max": max(xs) if xs else None}


def frames_of(doc):
    F = (doc or {}).get("frames_list") or {}
    keys = ("frame", "start", "stop", "busy", "period", "endPeriod", "minute", "runs", "ghostMs")
    cols = [F.get(k) or [] for k in keys]
    n = min(len(c) for c in cols) if cols else 0
    return [dict(zip(keys, (c[i] for c in cols))) for i in range(n)]


def hits(lo, hi, wins):
    for w in wins or []:
        if None in (w[0], w[1], lo, hi):
            continue
        if lo <= w[1] and hi >= w[0]:
            return True
    return False


def arm_summary(A):
    """x391d's: the kept frames (those overlapping no bus step inside the window), busy, period, end-to-end period,
    the minute frames' busy, and the perf windows' max."""
    fr = frames_of(A.get("ring_doc"))
    wins = A.get("drop_windows") or []
    kept = [f for f in fr if num(f.get("busy")) is not None and f["busy"] >= 0
            and not hits(f["start"], f["stop"], wins)]
    mins = [f for f in kept if f.get("minute") == 1]
    S = (A.get("perf_doc") or {}).get("samples_list") or {}
    w, mx = S.get("wall") or [], S.get("max") or []
    pw = [mx[k] for k in range(1, min(len(w), len(mx))) if not hits(w[k - 1], w[k], wins)]
    return {"frames_ring": len(fr), "frames": len(kept), "minute_frames": len(mins),
            "busy": summ([f["busy"] for f in kept]), "busy_minute": summ([f["busy"] for f in mins]),
            "period": summ([f["period"] for f in kept if num(f.get("period")) is not None and f["period"] >= 0]),
            "endPeriod": summ([f["endPeriod"] for f in kept
                               if num(f.get("endPeriod")) is not None and f["endPeriod"] >= 0]),
            "perf_max": summ(pw)}


def grade_rule6(idle, load, stats, load_reply, modq_reply):
    """IDLE, F, SMOKE, P99, MAX, STARVE, S over the two arms' summaries; returns {name: (verdict, obs, samples)}."""
    out = {}
    bi, pi = g(idle, "busy", "p99"), g(idle, "period", "p50")
    out["IDLE"] = (("unmeasured", {"why": "no idle frames"}, 0) if bi is None or pi is None else
                   (("as_predicted" if bi <= IDLE_BUSY_P99_MAX and IDLE_PERIOD_BAND[0] <= pi <= IDLE_PERIOD_BAND[1]
                     else "falsified"), {"busy_p99": bi, "period_p50": pi}, 1))
    fr = {k: (g(a, "frames"), g(a, "minute_frames")) for k, a in (("idle", idle), ("load", load))}
    okf = all((x or 0) >= MIN_FRAMES and (y or 0) >= MIN_MINUTE_FRAMES for x, y in fr.values())
    out["F"] = (("as_predicted" if okf else "falsified"), fr, sum((x or 0) for x, _ in fr.values()))
    ghosts = num(g(modq_reply, "ghosts"))
    runs = num(g(stats, "runs"))
    smoke = {"load_ok": g(load_reply, "ok"), "modq_ok": g(modq_reply, "ok"), "ghosts": ghosts, "runs": runs}
    oks = g(load_reply, "ok") is True and g(modq_reply, "ok") is True and ghosts == N_LOAD - REALS and (runs or 0) > 0
    out["SMOKE"] = (("as_predicted" if oks else "falsified"), smoke, 1)
    pl, pi99 = g(load, "endPeriod", "p99"), g(idle, "endPeriod", "p99")
    out["P99"] = (("unmeasured", {"why": "no end-to-end period"}, 0) if None in (pl, pi99) else
                  (("as_predicted" if pl - pi99 <= RULE_P99 else "falsified"),
                   {"load": pl, "idle": pi99, "add": pl - pi99}, 1))
    ml, mi = g(load, "perf_max", "max"), g(idle, "perf_max", "max")
    out["MAX"] = (("unmeasured", {"why": "no perf window"}, 0) if None in (ml, mi) else
                  (("as_predicted" if ml - mi <= RULE_MAX else "falsified"), {"load": ml, "idle": mi, "add": ml - mi}, 1))
    se = num(g(stats, "starvedEvents"))
    out["STARVE"] = (("unmeasured", {"why": "no ghost.stats"}, 0) if se is None else
                     (("as_predicted" if se == 0 else "falsified"), {"starvedEvents": se}, 1))
    s = {k: num(g(stats, k)) for k in ("failures", "storeGhostKeys", "neverRun")}
    out["S"] = (("unmeasured", {"why": "no ghost.stats"}, 0) if any(v is None for v in s.values()) else
                (("as_predicted" if all(v == 0 for v in s.values()) else "falsified"), s, 1))
    return out


def rule6_reading(idle, load):
    """Beside x391d's mod draws at the same spacing (#3744): a reading, never a grade."""
    pl, pi99 = g(load, "endPeriod", "p99"), g(idle, "endPeriod", "p99")
    return {"p99_add": None if None in (pl, pi99) else pl - pi99, "x391d_p99_adds": list(X391D_P99_ADDS),
            "longest_window": g(load, "perf_max", "max"), "x391d_longest": list(X391D_LONGEST),
            "worst_end_to_end": g(load, "endPeriod", "max"), "worst_minute_busy": g(load, "busy_minute", "max")}


def grade_z(out, D):
    """Z: no mod error line, admin not parked, no hedonics failure counter rose between S and C."""
    v, obs = G.grade_z(out)
    s0, s1 = g(D, "S", "hstats") or {}, g(D, "C", "hstats") or {}
    key = "NutritionRevamp.server.hedonics.stats."
    rose = {k: (num(s1.get(key + k)), num(s0.get(key + k))) for k in FAIL_KEYS}
    obs = dict(obs, failures=rose)
    if any(a is not None and b is not None and a > b for a, b in rose.values()):
        return "falsified", obs
    return v, obs


# ================================================================ the pre-boot checks (offline; tested)
def profile_doc_checks(name, doc, text=""):
    """The profile's TOML: its header naming its own file, fixture default, the one admin client, sleep off, PZTestKit
    and the staged copy, Nutrition false, DayLength 4, the [sandbox.NR] block of Mode, DeathPace and HealthCombine alone
    at the session's values, the version verify rows (server and client), the server timeout."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = sorted(v.get("side") for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version")
    return {"known_profile": True,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture": doc.get("fixture") == spec["fixture"],
            "clients": doc.get("clients", [USER]) == spec["clients"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods": mods == ["PZTestKit", NR],
            "mod_staged": paths.get(NR) == STAGE_MOD,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == spec["day_length"],
            "nr_block": sb.get("NR") == {"Mode": spec["mode"], "DeathPace": spec["pace"],
                                         "HealthCombine": spec["combine"]},
            "verify_rows": vr == ["client", "server"],
            "no_override": "client_overrides" not in doc,
            "server_timeout": srv.get("timeout") == SERVER_TIMEOUT_S}


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def prerun_current(key, repo=REPO, compute=None, committed=None):
    """The session's committed prediction against the one re-derived now (x50_prerun.compute)."""
    if compute is None:
        import x50_prerun as PR
        compute = PR.compute
    have = (committed if committed is not None else load_prerun(os.path.join(repo, PRERUN_FILE))).get(key)
    try:
        now = json.loads(json.dumps(compute([key])[key], sort_keys=True, default=str))
    except Exception as e:                                         # noqa: BLE001 - recorded, refuses the boot
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": have == now, "committed": have is not None,
            "diff": None if have == now else {"committed": have, "now": now}}


def preboot(key, driver_file, repo=REPO, compute=None):
    """The driver's file names its session (CLAUDE.md s5); no artifact of the prefix committed; the profile's TOML;
    STAGED_FROM mod/'s last commit; the harness markers; the fixture fresh; the prediction current. Returns (checks,
    ok)."""
    import glob
    import tomllib
    s = SESSIONS.get(key) or {}
    base = os.path.basename(driver_file)
    c = {"key": key in SESSIONS, "driver_file": base == s.get("driver"), "driver_prefix": base.startswith(key + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", key + "-*"))
    head = mod_head(repo)
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", s.get("profile", "?") + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(s.get("profile"), tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    c["harness_found"], c["harness_markers"] = L49.markers_ok(HARNESS_FILES, HARNESS_MARKERS, repo)
    fr = L48.fixture_fresh(repo)
    c["fixture"] = fr
    c["fixture_fresh"] = fr["fresh"]
    pr = prerun_current(key, repo, compute) if c["key"] else {"ok": False}
    c["prerun"] = pr
    c["prerun_current"] = pr["ok"]
    skip = ("profile_checks", "harness_found", "fixture", "prerun")
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO):
    """x45g_lib's gate at this lib's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


def parse_argv(argv, driver_file):
    """x49_lib's: a driver takes no argument; the refusal text, or None for a bare call."""
    return L49.parse_argv(argv, driver_file)


# ================================================================ the session
class Sess(G.Sess):
    """One x50 session's phases over an xlib.Xs, on x45g_lib.Sess's plumbing (k, lread, rec, poll, the clock, the ring
    and W). `launch(S, user, sub)` relaunches a client (x49_lib.launch_real)."""

    def __init__(self, xs, key, run_dir=None, prerun=None, launch=None):
        self.xs = xs
        self.out = xs.out
        self.key = key
        self.spec = SESSIONS[key]
        self.prof = PROFILES[self.spec["profile"]]
        self.D = self.out.setdefault("checks", {})
        self.run_dir = run_dir
        self.speeds = self.out.setdefault("speeds", [])
        self.cur_speed = None
        self.restore_to = None
        self.pages, self.eats, self.pairs, self.points, self.consts, self.drinks = [], [], [], [], [], []
        self.sets = self.out.setdefault("sets", [])
        self.red0 = None
        self.launch = launch
        self.P = prerun if prerun is not None else load_prerun().get(key, {})
        self.out["lib_x50"] = LIB_FILE
        self.out["constants_x50"] = dict(CONSTANTS)
        self.out["prerun_x50"] = self.P

    # -- reads
    def glob(self, tag, paths, log=True):
        return vals(self.lread(tag, SRV, "_G", paths, log=log))

    def hstats(self, tag):
        return self.glob(tag, HSTATS_G)

    def cooks(self, tag):
        return num(self.glob(tag, ("NutritionRevamp.server.hedonics.stats.cooks",), log=False).get(
            "NutritionRevamp.server.hedonics.stats.cooks"))

    def landed(self, tag):
        return num(self.glob(tag, (LANDED_G[3:],), log=False).get(LANDED_G[3:]))

    def writes(self, tag):
        return num(self.glob(tag, (WRITES_G[3:],), log=False).get(WRITES_G[3:]))

    def item_read(self, tag, side, ref, md=True):
        """witness.fields of FIELDS (and witness.moddata NR_PrepS) on one side; ref "#<id>" or a full type."""
        sref = (f"{USER}/{ref}") if side == SRV else ref
        f = self.k(tag + "_f", side, "witness.fields", f"item {sref} {','.join(FIELDS)}")
        row = {"fields": f.get("fields") if isinstance(f.get("fields"), dict) else {}, "resolved": f.get("resolved"),
               "error": f.get("error") or f.get("raw"), "wall": f.get("wall"), "wall_after": f.get("wall_after")}
        if row["resolved"] is not None and row["resolved"] is not False:
            row["resolved"] = True
        if md:
            m = self.k(tag + "_md", side, "witness.moddata", f"item:{sref} NR_PrepS")
            row["md"] = m.get("values") if isinstance(m.get("values"), dict) else {}
            row["wall_after"] = m.get("wall_after")
        return row

    def dish_read(self, tag, ref):
        return {"s0": self.item_read(tag + "_s0", SRV, ref), "c": self.item_read(tag + "_c", CLI, ref),
                "s1": self.item_read(tag + "_s1", SRV, ref)}

    def inv_ids(self, tag, full):
        r = self.k(tag, CLI, "inv.ids", full)
        items = r.get("items")
        if isinstance(items, dict):                    # the bus answers an empty list as {}
            items = []
        return [x for x in (items or []) if isinstance(x, dict)], r

    def perk(self, tag, level):
        r = self.k(tag, SRV, "perk.set", f"{USER} Cooking {int(level)}")
        row = {"level": level, "reply": {k: r.get(k) for k in ("perk", "requested", "before", "after", "route", "error",
                                                              "raw")}}
        self.D.setdefault("perks", []).append(row)
        return row

    def stats_all(self, tag):
        a = self.k(tag, SRV, "stats.all", USER)
        s = a.get("stats") if isinstance(a.get("stats"), dict) else {}
        return {"Unhappiness": num(s.get("Unhappiness")), "Hunger": num(s.get("Hunger")),
                "Boredom": num(s.get("Boredom")), "wall": a.get("wall"), "worldAge": num(a.get("worldAge"))}

    def wait_write(self, tag):
        """One writer minute: the writer's writes counter rising."""
        w0 = self.writes(tag + "_w0")

        def fn():
            w = self.writes(tag + "_w")
            return (w is not None and w0 is not None and w > w0), w
        return self.poll(tag, fn, WRITE_CAP_S)

    def common_S(self):
        P = self.D["S"] = {}
        P["players"] = self.xs.step("S_players", SRV, "players")["ack"]
        P["sandbox"] = self.glob("S_sv", ("SandboxVars.Nutrition", "SandboxVars.DayLength", "SandboxVars.NR.Mode",
                                          "SandboxVars.NR.DeathPace", "SandboxVars.NR.HealthCombine",
                                          "SandboxVars.SleepAllowed", "NutritionRevamp.version",
                                          OPT_PACE[3:], OPT_COMBINE[3:], OPT_DAYMIN[3:]))
        P["clock"] = self.clock_read()
        P["nutrition"] = self.k("S_nutrition", SRV, "nutrition.get", USER)
        P["stats_all"] = self.k("S_stats_all", SRV, "stats.all", USER)
        P["hstats"] = self.hstats("S_hstats")
        P["cooking"] = self.k("S_cooking", SRV, "perk.xp", f"{USER} Cooking")
        P["health"] = self.health("S_health")
        return P

    def restore_cooking(self):
        lv = num(g(self.D, "S", "cooking", "level"))
        self.D["cooking_restore"] = self.perk("C_perk", int(lv)) if lv is not None else {"skipped": "unread at S"}

    def common_C(self):
        P = self.D["C"] = {}
        P["hstats"] = self.hstats("C_hstats")
        self.restore_clock()

    def spawn_all(self, spawns):
        P = self.D["I"] = {"spawns": []}
        for full, n in spawns:
            P["spawns"].append(self.spawn(full, n, "I_" + full.split(".")[-1]))

    def closing_names(self):
        return ("C", "R")

    # -- the relog (x49_lib's)
    def relog(self, label, hold_s=OFFLINE_HOLD_S):
        P = {"quit_age": self.age(label + "_quit_a")}
        c = self.xs.clients.get(USER)
        q = {"wall0": self.xs.wall()}
        try:
            q["rc"] = c.quit(timeout=QUIT_TIMEOUT_S) if c is not None else None
        except Exception as e:                       # noqa: BLE001 - recorded
            q["error"] = f"{type(e).__name__}: {e}"
        q["wall1"] = self.xs.wall()
        self.xs.clients.pop(USER, None)
        P["quit"] = q

        def gone():
            a = self.xs.step(label + "_players", SRV, "players", log=False).get("ack")
            lst = a if isinstance(a, list) else ([] if isinstance(a, dict) and not a else None)
            return (lst is not None and USER not in lst), lst
        P["depart"] = self.poll(label + "_depart", gone, DEPART_CAP_S)
        P["depart_age"] = self.age(label + "_depart_a")
        if not P["depart"]["done"]:
            self.xs.note(f"{label}: admin never left the server inside the cap; no rejoin")
            return P
        self.sleep_until(self.xs.clock() + hold_s)
        P["launch_age"] = self.age(label + "_launch_a")
        P["launch"] = self.launch(self, USER, label.lower()) if self.launch else {"error": "no launcher"}
        if not g(P, "launch", "ready_took"):
            self.xs.note(f"{label}: admin was not ready after the relaunch")
            return P

        def back():
            a = self.xs.step(label + "_players2", SRV, "players", log=False).get("ack")
            return (isinstance(a, list) and USER in a), a
        P["back"] = self.poll(label + "_back", back, REJOIN_CAP_S)
        P["back_age"] = self.age(label + "_back_a")
        return P

    # -- the eat (x45g's, with a fraction and the item read around it)
    def eat(self, label, full, frac, arm=None, rec_paths=(), client_item=False, cancel_after=None):
        """eat.action <full> <frac> on the admin client with NO foodtimer.set (the mod owns the food timer); landed is
        the server's intake landed counter rising. Before and after: the server's item (by its id), the stats, the
        record paths; the client's item when client_item."""
        e = {"tag": label, "arm": arm, "food": full, "asked": frac, "landed": False}
        self.eats.append(e)
        got = self.k(label + "_id", SRV, "item.get", f"{USER} {full}")
        e["item0_get"] = {k: got.get(k) for k in ("id", "calories", "carbs", "lipids", "proteins", "hungChange",
                                                  "baseHunger", "age", "fresh", "offAge", "raw")}
        iid = num(got.get("id"))
        ref = f"#{int(iid)}" if iid is not None else full
        e["ref"] = ref
        e["item0"] = self.item_read(label + "_i0", SRV, ref, md=False)
        e["item0"].update({k: got.get(k) for k in ("calories", "carbs", "lipids", "proteins", "hungChange")})
        if client_item:
            e["citem0"] = self.item_read(label + "_c0", CLI, ref, md=False)
        e["rec0"] = self.rec(label + "_rec0", tuple(rec_paths), log=True) if rec_paths else {}
        e["stats0"] = self.stats_all(label + "_st0")
        b = self.landed(label + "_l0")
        e["age0"] = self.age(label + "_a0")
        q = self.k(label + "_eat", CLI, "eat.action", f"{full} {frac}")
        e["queued"] = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime",
                                             "moodleFoodEaten", "error", "raw")}
        self.xs.spawned_stop(q, label)
        if cancel_after is not None:
            mt = num(q.get("maxTime")) or 232.0
            self.sleep_until(self.xs.clock() + cancel_after * mt / 60.0)
            e["cancel"] = self.k(label + "_cancel", CLI, "action.cancel")

        def fn():
            a = self.landed(label + "_poll")
            return (a is not None and b is not None and a > b), a
        p = self.poll(label + "_land", fn, EAT_CAP_S)
        e["landed"] = p["done"]
        e["landed_age"] = self.age(label + "_a1")
        e["stats1"] = self.stats_all(label + "_st1")
        e["item1"] = self.item_read(label + "_i1", SRV, ref, md=False)
        if client_item:
            self.xs.sleep(SYNC_WAIT_S)
            e["citem1"] = self.item_read(label + "_c1", CLI, ref, md=False)
            e["sitem1b"] = self.item_read(label + "_i1b", SRV, ref, md=False)
        e["rec1"] = self.rec(label + "_rec1", tuple(rec_paths), log=True) if rec_paths else {}
        h0 = num(g(e, "item0", "fields", "getHungChange"))
        h1 = num(g(e, "item1", "fields", "getHungChange"))
        if e["landed"] and h0:
            e["frac"] = 1.0 if g(e, "item1", "resolved") is not True or h1 is None else 1.0 - h1 / h0
        return e

    def grade_set(self, name, res, falsifier):
        v, obs, samples = res
        self.xs.grade(name, v, obs, falsifier, samples=samples)

    def grade_common(self):
        v, obs = grade_z(self.out, self.D)
        self.xs.grade("Z", v, obs, "a mod error line, a hedonics failure counter rising, or admin parked")


class Prep(Sess):
    """x501: preparation quality (R2)."""

    def add(self, P, label, level, base_ref, ingredient, first=False, pair=True):
        """recipe.add Stir_fry <base> <ingredient>; polled on the server's cooks counter (and, first, on the new dish's
        id in the client's inventory); then the pair read (the server alone when not `pair`). Returns the add row."""
        a = {"add": f"{ingredient}@{level}", "ingredient": ingredient, "level": level, "base": base_ref,
             "completed": False}
        P.setdefault("adds", []).append(a)
        c0 = self.cooks(label + "_c0")
        ids0 = [x.get("id") for x in self.inv_ids(label + "_ids0", DISH)[0]] if first else []
        q = self.k(label + "_q", CLI, "recipe.add", f"{RECIPE} {base_ref} {ingredient}")
        a["queued"] = {k: q.get(k) for k in ("ok", "queued", "usable", "maxTime", "reason", "base", "used", "raw")}
        if q.get("queued") is not True:
            self.xs.note(f"{label}: recipe.add {ingredient} on {base_ref} not queued: {q.get('reason') or q.get('raw')}")
            return a

        def fn():
            c = self.cooks(label + "_poll")
            return (c is not None and c0 is not None and c > c0), c
        a["poll"] = self.poll(label + "_done", fn, ADD_CAP_S)
        a["completed"] = a["poll"]["done"]
        if not a["completed"]:
            return a
        ref = base_ref
        if first:
            def new():
                rows, _ = self.inv_ids(label + "_ids1", DISH)
                fresh = [x.get("id") for x in rows if x.get("id") not in ids0]
                return (len(fresh) == 1), fresh
            p = self.poll(label + "_new", new, ID_CAP_S)
            a["new_ids"] = p["last"]
            if not p["done"]:
                self.xs.note(f"{label}: no single new dish in the client's inventory: {p['last']!r}")
                return a
            ref = f"#{int(num(p['last'][0]))}"
            P["ref"] = ref
        if pair:                                       # the client's copy: wait for the seat's syncs first
            self.xs.sleep(SYNC_WAIT_S)
            a["read"] = self.dish_read(label + "_r", ref)
        else:                                          # the server's: the seat writes it in the complete call
            a["read"] = {"s0": self.item_read(label + "_r_s0", SRV, ref)}    # whose cooks counter was polled
        return a

    def dish(self, level):
        name = f"D{level}"
        P = self.D[name] = {"level": level, "adds": []}
        self.perk(f"{name}_perk", level)
        base = PAN
        for k, ing in enumerate(DISH_ADDS):
            a = self.add(P, f"{name}_{k}", level, base, ing, first=(k == 0), pair=(k == len(DISH_ADDS) - 1))
            if not a.get("completed") or P.get("ref") is None:
                self.xs.note(f"{name}: the dish stopped at add {k}")
                return
            if k == 0 and level == ANCHOR:
                self.ids_guard(P)
            base = P["ref"]

    def ids_guard(self, P):
        """After D3's first add D3 is the only dish: the server's item.get of it against the client's id (concern 3: a
        mismatch explains a run of unresolved server reads)."""
        got = self.k("D3_srvid", SRV, "item.get", f"{USER} {DISH}")
        sid, cid = num(got.get("id")), num(str(P.get("ref") or "")[1:] or None)
        P["server_id"], P["ids_agree"] = sid, (sid is not None and sid == cid)

    def phase_I(self):
        self.spawn_all(SPAWNS_501)

    def phase_D3(self):
        self.dish(3)

    def phase_D0(self):
        self.dish(0)

    def phase_D10(self):
        self.dish(10)

    def late(self, P, label, ingredient, levels=(3, 10)):
        for lv in levels:
            ref = g(self.D, f"D{lv}", "ref")
            if ref is None:
                continue
            self.perk(f"{label}_perk{lv}", lv)
            self.add(P, f"{label}_{lv}", lv, ref, ingredient, pair=False)     # RENAME and RELOG read the server

    def phase_RN(self):
        P = self.D["RN"] = {"renames": {}, "after": {}, "adds": []}
        for lv in (3, 10):
            ref = g(self.D, f"D{lv}", "ref")
            if ref is None:
                continue
            P["renames"][str(lv)] = self.k(f"RN_rename{lv}", CLI, "item.rename", f"{ref} {RENAMED[lv]}")
        self.xs.sleep(RENAME_WAIT_S)
        for lv in (3, 10):
            ref = g(self.D, f"D{lv}", "ref")
            if ref is not None:
                P["after"][str(lv)] = self.dish_read(f"RN_after{lv}", ref)
        self.late(P, "RN", LATE_ADD)

    def phase_RL(self):
        P = self.D["RL"] = {"before": {}, "after": {}, "adds": []}
        for lv in LEVELS:
            ref = g(self.D, f"D{lv}", "ref")
            if ref is not None:
                P["before"][str(lv)] = self.dish_read(f"RL_before{lv}", ref)
        P["relog"] = self.relog("RL", hold_s=RELOG_HOLD_S)
        if not g(P, "relog", "back", "done"):
            return
        self.xs.sleep(SYNC_WAIT_S)
        self.re_resolve(P)
        for lv in LEVELS:
            ref = g(self.D, f"D{lv}", "ref")
            if ref is not None:
                P["after"][str(lv)] = self.dish_read(f"RL_after{lv}", ref)
        self.late(P, "RL", RELOG_ADD)

    def re_resolve(self, P):
        """After the relog, each dish found again in the client's inventory: D3 and D10 by their names, D0 as the one
        dish not renamed; a dish whose id moved is read by its new id and the move is recorded (ids_changed)."""
        rows, _ = self.inv_ids("RL_ids", DISH)
        P["ids_after"] = rows
        by_name = {r.get("name"): r.get("id") for r in rows}
        plain = [r.get("id") for r in rows if not r.get("custom")]
        for lv in LEVELS:
            old = g(self.D, f"D{lv}", "ref")
            want = by_name.get(RENAMED[lv]) if lv in RENAMED else (plain[0] if len(plain) == 1 else None)
            if old is None or num(want) is None:
                continue
            new = f"#{int(num(want))}"
            if new != old:
                self.D[f"D{lv}"]["ref"] = new
                P.setdefault("ids_changed", {})[str(lv)] = [old, new]

    def phase_C(self):
        self.restore_cooking()
        self.common_C()

    def phases(self):
        return [("S", self.common_S), ("I", self.phase_I), ("D3", self.phase_D3), ("D0", self.phase_D0),
                ("D10", self.phase_D10), ("RN", self.phase_RN), ("RL", self.phase_RL), ("C", self.phase_C)]

    def closing_names(self):
        return ("C",)

    def grade_all(self):
        D = self.D
        perks = [p for p in D.get("perks") or [] if p is not D.get("cooking_restore")]
        self.grade_set("WRAP", grade_wrap(D.get("S"), perks), "wrappedCook not true, or a perk.set off its level")
        self.grade_set("ANCHOR", grade_anchor(D), "the Cooking-3 dish off the jar model, or its stamp not 1")
        self.grade_set("SCALE", grade_scale(D), "a Cooking 0 or 10 dish off the anchor x prepScale, or its stamp off")
        self.grade_set("CLIENT", grade_client(D), "a valid pair whose client field or stamp differs from the server's")
        self.grade_set("COUNTS", grade_counts_501(D), "a hedonics counter off the adds made")
        self.grade_set("RENAME", grade_rename(D), "the stamp lost to the rename's sync, or the next add compounding")
        self.grade_set("RELOG", grade_relog(D), "a stamp or value moved by the relog, or the next add off")
        self.grade_common()
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}


class Floor(Sess):
    """x502: the plain-energy floor (R1), graded against the HEAD replay."""

    def ring_read(self, tag):
        """The record's ring and the composed target, with the age read after."""
        return {"tag": tag, "rec": self.rec(tag, HED_READ, log=True), "age": self.age(tag + "_a")}

    def plain_eat(self, label, full, frac):
        e = self.eat(label, full, frac)
        if e["landed"]:
            e["write"] = self.wait_write(label + "_write")
        r = self.ring_read(label + "_ring")
        e["rec"], e["rec_age"] = r["rec"], r["age"]
        self.D.setdefault("reads", []).append(r)
        return e

    def phase_H(self):
        P = self.D["H"] = {}
        rec = [p for p in RING_502 if not p.startswith("_G.")]
        P["ring_paths"] = list(RING_502)
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(G.H1_EXTRA))
        P["ring_start"] = self.ring_start(list(RING_502))

    def phase_I(self):
        self.spawn_all(((BUTTER, 1), (PEANUT, 1)))

    def phase_E(self):
        self.D["E"] = [self.plain_eat(f"E{k + 1}", BUTTER, BUTTER_F) for k in range(PLAIN_EATS)]

    def phase_OFF(self):
        P = self.D["OFF"] = {}
        P["before"] = self.ring_read("OFF_before")
        P["relog"] = self.relog("OFF")
        if g(P, "relog", "back", "done"):
            P["write"] = self.wait_write("OFF_write")
            P["after"] = self.ring_read("OFF_after")

    def phase_REL(self):
        P = self.D["REL"] = {}
        P["before"] = self.ring_read("REL_before")
        P["eat"] = self.plain_eat("REL_eat", PEANUT, PEANUT_F)

    def phase_C(self):
        self.common_C()

    def phases(self):
        return [("S", self.common_S), ("H", self.phase_H), ("W", self.phase_W), ("I", self.phase_I),
                ("E", self.phase_E), ("OFF", self.phase_OFF), ("REL", self.phase_REL), ("C", self.phase_C),
                ("R", self.phase_R)]

    def replay_inputs(self):
        start_path = os.path.join(self.run_dir or "", "start.json")
        if not os.path.isfile(start_path):
            return None
        with open(start_path, encoding="utf-8") as fh:
            start = json.load(fh)
        nut = g(self.D, "S", "nutrition") or {}
        sex = g(self.D, "H", "h1_record", "values", "body.sex")
        player = {"female": sex == 2, "weight": num(nut.get("weight")) or 80.0,
                  "macros": [num(nut.get(k)) or 0.0 for k in ("calories", "carbs", "lipids", "proteins")],
                  "health": num(g(self.D, "S", "health")) or 100.0}
        return start, player, g(self.D, "W", "start_stats") or {}

    def grade_replay(self, rows):
        xs = self.xs
        inp = self.replay_inputs() if rows else None
        if inp is None:
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "no replay"}, "")
            return None
        start, player, start_stats = inp
        events, notes = eat_events(rows, self.eats)
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD, game_heal on",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": False,
                                    "death_pace": self.prof["pace"], "health_combine": self.prof["combine"],
                                    "day_minutes": DAY_MIN, "tol": {k: list(v) for k, v in REPLAY_TOL.items()},
                                    "placement_notes": notes}
        try:
            import replay_live as RL
            rep, _ = RL.replay_live(rows, events, start, paths=list(RING_502), user=USER, player=player,
                                    start_stats=start_stats, sleep_allowed=False, death_pace=self.prof["pace"],
                                    health_combine=self.prof["combine"], day_minutes=DAY_MIN, game_heal=True)
            d = RL.diff(rep, rows, REPLAY_TOL)
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return None
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": rep, "diff": d, "events": events}, indent=1, sort_keys=True,
                                    default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(rep), "fields": d.get("fields"), "classes": d.get("classes"),
                              "findings_n": len(d.get("findings") or [])}
        for f in REPLAY_TOL:
            v, obs = G.grade_replay_field(d, f)
            xs.grade(f"REPLAY_{f}", v, obs, f"{f} off the HEAD replay by more than {REPLAY_TOL[f][1]}")
        return rep

    def grade_all(self):
        D = self.D
        rows = self.ring_rows()
        self.out["ring_rows"] = len(rows)
        self.xs.grade("H1", *L48.grade_h1(g(D, "H", "h1_record"), g(D, "H", "ring_start"), H1_NIL_OK),
                      "a ring path other than H1_NIL_OK unresolved at the start")
        self.xs.grade("RING", *G.grade_ring(g(D, "R", "pages") or []), "a ring page unread or a ring error")
        reads = list(D.get("reads") or []) + [x for x in (g(D, "OFF", "before"), g(D, "OFF", "after"),
                                                          g(D, "REL", "before")) if x]
        self.grade_set("FLOOR_OF", grade_floor_of(reads), "a ring read's f off floorOf of its own slots")
        pred = [g(x, "f") for x in g(self.P, "eats") or []][:PLAIN_EATS]
        self.grade_set("RISE", grade_rise(D.get("E") or [], pred),
                       "f falling over the plain eats, ending at 0, off the prerun, or over the composed target")
        eats = list(D.get("E") or []) + ([g(D, "REL", "eat")] if g(D, "REL", "eat") else [])
        self.grade_set("LAST", grade_last(eats), "lastIntake's plain, class or allies off the table's")
        self.grade_set("OFFLINE", grade_offline(D.get("OFF")),
                       "a slot, i, f or the target moved across the relog, or s not moved by the absence")
        self.grade_set("RELEASE", grade_release(g(D, "REL", "eat"), g(D, "REL", "before")),
                       "f not 0 after the non-plain eat, or the target not falling by f's fall")
        self.grade_replay(rows)
        self.grade_common()
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}


class Allies(Sess):
    """x503: alliesthesia (R3) and the client's copy (I2)."""

    REC = ("moodLast.u", "lastIntake.fullType", "lastIntake.allies", "lastIntake.frac", "satiety.M", "hedonics.f")

    def phase_H(self):
        P = self.D["H"] = {}
        P["ring_start"] = self.ring_start(list(RING_503))

    def phase_I(self):
        self.spawn_all(SPAWNS_503)

    def seed_unhappy(self, tag):
        return self.k(tag, SRV, "stats.setany", f"{USER} UNHAPPINESS {UNHAPPY_SEED}")

    def seed_hungry(self, tag):
        P = {"M": self.record_set(tag + "_M", "satiety.M", "0"),
             "hunger": self.k(tag + "_h", SRV, "stats.setany", f"{USER} HUNGER {HUNGRY_SEED}")}
        P["write"] = self.wait_write(tag + "_w")
        return P

    def arm(self, name, full, frac, hungry, cancel_after=None, client_item=False, pre=None, unhappy=True):
        P = self.D[name] = {}
        if pre is not None:
            P["pre"] = pre()
        if hungry:
            P["seed"] = self.seed_hungry(name + "_hseed")
        if unhappy:
            P["unhappy"] = self.seed_unhappy(name + "_useed")
        P["eat"] = self.eat(name, full, frac, arm=name, rec_paths=self.REC, client_item=client_item,
                            cancel_after=cancel_after)

    def phase_R3S(self):
        self.arm("R3S", BUTTER, ALLIES_EAT_F, hungry=False)

    def phase_R3H(self):
        self.arm("R3H", BUTTER, ALLIES_EAT_F, hungry=True)

    def phase_R3C(self):
        self.arm("R3C", LARD, 1, hungry=True, cancel_after=CANCEL_FRAC)

    def phase_I2C(self):
        """The vanilla control: the potato aged stale, a quarter eaten sated, with no seed (no alliesthesia, no
        restore): its client field after is vanilla's own."""
        def pre():
            return self.k("I2C_age", SRV, "item.set", f"{USER} {POTATO} age {STALE_AGE_D}")
        self.arm("I2C", POTATO, POTATO_F / 2, hungry=False, client_item=True, pre=pre, unhappy=False)

    def phase_I2(self):
        self.arm("I2", POTATO, POTATO_F / 2, hungry=True, client_item=True)

    def phase_C(self):
        self.common_C()

    def phases(self):
        return [("S", self.common_S), ("H", self.phase_H), ("I", self.phase_I), ("R3S", self.phase_R3S),
                ("I2C", self.phase_I2C), ("R3H", self.phase_R3H), ("I2", self.phase_I2), ("R3C", self.phase_R3C),
                ("C", self.phase_C), ("R", self.phase_R)]

    def grade_all(self):
        D = self.D
        D["eats"] = self.eats
        self.xs.grade("RING", *G.grade_ring(g(D, "R", "pages") or []), "a ring page unread or a ring error")
        self.grade_set("PRE", grade_pre(self.eats), "HUNGER on the wrong side of Hungry at an arm's eat")
        self.grade_set("SATED", grade_sated(self.eats), "the sated delta off u x f x k, or allies not 1")
        self.grade_set("HUNGRY", grade_hungry(self.eats), "the Hungry delta off u x f x 0.6 x k, or allies not 0.6")
        self.grade_set("RATIO", grade_ratio(self.eats), "the Hungry over the sated delta per unit off 0.6")
        self.grade_set("REMAINDER", grade_remainder(self.eats), "a remainder's field off the field x hung1 / hung0")
        self.grade_set("CANCEL", grade_cancel(self.eats), "a cancelled Hungry part not scaled, or allies off")
        self.grade_set("I2", grade_i2(self.eats), "the client's field carrying the server's read-time value, where "
                       "the vanilla control I2C does not")
        self.grade_set("COUNTS", grade_counts_503(D), "the allies or restores counter off the Hungry eats")
        self.grade_common()
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}


class Taste(Sess):
    """x504: the taste class (R4) and Rule 6."""

    def phase_H(self):
        P = self.D["H"] = {}
        P["ring_start"] = self.ring_start(list(RING_504))

    def phase_I(self):
        self.spawn_all(SPAWNS_504)

    def make(self, label, adds):
        P = self.D[label] = {"adds": []}
        P["perk"] = self.perk(f"{label}_perk", DISH_EAT_LEVEL)
        base = PAN
        for k, ing in enumerate(adds):
            a = Prep.add(self, P, f"{label}_{k}", None, base, ing, first=(k == 0), pair=False)
            if not a.get("completed") or P.get("ref") is None:
                self.xs.note(f"{label}: the dish stopped at add {k}")
                return P
            base = P["ref"]
        P["rec0"] = self.rec(label + "_rec0", CLASS_KEYS, log=True)
        P["unhappy"] = self.k(label + "_useed", SRV, "stats.setany", f"{USER} UNHAPPINESS {UNHAPPY_SEED}")
        P["eat"] = self.eat(label + "_eat", DISH, 1, arm=label, rec_paths=("moodLast.u",))
        if P["eat"].get("landed"):
            P["write"] = self.wait_write(label + "_write")
        P["rec1"] = self.rec(label + "_rec1", CLASS_KEYS, log=True)
        return P

    def phase_A(self):
        self.make("A", DISH_A)

    def phase_B(self):
        self.make("B", DISH_B)

    def rule6_arm(self, tag, load):
        A = self.D[tag] = {"tag": tag, "load": load}
        if load:
            A["load_reply"] = self.k(f"{tag}_load", SRV, "ghost.load", f"{N_LOAD} mod feed")
            A["modq_on"] = self.k(f"{tag}_modq_on", SRV, "ghost.modq", "on")
            self.sleep_until(self.xs.clock() + SETTLE_S)
            A["reset"] = self.k(f"{tag}_reset", SRV, "ghost.stats", "reset")
        A["perf_arm"] = self.xs.step(f"{tag}_perf_arm", SRV, "perf.local", str(PERF_N))
        A["ring_arm"] = self.xs.step(f"{tag}_ring_arm", SRV, "tick.ring", str(RING_FRAMES))
        A["window_start_wall"] = self.xs.wall()
        self.sleep_until(self.xs.clock() + ARM_WALL_S)
        A["window_end_wall"] = self.xs.wall()
        after = self.xs.clock() - 1.0
        A["perf_read"] = self.xs.step(f"{tag}_perf_read", SRV, "perf.local", f"read {tag}")
        A["ring_read"] = self.xs.step(f"{tag}_ring_read", SRV, "tick.ring", f"read {tag}")
        if load:
            A["stats"] = self.k(f"{tag}_stats", SRV, "ghost.stats")
            A["modq_off"] = self.k(f"{tag}_modq_off", SRV, "ghost.modq", "off")
        A["perf_doc"] = self.xs.wait_doc(f"perf-local-{tag}", after)
        A["ring_doc"] = self.xs.wait_doc(f"tick-ring-{tag}", after)
        if load:
            A["stop"] = self.k(f"{tag}_stop", SRV, "ghost.stop")
            self.out["world_changes"]["left_in_place"].append(
                f"{tag}: {N_LOAD - REALS} ghost records ran against admin under the mod's queue")
        A["drop_windows"] = [[A["ring_arm"].get("epoch_ms_before"), A["ring_arm"].get("epoch_ms_after")],
                             [A["perf_read"].get("epoch_ms_before"), A["perf_read"].get("epoch_ms_after")]]
        for name in (f"perf-local-{tag}", f"tick-ring-{tag}"):
            if self.xs.server is not None and self.run_dir:
                src = os.path.join(self.xs.server.bus.results_dir, name + ".json")
                dst = os.path.join(self.run_dir, name + ".json")
                if os.path.isfile(src):
                    if os.path.abspath(src) != os.path.abspath(dst):
                        shutil.copyfile(src, dst)
                    self.xs.copied.append(name + ".json")
        A["summary"] = arm_summary(A)
        A.pop("ring_doc", None)
        A.pop("perf_doc", None)

    def phase_IDLE(self):
        self.rule6_arm("IDLE", False)

    def phase_LOAD(self):
        self.rule6_arm("LOAD", True)

    def phase_Z6(self):
        """The cleanup: no ghost load left behind whatever LOAD did."""
        self.D["Z6"] = {"stop": self.k("Z6_stop", SRV, "ghost.stop"), "modq_off": self.k("Z6_modq", SRV, "ghost.modq",
                                                                                         "off")}

    def phase_C(self):
        self.restore_cooking()
        self.common_C()

    def phases(self):
        return [("S", self.common_S), ("H", self.phase_H), ("I", self.phase_I), ("A", self.phase_A),
                ("B", self.phase_B), ("IDLE", self.phase_IDLE), ("LOAD", self.phase_LOAD), ("Z6", self.phase_Z6),
                ("C", self.phase_C), ("R", self.phase_R)]

    def closing_names(self):
        return ("Z6", "C", "R")

    def grade_all(self):
        D = self.D
        self.xs.grade("RING", *G.grade_ring(g(D, "R", "pages") or []), "a ring page unread or a ring error")
        self.grade_set("CLASS_A", grade_class(D, "A", "savoury", "savoury", flat=("fatty",)),
                       "dish A read fatty (the heaviest portion's class) or no class, or @savoury not rising")
        self.grade_set("CLASS_B", grade_class(D, "B", "fatty", "fatty"), "dish B not fatty, or @fatty not rising")
        self.grade_set("DISH_EAT", grade_dish_eat(D), "a dish eat's UNHAPPINESS delta off u x f x k for k in 1, 1.25 "
                       "(the eat not reading the dish's stored, scaled value)")
        idle, load = g(D, "IDLE", "summary"), g(D, "LOAD", "summary")
        res = grade_rule6(idle or {}, load or {}, g(D, "LOAD", "stats"), g(D, "LOAD", "load_reply"),
                          g(D, "LOAD", "modq_on"))
        falsifiers = {"IDLE": "idle busy p99 over 10 ms or period p50 outside 99-101", "F": "too few frames",
                      "SMOKE": "the load or the queue not on, or no ghost run", "P99": "the p99 add over 20 ms",
                      "MAX": "the longest-window add over 25 ms", "STARVE": "a starved minute event",
                      "S": "a ghost failure, a ghost store key or a never-run ghost"}
        for name, r in res.items():
            self.grade_set(name, r, falsifiers[name])
        self.out["readings"]["rule6"] = rule6_reading(idle or {}, load or {})
        self.grade_common()
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}


KINDS = {"x501": Prep, "x502": Floor, "x503": Allies, "x504": Taste}


# ================================================================ the boot
def main(key, driver_file, session_text, pred, budget_s):
    """One boot of x50-hedonics (x49b_lib.main's shape at this lib's session, staged copy and checks)."""
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_client, make_server, verify   # noqa: E402

    pre, ok = preboot(key, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    s = SESSIONS[key]
    prof = profile.load(s["profile"])
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(key)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=USER)
    xs.path = os.path.join(run_dir, s["artifact"])
    S = KINDS[key](xs, key, run_dir=run_dir, launch=L49.launch_real(make_client, prof, rec_fx, started, tl))
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "session": session_text, "driver": os.path.basename(driver_file),
        "lib": LIB_FILE, "user": USER, "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": pred, "constants": CONSTANTS, "meta": {"budget_s": budget_s},
        "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "driver_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + s["driver"]),
        "prerun_commit": git_say("log", "-1", "--format=%h", "--", PRERUN_FILE),
        "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    mg["version_is_release"] = mg.get("staged_version") == STAGED_VERSION
    if not (mg["ok"] and mg["verify_rows_match"] and mg["version_is_release"]):
        xs.refuse(f"the staged copy does not match the pinned commit, the verify rows or {STAGED_VERSION}: {mg!r}; "
                  "not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(profile.lint_sources(prof, prof.sources))
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        tl.mark("server_started", pid=server.proc.pid)
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[USER], started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, okm = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, okm):
            pass
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            S.body_run(S.phases())
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            Lg = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "mod_error": MOD_ERR_RX.pattern}}
            if server is not None:
                logs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
                Lg["server"], Lg["server_echo_excluded"] = [], 0
                for lp in logs:
                    hits_, skipped = X.grep_noecho(lp, LOG_RX, 300, ECHO_RX, NEVER_RX)
                    Lg["server"] += hits_
                    Lg["server_echo_excluded"] += skipped
                Lg["mod_error"] = [ln for ln in Lg["server"] if MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                Lg.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, s["artifact"])
    B._summary(out, run_id, run_dir)
    return out
