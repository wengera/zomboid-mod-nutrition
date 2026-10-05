# BeyondTen's perk and carry writes, the experience anti-cheat, and two install scans

Plan 3 Task 1 desk read, 2026-10-05. Build `42.20.4` · jar `b0bbce05d5`. Read-only: the workshop
tree `D:\SteamLibrary\steamapps\workshop\content\108600\3765241705\mods\BeyondTen`, the install's
`media\lua`, and the jar through `C:\Users\Angus\pz-b42\pz.sh grep|methods|refs|dump`. Nothing here
was exercised on a live server. Register rows this read extends (not re-derived): #1524–#1532
(BeyondTen), #2837 (co-boot, `BeyondTen.VERSION` 1.3.4), #2102 (the Strength ladder), #2103
(`setXPToLevel`), #2109 and #2118 (the Java cap 10), #2124 (vanilla rust), #2132 (`GameServer.addXp`
refreshes the checker), #2142–#2145 (carry), #2147–#2150 (the anti-cheat), #2162 and #2571 (the scans),
#2085 (X40, open).

## 1. What was read

| tree | files | read |
|---|---|---|
| `42/` (loaded on B42; `mod.info` `id=BeyondTen`, `versionMin=42.19`, `version=1.3.4`) | `client/BeyondTen/Client.lua` (342 lines, 2026-09-27), `client/BeyondTen/SkillUI.lua` (259, 2026-08-12), `client/BeyondTen/DetailedSkillTooltipsCompat.lua` (387, 2026-08-28), `server/BeyondTen/Server.lua` (495, 2026-09-04), `shared/BeyondTen/Shared.lua` (377, 2026-09-27), `shared/BeyondTen/Bonuses.lua` (822, 2026-09-27), `shared/BeyondTen/ExtendedBonuses.lua` (707, 2026-08-29), `shared/BeyondTen/SkillRecoveryJournal.lua` (973, 2026-08-28) | `Shared.lua`, `Server.lua`, `Client.lua` whole; `Bonuses.lua` 100–300 and 560–822 whole; the rest by grep for every writer below |
| `common/` | `media/lua/shared/Translate/EN/IG_UI.json` only | whole (strings) |
| root `media/` | the B41 package (`mod.info` `versionMin=41.78`, `versionMax=41.78`, `version=1.2.7`) | not loaded on B42; not read |

Writers grepped across all eight `42/` files: `setPerkLevelDebug`, `LevelPerk`, `LoseLevel`, `level0`,
`setPerkBoost`, `setXPToLevel`, `AddXP`, `addXp`, `setXP`, `setMaxWeight`, `MaxWeightBase`,
`MaxWeightDelta`, `getPerkLevel`, `Perks.Strength`, `Perks.Fitness`, `OnWeaponHitXp`, every `Events.`.

Result of the grep (2026-10-05), complete:

- `setPerkLevelDebug`, `LevelPerk`, `LoseLevel`, `level0`, `setPerkBoost`, `addXp` (the global),
  `setMaxWeightBase`, `setMaxWeightDelta`: **0 hits**.
- `setXPToLevel`: `Server.lua:226` (server `setRawXP`), `Client.lua:50` and `Client.lua:195` (both behind
  `isClient()` being false).
- six-argument `XP.AddXP`: `Server.lua:285`, `Client.lua:113` (both inside `applyNativeOverflow`).
- `setMaxWeight`: `Bonuses.lua:661` (server arm), `Bonuses.lua:695` (single-player arm).
- `getPerkLevel`: `Shared.lua:187` (the only Java level read); `ExtendedBonuses.lua:250` wraps the Lua
  `forageSystem.getPerkLevel`, not the Java method.

## 2. The experience reservoir (Server.lua)

On a dedicated server (`Server.lua:3` returns unless `isServer()`), BeyondTen keeps per-player state
`active[perkId] = { perk, baseline = getTotalXpForLevel(9) }` for every trainable perk whose Java level is
10 (`Server.lua:229-236`, `Shared.lua:12` `BT.RESERVOIR_LEVEL = 9`). Activation calls
`setXPToLevel(perk, 9)`: **the Java level stays 10 while the Java experience is parked at the level-9
cumulative total** — 337500 for Strength and Fitness on the ladder of #2102, where the level-10 total is
487500.

