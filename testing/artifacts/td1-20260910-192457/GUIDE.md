# `td1-20260910-192457` reading guide

**`td1-20260910-192457/teardown-longtermpreservation4220.json`** — produced by
`testing/experiments/td1_longtermpreservation4220.py` at commit `e3afaa0` (115.9 s wall, no
`error` key, `server_error_count 0`; 71 165 bytes, sha256
`df8542c17705839ca9af7d57516cd1af034c7472ab8e2f7591755dddf71cb9d5`). Slice 09's first teardown
session: a **mod** on a real dedicated server with a real client, reading the same inventory item
on both sides while the mod's own server-side `OnCooked` hook rewrote it. **It opens with the
skew note above** — four driver minors (`4239c5d`) and two harness read-backs (`903ccaa`) landed
after it, and it was not re-run; every number below is the file's own.

- **Provenance — the profile.** `testing/profiles/teardown-longtermpreservation4220.toml`:
  `fixture = "default"`, `[[mods]] id = "PZTestKit"` then `[[mods]] id =
  "SKITTLE_LongTermPreservation4220", workshop_id = "3774789651"`, **no `[sandbox]` block**, and
  three `[[verify]]` probes (server `items.count`, server `recipes.craft Skittles.MakeCuredMeat`
  — module-qualified, `45c0915` — and client `item.script`). The file's resolved form is in the
  artifact's own `profile` block, including the two source folders that reached
  `<run>/server/mods/`. Its acceptance run is named in `acceptance_run`:
  **`run-20260910-191842`** (`RESULT: PASS`, 3/3 probes, 70.6 s) — that run's own `report.json`
  is *not* committed here. What survives of it is this file's own `verify` key: the session
  **re-ran the same three probes itself** after `session_ready`, so those readings are this run's,
  not copies of the acceptance run's. Cite them from here; the acceptance run id is provenance.
