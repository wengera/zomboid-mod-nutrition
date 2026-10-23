# `x30-regrade-20261011` reading guide

**`x30-regrade-20261011/summary.json`**, **`x301.json`** and **`x302.json`** — a derived artifact: an analysis run, not a live run, and the F-T7-1 fix's own diff (ruling T7-1). Produced by `testing/experiments/x30_regrade.py`, committed with the fix at `51e6b2e9` (`replay_live`: ring activity events no longer mark rows `between`; logged eats, drinks and sleep events keep the skip), over the committed runs `x301-20261011-085950` and `x302-20261011-091000` with `tools/replay_live.py` at `51e6b2e9` (`sleep_allowed` true, the library entry `replay_live` and `diff`); nothing is booted and the run folders are read only. The output carries no commit stamp: the script, the tool and the output's provenance are the one commit `51e6b2e9` (`git log`). Run on a `git archive` of `51e6b2e9` with the two run folders copied in (on 2026-10-11 into a scratch folder), it reproduces all three files byte for byte (`cmp` silent): `summary.json` 1385 bytes, sha256 `97414340…8331a204`; `x301.json` 728, `6972d12c…4f0f27df`; `x302.json` 727, `bda159a7…7ee384a1`.

How to read it. Each `x30N.json` holds one run: `ring_rows`, `ring_activity_events` (2442 and 1860: still built, no longer marking rows), `tol` (do-not-cite) and `diff` (the tool's own: `fields.<f>.n`, `.max`, `.over`, `.worst_s`; `classes`; `skipped_n`; `ok`); `summary.json` the same per run with `graded_n` and `field_max`. Field names are literal keys with dots (`body.energyState`, `satiety.L`).
- **The diff** (`x30N.json` `diff.fields`; `summary.json` `<s>.ok`): x301 HUNGER max 0.00115, `body.energyState` 0.00184, `satiety.L` 0.0 over n = 2321; x302 HUNGER 0.00172, es 0.00161, L 0.0 over n = 1708; `over` 0 everywhere and `ok` true in both. The classes: `between` 120 and 151 (the rows after a logged eat, drink or sleep event), `gap` 208 and 271 (long minutes of the held nights, as the grade's guide defines them), offline 5 and 5. **This is the tool's diff of record for x301 and x302**: the run-time `replay.diff` (`b4b9a298`) compared 0 rows, and the in-driver REPLAY verdicts read falsified for that reason alone (F-T7-1). The maxima equal the grade's own diff's; the graded n differ because the tool also skips the row after each sleep event.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything here, as a measurement | — | An analysis run over `n = 1` runs; its replay figures are the tool's, its live figures copies of the committed rings. |
| `tol` (`x30N.json`) | HUNGER abs 0.002, es abs 0.005, L rel 0.005 | Copies of the tool's `DEFAULT_TOL` constants, not computed from these runs. |
| parents of the keys above, as a whole: none (`tol` sits at each file's top level) | — | Cite a reading by its path under `diff` (§ 4.9). |
