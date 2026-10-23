# `x172b-20261006-130714` reading guide

**`x172b-20261006-130714/itempass.json`** — produced by `testing/experiments/x172_itempass.py`, committed at `d8ee8ce` and run again unedited, on HEAD `8da267e` (mod `8da267e` clean, the close fix wave's regenerated files; probes `de10855` (TKX_ItemOverride) and `7ec0569` (TKX_DeclaredFood), harness Lua `d3554be`, clean)
(609.3 s wall; 875069 bytes, sha256 `62e7cb13…3136cc0d`, byte-for-byte identical to the run copy). **Plan 6 Task 12b, the second boot of the item pass, on the close-wave build**: one boot of the default fixture, one admin character, build 42.20.4, profile `x17-itempass` as `x172-20261006-110409`. `doctor_clean` true; `server_error_count` 0; `client_lua_error` false; the four `verify` rows `ok`. The driver names its run folder with the fixed prefix `x172`, so the file's `run_id` reads `x172-20261006-130714`; the committed folder carries the `x172b` id the plan gave this run, and the run folder under `testing/runs/` keeps the driver's name.

How to read it. Exactly as `x172-20261006-110409/itempass.json` (the guide above): the same keys, the same arms, the predictions recomputed by the driver from the files at `8da267e`. What differs from that run:

- **The build**: `summaries.A.files` reads `NR_Data_Nutrients.lua` 318196 B, `NR_Data_Infer.lua` 16801 B and `NR_ItemPass_Food.txt` 90124 B (the fix wave's regenerated files). None of the eleven arm-`B` foods, the Apple, the Orange or the Bread is among the twenty script blocks the wave changed; the one inference change is the `_default` choline density (0.0672518 to 0.0687147 per kcal), so arm `D`'s choline is 17.178675000000002 here against 16.81295 there, each equal to its own build's prediction.
- **What repeats exactly**: `items.count` (total 5096, food 726, Base 722, TKX 4); the six getters of all thirteen arm-`B` foods on all three reads; `NR_Nutrients` missing on every arm-`B` read and the eaten Apple; arm `I`; the `S0` loader replies; the `lastIntake` sources (baseline, baseline, inferred, declared, fluid); the declared string on both sides; `getFoodType` nil on `TKX.FibreBar`; arm `C`'s and `C2`'s `measured` values key for key; no checksum line.
- **What is timing, not the build**: the boot (server launch to `SERVER STARTED` 15.8 s, client `in_game` 38.8 s and `ready` 41.4 s, session ready at driver wall 59.084), the three tick windows (10.052752065293122, 10.050751318539158, 10.053752737407924), every `s` (arm `C`'s first read 0.9957546115917206, not 1: a slow minute fell between the landing and the read; arm `C2`'s first read exactly 1.0) and so every raw `buffer` value, the `worst_rel` values (all under 6e-16), the last digit of some `measured` values in arms `D`, `E` and `F_coffee` (float noise in buffer / s), the coffee's 31 sips and 35 landings (32 and 36 there) over the same 0.25 L, and the close counters (intake 4 eats, 35 landings, 0 failures; nutrients 857 minutes, 0 errors; kinetics 860 minutes, 0 failures).
- **F_cola**: **unmeasured** again — `fluid.fill` replied `no FluidType for Cola`; the driver was not edited to change it.
- **Logs**: the 80 kept lines on each side are the same lines as that run's up to their numbers; the server stdout holds as many `ERROR` (72) and `Exception` (90) lines as that run's and no `InvalidParameterException`; this run's client console carries no `pzt-cmd.txt` in-use collision.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot of this build; with `x172-20261006-110409`, two boots of two builds, one fixture, one admin character. |
| `run_id` | `x172-20261006-130714` | The driver's fixed prefix; this run's id is `x172b-20261006-130714`. |
| `predictions`, `baseline`, `constants` | the driver's tables | Computed or copied before the run; the tick baseline's own file is `x161b-20261006-065751/body.json`. |
| `summaries.*.pred_buffer`, `summaries.*.pred_ingested`, `summaries.*.grade*.rows.*.pred`, `summaries.B.*.*.rows.*.pred` | the driver's recomputations | Predictions recomputed after the run from live inputs; cite `measured` or the buffer. |
| `summaries.F_cola` | `ok` false | The arm took no reading (`fluid.fill` failed); not a falsification. |
| `summaries.A.ok`, `summaries.B.ok`, `summaries.G.ok`, `summaries.I.ok` | null | Those summaries carry their verdicts under other keys (`base_ok`, `total_ok`, per-type `ok`). |
| `logs.server`, `logs.client` | 80 lines each | The first 80 matching lines the driver kept (its cap, `logs.limits.log`), not counts. |
| `logs.client_checksum` | [] | The client's console log never carries the checksum kick's reason string, so an empty list is not an absence reading. |
