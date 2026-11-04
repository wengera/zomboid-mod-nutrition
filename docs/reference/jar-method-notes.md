# Reading the jar — method notes

Moved verbatim on 2026-09-17 from the slice-13 working read (`jar-locks.md`, gitignored until the restructure). Outside the page contract. The disassembler is **not in this repository**: `C:\Users\Angus\pz-b42\pz.sh` (`grep|methods|refs|dump`; `pz-b42/tools/pzdis.py`, `cp.py`, `dis.py`) against `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar` (42.20.4, `b0bbce05d5`), read-only. `docs/platform/jar-research.md` is written from the `tool` rows harvested here.

## Tool note

**Tool note (bounds on every "absence" below).** `pz.sh grep <s>` scans the raw bytes of all ~23.7k
`.class` entries and prints every class whose file contains the byte string — so it hits **method
names, field names, class names, descriptors and string literals alike**
(`pz-b42/tools/pzdis.py` `main()` → `if pat in z.read(e)`). A "no class contains that literal" answer
is therefore a **jar-wide absence of the identifier in any form**, which is the strongest absence this
toolchain can prove. Default cap is `--max 60`; no reading below hit the cap.
`pz.sh methods` lists **every** declared method regardless of access — access flags below were read
with a scratch parser over the same `cp.py` (`ACC_PUBLIC`/`ACC_PRIVATE` bits), because *private* is the
difference between a wall and a door for Lua.

## A worked query — the script checksum gate

```bash
./pz.sh grep checksum | grep -i script
./pz.sh dump zombie/scripting/ScriptManager Load
./pz.sh dump zombie/scripting/ScriptManager getChecksum
./pz.sh methods zombie/network/NetChecksum
./pz.sh dump    zombie/network/NetChecksum makeDigest
# inner classes need the $ escaped in Git Bash:
./pz.sh methods "zombie/network/NetChecksum\$Checksummer"
./pz.sh dump    "zombie/network/NetChecksum\$Checksummer" addFile
./pz.sh dump    "zombie/network/NetChecksum\$Checksummer" checksumToString
./pz.sh dump    "zombie/network/NetChecksum\$Comparer"    update
# ChecksumPacket is NOT at the bare name a traceback prints — the class path is
# zombie/network/packets/service/ChecksumPacket
./pz.sh methods zombie/network/packets/service/ChecksumPacket
./pz.sh dump    zombie/network/packets/service/ChecksumPacket parseServer
./pz.sh dump    zombie/network/packets/service/ChecksumPacket getReason
./pz.sh methods zombie/network/anticheats/AntiCheatChecksumUpdate
./pz.sh dump    zombie/network/anticheats/AntiCheatChecksumUpdate update
./pz.sh dump    zombie/network/anticheats/AntiCheatChecksumUpdate isDifferentChecksumTimeoutExpired
./pz.sh dump    zombie/network/anticheats/AntiCheat update
```

## Summary — where the jar disagreed with plan 13

