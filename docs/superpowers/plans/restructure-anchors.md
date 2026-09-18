# Anchor plan — the owners a register row may name

Deliverable 0 of the harvest (spec § The target tree, "The anchor plan"). A row's `owner` is `<page>#<slug>` from this file. A harvester that needs an anchor this file lacks writes `<page>#<new-slug>` and lists it under `## Anchors proposed` in its coverage part; the merge task folds the proposals in here. From Phase 2 on, the page carries the anchors and this file is the writers' checklist.

Thirty-two `## <page>` sections, in the target tree's order: 8 `areas/`, 8 `platform/`, 7 `facts/`, 6 `facts/other-mods/` (the catalog included), and `reference/wall-map.md`, `reference/datasets.md` and `reference/tools.md`.

Rules: an anchor names one mechanism, one table or one reading; no anchor appears on two pages except the section anchors named below; `platform/overview.md` owns routing anchors only (no number of its own); a `facts/` page owns measured properties of the food, body or nutrition systems; an `areas/` page owns readings and options, never a mechanism; `reference/wall-map.md` owns exactly the 64 row ids.

**Section anchors.** Every page under the page contract carries `#walls` (its `## Walls and bounds`, where a `bound` row and a mirror `contradiction` row land) and `#open` (its `## Open`). Five pages differ and say so in their section: `platform/overview.md` has no `#walls` (its boundary is `#coverage`), `areas/open-questions.md` has neither (the page is the open list), `reference/wall-map.md` has neither (it is the 64 verdict rows and nothing else), `reference/datasets.md` and `reference/tools.md` carry `#open` but no `#walls` (the section shape of the page contract does not reach them). `#sandbox` is the anchor of a page's sandbox-option table and exists only where the page has one. `#procedure` is the anchor of a `## Procedure` section; a number under it carries no tag. The slugs that may therefore repeat across pages are `#walls`, `#open`, `#sandbox`, `#procedure` and the per-teardown set `#what-it-does`, `#architecture`, `#techniques`, `#pitfalls`, `#compat`, `#mp`. The page path disambiguates them and no two of them own the same claim.

**Reference owners.** A `reference/` page may own a row: the register's `owner` column names a page and an anchor, and the page contract governs section shape and prose caps, which is a separate question. `wall-map.md`, `datasets.md` and `tools.md` therefore have anchor lists here. The three remaining moved reads and the generated file — `artifacts.md`, `experiments.md`, `jar-method-notes.md`, `harness-commands.md` — do not: a harvester placing a row on one of them writes `reference/<page>.md#<slug>` and lists the slug under `## Anchors proposed`.

## areas/new-nutrients.md
- `#store-options` — the options table for where a mod nutrient can live: character modData, item modData, global modData, a parallel Lua store, a script key; cost, wall and tags per row
- `#sync-route` — the reading of which wire route each store forces, per option, citing the route and field rows it rests on
- `#persistence` — the reading of what each store survives: a save, a rejoin, a foreign `transmitModData`, an item that changes type
- `#effect-paths` — the options table for where a mod nutrient's effect can attach: the moodle surface, the weight model, the item pass, the eat hooks
- `#walls` — what a new nutrient cannot be given on this build, each line citing the mechanism row that closes it
- `#open` — the rows no run has settled and the decisions the design must take about consumers and clamps

## areas/item-pass.md
- `#route-options` — the options table for the four routes into a vanilla item's nutrition: a `module Base` re-declaration, a per-item override block, an eat or cook Lua hook, item modData
- `#minimal-block` — the reading of the smallest override block that changes one key, and why a whole re-declaration is not needed
- `#scope` — the reading of which records a `module Base` pass covers and what falls outside it, including mod-added foods; the counts are `reference/datasets.md`
- `#walls` — the pass's risks as walls: the identity reset on append, the same-path drop, the absent corpus precedent, the dataset unit traps, the display-name weight guard, X15 and X33
- `#open` — the decisions the pass forces (mod-added foods in or out) and the experiments that settle its unknowns

## areas/eat-and-cook-hooks.md
- `#hook-options` — the options table for hook sites: `OnEat`, a `server/` wrapper of `ISEatFoodAction.complete`, `OnCooked`, `OnCreate`; side, what each can still change, cost and wall
- `#side-choice` — the reading of which side a hook must sit on for its numbers to survive, and what a client-side arm can and cannot do
- `#seat-in-the-order` — the reading of which seats see pre-intake values and which see post-intake ones, citing the eat order block
- `#cook-seat` — the reading of where a cooking-side hook sits and what a type change does under it
- `#walls` — the hooks this build does not offer, each line citing the mechanism row that closes it
- `#open` — X24, X31 and X33, and the decisions each would settle

