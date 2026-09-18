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
