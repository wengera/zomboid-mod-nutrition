# Nutrition Revamp — release notes

## 1.0.0 — 2026-10-13

The first release, for game build 42.21 and newer (`versionMin=42.21`, no maximum). Every script and Lua file is new, so this release is a server event: install it on the server first, then on clients. Every later code release changes a Lua file and is a server event too. The operator guide is `README.md`; the neighbour table is `COMPATIBILITY.md`.

- **Managed and Overlay:** in Managed mode (the default) vanilla's hunger, thirst and fatigue rates are set to zero at server start and the mod writes those stats once a game minute; in Overlay vanilla's stats stand and the mod writes only its effects. The mode is read at start.
- **Nutrients beyond the macros:** 27 tracked nutrients and substances, most with a daily requirement and steps of deficiency and excess, absorbed through a stomach that empties over time; the magnesium, niacin, folate and vitamin E upper limits count supplemental or added forms only, so food alone never raises their excess.
- **Re-based foods:** 522 vanilla foods' calories and macros re-based on published food-composition data, with a per-food nutrient table, an estimate for unmapped foods and a declared-nutrient key for other mods' foods.
- **Satiety from physiology:** hunger from the stomach's fullness, a pool of recently eaten energy and the energy-deficit drive, shaped by the time of day, hard exercise, sleep debt and nicotine withdrawal; an Overfull moodle past a comfortable stomach.
- **Thirst:** a body water pool with sodium and potassium, sweat and basic losses.
- **The body:** fat and lean mass written into vanilla's weight and weight band traits.
- **Strength and training:** the Strength level held under a lean-mass ceiling with a training memory; exercise billed by type.
- **Effects:** deficiency and excess effects on fatigue, mood, sickness, healing, colds, body temperature and traits, with health drains for the most severe states.
- **Caffeine, alcohol and sleep debt**, and monotony from eating one food day after day.
- **The interface:** a panel (with a sex-specific Body fat word at the Bands view), a food-tooltip band, a character-info tab and seven optional moodles (MoodleFramework when present, the mod's own icon column otherwise), with the detail set by `NR.VisibilityMode`; the mod's own icon column takes no mouse input, and an excess the panel's rows would not otherwise show (selenium, vitamin E) gets its own row.
- **Records:** each player's record kept in files under the server's cache folder, written at most once a real minute and after each eat, drink or respawn, and pruned after `NR.RecordKeepDays` real days offline; a player's time offline is skipped, not simulated: no sleep debt, monotony fade or nicotine-quit progress builds while away.
- **Self-report:** one line on each side at boot, and a boot warning when Nutrition Makes Sense is also loaded.

### Compatibility

The full table is `COMPATIBILITY.md`. In short:

- **Incompatible:** Nutrition Makes Sense (the server log warns at boot when both are loaded); mods that replace the hunger, energy or weight model, fatigue writers, and body-weight and metabolism mods; SomewhatTraitsCore's adaptive-metabolism trait.
- **No effect in Managed mode:** Nutrition Tweaker Enhanced and other hunger, thirst and fatigue rate tweaks; endurance tweaks stand.
- **Inert on 42.21 or on a dedicated server:** StatsAPI and Stat Tweaks Lib.
- **Unavailable to read:** ApocalipseBR Nutrition Sync Fix.
- **Load-order rule:** Reasonable Nutrition and Realistic Nutrition, rival item passes.
- **Rules that compose:** QualityCooking, BeyondTen, GirthsTweaks, EmergencyVomit, SkillRecoveryJournal, simpleStatus and other macro viewers, Evolving Traits World and other runtime trait systems, Tooltiplib and the tooltip mods.
- **Named semantic incompatibility:** SWMisc_Patches strips the Fitness boost from two weight band traits.
- **Optional:** MoodleFramework.
