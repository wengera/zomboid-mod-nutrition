# Platform overview
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: where a question about this build is routed — the four surfaces a mod reaches the game through, the two Lua states a multiplayer session runs, what the server owns, the shape of the session a mod runs inside, which page owns which mechanism, and what this library never read; every number lives on the page this one names for it.

## Rules

- Ask the routing table which page owns a mechanism before reading any page: a mod reaches the game through four surfaces only, and the command bus is the one sanctioned client-to-server path for anything the engine does not sync [#0888/C/C-only].
- Read the owner page before restating any number from it: the verdicts this page routes to are bounded to one build on a dedicated server with one client, one fixture and one admin character, and single player is never claimed [#1256/C/one-fixture].
- Treat a topic the coverage table marks absent as unknown rather than as a wall: the surface this library carries holds a row only where it used or measured the thing, so an absence is a coverage boundary and never a statement that the API does not exist [#0887/W/one-side].
- Check which branch a wall-map verdict took before quoting it as measured: six rows of the set that rests on the live platform sessions are classified from code alone, and every other row of that set is graded on its own run and artifact key [#1257/C/C-only].
- Decide which Lua state a file runs in from the loader rather than from its folder name: a mod's `media/lua/server/` files execute in the multiplayer client's state as well as the server's, and the side field, the per-side minute counter and the eat-hook wrapper flag all read client-side in the session that found it [#0854/M/n=1].
- Expect every file-scope side effect to run twice on a client: the server runs one Lua state and the client two, so each per-file loader line is printed twice there as well [#0878/M/n=1].
- Size a client-side log grep at no less than twice the predicted count: one mod's override block appeared twice in the client console and once in the server's, so a limit set at the predicted count saturates on the first block and truncates the second [#1762/M/n=1].
- Put the mod under test in the server's own mod list: the server's list is authoritative and the client reloads its Lua with it on join, so a client-side mod the server does not name is not in the session at all [#1824].
- Never call the remote console's help command: it throws a format exception inside the server's translator and logs two error lines [#1872].
- Drive the primary test client as the server's bootstrap admin whenever the logo must be skipped: the logo state is added unless the debug flag and a named debug option are both set, and servers accept the debug flag only for admin accounts [#1854].
- Stand a session up through the orchestrator's server side rather than by hand: it seeds the configuration file, installs the mods, starts the dedicated server without Steam, waits for the started banner, classifies the error-shaped log lines and stops the process cleanly [#1788].
- Budget an automated join for three character-creation screens: each is advanced by the same option handler, the spawn screen needs a valid list selection, and the appearance screen initialises the player and enters the world [#1855/C/C-only].
- Read the confirmed launch surface before adding a launch argument: it already fixes how a client auto-connects, how a dedicated server is started, what the remote console needs and which admin commands exist as classes [#1843].
- Seed universal plug-and-play off and keep a golden world to restore from: router detection otherwise runs on every boot, and a whole server fixture is small enough that a snapshot and a restore per run cost nothing [#1848].
- Expect neither a server browser nor a username launch argument on an automated join: the client's join surface is a fixed set of established facts about the connect argument, the enabled-mods file, the saved-server database and the creation route [#1852].


## How it works

This page routes; it does not explain: each mechanism below is stated with its numbers, grade and bound on exactly one other page, and this page names that page.
Four questions route any question about a mod on this build: which surface it reaches the game through, which Lua state the code runs in, which side owns the quantity it changes, and what the session allows; the routing table they resolve to follows them, and the coverage table names what this library never read.

<a id="surfaces"></a>
### The four surfaces

A mod reaches the game through four surfaces: engine events registered per Lua state at file scope, Java members reached by indexing, script-side hooks resolved by name out of the Lua global table, and the command bus, which is the only sanctioned client-to-server path for anything the engine does not sync [#0888/C/C-only].

| Surface | Who owns it | How a mod reaches it |
|---|---|---|
| **Events** (`Events.<Name>.Add/Remove`) | the engine, per Lua state | register at file scope; the state you land in is decided by the loader, not by the folder name |
| **Java members** | the jar; Kahlua publishes *methods*, never fields | index the member, then call it |
| **Script-side hooks** (`OnEat`, `OnCooked`, `OnCreate` in an item block) | the item script; resolved by NAME out of the Lua global table | define a **global** function |
| **The command bus** (`sendClientCommand` / `sendServerCommand`) | the mod | the only sanctioned client→server path for anything the engine does not sync |

The table is read from code alone, and the state a file scope lands in is decided by the loader, not by the folder the file sits in [#0888/C/C-only].
Events, Java members and script hooks are [`lua-platform.md`](lua-platform.md); the command bus is [`mp-model.md`](mp-model.md) for the mechanism and [`harness.md`](harness.md) for the instrument built on it.
Whether the engine loads a file at all, and in which order, is [`mod-anatomy.md`](mod-anatomy.md) and [`loader-and-scripts.md`](loader-and-scripts.md).
A mod that writes item data rather than code uses none of the four: a script file is the load-time definition both sides start from, its grammar on [`loader-and-scripts.md`](loader-and-scripts.md) and its item keys on [`../facts/food-item-model.md`](../facts/food-item-model.md).
Display text is [`mod-anatomy.md#translations`](mod-anatomy.md#translations), a packet's fields are [`../facts/wire-packets.md`](../facts/wire-packets.md), and the mod's own identity — whether its folder is found, which file supplies its id, whether its content matches the server's — is [`mod-anatomy.md`](mod-anatomy.md).

<a id="two-lua-states"></a>
### The two Lua states

The server runs one Lua state and the client two, so a mod's file-scope side effects run twice on a client and every per-file loader line is printed twice there [#0878/M/n=1].
The two client states are the main-menu one and the in-session one, both inside one process, and engine load output is printed once per state [#1762/M/n=1].
A mod's `media/lua/server/` files execute in the multiplayer client's Lua state as well as the server's: on the client the shared table's side field read `server`, the per-side minute counter read 58 on the client against 38 on the server, and the eat-hook wrapper flag read true client-side [#0854/M/n=1].
That reading is incidental to its session and the mechanism is untraced, so it is an observation and not a code path; the folder under `media/lua/` is a naming convention and not a deployment boundary [#0854/M/n=1].
A global written by a file under `server/` is therefore present in a client's own state, so a census that assumes a single writer reads two.
A client-side log grep must expect twice the predicted count: one mod's five-line override block appeared at client console lines 85 to 89 and again at 168 to 172, identical tails in identical order, each preceded by its own loading line, while the server printed the block once [#1762/M/n=1].
The client also discards its Lua and reloads it with the server's mod list on connect, which is stated at [the session](#process-model) and under [`## Open`](#open); the mod-list side is [`mod-anatomy.md#join`](mod-anatomy.md#join).
Which file runs at all — the file map, the execution list, per-side loading and the reload — is [`loader-and-scripts.md`](loader-and-scripts.md), and the runtime side test that survives both states is a rule on [`lessons.md`](lessons.md).

<a id="one-server"></a>
### One server, one owner per quantity

A session is one dedicated server process and one or more clients, and each quantity a nutrition mod touches has one owning side; every number, cadence and bound behind the list is at [`mp-model.md#ownership`](mp-model.md#ownership).

- The server owns the eat: a multiplayer client never reaches the eat action's completion step, so nothing hung off the client side of that path runs [#0110, #0109].
- The server owns the nutrition object, and a multiplayer client holds a mirror of it [#0125/M/one-fixture].
- The server owns the calorie store and the three macro stores, which reach the client as a push [#0898/M/n=1].
- The server owns hunger and thirst, and a client write to either is erased by the next snapshot [#0123/M/n=1].
- The server owns endurance [#2596/C/C-only] and fatigue [#0562/C/C-only].
- The server owns the body-weight write and the weight-band trait refresh, while the computation runs on both sides and the client throws its result away [#0559/M/n=1].
- Neither side owns the moodles: each recomputes them from its own stats, and they are absent from the player-stats packet [#1245/C/C-only].
- The server owns a food item's whole lifecycle, because the container hooks that fire on an add or a remove are gated on the process being a server [#0327].
- The server owns the cook transition, whose hook prints land in the server console with the client's empty [#1417/M/n=1].
- A skill level crosses by character sync rather than by either item packet, so it is visible to the next client read with no wait [#0353/M/n=1].
- The server owns the session's mod list, stated at [the session](#process-model).

So a mod's own numbers are computed where the eat completes, on the server, and a client display reads a mirror that is never authoritative and never a place to write [#0110, #0125/M/one-fixture].
An owner is not a writer (a quantity the client computes and discards is still the server's), a route is not an owner (a skill level travels on character sync), and a quantity with no owner is computed on both sides with neither authoritative [#0559/M/n=1, #0353/M/n=1, #1245/C/C-only].
The routes and packet timing are [`mp-model.md`](mp-model.md); each packet's fields and measured desyncs are [`../facts/wire-packets.md`](../facts/wire-packets.md).

<a id="process-model"></a>
### The session a mod runs inside

A mod runs inside a dedicated server started with a fixed argument set and client processes that joined it through a fixed sequence of screens; a process-model question is about one of four moments: the server's launch (which mods exist, what the log looks like), the client's launch (what the client can be driven into), the join (which Lua the client ends up running) and the admin surface (what changes without a restart).

Eleven facts about the game's own launch surface are what the pipeline design stands on: a client auto-connects from launch arguments with no server browser, Lua can join directly through exposed connect calls, several client instances need a cachedir each plus no Steam and never safe mode, the dedicated server is a named Java class with a fixed argument set, remote console exists with its port and password in the server options, admin commands are classes including the two Lua reloads, a time multiplier setter exists so nutrition ticks scale with game-world seconds, structured output from Lua is possible through the file writers, multiplayer character creation is Lua interface with characters persisting per account server-side, the server world lives in three named places, and the dynamic compiler is gone [#1843].
They are wiki and jar readings taken before the live spikes, on one build: the design's starting point, not a measured result [#1843].

The server side seeds its own configuration file with the ports, the remote-console settings, the mod list, an open flag and universal plug-and-play turned off, installs mods into the cachedir's mods folder, starts the dedicated server without Steam and with an admin password, waits for the server-started banner, classifies error-shaped log lines against the vanilla-noise baseline with stack frames attached to their head line, and stops with a quit on standard input, falling back to the remote console [#1788].
Five boot-spike facts changed the design: the server's own log file in the cachedir is not the client's console file name, the admin-password argument bootstraps the admin account non-interactively, router detection runs unless universal plug-and-play is seeded off, a no-Steam launch works cleanly, and a whole server fixture is about fifteen megabytes so a golden-world snapshot and restore per run is trivially cheap [#1848].
The server's mod list is authoritative and the client inherits it: the client reloads its Lua with the server's list on join, so its own enabled list matters only until the first join, and a client-side mod the server does not name is not in the session [#1824].

Sixteen facts about the client's launch and join surface were established by the join spike, from the connect argument landing on the connect popup with no server browser, through the absence of any username launch argument, the connect button's own call, the terms-screen version line, the state-transition markers, the enabled-mods file shape, the saved-server database, the character-creation route and the auto-connect popup that never presses connect, to the launcher's elevation prompt and implicit account creation on an open no-Steam server [#1852].
That spike ran eight attempts on one machine and one build, and four of its entries carry rows of their own: the first-launch mods reset, the logo skip, the debug refusal for a non-admin account and the three-screen creation flow [#1852].
The logo state is added unless the debug flag and a named debug option are both set, the option living in a key-value debug file in the cachedir — so the roughly twenty-second logo is skippable only for debug clients, which servers accept only for admin accounts, and no non-debug launch argument exists for it [#1854].
Multiplayer character creation is three screens and not the cooperative ones, each advanced by the same option handler: the spawn screen needs a valid list selection, the profession screen has no checks, and the appearance screen initialises the player, saves the account's names and enters the world; it is a Lua reading driven once by the join spike, not a measured sequence [#1855/C/C-only].

The remote console's help command throws a format exception inside the server's translator and logs two error lines, so it is never called [#1872].
The time-speed admin command is under [`## Open`](#open): its only evidence is a run that committed no artifact.
How a session is driven — the orchestrator, the profile, the sandbox block, the driven client, the bus and a reply — is [`harness.md`](harness.md), with the generated inventory at `reference/harness-commands.md`; what the game does with the mod list at each launch and the join, and the checksum gate that turns a script mismatch into a disconnect, are [`mod-anatomy.md`](mod-anatomy.md) and [`mod-anatomy.md#checksum-gate`](mod-anatomy.md#checksum-gate).
The admin surface has no page of its own; its boundary row is under the coverage table.

<a id="routing"></a>
### Which page owns which mechanism

Read this table before anything else: each row names one page, what it owns, and the anchors a question usually lands on; a number is stated once, on its owner page, and every other page cites it by tag.

| Page | What it owns | Anchors a question lands on |
|---|---|---|
| [`mod-anatomy.md`](mod-anatomy.md) | what a mod folder is: `mod.info` and its keys, discovery, which file supplies the id, the version dir against `common/`, translations, the missing-mod and version-gate failures, the join, the checksum gate, a one-sided mod | `#mod-info-keys`, `#mod-discovery`, `#id-chain`, `#version-dirs`, `#folder-name`, `#translations`, `#load-order-declarations`, `#missing-mod`, `#build-pinning`, `#join`, `#checksum-gate`, `#client-only-mods` |
| [`loader-and-scripts.md`](loader-and-scripts.md) | how a relative path becomes one file, how the Lua execution list is built, the `item` and `craftRecipe` grammars, and the block-level merge inside a script file | `#file-map`, `#lua-load-order`, `#script-dsl`, `#craft-recipe-grammar`, `#file-list`, `#bucket-append`, `#per-key-merge`, `#sorted-replay`, `#path-collisions`, `#default-moddata`, `#identity`, `#name-resolution`, `#per-side-load`, `#reload` |
| [`lua-platform.md`](lua-platform.md) | the Lua a mod runs inside: the dialect's gaps, what a protected call catches, what an unguarded raise costs, how a Java member is reached, how the script hooks resolve, the event surface, the registries, the removed APIs | `#kahlua-limits`, `#pcall`, `#raises`, `#debug-break`, `#java-members`, `#script-hooks`, `#events`, `#hooks`, `#registries`, `#removed-apis`, `#file-io`, `#dev-loop` |
| [`mp-model.md`](mp-model.md) | which side owns each quantity, the routes state can travel, when each packet fires, which pushes the server sends and to whom, what the receiver holds in between, and what a client's copy is and is not | `#ownership`, `#shapes`, `#routes-client-to-server`, `#routes-server-to-client`, `#packets`, `#sync-globals`, `#cached-packet`, `#item-moddata`, `#player-moddata`, `#wipe-and-replace`, `#command-bus`, `#what-a-client-copy-is` |
| [`harness.md`](harness.md) | the instrument every measured row here was taken with: the orchestrator, the profile, the sandbox block, the driven client, the bus and reply reading, probes, the witness, scenarios, cadence, artifact and driver discipline | `#pzt`, `#profiles`, `#sandbox`, `#driven-client`, `#bus`, `#reading-a-reply`, `#probes`, `#witness`, `#scenarios`, `#cadence`, `#time`, `#artifacts-discipline`, `#driver-rules`, `#experiment-contract`, `#procedure` |
| [`lessons.md`](lessons.md) | the standing rules this library leaves behind, with the page each rule rests on named beside it | `#rules`, `#anti-patterns`, `#testing-discipline`, `#corpus-drift`, `#measure-the-mechanism` |
| [`jar-research.md`](jar-research.md) | how a question about the game's Java becomes a citable claim: the disassembler's subcommands, absence, callers, access flags, offsets, the exposer dump | `#reading-the-jar`, `#method`, `#exposed`, `#procedure` |
| [`server-lifecycle.md`](server-lifecycle.md) | what a dedicated server does and fires when a player joins, is created, dies and leaves, how a player is addressed on the server, where per-player and world state is stored, and the order of the server's time events in a frame | `#join`, `#creation`, `#death`, `#ids`, `#player-store`, `#global-moddata`, `#tick-order`, `#disconnect` |
| [`sandbox-options.md`](sandbox-options.md) | a mod's own sandbox options: the declaration file and its grammar, the `SandboxVars` mirror and the option's name, the translation keys and the settings pages, the join sync, a change during a running session, and the server's own sandbox file | `#declaration`, `#lua-mirror`, `#translations`, `#sync`, `#runtime-change`, `#server-file` |
| [`client-ui.md`](client-ui.md) | the client-side interface a mod builds: the panel toolkit, window geometry and the layout file, keybinds and the mod-options API, textures, the inventory-item tooltip, the character-info window, the UI events and their cadence, and the Java UI classes a mod can read | `#panel-toolkit`, `#layout`, `#keybinds`, `#textures`, `#tooltip`, `#character-info`, `#cadence`, `#java-surface` |
| [`performance.md`](performance.md) | what a dedicated server frame is and what a mod's work costs inside it: the loop and its catch-up, the frame's order and its clock events, the scheduling primitives, the clocks and the engine's frame counter, Lua tables and the collector, the packet pass and a send, the global modData save and request, how to budget a change and the measured costs | `#budget`, `#frame`, `#frame-order`, `#scheduling`, `#levers`, `#clocks`, `#gc`, `#packets`, `#network`, `#global-moddata`, `#costs`, `#measure`, `#procedure` |
| [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md) | what a food item or a fluid container delivers when it is eaten or drunk: the getters, the fraction, the modifier ladder, the leftover, the drink path, the duration, the sandbox gate | `#getters`, `#eat`, `#modifiers`, `#partial`, `#fluid-path`, `#eat-type`, `#duration`, `#script-scale`, `#sandbox` |
| [`../facts/food-item-model.md`](../facts/food-item-model.md) | what a food item is: its state axes, the setters that write nothing, the item-level script keys, the poison fields, the shipped dataset's fidelity | `#state-axes`, `#dead-setters`, `#script-keys`, `#fluid-blocks`, `#poison`, `#dataset-fidelity` |
| [`../facts/spoilage.md`](../facts/spoilage.md) | what moves an item's age, what freezing and refrigeration multiply it by, what rot changes, which side owns the clock, and the sealed items with no clock | `#formula`, `#containers`, `#spawn-age`, `#sealed`, `#writes`, `#measured`, `#sandbox` |
| [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md) | the cook and burn transitions, what a craft recipe's inputs cost, the evolved-recipe summation and its join, and the nutrition delta of a type change | `#cook-block`, `#uses`, `#evolved`, `#evolved-join`, `#type-change`, `#craft-split`, `#butchering`, `#dataset-fidelity` |
| [`../facts/body-and-weight.md`](../facts/body-and-weight.md) | what the body does with the stores between meals: passive burn, hunger, thirst, the moodles, the weight bands and the traits that scale them | `#time-unit`, `#passive-burn`, `#metabolic-rate`, `#hunger-thirst`, `#multipliers`, `#fill-times`, `#coupling`, `#moodles`, `#weight-bands`, `#weight-traits`, `#traits`, `#sandbox` |
| [`../facts/nutrition-core.md`](../facts/nutrition-core.md) | the nutrition object's stores, the weight model that reads them, the clamps that bound them and the multi-day server check of that model | `#weight-model`, `#clamps`, `#verified`, `#macro-effects` |
| [`../facts/character-stats.md`](../facts/character-stats.md) | the registered character stats and the stats API, the seven updaters the stat hook skips and what each does beyond its stat, and one server update of a player up to the hook | `#registry`, `#updaters`, `#tick-order` |
| [`../facts/endurance-fatigue-sleep.md`](../facts/endurance-fatigue-sleep.md) | what moves a player's endurance and fatigue: the drain, the regeneration, the event writers, awake fatigue, sleep, the moodles the two stats drive and the setters a mod has against them | `#drain`, `#regen`, `#writers`, `#fatigue`, `#sleep`, `#moodles`, `#setters` |
| [`../facts/perks-and-strength.md`](../facts/perks-and-strength.md) | the Strength and Fitness perks: the level and experience stores, every experience write and its gates, the level writes and their events, the Java readers of the two levels, carry capacity, the experience anti-cheat, skill rust and the band-trait remap | `#stores`, `#xp-grants`, `#level-writes`, `#events`, `#readers`, `#carry-capacity`, `#anti-cheat`, `#skill-rust`, `#trait-remap` |
| [`../facts/exercise-and-training.md`](../facts/exercise-and-training.md) | the fitness object, its ten-minute tick, regularity, the per-rep experience, endurance and soreness, the exercise action's path to the server, and every shipped grant of Strength or Fitness experience | `#fitness-object`, `#exercise-path`, `#training-signals` |
| [`../facts/perception-speed.md`](../facts/perception-speed.md) | the rendered and the server view cones, night vision, hearing range, movement speed and its server-side formula, combat speed, melee and aiming delay, and the perception traits the engine reads | `#vision-cone`, `#server-visibility`, `#night-vision`, `#hearing`, `#speed`, `#combat`, `#dynamic-traits` |
| [`../facts/health-surfaces.md`](../facts/health-surfaces.md) | what a mod can drive in the body-damage model: overall and per-part health, regeneration, the severe-moodle drain, poison and infection, pain, wounds and healing, the mood moodles and the thermal door | `#health-api`, `#regeneration`, `#severe-drain`, `#poison-infection`, `#pain`, `#wounds`, `#mood-surface`, `#thermal` |
| [`../facts/wire-packets.md`](../facts/wire-packets.md) | which food and nutrition getters each packet reads, which it omits, and every desync measured per field and per arm | `#item-stats-packet`, `#player-stats-packet`, `#player-fields-packet`, `#experience-packet`, `#injuries-packet`, `#body-part-packet`, `#moddata-packet`, `#eat-food-packet`, `#cooked-thirst`, `#desyncs`, `#staircase` |
| [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) | what the installed workshop corpus and the public Workshop hold on the nutrition surface: the dated sweeps, per-candidate build status, the API surface and the corpus-level counts | `#sweep`, `#status`, `#api-surface`, `#corpus-facts` |
| [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) | a client-only mod split across `common/` and a version folder: what it does, the state it keeps, and what it collides with | `#what-it-does`, `#architecture`, `#data-model`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md) | a preservation mod's two cook hooks, and which of its techniques and failures to copy or avoid | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) | a pure client-side viewer of the player's status numbers: what it draws, how it is built, and the one call it makes that crosses the wire | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/beyondten.md`](../facts/other-mods/beyondten.md) | a stat the Java engine does not know about, layered on character modData, and what its three delivery mechanisms cost | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/itemquality.md`](../facts/other-mods/itemquality.md) | per-item mod values on crafted items, and why stat buffs written into live Java fields do not survive a dedicated server | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/moodleframework.md`](../facts/other-mods/moodleframework.md) | a client-side moodle widget library: its registration surface, the value it draws, its version-folder layout, its data model and its missing multiplayer surface | `#what-it-does`, `#architecture`, `#data-model`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |

Three boundaries catch most misroutes.
Whether a file loads at all is `mod-anatomy.md`; what happens to the blocks inside a loaded file is `loader-and-scripts.md`.
When a packet fires, what the receiver caches and what a transmit replaces is `mp-model.md`; the field lists and the measured desyncs are `facts/wire-packets.md`.
An engine fact a mod teardown found is a platform or facts row the teardown page cites; the teardown page owns only what that mod does.

The same routing by task shape:

- Whether a file loads, in what order and from which folder: [`mod-anatomy.md`](mod-anatomy.md), then [`loader-and-scripts.md`](loader-and-scripts.md) once it loads.
- Whether Lua may do a thing at all: [`lua-platform.md`](lua-platform.md), ending at `reference/wall-map.md` when the answer is no.
- What the other side holds: [`mp-model.md`](mp-model.md) for the route, [`../facts/wire-packets.md`](../facts/wire-packets.md) for the fields.
- A number the game computes: the `facts/` page whose mechanism owns it, never this one.
- A character stat, a perk level, endurance, fatigue, health or perception: [`../facts/character-stats.md`](../facts/character-stats.md), then the facts page that owns the stat; what a mod's own state can make the body do is [`../areas/body-effects.md`](../areas/body-effects.md).
- A player joining, being created, dying or leaving, how a player is addressed, and where per-player and world state is stored: [`server-lifecycle.md`](server-lifecycle.md).
- A sandbox option a mod declares: [`sandbox-options.md`](sandbox-options.md); a vanilla option is on the page it gates.
- A panel, a keybind, a tooltip line or a character-info tab: [`client-ui.md`](client-ui.md), and what a panel may believe about its number: [`mp-model.md`](mp-model.md).
- What a change costs the server's frame and how to measure it: [`performance.md`](performance.md); the order of the time events: [`server-lifecycle.md#tick-order`](server-lifecycle.md#tick-order).
- How to measure anything: [`harness.md`](harness.md); a question nothing here measured: [`jar-research.md`](jar-research.md).
- What another mod already does: [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md), then that mod's own page.
- What this mod should do about an answer: the `areas/` tree, which restates no mechanism.

A number quoted from any of these pages travels with its tag, which carries its grade, bound and status; a bounded number is true inside its bound and unknown outside it, and an unverified tag is listed under its page's open section and never quoted as a fact.

## Coverage
<a id="coverage"></a>

`platform/` is not a modding manual.
It holds what this library measured or read while building a nutrition mod on a dedicated `42.20.4` server with one client, and in one session a second, release client beside it [#3298/M/n=1].
Every verdict in the wall map is bounded to build `42.20.4` on a dedicated server with one client, one fixture and one admin character, and single-player is never claimed [#1256/C/one-fixture].
The full event roster lives on the wiki and the full command inventory lives in the testing reference: the curated Lua surface carries a row only where this library used or measured it, so an absence in it is a coverage boundary and never a statement that the API does not exist [#0887/W/one-side].
Every wall-map row that rests on the live platform sessions took one of three branches — the artifact settles it and the row is graded M on that run id and key, the artifact is inconclusive and the row states the verdict the remaining evidence supports, or the artifact is missing and the row is classified from C alone — so the C-only rows of that set are `H2`, `G4`, `I8`, `I10`, `I11` and `J5` [#1257/C/C-only].

| Topic | Status | Where |
|---|---|---|
| the eating and drinking pipeline | covered | [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md) |
| the food item model | covered | [`../facts/food-item-model.md`](../facts/food-item-model.md) |
| spoilage, freezing and rot | covered | [`../facts/spoilage.md`](../facts/spoilage.md) |
| cooking and recipes | covered | [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md) |
| the body, hunger, thirst and weight | covered | [`../facts/body-and-weight.md`](../facts/body-and-weight.md) |
| the nutrition store and the weight model | covered | [`../facts/nutrition-core.md`](../facts/nutrition-core.md) |
| the food and nutrition wire packets | covered | [`../facts/wire-packets.md`](../facts/wire-packets.md) |
| mod anatomy and the loader | covered | [`mod-anatomy.md`](mod-anatomy.md), [`loader-and-scripts.md`](loader-and-scripts.md) |
| the Lua platform and its dialect | covered | [`lua-platform.md`](lua-platform.md) |
| the multiplayer model | covered | [`mp-model.md`](mp-model.md) |
| the test harness | covered | [`harness.md`](harness.md) |
| reading the jar | covered | [`jar-research.md`](jar-research.md) |
| the workshop corpus and its teardowns | covered | [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) |
| the server's player lifecycle and global modData | covered | [`server-lifecycle.md`](server-lifecycle.md) |
| sandbox options a mod declares | covered | [`sandbox-options.md`](sandbox-options.md) |
| the UI framework | covered | [`client-ui.md`](client-ui.md) |
| server performance and the frame | covered | [`performance.md`](performance.md) |
| the character stats and their updaters | covered | [`../facts/character-stats.md`](../facts/character-stats.md) |
| endurance, fatigue and sleep | covered | [`../facts/endurance-fatigue-sleep.md`](../facts/endurance-fatigue-sleep.md) |
| perks and experience | covered | [`../facts/perks-and-strength.md`](../facts/perks-and-strength.md) |
| exercise and training | covered | [`../facts/exercise-and-training.md`](../facts/exercise-and-training.md) |
| perception and movement speed | covered | [`../facts/perception-speed.md`](../facts/perception-speed.md) |
| the health, wound and thermal surfaces | covered | [`../facts/health-surfaces.md`](../facts/health-surfaces.md) |
| timed actions | touched | rows on [`../facts/body-and-weight.md`](../facts/body-and-weight.md#passive-burn); no page |
| the crafting pipeline | touched | rows only; no page |
| server admin and remote console | touched | rows only; no page |
| build detection | touched | rows only; no page |
| client-only mods | touched | rows only; no page |
| the events roster | touched | rows only; no page |
| sounds | absent | nothing was read |
| tiles and sprites | absent | nothing was read |
| vehicles | absent | nothing was read |
| world and map mods | absent | nothing was read |
| Workshop publishing | absent | nothing was read |
| the save format | absent | nothing was read |
| vanilla food sources | absent | planned as a vanilla page and never written |
| cooking experience gain | absent | planned as a vanilla page and never written |
| the cooking interface | absent | planned as a vanilla page and never written |

Read the table by status.
`covered`: a page states each row with its grade and bound, and only its answer may be quoted as this library's.
`touched`: rows exist, scattered across the pages that needed them; the answer is partial, and the topic's boundary row below says where it stops.
`absent`: the surface was never opened and carries no row, by design (the three vanilla pages were planned and never written); the answer names the jar or the wiki mirror as the next step and infers nothing from the silence.
Neither a `touched` nor an `absent` gap is a statement about the game.

The pages added for three topics carry boundary rows of their own:
- The sandbox options a mod declares have a page of their own: [`sandbox-options.md`](sandbox-options.md) reads the declaration file and its grammar, the `SandboxVars` mirror, the join sync and a change during a running session with its replication, from the code and not on a live server, while the vanilla options stay on the pages they gate [#2738/C/C-only].
- The user-interface framework has a page of its own: [`client-ui.md`](client-ui.md) reads the panel toolkit, the tooltip and character-info wrap points, the UI events and their cadence and the Java UI classes a mod can read, from the code and not on a live client, beside the two corpus teardowns of a framework mod and a viewer mod [#2739/C/C-only].
- Server performance has a page of its own: [`performance.md`](performance.md) reads the server frame, the scheduling primitives, the clocks, garbage collection, a send and the global modData save from the bytecode, and prices the frame and the slow minute with two-player live readings and a ghost load, while every figure for a large player count stays arithmetic [#3448/C/C-only].

Each touched topic's boundary row:
- Timed actions: the eat and drink actions are read end to end and the multiplayer action manager's route into them is traced, while the action queue, its tick budget and how a mod adds an action of its own are unread [#2045/M/one-side/open].
- The crafting pipeline: the craft-recipe grammar, what an input really costs and the output's inherited state are stated on the loader and cooking pages, while the crafting interface, the handcraft action and the recipe-discovery surface are unread [#2046/C/one-side/open].
- Server admin and the remote console: the console's transport, the one admin command this library drove and the one that throws are stated here, while the admin command set as a whole and what each does to a running world are unread [#2047/C/one-side/open].
- Build detection: the version keys and what the availability gate compares are stated on the anatomy page, while what a mod can detect about the running build from inside Lua is unread [#2048/C/one-side/open].
- Client-only mods: one workshop mod is torn down as a pure client-side viewer and a second as a client-only cooking helper, while the general cost of shipping one side only, and what still reaches the other side, is stated as anatomy rather than as a topic of its own [#2049/M/n=1/open].
- The events roster: the events this library hooked and measured are stated on the Lua platform and harness pages, while the full roster and which events fire on a dedicated server were never enumerated here [#2051/C/one-side/open].

## Open
<a id="open"></a>

- That the client resets its Lua with the server's mod list on connect, dropping locally enabled mods, so that a client-side harness must survive a mid-flow reset with its stages keyed on screen visibility and its manifest re-read from disk, is unverified: its only evidence is a spike run over eight attempts on one machine and one build that committed no artifact folder; re-measure by joining with a client-side mod the server does not name and censusing the client's loaded mods before and after the connect, in a run whose artifact is committed [#1856/M/uncommitted/unverified].
- That the time-speed admin command sets the server's multiplier and broadcasts a multiplier packet to every client, works over the remote console, needs no debug flag, and that at a multiplier of thirty both sides ran at about thirty-two times real time with calorie burn scaling with it, is unverified: both spike runs committed no artifact folder; re-measure by driving the command over the remote console and taking paired clock and calorie readings on both sides in a run whose artifact is committed [#1868/M/uncommitted/unverified].
- Whether a `touched` topic gets a page of its own or stays a boundary row — settled by a pass that reads the rows each topic carries and decides whether they make a page.
- Decision: whether a mod's own code is allowed to live under `media/lua/server/` at all, or whether every file goes in a shared folder with an explicit runtime side test — the folder is not a deployment boundary and both copies run on a client [#0854/M/n=1, #0878/M/n=1].
- Decision: whether this tree carries an admin-and-remote-console page of its own — the one admin command the library drove is unverified and the console's help command is unusable, so the surface is presently two rows and a boundary [#1868/M/uncommitted/unverified, #1872].

## See also

- [`mod-anatomy.md`](mod-anatomy.md) and [`loader-and-scripts.md`](loader-and-scripts.md) — whether a file loads, the Lua execution list and the merge inside a script file.
- [`lua-platform.md`](lua-platform.md) — the dialect, Java members, script hooks and events.
- [`mp-model.md`](mp-model.md) and [`../facts/wire-packets.md`](../facts/wire-packets.md) — the ownership table, the routes and the field contracts behind every push.
- [`harness.md`](harness.md) and [`../reference/harness-commands.md`](../reference/harness-commands.md) — the instrument that stands a session up and its generated command inventory.
- [`lessons.md`](lessons.md) — the standing rules, the runtime side test included.
- [`jar-research.md`](jar-research.md) — how a question this tree does not answer becomes a citable claim.
- [`performance.md`](performance.md) — what a mod's work costs the server's frame.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) — what the corpus does with the same surfaces.
- [`../reference/experiments.md`](../reference/experiments.md) — the experiments that settle the open rows.
