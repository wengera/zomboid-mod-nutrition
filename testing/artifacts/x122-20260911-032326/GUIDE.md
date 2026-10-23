# `x122-20260911-032326` reading guide

**`x122-20260911-032326/platform-loader.json`** — produced by
`testing/experiments/x122_loader.py` at commit `73e1fd6` (75.6 s wall, no `error` key,
`server_error_count 0`, `client_lua_error false`; 46 035 bytes, sha256 `628ace2e…2149adb`,
byte-for-byte identical to the run copy). Slice 12's session 2: the `common/`-vs-version-dir merge
rule re-run on a subject **we** control, plus the arm KEEP 10's bound used to exclude. **Skew-free**
— driver and artifact in one commit on harness Lua at `5d9633f`, clean, with `doctor_clean true`
and `acceptance_run run-20260911-031417` in the file. The log readings replicate across both boots
(this session and the acceptance run).

- **Provenance — the profile.** `testing/profiles/x12-loader.toml`: `fixture = "default"`,
  `Mods=PZTestKit;TKX_LoaderVersion;TKX_CommonOnly`, **no `[sandbox]`**, one tier-(a) `[[verify]]`
  row — client `lua.global TKX_LoaderVersionTree`, a file with **no `common/` counterpart**, so it
  loads under either merge direction, which is what makes it a gate and not a discriminator.
  `TKX_CommonOnly` is deliberately ungated: whether a version dir with no `media/` still lets
  `common/` load is the measurement.
- **Provenance — the mods.** `tkx-loader-probe` (mod D: a `42.20/` and a `common/`, each with its
  own `mod.info` declaring a **different** id, and the same relative path
  `media/lua/shared/TKX_Loader_Which.lua` in both trees) and `TKX_CommonOnly` (mod E: a `42.20/`
  holding **only** a `mod.info`, the whole payload under `common/`). Both are `path =` mods from
  `testing/experiments/` at commit `f36a860`.
- **The two independent halves.** `summary.L2_which` (`version` on both sides) is the *resulting
  Lua state*; `summary.L2_trees` (the `common/`-only and version-only markers **both** resolving)
  says `common/` still ran. `phases.L2.reading.overrides_tails` is the *loader's own map*: one
  `mod "<id>" overrides <relpath>` line per shadowed file **per Lua state** — server 1, client 2 —
  with the tail a lower-cased relative path.
- **The new arm is `phases.L3.reading`.** `loading TKX_CommonOnly` printed (server 96, client
  86/166), the `common/media` payload global resolved on both sides and no `required mod … not
  found` appeared. KEEP 10's bound therefore now reads "a version dir that ships colliding files,
  **or none at all**". The arm still untested is a version dir that ships `media/` colliding with
  *nothing*.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session** (two boots of the same profile), one build, one purpose-built mod pair. What is at n = 2 is the *merge direction*, and only because `td3-20260911-001948` measured it on a workshop mod first. |
| `phases.L1` / `verdicts.L1`, as evidence about **id resolution** | `trivial`; `loading TKX_LoaderVersion` server 1 / client 2, `loading_common` 0 | **Degenerate by construction.** `Mods=` named `TKX_LoaderVersion` *and* the installed folder was named `TKX_LoaderVersion`, so the announce cannot separate "resolved through the version dir's `mod.info`" from "matched the folder name". `x123-20260911-034426` / `x123b-20260911-034500` are the boots that separate them. |
| "`TKX_LoaderCommon` was registered into `modIdToDir`" | `summary.L1_loading.common_id_mentions` `{server: 0, client: 0}` | **Unobserved, not confirmed — in either direction.** Zero mentions of the `common/` id in either log says the engine never *printed* it. Nothing here reads engine state, so it is neither evidence that the id was registered nor that it was not. The addressability question is `x123b`'s. |
| anything about **folder-name** resolution | — | Not exercised: this mod's folder name equals the version dir's id. `boots.drift` in `x123-20260911-034426` is the folder-drift reading. |
| `server_error_count: 0` / `summary.lua_error_hits`, read as "the log holds no `ERROR` lines" | `0` | It means **0 non-baseline** lines. `testing/pzt/server.py`'s `BASELINE_NOISE` whitelists the media-walk lines, and the raw server log holds **68** lines matching `ERROR`. Quote "no non-baseline server errors". |
| the `common/`-enumerated-first lines, read as the `activeFileMap` pass | the walk lines in `greps.loader_wide` | They are `AdvancedAnimator.loadModMedia`'s **media walk** frames, not the `activeFileMap` pass. The enumeration order of the map pass is a jar read (**C**, [`platform/loader-and-scripts.md#file-map`](../../../docs/platform/loader-and-scripts.md#file-map)), and the same caveat applies to `phases.L3` as to `phases.L2`: the outcome is proven, the mechanism is the jar. |
| `greps.commononly_wide` counts, quoted per mod | substring `tkx_loadercommon` | The pattern also matches **`TKX_LoaderCommonTree`**, the probe's own global, so a count mixes the mod id with the marker. A later driver should use `tkx_loadercommon(?![a-z])`. Two more frozen-driver notes: `TAIL_RX`'s id class excludes digits, so an unparsed `overrides` line vanishes from `tails` silently (reconcile `len(tails)` against `count`), and `media_trees_walked` is a **sorted set** — walk order survives only in the `wide_hits` line numbers. The file holds **one** doctor snapshot, not one per boot. |
