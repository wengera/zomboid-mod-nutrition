---
name: nutrition-testing-your-mod
description: Planning or grading the nutrition mod's own tests — its profiles (`testing/profiles/mod-under-test.toml`, the engine-resolved `id=`), `[[verify]]` rows, multi-day nutrition scenarios and the hunger and thirst they must manage, `DayLength`, the `Nutrition` sandbox option and the fixture's sandbox values, the owned experiments, a cross-side reading graded against its own skew band rather than equality, and what a green run does not prove.
---
## Read first
- docs/areas/testing-your-mod.md
- docs/platform/harness.md
- docs/reference/harness-commands.md

## Rules quoted
- Never read a green run as evidence that a mod loaded: the game answers a mod it cannot find with a warning and a clean boot, so the run fails fast at the server-started mark and the bus probes are what prove effect [#1793].
- Write every `[[verify]]` row as a gate certain to pass if the mod loaded at all, never as the reading the session exists for: an expectation is a substring of the dumped acknowledgement, so it cannot express absence or a numeric comparison [#1828, #2069/C/inference].
- Take the measurement on the side that owns the quantity: for nutrition, hunger and thirst, item aging and perks the server's reading is the measurement and the client's is a once-a-second mirror [#1826].
- Read the mod's state in a driver on the server, and read a client mirror only after a fresh `mirror.request` has answered: the client's mirror copy is a request-time snapshot of the server's numbers of that moment [#3012/C/inference, #2974/M/n=1].
- Manage hunger and thirst in anything that fills the calorie store: unattended, the level-4 thirst drain kills in about 35 game-hours on a 90-minute day and about 38 on the 60-minute default, the first figure measured once and the second arithmetic on it [#0179/M/one-fixture].
- Set the `Nutrition` sandbox option in the server's sandbox config: the nutrition update reads the option live every tick, a runtime flip from Lua is untried, and the Lua mirror of the option goes stale [#1127/C/C-only, #2058/C/inference].
- Run this mod's nutrition scenarios on the fixture's sandbox values, or pay for a fresh baseline beside any value moved: every nutrition reading in this library was taken on one fixture at one day length, so a moved option makes a new baseline rather than a comparison [#1253/C/one-fixture, #2071/C/inference].
- Read a sandbox option back off the run before a reading depends on it: only the day length has been set by a profile on a restored world and read back, while the other options the nutrition work names are settable and unexercised [#1809/C/C-only, #2072/C/inference].
- Grade a cross-side nutrition reading against a band built from its snapshot's own read skew, with the client half read first, and never against equality: a client-side reader is a staircase that steps when a packet lands while the server ramps, so a cross-side gap is a timing reading [#1483, #2070/C/inference].
- Never read a food tooltip's nutrition block as evidence of the Nutritionist gate unless the client runs without the debug flag and the food carries no label the viewer can read: the block also opens under the debug tooltip option and on a packaged food whose label the viewer can read, and the harness adds the debug flag to the admin account's client, so the block can show on a character holding neither Nutritionist trait [#2645/C/C-only, #1710, #2714/C/inference].
- Read a store a driver is about to raise and write it within one slow minute when the legacy mirror is on: the mirror rewrites the four stores on each slow minute, so a write sized from an earlier read lands against a store the mirror has since moved, as the x193 calorie arm's landed amount differed from the amount its driver predicted [#3309/C/inference] [#3293/M/n=1] [#3294/M/n=1].

## Also
- docs/reference/experiments.md — the specs of the owned experiments, their owners and the cost roll-up.
- docs/facts/body-and-weight.md#hunger-thirst — the thirst clock that kills an unattended subject, and the body-side sandbox option.
- docs/facts/wire-packets.md#staircase — the staircase a cross-side read draws and the band it is graded against.
