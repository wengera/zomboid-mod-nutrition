# `exp08-20260910-152944` reading guide

**`exp08-20260910-152944/witness-probe.json`** — produced by
`testing/experiments/s08_witness.py`, the live witness probe (slice 08, task 4), together with
the `witness.fields` / `witness.moddata` block of `PZTestKit_Core.lua` that it drives. **87.1 s
wall**: server boot `took 13.1`, client `took 32.8` (in-world at `t 47.3`), 17 probes between
`t 51.6` and `t 75.6`, `client_quit rc=0`, `server_stopped rc=0`. `server_errors` **empty**,
`faults []`, no client Lua error (0 lines matching the harness's own `LuaError|STACK TRACE|lua
error` regex in `clients/admin/console.txt`), doctor all-`ok` in `meta.doctor`. Dataset
`data/food-items.json` at sha256 `c71202bd…`, read and never written.

**Skew (slice 08 review round 1).** This file was produced by the driver at **`ba19649`**. Review round 1 then
edited `s08_witness.py` without re-running it: it added the `isinstance` guards that four
grading blocks (rows 10–13) were missing, so a reply that survived the bus guard as a *string*
records its shape instead of raising inside `grade()` and silently truncating the table; it
checked `WITNESS_MAX` against the getter lists instead of asserting it in prose; it let
amendment 3's `getOrCreate` finding be recognised in a bare-string reply as well as in a table's
`error`; it tightened rows 1–2's `expected` text to what their `ok` condition actually checks;
and it deleted two dead names (`ITEM_GET_KEYS`, `grades_by_name`). **Every one of those paths
was inert on this run** — all six `moddata_*` replies, the ones rows 10–13 read, arrived as
tables (the two `gate_*` string replies are the documented exception, row 14), `summary.reasked_probes` is empty,
and no getter list is near the cap — so **no number in this file moves**, and none of the
corrections below came from re-running anything. The three corrections that follow (the
`getSlicesOfBreadEaten` framing, the mechanism of the finding, and the reach of `moddata_item`)
are re-readings of what this file already contains, checked against the 42.20.4 jar.

The two commands had been reviewed and committed but **never executed** — there is no Lua
interpreter on this host, so every claim about them was a reading of the source. This file is
the first time either answered a live game, and it is what slices 09–11 cite instead of that
reading. **15 graded rows: 14 as expected, 1 finding, 0 misses** (`summary`), across both sides
of one session — plus **two ungraded results** that no row carries and that are read off the
probes by hand: that `transmitModData()` moves the whole table (below), and that a getter the
plan named is absent from this build entirely (below). `summary.not_as_expected` names one row
and cannot be read as the count of what this run found.

- **Both commands work on both sides, and `resolved` says whose subject answered.**
  `player_server` / `player_client` return the same four fields for the same five getters, each
  `resolved: "admin"`; the item probes return the same seven fields on both sides, each
  `resolved: "admin/Base.Apple #199691187"`. `count` is 5 / 7 and `truncatedAt` is absent
  everywhere — the `TK.WITNESS_MAX = 32` cap never bit.
- **The item's macros are checkable against something other than the witness**, which is what
  makes this an `M` row: `getCalories 95`, `getCarbohydrates 25.129999`, `getLipids 0.31`,
  `getProteins 0.47` against the dataset's `95.0 / 25.13 / 0.31 / 0.47`, and `getHungChange
  −0.16` against `hunger_change −16.0 × 0.01` (the instance constructor's ÷100, slice 05). All
  ten comparisons (five getters × two sides) match inside the float32 band; `item_get_server` is
  the independent second reading down slice 01's `item.get`, agreeing field for field. That last
  agreement is a **hand reading** off this file — `item.get` spells the same five differently
  (`carbs`, `hungChange`), and the driver records its reply raw rather than computing the
  comparison; only the dataset comparison is computed, in `item_comparison`.
- **`missing` and `nils` are a real three-way sort, and `missing` is not rare.**
  `absent_getter` puts **both** `getCalories` (it lives on `Nutrition`, not on `IsoPlayer`) and
  `getNoSuchThing` in `missing`, with `nils` empty and `fields` empty. The plan's own player
  getter list also names one: **`getSlicesOfBreadEaten` lands in `missing` on the server AND on
  the client**. This is **not** a Kahlua narrowing of a jar member — **42.20.4 has no such member
  anywhere.** A full constant-pool sweep of the jar (`./pz.sh grep SlicesOfBread` in the B42
  workspace) answers `no class contains that literal`; `IsoGameCharacter` (1450 methods),
  `IsoPlayer` (574) and `Nutrition` (26) have no `slice`/`bread` member between them; `media/lua`
  and `media/scripts` have no hit either. So it behaves exactly like `getNoSuchThing`, and it is
  in `missing` for the same reason: the plan named a getter this build does not have. What the
  run measures is the witness's *robustness* — `TK.call` indexes before it calls, so an unknown
  name is an entry in `missing` rather than a dead harness — not a narrower Lua surface.
  (Slices 09–11: a name in `missing` means "not on this object on this build". It does **not**
  distinguish "the jar has it but Lua cannot see it" from "nothing has it"; only a jar check
  does, and this run's one candidate turned out to be the second.)
- **The S6 modData shape reproduces through the generic command** — and shows more than the key
  it was asked about. Client after `moddata.set`: `pzt_witness = "v08"`, `keyCount 6`. Server
  **before** `transmitModData`: `keyCount 4`, `values {}`, `pzt_witness` in `missing`. Server
  **after**: `keyCount 6`, `values {"pzt_witness": "v08"}`. The two keys that arrive are
  `pzt_witness:string` **and `hotbar:table`** — so `transmitModData()` pushes the client's whole
  modData table, not the one key that changed. The census (`keys` as sorted `<name>:<type>`) is
  what makes that visible; a probe for the single key would have missed it. This one is
  justified by the file alone (4 → 6 keys, `hotbar` rode along) and the jar says why:
  `getPlayer():transmitModData()` is `IsoObject.transmitModData()`, which sends
  `ObjectModDataPacket`; its `write` serialises the sender's **whole** table
  (`getModData().save(bb)` behind an `isEmpty` flag) and its `parse` either `load`s that whole
  table into the receiver's `getModData()` or, when the sender's was empty, `wipe`s the
  receiver's. There is no per-key path. A teardown that writes one probe key on the client and
  transmits is rewriting the server's copy of every other key on that character.
- **`ModData.getOrCreate` exists on 42.20.4** — `moddata_global` answers with no `error`,
  `keyCount 0`, `keys {}`. That is the EXPECTED result and it is evidence of the binding only:
  `getOrCreate` **created** `pzt_probe_table`, the probe did. See *do not cite*. Note also that
  the `global:` branch never sets `resolved` at all — it has no subject to resolve — so a driver
  that reads `resolved` on every reply must treat its absence on this scope as normal.
- **The failure and usage shapes are as documented**, which is what lets every later driver know
  when it may meet a bare string. A subject that does not resolve answers a TABLE
  (`player_server_bad_user`: `resolved: false`, `error: "no online player nosuchuser"`); a bad
  `<player|item>` word and a bare `item` scope word answer the usage STRING; `witness.fields
  item` with no id answers a TABLE whose `error` starts `usage:`. All three gates are in the
  file as `gate_*`. The scope-word gate was exercised with `item` only — **`global` was not
  sent** — so the bare-`global` branch is read off the Lua (C), not measured here.
- **A client ignores the `<user>` it is given.** `player_client_wrong_user` asks the client for
  `player nosuchuser` and gets `resolved: "admin"` with `getUsername: "admin"` — `subjectOf`
  resolves the LOCAL player on that side. Always read `resolved`; never assume the name you sent
  is the subject that answered.
- **An empty `missing` / `nils` / `keys` arrives as `{}`, not `[]`** — a harness-wide property
  every later driver inherits, and measured here rather than argued from `TK.json`: 18 empty
  fields across 12 probes, **all of them JSON objects** (`empty_list_shapes` lists every one).
  Test emptiness with `not x`; never `== []`, never index position 0. `count` (names read) and
  `keyCount` (census size) are numbers whatever the shape does, and are the safe assertions.
- **How the `#<id>` route got its id.** `ITEM_GETTERS` does not ask for `getID`, so `item_byid`
  read the id out of `item_server`'s `resolved` label, whose item form ends `#<id>`
  (`session.item_id_source`). It is a reading, not a guess, and `item.get`'s independent
  `id: 199691187` agrees. `item_byid` resolves the same label as the fullType route.

**The one finding, and what actually causes it.**
`item_sides_cross_check.getModData.same` is **`false`**: the SERVER's copy of the apple has
`getModData() == {}` and the CLIENT's has `{"customName": "Apple"}` — same instance, same
`#199691187`, six of seven fields identical. The witness read both sides correctly; the
disagreement is in the game.

It is **not** MP item-modData ownership, and `customName` is not client-authored. It is a
**deserialization side effect**, and the jar names it exactly (42.20.4):

- `InventoryItem.setCustomName(Z)V` unconditionally does
  `getModData().rawset("customName", String.valueOf(this.name))` — one `putfield` and then that
  `rawset`, no branch. Writing the *flag* writes the modData key.
- Its call sites are six, and only one is on a path either side took here:
  `InventoryItem.load(ByteBuffer,int)`, `SyncItemFieldsPacket.processClient` /
  `.processServer`, `InventoryItem.createDefaultDeadBody`, `IsoDeadBody.getItem` and
  `CraftRecipeData.createOutputItems`. The last three are corpse and crafting paths; nothing in
  this run is a corpse or a craft.
- The server built the apple **in process** (`additem` → the item factory, never `load`), so its
  table stayed empty. The client received the same item **serialized** and `load()`-ed it, and
  `load` set the flag — which wrote the key.

So the asymmetry is expected for **any freshly `additem`-ed item**, and it is bookkeeping, not
mod data. Three rules follow for slices 09–11:

1. **Say which side you read.** An item's modData is not the same table on the two sides.
2. **Exclude `customName` from any mod-key census.** It is vanilla bookkeeping present on
   every client-side item that came off the wire or off disk, and absent on a server-side item
   that was built in process. It is not evidence of a mod, in either direction.
3. **When item modData does move, it moves wholesale.**
   `SyncItemFieldsPacket.processModData()` calls `getModData().wipe()` on the receiver (when it
   `hasModData`) and then `rawset`s every key of the sender's table into it. A teardown that
   writes item modData on one side loses it to the next field sync from the other that carries
   modData (`setData` sends `moddata` only when the sender item `hasModData()`, and `processModData`
   returns before the wipe when it is null).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `moddata_global.keyCount` / `.keys` | `0` / `{}` | **Not evidence that nothing stores anything under `pzt_probe_table`** — evidence that `ModData.getOrCreate` exists and creates. The Lua reads global scope through `getOrCreate`, which CREATES an absent table, so a global census can never report "no such table" and this one is reporting a table the probe itself had just made. Cite it for the binding (`witness.moddata global:<name>` reaches global ModData on 42.20.4) and for nothing else. A census of a table a *mod* owns is only meaningful when that mod is loaded and has run. |
| `player_server.fields.getMaxWeight`, `player_client.fields.getMaxWeight` | `12` | Right value, wrong noun if quoted as nutrition. `IsoGameCharacter.getMaxWeight()` is the character's **carry capacity**, not body weight: this fixture's body weight is ~80 kg, and every weight figure this repo has measured (`exp03-20260910-045523`, the slice-04 scenarios, `exp05b`'s `0.016 × weight/80`) is `Nutrition.getWeight()`. The getter was in the probe list to exercise the witness, not to measure a body. |
| `player_server.fields.getHoursSurvived` vs `player_client.fields.getHoursSurvived` | `0.031719` vs `0.033204` | **Not a desync.** The two probes are 0.5 real seconds apart on a clock running at `mult ≈ 4.6` (`session.time_start`), and each reply carries its own `worldAge` (`2.315918` / `2.317490`) which accounts for the gap. Nothing in this file compares a *moving* store across sides; the item macros, which do not move, are the cross-side comparison. |
| `session.rcon_additem` | `""` | The RCON call succeeded (`timeline` `additem ok=true`) and the server answered with an empty body. It says nothing about the spawn; `item_server` resolving `#199691187` 3.8 s later is what says the apple arrived. |
| `moddata_item.keyCount` / `.keys` | `0` / `{}` | **Not an independent corroboration of the cross-side asymmetry** — it corroborates the SERVER value (`{}`) only, and it is the same side and the same JVM that `item_sides_cross_check` already read. The matching client census (`witness.moddata item:admin/Base.Apple *` on the client) **was not run this session**: the client half of the finding rests on `item_client.fields.getModData` alone, one reading. Slice 09's first pass runs the census on both sides; until then cite the asymmetry from `item_sides_cross_check`, and cite this key only for the server side. |
| everything measured here, as a population | — | **`n = 1` everywhere.** One session, build 42.20.4, fixture `default`, one item (`Base.Apple`), one player. The command *shapes* are structural and should not vary, but the item numbers and the modData asymmetry are each a single reading. Nothing in this file supports a claim of the form "always" or "on every build" without a second run. |
| `meta.dataset_meta` | the dataset's whole `meta` block | Embedded verbatim: 5 258 of `meta`'s 7 086 JSON bytes (74 % of `meta`, 12 % of the file), and none of it is a measurement this run made. Only `build` (`42.20.4`) and `jar_hash` (`b0bbce05d5`) matter from it — they say which game build the dataset numbers came off, so that the item comparison above is a comparison of like with like. The rest is `data/food-items.json`'s own provenance and belongs to that file, not to this run; read it there. |

**What this file contains beyond the task brief's skeleton**, all of it read-only and recorded as
its own probe: `player_client_wrong_user` and `player_server_bad_user` (the client's `<user>`
disclosure and the server's failure shape), `item_get_server` (the independent `item.get`
reading), and the three `gate_*` shape probes. The brief's own `item_byid` route is exercised via
`resolved` rather than skipped — see the bullet above. Everything else is the brief's probe list
in the brief's order.
