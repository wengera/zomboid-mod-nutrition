# Perception and speed — the view cones, hearing, movement and combat speed
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: the rendered and the server view cones, night vision, hearing range, movement speed and its server-side formula, combat speed, melee and aiming delay, and which perception traits the engine reads; the packets that carry the speeds and the trait list are `facts/wire-packets.md`'s, their senders and cadences `platform/mp-model.md`'s, and the endurance stat behind the Endurance moodle `facts/endurance-fatigue-sleep.md`'s.

## Key facts

- The rendered view cone starts at 144 degrees and loses 72 degrees per unit of the fatigue stat, capped at 144 [#2292/C/C-only].
- A fatigue stat at its maximum costs a further 36 degrees of cone [#2293/C/C-only].
- A Panic moodle at level 4 exactly costs 36 degrees of cone [#2295/C/C-only].
- The Night Vision trait adds 36 times (1 minus daylight strength) degrees to the cone, so it is worth the most at night [#2298/C/C-only].
- The Eagle Eyed trait adds 36 times daylight strength to the cone, so it is worth nothing at night [#2297/C/C-only].
- The rendered cone is never computed on a dedicated server, because the lighting thread's creator returns at once when the server flag is set [#2301/C/C-only].
- Hearing range has a base of 3.5 tiles, 2.0 when Deaf, +3.0 for Keen Hearing and −1.0 for Hard of Hearing [#2308/C/C-only].
- Base movement speed is 0.8 less 0.15 per Endurance moodle level and 0.15 per Heavy Load moodle level [#2313/C/C-only].
- No nutrition quantity, macro or body weight enters the base-speed or the walk-speed computation [#2315/C/C-only].
- Combat speed loses 0.07 per Endurance and per Heavy Load moodle level and is clamped to [0.8, 1.6] before the heavy two-hander bonus [#2324/C/C-only].
- Combat speed is computed by the attacking client for its local player and by the server for everyone, and travels client to server in the hit packets [#2322/C/C-only] [#2323/C/C-only].
- After each shot the aiming delay is rewritten as its current value plus the weapon's recoil and aiming-time terms, clamped between 0 and the weapon's aiming time [#2326/C/C-only].
- A player object whose `remote` flag is clear starts a shove, a grapple or an aimed attack only while its melee delay is at or below 0 [#2321/C/C-only].
- On an attacking client, critical chance against a remote player moves by (weight − 80)/2 of the target's body weight around an 80.0 pivot [#2327/C/C-only].

## How it works

The engine has no single perception quantity and no member named for one [#2332/C/C-only].
The rendered view cone, the server's visibility cone, the hearing radius and the weapon sight range are separate computations with separate inputs, and none of them has a setter [#2333/C/C-only].

<a id="vision-cone"></a>
### The rendered view cone

The rendered player view cone is computed in degrees by `LightingJNI.calculateVisionCone` from a 144 base less 72 times the fatigue stat, capped at 144 [#2292/C/C-only].
A fatigue stat at its maximum costs a further 36 degrees of view cone [#2293/C/C-only].
A Drunk moodle level of 2 or more costs 0.36 times the intoxication stat in view-cone degrees [#2294/C/C-only].
A Panic moodle at level 4 exactly costs 36 degrees of view cone, and lower Panic levels cost nothing [#2295/C/C-only].
The view cone is clamped to [18, 180] degrees before the trait bonuses and to [18, 360] after the worn-item multiplier [#2296/C/C-only].
The Eagle Eyed trait adds 36 times daylight strength to the view cone, so it is worth nothing at night [#2297/C/C-only]; Night Vision's mirror-image term is under [night vision](#night-vision).
The worn-item vision multiplier scales the whole view cone and is the reciprocal of a modifier accumulated by dividing by each worn item's script `visionModifier` [#2299/C/C-only]; so an item above one widens the cone, one below one narrows it, and several compose multiplicatively.
The lerped view cone is held in a `private static` field, so it is one value per process rather than per character [#2300/C/C-only].

The view-cone computation does not run on a dedicated server, because the lighting thread's creator returns immediately when the server flag is set [#2301/C/C-only].
A server-side mod moves the cone only through its inputs — the fatigue and intoxication stats, the Drunk and Panic moodles, the worn items and the trait list — which the client reads on its next frame; the two stats reach it on the [player-stats packet](wire-packets.md#player-stats-packet).

The engine hands the native lighting the view cone, the effective fatigue, the detection range in a local the jar's debug information names `perceptionDistance`, and the boolean `hasTrait(SHORT_SIGHTED)` [#2303/C/C-only].
Two of those bear on distance: the Short Sighted boolean and the detection range, which is the hearing range under [hearing](#hearing); what the native code makes of either is outside the bytecode.
Effective fatigue, the value the native lighting receives, is `max(0, fatigue − 0.6) × 2.5` [#2304/C/C-only], so moderate tiredness never reaches the native side through this input.

The Short Sighted trait drives a screen-blur target, set when the trait and wearing glasses disagree [#2329/C/C-only].
Character reveal rate halves for a Short Sighted camera character and rises by half again for an Eagle Eyed one [#2330/C/C-only].
Weapon sight range collapses to the minimum for a Short Sighted character without glasses, and otherwise scales by 1 + aiming/30 and by 1.2 for Eagle Eyed [#2331/C/C-only].
Glasses therefore cancel the Short Sighted penalty on the sight range and the blur, and the blur and reveal rate read the camera character, so both act on the viewing client only.

<a id="server-visibility"></a>
### The server's visibility cone

The server runs its own perception model, `IsoGameCharacter.calculateVisibilityData`, whose cone is a cosine threshold built from fatigue, intoxication, Panic and Eagle Eyed, and which is 1.0 for a player in a vehicle [#2305/C/C-only].
In the server's visibility test a square takes the in-cone branch when the look-direction dot product does not exceed the cone threshold, so a higher cone value is a wider cone [#2306/C/C-only], and a player in a vehicle sees all the way round.
The hearing-reveal arm of the server's visibility test is gated behind a not-a-server check while the method's only caller is the server's own LOS thread, so that arm is not reached on any traced path [#2307/C/C-only].
The server's hearing figure is therefore computed and discarded on a dedicated server.
Night Vision appears only in the rendered cone, so the server's idea of what a player can see does not change with it [#2298/C/C-only]; a server-side write of fatigue or intoxication moves the server cone at once and the client cone after the next stats push [#2305/C/C-only].

<a id="night-vision"></a>
### Night vision

The engine has no quantity called dark vision [#2332/C/C-only].
The engine's dark-vision mechanism is the trait `CharacterTrait.NIGHT_VISION`, which adds 36 times (1 minus daylight strength) degrees to the view cone [#2298/C/C-only].
`CharacterTrait.NIGHT_VISION` also raises the player's render ambient to a floor of 0.20 whenever the computed ambient is below it, independently of the view cone [#2339/C/C-only].
The render settings that hold that floor are not exposed to Lua, and no Lua global names them, so a mod sees the trait and never its render effect [#3027/C/C-only].
Night-vision goggles are a render flag with no packet: the setter's only reader is the per-player render-settings path [#2328/C/C-only], so a server that sets the flag on its copy changes nothing the client draws.
Measured live, a NIGHT_VISION add pushed in the same tick reached the owning client's trait list 14 ms after the push, in daylight at game hour 13; its render effects were not read [#3059/M/n=1].

<a id="hearing"></a>
### Hearing

Hearing range is one public getter, `IsoGameCharacter.getDetectionRange`, with a base of 3.5 tiles, 2.0 when Deaf, +3.0 for Keen Hearing and −1.0 for Hard of Hearing [#2308/C/C-only].
Hearing range is then scaled by the worn-item hearing multiplier above a floor of 2.0 and reduced by the raw fatigue stat and by 0.01 times intoxication [#2309/C/C-only]; the raw stat, unlike the lighting's effective fatigue, narrows hearing at every increment.
Hearing range is used as a tile radius inside which a zombie counts as spotted without line of sight, unless the player is asleep [#2310/C/C-only].
The hear-distance modifier is a separate quantity read only for audio-listener selection and the alarm clock, multiplying by 4.5 when Hard of Hearing [#2311/C/C-only].
The weather hearing multiplier is read only for zombies, never for a player [#2312/C/C-only].

<a id="speed"></a>
### Movement speed

Which side computes walk and run speed is at [mp-model.md](../platform/mp-model.md#ownership), the packet that carries them at [wire-packets.md](wire-packets.md#injuries-packet), and its sender and cadence at [mp-model.md](../platform/mp-model.md#sync-globals); the formula below is the server's.
The base movement speed subtracts 0.15 per Endurance moodle level and 0.15 per Heavy Load moodle level from a 0.8 base [#2313/C/C-only].
Base movement speed also answers to torso and neck injuries at −0.1 each with +0.05 for a bandage, to left-thigh pain above 20, to worn and held bags, to wet natural ground and to sand [#2314/C/C-only].
No nutrition quantity enters the movement-speed chain: neither the base-speed nor the walk-speed method names a nutrition object, a macro or body weight [#2315/C/C-only]; a nutrition effect reaches it only through the Endurance moodle, injuries, pain, footwear or the thermoregulator, most directly the [Endurance moodle](endurance-fatigue-sleep.md#drain).
`updateSpeedModifiers` resets the run, walk and combat speed-modifier fields to 1 and rebuilds them from worn items, and the server calls it immediately before every injuries packet, so those three fields cannot hold a mod's value [#2289/C/C-only].
Missing or destroyed footwear multiplies both the run and the walk modifier by 0.85 [#2317/C/C-only].
A shoe kept at zero condition counts as missing here, so a worn-out pair costs the same as bare feet.

`setSpeedMod` is public and Lua-reachable but has no effect on a player, because every reader of the field is zombie code or the zombie packet [#2318/C/C-only].
A player's move speed reaches no engine path: its one reader `getMoveSpeed` is called only by `getPathSpeed`, which nothing in the jar calls, and its one engine writer is the temperature-state update, which writes a constant 0.06 [#2319/C/C-only].
Clothing run-speed penalties are drawn in the tooltip but not applied, because the method that would sum them has no caller in the jar [#2320/C/C-only].
A player therefore sees a speed penalty on a garment that the engine does not charge.

On the server, `IsoPlayer.currentSpeed` is set from the network movement flag to 1.5 when sprinting, 1.0 when running, 0.5 when walking and 0.0 when still [#2334/C/C-only].
`updateMovementRates` is called behind the server flag on the pass a `remote` player object takes and ungated on the pass a non-`remote` one takes, and the server sets `remote` on every connecting player, so a dedicated server runs it on the server-flag pass [#2335/C/C-only].
`IsoPlayer.runningTime` adds the thirty-frames-per-second multiplier each update while the player runs or sprints with non-zero deferred movement and resets to 0 otherwise, so it is a consecutive-running timer and not a daily total [#2336/C/C-only].
`IsoPlayer` declares no `getCurrentSpeed()` and no accessor for `runningTime`; both are public fields [#2337/C/C-only].

Measured live, a client write of 0.3 to `WalkSpeed` read 0.800000011920929, the control, at every one of the next 15 samples about 250 ms apart to about 3.8 s, standing and in a walking arm whose movement was not confirmed; the write was not read back in its own tick, so whether it took at all is [open](#open) [#3066/M/n=1].

On a server, the falling state's exit packet makes the server run the landing on its copy of the player with the impact the client put in the packet, then push the damage; the state's own exit on the client only stores that impact [#3028/C/C-only].
The character update also runs a landing when the player's next height would fall below the floor, with no side gate of its own, and these two are the jar's only callers of the landing; the bytecode does not settle whether a connected player's fall lands once or on both paths [#3032/C/C-only].
Measured live, a client raised 2 tiles and set falling landed once, on the server: the server's listener heard one `FALLDOWN` of 5.824217319488525 and the client's none, server health fell from 99.35848236083984 to 93.3729248046875 and client health from 99.35374450683594 to 93.37767791748047, and no leg fractured [#3064/M/n=1].
A landing called directly on the client, `DoLand(2.0)`, fired no `FALLDOWN` on either side [#3065/M/n=1].

<a id="combat"></a>
### Combat speed and reaction

Combat speed is computed for the local player on a client and for everyone on the server, and is stored on a field that backs the `CombatSpeed` animation variable [#2322/C/C-only].
Combat speed travels client to server inside the hit packets, read from the sender's `CombatSpeed` variable and written back with `setVariable` on the receiver [#2323/C/C-only], so the attacking client is authoritative for its own swing speed.
Combat speed answers to the Endurance and Heavy Load moodle levels at −0.07 per level each and is clamped to [0.8, 1.6] before the heavy two-hander bonus [#2324/C/C-only], so a mod that drives the Endurance moodle moves swing speed with no combat code of its own.
Neither knockback nor the combat-speed modifier is writable from Lua: `knockbackAttackMod` is a public field with no accessor and `combatSpeedModifier` is a private field rewritten from clothing on every speed update [#2338/C/C-only].

Melee delay is read on the pass a player object takes when its `remote` flag is clear: the player update starts a shove, a grapple or an aimed attack only while `getMeleeDelay()` is at or below 0, the swing state's `SetMeleeDelay` animation event writes it, and the server sets `remote` on every connecting player, so a dedicated server never reads the gate for a connected player [#2321/C/C-only].

The aiming delay is the reaction surface a mod can set, and the hit-chance computation reads it twice through `max(0, …)` [#2325/C/C-only].
After each shot the combat manager rewrites the aiming delay as its current value plus the weapon's recoil and aiming-time terms, clamped between 0 and the primary weapon's aiming time, so a mod's written delay survives only as the base of that sum and never above that ceiling [#2326/C/C-only].
Measured live, an aim flag a client sets by a write rather than by input does not hold: it read false at 555 of 601 ticks, the delay sat at the pistol's aiming time of 25.00, and a delay written to 31.25 read 25.00 from the next sample on [#3062/M/n=1].
The post-shot sum, the per-update aiming step and a write between shots while the player really aims are therefore unmeasured [#3063/M/n=1/open].
Vanilla's rack-firearm action writes the aiming delay additively, adding a term scaled by the gun's aiming time and the Reloading perk to the current delay [#2340/C/C-only]; a mod's write composes with it only if it too adds to the current value.
`OnWeaponSwing` fires from the swing state's entry with the player and the weapon in use, after the attack call whose last act is the post-shot aiming-delay write, so a handler of it runs after that write [#3026/C/C-only].
`OnPlayerAttackFinished` fires from the swing state's exit with the character and the weapon once the attack has landed, and vanilla's reload action listens to it and to `OnWeaponSwingHitPoint` [#3031/C/C-only].
Measured live, all three fire on the shooting client, `OnWeaponSwingHitPoint` 16 to 20 ms after `OnWeaponSwing` and `OnPlayerAttackFinished` 266 to 284 ms after it; the server side was not listened to [#3061/M/n=1].

On an attacking client, critical chance against another, remote player reads the target's body weight on both the shove and the melee arm, moving the chance by (weight − 80)/2 around an 80.0 pivot [#2327/C/C-only].
A lighter target is critted more often, and the weight read is the attacking client's copy of the target.

<a id="dynamic-traits"></a>
### Perception traits

The engine reads perception through traits by name, each effect running where its reader runs: Short Sighted and Eagle Eyed under [the rendered cone](#vision-cone), Night Vision under [night vision](#night-vision), and Deaf, Keen Hearing and Hard of Hearing under [hearing](#hearing).
Measured live on the client, a pushed Short Sighted add collapsed a pistol's sight range from 6 to its minimum of 2, prescription glasses worn restored 6, and removing the trait restored it too [#3060/M/n=1].
Vanilla Lua keys `CharacterTrait.SHORT_SIGHTED` in the trait clothing-selection table and `CharacterTrait.NIGHT_VISION` in the spawn-items key-ring table, which `SpawnItems` applies on `OnNewGame` [#2341/C/C-only]; whether any other vanilla Lua grants for either trait is [open](#open).
A server-side trait change travels in the [player-fields packet](wire-packets.md#player-fields-packet), sent as [sync-globals](../platform/mp-model.md#sync-globals) states; the weight-band traits share the same trait map, at [body-and-weight.md](body-and-weight.md#weight-traits).

## Walls and bounds
<a id="walls"></a>

- `LightingJNI` is absent from the exposer's class set, so no mod Lua can call the view-cone computation or the native lighting bridge [#2302/C/C-only].
- The jar contains no `getPerception`, `setPerception`, `getPerceivedDistance`, `getSightRange`, `DarkVision`, `darkVision` or `reactionTime` literal, so it has no member under any of those names [#2332/C/C-only].
- The engine has no setter for hearing range, the view cone or the worn-item vision and hearing modifiers [#2333/C/C-only].
- The worn-item vision and hearing modifiers are script values, so a mod moves them only through its own item scripts, not by a run-time write [#2299/C/C-only].
- The rendered cone is computed only on a client, and a dedicated server never reads the melee-delay gate for a connected player, so a server-side mod reaches either only through inputs the client receives [#2301/C/C-only] [#2321/C/C-only].

Not covered: the native side of the lighting bridge, and so what distance the Short Sighted boolean or the detection range stands for; how the animation data turns `WalkSpeed`, `RunSpeed`, `StrafeSpeed`, `FitnessSpeed` and `CombatSpeed` into a movement rate or a swing duration; the thermoregulator's movement and combat modifiers, read only as call sites; the injury-speed helpers, the idle and in-trees speeds and the slow factor, named in the chain but never dumped; how often the player update, the lighting update and the server LOS thread run on a live session; the rest of `IsoPlayer.updateLOS` and the client visibility polygon; the render view distance and the climate view distance; the contents of the trait registry; how a receiving side resolves a trait name it has not registered; whether Lua can read the public fields `currentSpeed` and `runningTime`; vanilla foraging's run-time reads of both traits, through its skill definitions in `Foraging/forageSkills.lua` and its trait loop in `Foraging/forageSystem.lua`, and what they change; the per-update melee-delay decay in `IsoGameCharacter.updateInternal`, which lowers the delay by `0.625 ×` the game-time multiplier; the per-update aiming step `IsoGameCharacter.updateAimingDelay`, which lowers the aiming delay while aiming by a step scaled by the game-time multiplier and the Aiming level, floored at zero, and resets it when not aiming; which player objects a client leaves with `remote` clear; and whether any vanilla or workshop Lua calls the inert speed members.

## Open
<a id="open"></a>

- Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold? — a walking arm with movement confirmed and a same-tick read-back is the reading still needed; -> [X47](../areas/open-questions.md#x47) [#2096/C/C-only/open].
- That no vanilla Lua outside the two creation tables grants clothing or an item keyed on Short Sighted or Night Vision, so that a runtime grant of either adds none, is unverified: it rests on a hand grep of the install's `media/lua`, not a committed dataset; re-measure by a committed sweep of vanilla Lua for both trait constants and both trait names [#2342/C/snapshot/unverified].
- Do the post-shot sum, the per-update aiming step and a client write between shots behave as the jar reads while a player really aims? — settled by an aim held by input with the delay below the aiming time; -> [X86](../areas/open-questions.md#x86) [#3063/M/n=1/open].
- The design must decide whether its perception effect is a dark-only effect, because the Night Vision term falls to nothing at full daylight [#2298/C/C-only].
- The design must decide on which side a swing-speed effect is applied, because the attacking client computes its own player's combat speed and sends it to the server [#2322/C/C-only] [#2323/C/C-only].

## See also

- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md#drain) — the endurance stat behind the Endurance moodle that both speed formulas read.
- [perks-and-strength.md](perks-and-strength.md) — the perk levels combat speed and weapon sight read.
- [body-and-weight.md](body-and-weight.md#weight-traits) — the weight-band traits and the body weight critical chance reads.
- [../platform/mp-model.md](../platform/mp-model.md#ownership) — which side computes walk and run speed and which side copies it.
- [wire-packets.md](wire-packets.md#injuries-packet) — the injuries-packet section: the field list of the packet that carries walk and run speed.
- [wire-packets.md](wire-packets.md#player-fields-packet) — the player-fields section: the trait block a server-side trait change travels in.
- [../platform/mp-model.md](../platform/mp-model.md#sync-globals) — the sync-globals section: who sends the injuries and trait pushes, gated how and how often.
- [../platform/jar-research.md](../platform/jar-research.md#walls) — why a cadence or a side verdict read from the jar is a run question.
