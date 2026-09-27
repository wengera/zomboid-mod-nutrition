# How the game reacts to the mod's writes — vanilla and other-mod compatibility

Scope: what the engine's own Java and the shipped `media/lua` do when the planned nutrition mod
writes the surfaces § 4.1, § 4.3, § 4.5 and § 4.9 of the design name — the perk-level clamp, the
`CalculateStats` takeover, the trait toggles and their push, the stat overwrites, and the vanilla
`Nutrition` sandbox option turned off. Build `42.20.4` · jar `b0bbce05d5`. Every jar cite is
`Class.method @off L<n>` from a dump taken in this session; every Lua cite is `file:line` in
`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`. Absences are quoted greps (§ F).

Sibling reports this one does not repeat: `jar-perks-strength.md` (the perk stores, the XP anticheat,
the Strength and Fitness consumer lists), `jar-endurance-fatigue-sleep.md` (the seven updaters'
formulas and the `CalculateStats` hook site), `jar-health-surfaces.md`, `jar-perception-speed.md`.

## Summary for the design

The engine reacts to almost none of these writes, and that is the problem rather than the relief: every
one of them is a bare field write with no event, no dirty flag and no consumer notification, so what
breaks is not the write but the vanilla bookkeeping that used to follow it.

The perk clamp is the sharpest case. `setPerkLevelDebug` writes `PerkInfo.level` and fires nothing, and
the only vanilla listener of `LevelPerk` is the shipped Lua that maps a Strength level onto
WEAK/FEEBLE/STOUT/STRONG — so the moment the mod clamps, the band traits are stale, and they stay stale
because vanilla's level-up is a *crossing* test on `getTotalXpForLevel(level + 1)` that can never fire
again for a level already passed. The clamp is therefore permanent: the mod owns the Strength level for
the rest of the character's life and must restore it itself. In the other direction the mod is safe only
as long as it never writes a level above the XP-implied one, because `XpUpdate`'s ten-minute rust check is
an *absolute* test that would pull an over-written level down one step at a time. The anti-cheat is not
in play — no XP moves — but the vanilla admin panel is: `SyncXp` from `ISPlayerStatsUI`'s trait editor
sends a client's whole XP object, and the receiving `XP.load` clears `perkList` and the trait list and
rebuilds both from the wire, on the server, with no side gate. The clamp and the trait set must be
re-asserted on a schedule, not once. The good news is that the server already pushes `PlayerXp` to each
owner every 1000 ms, so nothing the mod writes to a level or a trait needs a packet of its own.

`Hook.CalculateStats` is a switch, not a listener: `Event.trigger` returns true whenever the callback list
is non-empty and discards every callback's return value and every callback's error. Registering *is* the
takeover; a handler that throws freezes the stats instead of falling back; and the callback list is
unreadable from Lua — `Hook.CalculateStats` carries only `Add` and `Remove`, and `Event` declares no
accessor — so a second-registrant guard has to be behavioural or has to wrap `Add` before other mods
load. Vanilla claims three of the eight hooks and never this one, and no mod in the 182-folder workshop
corpus on this machine claims it either. Beyond the stats, the seven skipped updaters do six things worth
reproducing — the `lastEndurance` stamp, the ANGER decay, the idle-square timer and its boredom, the
sleeping `timeOfSleep` advance, the thirst ghost-mode gate and the FITNESS stat refresh — and one thing
worth dropping outright, the tripping rotation angle, which nothing reads. None of them touches sleep
wake-up, the exercise system or a packet.

The trait work is the friendliest surface and the one with the sharpest edge for other mods. Field 2 of
`sendSyncPlayerFields` is a pure owner-only push whose receiver *replaces* the whole trait list, so every
push erases a client-only mod's locally added traits — a hazard vanilla already creates on every finished
book read, which the mod would merely make frequent. `applyTraitFromWeight` blanket-removes exactly five
band traits and adds one, and vanilla runs it once per two thousand weight updates; calling it every
minute is the same operation at a thousand times the rate, so it must be gated on a band change. Two
side effects are worth writing into the mod's description rather than discovering in a bug report: a
NIGHT_VISION grant also floors the player's render ambient at 0.20, brightening the screen at night; and
the SHORT_SIGHTED penalty is silently cancelled by glasses on the weapon-sight arm while still moving the
blur and the zombie reveal rate.

On the stat writes, the library's reading holds — a client's `SyncPlayerStatsPacket` never applies on the
server, though not for the reason assumed: the packet has no `processServer` arm at all and its `parse`
has no side gate, and it is server-only because the sole send path is itself gated on `GameServer.server`.
Hunger and thirst have no competing writer beyond the eat and drink the mod already intercepts. Endurance
has three event writers between ticks — one per melee swing, one per vault, one per exercise repetition —
which an absolute per-tick write silently discards. Fatigue is reset above the hook every tick on a
default server, which is exactly why sleep debt belongs in the mod's own store. And `Nutrition.weight` is
not safe: `Commands.player.setWeight` lets any client set any player's weight with no admin check.

Turning the vanilla nutrition option off is narrower than it looks and leaves two live wires. It stops
the macro drain, the calorie update, the weight write and the band-trait refresh, and it freezes the three
weight-trend flags the character screen's arrow reads. It does **not** stop the vanilla protein store from
multiplying Strength XP by 1.5, nor the band traits from gating Fitness XP outright, nor the Nutritionist
food tooltip. So the mod inherits both: it must decide whether to drain the vanilla protein store itself,
and it must treat a band-trait write as a gameplay decision rather than a label.

## A — `setPerkLevelDebug` and everything that reads a perk LEVEL

### A.1 What the setter itself does, and what it does not do

`setPerkLevelDebug(Perk, int)` is nine instructions of field write plus one client-only push. It writes
`PerkInfo.level` on the existing info, or mints a `PerkInfo`, sets its `perk` and `level` and appends it
to `perkList` when the perk has no info yet. Then, and only when `GameClient.client` is non-null **and**
the character is an `IsoPlayer`, it calls `GameClient.sendPerks(player)`. Nothing else is in the body.

| member | signature | side | what it does | cite |
|---|---|---|---|---|
| `IsoGameCharacter.setPerkLevelDebug` | `(Perk;I)V` | either | writes `PerkInfo.level`; creates the info and appends to `perkList` when absent | `IsoGameCharacter.setPerkLevelDebug @0–@15 L4795–L4797`, `@18–@45 L4799–L4802` |
| the same, sync arm | — | client only | `GameClient.client != null && this instanceof IsoPlayer` → `GameClient.sendPerks` | `setPerkLevelDebug @46–@63 L4804–L4805` |
| absent from the body | — | — | no `LevelPerk`, no `AddXP`, no `getXP`, no `XP` field touched, no event trigger, no dirty flag, no `sendObjectChange` | the whole dump is 67 bytes and holds only `getPerkInfo`, `PerkInfo.level`, `PerkInfo.perk`, `perkList.add`, `GameClient.client`, `GameClient.sendPerks` |

So on a dedicated server the call is a pure field write with **no** push of its own and **no** Lua event.
It does not desync by itself either: the server re-pushes the whole XP object to the owning client once
a second (A.4), which is what carries the clamped level down.

### A.2 What goes stale because `LevelPerk` does not fire

`Events.LevelPerk` has exactly one vanilla listener, `xpUpdate.levelPerk`, and it does four things — only
two of which are the trait remap:

| what the handler does | file:line | staleness if the mod clamps without firing it |
|---|---|---|
| `getScriptManager():checkAutoLearn(owner)` on **every** perk's level-up | `server/XpSystem/XpUpdate.lua:204` (handler declared `:202`, registered `:395`) | auto-learned craft recipes are not re-checked; harmless for a Strength clamp, because the clamp never raises a level above what vanilla already levelled through |
| Strength → `remove(WEAK)`, `remove(FEEBLE)`, `remove(STOUT)`, `remove(STRONG)`, then add WEAK 0–1, FEEBLE 2–4, STOUT 6–8, STRONG ≥ 9 (**level 5 gets none**) | `:207–223` | the four Strength band traits keep whatever the last real level-up set, so a clamp from 9 to 4 leaves STRONG on the character — and STRONG is read by `getHittingMod`, `getWeightMod`, the endurance-drain multiplier and every other trait consumer |
| Fitness → the same blanket remove then UNFIT 0–1, OUT_OF_SHAPE 2–4, FIT 6–8, ATHLETIC ≥ 9 | `:227–243` | the mod does not clamp Fitness, so this arm only matters as a surface another mod may own |
| Farming 10, Mechanics 8/9/10, Electricity 3 recipe learning, `+1` if Inventive | `:245–269` | only fires on a rise; a clamp that falls cannot un-learn a recipe, and vanilla re-learns on `OnLoad` (`:353–376`, registered `:399`) |
| nothing else | the XP buffer and the multiplier reset are both commented out | `:274`, `:277–279` | — |

The remap is a **blanket remove then one add**: firing it yourself is safe for the four band traits it
owns and destructive for anything else, because it unconditionally removes all four before it adds one.
A trait mod that grants STRONG for its own reason loses it on the next Strength level-up, in vanilla
already — the mod inherits that, it does not create it.

### A.3 Does vanilla's XP fight a server-written level?

No, and the reason is that both directions are **crossing** tests, not absolute ones.

