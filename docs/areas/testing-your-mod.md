# Testing your mod — the plan this mod runs under the harness
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: this mod's test plan as a reading of the harness — the profiles it will ship, its scenarios and verification rows, the inputs a multi-day nutrition scenario fixes, the four named experiments it owns, how a cross-side reading is graded, what a tooltip probe can read and the sandbox values its evidence rests on, the mod's own options among them; every mechanism is `platform/harness.md`, the command table `reference/harness-commands.md` and the experiment specs `reference/experiments.md`

## Rules
<a id="rules"></a>

- Never read a green run as evidence that a mod loaded: the game answers a mod it cannot find with a warning and a clean boot, so the run fails fast at the server-started mark and the bus probes are what prove effect [#1793].
- Name a profile's mod by the engine-resolved id: that is the `id=` of the `mod.info` the build actually reads — the newest `42[.x[.y]]/` folder first, then `common/`, then the mod root — and never the folder name [#1558].
- Write every `[[verify]]` row as a gate certain to pass if the mod loaded at all, never as the reading the session exists for: an expectation is a substring of the dumped acknowledgement, so it cannot express absence or a numeric comparison [#1828, #2069/C/inference].
- Gate a probe that can stall the client on the server side: verification is asked only after the client is ready, so a stalled session's client row never runs and the run records a verification error instead of a pass or a fail [#1769/M/n=1].
- Cap the client wait in the profile whenever a probe can hang the client: the readiness wait is capped from the profile's client timeout, whose default is 300 seconds, and a profile that leaves the default sits out the full wait plus teardown — 384 seconds for a five-second hold — on a client that was never going to answer [#1768].
- Take the measurement on the side that owns the quantity: for nutrition, hunger and thirst, item aging and perks the server's reading is the measurement and the client's is a once-a-second mirror [#1826].
- Ask a probe of both sides: the acceptance profile put the same trait check to the server and to the client and both returned the mod's effect, so the mod was present in both Lua states and not merely in the server's [#1825/M/n=1].
- Manage hunger and thirst in anything that fills the calorie store: unattended, the level-4 thirst drain kills in about 35 game-hours on a 90-minute day and about 38 on the 60-minute default, the first figure measured once and the second arithmetic on it [#0179/M/one-fixture].
- Keep `24 × speed / day_minutes` at or below about eight game-minutes per wall second: at the fixture's ninety-minute day and a multiplier of thirty, which is exactly eight, three runs recorded 7.99, 7.99 and 8.00 world-minutes per wall second with exactly one tick per game minute [#1814/M/n=3].
- Leave the backstop a clear margin above the finisher: it is armed first, so it holds the lowest sequence number and wins a same-minute tie, and a test that finishes at exactly the backstop minute is timed out instead and reports an anonymous detail [#1774].
- Put every Java member call behind the index-first guard: a guarded call never raises and the argument-slot protected call never reaches the failure helper, while an unguarded raise, or a nested protected-call raise the mod catches, stalls the driven client [#1714/M/n=1].
- Set the `Nutrition` sandbox option in the server's sandbox config: the nutrition update reads the option live every tick, a runtime flip from Lua is untried, and the Lua mirror of the option goes stale [#1127/C/C-only, #2058/C/inference].
- Run this mod's nutrition scenarios on the fixture's sandbox values, or pay for a fresh baseline beside any value moved: every nutrition reading in this library was taken on one fixture at one day length, so a moved option makes a new baseline rather than a comparison [#1253/C/one-fixture, #2071/C/inference].
- Read a sandbox option back off the run before a reading depends on it: only the day length has been set by a profile on a restored world and read back, while the other options the nutrition work names are settable and unexercised [#1809/C/C-only, #2072/C/inference].
- Grade a cross-side nutrition reading against a band built from its snapshot's own read skew, with the client half read first, and never against equality: a client-side reader is a staircase that steps when a packet lands while the server ramps, so a cross-side gap is a timing reading [#1483, #2070/C/inference].
- Never read a food tooltip's nutrition block as evidence of the Nutritionist gate unless the client runs without the debug flag and the food carries no label the viewer can read: the block also opens under the debug tooltip option and on a packaged food whose label the viewer can read, and the harness adds the debug flag to the admin account's client, so the block can show on a character holding neither Nutritionist trait [#2645/C/C-only, #1710, #2714/C/inference].
- Record the measured window rather than the requested sleep, and name a snapshot tag by its measured offset rather than its intended one: one driver's window field read 10.0 seconds where the reads' own wall stamps give 12.54, and its tag named for three seconds after a transmit actually opened 7.58 seconds after it, so that driver's own window and tag keys are do-not-cite for exactly this reason [#1708/M/n=1].
- Treat a scenario verdict as the test and the evaluator and a clean session together: exit code 0 needs the harness test's own pass, the evaluator's agreement and no environment fault, each of which turns the result into a failure naming its count, marks the timeline and lands in the faults block of both the report and the committed artifact [#1785].
- Copy every piece of measured evidence a document cites into a tracked per-run artifact folder as JSON, kept byte-identical: the full run directories with their logs stay local and untracked [#1705].

## How it works

This page is the test plan of a mod that does not exist yet: which profiles it will ship, what its scenarios and verification rows are for, which inputs a multi-day nutrition run fixes, which named experiments it owns, how a cross-side reading is graded and which sandbox values its evidence rests on.
The instrument is [`../platform/harness.md`](../platform/harness.md), which owns every mechanism named below, and the commands a profile, a scenario or a driver can call are the generated table [`../reference/harness-commands.md`](../reference/harness-commands.md).
Where a mechanism appears below it is stated in one tagged sentence cited to its owner, and an untagged sentence beside it is this page's reading for this mod — which of those mechanisms the plan leans on, with which inputs, and what each run can and cannot prove.
The page owns rules and no fact, and every claim below is cited to the row that owns it.
Every measured row it cites was taken on the dedicated-server path with one driven client, and single player is never claimed [#1256/C/one-fixture].

<a id="mod-profiles"></a>
### The profiles this mod will ship

A profile is one file per named combination under test: the fixture to restore, the mods and where each comes from, the sandbox options to override, the accounts to attach and the probes that must answer before the session counts [#1789].
Its schema is [harness.md#profiles](../platform/harness.md#profiles), and a profile says only what differs from the command line's defaults [#1796].
Everything it asks for is resolved and validated before a process starts, so a wrong mod id or a misspelt sandbox key costs a second rather than a boot [#1790].

The mod ships no profile yet, and the plan seeds each one from `testing/profiles/mod-under-test.toml`, the acceptance profile whose shape every new profile copies [#2050].
That file carries the harness and one workshop mod on the golden fixture, with inline verification rows and a single sandbox override, and the harness page lists it among its worked examples ([`../platform/harness.md`](../platform/harness.md)).
Its override shortens the day, which a plain run never notices and a timed scenario does: a fifteen-minute day at a multiplier of thirty overran the game-minute scheduler [#1813/M/n=1].
The mod's profiles therefore copy the template's shape and not its sandbox block, whose day length is the pacing decision's to set.

Every profile of this mod pins the golden fixture, because every reading this library compares against was taken on it [#1253/C/one-fixture].
The profile's own fixture wins over a typed fixture flag, since it is the fixture its sandbox keys were validated against [#1797].
The mod enters by its own folder, named in the profile by the engine-resolved id of the mod-info file the build reads and never by the folder's name [#1558].
Placement copies it into both sides' per-run caches from one source map, so the server and the client cannot run different copies [#1823/M/n=1].
The harness mod is prepended when a profile leaves it out, because without it there is no bus and no probe [#1800].
No profile touches the fixture: the mods overlay a restored per-run copy, and the sandbox block is merged into that copy's own options file [#1792].
A resident neighbour named by its workshop item rather than by its mod id is a defect whenever the item ships more than one mod [#1617/C/snapshot].

The plan names four profiles, each pinning the golden fixture and the harness, and each proving one thing.

| profile | mod list | sandbox block | what it proves | tags |
|---|---|---|---|---|
| the mod's acceptance profile | the harness and the mod | none, so every option is the fixture's | that the mod arrived on both sides and its files ran in both Lua states | [#1793, #1825/M/n=1] |
| the mod's scenario profile | the harness and the mod | none, or the day length if the pacing decision moves it | the mod's numbers over game days, beside the baseline pair run on the same profile | [#1253/C/one-fixture, #1814/M/n=3, #2071/C/inference] |
| the vanilla-off profile, written only if the design switches vanilla nutrition off | the harness and the mod | the nutrition option off, set in the block and never at runtime | which of the update's arms the option actually freezes, beside the scenario profile's baseline | [#1127/C/C-only, #1277/C/open] |
| the stack profile | the harness, the mod and each resident neighbour, every one by its engine-resolved id | none | that the mod's gates still pass beside the mods a live server runs | [#1558, #1617/C/snapshot] |

The four named experiments this page owns bring profiles of their own, each in the acceptance profile's shape [#2050].
The neighbours the stack profile names are [packaging.md#resident-stack](packaging.md#resident-stack), which owns that reading.
A green run from any of these profiles says only that the session ran clean, because the game answers a missing mod with a warning and a clean boot [#1793].
What each profile proves is carried by its verification rows, which [the rows section](#verify-rows) sets out.

<a id="mod-scenarios"></a>
### The scenarios this mod runs

A scenario is a Lua test that runs on the world's own clock and hands its samples to a Python evaluator [#1772].
The mod's scenarios use the test layer as it ships: registered under the server's scenarios folder, sampled on the game-minute scheduler and graded by an evaluator keyed by the scenario's name ([#1786], [harness.md#scenarios](../platform/harness.md#scenarios)).
Every one but the client mirror below runs server-side, as the shipped ones do, because the server owns nutrition [#1782].
Each carries a backstop a clear margin above its finisher, because the backstop is armed first and wins a same-minute tie [#1774].
Every Java member a scenario touches goes through the guarded call, because an unguarded nil call aborts the rest of the once-a-minute body it fires in [#1781].
An evaluator that raises must not leave the world accelerated, which is why the runner restores the multiplier from a cleanup block, after the evaluator has run [#1704].

Four scenarios make up the plan, and each is evidence for one thing.

| scenario | what it runs | what it is evidence for | tags |
|---|---|---|---|
| the vanilla baseline with the mod loaded | the two shipped three-day runs, gain and fast, on the mod's scenario profile | that the mod leaves vanilla's weight arm where the decoded model puts it, if the design leaves that arm on | [#0157, #0159/M/one-fixture, #0160/M/one-fixture] |
| the mod's store over game days | a dose schedule into the mod's own store, sampled hourly, with the mod's own decay model integrated by its own evaluator | that the store moves on a live server as the mod's formula says | [#1772, #1786] |
| the vanilla-off pair | the baseline pair on the vanilla-off profile, each arm read against its own baseline | which arms freeze when the option is off, if the design switches it off | [#1277/C/open, #1136/C/C-only] |
| the client mirror | the same layer on the client side, reading the mod's display copy of its store | how far the copy a client draws trails the store it mirrors | [#1784, #1483] |

The baseline pair is the reference every other scenario is graded beside.
The decoded weight model reproduced on the live server on both the gain and the loss arm, each run's prediction integrated from its own calorie trace ([#0159/M/one-fixture, #0160/M/one-fixture], [nutrition-core.md#verified](../facts/nutrition-core.md#verified)).
The mod's own store scenario takes the same shape: drive one store from the server, sample the whole object on a fixed game-clock cadence, integrate the model over the samples the run produced, and compare against what the server reports.
That shape is what turns a formula read off the code into a statement about a live server, and a replacement model has to pass it before it is trusted in play.
What the shipped check proves is narrower than its numbers, because it asserts one thing, the weight delta over the run [#0170/M/one-fixture].
A mod scenario that needs a rate, a threshold crossing or a multiplier asserted writes that assertion into its own evaluator, because the existing one asserts none of them [#0170/M/one-fixture].
The shipped evaluator's tolerance is a fraction of the predicted delta with a floor in kilograms, and a mod evaluator sets its own beside it rather than borrowing it [#0157].

The client-mirror scenario is the one the runner is ready for and has never run: the client side is wired end to end with nothing registered on it [#1784].
Its reading is a staircase rather than a curve, so it is graded the way [the grading reading](#grading) sets out and never against the server's samples point for point [#1483].
A scenario doses through the setter rather than through food, so it tests a model and never an intake path [#0170/M/one-fixture].
The mod's intake math is therefore a driver's reading, a sequence of probes that queues a real eat from the client and reads both sides, as the harness page's procedure lays out ([harness.md#procedure](../platform/harness.md#procedure)).
The scheduler self-test is no check on pacing, because it passed on a run that overran: every assertion it makes is counted in ticks, and only the run's fitted cadence says whether the clock kept time ([#1813/M/n=1], [#1787]).

<a id="verify-rows"></a>
### The verification rows and what a failing one means

A verification row is a gate on the session and never a measurement in it.
Its expectation is a substring of the dumped acknowledgement, which matches at any nesting and so cannot express absence or a numeric comparison [#1828].
A failed row makes the result a named failure: on a plain run it also skips the hold, and on a scenario it folds into the result after the test has run [#1829].
Rows are asked only once the client is ready, so a client row never runs on a client that has hung [#1769/M/n=1].
Of the four nets against a missing mod, the rows are the only one that proves effect rather than arrival [#1818].
The standing contract fixes what a row may be: certain to pass if the mod loaded at all, never the reading that is the point of the session, and placed on the side whose loading is not itself the question [#2050].

The rows this mod's profiles carry follow from that contract.

| side | what the row reads | why it passes only if the mod loaded | tags |
|---|---|---|---|
| server | the harness's own version global through the global walk, sent first | it is the control that says the walk works on this side, so a miss on the next row names the mod rather than the path | [#1760] |
| server | a global the mod's shared file sets on its first line | it answers the moment the file has run, whatever the rest of the mod does | [#1760, #2050] |
| client | the same pair on the client | the shared file runs in both Lua states, and a probe asked of both sides proves both | [#1825/M/n=1] |
| server | one item only the mod declares, in its own module, if it ships new items | a new name collides with nothing, so the read cannot answer with the mod absent the way a vanilla item it overrides would; one side's answer says nothing about the other's | [#1020/M/n=1, #1724] |
| client | one translation key under the mod's own prefix, if it ships translations | a miss returns the key itself and vanilla defines no key with that prefix, so a hit proves the mod's translation tree loaded | [#1718, #1502/M/n=1] |

The translation row doubles as the positive control a session that calls the text read has to carry, since a session whose text reads all miss cannot tell a missing route from a broken command [#1250/M/one-side].
A failing row means the session was not the one asked for: the mod did not load, loaded on one side only, or its gate global moved.
It is never a finding about the mod's numbers, which no row can express [#1828].
The reading a session exists for — a store's value, a decay, a desync — belongs to a scenario's evaluator or a driver's verdicts.
A profile whose session may raise puts its gates on the server and caps the client wait, because the debug client parks on the first mod error and a client row then never runs ([#1769/M/n=1], [#1246/M/n=2]).
A run that reports failure on a probe raising by design is the profile working, and the grading comes off the artifact [#1767/M/n=1].

<a id="scenario-inputs"></a>
### The inputs a multi-day nutrition scenario fixes

A multi-day nutrition scenario fixes its inputs before it starts: the subject, the sandbox, the pacing, the management of hunger and thirst, and the dose schedule.
Each is fixed for a reason a row gives.

The subject is the fixture's admin character, resolved by username from the online players, so the client stays attached even though the test runs on the server [#1779].
It stays inside the weight slice the shipped check was walked on, with no band trait held, because that is the only state the check covers [#0170/M/one-fixture].
The slice matters because the gain and loss thresholds the evaluator integrates across are functions of the weight [#0149/C/C-only, #0151/M/one-fixture].

The sandbox is the fixture's own, option by option in [the roll-up](#sandbox), because every nutrition reading in this library was taken at those values [#1253/C/one-fixture].
The pacing is fixed before the run too, because the scheduler's clock is game minutes and a pace that outruns it leaves every rate fitted against it read off a clock that was not keeping time [#1787].
Which of the three clocks carries a run is the decision the options table below puts, and whichever it is, the day length and the multiplier stay inside the cadence ceiling together [#1814/M/n=3].
Every sample carries the game minute, the world age and the wall clock, and rates are fitted against the world age, so the multiplier cancels out of every rate a scenario reports [#1778, #0452/M/one-fixture].

The shipped nutrition runs pin hunger and thirst after every sample, and the reason is a death rather than tidiness [#1782, #0158/M/one-fixture].
Anything that fills the calorie store must manage hunger and thirst too: unattended, the level-4 thirst drain kills in about 35 game-hours on a 90-minute day and about 38 on the 60-minute default [#0179/M/one-fixture].
The first figure rests on one measured run and the second is arithmetic on it [#0179/M/one-fixture].
The calorie setter never touches hunger or thirst, so a scenario that doses calories leaves both clocks running [#0172/M/one-fixture].
The thirst crossing does not depend on the day length while the health drain does, which is why the two day lengths give two different deaths ([#0175/C/arith.], [body-and-weight.md#hunger-thirst](../facts/body-and-weight.md#hunger-thirst)).
Pinning is a control rather than a thumb on the scale, because neither the weight update nor the calorie update has a hunger or thirst term [#0178].
A subject that dies anyway spoils the run without failing it loudly: the update stops on a corpse while an external calorie write still lands, so the trace keeps a plausible calorie line beside frozen stores ([#0176/M/one-fixture, #0177/M/one-fixture], [nutrition-core.md#verified](../facts/nutrition-core.md#verified)).
The unpinned gain run is the precedent, its subject dead partway through and only its alive window citable [#0158/M/one-fixture].
The evaluator fails a run outright on a dead sample [#1786], and neither that verdict nor the thirst sample column has yet run on a live session [#0171/C/snapshot].
A scenario that wants the thirst clock itself as its reading drops the pin and reads the death as its result.

The dose schedule is the last input, because the calorie ceiling rather than the rate constant bounds a fed character [#0165/M/one-fixture].
A schedule that doses past the ceiling loses the excess to the clamp, so a scenario reads the store it got rather than the dose it asked for ([#0022/M/n=2], [nutrition-core.md#clamps](../facts/nutrition-core.md#clamps)).
The first day of a fed run is a ramp from an empty store, so a per-day rate read off that day is not the steady rate [#0162/M/one-fixture].

<a id="owned-experiments"></a>
### The experiments this mod owns

Four named experiments are this page's to run, because the design cannot be finished without them.
Two settle the wall map's unknown verdicts — whether a mod may override a vanilla translation key, and whether the drink path can be hooked [#1164/C/C-only/open, #1133/C/C-only/open].
The third measures the trait route the wall map reads from the code: whether a server push after a trait write reaches the client's trait list within its cadence, and whether a trait the mod registers behaves the same ([#2099/C/open], [wall-map.md#g4](../reference/wall-map.md#g4)).
The fourth tests the moodle framework, the widget route the wall map leaves a moodle beside a widget of the mod's own, none of whose legs has been measured ([#1295/C/open], [wall-map.md#d4](../reference/wall-map.md#d4)).
The other named experiments go to the build-out or stand alone, as [experiments.md § Owners and the cost roll-up](../reference/experiments.md) assigns them, and the build-out's decide how the mod is built rather than whether a part of it can be.
Each spec is [`experiments.md`](../reference/experiments.md) and each open row the four carry is indexed on [`open-questions.md`](open-questions.md); this page restates neither.

| experiment | what it settles | what makes the reading discriminate | what it costs | tags |
|---|---|---|---|---|
| [X4](open-questions.md#x4) | whether a server push after a trait write reaches the client's trait list, whether a client read sees the new trait within the push cadence, and whether a trait the mod registers behaves the same | the server's trait list is made non-empty first, because no run has yet held a non-empty list on either side, and the client's list is read before the push as the control | a single session with a new trait mod and a harness addition that pushes the trait list, sharing its boot with the weight-lot ladder and running its band edges last | [#2099/C/open, #2595/C/C-only, #1291/C/open] |
| [X5](open-questions.md#x5) | whether a mod translation file displaces a vanilla key or the merge keeps vanilla's | a new interface key the mod ships must hit in the same run, and the server arm is a control because a dedicated server resolves no display name | a single short session with a new translation mod | [#1276/C/open, #1250/M/one-side, #0848/M/n=1] |
| [X13](open-questions.md#x13) | whether a server-side wrapper of the drink action fires, and on which side | the shipped drink command moves the stores in the same session, so a silent wrapper reads as a silent Lua route rather than a silent fluid path | a harness addition that queues the real drink action, landed in its own commit, then a single session | [#1279/C/open, #1255/C/C-only] |
| [X29](open-questions.md#x29) | whether the moodle framework loads whole, whether its configuration file runs, and whether a moodle registered through it renders above its lowest level | each leg has its own reading, and a registered moodle held at its lowest level on the client would close the framework route and leave the mod a widget of its own | a desk read of the framework's own Lua first, because its interface is unread and a probe cannot be written blind, then a single session | [#1295/C/open, #0884/C/C-only/open, #1115/M/n=1/open] |

The minutes, sessions and write-up ceiling behind the cost column are [experiments.md § Owners and the cost roll-up](../reference/experiments.md), and the whole named programme is a ceiling rather than a commitment [#1973].
The trait experiment decides what a client may do with a band: the trait list reaches the player's own client on the player-fields packet's trait block and on the timed experience packet, read from the code and never exercised, so until [the live measurement](open-questions.md#x4) lands a client-side display or derivation that reads a band rests on an unmeasured route, which is why anything keyed on a band is evaluated on the server or its trait list pushed after each write ([#2595/C/C-only], [#2718/C/C-only], [#2727/C/inference], [mp-sync.md#authority](mp-sync.md#authority)).
The translation experiment decides whether the rebalance may rename a vanilla food, the one question the translation merge leaves open [#1164/C/C-only/open].
The drink experiment decides whether an intake correction can reach fluid drinks at all, since the fluid path has no eat hook ([#1133/C/C-only/open], [eat-and-cook-hooks.md#hook-options](eat-and-cook-hooks.md#hook-options)).
The framework experiment decides whether the mod draws its moodle through the framework or through a widget of its own: a registered moodle held at its lowest level on the client would leave the mod its own widget alone ([#1115/M/n=1/open], [ui-and-moodles.md#moodle-route](ui-and-moodles.md#moodle-route)).
Each runs under the standing contract — a profile in the acceptance profile's shape, a driver in the house shape with client-first paired reads, and gates that never measure [#2050].
The drink experiment's harness addition lands before its session in a commit of its own, with the command table regenerated and the next acceptance run as its smoke test ([#1279/C/open], [harness.md#procedure](../platform/harness.md#procedure)).
Until each lands, its area page states it as a wall, and this page carries the same four under [Walls and bounds](#walls).

<a id="grading"></a>
### How a cross-side comparison is graded

A cross-side comparison is graded on the server's reading, because for everything the server owns the client's reply is a once-a-second mirror [#1826].
The client's half is a reading about the mirror, and a test that reads only the client tests the mirror.
Drivers read the client first and the server second at every tag, so the skew between the two halves has a known sign ([#1485/M/n=1], [#2050]).
The two halves are separate bus round trips, and without a fixed order the sign of a gap would follow the read order rather than the engine.
Each read carries the driver's own wall stamps on either side of it, and a tag is named by the offset those stamps measured rather than by the sleep that was asked for [#1708/M/n=1].
A tag name is nominal and never a clock reading: one snapshot named for three seconds after a transmit opened well after that, because the snapshot before it had taken that long to walk both sides [#1341/M/n=1].
A snapshot inside a write's push window is an arrival-latency reading and is reported ungraded, each graded snapshot using its own time since the last write [#1488/M/n=1].

What a naive check gets wrong is the staircase.
A client-side reader of the nutrition store steps only when a packet lands while the server ramps, so equality is the wrong verdict to look for and a check that demands it reads a timing gap as a desync ([#1483], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
The graded form is a band built from each snapshot's own signed read skew and the store's decay rate, so a slow round trip widens the band instead of failing the row [#1485/M/n=1].
Every macro gap of the one session graded that way landed inside its band, which validates the band as consistent with the push rather than as tight [#1486/M/n=1].
Weight needs a band of its own sign, because the client never recomputes it and its gap runs the other way from the macros' on a gaining subject; the losing side of that band is untested [#1484/M/n=1].
Weight also crosses the wire narrowed to a float, so the two sides' weights are never equal to the bit and a bit-equality check fails by construction [#1487/M/n=1].
A mod value the client derives from the store inherits the same staircase, and it is graded with the same band.

A reading discriminates only when the two sides were first made to differ.
No run has yet held a non-empty trait list on either side, so the two sides' agreement in every run that could have shown a trait crossing answered nothing [#2595/C/C-only].
Every experiment this page owns names the control that makes its sides differ, and a reading that comes back trivial, unmeasured or falsified is written as such rather than re-run ([harness.md#driver-rules](../platform/harness.md#driver-rules)).

Two reply shapes are stale or side-relative by construction and are never graded as desyncs.
The nutrition setter's own acknowledgement carries the weight-direction flags one tick stale, because the weight update has not run again yet [#1492/M/n=1].
A container's string ends in a per-process identity hash, so comparing it across sides reads as a desync that is not one [#1507/C/n=1].

A probe that reads a food tooltip meets two hazards before it reads anything about the mod.
The food tooltip's nutrition block opens on any of three gates — the debug tooltip option in debug mode, a packaged food whose label the viewer can read, and the Nutritionist traits — so it can show on a character holding neither trait [#2645/C/C-only].
The harness adds the debug flag to the admin account's client, the default account a profile attaches ([#1710], [harness.md#profiles](../platform/harness.md#profiles)).
A tooltip probe therefore reads the trait gate only on a client launched without the flag and on a food with no label the viewer can read, and the plan's tooltip readings are about the mod's own band, never about the vanilla block's gate.
On the stack profile the tooltip's render is also the end of a wrap chain that several resident mods build with no sentinel, one of them calling its own fork of vanilla's render instead of the chain [#2568/C/snapshot].
What a tooltip probe draws there is that chain's output, so the mod's own band is graded on the acceptance profile and the stack profile asks only that the band still appears.

The number format bounds every comparison's resolution.
No bit-level claim may rest on an artifact written before the harness commit `291f977`, whose encoder rendered every non-integral number at six decimals [#1965].
A baseline written before that commit is compared at the older resolution and never at the bit.
The server error count is a classifier's output rather than a fault count, so a grading reads the error list itself [#1764].

<a id="sandbox"></a>
### The sandbox roll-up

Every sandbox option this mod's evidence depends on is listed below with the value the runs used, carried by citation from the row that owns it.
The values themselves are stated on the owner pages, so every cell here is an option name, a word and a tag.

| option | what it reaches | the value every nutrition run used | the runs that moved it | owner |
|---|---|---|---|---|
| `Nutrition` | the update tick only — the macro drain, the calorie burn and the weight update — and never intake [#0067, #0555] | the fixture's, on [#0087/M/one-fixture] | one client-local flip each way, with the server's drain unread [#0090/M/n=1]; the three-day check carries no off control [#0170/M/one-fixture] | [eating-pipeline.md#sandbox](../facts/eating-pipeline.md#sandbox) |
| `StatsDecrease` | hunger, thirst and fatigue, never calories [#0553] | the fixture's default [#1809/C/C-only] | one body-side run set every value through the live setter [#0483/M/n=1, #0556/M/n=1] | [body-and-weight.md#sandbox](../facts/body-and-weight.md#sandbox) |
| `FoodRotSpeed` | the elapsed hours the age formula converts into days [#0225/C/C-only] | the fixture's default [#1809/C/C-only] | none [#1830/C/C-only/open] | [spoilage.md#sandbox](../facts/spoilage.md#sandbox) |
| `FridgeFactor` | aging inside a powered fridge or freezer [#0224/C/C-only] | the fixture's default [#1809/C/C-only] | none [#1830/C/C-only/open] | [spoilage.md#sandbox](../facts/spoilage.md#sandbox) |
| `DayLength` | the clock every timed scenario is fitted against [#1809/C/C-only] | the fixture's [#1253/C/one-fixture, #0893/C/arith.] | the acceptance run's profile and two scheduler self-tests set a shorter day [#1807/M/n=1, #1813/M/n=1, #1816/M/n=1] | [harness.md#sandbox](../platform/harness.md#sandbox) |
| `Zombies` | the world's zombie population, fixed when the world is generated [#1811/C/inference] | the fixture's, none [#1701, #1807/M/n=1] | none: a change needs a fresh fixture [#1811/C/inference] | [harness.md#pzt](../platform/harness.md#pzt) |

One fixture and one value per option is the pattern the whole table shares, and it is the bound every nutrition reading carries [#1253/C/one-fixture].
Every option the nutrition work names is settable from a profile, and only the day length has been set by one [#1809/C/C-only].
A live sandbox write applies at once on a running dedicated server, measured on the server side of one run [#0556/M/n=1].
A client-local flip of the nutrition option reads back on the client, leaves the server's drain unread and leaves the option's Lua mirror stale ([#0090/M/n=1, #0091/M/n=1], [eating-pipeline.md#sandbox](../facts/eating-pipeline.md#sandbox)).
That is why the vanilla-off profile sets the option in its sandbox block, which is the server's own configuration for that run.
The block merges into the restored file rather than replacing it, so an option a profile leaves out keeps the fixture's value [#1806].
An option the world generator consumed is not retroactive, so an option that shapes the world is changed by provisioning a fresh fixture rather than by a profile [#1811/C/inference].
Nested options are out of the sandbox block's reach, and the answer there is again a fresh fixture [#1831].
The mod's own options are out of its reach too, because the block's key pattern takes only a top-level key and never names a mod option or its prefix [#2458/C/C-only].
How a test sets one is therefore a decision under [Open](#open), and the remedies are [sandbox-options.md#open](../platform/sandbox-options.md#open)'s.

## Options

A nutrition scenario spans game-days, and the harness offers three clocks to carry it across them.
Each costs something different and hits a different limit, and the cost of each is the harness's row rather than this page's.
No verdict row covers pacing, so the rows run from the slowest clock to the fastest.

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| real time | nothing to fit or validate, the world running at the fixture's own rate; a game day then lasts the fixture's whole day length in wall time, so a multi-day run occupies the machine for hours | a multi-day test at real time cannot finish inside any timeout worth waiting for, which is why the scenario runner ends a run whose time-speed command is refused rather than wait | [#0893/C/arith., #1783] |
| a shorter `DayLength` in the profile's sandbox block | one sandbox key, which survives the server's boot-time rewrite; every game-time rate holds, while every real-second figure moves with the day | the cadence ceiling binds the day length and the multiplier together, so a shorter day lowers the multiplier the scheduler keeps up with; every baseline in this library sits at the fixture's day length | [#1807/M/n=1, #1813/M/n=1, #1816/M/n=1, #0451, #1253/C/one-fixture] |
| the time-speed command at the fixture's day length | one runner flag, restored from a cleanup block after the evaluator; the three shipped three-day runs kept exactly one tick per game minute at the ceiling | above the ceiling the scheduler falls behind the world clock and the run sets its suspect flag; where the true ceiling sits above the known-safe demand is unmeasured | [#1814/M/n=3, #0156/M/one-fixture, #1704, #1787, #1815/M/n=1/open] |

At which pacing does each of this mod's timed scenarios run — real time, a shorter `DayLength` in its profile, or the time-speed command at the fixture's day length?

## Walls and bounds
<a id="walls"></a>

- Every baseline this plan compares against sits on one fixture, one admin character and one day length, and most measured rows are one session ([#1253/C/one-fixture], [harness.md#walls](../platform/harness.md#walls)).
- The plan drives one client at most: every verdict it leans on is bounded to one dedicated server with one client, so what a second client's copy holds, and whether a push reaches every client, cannot be tested here [#1256/C/one-fixture].
- The driven client is a debug client, and the first mod Lua error parks it in the debugger's modal break, so a raising path in this mod can be driven on the server side only, and a release client is unmeasured [#1246/M/n=2].
- Every client-side reading of a session whose debug client parked is unusable, so such a session is a server reading only [#0869/M/n=2].
- No client-side scenario has ever run: the client runner is wired and every registered scenario lives under the server folder [#1784].
- Persistence cannot be tested yet: `modData` across a save and reload is stated and never measured, and no run has restarted a world ([#1255/C/C-only], [open-questions.md#x28](open-questions.md#x28)).
- The trait route is read from the code and its arrival is unmeasured: the trait list reaches the owning client on the experience packet and on the player-fields packet's trait block, and no run has yet held a non-empty list on either side ([#2595/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4), [open-questions.md#x4](open-questions.md#x4)).
- The translation override is unmeasured: the translator merges rather than shadows, and no run has shipped a key that redefines a vanilla one ([#1164/C/C-only/open, #1276/C/open], [open-questions.md#x5](open-questions.md#x5)).
- The drink path's interceptability is unmeasured: the fluid path has no eat-hook twin and the Lua drink-driver path has never been driven ([#1133/C/C-only/open, #1279/C/open, #1255/C/C-only], [open-questions.md#x13](open-questions.md#x13)).
- No measured moodle route exists: the open route is a Lua-drawn widget, the framework's or the mod's own, and none of the framework's legs has been booted ([#1295/C/open], [wall-map.md#d4](../reference/wall-map.md#d4), [open-questions.md#x29](open-questions.md#x29)).
- Nothing on the bus executes a craft, so a crafted food's nutrition is read from the code and its create hooks stay unmeasured [#1248/C/C-only].
- No bus command synthesises a click or a key press, so a panel of this mod's own keeps its state invisible to the bus until a human clicks [#1498/M/n=1].
- A sandbox option that is nested, or that the world generator consumed, is out of a profile's reach, and changing one means a fresh fixture ([#1831], [#1811/C/inference]).
- A profile's sandbox block cannot set the mod's own options: its key pattern matches only a top-level key and excludes a nested-table opener, so the settable list never names a mod option or its prefix [#2458/C/C-only].
- A tooltip probe on the driven client reads a debug client's tooltip, whose nutrition block can show without the Nutritionist trait, and on any client a packaged food with a readable label shows the block too ([#2645/C/C-only], [#1710]).
- A tooltip probe on the stack profile reads the end of a sentinel-free wrap chain the resident mods build, one of whose links bypasses the chain with its own fork of vanilla's render, so it never reads the mod's wrap alone [#2568/C/snapshot].
- No bit-level claim may rest on an artifact written before the harness commit `291f977` [#1254/C/snapshot].

Not covered: a second machine or any continuous-integration host, a Linux dedicated server, a release client, a session with two driven clients, a save-and-reload cycle, and any session a person drives rather than the bus — every reading this plan can take is one Windows machine driving one dedicated server and at most one debug client.

## Open
<a id="open"></a>

- Whether a server push after a trait write reaches the client's trait list, whether a client read sees the new trait within the push cadence, and whether a trait the mod registers behaves the same — settled by making the server's trait list non-empty first and reading the client's in client-first pairs before and after a server-side trait push, the pre-push read as the control; -> X4 ([#2099/C/open, #2595/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4), [open-questions.md#x4](open-questions.md#x4)).
- Whether a mod translation file displaces a vanilla key or the merge keeps vanilla's — settled by a mod that redefines one vanilla item-name key beside a new interface key that must hit in the same run; -> X5 ([#1276/C/open, #1164/C/C-only/open], [open-questions.md#x5](open-questions.md#x5)).
- Whether the drink path is interceptable the way the eat path is — settled by a harness command that queues the real drink action, then one session counting a server-side wrapper's fires on each side against the shipped drink command as the control; -> X13 ([#1279/C/open, #1133/C/C-only/open], [open-questions.md#x13](open-questions.md#x13)).
- Whether the moodle framework loads whole, runs its configuration file and renders a registered moodle above its lowest level — settled by a desk read of its Lua, then one session reading its globals on both sides and the client's moodle block; -> X29 ([#1295/C/open, #0884/C/C-only/open, #1115/M/n=1/open], [open-questions.md#x29](open-questions.md#x29)).
- With vanilla nutrition switched off, which of the update's three arms actually freezes — settled by the baseline pair run on the vanilla-off profile against its own baselines; the build-out owns it, and this plan needs it only if the design switches the option off; -> X7 ([#1277/C/open], [open-questions.md#x7](open-questions.md#x7)).
- Whether `modData` survives a save and reload — settled by a boot, a write, a teardown and a second boot on the same run directory beside a control that must miss the key; the build-out owns it; -> X28 ([#1294/C/open], [open-questions.md#x28](open-questions.md#x28)).
- Which sandbox options survive a restore — settled by a profiled run that sets each nutrition option on a restored world and reads it back; no `X` id ([#1830/C/C-only/open], [harness.md#open](../platform/harness.md#open)).
- Where the cadence ceiling really sits above the known-safe demand — settled by scheduler self-tests that step the demand past it and read the fitted tick rate; no `X` id ([#1815/M/n=1/open], [harness.md#walls](../platform/harness.md#walls)).
- The thirst sample column and the evaluator's dead-subject verdict have never run on a live session — settled by the next pinned three-day run's committed artifact; no `X` id [#0171/C/snapshot].
- That the multiplier getter is scaled rather than the argument passed, that the time multiplier must always be changed through the broadcast admin command, and how a multiplier change re-syncs the client's clock are unverified, and their owner states them with their bounds ([#1869/M/uncommitted/unverified, #1870/M/uncommitted/unverified, #1871/M/uncommitted/unverified], [harness.md#open](../platform/harness.md#open)).
- That a small cross-side calorie gap in the witness spike is the sampling skew of a once-a-second mirror is unverified, and its owner states it with its bound ([#1875/M/uncommitted/unverified], [harness.md#open](../platform/harness.md#open)).
- Decision: at which pacing the mod's timed scenarios run — forced by the cadence ceiling binding the day length and the multiplier together while every baseline sits at the fixture's day length [#1814/M/n=3, #1253/C/one-fixture].
- Decision: whether the mod's load checks are verification rows or scenarios — forced by a verification expectation being a substring that cannot express absence or a numeric comparison [#1828].
- Decision: whether the mod ships a client-side scenario for its display copy — forced by the client runner being wired with nothing to run and by every client read of a live store being a staircase [#1784, #1483].
- Decision: whether any scenario moves a sandbox option off the fixture's value — forced by only the day length having been set by a profile, so a moved option buys a new baseline [#1809/C/C-only, #1253/C/one-fixture].
- Decision: in which order the four owned experiments are bought — forced by the framework experiment needing a desk read and the trait and drink experiments each a harness addition before their sessions, while the translation experiment needs neither [#1295/C/open, #1279/C/open, #2099/C/open].
- Decision: how this mod's tests set its own sandbox options — a harness merge that writes a profile's nested block into the mod's table in the server file, a two-pass run that boots once so the server writes the block and then merges into it, or a live set over the bus after boot, which reaches no consumer that reads at server start — forced by the profile block's top-level-only key pattern [#2458/C/C-only]; the harness change lands before any run that sets a mod option.
- Decision: whether a scenario pins the thirst clock or reads the death as its result — forced by an unattended thirst drain killing the subject partway through a multi-day run [#0179/M/one-fixture].

## See also

- [`../platform/harness.md`](../platform/harness.md) — the instrument: every mechanism this plan uses, from the profile to the artifact.
- [`../reference/harness-commands.md`](../reference/harness-commands.md) — the generated command table every profile, scenario and driver calls into.
- [`../reference/experiments.md`](../reference/experiments.md) — the specs of the four owned experiments, their owners and the cost roll-up.
- [`../facts/nutrition-core.md`](../facts/nutrition-core.md#verified) — the three-day verification the baseline pair reproduces.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#staircase) — the staircase a client-side read draws and the band it is graded against.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#hunger-thirst) — the thirst clock that kills an unattended subject, and the body-side sandbox option.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#sandbox) — the nutrition option and what a runtime flip of it does.
- [`../facts/spoilage.md`](../facts/spoilage.md#sandbox) — the rot options the roll-up carries.
- [`../platform/sandbox-options.md`](../platform/sandbox-options.md#open) — the mod's own options and the remedies for setting one from a test.
- [`../platform/client-ui.md`](../platform/client-ui.md#tooltip) — the tooltip a probe reads and the gates on its nutrition block.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#api-surface) — the resident wraps a stack-profile tooltip probe reads through.
- [`mp-sync.md`](mp-sync.md) — which side owns each quantity this plan grades.
- [`ui-and-moodles.md`](ui-and-moodles.md) — the display surfaces the trait, translation and framework experiments decide.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md) — the intake seats the drink experiment decides for fluids.
- [`new-nutrients.md`](new-nutrients.md) — the store a mod scenario doses, and the rule on the nutrition option.
- [`packaging.md`](packaging.md) — the resident stack the stack profile names.
- [`open-questions.md`](open-questions.md) — every open row and experiment named above.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the owned experiments settle.
