# `x126-20260911-045205` reading guide

**`x126-20260911-045205/platform-pcall.json`** — produced by `testing/experiments/x126_pcall.py`
at commit `72b6355` (119.9 s wall, no `error` key, `client_lua_error false`; 54 212 bytes, sha256
`ef67191e…88423cf`, byte-for-byte identical to the run copy). Slice 12's session 6, added by the
controller to measure **this library's own standing rule** — "a Kahlua nil call escapes `pcall` and
kills the whole handler" — which rested on `exp01-20260909-235420`, a run with no committed
artifact, while the jar read the other way twice over. **Skew-free** — driver and artifact in one
commit on harness Lua at `5d9633f`, clean, `doctor_clean true`,
`acceptance_run run-20260911-044417`, and the file additionally records
`harness_lua_commit_expected` / `harness_lua_commit_matches`.

- **Provenance — the profile and the probe.** `testing/profiles/x12-pcall.toml`:
  `fixture = "default"`, `Mods=PZTestKit;TKX_PcallProbe`, **no `[sandbox]`** (so `EveryOneMinute`
  fires every 3.75 real s), one tier-(a) row — client `lua.global TKX_P.version`, assigned in the
  table constructor on the file's first line, so it answers 1 the moment the file has run at all.
  The **server side is ungated on purpose**: the probe is a single `shared/` file, so whether the
  server VM runs it too is itself a reading (`TKX_P.side`). Mod G `TKX_PcallProbe` registers four
  handlers on one event: a counter, `pcall` on a global that is never defined, a second counter
  **behind** it, and `pcall(error, "boom")` as the control.
- **The reading, two passes 12 s apart, both sides.** `ok` `"false"` and `err`
  `"tried to call nil java.lang.RuntimeException"` — byte-identical per side — with `tail` advancing
  (client 3, server 15) and `behind` equal to `tail` on pass 1. The control held (`ctrl_ok`
  `"false"`, `ctrl_err` carrying `KahluaException boom`) and H0 fired (`before` 2 / 14). Real key
  paths: **`phases.reads.<side>.values.*`** (or `summary.values.<side>`) and
  **`verdicts.P21_client` / `verdicts.P21_server`** — not `readings.*` / `verdicts.P21`.
- **So the first half of the rule is wrong, and the guard survives for a different reason.** The
  quoted string is exactly what `pcall` **returns**. The jar confirms there is a real raise to catch
  (`KahluaThread.call(I)I @14-@23 L139`, `@25 ifnonnull 40`, `@30-@39 L142` `new RuntimeException` /
  `ldc 'tried to call nil'` / `athrow`; `pcall(I)I` invokes `call` at `@80-@85 L1740` inside its try
  and the `Throwable` arm at `@189 L1758` builds `getMessage()` + `getClass().getName()`) — so "a
  raise was caught" is the correct wording, and the **full** string, message *and* class name, is
  what to quote. `TK.call` / `tkxCall` stay because the catch **names nothing**
  (`names_the_global: false`; the engine logged nothing at all).
- **Bound.** This probe measured `pcall(<nil function argument>)` — the shallow arm, originating in
  `call(I)I @30-@39` **before** `pushNewCallFrame` and the nested `luaMainloop`. The nested shape
  and the unguarded raise are session 7 (`x127-20260911-052049`).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, two passes, one build, one probe shape. |
| `server_error_count: 4` and the four `server_errors` entries | 4 | **A harness classifier artefact — zero engine faults.** `ERROR_RX` (`testing/pzt/server.py:15`) is applied at `:253` to every non-indented server line no `BASELINE_NOISE` pattern whitelists, and there is no PZTK-echo pattern: all four entries are verbatim `PZTK: cmd #N lua.global -> …` echoes of **this driver's own bus replies**, which happen to carry the exception string it was reading. Any session whose readings quote an exception inflates the number the same way. Read `server_errors` itself. |
| the engine's log silence, read as evidence about **unguarded** raises | 0 hits for `TKX_DefinitelyNil`, `attempted to call`, `ExceptionLogger` | **No unguarded raise occurred here.** Silence is a property of the *caught, argument-slot* shape. `x127-20260911-052049` measured the unguarded and nested shapes, and there the engine logs the raise **in full** (73 + 73 trace blocks). |
| a pass's fields, read as an atomic snapshot | client `before` 2 < `tail` 3 on pass 1 | **Each `lua.global` field is its own bus round-trip.** A fire can land between two reads: on pass 2 `behind = tail + 1` on both sides (client 11/12, server 23/24). Compare **adjacent** fields (`behind` against `tail`), and read the per-side advances (`before`/`tail`/`behind`: client +9/+8/+9, server +8/+8/+9) rather than differencing across the passes. |
| `err`, quoted as the message alone | `tried to call nil java.lang.RuntimeException` | Quote the **whole** string. It is `getMessage()` concatenated with `getClass().getName()`; this library's old rule quoted only the message half, which is part of why the two readings were ever confused. |
| `summary.branch` / `verdicts.P21_*`, read as settling the rule's **second** half | `i_pcall_catches`, `as_predicted` | This run settles the first half only. "Kills the whole handler" was **unmeasured** until `x127`, where it turns out to be **right** for the handler's own body and **wrong** for the handlers behind it. |