| test | where | with a clamped-down level |
|---|---|---|
| level up | `threshold = perk.getTotalXpForLevel(getPerkLevel(perk) + 1)`; fires `LevelPerk(perk)` only when `xpBefore < threshold && xpAfter >= threshold`, then loops | `IsoGameCharacter$XP.AddXP @963–@1005 L14293–L14295`, loop back edge `@1098–@1116 L14306` | `xpBefore` is already above the threshold the clamped level implies, so the test fails: **vanilla never walks the level back up**. The mod owns the level from its first write onward and must itself restore it when its ceiling rises |
| level down | `threshold = perk.getTotalXpForLevel(getPerkLevel(perk))`; fires `LoseLevel(perk)` only when `xpBefore >= threshold && xpAfter < threshold`, then loops | `XP.AddXP @1119–@1160 L14309–L14312`, loop back edge `@1177–@1193 L14315` | also a crossing test, so a clamped-down level is not corrected downward either |
| the ten-minute rust check | `if level >= 1 and level <= 10 and getXp():getXP(perk) < PerkFactory.getPerk(perk):getTotalXpForLevel(level) then playerObj:LoseLevel(perk)` — an **absolute** test, run on every online player every ten minutes | `server/XpSystem/XpUpdate.lua:289–297` (the `LoseLevel` at `:294`), called from `xpUpdate.everyTenMinutes` `:299–334`, registered `:381` | this is the one that bites: a level written **above** the XP-implied level is pulled down one step per ten minutes, each step firing `LevelPerk(…, false)` and so remapping the band traits. The design's `min(xpLevel, ceiling)` clamp never crosses it — but only as long as `xpLevel` is computed from `getTotalXpForLevel` and not guessed |
| the Fitness `CharacterStat` refresh | `Stats.set(FITNESS, getPerkLevel(Fitness)/5 − 1)` runs at the **end of every** `AddXP` for Fitness, whether or not a level changed | `XP.AddXP @1196–@1250 L14318–L14319` | so the FITNESS stat tracks the clamped level for free on any Fitness XP gain, independently of the skipped `updateFitness` (§ B.3) |
| the level-up sound | on a server `sendObjectChange(PLAY_GAIN_EXPERIENCE_LEVEL_SOUND)`, locally `playGainExperienceLevelSound()`, suppressed at level 10 and for perks other than Strength/Fitness only in the level-10 guard | `XP.AddXP @1026–@1080 L14297–L14300` | a clamp is silent in both directions, which is the desired behaviour for a ceiling that moves with body composition |

### A.4 The XP packet: who overwrites whom

| member | side | what it does | cite |
|---|---|---|---|
| `NetworkPlayerManager.update` | server | on the **1000 ms** `statsUpdateLimit` it calls `syncStats` and then `syncXp` for every player in `IDToPlayerMap`; damage is 2000 ms and health 500 ms | `NetworkPlayerManager.update @13 L21`, `@122–@141 L31–L33`, `<clinit> @13–@23 L10` |
| `NetworkPlayerAI.syncXp` | server | sends `PacketType.PlayerXp` **to that player's own connection only**, gated on `isFullyConnected` and not a delayed disconnect | `NetworkPlayerAI.syncXp @0–@52 L719–L722` |
| `PlayerXpPacket.parse` | whichever side receives | `isConsistent` and not dead, then `XP.load(bb, 249)` straight over the receiver's copy; a throw is logged as `Player XP load error` and swallowed | `PlayerXpPacket.parse @6–@38 L43–L46`, `@44–@54 L47–L48` |
| `XP.load` | either | calls `CharacterTraits.load(bb)` **first**, then `totalXp`, `level`, `lastlevel`, then `xpMap.clear()` and reload, then **`perkList.clear()`** and a fresh `PerkInfo` per entry with the level read off the wire, then `xpMapMultiplier.clear()` and reload | `XP.load @0 L14384`, `@35–@92 L14388–L14396`, `@99–@109 L14398–L14399`, `@147–@186 L14407–L14410` |
| `PlayerXpPacket.processServer` | server | `sendToClients` — the packet is relayed after `parse` has already applied it | `PlayerXpPacket.processServer @3 L56` |
| the only vanilla client→server sender | client | the Lua global `SyncXp(char)`, from `ISPlayerStatsUI:onAddTrait` and `:onRemoveTrait` — the **admin** trait editor | `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:596`, `:671` |

Two consequences the design must hold. First, the server's write is carried to the owning client for
free on the one-second XP push, traits included, so a clamp needs no packet of the mod's own. Second,
`XP.load` is a **full replace of both the perk-level list and the character-trait list**, and the server
applies it from a client packet with no side gate: an admin adding or removing a trait through the vanilla
player-stats panel pushes that admin client's copy of the target player's levels and traits over the
server's, wiping both a clamped level and a server-side trait toggle in one packet.

### A.5 Who reads a perk LEVEL, and how each sees a clamp

Every Java consumer reads `getPerkLevel(perk)` live inside its own body with no Lua step and no cache
(the Strength and Fitness consumer tables in `jar-perks-strength.md`), so a clamp takes effect on the
next call. The vanilla Lua readers are:

| reader | file:line | how it sees a clamp |
|---|---|---|
| `ISEmptyGraves`, `ISFillGrave`, `ISDestroyStuffAction`, `ISDismantleAction`, `ISPickAxeGroundCoverItem`, `ISMoveableSpriteProps` | `server/BuildingObjects/ISEmptyGraves.lua:19`, `shared/TimedActions/ISFillGrave.lua:21`, `ISDestroyStuffAction.lua:327`, `ISDismantleAction.lua:102`, `ISPickAxeGroundCoverItem.lua:210`, `shared/Moveables/ISMoveableSpriteProps.lua:4058` | read live at action start; a clamp changes the next action's duration and nothing retroactively |
| `FishingRod.lua` | `shared/Fishing/FishingRod.lua:15` | caches `strengthSkill` on the rod object at construction — a clamp mid-session is not picked up until the next rod |
| `ISCharacterScreen.loadTraits` | `client/XpSystem/ISUI/ISCharacterScreen.lua:614–615` | assigns `self.Strength`/`self.Fitness` and **never reads them again** (dead store, grep of `self.Strength` in the file: two writes, no reads) |
| `ISPlayerStatsUI` | `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:704–705` | the same dead store |
| the skill list's own display | `ISCharacterScreen` renders the perk rows from `PerkFactory`/`getPerkLevel` each frame | the clamped level is what the player sees, with the XP bar still at its real fill — a cosmetic mismatch the design should expect |
| `ISCharacterScreen:render` → `traitsChanged` | `:74–75`, `:586–598`, `loadTraits` `:599–616`, also on `setVisible` `:50–52` | rebuilds the trait icon row whenever `getKnownTraits()` differs from the cached list, every frame — so a server-side trait toggle shows up live once the push lands |

## B — `Hook.CalculateStats` as a shared surface, and the seven updaters' non-stat work

### B.1 The hook is a switch, not a listener

| member | side | what it does | cite |
|---|---|---|---|
| `IsoGameCharacter.calculateStats` | either | animal → return; on a server, unless **both** `sleepAllowed` and `sleepNeeded` are true, `Stats.reset(FATIGUE)`; then `TriggerHook('CalculateStats', this)` and **return early when it comes back true**; otherwise the seven updaters in order | `calculateStats @0–@7 L10196`, `@8–@48 L10200–L10201`, `@49–@59 L10204–L10205`, `@60–@88 L10208–L10221` |
| `IsoPlayer.calculateStats` | — | `if (GameClient.client == null) super.calculateStats()` — the whole thing, fatigue reset included, is **server-side or single-player only** for a player | `IsoPlayer.calculateStats @0–@10 L3280–L3281` |
| `LuaHookManager.TriggerHook(String, Object)` | either | `EventMap.get(name)` → `Event.trigger(LuaManager.env, LuaManager.caller, args)` | `LuaHookManager.TriggerHook @10–@40 L36–L38` |
| `Event.trigger` | either | returns **false only when the callback list is empty**; otherwise walks the list, calls each with `LuaCaller.protectedCallVoid` (**return value discarded**), logs any throw through `ExceptionLogger.logException`, and returns **true** | `Event.trigger @0–@11 L26–L27`, `@82 L36`, `@269 L55`, `@194–@198 L41–L42`, `@322–@326 L56–L57`, `@222 L49`, `@350 L64` |
| the eight hooks | — | `AutoDrink`, `UseItem`, `Attack`, `CalculateStats`, `ContextualAction`, `WeaponHitCharacter`, `WeaponSwing`, `WeaponSwingHitPoint` | `LuaHookManager.AddEvents @0–@40 L127–L134` |

Three facts follow, and each is a compatibility rule in its own right.

1. **Registering is the takeover.** Any handler at all — a one-line logger from another mod — makes the
   hook return true and suppresses all seven updaters for every character on that host. The mod's
   "takeover mode" is not a mode it opts into; it is what the hook does. Conversely "overlay mode" is
   only reachable by **not registering**.
2. **An erroring handler does not fall back.** `protectedCallVoid` swallows the error and `trigger` still
   returns true, so a handler that throws every tick leaves hunger, thirst, fatigue, stress, boredom
   and endurance frozen rather than reverting to vanilla. A takeover handler therefore needs its own
   error accounting; the engine will not tell the player anything but a debug-log line.
