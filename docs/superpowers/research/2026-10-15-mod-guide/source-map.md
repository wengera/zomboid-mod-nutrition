# Plan 14 Task 1: the source map for the Nutrition Revamp player guide

Written 2026-10-15 at HEAD `10dfbc9b` (mod/ last touched at `498bd4a5`). This map is the run sheet for every later
brief of Plan 14 (ledger ruling): the charts, the source of every series, the promises, the vanilla model's formulas,
the vanilla-baseline sessions and the gaps. It cites register rows (`#NNNN`), science rows (`SNNNN`) and artifact
paths; it mints nothing.

## 0. Conventions every later task reads

**Display defaults (spec § 3.5).** Male, no traits, `NR.Mode` Managed, `NR.OnsetSpeed` 1, `StatsDecrease` 3
(×1.0, #0483), `DayLength` 4 (a 90-minute day, the fixture's and the game's default: `docs/platform/harness.md`
fixture table), and **sleep off** (`SleepAllowed`/`SleepNeeded` false: the fixture's false, false on
`docs/platform/harness.md`'s profile-key row for `[server] SleepAllowed / SleepNeeded`, with vanilla then resetting
FATIGUE, #3009; the mod README's Install section tells operators to turn them on for its sleep model). Only S6c and SC1 turn
sleep on, and say so on the chart.

**The two default bodies.** Vanilla's no-trait character weighs 80 kg (every vanilla run's setup weight; the weight
model's 80 kg anchor, #0149). The mod's no-trait male creation body is lean 52.02 kg, fat 13.005 kg, 65.025 kg
(x436 case (a), #3872). A mass chart either plots each from its own start or plots the change from start; Task 9
picks one and says it on the chart.

**The guide's foods.** One meal: `Base.CannedBologneseOpen` (vanilla 540 kcal, hunger −24 script points = −0.24;
the mod's item pass 540 kcal, 61.83 g carbohydrate, 22.194 g fat, 23.598 g protein, 10.26 mg vitamin C;
`data/food-nutrients.json` record `Base.CannedBologneseOpen`, `.vanilla` and `.per_item`). One food for weeks:
`Base.TunaTinOpen` (vanilla 370 kcal, hunger −0.18, 34 g fat, 15 g protein; the mod 370.062 kcal, 15.34 g fat,
54.44 g protein, no vitamin C), four a day = 1480 kcal. A mixed meal for the energy charts: the replay's `meal`
event with `comp` MIXED (`tools/replay_live.py` `MIXED`, 15/50/35 % protein/carbohydrate/fat).

**"Kernel replay"** below means `tools/replay_live.py` `replay_arm(events, minutes=N, backend="server", start=None,
player=<cfg>, rng="half", sleep_allowed=False, paths=(...))` run on the lupa host at HEAD. With no `weight` key in the
player cfg, first sight builds the mod's own creation body from the stand-in's traits (`PARTICIPANT_SIGHT` falls
through to `MET.ensureBody`), i.e. the default body above. `sleep_allowed` must be passed: left `None` the mod
reads an unset option as sleep allowed (the replay docstring) and an awake stand-in builds sleep debt. An eat of a
vanilla food is `{"minute": m, "kind": "eat", "fullType": "<id>", "cal": …, "carb": …, "lip": …, "pro": …,
"hunger": <script/100>, "foodType": …}` with the item pass's macros as the game's item reads them
(`NR_ItemPass_Food.txt`, generated from `data/food-nutrients.json` `.per_item` and written to two decimals, read as
float32: Task 4, the data winning over this map's first reading of `.per_item`); Task 4 asserts that the vector the
intake chain lands equals the mod's table and that record to the table's digits (as #3182 did live for an apple and
bread). Water for every replay that drinks is `autodrop` events of 500 g every 2 game hours from 08:00 to 22:00 (4 L
a day; Task 4 fix 1, review C-1: the 600 g at 08, 12, 16 and 20 first written here sat below the mod's own resting
loss and killed every multi-day replay by dehydration, lethal code 6, from about day 5). Every multi-day mod scenario
also eats real micronutrients: its meals are `plate` meals (replay_live's meal `plate`: the guide's foods and an
orange, whole vectors from the mod's table), since macro-only meals reach cardiac beriberi by day 24. Rule R-1: each
replay asserts it stays alive and under 3 % dehydration over its plotted window, unless its series names the death
and ends there. Measured speed: one game day of the server pipeline
takes about 0.34 s of CPU here (2026-10-15), so a 90-day replay is about 30 s.

**Ring leaves.** A ring row's keys are flat dotted strings (`"stomach.liquid"`, `"body.fm"`, `"satiety.M"`), so a
ring leaf is written in bracket form, `rows_list[k]["stomach.liquid"]`, and `read_artifact` (Task 3) must match the
longest key before it splits a path on dots. A bare `rows_list[k].HUNGER` is a plain key.

**"Strength day"** means the kernel's own `K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)` stepped once a game
day on `server_host.Host`, from `K.body.new(K.body.create(muscle, weight, K.strength.DEFAULTS, sexIdx, profBoost),
sex, 0)`, the level read with `K.strength.level(body.lm, body.N0, body.T, P)` and the written perk with
`K.strength.heldLevel(L, Lw)` (the call pattern of `testing/tests/kernel/test_strength_day.py` `_days`). S is hard
sets a week, p protein g/kg/day, E the day's energy balance in kcal. The README's "perfect training" is S 20,
p 2.0, E +10 % of TDEE; with the strength oracles' TDEE 2600 that is E +260 (`strength_oracles.py` uses 0.05 × 2600
for its year-1 oracle: Task 4 names which it uses).

**Proof runs and the HEAD-replay admission test.** A kernel series names the live run that shows the replay
matches the game (`proof_run`). Most mod live runs predate Plan 13's switch to the creation body (`c7e816e6`) and
its low-fat hunger ramp (`31ce0635`, `c5139c31`); the Plan 11f runs (x27x, x276 at `983ebd6`, x30x at `35c3049e`)
also predate Plan 11g's satiety rework, the gut stage that replaced the meal pool (`b3107be5`, `bc92b13f`,
`c2c96dd6`, `a552d14f`), so their HUNGER will most likely fail the test and their charts are planned as kernel
lines with the old runs as proof only. Their **live points** are drawn on a chart only when Task 4's
admission test passes: the HEAD kernel replay of that run's own inputs (its `start.json` and `events.json`, or a
fresh first sight with its event list where the old start record no longer loads under the no-compatibility rule)
reproduces the run's ring within the run's own graded tolerance (HUNGER 0.002, es 0.005; x361 guide's
`DEFAULT_TOL`). A run that fails the test stays as the proof run of the line and its points are not drawn.
x435 and x436 (`c5139c31`) have only behaviour-preserving skews after them (their guides' skew notes), so their
points need no test for the Strength and creation series. x434 (`0a6b0215`) predates Plan 13 Tasks 10b and 10c
(`f96e357f`, `31ce0635`, `aa869451`, `c5139c31`: fat starts, thin traits, the low-fat ramp, `heldLevel`'s drop
margin), which leave `K.strength.day`'s deficit partition untouched, so it stands for the partition only.

**do-not-cite.** Every artifact path below was picked from its run's reading guide; `read_artifact` (Task 3) still
checks each against `docs/reference/do-not-cite.csv` and its parents. Known traps: x361's `readings.courses.<c>.
series[0].*` (the landing row), every `*_replay` on a sip row, x34's `vs_replay.BOREDOM`, x362's `readings.day.*.
points`, x434's placed `ebDay`, every wall-clock leaf (`wall*`, `epoch_ms_*`); a whole `observed` or `readings`
object is a parent and is never cited, only its leaves.

## 1. Charts (39)

| id | section | title | x axis | y axis | series |
|---|---|---|---|---|---|
| H1 | At a glance | Hunger after one meal | game hours since the meal, 0–6 | hunger, 0–1 | H1-v-model, H1-v-live, H1-m-kernel |
| H2 | At a glance | Body mass on 1500 kcal a day | game days, 0–30 | kg (or change from start) | H2-v-model, H2-v-live, H2-m-fat, H2-m-lean, H2-m-total |
| H3 | At a glance | Strength over a year of training | game days, 0–365 | Strength level, 0–10 | H3-v-model-x1, H3-v-model-x15, H3-m-level, H3-m-written |
| H4 | At a glance | Five common foods, vanilla against the mod | food (Apple, Bread, Bolognese, Burger, Tuna) | kcal and grams per item | H4-v-kcal, H4-v-carb, H4-v-fat, H4-v-pro, H4-m-kcal, H4-m-carb, H4-m-fat, H4-m-pro |
| S1a | S1 Your first day | Hunger through a first day of four meals | game hours from 07:00, 0–24 | hunger | S1a-v-model, S1a-v-live, S1a-m-kernel |
| S1b | S1 | When the hunger moodles arrive without food | game hours from a fresh start, 0–36 | moodle level, 0–4 | S1b-v-model, S1b-v-live, S1b-m-kernel, S1b-m-live |
| S1c | S1 | Thirst without a drink | game hours, 0–24 | thirst, 0–1 | S1c-v-model, S1c-v-live, S1c-m-kernel, S1c-m-live |
| S2a | S2 Skipping meals | Hunger through a 36-hour fast and the refeed | game hours from the last meal, −12–60 | hunger | S2a-v-model, S2a-v-live, S2a-m-kernel, S2a-m-live |
| S2b | S2 | Eating after the fast | day after the fast (day 2, day 3) | intake ÷ the fed arm's | S2b-m-kernel, S2b-m-live, S2b-study-1613, S2b-study-1614 |
| S2c | S2 | Hunger as fat is lost | kg of fat lost | extra kcal a day eaten at the request | S2c-v-model, S2c-m-kernel, S2c-study |
| S2d | S2 | A long fast with water | game days, 0–90 | health, kg | S2d-v-model-health, S2d-v-live-health, S2d-v-model-weight, S2d-v-live-weight, S2d-m-mass, S2d-m-drain |
| S3a | S3 Living on one food | Vitamin C on tinned tuna alone | game days, 0–60 | vitamin C store (0–1) and grade | S3a-m-pool, S3a-m-grade, S3a-study-0224, S3a-study-0225 |
| S3b | S3 | Mood on one food | game days, 0–7 | unhappiness, boredom (0–100) | S3b-m-live-U, S3b-m-live-B, S3b-m-kernel-U, S3b-v-live-U, S3b-v-live-B |
| S3c | S3 | What fixes it: an orange a day | game days, 40–80 | vitamin C store | S3c-m-pool, S3c-study |
| S4a | S4 A year at the gym | Strength by diet | game days, 0–365 | Strength level | S4a-m-perfect, S4a-m-lowprotein, S4a-m-deficit, S4a-v-model-x1, S4a-v-model-x07 |
| S4b | S4 | Ten years toward the natural cap | game years, 0–10 | Strength level | S4b-m-level, S4b-m-cap, S4b-v-model, S4b-study |
| S4c | S4 | Stopping and starting again | game days, 0–910 | Strength level | S4c-m-kernel, S4c-v-model, S4c-study-0618, S4c-study-0078 |
| S5a | S5 Choosing your body | The starting body of each pick | pick (none, Strong+Obese, Weak+Overweight, Overly Lean, Weak+Gaunt, Feeble+Overly Lean) | kg; Strength level | S5a-m-live-lean, S5a-m-live-fat, S5a-m-live-weight, S5a-m-live-level, S5a-v-model-weight, S5a-v-model-level |
| S5b | S5 | How each body drifts, untrained | game days, 0–90 | Strength level; kg | S5b-m-strong-level, S5b-m-weak-level, S5b-m-none-level, S5b-m-gaunt-weight, S5b-m-overfat-weight, S5b-m-none-weight, S5b-v-model-level |
| S5c | S5 | A thin start is hungry | game days, 0–30 | energy state (hunger drive) | S5c-m-gaunt, S5c-m-none, S5c-m-live, S5c-v-model |
| S6a | S6 Coffee, beer, no sleep | Caffeine and tolerance | game hours over day 1 and day 14 | caffeine in the body (mg); fatigue | S6a-m-day1, S6a-m-day14, S6a-v-model |
| S6b | S6 | Four beers | game hours, 0–24 | intoxication (0–100); blood alcohol % | S6b-v-model, S6b-v-live, S6b-m-bac, S6b-m-intox, S6b-m-hangover |
| S6c | S6 | A short night and the next day's hunger | game days, 0–4 | sleep debt (h); hunger factor | S6c-m-kernel, S6c-m-live, S6c-v-model, S6c-study |
| SN1 | Nutrients and foods | What the five foods carry | food | mg or g per item | SN1-m-vitC, SN1-m-fibre, SN1-m-iron, SN1-m-sodium |
| SE1 | Eating and the stomach | A drink and a meal in the stomach | game minutes | grams; fill (0–1) | SE1-m-live-liquid, SE1-m-live-fill, SE1-m-kernel-fill |
| SH1 | Hunger | How long a meal holds hunger off | meal kcal | minutes to the hunger request | SH1-m-kernel, SH1-m-live, SH1-study-1247, SH1-study-1248 |
| SH2 | Hunger | Three meals against six | arm | mean hunger over 24 h (ratio) | SH2-m-kernel, SH2-m-live, SH2-study |
| ST1 | Thirst and salt | Ten hours at rest without a drink | game hours, 0–10 | thirst | ST1-v-model, ST1-m-kernel, ST1-m-live |
| ST2 | Thirst and salt | Five days without salt | game days, 0–5 | body sodium change (mmol/24 h); plasma sodium | ST2-m-live-na, ST2-m-live-plasma, ST2-m-kernel |
| ST3 | Thirst and salt | Health without water | game days, no food and no water | health | ST3-m-dry |
| SM1 | Monotony | Varying the diet lifts the mood | game hours after the last repeat | unhappiness | SM1-m-live, SM1-m-kernel |
| SB1 | The body | Lean mass at a deficit and a surplus, trained or not | game days, 0–60 | lean kg | SB1-m-def-rest, SB1-m-def-train, SB1-m-sur-rest, SB1-m-sur-train |
| SB2 | The body | Which weight trait a body gets | example body (lean 90 kg, average, soft 85 kg) | trait band | SB2-v-model, SB2-m-kernel |
| SX1 | Exercise and energy | Energy per hour by activity | activity | kcal per game hour at 80 kg | SX1-v-model, SX1-m-kernel, SX1-m-live |
| SX2 | Exercise and energy | Hunger after hard exercise | game minutes after the set | hunger | SX2-v-model, SX2-m-live, SX2-m-kernel |
| SS1 | Strength | A year's Strength by weekly sets | hard sets a week, 0–20 | Strength level after a year | SS1-m-kernel, SS1-v-model |
| SD1 | Deficiency and excess | Clinical scurvy and health | game days | health | SD1-m-live, SD1-m-kernel |
| SD2 | Deficiency and excess | How long each nutrient lasts with none eaten | nutrient | days to Marginal, days to Clinical | SD2-m-marginal, SD2-m-clinical, SD2-study |
| SC1 | Caffeine, alcohol and sleep | Short nights build a sleep debt | night | hours slept; debt (h) | SC1-m-live-booked, SC1-m-live-debt, SC1-m-kernel |
| SV1 | What you see on screen | The Overfull moodle | grams in the stomach | moodle level, 0–4 | SV1-m-kernel, SV1-m-live |

H1–H4 are the spec's headline charts; the At-a-glance comparison table is a table, not a chart. The Systems section
"the body traits and character creation" links to S5a–S5c and carries no chart of its own.

## 2. Series (147)

Badges: `live` (Measured live), `kernel` (Simulated by the mod's code), `vanilla-live` (Vanilla, measured),
`vanilla-model` (Vanilla, from the game's code), `study`. VM-n are the formulas of § 4. "Gap" means the source does
not exist yet; § 6 names what fills it.

### At a glance

| id | side | badge | source | notes |
|---|---|---|---|---|
| H1-v-model | vanilla | vanilla-model | VM1, VM3, VM4: HUNGER 0.25 at t0, eat `Base.CannedBologneseOpen` whole (−0.24, not cooked), 1-min steps for 6 h, DayLength 4, awake idle | After the eat HUNGER is 0.01, not at its minimum, so `JustAteFood` fills no timer (#3597, #0054) and hunger rises at once; the chart's second arm (eat at 0.10, hunger to 0) shows the 3120-unit freeze of about 17 game minutes (#0529). |
| H1-v-live | vanilla | vanilla-live | V1a `minute-ring-admin-1.json` `rows_list[k].HUNGER` and `.age`, arms A and B | Gap until V1 runs. |
| H1-m-kernel | mod | kernel | kernel replay: fresh default record from 07:00 (`hour_offset`), no food until the written HUNGER first reaches 0.25 (`RL.request_minute`), then eat `Base.CannedBologneseOpen` (item-pass macros), 6 h after; paths `HUNGER`, `satiety.M`, `body.energyState` | proof_run `x361-20261012-200722` (#3698, #3700: a 650 kcal mixed meal at the request, the replay equal to the live ring within 1.0e-4). No live points: x361's meal is `TKX.Mixed650`, not this one; its points live on SH1. |
| H2-v-model | vanilla | vanilla-model | VM6, VM7, VM8: 80 kg, calorie store 0, 3 × 500 kcal at 07/12/18 (MIXED macros into the stores), awake idle all day (sleep off), 30 days at 1-min steps | Vanilla gains at this intake: the idle day burns 1382.4 kcal at 80 kg (#0455), so the store climbs above the 1000 kcal gain threshold (#0149). |
| H2-v-live | vanilla | vanilla-live | V2 `nutrition.get` replies, hourly `weight` (and `calories`) | Gap until V2 runs. V2 starts its calorie store at 3000 (the value read first) and eats four `Base.TunaTinOpen` a day (1480 kcal), which vanilla's weight reads the same way (calories only, macros only as multipliers above 400 g, #0180, #0153). It validates the store's arithmetic and the gain rate over 36 h, not 30 days of drift: from a store of 0 the gain threshold is never reached in 36 h and weight would read flat (a trivial reading). |
| H2-m-fat | mod | kernel | kernel replay 30 days: `plate` meals of 500 kcal at 07/12/18, the replay's water; path `body.fm` read at each 07:00 day close | proof_run `x434-20261015-053645` (#3869: deficit closes equal to the kernel's replay of their inputs) and `x435-20261015-101839` (#3870). |
| H2-m-lean | mod | kernel | the same replay, `body.lm` + `body.lx` | Same proof. |
| H2-m-total | mod | kernel | the same replay, `body.fm` + `body.lm` + `body.lx` (the weight the mod writes, README "The body") | Same proof. |
| H3-v-model-x1 | vanilla | vanilla-model | VM11: start level 5 at 37 500 XP (#2874), +360 XP a set (#3844) × 20 sets a week, one every 8.4 game hours from hour 0, thresholds #2102, cap #2109, the protein factor pinned at 1 (`protein_factor`) | A pure extrapolation of one measured set. Task 4 (the model's output, Task 2 ruling): level 9 at the year's end, 412 980 XP; only the ×1.5 line reaches 10. |
| H3-v-model-x15 | vanilla | vanilla-model | VM11 with the protein factor pinned at 1.5 (protein store between 50 and 300, #2112) | #2112 is C-only; V3 measures it. Level 10 on day 292 (Task 4). |
| H3-m-level | mod | kernel | Strength day × 365 from the no-pick body, S 20, p 2.0, E +260, tdee 2600, ts 1; `K.strength.level` each day | proof_run x435 (#3870, #3871) and x434 (#3869). |
| H3-m-written | mod | kernel | the same run, `K.strength.heldLevel` day by day (the perk the player sees) | #3871 (the level write rises at the whole number live). |
| H4-v-kcal, -carb, -fat, -pro | vanilla | vanilla-model (provenance `dataset`) | the install's item script `<install>/media/scripts/generated/items/food.txt`, `Base.X.Calories`, `.Carbohydrates`, `.Lipids`, `.Proteins` for X in `Apple`, `Bread`, `CannedBologneseOpen`, `Burger`, `TunaTinOpen` (ruling H4-v: the game's own data is the vanilla source; `data/food-nutrients.json`'s `.vanilla` copy stays the mod's) | The 42.21 install (CLAUDE.md § 2). Four series. |
| H4-m-kcal, -carb, -fat, -pro | mod | kernel (provenance `dataset`) | the same records' `.per_item.calories`, `.carbs`, `.lipids`, `.proteins` (generated with `NR_ItemPass_Food.txt` by `tools/food_nutrients.py`, gated by its `--check`) | proof: x172b (#3182, #3183: a whole Apple and Bread landed the table's vector live). Four series. Burger's carbohydrate 0 → 46.65 g and tuna's protein 15 → 54.44 g are the chart's story. |

### Scenarios

| id | side | badge | source | notes |
|---|---|---|---|---|
| S1a-v-model | vanilla | vanilla-model | VM1, VM3, VM4: HUNGER 0 at 07:00, `Base.TunaTinOpen` (−0.18) at 08, 12, 16, 20 | |
| S1a-v-live | vanilla | vanilla-live | V2 ring `rows_list[k].HUNGER`, its first 24 h | Gap until V2 runs. |
| S1a-m-kernel | mod | kernel | kernel replay 24 h from a fresh default record at 07:00, eats `Base.TunaTinOpen` at the same clock | proof_run `x362-20261012-201625` (#3703, a maintenance day and a surplus day replayed within 2.1e-4) and x361. |
| S1b-v-model | vanilla | vanilla-model | VM1 + VM5's moodle thresholds: HUNGRY level from HUNGER 0, 36 h | Levels at 4.70, 8.32, 17.30 and 34.84 game hours (#0492–#0495). |
| S1b-v-live | vanilla | vanilla-live | V1b ring HUNGER → level (#0508 thresholds), plotted at the model-equivalent time of its 0.60 start | Gap until V1 runs. |
| S1b-m-kernel | mod | kernel | kernel replay 36 h, fresh default record, no food; path `_G.NutritionRevamp.server.bus.lastSig.admin` → energy level (the thousands digit, as `test_replay_live_energy.py` `long_fast_levels`) | proof_run `x364-20261012-203308` (#3705) and `x405-20261013-155742` (#3792). |
| S1b-m-live | mod | live | `x36-grade-20261012/grade.json` `sessions.x364.readings.ring_levels.changes[i].age` (i 0, 1) less `x364-20261012-203308/start.json` `rec.firstSeen`: level 1 at 8.37 h, level 2 at 20.86 h after first sight | Drawn only if x364 passes the admission test (its body was the pre-Plan-13 80 kg split). Pending for M1 (x446, the HEAD fresh record; Task 4 fix 2, ruling N-2): x364 passes the admission on its level-change ages (4.8 game minutes against a named 15), but its start (the pre-Plan-13 body, first sight at 10:00) is not the fresh HEAD record S1b-m-kernel simulates; Task 8 draws this from x446. |
| S1c-v-model | vanilla | vanilla-model | VM5: THIRST from 0 at 8.0e-6 per game-second, linear (#0476) | Level 1 at 4.17 h, level 4 at 29.17 h (#0492, #0495). |
| S1c-v-live | vanilla | vanilla-live | V1a ring `rows_list[k].THIRST` (8.5 h, unpinned) | Gap until V1 runs. |
| S1c-m-kernel | mod | kernel | kernel replay 24 h, fresh default record, no drink; paths `THIRST`, `fluids.thirstTarget` | proof_run `x151t-20261005-183551` (#2963, ten hours at rest equal to the kernel) — on the Plan 4 build: see G7. |
| S1c-m-live | mod | live | `x364-20261012-203308` `minute-ring-admin-{1,721,1441,1974}.json` `rows_list[k].THIRST`, `.age` (32 h, no drink) | THIRST was never graded against a replay in any run (G7); drawn only after the admission test with THIRST added. Pending for M1 (x446; Task 4 fix 2, ruling N-2): x364 passes the admission on THIRST (0.0018 against a named 0.002), but its start (the pre-Plan-13 body, THIRST 0.05, first sight at 10:00) is not the fresh HEAD record S1c-m-kernel simulates; Task 8 draws this from x446. |
| S2a-v-model | vanilla | vanilla-model | VM1, VM3, VM4: day 0 meals `Base.CannedBologneseOpen` at 07/12/18 with a last eat at 20:00 to HUNGER 0 (timer filled), no food for 36 h, then the same meals | |
| S2a-v-live | vanilla | vanilla-live | V1b ring HUNGER from its 0.60 start, placed on the model's curve | Gap until V1 runs. |
| S2a-m-kernel | mod | kernel | kernel replay of `test_replay_live_oracle.py` `fast_plans()`'s fast arm on the default body (warm days, day 0 "maint", day 1 skipped, days 2–3 "request"), sleep off; paths `HUNGER`, `body.energyState` | proof_run `x27-grade-20261010` (#3670) and x364 (#3705). |
| S2a-m-live | mod | live | x364 ring `rows_list[k].HUNGER` (a 32 h fast from a fresh record) | Admission test. |
| S2b-m-kernel | mod | kernel | `test_replay_live_energy.py` `fast_server()`'s ratios `r2`, `r3` (the oracle's 70 kg man, `MAN`) | The default-body variant is Task 4's choice; the oracle's body is the one its bands were fitted on. Sleep on, 23:00–07:00, the oracle's protocol (`sleep_events`, no `sleep_allowed` passed): the chart says so. |
| S2b-m-live | mod | live | `x27-grade-20261010/rows.json` `row6_7.ratios.2.live`, `row6_7.ratios.3.live` (1.2141, 0.9512; #3670) | Plan 11f build, before the 11g satiety rework: planned as proof only (the kernel line stands); drawn only if the x27x rings pass the admission test, which is unlikely. |
| S2b-study-1613 | — | study | S1613 (Johnstone 2002: 1.20 on the day after a 36 h fast) | |
| S2b-study-1614 | — | study | S1614 (Clayton 2016: 1.0 on day 3) | |
| S2c-v-model | vanilla | vanilla-model | VM14: no hunger term reads a body store (#0501, #0475): a flat 0 | |
| S2c-m-kernel | mod | kernel | `test_replay_live_energy.py` `fat_loss_server()` on the default body: intake at fat depletions 0, 0.05, 0.25, 0.40, 0.55 (`fat_loss_intake`) against kg of fat lost | proof_run `x436-20261015-094119` (#3874: the thin starts' energy state equal to `K.deficit.state(0, fatDep)` live). Sleep on, 23:00–07:00, the oracle's protocol; the chart says so. |
| S2c-study | — | study | S1254 converted per kg of fat (125 kcal/d, via S2208, S2206), band ×/÷ 1.5 (`deficit_oracles.py` `S1254_KCAL_PER_KG`, `S1254_TOL`) | |
| S2d-v-model-health | vanilla | vanilla-model | VM10: HUNGER from 0 to 0.70 at 34.84 h, then −3.564 health a game hour at DayLength 4, a 90-minute day (#0518), tier 3 adds no regeneration (#2353, #2354): death about 62.9 h after the last meal | x in game days, as the other S2d series (review I-2); the line ends at the death. |
| S2d-v-live-health | vanilla | vanilla-live | V1b `health.get` hourly `overall` | Gap until V1 runs. Vanilla death by hunger was never measured: the only death on record was thirst (#0173, #0174). |
| S2d-v-model-weight | vanilla | vanilla-model | VM6–VM8: the calorie store from 800 toward the −2200 floor, the weight with it (#0161, #0154) | Ends at the model's hunger death, 62.9 h (rule R-4; review I-1). Below 35 kg vanilla clamps the weight and drains health (`Nutrition.setWeight`, T2.4, now in VM8); a fast never reaches it first. |
| S2d-v-live-weight | vanilla | vanilla-live | `scenario-20261004-190146/scenario-nutrition_3day_fast.json` `test.samples[k].weight` (80 → 78.574 kg over 72 h, vanilla Nutrition on; hunger pinned, a control #0500) | Built 42.20.4; usable for vanilla data (amendments item 3). |
| S2d-m-mass | mod | kernel | kernel replay 90 days, no food, the replay's water; paths `body.fm`, `body.lm`, `body.lx` | proof_run x434 (#3869, the deficit partition). Rule R-1: the line ends at the death, cardiac beriberi (lethal code 3) from day 24.05, health gone at day 27.05 (Task 4 fix 1). |
| S2d-m-drain | mod | kernel | the same replay, the record's drain and lethal code (mirrored as `effects_drain`, `effects_lethal`, #3106; Task 4 confirms the record path) | The starvation drain (fat gone) was never measured live (G16); proof of the drain path is x161b's scurvy drain (#3106) and the dial (#3105). Also plotted: the mod's hunger never passes 0.69 (#3074, #3123). |
| S3a-m-pool | mod | kernel | kernel replay 60 days, four `Base.TunaTinOpen` a day at 08/12/16/20, `autodrop` water; path `nutrients.vitC.p` (plus the first two other records to reach grade 2, which Task 4 reads off the same replay) | proof_run `x151r-20261005-192030` (#2977, #2978: grade crossings where the kernel puts them, at OnsetSpeed 30; Plan 4 build, G11). Vitamin C is never scaled by OnsetSpeed (README options table), so no live run can reach its onset. Rule R-1: tuna alone kills by cardiac beriberi (lethal code 3) from day 54.97, health gone at day 57.97, where the S3a lines end (Task 4 fix 1). |
| S3a-m-grade | mod | kernel | the same replay, `nutrients.vitC.g` | |
| S3a-study-0224 | — | study | S0224 (161 days to scurvy signs, one self-experimenter) | Reference point. S0967 is superseded and its successor S0210 is open, so neither is drawn. |
| S3a-study-0225 | — | study | S0225 (about 40 days in the controlled series, Hodges 1971) | Reference point. |
| S3b-m-live-U | mod | live | `x34-regrade-20261011/rows.json` `row13.days.days.<d>.server_U`, d 0–6 (3.75, 13.83, 21.82, 28.19, 30, 24.32, 19.34; #3683) | Mod `c648c178`; monotony's later changes are the offline skip and refactors only (git log), so the mechanism stands; the eats were `TKX.Mono450`, the chart says so. |
| S3b-m-live-B | mod | live | the same days' `.moodLast_b` | BOREDOM itself is reset-bounded by the driver (guide), so the remembered target is plotted, not the stat. |
| S3b-m-kernel-U | mod | kernel | kernel replay 14 days, four `Base.TunaTinOpen` a day, then varied; path `UNHAPPINESS` | proof_run x34 chain (#3683, TWIN within 7.1e-15). |
| S3b-v-live-U | vanilla | vanilla-live | V2 ring `rows_list[k].UNHAPPINESS` | Gap until V2 runs; vanilla has no monotony (the tuna row's mood changes are blank). |
| S3b-v-live-B | vanilla | vanilla-live | V2 ring `rows_list[k].BOREDOM` | Shows vanilla's own idle boredom rise (x34 F-T9r-4). |
| S3c-m-pool | mod | kernel | S3a's replay continued to day 80 with one `Base.Orange` (item-pass vector) a day from day 45; `nutrients.vitC.p`, `.g` | proof as S3a. With the orange the replay stays alive to day 80: the orange also carries thiamine (0.120 mg against a tuna tin's 0.071), which keeps the thiamine grade at 3 at worst and averts S3a's cardiac beriberi death; the chart plots vitamin C alone (Task 4 fix 2, re-review N-1). |
| S3c-study | — | study | S0229 (time to symptom improvement after vitamin C treatment) | |
| S4a-m-perfect | mod | kernel | Strength day × 365, S 20, p 2.0, E +260 | proof x435, x434. |
| S4a-m-lowprotein | mod | kernel | the same, p 0.8 | |
| S4a-m-deficit | mod | kernel | the same, p 2.0, E −500 | |
| S4a-v-model-x1 | vanilla | vanilla-model | VM11, the protein factor pinned at 1 | Level 9 at the year's end (Task 4). |
| S4a-v-model-x07 | vanilla | vanilla-model | VM11, the protein factor pinned at 0.7 (protein store below −300, #2112) | |
| S4b-m-level | mod | kernel | Strength day × 3650, perfect training | proof x435. The oracle's long runs are `strength_oracles.py` `_yearly`, `o_year1`. |
| S4b-m-cap | mod | kernel | `K.strength.level(body.Fc, body.N0, P.Tmax, P)` of the same body (the level at the cap) | |
| S4b-v-model | vanilla | vanilla-model | VM11 at 20 sets a week with the protein factor pinned at 1.5, to level 10 and capped (#2109) | Task 4 (the model's output, Task 2 ruling): level 10 on about day 292 at ×1.5; at factor 1 the year ends at level 9 (412 980 XP). Once capped a set's XP is discarded, so rust returns: from about day 340 the line dips from 10 to 9 between sets (Task 2 review M-8; code only, no live reading, and the series says so). |
| S4b-study | — | study | S1915 (Kouri 1995's natural FFMI 25 kg/m², `strength_level.py` `FC_LIMIT`) shown as a level | |
| S4c-m-kernel | mod | kernel | Strength day: 365 d perfect, 365 d S 0 p 1.2 E 0, 180 d perfect | The detraining and regain arms were never closed live (G14). |
| S4c-v-model | vanilla | vanilla-model | VM11 + VM12 (rust): −1 XP per 1200-unit bucket once the timer passes 20 000 (#2151, #2154–#2156): the level does not move in a year | The first rust step comes 48.6 days after the last set (a fresh character's drops level 5 to 4 at day 48.6): code only, no live reading, and the series says so (Task 4). |
| S4c-study-0618 | — | study | S0618 (strength loss over 12 weeks of detraining and time to regain) | S0618's subjects were older men detrained 12 weeks against the mod's 52, so the timescales are not comparable; the mod regains to 6.92 in 8 weeks against 8.25 trained (Task 4 fix 1, review I-5). |
| S4c-study-0078 | — | study | S0078 (after 20 weeks of detraining, strength stayed above baseline while muscle size returned to it; on retraining, trained and untrained legs responded alike) | Replaces S0617, which is superseded by S0078. Its retraining finding is the opposite of a muscle-memory advantage; the series is drawn as a range above baseline, never a value (review I-4); the mod regains more slowly than S0618's under-8-week return (6.92 after 8 weeks against 8.25 trained), and the chart's note says so (review I-5). |
| S5a-m-live-lean | mod | live | `x436-20261015-094119/creation.json` `verdicts.36_<case>_body.observed.record.lm`, case a–f (#3872) | Task 4 cites the leaf, never `observed`. |
| S5a-m-live-fat | mod | live | `verdicts.36_<case>_body.observed.record.fm` | |
| S5a-m-live-weight | mod | live | `verdicts.36_<case>_body.observed.derived.mass` | |
| S5a-m-live-level | mod | live | `verdicts.36_<case>_xp.observed.client_level` and `.observed.xp` (Strength 5, 9, 1, 5, 1, 3) | `verdicts.36_<case>_xp` itself holds a `wall` leaf: never cited whole. |
| S5a-v-model-weight | vanilla | vanilla-model | VM9: creation weights Obese 105, Overweight 95, Underweight 70, Very Underweight 60 (#0533), none 80 | |
| S5a-v-model-level | vanilla | vanilla-model | VM13: start level 5 plus each muscle trait's boost | JT1 (a script read for Task 2): vanilla Weak starts at level 0, not 1; the mod's Weak 1 is the mod's own floor (Task 2 ruling). |
| S5b-m-strong-level | mod | kernel | kernel replay 90 days, stand-in traits `["strong"]` (the trait id the creation reads: Task 4 checks), meals at "request", sleep off; the written Strength level | proof x436 (creation), x434/x435 (closes). The README's "an idle Strong character settles in the Stout band". |
| S5b-m-weak-level | mod | kernel | the same with `["weak"]` (Task 4 confirms the id) | The spec's Weak. |
| S5b-m-none-level | mod | kernel | the same, no traits | |
| S5b-m-gaunt-weight | mod | kernel | the same with Very Underweight (Gaunt); `body.fm` + `body.lm` + `body.lx` | |
| S5b-m-overfat-weight | mod | kernel | the same with `["overweight"]` (shown as Overfat; Task 4 confirms the id) | The spec's Overfat. |
| S5b-m-none-weight | mod | kernel | the same, no traits | |
| S5b-v-model-level | vanilla | vanilla-model | VM11 + VM12: no XP from the start level 5 | A fresh character's first rust step drops level 5 to 4 at day 48.6 (the timer from −50 000 to 20 000): code only, no live reading, and the series says so (Task 2 ruling; not flat). |
| S5c-m-gaunt | mod | kernel | S5b's Gaunt replay, `body.energyState` | proof x436 (#3874). |
| S5c-m-none | mod | kernel | S5b's no-trait replay, `body.energyState` | |
| S5c-m-live | mod | live | `x436-20261015-094119/creation.json` `verdicts.36_{d,e,f}_hunger.observed.es` (1.4962, 1.6529, 1.4963; #3874) at day 0 | |
| S5c-v-model | vanilla | vanilla-model | VM14: hunger reads no weight or fat (#0488, #0501): flat 1 | |
| S6a-m-day1 | mod | kernel | kernel replay: `drink` Coffee 0.25 L at 08, 12, 16; paths `acute.caf` (mg) and `effects.fOff` | proof_run x151r (#2982, the 5.0 h half-life) and x161f (#3077); both on the Plan 4–5 build (G10). |
| S6a-m-day14 | mod | kernel | the same schedule every day to day 14; day 14's `acute.caf`, `effects.fOff` (the tolerance's effect) | Tolerance τ 7 days (`test_kernel_acute.py` `test_caffeine_tolerance_tau_7d_both_ways`). The 5 h half-life and the 7-day tolerance are the mod's game choices resting on open rows (S0851, S1123, direction only), so no study series is drawn. Live proof at HEAD: M2. |
| S6a-v-model | vanilla | vanilla-model | VM15: FATIGUE −0.025 a 0.25 L cup (−10 a litre, #2949), the same on day 14, plotted as the change per cup, not the flat `fatigue` series (Task 2 review M-7) | Assumes sleep allowed and needed, as V4 runs: under the display default (sleep off) vanilla resets FATIGUE every update (#3009) and the coffee's change does not last; the chart says so. |
| S6b-v-model | vanilla | vanilla-model | VM16: four 0.3 L beers at 0.05 a litre, 400 × alcohol × the hunger factor (#2923, #2926), decay 45.36 a game hour at DayLength 4 (#2922) | |
| S6b-v-live | vanilla | vanilla-live | V4 `stats.all` polls, `stats.INTOXICATION` | Gap until V4 runs (four `Base.BeerCan`, as the model); #2950 (DayLength 1) is the existing reading. |
| S6b-m-bac | mod | kernel | kernel replay: `drink` Beer 0.3 L × 4 over an hour; path the record's blood alcohol (`acute.bac` or its name in `NR_Kernel_Acute.lua`, Task 4) | proof_run `x161f-20261006-055908` (#3086) and x151r (#2983). |
| S6b-m-intox | mod | kernel | the same replay, the stand-in's `INTOXICATION` (the writer's target, `K.effects.intoxTarget`) | #3086. |
| S6b-m-hangover | mod | kernel | the same replay to 24 h, the hangover state | No live reading of a hangover exists yet; M2 reads it (G10). Kernel source `K.acute` hangover state (`test_kernel_acute.py` `test_hangover_starts_counts_down_and_ends`). |
| S6c-m-kernel | mod | kernel | kernel replay with `sleep_allowed=True`: nights 23:00–07:00 except one 03:00–07:00, meals at "request"; paths `acute.debtH`, `HUNGER` | proof_run `x30-grade-20261011` (#3677: bookings and debts equal to the kernel; the sleep factor within 0.00549). |
| S6c-m-live | mod | live | `x30-grade-20261011/rows.json` `row11.nights[i].booked_h`, `row11.closes[i].debt_after` (#3677) | Plan 11f build, before the 11g satiety rework: the bookings and debts (not HUNGER) are drawn after the admission test on the sleep kernel; M2 re-reads them at HEAD. |
| S6c-v-model | vanilla | vanilla-model | VM14: no sleep term on hunger (#0475): factor 1 | |
| S6c-study | — | study | S1566 (intake and hunger the day after one 4 h night) | |

### Systems reference

| id | side | badge | source | notes |
|---|---|---|---|---|
| SN1-m-vitC, -fibre, -iron, -sodium | mod | kernel (provenance `dataset`) | `data/food-nutrients.json` `items[pz_id = X].per_item.vitC`, `.fibre`, `.iron`, `.sodium` for H4's five foods | Four series; vanilla carries none of these. |
| SE1-m-live-liquid | mod | live | `x363-20261012-202827` ring `rows_list[k]["stomach.liquid"]` (water then milk; #3702, #3668) | Mod `7093079b`; the stomach kernel has not changed since (git log); admission test. |
| SE1-m-live-fill | mod | live | the same rows' `rows_list[k].stomachFill` | Sip rows: the `*_replay` values are do-not-cite. |
| SE1-m-kernel-fill | mod | kernel | the HEAD replay of x363's `events.json` from its `start.json`; `stomachFill` | |
| SH1-m-kernel | mod | kernel | `test_satiety_meal_studies.py`'s Callahan replay (the 190, 400, 825 kcal liquid preloads at 09:00) at HEAD | Its pins are 243, 266 and 329 min under the refit (the module's comment). |
| SH1-m-live | mod | live | `x36-grade-20261012/grade.json` `sessions.x361.readings.readings.C650_request_vs_anchor.live_min` (247.09) and `.C400_held_vs_180.live_min` (215.13) (#3700) | Admission test on x361. |
| SH1-study-1247 | — | study | S1247 (247, 286, 321 min) | |
| SH1-study-1248 | — | study | S1248 (320–425 min from a scheduled lunch to a freely requested dinner, Cummings 2004) | The 240–300 min anchor for a 650 kcal meal is #3700's, a reading of S1247 and S1248, not S1248's own value. |
| SH2-m-kernel | mod | kernel | the HEAD `replay_arm` of x276's six-meal events (`x276-20261010-143855/events.json`, from its `start.json`) against its three-meal arm (ruling 11f-3's arm protocol); mean HUNGER over the window | proof_run x276 (#3671), drawn as the line. |
| SH2-m-live | mod | live | `x27-grade-20261010/rows.json` `row8.mean_live_six`, `row8.mean_arm_three`, `row8.ratio_live` (#3671) | Plan 11f build (x276 at `983ebd6`), before the 11g rework: admission test; proof only if it fails. |
| SH2-study | — | study | S1608 (three against six meals) | |
| ST1-v-model | vanilla | vanilla-model | VM5, 10 h from 0 | |
| ST1-m-kernel | mod | kernel | kernel replay 10 h at rest, no drink, default body; `THIRST`, `fluids.thirstTarget` | Proof as S1c (G7). |
| ST1-m-live | mod | live | `x151t-20261005-183551/thirst.json` `records[51].fluids.dehydPct` (1.4369) and `records[51].fluids.thirstTarget` (0.2459) at 604.9 min (#2963) | An 80 kg female subject on the Plan 4 build: drawn only with that stated, or not at all (admission test cannot run on that build's records). |
| ST2-m-live-na | mod | live | `x28-grade-20261011/rows.json` `sodium.by_day.<d>.na_change_per_24h`, d 1–5 (#3688) | |
| ST2-m-live-plasma | mod | live | the same file's `sodium.by_day.0.naPlasma_min`, `sodium.by_day.5.naPlasma_max` | |
| ST2-m-kernel | mod | kernel | `testing/tests/kernel/test_sodium_balance.py` `simulate(days=5, na_day=0)` | |
| ST3-m-dry | mod | kernel | the same kernel replay as `S2d-m-dry` (no food and no water from a fresh record at 07:00, HUNGER 0, the mod's defaults; identical points and note); path the record's health | Plan 18 Task 5d (Angus's extra 2). The dehydration state opens at the 4 % deficit (32.88 h, Parched, #3908), starvation at 34.45 h; health is half gone at 83.83 h and gone at day 5.65, the fatal state dehydration on its straight line to a 17 % deficit (#4027). No live run reads it: x456 read the dehydration onset only (#3940). Checked in `test_mod_guide_series.py` with `S2d-m-dry`. |
| SM1-m-live | mod | live | `x343-20261011-165411` ring pages `rows_list[k].UNHAPPINESS` from the release's start to its end (`x34-regrade-20261011/rows.json` `row13.release.from_age` 110.30 to `.to_age` 161.67; 30 → 19.08, #3683) | |
| SM1-m-kernel | mod | kernel | the HEAD replay of x343's inputs (the x34-regrade twin) | |
| SB1-m-def-rest | mod | kernel | Strength day × 60, S 0, p 1.2, E −500 | proof x434. |
| SB1-m-def-train | mod | kernel | S 12, p 2.0, E −500 | |
| SB1-m-sur-rest | mod | kernel | S 0, p 1.2, E +500 | proof x435. |
| SB1-m-sur-train | mod | kernel | S 12, p 2.0, E +500 | |
| SB2-v-model | vanilla | vanilla-model | VM9 (#0155 bands by weight) for the three example bodies | |
| SB2-m-kernel | mod | kernel | `K.traits.axes(body, 1)` for the same bodies (#3856) | proof x436 (#3873). |
| SX1-v-model | vanilla | vanilla-model | VM6: kcal a game hour at 80 kg for asleep, idle, walking, running, sprinting, idle under `ISFitnessAction` (modifier 3, #2187), reading (0.5) (#0454–#0460) | |
| SX1-m-kernel | mod | kernel | `K.energy.COMPENDIUM` and the exercise MET table × 80 kg (the bill per class) | |
| SX1-m-live | mod | live | `x37-grade-20261013/grade.json` `sessions.x371.sets[i].bills[j].billed` (the live billed MET: squats 3, push-ups 3.8 ×3, sit-ups 3.8 ×3, burpees 7.5 ×3; #3730) | `sessions.x371.table[i].table_met` is the mod's constant echoed, used only as the label; `.billed_all` is a boolean, never cited. kcal a game hour = MET × 80 kg, a stated derivation. |
| SX2-v-model | vanilla | vanilla-model | VM2: exercising with the food-eaten moodle down, hunger rises at 6.4e-6 a game-second, below idle (#0471) | |
| SX2-m-live | mod | live | `x29-gate-20261011/rows.json` `row9.decay[0].S_30min_after_set`, `.mm_30min_after_set`, `row9.half_life_h` (#3675) | |
| SX2-m-kernel | mod | kernel | kernel replay of a Fitness set (an `activity` event `{exercising: true}` with a `setpath` of `_G.NutritionRevamp.server.fitness.exeType.admin` to `"burpees"`, 30 min) then rest; `satiety.S`, `HUNGER` | Task 4 checks that the bill reads 7.5 MET. |
| SS1-m-kernel | mod | kernel | Strength day × 365 at S 0, 3, 6, 10, 15, 20; p 1.6; E +260 | |
| SS1-v-model | vanilla | vanilla-model | VM11 at the same weekly sets | |
| SD1-m-live | mod | live | `x161b-20261006-065751/body.json` `summaries.I.health.per_game_h` (−0.59850) and `health_reads[53].overall`, `health_reads[70].overall` (#3106) | Plan 5 build; the effects kernel has not changed its drains since (git log). Task 4 fix 1 (review I-6): the series draws the measured span alone, health_reads[53] to [70]. |
| SD1-m-kernel | mod | kernel | `K.effects.drain` at clinical vitamin C held 30 days (`vitC.ah` ≥ the lethal threshold), integrated to health 0 | The 168 game hours to death are a game choice; S1168 is open (direction only), so no study series is drawn. |
| SD2-m-marginal | mod | kernel | per record of `NR_Data_Nutrients`/`K.nutrients`, zero intake from replete at OnsetSpeed 1 (`K.nutrients.stepPool`, `K.nutrients.grade` per day): days to grade 2 | The `test_kernel_nutrients.py` `test_step_pool_zero_intake_40_days` pattern. |
| SD2-m-clinical | mod | kernel | the same, days to grade 4 | |
| SD2-study | — | study | each record's own onset row (its science id in the record file) | Task 4 lists them. |
| SC1-m-live-booked | mod | live | `x30-grade-20261011/rows.json` `row11.nights[i].booked_h`, i 0–3 (#3677) | Plan 11f build: the sleep booking predates no rework of its own, but the run is pre-11g; admission test on the sleep kernel, M2 re-reads at HEAD. |
| SC1-m-live-debt | mod | live | the same file's `row11.closes[i].debt_after` | |
| SC1-m-kernel | mod | kernel | `K.acute.sleepMinute` over the same nights | |
| SV1-m-kernel | mod | kernel | `K.view.fullnessLevel(mass)` (`NR_Kernel_View.lua:537`) for 0–1200 g (#3623) | It calls `K.satiety.discomfort` with `CAPACITY_MAX_G` and `CAPACITY_HARD_G` and maps the 0–100 scale to levels 0–4; `discomfort` alone is not the moodle level. |
| SV1-m-live | mod | live | `x401-20261013-152929/accept.json` `verdicts.OF.observed.rows[i].server_mass` with the client levels 3, 4, 4 (#3778) | Staged copy of mod `fdd7767f` (Plan 11b); admission test before drawing. |

Series by badge: live 26, kernel 65, vanilla-live 11, vanilla-model 31, study 14; 147 in all, H4's two rows and
SN1's one row each counting as four series. The vanilla-live 11 are gaps until V1–V4 run, except S2d-v-live-weight.

Task 4's outcome (2026-10-15, after fix round 2): 127 series built, 12 pending on Task 8's runs (`PENDING_LIVE` in
`tools/mod_guide_series.py`: the vanilla-live gaps but S2d-v-live-weight, and S1b-m-live and S1c-m-live for M1, x446), 8 dropped (`DROPPED`: S2a-m-live,
S2b-m-live, SH2-m-live, SM1-m-live, SX2-m-live and ST2-m-live-plasma fail the G8 admission test on the quantity they
draw; ST1-m-live cannot take it; S2d-m-drain has no register row for its condition, G16). Admission grades each drawn
quantity at the run's own tolerance or a named game choice (the I-3 ruling): x364's THIRST and level-change ages pass,
but S1c-m-live and S1b-m-live wait on M1, whose fresh HEAD record matches the kernel lines (ruling N-2; their
x364 records stay in VALIDATION, marked superseded by M1). The admission and viability results are the data file's `validation` block.
S3b-m-live-U and -B keep days 0-4 (x341, x342); x343's days 5-6 fail the test.

## 3. Promises

| text | support | status |
|---|---|---|
| **No longer happens:** in Managed mode hunger never reaches the top Hungry moodle, so hunger never kills | #3123 (the cap at 0.69 and 0.83), #3074 (HUNGER ≤ 0.69 live on an empty stomach), #0508, #0516 | supported |
| **No longer happens:** in Managed mode thirst never reaches the top Thirst moodle, so thirst never kills (the deficiency drains still can) | #3123, #3103 (THIRST stops under level 4 live), #3011 | supported |
| **No longer happens:** a food's hunger value sets your hunger; a zero-calorie item no longer sates | #3614 (hunger from the stomach and the meal pool), #0503 (vanilla's coupling) | supported |
| **No longer happens:** hunger drops to zero after a meal | x361 `readings.courses.C650.nadir.live.HUNGER` (0.12539), README limitation "never reaches 0" | supported (needs a register row for the nadir: the leaf exists, no claim) |
| **No longer happens:** an idle character gains weight on 1500 kcal a day | H2-v-model (#0149, #0455) against H2-m-total | supported after Task 4 (series) |
| **No longer happens:** Strength experience levels you up; a year or so of grinding takes you to 10 (level 10 on about day 292 with the protein factor 1.5; level 9 at the year's end without) | #3851 (XP is the training signal), #3871 (the level follows the body), H3 series | supported |
| **No longer happens:** weight-band traits follow the scale; a muscular heavy character is no longer Overweight | #3856 (the fat axis scaled by lean), #3873, #0155 | supported |
| **No longer happens:** a thin or fat trait changes only the scale | #3874 (a thin start is hungry), #3872 (the bodies) | supported |
| **No longer happens:** Strength stays forever without training (vanilla's rust is one XP a step) | #2151, #2155 (vanilla), S4c-m-kernel (mod) | supported by series; the detraining arm has no live reading (G14) |
| **Can happen:** you get hungrier as you lose fat | S2c (S1254), #3874 | supported |
| **Can happen:** a missed day makes you eat about a fifth more the next day | #3670 (1.2141 live), S1613 | supported |
| **Can happen:** scurvy and the other deficiencies on a one-food diet | #2978 (crossings where the kernel puts them), #3106 (the drain), S3a series | supported |
| **Can happen:** after a month at clinical scurvy, untreated scurvy kills in about a week (a game choice) | #3106 (−0.598 health a game hour); S1168 open (direction only) | supported as a game choice |
| **Can happen:** a total fast kills (`NR.DeficienciesCanKill` on). At HEAD the starvation drain fires on its BMI-under-12 branch (about day 62 of a fast with water), not on "fat reserves gone": the fat share rises on a fast (20.0 % at creation, 21.6 % at the death on day 27, 26.4 % by day 90) and never meets the 4 % floor; and the first killer on a fast with water is cardiac beriberi (thiamine, lethal code 3) at day 24, dead by day 27 (S2d-m-mass) | README; #3105 (the dial); S2d-m-mass (kernel, ends at the death) | reworded (Task 4 fix 1, the I-8 ruling); the starvation clause needs a C row of the BMI branch read off `K.effects.drain` (G16, S2d-m-drain stays dropped until then). Mechanism candidate for Angus: the fast takes 84 % of its loss from lean (52.0 to 18.8 kg over 90 days) |
| **Can happen:** eating one food lowers mood to the first Unhappy and Bored level, and varying it lifts it | #3683 | supported (inference: the stat against #2369's level-1 thresholds; BOREDOM read as the remembered target `moodLast_b`, not a moodle read) |
| **Can happen:** long starvation puts you at refeeding risk | #3875 (refeeding risk 2 at a Weak and Gaunt start), #2987 (the risk state; `refeedEvent` false, no event) | supported as reworded; the sickness event itself (`K.acute.refeedEvent`) has no reading and is not promised |
| **Can happen:** a hangover after heavy drinking | M2 (to run), kernel test `test_kernel_acute.py` `test_hangover_starts_counts_down_and_ends` | dropped from the page unless M2 reads it (ruling G17); restored by an M2 claim |
| **Can happen:** coffee works less well when you drink it every day | #3077 (the offset follows caffeine and its tolerance live), S6a kernel series | reworded to the tolerance alone; withdrawal dropped (no reading) unless M2 reads it |
| **Can happen:** a short night raises the next day's hunger | #3677, #3638 | supported |
| **Can happen:** Night Vision from a long, well-stocked vitamin A and zinc intake | #3093, #3095 | supported |
| **Can happen:** Short Sighted at a clinical vitamin A deficiency | #3098 | supported |
| **Can happen:** on a salt-free diet the body loses sodium slowly and holds its blood sodium | #3688 (−8 mmol a day, plasma 140.07–141.49, grade 0 over five days) | reworded (ruling G17); "low blood sodium drains health" dropped |
| **Can happen:** an iron overdose makes you sick | #3084 (the excess rung drives food sickness) | supported as reworded; "drains health" dropped (ruling G17) |
| **Can happen:** overeating raises the Overfull moodle and never blocks an eat (vanilla still refuses at its own food-eaten level 3) | #3623, #3778, #0521, #2889 | supported |
| **Can happen:** a protein-rich, trained, fed body grows toward a natural cap no one passes | #3853, S1915, S4b series | supported |
| **Can happen:** a muscle start fades toward its set point when idle (an idle Strong settles in the Stout band) | #3855 (the half share), S5b-m-strong-level | supported after Task 4 (series) |
| **Can happen:** every nutrient replete speeds sleep's recovery 5 % (`NR.BalanceBonus`) | README only | dropped (ruling G17) |

## 4. The vanilla model's formulas (Task 2)

| name | formula | claim ids or jar target |
|---|---|---|
| VM1 hunger awake | dH/dt = 9.6e-6 × StatsDecrease mult × (1 − H) × appetite trait, per game-second; 0 while the food-eaten timer > 0 and not exercising | #0470, #0474, #0489, #0490, #0473, #0524, #0525, #0483, #2773 |
| VM2 hunger exercising and asleep | exercising: 6.4e-6 (moodle down), 1.92e-5 (moodle up); asleep 1.0e-6 × (1 − H) | #0471, #2774, #2775, #0472, #2783, #0498 |
| VM3 the food-eaten timer | after an eat, only if HUNGER is at its minimum: timer += abs(hungerChange) × f × 13000, ×2 cooked, cap 11 000; decays (the day length in real minutes)/30 units a game-second (3.0 at DayLength 4, a 90-minute day); moodle level 1 above 0 | #0054, #3597, #0503, #0530, #0529, #0511, #0528 |
| VM4 the eat | HUNGER += hungerChange × f (state-modified: cooked ×1.3, stale ÷1.3, rotten ÷2.2, burnt ÷3), clamped [0, 1]; script ÷100 | #0006, #0011, #0021, #0029–#0032, #0003 |
| VM5 thirst and its moodles | dT/dt = 8.0e-6 awake, 1.0e-6 asleep, linear; water −50 a litre (0.5 THIRST); HUNGRY at 0.15/0.25/0.45/0.70, THIRST at 0.12/0.25/0.70/0.84, strict | #0476, #0477, #0491, #0496, #2765, #2766, #2928, #0508, #0509 |
| VM6 calorie burn | per game-second × (weight/80): asleep 0.003, idle 0.016, walking 0.078, running 0.13, sprinting 0.169, idle under an action × its caloriesModifier (Fitness 3, reading 0.5, building 8); thermoregulator energy ≥ 1 (taken as 1) | #0453–#0461, #0187, #0462, #2187, #2720, #0464, #0456 |
| VM7 the stores | calories += item kcal × f at the eat; carbohydrate, lipid and protein drains 0.0035, 0.00113, 0.00086 a game-second; clamps calories [−2200, 3700], macros [−500, 1000] | #0036, #0069, #1193, #0168, #0022, #0023 |
| VM8 weight | gain above 1000 + (w − 80) × 40 at 1.3e-5 × min(1, cal/4000) kg/s, ×3 / ×2 above 700 / 400 g of carbohydrate or fat; loss below min(0, (w − 70) × 30) at 8.5e-6 × min(1, \|cal\|/2500) | #0149, #0151, #0152, #0153, #0154, #0161, #0166; validated #0158, #0159, #0160, #0164 |
| VM9 weight bands and creation weights | bands by weight inclusive at both ends; creation weights 105, 95, 70, 60, 50; none 80 | #0155, #0531, #3069, #0533, #0534 |
| VM10 starvation and health | HUNGRY 4 costs 3.564 health a game hour at DayLength 4 (THIRST 4: 17.82); tier 3 regenerates nothing; asleep at level 4 adds nothing | #0516, #0518, #0519, #2353, #2354, #2721, #0515, #2385 |
| VM11 Strength experience | 360 XP a push-up set to exhaustion (6 a rep); ×1.5 at protein 50–300, ×0.7 below −300; × the sandbox multiplier; thresholds 1500 … 487 500; nothing past level 10; dropped while asleep | #3844, #2112, #3835, #3836, #2102, #2109, #2122, #2161, #2874 |
| VM12 rust | −1 XP each 1200-unit bucket once the rust timer passes 20 000; timer +10 a ten minutes, −3000 a positive grant, floor −50 000 | #2151, #2152, #2154, #2155, #2156, #2868 |
| VM13 trait start levels | start at 5, then each muscle trait's Strength boost (and the band remap on LevelPerk) | #2104, #2157; **JT1** for the boosts |
| VM14 what hunger does not read | the hunger multiplier is a hard 1.0; no fatigue, sleep-debt, weight or calorie term | #0475, #0501, #0500, #0488 |
| VM15 coffee | FATIGUE += fatigueChange × litres (Coffee −10 a litre); held only with sleep allowed and needed | #2949, #2270 |
| VM16 intoxication | the fluid writer adds 400 × alcohol × (1.1 above 0.8 HUNGER, 1.25 between 0.6 and 0.8); Beer 0.05 a litre; decay 0.0042 × the multiplier a tick = 0.504 × the day length in real minutes a game hour (45.36 at DayLength 4) | #2923, #2926, #2919, #2922, #2918, #2950, #2951 |

**JT1 (the one jar or script read Task 2 needs).** The Strength boost each vanilla muscle trait gives at creation
(Weak, Feeble, Stout, Strong) and how `applyTraits` turns it into the start level: the install's body-trait script
blocks (the ones `mod/NutritionRevamp/common/media/scripts/NR_Traits_Body.txt` restates, #3860) for their `XPBoost`
Strength lines, and `./pz.sh dump IsoGameCharacter applyTraits` for the arithmetic (#2104 reads the seed of 5).
The mod's README states the outcome (Weak 1, Feeble 3, none 5, Stout 7, Strong 9) and #3855 cites it as a game
choice; x436 read Strength 9 and 1 live under the mod (#3872). A vanilla C row is minted by Task 2.

## 5. Sessions

All vanilla sessions: fixture `default` (build 42.21.0), **PZTestKit only, no NutritionRevamp and no TKX probe**,
`Nutrition = true` (the fixture's value; the verify row of `testing/profiles/x13-nutrition-on.toml`), DayLength 4
(the fixture's own; no sandbox key needed), one `admin` client (-debug). The precedent profile boots with PZTestKit
alone (x13-nutrition-on, `scenario-20261004-190146`). Every session: `python testing/pzt doctor`, free memory read
and ledgered (≥ 12 GB), a foreground polling wait (CLAUDE.md § 5), the artifact committed with its row, guide and
do-not-cite keys. Clock: RCON `settimespeed 30` (8 game minutes a wall second at DayLength 4, measured
7.99 in the x13 scenarios) between events, `settimespeed 1` around every eat and drink (a networked eat ends in real
time, about 10 s, #3766), `time.multiplier` as the server fallback; the driver restores the clock from the value it
read (CLAUDE.md § 5). Fixed cost per session about 3 min (doctor, seed, boot 41 s + client 38 s from the fixture's
timings, teardown and copy).

| id | purpose | readings | game hours | multiplier | wall estimate | harness commands |
|---|---|---|---|---|---|---|
| V1a | H1, S1c: a measured meal | arm A: `stats.set admin hunger 0.25 thirst 0`, eat `Base.CannedBologneseOpen` whole, 6 h; arm B: `stats.set admin hunger 0.10`, eat a second can (HUNGER to 0, timer filled), 2 h. HUNGER and THIRST every game minute; in arm B's first 25 game minutes, every 10 s at speed 1, `stats.get admin` (`foodTimer`, `standardFoodTime`) beside `moodle.level admin FOOD_EATEN`; `nutrition.get` hourly | 8.5 | 30 (1 around eats and arm B's first 25 min) | ~6 min | `minute.ring admin start` / `read` / `stop` (no paths), `stats.set`, `stats.get`, `eat.action` (client), `item.spawn` or RCON `additem`, `moodle.level admin FOOD_EATEN`, `nutrition.get`, `stats.all`, `time.snapshot`, `time.multiplier` (no `foodtimer.set`: it always writes) |
| V1b | S1b, S2a, S2d: starving to death | `stats.set admin hunger 0.60 thirst 0`, no food; `stats.set admin thirst 0` hourly (a control: hunger and thirst are independent, #0500, #0501); HUNGER every minute; `health.get` and `nutrition.get` hourly; `moodle.level admin HUNGRY` hourly; until death (predicted: level 4 at +8.3 h, health 0 about 28 h later) | ~37 | 30 | ~8 min | `minute.ring`, `stats.set`, `health.get`, `nutrition.get`, `moodle.level`, `time.snapshot` |
| V2 | H2, S1a, S3b: one food for 36 hours, as two sessions on one world (x443a day 1, x443b day 2 by a reuse boot of x443a's world; the controller's ruling on the Task 5 review's concern 3) | x443a: `nutrition.set admin calories 3000` and `weight 80` at the start (the values read first), so the gain branch runs from hour 0 (above the 1000 kcal threshold at 80 kg, #0149; rate 1.3e-5 × min(1, cal/4000) kg a game-second, #0152); the anchor is the world age read after the writes; the 36-h weight change predicted by the vanilla model before the run; `Base.TunaTinOpen` at the anchor + 0, 4, 8, 12 (x443a) and + 24, 28, 32 (x443b), relative because the DL4 sessions start near world age 2.35, past 08:00 (Task 5 review M-11); HUNGER, BOREDOM, UNHAPPINESS every minute; the store hourly (the Nutrition fields through `stats.get`, atomic with its age); `stats.set admin thirst 0` every 6 h from the anchor. x443b refuses a short or faulted x443a (its chain check) | 36 (the anchor to the anchor + 18, then + 18 to + 36) | 30 (1 around eats) | ~5.5 min each (BUDGET_S 420 each; 18 h of clock about 2.2 min, the eats at speed 1, the boot and teardown) | `minute.ring`, `nutrition.set`, `stats.get`, `eat.action`, `stats.set`, `stats.all` |
| V3 | H3, S4: Strength experience | push-up sets to exhaustion at speed 1 with `stats.set admin endurance 1` before each: A `nutrition.set admin proteins 0` (control, expect +360); B, in this order: `perk.park admin Strength 5` (37 500), then `xp.grant admin Strength 29700` **while the protein store is still 0** (giving 67 200, 300 under level 6's 67 500, #2102; `xp.grant` goes through `addXp`, so the protein factor would apply to it), then `nutrition.set admin proteins 100`, then the set (expect ×1.5 = 540 and a crossing to level 6 with STOUT); C `nutrition.set admin proteins -400` (expect ×0.7 = 252). XP and level before and after each (`perk.xp`); the trait list after B from `stats.get admin` (`traitList`), and optionally `trait.watch STOUT <s>` on the client | ~1.5 | 1 | ~8.5 min | `exercise.do pushups 10` (client), `perk.xp`, `perk.park`, `xp.grant`, `nutrition.set`, `stats.set`, `stats.get`, `trait.watch` (client, optional), `time.snapshot` |
| V4 | S6a, S6b: coffee and beer | profile `[server] SleepAllowed = true`, `SleepNeeded = true` (fatigue holds only then, #2949); A: `stats.set admin fatigue 0.5`, 0.25 L Coffee (`fluid.fill` a bottle, `drink.action`), FATIGUE before and after and for 1 game hour; B: four `Base.BeerCan` drunk back to back (as S6b's model and kernel), INTOXICATION polled every 2 s until 0 | ~1.5 | 1 | ~7 min | `fluid.fill`, `drink.action` (client), `stats.set`, `stats.all`, `time.snapshot` |

The ruling runs V1a, V1b, V2, V3, V4, M1 and M2. V2 runs as x443a and x443b on one world (the controller's ruling on
the Task 5 review's concern 3), so every session's whole call stays under about 9 min and none needs a detached
launch.

**Modded gap runs (both to run, ruling).**

| id | purpose | readings | game hours | multiplier | wall estimate | harness commands |
|---|---|---|---|---|---|---|
| M1 | Re-prove the hunger and thirst pipeline at HEAD after Plan 13's body switch and the 11g rework; the first THIRST graded against a replay (G7, G8) | staged copy of mod/ at HEAD (`tools/release_pack.py stage`), DayLength 1, `Nutrition = false`; fresh record carrying no filled fluid container (as x364; `setAutoDrink(false)` does not hold, #2941, so `autodrink.set` is not used); at the first request eat `Base.CannedBologneseOpen`; then no food for 24 h, the driver logging any `fluids.autoDrop` off the ring as `autodrop` events; ring paths HUNGER, THIRST, `satiety.*`, `stomachFill`, `fluids.*`, `body.fm`, `body.lm`, `body.energyState`, the bus signature; the replay graded HUNGER 0.002, es 0.005 and THIRST at a tolerance named before the run | ~32 | speed 5 (as x364) | ~8 min | `minute.ring` with paths, `eat.action`, `lua.read`, `stats.all`, `time.snapshot` |
| M2 | Live proof at HEAD for S6: caffeine and its tolerance offset, blood alcohol, the hangover and the sleep factor (G10, G15, G17) | sleep on; three coffees and four beers on day 1, a 4-hour night, meals at the request on day 2; ring paths the acute caffeine, blood alcohol, hangover, `acute.debtH` | ~30 | speed 5 | ~8 min | as M1, plus `drink.action`, `fluid.fill`, `player.sleep` |

## 6. Gaps

| id | gap | fill |
|---|---|---|
| G1 | Vanilla hunger after a real eat at the default DayLength: the timer's fill gate (`isAtMinimum`) is C-only (#3597, #0054) and every measured freeze came from a timer write (#0524) | V1a |
| G2 | Vanilla death by hunger was never measured (the one death was thirst, #0173; hunger stopped at 0.6999, #0174) | V1b |
| G3 | Vanilla weight under real eats: every weight run drove `setCalories` (#0170) | V2 from a store of 3000: it validates the store's arithmetic and the gain rate over 36 h, not 30 days of drift |
| G4 | Vanilla Strength: the protein factors (#2112) and a live level crossing with its band trait (#2157) are C-only | V3 |
| G5 | Vanilla intoxication and coffee at DayLength 4 (#2950, #2951 ran at DayLength 1) | V4 (ruled to run) |
| G6 | Vanilla muscle-trait start levels have no vanilla claim | JT1 (Task 2) |
| G7 | THIRST was never graded against a replay; the mod's thirst proof is x151t on the Plan 4 build, before the 2026-10-10 sodium changes | M1 (ruled to run) |
| G8 | Every mod hunger proof run (x27x–x36x) predates Plan 13's creation body and low-fat ramp, and x27x, x276 and x30x also predate Plan 11g's satiety rework; old start records may not load at HEAD (no-compatibility rule) | Task 4's admission test (ruled); M1; the pre-11g charts are kernel lines with the old runs as proof only |
| G9 | The guide's foods were never eaten in a mod live run (x361–x364 ate study foods) | covered by kernel replays with the item-pass vector (Task 4 asserts the landed vector equals the record, as #3182) |
| G10 | Caffeine, alcohol and hangover proof runs (x151r, x151r2, x161f) are Plan 4–5 builds; a hangover was never read live | M2 (ruled to run) |
| G11 | Vitamin C onset cannot be read live (never scaled by OnsetSpeed); the pool proof is x151r on the Plan 4 build | kernel badge with x151r as proof; stated |
| G12 | H4 and SN1 read dataset records, which fit none of the four provenance kinds | Ruled: a fifth provenance kind `dataset` {file, key}; the game's values take the badge vanilla-model, the mod's generated values the badge kernel (closed) |
| G13 | Strength over years has live proof only at the biology clock 30 over 2 to 4 closes (x434, x435) | kernel badge; stated |
| G14 | The detraining, regain and peak arms of the Strength day were never closed live | kernel badge with the oracle studies (S0618, S0078); stated |
| G15 | The sleep factor's live run (x30x) is the Plan 11f build, before the 11g rework | admission test; M2 (ruled to run) |
| G16 | The starvation drain (fat gone) has no live reading and no register row | kernel series S2d-m-drain plus a C row of its condition read off `K.effects.drain`; or M-run (a 90-day fast is out of a live session's reach) |
| G17 | Three README promises have no support: the hangover, the balance bonus and a health drain from low blood sodium or an iron overdose | Ruled: reworded or dropped in § 3 (the balance bonus and both health drains dropped, sodium and iron reworded, the hangover dropped unless M2 reads it); the README's same lines go to Task 11's fact check |

## Fix round 1

Applied from `.superpowers/sdd/2026-10-15-plan-14-mod-guide/task-1-review.md` (FAIL, 12 Important, 12 Minor) and the
ledger's rulings (G12, the sessions, G17, G8). Counts after the round: 39 charts; 147 series, kernel 65, live 26,
vanilla-model 31, vanilla-live 11, study 14.

| finding | what changed |
|---|---|
| I-1 | V3 reads the trait list with `stats.get admin` (`traitList`) after arm B; `trait.watch STOUT` optional on the client; `trait.check` removed. |
| I-2 | V3 arm B: `perk.park admin Strength 5`, then `xp.grant admin Strength 29700` at protein 0 (67 200), then `nutrition.set admin proteins 100`, then the set; the order and why stated; `xp.grant` added to the commands. |
| I-3 | V1a drops `foodtimer.set`; the timer is read with `stats.get admin` (`foodTimer`, `standardFoodTime`) every 10 s beside `moodle.level admin FOOD_EATEN`. |
| I-4 | SV1-m-kernel is `K.view.fullnessLevel(mass)` (`NR_Kernel_View.lua:537`), not `K.satiety.discomfort`. |
| I-5 | SX1-m-live cites `sessions.x371.sets[i].bills[j].billed`; `table_met` is the label only, `billed_all` never cited, the ×80 kg conversion stated as a derivation. |
| I-6 | S3a: S0967 dropped (superseded; S0210 open), S0224 and S0225 kept as two series. S4c: S0617 replaced by S0078, with its no-retraining-advantage finding stated. S6a's S0851 and S1123 and SD1's S1168 removed as study series, the half-life, the tolerance and the 168 h to death noted as game choices on open rows. The scurvy promise reworded to a game choice after a month at clinical. |
| I-7 | SH1-study-1248 reads S1248's own 320–425 min (Cummings 2004); the 240–300 anchor named as #3700's. |
| I-8 | S4b-v-model: about 42 weeks with the protein factor, about 62.5 without; the promise reads "a year or so". |
| I-9 | V2 starts its store at 3000 kcal, predicts the 36-h change before the run; H2-v-live and G3 say V2 validates the store's arithmetic and the gain rate, not 30 days of drift. |
| I-10 | § 0 and G8 name the Plan 11g satiety rework for x27x, x276 and x30x; SH2 gains SH2-m-kernel (the HEAD replay of x276's six-meal events against its three-meal arm) and SH2-m-live takes the admission test; S2b-m-live, S6c-m-live and SC1 marked proof only unless they pass. |
| I-11 | The refeeding promise reworded to "long starvation puts you at refeeding risk"; the event (`K.acute.refeedEvent`) not promised. |
| I-12 | M1 carries no filled fluid container and logs `fluids.autoDrop` as `autodrop` events; `autodrink.set` removed. |
| M-1 | The sleep-off default cites the harness profile-key row and #3009, not #2961. |
| M-2 | Leaves, not parents: x361 `nadir.live.HUNGER`; x151t `records[51].fluids.dehydPct`, `.thirstTarget`; x161b `summaries.I.health.per_game_h`, `health_reads[53].overall` and `[70].overall`; x436 `_xp.observed.client_level`, `.observed.xp`, `_body.observed.record.lm`, `.record.fm`, `.derived.mass`. |
| M-3 | § 0 states the ring's flat dotted keys and the bracket form; SE1's leaf rewritten; Task 3 told to match the longest key. |
| M-4 | § 0: x435 and x436 behaviour-preserving; x434 stands for the deficit partition only. |
| M-5 | SX2-m-kernel names `activity {exercising: true}` plus a `setpath` of `_G.NutritionRevamp.server.fitness.exeType.admin` to `"burpees"`; Task 4 checks 7.5 MET. |
| M-6 | S2b and S2c state "sleep on, the oracle's protocol". |
| M-7 | VM3, VM16 and S2d write "the day length in real minutes". |
| M-8 | V4 drinks four `Base.BeerCan`, as the model and the kernel. |
| M-9 | S6a-v-model states that it assumes sleep allowed and needed (#3009). |
| M-10 | S5b gains S5b-m-weak-level and S5b-m-overfat-weight. |
| M-11 | V2 is one 36-h session (ruling), re-estimated at about 9.5 min with the detached-launch fallback named. |
| M-12 | The mood promise is "supported (inference …)", BOREDOM read as `moodLast_b`. |
| Rulings | G12 closed with the `dataset` kind (H4, SN1 badges marked); sessions V1a, V1b, V2, V3, V4, M1, M2 all to run (V2a/V2b merged, M1 and M2 no longer optional); G17's three promises reworded or dropped (balance bonus dropped; sodium and iron reworded with their health drains dropped; hangover and withdrawal dropped unless M2 reads them); G8's admission test kept. |

## Plan 19 Task 8: Food mood

The Monotony topic became the divergence section "Food mood: what you eat and how you cook it" (`#sys-food-mood`), with
four changes (the stick of butter, cooking skill, hunger, taste class) and four new charts beside SM1, every number
read at generation time:

| chart | series | source |
|---|---|---|
| SM2 | SM2-v-model-U, SM2-m-kernel-U, SM2-v-model-B, SM2-m-kernel-B | `tools/hedonics_budget.py` `Oracle.rows()` (the reference diets over 14 days, the same eats on both sides): the mod's means off the oracle, vanilla's off VM17 over the oracle's own eats, the build failing if VM17 misses the oracle's vanilla side |
| SM3 | SM3-m-kernel | `K.hedonics.floorOf` on the registry's FLOOR_KNOTS, the plain share 0 to 1 by 0.05 |
| SM4 | SM4-m-scale, SM4-v-model, SM4-m-kernel | `K.hedonics.prepScale` at Cooking 0, 3 and 10; the oracle's sizing arm (both sides standing at its background) for the cooked diet at those levels |
| SM5 | SM5-v-model, SM5-m-kernel | `Base.Butter`'s UnhappyChange off `data/food-items.json`, and `K.hedonics.allies` full and just over the Hungry threshold |

VM17 (`tools/vanilla_model.py` `food_mood`) is vanilla's food mood: each eat adds UnhappyChange and BoredomChange times
the share eaten (#3655), nothing lowers UNHAPPINESS passively (#3033), an evolved dish carries its own value (#0298,
#4121), and the oracle's upkeep toward a standing background is the oracle's game choice on both sides. The proof runs
are x501-x504 (Plan 19 Task 7). Ruling T8-1: the cook's scale covers evolved dishes only, and the page says so.
