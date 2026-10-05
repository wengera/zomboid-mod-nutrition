# QualityCooking's eat wrap — the end-to-end code read (X45b gate)

> Plan 2, Task 1. A read-only, line-by-line read of QualityCooking's eat path, for the composition ruling Task 8 quotes and the X45b facts. Deleted at the plan close once its claims are minted (CLAUDE.md § 6). Tree read, read-only, this session (2026-10-05): `D:/SteamLibrary/steamapps/workshop/content/108600/3624538051/mods/QualityCooking/42/media/lua/` (QualityCooking) and `.../mods/QuestSystem/42/media/lua/` (QuestSystem, which holds `PersistentData`). Build 42.20.4 (b0bbce05d5); workshop item `3624538051`.

All pointers below are `lua:<path>:<lines>` with the path relative to the mod's `42/` root, in the form the register uses (`lua:media/lua/...`). The file read sits in QualityCooking's tree except `PersistentData.lua`, which is QuestSystem's (named per pointer).

## 1. What was read

| File | Mod | Role |
|---|---|---|
| `server/EventHandlers/CookingRollHandler.lua` | QualityCooking | the two eat wraps, `eatWithBuff`, `RollHandler.ApplyBuff`, and the two craft wraps |
| `shared/Utilities/CookingBuffMath.lua` | QualityCooking | `BuffMath.Macros`, `BuffMath.Allocate`, the buff describers |
| `shared/Utilities/QualityCookingData.lua` | QualityCooking | `Data.SetBuff`/`GetBuff`/`GetTier`/`Stamp`; the three mod-data keys |
| `server/EventHandlers/CookingBuffTicker.lua` | QualityCooking | the `EveryOneMinute` ticker that reads the buff and drives endurance/fatigue/hunger/carry-weight |
| `shared/QualityCookingInit.lua` | QualityCooking | the namespace and three custom events |
| `shared/Utilities/QualityCookingConfig.lua` | QualityCooking | `Config.IsEnabled`, the buff table, the sandbox multipliers |
| `shared/Utilities/PersistentData.lua` | QuestSystem | the global-modData store the buff rides |
| `mod.info` | QualityCooking | `require=\ItemQuality,\QuestSystem,\MoodleFramework` |

## 2. The eat wrap's shape — save-and-replace, no sentinel, saved original called inside each handler

`CookingRollHandler.lua` saves and replaces two methods on `ISEatFoodAction`, each unconditionally (no test for an already-installed wrapper, no sentinel flag on the action class or anywhere else):

- `local originalEatComplete = ISEatFoodAction.complete` then `function ISEatFoodAction:complete() return eatWithBuff(self, self.percentage, function() return originalEatComplete(self) end) end` — `lua:media/lua/server/EventHandlers/CookingRollHandler.lua:172-176`.
- `local originalEat = ISEatFoodAction.eat` then `function ISEatFoodAction:eat(food, percentage) ... return eatWithBuff(self, self.percentage * progress, function() return originalEat(self, food, percentage) end) end` — `lua:media/lua/server/EventHandlers/CookingRollHandler.lua:178-184`.

The saved original is passed into `eatWithBuff` as the `callOriginal` closure and **is always invoked**: every path through `eatWithBuff` ends in `callOriginal()` (`lua:media/lua/server/EventHandlers/CookingRollHandler.lua:142-170`) — the early-return guards (`not Config.IsEnabled()`, no food/player, not a `Food` instance, no tier points, or a `BlockedReason`) all `return callOriginal()` (lines 146, 154), and the main path binds `local result = callOriginal()` (line 165) and returns it (line 169). So QualityCooking's wrap never swallows the eat; it only decorates it.

