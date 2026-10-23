# `x183b-20261006-175149` reading guide

**`x183b-20261006-175149/interface.json`** — produced by `testing/experiments/x183_interface.py`, committed at `cc30694` and run again unedited, on HEAD `1f00efe` (mod `1f00efe`, clean: the close fix wave's client files — the tab's clip and wheel scroll, the tooltip band above the box at the screen edge and under `anchorBottomLeft`, `instantiate` before `RegisterWindow`, the `VisibilityMode` default 2 of ruling T13-1, the self-report's route; harness Lua `2f0d3d7`, clean; probe `TKX_DeclaredFood` `7ec0569`)
(294.5 s wall; 293692 bytes, sha256 `d8a8bf36…167e8bc39`, byte-for-byte identical to the run copy). **Plan 7 Task 13b, the third boot of the interface acceptance, on the close-wave build**: one boot of the default fixture, one admin character, build 42.20.4, profile `x18-interface` as `x183-20261006-163238` (`NR.VisibilityMode` 1 set by the profile, so the Bands default of ruling T13-1 is **not** exercised: the view reads 1 until the gate flips). `doctor_clean` true; `mod_dirty` false; `server_error_count` 0; `client_lua_error` false; all four `verify` rows `ok`. The driver names its run folder with the fixed prefix `x183`, so the file's `run_id` reads `x183-20261006-175149`; the committed folder carries the `x183b` id, and the run folder under `testing/runs/` keeps the driver's name.

How to read it. The shape is `x183-20261006-163238`'s. Every arm is `as_predicted` except `I`, **falsified** by its own pattern as on both earlier boots; `C` is `as_predicted` here where the first boot's was falsified. The primary reading is the load: no server error, no client Lua error, every surface's error counter 0 at all seven checks.

- **S0**: as the first boot — view level 1, `received` 2, option accessors 39, true, true, route `own`, `modOptions` loads 1 and failures 0, server `visibilityMode` 1. The client's self-report at `logs.client[91]` reads `frameworks=own` (the first boot's read `frameworks=none`).
- **A**: `nut_vitC_p` 0.9999668312490085, `nut_vitC_x` 0, `nut_vitC_g` 1.
- **B**: `restoredVisible` false; toggle 1 `r1` true, opens 1, requests 1, the client's count 2 to 3 within the poll; renders 390 then 600 over 3.506 s; toggle 2 `r1` false, closes 1; renders 870 and 870 over 3.512 s.
- **C**: `trait.local NUTRITIONIST add` `after` true, `listAfter` `nutritionist`; the request at wall 134.536, the level 3 at the first poll, 135.043; `hasTrait` true; rebuilds 3 to 4, `received` 3 to 4. The gate flipped on the own route this time.
- **D**: at level 3 (the gate having flipped), `Base.Apple` `r1` 24, `r2` `table`; `TKX.DeclaredBar` `r1` 10, `r2` `declared`; tooltip `draws` 0, because no hover is synthesised (the band above or below the box stays unmeasured).
- **E**: tab `added` 1, errors 0, renders 0 (never activated: the tab's clip and scroll are not exercised).
- **F**: probe before 0, on the UI manager; `setpath` 0.9938916125321331 to 0.05; the record's `vitC.g` `4` after the wait; pushes 1 to 2 at 5.038 s after the write; `received` 4 to 5; classes deficiency 3; probe `r1` 3, `r2` true, `r3` `own`; column x 1184, y 240, 40 by 264; renders 8419 then 8629 over 3.513 s.
- **H** and **boot**: server 10.003483800328473, 10.052752065293122, 10.002488181139586 (201, 202 and 201 ticks) and client 60.022989654655404, 60.01699065513967, 60.0199900049975 ticks per second; server launch to `SERVER STARTED` 15.0 s, the client `in_game` 34.7 s and `ready` 37.3 s after its start.
- **G**: quit rc 0 at 284.828, exit 286.872; `layout.ini` written after the client start (mtime epoch 1791323794750) with the same `NutritionRevamp.panel` and `charinfowindow` lines as both earlier boots; `ModOptions.ini` 0 bytes, 0 lines.
- **I** (falsified by its own pattern): the same 8 lines, six vanilla `ISUI` warnings and two `PZTK: cmd` echoes of the driver's own probes; no line from the mod.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character, one viewport (1280 by 720). |
| `run_id` | `x183-20261006-175149` | The driver's fixed run-folder prefix, not this run's id; cite the folder name `x183b-20261006-175149`. |
| `predictions`, `constants`, `baseline`, `deviations`, `verdicts.*.predicted` | the driver's tables | Written or copied before the run (the first boot's); the tick baseline's own file is `x172b-20261006-130714/itempass.json`, the band's `x181-20261006-152607/moodleframework.json`. |
| `verdicts.I.verdict` | falsified | The pattern caught the harness's echoes of the driver's own probes; cite `logs.server_ui` and `logs.server_ui_mod`. |
| `logs.server` | 120 lines | The first 120 matching lines the driver kept (its cap, `logs.limits.log`), not a count. |
| the length of `logs.client` | 120 lines | Also the cap, not a count; a single line of it (the self-report at index 91) is citable, so the key itself is not on the do-not-cite list for this run. |
