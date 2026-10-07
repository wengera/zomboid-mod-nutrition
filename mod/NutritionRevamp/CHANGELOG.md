# Nutrition Revamp — release notes

## 1.0.0 — 2026-10-06

The first release, for game build 42.20.4 (`versionMin=42.20.4`, no maximum). Every script file is new, so this release is a server event: install it on the server first, then on clients. The operator guide is `README.md`; the neighbour table is `COMPATIBILITY.md`.

- **Foundations:** the mod folder (`common/` beside one `42.20.4/` version directory), the server store with a read-only client mirror over the mod's own command bus, nine sandbox options re-read every in-game minute, the takeover stat hook with an overlay fallback, and the one-line self-report on each side.
- **Intake and stomach:** every eat and drink captured on the server as a nutrient vector before vanilla consumes the item, through a stomach buffer, gastric emptying and absorption; dishes, crafted outputs and drinks included.
- **The body model:** a two-compartment body (fat mass and lean mass) driven by resting and activity expenditure, written into the vanilla weight slot and the weight band trait.
- **Nutrient kinetics and records:** one declarative record per tracked nutrient (pool, absorption, elimination, requirement, deficiency and excess ladders), plus the fast pools — water, sodium and potassium — that drive thirst.
- **The effects table:** deficiency and excess consequences applied through stat coefficients, trait toggles, body-damage multipliers and health drains, with adequacy never a bonus beyond the optional balanced-diet bonus.
- **Strength and training:** the Strength level held under a lean-mass ceiling with strength memory, and training routed through the body model.
- **The item pass:** 522 vanilla foods' calories, carbohydrates, proteins and lipids re-based from published food-composition data (18 invertebrates from the insect literature), with a per-food nutrient table, an inference for foods the table does not map, and a declared-nutrient key other mods can use for their own foods.
- **The interface:** a collapsible panel, a food-tooltip band, a character-info tab and optional moodles (MoodleFramework when present, the mod's own icon column otherwise), with the detail each player sees set by `NR.VisibilityMode`.
- **Sync and persistence:** the per-player record kept inputs-only and versioned (with a migration from the earlier record shape), surviving a reconnect, a respawn, a clean restart and a hard kill, and the intakes other mods' eat actions hide reconciled as macros.
- **Measured on a dedicated server:** each behaviour above was read on a live dedicated server, the later ones with two clients.

### Compatibility

The full table, with what the mod does about each neighbour and the evidence behind it, is `COMPATIBILITY.md`. In short:

- **Incompatible, said plainly:** Nutrition Makes Sense (a second complete hunger, energy and weight model; as designed; its code unread); the hunger and thirst tweaks (five mods), the fatigue writers (five) and the body-weight and metabolism mods (three), because this mod owns those stats and the weight slot (as designed; their code unread); SomewhatTraitsCore's adaptive-metabolism trait, whose calorie write fights the body model (its other stat writes are read as outside changes).
- **Inert under takeover, said plainly:** Nutrition Tweaker Enhanced and nine endurance tweaks (as designed; their code unread).
- **Coexists but redundant:** ApocalipseBR Nutrition Sync Fix — its poll and this mod's own sync would both push; disable its sync module (as designed; its code unread).
- **Named semantic incompatibility:** SWMisc_Patches strips the Fitness boost from the Underweight and Overweight trait definitions at load; invisible at runtime.
- **Read the code before relying on it:** StatsAPI and Stat Tweaks Lib — if either claims the stat hook, run in Overlay mode (as designed; their code unread).
- **Load-order rule:** Reasonable Nutrition and Realistic Nutrition, rival item passes; the per-key merge of item blocks resolves by script path, not by `Mods=` order (as designed; their code unread).
- **Rule, composes:** QualityCooking (its eat wrap composes with this mod's; under takeover its stat writes are discarded — a patch mod may follow as its own item); BeyondTen (the Strength ceiling reads the perk's maximum at runtime; its endurance write is an outside change); GirthsTweaks (its multiplayer sleep is read as a sleep); EmergencyVomit (a vomit is an outside event the model reads, never fights); SkillRecoveryJournal (its protein-scaled multiplier is unwired in its current build; its tooltip lines can vanish while its own tooltip shows); simpleStatus and other macro viewers (the legacy mirror keeps their bars meaningful).
- **Rule:** Evolving Traits World and other runtime trait systems (traits the mod owns are re-asserted every slow tick; Evolving Traits World read from its author's repository, its Workshop copy unread); Tooltiplib and the tooltip mods (the tooltip wrap is idempotent; Tooltiplib as designed; its code unread).
- **Optional:** MoodleFramework, detected on the client and never a dependency.
