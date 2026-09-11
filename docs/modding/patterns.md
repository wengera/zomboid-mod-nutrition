# Patterns & anti-patterns — evidence from the approved corpus

**Verified against: 42.20.4 (`b0bbce05d5`)** — corpus read 2026-09-09; the measured
MP sync facts re-checked and the nutrition row corrected 2026-09-10 (slice 01);
slice-03 corrections 2026-09-10; the **server→client** sync table, the FILTER 1
addition and the first closed open question added 2026-09-10 (slice 09, the
LongTermPreservation4220 teardown); the modData-transmit wipe (FILTER 10), the
`updateWeight` flag half, the vanilla display-name control, the **contested**
client-copy row and the closed cadence question added 2026-09-10 (slice 10, the
simpleStatus teardown); the measured `common/`-vs-version-folder merge rule
(KEEP 10), FILTER 11, and the **per-arm resolution of that contested
client-copy row** added 2026-09-11 (slice 11, the AutoCook teardown).

Derived from the 230-mod inventory
([survey](../mods-survey/approved-modlist.md)) + line-level reads of
ItemQuality, BeyondTen, damnlib, KBW/ElyonLib, ChuckleberryFinn mods.
Rule of thumb throughout: **adopt what the well-behaved heavy mods converge
on; treat divergence as a decision point, not a free choice.**

## KEEP — patterns to adopt

1. **modData as the only durable mod state** (universal among survivors).
   Character/item/global modData saves and syncs on engine paths; live java
   fields are unsynced cache. Corollary from ItemQuality's failure: any live
   field you set must be *derivable* from modData and re-applied idempotently.
2. **The MP command bus**: `sendClientCommand(player, module, cmd, args)` →
   server `OnClientCommand` → validate → mutate → `sendServerCommand` back.
   20 mods client-side, 14 server-side — including the server's own stack.
   Server validates; client predicts at most.
3. **`OnInitGlobalModData` for world-scoped state** (14 mods) — the sanctioned
   init point for shared tables, before players exist.
4. **Idempotent monkey-patching with kept originals** (BeyondTen exemplar):
   `if target == BT._wrapper then return; BT._orig = target; target = wrapper`
   — safe under lua reload, unwindable, and composes when two mods wrap the
   same function. HorseMod (22 patch sites) shows the volume this reaches.
5. **Derived-on-read values** (BeyondTen): store XP/inputs in modData, compute
   levels/effects on read. No migrations when formulas change.
