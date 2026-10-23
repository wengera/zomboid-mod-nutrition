# `x132c-20261005-041640` reading guide

**`x132c-20261005-041640/cost.json`** — produced by `testing/experiments/x132_cost.py` at commit
`ad270bf` (178.3 s wall; 20 982 bytes, sha256 `3dd85b4f…2f61d3c4`, byte-for-byte identical to the run
copy). The **Plan 2 entry gate**, the design's § 6 cost budget, read in ONE live session of **two
serial boots** of the golden fixture: `boots.takeover` (`nr-takeover`, Mode 1) runs the mod's
`CalculateStats` handler instead of vanilla's seven stat updaters; `boots.overlay` (`nr-overlay`,
Mode 2) runs the seven updaters as the control. `doctor_clean true`, harness Lua `42425e9` clean,
build 42.20.4; `summary.verify_ok` `[true, true, true, true]` on both boots, `mods_not_found` empty on
both, `client_lua_error false` on both. **Skew-free**: the driver was written for this run and not
edited after it (it lands in this task's commit).

How to read it. Three phases, their verdicts in `verdicts`. **P1** (`phases.P1`) is the headline:
`bench.global NutritionRevamp.bench_fast 100000` on the takeover server returned `usPerCall 3.06`
(`ms 306` / `n 100000`) — the per-call wall cost of one whole fast-kernel step through the mod's entry
point. `bench_fast` fills one representative **steady-state awake** tick with every trait and flag
false, so the step takes its cheapest awake branch (the asleep, the stress-from-wounds/infection/
hemophobia and the idle-increment arms are not exercised; the not-deaf sound-stress arm and all seven
stat writes do run): the reading is a representative **floor** of the typical per-tick handler cost,
not a worst case. **P2** (`phases.P2`) is a **method note, not a measurement**: `bench.global
NutritionRevamp.kernel.fast.step 100000` calls the step with no arguments, so it raises on `inp.M` at
`NR_Kernel_Fast.lua:69` and `bench.global`'s own `pcall` catches it (`ack.calls 0`, `ack.error` set,
`ack.usPerCall 0.02` the cost of entering and catching the raise) — which is exactly why Task 2
exposed `bench_fast` as the step's benchable proxy. **P3** (`phases.P3`) reads `tick.rate 10` on each
boot server-side: takeover `10.01` ticks/s, overlay `10.10` ticks/s, `takeover_over_overlay 0.990` —
the handler holds the server tick rate within about 1 % of the seven updaters it replaces. The
absolute ~10 ticks/s is this host's own server OnTick cadence; the comparison is the ratio.

- **The entry-gate verdict** (`verdicts.ENTRY_GATE`, `summary.entry_gate`) is **`proceed`**: the
  per-call cost (3.06 µs) is within the ≤ 50 µs budget and takeover's tick rate tracks overlay's
  (≥ 90 %), so takeover stays the shipped default and Plan 2 runs as written. Had either failed, the
  overlay-default finding would have changed only the shipped mode and the § 6 claim (read by Task 11
  and Task 17), never the plan's other tasks — the engine is built either way.
- **The takeover boot's `server_error_count 7` is the P2 probe, not a fault.** The seven are the
  deliberate no-argument `kernel.fast.step` bench raising at `NR_Kernel_Fast.lua:69`, caught by
  `bench.global`'s `pcall`, plus the Kahlua `flushErrorMessage` / `STACK TRACE` lines the server error
  collector counts; the overlay boot, which runs no P2 probe, has `server_error_count 0`, and P1 and
  P3 on the takeover boot are clean.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one admin character, two boots, one build. |
| `phases.P2.ack.usPerCall`, `phases.P2.ack.ms` | `0.02`, `2` | P2 is a method note, not a measurement: `kernel.fast.step` was called with no arguments, raised on `inp.M` at `NR_Kernel_Fast.lua:69` and was caught by `bench.global`'s own `pcall` (`calls 0`, `error` set). The number is the cost of catching the raise, not of the step. Cite `phases.P1.ack.usPerCall` — `bench_fast` is the step's proxy. |
| `boots.takeover.server_error_count` | `7` | The seven are the P2 probe's expected caught raise (above), not a handler fault; `boots.overlay.server_error_count` is `0` and the P1/P3 readings are clean. |
