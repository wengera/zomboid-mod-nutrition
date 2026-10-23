# `x127-20260911-052049` reading guide

**`x127-20260911-052049/platform-raise.json`** — produced by `testing/experiments/x127_raise.py`
at commit `5d3f22d` (355.1 s wall; 179 849 bytes, sha256 `52427aca…03c91e5`, byte-for-byte identical
to the run copy). Slice 12's session 7, the follow-on `x126` earned: the **nested** `pcall` shape and
the **unguarded** raise. **Skew-free** — driver and artifact in one commit on harness Lua at
`5d9633f`, clean, `doctor_clean true`, `acceptance_run run-20260911-050339`. This is the only run of
the slice whose acceptance result is a **FAIL**, and that is the harness working:
`acceptance_result` is `FAIL: 970 server error lines; lua errors on admin`, because the exit code
needs zero non-baseline server errors and the probe raises on purpose. Keep the run and grade off
the artifact.

- **Provenance — the profile and the probe.** `testing/profiles/x12-raise.toml`:
  `fixture = "default"`, `Mods=PZTestKit;TKX_RaiseProbe`, **no `[sandbox]`**, one tier-(a) row —
  client `lua.global TKX_R.version`. Mod H `TKX_RaiseProbe` is a single `shared/` file registering
  four handlers on one event: a counter, the nested shape `pcall(function() SomeNil() end)`, an
  **unguarded** `TKX_DefinitelyNilThree()` with a tail counter after it, and a counter registered
  **behind** the raising handler.
- **Server VM — the three readings.** The nested shape **catches**: `nested_ok "false"`,
  `nested_err "Object tried to call nil in pcall java.lang.RuntimeException"`, `nested_tail`
  advancing 54 → 71 — so `KahluaThread.pcall`'s try covers the nested `luaMainloop`, not only the
  argument slot. The unguarded raise **aborts the rest of its own handler's body**: `raw_tail "0"`
  on both passes after ~70 fires. The handlers registered **behind** it still run: `behind` 55 → 72,
  in lockstep with `before` — `Event.trigger`'s per-callback `protectedCallVoid` inside
  `catch (Throwable)` (**C**, `@194-@198 L41-L42`, `@216-@219 L31`), confirmed live. Real key paths:
  `phases.reads.server.values.*`, `second_pass.reads.server.values.*`,
  `second_pass.deltas.server`, `verdicts.P22_server`,
  `phases.classification.server.{gates, readings.err}`; the two passes are **65 s** apart (server
  pass 2 opened at wall 274.97 against 209.75, ≈ 17.4 game minutes, coherent with Δ17).
- **Client VM — the freeze, and its cause is citable.** The `-debug` harness client reached
  `in_game`, printed **one** complete trace, and then stopped: console dead at its last line,
  `ready` never printed, the bus never answering a single command, the process still alive
  (`client_ready`, `summary.client_bus_answered false`, `bus_dead.client true`). Identical on **two**
  independent boots. The cause is **C confirmed by M**: `KahluaUtil.fail(String)` takes its
  `Core.debug` arm at `L95`, prints `Lua fail. Message: %s` at `L96` and calls
  `UIManager.debugBreakpoint` at `L97` — **before** the throw at `L100`; `debugBreakpoint` returns
  at once on a `GameServer.server` (`L1183`, so no server ever breaks) and otherwise enters the
  modal `UIManager.sync.begin()` pump. The measured signature is in
  `phases.engine_log_signature.per_side`: **client 1 × `:96` and 0 × `:100`, server 356 × `:100` and
  0 × `:96`** — the client's throw never ran. Negative control: `x126`'s same `-debug` launch never
  touched `fail` (its raise is `call` L142's direct `athrow`) and stayed alive all session. So
  guarded code is safe on a debug client; an unguarded raise, **or a nested-`pcall` raise the mod
  catches**, is not.
- **Both raises are logged in full.** 73 `in pcall` + 73 `in Add` engine hits, two `flushErrorMessage`
  Lua dumps and a complete Java trace per raise. "Silent" applies **only** to `x126`'s argument-slot
  shape, which never reaches `KahluaUtil.fail`. `luaMainloop` L763 → `fail` builds
  `"… in " + closure.prototype.name`, which is why the message names `pcall` / `Add` and never the
  global.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session** for the server readings (two passes), **n = 2 boots** for the client freeze; one build, one probe file, one raise family. |
| every **client-side** reading | `phases.reads.client.*`, `summary.values.client` / `counters.client` (all `null`), `phases.classification.client.gates`, `verdicts.P22_client` `unmeasured`, `summary.h1_branch.client` / `h2_branch.client` `unmeasured` | **The client froze before it answered anything.** Zero hits for the H2 line say it never even reached the unguarded raise. Every client row of this session is `unmeasured`, and the verdict says so. |
| `summary.sides_agree` | `false` | **One reading and one silence is not two readings.** The server answered and the client never did; there is nothing to agree or disagree with. |
| `server_error_count: 892`, read as a fault **count** | 892 | Genuine engine output this time (0 harness echoes) — but the arithmetic is **10 entries per fire**: 4 `flushErrorMessage` heads, 4 bare `STACK TRACE` lines (`ERROR_RX` matches those too) and 2 `Exception thrown` lines, so 89 × 10 ≈ 892. Semantically it is "trace lines the probe caused", not events. The same caveat sits on `acceptance_result`'s `970`. |
| `verify` / `verify_error`, read as a failed gate | `verify` `[]`, `verify_error "TimeoutError: no ack for #1 lua.global within 30s"` | **The gate never ran.** `verify` is asked after `client_ready`, and this client never became ready — so the single client-side row recorded a timeout instead of a pass or a fail. Gate a raising probe on the **server**. |
| the freeze, read as **nested-`pcall`-specific**, or as "any Lua error freezes the debug client" | one trace, H1's | Both handlers route through `KahluaUtil.fail`, so the break is **shape-independent within that family** and H1 merely came first; and `x126` falsifies "any Lua error" outright. The live split is by raise **origin** — `call`'s direct `athrow` versus `luaMainloop` → `fail` — not by handler. The confound that remains is two raising handlers in one mod: one more session with the raises in **separate** mods settles which fired the break. |
| **release**-client behaviour, and what sets `showLuaDebuggerOnError` | — | `Core.debug`-gated in the jar (**C**) and **unmeasured**. The follow-up is the same probe under a `debug=False` client — a harness launch-flag change, outside this slice's file scope and named in [`areas/open-questions.md#x23`](../../../docs/areas/open-questions.md#x23). |
| `probe.lines` as a pin into the probe file | `32` / `37` | Frozen line numbers: they re-point if `TKX_RaiseProbe.lua`'s header is edited. Re-locate by content. A second frozen-driver note: this session's `pzt run --hold 5` burned **384 s** because `x12-raise.toml` left `[client] timeout` at its 300 s default — a profile fix, not a harness defect (the wait **is** capped: `testing/pzt/client.py:211`, fed from `cli.py:157` and `profile.py:326`). |