| # | The plan said | The jar says (today) | Row affected |
|---|---|---|---|
| 1 | `IsoGameCharacter.getNutrition` | declared on **`IsoPlayer`** only | J2 / every row phrased on `character:` |
| 2 | `MoodleType` has **27** statics | **26**, all via `registerBase` — which is `private static`, so that arm is vanilla-only | D1 |
| 3 | moodle registration is the open door; record the members | registration works but is namespaced by **access control** (`register(String)` is the only public arm, and it hard-codes `isBase=false`, so `register("Name")` **throws**); then `Moodle.Update` **does** have a default path — every arm falls through to one shared tail `@3291–@3293 L571 updateMoodleLevel(level)`, and an unmatched type reaches it with the `@0–@6 L93` preset `MinMoodleLevel.ordinal() == 0` — so the private `updateMoodleLevel` **writes 0 into a mod moodle every tick** | **D1 → CANNOT** (a mod moodle is *pinned* at 0, not merely uncomputed) |
| 4 | `MoodleStat` carries the five threshold setter pairs (implying they are usable) | they are public **and `MoodleStat` is absent from `LuaManager$Exposer.exposeAll()`** ⇒ unreachable from Lua; only 20 of 26 types have a stat at all | **D2 → CANNOT** |
| 5 | `grep TriggerHook` → expect `CalculateStats` and `AutoDrink` "among them"; a new intake hook would be a new CAN row | the inventory is **closed at 8 declared / 6 fired**; **`UseItem` and `WeaponSwingHitPoint` are never triggered anywhere in the jar**. **No new CAN row.** | the hook table; B2 stays the Lua-wrapper workaround |
| 6 | `loadstring` "returns nothing outside dead string constants" | `LuaCompiler.loadstring` is a **live method** with a live caller (`UIDebugConsole.ProcessCommand @165 L390`); the real finding is that **no `loadstring` global is ever `rawset`** and the compiler is not exposed | J6 (verdict unchanged, mechanism corrected) |
| 7 | A5 / X6: does an unknown `item` key raise, warn, or vanish? (implied: needs an experiment) | **none of the three** — `DoParam`'s default arm `@11805–@11895 L2992–L3003` puts it in `Item.defaultModData` (Double, else raw String) and `InstanceItem @3477 L1868` copies it onto every instance ⇒ **settled from the jar, no experiment** | **A5 → CAN** |
| 8 | "no script checksum gate was found on 42.20.4" | there **is** one, and it is a **content hash**: `ScriptManager.Load @680 L1525` feeds every loaded script file (mods included) to `NetChecksum$Checksummer.addFile @0–@11 L39` → `Files.readAllBytes`, CR (`bipush 13`) stripped, `MessageDigest.update @62–@70 L47`, one running MD5; `ChecksumPacket.parseServer @72–@84 L231` compares it against `ScriptManager.instance.getChecksum()`, `@118–@146 L234–L235` lets `Capability.BypassLuaChecksum` skip it, and a mismatch ends in the server-side AntiCheat timeout (`AntiCheatChecksumUpdate.update @16–@25 L28–L29`, 60 s) and the client-side `NetChecksum$Comparer.update @74–@85 L213–L215` **forceDisconnect + kickReason**. Requirement: **byte-identical script files on both sides**, not a restriction on what a script may contain | **plan row J3 overturned** (`13-wall-map.md:155` — *not* notes § J3) |
| 9 | (not in the plan) | `Nutrition.update @0–@12 L65–L66` is behind the **`nutrition` boolean sandbox option** (`SandboxOptions.nutrition`, `public final`, read live every tick), and `@42 L75` **skips the macro drain entirely on a client** — the three decay rates are hard-coded Java floats, unlike the Lua `ZomboidGlobals` hunger/thirst rates | **new row**: turn vanilla nutrition off (**server sandbox config set**; a Lua runtime flip is **OPEN** — no `setValue` on `BooleanSandboxOption`, only on its exposed superclass `BooleanConfigOption`) and own the model |
| 10 | (not in the plan) | `CharacterTraitDefinition.addCharacterTraitDefinition(…)` is public static **and Lua-exposed** (`@667`) with cost/description/texture/granted-traits/granted-recipes/XP-boosts/mutual-exclusion ⇒ a mod trait is fully **selectable**, saved and synced — it just has **no Java effect** | **G1 → CAN WITH A WORKAROUND** (effect in Lua) |

**Method-note the later tasks should carry:** `./pz.sh refs <method>` is **not** a reverse-caller
query (amendment 4 asks for one). `pz.sh refs` takes `<class> <method>` and lists the constant-pool
references *inside* that method. Callers were found by `./pz.sh grep <methodName>` to narrow to the
classes that hold the literal, then scanning each of those classes' methods for the call. The scratch
scanner used for that and for the access flags lives at
`C:\Users\Angus\AppData\Local\Temp\claude\C--Users-Angus\affaff4d-3a91-4e3b-af86-a67b53cd3027\scratchpad\{hookscan,acc}.py`
(session-scoped; rewrite it from `pz-b42/tools/{cp,dis}.py` if a later task needs it).

## The swing's facing and the shove's reach (Plan 28)

Read on 2026-11-04 (Plan 28 Task 2) on build 42.21 (buildid 25485521, jar `4a0e9546ec`) with the same toolchain, against
F11's reading that after an attack swung from the held stance the frames' facing read one or three compass points off the
target while after every shove it read the target's bearing (`testing/artifacts/f_goals_12-20261103-144240/GUIDE.md` § 2).
The scans named "every method" dumped each method of the class with `pz.sh dump` and searched the dumps for the call; they
are per-class absences, not the jar-wide `grep` absence of the Tool note. The Bash recipe for a whole class is a loop over
`./pz.sh methods <class>` names into one file (a large class such as `IsoGameCharacter` takes a few minutes).

