# Lua API & events — the curated surface a nutrition mod needs

**Verified against: 42.20.4 (`b0bbce05d5`)** — written 2026-09-11 (slice 12) from the six
platform sessions `x121` / `x122` / `x123`+`x123b` / `x124` / `x126` / `x127`, the three
teardowns (`td1`/`td1b`, `td2`, `td3`), the harness's own Lua and the jar. Jar readings
re-taken on 42.20.4 the same day with `pz-b42/pz.sh`.

**This file is CURATED, not an inventory.** A row exists here only because **this library has
used it or measured it** — in the harness (`testing/PZTestKit/`), in the five slice-12
experiment mods (`testing/experiments/TKX_*`), in a teardown of a shipped mod, or in a jar read
taken for one of those. The full event roster lives on the wiki; the full command inventory
lives in [`../testing/README.md`](../testing/README.md). What is here is the surface a B42
nutrition mod actually stands on, with the side that owns each piece and whether it syncs.

**The three rules that shape everything below.** (1) `Nutrition`, hunger/thirst and item state
are **server-authoritative** and arrive on the client as a **push**, so a client-side reader is
reading a mirror, not a simulation. (2) A mod's `media/lua/server/` files are **not**
server-only in MP — they execute in the client's Lua state too. (3) Kahlua's "tried to call
nil" **is** caught by `pcall` — measured, both sides — but an **unguarded** one aborts the rest
of that handler's body and no log ever names the member, so every Java member is still reached
by indexing first. **§ 5 owns that rule, its bounds, and what it does to a `-debug` client.**

## Model — the four surfaces

| Surface | Who owns it | How a mod reaches it |
|---|---|---|
| **Events** (`Events.<Name>.Add/Remove`) | the engine, per Lua state | register at file scope; the state you land in is decided by the loader, not by the folder name |
| **Java members** | the jar; Kahlua publishes *methods*, never fields | index the member, then call it |
| **Script-side hooks** (`OnEat`, `OnCooked`, `OnCreate` in an item block) | the item script; resolved by NAME out of the Lua global table | define a **global** function |
| **The command bus** (`sendClientCommand` / `sendServerCommand`) | the mod | the only sanctioned client→server path for anything the engine does not sync |

Vanilla offers **no** extension point on the nutrition object itself: `Nutrition`'s whole
method list is 26 members — the five stores, the three direction flags, `update`,
`updateCalories`, `updateWeight`, `applyTraitFromWeight`, `applyWeightFromTraits`,
`characterHaveWeightTrouble`, `canAddFitnessXp`, `save`, `load` — with **no** `getModData` and
no generic accessor, and `grep setNutrition` finds **no class on the jar containing that
literal**, so Lua cannot substitute a different object for the one the engine constructs
(jar, 2026-09-11). Everything a mod adds therefore lives in modData, in item scripts, or in a
parallel store of its own.

## 1. Events

`Ev` is the grade for the **side + cadence** claim in that row. Corpus counts are
`hooks / distinct mods` from the 230-mod inventory, **recomputed 2026-09-10**
([`../mods-survey/approved-modlist.md`](../mods-survey/approved-modlist.md) § Event usage);
they are a **floor**, because the census sums each record's `top_events`, which keeps only a
mod's 8 most-used events.

| Event | Fires on | Cadence / when | What this library did with it | Ev |
|---|---|---|---|---|
| `OnClientCommand(module, command, player, args)` | **server** | once per `sendClientCommand` | the server arm of the harness bus (`testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua:517`); corpus 54 / 20 | C |
| `OnServerCommand(module, command, args)` | **client** | once per `sendServerCommand` | the client arm (`…/client/PZTestKit_Client.lua:449`), which is where the S6 witness replies land; corpus 43 / 14 | C |
| `EveryOneMinute` | **both** — measured | one game minute; **3.75 real s** at the fixture's `DayLength 4` (a 90-minute game day: 5400 s / 1440) | the slice-12 nutrient mod's whole drive train, one arm per tick (`testing/experiments/TKX_Nutrient/42.20/media/lua/{server,client}/…:76,29`); over one `x121` session the counter read **58 client / 38 server**, because the client VM ran the `server/` file's handler as well as the `client/` one. Also the harness's belt-and-braces server poll (`PZTestKit_Server.lua:1291`); corpus 22 / 10 | M (`x121-20260911-030023` key `phases.M7.mod_globals`, in [`testing/artifacts/x121-20260911-030023/platform-overrides.json`](../../testing/artifacts/x121-20260911-030023/platform-overrides.json)) for both sides firing; the 3.75 s figure is **C** (the fixture arithmetic, `testing/experiments/x121_overrides.py:85`) |
| `EveryTenMinutes` | not exercised here | ten game minutes | named by KEEP 8 as the other slow tier and **never registered by this library**; it is below the corpus histogram's top-12 cut, so its absence there is a floor artifact, not a zero | C ([patterns.md](patterns.md) KEEP 8; corpus census 2026-09-10) |
| `OnTick` | **both** | every frame | the harness's server poll, deliberately throttled `ticks % 20` (`PZTestKit_Server.lua:1285-1289`); the expensive tier — corpus 70 / 15, and FILTER 5 keeps nutrition out of it | C |
| `OnPlayerUpdate` | client | per player, per frame | **never registered by this library**; recorded because it is the corpus's most *widely* shared hook (55 / 39) and therefore the shared perf hotspot KEEP 8 tells us to stay off | C (corpus census 2026-09-10) |
| `OnCreatePlayer` | **client only** | after Click-to-Start | simpleStatus builds its whole panel here (`42.16/media/lua/client/ss.main.lua:82`) and has no server counterpart at all, which is why it cannot be authoritative about anything | W (the [Lua_event mirror](../../references/wiki-mirrors/lua-event.md), page version 42.20.4, fetched **2026-09-10**, corroborating the client-only marking) + C (`td2-20260910-231655` teardown read) |
| `OnInitGlobalModData` | both; **the server-side init point** | during world init, before players exist | simpleStatus's global-config pair `OnInitGlobalModData` / `OnReceiveGlobalModData` (`42.14/media/lua/server/ss.save.config.lua:30-53`); corpus 33 / 14. With `OnServerStarted` it is the pair that survives a dedicated server, because `OnCreatePlayer` / `OnGameStart` / `OnLoad` never fire there | W (same mirror + fetch date) + C |
| `OnServerStarted` | **server only** | end of world init | mod C retries its `ISEatFoodAction.complete` install here; the harness logs a line (`PZTestKit_Server.lua:1292`); corpus 11 / 6 | W (same mirror + fetch date) + M — see the wrapper row below |
| `OnGameBoot` | launch, both VMs | once at launch | mod C's third install site (`testing/experiments/TKX_EatHook/42.20/media/lua/server/TKX_EatHook_Server.lua:73`); corpus 38 / 16 | W (same mirror + fetch date) + M — see the wrapper row below |
| **Which install site actually wrapped** | both sides | — | `TKX_EatHook.wrapAt` read back **`"file"` on the client and on the server**: the file-scope `install("file")` (`…/TKX_EatHook_Server.lua:67`) won on both, and neither boot event's retry ever re-wrapped, because the sentinel `TKX_EatHook_Installed` (`:31`) made them no-ops. The retry is cover for **load order**, not the install | M (`x121-20260911-030023`, `phases.M5.globals.client.TKX_EatHook.wrapAt` and `.server.…`) |
| `OnPreFillInventoryObjectContextMenu` | client | every inventory right-click | AutoCook's only real entry point, and it lives in `common/` (`common/…/AutoCook_RISCookMenuInsertion.lua:117`); vanilla fires it at `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:374` with `(playerNum, context, items)` | C (`td3-20260911-001948` teardown read) |
| `OnKeyPressed` | client | per key | simpleStatus forwards keys to its bar (`42.16/media/lua/client/ss.main.lua:83-87`) | C (`td2-20260910-231655` teardown read) |
| `OnFETick` / `OnPostUIDraw` | client | per UI frame — `OnFETick` stops once the client leaves `MainScreenState`, `OnPostUIDraw` fires in **every** state | the harness's client poll registers **both** for exactly that reason (`PZTestKit_Client.lua:520-521`), throttled `ticks % 30` | C |

