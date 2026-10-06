# Effects engine seats — the jar desk reads for Plan 5

Reader: claude-opus-5-5 · 2026-10-06 · build 42.20.4 (jar b0bbce05d5) · read-only: every reading below is a `pz.sh dump`, `refs`, `methods` or `grep` of the installed jar, or a read of the installed `media/lua`; nothing was booted. Access flags were read with a session-scoped scratch parser over the toolchain's constant-pool module, and caller sets with a session-scoped scratch scanner that walks every method body of a named class through the toolchain's own `refs` (the toolchain has no reverse-caller index).

Each section gives the decompiled excerpt it rests on, with `@offset` and `L<line>`, the verdict, and the Plan 5 consequence. **Inference** marks every sentence that is not read straight off an instruction. The provisional tags `[T1.n]` are the claims delta `task-1-claims-delta.tsv` beside this plan's ledger.

## 1. The four `BodyDamage` sub-updaters: overwrite or increment?

The question (formulas briefing § L item 11; #2384 listed the bodies as unread): does each updater set its stat from scratch every update, which would erase a floor a `CalculateStats` handler writes after `BodyDamage.Update`, or does it add to and remove from the stored value?

**Verdict: none overwrites.** Each adds or removes an amount from the stored value, or calls `Stats.reset` (back to the stat's default) on a named condition. A value written after `BodyDamage.Update` in one update is the base the next update's change starts from (inference from the four bodies; not exercised live) [#3017/C/inference].

### 1.1 `UpdatePanicState` and its two helpers [#3013/C/C-only] [#3014/C/C-only]

```text
BodyDamage.UpdatePanicState()V
  @0    L458  n   = stats.numVisibleZombies
  @8    L459  old = getOldNumZombiesVisible();  @13 L462 setOldNumZombiesVisible(n)
  @18   L464  d   = n - old
  @22   L467  if hasTrait(DESENSITIZED): @35 L468 stats.reset(PANIC); return
  @47   L473  k = 0;  @50 L474 if d > 0: k += d
  @60   L479  if k > 0: @65 L480 IncreasePanic(k)  else: @74 L482 ReducePanic()
  @78   L484  return

BodyDamage.IncreasePanic(I)V
  @0    L391  in a vehicle: k = k / 2
  @14   L395  f = 1;  beta effect > 0: f = clamp(1 - betaDelta, 0, 1)        (@16-@52 L396-L402)
  @54   L406  COWARDLY f *= 2;  @71 L409 BRAVE f *= 0.3;  @90 L412 DESENSITIZED f *= 0.15
  @109  L416  stats.add(PANIC, getPanicIncreaseValue() * k * f)
  @129  L419  DESENSITIZED: stats.reset(PANIC)
BodyDamage.ReducePanic()V
  @0    L425  PANIC at minimum: return
  @14   L429  r = getPanicReductionValue() * GameTime.getThirtyFPSMultiplier()          (so r = value * (thirtyFPS + m) below)
  @26   L431  m = min(5, floor(hoursSurvived / 24 / 30));  @52 L436 r += getPanicReductionValue() * m
  @62   L439  asleep: r *= 2
  @76   L443  stats.remove(PANIC, r)
BodyDamage.<init>  @151 L92 panicIncreaseValue = 7.0;  @163 L94 panicReductionValue = 0.06
```

PANIC is raised by 7 per newly visible zombie (trait-scaled) and otherwise decays by 0.06 × (the thirty-FPS multiplier + the whole months survived, at most 5), doubled asleep. Desensitized resets it. Note the decay uses `getThirtyFPSMultiplier`, not `getMultiplier`, so it is a per-frame rate and not a game-time rate (read; its game-hour size is not derived here).

### 1.2 `UpdateBoredom` — boredom and unhappiness [#3015/C/C-only] [#3016/C/C-only]

```text
BodyDamage.UpdateBoredom()V
  @0    L1983 IsoSurvivor: return;  @11 L1987 an asleep IsoPlayer: return
  @32   L1992 in a room or idle-square time >= 1800:
  @59   L1993   currently idle: add(BOREDOM, boredomIncreaseRate * IDLENESS * mult)       (@69-@103 L1994)
                else:           add(BOREDOM, boredomIncreaseRate / 10 * IDLENESS * mult)  (@107-@145 L1996)
  @146  L2000   speaking and not calling out: remove(BOREDOM, boredomDecreaseRate * mult)
  @189  L2003   survivors near: remove(BOREDOM, boredomDecreaseRate * 0.1 * mult)
  @226  L2008   busy and IDLENESS < 0.1: remove(BOREDOM, boredomDecreaseRate * 0.5 * mult)
  @283  L2011 else (outdoors, not idle long): in a vehicle stopped: add (reading: rate/5, else rate) * mult;
                moving: remove 0.5 * rate * mult;  on foot @411 L2026: remove 0.1 * decreaseRate * mult
  @438  L2030 INTOXICATION > 20: remove(BOREDOM, boredomDecreaseRate * 2 * mult)
  @482  L2035 PANIC > 5: @499 L2036 stats.reset(BOREDOM)
  @510  L2040 BORED moodle level > 1 and not reading:
  @537  L2041   add(UNHAPPINESS, unhappinessIncrease * BORED level * mult)
  @576  L2044 STRESS moodle level > 1 and not reading:
  @603  L2045   add(UNHAPPINESS, unhappinessIncrease / 2.0 * STRESS level * mult)
  @646  L2047 SMOKER: timeSinceLastSmoke += 1e-4 * mult; above 1, add(NICOTINE_WITHDRAWAL, ...)   (@646-@755 L2047-L2054)
  @756  L2057 return
```

`UnhappinessIncrease = 0.0005` (`media/lua/shared/defines.lua:25`). The unhappiness terms need the BORED or STRESS moodle at level 2 or more (the branch skips at level ≤ 1). The platform briefing's "× 2 × STRESS moodle level" is a mis-reading: the stress term is `unhappinessIncrease / 2 × level` (`@613 ldc2_w 2.0; ddiv`).

### 1.3 Who else lowers UNHAPPINESS [#3033/C/inference]

A scan of every method body of `BodyDamage`, `IsoGameCharacter`, `IsoPlayer` and `Stats` for `CharacterStat.UNHAPPINESS` finds eight sites: the two adds above, the eat (`JustAteFood @425`), reading (`JustReadSomething @19`), a drink (`DrinkFluid @242`), petting an animal (`IsoPlayer.petAnimal @64, @146`) and one decay:

```text
IsoGameCharacter.updateInternal()V
  @902  L9142 depressFirstTakeTime > 0 or depressEffect > 0:
  @920  L9143   depressFirstTakeTime -= thirtyFPSMultiplier;  when it goes below 0:
  @950  L9146   depressEffect -= thirtyFPSMultiplier
  @965  L9147   stats.remove(UNHAPPINESS, 0.03 * thirtyFPSMultiplier)
```

So the only passive fall of UNHAPPINESS in those four classes is the antidepressant's, while its effect lasts (read; the scan is of four classes, not jar-wide, so a decay elsewhere is not excluded). **Inference:** a mod's unhappiness floor does not sit on top of a standing vanilla decay; once the mod's target falls, the stat stays where the floor left it unless the mod lowers it or a vanilla event (eating, reading, pills) does. Ruling 9's "vanilla's own decay runs underneath" holds for stress and panic and not for unhappiness.

### 1.4 `UpdateIllness` — food sickness [#3018/C/C-only]

```text
BodyDamage.UpdateIllness()V
  @0    L2564 SandboxOptions.decayingCorpseHealthImpact != 1:
  @13   L2565   s = GetBaseCorpseSickness();  @18 L2566 s > 0:
  @24   L2567     d = getCorpseSicknessDefense(s, true);  d > 0: s *= max(0, 1 - d/100)   (@34-@54 L2568-L2570)
  @55   L2573     RESILIENT s *= 0.75;  @77 L2575 PRONE_TO_ILLNESS s *= 1.25
  @96   L2578     s > 0: @102 L2579 add(FOOD_SICKNESS, s * mult); @121 L2580 setCorpseSicknessRate(s); @129 L2581 return
  @130  L2586 setCorpseSicknessRate(0)
  @138  L2587 POISON at minimum and FOOD_SICKNESS above minimum:
  @164  L2588   remove(FOOD_SICKNESS, ZomboidGlobals.foodSicknessDecrease * mult)
  @186  L2590 return
```

`FoodSicknessDecrease = 0.0015` (`defines.lua:44`). Food sickness decays only while POISON is at its minimum, and not at all while corpse sickness is being added.

### 1.5 The SICKNESS stat [#3019/C/inference] [#3025/C/arith.]

`UpdateIllness` never touches `CharacterStat.SICKNESS`. A scan of every method body of `BodyDamage`, `IsoGameCharacter`, `IsoPlayer`, `Thermoregulator`, `Stats`, `Moodle` and `ItemStatsPacket` for `CharacterStat.SICKNESS` finds three sites, all reads: `Thermoregulator.updateSetPoint @10, @30` and `Moodle.Update @737`. (`RecipeCodeOnEat` also names `CharacterStat` and was not scanned.) **Inference:** nothing in those classes decays or overwrites SICKNESS, so a written SICKNESS stays until something writes it again. The set-point consequence is § 3.

## 2. `UpdateCold` and `catchACold` [#3021/C/C-only] [#3022/C/C-only] [#3023/C/C-only]

The jar-wide grep for `CatchACold` hits `ZomboidGlobals`, `BodyDamage`, `Thermoregulator` and `Thermoregulator_tryouts`. Within `BodyDamage`, `setCatchACold` is called by `UpdateWetness` (accrual and decay), `UpdateCold @270` (the cure), `RestoreToFullHealth @89` and `loadMainFields @5`; `saveMainFields @2` writes `getCatchACold()`. The field itself is read and written only by its getter and setter.

```text
BodyDamage.UpdateWetness()V   (the catch-a-cold tail)
  @580  L851  c = 0;  @583 L852 thermoregulator != null: c = thermoregulator.getCatchAColdDelta()
  @599  L856  no cold yet and c > 0.1:
  @615  L859    PRONE_TO_ILLNESS c *= 1.7;  @636 L863 RESILIENT c *= 0.45;  @657 L866 OUTDOORSMAN c *= 0.25
  @678  L870    setCatchACold(getCatchACold() + catchAColdIncreaseRate * c * mult)
  @701  L872    getCatchACold() >= 100: @711 L873 setCatchACold(0); @716 L874 setHasACold(true);
                                        @721 L875 setColdStrength(20); @728 L876 setTimeToSneezeOrCough(0)
  @733  L881  c <= 0.1: @742 L882 setCatchACold(getCatchACold() - catchAColdDecreaseRate)   (no multiplier)
  @755  L883    below 0: @764 L884 setCatchACold(0)
```

`CatchAColdIncreaseRate = 0.003`, `CatchAColdDecreaseRate = 0.175` (`defines.lua:39-40`). The fall below the 0.1 delta is per update with no game-time multiplier (read; its game-time size therefore depends on the frame rate — inference).

```text
BodyDamage.UpdateCold()V
  @0    L976  hasACold:
  @7    L984    recovering = true
  @9    L987    not (square in a room, WET moodle 0, HYPOTHERMIA level < 1, FATIGUE <= 0.5,
                     HUNGER <= 0.25, THIRST <= 0.25):  @111 L996 recovering = false
  @113  L999    coldReduction > 0: recovering = true; coldReduction -= 0.005 * mult, floored at 0   (@122-@154 L1000-L1003)
  @157  L1008   recovering:
  @161  L1009     f = 1;  PRONE_TO_ILLNESS f = 0.5;  RESILIENT f = 1.5
  @196  L1018     coldStrength -= coldProgressionRate * f * mult;  coldReduction > 0: again   (@219-@246 L1019-L1020)
  @249  L1023     coldStrength < 0: @258 L1024 coldStrength = 0; @263 L1025 setHasACold(false); @268 L1026 setCatchACold(0)
  @276  L1031   else: f = 1; PRONE 1.2; RESILIENT 0.8; coldStrength += rate * f * mult, capped 100   (@276-@347 L1031-L1043)
  @350  L1048   sneeze and cough timers (@350-@438 L1048-L1062)
  @441        no cold and SMOKER: the smoker's sneeze timer (@441-@552 L1068-L1083)
```

**Verdict:** `UpdateCold` runs the course of a cold that has already started and touches `catchACold` only to zero it at the cure. `catchACold` accumulates in `UpdateWetness` from the thermoregulator's catch-a-cold delta, and it is reset by nothing per tick: it falls by 0.175 per update while the delta is at or below 0.1, is zeroed when it reaches 100 (and the cold starts) or when a cold is cured, and rides `saveMainFields`. Vanilla already ties the cold's course to nutrition-adjacent state: a cold recovers only while FATIGUE ≤ 0.5, HUNGER ≤ 0.25 and THIRST ≤ 0.25 (with the room, wet and hypothermia tests), and otherwise strengthens.

**Plan 5 consequence (inference):** the cold fold (ruling 17) reads the rise of `getCatchACold()` since its last write and scales it by `coldMul`; a fall (the 0.175 decay) and the zeroing at 100 must pass through unscaled, or the fold would mistake the onset reset for a negative delta. The fold scales incidence only; the HUNGER and THIRST views already move the course through vanilla's own gate, so the mod's views cross the 0.25 hunger and thirst edges in this updater too.

## 3. `Thermoregulator.getSetPoint` [#3024/C/C-only] [#3025/C/arith.]

`getSetPoint()F` is public on the public final `Thermoregulator`, a class in the exposer's set (#2248); the field `setPoint` is private and has no setter.

```text
Thermoregulator.getSetPoint()F        @0 L412 return this.setPoint
Thermoregulator.update()V             @40 L737 updateSetPoint()  (first step after the air temperatures; then
                                      @44 L739 updateCoreRateOfChange ... @60 L747 updateHeatDeltas ...)
Thermoregulator.updateSetPoint()V
  @0    L759  setPoint = 37.0
  @6    L762  SICKNESS above minimum: @19 L763-L764 setPoint += SICKNESS * 2.0
Thermoregulator.updateHeatDeltas()V
  @16   L967  coreHeatDelta < 0 and core > setPoint: coreHeatDelta *= 1 + (core - setPoint) / 2    (@25-@62 L968-L970)
  @68   L973  coreHeatDelta >= 0 and core < setPoint: coreHeatDelta *= 1 + (setPoint - core) / 4   (@68-@107 L973-L974)
  @217  L987  bodyHeatDelta = 0; core above or below setPoint: bodyHeatDelta = core - setPoint       (@222-@284 L988-L991)
```

`setPoint` is written only in the constructor, `load`, `reset`, `initNodes` and `updateSetPoint`.

**Verdict:** the set point is the core temperature the regulator steers toward — 37 °C, raised by 2 °C per unit of SICKNESS (a fever) — recomputed at the start of every thermoregulator update, and a mod can read it (`getBodyDamage():getThermoregulator():getSetPoint()`, on the server, where the thermoregulator runs, #2934) but not write it.

**Plan 5 consequences (inference):**
- Ruling 16's absolute target `setPoint + tempOffset` reads a public getter on an exposed class; the target moves with the mod's own SICKNESS writes.
- Ruling 12's SICKNESS targets are fevers: 0.30, 0.55 and 0.90 raise the set point to 37.6, 38.1 and 38.8 °C (arithmetic on the two constants), and nothing in the scanned classes decays SICKNESS (§ 1.5), so a toxicity rung heats the character for as long as the mod holds it — on top of the SICK moodle the rung is meant to show. Whether the core actually reaches the raised set point is unmeasured (the regulator's own gains are not derived here).

## 4. The four regeneration constants across a save [#3020/C/inference]

The jar-wide grep for `HealthAddition` hits `BodyDamage` alone, and the four fields `standardHealthAddition`, `reducedHealthAddition`, `severlyReducedHealthAddition` and `sleepingHealthAddition` are private. None of `BodyDamage.save`, `load`, `saveMainFields` or `loadMainFields` (dumped whole, 312, 292, 67 and 61 lines) names any of the four fields or their accessors (the same four bodies were read for the drunk fields by #2920, and still name neither).

**Verdict (inference):** the four constants are not saved with the character, so values a mod sets are lost at a reload and the constructor's defaults return. **Plan 5 consequence:** re-assert the four setters after load and on every rebuild, as ruling 17 already says. `drunkReductionValue` is the same case and is already settled (#2920); nothing new was minted for it.

## 5. The wake-up [#3029/C/C-only] [#3030/C/C-only]

The restoration code carries no wake-up (#2227). The wake-ups that exist:

```text
IsoGameCharacter.updateInternal()V
  @1558 L9233 asleep and an IsoPlayer and not an IsoAnimal:  @1583 L9234 IsoPlayer.processWakingUp()
              (after @1554 L9230 calculateStats)
IsoPlayer.processWakingUp()V
  @0    L3366 forceWakeUpTime == 0: forceWakeUpTime = 9.0
  @16   L3370 wake = the time of day has passed forceWakeUpTime since the last update   (@16-@83 L3370-L3380)
  @84   L3381 getAsleepTime() > 16: wake = true
  @97   L3385 GameClient.client or numPlayers > 1: wake = wake or pressedAim or pressedMovement   (@110-@134 L3386)
  @135  L3389 forceWakeUp: wake = true
  @144  L3393 asleep and wake: forceWakeUp = false; SleepingEvent.wakeUp(this); forceWakeUpTime = -1;
              a client sends the player   (@155-@194 L3394-L3400)
SleepingEvent.update(IsoPlayer)V
  @10   L300  very-close zombies: PANIC += 70, STRESS += 0.5, wakeUp     (@20-@97 L301-L306)
  @100  L308  the nightmare hour: the same, wakeUp                        (@100-@189 L308-L314)
  @192  L316  the intruder hour with zombie intruders: spawn them, wakeUp  (@192-@265 L316-L321)
```

`forceAwake` is called by `ReduceGeneralHealth` (health ≤ 10, #2346), `IsoPlayer.updateTemperatureCheck`, `IsoGameCharacter.FireCheck`, `AttackState.triggerPlayerReaction`, `AttackVehicleState.animEvent`, `Bite.process`, `IsoPlayer.OnDeath` and the building alarm through barricade, door and window thumps (jar-wide grep `forceAwake`, each caller scanned).

The sleep's length is set from FATIGUE once, at its start, in the client Lua: `ISWorldObjectContextMenu.onSleepWalkToComplete` sets `forceWakeUpTime` to the time of day plus `ZombRand(10 × FATIGUE, 13 × FATIGUE) + 1` hours, one less in a good bed and one more in a bad one, × 0.7 on a floor, × 0.5 Insomniac, × 0.75 Needs Less Sleep, × 1.18 Needs More Sleep, clamped to 3–16 (`ISWorldObjectContextMenu.lua:1077-1106`); the sleep dialog sets it from the hours the player picks (`ISSleepDialog.lua:63-73`).

**Verdict:** no fatigue value wakes a sleeper. The wake is a clock time chosen at sleep onset (from FATIGUE then, or by the player), 16 hours asleep, input in multiplayer, or an event (zombies, nightmare, intruders, damage at ≤ 10 health, temperature, fire). **Plan 5 consequence (inference):** the FATIGUE writer lowering F during sleep neither wakes the player earlier nor keeps them asleep longer; the mod's S at the moment the player lies down sets the sleep's length through the vanilla Lua, and a player whose S is rested by the morning keeps sleeping until the alarm. Which side runs `processWakingUp` for a connected player is not read (the call site has no side gate of its own; `updateInternal`'s caller per side was not traced).

## 6. `RenderSettings` and Lua [#3027/C/C-only]

`zombie.core.opengl.RenderSettings` and `RenderSettings$PlayerRenderSettings` are not in `LuaManager$Exposer.exposeAll()`'s `setExposed` class list (the dump read end to end, 3055 lines), and the jar-wide grep for `RenderSettings` hits twenty classes, none of them `LuaManager`, `LuaManager$Exposer` or `LuaManager$GlobalObject`, so no global function names it. The installed `media/lua` names it nowhere (grep 2026-10-06). `RenderSettings.getInstance()` is public static, but unreachable.

**Verdict:** the night-vision ambient floor (#2339) cannot be read or set from Lua; a mod sees the trait, not its render effect. A probe of it would be a client screenshot or a pixel read, not a Lua read.

## 7. The attack events [#3026/C/C-only] [#3031/C/C-only]

```text
LuaEventManager.AddEvents()V
  @294  L648  AddEvent("OnWeaponHitCharacter")   @301 L649 AddEvent("OnWeaponSwing")
  @322  L652  AddEvent("OnWeaponSwingHitPoint")  @329 L653 AddEvent("OnPlayerAttackFinished")
SwipeStatePlayer.enter(IsoGameCharacter)V
  @30   L174  not GameServer.server: SetCurrentGameSpeed(1)
  @65   L181  CombatManager.calculateAttackVars(player)
  @72   L182  doAttack(player, 2.0, player.getClickSound(), player.getAttackVars())
  @86   L183  weapon = player.getUseHandWeapon()     (local 3; not reassigned on any path from @90 to @285)
  @281  L212  triggerEvent("OnWeaponSwing", player, weapon)    then @289 L213 TriggerHook("WeaponSwing", player, weapon)
  @333  L223  (after the trigger) local 3 = player.getAttackVars().getWeapon(player)
SwipeStatePlayer.doAttack(IsoPlayer, F, String, AttackVars)V
  @54   L148  the primary item (or bare hands) is a HandWeapon:
  @177  L160    setRecoilDelay(attackVars.recoilDelay)
  @187  L161    CombatManager.setAimingDelay(player, weapon)            (#2326's post-shot write)
  @196  L163  return
SwipeStatePlayer.exit(IsoGameCharacter)V
  @322  L496  attacked = get(ATTACKED)
  @243  L484  weapon = CombatManager.getWeapon(character)
  @396  L508  attacked: @400 L509 triggerEvent("OnPlayerAttackFinished", character, weapon)
```

Every branch between `@90` and `@285` (the `@92`, `@99`, `@127`, `@134`, `@152`, `@170`, `@183`, `@190` and `@216` targets) lands at or before `@251` without storing local 3, so the event's second argument is the `getUseHandWeapon()` value of `@86 L183`.

**Verdict:** both candidate events exist on this build. `OnWeaponSwing(player, weapon)` fires in the swing state's `enter`, after `doAttack` has already made the post-shot aiming-delay write; `OnPlayerAttackFinished(character, weapon)` fires in its `exit` when the attack landed (the `ATTACKED` flag). Vanilla's own reload code listens to `OnWeaponSwingHitPoint` and `OnPlayerAttackFinished` (`ISReloadWeaponAction.lua:542-543`). `enter` carries a server branch, so the state is written to run on a server too; which side fires either event for a connected player's shot is not read.

**Plan 5 consequence (inference):** a client `OnWeaponSwing` handler runs after the post-shot write in the same `enter`, so an additive bump there is the later write of that shot; `OnPlayerAttackFinished` is the later seat, at the end of the swing. Whether the per-update aiming step (`IsoGameCharacter.updateAimingDelay`, platform briefing § 5.1) or `resetAimingDelay` erases the bump before the next shot is the live question (gate 2's X86).

## 8. The landing side [#3028/C/C-only] [#3032/C/C-only]

The jar-wide grep for `DoLand` hits two classes; the callers are `IsoGameCharacter.updateFalling @167` and `PlayerFallingState.processOnExit @14`.

```text
IsoGameCharacter.updateInternal()V   @531 updateFalling()
IsoGameCharacter.updateFalling()V
  @21   L9624 not shouldBeFalling: reset fall time and speed; return
  @49   L9633 dt = GameTime.getTimeDelta();  @56 L9635 GameServer.server: dt *= 0.16
  @121  L9651 the next z is below the floor: @129 L9652 setZ(floor); ...; @164 L9660 DoLand(speed)
PlayerFallingState.<init>   @0 L23 State(true, true, true, false)   (sync on enter, on exit, on square)
PlayerFallingState.exit     @33 L58 set(LANDING_IMPACT, getImpactIsoSpeed());  @47 L59 clearFallDamage()   (no DoLand)
PlayerFallingState.isProcessedOnExit   @0 L74 return true     (State's default @0 L209 returns false)
PlayerFallingState.processOnExit(character, params)
  @0    L79   character.DoLand(LANDING_IMPACT from params)
  @17   L80   character.getNetworkCharacterAI().syncDamage()
StatePacket.processServer
  @0    L138  stage == Exit:  @10 L139 state.isProcessedOnExit():  @23 L140 state.processOnExit(character, params.delegate)
```

**Verdict (read):** on a dedicated server, an exit-stage state packet for the falling state runs `DoLand` on the server's copy of the character with the landing impact the client put in the packet, then pushes the damage; no other state answers `isProcessedOnExit` for a fall. `updateFalling` also calls `DoLand` with no side gate of its own (it scales its time step on a server), reached from `updateInternal`.

**Unmeasured:** whether the server's `updateInternal` runs `updateFalling` for a connected player (so that a fall could land twice), and whether the owning client's own `updateFalling` lands it locally as well. **Plan 5 consequence (inference):** a mod listening to `OnPlayerGetDamage` with the `FALLDOWN` tag on the server sees the packet-driven landing; the fracture-risk seat (if ruled in) belongs on the server's `processOnExit` path, and gate 2's landing probe settles which side fires.

## 9. Summary of verdicts

| read | verdict | tags |
|---|---|---|
| `UpdatePanicState` | increments (`IncreasePanic` add) or decays (`ReducePanic` remove); Desensitized resets | #3013, #3014 |
| `UpdateBoredom` | boredom up and down by context, reset at PANIC > 5; UNHAPPINESS only rises (BORED or STRESS level ≥ 2) | #3015, #3016 |
| UNHAPPINESS decay | only the antidepressant term in four classes; no passive decay | #3033 |
| `UpdateIllness` | FOOD_SICKNESS: corpse add, else decay 0.0015 × mult only while POISON is at minimum; never SICKNESS | #3018 |
| SICKNESS | read only (set point, SICK moodle) in seven classes; nothing decays it there | #3019 |
| `catchACold` | accrues in `UpdateWetness` from the thermoregulator delta; −0.175 per update below the 0.1 delta; zeroed at 100 and at the cure; saved | #3021, #3022, #3023 |
| `getSetPoint` | public, exposed, read-only; 37 + 2 × SICKNESS, recomputed each update; the regulator's target | #3024, #3025 |
| regen constants save | not saved (inference from four save/load bodies and a jar-wide grep) | #3020 |
| wake-up | no fatigue value wakes; FATIGUE sizes the sleep at onset in client Lua | #3029, #3030 |
| `RenderSettings` | not exposed to Lua | #3027 |
| attack events | `OnWeaponSwing(player, weapon)` after the post-shot write; `OnPlayerAttackFinished(character, weapon)` at the swing's end | #3026, #3031 |
| landing | server runs `DoLand` from the client's exit packet; `updateFalling` also calls it; per-side behaviour unmeasured | #3028, #3032 |
