# Lessons
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the standing rules this library leaves behind — what the approved corpus converges on, what it does that this mod will not, what a measurement of this game is allowed to claim, and how fast the corpus itself moves underneath a count; every mechanism a rule rests on lives on the page this one cites for it.

## Rules
<a id="rules"></a>

- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Initialise world-scoped shared tables in `OnInitGlobalModData`: it is the sanctioned init point and it runs before players exist [#1066/C/snapshot].
- Monkey-patch idempotently and keep the original, testing for your own wrapper before you replace the target: that shape is safe under a Lua reload, unwindable, and it composes when two mods wrap the same function [#1067/C/snapshot].
- Store inputs in modData and derive the values on read: a derived-on-read model needs no migration when a formula changes [#1068/C/snapshot].
- Drive behaviour from declarative config tables read by a generic engine: content changes then never touch logic [#1069/C/snapshot].
- Register with a framework that already owns a contested value rather than writing that value last: cooperative detection avoids last-write-wins between two mods that both own carry weight or moodles [#1070/C/snapshot].
- Put slow simulation such as nutrient decay on `EveryOneMinute` or `EveryTenMinutes`, use `OnPlayerUpdate` only for per-frame needs behind a cheap early-out, and avoid `OnTick`: 38 mods already share `OnPlayerUpdate` and `OnTick` is the expensive tier [#1071/C/snapshot].
- Wrap every third-party and engine-boundary call in `pcall` and fail soft: an unguarded raise aborts the rest of the handler body it fires in, while the handlers registered behind it still run [#1072/C/snapshot, #0948/M/n=1, #0949/M/n=1].
- Ship a `42/` tree with `42.x/` overrides beside `common/` and declare dependency order with `mod.info` `require=`: the version folder wins a same-relative-path collision while `common/` supplies everything that folder does not ship [#1073/M/n=2].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Read the dataset or a server-side instance for what an item or a recipe is rather than a client-side instance's zero, and put anything that changes what eating, drinking or crafting delivers on the server: script data is the load-time definition both sides start from, while a client's copy of an instance is free to be wrong about a field the packet skipped [#0651].
- Never branch on an item display name server-side: a dedicated server has none [#0848/M/n=1].
- Gate a translation-dependent feature on an interface key and never on an item name: the text router carries no item-name prefix ([`mod-anatomy.md`](mod-anatomy.md#translations)), and nine keys across two sessions missed on both sides, bare and prefixed forms alike, while the same run read the display name straight off the instance [#1720/M/n=2].
- Define a script hook's target as a bare global function rather than a local or a table member, and put the file in `shared/` so both states define it: the name resolves as a global, and a hook that must run on one side only branches inside itself, because the file's folder will not do it [#0927/C/C-only].
- Reach every Java member by indexing first and calling second: a nil call never says which member was nil, aborts the body it sits in when unguarded and is session-ending on a debug client, and every Lua file in the experiment mods carries its own guard so that a mod never depends on the harness being installed [#0935/C/C-only].
- Gate a raising probe on the server side and set its profile's client timeout low: a debug client parks on the first unguarded mod Lua error [#1963/M/n=2].
- Never register the stat hook unless your handler reproduces every updater it skips, [their side effects](../areas/body-effects.md#rules) included, and cannot raise: registration is all-or-nothing for every player on the server, the handler's return is discarded, a second registrant cannot restore the updaters, and a raise inside it leaves the stats frozen [#2737/C/inference] [#2100/M/n=1] [#2086/M/n=1] [#2238/C/C-only] [#2240/C/C-only] [#2236/C/C-only] [#0896/C/C-only].
- Register a `Hook.*` handler with a dot call and pass the same closure object to `Remove`: the colon form registers nothing and raises no error, `Add` does not de-duplicate, and `Remove` removes one registration per call [#2805/C/inference, #2801/C/C-only, #2802/C/C-only].
- Reproduce the asleep endurance regeneration in a `CalculateStats` handler: the arm lives in the skipped sleeping updater, while the awake model runs outside the hook [#2806/C/inference, #2782/C/C-only, #2261/C/C-only].
- Re-apply the band traits a Strength or Fitness level implies yourself after writing that level through `setPerkLevelDebug`: the debug setter writes the level and nothing else, so neither the level event nor the listener that remaps the band traits on it runs [#2729/C/inference] [#2119/C/C-only] [#2127/C/C-only] [#2157/C/C-only].
- Re-locate a workshop mod's version-folder line cite by its quoted text before quoting it, and name the tree it was read in: Steam adds version trees to an installed item under the library, so the tree this build resolves moves and a line number read in an older tree is drifted rather than wrong [#2730/C/inference] [#2523/C/snapshot] [#1466/C/snapshot] [#1964/C/snapshot].

## How it works

<a id="anti-patterns"></a>
### What the corpus does that this mod will not

The rules above are what the well-behaved heavy mods converge on.
The lines below are the other half of the same reading: shapes the corpus ships, or shapes the corpus implies by what it gets away with, that this mod deliberately will not adopt.
Each is a filter, not a criticism — several are the exemplar mod's best available option on this build.
A filter line is used the way a rule is: as a test applied to this mod's own design before it is written, and as the first thing to check when a value behaves differently on the two sides of a session.
Most of them were paid for by a mod that shipped and worked, which is what makes them worth stating: none of these shapes announces itself as a defect while it is being written.
They divide into five groups, and each group is one question about where a cost or an authority ends up.

Authority is the first group, and all three lines say the same thing from different sides: a value has exactly one owner, and the wire decides where that owner may be.

- Never give a mod's authority to a field the sync packet does not carry, and verify per field: a write to an uncarried field depends on the server copy alone, and no amount of re-pushing repairs the client's [#1076/M/n=1].
- Read a food's numbers from the side that owns them and never build mod math on a getter whose value is transformed again on the wire: the item packet sends a cooked food's derived thirst getter and the receiver stores it as the raw field [#1084/M/n=2].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before any client transmits: player modData is a client-writable channel, and the mod that loses the data is never the mod that called `transmitModData` [#1085/M/n=2].

The third of those is the one that constrains a neighbour rather than this mod alone: a mod that never transmits still loses server-only keys to somebody else's transmit, so this mod's own state has to survive a call it does not make.
The teardown that supplied it is [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md), and the route itself is [`mp-model.md`](mp-model.md#wipe-and-replace).

The test all three apply is one question asked of three different artefacts: which side may write this value, and what does the other side hold instead.
For a field the packet carries, the answer is that the server writes and the client mirrors, and a client-side write is discarded or simply never leaves.
For a field the packet does not carry, the answer is that a client-side reader is reading its own copy forever, so the value either moves into script data, which both sides load identically and never sync, or it travels on this mod's own command.
The check that separates those two cases is the packet's field list and never the field's name, and the getter a setter calls and never the key it writes.
Neither check can be made once and trusted: the field list is per field and per build, which is the whole content of the first line above.

The second group is about state that corrects itself, or fails to.

- Make reconciliation converge rather than latch: one-shot repair logic and observation trackers that overwrite truth poison the value they were meant to protect [#1077/C/snapshot].
- Keep core nutrient math in its own tick rather than injecting effective levels or local variables into engine functions: each injection point breaks silently on a game update [#1078/C/snapshot].

Injection is acceptable for a bonus and not for core math, which is the distinction the exemplar mod itself draws; the cost of getting it wrong is a mod that still loads and quietly computes the wrong number.
A converging reconciler re-derives its value from the stored inputs every time it runs, so a wrong intermediate state is corrected on the next pass instead of being written into the record.
A latching one writes its conclusion once and keeps no way back, which is how an observation tracker ends up overwriting the truth it was built to observe.
Both lines are the derive-on-read rule seen from the failure side: what is stored is the input, and everything else is recomputed.

The third group is cost, and both lines are about paying it in the wrong place.

- Keep simulation off `OnTick`: the 69 hook registrations there are concentrated in the heavy tier and nutrition has no business in it [#1080/C/snapshot].
- Put the item pass's data in script files or lazily loaded modules rather than in Lua tables parsed at boot: data-as-Lua at scale pays its whole cost at load [#1081/C/snapshot].

Both cost lines are about when the bill arrives rather than how large it is.
The per-frame tier is already the crowded one before this mod's own work is added to it, which is what the hook-tier count says and is the whole of the cost argument here [#1080/C/snapshot].
A table of item data parsed at boot costs its whole size before the first player joins, where the same data in a script file is read by the loader that was going to walk the script tree anyway.
Nutrient decay is a slow quantity by construction, so it belongs on a slow hook, and nothing on this mod's critical path needs a reading more often than the minute tier gives it.

The fourth group is hygiene, where the corpus's own practice and this mod's differ by scale rather than by taste.

- Do not run a large multiplayer codebase with zero error handling: author discipline is what carries `KBW`, `HorseMod` and `damnlib` across 2 MB of Lua, and `KBW`'s own bug thread shows the cost when it slips [#1079/C/snapshot].
- Never use `loadstring`: the engine removed it in the `42.20.x` security fixes, and the corpus count is zero [#1082/C/snapshot].

Neither hygiene line says the corpus is careless: the trees running without protected calls are the ones with a single author holding the whole shape in mind.
This mod has no such guarantee, because it is written to sit on a server beside mods it does not control, so the boundary calls are wrapped and the failures are made soft and visible rather than fatal to every handler behind them.
The removed-function line is the cheapest of all of them to obey, since the corpus already does and the layout lint keeps it that way.

The last group is about the mods and the files that sit beside this one.

- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Treat a `common/` file the version folder shadows as unmaintained, deleting it or keeping it building against the same interface as the live copy: it is unexecuted code on that build, and nothing in the mod asserts the merge direction it depends on [#1086/M/n=1].

Rendering through a framework is the cooperative-detection rule applied to a surface rather than to a value, and the argument is the same: the last writer wins, and being the last writer is not a design.
The shadowed-file line is the mirror image of the layout rule above it: the same merge that makes the layout worth shipping is what lets a dead copy rot unnoticed, and the copies measured in the corpus call members this build removed.
An unguarded call to a removed member does not degrade a feature — it ends the body it fires in, which is why the shadowed copy is a hazard rather than clutter ([`lua-platform.md`](lua-platform.md#raises)).
What makes it a filter rather than a note is that nothing in such a mod asserts the direction it depends on: the mod is correct only because the loader happens to prefer the other copy, and no test in it would notice if that changed.

<a id="testing-discipline"></a>
### What a reading of this game is allowed to claim

Every measured rule on this page came off one instrument, and the instrument has its own failure modes.
Two of them are general enough to be rules in their own right, because both produce a number that looks like an answer.

- A grep limit is a break and not a window, on the server log as much as the client's: the reader stops at the limit, so a result of exactly the limit means saturation and never exhaustion — size it above the expected count, and never report a saturated read as a census [#1763].
- The missing-mod run reported zero server errors and that is not a contradiction: to this game a missing mod is a warning and a clean boot, so a zero error count must never be read as the mod loaded [#1821/M/n=1].

Both are the same mistake in two costumes: a reading whose shape is set by the instrument, taken for a reading whose shape is set by the game.
A saturated grep is the reader's ceiling; a clean boot is the classifier's silence.
The error count a run prints is a classifier's output rather than a fault count, so the list is read before the number is quoted ([#1764], [#1247], [`harness.md`](harness.md#reading-a-reply)).

What both rules ask for is one habit: say what the instrument would have shown had the answer been different.
A grep whose limit sits above the predicted count can separate a full census from a truncated one; a grep at the predicted count cannot, and it fails in the direction that reads as a pass.
A gate that asserts the mod took effect can separate a loaded mod from a merely named one; an error count cannot, and it fails in the same direction.
Both failures are silent, and both are closed before the session is paid for rather than after it.
A bound is recorded for the same reason, and it is the part of a measured rule that survives a build bump: the number may have to be taken again, but what was and was not exercised is what tells a later reader whether taking it again is necessary.
A reading that comes back trivial, unmeasured or falsified is written as such and never re-run for a prettier number ([`harness.md`](harness.md#driver-rules)).

Four further pieces of discipline belong to the harness and are stated there rather than here.
A client-side reader of a server-owned store steps when a packet lands where the server ramps, so the client's series measures the push and not the simulation ([#1483], [`../facts/wire-packets.md`](../facts/wire-packets.md#staircase)).
A client-side console grep sees each engine load line once per Lua state, so a client limit is sized against twice the predicted count ([`harness.md`](harness.md#reading-a-reply)).
Every named experiment inherits the same six clauses of profile, driver, provenance and verdict discipline, and a rider on an existing session is preferred to a session of its own ([`harness.md`](harness.md#experiment-contract), [`../reference/experiments.md`](../reference/experiments.md)).
A probe built to raise makes the run report failure by construction, which is the harness working rather than the probe failing, so the grade comes off the artifact and not off the console line ([`harness.md`](harness.md#driver-rules)).
The one rule that belongs to both this page and that one is the last of the imperatives above, the server-side gate and the low client timeout a raising probe is given [#1963/M/n=2].

<a id="corpus-drift"></a>
### The corpus moves while you are counting it

The installed workshop tree is not a fixed object, and nothing in this repository writes to it.
Two things drift independently and both matter: the set of folders on disk, and the contents of any one of them.

- Quote a corpus sweep with its stamp: the installed workshop tree is live and changes under a running session [#1964/C/snapshot].
- Steam rewrites the subtree inside a workshop item rather than every folder node: one item's own folder still carried an August modification time while the mod folder inside it had been rewritten at 13:47 on 2026-09-10 [#1841/C/snapshot].

The second line is why a modification time on the item folder is not a staleness check: the folder that moved is one level down, and an item whose own node looks months old may hold a tree rewritten minutes ago.
Every count in this library that was taken over that tree therefore carries a date, and the dated inventory snapshot is the object the corpus rules are computed over rather than the live folder.

Dating a count is not bookkeeping; it is what makes the count falsifiable at all.
A corpus rule such as the hook-tier line or the error-handling line is a statement about the mods that were installed on one particular afternoon, and the honest form of it names that afternoon.
A recount is then a new reading with a new date rather than a confirmation of the old one, and the two disagreeing is information about the tree rather than a defect in either.
The same discipline is what keeps a corpus rule from hardening into folklore: the pattern is common among the mods that survived on that tree, which is evidence about what works and not proof that the alternative fails.
It also bounds how long a rule on this page is worth anything without a fresh look, since the game ships monthly patches and the tree follows them.
The stamp at the head of this page carries the same discipline one level up, naming the build and the day the lines under it were read on [#1964/C/snapshot].

Line cites into a workshop mod drift the same way, and they drift without becoming wrong.

- Every version-folder line cite in the client-only mod's teardown ([`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md)) names the tree as it stood on 2026-09-10, and Steam added a newer tree to the item on 2026-09-13 whose copy of the panel file is 589 lines against the read copy's 583, so those cites are drifted rather than wrong and must be re-located by content before being quoted elsewhere; the measured readings are unaffected, because the run booted the older tree [#1466/C/snapshot].

The tree added on that date is the `42.20` one this build resolves, so the teardown's version-folder cites name a tree that is no longer the live one ([#2523/C/snapshot], [simplestatus.md#architecture](../facts/other-mods/simplestatus.md#architecture)).
Re-locating a cite by content rather than by line number is the standing practice that follows from it, written as a rule [above](#rules), and it applies to this repository's own files as much as to the corpus.
A line number is the least durable part of any cite, which is why every pointer in this library carries the text it names as well as the place it sat.
A drifted cite is also not a falsified reading: a run that booted the older tree measured the older tree, and what moved is the address rather than the answer.
The sweep counts themselves are the part of this section that no committed artifact backs, and they are listed under [Open](#open) rather than quoted as facts here.

<a id="measure-the-mechanism"></a>
### Measure the mechanism, not the mirror

The single reading that connects the rules on this page is that a client's copy of a server-owned value is a mirror, and a mirror can be measured perfectly and still tell you nothing about the thing it reflects.
The mirror is not a metaphor for a display: it is what a client's copy of a server-owned object is on this build.
A reader on that side sees exactly what the last packet left there, and it goes on seeing that after the server's own value has moved.
So a measurement of the client is a measurement of the last push, and it is a measurement of the mechanism only when the push and the value are known to agree.

Two of the rules above are that reading in two different places, and the third case is a row this page borrows from the packet facts.
A cooked food's thirst is wrong on the client not because the client simulates differently but because of what the packet sends and how the receiver stores it, so the number is honest on both sides and the mechanism is the transformation between them ([#1084/M/n=2]).
A field the packet does not carry is not slow to arrive; it never arrives, so re-pushing measures the sender and not the gap ([#1076/M/n=1]).
A client-side series of a pushed store is a staircase whose step width is the push cadence, so reading it faster measures the reader ([#1483], [`../facts/wire-packets.md`](../facts/wire-packets.md#staircase)).

The instrument rules under [what a reading may claim](#testing-discipline) are the same lesson turned on the harness itself: a grep limit and an error classifier both return a number whose shape belongs to the tool.

So the practice is to name the mechanism before taking the number.
Read the packet's field list rather than the field's name; read the getter that `setData` calls rather than the key it writes; read which file the loader mapped rather than which file the mod ships; read the dataset rather than a live instance whose zero may be a packet's omission ([#0651], [#1086/M/n=1]).
Each of those is a question with a code answer that can be settled before a server is booted, which is why the rows those four readings rest on are jar and script reads rather than runs [#0651, #1086/M/n=1].
The measurement then has something to falsify rather than something to report, and a reading that disagrees with the mechanism is worth more than one that agrees with it.
Where the mechanism cannot be read, the rule is written with the bound that the mechanism is untraced, which is what the whole of [Walls and bounds](#walls) below records.
An untraced mechanism is not a missing rule: the guard on a `server/` file is obeyed on the strength of the measurement alone, and the bound says only that a build bump could change the reason without changing the behaviour.

For this mod's own tests the reading has a direct consequence.
A test that reads a client-side value proves that the push arrived, and a test that reads the server's proves what the mod computed, so a pair of them is the smallest honest check of anything that crosses the wire.
Reading both sides of one tick is what makes the comparison a comparison rather than two unrelated samples, and it is why every driver in this library reads the client first and the server second at each tag ([`harness.md`](harness.md#probes)).

## Walls and bounds
<a id="walls"></a>

Every corpus-derived rule on this page is a snapshot reading over the installed tree, so each holds for the mods that survived on that tree at its stamp: a pattern common among survivors is evidence about what works, not proof that the alternative fails [#1064/C/snapshot, #1069/C/snapshot].
The counts those rules quote are dated for the same reason, and re-running the sweep is preferred to citing the numbers here [#1964/C/snapshot, #1466/C/snapshot].
The layout rule is bounded to a version directory that ships colliding files, or none at all; a version directory that ships files colliding with nothing is untested, and the sound shape it endorses is an entry point in `common/` calling a version-folder body [#1073/M/n=2].
The script-first rule rests on one session: one build, one fixture, one mod, one item, one player and one cook transition [#1074/M/n=1].
The `server/` guard rests on one session, the reading was incidental to a run aimed at other questions, and the mechanism is untraced — no loader pass has been read that maps a `server/` file into the client's state [#0855/M/n=1, #1075/M/n=1].
The debug-break rule is two boots of one build on one raise family, and a release client is unmeasured [#1963/M/n=2].
The stat-hook rule rests on code readings that one live session has since exercised: a registrant skipped the updaters whatever it returned, a second registrant did not restore them, and the hook never fired on the client, while the debug-setter rule is still read from the bytecode only [#2238/C/C-only, #2119/C/C-only] [#2100/M/n=1] [#2086/M/n=1].
The hook-target rule and the index-first rule are code readings rather than measurements: the global-name resolution and the guard's three reasons are read out of the engine, and the practice exists so that the failure is never exercised [#0927/C/C-only, #0935/C/C-only].
The uncarried-field rule and the shadowed-`common/` rule each rest on one session on one mod, on the dedicated-server path [#1076/M/n=1, #1086/M/n=1].
The transmit rule stands at two sessions for the client-to-server direction against one for the other, and its call-site half is a code read that no bus command could exercise, because each site needs an interface click [#1085/M/n=2].
The cooked-getter rule is vanilla's behaviour rather than a mod's, which is what makes it land on any mod that cooks anything in multiplayer [#1084/M/n=2].
The missing-mod lesson is one run, and the copied line carries the server's own words rather than the harness's [#1821/M/n=1].
The grep-limit rule has no measured bound at all: it is a property of the reader, learned from a limit that reported four override lines where the log held thirteen [#1763].
The translation gate rests on two sessions and nine keys that all missed, so it is bounded to what `getText` does not reach rather than to what the item-name table holds [#1720/M/n=2].
The corpus counts the hook-tier and error-handling rules quote are static counts over one dated sweep of the installed tree, and no mod on that list was run to produce them [#1071/C/snapshot, #1079/C/snapshot].
The framework and resident-interface rules are bounded to the mods resident on the target server on the sweep's date, so both become open questions again the moment that server's mod list changes [#1070/C/snapshot, #1083/C/snapshot].
Not covered: this page reads the corpus by static sweep and by line-level reads of a handful of mods rather than by running them, so no mod on the approved list has been profiled for processor or memory cost, no rule here was taken from a release client, a listen server or a single-player session, nothing was read about the Workshop publishing and subscription surface, and no lesson here covers how any of these patterns behave over the lifetime of a long-running save.

## Open
<a id="open"></a>

- That the item-name table is loaded and working and is simply not addressable from Lua's `getText` is unverified: every reply in the phase that asked missed, so the run carries no in-run positive control, and the route's soundness rests on an earlier session's client-side `IGUI_` hit taken on a different harness shape; re-measure by re-running the key phase with a key known to hit in the same session [#0849/M/n=2/unverified].
- That a corpus sweep must be quoted with its stamp is unverified as measured: the evidence is two sweeps twenty minutes apart whose output was never committed; re-measure by running the layout sweep into a committed artifact before and after a known workshop rewrite [#0867/C/snapshot/unverified].
- The post-rewrite sweep count is unverified: at 04:47 on 2026-09-11 Steam rewrote one workshop mod's version-dir `mod.info`, fixing an id typo, so a sweep taken after that reads 83 findings — 3 errors, 30 warnings and 50 informational — and the drifted-folder count is 51 rather than 52, but the sweep output was never committed; re-measure by re-running the layout sweep into a dated committed artifact [#0866/C/snapshot/unverified].
- The within-afternoon sweep movement is unverified: a lint sweep of the installed corpus moved twice in one afternoon on 2026-09-10 — 85 findings at about 13:00, 84 at 13:47 and 84 again at 14:40 — the single difference being one item whose media folder moved out of the common folder into its version folder, and no sweep output was committed; re-measure by committing each sweep's output with its timestamp [#1976/C/snapshot/unverified].
- Decision the rows force: whether this mod renders through `MoodleFramework` or through its own panels, given that a framework already owning a contested value is registered with rather than written over, and that a resident interface mod redraws the status surfaces on the target server [#1070/C/snapshot, #1083/C/snapshot].
- Decision the rows force: whether any per-player nutrient state lives in player modData at all, given that whichever side calls `transmitModData` replaces the receiver's whole table and the losing mod is never the calling one [#1085/M/n=2].
- Decision the rows force: which tier the nutrient decay tick runs on, given that the minute hooks are the slow tier, that a shared per-frame hook already carries the most registrations, and that `OnTick` is the expensive tier [#1071/C/snapshot, #1080/C/snapshot].
- Decision the rows force: whether the item pass ships entirely as script data, given that a script value is identical on both sides for free while a Lua write to a live item never leaves the server [#1074/M/n=1, #1076/M/n=1].
- Decision the rows force: whether this mod ships a `common/` tree at all, given that the version folder wins a collision and that a shadowed `common/` copy is unexecuted code nothing in the mod asserts the direction of [#1073/M/n=2, #1086/M/n=1].

## See also

- [`mod-anatomy.md`](mod-anatomy.md) — the mod folder, the version dir, the id chain and the translation tables these rules are written against.
- [`loader-and-scripts.md`](loader-and-scripts.md) — the file map and the script merge the layout rule and the script-first rule rest on.
- [`lua-platform.md`](lua-platform.md) — Kahlua's limits, what `pcall` catches, what an unguarded raise aborts, and the debug client's modal break.
- [`mp-model.md`](mp-model.md) — the routes mod state can travel, the wipe in both directions, and which side owns what.
- [`harness.md`](harness.md) — the instrument every measured rule here came off, and the reply-reading rules the testing lessons belong to.
- [`overview.md`](overview.md) — where a question about this build is routed before it reaches any of these pages.
- [`../facts/wire-packets.md`](../facts/wire-packets.md) — the packet field lists, the cooked-thirst transformation and the staircase.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md) — the corpus sweep itself, and the counts the corpus rules are computed over.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) — the teardown behind the player-modData rule.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) — the teardown behind the layout rule and the shadowed-file rule.
- [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md) — the teardown behind the script-first rule and the uncarried-field rule.
- [`../facts/other-mods/itemquality.md`](../facts/other-mods/itemquality.md) — the reconciliation and unsynced-field failures the filter lines generalise.
- [`../facts/other-mods/beyondten.md`](../facts/other-mods/beyondten.md) — the exemplar for idempotent patching, derived-on-read values and cooperative detection.
- [`../areas/packaging.md`](../areas/packaging.md) — where the layout and neighbour rules become this mod's own decisions.
- [`../areas/mp-sync.md`](../areas/mp-sync.md) — where the authority rules become a chosen route.
- [`../areas/body-effects.md`](../areas/body-effects.md) — where the stat-hook rule and the debug-setter rule become levers a nutrition mod pulls.
- [`../facts/perks-and-strength.md`](../facts/perks-and-strength.md#trait-remap) — the level writes, the level event and the band-trait remap the debug-setter rule rests on.
- [`../reference/experiments.md`](../reference/experiments.md) — the standing experiment contract the testing discipline inherits.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the walls of the pages this one cites are drawn from.