**Heartbeat discipline (KEEP 8), sharpened by slice 10.** Slow simulation — nutrient decay
included — belongs on `EveryOneMinute`/`EveryTenMinutes`, not on `OnPlayerUpdate` and never on
`OnTick`. And for anything that *reads* a server-owned value: **cache at the push cadence, not
the frame cadence.** simpleStatus issues up to **four** `getNutrition()` round trips per
visible macro bar per frame (ten for the weight bar) against a source that changes **once a
second** — `PlayerStatsPacket`, measured arriving at 0.766 s / 0.765 s — so ~59 of every 60
reads return an unchanged value ([teardown](../mods-survey/teardowns/simplestatus.md)
§ MP handling, run `td2-20260910-231655`).

**A raise aborts its own handler's body — not the handlers behind it.** An unguarded nil call
stopped the rest of *that* handler's body (`raw_tail` still `"0"` after ~70 fires) while every
handler registered behind it kept running (`behind` +17, in lockstep with `before`) — M,
`x127-20260911-052049`, **server VM only**, n = 1 session / two passes. The mechanism is
per-callback: `Event.trigger` routes each callback through `LuaCaller.protectedCallVoid` (`@89`
and `@276`, one per dispatch branch) inside a per-iteration
`catch (Throwable) → ExceptionLogger.logException` (`@194-@198 L41-L42`) and continues the loop
(`@216-@219 L31`) — C (jar, 2026-09-11). So a rim `pcall` (KEEP 9) keeps **your own** body
running, not the other handlers. The rule, both shapes and its bounds are in § 5.

## 2. Java members by owner

### `Nutrition` — server-authoritative, per `IsoPlayer`

Reached as `player:getNutrition()`; `getNutrition()` is declared on **`IsoPlayer`**, not on
`IsoGameCharacter` (jar method lists, 2026-09-11).

| Member | Side that owns it | Syncs? | Reading | Ev |
|---|---|---|---|---|
| `getCalories/setCalories`, and the `Carbohydrates` / `Lipids` / `Proteins` pairs | **server** | **yes, server→client** | pushed in `PlayerStatsPacket` at ~1 Hz and in `EatFoodPacket` at eat time. A client-side write is erased inside ~1 s; a server-side write reaches the client inside 3 s | M ([patterns.md](patterns.md) § Measured MP sync facts, runs `exp01-20260910-000351` / `exp03-20260910-045523`) |
| `getWeight/setWeight` | **server** | yes downward, never upward | **and the client cannot derive it either**: a `GameClient.client` early-out at `updateWeight @317-@320 L198` sits ahead of both `setWeight @326 L199` and `applyTraitFromWeight @350`, so a client computes a weight delta and discards it | M (same runs) for the write/discard; C (jar) for the skip |
| `isIncWeight` / `isIncWeightLot` / `isDecWeight` | computed on **both** sides | not packet fields — each side computes its own, and they **agree** | the three are written **ahead** of that skip (`updateWeight @0-@12 L138-L140` resets them, `@129-@131 L167` sets `incWeight`, `@186-@188 L178` and `@222-@224 L181` set `incWeightLot`, `@260-@262 L186` sets `decWeight`), so a client can derive a weight **direction** it cannot derive a weight. Slice 10 got agreement only in the **trivial** arm; `x121` ran the non-trivial ones and both sides agreed: **T/F/F** at calories 1500, **F/F/T** at −102.57 | M (`x121-20260911-030023`, JSON path `phases.M8.arms[]`, the `incWeight` and `decWeight` arms; the claims file labels this reading `m8`) |
| `setCalories` clamping | server | n/a | the store clamps are calories −2200…3700 and −500…1000 per macro, but **nothing clamps at zero**: `nutrition.set calories -100` read back **−102.57 server / −102.10 client** 8 s later — each side has run its own decay ticks since the write, so read the pair as two readings of "not clamped", not as a sync figure. Negative stores are a normal state, not an error state | M (`x121-20260911-030023`, JSON path `phases.M8.arms[1]` — `reading.server.calories` / `reading.client.calories`, `clamped: false`; also `verdicts.M8.observed.decWeight_arm`) |
| `updateWeight`'s cadence | server | n/a | per character update tick, **no timer gate**: `IsoPlayer.update @8` → `updateInternal1 @51 L2200` → `updateInternal2 @392-@402 L2306-L2307` (gated only on `SystemDisabler.doCharacterStats`) → `Nutrition.update @107 L81` → `updateWeight` | C (jar, re-read 2026-09-11; the same chain is recorded in that artifact at `m8.cadence`) |
| anything else — a mod field, a hook, a replacement object | — | n/a | **absent.** No `getModData` on `Nutrition`, no generic accessor, no `setNutrition` anywhere on the jar | C (method list + `grep setNutrition`, 2026-09-11) |

### `Food` / `InventoryItem` — the `TK.ITEM_STATE` set and what the packet carries

`TK.ITEM_STATE` (`testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua:146`) is
this library's working set: **28** keys, each a zero-argument getter reached through `TK.call`.
The split that matters is whether `ItemStatsPacket.setData` reads that getter — anything it
does not read is **server-only state the client will be permanently wrong about** after a
server-side write.

