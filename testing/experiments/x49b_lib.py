"""x49b_lib -- the session engine of Plan 18 Task 4, the live acceptance of the symptom layer (spec
docs/superpowers/specs/2026-10-21-symptoms-design.md section 4, the live acceptance): on a seeded Realistic fast with
water (starvation, then wet beriberi at clinical), the Pain, Endurance, Stress and Unhappy moodles at their predicted
progress on the server and on the client, the release after a snack, each graded against the HEAD replay of the run's
own inputs. One session, x494, one boot under 10 wall minutes in a foreground call, build 42.21.0.

Built on testing/experiments/xlib.py and on the frozen libs of the sessions it follows, imported unchanged (CLAUDE.md
s5: a lib is frozen with its first run):
  x48_lib.py   (x481's) its Sess (the record setter bracketed by two age reads, the clock and its restore, the ring
               and its pages, W's start.json, the thiamine write and its poll, the replay inputs), its write placement
               (build_events) and its pure grades H1, ONSET and BERI_ON, its fixture-fresh and prerun checks;
  x45g_lib.py  through it: the staged gate, the Z and RING grades, the replay-field grade;
  x49_lib.py   (x491-x493's) the probe's reads: the pair (a server lua.read of TKX_Symptoms.s and a client lua.read of
               TKX_Symptoms.c, valid when their wall midpoints sit within 1 s), the hold of pairs, the level trackers,
               the probe's error reads, the jar's thresholds and pain modifiers (level_of), and the pure grades
               P0_BASE (grade_base), the steady levels (grade_steady), the held levels (grade_hold_level) and the
               level-follows grade (grade_follows, FOLLOW_EPS: the Pain moodle's 120-update timer).
Their own constants (STAGED_FROM, SESSIONS, the ring) are theirs and never read for this session: this file names its
own staged copy, commit, session, profile, ring, schedule and tolerances. x48b_lib.py (x484's) is the shape this file
starts from (its preboot, gates, main and summary); it is not imported, since its constants are x484's.

THE STAGED COPY. The profile boots release/NutritionRevamp/Contents/mods/NutritionRevamp, re-staged from mod/'s last
commit (`python tools/release_pack.py stage mod/NutritionRevamp --out release`); staged_gate checks it against
release_pack.manifest() of mod/ at STAGED_FROM and refuses on a mismatch, and preboot refuses when STAGED_FROM is not
mod/'s last commit. mod/ is never booted (CLAUDE.md s5, x201).

THE PROFILE (testing/profiles/x49-accept.toml): fixture default, admin -debug, PZTestKit, the staged copy and the
probe TKX_Symptoms by its path (installed only through test profiles), Nutrition false (ruling T18-1), DayLength 4 (the
90-minute day the design's magnitudes are set for), SLEEP OFF (SleepAllowed and SleepNeeded false: the endurance cap is
the symptom lever that works on every server, and x484's replay of this fixture ran sleep off; the fatigue rows and
vanilla's endurance-deficit fatigue accrual are not observed here), [sandbox.NR] Mode 1, DeathPace 3 (Realistic),
HealthCombine 2 (Multiply) and Severity 1.0, the declared defaults written so the profile says what the run is. The
probe is an observer only: no hold is ever armed (its holds write the same stats the mod writes); its per-tick
snapshots on both sides (TKX_Symptoms.s and .c, the tracked part Torso_Lower, 7) and its level trackers are read.

THE FIRST SIGHT (CLAUDE.md s5). The default fixture's character has no store record, so the session starts on a fresh
record, which lands its seed plate and lays the mod's own creation body (x484's). The prediction (x49b_prerun.py, written
to x49b_prerun.json) is the HEAD replay of the session's schedule from x48_lib.FIRST_SIGHT's vanilla stats with no
typed weight; preboot refuses a boot whose committed prediction is not the HEAD replay's.

THE SESSION x494 accept (DayLength 4: a game minute is 3.75 wall s at speed 1):
  S   x48's reads (the sandbox, the clock, nutrition, stats, health, the constant), then the sandbox's InjurySeverity,
      the probe watching admin, its log reset, the client's tracked part 7, every part's added pain and S's pair.
  H   the minute ring (RING, the harness's cap of 32 paths) and H1's read.
  W   the store's next save as start.json (x48's).
  A   at speed 1: record.set satiety.M 0, then drain.fedAgeH to the age less STARVE_ONSET_H plus SEED_LEAD_H (x484's
      seed); SPEED_FAST until the record reads starveAcute, every poll's wall kept (the onset's wall bracket); speed 1.
  ON  the onset's arm at speed 1: ARM_SETTLE_S, both trackers reset, pairs for ON_S (to about 75 s after the onset, so
      both sides' Pain onset windows fall inside the arm's pairs; starvation's pain alone at its onset cap, Endurance
      1), the trackers and every part read.
  P1  at speed 1: record.set drain.pS P1_P (the smoothed starvation progress, so the cap and floors read their values at
      that progress inside the session; the active state keeps the largest progress, K.drain.smooth); polled until the
      record's stressFloor moves; then the floors read off the record and STRESS and UNHAPPINESS set to them once with
      stats.setany (THE FLOOR SEED, below); ARM_SETTLE_S, both trackers reset, pairs every PAIR_EVERY_S for P1_S, the
      trackers and every part read.
  B   x481's thiamine: record.set nutrients.thiamine.p THIAMINE_P, polled until the grade reads 4 (wet beriberi at
      clinical, its pain on both lower legs); then the arm's pairs for B_S, as P1.
  P2  as P1 at P2_P.
  L   THE RELEASE: at speed 1, record.set satiety.M SNACK_M (a real snack's meal pool, over K.drain.SUSPEND_M, the
      200 kcal snack's; since 6ee7c8d1 the kinetics step opens the meal spell on the pool before the minute clears it,
      driver review concern 1; it opens a meal spell and resets the unfed clock: starvation lapses; beriberi stays); polled until the
      record's mask drops starvation; pairs for L1_S at speed 1 (the immediate release), then SPEED_FAST and pairs for
      L2_S (the decay and the easing), each arm's trackers reset at its start; every part read.
  C   the clock back to the trueMult read at S (x48's); the probe's errors and every part read.
  R   the ring's pages.

THE FLOOR SEED. The writer raises STRESS toward its floor at moodRiseStress, 0.003 a game minute (K.hybrid), while
vanilla decays it 0.0018 a game minute between writes (x493's T91.25), and UNHAPPINESS at 22 a game hour, so a floor that
a seeded progress raises at once is reached only after hours (STRESS 0.30 after about 250 game minutes). A natural
progress moves far slower than either ramp, so the stat sits on its floor; the session seeds each stat at the floor the
record reads once and grades the floor's hold: STRESS stays over its floor less one interval's vanilla decay only while
the writer holds it (unheld it falls 0.0018 a game minute), and the writer's remembered UNHAPPINESS target
(record.moodLast.u, on the ring) carries the floor (UNHAPPINESS never falls on its own, so the stat alone cannot show
the hold); the release then shows the floor leaving (UNHAPPINESS falls by the remembered target's fall at once).
Each stat is set to max(its read, the floor), so a stat vanilla raised over its floor is never lowered (F8). The seeds
are replay events (kind stat) placed at the first ring row read after them. A reading guide or delta built on this run
never claims the mod RAISES STRESS or UNHAPPINESS to its floor: the seed put each stat there; the grades show the hold
(STRESS_FLOOR) and the target carrying the floor (UNHAPPY_FLOOR's ring half; its stat half does not discriminate).

THE WALL. Every arm is shortened to keep CLOSE_RESERVE_S of the budget for C and R; with under LEVEL_MIN_PAIRS pairs'
worth left the budget stops the session at that arm (xlib.Budget) and only the closing phases run. An arm shortened
records secs_asked and secs_given, and the grades timed on the full arm (PAIN_LEVELS, PAIN_TARGET, REL_END's level
bound, REL_STRESS's levels) read it unmeasured, never falsified (F5). The teardown is bounded (bounded_teardown: the
client's quit TEARDOWN_QUIT_S, the server's stop TEARDOWN_STOP_S, then hard_kill), so BUDGET_S 470 plus the close, the
teardown and the copy stays under the 600 s foreground cap (F3).

THE EFFECTS IN FORCE. The ring row s is read inside the minute event before the mod's queue drains (row s holds what
drain s - 1 left); a pair at world age a, with ring row s the last read at or before a, sees the effects of drain s - 1
or, a few ticks after the event, of drain s: the replay rows labelled s and s + 1. A ceiling is graded against the
larger of the two, a floor against the smaller; a predicted level is read only where both give one level.

THE GRADES (pure; each has a failing case in testing/tests/test_x49b_lib.py; a grade on no valid sample is unmeasured,
never as_predicted; every tolerance is named below, before any run):
  preconditions
    OPT        the first ring row: K.drain.OPT pace 3, combine 2 and dayMin 90; SandboxVars.NR.Severity and the polled
               severity 1.
    ONSET      x48's: a starveAcute row within SEED_LEAD_H + ONSET_SLACK_H game hours of the seed.
    P0_BASE    x49's at S's pair: no part holds added pain; PAIN, STRESS, UNHAPPY and ENDURANCE at level 0.
    BERI_ON    x48's: grade 4 and beriberi's fraction near 1 within BERI_GM game minutes of the thiamine write.
    H1, RING   x48's and x45g's (the ring's paths at the start, its pages read with no error).
    Z          no mod or probe error line in the server log, admin never parked, no probe-recorded error.
  the replay
    REPLAY_<f> for each REPLAY_TOL field (health, drain.target, the endurance cap, both floors, the lower torso's and the
               left lower leg's added-pain targets, the writer's remembered UNHAPPINESS target): every ring row within
               its tolerance of the HEAD replay of the run's own inputs. REPLAY_health is graded to the lapse row: past
               it the stand-in's uniform 5.05/17 heal (replay_live game_heal) misses the per-part clamp of
               AddGeneralHealth (jar, F2 of the driver review), predicted up to 0.35 health ahead about 25 game minutes
               after the lapse; every other field on every row (the record writes as setpath events at x48's
               placement, but a drain.pS write at the drain that first ran on it, place_progress: no drain moves the
               progress, so x48's would place it one drain late when it lands between a row's read and its drain, a
               minute of the floor rate's take, 0.059 health; the floor seeds as stat events).
  pain
    PAIN_PART  on every valid pair of ON, P1, B and P2 while the replay's lower-torso target is above 0 in both rows in
               force, the server's Torso_Lower added pain within [target - DIP x PART_DIP_GM - PART_TOL, target +
               PART_TOL] (DIP the decay a game minute, 0.01 x dayMin, Task 1's T91.19; the mod sets the part each
               minute, never lowering a higher value, ruling T3-1); and at each arm's end read every painful part (7,
               13, 14) in the same band.
    PAIN_TARGET at P1's and P2's last valid pair the server's PAIN within [TARGET_MIN_FRAC x inj x sum(mod x (target -
               DIP)), inj x sum(mod x target) + TARGET_TOL] (x49's P1_TARGET on the replay's targets; the replay
               carries the target, not live PAIN, so the band takes the minute's dip: Task 3 concern 5); unmeasured
               under TARGET_HZ_MIN server ticks a second (the pairs' snapshot ticks over their ms).
    PAIN_ONSET per side, the reads after the onset bracket the Pain moodle's change to level 1: the first level-1 read
               less the onset drain's latest wall not under the window's lo, the last level-0 read before it less the
               drain's earliest wall not over its hi (a gap between reads never falsifies; F1); the window
               [ONSET_LO_FRAC x approach - PAIR_EVERY_S, approach + timer + PAIR_EVERY_S + ONSET_SLACK_S], approach
               the 1/500-a-tick rise (#2362, T91.15) from 0 to 10 at the onset's mid PAIN at the measured server tick
               rate, timer the Pain moodle's 120 updates (Task 1's J9) at that rate or the client's measured frame
               rate; unmeasured under TARGET_HZ_MIN ticks, the client side under L49.CLIENT_FPS_MIN frames.
    PAIN_LEVELS the last STEADY_N valid pairs of P1, B, P2 and L2 read, on both sides, the Pain level of the mid PAIN
               (inj x sum(mod x (target - DIP / 2))) of the replay's targets in force.
    PAIN_FOLLOWS x49's P1_FOLLOWS over ON, P1, B, P2 and L1: each side's level is its own PAIN's, FOLLOW_EPS off a
               threshold (L2 is left out: at SPEED_FAST the lower torso's decay moves PAIN about 11 over the server's
               12 s timer).
  endurance
    END_CAP    on every valid pair of every arm (ON to L2), the server's ENDURANCE at or under the larger cap in force plus
               END_CLIMB_TOL (one interval's worst climb, END_REGEN_UNIT x 2 x dayMin x PART_DIP_GM): graded from the
               replay's effects.enduranceCap, never the stand-in's ENDURANCE (Task 3 review F3).
    END_LEVELS ON, P1, B and P2: every valid pair and both trackers read the Endurance level of the cap in force (the
               onset's 0.73: Endurance 1, light at onset).
  floors
    STRESS_FLOOR   on every valid pair of P1, B and P2, the server's STRESS at or over the smaller floor in force less
               STRESS_FLOOR_TOL (vanilla decays it between writes).
    UNHAPPY_FLOOR  the server's UNHAPPINESS at or over the smaller floor less UNHAPPY_FLOOR_TOL on every such pair, and
               every ring row of those arms' spans reads record.moodLast.u at or over its effects.unhappyFloor less
               U_TARGET_TOL (the writer's target carries the floor).
    STRESS_LEVELS, UNHAPPY_LEVELS  P1, B and P2: every valid pair and both trackers at the level of the floor in force.
  the release
    REL_LAPSE  (precondition) a ring row within LAPSE_GM game minutes of the snack's write reads starvation out of the
               mask, beriberi still in it.
    REL_PAIN   after the lapse row (plus one game minute), the server's Torso_Lower added pain never rises by more than
               PART_RISE_EPS between valid pairs (no set) and falls DIP a game minute within DECAY_GM_TOL over at
               least DECAY_MIN_N gaps with it above 0, its last read at the decay's own end (max(0, first - DIP x the
               game minutes), within PART_TOL plus DECAY_GM_TOL of the fall); PAIN_LEVELS' L2 reads the legs'.
    REL_END    the replay's cap in force at L2's last pair above P2's by at least EASE_MIN (eased); no valid pair of L1
               and L2 reads ENDURANCE under the pair before by more than END_FALL_EPS (no pull-down); L2's last
               STEADY_N pairs read, on both sides, the level of their own ENDURANCE and at most END_EASED_LEVEL_MAX (a
               sample within L49.FOLLOW_EPS_END of an edge skipped, at least LEVEL_MIN_PAIRS a side; F4).
    REL_UNHAPPY at the first ring row after the snack whose moodLast.u fell by REL_U_MIN_FALL or more, UNHAPPINESS
               within UNHAPPY_DROP_TOL of the row before's less that fall (at once); L1's last STEADY_N pairs read
               Unhappy level 0 on both sides.
    REL_STRESS after the lapse row, no valid pair reads STRESS over the pair before by more than STRESS_RISE_EPS; the
               fall over at least DECAY_MIN_N gaps a game minute within STRESS_DECAY_TOL of STRESS_DECAY_GM (vanilla's
               awake decay, #2772, x493's T91.25); L2's last STEADY_N pairs read, on both sides, the Stress level of
               P2's floor less STRESS_DECAY_GM a game minute since the lapse (a pair predicted within STRESS_FLOOR_TOL +
               L49.FOLLOW_EPS_STRESS of a threshold skipped; F7).
    REL_HEAL   (F2) the ring rows after the lapse row: health never over its own drain.target + REL_HEAL_TOL, never
               under the row before by more than REL_HEAL_TOL (no take), the last within REL_HEAL_TOL of its target;
               unmeasured until REL_HEAL_MIN_GM game minutes past the lapse row. The replay's health beside the live
               value is a reading (the stand-in's heal leads it); the stand-in's clamp is a Task 6 or close-review item.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402
import x48_lib as L48                                                         # noqa: E402
import x49_lib as L49                                                         # noqa: E402

REPO = X.REPO
SRV = X.SRV
CLIENT = L49.CLIENT
USER = L48.USER
NR = G.NR
LIB_FILE = "x49b_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "6ee7c8d1"                 # mod/'s last commit (Plan 18 Task 3b: the snack's spell check), staged
                                         # before the boot
STAGED_VERSION = "1.0.0"
PRERUN_FILE = "testing/experiments/x49b_prerun.json"
MIN_FREE_GB = 12.0
PROBE = L49.PROBE
PROBE_DIR = L49.PROBE_DIR

SESSIONS = {"x494": {"driver": "x494_accept.py", "artifact": "accept.json", "profile": "x49-accept"}}
PROFILES = {"x49-accept": {"fixture": "default", "clients": [USER], "day_length": 4, "mode": 1, "pace": 3,
                           "combine": 2, "severity": 1.0}}
SERVER_TIMEOUT_S = 240                   # the profile's [server] timeout: the slow-boot fallback's bound (x484's)

# ---- the jar's and the kernel's numbers (read before the run)
DAY_MIN = L48.DAY_MIN                    # DayLength 4: the 90-minute day
DIP_PER_GM_UNIT = L49.DECAY_PER_UNIT * L49.UNITS_PER_GM_PER_DAYMIN   # added pain falls 0.01 x dayMin a game minute (J3)
END_REGEN_UNIT = L49.END_REGEN_UNIT      # the mod's K.hybrid.END_REGEN_UNIT, the worst standing climb a unit (#2258)
UNITS_PER_GM_PER_DAYMIN = L49.UNITS_PER_GM_PER_DAYMIN
PAIN_MOD = L49.PAIN_MOD                  # BodyPartType.<clinit>: 7 Torso_Lower 0.78, 13 and 14 LowerLeg 0.6 (J5)
PAIN_PARTS = (7, 13, 14)                 # starvation's part, beriberi's two (NR_Data_Effects.lua SYMPTOMS)
TORSO = 7
STRESS_DECAY_GM = 0.0018                 # vanilla's awake STRESS decay a game minute at the 90-minute day (#2772;
                                         # x493-20261021-062610 T91.25: 0.00178-0.00182)
TICK_HZ_NOM = 10.0                       # the server's tick lock (#3355; x491: 9.9996-10.0002)
PAIN_TIMER_UPDATES = 120                 # Moodle.Update's painTimer (J9)
CLIENT_FPS_NOM = 60.0                    # x491's client frame rate
RISE_DIV = L49.RISE_DIV                  # PAIN rises (target - PAIN) / 500 a tick (#2362, T91.15)

# ---- the schedule (game minutes at DayLength 4)
SEED_LEAD_H = L48.SEED_LEAD_H            # x484's: the unfed clock to STARVE_ONSET_H - SEED_LEAD_H
STARVE_ONSET_H = L48.STARVE_ONSET_H
THIAMINE_P = L48.THIAMINE_P              # x481's: under the clinical rung 0.4167
P1_P = 0.5                               # the seeded smoothed progress of P1: cap 0.355 (Endurance 2), STRESS floor 0.30
                                         # (Stress 1), UNHAPPINESS floor 25 (Unhappy 1) (NR_Data_Effects.lua knots)
P2_P = 0.9                               # P2: cap 0.125 (Endurance 3), STRESS 0.55 (Stress 2), UNHAPPINESS 50 (Unhappy 2)
SNACK_M = 240.0                          # a real snack's meal pool, at K.drain.SUSPEND_M 236.44 or more (a 200 kcal
                                         # mixed snack's): since 6ee7c8d1 the kinetics step opens the meal spell on
                                         # the pool before the minute clears it (driver review concern 1)
SPEED_FAST = L48.SPEED_FAST              # 5: a game minute 0.75 wall s
PAIR_EVERY_S = L49.PAIR_EVERY_S          # 2.0
ARM_SETTLE_S = L49.ARM_SETTLE_S          # 4.0: one game minute at speed 1 and a little
ON_S = 70.0                              # the onset's pairs span both Pain onset windows (to about 75 s; F1)
P1_S = 35.0                              # P1's last pair about 126 s after the onset: PAIN's approach needs about 89
B_S = 50.0                               # Pain 2 by about 32 s after the legs' set (x491: 23.4-30.3 s)
P2_S = 40.0
L1_S = 16.0
L2_S = 46.0
ONSET_CAP_S = L48.ONSET_CAP_S            # 30.0
BERI_CAP_S = L48.BERI_CAP_S              # 15.0
FLOOR_CAP_S = 12.0                       # the seed's drain: at most two minute events at speed 1
LAPSE_CAP_S = 15.0
POLL_S = L48.POLL_S
CLOSE_RESERVE_S = 25.0                   # wall kept after the last arm for C and R
TEARDOWN_QUIT_S = 30                     # the bounded teardown's client quit and server stop (F3; x49's STOP_TIMEOUT_S
TEARDOWN_STOP_S = 45                     # precedent): pzt's own 60 s and 120 s could pass the 600 s foreground cap
REL_HEAL_MIN_GM = 50.0                   # REL_HEAL is measured once the ring reaches this many game minutes past the lapse
REL_HEAL_TOL = 0.002                     # REPLAY_TOL's health bound

# ---- the tolerances (named before any run)
REPLAY_TOL = {"health": ("abs", 0.002), "drain.target": ("abs", 0.002),
              "effects.enduranceCap": ("abs", 1e-6), "effects.stressFloor": ("abs", 1e-6),
              "effects.unhappyFloor": ("abs", 1e-4), "effects.pain.7": ("abs", 1e-6),
              "effects.pain.13": ("abs", 1e-6), "moodLast.u": ("abs", 1e-4)}
STEADY_N = L49.STEADY_N                  # 5
LEVEL_MIN_PAIRS = L49.LEVEL_MIN_PAIRS    # 3
FOLLOW_EPS = L49.FOLLOW_EPS              # 3.0 PAIN: the 120-update timer at the steepest rise
FOLLOW_EPS_LEVEL = {"pain": L49.FOLLOW_EPS, "endurance": L49.FOLLOW_EPS_END, "stress": L49.FOLLOW_EPS_STRESS,
                    "unhappy": L49.FOLLOW_EPS_UNHAPPY}
TARGET_MIN_FRAC = L49.TARGET_MIN_FRAC    # 0.85
TARGET_TOL = L49.TARGET_TOL              # 0.01
TARGET_HZ_MIN = L49.TARGET_HZ_MIN        # 9.0
PART_DIP_GM = 1.7                        # game minutes between two of the mod's writes at most: a minute event's dtM
                                         # (0.94-1.11 at speed 1, 0.8-1.6 at speed 5; ruling S0-1) and the ticks to
                                         # its drain
PART_TOL = 0.01
END_CLIMB_TOL = END_REGEN_UNIT * UNITS_PER_GM_PER_DAYMIN * DAY_MIN * PART_DIP_GM
STRESS_FLOOR_TOL = STRESS_DECAY_GM * PART_DIP_GM * 1.5 + 1e-4
UNHAPPY_FLOOR_TOL = 0.01
U_TARGET_TOL = 1e-4
ONSET_LO_FRAC = 0.8
ONSET_SLACK_S = 3.0
LAPSE_GM = 2.5                           # two minute events at speed 1 after the write (x48's BERI_GM)
PART_RISE_EPS = 0.01
DECAY_GM_TOL = L49.DECAY_GM_TOL          # 0.05
DECAY_MIN_N = L49.DECAY_MIN_N            # 5
PART_ZERO = 0.01
EASE_MIN = 0.1
END_FALL_EPS = 1e-4
END_EASED_LEVEL_MAX = 2                  # P2's Endurance 3 eased by one level at least: x493's climb (T91.22, about
                                         # 0.0066 a game minute) lifts 0.125 over 0.25 in about 19 game minutes
STRESS_RISE_EPS = 1e-4
STRESS_DECAY_TOL = 0.15
REL_U_MIN_FALL = 1.0
UNHAPPY_DROP_TOL = 1.0                   # vanilla's own rise over two game minutes (#3016: 0.09 a game minute at Stress 2;
                                         # the BORED term at most 0.18) with room

# ---- the ring (32 paths, the harness's cap)
OPT_PACE, OPT_COMBINE, OPT_DAYMIN = L48.OPT_PACE, L48.OPT_COMBINE, L48.OPT_DAYMIN
SB_SEVERITY = "_G.SandboxVars.NR.Severity"
POLLED_SEVERITY = "_G.NutritionRevamp.server.options.severity"
RING = ("drain.active", "drain.mask", "drain.recovering", "drain.target", "drain.rate", "drain.frac.1", "drain.frac.3",
        "drain.starveAcute", "drain.starvedH", "drain.fedAgeH", "drain.pS", "drain.bmi0",
        "satiety.M", "nutrients.thiamine.p", "nutrients.thiamine.g",
        "effects.enduranceCap", "effects.symCap", "effects.rowEndCap", "effects.stressFloor", "effects.unhappyFloor",
        "effects.stressTarget", "effects.unhappyTarget", "effects.pain.7", "effects.pain.13", "effects.pain.14",
        "effects.painOn", "moodLast.u",
        OPT_PACE, OPT_COMBINE, OPT_DAYMIN, SB_SEVERITY, POLLED_SEVERITY)
H1_NIL_OK = ("drain.frac.1", "drain.frac.3")
F1, F3 = L48.F1, L48.F3
MASK_STARVE = 1
MASK_BERI = 4

# ---- the harness and the probe
LUA_DIR = G.LUA_DIR
HARNESS_FILES = L48.HARNESS_FILES
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": tuple(f'TK.register("{c}", function(' for c in (
        "minute.ring", "stats.all", "stats.setany", "health.get", "witness.chain", "record.set", "nutrition.get",
        "bodypart.get", "players")) + ("function TK.TMH.sampleHealth(row, R)",),
    "PZTestKit_Core.lua": tuple(f'TK.register("{c}", function(' for c in ("time.snapshot", "lua.read", "lua.global",
                                                                         "lua.call")),
}
PROBE_MARKERS = L49.PROBE_MARKERS
ECHO_RX = G.ECHO_RX
NEVER_RX = G.NEVER_RX
LOG_RX = re.compile(r"NutritionRevamp|NR_|TKX_Symptoms|LuaError|STACK TRACE|lua error|attempted index|tried to call nil",
                    re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|TKX_Symptoms_\w+\.lua|failed:|STACK TRACE|attempted index|"
                        r"tried to call nil")

ARM_NAMES = ("ON", "P1", "B", "P2", "L1", "L2")
HOLD_ARMS = ("P1", "B", "P2")
END_ARMS = ("ON", "P1", "B", "P2")
PART_ARMS = ("ON", "P1", "B", "P2")
PAIN_LEVEL_ARMS = ("P1", "B", "P2", "L2")
FOLLOW_ARMS = ("ON", "P1", "B", "P2", "L1")

CONSTANTS = {k: v for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and isinstance(v, (int, float, str, bool, tuple, dict)) and k not in ("REPO", "HERE")}
CONSTANTS = {k: (v.pattern if hasattr(v, "pattern") else v) for k, v in CONSTANTS.items()}
CONSTANTS["LOG_RX"], CONSTANTS["MOD_ERR_RX"] = LOG_RX.pattern, MOD_ERR_RX.pattern

num = X.num
g = L49.g
vals = G.vals
level_of = L49.level_of
near_threshold = L49.near_threshold
ring_age = L48.ring_age
first_index = L48.first_index
same = L48.same


def load_prerun(path=None):
    return L48.load_prerun(path or os.path.join(REPO, PRERUN_FILE))


def dip_gm(day_min=DAY_MIN):
    """Added pain's fall a game minute: 0.005 a multiplier unit, 2 x dayMin units a game minute (J3, #2922)."""
    return DIP_PER_GM_UNIT * day_min


