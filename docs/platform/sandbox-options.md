# Sandbox options
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: a mod's own sandbox options — the declaration file and its grammar, the `SandboxVars` mirror and the option's name, the translation keys and the settings pages, the join sync and when the values land relative to mod Lua, a change during a running session, and the server's own sandbox file; the vanilla options a reading depends on are stated on the pages they gate, and setting an option from a test profile is `harness.md`'s.

## Rules

- Read a sandbox value at event time, at `OnServerStarted`, `OnGameStart` or later, never at file scope: every mod Lua file runs before the operator's values reach `SandboxVars` on both sides, and `OnGameBoot` fires before them on a joining client [T12.39] [T12.21] [T12.22] [T12.23] [T12.25].
- Capture the sub-table, never a value, when a file must hold a reference at load time: `toTable` reuses the sub-table object and rewrites only its leaves, so a captured table sees every later value while a captured value keeps the declared default [T12.40] [T12.24] [T12.23].
- End every key and value pair in the declaration file with a comma, the last one before the closing brace included: the reader erases the newlines, and only a comma ends a value [T12.41] [T12.4].
- Never write `//` in the declaration file, and comment with `/* */` alone: the parser strips block comments only, so `//` text runs on into the next value [T12.42] [T12.5].
- Give every operator-settable option a `page`: an option without one gets no row on the settings pages the admin panel and the sandbox screen build, only a missing-setting warning [T12.43] [T12.18].
- Spell the prefix the same in the declaration file, every `SandboxVars` read and every `getOptionByName` call: the prefix is the Lua table name and part of the name-map key, and a clash on the full name raises no error [T12.44] [T12.12] [T12.13] [T12.15] [T12.16].
- Poll or re-read an option to follow a mid-session change: an admin apply rewrites `SandboxVars` on every side and fires no event, so a value the mod cached stays stale until it reads again [T12.45] [T12.28] [T12.30].

## How it works

<a id="declaration"></a>
### The declaration file

