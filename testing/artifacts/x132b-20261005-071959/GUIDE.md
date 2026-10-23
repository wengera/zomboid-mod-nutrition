# `x132b-20261005-071959` reading guide

**`x132b-20261005-071959/coboot.json`** — produced by `testing/experiments/x132_coboot_b.py` at commit `a02e8d9`
(245.5 s wall; 119 772 bytes, sha256 `38d4d7ae…5b1cc5c3`, byte-for-byte identical to the run copy). **A second
co-boot, one boot of `x13-coboot`**: the first driver verbatim but for one boot and three more markers,
`QualityCooking.Server.EventHandlers.Roll`, `...BuffTicker` and `...Roll.ApplyBuff`, because the first run's
`QualityCooking.Server` is made by QualityCooking's **shared** init and so did not show its eat-wrapping
server file ran. Same provenance as `x132b-20261005-071013`; four `verify` rows `ok`, `server_error_count` 0.

How to read it. As `x132b-20261005-071013`'s boot A. **`verdicts.QC-wrap-file`**: `Roll` and `BuffTicker` tables and
`Roll.ApplyBuff` a function on both sides — `CookingRollHandler.lua` ran, and with it its unconditional
save-and-replace of `ISEatFoodAction.complete`. **`verdicts.X45b-A.observed`**: +95.30 kcal post, +95.26
late; `enter`/`exit` +1; `eats`/`landed` +1, share 1.0; every value finite; `.outermost` true again; no
buff. The console carries the same QuestSystem client error and the same baseline lines.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` eat, one fixture, one admin character. |
| `verdicts.X45a.verdict`, `verdicts.X45b-A.verdict`, `summary.verdicts` | `falsified` | As in `x132b-20261005-071013`: the baseline exception lines, and `.outermost` alone. |
| `boots.A.phases.eat.intake.bulk_delta` | 4.253 | A raw delta, not decay-corrected. |
