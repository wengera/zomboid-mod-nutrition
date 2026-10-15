# Plan 14 Task 1: the source map for the Nutrition Revamp player guide

Written 2026-10-15 at HEAD `10dfbc9b` (mod/ last touched at `498bd4a5`). This map is the run sheet for every later
brief of Plan 14 (ledger ruling): the charts, the source of every series, the promises, the vanilla model's formulas,
the vanilla-baseline sessions and the gaps. It cites register rows (`#NNNN`), science rows (`SNNNN`) and artifact
paths; it mints nothing.

## 0. Conventions every later task reads

**Display defaults (spec § 3.5).** Male, no traits, `NR.Mode` Managed, `NR.OnsetSpeed` 1, `StatsDecrease` 3
(×1.0, #0483), `DayLength` 4 (a 90-minute day, the fixture's and the game's default: `docs/platform/harness.md`
fixture table), and **sleep off** (`SleepAllowed`/`SleepNeeded` false, the dedicated-server default the fixture holds,
#2961; the mod README's Install section tells operators to turn them on for its sleep model). Only S6c and SC1 turn
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
"hunger": <script/100>, "foodType": …}` with the item pass's macros from `data/food-nutrients.json` `.per_item`;
Task 4 asserts that the vector the intake chain lands equals that record (as #3182 did live for an apple and
bread). Water for a long replay is `autodrop` events (grams). Measured speed: one game day of the server pipeline
takes about 0.34 s of CPU here (2026-10-15), so a 90-day replay is about 30 s.

**"Strength day"** means the kernel's own `K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)` stepped once a game
day on `server_host.Host`, from `K.body.new(K.body.create(muscle, weight, K.strength.DEFAULTS, sexIdx, profBoost),
sex, 0)`, the level read with `K.strength.level(body.lm, body.N0, body.T, P)` and the written perk with
`K.strength.heldLevel(L, Lw)` (the call pattern of `testing/tests/kernel/test_strength_day.py` `_days`). S is hard
sets a week, p protein g/kg/day, E the day's energy balance in kcal. The README's "perfect training" is S 20,
p 2.0, E +10 % of TDEE; with the strength oracles' TDEE 2600 that is E +260 (`strength_oracles.py` uses 0.05 × 2600
for its year-1 oracle: Task 4 names which it uses).

**Proof runs and the HEAD-replay admission test.** A kernel series names the live run that shows the replay
matches the game (`proof_run`). Most mod live runs predate Plan 13's switch to the creation body (`c7e816e6`) and
its low-fat hunger ramp (`31ce0635`, `c5139c31`). Their **live points** are drawn on a chart only when Task 4's
admission test passes: the HEAD kernel replay of that run's own inputs (its `start.json` and `events.json`, or a
fresh first sight with its event list where the old start record no longer loads under the no-compatibility rule)
reproduces the run's ring within the run's own graded tolerance (HUNGER 0.002, es 0.005; x361 guide's
`DEFAULT_TOL`). A run that fails the test stays as the proof run of the line and its points are not drawn.
x434, x435 and x436 ran on mod `c5139c31` and `0a6b0215` with only behaviour-preserving skews after them (their
guides' skew notes), so their points need no test for the Strength and creation series.

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
| S3a | S3 Living on one food | Vitamin C on tinned tuna alone | game days, 0–60 | vitamin C store (0–1) and grade | S3a-m-pool, S3a-m-grade, S3a-study |
| S3b | S3 | Mood on one food | game days, 0–7 | unhappiness, boredom (0–100) | S3b-m-live-U, S3b-m-live-B, S3b-m-kernel-U, S3b-v-live-U, S3b-v-live-B |
| S3c | S3 | What fixes it: an orange a day | game days, 40–80 | vitamin C store | S3c-m-pool, S3c-study |
| S4a | S4 A year at the gym | Strength by diet | game days, 0–365 | Strength level | S4a-m-perfect, S4a-m-lowprotein, S4a-m-deficit, S4a-v-model-x1, S4a-v-model-x07 |
| S4b | S4 | Ten years toward the natural cap | game years, 0–10 | Strength level | S4b-m-level, S4b-m-cap, S4b-v-model, S4b-study |
| S4c | S4 | Stopping and starting again | game days, 0–910 | Strength level | S4c-m-kernel, S4c-v-model, S4c-study-0618, S4c-study-0617 |
| S5a | S5 Choosing your body | The starting body of each pick | pick (none, Strong+Obese, Weak+Overweight, Overly Lean, Weak+Gaunt, Feeble+Overly Lean) | kg; Strength level | S5a-m-live-lean, S5a-m-live-fat, S5a-m-live-weight, S5a-m-live-level, S5a-v-model-weight, S5a-v-model-level |
| S5b | S5 | How each body drifts, untrained | game days, 0–90 | Strength level; kg | S5b-m-strong-level, S5b-m-none-level, S5b-m-gaunt-weight, S5b-m-none-weight, S5b-v-model-level |
| S5c | S5 | A thin start is hungry | game days, 0–30 | energy state (hunger drive) | S5c-m-gaunt, S5c-m-none, S5c-m-live, S5c-v-model |
| S6a | S6 Coffee, beer, no sleep | Caffeine and tolerance | game hours over day 1 and day 14 | caffeine in the body (mg); fatigue | S6a-m-day1, S6a-m-day14, S6a-v-model, S6a-study-0851, S6a-study-1123 |
| S6b | S6 | Four beers | game hours, 0–24 | intoxication (0–100); blood alcohol % | S6b-v-model, S6b-v-live, S6b-m-bac, S6b-m-intox, S6b-m-hangover |
| S6c | S6 | A short night and the next day's hunger | game days, 0–4 | sleep debt (h); hunger factor | S6c-m-kernel, S6c-m-live, S6c-v-model, S6c-study |
| SN1 | Nutrients and foods | What the five foods carry | food | mg or g per item | SN1-m-vitC, SN1-m-fibre, SN1-m-iron, SN1-m-sodium |
| SE1 | Eating and the stomach | A drink and a meal in the stomach | game minutes | grams; fill (0–1) | SE1-m-live-liquid, SE1-m-live-fill, SE1-m-kernel-fill |
| SH1 | Hunger | How long a meal holds hunger off | meal kcal | minutes to the hunger request | SH1-m-kernel, SH1-m-live, SH1-study-1247, SH1-study-1248 |
| SH2 | Hunger | Three meals against six | arm | mean hunger over 24 h (ratio) | SH2-m-live, SH2-study |
| ST1 | Thirst and salt | Ten hours at rest without a drink | game hours, 0–10 | thirst | ST1-v-model, ST1-m-kernel, ST1-m-live |
| ST2 | Thirst and salt | Five days without salt | game days, 0–5 | body sodium change (mmol/24 h); plasma sodium | ST2-m-live-na, ST2-m-live-plasma, ST2-m-kernel |
| SM1 | Monotony | Varying the diet lifts the mood | game hours after the last repeat | unhappiness | SM1-m-live, SM1-m-kernel |
| SB1 | The body | Lean mass at a deficit and a surplus, trained or not | game days, 0–60 | lean kg | SB1-m-def-rest, SB1-m-def-train, SB1-m-sur-rest, SB1-m-sur-train |
| SB2 | The body | Which weight trait a body gets | example body (lean 90 kg, average, soft 85 kg) | trait band | SB2-v-model, SB2-m-kernel |
| SX1 | Exercise and energy | Energy per hour by activity | activity | kcal per game hour at 80 kg | SX1-v-model, SX1-m-kernel, SX1-m-live |
| SX2 | Exercise and energy | Hunger after hard exercise | game minutes after the set | hunger | SX2-v-model, SX2-m-live, SX2-m-kernel |
| SS1 | Strength | A year's Strength by weekly sets | hard sets a week, 0–20 | Strength level after a year | SS1-m-kernel, SS1-v-model |
| SD1 | Deficiency and excess | Clinical scurvy and health | game days | health | SD1-m-live, SD1-m-kernel, SD1-study |
| SD2 | Deficiency and excess | How long each nutrient lasts with none eaten | nutrient | days to Marginal, days to Clinical | SD2-m-marginal, SD2-m-clinical, SD2-study |
| SC1 | Caffeine, alcohol and sleep | Short nights build a sleep debt | night | hours slept; debt (h) | SC1-m-live-booked, SC1-m-live-debt, SC1-m-kernel |
| SV1 | What you see on screen | The Overfull moodle | grams in the stomach | moodle level, 0–4 | SV1-m-kernel, SV1-m-live |

H1–H4 are the spec's headline charts; the At-a-glance comparison table is a table, not a chart. The Systems section
"the body traits and character creation" links to S5a–S5c and carries no chart of its own.

## 2. Series (146)

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
| H2-v-live | vanilla | vanilla-live | V2 `nutrition.get` replies, hourly `weight` (and `calories`) | Gap until V2 runs; V2 eats four `Base.TunaTinOpen` a day (1480 kcal), which vanilla's weight reads the same way (calories only, macros only as multipliers above 400 g, #0180, #0153). |
| H2-m-fat | mod | kernel | kernel replay 30 days: `meal` events size 500, `comp` MIXED at 07/12/18, `autodrop` 600 g at 08/12/16/20; path `body.fm` read at each 07:00 day close | proof_run `x434-20261015-053645` (#3869: deficit closes equal to the kernel's replay of their inputs) and `x435-20261015-101839` (#3870). |
| H2-m-lean | mod | kernel | the same replay, `body.lm` + `body.lx` | Same proof. |
| H2-m-total | mod | kernel | the same replay, `body.fm` + `body.lm` + `body.lx` (the weight the mod writes, README "The body") | Same proof. |
| H3-v-model-x1 | vanilla | vanilla-model | VM11: start level 5 at 37 500 XP (#2874), +360 XP a set (#3844) × 20 sets a week spread daily, thresholds #2102, cap #2109, protein factor 1 | A pure extrapolation of one measured set. |
| H3-v-model-x15 | vanilla | vanilla-model | VM11 with the protein factor 1.5 (protein store between 50 and 300, #2112) | #2112 is C-only; V3 measures it. |
| H3-m-level | mod | kernel | Strength day × 365 from the no-pick body, S 20, p 2.0, E +260, tdee 2600, ts 1; `K.strength.level` each day | proof_run x435 (#3870, #3871) and x434 (#3869). |
| H3-m-written | mod | kernel | the same run, `K.strength.heldLevel` day by day (the perk the player sees) | #3871 (the level write rises at the whole number live). |
| H4-v-kcal, -carb, -fat, -pro | vanilla | vanilla-model (see G12) | `data/food-nutrients.json` `items[pz_id = X].vanilla.calories`, `.carbohydrates`, `.lipids`, `.proteins` for X in `Base.Apple`, `Base.Bread`, `Base.CannedBologneseOpen`, `Base.Burger`, `Base.TunaTinOpen` | The 42.21 scan of the game's own scripts (`data/food-items.json`, the 2026-10-08 scan, CLAUDE.md § 2). Four series. |
| H4-m-kcal, -carb, -fat, -pro | mod | kernel (see G12) | the same records' `.per_item.calories`, `.carbs`, `.lipids`, `.proteins` (generated with `NR_ItemPass_Food.txt` by `tools/food_nutrients.py`, gated by its `--check`) | proof: x172b (#3182, #3183: a whole Apple and Bread landed the table's vector live). Four series. Burger's carbohydrate 0 → 46.65 g and tuna's protein 15 → 54.44 g are the chart's story. |

### Scenarios

| id | side | badge | source | notes |
|---|---|---|---|---|
| S1a-v-model | vanilla | vanilla-model | VM1, VM3, VM4: HUNGER 0 at 07:00, `Base.TunaTinOpen` (−0.18) at 08, 12, 16, 20 | |
| S1a-v-live | vanilla | vanilla-live | V2a ring `rows_list[k].HUNGER` | Gap until V2 runs. |
| S1a-m-kernel | mod | kernel | kernel replay 24 h from a fresh default record at 07:00, eats `Base.TunaTinOpen` at the same clock | proof_run `x362-20261012-201625` (#3703, a maintenance day and a surplus day replayed within 2.1e-4) and x361. |
| S1b-v-model | vanilla | vanilla-model | VM1 + VM5's moodle thresholds: HUNGRY level from HUNGER 0, 36 h | Levels at 4.70, 8.32, 17.30 and 34.84 game hours (#0492–#0495). |
| S1b-v-live | vanilla | vanilla-live | V1b ring HUNGER → level (#0508 thresholds), plotted at the model-equivalent time of its 0.60 start | Gap until V1 runs. |
| S1b-m-kernel | mod | kernel | kernel replay 36 h, fresh default record, no food; path `_G.NutritionRevamp.server.bus.lastSig.admin` → energy level (the thousands digit, as `test_replay_live_energy.py` `long_fast_levels`) | proof_run `x364-20261012-203308` (#3705) and `x405-20261013-155742` (#3792). |
| S1b-m-live | mod | live | `x36-grade-20261012/grade.json` `sessions.x364.readings.ring_levels.changes[i].age` (i 0, 1) less `x364-20261012-203308/start.json` `rec.firstSeen`: level 1 at 8.37 h, level 2 at 20.86 h after first sight | Drawn only if x364 passes the admission test (its body was the pre-Plan-13 80 kg split). |
| S1c-v-model | vanilla | vanilla-model | VM5: THIRST from 0 at 8.0e-6 per game-second, linear (#0476) | Level 1 at 4.17 h, level 4 at 29.17 h (#0492, #0495). |
| S1c-v-live | vanilla | vanilla-live | V1a ring `rows_list[k].THIRST` (8.5 h, unpinned) | Gap until V1 runs. |
| S1c-m-kernel | mod | kernel | kernel replay 24 h, fresh default record, no drink; paths `THIRST`, `fluids.thirstTarget` | proof_run `x151t-20261005-183551` (#2963, ten hours at rest equal to the kernel) — on the Plan 4 build: see G7. |
| S1c-m-live | mod | live | `x364-20261012-203308` `minute-ring-admin-{1,721,1441,1974}.json` `rows_list[k].THIRST`, `.age` (32 h, no drink) | THIRST was never graded against a replay in any run (G7); drawn only after the admission test with THIRST added. |
| S2a-v-model | vanilla | vanilla-model | VM1, VM3, VM4: day 0 meals `Base.CannedBologneseOpen` at 07/12/18 with a last eat at 20:00 to HUNGER 0 (timer filled), no food for 36 h, then the same meals | |
| S2a-v-live | vanilla | vanilla-live | V1b ring HUNGER from its 0.60 start, placed on the model's curve | Gap until V1 runs. |
| S2a-m-kernel | mod | kernel | kernel replay of `test_replay_live_oracle.py` `fast_plans()`'s fast arm on the default body (warm days, day 0 "maint", day 1 skipped, days 2–3 "request"), sleep off; paths `HUNGER`, `body.energyState` | proof_run `x27-grade-20261010` (#3670) and x364 (#3705). |
| S2a-m-live | mod | live | x364 ring `rows_list[k].HUNGER` (a 32 h fast from a fresh record) | Admission test. |
| S2b-m-kernel | mod | kernel | `test_replay_live_energy.py` `fast_server()`'s ratios `r2`, `r3` (the oracle's 70 kg man, `MAN`) | The default-body variant is Task 4's choice; the oracle's body is the one its bands were fitted on. |
| S2b-m-live | mod | live | `x27-grade-20261010/rows.json` `row6_7.ratios.2.live`, `row6_7.ratios.3.live` (1.2141, 0.9512; #3670) | Plan 11f build; graded against its own replay (`.replay` 1.2016, 0.9641), so the points are the live ones of that build — admission test on the x27x rings before drawing. |
| S2b-study-1613 | — | study | S1613 (Johnstone 2002: 1.20 on the day after a 36 h fast) | |
| S2b-study-1614 | — | study | S1614 (Clayton 2016: 1.0 on day 3) | |
| S2c-v-model | vanilla | vanilla-model | VM14: no hunger term reads a body store (#0501, #0475): a flat 0 | |
| S2c-m-kernel | mod | kernel | `test_replay_live_energy.py` `fat_loss_server()` on the default body: intake at fat depletions 0, 0.05, 0.25, 0.40, 0.55 (`fat_loss_intake`) against kg of fat lost | proof_run `x436-20261015-094119` (#3874: the thin starts' energy state equal to `K.deficit.state(0, fatDep)` live). |
| S2c-study | — | study | S1254 converted per kg of fat (125 kcal/d, via S2208, S2206), band ×/÷ 1.5 (`deficit_oracles.py` `S1254_KCAL_PER_KG`, `S1254_TOL`) | |
| S2d-v-model-health | vanilla | vanilla-model | VM10: HUNGER from 0 to 0.70 at 34.84 h, then −3.564 health a game hour at DayLength 4 (#0518), tier 3 adds no regeneration (#2353, #2354): death about 62.9 h after the last meal | |
| S2d-v-live-health | vanilla | vanilla-live | V1b `health.get` hourly `overall` | Gap until V1 runs. Vanilla death by hunger was never measured: the only death on record was thirst (#0173, #0174). |
| S2d-v-model-weight | vanilla | vanilla-model | VM6–VM8: calorie store to the −2200 floor, then 0.646 kg a game day (#0161, #0154) | |
| S2d-v-live-weight | vanilla | vanilla-live | `scenario-20261004-190146/scenario-nutrition_3day_fast.json` `test.samples[k].weight` (80 → 78.574 kg over 72 h, vanilla Nutrition on; hunger pinned, a control #0500) | Built 42.20.4; usable for vanilla data (amendments item 3). |
| S2d-m-mass | mod | kernel | kernel replay 90 days, no food, `autodrop` 600 g ×4 a day; paths `body.fm`, `body.lm`, `body.lx` | proof_run x434 (#3869, the deficit partition). |
| S2d-m-drain | mod | kernel | the same replay, the record's drain and lethal code (mirrored as `effects_drain`, `effects_lethal`, #3106; Task 4 confirms the record path) | The starvation drain (fat gone) was never measured live (G16); proof of the drain path is x161b's scurvy drain (#3106) and the dial (#3105). Also plotted: the mod's hunger never passes 0.69 (#3074, #3123). |
| S3a-m-pool | mod | kernel | kernel replay 60 days, four `Base.TunaTinOpen` a day at 08/12/16/20, `autodrop` water; path `nutrients.vitC.p` (plus the first two other records to reach grade 2, which Task 4 reads off the same replay) | proof_run `x151r-20261005-192030` (#2977, #2978: grade crossings where the kernel puts them, at OnsetSpeed 30; Plan 4 build, G11). Vitamin C is never scaled by OnsetSpeed (README options table), so no live run can reach its onset. |
| S3a-m-grade | mod | kernel | the same replay, `nutrients.vitC.g` | |
| S3a-study | — | study | S0224, S0225, S0967 (days from a vitamin-C-free diet to scurvy signs) | Reference points. |
| S3b-m-live-U | mod | live | `x34-regrade-20261011/rows.json` `row13.days.days.<d>.server_U`, d 0–6 (3.75, 13.83, 21.82, 28.19, 30, 24.32, 19.34; #3683) | Mod `c648c178`; monotony's later changes are the offline skip and refactors only (git log), so the mechanism stands; the eats were `TKX.Mono450`, the chart says so. |
| S3b-m-live-B | mod | live | the same days' `.moodLast_b` | BOREDOM itself is reset-bounded by the driver (guide), so the remembered target is plotted, not the stat. |
| S3b-m-kernel-U | mod | kernel | kernel replay 14 days, four `Base.TunaTinOpen` a day, then varied; path `UNHAPPINESS` | proof_run x34 chain (#3683, TWIN within 7.1e-15). |
| S3b-v-live-U | vanilla | vanilla-live | V2 ring `rows_list[k].UNHAPPINESS` | Gap until V2 runs; vanilla has no monotony (the tuna row's mood changes are blank). |
| S3b-v-live-B | vanilla | vanilla-live | V2 ring `rows_list[k].BOREDOM` | Shows vanilla's own idle boredom rise (x34 F-T9r-4). |
| S3c-m-pool | mod | kernel | S3a's replay continued to day 80 with one `Base.Orange` (item-pass vector) a day from day 45; `nutrients.vitC.p`, `.g` | proof as S3a. |
| S3c-study | — | study | S0229 (time to symptom improvement after vitamin C treatment) | |
| S4a-m-perfect | mod | kernel | Strength day × 365, S 20, p 2.0, E +260 | proof x435, x434. |
| S4a-m-lowprotein | mod | kernel | the same, p 0.8 | |
| S4a-m-deficit | mod | kernel | the same, p 2.0, E −500 | |
| S4a-v-model-x1 | vanilla | vanilla-model | VM11, factor 1 | |
| S4a-v-model-x07 | vanilla | vanilla-model | VM11, factor 0.7 (protein store below −300, #2112) | |
| S4b-m-level | mod | kernel | Strength day × 3650, perfect training | proof x435. The oracle's long runs are `strength_oracles.py` `_yearly`, `o_year1`. |
| S4b-m-cap | mod | kernel | `K.strength.level(body.Fc, body.N0, P.Tmax, P)` of the same body (the level at the cap) | |
| S4b-v-model | vanilla | vanilla-model | VM11 at 20 sets a week, to level 10 and capped (#2109) | Vanilla reaches 10 inside the first year. |
| S4b-study | — | study | S1915 (Kouri 1995's natural FFMI 25 kg/m², `strength_level.py` `FC_LIMIT`) shown as a level | |
| S4c-m-kernel | mod | kernel | Strength day: 365 d perfect, 365 d S 0 p 1.2 E 0, 180 d perfect | The detraining and regain arms were never closed live (G14). |
| S4c-v-model | vanilla | vanilla-model | VM11 + VM12 (rust): −1 XP per 1200-unit bucket once the timer passes 20 000 (#2151, #2154–#2156): the level does not move in a year | |
| S4c-study-0618 | — | study | S0618 (strength loss over 12 weeks of detraining and time to regain) | |
| S4c-study-0617 | — | study | S0617 (retraining previously trained muscle) | |
| S5a-m-live-lean | mod | live | `x436-20261015-094119/creation.json` `verdicts.36_<case>_body.observed` leaves for lm, case a–f (#3872) | Task 4 cites the leaf, never `observed`. |
| S5a-m-live-fat | mod | live | the same leaves for fm | |
| S5a-m-live-weight | mod | live | the same leaves for the weight | |
| S5a-m-live-level | mod | live | `verdicts.36_<case>_xp` leaves (Strength 5, 9, 1, 5, 1, 3) | |
| S5a-v-model-weight | vanilla | vanilla-model | VM9: creation weights Obese 105, Overweight 95, Underweight 70, Very Underweight 60 (#0533), none 80 | |
| S5a-v-model-level | vanilla | vanilla-model | VM13: start level 5 plus each muscle trait's boost | JT1 (a script read for Task 2). |
| S5b-m-strong-level | mod | kernel | kernel replay 90 days, stand-in traits `["strong"]` (the trait id the creation reads: Task 4 checks), meals at "request", sleep off; the written Strength level | proof x436 (creation), x434/x435 (closes). The README's "an idle Strong character settles in the Stout band". |
| S5b-m-none-level | mod | kernel | the same, no traits | |
| S5b-m-gaunt-weight | mod | kernel | the same with Very Underweight (Gaunt); `body.fm` + `body.lm` + `body.lx` | |
| S5b-m-none-weight | mod | kernel | the same, no traits | |
| S5b-v-model-level | vanilla | vanilla-model | VM11 + VM12: no XP, rust does not move a level in 90 days: flat at the start level | |
| S5c-m-gaunt | mod | kernel | S5b's Gaunt replay, `body.energyState` | proof x436 (#3874). |
| S5c-m-none | mod | kernel | S5b's no-trait replay, `body.energyState` | |
| S5c-m-live | mod | live | `x436-20261015-094119/creation.json` `verdicts.36_{d,e,f}_hunger.observed.es` (1.4962, 1.6529, 1.4963; #3874) at day 0 | |
| S5c-v-model | vanilla | vanilla-model | VM14: hunger reads no weight or fat (#0488, #0501): flat 1 | |
| S6a-m-day1 | mod | kernel | kernel replay: `drink` Coffee 0.25 L at 08, 12, 16; paths `acute.caf` (mg) and `effects.fOff` | proof_run x151r (#2982, the 5.0 h half-life) and x161f (#3077); both on the Plan 4–5 build (G10). |
| S6a-m-day14 | mod | kernel | the same schedule every day to day 14; day 14's `acute.caf`, `effects.fOff` (the tolerance's effect) | Tolerance τ 7 days (`test_kernel_acute.py` `test_caffeine_tolerance_tau_7d_both_ways`). |
| S6a-v-model | vanilla | vanilla-model | VM15: FATIGUE −0.025 a 0.25 L cup (−10 a litre, #2949), the same on day 14 | |
| S6a-study-0851 | — | study | S0851 (caffeine half-life range) | |
| S6a-study-1123 | — | study | S1123 (tolerance's time constant) | |
| S6b-v-model | vanilla | vanilla-model | VM16: four 0.3 L beers at 0.05 a litre, 400 × alcohol × the hunger factor (#2923, #2926), decay 45.36 a game hour at DayLength 4 (#2922) | |
| S6b-v-live | vanilla | vanilla-live | V4 `stats.all` polls, `stats.INTOXICATION` | Gap until V4 runs; #2950 (DayLength 1) is the existing reading. |
| S6b-m-bac | mod | kernel | kernel replay: `drink` Beer 0.3 L × 4 over an hour; path the record's blood alcohol (`acute.bac` or its name in `NR_Kernel_Acute.lua`, Task 4) | proof_run `x161f-20261006-055908` (#3086) and x151r (#2983). |
| S6b-m-intox | mod | kernel | the same replay, the stand-in's `INTOXICATION` (the writer's target, `K.effects.intoxTarget`) | #3086. |
| S6b-m-hangover | mod | kernel | the same replay to 24 h, the hangover state | No live reading of a hangover exists (G10); drawn only after M2 or with the gap stated. |
| S6c-m-kernel | mod | kernel | kernel replay with `sleep_allowed=True`: nights 23:00–07:00 except one 03:00–07:00, meals at "request"; paths `acute.debtH`, `HUNGER` | proof_run `x30-grade-20261011` (#3677: bookings and debts equal to the kernel; the sleep factor within 0.00549). |
| S6c-m-live | mod | live | `x30-grade-20261011/rows.json` `row11.nights[i].booked_h`, `row11.closes[i].debt_after` (#3677) | Plan 11f build; admission test. |
| S6c-v-model | vanilla | vanilla-model | VM14: no sleep term on hunger (#0475): factor 1 | |
| S6c-study | — | study | S1566 (intake and hunger the day after one 4 h night) | |

### Systems reference

| id | side | badge | source | notes |
|---|---|---|---|---|
| SN1-m-vitC, -fibre, -iron, -sodium | mod | kernel (see G12) | `data/food-nutrients.json` `items[pz_id = X].per_item.vitC`, `.fibre`, `.iron`, `.sodium` for H4's five foods | Four series; vanilla carries none of these. |
| SE1-m-live-liquid | mod | live | `x363-20261012-202827` ring `rows_list[k].stomach.liquid` (water then milk; #3702, #3668) | Mod `7093079b`; the stomach kernel has not changed since (git log); admission test. |
| SE1-m-live-fill | mod | live | the same rows' `stomachFill` | Sip rows: the `*_replay` values are do-not-cite. |
| SE1-m-kernel-fill | mod | kernel | the HEAD replay of x363's `events.json` from its `start.json`; `stomachFill` | |
| SH1-m-kernel | mod | kernel | `test_satiety_meal_studies.py`'s Callahan replay (the 190, 400, 825 kcal liquid preloads at 09:00) at HEAD | Its pins are 243, 266 and 329 min under the refit (the module's comment). |
| SH1-m-live | mod | live | `x36-grade-20261012/grade.json` `sessions.x361.readings.readings.C650_request_vs_anchor.live_min` (247.09) and `.C400_held_vs_180.live_min` (215.13) (#3700) | Admission test on x361. |
| SH1-study-1247 | — | study | S1247 (247, 286, 321 min) | |
| SH1-study-1248 | — | study | S1248 (240–300 min for 650 kcal) | |
| SH2-m-live | mod | live | `x27-grade-20261010/rows.json` `row8.mean_live_six`, `row8.mean_arm_three`, `row8.ratio_live` (#3671) | |
| SH2-study | — | study | S1608 (three against six meals) | |
| ST1-v-model | vanilla | vanilla-model | VM5, 10 h from 0 | |
| ST1-m-kernel | mod | kernel | kernel replay 10 h at rest, no drink, default body; `THIRST`, `fluids.thirstTarget` | Proof as S1c (G7). |
| ST1-m-live | mod | live | `x151t-20261005-183551/thirst.json` `records[51]` (dehydPct 1.4369, thirstTarget 0.2459 at 604.9 min; #2963) | An 80 kg female subject on the Plan 4 build: drawn only with that stated, or not at all (admission test cannot run on that build's records). |
| ST2-m-live-na | mod | live | `x28-grade-20261011/rows.json` `sodium.by_day.<d>.na_change_per_24h`, d 1–5 (#3688) | |
| ST2-m-live-plasma | mod | live | the same file's `sodium.by_day.0.naPlasma_min`, `sodium.by_day.5.naPlasma_max` | |
| ST2-m-kernel | mod | kernel | `testing/tests/kernel/test_sodium_balance.py` `simulate(days=5, na_day=0)` | |
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
| SX1-m-live | mod | live | `x37-grade-20261013/grade.json` `sessions.x371.table[i].table_met`, `.billed_all` (#3730) | |
| SX2-v-model | vanilla | vanilla-model | VM2: exercising with the food-eaten moodle down, hunger rises at 6.4e-6 a game-second, below idle (#0471) | |
| SX2-m-live | mod | live | `x29-gate-20261011/rows.json` `row9.decay[0].S_30min_after_set`, `.mm_30min_after_set`, `row9.half_life_h` (#3675) | |
| SX2-m-kernel | mod | kernel | kernel replay of a Fitness set (an `activity` event at the burpee class, `exercising` true, 30 min) then rest; `satiety.S`, `HUNGER` | |
| SS1-m-kernel | mod | kernel | Strength day × 365 at S 0, 3, 6, 10, 15, 20; p 1.6; E +260 | |
| SS1-v-model | vanilla | vanilla-model | VM11 at the same weekly sets | |
| SD1-m-live | mod | live | `x161b-20261006-065751/body.json` `summaries.I.health` and `health_reads[53]`, `health_reads[70]` (health −0.598 a game hour at clinical scurvy, #3106) | Plan 5 build; the effects kernel has not changed its drains since (git log). |
| SD1-m-kernel | mod | kernel | `K.effects.drain` at clinical vitamin C held 30 days (`vitC.ah` ≥ the lethal threshold), integrated to health 0 | |
| SD1-study | — | study | S1168 (time from clinical scurvy to death) | |
| SD2-m-marginal | mod | kernel | per record of `NR_Data_Nutrients`/`K.nutrients`, zero intake from replete at OnsetSpeed 1 (`K.nutrients.stepPool`, `K.nutrients.grade` per day): days to grade 2 | The `test_kernel_nutrients.py` `test_step_pool_zero_intake_40_days` pattern. |
| SD2-m-clinical | mod | kernel | the same, days to grade 4 | |
| SD2-study | — | study | each record's own onset row (its science id in the record file) | Task 4 lists them. |
| SC1-m-live-booked | mod | live | `x30-grade-20261011/rows.json` `row11.nights[i].booked_h`, i 0–3 (#3677) | |
| SC1-m-live-debt | mod | live | the same file's `row11.closes[i].debt_after` | |
| SC1-m-kernel | mod | kernel | `K.acute.sleepMinute` over the same nights | |
| SV1-m-kernel | mod | kernel | `K.satiety.discomfort(mass, 730, 1100)` for 0–1200 g (#3623) | |
| SV1-m-live | mod | live | `x401-20261013-152929/accept.json` `verdicts.OF.observed.rows[i].server_mass` with the client levels 3, 4, 4 (#3778) | Staged copy of mod `fdd7767f` (Plan 11b); admission test before drawing. |

Series by badge: live 26, kernel 62, vanilla-live 11, vanilla-model 31, study 16; 146 in all, H4's two rows and
SN1's one row each counting as four series. The vanilla-live 11 are gaps until V1–V4 run, except S2d-v-live-weight.

## 3. Promises

| text | support | status |
|---|---|---|
| **No longer happens:** in Managed mode hunger never reaches the top Hungry moodle, so hunger never kills | #3123 (the cap at 0.69 and 0.83), #3074 (HUNGER ≤ 0.69 live on an empty stomach), #0508, #0516 | supported |
| **No longer happens:** in Managed mode thirst never reaches the top Thirst moodle, so thirst never kills (the deficiency drains still can) | #3123, #3103 (THIRST stops under level 4 live), #3011 | supported |
| **No longer happens:** a food's hunger value sets your hunger; a zero-calorie item no longer sates | #3614 (hunger from the stomach and the meal pool), #0503 (vanilla's coupling) | supported |
| **No longer happens:** hunger drops to zero after a meal | x361 nadir 0.125 (`readings.courses.C650.nadir.live`), README limitation "never reaches 0" | supported (needs a register row for the nadir: x361 guide leaf exists, no claim) |
| **No longer happens:** an idle character gains weight on 1500 kcal a day | H2-v-model (#0149, #0455) against H2-m-total | supported after Task 4 (series) |
| **No longer happens:** Strength experience levels you up; a year of grinding takes you to 10 | #3851 (XP is the training signal), #3871 (the level follows the body), H3 series | supported |
| **No longer happens:** weight-band traits follow the scale; a muscular heavy character is no longer Overweight | #3856 (the fat axis scaled by lean), #3873, #0155 | supported |
| **No longer happens:** a thin or fat trait changes only the scale | #3874 (a thin start is hungry), #3872 (the bodies) | supported |
| **No longer happens:** Strength stays forever without training (vanilla's rust is one XP a step) | #2151, #2155 (vanilla), S4c-m-kernel (mod) | supported by series; the detraining arm has no live reading (G14) |
| **Can happen:** you get hungrier as you lose fat | S2c (S1254), #3874 | supported |
| **Can happen:** a missed day makes you eat about a fifth more the next day | #3670 (1.2141 live), S1613 | supported |
| **Can happen:** scurvy and the other deficiencies on a one-food diet | #2978 (crossings where the kernel puts them), #3106 (the drain), S3a series | supported |
| **Can happen:** clinical scurvy kills in about a week of game time without treatment | #3106 (−0.598 health a game hour), S1168 | supported |
| **Can happen:** starvation kills once the fat reserves are gone (`NR.DeficienciesCanKill` on) | README; #3105 (the dial); no live or register row of the starvation drain itself | needs a reading: S2d-m-drain from the kernel and a C row for the drain's condition (G16) |
| **Can happen:** eating one food lowers mood to the first Unhappy and Bored level, and varying it lifts it | #3683 | supported |
| **Can happen:** refeeding sickness after long starvation | #3875 (refeeding risk 2 at a Weak and Gaunt start), #2987 | supported |
| **Can happen:** a hangover after heavy drinking | none (kernel test only: `test_kernel_acute.py` `test_hangover_starts_counts_down_and_ends`) | needs a reading (M2) or drop |
| **Can happen:** caffeine tolerance and withdrawal | #3077 (the offset follows caffeine), kernel tests; no live tolerance reading | weak: kernel only for tolerance; keep with the kernel badge or read in M2 |
| **Can happen:** a short night raises the next day's hunger | #3677, #3638 | supported |
| **Can happen:** Night Vision from a long, well-stocked vitamin A and zinc intake | #3093, #3095 | supported |
| **Can happen:** Short Sighted at a clinical vitamin A deficiency | #3098 | supported |
| **Can happen:** low blood sodium from drinking without salt | #3688 (grade 0 over five sodium-free days), #3689 (the earlier build diluted) | weak: the live run shows the defence holding; the drain at a high grade has no live reading — reword to "the body defends its sodium" or mark needing a reading |
| **Can happen:** an iron overdose makes you sick | #3084 (the excess rung drives food sickness) | supported for sickness; "drains health" (README) has no row — reword or needs a reading |
| **Can happen:** overeating raises the Overfull moodle and never blocks an eat (vanilla still refuses at its own food-eaten level 3) | #3623, #3778, #0521, #2889 | supported |
| **Can happen:** a protein-rich, trained, fed body grows toward a natural cap no one passes | #3853, S1915, S4b series | supported |
| **Can happen:** a muscle start fades toward its set point when idle (an idle Strong settles in the Stout band) | #3855 (the half share), S5b-m-strong-level | supported after Task 4 (series) |
| **Can happen:** every nutrient replete speeds sleep's recovery 5 % (`NR.BalanceBonus`) | README only | needs a reading or a C row; drop from the page if neither |

## 4. The vanilla model's formulas (Task 2)

| name | formula | claim ids or jar target |
|---|---|---|
| VM1 hunger awake | dH/dt = 9.6e-6 × StatsDecrease mult × (1 − H) × appetite trait, per game-second; 0 while the food-eaten timer > 0 and not exercising | #0470, #0474, #0489, #0490, #0473, #0524, #0525, #0483, #2773 |
| VM2 hunger exercising and asleep | exercising: 6.4e-6 (moodle down), 1.92e-5 (moodle up); asleep 1.0e-6 × (1 − H) | #0471, #2774, #2775, #0472, #2783, #0498 |
| VM3 the food-eaten timer | after an eat, only if HUNGER is at its minimum: timer += abs(hungerChange) × f × 13000, ×2 cooked, cap 11 000; decays DayLength/30 units a game-second (3.0 at DayLength 4); moodle level 1 above 0 | #0054, #3597, #0503, #0530, #0529, #0511, #0528 |
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
| VM16 intoxication | the fluid writer adds 400 × alcohol × (1.1 above 0.8 HUNGER, 1.25 between 0.6 and 0.8); Beer 0.05 a litre; decay 0.0042 × the multiplier a tick = 0.504 × DayLength minutes a game hour (45.36 at DayLength 4) | #2923, #2926, #2919, #2922, #2918, #2950, #2951 |

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
| V1a | H1, S1a, S1c: a measured meal | arm A: `stats.set admin hunger 0.25 thirst 0`, eat `Base.CannedBologneseOpen` whole, 6 h; arm B: `stats.set admin hunger 0.10`, eat a second can (HUNGER to 0, timer filled), 2 h. HUNGER and THIRST every game minute, FoodEaten level every 10 s at speed 1 for the first 25 game minutes of arm B, `nutrition.get` hourly | 8.5 | 30 (1 around eats and arm B's first 25 min) | ~6 min | `minute.ring admin start` / `read` / `stop` (no paths), `stats.set`, `eat.action` (client), `item.spawn` or RCON `additem`, `moodle.level admin FoodEaten`, `foodtimer.set` (read-back only, no write), `nutrition.get`, `stats.all`, `time.snapshot`, `time.multiplier` |
| V1b | S1b, S2a, S2d: starving to death | `stats.set admin hunger 0.60 thirst 0`, no food; `stats.set admin thirst 0` hourly (a control: hunger and thirst are independent, #0500, #0501); HUNGER every minute; `health.get` and `nutrition.get` hourly; `moodle.level admin Hungry` hourly; until death (predicted: level 4 at +8.3 h, health 0 about 28 h later) | ~37 | 30 | ~8 min | `minute.ring`, `stats.set`, `health.get`, `nutrition.get`, `moodle.level`, `time.snapshot` |
| V2a | H2, S1a, S3b: one food, day 1 | `nutrition.set admin calories 0` and `weight 80` at the start (values read first); four `Base.TunaTinOpen` at 08, 12, 16, 20; HUNGER, BOREDOM, UNHAPPINESS every minute; `nutrition.get` hourly; `stats.set admin thirst 0` every 6 h | 24 (07:00–07:00) | 30 (1 around eats) | ~7 min | `minute.ring`, `nutrition.set`, `nutrition.get`, `eat.action`, `stats.set`, `stats.all` |
| V2b | H2, S3b: one food, day 2 | the same on the same world, from where V2a left it (the x27 and x34 chain precedent of sessions on one world) | 24 | 30 | ~7 min | as V2a |
| V3 | H3, S4: Strength experience | push-up sets to exhaustion at speed 1 with `stats.set admin endurance 1` before each: A `nutrition.set proteins 0` (control, expect +360); B `nutrition.set proteins 100` and `perk.park admin Strength` to 300 XP under level 6 (expect ×1.5 = 540 and a crossing to level 6 with STOUT); C `nutrition.set proteins -400` (expect ×0.7 = 252). XP and level before and after each (`perk.xp`), traits after B (`trait.check`) | ~1.5 | 1 | ~8.5 min | `exercise.do pushups 10` (client), `perk.xp`, `perk.park`, `nutrition.set`, `stats.set`, `trait.check`, `time.snapshot` |
| V4 | S6a, S6b: coffee and beer | profile `[server] SleepAllowed = true`, `SleepNeeded = true` (fatigue holds only then, #2949); A: `stats.set admin fatigue 0.5`, 0.25 L Coffee (`fluid.fill` a bottle, `drink.action`), FATIGUE before and after and for 1 game hour; B: three `Base.BeerCan` drunk back to back, INTOXICATION polled every 2 s until 0 | ~1.5 | 1 | ~7 min | `fluid.fill`, `drink.action` (client), `stats.set`, `stats.all`, `time.snapshot` |

V4 is the lowest priority: its vanilla series can be the model from #2922, #2923 and #2949 with #2950 and #2951 as
the measured rows (DayLength 1), if Angus prefers fewer sessions. None of the six sessions passes 10 minutes; none
needs the detached launch. V2 may run as one 36-hour session of about 9.5 min instead of V2a and V2b.

**Modded gap runs (optional; the kernel route with the older proof runs is admissible under the amendments' item 3).**

| id | purpose | readings | game hours | multiplier | wall estimate | harness commands |
|---|---|---|---|---|---|---|
| M1 (recommended) | Re-prove the hunger and thirst pipeline at HEAD after Plan 13's body switch; the first THIRST graded against a replay (G7, G8) | staged copy of mod/ at HEAD (`tools/release_pack.py stage`), DayLength 1, `Nutrition = false`; fresh record; at the first request eat `Base.CannedBologneseOpen`; then no food and no drink (`autodrink.set false`) for 24 h; ring paths HUNGER, THIRST, `satiety.*`, `stomachFill`, `fluids.*`, `body.fm`, `body.lm`, `body.energyState`, the bus signature; the replay graded HUNGER 0.002, es 0.005 and THIRST at a tolerance named before the run | ~32 | speed 5 (as x364) | ~8 min | `minute.ring` with paths, `eat.action`, `autodrink.set`, `lua.read`, `stats.all`, `time.snapshot` |
| M2 | Live proof at HEAD for S6: caffeine, blood alcohol, the hangover and the sleep factor (G10) | sleep on; three coffees and four beers on day 1, a 4-hour night, meals at the request on day 2; ring paths the acute caffeine, blood alcohol, hangover, `acute.debtH` | ~30 | speed 5 | ~8 min | as M1, plus `drink.action`, `fluid.fill`, `player.sleep` |

## 6. Gaps

| id | gap | fill |
|---|---|---|
| G1 | Vanilla hunger after a real eat at the default DayLength: the timer's fill gate (`isAtMinimum`) is C-only (#3597, #0054) and every measured freeze came from a timer write (#0524) | V1a |
| G2 | Vanilla death by hunger was never measured (the one death was thirst, #0173; hunger stopped at 0.6999, #0174) | V1b |
| G3 | Vanilla weight under real eats: every weight run drove `setCalories` (#0170) | V2a, V2b |
| G4 | Vanilla Strength: the protein factors (#2112) and a live level crossing with its band trait (#2157) are C-only | V3 |
| G5 | Vanilla intoxication and coffee at DayLength 4 (#2950, #2951 ran at DayLength 1) | V4 (optional) |
| G6 | Vanilla muscle-trait start levels have no vanilla claim | JT1 (Task 2) |
| G7 | THIRST was never graded against a replay; the mod's thirst proof is x151t on the Plan 4 build, before the 2026-10-10 sodium changes | M1 (recommended); otherwise S1c-m-live and ST1-m-live are not drawn and the thirst line carries the older proof |
| G8 | Every mod hunger proof run (x27x–x36x) predates Plan 13's creation body and low-fat ramp; old start records may not load at HEAD (no-compatibility rule) | Task 4's admission test; M1 |
| G9 | The guide's foods were never eaten in a mod live run (x361–x364 ate study foods) | covered by kernel replays with the item-pass vector (Task 4 asserts the landed vector equals the record, as #3182) |
| G10 | Caffeine, alcohol and hangover proof runs (x151r, x151r2, x161f) are Plan 4–5 builds; a hangover was never read live | M2, or S6b-m-hangover drawn with the gap stated on the chart |
| G11 | Vitamin C onset cannot be read live (never scaled by OnsetSpeed); the pool proof is x151r on the Plan 4 build | kernel badge with x151r as proof; stated |
| G12 | H4 and SN1 read dataset records, which fit none of the four provenance kinds | Task 3 decides: a fifth kind `data` (file, record id, key) or vanilla script values as `vanilla-model` and the generated table as `kernel` at the mod commit |
| G13 | Strength over years has live proof only at the biology clock 30 over 2 to 4 closes (x434, x435) | kernel badge; stated |
| G14 | The detraining, regain and peak arms of the Strength day were never closed live | kernel badge with the oracle studies (S0618, S0617); stated |
| G15 | The sleep factor's live run (x30x) is the Plan 11f build | admission test; M2 |
| G16 | The starvation drain (fat gone) has no live reading and no register row | kernel series S2d-m-drain plus a C row of its condition read off `K.effects.drain`; or M-run (a 90-day fast is out of a live session's reach) |
| G17 | Three README promises have no support: the hangover, the balance bonus and a health drain from low blood sodium or an iron overdose | reword, drop, or read (M2 covers the hangover) |
