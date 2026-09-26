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
- Ask a probe of both sides: the acceptance profile put the same trait check to the server and to the client and both returned the mod's effect, so the mod was present in both Lua states and not merely in the server's [#1825/M/n=1].
- Set the `Nutrition` sandbox option in the server's sandbox config: the nutrition update reads the option live every tick, a runtime flip from Lua is untried, and the Lua mirror of the option goes stale [#1127/C/C-only, #2058/C/inference].
- Run this mod's nutrition scenarios on the fixture's sandbox values, or pay for a fresh baseline beside any value moved: every nutrition reading in this library was taken on one fixture at one day length, so a moved option makes a new baseline rather than a comparison [#1253/C/one-fixture, #2071/C/inference].
- Read a sandbox option back off the run before a reading depends on it: only the day length has been set by a profile on a restored world and read back, while the other options the nutrition work names are settable and unexercised [#1809/C/C-only, #2072/C/inference].
- Grade a cross-side nutrition reading against a band built from its snapshot's own read skew, with the client half read first, and never against equality: a client-side reader is a staircase that steps when a packet lands while the server ramps, so a cross-side gap is a timing reading [#1483, #2070/C/inference].

## Also
- docs/reference/experiments.md — the specs of the owned experiments, their owners and the cost roll-up.
- docs/facts/body-and-weight.md#hunger-thirst — the thirst clock that kills an unattended subject, and the body-side sandbox option.
- docs/facts/wire-packets.md#staircase — the staircase a cross-side read draws and the band it is graded against.
