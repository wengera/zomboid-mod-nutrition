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

The engine has no single perception quantity.
The rendered view cone, the server's visibility cone, the hearing radius and the weapon sight range are separate computations with separate inputs.
Only some of them can be moved by moving a character stat, and none of them has a setter.
The sections below take them in that order, then movement speed, then combat, then the traits the engine reads by name.

<a id="vision-cone"></a>
### The rendered view cone

The rendered player view cone is computed in degrees by `LightingJNI.calculateVisionCone` from a 144 base less 72 times the fatigue stat, capped at 144 [#2292/C/C-only].
A fatigue stat at its maximum costs a further 36 degrees of view cone [#2293/C/C-only].
A Drunk moodle level of 2 or more costs 0.36 times the intoxication stat in view-cone degrees [#2294/C/C-only].
A Panic moodle at level 4 exactly costs 36 degrees of view cone [#2295/C/C-only].
Lower Panic levels cost nothing, so the Panic term is a step at the top of the moodle, not a slope.
The view cone is clamped to [18, 180] degrees before the trait bonuses and to [18, 360] after the worn-item multiplier [#2296/C/C-only].
The Eagle Eyed trait adds 36 times daylight strength to the view cone, so it is worth nothing at night [#2297/C/C-only].
The Night Vision trait adds the mirror-image term, stated under [night vision](#night-vision).

The worn-item vision multiplier scales the whole view cone and is the reciprocal of a modifier accumulated by dividing by each worn item's script `visionModifier` [#2299/C/C-only].
So an item whose script value is above one widens the cone, an item below one narrows it, and several worn items compose multiplicatively.
The item value is script data, so a mod moves it through its own item scripts rather than at run time.

The lerped view cone is held in a `private static` field, so it is one value per process rather than per character [#2300/C/C-only].
A client renders one local view, so in practice the one value is the local player's cone.
The view-cone computation does not run on a dedicated server, because the lighting thread's creator returns immediately when the server flag is set [#2301/C/C-only].
A server-side mod therefore never touches the rendered cone directly.
It moves the cone only by moving the cone's inputs: the fatigue and intoxication stats, the Drunk and Panic moodles, the worn items and the trait list.
The client then recomputes its own cone from those inputs on its next frame.
The fatigue and intoxication stats reach the client on the player-stats packet, whose field contract is at [wire-packets.md](wire-packets.md#player-stats-packet).

Besides position and view direction, the Java side hands the native lighting a few perception inputs per player.
The engine hands the native lighting the view cone, the effective fatigue, the detection range in a local the jar's debug information names `perceptionDistance`, and the boolean `hasTrait(SHORT_SIGHTED)` [#2303/C/C-only].
Two of those bear on distance: the Short Sighted boolean and the detection-range float, which is the hearing range stated under [hearing](#hearing) and so moves with the hearing traits, the worn items' hearing values, fatigue and intoxication.
What the native code makes of either as a distance is outside the bytecode, and it is carried under [Open](#open).
Effective fatigue, the value the native lighting receives, is `max(0, fatigue − 0.6) × 2.5` [#2304/C/C-only].
It is zero until the fatigue stat passes the threshold inside that expression, so moderate tiredness never reaches the native side through this input.

Short Sighted reaches three further client-side effects beyond the native boolean.
The Short Sighted trait drives a screen-blur target, set when the trait and wearing glasses disagree [#2329/C/C-only].
Character reveal rate halves for a Short Sighted camera character and rises by half again for an Eagle Eyed one [#2330/C/C-only].
Weapon sight range collapses to the minimum for a Short Sighted character without glasses, and otherwise scales by 1 + aiming/30 and by 1.2 for Eagle Eyed [#2331/C/C-only].
Glasses therefore cancel the Short Sighted penalty on the weapon-sight arm and on the blur, and a mod that grants the trait meets that cancellation wherever the player wears glasses.
The blur and the reveal rate read the camera character, so both are effects on the viewing client and not on what a server decides.

<a id="server-visibility"></a>
### The server's visibility cone

The server runs its own perception model, `IsoGameCharacter.calculateVisibilityData`, whose cone is a cosine threshold built from fatigue, intoxication, Panic and Eagle Eyed, and which is 1.0 for a player in a vehicle [#2305/C/C-only].
In the server's visibility test a square takes the in-cone branch when the look-direction dot product does not exceed the cone threshold, so a higher cone value is a wider cone [#2306/C/C-only].
The vehicle value is the widest the test admits: a player in a vehicle sees all the way round.
The hearing-reveal arm of the server's visibility test is gated behind a not-a-server check while the method's only caller is the server's own LOS thread, so that arm is not reached on any traced path [#2307/C/C-only].
The server's hearing figure is therefore computed and discarded on a dedicated server.

Fatigue, intoxication and Panic move both cones, each on its own side.
Eagle Eyed widens both.
Night Vision appears only in the rendered cone, so the server's own idea of what a player can see does not change with it.
A server-side write of fatigue or intoxication moves the server cone at once and the client cone after the next stats push.

<a id="night-vision"></a>
### Night vision

The engine has no quantity called dark vision; the absence is listed under [walls](#walls).
The engine's dark-vision mechanism is the trait `CharacterTrait.NIGHT_VISION`, which adds 36 times (1 minus daylight strength) degrees to the view cone [#2298/C/C-only].
The bonus is largest in full darkness and falls to nothing at full daylight, the reverse of Eagle Eyed's term.
`CharacterTrait.NIGHT_VISION` also raises the player's render ambient to a floor of 0.20 whenever the computed ambient is below it, independently of the view cone [#2339/C/C-only].
So the trait brightens a dark scene as well as widening the cone in it.
The render settings that hold that floor are not exposed to Lua, and no Lua global names them, so a mod sees the trait and never its render effect [#3027/C/C-only].
Night-vision goggles are a render flag with no packet: the setter's only reader is the per-player render-settings path [#2328/C/C-only].
A server that sets the goggles flag on a player's server copy changes nothing that player's client draws.
The trait is the lever that reaches the client; how a trait change travels is under [dynamic traits](#dynamic-traits).
Measured live, a NIGHT_VISION add pushed in the same tick reached the owning client's trait list 14 ms after the push, in daylight; its render effects were not read [#3059/M/n=1].

<a id="hearing"></a>
### Hearing

Hearing range is one public getter, `IsoGameCharacter.getDetectionRange`, with a base of 3.5 tiles, 2.0 when Deaf, +3.0 for Keen Hearing and −1.0 for Hard of Hearing [#2308/C/C-only].
Hearing range is then scaled by the worn-item hearing multiplier above a floor of 2.0 and reduced by the raw fatigue stat and by 0.01 times intoxication [#2309/C/C-only].
The fatigue term is the raw stat, not the effective fatigue the lighting receives, so every increment of tiredness narrows hearing.
Hearing range is used as a tile radius inside which a zombie counts as spotted without line of sight, unless the player is asleep [#2310/C/C-only].
The native lighting receives it as well, as one of those perception inputs.

Two other hearing quantities exist and neither is world perception.
The hear-distance modifier is a separate quantity read only for audio-listener selection and the alarm clock, multiplying by 4.5 when Hard of Hearing [#2311/C/C-only].
The weather hearing multiplier is read only for zombies, never for a player [#2312/C/C-only].
A mod that wants to move a player's hearing moves the inputs of the detection range: the three hearing traits, the worn items' script values, fatigue and intoxication.

<a id="speed"></a>
### Movement speed

A multiplayer client does not own its walk speed: which side computes it and which side copies it is stated at [mp-model.md](../platform/mp-model.md#ownership).
Which packet carries the walk and run floats, and its field list, is stated in the injuries-packet section of [wire-packets.md](wire-packets.md#injuries-packet).
Who sends that packet, gated how and how often, is stated in the sync-globals section of [mp-model.md](../platform/mp-model.md#sync-globals).
The formula below is therefore the server's, and the client sees its result one push later.

The base movement speed subtracts 0.15 per Endurance moodle level and 0.15 per Heavy Load moodle level from a 0.8 base [#2313/C/C-only].
Base movement speed also answers to torso and neck injuries at −0.1 each with +0.05 for a bandage, to left-thigh pain above 20, to worn and held bags, to wet natural ground and to sand [#2314/C/C-only].
No nutrition quantity enters the movement-speed chain: neither the base-speed nor the walk-speed method names a nutrition object, a macro or body weight [#2315/C/C-only].
The body-state inputs are the Endurance and Heavy Load moodles, injuries, pain, footwear and the thermoregulator.
A nutrition effect on speed therefore reaches the chain only through one of those, most directly the Endurance moodle, whose stat is described at [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md#drain).

The speed-modifier update resets the run, walk and combat modifiers to 1.0 on every call, so any external write to them survives only until the next call [#2289/C/C-only].
The same update rebuilds the combat modifier from worn clothing and bags.
Missing or destroyed footwear multiplies both the run and the walk modifier by 0.85 [#2317/C/C-only].
A shoe kept at zero condition counts as missing here, so a worn-out pair costs the same as bare feet.

Two Lua-reachable speed members move nothing on a player.
`setSpeedMod` is public and Lua-reachable but has no effect on a player, because every reader of the field is zombie code or the zombie packet [#2318/C/C-only].
A player's move speed reaches no engine path: its one reader `getMoveSpeed` is called only by `getPathSpeed`, which nothing in the jar calls, and its one engine writer is the temperature-state update, which writes a constant 0.06 [#2319/C/C-only].
A third surface is drawn but not applied.
Clothing run-speed penalties are drawn in the tooltip but not applied, because the method that would sum them has no caller in the jar [#2320/C/C-only].
A player therefore sees a speed penalty on a garment that the engine does not charge.

The server also keeps a coarse speed class and a running timer.
On the server, `IsoPlayer.currentSpeed` is set from the network movement flag to 1.5 when sprinting, 1.0 when running, 0.5 when walking and 0.0 when still [#2334/C/C-only].
`updateMovementRates` is called behind the server flag on the pass a `remote` player object takes and ungated on the pass a non-`remote` one takes, and the server sets `remote` on every connecting player, so a dedicated server runs it on the server-flag pass [#2335/C/C-only].
`IsoPlayer.runningTime` adds the thirty-frames-per-second multiplier each update while the player runs or sprints with non-zero deferred movement and resets to 0 otherwise, so it is a consecutive-running timer and not a daily total [#2336/C/C-only].
`IsoPlayer` declares no `getCurrentSpeed()` and no accessor for `runningTime`; both are public fields [#2337/C/C-only].
Whether Lua can read either field on an exposed class is a question the bytecode does not settle.

The movement levers a mod has are the server-side inputs of the formula.
A write to the `WalkSpeed` or `RunSpeed` animation variable on the server lasts until the formula next runs.
A client write of 0.3 to `WalkSpeed` was gone by the first sample a quarter second after it and stayed gone for about 4 s, standing and in a walking arm whose movement was not confirmed [#3066/M/n=1].
No window of a quarter second or more was seen, and because the write was not read back in its own tick, whether it took at all is still open, under [Open](#open).

A fall ends in a landing, and the jar has two landing paths.
On a server, the falling state's exit packet makes the server run the landing on its copy of the player with the impact the client put in the packet, then push the damage; the state's own exit on the client only stores that impact [#3028/C/C-only].
The character update also runs a landing when the player's next height would fall below the floor, with no side gate of its own, and these two are the jar's only callers of the landing; whether a connected player's fall lands once or on both paths is not read [#3032/C/C-only].
Measured live, a client pushed up two tiles fell one level and landed once, on the server: the server's listener heard one `FALLDOWN` of about 5.8, the client's none, both sides' health fell about 6 and no leg fractured [#3064/M/n=1].
A landing called directly on the client, `DoLand(2.0)`, fired no `FALLDOWN` on either side [#3065/M/n=1].

<a id="combat"></a>
### Combat speed and reaction

Combat speed is computed for the local player on a client and for everyone on the server, and is stored on a field that backs the `CombatSpeed` animation variable [#2322/C/C-only].
Combat speed travels client to server inside the hit packets, read from the sender's `CombatSpeed` variable and written back with `setVariable` on the receiver [#2323/C/C-only].
The attacking client is therefore authoritative for its own swing speed.
A server-side write reaches a player's swing only through the inputs the client reads when it computes the value.
Combat speed answers to the Endurance and Heavy Load moodle levels at −0.07 per level each and is clamped to [0.8, 1.6] before the heavy two-hander bonus [#2324/C/C-only].
A mod that drives the Endurance moodle moves swing speed with no combat code of its own.
Neither knockback nor the combat-speed modifier is writable from Lua: `knockbackAttackMod` is a public field with no accessor and `combatSpeedModifier` is a private field rewritten from clothing on every speed update [#2338/C/C-only].

Melee delay is a gate, not a multiplier.
Melee delay is read on the pass a player object takes when its `remote` flag is clear: the player update starts a shove, a grapple or an aimed attack only while `getMeleeDelay()` is at or below 0, the swing state's `SetMeleeDelay` animation event writes it, and the server sets `remote` on every connecting player, so a dedicated server never reads the gate for a connected player [#2321/C/C-only].
A server-side write of melee delay therefore acts on the gate only if the value reaches the client that reads it.

The aiming delay is the reaction surface a mod can set, and the hit-chance computation reads it twice through `max(0, …)` [#2325/C/C-only].
After each shot the combat manager rewrites the aiming delay as its current value plus the weapon's recoil and aiming-time terms, clamped between 0 and the primary weapon's aiming time, so a mod's written delay survives only as the base of that sum and never above that ceiling [#2326/C/C-only].
The post-shot sum is not the delay's only writer: a per-update aiming step also writes it, and that step is listed under [walls](#walls) as not covered.
Measured live, an aim flag a client sets by a write rather than by input does not hold: it read false at most ticks and the delay sat at the pistol's aiming time of 25, a delay written to 31.25 reading 25 again at the next sample [#3062/M/n=1].
The post-shot sum, the per-update step and a write between shots while the player really aims are therefore unmeasured [#3063/M/n=1/open].
Vanilla's rack-firearm action writes the aiming delay additively, adding a term scaled by the gun's aiming time and the Reloading perk to the current delay [#2340/C/C-only].
A mod's own write composes with that call as long as it, too, adds to the current value rather than replacing it.
Two Lua events bracket the swing that makes the post-shot write.
`OnWeaponSwing` fires from the swing state's entry with the player and the weapon in use, after the attack call whose last act is the post-shot aiming-delay write, so a handler of it runs after that write in the same entry [#3026/C/C-only].
`OnPlayerAttackFinished` fires from the swing state's exit with the character and the weapon once the attack has landed, and vanilla's reload action listens to it and to `OnWeaponSwingHitPoint` [#3031/C/C-only].
Measured live, all three fire on the shooting client, `OnWeaponSwingHitPoint` 16 to 20 ms after `OnWeaponSwing` and `OnPlayerAttackFinished` about 270 ms after it; the server side was not listened to [#3061/M/n=1].

On an attacking client, critical chance against another, remote player reads the target's body weight on both the shove and the melee arm, moving the chance by (weight − 80)/2 around an 80.0 pivot [#2327/C/C-only].
A lighter target is critted more often and a heavier one less.
The weight read is the attacking client's copy of the target, so it follows whatever that client last received about the target's weight.

<a id="dynamic-traits"></a>
### Perception traits

The engine reads perception through a handful of traits by name, and the trait list is a perception lever that reaches both the client's rendering and the server's model.
Short Sighted drives the native Short Sighted boolean, the blur, the reveal rate and the weapon sight range, all stated under [the rendered cone](#vision-cone).
Measured live on the client, a pushed Short Sighted add collapsed a pistol's sight range from 6 to its minimum of 2, prescription glasses worn restored 6, and removing the trait restored it too [#3060/M/n=1].
Eagle Eyed widens both cones, raises the reveal rate and lengthens weapon sight.
Night Vision widens the rendered cone in the dark and raises the ambient floor, stated under [night vision](#night-vision).
Deaf, Keen Hearing and Hard of Hearing set the hearing base, stated under [hearing](#hearing).

Vanilla Lua keys `CharacterTrait.SHORT_SIGHTED` in the trait clothing-selection table and `CharacterTrait.NIGHT_VISION` in the spawn-items key-ring table, which `SpawnItems` applies on `OnNewGame` [#2341/C/C-only].
Whether any other vanilla Lua grants clothing or an item for either trait is carried under [Open](#open).
Which packet carries a server-side trait change to a client, and to whom, is stated in the player-fields section of [wire-packets.md](wire-packets.md#player-fields-packet) and the sync-globals section of [mp-model.md](../platform/mp-model.md#sync-globals).
The weight-band traits share the same trait map, described at [body-and-weight.md](body-and-weight.md#weight-traits).
Each trait effect runs where its reader runs: the rendered cone, the blur, the reveal rate and the ambient floor on the client, the visibility cone on the server, and the detection range on whichever side asks for it.

## Walls and bounds
<a id="walls"></a>

- `LightingJNI` is absent from the exposer's class set, so no mod Lua can call the view-cone computation or the native lighting bridge [#2302/C/C-only].
- The jar contains no `getPerception`, `setPerception`, `getPerceivedDistance`, `getSightRange`, `DarkVision`, `darkVision` or `reactionTime` literal, so it has no member under any of those names [#2332/C/C-only].
- The engine has no setter for hearing range, the view cone or the worn-item vision and hearing modifiers [#2333/C/C-only].
- The worn-item vision and hearing modifiers are script values, so a mod moves them only through its own item scripts, not by a run-time write.
- The rendered cone is computed only on a client, and a dedicated server never reads the melee-delay gate for a connected player, so a server-side mod reaches either only through inputs the client receives [#2301/C/C-only] [#2321/C/C-only].

Not covered: the native side of the lighting bridge, and so what distance the Short Sighted boolean or the detection range stands for; how the animation data turns `WalkSpeed`, `RunSpeed`, `StrafeSpeed`, `FitnessSpeed` and `CombatSpeed` into a movement rate or a swing duration; the thermoregulator's movement and combat modifiers, read only as call sites; the injury-speed helpers, the idle and in-trees speeds and the slow factor, named in the chain but never dumped; how often the player update, the lighting update and the server LOS thread run on a live session; the rest of `IsoPlayer.updateLOS` and the client visibility polygon; the render view distance and the climate view distance; the contents of the trait registry; vanilla foraging's run-time reads of both traits, through its skill definitions in `Foraging/forageSkills.lua` and its trait loop in `Foraging/forageSystem.lua`, and what they change; the per-update melee-delay decay in `IsoGameCharacter.updateInternal`, which lowers the delay by `0.625 ×` the game-time multiplier; the per-update aiming step `IsoGameCharacter.updateAimingDelay`, which lowers the aiming delay while aiming by a step scaled by the game-time multiplier and the Aiming level, floored at zero, and resets it when not aiming; which player objects a client leaves with `remote` clear; and whether any vanilla or workshop Lua calls the inert speed members.

## Open
<a id="open"></a>

- Does a client-side write to the `WalkSpeed` animation variable inside the injuries-packet window hold? — settled by a client write sampled in Lua every quarter second for four seconds, walking and standing, against the packet's cadence; -> [X47](../areas/open-questions.md#x47) [#2096/C/C-only/open].
- That no vanilla Lua outside the two creation tables grants clothing or an item keyed on Short Sighted or Night Vision, so that a runtime grant of either adds none, is unverified: it rests on a hand grep of the install's `media/lua`, not a committed dataset; re-measure by a committed sweep of vanilla Lua for both trait constants and both trait names [#2342/C/snapshot/unverified].
- The design must decide which distance input a sight effect goes through, the Short Sighted boolean or the detection-range float the engine labels `perceptionDistance`, because both reach the native lighting and what the native side does with either is outside the bytecode [#2303/C/C-only].
- The design must decide whether its perception effect is a dark-only effect, because the Night Vision term falls to nothing at full daylight [#2298/C/C-only].
- The design must decide how a speed effect reaches the chain, because no nutrition term enters it and every modifier write is reset on the next speed update [#2315/C/C-only] [#2289/C/C-only].
- The design must decide on which side a swing-speed effect is applied, because the attacking client computes its own player's combat speed and sends it to the server [#2322/C/C-only] [#2323/C/C-only].
- The design must decide how a reaction effect keeps its aiming-delay scale, because the combat manager rewrites the delay after each shot [#2326/C/C-only].
- Do the post-shot sum, the per-update aiming step and a client write between shots behave as the jar reads while a player really aims? — settled by an aim held by input with the delay below the aiming time; -> [X86](../areas/open-questions.md#x86) [#3063/M/n=1/open].
- The design must decide whether it syncs a trait of its own for a perception effect, because how a receiving side resolves a trait name it has not registered is unread; the trait block's contract is in the player-fields section of [wire-packets.md](wire-packets.md#player-fields-packet).

## See also

- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md#drain) — the endurance stat behind the Endurance moodle that both speed formulas read.
- [perks-and-strength.md](perks-and-strength.md) — the perk levels combat speed and weapon sight read.
- [body-and-weight.md](body-and-weight.md#weight-traits) — the weight-band traits and the body weight critical chance reads.
- [../platform/mp-model.md](../platform/mp-model.md#ownership) — which side computes walk and run speed and which side copies it.
- [wire-packets.md](wire-packets.md#injuries-packet) — the injuries-packet section: the field list of the packet that carries walk and run speed.
- [wire-packets.md](wire-packets.md#player-fields-packet) — the player-fields section: the trait block a server-side trait change travels in.
- [../platform/mp-model.md](../platform/mp-model.md#sync-globals) — the sync-globals section: who sends the injuries and trait pushes, gated how and how often.
- [../platform/jar-research.md](../platform/jar-research.md#walls) — why a cadence or a side verdict read from the jar is a run question.
