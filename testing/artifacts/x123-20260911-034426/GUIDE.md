# `x123-20260911-034426` reading guide

**`x123-20260911-034426/platform-folder.json`** — produced by
`testing/experiments/x123_folder.py` at commit `ef1f678` (68.4 s wall; 54 862 bytes, sha256
`3e2246a7…a09daa4`, byte-for-byte identical to the run copy). Slice 12's session 3: the folder-drift
counterfactual [`platform/mod-anatomy.md#folder-name`](../../../docs/platform/mod-anatomy.md#folder-name) had recorded as *not run*, plus the
requested-id lookup of [`platform/mod-anatomy.md#id-chain`](../../../docs/platform/mod-anatomy.md#id-chain). **One driver, two boots, one file** — boot (a) is
this run id (`boots.drift`), boot (b) is **`x123b-20260911-034500`** (`boots.common_id`) and has no
folder of its own; `summary.run_ids` names both. **Skew-free** — driver and artifact in one commit
on harness Lua at `5d9633f`, clean (`commit`, `harness_lua_commit`, `harness_lua_dirty false`,
`session_2_run x122-20260911-032326`). **Server only: no client was attached to either boot.**

- **Provenance — the profile.** `testing/profiles/x12-loader.toml` again (session 2's), with the
  driver renaming the installed folder and rewriting the ini's `Mods=` line between boots:
  (a) folder `TKX_DriftedFolder`, `Mods=PZTestKit;TKX_LoaderVersion;TKX_CommonOnly`;
  (b) folder `TKX_DriftedFolder2`, `Mods=PZTestKit;TKX_LoaderCommon;TKX_CommonOnly`
  (`summary.listings`, `summary.ini_mods_lines`). Both listings and both ini lines are in the file.
- **`session.verify` is deliberately not called**, and the file says so in `verify_skipped`: every
  `[[verify]]` row of `x12-loader` is client-side and this session attaches no client, so each row
  would have recorded `no client attached` — neither a pass nor a fail. The bus readings carry the
  equivalent weight on the side that exists (`ping` → `pong` in 1.51 s, `TK.version` 1, 10/10 echo
  checks with no client attached, which is itself a harness fact).
- **The pair is the evidence.** (a) loads under the **version dir's** id although the folder name
  matches neither id — `loading TKX_LoaderVersion` at server log 94, the `overrides` line at 95,
  `TKX_LoaderWhich == "version"`, both tree markers resolved. (b) **fails** under the
  `common/mod.info` id — `required mod "TKX_LoaderCommon" not found` at server log **93**, zero
  `loading` / `overrides` lines, all three probe globals unresolved. Write the operational form:
  *for the requested-id lookup only the version dir's `mod.info` id is addressable; a folder
  carrying both `mod.info` files answers to one id.*
- **Id resolution is a pass that completes before any mod loads** — (b)'s WARN at log 93 precedes
  the first `loading` line, while (a)'s `loading` lines follow `Mods=` order exactly. n = 2 boots.
- **The top-level `server_errors` key is boot (b)'s**, whichever server was current at the last
  save; the file says so in `server_errors_note`. **Per-boot `boots.*` is authoritative.**

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` probe per boot**, one build, the **dedicated-server** path (`Mods=` → `ZomboidFileSystem.loadModAndRequired`), server only. The **client's own mod-list call site** — `ChooseGameInfo.getModDetails` reached from the mod selector — was never exercised and is named as slice 13's check. |
| `verdicts.P17`'s clauses 2 and 3 — the `overrides` line and the media mapping under the requested id | `parts` null; `observed.media_trees_walked.TKX_DriftedFolder2` `[]` | **Never exercised.** The boot failed at the requested-id lookup, so those clauses had nothing to run against. Four P17 clauses are null, not three. |
| the empty `media_trees_walked` for the probe folder, read as "the folder was never scanned" | `[]` | **Entailed, not measured.** Media mapping happens only for mods that load, so an unloaded mod walks no tree by definition. This cannot separate "scanned and rejected" from "never scanned"; corroboration only. |
| "every `mod.info` is registered" / "only one id is registered into `modIdToDir`" | — | **The run measures addressability, not the map.** Nothing here reads engine state. The measured statement is the operational one above; the mechanism (`ChooseGameInfo.readModInfoAux` parsing exactly one file) is **C**, in [`platform/mod-anatomy.md#id-chain`](../../../docs/platform/mod-anatomy.md#id-chain). |
| `subjects`, read as the declared ids | a file census per subject (paths, `commit`, `dirty`) | **It lists files, never ids.** The two declared ids are in `testing/experiments/tkx-loader-probe/common/mod.info` and `.../42.20/mod.info` at commit `f36a860`; cite those beside the reading. Future drivers should record the id per tree. |
| the post-pair `doctor` / tree-clean claims | — | Not in this artifact. Only the pre-run state is recorded. |
| a folder whose **only** `mod.info` is `common/mod.info` | — | **Untested here.** Both boots used a folder carrying **both** files. 4 installed mods have the `common/`-only shape and only AutoCook has booted (`td3-20260911-001948`); the purpose-built probe is slice 13's. |
| `verdicts.P17`'s grading path, as a general instrument | `falsified` | Frozen-driver note: the grading at `x123_folder.py` ~:900 would have written `falsified` even if `a_found` were `None`. It did not fire here (boot (a) found the mod), but the latent defect is worth knowing before the driver is copied. |