(The same file also save-and-replaces `ISHandcraftAction.performRecipe` at `:57-87` and `ISAddItemInRecipe.complete` at `:89-105`, each with no sentinel and each calling its saved original — the craft-stamp path, out of this task's eat scope but the same idiom.)

## 3. `eatWithBuff` reads the eaten macros BEFORE the original and applies the buff AFTER

`eatWithBuff(action, requested, callOriginal)` (`lua:media/lua/server/EventHandlers/CookingRollHandler.lua:142-170`):

1. derives the eaten fraction via `effectiveFraction` (`:113-123`, rescaling the requested fraction by `getBaseHunger()/getHungChange()` — the same share-eaten logic the mod's own engine computes);
2. reads the eaten macros **before** the original runs: `local eaten = BuffMath.Macros(food, fraction)` (line 158), where `BuffMath.Macros` returns `{proteins, carbohydrates, lipids, calories}` each multiplied by the fraction off the live item's getters (`lua:media/lua/shared/Utilities/CookingBuffMath.lua:8-15`);
3. allocates buff points from those macros (`BuffMath.Allocate`, line 159);
4. calls the saved original: `local result = callOriginal()` (line 165) — this is where vanilla `Eat` consumes the item;
5. **after** the original, applies the buff: `if BuffMath.HasPoints(points) then RollHandler.ApplyBuff(player, food, tier, points) end` (lines 166-168);
6. returns `result`.

So QualityCooking reads the pre-`Eat` item (its full macros scaled by the eaten fraction) before vanilla touches it, then applies its effect after — exactly the seat the mod's own eat wrapper wants. This is the central composition fact: both wrappers read the item before their shared saved original runs, so both see the same pre-`Eat` macros regardless of order.

## 4. The per-eat observable effect — a time-limited buff record in QuestSystem's global modData

`RollHandler.ApplyBuff(player, food, tier, points)` (`lua:media/lua/server/EventHandlers/CookingRollHandler.lua:125-140`) builds a record `{tier, dish, points, appliedAt, expiresAt, weightBase}` and calls `Data.SetBuff(player, record)` (line 136).

`Data.SetBuff` writes it to QuestSystem's persistent store under the key `cookingBuff`:
`function Data.SetBuff(player, record) PersistentData.Set(player, Data.BUFF_KEY, record) end` with `Data.BUFF_KEY = "cookingBuff"` — `lua:media/lua/shared/Utilities/QualityCookingData.lua:13,37-43`.

`PersistentData` is `QuestSystem.PersistentData`, a **global-modData** store, not item modData: `GlobalDataCache = ModData.getOrCreate("QuestSystemPersistent")` and the record lands under `globalData.players[steamId][key]`, keyed by steam id with a username/`"singleplayer"` fallback — `lua:media/lua/shared/Utilities/PersistentData.lua:5,26-30,34-45,219-235` (QuestSystem's tree). On a dedicated server `PersistentData.Set` runs the authoritative branch (server-side write + dirty-key sync to the client), and the whole eat path is server-side (`ApplyBuff` runs inside the server-side `complete`/`eat` wrap).

The buff is **consumed** by `CookingBuffTicker.lua` (`Events.EveryOneMinute`, server-only): `tickPlayer` reads `Data.GetBuff(player)`, expires it past `expiresAt`, reconciles carry weight (`player:setMaxWeightBase`), and runs per-buff `Effects` that `stats:add(CharacterStat.ENDURANCE | FATIGUE | HUNGER, ...)` scaled by `ZomboidGlobals.ImobileEnduranceIncrease`/`FatigueIncrease`/`HungerIncrease` — `lua:media/lua/server/EventHandlers/CookingBuffTicker.lua:21-115`. So QualityCooking's buff **writes `CharacterStat.HUNGER` every game-minute while active** (its `satiated` buff, from `lipids`): a hunger-rate interaction the mod must expect when it owns hunger. (It is gated: `Effects.hungerRate` no-ops while the `FOOD_EATEN` moodle is up — `:37-41`.)

### What rides item modData instead

Only the cooking **tier** and **chef** ride item modData, under named keys: `Data.TIER_KEY = "QualityCookingTier"`, `Data.CHEF_KEY = "QualityCookingChef"`, written by `Data.Stamp(item, tier, chef)` as `item:getModData()[Data.TIER_KEY] = tier.id` / `[Data.CHEF_KEY] = chef` — `lua:media/lua/shared/Utilities/QualityCookingData.lua:11-12,31-35`. These are the two item-modData keys a mod's per-instance modData census on a QualityCooking-cooked food would see; the buff itself is **not** on the item.

## 5. Config gate and requirements

- **Config gate:** every QualityCooking write is gated on `Config.IsEnabled()`, which reads `SandboxSettings.get("QualityCooking", "Enabled", true)` — `lua:media/lua/shared/Utilities/QualityCookingConfig.lua:30-32`. `eatWithBuff` returns the bare original when disabled (`:145-147`); the ticker no-ops when disabled (`CookingBuffTicker.lua:103`). Debug logging is behind `Config.Debug` (default `false`, `QualityCookingConfig.lua:13,16-18`).
- **Requirements:** `mod.info` declares `require=\ItemQuality,\QuestSystem,\MoodleFramework`. The tier roll (`ItemQuality.Roller`), the persistent store (`QuestSystem.PersistentData`) and the moodle library are all hard dependencies, so QualityCooking cannot boot without them — any co-boot test (X45a/X45b) must carry ItemQuality + QuestSystem + MoodleFramework beside it.

## 6. The composition reading — two save-and-replace wraps of one method

Two save-and-replace wraps of the same method **compose**: each captures whatever is currently bound to `ISEatFoodAction.complete`/`:eat` at its own load time into a local, then replaces the method with a handler that calls that captured upvalue. If mod A loads first and mod B loads second, B's local captures A's wrapper, so B's handler calls A's handler, which calls vanilla. The **outermost** wrapper (the one the engine invokes first on an eat) is therefore **whichever `server/` file runs last in load order**.

Across two different mods, that order is the **mod load order** (`Mods=` order, as modified by `loadModBefore`/`loadModAfter`), not a within-mod script-path sort: the stored-path replay rule orders *scripts within the load*, not Lua files across mods. So which of NutritionRevamp's wrapper (`NR_Server_Intake.lua`) and QualityCooking's (`CookingRollHandler.lua`) is outermost is **load-order-dependent** and cannot be read from the code alone — **X45b (#2095) measures it live** (`TKX_EatProbe`'s `.outermost` on one eat).

Two further facts the read settles, order-independent:

- **Both wrappers read the pre-`Eat` item regardless of order.** Each reads the item's macros *before* calling its saved original (QualityCooking at line 158; the mod's wrapper by the same design), and the saved original is the only thing that mutates the item. So whichever is outer, the inner one's saved-original call is still the first consume, and both reads precede it. The mod reads the item strictly before QualityCooking's handler only when the mod loads after QualityCooking (mod outer → mod's read runs first); but either way both see the un-consumed macros.
- **QualityCooking writes to different stores than the mod's intake**, so there is no write collision on the eat itself: QualityCooking writes a buff record to QuestSystem global modData (`cookingBuff`) and tier/chef to item modData; the mod writes its meal vector to its own player record's stomach. The only runtime overlap is the ticker's per-minute `CharacterStat.HUNGER` add (§ 4), which lives on the stat clock, not the eat.

## 7. The one rule a sentinel-guarded wrapper beside a sentinel-free one must obey

QualityCooking has **no** idempotency sentinel; the mod's own eat wrapper does (it tests for its own wrapper before replacing, per the plan's Global Constraints). A sentinel-guarded wrapper installed beside QualityCooking's sentinel-free one composes **only if it saves the current method and calls that saved original on every path that does not deliberately skip the eat.** If the mod's wrapper ever returned without calling its saved original (e.g. an early-return guard that forgets `callOriginal`), and the mod is outermost, QualityCooking's handler below it would never run and its buff would silently stop applying. The mod must therefore:

1. save `ISEatFoodAction.complete` (and `:serverStop`) into its own local before replacing;
2. install idempotently — test its own sentinel global (one per wrapper, outside `NutritionRevamp`, which a reload re-creates) before replacing, so a Lua reload does not wrap the wrapper;
3. **call the saved original on every return path**, including every guard and the `pcall`-caught failure path (the capture is wrapped in `pcall`, never the original), so QualityCooking's chain below always runs.

This is exactly the save-and-call-original idempotency the plan's ruling 6 and the Task 8 brief require; the code read confirms QualityCooking holds up its end (it always calls its saved original), so the composition rests entirely on the mod keeping its own wrapper save-and-call-original.

## 8. Ruling (for the Task 8 brief)

The mod's eat wrapper saves `ISEatFoodAction.complete`, tests for its own wrapper before replacing it, and calls the saved original on every path, so it composes with QualityCooking's sentinel-free save-and-replace of the same method; the outermost wrap is whichever `server/` file loads last (load-order-dependent across mods — X45b measures it live), and both wraps read the pre-`Eat` item regardless because each calls the saved original after its own read. QualityCooking's per-eat effect is a time-limited buff record written to QuestSystem's global modData under `cookingBuff` (scaled by the eaten macros, applied after the original), with only the cooking tier and chef on item modData; its only runtime hunger interaction is the per-minute `CharacterStat.HUNGER` write from its buff ticker.
