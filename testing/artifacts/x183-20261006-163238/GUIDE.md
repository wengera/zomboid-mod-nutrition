# `x183-20261006-163238` reading guide

**`x183-20261006-163238/interface.json`** — produced by `testing/experiments/x183_interface.py` on HEAD `dd9d1ef` (mod `dd9d1ef`, clean; harness Lua `2f0d3d7`, clean; probe `TKX_DeclaredFood` `7ec0569`) with the driver itself untracked at the run; it is committed unedited beside the artifact
(299.5 s wall; 295822 bytes, sha256 `23da87dc…85205084`, byte-for-byte identical to the run copy). **Plan 7 Task 11, the interface acceptance, own moodle route**: one boot of the default fixture, one admin character, build 42.20.4, profile `x18-interface` (PZTestKit, NutritionRevamp by path, TKX_DeclaredFood; `Nutrition` false, `DayLength` 1, `NR.VisibilityMode` 1). `doctor_clean` true; `mod_dirty` false; `server_error_count` 0; `client_lua_error` false; all four `verify` rows `ok`. The same driver ran unedited for `x183m-20261006-163808` with `--mf`.

How to read it. `predictions` is written before the boot, both routes' in one table; `verdicts.<arm>` holds each arm's prediction, falsifier, observation and verdict: `S0`, `A`, `B`, `D`, `E`, `F`, `H` and `G` `as_predicted`, `C` and `I` **falsified** (below). `phases.<arm>` holds every reply with its wall bracket, and `steps` every bus call; a `lua.global` read is kept whole (`resolved`, `type`, and `value` or `keyCount` or `failedAt`), a `lua.call` reply whole (`ok`, `nargs`, `r1`–`r3`). `phases.<arm>.stats` and `phases.S0.stats`/`phases.Z.stats` are the mod's own stats tables per surface. `mod_error_checks` holds the error counters read at each arm's check (all 0).

- **S0**: view level 1, `received` 2, option accessors 39, true, true, route `own`, `modOptions` loads 1 and failures 0, server `visibilityMode` 1; the client's sentinels resolved and the server's reads of client names `failedAt` (no client file on the server).
- **A**: `nut_vitC_p` 0.9999659982752191, `nut_vitC_x` 0, `nut_vitC_g` 1.
- **B**: `restoredVisible` false; toggle 1 `r1` true, opens 1, requests 1, the client's count 2 to 3 within the poll; renders 390 then 600 over 3.508 s; toggle 2 `r1` false, closes 1; renders 900 and 900 over 3.256 s.
- **C** (falsified): `trait.local NUTRITIONIST add` `after` true, `listAfter` `nutritionist`; the request's mirror arrived (`received` 3 to 4, rebuilds 3 to 4) but `hasTrait` read false and the level 1 at all four polls; the list was read right after the add (`listAfter`) and not re-read at or after the mirror's arrival, and `view.hasTrait` is the value cached at that arrival.
- **D**: at level 1, `Base.Apple` `r1` 1, `r2` `table`; `TKX.DeclaredBar` `r1` 1, `r2` `declared`; tooltip `draws` 0, because no hover is synthesised (not an absence of the band).
- **E**: tab `added` 1, errors 0, renders 0 (the tab was never activated, not a failed render).
- **F**: probe before 0, on the UI manager (the column is on it from its build); `setpath` 0.9936936148354479 to 0.05; the record's `vitC.g` `4` after the wait; pushes 1 to 2 at 4.293 s after the write; `received` 4 to 5; classes deficiency 3; probe `r1` 3, `r2` true, `r3` `own`; column x 1184, y 240, 40 by 264; renders 8629 then 8839 over 3.511 s.
- **H** and **boot**: server 10.051251430561775, 10.054753608760578, 10.05325237644951 and client 60.01699065513967, 60.022989654655404, 60.022989654655404 ticks per second; server launch to `SERVER STARTED` 15.1 s, the client `in_game` 35.2 s and `ready` 37.8 s after its start.
- **G**: quit rc 0; `layout.ini` written after the client start with `NutritionRevamp.panel x=60 y=200 width=280 height=121 visible=false pin=true` and `charinfowindow ... tabs=info,skills,health,clothingIns,protection,NutritionRevamp current=info`; `ModOptions.ini` 0 bytes, 0 lines.
- **I** (falsified by its own pattern): `logs.server_ui` 8 lines, six vanilla `ISUI` warnings and, in `logs.server_ui_mod`, two `PZTK: cmd` echoes of the driver's own server-side `lua.global` probes of `NR_ClientTooltip_Installed` and `NR_Client_Panel`; no line from the mod.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character, one viewport (1280 by 720). |
| `predictions`, `constants`, `baseline`, `deviations`, `verdicts.*.predicted` | the driver's tables | Written or copied before the run; the tick baseline's own file is `x172b-20261006-130714/itempass.json`, the band's `x181-20261006-152607/moodleframework.json`. |
| `verdicts.I.verdict` | falsified | The pattern caught the harness's echoes of the driver's own probes; cite `logs.server_ui` and `logs.server_ui_mod` for the lines. |
| `logs.server`, `logs.client` | 120 lines each | The first 120 matching lines the driver kept (its cap, `logs.limits.log`), not counts. |