3. **The fatigue reset is above the hook.** On a dedicated server with the default `SleepNeeded`, fatigue
   is reset to its default every tick *before* the hook fires, so no handler can stop it — which is why
   § 4.4's decision to hold sleep debt in the mod's own state is forced, not preferred.

### B.2 Can a mod count the registrants? No.

| surface | what Lua sees | cite |
|---|---|---|
| the `Hook` table | created by `Platform.newTable` and `rawset` into `LuaManager.env` under `'Hook'` | `LuaHookManager.register @0–@16 L162–L163` |
| `Hook.CalculateStats` | a fresh table holding exactly two keys, `Add` and `Remove`, each a Java function object, `rawset` under the hook's name | `Event.register @0–@42 L120–L125` |
| the callback list | `Event.callbacks`, a `java.util.ArrayList` initialised in the constructor; the class declares **only** `trigger`, `<init>` and `register` — there is no getter, no size accessor and no exposed field | `Event.<init> @4–@12 L23`, `methods zombie/Lua/Event` (three members) |

So there is no read path: a mod cannot ask how many handlers `Hook.CalculateStats` carries, nor list them,
nor learn whether it is first or second. Two routes remain, and both are the mod's own construction:

- **Wrap the door.** `Hook.CalculateStats` is an ordinary Lua table, so `Hook.CalculateStats.Add` can be
  replaced with a Lua function that counts, records the caller and forwards to the original. It works
  because the table is a plain `rawset` table (`Event.register @7 L122`), and it is load-order dependent:
  it only sees registrations made after the wrapper is installed, and it makes the mod the thing other
  mods trip over. Inference from the bytecode, not a measured behaviour.
- **Detect behaviourally.** Register nothing for one tick at boot and watch whether a stat the vanilla
  updaters own moves on its own — e.g. sample `THIRST` across a tick with no handler registered. This is
  the only route that needs nothing of other mods, and it is a live-run question.

Vanilla Lua itself registers three of the eight hooks and **never** `CalculateStats`:

| hook | vanilla registrant | cite |
|---|---|---|
| `AutoDrink` | added and removed around the auto-drink context menu | `client/ISUI/ISInventoryPaneContextMenu.lua:4056`, `:4060` |
| `ContextualAction` | `ContextualActionHandlerWrapper` | `client/TimedActions/ISContextualActions.lua:144` |
| `Attack` | `ISReloadWeaponAction.attackHook` | `shared/TimedActions/ISReloadWeaponAction.lua:544` |
| `CalculateStats`, `UseItem`, `WeaponHitCharacter`, `WeaponSwing`, `WeaponSwingHitPoint` | none | grep `Hook\.[A-Z][A-Za-z]*\.(Add|Remove)` over `media/lua`: 4 hits, the three above |

### B.3 What the seven updaters do besides writing the stats the design reproduces

| updater | stats it writes | its **non-stat** work | who reads that | cite |
|---|---|---|---|---|
| `IsoGameCharacter.updateEndurance` | `ENDURANCE` only under the unlimited-endurance cheat (`Stats.reset`) | `stats.setLastEndurance(stats.get(ENDURANCE))` every call | the only writer of `lastEndurance` in the jar; the design already reproduces it | `updateEndurance @0 L10360`, `@17–@24 L10361–L10362` |
| `updateTripping` | none | `stats.addTrippingRotAngle(0.06f)` while `stats.isTripping()` | **nobody**: the `trippingRotAngle` literal appears in `Stats.class` alone, and `TrippingRotAngle` appears nowhere in `media/lua` — the whole mechanic is inert on this build, so dropping it costs nothing | `updateTripping @0–@20 L10316–L10319`; jar-wide grep `trippingRotAngle` → `zombie/characters/Stats.class` only |
| `updateThirst` | `THIRST`, ×2 with HIGH_THIRST, ×0.5 with LOW_THIRST, the sleeping rate while asleep | none; it carries a **ghost-mode gate** (`isoPlayer.isGhostMode()` → skip) the mod must reproduce or knowingly drop | `updateThirst @2–@37 L10369–L10374`, `@38–@71 L10377`, `@74–@122 L10378–L10379`, `@125– L10381` |
| `updateStress` | `STRESS` from world sounds (skipped when DEAF), from each bitten and each scratched part, from infection, from `getTotalBlood()` when HEMOPHOBIC | **`Stats.remove(ANGER, angerDecrease × multiplier × deltaMinutesPerDay)`** — the only anger decay in the path | `ANGER`'s literal is held by `CharacterStat`, `IsoGameCharacter`, `IsoPlayer`, `Stats` and `Moodle` (method not narrowed) | `updateStress @0–@7 L10333`, `@8–@61 L10337–L10338`, `@62–@143 L10341–L10346`, `@208–@248 L10354`, `@249–@280 L10356–L10357` |
| `updateStats_WakeState` | none of its own | dispatch only: animal → return; runs when `GameServer.server` or (`!GameClient.client` and this is the local player); then `asleep ? updateStats_Sleeping() : updateStats_Awake()` | — | `updateStats_WakeState @0–@45 L10224–L10234` |
| `updateStats_Awake` | `STRESS` decay, `FATIGUE`, `HUNGER` in four arms, `IDLENESS` | **`updateIdleSquareTime()`** (advances or zeroes the `idleSquareTime` field), and `Stats.reset(IDLENESS)` while `isInCombat()` | `idleSquareTime`'s literal is in `IsoGameCharacter.class` only, so it feeds nothing but boredom | `updateStats_Awake @0–@30 L10242`, `@434 L10283`, `@438–@456 L10285–L10286`, `@459–@537 L10287–L10289`, `@538–@595 L10292–L10293`, `@598–@654 L10296–L10297`; `updateIdleSquareTime @0–@54 L17641–L17648` |
| `IsoPlayer.updateStats_Sleeping` | `FATIGUE`, `ENDURANCE`, `HUNGER`, `THIRST` | **`timeOfSleep` advance** (`putfield`), the field the restoration gate compares against `delayToActuallySleep`; no wake-up, no `setAsleep`, no bed release | `timeOfSleep`'s literal is in `IsoGameCharacter.class` and `IsoPlayer.class` only | `IsoPlayer.updateStats_Sleeping @276 L3328`; the only non-`Stats` `putfield` in the whole 262-line dump |
| `updateMorale` | `MORALE += clamp((1 − nicotineStress − 0.5) × 1e-4 (+0.5 when positive), 0, 1)` | none | the `MORALE` literal is held by `CharacterStat`, `IsoGameCharacter` and `Book` only — no moodle, no speed, no combat term | `updateMorale @0–@49 L10303–L10309` |
| `updateFitness` | `Stats.set(FITNESS, getPerkLevel(Fitness)/5 − 1)` | none | **it does not drive the exercise system**: that is `zombie/characters/BodyDamage/Fitness.update()`, a separate object with its own members, and the same stat write also runs at the end of every Fitness `AddXP` | `updateFitness @0–@25 L10312–L10313`; `XP.AddXP @1196–@1250 L14318–L14319`; `methods zombie/characters/BodyDamage/Fitness` |

Nothing in the seven touches sleep wake-up, the exercise system, a packet, a moodle recompute or a
`sendObjectChange`. The complete list of things a takeover drops beyond the stats is therefore: the
tripping rotation angle (inert), the anger decay, the idle-square timer and its boredom, the sleep
`timeOfSleep` advance, the `lastEndurance` stamp, the thirst ghost-mode gate, and the FITNESS stat's
per-tick refresh.

## C — trait writes, `applyTraitFromWeight`, and the trait sync

### C.1 Everything `NIGHT_VISION` and `SHORT_SIGHTED` reach

| trait | reader | side | what it does | cite |
|---|---|---|---|---|
| `NIGHT_VISION` | `LightingJNI.calculateVisionCone` | client | `+36.0 × (1 − dayLightStrength)` degrees on the cone, in both the on-foot and the vehicle arm | `calculateVisionCone @218–@235 L498–L499`, vehicle arm `@322–@325` |
| `NIGHT_VISION` | `RenderSettings$PlayerRenderSettings.updateRenderSettings` | client, render | when the computed `ambient` is **below 0.20**, it is raised to exactly `0.20` — the player's screen gets brighter in the dark, independently of the cone | `updateRenderSettings @411–@438 L199–L200` |
| `NIGHT_VISION` | `SpawnItems.lua` | creation | grants a key-ring item at character creation; never re-read | `shared/Items/SpawnItems.lua:233` |
| `NIGHT_VISION` | `FirearmPanel` | debug | a debug window toggle | jar-wide grep `NIGHT_VISION` → 5 classes: `CharacterTraitScriptGenerator`, `RenderSettings$PlayerRenderSettings`, `FirearmPanel`, `LightingJNI`, `CharacterTrait` |
| `SHORT_SIGHTED` | `LightingJNI.updatePlayer` → native `playerSet` | client | the boolean the native lighting gets; the only sight-distance input | `LightingJNI.updatePlayer @127 L566` (re-used from `jar-perception-speed.md`, not re-dumped here) |
| `SHORT_SIGHTED` | `IsoGameCharacter.updateVisionEffects` | client | the screen blur effect | `updateVisionEffects @0 L16607` (re-used) |
| `SHORT_SIGHTED` | `IsoGameCharacter.getAlphaUpdateRateMul` | either | the rate at which a zombie fades into view | `getAlphaUpdateRateMul @13 L6823` (re-used) |
| `SHORT_SIGHTED` | `HandWeapon.getMaxSightRange` | either | returns `getMinSightRange(character)` outright — **unless `isWearingGlasses()`**, which cancels the trait entirely on this arm | `HandWeapon.getMaxSightRange @0–@22 L1560–L1561` (re-used) |
| `SHORT_SIGHTED` | `TraitClothingSelectionDefinitions.lua` | creation | spawns glasses at creation; never re-read | `shared/Definitions/TraitClothingSelectionDefinitions.lua:101` |

