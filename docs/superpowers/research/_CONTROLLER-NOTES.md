# Controller notes — design phase research, 2026-09-27

Readings the controller took on the main thread while the research agents ran. Each is a claims candidate in the same form the agent reports use, and each names the register rows it touches. Nothing here has been applied to the register; that is the documentation plan's work under the § 3 gates.

## N1 — the Strength XP protein branch is live (falsifies #0137 and half of #0181)

Read on the jar 2026-09-27 with `./pz.sh dump 'zombie/characters/IsoGameCharacter$XP' AddXP`, the six-argument overload `AddXP(Perk, float, boolean, boolean, boolean, boolean)`:

- `IsoGameCharacter$XP.AddXP @63–@106 L14196–L14198`: when the perk is `Perks.Fitness` and the character is an `IsoPlayer`, `Nutrition.canAddFitnessXp` false returns before any XP is added (the weight-band gate the library already states at #0184 and #0538).
- `IsoGameCharacter$XP.AddXP @107–@171 L14203–L14205`: when the perk is `Perks.Strength` and the character is an `IsoPlayer`, `Nutrition.getProteins` strictly greater than 50.0 (`fcmpl; ifle`) and strictly less than 300.0 (`fcmpg; ifge`) multiplies the XP amount by 1.5.
- `IsoGameCharacter$XP.AddXP @172–@190 L14207–L14208`: `Nutrition.getProteins` strictly less than −300.0 multiplies the XP amount by 0.699999988079071.
- Both thresholds sit inside the protein store's measured clamp range of −500 to 1000 (#0023), so both arms are reachable in play; neither is measured on a live server.

Consequences for the register:

- `#0137` (eating-pipeline walls: "protein has no Strength-XP effect on this build, its only verified effect being the recovery modifier") is falsified on its first clause and goes `superseded` with a successor stating the branch above. The mirror's Build 34.5 numbers (1.5× between 50 and 300, 0.7× below −300) match the jar exactly, so the mirror corroborates rather than contradicts.
- `#0181` ("Proteins never touch weight and have no reachable effect anywhere in vanilla: the only reader outside the weight model is `getRecoveryMod` …") keeps its weight half and loses its "no reachable effect" half: `AddXP` is a second reader outside the weight model and its arms are reachable. Successor: proteins never touch weight; their two readers outside the weight model are `getRecoveryMod`, whose protein and lipid branches are dead under the clamps, and `AddXP`, whose Strength branch is live.
- `#0186` ("protein surplus … dead space", the new-nutrients rule "give every mod nutrient a consumer the mod writes itself") needs its protein clause narrowed: a protein surplus between 50 and 300 already has one vanilla consumer, Strength XP gain.
- `#0184` and the body-and-weight sentence "Fitness and Strength XP gating is weight-trait based rather than protein based" is half right: Fitness is gated by the band, Strength is scaled by protein. Reword.
- The catalog's reading of `SkillRecoveryJournal` (its `getProteins()` exercise multiplier 1.5 / 1.0 / 0.7, #1584) is that mod reproducing this vanilla branch for its own XP grants, not an invention of its own.

Consequence for the design: the mod's protein model gains a vanilla consumer it must not double-count. If the mod owns the vanilla protein store (writes it from its own protein pool), the vanilla Strength XP bonus follows automatically; if the mod leaves the vanilla store on its drain, the bonus fires on vanilla's number, not the mod's. Which overload a dedicated server actually reaches for a player's combat or exercise XP, and therefore on which side this branch evaluates and against which side's protein value, is in `jar-perks-strength.md` § B and § D and is not re-read here.

## N2 — the trait list has a packet, and server Lua can send it (answers the code half of X4; supersedes #1239, turns G4 from UNKNOWN to CAN WITH A WORKAROUND, C-only)

Read on the jar 2026-09-27, prompted by `jar-health-surfaces.md` § A noting that `SyncPlayerFieldsPacket` carries `CharacterTraits`:

- `SyncPlayerFieldsPacket.write @16–@48 L143–L145` loops the mask byte over six bits and calls `writeParam(1 << i)` for each bit set; `writeParam @1 L52` is a `lookupswitch` whose six keys decode (table read off the bytecode by the controller's script) as 1 → @60 known recipes, **2 → @127 `CharacterTraits.write`** (@131–@140), 4 → @146 already-read books, 8 → @209 `BodyDamage.saveMainFields`, 16 → @229 `isReading`, 32 → @247 `Fitness.save`. `parseParam` mirrors the switch and its key-2 arm calls `IsoPlayer.getCharacterTraits().read` (@134–@140).
- `CharacterTraits.read @0–@40 L115–L121` calls `reset()` first and then `add` for each name it reads, so the receiver's list is replaced wholesale by the sender's.
- `GameServer.sendSyncPlayerFields(IsoPlayer, byte) @0–@35 L2459–L2463` returns when the player is null or has no online id, otherwise sends `PacketType.SyncPlayerFields` with the player and the mask.
- Every Java caller of it on the jar, found by an overload-aware scan of the four classes the jar-wide grep names: `LuaManager$GlobalObject.sendSyncPlayerFields(IsoPlayer, byte) @0–@11 L3910–L3913` (a **Lua global**, gated on `GameServer.server`, a pass-through), `IsoGameCharacter.Eat(InventoryItem, float, boolean) @727–@729 L5807` with mask **8** (the body-damage main fields, the call `facts/eating-pipeline.md` already shows), and `Fitness.exerciseRepeat @72–@74 L200` with mask **32**. No Java code sends mask bit 2 in play.
- Vanilla Lua sends it once: `media/lua/shared/TimedActions/ISReadABook.lua:374` calls `sendSyncPlayerFields(self.character, 0x00000007)` (known recipes, traits and read books together) when a read finishes; the global is server-gated so that fires on the server's copy of the action. That is the one in-play route by which a client's trait list is refreshed after join on this build, which is why every run that read both sides' trait lists without a book read saw them empty and agreeing.
- Two sibling Lua globals exist in the same class and are worth the design's attention: `syncPlayerStats(IsoPlayer, int) @0–@35 L9809–L9812` (server-gated, sends `PacketType.SyncPlayerStats` with a stat mask — vanilla calls it with `SyncPlayerStatsPacket.Stat_Thirst` from `ISDrinkFromBottle.lua:82` and with `0x100`/`0x2` from the medical and farming actions), and `syncBodyPart(BodyPart, long)` (vanilla calls it with per-field masks from the medical actions, `ClientCommands.lua:596` with all bits). Both are the route by which server Lua causes a push rather than waiting for the 1 Hz snapshot; neither is measured here.

Consequences for the register: `#1239` ("no packet has been traced carrying the character trait list to a client") is superseded by the packet and its key; `#0968`, `#0595`, `#1275` and `#1161` (G4 UNKNOWN) move to a C-only verdict of CAN WITH A WORKAROUND — the workaround being a server-side `sendSyncPlayerFields(player, 2)` after any trait write, `applyTraitFromWeight` included — with the live measurement still X4's to take; the rule `#1104` ("evaluate anything band-keyed server-side, or feed it an explicitly transmitted value") stands, and its second arm now has a named mechanism. The "Not covered: the packet path that would carry a character's traits" lines on `body-and-weight.md`, `mp-model.md` and `ui-and-moodles.md` come off.

Consequence for the design: a band label, a trait-keyed client effect and any client-side derivation that reads the trait list become viable once the mod pushes mask 2 after its own trait writes; a client's copy is still only as fresh as the last push, and a vanilla book read will also refresh it. X4 stays the experiment that grades this M.

## N3 — health-surfaces headlines the design leans on (from `jar-health-surfaces.md`, not re-read)

- All body-damage, body-part, stat and thermoregulator updates return early on a multiplayer client for the local player, so the server owns them by an early return inside the tick rather than a caller gate.
- The health API is `ReduceGeneralHealth` and `AddGeneralHealth`; `setOverallBodyHealth` is an unclamped field write that `calculateOverallHealth` erases every tick; the engine's own kill is `ReduceGeneralHealth(110.0f)`.
- The regeneration tier switch decodes as low 0, high 3, default; the four tier constants and the severe-moodle constant (0.0165) all have public setters — settles the inferred mapping at `#0514` from C-inference to C-only.
- The severe-moodle drain has six terms (hunger `/50`, thirst `/10`, sick, bleeding, wound-infection, heavy-load), each firing `OnPlayerGetDamage(chr, tag, amount)`.
- The `CalculateStats` Lua hook returning true skips the whole vanilla stat update (`IsoGameCharacter.calculateStats @49–@59 L10204–L10205`), which the library holds at `#0469` as C-only.
- All 24 `CharacterStat` entries with min, max and default are transcribed; a late-registered stat is never in `ORDERED_STATS`, so never saved or synced.
- Healing speed is the wound timers and the herb/splint factors (public setters), not the four `*SpeedModifier` setters, whose only reader is movement speed; `damageScaler` has no setter.
- `syncBodyPart(part, mask)` is a server-only Lua global pushing any subset of 41 per-part fields (part health is mask value 1).
- Thermal writability is a near-wall: `ThermalNode` has no setters, but the core lerps halfway toward `CharacterStat.TEMPERATURE` each update, so that stat is the one door.
- Absences proved: `FoodSicknessLevel`, `getInfectionLevel`, `FakeInfectionLevel`, `getWoundHealingRate`, `setHealthAdditionModifier`, `setDamageScaler`, `DRUNKENNESS`, `CharacterStat.FEAR`, `Unconscious`, `Fainted`, `setColdResistance`, `setInsulationFactor`.

## N4 — cross-report corroborations and correction candidates noted on receipt (not re-read)

- `jar-perception-speed.md` independently reads the same trait packet as N2 (`SyncPlayerFieldsPacket` param bit 2, `CharacterTraits.read` as reset-then-add) and adds one bound N2 lacks: `INetworkPacket.send(IsoPlayer, …)` delivers to that player's own connection only, so a server-side trait push refreshes the affected player's client and no other client's copy of that player. A band label another player sees is therefore a separate question from the one the player sees.
- The same report finds `CharacterTrait.NIGHT_VISION` adds `36 × (1 − dayLightStrength)` degrees to the rendered cone (client-only computation, `LightingJNI.calculateVisionCone`), view distance is settable only through `hasTrait(SHORT_SIGHTED)`, hearing is `getDetectionRange` with no setter, and a multiplayer client copies its walk and run speed from `PlayerInjuriesPacket` (about every 2000 ms) rather than computing them. Combat speed is client-authoritative and travels client to server in the hit packet. These are the perception subsystem's whole lever set on this build.
- `platform-client-ui.md` reports the installed `simpleStatus` item now resolves its `42.20/` folder, whose bar prerender recomputes every 10 frames and resizes every 60, so `#1467`, `#1477` and `#1114` (the `42.16/` live tree and "no cache anywhere on the path") are correction candidates: the corpus drifted under the library, as [lessons.md#corpus-drift](../../platform/lessons.md#corpus-drift) says it would. The measured-arrivals half of `#1114` stands; the read-count half is dated to the sweep that produced it.
- `platform-client-ui.md` also reads the vanilla food-tooltip nutrition block as gated three ways (a debug option, an internal flag, either Nutritionist trait), so on the `-debug` harness client the block can appear without the trait — a false-positive hazard for any tooltip-reading probe, to be written into the test plan.
- `jar-endurance-fatigue-sleep.md` flags `#0561` ("the endurance updater returns immediately on a game client unless the character is an animal") as reading backwards against the bytecode. Re-dump `IsoGameCharacter.updateEndurance` and `IsoPlayer.updateEndurance` before that row is quoted again.
- `platform-sandbox-options.md` names a harness blocker: `pzt`'s sandbox-key regex excludes nested tables, so a mod's own `SandboxVars.<Prefix>.<Name>` option cannot be set from a profile's `[sandbox]` block today. A nested-aware merge is a harness change under CLAUDE.md § 5 and lands before any run that sets a mod option.

## N5 — the `CalculateStats` hook takes over players only, on the server only (the feasibility gate for architecture C)

Read on the jar 2026-09-27 after Angus chose the full-takeover architecture:

- `IsoGameCharacter.calculateStats @0–@7 L10196–L10197` returns at once for an animal, ahead of the hook, so animals are never affected by a registered `CalculateStats` handler.
- `IsoGameCharacter.calculateStats @8–@48 L10200–L10201`: on a server, when sleep is not both allowed and needed, `Stats.reset(FATIGUE)` runs every tick, ahead of the hook, so the multiplayer fatigue reset survives a takeover (the register's `#0562` mechanism, now with its offsets).
- `IsoGameCharacter.calculateStats @49–@59 L10204–L10205` calls `LuaHookManager.TriggerHook("CalculateStats", this)` and returns when it answers true; `@60–@88 L10208–L10221` otherwise runs, in order, `updateEndurance`, `updateTripping`, `updateThirst`, `updateStress`, `updateStats_WakeState`, `updateMorale`, `updateFitness`. Those seven are the whole of what a takeover must reproduce.
- `LuaHookManager.TriggerHook(String, Object) @0–@41 L35–L38` looks the name up in `EventMap` and returns `Event.trigger`'s value, or false when no hook of that name was ever added.
- `Event.trigger @0–@11 L26–L27` returns false only when `callbacks` is empty; otherwise it runs every callback through `LuaCaller.protectedCallVoid` and returns true at `@222–@223 L49` and `@350–@351 L64`, the callbacks' own return values discarded. Registering one handler therefore skips the seven updaters for every character that reaches the hook, whatever the handler returns, and a second mod's handler cannot restore them.
- `IsoZombie.calculateStats @0 L3456` is a bare `return`: zombies never reach the hook.
- `IsoPlayer.calculateStats @0–@10 L3280–L3283` calls the superclass only when `GameClient.client` is null: on a multiplayer client the hook never fires for the local player, so the takeover is server-side by construction.

Consequence for the design: architecture C is feasible and bounded. The handler runs for players (and any other `IsoLivingCharacter` that is not a zombie or an animal) on the server, it must reproduce exactly seven updaters, and its global, all-or-nothing nature is a compatibility wall with any other mod that registers the same hook, which the packaging page will state.

## Open items the controller is holding

- Which side evaluates the Strength protein branch for a multiplayer player (client-side `AddXP` then `SyncXp` up, or a server-side grant) — decide from `jar-perks-strength.md` § B before the effects subsystem is specified.
- The `getRecoveryMod` lipid and protein branches are read as dead under the clamps (#0181, #0183); the thresholds quoted there are −1000 and −1500. Confirm those thresholds once more when the register rows are rewritten, since the `AddXP` thresholds turned out to be inside the clamp.