def has_bit(mask, bit):
    m = num(mask)
    return m is not None and (int(round(m)) & bit) == bit


# ================================================================ the effects in force (pure)
def pain_targets(row):
    """{part: added-pain target} of a replay or ring row for PAIN_PARTS (0 when absent)."""
    return {i: (num((row or {}).get(f"effects.pain.{i}")) or 0.0) for i in PAIN_PARTS}


def pain_sum(row, injury=2, minus=0.0):
    """inj x sum(mod x max(0, target - minus)) over the row's painful parts: vanilla's PAIN target (#2362) of parts
    held `minus` under their targets."""
    f = L49.INJURY_FACTOR.get(injury, 1.0)
    return f * sum(PAIN_MOD[i] * max(0.0, t - minus) for i, t in pain_targets(row).items() if t > 0)


def pain_mid(row, day_min=DAY_MIN, injury=2):
    """The PAIN a held set of parts sits at between writes: their targets less half a minute's dip."""
    return pain_sum(row, injury, dip_gm(day_min) / 2.0)


class InForce:
    """The replay rows in force at a world age: ring row s, the last read at or before it, holds drain s - 1's state
    (the replay row labelled s); a few ticks after the event drain s ran (the row labelled s + 1). at(a) returns the
    two (the second None at the end), or (None, None) before the first ring row."""

    def __init__(self, ring, rep):
        self.ring = [(ring_age(r), r["s"]) for r in ring if ring_age(r) is not None and r.get("s") is not None]
        self.ring.sort()
        self.rep = {r.get("s"): r for r in rep or [] if r.get("s") is not None}

    def at(self, a):
        a = num(a)
        if a is None:
            return None, None
        s = None
        for age, rs in self.ring:
            if age <= a + 1e-12:
                s = rs
            else:
                break
        if s is None:
            return None, None
        return self.rep.get(s), self.rep.get(s + 1)

    def both(self, a, field):
        """The field's value in the two rows in force (the second may be None)."""
        r0, r1 = self.at(a)
        v0 = num((r0 or {}).get(field)) if r0 is not None else None
        v1 = num((r1 or {}).get(field)) if r1 is not None else None
        return v0, v1

    def hi(self, a, field):
        vs = [v for v in self.both(a, field) if v is not None]
        return max(vs) if vs else None

    def lo(self, a, field):
        vs = [v for v in self.both(a, field) if v is not None]
        return min(vs) if vs else None

    def one_level(self, a, kind, fn):
        """The level both rows in force give fn(row) (None when they differ or a row is missing)."""
        r0, r1 = self.at(a)
        rows = [r for r in (r0, r1) if r is not None]
        if not rows:
            return None, None
        vals_ = [fn(r) for r in rows]
        if any(v is None for v in vals_):
            return None, vals_
        lv = {level_of(kind, v) for v in vals_}
        return (lv.pop() if len(lv) == 1 else None), vals_


