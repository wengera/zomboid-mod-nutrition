# `x131-20261004-175014` reading guide

**`x131-20261004-175014/accept.json`** — produced by `testing/experiments/x131_accept.py` at commit
`58c103d` (117.9 s wall; 29 446 bytes, sha256 `2eb79300…278a4e4`, byte-for-byte identical to the run
copy). Plan 1 acceptance: the mod loads on both sides, the takeover handler registers and the stats
move. The first live boot of `NutritionRevamp` under the harness, on `testing/profiles/nr-accept.toml`
(`PZTestKit` + `NutritionRevamp` from `mod/NutritionRevamp`, golden fixture, **no `[sandbox]`**, so the
mod's `Mode` option is its default 1 = takeover). Harness Lua at `42425e9`, clean, `doctor_clean true`,
`acceptance_run "none: this is the acceptance run"`. **Skew-free**: the driver was written before the
run and not edited after it. One phase `P1`, every read wall-bracketed in `steps`, every verdict in
`verdicts`.

- **The mod loaded in both Lua states.** `phases.P1.versions` reads `0.1.0` on the client and the
  server (`verdicts.P1.1`), and the profile's two mod rows `verify[1]` / `verify[3]` pass;
  `mods_not_found` is empty on both sides.
- **The takeover handler registered.** `phases.P1.takeover.registered true`, `failures 0`,
  `disabledAt` unresolved (never set) and the hoist of `admin` complete
  (`phases.P1.takeover.hoistMissing.keyCount 0`) — `verdicts.P1.2`, `P1.2b`. The server log carries
  exactly one `[NutritionRevamp] fast: takeover handler registered` and one self-report
  `NutritionRevamp v0.1.0 build 42.20.4 side=server mode=takeover log=2 frameworks=none hook=true
  limitations=3`; the client console one `… side=client mode=takeover log=2 frameworks=none`
  (`phases.P1.logs.self_report_server`, `registered_lines`, `self_report_client`).
- **The stats move under the handler.** `phases.P1.statsMove`: two server `stats.all admin` reads
  11.81 s wall apart, 180.62 game-seconds by their own `worldAge`; thirst 0.0021137 → 0.0035588,
  Δ 1.44501e-3 against 8.0e-6 × 180.62 = 1.44495e-3 (ratio 1.00004, `verdicts.P1.3-thirst`); hunger
  0.0025333 → 0.0042614, Δ 1.72813e-3 against 9.6e-6 × (1 − h̄) × 180.62 = 1.72805e-3 (ratio 1.00005,
  graded on direction only, `verdicts.P1.3-hunger`). Both reads carry 24 stats and an empty `missing`
  (`phases.P1.field_count`). `phases.P1.calls`: `fast.stats.calls` 161 → 281 over 11.31 s wall
  (Δ 120, 10.6 per wall second, one player), `failures_end 0` (`verdicts.P1.4`).
- **The bench.** `phases.P1.bench`: `NutritionRevamp.kernel.fast.defaults` × 1000 in 2 ms on the
  server, `usPerCall 2` — at `getTimestampMs` resolution, so the reading is 2 ± 1 ms over the loop and
  is a first order of magnitude, not a cost.
- **Two findings the run was not built to look for.**
  (1) **The store never attaches.** The server log carries ten fires of `expected argument of type
  String, got KahluaTableImpl` at `NR_Core.lua:37` (`NR.call`), from `NR_Server_Store.lua:15`
  (`S.attach`): once in `OnInitGlobalModData` (`Add` at `:54`, inside `GlobalModData.init`) and
  then from `S.get` (`:26`) about once a game minute. `NR.call(ModData, "getOrCreate", name)` calls
  `m(ModData, name)`, passing the class table as the first argument of a static method that wants a
  String. That is the 60 in `server_error_count` (6 classifier entries per fire), and by the code path it is why
  `phases.P1.mirror.received` reads **0** and `NutritionRevamp.client.mirror` is unresolved
  (`verdicts.P1.5` falsified): `mirror.request` reaches `store.get`, which raises before
  `sendMirror`. (2) **The profile's control rows fail.** `verify[0]` / `verify[2]` ask
  `lua.global PZTestKit.version` and read `failedAt "PZTestKit"` on both sides: the harness global is
  `TK` (`TK.version = 1`), not `PZTestKit`, so the control is mis-named in the profile — the walk
  itself works, as the mod rows beside it show.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one player, one build. |
| `verdicts.P1.7`, `summary.verdicts.P1.7` | `as_predicted` | **Half of P1.7 was never measured.** Its "no Lua trace naming an `NR_` file" half grepped for `file: NR_…` / `MOD: NutritionRevamp`, and this build prints a mod frame as `Lua((MOD:Nutrition Revamp)).call(NR_Core.lua:37)` — the display name with a space, no `file:` prefix — so the trace grep could not match and did not. The server log carries ten such traces. Read the self-report half from `phases.P1.logs.self_report_server`, `registered_lines` and `self_report_client`, and the traces from `server_errors` and the run's server log. |
| `phases.P1.logs.server_trace_lines`, `phases.P1.logs.client_trace_lines` | `[]` | The same regex: an empty list is a regex that never matched, not an absence of traces. The client side is clean on other evidence (`client_lua_error false`, zero `STACK TRACE` lines in its console). |
| `verify`, read as "the four verification rows pass" | `summary.verify_ok [false, true, false, true]` | The two `false` rows are the mis-named harness control (`PZTestKit.version`; the global is `TK`), not a mod failure. Cite `verify[1]` and `verify[3]` for the mod. |
