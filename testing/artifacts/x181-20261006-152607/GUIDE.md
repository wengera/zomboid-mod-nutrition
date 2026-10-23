# `x181-20261006-152607` reading guide

**`x181-20261006-152607/moodleframework.json`** — produced by `testing/experiments/x181_moodleframework.py` on HEAD `9de2bc6` (probe `TKX_MF` `9de2bc6`, clean; harness Lua `2f0d3d7`, clean) with the driver itself untracked at the run; it is committed unedited beside the artifact
(197.7 s wall; 123323 bytes, sha256 `a285ba5b…94b69019`, byte-for-byte identical to the run copy). **Plan 7 Task 4, gate X29**: one boot of the default fixture, one admin character, build 42.20.4, profile `x18-moodleframework` (PZTestKit, MoodleFramework by `workshop_id` 3396446795, TKX_MF). `doctor_clean` true; `server_error_count` 0; `client_lua_error` false; both `verify` rows `ok` (`TKX_MF.detected` true). The MoodleFramework tree was re-read and dated before the boot (`mf_tree`, and the driver's docstring): `42.20/` ships `MF_ISMoodle.lua` only, `common/` the configuration file and a `mod.info` dated 2026-09-07.

How to read it. `predictions` is written before the boot; `verdicts.<leg>` holds each leg's prediction, falsifier, observation and verdict (`as_predicted` for all nine). `phases.<leg>` holds every reply with its wall bracket, and `steps` every bus call. A `lua.global` read is kept whole: `resolved`, `type`, and `value` or `keyCount` or `failedAt`. The three value legs (`iii_control`, `iii_render`, `iii_backoff`) each hold the `moddata.set` reply, a `state` read 3 s after the write (`level`, `gbn`, `onUI`, `lastSet`), the moodle instance's own fields (`moodle_fields`), two render-count reads (`read1`, `read2`) about 4 s apart, and the deltas with their windows. `renders` counts calls of the framework moodle's `render` through the probe's wrap of that instance's field (`iii_pre.wrapped` true); `ownRenders` counts the probe's own widget's `render`.

- **F**: `detected`, `created`, `moodleFound` and `ownOnUI` true, `errors` 0; `TKX_MF.moodle` a table of 58 keys.
- **i**: the server log one `loading MoodleFramework` line, the client console two; client `MF` a table of 27 keys, `MF.createMoodle` and `MF.getMoodle` functions; server `MF` and `MF.createMoodle` `failedAt` `MF`.
- **ii**: client `MF.key` `MoodleFramework`, `TKX_MF.cfgKey` the same, `MF.hasBorder`, `MF.hasBackground`, `MF.hasBGColor` and `MF.overrideGray` functions; server `MF.key` `failedAt` `MF`. Both kept logs carry `mod "MoodleFramework" overrides media/lua/client/mf_ismoodle.lua`.
- **iii_control** (0.5): level 0, gbn 0, `onUI` unresolved (the field never set), renders 0 and 0 over 4.011 s; ownRenders 2239 then 2479.
- **iii_render** (0.95): level 4, gbn 1, `onUI` true, `moodle_fields.addedToUIManager` true; renders 569 then 809 over 4.02 s; ownRenders 3169 then 3409. The moodle sat at x 1238, y 120, 32 by 32 in all three legs.
- **iii_backoff** (0.5 again): level 0, gbn 0, `onUI` false; renders 930 and 930 over 4.014 s; ownRenders 4099 then 4339.
- **X**: `MoodlesUI` a table of 3 keys, `MoodlesUI.getInstance` a function, `TKX_MF.moodlesUI` true; the stack box x 1238, y 424, w 32, h 720 at first sight and again here.
- **L**: `lua.call getTimestampMs` `{ok true, nargs 0, r1 <ms>}` on both sides; `lua.call MF.getMoodle TKX 0` `{ok true, nargs 2, r1_keys 58}`; `lua.call MoodlesUI.getInstance` `{ok true, nargs 0, r1_type userdata}`; a missing target `{ok false, failedAt noSuchFn}`; client `lua.setpath TKX_MF.setpathSmoke 7` `{ok true, before "nil", after "7"}`, read back as the number 7.
- **T** and **boot**: one 20 s window, server 10.001990445859873 and client 60.03199040287914 ticks per second; server launch to `SERVER STARTED` 40.3 s, the client `in_game` 36.8 s and `ready` 39.3 s after its start, session ready at driver wall 81.503.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character, one framework moodle with no icon of its own. |
| `predictions`, `constants`, `mf_tree`, `baseline`, `verdicts.*.predicted` | the driver's tables | Written or copied before the run; the tick baseline's own file is `x161b-20261006-065751/body.json`. |
| `logs.server`, `logs.client` | 80 lines each | The first 80 matching lines the driver kept (its cap, `logs.limits.log`), not counts; past the mod lines they are the harness mod's own `AdvancedAnimator` missing-folder exceptions. |
| `phases.iii_control.state.onUI` | unresolved | The flag is never set before the first non-neutral value; read `moodle_fields.addedToUIManager` beside it, also unresolved, as the absence. |
| `verdicts.i.line_counts_exact` | true | A grade of the driver's, not a reading; cite `logs.server_load` and `logs.client_load`. |
