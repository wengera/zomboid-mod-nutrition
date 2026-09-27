# Nutrition mod — design

Written 2026-09-27 against build `42.20.4` (jar `b0bbce05d5`), a dedicated-server multiplayer target, from the reference library in this repository and the thirteen research reports under `docs/superpowers/research/`. Sections 1 to 4 of the architecture were approved one at a time; sections 5 to 10 were written with the controller's defaults on Angus's instruction, and every default is listed once in § 7 for the re-review that closes the design phase. The spec is tracked while the program runs and deleted at its close; the pages, the registers and the mod are what stay.

## 0. How to read this

- A **ruling** is a decision Angus took; it is not reopened by an implementer.
- A **default** is a decision the controller took under the instruction to assume the sensible choice; § 7 lists them all and each is open at the re-review.
- A **gate** is an experiment or a jar reading a plan must land before the work that depends on it.
- Every number the mod ships cites a row of one of two registers: the claims register `docs/reference/claims.tsv` for what the game does, and the science register this program creates for what the evidence says. A number with no row does not ship.
- Register rows are referred to here by id in prose ("register row 1140"); the bracketed tag grammar is reserved for the pages.

## 1. Goals and non-goals

The mod is a realism nutrition overhaul for Project Zomboid Build 42 on a dedicated multiplayer server, released publicly on the Workshop.

Goals:

- Track about twenty-five nutrients beyond the vanilla four macros, with body pools, real depletion and repletion kinetics, and graded deficiency and excess states pinned to published evidence.
- Replace the vanilla energy and weight model with a two-compartment body of fat mass and lean mass, lean-mass-based resting expenditure, activity expenditure that scales with total mass, evidence-based partitioning of deficit and surplus, and strength capped by lean mass with strength memory.
- Drive hunger, thirst, endurance, fatigue, perception, movement and combat responsiveness, health and healing, mood and thermal tolerance from nutritional state, with a balanced diet at the top of every ladder.
- Rebalance the vanilla food records' macros from public-domain food-composition data and give every record a nutrient vector.
- Show the player symptoms first and numbers only when the character has the knowledge or the server allows it.
- Full unit coverage of the model, live server scenarios that integrate the model against the real server, and paired cross-side reads for everything that crosses the wire.
- No measurable performance degradation on the server tick or the client frame.

Non-goals for the first release: new food items, cooking-skill changes, farming or foraging changes, an animal or NPC nutrition model, single-player claims, and any dependency on a third-party mod.

## 2. Rulings

