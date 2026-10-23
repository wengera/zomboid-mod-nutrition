# `exp01-20260910-003929` reading guide

**`exp01-20260910-003929/eat-matrix.json`** — produced by `testing/experiments/s01_eat_matrix.py`
at commit `1d32909`. Since `39fceca` the script additionally:

- Records **`state_spawned`** per row (surfaced as `stateSpawned` in `summary`) — the item's
  provenance at `item.state` time, which is the reading that matters, because `item.state` does
  the find-or-spawn and a later `eat` would report "found" either way. This file has neither key.
- Matches **`log_grep` case-insensitively**. The committed **`log_grep.Nutrition: []` is a
  case-sensitive false negative**: the harness logs its own commands lowercase
  (`nutrition.get`), and a case-insensitive grep of the same server log returns 27 hits. The
  `SyncItemFields` and `EatFood` zeros in that block **were** re-verified case-insensitively
  against `testing/runs/exp01-20260910-003929/server-stdout.log` (`grep -ic` → 0 for both) and
  stand.
- Runs an **unconditional `sandbox.set Nutrition true` in teardown** (recorded as
  `sandbox_nutrition_restored`). This run has no such key: the belt-and-braces restore did not
  exist yet. Its in-band restore did run and read back `true`
  (`probe_sandbox.restore_true.after`), so the fixture was left as found regardless.