def pair_age(p):
    return num(g(p, "s", "age"))


def arm_pairs(pairs, arms):
    arms = (arms,) if isinstance(arms, str) else tuple(arms)
    return [p for p in pairs if p.get("valid") and p.get("arm") in arms]


def server_hz(pairs):
    """Server ticks a second over the valid pairs: the median of the snapshot's tick count over its ms."""
    rates, prev = [], None
    for p in pairs:
        if not p.get("valid"):
            continue
        if prev is not None:
            n0, n1 = num(g(prev, "s", "n")), num(g(p, "s", "n"))
            m0, m1 = num(g(prev, "s", "ms")), num(g(p, "s", "ms"))
            if None not in (n0, n1, m0, m1) and n1 > n0 and m1 > m0:
                rates.append((n1 - n0) / ((m1 - m0) / 1000.0))
        prev = p
    return statistics.median(rates) if rates else None


def place_progress(rows, p, a_before):
    """The s of the drain that first ran on a drain.pS write of p: the ring row before the first row read from
    a_before on whose frac.1 reads 1 - p (that row holds the drain's output); None when no such row."""
    if p is None or a_before is None:
        return None
    for i in range(1, len(rows)):
        a, f = ring_age(rows[i]), num(rows[i].get(F1))
        if a is not None and a >= a_before - 1.0 / 60.0 and f is not None and abs(f - (1.0 - p)) <= 1e-9:
            return rows[i]["s"] - 1                        # right across a ring gap too (F6)
    return None


# ================================================================ the preconditions (pure)
def grade_opt(rows, prof):
    """OPT: the first ring row's K.drain.OPT pace, combine and dayMin, the sandbox's and the polled Severity."""
    if not rows:
        return "unmeasured", {"why": "no ring row"}
    r = rows[0]
    want = {OPT_PACE: prof["pace"], OPT_COMBINE: prof["combine"], OPT_DAYMIN: DAY_MIN, SB_SEVERITY: prof["severity"],
            POLLED_SEVERITY: prof["severity"]}
    got = {k: r.get(k) for k in want}
    off = {k: (got[k], v) for k, v in want.items() if not same(got[k], v)}
    return ("falsified" if off else "as_predicted"), {"s": r.get("s"), "read": got, "off": off}


def grade_z(log_errors, parked, probe_errors):
    """Z: x49's over the mod's and the probe's error lines."""
    v, obs, _ = L49.grade_z(log_errors, parked, probe_errors)
    return v, obs


# ================================================================ pain (pure)
def part_band(target, day_min=DAY_MIN):
    return target - dip_gm(day_min) * PART_DIP_GM - PART_TOL, target + PART_TOL


def grade_part(pairs, inf, arm_reads, arms=PART_ARMS, day_min=DAY_MIN):
    """PAIN_PART: the server's Torso_Lower added pain inside its band on every valid pair of `arms` while both rows
    in force set it; each arm-end read of every painful part inside its band (arm_reads: {arm: {age, parts: {i: v}}})."""
    used, bad = [], []
    for p in arm_pairs(pairs, arms):
        a, v = pair_age(p), num(g(p, "s", "part"))
        t0, t1 = inf.both(a, f"effects.pain.{TORSO}")
        if v is None or t0 is None or not (t0 > 0) or (t1 is not None and not (t1 > 0)):
            continue
        lo, hi = part_band(min(x for x in (t0, t1) if x is not None), day_min)[0], \
            part_band(max(x for x in (t0, t1) if x is not None), day_min)[1]
        row = {"tag": p.get("tag"), "part": TORSO, "v": v, "lo": lo, "hi": hi}
        used.append(row)
        if not lo <= v <= hi:
            bad.append(row)
    ends = []
    for arm, rd in (arm_reads or {}).items():
        a = num((rd or {}).get("age"))
        for i, v in ((rd or {}).get("parts") or {}).items():
            i, v = int(i), num(v)
            t0, t1 = inf.both(a, f"effects.pain.{i}")
            if v is None or t0 is None or not (t0 > 0) or (t1 is not None and not (t1 > 0)):
                continue
            lo = part_band(min(x for x in (t0, t1) if x is not None), day_min)[0]
            hi = part_band(max(x for x in (t0, t1) if x is not None), day_min)[1]
            row = {"arm": arm, "part": i, "v": v, "lo": lo, "hi": hi}
            ends.append(row)
            if not lo <= v <= hi:
                bad.append(row)
    obs = {"n_pairs": len(used), "n_ends": len(ends), "ends": ends, "off": bad[:20],
           "band": f"[target - {dip_gm(day_min)} x {PART_DIP_GM} - {PART_TOL}, target + {PART_TOL}]"}
    if not used or not ends:
        obs["why"] = "no pair or no arm-end read with a lower-torso target set"
        return "unmeasured", obs, used + ends
    return ("as_predicted" if not bad else "falsified"), obs, used + ends