| `TK.ITEM_STATE` keys | In `ItemStatsPacket.setData`? | Ev |
|---|---|---|
| `cooked` `burnt` `frozen` `hungChange` `baseHunger` `calories` `carbs` `lipids` `proteins` `uses` `cookingTime` `heat` `minutesToCook` `minutesToBurn` | **yes** — `setData` reads `isCooked`, `isBurnt`, `isFrozen`, `getHungChange`, `getBaseHunger`, `getCalories`, `getCarbohydrates`, `getLipids`, `getProteins`, `getCurrentUsesFloat`, `getCookingTime`, `getHeat`/`getItemHeat`, `getMinutesToCook`, `getMinutesToBurn` | C (jar, the `setData` getter list read 2026-09-11); **M** for `calories`, `burnt`, `cookingTime`, `heat` (run `exp02-20260910-030433`) and for four of the five fields `setData` sends for the macro block — calories, proteins, lipids and `hungChange` — server→client (run `td1-20260910-192457`); `carbohydrates` went 0 → 0, which carries no information, so its packet membership stays C |
| `thirstChange` | **yes, but lossy** — `setData` sends `getThirstChange()`, the *cooked-ladder* getter, and `applyItemStats` stores it with `setThirstChange`, i.e. as the **raw** field: 0.2 → 0.1 on the wire → 0.05 on read. One halving per server→client hop; it converges | M (runs `td1-20260910-192457`, `td1b-20260910-202029`; FILTER 9) |
| `actualWeight` | **yes, by a different getter** — `setData` fills the field from `getActualWeightUnmodded()`, not `getActualWeight()`, so which value arrives depends on a guard the sender may have moved | M (run `td1b-20260910-202029`); C (jar, `Food.getActualWeight`) |
| `rotten` `age` `fresh` `offAge` `offAgeMax` `freezingTime` `hungerChange` `isCookable` `weight` `customWeight` `lastCookMinute` | **no.** `age` and `offAge`/`offAgeMax` are measured not to cross; `isCookable`/`isCustomWeight` are measured to stay wrong on the client; `hungerChange` is a read-time ladder getter, not a field (the packet carries the raw `hungChange` instead); `rotten` and `fresh` derive from `age` | M for `age`, `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` (runs `exp02-20260910-030433`, `td1-20260910-192457`); C for the rest (the `setData` getter list) |
| `id` | **carried, as addressing** — not state. `setData` reads the field `InventoryItem.id` (`@67`) straight into the packet's own `id` (`@70`), which is how the receiving side finds the instance the rest of the payload is about; it is not a value a mod should treat as synced item state | C (jar, `ItemStatsPacket.setData @65-@70 L162`, read 2026-09-11) |

| Other member | Side | Syncs? | Reading | Ev |
|---|---|---|---|---|
| `getModData()` on an item → `KahluaTable` | both hold a copy | **yes**, item modData is in the sync set | reached as `item:getModData()`; the return type is a `KahluaTable`, so it is Lua-shaped on both sides | C (jar, `InventoryItem.getModData()Lse/krka/kahlua/vm/KahluaTable;`) |
| `syncItemFields()` | measured **client→server only** | — | mod B writes `imd.TKX_fibre = 12.5` then `syncItemFields()` on a `Base.Cheese` (`testing/experiments/TKX_Nutrient/42.20/media/lua/server/TKX_Nutrient_Server.lua:28-29`). Both sides read the key at the first census, 3 s after the spawn — **but the write came from the client VM**: `TKX_Nutrient.itemWrites` was **1 on the client and 0 on the server**, i.e. the client's copy of the `server/` file got there first and the server's tick then skipped on its own "already done" guard. So what this measured is a **client-side** item-modData write reaching the server; the server→client direction of `syncItemFields` is **untested here** | M (`x121-20260911-030023` keys `phases.M7.before` / `.after` / `.mod_globals`), bounded as stated |
| `getActualWeightUnmodded()` | both | the field travels; the **value** depends on the sender's own guard | it returns **0** whenever `getDisplayName().equals(getFullType())` — the slice-09 display-name guard, re-confirmed on the client in `x121`: `TKX.FibreBarJson` read `getDisplayName "TKX Fibre Bar Json"` and `getActualWeightUnmodded 0.3` on the **client**, while the same instance on the **server** read the name as the fullType and the weight as **0**, because a dedicated server resolves no display name at all. Never read this as a weight fact | M (`x121-20260911-030023`, JSON path `phases.M4.items["TKX.FibreBarJson"].witness`) |
| `sendItemStats(item)` | server only | it is the push | it is `GameServer.sendItemStats`; on a client it is a silent no-op, and there is no client→server "push my item fields" API | M (spike S6) |

### `IsoPlayer` / `IsoGameCharacter`

| Member | Side | Syncs? | Reading | Ev |
|---|---|---|---|---|
| `getModData()` → `KahluaTable` (`IsoObject.getModData`) | both hold a copy | **not until someone transmits** | the durable per-character store, and the only one a mod can add keys to | C (jar) + M ([patterns.md](patterns.md) § Measured MP sync facts, spike S6) |
| `transmitModData()` — **client → server** | either side may call it | **whole-table wipe and replace** | `x121` planted `TKX_ServerOnly` on the server, transmitted from the client, and the key was gone 1.27 s later while the client's keys arrived; the server's key set became *exactly* the client's | M (`x121-20260911-030023` key `phases.M9`) at n = 2 with `td2-20260910-231655`; mechanism C (`ObjectModDataPacket.write`, `KahluaTableImpl.load @0-@6 L332-L333` wipes before it rawsets) |
| `transmitModData()` — **server → client** | server | **the same shape in the other direction**, measured for the first time in slice 12 | after a server-driven transmit the client **lost** `TKX_eat_onEat_client` and `hotbar`, **gained** `TKX_eat_onEat_server`, and the server-only residual was empty. Graded after setting aside the one key the client's own handler rewrites each tick | M (`x121-20260911-030023` key `phases.M6.after_transmit`), n = 1 |
| the routing itself | both | both directions are real; neither is a merge | `IsoObject.transmitModData @0-@7 L4850-L4851` **returns silently** if the object's square is null; otherwise `@8-@28 L4853-L4854` sends `ObjectModData` on a client and `@31-@38 L4855-L4856` calls `GameServer.sendObjectModData` on a server | C (jar, 2026-09-11) |
| `getModData()` writes from a `server/` file | **lands in the client VM too** | n/a | mod B's `server/` file wrote `TKX_fibre` into the client's own copy of player modData, and mod C's `shared/` probe wrote `TKX_eat_onEat_client`, because a `media/lua/server/` file executes in the MP client's Lua state (§ MP behaviour) | M (`x121-20260911-030023` key `phases.M7.mod_globals.client`) |
| `hasTrait(CharacterTrait)` | both | traits are character state; **not** in `PlayerStatsPacket` | the jar exposes only `hasTrait(CharacterTrait)` and `hasTrait(CharacterTrait[])` — **there is no string overload**. The game's own Lua route is `char:getCharacterTraits():add(CharacterTrait.X)`, so a string argument is exactly the argument mismatch § 5 tells you not to make; the harness reads traits back off the trait *list* instead, never through `hasTrait` (`PZTestKit_Server.lua:227-274`) | C (jar method list, 2026-09-11) |
| `getXp()` then `XP.getXP(Perk)` | server owns the value | perk level reaches the client within one bus round trip | **two calls, never one**: `IsoGameCharacter.getXp()` is zero-argument and answers the inner `IsoGameCharacter$XP` object; the number comes from `XP.getXP(PerkFactory$Perk)F` on *that* object. There is no single getter — which is precisely why `witness.fields` (zero-argument getters only) cannot read XP, and why the harness has a dedicated `perk.xp` (`PZTestKit_Server.lua:89-110`) | C (jar method lists, 2026-09-11); M for the level reaching the client (run `exp02-20260910-030433`) |

