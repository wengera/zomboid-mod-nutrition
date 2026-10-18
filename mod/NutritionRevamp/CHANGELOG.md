# Nutrition Revamp — release notes

## 1.0.0 — 2026-10-13

The first release, for game build 42.21 and newer (`versionMin=42.21`, no maximum). Every script and Lua file is new, so this release is a server event: install it on the server first, then on clients. Every later code release changes a Lua file and is a server event too. The operator guide is `README.md`; the neighbour table is `COMPATIBILITY.md`.

- **Managed and Overlay:** in Managed mode (the default) vanilla's hunger, thirst and fatigue rates are set to zero at server start and the mod writes those stats once a game minute; in Overlay vanilla's stats stand and the mod writes only its effects. The mode is read at start.
- **Nutrients beyond the macros:** 27 tracked nutrients and substances, most with a daily requirement and steps of deficiency and excess, absorbed through a stomach that empties over time; the magnesium, niacin, folate and vitamin E upper limits count supplemental or added forms only, so food alone never raises their excess.
- **Re-based foods:** 522 vanilla foods' calories and macros re-based on published food-composition data, with a per-food nutrient table, an estimate for unmapped foods and a declared-nutrient key for other mods' foods.
- **Satiety from physiology:** hunger from the stomach's fullness, a pool of recently eaten energy and the energy-deficit drive, shaped by the time of day, hard exercise, sleep debt and nicotine withdrawal; an Overfull moodle past a comfortable stomach.
- **Thirst:** a body water pool with sodium and potassium, sweat and basic losses.
- **The body:** fat mass, lean mass and a labile lean written into vanilla's weight; the weight band traits follow body fat, not weight (Overly Lean, Gaunt and Emaciated below 12, 8 and 5 % body fat; Overfat and Obese at fat cuts scaled by the body's lean), under the mod's names; a body that lost fat from its own reference grows hungrier past a tenth of it lost.
- **Strength from lean mass:** the Strength level reads lean mass, a trained neural factor and an innate factor set by the muscle trait; vanilla's Strength experience is the training signal and never moves the level; growth needs training, protein and energy together and slows toward a natural cap; muscle detrains after two weeks without training and comes back fast toward a remembered peak; the level rises at a whole number and falls only a quarter level below it; with BeyondTen the mod writes its Strength mastery above 10; 34 sandbox options tune it. Exercise billed by type.
- **Character creation:** Weak, Feeble, Stout and Strong at their vanilla costs and start levels, built from lean mass; Overfat and Obese (giving 6 and 10 points) start with more fat, Overly Lean and Gaunt (giving 6 and 10 points) with less fat and hungry until it is regained; a profession's Strength boost raises the start like a small trait; the server re-checks the points and exclusions and strips an illegal pick. `NR.SexSpecific` (off by default): off, every character uses the male values wherever the mod indexes by sex.
- **Effects:** deficiency and excess effects on fatigue, mood, sickness, healing, colds, body temperature and traits, with health drains for the most severe states.
- **Caffeine, alcohol and sleep debt**, and monotony from eating one food day after day.
- **The interface:** a panel (with a Body fat word and the body's true Strength level at the Bands view), a food-tooltip band, a character-info tab and five optional moodles (MoodleFramework when present, the mod's own icon column otherwise), with the detail set by `NR.VisibilityMode`; the mod's own icon column takes no mouse input, and an excess the panel's rows would not otherwise show (selenium, vitamin E) gets its own row.
- **Records:** each player's record kept in files under the server's cache folder, written at most once a real minute and after each eat, drink or respawn, and pruned after `NR.RecordKeepDays` real days offline; nothing about a character changes while its player is offline: the record resumes exactly as it was left, and a record day closes after 24 online game hours, so the body, training and Strength stand still while away.
- **Self-report:** one line on each side at boot, and a boot warning when Nutrition Makes Sense is also loaded.

### Game feel (since 2026-10-13, before the first upload)

The mod now plays alongside the game's own rhythm: hunger and thirst follow vanilla's pace and moodles, and the deadly states take health as damage to a floor instead of a hidden clock.