- **Provenance — the mod.** Workshop item `3774789651`, folder `LongTermPreservation4220`,
  version folder `42.20/` (its only one), `42.20/mod.info` declaring
  `id=SKITTLE_LongTermPreservation4220`, `author=Skittles`, **no `require=`**, no sandbox
  options; 239 131 B, every file stamped 2026-09-01 13:13. The workshop tree is read-only to the
  harness. **`folder_check` is the reading that says where the copy landed**: `listing
  ["PZTestKit", "SKITTLE_LongTermPreservation4220"]`, `source_folder_present false`,
  `mod_info_at_id true`, `ini_mods_line Mods=PZTestKit;SKITTLE_LongTermPreservation4220` — the
  folder-to-id rename, measured, which is what closes
  [`platform/harness.md#profiles`](../../../docs/platform/harness.md#profiles).
- **How to read the cross-side rows.** `comparisons[]` holds three graded blocks (`baseline`,
  `t+0s`, `t+3s`), each comparing the same **26** getters server-vs-client numerically under
  `tolerance.value` (1e-6), with `same_instance` and a `desynced` list. `same_instance` is
  `true` and `getID` is `562521975` on both sides at all three, so every disagreement is two
  copies of one item, not two items. The four headline desyncs (`getOffAge`, `getOffAgeMax`,
  `isCookable`, `isCustomWeight`) sit in `desynced` beside three more the static read did not
  predict (`getActualWeight`, `getThirstChange`, `getHeat`) and one control that was expected to
  differ (`getAge`) — `desynced` is a list of *differences*, not a list of *findings*, so read it
  against the teardown's table rather than quoting its length.
- **Who ran the cook transition.** `who_ran_it.before_cooked` is **`true`** — the server's own
  inventory-item tick had already run the hook before the witness `item.update` reached the item
  (outcome (c)). The four hook prints are in `server_hook_lines` with the server's own frame and
  millisecond clock (`f:643 st:800,113,605-607`); `client_hook_lines` is **empty**, for the
  second session in a row. `outcome` records all three candidate outcomes as booleans.
- **Every float on this bus is rounded to six decimals** (`TK.json` formats a non-integral
  number with `%.6f`), so no reading in this file supports a bit-for-bit claim. The ulp-level
  weight predictions the slice was written against are simply not obtainable here; every desync
  it grades is whole-value (0.05 to 1e9), far above the tolerance.
- **The witness read what it was asked to.** `field_count` is **26** on every `witness.fields`
  reply on both sides at all three snapshots (`field_count_ok true`), so the getter list reached
  the wire as one whitespace-free token and nothing was silently dropped.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `snapshots[].{server,client}.census_player.beyondVanilla` | all four/five vanilla fitness keys (`fitnessMod`, `fitnessUpTimer`, `strengthMod`, `strengthUpTimer`, and `hotbar` on the client) | **A driver defect, fixed after the run (`4239c5d`).** The exclusion set `VANILLA_ITEM_KEYS = {customName}` was applied to the **player** scope too, so every vanilla player key came back flagged as a finding. The census itself (`keys`, `keyCount`) is correct and is what to quote; `beyondVanilla` on the **player** rows is noise. The **item** rows' `beyondVanilla` (`Tooltip`) is right. **Dated note, 2026-09-10 (slice 10):** the player counts here — server 4 / client 5 — are a *late-session* reading. `td2-20260910-231655` took the same census six times and found the server's player modData **empty at join**, gaining the four vanilla fitness keys 22–33 s after `session_ready`; at join the pair is server 0 / client 5. |
| `who_ran_it.reading` | "…fired the hook between the action and this call" | True as a *timing* statement and misleading as a causal one. The `lastCookMinute -1` step is measured **not** to be a precondition: the cook block had already been entered twice this run, 1.33–1.67 game minutes apart, and on `td1b-20260910-202029` the same transition fired **907 ms before** that write reached the server. Cite `before_cooked` for outcome (c); never cite this run as evidence that the flip unblocked anything. |
| `rcon_additem` | `""` | The RCON `additem` answered with an empty body. It says nothing about the spawn; `timeline`'s `additem ok=True` and the client resolving the item id 3 s later are what say it worked. The driver records the boolean as `rcon_additem_ok` only from `4239c5d` on, which is after this run. |
| `notes` | `[]` | Correct here, but **not** reusable as a test. `notes` was both the dormant re-ask branch's sink and, from `4239c5d`, the home of a standing `KEYS_NOTE` — so on later artifacts an empty `notes` is not the "nothing went wrong" signal. On this file it is genuinely empty: no re-ask fired. |
| `steps[].ack.*.lastCookMinute`, `steps[].ack.gameMinute` | absent | The harness gained both in `903ccaa`, after this run. Their absence here is skew, not a reading; the `item.update` step does carry `gameMinute 26`, which is the one counter this build of the harness reported. |
| `getHeat` on the client (frozen at 1.84703 across 12 s) | — | A real reading, and **one item over 12 s**. It says the client's copy of *this* server-spawned item did not tick; it is not a general law about client-side item updates. Quote it as the observation. **Dated note, 2026-09-11 (slice 11):** the "mechanism unexplained" half is no longer true for the cooking case. Slice 10 (`td2-20260910-231655`, `appendix.A2`) read a server-pinned `Base.Steak` that **did** move on the client, which put the canonical row in [`platform/mp-model.md#what-a-client-copy-is`](../../../docs/platform/mp-model.md#what-a-client-copy-is) into contention; slice 11 then ran the probe that row named — the same pin at `heat 1.2`, **below** `Food.update`'s 1.6 cooking gate (`td3-20260911-001948`, `carrier`) — and the client's copy was bit-frozen while the server's decayed. That row now reads **resolved per arm**: the carrier is the per-game-minute `sendItemStats` inside `Food.update`'s cooking branch, and **this** reading is its below-gate arm. **M per arm**, n = 1 in each; mechanism **C**. |
| everything measured here, as a population | — | **`n = 1`.** One session, build 42.20.4, fixture `default`, one mod, one item (`Skittles.CuredPork`), one player, one cook transition. The desyncs are structural (they follow from the packet's field list) but every *number* is a single reading, and the two surprises — the weight and the thirst rows — are each a single session until `td1b-20260910-202029` re-reads them. |
