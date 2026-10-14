# Trait levers: how a mod can change the vanilla weight, strength and fitness creation traits (42.21)

Research note, read-only. Build: 42.21.0 install and jar `4a0e9546ec` (2026-10-14).
Jar reads are `pz.sh dump|refs|methods|grep` on that jar; offsets are bytecode `@`, lines are the class's `L` numbers.
Install paths are relative to `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\`.
Markers: **[code]** = read in code on 42.21; **[inferred]** = follows from code read but not traced end to end; **[live]** = needs a live check.
Register tags are given where the repository already holds a row; most of those rows were read on 42.20.4, and the ones re-checked here are noted.

---

## 1. How a trait definition is made

### 1.1 Where vanilla defines them

- **Script, not Lua.** All 97 vanilla definitions are `character_trait_definition` blocks inside `module Base` in `scripts/generated/characters/character_traits.txt` (1084 lines, 97 blocks). **[code]**
- The block names its trait through the key `CharacterTrait = base:<id>`, which resolves against the trait registry `Registries.CHARACTER_TRAIT` (`CharacterTraitDefinitionScript.loadCharacterTraitDefinition @164–@189 L60–L61`). The definition is **keyed by that registry object, not by the block name** (see 2.1). **[code]**
- Lua builds nothing on 42.21. `shared/NPCs/MainCreationMethods.lua:103–111` (`DoTraits`, run at `OnGameBoot`, `:6364`) only loops `CharacterTraitDefinition.getTraits()` and rewrites each description (`SetTraitDescription`, `:113–135`), appending one `+N Perk` line for each XP boost through `setDescription` (`:134`). **[code]**
- `CharacterTraitDefinition.addCharacterTraitDefinition` is public static and Lua-exposed [#1212/C/C-only]; it is the call the script loader makes (`loadCharacterTraitDefinition @648–@658 L105`). **[code]**

### 1.2 The fields

The script keys parsed by `loadCharacterTraitDefinition` (`@164–@598 L60–L96`), with the default each takes when a body omits it (`@0–@37 L31–L37`) **[code]**:

| Script key | Default when omitted | Lands in | Lua getter / setter |
|---|---|---|---|
| `CharacterTrait` | null | `characterTraitType` (the map key) | `getType()` |
| `UIName` | null | `displayName` = `Translator.getText(key)` at construction (`<init> @48–@62 L35`) | `getLabel()` / none |
| `Cost` | 0 | `cost` (`Integer.parseInt`) | `getCost()` / **no setter** |
| `UIDescription` | null | `description` = `getText(key)` if non-empty (`<init> @70–@88 L37–L38`) | `getDescription()` / `setDescription(String)` (`L160`) |
| `IsProfessionTrait` | false | `isProfessionTrait`, read back as `isFree()` (`isFree @0–@4 L100`) | `isFree()` / **no setter** |
| `DisabledInMultiplayer` | false | `disabledInMultiplayer` | `isDisabledInMultiplayer()` / `setDisabledInMultiplayer(bool)` |
| `XPBoosts` | none | `xpBoosts` HashMap\<Perk,Integer\> via `addXPBoost` (`@663–@715 L106–L107`) | `getXpBoosts()` returns the **live** map (`L133`) / `addXPBoost(Perk,int)` (`HashMap.put`, `L178`) |
| `MutuallyExclusiveTraits` | none | `mutuallyExclusiveTraits` via `addMutuallyExclusive` (`@721–@756 L109–L110`) | `getMutuallyExclusiveTraits()` returns the **live** list (`L129`) / `addMutuallyExclusive` (one-way, `L182`), static `setMutualExclusive(a,b)` (two-way, `L73–L81`) |
| `GrantedTraits` | none | `grantedTraits` via `addGrantedTrait` (`L115–L116`) | `getGrantedTraits()` returns a **copy** (`L113`) / `addGrantedTrait` only |
| `GrantedRecipes` | none | `grantedRecipes` (`L112–L113`) | `getGrantedRecipes()` / `addGrantedRecipe` |
| `Texture` | `media/ui/Traits/trait_<name>.png`, else `trait_generic.png` (`<init> @97–@135 L41–L43`) | `texture` | `getTexture()` / `setTexture` |

An unknown key logs `Unknown key '%s' in CharacterTraitDefinitionScript` and **throws in `-debug`** (`@598–@644 L98–L100`). **[code]**
The registry behind the definitions is a static `LinkedHashMap` (`<clinit> @0–@7 L19`); `getTraits()` returns a **new ArrayList copy** of its values (`L64`). **[code]**
`DisabledInMultiplayer` has no reader anywhere: a jar-wide literal grep finds `isDisabledInMultiplayer` only in its own class, and no install Lua calls it, so it is inert on 42.21. **[code]**

### 1.3 The in-scope traits as shipped on 42.21 (`character_traits.txt`) **[code]**

| Trait (line) | IsProfessionTrait | Cost | XPBoosts | MutuallyExclusiveTraits |
|---|---|---|---|---|
| Obese (`:743`) | **true** | 0 | Fitness=-2 | athletic, emaciated, fit, lighteater, very underweight, underweight, overweight |
| Overweight (`:788`) | **true** | 0 | Fitness=-1 | athletic, fit, emaciated, very underweight, underweight |
| Underweight (`:978`) | **true** | 0 | Fitness=-1 | obese, very underweight, overweight |
| Very Underweight (`:1002`) | **true** | 0 | Fitness=-2 | athletic, obese, overweight, heartyappetite, underweight |
| Emaciated (`:281`) | **true** | -10 | — | obese, overweight |
| Weight Gain (`:1037`) | false | -2 | — | weightloss; **GrantedTraits = overweight** |
| Weight Loss (`:1049`) | false | -2 | — | weightgain; **GrantedTraits = underweight** |
| Weak (`:1014`) | false | -10 | Strength=-5 | feeble, stout, strong |
| Feeble (`:325`) | false | -6 | Strength=-2 | stout, strong, weak |
| Stout (`:910`) | false | 6 | Strength=2 | feeble, strong, weak |
| Strong (`:922`) | false | 10 | Strength=4 | feeble, stout, weak |
| Unfit (`:990`) | false | -10 | Fitness=-4 | athletic, fit, out of shape |
| Out of Shape (`:776`) | false | -6 | Fitness=-2 | athletic, fit, unfit |
| Fit (`:358`) | false | 6 | Fitness=2 | athletic, obese, out of shape, overweight, unfit |
| Athletic (`:58`) | false | 10 | Fitness=4 | overweight, fit, obese, out of shape, unfit, very underweight, smoker |

Consequence: **on 42.21 none of the five weight-band traits is directly selectable.** The creation lists admit only `not isFree() and cost > 0` (good list) or `cost < 0` (bad list) (`client/OptionScreens/CharacterCreationProfession.lua:901`, `:912`), and all five carry `IsProfessionTrait = true`. Overweight and Underweight reach a character only as the free grants of Weight Gain and Weight Loss; Obese, Very Underweight and Emaciated are unreachable at creation in vanilla. **[code]**
The Fitness offsets match the register's 42.20.4 reading [#0539/C/C-only]; the grants match [#0548/C/C-only] [#0549/C/C-only].

---

## 2. How a mod changes a vanilla trait's cost, description, XP boost or exclusions

### 2.1 A same-name script block replaces the whole definition (it does not merge per key) — **[code]**, **[live]** to confirm

- A repeated block name appends a body to the existing script object, and `ScriptBucket.LoadScripts` calls `Load` **once per body** in order (`@154–@216 L253–L259`, verified on the 42.21 jar), as the item pass relies on [#1183/M/n=2].
- Unlike `Item.Load`, which assigns per key, `CharacterTraitDefinitionScript.Load` (`@0–@27 L24–L27`) → `loadCharacterTraitDefinition` builds every field **from that body's keys alone, starting from the defaults** of 1.2, and ends in `addCharacterTraitDefinition` (`@648–@658 L105`), which does `characterTraitDefinitions.put(trait, new definition)` (`addCharacterTraitDefinition @0–@31 L54–L56`). `put` on an existing key **replaces** the object (LinkedHashMap keeps its list position).
- So the **last body in replay order wins outright**: a mod body that omits `XPBoosts` leaves the trait with no boost; one that omits `IsProfessionTrait` makes it `false` (selectable); one that omits `CharacterTrait` registers a definition under the **null** key and leaves vanilla's untouched, while that junk entry then appears in `getTraits()` and is iterated by the creation UI and by `DoTraits`. **A mod override must restate the full block.** **[code]**
- This is the opposite of the item merge and is **not** the craftRecipe append either: the script object appends, but the definition registry replaces.
- Name it exactly as vanilla does (`module Base { character_trait_definition base:obese { … } }`) so it lands in the same bucket entry and replays after vanilla's body (vanilla files before mod files, path-sorted [#1183/M/n=2]). A **differently named** block carrying `CharacterTrait = base:obese` also replaces vanilla's definition, but `LoadScripts` walks the bucket's `HashMap.values()` (`@0–@7 L231`), so its order against vanilla's block is hash order, not path order. **[code]** / **[inferred]**
- Workshop precedent: Girth's Tweaks ships `module Base { character_trait_definition base:desensitized { … full block, Cost = 8, an extra exclusion … } }` (`workshop/content/108600/3745960616/mods/GirthsTweaks/42/media/scripts/GT_DesensitizedTrait.txt:1–13`), a full restatement. **[code]** (the corpus file; its effect is not measured)
- Script files are checksummed byte for byte between client and server [#1182/C/C-only], so a script override must ship identically on both sides (it does when the mod is in `Mods=`).

### 2.2 Lua can edit the existing definition object — **[code]**, **[live]** for the Kahlua overload arms

What Lua can change in place:

| Change | Lever | Notes |
|---|---|---|
| XP boost (add or replace a perk) | `def:addXPBoost(Perks.Fitness, n)` | `HashMap.put` with `Integer.valueOf` (`L178`); replaces an existing entry |
| XP boost (drop a perk) | `def:getXpBoosts():remove(Perks.Fitness)` | live map (`L133`). Do **not** `:put` from Lua: a Lua number arrives as a Double and `applyTraits` does `checkcast Integer` (`@168 L11685`) — **[inferred]** |
| Exclusion (add or remove) | `def:getMutuallyExclusiveTraits():add(CharacterTrait.X)` / `:remove(CharacterTrait.X)`, or static `CharacterTraitDefinition.setMutualExclusive(a, b)` (both directions plus `updateMutualExclusiveTraits`, `L73–L81`, `L206–L218`) | live list (`L129`). Whether Kahlua binds `remove(Object)` rather than `remove(int)` for a `CharacterTrait` argument is **[live]**; the corpus uses exactly this form (below) |
| Description | `def:setDescription(s)` (`L160`) | vanilla's `DoTraits` at `OnGameBoot` then **appends** the XP lines to whatever is there (`MainCreationMethods.lua:114–134`) |
| Granted trait | `def:addGrantedTrait(t)` only | `getGrantedTraits()` is a **copy** (`L113`), so a grant (Weight Gain → Overweight) **cannot be removed from Lua** except by re-adding the definition |
| Cost, `IsProfessionTrait` (selectability), UIName | **no setter** | only by re-adding (`addCharacterTraitDefinition`, which replaces) or a script override |
| Re-add | `CharacterTraitDefinition.addCharacterTraitDefinition(CharacterTrait.OBESE, "UI_trait_obese", cost, "UI_trait_obesedesc", free[, disabledMP])` | a **fresh** object: every boost, exclusion, grant and recipe must be re-added by hand; the name and description arguments are translation **keys** (`<init>` calls `getText`) |
| Remove a definition from the list | not possible | `getTraits()` is a copy (`L64`); `reset()` clears **all** (`L60`) |

When it must run **[code]**:
- Scripts load **before** any Lua on both sides: dedicated server `GameServer.doMinimumInit` runs `ScriptManager.Load` at `@237` before `LuaManager.LoadDirBase` at `@335–@348` and `OnGameBoot` at `@519`; client `GameWindow.init` runs `initShared` (which calls `ScriptManager.Load`, `initShared @145`) at `@243 L1143` before `LoadDirBase` at `@259 L1146`.
- So a **`shared/` file-scope** edit sees the vanilla definitions and runs before vanilla's own `OnGameBoot` `DoTraits` (registered by the earlier-loaded vanilla file, run after every file has loaded), which then appends the boost lines to the edited description. An `OnGameBoot` handler also works, but runs after `DoTraits` and must re-append the boost lines itself (`BaseGameCharacterDetails.SetTraitDescription(def)` is a global function). **[inferred]**
- `ScriptManager.Reset` calls `CharacterTraitDefinition.reset()` (`Reset @125`), so any script reload rebuilds the definitions from scripts and drops Lua edits; on a client this pairs with a Lua reload, which re-runs the file-scope edit. Whether an MP join reloads scripts on the client is **[live]**.
- Workshop precedent for exactly the in-scope edit: `SWMisc_Patches` removes the Fitness boost from Underweight and Overweight at **shared file scope**: `underweight:getXpBoosts():remove(Perks.Fitness)` and the same for Overweight (`workshop/content/108600/3621968227/mods/SWMisc_Patches/42/media/lua/shared/SWMisc_Patches_Traits.lua:5–12`), and edits exclusions with `getMutuallyExclusiveTraits():remove(CharacterTrait.X)` in both directions (`:14–26`). SomewhatTraits adds exclusions to Weight Gain and Weight Loss the same way (`3498347699/mods/SomewhatTraits/42.15/media/lua/shared/SWTraits_MET.lua:29–38`). **[code]** (corpus; not measured here)

### 2.3 Multiplayer: who reads which side's definitions — **[code]**

- The **client's** creation screen reads the **client's** definitions for list membership, cost, points, exclusions and the XP preview (`CharacterCreationProfession.lua:405–432`, `:896–916`, `:643–716`).
- The client sends **only trait names**: `initWorld` copies every selected list item, the free grants included, into `getWorld():addLuaTrait(...)` (`CharacterCreationProfession.lua:1080–1084`; coop at `CoopCharacterCreation.lua:65–68`); `CreatePlayerPacket.set` reads `IsoWorld.getLuaTraits` (`set @26–@41`), `write` puts a short count and one UTF name each (`write @77–@122`), and the server's `parse` rebuilds the list by `CharacterTrait.get(ResourceLocation.of(name))` (`parse @96–@142 L109–L112`).
- The **server** then applies its **own** definitions: `CreatePlayerPacket.processServer` builds the player (`new IsoPlayer @948–@965 L276`), calls `applyTraits(characterTraits)` (`@1021–@1029 L282`), `applyProfessionRecipes` (`L283`), `applyCharacterTraitsRecipes` (`L284`), fires `OnNewGame` (`L291`), saves the player (`ServerPlayerDB`, `L293–L294`) and sends `CreatePlayer` back, whose server-side `write` serialises the whole player (`write @128–@150`, `IsoPlayer.save`).
- So **the XP boosts and the creation weight come from the server's definitions**, and cost and exclusions are **client-UI only**: `processServer` reads no cost and no exclusion (its reference list has no `getCost`, `isFree` or `getMutuallyExclusiveTraits`), and the only jar readers of the exclusion list besides its own class are a debug window (`grep getMutuallyExclusiveTraits` → `CharacterTraitDefinition`, `ScenePanel`). **[code]** The server trusts whatever trait list arrives. **[inferred]**
- Therefore an edit must be in `shared/` (both sides) or the creation screen previews one thing and the server applies another; a client-only edit changes only the display. The profession's XP boosts, by contrast, travel inside the client's `SurvivorDesc` (`SurvivorDesc.save` writes `getXPBoostMap` @145–@198), set client-side by `desc:setProfessionSkills` (`CharacterCreationProfession.lua:476`). **[code]**

---

## 3. What creation does with each trait

### 3.1 `IsoGameCharacter.applyTraits(List)` (`@0–@485 L11655–L11720`) **[code]**

1. Seeds a level map with **Fitness 5 and Strength 5** (`@5–@36 L11659–L11663`).
2. For each trait in the list: `characterTraits.set(trait, true)` (`@72–@79 L11671`), then sums that trait's `getXpBoosts()` from the **current** definition into the map (`@83–@214 L11673–L11690`).
3. **If the character is an `IsoPlayer`, calls `getNutrition().applyWeightFromTraits()`** (`@220–@234 L11694–L11695`).
4. Adds the descriptor's `XPBoostMap` (the profession's boosts) into the same map (`@237–@343 L11699–L11707`).
5. For each perk: clamps to 0..10, **writes `XPBoostMap[perk] = min(3, level)` back into the descriptor** (`@406–@441 L11712–L11714`), calls `LevelPerk(perk)` `level` times (`@445–@464 L11715–L11716`), then `XP.setXPToLevel(perk, level)` (`@467–@479 L11718`).

Callers: the MP server's `CreatePlayerPacket.processServer @1029 L282`; single-player `IsoWorld.init @5285 L2714` (with `getLuaTraits()`); and `LuaManager$GlobalObject.addPlayerToWorld @134`. On an MP client `IsoWorld.init` instead sends `sendCreatePlayer` (`@4386 L2586`) and waits for the server's player (`L2587`). **[code]**

### 3.2 `Nutrition.applyWeightFromTraits()` (`@0–@100 L225–L240`) **[code]**

Five sequential `if hasTrait` → `setWeight`: Emaciated 50.0 (`L225–L226`), Very Underweight 60.0 (`L228–L229`), Underweight 70.0 (`L231–L232`), Overweight 95.0 (`L234–L235`), Obese 105.0 (`L237–L238`). With no band trait it writes nothing, so the weight stays at its default. The values match [#0533/C/C-only]; the order (last match wins) is [#0597/C/C-only/open].
It runs **inside `applyTraits`, before the perk levels are written and before `OnNewGame`**, on the server in MP.

### 3.3 The Strength and Fitness levels, and the band-trait remap at creation **[code]** / **[inferred]**

- Starting level = 5 + sum of the trait boosts + profession boosts, clamped 0..10 (3.1). Example: Strong → Strength 9; Weak → 0; Overweight → Fitness 4; Obese → Fitness 3.
- `LevelPerk(perk)` → `LevelPerk(perk, true)` (`L4873`) fires the Lua **`LevelPerk` event on every increment**, in both branches (`@163–@180 L4853`, `@277–@294 L4868`).
- The server file `server/XpSystem/XpUpdate.lua:196–238` (`Events.LevelPerk.Add`, `:389`) strips WEAK/FEEBLE/STOUT/STRONG (and UNFIT/OUT_OF_SHAPE/FIT/ATHLETIC) and adds one by the level [#2157/C/C-only]. Since `applyTraits` climbs from 0 one level at a time, **the trait a character ends creation with is the remap's band for its final level**, not necessarily what was picked. **[inferred]**
  - Consequences: Weak (level 0) fires no event and keeps WEAK; Feeble ends FEEBLE at 3; Stout STOUT at 7; Strong STRONG at 9.
  - **Weight Gain** → Overweight (Fitness −1) → Fitness 4 → the remap adds **OUT_OF_SHAPE** although it was never picked; Obese or Very Underweight (Fitness 3) would do the same.
  - A mod that changes a strength trait's boost changes the trait the character ends up with: Strong at +2 ends at 7 and is remapped to STOUT. **[inferred]**, **[live]**
- `IsoPlayer`'s constructor runs **before** `applyTraits` in `processServer` (`L276` vs `L282`), and [#2144/C/C-only] puts STRONG/WEAK/FEEBLE/STOUT into `maxWeightDelta` only in the constructors. A freshly created character's carry delta may therefore miss its strength trait until it is next constructed (a reconnect or load). **[inferred]**, **[live]**
- Side effect: step 5 sets the descriptor's XP-boost map to `min(3, level)` for Fitness and Strength as well, so a default 5 writes 3 into it. What that map does to later XP gain is not read here. **[code]**

### 3.4 Replacing or undoing it at creation **[code]** / **[inferred]**

- **Server-side `OnNewGame` is the lever.** It fires at `CreatePlayerPacket.processServer @1074–@1082 L291` as `triggerEvent("OnNewGame", player, nil)`, after `applyTraits`, the weight write and the recipe grants, and **before** the player is saved (`L293–L294`) and serialised back to the client (`L296–L299`). A handler there can `getNutrition():setWeight(w)`, add or remove traits (`getCharacterTraits():add/remove`), and rewrite levels. Its writes travel to the owning client inside the `CreatePlayer` reply's `IsoPlayer.save`. **[code]** for the order, **[live]** for arrival.
  - Vanilla uses this hook server-side: `shared/Items/SpawnItems.lua:142–146` returns on `isClient()` and then reads `getCharacterTraits():getKnownTraits()` (`:263–264`); `server/XpSystem/XpUpdate.lua:343–345` and `:391` run `getFitness():init()` there.
  - `OnNewGame` **also** fires on the MP client once the server's player has arrived (`IsoWorld.init @4673–@4680 L2627`), with the square as the second argument; a `shared/` handler must branch on `isServer()` / `isClient()` as `SpawnItems` does.
  - A level rewrite: `setPerkLevelDebug` fires no `LevelPerk` and no remap [#2870/M/n=1]; `LevelPerk` does fire it. The band traits must be set to match by hand, or the remap's next run (a real level change) reassigns them.
- **Client-side before the send**: wrap `CharacterCreationProfession.initWorld` (`:1069–1084`) to edit `getWorld():getLuaTraits()` before `sendCreatePlayer` reads it. That edits only what the client asks for; the server still applies its own definitions. **[inferred]**
- `applyWeightFromTraits` itself is a Java method; it cannot be replaced, only overwritten after it runs (`OnNewGame`), or avoided by not sending a band trait.

### 3.5 Hiding a vanilla trait, or re-describing it **[code]**

- **Hide (robust):** make the definition `IsProfessionTrait = true` through a full-block script override (2.1) or a Lua re-add with `free = true`. `isFree()` is the flag both list builders filter on (`:901`, `:912`) **and** the one `doTestForMutuallyExclusiveTraits` skips when it re-adds an excluded trait (`:669`). This is how vanilla hides the five band traits.
- **Hide (UI wrap):** wrap `populateTraitList` / `populateBadTraitList` or `isTraitEnabled` (`:888–894`) and drop the item, as Girth's Tweaks does for Restless Sleeper (`3745960616/mods/GirthsTweaks/42/media/lua/client/GT_NoRestlessSleeper.lua:7–24`). Leak: `doTestForMutuallyExclusiveTraits` re-adds an excluded trait straight to a list with `addUniqueItem` when its excluder is removed (`:670–676`), bypassing the wrapped builder until the next repopulate. **[inferred]**
- A trait set to `Cost = 0` while not free still lands in the **bad** list through that re-add arm (`:674–675`, the `else` of `cost > 0`). **[inferred]**
- **Re-describe:** override the translation keys `UI_trait_*` / `UI_trait_*desc` in the mod's `Translate/EN/*.json`: a mod's value for a vanilla key wins on the client [#1164/M/n=1]; client `Translator.loadFiles` runs before the scripts build the definitions (`GameWindow.init L1137` vs `L1143`). Or `setDescription` at file scope (2.2). Both are display-only; the server keeps vanilla strings [#1164/M/n=1].

---

## 4. Hooks: "the player finished creation, here are the chosen traits" on a dedicated server

- **`OnNewGame(player, square)`** fires on the dedicated server once per new character, from `CreatePlayerPacket.processServer @1074–@1082 L291`, **after** `applyTraits` has set every chosen trait on the player and written weight and levels, with `square = nil`. The server sees the traits there through `player:getCharacterTraits():getKnownTraits()` (the vanilla precedent is `SpawnItems.lua:263–264`) or `player:hasTrait(CharacterTrait.X)`. **[code]**; the live reading is **[live]**.
  - The list it sees is the client's selection **after** the remap of 3.3 (a strength or fitness band trait may already differ from the pick), plus the free grants the client sent. **[inferred]**
  - The originally picked list is not kept elsewhere on the server: `CreatePlayerPacket.characterTraits` is a packet field, not on the player. **[inferred]**
- **`OnCreatePlayer`** is **client-only**: its trigger sites are `GameLoadingState.exit @77`, `LuaManager$GlobalObject.initUISystem @3` and `AddCoopPlayer.update @768`, and the literal appears in no server packet or `GameServer` class (jar-wide `grep OnCreatePlayer`: those three plus the `LuaEventManager` registration). **[code]** Girth's Tweaks therefore removes a trait in `OnCreatePlayer` and then forwards it to the server with `sendClientCommand` (`GT_NoRestlessSleeper.lua:26–33`).
- `OnNewGame` on the client side fires at `IsoWorld.init L2627`; a server-authoritative design ignores it or guards it. **[code]**

---

## 5. Mutual exclusions

- **Data:** each definition holds a one-way list (`MutuallyExclusiveTraits` script key → `addMutuallyExclusive`, `L182`). Vanilla writes most pairs on both sides, but not all: Overweight does not list Obese while Obese lists Overweight; Athletic lists Very Underweight but not Underweight, and Underweight does not list Athletic (1.3). **[code]**
- **Test:** `isMutuallyExclusive(other)` (`@0–@76 L191–L202`) is true when this trait's list holds the other's type, **or when any trait this one grants lists it**. So Weight Gain is blocked by Athletic and Fit through its grant Overweight's list, with no exclusion of its own. **[code]**
- **Enforcement:** UI only. The creation screen removes excluded items from the lists on add (`doTestForMutuallyExclusiveTraits`, `:665–686`), filters with `isTraitExcluded` (`:688–695`, a one-way `trait:isMutuallyExclusive(selected)`), and drops picks excluded by a profession's grants (`:447–453`). The server applies whatever list it receives (2.3). **[code]**
- **Changing them:** add with `def:addMutuallyExclusive(t)` (one way), `def:getMutuallyExclusiveTraits():add(t)` (one way), or `CharacterTraitDefinition.setMutualExclusive(a, b)` (both ways, `L73–L81`); remove with `def:getMutuallyExclusiveTraits():remove(t)` on each side; or restate the block in a script override. Because the UI test is one-way on the candidate trait, an exclusion should be written on **both** definitions, as the corpus mods do (2.2). **[code]**, the Kahlua `remove` arm **[live]**
- The weight-band traits are also kept exclusive **at runtime by a different mechanism**, unrelated to the definitions: `applyTraitFromWeight` removes all five and re-adds one by weight [#0531/M/n=1] [#2722/C/C-only]. The Strength and Fitness ladders likewise go through the `LevelPerk` remap [#2157/C/C-only]. Editing the definition's exclusions changes neither.

---

## 6. Compact answers

1. **Definition:** `character_trait_definition base:<id>` blocks in `module Base`, `scripts/generated/characters/character_traits.txt`; fields `CharacterTrait`, `UIName`, `Cost`, `UIDescription`, `IsProfessionTrait` (= `isFree`), `DisabledInMultiplayer` (inert on 42.21), `XPBoosts`, `MutuallyExclusiveTraits`, `GrantedTraits`, `GrantedRecipes`, `Texture`. Lua only rewrites the descriptions at `OnGameBoot`. On 42.21 the five weight-band traits are `IsProfessionTrait = true` and unselectable; Overweight and Underweight arrive only as grants of Weight Gain and Weight Loss.
2. **Changing one:** a same-name script block **replaces the whole definition** (a fresh object per body, keyed by the trait, last body wins, omitted keys default), so restate the full block. From Lua, at `shared/` file scope, edit the live object: `addXPBoost` and `getXpBoosts():remove`, `getMutuallyExclusiveTraits():add/remove` or `setMutualExclusive`, `setDescription`. Cost, free flag and name have no setter, so they need a re-add or a script override; a grant cannot be removed from Lua. The server applies its own definitions for XP boosts and weight, while the client UI uses its own for cost and exclusions, so the edit must load on both sides.
3. **Creation:** the server's `applyTraits` sets the traits, sums the XP boosts on a base of Fitness 5 and Strength 5, writes the band weight via `applyWeightFromTraits` (50/60/70/95/105, sequential ifs), adds the profession boosts, and climbs the levels through `LevelPerk`, which fires the `XpUpdate.lua` remap at every step. A server `OnNewGame` handler runs after all of that and before the save and reply, so it can overwrite weight, traits and levels. A trait is hidden by the free flag, or more weakly by a list-builder wrap, and re-described by a translation override or `setDescription`.
4. **Hook:** `OnNewGame(player, nil)` on the dedicated server, after the traits are applied; `OnCreatePlayer` never fires there. `OnNewGame` also fires on the client after the server's player arrives.
5. **Exclusions:** one-way lists plus grant inheritance, enforced only by the creation UI; a mod adds or removes them on both definitions from Lua or restates the block. The runtime band swaps (weight, Strength, Fitness) are separate engine and Lua mechanisms that the definition's exclusions do not touch.

---

## 7. What a live harness session would need to settle

1. **Script override semantics:** a mod `module Base` block `base:obese` with only `Cost` changed. Does the server's `getCharacterTraitDefinition(OBESE)` read the new cost **and** an empty XP map (full replace)? Does a block that omits `CharacterTrait` leave a null-keyed entry in `getTraits()`? Read on both sides.
2. **Lua edit arms:** at `shared/` file scope, `getXpBoosts():remove(Perks.Fitness)`, `addXPBoost(Perks.Strength, 2)` and `getMutuallyExclusiveTraits():remove(CharacterTrait.X)`. Read back on both sides; confirm Kahlua binds `ArrayList.remove(Object)`, and that a Lua `HashMap.put` stores a Double (the expected failure).
3. **Client definitions after an MP join:** do the client's definitions reflect the server's mod list (script reload plus Lua re-run) at the creation screen, and do the mod's `UI_trait_*` keys show there?
4. **Server `OnNewGame` at creation:** does the handler see the chosen traits, the 95/105 weight and the summed levels? Do its writes (setWeight, trait add or remove, a level change) reach the owning client in the `CreatePlayer` reply, without a separate push?
5. **The creation remap:** does a Weight Gain character start with OUT_OF_SHAPE (Fitness 4)? Does a Strong trait at a modded +2 end as STOUT?
6. **Carry capacity at creation:** does a freshly created Strong or Weak character carry its trait's `maxWeightDelta` before and after a reconnect (constructor-before-`applyTraits` ordering)?
7. **Trust boundary:** does the server accept a trait list that breaks cost or exclusions, e.g. Obese sent directly, or Obese plus Overweight (and which weight wins, [#0597/C/C-only/open])?
8. **The `min(3, level)` write** into the descriptor's XP-boost map for Fitness and Strength: read the map after creation, and trace what it does to XP gain (a jar read before the live one).
