# Sandbox options
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: a mod's own sandbox options — the declaration file and its grammar, the `SandboxVars` mirror and the option's name, the translation keys and the settings pages, the join sync and when the values land relative to mod Lua, a change during a running session, and the server's own sandbox file; the vanilla options a reading depends on are stated on the pages they gate, and setting an option from a test profile is `harness.md`'s.

## Rules

- Read a sandbox value at event time, at `OnServerStarted`, `OnGameStart` or later, never at file scope: every mod Lua file runs before the operator's values reach `SandboxVars` on both sides, and `OnGameBoot` fires before them on a joining client [#2460/C/inference] [#2442/C/C-only] [#2443/C/C-only] [#2444/C/C-only] [#2446/C/C-only].
- Capture the sub-table, never a value, when a file must hold a reference at load time: `toTable` reuses the sub-table object and rewrites only its leaves, so a captured table sees every later value while a captured value keeps the declared default [#2461/C/inference] [#2445/C/C-only] [#2444/C/C-only].
- End every key and value pair in the declaration file with a comma, the last one before the closing brace included: the reader erases the newlines, and only a comma ends a value [#2462/C/inference] [#2425/C/C-only].
- Never write `//` in the declaration file, and comment with `/* */` alone: the parser strips block comments only, so `//` text runs on into the next value [#2463/C/inference] [#2426/C/C-only].
- Give every operator-settable option a `page`: an option without one gets no row on the settings pages the admin panel and the sandbox screen build, only a missing-setting warning [#2464/C/inference] [#2439/C/C-only].
- Spell the prefix the same in the declaration file, every `SandboxVars` read and every `getOptionByName` call: the prefix is the Lua table name and part of the name-map key, and a clash on the full name raises no error [#2465/C/inference] [#2433/C/C-only] [#2434/C/C-only] [#2436/C/C-only] [#2437/C/C-only].
- Poll or re-read an option to follow a mid-session change: an admin apply rewrites `SandboxVars` on every side and fires no event, so a value the mod cached stays stale until it reads again [#2466/C/inference] [#2449/C/C-only] [#2451/C/C-only].

## How it works

<a id="declaration"></a>
### The declaration file

A mod declares its own options in one file, `media/sandbox-options.txt`, inside its version dir, or inside `common/` when the version dir ships no such file, and the loader reads exactly one of the two per mod [#2422/C/C-only].
The version dir's copy wins outright: when it exists the `common/` copy is never opened, so a mod that ships both runs on the version dir's alone [#2422/C/C-only].
A mod root's own `media/sandbox-options.txt` is never read on this build, because the loader builds only the version-dir and `common/` paths and `common/` resolves to `<modRoot>/common`, not to the mod root [#2423/C/C-only].
A mod that ships its declaration only at the root, the older layout, therefore registers no options at all [#2423/C/C-only].
Which folder counts as the version dir is the resolver [mod-anatomy.md](mod-anatomy.md#version-dirs) states [#0825/C/C-only].

The loader walks the resolved active mod list, which on a joining client is the server's mod list with the client's own translation-only mods added [#2424/C/C-only].
A joining client therefore registers the options of the server's mods [#2424/C/C-only].
Registration runs before any mod Lua, on both sides, as [the join timing](#sync) sets out [#2442/C/C-only] [#2443/C/C-only].

The reader concatenates the file's lines with no separator before `ScriptParser` sees them, so line breaks carry no meaning and a key and value pair ends only at a comma [#2425/C/C-only].
A pair with no trailing comma runs into the next pair's text, and the last pair before a closing brace is dropped when it has none [#2425/C/C-only].
Block layout is free for the same reason: one line per option and one line per key parse identically [#2425/C/C-only].
Comments are stripped by `ScriptParser.stripComments`, which removes `/* */` and nothing else [#2426/C/C-only].
A `//` is therefore ordinary text, and what follows it runs on to the next comma as part of a value [#2426/C/C-only].
The file opens with `VERSION = 1,` at top level [#2427/C/C-only].
A missing or different value raises `invalid or missing VERSION`, and every option in the file is lost [#2427/C/C-only].
Every block after it must be typed `option`, compared case-insensitively, or the file raises `unknown block type` [#2428/C/C-only].
The option id is the second whitespace token before the brace, and later tokens are discarded, so `option X = {` parses as `option X {` [#2428/C/C-only].
The `type` key takes `boolean`, `double`, `enum`, `integer` or `string`, matched case-sensitively after a trim [#2429/C/C-only].
Any other type warns `unknown option type` and drops that one option, while the rest of the file still loads [#2429/C/C-only].

The keys each type needs, a missing one dropping the option with a `failed to parse custom sandbox option` warning [#2430/C/C-only]:

| `type` | required | optional beyond `page` and `translation` | dropped when |
|---|---|---|---|
| `boolean` | `default` | — | `default` is absent |
| `integer` | `min`, `max`, `default` | — | any of the three is absent |
| `double` | `min`, `max`, `default` | — | any of the three is absent |
| `enum` | `numValues`, `default` | `valueTranslation` | `numValues` is not above zero, or the one-based `default` is not above zero |
| `string` | `default`, which may be empty | — | `default` is absent |

`page` and `translation` are the only keys the shared `parseCommon` reads, each trimmed and collapsed to null when blank [#2431/C/C-only].
A declaration of `page =,` therefore declares no page at all, with the consequence [the settings pages](#translations) state [#2431/C/C-only].
No per-type parse reads `description`, `tooltip` or `title`, so a block carrying them loads with those keys ignored, and an option's tooltip comes from a translation key instead [#2431/C/C-only].
How many corpus blocks carry those ignored keys is a hand count, stated under [Open](#open).
A string option's `default` may contain `=`, because only the first `=` splits key from value [#2432/C/C-only].
It can never contain a comma, because the comma ends the value [#2432/C/C-only].
A list a string option carries therefore needs another separator, such as a semicolon [#2432/C/C-only].

A declaration shaped by that grammar, read from the loader and not booted, every pair comma-terminated and every option on a page [#2425/C/C-only] [#2430/C/C-only]:

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

An option id with exactly one dot is split by `SandboxOptions.parseName` into a table name and a short name [#2433/C/C-only].
Such an option mirrors into Lua as `SandboxVars.<tableName>.<shortName>`, one sub-table per prefix [#2433/C/C-only].
An id with no dot, or with more than one, keeps its full name and mirrors flat into `SandboxVars` itself [#2433/C/C-only].
A mod option is therefore read as `SandboxVars.MyMod.Opt`, and a two-dot id such as `MyMod.Group.Opt` does not nest twice [#2433/C/C-only].
The prefix before the dot is free text and need not be the mod id: a corpus mod whose id is `MoreDifficultZonesB42` declares its options under `OnWeaponSwing` [#2434/C/C-only].
The prefix is still the table name every reader must spell, in Lua and in the name map alike [#2434/C/C-only].
How far the installed corpus follows the dotted convention is a hand count, stated under [Open](#open).

The Java name map is keyed on the full dotted name [#2436/C/C-only].
`getSandboxOptions():getOptionByName("MyMod.Opt")` and `getSandboxOptions():set("MyMod.Opt", v)` therefore both resolve a mod option [#2436/C/C-only].
`set` throws `IllegalArgumentException` on a name it does not know, so a misspelt name fails at the call rather than writing nothing [#2436/C/C-only].

The Lua mirror is written by `toTable`, which looks up the option's sub-table in `SandboxVars`, reuses it when it is already a table, creates and stores a new one only when it is not, and then sets the leaf [#2445/C/C-only].
A mod Lua file that captures the sub-table at file scope, `local sv = SandboxVars.MyMod`, therefore keeps seeing current values, because every later write lands on the same table object [#2445/C/C-only].
A file that captures a leaf, `local v = SandboxVars.MyMod.Opt`, holds only what the leaf was at that moment, which is the declared default (see [the join timing](#sync)) [#2444/C/C-only].

`SandboxVars` itself is built by the shipped `media/lua/shared/Sandbox/SandboxVars.lua`, which requires the Apocalypse preset table and then calls `initSandboxVars()` [#2447/C/C-only].
That method reads each option out of the table and writes it straight back [#2447/C/C-only].
A vanilla option therefore takes the preset's literal, while a mod option, which the preset does not name, is written out at its current Java value [#2447/C/C-only].
`initSandboxVars` has no Java caller: the jar holds its name in its own class only, so that one Lua call is what writes the mod sub-tables into `SandboxVars` at load [#2448/C/C-only].
A mod option's default is the value its declaration names, unchanged by the Apocalypse load that redefines every vanilla default in the `SandboxOptions` constructor [#2457/C/C-only].
The declared default is thus what every read point before the operator's values returns, on either side [#2457/C/C-only] [#2444/C/C-only].

<a id="translations"></a>
### Translation keys and the settings pages

An option's label key is `Sandbox_<translation>`, or `Sandbox_<shortName>` when the declaration gives no `translation` [#2438/C/C-only].
Its tooltip key is `Sandbox_<translation>_tooltip`, read through `getTextOrNull`, so a tooltip is optional [#2438/C/C-only].
An enum's value labels are `Sandbox_<valueTranslation>_option<N>`, counting from one to `numValues` [#2438/C/C-only].
The page's own label is `Sandbox_<page>`, which the settings screen reads through `getText` [#2438/C/C-only].
Where a mod's translation files sit, and how they merge with vanilla's, is [mod-anatomy.md](mod-anatomy.md#translations)'s.

The admin panel and the sandbox screen both build their pages from one settings table, into which the shipped settings screen appends a row for every custom option that names a page [#2439/C/C-only].
A custom option whose `page` is null gets no row on any of those pages [#2439/C/C-only].
A client or server prints `WARN:MISSING in SettingsTable: <name>` for such an option instead [#2439/C/C-only].
`page` is therefore in practice mandatory for any option an operator is meant to set, and an option left without one is still registered, synced and readable from Lua [#2439/C/C-only] [#2440/C/C-only].
A blank `page =,` counts as no page, as [the declaration](#declaration) states [#2431/C/C-only].

<a id="sync"></a>
### The join sync and when the values land

The server writes its entire sandbox option list into the connection-details blob as name and value strings [#2440/C/C-only].
A custom option is an ordinary member of that list, so a mod option reaches a joining client with no work from the mod [#2440/C/C-only].
A client that receives a name it does not have logs `unknown SandboxOption` and skips it rather than failing the join [#2441/C/C-only].
Where that blob sits among the other packets of the join is [mp-model.md](mp-model.md#packets)'s, and the join as a whole is [server-lifecycle.md](server-lifecycle.md#join)'s.

The order of the join decides what a mod's Lua sees [#2442/C/C-only].
On a joining client `Finish()` calls `receiveServerOptions`, which runs the whole of `Core.ResetLua` [#2442/C/C-only].
That reset covers the mod load, the custom-option registration, `SandboxVars.lua`, every mod Lua file at file scope, and the `OnGameBoot`, `OnMainMenuEnter` and `OnResetLua` events [#2442/C/C-only].
Only after it does `Finish()` call `receiveSandboxOptions`, whose `toLua()` writes the server's values into `SandboxVars` [#2442/C/C-only].
On a dedicated server the custom options register before all three `LuaManager.LoadDirBase` passes, which run before the server reads its sandbox file and before its `toLua()` [#2443/C/C-only].
Mod Lua file scope therefore precedes the operator's values on the server too [#2443/C/C-only].
A mod Lua file that reads a sandbox value at file scope gets the mod's declared default on the server and on every joining client, never the operator's setting [#2444/C/C-only].
`OnGameBoot` fires after the values land on a dedicated server and before them on a joining client, so it is not a symmetric read point [#2446/C/C-only].
`OnServerStarted` and `OnGameStart` both fire after the values land [#2446/C/C-only].

What each read point returns, by side [#2444/C/C-only] [#2445/C/C-only] [#2446/C/C-only]:

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
An admin's `sendToServer` sends the whole option list, and the server applies it, calls `toLua()`, rewrites its sandbox file and rebroadcasts the raw buffer to every connection [#2449/C/C-only].
Each client then applies the buffer and calls its own `toLua()` [#2449/C/C-only].
One apply therefore updates `SandboxVars` on the server and on every connected client, mod options included [#2449/C/C-only].
The packet type requires `Capability.SandboxOptions` [#2450/C/C-only].
The server's packet dispatch runs a packet's handler only when the authorization check passes, which it does only when the connection's role holds the packet's required capability, so a sandbox-options packet from a connection without that capability reaches no handler [#2450/C/C-only].
Nothing announces the change to Lua, because the engine has no event for it ([Walls and bounds](#walls)) [#2451/C/C-only].
A mod that cached a value therefore keeps the old one until it reads again, and a captured sub-table is the one reference the apply refreshes in place [#2451/C/C-only] [#2445/C/C-only].
A server `SandboxOptions:set` changes the option object but not `SandboxVars`, so a mod that polls `SandboxVars` never sees it [#2887/M/n=1].
A server Lua assignment into the nested `SandboxVars` leaf reaches a mod that polls it [#2914/M/n=1].
A `SandboxVars` leaf assigned on the server is read live by a per-tick reader within seconds [#2969/M/n=1].
Whether the Lua mirror follows an admin push on a live server is the measurement [Open](#open) names.

<a id="server-file"></a>
### The server's sandbox file

A dedicated server rewrites `<serverName>_SandboxVars.lua` on every boot, whether or not the file already existed [#2452/C/C-only].
A file that predates a mod therefore gains the mod's nested block at its declared defaults, and nothing needs editing by hand before the first boot [#2452/C/C-only].
An option missing from that file keeps its current value rather than being reset, because `fromTable` returns at once when the option's sub-table is absent [#2453/C/C-only].
A server sandbox file that fails to load makes the server print the file's canonical path and call `System.exit(1)` [#2454/C/C-only].
A malformed mod block in that file is therefore a boot failure and not a silent default [#2454/C/C-only].
The writer groups options by table name and writes each mod prefix as a nested Lua table at four spaces, with its short-named options at eight [#2455/C/C-only].
String values are quoted and escaped [#2455/C/C-only].
Selecting a shipped sandbox preset never touches a mod option: `loadGameFile` runs the preset's Lua table through `fromTable`, and an option the table does not name is left alone [#2456/C/C-only].
A mod option's shipped default therefore survives any preset the operator picks [#2456/C/C-only] [#2457/C/C-only].
Setting a mod option from a test profile is a separate matter: the profile's nested `[sandbox.<Prefix>]` table reaches it ([harness.md](harness.md#sandbox)) [#2807/M/n=1].

The shape of a mod's block in the written file, read off the writer and not booted [#2455/C/C-only]:

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

The engine has no Lua event for a sandbox option change: `OnSandboxOptionsChanged`, `OnSandboxOptions`, `SandboxOptionsChanged`, `OnSandboxVars`, `SandboxChanged` and `OnSandboxChange` are each absent from every class in the jar, and `LuaEventManager` holds no string containing `Sandbox` [#2451/C/C-only].
The engine does not reject a duplicate option name: `addOption` keeps both options in its list and the last in its name map, so two mods declaring the same prefix and short name collide silently [#2437/C/C-only].
Every timing statement on this page is read off call order in the bytecode and has not been observed on a booted session, the file-scope default included [#2444/C/C-only].
A profile's nested `[sandbox.<Prefix>]` table sets a mod's own option, so a test needs no re-provisioned fixture for it [#2807/M/n=1].
Not covered: `SandboxOptions.applySettings()`, which runs before every `toLua()` on each arrival path; the connection-details request chain beyond its read order; the option-name and value upgrade rules and whether a mod name can collide with one; the enum value-label fallback when a key is missing; whether a value outside a mod option's declared `min` and `max`, arriving over the wire or out of the server file, is clamped, rejected or kept; whether a mod can ship or shadow a preset such as `Apocalypse.lua`; the settings manager's own folder resolution for the server file; the `text` option type the admin panel branches on; any other declaration filename; and any other Java writer of `SandboxVars` — this library read none of them.

## Open
<a id="open"></a>

- Whether a runtime flip of a sandbox option from Lua takes effect, and whether the Lua mirror follows an admin push on a live server, is unmeasured — settled by one session reading the Java option, the Lua mirror and the gated behaviour beside a no-flip control; -> [X17](../areas/open-questions.md#x17) [#1283/C/open] [#0140/C/C-only/open].
- That all 1308 `option` lines across the 103 installed `sandbox-options.txt` files use a dotted id is unverified: the count is a hand scan of the installed workshop tree whose output is not a committed dataset, and the dated inventory counts dotted lines in each mod's live file only; re-measure by a committed sweep that counts every option line, dotted or not, in every tree a mod ships [#2435/C/snapshot/unverified].
- That 380 option blocks in the installed corpus carry a `description` key, 65 a `tooltip` key and 2 a `title` key is unverified: the counts are a hand scan whose output is not a committed dataset; re-measure by a committed sweep that counts each key per option block [#2459/C/snapshot/unverified].
- Decision: whether the mod reads each option at use time or caches it at `OnServerStarted` and `OnGameStart` with a re-read on a cadence — forced by the file-scope default [#2444/C/C-only] and the missing change event [#2451/C/C-only].

## See also

- [`mod-anatomy.md`](mod-anatomy.md) — the version dir and `common/` the declaration file sits in, and where a mod's translation files go.
- [`lua-platform.md`](lua-platform.md#events) — the events a mod reads its options from.
- [`mp-model.md`](mp-model.md) — what crosses the wire at the join and after it.
- [`server-lifecycle.md`](server-lifecycle.md) — the join and the boot this page's timing sits inside.
- [`harness.md`](harness.md#sandbox) — the profile's sandbox block and what it can set.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#sandbox) — the vanilla `Nutrition` option and its runtime flip.
- [`../areas/testing-your-mod.md`](../areas/testing-your-mod.md#sandbox) — the fixture's sandbox values the mod's tests run on.
- [`../areas/open-questions.md`](../areas/open-questions.md#x17) — `X17`, the runtime-flip experiment.