**The swing sets no facing.** No step of a player's melee swing turns it toward its target: `IsoPlayer.DoAttack` hands to
`CombatManager.pressedAttack` (`jar:IsoPlayer.DoAttack(F,String) @0–@19 L6187–L6193`), none of `CombatManager`'s 120 methods
or `SwipeStatePlayer`'s 35 invokes a facing setter (`setForwardDirection`, `setDirectionAngle`, `setForwardIsoDirection`,
`faceLocation`, `faceThisObject`, `DirectionFromVector`), `SwipeStatePlayer.execute` only stops the action queue
(`jar:SwipeStatePlayer.execute @0–@21 L264–L269`), and the swing animation's `BlockTurn` event sets the player's
ignore-movement flag (`jar:SwipeStatePlayer.OnAnimEvent_BlockTurn @0–@5 L287`) [#4588/C].

**The aimed player faces the mouse.** While a local player reads aiming, its update faces the mouse cursor: after firing
`OnPlayerUpdate` (`jar:IsoPlayer.updateInternal2 @1141–@1145 L2446`) the update sets the aiming flag from the input state,
the force-aim counting as the aim key held (`jar:IsoPlayer.UpdateInputState @378–@387 L4397–L4398`;
`jar:CharacterInputComponent.isAimKeyDown @0–@19 L300`; `jar:IsoPlayer.updateInternal2 @1709–@1717 L2580–L2581`), and then,
aiming and not an NPC, fishing or farming, sets the forward direction to `getAimVector`, the unit vector from the player to
the aiming reticle (`jar:IsoPlayer.updateInternal2 @2946–@2999 L2802–L2805`; `jar:IsoPlayer.getAimVector @0–@19 L1743–L1747`;
`jar:IsoPlayer.calculateAimVector @0–@66 L1751–L1757`), which for a player not on a gamepad is the mouse cursor's position
(`jar:AimingReticle.getXA @0–@22 L32–L34`), and an update that returns early, on the ignore-movement flag or sleep among
others, skips it (`jar:IsoPlayer.updateInternal2 @1295–@1314 L2494–L2496`) [#4589/C].

**The order in a tick.** A client tick runs every player's update and then its post-update, which hands the forward direction
to the animation player as its target, fires the animation events, turns the animation and copies the forward direction
into the view cone's angle, before `OnTick` fires (`jar:IngameState.updateInternal @1064–@1067 L1550`;
`jar:IngameState.updateInternal @1330–@1331 L1573`; `jar:IsoWorld.updateWorld @0–@4 L3350`; `jar:IsoWorld.updateWorld @63–@66 L3359`;
`jar:IsoGameCharacter.postUpdateAnimating @14–@21 L10915–L10917`; `@88–@98 L10938–L10939`; `@184–@263 L10957–L10963`;
`@291–@292 L10967`), and `faceThisObject` on a character sets the forward direction and only the animation's target, not its
angle (`jar:IsoGameCharacter.faceThisObjectAlt @63–@99 L10642–L10648`; `jar:AnimationPlayer.setTargetDirection @24–@86 L894–L898`),
so while the player aims, a facing written from `OnTick` or `OnPlayerUpdate` is overwritten by the next update's aim facing
before the animation reads it [#4590/C].

**`getDir()` and the hit test.** `getDir()` returns the stored `dir` field (`jar:IsoObject.getDir @0–@4 L1935`;
`jar:IsoObject.getForwardIsoDirection @0–@4 L1952`), which `setForwardDirection` writes as the eight-point direction of the
forward vector (`jar:IsoGameCharacter.setForwardDirection(FF) @0–@30 L2823–L2826`), not the animation's angle, and the melee
hit test reads the animation: a target's dot is taken with the look vector, the animation player's angle plus its twist
(`jar:IsoGameCharacter.getDotWithForwardDirection(FF) @0–@45 L2963–L2967`; `jar:IsoGameCharacter.getLookAngleRadians @0–@53 L2883–L2891`),
a melee target counts only with that dot from the weapon's `MinAngle` (÷ 1.5 for a prone target) to its `MaxAngle` (1 at
construction) and inside its range (`jar:CombatManager.getNearestMeleeTargetPosAndDot @0–@104 L1626–L1641`), and the list is
built at the press, where an empty list makes the attack of a weapon type that can miss a `MISS`
(`jar:CombatManager.pressedAttack @573–@575 L3279`; `@615–@719 L3286–L3301`), and again at the swing's collision event
(`jar:CombatManager.attackCollisionCheck @256–@258 L715`) [#4591/C].

**The shove's reach.** A shove's targets come from `CombatManager.calcHitListShove` with the bare hands as its weapon
(`Base.BareHands`: `MaxRange = 1.1`, `MinAngle = 0.5`, category unarmed so `getRangeMod` answers 1.0): a standing character
within 3 tiles centre to centre (distance squared at most 9.0) whose nearest of its head, pelvis and position lies under 1.1
tiles of the shover in the horizontal plane (1.1 + 0.20000000298023224 against a zombie lunging at the shover from under 2
tiles) with the look's dot at least 0.5, and a prone one only when the shove aims at the floor, which `SwipeStatePlayer.enter`
plays as the stomp when the floor target is under 0.6000000238418579 tiles (`jar:CombatManager.calcHitListShove @130–@159 L1882–L1887`;
`@295–@315 L1908–L1910`; `jar:IsoGameCharacter.isMeleeAttackRange @38–@156 L6361–L6369`; `jar:HandWeapon.getRangeMod @0–@96 L491–L511`;
`jar:SwipeStatePlayer.enter @445–@497 L234–L236`) [#4592/C].

**The listing and the facing.** `IsoCell.getZombieList` returns the cell's `zombieList` field with no facing term
(`jar:IsoCell.getZombieList @0–@4 L3204`), no class contains `getZombiesSeen` or `getSeenZombies`, and the facing reaches only
the player's spotting: `IsoPlayer.updateLOS` adds a zombie to the spotted list and sets the objects' alpha from the squares'
sight (`jar:IsoPlayer.updateLOS @501–@557 L6287–L6292`; `@886–@892 L6342`), which `IsoGridSquare.CalcVisibility` refuses
outside the view cone around the light-info angle (`jar:IsoGridSquare.CalcVisibility @239–@270 L9100–L9104`; `@377–@396 L9121`)
that `updateLightInfo` copies from the forward direction in the post-update (`jar:IsoGameCharacter.updateLightInfo @153–@172 L10853–L10854`) [#4593/C].

**What this means for the harness (inference from the readings above and the harness code at `597b826a`, not rows).**
- The frames' `me.dir` (`PZAgent_Sense.lua` L103) is the `dir` field, and the skills tick before the frame is read in one
  `OnTick` (`PZAgent_Main.lua` L195, L200): a frame reports the facing its skill has just written, not the body. Under the
  held stance (the Motor's per-update `setForceAim(true)`) the body and the view cone face the mouse cursor, and an attack's
  frames after its swing read the cursor's direction, its skill writing no facing after the press; a shove starts by
  releasing the stance (`PZAgent_Stance.lua` L190), so no aim facing follows its `faceThisObject` and its frames read the bearing.
- Ruling P28-F: a `faceThisObject` on every tick of the swing would not reach the animation while the stance is held; the
  change is to release the held stance before the attack's swing, as the shove does, and to face the target at least one
  update before `DoAttack`, since the press builds its hit list from the animation's angle at that moment.
- `SHOVE_EARLY_R` = 1.1 tiles to the zombie's position: on one floor the nearest point is never farther than the position.
- `me.zombiesSeen` is the cell list's size (`PZAgent_Sense.lua` L250), so neither it nor the frames' zombies depend on the
  facing; a look-around changes nothing the planner reads.

**Open (not read).** How many updates the animation takes to turn toward a new target (`AnimationPlayer.DoAngles`, the
animation's turn rate); where `BlockTurn` falls in the bat's swing; whether a `MISS` attack's animation fires the collision
event; whether the server's choice of the zombies it sends a client depends on the client's facing; the view cone's width.