A mod declares its own options in one file, `media/sandbox-options.txt`, inside its version dir, or inside `common/` when the version dir ships no such file, and the loader reads exactly one of the two per mod [T12.1].
The version dir's copy wins outright: when it exists the `common/` copy is never opened, so a mod that ships both runs on the version dir's alone [T12.1].
A mod root's own `media/sandbox-options.txt` is never read on this build, because the loader builds only the version-dir and `common/` paths and `common/` resolves to `<modRoot>/common`, not to the mod root [T12.2].
A mod that ships its declaration only at the root, the older layout, therefore registers no options at all [T12.2].
Which folder counts as the version dir is the resolver [mod-anatomy.md](mod-anatomy.md#version-dirs) states [#0825/C/C-only].

The loader walks the resolved active mod list, which on a joining client is the server's mod list with the client's own translation-only mods added [T12.3].
A joining client therefore registers the options of the server's mods [T12.3].
Registration runs before any mod Lua, on both sides, as [the join timing](#sync) sets out [T12.21] [T12.22].

The reader concatenates the file's lines with no separator before `ScriptParser` sees them, so line breaks carry no meaning and a key and value pair ends only at a comma [T12.4].
A pair with no trailing comma runs into the next pair's text, and the last pair before a closing brace is dropped when it has none [T12.4].
Block layout is free for the same reason: one line per option and one line per key parse identically [T12.4].
Comments are stripped by `ScriptParser.stripComments`, which removes `/* */` and nothing else [T12.5].
A `//` is therefore ordinary text, and what follows it runs on to the next comma as part of a value [T12.5].
The file opens with `VERSION = 1,` at top level [T12.6].
A missing or different value raises `invalid or missing VERSION`, and every option in the file is lost [T12.6].
Every block after it must be typed `option`, compared case-insensitively, or the file raises `unknown block type` [T12.7].
The option id is the second whitespace token before the brace, and later tokens are discarded, so `option X = {` parses as `option X {` [T12.7].
The `type` key takes `boolean`, `double`, `enum`, `integer` or `string`, matched case-sensitively after a trim [T12.8].
Any other type warns `unknown option type` and drops that one option, while the rest of the file still loads [T12.8].

The keys each type needs, a missing one dropping the option with a `failed to parse custom sandbox option` warning [T12.9]:

| `type` | required | optional beyond `page` and `translation` | dropped when |
|---|---|---|---|
| `boolean` | `default` | — | `default` is absent |
| `integer` | `min`, `max`, `default` | — | any of the three is absent |
| `double` | `min`, `max`, `default` | — | any of the three is absent |
| `enum` | `numValues`, `default` | `valueTranslation` | `numValues` is not above zero, or the one-based `default` is not above zero |
| `string` | `default`, which may be empty | — | `default` is absent |

`page` and `translation` are the only keys the shared `parseCommon` reads, each trimmed and collapsed to null when blank [T12.10].
A declaration of `page =,` therefore declares no page at all, with the consequence [the settings pages](#translations) state [T12.10].
No per-type parse reads `description`, `tooltip` or `title`, so a block carrying them loads with those keys ignored, and an option's tooltip comes from a translation key instead [T12.10].
How many corpus blocks carry those ignored keys is a hand count, stated under [Open](#open).
A string option's `default` may contain `=`, because only the first `=` splits key from value [T12.11].
It can never contain a comma, because the comma ends the value [T12.11].
A list a string option carries therefore needs another separator, such as a semicolon [T12.11].

A declaration shaped by that grammar, read from the loader and not booted, every pair comma-terminated and every option on a page [T12.4] [T12.9]:

```
VERSION = 1,

/* one block per option; layout is free */
option MyMod.Enabled
{
    type = boolean,
    default = true,
    page = MyMod,
    translation = MyMod_Enabled,
}

option MyMod.OnsetDays
{
    type = double, min = 0.5, max = 365.0, default = 14.0,
    page = MyMod, translation = MyMod_OnsetDays,
}

option MyMod.Severity
{
    type = enum, numValues = 3, default = 2,
    page = MyMod, translation = MyMod_Severity, valueTranslation = MyMod_SeverityValues,
}
```

<a id="lua-mirror"></a>
### The `SandboxVars` mirror and the option's name

An option id with exactly one dot is split by `SandboxOptions.parseName` into a table name and a short name [T12.12].
Such an option mirrors into Lua as `SandboxVars.<tableName>.<shortName>`, one sub-table per prefix [T12.12].
An id with no dot, or with more than one, keeps its full name and mirrors flat into `SandboxVars` itself [T12.12].
A mod option is therefore read as `SandboxVars.MyMod.Opt`, and a two-dot id such as `MyMod.Group.Opt` does not nest twice [T12.12].
The prefix before the dot is free text and need not be the mod id: a corpus mod whose id is `MoreDifficultZonesB42` declares its options under `OnWeaponSwing` [T12.13].
The prefix is still the table name every reader must spell, in Lua and in the name map alike [T12.13].
How far the installed corpus follows the dotted convention is a hand count, stated under [Open](#open).

The Java name map is keyed on the full dotted name [T12.15].
`getSandboxOptions():getOptionByName("MyMod.Opt")` and `getSandboxOptions():set("MyMod.Opt", v)` therefore both resolve a mod option [T12.15].
`set` throws `IllegalArgumentException` on a name it does not know, so a misspelt name fails at the call rather than writing nothing [T12.15].

The Lua mirror is written by `toTable`, which looks up the option's sub-table in `SandboxVars`, reuses it when it is already a table, creates and stores a new one only when it is not, and then sets the leaf [T12.24].
A mod Lua file that captures the sub-table at file scope, `local sv = SandboxVars.MyMod`, therefore keeps seeing current values, because every later write lands on the same table object [T12.24].
A file that captures a leaf, `local v = SandboxVars.MyMod.Opt`, holds only what the leaf was at that moment, which is the declared default (see [the join timing](#sync)) [T12.23].

`SandboxVars` itself is built by the shipped `media/lua/shared/Sandbox/SandboxVars.lua`, which requires the Apocalypse preset table and then calls `initSandboxVars()` [T12.26].
That method reads each option out of the table and writes it straight back [T12.26].
A vanilla option therefore takes the preset's literal, while a mod option, which the preset does not name, is written out at its current Java value [T12.26].
`initSandboxVars` has no Java caller: the jar holds its name in its own class only, so that one Lua call is what writes the mod sub-tables into `SandboxVars` at load [T12.27].
A mod option's default is the value its declaration names, unchanged by the Apocalypse load that redefines every vanilla default in the `SandboxOptions` constructor [T12.36].
The declared default is thus what every read point before the operator's values returns, on either side [T12.36] [T12.23].

<a id="translations"></a>
### Translation keys and the settings pages

An option's label key is `Sandbox_<translation>`, or `Sandbox_<shortName>` when the declaration gives no `translation` [T12.17].
Its tooltip key is `Sandbox_<translation>_tooltip`, read through `getTextOrNull`, so a tooltip is optional [T12.17].
An enum's value labels are `Sandbox_<valueTranslation>_option<N>`, counting from one to `numValues` [T12.17].
The page's own label is `Sandbox_<page>`, which the settings screen reads through `getText` [T12.17].
Where a mod's translation files sit, and how they merge with vanilla's, is [mod-anatomy.md](mod-anatomy.md#translations)'s.

The admin panel and the sandbox screen both build their pages from one settings table, into which the shipped settings screen appends a row for every custom option that names a page [T12.18].
A custom option whose `page` is null gets no row on any of those pages [T12.18].
A client or server prints `WARN:MISSING in SettingsTable: <name>` for such an option instead [T12.18].
`page` is therefore in practice mandatory for any option an operator is meant to set, and an option left without one is still registered, synced and readable from Lua [T12.18] [T12.19].
A blank `page =,` counts as no page, as [the declaration](#declaration) states [T12.10].

<a id="sync"></a>
### The join sync and when the values land

The server writes its entire sandbox option list into the connection-details blob as name and value strings [T12.19].
A custom option is an ordinary member of that list, so a mod option reaches a joining client with no work from the mod [T12.19].
A client that receives a name it does not have logs `unknown SandboxOption` and skips it rather than failing the join [T12.20].
Where that blob sits among the other packets of the join is [mp-model.md](mp-model.md#packets)'s, and the join as a whole is [server-lifecycle.md](server-lifecycle.md)'s.

The order of the join decides what a mod's Lua sees [T12.21].
On a joining client `Finish()` calls `receiveServerOptions`, which runs the whole of `Core.ResetLua` [T12.21].
That reset covers the mod load, the custom-option registration, `SandboxVars.lua`, every mod Lua file at file scope, and the `OnGameBoot`, `OnMainMenuEnter` and `OnResetLua` events [T12.21].
Only after it does `Finish()` call `receiveSandboxOptions`, whose `toLua()` writes the server's values into `SandboxVars` [T12.21].
On a dedicated server all three `LuaManager.LoadDirBase` passes run before the server reads its sandbox file and before its `toLua()` [T12.22].
Mod Lua file scope therefore precedes the operator's values on the server too [T12.22].
A mod Lua file that reads a sandbox value at file scope gets the mod's declared default on the server and on every joining client, never the operator's setting [T12.23].
`OnGameBoot` fires after the values land on a dedicated server and before them on a joining client, so it is not a symmetric read point [T12.25].
`OnServerStarted` and `OnGameStart` both fire after the values land [T12.25].

What each read point returns, by side [T12.23] [T12.24] [T12.25]:

| read | joining client | dedicated server |
|---|---|---|
| a value at file scope | the declared default | the declared default |
| the sub-table at file scope, its leaf read later | the server's value | the file's value |
| a value in an `OnGameBoot` handler | the declared default | the file's value |
| a value at `OnGameStart` (client) or `OnServerStarted` (server), or any later event | the server's value | the file's value |

<a id="runtime-change"></a>
### A change during a running session

`SandboxOptions.set(String,Object)` writes only the local option object, and a changed option reaches the server through `SandboxOptions.sendToServer()`, the route the admin panel takes [#0092].
The Lua mirror of a vanilla option read stale after a runtime set of the Java option on a client [#0091/M/n=1].
On a running dedicated server a set applies to the server's own option at once with no push [#0556/M/n=1].
An admin's `sendToServer` sends the whole option list, and the server applies it, calls `toLua()`, rewrites its sandbox file and rebroadcasts the raw buffer to every connection [T12.28].
Each client then applies the buffer and calls its own `toLua()` [T12.28].
One apply therefore updates `SandboxVars` on the server and on every connected client, mod options included [T12.28].
The packet type requires `Capability.SandboxOptions` [T12.29].
The packet authorization check passes a connection only when its role holds the packet's required capability, so a connection without that capability is refused [T12.29].
Nothing announces the change to Lua, because the engine has no event for it ([Walls and bounds](#walls)) [T12.30].
A mod that cached a value therefore keeps the old one until it reads again, and a captured sub-table is the one reference the apply refreshes in place [T12.30] [T12.24].
Whether the Lua mirror follows an admin push on a live server is the measurement [Open](#open) names.

<a id="server-file"></a>
### The server's sandbox file

A dedicated server rewrites `<serverName>_SandboxVars.lua` on every boot, whether or not the file already existed [T12.31].
A file that predates a mod therefore gains the mod's nested block at its declared defaults, and nothing needs editing by hand before the first boot [T12.31].
An option missing from that file keeps its current value rather than being reset, because `fromTable` returns at once when the option's sub-table is absent [T12.32].
A server sandbox file that fails to load makes the server print the file's canonical path and call `System.exit(1)` [T12.33].
A malformed mod block in that file is therefore a boot failure and not a silent default [T12.33].
The writer groups options by table name and writes each mod prefix as a nested Lua table at four spaces, with its short-named options at eight [T12.34].
String values are quoted and escaped [T12.34].
Selecting a shipped sandbox preset never touches a mod option: `loadGameFile` runs the preset's Lua table through `fromTable`, and an option the table does not name is left alone [T12.35].
A mod option's shipped default therefore survives any preset the operator picks [T12.35] [T12.36].
Setting a mod option from a test profile is a separate matter: the profile's sandbox block cannot reach a nested table ([harness.md](harness.md#sandbox)) [T12.37].

The shape of a mod's block in the written file, read off the writer and not booted [T12.34]:

```lua
SandboxVars = {
    ...
    MyMod = {
        Enabled = true,
        OnsetDays = 14.0,
        Label = "text",
    },
}
```

## Walls and bounds
<a id="walls"></a>

The engine has no Lua event for a sandbox option change: `OnSandboxOptionsChanged`, `OnSandboxOptions`, `SandboxOptionsChanged`, `OnSandboxVars`, `SandboxChanged` and `OnSandboxChange` are each absent from every class in the jar, and `LuaEventManager` holds no string containing `Sandbox` [T12.30].
The engine does not reject a duplicate option name: `addOption` keeps both options in its list and the last in its name map, so two mods declaring the same prefix and short name collide silently [T12.16].
Every timing statement on this page is read off call order in the bytecode and has not been observed on a booted session, the file-scope default included [T12.23].
A profile's sandbox block cannot set a mod's own option, and the remedy is the decision under [Open](#open) [T12.37].
Not covered: `SandboxOptions.applySettings()`, which runs before every `toLua()` on each arrival path; the connection-details request chain beyond its read order; the option-name and value upgrade rules and whether a mod name can collide with one; the enum value-label fallback when a key is missing; whether a value outside a mod option's declared `min` and `max`, arriving over the wire or out of the server file, is clamped, rejected or kept; whether a mod can ship or shadow a preset such as `Apocalypse.lua`; the settings manager's own folder resolution for the server file; the `text` option type the admin panel branches on; any other declaration filename; and any other Java writer of `SandboxVars` — this library read none of them.

## Open
<a id="open"></a>

- Whether a runtime flip of a sandbox option from Lua takes effect, and whether the Lua mirror follows an admin push on a live server, is unmeasured — settled by one session reading the Java option, the Lua mirror and the gated behaviour beside a no-flip control; -> [X17](../areas/open-questions.md#x17) [#1283/C/open] [#0140/C/open].
- That all 1308 `option` lines across the 103 installed `sandbox-options.txt` files use a dotted id is unverified: the count is a hand scan of the installed workshop tree whose output is not a committed dataset, and the dated inventory counts dotted lines in each mod's live file only; re-measure by a committed sweep that counts every option line, dotted or not, in every tree a mod ships [T12.14].
- That 380 option blocks in the installed corpus carry a `description` key, 65 a `tooltip` key and 2 a `title` key is unverified: the counts are a hand scan whose output is not a committed dataset; re-measure by a committed sweep that counts each key per option block [T12.38].
- Decision: how the mod's own tests set its options — a merge that writes a profile's nested block into the mod's table in the server file, a two-pass run that boots once so the server writes the block and then merges into it, or a live set through the bus after boot, which cannot give the value to a consumer that reads at `OnServerStarted` — forced by the profile block's top-level-only key pattern [T12.37]; the harness change lands before any run that sets a mod option.
- Decision: whether the mod reads each option at use time or caches it at `OnServerStarted` and `OnGameStart` with a re-read on a cadence — forced by the file-scope default [T12.23] and the missing change event [T12.30].

## See also

- [`mod-anatomy.md`](mod-anatomy.md) — the version dir and `common/` the declaration file sits in, and where a mod's translation files go.
- [`lua-platform.md`](lua-platform.md#events) — the events a mod reads its options from.
- [`mp-model.md`](mp-model.md) — what crosses the wire at the join and after it.
- [`server-lifecycle.md`](server-lifecycle.md) — the join and the boot this page's timing sits inside.
- [`harness.md`](harness.md#sandbox) — the profile's sandbox block and what it can set.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#sandbox) — the vanilla `Nutrition` option and its runtime flip.
- [`../areas/testing-your-mod.md`](../areas/testing-your-mod.md#sandbox) — the fixture's sandbox values the mod's tests run on.
- [`../areas/open-questions.md`](../areas/open-questions.md#x17) — `X17`, the runtime-flip experiment.
