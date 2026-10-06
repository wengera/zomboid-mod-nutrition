# Wire packets — field contracts and measured desyncs
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the field contract of each food, nutrition and character packet — item stats, player stats, player fields, experience, injuries, body part, modData and eat — what each omits, and every desync measured per field and per arm; who sends each packet, when and gated how is `platform/mp-model.md`

## Key facts

- The item-stats packet carries 43 fields — two addressing, two presence flags and 39 item-state values — and that set is the whole of what a write to an item's own fields can reach the other side through [#0334, #1036, #1396].
- The receiver applies 40 of those 43: the two addressing fields never land, and `uses` is written but dropped for anything that is not a drainable combo [#0336].
- Twenty of the value fields are written only behind a bit-header flag, and `parse` mirrors each guard, so a skipped field is not read at all [#0338/C/C-only].
- Eleven of the 28 item-state getters this library reads are absent from the packet, and five of the eleven are measured not to cross or to stay wrong on the client [#0907/M/n=1].
- Nine item fields are absent from all 43 packet names: the cookable flag, the plain weight, the custom-weight flag, the age, the two age-window fields, the last-aged stamp, the freezing time and the rotten flag [#1398].
- The player-stats packet is an unconditional full snapshot pushed once a second, and its whole nutrition payload is five floats — calories, proteins, lipids, carbohydrates and weight — with no flag byte [#0114, #1481].
- Weight crosses as a float and is widened back to a double on arrival, so the client's mirror is exactly float32-representable at 6 of 6 snapshots where the server's is not at 5 of 5 [#1487/M/n=1].
- A server-side write of the four macros or the raw hunger change arrives intact: calories 300 to 210, proteins 50 to 35, lipids 12 to 8.4 and the hunger change −0.6 to −0.42 [#1105/M/n=1, #1666/M/n=1].
- A cooked food's thirst change halves once per server-to-client hop — 0.2 becomes 0.1 on the wire and reads 0.05 on the client — and converges rather than compounding [#1038/M/n=2].
- Four item fields desync whole across a cook transition and nothing later repairs them: the two age-window bounds, the cookable flag and the custom-weight flag [#1037/M/n=1].
- A zero-valued conditionally-written field arrives carrying the last packet's value: an apple synced after a steak reached the client holding the steak's cooking time of 71.119644 [#0346/M/n=1].
- A client-side write of vanilla nutrient numbers onto the player is overwritten within a second by the 1 Hz push, while a write to the mod's own fields survives and desyncs instead [#0129/M/n=1].
- The eat packet overwrites the receiver's whole `Nutrition`, and neither of its two handlers applies any numbers of its own [#0113, #0116].
- Three character packets replace the receiver's copy rather than merging into it: the player-fields trait block resets the trait list before re-adding the sender's, the experience packet reloads traits, per-perk experience, perk levels and multipliers wholesale, and a sync-stats packet with mask `-1` reloads the whole `Nutrition` object [#2617/C/C-only] [#2620/C/C-only] [#2627/C/C-only].
- The modData packet drops any pair whose type byte is minus one, so strings, doubles, nested tables and booleans travel while functions and Java objects do not [#1495].

## How it works

Four packets carry food and nutrition state between a dedicated server and its client, and this page is the payload of each.
Two of them are item packets and two are player packets, and a mod's reach on either side ends exactly at the field lists below.
The character state around them — the player-fields blocks, experience and perk levels, the injuries floats and one body part at a time — rides its own packets, whose payloads follow the player packet's.
Where a value is not in a list, no re-push repairs it: the receiving side keeps whatever it last computed or last read off the wire, indefinitely.
The mechanisms — who sends each packet, when it fires, under what gate, what the receiver caches between sends, and which routes exist in the other direction — are [`platform/mp-model.md`](../platform/mp-model.md).
This page states only what each payload contains, and what the two sides then read back.

<a id="item-stats-packet"></a>
### The item packet's field contract

Three things decide whether a value a mod writes onto an item shows up on a client: whether the field is in the packet's list, whether the sender's own value clears that field's write guard, and whether the receiver applies it.
All three fail independently, and the rows below separate them.
A field that is in the list but written behind a guard is the worst of the three, because it looks present and reads wrong.

`ItemStatsPacket.setData` populates 43 distinct packet fields and `write` puts exactly those 43 on the wire: a container id and an item id for addressing, the `isFluidContainer` and `isFood` presence flags — pure gates in the receiver, never applied to the item — and 39 item-state values, which is the whole of what a Lua hook's write to an item can reach the other side through [#0334, #1036, #1396].
Item sync is two packets, not one: `ItemStatsPacket` has seven members and runs server to client only, carrying those 43 fields and not `conditionMax`, with the send a silent no-op on a client, while `SyncItemFieldsPacket` has fifteen members, is the `syncItemFields()` route, and wipes and replaces the receiver's item modData [#1119].
When each packet fires, and what the receiver's cached packet object does between sends, is [`platform/mp-model.md#packets`](../platform/mp-model.md#packets).

Three fields in the list are easy to misread, and each one changes what a mod may assume.
`isCustomName` is not a presence flag despite sitting beside the two that are: it is read off the item, `write` uses it only to decide whether the `16777216` bit-header flag is added while the name itself goes on the wire unconditionally, and the receiver applies it through the item's custom-name setter, so it is ordinary item state [#0335].
`setData` writes the heat packet field twice — from the item heat getter and then from the food heat getter, which overwrites it for any food — `write` emits it once, and the receiver applies it into both the item heat and the food heat, while `customName` and `name` stay two distinct packet fields [#0337].
And the receiver applies 40 of the 43: besides the two addressing fields, `uses` is written but never applied, because the receiving side rebuilds it from the used delta times the maximum uses only inside the drainable-combo branch and drops the wire value for any other item [#0336].

Most of the food block is written conditionally, and that is the shape behind every stale read on this page.
`ItemStatsPacket.write` puts twenty of its value fields on the wire only behind a bit-header flag and `parse` mirrors each guard, so a skipped field is simply not read; the table gives all twenty with the guard each sits behind — eighteen a plain non-zero test, `poisonDetectionLevel` a test against −1 and `fertilizedTime` the fertilized boolean — and the flag each one carries [#0338/C/C-only].

| Guard in `write` (skipping it leaves the field stale) | Field(s) | Flag |
|---|---|---|
| `!= 0f` | `cookingTime`, `minutesToCook`, `minutesToBurn`, `hungChange` | 16, 32, 64, 128 |
| all four `== 0f` | `calories`, `proteins`, `lipids`, `carbohydrates` — one block, any one non-zero writes all four | 256 |
| `!= 0f` | `thirstChange`, `painReduction`, `endChange`, `stressChange`, `fatigueChange`, `unhappyChange`, `boredomChange`, `baseHunger` | 512, 2048, 4096, 16384, 32768, 65536, 131072, 2097152 |
| `!= 0` (int) | `fluReduction`, `foodSicknessChange` | 1024, 8192 |
| `!= -1` | `poisonDetectionLevel` | 524288 |
| `isFertilized` | `fertilizedTime` — a stale time then lands on a *non*-fertilized item | 33554432 |

The flag column is the bit each field's presence sets in the packet's header.
The receiving half has no matching guard.
The receiver applies unconditionally: the cooking-time setter is one of 31 food setters that run with no guard beyond the single is-food test, so whatever the field holds is written onto the item [#0339, #1203/C/C-only].
Four groups of fields cannot carry a stale value, and it is worth knowing which: `extraItems` and `spices` are conditionally written but `parse` clears both before the flag test; `poisonPower`'s bit-header flag is added unconditionally; the seven pure booleans — frozen, tainted, cooked, burnt, alcoholic, custom-name and fertilized — are re-derived from the bit header on every parse; and `condition`, `uses`, `usedDelta`, `heat`, `name` and `actualWeight` are written outside the bit header altogether [#0344, #0345, #1205/C/C-only].
What makes the stale read possible at all — one cached packet object per type with no reset, against a data setter that refreshes every field off the item before each send, so that the stale value lives on the receiving object and never originates on the sending one — is [`platform/mp-model.md#cached-packet`](../platform/mp-model.md#cached-packet).
The practical shape is easy to state and easy to forget: a field a mod leaves at zero is a field the mod has no control over on the client.

Two of the conditionally-written fields are lists rather than numbers, and they are the only place the packet carries what a dish was made of [#2629/C/C-only].
`ItemStatsPacket` carries a food's `extraItems` and `spices` lists: `setData` copies both off the food, `write` puts each on the wire only when it is non-empty, `extraItems` behind flag `4194304` and `spices` behind flag `8388608`, as a one-byte count followed by one UTF string per entry, `parse` clears its copy of each list before the flag test, and `applyItemStats` replaces the food's own list with the packet's [#2629/C/C-only].
`SyncItemFieldsPacket` carries neither list: a jar-wide grep for `extraItems` returns only `InventoryItem`, `ItemStatsPacket` and `EvolvedRecipe`, and one for `spices` adds only `Food`, so the item-stats packet is the only packet class that names either [#2630/C/C-only].
A `syncItemFields()` call therefore leaves a dish's ingredient and spice lists where they were on the client, and of the two item packets only the item-stats send moves them; the item's saved blob is a separate carrier this page does not read [#2630/C/C-only].

The field list is 43 names dumped from the packet's write method on 2026-09-10, covering the condition, the heat, the cooking time, the four macros, the raw hunger and thirst fields, the burn and cook minute fields, the fluid and food presence flags and the addressing pair [#1397/C/snapshot]:

```
actualWeight baseHunger boredomChange calories carbohydrates condition containerId cookingTime
endChange extraItems fatigueChange fertilizedTime fluReduction fluidContainer foodSicknessChange
heat hungChange id isAlcoholic isBurnt isCooked isCustomName isFertilized isFluidContainer isFood
isFrozen isTainted isWet lipids minutesToBurn minutesToCook name painReduction
poisonDetectionLevel poisonPower proteins spices stressChange thirstChange unhappyChange
usedDelta uses wetCooldown
```

What the list omits is as load-bearing as what it carries.
Nine item fields are absent from all 43 names: the cookable flag, the plain weight, the custom-weight flag, the age, the two age-window fields, the last-aged stamp, the freezing time and the rotten flag [#1398].
A reverse-reference scan for callers of the age setter returns no packet class at all, which is the same boundary read from the other end; the scan is whole-jar and the source gives the setter no bytecode offset [#0333/C/C-only].

The packet's own name list is the authoritative membership test, but it is not the list a probe can read.
The harness reads zero-argument getters rather than fields, so the two lists differ in shape even where they agree in substance.
Against the harness's own working set the split is therefore sharper, because every key in it is something a probe can actually read on both sides.
That set is 28 keys, each a zero-argument getter, and what matters is whether the packet's data setter reads that getter: 16 of the 28 are read and 11 are omitted, with the item id carried as addressing rather than as state [#0903/C/C-only].

| `TK.ITEM_STATE` keys | In `ItemStatsPacket.setData`? |
|---|---|
| `cooked` `burnt` `frozen` `hungChange` `baseHunger` `calories` `carbs` `lipids` `proteins` `uses` `cookingTime` `heat` `minutesToCook` `minutesToBurn` | **yes** — `setData` reads `isCooked`, `isBurnt`, `isFrozen`, `getHungChange`, `getBaseHunger`, `getCalories`, `getCarbohydrates`, `getLipids`, `getProteins`, `getCurrentUsesFloat`, `getCookingTime`, `getHeat`/`getItemHeat`, `getMinutesToCook`, `getMinutesToBurn` |
| `thirstChange` | **yes, but lossy** — `setData` sends `getThirstChange()`, the *cooked-ladder* getter, and `applyItemStats` stores it with `setThirstChange`, i.e. as the **raw** field: 0.2 → 0.1 on the wire → 0.05 on read. One halving per server→client hop; it converges |
| `actualWeight` | **yes, by a different getter** — `setData` fills the field from `getActualWeightUnmodded()`, not `getActualWeight()`, so which value arrives depends on a guard the sender may have moved |
| `rotten` `age` `fresh` `offAge` `offAgeMax` `freezingTime` `hungerChange` `isCookable` `weight` `customWeight` `lastCookMinute` | **no.** `age` and `offAge`/`offAgeMax` are measured not to cross; `isCookable`/`isCustomWeight` are measured to stay wrong on the client; `hungerChange` is a read-time ladder getter, not a field (the packet carries the raw `hungChange` instead); `rotten` and `fresh` derive from `age` |
| `id` | **carried, as addressing** — not state. `setData` reads the field `InventoryItem.id` straight into the packet's own `id`, which is how the receiving side finds the instance the rest of the payload is about; it is not a value a mod should treat as synced item state |

The table is the membership split alone; the grade and the run behind each of its rows are carried by the register row its caption cites.
The data setter reads 14 of those getters directly — the cooked, burnt and frozen flags, the raw hunger change, the base hunger, the four macros, the current uses, the cooking time, the heat and the two cook and burn minute counts — and four of them are measured to cross, as are four of the five fields of the macro block, while the carbohydrate field moved from zero to zero, carries no information, and stays a code reading [#0904/M/n=1].
Eleven item-state keys are absent from the packet — the rotten, fresh and cookable flags, the age and the two off-age bounds, the freezing time, the read-time hunger change, the plain and custom weights and the last cook minute — and five of them are measured not to cross or to stay wrong on the client: the age, the two off-age bounds, the cookable flag and the custom-weight flag [#0907/M/n=1].
The rotten and fresh flags derive from the age and the read-time hunger change is a ladder getter rather than a field, so those three are code readings rather than measurements.
The item id travels as addressing and not as state: the setter copies the item's own id field straight into the packet's id, which is how the receiving side finds the instance the rest of the payload is about [#0908/C/C-only].

The weight field is the one entry whose value depends on the sender's own guards rather than on the field list.
The packet fills its actual-weight field from the unmodded weight getter rather than the plain one, so which value arrives depends on a guard the sender may have moved [#0906/M/n=1].
That getter returns zero when the item's display name equals its full type, and the display-name getter returns the item's own name field, so the packet fills the actual weight from a getter that can be guarded to zero, and that zero is what travels [#1425].
A new item with no translation entry therefore ships weight 0 to every client [#1028].
A probe that reads the weight on one side only cannot tell a guard from a sync, which is why both weight getters are read separately in every arm below.

The macro block is the part a nutrition mod cares about most, and it is the part that behaves.
A server-side write of the macros or of the raw hunger change arrives intact, the hunger change as the raw field so that each side ladders it once: calories 300 to 210, proteins 50 to 35, lipids 12 to 8.4 and the hunger change −0.6 to −0.42, equal on both sides to within the comparison tolerance, with the carbohydrate row moving from zero to zero and carrying no information [#1105/M/n=1, #1666/M/n=1].
Both sides then read the raw field at −0.42 and the derived getter at −0.546, which is the correct shape: one ladder application per side [#1400/M/n=1].
That is the one part of the item contract a nutrition mod can lean on without a workaround.
It is also the control that makes the thirst row below legible: the same session read the hunger field right while the thirst field was wrong.

Per field, graded by what was put to the test — a field carries information only when the two sides were first made to differ on it — the contract is twelve fields and field groups with their owning side and whether the packet carries each: `age`, `offAge`, `offAgeMax`, `freezingTime`, `lastAged` and the rotten field never travel, while `calories`, `burnt`, `cookingTime`, `heat`, `cooked`, `frozen`, the four macros and the mood deltas do [#0347/M/n=1].
Only five of its twelve rows were made to differ in a run; the rest are code readings, and the measured arms of those five are the table at [the desyncs](#desyncs).

| Field | Owning side | In `ItemStatsPacket`? |
|---|---|---|
| `age` | server (only the server runs `updateAge`) | **no** |
| `calories` | server | **yes** |
| `burnt` | server | **yes** |
| `cookingTime` | server | **yes** |
| `heat` | server | **yes** |
| `cooked` | server | yes (in the field list) |
| `offAge`, `offAgeMax`, `freezingTime`, `lastAged` | server | **no** (absent from the field list) |
| `frozen` | server | yes (the boolean is in the list; the 0–100 `freezingTime` behind it is not) |
| `hungChange`, `baseHunger`, `carbohydrates`, `proteins`, `lipids`, `thirstChange` | server | yes |
| `minutesToCook`, `minutesToBurn`, `poisonPower`, `poisonDetectionLevel`, `extraItems`, `spices`, `condition`, `uses` | server | yes |
| `rotten` (the field) | — | no |
| Cooking **perk level** (drives the evolved-recipe summation) | server | n/a (character sync, not `ItemStatsPacket`) |

The table is the contract, not the evidence: each row says who owns the field and whether the packet carries it, and nothing more.

<a id="player-stats-packet"></a>
### The player packet's field contract

The player side has one carrier, and it runs whether or not anything changed.
Nothing in its payload is conditional, so a quiet second costs exactly as many bytes as a busy one, and there is no window in which a client-side write to a carried field is safe.
The server pushes the whole `Nutrition` object once a second unconditionally, through `NetworkPlayerAI.syncStats` on a 1000 ms `UpdateLimit`, inside `PacketType.PlayerStats`, whose `write` and `parse` embed `Nutrition.save` and `Nutrition.load` [#0114].
`PlayerStatsPacket.write` is an unconditional full snapshot in a fixed order: the player id, the whole stats registry, the nutrition object's calories, proteins, lipids, carbs and weight, the time since the last smoke, and the body-damage main fields [#0564].

```java
PlayerID.write(bb);                                   // @0  L31
getPlayer().getStats().save(bb.bb);                   // @5  L33  — one float per CharacterStat.ORDERED_STATS
getPlayer().getNutrition().save(bb.bb);               // @19 L34  — calories, proteins, lipids, carbs, weight
bb.putFloat(getPlayer().getTimeSinceLastSmoke());     // @33 L35
getPlayer().getBodyDamage().saveMainFields(bb.bb);    // @44 L36
```

`Nutrition.save` and `Nutrition.load` write and read calories, proteins, lipids, carbohydrates and weight in that order, and `load` goes through the clamping setters, so the arriving numbers are clamped on the receiver rather than trusted as sent [#0108].
Inbound, a client consumes exactly that: the nutrition save's five floats and nothing else, the weight narrowed to a float on the way out and widened back on the way in, with no flag byte anywhere in the payload [#1481].
The narrowing is visible in the numbers themselves: the client's mirrored weight is exactly float32-representable at 6 of 6 snapshots while the server's is not at 5 of 5 drifted readings, because the nutrition getter is a double and the wire field is a float [#1487/M/n=1].
That reading is obtainable only under a widened float rendering, so a probe that prints six decimals cannot see it.
For a reader the consequence is that the two sides' weights are never expected to be equal to the bit, and a probe testing for equality reports a defect that is not there.

What rides along with the nutrition block matters as much as the block itself.
`Stats.save` writes the whole stat registry with no per-field bitmask, so hunger, thirst, endurance and fatigue ride along with the other 20 registered stats from anger to zombie infection [#0566].
The registry's order, and why a stat a mod registers is outside it, is [`character-stats.md#registry`](character-stats.md#registry).
A mod that writes any registered stat on a client is therefore writing into a value the next snapshot replaces, whether or not that mod's own field is involved.
The packet carries neither moodles, which each side recomputes, nor `CharacterTraits` [#0567].
The three weight-direction flags are not in it either, and the client agrees anyway because the engine recomputes them: the character update calls the nutrition update gated only on the character-stats switch, whose client arm calls the weight update, and the weight update sets all three flags before its client skip reaches the weight write [#1489].
Neither player-stats packet carries a perk level or an experience value: `PlayerStatsPacket.write` writes the player id, the stats, the nutrition save, the time since the last smoke and the body-damage main fields, `SyncPlayerStatsPacket.write` writes the player id, the mask and either the nutrition save or the masked stat floats, and no method of either class references a perk or XP member [#2628/C/C-only].
Perk levels and experience travel on their own packets, which are [the experience packet](#experience-packet) below.

The other nutrition-bearing send on the eat path carries none of this.
The `SyncPlayerStats` packet that `Eat` sends carries no nutrition bits: its mask is THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE and PAIN, alongside `GameServer.sendSyncPlayerFields(player, 8)` [#0115].
That packet has two forms keyed on its int mask, and only one of them is a nutrition carrier [#2627/C/C-only].
With the mask at `-1`, `SyncPlayerStatsPacket.write` embeds `Nutrition.save` and `parse` calls `Nutrition.load`, replacing the receiver's whole `Nutrition` object — calories, proteins, lipids, carbohydrates and weight — and with any other mask it writes and reads one float per set bit, bit `i` selecting the stat at index `i` of `CharacterStat.ORDERED_STATS` [#2627/C/C-only].
The `-1` form is the eat packet's payload under another packet type, so it lands through the same clamping setters, and a per-bit form never touches the nutrition store [#0108, #0113, #2627/C/C-only].
The mask value of each stat is [`character-stats.md#registry`](character-stats.md#registry); who may send either form, and when, is [`platform/mp-model.md#sync-globals`](../platform/mp-model.md#sync-globals).

The consequence for a mod is a fork with no third branch.
A client-side Lua mod that writes vanilla nutrient numbers onto `IsoPlayer` is overwritten within a second by the 1 Hz packet, while one that writes its own fields is not overwritten, because custom fields are not in the packet — and it then desyncs from the vanilla numbers the server keeps recomputing [#0129/M/n=1].
The overwrite arm of that reading is measured on vanilla calories only, and the custom-field arm is read off the packet's field list rather than measured.
Which side owns each quantity, and what the other side holds instead, is [`platform/mp-model.md#ownership`](../platform/mp-model.md#ownership).

<a id="player-fields-packet"></a>
### The player-fields packet's six blocks

The player-fields packet is a set of six optional blocks behind one mask byte, and the byte decides what a push carries [#2616/C/C-only].
It carries a character's trait list, which the experience packet below carries too, and five other blocks beside it, so the bit a sender picks decides what the receiver has refreshed and what it keeps [#2616/C/C-only].
`SyncPlayerFieldsPacket.write` puts the player id and the mask byte on the wire and then, for each of the byte's six low bits that is set, in ascending order, writes one block through `writeParam`; `parseParam` mirrors the same switch, so the receiver reads exactly the blocks the sender wrote and in the same order, and the table gives each bit, what the sender writes and what the receiver does with it [#2616/C/C-only]:

| Bit | Block | Sender writes | Receiver |
|---|---|---|---|
| `1` | known recipes | an int count, then each recipe name as a UTF string | adds each name it does not already hold |
| `2` | character traits | `CharacterTraits.write` | `CharacterTraits.read` |
| `4` | already-read books | an int count, then each book name as a UTF string | adds each name it does not already hold |
| `8` | body-damage main fields | `BodyDamage.saveMainFields` | `BodyDamage.loadMainFields` |
| `16` | the reading flag | `isReading` as a boolean | `setReading` |
| `32` | fitness | `Fitness.save` | `Fitness.load` |

The last column is where the blocks part company.
The recipe and book blocks merge into what the receiver already holds, so a push never removes a recipe or a book from the far side [#2616/C/C-only].
The trait block does the opposite.
The trait block is a full replace keyed on registry locations: `CharacterTraits.write` puts a count and then each known trait's `CHARACTER_TRAIT` registry location as a string, and `CharacterTraits.read` first calls `reset`, which clears the known-trait list and sets every entry of the trait map false, and then adds each trait it reads, so the receiver's list becomes the sender's [#2617/C/C-only].
A trait the receiver holds and the sender lacks is therefore gone after the push, and a push of an empty list empties the receiver's [#2617/C/C-only].

Bit `8` carries the body's cold, infection and timer state, and not its health [#2618/C/C-only].
`BodyDamage.saveMainFields` writes exactly eleven fields, in order the cold-catch value, the has-a-cold flag, the cold strength, the sneeze-or-cough timer as an int, the reduce-fake-infection flag, the health-from-food timer, the pain reduction, the cold reduction, the infection time, the infection mortality duration and the cold damage stage, and neither overall health nor any per-part field is among them [#2618/C/C-only].
The same eleven fields are the last block of the once-a-second player-stats packet, as its code block above shows [#0114, #0564].
A client's copy of the health-from-food timer is therefore, as read from the code and not measured, as fresh as the last of those two pushes, unless something on the client recomputes it, which this page does not read [#2618/C/C-only].
Per-part state travels on [the body-part packet](#body-part-packet), never in this block [#2618/C/C-only].

Bit `32` is the whole fitness object: `writeParam` hands the buffer to `Fitness.save` and `parseParam` hands it to `Fitness.load` [#2616/C/C-only].
What the fitness object holds is [`exercise-and-training.md#fitness-object`](exercise-and-training.md#fitness-object).
Which Java calls and which Lua globals send which bits, under what gate and to whom, is [`platform/mp-model.md#sync-globals`](../platform/mp-model.md#sync-globals); this section is only the blocks.

<a id="experience-packet"></a>
### The experience packet and the perk-level packet

The experience packet and the perk-level packet both carry skill state, and they write into different places on the receiver.
The experience packet replaces the whole skill state, and the perk-level packet writes three side fields and never touches the perk list [#2620/C/C-only] [#2623/C/C-only].

`PlayerXpPacket.write` serialises the player's whole `XP` object with `XP.save`, `parse` reads it straight back with `XP.load` at version `249` unless the packet is inconsistent or the player is dead, and `processServer` does nothing but call `sendToClients` [#2622/C/C-only].
The payload is therefore the whole experience save, in this order: the character's traits, the total experience as a float, the global level and last level as ints, the per-perk experience map as a count then each perk with its float experience, the per-perk level list as a count then each perk with its int level, and the multiplier map as a count then each perk with its float multiplier and its minimum and maximum level as bytes, all of which the receiver loads straight over its own copy [#2621/C/C-only].
`XP.load` replaces rather than merges: it calls `CharacterTraits.load`, which resets the trait list before adding each name it reads, then clears the per-perk experience map, clears `perkList` and rebuilds one `PerkInfo` per wire entry, and clears the multiplier map before refilling it, skipping any entry whose perk does not resolve [#2620/C/C-only].
After the packet lands, the receiver's levels, per-perk experience, multipliers and traits are the sender's, whatever the receiver held a moment before, except that an entry whose perk does not resolve is dropped and the total experience is reset to the global level's threshold when the loaded total exceeds the next level's [#2620/C/C-only].
That includes the trait list, so the experience packet is a second carrier of the same list the player-fields trait block carries, and it replaces it the same way [#2620/C/C-only] [#2621/C/C-only].
Where those stores live, and which vanilla code writes them, is [`perks-and-strength.md#stores`](perks-and-strength.md#stores).

The `SyncPerks` packet carries only the Sneak, Strength and Fitness levels as three ints, after the player index as a byte on the client's send and after the online id as a short on the server's relay, and both receivers write them into `remoteSneakLvl`, `remoteStrLvl` and `remoteFitLvl` rather than into the perk list, the client receiver returning for a local player [#2623/C/C-only].
So the perk-level packet never writes the perk list, and the three remote fields are the only thing it changes [#2623/C/C-only].
Who sends each of the two, and how often, is [`platform/mp-model.md#packets`](../platform/mp-model.md#packets).

<a id="injuries-packet"></a>
### The injuries packet's five floats

The injuries packet carries the movement speeds and nothing else [#2624/C/C-only].
`PlayerInjuriesPacket` carries five floats after the player id: the `IdleSpeed`, `StrafeSpeed` and `WalkInjury` animation variables, read off the player by the sender with fallbacks `0.01`, `1` and `0`, and the network AI's `walkSpeed` and `runSpeed`, and `parse` sets the three variables and the two network-AI fields in that order when the packet is consistent [#2624/C/C-only].
None of the five is a stat, a perk or a nutrition value, so a mod that slows a character through a stat reaches the client's animation through whatever the server's speed code then writes into these fields, and through no other packet that names walk speed under that name, the grep bound [the walls](#walls) state [#2624/C/C-only] [#2625/C/C-only].
How the walk and run speeds are computed, and what feeds them, is [`perception-speed.md#speed`](perception-speed.md#speed); when the packet is sent is [`platform/mp-model.md#sync-globals`](../platform/mp-model.md#sync-globals).

<a id="body-part-packet"></a>
### The body-part packet's field mask

The body-part packet carries per-part state one part at a time, and it selects its fields with a mask as wide as a long [#2626/C/C-only].
`BodyPartSyncPacket` carries one body part: the player id, the part's index as a byte and a 64-bit field mask as a long, then for each of the mask's 42 low bits that is set the field `BodyPart.syncWrite` writes for key bit-plus-one; the switch covers keys 1 to 41, so 41 fields are selectable and key 1, mask value 1, is the part's health; the receiver's `parse` walks the same 42 bits and hands each set one to `BodyPart.sync`; the block gives every key, its mask bit and the type it puts on the wire [#2626/C/C-only]:

```
key bit  field                 type     key bit  field                 type
  1   0  health                float     22  21  alcoholLevel          float
  2   1  bandaged              boolean   23  22  additionalPain        float
  3   2  bitten                boolean   24  23  bandageType           UTF
  4   3  bleeding              boolean   25  24  getBandageXp          boolean
  5   4  isBleedingStemmed     boolean   26  25  getStitchXp           boolean
  6   5  isCauterized          boolean   27  26  getSplintXp           boolean
  7   6  scratched             boolean   28  27  fractureTime          float
  8   7  stitched              boolean   29  28  splint                boolean
  9   8  deepWounded           boolean   30  29  splintFactor          float
 10   9  isInfected            boolean   31  30  haveBullet            boolean
 11  10  isFakeInfected        boolean   32  31  burnTime              float
 12  11  bandageLife           float     33  32  needBurnWash          boolean
 13  12  scratchTime           float     34  33  lastTimeBurnWash      float
 14  13  biteTime              float     35  34  splintItem            UTF
 15  14  alcoholicBandage      boolean   36  35  plantainFactor        float
 16  15  woundInfectionLevel   float     37  36  comfreyFactor         float
 17  16  infectedWound         boolean   38  37  garlicFactor          float
 18  17  bleedingTime          float     39  38  cut                   boolean
 19  18  deepWoundTime         float     40  39  cutTime               float
 20  19  haveGlass             boolean   41  40  stiffness             float
 21  20  stitchTime            float
```

The mask value of a key is `1 << bit`, so the part's health alone is mask `1` and every field at once is the low 41 bits set [#2626/C/C-only].
A field outside the mask is not on the wire, and the receiver leaves its own copy of that field as it was [#2626/C/C-only].
The packet carries no body-wide value, overall health is in neither this packet nor the main-field block, and the cold and infection timers and the pain and cold reductions travel in that block, above [#2626/C/C-only] [#2618/C/C-only].
What each per-part field means to the body's own update is [`health-surfaces.md#wounds`](health-surfaces.md#wounds); who may send this packet is [`platform/mp-model.md#sync-globals`](../platform/mp-model.md#sync-globals).

<a id="moddata-packet"></a>
### The modData packet's type bytes

The modData route is the one place a mod chooses its own payload, and the type byte decides what survives.
The modData packet serialises the whole table; the table save silently drops any pair whose type byte is minus one, so strings, doubles, nested tables and booleans travel while functions and Java objects do not; the load wipes the receiver before it writes; the parse wipes it outright when the sender's table was empty; and the transmit returns silently if the player's square is null [#1495].
A nested Lua table therefore crosses whole and carries its shape rather than having its contents merged into the receiver's: one mod's table arrived on the server as an empty table with the same eight leaves missing [#1337/M/n=1].
Reading that as "nested tables sync" is the error the shape invites, because an empty table crosses just as faithfully as a full one.
The type byte is the whole of the wire-safety rule: anything a mod stores that is not a string, a number, a boolean or another table is silently absent on the far side, with no error and no log line.
The transmit is silent when it does nothing as well, so a census cannot tell a dropped key from a skipped call without a control key that is known to cross.
Which direction wipes what, and which side loses data when some other mod transmits, is [`platform/mp-model.md#wipe-and-replace`](../platform/mp-model.md#wipe-and-replace).

<a id="eat-food-packet"></a>
### The eat packet's field contract

The eat packet's payload is the nutrition store and nothing else, and its handlers are inert.
The server pushes the whole `Nutrition` object at eat time: `Eat` sends `PacketType.EatFood`, `EatFoodPacket.write` embeds `Nutrition.save`, and `parse` calls `Nutrition.load` on the receiver, overwriting its whole `Nutrition` [#0113].
Receiving the packet applies no numbers of its own: `processClient` and `processServer` both only call `EatOnClient`, which fires `OnEat` and nothing else, while the numbers arrive through the `Nutrition.load` inside `parse` [#0116].
A hook on that path is therefore a notification, not an intake point, and a mod that wants to change what an eat delivers cannot do it there.
The store is replaced whole rather than merged, so any client-side change to it made between two eats is gone after the next one.
Two sends leave the server on an eat and only one of them carries nutrition, which is why the other one is described under the player packet rather than here.
The order of writes inside `Eat`, and the rest of the intake path, is [`eating-pipeline.md#eat`](eating-pipeline.md#eat).

<a id="cooked-thirst"></a>
### The cooked-food thirst value

Every other value on the item packet is sent and stored through matching accessors, which is why this one field earns an anchor of its own.
One field is sent through a different getter from the one the receiver stores into, and the mismatch is measurable.
The item packet sends the cooked-ladder thirst getter, which halves a cooked food's value, and the receiver stores it with the raw setter, so the receiving side's own getter ladders it a second time, while the hunger field does not have this problem because the packet reads the raw field — the contrast that makes the thirst row a defect rather than a convention [#1408].
The result is one halving per server-to-client hop: 0.2 becomes 0.1 on the wire and reads 0.05 on the client [#1038/M/n=2].

Measured on a cook transition, the server read 0.1 and the client 0.05 — a difference of 0.05 on a field the mod under test never touches, which makes it a vanilla defect surfaced by any mod that cooks anything in multiplayer [#1407/M/n=1].
It converges rather than compounding: a deliberate second push left the client at 0.05 with the server unchanged at 0.1, because compounding would need a client-to-server item hop and that route is a silent no-op [#1409/M/n=1].
The bus renders every float rounded to six decimals, so the evidence here is a whole-value difference rather than a bit-for-bit one.

<a id="desyncs"></a>
### The measured desyncs

Every row below is a pair of reads of the same instance, or the same character, on one live dedicated server with one real client, the client half read first at every tag.
A field carries information only where the two sides were first made to differ, so the synced rows are listed beside the desynced ones: a match on a field both sides already agreed about says nothing.
The table is read field by field rather than run by run, because an arm belongs to a field and not to a session.
A row that says a field travels is a row where a server-side write was made and the client's read afterwards matched it; a row that says a field desyncs is a row where the same kind of write was made and the client's read afterwards did not.
The arms are not interchangeable: a cook transition, a direct write and a full accelerated game day exercise different push paths, so a field can travel under one and stay stale under another.
Where two rows cover the same field on different arms, both are kept for that reason.
Two distinctions run through the table and are easy to collapse.
Not carried is not the same as desynced — a field the packet omits can still read the same on both sides, because neither side ever changed it.
And agreement under an arm where both sides answer the same by construction is not evidence that anything is synced or recomputed.
The Run column names the artifact each row rests on, and it is the run that row's own register pointer names.

| Field | Arm | Reading | Run |
|---|---|---|---|
| `Nutrition`, all five floats (player) | an eat, then idle | server and client converge to bit-identical values: 746.838 against 746.967 before the eat, 838.475 against 838.605 immediately after, 837.055 on both sides five seconds later; the residual 0.13 kcal offset is sub-second sampling skew on a 0.259 kcal per second drain, not divergence [#0122/M/one-fixture] | `exp01-20260910-003929` |
| `calories` (item) | a server-side write | travels: a write of 999 read back as 999 on the client [#0349/M/n=1] | `exp02-20260910-030433` |
| the four macros (item) | a server-side cook hook multiplying by 0.70 | travel: the server read calories 210, proteins 35, lipids 8.4 and carbohydrates 0 and the client read the same four, the carbohydrate row carrying no information because 0.70 of 0 is 0 [#1399/M/n=1] | `td1-20260910-192457` |
| `burnt` | a burn transition | travels: the client received the change from false to true [#0350/M/n=1] | `exp02-20260910-030433` |
| `cookingTime` | a cook transition | travels: the client received the change from 0 to 71.061172 [#0351/M/n=1] | `exp02-20260910-030433` |
| `heat` | a cook transition | travels: the client received the change from 1 to 1.83512 [#0352/M/n=1] | `exp02-20260910-030433` |
| `cookingTime` | an item synced immediately after another item | stale: an apple arrived on the client carrying the steak's cooking time of 71.119644, a value the apple had held on neither side, while its own non-zero minutes to cook 60 and minutes to burn 120 arrived correctly; it reproduced, and survived cooling the steak below the cooking gate [#0346/M/n=1, #1204/M/n=1] | `exp02-20260910-030433` |
| `age` | four arms in one session | never reaches the client: with the server at 3.250943, 3.251331 and 3.5 the client read 0 after an explicit stats send, after a syncing aging call and after a full accelerated game day [#0348/M/n=1] | `exp02-20260910-030433` |
| the aging fields as a group | two runs | do not cross: age was measured not to cross and the two off-age bounds moved from packet-read to measured, while the freezing time, the last-aged stamp and the rotten field are absent from the packet too but have not been measured [#1107/M/n=2] | `exp02-20260910-030433`, `td1-20260910-192457` |
| `offAge`, `offAgeMax`, `freezingTime`, `lastAged`, `rotten` | a cook transition | item aging is server-owned and never crosses [#1242/M/n=1] | `td1-20260910-192457` |
| `offAge`, `offAgeMax` | a cook hook writing the never-ages sentinel | desync whole: after the hook wrote 1 000 000 000 to both, the client still read 53 and 60, differences of 999 999 947 and 999 999 940, on two post-cook snapshots 11.1 s apart, and nothing later repaired it, so the client still thinks the meat spoils [#1401/M/n=1, #1667/M/n=1] | `td1-20260910-192457` |
| `isCookable` | a cook transition | desyncs: the server went true to false while the client stayed true, so the client's copy will re-enter the cooking block whenever it does tick [#1402/M/n=1] | `td1-20260910-192457` |
| `isCustomWeight` | a cook transition | desyncs: the server went false to true while the client stayed false, and it is the field that makes the two weight readings legible [#1403/M/n=1] | `td1-20260910-192457` |
| `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` together | eleven item writes by one mod | none of the four is among the packet's fields and none arrives: the client read offAge 53 against the server's 1e9 and isCookable true against false [#1037/M/n=1] | `td1-20260910-192457` |
| `actualWeight` | a cook transition, two sessions | the server read 0 and the client 0.35, a gap of 0.35, and the mod's 30 per cent cut is discarded on the authoritative side rather than merely desynced — a reading that falsified the prediction of both sides settling at about 0.35; the split is `isCustomWeight` choosing a different arm on each side [#1404/M/n=2, #1106/M/n=1] | `td1-20260910-192457`, `td1b-20260910-202029` |
| `actualWeightUnmodded` | before and after cooking, two sessions | reads 0 on both sides at both moments, so that 0 is the display-name guard rather than a cook effect [#1405/M/n=2] | `td1b-20260910-202029` |
| `weight` (the plain getter) | a cook transition | uncarried and not desynced: both sides read 0.5, which is why the observable desyncs on that item are four rather than five [#1406/M/n=1] | `td1-20260910-192457` |
| `isCooked`, `cookingTime`, `minutesToCook`, `minutesToBurn` | a cook transition | synced: the client's cooked true is the packet's rather than its own, and the cooking time read 301.061554 on both sides rather than the flat 301 that was pinned, because the server's own tick had added heat over 1.5 times 0.05 [#1410/M/n=1] | `td1-20260910-192457` |
| the four uncarried fields | the pre-cook baseline against the two post-cook snapshots | a change rather than a standing difference: the baseline snapshot is not desynced at all, and the server half of the four reproduced on a second run [#1416/M/n=1] | `td1-20260910-192457` |
| `isIncWeight`, `isIncWeightLot`, `isDecWeight` | six snapshots, the baseline in the neither arm and five across two gain arms | agree on both sides at every snapshot and match the arm the server's own macros predict at each one, so a client-side suffix derived from them is correct on a multiplayer client; both sides' trait lists were empty throughout, so the flags' dependency on both sides computing the same gain threshold is untested [#1490/M/n=1] | `td2-20260910-231655` |
| the same three flags | four snapshots inside the neither arm | read false on both sides throughout, but under the weight update's neither arm only: at weight 80 the gain threshold is 1000 and the loss threshold 0, and calories ran 798.45 down to 782.90 strictly between them, an arm in which both sides answer false whether or not the client recomputes anything [#1347/M/n=1] | `td3-20260911-001948` |

<a id="staircase"></a>
### The staircase a client-side reader sees

A client-side reader of the nutrition store is a staircase that steps only when a packet lands, while the server is a ramp, because the nutrition update jumps past its three explicit macro decays and the calorie update on a client arm, so a cross-side gap is a timing reading rather than float noise and equal is the wrong verdict to look for [#1483].
Weight is the exception that proves the mechanism: its cross-side gap is negative at every post-action snapshot, the opposite sign to the macros', which is the weight update's client skip measured rather than read, because the client never recomputes weight and its staircase sits below a rising server [#1484/M/n=1].
That weight arm was exercised on the gain side only, so the loss arm and its opposite-signed band are untested.

The way to read one is a band, not an equality.
The cross-side comparison of the five drawn numbers is a 30-row table dated 2026-09-10 — six snapshots by five fields — each row graded against a band computed from that snapshot's own signed read skew rather than against equality, with the client half read first at every tag so the skew is non-negative [#1485/M/n=1].
The decay rate the bands use is derived from the fixture's own day-length setting and corroborated by the session's own slope.
Because the band is built from the snapshot's own read skew rather than from a fixed tolerance, a slow round trip widens the band instead of failing the row.
A reading outside its band is a finding rather than a reason to re-run.
The construction is what lets a client-side reader be graded at all, since the two sides are never sampled at the same instant.
For a probe author the operative part is the ordering: read the client half first at every tag, so the skew has a known sign.

| tag | field | server | client | gap | band | in band |
|---|---|---|---|---|---|---|
| `baseline` | calories | 798.3768920898438 | 799.2306518554688 | 0.853759765625 | [0.58496, 1.036544] (r 0.256) | **yes** |
| | carbs | −0.35502830147743225 | −0.16830335557460785 | 0.1867249459028244 | [0.12796, 0.226744] (r 0.056) | **yes** |
| | lipids | −0.11462342739105225 | −0.054337941110134125 | 0.06028548628091812 | [0.0413128, 0.0732059] (r 0.01808) | **yes** |
| | proteins | −0.08723551779985428 | −0.04135453701019287 | 0.04588098078966141 | [0.0314416, 0.0557142] (r 0.01376) | **yes** |
| | weight | 80 | 80 | 0 | [−7.63e-06, +7.63e-06] (ρ 0, neither arm) | **yes**, bit-identical |
| `t0` | calories | 1999.052978515625 | 1999.7698974609375 | 0.7169189453125 | [0.389378, 0.841732] | yes (ungraded: latency) |
| | carbs | −0.9847724437713623 | −0.8281469941139221 | 0.15662544965744019 | [0.085176, 0.184128] | yes (ungraded) |
| | lipids | −0.3179408013820648 | −0.26737314462661743 | 0.05056765675544739 | [0.0274997, 0.059447] | yes (ungraded) |
| | proteins | −0.24197259545326233 | −0.20348750054836273 | 0.0384850949048996 | [0.020929, 0.0452429] | yes (ungraded) |
| | weight | 80.00038421184581 | 80.00009155273438 | **−0.00029265911143738776** | [−0.00034942, −0.00015048] (ρ +1.0395e-4, gain ×1) | yes (ungraded) |
| `t+3s` | calories | 1997.18310546875 | 1998.2333984375 | 1.05029296875 | [0.39271, 1.16661] | **yes** |
| | carbs | −1.3930763006210327 | −1.16377592086792 | 0.2293003797531128 | [0.085904, 0.255192] | **yes** |
| | lipids | −0.449764609336853 | −0.37573328614234924 | 0.07403132319450378 | [0.0277347, 0.0823906] | **yes** |
| | proteins | −0.3422987163066864 | −0.28595632314682007 | 0.05634239315986633 | [0.0211078, 0.0627043] | **yes** |
| | weight | 80.00114177246815 | 80.00071716308594 | **−0.0004246093822075636** | [−0.00048089, −0.00015168] (ρ +1.0385e-4, gain ×1) | **yes** |
| `t2+0s` | calories | 1994.6201171875 | 1995.414794921875 | 0.794677734375 | [0.390159, 0.970276] | yes (ungraded) |
| | carbs | 799.7754516601562 | 799.9495239257812 | 0.174072265625 | [0.085344, 0.21224] | yes (ungraded) |
| | lipids | −0.6303383708000183 | −0.574343204498291 | 0.055995166301727295 | [0.0275539, 0.0685232] | yes (ungraded) |
| | proteins | −0.4797268807888031 | −0.4371109902858734 | 0.04261589050292969 | [0.0209702, 0.0521504] | yes (ungraded) |
| | weight | 80.0030074610022 | 80.00204467773438 | **−0.0009627832678233972** | [−0.00118693, −0.00046658] (ρ +3.1116e-4, gain ×3) | yes (ungraded) |
| `t2+3s` | calories | 1992.5694580078125 | 1993.6204833984375 | 1.051025390625 | [0.392219, 1.2934] | **yes** |
| | carbs | 799.3273315429688 | 799.5572509765625 | 0.22991943359375 | [0.085792, 0.282912] | **yes** |
| | lipids | −0.7747547030448914 | −0.7007291913032532 | 0.07402551174163818 | [0.0276986, 0.0913402] | **yes** |
| | proteins | −0.5896369814872742 | −0.5332988500595093 | 0.05633813142776489 | [0.0210803, 0.0695155] | **yes** |
| | weight | 80.0054916049794 | 80.00421905517578 | **−0.0012725498036161298** | [−0.001578, −0.00046858] (ρ +3.1084e-4, gain ×3) | **yes** |
| `final` | calories | 1982.8211669921875 | 1983.617431640625 | 0.7962646484375 | [0.325958, 1.03523] | **yes** |
| | carbs | 797.1956176757812 | 797.3696899414062 | 0.174072265625 | [0.071288, 0.226408] | **yes** |
| | lipids | −1.4610061645507812 | −1.4050037860870361 | 0.05600237846374512 | [0.0230158, 0.0730974] | **yes** |
| | proteins | −1.111916422843933 | −1.0692952871322632 | 0.04262113571166992 | [0.0175165, 0.0556317] | **yes** |
| | weight | 80.01726107890681 | 80.01630401611328 | **−0.0009570627935318043** | [−0.00125821, −0.00038614] (ρ +3.0932e-4, gain ×3) | **yes** |

The table is the comparison alone; every cell in it comes from the run the caption's row names.
Every macro gap at every one of the six snapshots landed inside its band, including the two the settle rule declined to grade, so the five numbers a client-side reader of this shape draws are the server's, late by under a second, and there is no unsynced-field authority hazard in reading them [#1486/M/n=1].
The falsifier was never approached, so the rule is validated as consistent with a once-a-second push rather than as tight.
What a client's copy of a server-owned object is and is not — a push, not a simulation — is [`platform/mp-model.md#what-a-client-copy-is`](../platform/mp-model.md#what-a-client-copy-is).

## Walls and bounds
<a id="walls"></a>

- A zero-valued item-stats field is not trustworthy on a client: any of the twenty conditionally-written fields arrives carrying the previous packet's value whenever the sending item's own value is zero, so a client-side read on an item that should be zero may be reading another item's number; only the cooking time has been seen to carry over, and the other nineteen are read off the write and parse guard lists [#0361/M/n=1].
- The unmodded actual-weight getter returns zero whenever an item's display name equals its full type: the same instance read a weight of 0.3 on the client, where the name resolved, and zero on the server, where the mod item's display name read as its full type [#3207/M/n=1].
- That last reading is the display-name guard and never a weight fact; the weight facts are the plain getter and the direction flags.
- A mod cannot add a field to the item packet, nor depend on a field it omits: the class has no reset, no registry, no callback and no per-field opt-in [#1144/M/n=1].
- A mod cannot trust a zero-valued packet field, for the reason the first line gives [#1146/M/n=1].
- A mod cannot trust a cooked food's thirst value read on a client [#1147/M/n=1].
- A mod cannot trust a live item field's client copy to tick; that wall's own reading is not settled, and it is bounded to one item, one window and one fixture [#1148/M/n=1/unverified].
- A mod cannot push a player stat from the client, nor observe or suppress the player-stats write [#1149/M/n=1].
- A mod cannot push an item field from the client either, because every arm of the item-stats send is a server-to-client fan-out [#1150/C/C-only].
- A new item absent from the translation table ships a zero weight to every client [#1166/C/C-only].
- The engine has no packet other than the injuries packet that names walk speed: a jar-wide grep for `walkSpeed` returns `PlayerInjuriesPacket` as the only packet class, beside `IsoGameCharacter`, `IsoPlayer`, `NetworkPlayerAI` and the two fake-client classes; the grep is literal, so a packet carrying the speed under another name is not excluded [#2625/C/C-only].
- Every per-arm reading on this page is taken on the dedicated-server path with one real client, one fixture, and one item or one character per arm; where an arm was read on two runs the register row says so, and no arm is repeated across builds.
- Floats arrive over the command bus rounded to six decimals, so no reading here supports a bit-for-bit claim except the two whose rows state one.
- No arm on this page was taken with more than one client attached, so nothing here speaks to what a second client's copy holds.
- Single-player is never claimed anywhere on this page: on that path the server arm and the client arm are the same process and no packet is involved.

Not covered: the full item-serialisation carriers, which are the only route an item's stored blob travels on and which no run in this library has read; the save and load round trip; the receiving setters behind `BodyDamage.loadMainFields`, `Fitness.load` and `BodyPart.sync`, which this page names but does not decode; every packet outside the food, nutrition and character set above; a live arm of the four character packets; and the transport layer beneath all of them.

## Open
<a id="open"></a>

- Which of the twenty conditionally-written item-stats fields actually carry over at runtime — only the cooking time has been seen to, in a case whose receiver happened to be non-cookable, which the mechanism says is incidental but no run has shown to be; settled by one confirmation, syncing an item with a distinctive cooking time and then a zero-valued item [#0372/M/n=1/open].
- Whether the item packet really carries `cooked` — the field is in the list but both sides already read false when they were read, so the match is uninformative; settled by one divergence test, setting it on the server only and then reading the client [#0377/C/C-only/open].
- Whether the two weight-direction flags a client-side spice gate reads can desync — the risk follows from the flags being absent from the player packet, and no session has driven the character out of the neither arm; settled by a session that drives calories above 1000 or below 0 and re-reads both sides [#1348/C/inference/open].
- Whether a relog or a save round trip repairs the client's copy of the four uncarried fields, and whether the client keeping the cookable flag true makes its copy re-enter the cooking block and call a nil hook, which neither session reproduced; the save and load path is different from the item-stats packet and nothing in these sessions reads it [#1434/C/inference/open].
- Decision: whether a per-instance mod nutrient rides an existing packet field, item modData or the command bus — the packet has no per-field opt-in and the receiver drops anything outside its field list [#1144/M/n=1].
- Decision: whether a client-side reader may display a cooked food's thirst value at all, or must re-derive it from the script — the value it reads is halved once per hop [#1038/M/n=2].
- Decision: whether the mod re-derives freshness on the client or hides it there — the aging fields are server-owned and never cross [#1242/M/n=1].
- Decision: whether a translation entry is a hard requirement of every new mod item — without one the wire's weight field is zero on every client [#1028].
- Decision: whether the mod pushes the trait block after its own trait writes, and with which other bits — a push replaces the client's whole trait list rather than adding to it [#2617/C/C-only].
- Decision: whether a client-side reader of perk levels reads a remote player's perk list or the three remote level fields — the perk-level packet never writes the perk list and writes the remote fields alone [#2623/C/C-only].

## See also

- [`platform/mp-model.md`](../platform/mp-model.md) — what a packet is, when each fires, the cached packet object, wipe-and-replace, and the routes a mod can use instead of the wire.
- [`food-item-model.md`](food-item-model.md) — the item's state axes and script keys, which decide what there is to put on the wire.
- [`eating-pipeline.md`](eating-pipeline.md) — the order of writes inside `Eat` and the packets it sends.
- [`nutrition-core.md`](nutrition-core.md) — the store the player packet carries, and its clamps.
- [`body-and-weight.md`](body-and-weight.md) — the weight bands the direction flags are computed from.
- [`character-stats.md`](character-stats.md) — the stat registry whose order the stats packets walk and whose indices the sync-stats mask selects.
- [`perks-and-strength.md`](perks-and-strength.md) — the perk and experience stores the experience packet replaces.
- [`exercise-and-training.md`](exercise-and-training.md) — the fitness object the player-fields packet's fitness block carries.
- [`health-surfaces.md`](health-surfaces.md) — the body-damage and per-part state the main-field block and the body-part packet carry.
- [`perception-speed.md`](perception-speed.md) — the movement speeds the injuries packet carries.
- [`other-mods/longtermpreservation.md`](other-mods/longtermpreservation.md) — the item-side teardown most of the desync arms were taken on.
- [`other-mods/simplestatus.md`](other-mods/simplestatus.md) — the read-side teardown behind the staircase and the band method.
- [`other-mods/autocook.md`](other-mods/autocook.md) — the nested-modData arm and the weight-flag arm that stayed trivial.
- [`reference/wall-map.md`](../reference/wall-map.md) — every sync verdict cited above, in one place.
- [`reference/experiments.md`](../reference/experiments.md) — the named experiments, for the rows under Open that have one.
