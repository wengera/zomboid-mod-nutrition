# Intoxication and the water seats — four desk reads for Plan 4

Read 2026-10-05 by the Plan 4 Task 1 implementer (claude-opus-5-5) on the jar of build 42.20.4 (b0bbce05d5) through the local `pz-b42` toolchain (`./pz.sh methods|dump|refs|grep`, read-only), and on the shipped Lua and scripts of the install (read-only).
Access flags were read with a session-scoped scratch parser over the toolchain's own constant-pool module (`tools/cp.py`), as `docs/platform/jar-research.md` requires; the parser was not kept.
Nothing here was exercised on a live server: every sentence is a code reading, and every sentence marked **inference** goes beyond what the code says.
The claims this report lands are the Task 1 delta's `T1.1`–`T1.17` (`.superpowers/sdd/2026-10-05-plan-4-kinetics/task-1-claims-delta.tsv`); the section numbers below are the delta's `source` cells.

## 1. The intoxication decay

### The site

`BodyDamage.Update()V` (public), dumped whole (1167 lines of listing):

```text
   21  L2159  getstatic   GameClient.client ; ifeq 63
   27  L2160  Type.tryCastTo(parentChar, IsoPlayer)
   40  L2161  ifnull 63 ; isAlive ; ifeq 63
   51  L2162  isLocalPlayer ; ifne 62
   58  L2163  RestoreToFullHealth
   62  L2165  return                       <- every live player on a client returns here
   63  L2169  isGodMod ... L2172 return    (god mode: restore and return)
  211  L2198  thermoregulator ifnull 225
  222  L2199  Thermoregulator.update
  225–258     UpdateDraggingCorpse ... UpdateIllness (L2202–L2210)
  261  L2212  getOverallBodyHealth == 0 -> L2213 return
  ...
  527  L2263  stats  getstatic CharacterStat.INTOXICATION
  534         getDrunkReductionValue
  538         GameTime.instance.getMultiplier
  544         fmul
  545         Stats.remove                 <- the decay
```

