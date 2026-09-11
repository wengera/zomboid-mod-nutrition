# Patterns & anti-patterns — evidence from the approved corpus

**Verified against: 42.20.4 (`b0bbce05d5`)** — corpus read 2026-09-09; the measured
MP sync facts re-checked and the nutrition row corrected 2026-09-10 (slice 01);
slice-03 corrections 2026-09-10; the **server→client** sync table, the FILTER 1
addition and the first closed open question added 2026-09-10 (slice 09, the
LongTermPreservation4220 teardown).

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
   `offAgeMax`, `weight` and `customWeight`. The six arrive; of the five, the
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

## Measured MP sync facts (42.20.4, spike S6 — [testing/spikes.md](../testing/spikes.md))

Established with the sync witness on a real dedicated server + real client;
they sharpen KEEP 1–2 and FILTER 1.

| Change made on the client | Reaches the server? | Ev |
|---|---|---|
| `player:getModData().k = v` | **no** — until `player:transmitModData()`, then yes | M (spike S6) |
| `setCondition` / `setConditionMax` / `getModData()` on an inventory item, then `sendItemStats(item)` | **never** — `sendItemStats` is `GameServer.sendItemStats` (server → owning client, packet `ItemStats`); on a client it is a silent no-op. There is no client→server "push my item fields" API, and waiting 60 s changes nothing | M (spike S6) |
| `inventory:AddItem("Base.X")` client-side | **never** — the server's copy of the player's inventory (it does hold one: a server-side `additem` shows up on both sides with one id) never gains the item | M (spike S6) |
| nutrition (`getNutrition()` calories/weight/macros) | **never** — and it is overwritten. `Nutrition` is **server-authoritative**: the eat itself completes on the server, which pushes the whole object at eat time (`EatFoodPacket`) and once a second (`PlayerStatsPacket`). A client `setCalories(3000)` never reached the server and was back to the server's value inside 3 s; a server-side write reached the client inside 3 s. The 0.2 kcal agreement S6 measured is mirror lag, not client authority | M (run `exp01-20260910-000351`) |
| `getStats():set(CharacterStat.HUNGER / .THIRST, v)` client-side | **never** — same shape as nutrition: a client write to 0.9 was gone within 3 s while a server-side write to 0.4 reached the client. Re-measured with a tighter bound: a client write of 0.9 against a server pinned to 0.3 read back 0.9 at t = 0.51 s and **0.3004 at t = 1.42 s** — the revert lands inside 1.5 s, consistent with the 1 Hz push | M (runs `exp01-20260910-003929`, `exp03-20260910-045523`) |
| `getNutrition():setWeight(v)` client-side | **never — and the client cannot derive weight either.** `Nutrition.updateWeight` runs on the client but a `GameClient.client` skip (`@317–@320 L198`) sits before `setWeight` and before `applyTraitFromWeight`, so the client computes a weight delta, discards it, and **never applies the weight band traits**. A client `setWeight(105)` read back 105 with `hasTrait(Obese)` false, then reverted to the server's 80 within 3 s with `Obese` still false. Consequence for a mod (**inference, not measured**): the band traits are not in `PlayerStatsPacket`, and whether any *other* packet syncs `CharacterTraits` was not traced (open question 10 in [../vanilla/body-stats.md](../vanilla/body-stats.md)) — so evaluate anything keyed on Obese/Overweight/Underweight/Emaciated server-side, or feed it an explicitly transmitted value, as the safe default rather than a proven necessity | M (run `exp03-20260910-045523`) for the client write/discard; the consequence is an **inference under C** — the `GameClient.client` skip and `PlayerStatsPacket`'s field list are code-read, the "so evaluate it server-side" step is our reasoning from them, not a separate measurement; mechanism and citations in [../vanilla/body-stats.md](../vanilla/body-stats.md) § MP behaviour |

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
| `setActualWeight` | **the field travels** (`setData` fills it from `getActualWeightUnmodded()`), but read back the two sides disagreed **0 vs 0.35**. The display-name guard alone does not explain it: `getActualWeightUnmodded` returns 0 whenever `getDisplayName().equals(getFullType())`, and that was true on **both** sides for that mod item (false for a vanilla control, `Base.Steak`, 0.3 everywhere) — a symmetric guard cannot produce an asymmetric reading. What splits the sides is `isCustomWeight` **choosing an arm**: the server, where the mod had just set it `true`, goes `Food.getActualWeight @288 L910` → the guarded `InventoryItem` route → **0**; the client, still `false`, goes `@215-@287 L902-L908` → script weight × hunger fraction → **0.35**. Check a getter's guards *and* which arm your own write moves it onto before trusting a synced field | **M** for the two values (run `td1b-20260910-202029`); **C** for the arms (jar, `Food.getActualWeight`) |
| the aging fields — `age`, `offAge`, `offAgeMax` | **never** — `age` was measured not to cross in slice 02, and slice 09 moves `offAge`/`offAgeMax` from packet-read to measured. `freezingTime`, `lastAged` and `rotten` are absent from the packet too but have **not** been measured, so they stay **C** | M (runs `exp02-20260910-030433`, `td1-20260910-192457`); `freezingTime` / `lastAged` / `rotten` **C** |
| anything at all, on a client copy that is not ticking | **the push lands, the simulation does not.** The client's copy of a server-spawned item held `heat` and `cookingTime` frozen across 11.1 s while the server's ran two or three ticks — so a client-side reader sees the last pushed value, not a live one. Mechanism open (the update path carries no side guard) | M on the freeze (run `td1-20260910-192457`); the cause is **C** and unexplained |

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
- What cadence does simpleStatus poll nutrition at, and does it read
  getNutrition() client-side only?
- MoodleFramework API surface + MP behavior — adoption decision.
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