def grade_pain_target(pairs, arm, inf, day_min=DAY_MIN, injury=2, short=()):
    """PAIN_TARGET at one arm: the server's PAIN at its last valid pair inside [TARGET_MIN_FRAC x pain_sum(target -
    DIP), pain_sum(target) + TARGET_TOL], both rows in force; unmeasured under TARGET_HZ_MIN ticks a second, or when
    the budget shortened the arm (in short, F5: the approach is timed on the full arm)."""
    if arm in short:
        return "unmeasured", {"arm": arm, "why": "arm shortened by the budget"}, []
    vp = arm_pairs(pairs, arm)
    if not vp:
        return "unmeasured", {"arm": arm, "why": "no valid pair"}, []
    p = vp[-1]
    a, pain = pair_age(p), num(g(p, "s", "pain"))
    r0, r1 = inf.at(a)
    rows = [r for r in (r0, r1) if r is not None]
    hz = server_hz(vp)
    obs = {"arm": arm, "tag": p.get("tag"), "pain": pain, "hz": hz}
    if not rows or pain is None:
        obs["why"] = "no row in force or no PAIN read"
        return "unmeasured", obs, []
    lo = TARGET_MIN_FRAC * min(pain_sum(r, injury, dip_gm(day_min)) for r in rows)
    hi = max(pain_sum(r, injury) for r in rows) + TARGET_TOL
    obs.update({"lo": lo, "hi": hi})
    if not hi > TARGET_TOL:
        obs["why"] = "no painful part in force"
        return "unmeasured", obs, []
    if hz is None or hz < TARGET_HZ_MIN:
        obs["why"] = f"server tick rate {hz} a second, under {TARGET_HZ_MIN} or unread"
        return "unmeasured", obs, []
    return ("as_predicted" if lo <= pain <= hi else "falsified"), obs, [pain]


def onset_window(t_mid, side, hz=TICK_HZ_NOM, fps=CLIENT_FPS_NOM):
    """(lo, hi) wall seconds from the onset's drain to the first Pain level 1 read on `side` ("s" or "c"): the
    1/RISE_DIV-a-tick approach from 0 past 10 at the mid PAIN t_mid at hz server ticks a second, then the moodle timer
    (PAIN_TIMER_UPDATES server ticks, or client frames at fps), the pair spacing and the slack."""
    if t_mid is None or not t_mid > L49.PAIN_TH[0] or not hz or (side == "c" and not fps):
        return None
    ticks = math.log(t_mid / (t_mid - L49.PAIN_TH[0])) / -math.log(1.0 - 1.0 / RISE_DIV)
    approach = ticks / hz
    timer = PAIN_TIMER_UPDATES / (hz if side == "s" else fps)
    return ONSET_LO_FRAC * approach - PAIR_EVERY_S, approach + timer + PAIR_EVERY_S + ONSET_SLACK_S


def grade_pain_onset(pairs, set_after, set_before, t_mid, arms=("ON", "P1")):
    """PAIN_ONSET (driver review F1): the onset's drain lies in (set_after, set_before) wall seconds. Per side, over
    its reads after set_after in order: the first level-1 read i1 and the read before it (set_after when none) bracket
    the moodle's change; early when the level-1 read less set_before is under the window's lo, late when the last
    level-0 read less set_after is over its hi (a gap between reads never falsifies). The window is at the measured
    server tick rate and client frame rate over `arms`; unmeasured under TARGET_HZ_MIN ticks a second, the client side
    unmeasured under L49.CLIENT_FPS_MIN frames; a side with no level-1 read is falsified only once its last read is
    past hi."""
    hz = server_hz(arm_pairs(pairs, arms))
    fps = L49.client_rate(pairs, arms)
    obs = {"set_after": set_after, "set_before": set_before, "t_mid": t_mid, "hz": hz, "fps": fps, "sides": {}}
    if set_after is None or set_before is None or t_mid is None:
        obs["why"] = "the onset's wall bracket or its mid PAIN unread"
        return "unmeasured", obs, []
    if hz is None or hz < TARGET_HZ_MIN:
        obs["why"] = f"server tick rate {hz} a second, under {TARGET_HZ_MIN} or unread"
        return "unmeasured", obs, []
    used, bad = [], []
    for side, wk in (("s", "ws"), ("c", "wc")):
        o = {}
        obs["sides"][side] = o
        if side == "c" and (fps is None or fps < L49.CLIENT_FPS_MIN):
            o["why"] = f"unmeasured: client frame rate {fps} a second, under {L49.CLIENT_FPS_MIN} or unread"
            continue
        win = onset_window(t_mid, side, hz, fps)
        o["window"] = win
        seq = [p for p in pairs if p.get("arm") in ARM_NAMES and num(g(p, side, "lvPain")) is not None
               and num(p.get(wk)) is not None and num(p.get(wk)) > set_after]
        i1 = next((i for i, p in enumerate(seq) if num(g(p, side, "lvPain")) >= 1), None)
        if i1 is None:
            last = num(seq[-1][wk]) if seq else None
            o["why"] = "no level-1 read"
            if last is not None and last - set_after > win[1]:
                bad.append(side)
            continue
        last0 = num(seq[i1 - 1][wk]) if i1 else set_after
        first = num(seq[i1][wk])
        o.update({"tag": seq[i1].get("tag"), "bracket": [last0 - set_after, first - set_before]})
        o["early"] = first - set_before < win[0]
        o["late"] = last0 - set_after > win[1]
        used.append(o)
        if o["early"] or o["late"]:
            bad.append(side)
    if bad:
        return "falsified", obs, used
    if not used:
        return "unmeasured", obs, []
    return "as_predicted", obs, used


def arm_level_want(pairs, arm, inf, kind, fn):
    """The level the rows in force at the arm's last valid pair give fn (None when they differ, no pair, or the value
    sits within the kind's follow epsilon of a threshold), with its reading."""
    vp = arm_pairs(pairs, arm)
    if not vp:
        return None, {"arm": arm, "why": "no valid pair"}
    lv, vs = inf.one_level(pair_age(vp[-1]), kind, fn)
    o = {"arm": arm, "values": vs, "want": lv}
    if lv is None:
        o["why"] = "the rows in force give no one level"
        return None, o
    if any(near_threshold(kind, v, FOLLOW_EPS_LEVEL[kind]) for v in vs):
        o["why"] = "the predicted value sits within the follow epsilon of a threshold"
        return None, o
    return lv, o


def grade_pain_levels(pairs, inf, day_min=DAY_MIN, injury=2, arms=PAIN_LEVEL_ARMS, short=()):
    """PAIN_LEVELS: each arm's last STEADY_N valid pairs read, on both sides, the Pain level of the mid PAIN of the
    replay's targets in force; an arm the budget shortened (in short) reads unmeasured (F5)."""
    parts, results = {}, []
    for arm in arms:
        if arm in short:
            parts[arm] = {"arm": arm, "why": "arm shortened by the budget"}
            results.append(("unmeasured", parts[arm], []))
            continue
        want, o = arm_level_want(pairs, arm, inf, "pain", lambda r: pain_mid(r, day_min, injury))
        if want is None:
            parts[arm] = o
            results.append(("unmeasured", o, []))
            continue
        v, so, samples = L49.grade_steady(pairs, arm, "lvPain", want)
        so.update({"predicted": o})
        parts[arm] = so
        results.append((v, so, samples))
    v, _, samples = L49.combine(results)
    return v, parts, samples


def grade_pain_follows(pairs):
    """PAIN_FOLLOWS: x49's P1_FOLLOWS over FOLLOW_ARMS."""
    return L49.grade_follows(pairs, FOLLOW_ARMS, "pain", "pain", "lvPain", FOLLOW_EPS)


# ================================================================ endurance and the floors (pure)
def grade_end_cap(pairs, inf, arms=ARM_NAMES):
    """END_CAP: every valid pair's server ENDURANCE at or under the larger cap in force plus END_CLIMB_TOL."""
    used, bad = [], []
    for p in arm_pairs(pairs, arms):
        a, e = pair_age(p), num(g(p, "s", "endurance"))
        cap = inf.hi(a, "effects.enduranceCap")
        if e is None or cap is None:
            continue
        row = {"tag": p.get("tag"), "endurance": e, "cap": cap}
        used.append(row)
        if e > cap + END_CLIMB_TOL + 1e-9:
            bad.append(row)
    obs = {"n": len(used), "tol": END_CLIMB_TOL, "off": bad[:20]}
    if not used:
        obs["why"] = "no valid pair with a cap in force"
        return "unmeasured", obs, used
    return ("as_predicted" if not bad else "falsified"), obs, used


def grade_held_levels(pairs, inf, arm_trk, lv_key, kind, fn, arms=HOLD_ARMS):
    """END_LEVELS, STRESS_LEVELS, UNHAPPY_LEVELS: every valid pair of each arm and both trackers read the level the
    rows in force give fn (x49's grade_hold_level)."""
    parts, results = {}, []
    for arm in arms:
        want, o = arm_level_want(pairs, arm, inf, kind, fn)
        if want is None:
            parts[arm] = o
            results.append(("unmeasured", o, []))
            continue
        trk = (arm_trk or {}).get(arm) or {}
        v, ho, samples = L49.grade_hold_level(pairs, arm, lv_key, want, trk.get("server"), trk.get("client"))
        ho.update({"predicted": o})
        parts[arm] = ho
        results.append((v, ho, samples))
    v, _, samples = L49.combine(results)
    return v, parts, samples


def grade_stress_floor(pairs, inf, arms=HOLD_ARMS):
    """STRESS_FLOOR: every valid pair's server STRESS at or over the smaller floor in force less STRESS_FLOOR_TOL."""
    used, bad = [], []
    for p in arm_pairs(pairs, arms):
        a, v = pair_age(p), num(g(p, "s", "stress"))
        fl = inf.lo(a, "effects.stressFloor")
        if v is None or fl is None or not fl > 0:
            continue
        row = {"tag": p.get("tag"), "stress": v, "floor": fl}
        used.append(row)
        if v < fl - STRESS_FLOOR_TOL:
            bad.append(row)
    obs = {"n": len(used), "tol": STRESS_FLOOR_TOL, "off": bad[:20]}
    if not used:
        obs["why"] = "no valid pair with a floor in force"
        return "unmeasured", obs, used
    return ("as_predicted" if not bad else "falsified"), obs, used