## areas/mp-sync.md
- `#sync-options` — the options table for the three routes mod state can travel: the command bus, `transmitModData`, script data loaded per side; cost, wall and tags per row
- `#authority` — the reading of which side this mod must own each quantity on, citing the ownership rows
- `#failure-modes` — the reading of how each route fails on a live server, citing the mechanism rows rather than restating them
- `#walls` — what no route offers this design, each line citing its wall-map row
- `#open` — the sync questions a run must settle before the design fixes a route

## areas/ui-and-moodles.md
- `#surface-options` — the options table for the three display surfaces: a client panel, a moodle through MoodleFramework, tooltip and translation text
- `#moodle-route` — the reading of MoodleFramework as the only route to a new moodle and what adopting it costs; the registry mechanism is `platform/lua-platform.md#registries`
- `#read-cadence` — the reading of cache on the push, not on the frame: what a client-side reader may draw from a once-a-second source
- `#honest-but-wrong` — the reading that a displayed number can be honest and still wrong, citing the staircase and cooked-thirst rows
- `#walls` — what the UI layer cannot do on this build, each line citing its wall-map row
- `#open` — X29 and the decisions the derived UI question forces

## areas/packaging.md
- `#layout` — the reading of this mod's folder shape: which files ship in the version dir, which in `common/`, and why
- `#checksum-plan` — the reading of what this mod does about the three gate arms, byte-identical files on both sides, X16
- `#resident-stack` — the reading of the mods that will sit beside it on a live server and what each of them touches
- `#compat-options` — the options table for compatibility approaches: shadow, `common/` split, a patch mod, do nothing
- `#shelf-life` — the reading that the stamp is a shelf life: monthly patches, corpus drift, what must be re-measured after a build bump
- `#walls` — the packaging limits this mod inherits, each line citing the mechanism row that closes it
- `#open` — the packaging decisions the design must take and the uninstalled Workshop neighbours that block them

## areas/testing-your-mod.md
- `#mod-profiles` — the profiles this mod ships, which fixture and mod list each pins, and what each one proves; the schema is `platform/harness.md#profiles`
- `#mod-scenarios` — the scenarios this mod runs and what each is evidence for
- `#verify-rows` — the `[[verify]]` probes this mod's profiles carry and what a failing probe means
- `#scenario-inputs` — the inputs a multi-day nutrition scenario needs (subject, sandbox, pacing, thirst management) and why each is fixed
- `#owned-experiments` — the experiments this mod owns (X4, X5, X13, X29): what each settles and what it costs
- `#grading` — the reading of how a cross-side comparison is graded: client-first reads, driver-side wall brackets, what a staircase does to a naive check
- `#sandbox` — the sandbox roll-up table: every option this mod's evidence depends on, with the value each run used
- `#walls` — what this plan cannot test on this machine, each with its bound
- `#open` — the measurements the plan still owes and the runs that would settle them

