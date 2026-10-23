# `x202-20261006-220437` reading guide

**`x202-20261006-220437/raise.json`** — produced by `testing/experiments/x202_client_raise.py`, written before the boot and committed at `31b0b31` with the probe mod and the profile before the run, unedited since, on HEAD `31b0b31` (mod `1a8e207`, clean, staged as for x201; probe `31b0b31`, clean; harness Lua `fadf698`, clean)
(359.5 s wall; `raise.json` 88388 bytes, sha256 `db7e707c…a01a0af7`, byte-for-byte identical to the run copy). **Plan 9 Task 5, live 2, X23**: the driver's own layout lint (`lint_errors` empty), one server boot, two clients attached one at a time through `attach_clients` with a 180 s ready wait (`deviations`: the profile's 60 s client timeout guards `pzt run`, and no raise happens before the driver fires the event) — `admin` with `-debug`, then `bob` without it (`boot.client_debug`) — build 42.20.4, profile `x20-raise` (PZTestKit + the staged NutritionRevamp + `TKX_ClientRaise`, by path; `Nutrition` false; DayLength 1; one server-side `verify` row, `ok`). `doctor_clean` true; `server_error_count` 0.

How to read it. Every verdict is `as_predicted`. The probe is `TKX_ClientRaise.lua`, a `client/` file: `TKX_CR` holds string counters; the custom event `TKX_ClientRaise` carries H0 (`before` ++), H1 (an unguarded `TKX_DefinitelyNilClient()` at line 42, then `raw_tail` ++) and H2 (`behind` ++); `debugFlag` and `showFlag` are read once at `OnGameStart`. Every bus read records its status (`answered` or `timeout`). The `B` and `C` console blocks are the lines after a byte offset taken just before each trigger, the bus's `PZTK: ` echo lines dropped.

- **A**: `TKX_CR.version` 1 and `registered` `"true"` on both clients; all six counters `"0"` before any trigger.
- **X23** (`bob`, release): the `event.trigger` reply `ok` true; 15 rounds, 45 reads, 45 answered, 0 timed out; `before` `"1"`, `raw_tail` `"0"`, `behind` `"1"` at every read; `bob` in the server's player list after `B` and in `D`, its process alive, no `kicked` marker, and `D`'s read again `1`, `"1"`, `"0"`, `"1"`. Its console's flagged lines: one trace whose exception is `java.lang.RuntimeException: Object tried to call nil in Add at KahluaUtil.fail(KahluaUtil.java:100)`, the Lua stack `TKX_ClientRaise.lua:42` under `event.trigger`; the harness's `lua_error` marker matched that trace.
- **X23_admin** (`admin`, -debug): the trigger's reply timed out at 10 s and all 9 reads after it timed out; the console printed `Lua fail. Message: Object tried to call nil in Add` from `KahluaUtil.fail(KahluaUtil.java:96)`; the `lua_error` marker absent before the trigger and present after; the process alive at the end of `C` (the teardown's quit timed out, `client_quit` rc `null`, and the harness killed it).
- **X23_flags**: `debugFlag` `"false"` on `bob` and `"true"` on `admin`; `showFlag` `"true"` on both, and `lua.call UIManager.isShowLuaDebuggerOnError` replied `r1` true on both.
- The server log after the trigger held one line, the bus echo; nothing of the probe's.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one raise shape, one release client. |
| `predictions`, `constants`, `deviations`, `world_changes`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `verdicts.X23_admin.observed.before_last`, `verdicts.X23_admin.observed.raw_tail_last`, `verdicts.X23_admin.observed.behind_last` | `null` | No read answered; `null` is an absent reply, not a counter value. |
| `verdicts.X23.observed.console_flagged_count`, `verdicts.X23_admin.observed.console_flagged_count` | 8 and 4 | Counts of flagged lines, a trace's header lines counted apiece; cite the lines in `phases.B.console.flagged` and `phases.C.console.flagged`. |
