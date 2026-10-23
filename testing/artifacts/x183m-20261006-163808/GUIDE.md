# `x183m-20261006-163808` reading guide

**`x183m-20261006-163808/interface.json`** — produced by `testing/experiments/x183_interface.py --mf` (the driver of `x183-20261006-163238`, run unedited and committed at `cc30694` after both boots) on HEAD `dd9d1ef` (mod `dd9d1ef`, clean; harness Lua `2f0d3d7`, clean; probe `TKX_DeclaredFood` `7ec0569`) with the driver untracked at the run; it is committed unedited beside the artifact
(298.7 s wall; 292640 bytes, sha256 `e86c7b2e…3765f708f`, byte-for-byte identical to the run copy). **Plan 7 Task 11, the interface acceptance, MoodleFramework route**: one boot of the default fixture, one admin character, build 42.20.4, profile `x18-interface-mf` (PZTestKit, MoodleFramework by `workshop_id` 3396446795, NutritionRevamp by path, TKX_DeclaredFood; `Nutrition` false, `DayLength` 1, `NR.VisibilityMode` 1). `doctor_clean` true; `mod_dirty` false; `server_error_count` 0; `client_lua_error` false; all four `verify` rows `ok`.

How to read it. The shape is `x183-20261006-163238`'s. Every arm is `as_predicted` except `I`, **falsified** by its own pattern as on the first boot. `phases.F.before.handle` and `phases.F.after.handle` hold the framework moodle's own Lua fields; `phases.F.after_r1`, `phases.F.after_r2` and `phases.F.column_renders_delta` read 0 because this route builds no column.

- **S0**: view level 1, `received` 2, option accessors 39, true, true, route `framework`, `moodles.stats` created 6, got 6; `modOptions` loads 1 and failures 0; server `visibilityMode` 1.
- **A**: `nut_vitC_p` 0.9999719987172964, `nut_vitC_x` 0, `nut_vitC_g` 1.
- **B**: `restoredVisible` false; toggle 1 `r1` true, opens 1, requests 1, the client's count 2 to 3 within the poll; renders 390 then 600 over 3.506 s; toggle 2 `r1` false, closes 1; renders 900 and 900 over 3.503 s.
- **C**: the request at wall 135.998, the level 3 at the first poll, 136.502; `hasTrait` true; rebuilds 3 to 4.
- **D**: at level 3, `Base.Apple` `r1` 24, `r2` `table`; `TKX.DeclaredBar` `r1` 10, `r2` `declared`; tooltip `draws` 0, because no hover is synthesised.
- **E**: tab `added` 1, errors 0, renders 0 (never activated).
- **F**: probe before `r1` 0, `r2` false; `setpath` 0.993896102380699 to 0.05; the record's `vitC.g` `4` after the wait; pushes 1 to 2 at 4.279 s after the write; `received` 4 to 5; classes deficiency 3; probe `r1` 3, `r2` true, `r3` `framework`; the handle at x 1238, y 162, 32 by 32, `addedToUIManager` true (y 120 before the write); `handle.value` unresolved.
- **H** and **boot**: server 10.05325237644951, 10.002985965959988, 10.051251430561775 and client 60.022989654655404, 60.01399160503698, 60.0199900049975 ticks per second; server launch to `SERVER STARTED` 15.6 s, the client `in_game` 36.8 s and `ready` 38.8 s after its start.
- **G**: quit rc 0; `layout.ini` written after the client start with the same `NutritionRevamp.panel` and `charinfowindow` lines as the first boot; `ModOptions.ini` 0 bytes, 0 lines.
- **I** (falsified by its own pattern): the same 8 lines, six vanilla `ISUI` warnings and two `PZTK: cmd` echoes of the driver's own probes; no line from the mod.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character, one viewport (1280 by 720), one framework moodle read. |
| `predictions`, `constants`, `baseline`, `deviations`, `verdicts.*.predicted` | the driver's tables | Written or copied before the run. |
| `verdicts.I.verdict` | falsified | The pattern caught the harness's echoes of the driver's own probes; cite `logs.server_ui` and `logs.server_ui_mod`. |
| `logs.server`, `logs.client` | 120 lines each | The first 120 matching lines the driver kept (its cap), not counts. |
| `phases.F.column_renders_delta`, `phases.F.after_r1`, `phases.F.after_r2` | 0 | The framework route builds no own column; not a stopped draw. |
| `phases.F.after.handle.value`, `phases.F.before.handle.value` | unresolved | Not the framework's value field; the probe's level is the reading. |