6. **Declarative config tables** driving generic engines (ItemQuality's stat
   categories; KBW's JSON buildable definitions at the extreme). Content
   changes then never touch logic.
7. **Cooperative framework detection** (BeyondTen×UCWF): if a framework owns a
   contested value (carry weight, moodles), register with it when present
   instead of last-write-wins. For us: MoodleFramework is server-approved —
   evaluate adoption before rolling our own moodle rendering.
8. **Heartbeat discipline**: prefer `EveryOneMinute`/`EveryTenMinutes` (10
   mods) for slow simulation (nutrient decay!), `OnPlayerUpdate` only for
   per-frame needs with cheap early-outs — 38 mods share that hook; be a good
   neighbor. `OnTick` is the expensive tier (14 mods) — avoid.
9. **Error hygiene at boundaries**: CleanUI (101 pcall), Economy (58),
   BeyondTen (47) wrap third-party/engine-boundary calls. A failed hook that
   throws kills every later handler on that event — pcall at the rim, fail
   soft, log.
10. **Version-folder layout** `42/` + `42.x/` overrides + `common/` (every
    mod on the list) with `mod.info` `require=` for dependency ordering
    (ChuckleberryFinn mods chain: SRJ → AlertSystem + errorMagnifier).
    **The combination rule is now measured** (slice 11, run
    `td3-20260911-001948`): the **version folder's file wins** a
    same-relative-path collision, `common/` supplies everything the version
    folder does not ship, and both end up in **one** Lua state — translations
    excepted, because `Translator` merges rather than resolving through
    `activeFileMap`. AutoCook's `42.13/` port is **three files / ~40 lines**
    against 1 238 shared lines in `common/`, and five independent readings
    agreed on the direction ([teardown](../mods-survey/teardowns/autocook.md)
    § Architecture). Two consequences worth adopting with it: **a
    `common/`-hosted entry point with a version-folder implementation** is a
    sound shape — one `Events.*.Add` in `common/`
    (`AutoCook_RISCookMenuInsertion.lua:117`) calling into the per-build body —
    and the inventory's per-mod numbers are computed over the **live folder
    only**, so a mod built this way reads as registering nothing (`top_events:
    []` for AutoCook is correct and misleading at once; `media_at` with two
    entries is the flag). The hazard on the other side is FILTER 11.
    **Outcome M** (n = 1 session, two independent halves), **mechanism C**
    (four jar sites), and bounded to a mod whose version dir actually ships
    colliding files.
11. **Script-first for item data; Lua only for what the packet can carry**
    (LongTermPreservation4220, measured — run `td1-20260910-192457`). Item
    scripts are loaded **per side and never synced**, so a value written in a
    script is identical on both sides for free: that mod's `DaysFresh = 53` is
    right everywhere, while the same shelf life written from Lua onto the live
    item (`setOffAge`) never leaves the server. Its `item.script` reply is field
    for field identical on both sides, which is what makes the split clean
    rather than inferred. Put our item pass in scripts, and reach for a
    server-side field write only when the field is in `ItemStatsPacket` or the
    value may stay server-only.

## FILTER OUT — anti-patterns observed or implied

1. **Unsynced-field authority** — ItemQuality's conditionMax lesson; the
   engine's sync packet list is the contract, verify per field.
   **Now measured end-to-end on a second mod**: a mod that writes an item field
   `ItemStatsPacket` does not carry depends on the **server copy alone**, and no
   amount of re-pushing repairs the client's. LongTermPreservation4220's
   server-side `OnCooked` hook writes **eleven** fields
   (`recipe_meats.lua:36-49`; the per-call table is in the teardown's
   § Architecture): **six** the packet carries — the four macros, `hungChange`
   and `actualWeight` — and **five** it does not: `isCookable`, `offAge`,
   `offAgeMax`, `weight` and `customWeight`. Six are carried (four measured intact; `carbohydrates` 0 → 0 carries no information; `actualWeight` arrives but see its row below); of the five, the
   four the client is left **permanently wrong** about are `offAge`,
   `offAgeMax`, `isCookable` and `isCustomWeight` (`weight` is uncarried but not
   desynced — both sides read 0.5, and "not carried" is not "desynced").
   Measured on both sides of one live dedicated server, on the two post-cook
   snapshots 11.1 s apart — the pre-cook baseline shows no desync at all
   ([teardown](../mods-survey/teardowns/longtermpreservation4220.md), run
   `td1-20260910-192457`). The corollary that bit *that* mod is sharper than the
   rule: writing an uncarried field (`setCustomWeight(true)`) also flipped which
   arm the server's own getter took, so its 30 % weight reduction was discarded
   on the authoritative side, not merely desynced.
2. **One-shot repair logic + observation trackers that overwrite truth**
   (ItemQuality's KnownCondition poisoning). Reconciliation must converge,
   not latch.
3. **Effective-level/local-variable injection for core math** (BeyondTen uses
   it for *bonuses*, acceptably) — each injection point breaks silently on
   game updates. Core nutrient math owns its own tick instead.
4. **Zero error-handling in huge codebases** — KBW/HorseMod/damnlib run 0
   pcall across 2MB+ lua; they get away with it via author discipline, but
   KBW's own bug thread (server-freeze on chunk load, T-junction silent
   failures) shows the cost. Not our style for an MP mod.
5. **`OnTick` for simulation** — 69 hook registrations concentrated in the
   heavy tier; nutrition has no business there.
6. **Data-as-lua at scale without laziness** (BaseQuests: 423KB of tables
   parsed at boot) — fine for a quest pack; our item-pass data belongs in
   script files or lazily-loaded modules.
7. **`loadstring` anything** — removed from the engine (42.20.x security
   fixes); corpus count is zero, keep it zero.
8. **Fighting resident UI mods** — CleanUI redraws status surfaces on this
   server; render through MoodleFramework/own panels, don't patch the same
   widgets it patches.
9. **Trusting a cooked food's *derived* getters to round-trip** (measured, runs
   `td1-20260910-192457` / `td1b-20260910-202029`). `ItemStatsPacket` sends
   `Food.getThirstChange()` — a value the cooked ladder has **already** been
   applied to — and the receiver stores it as the **raw** field, so a cooked
   item's thirst reads half on the client (0.2 → 0.1 on the wire → 0.05 on
   read), **one halving per server→client hop, and it converges** — there is no
   client→server item hop to compound it. `hungChange` is sent raw and is fine.
   This is vanilla's defect, not a mod's, and it lands on any mod that cooks
   anything in MP. Rule: read a food's numbers from the side that owns them, and
   never build our own math on a getter whose value is transformed again on the
   wire — check `setData`'s getter, not the field name. **Canonical graded
   row:** § Measured MP sync facts → *The other direction — server → client*,
   the `thirstChange` row; this entry is a copy and that row owns the numbers.
