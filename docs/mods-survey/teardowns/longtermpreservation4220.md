# Teardown: Long Term Preservation [42.20] (`SKITTLE_LongTermPreservation4220`)

**Verified against: 42.20.4 (`b0bbce05d5`)** — mod read cold 2026-09-10 (no server), then
measured the same day on two dedicated-MP sessions with a real client:
`td1-20260910-192457` and `td1b-20260910-202029`.

- **Workshop ID / mod ID(s):** item **`3774789651`**, one mod, declared id
  **`SKITTLE_LongTermPreservation4220`** (`42.20/mod.info:2`). The **folder** is
  `LongTermPreservation4220` — a whole-prefix drift from the id, which `mod_lint` reports as
  `folder-id` INFO (exit 0, `0 ERROR / 0 WARN / 1 INFO`, 2026-09-10). Always use the declared id
  in `Mods=`; `index["LongTermPreservation4220"]` is `None`. Workshop page (W):
  *Long Term Preservation [42.20]*, 239.131 KB, posted Jul 30 @ 6:31pm, **never updated** —
  <https://steamcommunity.com/sharedfiles/filedetails/?id=3774789651>, fetched 2026-09-10 17:46
  into [`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json).
- **Build examined (date + version folder used):** **`42.20/`**, and it is the mod's *only*
  version folder — no `common/`, no other `42.x` (census of 52 files, 2026-09-10; inventory row
  `version_dirs ["42.20"]`, `media_at ["42.20/media"]`, `live_media true`). Every one of the 52
  files carries the same mtime, **2026-09-01 13:13** — a single Steam *download* stamp, not an
  update history. 239 131 B total, of which `poster.png` + `SaltRock.png` + `SaltRock.fbx` are
  188 245 B (79 %). Inventory figures used below are `data/mod-inventory.json` at commit
  `9f551f6`, swept **2026-09-10 17:47**: **15** live `item` blocks, **117** nutrition-key writes,
  `signals.food_nutrition 4`, `signals.events_add 1`, `lua_kb 3`.
- **Author · dependencies · license/permissions posture:** author **`Skittles`**
  (`42.20/mod.info:3`); `versionMin=42.0.0`, `pzversion=42`, `modversion=1.2` (`:7,8,9`).
  **No `require=` line exists in `mod.info` at all** (the file is 9 lines) → empty dependency
  list, nothing to install beside it. The mod ships **no licence or readme file** (52-file
  census, 2026-09-10) and the fetched Workshop record carries no licence field, so the posture is
  default Steam Workshop terms: **read it, do not vendor it**. Its own `mod.info:6` describes it
  as a *"Community update of Skittles' mod for build 42.20"*, i.e. it is already a re-upload.
  Nothing here is copied into our mod; only patterns are taken.

Grades: **C** = code/script/dataset reading (every one carries `path:line` or a jar dump),
**M** = measured on a run named in the cell, **W** = Workshop page. Mod-relative paths are
relative to `3774789651/mods/LongTermPreservation4220/`; vanilla Java is cited as
`Class.method @offset` from the 42.20.4 jar.

## What it does (player-facing)

1. **Salting and drying.** `MakeCuredMeat` turns 1 raw meat + 5 salt into a `Cured*` twin that
   keeps **53 / 60 days** instead of vanilla's 2 / 4
   (`42.20/media/scripts/recipes/recipe_cured.txt:8-33`;
   `42.20/media/scripts/items/items_dried.txt:23-24`; vanilla `Base.Pork` is 2 / 4,
   `data/food-items.json` ← `items/food.txt:9690`).
2. **Jarring for four meats vanilla does not cover.** `MakeJarredMeat` / `OpenJarOfFoodMeat`
   clone vanilla's `MakeJar` / `OpenJarOfFood` — same Java `OnCreate` statics, same times
   (`recipe_cured.txt:74-129`).
3. **Pemmican, rendered lard, mashed berries and jam**
   (`recipe_cured.txt:35-53,55-71,149-165,167-183`).
4. **A foraged salt rock** plus a mortar-and-pestle recipe that crushes it into `Base.Salt`
   (`42.20/media/lua/shared/Foraging/forageable_items.lua:3-25`; `recipe_cured.txt:131-147`).
5. **Cooking a cured meat makes it non-perishable and 30 % less nutritious**
   (`42.20/media/lua/server/recipe_meats.lua:34-53`); cooking a jar re-bases its age onto a
   180 / 150-day window (`:56-61`). This fifth line is the whole reason the mod was picked, and
   it is the half that does not survive the trip to a client — § MP handling.

## Architecture

**Files that matter** (whole census **52** files, 2026-09-10: 1 `mod.info`, 2 Lua, 3 script
`.txt`, 38 translation `.txt`, 8 art). Line counts are real last-line numbers; 36 of the 44 text
files end without a terminating newline, so `wc -l` reads one lower.

| File | Lines | Side | Role | Ev |
|---|---:|---|---|---|
| `42.20/media/lua/server/recipe_meats.lua` | 61 | **server** (+ singleplayer) | all 7 Lua globals; every nutrition write in the mod | C |
| `42.20/media/lua/shared/Foraging/forageable_items.lua` | 28 | shared (both sides) | the mod's entire event surface | C |
| `42.20/media/scripts/items/items_dried.txt` | 412 | script (loaded per side, never synced) | 15 live `item` blocks | C |
| `42.20/media/scripts/recipes/recipe_cured.txt` | 186 | script | 8 `craftRecipe` + 3 `itemMapper` | C |
| `42.20/media/scripts/items/models_skittles.txt` | 16 | script | 2 `model` blocks | C |
| `42.20/media/lua/shared/Translate/EN/{ItemName,Recipes,Tooltip}_EN.txt` | 18 / 11 / 6 | shared | 15 item names, 8 recipe names, 3 tooltips; 13 language trees in all | C |

Lua total is **89 lines** across two files. There is no `lua/client/` tree.

**Entry points.** Exactly **one** `Events.*.Add` in the whole mod —
`Events.onAddForageDefs.Add(onAddForageDefs)` (`forageable_items.lua:28`), after
`require 'Foraging/forageSystem'` (`:1`), registering `Skittles.SaltRock` with `snowChance -50`,
8 zones and `xp = 2` (`:4-25`). Everything else dispatches **from script into Lua**, 15 sites:
`OnCooked = OnCookedTest` on the 4 cured meats (`items_dried.txt:22,51,80,110`),
`OnCooked = CannedFood_OnCooked` on the 8 jar items
(`:160,184,209,233,257,281,305,329`), and `onCreate = AdjustStates` / `onTest = TryMeat` /
`onCreate = AdjustStatesPemmican` (`recipe_cured.txt:12,13,39`). Two further script keys call
**Java** statics directly: `OnCreate = RecipeCodeOnCreate.makeJar` (`recipe_cured.txt:78`) and
`…applyLidCondition` (`:110`), both present on 42.20.4 (jar `methods` dump). There is no timed
action, no context menu, no `ISBaseTimedAction:derive`, no `function IS…:` anywhere.

**Data model — there is none of the usual kind.** Over the whole live tree (sweep 2026-09-10):
**0** `getModData` / `setModData` / `ModData.` / `transmitModData`, **0** `SandboxVars.` and no
`sandbox-options.txt`, **0** `sendClientCommand` / `sendServerCommand` / `OnClientCommand` /
`OnServerCommand`, **0** `getNutrition()` — the mod never touches a *player*. **All state lives
in one `InventoryItem`'s own Java fields**, written by the two `OnCooked` hooks. That is the
entire architecture, and it is why the MP question is sharp.

**`OnCookedTest`'s 11 setter calls and four `print`s** (`recipe_meats.lua:34-53`), with packet
membership read off
`ItemStatsPacket.write`'s constant pool (re-dumped 2026-09-10: the packet names **43** fields):

| Line | Call | Carried by `ItemStatsPacket`? | Ev |
|---|---|---|---|
| `:36` | `setIsCookable(false)` | no | C |
| `:39` | `setOffAge(1000000000)` — the "never ages" sentinel | no | C |
| `:40` | `setOffAgeMax(1000000000)` | no | C |
| `:42` | `setActualWeight(getActualWeight() * 0.7)` | **yes** — `setData` fills `packet.actualWeight` from `Food.getActualWeightUnmodded()` (`@469-475 L213`); `applyItemStats` writes it back with `Food.setActualWeight` (`@274-279 L555`) | C |
| `:43` | `setWeight(getActualWeight())` | no — `InventoryItem.weight` is not one of the 43 | C |
| `:44` | `setCustomWeight(true)` | no | C |
| `:45-:48` | `setCarbohydrates` / `setLipids` / `setProteins` / `setCalories`, each `× 0.70` | **yes** (all four) | C |
| `:49` | `setHungChange(× 0.70)` | **yes**, and as the **raw** field (`setData @254` reads `getHungChange`) | C |
| `:35,37,41,52` | four `print()` calls (`changing da meat`, `post cookable`, `meat change days`, `meat done`) | server console only | C |

`CannedFood_OnCooked` (`recipe_meats.lua:56-61`) writes `setOffAgeMax(180)`, `setOffAge(150)` and
`setAge(getOffAgeMax() * aged)` — **not one of those three fields is in the packet**, so the
jarring half of the mod writes nothing a client can ever learn (C). The double read of
`getOffAgeMax()` at `:57` and `:60` is deliberate, not a bug: it preserves the aged *fraction*
onto the new window (a jar at 10 % of its old life comes out at 18 days of a 180-day life).

**Client / server / shared split — the mod's central structural fact.** `lua/server/` holds all
7 globals; `lua/shared/` holds the forage def and the translations; there is no `lua/client/`.
So on an MP client `OnCookedTest`, `CannedFood_OnCooked`, `TryMeat`, `TryMeatLard`,
`TryMeatCanned`, `AdjustStates` and `AdjustStatesPemmican` are **undefined globals**, while the
item scripts that name them load identically on both sides — measured: `item.script
Skittles.CuredPork` on server and client came back **identical field for field**
(`HungerChange -60`, `ThirstChange 20`, `DaysFresh 53`, `DaysTotallyRotten 60`,
`IsCookable true`, `MinutesToCook 300`, `MinutesToBurn 900`), differing only in `side`
(**M** — `td1-20260910-192457`, key `item_script`). Every runtime difference below is therefore
attributable to the packet, not to a script mismatch.

`Food.update`'s `OnCooked` dispatch is **not** server-gated — `LuaManager.env.rawget(getOnCooked())`
→ `LuaCaller.protectedCallVoid` (`Food.update @627-@718 L462-L467`, C) — so a client that drove
its own copy of a cured meat to the cook transition would call a **nil** Lua function. On both
sessions the client's console held **zero** hook prints and **zero** nil-call or
`protectedCallVoid` lines (`client_hook_lines: []` on `td1` and on `td1b`), because the client's
copy never reached the transition at all (§ MP handling). The nil-call behaviour therefore stays
**unmeasured**, and this teardown does not claim it either way.

## MP handling

**Where authority lives: entirely on the server, and the wire is vanilla's.** LTP has no
networking of any kind (0 command-bus sites, 0 modData, 0 `sendItemStats` calls of its own). The
engine pushes for it: **inside `Food.update`'s cooking block** there are two
`GameServer.sendItemStats(this)` calls — `@94-@101 L378-379` (before the transition) and
`@916-@923 L499-500` (after it) — and those two are the ones that carry LTP's writes.
`Food.update` has a **third**, outside that block: `@1245-@1252 L535-536`, at the end of the
tainted-water boiling branch where `cookingTime > 10` sets `isTainted = false` (`@1240-@1242
L533`). All three are behind `if (GameServer.server)` (C). So the mod's whole MP contract is
**`ItemStatsPacket`'s 39 item-state fields**, and anything it writes outside that list is
server-only state.

`ItemStatsPacket.setData` puts **43** fields on the wire, of which **39 are item state**. The
other four are `containerId` and `id` (addressing) and `isFluidContainer` and `isFood` (presence
flags), none of them ever applied to the item — the reconciliation
[`../../vanilla/food-item-model.md`](../../vanilla/food-item-model.md) § MP behaviour already
carries, and the count slice 02 published. The 43 names, dumped from `ItemStatsPacket.write` on
42.20.4 (2026-09-10) — the four non-state ones are named again inside it — `actualWeight
baseHunger boredomChange calories carbohydrates condition containerId cookingTime endChange
extraItems fatigueChange fertilizedTime fluReduction fluidContainer foodSicknessChange heat
hungChange id isAlcoholic isBurnt isCooked isCustomName isFertilized isFluidContainer isFood
isFrozen isTainted isWet lipids minutesToBurn minutesToCook name painReduction
poisonDetectionLevel poisonPower proteins spices stressChange thirstChange unhappyChange
usedDelta uses wetCooldown` — of which `containerId`, `id`, `isFluidContainer` and `isFood` are
the four that are **not** item state. **`isCookable`, `weight`, `customWeight`, `age`, `offAge`,
`offAgeMax`, `lastAged`, `freezingTime` and `rotten` are absent from all 43** (C).

**Measured, both sides of one live dedicated server, same instance (`getID 562521975` on both,
`same_instance true` at all three snapshots).** Values are the t+3s snapshot of
`td1-20260910-192457` (`comparisons[2]`); the comparison is numeric under the session's tolerance
rule, `|server − client| ≤ 1e-6` is synced.

| Field / key | Server after cook | Client | In the packet? | Reading | Ev |
|---|---|---|---|---|---|
| `getCalories` | 300 → **210** | **210** | yes | synced — the ×0.70 travels | M — `td1` |
| `getProteins` | 50 → **35** | **35** | yes | synced | M — `td1` |
| `getLipids` | 12 → **8.4** | **8.4** | yes | synced | M — `td1` |
| `getCarbohydrates` | 0 → 0 | 0 | yes | ×0.70 of 0 — **no information**, kept so "all four macros" is honest | M — `td1` |
| `getHungChange` | −0.6 → **−0.42** | **−0.42** | yes, **raw** | synced at the bus's resolution (§ instrument limit) | M — `td1` |
| `getHungerChange` | −0.6 → **−0.546** | **−0.546** | derived | synced: the raw field travels and **each side ladders it once** (−0.42 × 1.3). This is the correct shape, and the contrast that makes the thirst row a defect | M — `td1` |
| `getOffAge` | 53 → **1 000 000 000** | **stays 53** | **no** | **DESYNC**, Δ 999 999 947 — the client still thinks the meat spoils | M — `td1` |
| `getOffAgeMax` | 60 → **1 000 000 000** | **stays 60** | **no** | **DESYNC**, Δ 999 999 940 | M — `td1` |
| `isCookable` | true → **false** | **stays true** | **no** | **DESYNC** — the client's copy will re-enter `Food.update`'s cook block whenever it does tick | M — `td1` |
| `isCustomWeight` | false → **true** | **stays false** | **no** | **DESYNC**, and it is the field that makes the two weight rows below legible | M — `td1` |
| `getActualWeight` | 0.5 → **0** | 0.5 → **0.35** | yes (as `actualWeightUnmodded`) | **DESYNC, Δ 0.35 — and the mod's 30 % cut is *discarded* server-side, not merely desynced.** Predicted synced at ~0.35 by two arms; falsified | M — `td1`, `td1b` |
| `getActualWeightUnmodded` | **0** (also 0 at baseline) | **0** | yes | equal, and **0 on both sides before any cooking** — the display-name guard, not a cook effect | M — `td1`, `td1b` |
| `getWeight` | **0.5** | **0.5** | **no** | **uncarried and NOT desynced** — both sides read 0.5. "Not carried" is not "desynced"; the four observable desyncs are the four rows above, not five | M — `td1` |
| `getThirstChange` | 0.2 → **0.1** | 0.2 → **0.05** | yes, through the **cooked getter** | **VANILLA DEFECT**, Δ 0.05 — the mod never touches thirst. One halving per server→client hop; it converges, it does not compound | M — `td1`, `td1b` |
| `isCooked` | false → true | true | yes | synced — and the client's `true` is the packet's, not its own (the client never ran the hook) | M — `td1` |
| `getCookingTime` | **301.061554** | **301.061554** | yes | synced, and 301.06 rather than the flat 301 we pinned: the server's own tick added `heat/1.5 × 0.05` | M — `td1` |
| `getMinutesToCook` / `getMinutesToBurn` | 300 / 900 | same | yes | synced | M — `td1` |
| `getHeat` | 1.79561 → **1.39397** over 11.1 s | **frozen at 1.84703** | yes | the client's copy is **not ticking** — it holds the value the post-transition push carried | M — `td1` |
| `getAge` | 0 → 0.006526 | **stays 0** | **no** | control; agrees with the prior measurement that `age` never reaches a client | M — `td1`, prior `exp02-20260910-030433` |
| Cooking XP (server, `Perks.Cooking`) | 0 → **2.5** with `chef` set; **0** with `chef` unset | n/a (an MP client grants none) | not an item field | the grant fired on the **server** — an independent confirmation of who ran the hook, and a sound discriminator in both directions. **2.5 is the credited delta, not the grant:** `Food.update @806-@812` calls `GameServer.addXp(chef, Perks.Cooking, 10.0f)`, and `IsoGameCharacter$XP.AddXP` puts a default fixture character (empty XP-boost map) on its **×0.25** arm — 10.0 × 0.25 = 2.5 (C for the ladder, M for the delta) | M — `td1` (`xp_delta 2.5`), `td1b` (`xp_delta 0`) |
| item modData `Tooltip` | present | present | no (script-driven) | both sides instantiate it from `Tooltip = Tooltip_CuredMeat` (`items_dried.txt:34`); **not** evidence of a sync | M — `td1`, `td1b` |
| item modData `customName` | absent (the server census is `Tooltip` alone) | present | no | vanilla deserialisation bookkeeping on the side that came off the wire; present on a **vanilla** control item too | M — `td1`, `td1b` |

**The four headline desyncs are `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight`.** They
were predicted from the packet's field list and confirmed on the **two post-cook snapshots,
11.1 s apart** (`snapshots[1].wall 84.019` → `[2] 95.11`) — the baseline snapshot, taken before
the transition, is not desynced at all (`comparisons[0].desynced []`, which is what makes the
other two readings a *change* rather than a standing difference); the server half
reproduced on a second run (`td1b`: `offAge`/`offAgeMax` 1e9, `isCookable false`,
`customWeight true`) — not re-graded, but reproduced. The session then found **two more the
static read did not predict**: the weight row and the thirst row.

**Who ran the cook transition: the server's own inventory-item tick.** `item.update`'s
`before.cooked` came back **`true`** (`td1`, `who_ran_it.before_cooked`), with `before` already
carrying `offAge 1000000000`, `isCookable false`, `customWeight true` — so the hook had fired
before the witness call, and the four `OnCookedTest` prints are in the **server** console in one
frame, **1.71 s** earlier (`server_hook_lines`, `f:643 st:800,113,605-607`). That 1.71 s is a
**console-derived** figure: the artifacts carry the wall times of the bus acks, while the bus acks
carry no frame stamp — the hook lines' `st:` stamps ARE in the committed `server_hook_lines`, but the
ack side of the subtraction exists only in the server console under the gitignored
`testing/runs/td1-20260910-192457/`, so the subtraction is reproducible only on this machine. The client
console is empty. Three readings the sessions forced on top of that, all of them corrections to
what the static read assumed:

- **The scripted `lastCookMinute -1` flip is not a precondition.** On `td1` the cook block had
  already been entered twice (1.33–1.67 game minutes apart), so the minute gate had reopened on
  its own; on `td1b` the transition fired **907 ms before** the flip reached the server — again a
  figure whose ack-side stamp exists only in the server console under the gitignored
  `testing/runs/td1b-20260910-202029/` (the hook stamp itself is in the committed `server_hook_lines`),
  against the ack wall time in the artifact. The committed keys are on the **step row**:
  `steps[set_lastCookMinute]` carries `cooked: true` and `before_lastCookMinute: 23` as flat
  keys (the nested `before` object lives one level deeper, on `…ack.before`, and reads the same).
  `heat > 1.6` plus `cookingTime > minutesToCook` suffice, and the minute gate opens by itself
  within one game minute. **M** — `td1`, `td1b`.
- **The server's inventory-item tick runs about once every 5 s, not every frame.** Bounded three
  ways on `td1` (heat *exactly* constant across three reads in the window, ~50 frames with no
  tick, and the 0.15003 heat step being `0.001 × accum` for ≈5 s of accumulation) and reproduced
  on `td1b` (0.15291). Heat decay measured at **≈0.036/s** at this fixture's `mult 4.7961`.
  Mechanism (C): `InventoryItem.calculateTimeMultiplier`'s `GameServer.server` arm (`@0-@3`) is
  real-time-delta driven and clamped at 6 s, and `Food.updateTemperature` only acts once its
  accumulator reaches 10.0. **M** — `td1`, `td1b`. Consequence for any harness: a bus call cannot
  win a race against this tick, so a probe must not assume per-frame item updates.
- **The client's copy of a server-spawned item did not reach `Food.update` at all.** Over the
  same **11.1 s** its `getHeat` (1.84703), `getCookingTime` (301.061554) and `getAge` (0) never
  moved while the server's ran two or three ticks. The client arm of `calculateTimeMultiplier`
  (`GameTime.getMultiplier()`) would have accumulated on any tick at all, so "zero ticks" is the
  reading. The **mechanism is open** — the call path
  `IsoGameCharacter.updateInternal @1918-@1925 L9296` → `recursiveItemUpdater @0-@61` →
  `InventoryItem.update()` carries no side guard (C). The only guard on that path is the
  `isZombie` test immediately above it (`@1911-@1915 L9295`), which a player character fails, so
  why it did not run is unexplained. (Offsets as `docs/superpowers/plans/02-notes.md:1038` gives
  them; `testing/experiments/td1_longtermpreservation4220.py:18` still quotes the older
  `@1911-@1923` span that merged the guard with the call — the driver is deliberately not edited
  after its run.) **M on the freeze**, open on the cause; it qualifies
  `docs/superpowers/plans/02-notes.md:1038-1040`, which the static read leaned on.
  **The next check, for slice 10's pass** (whose subject `simpleStatus` is a pure client reader):
  take a client-side `witness.fields` of the item's *container* — is the instance the client is
  answering about actually held by the local player's inventory object, or by a detached copy? —
  and read the client's `heat` / `cookingTime` twice 10 s apart on an item the client itself
  holds. Those two readings separate "never scheduled" from "scheduled on a different object".

**The weight story, and the mod-authoring finding inside it.** Predicted: server ≈ 0.35 stored,
client 0.35 recomputed, synced by two different arms of `Food.getActualWeight`. Measured: server
**0**, client **0.35**. The chain, all of it read directly on `td1b`:

- `getActualWeightUnmodded @0-@24` is `displayName.equals(fullType) ? 0 : max(actualWeight, 0)`,
  and `InventoryItem.getDisplayName()` is `return this.name` (C, jar).
- `getDisplayName` on **both** sides for `Skittles.CuredPork` is **`Skittles.CuredPork`** — equal
  to `getFullType`, before and after cooking, so the guard returns 0 on both sides from the first
  reading, with the stored field still at 0.5 (**M** — `td1b`, `answers.4.1_mod_raw` /
  `4.1_mod_cooked`). `Item.InstanceItem @3380-@3393` seeds `actualWeight` **and** `weight` from
  the same `Weight = 0.5` (`items_dried.txt:12`) on both sides, so the guard is **symmetric**.
- The vanilla control `Base.Steak` reads `getDisplayName` **`Steak`** on both sides and keeps
  **0.3** everywhere, `differs: []` (**M** — `td1b`, `answers.4.2_vanilla_raw` /
  `4.2_vanilla_after`). So this dedicated server resolves vanilla item names perfectly well: it
  is **not** a server-wide failure.
- The 0-vs-0.35 split is therefore **`isCustomWeight` choosing an arm**: server `customWeight`
  true → `Food.getActualWeight @288 L910` → the guarded `InventoryItem` route → **0**; client
  `customWeight` false → `@215-@287 L902-L908`, script weight × hunger fraction → **0.35**
  (C for the arms, M for both values).
- **Consequence:** once LTP cooks a cured meat the dedicated server reports it as weighing
  **nothing**, and `ItemStatsPacket.setData @472` fills the packet from
  `getActualWeightUnmodded()`, so the 0 is what travels. The client only reads 0.35 because it
  recomputes from the packet-carried `hungChange`.
- **Open question, with the control that settles it.** Three hypotheses are still unseparated:
  (i) **no translation entry** — `Skittles.CuredPork` has no name in whatever table
  `InventoryItem.name` is resolved from, so the name falls back to the full type; (ii) **the
  B41-layout file is ignored** — LTP ships `42.20/media/lua/shared/Translate/EN/ItemName_EN.txt`
  (`:3` = `ItemName_Skittles.CuredPork = "Cured Pork"`), which is the **B41** layout, while
  42.20.4 ships translations as `ItemName.json` (`tools/food_scan.py:270-271`: "the B41
  `ItemName_EN.txt` layout is gone"), so the mod's name may simply never be loaded on 42.20.4;
  (iii) **mod translations are not consulted at all** for `InventoryItem.name` on a dedicated
  server. n = 2 supports only "not dedicated-server-wide" and "this item's name does not
  resolve".
  **The control criterion, corrected.** It is *not* "an item with no `DisplayName =` line":
  **no vanilla food has one** — 0 of the 1 005 records in
  [`data/food-items.json`](../../../data/food-items.json) and 0 occurrences in vanilla
  `media/scripts/generated/items/food.txt` (2026-09-10), so that criterion selects everything and
  discriminates nothing. The discriminator is the **translation table**: six `module Base` foods
  are absent from `media/lua/shared/Translate/EN/ItemName.json` (4 889 entries) and therefore
  carry a null `display_name` in the dataset — `Base.FruitSaladClay` and
  `Base.HotDrink{Copper,Gold,Metal,Silver,Tumbler}` — while `Base.Steak`, the control this pass
  already read, **is** in `ItemName.json` as `"Steak"`. Reading `getDisplayName` on those six
  beside `Base.Steak` separates (i)+(iii) from a mod-specific failure; LTP cannot supply the
  control itself, having **no live item carrying `DisplayName =`** (both occurrences sit inside
  the `/* OBSOLETE */` block, `items_dried.txt:377,395`), and neither remaining teardown pick has
  any item block at all. **Slice 10's session runs the six-vs-`Steak` reads**; nothing here does.
  (The mod's only display-name code is commented out: `recipe_meats.lua:50-51`.)

**A vanilla defect found by accident: a cooked food's thirst halves on every server→client hop.**
(Canonical graded row: [`../../modding/patterns.md`](../../modding/patterns.md) § Measured MP
sync facts → *The other direction — server → client*, the `thirstChange` row. This section is a
copy; that row owns the numbers.)
The mod never touches thirst, yet after the transition the server reads **0.1** and the client
**0.05**. `ItemStatsPacket.setData` sends `Food.getThirstChange()` — the *cooked ladder* getter
(`burnt → /5`, `isCooked() → /2`, else raw; `@0-@30 L1866-L1875`) — at `@299`, and
`applyItemStats @188/191` stores it with `setThirstChange`, i.e. **as the raw field**, so the
receiver's own getter ladders it a second time. `hungChange` does not have this problem because
`setData @254` reads the **raw** field. C for the mechanism, **M** for the observation. It is
**one halving per server→client hop and it converges**: a deliberate second `sendItemStats` push left the
client at 0.05 → 0.05 with the server unchanged at 0.1 (`td1b`, `thirst_hops.delta 0.0`);
compounding would need a client→server item-stats hop, which
[`../../modding/patterns.md`](../../modding/patterns.md) records as a silent no-op. Any mod that
cooks anything in MP surfaces this; LTP is only the messenger.

**modData census, both sides, three snapshots (`td1`) plus a vanilla control (`td1b`).** LTP
writes **no** modData (0 `getModData` in the whole tree, C), and the census agrees — but it is
not empty:

| Item | Server | Client | Ev |
|---|---|---|---|
| `Skittles.CuredPork` (mod) | `keyCount 1` — `Tooltip:string` | `keyCount 2` — `Tooltip`, `customName` | M — `td1`, `td1b` |
| `Base.Steak` (vanilla control) | `keyCount 0` | `keyCount 1` — `customName` | M — `td1b` |

`Tooltip` is **not** a Lua write: `Item.InstanceItem @3505-@3510` passes the script block's
tooltip to `InventoryItem.setTooltip`, whose **first act** is
`getModData():rawset("Tooltip", value)` (C, jar). So **any script `Tooltip =` line is an item
modData key on every side that instantiates the item** — general, not LTP-specific, and the
vanilla control (no `Tooltip =` line, no key) confirms the route rather than weakening it. The
census baseline for later teardowns is therefore: exclude `customName` always, and exclude
`Tooltip` for any item whose script declares one. No push changed either census.

**Latent risks not measured.** (i) Whether a relog or a save round-trip repairs the client's
copy of the four uncarried fields is **not** measured here — `InventoryItem.save`/`load` is a
different path from `ItemStatsPacket`, and nothing in these sessions reads it. (ii) The client's
copy keeps `isCookable true`, so if it ever does tick `Food.update` it can re-enter the cook
block on its own and call a nil `OnCookedTest`; neither session reproduced that.

**Instrument limit, recorded rather than worked around.** `TK.json` renders a non-integral
number with `string.format("%.6f")`, so **every float on the bus arrives rounded to six
decimals**. The ulp-level predictions the static read made (0.3500000536441803 vs
0.3500000238418579; "one ulp above an exact 0.5" on `getWeight`) are **not obtainable through
this harness** — they collapse to `0.350000` / `0.500000`. Rows above read "synced at the bus's
resolution", never "bit-equal". Every desync graded here is whole-value (0.05 to 1e9), far above
the 1e-6 rule, so no verdict turns on it.

## Techniques worth stealing

- **Script-key dispatch into your own Lua instead of monkey-patching a vanilla function.**
  `OnCooked = OnCookedTest` (`items_dried.txt:22`), `onCreate` / `onTest`
  (`recipe_cured.txt:12,13`). The mod patches **zero** vanilla API surface and still runs code
  at the moment it cares about. All 7 of its globals are new names — checked name by name
  against the whole vanilla `media/lua/` tree, **0** hits (C, 2026-09-10).
- **Consume vanilla extension points rather than reimplementing them:** `Events.onAddForageDefs`
  + `forageSystem.addItemDef` for a new forageable (`forageable_items.lua:3-25,28`), and the
  Java statics `RecipeCodeOnCreate.makeJar` / `.applyLidCondition` called straight from script
  (`recipe_cured.txt:78,110`) — the jarring recipes get vanilla's exact behaviour for free.
- **`itemMapper` to collapse a 4-input / 4-output family into one recipe block**
  (`recipe_cured.txt:19,24,26-32`). Measured working: `getPossibleResultItems()` resolved
  `item 1 mapper:meatType` to all four cured meats (**M** — `td1-20260910-192457`,
  `recipe_lookup.bare.outputs[0].itemFullTypes`, the committed reading; the acceptance run
  `run-20260910-191842` saw the same thing first, but its `report.json` is under the gitignored
  `testing/runs/`, so it is provenance, not the citable evidence).
- **Re-basing an age fraction onto a new window by re-reading the setter's own result**
  (`recipe_meats.lua:57-60`): compute the fraction against the old max, set the new max, then
  set the age from the *new* max. It reads like a double-read bug and is the correct idiom.
- **Its own `module Skittles` for everything** (`items_dried.txt:1`, `recipe_cured.txt:1`,
  `models_skittles.txt:1`), importing `Base`. **Zero** name collisions against vanilla's **5 092
  distinct item names** — 5 105 `item` blocks across `media/scripts/generated/items`, 13 of them
  redefinitions of a name declared earlier, and every one under `module Base`, which is the only
  module vanilla declares (C, 2026-09-10; the live `items.count` total of **5 107** in
  `td1`'s `verify[0].got` is those 5 092 plus LTP's own 15 blocks) — and against
  `data/recipes.json`'s 969 recipes (C, 2026-09-10) — the
  clean shape for a content mod that adds rather than rebalances.
- **Pinning shelf life in the script, not in Lua** (`DaysFresh = 53` /
  `DaysTotallyRotten = 60`, `items_dried.txt:23-24`): script values load identically on both
  sides and need no sync at all. Everything LTP does in *Lua* is what desyncs; everything it
  does in *script* is safe. That contrast, on one mod, is the single most useful thing in this
  teardown.

## Pitfalls / anti-patterns

1. **Writing item fields the sync packet does not carry.** `setIsCookable`, `setOffAge`,
   `setOffAgeMax`, `setCustomWeight` (`recipe_meats.lua:36,39,40,44`) are all outside
   `ItemStatsPacket`'s 43 fields, so the client's copy of a cured meat keeps `DaysFresh 53` and
   `isCookable true` forever. **Rule: the packet's field list is the contract. A mod that writes
   an item field the packet does not carry depends on the server copy alone — any client-side
   reader of that field is reading a stale value, and no amount of re-pushing fixes it.** This is
   the ItemQuality failure mode ([`itemquality.md`](itemquality.md)) arriving in a mod that is
   otherwise well-built, and it is now a FILTER row in
   [`../../modding/patterns.md`](../../modding/patterns.md).
2. **Flipping `customWeight` on an item whose display name does not resolve silently destroys the
   value you just computed.** `:42-:44` writes 0.35, then moves the server onto the arm that
   reads it through `getActualWeightUnmodded`'s display-name guard — which returns **0**. The
   mod's intended 30 % weight reduction is discarded on the authoritative side. **Rule: do not
   write derived values into engine fields whose getters have guards you have not read; prefer
   modData plus a derived-on-read value.**
3. **Seven unqualified `_G` globals with generic names** — `AdjustStates`, `TryMeat`,
   `TryMeatLard`, `TryMeatCanned`, `AdjustStatesPemmican`, `OnCookedTest`,
   `CannedFood_OnCooked` (`recipe_meats.lua:2,9,17,26,30,34,56`). A grep of every `.lua` in the
   installed 230-mod corpus (2026-09-10) finds exactly one file defining any of them — LTP's
   own — so there is no collision **today**, but a `craftRecipe onCreate` calling someone else's
   `AdjustStates` would fail silently and load-order-dependently. **Rule: namespace everything
   (`NUT_…` or a single table).**
4. **Dead and defective code wired into live keys.** `AdjustStates` and `AdjustStatesPemmican`
   (`:26-28,30-32`) are **empty bodies** attached to two live `craftRecipe onCreate` keys, under
   a comment describing weight code that is not there (`:24-25`). `TryMeatLard` and
   `TryMeatCanned` (`:9-14,17-22`) have zero reference sites. `recipe_meats.lua:19` writes
   `return 0.15 < sourceItem:getActualWeight() < 1`, which parses as `(0.15 < w) < 1` — a boolean
   compared to a number, which standard Lua raises on; it is unreachable, so it has never run.
   And the **live** `onTest`, `TryMeat`, is a no-op guard: its comment says *"Only meats above a
   weight of 0.2"* (`:1`) while its body returns `getActualWeight() > 0.0` (`:4`) and a
   non-`Food` input returns `true` unconditionally (`:6`). **Rule: a hook key wired to an empty
   function is worse than no key — it looks handled.**
5. **A brace-unbalanced script file, tolerated by the engine.** `items_dried.txt:374` opens
   `/* OBSOLETE` and `:409` closes it *inside* the `DriedBeef` body, so the comment-stripped file
   is **17 `{` against 18 `}`** and `:412`'s `}` closes nothing. The engine loaded all 15 blocks
   anyway: `items.count` answered `foodByModule {"Base": 722, "Skittles": 14}` at join — exactly
   the 15 live blocks minus `SaltRock` (`base:normal`, `items_dried.txt:348`) (**M** —
   `td1-20260910-192457`, `verify[0].got.foodByModule` and `items_census.foodByModule_Skittles`,
   the committed readings; reproduced on `td1b`. The acceptance run `run-20260910-191842` read it
   first, but its `report.json` lives under the gitignored `testing/runs/`, so it is provenance).
   The parse abort this could have caused did not happen, and that tolerance is now a
   measured fact rather than an assumption. **Rule: it still should not ship — `parse_script` and
   the engine agreeing today is luck, not contract.**
6. **`print()` in a shipped hook.** Four lines per cooked meat on the server console
   (`:35,37,41,52`). They are the reason this teardown could date the transition to the
   millisecond, and they are noise on a busy server with no way for an admin to turn them off.
7. **The jarring half writes nothing a client can learn** — 8 of the mod's 12 `OnCooked` sites.
   `CannedFood_OnCooked` sets only `offAge`,
   `offAgeMax` and `age` — three uncarried fields — so on a dedicated server a jarred food's
   client copy shows the *pre-cook* shelf life indefinitely. **Rule: before writing a hook,
   check whether any of its writes are in the packet; if none are, the feature is
   singleplayer-only whether or not you meant it to be.**

## Compatibility notes

- **Load order is irrelevant to LTP.** No monkey-patching, no vanilla script-block
  redefinition (0 collisions on all 15 item names, 8 recipe names and 2 model names, C
  2026-09-10), no `require=` in `mod.info`, and its one `require` is vanilla's own
  `Foraging/forageSystem`. The single ordering-sensitive surface is the forage-def
  registration, which vanilla's `onAddForageDefs` event already serialises.
- **Patched API surface: zero**, and the loader says so in its own words. Both artifacts'
  `mod_log_lines` carry the same pair of `LOG : Mod` lines: `loading
  SKITTLE_LongTermPreservation4220`, then `mod "SKITTLE_LongTermPreservation4220" overrides` —
  the loader's **override census**, printed per mod as the name followed by the list of vanilla
  files this mod shadows. Here the list is **empty**: the line ends at `overrides` (88 characters,
  well inside the 200-character capture limit that truncates the three `NoSuchFileException`
  lines beside it), so the engine agrees LTP shadows nothing (**M** — `td1`, `td1b`,
  `mod_log_lines[1]`). It consumes three extension points (`onAddForageDefs`, the script hook
  keys, the `RecipeCodeOnCreate` statics) and replaces nothing. Re-loading it is idempotent by
  construction: `recipe_meats.lua` assigns 7 plain globals at file scope and holds no state.
- **The `_G` namespace is the one real conflict risk** — see Pitfalls 3.
- **No command bus and no UI surface**, so it cannot collide with the resident Girth stack's
  command sites or with CleanUI's client UI tree. Both counts are the slice-08 catalog's, dated
  **2026-09-10**: **228** `sendClientCommand` / `OnClientCommand` / `sendServerCommand` sites
  across the six Girth mods, 96 of them in `QuestSystem`
  ([`../approved-modlist.md`](../approved-modlist.md) § the resident stack — the "110+" this doc
  first carried was a pre-slice-08 figure); and CleanUI's live `42.19/` ships **54** client Lua
  files, **33** of them at the same relative path as a vanilla `media/lua` file, i.e.
  replacements (C, counted 2026-09-10). LTP's own surface is 0 on both.
- **Overlap with our own item pass.** LTP adds **14 new food items with a full macro set** in
  `module Skittles` (117 nutrition-key writes, 2026-09-10 17:47). An item pass that rewrites
  `module Base` food definitions will **not** touch them, so on a server running both, 14 foods
  keep upstream numbers while vanilla's are re-based. Five of them also feed vanilla evolved
  recipes (`EvolvedRecipe = Soup:15;Stew:15;…` on `items_dried.txt:17,46,75,105,134`), so they
  flow into vanilla dish macros through `EvolvedRecipe.addItem`. Conversely two **vanilla** items
  are produced by LTP recipes — `Base.Lard` (`recipe_cured.txt:69`) and `Base.JamFruit` (`:181`)
  — so any change we make to those two is inherited by its crafting for free.
- **`CuredFish` is the one item whose macros are not its input's**: 420/3/25/55
  (`items_dried.txt:115-118`) against `Base.FishFillet`'s 205/1/12/28.52 — roughly a doubling,
  where `CuredPork` / `CuredBeef` / `CuredVenison` copy their inputs exactly. If we ever balance
  against LTP, that is the outlier to know about.
- **What a client-side reader (simpleStatus, CleanUI) gets wrong on a cooked cured meat.** The
  four uncarried fields — `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` — plus
  `getThirstChange`, which reads **half** the server's value (vanilla's defect, not LTP's). The
  five macros are right. `getWeight` is right (0.5 on both sides), and `getActualWeight` is the
  one field where the **client** holds the intended value (0.35) and the **server** does not (0),
  so a client UI drawing weight is not misled while anything computing server-side is. A UI
  drawing shelf life, cookability or thirst is.
- **Installation does land the folder under the declared id** (that it *must* is an inference,
  not a measurement — no run left a drifting folder unrenamed; see
  [`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 6). The harness's own placement was
  verified on this mod: the run's `mods/` listing is `["PZTestKit",
  "SKITTLE_LongTermPreservation4220"]`, no `LongTermPreservation4220/` present,
  `mod.info` found at the id path, and `Mods=PZTestKit;SKITTLE_LongTermPreservation4220`
  (**M** — `td1`, `folder_check`). The server logged
  `loading SKITTLE_LongTermPreservation4220` and three benign
  `java.nio.file.NoSuchFileException` lines for `common/media/AnimSets`,
  `common/media/actiongroups` and `42.20/media/AnimSets` — folders the mod does not ship; the
  loader probes for them on every mod and both runs still recorded `errors=0`.
- **Recipe lookup by name needs the module prefix.** `Skittles.MakeCuredMeat` resolves; the bare
  `MakeCuredMeat` resolves against **neither** spelling the shipped lookup tries, because
  `ScriptBucketCollection.getScript` sends a dot-less name to `getModule("Base")` (C). The
  harness now falls back to a scan of all **977** craft recipes (2026-09-10) and resolves it
  (**M** — `td1`, `recipe_lookup.bare.lookup.route "module-scan"`). That **977** is the live
  count *with the mod loaded*: `data/recipes.json`'s **969** `craftRecipe` blocks (C, the vanilla
  scan) plus LTP's own **8** (`recipe_cured.txt`) — the two numbers are the same census on either
  side of the mod, not a disagreement. Anything that looks up a modded recipe by name must
  qualify it.

## Verdict for our mod

**Not a dependency, and not a conflict — a neighbour, and the clearest available demonstration
of the exact failure we must not ship.**

**Adopt:**

- **Script-first.** Everything LTP expresses in item scripts is correct on both sides for free;
  everything it expresses in a server-side Lua hook is either correct-by-accident (the five
  packet-carried macros) or wrong (the four uncarried fields, the weight). Our item pass belongs
  in scripts; our per-player state belongs in modData with an explicit transmit. Live Java item
  fields are for values we are content to leave server-only.
- **Its hook style** — script keys dispatching into our own namespaced Lua, zero vanilla
  functions patched — and its extension-point discipline (`onAddForageDefs`, `itemMapper`, the
  `RecipeCodeOnCreate` statics).
- **The `module <Ours>` + no `module Base` redefinition shape** for anything we *add*. Note that
  our item *pass* is the opposite case by definition, and the corpus contains no precedent for
  it ([`../nutrition-mods.md`](../nutrition-mods.md) § Open questions 8).

**Avoid:**

- Authority in unsynced item fields (Pitfall 1) — with LTP as the citation, not a hypothetical.
- Deriving and storing weight into engine fields (Pitfall 2).
- Unqualified globals (Pitfall 3); empty hook bodies and dead guards (Pitfall 4).
- Relying on any cooked-food value round-tripping faithfully: `thirstChange` demonstrably does
  not, and that is vanilla's, so our own numbers must be read from the side that owns them.

**Carry forward:** if we ship a `module Base` item pass, LTP's 14 items are outside it by
construction. Decide explicitly whether to ship a compatibility patch for `module Skittles` or to
accept that a server running both has 14 foods on upstream numbers — do not discover it later.

## Sources

**Measured runs** (both on the `default` fixture, build 42.20.4, one dedicated server + one real
client; full run directories stay local under the gitignored `testing/runs/`):

- **`run-20260910-191842`** — acceptance, `pzt run --profile teardown-longtermpreservation4220
  --hold 5`, `RESULT: PASS`, exit 0, 3/3 `verify ok=True`, 70.6 s. **Provenance, not evidence:**
  its `report.json` is under the gitignored `testing/runs/` and so is not checkable from a clone
  ([`docs/decisions.md`](../../decisions.md), the slice-01 row: an **M** must be). Every
  `items.count` / `recipes.craft` number this doc grades **M** is cited from `td1`'s committed
  artifact instead (`verify[0..1].got`, `items_census`, `recipe_lookup`), where the same three
  probes were re-asked by the session itself.
- **`td1-20260910-192457`** — the session. Artifact
  [`testing/artifacts/td1-20260910-192457/teardown-longtermpreservation4220.json`](../../../testing/artifacts/td1-20260910-192457/teardown-longtermpreservation4220.json)
  (71 165 B; 115.9 s wall; `server_error_count 0`), driver
  `testing/experiments/td1_longtermpreservation4220.py` at commit `e3afaa0`. Keys cited:
  `comparisons[]` (three snapshots), `snapshots[].{server,client}`, `steps[]`, `who_ran_it`,
  `guard`, `server_hook_lines`, `client_hook_lines`, `xp_before`/`xp_after`/`xp_delta`,
  `item_script`, `items_census`, `recipe_lookup`, `folder_check`, `mod_log_lines`, `outcome`.
- **`td1b-20260910-202029`** — the follow-up micro-session. Artifact
  [`testing/artifacts/td1b-20260910-202029/teardown-longtermpreservation4220-followup.json`](../../../testing/artifacts/td1b-20260910-202029/teardown-longtermpreservation4220-followup.json)
  (41 075 B; 96.9 s wall; `server_error_count 0`), driver
  `testing/experiments/td1b_longtermpreservation4220.py` at commit `38ecf23`. Keys cited:
  `answers`, `weight_reads[]`, `thirst_hops`, `censuses[]`, `steps[]`, `item_get_after_cook`,
  `xp_delta`, `server_hook_lines`, `client_hook_lines`.
- Provenance, reading guides and the *do not cite* list for both:
  [`../../../testing/artifacts/README.md`](../../../testing/artifacts/README.md).
- Profile: `testing/profiles/teardown-longtermpreservation4220.toml` (harness + `[[mods]]
  workshop_id = "3774789651"`, no `[sandbox]` block; the module-qualified recipe probe landed in
  `45c0915`). Harness commands used here were added in `37e411e` (server `item.script`, the four
  `ITEM_STATE` weight/cookable keys, the `chef` setter, `perk.xp`, the recipe module scan, and
  the `witness.moddata` trailing-colon gate fix) and `903ccaa` (`lastCookMinute` read-back,
  `gameMinute` on `item.set` acks) — see [`../../testing/README.md`](../../testing/README.md).

**The mod itself** (read-only; `3774789651/mods/LongTermPreservation4220/`, all files stamped
2026-09-01 13:13): `42.20/mod.info`; `42.20/media/lua/server/recipe_meats.lua`;
`42.20/media/lua/shared/Foraging/forageable_items.lua`;
`42.20/media/scripts/items/items_dried.txt`; `42.20/media/scripts/recipes/recipe_cured.txt`;
`42.20/media/scripts/items/models_skittles.txt`;
`42.20/media/lua/shared/Translate/EN/{ItemName,Recipes,Tooltip}_EN.txt`.

**Datasets:** [`data/mod-inventory.json`](../../../data/mod-inventory.json) — the
`SKITTLE_LongTermPreservation4220` row (230 mod folders swept 2026-09-10 17:47, at `9f551f6`);
[`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json) — the
`3774789651` result (fetched 2026-09-10 17:46, W);
[`data/food-items.json`](../../../data/food-items.json) — the vanilla values of the recipe
inputs, and the `display_name` column that supplies the six-item control set for the open
question above; [`data/recipes.json`](../../../data/recipes.json) — the 969-recipe collision
check.

**Vanilla scripts and translations (C, read 2026-09-10):**
`media/scripts/generated/items/` — 5 105 `item` blocks, 5 092 distinct names, all `module Base`,
0 `DisplayName =` lines in `items/food.txt`;
`media/lua/shared/Translate/EN/ItemName.json` — 4 889 entries, the table the six null
`display_name` foods are absent from and `Base.Steak` is present in.

**Engine (C, 42.20.4 jar dumps taken 2026-09-10):** `Food.update` (the cook block, the
`OnCooked` dispatch `@627-@718`, the XP branch `@755-@812`, and all three `sendItemStats` calls
— `@94-@101`, `@916-@923` and `@1245-@1252` in the tainted-boil branch),
`Food.getThirstChange @0-@30`, `Food.getActualWeight @208-@288`,
`InventoryItem.getActualWeightUnmodded @0-@24`, `InventoryItem.getDisplayName @0-@4`,
`InventoryItem.setTooltip @0-@13`, `InventoryItem.calculateTimeMultiplier`,
`Food.updateTemperature`, `Item.InstanceItem @3380-@3393` and `@3505-@3510`,
`ItemStatsPacket.write` / `.setData` / `.applyItemStats`, `IsoGameCharacter$XP.AddXP`,
`ScriptBucketCollection.getScript`.

**Neighbouring library docs:** [`../../modding/patterns.md`](../../modding/patterns.md) (the
KEEP/FILTER rows and the measured sync facts this teardown adds to),
[`../../vanilla/food-item-model.md`](../../vanilla/food-item-model.md) and
[`../../vanilla/eating-pipeline.md`](../../vanilla/eating-pipeline.md) (the item lifecycle and
the eat path), [`../nutrition-mods.md`](../nutrition-mods.md) (the catalog rows for this mod —
§ The three picks, § Discrepancies rows 1 and 6, § Open questions 4 and 6),
[`../approved-modlist.md`](../approved-modlist.md) (the corpus and the queue),
[`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 6 (the folder→id
rename — the placement half closed **M** by this pass's `folder_check`, the "is it required"
half left **C** with its control named), and [`itemquality.md`](itemquality.md) (the same
unsynced-field failure, in a mod that meant to sync).
