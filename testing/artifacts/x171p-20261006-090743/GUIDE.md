# `x171p-20261006-090743` reading guide

**`x171p-20261006-090743/scripts.json`** — produced by `testing/experiments/x171_scripts.py` on HEAD `598f619` (probes `511f6e4`, harness Lua `d3554be`, clean) with the driver itself untracked at the run; it is committed unedited beside the artifact
(184.4 s wall; 66655 bytes, sha256 `d61eae0a…a202fd3d`, byte-for-byte identical to the run copy). **Plan 6 Task 8, X15**: two boots of the default fixture, one admin character, build 42.20.4; `solo` ran PZTestKit and `TKX_PartialBlock` alone (an implementer addition: in the profile's pair the second block restates `ItemType` after the omitting one and would mask a demotion), `pair` ran the profile `x17-partial` as built. `doctor_clean` true before each boot; `server_error_count` 0 and `client_lua_error` false in both; the pair boot's two `verify` rows `ok`.
A first attempt, `x171p-20261006-090606`, died at a driver TypeError (a `Timeline.mark` keyword clash) after the server started and before any client or reading; its run folder is left as is, its artifact copy was deleted uncommitted, and the driver's only change before this run renamed that keyword.

How to read it. `phases.<boot>` holds every reply with its wall bracket: `A` the server's `items.count` digest, `B` the two `item.script` reads per side (no macro on the script object: the known gap), `pre` the empty inventory checks, `spawns` the RCON `additem` rows with the client poll and the server read-back of the same id, and `C_orange`, `C2_local_orange`, `E_apple` each with `fields_client`/`fields_server` (13 getters, `count_ok_*`), `moddata_client`/`moddata_server`, `grade_*` (the driver's comparison against its predictions, tolerance 1e-3) and `nr_*`. Every two-sided read is client first. The client's copy of a server-spawned item lists a `customName` modData key the server's copy lacks; the client-local spawn lacks it too.

- **A**: `total` 5092 and `foodByModule.Base` 722 in both boots, the baseline's counts.
- **C (merge)**: the Orange read 400 / 16.270000457763672 / 0.30000001192092896 / 1 / -0.11999999731779099 / -0.07999999821186066, `getCategory` Food, on both sides in both boots.
- **D (default modData)**: `fibre:12;vitC:3` alone, `fibre:13;vitC:4` beside the second mod, on both sides.
- **C2**: the client-local Orange matched the server-spawned one; the server read of its id is unresolved by construction.
- **E**: the Apple carried no `NR_Nutrients` on either side and read its vanilla macros.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one admin character, one item. |
| `predictions`, `baseline` | the driver's tables | Written before the run; the baseline's own file is `exp05-20260910-084109/food-scan.json`. |
| `phases.*.logs.server`, `phases.*.logs.client` | up to 60 lines | The first 60 matching lines the driver kept (its cap, `phases.<boot>.logs.limit`), not a count. |