def grade_unhappy_floor(pairs, inf, rows, spans, arms=HOLD_ARMS):
    """UNHAPPY_FLOOR: every valid pair's server UNHAPPINESS at or over the smaller floor in force less
    UNHAPPY_FLOOR_TOL, and every ring row inside the arms' spans ({arm: (a0, a1)}) reads moodLast.u at or over its
    effects.unhappyFloor less U_TARGET_TOL."""
    used, bad, rbad, rn = [], [], [], 0
    for p in arm_pairs(pairs, arms):
        a, v = pair_age(p), num(g(p, "s", "unhappy"))
        fl = inf.lo(a, "effects.unhappyFloor")
        if v is None or fl is None or not fl > 0:
            continue
        row = {"tag": p.get("tag"), "unhappy": v, "floor": fl}
        used.append(row)
        if v < fl - UNHAPPY_FLOOR_TOL:
            bad.append(row)
    for arm in arms:
        a0, a1 = (spans or {}).get(arm) or (None, None)
        if a0 is None or a1 is None:
            continue
        for r in rows:
            a = ring_age(r)
            u, fl = num(r.get("moodLast.u")), num(r.get("effects.unhappyFloor"))
            if a is None or not a0 <= a <= a1 or u is None or fl is None or not fl > 0:
                continue
            rn += 1
            if u < fl - U_TARGET_TOL:
                rbad.append({"s": r.get("s"), "moodLast.u": u, "floor": fl})
    obs = {"n": len(used), "ring_rows": rn, "tol": UNHAPPY_FLOOR_TOL, "off": bad[:20], "ring_off": rbad[:20]}
    if bad or rbad:
        return "falsified", obs, used
    if not used or not rn:
        obs["why"] = "no valid pair or no ring row with a floor in force"
        return "unmeasured", obs, used
    return "as_predicted", obs, used


# ================================================================ the release (pure)
def lapse_index(rows, a_snack):
    """The first ring row after the snack's write whose mask has starvation out and beriberi in."""
    if a_snack is None:
        return None
    return first_index(rows, lambda r: (ring_age(r) or -1) > a_snack and num(r.get("drain.mask")) is not None
                       and not has_bit(r.get("drain.mask"), MASK_STARVE) and has_bit(r.get("drain.mask"), MASK_BERI))


def grade_lapse(rows, a_snack):
    """REL_LAPSE (precondition): the lapse row within LAPSE_GM game minutes of the snack's write."""
    if a_snack is None or not rows:
        return "unmeasured", {"why": "no snack write or no ring row"}
    i = lapse_index(rows, a_snack)
    obs = {"snack_age": a_snack, "s": None if i is None else rows[i]["s"]}
    if i is None:
        late = (ring_age(rows[-1]) or 0) > a_snack + LAPSE_GM / 60.0
        obs["why"] = "no row with starvation out of the mask and beriberi in it"
        return ("falsified" if late else "unmeasured"), obs
    r = rows[i]
    obs.update({"age": ring_age(r), "lag_gm": (ring_age(r) - a_snack) * 60.0, "mask": r.get("drain.mask"),
                "recovering": r.get("drain.recovering"), "frac1": r.get(F1)})
    return ("as_predicted" if obs["lag_gm"] <= LAPSE_GM else "falsified"), obs


def after_pairs(pairs, a0, arms=("L1", "L2")):
    return [p for p in arm_pairs(pairs, arms) if pair_age(p) is not None and pair_age(p) > a0]


def grade_rel_pain(pairs, a_lapse, day_min=DAY_MIN):
    """REL_PAIN: after the lapse row (plus one game minute) the Torso_Lower added pain never rises by more than
    PART_RISE_EPS between valid pairs, falls DIP a game minute within DECAY_GM_TOL over at least DECAY_MIN_N gaps with
    both ends above 0, and its last read sits at the decay's own end, max(0, the first read - DIP x the game minutes
    between), within PART_TOL plus DECAY_GM_TOL of the fall (so an arm the budget shortened is graded at its own end,
    driver review F5)."""
    if a_lapse is None:
        return "unmeasured", {"why": "no lapse row"}, []
    ps = [p for p in after_pairs(pairs, a_lapse + 1.0 / 60.0) if num(g(p, "s", "part")) is not None]
    rises, fall, gm, n = [], 0.0, 0.0, 0
    for a, b in zip(ps, ps[1:]):
        va, vb = num(g(a, "s", "part")), num(g(b, "s", "part"))
        if vb > va + PART_RISE_EPS:
            rises.append({"tag": b.get("tag"), "from": va, "to": vb})
        if va > 0 and vb > 0 and pair_age(b) > pair_age(a):
            fall += va - vb
            gm += (pair_age(b) - pair_age(a)) * 60.0
            n += 1
    want = dip_gm(day_min)
    end = num(g(ps[-1], "s", "part")) if ps else None
    obs = {"n_pairs": len(ps), "n_gaps": n, "rises": rises[:10], "end": end, "want_gm": want}
    if n < DECAY_MIN_N or end is None:
        obs["why"] = f"fewer than {DECAY_MIN_N} decay gaps or no pair"
        return ("falsified" if rises else "unmeasured"), obs, []
    v0 = num(g(ps[0], "s", "part"))
    end_want = max(0.0, v0 - want * (pair_age(ps[-1]) - pair_age(ps[0])) * 60.0)
    obs.update({"end_want": end_want, "end_tol": PART_TOL + DECAY_GM_TOL * (v0 - end_want)})
    obs["per_gm"] = fall / gm if gm > 0 else None
    obs["rel"] = (obs["per_gm"] / want - 1.0) if obs["per_gm"] is not None else None
    ok = (not rises and obs["rel"] is not None and abs(obs["rel"]) <= DECAY_GM_TOL
          and abs(end - end_want) <= obs["end_tol"])
    return ("as_predicted" if ok else "falsified"), obs, [obs["per_gm"]]


def grade_rel_end(pairs, inf, a_lapse, cap_before, short=False):
    """REL_END: the cap in force at L2's last pair above cap_before (P2's) by EASE_MIN; no pull-down after the lapse;
    L2's last STEADY_N pairs read their own ENDURANCE's level, at most END_EASED_LEVEL_MAX, on both sides, a sample
    within L49.FOLLOW_EPS_END of an edge skipped (a moodle a tick behind its stat, F4) and at least LEVEL_MIN_PAIRS
    samples a side graded. An L2 the budget shortened (short) leaves the level bound unmeasured (F5)."""
    obs = {"cap_before": cap_before, "short": short}
    l2 = arm_pairs(pairs, "L2")
    if a_lapse is None or not l2 or cap_before is None:
        obs["why"] = "no lapse row, no L2 pair or no P2 cap"
        return "unmeasured", obs, []
    cap_after = inf.lo(pair_age(l2[-1]), "effects.enduranceCap")
    obs["cap_after"] = cap_after
    ps = after_pairs(pairs, a_lapse)
    falls = []
    for a, b in zip(ps, ps[1:]):
        ea, eb = num(g(a, "s", "endurance")), num(g(b, "s", "endurance"))
        if ea is not None and eb is not None and eb < ea - END_FALL_EPS:
            falls.append({"tag": b.get("tag"), "from": ea, "to": eb})
    last = l2[-STEADY_N:]
    lv, n_side = [], {"s": 0, "c": 0}
    for p in last:
        for side in ("s", "c"):
            e, got = num(g(p, side, "endurance")), g(p, side, "lvEnd")
            if e is None or near_threshold("endurance", e, L49.FOLLOW_EPS_END):
                continue
            n_side[side] += 1
            lv.append({"tag": p.get("tag"), "side": side, "endurance": e, "got": got,
                       "want": level_of("endurance", e)})
    lv_bad = [x for x in lv if x["got"] != x["want"] or x["got"] is None or x["got"] > END_EASED_LEVEL_MAX]
    ages = [pair_age(p) for p in ps if pair_age(p) is not None]
    climb = None
    if len(ps) >= 2 and ages[-1] > ages[0]:
        e0, e1 = num(g(ps[0], "s", "endurance")), num(g(ps[-1], "s", "endurance"))
        if e0 is not None and e1 is not None:
            climb = (e1 - e0) / ((ages[-1] - ages[0]) * 60.0)
    obs.update({"n_pairs": len(ps), "falls": falls[:10], "levels": lv, "graded_a_side": n_side,
                "off_levels": lv_bad[:10], "climb_gm": climb})
    if cap_after is None:
        obs["why"] = "no cap in force at L2's end"
        return "unmeasured", obs, []
    if cap_after < cap_before + EASE_MIN or falls:
        return "falsified", obs, ps
    if short:
        obs["why"] = "L2 shortened by the budget: the level bound is unmeasured"
        return "unmeasured", obs, []
    if min(n_side.values()) < LEVEL_MIN_PAIRS:
        obs["why"] = f"fewer than {LEVEL_MIN_PAIRS} level samples a side away from an edge"
        return "unmeasured", obs, []
    return ("falsified" if lv_bad else "as_predicted"), obs, ps


def grade_rel_heal(rows, i_lapse, rep=None):
    """REL_HEAL (driver review F2), on the ring rows after the lapse row: every row's health at or under its own
    drain.target plus REL_HEAL_TOL, none under the row before by more than REL_HEAL_TOL (no drain take), the last within
    REL_HEAL_TOL of its target; unmeasured until the ring reaches REL_HEAL_MIN_GM game minutes past the lapse row. The
    replay's health beside the live value on each row is a reading (its uniform heal leads the live one)."""
    if i_lapse is None:
        return "unmeasured", {"why": "no lapse row"}, []
    span = [r for r in rows[i_lapse + 1:] if num(r.get("health")) is not None and num(r.get("drain.target")) is not None]
    rep_h = {r.get("s"): num(r.get("health")) for r in rep or []}
    obs = {"n": len(span), "lag": [{"s": r.get("s"), "live": num(r["health"]), "replay": rep_h.get(r.get("s"))}
                                   for r in span[::5]][:40]}
    over = [{"s": r.get("s"), "health": num(r["health"]), "target": num(r["drain.target"])} for r in span
            if num(r["health"]) > num(r["drain.target"]) + REL_HEAL_TOL]
    falls = [{"s": b.get("s"), "from": num(a["health"]), "to": num(b["health"])} for a, b in zip(span, span[1:])
             if num(b["health"]) < num(a["health"]) - REL_HEAL_TOL]
    obs.update({"over": over[:10], "falls": falls[:10]})
    if over or falls:
        return "falsified", obs, span
    a0 = ring_age(rows[i_lapse])
    if not span or a0 is None or (ring_age(span[-1]) - a0) * 60.0 < REL_HEAL_MIN_GM:
        obs["why"] = f"the ring ends under {REL_HEAL_MIN_GM} game minutes past the lapse row"
        return "unmeasured", obs, []
    last = span[-1]
    obs["last_gap"] = num(last["drain.target"]) - num(last["health"])
    return ("as_predicted" if abs(obs["last_gap"]) <= REL_HEAL_TOL else "falsified"), obs, span


def replay_verdict(results):
    """REPLAY_ over the pre-lapse and post-lapse diffs: falsified if either is, as_predicted if either is (a span may hold
    no row), else unmeasured; the observed values of both kept."""
    vs = [v for v, _ in results]
    obs = {"spans": [o for _, o in results]}
    if "falsified" in vs:
        return "falsified", obs
    return ("as_predicted" if "as_predicted" in vs else "unmeasured"), obs


def release_step(rows, a_snack):
    """The ring rows (before, at) of the release: the first row after the snack's write whose moodLast.u fell from the
    row before by REL_U_MIN_FALL or more; (None, None) when none."""
    if a_snack is None:
        return None, None
    for i in range(1, len(rows)):
        a = ring_age(rows[i])
        u0, u1 = num(rows[i - 1].get("moodLast.u")), num(rows[i].get("moodLast.u"))
        if a is not None and a > a_snack and u0 is not None and u1 is not None and u0 - u1 >= REL_U_MIN_FALL:
            return rows[i - 1], rows[i]
    return None, None


