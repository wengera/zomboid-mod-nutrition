# `x201-20261006-215125` reading guide

**`x201-20261006-215125/release.json`** and **`x201-20261006-215125/MANIFEST.json`** — produced by `testing/experiments/x201_release.py`, written before the boot and committed at `c3265f9` before the run, unedited since, on HEAD `c3265f9` (mod `1a8e207`, clean: the 1.0.0 tree; `tools/release_pack.py` at `3f2607d`; harness Lua `fadf698`, clean)
(133.1 s wall; `release.json` 82121 bytes, sha256 `328e6093…4297f16b`; `MANIFEST.json` 10197 bytes, sha256 `0e0c69e1…28bd52beb`, the staged `release/NutritionRevamp/MANIFEST.json` copied byte-identical by the driver; both byte-for-byte identical to the run copies). **Plan 9 Task 4, live 1**: the build staged by `python tools/release_pack.py stage mod/NutritionRevamp --out release` (0 ERROR, 1 WARN: no `preview.png`), the driver's own layout lint of the staged folder (`lint_errors` empty), one server boot, two clients attached one at a time through `attach_clients` — `admin` with `-debug`, then `bob` without it (`boot.client_debug`) — build 42.20.4, profile `x20-release` (PZTestKit + the staged NutritionRevamp by path; `Nutrition` false; DayLength 1; no `[sandbox.NR]` block; sleep off). `doctor_clean` true; `mod_dirty` false; `server_error_count` 0; `admin_lua_error` false; every `verify` row `ok`.

How to read it. Every verdict is `as_predicted` except `F`, **unmeasured**: the harness's `item.script` reads a script item through its property getters, and its reply for `Base.Acorn` carries no `Calories` key on any side (`phases.F.acorn.*.access` lists the seven getters it found), so the pass's calorie value was not read through that route — the self-reports' `itemPass=true` is the mod's own sentinel read (a fresh instance's `Food.getCalories`). Phases `A`, `B` and `C` are read off the server log and the client consoles after teardown, with the bus's `PZTK: ` echo lines dropped first (`logs.*.*_echo_excluded`, all 0).

- **D**: 65 files staged, 65 under `mod/NutritionRevamp/`, 65 pairs equal, none only in the repository; 65 manifest entries, each equal to its staged file's sha256; the copies the harness placed in `server/`, `clients/admin/` and `clients/bob/` `mods/NutritionRevamp` 65 files each, 65 equal.
- **S0**: both clients ready; the three `verify` rows `ok` (the version `"1.0.0"` on `client` and `client:bob`); the server's player list `admin` and `bob`.
- **E**: `NutritionRevamp.version` `1.0.0` and `NutritionRevamp.build` `42.20.4` on `bob`, `admin` and the server.
- **F**: `NutritionRevamp.itemPassActive` a function on the server; `Base.Acorn`'s `Calories` not in the `item.script` reply on any side (unmeasured); its `HungerChange` -10 on all three, recorded and not graded.
- **Z**: no mod error line; `admin` not parked.
- **A**: one server line, `side=server mode=takeover itemPass=true legacyMirror=on frameworks=n/a hook=true limitations=9 nutritionOn=false log=2`, version `1.0.0`, build `42.20.4`.
- **B**: one line on each console, `side=client mode=takeover itemPass=true frameworks=none log=2` on `bob` and on `admin`.
- **C**: two `Connected new client` lines, `first sight of admin` and `first sight of bob`; `bob` ready 40.8 s after its launch (`admin` 38.3 s); three `checksum` lines on the server (the `Checksum: Warning` log-level line, `scriptChecksum:`, `luaChecksum:`) and three on `bob`'s console (`AntiCheatChecksum` missing from a settings table, `DoLuaChecksum start`, `DoLuaChecksum end`), none matching mismatch, differ, kick, disconnect or fail.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters. |
| `predictions`, `constants`, `deviations`, `world_changes`, `meta.staged_mod`, `meta.staged_manifest`, `meta.staging_command`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `verdicts.F.observed.acorn_calories`, `verdicts.F.verdict` | `null` on each side; unmeasured | The `item.script` reply has no `Calories` key; `null` is an absent key, not a reading of the pass. |
| `verdicts.C.observed.checksum_lines` | 3 and 3 | Counts of every line holding `checksum`, the boot's own prints included; cite `verdicts.C.observed.checksum_bad`. |