10. **Keeping server-authoritative state in player modData on a server that also runs a
    client-side transmitter** (**M** for the wipe — slice 10, run `td2-20260910-231655`; **C**
    for the seven-call-site half, which is a code read of `ISSSBar.lua` and was *not* exercised,
    because no bus command can synthesise the UI click each site needs). A client
    `player:transmitModData()` sends the **whole** table and the receiver **wipes before it
    rawsets** (`KahluaTableImpl.load @0-@6 L332-L333`), so the server's copy of that player's
    modData becomes *exactly* the client's: a key planted on the server only vanished on the
    first transmit, while the client's keys arrived. simpleStatus fires that transmit from
    **seven** UI-input handlers — a bar drag, a menu toggle, a font change
    (`ISSSBar.lua:274,282,290,297,307,476,540` → `:35`) — none of which knows anything about
    your keys. **Rule: player modData is a client-writable channel in practice. Either keep
    server-authoritative per-player state out of it (server-side table + `sendServerCommand`, or
    global modData), or guarantee the client's copy is complete before any client transmits.**
    The mod that loses the data is never the mod that called `transmitModData`, which is what
    makes this a FILTER rather than a note: our own state has to survive *someone else's*
    transmit. Full reading:
    [teardown](../mods-survey/teardowns/simplestatus.md) § MP handling.
    **Second subject, slice 11** (run `td3-20260911-001948`): AutoCook has **9**
    `getModData()` sites and **zero** `transmitModData`, and its whole nested
    `AutoCook` table still crossed to the server the first time something else
    on that client transmitted — the server's census became *exactly* the
    client's, `hotbar` included. "We never transmit" is not a guarantee about
    anything in player modData.
11. **Leaving a `common/` copy of a file the version folder shadows** and
    letting it rot (measured, slice 11, run `td3-20260911-001948`). Under
    KEEP 10's rule a `common/` file with a version-folder counterpart is
    **unexecuted code on that build**, and AutoCook's three shadowed copies
    have quietly accumulated calls the engine removed: `HasTrait(String)` at
    `common/…/AutoCook.lua:39` and `common/…/ISCharacterCook.lua:50,221`, and
    `getTypeString()` at `common/…/AutoCook_AutoCraftRecipes.lua:39` — none of
    which exists on 42.20.4. They are harmless **only** because the version
    folder wins, which nothing in the mod asserts and which this library had
    not measured until now; and a Kahlua "tried to call nil" is uncatchable, so
    the failure mode is not a degraded feature. It is **not "dying at file
    load"** either — none of the four calls sits at file scope. What would die
    is the character-info window as it is **built**, inside `createPlayerData`
    at spawn: `ISCharacterCook:createChildren` calls `AutoCook.init` at `:17`
    and `createCookingModeCombo` unconditionally at `:23`, and between them
    they reach three of the four sites (`AutoCook.lua:39` from `init`;
    `AutoCook_AutoCraftRecipes.lua:39` inside `initAutoCraftRecipes`, called
    from `init:53`; `ISCharacterCook.lua:221` inside `createCookingModeCombo`).
    The session's console grep returned **0** such raises, so the bounded
    confirmation is wider than one line: the whole **window-build** path did
    not execute the `common/` copies — load-bearing because
    `common/…/AutoCook.lua:38`, the line before the first site, demonstrably
    did, and the join-time census puts that path at `session_ready + 1.044 s`.
    Only `common/…/ISCharacterCook.lua:50` stays uncovered: it sits inside
    `prerender`, which needs the Cook tab rendered, and nothing on the bus
    opens it. **Rule: treat a shadowed `common/`
    file as unmaintained — delete it, or keep it building against the same API
    as the live copy; never let the live path depend on a merge direction you
    have not read out of the engine.** Full reading:
    [teardown](../mods-survey/teardowns/autocook.md) § Pitfalls 1.

## Measured MP sync facts (42.20.4, spike S6 — [testing/spikes.md](../testing/spikes.md))

Established with the sync witness on a real dedicated server + real client;
they sharpen KEEP 1–2 and FILTER 1.

