# 01 — Intake pipeline: code map (Task 4 notes)

**Scope:** how a `Food` item's script values become `Stats` / `Nutrition` deltas.
Read-only code map; no source changed, nothing committed.

**Sources**

| | |
|---|---|
| jar | `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`, B42.20.4 (per `pz-b42/WORKSPACE.md`) |
| disassembler | `C:\Users\Angus\pz-b42\pz.sh` (pzdis; numeric literals resolved inline) |
| Lua | `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua\` |
| scripts | `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\scripts\generated\items\food.txt` |
| prior findings cited | `docs/vanilla/nutrition-core.md`, `docs/testing/spikes.md` §S6 |

**Citation form.** `zombie/characters/IsoGameCharacter.Eat(InventoryItem,float,boolean) @163`
= bytecode offset in that method's dump; `@L5769` = the source-line label pzdis prints
alongside. Lua as `ISEatFoodAction.lua:174`. Ev column: `C` = read from bytecode/Lua
(no measurement).

**Scale note (needed for every number below).** `Item.InstanceItem` divides the script's
`HungerChange` / `ThirstChange` / `EnduranceChange` by **100** before storing them
(`zombie/scripting/objects/Item.InstanceItem(String,boolean) @546–@595`), because
`CharacterStat.HUNGER` and `THIRST` are registered `min 0, max 1`
(`zombie/characters/CharacterStat.<clinit> @91–@99`, `@231–@239`).
`Calories` / `Carbohydrates` / `Lipids` / `Proteins` are **not** rescaled — the raw
script number goes to the item field and from there straight into `Nutrition`
(`Item.InstanceItem @745–@781`). So `Apple` (`food.txt:8658`) carries
`hungChange = -0.16`, `thirstChange = -0.07`, `calories = 95.0`, `carbohydrates = 25.13`.
`baseHunger` is initialised **equal to** `hungChange` at instantiation
(`Item.InstanceItem @572–@582`); thereafter `hungChange` shrinks as the item is
part-eaten and `baseHunger` stays at the full-portion value.

---

## Q1 — What `IsoGameCharacter.Eat(item, fraction, useUtensil)` does

Method: `zombie/characters/IsoGameCharacter.Eat(InventoryItem,float,boolean)Z`, 968 bytes.
The two other overloads are trampolines: `Eat(item,f)` → `Eat(item,f,false)` (`@3 L5721`),
`Eat(item)` → `Eat(item,1.0f)` (`@2 L5848`).

Order of operations, each step with the getter → setter it drives:

| # | Step | Getter | Setter / target | Guard | Cite |
|---|---|---|---|---|---|
| 0 | type check | — | return `false` | `item instanceof Food` else bail | `Eat @1 L5741` |
| 1 | clamp fraction | — | `f = PZMath.clamp(f, 0, 1)`; save raw copy as `f0` | none | `Eat @18 L5747`, `@25 L5749` |
| 2 | rescale fraction to remaining portion | `getBaseHunger`, `getHungChange` | `f = clamp01(baseHunger*f / hungChange)` | both ≠ 0 | `Eat @28–@78 L5753–L5757` |
| 3 | hunger crumb rule | `getHungChange` | `f = 1` | `hungChange < 0 && hungChange*(1-f) > -0.01` | `Eat @79–@106 L5760–L5761` |
| 4 | thirst crumb rule | `getHungChange`, `getThirstChange` | `f = 1` | `hungChange == 0 && thirstChange < 0 && thirstChange*(1-f) > -0.01` | `Eat @107–@144 L5764–L5765` |
| 5 | **THIRST** | `getThirstChange` | `stats.add(THIRST, v*f)` | none | `Eat @145 L5768` |
| 6 | **HUNGER** | `getHungerChange` | `stats.add(HUNGER, v*f)` | none | `Eat @163 L5769` |
| 7 | ENDURANCE | `getEnduranceChange` | `stats.add(ENDURANCE, v*f)` | none | `Eat @181 L5770` |
| 8 | STRESS | `getStressChange` | `stats.add(STRESS, v*f)` | none | `Eat @199 L5771` |
| 9 | FATIGUE | `getFatigueChange` | `stats.add(FATIGUE, v*f)` | none | `Eat @217 L5772` |
| 10 | **Nutrition, normal** | `getCalories/Carbohydrates/Proteins/Lipids` | `nutrition.setX(getX() + v*f)` | `player != null && !isBurnt()` | `Eat @246–@338 L5776–L5782` |
| 11 | **Nutrition, burnt** | same four | `nutrition.setX(getX() + v*f/5.0)` | `player != null && isBurnt()` | `Eat @341–@446 L5783–L5787` |
| 12 | pain relief | `getPainReduction` | `bodyDamage.setPainReduction(cur + v*f)` | none | `Eat @449 L5789` |
| 13 | cold relief | `getFluReduction` (int→float) | `bodyDamage.setColdReduction(cur + v*f)` | none | `Eat @471 L5790` |
| 14 | food-sickness cure | `getFoodSicknessChange` | `stats.remove(FOOD_SICKNESS, a)` and `stats.remove(POISON, a)` where `a = |change|*f` | `FOOD_SICKNESS above minimum && change < 0 && effectiveEdibleBuffTimer <= 0` | `Eat @494–@562 L5791–L5794` |
| 15 | set buff cooldown | — | `effectiveEdibleBuffTimer = Rand.Next(lo,hi)` | Iron Gut 80–150 · Weak Stomach 200–280 · else 120–230 | `Eat @563–@633 L5795–L5800` |
| 16 | **sickness / poison / mood** | — | `bodyDamage.JustAteFood(food, f, useUtensil)` | none — **the only use of `useUtensil`** | `Eat @634 L5803` |
| 17 | server broadcast | — | `SyncPlayerStats` (THIRST+HUNGER+ENDURANCE+STRESS+FATIGUE+PAIN bits), `GameServer.sendSyncPlayerFields(player, 8)`, `EatFood` packet | `GameServer.server && this instanceof IsoPlayer` | `Eat @645–@759 L5805–L5808` |
| 18 | `OnEat` Lua hook | `getOnEat` | `LuaCaller.pcallvoid(fn, item, character, (double)f)` | `getOnEat() != null && LuaManager.getFunctionObject(name) != null` | `Eat @762–@802 L5811–L5814` |
| 19a | consume whole item | — | `setHungChange(0)`, `UseAndSync()`, return `true` | `f == 1.0f` | `Eat @803–@820 L5819–L5821` |
| 19b | consume part | — | `multiplyFoodValues(1 - f)` on the item | `f != 1.0f` | `Eat @823–@844 L5823–L5825` |
| 19c | post-partial crumb sweep | `getHungChange`,`getThirstChange` (pre-scale copies) | `setHungChange(0)`, `UseAndSync()`, return `true` | `oldHung == 0 && oldThirst < 0 && newThirstChange > -0.01` | `Eat @845–@883 L5826–L5829` |
| 20 | item weight bookkeeping | `getWeight`, `Item.getActualWeight(replaceOnUse)` | `setWeight(w - f0*(w - base) )`… see pseudo-code | `isCustomWeight()` | `Eat @884–@960 L5832–L5839` |
| 21 | sync | — | `syncItemFields()`, return `true` | none | `Eat @961–@967 L5841–L5843` |

**Clamps.**
- `Stats.add` → `Stats.set` → `CharacterStat.clamp` → `PZMath.clamp(v, min, max)`
  (`zombie/characters/Stats.set(CharacterStat,float) @6`,
  `zombie/characters/CharacterStat.clamp(float) @0`). HUNGER and THIRST are `[0, 1]`.
  **Overshoot is silently discarded** — eating a 900-kcal meal at hunger 0.05 loses the
  rest of the hunger relief but keeps *all* of the calories.
- `Nutrition.setCalories` clamps to **`[-2200, 3700]`**
  (`zombie/characters/BodyDamage/Nutrition.setCalories(float) @1`, `@12`).
- `setCarbohydrates` / `setProteins` / `setLipids` each clamp to **`[-500, 1000]`**
  (`Nutrition.setCarbohydrates @1/@12`, `setProteins @1/@12`, `setLipids @1/@12`).
- `Food.setCalories` / `setCarbohydrates` / `setHungChange` / `setThirstChange` on the
  **item** are bare field writes, no clamp (`Food.setCalories @0 L2143`, etc.).

**Nutrition is player-only.** `Type.tryCastTo(this, IsoPlayer.class)` — an `IsoAnimal` or
NPC gets stats, pain, cold, sickness, but no `Nutrition` write (`Eat @235–@251 L5774–L5776`).

**`useUtensil` never touches hunger, thirst or nutrition.** Its only consumer is
`BodyDamage.JustAteFood(Food,float,boolean)`, where it scales BOREDOM and UNHAPPINESS
by 1.25 (if the change is negative, i.e. beneficial) or 0.75 (if positive)
(`JustAteFood @322–@379 L5624–L5633` for boredom, `@383–@440 L5636–L5644` for unhappiness).
Utensils also cut eating **time** — see Q8.

---

## Q2 — the hunger/thirst getters and how item state modifies them

### `getBaseHunger()` — `Food.getBaseHunger()F @0 L1891`
Bare read of `Food.baseHunger`. No state modifiers. Set to `HungerChange/100` at
instantiation and never re-scaled by `multiplyFoodValues`; it is the *full-portion*
hunger value and exists so partial eating can be expressed as "x% of the whole item"
rather than "x% of what's left".

### `getHungChange()` — `Food.getHungChange()F @0 L1816`
Bare read of `Food.hungChange`: the **raw remaining** hunger value. No cooked/rotten
modifiers. `getBaseHungChange()` is just an alias (`@0 L1812`).
This is the field `multiplyFoodValues` shrinks and that `Eat` zeroes when the item is
finished.

### `getHungerChange()` — `Food.getHungerChange()F` @L1682–L1708 — **the modified one**

```java
float h = this.hungChange;
if (h != 0) {
    if (isCooked())      return h * 1.3f;                          // @11–@23  L1686-L1687
    float sign = (h < 0) ? -1f : 1f;                               // @24–@36  L1692
    float a    = Math.abs(h);                                      // @37      L1694
    if (burnt)                       return max(a / 3.0f,  0.01f) * sign;   // @42–@62  L1697-L1698
    if (age >= offAge && age < offAgeMax)
                                     return max(a / 1.3f,  0.01f) * sign;   // @63–@102 L1700-L1701
    if (age >= offAgeMax)            return max(a / 2.2f,  0.01f) * sign;   // @103–@129 L1703-L1704
}
return h;
```

Note the order: **cooked wins over burnt and over rot**. An item that is both
`cooked` and past `offAgeMax` returns `h*1.3`, not `h/2.2`. (`isCooked()` is
`InventoryItem.isCooked()F @0 L2585`, a bare read of `InventoryItem.cooked`;
`Food` does not override it.)

### `getThirstChange()` — `Food.getThirstChange()F` @L1866–L1875

```java
float t = this.thirstChange;
if (burnt)     return t / 5.0f;   // @5–@17  L1868-L1869
if (isCooked())return t / 2.0f;   // @18–@28 L1871-L1872
return t;
```

Burnt wins over cooked here (opposite precedence to hunger). **Rot does not affect
thirst at all.** `getThirstChangeUnmodified()` is the bare field
(`Food.getThirstChangeUnmodified()F @0 L1746`).

### The four nutrition getters — **completely unmodified**

`Food.getCalories/getCarbohydrates/getLipids/getProteins` are each a single
`getfield` (`@0 L2139`, `L2115`, `L2123`, `L2131`). **Nothing** — cooking, burning,
rotting, freezing, poison — scales the stored nutrition values. The only state that
touches nutrition intake is the `isBurnt()` **/5 divisor applied at `Eat` time**
(step 11 above), and the `multiplyFoodValues(1-f)` shrink of the leftover.

Consequence worth flagging for the mod: **rotten food gives full calories and full
macros.** Only its hunger relief (÷2.2), stress (÷2), endurance (÷2), boredom (+20)
and unhappiness (+20) degrade — plus the sickness roll.

> **Correction (slice 01, task 7 fix round 1): the "endurance (÷2)" in the prose above is
> wrong; the table below is right.** `Food.getEnduranceChange` (`@0–@67 L1605–L1615`) has
> branches for burnt (`/3`), stale (`/2`) and cooked (`×2`) only — rot has no branch, and a
> rotten item is past the stale window (`age ≥ offAgeMax`), so it falls through to the raw
> value. The ÷2 belongs to *stale*, not rotten. `docs/vanilla/eating-pipeline.md` states the
> table's version.

### Other item state, for completeness

| Getter | burnt | stale (`offAge ≤ age < offAgeMax`) | rotten (`age ≥ offAgeMax`) | cooked | frozen |
|---|---|---|---|---|---|
| `getEnduranceChange` (`@0 L1605`) | `/3` | `/2` | — (falls through to cooked/raw) | `×2` | — |
| `getStressChange` (`@0 L1713`) | `/4` | `/1.3` | `/2` | `×1.3` | — |
| `getFoodSicknessChange` (`@0 L2078`) | `/3` | `/1.3` | `/2.2` | `×1.3` | — |
| `getBoredomChange` (`@0 L1657`) | `+20` | `+10` | `+20` | — | `+30` unless `type=="Icecream"` or tag `GOOD_FROZEN` |
| `getUnhappyChange` (`@0 L1625`) | `+20` | `+10` | `+20` | `+2` if `isBadCold && isCookable && heat<1.3`; `-2` if `isGoodHot && isCookable && heat>1.3` | `+30`, same exception |
| `getFatigueChange` | — | — | — | — | — (bare `InventoryItem.fatigueChange`, `@0 L3004`) |

All of these short-circuit to the raw field when `isFertilized()`
(`getBoredomChange @5`, `getUnhappyChange @5`, `getStressChange @0`).
`isRotten()` itself also returns `false` for fertilized eggs
(`Food.isRotten()Z @0 L1832`).

### Poison

`Food.isPoison()`/`getPoisonPower()` are bare fields (`@0 L1909`, `@0 L1941`) and are
**not** read by `Eat`. Poison is applied inside `BodyDamage.JustAteFood(Food,float,boolean)`:

- `poisonPower > 0` → `p = poisonPower * f`; Iron Gut `/2` unless `getType()=="Bleach"`;
  Weak Stomach `×2`; `stats.add(POISON, p)` and `stats.add(PAIN, poisonPower*f/6)`
  (`JustAteFood @0–@101 L587–L598`).
- `isTainted()` → `stats.add(POISON, 20.0*f)`, `stats.add(PAIN, 10.0*f/6)`
  (`@177–@223 L607–L610`).
- **rot sickness roll** (`@677–@953 L703–L743`): only when `age ≥ offAgeMax`;
  `d = clamp(age-offAgeMax, 1, 5)`; `chance% = d/(offAgeMax-offAge)*100` (100 if
  `offAgeMax ≤ offAge`); Iron Gut `/2`, Weak Stomach `×2`; skipped entirely if already
  infected. Hit → `POISON += 5*|hungChange*10|*f`; miss → `POISON += 2*|hungChange*10|*f`
  (the *miss* branch still adds poison, just less).
- **dangerous uncooked** (`@555–@676 L669–L696`): `!isCooked() && isbDangerousUncooked()`
  → `healthFromFoodTimer = 0`, chance `75` (`5` if tag `EGG`); Iron Gut `/2` (and `0` for
  eggs), Weak Stomach `×2`; on a hit, and not infected, and not burnt →
  `POISON += 15.0*f`.

`multiplyFoodValues` also scales `poisonPower` by `(1-f)` (`@144–@153 L2302`), so half an
apple carries half the poison.

### `RemoveNegativeEffectOnCooked`

Read in exactly **one** place: `Food.update()` @579 `L451`, inside the block that fires
when the item crosses into `cooked` (`setCooked(true)` at `Food.update @413 L423`).
It is a **one-shot permanent mutation of the item's stored fields**, not an `Eat`-time
modifier:

```java
if (isRemoveNegativeEffectOnCooked()) {
    if (thirstChange  > 0) setThirstChange(0);   // @585–@598  L452-L453
    if (unhappyChange > 0) setUnhappyChange(0);  // @599–@612  L455-L456
    if (boredomChange > 0) setBoredomChange(0);  // @613–@626  L458-L459
}
```

Only the *positive* (bad) values are zeroed; calories and macros are untouched.
A sibling flag `Item.removeUnhappinessWhenCooked` zeroes `unhappyChange` at the same
transition (`Food.update @418–@432 L424-L425`).
Verified by a whole-jar scan for `isRemoveNegativeEffectOnCooked` — the only other hits
are the script parser (`Item.DoParam @7226`), the instantiator
(`Item.InstanceItem @687`) and the generator.

### Frozen

Frozen affects **only** boredom/unhappiness (`+30` each, unless Icecream / `GOOD_FROZEN`).
It does not gate `Eat`, does not touch hunger, thirst, calories or macros. The only
frozen gate in the Lua UI is on evolved-recipe use, not eating
(`ISInventoryPaneContextMenu.lua:2036`).

---

## Q3 — how the fraction scales things, and what happens to the leftover

**On the eater:** every stat and every nutrient is multiplied by the *same* scalar `f`
— see the Q1 table, steps 5–14. Burnt food additionally divides the four nutrients
by 5 (step 11). There is no separate per-nutrient fraction.

**But `f` is not the menu fraction.** `Eat` first rewrites it (step 2):

```
f_arg = clamp01(f_arg)
if baseHunger != 0 && hungChange != 0:
    f = clamp01( baseHunger * f_arg / hungChange )
