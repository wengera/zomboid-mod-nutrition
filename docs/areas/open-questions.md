# Open questions
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: every open row in the register, the decisions the area pages leave to the design, and one subsection per surviving named experiment; the experiment specs stay in `reference/experiments.md`

## Index
<a id="index"></a>

One line per `open` row in the register, whichever page owns it, in id order.
The owner cell links the section that states the row; the X cell names the experiment that settles it, or a dash where no experiment does.

| id | question | owner | X | settled by |
|---|---|---|---|---|
| [#0139/M/n=1/open] | Whether a client-local flip of the sandbox `Nutrition` option halts the server-side drain is unsettled: the flipped window accounted for 41.4 per cent of its game-time against 99.0 per cent in the control, with two server reads 1.7 s apart identical to six decimals. | [open-questions.md](#x17) | X17 | a runtime flip of the option through its config setter, read against a no-flip control |
| [#0140/C/C-only/open] | Whether the Lua `SandboxVars` mirror is also stale after an admin-panel push is unmeasured. | [open-questions.md](#x17) | X17 | reading the Lua mirror beside the Java option after an admin-panel push |
| [#0141/M/n=2/open] | Whether a timed action's `maxTime` tick budget scales with `settimespeed` is unmeasured: the observed 42 or more ticks per wall second is consistent with a per-frame budget rather than a game-clock interval. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | one queued eat at a raised time speed against the pair taken at normal speed |
| [#0142/C/open] | How far weight and hunger drift apart on a part-eaten custom-weight item, and whether the `f0` write is intentional, is unmeasured. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | eating a canned food a quarter at a time and logging its weight, `hungChange` and `baseHunger` at each step |
| [#0143/C/open] | Which items ever set `baseHunger` different from `hungChange` at spawn is unknown: every path found initialises them equal, and `Food.copyNutritionFromRatio`, `IsoAnimal.modifyMeat`, `RecipeCodeOnCreate.makeCoffee` and `ItemStatsPacket.applyItemStats` write `baseHunger` separately and were not read. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | reading the two writers still unread, `RecipeCodeOnCreate.makeCoffee` and `ItemStatsPacket.applyItemStats` |
| [#0145/C/snapshot/open] | The client-to-server direction of `EatFoodPacket` is latent: `GameClient.eatFood` has no callers, and a mod could call it. | [mp-model.md](../platform/mp-model.md#open) | — | calling the game client's eat-food method from a mod and reading both sides |
| [#0146/C/open] | `getHealthFromFoodTimeByHunger()` was not dumped; it scales the food-to-health loop rather than intake. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | a jar dump of the method |
| [#0147/C/open] | No vanilla item was checked for `DaysFresh` equal to `DaysTotallyRotten`, the shape that makes the rot-roll denominator take the 100 per cent branch. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | scanning the food script for that pair of keys |
| [#0190/C/snapshot/open] | `Nutrition.caloriesMax` and `caloriesMin` are maintained but no reader was found for either. | [nutrition-core.md](../facts/nutrition-core.md#open) | — | a fresh jar-wide reader scan of both fields, with the exposer dump beside it |
| [#0191/M/n=1/open] | What the server validates on an incoming nutrition write is unmeasured: the probes show a client write being overwritten by the next push rather than rejected, which is a different mechanism from validation. | [mp-model.md](../platform/mp-model.md#open) | — | a probe that separates rejection from overwrite |
| [#0251/M/uncommitted/open] | The thaw rate does not reproduce: one run measured 47.25 per cent of `freezingTime` per game hour and a second run of the same script measured 67.8 per cent, against the code's 66.7 per cent at a thaw time of 1.5 hours. | [spoilage.md](../facts/spoilage.md#open) | — | a third run of the same phase at the same time speed and in the same container, its artifact committed |
| [#0371/M/n=1/open] | The measured age gain over one accelerated game day is 1.00777 against 1.02320 predicted over the containing window of 24.556793 game hours at rot speed 3, and the 1.5 per cent shortfall is unexplained. | [spoilage.md](../facts/spoilage.md#open) | — | a run that brackets the item's own aging window rather than the wait loop's clock samples |
| [#0372/M/n=1/open] | Only `cookingTime` has been seen to carry over between packets; the other nineteen conditionally-written fields are read off the write and parse guard lists and have never been made to differ in a run. | [wire-packets.md](../facts/wire-packets.md#open) | — | syncing an item with a distinctive cooking time and then a zero-valued item |
| [#0373/C/C-only/open] | The fridge and freezer container multipliers are unmeasured: they need a placed powered appliance whose container type is fridge or freezer on a square with electricity, which the fixture world does not provide at the spawn point. | [spoilage.md](../facts/spoilage.md#open) | — | a run that sets a container custom temperature, or that spawns a powered appliance |
| [#0374/C/C-only/open] | Whether food ages at all in single-player at default settings is unsettled: the code gates the aging call on the server flag, returns from the rot path on clients and otherwise needs `ReplaceOnRotten` or a non-negative removal day count, leaving only the compost update and the grab-world-item path. | [spoilage.md](../facts/spoilage.md#open) | — | a single-player measurement, which a dedicated-server harness cannot give |
| [#0375/C/C-only/open] | The syncing form of the aging call has only two callers, the `ReplaceOnRotten` branch of the rot path and the compost update, so on a dedicated server the rate-limited stats send on a rot transition effectively never fires for ordinary food. | [spoilage.md](../facts/spoilage.md#open) | — | a live server log across a rot transition |
| [#0376/C/C-only/open] | How often a multiplayer server re-sends inventory items, and therefore how often a client's freshness display refreshes, was not traced. | [mp-model.md](../platform/mp-model.md#open) | — | tracing the cadence of the item-list receiver |
| [#0377/C/C-only/open] | Whether the item-stats packet really carries `cooked` is unsettled: the field is in the list but both sides already read false when they were read, so the match is uninformative. | [wire-packets.md](../facts/wire-packets.md#open) | — | one divergence test, setting `cooked` on the server only and reading the client |
| [#0378/C/C-only/open] | The translation labels of the fridge-factor and rot-speed enums were not read, so only the numeric mapping decoded from the raw tableswitch is established. | [spoilage.md](../facts/spoilage.md#open) | — | reading the sandbox translation files |
| [#0379/C/C-only/open] | `Food.rottenTime` has a getter, a setter and save and load support, no script key, one writer in the compost update and zero readers, and `Poison` and `UseForPoison` parse into fields with no Java or vanilla-Lua reader, so all three look like mod-facing API rather than mechanics. | [food-item-model.md](../facts/food-item-model.md#open) | — | a reader scan that reaches outside the jar and the vanilla Lua tree |
| [#0380/C/C-only/open] | No reader for `AddIngredientIfCooked`, which 37 recipe blocks use, was traced beyond the ingredient-usability check. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | — | dumping the key's readers from the jar |
| [#0381/C/C-only/open] | `EvolvedRecipe.useSpice` and its two overloads were never dumped, so the spice branch's effect beyond the herbal-tea sums is unread. | [open-questions.md](#x9b) | X9b | a jar dump of both `useSpice` overloads and the ingredient usability check |
| [#0384/C/C-only/open] | The behaviour of an item whose fresh and rotten thresholds are equal is unmeasured at eat time, where it takes the hundred-per-cent branch of the rot-sickness denominator. | [spoilage.md](../facts/spoilage.md#open) | — | eating `Base.RatKing` on a live server and reading the sickness roll |
| [#0591/M/n=1/open] | The walking, running and sprinting burn constants are unmeasured: the run's server saw the moving flag in 5 of 52 samples, one consecutive pair, and never saw the running flag, so the run flag did not reach the server's copy of the character on the walk-to plus set-running route. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | the walk, run and sprint burn ratios; running never reaches the server (#2877) |
| [#0592/M/n=1/open] | The asleep burn branch is unmeasured: the sleep write held on the immediate read-back but did not persist, and the next row's 52 server samples all read the character awake with idle-rate burn about 27 s later, so whether the sleep was walked off or never persisted is undetermined. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | a sleep arm that verifies the state on the server before the window opens |
| [#0593/C/C-only/open] | Whether the 1.2 running thirst factor ever fires on a dedicated server is unknown: it is gated on the character being the local player instance, which on a headless server is probably never true, so running may not raise thirst in multiplayer at all. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | the same running branch the burn constants need |
| [#0594/C/C-only/open] | The real range of the thermoregulator's energy multiplier is unknown: the primary and secondary totals are written by updateNodes from a loop that was not traced, so the size of the cold-weather burn bonus is unbounded here. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | a temperature-controlled pair of idle windows |
| [#0596/C/C-only/open] | Whether split-screen players 2 to 4 accrue hunger or thirst locally is unverified: in single-player the wake-state and thirst updaters run only for the local player instance. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | a split-screen boot |
| [#0597/C/C-only/open] | The write order of applyWeightFromTraits is not exercised: its branches are sequential ifs, so a character carrying two weight traits - blocked in the UI, but reachable by a mod - would end at the last matching branch. | [body-and-weight.md](../facts/body-and-weight.md#open) | — | a probe that adds two band traits from Lua and reads the written weight back |
| [#0663/C/snapshot/open] | Whether the 16 unresolved `ReplaceOn*` targets should be resolved against a wider item scan is open: 15 are ordinary items outside the food and drink set and the sixteenth is the `Base.MugRed` defect. | [datasets.md](../reference/datasets.md#open) | — | resolving the targets against an item scan wider than the food and drink set |
| [#0664/C/snapshot/open] | Four fluid-only property shapes have no row in the 114-key table — `alcohol` in a fluid's `Properties` and the `Poison` block's `maxEffect`, `minAmount` and `diluteRatio` — while `fluReduction` and `painReduction` are not among them, being in the table and merely having no column. | [datasets.md](../reference/datasets.md#open) | — | giving the four shapes rows in the script-key reference |
| [#0665/C/snapshot/open] | A pick-random row's nutrition numbers are one draw and not an expectation over the pool, so anything that averages or worst-cases a spawn has to fan out through `fluid_ids` into the `fluids` records. | [datasets.md](../reference/datasets.md#open) | — | a decision on whether the dataset publishes an expectation over the pool |
| [#0672/C/C-only/open] | Fluid containers have no live census route: the script `Item` exposes no component accessor to Kahlua, so the 133 count is scanner-only and only fluid definitions can be read back. | [datasets.md](../reference/datasets.md#open) | — | a live read of an item's components, which the build does not expose |
| [#0674/C/C-only/open] | How the game picks a container's spawn fill between `InitialPercentMin` and `InitialPercentMax` is read but not measured, and whether the dataset should carry the two bounds as columns is open with it. | [datasets.md](../reference/datasets.md#open) | — | spawning several `Base.WineOpen` and reading each instance's fill against its range |
| [#0777/C/snapshot/open] | Whether the 202 `component CraftRecipe` entity build recipes belong in a third dataset, and whether any of them consumes food, is open. | [datasets.md](../reference/datasets.md#open) | — | scanning those blocks' `inputs` against the food dataset |
| [#0778/C/C-only/open] | Reaching `ItemUser.UseItem`'s removal branch needs a real `ISHandcraftAction` craft rather than an item command, so everything the dataset says about a `mode:destroy` line annihilating the rest of an item is still open to measurement. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | X31 | a live craft on the harness craft command |
| [#0779/C/snapshot/open] | The 33 drying recipes write a `variable` range on both sides while a separate jar reading puts `isVariableAmount` as never firing in vanilla and pins the variable input ratio at 1.0; both cannot be right, and one live craft probe reading the input count and the input's amount and maximum amount would settle it. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | — | one live craft probe reading the input count and the input's amount and maximum amount |
| [#0780/C/open] | The rotten branch of the evolved summation is not computed per row, and a mod that cares about cooking with rotten stock needs it plus the instance's rotten flag, which is not script data. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | — | computing the rotten arm per row and reading the rotten flag off the instance |
| [#0781/C/snapshot/open] | `data/food-items.json` carries no `UseDelta` column, so the drainable charging rule is unconditional where the jar's own test is drainable and `UseDelta` below 1; both vanilla drainable inputs are cigarette packs with null macros, but a modded drainable food input with real macros would be weighed at 0 with only the note saying why. | [datasets.md](../reference/datasets.md#open) | — | a `UseDelta` column the charging rule can test |
| [#0782/C/n=1/open] | A second partial-use row would widen the measured base of the per-use rule, which rests on `Base.Icecream` alone; `Base.Salt` at 1 of 10 uses is a two-minute probe on the existing command. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | — | `Base.Salt` at 1 of 10 uses on the existing command |
| [#0783/C/snapshot/open] | Whether the scanner should widen the output-mapper rule to take a `default` as a type is open: with one vanilla case today, a mod shipping a mapper with only a `default` would have its outputs silently resolve to nothing. | [tools.md](../reference/tools.md#open) | — | scanning a mod that ships such a mapper and reading what `meta.outputMapperIssues` records |
| [#0784/C/snapshot/open] | What the `OnCreate` hooks of the 37 output-less recipes do to nutrition, if anything, is unread: the dataset records the hook name and refuses the delta. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | X31 | executing one of the hooks on the game's own craft path |
| [#0785/C/C-only/open] | The five parse-time `EvolvedRecipe` aliases were never live-checked, and one probe settles them: on the aliased reading `RicePot` resolves to nothing as a recipe name while the four `Rice`-templated recipes must list the items whose keys are written `RicePot` or `RicePan`. | [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open) | — | one probe reading whether `RicePot` resolves as a recipe name and what the `Rice`-templated recipes list |
| [#0823/C/C-only/open] | Whether a folder carrying only `common/mod.info` resolves under the requested-id lookup is un-run as a purpose-built probe: the folder both boots used carried both files, and one boot closes it. | [open-questions.md](#x21) | X21 | a purpose-built folder carrying only `common/mod.info`, gated on the server and read on both sides |
| [#0835/M/n=2/open] | Whether a version dir that ships `media/` colliding with nothing loads, and whether a shadowed `common/` file is then inert, is un-run: both measured arms had either a collision or an empty version dir. | [open-questions.md](#x22) | X22 | a mod whose version dir ships a colliding and a non-colliding file, with a sentinel only the shadowed `common/` copy can set |
| [#0856/M/n=1/open] | What maps a mod's `server/` tree into the client's Lua state is unread: the outcome is measured at one session and the loader step that does it has not been traced, so a `server/` file printing its side at file scope on both sides is the probe that would settle it. | [open-questions.md](#x18) | X18 | one mod writing a distinct global from each of its `client`, `server` and `shared` files, read on both sides |
| [#0877/C/C-only/open] | Everything measured about the `mod.info` chain, the version dirs and the folder name was measured on the dedicated-server path: the client's own mod-list call site, which reaches `getModDetails` from the selector rather than from `loadMods`, was never exercised, and a client-side boot with a drifted folder has not been run. | [mod-anatomy.md](../platform/mod-anatomy.md#open) | X21 | booting the folder probe and reading the selector's own resolution |
| [#0882/C/C-only/open] | Whether `loadModAfter=` and `loadModBefore=` reach a dedicated server at all is unsettled: the jar and the vanilla Lua tree say they do not, and nothing has booted a pair of mods that disagree about order. | [mod-anatomy.md](../platform/mod-anatomy.md#open) | — | booting a pair of mods that disagree about order and reading the loader's `loading` lines |
| [#0883/C/C-only/open] | What a duplicate id across two mod roots does in practice is unsettled: the earlier-folder tie-break is a code reading only, and the id-to-dir map's put-if-absent and the mod map's replacement can in principle disagree about which folder a given id ends up pointing at. | [mod-anatomy.md](../platform/mod-anatomy.md#open) | — | installing one id in two roots and reading which folder the loader walks |
| [#0885/M/n=1/open] | Whether item modData moves from server to client is un-run: the player-modData directions were measured and the item-modData direction across the same hop was never exercised. | [open-questions.md](#x14) | X14 | a server-only key write, a client census that must miss it, a forced item push and a second census |
| [#0886/M/n=2/open] | Which string orders the script-body replay is unmeasured: a mod whose id sorts last while its script file sorts first has not been booted, and mod id, folder name, stored script path and `mod.info` display name all sort identically in every boot this library has run. | [open-questions.md](#x19) | X19 | four sort mods, each built to win under exactly one candidate key |
| [#0967/C/C-only/open] | The item-block creation hook has never been fired by any session in this library: it is read off the jar only, and it is the one hook that runs at instantiation, which is where a per-item nutrient field would most naturally be seeded. | [lua-platform.md](../platform/lua-platform.md#open) | X31 | a session that instantiates a modded item through the game's own craft path with the hook registered |
| [#0970/C/C-only/open] | Whether a mod-registered moodle type carries any Java effect is unmeasured: the registration methods exist and the type is Lua-exposed, but nothing in this library has registered one. | [open-questions.md](#x2) | X2 | a session that registers a moodle type and reads what its level drives, which the `X2` probe does not do |
| [#1040/M/one-side/open] | Whether item modData moves in the server-to-client direction through syncItemFields() is unmeasured. | [open-questions.md](#x14) | X14 | the writing mod's `server/` file guarded so only the server writes, then a forced sync and a census of both sides |
| [#1056/C/C-only/open] | Which string the replay sort orders, the mod id, the folder name, the stored script path or the mod.info display name, is unseparated by measurement, and the jar says the stored path. | [open-questions.md](#x19) | X19 | four sort mods, each built to win under exactly one candidate key |
| [#1062/C/C-only/open] | Whether the per-key merge survives a reloadlua or script reload is unread: LoadScripts's var5 is 0 on ScriptLoadMode.Reload, so on a reload the reset runs before the first body too, still a no-op for an item, but ResetOnceOnReload and PreReload take other paths this library did not read. | [loader-and-scripts.md](../platform/loader-and-scripts.md#open) | — | driving a reload in a running session and re-reading a merged item's keys |
| [#1063/C/C-only/open] | Whether the fresh net id Item.InitLoadPP allocates per appended body ever puts a stale id on the wire is unread. | [open-questions.md](#x27) | X27 | reading a multiply-redefined item's id on both sides, where agreement bounds the risk |
| [#1274/C/open] | Is `MoodleStat` reachable from Kahlua at all, given that C is a jar-proven absence? | [open-questions.md](#x2) | X2 | a global read of `MoodleStat` beside two exposed controls that must answer in the same call |
| [#1278/C/open] | What does the spice branch do beyond the herbal-tea sums? | [open-questions.md](#x9b) | X9b | a desk read of the spice method's two overloads and the ingredient usability check |
| [#1280/C/open] | Does item modData move server to client? | [open-questions.md](#x14) | X14 | a server-only key write, a client census that must miss it, a forced item push and a second census |
| [#1283/C/open] | Can Lua flip the `Nutrition` sandbox option at runtime, does it replicate, and does the drain stop? | [open-questions.md](#x17) | X17 | a harness route to the option's config setter and a session reading the Java option, the Lua mirror and the drain beside a no-flip control |
| [#1284/C/open] | What maps a mod's `server/` file into the MP client's Lua state? | [open-questions.md](#x18) | X18 | one mod writing a distinct global from each of its `client`, `server` and `shared` files, read on both sides |
| [#1285/C/open] | Which string is the replay sort key — id, folder name, stored script path, or display name? | [open-questions.md](#x19) | X19 | four sort mods, each built to win under exactly one candidate key |
| [#1286/C/open] | Do two mods at the same relative path both load — for a script file, and for a Lua file? | [open-questions.md](#x20) | X20 | two mods shipping the same relative script and Lua paths with different content, plus a boot with a mod file at a vanilla relative script path |
| [#1287/C/open] | Does a folder whose only `mod.info` is `common/mod.info` resolve, and does the client's mod-list call site agree with the dedicated server's? | [open-questions.md](#x21) | X21 | a mod carrying `common/mod.info` and nothing else, its verify gate on the server only, read on both sides |
| [#1288/C/open] | Does a version dir shipping `media/` that collides with nothing still load, and does a shadowed `common/` copy ever execute? | [open-questions.md](#x22) | X22 | a mod whose `common/` and version dir each ship a colliding and a non-colliding file, with a sentinel only the shadowed copy can set |
| [#1292/C/open] | Does CleanUI's `pcall(triggerEvent, …)` wrapper change what an unguarded raise does inside a dispatch? | [open-questions.md](#x26) | X26 | a harness entry into the context-menu builder and one session reading the wrapper's own failure line and the handlers behind the raise |
| [#1293/C/open] | Does `InitLoadPP`'s per-body net-id reallocation ever put a stale id on the wire? | [open-questions.md](#x27) | X27 | reading a multiply-redefined item's id and full type on both sides, where agreement bounds the risk |
| [#1296/C/open] | Does a file-scope `ZomboidGlobals.HungerIncrease` assignment from a mod actually change the drain? | [open-questions.md](#x30) | X30 | a file-scope and a game-start assignment read against the server's drain rate and the fixture's baseline rate |
| [#1297/C/open] | Does a dotted `OnCooked` name fire, on which side, and can the cooking pipeline be driven end to end at all? | [open-questions.md](#x31) | X31 | a cook-transition session with a dotted target, then a harness craft command that reaches a crafted instance |
| [#1299/C/open] | Does a cancelled eat of an item whose state-modified `abs(getHungerChange()*100)` is 1 or less really apply nothing at all? | [open-questions.md](#x33) | X33 | a completed eat, a cancelled eat of a normal item and a cancelled eat of an item driven under the guard |
| [#1348/C/inference/open] | Whether the two weight-direction flags Auto Cook's smart-spice gate reads can desync is unsettled; settling it needs a session that drives calories above 1000 or below 0 and re-reads both sides. | [wire-packets.md](../facts/wire-packets.md#open) | — | a session that drives calories above 1000 or below 0 and re-reads both sides |
| [#1375/C/C-only/open] | Which mod.info supplies a mod's id when the mod ships more than one is not settled; Auto Cook ships exactly one and cannot discriminate, so no id-read order may be stated on its strength. | [mod-anatomy.md](../platform/mod-anatomy.md#open) | X21 | a purpose-built folder whose only `mod.info` is `common/mod.info` |
| [#1422/C/C-only/open] | The call path from the character update through the recursive item updater to the item update carries no side guard, and the only guard on that path is an is-zombie test a player character fails, so why a client copy does not run it is unexplained for every field but cooking. | [mp-model.md](../platform/mp-model.md#open) | — | tracing what stops the item update on a client |
| [#1429/C/C-only/open] | Whether 42.20.4 ever loads a B41-layout item-name translation file stays open by design, because separating it from the no-entry case needs an item-name JSON added to a mod tree, which is a write under the read-only workshop folder. | [food-item-model.md](../facts/food-item-model.md#open) | — | repeating the pair inside a writable copy of the mod tree |
| [#1434/C/inference/open] | Whether a relog or a save round-trip repairs the client's copy of the four uncarried fields is not measured, and because the client's copy keeps the cookable flag true it could re-enter the cooking block on its own and call a nil hook, which neither session reproduced. | [wire-packets.md](../facts/wire-packets.md#open) | — | a relog read of a cooked item on both sides |
| [#1545/M/n=1/open] | Whether a resident mod's protected-call wrapper changes what an unguarded raise does on a client is open: the run that would have measured the nested shape lost every client reading, its client bus never answering, and on a debug client even a caught nested raise routes through the Kahlua failure path and parks the process. | [lua-platform.md](../platform/lua-platform.md#open) | X26 | one session that drives the interface mod's context-menu entry through a harness addition, reading that mod's own printed failure line and whether the handlers behind the raiser ran |
| [#1664/C/open] | Which `mod.info` the live id chain reads when a folder holds several is unsettled: the dead `searchForModInfo` body would take the first whose id matches in directory-listing order, and the live `loadMods` to `readModInfoAux` chain has not been read for that ordering. | [mod-anatomy.md](../platform/mod-anatomy.md#open) | X21 | the same purpose-built folder probe |
| [#1668/C/open] | Whether AutoCook's per-player cooking settings survive a relog on a dedicated server is unmeasured, and it is the cheapest multiplayer question the catalog raises. | [catalog.md](../facts/other-mods/catalog.md#open) | — | a profiled session that writes a setting, relogs the character and re-reads player modData on both sides |
| [#1671/C/open] | TryMeatCanned writes a chained comparison that parses as a boolean compared to a number, which standard Lua raises on; nothing calls it, so it has never run and whether Kahlua raises the same way is unverified. | [catalog.md](../facts/other-mods/catalog.md#open) | — | calling that function from the command bus |
| [#1770/C/C-only/open] | The harness mod ships two identical mod-info files, one at the mod root and one in the version folder, and which copy this build reads first when two exist is recorded as open by the harness's own layout note. | [harness.md](../platform/harness.md#open) | — | a boot that names each copy's own id in turn against a purpose-built folder |
| [#1815/M/n=1/open] | The one measurement of the event's own ceiling is 10.08 ticks per wall second, on the run that overran, and where the true ceiling sits between eight and 10.08 is unmeasured. | [harness.md](../platform/harness.md#walls) | — | scheduler self-tests that step the demand past the ceiling and read the fitted tick rate |
| [#1830/C/C-only/open] | Which sandbox options survive a restore is open: only the day length has been set by a profile on a restored world and measured to apply, and the other four keys the mod work cares about are unexercised. | [harness.md](../platform/harness.md#open) | — | a profiled run that sets each option on a restored world and reads it back |
| [#2045/M/one-side/open] | Timed actions are touched by rows but have no page: the eat and drink actions are read end to end and the multiplayer action manager's route into them is traced, while the action queue, its tick budget and how a mod adds an action of its own are unread. | [overview.md](../platform/overview.md#coverage) | — | a read of the action queue, its tick budget and the route by which a mod adds an action |
| [#2046/C/one-side/open] | The crafting pipeline is touched by rows but has no page: the craft-recipe grammar, what an input really costs and the output's inherited state are stated on the loader and cooking pages, while the crafting interface, the handcraft action and the recipe-discovery surface are unread. | [overview.md](../platform/overview.md#coverage) | — | a read of the crafting interface, the handcraft action and the recipe-discovery surface |
| [#2047/C/one-side/open] | Server admin and the remote console are touched by rows but have no page: the console's transport, the one admin command this library drove and the one that throws are stated on the overview, while the admin command set as a whole and what each does to a running world are unread. | [overview.md](../platform/overview.md#coverage) | — | a read of the admin command set against a running world |
| [#2048/C/one-side/open] | Build detection is touched by rows but has no page: the version keys and what the availability gate compares are stated on the anatomy page, while what a mod can detect about the running build from inside Lua is unread. | [overview.md](../platform/overview.md#coverage) | — | a read of what Lua can learn about the running build |
| [#2049/M/n=1/open] | Client-only mods are touched by rows but have no page: one workshop mod is torn down as a pure client-side viewer and a second as a client-only cooking helper, while the general cost of shipping one side only, and what still reaches the other side, is stated as anatomy rather than as a topic of its own. | [overview.md](../platform/overview.md#coverage) | — | a read of what a one-sided mod still reaches on the other side |
| [#2051/C/one-side/open] | The events roster is touched by rows but has no page: the events this library hooked and measured are stated on `platform/lua-platform.md` and `platform/harness.md`, while the full roster and which events fire on a dedicated server were never enumerated here. | [overview.md](../platform/overview.md#coverage) | — | enumerating the full events roster and which events fire on a dedicated server |
| [#2081/C/open] | Does a `CalculateStats` handler that reproduces the seven skipped updaters from the library's formulas track vanilla's stat trajectory, stat by stat, over several game-hours on a live server? | [open-questions.md](#x34) | X34 | two boots of one fixture, with no handler and with the reproducing handler, sampling the seven stats hourly against a per-stat band |
| [#2082/C/open] | Is a `CalculateStats` handler's endurance write the last before the player-stats push, as the tick order reads? | [open-questions.md](#x35) | X35 | a sentinel endurance written each tick and read in client-first pairs at rest and running, beside an arm with the handler removed |
| [#2083/C/open] | Does `Fitness.update` tick on the server for a connected player? | [open-questions.md](#x36) | X36 | a seeded exercise, then two game-days without one, reading the server's regularity for the predicted fall |
| [#2085/C/open] | What is the experience anti-cheat's check interval, and does a server-side burst of grants trip it? | [open-questions.md](#x40) | X40 | a desk read of what enables the check, then above- and below-bound server-side bursts, the lower sized off the bound the first trip logs, beside a console-grant control, timing the logged trips |
| [#2087/C/open] | Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value? | [open-questions.md](#x48) | X48 | melee hits with the protein store raised on the server alone and then on the client alone, reading the Strength experience per hit |
| [#2096/C/C-only/open] | Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold? | [open-questions.md](#x47) | X47 | a client write sampled in Lua every quarter second for four seconds, against the packet's cadence |
| [#2829/M/n=1/open] | Two drink corners are unmeasured, cancel semantics and the 100 ms anim-event cadence under `settimespeed`, and when the new fill and the new calories arrive on the client is read only to a poll of 1.5 to 2 s: the client trailed the server by about one poll and reached the same totals. | [eating-pipeline.md](../facts/eating-pipeline.md#open) | — | a drink cancelled partway and a drink at a raised time speed, each read on both sides |
| [#2946/M/n=1/open] | Whether the climate override moves an outdoor character's air and core, and whether a hot exposure with activity raises the fluids multiplier above 1, is unmeasured: the one run stood the character where the air read 22.0 under both overrides and walked it at 16 degrees. | [open-questions.md](#x51) | X51 | the climate override held over an outdoor character, idle and walking, reading the server's thermoregulator per tick |
| [#2960/C/C-only/open] | Whether a script `OnEat` given to `Base.PillsVitamins` by a mod's item block runs on the server when the pill is taken is unmeasured: the pill path calls the drainable's `OnEat`, as the jar reads, and run x151s-20261005-165844 took the pill with none assigned. | [open-questions.md](#x59) | X59 | a pill taken with a script `OnEat` assigned, counting its calls on both sides |
| [#2972/M/n=1/open] | Whether the mod's sweat term fires live is unmeasured: a 60 s walk took the server's `body.met` from 1.6 to 3.0 and never above the term's 3 MET floor, so `sweatLmin` stayed 0 and `sweatActive` false. | [open-questions.md](#x64) | X64 | a run or an activity the server classifies above 3 MET for game hours, reading the sweat fields |
| [#2992/M/n=1/open] | Whether an unbroken sleep resets the mod's hours awake live is unmeasured: under the harness's sleep hold `sleptH` read at most 0.3195 at the 35 reads, below the one-hour nap threshold, and `awakeH` never reset across the hold. | [open-questions.md](#x69) | X69 | a client-initiated sleep, or a hold that keeps every minute asleep for over an hour, reading `acute.awakeH` and `sleptH` |
| [#3045/M/n=1/open] | Whether halving the regeneration constants halves awake regeneration is unmeasured: run x161s-20261006-031534 wrote and read them back, but both windows ran at hunger moodle level 4, whose tier adds nothing. | [open-questions.md](#x80) | X80 | a damaged part read in two windows, before and after the halving, with the hunger, thirst and sickness moodles low enough that the regeneration tier is not 3 |
| [#3063/M/n=1/open] | Whether the post-shot sum, the per-update aiming step and a client write between shots behave as the jar reads while a player really aims is unmeasured: run x161p-20261006-035559's harness aim flag did not hold. | [open-questions.md](#x86) | X86 | an aim held by input with the delay below the aiming time, sampled per client tick across shots |
| [#3047/M/n=1/open] | What steady core offset a TEMPERATURE target written on every update holds is unmeasured: the probe had no per-tick writer, so run x161s-20261006-031534 read only one write. | [open-questions.md](#x81) | X81 | a per-tick writer of an absolute target for game hours, reading the server's core and set point |
| [#3129/M/n=1/open] | Whether the mod's cold fold scales a catchACold rise is unmeasured: run x161b-20261006-065751 held a climate override of -10 and a soaked character, the thermoregulator's catch-a-cold delta stayed under the 0.1 the accrual needs and catchACold read 0 at all 32 reads. | [open-questions.md](#x105) | X105 | an outdoor or wet-and-cold seat that lifts the delta over 0.1 for game hours, reading catchACold with the fold on and off |
| [#3136/C/open] | Whether a partial item block that omits `DisplayCategory` as well as `ItemType` still merges into a food is unmeasured: both blocks of run x171p-20261006-090743 kept `DisplayCategory = Food`. | [item-pass.md](item-pass.md#open) | — | the same partial block with both keys omitted, reading the base-module food count and the instance getters on both sides |
| [#3178/C/open] | Whether the server's 60 s checksum arm acts on a mismatched client is unmeasured: run x171c-20261006-091054 watched 157.806 s past the warning and saw no act, the client having force-disconnected 0.290 s after the anti-cheat line. | [item-pass.md](item-pass.md#open) | — | a mismatched client held connected past the 60 s grace, reading the server log for the timeout act |
| [#3244/M/n=2/open] | Whether the tooltip band lands on screen below the engine's box, above it at the bottom edge and clear of an anchored slot is unmeasured: the probe ran the band's entry function and the hover draw count read 0 on both boots. | [client-ui.md](../platform/client-ui.md#open) | — | a hover synthesiser reading the band's pixels or the element's draw calls |
| [#3245/M/n=1/open] | Whether a saved `visible=true` panel line restores the panel open is unmeasured: the fixture's layout file carried no line for the panel and the quit wrote `visible=false`. | [client-ui.md](../platform/client-ui.md#open) | — | a second boot on a user directory carrying the line |
| [#3246/M/n=1/open] | Whether the tab draws on screen, survives a tear-off through its wrap and fires the layout save's `current`-clearing branch is unmeasured: its render ran once through a method call without an error, a method call reaches no tear-off, and it was never the active tab at the quit. | [client-ui.md](../platform/client-ui.md#open) | — | a click synthesiser that activates the tab and tears it off before the quit |
| [#3248/M/n=1/open] | Whether a scrolled panel clips its rows at the window's edge is unmeasured: at the Bands level the rows fit and the wheel had nothing to scroll. | [client-ui.md](../platform/client-ui.md#open) | — | the wheel at the Numbers level, where the rows are expected to overflow, reading the rows' draw calls after a scroll |

## Decisions
<a id="decisions"></a>

One line per decision the area pages' `## Open` sections leave to the design, each with the fact that forces it and no recommendation; a decision two pages state is written once and links both.

- Which store holds each mod nutrient's authoritative value — forced by modData being the only durable mod state while any client's transmit replaces the server's copy of a player's table [#1122/C/C-only, #1151/M/n=2] ([new-nutrients.md#open](new-nutrients.md#open)).
- What range each mod nutrient store is held to, and whether it runs negative — forced by vanilla's clamps living inside the `Nutrition` setters that a parallel store never passes through, and by negative vanilla stores being an ordinary state [#0022/M/n=2, #0023/M/n=2, #0901/M/n=1] ([new-nutrients.md#open](new-nutrients.md#open)).
- Whether each mod nutrient decays, and on which clock — forced by vanilla's drain being compiled into the nutrition update and reaching no store but its own macro stores [#1193/C/C-only] ([new-nutrients.md#open](new-nutrients.md#open)).
- Whether a per-item mod value, a per-item nutrient among them, is a per-type script value, an entry in a per-type Lua table or per-instance state — forced by a script key agreeing on both sides for free while every instance takes a deep copy of it, by a `fluid` block storing no script key at all, and by item modData moving whole and its route being measured in one direction only [#1124/M/n=1, #2676/C/C-only, #2682/C/C-only, #1126/M/one-side, #1241/M/one-side] ([new-nutrients.md#open](new-nutrients.md#open), [mp-sync.md#open](mp-sync.md#open)).
- Whether a per-item nutrient must follow an item through a type change — forced by the replacement being built from its own script, with the swap naming the condition states and the age, and not item modData, as what it copies [#0266, #0243] ([new-nutrients.md#open](new-nutrients.md#open)).
- Whether any mod nutrient acts through vanilla's weight model or through a model of the mod's own — forced by the model's one switch taking the drain, the burn and the weight arm together, and by the Strength grant on the protein store being the one other vanilla consumer, with the carbohydrate store and diet quality dead space [#1136/C/C-only, #2112/C/C-only, #2696/C/inference] ([new-nutrients.md#open](new-nutrients.md#open)).
- Whether the item pass reaches foods other mods declare in their own modules or leaves them on upstream numbers — forced by a `module Base` pass not touching those foods and a block naming one being an override only while that mod loads [#1030/M/n=1, #1002] ([item-pass.md#open](item-pass.md#open)).
- Whether the item pass re-bases drinks per litre — forced by a drink's nutrition living on a fluid rather than on any key of the container's own block [#0626/C/snapshot, #0604/M/n=2] ([item-pass.md#open](item-pass.md#open)).
- Whether the item pass names `HungerChange` at all or re-bases the macros alone — forced by hunger driving weight, recipe cost, the portion menu and the cancel guard, where the macros move intake alone [#1214/C/C-only, #0701/M/n=3, #0036/M/one-fixture] ([item-pass.md#open](item-pass.md#open)).
- Which route carries each value the item pass changes — forced by a script block loading on both sides for free where a per-instance Lua write has to cross the wire [#1001/M/n=1] ([item-pass.md#open](item-pass.md#open)).
- Whether the intake correction sits in the completion wrapper, before `Eat` writes, or in the eat hook, after it — forced by only the wrapper seeing pre-intake values while the eat hook's store already holds the eat [#1033/M/n=1, #0008] ([eat-and-cook-hooks.md#open](eat-and-cook-hooks.md#open)).
- Whether the correction must also cover a cancelled eat — forced by a cancel reaching `Eat` through the server-stop step and never through the completion step [#0111] ([eat-and-cook-hooks.md#open](eat-and-cook-hooks.md#open)).
- Whether a cooked item's nutrition comes from a cook hook on the instance or from a replacement item's script — forced by the swap returning before the hook runs, and by a hook's item-field writes reaching the client only where the item packet carries them [#0266, #1036] ([eat-and-cook-hooks.md#open](eat-and-cook-hooks.md#open)).
- Whether the intake correction also wraps the world-source drink action — forced by a drink-action wrapper never seeing a drink from a world water source [#2690/C/C-only] ([eat-and-cook-hooks.md#open](eat-and-cook-hooks.md#open)).
- Which route each quantity this mod owns travels on — forced by the three routes failing three different ways: the transmit replaces a whole table on another mod's call, a script value is fixed per type at load and checksummed at the join, and the bus stores nothing [#1151/M/n=2, #1182/C/C-only, #1153/C/C-only] ([mp-sync.md#open](mp-sync.md#open)).
- Which values the client displays are derived on the client and which are sent from the server — forced by the band traits reaching the client only on server pushes, the experience push measured landing within about half a second [#2759/M/n=3], by the cooked-thirst halving, and by a derived value being right only while every input it reads is carried [#2595/C/C-only, #1038/M/n=2, #1508] ([mp-sync.md#open](mp-sync.md#open)).
- Whether the design leans on modData surviving a restart — settled: both scopes survived a clean quit and reload and a hard kill lost a minute-old global write, in run `x131p-20261004-192310` [#1294/M/n=1, #2097/M/n=1, #2098/M/n=1, #2758/M/n=1] ([mp-sync.md#open](mp-sync.md#open)).
- Whether item round trips are keyed on the item id before the net-id run lands — forced by the per-body reallocation being unread for an item several mods append to [#1063/C/C-only/open] ([mp-sync.md#open](mp-sync.md#open)).
- Whether the mod's numbers stay inside the display bands the torn-down viewer hard-codes — forced by those bands going wrong silently on a re-based scale [#1514, #1522] ([ui-and-moodles.md#open](ui-and-moodles.md#open)).
- Whether the server's 60 s checksum arm acts on a mismatched client, not seen in the 157.806 s watched [#3178/C/open], [#1231/C/C-only] ([item-pass.md#open](item-pass.md#open)).
- Which compatibility approach this mod takes toward each resident it shares a file or a key with — forced by the loader keeping one file per relative path and the replay deciding a contested key by the stored script path [#1173/C/C-only, #1183/M/n=2] ([packaging.md#open](packaging.md#open)).
- Whether a patch mod, if one ships, rides this mod's Workshop item as a second folder or an item of its own — forced by a server naming mods by id and resident items already shipping several mods each [#1219/C/C-only, #1543/C/snapshot] ([packaging.md#open](packaging.md#open)).
- Whether this mod ships beside a public fix for the multiplayer nutrition-sync problem on one server — forced by that fix working on the same problem this mod's own state routes answer, and blocked by the fix being uninstalled, so what it replaces, shadows or transmits is unread until someone subscribes to it and re-runs the inventory [#1605/W/snapshot, #1600] ([packaging.md#open](packaging.md#open)).
- Whether a block of this mod naming the preservation mod's foods can coexist with the third-party patch that claims that mod launders nutrition — blocked by the patch being uninstalled, and forced by a block naming another mod's food being an override only while that mod loads [#1606/W/snapshot, #1030/M/n=1, #1600] ([packaging.md#open](packaging.md#open)).
- Whether this mod is built to share a server with any public nutrition overhaul — blocked by none of the nutrition term's results being installed, and forced by `incompatible=` stopping nothing on a server [#1599/W/snapshot, #0813/C/C-only] ([packaging.md#open](packaging.md#open)).
- Whether the five Workshop neighbours' code (Nutrition Makes Sense 3690404044, StatsAPI 2997722072, Stat Tweaks Lib 3415375593, ApocalipseBR Nutrition Sync Fix 3736275816, Tooltiplib 3694097672) agrees with the stances the compatibility approaches rest on — deferred on 2026-10-06: not subscribed, so none is installed; settled by subscribing and reading each against its one question, and not an `X` row [#1599/W/snapshot, #0813/C/C-only] ([packaging.md#open](packaging.md#open)).
- At which pacing the mod's timed scenarios run — forced by the cadence ceiling binding the day length and the multiplier together while every baseline sits at the fixture's day length [#1814/M/n=3, #1253/C/one-fixture] ([testing-your-mod.md#open](testing-your-mod.md#open)).
- Whether the mod's load checks are verification rows or scenarios — forced by a verification expectation being a substring that cannot express absence or a numeric comparison [#1828] ([testing-your-mod.md#open](testing-your-mod.md#open)).
- Whether the mod ships a client-side scenario for its display copy — forced by the client runner being wired with nothing to run and by every client read of a live store being a staircase [#1784, #1483] ([testing-your-mod.md#open](testing-your-mod.md#open)).
- Whether any scenario moves a sandbox option off the fixture's value — forced by only the day length having been set by a profile, so a moved option buys a new baseline [#1809/C/C-only, #1253/C/one-fixture] ([testing-your-mod.md#open](testing-your-mod.md#open)).
- Whether a scenario pins the thirst clock or reads the death as its result — forced by an unattended thirst drain killing the subject partway through a multi-day run [#0179/M/one-fixture] ([testing-your-mod.md#open](testing-your-mod.md#open)).
- Whether the stats a diet moves are taken over or overlaid — forced by a takeover suppressing all seven updaters for every player, which no other mod can undo, while an overlay leaves vanilla's rates running [#2238/C/C-only, #2240/C/C-only] ([body-effects.md#open](body-effects.md#open)).
- Which store is the truth for a clamped Strength or Fitness — forced by the level and the experience being separate stores, each moved by a different vanilla writer [#2101/C/C-only, #2124/C/C-only] ([body-effects.md#open](body-effects.md#open)).
- How large a single server-side experience grant the mod issues — forced by a tripped anti-cheat check kicking or banning the player while its interval is unread [#2147/C/C-only, #2148/C/C-only] ([body-effects.md#open](body-effects.md#open)).
- Whether a warmth effect writes the temperature stat every update or accepts the single lerp step of one write — forced by one write moving the thermal core only one lerp step toward it [#2373/C/C-only] ([body-effects.md#open](body-effects.md#open)).
- Which distance input a sight effect goes through, the Short Sighted boolean or the detection range — forced by both reaching the native lighting, whose use of either is outside the bytecode [#2303/C/C-only] ([body-effects.md#open](body-effects.md#open)).
- Whether an activity-scaled quantity reads the metabolic-rate classes or classifies the player itself — forced by the classes being floors raised by endurance and load, none of it measured on a server [#2633/C/C-only, #2649/C/C-only] ([body-effects.md#open](body-effects.md#open)).

## Experiments

One subsection per surviving named experiment, in id order: the open rows this page owns under it, the open rows it settles on other pages, the area pages that wait on it, and a pointer to its full spec in [experiments.md](../reference/experiments.md), which this page never restates.

<a id="x2"></a>
### X2 — Is `MoodleStat` reachable from Kahlua at all?
- `MoodleStat` is absent from the classes the jar exposes, and whether it is reachable from Kahlua at all is unmeasured [#1274/C/open].
- Whether a mod-registered moodle type carries any Java effect is unmeasured: the registration methods exist and the type is Lua-exposed, but nothing in this library has registered one, and the reachability probe does not register one either [#0970/C/C-only/open].
- Waiting on it: [ui-and-moodles.md](ui-and-moodles.md#open).
- Settled by: a global read of `MoodleStat` beside two exposed controls that must answer in the same call, riding any session with a client — [experiments.md § Named experiments](../reference/experiments.md), row `X2`.

<a id="x5"></a>
### X5 — Does a mod JSON displace a vanilla translation key? (settled)
- Settled by run x182: a mod translation JSON displaces a vanilla interface key on the client [#3201/M/n=1]; see [experiments.md § Named experiments](../reference/experiments.md), row `X5`.

<a id="x9b"></a>
### X9b — What does the spice branch do beyond the herbal-tea sums?
- What the spice branch does beyond the herbal-tea sums is unread [#1278/C/open].
- `EvolvedRecipe.useSpice` and its two overloads have never been dumped, so the spice branch's effect beyond the herbal-tea sums is unread [#0381/C/C-only/open].
- Waiting on it: [eat-and-cook-hooks.md](eat-and-cook-hooks.md#open).
- Settled by: a desk read of both spice overloads and the ingredient usability check, with no boot — [experiments.md § Named experiments](../reference/experiments.md), row `X9b`.

<a id="x14"></a>
### X14 — Does item modData move server to client?
- Whether item modData moves server to client is open [#1280/C/open].
- The player-modData directions are measured and the item-modData direction across the same hop has never been exercised: in the one phase that read it, both sides already held the probe key and the server wrote nothing, so the phase graded a state and not a crossing [#0885/M/n=1/open].
- Whether item modData moves server to client through `syncItemFields()` is unmeasured, the one measured direction being client to server [#1040/M/one-side/open].
- Waiting on it: [new-nutrients.md](new-nutrients.md#open), [mp-sync.md](mp-sync.md#open).
- Settled by: a server-only key write, a client-first census that must miss it, a forced item push and a second census — [experiments.md § Named experiments](../reference/experiments.md), row `X14`.

<a id="x17"></a>
### X17 — Can Lua flip the `Nutrition` sandbox option at runtime, does it replicate, and does the drain stop?
- Whether Lua can flip the `Nutrition` sandbox option at runtime, whether the flip replicates and whether the drain stops is open [#1283/C/open].
- Whether a client-local flip of the option halts the server-side drain is unsettled: the flipped window accounted for 41.4 per cent of its game-time against 99.0 per cent in the control, with two server reads 1.7 s apart identical to six decimals, in one flipped window with no repeat and no `sendToServer` push [#0139/M/n=1/open].
- Whether the Lua `SandboxVars` mirror is also stale after an admin-panel push is unmeasured, and the code reading predicts it fresh on both sides, because the server and every connected client call `toLua()` when they apply the push ([#0140/C/C-only/open], [#2449/C/C-only], [sandbox-options.md#runtime-change](../platform/sandbox-options.md#runtime-change)).
- Waiting on it: [new-nutrients.md](new-nutrients.md#open).
- Settled by: a harness route to the option's config setter and one session reading the Java option, the Lua mirror and the drain beside a no-flip control — [experiments.md § Named experiments](../reference/experiments.md), row `X17`.

<a id="x18"></a>
### X18 — What maps a mod's `server/` file into the multiplayer client's Lua state?
- What maps a mod's `server/` file into the multiplayer client's Lua state is open [#1284/C/open].
- That a `server/` file runs in the client's Lua state is measured once, incidentally, and the loader step that does it has not been traced, so a `server/` file printing its side at file scope on both sides is the probe that settles it [#0856/M/n=1/open].
- Settled by: one mod whose `client`, `server` and `shared` files each write their own folder name into a distinct global and onto an order list, read on both sides — [experiments.md § Named experiments](../reference/experiments.md), row `X18`.

<a id="x19"></a>
### X19 — Which string is the replay sort key: mod id, folder name, stored script path or display name?
- Which string is the replay sort key, the mod id, the folder name, the stored script path or the display name, is open [#1285/C/open].
- The jar names the stored script path as the sort key, and no measurement separates it from the other three candidates [#1056/C/C-only/open].
- A mod whose id sorts last while its script file sorts first has not been booted, and mod id, folder name, stored script path and `mod.info` display name sort identically in every boot this library has run, two permutations of the same bodies plus one earlier session [#0886/M/n=2/open].
- Waiting on it: [item-pass.md](item-pass.md#open).
- Settled by: four sort mods, each built to win under exactly one candidate key, in the shared script-replay boot — [experiments.md § Named experiments](../reference/experiments.md), row `X19`.

<a id="x20"></a>
### X20 — Do two mods at the same relative path both load, for a script file and for a Lua file?
- Whether two mods at the same relative path both load, for a script file and for a Lua file, is open [#1286/C/open].
- Waiting on it: [item-pass.md](item-pass.md#open), [packaging.md](packaging.md#open).
- Settled by: two mods shipping the same relative script and Lua paths with different content, reading which item and which global survive, plus a separate boot with a mod file at a vanilla relative script path — [experiments.md § Named experiments](../reference/experiments.md), row `X20`.

<a id="x21"></a>
### X21 — Does a folder whose only `mod.info` is `common/mod.info` resolve, and does the client's mod-list call site agree with the dedicated server's?
- Whether a folder whose only `mod.info` is `common/mod.info` resolves, and whether the client's mod-list call site agrees with the dedicated server's, is open [#1287/C/open].
- The requested-id lookup for a folder carrying only `common/mod.info` has not been run as a purpose-built probe: the folder both boots used carried both files, the jar fallback is read and not measured, and one boot closes it [#0823/C/C-only/open].
- It also settles [#0877/C/C-only/open], [#1375/C/C-only/open] and [#1664/C/open] on [mod-anatomy.md](../platform/mod-anatomy.md#open).
- Waiting on it: [packaging.md](packaging.md#open).
- Settled by: a purpose-built mod carrying `common/mod.info` and nothing else, its verify gate on the server side only, read on both sides — [experiments.md § Named experiments](../reference/experiments.md), row `X21`.

<a id="x22"></a>
### X22 — Does a version dir shipping `media/` that collides with nothing still load, and does a shadowed `common/` copy ever execute?
- Whether a version dir shipping `media/` that collides with nothing still loads, and whether a shadowed `common/` copy ever executes, is open [#1288/C/open].
- Both measured arms had either a collision or an empty version dir, so a version dir that ships `media/` colliding with nothing, and the inertness of a shadowed `common/` file, are unrun [#0835/M/n=2/open].
- Waiting on it: [packaging.md](packaging.md#open).
- Settled by: a mod whose `common/` and version dir each ship a colliding and a non-colliding file, with a sentinel only the shadowed copy can set — [experiments.md § Named experiments](../reference/experiments.md), row `X22`.

<a id="x23"></a>
### X23 — How does a release client behave on an unguarded raise, and what sets `showLuaDebuggerOnError`?
- Settled by run x202-20261006-220437: a release client answered through the raise with the raising handler's body cut and the handler chain intact [#3317/M/n=1] [#0958/M/n=1], and the tail counter read zero while the counters ahead of and behind the raising handler read one [#0959/M/n=2].
- The -debug client beside it, given the same trigger, parked [#3318/M/n=1].
- The debugger-on-error flag is set true once after `OnGameBoot` and by a debug-only key, and the debug flag gates the failure helper [#3320/C/C-only].
- The reading is one release client, one raise shape, one fire; the settling run is [experiments.md § Named experiments](../reference/experiments.md), row `X23`.

<a id="x26"></a>
### X26 — Does `CleanUI`'s `pcall(triggerEvent, …)` wrapper change what an unguarded raise does inside a dispatch?
- Whether `CleanUI`'s `pcall(triggerEvent, …)` wrapper changes what an unguarded raise does inside a dispatch is open, its runtime half inferred from the code and never driven [#1292/C/open].
- It also settles [#1545/M/n=1/open] on [lua-platform.md](../platform/lua-platform.md#open).
- Waiting on it: [packaging.md](packaging.md#open).
- Settled by: a harness entry into the inventory context-menu builder and one session reading the wrapper's own failure line and whether the handlers behind the raise ran — [experiments.md § Named experiments](../reference/experiments.md), row `X26`.

<a id="x27"></a>
### X27 — Does `InitLoadPP`'s per-body net-id reallocation ever put a stale id on the wire?
- Whether `InitLoadPP`'s per-body net-id reallocation ever puts a stale id on the wire is open [#1293/C/open].
- `Item.InitLoadPP` allocates a fresh net id per appended body, a jar reading with no measurement behind it, and whether that ever puts a stale id on the wire is unread [#1063/C/C-only/open].
- Waiting on it: [item-pass.md](item-pass.md#open), [mp-sync.md](mp-sync.md#open).
- Settled by: reading a multiply-redefined item's id and full type on both sides in the shared script-replay boot, where the two sides agreeing bounds the risk — [experiments.md § Named experiments](../reference/experiments.md), row `X27`.

<a id="x29"></a>
### X29 — Does `MoodleFramework` load whole and render a registered moodle? (settled)
- Settled by run x181: a moodle registered through MoodleFramework renders on a dedicated-server client [#3192/M/n=1]; see [experiments.md § Named experiments](../reference/experiments.md), row `X29`.

<a id="x30"></a>
### X30 — Does a file-scope `ZomboidGlobals.HungerIncrease` assignment from a mod actually change the drain?
- Whether a file-scope `ZomboidGlobals.HungerIncrease` assignment from a mod actually changes the drain is open [#1296/C/open].
- Settled by: a file-scope assignment and a game-start assignment from one mod, read against the server's drain rate and the fixture's baseline rate — [experiments.md § Named experiments](../reference/experiments.md), row `X30`.

<a id="x31"></a>
### X31 — Does a dotted `OnCooked` name fire, on which side, and can the cooking pipeline be driven end to end at all?
- Whether a dotted `OnCooked` name fires, on which side, and whether the cooking pipeline can be driven end to end at all is open [#1297/C/open].
- It also settles [#0778/C/C-only/open] and [#0784/C/snapshot/open] on [cooking-and-recipes.md](../facts/cooking-and-recipes.md#open), and [#0967/C/C-only/open] on [lua-platform.md](../platform/lua-platform.md#open).
- Waiting on it: [eat-and-cook-hooks.md](eat-and-cook-hooks.md#open).
- Settled by: a cook-transition session with a dotted target, then a harness craft command that reaches a crafted instance with the creation hook registered — [experiments.md § Named experiments](../reference/experiments.md), row `X31`.

<a id="x33"></a>
### X33 — Does a cancelled eat of an item whose state-modified `abs(getHungerChange()*100)` is 1 or less really apply nothing at all?
- Whether a cancelled eat of an item whose state-modified `abs(getHungerChange()*100)` is 1 or less really applies nothing at all is open [#1299/C/open].
- Both boots of session S-D left it unmeasured: the harness's stop clears only actions not yet started, so the started eats of the second boot ran to completion, the first boot's eats reached `complete` and raised in a wrap cycle, and no cancel reached the server-stop step in either [#2834/M/n=2].
- Waiting on it: [eat-and-cook-hooks.md](eat-and-cook-hooks.md#open), [item-pass.md](item-pass.md#open).
- Settled by: a client command that stops a started action (`IsoGameCharacter.StopAllActionQueue`), then a completed eat, a cancelled eat of a normal item and a cancelled eat of an item driven under the guard, each read on the server — [experiments.md § Named experiments](../reference/experiments.md), row `X33`.

<a id="x34"></a>
### X34 — Does a `CalculateStats` handler that reproduces the seven skipped updaters from the library's formulas track vanilla's stat trajectory, stat by stat, over several game-hours on a live server?
- Whether a `CalculateStats` handler that reproduces the seven skipped updaters from the library's formulas tracks vanilla's stat trajectory, stat by stat, over several game-hours on a live server is open [#2081/C/open].
- Run `x132r-20261005-072441` ran the asleep arm under a partial hold, about 15 % of stat updates awake: asleep thirst tracked vanilla's inside the band as a mixed-sample parity reading, fatigue and endurance sat at their floor and ceiling on a rested character, and the running arm only walked, the harness run command not running [#2841/M/n=2] [#2840/M/n=2].
- X34's asleep arm needs a hold that wins at every stat update: `player.sleep.hold`'s once-per-tick re-assert loses about 15 % of updates to the client's reset (x132r-20261005-072441); a re-assert inside the stat tick itself, or a suppressed client reset, would close it [#2840/M/n=2].
- Waiting on it: [character-stats.md](../facts/character-stats.md#open), [endurance-fatigue-sleep.md](../facts/endurance-fatigue-sleep.md#open).
- Settled by: two boots of one restored fixture, one with no handler registered and one with the reproducing handler, sampling the seven stats hourly on the server against a per-stat band — [experiments.md § Named experiments](../reference/experiments.md), row `X34`.

<a id="x35"></a>
### X35 — Is the handler's endurance write the last before the push, as the tick order reads?
- Whether a `CalculateStats` handler's endurance write is the last write before the player-stats push, as the tick order reads, is open [#2082/C/open].
- Run `x132r-20261005-072441` could not take it: no handler in the tree writes the sentinel, the mod having dropped its own and the probe mod's handlers writing no stat, and the harness run command only walked [#2840/M/n=2].
- Run `x161s-20261006-031534` read only vanilla's awake endurance reaching the client, within about one push, no handler writing awake endurance on that boot (code inference; #3050's bound) [#3050/M/n=1].
- Run `x161f-20261006-055908` read one discriminating resting pair with the endurance fold on: the client's copy equalled the handler-written value read mid-regeneration a push earlier; no running arm [#3079/M/n=1].
- Waiting on it: [character-stats.md](../facts/character-stats.md#open), [endurance-fatigue-sleep.md](../facts/endurance-fatigue-sleep.md#open).
- Settled by: a handler writing a sentinel endurance each tick, read in client-first pairs at rest and while running, beside an arm with the handler removed — [experiments.md § Named experiments](../reference/experiments.md), row `X35`.

<a id="x36"></a>
### X36 — Does `Fitness.update` tick on the server for a connected player?
- Whether `Fitness.update`'s decay ticks on the server for a connected player is open [#2083/C/open]; the rep path is settled (#2879).
- Waiting on it: [exercise-and-training.md](../facts/exercise-and-training.md#open).
- Settled by: a seeded exercise, then two game-days with no exercise, reading the server's regularity for the fall the decay predicts — [experiments.md § Named experiments](../reference/experiments.md), row `X36`.

<a id="x40"></a>
### X40 — What is the experience anti-cheat's check interval, and does a server-side burst of grants trip it?
- Whether a server-side burst of grants trips the experience anti-cheat on a non-admin connection is open [#2085/C/open]; on the admin connection it drew no kick and no line [#2873/M/n=1].
- Waiting on it: [perks-and-strength.md](../facts/perks-and-strength.md#open).
- Settled by: a desk read of what enables the check, then above-bound and below-bound bursts of server-side grants beside a console-grant control, timing the logged trips — [experiments.md § Named experiments](../reference/experiments.md), row `X40`.

<a id="x45b"></a>
### X45b residual — What does QualityCooking's per-eat buff do beside a second eat wrap?
- QualityCooking's per-eat effect stays unmeasured: a spawned Apple carries no cooking tier, so its handler calls the original and writes no buff, and the composition of the two wraps was read without it [#2838/M/n=3].
- Settled by: a harness command that stamps an item's modData on the server (`QualityCookingTier`), then one eat of the stamped item with both wraps installed, reading QuestSystem's `cookingBuff` record — [experiments.md § Named experiments](../reference/experiments.md), row `X45b`.

<a id="x47"></a>
### X47 — Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold?
- Whether a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window holds is open [#2096/C/C-only/open]; run x161p-20261006-035559 read the write gone by the first sample a quarter second after it, standing and in a walking arm whose movement was not confirmed, with no read-back in the writing tick [#3066/M/n=1].
- Waiting on it: [perception-speed.md](../facts/perception-speed.md#open).
- Settled by: a client write sampled in Lua every quarter second for four seconds, walking and standing, against the packet's cadence — [experiments.md § Named experiments](../reference/experiments.md), row `X47`.

<a id="x48"></a>
### X48 — Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value?
- Whether a client-originated hit or rep grant reaches the Strength protein branch on the server's store is open [#2087/C/open]; the server route is settled [#2872/M/n=1].
- Waiting on it: [perks-and-strength.md](../facts/perks-and-strength.md#open).
- Settled by: melee hits with the protein store raised on the server alone and then on the client alone, reading the Strength experience each hit grants — [experiments.md § Named experiments](../reference/experiments.md), row `X48`.

<a id="x51"></a>
### X51 — Do the climate override and activity move an outdoor character's thermoregulator?
- Whether the climate override reaches an outdoor character's air and core, and whether heat with activity raises the fluids multiplier, is open [#2946/M/n=1/open]; the getters' live server reading is settled [#2935/M/n=1].
- Waiting on it: [body-and-weight.md](../facts/body-and-weight.md#multipliers).
- Settled by: the climate override held over an outdoor character, idle and walking, reading the server's thermoregulator per tick — [experiments.md § Named experiments](../reference/experiments.md), row `X51`.

<a id="x59"></a>
### X59 — Does a script `OnEat` on the vitamin pill run on the server?
- Whether a mod's script `OnEat` on `Base.PillsVitamins` runs when the pill is taken is open [#2960/C/C-only/open]; the jar reads the call [#2955/C/C-only], and the pill action runs on the server [#2952/M/n=1].
- Waiting on it: [eating-pipeline.md](../facts/eating-pipeline.md#pill-path).
- Settled by: a pill taken with a script `OnEat` assigned, counting its calls on both sides — [experiments.md § Named experiments](../reference/experiments.md), row `X59`.

<a id="x64"></a>
### X64 — Does the mod's sweat term fire live?
- Whether the sweat term fires on a live server is open [#2972/M/n=1/open]; the drink, sodium and world-water routes it shares the pool with are settled [#2966/M/n=1, #2967/M/n=1, #2970/M/n=1].
- Waiting on it: [testing-your-mod.md](testing-your-mod.md#scenario-inputs).
- Settled by: a run or an activity the server classifies above 3 MET for game hours [#2972/M/n=1/open], reading the sweat fields — [experiments.md § Named experiments](../reference/experiments.md), row `X64`.

<a id="x69"></a>
### X69 — Does an unbroken sleep reset the mod's hours awake?
- Whether an unbroken sleep resets hours awake on a live server is open [#2992/M/n=1/open]; the window accounting, the debt and the impairment unit under the harness's hold are settled [#2986/M/n=1, #2985/M/n=1].
- Waiting on it: [testing-your-mod.md](testing-your-mod.md#scenario-inputs).
- Settled by: a client-initiated sleep, or a hold that keeps every minute asleep for over an hour [#2992/M/n=1/open], reading `acute.awakeH` and `sleptH` — [experiments.md § Named experiments](../reference/experiments.md), row `X69`.

<a id="x80"></a>
### X80 — Does halving the regeneration constants halve awake regeneration?
- Whether the halved constants halve the awake tier's regeneration is open [#3045/M/n=1/open]; the setters and getters answer and the values hold within a session, and they are not saved [#3020/C/inference].
- Waiting on it: [health-surfaces.md](../facts/health-surfaces.md#regeneration).
- Settled by: a damaged part read in two windows, at the defaults and halved, with the hunger, thirst and sickness moodles low enough that the regeneration tier is not 3 [#2353/C/C-only] — [experiments.md § Named experiments](../reference/experiments.md), row `X80`.

<a id="x81"></a>
### X81 — What steady core offset does a per-update TEMPERATURE target hold?
- What offset a target written on every update holds is open [#3047/M/n=1/open]; one write moves the core halfway at the next tick [#3046/M/n=1].
- Run `x161b-20261006-065751` could not take it: at rest the core sat about 0.45 under the set point, so the mod's -0.2 target never acted [#3115/M/n=1] [#3100/M/n=1].
- Waiting on it: [health-surfaces.md](../facts/health-surfaces.md#thermal).
- Settled by: a per-tick writer of an absolute target for game hours, reading the core and the set point — [experiments.md § Named experiments](../reference/experiments.md), row `X81`.

<a id="x86"></a>
### X86 — Does the aiming delay follow the jar's post-shot sum and per-update step while a player aims?
- Whether the sum, the step and a write between shots behave as read while a player really aims is open [#3063/M/n=1/open]; a written aim flag does not hold and the delay then sits at the aiming time [#3062/M/n=1], and the three attack events fire on the shooting client [#3061/M/n=1].
- Waiting on it: [perception-speed.md](../facts/perception-speed.md#combat).
- Settled by: an aim held by input with the delay below the aiming time, sampled per client tick across shots, with a write between shots — [experiments.md § Named experiments](../reference/experiments.md), row `X86`.

<a id="x105"></a>
### X105 — Does the cold fold scale a catchACold rise?
- Whether the fold that scales the cold accumulator's rise does so on a live server is open [#3129/M/n=1/open]; sleep debt raised the cold multiplier to 2.5 at the next rebuild [#3099/M/n=1], and the climate override and a soaked character never lifted the thermoregulator's delta over the 0.1 the accrual needs, so the fold made no write [#3114/M/n=1].
- Waiting on it: [health-surfaces.md](../facts/health-surfaces.md#poison-infection).
- Settled by: an outdoor or wet-and-cold seat that lifts the catch-a-cold delta past the accrual's gate for game hours, reading catchACold with the fold on and off — [experiments.md § Named experiments](../reference/experiments.md), row `X105`.

## See also

- [experiments.md](../reference/experiments.md) — the full spec of every named experiment, its merged sessions, splits, riders and cost roll-up.
- [new-nutrients.md](new-nutrients.md) — where a mod nutrient's value lives and how it acts.
- [item-pass.md](item-pass.md) — the food rebalance through script blocks.
- [eat-and-cook-hooks.md](eat-and-cook-hooks.md) — where an intake correction and a cook-side seat can sit.
- [mp-sync.md](mp-sync.md) — which route each quantity travels between server and client.
- [ui-and-moodles.md](ui-and-moodles.md) — what the mod can show a player, and the moodle route.
- [packaging.md](packaging.md) — the layout, the checksum gate and the resident mods.
- [testing-your-mod.md](testing-your-mod.md) — how the mod goes under the harness.
- [overview.md#coverage](../platform/overview.md#coverage) — the surfaces the library touches but has no page for, each an open row in the index.
