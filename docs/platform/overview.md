# Platform overview
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: where a question about this build is routed — the four surfaces a mod reaches the game through, the two Lua states a multiplayer session runs, what the server owns, the shape of the session a mod runs inside, which page owns which mechanism, and what this library never read; every number lives on the page this one names for it.

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

This page routes; it does not explain.
Every mechanism below is owned by exactly one other page, which states it with its numbers, its grade and its bound, and this page says only which page that is and what shape the answer takes.
Four things decide the routing of any question about a mod on this build: which surface the mod would reach the game through, which Lua state the code would run in, which side owns the quantity it would change, and what the session the mod runs inside allows.
The coverage table below closes the page by naming what this library never read at all, so that an absent answer is recognisable as absent rather than guessed.
The reading order from a cold start is this page, then the page the routing table names, then whichever page that one hands off to; nothing below needs to be read in full.
Those four questions are the first four subsections below, and a task will usually match one of them and none of the others; the fifth subsection is the routing table they resolve to.

<a id="surfaces"></a>
### The four surfaces

A mod reaches the game through four surfaces: engine events registered per Lua state at file scope, Java members reached by indexing, script-side hooks resolved by name out of the Lua global table, and the command bus, which is the only sanctioned client-to-server path for anything the engine does not sync [#0888/C/C-only].

| Surface | Who owns it | How a mod reaches it |
|---|---|---|
| **Events** (`Events.<Name>.Add/Remove`) | the engine, per Lua state | register at file scope; the state you land in is decided by the loader, not by the folder name |
| **Java members** | the jar; Kahlua publishes *methods*, never fields | index the member, then call it |
| **Script-side hooks** (`OnEat`, `OnCooked`, `OnCreate` in an item block) | the item script; resolved by NAME out of the Lua global table | define a **global** function |
| **The command bus** (`sendClientCommand` / `sendServerCommand`) | the mod | the only sanctioned client→server path for anything the engine does not sync |

That table is read from code alone, and the qualification it carries is the one that routes the rest of this page: the state a file scope lands in is decided by the loader, not by the folder the file sits in [#0888/C/C-only].
Each surface has one owner page.
The event surface, the Java-member surface and the script-hook surface are [`lua-platform.md`](lua-platform.md), which holds the dialect's gaps, what a protected call catches, how a member is reached and how each hook resolves.
The command bus is [`mp-model.md`](mp-model.md) for the mechanism and [`harness.md`](harness.md) for the instrument built on it.
Which file supplies a surface at all — whether the engine ever loads it, and in which order — is [`mod-anatomy.md`](mod-anatomy.md) and [`loader-and-scripts.md`](loader-and-scripts.md).
A mod that writes item data rather than code reaches the game through none of the four, because a script value is the load-time definition both sides start from rather than anything reached at runtime.

Those four are how a mod reaches the engine.
A different four decide what a mod can carry into a running session, and they are worth naming separately because each has a different owner page and a different failure mode.
A script file carries item and recipe data, which is the load-time definition both sides start from; the grammar is [`loader-and-scripts.md`](loader-and-scripts.md) and the item keys are [`../facts/food-item-model.md`](../facts/food-item-model.md).
Lua carries behaviour, and which state it lands in is the loader's decision rather than the folder's; the dialect and its limits are [`lua-platform.md`](lua-platform.md).
A translation table carries display text, is built independently on each side, and is effectively empty on a dedicated server, so nothing server-side may branch on one; the merge is [`mod-anatomy.md#translations`](mod-anatomy.md#translations).
A packet carries live state between the two sides, and what a mod may and may not do to one is [`mp-model.md`](mp-model.md) for the mechanism and [`../facts/wire-packets.md`](../facts/wire-packets.md) for the field lists.
The fifth thing a mod carries is the identity of the mod itself, which is neither code nor data: whether the folder is found, which file supplies its id and whether its content matches the server's is [`mod-anatomy.md`](mod-anatomy.md).

<a id="two-lua-states"></a>
### The two Lua states

The server runs one Lua state and the client two, so a mod's file-scope side effects run twice on a client and every per-file loader line is printed twice there [#0878/M/n=1].
The two client states are the main-menu one and the in-session one, both inside one process, and engine load output is printed once per state [#1762/M/n=1].
A mod's `media/lua/server/` files execute in the multiplayer client's Lua state as well as the server's: on the client the shared table's side field read `server`, the per-side minute counter read 58 on the client against 38 on the server, and the eat-hook wrapper flag read true client-side [#0854/M/n=1].
The folder under `media/lua/` is therefore a naming convention and not a deployment boundary, and the only reliable side test is a runtime one.
That reading is incidental to the session that produced it and the mechanism behind it is untraced, so the mapping that puts a `server/` file into the client's state is stated as an observation and not as a code path [#0854/M/n=1].
Both facts have the same practical consequence for anything that reads a log.
A client-side log grep must expect twice the predicted count: one mod's five-line override block appeared at client console lines 85 to 89 and again at 168 to 172, identical tails in identical order, each preceded by its own loading line, while the server printed the block once [#1762/M/n=1].
A limit set at the predicted count therefore saturates on the first block, truncates the second and reads as a pass.
The join adds a third reset to the same picture: the client discards its own Lua and reloads it with the server's mod list on connect, which is stated at [one server](#one-server) and under [`## Open`](#open), and the mod-list side of that reset is [`mod-anatomy.md#join`](mod-anatomy.md#join).
Everything else about which file runs at all — the file map, the execution list, per-side loading and the in-session reload — belongs to [`loader-and-scripts.md`](loader-and-scripts.md), and the guard a mod writes to survive all of this is a rule on [`lessons.md`](lessons.md).

Three consequences follow, and each has caught a reading in this library.
A file-scope registration is per state, so a handler written once is installed twice on a client and once on the server, and a per-tick counter reads accordingly.
A global written by a file under `server/` is present in a client's own state, so a census that assumes a single writer reads two.
A count taken off a client log is a count of states as much as of events, so it is either compared against a doubled prediction or not compared at all.
The defensive shape that survives all three is a runtime side test rather than a folder, written so that it is itself safe when the side global is absent, and it is a rule on [`lessons.md`](lessons.md).

<a id="one-server"></a>
### One server, one owner per quantity

A multiplayer session on this build is one dedicated server process and one or more client processes, and every quantity a nutrition mod touches has exactly one side that computes it.
The sentences below name the owner and nothing else; each number, each cadence and each bound lives at [`mp-model.md#ownership`](mp-model.md#ownership).

The server owns the eat: a multiplayer client never reaches the eat action's completion step, so nothing a mod hangs off the client side of that path runs at all ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0110, #0109].
The server owns the nutrition object, and a multiplayer client holds a mirror of it ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0125/M/one-fixture].
The server owns the calorie store and the three macro stores, which reach the client as a push ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0898/M/n=1].
The server owns hunger and thirst, and a client write to either is erased by the next snapshot ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0123/M/n=1].
The server owns endurance ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0561].
The server owns fatigue ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0562/C/C-only].
The server owns the body-weight write and the weight-band trait refresh, while the computation itself runs on both sides and the client throws its result away ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0559/M/n=1].
Neither side owns the moodles: each recomputes them from its own stats, and they are absent from the player-stats packet ([`mp-model.md#ownership`](mp-model.md#ownership)) [#1245/C/C-only].
The server owns a food item's whole lifecycle, because the container hooks that fire on an add or a remove are gated on the process being a server ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0327].
The server owns the cook transition, whose hook prints land in the server console with the client's empty ([`mp-model.md#ownership`](mp-model.md#ownership)) [#1417/M/n=1].
A skill level crosses by character sync rather than by either item packet, so it is visible to the next client read with no wait ([`mp-model.md#ownership`](mp-model.md#ownership)) [#0353/M/n=1].
The server owns the session's mod list too, and what the client inherits on join is stated at [the session a mod runs inside](#process-model).

Two consequences of that list decide most designs before any code is written.
A mod's own numbers must be computed where the eat completes, which is the server, and a client-side implementation of the same maths has no path to run on.
A client-side display is reading a mirror, so it is never authoritative and never a place to write.
What the routes are, when each packet fires and what the receiver holds in between is [`mp-model.md`](mp-model.md); which fields each packet actually carries and every measured per-field desync is [`../facts/wire-packets.md`](../facts/wire-packets.md).

Two distinctions in that list are the ones an agent gets wrong.
An owner is not a writer: a quantity the client computes and then discards is still the server's, and the owner page says which of the two the client is doing.
A route is not an owner either: some quantities reach the other side on a packet named for them and at least one reaches it on character sync instead, so the route is asked for separately from the ownership.
Where a quantity has no owner at all, both sides compute it and neither is authoritative, which is a third answer and not a missing one.

<a id="process-model"></a>
### The session a mod runs inside

A mod on this build never runs alone: it runs inside a dedicated server process that was started with a fixed argument set, and inside client processes that joined it through a fixed sequence of screens.
The shape of that session decides what a test can do and what an admin can do to a running world, so it is stated here once and cited from the pages that depend on it.
There are four moments in a session a mod can be affected by, and a question about the process model is always about one of them: the server's launch, the client's launch, the join, and whatever an admin does to the world afterwards.
The server's launch decides which mods exist at all and what the log will look like; the client's launch decides what the client can be driven into; the join decides which Lua the client ends up running; and the admin surface decides what can be changed without a restart.

Eleven facts about the game's own launch surface are what the pipeline design stands on: a client auto-connects from launch arguments with no server browser, Lua can join directly through exposed connect calls, several client instances need a cachedir each plus no Steam and never safe mode, the dedicated server is a named Java class with a fixed argument set, remote console exists with its port and password in the server options, admin commands are classes including the two Lua reloads, a time multiplier setter exists so nutrition ticks scale with game-world seconds, structured output from Lua is possible through the file writers, multiplayer character creation is Lua interface with characters persisting per account server-side, the server world lives in three named places, and the dynamic compiler is gone [#1843].
That list is a set of readings taken from the wiki and the jar before the live spikes, on one build, so it is the design's starting point rather than a measured result [#1843].

The server side of a session is stood up the same way every time.
The server side seeds its own configuration file with the ports, the remote-console settings, the mod list, an open flag and universal plug-and-play turned off, installs mods into the cachedir's mods folder, starts the dedicated server without Steam and with an admin password, waits for the server-started banner, classifies error-shaped log lines against the vanilla-noise baseline with stack frames attached to their head line, and stops with a quit on standard input, falling back to the remote console [#1788].
Five boot-spike facts changed the design: the server's own log file in the cachedir is not the client's console file name, the admin-password argument bootstraps the admin account non-interactively, router detection runs unless universal plug-and-play is seeded off, a no-Steam launch works cleanly, and a whole server fixture is about fifteen megabytes so a golden-world snapshot and restore per run is trivially cheap [#1848].
The server's mod list is authoritative and the client inherits it: the client reloads its Lua with the server's list on join, so its own enabled list matters only until the first join, and a client-side mod the server does not name is not in the session [#1824].

The client side is where the session's surface is widest.
Sixteen facts about the client's launch and join surface were established by the join spike, from the connect argument landing on the connect popup with no server browser, through the absence of any username launch argument, the connect button's own call, the terms-screen version line, the state-transition markers, the enabled-mods file shape, the saved-server database, the character-creation route and the auto-connect popup that never presses connect, to the launcher's elevation prompt and implicit account creation on an open no-Steam server [#1852].
That set was taken in one spike over eight attempts on one machine and one build, and four of its entries carry rows of their own: the first-launch mods reset, the logo skip, the debug refusal for a non-admin account and the three-screen creation flow [#1852].
The logo state is added unless the debug flag and a named debug option are both set, the option living in a key-value debug file in the cachedir — so the roughly twenty-second logo is skippable only for debug clients, which servers accept only for admin accounts, and no non-debug launch argument exists for it [#1854].
Multiplayer character creation is three screens and not the cooperative ones, each advanced by the same option handler: the spawn screen needs a valid list selection, the profession screen has no checks, and the appearance screen initialises the player, saves the account's names and enters the world [#1855/C/C-only].
That creation flow is a Lua reading on this build taken once by the join spike, so it is a code reading rather than a measured sequence [#1855/C/C-only].

The admin surface a running session exposes is narrow and partly hostile.
The remote console's help command throws a format exception inside the server's translator and logs two error lines, so it is never called [#1872].
The time-speed admin command, which is the one admin command this library leaned on, is stated under [`## Open`](#open) because its only evidence is a run that committed no artifact.
Everything about how a session is actually driven — the orchestrator, the profile, the sandbox block, the driven client, the bus and how a reply is read — is [`harness.md`](harness.md), and the generated command inventory is `reference/harness-commands.md`.
What a mod folder must look like for any of this to load it is [`mod-anatomy.md`](mod-anatomy.md), and the checksum gate that turns a script mismatch into a disconnect rather than a silent degrade is [`mod-anatomy.md#checksum-gate`](mod-anatomy.md#checksum-gate).
Each of the four moments has a page that owns its mechanisms, and this section owns only the shape.
The two launches and the join are [`harness.md`](harness.md) for how they are driven and [`mod-anatomy.md`](mod-anatomy.md) for what the game does with the mod list at each of them.
The admin surface has no page of its own, and what that means is a boundary row under the coverage table.

<a id="routing"></a>
### Which page owns which mechanism

This is the table to read before reading anything else.
Each row names one page, what that page owns, and the anchors inside it that a question usually lands on.
A number is stated once, on the page that owns it; every other page cites it by tag and links here.
Where two pages look adjacent, the third column says which side of the boundary a question falls on.

| Page | What it owns | Anchors a question lands on |
|---|---|---|
| [`mod-anatomy.md`](mod-anatomy.md) | what a mod folder is: `mod.info` and its keys, discovery, which file supplies the id, the version dir against `common/`, translations, the missing-mod and version-gate failures, the join, the checksum gate, a one-sided mod | `#mod-info-keys`, `#mod-discovery`, `#id-chain`, `#version-dirs`, `#translations`, `#load-order-declarations`, `#missing-mod`, `#build-pinning`, `#join`, `#checksum-gate`, `#client-only-mods` |
| [`loader-and-scripts.md`](loader-and-scripts.md) | how a relative path becomes one file, how the Lua execution list is built, the `item` and `craftRecipe` grammars, and the block-level merge inside a script file | `#file-map`, `#lua-load-order`, `#script-dsl`, `#craft-recipe-grammar`, `#bucket-append`, `#per-key-merge`, `#sorted-replay`, `#path-collisions`, `#default-moddata`, `#per-side-load`, `#reload` |
| [`lua-platform.md`](lua-platform.md) | the Lua a mod runs inside: the dialect's gaps, what a protected call catches, what an unguarded raise costs, how a Java member is reached, how the script hooks resolve, the event surface, the registries, the removed APIs | `#kahlua-limits`, `#pcall`, `#raises`, `#debug-break`, `#java-members`, `#script-hooks`, `#events`, `#hooks`, `#registries`, `#removed-apis`, `#file-io`, `#dev-loop` |
| [`mp-model.md`](mp-model.md) | which side owns each quantity, the routes state can travel, when each packet fires, what the receiver holds in between, and what a client's copy is and is not | `#ownership`, `#routes-client-to-server`, `#routes-server-to-client`, `#packets`, `#cached-packet`, `#item-moddata`, `#player-moddata`, `#wipe-and-replace`, `#command-bus`, `#what-a-client-copy-is` |
| [`harness.md`](harness.md) | the instrument every measured row here was taken with: the orchestrator, the profile, the sandbox block, the driven client, the bus and reply reading, probes, the witness, scenarios, cadence, artifact and driver discipline | `#pzt`, `#profiles`, `#sandbox`, `#driven-client`, `#bus`, `#reading-a-reply`, `#probes`, `#witness`, `#scenarios`, `#cadence`, `#time`, `#driver-rules` |
| [`lessons.md`](lessons.md) | the standing rules this library leaves behind, with the page each rule rests on named beside it | `#rules`, `#anti-patterns`, `#testing-discipline`, `#corpus-drift`, `#measure-the-mechanism` |
| [`jar-research.md`](jar-research.md) | how a question about the game's Java becomes a citable claim: the disassembler's subcommands, absence, callers, access flags, offsets, the exposer dump | `#reading-the-jar`, `#method`, `#exposed`, `#procedure` |
| [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md) | what a food item or a fluid container delivers when it is eaten or drunk: the getters, the fraction, the modifier ladder, the leftover, the drink path, the duration, the sandbox gate | `#getters`, `#eat`, `#modifiers`, `#partial`, `#fluid-path`, `#eat-type`, `#duration`, `#sandbox` |
| [`../facts/food-item-model.md`](../facts/food-item-model.md) | what a food item is: its state axes, the setters that write nothing, the item-level script keys, the poison fields, the shipped dataset's fidelity | `#state-axes`, `#dead-setters`, `#script-keys`, `#poison`, `#dataset-fidelity` |
| [`../facts/spoilage.md`](../facts/spoilage.md) | what moves an item's age, what freezing and refrigeration multiply it by, what rot changes, which side owns the clock, and the sealed items with no clock | `#formula`, `#containers`, `#spawn-age`, `#sealed`, `#writes`, `#sandbox` |
| [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md) | the cook and burn transitions, what a craft recipe's inputs cost, the evolved-recipe summation and its join, and the nutrition delta of a type change | `#cook-block`, `#uses`, `#evolved`, `#evolved-join`, `#type-change`, `#dataset-fidelity` |
| [`../facts/body-and-weight.md`](../facts/body-and-weight.md) | what the body does with the stores between meals: passive burn, hunger, thirst, the moodles, the weight bands and the traits that scale them | `#passive-burn`, `#hunger-thirst`, `#multipliers`, `#moodles`, `#weight-bands`, `#weight-traits`, `#sandbox` |
| [`../facts/nutrition-core.md`](../facts/nutrition-core.md) | the nutrition object's stores, the weight model that reads them, the clamps that bound them and the multi-day server check of that model | `#weight-model`, `#clamps`, `#verified`, `#macro-effects` |
| [`../facts/wire-packets.md`](../facts/wire-packets.md) | which food and nutrition getters each packet reads, which it omits, and every desync measured per field and per arm | `#item-stats-packet`, `#player-stats-packet`, `#moddata-packet`, `#eat-food-packet`, `#cooked-thirst`, `#desyncs`, `#staircase` |
| [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) | what the installed workshop corpus and the public Workshop hold on the nutrition surface: the dated sweeps, per-candidate build status, the API surface and the corpus-level counts | `#sweep`, `#status`, `#api-surface`, `#corpus-facts` |
| [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) | a client-only mod split across `common/` and a version folder: what it does, the state it keeps, and what it collides with | `#what-it-does`, `#architecture`, `#data-model`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md) | a preservation mod's two cook hooks, and which of its techniques and failures to copy or avoid | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) | a pure client-side viewer of the player's status numbers: what it draws, how it is built, and the one call it makes that crosses the wire | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/beyondten.md`](../facts/other-mods/beyondten.md) | a stat the Java engine does not know about, layered on character modData, and what its three delivery mechanisms cost | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |
| [`../facts/other-mods/itemquality.md`](../facts/other-mods/itemquality.md) | per-item mod values on crafted items, and why stat buffs written into live Java fields do not survive a dedicated server | `#what-it-does`, `#architecture`, `#mp`, `#techniques`, `#pitfalls`, `#compat` |

Three boundaries inside that table catch most misroutes.
Whether a file loads at all is `mod-anatomy.md`, while what happens to the blocks inside a file that did load is `loader-and-scripts.md`.
The packet mechanisms — when a packet fires, what the receiver caches, what a transmit replaces — are `mp-model.md`, while the field lists and the measured desyncs are `facts/wire-packets.md`.
An engine fact a mod teardown discovered is a platform or facts row that the teardown page cites; the teardown page owns only what that mod does.
The nutrition lens on all of this — what a design should do with it — is the `areas/` tree, which states no mechanism of its own, and the verdict rows those readings are drawn from are `reference/wall-map.md`.

The same routing, read by the shape of the task rather than by the name of the page:

- Whether a file loads at all, in what order, and from which folder starts at [`mod-anatomy.md`](mod-anatomy.md) and moves to [`loader-and-scripts.md`](loader-and-scripts.md) once the file is known to load.
- Whether a piece of Lua may do a thing at all starts at [`lua-platform.md`](lua-platform.md), and ends at `reference/wall-map.md` when the answer is no.
- What the other side will be holding starts at [`mp-model.md`](mp-model.md) for the route and ends at [`../facts/wire-packets.md`](../facts/wire-packets.md) for the fields.
- A number the game itself computes starts in the `facts/` tree, on the page whose mechanism owns that number, and never on this one.
- How to measure any of it starts at [`harness.md`](harness.md); a question nothing here measured starts at [`jar-research.md`](jar-research.md).
- What another mod already does about it starts at [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) and continues on that mod's own page.
- What this mod should do about the answer is the `areas/` tree, which restates no mechanism and carries the design's own readings.

A number quoted from any of those pages travels with the tag it is stated under, because the tag is what makes it re-checkable: the grade, the bound and the status all sit inside it.
A tag whose suffix names a bound marks a number that is true inside that bound and unknown outside it, which is why the bound is quoted beside the number rather than dropped.
A tag marked unverified is not an answer at all: it is listed under its page's open section and nowhere else, and it is never quoted as a fact.

## Coverage
<a id="coverage"></a>

`platform/` is not a modding manual.
It holds what this library measured or read while building a nutrition mod on a dedicated `42.20.4` server with one client.
A topic marked absent has no page, no rule and no claim here; an agent asked about it says so and reads the jar or the mirror, and never infers a wall from silence.
Every verdict is dedicated-server multiplayer; single-player is never claimed.

The full event roster lives on the wiki and the full command inventory lives in the testing reference: the curated Lua surface carries a row only where this library used or measured it [#0887/W/one-side].
That surface is curated and not an inventory, so an absence in it is a coverage boundary and never a statement that the API does not exist [#0887/W/one-side].
Every verdict in the wall map is bounded to build `42.20.4` on a dedicated server with one client, one fixture and one admin character, and single-player is never claimed [#1256/C/one-fixture].
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
| the workshop corpus and five teardowns | covered | [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) |
| sandbox options a mod declares | touched | rows only; no page |
| the UI framework | touched | rows only; no page |
| timed actions | touched | rows only; no page |
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

Each touched topic carries its own boundary row, so the boundary is in the register and not only on this page.
The events roster's boundary is the curated-surface row stated above, and the other seven topics each carry a row of their own.
The sandbox options a mod declares are touched by rows but have no page: the vanilla options this library read are stated on the pages they gate and the harness merges a profile's block into a fixture, while how a mod declares an option of its own, and whether Lua can flip one at runtime and have it replicate, is unread [#2043/C/one-side/open].
The user-interface framework is touched by rows but has no page: the corpus teardowns read one framework mod's registration surface and one viewer mod's panel, while the interface toolkit itself, its widget set and its own event surface are unread [#2044/C/one-side/open].
Timed actions are touched by rows but have no page: the eat and drink actions are read end to end and the multiplayer action manager's route into them is traced, while the action queue, its tick budget and how a mod adds an action of its own are unread [#2045/M/one-side/open].
The crafting pipeline is touched by rows but has no page: the craft-recipe grammar, what an input really costs and the output's inherited state are stated on the loader and cooking pages, while the crafting interface, the handcraft action and the recipe-discovery surface are unread [#2046/C/one-side/open].
Server admin and the remote console are touched by rows but have no page: the console's transport, the one admin command this library drove and the one that throws are stated here, while the admin command set as a whole and what each does to a running world are unread [#2047/C/one-side/open].
Build detection is touched by rows but has no page: the version keys and what the availability gate compares are stated on the anatomy page, while what a mod can detect about the running build from inside Lua is unread [#2048/C/one-side/open].
Client-only mods are touched by rows but have no page: one workshop mod is torn down as a pure client-side viewer and a second as a client-only cooking helper, while the general cost of shipping one side only, and what still reaches the other side, is stated as anatomy rather than as a topic of its own [#2049/M/n=1/open].

Not every absence above is equal, and the table is read by status rather than by row.
A `covered` row means a page collects the rows and states each with its grade and its bound, and that is the only status whose answer may be quoted as this library's.
A `touched` row means the rows exist but are scattered across the pages that needed them, so the answer is partial and the topic's boundary row says exactly where it stops.
An `absent` row means this library never opened the surface at all and carries no register row, by design; the honest answer to a question about one names the jar or the wiki mirror as the next step and stops.
A `touched` gap is a gap in this tree; an `absent` gap is a gap in what was read, and neither is a statement about the game.
The three never-written vanilla pages are listed as absent for the same reason: they were planned, nothing was written, and no row anywhere stands in for them.

An agent answering out of this tree therefore says one of three things.
For a covered topic it quotes the owner page's sentence with the tag that sentence carries.
For a touched topic it says what the rows establish, names the boundary row that says where they stop, and goes no further.
For an absent topic it says this library never read it, points at the jar or the wiki mirror as the next step, and infers nothing from the silence.

## Open
<a id="open"></a>

- That the client resets its Lua with the server's mod list on connect, dropping locally enabled mods, so that a client-side harness must survive a mid-flow reset with its stages keyed on screen visibility and its manifest re-read from disk, is unverified: its only evidence is a spike run over eight attempts on one machine and one build that committed no artifact folder; re-measure by joining with a client-side mod the server does not name and censusing the client's loaded mods before and after the connect, in a run whose artifact is committed [#1856/M/uncommitted/unverified].
- That the time-speed admin command sets the server's multiplier and broadcasts a multiplier packet to every client, works over the remote console, needs no debug flag, and that at a multiplier of thirty both sides ran at about thirty-two times real time with calorie burn scaling with it, is unverified: both spike runs committed no artifact folder; re-measure by driving the command over the remote console and taking paired clock and calorie readings on both sides in a run whose artifact is committed [#1868/M/uncommitted/unverified].
- Whether a topic the coverage table marks `touched` gets a page of its own or stays a boundary row — settled by a pass that reads the rows each topic already carries and decides whether they make a page; each topic's boundary row is stated under [`## Coverage`](#coverage) and says what is established and what is unread, because an agent reading only this tree cannot otherwise tell a thin topic from an unread one.
- Decision: whether a mod's own code is allowed to live under `media/lua/server/` at all, or whether every file goes in a shared folder with an explicit runtime side test — the folder is not a deployment boundary and both copies run on a client [#0854/M/n=1, #0878/M/n=1].
- Decision: whether this tree carries an admin-and-remote-console page of its own — the one admin command the library drove is unverified and the console's help command is unusable, so the surface is presently two rows and a boundary [#1868/M/uncommitted/unverified, #1872].

## See also

- [`mod-anatomy.md`](mod-anatomy.md) — what a mod folder is, and whether a file is loaded at all before any of the four surfaces matters.
- [`loader-and-scripts.md`](loader-and-scripts.md) — the file map, the Lua execution list and the block-level merge inside a script file.
- [`lua-platform.md`](lua-platform.md) — the dialect, the Java-member route, the script hooks and the event surface this page routes to.
- [`mp-model.md`](mp-model.md) — the ownership table every sentence under one server links to, and the routes between the two sides.
- [`harness.md`](harness.md) — the instrument the process model is written from, and the profile that stands a session up.
- [`lessons.md`](lessons.md) — the standing rules, including the runtime side test the two Lua states force.
- [`jar-research.md`](jar-research.md) — how a question this tree does not answer becomes a citable claim from the jar.
- [`../facts/wire-packets.md`](../facts/wire-packets.md) — the field contracts behind every push named under one server.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) — what the corpus does with the same surfaces, and the dated sweeps behind the corpus counts.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments that settle the open rows this page and the pages it routes to carry.
- [`../reference/harness-commands.md`](../reference/harness-commands.md) — the generated command inventory the command-bus surface resolves to.