def grade_rel_unhappy(rows, pairs, a_snack):
    """REL_UNHAPPY: at the release step UNHAPPINESS within UNHAPPY_DROP_TOL of the row before's less the remembered
    target's fall; L1's last STEADY_N valid pairs read Unhappy 0 on both sides."""
    r0, r1 = release_step(rows, a_snack)
    obs = {"snack_age": a_snack}
    if r0 is None:
        late = rows and (ring_age(rows[-1]) or 0) > (a_snack or 0) + LAPSE_GM / 60.0
        obs["why"] = "no row whose remembered UNHAPPINESS target fell"
        return ("falsified" if late and a_snack is not None else "unmeasured"), obs, []
    u0, u1 = num(r0.get("UNHAPPINESS")), num(r1.get("UNHAPPINESS"))
    fall = num(r0.get("moodLast.u")) - num(r1.get("moodLast.u"))
    obs.update({"s": r1.get("s"), "fall": fall, "unhappy_before": u0, "unhappy_after": u1})
    if u0 is None or u1 is None:
        obs["why"] = "UNHAPPINESS unread on the ring"
        return "unmeasured", obs, []
    want = max(0.0, u0 - fall)
    obs["want"] = want
    step_ok = abs(u1 - want) <= UNHAPPY_DROP_TOL
    v, so, samples = L49.grade_steady(pairs, "L1", "lvUnhappy", 0)
    obs["l1"] = so
    if v == "unmeasured":
        return "unmeasured", obs, []
    return ("as_predicted" if step_ok and v == "as_predicted" else "falsified"), obs, samples


def grade_rel_stress(pairs, a_lapse, floor_before, short=False):
    """REL_STRESS: after the lapse row no rise over STRESS_RISE_EPS between valid pairs; the fall a game minute within
    STRESS_DECAY_TOL of STRESS_DECAY_GM over at least DECAY_MIN_N gaps; L2's last STEADY_N pairs at the Stress level of
    floor_before less STRESS_DECAY_GM a game minute since the lapse, on both sides, a pair whose predicted value sits
    within STRESS_FLOOR_TOL + L49.FOLLOW_EPS_STRESS of a threshold skipped (F7). An L2 the budget shortened (short)
    leaves the levels unmeasured (F5)."""
    obs = {"floor_before": floor_before, "short": short}
    if a_lapse is None or floor_before is None:
        obs["why"] = "no lapse row or no P2 floor"
        return "unmeasured", obs, []
    ps = [p for p in after_pairs(pairs, a_lapse) if num(g(p, "s", "stress")) is not None]
    rises, fall, gm, n = [], 0.0, 0.0, 0
    for a, b in zip(ps, ps[1:]):
        va, vb = num(g(a, "s", "stress")), num(g(b, "s", "stress"))
        if vb > va + STRESS_RISE_EPS:
            rises.append({"tag": b.get("tag"), "from": va, "to": vb})
        if vb > 0 and pair_age(b) > pair_age(a):
            fall += va - vb
            gm += (pair_age(b) - pair_age(a)) * 60.0
            n += 1
    obs.update({"n_pairs": len(ps), "n_gaps": n, "rises": rises[:10], "want_gm": STRESS_DECAY_GM})
    if n < DECAY_MIN_N or gm <= 0:
        obs["why"] = f"fewer than {DECAY_MIN_N} gaps"
        return ("falsified" if rises else "unmeasured"), obs, []
    obs["per_gm"] = fall / gm
    obs["rel"] = obs["per_gm"] / STRESS_DECAY_GM - 1.0
    if rises or abs(obs["rel"]) > STRESS_DECAY_TOL:
        return "falsified", obs, ps
    l2 = arm_pairs(pairs, "L2")[-STEADY_N:]
    if short or len(l2) < STEADY_N:
        obs["why"] = "L2 shortened by the budget or under STEADY_N pairs: the levels are unmeasured"
        return "unmeasured", obs, []
    lv = []
    for p in l2:
        pred = floor_before - STRESS_DECAY_GM * (pair_age(p) - a_lapse) * 60.0
        if near_threshold("stress", pred, STRESS_FLOOR_TOL + L49.FOLLOW_EPS_STRESS):
            continue
        want = level_of("stress", pred)
        for side in ("s", "c"):
            lv.append({"tag": p.get("tag"), "side": side, "got": g(p, side, "lvStress"), "want": want})
    lv_bad = [x for x in lv if x["got"] != x["want"]]
    obs.update({"levels": lv, "off_levels": lv_bad[:10]})
    if not lv:
        obs["why"] = "every L2 pair's prediction sits near a threshold"
        return "unmeasured", obs, []
    return ("falsified" if lv_bad else "as_predicted"), obs, ps