| Change made on the client | Reaches the server? | Ev |
|---|---|---|
| `player:getModData().k = v` | **no** — until `player:transmitModData()`, then yes. **And the transmit is a whole-table WIPE AND REPLACE, measured** (2026-09-10, run `td2-20260910-231655`): a key planted on the **server** only (`pzt_ss_server`) was **gone** from the server's census after one client `transmitModData()`, while the client's own key and an unrelated `hotbar` arrived — the server's key set became *exactly* the client's. Mechanism (C, jar): `ObjectModDataPacket.write @8-@52 L42-L44` serialises the whole table and `KahluaTableImpl.load @0-@6 L332-L333` **wipes before it rawsets**; an empty sender's table wipes the receiver outright (`parse @126-@139 L76-L77`), and `transmitModData` returns silently if the player's square is null (`IsoObject.transmitModData @0-@7 L4850-L4851`). So a client transmit destroys any player-modData key the server holds and that client's copy lacks — see FILTER 10 | M (spike S6) for the arrival; **M** (run `td2-20260910-231655`, `wipe_reading`) for the wipe |
| `setCondition` / `setConditionMax` / `getModData()` on an inventory item, then `sendItemStats(item)` | **never** — `sendItemStats` is `GameServer.sendItemStats` (server → owning client, packet `ItemStats`); on a client it is a silent no-op. There is no client→server "push my item fields" API, and waiting 60 s changes nothing | M (spike S6) |
| `inventory:AddItem("Base.X")` client-side | **never** — the server's copy of the player's inventory (it does hold one: a server-side `additem` shows up on both sides with one id) never gains the item | M (spike S6) |
| nutrition (`getNutrition()` calories/weight/macros) | **never** — and it is overwritten. `Nutrition` is **server-authoritative**: the eat itself completes on the server, which pushes the whole object at eat time (`EatFoodPacket`) and once a second (`PlayerStatsPacket`). A client `setCalories(3000)` never reached the server and was back to the server's value inside 3 s; a server-side write reached the client inside 3 s. The 0.2 kcal agreement S6 measured is mirror lag, not client authority | M (run `exp01-20260910-000351`) |
| `getStats():set(CharacterStat.HUNGER / .THIRST, v)` client-side | **never** — same shape as nutrition: a client write to 0.9 was gone within 3 s while a server-side write to 0.4 reached the client. Re-measured with a tighter bound: a client write of 0.9 against a server pinned to 0.3 read back 0.9 at t = 0.51 s and **0.3004 at t = 1.42 s** — the revert lands inside 1.5 s, consistent with the 1 Hz push | M (runs `exp01-20260910-003929`, `exp03-20260910-045523`) |
| `getNutrition():setWeight(v)` client-side | **never — and the client cannot derive weight either.** `Nutrition.updateWeight` runs on the client but a `GameClient.client` skip (`@317–@320 L198`) sits before `setWeight` and before `applyTraitFromWeight`, so the client computes a weight delta, discards it, and **never applies the weight band traits**. A client `setWeight(105)` read back 105 with `hasTrait(Obese)` false, then reverted to the server's 80 within 3 s with `Obese` still false. Consequence for a mod (**inference, not measured**): the band traits are not in `PlayerStatsPacket`, and whether any *other* packet syncs `CharacterTraits` was not traced (open question 10 in [../vanilla/body-stats.md](../vanilla/body-stats.md)) — so evaluate anything keyed on Obese/Overweight/Underweight/Emaciated server-side, or feed it an explicitly transmitted value, as the safe default rather than a proven necessity. **Slice 10 measured the half of `updateWeight` that runs BEFORE that skip** (2026-09-10, run `td2-20260910-231655`): the three direction flags `isIncWeight` / `isIncWeightLot` / `isDecWeight` are set at `@129-@131 L167`, `@186-@188 L178`, `@222-@224 L181` and `@260-@262 L186` — all of them ahead of the `@317-@320 L198` skip — so a client **does** compute them, and they agreed with the server's on **both sides at all six snapshots**, matching the arm predicted from that snapshot's own macros. A client can therefore derive a weight *direction* it cannot derive a weight. Two caveats: both sides' trait lists were **empty**, so this is "no disagreement on a character with no band traits", not an answer to open question 10; and `setIncWeightLot(true)` fires on the ×2 arm as well as the ×3 (`updateWeight @194-@226 L179-L181`), i.e. from **carbs or lipids > 400**, not 700 — correct the threshold wherever 700 is quoted alone | M (run `exp03-20260910-045523`) for the client write/discard; **M** (run `td2-20260910-231655`, `grades[].flags`) for the flags agreeing on both sides; the 400 threshold is **C** (jar); the consequence is an **inference under C** — the `GameClient.client` skip and `PlayerStatsPacket`'s field list are code-read, the "so evaluate it server-side" step is our reasoning from them, not a separate measurement; mechanism and citations in [../vanilla/body-stats.md](../vanilla/body-stats.md) § MP behaviour |

