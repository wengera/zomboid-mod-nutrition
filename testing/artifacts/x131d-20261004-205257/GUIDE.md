# `x131d-20261004-205257` reading guide

**`x131d-20261004-205257/accept-c.json`** — produced by `testing/experiments/x131_accept_c.py` at commit
`9a424d8` (124.2 s wall; 40 796 bytes, sha256 `4e47bce9…617f9a9b`, byte-for-byte identical to the run
copy). Plan 1 acceptance **run C**, the smoke test of the fix-wave commit `9a424d8`: the takeover
handler now finds its hoisted handles in `NutritionRevamp.server.fast.byChar`, a Lua table keyed by the
`IsoPlayer` object, and falls back to the guarded username lookup only on a miss. Same profile as
`x131b-20261004-175911` (`testing/profiles/nr-accept.toml`, golden fixture, no `[sandbox]`, so `Mode` is
its default 1 = takeover); harness Lua at `42425e9`, clean, `doctor_clean true`, `acceptance_run
"x131b-20261004-175911"`. **Skew-free**: the driver is a copy of the frozen b driver, changed before the
run only in its artifact name, `SESSION`, `ACCEPTANCE_RUN`, the run-id prefix and a new P1.9, and not
edited after it. Every verdict `as_predicted`; `summary.verify_ok` `[true, true, true, true]`;
`server_error_count 0`; `client_lua_error false`; zero `STACK TRACE` lines in either log.

How to read it. `phases.P1.byChar` is the new reading. Its four counter reads were taken in the sandwich
order `byCharHits` a, `calls` a, a 10 s wait, `calls` b, `byCharHits` b, so the hits window (12.06 s)
contains the calls window (10.04 s): with no miss between the two calls reads, `dHits >= dCalls` by
construction. Read `dHits` against `dCalls`; `failures` and `disabledAt` sit beside them at both ends.

- **The character key hits.** `byCharHits` 458 → 571 (`dHits` 113) while `calls` 466 → 566 (`dCalls`
  100): every handler call inside the calls window took the `FAST.byChar[character]` hit, so a Kahlua
  table keyed by the `IsoPlayer` returned the stored entry on the engine's every call. `failures` 0 and
  `disabledAt` unresolved (never set) at both ends (`verdicts.P1.9`).
- **Every b-run reading reproduces.** `versions` `0.1.0` on both sides; `takeover` `registered true`,
  `failures 0`, hoist `missing` keyCount 0; `statsMove` thirst Δ 1.27911e-3 against 8.0e-6 × 159.86
  game-s = 1.27892e-3 (ratio 1.00015), hunger ratio 1.00016 (direction graded); `calls` 159 → 266 over
  10.04 s wall; `mirror` `received 1`, `username` / `v` / `mode` `"admin"` / `1` / `1`; `bench`
  `usPerCall 2`; `store` `records.admin.v` 1, `players.minutes` 19 → 22 over 10.02 s wall; `logs` one
  server self-report, one registration line, one client self-report, and no trace line on either side.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one player, one build. |
| `phases.P1.byChar.calls_minus_hits`, `summary.byChar.calls_minus_hits` | `{a: 8, b: -5}` | Each side of the difference is two sequential bus reads under a second apart at about 10 handler calls a second, so it measures the read gap, not the misses since boot. |
| `phases.P1.byChar.dHits_minus_dCalls`, `summary.byChar.dHits_minus_dCalls` | `13` | The surplus is the sandwich order's wider hits window (its reads bracket the calls reads), not hits beyond calls. |
| `phases.P1.mirror.received`, read as "the first-sight send arrived" | `1` | As in `x131b-20261004-175911`: two sends reach the client by the code path and the count reads 1; cite it as "a mirror arrived". |
| `phases.P1.store.minutes.serverWorldAge` | `{a: null, b: null}` | A `lua.global` ack carries no world age, so the nulls are an absent field; the window is `window_measured_s`. |
