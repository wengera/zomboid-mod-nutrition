# `x182-20261006-152945` reading guide

**`x182-20261006-152945/translate.json`** — produced by `testing/experiments/x182_translate.py` on HEAD `97454e7` (probe `TKX_TranslateOverride` `ff0e50f`, clean; harness Lua `2f0d3d7`, clean) with the driver itself untracked at the run; it is committed unedited beside the artifact
(84.2 s wall; 40431 bytes, sha256 `998f1d72…d69f4fd1`, byte-for-byte identical to the run copy). **Plan 7 Task 4, gate X5**: one boot of the default fixture, one admin character, build 42.20.4, profile `x18-translate` (PZTestKit, TKX_TranslateOverride). `doctor_clean` true; `server_error_count` 0; `client_lua_error` false; both `verify` rows `ok` (the client `IGUI_TKX_Probe` hit). HEAD moved to `97454e7` (Task 3's view kernel, under `mod/`, which this profile does not load) between the two sessions.

How to read it. `predictions` is written before the boot, with its basis (the jar's fill order); `vanilla` holds the install's own EN values for the two redefined keys, read by the driver. `verdicts.<leg>` holds each leg's prediction, falsifier, observation and verdict: `P`, `K` and `N` `as_predicted`, `S` **falsified**, with `verdicts.S.LOUD` naming why. `phases.<leg>` holds every reply with its wall bracket, and `steps` every bus call. `positive_control_hit` is true, so every other reading in the file is readable.

- **P**: client `text.get IGUI_TKX_Probe` `tkx-hit`, miss false (and again at `Z`); server the key itself, miss true.
- **K**: client `text.get IGUI_invpanel_Type` `TKX Type`, miss false, against vanilla's `Item`.
- **N**: no apple on either side before the spawn; the client `item.spawn` (`id=1883396734`) read `getDisplayName` `TKX Apple`, `getFullType` `Base.Apple`; the server did not see it; after RCON `additem` the server resolved its own apple (#1725605724) at the first try and read `getDisplayName` `Apple`, `getFullType` `Base.Apple`. The client's final read resolved the client-local apple again, not the replica of the server's.
- **S**: server `text.get IGUI_invpanel_Type` `Item`, miss false — the server control's prediction (a miss, and a display name equal to the full type) is falsified: the server resolves vanilla's strings and not the mod's.
- **L**: client `getText IGUI_TKX_Probe` `tkx-hit`, `getText IGUI_invpanel_Type` `TKX Type`, `getItemNameFromFullType Base.Apple` `TKX Apple`; server `IGUI_TKX_Probe` (the key), `Item`, `Apple`; every call `{ok true, nargs 1, r1 <string>}`.
- **boot**: server launch to `SERVER STARTED` 15.0 s, the client `in_game` 35.3 s and `ready` 37.3 s after its start, session ready at driver wall 54.049.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one admin character, one language (EN), one item and two interface keys. |
| `predictions`, `constants`, `verdicts.*.predicted` | the driver's tables | Written before the run; not readings. |
| `vanilla` | `Item`, `Apple` | Read by the driver from the install's files at import, not from the game. |
| `logs.server`, `logs.client` | 72 and 67 lines | Every line the driver's broad pattern matched (under its cap of 80, `logs.limits.log`), so not a count of anything the pattern names; past the mod lines they are the harness mod's own `AdvancedAnimator` missing-folder exceptions and one vanilla `Translation: Warning` line. |