```

`baseHunger` is the *whole item's* hunger value and `hungChange` is what's *left*. So
"eat a quarter" on an already-half-eaten apple asks for a quarter of the **original**
apple, which is half of the remainder → `f = 0.5`. The identical arithmetic is
duplicated in Lua for the tooltip (`ISInventoryPaneContextMenu.lua:2062–2070`) and for
the utensil-scrape sound (`ISEatFoodAction.lua:279–284`).

**Crumb rules.** Steps 3 and 4 promote `f` to `1.0` when the leftover would be smaller
than `0.01` hunger units (= 1 script point). Step 19c re-checks the same thing for
drink-type food after the multiply. Effect: you can never leave a 0.5-point sliver.

**Yes — the remainder's nutrition is reduced proportionally.**
`Eat @837–@844 L5825` calls `Food.multiplyFoodValues(1.0f - f)`, which multiplies
**fifteen** stored fields by `(1-f)`:

`boredomChange, unhappyChange, hungChange, fluReduction (int), thirstChange,
painReduction, foodSicknessChange (int), endChange, stressChange, fatigueChange,
calories, carbohydrates, proteins, lipids, poisonPower (int)`
(`Food.multiplyFoodValues(float)V @0–@153 L2288–L2302`).

Notes on that method:
- it feeds itself the **unmodified** getters where they exist
  (`getBoredomChangeUnmodified @2`, `getUnhappyChangeUnmodified @12`,
  `getThirstChangeUnmodified @44`, `getEnduranceChangeUnmodified @76`,
  `getStressChangeUnmodified @86`) so cooked/rotten multipliers are not baked in;
- but **`hungChange` uses `getHungChange()`** (`@22`) — also the raw field — consistent;
- `getCalories()`/`getCarbohydrates()`/`getProteins()`/`getLipids()` are raw fields
  anyway, so calories scale exactly linearly: eat half an Apple, the half left has
  `calories = 47.5`, `carbohydrates ≈ 12.57`;
- the three `int` fields round toward zero after the multiply (`f2i`), so
  `fluReduction`, `foodSicknessChange` and `poisonPower` erode faster than linearly on
  small items.

`baseHunger` is deliberately **not** in that list — it stays at the full-portion value,
which is what makes step 2's rescale meaningful.

**Item weight** (only when `isCustomWeight()`), `Eat @884–@960 L5832–L5839`:

```
base = 0
if (isCustomWeight()) {
    Item repl = replaceOnUseFullType == null ? null : ScriptManager.instance.getItem(replaceOnUseFullType);
    if (repl != null) base = repl.getActualWeight();          // e.g. the empty can
    setWeight( (w - base) - f0 * (w - base) + base );          // f0 = the *pre*-rescale clamped fraction
}
```

Note it uses `f0` (the argument after `clamp(0,1)` but **before** the baseHunger
rescale, stored at `Eat @25 L5749`), not the `f` that scaled the nutrition. On a
part-eaten item those two differ — flagged in "Open / uncertain".

---

## Q4 — drinks

There are two separate paths and they do **not** share code.

**(a) Food-type drinks (`ThirstChange` on a `Food` item)** go through `Eat` exactly like
solid food. They are only distinguished by `CustomMenuOption = Drink`, which changes the
animation (`ISEatFoodAction.lua:118–121`) and the eating-time formula
(`ISEatFoodAction.lua:232–241`). Their thirst is step 5 of `Eat`; their calories/macros
are step 10 of `Eat`. So **yes, for food-type drinks thirst and nutrition are coupled**:
a `Food` with `ThirstChange = -30, Calories = 140` (a soda) delivers both, both scaled
by the same `f`.

**(b) `DrinkFluid` — the B42 fluid-container path.** Four overloads, all funnelling into
`DrinkFluid(FluidContainer,float,boolean)`:

- `DrinkFluid(InventoryItem)` → `(item, 1.0f)` (`@2 L5945`)
- `DrinkFluid(InventoryItem,float)` → `(item, f, false)` (`@3 L5853`)
- `DrinkFluid(InventoryItem,float,boolean)` → requires `ComponentType.FluidContainer`,
  else returns `false`; delegates to the container overload (`@0–@26 L5858–L5863`)
- `DrinkFluid(FluidContainer,float)` → `(c, f, false)` (`@3 L5868`)

The real body, `DrinkFluid(FluidContainer,float,boolean)Z` @L5873–L5940:

1. **Nutrition first, before anything is consumed** — `player != null` →
   `nutrition.setCalories(getCalories() + props.getCalories()*f)` and the same for
   carbohydrates, proteins, lipids, from
   `FluidContainer.getProperties()` → `SealedFluidProperties`
   (`@11–@100 L5876–L5881`). **No burnt divisor, no other modifier.**
   → **thirst and nutrition are coupled here too.**
2. `FluidConsume fc = container.removeFluid(getAmount() * f, true)` (`@129–@140 L5885`).
3. All the stat deltas come from `fc` and are **not** multiplied by `f` again — the
   fraction was already applied to the *amount removed*:
   `THIRST += fc.getThirstChange()` (`@142 L5888`), then HUNGER, ENDURANCE, STRESS,
   FATIGUE, BOREDOM, UNHAPPINESS (`@158–@253 L5889–L5894`) — note BOREDOM and
   UNHAPPINESS are both fed `fc.getUnhappyChange()`.
4. `healthFromFoodTimer += (int)(|fc.getHungerChange()| * 13000.0)` (`@254–@284 L5896–L5897`).
5. `fc.getAlcohol() > 0` → `BodyDamage.JustDrankBoozeFluid` (`@287 L5899`).
6. painReduction / coldReduction `+=` (no `f`) (`@309–@346 L5903–L5904`).
7. poison `p = fc.getPoison()`; `isTainted()` → `p *= 0.75`; Iron Gut → `p = 0` if
   tainted else `p /= 2` unless the primary fluid is `FluidType.Bleach`; Weak Stomach →
   `p *= 1.2` if tainted else `p *= 2`; `stats.add(POISON, p)` (`@349–@451 L5906–L5924`).
8. food-sickness cure block, same shape as `Eat` but the sign test is
   `foodSicknessChange > 0` here (`@452–@589 L5926–L5934`).
9. `GameServer.server && this instanceof IsoPlayer` → `SyncPlayerStats` with
   INTOXICATION+THIRST+HUNGER+ENDURANCE+STRESS+FATIGUE+BOREDOM bits (`@590–@674 L5937–L5938`).

**Differences from `Eat` worth recording:**
- no `PZMath.clamp` on the fraction, no `baseHunger` rescale, no crumb rules;
- no `OnEat` hook, no `JustAteFood`, no `EatFood` packet;
- the `boolean` third argument is **never read** in the method body — no utensil effect
  on drinking;
- nutrition is applied even for burnt/whatever — the concept doesn't exist for fluids.

The Lua driver is `ISDrinkFluidAction.lua`; it calls `DrinkFluid` **incrementally**
during the action (`updateEat`, lines 107–118) rather than once at the end:
`update()` calls it when `not isClient()` (line 26–29) and `animEvent` calls it when
`isServer()` (lines 40–46), with `serverStart` seeding an emulated anim event (line 37).
`complete()` calls `updateEat(1)` (line 103). Each call consumes the *difference*
between the target ratio and what's already gone (lines 109–113), so it is idempotent.

---

## Q5 — what the sandbox `Nutrition` option switches off

**Option definition:** `SandboxOptions.<init> @1080–@1089 L132` —
`this.nutrition = newBooleanOption("Nutrition", false)`. The Java-side default is
`false`, but every shipped preset sets it true (`media/lua/shared/Sandbox/Apocalypse.lua:64`,
`Extinction.lua:64`, `Outbreak.lua:64`, `Rising.lua:64`, `SixMonthsLater.lua:39`).

**Whole-jar scan for reads of `SandboxOptions.nutrition` returns exactly two sites:**
the constructor that creates it, and `Nutrition.update()` @3. Nothing else in the jar
reads it.

`zombie/characters/BodyDamage/Nutrition.update()V`:

```java
if (!SandboxOptions.instance.nutrition.getValue()) return;      // @0–@12   L65-L66
if (parent == null || parent.isDead())            return;       // @13–@30  L68-L69
if (parent.isGodMod())                            return;       // @31–@41  L71-L72
if (!GameClient.client) {                                       // @42      L75
    setCarbohydrates(getCarbohydrates() - 0.0035f   * gameWorldSecondsSinceLastUpdate);  // @48  L76
    setLipids       (getLipids()        - 0.00113f  * ...);                              // @66  L77
    setProteins     (getProteins()      - 0.00086f  * ...);                              // @84  L78
    updateCalories();                                                                    // @102 L79
}
updateWeight();                                                 // @106     L81
```

**Answer: it switches off both — but not the stores.**

- The passive macro drain, `updateCalories()` (the calorie burn) **and**
  `updateWeight()` are all past the early return, so all three stop.
- The **stores keep filling**: `IsoGameCharacter.Eat` and `DrinkFluid` write
  `Nutrition.setCalories/…` with **no sandbox guard anywhere in either method** — I
  scanned both dumps and the jar-wide reference list; the only `SandboxOptions` read on
  the whole intake path is the one above.
- Consequently with `Nutrition = false`: eating still accumulates calories and macros
  (clamped at 3700 / 1000), nothing ever burns them off, and weight is frozen at
  whatever it was. Save/load and the MP packets still carry the values
  (`Nutrition.save/load @0 L209/L217`).

**Two further gates on the same call**, worth listing because they are *not* the
sandbox option:
- `IsoPlayer.updateInternal2() @392–@402 L2306-L2307`:
  `if (SystemDisabler.doCharacterStats) nutrition.update();` — this is the **only**
  caller of `Nutrition.update()` in the jar.
- the `!GameClient.client` branch above: on a multiplayer **client** the macro drain and
  calorie burn never run locally. `updateWeight()` does still run client-side.
  (This corrects the note in `docs/vanilla/nutrition-core.md` §MP behavior, which has it
  the other way round.)

`updateWeight()` itself has no client/server guard (`Nutrition.updateWeight()V @0 L138`
onward) and matches the model already recorded in `docs/vanilla/nutrition-core.md`
(gain threshold `1000 + (w-80)*40`, trait bases 700/1800, rate `1.3e-5 × min(1, cal/4000)`,
×3 above 700 carbs-or-lipids, ×2 above 400, loss `8.5e-6 × min(1, |cal|/2500)`) — re-read
and confirmed unchanged on this jar.

---

## Q6 — `OnEat`, `EatType`, `EatTime`

### `OnEat` (`Food.getOnEat()Ljava/lang/String; @0`)

Fired at `Eat @762–@802 L5811–L5814`, i.e. **after** every stat, nutrition, pain, cold,
sickness and `JustAteFood` write, and **before** the item is consumed / scaled down:

```java
if (food.getOnEat() != null) {
    Object fn = LuaManager.getFunctionObject(food.getOnEat());
    if (fn != null)
        LuaManager.caller.pcallvoid(LuaManager.thread, fn, item, this, BoxedStaticValues.toDouble(f));
}
```

Signature seen by Lua: `fn(item, character, fraction)` where `fraction` is the
**rescaled** `f`, not the menu percentage. Return value ignored (`pcallvoid`).
Because it runs before step 19, a hook can still read/modify `hungChange`,
`calories` etc. and have `multiplyFoodValues` operate on the modified values.
It does **not** change the pipeline itself — nothing downstream reads a result.

`EatOnClient(InventoryItem,float)Z` is the hook-only twin: type-check, then the identical
`OnEat` call, then `return true` — **no stats, no nutrition, nothing else**
(`IsoGameCharacter.EatOnClient @0–@57 L5725–L5736`). It exists so the packet receiver can
run mod hooks without double-applying effects.

### `EatType` (`InventoryItem.getEatType()Ljava/lang/String; @0 L3828` → `Item.eatType`)

**No Java runtime consumer.** A jar-wide scan for `getEatType` finds only the script
generators. Everything is Lua and it is **purely presentational plus one timing rule**:

- picks the animation variable `FoodType` and whether a fork/spoon is shown as a second
  hand item (`ISEatFoodAction.lua:73–110`);
- `"Pot"`/`"PotForged"` overrides the hand models (`:112–114`);
- gates the canned-food scrape sound (`:42–48`);
- gates which types will auto-pick up a utensil at all — `Can`, `Candrink`, `2hand`,
  `Plate`, `2handbowl` (`ISEatFoodAction.lua:264` in `getSecondItem`), which is what
  sets `useUtensil` (`:313–315`) and therefore feeds the boredom/unhappiness multiplier
  and the eating-time reduction;
- `"popcan"` (lower-case) forces `maxTime = 160` (`:250–252`).

It does **not** touch hunger, thirst or nutrition.

### `EatTime` / `Eattime` (`InventoryItem.getEatTime()I @0 L4933` → `Item.getEatTime()`)

Also has **no Java consumer**. Its single use is `ISEatFoodAction.lua:247`:
`if self.item:getEatTime() and self.item:getEatTime() > 0 then maxTime = self.item:getEatTime() end`
— a hard override of the computed duration, applied after everything else except the
`popcan` rule. Duration only; no effect on what is absorbed.
(The script-parser spelling is `Eattime`, per `generation/builders/ItemBuilder`.)

---

## Q8 — eating time, and which side calls `Eat`

### The eating-time formula, `ISEatFoodAction.lua:203–254`

```lua
if character:isTimedActionInstant() then return 1 end                       -- :204-206

