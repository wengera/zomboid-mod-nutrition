# `x193-20261006-201004` reading guide

**`x193-20261006-201004/two.json`** — produced by `testing/experiments/x193_two_clients.py`, written before the boot and committed with this file unedited, on HEAD `81b244d` (mod `0df50bb`, clean: the sync build — `NR_Server_Reconcile.lua` at `2d4dc4d` and `0df50bb`; harness Lua `0ff30f4`, clean; the named-client driver side and fixture `two` at `3ce7119`)
(356.9 s wall; 397565 bytes, sha256 `c25509f8…cdb987af5e`, byte-for-byte identical to the run copy). **Plan 8 Task 7, live 3**: one server boot, two clients attached one at a time through `attach_clients` — `admin` with `-debug`, then `bob` without it (a release client; `boot.client_debug`) — build 42.20.4, profile `x19-two` (PZTestKit + NutritionRevamp by path + TKX_DeclaredFood; `Nutrition` false; DayLength 1; no `[sandbox.NR]` block; sleep off). `doctor_clean` true; `mod_dirty` false; `server_error_count` 0; `admin_lua_error` false; every `verify` row `ok`.

How to read it. Every verdict is `as_predicted` except `D`, **falsified** on one clause only: the driver predicted the landed calories at 500 plus or minus 10 and the landing read 512.6971752597278, having read the store (`phases.D.before.store`, wall 232.242) before its write (`phases.D.set`, wall 236.815), a gap in which the legacy mirror's rewrite of the store would explain the difference (inference, not read); every other clause of `D` held. Every step carries its `side` (`server`, `client:bob`, `client:admin`); paired reads run `bob`, then `admin`, then the server. `kin_minutes` and the reconcile `minutes` count one per player per slow minute, so two players add two a minute (inference from the adapters).

- **S0**: `admin` ready 36.3 s and `bob` 40.9 s after their launches; each mirror's `username` its own; `received` 2 on each; `view.level` 2 on each; `isDebugEnabled` false on `bob`, true on `admin`; `getLuaDebuggerErrorCount` 0 on each; both records `v` 2, `reconcile.count` 0; a first-sight line for each.
- **A**: `bob.nutrients.vitC.p` set 0.05 (before 0.9978313092972612); `bob`'s grade 4 after 2 s; the effects pushes 2 → 3; `bob`'s `received` 2 → 3 by 20.381 s after the write, `nut_vitC_g` 1 → 4, username `bob`; `admin`'s `received` 2 → 2, `nut_vitC_g` 1, username `admin`.
- **B**: `ModData.exists` false on both clients, each census `keyCount` 0 with `bob` and `admin` missing (the census creates an empty local table, so it was read after the exists); the server's exists true, `keyCount` 2.
- **E**: `bob`'s key presses 0 → 1 → 2, opens 0 → 1, requests 0 → 1, closes 0 → 1, visible true then false; `received` 3 → 4 at the first read; level 2, deficiency class 3, `rows[3].text` `UI_NR_Class_deficiency_3`, 30 rows; `admin`'s panel counters 0 and deficiency class 0.
- **C**: the push reply's `traitList` `["nutritionist"]`; `bob`'s list size 0 → 1 at the first read and at 1.025 and 2.299 s; `admin`'s list 0 throughout; the server's `bob` 1 and `admin` 0; at `bob`'s pulled mirror `bob` hasTrait true and level 3, `admin` false and 2. `admin`'s client copy of `bob` is not read (`phases.C.admin_copy_of_bob`).
- **D**: the calorie store -349.5829772949219 → written 150.41702270507812; `reconcile.count` 0 → 1 at the first poll and 1 at the follow-up; `lastIntake` `reconciled`, 512.6971752597278 kcal, carbs, lipids and proteins 0; the stomach buffer's calories 0 → 506.59490568777954 → 467.6029263981277; no other buffer key and no nutrient pool risen; `landed` 0 → 1 → 1; `admin`'s count 0 throughout; no `reconcile:` line in the server log (a level-3 line at `log=2`).
- **F**: `bob` answered `TK.version` 1 and the mod's `0.1.0` over the bus, `isDebugEnabled` and `getDebug` false, error count 0, the tooltip's original a function; `admin` true, true, 0; the server false, false, 0.
- **G**: the server 10.051751592356688, 10.0542531481758 and 10.051251430561775 ticks a second with both clients attached; `bob` and `admin` about 60.
- **Z**: `bob`'s count 1, `admin`'s 0; store failures 0; no mod error.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters. |
| `predictions`, `constants`, `deviations`, `world_changes`, `verdicts.*.predicted` | the driver's tables | Written before the run; not readings. |
| `baseline`, `verdicts.G.observed.baseline` | x183b's ticks | Copied from `x183b-20261006-175149`; cite that run's own file. |
| `verdicts.D.verdict` | falsified | Falsified only on the landed amount; cite the clauses in `verdicts.D.observed`. |
| `phases.E.after1.bob.row_def_*.first.after`, `phases.E.after1.bob.row_def_*.restored`, `verdicts.E.observed.bob_row3_restored` | `0` and the written-back value | The driver's own writes in its `lua.setpath` read; the reading is each `.before` (`.value`). |
| `verdicts.B.observed.bob.keys`, `verdicts.B.observed.admin.keys`, `phases.B.bob.census.keys`, `phases.B.admin.census.keys` | `{}` | The empty Lua table, which the encoder writes as an object; an empty list. |