### `ScriptManager` and the script `Item`

| Member | Side | Reading | Ev |
|---|---|---|---|
| `getScriptManager():getItem(fullType)`, fallback `FindItem(fullType)` | both — **script data is loaded per side and never synced**, so the two sides' definitions are two readings | the harness tries `getItem` first, then the form the game's own Lua uses; it records which one answered (`PZTestKit_Core.lua:219-222`) | C (jar: `getItem(String)Item`, `FindItem(String)Item`, `FindItem(String,Z)Item`); M for the two sides agreeing field for field on a mod item (run `td1-20260910-192457`, key `item_script`) |
| the four macros on the **script** object | **unreadable from Kahlua, both sides** | the script `Item` carries `getHungerChange()`, `getDaysFresh()` and the rest, but there is **no** `getCalories` / `getCarbohydrates` / `getLipids` / `getProteins` on it. The values exist as **public fields**, which is why `Item.InstanceItem @745-@778 L1578-L1581` reads them with `getfield` straight into the `Food` instance — and Kahlua publishes methods, not fields. All three routes (`get<X>`, `is<X>`, the bare field) come back absent on **both** sides for all four keys, on vanilla and mod items alike. Per-item macro numbers must come off an **instance**, or out of the script text | M (`x121-20260911-030023` key `phases.M1.script_access`, four items × two sides, re-confirming slice 01 and `td1-20260910-192457`); C (jar method list + `InstanceItem`) |

## 3. Script-side hooks

Three hooks can be named from inside an item block. They do **not** share a resolution rule,
and that is the trap.

| Hook | Declared as | How the name resolves | Fires on | Ev |
|---|---|---|---|---|
| `OnEat` | `OnEat = <name>,` in the item block (`testing/experiments/TKX_EatHook/42.20/media/scripts/tkx_eat_hook.txt:22`) | `IsoGameCharacter.Eat @762-@802 L5811-L5814`: `LuaManager.getFunctionObject(food.getOnEat())` → `LuaCaller.pcallvoid`. **`getFunctionObject` takes a global function NAME** — a local or a table member is simply never found | **both sides** — one call each on a single whole-item eat, `lastFraction` 1. One eat at `fraction 1` cannot separate "once per eat" from "once per portion", which is what the `fraction` reading exists for; that stays open. The client's call comes from the packet twin `IsoGameCharacter.EatOnClient @0-@57 L5725-L5736`, which fires the hook and applies **no** numbers | M (`x121-20260911-030023`, JSON path `phases.M5.globals`, both sides — `TKX_EatHook.calls` 1 client and 1 server, `lastSide` `client`/`server`, `lastFraction` 1; the claims file labels this `phases.M5a`); C (jar) for the mechanism |
| `OnCooked` | `OnCooked = <name>,` | **a different route**: `Food.update @627-@718 L462-L467` does `LuaManager.env.rawget(getOnCooked())` → `LuaCaller.protectedCallVoid(item)`, and if the name contains a `.` it **splits on the dot** and does a two-level `rawget`, so `Table.func` works here and does not work for `OnEat` | inside `Food.update`'s cook block — **not** server-gated in the dispatch itself, but reached only by the side that actually runs the cook transition. On both LTP sessions every hook print was in the **server** console and the client's was empty, because the client's copy never reached the transition | C (jar, 2026-09-11, matching the slice-09 read); M for the server-side firing (runs `td1-20260910-192457` / `td1b-20260910-202029`) |
| `OnCreate` | `OnCreate = <name>,` → the script `Item`'s `getLuaCreate()` | `InventoryItem.initialiseItem @0-@35 L4214-L4221`: `getLuaCreate()` → `LuaManager.getFunctionObject` → `LuaCaller.protectedCallVoid(item)`, signature `fn(item)`. Same global-name rule as `OnEat` | at instantiation, once — `Item.InstanceItem @4051-@4063 L1943-L1947` calls it only when `isInitialised()` is false. It therefore fires on **whichever side instantiates**, and item scripts load on both | C (jar, 2026-09-11) — **not exercised by any session in this library** |

**The practical rule.** Define the target as a bare global function, not a local and not a
table member: `TKX_OnEatProbe` is a global on purpose
(`testing/experiments/TKX_EatHook/42.20/media/lua/shared/TKX_EatHook.lua:41`), and putting the
file in `shared/` is what makes both states define it. If you want the hook to run on **one**
side, branch inside it — the file's folder will not do it for you (§ MP behaviour).

**Where to intercept an eat in MP.** `ISEatFoodAction:complete()` runs **server-only**, and a
Lua wrapper of it fires **before** `OnEat`: `x121` read
`TKX_EatHook.order == "complete onEat "` on the server and `"onEat "` on the client, with
`completes` 1 / 0 and `lastComplete "Base.Banana"` server-side only. So a mod that needs the
food item **intact, before `IsoGameCharacter.Eat` consumes it** has to sit in the wrapper, not
in `OnEat` — and the wrapper installs on the client too, where it stays silent
(M — `x121-20260911-030023`, JSON path `phases.M5.globals`, n = 1; the claims file labels this `phases.M5b`).

## 4. The command bus — the harness's own API, and the model for ours

**[`../testing/README.md`](../testing/README.md) § Command bus is the authority on the command
inventory.** It is not restated here, and it should not be copied anywhere else — it moves.

What the bus is *for*, in two roles:

1. **The instrument.** Every `M` row in this file was taken through it: a file-backed
   request/ack channel that both sides answer, with the reflective trio
   (`witness.fields`, `witness.moddata`, `lua.global`) doing the reading so a new subject needs
   no new command. Two slice-12 commits touched it: **`ad683fe`** moved `text.get` into
   `shared/PZTestKit_Core.lua` so **both** sides answer it, and **`5d9633f`** added the
   null guard that distinguishes a Java `null` return from a translation miss. Read a reply
   carrying `null: true` as **INCONCLUSIVE — not a miss**: it says the lookup route answered
   nothing at all, where a miss returns the key itself. The guard has **never fired** across
   `x121` and `x124` — 0 replies carrying `null: true` — so it is untriggered, not confirmed.
2. **The model for our own protocol (KEEP 2).** `sendClientCommand(player, module, cmd, args)`
   → server `OnClientCommand` → validate → mutate → `sendServerCommand` back. The harness is
   the smallest working example of it in this repo (`PZTestKit_Client.lua:100-111` sending,
   `PZTestKit_Server.lua:517` receiving, `:514` replying). Server validates; client predicts at
   most. For a nutrition mod this is not a style choice: the eat completes on the server, so
   any nutrient math has to run there and be pushed.

