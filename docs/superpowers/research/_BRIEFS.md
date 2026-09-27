# Research briefs — design phase, commissioned 2026-09-27

Thirteen fresh Opus subagents were dispatched from the brainstorm session with the briefs below. Each writes one report into this directory. A report missing from this directory when a session resumes is re-commissioned from its brief here, verbatim in substance. The shared preamble applies to every brief.

## Shared preamble

Research only. Do not modify anything in the repository except the one report file named; never commit. Toolchain at `C:\Users\Angus\pz-b42` is read-only (`./pz.sh grep|methods|refs|dump <class> [method]` from bash with `cd /c/Users/Angus/pz-b42`); read its `WORKSPACE.md` first, then `docs/platform/jar-research.md` (cite as `Class.method @off L<n>`; prove absence with a jar-wide grep; check access flags; check Lua exposure against the `LuaManager$Exposer` class set). The install at `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop tree at `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only. Every report carries `## Summary for the design` (10-20 plain sentences), the lettered findings sections with tables, `## Claims candidates` (one line per fact worded as a claim with its cite, grade C, bound "C-only" or "snapshot" dated for corpus reads) and `## Not read`. Science reports: never fabricate or guess a citation; every citation carries a DOI or PMID verified by fetching the PubMed, publisher or Crossref page; grade MA (meta-analysis or systematic review), RCT, COH (cohort or depletion study), AUTH (IOM/NASEM DRI, EFSA, WHO), TXT (textbook or review); end with `## Gaps` and `## Bibliography`. Return only a 10-line summary and the report path.

## jar-perks-strength.md

Design question: Strength capped by and growing with a mod-computed lean body mass; Fitness tied to nutritional state. Read first `docs/platform/lua-platform.md#java-members`, `#registries` and `docs/facts/body-and-weight.md#weight-traits`.
A. The perk API reachable from Lua: every method on `IsoGameCharacter`/`IsoPlayer` and the experience object that reads or writes a perk's XP or level (getters, `AddXP` overloads and their multipliers — trait boosts, `getMultiplier`, sandbox XP multipliers — `setXPToLevel`, level-up/down, `LoseLevel`, `setPerkLevelDebug`, anything that caps a level); signature, flags, class exposure, callable from Kahlua.
B. Which side owns perk XP and level in multiplayer; the packet or class that carries perks (a Cooking level set on the server reached the client on the next read); whether a client-side XP write reaches the server; the XP-gain event surface exposed to Lua and which side fires it.
C. Every Java consumer of the Strength level and of the Fitness level (melee damage, push/shove, carry capacity via `BodyDamage.UpdateStrength`, climbing, endurance drain and recovery, combat speed, knockback, bashing), formula or branch as read, Lua-wrappable or Java-only; whether "effective strength" can be imposed without changing the perk level and via which exposed setter.
D. Fitness and Strength XP-gain sources (`ISFitnessAction`, combat XP, sandbox multipliers, `canAddFitnessXp`), any regularity, muscle-strain or skill-rust mechanism on this build and its Lua surface.
E. Absences proved by jar-wide grep.

## jar-endurance-fatigue-sleep.md

Design question: endurance, fatigue and recovery answering to nutritional state, written on the server through the stats object each game minute without flicker or erasure. Read first `docs/facts/body-and-weight.md`, `docs/platform/mp-model.md#ownership`, `docs/facts/wire-packets.md#player-stats-packet`.
A. The complete `CharacterStat` enum and the `Stats` API; which stats the player-stats packet carries.
B. `updateEndurance` in full: drain per state, regen (`getRecoveryMod`, the Fitness curve, resting and sleeping multipliers, `EnduranceRegenMultiplier`), every trait or modifier.
C. Fatigue and sleep: accumulation formula, the sleep-allowed and sleep-needed gates, the multiplayer reset, how sleep restores, the Lua surface for forcing or blocking sleep, Tired moodle thresholds and effects, whether a server with sleep disabled pins fatigue.
D. Every public setter on `IsoGameCharacter`/`IsoPlayer` whose name contains Mod, Modifier, Multiplier or Speed: flags, exposure, which side reads it, whether a server write survives the push and whether any packet carries it.
E. `Thermoregulator`: exposure, setters, whether it reads weight or a fat term, the primary and secondary total inputs.
F. Absences.