-- DEAD CODE: computed, then unconditionally overwritten at :243
local maxTime = math.abs(item:getBaseHunger() * 150 * percentage) * 8       -- :208
if maxTime > math.abs(item:getHungerChange() * 150 * 8) then                -- :210-212
    maxTime = math.abs(item:getHungerChange() * 150 * 8)
end

hungerConsumed = math.abs(item:getBaseHunger() * percentage * 100)          -- :214
eatingLoop = 1
if hungerConsumed >= 30 then eatingLoop = 2 end                             -- :216-218
if hungerConsumed >= 80 then eatingLoop = 3 end                             -- :219-221
if useUtensil and eatingLoop >= 2 then eatingLoop = eatingLoop - 1 end      -- :224-229

timerForOne = 232                                                           -- :231
if item:getCustomMenuOption() == getText("ContextMenu_Drink") then          -- :232
    hungerConsumed = math.abs(item:getThirstChange() * percentage * 100)    -- :233
    timerForOne = 171                                                       -- :234
    if hungerConsumed >= 3 then eatingLoop = 2 end                          -- :235-237
    if hungerConsumed >= 6 then eatingLoop = 3 end                          -- :238-240
end

maxTime = timerForOne * eatingLoop                                          -- :243
if hungerConsumed == 0 then maxTime = 460 end                               -- :246
if item:getEatTime() and item:getEatTime() > 0 then maxTime = item:getEatTime() end  -- :247
if item:getEatType() == "popcan" then maxTime = 160 end                     -- :250-252
```

So the real result is one of **232 / 464 / 696** ticks for food, **171 / 342 / 513** for
drink, **460** for zero-hunger items (cigarettes), or an outright `EatTime` /
`popcan`-160 override. Lines 208–212 are computed and discarded — worth knowing before
anyone "fixes" them.

Caveat: the drink branch at `:232` *reassigns* `eatingLoop` from the thirst thresholds,
which **undoes** the utensil reduction applied at `:224–229` for drink-type items.

Result is then passed through `ISBaseTimedAction:adjustMaxTime`
(`ISBaseTimedAction.lua:99–…`, called from `:create`): `×(1 + UNHAPPY moodle/4)` and
`×(1 + DRUNK moodle/4)`. Hand-wound pain is skipped because `ignoreHandsWounds = true`
(`ISEatFoodAction.lua:325`).

Menu fractions are 1 / 0.5 / 0.25 (`ISInventoryPaneContextMenu.lua:508`, `:513`, `:516`),
with Half offered only when `|hungerChange*100| ≥ 2` and `≥ baseHunger/2`, Quarter when
`≥ 4` and `≥ baseHunger/4` (`:510–:516`). Whole flow:
`onEatItems` (`:3782`) → `eatItem` (`:3584`) → `ISTimedActionQueue.add(ISEatFoodAction:new(...))` (`:3639`).

### The `isClient()` / `isServer()` branches in `ISEatFoodAction.lua`

| Line | Branch | What it does |
|---|---|---|
| `:24` | `isClient() and self.item` | `isValid` uses `containsID(id)` on a client (item identity survives a re-send), plain `contains(item)` otherwise; on a client a missing item calls `forceComplete()` rather than failing |
| `:52` | `isClient() and self.item` | `start` re-resolves `self.item` by id from the local inventory |
| `:136` | `not isClient() and not isServer()` | **singleplayer only** — `stop()` calls `self:serverStop()` itself, so a cancelled action still applies partial eating in SP |
| `:174` | *(no guard)* | `complete()` → `self.character:Eat(self.item, self.percentage, self.useUtensil)` |
| `:199` | *(no guard)* | `eat()` → `self.character:Eat(self.item, percentage, self.useUtensil)` after `percentage = self.percentage * (progress > 0.95 and 1.0 or progress)` (`:195–198`) |
| `:305` | `not isServer()` | `new()` only probes for an open flame on non-server |

Line `:151` is where the partial value comes from:
`self:eat(self.item, self.netAction and self.netAction:getProgress() or self:getJobDelta())`.
`netAction` is injected into the Lua table by `NetTimedAction.parse @225` — it exists
**only on the server**, so in SP the fallback `getJobDelta()` is used.

### Who actually calls `Eat` — the decisive chain

`ISEatFoodAction` has **no** `isClient()/isServer()` guard on `complete()`. The gating is
one level down, in Java:

```
zombie/characters/CharacterTimedActions/LuaTimedActionNew.complete()V
   @31  L162   getstatic GameClient.client ; ifne 62      <-- on an MP CLIENT, skip
   @37  L163   ... rawget 'complete' ; LuaCaller.pcall