### The other direction — server → client, on one item (slice 09)

The table above is a **client→server** table. Slice 09's teardown of
LongTermPreservation4220 is the first evidence the library has in the **other**
direction: a server-side hook rewriting an inventory item while a real client
holds the same instance (`getID` identical, `same_instance true` at every
snapshot). "Reaches the client" below means the two sides' getters agree to
within 1e-6, read on both sides through the same witness command.

| Change made on the server (a `Food` item in a player's inventory) | Reaches the client? | Ev |
|---|---|---|
| `setCalories` / `setProteins` / `setLipids` / `setCarbohydrates` / `setHungChange` | **yes, intact** — all five are in `ItemStatsPacket`, `hungChange` as the **raw** field, so each side ladders it once and both read the same `getHungerChange`. **Four** of the five are measured intact (calories 300→210, proteins 50→35, lipids 12→8.4, `hungChange` −0.6→−0.42); `getCarbohydrates` went 0 → 0 (×0.70 of zero), which carries no information, so *carbohydrates'* packet membership is **C**, read off `setData`, not measured | M (run `td1-20260910-192457`) for four; **C** for `carbohydrates` |
| `setOffAge` / `setOffAgeMax` / `setIsCookable` / `setCustomWeight` | **never** — none is among the packet's 43 fields. The client kept `offAge 53` against the server's 1e9 and `isCookable true` against `false`, on the **two post-cook snapshots 11.1 s apart** (the pre-cook baseline is not desynced at all), and nothing later repairs it | M (same run) |
| a cooked food's `thirstChange` | **yes, but halved.** `ItemStatsPacket.setData` sends `Food.getThirstChange()` — the *cooked ladder* getter — while `applyItemStats` stores it with `setThirstChange`, i.e. as the **raw** field, so the receiver ladders it a second time: 0.2 → 0.1 on the wire → 0.05 on read. A **vanilla** defect, surfaced by any mod that cooks anything in MP. It is **one halving per server→client hop and it converges** (a second push left the client at 0.05 with the server unchanged at 0.1) — compounding would need a client→server item hop, which the table above records as a silent no-op | M (runs `td1-20260910-192457`, `td1b-20260910-202029`) |
| `setActualWeight` | **the field travels** (`setData` fills it from `getActualWeightUnmodded()`), but read back the two sides disagreed **0 vs 0.35**. The display-name guard alone does not explain it: `getActualWeightUnmodded` returns 0 whenever `getDisplayName().equals(getFullType())`, and that was true on **both** sides for that mod item (false for a vanilla control, `Base.Steak`, 0.3 everywhere) — a symmetric guard cannot produce an asymmetric reading. What splits the sides is `isCustomWeight` **choosing an arm**: the server, where the mod had just set it `true`, goes `Food.getActualWeight @288 L910` → the guarded `InventoryItem` route → **0**; the client, still `false`, goes `@215-@287 L902-L908` → script weight × hunger fraction → **0.35**. Check a getter's guards *and* which arm your own write moves it onto before trusting a synced field. **The guard's own trigger is now measured inside vanilla** (2026-09-10, run `td2-20260910-231655`, appendix A1, a pass-1 follow-up): `Base.FruitSaladClay` — a vanilla food **absent** from `media/lua/shared/Translate/EN/ItemName.json` — reads `getDisplayName() == getFullType()` and `getActualWeightUnmodded() == 0` on **both** sides, while `Base.Steak` (present at `ItemName.json:4218`) reads `Steak` and keeps 0.3 on both. So "no name in the translation table" is sufficient on its own; no mod-specific explanation is needed for the mod item, and no sync explanation survives either (both sides agree) | **M** for the two values (run `td1b-20260910-202029`); **M** for the vanilla display-name control (run `td2-20260910-231655`, `appendix.A1`); **C** for the arms (jar, `Food.getActualWeight`) |
| the aging fields — `age`, `offAge`, `offAgeMax` | **never** — `age` was measured not to cross in slice 02, and slice 09 moves `offAge`/`offAgeMax` from packet-read to measured. `freezingTime`, `lastAged` and `rotten` are absent from the packet too but have **not** been measured, so they stay **C** | M (runs `exp02-20260910-030433`, `td1-20260910-192457`); `freezingTime` / `lastAged` / `rotten` **C** |
| anything at all, on a client copy that is not ticking | **RESOLVED, per arm, 2026-09-11 (slice 11, run `td3-20260911-001948`) — the discriminator is the 1.6 cooking gate, and the carrier is `Food.update`'s cooking-branch `sendItemStats`.** The probe the contested row itself named was run: a server-pinned vanilla `Base.Steak` at **`heat 1.2`, BELOW the gate**, read on both sides twice **12.54 s** apart. The **client's copy was frozen to the bit** (`1.2000000476837158` / `getCookingTime 0` at both reads) while the **server's decayed to the 1.0 floor** — the mirror image of pass 2's above-gate arm, and the same shape as pass 1's freeze. The pin's own push did arrive (`item.set` fires `sendItemStats` on its way out; both sides read the identical value at read 1), so the freeze is not "the client never saw it". **Grading: M per arm** — `n = 1` in each of the three arms, across three sessions — **mechanism C** (the jar text below). **What it REFINES rather than confirms:** `updateTemperature` runs unconditionally inside `Food.update`, so the honest statement about the below-gate arm is "**`Food.update` did not advance the client's held copy in this window**", not "the client cannot tick"; the hypothesis's "a client copy *can* tick" clause is narrowed, not proved. **Still open:** one item, one 12.54 s window, one fixture; frozen and non-cookable items are untested, and so is every other push path. **The operative rule is unchanged: a client-side reader of a live item field may be reading a push, not a simulation, and must not assume either.** Full reading: [teardown](../mods-survey/teardowns/autocook.md) § MP handling → The carrier. The three readings, kept because each is a separate arm: *Slice 09 (run `td1-20260910-192457`):* the client's copy of a server-spawned `Skittles.CuredPork` held `heat` and `cookingTime` **frozen across 11.1 s** (client 1.84703 while the server fell 1.79561 → 1.39397, same instance `#562521975`) — the push lands, the simulation does not. *Slice 10 (2026-09-10, run `td2-20260910-231655`, appendix A2, a **pass-1 follow-up** carried on a different session):* a server-pinned vanilla `Base.Steak` **did move** on the client — `heat` 2 → 1.697029948234558 and `cookingTime` 0 → 0.1182333305478096 over 10.5 s — **bit-identical to the server across a 0.5 s read offset** during which an independently ticking copy would have decayed further. **The mechanism that reconciles them (C, jar) — a hypothesis when it was written, and the thing the third arm then confirmed:** `Food.update` has no client guard and `updateTemperature` runs unconditionally, so a client copy *can* tick; and the push is `Food.update @86-@103 L377-L379` — `if (GameTime.getMinutes() != lastCookMinute) { if (GameServer.server != null) GameServer.sendItemStats(this); … }`, once per **game minute** (≈3.75 real s at `DayLength 4`) **while the cooking branch is live**, gated at `@49-@71 L372-L373` on `isCookable && !isFrozen() && heat > 1.6f`. The Steak never left that gate (2.0 → 1.697) so pushes kept the sides identical; the CuredPork **crossed** it, and the pushes stopped. *Slice 11 (2026-09-11, run `td3-20260911-001948`, `carrier`):* the same pin **below** the gate froze the client's copy while the server's moved — the third arm, and the one that makes the gate the measured discriminator rather than a candidate | **M** on all three readings (runs `td1-20260910-192457`, `td2-20260910-231655` `appendix.A2`, and `td3-20260911-001948` `carrier`), **M per arm** with `n = 1` in each; the mechanism stays **C** (jar) and the bounds above stay open |

Two timing facts from the same sessions, for anyone designing a probe or a
heartbeat around item state: **the dedicated server's inventory-item tick runs
about once every 5 s, not every frame** (bounded three ways and reproduced on a
second run; `InventoryItem.calculateTimeMultiplier`'s server arm is
real-time-delta driven and clamped at 6 s), and a bus call therefore **cannot
be made the cause** of a server-side item transition on a fixture at this time
multiplier — the tick wins the race. Heat decay measured at ≈0.036/s at
`mult 4.7961`.

Consequences for the nutrition mod:
- **Item mutations go through the command bus** (KEEP 2): client →
  `sendClientCommand` → server edits the item → `sendItemStats` broadcasts.
  Editing a food item's fields client-side (e.g. per-item nutrient values)
  desyncs silently — the ItemQuality failure, now reproducible on demand.
  **"Broadcasts" is not a synonym for "both sides now agree"** (slice 09): the
  broadcast carries 43 fields (39 of them item state) and is faithful for
  `hungChange`, lossy for `thirstChange`, and silent about everything outside
  the list — see the
  server→client table above before assuming a server-side edit has landed.
- **Per-player nutrient state lives in player modData and is
  `transmitModData()`-ed on change**, or lives server-side and is pushed with
  `sendServerCommand`. One owner per value; the witness suite checks it.
- **Any parallel nutrient store must be computed server-side and pushed, or
  live in modData with an explicit transmit.** Vanilla `Nutrition` is recomputed
  on the server and pushed at 1 Hz, so a client-side write to it is erased
  within a second; a client-side write to *custom* fields is not erased (they
  are not in the packet) but drifts away from the vanilla numbers, which keep
  moving server-side. Whatever the mod does about nutrient math has to run where
  `Eat` runs — the server. Full chain, packets and citations:
  [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md) § MP behaviour.
- Accelerated tests: RCON `settimespeed <x>` broadcasts to every client and
  nutrition ticks scale with it (spike S5); always restore through the same
  command.

## Open pattern questions (feed into teardowns)

- ~~How does LongTermPreservation4220 override vanilla food spoilage — item
  script redefinition, lua-side, or both?~~ **Answered, slice 09
  ([teardown](../mods-survey/teardowns/longtermpreservation4220.md), runs
  `td1-20260910-192457` / `td1b-20260910-202029`): neither — it overrides
  nothing.** It adds 14 new food items in its own `module Skittles` (zero
  vanilla name collisions) and pins their shelf life *in the item script*; the
  only Lua is a **server-side** `OnCooked` hook that rewrites the crafted
  instance's fields. So the mechanism splits cleanly, and that is the answer
  our item pass needed: the **script** half is correct on both sides for free,
  while the **Lua** half reaches a client only through `ItemStatsPacket` — the
  four macros and `hungChange` arrive, and `offAge`, `offAgeMax`, `isCookable`
  and `isCustomWeight` never do, so the client's copy of a cured meat still
  believes it spoils in 53 days.
- ~~What cadence does simpleStatus poll nutrition at, and does it read
  getNutrition() client-side only?~~ **Answered, slice 10
  ([teardown](../mods-survey/teardowns/simplestatus.md), run
  `td2-20260910-231655`): per UI frame, uncached, and client-side only.**
  `SSBar:prerender` calls `prepareBarInfo()` unconditionally
  (`ISSSBar.lua:464`), which reads `bar.valueFn(self.player)` at `:171` and
  then re-enters it up to three more times per bar through
  `percentFn` / `textFn` / `colorFn` at `:236-238` — so a single frame issues
  **up to four `player:getNutrition()` round trips per visible nutrition bar**,
  with no cache anywhere (the file's one timer, `:453-457`, throttles
  `adjustWindowSize`, never the value read). **The bound is per bar, and four
  is the floor rather than the ceiling: the weight bar costs ten** — one
  `valueFn`, two re-entries, and **seven** further direct `getNutrition()` calls
  its `textFn` makes for the three direction flags
  (`ss.stats.lua:404-411`). The mod is 7 client-only Lua
  files: it registers **nothing** server-side, so all 12 nutrition reads are
  client-side by construction (C, 2026-09-10). **The source it polls changes
  once a second** — `PlayerStatsPacket`, measured here at 0.766 s / 0.765 s
  arrival — so ~59 of every 60 reads return an unchanged value. **Rule for our
  own UI: cache at the push cadence, not the frame cadence.** What the mod
  draws is nonetheless correct: every one of its five macros mirrored inside
  its signed per-snapshot band on all six snapshots.
- MoodleFramework API surface + MP behavior — adoption decision. **One
  precondition is now settled** (slice 11, 2026-09-11): the framework is
  **whole** on 42.20.4 — its `42.20/` folder ships only `MF_ISMoodle.lua`, and
  under KEEP 10's measured rule `MF_Config.lua` survives from `common/` and
  executes, so an adoption read is no longer blocked on the layout question
  ([`../mods-survey/nutrition-mods.md`](../mods-survey/nutrition-mods.md)
  § Open questions 3). The API surface and MP behaviour are still unread.
- ~~How does a `common/` folder combine with the live `42.x/` folder?~~
  **Answered, slice 11** ([teardown](../mods-survey/teardowns/autocook.md),
  run `td3-20260911-001948`): **version-wins**, with translations merged rather
  than shadowed. The statement, its grading and its bounds are KEEP 10.
- How the Girth stack namespaces its 228 command sites (slice-08 catalog,
  2026-09-10 — the "110+" this list used to carry predates that sweep;
  collision risk for our module names on the same bus).

## Sources

- Corpus: the 230-mod inventory ([survey](../mods-survey/approved-modlist.md),
  `tools/mod_inventory.py`) plus line-level reads of ItemQuality, BeyondTen,
  damnlib, KBW/ElyonLib and the ChuckleberryFinn mods — see the teardowns under
  [../mods-survey/teardowns/](../mods-survey/teardowns/).
- Measured MP behaviour: spike **S6** (runs `spike-20260909-143930`,
  `spike-20260909-144417`) and spike **S5**, both in
  [../testing/spikes.md](../testing/spikes.md); nutrition and hunger/thirst
  authority from runs `exp01-20260910-000351` and `exp01-20260910-003929`, whose result
  JSON is committed at
  [`testing/artifacts/exp01-20260910-000351/eat-smoke.json`](../../testing/artifacts/exp01-20260910-000351/eat-smoke.json)
  and
  [`testing/artifacts/exp01-20260910-003929/eat-matrix.json`](../../testing/artifacts/exp01-20260910-003929/eat-matrix.json)
  (the full run directories with their logs stay local under `testing/runs/<run id>/`,
  which is gitignored). Weight, the weight band traits and the tighter hunger revert
  bound come from run `exp03-20260910-045523`, committed at
  [`testing/artifacts/exp03-20260910-045523/body.json`](../../testing/artifacts/exp03-20260910-045523/body.json).
- Engine side of the nutrition rows: [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md)
  (jar and Lua citations for `IsoGameCharacter.Eat`, `EatFoodPacket`,
  `PlayerStatsPacket`, `Nutrition.update`).
- **Server→client item sync** (the table above, FILTER 1's measured half and the
  closed open question): runs `td1-20260910-192457` and `td1b-20260910-202029`,
  committed at
  [`testing/artifacts/td1-20260910-192457/teardown-longtermpreservation4220.json`](../../testing/artifacts/td1-20260910-192457/teardown-longtermpreservation4220.json)
  and
  [`testing/artifacts/td1b-20260910-202029/teardown-longtermpreservation4220-followup.json`](../../testing/artifacts/td1b-20260910-202029/teardown-longtermpreservation4220-followup.json),
  with the field-by-field reading, the `ItemStatsPacket` membership list and the
  jar citations in
  [../mods-survey/teardowns/longtermpreservation4220.md](../mods-survey/teardowns/longtermpreservation4220.md)
  § MP handling. Provenance and *do not cite* notes for both runs:
  [`../../testing/artifacts/README.md`](../../testing/artifacts/README.md).
- **The client→server modData wipe, the `updateWeight` flag half, the contested
  client-copy row and the vanilla display-name control** (slice 10, 2026-09-10):
  run `td2-20260910-231655`, committed at
  [`testing/artifacts/td2-20260910-231655/teardown-simplestatus.json`](../../testing/artifacts/td2-20260910-231655/teardown-simplestatus.json)
  — keys `wipe_reading`, `phase2[]`, `grades[].flags`, `appendix.A1`,
  `appendix.A2` — with the field-by-field reading, the signed per-snapshot band
  and the jar citations in
  [../mods-survey/teardowns/simplestatus.md](../mods-survey/teardowns/simplestatus.md)
  § MP handling. **It is the first artifact written under the widened float
  rendering** (`291f977`, `tostring` rather than `%.6f`), which is why its
  weight rows support a bit-level claim and no earlier artifact does; the
  *do not cite* list is in
  [`../../testing/artifacts/README.md`](../../testing/artifacts/README.md).
- **The `common/`-vs-version-folder merge rule (KEEP 10), FILTER 11 and the
  below-gate arm that resolves the client-copy row** (slice 11, 2026-09-11):
  run `td3-20260911-001948`, committed at
  [`testing/artifacts/td3-20260911-001948/teardown-autocook.json`](../../testing/artifacts/td3-20260911-001948/teardown-autocook.json)
  — keys `M1_overrides`, `M4_globals`, `summary.M4_autocook_keyCount_client`,
  `nilcall_lines`, `transmit_reading`, `carrier` — with the five readings, the
  jar call sites and the bounds in
  [../mods-survey/teardowns/autocook.md](../mods-survey/teardowns/autocook.md)
  § Architecture and § MP handling. The *do not cite* list for that run
  (including the `window_s` mismatch and the trivial weight-flag arm) is in
  [`../../testing/artifacts/README.md`](../../testing/artifacts/README.md).
