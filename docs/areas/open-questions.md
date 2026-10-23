# Open questions
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: every open row in the register by topic, the decisions the area pages leave to the design, and one subsection per surviving named experiment; the experiment specs stay in `reference/experiments.md`

## Index
<a id="index"></a>

One line per `open` row in the register, whichever page owns it (the row's owner cell names the section that states it in full), grouped by topic and in id order within a topic.
The last cell names the experiment that settles the row, or, where none does, the reading that would.

### Mod loading, layout and script replay
| id | question | settled by |
|---|---|---|
| [#0823/C/C-only/open] | Whether a folder carrying only `common/mod.info` resolves under the requested-id lookup is un-run as a purpose-built probe. | [X21](#x21) |
| [#0835/M/n=2/open] | Whether a shadowed `common/` file is inert when a version dir ships `media/` beside it is un-run. | [X22](#x22) |
| [#0856/M/n=1/open] | What maps a mod's `server/` tree into the client's Lua state is unread: the loader step that does it has not been traced. | [X18](#x18) |
| [#0877/C/C-only/open] | The client's own mod-list call site was never exercised: everything measured about the `mod.info` chain, the version dirs and the folder name was measured on the dedicated-server path. | [X21](#x21) |
| [#0882/C/C-only/open] | Whether `loadModAfter=` and `loadModBefore=` reach a dedicated server at all is unsettled: the jar and the vanilla Lua tree say they do not, and no boot has tested it. | booting a pair of mods that disagree about order and reading the loader's `loading` lines |
| [#0883/C/C-only/open] | What a duplicate id across two mod roots does in practice is unsettled: the earlier-folder tie-break is a code reading only. | installing one id in two roots and reading which folder the loader walks |
| [#0886/M/n=2/open] | Which string orders the script-body replay is unmeasured. | [X19](#x19) |
| [#1056/C/C-only/open] | Which string the replay sort orders is unseparated by measurement, and the jar says the stored path. | [X19](#x19) |
| [#1062/C/C-only/open] | Whether the per-key merge survives a reloadlua or script reload is unread. | driving a reload in a running session and re-reading a merged item's keys |
| [#1063/C/C-only/open] | Whether the fresh net id Item.InitLoadPP allocates per appended body ever puts a stale id on the wire is unread. | [X27](#x27) |
| [#1284/C/open] | What maps a mod's `server/` file into the MP client's Lua state? | [X18](#x18) |
| [#1285/C/open] | Which string is the replay sort key — id, folder name, stored script path, or display name? | [X19](#x19) |
| [#1286/C/open] | Do two mods at the same relative path both load — for a script file, and for a Lua file? | [X20](#x20) |
| [#1287/C/open] | Does a folder whose only `mod.info` is `common/mod.info` resolve, and does the client's mod-list call site agree with the dedicated server's? | [X21](#x21) |
| [#1288/C/open] | Does a version dir shipping `media/` that collides with nothing still load, and does a shadowed `common/` copy ever execute? | [X22](#x22) |
| [#1293/C/open] | Does `InitLoadPP`'s per-body net-id reallocation ever put a stale id on the wire? | [X27](#x27) |
| [#1375/C/C-only/open] | Which mod.info supplies a mod's id when the mod ships more than one is not settled. | [X21](#x21) |
| [#1664/C/open] | Which `mod.info` the live id chain reads when a folder holds several is unsettled. | [X21](#x21) |
| [#3136/C/open] | Whether a partial item block that omits `DisplayCategory` as well as `ItemType` still merges into a food is unmeasured. | the same partial block with both keys omitted, reading the base-module food count and the instance getters on both sides |
| [#3178/C/open] | Whether the server's 60 s checksum arm acts on a mismatched client is unmeasured: 157.806 s watched past the warning saw no act. | a mismatched client held connected past the 60 s grace, reading the server log for the timeout act |

### Lua runtime, events and uncovered surfaces
| id | question | settled by |
|---|---|---|
| [#0967/C/C-only/open] | The item-block creation hook has never been fired by any session in this library; it is read off the jar only. | [X31](#x31) |
| [#1292/C/open] | Does CleanUI's `pcall(triggerEvent, …)` wrapper change what an unguarded raise does inside a dispatch? | [X26](#x26) |
| [#1545/M/n=1/open] | Whether a resident mod's protected-call wrapper changes what an unguarded raise does on a client is open: the run that would have measured it lost every client reading. | [X26](#x26) |
| [#2045/M/one-side/open] | Timed actions have no page: the action queue, its tick budget and how a mod adds an action of its own are unread. | a read of the action queue, its tick budget and the route by which a mod adds an action |
| [#2046/C/one-side/open] | The crafting pipeline has no page: the crafting interface, the handcraft action and the recipe-discovery surface are unread. | a read of the crafting interface, the handcraft action and the recipe-discovery surface |
| [#2047/C/one-side/open] | Server admin and the remote console have no page: the admin command set as a whole and what each does to a running world are unread. | a read of the admin command set against a running world |
| [#2048/C/one-side/open] | Build detection has no page: what a mod can detect about the running build from inside Lua is unread. | a read of what Lua can learn about the running build |
| [#2049/M/n=1/open] | Client-only mods have no page: the general cost of shipping one side only, and what still reaches the other side, is stated as anatomy rather than as a topic of its own. | a read of what a one-sided mod still reaches on the other side |
| [#2051/C/one-side/open] | The events roster has no page: the full roster and which events fire on a dedicated server were never enumerated. | enumerating the full events roster and which events fire on a dedicated server |

### Sandbox options
| id | question | settled by |
|---|---|---|
| [#0139/M/n=1/open] | Whether a client-local flip of the sandbox `Nutrition` option halts the server-side drain is unsettled. | [X17](#x17) |
| [#0140/C/C-only/open] | Whether the Lua `SandboxVars` mirror is also stale after an admin-panel push is unmeasured. | [X17](#x17) |
| [#1283/C/open] | Can Lua flip the `Nutrition` sandbox option at runtime, does it replicate, and does the drain stop? | [X17](#x17) |

### Sync and the wire
| id | question | settled by |
|---|---|---|
| [#0145/C/snapshot/open] | The client-to-server direction of `EatFoodPacket` is latent: `GameClient.eatFood` has no callers, and a mod could call it. | calling the game client's eat-food method from a mod and reading both sides |
| [#0191/M/n=1/open] | What the server validates on an incoming nutrition write is unmeasured: the probes show a client write overwritten by the next push, not rejected. | a probe that separates rejection from overwrite |
| [#0372/M/n=1/open] | Only `cookingTime` has been seen to carry over between packets; the other nineteen conditionally-written fields have never been made to differ in a run. | syncing an item with a distinctive cooking time and then a zero-valued item |
| [#0376/C/C-only/open] | How often a multiplayer server re-sends inventory items, and so how often a client's freshness display refreshes, was not traced. | tracing the cadence of the item-list receiver |
| [#0377/C/C-only/open] | Whether the item-stats packet really carries `cooked` is unsettled: both sides already read false, so the match is uninformative. | one divergence test, setting `cooked` on the server only and reading the client |
| [#0885/M/n=1/open] | Whether item modData moves from server to client is un-run. | [X14](#x14) |
| [#1040/M/one-side/open] | Whether item modData moves in the server-to-client direction through syncItemFields() is unmeasured. | [X14](#x14) |
| [#1280/C/open] | Does item modData move server to client? | [X14](#x14) |
| [#1348/C/inference/open] | Whether the two weight-direction flags Auto Cook's smart-spice gate reads can desync is unsettled. | a session that drives calories above 1000 or below 0 and re-reads both sides |
| [#1422/C/C-only/open] | Why a client copy does not run the item update is unexplained for every field but cooking: the call path to it carries no side guard. | tracing what stops the item update on a client |
| [#1434/C/inference/open] | Whether a relog or a save round-trip repairs the client's copy of the four uncarried fields is not measured. | a relog read of a cooked item on both sides |

### Eating, drinking and cooking
| id | question | settled by |
|---|---|---|
| [#0142/C/open] | How far weight and hunger drift apart on a part-eaten custom-weight item, and whether the `f0` write is intentional, is unmeasured. | eating a canned food a quarter at a time and logging its weight, `hungChange` and `baseHunger` at each step |
| [#0143/C/open] | Which items ever set `baseHunger` different from `hungChange` at spawn is unknown: every path found initialises them equal, and four writers that set `baseHunger` separately were not read. | reading the two writers still unread, `RecipeCodeOnCreate.makeCoffee` and `ItemStatsPacket.applyItemStats` |
| [#0146/C/open] | `getHealthFromFoodTimeByHunger()` was not dumped; it scales the food-to-health loop rather than intake. | a jar dump of the method |
| [#0190/C/snapshot/open] | `Nutrition.caloriesMax` and `caloriesMin` are maintained but no reader was found for either. | a fresh jar-wide reader scan of both fields, with the exposer dump beside it |
| [#0380/C/C-only/open] | No reader for `AddIngredientIfCooked`, which 37 recipe blocks use, was traced beyond the ingredient-usability check. | dumping the key's readers from the jar |
| [#0778/C/C-only/open] | What the dataset says about a `mode:destroy` line annihilating the rest of an item is open to measurement: `ItemUser.UseItem`'s removal branch needs a real `ISHandcraftAction` craft. | [X31](#x31) |
| [#0779/C/snapshot/open] | The 33 drying recipes write a `variable` range on both sides while a jar reading has `isVariableAmount` never firing in vanilla; both cannot be right. | one live craft probe reading the input count and the input's amount and maximum amount |
| [#0780/C/open] | The rotten branch of the evolved summation is not computed per row. | computing the rotten arm per row and reading the rotten flag off the instance |
| [#0782/C/n=1/open] | The per-use rule rests on `Base.Icecream` alone; a second partial-use row would widen its measured base. | `Base.Salt` at 1 of 10 uses on the existing command |
| [#0784/C/snapshot/open] | What the `OnCreate` hooks of the 37 output-less recipes do to nutrition, if anything, is unread. | [X31](#x31) |
| [#0785/C/C-only/open] | The five parse-time `EvolvedRecipe` aliases were never live-checked. | one probe reading whether `RicePot` resolves as a recipe name and what the `Rice`-templated recipes list |
| [#1297/C/open] | Does a dotted `OnCooked` name fire, on which side, and can the cooking pipeline be driven end to end at all? | [X31](#x31) |
| [#2829/M/n=1/open] | Two drink corners are unmeasured, cancel semantics and the 100 ms anim-event cadence under `settimespeed`, and the client's arrival of the new fill and calories is read only to a poll of 1.5 to 2 s. | a drink cancelled partway and a drink at a raised time speed, each read on both sides |
| [#2960/C/C-only/open] | Whether a script `OnEat` given to `Base.PillsVitamins` by a mod's item block runs on the server when the pill is taken is unmeasured. | [X59](#x59) |
| [#3595/C/open] | Whether a declared nutrient vector on an instance whose calories and hunger were scaled apart can be anchored on the type's script calories is open: those calories are read only off a fresh instance made through `instanceItem`, which runs the type's `OnCreate`. | a read of a type's script calories that runs no `OnCreate`, then the declared step anchored on it |

### Spoilage and the food item
| id | question | settled by |
|---|---|---|
| [#0147/C/open] | No vanilla item was checked for `DaysFresh` equal to `DaysTotallyRotten`, the shape that makes the rot-roll denominator take the 100 per cent branch. | scanning the food script for that pair of keys |
| [#0251/M/uncommitted/open] | The thaw rate does not reproduce: two runs of the same script measured 47.25 and 67.8 per cent of `freezingTime` per game hour, against the code's 66.7 per cent. | a third run of the same phase at the same time speed and in the same container, its artifact committed |
| [#0371/M/n=1/open] | The measured age gain over one accelerated game day, 1.00777 against 1.02320 predicted, falls 1.5 per cent short, unexplained. | a run that brackets the item's own aging window rather than the wait loop's clock samples |
| [#0373/C/C-only/open] | The fridge and freezer container multipliers are unmeasured: the fixture world has no powered appliance at the spawn point. | a run that sets a container custom temperature, or that spawns a powered appliance |
| [#0374/C/C-only/open] | Whether food ages at all in single-player at default settings is unsettled. | a single-player measurement, which a dedicated-server harness cannot give |
| [#0375/C/C-only/open] | The syncing form of the aging call has two callers only, so on a dedicated server the rate-limited stats send on a rot transition effectively never fires for ordinary food. | a live server log across a rot transition |
| [#0378/C/C-only/open] | The translation labels of the fridge-factor and rot-speed enums were not read; only their numeric mapping is established. | reading the sandbox translation files |
| [#0379/C/C-only/open] | `Food.rottenTime`, `Poison` and `UseForPoison` have no Java or vanilla-Lua reader, so all three look like mod-facing API rather than mechanics. | a reader scan that reaches outside the jar and the vanilla Lua tree |
| [#0384/C/C-only/open] | An item whose fresh and rotten thresholds are equal is unmeasured at eat time, where it takes the hundred-per-cent branch of the rot-sickness denominator. | eating `Base.RatKing` on a live server and reading the sickness roll |
| [#1429/C/C-only/open] | Whether 42.20.4 ever loads a B41-layout item-name translation file stays open by design. | repeating the pair inside a writable copy of the mod tree |

### Datasets and tools
| id | question | settled by |
|---|---|---|
| [#0663/C/snapshot/open] | Whether the 16 unresolved `ReplaceOn*` targets should be resolved against a wider item scan is open. | resolving the targets against an item scan wider than the food and drink set |
| [#0664/C/snapshot/open] | Four fluid-only property shapes have no row in the 114-key table: `alcohol` in a fluid's `Properties` and the `Poison` block's `maxEffect`, `minAmount` and `diluteRatio`. | giving the four shapes rows in the script-key reference |
| [#0665/C/snapshot/open] | A pick-random row's nutrition numbers are one draw and not an expectation over the pool. | a decision on whether the dataset publishes an expectation over the pool |
| [#0672/C/C-only/open] | Fluid containers have no live census route: the script `Item` exposes no component accessor to Kahlua, so the 133 count is scanner-only. | a live read of an item's components, which the build does not expose |
| [#0674/C/C-only/open] | How the game picks a container's spawn fill between `InitialPercentMin` and `InitialPercentMax` is read but not measured, and whether the dataset carries the two bounds as columns is open with it. | spawning several `Base.WineOpen` and reading each instance's fill against its range |
| [#0777/C/snapshot/open] | Whether the 202 `component CraftRecipe` entity build recipes belong in a third dataset, and whether any of them consumes food, is open. | scanning those blocks' `inputs` against the food dataset |
| [#0781/C/snapshot/open] | `data/food-items.json` carries no `UseDelta` column, so the drainable charging rule is unconditional where the jar tests drainable and `UseDelta` below 1. | a `UseDelta` column the charging rule can test |
| [#0783/C/snapshot/open] | Whether the scanner should widen the output-mapper rule to take a `default` as a type is open. | scanning a mod that ships such a mapper and reading what `meta.outputMapperIssues` records |

### Vanilla body, stats and perks
| id | question | settled by |
|---|---|---|
| [#0591/M/n=1/open] | The walking, running and sprinting burn constants are unmeasured: the run flag did not reach the server's copy of the character on the walk-to plus set-running route. | the walk, run and sprint burn ratios; running reached the server on none of x141a's ticks (#2877) and on 11 of 188 of x224's sprint leg [#3384/M/n=1] |
| [#0592/M/n=1/open] | The asleep burn branch is unmeasured: the sleep write held on the immediate read-back but did not persist. | a sleep arm that verifies the state on the server before the window opens |
| [#0593/C/C-only/open] | Whether the 1.2 running thirst factor ever fires on a dedicated server is unknown: it is gated on the local player instance, so running may not raise thirst in multiplayer at all. | the same running branch the burn constants need |
| [#0594/C/C-only/open] | The real range of the thermoregulator's energy multiplier is unknown, so the size of the cold-weather burn bonus is unbounded here. | a temperature-controlled pair of idle windows |
| [#0596/C/C-only/open] | Whether split-screen players 2 to 4 accrue hunger or thirst locally is unverified. | a split-screen boot |
| [#0597/C/C-only/open] | The write order of applyWeightFromTraits is not exercised: a character carrying two weight traits, reachable by a mod, would end at the last matching branch. | a probe that adds two band traits from Lua and reads the written weight back |
| [#2081/C/open] | Does a `CalculateStats` handler that reproduces the seven skipped updaters from the library's formulas track vanilla's stat trajectory, stat by stat, over several game-hours on a live server? | [X34](#x34) |
| [#2082/C/open] | Is a `CalculateStats` handler's endurance write the last before the player-stats push, as the tick order reads? | [X35](#x35) |
| [#2083/C/open] | Does `Fitness.update` tick on the server for a connected player? | [X36](#x36) |
| [#2085/C/open] | What is the experience anti-cheat's check interval, and does a server-side burst of grants trip it? | [X40](#x40) |
| [#2087/C/open] | Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value? | [X48](#x48) |
| [#2096/C/C-only/open] | Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold? | [X47](#x47) |
| [#2946/M/n=1/open] | Whether the climate override moves an outdoor character's air and core, and whether a hot exposure with activity raises the fluids multiplier above 1, is unmeasured. | [X51](#x51) |
| [#3045/M/n=1/open] | Whether halving the regeneration constants halves awake regeneration is unmeasured. | [X80](#x80) |
| [#3047/M/n=1/open] | What steady core offset a TEMPERATURE target written on every update holds is unmeasured. | [X81](#x81) |
| [#3063/M/n=1/open] | Whether the post-shot sum, the per-update aiming step and a client write between shots behave as the jar reads while a player really aims is unmeasured. | [X86](#x86) |
| [#4113/C/inference/open] | Whether a body part's added pain survives a relog alone, apart from a server restart, is unmeasured. | a relog without a restart, reading the part's added pain on the server after the rejoin |

### The worked example's body model and lethal states
| id | question | settled by |
|---|---|---|
| [#2992/M/n=1/open] | Whether an unbroken sleep resets the mod's hours awake live is unmeasured. | [X69](#x69) |
| [#3129/M/n=1/open] | Whether the mod's cold fold scales a catchACold rise is unmeasured. | [X105](#x105) |
| [#3996/C/open] | Whether a fasting body's water need falls below the fed basal turnover is open. | a fasting-urine research pass |
| [#3998/C/open] | Whether the Strength fit's model step should follow the kernel's deficit arm is open: its non-exact step still applies Alpert's ceiling and the dropping fat floor. | the next re-fit of the protection weights on the kernel's own arm |
| [#3999/C/open] | Whether the protection weights under-predict lean loss in fed training deficits is open. | a re-fit of wT and wP on the kernel's own deficit arm |
| [#4023/M/n=1/open] | Whether the Add rule combines several active lethal states in the live game as the kernel does is unmeasured: run x482 exercised Add with one state only. | a live session with two lethal states active under Add, its target and health against the HEAD replay of the run's own inputs |
| [#4024/C/inference/open] | Whether a body that loses BMI much faster than the calibration body drops its health in one minute at the starvation state's first record-day close in the live game is unmeasured. | a live hold of a thin body across its first record-day close, graded against the replay of its own ring |
| [#4039/C/inference/open] | Whether the worked example's straight lines hold in the live game on Realistic dehydration's deficit clock and at Shortened pace is unmeasured. | a live Realistic dehydration hold and a Shortened hold, each graded against the HEAD replay of its own ring |
| [#4040/C/inference/open] | Whether a live switch of NR.HealthCombine with a lethal state active is followed within a game minute is unmeasured. | a live NR.HealthCombine switch with two states active, graded against the HEAD replay of its own ring |
| [#4053/C/inference/open] | Whether the worked example's recovering ceiling holds in the live game is unmeasured. | a live hold that lapses a lethal state, graded against the HEAD replay of its own ring through its recovery |
| [#4108/C/open] | Whether the worked example's starvation pain should follow the hunger pangs' course is open: its pain is flat while the state is active, a placeholder. | a research pass whose rows set the pangs' course, swapped into the symptom table as data |
| [#4109/C/open] | Whether the worked example's lethal states should bring deeper aches as the body wastes is open. | a research pass whose rows set the aches' onset and depth |
| [#4110/C/inference/open] | Whether a lethal state's symptoms disturb sleep in the live game is unmeasured. | a sleep-on session reading the delay to sleep with and without a state's floors and pain |
| [#4111/C/open] | Whether the worked example's wet beriberi and pellagra should show their prodromes before the clinical grade is open. | a research pass and a symptom row read on the nutrient grade before the state opens |
| [#4112/C/open] | Whether each symptom should start at its own point of a lethal state's course is open. | a research pass whose rows give each symptom's onset per state |
| [#4117/C/inference/open] | Whether a painkiller holds a lethal state's ache down on a dedicated server is unmeasured. | a session that gives a starving or dehydrated character a painkiller and reads PAIN, the parts' added pain and the Pain moodle on the server through the effect and after it |
| [#4118/C/inference/open] | Whether the worked example's symptom endurance cap speeds a character's tiring in the live game with sleep on is unmeasured. | a sleep-on session reading FATIGUE's awake rise with and without a lethal state's cap |

### Client UI and moodles
| id | question | settled by |
|---|---|---|
| [#0970/C/C-only/open] | Whether a mod-registered moodle type carries any Java effect is unmeasured. | [X2](#x2) |
| [#1274/C/open] | Is `MoodleStat` reachable from Kahlua at all, given that C is a jar-proven absence? | [X2](#x2) |
| [#3244/M/n=2/open] | Whether the tooltip band lands on screen below the engine's box, above it at the bottom edge and clear of an anchored slot is unmeasured. | a hover synthesiser reading the band's pixels or the element's draw calls |
| [#3245/M/n=1/open] | Whether a saved `visible=true` panel line restores the panel open is unmeasured. | a second boot on a user directory carrying the line |
| [#3246/M/n=1/open] | Whether the tab draws on screen, survives a tear-off through its wrap and fires the layout save's `current`-clearing branch is unmeasured. | a click synthesiser that activates the tab and tears it off before the quit |
| [#3248/M/n=1/open] | Whether a scrolled panel clips its rows at the window's edge is unmeasured. | the wheel at the Numbers level, where the rows are expected to overflow, reading the rows' draw calls after a scroll |

### Testing, the harness and performance
| id | question | settled by |
|---|---|---|
| [#1770/C/C-only/open] | Which of the harness mod's two identical mod-info files this build reads first is open. | a boot that names each copy's own id in turn against a purpose-built folder |
| [#1815/M/n=1/open] | Where the event's true ceiling sits between eight and 10.08 ticks per wall second is unmeasured. | scheduler self-tests that step the demand past the ceiling and read the fitted tick rate |
| [#1830/C/C-only/open] | Which sandbox options survive a restore is open: only the day length has been set by a profile on a restored world and measured to apply. | a profiled run that sets each option on a restored world and reads it back |
| [#3788/M/n=1/open] | Whether a fresh record's first-minute eat lands before the writer's first seed and is left out of the meal pool M is unmeasured. | a harness change that defers the server's first sight of the relaunched client until its eat is queued, then the eat and the writer's seed count read beside it |
| [#3997/C/open] | Whether a drink's per-row mass in the live drivers' event log matches the mass the live sips landed is open. | an event builder that apportions each drink by the mass each row's sips landed |
| [#4000/C/open] | Whether a stall's carry keeps the server's worst frame under the drain's tick budget live is unmeasured. | a live stall at the 60-player design load reading the worst frame across a carry's slots |
| [#4114/C/inference/open] | Whether the server's Pain moodle followed its PAIN within one 120-update window in run x495 is ungraded. | a regrade script with a tolerance sized to the run's own rise, its output a new derived artifact |
| [#4115/C/inference/open] | Whether the replay host's heal matches the game's after a lapse is open: tools/replay_live.py's stand-in heals with no per-part clamp, so after a lapse the replay's health leads the live one. | a stand-in heal with the per-part clamp, proved against a live heal after a lapse |

### Other mods
| id | question | settled by |
|---|---|---|
| [#1668/C/open] | Whether AutoCook's per-player cooking settings survive a relog on a dedicated server is unmeasured. | a profiled session that writes a setting, relogs the character and re-reads player modData on both sides |
| [#1671/C/open] | Whether Kahlua raises on TryMeatCanned's chained comparison, a boolean compared to a number, is unverified: nothing calls it. | calling that function from the command bus |

## Decisions
<a id="decisions"></a>

One line per decision the area pages leave to the design, with the fact that forces it and no recommendation, grouped by the page whose `## Open` states it.

### [new-nutrients](new-nutrients.md#open)
- Which store holds each mod nutrient's authoritative value — forced by modData being the only durable mod state while any client's transmit replaces the server's copy of a player's table [#1122/C/C-only, #1151/M/n=2].
- What range each mod nutrient store is held to, and whether it runs negative — forced by vanilla's clamps living inside the `Nutrition` setters that a parallel store never passes through, and by negative vanilla stores being an ordinary state [#0022/M/n=2, #0023/M/n=2, #0901/M/n=1].
- Whether each mod nutrient decays, and on which clock — forced by vanilla's drain being compiled into the nutrition update and reaching no store but its own macro stores [#1193/C/C-only].
- Whether a per-item mod value, a per-item nutrient among them, is a per-type script value, an entry in a per-type Lua table or per-instance state — forced by a script key agreeing on both sides for free while every instance takes a deep copy of it, by a `fluid` block storing no script key at all, and by item modData moving whole and its route being measured in one direction only [#1124/M/n=1, #2676/C/C-only, #2682/C/C-only, #1126/M/one-side, #1241/M/one-side] (also [mp-sync](mp-sync.md#open)).
- Whether a per-item nutrient must follow an item through a type change — forced by the replacement being built from its own script, with the swap naming the condition states and the age, and not item modData, as what it copies [#0266, #0243].
- Whether any mod nutrient acts through vanilla's weight model or through a model of the mod's own — forced by the model's one switch taking the drain, the burn and the weight arm together, and by the Strength grant on the protein store being the one other vanilla consumer, with the carbohydrate store and diet quality dead space [#1136/C/C-only, #2112/C/C-only, #2696/C/inference].

### [item-pass](item-pass.md#open)
- Whether the item pass reaches foods other mods declare in their own modules or leaves them on upstream numbers — forced by a `module Base` pass not touching those foods and a block naming one being an override only while that mod loads [#1030/M/n=1, #1002].
- Whether the item pass re-bases drinks per litre — forced by a drink's nutrition living on a fluid rather than on any key of the container's own block [#0626/C/snapshot, #0604/M/n=2].
- Whether the item pass names `HungerChange` at all or re-bases the macros alone — forced by hunger driving weight, recipe cost, the portion menu and the cancel guard, where the macros move intake alone [#1214/C/C-only, #0701/M/n=3, #0036/M/one-fixture].
- Which route carries each value the item pass changes — forced by a script block loading on both sides for free where a per-instance Lua write has to cross the wire [#1001/M/n=1].
- Whether the server's 60 s checksum arm acts on a mismatched client, not seen in the 157.806 s watched [#3178/C/open], [#1231/C/C-only].

### [eat-and-cook-hooks](eat-and-cook-hooks.md#open)
- Whether the intake correction sits in the completion wrapper, before `Eat` writes, or in the eat hook, after it — forced by only the wrapper seeing pre-intake values while the eat hook's store already holds the eat [#1033/M/n=1, #0008].
- Whether the correction must also cover a cancelled eat — forced by a cancel reaching `Eat` through the server-stop step and never through the completion step [#0111].
- Whether a cooked item's nutrition comes from a cook hook on the instance or from a replacement item's script — forced by the swap returning before the hook runs, and by a hook's item-field writes reaching the client only where the item packet carries them [#0266, #1036].
- Whether the intake correction also wraps the world-source drink action — forced by a drink-action wrapper never seeing a drink from a world water source [#2690/C/C-only].

### [mp-sync](mp-sync.md#open)
- Which route each quantity this mod owns travels on — forced by the three routes failing three different ways: the transmit replaces a whole table on another mod's call, a script value is fixed per type at load and checksummed at the join, and the bus stores nothing [#1151/M/n=2, #1182/C/C-only, #1153/C/C-only].
- Which values the client displays are derived on the client and which are sent from the server — forced by the band traits reaching the client only on server pushes, the experience push measured landing within about half a second [#2759/M/n=3], by the cooked-thirst halving, and by a derived value being right only while every input it reads is carried [#2595/C/C-only, #1038/M/n=2, #1508].
- Whether item round trips are keyed on the item id before the net-id run lands — forced by the per-body reallocation being unread for an item several mods append to [#1063/C/C-only/open].

### [ui-and-moodles](ui-and-moodles.md#open)
- Whether the mod relies on the tooltip's per-draw hide of vanilla's hunger line before a hover is measured — forced by the harness being unable to hover, so no run has drawn a food tooltip and the hide and the band's place are read from the code alone [#3920/C/inference].
- Whether the mod's numbers stay inside the display bands the torn-down viewer hard-codes — forced by those bands going wrong silently on a re-based scale [#1514, #1522].

### [packaging](packaging.md#open)
- Whether a patch mod, if one ships, rides this mod's Workshop item as a second folder or an item of its own — the neighbour reads name no neighbour a patch must target: one is incompatible outright, two never run on a server and one composes [#3527/C/inference, #3534/C/inference, #3541/C/inference, #3551/C/inference]; forced by a server naming mods by id and resident items already shipping several mods each [#1219/C/C-only, #1543/C/snapshot].
- Whether a block of this mod naming the preservation mod's foods can coexist with the third-party patch that claims that mod launders nutrition — blocked by the patch (3796644824) not being installed, and forced by a block naming another mod's food being an override only while that mod loads [#1606/W/snapshot, #1030/M/n=1, #1600].
- Whether this mod is built to share a server with any public nutrition overhaul — Nutrition Makes Sense writes the same stats each minute and re-bases 438 of the same foods [#3527/C/inference, #3526/C/arith.], and `incompatible=` stops nothing on a server [#1599/W/snapshot, #0813/C/C-only].

### [testing-your-mod](testing-your-mod.md#open)
- At which pacing the mod's timed scenarios run — forced by the cadence ceiling binding the day length and the multiplier together while every baseline sits at the fixture's day length [#1814/M/n=3, #1253/C/one-fixture].
- Whether the mod's load checks are verification rows or scenarios — forced by a verification expectation being a substring that cannot express absence or a numeric comparison [#1828].
- Whether the mod ships a client-side scenario for its display copy — forced by the client runner being wired with nothing to run and by every client read of a live store being a staircase [#1784, #1483].
- Whether any scenario moves a sandbox option off the fixture's value — forced by only the day length having been set by a profile, so a moved option buys a new baseline [#1809/C/C-only, #1253/C/one-fixture].
- Whether a scenario pins the thirst clock or reads the death as its result — forced by an unattended thirst drain killing the subject partway through a multi-day run [#0179/M/one-fixture].

### [body-effects](body-effects.md#open)
- Which mode a server runs the worked example in, Managed, whose writer owns hunger, thirst and fatigue with vanilla's rise rates zeroed at boot, or Overlay, which leaves those three stats to vanilla — the mode is read once at the server's boot, so a change takes a restart, Managed's zeroed rates read 0 to every other mod, and a takeover is no third mode, because it suppresses all seven updaters for every player and no other mod can undo it [#3796/C/inference] [#3797/C/inference] [#3365/C/C-only] [#2238/C/C-only] [#2240/C/C-only].
- Which store is the truth for a clamped Fitness — settled for Strength in the build, the worked example writing both stores from its own model [#3861/C/inference]; forced by the level and the experience being separate stores, each moved by a different vanilla writer [#2101/C/C-only, #2124/C/C-only].
- How large a single server-side experience grant the mod issues — forced by a tripped anti-cheat check kicking or banning the player while its interval is unread [#2147/C/C-only, #2148/C/C-only].
- Whether a warmth effect writes the temperature stat every update or accepts the single lerp step of one write — forced by one write moving the thermal core only one lerp step toward it [#2373/C/C-only].
- Which distance input a sight effect goes through, the Short Sighted boolean or the detection range — forced by both reaching the native lighting, whose use of either is outside the bytecode [#2303/C/C-only].
- Whether an activity-scaled quantity reads the metabolic-rate classes or classifies the player itself — forced by the classes being floors raised by endurance and load, none of it measured on a server [#2633/C/C-only, #2649/C/C-only].
- Whether a Fitness set's bill is capped at its asked length — not built (ruling T4-1); forced by a set the client abandons without a stop billing its type until the client disconnects, as vanilla's server keeps the set running too [#3737/C/inference] [#3734/M/n=1].

## Experiments

One subsection per surviving named experiment, in id order: the rows it owns, the rows it settles elsewhere, the pages that wait on it and its row in [experiments.md](../reference/experiments.md), which holds the full spec.

<a id="x2"></a>
### X2 — `MoodleStat` from Kahlua
- Is `MoodleStat` reachable from Kahlua at all, given that C is a jar-proven absence? [#1274/C/open]
- Whether a mod-registered moodle type carries any Java effect is unmeasured: the registration methods exist and the type is Lua-exposed, but nothing in this library has registered one, and the reachability probe does not either [#0970/C/C-only/open].
- Settles it: a global read of `MoodleStat` beside two exposed controls answering in the same call, riding any session with a client (row `X2`). Waiting: [ui-and-moodles](ui-and-moodles.md#open).

<a id="x14"></a>
### X14 — Item modData server to client
- Does item modData move server to client? [#1280/C/open]
- Un-run: the player-modData directions are measured, but in the one phase that read the item direction both sides already held the probe key and the server wrote nothing, so the phase graded a state and not a crossing [#0885/M/n=1/open].
- Whether item modData moves server to client through `syncItemFields()` is unmeasured; the one measured direction is client to server [#1040/M/one-side/open].
- Settles it: a server-only key write, a client-first census that must miss it, a forced item push and a second census (row `X14`). Waiting: [new-nutrients](new-nutrients.md#open), [mp-sync](mp-sync.md#open).

<a id="x17"></a>
### X17 — A runtime flip of the `Nutrition` option
- Can Lua flip the `Nutrition` sandbox option at runtime, does it replicate, and does the drain stop? [#1283/C/open]
- Whether a client-local flip of the option halts the server-side drain is unsettled: the flipped window accounted for 41.4 per cent of its game-time against 99.0 per cent in the control, with two server reads 1.7 s apart identical to six decimals, in one flipped window with no repeat and no `sendToServer` push [#0139/M/n=1/open].
- Whether the Lua `SandboxVars` mirror is also stale after an admin-panel push is unmeasured; the code reading predicts it fresh on both sides, because the server and every connected client call `toLua()` when they apply the push ([#0140/C/C-only/open], [#2449/C/C-only], [sandbox-options](../platform/sandbox-options.md#runtime-change)).
- Settles it: a harness route to the option's config setter and one session reading the Java option, the Lua mirror and the drain beside a no-flip control (row `X17`). Waiting: [new-nutrients](new-nutrients.md#open).

<a id="x18"></a>
### X18 — What maps a `server/` file into the client
- What maps a mod's `server/` file into the MP client's Lua state? [#1284/C/open]
- That a `server/` file runs in the client's Lua state is measured once, incidentally; the loader step that does it is untraced, so a `server/` file printing its side at file scope on both sides settles it [#0856/M/n=1/open].
- Settles it: one mod whose `client`, `server` and `shared` files each write their folder name into a distinct global and an order list, read on both sides (row `X18`).

<a id="x19"></a>
### X19 — The replay sort key
- Which string is the replay sort key — id, folder name, stored script path, or display name? [#1285/C/open]
- The jar names the stored script path, and no measurement separates it from the other three candidates [#1056/C/C-only/open].
- No boot has run a mod whose id sorts last while its script file sorts first: the four candidates sort identically in every boot this library has run, two permutations of the same bodies plus one earlier session [#0886/M/n=2/open].
- Settles it: four sort mods, each built to win under exactly one candidate key, in the shared script-replay boot (row `X19`). Waiting: [item-pass](item-pass.md#open).

<a id="x20"></a>
### X20 — Two mods at one relative path
- Do two mods at the same relative path both load — for a script file, and for a Lua file? [#1286/C/open]
- Settles it: two mods shipping the same relative script and Lua paths with different content, reading which item and which global survive, plus a boot with a mod file at a vanilla relative script path (row `X20`). Waiting: [item-pass](item-pass.md#open), [packaging](packaging.md#open).

<a id="x21"></a>
### X21 — A folder with only `common/mod.info`
- Does a folder whose only `mod.info` is `common/mod.info` resolve, and does the client's mod-list call site agree with the dedicated server's? [#1287/C/open]
- The requested-id lookup for such a folder is un-run as a purpose-built probe: the folder both boots used carried both files, the jar fallback is read and not measured, and one boot closes it [#0823/C/C-only/open].
- It also settles [#0877/C/C-only/open], [#1375/C/C-only/open] and [#1664/C/open] on [mod-anatomy](../platform/mod-anatomy.md#open).
- Settles it: a mod carrying `common/mod.info` and nothing else, its verify gate on the server only, read on both sides (row `X21`). Waiting: [packaging](packaging.md#open).

<a id="x22"></a>
### X22 — A version dir's `media/` beside `common/`
- Does a version dir shipping `media/` that collides with nothing still load, and does a shadowed `common/` copy ever execute? [#1288/C/open]
- The first half is settled for a version dir whose `media/` holds only the options file: run x222's options file read 1.5 [#3361/M/n=1].
- The measured arms had a collision or an empty version dir, so the inertness of a shadowed `common/` file stays un-run [#0835/M/n=2/open].
- Settles it: a mod whose `common/` and version dir each ship a colliding and a non-colliding file, with a sentinel only the shadowed copy can set (row `X22`). Waiting: [packaging](packaging.md#open).

<a id="x26"></a>
### X26 — `CleanUI`'s wrapper and an unguarded raise
- Does CleanUI's `pcall(triggerEvent, …)` wrapper change what an unguarded raise does inside a dispatch? Its runtime half is inferred from the code and never driven [#1292/C/open].
- It also settles [#1545/M/n=1/open] on [lua-platform](../platform/lua-platform.md#open).
- Settles it: a harness entry into the inventory context-menu builder and one session reading the wrapper's own failure line and whether the handlers behind the raise ran (row `X26`). Waiting: [packaging](packaging.md#open).

<a id="x27"></a>
### X27 — `InitLoadPP`'s net-id reallocation
- Does `InitLoadPP`'s per-body net-id reallocation ever put a stale id on the wire? [#1293/C/open]
- `Item.InitLoadPP` allocates a fresh net id per appended body, a jar reading with no measurement behind it [#1063/C/C-only/open].
- Settles it: a multiply-redefined item's id and full type read on both sides in the shared script-replay boot, where agreement bounds the risk (row `X27`). Waiting: [item-pass](item-pass.md#open), [mp-sync](mp-sync.md#open).

<a id="x31"></a>
### X31 — A dotted `OnCooked` name and the cooking pipeline
- Does a dotted `OnCooked` name fire, on which side, and can the cooking pipeline be driven end to end at all? [#1297/C/open]
- It also settles [#0778/C/C-only/open] and [#0784/C/snapshot/open] on [cooking-and-recipes](../facts/cooking-and-recipes.md#open), and [#0967/C/C-only/open] on [lua-platform](../platform/lua-platform.md#open).
- Settles it: a cook-transition session with a dotted target, then a harness craft command that reaches a crafted instance with the creation hook registered (row `X31`). Waiting: [eat-and-cook-hooks](eat-and-cook-hooks.md#open).

<a id="x34"></a>
### X34 — A reproducing `CalculateStats` handler against vanilla
- Does a `CalculateStats` handler that reproduces the seven skipped updaters from the library's formulas track vanilla's stat trajectory, stat by stat, over several game-hours on a live server? [#2081/C/open]
- Its asleep arm ran under a partial hold, about 15 % of stat updates awake: asleep thirst tracked vanilla's inside the band as a mixed-sample parity reading, fatigue and endurance sat at their floor and ceiling on a rested character, and the running arm only walked [#2841/M/n=2] [#2840/M/n=2].
- The arm needs a hold that wins at every stat update: `player.sleep.hold`'s once-per-tick re-assert loses about 15 % of updates to the client's reset [#2840/M/n=2].
- Settles it: two boots of one restored fixture, without and with the reproducing handler, sampling the seven stats hourly on the server against a per-stat band (row `X34`). Waiting: [character-stats](../facts/character-stats.md#open), [endurance-fatigue-sleep](../facts/endurance-fatigue-sleep.md#open).

<a id="x35"></a>
### X35 — The handler's endurance write and the push
- Is a `CalculateStats` handler's endurance write the last before the player-stats push, as the tick order reads? [#2082/C/open]
- No handler in the tree writes the sentinel, and the harness run command only walked [#2840/M/n=2].
- Vanilla's awake endurance reaches the client within about one push, no handler writing awake endurance (code inference; #3050's bound) [#3050/M/n=1]; one resting pair with the endurance fold on read the client's copy equal to the handler-written value a push earlier, with no running arm [#3079/M/n=1].
- Settles it: a handler writing a sentinel endurance each tick, read in client-first pairs at rest and while running, beside an arm with the handler removed (row `X35`). Waiting: [character-stats](../facts/character-stats.md#open), [endurance-fatigue-sleep](../facts/endurance-fatigue-sleep.md#open).

<a id="x36"></a>
### X36 — `Fitness.update` on the server
- Does `Fitness.update` tick on the server for a connected player? Its decay is open; the rep path is settled (#2879) [#2083/C/open].
- Settles it: a seeded exercise, then two game-days with none, reading the server's regularity for the fall the decay predicts (row `X36`). Waiting: [exercise-and-training](../facts/exercise-and-training.md#open).

<a id="x40"></a>
### X40 — The experience anti-cheat
- What is the experience anti-cheat's check interval, and does a server-side burst of grants trip it? Open for a non-admin connection [#2085/C/open]; on the admin connection a burst drew no kick and no line [#2873/M/n=1].
- A grant of 30000 through `addXp` on a user connection drew no kick over 130.5 s, trivial here because `addXp` re-seeds the checker after every grant [#3843/M/n=1].
- Settles it: a desk read of what enables the check, then above- and below-bound server-side bursts beside a console-grant control, timing the logged trips (row `X40`). Waiting: [perks-and-strength](../facts/perks-and-strength.md#open).

<a id="x45b"></a>
### X45b residual — QualityCooking's per-eat buff
- QualityCooking's per-eat effect stays unmeasured: a spawned Apple carries no cooking tier, so its handler calls the original and writes no buff, and the two wraps' composition was read without it [#2838/M/n=3].
- Settles it: a harness command that stamps `QualityCookingTier` into an item's modData on the server, then one eat of it with both wraps installed, reading QuestSystem's `cookingBuff` record (row `X45b`).

<a id="x47"></a>
### X47 — A client `WalkSpeed` write
- Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold? [#2096/C/C-only/open]
- Run x161p-20261006-035559 read the write gone by the first sample a quarter second after it, standing and in a walking arm whose movement was not confirmed, with no read-back in the writing tick [#3066/M/n=1].
- Settles it: a client write sampled in Lua every quarter second for four seconds, walking and standing, against the packet's cadence (row `X47`). Waiting: [perception-speed](../facts/perception-speed.md#open).

<a id="x48"></a>
### X48 — The side of the Strength protein branch
- Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value? Open for a client-originated hit or rep grant [#2087/C/open]; the server route is settled [#2872/M/n=1].
- Settles it: melee hits with the protein store raised on the server alone and then on the client alone, reading the Strength experience each hit grants (row `X48`). Waiting: [perks-and-strength](../facts/perks-and-strength.md#open).

<a id="x51"></a>
### X51 — The climate override on an outdoor thermoregulator
- Whether the climate override moves an outdoor character's air and core, and whether a hot exposure with activity raises the fluids multiplier above 1, is unmeasured: the one run stood the character where the air read 22.0 under both overrides [#2946/M/n=1/open]; the getters answer live on the server [#2935/M/n=1].
- Settles it: the climate override held over an outdoor character, idle and walking, reading the server's thermoregulator per tick (row `X51`). Waiting: [body-and-weight](../facts/body-and-weight.md#multipliers).

<a id="x59"></a>
### X59 — A script `OnEat` on the vitamin pill
- Whether a mod's script `OnEat` on `Base.PillsVitamins` runs on the server when the pill is taken is unmeasured [#2960/C/C-only/open]; the jar reads the call [#2955/C/C-only], and the pill action runs on the server [#2952/M/n=1].
- Settles it: a pill taken with a script `OnEat` assigned, counting its calls on both sides (row `X59`). Waiting: [eating-pipeline](../facts/eating-pipeline.md#pill-path).

<a id="x69"></a>
### X69 — An unbroken sleep and the mod's hours awake
- Whether an unbroken sleep resets the mod's hours awake live is unmeasured: under the harness's sleep hold `sleptH` read at most 0.3195 at the 35 reads, below the one-hour nap threshold, and `awakeH` never reset [#2992/M/n=1/open]; the window accounting, the debt and the impairment unit under the hold are settled [#2986/M/n=1, #2985/M/n=1].
- Settles it: a client-initiated sleep, or a hold that keeps every minute asleep for over an hour, reading `acute.awakeH` and `sleptH` (row `X69`). Waiting: [testing-your-mod](testing-your-mod.md#scenario-inputs).

<a id="x80"></a>
### X80 — Halved regeneration constants
- Whether halving the regeneration constants halves the awake tier's regeneration is unmeasured: both windows ran at hunger moodle level 4 [#3045/M/n=1/open]; the setters and getters answer and the values hold within a session, unsaved [#3020/C/inference].
- Settles it: a damaged part read in two windows, at the defaults and halved, with the hunger, thirst and sickness moodles low enough that the regeneration tier is not 3 [#2353/C/C-only] (row `X80`). Waiting: [health-surfaces](../facts/health-surfaces.md#regeneration).

<a id="x81"></a>
### X81 — A per-update TEMPERATURE target
- What steady core offset a TEMPERATURE target written on every update holds is unmeasured: the probe had no per-tick writer [#3047/M/n=1/open]; one write moves the core halfway at the next tick [#3046/M/n=1].
- At rest the core sat about 0.45 under the set point, so the mod's -0.2 target never acted [#3115/M/n=1] [#3100/M/n=1].
- Settles it: a per-tick writer of an absolute target for game hours, reading the core and the set point (row `X81`). Waiting: [health-surfaces](../facts/health-surfaces.md#thermal).

<a id="x86"></a>
### X86 — The aiming delay under a real aim
- Whether the post-shot sum, the per-update step and a write between shots behave as the jar reads while a player really aims is unmeasured [#3063/M/n=1/open]; a written aim flag does not hold and the delay then sits at the aiming time [#3062/M/n=1], and the three attack events fire on the shooting client [#3061/M/n=1].
- Settles it: an aim held by input with the delay below the aiming time, sampled per client tick across shots, with a write between shots (row `X86`). Waiting: [perception-speed](../facts/perception-speed.md#combat).

<a id="x105"></a>
### X105 — The cold fold on a catchACold rise
- Whether the mod's cold fold scales a catchACold rise on a live server is unmeasured [#3129/M/n=1/open]; sleep debt raised the cold multiplier to 2.5 at the next rebuild [#3099/M/n=1], and a cold climate override and a soaked character never lifted the thermoregulator's delta over the 0.1 the accrual needs, so the fold made no write [#3114/M/n=1].
- Settles it: an outdoor or wet-and-cold seat that lifts the catch-a-cold delta past the accrual's gate for game hours, reading catchACold with the fold on and off (row `X105`). Waiting: [health-surfaces](../facts/health-surfaces.md#poison-infection).

## See also

- [experiments.md](../reference/experiments.md) — the full spec of every named experiment, its sessions, splits, riders and cost.
- [overview.md#coverage](../platform/overview.md#coverage) — the surfaces the library touches but has no page for, each an open row above.
- The area pages whose `## Open` the decisions come from: [new-nutrients](new-nutrients.md), [item-pass](item-pass.md), [eat-and-cook-hooks](eat-and-cook-hooks.md), [mp-sync](mp-sync.md), [ui-and-moodles](ui-and-moodles.md), [packaging](packaging.md), [testing-your-mod](testing-your-mod.md), [body-effects](body-effects.md).
