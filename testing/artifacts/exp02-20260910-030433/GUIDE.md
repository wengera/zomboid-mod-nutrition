# `exp02-20260910-030433` reading guide

**`exp02-20260910-030433/lifecycle.json`** — produced by `testing/experiments/s02_lifecycle.py`
at commit `5714117`. Since `d9ff9a7` the script writes five keys this file therefore lacks:

- **`fixture`** and **`build`** at the top level — the fixture name and the server build parsed
  out of the startup log. Absent here, so the fixture and the build behind these numbers are on
  the word of the run report (slice 02's task-M report, in the SDD workspace, outside the tree) rather
  than the artifact.
- **`dWorldHoursWait`** and **`dWorldHoursContaining`** on phase (c). This file carries the wait
  window only, as `summary.c.dWorldHours` = **24.50126** game-hours. The *containing* window —
  from the `setAge(0)` reply to the `item.get` reply, which is the window the item actually aged
  over — is **not** a key here; the doc derives it from the two `serverWorldAge` stamps this file
  does carry (**2.400196 → 26.956989** = 24.556793 game-h).
- **`expectedFrom`**, the flag saying which of the two windows the prediction was computed over.
  The prediction in this file, `summary.c.expectedAtRotSpeed1` = **1.0209**, is therefore the
  **wait-window** figure — which flatters the phase-(c) shortfall to 1.3 %. The current script
  predicts over the containing window instead. **The 1.0232 / 1.5 % pair quoted in
  [`facts/spoilage.md#open`](../../../docs/facts/spoilage.md#open) is
  derived in the doc from this file's two `serverWorldAge` values, not read off a key** — that is
  the correction, and it changes the residual, not the measurement: `summary.c.serverAge`
  (**1.00777**) is what was measured and is unaffected.
