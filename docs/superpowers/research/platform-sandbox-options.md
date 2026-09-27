# Jar + corpus reading: a mod's own sandbox options on B42

Read from one jar of build `42.20.4` (`b0bbce05d5`) on 2026-09-27 with `pz-b42/tools/pzdis.py` via `./pz.sh`, plus the shipped Lua under `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua` and the installed workshop corpus under `D:\SteamLibrary\steamapps\workshop\content\108600` (both read-only).
Every offset and line belongs to this build only; a patch moves all of them together.
Caller sets were built grep-then-scan with a scratch scanner rebuilt over `pz-b42/tools/cp.py` and `pz-b42/tools/dis.py` for this session; absences are jar-wide byte greps over every class entry, with the exact string quoted.
Corpus counts are dated 2026-09-27 and drift under a running session.

## Summary for the design

A mod declares its own sandbox options in one file, `media/sandbox-options.txt`, placed inside the mod's **version dir** or its **`common/`** dir — never at the mod root, which is the B41 location and a dead path on B42, and at least one installed mod (damnlib, workshop 3171167894) ships there and so registers nothing.
The loader is `zombie/sandbox/CustomSandboxOptions`: `init()` walks `ZomboidFileSystem.getModIDs()` — the *resolved active* mod list, which on a joining client is the server's `Mods=` list — tries `<versionDir>/media/sandbox-options.txt` first and falls back to `<commonDir>/media/sandbox-options.txt`, reading exactly one file per mod.
The file is parsed by the ordinary `ScriptParser`, so the grammar is `VERSION = 1,` at top level followed by `option <Prefix>.<Name> { type = …, default = …, min = …, max = …, page = …, translation = …, valueTranslation = …, numValues = …, }` — and because the reader concatenates the file's lines **without newlines** before parsing, every key/value pair must end in a comma including the last one before `}`, only `/* */` comments are stripped (`//` would swallow the rest of the file), and a string `default` may contain `=` but never a comma.
The dot in the option id is the whole mechanism: `SandboxOptions.parseName` splits the id once on `.` into `tableName` and `shortName`, and `toTable`/`fromTable` then read and write `SandboxVars[tableName][shortName]` — so a mod option is `SandboxVars.<Prefix>.<Name>`, and all 1308 option lines in the installed corpus use a dotted id.
The prefix need not be the mod id (MoreDifficultyB42 declares `OnWeaponSwing.*` from a mod whose id is `MoreDifficultZonesB42`), but it is the table name every consumer must spell, and `optionByName` is keyed on the full dotted name, so `getSandboxOptions():getOptionByName("MyMod.Opt")` and `:set("MyMod.Opt", v)` both work.
Sync is free and total: the server writes its whole option list into the connection-details packet (`ConnectionDetails.writeSandboxOptions` → `SandboxOptions.save`), which iterates `options` — custom options included, because a custom option is constructed as an ordinary `BooleanSandboxOption`/`IntegerSandboxOption`/… and `addOption`ed into the same list — and the client parses it in `ConnectToServerState.receiveSandboxOptions` with `load` + `applySettings` + `toLua`.
The hard timing fact, and the one the design must build around, is that **`toLua()` lands after all mod Lua has run at file scope, on both sides**: on the client `ConnectToServerState.Finish` calls `receiveServerOptions` (which runs the whole of `Core.ResetLua` — mod load, custom-option registration, `SandboxVars.lua`, every mod Lua file, and the `OnGameBoot`/`OnResetLua` events) *before* `receiveSandboxOptions`; on the server `GameServer.doMinimumInit` runs `LuaManager.LoadDirBase` for shared/client/server at @341–@354 and only reads `<server>_SandboxVars.lua` at @429 and calls `toLua()` at @473.
So a `media/lua/shared` file that reads a *value* at file scope (`local onset = SandboxVars.MyMod.Onset`) gets the mod's declared default on both sides and never the operator's setting — a live bug present in the corpus (MoreDifficultyB42's `ZoneCheck_shared.lua` and SD-distro's `SDDistro.lua` both do it) — while a file that captures the *sub-table* (`local sv = SandboxVars.MyMod`) is safe, because `toTable` reuses an existing sub-table object and only `rawset`s the leaf.
The only correct pattern is to read at use time, or at `OnGameStart`/`OnServerStarted`, both of which fire after the values land; `OnGameBoot` is safe on the server and **not** on a joining client.
A running change works and is symmetric: an admin's `SandboxOptions.sendToServer()` (the admin panel's `onButtonApply`) sends the full option list, `GameServer.receiveSandboxOptions` applies it, calls `toLua()`, rewrites `<server>_SandboxVars.lua`, and rebroadcasts the raw buffer to every connection, so every client's `GameClient.receiveSandboxOptions` writes its own `SandboxVars` — the packet is gated on `Capability.SandboxOptions` through `PacketAuthorization.isAuthorized`.
There is **no** Lua event when sandbox options change: `OnSandboxOptionsChanged`, `OnSandboxOptions`, `SandboxOptionsChanged`, `OnSandboxVars`, `SandboxChanged` and `OnSandboxChange` are each absent from every class entry in the jar, and `LuaEventManager`'s own string pool holds no event name containing "Sandbox" — so a mod that must react to a mid-session change has to poll or wrap something itself.
For the server file: the server *always* rewrites `<serverName>_SandboxVars.lua` on boot, writing each mod prefix as a nested table at four spaces with its options at eight, so a file that predates the mod simply lacks the mod's sub-table, `fromTable` returns early and leaves the declared defaults in place, and the boot rewrite then adds the block — nothing is lost and nothing needs hand-editing before first boot.
One practical trap for the UI: an option whose `page` is empty gets **no admin-panel row at all** (`ServerSettingsScreen.lua` skips `option:isCustom() and option:getPageName() ~= nil` and prints `WARN:MISSING in SettingsTable: <name>`), so `page` is effectively mandatory for an operator-settable option, and its own label comes from `getText("Sandbox_" .. pageName)`.
Finally, the harness cannot currently set a mod option: `testing/pzt/server.py`'s `SANDBOX_KEY_RX = ^ {4}(\w+) = (?!\{)` deliberately matches only top-level keys and excludes nested-table openers, so `sandbox_keys()` never lists a mod option, `check_sandbox` rejects the key, and a dotted key would be appended as invalid Lua — a nested-aware merge is a prerequisite for testing this mod's own options.

## A — Declaration

### A.1 Where the file goes