## jar-perception-speed.md

Design question: vision range and cone, dark vision, hearing, reaction and combat speed, movement speed answering to nutritional state; what is settable, from which side, and whether it syncs. Read first `docs/platform/mp-model.md#ownership`, `#what-a-client-copy-is`, `docs/platform/lua-platform.md#registries`.
A. Vision: how the engine computes view cone and distance, the trait readers (Eagle Eyed, Short Sighted, Cat's Eyes), the dark-vision mechanism, LOS/lighting, which side computes each, every public setter, what packets carry the fields.
B. Hearing: the same for hearing range and the Keen Hearing / Hard of Hearing readers.
C. Movement speed: every modifier entering walk/run/sprint speed, which side applies it, every exposed setter and its sync.
D. Combat and reaction: attack speed and swing delay modifiers, critical chance, other reaction surfaces; side, setters, packets.
E. Dynamic traits: whether a server-side trait add or remove at runtime is carried to clients; the callers of `CharacterTraits.write/read` and which packet or save path each belongs to.
F. Absences.

## jar-dishes-item-nutrients.md

Design question: ~25 nutrients per food; per-instance cases are evolved dishes, split craft outputs, split portions, animal meat with per-animal ratios, fluid containers. Read first `docs/facts/cooking-and-recipes.md`, `docs/facts/eating-pipeline.md`, `docs/areas/new-nutrients.md`, `docs/facts/wire-packets.md#item-stats-packet`, `#moddata-packet`.
A. Evolved dishes: does a `Food` instance carry its ingredient list (`getExtraItems`, `getSpices`, storage form, save/load, `ItemStatsPacket` and `SyncItemFieldsPacket` carriage), and does it preserve each ingredient's contributed amount or only the type.
B. The summation: what `EvolvedRecipe.addItem` writes, any Lua hook or event inside it, whether it copies ingredient modData to the dish, the Cooking-skill scaling.
C. Craft recipes: the exact method behind "an input flagged to pass its food on gives every output a share", what it copies, whether `OnCreate` or an event fires with the input available.
D. `IsoAnimal.modifyMeat` and `Food.copyNutritionFromRatio`: what they scale and whether the factor is recoverable from the instance.
E. Item modData at eat time on the server: exposure, whether the default modData copy is per instance or shared, proof that `multiplyFoodValues` does not touch modData.
F. Fluids: whether the fluid loader keeps unrecognised keys anywhere reachable, the `FluidContainer` API to read the fluid mix and amounts, and how `ISDrinkFluidAction` calls `DrinkFluid` incrementally (file and lines) so a server-side wrapper knows what to wrap.
G. Absences.

## jar-health-surfaces.md

Design question: deficiency and excess states expressed through health and regeneration, wound healing and bleeding, infection resistance, fracture risk, sickness, pain, thermal tolerance, mood and the body-part model. Read first `docs/facts/body-and-weight.md#moodles`, `#weight-traits`, `docs/platform/mp-model.md#ownership`, `docs/facts/wire-packets.md#player-stats-packet`.
A. `BodyDamage` API as exposed to Lua: overall health getters and setters, the regeneration path and its tiers, `healthFromFoodTimer`, sickness and poison and infection fields, pain, temperature; signature, flags, exposure, owner side, packet carriage.
B. `BodyPart` API: bleeding, bandage, wound healing rates, fracture, deep wound, infection, stiffness, per-part health; which side updates and how a client learns of a change.
C. The mood `Stats` fields (stress, panic, unhappiness, boredom, drunkenness, pain, sickness) with moodle thresholds and the server guard in their updaters.
D. `Thermoregulator` public setters for resistance or insulation only.
E. Death and knock-out surfaces a fatal or fainting effect would use.
F. Absences.

## science-energy-body.md

Scope: energy, body composition, muscle, hydration, starvation. 1 REE equations (Mifflin-St Jeor, Harris-Benedict revised, Katch-McArdle/Cunningham; validation reviews; FFM vs FM scaling; adaptive thermogenesis). 2 Activity energy: Compendium MET values for the game's states, kcal per kg per km approximations, load-carriage equations (Pandolf), cold thermogenesis. 3 Body composition dynamics: energy density of FM and FFM change, Forbes curve and Hall p-ratio, maximum fat-oxidation rate in starvation, overfeeding partitioning, regain. 4 Protein and muscle: intake for gain and retention, per-meal distribution, hypertrophy rates, loss in immobilisation, bed rest and starvation, deficit with and without protein and training, protein-energy malnutrition consequences. 5 Muscle memory: myonuclear retention, retraining vs initial gain rates, what is supported in humans. 6 Strength vs lean mass: allometric scaling, neural share of early gain, strength loss per unit muscle loss, strength in obesity. 7 Hydration: requirements, sweat rates, the 2 percent threshold for endurance, cognition thresholds, time to death, hyponatraemia. 8 Starvation timeline: fasting days 1-3, ketosis, survival range, BMI thresholds, refeeding syndrome, semi-starvation cognition and mood. 9 Obesity effects relevant to a survival game.

## science-vitamins.md

Scope: A, D, E, K, C, B1, B2, B3, B5, B6, B7, B9, B12, choline. Per vitamin: EAR, RDA/AI, UL (DRI citations); body store and depletion kinetics with time to biochemical depletion and to clinical signs; deficiency effects with magnitudes (fatigue and work capacity, wound healing, bleeding, dark adaptation, immune function and infection risk, bone, neurological, mood and cognition, anaemia, cardiac, lethality timelines); excess and toxicity; repletion speed; relevance flags for the game's 1993 Kentucky scavenged diet with USDA FoodData Central values and cooking and canning loss fractions. Cross-cutting interactions section.

## science-minerals-fibre-fats.md

Scope: sodium, potassium, chloride, calcium, magnesium, phosphorus, iron, zinc, iodine, selenium, copper, manganese; dietary fibre; omega-3 and omega-6 essential fatty acids; carbohydrate quality; alcohol and caffeine as they interact with hydration, sleep and nutrient status. Per item: requirement (EAR, RDA/AI, UL, CDRR); store and depletion kinetics; deficiency effects with magnitudes (iron and endurance, zinc and immunity and wound healing, iodine, electrolyte weakness and cramps and hyponatraemia, magnesium, bone, selenium, fibre and gut, EFA deficiency timeline, low-carbohydrate and high-protein performance); excess and toxicity; sweat and loss modelling (sweat sodium and potassium concentrations and rates by exertion and heat); alcohol diuresis, sleep and coordination dose-response; caffeine diuresis, sleep latency, alertness; relevance flags for the game's diet.

## platform-sandbox-options.md

Design question: a public-Workshop mod's own sandbox options, set by an operator and read identically on the server and every client. Read first `docs/facts/body-and-weight.md#sandbox`, `docs/facts/eating-pipeline.md#sandbox`.
A. Declaration: the `sandbox-options.txt` format and location, the loader class and method, `common/` vs version dir, the Lua exposure (`SandboxVars.<ModId>.<Option>` or otherwise, citing the mirror-building code), translations; SkillRecoveryJournal (workshop 2503622437) and other installed mods as worked examples with file paths and lines.
B. Sync: how the server's values reach a joining client, whether mod options are included, when `SandboxVars` is rebuilt relative to arrival and to mod Lua load, what a file-scope read gets vs an event-time read.
C. Runtime change: the admin panel's `sendToServer` path, whether an event fires on change.
D. Presets and the server's sandbox file: how a mod option is written and read back, what happens when the file predates the mod, how the harness's `[sandbox]` profile block would set one.
E. Absences. Plus `## Worked example`: a minimal correct `sandbox-options.txt` with the read on each side, labelled as derived.

## moodleframework-desk-read.md

Desk read of MoodleFramework (workshop 3396446795) and the vanilla moodle Lua and Java it touches. Read first `docs/areas/ui-and-moodles.md`, `docs/facts/other-mods/catalog.md#status`.
A. The public API a consumer calls (registration, value and level setting, thresholds, texture, text, polarity), signatures and file:line, naming which version folder each file lives in and which copy 42.20.4 executes under the merge rule.
B. Mechanism: engine `MoodleType` registration or own widgets, hooks and events, sides its files run on, what happens to a value across the wire.
C. Multiplayer: bus or modData use, player modData transmits, what a server-authoritative consumer must do.
D. Robustness: version-folder layout and diffs, removed-API hazards, runtime detection global and timing.
E. Alternatives in vanilla moodle UI Lua for drawing a custom stack without the framework. Plus `## Minimal consumer`, labelled untested.

## platform-client-ui.md

Design question: a movable, collapsible client panel with a keybind; extra lines on a food tooltip; a character-info tab; possibly a custom icon stack, all without shadowing a vanilla Lua file. Read first `docs/areas/ui-and-moodles.md`, `docs/facts/other-mods/simplestatus.md`.
A. Panel toolkit: ISUI base classes and conventions, position persistence, the keybinding and mod-options surface on this build (`PZAPI.ModOptions` if present), font and texture loading.
B. Food tooltip: how `ISToolTipInv` renders and where a mod appends lines idempotently without shadowing; Java `ObjectTooltip`/`Food.DoTooltip`; whether CleanUI ships `ISToolTipInv.lua`.
C. Character info window tabs (AutoCook's `ISCharacterInfoWindow_AddTab.lua` quoted) and the health panel extension point.
D. Vanilla moodle UI and whether a mod can draw its own column; texture layout.
E. Client events and cadence with the library's cost caveat.
F. Absences. Plus `## Minimal shapes`, labelled untested.

## platform-server-lifecycle.md

Design question: on the dedicated server, when a player object exists and is ready (join, creation, respawn, reconnect), when it leaves and dies, how to address it, so a server-authoritative store can initialise, load, mirror and stop ticking. Read first `docs/platform/lua-platform.md#events`, `docs/platform/mp-model.md#player-moddata`, `#command-bus`.
A. Every Lua event the server fires carrying a player or connection: `triggerEvent` call sites in `GameServer`, `ServerMap`, `NetworkPlayerAI`, the packet receivers, `IsoPlayer` and the death path; arguments, moment in the join sequence, side; which the client fires too.
B. The server player registry: `getOnlinePlayers`, lookups by online id and username, the stable identifier across a reconnect, whether a respawn is a new object with fresh modData.
C. Durable per-player storage: `IsoPlayer.getModData` save path and timing on the server; global modData (`ModData.getOrCreate/transmit/add/exists`, the two events), where and when it is saved, what `transmit` sends and to whom.
D. Server-side per-minute and per-tick hooks that see every player and their order relative to the 1000 ms stats push.
E. Absences. Plus `## Recommended lifecycle`, labelled untested.

## food-data-pipeline.md

Scope: the food-composition data pipeline for the item pass. Read first `docs/reference/datasets.md`, `data/README.md`, a sample of `data/food-items.csv`.
A. Source candidates: USDA FoodData Central variants (licence, size, format, nutrient id conventions, API key needs), alternatives only where USDA lacks a nutrient (iodine), verified download URLs.
B. Retention factors: the USDA nutrient retention table, canning losses for vitamin C and thiamine, application across the game's states.
C. Mapping strategy for ~700 game food names to FDC entries with confidence, portion weight sources, evolved dishes and fluids.
D. Pipeline shape under `tools/` with this repository's conventions and its test surface.
E. Validation cross-checks: Atwater energy vs FDC energy, sanity ranges, vanilla macros vs FDC for ten sampled foods. Plus `## Recommended pipeline`, `## Gaps`, `## Sources`.