- The decay is `INTOXICATION -= drunkReductionValue × GameTime.getMultiplier()` on every call (`@527–@548 L2263`), with **no** `getDeltaMinutesPerDay` factor [#2918/C/C-only].
- It sits after the client return (`@21–@62 L2159–L2165`), so in multiplayer it runs on the server only (as the rest of the body tick does, #2384) [#2918/C/C-only].
- The body's only Lua calls are `LuaEventManager.triggerEvent("OnPlayerGetDamage", …)` at `@1526 L2398` and later; there is no `LuaHookManager.TriggerHook` in the body, so no hook lets Lua skip the decay [#2918/C/C-only].

### The constants and the door

`BodyDamage.<init>`:

```text
  169  L95  ldc 400.0     putfield drunkIncreaseValue
  175  L96  ldc 0.0042    putfield drunkReductionValue
```

Flags (scratch parser): `drunkIncreaseValue` and `drunkReductionValue` are `private float`; `getDrunkReductionValue`, `setDrunkReductionValue`, `getDrunkIncreaseValue`, `setDrunkIncreaseValue` are `public`; `BodyDamage` is `public final` and in the exposer's class set (#2248).
`setDrunkReductionValue @0–@5 L2927–L2928` is a bare `putfield` [#2919/C/C-only].

- `jar-wide grep drunkReductionValue` → `BodyDamage` only; `jar-wide grep setDrunkReductionValue` → `BodyDamage` only (its own declaration — no caller); the shipped Lua (`media/lua`) names neither `DrunkReduction` nor `DrunkIncrease`.
- `save`, `load`, `saveMainFields` and `loadMainFields` were dumped and none names either drunk field; the class's bytes hold the string `drunkReductionValue` once (the field ref) [#2920/C/inference].
- **Inference:** a value a mod sets through `setDrunkReductionValue` lives only on the in-memory `BodyDamage`; a reload (or any reconstruction of the body) starts again from 0.0042 [#2920/C/inference].

### The order against the hook

`IsoGameCharacter.updateInternal @1524–@1555 L9222–L9230`:

```text
 1524  L9222  SystemDisabler.doCharacterStats ifeq 1548
 1537  L9224  getBodyDamage().Update()
 1544  L9225  updateBandages
 1548  L9229  SystemDisabler.doCharacterStats ifeq 1558
 1554  L9230  calculateStats()                <- CalculateStats hook inside (#2723)
```

So within one update the decay (and every other body-tick write) lands **before** the `CalculateStats` hook, and a handler's INTOXICATION write is the later one [#2921/C/C-only].

### The rate in game time (derived)

`GameTime.update @469–@486 L519`: the time of day advances by `1 / minutesPerDay / 60 × getMultiplier() / 2` hours per update, i.e. `getMultiplier ÷ (120 × minutesPerDay)` (#2795).
So the multiplier sums to `120 × minutesPerDay` over one game-hour, and the decay is `0.0042 × 120 × minutesPerDay = 0.504 × minutesPerDay` per game-hour [#2922/C/arith.]:

| day length | decay per game-hour | 100 → 0 |
|---|---|---|
| 60 min (default) | 30.24 | 3.31 game-h |
| 90 min (the fixture) | 45.36 | 2.20 game-h |

Cross-check (the same shape, measured): the THIRST level-4 health term is `healthReductionFromSevereBadMoodles / 10 × getMultiplier()` (`BodyDamage.Update @1337–@1352 L2378`; the constructor's `0.0165` at `@90–@93 L79`), i.e. `0.00165 × 10800 = 17.82` per game-hour on a 90-minute day — measured at 17.820029 (#0519).
The decay itself is **not** measured; Task 5's beer-can session is its measurement.

### What a mod writer must do to own INTOXICATION (the Plan 5 consequence — inference throughout)

1. **Write it from the handler every update.** The decay runs before the hook in the same update [#2921/C/C-only], so a takeover handler that sets INTOXICATION from the mod's BAC on every call wins every update, exactly as the hunger and thirst views win over vanilla's eat and drink writes. The vanilla writers (`JustDrankBooze`, `JustDrankBoozeFluid`) add at the eat and the drink, outside the hook; their add is overwritten at the next handler call. This is the pattern the plan's thirst view already uses.
2. **Or zero the decay.** `setDrunkReductionValue(0)` is a public setter on an exposed class [#2919/C/C-only], so a mod can switch the decay off and own the fall itself; but the value is not saved [#2920/C/inference], so the mod must set it again after every load and every respawn (an `OnCreatePlayer`/`OnGameStart`-time write on the server, and on any body reconstruction). The vanilla adds at the drink still land and would still need cancelling.
3. **Either way**, the vanilla adds must be neutralised or absorbed: option 1 absorbs them by overwrite; option 2 does not. Option 1 is the lower-risk route and needs no save-time bookkeeping. The `SyncPlayerStats` send at the end of `DrinkFluid` carries INTOXICATION [#2925/C/C-only], so a client may briefly see vanilla's add until the next push of the handler's value — a skew Task 5 should measure.
4. The decay is real-time-constant and game-time-variable (it scales with day length, as the severe-moodle health terms do, #0518), so any mod comparison against vanilla's own drunkenness must state the day length.

## 2. The alcohol writers

### `DrinkFluid` — the drink path

`IsoGameCharacter.DrinkFluid(Lzombie/entity/components/fluids/FluidContainer;FZ)Z` (public; the four other overloads funnel into it, #0084):

```text
  129  L5885  fc.removeFluid(fc.getAmount() × f, true) -> consume (local 7)
  142–253     THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE, BOREDOM, UNHAPPINESS += consume.get…   (L5888–L5894)
  254–284     healthFromFoodTimer += |hungerChange| × 13000                                       (L5896–L5897)
  287  L5899  consume.getAlcohol() > 0 ?
  297  L5900    getBodyDamage().JustDrankBoozeFluid(consume.getAlcohol())
  309–346     painReduction, coldReduction                                                       (L5903–L5904)
  349–451     poison ladder (#0066)
  590  L5937  GameServer.server && IsoPlayer ->
  603  L5938    INetworkPacket.send(SyncPlayerStats, [player, mask(INTOXICATION)+mask(THIRST)+mask(HUNGER)+mask(ENDURANCE)+mask(STRESS)+mask(FATIGUE)+mask(BOREDOM)])
```

The alcohol is the removed consume's (`FluidConsume` declares no `getAlcohol`; it inherits it from `SealedFluidProperties`, #2688), so the argument already carries the share drunk and is not re-multiplied by `f` [#2925/C/C-only].

### `JustDrankBoozeFluid(a)`

`BodyDamage.JustDrankBoozeFluid @0–@119 L516–L532`:

```text
  L516  x = 1.0
  L517  x = x × a
  L520  HUNGER > 0.8 ?  L521 x ×= 1.1
  L522  else HUNGER > 0.6 ?  L523 x ×= 1.25
  L526  INTOXICATION += getDrunkIncreaseValue() × x          (400 × x)
  L528  parentChar.SleepingTablet(0.02 × a)
  L529  parentChar.BetaAntiDepress(0.4 × a)
  L530  parentChar.BetaBlockers(0.2 × a)
  L531  parentChar.PainMeds(0.2 × a)
```

The hunger ladder is the reverse of the food path's (1.1 above 0.8, 1.25 between 0.6 and 0.8) [#2923/C/C-only]. Whether that is deliberate is not readable; it is what the bytecode does.

### `JustDrankBooze(food, f)` — the food path (#0055 routes to it)

`BodyDamage.JustDrankBooze @0–@174 L487–L513`: `x = 1`; if `baseHunger ≠ 0`, `f = hungChange × f ÷ baseHunger × 2` (L491–L492); `x = x × f`; × 0.25 when the item's name contains `beer` (lower-cased) or it has `ItemTag.LOW_ALCOHOL` (L497–L498); × 1.25 when HUNGER > 0.8, else × 1.1 when HUNGER > 0.6 (L501–L504); `INTOXICATION += 400 × x` (L507); the same four pill calls on the rescaled `f` (L509–L512) [#2924/C/C-only].

### The scale of a vanilla drink (derived)

`fluids_Alcoholic.txt`: `fluid Beer` (line 3) carries `alcohol = 0.05` (line 23); Brandy 0.4, Champagne 0.12. Through the per-litre chain (#0630, #1891) a litre of beer drunk at HUNGER ≤ 0.6 hands `JustDrankBoozeFluid` 0.05 and adds `400 × 0.05 = 20` INTOXICATION; half a litre 10 [#2926/C/arith.]. **Inference:** that the consume's alcohol is per-litre × litres removed follows the chain the macros are measured on (#1892); the alcohol cell itself is not measured.

## 3. The auto-drink

### The search and the litres

`IsoGameCharacter.autoDrink @0–@233 L11727–L11759` (public; #2769 and #2770 read its gates and the `min(container, 2 × thirst)` drink):

```text
   99  L11743  THIRST > 0.1 ?  else return
  117  L11747  item = getWaterSource(getInventory().getItems())
  129  L11748  item != null && item.hasComponent(FluidContainer) ?
  143  L11750  t2 = THIRST × 2
  156  L11751  litres = min(fc.getAmount(), t2)
  168  L11752  frac = litres / fc.getAmount()
  179  L11753  DrinkFluid(item, frac, false)
  188  L11754  server && IsoPlayer -> L11755 send(SyncItemFields, [player, item])
```

`IsoGameCharacter.getWaterSource(ArrayList) @0–@142 L11762–L11785` walks the list it is given — the main inventory's top-level items, not the contents of bags — in order [#2927/C/C-only]:

```text
  for each item:
    if item.isWaterOnlySource():                       L11767
       ok = !(fc.isCategory(Hazardous) && SandboxOptions.enableTaintedWaterText)   L11769
    else continue
    if !ok continue
    if item has FluidContainer and amount >= 0.12  -> return item     L11777–L11779
    if !(item instanceof InventoryContainer)        -> return item     L11780–L11782
  return null
```

`InventoryItem.isWaterOnlySource @0–@35 L2894` = has a `FluidContainer`, the container `isWaterOnlySource`, and not `isMultiTileMoveable`; `FluidContainer.isWaterOnlySource @0–@61 L879–L889` = not empty and every `FluidInstance`'s fluid `isCategory(FluidCategory.Water)`.
So a tainted container is skipped only while the tainted-water text option is on (with the text off the character drinks it unknowingly), and a nearly-empty bottle (< 0.12 L) first in the list is still returned unless it is a bag — then drunk to its last drop.

### Litres from the THIRST drop (derived)

The `Water` category is carried by exactly three fluids, all in `fluids.txt`: `Water` (category line 10, `ThirstChange = -50.0` line 14), `TaintedWater` (26, 30) and `CarbonatedWater` (47, 51); no fluid in `fluids_Alcoholic.txt` or `fluids_Beverages.txt` carries it (a grep of the three files for a bare `Water,` category line, 2026-10-05).
`getThirstChange` divides by 100 (#0629), so every water-only container is worth 0.5 THIRST per litre, and `min(amount, 2 × thirst)` litres lower THIRST by `min(amount/2, thirst)` — i.e. by exactly half the litres drunk [#2928/C/arith.].
**The handler's bracket therefore converts a THIRST drop Δ to 2Δ litres** with no need to know which container was found. (The conversion holds while THIRST's floor at 0 does not clip — it cannot, since the drink is at most `2 × thirst`.)

### No cooldown — the Task 12 hazard (inference)

The body has no timer, no last-drink field and no per-call cap beyond `2 × thirst` [#2929/C/C-only].
Under the plan's thirst view the handler writes `out.thirst = thirstTarget` (today `NR_Server_Fast.lua:222`) and then calls `h.autoDrink(p)` (`:236`) on every pass. **Inference:** if the drink lowers THIRST but `thirstTarget` does not fall until the slow clock lands the water (up to a game-minute later), the next tick restores THIRST to the target, `autoDrink` sees THIRST > 0.1 again and drinks again — every tick, until the bottle is empty or the slow clock catches up. Task 12's bracket must therefore also suppress re-drinking while a drop is pending (for example: subtract the pending `autoDrop` from the view on the fast clock, or skip the call while `autoDrop > 0`), and Task 4 should measure the repeat directly.

## 4. The world-water route

### The action (Lua, `media/lua/shared/TimedActions/ISTakeWaterAction.lua`)

Queued with no item by `ISWorldObjectContextMenu.lua:2059` (#2690). The no-item arm:

```lua
-- new (lines 193-198)
local thirst = o.character:getStats():get(CharacterStat.THIRST) * 2
local waterNeeded = math.min(thirst, waterAvailable)
o.waterUnit = waterNeeded
o.startUsedAmount = 0.0
o.startThirst = thirst;
o.endUsedAmount = math.min(o.waterUnit, 1.0)

-- updateUse (lines 31-47)
local usedTarget = self.waterUnit * targetDelta;
...  -- no item:
currentUsedAmount = self.startThirst - (self.character:getStats():get(CharacterStat.THIRST) * 2);   -- line 41
local usedSoFar = currentUsedAmount - self.startUsedAmount;
local toUseAmount = math.max(0, usedTarget - usedSoFar);
self:transferFluid(toUseAmount);

-- transferFluid (lines 135-148), no item:
local fluidContainer = self.waterObject:moveFluidToTemporaryContainer(_amount);
self.character:DrinkFluid(fluidContainer, 1);
FluidContainer.DisposeContainer(fluidContainer);
```

`updateUse` is called from `update` when `not isClient()` (lines 25-28) with the net action's progress, from `animEvent` on a server for `takeFluid` (lines 155-161, emulated by `serverStart` at line 152), and from `complete` with a delta of 1 (lines 130-133) [#2930/C/C-only] [#2931/C/C-only].
`IsoObject.moveFluidToTemporaryContainer(F) @0–@27 L2999–L3003`: `amount = clamp(F, 0, getFluidAmount())`; `fc = FluidContainer.CreateContainer()`; `fc.setCapacity(amount)`; `transferFluidTo(fc, amount)`; return `fc` [#2931/C/C-only].

### Which side builds it

`NetTimedAction.parse @0–@233 L149–L177`: on `GameServer.server` and a `Request` state (`@6–@19 L150`) it reads the type and name strings and the argument table, looks up `LuaManager.get(type)` and `LuaManager.getFunctionObject(type + ".new")` (the suffix is the class's string-concatenation recipe `\u0001.new`), calls it through `LuaCaller.protectedCall` with the type table followed by the arguments, and stores the returned table as `action` with `name` and `netAction` rawset on it (`@72–@228 L157–L175`) [#2932/C/C-only].
So on a dedicated server the take-water action's `new` — and its `THIRST` read — runs on the **server**, against the server's THIRST. (That `complete` is invoked on the server is the drink action's measured behaviour, #2825; the take-water action rides the same `NetTimedAction` machinery. **Inference** for this action until Task 4 runs it.)

### The seat a wrapper can read litres at (the Task 12 consequence)

- **The seat is `transferFluid(_amount)`, not `complete`.** The action drinks in increments; `complete` only tops up the remainder with `updateUse(1)`. A server-side wrapper of `ISTakeWaterAction.transferFluid` that, when `self.item == nil`, reads `_amount` (clamped to `self.waterObject:getFluidAmount()`, as the move clamps it) before calling through sees every litre the route drinks [#2931/C/C-only]. A wrapper of `complete` alone would miss all but the last step. (**Inference**: the wrapper must be on the class table in a file the server loads, `shared/` or `server/`, as the drink wrap is.)
- The fluid drunk is the source's: water, or tainted water from a tainted source; the wrapper should read the source's fluid (or the temporary container's primary fluid inside a wrap of `DrinkFluid` is unreachable from Lua — the `DrinkFluid` call is Java), so sampling `self.waterObject` before the call through is the readable route (**inference**).
- **The accounting hazard (inference).** The action measures what it has drunk from THIRST itself (`startThirst − 2 × THIRST`, line 41). Under the plan's thirst view the fast clock rewrites THIRST to `thirstTarget` every tick, and `thirstTarget` falls only when the slow clock lands the water. Between those, `usedSoFar` reads near 0, so each `updateUse` transfers `waterUnit × delta` again rather than the increment: the route would over-drink, draining the source by roughly the sum of the progress fractions times `waterUnit` (bounded by the source and by the action's duration, `waterUnit × 100 + 15` ticks), and the mod would land every litre. The wrapper therefore has to keep the action's accounting honest — for example by wrapping `updateUse` to compute `usedSoFar` from the litres the wrapper has itself counted for this action instance rather than from THIRST. Task 4 should measure a world-water drink with the thirst view on before Task 12 commits to a shape.
- If Task 4 finds the server never runs the transfer for this action, world water is a stated limitation (ruling 9's fallback).

## 5. The thermoregulator getters

`Thermoregulator` is `public final` and in the exposer's class set (#2248); `BodyDamage.getThermoregulator()` is `public` (flags read). The four getters the sweat term needs are all `public` (flags read) and bare reads [#2933/C/C-only]:

| getter | body | returns |
|---|---|---|
| `getFluidsMultiplier()D` | `@0–@4 L327` getfield `fluidsMultiplier` | the hot-side thirst multiplier (#0478), a double |
| `getCoreTemperature()F` | `@0–@7 L392` getfield `core` → `ThermalNode.celcius` | the core node, °C |
| `getExternalAirTemperature()F` | `@0–@4 L424` getfield `externalAirTemperature` | the air the body sees |
| `getBodyFluids()F` | `@0–@12 L1184` `1 − stats.get(THIRST)` | not a store: one minus THIRST |

Also public and bare (not dumped here): `getEnergyMultiplier`, `getMetabolicRate` (read live on the server, #2875), `getCoreCelcius`, `getTemperatureAir`, `getTemperatureAirAndWind`, `getDbg_primTotal`, `getDbg_secTotal`.

- The values are computed by `Thermoregulator.update`, which `BodyDamage.Update` calls at `@211–@222 L2198–L2199` — after the client return (`@21–@62`) and only when the `thermoregulator` field is non-null [#2934/C/C-only]. So the server's copy is the computed one in multiplayer, and a reader must nil-check `getThermoregulator()`. Other callers of `update` were not searched; what a client's copy holds is not read (Plan 1 read the getters client-side; the open range question is #0594).
- **Inference (feedback):** `getBodyFluids` reads THIRST, and the thermoregulator's hot-side heat loss already scales with `1 − thirst` (#2380). Once THIRST is the water pool's view, both read the mod's dehydration — which is the intended coupling, but a sweat term that reads `getFluidsMultiplier` and feeds the pool that feeds THIRST that feeds the thermoregulator is a loop; it is damped (the multiplier is a heat term, not a thirst term), but Task 8/12 should not read `getBodyFluids` as an independent input.
- Task 4 measures whether the getters read live on the server for a connected player and their hot/cold range.

## Desk verdicts (one line each)

1. **Intoxication decay:** `BodyDamage.Update @527–@548 L2263`, `INTOXICATION -= 0.0042 × getMultiplier()` per update, server-only, before the `CalculateStats` hook, no Lua hook can skip it; ≈ 30.24 per game-hour on the 60-minute day (45.36 on 90); the reduction value is publicly settable but not saved [#2918/C/C-only]–[#2922/C/arith.].
2. **The alcohol branch:** `DrinkFluid @287–@306 L5899–L5900` hands the removed consume's alcohol to `JustDrankBoozeFluid`, which adds `400 × a` (× 1.1 above 0.8 hunger, × 1.25 in 0.6–0.8) plus four pill effects; the server's stats sync carries INTOXICATION; a litre of beer is 20 [#2923/C/C-only]–[#2926/C/arith.].
3. **The auto-drink fraction:** the first top-level water-only item (Water, TaintedWater or CarbonatedWater, all 0.5 THIRST/L), `min(amount, 2 × thirst)` litres, so a THIRST drop Δ is exactly 2Δ litres; no cooldown, so a thirst view re-triggers it every tick unless suppressed [#2927/C/C-only]–[#2929/C/C-only].
4. **The world-water seat:** incremental; the server builds and runs the action; the litres are `transferFluid(_amount)` (a temporary container of that capacity, drunk whole), reached from `update`/`animEvent`/`complete` — wrap `transferFluid`, not `complete`; the action's own accounting reads THIRST and will over-drink under a thirst view unless the wrapper fixes it [#2930/C/C-only]–[#2932/C/C-only].
5. **The thermoregulator getters:** public bare reads on an exposed class via the public `getThermoregulator()` (nil-able), computed server-side; `getBodyFluids` is `1 − THIRST`, not a store [#2933/C/C-only] [#2934/C/C-only].
