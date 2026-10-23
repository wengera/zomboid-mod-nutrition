# `td3-20260911-001948` reading guide

**`td3-20260911-001948/teardown-autocook.json`** — produced by
`testing/experiments/td3_autocook.py` at commit `3f4b646` (179.4 s wall, no `error` key,
`server_error_count 0`, `client_lua_error false`; 64 170 bytes, sha256 `5401ea22…7d0fd63`,
byte-for-byte identical to the run copy). Slice 11's teardown session, and the **loader** side of
the set: a mod split across `common/` and `42.13/` on a real dedicated server with a real client,
read four independent ways to settle which tree's copy of a colliding file actually executes.
**Skew-free** — driver and artifact in one commit on harness Lua at `d8cc34e`, clean, all five
provenance facts in the file (`commit`, `harness_lua_commit`, `harness_lua_dirty false`,
`doctor_clean true`, `acceptance_run run-20260911-001251`). It is the first artifact carrying
`lua.global` replies.

- **Provenance — the profile.** `testing/profiles/teardown-autocook.toml`: `fixture = "default"`,
  `[[mods]] id = "PZTestKit"` then `[[mods]] id = "AutoCook", workshop_id = "3388721641"`, **no
  `[sandbox]` block**, and **two** tier-(a) `[[verify]]` probes — client `text.get
  UI_AutoCookMode` expecting `"Cooking diet: "`, and client `witness.moddata player:admin *`
  expecting `"AutoCook:table"`. The profile was committed at `7dfd3a6`; its comment block was
  corrected in `d8cc34e` (row 2 proves `common/` ran and the require chain completed — it does
  **not** name the winning copy). Its acceptance run is named in `acceptance_run`:
  **`run-20260911-001251`** (`RESULT: PASS`, 95.3 s, both rows `ok=True`) — that run's
  `report.json` is *not* committed here, and the session re-asked both probes itself, so cite
  `verify[0]` / `verify[1]` from this file and treat the acceptance run id as provenance. Anchor
  note for anyone reproducing the timing: on that run the two rows read green at
  **`session_ready + 0.5 s` and `+ 1.0 s`**, not at `client_ready`, which is ~2.3 s earlier.
- **Provenance — the mod.** Workshop item `3388721641`, folder `AutoCook`, declared id `AutoCook`
  (**no drift**), `mod.info` at `common/mod.info`, live version folder **`42.13/`** of two
  (`42.13`, `42`) beside a `common/` that is the **bigger** tree and a `42/` holding two PNGs and
  nothing else; author `Tchernobill`, `modversion 1.6`, **no `require=`**, no sandbox options,
  **no `media/scripts/` in any tree**; 19 files / 129 161 B, 16 stamped 2026-08-12 00:02 and
  three (the v1.6 update) 2026-09-07 21:54. The workshop tree is read-only to the harness.
- **How to read the merge-rule readings — four of them, and they are not equals.** `M1_overrides`
  is the **loader's map** (5 lines on the server log, tails in `M1_overrides.server_log.tails`);
  `M4_globals.client` is the **resulting Lua state** (both 42.13-only discriminators present),
  and `summary.M4_autocook_keyCount_client` (**49**, against 47 for a common-wins state) is an
  arithmetic cross-check of the same. Those are the two independent halves, and the outcome they
  agree on is graded **M**. `M3_translations` is **non-discriminating** on its own (both JSONs
  exist only in `common/`), and the modData census is **neither direction** — see the *do not
  cite* table. The mechanism behind all of it is **C**, from the jar.
- **`nilcall_lines` is a bounded negative — and the bound is WIDER than one line.** Zero
  `tried to call nil|HasTrait|getTypeString` on either side proves that the whole
  **window-build** path did not execute the `common/` copies: `ISCharacterCook:createChildren`
  calls `AutoCook.init` at `:17` and `createCookingModeCombo` **unconditionally** at `:23`, which
  between them reach `common/…/AutoCook.lua:39` (from `AutoCook:init`),
  `common/…/AutoCook_AutoCraftRecipes.lua:39` (inside `initAutoCraftRecipes` `:3-54`, from
  `AutoCook:init:53`) and `common/…/ISCharacterCook.lua:221` (inside `createCookingModeCombo`
  `:199-235`). It is load-bearing because the line before the first of them
  (`common/…/AutoCook.lua:38`, the modData write) demonstrably did execute on this fresh
  character, and `snapshots[0].client.census_player` times that path at `session_ready + 1.044 s`.
  **None of the four calls sits at file scope**, so "dying at file load" is the wrong model — the
  raise would land when the character-info window is built, inside `createPlayerData` at spawn.
  What it still says nothing about is `common/…/ISCharacterCook.lua:50`, which sits inside
  `prerender` and is unreachable without opening the Cook tab; nothing on the bus opens it.