- **Hunger on vanilla's rhythm:** a satisfying meal reads as fed, and Peckish and Hungry come back on about vanilla's schedule through the day; a hunger level steps down only once hunger is a little under its threshold, so a moodle no longer flickers.
- **Starving and Parched show again:** in Managed mode the top Hungry and Thirsty moodles appear when the body truly starts to starve (about thirty hours without food, near vanilla's time) or reaches a 4 % body-water deficit (about 32 hours without water at rest). While they show, the game's own starvation and thirst health loss is off for that player, and the mod puts back the game's other health losses that share that setting (sickness, bleeding, heavy load, weight under 35 kg).
- **Health drains to a floor, not a death clock:** starvation, dehydration, clinical scurvy, beriberi and pellagra, very low blood sodium and an iron overdose each drain health at their own pace to a floor, first half health, that deepens only as the state worsens and reaches zero at the state's real death point: starvation at a BMI of 12 (about two months with water), dehydration at a 17 % deficit (under a week), beriberi about five weeks after it turns clinical, scurvy after 90 days and pellagra after 180. Floors stay above the level where the game wakes a sleeper until the last stage. While a drain runs, regeneration and the food heal pause and wounds still mend toward the floor. No option turns the drains off.
- **Snacks and starvation:** eating 600 kcal or less over the last three to four days keeps a starving body Starving between meals, and only a real meal or snack of about 200 kcal or more ends the state; a floret an hour no longer does.
- **Starvation in phases:** weakness first, then cold intolerance and slower healing from about day 3, then infections and low mood from about day 14.
- **Water by body size:** basic water loss is about 2 litres a day for the average body and more for a bigger one. High Thirst raises it by half and Low Thirst halves it; the game's stat-speed option scales it too.
- **Thiamine:** beriberi now turns clinical after about six weeks with none eaten.
- **Fullness by weight and volume:** an airy food fills a little more than its weight alone; drinks count at their own weight in the stomach.
- **Overfull has teeth:** the third step slows the body like a heavy load; at the fourth the character feels queasy and the game's own refusal stops the next eat until the stomach empties (water stays allowed). No vomiting.
- **Water passes a meal:** water drunk with or after a meal leaves the stomach in about a quarter of an hour, as on an empty stomach; only a drink's own calories slow it. A meal and a bottle of water no longer hold the top Overfull step for long.
- **Well Fed:** a satisfying meal shows vanilla's Well Fed for about half an hour with a gentle heal, at every day length.
- **The interface:** the Energy and Hydration moodles are gone; the Deficiency moodle reads only nutrients whose shortage has an effect; a new option hides the first level of the Stimulant, Sleep and Excess moodles; the panel adds a line for each health-draining state, a weight trend (losing, steady or gaining) and the dehydration per cent; the food tooltip now opens with about how long a whole one fills you, in place of vanilla's hunger line; monotony's mood floor no longer flickers at its edge.
- **Coffee, beer and hangovers:** a new option, `NR.StimulantRealism`, Game (the default) or Realistic. Game: a cup eases fatigue about twice as much as vanilla's, four beers within an hour reach about vanilla's first Drunk level, and the hangover is mild and short. Realistic keeps the stronger pharmacological sizes. Timing follows the science in both.
- **A fresh start:** a new character eats a fresh plate of ordinary food before the mod's first minute, so its first hunger reads like the game's own spawn.
- **Overlay:** vanilla's own starvation and thirst deaths run there as in the base game; the mod's starvation and dehydration drains do not, and its other drains still do.

### Compatibility

The full table is `COMPATIBILITY.md`. In short:

- **Incompatible:** Nutrition Makes Sense (the server log warns at boot when both are loaded); mods that replace the hunger, energy or weight model, fatigue writers, and body-weight and metabolism mods; SomewhatTraitsCore's adaptive-metabolism trait.
- **No effect in Managed mode:** Nutrition Tweaker Enhanced and other hunger, thirst and fatigue rate tweaks; endurance tweaks stand.
- **Inert on 42.21 or on a dedicated server:** StatsAPI and Stat Tweaks Lib.
- **Unavailable to read:** ApocalipseBR Nutrition Sync Fix.
- **Load-order rule:** Reasonable Nutrition and Realistic Nutrition, rival item passes.
- **Rules that compose:** QualityCooking, BeyondTen, GirthsTweaks, EmergencyVomit, SkillRecoveryJournal, simpleStatus and other macro viewers, Evolving Traits World and other runtime trait systems, Tooltiplib and the tooltip mods.
- **Rule:** SWMisc_Patches strips the Fitness boost from two weight band trait definitions and edits their exclusions at load; the mod's restated weight blocks carry no Fitness boost, so its strip finds none, and its exclusion edits would reach the restated blocks, which the server's creation check reads (unmeasured).
- **Optional:** MoodleFramework.
