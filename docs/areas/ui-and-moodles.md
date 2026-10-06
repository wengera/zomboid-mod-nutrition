# UI and moodles — what a nutrition mod can show a player
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the nutrition-design reading of the display surfaces — a moodle as a client widget through `MoodleFramework` or the mod's own, the moodle level a stat value reaches, a client panel, a tooltip line, a character-info tab and translation text — what each costs and which wall it hits, how often a client-side reader should read, how the trait list reaches a client, and why a displayed number can be honest and still wrong; the widget toolkit and its wrap points are `platform/client-ui.md`, the moodle and trait registries `platform/lua-platform.md`, the translation tables `platform/mod-anatomy.md` and the packet contents `facts/wire-packets.md`

## Rules

- Cache a nutrition value at the push cadence rather than the frame cadence: the source changes once a second and the measured arrivals show it, while a viewer's read count is the viewer's own and drifts with its version, the arrivals measured in one session [#2692/M/n=1] [#2524/C/C-only].
- Never register a moodle type of your own through the vanilla registry: a registered type reaches every character and is driven back to its lowest level every tick, and a duplicate id corrupts the registry before the call throws [#1140/C/C-only, #2060/C/inference].
- Register with a framework that already owns a contested value rather than writing that value last: cooperative detection avoids last-write-wins between two mods that both own carry weight or moodles [#1070/C/snapshot].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Test a Java class against the exposer's class set before you plan on it: the exposure test is a strict membership test, so a class the jar carries and the exposer does not register is unreachable [#0963/C/C-only].
- Put a protected call at every engine and third-party boundary: it keeps your own handler body running, which the survival of the handlers behind you does not give you [#0944/M/n=1, #0948/M/n=1].
- Keep a raising call out of a client launched with the debug flag: the failure helper's debug arm enters the modal break and the process never answers again, on two boots out of two [#0954/M/n=2, #0955/C/C-only].
- Take a client-side moodle read at least one push after a server-side stat write: the moodle recompute has no side guard, so the client recomputes from a mirror that can lag by a push [#0570/C/C-only].
- Derive a client-side value from packet-carried inputs only with its dependency list written down and each input checked against the packet's field list: a derived value is desync-free only while every input is carried faithfully, a cooked food's thirst change and a zero-valued conditionally-written item field are not, and the weight-band traits arrive only on the experience and trait-block pushes, as of the last push [#1508, #2731/C/inference] [#0567] [#2595/C/C-only] [#1146/M/n=1] [#1147/M/n=1].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or push the trait list after you write it as [the trait-push rule](../areas/mp-sync.md#rules) says: the band traits are not in the player-stats packet; they reach the affected player's client on the player-fields packet's trait block and on the timed experience packet, each as fresh as its last push, and no player-addressed push refreshes another client's copy [#2727/C/inference] [#2595/C/C-only] [#2606/C/C-only] [#2603/C/C-only] [#2612/C/C-only].
- Compare a trait by the registry object and never by its name: the name getter answers lowercased, so a string comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].
- Read a food's numbers from the side that owns them and never build mod math on a getter whose value is transformed again on the wire: the item packet sends a cooked food's derived thirst getter and the receiver stores it as the raw field [#1084/M/n=2].
- Treat a client's freshness display as arbitrarily stale: it is whatever the last full serialisation of the item said, and nothing re-sends the age until the item is serialised whole again [#0357/C/inference].
- Ship a mod's item names in a B42 `ItemName.json` whose keys are the bare `Module.Name`: the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
- Expect a mod translation to add keys rather than replace them: the reader merges into a shared map, so vanilla's keys survive beside the mod's [#0841/C/C-only].
- Never branch on an item's display name server-side or reach for one through `getText`: a dedicated server resolves no mod display name and the text router carries no item-name prefix [#1026/M/n=2].

## How it works

A nutrition overhaul tracks more than vanilla shows, and everything it shows has to reach the player through a surface the engine already draws or one the mod draws itself.
This page owns no mechanism of those surfaces: it reads the registries, the widget toolkit, the packets and the translation tables owned by the pages below it, and states what each reading means for a display.
The moodle surface is decided by the registries and by the widget a mod draws, a client panel by the packets its numbers travel on, and text by the translator.
The five readings below take the moodle, the level a stat value reaches, the panel's read cadence and the trait list a label rests on in turn, and then the failure all of them share; the panel, tooltip, tab and icon-column shapes and the text surface are costed under [Options](#surface-options).

<a id="moodle-route"></a>
### A moodle is a client widget, drawn by `MoodleFramework` or by the mod

A moodle is the surface a player already reads for hunger and thirst, and it is the only one of the three that acts as well as shows: a vanilla moodle's level feeds carry capacity, health regeneration and the severe-level health loss ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)).
That is what makes a moodle attractive for a new nutrient, and it is also the surface this build closes hardest in the engine while leaving it open in Lua.

A mod could reach a moodle through the vanilla registry in two ways, and what each is worth is settled on the platform page rather than here ([lua-platform.md#registries](../platform/lua-platform.md#registries)).
A moodle type the mod registers itself succeeds, reaches every character and is then held at its lowest level every tick, so the door leads nowhere [#1140/C/C-only].
Retuning a vanilla moodle is closed from the other side, because the class that holds every threshold cannot be reached from Lua [#1141/C/C-only].
Both are readings of this build's bytecode rather than failed attempts: nothing in this library has registered a moodle type or called a threshold setter [#0969/C/C-only, #2040/C/C-only].
With both registry doors closed, a moodle a mod adds is a Lua widget drawn beside the vanilla stack, and the wall map's verdict on that route is [wall-map.md#d4](../reference/wall-map.md#d4) [#2555/C/inference].
The vanilla stack offers no seat for one: the Java moodle panel has no add, insert or register call and every helper it has takes a registered type, so whatever a mod adds is drawn beside the stack and never inside it [#2554/C/C-only].
A mod that calls the vanilla registration anyway buys nothing a player can see and puts the registry's shared state at risk, which is the rule against it above [#1198/C/C-only].

One moodle move is left to a mod without any widget, and it is a way of acting rather than of showing.
A mod can drive a vanilla moodle by moving the stat behind it on the server, and the moodle then means exactly what vanilla says it means, while the class that would let it mean anything else stays out of reach ([#0568/M/n=2], [#1141/C/C-only]).
That puts the nutrient's effect in front of the player as hunger or thirst and never puts the nutrient itself there.
Where the stat is written decides nothing about where the moodle is computed: each side recomputes its own moodles from its own copy of the stats, and nothing about a moodle crosses the wire [#1143/C/C-only].
A client-side moodle is therefore exactly as late as the client's stats, which is what the rule on reading a moodle one push after a write is for.

`MoodleFramework` is a client widget library and not a registry wrapper: it registers no engine moodle type, its moodles are plain `ISUIElement` widgets, and so neither the pinned level nor the registry's duplicate-id hazard reaches them ([#2531/C/C-only], [#1198/C/C-only]).
Its whole surface is a create call that takes only a name and an access call that returns the widget for a player number, and everything else is set on the instance the access call returns [#2532/C/C-only].
A framework moodle's level and polarity are derived from one stored value against a threshold table, so a consumer controls a moodle through one float and never through a level [#2533/C/C-only].
The framework clamps nothing, so the consumer keeps its value inside the framework's convention before the call [#2535/C/C-only].
A moodle that is registered and never set renders nothing, because the widget joins the UI manager only while its value sits off neutral, so an absent render is not evidence that the framework failed [#2534/C/C-only].

The framework runs on the client only: every Lua file it ships sits under the client folder, so `MF` is nil on a dedicated server and every framework call lives in the consumer's own client file [#2536/C/C-only].
It has no transport either: it sends no command, handles none and transmits no modData, so the value a client draws is a value that client's own Lua set [#2537/C/C-only].
A server-held nutrient therefore reaches a framework moodle only over the mod's own bus, the server sending the value and a client handler setting it on the widget [#2540/C/inference].
The stored value lives in a per-client Lua table keyed by the character object rather than in player modData, so it is neither saved nor transmitted, no other mod's transmit can wipe it, and the consumer sets it again after every player creation [#2538/C/C-only].
Configuration waits for the widget, which the framework builds on player creation, so a consumer configures and first sets its moodle from a player-creation handler of its own [#2548/C/inference].
A mod that treats the framework as optional detects it with a type test on the framework's global at game boot or later, because a file-scope test can run before the framework's file loads and a `require` fails when the framework is absent [#2547/C/inference].

The widget route is not the framework's alone.
The vanilla moodle stack and the framework both draw through an element on the UI manager, so a mod can derive its own `ISUIElement`, add it to the UI manager and draw its moodle in `render()` without the framework, and vanilla Lua also draws text from a draw event with no widget at all; both readings are of the code and neither has been drawn [#2555/C/inference].
Such a column of the mod's own is costed under [Options](#status-icon-column), beside the framework's.

Adopting the framework costs four things, and each is a different kind of cost.
The first is a dependency: the framework is a separate workshop mod, so every server that runs this mod runs it too, and the declaration that orders two mods at load is the loader's to describe ([mod-anatomy.md#load-order-declarations](../platform/mod-anatomy.md#load-order-declarations)).
The framework sits on the target server's approved list, which is what the platform's framework rule rests on, a reading bounded to that server's mod list on the sweep's date [#1070/C/snapshot].
The second is its layout: its newest version folder ships a single file, and its configuration file lives only in an older tree and in `common/` [#1614].
That the framework loads whole on this build follows from the merge rule applied to that layout [#1319/C/snapshot], and one boot confirmed it, its configuration file executing beside the newest folder's moodle file ([T4.1/M/n=1], [T4.2/M/n=1]).
The moodle file that executes calls helpers only the configuration file defines, so the merge rule is what supplies a hard runtime dependency [#2541/C/C-only].
Its older moodle files call an engine member this build lacks, and a release that stops shipping the newer version folders would put one of them back in play, invisibly to a consumer [#2543/C/C-only].
It is also the one mod in the corpus whose `mod.info` chain differs between the layout lint and the engine, although the two files they open declare the same id [#0824/C/snapshot].
The third is its guards: it contains no protected call anywhere, so every call a consumer makes into it is guarded by the consumer's own protected call or by nothing [#2546/C/C-only].
The fourth was whether one of its moodles shows on a live client at all, and one session measured it: set to 0.95 a moodle read level 4, joined the UI manager and its render calls climbed from 569 to 809 in 4.02 s, while at 0.5 it stayed off the UI manager with no render call ([#1295/C/open], [T4.5/M/n=1], [T4.4/M/n=1]).
A widget of the mod's own drew in the same session at the same cadence, so the framework is one working route and the mod's own widget a second ([#2742/M/n=1/open], [T4.7/M/n=1]).

Whatever widget draws it, the level has to be computed on a side that holds the nutrient.
A nutrient the mod keeps on the server reaches a client only over a route the mod runs itself, because the player-stats push carries vanilla's fields and never a mod's own [#0129/M/n=1].
The framework maps a value to a level on the client that set it and nowhere else, so the side that holds the nutrient decides the value and the client only maps it ([#2533/C/C-only], [#2537/C/C-only]).
A mod moodle is also not among the types vanilla's consequences read: the carry-capacity, regeneration and health consumers name vanilla's own types ([#0513/M/n=1, #0516], [body-and-weight.md#moodles](../facts/body-and-weight.md#moodles), [health-surfaces.md#regeneration](../facts/health-surfaces.md#regeneration)), and whether a mod-registered type carries any Java effect at all is open [#0970/C/C-only/open].
A framework moodle or a widget of the mod's own is therefore a display, and anything the nutrient does to the body is written in Lua beside it, exactly as a mod trait's effect has to be [#1158/C/C-only].

A moodle drawn through the framework also shares the screen with the mods resident beside it.
The interface mod resident on the target server redraws the status surfaces, and drawing through the framework or through a panel of the mod's own is the rule that keeps this mod out of that mod's widgets [#1083/C/snapshot].
The framework's configuration file also mutates the engine's shared gray colour object in place from its own options page, so a panel that draws with that object on a client running the framework draws in the framework's colour [#2550/C/C-only].
Both server-specific readings are bounded to that server's mod list on the sweep's date, and both reopen the moment the list changes [#1070/C/snapshot, #1083/C/snapshot].

<a id="stat-moodles"></a>
### What a stat value shows as a moodle

A mod that moves a stat on the server moves the moodle the stat feeds, because each side recomputes its own moodles from its own copy of the stats, and the level a value reaches is fixed by thresholds a mod cannot change [#1143/C/C-only] [#1141/C/C-only].
The thresholds are on [the mood surface](../facts/health-surfaces.md#mood-surface), [the hunger and thirst moodles](../facts/body-and-weight.md#moodles) and [the tired moodle](../facts/endurance-fatigue-sleep.md#moodles) [#2369/C/C-only] [#0508/M/n=1] [#0509/M/n=1] [#2279/C/C-only].
No reader of the mood, tired, sick or drunk moodle levels exists on the harness: its `stats.get` carries the hungry, thirst, food-eaten, heavy-load and endurance levels only (its list is `TK.MOODLES`, `repo:testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua:372`), so every level below for those moodles is the registered threshold applied to a measured stat value, and no run has seen the level itself.
The registered thresholds are not a measured firing point for the mood rows [#2369/C/C-only].

The held hunger view read 0.69 and the held thirst view 0.83, under the level-4 thresholds of 0.70 and 0.84, which puts both moodles at level 3 and keeps them off the level-4 drain [#3074/M/n=1] [#3103/M/n=1] [#0508/M/n=1] [#0509/M/n=1].
FATIGUE crossed 0.6, 0.7 and 0.8, the first three Tired thresholds, at world age 15.29, 17.19 and 19.68 h, about 12.2, 14.1 and 16.6 h after the character's first minute on the server [#3075/M/n=1] [#2279/C/C-only].
FOOD_SICKNESS at 55 sits over the SICK moodle's second threshold of 0.50 and at 85 over its third of 0.75, on the stat's 0 to 100 scale read as a hundredth, so the SICK moodle stands at level 2 and then level 3, and a value of 95 would stand over the fourth [#2369/C/C-only] [#3130/C/C-only] [#3084/M/n=1] [#3104/M/n=1] [#3039/M/n=1].
PANIC floor targets of 10 to 19.25 sit between the first threshold of 6 and the second of 30, which is level 1, and a target of 35 sits between 30 and 65, which is level 2 by arithmetic against those bands; the floor held 10 and 12.75 and tracked the target to 14.5 on one boot [#3101/M/n=1], while on another PANIC never reached a target of 19.25, 35 or 14.75 [#3082/M/n=1] [#2369/C/C-only].
UNHAPPINESS floor targets of 22.92 and 25 sit between the UNHAPPY thresholds of 20 and 45, which is level 1, and the released 4.1667 sits under the first [#2369/C/C-only] [#3083/M/n=1].
A STRESS floor of 0.06 sits under the STRESS moodle's first threshold of 0.25 and shows no moodle, and an INTOXICATION that peaked at 2.85 sits under the DRUNK moodle's first threshold of 10 [#2369/C/C-only] [#3080/M/n=1] [#3086/M/n=1].

<a id="read-cadence"></a>
### Cache on the push, not on the frame

A client-side reader of the nutrition store reads a mirror, and the mirror changes only when a packet lands.
The server pushes the whole store in one unconditional snapshot once a second ([#0114], [wire-packets.md#player-stats-packet](../facts/wire-packets.md#player-stats-packet)).
Its whole nutrition payload is the store's five floats and nothing else [#1481].
Between two pushes the client's copy of the macros and the calories does not move, because the client arm of the nutrition update skips the decays that move the server's ([#1483], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
A reader that reads every frame therefore reads one value over and over until the next packet replaces it.
A mod can neither observe nor suppress the player-stats write, so a client-side reader cannot tie a redraw to the write and can only poll [#1149/M/n=1].

The one viewer mod this library tore down, `simpleStatus`, shows why the rule rests on the source rather than on the viewer.
Its resolved copy advances a frame counter and prepares its bars, the only code that calls a bar's value function, only on a fixed fraction of frames, drawing the prepared values on every frame between [#2524/C/C-only].
So the reads it makes follow its own frame counter and not the store's changes: a throttled render loop still calls an uncached value function many times between two pushes [#2725/C/inference].
That count is a property of one version's render loop, and another version or another viewer reads at a count of its own.
Cache a nutrition value at the push cadence rather than the frame cadence, because the source changes once a second and the measured arrivals show it, while a viewer's read count is the viewer's own and drifts with its version [#2692/M/n=1].
The arrivals were measured in one session and the read count is a reading of one viewer's code, so the rule is exact about how often the source moves and silent about what a repeated read costs [#2692/M/n=1] [#2524/C/C-only].
No shipped command measures frame time or Lua call counts, so the saving the rule buys is a count of avoided reads rather than a measured cost [#2524/C/C-only].
The framework positions its own moodles at the frame cadence with no cache, which a consumer cannot cache away; what a consumer controls is how often it sets a value, and that is the cadence this rule governs ([#2549/C/C-only], [moodleframework.md#pitfalls](../facts/other-mods/moodleframework.md#pitfalls)).

Caching at the push cadence means reading the store about as often as it can change and drawing the cached value in between.
It does not mean reading at the instant a packet lands, which no hook offers, so a cached reader trails the server by up to one push plus its own refresh interval.
That lag is the price of the saving, and for a nutrition display it is a small one: a server-side write reached the client within a measured bound of under a second ([#1493/M/n=1], [mp-model.md#routes-server-to-client](../platform/mp-model.md#routes-server-to-client)).
The heavier work belongs off the render path altogether: slow simulation sits on the minute events, a per-frame hook is for per-frame needs behind a cheap early-out, and the tick event is the expensive tier [#1071/C/snapshot].
A display of a mod nutrient pays the staleness twice, once for the route the mod's own value travels on and once for the cache in front of it.

What a client-side reader may draw from the mirror splits on the packet's field list and not on the getter it calls [#1523/M/n=1].
The store's floats are on the packet, and every macro gap a viewer's bars showed sat inside the band that one read skew and one push explain, so those numbers are the server's, late by under a second ([#1486/M/n=1], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
Weight is carried but never recomputed on a client, so its mirror sits below a rising server rather than above it [#1484/M/n=1].
The three weight-direction flags are not carried at all and still agree, because the client recomputes them from values that are ([#1489], [#1490/M/n=1]).
That agreement was read on a character holding no band trait, so the flags' dependence on both sides computing the same threshold is untested [#1490/M/n=1].
The band traits are not on the player-stats packet; they reach the client on other pushes, traced [below](#trait-arrival) from the code and not measured ([#0567], [#2595/C/C-only]).
A vanilla moodle is recomputed on the client from the mirror, so it is as late as the mirror and no later [#1143/C/C-only].
A mod's own values are on no vanilla packet: a client-side write of a vanilla nutrient number is overwritten within a second, while a mod's own field survives the push and simply desyncs, that second half read off the packet's field list rather than measured [#0129/M/n=1].
A mod value therefore reaches a panel only over a route the mod runs, the command bus or a transmitted modData table, and each route fails in its own way on a live server ([mp-model.md#command-bus](../platform/mp-model.md#command-bus), [mp-model.md#wipe-and-replace](../platform/mp-model.md#wipe-and-replace)).
The command bus is the route a mod controls end to end [#1153/C/C-only], while a player's modData is replaced whole by whichever mod on that client transmits it next [#1151/M/n=2].

A value a panel derives on the client, instead of fetching it, is only as good as its least-carried input.
The torn-down viewer derives its weight-direction suffix from the three uncarried flags, and it is right because the engine recomputes them from carried inputs; the technique is the dependency check rather than the derivation [#1508].
Its dependency list has one entry the player-stats packet does not carry, the band traits, and writing that list down is the step the technique cannot skip [#1508].
That is the rule on checking every input of a derived display against the field list, and the rule on evaluating anything band-keyed on the server, or pushing the trait list after each write, is its sharpest case ([#2731/C/inference], [#2727/C/inference]).
The staircase and flag readings in this section are one session on the dedicated-server path with one client and one character, and the weight arm was driven on the gain side only ([#1484/M/n=1], [#1490/M/n=1]).
The per-frame counts are the one worked viewer's, so another panel's cost follows its own read shape rather than that mod's.

<a id="trait-arrival"></a>
### The trait list reaches a client

A band label, a trait-keyed colour or any display that branches on a trait reads the client's own trait list, and that list is a copy the server sends.
Traits are applied server-side, the engine's own weight-band refresh running only off a game client, and the list reaches the owning player's client on two server pushes: the experience packet, whose payload opens with the trait list, and the player-fields packet's trait block, which server Lua sends through `sendSyncPlayerFields(player, 2)` and vanilla sends on a finished book read [#2595/C/C-only].
The experience push runs on the same once-a-second limit as the stats snapshot, so the timed route alone leaves a client's list at most about a second behind the server's [#2608/C/C-only].
Both carriers replace the receiver's list rather than merge into it, so after either lands the client holds the server's list, a removal included ([#2617/C/C-only], [#2620/C/C-only], [wire-packets.md#player-fields-packet](../facts/wire-packets.md#player-fields-packet), [wire-packets.md#experience-packet](../facts/wire-packets.md#experience-packet)).
The engine fires no event and sends no packet when a trait is written [#2601/C/C-only].
No Java code sends the trait bit, and vanilla sends it on a finished book read, so a mod that wants a trait it writes on the server shown before the next timed push sends the block itself ([#2604/C/C-only], [#2606/C/C-only], [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)).
`sendSyncPlayerFields` does nothing off a server and returns silently for a player with no online id, so a call is no proof that the client's list moved [#2602/C/C-only].
Every one of these pushes is addressed to the player's own connection, so none of them refreshes another client's copy of that character, and a label one player sees on another rests on a different route [#2603/C/C-only].
A client cannot push a trait the other way on an ordinary connection: the vanilla stats panel's experience upload, which carries the trait list, is loaded by the server only from a connection whose role holds the stats-panel capability ([#2615/C/C-only], [#2612/C/C-only]).
On the client, the character screen rebuilds its trait icons whenever the list it reads differs from the icons it holds, so a pushed trait appears there without a refresh [#2504/C/C-only].
The route is traced from the bytecode and the files ([#2595/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4)), and its arrival is measured: with no push a server-written trait reached the owning client's list within about half a second in three trials [#2759/M/n=3].
A trait the mod registers reads back in that list by the path of its id alone, so a panel's test matches that path, never the full id [#2761/M/n=1].
A server-side trait-block push (`sendSyncPlayerFields(player, 2)`) in the same tick as the trait write makes the arrival sooner, within tens of milliseconds (measured through the harness's `trait.add.push`) ([mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)) [#2099/M/n=6].
A band label drawn from the client's own list is therefore the owning player's alone, as fresh as the last push of either carrier, and the rule on pushing the trait block after a server-side write is [mp-sync.md](mp-sync.md#rules)'s.

<a id="honest-but-wrong"></a>
### A number can be honest and still wrong

A number on a display can be honest, in that it is exactly what the getter it read returned, and still be wrong about the thing the player takes it to show.
The two come apart in a small set of ways on this build, and each one is a property of what reaches the client rather than of the display that draws it.
Knowing which way a number can be wrong is what lets a design choose its source, so each way below ends with the source that is right.

The first way is lateness.
A client-side reader of the store sees a staircase that steps when a packet lands while the server's value is a ramp, so a cross-side gap is a timing reading and equality is the wrong verdict to look for ([#1483], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
The comparison that grades such a reader is a band built from each snapshot's own read skew, with the client half read first, rather than an equality [#1485/M/n=1].
Graded that way, every macro a viewer drew was the server's number, late by under a second [#1486/M/n=1].
A late number is honest, and the error it carries closes at the next push.
It turns wrong only when something compares it with the server at the same instant, which a display never does and a test often does.
The right source for it is the mirror itself, drawn through the cache [the section above](#read-cadence) describes.

The second way is a value transformed on the wire.
The item packet sends a cooked food's thirst through the getter that applies the cooked ladder, and the receiver stores it into the raw field, so the client's own getter applies the ladder a second time ([#1408], [wire-packets.md#cooked-thirst](../facts/wire-packets.md#cooked-thirst)).
The result is one halving per server-to-client hop [#1038/M/n=2].
It converges rather than compounding, because no item route runs from the client back to the server to feed the halved value round again [#1409/M/n=1].
Every step of that is honest: the server reads its field, the packet carries a getter's value, and the client reads its own field through its own getter.
The number the client shows is still not the number the item has, and any mod that reads that getter on a client inherits the error, because the defect is vanilla's rather than a mod's [#1147/M/n=1].
The right source is the side that owns the number, which is the rule on reading a food's numbers from its owner [#1084/M/n=2].

The third way is a value that stops arriving.
A client's freshness display is whatever the last full serialisation of the item said and can be arbitrarily stale, because nothing re-sends the age until the item is serialised whole again ([#0357/C/inference], [mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is)).
After a cook the item's age window, its cookable flag and its custom-weight flag stay wrong on the client together with the thirst getter, so a panel that draws them draws the client's pre-cook belief [#1523/M/n=1].
The right source for a live item field is the server, asked over the bus, rather than the client's copy ([#1423/M/n=1], [#1111]).

The fourth way is a value borrowed from another item.
A conditionally-written item field that should be zero arrives carrying the previous packet's value, because the receiver reuses one cached packet per type and applies every field unconditionally ([#0346/M/n=1], [#1146/M/n=1]).
A display that reads such a field shows another item's number under this item's name, and the getter is honest about the field it reads.
The right source is again the server, or the script where the value is a definition rather than a state [#0651].

The fifth way is a guard that reads as a quantity.
The unmodded actual-weight getter answers zero whenever an item's display name equals its full type, which is the case for a mod item on a dedicated server and for any item without a translation entry on a client ([#0911/M/n=1], [#1023/M/n=1]).
That zero is the display-name guard and never a weight fact, so a panel that shows that getter shows the item's translation state rather than its weight.
The guard also reaches the wire, because the packet's weight field is filled from that getter, so a new food shipped without a translation entry sends a weight of zero to every client [#1166/C/C-only].
The weight facts are the plain weight getter and the direction flags, and the one thing that keeps the guard off a new item is a translation entry [#0911/M/n=1, #1166/C/C-only].

The sixth way is a scale somebody else chose.
The torn-down viewer hard-codes display bands that encode vanilla's balance, so a rebalance that moves the macro numbers makes its colours and captions lie silently [#1514].
The number beside the colour stays honest; the judgement drawn around it goes wrong, and the rebalance that breaks it never touches that viewer's code, on every client that runs it [#1522].
This mod's own panel carries the same exposure turned around, since any band it draws is a copy of a balance that has to move when the balance does.

Read together, the six ways give one test for any number a display draws: ask what the packet carries, not what the getter returns [#1523/M/n=1].
A number the packet carries untransformed is late and right; a number it transforms, omits or borrows is honest and wrong on a client, and the right source for it is the script or the server.
The rules on reading a food's numbers from its owner and on treating freshness as stale are this reading's two imperatives, and both are the platform's own lines, copied.

## Options

A nutrition number reaches a player through one of three surfaces, and they differ in who computes the number, which side draws it and what a mod has to reach to put it there.
A moodle is drawn from a level, by the engine or by a widget, and it is the only surface whose vanilla form has consequences of its own ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)).
A client panel is code the mod owns end to end, drawn on the client from whatever the client holds, which is the shape the torn-down viewer takes [#1469].
Tooltip text is keyed per item: `Tooltip` is one of the item-level keys the script reference lists, and that reference's runtime-effect column gives it as a translated tooltip key ([#0215/C/snapshot], [food-item-model.md#script-keys](../facts/food-item-model.md#script-keys)).
A script tooltip line also becomes an item-modData key on every side that builds the item, so the text surface is not free of the modData surface ([#1044], [loader-and-scripts.md#default-moddata](../platform/loader-and-scripts.md#default-moddata)).
The vanilla food tooltip already carries a nutrition block, which either Nutritionist trait opens and which is the trait's one reader in the jar ([#0546/C/snapshot], [#0547/C/C-only]), and the same block also opens under the debug tooltip option and on a packaged food whose label the viewer can read [#2645/C/C-only].
The tooltip body is built in Java and Lua only hosts the drawing, so a mod adds a line of its own by wrapping the tooltip panel's render, the shape [the tooltip option](#tooltip-line) costs ([#2490/C/C-only], [client-ui.md#tooltip](../platform/client-ui.md#tooltip)).
Translation text resolves on the client alone: a mod's keys merge beside vanilla's, and a dedicated server resolves no display name at all ([#1163/M/n=1], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
A mod's value for a vanilla key wins on the client, a redefined `Base.Apple` reading the mod's name there [T4.15/M/n=1], while the server keeps vanilla's strings and never sees the mod's ([T4.16/M/n=1], [T4.17/M/n=1]).
The text router carries no item-name prefix, so a feature that must know whether a translation loaded is gated on an interface key rather than on an item name [#1720/M/n=2].
None of the three excludes the others: a design can show one nutrient as a moodle, the whole store in a panel and a food's character in its tooltip, and each choice is costed on its own.
Each row below names what the surface costs and the wall it runs into, with the verdict rows that decide both, in the wall map's own row order; the four shapes after the table are the forms a panel, a tooltip line, a tab and an icon column take on this build.

<a id="surface-options"></a>
### The three display surfaces

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| a moodle through `MoodleFramework` | a runtime dependency on a third-party client-only widget library with no transport, so the value comes over the mod's own bus to a client handler that sets it; the consumer guards every call, detects the framework by a type test and inherits its version-folder hazard; vanilla's moodle consumers ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)) name only vanilla's own types | a mod's own registered type is pinned at its lowest level and vanilla's thresholds are unreachable, so a moodle is a widget beside the stack, the framework's or the mod's own; one session drew both on a dedicated-server client (`X29`) | [#1140/C/C-only], [#1141/C/C-only], [#2531/C/C-only], [#2537/C/C-only], [#2540/C/inference], [#2543/C/C-only], [#2546/C/C-only], [#2547/C/inference], [#1295/C/open], [#0513/M/n=1] |
| a client panel | the whole panel is client code the mod owns: it caches at the push cadence, fetches any mod-owned value over the command bus or a transmitted table, and shares the screen with a resident interface mod | a client reads a pushed mirror and cannot observe the player-stats write; a cooked food's thirst reads halved on a client; the band traits reach the owning client on server pushes addressed to it alone, the experience packet and a trait-block push, and another client on an authorized client's experience relay and on the connected-player packet the server sends at a join or on a player-data request, routes read from the code and not measured (`X4`) | [#1147/M/n=1], [#1149/M/n=1], [#2595/C/C-only], [#2603/C/C-only], [#2612/C/C-only], [#2734/C/C-only], [#2692/M/n=1] |
| tooltip and translation text | text keyed per item or per interface key and resolved on the client alone; a script tooltip line becomes an item-modData key on every instance | a mod's keys merge rather than shadow, and a mod's value for a vanilla key displaces vanilla's on the client while the server keeps vanilla's (`X5`); a dedicated server resolves no mod display name; a new food without a translation entry ships a zero weight | [#1163/M/n=1], [#1164/C/C-only/open], [T4.15/M/n=1], [#1166/C/C-only], [#1167/M/n=1], [#1044] |

Which surface carries each nutrient the design shows: a moodle widget on a route no run has confirmed, a client panel the mod owns end to end, or keyed text that only a client resolves?

<a id="panel-window"></a>
### A panel as a collapsable window

The panel a client draws is one more derive on the UI manager, and the toolkit decides how much of a window the mod writes.
A panel derived from the collapsable window inherits a title bar, a close button, a pin and collapse pair and resize widgets, and drags without code of its own [#2467/C/C-only].
A content panel becomes such a window in one call, which hands back the window to register and to add [#2471/C/C-only].
A bare panel drags only when its flag is set, so a panel that should stay put needs nothing [#2468/C/C-only].
A hidden panel that leaves the UI manager's list costs nothing per frame, because the engine renders only the elements on that list [#2469/C/C-only].
Its geometry persists through the layout manager into a file written only when a session ends, or through player modData that crosses the wire on every save, and the registration rule and that choice are [client-ui.md](../platform/client-ui.md#layout)'s [#2476/C/C-only].
The cost is the panel's own draw and its read cadence, which [the cadence section](#read-cadence) sets, and the wall is the mirror it reads from.

<a id="tooltip-line"></a>
### A line in the item tooltip

A food's nutrients belong where the player already looks at a food, and that is the inventory tooltip.
The tooltip body is built in Java inside one render method, which Lua wraps, and one wrap of it covers the item tooltip at every site the install constructs it ([#2490/C/C-only], [#2494/C/C-only]).
The crafting slot's tooltip is a second route with its own wrap point, so a line meant for both is written twice [#2495/C/C-only].
The tooltip's height is fixed by Java before any Lua sees it, so a mod's band is drawn and framed below the engine's box, as the two tooltip rules on [client-ui.md](../platform/client-ui.md#tooltip) say [#2491/C/C-only].
The render does nothing while a context menu is open, so a wrap that draws after it repeats that test [#2496/C/C-only].
The resident interface mod leaves this route intact: its own inventory files still construct the vanilla tooltip panel, so a wrap of that panel's render survives it, while under it a stack's tooltip describes one representative item ([#2499/C/C-only], [#2500/C/C-only]).
The vanilla nutrition block in that tooltip opens under the debug tooltip option, on a packaged food whose label the viewer can read, or for either Nutritionist trait, so the mod's band sits beside a block some players see on some foods and not on others [#2645/C/C-only].

<a id="character-info-tab"></a>
### A tab in the character-info window

A per-character nutrition panel can live as a tab beside the skills and health tabs instead of as a floating window.
A mod adds one by wrapping the window's child construction at file scope to add a view, because the window is built on player creation [#2501/C/C-only].
The window has no tab registry: its tabs are hard-coded in several places, so a mod tab costs method wraps where a registry would cost a call [#2513/C/C-only].
A tab's name is its translated string and the same string is its toggle argument [#2503/C/C-only].
A mod tab never writes its name into the saved layout key, which vanilla resolves through a table with no entry for a mod tab [#2502/C/C-only].
The tab rule is [client-ui.md](../platform/client-ui.md#character-info)'s, and the worked tab is [autocook.md](../facts/other-mods/autocook.md#architecture)'s.

<a id="status-icon-column"></a>
### A status-icon column beside the moodles

A mod that wants moodle-like icons without the framework draws a column of its own widgets, lined up against the vanilla stack.
The vanilla moodle panel is in the exposer's class set with a public instance getter and readable bounds, so its box is an anchor for a mod's icon column, though the class offers no mutator [#2509/C/C-only].
A live client read that box through the instance getter, so the anchor is real, though the design keeps its column at a fixed inset of its own ([T4.9/M/n=1], [T4.10/M/n=1]).
The column is a derived widget on the UI manager drawn in its own `render()`, the same kind of object the framework draws [#2555/C/inference], and such a widget, added at player creation with no framework call, drew 240 times in each 4 s window of one session ([T4.7/M/n=1], [#2742/M/n=1/open]).
Its icons are the mod's own textures, loaded in a client file behind a nil check, and its level logic is the mod's own Lua, since nothing in the engine maps a value to a level for it ([client-ui.md#textures](../platform/client-ui.md#textures)).
The framework places its moodles by counting vanilla's and its own and nothing else, so a column beside a framework stack takes its own slot or overlaps it [#2549/C/C-only].
The cost is a widget the mod writes whole, drawn every client frame once it is on the UI manager ([T4.8/M/n=1], [client-ui.md#cadence](../platform/client-ui.md#cadence)).

## Walls and bounds
<a id="walls"></a>

- A mod cannot register a new moodle type that works: registration reaches every character and the level is pinned at its lowest every tick ([#1140/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- A mod cannot retune a vanilla moodle's thresholds nor change what a moodle does: the class that holds the thresholds is unreachable from Lua ([#1141/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- Both moodle routes are measured on one session only: the framework loaded whole and its moodle and a widget of the mod's own each drew on a dedicated-server client, counted as render calls rather than seen on screen, with one fixture and one character ([#1295/C/open, #0884/C/C-only/open, #2742/M/n=1/open], [#2555/C/inference], [wall-map.md#d4](../reference/wall-map.md#d4)).
- `MoodleFramework` carries nothing between the sides: it is nil on a dedicated server and has no command, handler or modData transmit, so a server value reaches its moodle only over the mod's own bus ([#2536/C/C-only], [#2537/C/C-only]).
- Nothing carries a moodle between the sides: each side recomputes its own from its own mirror, so a client's moodle is exactly as late as its stats ([#1143/C/C-only]).
- A mod cannot trust a zero-valued item field on a client, because it can arrive holding another item's value ([#1146/M/n=1]).
- A mod cannot trust a cooked food's thirst value read on a client, and neither can a display that draws it ([#1147/M/n=1], [wire-packets.md#cooked-thirst](../facts/wire-packets.md#cooked-thirst)).
- A mod cannot observe or suppress the player-stats write, so no panel can tie a redraw to the write ([#1149/M/n=1]).
- A trait a mod adds is selectable and saved but carries no effect of its own, so anything it should show or do is written in Lua ([#1158/C/C-only]).
- A band trait reaches the owning player's client on server pushes addressed to it alone, the timed experience push and a trait-block push that server Lua or a book read sends, and another client on an authorized client's experience relay and on the connected-player packet the server sends at a join or on a player-data request, neither of which a trait write triggers; the routes are traced from the code, and the owning client's arrival is measured on non-empty trait lists, within about half a second with no push [#2759/M/n=3] and within tens of milliseconds with the push [#2839/M/n=6] ([#2595/C/C-only], [#2603/C/C-only], [#2612/C/C-only], [#2734/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4), [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)).
- A mod cannot test a trait by its string name, because the string form is removed on this build ([#1162/C/C-only]).
- The character-info window has no tab registry, so a mod tab is a set of method wraps ([#2513/C/C-only], [client-ui.md#character-info](../platform/client-ui.md#character-info)).
- Translations are client-only: a mod's keys merge beside vanilla's and a dedicated server resolves no display name ([#1163/M/n=1], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
- A rename of a vanilla food reaches the client only: a mod's value for a vanilla key displaced vanilla's there in one session, while the dedicated server kept vanilla's strings ([#1164/C/C-only/open], [#1276/C/open], [T4.16/M/n=1], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
- A mod cannot name its items through the older text-table layout ([#1165/M/n=1]).
- A mod cannot ship a food absent from the translation table without every client receiving its weight as zero ([#1166/C/C-only]).
- A mod cannot resolve or branch on an item name anywhere but the client's display-name getter ([#1167/M/n=1]).
- The read-cadence rule rests on arrivals measured in one session, and a viewer's read count is a reading of its own code that no command measures as frame time, so the rule bounds a count of reads rather than a cost ([#2692/M/n=1], [#2524/C/C-only]).
- Every client-side reading this page cites was taken on a dedicated server with one client, one fixture and one character, and single-player is never claimed ([#1256/C/one-fixture]).

Not covered: the vanilla food tooltip's layout beyond its gates; the character screen's trait display beyond its rebuild on a list change; whether `CleanUI` moves, hides or redraws a framework moodle or a mod's icon column; controller and split-screen input; and any measurement of frame time or draw cost — this library read none of them.

## Open
<a id="open"></a>

- Whether the moodle stat class is reachable from Kahlua at all — settled by a global read of that class beside two exposed controls that must answer in the same call; -> X2 ([#1274/C/open], [open-questions.md#x2](open-questions.md#x2)).
- Whether a mod-registered moodle type carries any Java effect — settled by a session that registers one and reads what its level drives, which no named experiment runs; the register files the row under X2 ([#0970/C/C-only/open], [open-questions.md#x2](open-questions.md#x2)).
- That a mod's translation file at a vanilla relative path costs vanilla nothing is unverified, and its owner states it with its bound ([#1340/M/n=1/unverified], [mod-anatomy.md#open](../platform/mod-anatomy.md#open)).
- That the text route cannot reach the item-name table on either side is unverified for want of an in-run positive control, and its owner states it with its bound ([#0845/M/n=2/unverified], [mod-anatomy.md#open](../platform/mod-anatomy.md#open)).
- The design must decide whether it requires `MoodleFramework`, detects it optionally or draws its own widget, because a hard dependency inherits the framework's version-folder hazard and an optional one needs a fallback widget of its own [#2543/C/C-only, #2547/C/inference, #1070/C/snapshot].
- The design must decide which slot a fallback widget takes beside a framework stack, because the framework places its moodles by counting vanilla's and its own and nothing else [#2549/C/C-only, #2555/C/inference].
- The design must decide which values its panel derives on the client and which it fetches from the server, because a derived value is right only while every input it reads is carried, and the band traits travel on other packets than the stats they would be read beside [#1508, #2595/C/C-only].
- The design must decide whether its panel shows a band label drawn from the client's own trait list, because that list reaches the client within about half a second of a server write with no push [#2759/M/n=3] while the mod's own push sent with the write brings it within tens of milliseconds [#2595/C/C-only, #2099/M/n=6].
- The design must decide whether a band label waits for the timed experience push or follows a trait-block push the mod sends after each write, because no Java code sends the trait bit [#2604/C/C-only, #2608/C/C-only].
- The design must decide how stale a displayed value may be, because a client panel cannot observe the player-stats write and draws a mirror late by up to one push plus its own refresh interval [#1149/M/n=1, #1486/M/n=1].
- The design must decide whether a cooked food's thirst is shown on a client at all, or re-derived from the script, because the client's getter reads a value halved once per hop [#1038/M/n=2].
- The design must decide whether it renames any vanilla food, because a mod's value for a vanilla key displaces vanilla's on the client and not on the server [#1164/C/C-only/open].
- The design must decide whether its numbers stay inside the display bands the torn-down viewer hard-codes, because those bands go wrong silently on a re-based scale [#1514, #1522].

## See also

- [`../platform/client-ui.md`](../platform/client-ui.md#panel-toolkit) — the widget toolkit, the tooltip and tab wrap points and the moodle stack's Java surface.
- [`../platform/lua-platform.md`](../platform/lua-platform.md#registries) — the moodle and trait registries, and what each registration is worth.
- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#translations) — the translation tables, the merge, and the dedicated server that resolves no display name.
- [`../platform/mp-model.md`](../platform/mp-model.md#what-a-client-copy-is) — what a client's copy of a server object is, and is not.
- [`../platform/mp-model.md`](../platform/mp-model.md#sync-globals) — the sync globals, the trait push and the single recipient.
- [`../platform/lessons.md`](../platform/lessons.md#anti-patterns) — the framework, resident-interface and cooked-getter rules this page copies.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#staircase) — the staircase a client-side reader sees, and the band that grades it.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#cooked-thirst) — the cooked-food thirst value and its halving.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#experience-packet) — the experience packet and the trait list it carries.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#moodles) — the vanilla moodles, their thresholds and what each level does.
- [`../facts/other-mods/moodleframework.md`](../facts/other-mods/moodleframework.md#what-it-does) — the framework torn down: its registration surface, its client-only layout and its pitfalls.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md#mp) — the worked viewer: what a pure client reader can and cannot show.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#status) — the framework's layout and build status.
- [`new-nutrients.md`](new-nutrients.md#effect-paths) — the moodle surface as one of a new nutrient's effect paths.
- [`mp-sync.md`](mp-sync.md#sync-options) — the routes a mod-owned value takes to reach a client panel.
- [`testing-your-mod.md`](testing-your-mod.md#owned-experiments) — the experiments behind this page's walls, as this mod's own.
- [`open-questions.md`](open-questions.md#decisions) — the decisions above, beside every other area's.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows cited above.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments the open rows point at.