- **The carrier probe is a PASS-1/PASS-2 follow-up, not an AutoCook finding.** `carrier` pins a
  vanilla `Base.Steak` at `heat 1.2` — **below** `Food.update`'s 1.6 cooking gate — and reads both
  sides twice. Cite it against
  [`platform/mp-model.md#what-a-client-copy-is`](../../../docs/platform/mp-model.md#what-a-client-copy-is)
  and
  [`platform/mp-model.md#open`](../../../docs/platform/mp-model.md#open),
  never against AutoCook, which owns no item and reads no item field on the bus.
- **The transmit is corroboration with one new consequence.** `transmit_reading` reproduces pass
  2's wipe-and-replace with a second subject (`server_census_equals_client true`) — but this
  session planted **no server-only key**, so it does **not** re-measure the *wipe* half; that
  stays pass 2's reading. What is new is subject-specific: a mod with **0** `transmitModData` had
  its whole nested table pushed to the server by somebody else's transmit.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1`.** One session, build 42.20.4, fixture `default`, one mod, one character, one machine. Every one of P1–P9 landed on its predicted branch, so no falsifier was approached: the merge rule is validated as *consistent* with the wiki's, not stress-tested. And it is bounded to a mod whose `getVersionDir()` resolves to a tree that **ships colliding files** — a version dir that is absent, empty, or ships only files `common/` lacks is untested here. |
| `snapshots[].client.census_player`, as a merge-**direction** reading | `AutoCook:table` present at `session_ready + 1.044 s` | **It names neither direction.** The key proves `common/` ran and the require chain completed (`addCharacterPageTab` is defined only in `common/…/ISCharacterInfoWindow_AddTab.lua:2`), but the `common/` copy of `AutoCook.lua` writes the same key at the same line (`:38`), one line *before* its B41-era `HasTrait` call at `:39` — so a green row is consistent with either copy having won. Only `M4_globals` separates them. |
| `M3_translations`, as a merge-direction reading | `"Cooking diet: "`, `miss false` | Non-discriminating: both translation JSONs exist **only** in `common/`, so no collision is being resolved. What it *does* measure is that the `Translator` **merges** — the two vanilla controls (`ContextMenu_Destroy`, `UI_Yes`) still answer their vanilla text although the mod ships same-named files at the same relative paths. |
| the three weight-direction flags in `snapshots[].{client,server}.nutrition`, as an answer about `AutoCook:allowSpice`'s gate | all `false`, agreeing on both sides at all four snapshots | **Agreement under the trivial arm.** The character sat in `Nutrition.updateWeight`'s **none** arm all session: weight 80 ⇒ gain threshold 1000, loss threshold 0, calories 798.45 → 782.90, strictly between them. Both sides answer `false` in that arm whether or not the client recomputes anything. The gate at `42.13/…/AutoCook.lua:216,219` is **unsettled**; settling it needs a session driving calories outside `[0, 1000]` (slice-12 item). |
| `carrier.window_s` | `10.0` | The **requested** sleep, not the measured window. The reads' own wall stamps give **12.54 s** (client 154.154 → 166.695). Quote the stamps. |
| `carrier.gate`, quoted as the gate's **comparison** | "… gated at heat **>= 1.6**; this probe pins heat at 1.2, BELOW it." | The `>=` is the **driver's** wording, not the jar's. `Food.update @63-@71 L373` is `ldc_w 1.600000023841858; fcmpl; ifle`, so a heat of **exactly** 1.6 does **not** enter the branch: the gate is **strict**, `heat > 1.6f`, which is what every doc in the library quotes. The artifact string and the driver docstring that produced it (`testing/experiments/td3_autocook.py:540`) are both frozen and both say `>=`. Quote the jar. Nothing measured here turns on it — the pin at 1.2 is below the gate under either reading. |
| the `t+3s` snapshot tag, read as "three seconds after the transmit" | tag `t+3s` | A **nominal** name. That snapshot opened at **transmit + 7.58 s** (the `t0` snapshot took 7.58 s to walk both sides). The server census *inside* `t0` sat at **transmit + 2.04 s** and already showed all seven keys, so the crossing is bounded at ≤ 2.04 s and nothing here measures it more tightly. |
| `phase2[0]`, quoted as "the write had not crossed 1.8 s later" | server `keyCount 4` | The server census **opened 0.51 s after the `moddata.set` ack** (134.918 → 135.427) and closed 1.77 s after it. Quote the bracket, not its far end. |
| `carrier`, as a general statement that client item copies never tick | client frozen, server moved | **One arm, one item, one 12.54 s window, one fixture.** `updateTemperature` runs unconditionally inside `Food.update`, so the reading is "`Food.update` did not advance the client's held copy in this window" — it **refines** the "a client copy can tick" clause rather than confirming it. Frozen and non-cookable items and every other push path are untested. |
| the `getContainer` strings in `carrier.*_read_*` | `…parent:IsoPlayer{ Name:null, ID:5 }` (client) against `ID:1` (server) | **Presence and within-side stability only.** `ItemContainer.toString()` ends in a per-JVM identity hash, so the two sides' strings differ by construction; comparing them across sides reads as a desync and is not one. |
| `M1_overrides.client_console.count` | `10` | Not ten shadowed files — **the same five-line block twice**, once per client Lua state (lines 85–89 and 168–172, each preceded by its own `loading AutoCook` at 84 / 167). The server printed it once. A client-side grep must expect **2 × n**. |
| `moddata_keys` | the three probes joined by a pipe separator for the reader | A **display** string, not a bus token — the probes were sent separately, and `notes[0]` says so. |
| `verify`'s row 2 `missing` | `{}` | The `*` is skipped by the census's own `~= "*"` guard, so it never lands in `missing` and its absence there is **not** a hit. The number worth quoting is `keyCount` (**6**). |
| anything about the cooking pipeline | — | **Nothing on the bus reaches it.** The only entry is a context-menu option whose handler runs on a right-click; no shipped command clicks, presses a key or calls `triggerEvent`. `chooseItem`, `filterFood`, `allowSpice`, `acceptIngredient` and all five diets stay **C** — `M4_globals` read four of the mod's functions and **called none**. |
