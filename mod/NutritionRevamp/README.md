# Nutrition Revamp — operator guide

Nutrition Revamp 1.0.0 is a realism nutrition overhaul for Project Zomboid Build 42 dedicated servers.
It tracks nutrients beyond the four vanilla macros, re-bases the vanilla foods' calories and macros on published food-composition data, and drives hunger, thirst, body weight, strength and a table of deficiency and excess effects from its own body model.
This guide is for the person running the server. The release notes are `CHANGELOG.md` and the neighbour mods are `COMPATIBILITY.md`, both beside this file.

## Install

- The mod id is `NutritionRevamp`. Add it to the server's `Mods=` line by that id, and add the Workshop item to the server's `WorkshopItems=` line.
- The server's mod list is the one that counts: a joining client loads what the server lists, whatever its own mod menu holds.
- The mod declares no dependency. MoodleFramework is optional: when a client has it, the mod's moodles use it; without it the mod draws its own icon column.
- The mod is built and tested for game build 42.20.4. Its folder has one version directory, `42.20.4/`, holding `mod.info` and the sandbox options, and `common/` holding everything else.
- A clean stop or restart loses at most the last real minute of each player's digestion drift, because the game gives a mod no save or stop event on a dedicated server, while eats, drinks and respawns are saved within a game minute.

## Set the vanilla Nutrition option off

Set the vanilla sandbox option `Nutrition = false` before the first boot. The mod owns the macro stores and body weight; with vanilla's nutrition update on, vanilla keeps subtracting from the calorie, carbohydrate, lipid and protein stores on its own clock and never adds to them, and rewrites the weight flags every tick. The mod's legacy mirror and its missed-intake reconciliation then see a drain they must not reconcile, and the two models fight over weight.

The mod never changes the option itself. When it finds the option on at boot it prints a warning line at every log level and its self-report reads `nutritionOn=true`.

## Sandbox options

Every option sits on the sandbox page `Nutrition Revamp` under the prefix `NR`.

| option | default | what it does |
|---|---|---|
| `NR.Mode` | 1 (Takeover) | How the mod drives the stats. Takeover: the mod replaces the vanilla stat update on the server through the `CalculateStats` hook. Overlay: the vanilla update runs and the mod writes after it. Choose Overlay when another mod claims the hook. |
| `NR.LogLevel` | 2 (Normal) | How much the mod prints to the server console: 1 Quiet (the self-report and warnings only), 2 Normal, 3 Verbose. |
| `NR.LegacyMirror` | true | On: every minute the server writes the vanilla calorie, protein, carbohydrate and lipid stores from the mod's trailing 24 hours, so vanilla code and other mods that read those stores keep working. Off: the mod leaves those stores alone. |
| `NR.OnsetSpeed` | 1.0 (0.5 to 30) | Multiplies how fast the slow deficiencies develop and recover (the nutrients that take more than 90 days to reach a clinical deficiency). 1.0 is real time. The fast nutrients, water, caffeine, alcohol, glycogen and sleep are never scaled. |
| `NR.DeficienciesCanKill` | true | On: the most severe states drain health until treated. Off: they never drain health. Hunger and thirst never reach vanilla's lethal top level either way. |
| `NR.ExcessEffectsOn` | true | On: an intake above a nutrient's upper limit raises that nutrient's excess level. Off: every excess level reads zero; intake is still tracked. |
| `NR.BalanceBonus` | true | On: while every tracked nutrient is replete, endurance regeneration and fatigue recovery run 5 percent faster. A game choice. |
| `NR.Severity` | 1.0 (0 to 3) | Scales every penalty a deficiency or an excess brings. 0 removes them all except the health drains, which `NR.DeficienciesCanKill` controls. |
| `NR.VisibilityMode` | 2 (Bands) | How much each player's interface shows: 1 Symptoms, 2 Bands, 3 Numbers. A character with the Nutritionist trait sees Numbers whatever the option. |

The server re-reads the options every in-game minute, so a change made while the server runs takes effect without a restart.

## Takeover and overlay

In takeover mode (the default) the mod installs the server's stat-update hook and runs the stat update itself for the stats it models, so a rate tuning made through `ZomboidGlobals` or the sandbox multipliers is followed by the mod's handler the same way, while a mod that writes a stat directly is read as an outside change; awake endurance stays vanilla's in this build. In overlay mode the vanilla stat update runs as usual and the mod writes its own values after it; choose it when another mod needs the hook. The self-report says which mode is running and whether the hook was installed.

## The self-report

At boot the server console prints one line, and each client console prints one when the player joins:

```
[NutritionRevamp] NutritionRevamp v1.0.0 build 42.20.4 side=server mode=takeover itemPass=true legacyMirror=on frameworks=n/a hook=true limitations=9 nutritionOn=false log=2
[NutritionRevamp] NutritionRevamp v1.0.0 build 42.20.4 side=client mode=takeover itemPass=true frameworks=MoodleFramework log=2
```

- `itemPass` is `true` when the mod's food values are loaded (it reads one food, the acorn, and compares its calories with the mod's value), `false` when the vanilla value or another mod's value won, and `unread` when the read could not be made.
- `legacyMirror` is the `NR.LegacyMirror` option. `frameworks` names MoodleFramework on a client that has it, else `none`; the server prints `n/a` because the framework is client-side.
- `hook` says whether the takeover hook was installed and `limitations` counts the known limitations this release's takeover hook ships with (9 in 1.0.0, the count of the handler's limitation list in this build); a different number means a different build of the mod. `nutritionOn=true` means the vanilla Nutrition option is on (see above).

When you report a bug that involves food, eating, weight or stats, paste both lines — the server's from the server console log and the client's from the player's `console.txt` — with the mod list. A large nutrition mod is the usual first suspect for an unrelated food bug, and the two lines settle most of those at once.

## When the mod does not load

The mod declares `versionMin=42.20.4` and no maximum. On a game build older than 42.20.4 the game treats the mod as absent: the log prints the same not-found line it prints for a mod folder that is not there, or for a missing dependency. When the mod does not load, read its `mod.info` and compare `versionMin` with the game build rather than trusting the log line. On a later build the `42.20.4/` directory stays in use until a release ships a newer one.

## Updates and the join checksum

The game hashes every script file a mod ships and compares the hashes when a client joins. Any update of this mod that changes a script file — its food values above all — is a server event:

1. Stop the server, update the mod on the server, start it.
2. Then let clients update. A client holding different script files than the server fails the join check until both hold the same release.

Never give a player a checksum-bypass role to get them in: the bypass skips the check but leaves the difference, and that player then plays on food values the server does not hold. The Lua files are hashed too (both clients printed a Lua checksum line at the join), and what that check does with a changed `.lua` file is unread, so treat any update that changes a `.lua` file as a server event as well until it is read. Each release's notes say whether it changes a script file.

## When another mod raises an error

A release client was tested with one mod that raises an error in an event handler, and the reading was one shape: the raising handler stops, and the handlers around it and the client go on. A client run with `-debug` stops in the Lua debugger instead, so a player on a release client does not see that stop.