# ================================================================ the pre-boot checks (offline; tested)
def profile_doc_checks(name, doc, text=""):
    """The profile's TOML against PROFILES[name]: its header naming its own file, fixture default, the one admin
    client, sleep off, PZTestKit, the staged copy and the probe by its path, Nutrition false, DayLength 4, the
    [sandbox.NR] block of Mode, DeathPace, HealthCombine and Severity alone at the session's values, the version
    verify rows (the mod and the probe, server and client), the server timeout."""
    spec = PROFILES.get(name)
    if spec is None:
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = doc.get("verify") or []
    nr_rows = sorted(v.get("side") for v in vr if v.get("args") == f"{NR}.version")
    pr_rows = sorted(v.get("side") for v in vr if v.get("args") == f"{PROBE}.version")
    return {"known_profile": True,
            "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
            "fixture": doc.get("fixture") == spec["fixture"],
            "clients": doc.get("clients", [USER]) == spec["clients"],
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods": mods == ["PZTestKit", NR, PROBE],
            "mod_staged": paths.get(NR) == STAGE_MOD,
            "probe_path": paths.get(PROBE) == PROBE_DIR,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == spec["day_length"],
            "nr_block": sb.get("NR") == {"Mode": spec["mode"], "DeathPace": spec["pace"],
                                         "HealthCombine": spec["combine"], "Severity": spec["severity"]},
            "verify_rows": nr_rows == ["client", "server"] and pr_rows == ["client", "server"],
            "no_override": "client_overrides" not in doc,
            "server_timeout": srv.get("timeout") == SERVER_TIMEOUT_S}


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def preboot(key, driver_file, repo=REPO, compute=None):
    """The driver's file names its session (CLAUDE.md s5); no artifact of the prefix committed; the profile's TOML;
    STAGED_FROM mod/'s last commit; the harness and probe markers; the fixture fresh; the prerun current. Returns
    (checks, ok)."""
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
    c["probe_found"], c["probe_markers"] = L49.markers_ok({p: p for p in PROBE_MARKERS}, PROBE_MARKERS, repo)
    fr = L48.fixture_fresh(repo)
    c["fixture"] = fr
    c["fixture_fresh"] = fr["fresh"]
    if c["key"]:
        if compute is None:
            import x49b_prerun as PR
            compute = PR.compute
        pr = L48.prerun_current(key, repo, compute, committed=load_prerun(os.path.join(repo, PRERUN_FILE)))
    else:
        pr = {"ok": False}
    c["prerun"] = pr
    c["prerun_current"] = pr["ok"]
    skip = ("profile_checks", "harness_found", "probe_found", "fixture", "prerun")
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO):
    """x45g_lib's gate at this lib's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


def parse_argv(argv, driver_file):
    return L49.parse_argv(argv, driver_file)


# ================================================================ the session
class Sess(L48.Sess):
    """x494's phases over an xlib.Xs: x48_lib.Sess's plumbing (the record writes, the clock, the ring, W, the
    thiamine), x49_lib.Sess's probe reads (the pairs, the trackers, the errors)."""

    # x49_lib.Sess's probe reads, as they are (their module's PROBE, CLIENT and paths)
    call = L49.Sess.call
    mid = staticmethod(L49.Sess.mid)
    read = L49.Sess.read
    pair = L49.Sess.pair
    hold_pairs = L49.Sess.hold_pairs
    trk = L49.Sess.trk
    trk_reset = L49.Sess.trk_reset
    errors_read = L49.Sess.errors_read

    def __init__(self, xs, key, run_dir=None, prerun=None):
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
        self.pages, self.eats, self.points, self.consts, self.drinks = [], [], [], [], []
        self.pairs = self.out.setdefault("pairs", [])
        self.arms = self.out.setdefault("arms", [])
        self.sets = self.out.setdefault("sets", [])
        self.stat_sets = self.out.setdefault("stat_sets", [])
        self.sandbox = self.out.setdefault("sandbox_writes", [])
        self.polls = self.out.setdefault("death_polls", [])
        self.red0 = None
        self.dead = False
        self.injury = 2
        self.P = prerun if prerun is not None else load_prerun().get(key, {})
        self.out["lib_x49b"] = LIB_FILE
        self.out["constants_x49b"] = dict(CONSTANTS)
        self.out["prerun_x49b"] = self.P

    # -- reads and writes
    def rec_walls(self, tag, paths, log=False):
        """A record read with its wall bracket."""
        a = self.lread(tag, SRV, f"record:{USER}", paths, log=log)
        return vals(a), num(a.get("wall")), num(a.get("wall_after"))

    def stat_seed(self, tag, stat, value):
        """stats.setany <user> <stat> <value>, bracketed by two age reads; logged for the replay's stat events."""
        a0 = self.age(tag + "_a0")
        r = self.k(tag, SRV, "stats.setany", f"{USER} {stat} {value}")
        a1 = self.age(tag + "_a1")
        row = {"tag": tag, "stat": stat, "value": num(value), "age_before": a0, "age": a1,
               "reply": {k: r.get(k) for k in ("ok", "stat", "requested", "before", "after", "reason", "raw")}}
        row["ok"] = r.get("ok") is True
        if not row["ok"]:
            self.xs.note(f"{tag}: stats.setany {stat} {value} answered {r.get('reason') or r.get('raw')!r}")
        self.stat_sets.append(row)
        return row

    def parts_read(self, tag):
        """Every part's added pain on the server, with the age read after it."""
        a = self.k(tag, SRV, "bodypart.get", f"{USER} all")
        rows = a.get("parts") if isinstance(a.get("parts"), list) else []
        parts = {}
        for r in rows:
            if isinstance(r, dict) and num(r.get("index")) is not None:
                parts[str(int(num(r["index"])))] = num(r.get("additionalPain"))
        return {"ok": a.get("ok"), "parts": parts, "age": self.age(tag + "_a"), "raw": a.get("raw")}

    def budget_secs(self, secs):
        """An arm's pairs shortened so CLOSE_RESERVE_S stays for C and R; under LEVEL_MIN_PAIRS pairs' worth left, the
        budget stops the session there (xlib.Budget: the closing phases still run)."""
        left = self.xs.budget_s - CLOSE_RESERVE_S - self.xs.wall()
        if left < PAIR_EVERY_S * LEVEL_MIN_PAIRS:
            raise X.Budget(f"wall {self.xs.wall()} s leaves {left:.1f} s for an arm before the close reserve")
        return min(secs, left)

    def arm(self, name, secs, settle=True):
        """An arm's pairs: (settle) ARM_SETTLE_S, both trackers reset, pairs every PAIR_EVERY_S for secs (budget
        permitting), the trackers read and every part read."""
        rec = {"arm": name, "epoch_ms": int(self.xs.clock() * 1000), "age0": self.age(name + "_age0")}
        self.arms.append(rec)
        if settle:
            self.xs.sleep(ARM_SETTLE_S)
        self.trk_reset(name)
        rec["settled_epoch_ms"] = int(self.xs.clock() * 1000)
        rec["secs_asked"] = secs
        rec["secs_given"] = self.budget_secs(secs)
        rec["pairs"] = self.hold_pairs(name, rec["secs_given"])
        rec["trk"] = self.trk(name)
        rec["parts_end"] = self.parts_read(name + "_parts")
        rec["age1"] = rec["parts_end"]["age"]
        rec["end_epoch_ms"] = int(self.xs.clock() * 1000)
        return rec

    def arm_short(self, name):
        """Whether the budget shortened the arm (F5): given under asked by more than half a second."""
        a = self.arm_rec(name)
        asked, given = num(a.get("secs_asked")), num(a.get("secs_given"))
        return asked is not None and given is not None and given < asked - 0.5

    def seed(self, name, p):
        """The smoothed progress to p at speed 1, polled until the record's stressFloor moves; the floors read off the
        record and STRESS and UNHAPPINESS set to them (THE FLOOR SEED)."""
        P = self.D[name] = {}
        self.set_speed(1, name + "_one")
        P["pre"] = self.rec(name + "_pre", ("drain.pS", "effects.stressFloor", "effects.unhappyFloor",
                                            "effects.enduranceCap"), log=True)
        f0 = num(P["pre"].get("effects.stressFloor")) or 0.0
        P["set"] = self.write(name + "_pS", "drain.pS", f"{p}")

        def fn():
            v = self.rec(name + "_poll", ("drain.pS", "effects.stressFloor"))
            fl = num(v.get("effects.stressFloor"))
            return fl is not None and fl > f0 + 0.01, v
        P["poll"] = self.poll(name + "_floor", fn, FLOOR_CAP_S, POLL_S)
        P["floors"] = self.rec(name + "_floors", ("drain.pS", "effects.stressFloor", "effects.unhappyFloor",
                                                  "effects.enduranceCap", "effects.symCap"), log=True)
        fs, fu = num(P["floors"].get("effects.stressFloor")), num(P["floors"].get("effects.unhappyFloor"))
        if P["poll"]["done"] and fs is not None and fu is not None:
            now, _ = self.read(name + "_stats", SRV, f"{PROBE}.s", ("stress", "unhappy"), log=True)
            P["stats_before_seed"] = now
            s0, u0 = num(now.get("stress")), num(now.get("unhappy"))
            # each stat set to max(its read, the floor): a stat vanilla raised over its floor (BORED and Stress 2 raise
            # UNHAPPINESS, #3016) is never lowered by the seed (driver review F8)
            P["seed_stress"] = self.stat_seed(name + "_stress", "STRESS", repr(max(fs, s0 if s0 is not None else fs)))
            P["seed_unhappy"] = self.stat_seed(name + "_unhappy", "UNHAPPINESS",
                                               repr(max(fu, u0 if u0 is not None else fu)))
        else:
            self.xs.note(f"{name}: the floors never moved; no stat seed")
        return P

    # ======================================================== the phases
    def phase_S(self):
        self.phase_S48()
        P = self.D["S"]
        P["sandbox_x49b"] = self.glob_read("S_sv2", ("SandboxVars.InjurySeverity", "SandboxVars.NR.Severity",
                                                     "SandboxVars.NR.Mode", "SandboxVars.SleepAllowed",
                                                     "SandboxVars.SleepNeeded", "SandboxVars.EndRegen",
                                                     "NutritionRevamp.server.options.severity"), log=True)
        inj = num(P["sandbox_x49b"].get("SandboxVars.InjurySeverity"))
        self.injury = int(inj) if inj is not None and int(inj) in L49.INJURY_FACTOR else 2
        if inj is None or int(inj) != 2:
            self.xs.note(f"S: InjurySeverity read {inj}; the PAIN predictions use the factor of {self.injury}")
        P["watch"] = self.call("S_watch", SRV, "watch", USER)
        P["reset"] = self.call("S_reset", SRV, "reset")
        P["cpart"] = self.call("S_cpart", CLIENT, "cpartSet", TORSO)
        P["parts"] = self.k("S_parts", SRV, "bodypart.get", f"{USER} all")
        P["errors"] = self.errors_read("S")
        self.xs.sleep(1.0)
        P["pair"] = self.pair("S_pair", "S")
        sm, ws = num(g(P["pair"], "s", "ms")), num(P["pair"].get("ws"))
        P["clock_skew_ms"] = (sm - 1000.0 * (self.xs.t0 + ws)) if sm is not None and ws is not None else None

    def phase_H(self):
        P = self.D["H"] = {}
        rec = [p for p in RING if not p.startswith("_G.")]
        P["ring_paths"] = list(RING)
        P["h1_record"] = self.lread("H_h1", SRV, f"record:{USER}", rec + list(G.H1_EXTRA))
        P["h1_globals"] = self.lread("H_h1g", SRV, "_G", [p[3:] for p in RING if p.startswith("_G.")])
        P["ring_start"] = self.ring_start(list(RING))

    def phase_A(self):
        """x484's seed at speed 1; SPEED_FAST until the record reads starveAcute, every poll's wall bracket kept (the
        last false read and the first true read bracket the onset's drain); speed 1."""
        P = self.D["A"] = {}
        self.set_speed(1, "A_one")
        P["pre"] = self.rec("A_pre", ("satiety.M", "drain.fedAgeH", "drain.starveAcute"), log=True)
        P["set_M"] = self.write("A_M", "satiety.M", "0")
        a = self.age("A_a")
        P["set_fed"] = self.write("A_fed", "drain.fedAgeH", f"{a - STARVE_ONSET_H + SEED_LEAD_H:.6f}")
        P["seed_age"] = P["set_fed"]["age"]
        P["fed_after"] = self.rec("A_fed_check", ("satiety.M", "drain.fedAgeH"), log=True)
        self.set_speed(SPEED_FAST, "A_go")
        br = {"false": None, "true": None}

        def fn():
            v, w0, w1 = self.rec_walls("A_poll", ("drain.starveAcute", "drain.active", "effects.painOn"))
            on = v.get("drain.starveAcute") is True
            br["true" if on else "false"] = [w0, w1]
            return on, v
        P["poll"] = self.poll("A_onset", fn, ONSET_CAP_S, POLL_S)
        P["onset_bracket"] = dict(br)
        P["onset_polled_age"] = self.age("A_on") if P["poll"]["done"] else None
        self.set_speed(1, "A_slow")
        P["drain"] = self.rec("A_drain", ("drain.active", "drain.mask", "drain.target", "effects.painOn",
                                          "effects.pain.7", "effects.enduranceCap"), log=True)

    def phase_ON(self):
        self.arm("ON", ON_S)

    def phase_P1(self):
        self.seed("P1", P1_P)
        self.arm("P1", P1_S)

    def phase_B(self):
        super().phase_B()
        self.arm("B", B_S)

    def phase_P2(self):
        self.seed("P2", P2_P)
        self.arm("P2", P2_S)

    def phase_L(self):
        P = self.D["L"] = {}
        self.set_speed(1, "L_one")
        P["pre"] = self.rec("L_pre", ("drain.mask", "drain.pS", "effects.enduranceCap", "effects.stressFloor",
                                      "effects.unhappyFloor", "moodLast.u", "satiety.M"), log=True)
        P["set_M"] = self.write("L_M", "satiety.M", f"{SNACK_M}")

        def fn():
            v = self.rec("L_poll", ("drain.mask", "drain.recovering", "drain.pS"))
            return v.get("drain.mask") is not None and not has_bit(v.get("drain.mask"), MASK_STARVE), v
        P["poll"] = self.poll("L_lapse", fn, LAPSE_CAP_S, POLL_S)
        P["after"] = self.rec("L_after", ("drain.mask", "drain.recovering", "drain.pS", "effects.enduranceCap",
                                          "effects.stressFloor", "effects.unhappyFloor", "moodLast.u"), log=True)
        self.arm("L1", L1_S, settle=False)
        self.set_speed(SPEED_FAST, "L_fast")
        self.arm("L2", L2_S, settle=False)

    def phase_C(self):
        self.restore_clock()
        P = self.D["C"] = {}
        P["errors"] = self.errors_read("C")
        P["parts"] = self.parts_read("C_parts")

    def phases(self):
        return [("S", self.phase_S), ("H", self.phase_H), ("W", self.phase_W48), ("A", self.phase_A),
                ("ON", self.phase_ON), ("P1", self.phase_P1), ("B", self.phase_B), ("P2", self.phase_P2), ("L", self.phase_L),
                ("C", self.phase_C), ("R", self.phase_R)]

    def closing_names(self):
        return ("C", "R")

    # ======================================================== the replay
    def stat_events(self, rows):
        """Each floor seed as a stat event at the first ring row read after it (an unplaced seed is booked)."""
        events, book = [], []
        for st in self.stat_sets:
            if not st.get("ok"):
                book.append({"stat": st.get("stat"), "skipped": "the write did not answer ok"})
                continue
            a = num(st.get("age"))
            i = first_index(rows, lambda r: a is not None and (ring_age(r) or -1) > a + 1e-12)
            s = rows[i]["s"] if i is not None else None
            book.append({"stat": st["stat"], "value": st["value"], "s": s, "how": "age" if s else "unplaced"})
            if s is not None:
                events.append({"s": s, "kind": "stat", "stat": st["stat"], "value": st["value"], "label": st["tag"]})
        return events, book

    def progress_events(self, rows):
        """Each drain.pS write placed at the drain that first ran on it: the ring row before the first row read after
        a_before whose frac.1 reads 1 - p (place_progress); x48's place_set would place a value no drain moves (the
        active state keeps the largest progress) one drain late when the write lands between a row's read and its drain,
        and that drain's take moves health by a minute of the floor rate (0.059, over REPLAY_TOL)."""
        events, book = [], []
        for st in self.sets:
            if st.get("path") != "drain.pS":
                continue
            rep = st.get("reply") or {}
            if rep.get("ok") is not True:
                book.append({"path": st.get("path"), "skipped": "the set did not answer ok"})
                continue
            v = num(rep.get("after"))
            v = num(st.get("value")) if v is None else v
            s = place_progress(rows, v, num(st.get("age_before")))
            book.append({"path": "drain.pS", "value": v, "s": s, "how": "progress" if s is not None else "unplaced"})
            if s is not None:
                events.append({"s": s, "kind": "setpath", "path": "drain.pS", "value": v, "label": st.get("tag")})
        return events, book

    def grade_replay(self, rows):
        """The HEAD replay of the run's own ring (sleep off, game_heal on), the record writes as setpath events and the
        floor seeds as stat events; every REPLAY_TOL field graded. Returns the replay rows or None."""
        xs = self.xs
        inp = self.replay_inputs() if rows else None
        if inp is None:
            self.out["replay"] = {"error": "no ring rows or no start record"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "no replay"}, "")
            return None
        start, player, start_stats = inp
        ev_set, book = L48.build_events(rows, [st for st in self.sets if st.get("path") != "drain.pS"])
        ev_p, pbook = self.progress_events(rows)
        ev_stat, sbook = self.stat_events(rows)
        events = sorted(ev_set + ev_p + ev_stat, key=lambda e: e["s"])
        book = book + pbook
        day_min = num(rows[0].get(OPT_DAYMIN)) or DAY_MIN
        if self.run_dir:
            for name, obj in (("events.json", events), ("player.json", player)):
                with open(os.path.join(self.run_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(obj, fh, indent=1, sort_keys=True)
                xs.copied.append(name)
        self.out["model_inputs"] = {"tool": "tools/replay_live.py replay_live (ServerReplay) at HEAD, game_heal on",
                                    "ring": self.pages, "events": "events.json", "start": "start.json",
                                    "start_stats": start_stats, "player": player, "sleep_allowed": False,
                                    "death_pace": self.prof["pace"], "health_combine": self.prof["combine"],
                                    "day_minutes": day_min, "tol": {k: list(v) for k, v in REPLAY_TOL.items()},
                                    "placement": book, "stat_placement": sbook}
        try:
            import replay_live as RL
            rep, _ = RL.replay_live(rows, events, start, paths=list(RING), user=USER, player=player,
                                    start_stats=start_stats, sleep_allowed=False, death_pace=self.prof["pace"],
                                    health_combine=self.prof["combine"], day_minutes=day_min, game_heal=True)
            i_l = lapse_index(rows, num(g(self.D, "L", "set_M", "age")))
            d = RL.diff(rep, rows if i_l is None else rows[:i_l + 1], REPLAY_TOL)
            d_post = None
            if i_l is not None:
                d_post = RL.diff(rep, rows[i_l + 1:], {k: v for k, v in REPLAY_TOL.items() if k != "health"})
        except Exception as e:                     # noqa: BLE001 - recorded, graded unmeasured
            self.out["replay"] = {"error": f"{type(e).__name__}: {e}"}
            for f in REPLAY_TOL:
                xs.grade(f"REPLAY_{f}", "unmeasured", {"why": "the replay raised"}, "")
            return None
        if self.run_dir:
            with open(os.path.join(self.run_dir, "replay.json"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"rows": rep, "diff": d, "diff_after_lapse": d_post, "events": events}, indent=1,
                                    sort_keys=True, default=str) + "\n")
            xs.copied.append("replay.json")
        self.out["replay"] = {"rows": len(rep), "fields": d.get("fields"), "classes": d.get("classes"),
                              "findings_n": len(d.get("findings") or []), "lapse_s": None if i_l is None else rows[i_l]["s"],
                              "fields_after_lapse": (d_post or {}).get("fields"),
                              "findings_after_lapse_n": len((d_post or {}).get("findings") or [])}
        for f in REPLAY_TOL:
            res = [G.grade_replay_field(d, f)]
            if d_post is not None and f != "health":
                res.append(G.grade_replay_field(d_post, f))
            self._g(f"REPLAY_{f}", replay_verdict(res), f"{f} off the HEAD replay by more than {REPLAY_TOL[f][1]}")
        return rep

    # ======================================================== the grades
    def _g3(self, name, res, falsifier):
        v, obs, samples = res
        self.xs.grade(name, v, obs, falsifier, samples=samples)

    def arm_rec(self, name):
        for a in self.arms:
            if a.get("arm") == name:
                return a
        return {}

    def grade_all(self):
        rows = self.ring_rows()
        self.out["ring_rows"] = len(rows)
        self._g("H1", L48.grade_h1(g(self.D, "H", "h1_record"), g(self.D, "H", "ring_start"), H1_NIL_OK),
                "a ring path other than H1_NIL_OK unresolved at the start")
        self._g("RING", G.grade_ring(g(self.D, "R", "pages") or []), "a ring page unread or a ring error")
        probe_err = {k: v for k, v in (("S", g(self.D, "S", "errors")), ("C", g(self.D, "C", "errors"))) if v}
        flat = {f"{k}.{s}": e for k, v in probe_err.items() for s, e in v.items()}
        self._g("Z", grade_z(g(self.out, "logs", "mod_error") or [], self.out.get("admin_lua_error"), flat),
                "a mod or probe error line, a probe-recorded error, or admin parked")
        self._g("OPT", grade_opt(rows, self.prof), "the first row's drain options or Severity off the profile's")
        seed = num(g(self.D, "A", "seed_age"))
        self._g("ONSET", L48.grade_onset(rows, seed), "no starveAcute row within the lead and the slack")
        self._g3("P0_BASE", L49.grade_base(g(self.D, "S", "pair"), g(self.D, "S", "parts") or {}),
                 "a part holding added pain, or PAIN, STRESS, UNHAPPY or ENDURANCE off level 0 at the first sight")
        a_p = num(g(self.D, "B", "set_p", "age"))
        self._g("BERI_ON", L48.grade_beri(rows, a_p), "no clinical grade and beriberi fraction within BERI_GM")
        rep = self.grade_replay(rows)
        self.grade_symptoms(rows, rep)
        self.out["verdict_summary"] = {k: v.get("verdict") for k, v in self.out["verdicts"].items()}

    def arm_span(self, name):
        a = self.arm_rec(name)
        return num(a.get("age0")), num(a.get("age1"))

    def grade_symptoms(self, rows, rep):
        inf = InForce(rows, rep or [])
        dm = num(rows[0].get(OPT_DAYMIN)) if rows else None
        dm = dm or DAY_MIN
        inj = self.injury
        reads = {}
        for name in ARM_NAMES:
            pe = self.arm_rec(name).get("parts_end") or {}
            if pe.get("parts"):
                reads[name] = {"age": pe.get("age"), "parts": pe.get("parts")}
        part_reads = {k: v for k, v in reads.items() if k in PART_ARMS}
        self._g3("PAIN_PART", grade_part(self.pairs, inf, part_reads, PART_ARMS, dm),
                 "the lower torso's added pain, or a painful part at an arm's end, outside its band")
        short = tuple(n for n in ARM_NAMES if self.arm_short(n))
        self.out["arms_short"] = list(short)
        self._g3("PAIN_TARGET", L49.combine([grade_pain_target(self.pairs, "P1", inf, dm, inj, short),
                                             grade_pain_target(self.pairs, "P2", inf, dm, inj, short)]),
                 "the server's PAIN outside its band at P1's or P2's end")
        br = g(self.D, "A", "onset_bracket") or {}
        i_on = L48.onset_index(rows, num(g(self.D, "A", "seed_age")))
        t_mid = None
        if i_on is not None and rep:
            r_on = next((r for r in rep if r.get("s") == rows[i_on]["s"]), None)
            t_mid = pain_mid(r_on, dm, inj) if r_on is not None else None
        self._g3("PAIN_ONSET", grade_pain_onset(self.pairs, (br.get("false") or [None])[0],
                                                (br.get("true") or [None, None])[1], t_mid),
                 "a side's first Pain level 1 outside its window from the onset's drain")
        self._g3("PAIN_LEVELS", grade_pain_levels(self.pairs, inf, dm, inj, short=short),
                 "an arm's last pairs reading a Pain level other than the replay's mid PAIN's")
        self._g3("PAIN_FOLLOWS", grade_pain_follows(self.pairs), "a side's Pain level off its own PAIN's")
        self._g3("END_CAP", grade_end_cap(self.pairs, inf), "the server's ENDURANCE over the cap in force")
        trk = {n: self.arm_rec(n).get("trk") for n in ARM_NAMES}
        self._g3("END_LEVELS", grade_held_levels(self.pairs, inf, trk, "lvEnd", "endurance",
                                                 lambda r: num(r.get("effects.enduranceCap")), END_ARMS),
                 "a pair or a tracker reading an Endurance level other than the cap's")
        self._g3("STRESS_FLOOR", grade_stress_floor(self.pairs, inf), "the server's STRESS under its floor")
        spans = {n: self.arm_span(n) for n in HOLD_ARMS}
        self._g3("UNHAPPY_FLOOR", grade_unhappy_floor(self.pairs, inf, rows, spans),
                 "the server's UNHAPPINESS under its floor, or the writer's target under the floor")
        self._g3("STRESS_LEVELS", grade_held_levels(self.pairs, inf, trk, "lvStress", "stress",
                                                    lambda r: num(r.get("effects.stressFloor"))),
                 "a pair or a tracker reading a Stress level other than the floor's")
        self._g3("UNHAPPY_LEVELS", grade_held_levels(self.pairs, inf, trk, "lvUnhappy", "unhappy",
                                                     lambda r: num(r.get("effects.unhappyFloor"))),
                 "a pair or a tracker reading an Unhappy level other than the floor's")
        a_m = num(g(self.D, "L", "set_M", "age"))
        self._g("REL_LAPSE", grade_lapse(rows, a_m), "no row with starvation lapsed and beriberi active")
        i_l = lapse_index(rows, a_m)
        a_l = ring_age(rows[i_l]) if i_l is not None else None
        p2 = arm_pairs(self.pairs, "P2")
        cap_p2 = inf.hi(pair_age(p2[-1]), "effects.enduranceCap") if p2 else None
        fl_p2 = inf.lo(pair_age(p2[-1]), "effects.stressFloor") if p2 else None
        self._g3("REL_PAIN", grade_rel_pain(self.pairs, a_l, dm),
                 "the lower torso's added pain set again, or falling off vanilla's decay, after the lapse")
        self._g3("REL_END", grade_rel_end(self.pairs, inf, a_l, cap_p2, "L2" in short),
                 "the cap not eased, ENDURANCE pulled down, or an end level off its own or over the eased bound")
        self._g3("REL_UNHAPPY", grade_rel_unhappy(rows, self.pairs, a_m),
                 "UNHAPPINESS not dropping by the target's fall at once, or Unhappy shown after the release")
        self._g3("REL_STRESS", grade_rel_stress(self.pairs, a_l, fl_p2, "L2" in short),
                 "STRESS raised after the lapse, falling off vanilla's decay, or an end level off the prediction")
        self._g3("REL_HEAL", grade_rel_heal(rows, i_l, rep),
                 "health over its target, taken after the lapse, or short of the target REL_HEAL_MIN_GM past it")


# ================================================================ the boot
def bounded_teardown(tl, server, clients):
    """pzt's teardown with bounded waits (driver review F3): each client's quit TEARDOWN_QUIT_S, the server's stop
    TEARDOWN_STOP_S; hard_kill follows in xs.finish, so the foreground call stays under 600 s at BUDGET_S."""
    for c in clients:
        if c.alive:
            tl.mark("client_quit", user=c.username, rc=c.quit(timeout=TEARDOWN_QUIT_S))
    if server.alive:
        tl.mark("server_stopped", rc=server.stop(timeout=TEARDOWN_STOP_S), errors=len(server.errors))


def _summary(out, run_id, run_dir):
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"), "skipped_phases": out.get("skipped_phases"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "logs_error": out.get("logs_error"),
                      "run_id": run_id, "run_dir": run_dir, "memory": out.get("memory"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


def main(key, driver_file, session_text, pred, budget_s):
    """One boot of x494's profile (x48b_lib.main_line's shape at this lib's session, staged copy, probe and checks)."""
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, verify   # noqa: E402

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
    S = Sess(xs, key, run_dir=run_dir)
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
        "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
        "probe_dirty": git_dirty(PROBE_DIR)[0],
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "lib_x48_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x48_lib.py"),
        "lib_x49_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x49_lib.py"),
        "lib_x45g_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/x45g_lib.py"),
        "driver_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + s["driver"]),
        "prerun_commit": git_say("log", "-1", "--format=%h", "--", PRERUN_FILE),
        "replay_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/replay_live.py"),
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"] or out["probe_dirty"]:
        xs.refuse("the harness Lua or the probe mod is dirty; commit before the boot (CLAUDE.md s5)")
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
                    hits, skipped = X.grep_noecho(lp, LOG_RX, 300, ECHO_RX, NEVER_RX)
                    Lg["server"] += hits
                    Lg["server_echo_excluded"] += skipped
                Lg["mod_error"] = [ln for ln in Lg["server"] if MOD_ERR_RX.search(ln)][:40]
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                Lg.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        xs.finish(bounded_teardown, hard_kill, every, read_logs=read_logs, grade_all=S.grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, s["artifact"])
    _summary(out, run_id, run_dir)
    return out