1. **Release target: public Workshop from day one.** No hard third-party dependency; MoodleFramework is optional and detected at runtime; the mod's own panel is the primary surface; sandbox dials and compatibility rules are in scope from the start.
2. **Hunger and thirst are driven by the model.** The vanilla stats are what the model writes, so other mods that read them keep working.
3. **Visibility: symptoms first, numbers gated** behind the vanilla Nutritionist trait or a server option.
4. **Default pace: real timescales at 1×**, with onset and severity dials.
5. **Architecture C: full takeover.** Vanilla nutrition off at the sandbox and every stat updater replaced through the `CalculateStats` hook on the server. The overlay shape (write after vanilla's tick) is kept as a sandbox-selectable fallback mode. The controller stated the compatibility cost (the hook is global and all-or-nothing) and Angus reaffirmed.
6. **Strength: own the Strength level.** A lean-mass ceiling lowers the level as lean mass falls and restores it as mass returns; vanilla experience gain runs underneath and is preserved through the dip; carry capacity through its own setter. No effective-strength setter exists on this build.
7. **Muscle memory is strength memory.** Lean mass regrows at ordinary hypertrophy rates; the Strength level restores fast as mass recovers; the science register says so.
8. **Performance at the forefront** (Angus, on approving § 4.1): budgets per clock, an instrument before any claim, fast-path rules, a review gate. § 6.

## 3. Evidence base

The library: `docs/areas/*` for the design lens, `docs/platform/*` and `docs/facts/*` for the mechanisms, `docs/reference/claims.tsv` for every claim's grade and pointer.

The research wave of 2026-09-27, thirteen reports under `docs/superpowers/research/` with the briefs in `_BRIEFS.md` and the controller's own verified readings in `_CONTROLLER-NOTES.md` (N1 to N5):

| report | what the design takes from it |
|---|---|
| `jar-perks-strength.md` | no effective-strength lever; carry capacity ownable (`setMaxWeightBase`, `setMaxWeightDelta`); the server owns XP and level; `setPerkLevelDebug` and `level0` exist for Lua; the anti-cheat XP-rate trip; skill rust is Lua; the live protein branch in `AddXP` (N1) |
| `jar-endurance-fatigue-sleep.md` | the seven updaters behind `CalculateStats`; the drain, regen and fatigue formulas; endurance and fatigue reach speed and combat only through moodle levels; no speed or regen setters; the thermoregulator already reads weight as fatness |
| `jar-perception-speed.md` | the client-only vision cone and its inputs; night vision as a trait scaled by darkness; view distance only through the Short Sighted trait; hearing through `getDetectionRange`; movement speed copied from `PlayerInjuriesPacket`; combat speed client-authoritative through moodles; the trait packet reaches the affected player only |
| `jar-dishes-item-nutrients.md` | dishes carry ingredient full types and counts; craft splits pass food and extra items; the handcraft action's consumed-item map; meat noise ±11 %; item modData is a deep per-instance copy; fluids reject unknown keys; the drink wrap point |
| `jar-health-surfaces.md` | `ReduceGeneralHealth` and `AddGeneralHealth` as the health API; regen tier setters; six severe-moodle drain terms with `OnPlayerGetDamage`; `syncBodyPart`; the temperature stat as the thermal door; the 24 stats with ranges |
| `platform-sandbox-options.md` | the option file grammar and location; free sync of custom options; the file-scope read trap; runtime change with no event; the harness's nested-key blocker |
| `moodleframework-desk-read.md` | a pure client widget library, no engine registration, no multiplayer surface; consumer mirrors and sets on the client; detection by function type |
| `platform-client-ui.md` | `ISCollapsableWindow` and `ISLayoutManager`; `PZAPI.ModOptions` keybinds and the load trap; the `ISToolTipInv:render` wrap; the character-info tab wraps; the debug-client tooltip gate |
| `platform-server-lifecycle.md` | no join event; `OnNewGame(IsoPlayer, nil)` on creation and respawn; death not observable by event server-side; online id recycled; username as the key; the player blob carries no modData; global modData saved per world; global transmit broadcasts |
| `food-data-pipeline.md` | SR Legacy as the spine; the nutrient-id join trap; the iodine gap; measured state pairs over retention factors; the ~342 distinct compositions; item weight is not a portion mass; the Atwater validator |
| `science-energy-body.md` | Mifflin-St Jeor lean-mass form; 2024 Compendium METs; Alpert's fat ceiling; Forbes and Hall partitioning; hypertrophy and loss rates; strength memory, not mass memory; hydration thresholds and the two contradictions to rule on |
| `science-vitamins.md` | requirements, stores, onset timelines, deficiency and excess effects and food relevance for fourteen vitamins; 77 verified citations |
| `science-minerals-fibre-fats.md` | the same for twelve minerals, fibre, essential fats, carbohydrate quality, alcohol and caffeine; phytate as the shared absorption property; sweat losses; 54 verified citations |

## 4. Architecture

### 4.1 Runtime shape (approved)

Three Lua layers with one direction of dependency. A **pure kernel** in `shared/` holds every formula as side-free functions, tables in and tables out, in the Kahlua-safe subset (no `goto`, no integer format of floats, no length operator on Java lists, no Java objects inside the kernel). **Server adapters** in `server/`, each behind a nil-checked runtime side test, read the engine into plain tables, call the kernel and write the results back. The **client layer** holds the panel, the tooltip wrap, the optional moodle bridge and a read-only mirror of the player's state; it never computes.

Two server clocks, one owner:

- The **fast clock** is the takeover handler on `Hook.CalculateStats`. It fires per player per update tick on the server only (controller note N5: animals return before the hook, the zombie override is empty, the player override calls the base only when the process is not a game client) and reproduces the seven vanilla updaters — endurance, tripping, thirst, stress, the awake and asleep hunger and fatigue updater, morale, fitness — from the game-second delta and a coefficient set the slow clock left for it. It allocates nothing and calls no Java member beyond the hoisted stat handles.
- The **slow clock** is `EveryOneMinute`, which runs the whole model: stomach and absorption, pools and kinetics, energy balance and body composition, status grades, the derived coefficient set, the weight write into the vanilla slot, the perk ceiling, the health and body-part effects, and the mirror push to that player's client. It runs the players staggered across the minute's ticks so no single frame carries them all.

A player is initialised on first sight in the slow clock's walk of the online list, since the server fires no join event, and dropped when it leaves the list; `OnNewGame(IsoPlayer, nil)`, which fires server-side on creation and on respawn, resets the character's body to a fresh start. Death is detected by the dead flag in the walk.

One sandbox option selects the mode: **takeover** (default) or **overlay**, where the hook is not registered and the fast clock writes its adjustments after vanilla's updaters have run. The kernel computes the same deltas in both modes; the switch changes one adapter. Overlay exists for servers whose other mods claim the hook.

Durable state is one global modData table keyed by username, cached in a server Lua table and never written to player modData. Global modData is loaded and saved per world by the engine as its own file (lifecycle report § C); its save cadence is unread and is the persistence experiment's to measure.

### 4.2 Intake (approved)

Every eat is read off the item, never recomputed. A server-side wrapper of `ISEatFoodAction.complete` snapshots the item before the original runs — full type, raw hunger value, state flags, ingredient list, any per-instance nutrient map on its modData — and reads it again afterwards; the share eaten is the drop in raw hunger over the item's base hunger. A wrapper of the action's `serverStop` catches cancelled eats the same way; a wrapper of `ISDrinkFluidAction:updateEat` reads litres consumed as the container's amount before minus after, the only seat the fluid path has. Each wrapper holds its sentinel in a global of its own, guards on the nil-checked side test, and always calls the original.

The nutrient vector is assembled from four sources: the **per-type baseline** from one Lua data table keyed by full type, generated by the data pipeline and loaded once per side (not script keys, which become a deep per-instance modData copy on every food in the world); **dishes** as the sum of ingredient baselines times counts from the dish's ingredient list, scaled to the dish's own macro total to recover the cooking share the list does not keep; **crafted outputs** that inherit an input's food from a nutrient map written at creation out of the consumed-item map the vanilla handcraft action records; **animal meat** scaled by raw hunger against the type baseline, accepting the ±11 % per-field noise; **fluids** from a per-fluid table keyed by fluid type string, per litre. State multipliers for cooked, burnt, rotten and frozen apply per nutrient class from the retention data; burnt and rotten are labelled mod judgements.

The vector lands in a **stomach buffer**. Gastric emptying moves it into absorption over hours; absorption applies bioavailability, phytate and fat co-ingestion factors; the pools receive the result. Hunger derives from stomach fill and energy state; vanilla's own hunger and thirst writes inside the eat are overwritten on the next tick, so a client sees vanilla's number for at most one push. Cost: one item read per eat, nothing per tick.

### 4.3 Energy and body (approved)

The body is fat mass and lean mass. At first sight a character's vanilla weight is split by a register-cited body-fat relation from weight, build proxies and sex, the creation band traits placing obese, overweight and underweight starts in the right fat range; until the relation is cited the split is a mod judgement.

Expenditure: resting expenditure is the lean-mass form of Mifflin-St Jeor; activity expenditure is a 2024 Compendium metabolic-equivalent table mapped onto the engine's states (sleeping, idle, walking, running, sprinting by extrapolation, the timed-action classes by their vanilla calorie-modifier bands, load carriage from inventory weight through the Pandolf terms flagged as secondary-sourced), per kilogram of total mass; the thermoregulator's cold term multiplies rest and sleep as vanilla does; adaptive thermogenesis is a small bounded reduction under sustained deficit.

Balance is integrated per minute and partitioned per day: a deficit is paid by fat up to Alpert's ceiling of about 290 kJ per kilogram of fat per day and the remainder by lean mass the same day; a surplus is partitioned by the Forbes and Hall relation with the lean share raised by adequate protein and by training, which the engine reports through exercise actions and Strength and Fitness experience events; lean gain is capped at evidenced hypertrophy rates and lean loss under deficit is slowed by protein and training.

Strength is a ceiling derived from lean mass by the register's allometric relation, applied to the Strength level each minute, lowered as lean mass falls and restored fast as it returns, vanilla experience preserved underneath; carry capacity follows lean mass through `setMaxWeightBase` and `setMaxWeightDelta`. Total mass is written into the vanilla weight slot each minute; the band trait is refreshed when the band changes and pushed to that client with the player-fields packet's trait bit (controller note N2), so vanilla's fourteen readers, the thermoregulator's fatness term and other mods' viewers keep working. Sweat, respiration and cold-diuresis loss terms feed § 4.4.

### 4.4 Nutrient kinetics (approved)

Every nutrient is one declarative record — pool size, elimination term, absorption defaults and interaction factors, requirement, status ladder (replete, marginal, depleted, clinical), excess ladder with acute thresholds, repletion cap — and the kernel is one generic engine over the records; every number in a record cites a science-register row by id and a checker fails an uncited number. Iron, vitamin A and B12 carry two compartments; water and the electrolytes are fast pools charged by the § 4.3 loss terms and by alcohol and caffeine diuresis, caffeine's fading in a habitual drinker through a tolerance that decays over days. Timelines are calibrated to the register's documented onset from replete at zero intake; B12 is modelled at its real, longer-than-a-game scale and the onset dial is what compresses it. Grades are recomputed each minute; the coefficient set § 4.5 reads is rebuilt only when a grade changes. Interactions ride the records. Thirst is water deficit with sodium concentration as its second input; the dehydration endurance threshold is a ruling on two conflicting sources, mild from 2 % of body mass and steepening toward 4 %, both cited; refeeding after prolonged starvation is a risk state with both incidence figures documented. Four dials: onset speed, severity, whether deficiencies can kill, whether excess effects are on.

### 4.5 Effects (default)

The effects layer is a declarative **effects table**: for each nutrient and grade, a list of (surface, magnitude, register row). The slow clock composes the active rows into one coefficient set per player when a grade changes; adapters apply the set through five channels, chosen by what each surface actually reaches on this build:

| channel | surfaces | mechanism | cadence |
|---|---|---|---|
| stat coefficients | hunger, thirst, endurance drain and regen, fatigue accrual and sleep recovery, stress, unhappiness, boredom, panic | read by the takeover handler | per tick, constant between grade changes |
| trait toggles | night vision, short-sightedness | server-side add or remove with an ownership flag so a natively held trait is never removed, then `sendSyncPlayerFields(player, 2)` | on grade change |
| body-damage setters | regeneration tiers, wound and bleeding timers, herb factors, infection progression, temperature stat, pain | public setters the health report lists; `syncBodyPart` where a part field must reach the client | on grade change and per minute |
| health drains | starvation, terminal scurvy, cardiac beriberi, severe hyponatraemia, acute toxicities | `ReduceGeneralHealth` per minute, gated by the lethality dial; nausea through the food-sickness and poison stats | per minute |
| event-driven | aiming delay after each shot, fracture risk on landing, a client-side speed write inside the two-second push window for severe states | wrappers and events the perception and health reports name | on the event |

Perception follows from the levers the jar allows: the cone and hearing read fatigue and intoxication, which the fast clock owns; dark vision is the night-vision trait scaled by darkness, granted at a replete vitamin A grade held for long enough and withdrawn on decline, never touching a natively held trait; view distance is the Short Sighted toggle at clinical vitamin A deficiency. Movement and combat responsiveness come first from the endurance and heavy-load moodles the model already drives, which reduce base speed and swing speed on both sides for free, and only for severe states from the direct speed write. Fitness is tied to nutrition through the endurance regeneration the mod owns, not through the Fitness perk, which vanilla keeps gating by band.

**Balanced-diet bonuses** are the top of each ladder where the evidence supports one — vitamin D repletion and respiratory infection risk, iron repletion and work capacity, hydration and vigilance, adequate protein with training and lean gain — plus one **BalanceBonus** dial, on by default at strength one, labelled a game choice, that adds a small endurance-regeneration and fatigue-recovery credit while every tracked nutrient sits in its replete band.

No fainting state exists on this build, so hypoglycaemia and severe dehydration express through fatigue, speed and the temperature stat, and lethality through the health drain.

### 4.6 Item pass and data pipeline (default)

The pipeline is a tool under `tools/` following the repository's scanner conventions: a curated mapping from every food record's id to a USDA SR Legacy entry with a confidence column, the SR Legacy extract subset committed with provenance, the nutrient-id join on FDC's internal ids, iodine filled from the USDA/FDA/ODS iodine database or CoFID, cooked and raw states paired from measured SR entries where they exist and retention factors otherwise, and an Atwater energy cross-check with per-nutrient sanity ranges. It emits `data/food-nutrients.json` and, from it, two shipped artefacts: the per-type nutrient **Lua data table** and the **`module Base` partial blocks** that re-base `Calories`, `Carbohydrates`, `Proteins` and `Lipids` on every mapped food record. `HungerChange` and `ThirstChange` are left at vanilla, because hunger is the model's and the hunger key drives recipe cost, the portion menu, the cancel guard and displayed weight. Drinks are re-based only in the per-fluid Lua table, because `fluid` block merging is unread. Records without a mapping carry an explicit reason and a coverage test fails on a record with neither. The mapping works by composition family, since the 644 per-item food rows hold about 342 distinct macro tuples.

### 4.7 Interface (default)

The **panel** derives from `ISCollapsableWindow`, registers with `ISLayoutManager` for position persistence, and reads the client mirror at the push cadence, redrawing only on change. Its default view is symptoms and coarse bands with text; exact pools, intakes and per-food micronutrients appear when the character holds either Nutritionist trait or the server's **VisibilityMode** option allows them. The **keybind** and options live in `PZAPI.ModOptions`, with the mod calling its load once inside a protected call at boot as CleanUI does. The **tooltip** appends lines by wrapping `ISToolTipInv:render` idempotently and drawing into the space it makes, gated the same way as the panel, and the test plan notes that the harness's debug client shows vanilla's nutrition block without the trait. A **character-info tab** is added through the three wraps AutoCook demonstrates, with the restore-layout gap closed. **Moodles** are optional: when `MF.createMoodle` is a function the client creates one framework moodle per symptom class and sets its value from the mirror; otherwise a small own `ISUIElement` column draws the same icons in a fixed slot, anchored under the vanilla stack if `MoodlesUI` clears the exposure test. Translations ship as B42 `ItemName.json` and interface keys under the mod's prefix, and nothing server-side reads a display name.

### 4.8 Sync and persistence (default)

The **command bus** carries every mod value that crosses the wire, under a module name no resident mod uses. The server sends each player a **mirror message** — a flat table of scalars: grades, band, body composition, the panel's display values — on first sight, on any grade or band change, and otherwise at most once per minute; the client installs it and never writes back. Client requests are limited to "send me my mirror" on panel open. The engine's own pushes carry the vanilla stats the model writes; the trait packet carries band and perception traits after a mod-caused push; the global store is never transmitted, because the global transmit broadcasts a whole table to every connection. Every payload key is a string, number or boolean.

**Persistence** is the global modData table `NutritionRevamp.players`, keyed by username, holding per player a version field and the model's inputs only (pools, masses, stomach, flags), everything else derived on read so a formula change needs no migration. The server cache writes through on change; the engine saves the table with the world. A respawn resets the character's record on `OnNewGame`; a reconnect reloads it on first sight; a dead character's record is kept until its respawn. Whether the table survives a restart is experiment X28's to grade before any live scenario depends on it.

### 4.9 Packaging and compatibility (default)

Mod id `NutritionRevamp`, sandbox prefix `NR`, bus module `NutritionRevamp`. Layout: `common/` holds every Lua file and the data table; the version dir named for the verified build holds `mod.info` and `media/sandbox-options.txt`; the item pass's script files carry mod-unique basenames without a `template_` prefix; no file sits at a vanilla relative path. `versionMin` is declared for the verified build and no `versionMax`, with the failure mode (a gated mod reads as a missing one) documented for operators. No `require=`; MoodleFramework is detected, never required. Every Workshop update that changes a script file is documented as a server event because of the join checksum. Compatibility rules: the `CalculateStats` hook is stated as a wall against any other mod that registers it, with overlay mode as the remedy; the item pass does not reach foods other mods declare in their own modules; a status viewer with hard-coded bands miscalibrates on the re-based scale and is named. The layout lint runs on the folder before every boot.

### 4.10 Testing and proof (default)

Four tiers, every one a gate on its plan:

1. **Static.** The Kahlua rules as a lint over every Lua file; the layout lint; the claims checker and the science checker; a hot-path lint that flags allocation, string building, protected calls and Java lookups inside the fast clock.
2. **Unit.** The kernel runs offline under a Lua 5.1 host (`lupa`) from pytest, with line coverage collected through a debug hook and reported per file; the target is 100 % of kernel lines and every branch the config table can reach, plus property tests: mass balance closes, no pool goes negative, grades are monotone in intake, the takeover handler reproduces vanilla's seven updaters bit-close on the endurance report's formulas.
3. **Live scenarios.** The shipped model-versus-server shape: drive one input, sample the whole state hourly on the game-minute scheduler, integrate the kernel over the run's own trace, compare against what the server reports inside a stated tolerance — for body composition, for each nutrient's kinetics at a compressed onset dial, and for hunger and thirst under takeover. A vanilla baseline runs beside every mod run for the performance instrument.
4. **End to end.** Real eats through the client's eat action and real drinks through the harness's drink action, a multi-day scripted diet with deficiency onset, a rejoin and a restart for persistence, paired client-first reads of every mirrored value graded against a skew band, and a two-client session once the harness supports one.

Every measured claim lands as a committed artifact with its register row under the § 3 gates of `CLAUDE.md`, and a reading that comes back trivial or falsified is written as such.

## 5. Sub-projects and plan order

Each row is one spec-to-plan cycle under `superpowers:writing-plans` and `superpowers:subagent-driven-development`.

| plan | scope | gates before it | harness changes it lands first |
|---|---|---|---|
| 0 Documentation pass | register rows from the eight platform and jar reports' claims candidates; the supersessions and corrections in § 9; new facts pages (perks and strength, endurance-fatigue-sleep, perception-speed, health surfaces, server lifecycle), platform pages (sandbox options, client interface), the MoodleFramework teardown, the overview coverage table; area pages updated; the **science register** (`docs/reference/science.tsv`), its checker and its page; the three science reports distilled into rows | none | none |
| 1 Foundations | mod skeleton and lint; the kernel test harness (`lupa`, pytest, coverage hook); bus protocol and store; sandbox options file and read timing; the takeover handler reproducing the seven updaters with no nutrition terms yet; mode switch; profiles | X7 (which arms freeze with the option off), X28 (persistence), X4 as a mod-caused trait push, the `CalculateStats` handler's live verification | nested-key sandbox merge; the timing instrument; `drink.action`; a trait-push probe |
| 2 Intake | the three wrappers; the four-source vector; stomach and absorption; dish, craft, meat and fluid cases | X13 (drink wrap fires), X24 (eat hook per portion, for the cancel path) | a craft probe if X31 is needed for the creation map |
| 3 Energy and body | expenditure, balance, partitioning, masses, weight write, band push, strength ceiling, carry capacity | the perk-level write and anti-cheat rate on a live server | — |
| 4 Kinetics | the record engine, the records, calibration, interactions, water and electrolytes, dials | — | — |
| 5 Effects | the effects table and the five channels; perception; bonuses; lethality | trait-push measured (X4); speed-write window measured | probes for aiming delay and landing |
| 6 Item pass | the pipeline tool, the mapping, the data table, the script blocks, coverage tests | X15 (partial block without `ItemType`), X16 (checksum kick) | — |
| 7 Interface | panel, keybind, tooltip wrap, tab, optional moodles, translations | X29 (framework renders), X5 (translation override) | a click or key synthesiser if a panel state must be read by the bus |
| 8 Sync and persistence hardening | mirror cadence, rejoin, respawn, restart, two clients | X28 measured; a second driven client | second-client support in `pzt` |
| 9 Packaging and release | layout, manifest, Workshop discipline, compatibility pages, the operator guide | X20 and X22 if `common/` shapes are questioned | — |

## 6. Performance constraints

- **Budgets.** The takeover handler costs no more per player per tick than the seven vanilla updaters it replaces, measured. The slow clock's per-player pass is bounded and the players are staggered across the minute. The client redraws only on change and reads the mirror, never the engine, per frame.
- **Instrument before claim.** A harness addition times the handler and the minute pass from Lua and reports per-tick and per-minute costs; every performance claim is a mod run beside a vanilla baseline on the same fixture, committed as artifacts.
- **Fast-path rules.** No table allocation, no string building, no protected call and no Java member lookup per tick beyond hoisted handles; per-type data in one table loaded at boot, never per-instance modData copies; coefficient sets rebuilt on grade change only.
- **Review gate.** A reviewer checks each task's hot path against these rules; a measured regression fails the task.

## 7. Assumptions to re-review

Every default the controller took, for the review that closes the design phase:

1. The stomach model: first-order gastric emptying over hours with meal-composition scaling; the constants need science-register rows (energy report gap).
2. The initial fat and lean split from vanilla weight, build and sex, and the creation-band placements; the relation needs a cited row.
3. Sprinting expenditure by extrapolation from running; load carriage from secondary-sourced Pandolf coefficients.
4. Adaptive thermogenesis as a small bounded term.
5. Alpert's ceiling applied per game day with lean mass paying the overflow the same day.
6. Training signal = exercise actions and Strength and Fitness experience events.
7. The Strength ceiling relation (allometric) and the speed of strength restoration.
8. Vanilla experience preserved under a lowered level by storing the ceiling-clipped level separately from vanilla XP.
9. Two-compartment models for iron, vitamin A and B12 only.
10. Calibration to documented onset rather than raw half-lives; B12 at real scale.
11. The dehydration ruling (mild from 2 %, steepening to 4 %).
12. Refeeding as a risk state with both incidences documented.
13. Coefficients rebuilt only on grade change.
14. The five effect channels and their surfaces; perception through fatigue, the night-vision and short-sighted toggles, and moodle-driven speed; the direct speed write only for severe states.
15. Fitness tied to nutrition through endurance regeneration, the Fitness perk untouched.
16. The BalanceBonus dial: on by default, strength one, a labelled game choice.
17. No fainting; lethality only through the health drain behind the lethality dial.
18. The item pass re-bases the four macros only; hunger and thirst keys untouched; drinks only in the per-fluid table.
19. Per-type nutrients in a Lua data table rather than script keys.
20. The interface set: collapsible window, layout-manager persistence, `PZAPI.ModOptions` keybind, tooltip wrap, character-info tab, optional framework moodles with an own fallback column.
21. VisibilityMode as a server option beside the Nutritionist gate.
22. Mirror cadence: first sight, grade or band change, at most once per minute; client requests only on panel open.
23. Global modData `NutritionRevamp.players` keyed by username, inputs only, a version field, derived on read.
24. Respawn resets on `OnNewGame`; a dead record kept until respawn.
25. Mod id, prefix and bus module names.
26. `common/` for all Lua and data, the version dir for the manifest and the options file; `versionMin` only.
27. The plan order in § 5 and the gates assigned to each plan.
28. The performance budgets in § 6 and the 100 % kernel line-coverage target.
29. Takeover mode as the default with overlay as the fallback (a ruling, restated here because the compatibility wall is the design's largest external risk).

## 8. Open questions and experiments the plans must run

From the library's open rows: X7, X28, X4, X13, X24, X14, X15, X16, X29, X5, X17 (only if a runtime flip of the vanilla option is ever wanted; the design sets it in the sandbox file instead), X31 (only if the creation hook is needed for the craft map).

New from the research, to be named as experiments in Plan 0: whether the takeover handler reproduces vanilla's seven updaters bit-close on a live server; whether a server-side `sendSyncPlayerFields(player, 2)` after a trait write reaches the client (the measured half of N2); whether the client-side walk-speed variable write inside the push window holds; which side evaluates the Strength protein branch for a multiplayer player (N1); the global modData save cadence; the `#0561` wording conflict; the `OnCharacterDeath` caller.

## 9. Register impact queued for Plan 0

- Superseded or corrected: rows 0137 and 0181 (the Strength XP protein branch is live, N1); row 1239 and the G4 verdict (the trait packet exists and server Lua can send it, N2); row 0514 (the regen tier mapping is now read, not inferred); row 0561 (wording to re-read); rows 1467, 1477 and 1114 (the installed `simpleStatus` now caches and resolves `42.20/`); row 1104's second arm gains its mechanism; row 0186's protein clause narrows.
- New rows: every "Claims candidates" line of the eight platform and jar reports and the five controller notes, minted in the commits that land their pages, with the harvest source cell naming the report.
- The science register: a new register with columns id, parameter, value, range, population, grade (MA, RCT, COH, AUTH, TXT), citation with DOI or PMID, source report, status; its checker mirrors the claims checker's schema and pointer rules and adds a citation-form rule.
