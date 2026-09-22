# Spoilage — the age clock, freezing and rot
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: what moves a food item's age, what freezing and refrigeration multiply it by, what rot changes and what it leaves alone, which side of a session owns the clock, and the sealed items that have no clock at all; the thresholds age is compared against are `facts/food-item-model.md`, the eat-time effect of rot is `facts/eating-pipeline.md`, and the item packet's field list is `facts/wire-packets.md`.

## Key facts

- `age` advances by the elapsed world hours times `getFoodRotSpeed()` divided by 24, so at the default rot speed of 1.0 one game day adds about one day of age [#0220/M/n=1].
- A frozen item multiplies its elapsed aging hours by 0.0, so aging stops rather than slowing [#0222/M/n=1].
- An item in a powered fridge or freezer multiplies its elapsed aging hours by `getFridgeFactor()` [#0223/C/C-only], whose sandbox default is 0.2 [#0224/C/C-only].
- `freezingTime` rises by the elapsed world hours divided by 4 and times 100, so an item reaches 100 per cent frozen in four game hours [#0229].
- `offAge` and `offAgeMax` default to 1000000000, the never-ages sentinel, at which `canAge()` is false [#0221].
- Not one sealed can declares `DaysFresh`, so a sealed can never rots and is never removed [#0308/C/snapshot].
- Across the three aging methods the only item fields written are `age`, `lastAged`, `heat`, `freezingTime` with `frozen` through its setter, `lastFrozenUpdate`, and `fertilized` set to false [#0253].
- Aging never touches `hungChange`, `thirstChange`, `calories`, `carbohydrates`, `proteins`, `lipids`, `unhappyChange`, `boredomChange` or `stressChange`, so every rot effect is computed at read time by the `Food` getters [#0254/M/n=1].
- The stored `getHungChange` stays at -0.4 at every age while the read-time `getHungerChange` reads -0.4 fresh, -0.307692 stale and -0.181818 rotten [#0247/M/n=1].
- `Food.update` calls `updateAge` only when it is running on a server, so a client never advances an item's age [#0245].
- A client's copy of an item gains no age at all over a full accelerated game day: the client's age change was 0 against 1.00777 on the server [#0249/M/n=1].
- The server's inventory-item tick runs about once every 5 s rather than every frame, with heat decaying at about 0.036 per real second at this fixture's multiplier of 4.7961 [#1419/M/n=2].
- `ItemPickerJava.rotItem` sets 75 per cent of spawned perishables to `getOffAgeMax()` and 95 per cent of the remainder to `getOffAge()` [#0239].
- The sandbox option `DaysForRottenFoodRemoval` defaults to -1, which disables removal, and every shipped preset sets -1 [#0233/C/snapshot].

## How it works

<a id="formula"></a>
### The aging formula

An item's age is a single float in days and exactly one method advances it.
That method does more than arithmetic: it also drives freezing, tracks the container's temperature, and decides whether a rot transition has just happened.
The order it does those things in is what makes the rest of this page legible.
Read it as a fixed sequence rather than as a set of independent effects.

`Food.updateAge` reads the world clock, updates freezing, clamps `lastAged` forward, lerps `heat` toward the container, applies the frozen and fridge rate modifiers to the elapsed hours, advances `age`, and only then fires the rot transition event or the stats sync [#0219].

```java
// zombie/inventory/types/Food.updateAge(boolean sync)   @0–@510  L736–L783
float nowH = GameTime.getInstance().getWorldAgeHours();          // @0   L736
ItemContainer c = getOutermostContainer();                       // @8   L738
updateFreezing(c, nowH);                                         // @13  L739
lastAged = GameTime.checkHours(lastAged, nowH);                  // @19  L741   (last<0 ? now : min(last,now))
if (nowH <= lastAged) return;                                    // @35  L742
double dH = nowH - lastAged;                                     // @44  L743

// heat tracks the container: lerp over a 1/3-hour window, else snap
if (c != null && heat != c.getTemprature()) { … }                // @53–@139 L744–L751

// ---- rate modifiers ----
if (isFrozen())                        dH *= 0.0;                // @140 L754-755   FROZEN STOPS AGING
else if (isInFridge(c) || isInFreezer(c)) {                      // @156 L756
    if (c.getSourceGrid() != null && c.getSourceGrid().haveElectricity())
        dH *= getFridgeFactor();                                 // @172 L757/L760
    else if (elecShutModifier > -1 && lastAged < elecShutModifier*24) {
        float cut = Math.min(elecShutModifier*24, nowH);         // @230 L762
        dH = (cut - lastAged) * getFridgeFactor();               // @246 L763
        if (nowH > elecShutModifier*24) dH += nowH - elecShutModifier*24;   // @261 L765-766
    }
}

boolean wasFresh  = !burnt && offAge    < 1e9 && age <  offAge;  // @294 L771
boolean wasRotten = !burnt && offAgeMax < 1e9 && age >= offAgeMax;// @331 L772

age      += (dH * getFoodRotSpeed()) / 24.0;                     // @368 L774   <-- THE FORMULA
lastAged  = nowH;                                                // @391 L775

if (!GameServer.server && (fresh or rotten flipped))
    LuaEventManager.triggerEvent("OnContainerUpdate", this);     // @470 L779-780
if (sync && GameServer.server) GameServer.sendItemStats(this);   // @497 L782-783
```

`age` advances by the elapsed world hours times `getFoodRotSpeed()` divided by 24, so at the default rot speed of 1.0 one game day adds about one day of age [#0220/M/n=1].

That line is both read from the code and measured, but the measurement is one item on one fixture against a dedicated server at a sandbox rot speed of three.
The measured day came in slightly under the prediction over the window that contains it.
The qualitative result — about a day of age per game day — is unaffected, and the shortfall itself is under [Open](#open).

`offAge` and `offAgeMax` default to 1000000000, the never-ages sentinel, at which `canAge()` is false [#0221].

`Food.updateRotting` returns immediately when `offAgeMax` is still the 1000000000 sentinel [#0241].

An item that declares no shelf life is therefore inert on both halves of the clock.
Its age still advances, but nothing ever reads that age as a transition and nothing ever removes the item.
That single sentinel is the whole mechanism behind sealed goods, and it is the value a mod should test.

Aging never touches `hungChange`, `thirstChange`, `calories`, `carbohydrates`, `proteins`, `lipids`, `unhappyChange`, `boredomChange` or `stressChange`, so every rot effect is computed at read time by the `Food` getters [#0254/M/n=1].

Rot is a view of age, not a mutation of the item.
A stored macro is a pure function of the script value and of how much of the item has been eaten, and it stays that function from the moment the item spawns to the moment it is destroyed.
A mod that wants rot to cost calories has to change the eat path or the getters.
Changing the item does not do it, because nothing writes the item.

The axis itself — what `isFresh`, the un-named stale band and `isRotten` derive from, and how the script keys seed the thresholds — is stated once on [food-item-model.md](food-item-model.md#state-axes).
This page states what moves the age those thresholds are compared against, and the measured consequences of moving it.

One shipped item makes the two thresholds equal: `item RatKing` sets both `DaysFresh` and `DaysTotallyRotten` to 0, so it spawns already rotten with an age of 0 at or above an `offAgeMax` of 0 while `canAge()` is still true [#0383/C/snapshot].

<a id="containers"></a>
### Fridge, freezer and frozen

Two container effects reach the aging step and they are not the same effect.
Refrigeration is a multiplier on elapsed time and depends on the electrical grid.
Freezing is a state the item itself carries, reached gradually and left gradually, whose effect at the top of its range is total.
An item in a running freezer is subject to both in sequence: first as a fridge, then, once it has actually frozen, as a stop.

A frozen item multiplies its elapsed aging hours by 0.0, so aging stops rather than slowing [#0222/M/n=1] — measured on one item on one fixture over 1.172 game-hours in a player inventory, with an age change of 0.000000.

An item in a powered fridge or freezer multiplies its elapsed aging hours by `getFridgeFactor()` [#0223/C/C-only].

That branch is read from the code and never measured: the container multipliers need a placed, powered appliance, which the fixture world does not offer at the spawn point.
The frozen arm above needed no appliance, and so it is the one arm of this subsection that carries a measurement.

The unpowered fridge and freezer grace branch runs only while `elecShutModifier` is above -1 and `lastAged` is below `elecShutModifier` times 24 hours, ageing at the fridge factor up to that cutoff and at the full rate beyond it [#0226].

So refrigeration survives the loss of power for a bounded stretch of the run and then stops entirely.
An item that sat in a dead fridge past the cutoff is aged at the full rate for every hour beyond it, and nothing carries the fridge's benefit forward once the window has closed.

Which containers count is decided by two predicates, and they are ordered.

`ItemContainer.isFreezer()` is true when the container's type equals the freezer container type or the literal freezer [#0235].

`ItemContainer.isFridge()` returns false for anything that is already a freezer, then tests the literal fridge, and otherwise reads the parent object's `IsoPropertyType.IS_FRIDGE` property; a player inventory is neither fridge nor freezer [#0236].

The second predicate excluding the first matters for anything that reads the two as a pair.
A test written as fridge-or-freezer is the complete cover; a test written as fridge alone silently drops every freezer.

`ItemContainer.getTemprature()` is the only source of `Food.heat`, and it answers by container condition [#0237].

| Container condition | `getTemprature()` |
|---|---|
| `customTemperature != 0` | that value (short-circuits everything below) |
| powered fridge or freezer | `0.2` |
| powered stove, or `type == "microwave"` with an `IsoStove` parent | `IsoStove.getCurrentTemperature()` = `(currentTemperature + 100) / 100` |
| `IsoBarbecue` / `IsoFireplace` parent | that object's `getTemperature()` |
| unpowered fridge/freezer, inside the elec-shutoff window, time-of-day < 13:00 | `Lerp(0.2, 1, (timeOfDay − 7) / 6)` |
| everything else | `1.0` (ambient) |

Heat is the input to freezing and to the cook block alike, which is why a custom container temperature is the cheapest lever a future run has on either.
It short-circuits every branch below it and needs no world object at all.
What the cook block does with that heat is [cooking-and-recipes.md](cooking-and-recipes.md#cook-block).

An item's `heat` is lerped toward its container's temperature over a window of one third of a game hour, twenty game minutes, and snapped to it otherwise [#0228].

`freezingTime` rises by the elapsed world hours divided by 4 and times 100, so an item reaches 100 per cent frozen in four game hours [#0229].

`freezingTime` falls by the elapsed world hours divided by a thaw time of 1.5 hours and times 100, doubled in a powered fridge and divided by six when the container is above 1.0 [#0230/C/C-only].

The thaw side is a code reading only.
Two runs of the same script disagreed with each other and with the code, so no thaw number anywhere in this library is quotable as measured; the disagreement is under [Open](#open).

The `frozen` flag flips only at the boundaries: `setFreezingTime` sets it true at 100 or above and false at 0 or below, so an item at 44.6 per cent is still frozen [#0231/M/n=1].

That boundary rule is what makes the stop total rather than gradual.
Between the two boundaries the percentage moves continuously while the flag does not move at all, so a half-thawed item is still being aged at zero.
The rate is a step function of the flag, not a function of the percentage.

<a id="spawn-age"></a>
### The age an item spawns with

An item does not enter the world at age zero.
Loot generation pre-ages it against the length of the run, so that a house cleared late in a game holds food that has already spoiled, and then rolls separately for whether the item is outright rotten.
Both steps run before any tick of the clock described above, and both are invisible afterwards: what survives is just an age.

`Food.setAutoAge()` is called from exactly one place, `ItemPickerJava.doRollItemInternal`, and pre-ages a spawned item by the world age plus the time since the apocalypse less one times 30 days, discounting fridge time by `getFridgeFactor()` and freezer time as zero with `freezingTime` set from the leftover, then multiplying by `getFoodRotSpeed()` [#0238].

`ItemPickerJava.rotItem` sets 75 per cent of spawned perishables to `getOffAgeMax()` and 95 per cent of the remainder to `getOffAge()` [#0239].

Read together, the overwhelming majority of perishable loot is stale or rotten the moment it is generated.
The sandbox rot speed scales the pre-aging as well as the ticking clock, so a slower world spawns fresher loot and not merely loot that spoils more slowly.
The exemption that keeps sealed goods out of that roll is stated with the rest of the sealed mechanism, at [sealed cans](#sealed).

<a id="sealed"></a>
### Sealed cans, the replacement links and the ones a dataset cannot resolve

Sealed is not a flag in the engine.
It is the absence of a shelf life, plus a pair of script keys that the spawn-rot roll happens to test, plus a set of opened variants that do declare a shelf life.
Three different markers look as though they mean sealed and only two of them do anything.
A mod that picks the wrong one silently gets the wrong set of items.

`Packaged` is copied onto the instance and readable as `Food.isPackaged()`, which has no Java caller in the jar and no vanilla Lua reader, so it is a pure marker for scripts and mods [#0306/C/C-only].

That reading is a whole-jar reverse-reference scan plus a grep of the vanilla Lua tree, so a reader outside those two places would not show.

`CannedFood` is never copied onto the instance and has no getter: it is read only off the script object, by `InventoryItem.getStringItemType()`, by `ItemPickerJava.getLootType`, which maps it to the canned-food loot sandbox modifier, and by the spawn-rot exemption [#0307].

The spawn-rot roll exempts any item whose script sets both `cannedFood` and `cantEat` [#0240].

Not one sealed can declares `DaysFresh`, so `offAge` and `offAgeMax` stay at the 1000000000 sentinel, `canAge()` is false and `updateRotting` returns at once: a sealed can never rots and is never removed [#0308/C/snapshot] — all 21 sealed cans of the 2026-09-10 script snapshot.

Opening a can is what starts its clock: the opened variants declare the `DaysFresh` and `DaysTotallyRotten` thresholds the sealed item lacks, along with `HungerChange`, `EvolvedRecipe`, a tin-can `ReplaceOnUse` and `IsCookable` [#0309/C/snapshot].

A mod that wants sealed semantics should key off `getOffAgeMax()` still holding 1000000000, or off the `CannedFood` and `CantEat` pair, never off `isPackaged()` [#0316/C/inference].

That is an inference from the counts and the sentinel rather than a measurement, and it is the practical form of everything above.
The sentinel is what the engine itself tests, the key pair is what the spawn roll tests, and the packaging flag is read by nothing.

Home canning rewrites the age axis on the cook transition, setting `offAgeMax` to 1560 and `offAge` to 730 and rescaling `age` by the old ratio of age to `offAgeMax` — about two years to stale and 4.3 years to rotten, with the fraction consumed preserved [#0310].

Preserving the ratio rather than the age is the part worth copying.
The item keeps how far through its life it was and not how many days it had accumulated, so a nearly-spoiled ingredient does not come out of the jar fresh.
A mod can rewrite a crafted instance from that same cooked hook [#1154/M/n=1].

`ReplaceOnUse` names the leftover container: the eat action's custom-weight branch uses the replacement's weight as its floor, and the inventory context menu and the dump-contents action build the replacement [#0311].

With `ReplaceOnRotten` set, `updateRotting` ages the item every tick and, once it is rotten, creates the replacement, copies `age` and the condition states onto it and destroys the original [#0243].

All 8 `ReplaceOnRotten` links conserve every macro — `Base.SugarBeetSyrupPot` to `Base.SugarBeetSugarPot` and the seven ice-cream melts are zero in all four macros and in hunger and thirst, with only `thirstChange` in `absentMacros` [#0755/C/arith.].

Every `ReplaceOnRotten` swap is server-only: `Food.updateRotting` returns immediately on a client and it is the method that both ages the item and creates the replacement, so a client never performs one of the 8 melts [#0757].

110 `ReplaceOnUse` and 42 `ReplaceOnDeplete` links join the 3 cooked and 8 rotten ones; 12 of the 163 carry a delta, counting `Base.Pumpkin` to `Base.PumpkinSeed`, and the other 151 are refused by name — 114 as `no-nutrition` and 37 as `not-in-dataset` [#0756/C/snapshot].

The cooked links and what a type change moves belong to [cooking-and-recipes.md](cooking-and-recipes.md#type-change).
The rotten and use links are stated here, because those two are driven by the rot path and the eat path this page owns.
The refusals above are not all the same kind of refusal, and the dataset says which is which.

37 `ReplaceOn*` links in the food scan do not resolve to a scanned id — 23 `ReplaceOnUse` and 14 `ReplaceOnDeplete` over 16 distinct targets, 15 of them real items outside the food set and one defined nowhere at all [#0607/C/snapshot].

`items/food.txt:6531` `item HotDrinkRed` writes `ReplaceOnUse = Base.MugRed`, no `item` block anywhere under `media/scripts` defines `MugRed`, and `EN/ItemName.json:3069` still carries its name — `42.20.4` translates an item it never defines [#0653/C/snapshot].

So an unresolved replacement link is the expected signal that a link leaves the food set, with exactly one exception, and that exception is a vanilla data defect.
The definition went away while both the translation entry and the link outlived it.
A mod that walks replacement links has to tolerate a target that no `item` block defines at all, not merely one that is not food.

<a id="writes"></a>
### Which side writes age, and how often

The whole of the lifecycle above belongs to the server.
Not one branch of it is shared with a client, and no packet carries the result.
A client's idea of an item's freshness is whatever the last full serialization of that item happened to carry.
This is the single most consequential fact on the page for a multiplayer mod.

`Food.update` calls `updateAge` only when it is running on a server, so a client never advances an item's age [#0245].

`Food.updateRotting` returns immediately on any multiplayer client, so no client ever runs the rot path [#0242].

A client's copy of an item gains no age at all over a full accelerated game day: the client's age change was 0 against 1.00777 on the server [#0249/M/n=1].

Age never reaches a client: the server went from 0 to 0.006526 while the client stayed at 0 [#1412/M/n=2].

Those two are separate sessions reading the same field, one across an accelerated day and one across a cook transition in another mod's teardown.
They agree, and what the item packet does and does not declare is [wire-packets.md](wire-packets.md#item-stats-packet).

Across `updateAge`, `updateFreezing` and `updateRotting` the only item fields written are `age`, `lastAged`, `heat`, `freezingTime` with `frozen` through its setter, `lastFrozenUpdate`, and `fertilized` set to false [#0253].

The item-stats sync on the aging path is rate-limited to one call per 1000 ms, and only the no-argument `updateAge()` passes that limit's result [#0232].

The sync argument gates the only item-stats send on the aging path and `Food.update`'s own aging call passes false, so the rot-transition sync fires only from the no-argument aging call, and that packet does not carry the new age anyway [#0356].

Both halves of that matter.
The rate limit means the aging path could never push more than one update a second even if it fired, and the argument means the ordinary ticking route never asks it to.
Whether the syncing form is reached for ordinary food at all is under [Open](#open).

How often the server runs any of this is a property of the item tick rather than of the aging code.

`InventoryItem.update()` is called by the cell's item processing for world and container items and by the character's recursive item updater for every non-zombie character's inventory, once per tick and with no side guard [#0324/C/C-only].

The server's inventory-item tick runs about once every 5 s rather than every frame, with heat decaying at about 0.036 per real second at this fixture's multiplier of 4.7961; the mechanism is that the server arm of the time multiplier is real-time-delta driven and clamped at 6 s while the temperature update acts only once its accumulator reaches 10.0 [#1419/M/n=2].

That cadence is bounded three ways on one session and reproduced on a second, on one fixture with one item.
It is why a driver that polls an item faster than the tick reads the same value several times over: the plateau is the tick, not the instrument.

<a id="measured"></a>
### The measured arms

Every reading below is one item, `Base.Steak`, on the fixture default, with client-side age writes on a server-spawned item so that nothing is aging while the getters are read.
Each row names the bound it was taken under and the run it rests on.

| Reading | Measured | Bound | Run | |
|---|---|---|---|---|
| the four macros against age | 220 kcal, 0 carbohydrates, 9.35 lipids and 31.62 proteins, identical at ages 0, 1.9, 2.1 and 4.1 | one item at four ages, read at the getter | `exp02-20260910-030433` | [#0246/M/n=1] |
| stored hunger against read-time hunger | stored -0.4 at every age; read-time -0.4 fresh, -0.307692 stale, -0.181818 rotten | one item at four ages, client-side age writes | `exp02-20260910-030433` | [#0247/M/n=1] |
| the stale band | at age 2.1 on an item with `offAge` 2 and `offAgeMax` 4, both `isFresh` and `isRotten` read false | one item on one fixture | `exp02-20260910-030433` | [#0248/M/n=1] |
| one forced syncing server tick | `age` advanced by 0.000388 | the server was aging the item concurrently, so the tick's own contribution is not isolated | `exp02-20260910-030433` | [#0250/M/n=1] |

The stale band is the row worth dwelling on.
The engine has three states and names only two of them, so an item can be neither fresh nor rotten, and a mod that branches on the two predicates alone has an unhandled middle.

The page's other measured arms belong to the mechanisms they bound rather than to this table.
The rate itself is at [the aging formula](#formula), the frozen multiplier and the flag boundary at [fridge, freezer and frozen](#containers), and the client's zero at [which side writes age](#writes).

<a id="sandbox"></a>
### The rot sandbox options

Four sandbox options reach the aging path.
Two of them are multipliers, one bounds the grace period after the power fails, and one decides whether rotten food is ever deleted.
Each reaches the aging code through a getter rather than being read as an option, so the enum mapping below is what a mod actually needs.

| Option | Values | Default | What it does | |
|---|---|---|---|---|
| `FoodRotSpeed` | enum 1 to 5, mapping to 1.7, 1.4, 1.0, 0.7 and 0.4 | 3, and therefore 1.0 | multiplies the elapsed hours the age formula converts into days | [#0225/C/C-only] |
| `FridgeFactor` | enum 1 to 6, mapping to 0.4, 0.3, 0.2, 0.1, 0.03 and 0.0 | 3, and therefore 0.2 | multiplies the elapsed hours inside a powered fridge or freezer | [#0224/C/C-only] |
| `ElecShutModifier` | days, or -1 | 14 in four of the five shipped presets, -1 in `SixMonthsLater` | bounds the unpowered fridge and freezer grace branch; -1 disables the grace entirely | [#0227/C/snapshot] |
| `DaysForRottenFoodRemoval` | days, or -1 | -1, which disables removal, and every shipped preset sets -1 | gates whether rotten food is ever deleted at all | [#0233/C/snapshot] |

Both enums were decoded from the raw tableswitch, so the numeric mapping is established and the translation labels are not.
The labels themselves are under [Open](#open).

All five shipped presets set `FoodRotSpeed` to 3, and all set `FridgeFactor` to 3 except `Outbreak`, which sets 4 and so ages fridged food at 0.1 rather than 0.2 [#0234/C/snapshot].

Without `ReplaceOnRotten`, `updateRotting` acts only when `DaysForRottenFoodRemoval` is 0 or more, destroying the item past `offAgeMax` plus that many days [#0244].

No shipped preset enables that branch, so in practice vanilla never deletes a rotten item.
Rotten food accumulates and stays readable for as long as its container does.
A mod that assumes spoiled items eventually vanish is assuming a sandbox no preset ships.

## Walls and bounds
<a id="walls"></a>

- Every measured aging reading on this page rests on sandbox `FoodRotSpeed` 3, `FridgeFactor` 3, `DaysForRottenFoodRemoval` -1 and `ElecShutModifier` 14, on one live session on the fixture default against a dedicated server [#0252/M/one-fixture].
- The mirror says that in the freezer compartment the spoil rate is reduced by 25 times; no factor of 25 appears anywhere on the aging path — a freezer applies the same fridge factor as a fridge while the item is unfrozen, and once `freezingTime` reaches 100 the rate is 0.0, stopped rather than divided [#0362/M/n=1].
- The mirror says the spoil rate is reduced by 5 times in a fridge, repeated as increasing spoil time by 5 times; that is true only as the default — the fridge factor is a sandbox enum of 0.4, 0.3, 0.2, 0.1, 0.03 and 0.0 whose default 3 is that five times, it applies only on a powered grid, the `Outbreak` preset ships 4 for ten times, and unpowered food reverts to the full rate once the electricity-shutoff window closes [#0363/C/C-only].
- The mirror says that as food begins to rot its effects become more negative, which reads as blanket; rot leaves all four macros untouched — 220 kcal, 0 carbohydrates, 9.35 lipids and 31.62 proteins identical at ages 0, 1.9, 2.1 and 4.1 — and only the read-time hunger, stress, boredom, unhappiness and the sickness roll degrade, while thirst and endurance have no rot branch at all [#0364/M/n=1].
- The mirror's fridges table reads as a refrigeration roster; it groups tiles by category rather than by container type and carries no spoilage, power or temperature figure, and because the fridge test returns false for anything already a freezer, the cooled shelves and display counter tiles are its likeliest false positives [#0368/C/C-only].
- The container multipliers, the thaw rate and the single-player path are code readings with no measurement behind them; each is stated as such where it appears and carried in full under Open.

Not covered: the compost and grab-world-item routes into aging were never opened and no single-player process was ever booted, no fridge, freezer, generator or stove object was ever placed, so every container multiplier here is a code reading, and no wiki mirror exists for spoilage itself — the four mirror rows above are the whole of the secondary corroboration this page has.

## Open
<a id="open"></a>

- Whether the thaw rate reproduces: one run measured 47.25 per cent of `freezingTime` per game hour and a second run of the same script measured 67.8 per cent, against the code's 66.7 per cent at a thaw time of 1.5 hours — settled by a third run of the same phase at the same time speed and in the same container, with its artifact committed [#0251/M/uncommitted/open].
- Why the measured age gain over one accelerated game day is 1.00777 against 1.02320 predicted over the containing window of 24.556793 game hours at rot speed 3, a 1.5 per cent shortfall — settled by a run that brackets the item's own aging window rather than the wait loop's clock samples [#0371/M/n=1/open].
- What the fridge and freezer container multipliers actually are: they need a placed powered appliance whose container type is fridge or freezer on a square with electricity, which the fixture world does not provide at the spawn point — settled by a run that sets a container custom temperature, which short-circuits the container temperature getter, or that spawns an appliance [#0373/C/C-only/open].
- Whether food ages at all in single-player at default settings: the code gates the aging call on the server flag, returns from the rot path on clients and otherwise needs `ReplaceOnRotten` or a non-negative removal day count, leaving only the compost update and the grab-world-item path — settled by a single-player measurement, which a dedicated-server harness cannot give [#0374/C/C-only/open].
- Whether the syncing form of the aging call ever fires for ordinary food on a dedicated server: it has only two callers, the `ReplaceOnRotten` branch of the rot path and the compost update — settled by a live server log across a rot transition [#0375/C/C-only/open].
- What the translation labels of the fridge-factor and rot-speed enums are, the numeric mapping being all the raw tableswitch established — settled by reading the sandbox translation files [#0378/C/C-only/open].
- How an item whose fresh and rotten thresholds are equal behaves at eat time, where it takes the hundred-per-cent branch of the rot-sickness denominator — settled by eating `Base.RatKing` on a live server and reading the sickness roll [#0384/C/C-only/open].
- The design must decide whether its own nutrients degrade with age, and if so where: nothing in the engine writes a macro as an item ages, so any degradation is a getter change or an eat-path change rather than an item change [#0254/M/n=1].
- The design must decide which sealed marker it keys off, because the three candidates do not select the same set and only two of them are read by anything [#0316/C/inference].
- The design must decide whether a client ever needs an item's age, because no packet carries it and a client's copy never advances on its own [#1412/M/n=2].
- The design must decide what it does with rotten items the engine never removes, since the removal option is disabled in every shipped preset [#0233/C/snapshot].

## See also

- [food-item-model.md](food-item-model.md#state-axes) — the three state axes, the thresholds age is compared against, and the setters that write nothing.
- [eating-pipeline.md](eating-pipeline.md#modifiers) — what a stale or rotten item does to an intake at read time.
- [cooking-and-recipes.md](cooking-and-recipes.md#type-change) — the cook transition, the cooked replacement links and the deltas a type change applies.
- [wire-packets.md](wire-packets.md#item-stats-packet) — the item packet's field contract and the aging fields it omits.
- [other-mods/longtermpreservation.md](other-mods/longtermpreservation.md#mp) — a shipped mod that writes the never-ages sentinel onto ordinary food, and what desyncs when it does.
- [../platform/mp-model.md](../platform/mp-model.md#shapes) — the item save and load blob, the only carrier the aging fields have.