## areas/open-questions.md
> The page is the open list, so it carries neither `#walls` nor `#open`; a hole deliberately given no X id is a `bound` row on its wall-map row. The 26 `#x<n>` anchors below are the surviving named-experiment ids of `reference/experiments.md` § Named experiments, which holds each one's full spec.
- `#index` — the index table: one line per open row with its id, question, owner page, `-> X<N>` and the check that settles it
- `#decisions` — the decisions the design must take, each with the fact that forces it and no recommendation
- `#x2` — the index line for X2 (is `MoodleStat` reachable from Kahlua at all): question, owner, the settling check as a pointer
- `#x4` — the index line for X4 (does any packet carry character traits to a client): question, owner, the settling check as a pointer
- `#x5` — the index line for X5 (does a mod JSON displace a vanilla translation key): question, owner, the settling check as a pointer
- `#x7` — the index line for X7 (with vanilla nutrition off, which arm froze): question, owner, the settling check as a pointer
- `#x9b` — the index line for X9b (what the spice branch does beyond the herbal-tea sums): question, owner, the settling check as a pointer
- `#x13` — the index line for X13 (is the drink path interceptable the way the eat path is): question, owner, the settling check as a pointer
- `#x14` — the index line for X14 (does item modData move server to client): question, owner, the settling check as a pointer
- `#x15` — the index line for X15 (does a partial `item` block with `ItemType` omitted still merge): question, owner, the settling check as a pointer
- `#x16` — the index line for X16 (does a one-byte script mismatch kick a joining client): question, owner, the settling check as a pointer
- `#x17` — the index line for X17 (can Lua flip the nutrition sandbox option at runtime): question, owner, the settling check as a pointer
- `#x18` — the index line for X18 (what maps a mod's `server/` file into the client's Lua state): question, owner, the settling check as a pointer
- `#x19` — the index line for X19 (which string is the replay sort key): question, owner, the settling check as a pointer
- `#x20` — the index line for X20 (do two mods at the same relative path both load): question, owner, the settling check as a pointer
- `#x21` — the index line for X21 (does a `common/`-only `mod.info` resolve under the requested-id lookup): question, owner, the settling check as a pointer
- `#x22` — the index line for X22 (does a colliding-with-nothing version dir load, and is a shadowed `common/` file inert): question, owner, the settling check as a pointer
- `#x23` — the index line for X23 (how a release client behaves on an unguarded raise): question, owner, the settling check as a pointer
- `#x24` — the index line for X24 (does `OnEat` fire once per eat or once per portion): question, owner, the settling check as a pointer
- `#x25` — the index line for X25 (is the weight-lot flag ever true, and does the client copy agree): question, owner, the settling check as a pointer
- `#x26` — the index line for X26 (does a resident mod's `pcall` wrapper change what an unguarded raise does): question, owner, the settling check as a pointer
- `#x27` — the index line for X27 (does the per-body net-id reallocation ever put a stale id on the wire): question, owner, the settling check as a pointer
- `#x28` — the index line for X28 (does modData survive a save and reload): question, owner, the settling check as a pointer
- `#x29` — the index line for X29 (does MoodleFramework load whole and render a registered moodle): question, owner, the settling check as a pointer
- `#x30` — the index line for X30 (does a file-scope globals assignment change the drain): question, owner, the settling check as a pointer
- `#x31` — the index line for X31 (does a dotted `OnCooked` name fire, and on which side): question, owner, the settling check as a pointer
- `#x32` — the index line for X32 (does a stat-tick handler returning true really skip the updaters): question, owner, the settling check as a pointer
- `#x33` — the index line for X33 (does a cancelled eat under the partial-eating guard apply nothing at all): question, owner, the settling check as a pointer

## platform/overview.md
> Routing anchors only: this page owns no number except the two rows below, and carries no `#walls` because its boundary is `#coverage`.
- `#surfaces` — the four surfaces a mod touches (scripts, Lua, translations, packets) and what each can carry
- `#two-lua-states` — the server VM and the client VM, the join-time Lua reset, and that a mod's `server/` file executes in both
- `#one-server` — what the server owns, one sentence per quantity, each linking `mp-model.md#ownership`
- `#process-model` — launch, join, RCON and admin commands: the shape of the session a mod runs inside
- `#coverage` — the coverage table of general topics as covered, touched or absent, each touched and absent row carrying the `open` row that records the boundary
- `#routing` — which page owns which mechanism: the table an agent reads before it reads anything else
- `#open` — routing questions the tree has not settled, such as a topic with rows and no page

## platform/mod-anatomy.md
- `#mod-info-keys` — every `mod.info` key and what the loader does with it
- `#load-order-declarations` — `Mods=` and `require=`: what each declaration does and does not guarantee
- `#mod-discovery` — how the game finds mod folders under Steam and under `-nosteam`
- `#id-chain` — the declared id, which `mod.info` the live chain reads, and one id per folder
- `#version-dirs` — the version folder against `common/`: the file-level merge, which file wins a same-relative-path collision, what an empty version dir costs
- `#folder-name` — the folder name against the declared id, and which of the two `Mods=` takes
- `#translations` — how mod translation tables are merged rather than shadowed, and which layout is never loaded
- `#missing-mod` — what a missing mod or a failed version gate does at load and at join, and what the error text does not tell you
- `#build-pinning` — pinning a mod to a build: the version keys, what the gate compares, what a mod can detect at runtime
- `#join` — the join reset of `default.txt` against the server's `Mods=`
- `#checksum-gate` — all three arms (script, Lua, anim), the CR normalisation, the load-ordered MD5, the bypass role and the AntiCheat timeout
- `#client-only-mods` — a mod that loads on one side only: what that costs and what still reaches the other side
- `#walls` — anatomy limits and their bounds, each line citing the mechanism row that closes it
- `#open` — the anatomy rows no run has settled

## platform/loader-and-scripts.md
> 16 anchors under a 400-line prose cap: if the Phase 2 writer needs the split, the file-map group (`#file-map`, `#lua-load-order`, `#path-collisions`, `#per-side-load`) moves to a sibling page and the register is retargeted by delta.
- `#file-map` — `activeFileMap`: the two unconditional passes, the `overrides` line, one absolute path per relative path
- `#lua-load-order` — `LoadDirBase`'s walk and vanilla-first dedupe, and how `require` resolves through the merged map
- `#script-dsl` — the script grammar: `module` and `item` blocks, comment stripping, brace tolerance
- `#craft-recipe-grammar` — the `craftRecipe` block: inputs, outputs and the keys a mod may set, general to any mod
- `#file-list` — `searchFolders` and the stored lower-cased script path that later orders the replay
- `#bucket-append` — a repeated name appends a body to the bucket and the script reset is a bare return
- `#per-key-merge` — a partial `item` block merges per key, last body wins per key
- `#sorted-replay` — bodies replay sorted by the stored script path, independent of `Mods=` position, with the `template_` pre-sort
- `#path-collisions` — two mods at one relative script path: which is dropped and what the loader reports
- `#default-moddata` — the default modData arm of the item parser and what a custom key inside a vanilla block does
- `#identity` — `InitLoadPP`, the net id and `fileName`: what a re-declaration does to an item's identity
- `#name-resolution` — a bare script name against a module-qualified lookup
- `#per-side-load` — script data loads per side and never crosses the wire, so a script value is identical on both sides for free
- `#reload` — what a script reload does in a running session and what it does not
- `#walls` — the loader's limits and their bounds, including X15, X19, X20 and X27
- `#open` — the loader rows no run has settled

## platform/lua-platform.md
- `#kahlua-limits` — what the Kahlua dialect does not have and what each absence costs a mod
- `#pcall` — what `pcall` catches, including a nil call on a Java member
- `#raises` — what an unguarded raise aborts and what survives it, per side
- `#debug-break` — the `-debug` client's modal break on an unguarded mod error
- `#java-members` — reaching a Java member from Lua: index-first access, arity, overloads and the exposure test
- `#script-hooks` — how `OnEat`, `OnCooked` and `OnCreate` resolve, which side calls each, what the client-side twin does not apply, and where a `server/` wrapper of a timed action sits
- `#events` — the events this library exercised and what each one guarantees
- `#hooks` — the `Hook.*` surface: what a hook trigger replaces and what it cannot
- `#registries` — `MoodleType` and `CharacterTrait`: what registration gives a mod and what it does not, including the two moodle walls
- `#removed-apis` — the APIs removed on this build and what stands in for each
- `#file-io` — what Lua may read and write, on which side
- `#dev-loop` — `reloadlua` and the rest of the in-session dev loop
- `#walls` — Lua-side limits whose mechanism has no other home, each with its bound
- `#open` — the Lua-platform rows no run has settled

## platform/mp-model.md
- `#ownership` — which side owns each quantity and what the other side holds instead
- `#shapes` — the shapes mod state can travel in (a packet field, a modData table, a command payload) and what each costs
- `#routes-client-to-server` — the routes that exist from the client and what each will not carry
- `#routes-server-to-client` — the routes that exist from the server and the cadence each runs at
- `#packets` — the packet mechanisms: which packets carry food and player state, when each fires, what a send does not wait for; the field lists are `facts/wire-packets.md`
- `#cached-packet` — one cached packet object per type with no reset, and what a stale field reads as
- `#item-moddata` — how item modData moves, whole-table, and when
- `#player-moddata` — the player modData table: what it holds at join, what appears later, and why a census is per scope
- `#wipe-and-replace` — `transmitModData` in both directions and the wire-safe types
- `#command-bus` — `sendClientCommand` and `sendServerCommand`: the one route a mod fully controls
- `#what-a-client-copy-is` — what a client's copy of a server object is and is not: the push, the gate, the direction flags
- `#walls` — what no route offers, each line citing its wall-map row
- `#open` — the MP rows no run has settled

## platform/harness.md
- `#pzt` — the `pzt` commands and what each one proves
- `#profiles` — the profile schema: fixture, mod list, sandbox block, verify rows
- `#sandbox` — the sandbox block: how options are merged into a run and which of them change a reading
- `#driven-client` — the driven client: what it is, what it runs with, and what it cannot be asked to do
- `#bus` — the command-bus protocol: how a command is registered, called and answered
- `#reading-a-reply` — the reply-reading rules: the three buckets, the empty-list shape, `resolved`, the limit BREAK, the `null` guard
- `#probes` — probe design: per-scope exclusion sets, client-first pairs, the re-ask-once guard; the witness contract and its `field_count` assert are `#witness`
- `#witness` — the witness contract: `witness.fields` and `witness.moddata`, zero-argument getters only, the three buckets, the `field_count` assert a driver makes against a reply
- `#scenarios` — the scenario layer and what a scenario may assume
- `#cadence` — the cadence ceiling: what a driver may ask for per game-hour
- `#time` — game time against real time, and the day-length setting every reading depends on
- `#artifacts-discipline` — artifacts committed byte-identical, a driver never edited after its run, a do-not-cite key never quoted
- `#driver-rules` — driver discipline: the house driver shape, predictions and verdicts, how a falsified or trivial reading is written
- `#experiment-contract` — the standing rules for a named experiment (owner, cost, riders, merges); the specs themselves are `reference/experiments.md`
- `#walls` — what the instrument cannot yet measure, each with the reason
- `#procedure` — the numbered steps from profile to scenario to driver to evidence
- `#open` — the harness rows no run has settled

## platform/lessons.md
- `#rules` — the KEEP rules: one imperative each, tagged with the mechanism row it rests on
- `#anti-patterns` — the FILTER rules: what the corpus does that this mod will not
- `#testing-discipline` — the testing lessons: the staircase before the ramp, the six clauses, the riders, the doubled grep limit, the classifier
- `#corpus-drift` — the workshop corpus drifts, so every count is dated
- `#measure-the-mechanism` — measure the mechanism, not the mirror
- `#walls` — rules that hold only inside their bound, each naming it
- `#open` — the lessons a later run would confirm or overturn

## platform/jar-research.md
- `#reading-the-jar` — the disassembler's subcommands and what each does and does not tell you
- `#method` — reverse callers, access flags, inner classes, and offsets written `Class.method @off L<n>` and re-located by content
- `#exposed` — the exposer dump as the exposure test and what it does not cover
- `#walls` — what a jar read cannot settle, each with its bound
- `#procedure` — the numbered steps for answering a question from the jar; the disassembler lives in `C:\Users\Angus\pz-b42` and is not part of this repository
- `#open` — the jar questions this library left unread

## facts/eating-pipeline.md
- `#getters` — the getters and setters the pipeline reads and writes, and what each name means
- `#eat` — the order of writes inside `Eat`, as one annotated block whose claim is the order
- `#modifiers` — the modifier ladder: every multiplier an intake passes through, as one table
- `#partial` — partial eating: the rescaled fraction and what the remainder keeps
- `#fluid-path` — the drink path and the per-litre chain: what a fluid container's numbers mean
- `#eat-type` — what the eat action does with `EatType` and `Eattime`: animation, utensil, sound, the duration override; the keys themselves are `facts/food-item-model.md#script-keys`
- `#duration` — how the eat duration is computed and why a reading must not depend on it
- `#script-scale` — the script-to-instance scale, stated once on the page's worked example
- `#sandbox` — the `Nutrition` sandbox option: what it gates and what keeps running when it is off
- `#walls` — the pipeline's bounds and the mirror contradictions its numbers correct
- `#open` — the eat-path rows no run has settled

## facts/food-item-model.md
- `#state-axes` — the axes an item's state moves on, and which are stored against which are derived
- `#dead-setters` — the setters that write nothing on this build
- `#script-keys` — the script keys and what the loader does with each, as one table
- `#poison` — the poison fields and what reads them
- `#walls` — the item model's bounds and the mirror contradictions its numbers correct
- `#open` — the item-model rows no run has settled

## facts/spoilage.md
- `#formula` — the aging formula and the rot thresholds, and that rot is a view of age rather than a mutation
- `#containers` — fridge, freezer and frozen: what each multiplies and when electricity matters
- `#spawn-age` — the age an item spawns with and the spawn-time rot roll
- `#sealed` — sealed cans, the `ReplaceOnUse` and `ReplaceOnRotten` transitions, and the `ReplaceOn*` links a dataset cannot resolve
- `#writes` — which side writes age and how often the server ticks an item
- `#measured` — the measured aging rates per arm, as one table, each with the run it rests on
- `#sandbox` — the rot sandbox options and their defaults
- `#walls` — spoilage bounds and the mirror contradictions its numbers correct
- `#open` — the spoilage rows no run has settled

## facts/cooking-and-recipes.md
- `#cook-block` — the cook block: the heat gates, the cook and burn branches, as one annotated block
- `#uses` — recipe IO and the uses-not-items rule, measured per use
- `#evolved` — evolved-recipe summation: what a dish banks from each ingredient
- `#evolved-join` — the resolution rules that decide which items an evolved recipe accepts
- `#type-change` — the deltas a type change applies, as one table, and what cooking alone does not move
- `#walls` — cooking bounds and the mirror contradictions its numbers correct
- `#open` — the cooking rows no run has settled

## facts/body-and-weight.md
- `#time-unit` — the time unit every rate on this page is stated in
- `#passive-burn` — the passive burn branches and the rate of each
- `#hunger-thirst` — how hunger and thirst accumulate, including the sleeping arm
- `#multipliers` — the multipliers applied to hunger, thirst and burn
- `#fill-times` — how fast each stat fills from empty, as one table derived from the rates
- `#coupling` — how hunger and calories are coupled and where they are not
- `#moodles` — the moodle thresholds and what drives each
- `#weight-bands` — the weight bands and their comparison edges
- `#weight-traits` — the traits a weight band applies and what each one does
- `#traits` — the traits with live readers in the nutrition path
- `#sandbox` — the body-side sandbox options and their defaults
- `#walls` — body bounds and the mirror contradictions its numbers correct
- `#open` — the body rows no run has settled

## facts/nutrition-core.md
- `#weight-model` — the weight model as one annotated block: what each macro contributes per tick
- `#clamps` — the store clamps on calories and on the three macros
- `#verified` — the three-day server verification: what was predicted, what was measured, how close the two came
- `#macro-effects` — what each macro does once stored and which of them has no live consumer
- `#walls` — nutrition-core bounds and the mirror contradictions its numbers correct
- `#open` — the nutrition-core rows no run has settled

## facts/wire-packets.md
- `#item-stats-packet` — the item packet's field contract: which food getters it reads and which it omits
- `#player-stats-packet` — the player packet's field contract: what it declares and what it never carries
- `#moddata-packet` — the modData packet's type bytes: which Lua values survive the wire
- `#cooked-thirst` — the cooked-food thirst value the packet sends against the one the server applied
- `#desyncs` — the measured desyncs, per field and per arm, each with the run it rests on
- `#staircase` — the once-a-second staircase a client-side reader sees, and how to read one
- `#walls` — what the wire cannot carry, and the bound on every per-arm measurement
- `#open` — the wire rows no run has settled

## facts/other-mods/autocook.md
- `#what-it-does` — what the mod does in play, as facts rather than a review
- `#architecture` — its file layout, entry points and where its logic runs
- `#data-model` — the state it keeps, where it keeps it, and what it does at load
- `#techniques` — the techniques worth stealing, one line each
- `#pitfalls` — what it gets wrong or pays for, each line citing the mechanism row that explains it
- `#compat` — what it collides with and what a nutrition mod must do about it
- `#mp` — its multiplayer behaviour, citing `facts/wire-packets.md` rows and restating none
- `#open` — what the teardown did not settle

## facts/other-mods/longtermpreservation.md
- `#what-it-does` — what the mod does in play, as facts rather than a review
- `#architecture` — its file layout, entry points and where its logic runs
- `#techniques` — the techniques worth stealing, one line each
- `#pitfalls` — what it gets wrong or pays for, each line citing the mechanism row that explains it
- `#compat` — what it collides with and what a nutrition mod must do about it
- `#mp` — its multiplayer behaviour, citing `facts/wire-packets.md` rows and restating none
- `#open` — what the teardown did not settle

## facts/other-mods/simplestatus.md
- `#what-it-does` — what the mod does in play, as facts rather than a review
- `#architecture` — its file layout, entry points and where its logic runs
- `#techniques` — the techniques worth stealing, one line each
- `#pitfalls` — what it gets wrong or pays for, each line citing the mechanism row that explains it
- `#compat` — what it collides with and what a nutrition mod must do about it
- `#mp` — its multiplayer behaviour, citing `facts/wire-packets.md` rows and restating none
- `#open` — what the teardown did not settle

## facts/other-mods/beyondten.md
- `#what-it-does` — what the mod does in play, as facts rather than a review
- `#architecture` — its file layout, entry points and where its logic runs
- `#techniques` — the techniques worth stealing, one line each
- `#pitfalls` — what it gets wrong or pays for, each line citing the mechanism row that explains it
- `#compat` — what it collides with and what a nutrition mod must do about it
- `#mp` — its multiplayer behaviour, citing `facts/wire-packets.md` rows and restating none
- `#open` — what the teardown did not settle

## facts/other-mods/itemquality.md
- `#what-it-does` — what the mod does in play, as facts rather than a review
- `#architecture` — its file layout, entry points and where its logic runs
- `#techniques` — the techniques worth stealing, one line each
- `#pitfalls` — what it gets wrong or pays for, each line citing the mechanism row that explains it
- `#compat` — what it collides with and what a nutrition mod must do about it
- `#mp` — its multiplayer behaviour, citing `facts/wire-packets.md` rows and restating none
- `#open` — what the teardown did not settle

## facts/other-mods/catalog.md
- `#sweep` — the dated sweeps: what was searched, when, and what each one returned
- `#status` — the B42 status table: which mods are current, which are stale, which are not installed
- `#api-surface` — the API surface the corpus uses, as one table
- `#corpus-facts` — corpus-level facts: counts, conventions, and what no mod in the corpus does
- `#walls` — what the survey cannot see, each with its snapshot date
- `#open` — the corpus questions a re-sweep would settle

## reference/wall-map.md
> One anchor per map row, 64 in all, outside the page contract: the row's `Ev` cell carries the register ids. A merged row's anchor hyphenates its ids, so row `A2+A7` is `#a2-a7` and a register row citing `A7` names `#a2-a7`.
- `#a1` — row `A1` CANNOT: add a field to the Java `Nutrition` object
- `#a2-a7` — row `A2+A7` CAN: a parallel per-player nutrient store, server-side, that persists
- `#a3` — row `A3` CAN WITH A WORKAROUND: keep the mod's nutrient in player modData
- `#a4` — row `A4` CAN: per-item nutrient values in the item script
- `#a5` — row `A5` CAN: a custom key inside a vanilla `item` block
- `#a6` — row `A6` CAN WITH A WORKAROUND: per-item nutrient values in item modData
- `#a8` — row `A8` CAN: turn vanilla nutrition off and own the macro model
- `#b1` — row `B1` CAN: run the intake math where `Eat` runs
- `#b2` — row `B2` CAN WITH A WORKAROUND: intercept before vanilla's numbers land
- `#b3` — row `B3` CAN WITH A WORKAROUND: correct after the fact from `OnEat`
- `#b4-b5` — row `B4+B5` CANNOT: have one `OnEat` handler fire once in MP, or wrap `complete` client-side
- `#b6` — row `B6` CAN: handle a partial or cancelled eat
- `#b7` — row `B7` UNKNOWN: hook the drink path the way the eat path is hooked
- `#b8` — row `B8` CAN: skip vanilla's whole stat tick and run our own
- `#c1` — row `C1` CANNOT: change the thresholds or rates inside the weight update
- `#c2` — row `C2` CAN WITH A WORKAROUND: replace the weight model wholesale
- `#c3-c6` — row `C3+C6` CAN: write weight, and apply the band traits, from Lua
- `#c4` — row `C4` CANNOT: let the client compute weight
- `#c5` — row `C5` CAN: read the weight-direction flags client-side
- `#d1` — row `D1` CANNOT: register a new `MoodleType` that works
- `#d2-d3` — row `D2+D3` CANNOT: retune an existing moodle's thresholds, or change what a moodle does
- `#d4` — row `D4` CAN WITH A WORKAROUND: render a mod nutrient as a moodle
- `#d5` — row `D5` CAN: get a moodle to the other side
- `#e1-e2` — row `E1+E2` CANNOT: add a field to the item packet, or depend on a field it omits
- `#e3` — row `E3` CAN WITH A WORKAROUND: get a per-item mod value to the client anyway
- `#e4` — row `E4` CANNOT: trust a zero-valued packet field
- `#e5` — row `E5` CANNOT: trust a cooked food's thirst change client-side
- `#e6` — row `E6` CANNOT: trust a live item field's client copy to tick
- `#e7-e12` — row `E7+E12` CANNOT: push a player stat client to server, or observe or suppress the player-stats write
- `#e8` — row `E8` CANNOT: push an item field client to server
- `#e9` — row `E9` CAN WITH A WORKAROUND: server-authoritative state in player modData
- `#e10` — row `E10` CANNOT: transmit part of player modData
- `#e11` — row `E11` CAN: move mod state over the command bus
- `#f1` — row `F1` CAN: rewrite a crafted instance from `OnCooked`
- `#f2-f3` — row `F2+F3` CANNOT: change vanilla's cooking gates, timers or evolved-recipe perk scaling
- `#f4` — row `F4` CAN: set per-item cook times
- `#f5` — row `F5` CAN: control spice behaviour
- `#g1-g6` — row `G1+G6` CAN WITH A WORKAROUND: add a new trait that is selectable, saved, and does something
- `#g2` — row `G2` CANNOT: change a vanilla appetite trait's multiplier
- `#g3` — row `G3` CAN: add or remove a trait from Lua
- `#g4` — row `G4` UNKNOWN: rely on a weight-band trait client-side
- `#g5` — row `G5` CANNOT: use the string-argument trait test or the item type-string getter
- `#h1` — row `H1` CAN: ship mod translations beside vanilla's
- `#h2` — row `H2` UNKNOWN: override a vanilla translation key
- `#h3` — row `H3` CANNOT: use a B41-layout item-name translation file
- `#h4` — row `H4` CANNOT: ship a food absent from the translation table
- `#h5-h6` — row `H5+H6` CANNOT: resolve or branch on an item name outside the client's display name
- `#i1-i6` — row `I1+I6` CAN: replace a vanilla Lua file at its own relative path, and `require` across the merged map
- `#i2` — row `I2` CAN WITH A WORKAROUND: retune hunger and thirst through the globals table
- `#i3` — row `I3` CAN: ship `common/` beside a version folder
- `#i4-i5` — row `I4+I5` CAN: rely on the `mod.info` id-read order, and install under a folder whose name is not the declared id
- `#i7` — row `I7` CANNOT: use `loadstring`
- `#i8` — row `I8` CAN WITH A WORKAROUND: coexist with a second mod shadowing the same Lua file
- `#i9` — row `I9` CAN WITH A WORKAROUND: keep server-only logic in the `server/` folder
- `#i10` — row `I10` CANNOT: have two mods both load a file at the same relative script path
- `#i11` — row `I11` CANNOT: replace only part of a shadowed Lua file
- `#i12` — row `I12` CANNOT: diagnose a build gate from the loader's error text
- `#i13` — row `I13` CAN: catch a Kahlua nil call with `pcall`
- `#i14` — row `I14` CAN WITH A WORKAROUND: survive an unguarded raise
- `#j1` — row `J1` CAN: redefine a vanilla `module Base` food block
- `#j2` — row `J2` CAN WITH A WORKAROUND: do it across every `base:food` item and its drainable and fluid-container records
- `#j3` — row `J3` CANNOT: survive an MP script mismatch
- `#j4` — row `J4` CAN: rely on the replay order
- `#j5` — row `J5` CANNOT: assume a redefinition leaves the item's identity alone

## reference/datasets.md
> Outside the page contract's section shape, but an owner like any other page: it carries `#open` and no `#walls`.
- `#columns` — the column authority for `data/*`: `nutrition_source`, `nutrition_basis` and what each value means, the per-litre fluid join, the `*_per_container` derivations, absent against zero, and which columns are derived rather than read
- `#kinds` — the four `kind` buckets (`food`, `drainable`, `fluid_container`, `fluid`) and the first-match selection rule that assigns them
- `#counts` — every dated dataset count: foods, drinkables, fluid containers, fluids, recipes, evolved recipes, and the scan stamp each one rests on
- `#mod-inventory` — the corpus snapshot's columns, the `live_media` and `media_at` partial-view caveat on any zero, and the sweep stamp
- `#workshop-rows` — the workshop search's row shape and what a not-installed row can and cannot be used for
- `#schemas` — the CSV and JSON split per dataset, and which of the two is authoritative for a given field
- `#fidelity-links` — pointers to the `facts/` rows that measured the datasets against the game; owns no number of its own
- `#open` — the dataset questions a re-scan or a measurement would settle

## reference/tools.md
> Outside the page contract's section shape, but an owner like any other page: it carries `#open` and no `#walls`.
- `#doc-lint` — `doc_lint.py`: the stamp rule, the `Ev`-grade rule, the placeholder rule, what it skips and where it still runs after the cut
- `#mod-lint` — `mod_lint.py`: the nine rules with their engine standing, five error, three warn, one info, and which of them is a measured statement rather than a convention
- `#mod-inventory-tool` — `mod_inventory.py`: what it walks, what it records per mod, and why every run is a dated snapshot
- `#food-scan` — `food_scan.py`: the parser API, the comment-stripping rule, and the selection call the datasets rest on
- `#recipe-scan` — `recipe_scan.py`: what it reads from the recipe and evolved-recipe scripts and what it leaves unresolved
- `#workshop-search` — `workshop_search.py`: the query surface and the three row states a result can be in
- `#wiki-mirror` — `wiki_mirror.py`: how a mirror is fetched, stamped and re-read, and what a mirror may be cited for
- `#claims-tools` — `claimslib.py`, `claims_harvest.py`, `claims_check.py`, `bus_inventory.py` and `luabalance.py`: conventions, exit codes and when each must run; their rules are the spec's, not this page's
- `#conventions` — the conventions every tool here shares: argument shape, exit codes, where output lands, and the dated-count rule
- `#open` — the tool questions a later change would settle
