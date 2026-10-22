-- NR_Data_Dials.lua -- not a kernel file: the registry of the mod's tuning dials (Plan 19, spec Part A; ruling T1-1),
-- as NR.data.dials = { [id] = row }. It sorts before every kernel file (NR_Data_ < NR_Kernel), so a kernel resolves its
-- dials into its own table fields when it loads (K.monotony.SLOPE = K.dials.get('monotony.SLOPE'), NR_Kernel.lua) and
-- no lookup runs per tick or per minute (Rule 6); the fields stay patchable (replay_live.set_constants, the fit tools).
-- The id is <domain>.<path>, the kernel sub-table and the field (monotony.SLOPE is K.monotony.SLOPE); an adapter's
-- domain is its short table name. One row a line, appended by domain, so a later block never moves an earlier line:
--   value   the dial's value as the kernel wrote it (a number, a boolean or a table; an expression stays an expression,
--           so the double is bit-identical)
--   unit    its unit
--   min     its range, inclusive (a table's every number); a sandbox-backed row's min and max are its option's
--   max
--   src     where the value comes from: space-separated tokens, each a science row (S1234), a register row (#1234) or
--           one of game choice, vanilla, fitted, inference (vanilla names its # row)
--   note    one short sentence
-- and optionally:
--   opt     the sandbox option under NR. that sets it (re-resolved by K.dials.apply, NR_Kernel_Dials.lua); int = true
--           for an integer option, where an out-of-range value reads the default
--   int
--   fit     the fit or calibration that owns the value (a re-fit re-sets it)
--   same    another dial's id: the row has no value, unit range or option of its own and resolves to that dial
--   fixed   true for a value read off the game that must not be tuned: min == max == value, never an option
-- The long provenance is the line's trailing comment, verbatim from the kernel line it replaced. tools/dials.py lists,
-- checks, diffs and sets the rows (a set edits one line in place); tools/dial_lint.py flags a magnitude left outside.
-- Strings are single-quoted, so a register pointer can quote a row.
local NR = NutritionRevamp
NR.data = NR.data or {}
NR.data.dials = {}
local D = NR.data.dials

-- monotony (Plan 19 Task 2, wave W1): NR_Kernel_Monotony.lua, the self-releasing UNHAPPINESS and BOREDOM floor
D['monotony.WINDOW_H'] = { value = 168, unit = 'game h', min = 24, max = 720, src = 'game choice S1592 S1593', note = 'how long a type is remembered after its latest eat' } -- game choice, Plan 11e (ruling 11e-1): the 7 game days a type is remembered, measured from the type's latest eat; a type eaten daily keeps its decayed older eats (ruling T3-4); S1592's daily-against-weekly contrast and S1593's monotony week set the scale, not the size; since Plan 11f Task 9b fix 1 a type past it is forgotten only once its decayed count is one portion or less, where its level is already 0, so the window bounds the record without a step in the floor
D['monotony.HALF_LIFE_H'] = { value = 72, unit = 'game h', min = 6, max = 336, src = 'game choice S1592', note = 'the half-life of the portion count of a type' } -- game choice, Plan 11e (ruling 11e-1): the count's 3-day half-life inside the window, so a type left uneaten for days stops counting (S1592: spacing the presentations slows habituation)
D['monotony.SLOPE'] = { value = 4.3, unit = 'mood points per portion', min = 0, max = 20, src = 'game choice S1592 S1595 S1597 #0042', note = 'the level each recent portion past the first adds' } -- game choice, Plan 11e (ruling 11e-1): the level per recent portion past the first, sized so right after the fifth meal-sized eat of one type at one a day the level reads 4.3 x (2^-1/3 + 2^-2/3 + 2^-1 + 2^-4/3) = 9.98 on each stat, vanilla's stale +10 (#0042); direction S1592-S1595, S1597
D['monotony.CAP'] = { value = 30, unit = 'mood points', min = 0, max = 59, src = 'game choice S1592 S1597 #2369 #0042', note = 'the most the level of a type reaches' } -- game choice, Plan 11e (ruling 11e-1), a level since Plan 11f (ruling T9-1), 30 since Plan 11f Task 9b fix 1 (Angus 2026-10-11, level-1 moodles; S1592-S1597 give direction, not size; thresholds #2369): a type's level, and so the target, never exceeds 30, so a one-food diet at three portions a day holds 30 from day 5, above UNHAPPY level 1 (20) by 10 and BORED level 1 (25) by 5 and under BORED level 2 (50); Moodle.Update sets a level only when the stat is strictly above its threshold (fcmpl/ifle: BORED @856-@873 L219-L220, UNHAPPY @967-@984 L237-L238 on 42.21); vanilla's stale +10 (#0042) still sizes SLOPE but no longer binds the cap, which was vanilla's rotten +20 (#0042) before the fix
D['monotony.STAPLE'] = { value = 0.25, unit = 'multiplier', min = 0, max = 1, src = 'game choice S1593 S1595', note = 'the share of the level a staple holds' } -- game choice, Plan 11e (ruling 11e-1): a staple's level multiplier, outside the cap (Plan 11f Task 9b); S1593's potato product resisted monotony and S1595's bread and butter showed no fall in pleasantness, neither giving a size
D['monotony.MEAL_KCAL'] = { value = 400, unit = 'kcal', min = 100, max = 1500, src = 'game choice S1592 S1595', note = 'the landed energy of one meal-sized portion' } -- game choice, Plan 11e (ruling T3-3); the studies' unit is a served portion (S1592-S1595): the landed energy of one meal-sized portion, the weight-1 eat
D['monotony.BORED_MAX'] = { value = 49, unit = 'mood points', min = 0, max = 49, src = 'game choice #2369 #3015', note = 'the ceiling of the BOREDOM target, under the BORED level-2 step' } -- game choice, Plan 11f (ruling T9-3): the BOREDOM target is held one under the BORED level-2 step 50 (#2369; MoodleStat.<clinit> @118-@133 L16 on 42.21), because vanilla adds UNHAPPINESS while the BORED moodle is above level 1 (BodyDamage.UpdateBoredom @510-@575 L2042-L2043 on 42.21), so monotony alone never drives that term; vanilla also resets BOREDOM while PANIC > 5 (UpdateBoredom @482-@509, #3015), the mod's own dehydration PANIC floor included (ruling T9-3), so the BOREDOM floor is wiped while the character panics
D['monotony.DEAD_ZONE'] = { value = 0.02, unit = 'share of the threshold', min = 0, max = 0.2, src = 'game choice', note = 'the dead zone of the mood floor under a moodle threshold' } -- game choice (spec section 10: the dead-zone width; item 10c): a share of the threshold, 0.4 at UNHAPPY 20, 0.5 at BORED 25
D['monotony.HOLD_EPS'] = { value = 0.01, unit = 'mood points', min = 0.001, max = 1, src = 'game choice', note = 'how far over its threshold a held target sits' } -- game choice (spec section 10: the dead-zone width): mood points a held target sits over its threshold, far under a moodle step and over float noise