Why: the Java cap (#2109) discards non-negative grants once experience reaches the level-10 total, so
BeyondTen parks experience one level lower to keep vanilla grants landing, then harvests them.

- Every server tick (`Server.OnTick` → `OnPlayerUpdate`, `Server.lua:352-365, 389-395`)
  `resetReservoirs` (`Server.lua:322-350`) reads `getXp():getXP(perk) − baseline`; a non-zero delta is
  banked as mastery experience (`captureMasteryDelta`, `Server.lua:288-304`) and experience is re-parked
  with `setXPToLevel(perk, 9)` (`Server.lua:302`).
- `Events.AddXP` (`Server.OnAddXP`, `Server.lua:397-413`) is the primary path: the event's amount is
  banked and the reservoir re-parked in the same call; the tick poll is the fallback for direct
  XP-map writers.
- The award that first reaches native level 10 is not banked: `OnAddXP` only activates the perk
  (`Server.lua:406-410`), which drops experience from wherever it was to the level-9 total.
- A negative amount larger than the banked mastery (`applyNativeOverflow`, `Server.lua:279-286`)
  deactivates the perk, writes the level-10 total (`setXPToLevel(perk, 10)`) and passes the unabsorbed
  remainder to the six-argument `XP.AddXP(perk, amount, false, false, false, false)`; through vanilla's
  crossing loop (#2123) that can lower the Java level to 9.
- Before a world save (`Events.OnSave` and `Events.OnServerStartSaving`, `Server.lua:424-439, 489-490`) it
  writes every parked perk back to the level-10 total so the save is usable without the mod, and on the
  next tick restores the level-9 total without banking the jump (`restoreAfterSave` → `skipCapture`,
  `Server.lua:323, 342-343`). A write that looks like an external restore to the level-10 total is
  likewise re-parked, not banked (`Server.lua:338-344`).
- A rescan every 60 ticks (`Server.ScanPlayer`, `Server.lua:306-320, 360-364`) activates any perk that
  reached 10 and drops the record of any perk whose Java level fell below 10 — without touching its
  experience.

The rust pass. `installPassiveProtection` (`Server.lua:441-468`, run at file load and at
`OnServerStarted`) replaces `xpUpdate.checkForLosingLevel` with a sentinel-guarded wrapper: for Strength or
Fitness at Java level 10 with an active record it banks the delta (or re-parks) and **returns without
calling vanilla's check**; every other call goes to the original. The original is the absolute test of
#2124 (`XpUpdate.lua:289-297`: `LoseLevel` when experience is below `getTotalXpForLevel(level)`), which
would otherwise fire at once on a parked level-10 perk (337500 < 487500). Vanilla's −1 rust grant
(`addXp(playerObj, perk, getLoosingXpValue())`, `XpUpdate.lua:312, 325`) still runs, reaches
`Events.AddXP` and is debited from the mastery bank.

The client file (`Client.lua`) mirrors this logic for single-player only: `setRawXP`, the tick poll,
`OnAddXP` and `OnSave` all return when `isClient()` is true (`Client.lua:49, 157, 187, 218`), and its rust
wrapper passes straight to the original on a multiplayer client (`Client.lua:297`). `client/` files do not
load on a dedicated server. So on a dedicated server **every BeyondTen write to the Java experience map is
made by `Server.lua`**, and on a connected client none is.

## 3. Mastery levels: storage and derivation (Shared.lua, Server.lua)

- `BT.GetEffectiveLevel` (`Shared.lua:247-253`): the Java `getPerkLevel` whenever it is below 10;
  only at 10 the mastery state 10–15 from `GetMasteryState` (`Shared.lua:231-245`). `GetMasteryRanks` =
  effective − 10, floored 0. BeyondTen never writes the Java level, so **`getPerkLevel` never reads
  above 10 because of BeyondTen** (the Java clamp is #2118).
- Per-level mastery cost `cost(L) = xp10 + (xp10 − xp9)·(L − 10)` (`Shared.lua:192-213`), where
  `xp9`/`xp10` are the perk's level-9 and level-10 costs. For Strength and Fitness (#2102: level 9 costs
  120000, level 10 costs 150000, step 30000): 180000, 210000, 240000, 270000, 300000 for levels 11–15,
  1 200 000 in all (arithmetic).
- The Java ladder has no rung past 10: `PerkFactory$Perk.getXpForLevel` answers −1 for any level
  outside 1–10 (`@103–@117 L210–L213`) and `getTotalXpForLevel` skips −1 entries
  (`@0–@39 L217–L224`), so `getTotalXpForLevel(11)` equals `getTotalXpForLevel(10)` (487500 for
  Strength). BeyondTen never calls it above 10; it builds its own costs from `getXp9()`/`getXp10()`.
- **Store, dedicated server (1.3.4).** The authoritative mastery table is the global modData table
  `BeyondTen_ServerMastery_v1` (`Server.lua:11, 35-41`), `players[<token>].perks[<perkId>] = xp`, the token
  a two-hash digest of `user:<username>|slot:<playerIndex>` (`Server.lua:43-67`). Shared reads and writes
  are routed through it by hooks the server file installs (`BT._storedXPReader` and friends,
  `Server.lua:220-223`). Character modData key `BeyondTen` (`Shared.lua:9, 127-142`) —
  `perks[<perkId>].xp` — is only a mirror: imported once into the global record on first sight as a
  migration (`Server.lua:99-121`), then overwritten from the global record every tick
  (`publishCanonicalXP`, `Server.lua:123-159, 357`), "not trusted as authority" (`Shared.lua:170-171`).
  The client's mirror is fed by server commands `Sync` (full, on the client's `RequestSync`) and
  `SyncPerk` (per change) (`Server.lua:238-272, 415-422`; `Client.lua:236-284`). On death the global
  record is reset to an empty tombstone (`Server.lua:367-381`).
- This supersedes #1528's "keeps all of its state in character modData … needs no custom packet":
  on a dedicated server the state is global modData plus two server commands. #1526's "banked in
  character modData" holds only for the mirror (and single-player).

## 4. Carry and endurance (Bonuses.lua)

`Bonuses.lua` registers `Events.OnTick` on both sides (`:807`); `updatePlayers` walks
`getOnlinePlayers()` on a server (`:764-781`). Per player (`updatePlayerBonuses`, `:737-762`):

- **Carry.** If the Unified Carry Weight Framework is present (global API or the activated-mod check,
  `:80-127`), BeyondTen registers a max-weight modifier `{ add = ranks / otherMultipliers }` and asks the
  framework to recompute on a rank change (`:180-243`); it does not write the field. Otherwise, on the
  server (`updateCarryCapacity`, `:651-664`) **every tick**: `getBodyDamage():UpdateStrength()` (the
  vanilla recompute of #2142, which reads `getMaxWeightDelta()`), then
  `setMaxWeight(floor(getMaxWeight() + StrengthMasteryRanks + 0.5))` only when that differs. At zero
  Strength mastery ranks nothing is written, but the `UpdateStrength()` call still runs every tick for
  every online player. **It never calls `setMaxWeightBase` or `setMaxWeightDelta`** (grep, § 1).
  Composition with a delta writer: the delta is applied inside `UpdateStrength`, BeyondTen's
  `+ranks` lands on top of the result.
- **Endurance** (`updateEndurance`, `:701-735`, run where `isClient()` is false, `:761`). Each tick it
  compares `CharacterStat.ENDURANCE` with its own last value: a loss is cut by
  `min(0.35, 0.02·Fitness ranks [+0.02·Sprinting ranks running] [+0.015·Nimble ranks moving and aiming]
  [+0.01·(Sneak+Lightfoot) ranks moving and sneaking])`, a gain raised by `min(0.15, 0.02·Fitness ranks)`,
  and the result written with `stats:set(CharacterStat.ENDURANCE, …)` when it differs by more than 1e-6.
  At zero ranks in all five perks the value is unchanged and nothing is written.

## 5. The experience anti-cheat (jar)

| question | reading | cite |
|---|---|---|
| interval | per player, at most once per **60000 ms**: `isXpGrowthRateTooHigh` returns false until `NetworkPlayerAI.isXpCheckerIntervalPassed` (the `XpChecker`'s `UpdateLimit`, built with 60000) passes | `NetworkCharacterAI$XpChecker.<init> @4–@15 L96`; `NetworkCharacterAI.isXpCheckerIntervalPassed @0–@10 L399`; `AntiCheatXPUpdate.isXpGrowthRateTooHigh @0–@11 L79–L80` |
| the limiter | `UpdateLimit.Check` is true once more than `delay` has elapsed since `last`; it then advances `last` by one delay, or sets it to now when more than three delays behind | `UpdateLimit.Check @0–@60 L43–L52` |
| who drives it | the server main loop calls each connection's `PacketValidator.update` every frame; that calls `AntiCheat.update(connection)`, which runs every anti-cheat entry's `update`, except while `GameServer.fastForward` is set or the connection is a delayed disconnect | `GameServer.main @4487–@4492 L1135`; `PacketValidator.update @0–@31 L25–L29`; `AntiCheat.update @0–@55 L124–L132` |
| growth | `getXP(perk)` minus the value `NetworkPlayerAI.setXp` returns — the checker's previous stored value (0 when none), which the same call overwrites with the current value; only a rise above the bound trips, a fall never does; the perk walk stops at the first trip, so later perks keep their older stored values until the next pass | `isPerkXpGrowthRateTooHigh @0–@22 L65–L67, @50–@56 L71`; `NetworkCharacterAI.setXp @0–@33 L403–L404`; `isXpGrowthRateTooHigh @12–@47 L83–L85` |
| bound | `1000 × getMaxPerkXpMultiplier × getMaxPerkXpBoostMultiplier` (#2147, #2149); the multiplier is `max(1, the perk's XP multiplier, the checker's stored multiplier)` times `max(1, the global sandbox XP multiplier)` when its toggle is on, else `max(1, the per-perk sandbox option)` — never below 1. No Strength boost, default sandbox: 1000 × 1 × 0.25 = **250 per check** | `AntiCheatXPUpdate.getMaxPerkXpMultiplier @0–@117 L48–L61` |
| snapshot refresh | `updateXpChecker` copies the live experience, boost and multiplier maps into the checker; it is called by `XP.load`, `GameServer.addXp` (#2132) and the console `addxp`; `XP.setXPToLevel` and every `XP.AddXP` overload do not call it | `NetworkCharacterAI.updateXpChecker @0–@95 L418–L421`; `IsoGameCharacter$XP.load @306–@313 L14429`; `AddXPCommand.Command @292–@297 L74`; `IsoGameCharacter$XP.setXPToLevel @0–@106 L14462–L14477` (refs: no `updateXpChecker`) |
| enabling option | entry `XPUpdate` of the `AntiCheat` enum, bound to `ServerOptions.antiCheatXp` = the server option **`AntiCheatXP`**, an enumeration 1–4, **default 2**, with a suspicion threshold of 2. Values (the shipped `UI.json:1819-1822`): 1 ban, 2 kick, 3 log, 4 disabled. `AntiCheat.isEnabled` is false at 4, and on a co-op host (`GameServer.coop`) unless `Core.antiCheats` | `AntiCheat.<clinit> @219–@241 L34`; `ServerOptions.<init> @2312–@2326 L199`; `EnumConfigOption.<init> @0–@5 L8` → `IntegerConfigOption(name, 1, numValues, default)`; `AntiCheat.isEnabled @0–@35 L102` |
| `act` | on a failed check `AntiCheat.update` calls `act(connection, "update failed")` (#2148). `act` returns at once when the entry is disabled, the connection is not fully connected, or the user's role holds `CantBeKickedByAnticheat`. Otherwise: the connection's counter for that entry +1 (`SuspiciousActivity.report`), `AntiCheat.log`; and only when `Core.debug` is false: `doLogUser`, then if counter ≥ 2: value 1 → `doBanUser`, value 2 → `doKickUser`, value 3 → nothing more. The counter falls by 1 every 150000 ms. So at the default (kick) a single trip is logged; a second trip before the counter decays kicks | `AntiCheat.act @0–@131 L163–L181` (the `lookupswitch` at `@76` decoded from the class bytes: key 1 → `@104` `doBanUser`, key 2 → `@119` `doKickUser`, default → `@131` return); `SuspiciousActivity.report @9–@44 L39–L42`; `SuspiciousActivity.<init> @17–@28 L11`; `SuspiciousActivity.update @0–@113 L19–L26` |
| who is exempt | `CantBeKickedByAnticheat` is granted explicitly to `observer` (`Roles.addStatic @346–@350 L375`) and `gm` (`@628–@633 L409`), and `moderator` (`@803–@841 L429–L430`, then eight removals at L432–L439, none of them this capability) and `admin` (`@977–@1015 L447–L448`) take every capability; `banned`, `user` and `priority` do not hold it. So `act` is a no-op for an admin, moderator, gm or observer, and the experience check can kick or ban only a `user` or `priority` connection | `Roles.addStatic` as cited |

What the X40 session must know from this:

- The fixture server runs `AntiCheatXP=2` (kick) (`testing/fixtures/default/cache/server/Server/pzt.ini:385`),
  without `-debug` (`testing/pzt/server.py:244-246`).
- The harness character `admin` holds `CantBeKickedByAnticheat`, so a trip never reaches the counter,
  the user log, a kick or a ban for it — `act` returns before `AntiCheat.log`. The only trace of a trip
  for the admin is the `perk %s xp growth is too high: …` line `isPerkXpGrowthRateTooHigh` writes on
  `DebugType.Multiplayer` before `act` is called. Whether that line reaches the server console under the
  server's default debug-log filter was not read (`DebugType.error` → `DebugLogStream.errorWithTraceOffset`).
- A non-admin character at the default policy is logged on the first trip and kicked on the second
  within the 150 s decay window.

## 6. Install scans (2026-10-05)

`grep -rn` over `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua` (1395 `.lua` files, the
`media\lua` tree in full, read-only):

- `setMaxWeight`: 22 hits, **all** in `shared/Fishing/fishing_properties.lua` — the definition of the Lua
  method `Fishing.FishConfig:setMaxWeight(weight)` (`:115`) and 21 fish-config calls
  (`:222, 243, 264, 285, 307, 328, 349, 370, 391, 412, 433, 454, 475, 496, 517, 540, 561, 584, 607, 630,
  649`), none on a character.
- `MaxWeightDelta`, `MaxWeightBase` (any case-sensitive occurrence, so both setters and getters): **0 hits**.
- `applyTraitFromWeight`: **0 hits**.

Verdicts: **#2162 verified** — no vanilla Lua file calls `setMaxWeightDelta` or `setMaxWeightBase`
(and no vanilla Lua calls the character's `setMaxWeight` either). **#2571 verified** — vanilla's
`media/lua` calls `applyTraitFromWeight` nowhere.

## 7. For Task 14 (the Strength adapter)

- BeyondTen never writes the Java Strength or Fitness level; its only Java writes are experience writes
  (`setXPToLevel` to the level-9 or level-10 total, and the six-argument `AddXP` with a negative
  remainder), server-side, on every tick for a level-10 perk. A level-only clamp is not fought by any
  BeyondTen setter.
- **The XP-implied level is wrong by one at Java level 10 while BeyondTen runs.** A level-10 Strength reads
  337500 experience (the level-9 total), so a clamp that computes the XP-implied level from
  `getXp():getXP(Strength)` against `getTotalXpForLevel` gets 9 and would write 9. Consequence chain
  (reading, not measured): BeyondTen drops its record at the next rescan, experience stays 337500 (exactly
  the level-9 total, so vanilla rust does not lower it further), mastery experience stays banked but
  dormant (effective level = Java level), and the level-10 rung costs the full 150000 again before
  `LevelPerk` re-crosses it, whereupon BeyondTen re-parks experience at 337500 — so the clamp would hold
  the character at 9 indefinitely. The adapter must treat a Java level of 10 whose experience is at or
  above the level-9 total as XP-implied 10 when BeyondTen is loaded (a global `BeyondTen` table with
  `NATIVE_MAX_LEVEL`), or equivalently never lower a level below 10 on the strength of a parked
  reservoir alone.
- Transient values: for one tick after a world save the experience reads the level-10 total; any reading
  of the XP map is a snapshot of a value BeyondTen rewrites every tick.
- Carry: BeyondTen's server write is `setMaxWeight` after its own `UpdateStrength()` call, both every tick,
  so a `setMaxWeightDelta` write is honoured within one tick and BeyondTen's `+ranks` sits on top.
- Endurance (Plan 5): BeyondTen's server tick rescales the endurance change for mastery ranks > 0 and
  writes `CharacterStat.ENDURANCE`, a second writer on the stat the mod's handler owns; its order against
  `Hook.CalculateStats` is unread.
