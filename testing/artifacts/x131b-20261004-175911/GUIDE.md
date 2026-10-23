# `x131b-20261004-175911` reading guide

**`x131b-20261004-175911/accept-b.json`** — produced by `testing/experiments/x131_accept_b.py` at commit
`afdd7f4` (112.3 s wall; 32 976 bytes, sha256 `a8bbd9f8…5a9491e4`, byte-for-byte identical to the run
copy). Plan 1 acceptance **re-run** after the store fix `65d1e8d` (`ModData.getOrCreate(name)` as a
static, behind a nil check and a `pcall`; the profiles' control rows renamed to `TK.version`). Same
profile as `x131-20261004-175014` (`testing/profiles/nr-accept.toml`, golden fixture, no `[sandbox]`, so
`Mode` is its default 1 = takeover); harness Lua at `42425e9`, clean, `doctor_clean true`,
`acceptance_run "x131-20261004-175014"`. **Skew-free**: the driver is a copy of the frozen first driver,
changed before the run only in its artifact name, `SESSION`, `ACCEPTANCE_RUN`, the trace regex (the
engine frame shape `Lua((MOD:Nutrition Revamp)).<fn>(NR_….lua:N)`, limit 40, checked against the first
run's log first: 154 hits there), P1.5 (the mirror read field by field) and a new P1.8 (the store
record and the slow clock), and not edited after it. Every verdict `as_predicted`; `summary.verify_ok`
`[true, true, true, true]`; `server_error_count 0`; `client_lua_error false`; zero `STACK TRACE` lines
in either log.

- **The store attaches.** The server log carries `[NutritionRevamp] store attached (new world: true)`
  (line 1996, before the takeover registration at 2046) and no trace; `phases.P1.store.record_v`:
  `NutritionRevamp.server.store.records.admin.v` resolves to `1`, and `records` is a table of
  `keyCount 1` (`verdicts.P1.8`).
- **The mirror reaches the client.** `phases.P1.mirror`: `NutritionRevamp.client.received` reads `1`,
  `client.mirror` is a table of `keyCount 9`, and its `username` / `v` / `mode` read `"admin"` / `1` /
  `1` (`verdicts.P1.5`). The server log carries `players: first sight of admin` at frame 360.
- **The slow clock ticks.** `phases.P1.store.minutes`: `server.players.minutes` 21 → 23 over 10.03 s
  wall (`verdicts.P1.8`).
- **The first run's readings reproduce.** `phases.P1.versions` `0.1.0` on both sides; `takeover`
  `registered true`, `failures 0`, hoist `missing` keyCount 0; `statsMove` thirst Δ 1.44563e-3 against
  8.0e-6 × 180.71 game-s = 1.44572e-3 (ratio 0.99994), hunger Δ 1.72878e-3 against 1.72887e-3 (ratio
  0.99995, direction graded); `calls` 165 → 285 over 11.29 s wall (Δ 120, 10.6 per wall second),
  `failures_end 0`; `bench` `usPerCall 2`; `logs` one server self-report `… side=server mode=takeover
  log=2 frameworks=none hook=true limitations=3`, one `fast: takeover handler registered`, one client
  self-report, and the trace lists empty under a regex that does match this build's frames.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one player, one build. |
| `phases.P1.mirror.received`, read as "the first-sight send arrived" | `1` | Two sends reach this client by the code path — the answer to its `OnGameStart` `mirror.request` and the server's first-sight `sendMirror` — and the count reads 1, not 2. The run does not say which one arrived, nor why the other did not; cite it as "a mirror arrived", not as which route carried it. |
| `phases.P1.store.minutes.serverWorldAge` | `{a: null, b: null}` | A `lua.global` ack carries no world age, so the nulls are an absent field, not a reading; the window is the wall pair `window_measured_s`. |
