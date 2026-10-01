# UI and moodles — what a nutrition mod can show a player
Verified against 42.20.4 (b0bbce05d5) · 2026-09-26 · scope: the nutrition-design reading of the display surfaces — a client panel, a moodle through `MoodleFramework`, tooltip and translation text — what each costs and which wall it hits, how often a client-side reader should read, and why a displayed number can be honest and still wrong; the moodle and trait registries are `platform/lua-platform.md`, the translation tables `platform/mod-anatomy.md` and the packet contents `facts/wire-packets.md`

## Rules

- Cache a nutrition value at the push cadence rather than the frame cadence: the source changes once a second while an uncached panel reads it up to four times per macro bar and ten times per weight bar every frame, the counts read off one viewer's render loop and the arrivals measured in one session [#1114/M/n=1].
- Never register a moodle type of your own through the vanilla registry: a registered type reaches every character and is driven back to its lowest level every tick, and a duplicate id corrupts the registry before the call throws [#1140/C/C-only, #2060/C/inference].
- Register with a framework that already owns a contested value rather than writing that value last: cooperative detection avoids last-write-wins between two mods that both own carry weight or moodles [#1070/C/snapshot].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Test a Java class against the exposer's class set before you plan on it: the exposure test is a strict membership test, so a class the jar carries and the exposer does not register is unreachable [#0963/C/C-only].
- Put a protected call at every engine and third-party boundary: it keeps your own handler body running, which the survival of the handlers behind you does not give you [#0944/M/n=1, #0948/M/n=1].
- Keep a raising call out of a client launched with the debug flag: the failure helper's debug arm enters the modal break and the process never answers again, on two boots out of two [#0954/M/n=2, #0955/C/C-only].
- Take a client-side moodle read at least one push after a server-side stat write: the moodle recompute has no side guard, so the client recomputes from a mirror that can lag by a push [#0570/C/C-only].
- Derive a client-side value from packet-carried inputs only with its dependency list written down and each input checked against the packet's field list: a derived value is desync-free only while every input is carried faithfully, and the band traits, a cooked food's thirst and a zero-valued conditional item field are not [#1508, #2052/C/inference].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or feed it an explicitly transmitted value: the band traits are not in the player-stats packet and no other packet was traced carrying the trait list [#1104/C/inference].
- Compare a trait by the registry object and never by its name: the name getter answers lowercased, so a string comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].
- Read a food's numbers from the side that owns them and never build mod math on a getter whose value is transformed again on the wire: the item packet sends a cooked food's derived thirst getter and the receiver stores it as the raw field [#1084/M/n=2].
- Treat a client's freshness display as arbitrarily stale: it is whatever the last full serialisation of the item said, and nothing re-sends the age until the item is serialised whole again [#0357/C/inference].
- Ship a mod's item names in a B42 `ItemName.json` whose keys are the bare `Module.Name`: the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
- Expect a mod translation to add keys rather than replace them: the reader merges into a shared map, so vanilla's keys survive beside the mod's [#0841/C/C-only].
- Never branch on an item's display name server-side or reach for one through `getText`: a dedicated server resolves no mod display name and the text router carries no item-name prefix [#1026/M/n=2].

## How it works

A nutrition overhaul tracks more than vanilla shows, and everything it shows has to reach the player through a surface the engine already draws or one the mod draws itself.
This page owns no mechanism of those surfaces: it reads the registries, the packets and the translation tables owned by the pages below it, and states what each reading means for a display.
The moodle surface is decided by the registries, a client panel by the packets its numbers travel on, and text by the translator.
The three readings below take the moodle and the panel in turn and then the failure both of them share; the text surface is read where it is costed, under [Options](#surface-options).

<a id="moodle-route"></a>
### `MoodleFramework` is the only moodle route

A moodle is the surface a player already reads for hunger and thirst, and it is the only one of the three that acts as well as shows: a vanilla moodle's level feeds carry capacity, health regeneration and the severe-level health loss ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)).
That is what makes a moodle attractive for a new nutrient, and it is also the surface this build closes hardest.

A mod could reach a moodle through the vanilla registry in two ways, and what each is worth is settled on the platform page rather than here ([lua-platform.md#registries](../platform/lua-platform.md#registries)).
A moodle type the mod registers itself succeeds, reaches every character and is then held at its lowest level every tick, so the door leads nowhere [#1140/C/C-only].
Retuning a vanilla moodle is closed from the other side, because the class that holds every threshold cannot be reached from Lua [#1141/C/C-only].
Both are readings of this build's bytecode rather than failed attempts: nothing in this library has registered a moodle type or called a threshold setter [#0969/C/C-only, #2040/C/C-only].
With both doors closed, the one moodle surface left is adopting `MoodleFramework` and registering through its own interface rather than through the vanilla registry [#1142/C/C-only].
The framework is therefore the route by elimination and not by comparison: there is no second candidate on this build to weigh it against.
A mod that calls the vanilla registration anyway buys nothing a player can see and puts the registry's shared state at risk, which is the rule against it above [#1198/C/C-only].

One moodle move is left to a mod without the framework, and it is a way of acting rather than of showing.
A mod can drive a vanilla moodle by moving the stat behind it on the server, and the moodle then means exactly what vanilla says it means, while the class that would let it mean anything else stays out of reach ([#0568/M/n=2], [#1141/C/C-only]).
That puts the nutrient's effect in front of the player as hunger or thirst and never puts the nutrient itself there.
Where the stat is written decides nothing about where the moodle is computed: each side recomputes its own moodles from its own copy of the stats, and nothing about a moodle crosses the wire [#1143/C/C-only].
A client-side moodle is therefore exactly as late as the client's stats, which is what the rule on reading a moodle one push after a write is for.

Adopting the framework costs four things, and each is a different kind of cost.
The first is a dependency: the framework is a separate workshop mod, so every server that runs this mod runs it too, and the declaration that orders two mods at load is the loader's to describe ([mod-anatomy.md#load-order-declarations](../platform/mod-anatomy.md#load-order-declarations)).
The framework sits on the target server's approved list, which is what the platform's framework rule rests on, a reading bounded to that server's mod list on the sweep's date [#1070/C/snapshot].
The second is its layout: its newest version folder ships a single file, and its configuration file lives only in an older tree and in `common/` [#1614].
That the framework loads whole on this build follows from the merge rule applied to that layout, so it is a derivation and not a boot [#1319/C/snapshot].
It is also the one mod in the corpus whose `mod.info` chain differs between the layout lint and the engine, although the two files they open declare the same id [#0824/C/snapshot].
The third is its interface: the registration call a mod would make, the side it runs on and what it does in multiplayer are unread, so a probe cannot yet be written against it [#1142/C/C-only].
The fourth is the one that matters most: whether a moodle registered through the framework ever shows above its lowest level on a client is unread, and a zero there would mean this mod has no moodle route at all [#1115/M/n=1/open].
That last unknown is why the moodle route is [a wall](#walls) on this page rather than a detail of adoption.

Whatever the framework draws, the level it draws has to be computed on a side that holds the nutrient.
A nutrient the mod keeps on the server reaches a client only over a route the mod runs itself, because the player-stats push carries vanilla's fields and never a mod's own [#0129/M/n=1].
Where the framework computes a registered moodle's level, and whether it computes it on both sides the way vanilla does, is part of the same unread interface.
A mod moodle is also not among the types vanilla's consequences read: the carry-capacity, regeneration and health consumers name vanilla's own types ([#0513/M/n=1, #0514/C/C-only, #0516], [body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)), and whether a mod-registered type carries any Java effect at all is open [#0970/C/C-only/open].
A framework moodle is therefore a display, and anything the nutrient does to the body is written in Lua beside it, exactly as a mod trait's effect has to be [#1158/C/C-only].
Whether the framework itself goes through the vanilla registry, and so meets the same pinned level and the same duplicate-id hazard, belongs to the same unread interface ([#1140/C/C-only], [#1198/C/C-only]).

A moodle drawn through the framework also shares the screen with the mods resident beside it.
The interface mod resident on the target server redraws the status surfaces, and drawing through the framework or through a panel of the mod's own is the rule that keeps this mod out of that mod's widgets [#1083/C/snapshot].
Both server-specific readings are bounded to that server's mod list on the sweep's date, and both reopen the moment the list changes [#1070/C/snapshot, #1083/C/snapshot].

<a id="read-cadence"></a>
### Cache on the push, not on the frame

A client-side reader of the nutrition store reads a mirror, and the mirror changes only when a packet lands.
The server pushes the whole store in one unconditional snapshot once a second ([#0114], [wire-packets.md#player-stats-packet](../facts/wire-packets.md#player-stats-packet)).
Its whole nutrition payload is the store's five floats and nothing else [#1481].
Between two pushes the client's copy of the macros and the calories does not move, because the client arm of the nutrition update skips the decays that move the server's ([#1483], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
A reader that reads every frame therefore reads one value over and over until the next packet replaces it.
A mod can neither observe nor suppress the player-stats write, so a client-side reader cannot tie a redraw to the write and can only poll [#1149/M/n=1].

The one viewer mod this library tore down, `simpleStatus`, reads in exactly that way.
Its prerender prepares every bar unconditionally, and each bar's value is read once and then read again by the closures that label and colour it, with no cache anywhere on the path [#1477/C/C-only/superseded].
Nothing memoises, so the number of reads grows with the visible bars rather than with the number of changes.
Cache a nutrition value at the push cadence rather than the frame cadence, because the source changes once a second while an uncached interface reads it up to four times per macro bar and ten times per weight bar every frame, so about 59 of every 60 of those reads return the value the frame before already had [#1114/M/n=1].
The counts are a reading of that mod's code and the arrivals were measured in one session, so the rule is exact about what a per-frame read repeats and silent about what the repetition costs [#1114/M/n=1].
No shipped command measures frame time or Lua call counts, so the saving the rule buys is a count of avoided reads rather than a measured cost [#1477/C/C-only/superseded].

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
The band traits themselves are not on the player-stats packet and no other packet carrying them has been traced, so a band label drawn from the client's own trait list rests on nothing measured ([#0567], [#1161/C/C-only/open]).
A vanilla moodle is recomputed on the client from the mirror, so it is as late as the mirror and no later [#1143/C/C-only].
A mod's own values are on no vanilla packet: a client-side write of a vanilla nutrient number is overwritten within a second, while a mod's own field survives the push and simply desyncs, that second half read off the packet's field list rather than measured [#0129/M/n=1].
A mod value therefore reaches a panel only over a route the mod runs, the command bus or a transmitted modData table, and each route fails in its own way on a live server ([mp-model.md#command-bus](../platform/mp-model.md#command-bus), [mp-model.md#wipe-and-replace](../platform/mp-model.md#wipe-and-replace)).
The command bus is the route a mod controls end to end [#1153/C/C-only], while a player's modData is replaced whole by whichever mod on that client transmits it next [#1151/M/n=2].

A value a panel derives on the client, instead of fetching it, is only as good as its least-carried input.
The torn-down viewer derives its weight-direction suffix from the three uncarried flags, and it is right because the engine recomputes them from carried inputs; the technique is the dependency check rather than the derivation [#1508].
Its dependency list has one uncarried entry, the band traits, and writing that list down is the step the technique cannot skip [#1508].
That is the rule on checking every input of a derived display against the field list, and the rule on evaluating anything band-keyed on the server is its sharpest case ([#2052/C/inference], [#1104/C/inference]).
The staircase and flag readings in this section are one session on the dedicated-server path with one client and one character, and the weight arm was driven on the gain side only ([#1484/M/n=1], [#1490/M/n=1]).
The per-frame counts are the one worked viewer's, so another panel's cost follows its own read shape rather than that mod's.

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
A moodle is drawn from a level, by the engine or by a framework, and it is the only surface with consequences of its own ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)).
A client panel is code the mod owns end to end, drawn on the client from whatever the client holds, which is the shape the torn-down viewer takes [#1469].
Tooltip text is keyed per item: `Tooltip` is one of the item-level keys the script reference lists, and that reference's runtime-effect column gives it as a translated tooltip key ([#0215/C/snapshot], [food-item-model.md#script-keys](../facts/food-item-model.md#script-keys)).
A script tooltip line also becomes an item-modData key on every side that builds the item, so the text surface is not free of the modData surface ([#1044], [loader-and-scripts.md#default-moddata](../platform/loader-and-scripts.md#default-moddata)).
The vanilla food tooltip already carries a nutrition block, shown only to a character holding either Nutritionist trait, and that tooltip is the trait's one reader in the jar ([#0546/C/snapshot], [#0547/C/C-only]).
How that tooltip is built, and whether a mod can add a line to it, is outside what this library read, because the interface toolkit itself is unread [#2044/C/one-side/open].
Translation text resolves on the client alone: a mod's keys merge beside vanilla's, and a dedicated server resolves no display name at all ([#1163/M/n=1], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
The text router carries no item-name prefix, so a feature that must know whether a translation loaded is gated on an interface key rather than on an item name [#1720/M/n=2].
None of the three excludes the others: a design can show one nutrient as a moodle, the whole store in a panel and a food's character in its tooltip, and each choice is costed on its own.
Each row below names what the surface costs and the wall it runs into, with the verdict rows that decide both, in the wall map's own row order.

<a id="surface-options"></a>
### The three display surfaces

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| a moodle through `MoodleFramework` | a runtime dependency on a third-party workshop mod whose registration interface and multiplayer behaviour are unread and whose wholeness on this build is derived rather than booted; the level must be computed on a side that holds the nutrient, and vanilla's moodle consumers ([body-and-weight.md#moodles](../facts/body-and-weight.md#moodles)) name only vanilla's own types | a mod's own moodle type is pinned at its lowest level and vanilla's thresholds are unreachable, which leaves the framework as the only route; no run has seen a framework moodle render above its lowest level (`X29`) | [#1140/C/C-only], [#1141/C/C-only], [#1142/C/C-only], [#1115/M/n=1/open], [#0513/M/n=1] |
| a client panel | the whole panel is client code the mod owns: it caches at the push cadence, fetches any mod-owned value over the command bus or a transmitted table, and shares the screen with a resident interface mod | a client reads a pushed mirror and cannot observe the player-stats write; a cooked food's thirst reads halved on a client; the band traits travel on no traced packet (`X4`) | [#1147/M/n=1], [#1149/M/n=1], [#1161/C/C-only/open], [#1114/M/n=1] |
| tooltip and translation text | text keyed per item or per interface key and resolved on the client alone; a script tooltip line becomes an item-modData key on every instance | a mod's keys merge rather than shadow, so whether one can redefine a vanilla key is unmeasured (`X5`); a dedicated server resolves no display name; a new food without a translation entry ships a zero weight | [#1163/M/n=1], [#1164/C/C-only/open], [#1166/C/C-only], [#1167/M/n=1], [#1044] |

Which surface carries each nutrient the design shows: a framework moodle on a route no run has confirmed, a client panel the mod owns end to end, or keyed text that only a client resolves?

## Walls and bounds
<a id="walls"></a>

- A mod cannot register a new moodle type that works: registration reaches every character and the level is pinned at its lowest every tick ([#1140/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- A mod cannot retune a vanilla moodle's thresholds nor change what a moodle does: the class that holds the thresholds is unreachable from Lua ([#1141/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- No measured moodle route exists: the framework is the only route left, its wholeness is derived rather than booted, its interface is unread and no run has seen one of its moodles render ([#1142/C/C-only], [#1295/C/open, #0884/C/C-only/open], [open-questions.md#x29](open-questions.md#x29)).
- Nothing carries a moodle between the sides: each side recomputes its own from its own mirror, so a client's moodle is exactly as late as its stats ([#1143/C/C-only]).
- A mod cannot trust a zero-valued item field on a client, because it can arrive holding another item's value ([#1146/M/n=1]).
- A mod cannot trust a cooked food's thirst value read on a client, and neither can a display that draws it ([#1147/M/n=1], [wire-packets.md#cooked-thirst](../facts/wire-packets.md#cooked-thirst)).
- A mod cannot observe or suppress the player-stats write, so no panel can tie a redraw to the write ([#1149/M/n=1]).
- A trait a mod adds is selectable and saved but carries no effect of its own, so anything it should show or do is written in Lua ([#1158/C/C-only]).
- The trait sync path is untraced: the band traits are not on the player-stats packet and no packet that carries the trait list has been traced, so no client-side display can rely on a band trait ([#1161/C/C-only/open], [#1275/C/superseded], [open-questions.md#x4](open-questions.md#x4)).
- A mod cannot test a trait by its string name, because the string form is removed on this build ([#1162/C/C-only]).
- Translations are client-only: a mod's keys merge beside vanilla's and a dedicated server resolves no display name ([#1163/M/n=1], [mod-anatomy.md#translations](../platform/mod-anatomy.md#translations)).
- The translation override is unmeasured: the translator merges rather than shadows, and no run has shipped a key that redefines a vanilla one, so whether a rebalance may rename a vanilla food is not known ([#1164/C/C-only/open], [#1276/C/open], [open-questions.md#x5](open-questions.md#x5)).
- A mod cannot name its items through the older text-table layout ([#1165/M/n=1]).
- A mod cannot ship a food absent from the translation table without every client receiving its weight as zero ([#1166/C/C-only]).
- A mod cannot resolve or branch on an item name anywhere but the client's display-name getter ([#1167/M/n=1]).
- The read-cadence rule is one viewer's render loop read from its code against arrivals measured in one session, and no command measures frame time, so it bounds a count of reads rather than a cost ([#1114/M/n=1], [#1477/C/C-only/superseded]).
- Every client-side reading this page cites was taken on a dedicated server with one client, one fixture and one character, and single-player is never claimed ([#1256/C/one-fixture]).

Not covered: the engine's own interface toolkit, its widget set and its event surface; the vanilla food tooltip's layout beyond its one trait gate; `MoodleFramework`'s own Lua; the character screen's trait display; controller and split-screen input; and any measurement of frame time or draw cost — this library read none of them.

## Open
<a id="open"></a>

- Whether `MoodleFramework` loads whole on this build, whether its configuration file executes and whether a moodle registered through it renders above its lowest level — settled by a desk read of its own Lua that names its registration call, then one session reading its globals on both sides and the client's moodle block; -> X29 ([#1295/C/open, #0884/C/C-only/open, #1115/M/n=1/open], [open-questions.md#x29](open-questions.md#x29)).
- Whether any packet carries the character's traits to a client, and whether a trait the mod registers behaves the same — settled by making the server's trait list non-empty and reading the client's across at least two pushes, client first; -> X4 ([#1275/C/superseded, #0968/C/C-only/open, #1161/C/C-only/open, #0595/C/C-only/superseded], [open-questions.md#x4](open-questions.md#x4)).
- Whether a mod's translation file displaces a vanilla key or the merge keeps vanilla's — settled by a mod that redefines one vanilla item-name key and one vanilla interface key beside a new interface key that must hit in the same run; -> X5 ([#1276/C/open, #1164/C/C-only/open], [open-questions.md#x5](open-questions.md#x5)).
- Whether the moodle stat class is reachable from Kahlua at all — settled by a global read of that class beside two exposed controls that must answer in the same call; -> X2 ([#1274/C/open], [open-questions.md#x2](open-questions.md#x2)).
- Whether a mod-registered moodle type carries any Java effect — settled by a session that registers one and reads what its level drives, which no named experiment runs; the register files the row under X2 ([#0970/C/C-only/open], [open-questions.md#x2](open-questions.md#x2)).
- Whether the engine's interface toolkit offers a panel anything beyond what one viewer mod's code shows — settled by a read of the toolkit's panel and event classes; no experiment id ([#2044/C/one-side/open], [overview.md#coverage](../platform/overview.md#coverage)).
- That a mod's translation file at a vanilla relative path costs vanilla nothing is unverified, and its owner states it with its bound ([#1340/M/n=1/unverified], [mod-anatomy.md#open](../platform/mod-anatomy.md#open)).
- That the text route cannot reach the item-name table on either side is unverified for want of an in-run positive control, and its owner states it with its bound ([#0845/M/n=2/unverified], [mod-anatomy.md#open](../platform/mod-anatomy.md#open)).
- The design must decide whether any nutrient is shown as a moodle before the framework route is settled, because the framework is the only route and no run has seen one of its moodles above the lowest level [#1142/C/C-only, #1115/M/n=1/open].
- The design must decide whether this mod requires `MoodleFramework` on every server that runs it, because a moodle route through the framework makes a third-party mod a runtime dependency [#1142/C/C-only, #1070/C/snapshot].
- The design must decide which values its panel derives on the client and which it fetches from the server, because a derived value is right only while every input it reads is carried and the band traits are not [#1508, #1161/C/C-only/open].
- The design must decide whether its panel shows a band label at all while the trait sync path is untraced, because the client's trait list is filled by no traced packet [#1161/C/C-only/open, #0968/C/C-only/open].
- The design must decide how stale a displayed value may be, because a client panel cannot observe the player-stats write and draws a mirror late by up to one push plus its own refresh interval [#1149/M/n=1, #1486/M/n=1].
- The design must decide whether a cooked food's thirst is shown on a client at all, or re-derived from the script, because the client's getter reads a value halved once per hop [#1038/M/n=2].
- The design must decide whether it renames any vanilla food, because the translation override is unmeasured and the answer governs whether a rebalance may rename vanilla foods [#1164/C/C-only/open].
- The design must decide whether its numbers stay inside the display bands the torn-down viewer hard-codes, because those bands go wrong silently on a re-based scale [#1514, #1522].

## See also

- [`../platform/lua-platform.md`](../platform/lua-platform.md#registries) — the moodle and trait registries, and what each registration is worth.
- [`../platform/mod-anatomy.md`](../platform/mod-anatomy.md#translations) — the translation tables, the merge, and the dedicated server that resolves no display name.
- [`../platform/mp-model.md`](../platform/mp-model.md#what-a-client-copy-is) — what a client's copy of a server object is, and is not.
- [`../platform/lessons.md`](../platform/lessons.md#anti-patterns) — the framework, resident-interface and cooked-getter rules this page copies.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#staircase) — the staircase a client-side reader sees, and the band that grades it.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#cooked-thirst) — the cooked-food thirst value and its halving.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#moodles) — the vanilla moodles, their thresholds and what each level does.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md#mp) — the worked viewer: what a pure client reader can and cannot show.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#status) — the framework's layout and build status.
- [`new-nutrients.md`](new-nutrients.md#effect-paths) — the moodle surface as one of a new nutrient's effect paths.
- [`mp-sync.md`](mp-sync.md#sync-options) — the routes a mod-owned value takes to reach a client panel.
- [`testing-your-mod.md`](testing-your-mod.md#owned-experiments) — the experiments behind this page's walls, as this mod's own.
- [`open-questions.md`](open-questions.md#decisions) — the decisions above, beside every other area's.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows cited above.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments the open rows point at.