The bus also answers **with no client attached** (server `ping` → `pong` in 1.51 s, `TK.version`
1, 10/10 echo checks — M, `x123-20260911-034426` / `x123b-20260911-034500`), which is what makes
server-only counterfactuals cheap.

## 5. What Kahlua cannot do

B42's Lua is Kahlua, not PUC Lua. These are the rules every file in this repo is written to.

| Limit | Consequence for a mod | Ev |
|---|---|---|
| **Calling a nil member raises** — `pcall` catches it; an unguarded call does not | index first, then call: `TK.call(obj, name, …) → (present, value)` (`PZTestKit_Core.lua:126-131`), and **every Lua file in the experiment mods that touches a Java member carries its own six-line `tkxCall`**, so a mod never depends on the harness being installed (`TKX_EatHook.lua:12`, `TKX_EatHook_Server.lua:22`, `TKX_Nutrient.lua:13`, `TKX_Nutrient_Server.lua:13`, `TKX_Nutrient_Client.lua:10`). The raise itself is a bare `RuntimeException("tried to call nil")` at `KahluaThread.call(I)I @25-@39 L141-L142`, with the interpreter's own sites at `luaMainloop @3041-@3044 L765` and `@3340-@3343 L842` going through `KahluaUtil.fail` / `luaAssert`. **What `pcall` does and does not save you from is measured — the rule is the block below this table, and it is written once** | C (jar, 2026-09-11) for the raise sites; M (`x126-20260911-045205`, `x127-20260911-052049`) for the rule below |
| **An argument-arity (or ambiguous-overload) mismatch raises the same way** | `witness.fields` takes **zero-argument getters only** and passes nothing to the member it reads (`PZTestKit_Core.lua:558-562`); a nil into an overloaded member is the same trap — `getFirstTypeRecurse` is overloaded `(String)` / `(ItemKey)`, so the harness refuses a nil id before the lookup rather than paying for the dispatch. Whatever the Java member throws comes back out as a `RuntimeException` carrying the class name (`KahluaThread.call(I)I @70-@102 L149-L150`), i.e. the same shape the block below describes — **not measured here**, because the practice is to never make the call | C (harness code, the jar's overload lists, and that re-throw site, 2026-09-11); the practice is why no slice-08–12 session lost a side to it |
| **`isServer()` / `isClient()` still get a nil check before `pcall`** | not because the raise escapes — it does not — but because `pcall(nil)` comes back as a *failure that names nothing*, so "the global is absent" and "the global threw" are the same reply. Every experiment mod resolves its side as `if isServer ~= nil then pcall(isServer) …` (`TKX_EatHook.lua:27-36`), which turns absence into a branch instead of an error string | M (`x126-20260911-045205`, `phases.reads.client.values.err` / `phases.reads.server.values.err` = `tried to call nil java.lang.RuntimeException`, with `names_the_global: false` under `verdicts.P21_client` / `verdicts.P21_server`) for the catch and the silence; C (the mods' own code) for the practice |
| **No `goto`** | loops and early-outs only — a standing harness rule, obeyed by every Lua file in this repo | C ([`../testing/README.md`](../testing/README.md), the scenario section's *same Java rules* bullet) |
| **`%d` on a float raises** | never format a Lua number with `%d`; the harness formats integers through a `%.0f` branch with its own `1e15` cut-off (`PZTestKit_Core.lua`, `TK.json`) | C (same standing rule and the same bullet) |
| **`#` does not work on a Java list** | walk `size()` / `get(i)` from 0 — mod B does exactly that for both the online-player list and an inventory (`TKX_Nutrient_Server.lua:33-45`) | C |
| **`pairs()` on a Java-backed object raises** | `lua.global`'s walk takes a hop only when the node is a `table`, and gates `keyCount` on `type(v) == "table"` (`PZTestKit_Core.lua:794`) | C |
| **`string.format` is Kahlua's own** | its `%g` is `StringLib.appendSignificantNumber` + `roundToSignificantNumbers`, a reimplementation whose exactness cannot be established from the bytecode — so it is **not** Java's `%g`. The bus renders numbers with `tostring` instead (`KahluaUtil.numberToString` → `Double.toString` for a non-integral double, which round-trips exactly), since `291f977` | C (jar) |
| **A sentinel for a wrapped vanilla method must live OUTSIDE any table the shared file re-creates** | `TKX_EatHook.lua:19` re-creates `TKX_EatHook` by plain assignment on every load, so the wrap sentinel lives in its own global `TKX_EatHook_Installed` (`TKX_EatHook_Server.lua:31`). Kept inside, a `reloadlua` of the shared file would wipe it while the old wrapper was still installed, and the next install would wrap the wrapper | C (the mod's own code and its reasoning; the `wrapAt "file"` reading on both sides is consistent with a single wrap per VM) |
| **(not a Kahlua limit — a loader fact, listed here because it bites the same code)** a mod's `media/lua/server/` file runs in the **MP client's** Lua state too | resolve the side at runtime (`isServer()`, nil-checked as above) instead of trusting the folder; "only my server file writes this" is false until the guard is there. § MP behaviour owns the row, the three witnesses and the bound | M (`x121-20260911-030023` key `phases.M7.mod_globals.client`; n = 1 session, incidental, mechanism untraced) |

**The nil-call rule, measured (sessions 6 and 7).** The one place this file states it.

- **`pcall` catches it — both shapes.** The argument slot (the `TK.call` / `tkxCall` shape)
  returned `false, "tried to call nil java.lang.RuntimeException"` on **both** sides,
  byte-identical and on both passes (**M**, `x126-20260911-045205`,
  `phases.reads.<side>.values.ok` / `.err`, `verdicts.P21_client` / `P21_server`; n = 1 session,
  two passes 12 s apart); the nested shape `pcall(function() SomeNil() end)` returned
  `false, "Object tried to call nil in pcall java.lang.RuntimeException"` with the lines after
  it still running (**M**, `x127-20260911-052049`, `phases.reads.server.values.nested_ok` /
  `.nested_err` / `.nested_tail`, `verdicts.P22_server`; **server VM only**, two passes). Quote
  the **whole** string, class name included.
- **Why it catches (C, jar 2026-09-11).** `KahluaThread.call(I)I` loads the callee
  (`@14-@23 L139`), branches (`@25 ifnonnull 40`) and **throws** (`@30-@39 L142`) — no "returns
  false without raising" arm exists. `BaseLib.pcall @0-@10 L313` enters
  `KahluaThread.pcall(I)I`, whose try covers that `call` (`@80-@85 L1740`) **and** the nested
  `luaMainloop` it runs after pushing a frame (`@145`, `@155-@158 L162`) — which is why both
  shapes are caught; its `Throwable` arm (`@189-@213 L1758-L1760`) concatenates `getMessage()`
  with `getClass().getName()` beside `Boolean.FALSE` (`@256-@276 L1768-L1769`), the only
  producer of the observed string.
- **Unguarded, it aborts the rest of that handler's body** (`raw_tail` `"0"`) **but not the
  handlers behind it** (`behind` +17 in lockstep with `before`) — **M**, x127,
  `phases.reads.server.values.raw_tail` / `.behind` / `.before`, `second_pass.deltas.server`,
  server VM only; mechanism **C** (`Event.trigger`, § 1).
- **The silence is about the *name*, and only one shape is quiet.** x126's argument-slot catch
  printed nothing at all in either console — `names_the_global: false`
  (`verdicts.P21_<side>.observed.err`), 0 hits for the probe's global, for `attempted to call`
  and for `ExceptionLogger` (`greps.*`) — because that raise is `call`'s direct `athrow` and
  never reaches `KahluaUtil.fail`. Both x127 shapes are **logged in full** (73 engine hits each
  for `… in pcall` and `… in Add` — `greps_final.<pattern>.server.engine_count`). What no log
  ever prints is the **name** (`TKX_DefinitelyNilThree` / `…Too`: 0 hits on both sides —
  `greps_final.*`, `phases.engine_log_signature.per_side.*.names_the_global`) — **M** — because
  `luaMainloop` builds the message as `"Object tried to call nil in " + closure.prototype.name`
  before calling `fail` (`@3020-@3035 L763`, fallback `"… in unknown"` `@3041-@3044 L765`,
  **C**): it names the enclosing closure, never the missing global.
- **So the guard stays, reason rewritten.** Index first, call second — not because `pcall`
  fails to catch, but because a nil call never says **which** member was nil, aborts the body it
  sits in when unguarded, and on a `-debug` client is session-ending (below). The slice-08
  outage `exp01-20260909-235420` (the client stopped answering the bus) is explained by *the
  raise aborted the bus-pump handler's body every tick* — that run predates the artifact
  convention and has **no committed JSON**, so the explanation is **C**, never a measurement.
- **A `-debug` client does not survive one: it parks in the Lua debugger.** On two independent
  boots the harness client reached `in_game`, printed one complete trace, then stopped — console
  dead, `ready` never printed, bus never answering, process alive (**M**, x127, `client_ready`,
  `summary.client_bus_answered`, `bus_dead.client`, `verdicts.P22_client` = `unmeasured`,
  n = 2 boots). The route is `KahluaUtil.fail(String)` and the two sides took different arms of
  it: it tests `Core.debug && UIManager.defaultthread == LuaManager.thread` (`L95`), and on the
  true arm prints `Lua fail. Message: %s` (`L96`) and calls
  `UIManager.debugBreakpoint(currentfile, currentLine − 1)` (`@35-@50 L97`) **before** the
  `athrow` at `@53-@61 L100`. The client's log carries that `L96` line and never the throw, the
  server's only the throw (**M**,
  `phases.engine_log_signature.per_side.{client,server}.h1_message_first_hit`), so the client
  never left `debugBreakpoint` — which returns unless `showLuaDebuggerOnError` (`L1173`), returns
  at once on a `GameServer.server` (`L1183`, so no server ever breaks), else swaps
  `defaultthread` to `LuaManager.debugthread` (`L1192-L1193`), calls `DoLuaDebuggerOnBreak`
  (`@300 L1239`) and enters the modal `UIManager.sync.begin()` pump (`@331-@334 L1244`), **C**.
  The harness launches its admin client with `-debug` (`testing/pzt/client.py:137-139`);
  **negative control**: x126's same debug client never froze, because that shape never reaches
  `fail`. So **"any Lua error freezes a debug client" is false** — one routed through `fail`
  does, and **catching it does not help**: x127's *caught* nested raise took the same route, so
  on a debug client only the index-first guard, which never raises at all, keeps you alive.
  Open: the **release** client (`Core.debug`-gated — C, unmeasured) and what sets
  `showLuaDebuggerOnError`.

## 6. Removed or absent on 42.20.4

Each of these is a live hazard, not trivia: a shipped mod still calling one **raises**, and an
unguarded raise aborts the rest of the handler body that reached it — without ever naming the
member (§ 5).

| API | Jar reading (2026-09-11) | Still called in the corpus by | Ev |
|---|---|---|---|
| `loadstring` | present only as a dead string constant in `LuaCompiler`, `BlockingKahluaThread` and `UIDebugConsole` — not reachable from mod Lua | **nobody** — the corpus sweep (2026-09-10, 230 mods) counts **0** users, and `tools/mod_lint.py` keeps it there with an ERROR rule | C (jar) + M (the sweep, [`../testing/profiles.md`](../testing/profiles.md)) |
| `HasTrait(String)` | `IsoGameCharacter` exposes **only** `hasTrait(CharacterTrait)` and `hasTrait(CharacterTrait[])` | AutoCook, in shadowed `common/` copies: `common/…/AutoCook.lua:39` and `common/…/ISCharacterCook.lua:50,221` | C (jar method list) + M for the copies being unexecuted on the window-build path (run `td3-20260911-001948`) |
| `getTypeString()` | absent from **both** `zombie/inventory/InventoryItem` (which has `getType()` and `getGunTypeString()`) and `zombie/scripting/objects/Item` | AutoCook, `common/…/AutoCook_AutoCraftRecipes.lua:39` | C + M (same run) |
| `zombie/inventory/ItemUser` | the class exists, but it is **not in `LuaManager$Exposer.exposeAll`'s constant-pool set**, where `InventoryItem` and `ItemContainer` both are — so Kahlua cannot reach it | nobody; slice 06 had to reproduce `ItemUser.UseItem`'s per-use arithmetic with `setCurrentUses` instead ([decisions.md](../decisions.md), 2026-09-10) | C |
| `Stats.getHunger()` / `getThirst()` | `zombie/characters/Stats`'s method list contains **neither name** — hunger and thirst are reached as `getStats():get(CharacterStat.HUNGER)` | **no corpus user recorded** — and no sweep has looked for this member specifically; the survey's `getHunger*` hits are all `InventoryItem.getHungerChange`, a different member. The B41 idiom appears in this repo's own slice-01 plan text, which is why every harness snapshot records `statsApi` | C |
| the script `Item`'s macro getters | no `getCalories` / `getCarbohydrates` / `getLipids` / `getProteins` on `zombie/scripting/objects/Item`; they are public fields, read by `InstanceItem` with `getfield` | n/a — this is an absence every mod hits, including ours | M (`x121-20260911-030023` key `phases.M1.script_access`) + C |
| the **B41 translation layout** `ItemName_EN.txt` | not loaded on 42.20.4 | mod A ships both layouts side by side as the discriminator: the item declared only in `ItemName_EN.txt` (`TKX.FibreBarNamed`) read its name as the **fullType** on both sides, while the one declared in B42's `ItemName.json` (`TKX.FibreBarJson`) resolved on the client | M (`x121-20260911-030023` key `phases.M4`), n = 1 each |

**And one route that is present but does not lead where you expect.** `getText` is **not** the
way to an item name on 42.20.4 under **either** key form: bare `Base.Apple`,
`TKX.FibreBarJson`, `TKX.FibreBarNamed` and the B41-prefixed controls all returned a genuine
miss (`miss: true`, `text == key`, no `null`, no `error`) on **both** sides — while the same
item read `getDisplayName() == "TKX Fibre Bar Json"` off the **instance**. The `ItemName.json`
table is loaded and working; it is the `getText` **route** that does not reach it
(M — `x124-20260911-035819` key `phases.O5`, n = 2 sessions for the prefixed form, n = 1 for
the bare form). Two bounds, both from the Task 6b review: every `x124` reply missed, so that
session carries **no in-run positive control** — soundness rests on slice 10's client-side IGUI
hit (`text.get IGUI_SS_BARTITLE_HAPPY` → `"Happiness"`, `miss: false`, run
`td2-20260910-231655`), a different session and an earlier harness shape; and **no** server-side
`text.get` has ever returned a hit (9 keys across `x121` + `x124`), which says the route
**answers** on the server, not that the server's table is populated. A dedicated server also
resolves **no display name at all**, JSON included. **Rule: gate a translation-dependent
feature on an IGUI key, never on an item name, and never branch on a name server-side.**

## MP behaviour

**`media/lua/server/` is not a server-only folder in MP.** In `x121` a mod's `server/` file
executed in the **client's** Lua state, on three independent witnesses: the shared table's
`side` field read `"server"` on the client, the `EveryOneMinute` counter read **58 client / 38
server** (two registered handlers in the client VM against one in the server's — consistent
with ~104 s of client uptime at 3.75 s per firing), and the item-modData arm's `itemWrites`
landed **1 on the client, 0 on the server**. Grade **M**, n = 1 session, **incidental** (no
probe was aimed at this — it fell out of three arms asking other questions) and **mechanism
untraced** — see the loader chain in [`anatomy.md`](anatomy.md). **Guard every `server/` file
with `isServer()`** (nil-checked, § 5) rather than trusting the folder; and treat
"only my server file writes this" as false until the guard is there.

**Everything the engine owns flows one way.** Client-side writes to `Nutrition`, to
`CharacterStat.HUNGER`/`THIRST`, and to any item field are overwritten or simply never leave
the client; server-side writes reach the client only for the fields `ItemStatsPacket` and
`PlayerStatsPacket` actually carry (§ 2). The exception is **player modData**, which is a
*client-writable* channel in practice: any client's `transmitModData()` replaces the server's
copy of that player's table wholesale, and slice 12 measured the mirror-image replacement in
the server→client direction. The mod that loses data is never the mod that called transmit.
**So: keep server-authoritative per-player state out of player modData** (a server-side table
plus `sendServerCommand`, or global modData), or guarantee the client's copy is complete before
anyone transmits (FILTER 10).

**Reads are pushes.** A client-side reader of a live item or nutrition field may be reading a
push rather than a simulation and must not assume either — `Food.update`'s cooking-branch
`sendItemStats` is gated on strict `heat > 1.6f`, and below that gate a client's held copy did
not advance at all over a measured 12.54 s window (run `td3-20260911-001948`;
[patterns.md](patterns.md) § Measured MP sync facts owns the graded row and its bounds).

## Discrepancies

- **RESOLVED 2026-09-11 — the nil-call rule was half right; the bytecode was right.** The rule
  said Kahlua's "tried to call nil" escapes `pcall` *and* kills the handler chain, against a
  bytecode reading (`KahluaThread.pcall(I)I`'s `Throwable` arm `@189-@213 L1758-L1760`, beside
  its `KahluaException` arm `@173-@186 L1755-L1757`) that said it should be caught. Both halves
  are now measured (§ 5): `pcall` **catches** (x126 both sides, x127 nested server-side — the
  quoted string is what `pcall` *returns*), and an unguarded raise **aborts its own handler's
  body** (right) **but not the handlers behind it** (wrong); the guard is kept for the rewritten
  reasons, not this one. Still lost: every client-side reading of `x127` (the `-debug` client
  parked in the Lua debugger — cause settled in § 5). Still ungraded: the slice-08 outage.
- **`getText` misses everywhere, yet `getDisplayName()` resolves.** Recorded above; the
  reconciliation is that the two do not share a route, and only the instance getter was ever
  shown to reach the table.
- **`x121`'s own `text.get` readings are superseded.** That session asked the B41 prefixed key
  form of a B42 table; its translation readings are do-not-cite, and `x124`'s bare-form probe
  is what this file quotes.

## Open questions

1. **How a `server/` file reaches the client's Lua state.** The outcome is M at n = 1; the
   loader step that maps it is unread. Until it is, `isServer()` is the only safe guard.
2. **`syncItemFields()` server→client.** Measured only client→server (above). The probe is a
   server-side item-modData write on an instance the client already holds, with the client's
   own copy of the `server/` file disabled by an `isServer()` guard so the direction is
   unambiguous.
3. **`OnCreate`.** Read off the jar only; no session has fired one. Worth a probe because it is
   the one hook that runs at *instantiation*, which is where a per-item nutrient field would
   most naturally be seeded.
4. **Whether any packet syncs `CharacterTraits`.** The weight-band traits are not in
   `PlayerStatsPacket` and nothing else has been traced; both sides' trait lists were empty in
   every run so far, so "no disagreement" is not an answer
   ([body-stats.md](../vanilla/body-stats.md) open question 10).
5. **What a *release* client does with a `KahluaUtil.fail` raise.** The debug-client break is
   settled (§ 5, C confirmed by M) and gated on `Core.debug`; nothing here has run a
   `debug=False` client, so the release path is **C, unmeasured**. The same run should settle
   what sets `UIManager.showLuaDebuggerOnError`, the break's other gate.
6. **The nil-call rule on the client, unguarded.** The body-abort / chain-survives half is
   **server VM only** (`x127`, because the debug client parked) — treat the client half as
   jar-supported (C) and unmeasured. Split any follow-up by raise **origin** (`call(I)I`'s
   direct `athrow` vs `luaMainloop` → `fail`), not by handler shape: both of `x127`'s handlers
   took the `fail` route, so that session cannot separate them.
7. **Whether a mod-registered `MoodleType` carries a Java effect.** `MoodleType.register` and
   `MoodleStat.register` exist on the jar — `MoodleType.register(String)`, `registerBase(String)`,
   `register(boolean, String)` and `MoodleStat.register(MoodleType, F, F, F, F, F)`, read
   2026-09-11 — and `MoodleType` is Lua-exposed (the harness reads `MoodleType.FOOD_EATEN` at
   `PZTestKit_Client.lua:436`), but nothing here has registered one, so whether a
   mod-registered type carries any Java effect is unmeasured.

## Sources

- **Slice-12 sessions**, all on build 42.20.4 with a real dedicated server:
  `x121-20260911-030023` (overrides / eat hooks / custom nutrient fields — JSON paths
  `phases.M1`, `M4`, `M5`, `M6`, `M7`, `M8`, `M9`, plus the top-level `m8` block the claims
  file names), committed at
  [`testing/artifacts/x121-20260911-030023/platform-overrides.json`](../../testing/artifacts/x121-20260911-030023/platform-overrides.json);
  `x124-20260911-035819` (key `phases.O5`, the `getText` key-form probe), at
  [`testing/artifacts/x124-20260911-035819/platform-order.json`](../../testing/artifacts/x124-20260911-035819/platform-order.json);
  `x123-20260911-034426` / `x123b-20260911-034500` (the server-only bus readings), at
  [`testing/artifacts/x123-20260911-034426/platform-folder.json`](../../testing/artifacts/x123-20260911-034426/platform-folder.json);
  `x126-20260911-045205` (the `pcall` probe — `phases.reads.<side>.values.{ok, err, tail,
  behind, ctrl_ok, ctrl_err}`, `verdicts.P21_client` / `P21_server` incl.
  `observed.err.names_the_global`, `summary.values.<side>`, `second_pass`, `greps.*`), at
  [`testing/artifacts/x126-20260911-045205/platform-pcall.json`](../../testing/artifacts/x126-20260911-045205/platform-pcall.json);
  `x127-20260911-052049` (the raise probe — `phases.reads.server.values.{nested_ok, nested_err,
  nested_tail, raw_tail, behind, before}`, `second_pass.deltas.server`, `verdicts.P22_server`,
  `verdicts.P22_client` (`unmeasured`), `greps_final.<pattern>.<side>.{count, engine_count}`,
  `phases.engine_log_signature.per_side.*`, `client_ready`, `summary.client_bus_answered`,
  `bus_dead.client`), at
  [`testing/artifacts/x127-20260911-052049/platform-raise.json`](../../testing/artifacts/x127-20260911-052049/platform-raise.json).
  Do-not-cite, and obeyed here: every client-side *reading* of `x127` (its bus never answered),
  its `summary.sides_agree`, both runs' `server_error_count` as a fault count. The freeze's
  **cause** became citable with the Task 6e review (C confirmed by M); only the **release**-client
  behaviour stays uncitable.
  `x122-20260911-032326` is cited by [`anatomy.md`](anatomy.md), not here.
- **Earlier measured rows quoted by run id, not re-graded here:** spike **S6**
  (`spike-20260909-143930`, `spike-20260909-144417`), `exp01-20260910-000351`,
  `exp01-20260910-003929`, `exp02-20260910-030433`, `exp03-20260910-045523`,
  `td1-20260910-192457`, `td1b-20260910-202029`, `td2-20260910-231655`,
  `td3-20260911-001948`. Their graded statements and bounds live in
  [`patterns.md`](patterns.md) § Measured MP sync facts and in the teardowns under
  [`../mods-survey/teardowns/`](../mods-survey/teardowns/); the *do not cite* list for every run
  is [`../../testing/artifacts/README.md`](../../testing/artifacts/README.md).
- **Jar** (`projectzomboid.jar`, 42.20.4, read 2026-09-11 with `pz-b42/pz.sh`):
  `Nutrition.updateWeight @0-@350 L138-L199` and the `Nutrition` method list;
  `IsoGameCharacter.Eat @762-@802 L5811-L5814`; `IsoGameCharacter.EatOnClient @0-@57
  L5725-L5736`; `Food.update @627-@718 L462-L467` (the `OnCooked` dispatch);
  `InventoryItem.initialiseItem @0-@35 L4214-L4221`; `Item.InstanceItem @745-@778 L1578-L1581`
  and `@4051-@4063 L1943-L1947`; `IsoObject.transmitModData @0-@38 L4850-L4856`;
  `ItemStatsPacket.setData`'s getter list and its `@65-@70 L162` id copy;
  `LuaManager.getFunctionObject(String)` and
  `LuaManager$Exposer.exposeAll`'s class set; `KahluaThread.call(I)I @14-@39 L139-L142`,
  `@70-@102 L149-L150` and `@145-@158 L157-L162`, `BaseLib.pcall @0-@10 L313`,
  `KahluaThread.pcall(I)I @80-@85 L1740` and `@173-@276 L1755-L1769`,
  `KahluaThread.luaMainloop @3020-@3035 L763`, `@3041-@3044 L765` and `@3340-@3343 L842`;
  `KahluaUtil.fail(String) @0-@61 L95-L100`; `UIManager.debugBreakpoint(String,J)`
  `L1173` / `L1183` / `L1192-L1193` / `@300 L1239` / `@331-@334 L1244`;
  `zombie/Lua/Event.trigger @89` / `@194-@198 L41-L42` /
  `@216-@219 L31` / `@276`; and the method lists of `Stats`, `IsoGameCharacter`,
  `IsoGameCharacter$XP`, `InventoryItem`, `Food`, `ScriptManager` and
  `zombie.scripting.objects.Item` (the absences in § 6).
- **This repo's own code, cited by path and line:**
  `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`,
  `…/server/PZTestKit_Server.lua`, `…/client/PZTestKit_Client.lua`, and the five experiment
  mods under `testing/experiments/TKX_*` — `TKX_ItemOverride`, `TKX_Nutrient`, `TKX_EatHook`
  and `TKX_CommonOnly` added in `f36a860` and fixed in `de10855`; `TKX_ZWatermelon` added in
  `f6c336e`. Harness commits touched by slice 12:
  `ad683fe` (`text.get` moved to `shared/`) and `5d9633f` (its null guard).
- **Wiki (W), corroboration only:**
  [`../../references/wiki-mirrors/lua-event.md`](../../references/wiki-mirrors/lua-event.md),
  PZwiki *Lua_event*, page version 42.20.4, **fetched 2026-09-10** — the boot order and the
  client-only / server-only markings on `OnCreatePlayer`, `OnGameStart`, `OnLoad`,
  `OnServerStarted`, `OnInitGlobalModData` and `OnGameBoot`.
- **Corpus counts**, recomputed **2026-09-10** over the 230-mod inventory and a floor by
  construction: [`../mods-survey/approved-modlist.md`](../mods-survey/approved-modlist.md)
  § Event usage.
- **Neighbouring library docs:** [`anatomy.md`](anatomy.md) (the loader chain and the
  `server/`-in-the-client row), [`item-overrides.md`](item-overrides.md) (script redefinition
  and replay order), [`patterns.md`](patterns.md) (the graded MP sync tables and the KEEP/FILTER
  rows), [`../testing/README.md`](../testing/README.md) § Command bus (the authority on the
  command inventory), [`../vanilla/eating-pipeline.md`](../vanilla/eating-pipeline.md),
  [`../vanilla/nutrition-core.md`](../vanilla/nutrition-core.md),
  [`../vanilla/food-item-model.md`](../vanilla/food-item-model.md),
  [`../vanilla/body-stats.md`](../vanilla/body-stats.md).