| item | value | side | cite |
|---|---|---|---|
| filename | `sandbox-options.txt`, exactly; the only class in the jar holding that literal is `CustomSandboxOptions` | both | `jar:jar-wide grep sandbox-options.txt` → 1 hit |
| path built (first try) | `<versionDir>` + sep + `media` + sep + `sandbox-options.txt` | both | `jar:CustomSandboxOptions.init @40–@63 L33`; concat recipe `\x01\x01media\x01sandbox-options.txt` in the class's constant pool |
| path built (fallback) | `<commonDir>` + sep + `media` + sep + `sandbox-options.txt`, tried only when the version-dir file does not exist or is a directory | both | `jar:CustomSandboxOptions.init @65–@144 L34–L39` (`exists`→`ifeq 94`, `isDirectory`→`ifne 94`, then `goto 145` after the version-dir read) |
| files read per mod | exactly one — the version dir wins and the `common/` copy is then never read | both | `jar:CustomSandboxOptions.init @91 L35` (`goto 145`) |
| `versionDir` | `<modRoot>/<getModVersionDirName(modRoot)>`, absolute; defaults to `42` when no entry qualifies | both | `jar:ChooseGameInfo$Mod.<init> @150–@193 L524–L528`; resolver already carried at [#0825/C/C-only] |
| `commonDir` | `<modRoot>/common`, absolute — **never the mod root** | both | `jar:ChooseGameInfo$Mod.<init> @141–@177 L523–L527` |
| `<modRoot>/media/sandbox-options.txt` | dead on B42: the loader builds no such path | both | same two cites; corpus: `damnlib/media/sandbox-options.txt` is the mod's only copy and its `42.20/media` and `common/media` hold none |
| which mods are scanned | `ZomboidFileSystem.getModIDs()` = the field `mods`, the resolved active list; on a client that is `GameClient.instance.serverMods` | both | `jar:ZomboidFileSystem.getModIDs @1 L972`; `jar:ZomboidFileSystem.loadMods(String) @7–@42 L843–L847` |
| a mod with no details | `ChooseGameInfo.getAvailableModDetails(id) == null` → skipped silently | both | `jar:CustomSandboxOptions.init @32–@37 L30–L31` |

Corpus, 2026-09-27: 103 `sandbox-options.txt` files across the installed workshop tree, 1308 `option` lines, 51 distinct prefixes. 17 of the 103 sit under `common/media/`; the rest are split between version dirs and the dead mod-root `media/`.

### A.2 The block grammar

| item | value | side | cite |
|---|---|---|---|
| reader | `readFile` reads the file line by line into a `StringBuilder` **with no separator appended**, then `parse(sb.toString())` | both | `jar:CustomSandboxOptions.readFile @27–@61 L61–L66` (`append(str)` with no newline) |
| consequence | newlines are erased before parsing, so block layout is free, but a pair with no trailing comma merges into the next line's text and fails its type check | both | `jar:ScriptParser.readBlock @152–@205 L213–L218` (a `,` closes a Value) |
| comments | only `/* */` are stripped; no `//` and no `#` handling exists in `stripComments` | both | `jar:ScriptParser.stripComments @15–@160 L235–L261`, read whole |
| top-level header | `VERSION = 1,` required; parsed with `PZMath.tryParseInt(-1)`, rejected unless `1 <= v <= 1`, else `RuntimeException("invalid or missing VERSION")` | both | `jar:CustomSandboxOptions.parse @12–@54 L81–L87` |
| every child block | must have `type` (the first whitespace token) equal to `option`, case-insensitively, else `RuntimeException("unknown block type …")` | both | `jar:CustomSandboxOptions.parse @86–@116 L91–L92` |
| the option id | the **second** whitespace token before the `{`; further tokens are discarded, so `option X = {` parses identically to `option X {` | both | `jar:ScriptParser.readBlock @49–@95 L198–L201` |
| missing id | warn `missing or empty option id`, option dropped | both | `jar:CustomSandboxOptions.parseOption @0–@19 L105–L107` |
| `type` values | `boolean`, `double`, `enum`, `integer`, `string` — exact, case-**sensitive** `String.equals` after `trim()` | both | `jar:CustomSandboxOptions.parseOption @62–@190 L116` (lookupswitch on `hashCode` then `equals`) |
| unknown/missing `type` | warn `unknown option type "%s"` / `missing or empty value "type"`, option dropped | both | `jar:CustomSandboxOptions.parseOption @41–@50 L112–L113`, `@249–@273 L128–L129` |
| a block that fails to build | warn `failed to parse custom sandbox option "%s"` and is not added; the rest of the file still loads | both | `jar:CustomSandboxOptions.parse @125–@150 L96–L98` |
| key/value split | first `=` in the Value's raw text; key is before, value is after (callers `trim()`) | both | `jar:ScriptParser$Block.getValue @27–@57 L153–L155`, `jar:ScriptParser$Value.getValue @0–@30 L52–L53` |
| a value containing `=` | allowed (only the first `=` splits) | both | same; corpus: SkillRecoveryJournal's `CraftRecipe` default holds `LeatherStrips=3` |
| a value containing `,` | impossible — the comma terminates the Value | both | `jar:ScriptParser.readBlock @152–@205 L213–L218` |

Per-type required keys, each missing one dropping the whole option:

| `type` | required | optional | sentinel that drops it | cite |
|---|---|---|---|---|
| `boolean` | `default` (`Boolean.parseBoolean`, so anything but `true` is false) | — | `default` key absent | `jar:CustomBooleanSandboxOption.parse @0–@48 L14–L23` |
| `integer` | `min`, `max`, `default` (all three) | — | any of the three equal to `Integer.MIN_VALUE` after `tryParseInt` | `jar:CustomIntegerSandboxOption.parse @0–@76 L18–L28` |
| `double` | `min`, `max`, `default` (all three) | — | any of the three `NaN` after `tryParseDouble` | `jar:CustomDoubleSandboxOption.parse @0–@85 L18–L28` |
| `enum` | `numValues` (> 0), `default` (> 0, so 1-based) | `valueTranslation` | `numValues <= 0` or `default <= 0` | `jar:CustomEnumSandboxOption.parse @0–@79 L18–L31` |
| `string` | `default` (may be empty after `trim`) | — | `default` key absent; no `min`/`max` (max length is passed `-1`) | `jar:CustomStringSandboxOption.parse @0–@43 L14–L22`; `jar:SandboxOptions.newCustomOption @200 L1890` |
| all types | — | `page`, `translation`; both `trim`med then `discardNullOrWhitespace`, so `page =,` yields `null` | — | `jar:CustomSandboxOption.parseCommon @0–@51 L41–L51`; `jar:StringUtils.discardNullOrWhitespace @0–@12 L54` |

Keys the loader **ignores**, though the corpus uses them: `description` (380 occurrences), `tooltip` (65), `title` (2). Nothing in `parseCommon` or any per-type `parse` reads them; the tooltip comes from a translation key instead (A.4).

### A.3 Registration and the Lua mirror

| item | value | side | cite |
|---|---|---|---|
| when `init()` runs, client | inside `Core.ResetLua`, after `ZomboidFileSystem.loadMods` and before `ScriptManager.Load` and `LuaManager.LoadDirBase` | client | `jar:Core.ResetLua(String,String) @193 L4168`, `@230 L4174`, `@239 L4175`, `@247 L4177`, `@324 L4194` |
| when `init()` runs, server | `GameServer.doMinimumInit`, before `ScriptManager.Load` and before all three `LoadDirBase` calls | server | `jar:GameServer.doMinimumInit @219 L1461`, `@228 L1462`, `@237 L1464`, `@341/@348/@354 L1488–L1490` |
| also at boot | `GameWindow.initShared @115/@124` | client | `jar:GameWindow.initShared @112–@127` |
| also in the constructor | `SandboxOptions.<init>` calls `CustomSandboxOptions.instance.initInstance(this)`, so any freshly constructed `SandboxOptions` (e.g. the admin panel's `SandboxOptions.new()`) carries the mod options | both | `jar:SandboxOptions.<init> @3022–@3026 L396` |
| reset | `CustomSandboxOptions.Reset()` clears the parsed list; `SandboxOptions.removeCustomOptions()` removes them from `options` and from `optionByName` | both | `jar:CustomSandboxOptions.Reset @0 L46`; `jar:SandboxOptions.removeCustomOptions @0–@66 L1909–L1914` |
| what a custom option becomes | an ordinary `SandboxOptions$<Type>SandboxOption`, then `setCustom()`, then `setPageName(page)` and `setTranslation(translation)` if non-null | both | `jar:SandboxOptions.newCustomOption @0–@225 L1865–L1893`; `jar:SandboxOptions.addCustomOption @0–@51 L1897–L1905` |
| the name split | `parseName(id)` returns `[null, id]` unless `id.contains(".")` and `id.split("\\.")` yields exactly 2 parts, then `[part0, part1]` | both | `jar:SandboxOptions.parseName @0–@50 L660–L668` |
| where the split is stored | `tableName` = part 0, `shortName` = part 1, set in the option's constructor, which then `addOption`s itself | both | `jar:SandboxOptions$BooleanSandboxOption.<init> @6–@33 L709–L712` |
| `optionByName` key | `ConfigOption.getName()` — the **full dotted name** | both | `jar:SandboxOptions.addOption @9–@26 L1302` |
| Lua mirror shape | `SandboxVars.<tableName>.<shortName>`; with `tableName == null` (a dotless id) it is `SandboxVars.<shortName>` | both | `jar:SandboxOptions$BooleanSandboxOption.toTable @0–@72 L764–L775` |
| sub-table creation | `toTable` `rawget`s `SandboxVars[tableName]`; if it is already a `KahluaTable` it is **reused**, otherwise a new table is created and `rawset` into `SandboxVars` | both | `jar:SandboxOptions$BooleanSandboxOption.toTable @7–@57 L765–L771` |
| a Lua-side capture of the sub-table | therefore survives every later `toLua()` and sees new values, because only the leaf is `rawset` | both | same cite, `@58–@67 L774` |
| `fromTable` on a missing sub-table | returns immediately, leaving the Java option at its current value | both | `jar:SandboxOptions$BooleanSandboxOption.fromTable @0–@35 L748–L753` |
| `SandboxVars` creation | `media/lua/shared/Sandbox/SandboxVars.lua`: `SandboxVars = require "Sandbox/Apocalypse"` then `getSandboxOptions():initSandboxVars()` | both | `file:media/lua/shared/Sandbox/SandboxVars.lua:1-4` |
| `initSandboxVars` | for every option: `fromTable(SandboxVars)` then `toTable(SandboxVars)` — so vanilla options take the preset literal, and mod options (absent from the preset) are written out at their current Java value | both | `jar:SandboxOptions.initSandboxVars @0–@60 L454–L463` |
| `toLua` | `rawget`s the `SandboxVars` global and calls `toTable` on every option | both | `jar:SandboxOptions.toLua @0–@51 L413–L418` |
| `initSandboxVars` callers | none in Java; the only call anywhere on the install is the Lua one above | both | `jar:jar-wide grep initSandboxVars` → 1 hit, `SandboxOptions.class` itself |
| duplicate ids | `addOption` appends to `options` *and* `put`s into `optionByName`, so two options with the same full name both live in the list while the map keeps the last — a cross-mod prefix collision is not rejected | both | `jar:SandboxOptions.addOption @0–@26 L1301–L1302` (no containsKey check) |

### A.4 Translations

| item | key | cite |
|---|---|---|
| option label | `Sandbox_<translation>`, or `Sandbox_<shortName>` when `translation` is null | `jar:SandboxOptions$BooleanSandboxOption.getTranslatedName @0–@30 L738`; concat recipe `Sandbox_\x01` |
| option tooltip | `Sandbox_<translation>_tooltip`, via `Translator.getTextOrNull` (so it is optional) | `jar:SandboxOptions$BooleanSandboxOption.getTooltip @0–@30 L743`; recipe `Sandbox_\x01_tooltip` |
| enum value labels | `Sandbox_<valueTranslation>_option<N>`, N from 1 to `numValues` | recipe `Sandbox_\x01_option\x01` in `SandboxOptions$EnumSandboxOption.class` |
| page label | `getText("Sandbox_" .. pageName)` | `file:media/lua/client/OptionScreens/ServerSettingsScreen.lua:5149-5150`; `file:media/lua/client/ISUI/AdminPanel/ISServerSandboxOptionsUI.lua:515` |
| file | any `media/lua/shared/Translate/<LANG>/Sandbox.json` (a flat JSON object of key → string) | corpus: `Skill Recovery Journal/common/media/lua/shared/Translate/EN/Sandbox.json` |

### A.5 Worked example from the corpus — SkillRecoveryJournal (workshop 2503622437)

Mod id `SkillRecoveryJournal`; version dirs `42.19/` and `42.20.1/` plus `common/` and a legacy root `media/`. Scores 42019 and 42020 against the build's 42020 ceiling, so **`42.20.1/` is the live version dir** and `42.20.1/media/sandbox-options.txt` is the file that loads; `common/media/` ships no `sandbox-options.txt` and the root `media/` copy is dead.

`42.20.1/media/sandbox-options.txt` (CRLF), first lines verbatim:

```
VERSION = 1,

option SkillRecoveryJournal.RecoveryPercentage
{type = integer, min = 1, max = 100, default = 100, page = SkillRecoveryJournal, translation = SkillRecoveryJournalPercentage,}

option SkillRecoveryJournal.TranscribeSpeed
{type = double, min = 0.001, max = 1000, default = 1, page = SkillRecoveryJournal, translation = SkillRecoveryJournalTranscribeSpeed,}

option SkillRecoveryJournal.RecoverProfessionAndTraitsBonuses
{type = boolean, default = false, page =, translation =,}

option SkillRecoveryJournal.SecurityFeatures
{type = enum, numValues = 3, default = 1, page = SkillRecoveryJournal, translation = SkillRecoveryJournal_SecurityFeatures, valueTranslation = SkillRecoveryJournal_SecFeat_Values,}

option SkillRecoveryJournal.CraftRecipe
{type = string, default = , page = SkillRecoveryJournal, translation = SkillRecoveryJournalCraftRecipe,}
```

Note `page =, translation =,` on `RecoverProfessionAndTraitsBonuses`: both resolve to `null`, which makes that option invisible in the admin panel and the main-menu sandbox screen (B.4) and prints `WARN:MISSING in SettingsTable: SkillRecoveryJournal.RecoverProfessionAndTraitsBonuses` on a client or server.

`common/media/lua/shared/Translate/EN/Sandbox.json`, lines 2–4 and 41–43:

```json
"Sandbox_SkillRecoveryJournal": "Skill Recovery Journal",
"Sandbox_SkillRecoveryJournalPercentage": "General Skill Recovery Percentage",
"Sandbox_SkillRecoveryJournalPercentage_tooltip": "The amount of experience recovered from reading bound journals.<br>…",
…
"Sandbox_SkillRecoveryJournal_SecFeat_Values_option1": "Prevent Username/SteamID Mismatch",
"Sandbox_SkillRecoveryJournal_SecFeat_Values_option2": "Only Prevent SteamID Mismatch",
"Sandbox_SkillRecoveryJournal_SecFeat_Values_option3": "Don't Prevent Mismatches"
```

The first key is the *page* label (`page = SkillRecoveryJournal` → `Sandbox_SkillRecoveryJournal`); the rest are the option labels, tooltips and enum values, all matching the A.4 grammar exactly.

Its 30-odd reads all use the nested form and all sit **inside functions**, e.g. `42.20.1/media/lua/shared/Skill Recovery Journal Calc.lua:122`:

```lua
local killsRecoveryPercentage = SandboxVars.SkillRecoveryJournal.KillsTrack or 0
```

and `42.20.1/media/lua/shared/Skill Recovery Journal Main.lua:58` reads a computed key:

```lua
local specific = SandboxVars.SkillRecoveryJournal["Recover"..ID.."Skills"]
```

### A.6 Second worked example — MoreDifficultyB42 (workshop 3325808670), showing the `common/` route and the prefix/id split

`3325808670/mods/MoreDifficultyB42/` has no version dirs, so `versionDir` resolves to the non-existent `42/` and the loader falls through to `common/media/sandbox-options.txt`. `mod.info` says `id=MoreDifficultZonesB42`, but the option prefix is `OnWeaponSwing` — proof the table name is arbitrary:

```
VERSION = 1,

option OnWeaponSwing.Tier1dmg
{
    type = double,
    min = 0.1,
    max = 10.0,
    default = 1.0,

	page = OnWeaponSwing,
	translation = OnWeaponSwing_Tier1dmg,
}
```

Multi-line blocks and a blank line inside the braces both work, because newlines are erased before parsing. This mod also demonstrates the file-scope trap: `common/media/lua/shared/ZoneCheck_shared.lua:205-208` reads four *values* at file scope, so those four always hold the declared defaults regardless of what the operator set.

## B — Sync

### B.1 The join packet

| item | value | side | cite |
|---|---|---|---|
| carrier | the connection-details blob, one packet, requested via `RequestDataPacket` | server → client | `jar:ConnectionDetails.write @33 L?` (refs list); `jar:jar-wide grep ConnectionDetails` → `RequestDataPacket`, `RequestDataPacket$RequestID` |
| sender | `ConnectionDetails.writeSandboxOptions(ByteBufferWriter)` → `SandboxOptions.instance.save(bb)` | server | `jar:ConnectionDetails.writeSandboxOptions` (refs: `SandboxOptions.instance`, `SandboxOptions.save`) |
| field order in the blob | serverDetails, gameMap, workshopItems, **mods**, startLocation, **serverOptions**, **sandboxOptions**, gameTime, erosionMain, globalObjects, resetID, berries, worldDictionary | server | `jar:ConnectionDetails.write @3–@57` (refs in order) |
| receiver | `ConnectToServerState.receiveSandboxOptions` → `load(bb)`, `applySettings()`, `toLua()` | client | `jar:ConnectToServerState.receiveSandboxOptions @0–@22 L141–L144` |
| read order on the client | `Finish()` calls receiveStartLocation, receiveServerOptions, **receiveSandboxOptions**, receiveGameTime, … in that order | client | `jar:ConnectToServerState.Finish @7 L689`, `@31 L696`, `@55 L703`, `@79 L710` |
| wire format | magic `S A N D`, int 249, int version 6, int count, then count × (`WriteString(fullName)`, `WriteString(valueAsString)`), then the world preset name | server | `jar:SandboxOptions.save @0–@122 L610–L625` |
| are mod options included? | **yes** — `save` iterates `this.options`, and a custom option was `addOption`ed into that same list | server | `jar:SandboxOptions.save @43–@109 L618–L622`; `jar:SandboxOptions$BooleanSandboxOption.<init> @28 L712` |
| unknown name on the client | `optionByName.get(name) == null` → `DebugLog.log("unknown SandboxOption \"…\"")` and skipped; nothing throws | client | `jar:SandboxOptions.load(ByteBuffer) @81–@110 L645–L648` |
| known name | `option.asConfigOption().parse(valueString)` | client | `jar:SandboxOptions.load(ByteBuffer) @113–@124 L650` |
| client without the mod | cannot happen for a required mod — `CheckMods` force-disconnects with `connect-mod-required` before `Finish()` when a server mod is missing locally | client | `jar:ConnectToServerState.CheckMods @124–@255 L669–L677` |
| upgrades | each name and value passes `upgradeOptionName`/`upgradeOptionValue` against the sent version before lookup | client | `jar:SandboxOptions.load(ByteBuffer) @61–@79 L642–L643` |

### B.2 When `SandboxVars` is (re)built, relative to mod Lua

Client, joining a dedicated server — one call chain, in order:

| step | what happens | cite |
|---|---|---|
| 1 | `Finish()` → `receiveStartLocation` | `jar:ConnectToServerState.Finish @7 L689` |
| 2 | `Finish()` → `receiveServerOptions`, which ends with `Core.getInstance().ResetLua("client", "ConnectedToServer")` | `jar:ConnectToServerState.receiveServerOptions @40–@47 L135` |
| 2a | inside `ResetLua`: `CustomSandboxOptions.Reset`, `SandboxOptions.Reset`, `LuaManager.init` | `jar:Core.ResetLua @111 L4149`, `@114 L4150`, `@129 L4155` |
| 2b | `ZomboidFileSystem.loadMods("client")` → the server's mod list | `jar:Core.ResetLua @193 L4168` |
| 2c | `CustomSandboxOptions.init()` + `initInstance(SandboxOptions.instance)` — the mod's options are now registered at their **declared defaults** | `jar:Core.ResetLua @230 L4174`, `@239 L4175` |
| 2d | `ScriptManager.Load` | `jar:Core.ResetLua @247 L4177` |
| 2e | `LuaManager.LoadDirBase` — **every Lua file runs at file scope here**, including `media/lua/shared/Sandbox/SandboxVars.lua` (which builds `SandboxVars` from the Apocalypse literal and calls `initSandboxVars()`) and every mod file | `jar:Core.ResetLua @324 L4194` |
| 2f | `LuaEventManager.triggerEvent("OnGameBoot")`, `("OnMainMenuEnter")`, `("OnResetLua", …)` | `jar:Core.ResetLua @359–@374 L4207–L4209` |
| 3 | `Finish()` → `receiveSandboxOptions` → `load(bb)`, `applySettings()`, **`toLua()`** — only now does `SandboxVars` hold the server's values | `jar:ConnectToServerState.Finish @55 L703`; `jar:ConnectToServerState.receiveSandboxOptions @0–@22 L141–L143` |
| 4 | `IngameState` later triggers `OnGameStart` | `jar:jar-wide grep OnGameStart` → `LuaEventManager`, `IngameState` only |

Server, dedicated boot — `GameServer.main` → `doMinimumInit` (@2254), then `startServer` (@2520):

| step | offset / line | what happens |
|---|---|---|
| 1 | `@219 L1461`, `@228 L1462` | `CustomSandboxOptions.init()` + `initInstance` — options at declared defaults |
| 2 | `@237 L1464` | `ScriptManager.Load` |
| 3 | `@341/@348/@354 L1488–L1490` | `LuaManager.LoadDirBase("shared")`, `("client")`, `("server")` — **all mod Lua file scope runs here** |
| 4 | `@417 L1500` | `File.exists` on `<cacheDir>/Server/<serverName>_SandboxVars.lua` |
| 5 | `@429 L1501` | `loadServerLuaFile(serverName)`; on `false` the server prints the path and `System.exit(1)` |
| 6 | `@466 L1506` / `@491 L1510` | `saveServerLuaFile(serverName)` — the file is rewritten either way |
| 7 | `@473 L1507` / `@498 L1511` | **`toLua()`** — `SandboxVars` now holds the file's values |
| 8 | `@525 L1516` | `LuaEventManager.triggerEvent("OnGameBoot")` |
| 9 | `startServer @231` | `LuaEventManager.triggerEvent("OnServerStarted")` |

### B.3 What a file-scope read gets versus an event-time read

| read | client, joined to a server | server | why |
|---|---|---|---|
| `local x = SandboxVars.MyMod.Opt` at file scope | the mod's declared default | the mod's declared default | file scope is step 2e / step 3; `toLua()` is step 3 / step 7 |
| `local sv = SandboxVars.MyMod` at file scope, then `sv.Opt` inside a function | the server's value | the file's value | `toTable` reuses the existing sub-table object and only `rawset`s the leaf (`jar:…toTable @18–@32 L766–L767`) |
| `SandboxVars.MyMod.Opt` inside a function called from `OnGameBoot` | **declared default** — `OnGameBoot` fires inside `ResetLua`, before the packet | the file's value — `OnGameBoot` is at `@525`, after `toLua()` | asymmetric; do not use |
| `SandboxVars.MyMod.Opt` at `OnGameStart` / `OnServerStarted` / any gameplay event | the server's value | the file's value | both fire after `toLua()` |
| `getSandboxOptions():getOptionByName("MyMod.Opt"):getValue()` at any time | whatever the Java `ConfigOption` holds, which `load` updates one step before `toLua` | same | `jar:SandboxOptions.getOptionByName @0–@11 L1315`; keyed on the full dotted name (`jar:SandboxOptions.addOption @19 L1302`) |

Corpus evidence for both halves: `Skill Recovery Journal` reads only inside functions (30+ sites); `HayesCustoms/media/lua/shared/hcustoms_Tweaker.lua:3` and `ZVirusVaccine42BETA/42.20/media/lua/server/Items/LabDistributions.lua:230` capture the sub-table at file scope (safe); `MoreDifficultyB42/common/media/lua/shared/ZoneCheck_shared.lua:205-208` and `SD-distro/common/media/lua/server/SDDistro.lua:3` capture values at file scope (broken — always the default).

### B.4 The operator-facing UI

| item | value | side | cite |
|---|---|---|---|
| where mod options appear | `ServerSettingsScreen.lua` iterates `getSandboxOptions():getNumOptions()` at file scope and, for each `option:isCustom() and option:getPageName() ~= nil`, finds or creates a page named `option:getPageName()` and appends `{ name = option:getName() }` | client | `file:media/lua/client/OptionScreens/ServerSettingsScreen.lua:5132-5146` |
| an option with no page | gets no page and no row, and prints `WARN:MISSING in SettingsTable: <fullName>` on a client or server | client | `file:…/ServerSettingsScreen.lua:5145-5147`, `5192-5198` |
| page label | `page.name = page.title or getText("Sandbox_" .. page.name)` | client | `file:…/ServerSettingsScreen.lua:5149-5150` |
| widget per type | boolean → checkbox, double → free-text entry, integer → numeric entry, enum → dropdown of `getValueTranslationByIndex(k)`, string → string entry | client | `file:…/ServerSettingsScreen.lua:5157-5186` |
| admin panel | `ISServerSandboxOptionsUI:new` builds `SandboxOptions.new()` and `copyValuesFrom(getSandboxOptions())`, so the editing copy carries the mod options too | client | `file:media/lua/client/ISUI/AdminPanel/ISServerSandboxOptionsUI.lua:795-796`; `jar:SandboxOptions.<init> @3022–@3026 L396` |

## C — Runtime change

| item | value | side | cite |
|---|---|---|---|
| Lua entry point | `getSandboxOptions():set(name, value)` writes only the local `ConfigOption`; it throws `IllegalArgumentException` on an unknown name and does **not** touch `SandboxVars` | either | `jar:SandboxOptions.set @16–@56 L1322–L1327` |
| works for a mod option | yes — `optionByName` is keyed on the full dotted name | either | `jar:SandboxOptions.addOption @9–@26 L1302` |
| pushing the change | `SandboxOptions.sendToServer()` → `GameClient.instance.sendSandboxOptionsToServer(this)`, no-op when not a client | client | `jar:SandboxOptions.sendToServer @0–@13 L1859–L1862` |
| the packet | `PacketType.SandboxOptions`, body = `SandboxOptions.save(bb)` — the whole option list, mod options included | client → server | `jar:GameClient.sendSandboxOptionsToServer @0–@31 L2753–L2761` |
| authorization | `PacketAuthorization.isAuthorized` passes only when the connection's `Role.hasCapability(PacketType.requiredCapability)`; for this packet that constant is `Capability.SandboxOptions` | server | `jar:PacketTypes$PacketAuthorization.isAuthorized @0–@36 L273`; `jar:PacketTypes$PacketType.<clinit> @1892–@1916` (`'SandboxOptions'` then `Capability.SandboxOptions`) |
| server handling | `load(bb)` → `applySettings()` → **`toLua()`** → `saveServerLuaFile(serverName)` → rebroadcast | server | `jar:GameServer.receiveSandboxOptions @0–@31 L1735–L1739` |
| rebroadcast | for **every** entry in `udpEngine.connections`: `startPacket`, `doPacket(SandboxOptions)`, `reader.rewind()`, `put(reader)`, `send` — the raw buffer, unchanged, including back to the sender | server → all clients | `jar:GameServer.receiveSandboxOptions @32–@105 L1741–L1747` |
| client handling | `load(bb)` → `applySettings()` → **`toLua()`**, wrapped in a catch that only logs | client | `jar:GameClient.receiveSandboxOptions @0–@30 L2766–L2772` |
| net effect | after one admin apply, `SandboxVars.<Prefix>.<Name>` is updated on the server and on every connected client, and the server's sandbox file on disk is rewritten | both | the three cites above |
| the vanilla admin path | `ISServerSandboxOptionsUI:onButtonApply` → `settingsFromUI(self.options)` → `self.options:sendToServer()` (client only), then `IsoWorld.parseDistributions()` and `StoryClutter.Init()` | client | `file:media/lua/client/ISUI/AdminPanel/ISServerSandboxOptionsUI.lua:763-772` |
| Lua event on change | **none exists** | — | jar-wide greps, all "no class contains that literal": `OnSandboxOptionsChanged`, `OnSandboxOptions`, `SandboxOptionsChanged`, `OnSandboxVars`, `SandboxChanged`, `OnSandboxChange`; and `LuaEventManager`'s own UTF8 pool holds no string containing `Sandbox` |
| what that costs a mod | a mid-session change is silent: nothing recomputes a cached value, nothing re-reads a captured leaf, nothing fires. A mod that must react has to poll (`EveryOneMinute` re-read is enough) or wrap `ISServerSandboxOptionsUI.onButtonApply` client-side and send its own bus message | both | inference from the absence above |
| main-menu / SP path | `SandboxOptionsScreen:setSandboxVars` writes the option objects then calls `options:toLua()` directly — no packet | client | `file:media/lua/client/OptionScreens/SandboxOptions.lua:945-953` |
| the known stale-mirror rule | generalises to mod options unchanged: `set` writes the `ConfigOption` and `toLua()`/`initSandboxVars()` are the only writers of `SandboxVars` | both | `jar:SandboxOptions.set @46–@56 L1326`; existing rows [#0091/M/n=1], [#0092] |

## D — Presets and the server's `<server>_SandboxVars.lua`

| item | value | side | cite |
|---|---|---|---|
| file path | `ServerSettingsManager.getNameInSettingsFolder("<serverName>_SandboxVars.lua")`; the boot check builds it as `<cacheDir>/Server/<serverName>_SandboxVars.lua` | server | `jar:SandboxOptions.loadServerLuaFile @0–@18 L1442–L1443`; `jar:GameServer.doMinimumInit @388–@415 L1499`; recipe `\x01_SandboxVars.lua` |
| read | `readLuaFile(path)`: returns false if absent; else stashes and nulls the `SandboxVars` global, drops the path from `LuaManager.loaded`, `RunLua(path)`, reads the new global, reads and clears `VERSION`, runs `upgradeLuaTable`, then `fromTable` for **every** option, then restores the stashed global | server | `jar:SandboxOptions.readLuaFile @0–@296 L1579–L1621` |
| an option absent from the file | keeps its current (declared-default) value — the mod's sub-table is simply not there and `fromTable` returns at once | server | `jar:SandboxOptions$BooleanSandboxOption.fromTable @0–@35 L748–L753` |
| a file that predates the mod | loads normally, the mod's options stay at their declared defaults, and the **boot rewrite adds the mod's block** | server | `jar:GameServer.doMinimumInit @429 L1501` then `@466 L1506` then `@473 L1507` |
| no file at all | the load is skipped entirely and `saveServerLuaFile` writes a fresh full file from the defaults | server | `jar:GameServer.doMinimumInit @417–@498 L1500–L1511` (the `ifeq 479` branch) |
| a file that fails to parse | `loadServerLuaFile` returns false → the server prints the canonical path and `System.exit(1)` | server | `jar:GameServer.doMinimumInit @432–@451 L1501–L1503` |
| write | `saveServerLuaFile(name)` → `writeLuaFile(path, false)` | server | `jar:SandboxOptions.saveServerLuaFile @0–@17 L1447` |
| write layout | header `SandboxVars = {` + `    VERSION = 6,`; then all `tableName == null` options flat at four spaces; then one nested group per distinct `tableName`, in first-seen order, `    <tableName> = {` / `        <shortName> = <value>,` / `    },` | server | `jar:SandboxOptions.writeLuaFile @227–@263 L1650–L1656`, `@125–@151 L1639–L1640`, `@505–@777 L1682–L1710` |
| flat vs nested key | flat group writes `ConfigOption.getName()` (full name); nested group writes `getShortName()` | server | `jar:SandboxOptions.writeLuaFile @474–@489 L1680` vs `@735–@749 L1707` |
| value rendering | `ConfigOption.getValueAsLuaString()`; a string option is `"%s"` with `\` and `"` escaped | server | `jar:ConfigOption.getValueAsLuaString @0–@4 L32`; `jar:StringConfigOption.getValueAsLuaString @0–@30 L82` |
| comments in the written file | with the flag false (the server path) each option gets its tooltip as a `--` comment and each enum value a `-- <n> = <label>` line; with the flag true (the preset path) neither is written and the header is `return {` | server | `jar:SandboxOptions.writeLuaFile @232–@263 L1651–L1656`, `@313–@454 L1658–L1676` |
| shipped presets | `loadGameFile(name)` reads `media/lua/shared/Sandbox/<name>.lua`, `RunLua`s it, requires a `KahluaTable` (else `RuntimeException "<file> must return a SandboxVars table"`) and `fromTable`s every option; an option absent from the preset is untouched | both | `jar:SandboxOptions.loadGameFile @0–@128 L1462–L1480` |
| so selecting a preset | never resets a mod option — the five shipped presets (`Apocalypse`, `Extinction`, `Outbreak`, `Rising`, `SixMonthsLater`) contain no mod keys | both | same cite; `file:media/lua/shared/Sandbox/` listing |
| where mod defaults come from | `SandboxOptions.<init>` registers the custom options, then `loadGameFile("Apocalypse")`, then `setDefaultsToCurrentValues()` — so vanilla defaults become the Apocalypse values while a mod option's default stays what its file declared | both | `jar:SandboxOptions.<init> @3022–@3056 L396–L405` |
| user presets | `loadPresetFile`/`savePresetFile` use `LuaManager.getSandboxCacheDir()` and the INI-style `readTextFile`/`writeTextFile`, not Lua | client | `jar:SandboxOptions.loadPresetFile @0–@17 L1451`; `jar:SandboxOptions.savePresetFile @0–@27 L1455–L1458` |
| `upgradeLuaTable` on a mod sub-table | recurses into nested tables generically with a `<prefix>.<key>` name, runs `upgradeOptionName`/`upgradeOptionValue` on each leaf, then `rawset`s with the prefix stripped — so an unmatched mod name passes through unchanged | server | `jar:SandboxOptions.upgradeLuaTable @0–@159 L1838–L1849` |

### D.1 What the harness can and cannot do today

| item | value | cite |
|---|---|---|
| the fixture's file | `testing/fixtures/default/cache/server/Server/pzt_SandboxVars.lua`, the real server-written shape: top-level options at four spaces, five nested tables (`Basement`, `Map`, `ZombieLore`, `ZombieConfig`, `MultiplierConfig`) opening at four with members at eight | `file:testing/fixtures/default/cache/server/Server/pzt_SandboxVars.lua:1,765,776,786,912,944` |
| the key pattern | `SANDBOX_KEY_RX = re.compile(r"^ {4}(\w+) = (?!\{)")` — four spaces exactly, and the negative lookahead deliberately excludes a nested-table opener | `tool:testing/pzt/server.py:91-93` |
| `sandbox_keys(path)` | lists only those top-level keys, so **no mod option and no mod prefix is ever listed** | `tool:testing/pzt/server.py:96-99` |
| `check_sandbox` | raises `ProfileError` for any `[sandbox]` key not in that list — a profile naming `MyMod.Opt` or `Opt` fails validation, by design ("nested tables such as Map/ZombieLore are not settable from a profile") | `tool:testing/pzt/profile.py:218-235` |
| `merge_sandbox_vars` | rewrites only matching top-level lines and appends anything unmatched as `    <key> = <value>,` before the column-0 `}` | `tool:testing/pzt/server.py:108-139` |
| so a dotted key | would be appended as `    MyMod.Opt = 3,` inside a table constructor — not valid Lua, and the server would exit 1 on `loadServerLuaFile` returning false | `tool:testing/pzt/server.py:131-138`; `jar:GameServer.doMinimumInit @432–@451 L1501–L1503` |
| verdict | **a mod option cannot be merged the same way.** The harness needs a nested-aware path: either `[sandbox.MyMod] Opt = 3` in the TOML mapped onto the existing `    MyMod = {` block (rewriting an eight-space key inside it, appending the block before the column-0 `}` when absent), or a boot-then-merge two-pass run (boot once so the server writes the mod's block, then merge into it) | derived from the four cites above |
| the cheap alternative | do not merge at all: boot with defaults and set the option live through the bus with `getSandboxOptions():set("MyMod.Opt", v)` then `getSandboxOptions():toLua()` on each side, or `:sendToServer()` from an admin client — the values reach every side by C's path and the server rewrites its own file | `jar:SandboxOptions.set @16–@56 L1322–L1327`; `jar:GameServer.receiveSandboxOptions @0–@105 L1735–L1747` |
| what a merge path buys | the option is right from the first tick, before any `OnGameBoot`/`OnServerStarted` consumer reads it — which a live `set` cannot give | inference from B.2 |

## E — Absences (jar-wide greps, exact strings quoted)

| string searched | result | what it settles |
|---|---|---|
| `OnSandboxOptionsChanged` | no class contains that literal | no such Lua event |
| `OnSandboxOptions` | no class contains that literal | no event under that prefix at all |
| `SandboxOptionsChanged` | no class contains that literal | not under a bare name either |
| `OnSandboxVars` | no class contains that literal | — |
| `SandboxChanged` | no class contains that literal | — |
| `OnSandboxChange` | no class contains that literal | — |
| `sandbox-options.bin` | no class contains that literal | no compiled/binary variant of the declaration file |
| `initSandboxVars` | exactly one class, `zombie/SandboxOptions` | the method has no Java caller; the shipped `SandboxVars.lua` is the only call site on the install |
| `updateFromLua` | exactly one class, `zombie/SandboxOptions` | its only caller is `SandboxOptions.load()` (the save-file path) |
| `sandbox-options.txt` | exactly one class, `zombie/sandbox/CustomSandboxOptions` | the two paths in `init()` are the only places the file is looked for |
| `valueTranslation` | three classes: `SandboxOptions$EnumSandboxOption`, `SandboxOptions`, `sandbox/CustomEnumSandboxOption` | the key is enum-only |
| `CustomSandboxOptions` | six classes: `GameWindow`, `SandboxOptions`, `core/Core`, `gameStates/IngameState`, `network/GameServer`, and itself | the complete caller set for registration |

Grep caps: every one of these returned well under the default `--max 60`, so no list above is truncated. `zombie/SandboxOptions` itself was run at `--max 300` and still reported the cap at 60 on the default run, so the network-class narrowing in B.1 was taken from the raised run.

Two further absences are *not* proved and must not be written as walls: I did not grep for a per-mod sandbox declaration under any other filename, and I did not establish that no other Java call site writes `SandboxVars` (I read `toLua`, `initSandboxVars`, `readLuaFile` and the three `receiveSandboxOptions` handlers, which is a read-set and not an exhaustive scan of writers of the `'SandboxVars'` literal).

## Worked example (derived, not measured)

Derived from the vanilla loader's grammar (§ A.2) and the corpus form (§ A.5, § A.6). **Nothing below has been booted.** Fictional mod id `NutriRealism`, prefix `NutriRealism`.

`NutriRealism/common/media/sandbox-options.txt` — LF or CRLF both fine; every pair ends in a comma, including the last before `}`:

```
VERSION = 1,

option NutriRealism.Enabled
{
    type = boolean,
    default = true,
    page = NutriRealism,
    translation = NutriRealism_Enabled,
}

option NutriRealism.ReplaceVanillaNutrition
{
    type = boolean,
    default = true,
    page = NutriRealism,
    translation = NutriRealism_ReplaceVanillaNutrition,
}

option NutriRealism.DeficiencyOnsetDays
{
    type = double,
    min = 0.5,
    max = 365.0,
    default = 14.0,
    page = NutriRealism,
    translation = NutriRealism_DeficiencyOnsetDays,
}

option NutriRealism.SeverityScale
{
    type = integer,
    min = 1,
    max = 10,
    default = 3,
    page = NutriRealism,
    translation = NutriRealism_SeverityScale,
}

option NutriRealism.LethalDeficiency
{
    type = enum,
    numValues = 3,
    default = 2,
    page = NutriRealism,
    translation = NutriRealism_LethalDeficiency,
    valueTranslation = NutriRealism_Lethality,
}

option NutriRealism.ExemptFoodTags
{
    type = string,
    default = ,
    page = NutriRealism,
    translation = NutriRealism_ExemptFoodTags,
}
```

`NutriRealism/common/media/lua/shared/Translate/EN/Sandbox.json`:

```json
{
    "Sandbox_NutriRealism": "Nutrition Realism",
    "Sandbox_NutriRealism_Enabled": "Enable the nutrient model",
    "Sandbox_NutriRealism_Enabled_tooltip": "Turn the whole mod off without unloading it.",
    "Sandbox_NutriRealism_ReplaceVanillaNutrition": "Replace vanilla nutrition",
    "Sandbox_NutriRealism_ReplaceVanillaNutrition_tooltip": "Turns the vanilla Nutrition option off and runs this mod's macro model instead.",
    "Sandbox_NutriRealism_DeficiencyOnsetDays": "Days to first deficiency",
    "Sandbox_NutriRealism_DeficiencyOnsetDays_tooltip": "In-game days of zero intake of a nutrient before its first effect.",
    "Sandbox_NutriRealism_SeverityScale": "Deficiency severity",
    "Sandbox_NutriRealism_SeverityScale_tooltip": "1 is cosmetic, 10 is punishing.",
    "Sandbox_NutriRealism_LethalDeficiency": "Deficiencies can kill",
    "Sandbox_NutriRealism_LethalDeficiency_tooltip": "Whether a sustained deficiency can reduce health to zero.",
    "Sandbox_NutriRealism_Lethality_option1": "Never",
    "Sandbox_NutriRealism_Lethality_option2": "Slowly",
    "Sandbox_NutriRealism_Lethality_option3": "Quickly",
    "Sandbox_NutriRealism_ExemptFoodTags": "Exempt food tags",
    "Sandbox_NutriRealism_ExemptFoodTags_tooltip": "Semicolon-separated tags this mod ignores. Commas are not allowed here."
}
```

The Lua read, identical on both sides — `common/media/lua/shared/NutriRealism_Config.lua`:

```lua
NutriRealism = NutriRealism or {}

-- SAFE at file scope: this captures the sub-table object, which toLua() reuses and
-- only rawsets leaves into. It is nil until initSandboxVars() has run, so guard it.
local SV = SandboxVars.NutriRealism

-- NOT safe at file scope, and the reason this file has no such line:
--   local onset = SandboxVars.NutriRealism.DeficiencyOnsetDays   -- always 14.0

local DEFAULTS = {
    Enabled = true,
    ReplaceVanillaNutrition = true,
    DeficiencyOnsetDays = 14.0,
    SeverityScale = 3,
    LethalDeficiency = 2,
    ExemptFoodTags = "",
}

--- Read one option. Call this at use time or from an event, never at file scope.
function NutriRealism.opt(key)
    local t = SV or SandboxVars.NutriRealism     -- re-resolve after a ResetLua
    local v = t and t[key]
    if v == nil then return DEFAULTS[key] end
    return v
end
```

Server side — `common/media/lua/server/NutriRealism_Server.lua`:

```lua
-- OnServerStarted is after GameServer.doMinimumInit's toLua(), so the operator's
-- <server>_SandboxVars.lua values are in place here.
local function onServerStarted()
    if not NutriRealism.opt("Enabled") then return end
    if NutriRealism.opt("ReplaceVanillaNutrition") then
        getSandboxOptions():set("Nutrition", false)
        getSandboxOptions():toLua()              -- set() alone leaves SandboxVars stale
    end
    NutriRealism.startTick()
end
Events.OnServerStarted.Add(onServerStarted)
```

Client side — `common/media/lua/client/NutriRealism_Client.lua`:

```lua
-- OnGameBoot is NOT usable here: on a joining client it fires inside Core.ResetLua,
-- before ConnectToServerState.Finish reads the sandbox packet. OnGameStart is after.
Events.OnGameStart.Add(function()
    local severity = NutriRealism.opt("SeverityScale")
    NutriRealism.ui = NutriRealism.newPanel(severity)
end)

-- A mid-session admin apply fires no event, so re-read on a cheap cadence.
Events.EveryOneMinute.Add(function()
    NutriRealism.ui:setSeverity(NutriRealism.opt("SeverityScale"))
end)
```

What the server will then write into `<serverName>_SandboxVars.lua` on its next boot (derived from `writeLuaFile`'s emitted shape and the fixture's real file):

```lua
SandboxVars = {
    VERSION = 6,
    ...
    -- Turn the whole mod off without unloading it.
    NutriRealism = {
        Enabled = true,
        ReplaceVanillaNutrition = true,
        DeficiencyOnsetDays = 14.0,
        SeverityScale = 3,
        -- 1 = Never
        -- 2 = Slowly
        -- 3 = Quickly
        LethalDeficiency = 2,
        ExemptFoodTags = "",
    },
}
```

(The exact comment placement and the number formatting of a double are the parts I did not read instruction by instruction; the nesting, the indents, the `<shortName> = <luaValue>,` form and the quoted string are read off `writeLuaFile`.)

## Claims candidates

Each line is worded as it would go on a page. Grade C, bound "C-only" throughout unless the line says otherwise; ids are for the controller to assign.

1. A mod declares its own sandbox options in `media/sandbox-options.txt` inside its version dir, or inside `common/` when the version dir does not ship one, and the loader reads exactly one of the two per mod — `jar:CustomSandboxOptions.init @40–@144 L33–L39` · C · C-only.
2. The mod root's own `media/sandbox-options.txt` is never read on this build: the loader builds only `<versionDir>/media/…` and `<commonDir>/media/…`, and `commonDir` is `<modRoot>/common` rather than the mod root — `jar:CustomSandboxOptions.init @40–@144 L33–L39`, `jar:ChooseGameInfo$Mod.<init> @141–@193 L523–L528` · C · C-only.
3. The loader walks `ZomboidFileSystem.getModIDs()`, the resolved active mod list, so on a joining client the option set is built from the server's mod list and is identical on both sides — `jar:CustomSandboxOptions.init @0–@6 L26`, `jar:ZomboidFileSystem.getModIDs @1 L972`, `jar:ZomboidFileSystem.loadMods(String) @7–@42 L843–L847` · C · C-only.
4. The declaration file is parsed by the ordinary `ScriptParser` after its lines are concatenated with no separator, so newlines are erased and every key/value pair must end in a comma, the last one included — `jar:CustomSandboxOptions.readFile @27–@61 L61–L66`, `jar:ScriptParser.readBlock @152–@205 L213–L218` · C · C-only.
5. `ScriptParser.stripComments` removes only `/* */`, so a `//` comment in a declaration file is not a comment and swallows text up to the next comma — `jar:ScriptParser.stripComments @15–@160 L235–L261` (read whole) · C · C-only.
6. `VERSION = 1,` is mandatory and must be exactly 1: anything else raises `invalid or missing VERSION` and the whole file is lost — `jar:CustomSandboxOptions.parse @12–@54 L81–L87` · C · C-only.
7. Every block must be typed `option` (case-insensitively) or the file raises `unknown block type`, and the option id is the second whitespace token before the brace, so `option X = {` and `option X {` parse identically — `jar:CustomSandboxOptions.parse @86–@116 L91–L92`, `jar:ScriptParser.readBlock @49–@95 L198–L201` · C · C-only.
8. The five accepted `type` values are `boolean`, `double`, `enum`, `integer` and `string`, matched with a case-sensitive `equals` after `trim`, and anything else warns `unknown option type` and drops that one option while the rest of the file loads — `jar:CustomSandboxOptions.parseOption @62–@273 L116–L129`, `jar:CustomSandboxOptions.parse @125–@163 L96–L101` · C · C-only.
9. An `integer` or `double` option needs all three of `min`, `max` and `default`, an `enum` needs `numValues > 0` and a 1-based `default > 0`, and a `boolean` or `string` needs only `default`; a missing one drops the option with a `failed to parse custom sandbox option` warning — `jar:CustomIntegerSandboxOption.parse @0–@76 L18–L28`, `jar:CustomDoubleSandboxOption.parse @0–@85 L18–L28`, `jar:CustomEnumSandboxOption.parse @0–@79 L18–L31`, `jar:CustomBooleanSandboxOption.parse @0–@48 L14–L23`, `jar:CustomStringSandboxOption.parse @0–@43 L14–L22` · C · C-only.
10. `page` and `translation` are the only two keys `parseCommon` reads, both blank-collapsed to null, so the `description`, `tooltip` and `title` keys 380, 65 and 2 corpus option blocks carry are silently ignored — `jar:CustomSandboxOption.parseCommon @0–@51 L41–L51`, `jar:StringUtils.discardNullOrWhitespace @0–@12 L54`, corpus scan of 103 files on 2026-09-27 · C · C-only.
11. A string option's default may contain `=` because only the first `=` splits key from value, but may never contain a comma because the comma ends the value — `jar:ScriptParser$Block.getValue @27–@57 L153–L155`, `jar:ScriptParser$Value.getValue @0–@30 L52–L53`, `jar:ScriptParser.readBlock @152–@205 L213–L218` · C · C-only.
12. A dotted option id is split once by `SandboxOptions.parseName` into a table name and a short name, and the option's Lua mirror is then `SandboxVars.<tableName>.<shortName>`; a dotless id mirrors flat as `SandboxVars.<name>` — `jar:SandboxOptions.parseName @0–@50 L660–L668`, `jar:SandboxOptions$BooleanSandboxOption.<init> @6–@27 L709–L711`, `jar:SandboxOptions$BooleanSandboxOption.toTable @0–@72 L764–L775` · C · C-only.
13. The dotted prefix is free text and need not be the mod id, but it is the table name every reader must spell — `jar:SandboxOptions.parseName @0–@50 L660–L668`; corpus: `MoreDifficultyB42` (`id=MoreDifficultZonesB42`) declares `OnWeaponSwing.*` · C · C-only.
14. All 1308 `option` lines across the 103 installed `sandbox-options.txt` files use a dotted id, so the nested mirror is the universal corpus convention — corpus scan on 2026-09-27 · C · C-only (dated; the corpus drifts).
15. `SandboxOptions`' name map is keyed on the full dotted name, so `getOptionByName("MyMod.Opt")` and `set("MyMod.Opt", v)` both resolve a mod option — `jar:SandboxOptions.addOption @9–@26 L1302`, `jar:SandboxOptions.getOptionByName @0–@11 L1315`, `jar:SandboxOptions.set @16–@56 L1322–L1327` · C · C-only.
16. `addOption` neither checks nor rejects a duplicate full name: the list keeps both options and the map keeps the last, so two mods sharing a prefix and a short name collide silently — `jar:SandboxOptions.addOption @0–@26 L1301–L1302` · C · C-only.
17. A mod option's label is `Sandbox_<translation>`, its tooltip `Sandbox_<translation>_tooltip` read through `getTextOrNull`, its enum value labels `Sandbox_<valueTranslation>_option<N>`, and its page label `Sandbox_<page>`; with no `translation` the label key falls back to `Sandbox_<shortName>` — `jar:SandboxOptions$BooleanSandboxOption.getTranslatedName @0–@30 L738`, `…getTooltip @0–@30 L743`, concat recipes in `SandboxOptions$EnumSandboxOption.class`, `file:media/lua/client/OptionScreens/ServerSettingsScreen.lua:5149-5150` · C · C-only.
18. A custom option with a null `page` gets no row in the admin panel or the sandbox screen and instead prints `WARN:MISSING in SettingsTable: <name>`, so `page` is effectively mandatory for an operator-settable option — `file:media/lua/client/OptionScreens/ServerSettingsScreen.lua:5132-5147,5192-5198` · C · C-only.
19. The server writes its entire sandbox option list into the connection-details packet as name/value string pairs, and because a custom option is an ordinary option in the same list, a mod option is carried to a joining client with no work from the mod — `jar:ConnectionDetails.writeSandboxOptions`, `jar:SandboxOptions.save @43–@109 L618–L622`, `jar:SandboxOptions$BooleanSandboxOption.<init> @28 L712` · C · C-only.
20. A client that receives a sandbox option name it does not have logs `unknown SandboxOption` and skips it rather than failing the join — `jar:SandboxOptions.load(ByteBuffer) @81–@110 L645–L648` · C · C-only.
21. On a joining client the whole of `Core.ResetLua` — mod load, custom-option registration, `SandboxVars.lua`, every mod Lua file at file scope, and the `OnGameBoot`, `OnMainMenuEnter` and `OnResetLua` events — runs inside `receiveServerOptions`, which `Finish()` calls before `receiveSandboxOptions` — `jar:ConnectToServerState.Finish @31–@55 L696–L703`, `jar:ConnectToServerState.receiveServerOptions @40–@47 L135`, `jar:Core.ResetLua @193–@374 L4168–L4209` · C · C-only.
22. On a dedicated server all three `LuaManager.LoadDirBase` passes run before the server's sandbox file is read and before `toLua()`, so mod Lua file scope precedes the operator's values there too — `jar:GameServer.doMinimumInit @341–@354 L1488–L1490`, `@429 L1501`, `@473 L1507` · C · C-only.
23. A mod Lua file that reads a sandbox *value* at file scope gets the mod's declared default on both the server and every client, never the operator's setting — `jar:GameServer.doMinimumInit @341–@473 L1488–L1507`, `jar:ConnectToServerState.Finish @31–@55 L696–L703` · C · C-only.
24. A mod Lua file that captures the sandbox *sub-table* at file scope is safe, because `toTable` reuses an existing sub-table object and only `rawset`s the leaf value into it — `jar:SandboxOptions$BooleanSandboxOption.toTable @7–@67 L765–L774` · C · C-only.
25. `OnGameBoot` fires after the sandbox values land on a dedicated server and before them on a joining client, so it is not a symmetric read point; `OnServerStarted` and `OnGameStart` both fire after — `jar:GameServer.doMinimumInit @473–@525 L1507–L1516`, `jar:GameServer.startServer @231`, `jar:Core.ResetLua @359 L4207`, `jar:jar-wide grep OnGameStart` → `LuaEventManager` and `IngameState` only · C · C-only.
26. `SandboxVars` is built by the shipped `media/lua/shared/Sandbox/SandboxVars.lua`, which requires the Apocalypse preset table and then calls `initSandboxVars()`; that method reads each option out of the table and writes it straight back, so a vanilla option takes the preset literal and a mod option, absent from the preset, is written out at its current Java value — `file:media/lua/shared/Sandbox/SandboxVars.lua:1-4`, `jar:SandboxOptions.initSandboxVars @0–@60 L454–L463` · C · C-only.
27. `initSandboxVars` has no Java caller anywhere in the jar; the shipped `SandboxVars.lua` is its only call site on the install — `jar:jar-wide grep initSandboxVars` (1 hit, the declaring class) · C · C-only.
28. An admin's `sendToServer` sends the whole option list, the server applies it, calls `toLua()`, rewrites its sandbox file and rebroadcasts the raw buffer to every connection, so one apply updates `SandboxVars` on the server and on every connected client — `jar:SandboxOptions.sendToServer @0–@13 L1859–L1862`, `jar:GameClient.sendSandboxOptionsToServer @0–@31 L2753–L2761`, `jar:GameServer.receiveSandboxOptions @0–@105 L1735–L1747`, `jar:GameClient.receiveSandboxOptions @0–@30 L2766–L2772` · C · C-only.
29. The sandbox-options packet is gated on `Capability.SandboxOptions` through the packet authorization check, so an unprivileged client's send is dropped before the handler runs — `jar:PacketTypes$PacketAuthorization.isAuthorized @0–@36 L273`, `jar:PacketTypes$PacketType.<clinit> @1892–@1916` · C · C-only.
30. No Lua event fires when sandbox options change: `OnSandboxOptionsChanged`, `OnSandboxOptions`, `SandboxOptionsChanged`, `OnSandboxVars`, `SandboxChanged` and `OnSandboxChange` are each absent from every class entry in the jar, and `LuaEventManager`'s string pool holds no event name containing `Sandbox` — `jar:jar-wide grep` ×6 plus a full read of `LuaEventManager`'s UTF8 pool · C · C-only.
31. A dedicated server rewrites `<serverName>_SandboxVars.lua` on every boot whether or not the file already existed, so a file that predates a mod simply gains the mod's nested block at its declared defaults — `jar:GameServer.doMinimumInit @417–@498 L1500–L1511`, `jar:SandboxOptions.saveServerLuaFile @0–@17 L1447` · C · C-only.
32. An option missing from the server's sandbox file keeps its current value rather than being reset, because `fromTable` returns at once when the option's sub-table is absent — `jar:SandboxOptions$BooleanSandboxOption.fromTable @0–@35 L748–L753`, `jar:SandboxOptions.readLuaFile @233–@270 L1611–L1612` · C · C-only.
33. A server sandbox file that fails to load makes the server print the file's canonical path and exit 1, so a malformed mod block is a boot failure and not a silent default — `jar:GameServer.doMinimumInit @432–@451 L1501–L1503`, `jar:SandboxOptions.readLuaFile @297–@305 L1616–L1618` · C · C-only.
34. `writeLuaFile` groups options by table name and writes each mod prefix as a nested Lua table at four spaces with its short-named options at eight, string values quoted and escaped — `jar:SandboxOptions.writeLuaFile @94–@224 L1638–L1648`, `@505–@777 L1682–L1710`, `jar:StringConfigOption.getValueAsLuaString @0–@30 L82` · C · C-only.
35. Selecting a shipped sandbox preset never touches a mod option: `loadGameFile` runs the preset's Lua table through `fromTable`, and an option the table does not name is left alone — `jar:SandboxOptions.loadGameFile @0–@128 L1462–L1480` · C · C-only.
36. A mod option's "default" is the value its declaration file named, unchanged by the Apocalypse load that redefines every vanilla default in `SandboxOptions`' constructor — `jar:SandboxOptions.<init> @3022–@3056 L396–L405` · C · C-only.
37. The harness cannot set a mod sandbox option through a profile's `[sandbox]` block: the key pattern matches only four-space top-level keys and excludes a nested-table opener, so `sandbox_keys` never lists one, `check_sandbox` rejects the key, and a dotted key would be appended as invalid Lua — `tool:testing/pzt/server.py:91-99,108-139`, `tool:testing/pzt/profile.py:218-235` · C · C-only.

## Not read

- `SandboxOptions.applySettings()` — called on both sides right before `toLua()` on every arrival path; I did not dump it, so what it recomputes (and whether it can touch anything a mod option feeds) is unread.
- `ConnectionDetails.write`'s own caller chain beyond the grep that named `RequestDataPacket` and `RequestDataPacket$RequestID`; I read the field order out of `refs` and did not dump `write` itself or the request packet, so "one packet at join, requested by the client" is inferred from the read order in `Finish()` rather than dumped.
- `SandboxOptions.upgradeOptionName` and `upgradeOptionValue` — read only as call sites. Whether a mod prefix or short name can collide with a vanilla rename rule at a lower `VERSION` is unsettled, and so is whether `upgradeLuaTable`'s prefix-stripping `replace` can corrupt a mod key that contains the prefix string.
- `EnumSandboxOption.getValueTranslationByIndex` / `ByIndexOrNull` bodies, so the exact fallback when an enum value translation key is missing is unread (the comment-writing path catches an exception around it, which suggests it can throw).
- `ConfigOption.parse` and `setValueFromObject` bodies — so whether a value outside a mod option's declared `min`/`max` arriving over the wire or out of the server file is clamped, rejected or accepted is unread. This matters for a mod that ships a narrow range and then widens it.
- Whether a mod can ship its own `media/lua/shared/Sandbox/<Name>.lua` preset (or shadow `Apocalypse.lua`) through `activeFileMap`: `loadGameFile` uses `ZomboidFileSystem.getMediaFile`, which suggests it would resolve a mod's copy, but I did not read `getMediaFile` and did not test it. A shadowed `Apocalypse.lua` would be a serious cross-mod hazard and is worth its own reading.
- `ServerSettingsManager.getNameInSettingsFolder` — so the sandbox file's directory is taken from `GameServer.doMinimumInit`'s own path build and from the harness fixture's layout rather than from the settings manager itself.
- The `text` sandbox option type the admin-panel Lua branches on (`option:getType() == "text"`): no `CustomTextSandboxOption` exists, so a mod cannot declare one, but I did not establish which Java class produces it.
- No live run: every timing claim here is read off call order in bytecode. In particular "a file-scope value read gets the default" has never been observed on a booted session, and the harness is currently unable to set a mod option to make the two readings differ (§ D.1) — that is the first experiment this research implies.
- Corpus breadth: I read `SkillRecoveryJournal`, `MoreDifficultyB42` and `damnlib` in detail and scanned the other 100 files only for keys, prefixes, `VERSION` lines and comment style. The 86 `option X = {` lines and the 17 `common/media/` placements were counted, not individually opened.