```

So **an MP client never runs `ISEatFoodAction:complete()`**, and therefore never calls
`Eat`. `ISEatFoodAction:perform()` has its `Eat` line commented out
(`ISEatFoodAction.lua:168`), so no client-side application there either.

The client instead mirrors the action to the server at start:

```
LuaTimedActionNew.start()  @60 L127  if (GameClient.client && !useCustomRemoteTimedActionSync) {
                            @73 L128     setWaitForFinished(true);
                            @78 L129     transactionId = ActionManager.getInstance().createNetTimedAction(player, table);
                                      }
ActionManager.createNetTimedAction  @0-@22 L236-L238  -> NetTimedActionPacket -> server
```

and the server drives it:

```
ActionManager.update()      @0  L66   getstatic GameServer.server ; ifeq <end>   <-- SERVER ONLY
                            @72 L70   action.perform()
NetTimedAction.perform()    @0-@27 L140  rawget 'complete' ; protectedCallBoolean
                                       -> ISEatFoodAction:complete()  -> character:Eat(...)
NetTimedAction.stop()       @0-@53 L114  rawget 'serverStop'
                                       -> ISEatFoodAction:serverStop() -> partial eat
```

Cancel path: client `LuaTimedActionNew.stop() @70 L143` → `ActionManager.remove(id, true)`
→ `@14–@52 L179–L184` sends `GeneralActionPacket.setReject` → server
`GeneralActionPacket.processServer @29 L41` → `ActionManager.stop` → `Action.stop()`
(`ActionManager.remove @239 L206`) → `NetTimedAction.stop()` → Lua `serverStop`.

**Therefore, in MP `IsoGameCharacter.Eat` runs on the server, not on the client** —
both for a completed eat and for a cancelled/partial one. In singleplayer it runs
locally (`GameClient.client` false, so `LuaTimedActionNew.complete` calls the Lua).

### `EatFoodPacket` and `GameClient.eatFood`

`EatFoodPacket` (`zombie/network/packets/actions/EatFoodPacket`):

- `set(IsoPlayer,Food,float)` stores player id, `percentage`, and the `Food` (`@0–@18 L46–L48`).
- `write(ByteBufferWriter)` writes the player id, the float, **`player.getNutrition().save(bb)`**,
  and `food.saveWithSize(bb, false)` (`@0–@45 L69–L75`).
- `parse(...)` reads the id and float, then **`player.getNutrition().load(bb)`** — it
  overwrites the receiving side's whole Nutrition (calories, proteins, lipids,
  carbohydrates, weight) — then deserialises the food into a **detached copy**
  (`@0–@51 L53–L63`).
- `processClient(UdpConnection)` → `player.EatOnClient(food, percentage)` — hook only
  (`@0–@19 L80–L81`).
- `processServer(PacketType,UdpConnection)` → `if (isConsistent(conn)) processClient(conn)`
  — the **same** hook-only handler (`@0–@13 L85–L86`).
- `isConsistent` requires a consistent player id, non-null food, and
  `0 ≤ percentage < 100.0` (`@0–@42 L92`).

So the packet's real payload is the **Nutrition snapshot in `parse`**; `processClient`
only fires mod hooks. `Nutrition.save/load` order is
calories, proteins, lipids, carbohydrates, weight (float)
(`Nutrition.save @0–@45 L209–L213`, `Nutrition.load @0–@41 L217–L221`, and note `load`
goes through the clamping setters).

`GameClient.eatFood(IsoPlayer,Food,float)V @0–@49 L2041–L2047` builds an `EatFoodPacket`,
`set`s it, and sends it on `GameClient.connection`. **It has no callers** — a jar-wide
scan finds none, and `grep -r eatFood media/lua` finds none. It is the client→server
direction of a design that is currently only used server→client (the send inside
`Eat @732–@759 L5808`). Treat it as latent/legacy, but note a mod *could* call it.

---

## Q7 inputs — everything the code says about sides

For the later measured-MP row. All Ev = C.

1. **`Eat` runs on the server in MP, on the local machine in SP.** Chain in Q8.
   Citation set: `LuaTimedActionNew.complete @31 L162`; `LuaTimedActionNew.start @60–@96 L127–L129`;
   `ActionManager.update @0 L66`, `@72 L70`; `NetTimedAction.perform @0–@27 L140`;
   `ISEatFoodAction.lua:174`.
2. **Cancels also resolve on the server**: `NetTimedAction.stop @0–@53 L114` → Lua
   `serverStop` (`ISEatFoodAction.lua:141–153`), which re-derives the fraction from
   `self.netAction:getProgress()` (`:151`). The `not isClient() and not isServer()`
   guard at `:136` exists so SP does the same thing without double-applying.
3. **The server pushes the whole Nutrition object at eat time**: `Eat @732–@759 L5808`
   sends `PacketType.EatFood`, whose `write` embeds `Nutrition.save`
   (`EatFoodPacket.write @19–@33 L71`), and whose `parse` on the receiver calls
   `Nutrition.load` (`EatFoodPacket.parse @17–@31 L56`).
4. **And again every second, unconditionally**:
   `NetworkPlayerManager.update @0 L19` is server-gated; `statsUpdateLimit = new UpdateLimit(1000)`
   (`NetworkPlayerManager.<clinit> @13–@23 L10`); the check at `@13 L21` drives
   `NetworkPlayerAI.syncStats @32–@50 L711`, which sends `PacketType.PlayerStats`;
   `PlayerStatsPacket.write @19–@33 L34` embeds `Nutrition.save` and
   `PlayerStatsPacket.parse @31–@45 L48` calls `Nutrition.load`.
   → **1 Hz server→client mirror of calories/macros/weight**, plus the full `Stats` map
   and `BodyDamage` main fields.
5. **The client does not simulate nutrition drain**: `Nutrition.update @42 L75` skips the
   macro decay and `updateCalories()` when `GameClient.client`. It *does* still run
   `updateWeight()` from whatever calories it last received.
6. **`EatOnClient` is stat-free** (`@0–@57 L5725–L5736`) — receiving the `EatFood` packet
   fires `OnEat` only; the numbers arrive via the `Nutrition.load` in `parse`.
7. **`SyncPlayerStats` from `Eat`** covers THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE,
   PAIN bit-masks only (`Eat @658–@722 L5806`) — **no nutrition bits**; plus
   `GameServer.sendSyncPlayerFields(player, 8)` (`@723–@731 L5807`).
8. **Consequence for the mod design:** a client-side Lua mod that writes its own nutrient
   numbers onto `IsoPlayer` will be overwritten by nothing (custom fields aren't in the
   packet) but will **desync from the vanilla numbers**, because vanilla's are recomputed
   server-side and pushed at 1 Hz. Any parallel store must either live server-side
   (`sendClientCommand` → server mutates → server pushes) or accept client-only
   semantics — the same conclusion `docs/testing/spikes.md` §S6 reached for item fields.
9. **Correction to `docs/testing/spikes.md` §S6 wording.** S6 concluded "the client
   computes nutrition; the server keeps a live mirror". The bytecode says the reverse:
   the *server* computes (drain, burn, and `Eat` itself) and pushes at 1 Hz; the client's
   drain is disabled. The 0.2 kcal agreement S6 measured is consistent with both
   readings, so the observation stands but the direction should be flipped.
   Suggested measurement to settle it live: with a client connected, freeze the server's
   `Eat` path and watch whether client calories still fall — under the code reading they
   will not (client decay is off), under S6's they would.

---

## Modifier table

Every row Ev = **C** (read from bytecode / Lua; nothing measured).

| Modifier | Applies to | Effect (with constant) | Source | Ev |
|---|---|---|---|---|
| argument clamp | fraction `f` | `f = PZMath.clamp(f, 0, 1)` | `IsoGameCharacter.Eat(InventoryItem,float,boolean) @18 L5747` | C |
| baseHunger rescale | fraction `f` | `f = clamp01(baseHunger * f / hungChange)` when both ≠ 0 | `Eat @28–@78 L5753–L5757` | C |
| hunger crumb rule | fraction `f` | `f = 1` if `hungChange < 0 && hungChange*(1-f) > -0.01` | `Eat @79–@106 L5760–L5761` | C |
| thirst crumb rule | fraction `f` | `f = 1` if `hungChange == 0 && thirstChange < 0 && thirstChange*(1-f) > -0.01` | `Eat @107–@144 L5764–L5765` | C |
| fraction scaling | THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE | each `stats.add(stat, getter() * f)` | `Eat @145/@163/@181/@199/@217 L5768–L5772` | C |
| fraction scaling | calories, carbs, proteins, lipids | `nutrition.setX(getX() + itemX * f)` | `Eat @246–@338 L5776–L5782` | C |
| **burnt (intake)** | the four nutrients | `+ itemX * f / 5.0` instead | `Eat @341–@446 L5783–L5787` | C |
| non-player guard | the four nutrients | skipped entirely when `Type.tryCastTo(IsoPlayer)` is null | `Eat @235–@251 L5774–L5776` | C |
| stat clamp | HUNGER, THIRST | `PZMath.clamp(v, 0, 1)` — overshoot discarded | `Stats.set @6`; `CharacterStat.clamp @0 L70`; `CharacterStat.<clinit> @91/@231` | C |
| store clamp | calories | `[-2200, 3700]` | `Nutrition.setCalories @1 L321, @12 L324` | C |
| store clamp | carbs / proteins / lipids | `[-500, 1000]` each | `Nutrition.setCarbohydrates/@setProteins/@setLipids @1/@12` | C |
| fraction scaling | painReduction, coldReduction | `+= getPainReduction()*f`, `+= getFluReduction()*f` | `Eat @449 L5789`, `@471 L5790` | C |
| food-sickness cure | FOOD_SICKNESS, POISON | `-= |foodSicknessChange| * f`, guarded by `stat above min && change < 0 && effectiveEdibleBuffTimer <= 0` | `Eat @494–@562 L5791–L5794` | C |
| Iron Gut (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(80, 150)` | `Eat @576–@586 L5796` | C |
| Weak Stomach (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(200, 280)` | `Eat @605–@615 L5798` | C |
| no trait (buff timer) | `effectiveEdibleBuffTimer` | `Rand.Next(120, 230)` | `Eat @621–@631 L5800` | C |
| **cooked** | `getHungerChange` | `× 1.3` — takes precedence over burnt and rot | `Food.getHungerChange @11–@23 L1686-L1687` | C |
| **burnt** | `getHungerChange` | `max(|h|/3.0, 0.01) × sign(h)` | `Food.getHungerChange @42–@62 L1697-L1698` | C |
| **stale** (`offAge ≤ age < offAgeMax`) | `getHungerChange` | `max(|h|/1.3, 0.01) × sign(h)` | `Food.getHungerChange @63–@102 L1700-L1701` | C |
| **rotten** (`age ≥ offAgeMax`) | `getHungerChange` | `max(|h|/2.2, 0.01) × sign(h)` | `Food.getHungerChange @103–@129 L1703-L1704` | C |
| **burnt** | `getThirstChange` | `/ 5.0` — takes precedence over cooked | `Food.getThirstChange @5–@17 L1868-L1869` | C |
| **cooked** | `getThirstChange` | `/ 2.0` | `Food.getThirstChange @18–@28 L1871-L1872` | C |
| *(none)* | `getCalories/Carbohydrates/Lipids/Proteins` | bare `getfield` — no cooked/burnt/rotten/frozen modifier exists | `Food.getCalories @0 L2139` (+ L2115/L2123/L2131) | C |
| burnt / stale / cooked | `getEnduranceChange` | `/3` · `/2` · `×2` | `Food.getEnduranceChange @0–@67 L1605–L1615` | C |
| burnt / stale / rotten / cooked | `getStressChange` | `/4` · `/1.3` · `/2` · `×1.3` | `Food.getStressChange @12–@103 L1717–L1730` | C |
| burnt / stale / rotten / cooked | `getFoodSicknessChange` | `/3` · `/1.3` · `/2.2` · `×1.3` (int truncation) | `Food.getFoodSicknessChange @0–@103 L2078–L2090` | C |
| frozen | `getBoredomChange`, `getUnhappyChange` | `+30` each, unless `type=="Icecream"` or tag `GOOD_FROZEN` | `Food.getBoredomChange @43–@59 L1663-L1664`; `getUnhappyChange @43–@59 L1631-L1632` | C |
| burnt / stale / rotten | `getBoredomChange`, `getUnhappyChange` | `+20` · `+10` · `+20` each | `Food.getBoredomChange @60–@123 L1666–L1675` | C |
| badCold / goodHot | `getUnhappyChange` | `+2` if `isBadCold && isCookable && isCooked && heat < 1.3`; `-2` if `isGoodHot && isCookable && isCooked && heat > 1.3` | `Food.getUnhappyChange @124–@195 L1645–L1649` | C |
| fertilized | boredom / unhappy / stress | all modifiers bypassed, raw field returned; `isRotten()` also forced false | `Food.getBoredomChange @5`, `getUnhappyChange @5`, `getStressChange @0`, `isRotten @0 L1832` | C |
| **RemoveNegativeEffectOnCooked** | item fields `thirstChange`, `unhappyChange`, `boredomChange` | on the cook transition, each is set to 0 **if positive**; permanent, one-shot; nutrition untouched | `Food.update @578–@626 L451–L459` (cook block starts `@413 L423`) | C |
| removeUnhappinessWhenCooked | item field `unhappyChange` | set to 0 on the cook transition | `Food.update @418–@432 L424-L425` | C |
| **useUtensil** | BOREDOM | `× 1.25` if `boredomChange*f < 0`, else `× 0.75` | `BodyDamage.JustAteFood(Food,float,boolean) @322–@379 L624–L633` | C |
| **useUtensil** | UNHAPPINESS | `× 1.25` if `unhappyChange*f < 0`, else `× 0.75` | `JustAteFood @383–@440 L636–L644` | C |
| **useUtensil** | eating duration | `eatingLoop -= 1` when `eatingLoop ≥ 2` (undone for drink-type items at `:232`) | `ISEatFoodAction.lua:224–229` | C |
| poison power | POISON, PAIN | `POISON += poisonPower*f` (Iron Gut `/2` unless type `Bleach`; Weak Stomach `×2`); `PAIN += poisonPower*f/6` | `JustAteFood @0–@101 L587–L598` | C |
| tainted | POISON, PAIN | `POISON += 20.0*f`; `PAIN += 10.0*f/6` | `JustAteFood @177–@223 L607–L610` | C |
| rot sickness roll | POISON | chance% = `clamp(age-offAgeMax,1,5)/(offAgeMax-offAge)*100` (100 if `offAgeMax ≤ offAge`), Iron Gut `/2`, Weak Stomach `×2`, skipped if already infected; hit → `+5*|hungChange*10|*f`, miss → `+2*|hungChange*10|*f` | `JustAteFood @677–@953 L703–L743` | C |
| dangerous uncooked | POISON, healthFromFoodTimer | `healthFromFoodTimer = 0`; chance 75 (5 with tag `EGG`), Iron Gut `/2` (0 for eggs), Weak Stomach `×2`; on hit, not infected, not burnt → `POISON += 15.0*f` | `JustAteFood @555–@676 L669–L696` | C |
| hunger-at-zero health tick | healthFromFoodTimer | when `HUNGER` is at minimum: `+= |getHungerChange()|*f*getHealthFromFoodTimeByHunger()`, doubled if `isCooked()`, capped at `11000.0` | `JustAteFood @454–@538 L650–L660` | C |
| alcoholic | intoxication | `isAlcoholic()` → `JustDrankBooze(food, f)` | `JustAteFood @441–@453 L646-L647` | C |
| Tutorial game mode | everything after mood | early `return` before the sickness rolls | `JustAteFood @539–@554 L664-L665` | C |
| **leftover scaling** | 15 item fields incl. calories/carbs/proteins/lipids | `multiplyFoodValues(1 - f)`; `fluReduction`, `foodSicknessChange`, `poisonPower` truncate to int | `Eat @837–@844 L5825`; `Food.multiplyFoodValues @0–@153 L2288–L2302` | C |
| full-consume | item | `f == 1.0f` → `setHungChange(0)` + `UseAndSync()` | `Eat @803–@820 L5819–L5821` | C |
| post-partial crumb sweep | item | `oldHung == 0 && oldThirst < 0 && newThirst > -0.01` → `setHungChange(0)` + `UseAndSync()` | `Eat @845–@883 L5826–L5829` | C |
| custom weight | item weight | `w' = (w - base) - f0*(w - base) + base`, `base = replaceOnUse item's actual weight`; **uses the pre-rescale `f0`** | `Eat @884–@960 L5832–L5839` | C |
| script→stat scale | HungerChange / ThirstChange / EnduranceChange | `/100` at instantiation; Calories/Carbs/Lipids/Proteins **not** scaled | `Item.InstanceItem @546–@595`, `@745–@781` | C |
| sandbox `Nutrition = false` | macro drain, `updateCalories`, `updateWeight` | all three skipped (early return); **`Eat`/`DrinkFluid` stores unaffected** | `Nutrition.update @0–@12 L65-L66` (only runtime read in the jar) | C |
| `SystemDisabler.doCharacterStats` | `Nutrition.update` | not called at all when false | `IsoPlayer.updateInternal2 @392–@402 L2306-L2307` | C |
| MP client | macro drain + `updateCalories` | skipped when `GameClient.client`; `updateWeight()` still runs | `Nutrition.update @42 L75`, `@106 L81` | C |
| passive drain rates | carbs / lipids / proteins | `−0.0035` / `−0.00113` / `−0.00086` per game-world second | `Nutrition.update @48/@66/@84 L76–L78` | C |
| passive burn | calories | `−0.13×mod×weightRatio` running or sprinting (`mod` 1.0 / 1.3), `−0.13×0.6×…` walking, `−0.003×…` asleep, `−0.016×…` idle; `weightRatio = weight/80`; `mod` also `8.0` while swiping/climbing, else the current action's `caloriesModifier` | `Nutrition.updateCalories @0–@318 L88–L118` | C |
| eating duration | maxTime | `232 × eatingLoop` (food) or `171 × eatingLoop` (drink); loop 1/2/3 at hungerConsumed ≥30/≥80 (food) or thirst ≥3/≥6 (drink) | `ISEatFoodAction.lua:214–243` | C |
| zero-hunger item | maxTime | `460` | `ISEatFoodAction.lua:246` | C |
| `EatTime` script field | maxTime | hard override when `> 0` | `ISEatFoodAction.lua:247` | C |
| `EatType == "popcan"` | maxTime | `160` | `ISEatFoodAction.lua:250–252` | C |
| unhappy / drunk moodles | maxTime | `× (1 + UNHAPPY/4) × (1 + DRUNK/4)`; hand wounds skipped (`ignoreHandsWounds`) | `ISBaseTimedAction.lua:99–106`; `ISEatFoodAction.lua:325` | C |
| instant-action cheat | maxTime | `return 1` | `ISEatFoodAction.lua:204–206` | C |
| FOOD_EATEN moodle | whole action | `isValidStart` false at moodle level ≥ 3; menu shows "can't eat more" | `ISEatFoodAction.lua:14`; `ISInventoryPaneContextMenu.lua:499–504` | C |

---

## Reconstructed pseudo-code of `Eat`

```java
// zombie/characters/IsoGameCharacter.Eat(InventoryItem item, float f, boolean useUtensil)
boolean Eat(InventoryItem item, float f, boolean useUtensil) {

    if (!(item instanceof Food)) return false;              // @1  L5741
    Food food = (Food) item;

    f = PZMath.clamp(f, 0f, 1f);                            // @18 L5747
    float f0 = f;                                           // @25 L5749  (kept for the weight math)

    // --- fraction is re-expressed as a share of what is LEFT --------------
    if (food.getBaseHunger() != 0f && food.getHungChange() != 0f) {   // @28 L5753
        float want = food.getBaseHunger() * f;
        f = PZMath.clamp(want / food.getHungChange(), 0f, 1f);        // @57 L5755-L5756
    }
    // --- don't leave a crumb ----------------------------------------------
    if (food.getHungChange() < 0f
        && food.getHungChange() * (1f - f) > -0.01f) f = 1f;          // @79  L5760-L5761
    if (food.getHungChange() == 0f
        && food.getThirstChange() < 0f
        && food.getThirstChange() * (1f - f) > -0.01f) f = 1f;        // @107 L5764-L5765

    // --- stats (each clamped by CharacterStat; HUNGER/THIRST are [0,1]) ----
    stats.add(THIRST,    food.getThirstChange()    * f);              // @145 L5768
    stats.add(HUNGER,    food.getHungerChange()    * f);              // @163 L5769
    stats.add(ENDURANCE, food.getEnduranceChange() * f);              // @181 L5770
    stats.add(STRESS,    food.getStressChange()    * f);              // @199 L5771
    stats.add(FATIGUE,   food.getFatigueChange()   * f);              // @217 L5772

    // --- nutrition (players only; burnt costs 80%) -------------------------
    IsoPlayer p = Type.tryCastTo(this, IsoPlayer.class);              // @235 L5774
    if (p != null && !food.isBurnt()) {                               // @246 L5776
        Nutrition n = p.getNutrition();
        n.setCalories     (n.getCalories()      + food.getCalories()      * f);   // @281 L5778
        n.setCarbohydrates(n.getCarbohydrates() + food.getCarbohydrates() * f);   // @299 L5779
        n.setProteins     (n.getProteins()      + food.getProteins()      * f);   // @317 L5780
        n.setLipids       (n.getLipids()        + food.getLipids()        * f);   // @335 L5781
    } else if (p != null && food.isBurnt()) {                         // @341 L5783
        Nutrition n = p.getNutrition();
        n.setCalories     (n.getCalories()      + food.getCalories()      * f / 5.0f);  // @380 L5784
        n.setCarbohydrates(n.getCarbohydrates() + food.getCarbohydrates() * f / 5.0f);  // @402 L5785
        n.setProteins     (n.getProteins()      + food.getProteins()      * f / 5.0f);  // @424 L5786
        n.setLipids       (n.getLipids()        + food.getLipids()        * f / 5.0f);  // @446 L5787
    }

    getBodyDamage().setPainReduction(getBodyDamage().getPainReduction()
                                     + food.getPainReduction() * f);  // @449 L5789
    getBodyDamage().setColdReduction(getBodyDamage().getColdReduction()
                                     + food.getFluReduction()  * f);  // @471 L5790

    // --- food-sickness cure ------------------------------------------------
    if (stats.isAboveMinimum(FOOD_SICKNESS)
        && food.getFoodSicknessChange() < 0
        && effectiveEdibleBuffTimer <= 0f) {                          // @494 L5791
        float a = Math.abs(food.getFoodSicknessChange()) * f;         // @524 L5792
        stats.remove(FOOD_SICKNESS, a);                               // @537 L5793
        stats.remove(POISON,        a);                               // @550 L5794
        if      (characterTraits.get(IRON_GUT))     effectiveEdibleBuffTimer = Rand.Next( 80f, 150f);
        else if (characterTraits.get(WEAK_STOMACH)) effectiveEdibleBuffTimer = Rand.Next(200f, 280f);
        else                                        effectiveEdibleBuffTimer = Rand.Next(120f, 230f);
    }

    // --- poison / rot / mood; the ONLY consumer of useUtensil ---------------
    getBodyDamage().JustAteFood(food, f, useUtensil);                 // @634 L5803

    // --- MP: server tells everyone ------------------------------------------
    if (GameServer.server && this instanceof IsoPlayer) {             // @645 L5805
        INetworkPacket.send(SyncPlayerStats, this,
            bits(THIRST|HUNGER|ENDURANCE|STRESS|FATIGUE|PAIN));       // @658 L5806
        GameServer.sendSyncPlayerFields((IsoPlayer) this, 8);         // @723 L5807
        INetworkPacket.send(EatFood, this, food, Float.valueOf(f));   // @732 L5808
    }

    // --- mod hook, AFTER the effects, BEFORE the item is consumed ------------
    if (food.getOnEat() != null) {                                    // @762 L5811
        Object fn = LuaManager.getFunctionObject(food.getOnEat());
        if (fn != null)
            LuaManager.caller.pcallvoid(LuaManager.thread, fn,
                                        item, this, BoxedStaticValues.toDouble(f));  // @785 L5814
    }

    // --- consume the item ----------------------------------------------------
    if (f == 1.0f) {                                                  // @803 L5819
        food.setHungChange(0f);                                       // @809 L5820
        food.UseAndSync();                                            // @815 L5821
    } else {
        float oldHung   = food.getHungChange();                       // @823 L5823
        float oldThirst = food.getThirstChange();                     // @830 L5824
        food.multiplyFoodValues(1.0f - f);                            // @837 L5825
        if (oldHung == 0f && oldThirst < 0f
            && food.getThirstChange() > -0.01f) {                     // @845 L5826
            food.setHungChange(0f);                                   // @871 L5827
            food.UseAndSync();                                        // @877 L5828
            return true;                                              // @882 L5829
        }
        float base = 0f;                                              // @884 L5832
        if (food.isCustomWeight()) {                                  // @887 L5833
            String t   = food.getReplaceOnUseFullType();
            Item   rep = (t == null) ? null : ScriptManager.instance.getItem(t);
            if (rep != null) base = rep.getActualWeight();            // @926 L5837
            float w = food.getWeight();
            food.setWeight( (w - base) - f0 * (w - base) + base );    // @933 L5839
        }
    }
    food.syncItemFields();                                            // @961 L5841
    return true;                                                      // @966 L5843
}
```

---

## Open / uncertain — candidates for live experiments

1. **`f0` vs `f` in the weight write.** `Eat @943 L5839` multiplies by `f0` (the clamped
   argument) while everything else uses the rescaled `f`. On a part-eaten custom-weight
   item they differ, so weight and hunger drift apart. Bytecode is unambiguous about
   *which* local is used (slot 5 = `f0`, stored at `@25 L5749`); what I cannot settle
   from bytecode is whether this is intentional or a bug, and how big the drift gets in
   practice. **Experiment:** eat quarter → quarter → quarter of a canned food and log
   `getWeight()`, `getHungChange()`, `getBaseHunger()` after each.
2. **Which food items actually set `baseHunger ≠ hungChange` at spawn.** Every path I
   found initialises them equal; only `multiplyFoodValues` (which skips `baseHunger`),
   `IsoAnimal.modifyMeat`, `Food.copyNutritionFromRatio`, `RecipeCodeOnCreate.makeCoffee`
   and `ItemStatsPacket.applyItemStats` write `baseHunger` separately. I did not read
   those five. **Experiment / next read:** dump `Food.copyNutritionFromRatio` and
   `IsoAnimal.modifyMeat` to see whether crafted/butchered items keep the invariant.
3. **`getHealthFromFoodTimeByHunger()`** — the multiplier in the healing-from-food block
   of `JustAteFood` was not dumped. Affects nothing in the intake numbers but does affect
   the food→health loop the mod may want to touch.
4. **`Nutrition.caloriesMax` / `caloriesMin` bookkeeping** (`updateCalories @319–@358
   L121–L125`) — these are running extremes, but I did not find where they are read.
   Possibly UI/debug only. Worth one grep before assuming they're inert.
5. **Whether `EatFoodPacket` is broadcast to all clients or only the eater.**
   `INetworkPacket.send(IsoPlayer, PacketType, Object[])` was not dumped; the receiving
   side's `parse` writes into `PlayerID.getPlayer().getNutrition()`, which would be
   correct either way, but the traffic cost differs. **Experiment:** two clients, one
   eats, log `OnEat` firing on the other.
6. **`GameClient.eatFood` is dead in vanilla** — no jar caller, no Lua caller. I cannot
   rule out that a mod or a code path built through reflection/Lua exposure uses it.
   Low risk; note it if a mod conflict shows up.
7. **The `useUtensil` boredom sign test uses `getBoredomChange() * f`** but then applies
   the factor to `getBoredomChange() * f` again (`JustAteFood @360–@379 L633`) — the
   product is computed twice, which is fine, but it means the test is on the *scaled*
   value. Since `f > 0` the sign is the same; harmless, recorded for completeness.
8. **`Nutrition = false` behaviour is inferred, not observed.** The reading "stores still
   fill, nothing ever drains, weight frozen" follows from one early return plus the
   absence of any other read. **Experiment:** sandbox with `Nutrition = false`, eat a
   large meal, watch `getNutrition():getCalories()` over an in-game day.
9. **S6 direction flip (see Q7 §9)** — needs the live check described there before
   `docs/testing/spikes.md` is amended.
10. **Rot-roll denominator when `offAgeMax == offAge`.** The code takes the `100%` branch
    (`JustAteFood @759 L720`), so any item with equal thresholds is a guaranteed sickness
    roll once rotten. No vanilla item was checked for that shape. **Next read:** scan
    `food.txt` for `DaysFresh == DaysTotallyRotten`.
