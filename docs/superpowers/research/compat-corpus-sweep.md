# Compatibility sweep — the installed corpus and vanilla Lua against the nutrition mod's surfaces

Research note for the nutrition mod design (spec `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` §§ 4.1, 4.5, 4.7, 4.9).
Scope: **shipped files only**. Nothing was booted, so every line below is a read of a file on disk at the stamp in `## Method`, never a reading of behaviour in play. The corpus tree is live and Steam rewrites it under a sweep ([`platform/lessons.md#corpus-drift`](../../platform/lessons.md#corpus-drift)), so every count carries its minute.

## Summary for the design

A compatibility sweep of the installed workshop corpus — 182 items, 234 mod folders, 2 404 live Lua files and 2 445 live script files — plus the game's own 1 395 Lua files, against the ten surfaces the nutrition mod touches, on 2026-09-27. Nothing was booted. **108 of the 234 mod folders hit at least one surface**, but the hits concentrate: seven mods carry every collision that matters, and one of them arrived after the library's last inventory.

**The three most consequential findings.**

1. **`Hook.CalculateStats` is uncontested, corpus-wide, and not reachable from vanilla's own Lua either.** A grep of every `.lua` in all 234 mod folders and all their version dirs — not just the live ones — returns **zero** hits for `CalculateStats`, `LuaHookManager` and `TriggerHook`. The only `Hook.<name>` use anywhere in the corpus is CleanUI's `Hook.AutoDrink.Add/Remove`, and that is a verbatim carry-over from its fork of vanilla's `ISInventoryPaneContextMenu.lua`. Vanilla's own `media/lua` uses `Hook.AutoDrink`, `Hook.ContextualAction` and `Hook.Attack` and never `Hook.CalculateStats`. So the takeover mode of § 4.1 has no rival on this server today, and the overlay fallback is insurance against a mod that is not installed here rather than against a resident.
2. **A brand-new resident, `QualityCooking`, collides with the mod on five surfaces at once — including the exact eat seat § 4.2 claims.** It arrived on the resident Girth Workshop item `3624538051` after the library's 2026-09-10 inventory (which knew five mods on that item; there are now six). It wraps `ISEatFoodAction.complete` **and** `ISEatFoodAction.eat` in a `server/` file, non-idempotently and with no sentinel; it reads the four macro keys off the eaten food to score a buff, so the item pass re-bases its inputs; it runs an `EveryOneMinute` **server** clock that `stats:add`s `ENDURANCE`, `FATIGUE` and `HUNGER` using vanilla's own `ZomboidGlobals` constants; it calls `player:setMaxWeightBase` and caches the pre-buff base to restore later; it calls `syncPlayerStats` with the hunger bit; and it creates a `MoodleFramework` moodle. This is the one mod in the corpus that must be read line by line before the mod ships.
3. **The `setMaxWeightDelta` / `setMaxWeightBase` split in § 4.3 is already load-bearing, and the spec picked the right side by luck or by judgement.** `setMaxWeightDelta` has **zero** corpus hits; `setMaxWeightBase` has two, both in `QualityCooking`'s minute ticker, and one of them restores a **cached** base value on expiry. Had the mod written base, QualityCooking's expiry would have reverted it to a stale snapshot. Writing delta keeps the two writers on disjoint fields.

**Which residents collide with which surface.** `QualityCooking` collides on the eat seat (5), the stat writes (2), carry weight (4), the moodle bridge (7) and the minute clock (10). `SomewhatTraitsCore` collides on the stat writes (2) — 28 server-side `stats:add`/`:remove` calls on endurance, fatigue, stress, unhappiness, boredom and intoxication from **24 `OnTick` handlers** — and wraps `ISEatFoodAction.getDuration` and `ISDrinkFluidAction.getDuration` in `shared/`. `GirthsTweaks` collides on the stat writes: `ST_MPSleep.lua` sets `FATIGUE` to zero and writes `ENDURANCE` on the server, which is a second owner of two stats the fast clock writes every tick. `BeyondTen` collides on the perk surface — `setXPToLevel` on both sides, `Events.AddXP` listeners on both sides — and sets `ENDURANCE` in `shared/`. `SkillRecoveryJournal` collides on the tooltip (it wraps `ISToolTipInv:render` and, in its own tooltip path, calls a **forked copy** of vanilla's render instead of the chain), on `sendSyncPlayerFields` (bit `0x1`) and on `canAddFitnessXp`. `AutoCook` is the sole owner of the three `ISCharacterInfoWindow` wraps § 4.7 plans and the sole `ISLayoutManager.RegisterWindow` caller in the corpus. `MoodleFramework` is the framework, with two other consumers already on it (`QualityCooking`, `MoreDifficultZonesB42`). `simpleStatus` reads the macros and the weight trend client-side and its live folder has moved `42.16 → 42.20` since the catalog's cites were taken. `SKITTLE_LongTermPreservation4220` and `Horse` touch only script data the pass does not reach.

**Which surfaces are uncontested.** Besides the hook: `setMaxWeightDelta`, `applyTraitFromWeight`, any `getNutrition():set*` call, `ReduceGeneralHealth`, `AddGeneralHealth` on the player's own body outside one lab mod, `setOverallBodyHealth`, `setCatchACold`, `setWoundInfectionLevel`, `setInfectionGrowthRate`, `setAimingDelay`, `CharacterStat.TEMPERATURE`, `ISEatFoodAction:serverStop`, `ISEatFoodAction:isValid`, `ISDrinkFluidAction:updateEat`, `MoodlesUI` (no mod touches it; vanilla itself calls `MoodlesUI.getInstance():wiggle`, so the exposure test § 4.7 wants has a vanilla precedent), a `module Base` item block naming a vanilla **food**, any redefinition of a vanilla **fluid**, and any `evolvedrecipe` block. The bus module name `NutritionRevamp` and the sandbox prefix `NR` are both absent from the corpus's 118 bus strings and 47 sandbox prefixes. No mod reads `SandboxVars.Nutrition`, so nothing branches on the vanilla option the takeover turns off.

**Where the design must act.** The trait-definition mutators are the quiet hazard: `SWMisc_Patches` strips the `Perks.Fitness` XP boost off the **Underweight** and **Overweight** trait definitions at load, in `shared/`, so the band traits § 4.3 refreshes carry different meaning on this server than in vanilla, and `KeenPerception` and `SomewhatTraits` rewrite mutually-exclusive trait lists the same way. The tooltip is a seven-deep non-idempotent wrap chain before the mod adds its own. The minute tier the slow clock wants already carries about eighteen handlers that run on a dedicated server, and the per-tick tier about fifty-five, twenty-four of them one mod's. And the corpus has drifted: 182 items / 234 folders today against 179 / 230 on 2026-09-10, with four mods added and four live folders moved.

## Method

- **Sweep stamp:** 2026-09-27 16:28–16:45 local, build `42.20.4` (jar `b0bbce05d5`). Tree stamp rule: the installed workshop tree is live and Steam rewrites the subtree inside an item rather than the item node, so every count here is quoted with the minute above and a recount is a new reading rather than a confirmation ([`platform/lessons.md#corpus-drift`](../../platform/lessons.md#corpus-drift)).
- **Corpus swept:** `D:\SteamLibrary\steamapps\workshop\content\108600`, read-only — **182 workshop items holding 234 mod folders**, against 179 / 230 in `data/mod-inventory.json` (2026-09-10 17:47). **2 404 live `.lua` files** and **2 445 live script `.txt` files** were opened.
- **Live-folder resolution:** re-resolved from disk today rather than taken from the dated inventory, by importing `tools/mod_lint.py`'s `version_dirs` / `info_chain` / `read_info` / `media_root` — the same resolver `tools/mod_inventory.py` delegates to, so identity is not re-decided here. For each mod the sweep reads **`<live>/media/lua` plus `common/media/lua`** (and the same two for `media/scripts`), because `common/` is a shipped layout the running build also loads. A mod with no resolvable version dir is read at its root `media/`. Non-live version dirs are excluded, except where a line below says "all folders" — surface 1's negative and the `setPanic`/`setBoredom`/`setUnhappyness` note were taken over every folder on purpose.
- **Drift against the 2026-09-10 inventory:** 4 mod folders **added** — `QualityCooking` (item `3624538051`, the resident Girth item, taking it from five mods to six), `NewMusic` (`3739256725`), `SDMusic` (`3793913223`), `SDMixtape` (`3801904948`); **0 removed**; **4 live folders moved** — `isoContainers` `42.13→42.20`, `SimpleStatus` `42.16→42.20`, `KI5campers` `42.13→42.20`, `70chevelle` `42.13→42.20`. The `SimpleStatus` move means every `42.16/…` line cite in [`facts/other-mods/simplestatus.md`](../../facts/other-mods/simplestatus.md) now names a shadowed folder and must be re-located by content.
- **Vanilla tree swept:** `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`, read-only — **1 395 `.lua` files**, same patterns.
- **Classification:** each hit is labelled *definition* (the match is the name being defined, `function X…` or an assignment left-hand side), *wrap* (a `local orig… = <target>` save immediately above a redefinition of the same name — reported as `wrap-save`, with the redefinition line beside it), *call*, *read* or *comment*. `comment` is a `--` earlier on the line outside a string, or a line inside an unclosed `--[[`. Classifications on the load-bearing hits were re-read by hand.
- **Grep patterns, verbatim** (Python `re`, per line, one hit per pattern per line):
  - **S1** `Hook\.CalculateStats` · `\bCalculateStats\b` · `LuaHookManager` · `TriggerHook`
  - **S2** `getStats\(\)\s*[:.]\s*(?:set|add|remove)\w*` · `\bsetHunger\b` · `\bsetThirst\b` · `\bsetEndurance\b` · `\bsetFatigue\b` · `\bsetStress\b` · `\bsetPanic\b` · `\bsetUnhappyness\b` · `\bsetBoredom\b` · `CharacterStat\.` · `getNutrition\(\)\s*[:.]\s*set\w*` · `\bsetWeight\b` · `applyTraitFromWeight`
  - **S3** `setPerkLevelDebug` · `\blevel0\b` · `setXPToLevel` · `LoseLevel` · `\bAddXP\b` · `\baddXp\b` · `Events\.LevelPerk` · `Events\.AddXP` · `OnWeaponHitXp` · `SyncXp` · `getPerkLevel\(\s*Perks\.Strength` · `Perks\.Fitness` · `canAddFitnessXp`
  - **S4** `setMaxWeightBase` · `setMaxWeightDelta` · `getCharacterTraits\(\)\s*[:.]\s*(?:add|remove|set)\w*` · `CharacterTrait\.(?:NIGHT_VISION|SHORT_SIGHTED|EAGLE_EYED|KEEN_HEARING)` · `CharacterTrait\.\w+` · `\b(?:Obese|Overweight|Underweight|Emaciated)\b` · `sendSyncPlayerFields` · `syncPlayerStats` · `syncBodyPart`
  - **S5** `ISEatFoodAction` · `ISDrinkFluidAction` · `\bDrinkFluid\b` · `\bOnEat\b` · `\bEatFood\b` · `multiplyFoodValues`
  - **S6** `ReduceGeneralHealth` · `AddGeneralHealth` · `setOverallBodyHealth` · `setHealthFromFoodTimer` · `setCatchACold` · `setWoundInfectionLevel` · `setInfectionGrowthRate` · `setBleedingTime` · `\bTEMPERATURE\b` · `Thermoregulator` · `setAimingDelay` · `setPainReduction`
  - **S7** `ISToolTipInv\s*[.:]\s*render` · `ISCharacterInfoWindow` · `ISHealthPanel` · `ISCollapsableWindow` · `ISLayoutManager\.RegisterWindow` · `PZAPI\.ModOptions` · `keyBinding` · `MF\s*[.:]\s*(?:createMoodle|getMoodle)` · `MoodlesUI`
  - **S8** `ModData\.getOrCreate` · `ModData\.transmit` · `sendClientCommand` · `sendServerCommand` · `SandboxVars\.\w+`; bus module strings from `(sendClientCommand|sendServerCommand|OnClientCommand|OnServerCommand)\s*\(([^)]*)` taking the **first** string literal in the argument list; sandbox prefixes from `^\s*option\s+([\w.]+)` in every live `media/sandbox-options.txt`
  - **S9** over comment-stripped script text (`tools/food_scan._strip_comments`, the engine's own comment rule): `^\s*module\s+(\S+)` for the enclosing module, `^[ \t]*item[ \t]+(\w[\w.-]*)[ \t]*\{?[ \t]*$` for item definitions, `^\s*fluid\s+(\w[\w.-]*)`, `^\s*evolvedrecipe\s+(\w[\w.-]*)`, `^\s*(OnCooked|OnEat|ReplaceOnCooked|EvolvedRecipe)\s*=`
  - **S10** `Events\.OnTick\.Add` · `Events\.OnPlayerUpdate\.Add` · `Events\.EveryOneMinute\.Add` · `Events\.EveryTenMinutes\.Add`
- **Name set for the S9 collision census:** the **1 005** item records of `data/food-items.json` (722 of them `kind: food`, the rest `drainable` and `fluid_container`) and its **61** fluid records — not all ~5 100 vanilla item definitions. So "no vanilla name collision" below means *no collision with a food, drainable or fluid-container record*, which is the question the item pass asks; `Horse`'s known `Base.Rope` redefinition is outside that set by construction.
- **Caveats on the S8 module list:** the first-literal rule misreads a call shaped `sendServerCommand(player, MODULE_VAR, "command", …)` as the command rather than the module, which is why several `QuestSystem` and `KnoxBuildworks` entries below are command names. The list is therefore a superset of the module namespace and a floor on it; what it is used for here — proving `NutritionRevamp` and `NR` absent — is unaffected.

## Matrix

One row per mod with at least one non-comment hit on any surface: **108 of 234**. Ordered by the sharpest hit (a wrap or write on a low-numbered surface first), then by breadth. The tail of the table is mods whose only hits are surface 8 (`SandboxVars.` reads or a command bus) or surface 10 (an `OnPlayerUpdate` registration) — both patterns are corpus-wide background rather than a collision, and the rows are kept so the count is a census.

| mod id | item | live folder | surfaces | sharpest hit |
|---|---|---|---|---|
| `QualityCooking` | `3624538051` | `42` | 2, 4, 5, 6, 7, 8, 10 | `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingRollHandler.lua:170` ISEatFoodAction |
| `SomewhatTraitsCore` | `3498347699` | `42.15` | 2, 4, 5, 8, 10 | `3498347699/mods/SomewhatTraitsCore/42.15/media/lua/shared/SWTraitsCoreOverrides_shared.lua:29` ISEatFoodAction |
| `EmergencyVomitB42` | `3731711925` | `42` | 2, 5, 6, 8, 10 | `3731711925/mods/EmergencyVomitB42/42/media/lua/client/EmergencyVomit_Dialogues.lua:241` ISEatFoodAction |
| `Horse` | `3661336777` | `42` | 2, 4, 5, 7, 8, 9, 10 | `3661336777/mods/HorseMod/42/media/lua/shared/HorseMod/patches/ActionBlocker.lua:27` ISEatFoodAction |
| `CleanUI` | `3437629766` | `42.19` | 2, 4, 5, 7, 8, 10 | `3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPane.lua:6` ISEatFoodAction |
| `Economy` | `3624538051` | `42` | 2, 5, 6, 8 | `3624538051/mods/Economy/42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:647` multiplyFoodValues |
| `SWMisc_Patches` | `3621968227` | `42` | 3, 4, 5, 8 | `3621968227/mods/SWMisc_Patches/42/media/lua/shared/SWMisc_Patches_Overrides_shared.lua:12` ISEatFoodAction |
| `ZVirusVaccine42BETA` | `3615135168` | `42.20` | 2, 3, 4, 6, 7, 8, 9, 10 | `3615135168/mods/ZVirusVaccine42BETA/42.20/media/lua/server/HealthSystem/LabAutopsyLogic_Server.lua:428` getStats():set/add/remove |
| `GirthsTweaks` | `3745960616` | `42` | 2, 3, 4, 7, 8, 10 | `3745960616/mods/GirthsTweaks/42/media/lua/client/GT_BoredomRelief.lua:10` getStats():set/add/remove |
| `BeyondTen` | `3765241705` | `42` | 2, 3, 8, 10 | `3765241705/mods/BeyondTen/42/media/lua/shared/BeyondTen/Bonuses.lua:709` CharacterStat. |
| `SWServerUtils` | `3744609615` | `42` | 2, 3, 8, 10 | `3744609615/mods/SWServerUtils/42/media/lua/server/SWServerUtils_Commands.lua:23` CharacterStat. |
| `storm-core-b42` | `3670772371` | `42` | 2, 4, 8, 10 | `3670772371/mods/storm/42/media/lua/client/StormTransferFix.lua:462` CharacterStat. |
| `ProjectArcade` | `3645980077` | `42.15` | 2, 8, 10 | `3645980077/mods/ProjectArcade/common/media/lua/client/TimedActions/ProjectArcade_PlayArcadeTimedAction.lua:348` setStress |
| `simpleStatus` | `2867431511` | `42.20` | 2, 6, 7 | `2867431511/mods/SimpleStatus/42.20/media/lua/client/SimpleStatus.lua:77` CharacterStat. |
| `FasterResting` | `3634568288` | `42` | 2, 10 | `3634568288/mods/FasterResting/42/media/lua/server/SWFasterResting.lua:28` CharacterStat. |
| `SKITTLE_LongTermPreservation4220` | `3774789651` | `42.20` | 2, 9 | `3774789651/mods/LongTermPreservation4220/42.20/media/lua/server/recipe_meats.lua:43` setWeight |
| `JadePackingSD` | `3779653231` | `42` | 2 | `3779653231/mods/JadePackingSD/42/media/lua/shared/JadePacking_State.lua:12` setWeight |
| `SWMisc_Resting` | `3621968227` | `42` | 2, 7, 10 | `3621968227/mods/SWMisc_Resting/42/media/lua/client/SWMisc_Resting_Main.lua:15` CharacterStat. |
| `SkillRecoveryJournal` | `2503622437` | `42.20.1` | 3, 4, 7, 8, 10 | `2503622437/mods/Skill Recovery Journal/42.20.1/media/lua/shared/Skill Recovery Journal XP.lua:5` Perks.Fitness |
| `KnoxBuildworks` | `3772269882` | `42` | 3, 7, 8, 10 | `3772269882/mods/KnoxBuildworks/42/media/lua/client/KnoxBuildworks/Debug/BuildTestRunner.lua:195` setPerkLevelDebug |
| `NewMusic` | `3739256725` | `42` | 3, 7, 8, 10 | `3739256725/mods/Talis New Music/42/media/lua/shared/slot/NMDeviceDisassembly.lua:78` AddXP |
| `QuestSystem` | `3624538051` | `42` | 3, 7, 8, 10 | `3624538051/mods/QuestSystem/42/media/lua/server/EventHandlers/DummiesBookHandler.lua:15` AddXP |
| `STA_PryOpen` | `3579640010` | `42.20` | 3, 4, 7, 8 | `3579640010/mods/STA_PryOpen/common/media/lua/shared/STA_PryOpen_Utils.lua:550` getPerkLevel(Perks.Strength |
| `CombatTraitsCore` | `3427091746` | `42.15` | 3, 8, 10 | `3427091746/mods/CombatTraitsCore/42.15/media/lua/client/SWCombatTraitsCore_client.lua:89` getPerkLevel(Perks.Strength |
| `ElyonLib` | `3384377738` | `42` | 3, 8, 10 | `3384377738/mods/ElyonLib/42/media/lua/shared/ElyonLib/Rewards/GrantUtils.lua:90` AddXP |
| `OZD-ZonesB42` | `3325808670` | `42` | 3, 8, 10 | `3325808670/mods/OZD-ZonesB42/common/media/lua/server/OnZombieDeadZones.lua:44` addXp |
| `WorkingKnowledge` | `3717099183` | `42` | 3, 4, 8 | `3717099183/mods/WorkingKnowledge/42/media/lua/server/WK_Server.lua:64` addXp |
| `dustinguished_bolt_cutters` | `3671176591` | `42.15` | 3, 8, 10 | `3671176591/mods/dustinguished_bolt_cutters/common/media/lua/client/dgmc_bolt_cutters_context.lua:42` getPerkLevel(Perks.Strength |
| `BookConsumerB42` | `3772533498` | `42` | 3, 8 | `3772533498/mods/BookConsumerB42/common/media/lua/shared/TimedActions/ISReadABook_BookConsumer.lua:102` setXPToLevel |
| `ExerciseWithCorpses` | `3404074048` | `42` | 3, 8 | `3404074048/mods/ExerciseWithCorpses/common/media/lua/server/getSwole.lua:34` addXp |
| `90pierceArrow` | `2942793445` | `42.13` | 3 | `2942793445/mods/90pierceArrow/42.13/media/lua/server/90pierceArrow_server.lua:111` AddXP |
| `BaseQuests` | `3624538051` | `42` | 3 | `3624538051/mods/BaseQuests/42/media/lua/shared/MarchRidge/Quests.lua:91` Perks.Fitness |
| `STA_EngineRebuild` | `3628452306` | `42` | 3 | `3628452306/mods/STA_EngineRebuild/common/media/lua/shared/TimedActions/STA_EngineRebuild_ISEngineRebuildAction.lua:68` addXp |
| `AutoCook` | `3388721641` | `42.13` | 4, 7 | `3388721641/mods/AutoCook/42.13/media/lua/client/AutoCook.lua:39` CharacterTrait.<other> |
| `CHGRedux` | `3625590608` | `42` | 4, 8 | `3625590608/mods/CHGRedux/42/media/lua/shared/Items/CHGRedux_SpawnItems.lua:95` CharacterTrait.<other> |
| `PainkillersRemoveMuscleStrain` | `3398090604` | `42` | 4, 8 | `3398090604/mods/PainkillersRemoveMuscleStrain/common/media/lua/shared/pillsArmMuscleStrain_removal.lua:53` syncBodyPart |
| `KeenPerception` | `3685392864` | `42` | 4 | `3685392864/mods/KeenPerception/42/media/lua/shared/SWKeenPerception.lua:11` CharacterTrait.<perception> |
| `ResearchLabInternProfession` | `3615135168` | `42.20` | 4 | `3615135168/mods/ResearchLabInternProfession/42.20/media/lua/shared/Definitions/RLPMainLoader.lua:43` CharacterTrait.<other> |
| `SomewhatTraits` | `3498347699` | `42.15` | 4 | `3498347699/mods/SomewhatTraits/42.15/media/lua/shared/SWTraits_MET.lua:34` CharacterTrait.<other> |
| `ItemQuality` | `3624538051` | `42` | 7, 8, 10 | `3624538051/mods/ItemQuality/42/media/lua/client/UI/QualityItemTooltip.lua:95` ISToolTipInv.render / :render |
| `KATTAJ1_ClothesCore` | `3470422050` | `42.15` | 7 | `3470422050/mods/KATTAJ1 Clothes Core/42.15/media/lua/client/KATTAJ1_TooltipFixer.lua:3` ISToolTipInv.render / :render |
| `sd-teleporter` | `3662913642` | `42` | 7, 8, 10 | `3662913642/mods/SD-teleporter/common/media/lua/client/sd-teleporter-tooltip.lua:77` ISToolTipInv.render / :render |
| `MoodleFramework` | `3396446795` | `42.20` | 7 | `3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:25` MF.createMoodle / MF.getMoodle |
| `SDQuests` | `3745960616` | `42` | 7, 8, 9, 10 | `3745960616/mods/SDQuests/42/media/lua/client/SDQColorChange.lua:2` ISCollapsableWindow |
| `DataLogger` | `3745960616` | `42` | 7, 8, 10 | `3745960616/mods/DataLogger/42/media/lua/client/KillCountAdmin.lua:1` ISCollapsableWindow |
| `FancyLanterns` | `3267733558` | `42.15` | 7, 8, 10 | `3267733558/mods/FancyLanterns/42.15/media/lua/client/SWFancyLanterns_ModOptions.lua:11` PZAPI.ModOptions |
| `KWRR_Security` | `3455571945` | `42.20` | 7, 8, 10 | `3455571945/mods/KWRR_Security/common/media/lua/client/KWRR_Security_Client.lua:124` ISHealthPanel |
| `MoreDifficultZonesB42` | `3325808670` | `42` | 7, 8, 10 | `3325808670/mods/MoreDifficultyB42/common/media/lua/client/MoodleTier.lua:10` MF.createMoodle / MF.getMoodle |
| `PlumbingFixed` | `3626008449` | `42` | 7, 8, 10 | `3626008449/mods/PlumbingFixed/42/media/lua/client/PFModOptions.lua:7` PZAPI.ModOptions |
| `SDHC` | `3789019583` | `42` | 7, 8, 10 | `3789019583/mods/SDHC/common/media/lua/client/UI/ISHorseManagementUI.lua:1` ISCollapsableWindow |
| `CustomGamepadUI` | `3001154607` | `42` | 7, 10 | `3001154607/mods/CustomGamepadUI/42/media/lua/client/SWModOptions.lua:56` PZAPI.ModOptions |
| `EssentialCarNotifications` | `3350173580` | `42.15` | 7, 10 | `3350173580/mods/EssentialCarNotifications/42.15/media/lua/client/SWEssentialCarNotifications.lua:11` PZAPI.ModOptions |
| `MorePlushies` | `2795036124` | `42` | 7, 8 | `2795036124/mods/MorePlushies/42/media/lua/client/ISUI/MorePlushies_Viewer.lua:17` ISCollapsableWindow |
| `Neat_Crafting` | `3502080466` | `42.13` | 7, 10 | `3502080466/mods/Neat_Crafting/common/media/lua/client/Neat_Crafting/NC_ModOptions.lua:27` PZAPI.ModOptions |
| `P4TidyUpMeister` | `2769706949` | `42.20` | 7, 10 | `2769706949/mods/P4TidyUpMeister/42.20/media/lua/client/P4TidyUpMeister.lua:38` PZAPI.ModOptions |
| `ProximityInventory` | `2847184718` | `42` | 7, 8 | `2847184718/mods/ProximityInventory/common/media/lua/client/ProximityInventory/ISInventoryPage.lua:34` PZAPI.ModOptions |
| `SomewhatCompanions` | `3582919946` | `42.13` | 7, 8 | `3582919946/mods/SomewhatCompanions/42.13/media/lua/client/SomewhatSlots_ModOptions.lua:12` PZAPI.ModOptions |
| `UndeadSurvivor42` | `3739427877` | `42` | 7, 8 | `3739427877/mods/Undead Survivor/42/media/lua/client/UndeadSurvivor_Hotbar.lua:15` keyBinding |
| `NSOENMIOEACTDD` | `3427114019` | `42` | 7 | `3427114019/mods/NSOENMIOEACTDD/42/media/lua/client/Vehicles/ISUI/SWNSOENMIOEACTDD_ISVehicleMenu.lua:12` PZAPI.ModOptions |
| `alicesWeaponSlingRadialMenu` | `3775549570` | `42` | 7 | `3775549570/mods/alicesWeaponSlingRadialMenu/42/media/lua/client/AliceWeaponSling_RadialMenu.lua:16` keyBinding |
| `errorMagnifier` | `2896041179` | `42.15` | 7 | `2896041179/mods/errorMagnifier/42.15/media/lua/client/errorMagnifier_Main.lua:352` ISCollapsableWindow |
| `biogas` | `2925657627` | `42` | 8, 9 | `2925657627/.../BioGasFluids.txt:3` fluid LiquidFertilizer |
| `1VCESTANDARD` | `3421271152` | `42.19` | 9 | `3421271152/.../VCEcontainers.txt:129` item Bag_HydrationBackpack in module Base |
| `SDUtils` | `3662913642` | `42` | 8, 10 | `3662913642/mods/SDUtils/common/media/lua/client/removevehicles.lua:255` SandboxVars.<name> |
| `KATTAJ1_Military` | `3470426196` | `42.15` | 8 | `3470426196/mods/KATTAJ1 Military Pack/42.15/media/lua/server/NPCs/KATTAJ1_MilitaryArmorDefinition.lua:24` SandboxVars.<name> |
| `SDDistro` | `3662913642` | `42` | 8 | `3662913642/mods/SD-distro/common/media/lua/server/SDDistro.lua:204` SandboxVars.<name> |
| `damnlib` | `3171167894` | `42.20` | 8, 10 | `3171167894/mods/damnlib/42.20/media/lua/client/DAMN_Client.lua:14` sendClientCommand |
| `ArcadiaAnimalFix_B42` | `3786854702` | `42` | 8, 10 | `3786854702/mods/ArcadiaAnimalFix_B42/42/media/lua/client/ArcadiaAnimalFix/ArcadiaAnimalFix_VehicleTransport.lua:21` sendClientCommand |
| `CleanHotBar` | `3461263912` | `42.15` | 8, 10 | `3461263912/mods/CleanHotBar/common/media/lua/client/hotbar/commonsense_patch.lua:3` SandboxVars.<name> |
| `MoreDifficultZombiesB42` | `3325808670` | `42` | 8, 10 | `3325808670/mods/MoreDifficultZombiesB42/common/media/lua/client/sdzombies_clientb42.lua:94` SandboxVars.<name> |
| `SDVC` | `3763759011` | `42` | 8, 10 | `3763759011/mods/SDVC/common/media/lua/client/UI/SDVCPermissionsPanel.lua:338` sendClientCommand |
| `YAPZLib` | `3624971238` | `42` | 8, 10 | `3624971238/mods/YetAnotherPZLib/42/media/lua/client/DebugUIs/YAPZLib/DebugContextMenu.lua:6` sendClientCommand |
| `86fordE150` | `2870394916` | `42.20` | 8 | `2870394916/mods/86fordE150/42.20/media/lua/client/86fordE150_theLegThing.lua:20` sendClientCommand |
| `MailboxStories` | `3728301676` | `42` | 8 | `3728301676/mods/Mailbox Stories/42/media/lua/shared/MailboxStories/MS_Core.lua:232` SandboxVars.<name> |
| `QualityEnhancements` | `3624538051` | `42` | 8 | `3624538051/mods/QualityEnhancements/42/media/lua/client/UI/QualityEnhancementsPanel.lua:328` sendClientCommand |
| `RemoveAllItems` | `3413255058` | `42.14` | 8 | `3413255058/mods/RemoveAllItems/42.14/media/lua/client/RemoveAllItems.lua:70` sendClientCommand |
| `VVR` | `3423424077` | `42` | 8 | `3423424077/mods/VanillaVehiclesReplacerKI5/42/media/lua/server/VVR/Replace.lua:123` SandboxVars.<name> |
| `SDBus` | `3662913642` | `42` | 8, 10 | `3662913642/mods/sd-bus/common/media/lua/client/SD-bus-client.lua:15` SandboxVars.<name> |
| `HayesCustoms` | `2884278892` | `42` | 8 | `2884278892/mods/HayesCustoms/42/media/lua/shared/hcustoms_SandboxUtils.lua:37` SandboxVars.<name> |
| `65banshee` | `3566868353` | `42.13` | 10 | `3566868353/mods/65banshee/42.13/media/lua/server/65banshee_server.lua:150` Events.OnPlayerUpdate.Add |
| `68firebird` | `3258343790` | `42.13` | 10 | `3258343790/mods/68firebird/42.13/media/lua/client/68firebird_client.lua:69` Events.OnPlayerUpdate.Add |
| `69camaro` | `2991201484` | `42.13` | 10 | `2991201484/mods/69camaro/42.13/media/lua/client/69camaro_client.lua:48` Events.OnPlayerUpdate.Add |
| `69charger` | `3631989559` | `42.20` | 10 | `3631989559/mods/69charger/42.20/media/lua/client/69charger_client.lua:51` Events.OnPlayerUpdate.Add |
| `69fordMustang` | `3756938756` | `42.13` | 10 | `3756938756/mods/69fordMustang/42.13/media/lua/client/69fordMustang_client.lua:52` Events.OnPlayerUpdate.Add |
| `70barracuda` | `2913633066` | `42.13` | 10 | `2913633066/mods/70barracuda/42.13/media/lua/client/70barracuda_client.lua:51` Events.OnPlayerUpdate.Add |
| `70chevelle` | `3766571591` | `42.20` | 10 | `3766571591/mods/70chevelle/42.20/media/lua/client/70chevelle_client.lua:57` Events.OnPlayerUpdate.Add |
| `70dodge` | `2873290424` | `42.13` | 10 | `2873290424/mods/70dodge/42.13/media/lua/client/70dodge_client.lua:51` Events.OnPlayerUpdate.Add |
| `70roadRunner` | `3642935062` | `42.13` | 10 | `3642935062/mods/70roadRunner/42.13/media/lua/client/70roadRunner_client.lua:47` Events.OnPlayerUpdate.Add |
| `73fordFalcon` | `3490370700` | `42.20` | 10 | `3490370700/mods/73fordFalcon/42.20/media/lua/client/73fordFalcon_client.lua:89` Events.OnPlayerUpdate.Add |
| `73nissanGTR` | `3743371090` | `42.13` | 10 | `3743371090/mods/73nissanGTR/42.13/media/lua/client/73nissanGTR_client.lua:48` Events.OnPlayerUpdate.Add |
| `76chryslerNewYorker` | `3730833846` | `42.13` | 10 | `3730833846/mods/76chryslerNewYorker/42.13/media/lua/server/76chryslerNewYorker_server.lua:156` Events.OnPlayerUpdate.Add |
| `78lamboCountach` | `3726526329` | `42.13` | 10 | `3726526329/mods/78lamboCountach/42.13/media/lua/server/78lamboCountach_server.lua:225` Events.OnPlayerUpdate.Add |
| `82firebird` | `3320947974` | `42.13` | 10 | `3320947974/mods/82firebird/42.13/media/lua/server/82firebird_server.lua:169` Events.OnPlayerUpdate.Add |
| `82jeepJ10` | `2886832257` | `42.13` | 10 | `2886832257/mods/82jeepJ10/42.13/media/lua/client/82jeepJ10_client.lua:35` Events.OnPlayerUpdate.Add |
| `84buickElectra` | `3596903773` | `42.13` | 10 | `3596903773/mods/84buickElectra/42.13/media/lua/client/84buickElectra_client.lua:76` Events.OnPlayerUpdate.Add |
| `84cadillacDeVille` | `3592777775` | `42.13` | 10 | `3592777775/mods/84cadillacDeVille/42.13/media/lua/client/84cadillacDeVille_client.lua:76` Events.OnPlayerUpdate.Add |
| `84corvette` | `3684254299` | `42.13` | 10 | `3684254299/mods/84corvette/42.13/media/lua/server/84corvette_server.lua:184` Events.OnPlayerUpdate.Add |
| `85chevyStepVan` | `3614034284` | `42.13` | 10 | `3614034284/mods/85chevyStepVan/42.13/media/lua/server/85chevyStepVan_server.lua:124` Events.OnPlayerUpdate.Add |
| `87fordB700` | `3110911330` | `42.20` | 10 | `3110911330/mods/87fordB700/42.20/media/lua/client/87fordBF700_client.lua:17` Events.OnPlayerUpdate.Add |
| `87toyotaMR2` | `3052360250` | `42.13` | 10 | `3052360250/mods/87toyotaMR2/42.13/media/lua/server/87toyotaMR2_server.lua:201` Events.OnPlayerUpdate.Add |
| `89defender` | `3570973322` | `42.13` | 10 | `3570973322/mods/89defender/42.13/media/lua/server/89defender_server.lua:304` Events.OnPlayerUpdate.Add |
| `91nissan240sx` | `3504401781` | `42.13` | 10 | `3504401781/mods/91nissan240sx/42.13/media/lua/server/91nissan240sx_server.lua:192` Events.OnPlayerUpdate.Add |
| `91range` | `2409333430` | `42.13` | 10 | `2409333430/mods/91range/42.13/media/lua/client/91range_client.lua:74` Events.OnPlayerUpdate.Add |
| `92nissanGTR` | `2846036306` | `42.13` | 10 | `2846036306/mods/92nissanGTR/42.13/media/lua/client/92nissanGTR_client.lua:29` Events.OnPlayerUpdate.Add |
| `95impreza` | `3647735736` | `42.13` | 10 | `3647735736/mods/95impreza/42.13/media/lua/server/95impreza_server.lua:151` Events.OnPlayerUpdate.Add |
| `HereGoesTheSun` | `3618557184` | `42.15` | 10 | `3618557184/mods/HereGoesTheSun/42.15/media/lua/client/HGTS_StormMood_Client.lua:64` Events.OnTick.Add |
| `RikuMeleeB42` | `3623584152` | `42` | 10 | `3623584152/mods/RikuMelee/42/media/lua/client/RMW_BrokenWeapons.lua:22` Events.OnPlayerUpdate.Add |
| `alicesWeaponSling` | `3775549570` | `42` | 10 | `3775549570/mods/alicesWeaponSling/42/media/lua/client/AliceWeaponSling_ISHotbar.lua:423` Events.OnTick.Add |

## 1. The stat hook

**Zero hits in the corpus, over every folder of every mod rather than only the live ones.** `CalculateStats`, `Hook.CalculateStats`, `LuaHookManager` and `TriggerHook` appear in no `.lua` file under `D:\SteamLibrary\steamapps\workshop\content\108600`.

The only `Hook.<name>` uses in the whole corpus are one mod's, and they are copied vanilla:

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `CleanUI` | `3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:4577` | `Hook.AutoDrink.Remove(hookAutoDrink)` | call | removes vanilla's auto-drink hook inside CleanUI's whole-file fork of vanilla's context menu; the same pair also sits in its shadowed `42.15/` and `42.16/` copies |
| `CleanUI` | `3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:4581` | `Hook.AutoDrink.Add(hookAutoDrink)` | call | re-adds it; verbatim from vanilla `client/ISUI/ISInventoryPaneContextMenu.lua:4060` |

Reading: the `Hook` global is in use on this server, so the table exists and is reachable from mod Lua, but no mod registers on the stat hook. Takeover mode (§ 4.1) claims a hook nobody else wants **on the installed corpus at this stamp**; the wall the spec states against another mod registering it stands as a release note for servers this sweep cannot see, not as a live conflict.

## 2. Writes to player stats and nutrition

187 live hits over 17 mods. Sorted by what the write owns.

**The stats the fast clock owns — endurance, fatigue, hunger, thirst.** Every one of these is a second writer of a value § 4.1 makes the mod authoritative for.

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SomewhatTraitsCore` | `3498347699/mods/SomewhatTraitsCore/42.15/media/lua/server/SWTraitsCore_server.lua:103` | `stats:add(CharacterStat.ENDURANCE, extraEndurance)` | call | one of five endurance credits, all server-side, all from `OnTick` handlers gated on a trait |
| `SomewhatTraitsCore` | `…/SWTraitsCore_server.lua:163` | `stats:remove(CharacterStat.FATIGUE, extraFatigue)` | call | one of five fatigue credits on the same clock |
| `SomewhatTraitsCore` | `…/SWTraitsCore_server.lua:84,86` | `nutrition:setCalories(calories + extraCalories)` / `(calories - extraCalories)` | call | the corpus's only **player macro** write; `dayLengthMultiplier × 0.5` calories to hold body weight in 77–83 kg |
| `SomewhatTraitsCore` | `…/SWTraitsCore_server.lua:118,119,143,144,179,194,195,238,239,255,288,302,316,353,394,423,424,443,444,460,475,476` | `stats:add`/`:remove` on `BOREDOM`, `UNHAPPINESS`, `STRESS`, `INTOXICATION`, `FATIGUE`, `ENDURANCE` | call | 28 writes in one server file, the mod's whole effect surface |
| `GirthsTweaks` | `3745960616/mods/GirthsTweaks/42/media/lua/server/ST_MPSleep.lua:51` | `stats:set(CharacterStat.FATIGUE, 0)` | call | zeroes fatigue on its multiplayer sleep path, server-side — an absolute write, not a delta |
| `GirthsTweaks` | `…/ST_MPSleep.lua:70` | `stats:set(CharacterStat.FATIGUE, math.max(0, modData.sdFatigue))` | call | restores a fatigue value it stashed in modData |
| `GirthsTweaks` | `…/ST_MPSleep.lua:71` | `stats:set(CharacterStat.ENDURANCE, math.min(1, modData.sdEndurance))` | call | restores endurance the same way |
| `GirthsTweaks` | `…/client/GT_BoredomRelief.lua:10` | `player:getStats():remove(CharacterStat.BOREDOM, sv.BoredomReliefAmount)` | call | client-side boredom credit off a sandbox amount |
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingBuffTicker.lua:25` | `stats:add(CharacterStat.ENDURANCE, ZomboidGlobals.ImobileEnduranceIncrease * … * player:getRecoveryMod() * ctx.multiplier * fraction)` | call | endurance-regen buff, server-side, on `EveryOneMinute`, reproducing vanilla's own constant |
| `QualityCooking` | `…/CookingBuffTicker.lua:33` | `stats:add(CharacterStat.FATIGUE, -ZomboidGlobals.FatigueIncrease * Config.StatsDecreaseMultiplier() * enduranceMod * …)` | call | fatigue-rate buff on the same clock, reading endurance to scale itself |
| `QualityCooking` | `…/CookingBuffTicker.lua:39` | `stats:add(CharacterStat.HUNGER, -ZomboidGlobals.HungerIncrease * Config.StatsDecreaseMultiplier() * …)` | call | hunger-rate buff, gated on the `FOOD_EATEN` moodle being at level 0 |
| `QualityCooking` | `…/shared/Utilities/CookingDebugCommands.lua:10` | `player:getStats():set(CharacterStat.HUNGER, value)` | call | a debug command that sets hunger absolutely, in `shared/`, behind an `isClient()` branch at `:18` |
| `FasterResting` | `3634568288/mods/FasterResting/42/media/lua/server/SWFasterResting.lua:32` | `stats:add(CharacterStat.ENDURANCE, extraEndurance)` | call | server-side endurance credit while resting, on `OnTick` |
| `FasterResting` | `…/SWFasterResting.lua:34` | `stats:add(CharacterStat.ENDURANCE, extraEndurance * 2)` | call | the doubled branch of the same |
| `SWServerUtils` | `3744609615/mods/SWServerUtils/42/media/lua/server/SWServerUtils_Commands.lua:23` | `stats:remove(CharacterStat.ENDURANCE, extraEndurance)` | call | an admin command that drains endurance, server-side |
| `BeyondTen` | `3765241705/mods/BeyondTen/42/media/lua/shared/BeyondTen/Bonuses.lua:710` | `stats:set(CharacterStat.ENDURANCE, current)` | call | absolute endurance write in `shared/`, so it executes in both states |
| `EmergencyVomitB42` | `3731711925/mods/EmergencyVomitB42/42/media/lua/server/EmergencyVomit_Main.lua:72` | `setStat(playerObj, CharacterStat.THIRST, math.max(0.80, getStat(playerObj, CharacterStat.THIRST, 0)))` | call | floors thirst at 0.80 after a vomit, server-side |
| `EmergencyVomitB42` | `…/EmergencyVomit_Main.lua:73` | `setStat(playerObj, CharacterStat.HUNGER, math.max(0.75, …))` | call | floors hunger at 0.75 — a direct override of whatever the model wrote |
| `EmergencyVomitB42` | `…/EmergencyVomit_Main.lua:82` | `setStat(playerObj, CharacterStat.ENDURANCE, math.max(0.0, … - 0.80))` | call | drains 0.80 endurance |
| `EmergencyVomitB42` | `…/EmergencyVomit_Main.lua:136,139,140,183,186` | `setStat(…, CharacterStat.SICKNESS / FOOD_SICKNESS / POISON, …)` | call | caps the sickness family after a rescue vomit |
| `EmergencyVomitB42` | `3731711925/…/42/media/lua/client/EmergencyVomit_Action.lua:29,30,39,73,76,77,95,98` | the same eight writes via `EmergencyVomit.setStat` | call | the client mirror of the server file — the same stats written on both sides |

**The mood stats § 4.5 writes through the coefficient set.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `ProjectArcade` | `3645980077/mods/ProjectArcade/common/media/lua/server/ProjectArcade_MoodServer.lua:14,17,20` | `stats:set(CharacterStat.BOREDOM / UNHAPPINESS / STRESS, math.max(0, …))` | call | absolute mood writes, server-side, after an arcade session |
| `ProjectArcade` | `…/ProjectArcade_MoodServer.lua:52,55,58` | `stats:set(CharacterStat.BOREDOM / UNHAPPINESS / STRESS, math.min(…, math.max(0, … + delta)))` | call | the clamped delta form of the same three |
| `ProjectArcade` | `…/common/media/lua/client/TimedActions/ProjectArcade_PlayArcadeTimedAction.lua:333,334,335,960,961,962,970` | the same three stats, client-side | call | the client half; `:348-349` reach `stats:setStress` by name after a `stats.setStress` nil-check |
| `ProjectArcade` | `…/ProjectArcade_MoodServer.lua:27-28`, `…PlayArcadeTimedAction.lua:341-342` | `bd:setBoredomLevel(math.max(0, bd:getBoredomLevel() - boredomDecrease))` | call | also writes the **BodyDamage** boredom level, both sides, behind a member nil-check |
| `storm-core-b42` | `3670772371/mods/storm/42/media/lua/client/StormTransferFix.lua:462` | `stats:add(CharacterStat.UNHAPPINESS, rate / 100)` | call | client-side unhappiness charge during a transfer |
| `storm-core-b42` | `…/StormTransferFix.lua:474` | `stats:add(CharacterStat.STRESS, rate / 10000)` | call | client-side stress charge |
| `ZVirusVaccine42BETA` | `3615135168/…/42.20/media/lua/server/HealthSystem/LabAutopsyLogic_Server.lua:428` | `player:getStats():add(CharacterStat.PANIC, 25)` | call | panic charge on an autopsy, server-side, followed by `syncPlayerStats(player, 0x00000100)` at `:429` |
| `ZVirusVaccine42BETA` | `…/LabMorgueLogic_Server.lua:489` | `player:getStats():add(CharacterStat.PANIC, 25)` | call | the same in the morgue path |
| `ZVirusVaccine42BETA` | `…/LabCollectBloodLogic_Server.lua:76` | `player:getStats():add(CharacterStat.PAIN, 5)` | call | pain charge on a blood draw |
| `ZVirusVaccine42BETA` | `…/VaccineLogic_Server.lua:97` | `player:getStats():set(CharacterStat.ZOMBIE_INFECTION, 0)` | call | clears infection — not a mod surface, listed for completeness |
| `Horse` | `3661336777/mods/HorseMod/42/media/lua/client/HorseMod/player/PlayerDamage.lua:152` | `stats:add(CharacterStat.PAIN, pain)` | call | client-side pain on a fall, paired with `syncBodyPart` calls at `:106,177,206,246` |

**Nutrition-object and weight writes.**

- **`getNutrition():set*` — zero hits across all folders.** No mod in the corpus writes a macro or the body weight through the nutrition object at all. The catalog's "only two mods write a nutrition macro" reading holds, and both of them do it through `setCalories`-family names rather than a `getNutrition():set` call shape.
- **`applyTraitFromWeight` — zero hits**, in the corpus and in vanilla's `media/lua` both. The band-trait refresh § 4.3 wants has no Lua-side competitor and no Lua-side precedent.
- `setWeight` hits are all **item** weight, not body weight:

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SKITTLE_LongTermPreservation4220` | `3774789651/mods/LongTermPreservation4220/42.20/media/lua/server/recipe_meats.lua:43` | `meatToChange:setWeight(meatToChange:getActualWeight());` | call | normalises the crafted instance's weight beside the ×0.70 macro scaling |
| `Economy` | `3624538051/mods/Economy/42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:454` | `if spec.weight then pcall(data.setWeight, data, spec.weight) end` | call | restores a serialised shop item's weight, inside a protected call |
| `JadePackingSD` | `3779653231/mods/JadePackingSD/42/media/lua/shared/JadePacking_State.lua:12` | `item:setWeight(weight)` | call | packing state writes an item's weight in `shared/` |

**`CharacterStat.` read-only consumers** that a re-based scale reaches unannounced: `simpleStatus` 26 hits (all client, one file), `CleanUI` 7, `SWMisc_Resting` 1, `BeyondTen` 3 reads beside its one write, `FasterResting` 4, `SWServerUtils` 2, `Horse` 3.

**A shadowed-folder note.** `SomewhatTraitsCore` ships a much larger client implementation in its **dead** `42.12/` folder and its B41 root `media/` — `setUnhappynessLevel`, `setBoredomLevel`, `setPanic` and `bodyDamage:setPanicReductionValue(0.0)` with the comment *"dividing vannila code by zero and reimplementing it from scratch"*. None of it is live on `42.20.4` (live is `42.15`), so it is unexecuted code today and a hazard only if the author bumps that folder — the shadowed-copy rule ([`platform/lessons.md`](../../platform/lessons.md#anti-patterns)) applied to a version dir rather than to `common/`.

## 3. Perks and XP

94 live hits over 13 mods. The surfaces § 4.3's Strength clamp touches.

**`setPerkLevelDebug` — one hit in the whole corpus, and it is a dev path.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `KnoxBuildworks` | `3772269882/mods/KnoxBuildworks/42/media/lua/client/KnoxBuildworks/Debug/BuildTestRunner.lua:195` | `player:setPerkLevelDebug(perk, level)` | call | sets a perk level inside a client-side build-test harness |

**`setXPToLevel` and the `Events.AddXP` listeners — `BeyondTen` is the collision.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `BeyondTen` | `3765241705/mods/BeyondTen/42/media/lua/client/BeyondTen/Client.lua:48` | `player:getXp():setXPToLevel(perk, level)` | call | writes a perk's XP to a level target, client-side |
| `BeyondTen` | `…/client/BeyondTen/Client.lua:180` | `player:getXp():setXPToLevel(active.perk, BT.NATIVE_MAX_LEVEL)` | call | pins a perk at vanilla's max so its own levels 11–15 can ride above it |
| `BeyondTen` | `3765241705/…/42/media/lua/server/BeyondTen/Server.lua:226` | `if player and perk then player:getXp():setXPToLevel(perk, level) end` | call | the server half of the same write |
| `BeyondTen` | `…/client/BeyondTen/Client.lua:315` | `Events.AddXP.Add(Client.OnAddXP)` | call | intercepts every XP grant on the client |
| `BeyondTen` | `…/server/BeyondTen/Server.lua:487` | `Events.AddXP.Add(Server.OnAddXP)` | call | and on the server |
| `BeyondTen` | `…/server/BeyondTen/Server.lua:285` | `player:getXp():AddXP(perk, amount, false, false, false, false)` | call | its own grant path, with the four vanilla flags off |
| `BeyondTen` | `…/shared/BeyondTen/Bonuses.lua:788` | `Events.OnWeaponHitXp.Add(onServerWeaponMaintenanceEvent)` | call | the corpus's only `OnWeaponHitXp` listener, in `shared/` |
| `BeyondTen` | `…/shared/BeyondTen/Bonuses.lua:691,704` | `BT.GetMasteryRanks(player, Perks.Fitness) * 0.02` | read | Fitness-derived endurance protection and recovery multipliers |
| `BeyondTen` | `…/client/Client.lua:277`, `…/server/Server.lua:447` | `local passive = perk == Perks.Strength or perk == Perks.Fitness` | read | treats Strength and Fitness as the passive pair, which is the pair § 4.3 clamps |
| `SkillRecoveryJournal` | `2503622437/mods/Skill Recovery Journal/42.20.1/media/lua/shared/Skill Recovery Journal Shared Events.lua:62` | `Events.AddXP.Add(SRJmodHandler.checkIfDeductedXP)` | call | a second `Events.AddXP` listener, in `shared/`, so it runs on both sides |
| `BookConsumerB42` | `3772533498/mods/BookConsumerB42/common/media/lua/shared/TimedActions/ISReadABook_BookConsumer.lua:102` | `self.character:getXp():setXPToLevel(trainedStuff.perk, self.character:getPerkLevel(trainedStuff.perk));` | call | re-pins XP to the current level after a book read |
| `BookConsumerB42` | `…/ISReadABook_BookConsumer.lua:121,123` | `if SyncXp and (…)` / `SyncXp(self.character);` | call | the corpus's only `SyncXp` calls, guarded by a side test |

**The nutrition-gated Fitness XP path — the one consumer of a number the model re-bases.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SkillRecoveryJournal` | `2503622437/…/42.20.1/media/lua/shared/Skill Recovery Journal Main.lua:23` | `if player:getNutrition():canAddFitnessXp() then return end` | call | gates its own fitness handling on vanilla's calorie predicate, in `shared/` |
| `SkillRecoveryJournal` | `…/Main.lua:25` | `local fitness = player:getPerkLevel(Perks.Fitness)` | read | reads the Fitness level the mod's model does not clamp |
| `SkillRecoveryJournal` | `…/Skill Recovery Journal XP.lua:134` | `--if perk == Perks.Fitness and (not player:getNutrition():canAddFitnessXp()) then exerciseMultiplier 0 end` | comment | the author's own note that the protein multiplier below is not yet wired |
| `SkillRecoveryJournal` | `…/Skill Recovery Journal XP.lua:5,7` | `function SRJ_XPHandler.isSkillExcludedFrom.SpeedReduction(perk) return (perk == Perks.Sprinting or perk == Perks.Fitness or perk == Perks.Strength) or` | definition | excludes Strength and Fitness from its speed scaling — the same two perks § 4.3 owns |

**The band traits' XP boosts — mutated at load, in `shared/`.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SWMisc_Patches` | `3621968227/mods/SWMisc_Patches/42/media/lua/shared/SWMisc_Patches_Traits.lua:8` | `underweight:getXpBoosts():remove(Perks.Fitness)` | call | strips the Fitness XP boost from the **Underweight** trait definition on both sides |
| `SWMisc_Patches` | `…/SWMisc_Patches_Traits.lua:11` | `overweight:getXpBoosts():remove(Perks.Fitness)` | call | and from **Overweight** |

**`addXp` / `AddXP` grant sites**, all read as callers rather than owners of the surface: `ZVirusVaccine42BETA` 6 (server, Doctor and Butchering), `SWServerUtils` 4 (server, including `addXp(player, Perks.Strength, 2)` and `Perks.Fitness, 1`), `ExerciseWithCorpses` 2 live in `common/server/getSwole.lua:34-35` (`Perks.Fitness` and `Perks.Strength` from corpse exercise; four more in `common/shared/getSwole.lua:42-45` are commented out), `OZD-ZonesB42` 2 (server, Strength and Fitness per zone tier), `STA_PryOpen` 5 (`shared/`, one of them `Perks.Strength, 2`), `dustinguished_bolt_cutters` 2 (`shared/`, Strength), `GirthsTweaks` 3, `QuestSystem` 2, `KnoxBuildworks` 1, `WorkingKnowledge` 1, `ElyonLib` 1, `NewMusic` 2, `STA_EngineRebuild` 1, `90pierceArrow` 1. `getPerkLevel(Perks.Strength` readers: `CombatTraitsCore` 2 (client and server), `STA_PryOpen` 4, `dustinguished_bolt_cutters` 2, `ExerciseWithCorpses` 1 — every one of these reads a level the clamp can lower.

**Zero hits:** `level0`, `LoseLevel`, `Events.LevelPerk` — no mod listens to the level-change event vanilla uses to swap the Strength and Fitness traits, and no mod calls `LoseLevel`.

## 4. Carry capacity and traits

150 live hits over 17 mods.

**Carry capacity.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingBuffTicker.lua:56` | `player:setMaxWeightBase(record.weightBase + carryWeightBonus(record.points))` | call | applies a cooking carry-weight buff by writing **base**, server-side, reconciled once per minute against a cached `record.appliedAt` |
| `QualityCooking` | `…/CookingBuffTicker.lua:61` | `player:setMaxWeightBase(record.weightBase)` | call | on expiry, restores the **cached** pre-buff base — so any other writer of base between apply and expiry is silently reverted |

**`setMaxWeightDelta` — zero hits across all folders.** § 4.3's channel for the acute carry-capacity factor is uncontested, and it is the only one of the two setters that is.

**Runtime trait add/remove on a player.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `GirthsTweaks` | `3745960616/mods/GirthsTweaks/42/media/lua/server/GT_NoRestlessSleeperServer.lua:5` | `player:getCharacterTraits():remove(CharacterTrait.INSOMNIAC)` | call | removes a trait on the server with no ownership flag — the shape § 4.5's trait channel must not copy |
| `GirthsTweaks` | `…/client/GT_NoRestlessSleeper.lua:29` | `player:getCharacterTraits():remove(CharacterTrait.INSOMNIAC)` | call | the client mirror of the same removal |

That is the whole of it: **no mod in the corpus adds or removes `NIGHT_VISION`, `SHORT_SIGHTED`, `EAGLE_EYED`, `KEEN_HEARING` or any band trait on a player at runtime.** § 4.5's trait-toggle channel is otherwise uncontested.

**Trait *definition* mutation at load — the quiet hazard.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SWMisc_Patches` | `3621968227/mods/SWMisc_Patches/42/media/lua/shared/SWMisc_Patches_Traits.lua:5` | `local underweight = CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait.UNDERWEIGHT)` | read | opens the Underweight **definition** to edit it, in `shared/` — 10 `CharacterTraitDefinition` calls in this one file |
| `SWMisc_Patches` | `…/SWMisc_Patches_Traits.lua:14` | `local keenHearing = CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait.KEEN_HEARING)` | read | and the Keen Hearing definition |
| `SWMisc_Patches` | `…/SWMisc_Patches_Traits.lua:20` | `hardOfHearing:getMutuallyExclusiveTraits():remove(CharacterTrait.KEEN_HEARING)` | call | makes Hard of Hearing and Keen Hearing co-holdable |
| `SWMisc_Patches` | `…/SWMisc_Patches_Traits.lua:24` | `deaf:getMutuallyExclusiveTraits():remove(CharacterTrait.KEEN_HEARING)` | call | and Deaf with Keen Hearing |
| `KeenPerception` | `3685392864/mods/KeenPerception/42/media/lua/shared/SWKeenPerception.lua:5,10,11,15` | `keenHearing:getMutuallyExclusiveTraits():remove(CharacterTrait.HARD_OF_HEARING)` | call | the same edit from the other side, 6 definition reads and 4 exclusivity removals |
| `SomewhatTraits` | `3498347699/mods/SomewhatTraits/42.15/media/lua/shared/SWTraits_MET.lua:18,20` | `SWCTrait:getMutuallyExclusiveTraits():add(SWT.traits.SWOneTrickPony)` | call | 56 definition reads and 36 exclusivity edits for its own trait set |
| `CombatTraits` | `3427091746/mods/CombatTraits/42.15/media/lua/shared/SWCombatTraits_MET.lua:24,26` | `local met = SWCTrait:getMutuallyExclusiveTraits()` | read | 4 definition reads, 3 exclusivity edits |
| `SkillRecoveryJournal` | `2503622437/…/42.20.1/media/lua/shared/Skill Recovery Journal Calc.lua:98,101` | `local playerTraits = player:getCharacterTraits()` / `CharacterTraitDefinition.getCharacterTraitDefinition(traitTrait)` | read | reads a player's traits and their definitions to score a recovery multiplier |

`CharacterTrait.<perception>` readers besides those: `Horse` at `…/shared/HorseMod/riding/RidingMovement.lua:355` maps `[CharacterTrait.EAGLE_EYED] = 0.5` into a fall-chance table, so granting or removing a perception trait changes horse riding.

**Sync calls.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SkillRecoveryJournal` | `2503622437/…/42.20.1/media/lua/shared/Skill Recovery Journal Action Util.lua:133-134` | `if isServer() and sendSyncPlayerFields then` / `sendSyncPlayerFields(player, 0x00000001)` | call | the corpus's only `sendSyncPlayerFields`, bit `0x1`, behind a side test and a member nil-check — the guarded shape the rules ask for. § 4.5 plans bit `2`, a different field |
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingDebugHandler.lua:10` | `syncPlayerStats(player, SyncPlayerStatsPacket.getBitMaskForStat(CharacterStat.HUNGER))` | call | pushes hunger by name rather than by a magic constant — the readable idiom |
| `ZVirusVaccine42BETA` | `…/LabAutopsyLogic_Server.lua:429`, `…/LabMorgueLogic_Server.lua:490` | `syncPlayerStats(player, 0x00000100)` | call | pushes the stat it just charged |
| `Horse` | `3661336777/mods/HorseMod/42/media/lua/client/HorseMod/player/PlayerDamage.lua:106` | `syncBodyPart(part, BodyPartSyncPacket.BD_additionalPain)` | call | **client-side** `syncBodyPart` after a client-side pain write — four more at `:177,206,246` |
| `PainkillersRemoveMuscleStrain` | `3398090604/…/common/media/lua/shared/pillsArmMuscleStrain_removal.lua:53` | `syncBodyPart(bodyPart, 0xFFFFFFFFFFF)` | call | pushes **every** body-part bit in `shared/`, the widest mask in the corpus |

**Band-trait name literals:** two, both comments — `AutoCook`'s `ISCharacterCook.lua:98` (live copy and `common/` copy) carries `--35- => dies. 50- emaciated. 65- VUnderweight. 75- Underweight. 85+ Overweight. 100+ Obese`, a hard-coded reading of the vanilla weight bands the item pass and the body model move.

## 5. Eat and drink

33 live hits over 6 mods. **The eat action is wrapped by three mods and the seats divide cleanly.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingRollHandler.lua:170` | `local originalEatComplete = ISEatFoodAction.complete` | wrap-save | **the same seat § 4.2 claims**, in a `server/` file, with no sentinel and no idempotency test |
| `QualityCooking` | `…/CookingRollHandler.lua:172` | `function ISEatFoodAction:complete()` | definition | the replacement: `return eatWithBuff(self, self.percentage, function() return originalEatComplete(self) end)` |
| `QualityCooking` | `…/CookingRollHandler.lua:176` | `local originalEat = ISEatFoodAction.eat` | wrap-save | also wraps the per-bite `eat`, which § 4.2 does not |
| `QualityCooking` | `…/CookingRollHandler.lua:178` | `function ISEatFoodAction:eat(food, percentage)` | definition | rounds progress above 0.95 to 1 and scales `self.percentage` by it before calling the original |
| `QualityCooking` | `…/CookingRollHandler.lua:156` | `local eaten = BuffMath.Macros(food, fraction)` | call | reads the eaten food's four macros to allocate buff points — **a consumer of every number the item pass re-bases**, inside the eat |
| `QualityCooking` | `…/CookingRollHandler.lua:100` | `if isServer() then syncItemModData(self.character, item) end` | call | the only side test in that file; the two wraps themselves are installed unconditionally |
| `EmergencyVomitB42` | `3731711925/…/42/media/lua/client/EmergencyVomit_Dialogues.lua:232-234` | `ISEatFoodAction.emergencyVomitOriginalStart = ISEatFoodAction.emergencyVomitOriginalStart or EmergencyVomit.EatFoodOriginalStart or ISEatFoodAction.start` | definition-lhs | the **idempotent** save: stores the original on the class itself under a mod-unique key, falling back three deep |
| `EmergencyVomitB42` | `…/EmergencyVomit_Dialogues.lua:240` | `if not ISEatFoodAction.emergencyVomitPatched then` | call | the sentinel test — the shape the rules endorse and the only one in the corpus |
| `EmergencyVomitB42` | `…/EmergencyVomit_Dialogues.lua:241,250,257` | `function ISEatFoodAction:start()` / `:complete()` / `:eat(food, percentage)` | definition | three client-side wraps, each calling its saved original at `:247,252,259` |
| `EmergencyVomitB42` | `…/EmergencyVomit_Dialogues.lua:262` | `ISEatFoodAction.emergencyVomitPatched = true` | definition-lhs | closes the sentinel |
| `SomewhatTraitsCore` | `3498347699/mods/SomewhatTraitsCore/42.15/media/lua/shared/SWTraitsCoreOverrides_shared.lua:29` | `local original_ISEatFoodActiongetDuration = ISEatFoodAction.getDuration` | wrap-save | wraps the **duration**, in `shared/`, so on both sides |
| `SomewhatTraitsCore` | `…/SWTraitsCoreOverrides_shared.lua:30-31` | `function ISEatFoodAction:getDuration()` / `local o = original_ISEatFoodActiongetDuration(self)` | definition, call | scales eating time off a trait |
| `SomewhatTraitsCore` | `…/SWTraitsCoreOverrides_shared.lua:9-11` | `local original_ISDrinkFluidActiongetDuration = ISDrinkFluidAction.getDuration` / `function ISDrinkFluidAction:getDuration()` | wrap-save, definition | the same for drinking duration |
| `CleanUI` | `3437629766/mods/CleanUI/42.19/media/lua/client/ISUI/ISInventoryPane.lua:6` | `require "TimedActions/ISEatFoodAction"` | call | its fork of the inventory pane pulls the action in |
| `CleanUI` | `…/ISUI/ISInventoryPaneContextMenu.lua:4100` | `ISTimedActionQueue.add(ISEatFoodAction:new(playerObj, item, percentage));` | call | **queues** the eat from its forked portion menu — so on this server the eat is started by CleanUI's copy, not vanilla's |
| `CleanUI` | `…/ISUI/ISInventoryPaneContextMenu.lua:2643` | `ISTimedActionQueue.add(ISDrinkFluidAction:new(playerObj, item, percent))` | call | and the drink |
| `SWMisc_Patches` | `3621968227/…/42/media/lua/shared/SWMisc_Patches_Overrides_shared.lua:10,12` | `["ISDrinkFluidAction"] = true,` / `["ISEatFoodAction"] = true,` | read | names both actions as string keys in an override-allow table; not a wrap |
| `Horse` | `3661336777/mods/HorseMod/42/media/lua/shared/HorseMod/patches/ActionBlocker.lua:21,27` | `["ISDrinkFluidAction"] = true,` / `["ISEatFoodAction"] = true,` | read | blocks both actions while mounted, by class-name string; not a wrap |
| `Economy` | `3624538051/mods/Economy/42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:647` | `if serialized.foodRemaining then pcall(item.multiplyFoodValues, item, serialized.foodRemaining) end` | call | the corpus's only `multiplyFoodValues`, inside a protected call, restoring a shop item's remaining food |

**Zero hits, corpus-wide, over all folders:** `ISEatFoodAction:serverStop` / `.serverStop`, `ISEatFoodAction:isValid`, `updateEat` in any form (so `ISDrinkFluidAction:updateEat` too), `OnEat` as a Lua global, `EatFood`, `DrinkFluid`. § 4.2's cancelled-eat seat and its whole fluid seat are uncontested; the `complete` seat is not.

Reading: `QualityCooking` and the nutrition mod would both wrap `ISEatFoodAction.complete` on the server. Both wraps call their original, so both bodies run and neither is lost — but the order decides whether `QualityCooking` scores its buff off the item before or after the mod's own snapshot, and § 4.2's "snapshot the item before the original runs, read it again afterwards" measures the drop in raw hunger, which `QualityCooking`'s wrap does not change. The sharper risk is the reverse: `QualityCooking` has no sentinel, so a Lua reload re-wraps it and the chain grows, and § 4.2's own sentinel must therefore survive being wrapped by an unsentinelled neighbour rather than only by itself.

## 6. Body damage and thermal

Only 10 live hits over 5 mods — the thinnest surface in the sweep.

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `simpleStatus` | `2867431511/mods/SimpleStatus/42.20/media/lua/client/ss.stats.lua:482,486,511,515` | `local thermos = player:getBodyDamage():getThermoregulator()` | call | four client-side reads of the thermoregulator for its status bars |
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/shared/Utilities/CookingDebugCommands.lua:11` | `player:getBodyDamage():setHealthFromFoodTimer(0)` | call | a debug command that clears the food-health timer |
| `EmergencyVomitB42` | `3731711925/…/42/media/lua/server/EmergencyVomit_Main.lua:95` | `callBodyMethod(body, "setHealthFromFoodTimer", 0)` | call | clears the same timer after a vomit, server-side, through a nil-checked indirect call |
| `EmergencyVomitB42` | `3731711925/…/42/media/lua/client/EmergencyVomit_Action.lua:52` | `callBodyMethod(body, "setHealthFromFoodTimer", 0)` | call | the client mirror |
| `ZVirusVaccine42BETA` | `…/42.20/media/lua/server/HealthSystem/LabAlbuminLogic_Server.lua:39` | `body:AddGeneralHealth(newHealth - health)` | call | the corpus's only `AddGeneralHealth` on a player, server-side, from an albumin transfusion |
| `ZVirusVaccine42BETA` | `…/LabCollectBloodLogic_Server.lua:75` | `arm:setBleedingTime(0)` | call | the corpus's only `setBleedingTime`, stopping the draw-site bleed |
| `Economy` | `3624538051/mods/Economy/42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:250` | `{ key = "pain", get = "getPainReduction", set = "setPainReduction" },` | read | a **name** in a serialiser field map, not a call |

**Zero hits, corpus-wide, over all folders:** `ReduceGeneralHealth`, `setOverallBodyHealth`, `setCatchACold`, `setWoundInfectionLevel`, `setInfectionGrowthRate`, `setAimingDelay`, `CharacterStat.TEMPERATURE`. Every one of § 4.5's body-damage-setter, health-drain and aiming-delay channels is uncontested on this server. `setHealthFromFoodTimer` is the one shared field, and both users write it to zero rather than reading it, so a mod that drains health from starvation through that timer has two neighbours that reset it.

## 7. Interface

321 live hits over 27 mods.

**`ISToolTipInv:render` — a seven-deep, non-idempotent wrap chain.** Every one of the seven saves the original into a local and replaces the method with no sentinel and no test for its own wrapper; the mod's own wrap would be the eighth.

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SkillRecoveryJournal` | `2503622437/…/42.20.1/media/lua/client/Skill Recovery Journal Tooltip.lua:215-216` | `local ISToolTipInv_render = ISToolTipInv.render` / `function ISToolTipInv:render()` | wrap-save, definition | **and at `:258` it calls `ISToolTipInv_render_Override(self, journalTooltipWidth)`, its own forked copy of vanilla's render, instead of the chain** — in the journal-tooltip path every wrap below it is skipped; `:274` takes the chain for other items |
| `KATTAJ1_ClothesCore` | `3470422050/mods/KATTAJ1 Clothes Core/42.15/media/lua/client/KATTAJ1_TooltipFixer.lua:3-4,13` | `local old_ISToolTipInv_render = ISToolTipInv.render` / `function ISToolTipInv:render()` / `old_ISToolTipInv_render(self)` | wrap-save, definition, call | clothing tooltip fix; calls through |
| `ItemQuality` | `3624538051/mods/ItemQuality/42/media/lua/client/UI/QualityItemTooltip.lua:95,97,100` | `local originalRender = ISToolTipInv.render` / `function ISToolTipInv:render()` / `originalRender(self)` | wrap-save, definition, call | quality lines; also wraps `ISToolTipInv.setItem` at `:30-32` |
| `QuestSystem` | `3624538051/mods/QuestSystem/42/media/lua/client/EventHandlers/FriendshipBraceletHandler.lua:56,58` | `local originalToolTipRender = ISToolTipInv.render` / `function ISToolTipInv:render()` | wrap-save, definition | bracelet lines |
| `GirthsTweaks` | `3745960616/mods/GirthsTweaks/42/media/lua/client/GT_WeaponTooltip.lua:3,307,317` | `local originalRender = ISToolTipInv.render` / `function ISToolTipInv:render()` / `return originalRender(self)` | wrap-save, definition, call | weapon lines |
| `GirthsTweaks` | `…/client/GT_ItemOwnership.lua:27,30,32` | `local ISToolTipInv_render = ISToolTipInv.render` / `function ISToolTipInv:render()` / `ISToolTipInv_render(self)` | read, definition, call | **a second wrap by the same mod**, in a different file |
| `sd-teleporter` | `3662913642/mods/SD-teleporter/common/media/lua/client/sd-teleporter-tooltip.lua:4,77,87` | `local callback_render = ISToolTipInv.render;` / `function ISToolTipInv:render()` / `return callback_render(self);` | read, definition, call | teleporter lines |

**`ISCharacterInfoWindow` — one mod, the exact three wraps § 4.7 plans.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `AutoCook` | `3388721641/mods/AutoCook/common/media/lua/client/ISCharacterInfoWindow_AddTab.lua:6-8` | `local upperLayer_ISCharacterInfoWindow_createChildren = ISCharacterInfoWindow.createChildren` / `function ISCharacterInfoWindow:createChildren()` / `upperLayer_ISCharacterInfoWindow_createChildren(self)` | wrap-save, definition, call | adds its tab after vanilla builds the children |
| `AutoCook` | `…/ISCharacterInfoWindow_AddTab.lua:16-17,21` | `local upperLayer_ISCharacterInfoWindow_onTabTornOff = ISCharacterInfoWindow.onTabTornOff` / `function ISCharacterInfoWindow:onTabTornOff(view, window)` | wrap-save, definition, call | keeps the tab working when torn off |
| `AutoCook` | `…/ISCharacterInfoWindow_AddTab.lua:29-31` | `local upperLayer_ISCharacterInfoWindow_SaveLayout = ISCharacterInfoWindow.SaveLayout` / `function ISCharacterInfoWindow:SaveLayout(name, layout)` | wrap-save, definition, call | persists its tab's layout |
| `AutoCook` | `…/ISCharacterInfoWindow_AddTab.lua:26` | `--function ISCharacterInfoWindow:RestoreLayout(name, layout)` | comment | **the restore half is commented out** — the gap § 4.7 says it will close |
| `AutoCook` | `3388721641/mods/AutoCook/42.13/media/lua/client/ISCharacterCook.lua:2` and `common/…:2` | `require "ISCharacterInfoWindow_AddTab"` | call | the live `42.13/` tree requires a file only `common/` ships, the merge case the catalog records |

**`ISLayoutManager.RegisterWindow` — one caller in the entire corpus**, `AutoCook`, at `3388721641/mods/AutoCook/common/media/lua/client/ISCharacterInfoWindow_AddTab.lua` (one call). Vanilla itself registers 19 windows, `'charinfowindow'`, `'charinfowindow.info'`, `.skills`, `.health`, `.clothingIns`, `.protection` among them, so § 4.7's panel must register a name outside that set and outside AutoCook's.

**`MoodleFramework` and its consumers.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `MoodleFramework` | `3396446795/mods/MoodleFramework/42.20/media/lua/client/MF_ISMoodle.lua:25` | `function MF.createMoodle(moodleName)` | definition | the framework's own entry point, live on `42.20` |
| `MoodleFramework` | `…/MF_ISMoodle.lua:35` | `function MF.getMoodle(moodleName,playerNum)` | definition | the accessor § 4.7 probes for |
| `MoodleFramework` | `…/MF_ISMoodle.lua:4` | `--MF.createMoodle("Proteins");` | comment | the framework's own example is a **protein moodle** |
| `MoodleFramework` | `…/MF_ISMoodle.lua:255` | `if self.MoodleOscilationLevel < 0.015 then self.MoodleOscilationLevel = 0 end--saturate like MoodlesUI.java` | comment | the only `MoodlesUI` mention in the corpus, and it is a comment |
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/client/UI/CookingBuffMoodle.lua:24` | `MF.createMoodle(BuffMoodle.NAME)` | call | one framework moodle for its cooking buff |
| `QualityCooking` | `…/CookingBuffMoodle.lua:76` | `local moodle = MF.getMoodle(BuffMoodle.NAME, player:getPlayerNum())` | call | sets its value from client state |
| `MoreDifficultZonesB42` | `3325808670/mods/MoreDifficultyB42/common/media/lua/client/MoodleTier.lua:10,16,18` | `MF.createMoodle("SD6Tier"..i)` / `MF.getMoodle("SD6Tier"..i):setValue(strength)` | call | three tier moodles built in a loop |

So the framework has **two** resident consumers holding four moodles between them; a nutrition moodle per symptom class joins a stack that is already non-empty, and the names must not collide with `SD6Tier<n>` or QualityCooking's.

**`PZAPI.ModOptions` — 91 hits over 21 mods.** The option-page ids actually claimed, read off `:create` calls: `P4TidyUpMeister`, `ProximityInventory`, `SimpleStatus`, `CustomGamepadUI`, MoodleFramework's `MF.key`, `NSOENMIOEACTDD`, `Neat_Crafting`, `STA_PryOpen`, `SWMisc`, `PlumbingFixed`, `HorseMod`, `KnoxBuildworks`, `FancyLanterns`, `EssentialCarNotifications`, `SomewhatSlots`, `NewMusic`, `GirthsTweaks`, and via `QuestSystem.ModOptionsBuilder.Build` → `PZAPI.ModOptions:create(modId, modName)` the four ids `QuestSystem`, `Economy`, `QualityCooking`, plus its own. `CleanUI` does not create a page; it **reads** three, `PZAPI.ModOptions:getOptions("CleanUI")`, `("BicycleMod")`, `("ItemRarityUI")`, and calls `:save("BicycleMod")`. `GirthsTweaks` uses the cooperative idiom `PZAPI.ModOptions:getOptions(OPTIONS_ID) or PZAPI.ModOptions:create(OPTIONS_ID, "IGUI_GT_ModOptionsTitle")` in two files — the exemplar for a mod with several option files. No page id resembles `NutritionRevamp` or `NR`.

**`keyBinding` — 10 hits over 3 mods**, all the vanilla `table.insert(keyBinding, bind)` idiom: `FancyLanterns` (`shared/SWFancyLanterns_keyBinding.lua:3,7,11`), `UndeadSurvivor42` (`client/UndeadSurvivor_Hotbar.lua:15,23`), `alicesWeaponSlingRadialMenu` (`client/AliceWeaponSling_RadialMenu.lua:16` `keyBinding = keyBinding or {}`, then `:21,30,34`). The last one's `or {}` guard is the shape to copy; vanilla reads the table at `MainOptions.lua:3478` with the comment `-- keyBinding comes from keyBinding.lua`.

**`ISHealthPanel` — no wrap.** `MiniHealthPanel` (`2866258937/…/MiniHealthTreatments.lua:4,116`) carries two comments — `-- == Literal copy-paste of items functions from ISHealthPanel.lua ==` and `-- FIXME: ISHealthPanel.actions never gets cleared` — and `KWRR_Security` reads `ISHealthPanel.cheat` at `…/KWRR_Security_Client.lua:124` for its anti-cheat. Nobody replaces the panel, so a health-panel line or button is available.

**`ISCollapsableWindow` — 173 hits over 13 mods, of which 26 are `:derive`**: `KnoxBuildworks` 8, `SDQuests` 3, `NewMusic` 3, `GirthsTweaks` 3, `SDHC` 2, and one each from `SkillRecoveryJournal`, `QuestSystem`, `PlumbingFixed`, `MorePlushies`, `errorMagnifier`, `DataLogger`. § 4.7's panel joins a crowd on a class nobody has replaced, which is the uncontested case.

## 8. Data and options

1 052 live hits over 44 mods.

**`ModData.getOrCreate` — 59 hits over 14 mods:** `QuestSystem`, `Economy`, `GirthsTweaks`, `SDQuests`, `SDHC`, `BeyondTen`, `Horse`, `KnoxBuildworks`, `NewMusic`, `ProjectArcade`, `MoreDifficultZonesB42`, `KWRR_Security`, `DataLogger`, `damnlib`. **`ModData.transmit` — 24 hits over 5 mods:** `QuestSystem`, `NewMusic`, `ProjectArcade`, `MoreDifficultZonesB42`, `damnlib`. Every one of those five broadcasts a whole global table, which is the reason § 4.8 keeps the mod's global store off the wire; and `simpleStatus`'s single `transmitModData` on **player** modData (catalog `#1626`) is the reason § 4.8 keeps per-player state out of player modData. Both rules are confirmed to have live triggers on this server.

**Bus module strings.** Extracted from every `sendClientCommand` / `sendServerCommand` / `OnClientCommand` / `OnServerCommand` call in the live trees, first string literal per call: **118 distinct strings over 36 mods**, listed per mod below. `NutritionRevamp` and `NR` appear in none of them, and no string contains `nutri` in any case.

| mod id | strings |
|---|---|
| `QuestSystem` | `ClearPlayer`, `CompleteQuest`, `Create`, `Delete`, `Dump`, `FullSync`, `Grant`, `GrantQuest`, `GrantTitle`, `QuestStateSync`, `QuestStateUpdate`, `QuestSystem`, `RefreshNpcVisuals`, `RemoveGlobal`, `RequestAllPlayers`, `RequestDirectory`, `RequestFullSync`, `RequestSync`, `ResetAll`, `ResetCooldown`, `Revoke`, `Set`, `SetGlobal`, `SetGlobalField`, `SetSelected`, `SyncAllPlayersBegin`, `SyncAllPlayersChunk`, `SyncAllPlayersEnd`, `SyncDirectory`, `SyncGlobal`, `SyncGlobalFields`, `SyncGlobalKeys`, `SyncPlayer`, `SyncPlayerKeys`, `SyncPlayerListPush` |
| `KnoxBuildworks` | `BPBuildBatchEnd`, `BPBuildBatchStart`, `BPForget`, `BPRequest`, `BPSync`, `BPSyncAll`, `BuildableRulesError`, `BuildableRulesRequest`, `BuildableRulesSave`, `BuildableRulesSync`, `DrumMode`, `Hello`, `erosion` |
| `GirthsTweaks` | `CharBackupList`, `CharBackupNow`, `CharBackupRestore`, `CharBackupSearch`, `GirthsTweaks`, `MPSleep`, `SDCaches`, `ZombieLootConfig`, `ZombieLootGet`, `ZombieLootSave`, `ZombieLootSaved`, `map` |
| `NewMusic` | `debug_set`, `debug_sync`, `device_disassemble`, `intent`, `media_flip`, `media_flip_result`, `registry_sync_ack`, `registry_update`, `request_inventory_state_sync`, `request_registry_sync`, `state`, `vehicle_loot_stale_reject` |
| `Economy` | `BankAdminAdjustedSelf`, `BankTransferReceived`, `DrainPendingSales`, `DrainRentNotices`, `Economy`, `Hire`, `Shopkeep` |
| `storm-core-b42` | `cancelTransfer`, `placeItem`, `transferItem`, `ui` |
| `damnlib` | `character`, `player`, `that_damn_lib`, `vehicle` |
| `SDUtils` | `SDDebug`, `SDSafehouse`, `sdLogger`, `vehicle` |
| `BeyondTen` | `RequestSync`, `Sync`, `SyncPerk` |
| `SkillRecoveryJournal` | `ISLogSystem`, `SkillRecoveryJournal`, `SkillRecoveryJournalAdmin` |
| `ProjectArcade` | `CoinPusherPlayResult`, `CoinPusherState`, `PayCoinsResult`, `ProjectArcade` |
| `CleanUI`, `RemoveAllItems`, `SWMisc_Patches` | `object` (vanilla's own module, carried over in forked files) |
| `86fordE150` | `vehicle` |
| single-string mods | `ArcadiaAnimalFix_B42` `ArcadiaAnimalFix` · `CombatTraitsCore` `SWCombatTraitsCore` · `DataLogger` `DataLogger` · `ElyonLib` `ElyonLib` · `EmergencyVomitB42` `EmergencyVomit` · `KWRR_Security` `KWRR_Security` · `PainkillersRemoveMuscleStrain` `lastPill` · `PlumbingFixed` `PlumbingFixed` · `SDHC` `SDHC` · `SDQuests` `SDQuests` · `SDVC` `SDVehicleClaim` · `STA_PryOpen` `STA_PryOpen` · `SWServerUtils` `SWServerUtils` · `SomewhatTraitsCore` `SWTraitsCore` · `UndeadSurvivor42` `UndeadSurvivor` · `WorkingKnowledge` `WorkingKnowledge` · `YAPZLib` `YAPZLib` · `sd-teleporter` `SDT` |

**`sandbox-options.txt` option prefixes.** 56 live files; **47 distinct prefixes**, every option in every file prefixed (no unprefixed option anywhere in the corpus):

`BioGas`, `BookConsumer`, `CHGRedux`, `DAMN`, `DGMC_Bolt_Cutters`, `Economy`, `ExerciseWithCorpses`, `GirthsTweaks`, `HCustoms`, `HereGoesTheSun`, `HorseMod`, `ItemQuality`, `KATTAJ1`, `KWRR_Security`, `KnoxBuildworks`, `MPSleep`, `MailboxStories`, `MorePlushies`, `NewMusic`, `OFC`, `OZD`, `OnWeaponSwing`, `PainkillersRemoveMuscleStrain`, `ProjectArcade`, `ProximityInventory`, `QualityCooking`, `QualityEnhancements`, `QuestSystem`, `SDHC`, `SDQuests`, `SDTeleporter`, `SDVehicleClaim`, `SDVehicleReroll`, `SDbus`, `STA_EngineRebuild`, `STA_PryOpen`, `SWCompanions`, `SWFancyLanterns`, `SWMisc`, `SWServerUtils`, `SkillRecoveryJournal`, `SpawnChanceModifier`, `Storm`, `UndeadSurvivor`, `VVR`, `WorkingKnowledge`, `ZombieVirusVaccineBETA`.

**`NR` is free.** Two prefixes worth naming beside it: `GirthsTweaks` ships **two** prefixes in one file (`GirthsTweaks` and `MPSleep`, 47 options), and `SDDistro` ships two (`OFC`, `SpawnChanceModifier`), so a second prefix in one file is precedented. The largest single file is `KATTAJ1_Military` at 95 options.

**`SandboxVars.` reads — 450 hits over 41 mods.** Almost every mod reads only its own prefix. The cross-reads that matter:

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `QualityCooking` | `3624538051/mods/QualityCooking/42/media/lua/shared/Utilities/QualityCookingConfig.lua:74` | `return STATS_DECREASE[SandboxVars and SandboxVars.StatsDecrease] or 1.0` | call | reads the **vanilla** stats-decrease multiplier the takeover handler also reproduces; also reads `EndRegen` |
| `GirthsTweaks` | `3745960616/…/42/media/lua/server/ST_MPSleep.lua:11,13,15,16` | `if SandboxVars.DayLength == 1 then` | call | branches on vanilla `DayLength`, the option the test plan drives |
| `PlumbingFixed` | `3626008449/…/42/media/lua/client/DebugUIs/Scenarios/DebugPlumbing.lua:15` | `SandboxVars.FoodLoot = 1` | definition-lhs | **writes** a vanilla sandbox var from a client debug scenario |
| `BeyondTen` | `3765241705/…` | `SandboxVars.SkillRecoveryJournal…` (6) | call | reads another mod's prefix for cooperative detection |
| `SkillRecoveryJournal` | `2503622437/…` | `SandboxVars.XpMultiplier`, `SandboxVars.XpMultiplierAffectsPassive` | call | reads vanilla's XP multipliers |
| `SDHC`, `MoreDifficultZonesB42`, `MailboxStories`, `ElyonLib`, `CleanHotBar`, `CleanUI`, `QuestSystem` | various | `SandboxVars.HorseMod…`, `SandboxVars.SDGlobalRewards…`, `SandboxVars.Loot…`, `SandboxVars.ZombieAttractionMultiplier`, `SandboxVars.CommonSense…`, `SandboxVars.EnablePoisoning`, `SandboxVars.MultiplierConfig` | call | more cross-prefix and vanilla reads |

**`SandboxVars.Nutrition` — zero hits.** No mod in the corpus branches on the vanilla nutrition option, so turning it off under takeover breaks nothing a resident reads.

## 9. Food scripts

Read comment-stripped over 2 445 live `.txt` files. **Re-checked and dated 2026-09-27 16:41.**

**`module Base` item blocks naming a vanilla food: zero, still.** The catalog's 2026-09-10 reading holds seventeen days later. The one collision the sweep found is a container, not a food:

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `1VCESTANDARD` | `3421271152/mods/Vanilla Clothing Expansion MP/42.19/media/scripts/VCEcontainers.txt:129` | `item Bag_HydrationBackpack` inside `module Base` | definition | redefines the vanilla `Base.Bag_HydrationBackpack` **fluid_container** record whole (`ItemType = base:container`, `Capacity = 12`) — it names no nutrition key, so the item pass and it share nothing |

So **on `42.20.4` at this stamp the installed corpus still holds no vanilla food override at all**, and the item pass has no corpus precedent for a `module Base` redefinition of a food. (Scope: collisions measured against the 1 005 food, drainable and fluid-container names in `data/food-items.json`; `Horse`'s known `Base.Rope` redefinition is outside that name set.)

**`fluid` blocks: 16, all new names, all in `module Base`.**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `biogas` | `2925657627/mods/biogas/42/media/scripts/BioGasFluids.txt:3` | `fluid LiquidFertilizer` | definition | one new fluid under `module Base` |
| `ZVirusVaccine42BETA` | `3615135168/…/42.20/media/scripts/generated/LabFluids.txt:3,19,51,83,115,142,169,196,223,255,287,319,351,382,413` | `fluid PurifiedWater`, `SodiumHypochlorite`, `HydrogenPeroxide`, `AmmoniumSulfate`, `BloodPlasma`, `BloodCells`, `Leukocytes`, `Antibodies`, `InfectedBlood`, `TaintedBlood`, `SulfuricAcid`, `HydrochloricAcid`, `BrainFluidLow`, `BrainFluidMid`, `BrainFluidHigh` | definition | fifteen new fluids under `module Base` |

**No mod redefines a vanilla fluid name.** § 4.6's decision to re-base drinks only in the per-fluid Lua table — because `fluid` block merging is unread — is therefore untested by the corpus as well: nobody has exercised the merge.

**`evolvedrecipe` blocks: zero.** Mods reach vanilla's evolved recipes through the item key instead:

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `Horse` | `3661336777/mods/HorseMod/42/media/scripts/HorseMod/items/food.txt:10` | `EvolvedRecipe = Pizza:20;Stew:20;Stir fry:20;Sandwich:5\|Cooked;Salad:10\|Cooked;Pasta:20;Rice:20;Taco:5\|Cooked;Burrito:10\|Cooked;AddBaitToChum:20,` | definition | adds one of its own foods as an ingredient to nine vanilla evolved recipes; a second identical key at `:38` |
| `SKITTLE_LongTermPreservation4220` | `3774789651/…/42.20/media/scripts/` | `EvolvedRecipe = …` ×5 | definition | five of its own foods feed vanilla evolved recipes |

**`OnCooked` / `OnEat` / `ReplaceOnCooked` script keys:**

| mod id | file:line | matched text | kind | what it does |
|---|---|---|---|---|
| `SKITTLE_LongTermPreservation4220` | `3774789651/…/42.20/media/scripts/items/items_dried.txt:22` (and 11 more) | `OnCooked = OnCookedTest` / `OnCooked = CannedFood_OnCooked` | definition | 12 `OnCooked` keys whose Lua target multiplies the crafted instance's four macros and `HungChange` by 0.70 in `lua/server/` |
| `ZVirusVaccine42BETA` | `3615135168/…/42.20/media/scripts/` | `ReplaceOnCooked = …` ×4 | definition | four cook-replacement items |
| `SDQuests` | `3745960616/mods/SDQuests/42/media/scripts/SDQBoneHurtingJuice.txt:23` | `OnEat = SDQBoneHurtingJuice_OnEat,` | definition | **the corpus's only `OnEat` script key**; its target is `function SDQBoneHurtingJuice_OnEat(food, character, percent)` at `3745960616/mods/SDQuests/42/media/lua/shared/SDQBoneHurtingJuice.lua:39` — a bare global in `shared/`, exactly the shape the eat-hook rules prescribe |

So the script-hook seats the mod might use are held on one item each: `OnEat` by one quest food, `OnCooked` by the preservation mod's fourteen. Neither is a global seat, because both keys are per item.

## 10. Cadence

Live registrations, non-comment, per mod and per side (`client` = under `lua/client/`, `server` = under `lua/server/`, `shared` = under `lua/shared/`, which executes in both states).

| mod id | OnTick | OnPlayerUpdate | EveryOneMinute | EveryTenMinutes | sides |
|---|---:|---:|---:|---:|---|
| `SomewhatTraitsCore` | **24** | 6 | 0 | 0 | OnTick server×24; OnPlayerUpdate client×6 |
| `NewMusic` | 12 | 0 | 2 | 0 | OnTick client×6 server×6; EveryOneMinute server×2 |
| `Horse` | 7 | 4 | 0 | 0 | OnTick shared×5 client×2; OnPlayerUpdate client×3 shared×1 |
| `KnoxBuildworks` | 7 | 1 | 2 | 0 | OnTick client×6 shared×1; EveryOneMinute shared×2 |
| `CleanUI` | 6 | 0 | 0 | 0 | OnTick client×6 |
| `GirthsTweaks` | 4 | 3 | 4 | 2 | OnTick client×4; OnPlayerUpdate client×2 server×1; EveryOneMinute server×3 client×1; EveryTenMinutes server×1 client×1 |
| `alicesWeaponSling` | 4 | 0 | 0 | 0 | OnTick shared×3 client×1 |
| `BeyondTen` | 3 | 1 | 0 | 0 | OnTick client×1 server×1 shared×1; OnPlayerUpdate client×1 |
| `QuestSystem` | 3 | 1 | 3 | 0 | OnTick server×2 shared×1; EveryOneMinute client×1 server×1 shared×1 |
| `ZVirusVaccine42BETA` | 3 | 0 | 1 | 2 | OnTick server×2 client×1; EveryOneMinute server×1; EveryTenMinutes server×2 |
| `storm-core-b42` | 3 | 0 | 0 | 0 | OnTick client×3 |
| `SDUtils` | 2 | 1 | 1 | 0 | OnTick client×1 server×1 |
| `ElyonLib` | 2 | 0 | 1 | 0 | OnTick client×1 shared×1; EveryOneMinute shared×1 |
| `KWRR_Security` | 2 | 0 | 1 | 1 | OnTick client×2; EveryOneMinute client×1; EveryTenMinutes server×1 |
| `ProjectArcade` | 2 | 0 | 0 | 0 | OnTick client×1 server×1 |
| `YAPZLib` | 2 | 0 | 0 | 0 | OnTick shared×2 |
| `SWServerUtils` | 0 | 3 | **5** | 1 | EveryOneMinute client×5; EveryTenMinutes client×1; OnPlayerUpdate client×2 shared×1 |
| `ItemQuality` | 1 | 1 | 0 | 0 | OnTick shared×1; OnPlayerUpdate shared×1 |
| `HereGoesTheSun` | 1 | 0 | 2 | 0 | EveryOneMinute server×1 shared×1; OnTick client×1 |
| `SkillRecoveryJournal` | 1 | 0 | 0 | 0 | OnTick shared×1 |
| `FasterResting` | 1 | 0 | 0 | 0 | OnTick server×1 |
| `ArcadiaAnimalFix_B42` | 1 | 0 | 0 | 0 | OnTick server×1 |
| `CleanHotBar`, `MoreDifficultZombiesB42`, `Neat_Crafting`, `SDBus` | 1 each | 0 | 0 | 0 | OnTick client×1 each |
| `QualityCooking` | 0 | 0 | 2 | 0 | EveryOneMinute server×1 client×1 |
| `SDQuests` | 0 | 0 | 1 | 2 | EveryOneMinute server×1; EveryTenMinutes server×1 shared×1 |
| `SDVC` | 0 | 0 | 2 | 0 | EveryOneMinute server×2 |
| `DataLogger` | 0 | 0 | 2 | 1 | EveryOneMinute client×1 server×1; EveryTenMinutes server×1 |
| `PlumbingFixed` | 0 | 0 | 1 | 0 | EveryOneMinute server×1 |
| `MoreDifficultZonesB42` | 0 | 1 | 1 | 0 | EveryOneMinute client×1; OnPlayerUpdate shared×1 |
| `dustinguished_bolt_cutters` | 0 | 0 | 1 | 0 | EveryOneMinute shared×1 |
| `CombatTraitsCore` | 0 | 1 | 0 | 1 | EveryTenMinutes client×1; OnPlayerUpdate client×1 |
| `OZD-ZonesB42` | 0 | 0 | 0 | 1 | EveryTenMinutes server×1 |
| `sd-teleporter` | 0 | 2 | 0 | 1 | EveryTenMinutes server×1; OnPlayerUpdate client×2 |
| `EmergencyVomitB42` | 0 | 2 | 0 | 0 | OnPlayerUpdate client×1 server×1 |
| `PainkillersRemoveMuscleStrain` | 0 | 0 | 0 | 1 | EveryTenMinutes (via `common/shared/`) |
| 27 car mods + 9 others | 0 | 1–2 each | 0 | 0 | almost all `OnPlayerUpdate client×1` or `server×1` |

**Totals: `OnTick` 95 registrations over 25 mods; `OnPlayerUpdate` 66 over 47; `EveryOneMinute` 32 over 17; `EveryTenMinutes` 12 over 9.** Against the catalog's 2026-09-10 census (`OnTick` 70/15, `OnPlayerUpdate` 55/39, `EveryOneMinute` 22/10) these are higher because this sweep counts `common/` as well as the live version folder and reads registrations directly rather than summing each record's top eight events.

**What runs on a dedicated server.** Counting `server/` plus `shared/` registrations only: `OnTick` about **55** (39 `server/` + 16 `shared/`, 24 of the 39 one mod's), `EveryOneMinute` about **18** (12 `server/` + 6 `shared/`), `EveryTenMinutes` about **7**. So § 4.1's slow clock joins a minute tier carrying roughly eighteen handlers, and the takeover handler runs beside roughly fifty-five per-tick handlers — which is the cost context for § 6's hot-path budget, and the reason `SomewhatTraitsCore`'s 24 server `OnTick` handlers are the single largest per-tick neighbour on the box.

## Vanilla Lua neighbours

3 378 hits over 1 395 files. Vanilla's own Lua is a neighbour on nine of the ten surfaces; the readings that bear on the design:

**Surface 1.** `CalculateStats`, `LuaHookManager` and `TriggerHook` appear **nowhere** in `media/lua`. The `Hook` table is used at `client/ISUI/ISInventoryPaneContextMenu.lua:4056,4060` (`Hook.AutoDrink`), `client/TimedActions/ISContextualActions.lua:144` (`Hook.ContextualAction.Add`) and `shared/TimedActions/ISReloadWeaponAction.lua:544` (`Hook.Attack.Add`). So the hook the mod registers is a Java-side surface with no Lua-side vanilla registrant — consistent with § 4.1's controller notes N5/N6 being jar readings rather than Lua readings.

**Surface 3 — the sharpest vanilla neighbour of all.** `server/XpSystem/XpUpdate.lua` owns the Strength and Fitness economy the mod clamps:
- `:395` `Events.LevelPerk.Add(xpUpdate.levelPerk)` and `:209-242` — on **every level change**, `xpUpdate.levelPerk` removes and re-adds the Strength traits `WEAK`/`FEEBLE`/`STOUT`/`STRONG` and the Fitness traits `UNFIT`/`OUT_OF_SHAPE`/`FIT`/`ATHLETIC` by band. Whether § 4.3's `setPerkLevelDebug` write fires `Events.LevelPerk` decides whether the clamp also rewrites eight traits it never named; if it does, a level fall strips `STRONG` and adds `FEEBLE`, and the mod's trait-ownership flag must cover those eight too.
- `:381` `Events.EveryTenMinutes.Add(xpUpdate.everyTenMinutes)` and `:298-333` — the decay loop that credits **negative** XP to Strength and Fitness through `addXp(playerObj, Perks.Strength, getLoosingXpValue())` at `:312` and `:325`, then calls `xpUpdate.checkForLosingLevel`, which calls `playerObj:LoseLevel(perk)` at `:294`. This runs on the minute-ten tier the mod also uses, and it is the mechanism that makes "the shown level is the smaller of vanilla's own level and a ceiling" a moving target rather than a static one.
- `:334-345` `xpUpdate.getModData` writes `strengthUpTimer`, `strengthMod`, `fitnessUpTimer`, `fitnessMod` into **player modData**. Vanilla's own XP decay state therefore sits in the channel a neighbour's `transmitModData` wipes — the risk § 4.8 avoids for the mod's state is one vanilla already takes for its own.
- `:393` `Events.AddXP.Add(xpUpdate.addXp)`, `:176-199` — the vanilla `Events.AddXP` listener that resets the decay timers and is the third listener on that event beside `BeyondTen`'s two and `SkillRecoveryJournal`'s one.
- `:14,70` read `CharacterStat.ENDURANCE` against `getStats():getEnduranceWarning()` to decide whether a run or a hit grants Fitness or Strength XP — so the endurance value the fast clock writes **gates vanilla's own training signal**, which is § 4.3's training-sample input read from the other end.
- `setPerkLevelDebug` in vanilla: five sites, all non-production — `client/DebugUIs/DebugMenu/General/ISStatsAndBody.lua:229`, `client/DebugUIs/Scenarios/AiteronScenario.lua:83`, `client/DebugUIs/Scenarios/PatrickScenario.lua:99`, `client/Tests/TimedActionsTests.lua:141`, `shared/NPCs/SurvivorSwap.lua:29`.

**Surface 2.** `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:659` `sendClientCommand(getPlayer(), 'player', 'setWeight', args)` → `server/ClientCommands.lua:599` `Commands.player.setWeight` → `:602` `otherPlayer:getNutrition():setWeight(args.weight)`. Vanilla ships an **admin bus command on module `'player'` that writes the body-weight slot server-side**, and the same panel adds and removes traits at `:594,669` and calls `SyncXp` at `:596,671`. So the weight slot § 4.3 writes each minute, and the traits § 4.5 toggles, both have a vanilla admin path that can move them between two of the mod's ticks. `shared/NPCs/SurvivorSwap.lua:34` `playerObj:getNutrition():setWeight(data.weight or 80)` is the other writer. `server/Traps/STrapGlobalObject.lua:352` `item:setWeight(actualWeight)`.

**Surface 4.** `sendSyncPlayerFields` bitmasks in use: `0x00000001` (`shared/TimedActions/ISResearchRecipe.lua:85`), `0x00000007` (`shared/TimedActions/ISReadABook.lua:374` — so bit 2, the bit § 4.5 plans, is already sent by vanilla inside that mask), `0x00000010` (`shared/TimedActions/ISWriteSomething.lua:71,78,98`). `syncPlayerStats` masks: `SyncPlayerStatsPacket.Stat_Thirst` (`ISDrinkFromBottle.lua:82`), `0x00000100` (eight healing actions), `0x00000002` (`SFarmingSystem.lua:503`, `ISRemoveBush.lua:172`). `syncBodyPart` masks range from `0x00480000` to `0xFFFFFFFFFFF` (`server/ClientCommands.lua:596`). `getCharacterTraits():add/remove` — 19 sites, twelve of them the `XpUpdate.lua` band swaps above. `shared/Definitions/TraitClothingSelectionDefinitions.lua:101` keys a clothing table off `CharacterTrait.SHORT_SIGHTED` and `shared/Items/SpawnItems.lua:233` keys a spawn table off `CharacterTrait.NIGHT_VISION` — **both are character-creation reads**, so granting either trait at day fourteen retro-fits no clothing and spawns no keyring, which is a display-consistency note rather than a conflict.

**Surface 5.** `shared/TimedActions/ISEatFoodAction.lua` — the seats exist exactly as § 4.2 names them: `:23 isValid`, `:126 stop` (which at `:136-137` calls `self:serverStop()` only when neither client nor server), `:141 serverStop`, `:155 perform`, `:173 complete` (`self.character:Eat(self.item, self.percentage, self.useUtensil)` at `:174`), `:193 eat` (`:199` the same `Eat` call at a per-bite percentage), `:203 getDuration`, `:305 if not isServer() then` inside `new`. `shared/TimedActions/ISDrinkFluidAction.lua` — `:109 updateEat` is the only place litres move (`:116 self.character:DrinkFluid(self.item, deltaToConsume, self.useUtensil)` then `:117 self.item:syncItemFields()`), reached from `:29 update`, `:45 animEvent` under `if isServer()`, and `:105 complete` with `self:updateEat(1)`. § 4.2's "the only seat the fluid path has" is confirmed by the file. `shared/Traps/TimedActions/ISAddBaitAction.lua:39` `bait:multiplyFoodValues(1.0 - math.min(-0.05 / bait:getHungChange(), 1.0))` is vanilla's own use of the item-wide macro scaler, keyed off `getHungChange()`.

**Surface 6.** `ReduceGeneralHealth` and `AddGeneralHealth` appear once each, both in `client/DebugUIs/DebugMenu/General/ISStatsAndBody.lua:242,244`, so the health-drain channel is an engine surface with no production Lua caller. `setCatchACold(0.0)` once, `client/LastStand/AReallyCDDAy.lua:78`. `setWoundInfectionLevel` four sites, all the health panel and its bus twin (`ISHealthPanel.lua:298,300`, `ClientCommands.lua:567,569`). `setBleedingTime` six, same pair. `setAimingDelay` **once**, `shared/TimedActions/ISRackFirearm.lua:32` `self.character:setAimingDelay(self.character:getAimingDelay() + self.gun:getAimingTime() * (0.15 - …))` — so § 4.5's per-shot aiming-delay write shares the setter with racking a firearm, and the two are additive on the same field. `getThermoregulator()` six reads, all debug and clothing-insulation panels. `CharacterStat.TEMPERATURE` once, `ISStatsAndBody.lua:77`, a debug slider.

**Surface 7.** `client/ISUI/ISToolTipInv.lua:43 function ISToolTipInv:render()` is the single definition the seven corpus wraps and the mod's eighth all chain onto; `:3 ISToolTipInv = ISPanel:derive("ISToolTipInv")`, `:9 setItem`, `:181 new`. `ISCharacterInfoWindow` is at `client/XpSystem/ISUI/ISCharacterInfoWindow.lua` — `:103 createChildren`, `:182 onTabTornOff`, `:202 RestoreLayout`, `:291 SaveLayout`, `:331 new` — and it registers six layout names at `:154,185,188,191,194,197`. `ISLayoutManager.RegisterWindow` is defined at `client/ISUI/ISLayoutManager.lua:6` and called 19 times. `PZAPI.ModOptions` lives at `client/PZAPI/ModOptions.lua` — `:247 create`, `:255 getOptions`, `:259 save`, `:292 load` — and `client/OptionScreens/MainOptions.lua` reads `keyBinding` at `:3478-3481` with the comment `-- keyBinding comes from keyBinding.lua`, plus `MainOptions.keyBindingLength` layout arithmetic at `:2157,2175,2347-2352`. **`MoodlesUI` is reachable from Lua and vanilla uses it**: `shared/TimedActions/ISReloadWeaponAction.lua:474-483` calls `MoodlesUI.getInstance()` and `MoodlesUI.getInstance():wiggle(MoodleType.PANIC / STRESS / DRUNK / TIRED / ENDURANCE / PAIN)`, seven calls — which is a partial pass on § 4.7's exposure test (the instance and `wiggle` are exposed; whether a position or geometry getter is, is a separate read).

**Surface 8.** `ModData.getOrCreate` 7 sites, `ModData.transmit` **1** — `server/Foraging/forageServer.lua:49 ModData.transmit("forageData")`, so vanilla itself broadcasts one global table. `sendClientCommand` 113, `sendServerCommand` 30. `SandboxVars.` 1 583 reads. Vanilla's own animal bus uses module `'animal'` with commands `setHunger`, `setThirst`, `setStress` (`client/ISUI/Animal/ISAnimalContextMenu.lua:597,732,735` → `server/ClientCommands.lua:875,891,899`), which is why the S2 `setHunger`/`setThirst` hits in vanilla are animal commands and not player writes.

**Surface 10.** Vanilla registers `OnTick` 22, `OnPlayerUpdate` 3, `EveryOneMinute` 2, `EveryTenMinutes` 7 — one of the seven being `xpUpdate.everyTenMinutes`. So the mod's slow clock shares its tier with vanilla's own Strength and Fitness decay.

## Verdicts

Per resident-stack mod, then every other mod with a hit that matters. A verdict is a reading of shipped files, and no pair of these was booted together.

**The resident stack.**

| mod | verdict | reason |
|---|---|---|
| `QualityCooking` (new on item `3624538051`) | **needs a rule and a code read before release; a patch mod is likely** | The only mod sharing § 4.2's `ISEatFoodAction.complete` seat, and it also wraps `.eat`; it writes `ENDURANCE`, `FATIGUE` and `HUNGER` server-side on `EveryOneMinute` with vanilla's own constants, which the takeover handler's next tick discards for endurance (the handler writes from its own store and never reads back) and overwrites for hunger (derived from stomach fill); it reads the four macros off the eaten food, so the item pass silently re-scales its buff tiers; it writes `setMaxWeightBase` and restores a cached base on expiry. Coexistence is possible on the wrap (both call their originals) and impossible on the stat writes without a stated rule. Its `MF` moodle name must not collide. |
| `CleanUI` | **coexists, with a rule** | 6 client `OnTick` handlers, no stat writes of its own, 7 `CharacterStat.` reads. It **queues both the eat and the drink from its forked context menu**, so the actions the mod wraps are constructed by CleanUI's copy on this server; the wraps still apply, because the wrap is on the class and not on the call site. The standing rules already cover it: no Lua file at a vanilla relative path, no status widget on top of its redraw. |
| `SomewhatTraitsCore` | **needs a rule** | 28 server-side stat writes from **24 `OnTick` handlers**, including five endurance credits and five fatigue credits — a second owner of two stats § 4.1 makes the mod authoritative for, on a faster clock. It also wraps `ISEatFoodAction.getDuration` and `ISDrinkFluidAction.getDuration` in `shared/`, which the mod does not touch. Its calorie write (the corpus's only player macro write) is a third owner of the calorie store. No packaging lever separates two writers of one stat on one side; the rule is a release note naming the trait. |
| `GirthsTweaks` | **needs a rule** | `ST_MPSleep.lua` **sets** `FATIGUE` to zero and writes `ENDURANCE` absolutely on the server, from a value it stashes in modData across a sleep — an absolute write that the fast clock's own stored value will overwrite on the next tick, so the mod breaks its multiplayer sleep feature unless § 4.4's sleep-debt model is told about it. It is also the corpus's only runtime trait remover and its only two-prefix sandbox file, and it wraps `ISToolTipInv:render` twice. |
| `SkillRecoveryJournal` | **coexists, with a rule** | Wraps `ISToolTipInv:render` and, in its own tooltip path, calls a **forked copy of vanilla's render** instead of the chain — so a mod wrapping below it loses its tooltip lines whenever the journal tooltip is shown. `canAddFitnessXp()` and `getProteins()` in `shared/` consume numbers the mod re-bases. Its `sendSyncPlayerFields(player, 0x1)` is a different bit from § 4.5's `2`. The rule is a load-order note, not code. |
| `AutoCook` | **coexists** | Sole owner of the three `ISCharacterInfoWindow` wraps and the corpus's only `ISLayoutManager.RegisterWindow` caller. § 4.7 plans the same three wraps, which compose as long as the mod's own are idempotent and save AutoCook's rather than vanilla's; the `RestoreLayout` gap is AutoCook's own commented-out line, so closing it is additive. Its entry points live in `common/` only, as the catalog records. |
| `MoodleFramework` | **coexists** | Whole on this build; `MF.createMoodle` and `MF.getMoodle` are both defined in the live `42.20/` copy. Two other consumers already hold four moodles. Detection, never a `require=`, per § 4.9. |
| `simpleStatus` | **coexists, and will misreport** | Live folder has moved `42.16 → 42.20`, so the catalog's line cites need re-locating. 26 client `CharacterStat.` reads and four `getThermoregulator()` reads, no writes. Its bars read a re-based scale against hard-coded bands and will be wrong without anything failing; and its single `transmitModData` on player modData is the reason § 4.8 keeps mod state out of that table. |
| `SKITTLE_LongTermPreservation4220` | **coexists** | 12 `OnCooked` script keys and 5 `EvolvedRecipe` keys, all on foods in `module Skittles`; one `item:setWeight` beside its macro scaling. The item pass does not reach its module. |
| `Horse` | **coexists** | Its `module Base` collision is `Rope`, not a food. It blocks `ISEatFoodAction` and `ISDrinkFluidAction` by class-name string while mounted, reads `CharacterTrait.EAGLE_EYED` into a fall table, writes `PAIN` client-side and calls `syncBodyPart` client-side four times. Nothing the mod owns. |
| `QuestSystem`, `Economy`, `BaseQuests`, `SDQuests`, `ItemQuality`, `QualityEnhancements` (rest of item `3624538051` / `3745960616`) | **coexist, with a bus-name rule** | Between them: ~120 bus strings, two `ISToolTipInv:render` wraps, `Economy`'s `multiplyFoodValues` and its `setPainReduction`/`setWeight` serialiser field map, `SDQuests`'s single `OnEat` script key, `QuestSystem`'s shared `ModOptionsBuilder`. None writes a stat the mod owns. The rule is a module name none of them uses. |

**Other mods with a hit that matters.**

| mod | verdict | reason |
|---|---|---|
| `EmergencyVomitB42` | **coexists, with a rule** | Floors `HUNGER` at 0.75 and `THIRST` at 0.80 and drains 0.80 endurance after a vomit, on **both** sides, and clears `setHealthFromFoodTimer`. Every one of those is a stat the model owns, so the rule is that a vomit is an external event the model must read rather than fight. Its `ISEatFoodAction` wrap is the corpus's only **idempotent** one, with a sentinel — the exemplar § 4.2's own sentinel should match. |
| `SWMisc_Patches` | **needs a rule** | Strips the `Perks.Fitness` XP boost from the **Underweight** and **Overweight** trait definitions in `shared/`, so the band traits § 4.3 refreshes mean something different on this server; also rewrites Keen Hearing exclusivity. A definition edit at load is invisible to any runtime check the mod could make, so the rule is a named incompatibility of the band-trait semantics, not of the code. |
| `BeyondTen` | **needs a rule** | Two `Events.AddXP` listeners (client and server), `setXPToLevel` on both sides, an `OnWeaponHitXp` listener in `shared/`, an absolute `ENDURANCE` write in `shared/`, and it treats Strength and Fitness as its passive pair — the same pair § 4.3 clamps. Its levels 11–15 sit above vanilla's max, so a ceiling clamped to the vanilla perk range fights it directly. This is the second mod after `QualityCooking` whose code must be read before release. |
| `FasterResting`, `SWServerUtils` | **need a rule** | Both write `ENDURANCE` server-side (`FasterResting` on `OnTick`, `SWServerUtils` from an admin command). Under takeover the fast clock's write is the last before the push, so both lose silently; the rule is a release note. |
| `ProjectArcade` | **coexists, with a rule** | Absolute `BOREDOM`, `UNHAPPINESS`, `STRESS` writes plus `bd:setBoredomLevel`, on both sides. § 4.5 writes stress and unhappiness through coefficients and leaves boredom alone, so the overlap is two of three and the writes are event-driven rather than clocked. |
| `storm-core-b42`, `ZVirusVaccine42BETA`, `KeenPerception`, `SomewhatTraits`, `CombatTraits`, `CombatTraitsCore`, `PainkillersRemoveMuscleStrain`, `BookConsumerB42`, `ExerciseWithCorpses`, `OZD-ZonesB42`, `STA_PryOpen`, `dustinguished_bolt_cutters`, `WorkingKnowledge`, `KnoxBuildworks`, `ElyonLib`, `NewMusic`, `1VCESTANDARD`, `biogas`, `JadePackingSD`, `MiniHealthPanel`, `KWRR_Security`, `KATTAJ1_ClothesCore`, `sd-teleporter`, `MoreDifficultZonesB42`, `SWMisc_Resting`, `PlumbingFixed`, `DataLogger`, `SDVC`, `SDUtils`, `SDBus`, `SDHC`, `YAPZLib`, `damnlib`, `ArcadiaAnimalFix_B42`, `CleanHotBar`, `Neat_Crafting`, `alicesWeaponSling(RadialMenu)`, `UndeadSurvivor42`, `FancyLanterns`, `CustomGamepadUI`, `EssentialCarNotifications`, `P4TidyUpMeister`, `ProximityInventory`, `SomewhatCompanions`, `MorePlushies`, `HayesCustoms`, `KATTAJ1_Military`, `MailboxStories`, `VVR`, `CHGRedux`, `RemoveAllItems`, `errorMagnifier`, `RikuMeleeB42`, `HereGoesTheSun`, `MoreDifficultZombiesB42`, `ResearchLabInternProfession`, `STA_EngineRebuild`, `90pierceArrow`, `SDDistro`, `NSOENMIOEACTDD`, and the 27 car mods | **coexist** | Each hits only surfaces the mod does not own, or hits an owned surface once in a dev path, a serialiser field map, a comment or an event the mod never fires. `ZVirusVaccine42BETA` is the widest of them at eight surfaces, and every one of its hits is on a stat or body field § 4.5 does not claim (`PANIC`, `PAIN`, `ZOMBIE_INFECTION`, one `AddGeneralHealth`, one `setBleedingTime`) or is a new fluid under `module Base`. `KnoxBuildworks`'s `setPerkLevelDebug` is inside a client build-test runner. |
| `(vanilla `media/lua`)` | **coexists, with two rules** | `XpUpdate.lua`'s `Events.LevelPerk` band-trait swap and its `EveryTenMinutes` Strength/Fitness decay are the two vanilla neighbours § 4.3's clamp must be written against: the first may rewrite eight traits the clamp never names, the second moves the level the clamp reads. `ClientCommands.lua`'s `player.setWeight` admin path and the `ISPlayerStatsUI` trait buttons are an out-of-band writer of two values the mod owns. |

**Nobody is `incompatible` on the installed corpus.** Every collision found here is either a second writer of a stat (resolved by a stated rule and a release note, because no packaging lever separates two writers of one field on one side) or a wrap chain that composes. The `incompatible` verdict belongs to the public Workshop nutrition overhauls, none of which is installed here — that is [`compat-workshop-neighbours.md`](compat-workshop-neighbours.md)'s question, not this sweep's.

## Claims candidates

Each line is one fact, grade **C**, bound **snapshot**, sweep date **2026-09-27**.

1. No `.lua` file in any folder of the 234-mod installed workshop corpus references `CalculateStats`, `Hook.CalculateStats`, `LuaHookManager` or `TriggerHook`, and the corpus's only `Hook.<name>` use is CleanUI's `Hook.AutoDrink` carried over from its fork of vanilla's context menu — 2026-09-27 16:28 sweep. [C/snapshot]
2. Vanilla's `media/lua` references no stat hook either: its `Hook` uses are `AutoDrink`, `ContextualAction` and `Attack` only, over 1 395 files — 2026-09-27. [C/snapshot]
3. The installed corpus at the 2026-09-27 16:28 sweep is 182 workshop items holding 234 mod folders, against 179 / 230 on 2026-09-10, with 4 folders added (`QualityCooking`, `NewMusic`, `SDMusic`, `SDMixtape`), none removed, and 4 live folders moved (`isoContainers`, `SimpleStatus`, `KI5campers`, `70chevelle`, each to a `42.20` tree). [C/snapshot]
4. Workshop item `3624538051` now ships six mod folders rather than the five a 2026-09-10 reading names, the sixth being `QualityCooking` — 2026-09-27. [C/snapshot]
5. `simpleStatus`'s live folder is `42.20` at the 2026-09-27 sweep, not the `42.16` its teardown's line cites name, so those cites are drifted and must be re-located by content. [C/snapshot]
6. `QualityCooking` wraps both `ISEatFoodAction.complete` and `ISEatFoodAction.eat` in a `server/` file with no idempotency sentinel, at `3624538051/mods/QualityCooking/42/media/lua/server/EventHandlers/CookingRollHandler.lua:170-181` — 2026-09-27. [C/snapshot]
7. `QualityCooking` reads an eaten food's four macros inside that wrap (`BuffMath.Macros(food, fraction)` at the same file `:156`) to allocate buff points, making it a consumer of every value a vanilla-food re-base moves — 2026-09-27. [C/snapshot]
8. `QualityCooking`'s `EveryOneMinute` server handler writes `CharacterStat.ENDURANCE`, `FATIGUE` and `HUNGER` through `stats:add` using `ZomboidGlobals.ImobileEnduranceIncrease`, `ZomboidGlobals.FatigueIncrease` and `ZomboidGlobals.HungerIncrease`, at `…/CookingBuffTicker.lua:25,33,39` — 2026-09-27. [C/snapshot]
9. `setMaxWeightDelta` has zero hits in any folder of the installed corpus, while `setMaxWeightBase` has two, both `QualityCooking`'s, one of which restores a cached pre-buff base on expiry — 2026-09-27. [C/snapshot]
10. Exactly three mods wrap a method of `ISEatFoodAction` in the live corpus — `QualityCooking` (`complete`, `eat`, server), `EmergencyVomitB42` (`start`, `complete`, `eat`, client) and `SomewhatTraitsCore` (`getDuration`, shared) — and `EmergencyVomitB42`'s is the only one with an idempotency sentinel — 2026-09-27. [C/snapshot]
11. `ISEatFoodAction:serverStop`, `ISEatFoodAction:isValid` and `updateEat` in any form have zero hits in any folder of the installed corpus, so the cancelled-eat seat and the whole fluid seat are uncontested — 2026-09-27. [C/snapshot]
12. `ISToolTipInv:render` is wrapped by seven files across six mods in the live corpus, none with an idempotency sentinel, and `SkillRecoveryJournal`'s wrap calls a forked copy of vanilla's render rather than the saved chain in its own tooltip path — 2026-09-27. [C/snapshot]
13. `AutoCook` is the only mod in the corpus wrapping `ISCharacterInfoWindow` and the only caller of `ISLayoutManager.RegisterWindow`; vanilla registers 19 windows including six `charinfowindow*` names — 2026-09-27. [C/snapshot]
14. `MoodleFramework` has two resident consumers holding four moodles between them at the 2026-09-27 sweep: `QualityCooking` one and `MoreDifficultZonesB42` three (`SD6Tier<n>`). [C/snapshot]
15. `MoodlesUI` is called from vanilla's own Lua — seven `MoodlesUI.getInstance()` and `:wiggle(MoodleType.…)` calls at `shared/TimedActions/ISReloadWeaponAction.lua:474-483` — and by no mod in the corpus — 2026-09-27. [C/snapshot]
16. `applyTraitFromWeight` and any `getNutrition():set*` call have zero hits in the installed corpus, and `applyTraitFromWeight` has zero in vanilla's `media/lua` too — 2026-09-27. [C/snapshot]
17. `ReduceGeneralHealth`, `setOverallBodyHealth`, `setCatchACold`, `setWoundInfectionLevel`, `setInfectionGrowthRate`, `setAimingDelay` and `CharacterStat.TEMPERATURE` have zero hits in any folder of the installed corpus — 2026-09-27. [C/snapshot]
18. No mod in the installed corpus adds or removes `CharacterTrait.NIGHT_VISION`, `SHORT_SIGHTED`, `EAGLE_EYED`, `KEEN_HEARING` or a band trait on a player at runtime; the corpus's only runtime trait mutation is `GirthsTweaks` removing `CharacterTrait.INSOMNIAC` on both sides — 2026-09-27. [C/snapshot]
19. `SWMisc_Patches` strips the `Perks.Fitness` XP boost from the vanilla **Underweight** and **Overweight** trait definitions at load, in `shared/`, at `3621968227/mods/SWMisc_Patches/42/media/lua/shared/SWMisc_Patches_Traits.lua:8,11` — 2026-09-27. [C/snapshot]
20. `sendSyncPlayerFields` has exactly two corpus hits, both `SkillRecoveryJournal`'s at bit `0x00000001` and behind an `isServer()` test and a member nil-check; vanilla itself sends `0x1`, `0x7` and `0x10` — 2026-09-27. [C/snapshot]
21. The corpus's live bus calls yield 118 distinct first-literal strings over 36 mods, and neither `NutritionRevamp` nor `NR` nor any string containing `nutri` is among them — 2026-09-27. [C/snapshot]
22. The corpus ships 56 live `sandbox-options.txt` files carrying 47 distinct option prefixes, every option prefixed, and `NR` is not among them; two mods ship two prefixes in one file — 2026-09-27. [C/snapshot]
23. No mod in the installed corpus reads `SandboxVars.Nutrition`; `QualityCooking` reads `SandboxVars.StatsDecrease` and an `EndRegen` option, and `GirthsTweaks` branches on `SandboxVars.DayLength` — 2026-09-27. [C/snapshot]
24. On `42.20.4` at the 2026-09-27 sweep the installed corpus still holds no `module Base` item block naming a vanilla food; the one collision with the 1 005-name food dataset is `1VCESTANDARD` redefining the `Base.Bag_HydrationBackpack` fluid-container record. [C/snapshot]
25. The corpus's 16 live `fluid` blocks (1 `biogas`, 15 `ZVirusVaccine42BETA`) all declare new names under `module Base`, and no mod redefines a vanilla fluid or declares an `evolvedrecipe` block — 2026-09-27. [C/snapshot]
26. The corpus holds exactly one `OnEat` script key, `SDQuests`'s at `3745960616/mods/SDQuests/42/media/scripts/SDQBoneHurtingJuice.txt:23`, whose target is a bare global in `shared/` at `…/lua/shared/SDQBoneHurtingJuice.lua:39` — 2026-09-27. [C/snapshot]
27. Live corpus event registrations at the 2026-09-27 sweep, counting the live version folder plus `common/`: `OnTick` 95 over 25 mods, `OnPlayerUpdate` 66 over 47, `EveryOneMinute` 32 over 17, `EveryTenMinutes` 12 over 9. [C/snapshot]
28. Of those, the handlers that execute on a dedicated server (`server/` plus `shared/`) are about 55 on `OnTick`, 18 on `EveryOneMinute` and 7 on `EveryTenMinutes`; 24 of the `OnTick` handlers are `SomewhatTraitsCore`'s alone — 2026-09-27. [C/snapshot]
29. `SomewhatTraitsCore` writes 28 player stats from one server file (`endurance`, `fatigue`, `stress`, `unhappiness`, `boredom`, `intoxication`) at `3498347699/mods/SomewhatTraitsCore/42.15/media/lua/server/SWTraitsCore_server.lua`, and ships a larger client implementation in its dead `42.12/` and root `media/` trees that writes `setPanic`, `setBoredomLevel`, `setUnhappynessLevel` and `setPanicReductionValue(0.0)`; the live calorie write is `nutrition:setCalories` at `:84,86` — 2026-09-27. [C/snapshot]
30. `GirthsTweaks` sets `CharacterStat.FATIGUE` to zero and writes `CharacterStat.ENDURANCE` absolutely on the server from values stashed in modData, at `3745960616/mods/GirthsTweaks/42/media/lua/server/ST_MPSleep.lua:51,70,71` — 2026-09-27. [C/snapshot]
31. Vanilla's `server/XpSystem/XpUpdate.lua` removes and re-adds eight Strength and Fitness band traits on `Events.LevelPerk` (`:209-242`) and credits negative Strength and Fitness XP then calls `LoseLevel` on `EveryTenMinutes` (`:298-333`, `:294`), so the Strength level a clamp reads moves on that tier — 2026-09-27. [C/snapshot]
32. Vanilla stores its own XP-decay state (`strengthUpTimer`, `strengthMod`, `fitnessUpTimer`, `fitnessMod`) in **player** modData at `server/XpSystem/XpUpdate.lua:334-345` — 2026-09-27. [C/snapshot]
33. Vanilla ships a bus path that writes the body-weight slot server-side: `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:659` `sendClientCommand(getPlayer(), 'player', 'setWeight', args)` → `server/ClientCommands.lua:599,602` `otherPlayer:getNutrition():setWeight(args.weight)`, and the same panel adds and removes traits at `:594,669` — 2026-09-27. [C/snapshot]
34. `setAimingDelay` is called exactly once in vanilla's `media/lua`, at `shared/TimedActions/ISRackFirearm.lua:32`, additively on the existing value — 2026-09-27. [C/snapshot]
35. Vanilla reads `CharacterTrait.SHORT_SIGHTED` and `CharacterTrait.NIGHT_VISION` only in character-creation tables (`shared/Definitions/TraitClothingSelectionDefinitions.lua:101`, `shared/Items/SpawnItems.lua:233`), so a runtime grant of either adds no clothing and no item — 2026-09-27. [C/snapshot]
36. `ISDrinkFluidAction:updateEat` at `shared/TimedActions/ISDrinkFluidAction.lua:109` is the only place litres move in vanilla's drink path, reached from `update`, `animEvent` under `isServer()` and `complete`, and it calls `syncItemFields()` immediately after `DrinkFluid` — 2026-09-27. [C/snapshot]

## Not read

- **No mod was booted.** Every line is a read of a shipped file. Load order, which wrap ends up outermost, whether `QualityCooking`'s and the mod's eat wraps compose in practice, and whether `setPerkLevelDebug` fires `Events.LevelPerk` are all runtime questions this sweep cannot answer. The last is a jar question and belongs to [`pz-jar-research`](../../platform/jar-research.md).
- **Non-live version folders were excluded** except where a line says "all folders". `SomewhatTraitsCore`'s dead `42.12/` tree is named because its content is alarming, not because it runs; other mods' shadowed trees were not read.
- **`media/lua` only.** No mod's `media/scripts` was read for anything but surface 9, and no `.txt`, `.json`, translation file, tile definition or model was read at all.
- **The S8 module list is a floor**, not the module namespace: the first-literal rule misreads a call whose module is a variable. Proving `NutritionRevamp` and `NR` absent is unaffected; counting how many distinct modules exist is not answered.
- **The S9 collision census is scoped to `data/food-items.json`'s 1 005 item names and 61 fluid names**, not to all ~5 100 vanilla item definitions, so a mod redefining a vanilla non-food item other than `Bag_HydrationBackpack` would not appear. `Horse`'s `Base.Rope` is the known example.
- **`fluid` block merge semantics were not read** — the sweep counts blocks, and whether a partial `fluid` block merges per key on this build is the unread mechanism § 4.6 already flags.
- **`MoodlesUI`'s geometry surface was not read.** `getInstance()` and `wiggle()` are shown reachable; whether a position, size or slot getter is exposed to Lua is a separate jar or Lua read, and § 4.7's anchoring decision needs it.
- **The `Hook` table's own registration API was not read.** The sweep proves nobody registers `CalculateStats`; it does not show what `Hook.CalculateStats.Add` expects, which is § 4.1's jar question.
- **No `mod.info` `require=` or `loadModBefore=`/`loadModAfter=` graph was built**, so nothing here says which of two wraps wins on this server's actual `Mods=` line.
- **Nothing outside the installed tree.** The public Workshop nutrition overhauls, the ApocalipseBR sync fix and the third-party preservation patch are not installed and were not read here; they are [`compat-workshop-neighbours.md`](compat-workshop-neighbours.md)'s subject.
- **Counts drift.** The tree changed by 3 items and 4 folders in the seventeen days since the last inventory, and it will change again. Every number above is quoted with 2026-09-27; a recount is a new reading.
