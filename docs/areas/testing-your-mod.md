# Testing your mod — the plan this mod runs under the harness
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: this mod's test plan as a reading of the harness — the profiles it will ship, its scenarios and verification rows, the inputs a multi-day nutrition scenario fixes, the four named experiments it owns, how a cross-side reading is graded, what a tooltip probe can read and the sandbox values its evidence rests on, the mod's own options among them; every mechanism is `platform/harness.md`, the command table `reference/harness-commands.md` and the experiment specs `reference/experiments.md`

## Rules
<a id="rules"></a>

- Never read a green run as evidence that a mod loaded: the game answers a mod it cannot find with a warning and a clean boot, so the run fails fast at the server-started mark and the bus probes are what prove effect [#1793].
- Name a profile's mod by the engine-resolved id: that is the `id=` of the `mod.info` the build actually reads — the newest `42[.x[.y]]/` folder first, then `common/`, then the mod root — and never the folder name [#1558].
- Write every `[[verify]]` row as a gate certain to pass if the mod loaded at all, never as the reading the session exists for: an expectation is a substring of the dumped acknowledgement, so it cannot express absence or a numeric comparison [#1828, #2069/C/inference].
- Gate a probe that can stall the client on the server side: verification is asked only after the client is ready, so a stalled session's client row never runs and the run records a verification error instead of a pass or a fail [#1769/M/n=1].
- Cap the client wait in the profile whenever a probe can hang the client: the readiness wait is capped from the profile's client timeout, whose default is 300 seconds, and a profile that leaves the default sits out the full wait plus teardown — 384 seconds for a five-second hold — on a client that was never going to answer [#1768].
- Take the measurement on the side that owns the quantity: for nutrition, hunger and thirst, item aging and perks the server's reading is the measurement and the client's is a once-a-second mirror [#1826].
- Read the mod's state in a driver on the server, and read a client mirror only after a fresh `mirror.request` has answered: the client's mirror copy is a request-time snapshot of the server's numbers of that moment [#3012/C/inference, #2974/M/n=1].
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

The mod ships three profiles, `nr-accept`, `nr-takeover` and `nr-overlay`, and each is seeded from `testing/profiles/mod-under-test.toml`, the acceptance profile whose shape every profile copies [#2050].
That file carries the harness and one workshop mod on the golden fixture, with inline verification rows and a single sandbox override, and the harness page lists it among its worked examples ([`../platform/harness.md`](../platform/harness.md)).
Its override shortens the day, which a plain run never notices and a timed scenario does: a fifteen-minute day at a multiplier of thirty overran the game-minute scheduler [#1813/M/n=1].
The mod's profiles therefore copy the template's shape and not its sandbox block: `nr-accept` sets no option, and `nr-takeover` and `nr-overlay` set the day length to its shortest value beside the mod's own mode in a nested `[sandbox.NR]` table [#2807/M/n=1].

Every profile of this mod pins the golden fixture, because every reading this library compares against was taken on it [#1253/C/one-fixture].
The profile's own fixture wins over a typed fixture flag, since it is the fixture its sandbox keys were validated against [#1797].
The mod enters by its own folder, named in the profile by the engine-resolved id of the mod-info file the build reads and never by the folder's name [#1558].
Placement copies it into both sides' per-run caches from one source map, so the server and the client cannot run different copies [#1823/M/n=1].
The harness mod is prepended when a profile leaves it out, because without it there is no bus and no probe [#1800].
No profile touches the fixture: the mods overlay a restored per-run copy, and the sandbox block is merged into that copy's own options file [#1792].
A resident neighbour named by its workshop item rather than by its mod id is a defect whenever the item ships more than one mod [#1617/C/snapshot].

The mod ships three profiles, the plan names two more, the intake plan's live runs added six experiment profiles, the body plan's added four and the interface plan's added four, each pinning the golden fixture and the harness, and each proving one thing.

| profile | mod list | sandbox block | what it proves | tags |
|---|---|---|---|---|
| `nr-accept`, the acceptance profile | the harness and the mod | none, so every option is the fixture's | that the mod arrived on both sides and its files ran in both Lua states | [#1793, #1825/M/n=1] |
| `nr-takeover`, the takeover profile | the harness and the mod | the day length and `[sandbox.NR] Mode = 1` | that the takeover handler registers and tracks vanilla's stats over game hours, beside the baseline of the same fixture | [#2807/M/n=1, #2809/M/n=1, #1253/C/one-fixture, #1814/M/n=3, #2071/C/inference] |
| `nr-overlay`, the baseline profile | the harness and the mod | the day length and `[sandbox.NR] Mode = 2` | the overlay boot the takeover arm is read against, the same fixture and day length with vanilla's own stat update running | [#2807/M/n=1, #2809/M/n=1] |
| `x13-drink`, the drink-wrapper profile | the harness, the mod and `TKX_DrinkHook` | none | that a server-side wrapper of the drink action fires on the server while the client's counters stay at 0, against a control in the same session, the shipped direct drink, that moves the stores and fires nothing (run `x132d-20261005-060046`) | [#2825/M/n=1, #2826/M/n=1, #2827/M/n=1] |
| `x13-eat`, the probe-first eat profile | the harness, `TKX_ItemOverride`, `TKX_Nutrient`, `TKX_EatHook` and the mod, in that `Mods=` order | none | that two save-and-replace wrappers of the eat completion with the probe loading first form a call cycle on every eat, which is the run's whole reading and is kept as evidence (run `x132e-20261005-062748`) | [#2835/M/n=1] |
| `x13-eat-b`, the mod-first eat profile | the same mods with the mod listed before the probe | none | that the eat hook fires once per portion, that the two fractions differ on every eat after the first, that a finishing eat lands NaN and that the harness stop does not cancel a started eat (run `x132e-20261005-063700`) | [#2830/M/n=1, #2831/M/n=1, #2832/M/n=1, #2834/M/n=2] |
| `x13-coboot`, the quality-stack co-boot | the harness, the mod, `ItemQuality`, `QuestSystem`, `QualityCooking`, `MoodleFramework`, `BeyondTen` and `TKX_EatProbe`, the probe last in `Mods=` | none | that each co-booted mod's marker resolves on both sides and that one eat applies once with QualityCooking's wrap, the mod's and the probe's installed, the last wrap in `Mods=` outermost (runs `x132b-20261005-071013`, `x132b-20261005-071959`) | [#2837/M/n=2, #2838/M/n=3, #2094/M/n=2, #2095/M/n=3] |
| `x13-coboot-control`, the co-boot's control | the harness, the mod, `BeyondTen` and the probe | none | the same eat without QualityCooking and its three requirements, the counts and calories the co-boot's are read against | [#2838/M/n=3, #2095/M/n=3] |
| `x13-residual`, the residual-arms profile | the harness, the mod and `TKX_CalcStats` | the day length at 1 and `[sandbox.NR] Mode = 1`; the driver boots `nr-overlay` for its control | the trait push arm, the asleep arm under the harness's partial hold and the running arm, which only walked (run `x132r-20261005-072441`) | [#2839/M/n=6, #2840/M/n=2, #2841/M/n=2, #2081/C/open, #2082/C/open] |
| `x14-strength`, the strength-gate profile | the harness, the mod and the probe mods `TKX_XpEvents` and `TKX_XpBurst` | `[sandbox.NR] Mode = 1`, the fixture's own day length, the vanilla `Nutrition` option left on | that a server debug level write holds, that the server-side experience events fire and that a checker-free burst drew no kick on the admin connection (run `x141s-20261005-105131`) | [#2867/M/n=1, #2871/M/n=1, #2873/M/n=1] |
| `x14-activity`, the activity-gate profile | the harness, the mod and the probe mods `TKX_MetWatch` and `TKX_XpEvents` | `[sandbox.NR] Mode = 1`, the fixture's own day length, the vanilla `Nutrition` option left on | what the server can read of a connected player's activity: the metabolic rate classifies, the run and sprint flags and the action stack do not arrive, and a rep and a hit fire their events (run `x141a-20261005-111005`) | [#2875/M/n=1, #2877/M/n=1, #2878/M/n=1, #2879/M/n=1, #2880/M/n=1] |
| `x14-body`, the body-acceptance profile | the harness, the mod and `TKX_MetWatch` | `Nutrition = false`, the day length at 1 and `[sandbox.NR] Mode = 1`, `LegacyMirror = true` | the body model over nine accelerated fasting closes, the weight slot held on both sides, the re-assertion and the cost; its first run (`x141b-20261005-122603`) ran with the vanilla option on, a profile defect since corrected, so the flags and the stores it read were vanilla's | [#2881/M/n=1, #2882/M/n=1, #2883/M/n=1, #2884/M/n=1, #2885/M/n=1, #2886/M/n=1] |
| `x14-clamp`, the clamp-acceptance profile | the harness, the mod and `TKX_XpEvents` | `Nutrition = false`, the day length at 1 and `[sandbox.NR] Mode = 1` | the Strength clamp against a vanilla level-up and an admin write, the rise and fall pacing, the carry delta, the coefficients and the rep counter (run `x141c-20261005-132133`) | [#2891/M/n=1, #2893/M/n=1, #2894/M/n=1, #2896/M/n=1, #2897/M/n=1, #2898/M/n=1, #2900/M/n=1] |
| `x18-moodleframework`, the framework-gate profile | the harness, MoodleFramework by its workshop id and the probe mod `TKX_MF` | none | whether the framework loads whole, runs its configuration file and renders a registered moodle at 0.95 beside a neutral 0.5 control and a widget of the mod's own, counted as render calls (run `x181-20261006-152607`) | [#3188/M/n=1, #3189/M/n=1, #3190/M/n=1, #3191/M/n=1, #3192/M/n=1, #3193/M/n=1, #3194/M/n=1] |
| `x18-translate`, the translation-override profile | the harness and the probe mod `TKX_TranslateOverride` | none | whether a mod's JSON displaces a vanilla item name and a vanilla interface key on each side, beside a new interface key that must hit in the same run (run `x182-20261006-152945`) | [#3200/M/n=1, #3201/M/n=1, #3202/M/n=1, #3203/M/n=1, #3204/M/n=1] |
| `x18-interface`, the interface-acceptance profile | the harness, the mod and `TKX_DeclaredFood` | `Nutrition = false`, the day length at 1, `[sandbox.NR] VisibilityMode = 1`, sleep off | the interface build's load, its panel, tooltip probe, tab and own moodle column, a forced vitamin C deficiency and the layout write at the quit (run `x183-20261006-163238`) | [#3212/M/n=1, #3214/M/n=1, #3215/M/n=2, #3216/M/n=1, #3217/M/n=2, #3218/M/n=1, #3219/M/n=1, #3220/M/n=1, #3221/M/n=2, #3222/M/n=1, #3223/M/n=2] |
| `x18-interface-mf`, the same acceptance beside the framework | the same mods and MoodleFramework by its workshop id | the same | the same arms on the framework route, where the Nutritionist gate flipped and the deficiency moodle reached its bad side (run `x183m-20261006-163808`) | [#3226/M/n=1, #3227/M/n=1, #3228/M/n=1, #3229/M/n=1, #3230/M/n=2, #3231/M/n=1] |
| the vanilla-off profile, planned and written only if the design switches vanilla nutrition off | the harness and the mod | the nutrition option off, set in the block and never at runtime | the mod's own arms over game days with vanilla's frozen, since the option freezes all three of the update's arms, beside the scenario profile's baseline | [#1127/C/C-only, #1277/M/n=1] |
| the stack profile, planned | the harness, the mod and each resident neighbour, every one by its engine-resolved id | none | that the mod's gates still pass beside the mods a live server runs | [#1558, #1617/C/snapshot] |

The acceptance profile's row now has a measurement: under it the mod loaded in both Lua states and its takeover handler registered at the server-started event, the version global answering on both sides and the server log carrying the registration line and a self-report naming the takeover mode [#2746/M/n=1].
In the same session the server's hunger and thirst advanced under that handler at the vanilla rates, thirst by 1.44501e-3 over 180.62 game-seconds against a predicted 1.44495e-3, while the handler's own call count rose from 161 to 281 [#2747/M/n=1].

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
| the vanilla-off pair | the baseline pair on the vanilla-off profile, each arm read against its own baseline | that all three arms still freeze with the mod loaded, as they froze with the harness alone, if the design switches it off | [#1277/M/n=1, #1136/C/C-only] |
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
The health-from-food timer keeps a starving subject alive but holds FOOD_EATEN at level 4, which refuses every eat [#2889/M/n=1, #0077]; world age 0 is 07:00 on the default fixture [#2890/M/n=1].
The evaluator fails a run outright on a dead sample [#1786], and neither that verdict nor the thirst sample column has yet run on a live session [#0171/C/snapshot].
A scenario that wants the thirst clock itself as its reading drops the pin and reads the death as its result.

The dose schedule is the last input, because the calorie ceiling rather than the rate constant bounds a fed character [#0165/M/one-fixture].
A schedule that doses past the ceiling loses the excess to the clamp, so a scenario reads the store it got rather than the dose it asked for ([#0022/M/n=2], [nutrition-core.md#clamps](../facts/nutrition-core.md#clamps)).
The first day of a fed run is a ramp from an empty store, so a per-day rate read off that day is not the steady rate [#0162/M/one-fixture].
At first sight the server's record split the admin's 80 kg exactly by the band-anchored table [#2881/M/n=1].
The mod's drink wrapper already lands a drink's water in the pool before any thirst view exists: 0.11304 litres drunk through the game's drink action counted 58 sips and 57 landings and moved 113.036 g through the stomach into `pool.water`, half of it within about 25 s [#2944/M/n=1].
A scenario that hands the player water has to reckon with `autoDrink`: a 0.9-litre canteen given by RCON reached its drink holding 0.11304 litres, drunk down by `autoDrink` before it, first at the THIRST drained over the A windows and then at the 0.2 write, with the flag back on after it had been written off [#2945/M/n=1, #2941/M/n=1].
The drink wrapper lands a beer's ethanol the same way: a 0.3-litre can drunk through the game's drink action counted 34 sips and 33 landings and put 7.937 g in `pool.ethanol` with 3.913 g still buffered, 11.850 g in all [#2958/M/n=1].
A pill passes the mod by: across a vitamin pill on each boot the eat and drink wrappers' counters held, the last intake did not change and the caffeine pool held 0 [#2953/M/n=1].
A scenario that holds sleep has to reckon with the fast-forward: under the takeover handler a held sleep on a server that allows and needs sleep brought FATIGUE from 0.6009 at world age 7.725 h to 0.0022 at 30.084 h, 42.2 s of server wall time into the hold, and HUNGER read 1 and THIRST 0.5439 after it [#2957/M/n=1, #2956/M/n=1].
The mod's pooled water did not move while `autoDrink` drank 0.9 litres or while the world-source drink took THIRST from 0.4099 to 0.0012, because no drink wrapper sees either route [#2940/M/n=1, #2942/M/n=1].
Over nine accelerated fasting days each day close moved fat and lean by exactly the partition law, 80.00 to 75.67 kg for an idle female [#2882/M/n=1].
The weight write re-asserts within the first read after an admin write of 120 [#2885/M/n=1].
With the legacy mirror on the calorie store tracks the trailing-24 h balance map [#2886/M/n=1].
A replete character's coefficients read exactly 1 at first sight [#2891/M/n=1].
A day's training reaches TAC one close late [#2892/M/n=1].
The carry delta is re-asserted against another writer within one slow minute [#2893/M/n=1].
A vanilla level-up across the ceiling lasts less than one slow minute: the clamp writes the level back and its remap removes the band trait vanilla's listener is inferred to have added (no trait read showed STOUT; the band change is read off the clamp's push counter), before the client sees it [#2894/M/n=1].
An admin debug write is re-asserted the next minute [#2896/M/n=1].
The rise waits six game hours of the ceiling standing above the shown level, counted from when it began, not from when the XP-implied level returned [#2897/M/n=1].
With `Nutrition = false` in the server's sandbox file the mod's boot precondition check is silent [#2909/M/n=1].
The mod's first-sight mirror carries the body [#2910/M/n=1].
The mod's blend follows the hours since the last day close [#2913/M/n=1].
The harness's `globalmoddata.setpath` record edit sets a live mod record in place [#2915/M/n=1].
The harness's `zombie.near` spawns none on the default fixture [#2916/M/n=1].
An eat of a client-only item raises server-side and blocks the queue behind it, so a run must `inventory.add` on the server first [#2917/M/n=1].
A lean-driven fall lands within one slow minute of the day close that drops the ceiling, with its band trait pushed [#2898/M/n=1].
Under the harness's sleep hold an rmod of 0.848 slowed endurance regeneration to 0.904 of the rmod-1 rate [#2899/M/n=1].
The whole Plan 4 build ran its first boot without a mod error, its nutrients adapter counting 1689 minutes and 0 errors [#2975/M/n=1].
At first sight the record's fluids hold their creation values less the basal loss, the sodium balance equal to the kernel's to the last digit, with the epoch at 0, every record replete and the sleep state frozen on a server that disables sleep [#2961/M/n=1].
The server's THIRST is the record's view, holding each stamp for a slow minute, and the client's copy reads within 0.00085 of it; the view rises with the basal loss at about the rate vanilla's drain did [#2962/M/n=1].
A scenario that holds a subject at rest gets the kernel's numbers for that subject, not the 80 kg male hand values: ten game hours took the fixture's female subject to a 1.4369 % deficit and a target of 0.24594, the sodium balance exact and the water short only by the cold-diuresis term [#2963/M/n=1].
The performance scalars follow the deficit: `iu` rises from 1 % and the carry delta steps to 0.97 at a 2.2 % deficit and 0.94 at 9 % [#2964/M/n=1].
The auto-drink bracket lands what `autoDrink` drinks, the 0.9 L canteen in full within a slow minute or two, no wrapper sip counted, so a scenario that leaves a filled container in the inventory with THIRST above 0.1 gets that water in the pool [#2965/M/n=1].
A litre drunk through the drink action lands in full, the view falling at once and the deficit as the water absorbs, and the surplus after it clears at the stated 320 g an hour [#2966/M/n=1].
A cola's sodium lands to the milligram through the stomach into the sodium balance [#2967/M/n=1].
Record edits through `globalmoddata.setpath` drive the plasma-sodium index and the hypotonic cap as the kernel states them; the plan's 122 mmol/L for +8 L is an 80 kg male's and this subject read 113.03 [#2968/M/n=1].
The kill dial is live: off, it holds the target at 0.83 at a 9 % deficit, and on, the target reads 1.0 [#2969/M/n=1].
World water lands at the action's own scale, within twice the window's highest THIRST, the action's planned litres unread, and the view falls [#2970/M/n=1].
The client's mirror copy answers a fresh request and is never read without one [#2974/M/n=1].
The second boot of the Plan 4 build, with sleep allowed and the onset dial at its maximum, ran without a mod error through four day closes [#2976/M/n=1].
A scenario that wants a deficiency inside a session dials a record that takes the dial: vitamin C does not, staying at grade 1 at every read across 95.6 game hours at the maximum dial [#2977/M/n=1].
The records that take it, and vitamin K, crossed their grades inside the read brackets the mod's kernel replay puts them in, the replay's grades equal to the read ones at every interval [#2978/M/n=1].
The epoch counts one per grade or excess-output change and nothing else in the session [#2979/M/n=1].
An eaten vitamin lands on its record through the zero-order-hold step, a lettuce's vitamin C to the decimal the step gives [#2980/M/n=1].
A loaf's phytate in the stomach buffer cut the iron absorbed per milligram emptied by about half a per cent (0.179 against 0.18), matching the kernel's per-minute value and not the meal-level one that would give a quarter [#2981/M/n=1].
A coffee's caffeine lands whole and the body load halves every five game hours for a fast metaboliser, the drain coefficient carrying its effect [#2982/M/n=1].
A single beer drunk through the drink action read 0 blood alcohol at every read, at most 0.0663 g of ethanol a game minute leaving the stomach, while the day's alcohol total took it at once [#2983/M/n=1].
Glycogen fell on the minutes read above 3 MET, a squat set reaching 4.0 MET on the server, and fell at rest at the fixture's indoor air under a cold multiplier above 1, so the store never refilled [#2984/M/n=1].
With sleep allowed the sleep state runs from the record's creation and the impairment unit is the kernel's sum at every read [#2985/M/n=1].
A scenario that holds sleep through the harness gets the asleep minutes booked into the debt windows but never a reset of hours awake: `sleptH` read at most 0.3195 at the 35 reads while `awakeH` rose from 22.87 to 32.62 [#2986/M/n=1].
Record edits to the starvation count and the day's intake drive the refeeding risk at the next close, and the fasting closes of a held sleep keep it [#2987/M/n=1].
The excess dial zeroes the output while the excess sum keeps integrating, and the output returns at the first read after the dial comes back [#2988/M/n=1].
The bench's first call on the second boot ran above Plan 3's range and the two after it within 5 per cent of its top [#2989/M/n=1].
The client's mirror copy carries the record's grades, epoch and acute scalars at a fresh request [#2991/M/n=1].
The Plan 5 gate-1 boot of the mod at `d2301d6` ran its arms without a mod error [#3034/M/n=1].
Both gate-2 boots of the mod at `9cc8d8d`, one with sleep allowed and needed and one with neither, ran their arms without a mod error [#3051/M/n=1].
The mod's weight adapter undoes a weight written beside it: after each of four band-edge weights written on the server, the next read about a second later gave 80 kg and no band trait, the adapter counting four band repairs and four pushes [#3052/M/n=1].
On a server with sleep neither allowed nor needed the FATIGUE the mod's handler writes sits at the reset value, about 1e-4 on both sides [#3053/M/n=1].
On that boot, with `Nutrition = false` and no meal, the HUNGER the handler writes rose from 0.02291393093764782 at world age 3.1852712631225586 h to 1 by 9.428855895996094 h, the HUNGRY moodle reaching level 4 and the hunger damage tag then firing every tick [#3035/M/n=1]; at that level the regeneration tier adds nothing [#2353/C/C-only], so a scenario that leaves its subject unfed reads no regeneration from then on.
The fix wave's boot, the third of the Plan 4 build, ran without a mod error through three day closes [#2993/M/n=1].
A phytate-rich meal now cuts iron by the meal in the stomach: with a loaf's 400 mg of phytate buffered the pool took about 0.047 mg of iron per mg emptied, rising toward 0.18 as the loaf emptied, across the 113 intervals before the sleep hold [#2994/M/n=1]; the record took that at the buffer-calcium factor over those intervals, then read about 0.0012 under it from the hold's F_p4 interval through the bread's tail and the steak, a gap the run did not explain [#2995/M/n=1]; and a steak on an empty buffer took 0.18 across 33 intervals [#2996/M/n=1].
A scenario that doses caffeine or alcohol gets it through the gut lane, never the stomach: a coffee's caffeine peaked at 82.92 mg about two game hours after the drink [#2997/M/n=1], and a single beer read a peak of 0.00568 %, 9 % under the whole-dose-at-once prediction, which it falsifies as a point; the replay from the landed state matches it, read as the sips spreading the landing [#2998/M/n=1].
At rest indoors the glycogen store fell from the first-sight store of 460.78 on a day without carbohydrate, and after a record edit to 150 it held at MET 3.0 and rose from the first read at MET 2.5, its changes matching a replay with no shivering draw [#2999/M/n=1]; a squat set read mostly 3.0 MET on the server, where the store neither draws nor refills [#3000/M/n=1].
A scenario that holds sleep through the harness now gets the hours-awake reset: one sleep bout spanned the whole hold across the missed asleep reads, `awakeH` reading 0 at every read after the first [#3001/M/n=1], with the sleep pressure falling and the debt and impairment readings trivial at a hold begun under 16 hours awake [#3002/M/n=1].
The bench on the third boot read within Plan 3's range and 2.1 per cent above its top after a discarded warm-up call [#3003/M/n=1].
The first live boot of the whole Plan 5 build, the effects adapter and the fast handler's new writes included, ran nineteen minutes of arms without a mod error [#3070/M/n=1].
The coefficient set is on the record from the first read after a join, and its epoch counts the rebuilds through the session [#3071/M/n=1].
The server's FATIGUE is the writer's `S + circ + fOff` from the record at every read bracketed by record reads, exactly, and the client's copy is a value the server held about a push earlier [#3072/M/n=1, #3073/M/n=1].
An empty stomach no longer reaches the level-4 hunger drain: the HUNGER view held at 0.69 with the hungry moodle at level 3 and no `HUNGRY` damage tag in any probe window, while the thirst cap was not approached [#3074/M/n=1].
The Tired thresholds fell within about a tenth of a game hour of the kernel's replay of the live record, roughly twelve, fourteen and sixteen and a half hours after the record's birth near 10:05 [#3075/M/n=1].
A scenario that holds sleep through the harness gets the recovery constant only on the minutes the record counts asleep, about 85 per cent of them, so S falls more slowly than a wholly asleep step [#3076/M/n=1].
A coffee moves the fatigue offset by the kernel's caffeine term at every slow minute [#3077/M/n=1].
The endurance fold switched on live scales a squat set's drop within the run's coarse band, while two resting windows do not isolate its regeneration arm [#3078/M/n=1].
A clinical B-vitamin store drives STRESS up at the net rate and holds it on the floor, and the floor's removal hands the stat back to the decay [#3080/M/n=1].
The set the record carries is the composer's on that record at every whole read [#3081/M/n=1].
The first boot's PANIC floor, written as a rise, did not lift PANIC: it stayed at one update's rise whatever the target [#3082/M/n=1].
The UNHAPPINESS floor rises at its rate, holds and is released once when the target falls [#3083/M/n=1].
An excess rung drives FOOD_SICKNESS to its floor at the net rate with POISON at 0, and the excess dial off hands it to vanilla's decay [#3084/M/n=1].
The Severity dial reaches the set at the next rebuild [#3085/M/n=1].
INTOXICATION follows the gut lane's target rather than the drink writer's total, except for one update after each sip [#3086/M/n=1].
The aim multiplier reaches the client's mirror and the swing stub and is applied nowhere [#3088/M/n=1].
On this boot the fast kernel step's two kept bench runs sat inside 10 per cent of the Plan 4 reading [#3089/M/n=1]; with the second boot's runs the verdict is unresolved (T14-1) [#3112/M/n=1], and the handler's Plan 5 writes are outside the bench; the effects push is deduplicated to a fraction of its marks [#3090/M/n=1].
The second live boot of the Plan 5 build, with the PANIC floor a hold, ran 1341.8 s (22.4 minutes) of arms without a mod error [#3091/M/n=1], and the set on the record equalled the composer's replay at every whole read, the drains and their codes included [#3092/M/n=1].
Night vision follows its day counter: with the retinol average edited over the requirement the counter ran one day per game day and granted the trait at 14, the client seeing it inside the round trip of the record read before the grant [#3093/M/n=1].
An outside removal of the granted trait was undone by the next read [#3094/M/n=1], vitamin A at grade 2 withdrew it on both sides [#3095/M/n=1], a NIGHT_VISION the mod had not added stayed through about twelve slow minutes [#3096/M/n=1], and with no preformed retinol the counter only fell [#3097/M/n=1].
Clinical vitamin A put Short Sighted on both sides about a quarter of a second after the edit, collapsing the pistol's sight range from 6 to 2, and Severity 0.5 or a climb to grade 3 took it off again [#3098/M/n=1].
Sleep debt raised the cold multiplier to 2.5 at the next rebuild [#3099/M/n=1].
Iron's clinical grade stamped the temperature target 0.2 under the set point, but the core sat under the target at rest and through a 20-game-minute squat set, so the steady offset read is the regulator's own and the target's held equilibrium stays open [#3100/M/n=1].
The PANIC floor now holds its target from the first sample that left 0, the client copying it within about a push [#3101/M/n=1], and a lower target lets PANIC fall at vanilla's decay and then holds it [#3102/M/n=1].
With a 7 per cent water deficit the THIRST view stopped at the 0.83 cap on both sides and the thirst damage never fired [#3103/M/n=1].
Iron's lethal rung drained health at its stated rate with the regeneration constants at 0 and FOOD_SICKNESS held at 85 with POISON at 0 [#3104/M/n=1], and turning the kill dial off stopped the drain by the first record read, 7.8 s after the dial's reply [#3105/M/n=1]; thirty days of clinical vitamin C drained at the scurvy rate and the code reached the client's mirror [#3106/M/n=1].
The day close grades protein-energy from the starvation count, not from an edited BMI [#3107/M/n=1].
Protein-energy grade 3 with vitamin C at grade 3 slowed a scratch's countdown by 0.6785 against the predicted 0.68 [#3108/M/n=1].
Clinical vitamin C slowed a bleed by 0.8002 against 1/1.25 [#3109/M/n=1] and gave one bruise in about two game days against 1.03 expected [#3110/M/n=1].
Protein-energy grade 4 sped an infection by 2.3055 against 2.3, the client's copy following the folded level [#3111/M/n=1].
On this boot the bench's first kept run read above the 10 per cent band over Plan 4's reading and the second inside it [#3112/M/n=1].
The first boot of the item-pass build loaded the generated nutrient table, the inference templates and the item-pass script file on both sides without a mod error, the intake landing every eat and sip of the session with no failure [#3140/M/n=1], and a second boot on the close fix wave's regenerated files loaded them the same way [#3179/M/n=2].
Its boot reached ready about as fast as the Plan 5 build's second boot, and its tick rate sat about half a per cent under that boot's [#3142/M/n=1]; the second boot's tick rate sat at the same level, its client a few seconds slower to ready [#3181/M/n=2].
An eaten food on the table lands the table's vector with the four macros the live item delivered: a whole apple matched the table entry on every non-macro key, its macros those of the profile's restated test apple [#3145/M/n=1], and a whole loaf landed the generated table's 40.02 mg of phytate [#3146/M/n=1]; the second boot landed both vectors again key for key [#3182/M/n=2, #3183/M/n=2].
A scenario that eats a food a test mod also restates reads the test mod's macros wherever its script path sorts after the pass's, as the acceptance profile's apple did [#3144/M/n=2].
A food outside the table with no FoodType lands the `_default` template times its calories [#3147/M/n=1], and a food declaring `NR_Nutrients` lands its declared keys ahead of the table, its B12 landing at half the declared 0.5 [#3148/M/n=1]; the second boot repeated both, the inferred choline following that build's new `_default` density [#3184/M/n=2, #3185/M/n=2].
A coffee lands the fluid table's per-litre vector times the litres drunk, its caffeine on the gut lane, while the cola arm took no reading [#3149/M/n=1], and the second boot read the same [#3186/M/n=2].
The item-pass build's 90 121-byte script file loaded the same on both sides under the admin bypass, so that boot says the copies agreed and nothing about the checksum gate itself [#3140/M/n=1, #3152/M/n=1], as the close-wave build's 90 124-byte file did on the second boot [#3179/M/n=2, #3187/M/n=2].
The pass puts no mod key on a vanilla food [#3150/M/n=2], leaves a reasoned record's script alone and re-bases a mapped row whatever part file it sits in [#3151/M/n=2], and under the fixture's admin role the boot stayed connected with no checksum line, a reading under the bypass rather than of the gate [#3152/M/n=1, #3187/M/n=2].
The first live boot of the interface build loaded clean, every surface's error counter at 0, the view at level 1 under the server's option and the moodles on their own column [#3212/M/n=1], and the mirror carried the new pool-fraction and excess keys beside each grade [#3213/M/n=1].
The panel opened on its toggle, requested the mirror, drew while open and stopped drawing once closed [#3214/M/n=1]; the tab read added once at first sight, its render count 0 at every check [#3221/M/n=2].
On that boot a client-local Nutritionist trait did not flip the view to level 3: the requested mirror arrived and the view rebuilt, but its trait read came back false, and the run does not say whether the client's list had already lost the trait [#3219/M/n=1].
The tooltip probe resolved the intake's own source per item, `table` for the apple and `declared` for the declared bar, one line each at level 1, while the band's on-screen draw stays unmeasured because the harness cannot hover [#3220/M/n=1].
A clinical vitamin C written into the record reached the own moodle column within one effects push, the deficiency class reading 3 and the column drawing [#3222/M/n=1], at a fixed inset clear of the vanilla moodle band [#3223/M/n=2].
The boot ticked at the item-pass build's server rate [#3224/M/n=1], and the server's log carried no interface line from the mod [#3225/M/n=2].
The second boot, with MoodleFramework installed, loaded as clean on the framework route [#3226/M/n=1], and there the same client-local trait flipped the view to level 3 within the first read after the request [#3227/M/n=1], so the gate's client-local route read differently on the two boots, and whether the client's list lost the trait before the mirror's arrival or the view's read missed it is unseparated [#3241/M/n=1].
At level 3 the tooltip probe listed 24 lines for the apple and 10 for the declared bar [#3228/M/n=1], the panel and the tab repeated the first boot's counts [#3231/M/n=1], and the forced clinical vitamin C put the framework's deficiency moodle on its bad side at level 3 on the UI manager, the first bad-side reading of the framework [#3229/M/n=1].
The third boot, on the close-wave build whose tab, tooltip, panel, options and view files had changed, loaded clean again on the own route [#3249/M/n=2], the mirror's keys and the panel's toggle, request and draw-while-open repeating [#3250/M/n=2, #3251/M/n=2] and the tab again added once and never drawn [#3221/M/n=2], and the client's self-report now named its `own` route [#3258/M/n=1].
On that boot the same client-local Nutritionist trait flipped the own route's view to level 3 at the first read [#3254/M/n=2], so the tooltip probe listed 24 and 10 lines [#3255/M/n=2], and the forced clinical vitamin C reached the column again [#3256/M/n=2] at the same inset [#3223/M/n=2]; the boot ticked at the same server rate [#3257/M/n=2] and the server's log again carried no interface line from the mod [#3225/M/n=2].
That boot ticked at the same server rate [#3232/M/n=1], and its server log again held no interface line from the mod [#3233/M/n=1].
The first boot of the sync build, whose profile sets no visibility key, loaded clean with the store and reconciliation adapters [#3272/M/n=1], both sides reading the Bands default [#3260/M/n=1]; the admin's record was created at the store's version 2 with no migration [#3261/M/n=1], and with the admin idle the reconciliation landed nothing through the boot [#3262/M/n=1].
A Nutritionist trait the server added and pushed reached the client's list at the first read and turned the view to level 3 at the next mirror [#3263/M/n=1], and a server removal with the trait push took it out again and the view back to level 2 [#3264/M/n=1].
At the Bands level the panel fit its rows, so its wheel had nothing to scroll and declined both calls [#3267/M/n=1], while the character-info tab's wheel scrolled its rows by one step and back [#3268/M/n=1]; the tab's render, called outside the UI frame, ran once without an error [#3269/M/n=1], and the window's heights read the same after it as before [#3270/M/n=1].
The boot reached ready and ticked at the interface build's server rate [#3271/M/n=1].
The persistence run's four boots each started their server in 14.9 to 16.1 s and reached a ready fixture client [#3286/M/n=1], and with the admin idle the reconciliation landed nothing across a reconnect, a reload, a respawn, a hard kill and a fresh creation [#3283/M/n=1].
A freshly restored client cache already held a `layout.ini` before its first start, which the driver had predicted absent, so its presence never tells a fresh restore from a warm one [#3285/M/n=1].
The two-client session attached the debug client and then the release client, each reaching ready [#3298/M/n=1], and the release client read its debug flags false and a Lua error count of 0 [#3297/M/n=1]; with both clients attached the server ticked at the one-client rate [#3299/M/n=1].
On the release client a Lua-triggered key press toggled the panel, which showed that player's own deficiency class while the other client's panel stayed shut [#3296/M/n=1].
A server write raising one player's vanilla calorie store with no eat was reconciled at the next slow minute as macros only, with no nutrient pool moved and the other player uncounted [#3293/M/n=1].
The driver predicted the landed amount from a read of the store taken before its write, and the landing read 512.6971752597278 kcal against the predicted 500 plus or minus 10, so the prediction was falsified on the amount, the cause being inference [#3294/M/n=1], and the landing logs nothing at the default log level [#3295/M/n=1].
The interface build's mirror carries three scalars per key of the record order, `nut_<key>_g`, `nut_<key>_p` and `nut_<key>_x`, and the order holds 27 keys, so the two families the build added are 54 scalars; the effects push that sends the mirror is held to one per player per 60 000 ms of server wall clock, and a display of it is as old as the last push, up to the push gap plus one slow minute's flush, because the bus reads the dirty flag on the slow minute [#3238/C/inference].
The build's tooltip entry lookup reads nine members of the hovered item on each render before it consults its cache, a cost in getter calls and never a measured frame time [#3239/C/inference].
The build's requirement table keys a record by the vector's own key through an alias (`retinol` for the record `vitA`) and enters a scaled record at its cited daily floor or at its per-kilogram rate times a 70 kg reference, so vitamin A, thiamine, niacin, vitamin B6 and vitamin K rank rich or low in the tooltip band; the interface build's table had excluded them, a defect fixed in the sync build [#3259/C/inference].

<a id="owned-experiments"></a>
### The experiments this mod owns

Four named experiments are this page's to run, because the design cannot be finished without them.
Two settle the wall map's unknown verdicts — whether a mod may override a vanilla translation key, settled by run `x182-20261006-152945`, and whether the drink path can be hooked, settled by run `x132d-20261005-060046` [#1164/M/n=1, #1133/M/n=1].
The third measures the trait route the wall map reads from the code: whether a server push after a trait write reaches the client's trait list within its cadence, and whether a trait the mod registers behaves the same ([#2099/M/n=6], [wall-map.md#g4](../reference/wall-map.md#g4)).
The fourth tested the moodle framework, the widget route the wall map leaves a moodle beside a widget of the mod's own, and all three of its legs were measured in run `x181-20261006-152607` ([#1295/M/n=1], [wall-map.md#d4](../reference/wall-map.md#d4)).
The other named experiments go to the build-out or stand alone, as [experiments.md § Owners and the cost roll-up](../reference/experiments.md) assigns them, and the build-out's decide how the mod is built rather than whether a part of it can be.
Each spec is [`experiments.md`](../reference/experiments.md) and each open row the four carry is indexed on [`open-questions.md`](open-questions.md); this page restates neither.

| experiment | what it settles | what makes the reading discriminate | what it costs | tags |
|---|---|---|---|---|
| [X4](../platform/mp-model.md#sync-globals) | whether a server push after a trait write reaches the client's trait list, whether a client read sees the new trait within the push cadence, and whether a trait the mod registers behaves the same | the server's trait list is made non-empty first, because a trait crossing cannot be read on an empty list, and Plan 1's run (x131t) and Plan 2's (x132r) both read a non-empty list on the server and on the client, and the control is the same write with no push, graded on arrival time: the experience packet is predicted to carry the trait within a second without a push, so a read before the push does not discriminate and the push shows only by arriving sooner | a single session with a new trait mod that stamps each write and each arrival and a harness addition that pushes the trait list, sharing its boot with the weight-lot ladder and running its band edges last | [#2099/M/n=6, #2759/M/n=3, #2839/M/n=6, #2595/C/C-only, #2608/C/C-only, #1291/M/n=1] |
| [X5](open-questions.md#x5) | whether a mod translation file displaces a vanilla key or the merge keeps vanilla's — settled in run `x182-20261006-152945`: the mod's value won on the client and the server kept vanilla's | a new interface key the mod ships must hit in the same run, and the server arm is a control because a dedicated server resolves no mod item's display name | a single short session with a new translation mod | [#1276/M/n=1, #1250/M/one-side, #0848/M/n=1, #3203/M/n=1] |
| [X13](../reference/wall-map.md#b7) | whether a server-side wrapper of the drink action fires, and on which side — settled in run `x132d-20261005-060046`: on the server only | the shipped drink command moves the stores in the same session, so a silent wrapper reads as a silent Lua route rather than a silent fluid path | a harness addition that queues the real drink action, landed in its own commit, then a single session | [#1279/M/n=1, #1255/C/C-only] |
| [X29](open-questions.md#x29) | whether the moodle framework loads whole, whether its configuration file runs, and whether a moodle registered through it renders above its lowest level — settled in run `x181-20261006-152607`: it loaded whole, the file ran and the moodle rendered | each leg has its own reading, the render leg drives a registered moodle past a threshold beside a value that must leave it undrawn, and a moodle that never draws on the client would close the framework route and leave the mod a widget of its own | a single short session with a probe mod, the framework's interface being read from its live tree | [#1295/M/n=1, #0884/M/n=1, #2742/M/n=1, #3192/M/n=1] |

The minutes, sessions and write-up ceiling behind the cost column are [experiments.md § Owners and the cost roll-up](../reference/experiments.md), and the whole named programme is a ceiling rather than a commitment [#1973].
The trait experiment decides what a client may do with a band: the trait list reaches the player's own client on the player-fields packet's trait block and on the timed experience packet, read from the code and never exercised, so until [the live measurement](../platform/mp-model.md#sync-globals) lands a client-side display or derivation that reads a band rests on an unmeasured route, which is why anything keyed on a band is evaluated on the server or its trait list pushed after each write ([#2595/C/C-only], [#2718/C/C-only], [#2727/C/inference], [mp-sync.md#authority](mp-sync.md#authority)).
The translation experiment settled that a mod's value for a vanilla key wins on the client while the dedicated server keeps vanilla's strings, so a rename is a display change on the client only ([#1164/M/n=1], [#3203/M/n=1]).
The drink experiment settled that an intake correction can reach fluid drinks, though the fluid path has no eat hook, through a server-side wrapper of the drink action ([#1133/M/n=1], [eat-and-cook-hooks.md#hook-options](eat-and-cook-hooks.md#hook-options)).
The framework experiment settled that both routes draw: a registered moodle left its lowest level on the client and a widget of the mod's own drew beside it ([#2742/M/n=1], [ui-and-moodles.md#moodle-route](ui-and-moodles.md#moodle-route)); the framework experiment ran first and the translation experiment second.
Each runs under the standing contract — a profile in the acceptance profile's shape, a driver in the house shape with client-first paired reads, and gates that never measure [#2050].
The drink experiment's harness addition landed before its session in a commit of its own, with the command table regenerated and the session as its smoke test ([#1279/M/n=1], [harness.md#procedure](../platform/harness.md#procedure)).
Each of the four has now run, so its area page states it as a measured wall, and this page carries the same four under [Walls and bounds](#walls).

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
Before X4's run no run had held a non-empty trait list on either side, so the two sides' agreement in every earlier run that could have shown a trait crossing answered nothing [#2595/C/C-only]; X4's no-push arm then timed a server-written trait onto the client's list within about half a second [#2759/M/n=3].
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
A vanilla nested option is out of the sandbox block's reach, and the answer there is again a fresh fixture [#2811].
The mod's own options are in its reach through a nested `[sandbox.<Prefix>]` table, which booted the mod in each of its two modes [#2807/M/n=1].

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
- Persistence is measured once: a session can restart a world on its own run directory, and `modData` in the player and global scopes survived a clean save and reload while a boot on the restored fixture missed it ([#1294/M/n=1], [server-lifecycle.md#global-moddata](../platform/server-lifecycle.md#global-moddata)).
- The trait route to the owning client is measured on non-empty trait lists: a server write reaches the client's list within about half a second with no push [#2759/M/n=3] and within tens of milliseconds with the player-fields trait-block push sent in the same tick [#2839/M/n=6], while the two packets that carry it are read from the code ([#2595/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4), [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)).
- The translation override is measured once: a mod's value won for two vanilla keys on the client and the dedicated server kept vanilla's strings and missed the mod's new key, in one session with language EN only ([#1164/M/n=1, #1276/M/n=1, #3203/M/n=1, #3204/M/n=1], [open-questions.md#x5](open-questions.md#x5)).
- A container drink from the drink action reaches a mod through a server-side wrapper of its `updateEat`, measured in one session: it fires on the server and the client's counters stayed at 0, and it misses a direct `DrinkFluid` call and the world-water route ([#1133/M/n=1, #1279/M/n=1, #1255/C/C-only, #2827/M/n=1, #2690/C/C-only], [wall-map.md#b7](../reference/wall-map.md#b7)).
- The moodle routes are measured once each: a Lua-drawn widget, the framework's or the mod's own, drew on a dedicated-server client, counted as render calls and never seen on screen, and the framework's bad side was read in one acceptance boot ([#1295/M/n=1], [#3229/M/n=1], [wall-map.md#d4](../reference/wall-map.md#d4), [open-questions.md#x29](open-questions.md#x29)).
- Nothing on the bus executes a craft, so a crafted food's nutrition is read from the code and its create hooks stay unmeasured [#1248/C/C-only].
- No bus command synthesises a click or a key press, so a panel of this mod's own keeps its state invisible to the bus until a human clicks [#1498/M/n=1]; the interface acceptance boots therefore toggled the panel through a call, read render counters and layout files, and never exercised a key press, a hover or a wheel ([#3214/M/n=1], [#3220/M/n=1]).
- A sandbox option that is nested, or that the world generator consumed, is out of a profile's reach, and changing one means a fresh fixture ([#2811], [#1811/C/inference]).
- A profile's top-level sandbox keys cannot set the mod's own options, and its nested `[sandbox.<Prefix>]` table can [#2807/M/n=1].
- A tooltip probe on the driven client reads a debug client's tooltip, whose nutrition block can show without the Nutritionist trait, and on any client a packaged food with a readable label shows the block too ([#2645/C/C-only], [#1710]).
- A tooltip probe on the stack profile reads the end of a sentinel-free wrap chain the resident mods build, one of whose links bypasses the chain with its own fork of vanilla's render, so it never reads the mod's wrap alone [#2568/C/snapshot].
- No bit-level claim may rest on an artifact written before the harness commit `291f977` [#1254/C/snapshot].
- The Plan 2 § 6 cost budget is measured and holds, the reading taken on the Plan 1 fast step at efd9e97 before Task 11 replaced the hunger-drain arms with the stomach-fill term (the change removes branches and adds one scalar read, so it bounds the shipped step from above without a re-run): `NutritionRevamp.bench_fast`, one whole fast step run through the takeover entry point over a representative steady-state awake tick, costs 3.06 µs per call (100 000 calls in 306 ms), a per-tick floor rather than a worst case [#2822/M/n=1]; on the same fixture a takeover boot and an overlay boot answer `tick.rate` at 10.01 and 10.10 server ticks per second (ratio 0.990), so the handler holds the tick rate within about 1 % of the seven updaters it replaces [#2823/M/n=1]; the entry gate proceeds and takeover stays the shipped default [#2824/M/n=1] ([artifacts.md](../reference/artifacts.md)).
- The Plan 3 build left the cost where Plan 2 measured it [#2888/M/n=1].
- The Plan 4 build left the cost where Plan 3 left it [#2973/M/n=1].
- Four instruments the body plan's acceptance runs lacked bound what they could read: a live sandbox flip that reaches `SandboxVars` (the mirror's off state [#2887/M/n=1]; since measured, a server assignment into the leaf read live by the mod's per-tick reader [#2969/M/n=1]), a body-record edit through the bus, which writes top-level keys only (the lean-driven rise [#2897/M/n=1]), a command that places a zombie beside the player (the hit count [#2880/M/n=1]) and a lighter or male fixture subject (the weight band's crossing [#2882/M/n=1]); each is named here. The arms those runs left unmeasured: the regeneration coefficient's effect under a full sleep hold (under the partial hold the held sleep regenerated at 0.904 of the rmod-1 rate against 0.848 to 0.860 predicted [#2899/M/n=1]; the awake share of the held updates is a hypothesis the hold's confounds leave open); the lean-driven rise of the Strength ceiling and the fall's pacing past one level [#2897/M/n=1] [#2898/M/n=1]; the melee-hit counting, since the hit event fires for a connected player's melee hits [#2880/M/n=1] but the acceptance run's horde put no zombie within reach; the legacy mirror's off state, since a server-side sandbox set changed the option object and not the `SandboxVars` table a polling mod reads [#2887/M/n=1]; the hunger floor under an energy deficit on a live starving character, because the control that kept the subject alive held a moodle that refused every eat [#2889/M/n=1]; and the weight band's crossing, which the fixture's female subject did not reach in nine closes [#2882/M/n=1]. The Plan 4 acceptance runs lacked five more: a fixture subject that walks above 3 MET for game hours, since the 60 s walk never took the server's activity above the sweat term's floor [#2972/M/n=1/open]; a male subject; a hook for `autoDrink` itself, since only the flag was written and read back [#2941/M/n=1]; a script `OnEat` on the vitamin pill, whose seat the jar reads and no run exercised [#2960/C/C-only/open]; and the heat half of the climate override, whose admin value reached the manager and not the character's air [#2946/M/n=1/open]. The Plan 5 acceptance runs lacked six more: five bench runs per boot read as a median, because the four kept single runs of the fast step's bench span 3.20 to 4.44 microseconds, as wide as the 10 per cent band, and so left its cost verdict unresolved [#3089/M/n=1] [#3112/M/n=1]; a reader of the mood, tired, sick and drunk moodle levels, whose levels the acceptance infers from the registered thresholds [#2369/C/C-only]; an outdoor or wet-and-cold seat that lifts the thermoregulator's catch-a-cold delta over 0.1 for game hours, which the cold fold's reading needs [#3114/M/n=1] [#3129/M/n=1/open]; a heat or exertion source that holds the core above the set point for game hours, which the held temperature target's reading needs [#3047/M/n=1/open]; an in-handler probe of the endurance write, which the running arm of X35 needs [#2082/C/open] [#3079/M/n=1]; and a Lua setter that reaches a client table, because `lua.setpath` is registered on the server only and sets a scalar there, as [the command table](../reference/harness-commands.md) lists it. Three harness quirks bound those readings and are a fix for the next harness change: the trait-name check lower-cases the name while the list key is `nightvision`, so it reads false whatever the list holds [#3094/M/n=1]; a record read reports a false boolean as missing [#3095/M/n=1]; and `TKX_StatWatch` never clears a previous window's damage-tag keys, so an unfired tag can carry a stale count (the paths are on the `do-not-cite.csv` list).

Not covered: a second machine or any continuous-integration host, a Linux dedicated server, a release client, a session with two driven clients, a save-and-reload cycle, and any session a person drives rather than the bus — every reading this plan can take is one Windows machine driving one dedicated server and at most one debug client.

## Open
<a id="open"></a>

- Whether the client's list lost the Nutritionist trait before the mirror's arrival or the view's read missed it is unseparated: the add read true in the client's list on the own-route boot while the view's trait read stayed false, and it flipped the view on the framework-route boot and on a second own-route boot [#3254/M/n=2] — settled by a run that re-reads the trait list at intervals after the add and at the mirror's arrival, and an add that is synced [#3241/M/n=1].
- Whether the tooltip band lands on screen and where its bottom-edge branch puts it is unmeasured, the probe running the band's entry function and the hover draw count reading 0 — settled by a hover synthesiser reading the band's pixels or draw calls [#3244/M/n=2/open].
- Whether a saved `visible=true` panel line restores the panel open is unmeasured — settled by a second boot on a user directory carrying the line [#3245/M/n=1/open].
- Whether the tab's tear-off wrap and its `current`-clearing branch run is unmeasured — settled by a click synthesiser that activates the tab and tears it off before the quit [#3246/M/n=1/open].
- Whether the panel's key press toggles it is unmeasured, the toggle having been a `lua.call` — settled by a key synthesiser [#3247/M/n=1].
- Whether a scrolled panel clips its rows is unmeasured — settled by a wheel synthesiser [#3248/M/n=1/open].
- Which sandbox options survive a restore — settled by a profiled run that sets each nutrition option on a restored world and reads it back; no `X` id ([#1830/C/C-only/open], [harness.md#open](../platform/harness.md#open)).
- Where the cadence ceiling really sits above the known-safe demand — settled by scheduler self-tests that step the demand past it and read the fitted tick rate; no `X` id ([#1815/M/n=1/open], [harness.md#walls](../platform/harness.md#walls)).
- A real run is a harness need before X34's running arm and X35's running pairs can be read, because `player.run` sets the running and path-find running flags and the character still only walks, while the asleep hold re-asserts the server's flag once per tick and about 15 % of stat updates still ran awake under it; X35 also needs a handler writing its sentinel [#2840/M/n=2] (#2081, #2082); -> X34, X35.
- The thirst sample column and the evaluator's dead-subject verdict have never run on a live session — settled by the next pinned three-day run's committed artifact; no `X` id [#0171/C/snapshot].
- That the multiplier getter is scaled rather than the argument passed, that the time multiplier must always be changed through the broadcast admin command, and how a multiplier change re-syncs the client's clock are unverified, and their owner states them with their bounds ([#1869/M/uncommitted/unverified, #1870/M/uncommitted/unverified, #1871/M/uncommitted/unverified], [harness.md#open](../platform/harness.md#open)).
- That a small cross-side calorie gap in the witness spike is the sampling skew of a once-a-second mirror is unverified, and its owner states it with its bound ([#1875/M/uncommitted/unverified], [harness.md#open](../platform/harness.md#open)).
- Decision: at which pacing the mod's timed scenarios run — forced by the cadence ceiling binding the day length and the multiplier together while every baseline sits at the fixture's day length [#1814/M/n=3, #1253/C/one-fixture].
- Decision: whether the mod's load checks are verification rows or scenarios — forced by a verification expectation being a substring that cannot express absence or a numeric comparison [#1828].
- Decision: whether the mod ships a client-side scenario for its display copy — forced by the client runner being wired with nothing to run and by every client read of a live store being a staircase [#1784, #1483].
- Decision: whether any scenario moves a sandbox option off the fixture's value — forced by only the day length having been set by a profile, so a moved option buys a new baseline [#1809/C/C-only, #1253/C/one-fixture].
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
