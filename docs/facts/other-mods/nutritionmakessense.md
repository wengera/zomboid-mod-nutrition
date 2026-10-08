# Nutrition Makes Sense
Verified against 42.21.0 (4a0e9546ec) · 2026-10-08 · scope: what the Nutrition Makes Sense overhaul does on a dedicated server, what it reads and writes, its food pass against this repository's, and where it collides with a server mod that owns hunger, the calorie store and weight; the stat, packet and loader mechanisms it rides are handed off to their own pages.

## Key facts
<a id="techniques"></a>

- Leave an item's `HungerChange` alone and scale the hunger drop the eat applied instead, because the key is also the portion reservoir that gates partial eats and evolved-recipe ingredient use, by the mod's own account [#3518/C/snapshot].
- Let a field another mod is seen to change go: capture a baseline, write only while the field still holds your own last write, and stop for good once it does not [#3524/C/snapshot].
- Infer intake from the store rather than hooking the eat only when the mod needs no nutrient detail: a calorie rise is a meal of unknown content, and every other writer's rise is booked as one too [#3517/C/snapshot].

## How it works

<a id="what-it-does"></a>
### What it does

Nutrition Makes Sense replaces vanilla's hunger, energy and weight model with its own: an energy reserve band on the calorie store, the Well Fed timer read as a stomach, an appetite curve on hunger, and a malnutrition value that slows endurance regeneration and natural recovery.
Workshop item `3690404044` ships the mod id `NutritionMakesSense`, modversion 2.0.2 by Deharath, as a `42/mod.info` that sets `versionMin=42.14.0` beside its content under `common/`, so Build 42.21 finds it through that `mod.info` and loads it [#3513/C/snapshot].
Every Java member its per-player tick reads or writes is on the 42.21 jar, and it reaches each through a helper that returns nil for a missing member and calls the rest under `pcall` [#3514/C/C-only].
It keeps vanilla's own update running and corrects its results afterwards: it zeroes no rate and claims no stat hook (see [`#architecture`](#architecture)).

<a id="architecture"></a>
### The server tick and what it writes

On a dedicated server it registers one `EveryOneMinute` handler, installed from its `server/` entry file behind an `isServer()` test, that walks `getOnlinePlayers()` and for each player runs its model tick and then checks or sends a display snapshot; it registers its `OnPlayerUpdate` handler only where `isServer()` is false [#3515/C/snapshot].
Each tick it reads `HUNGER`, the calorie, macro and weight stores, the Well Fed timer and `ENDURANCE`, runs a pure-Lua model, writes back `HUNGER` through `stats:set`, calories and weight through the `Nutrition` setters and the Well Fed timer, each only when it moved more than 0.00001, and rescales `ENDURANCE` itself; it assigns no `ZomboidGlobals` field and registers no `Hook.CalculateStats` [#3516/C/snapshot].
The model is therefore a second writer on top of vanilla's, and what it does with a value it did not write decides every collision below.

It hooks no intake: a rise of the calorie store above 0.5 kcal since its own last write is booked as a meal, sized as the rise plus its running estimate of vanilla's burn over the step, and the fat and protein eaten are the rises in those two stores [#3517/C/snapshot].
It keeps 70 % of an eat's hunger drop by scaling the applied drop at its next tick and leaves the items' `HungerChange` alone, because, its own comment says, that key is also the portion reservoir that gates Eat Half and Eat Quarter and evolved-recipe ingredient use [#3518/C/snapshot].
A hunger value it did not write is taken when it fell by more than 0.0005, scaled to 70 % of the fall when the same tick booked a meal, or when it rose by more than 0.02 plus three times its ceiling on vanilla's own rise, `0.105 * (1 - hunger)` per hour; any smaller rise is overwritten by its own last write plus its own rate [#3519/C/snapshot].
It takes a weight it did not write only when the weight moved more than 0.2 kg since its own last write, and overwrites a smaller change [#3520/C/snapshot].
It scales the three natural-recovery `HealthAddition` fields from a captured baseline and stops writing a field once it sees another writer change it [#3524/C/snapshot].

Its persistent state is one table under the key `NutritionMakesSense2` in the player's modData, and it uses no global modData [#3521/C/snapshot].
That store is the shape the library warns against for server-owned state, because a client's transmit replaces the server's copy of the table ([#1085/M/n=2], [`../../platform/mp-model.md#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace)).
It wraps `ISEatFoodAction.complete` at `OnGameStart` and `OnServerStarted`, calls the original first, then forces a model tick and, on a server, calls `syncPlayerStats(player, -1)` [#3522/C/snapshot].
It sends each player a ten-key display snapshot through `sendServerCommand` when a value changed or ten seconds passed, checked at most every two seconds, and a client's snapshot request forces a model tick and a send with no server-side limit [#3523/C/snapshot].

<a id="food-pass"></a>
### The food pass

Its one food script restates 519 `module Base` item blocks of about 18.8 keys each, 517 of them naming a food of the 42.21 dataset's 722; compared only where the vanilla record carries the key, its `Calories` differ from vanilla's on 487 of those, its other three macros on 449 to 457 and its `HungerChange` on 82, and 10 more blocks set the four macros on a vanilla record that carries none of them [#3525/C/arith.].
438 of its item blocks name an item this repository's generated item pass also re-bases, and on those 438 its `Calories` over this pass's read a median of 1.14, within 20 % on 114 items and more than a factor of two apart on 139 [#3526/C/arith.].
Which of the two passes wins a key both set is decided by the stored script path, not by `Mods=` order ([#1055/M/n=2], [`../../platform/loader-and-scripts.md#sorted-replay`](../../platform/loader-and-scripts.md#sorted-replay)), and which way that falls for these two files is unread.

<a id="collisions"></a>
### How it collides

Nutrition Makes Sense cannot share a server with a mod that writes `HUNGER`, the calorie store and weight each minute and books any calorie rise as a missed intake: each reads the other's calorie writes as meals, and its tick overwrites a hunger or weight write it did not make unless the change crosses its own thresholds [#3527/C/inference].
Against a mod that zeroes vanilla's hunger rate, its own rate still runs, because it never reads the rate it would be zeroed through [#3516/C/snapshot, #3519/C/snapshot].
Both mods would also re-base 438 of the same foods, with calorie values that disagree by more than a factor of two on 139 of them [#3526/C/arith.].

<a id="hitching"></a>
### Server cost

An estimate from the code, unmeasured: its minute handler makes about 25 to 35 protected Java calls and one small Lua model step per online player, every player in the one minute frame, and its snapshot sends are not staggered [#3529/C/inference].
Each of those sends serialises its table on the main thread once per receiver ([#3437/C/C-only], [`../../platform/performance.md#budget`](../../platform/performance.md#budget)).

## Walls and bounds

Every line on this page is a reading of the installed copy's code on 2026-10-08, and nothing here was booted; the Workshop copy drifts, so its line cites drift [#3513/C/snapshot].
The food-pass counts come from an uncommitted scratch script over the installed script and the 42.21 food dataset [#3525/C/arith.].

<a id="licence"></a>
### Licence

None of its 36 files carries a licence, permission or credits text, and its `mod.info` names the author only [#3528/C/snapshot].
With no grant the default is all rights reserved: copying its code, art or strings into another mod needs the author's permission.

Not covered: its client UI (the tooltip rows, the health-panel lines, the Nutrition window, the moodle and the weight trend) beyond a grep for writes; its single-player path; its recipe overrides and the split-recipe `OnCreate` that rescales cut outputs; the Workshop page and its terms; and any live reading of the two mods together.

## Open
<a id="open"></a>

- Which of the two item passes wins the 438 shared foods [#3526/C/arith.] on a server loading both — settled by a co-boot reading one shared food's `Calories` on the server; no `X` id.
- Whether its malnutrition value survives a reconnect, given its player-modData store — settled by a session that plants a value, reconnects the client and reads the server's table; no `X` id.

## See also

- [`../../platform/mp-model.md#player-moddata`](../../platform/mp-model.md#player-moddata) — when a player's modData crosses sides, the store this mod keeps its state in.
- [`../../platform/loader-and-scripts.md#sorted-replay`](../../platform/loader-and-scripts.md#sorted-replay) — the replay that decides a key two item passes both set.
- [`../../areas/item-pass.md`](../../areas/item-pass.md) — this repository's own item pass, the other side of the shared foods.
- [`catalog.md#status`](catalog.md#status) — the Workshop page reading and the code-read status of this and the other neighbours.