So the design's assumption that these two traits are "perception only" holds, with three caveats: the
night-vision grant also **brightens the screen**, the short-sight penalty is **silently cancelled by
glasses** on the weapon-sight arm (a player wearing any glasses sees no weapon-range penalty from the
mod's clinical-deficiency toggle), and both are read on the **client**, so the toggle is worthless until
the client's copy carries it.

### C.2 `applyTraitFromWeight` — what it owns and what it leaves alone

| what | cite |
|---|---|
| it unconditionally removes exactly five traits — `UNDERWEIGHT`, `VERY_UNDERWEIGHT`, `EMACIATED`, `OVERWEIGHT`, `OBESE` — and touches no other trait | `Nutrition.applyTraitFromWeight @0–@62 L247–L251` |
| then adds one by band: `weight ≥ 100` → OBESE; `85 ≤ w < 100` → OVERWEIGHT; `65 < w ≤ 75` → UNDERWEIGHT; `50 < w ≤ 65` → VERY_UNDERWEIGHT; `w ≤ 50` → EMACIATED; `75 ≤ w < 85` → **no trait** | `@65–@86 L253–L254`, `@89–@121 L256–L257`, `@124–@156 L259–L260`, `@159–@191 L262–L263`, `@194–@215 L265–L266` |
| it pushes nothing: no packet, no `sendSyncPlayerFields`, no dirty flag | the whole dump is 219 bytes and holds only `getCharacterTraits`, `remove`, `add`, `getWeight` |
| vanilla calls it from `Nutrition.updateWeight` **once per 2000 `updateWeight` calls**, behind the `GameClient.client` gate, so on a server only and rarely | `Nutrition.updateWeight @317–@320 L198`, `@329–@346 L200–L201`, `@349–@355 L202–L203` |

For a trait mod: the five band traits are a shared surface and vanilla is the aggressive party — any mod
that grants OBESE or UNDERWEIGHT for its own reason loses it at the next call, in vanilla already. The
design calling `applyTraitFromWeight` after its own weight write is behaving exactly as vanilla does,
only more often; what it must not do is call it when it did not change the weight, because each call is
a remove-then-add that would wipe another mod's band trait on a cadence vanilla never had.

### C.3 What `sendSyncPlayerFields(player, 2)` actually does

| step | what it does | cite |
|---|---|---|
| the Lua global | `sendSyncPlayerFields(IsoPlayer, byte)` returns immediately unless `GameServer.server` is set, then delegates | `LuaManager$GlobalObject.sendSyncPlayerFields @0–@8 L3910–L3911` |
| `GameServer.sendSyncPlayerFields` | returns silently when the player is null **or `onlineId == -1`**; otherwise `INetworkPacket.send(player, PacketType.SyncPlayerFields, {player, byte})` | `GameServer.sendSyncPlayerFields @0–@12 L2459–L2460`, `@13–@32 L2462` |
| `INetworkPacket.send(IsoPlayer, …)` | on a server, `getConnectionFromPlayer(player)` and send to **that one connection**; nothing at all when the connection is null | `INetworkPacket.send @0–@21 L261–L267` |
| the mask | `syncParams` is a **six-bit mask**: `write` and `parse` loop `i = 0..5` and call `writeParam(1 << i)` / `parseParam(1 << i)` for each set bit, so the field values are 1, 2, 4, 8, 16, 32 | `SyncPlayerFieldsPacket.write @16–@45 L143–L145`, `parse @17–@46 L156–L158` |
| the write side | field `2` writes `getCharacterTraits().write(bb)`; vanilla's own comment names the fields `PF_Recipes + PF_Traits + PF_AlreadyReadBook` for mask `0x07` | `SyncPlayerFieldsPacket.writeParam @127–@143 L61–L64`; `shared/TimedActions/ISReadABook.lua:373–374` |
| the read side | field `2` calls `getCharacterTraits().read(bb)` | `SyncPlayerFieldsPacket.parseParam @127–@143 L104–L107` |
| `CharacterTraits.read` | **`reset()` first**, then one `add` per name off the wire | `CharacterTraits.read @0 L115`, `@16–@31 L118–L119` |
| `CharacterTraits.reset` | `knownTraits.clear()` and every entry of the `traits` map set to `false` | `CharacterTraits.reset @0–@9 L154–L155`, `@23–@54 L156–L157` |

Four consequences:

1. It is a **pure push**. The server's own copy is whatever the mod already wrote; the call adds nothing
   to it and can be made freely after the write.
2. It reaches **only the owning client**. No other client's copy of that character's traits is touched,
   and vanilla has no server→everyone trait push at all: the one-second `syncXp` is also owner-only
   (`NetworkPlayerAI.syncXp @6–@13 L720–L721`), and the only path that reaches other clients is a
   *client-originated* `PlayerXp` being relayed (`PlayerXpPacket.processServer @3 L56`).
3. The receiving side is a **full replace**, not a merge: every trait a client-only mod added locally is
   erased on each push. That is a real hazard for client-side trait mods, and it already exists in
   vanilla on every relayed `PlayerXp` (`XP.load @0 L14384` calls the same `CharacterTraits.load`) — but a
   mod that pushes field 2 on every grade change converts a rare event into a frequent one.
4. It silently does nothing for a player with `onlineId == -1` or no connection, so a push is not proof
   of delivery and the mod cannot learn from the call whether it landed.

Vanilla's only other `sendSyncPlayerFields` caller in this area uses a different field: the exercise
system pushes field **32** after each repetition (`Fitness.exerciseRepeat @71–@74 L199–L200`), so nothing
in vanilla competes with the mod on field 2.

## D — the stat overwrites and every competing writer

### D.1 Writers of HUNGER, THIRST, ENDURANCE and FATIGUE outside the seven updaters

| writer | stat | side | cadence | cite |
|---|---|---|---|---|
| `IsoGameCharacter.calculateStats` | `FATIGUE` → `Stats.reset` | server | **every tick**, unless both `sleepAllowed` and `sleepNeeded` are true; runs **above** the hook so no handler can stop it | `calculateStats @8–@48 L10200–L10201` |
| `IsoGameCharacter.Eat` | `HUNGER`, `THIRST`, `ENDURANCE`, `FATIGUE`, plus the four nutrition setters, then the server's `SyncPlayerStats` send | either | per eat | register row [#0006]; the order is `eating-pipeline.md` |
| `IsoGameCharacter.DrinkFluid` | `THIRST` and the nutrition block, unclamped fraction | either | per drink | register rows [#0669], [#0148/open]; `eating-pipeline.md` |
| `CombatManager.processWeaponEndurance` | `ENDURANCE` → `Stats.remove(effectiveWeight × 0.18 × weapon fatigue mod × character fatigue mod × weapon endurance mod × 0.3 (+ two-hand term) × 0.04 × trait endurance-loss modifier)`, skipped when the weapon has `isUseEndurance()` false | either | **per swing** | `processWeaponEndurance @0–@7 L1190–L1191`, `@49–@81 L1200`, `@83–@107 L1201–L1202` |
| `ClimbOverFenceState.enter` | `ENDURANCE` → `Stats.remove`, two arms off `ZomboidGlobals.runningEnduranceReduce` | either | per vault; `ClimbOverWallState` and `ClimbSheetRopeState` hold the same literal | `ClimbOverFenceState.enter @59–@70`, `@105–@108` |
| `Fitness.reduceEndurance` | `ENDURANCE`, base `0.015` scaled by a log of the exercise's regularity | either | per exercise repetition, from `exerciseRepeat` | `Fitness.reduceEndurance @0 L245`, `@34–@54 L253–L254`; `Fitness.exerciseRepeat @32–@35 L195` |
| `SleepingEvent.wakeUp(chr, bool)` | `FATIGUE` → `Stats.remove` on a `'goodBed'` branch; also `setAsleep(false)` | either (the client arm sends `WakeUpPlayer`) | per wake-up | `SleepingEvent.wakeUp @129–@131 L511`, `@175–@220 L526–L527`, client arm `@5–@15 L492–L493` |
| `Nutrition.update` | the four macro stores and, through `updateWeight`, `Nutrition.weight` | server/SP for the macros; `updateWeight` also runs on a client | per `BodyDamage` update | `Nutrition.update @0–@12 L65–L66`, `@42–@106 L75–L81` |
| `Commands.player.setWeight` | `Nutrition.weight` → `setWeight(args.weight)` on **any** player by online id | server, from a client command | on demand | `server/ClientCommands.lua:599–604`; the dispatcher `:1249–1258` has **no admin or capability check** |
| `ISPlayerStatsUI` weight field | the same, client-side when not a client, else the `player`/`setWeight` command | admin UI | on demand | `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:652–666` (`onChangeWeight`, clamped 30–130) |
| `ISStatsAndBody` debug panel | every one of the 24 stats through a slider, `getPlayer():getStats():set(v.enum, …)`, plus `setPerkLevelDebug(Perks.Fitness, …)` | **client only** | on drag | `client/DebugUIs/DebugMenu/General/ISStatsAndBody.lua:35–75`, `:223`, `:229`, `:256` |
| vanilla Lua `syncPlayerStats(player, mask)` callers | no stat write of their own — they push a mask after a Lua-side write | server-gated global | per action | `shared/TimedActions/ISApplyBandage.lua:108`, `ISDrinkFromBottle.lua:82`, `ISRemoveBush.lua:172`, `server/Farming/SFarmingSystem.lua:503` and the other cataplasm actions |
| `ISDrinkFromBottle` | `THIRST` −0.1 per use, hardcoded, no nutrition | either | per use — but its caller chain is dead on this build | register row [#0670/C/snapshot] |
| readers, not writers | `ISWorldObjectContextMenuLogic.createMenuEntries` reads `FATIGUE` (`Stats.get`) to gate the sleep menu | client | per menu | `createMenuEntries @2634–@2637` |

The cadence picture the design needs: the mod's per-tick overwrite competes with nothing on hunger and
thirst except the eat and drink writes it already intercepts; on **endurance** it competes with three
event writers (swing, vault, exercise rep) that fire between ticks, so the design's "write endurance from
the mod's own stored value every tick and never read it back" silently discards the swing and vault
costs unless the mod reproduces them; and on **fatigue** the per-tick `Stats.reset` above the hook is
unbeatable, which is § 4.4's stated reason for holding sleep debt privately.

### D.2 Does a client's `SyncPlayerStatsPacket` ever apply on the server?

The library's answer holds, but the mechanism is not a `processServer` arm — there is none.

| member | what it shows | cite |
|---|---|---|
| `SyncPlayerStatsPacket` members | `<init>`, `getBitMaskForStat`, `setData`, `parse`, `write` — **no `processServer`, no `processClient`** | `methods zombie/network/packets/SyncPlayerStatsPacket` |
| `SyncPlayerStatsPacket.parse` | **no side gate at all**: `PlayerID.parse`, then `syncParams`; when `syncParams == -1` it calls `getNutrition().load(bb)`, otherwise it walks `CharacterStat.ORDERED_STATS` and calls `Stats.parse(bb, i)` for each set bit | `parse @0–@14 L50–L51`, `@17–@42 L53–L54`, `@45–@84 L56–L58` |
| the only send path | the Lua global `syncPlayerStats(player, mask)` is gated on `GameServer.server` and `isExistInTheWorld`, and sends through `INetworkPacket.send(IsoPlayer, …)`, which is **itself** gated on `GameServer.server` and targets that player's own connection | `LuaManager$GlobalObject.syncPlayerStats @0–@32 L9809–L9810`; `INetworkPacket.send @0–@21 L261–L267` |

So the packet is structurally server→one-client: the only overload that sends it refuses to run off a
server, and the receiver has no side gate because it never needs one. Two riders worth the design's
attention: `parse` applies to **whatever player the id names**, not the receiver, and `syncParams == -1`
is a whole-`Nutrition` replace — `Nutrition.load` overwrites calories, proteins, lipids, carbohydrates
**and weight** (`Nutrition.load @0–@41 L217–L222`), so that one mask value is a competing writer of the
weight slot the design owns.

### D.3 The admin stat path

`GameServer.receiveChangePlayerStats` is the `ChangePlayerStats` server arm: it resolves the player from
`IDToPlayerMap`, calls `IsoPlayer.setPlayerStats(reader, utf)` and re-broadcasts `ChangePlayerStats` with
`createPlayerStats` to every other connection, copying the mute flag and the role onto the target's
connection along the way (`GameServer.receiveChangePlayerStats @5–@40 L1402–L1408`, `@134–@165 L1418–L1421`).
`canModifyPlayerStats(UdpConnection, IsoPlayer)` is the capability gate used on the `addXp` path
(`jar-perks-strength.md`). This path is about the *player record* — role, mute, warning points — not the
`CharacterStat` array, so it does not compete with the mod's writes; the client-side entry points are
`ISPlayerStatsUI.lua:575`, `:604`, `:612`, `:625`, `:632`, `:639`.

## E — the vanilla `Nutrition` sandbox option turned off

### E.1 The one branch, and everything downstream of it

`Nutrition.update` returns on the first instruction pair when `SandboxOptions.instance.nutrition` is
false (`Nutrition.update @0–@12 L65–L66`). Everything below is therefore what vanilla stops doing:

| what stops | side | cite | what still happens |
|---|---|---|---|
| the macro drain — carbohydrates `0.0035`, lipids `0.00113`, proteins `0.00086` per game-world second | server/SP (`GameClient.client` gate at `@42 L75`) | `Nutrition.update @48–@99 L76–L78` | the four stores keep filling from `Eat` and `DrinkFluid`, which have no sandbox guard ([#0067], [#0089/C/inference]) |
| `updateCalories()` | server/SP | `@102–@105 L79` | — |
| `updateWeight()` — and with it `setWeight`, the `updatedWeight` counter and `applyTraitFromWeight` | both sides reach it, the write arm is server/SP | `@106–@110 L81`; `updateWeight @317–@358 L198–L206` | the weight value persists in the save and on the wire; nothing moves it |
| the three weight-trend flags `isIncWeight`, `isIncWeightLot`, `isDecWeight` | — | they are cleared at `updateWeight @0–@12 L138–L140` and set in its branches | **they freeze at the last run's values**, and `ISCharacterScreen` draws the weight arrow from them — `client/XpSystem/ISUI/ISCharacterScreen.lua:119–128` — so a stuck "gaining weight" arrow is a visible artefact of switching the option off |
| the band-trait refresh | server/SP | `updateWeight @349 L202` | the five band traits keep whatever they held; **nothing in vanilla will refresh them again**, which is why the design has to own `applyTraitFromWeight` itself |

### E.2 What is **not** gated by the option and keeps running

| surface | what it does | cite |
|---|---|---|
| `Nutrition.canAddFitnessXp()` | `XP.AddXP` returns **early**, granting no Fitness XP at all, when the perk is Fitness and this returns false: false at Fitness level ≥ 9 with any weight trouble, and at level ≥ 6 when EMACIATED, OBESE or VERY_UNDERWEIGHT | `XP.AddXP @63–@106 L14196–L14198`; `Nutrition.canAddFitnessXp @0–@23 L275–L276`, `@24–@83 L277–L280`; `characterHaveWeightTrouble @0–@70 L271` (EMACIATED, OBESE, VERY_UNDERWEIGHT twice, OVERWEIGHT) |
| the protein → Strength XP multiplier | `XP.AddXP` multiplies a **Strength** gain by `1.5` when `50 < proteins < 300` and by `0.7` when `proteins < −300`, reading the vanilla protein store directly with no sandbox guard | `XP.AddXP @107–@190 L14203–L14208` |
| `Food.DoTooltip`'s nutrition block | shown when the viewer has `NUTRITIONIST` or `NUTRITIONIST2`; **no `SandboxOptions` reference in the method's outbound references** | `refs zombie/inventory/types/Food DoTooltip` → `CharacterTrait.NUTRITIONIST @1271`, `NUTRITIONIST2 @1282`, `'Tooltip_food_Nutrition'` `@1297`, `@1494`, `@1564` |
| `applyTraitFromWeight` itself | a plain public method on an exposed class; callable whether the option is on or off | `Nutrition.applyTraitFromWeight` (§ C.2) |
| the `Nutrition` save and wire carriers | `Nutrition.save`/`load` and the `syncParams == -1` arm of `SyncPlayerStatsPacket` carry the four stores and the weight regardless | `Nutrition.load @0–@41 L217–L222`; `SyncPlayerStatsPacket.parse @25–@42 L54` |
| `Thermoregulator`'s fatness term | reads `Nutrition.getWeight()` with no sandbox guard (sibling report) | `jar-endurance-fatigue-sleep.md` |
| a second gate **above** the option | `Nutrition.update` is not called at all when `SystemDisabler.doCharacterStats` is false | register row [#0068] |

Two consequences the design should carry. First, **turning the option off does not disconnect the vanilla
stores from vanilla gameplay**: the protein store keeps multiplying Strength XP and the band traits keep
gating Fitness XP, while the drain that used to bring the protein store back down is gone — so proteins
left high by an eat stay high, and the ×1.5 Strength-XP bonus becomes close to permanent unless the mod
drains the vanilla store itself. Second, the weight slot and the band traits become **entirely** the
mod's: nothing else moves them, which is what the design wants, and nothing else corrects them if the mod
stops writing.

Whether the option has other readers: the register's scan of 2026-09-10 found exactly two sites, the
option's constructor and `Nutrition.update` ([#0088/C/snapshot]). A byte grep for `nutrition` in this
session returns eight classes — `SandboxOptions`, `Nutrition`, `IsoGameCharacter`, `IsoPlayer`,
`Thermoregulator`, `Thermoregulator_tryouts`, `EvolvedRecipe`, `CharacterTraitScriptGenerator` — but the
plausible extra arms were checked and hold no `SandboxOptions` reference (`refs EvolvedRecipe.addItem`,
`refs EvolvedRecipe.useSpice`: none), consistent with the register: the other hits are the `nutrition`
field and `getNutrition()` call sites, not the option.

## F — absences, each a quoted grep

| the search | the result | what it proves |
|---|---|---|
| `./pz.sh grep OnTraitAdded`, `grep TraitAdded`, `grep OnAddTrait` | `no class contains that literal` (three times) | **no trait-change event exists.** `CharacterTraits.add` and `remove` are one-line forwards to `set` with no event, no dirty flag and no push (`add @0–@7 L82–L83`, `remove @0–@7 L86–L87`), so no mod can observe the nutrition mod's trait toggles reactively, and the mod cannot observe another mod's |
| `grep -rn "CalculateStats" --include=*.lua` over `media/lua` | 0 hits | no shipped Lua registers, reads or mentions the hook; a mod taking it is the only consumer in a vanilla install |
| `grep -rnE "Hook\.[A-Z][A-Za-z]*\.(Add\|Remove)" --include=*.lua` over `media/lua` | 4 hits: `AutoDrink` ×2, `ContextualAction`, `Attack` | vanilla uses three of the eight hooks and never `CalculateStats` |
| `./pz.sh grep trippingRotAngle` | `zombie/characters/Stats.class` only; `grep -rn "TrippingRotAngle" --include=*.lua` → 0 hits | the tripping rotation angle `updateTripping` advances has no consumer outside `Stats` on this build |
| `./pz.sh grep idleSquareTime` | `zombie/characters/IsoGameCharacter.class` only | the idle-square timer feeds nothing but boredom |
| `./pz.sh grep setMaxWeightDelta` and `grep maxWeightDelta` | `zombie/characters/IsoPlayer.class` only, both; `grep -rn "MaxWeightDelta" --include=*.lua` over `media/lua` → 0 hits | no vanilla Java caller and no vanilla Lua caller, so the mod's `setMaxWeightDelta` fights nothing in vanilla — but it **replaces** the value the `IsoPlayer` constructor derived from the STRONG/WEAK/FEEBLE/STOUT creation traits, which nothing else ever refreshes (`jar-perks-strength.md`, rows 29–30) |
| `methods zombie/Lua/Event` | three members — `trigger`, `<init>`, `register` | no getter for `Event.callbacks`, so the registrant list is unreadable from Lua |
| `methods zombie/network/packets/SyncPlayerStatsPacket` | `<init>`, `getBitMaskForStat`, `setData`, `parse`, `write` | no `processServer` and no `processClient` arm at all |
| `dump zombie/characters/IsoPlayer getMaxWeight` | `method not found` | `IsoPlayer` does not override carry capacity; the recompute is `BodyDamage.UpdateStrength` |
| `grep -rln "Hook.CalculateStats"` over the workshop corpus, `D:\SteamLibrary\steamapps\workshop\content\108600`, 182 mod folders, 2026-09-27 | 0 files | no mod installed on this machine claims the hook today — a dated reading, and the corpus drifts |
| `grep -rhoE "Hook\.[A-Z][A-Za-z]*\.(Add\|Remove)"` over the same corpus, same date | 12 hits, all `Hook.AutoDrink` (6 `Add`, 6 `Remove`) — nothing else | the only hook the installed mods touch is the one they inherited by copying `ISInventoryPaneContextMenu`; `CalculateStats`, `Attack`, `UseItem` and the three weapon hooks are unclaimed in this corpus |

## Behaving-nicely rules

1. **After every level clamp, fire the trait remap yourself.** `setPerkLevelDebug` writes `PerkInfo.level`
   and nothing else — no `LevelPerk` event, no XP touch, no push (`setPerkLevelDebug @0–@63 L4795–L4805`) —
   and the only vanilla listener of `LevelPerk` is what maps a Strength level to WEAK/FEEBLE/STOUT/STRONG
   (`XpUpdate.lua:207–223`). Re-run the same band logic in the mod (do **not** call `LevelPerk`, which would
   increment the level again) and keep vanilla's bands, including "level 5 gets no trait".
2. **Never write a level above the XP-implied level.** `xpUpdate.everyTenMinutes` → `checkForLosingLevel`
   is an absolute test and calls `LoseLevel` whenever `getXP(perk) < getTotalXpForLevel(level)`
   (`XpUpdate.lua:289–297`, `:299–334`). Compute the XP-implied level from
   `PerkFactory.getPerk(p):getTotalXpForLevel(n)` rather than tracking it, and clamp to it.
3. **Own the level for good once you have clamped it.** `XP.AddXP`'s level-up is a crossing test on
   `getTotalXpForLevel(getPerkLevel + 1)` (`@963–@1005 L14293–L14295`), so vanilla will never restore a
   level the mod lowered. The mod must write the level back up itself when its ceiling rises.
4. **Do not send `SyncXp` from anywhere, and expect the vanilla admin panel to break the clamp.**
   `XP.load` clears `perkList` and rebuilds the levels off the wire and calls `CharacterTraits.load` first
   (`@0 L14384`, `@99–@186 L14398–L14410`), `PlayerXpPacket.parse` has no side gate and `processServer`
   relays it (`parse @6–@38 L43–L46`, `processServer @3 L56`), and `ISPlayerStatsUI:onAddTrait` /
   `onRemoveTrait` call `SyncXp` (`:596`, `:671`). Re-assert the clamp and the trait set on a schedule,
   not once, so an admin trait edit self-heals.
5. **Do not push the perk level; the server already does.** `NetworkPlayerManager.update` calls `syncXp`
   on the 1000 ms stats limit and `NetworkPlayerAI.syncXp` sends `PlayerXp` to that player's own
   connection (`<clinit> @13–@23 L10`, `update @122–@141 L31–L33`, `syncXp @0–@52 L719–L722`). Budget one
   second of client-side staleness rather than a packet.
6. **Count `CalculateStats` registrants at boot behaviourally, because the list is unreadable.**
   `Hook.CalculateStats` is a Lua table with only `Add` and `Remove` (`Event.register @0–@42 L120–L125`) and
   `Event` declares no getter for `callbacks`. If the mod wants a second-registrant guard it must either
   wrap `Hook.CalculateStats.Add` before other mods load, or sample a vanilla-owned stat across one tick
   with nothing registered. State the limitation rather than claiming detection.
7. **Treat registration itself as the takeover, and the handler as unfailable.** `Event.trigger` returns
   true whenever the list is non-empty and swallows every callback error through `protectedCallVoid`
   (`@0–@11 L26–L27`, `@82 L36`, `@222 L49`, `@350 L64`). A handler that throws freezes hunger, thirst,
   fatigue, stress and boredom instead of reverting to vanilla, so wrap the handler body in its own
   guard, count failures, and have a failure mode that writes *something* sane.
8. **Reproduce, or knowingly drop and document, the seven updaters' six non-stat side effects:** the
   `lastEndurance` stamp (`updateEndurance @0 L10360`), the ANGER decay (`updateStress @249–@280 L10356`),
   `updateIdleSquareTime` and the in-combat `Stats.reset(IDLENESS)` (`updateStats_Awake @434–@456
   L10283–L10286`), the sleeping `timeOfSleep` advance (`IsoPlayer.updateStats_Sleeping @276 L3328`), the
   thirst ghost-mode gate (`updateThirst @38–@71 L10377`), and the FITNESS stat refresh
   (`updateFitness @0 L10312`). The tripping rotation angle can be dropped outright: nothing reads it (§ F).
9. **Keep writing the FITNESS `CharacterStat` if you skip `updateFitness`.** It is the perk level's mirror
   and is otherwise refreshed only on a Fitness XP gain (`XP.AddXP @1196–@1250 L14318–L14319`).
10. **Do not fight the per-tick fatigue reset; it is above the hook.** On a server with `SleepNeeded` off,
    `calculateStats` resets FATIGUE before `TriggerHook` (`@8–@48 L10200–L10201`), so sleep debt must live
    in the mod's own store — which § 4.4 already decided.
11. **Add the endurance event writers to the fast clock's budget or accept losing them.** A per-tick
    absolute endurance write erases the per-swing cost (`CombatManager.processWeaponEndurance @83–@107
    L1201–L1202`), the per-vault cost (`ClimbOverFenceState.enter @59–@70`) and the exercise-rep cost
    (`Fitness.reduceEndurance @0 L245`), all of which land between ticks.
12. **Push traits only when they changed, and only for the owner.** `sendSyncPlayerFields(player, 2)` is
    server-gated, targets that player's connection alone, and the receiver's `CharacterTraits.read` resets
    the whole list before re-adding (`GlobalObject.sendSyncPlayerFields @0–@8 L3910–L3911`;
    `INetworkPacket.send @0–@21 L261–L267`; `CharacterTraits.read @0 L115`; `reset @0–@54 L154–L157`). Every
    push destroys a client-only mod's locally added traits, so push on change, never on a timer.
    Vanilla already does this on any book read (`ISReadABook.lua:374` sends mask `0x07`, trait bit included).
13. **Set the ownership flag before adding a trait and check it before removing one**, because there is no
    trait-change event to coordinate with (§ F) and `applyTraitFromWeight` and `xpUpdate.levelPerk` both
    blanket-remove their whole band before adding (`applyTraitFromWeight @0–@62 L247–L251`;
    `XpUpdate.lua:209–212`, `:229–232`). The mod's own remove must be conditional where vanilla's is not.
14. **Call `applyTraitFromWeight` only when the weight band changed.** Vanilla calls it once per 2000
    `updateWeight` calls (`Nutrition.updateWeight @329–@355 L200–L203`); calling it every minute converts a
    rare blanket remove-then-add of five traits into a frequent one, which is what would break a band-trait
    mod that vanilla only grazes.
15. **Expect the night-vision grant to brighten the player's screen**, not only widen the cone:
    `RenderSettings$PlayerRenderSettings.updateRenderSettings` floors `ambient` at `0.20` for a
    NIGHT_VISION holder (`@411–@438 L199–L200`). Say so in the mod's description; it is the most visible
    thing the vitamin-A effect does.
16. **Expect the short-sight penalty to be silently cancelled by glasses** on the weapon-sight arm
    (`HandWeapon.getMaxSightRange @0–@22 L1560–L1561`), and to also move the blur and the zombie reveal
    rate (`IsoGameCharacter.updateVisionEffects @0 L16607`, `getAlphaUpdateRateMul @13 L6823`).
17. **Fold the creation-trait carry factor into `setMaxWeightDelta`.** The STRONG/WEAK/FEEBLE/STOUT factor
    reaches `maxWeightDelta` only in the `IsoPlayer` constructor and nothing refreshes it
    (`jar-perks-strength.md` rows 29–30), so a bare write silently removes a Strong character's carry bonus.
    The recompute reads the field on every `BodyDamage.UpdateStrength`, so the write survives but any other
    mod writing the same field is a last-writer-wins conflict worth naming in the mod's compatibility notes.
18. **Re-assert `Nutrition.weight` rather than trusting it, and never derive body composition from it.**
    `Commands.player.setWeight` lets **any** client set **any** player's weight on the server with no
    admin check (`server/ClientCommands.lua:599–604`, dispatcher `:1249–1258`), and a
    `SyncPlayerStatsPacket` with `syncParams == -1` replaces the whole `Nutrition` object including weight
    (`parse @25–@42 L54`; `Nutrition.load @0–@41 L217–L222`).
19. **Decide explicitly what to do with the vanilla protein store once the option is off.** `XP.AddXP`
    multiplies Strength XP by `1.5` while `50 < proteins < 300` with no sandbox guard
    (`@139–@190 L14204–L14208`), and the drain that used to bring the store down is exactly what the option
    switched off — so either drain it in the mod or accept a near-permanent Strength-XP bonus.
20. **Remember that the band traits gate vanilla Fitness XP.** `XP.AddXP` grants no Fitness XP at all when
    `canAddFitnessXp()` is false: at Fitness ≥ 9 with any weight trouble, at ≥ 6 when EMACIATED, OBESE or
    VERY_UNDERWEIGHT (`@63–@106 L14196–L14198`; `canAddFitnessXp @0–@85 L275–L280`). Writing a band trait is
    therefore a gameplay write, not a cosmetic one.
21. **Expect a frozen weight arrow on the character screen with the option off.** `isIncWeight`,
    `isIncWeightLot` and `isDecWeight` are only cleared and set inside `updateWeight`
    (`@0–@12 L138–L140`), which no longer runs; `ISCharacterScreen.lua:119–128` draws from them. Either set
    them from the mod each minute or accept a stale arrow.
22. **Do not rely on any push reaching other clients' copies of a character's traits.** The server's
    `syncXp` and `sendSyncPlayerFields` are both owner-only; the only path that reaches other clients is a
    client-originated `PlayerXp` relay (`processServer @3 L56`). A band trait the mod grants is invisible
    to other players' copies until they relog.

## Claims candidates

All grade **C**, bound **C-only**. Rows marked *(dup)* restate a candidate already proposed by
`jar-perks-strength.md` or `jar-endurance-fatigue-sleep.md` and should be minted once, not twice.

1. `setPerkLevelDebug` writes `PerkInfo.level` and nothing else: no XP write, no `getXP` read, no `LevelPerk` event, no dirty flag, and its only push arm is client-side `GameClient.sendPerks` — `jar:IsoGameCharacter.setPerkLevelDebug @0–@45 L4795–L4802`, `@46–@63 L4804–L4805`. *(dup, extended: the absence of the event and the XP touch is new)*
2. The `LevelPerk` event's only vanilla listener does four things — `checkAutoLearn`, the Strength band remap, the Fitness band remap and the Farming/Mechanics/Electricity recipe learning — so a level written without firing it leaves all four stale — `lua:media/lua/server/XpSystem/XpUpdate.lua:202–269`, registered `:395`.
3. Vanilla's level-up and level-down are both crossing tests on `getTotalXpForLevel`, so a level lowered by a mod is never restored and never corrected by the XP system — `jar:IsoGameCharacter$XP.AddXP @963–@1005 L14293–L14295`, `@1119–@1160 L14309–L14312`.
4. `xpUpdate.checkForLosingLevel` is an absolute test run on every online player every ten minutes and calls `LoseLevel` whenever the perk's XP is below the requirement for the stored level — `lua:media/lua/server/XpSystem/XpUpdate.lua:289–297`, `:299–334`, `:381`.
5. `XP.AddXP` re-writes `CharacterStat.FITNESS` from the Fitness perk level at the end of every Fitness XP gain, whether or not a level changed — `jar:IsoGameCharacter$XP.AddXP @1196–@1250 L14318–L14319`.
6. On a server, `NetworkPlayerManager.update` pushes `PlayerXp` to each player's own connection on the 1000 ms stats limit, alongside the stats snapshot — `jar:NetworkPlayerManager.<clinit> @13–@23 L10`, `update @122–@141 L31–L33`, `NetworkPlayerAI.syncXp @0–@52 L719–L722`.
7. `XP.load` is a full replace of both the perk-level list and the character-trait list: it calls `CharacterTraits.load` first, then clears `perkList` and rebuilds each `PerkInfo` from the wire — `jar:IsoGameCharacter$XP.load @0 L14384`, `@99–@109 L14398–L14399`, `@147–@186 L14407–L14410`.
8. The vanilla player-stats admin panel pushes a client's whole XP object, levels and traits included, to the server on every trait add or remove — `lua:media/lua/client/ISUI/PlayerStats/ISPlayerStatsUI.lua:596`, `:671`; `jar:PlayerXpPacket.parse @6–@38 L43–L46`.
9. `Hook.CalculateStats` is a Lua table with exactly two keys, `Add` and `Remove`, and `Event` declares no accessor for its callback list, so the number and identity of a hook's registrants are unreadable from Lua — `jar:Event.register @0–@42 L120–L125`, `jar:Event.<init> @4–@12 L23`, `jar:methods zombie/Lua/Event` (three members).
10. Vanilla Lua registers three of the engine's eight hooks — `AutoDrink`, `ContextualAction` and `Attack` — and no shipped Lua file mentions `CalculateStats` — `lua:media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:4056`, `:4060`, `client/TimedActions/ISContextualActions.lua:144`, `shared/TimedActions/ISReloadWeaponAction.lua:544`; `lua:grep CalculateStats over media/lua` (0 hits).
11. `updateTripping`'s only write is the tripping rotation angle, and nothing outside `Stats` reads it on this build — `jar:IsoGameCharacter.updateTripping @0–@20 L10316–L10319`, `jar:jar-wide grep trippingRotAngle` (`Stats.class` only), `lua:grep TrippingRotAngle over media/lua` (0 hits).
12. `updateStress` also decays `ANGER`, and `updateStats_Awake` also advances the idle-square timer and resets `IDLENESS` in combat — `jar:IsoGameCharacter.updateStress @249–@280 L10356–L10357`, `updateStats_Awake @434–@456 L10283–L10286`, `updateIdleSquareTime @0–@54 L17641–L17648`.
13. `IsoPlayer.updateStats_Sleeping`'s only non-stat write is the `timeOfSleep` advance; it contains no wake-up, no `setAsleep` and no bed release — `jar:IsoPlayer.updateStats_Sleeping @276 L3328`.
14. `IsoGameCharacter.updateFitness` does not drive the exercise system: the exercise system is the separate `Fitness` object — `jar:IsoGameCharacter.updateFitness @0–@25 L10312–L10313`, `jar:methods zombie/characters/BodyDamage/Fitness`.
15. `MORALE`'s literal is held by three classes only — `CharacterStat`, `IsoGameCharacter` and `Book` — so skipping `updateMorale` reaches no moodle, speed or combat term — `jar:jar-wide grep MORALE`.
16. `CharacterTrait.NIGHT_VISION` also raises the player's render ambient to a floor of `0.20` whenever the computed ambient is below it, independently of the view cone — `jar:RenderSettings$PlayerRenderSettings.updateRenderSettings @411–@438 L199–L200`.
17. No trait-change event exists: `CharacterTraits.add` and `remove` are one-line forwards to `set` with no event and no push — `jar:CharacterTraits.add @0–@7 L82–L83`, `remove @0–@7 L86–L87`, `jar:jar-wide grep OnTraitAdded, TraitAdded, OnAddTrait` (all absent).
18. `applyTraitFromWeight` removes exactly the five weight-band traits and adds one by band, with `75 ≤ weight < 85` getting none, and pushes nothing — `jar:Nutrition.applyTraitFromWeight @0–@62 L247–L251`, `@65–@215 L253–L266`.
19. Vanilla refreshes the weight-band traits only once per 2000 `updateWeight` calls, on the server side of the call — `jar:Nutrition.updateWeight @317–@320 L198`, `@329–@355 L200–L203`.
20. `sendSyncPlayerFields(player, n)` is server-gated, its `syncParams` is a six-bit mask, bit value 2 is the character-trait list, and the packet goes to that player's own connection alone — `jar:LuaManager$GlobalObject.sendSyncPlayerFields @0–@8 L3910–L3911`, `jar:GameServer.sendSyncPlayerFields @0–@32 L2459–L2462`, `jar:INetworkPacket.send @0–@21 L261–L267`, `jar:SyncPlayerFieldsPacket.write @16–@45 L143–L145`, `writeParam @127–@143 L61–L64`.
21. The trait bit's receiver replaces the whole trait list: `CharacterTraits.read` calls `reset`, which clears `knownTraits` and sets every map entry false, before re-adding each name off the wire — `jar:SyncPlayerFieldsPacket.parseParam @127–@143 L104–L107`, `jar:CharacterTraits.read @0 L115`, `@16–@31 L118–L119`, `jar:CharacterTraits.reset @0–@54 L154–L157`.
22. Vanilla already pushes the trait bit on a finished book read, as part of mask `0x07` — `lua:media/lua/shared/TimedActions/ISReadABook.lua:374`.
23. `SyncPlayerStatsPacket` declares no `processServer` and its `parse` has no side gate; the packet is server-only in practice because its sole send path, `INetworkPacket.send(IsoPlayer, …)`, is itself gated on `GameServer.server` — `jar:methods zombie/network/packets/SyncPlayerStatsPacket`, `jar:SyncPlayerStatsPacket.parse @0–@84 L50–L58`, `jar:LuaManager$GlobalObject.syncPlayerStats @0–@32 L9809–L9810`, `jar:INetworkPacket.send @0–@21 L261–L267`.
24. A `SyncPlayerStatsPacket` whose `syncParams` is −1 replaces the receiver's whole `Nutrition` object — calories, proteins, lipids, carbohydrates and weight — `jar:SyncPlayerStatsPacket.parse @17–@42 L53–L54`, `jar:Nutrition.load @0–@41 L217–L222`.
25. Endurance has three event writers outside the updaters: one per melee swing, one per vault and one per exercise repetition — `jar:CombatManager.processWeaponEndurance @49–@107 L1200–L1202`, `jar:ClimbOverFenceState.enter @59–@70`, `jar:Fitness.reduceEndurance @0–@54 L245–L254`.
26. `SleepingEvent.wakeUp` clears the asleep flag and removes fatigue on its good-bed branch — `jar:SleepingEvent.wakeUp @129–@131 L511`, `@175–@220 L526–L527`.
27. `Commands.player.setWeight` sets any player's vanilla weight from a client command with no admin or capability check anywhere in the dispatch path — `lua:media/lua/server/ClientCommands.lua:599–604`, `:1249–1258`.
28. `XP.AddXP` grants no Fitness XP at all when `canAddFitnessXp()` is false, which is decided by the weight-band traits: false at Fitness ≥ 9 with any weight trouble and at ≥ 6 when EMACIATED, OBESE or VERY_UNDERWEIGHT — `jar:IsoGameCharacter$XP.AddXP @63–@106 L14196–L14198`, `jar:Nutrition.canAddFitnessXp @0–@85 L275–L280`, `jar:Nutrition.characterHaveWeightTrouble @0–@70 L271`.
29. `XP.AddXP` multiplies a Strength gain by 1.5 while the vanilla protein store is between 50 and 300 and by 0.7 below −300, with no sandbox guard — `jar:IsoGameCharacter$XP.AddXP @107–@190 L14203–L14208`.
30. The three weight-trend flags the character screen's weight arrow reads are written only inside `updateWeight`, so they freeze when the nutrition option is off — `jar:Nutrition.updateWeight @0–@12 L138–L140`, `lua:media/lua/client/XpSystem/ISUI/ISCharacterScreen.lua:119–128`.
31. The vanilla food tooltip's nutrition block is gated on the Nutritionist traits and not on the nutrition sandbox option — `jar:refs zombie/inventory/types/Food DoTooltip` (`CharacterTrait.NUTRITIONIST @1271`, `NUTRITIONIST2 @1282`, `'Tooltip_food_Nutrition' @1297`, no `SandboxOptions` reference).
32. `setMaxWeightDelta` and the `maxWeightDelta` field are confined to `IsoPlayer` and are called by no vanilla Lua file — `jar:jar-wide grep setMaxWeightDelta`, `grep maxWeightDelta` (`IsoPlayer.class` only), `lua:grep MaxWeightDelta over media/lua` (0 hits). *(dup of `jar-perks-strength.md` row 29, with the Lua absence added)*
33. `ISCharacterScreen` rebuilds its trait icon row every frame from `getKnownTraits()` whenever the list differs, so a server-side trait toggle appears without a UI refresh — `lua:media/lua/client/XpSystem/ISUI/ISCharacterScreen.lua:74–75`, `:586–598`.
34. `ISCharacterScreen` and `ISPlayerStatsUI` each assign the Strength and Fitness levels to a field they never read — `lua:media/lua/client/XpSystem/ISUI/ISCharacterScreen.lua:614–615`, `client/ISUI/PlayerStats/ISPlayerStatsUI.lua:704–705`.
35. No mod in the 182-folder workshop corpus on this machine registers `Hook.CalculateStats`, and the only hook any of them touches is `AutoDrink` — `corpus:D:\SteamLibrary\steamapps\workshop\content\108600, grep Hook.CalculateStats (0 files) and grep "Hook\.[A-Z][A-Za-z]*\.(Add|Remove)" (12 hits, all AutoDrink), 2026-09-27`. Bound: dated, the corpus drifts.

Already in the register, cited above rather than re-minted: [#0006] (the `Eat` write order and its sends),
[#0067] and [#0089] (what the nutrition option gates and what keeps filling), [#0068] (the
`SystemDisabler` gate above it), [#0088] (the option's two reader sites), [#0669] and [#0670]
(`DrinkFluid`'s unclamped fraction, `ISDrinkFromBottle` as dead code).

## Not read

- **Which method reads the `FITNESS` `CharacterStat`.** The literal is held by `Thermoregulator`,
  `FitnessState`, `Fitness`, `IsoGameCharacter$XP` and `IsoGameCharacter`; `refs` on
  `Thermoregulator.updateMetabolicRate` and `updateBodyMultipliers` found only `ENDURANCE`, so the
  consumer was not narrowed. Until it is, "the FITNESS stat goes stale under takeover" is a statement
  about the write and not about a consequence.
- **What reads `ANGER` and `MORALE`.** `ANGER`'s literal sits in `Moodle`, `Stats`, `IsoPlayer` and
  `IsoGameCharacter` and `MORALE`'s in `Book`; neither was narrowed to a method, so the cost of dropping
  the anger decay and the morale trickle is unpriced.
- **Where `SHORT_SIGHTED` and `THIRST` are read inside `ISWorldObjectContextMenuLogic`.** Only the
  `FATIGUE` read in `createMenuEntries` was located; the `THIRST` site was not, so "menus read and never
  write these stats" rests on one of the two.
- **The `IsoGameCharacter` site that holds `sendSyncPlayerFields`.** `refs` on `learnRecipe` and
  `setAlreadyReadBook` found nothing, so which base-class path pushes player fields is unread.
- **`Fitness.update`'s caller.** `BodyDamage.Update`'s outbound references name `Thermoregulator.update`
  and not `Fitness.update`, so where the exercise system is driven from was not established — it matters
  only for the claim that a takeover does not touch it, which rests on `updateFitness`'s body instead.
- **Everything about a live session.** Whether the `Hook` table exists in a dedicated server's Lua
  environment at all, whether a server-written level survives the next second's `PlayerXp` push in
  practice, whether a `sendSyncPlayerFields(player, 2)` push actually lands, how often `BodyDamage.Update`
  and therefore `Nutrition.update` run on a real server tick, and whether `Commands.player.setWeight` is
  reachable from an unprivileged client in fact rather than in the code — each is a harness question.
- **The workshop reading is one machine on one date.** 182 mod folders on 2026-09-27; a mod that claims
  the hook may exist elsewhere on the Workshop and is not excluded by this scan.
- **The `Event` and `LuaHookManager` exposure verdicts.** Neither class was tested against the exposer's
  class set, so "a mod could wrap `Hook.CalculateStats.Add`" rests on the table being a plain Lua table,
  not on any Java member being reachable.
- **`Nutrition.updateWeight`'s middle.** Only its head (the trait factors and the calorie thresholds) and
  its tail (the `setWeight`, the counter and the trait call) were read; the gain and loss arms between
  `@186` and `@311` were not, so no claim here describes vanilla's weight rate.
