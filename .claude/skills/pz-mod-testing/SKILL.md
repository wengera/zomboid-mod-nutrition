---
name: pz-mod-testing
description: Running, changing or reading the live test harness — `python testing/pzt doctor`, `pzt run --profile`, `pzt scenario`, a `testing/profiles/*.toml` profile with `[[mods]]`, `[sandbox]`, `[[verify]]` and `[client] timeout`, the `PZTestKit` harness mod and a `TK.register` bus command (the generated `docs/reference/harness-commands.md`, `tools/bus_inventory.py`, `tools/luabalance.py`), a probe or witness reply, a driver under `testing/experiments/`, a live dedicated-server run and its committed `testing/artifacts/<run-id>/` JSON, a verification error or a run's exit code.
paths: ["testing/**"]
---
## Read first
- docs/platform/harness.md
- docs/reference/harness-commands.md
- docs/areas/testing-your-mod.md

## Rules quoted
- Never read a green run as evidence that a mod loaded: the game answers a mod it cannot find with a warning and a clean boot, so the run fails fast at the server-started mark and the bus probes are what prove effect [#1793].
- Name a profile's mod by the engine-resolved id: that is the `id=` of the `mod.info` the build actually reads — the newest `42[.x[.y]]/` folder first, then `common/`, then the mod root — and never the folder name [#1558].
- Write every `[[verify]]` row as a gate certain to pass if the mod loaded at all, never as the reading the session exists for: an expectation is a substring of the dumped acknowledgement, so it cannot express absence or a numeric comparison [#1828, #2069/C/inference].
- Gate a probe that can stall the client on the server side: verification is asked only after the client is ready, so a stalled session's client row never runs and the run records a verification error instead of a pass or a fail [#1769/M/n=1].
- Put every Java member call behind the index-first guard: a guarded call never raises and the argument-slot protected call never reaches the failure helper, while an unguarded raise, or a nested protected-call raise the mod catches, stalls the driven client [#1714/M/n=1].
- Cap the client wait in the profile whenever a probe can hang the client: the readiness wait is capped from the profile's client timeout, whose default is 300 seconds, and a profile that leaves the default sits out the full wait plus teardown — 384 seconds for a five-second hold — on a client that was never going to answer [#1768].
- Make every timing step a predicate with a budget and never a sleep: the world-ready barrier is a harness handshake rather than a timer [#1845].
- Copy every piece of measured evidence a document cites into a tracked per-run artifact folder as JSON, kept byte-identical: the full run directories with their logs stay local and untracked [#1705].

## Also
- docs/platform/harness.md#driven-client — the two-client fixture, the named `client:<user>` side, the profile's `clients` key and the release client.
- docs/reference/experiments.md — the named experiment specs a driver implements.
- docs/platform/lua-platform.md#kahlua-limits — the dialect every harness Lua edit must parse under.
- docs/reference/tools.md#claims-tools — the bus inventory generator and the Lua balance check a harness commit runs.
