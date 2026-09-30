# MP sync — the routes this mod's state travels
Verified against 42.20.4 (b0bbce05d5) · 2026-09-26 · scope: which side this mod owns each quantity on, the three routes its own state can travel between a dedicated server and its clients, how each route fails on a live server and what no route offers; the packet mechanisms are `platform/mp-model.md` and the field contracts `facts/wire-packets.md`

## Rules

- Run anything that changes what eating delivers where `Eat` runs, on the server, and carry its state by server mutation over the command bus, a parallel player-modData store transmitted on change, or client-only semantics: a multiplayer client never reaches `Eat`, so nothing it computes lands in the vanilla store the eat writes [#0128/C/inference, #0109].
- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or feed it an explicitly transmitted value: the band traits are not in the player-stats packet and no other packet was traced carrying the trait list [#1104/C/inference].
- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Never push an item stat field from a client: the item-stats send is the server's own call with no client-side counterpart, so on a client it does nothing at all — the one client-to-server item route is the item-fields sync, a different packet carrying modData and condition [#0330/C/C-only, #1240/C/C-only].
- Poll the server over the bus for a live item field rather than reading the client's copy: whether that copy advances is answered per arm and never once, and the three sessions that read one read it in three different arms of the same gate [#1423/M/n=1, #1111].
- Derive a client-side value from packet-carried inputs only with its dependency list written down and each input checked against the packet's field list: a derived value is desync-free only while every input is carried faithfully, and the band traits, a cooked food's thirst and a zero-valued conditional item field are not [#1508, #2052/C/inference].
- Overwrite every client-side prediction of a mod-owned value with the server's next answer: a client write to a vanilla store is erased by the next snapshot, but a write to a field no packet carries is never erased and drifts from the server's value instead [#0129/M/n=1, #2053/C/inference].
- Address an item in a bus round trip by its id and never by its display name: the id names the same instance on both sides of a single-bodied item, while a dedicated server resolves no display name at all [#1145/M/n=1, #2054/C/inference].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].

## How it works

A nutrition overhaul on a dedicated server asks the same question of every quantity it touches: which side computes it, which route carries it to the other side, and what the other side holds between arrivals.
The mechanisms that answer it are [`../platform/mp-model.md`](../platform/mp-model.md), and the payload of every packet involved is [`../facts/wire-packets.md`](../facts/wire-packets.md); this page restates neither.
What it adds is the reading for this mod: where each quantity has to live, which of the three routes a mod can choose each of its own values rides, and how each route fails once real clients and other mods share the server.
The page owns one rule and no fact: every claim below is cited to the row that owns it, and the untagged sentences are this mod's reading of those rows.
Every measured row it cites was read on the dedicated-server path with one real client attached, and single player is never claimed.

<a id="authority"></a>
### Which side this mod owns each quantity on

The authority question is settled before the design begins, because the eat itself runs on the server.
The client's timed action only queues it: the server's action manager performs the net action and reaches the character's eat call, while a multiplayer client never runs the completion step at all [#0110, #0109].
A cancelled eat resolves on the server too, through a net action that exists only there [#0111].
The eat packet's receiver fires the eat event and applies no numbers of its own, so a client-side handler on that path is told about an eat and changes nothing it delivered [#0116].
The eat event fires on both sides, so a handler that writes anything tests which side it is on before it writes [#1131/M/n=1].
The wall-map verdict is the same reading from the other end: a mod can run its intake math where the eat runs, and that is on the server [#1128/M/n=1].
Every nutrient this mod adds is therefore computed on the server, whatever store keeps it and whatever route shows it to the player, and the rule that follows sits with the options below ([Options](#sync-options)).

The vanilla stores the mod reads have one owner each, and it is always the server.
The nutrition object is the server's, and a multiplayer client holds a mirror of it [#0125/M/one-fixture].
A client does not run the drain at all, because the nutrition update skips the macro decay and the calorie update on a game client [#0117].
Hunger and thirst tick on the server only, and endurance and fatigue are the server's in the same way [#0560/M/n=1, #0561, #0562/C/C-only].
A client-side write to any of those stores is erased by the next player-stats snapshot, which is what gives each of them exactly one owner ([#0568/M/n=2], [mp-model.md#routes-client-to-server](../platform/mp-model.md#routes-client-to-server)).
A mod that retunes the hunger and thirst constants has to do it on the server for the same reason: the updater that reads them runs there [#0569/C/C-only].
Each eat's own packet overwrites the receiver's whole nutrition object as well, so a client-side change to that store survives no eat [#0113].
Two further values cross by a route that is neither item packet, the Cooking perk level and the inventory weight a capacity bar draws, and both read identically on the two sides [#0353/M/n=1, #1499/M/n=1].
What the client holds of all of these is the result of the last push that reached it, never a simulation of the server's object ([mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is)).

Weight is the one vanilla quantity whose ownership splits by field, and a nutrition overhaul reads every one of its fields.
The server owns the value and the client never computes it: the weight update skips before the setter on a client, while the three direction flags are written ahead of that skip and stay readable client-side [#1238/M/n=1].
Those flags are not packet fields, and each side's own computation of them agreed with the other's on both non-trivial arms [#0900/M/n=1].
The client may therefore show which way the weight is moving, and may never show a weight of its own [#1139/M/n=1, #1138/M/n=1].
The band traits are applied on the server, and no packet has been traced carrying them to a client [#1239/C/C-only].
Anything this mod keys on a band is therefore evaluated on the server or fed a value the mod sends itself [#1104/C/inference].
Whether a client can rely on a band trait at all is an open verdict rather than a wall, and it is listed under [Open](#open) [#1161/C/C-only/open].

On the item side the server owns the whole lifecycle.
The container hooks that fire as an item enters or leaves a container are server-gated, and the cook transition runs on the server [#0327, #1417/M/n=1].
The item-state values the item packet carries are pushed from the server only, and there is no client-to-server item-stats route [#1240/C/C-only].
The aging fields never cross at all, so the freshness a client shows is whatever the last full serialisation of the item left behind ([#1242/M/n=1], [#0357/C/inference]).
Whether a client's copy of an item advances between pushes is answered per arm and never once, so a design that needs a live item value asks the server for it [#1423/M/n=1].
For a value this mod attaches to an item, the design picks between two kinds of owner.
A value written in the item script has no run-time owner, because both sides load the same script and nothing syncs it [#1124/M/n=1].
A value written into item modData belongs to whichever side wrote it last, because the item-fields sync wipes the receiver and copies the sender's keys — a reading measured in the client-to-server direction only [#1241/M/one-side].

The mod's own per-player store has no vanilla owner, so the design assigns one.
Character, item and global modData are the only durable mod state the engine saves, which makes one of them the store whichever route carries its copies [#1122/C/C-only].
Player modData is a table both sides hold a copy of, and it does not cross until something transmits it [#0913/M/n=1].
The server is the only side that can own that store, because the intake that changes it completes there.
A server-side table or global modData is set up on the global-mod-data init hook or the server-started hook, the pair read as surviving a dedicated server where the player-creation, game-start and load hooks never fire [#0895/C/one-side].
The client's copy is then a display mirror, and how that mirror is refreshed is exactly the choice the options table puts.
A mirror refreshed on the mod's own command is late by one round trip, while a mirror refreshed by a server-side transmit is as current as the server's last call, and any transmit from that client in the meantime writes the client's copy back over the server's [#1042/M/n=2].

Two quantities have no owner at all, and both reach the player's screen.
Moodles are recomputed on each side from that side's own stats and are absent from the player-stats packet, so a client's moodle is a function of its mirror [#1245/C/C-only].
A client-side moodle read taken straight after a server-side write can therefore lag by up to one push [#0570/C/C-only].
Item display names are the other gap: a dedicated server resolves none, so no server-side decision may branch on one [#0848/M/n=1].

Which side a file runs on is an authority question of its own, and the folder does not answer it.
A mod's `server/` files also execute in the multiplayer client's Lua state, so a write the design gives to the server needs a runtime side test in the file [#1174/M/n=1].
The consequence shows up in the mod's own writes: an item-modData write in a mod's `server/` file came from the client's Lua state while the server's own tick skipped on its guard, so a census of writers records the side [#0910/M/n=1].

The ownership reading, one line per quantity:

| quantity | owner | what the other side holds | tags |
|---|---|---|---|
| the intake: an eat and a cancelled eat | server | a notification that applies no numbers | [#0110, #0111, #0116] |
| the vanilla nutrition store and the player stats | server | a mirror the next player-stats snapshot overwrites | [#0125/M/one-fixture, #0568/M/n=2] |
| weight | server | the three direction flags, computed on each side, and never a weight of its own | [#1238/M/n=1, #0900/M/n=1] |
| the weight-band traits | server | nothing traced | [#1239/C/C-only, #1161/C/C-only/open] |
| item state in the item packet | server | the last push, stale in any zero-valued conditional field | [#1240/C/C-only, #0343] |
| item aging | server | nothing: the fields never cross | [#1242/M/n=1] |
| a per-item mod value in the item script | neither: both sides load it | the same value | [#1124/M/n=1] |
| a per-item mod value in item modData | the last writer | a wholesale copy, measured client to server only | [#1241/M/one-side] |
| the mod's per-player store | server, by this mod's design | a mirror on the route the options choose | [#1122/C/C-only, #0913/M/n=1] |
| moodles | neither: each side recomputes | its own recompute from its own mirror | [#1245/C/C-only] |
| item display names | client | nothing on a dedicated server | [#0848/M/n=1] |

<a id="failure-modes"></a>
### How each route fails on a live server

The transmit and the engine's own pushes fail silently: nothing raises, nothing logs, and the value a reader sees afterwards is plausible ([#0916/C/C-only], [#1495]).
The three fail at three different moments: the transmit whenever any mod on the client calls it, script data at the join, and the bus wherever the mod's own handler does.
The eat packet beneath the intake is no louder, because its send leaves no line in any log a probe can read [#0131/M/n=1].
A silent failure is therefore found by a paired read of both sides or not at all, which is why every driver reads the client first and the server second ([harness.md#probes](../platform/harness.md#probes)).

The transmit fails by moving too much rather than too little.
It serialises the whole player-modData table, and the receiver wipes its copy before it writes, so an empty sender wipes the receiver outright [#1091].
From the client, one transmit makes the server's copy exactly the client's, including the loss of any key only the server held [#0914/M/n=2].
From the server, the same wipe-and-replace shape holds on a thinner bound [#0915/M/n=1].
The mod that loses a key is not the mod that transmitted.
A client-only interface mod fires the call from its own input handlers, and each of those sites rewrites the server's whole copy of that player's table ([#1482], [simplestatus.md#mp](../facts/other-mods/simplestatus.md#mp)).
A mod that never transmits at all still has its whole nested table carried to the server the first time something else on that client transmits [#1088/M/n=1].
A server-only key in player modData therefore lives until a neighbour's user drags a panel, which is why the wall map allows server-authoritative state there only with a workaround [#1151/M/n=2].
What crosses is decided by type: strings, numbers, booleans and nested tables travel, while functions and Java objects are dropped with no error ([#1495], [wire-packets.md#moddata-packet](../facts/wire-packets.md#moddata-packet)).
A nested table crosses whole and keeps its shape, so an empty table reads on the far side exactly as it left [#1337/M/n=1].
The call also returns silently when the object's square is null, so from outside a skipped transmit and a dropped key look the same [#0916/C/C-only].
A census of the table is time-dependent besides, because the server writes the vanilla fitness keys into its copy lazily after join [#1338/M/n=2].
And whether any of the table survives a save and reload is read from the code and never measured, so the route's durability is a code reading until the persistence run lands [#1122/C/C-only].

Script data fails at the join rather than during play.
Every loaded script file, the mod's own included, feeds one checksum the server compares when a client joins, so a mismatch is a disconnect rather than a degraded value, and no arm of that gate has been measured [#1182/C/C-only].
The checksum drops every carriage-return byte before it folds a file in, so the files must match byte for byte on both sides apart from their line endings [#1182/C/C-only].
A script fixes a type's default at load, so it cannot follow anything that happens to one instance or one player: a cook, a spoil or a per-player adjustment travels on one of the other two routes or does not travel.
Where a per-instance change lands in a field the item packet does not carry, a Lua write on the server stays on the server, and the client's copy is left wrong in a way no re-push repairs ([#1076/M/n=1], [#1037/M/n=1]).
That is the measured cost of a Lua write where a script value would have served [#1074/M/n=1].
The script route's one guarantee is also its limit: a script value is identical on both sides because both sides loaded the same file, and nothing about it was ever sent.

The command bus fails only where the mod's own code does.
It carries no wipe and depends on no packet's field list, which is why the wall map lists it as a route a mod can simply use [#1153/C/C-only].
Its costs are structural rather than silent: both ends must be written, a round trip moves a value and stores nothing, and the module name shares one namespace with every other mod's command sites ([mp-model.md#command-bus](../platform/mp-model.md#command-bus)).
Durability therefore comes from a store beside the bus, never from the bus itself.
A client that joins after the mod's last answer holds no copy until the mod sends one, so a mirror kept over the bus needs a send when a player arrives as well as when a value changes.
A handler that raises unguarded loses the rest of its own body while the handlers registered behind it keep running, so the failure is a half-applied mutation rather than a dead bus ([#0948/M/n=1], [#0896/C/C-only], [lua-platform.md#raises](../platform/lua-platform.md#raises)).
A value the bus delivers is a snapshot the server sent, and a client-side prediction written beside it is corrected by nothing: a client write to a field the player packet does not carry is outside the snapshot that erases a vanilla write, so it drifts from the server's value instead — an arm read off the packet's field list rather than measured [#0129/M/n=1].
Addressing an item over the bus rests on the item id naming the same instance on both sides, the workaround the wall map gives for a per-item value [#1145/M/n=1].
That holds for a single-bodied item, while whether an item whose script body several mods append can put a stale id on the wire is the unread net-id question listed under [Open](#open) [#1063/C/C-only/open].

Client-only semantics — deriving a value on the client from inputs both sides already hold — is the third shape the rule under [Options](#sync-options) names, and it rides the routes above rather than being one of them.
It fails the moment one input is not carried, which makes the dependency list rather than the derivation the technique [#1508].
The weight-direction flags are the worked case: they agreed on both sides at every snapshot, but on a character holding no band trait, so their dependency on the band is untested [#1490/M/n=1].
A client-side reader of that kind gets things right and wrong along one line, the packet's field list, and along no other [#1523/M/n=1].
The same check applies to anything the mod sends in a table: one key holding a flat table of scalars carries every type the wire keeps and none it drops, a property worth checking deliberately rather than discovering later [#1509].

The engine's own pushes sit underneath all three routes, and a design that reads a vanilla value on the client inherits their failures.
A client-side reader of the nutrition store is a staircase that steps when a packet lands while the server ramps, so a cross-side gap is a timing reading and never float noise ([#1483], [wire-packets.md#staircase](../facts/wire-packets.md#staircase)).
Every macro gap measured against its band landed inside it, so what a client draws from that store is the server's value, late and otherwise right [#1486/M/n=1].
The weight the client mirrors is narrowed to a float on the wire and widened back on arrival, so the two sides' weights are never equal to the bit and equality is the wrong test [#1487/M/n=1].
An eat's own push reaches the client as a single step some seconds after the player queued it, so a client-side display of an eat changes only once the server has completed the action and pushed the result [#0121/M/n=2].
On the item side, a zero-valued conditionally-written field arrives carrying whatever the reused packet object last held, because the receiver keeps one packet object per type with no reset ([#0343], [mp-model.md#cached-packet](../platform/mp-model.md#cached-packet)).
A cooked food's thirst change is halved once per server-to-client hop, a vanilla transformation that any mod reading that getter on a client inherits ([#1038/M/n=2], [wire-packets.md#cooked-thirst](../facts/wire-packets.md#cooked-thirst)).
Four item fields desync whole across a cook, and nothing later repairs them ([#1037/M/n=1], [wire-packets.md#desyncs](../facts/wire-packets.md#desyncs)).
Item modData fails before any mod writes to it: the two sides' tables differ on an untouched item, the client's copy carrying a custom-name key the server's copy lacks [#1639/M/n=1].
A census that tests an item's table for emptiness therefore counts keys and excludes that key always, and the tooltip key for any item whose script declares one [#1415/M/n=1].
The item-fields sync that carries item modData is measured in the client-to-server direction only, so the direction a server-owned per-item value would need is a question under [Open](#open) [#1241/M/one-side].

## Options

<a id="sync-options"></a>
### The three routes this mod's own state can travel

Anything that alters what eating delivers to a multiplayer player has to run where `Eat` runs, on the server, so the three viable shapes are mutating on the server over the command bus, keeping a parallel store in player modData and calling `transmitModData()` on change, or accepting client-only semantics [#0128/C/inference].
The table below lists the three routes a mod's own state can travel: the command bus, the player-modData transmit, and script data loaded per side.
The engine's own packets are not a route on this list, because a mod can cause one to fire and cannot change what it carries ([mp-model.md#packets](../platform/mp-model.md#packets)).
The rows follow the wall map's order.

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| `transmitModData` on player modData | no protocol to write and a store the engine saves, at the price of moving the whole table in both directions on a call any mod on that client can make; only strings, numbers, booleans and tables cross | no part of the table can be sent alone, and server-authoritative state survives there only with a workaround, because the transmit that replaces it is another mod's call | [#1123/M/n=2, #1151/M/n=2, #1152/M/n=2, #1495] |
| script data loaded per side | nothing at run time, since both sides load the same file; the value is a type's default fixed at load, so no per-instance or per-player change can ride it, and every shipped script file must match byte for byte on both sides apart from its line endings | a script mismatch disconnects the joining client rather than degrading; a per-instance value falls back to item modData or the bus | [#1124/M/n=1, #1145/M/n=1, #1182/C/C-only] |
| the command bus | both ends written by the mod, a store beside it for anything durable, and one namespace shared with every other mod's command sites; the one route whose payload, timing and direction the mod chooses | none of its own; it inherits the two push walls — no player stat and no item stat field can be pushed from a client — so every authoritative write it carries is made on the server | [#1153/C/C-only, #0932, #1149/M/n=1, #1150/C/C-only] |

Which route does each quantity this mod owns travel on: the command bus, a player-modData transmit, or script data loaded per side?

## Walls and bounds
<a id="walls"></a>

- No route adds a field to the item packet, or lets a mod value depend on a field the packet omits: the class has no per-field opt-in [#1144/M/n=1].
- No route makes a zero-valued item-packet field trustworthy on a client: the reused packet object supplies the value the sender skipped [#1146/M/n=1].
- No route makes a cooked food's thirst value trustworthy on a client: the packet sends one getter and the receiver stores it through another [#1147/M/n=1].
- No route pushes a player stat from a client, or observes or suppresses the player-stats write: the snapshot is unconditional and carries no filter [#1149/M/n=1].
- No route pushes an item stat field from a client: every arm of the item-stats send is a server-to-client fan-out [#1150/C/C-only].
- No route transmits part of player modData: the packet sends the table and the receiver wipes before it writes [#1152/M/n=2].
- No route lets the client compute a weight: the weight update skips before the setter on a client [#1138/M/n=1].
- No route survives a script mismatch between the two sides: the join checksum disconnects the client [#1182/C/C-only].
- Player modData holds this mod's nutrient only with a workaround, because the transmit is a whole-table wipe and replace in both directions [#1123/M/n=2].
- Player modData holds server-authoritative state only with a workaround, because the transmit that destroys it is somebody else's call [#1151/M/n=2].
- Item modData holds a per-item value only with a workaround, because the sync wipes the receiver before it copies the sender's keys [#1126/M/one-side].
- A per-item mod value reaches the client only with a workaround — a script value, item modData, or a bus round trip keyed on the item id [#1145/M/n=1].
- Server-only logic stays on the server only with a workaround, a runtime side test, because a mod's `server/` files also run in the client's Lua state [#1174/M/n=1].
- The command bus is the one route with no wall of its own: it has no wipe and no packet dependency [#1153/C/C-only].
- Every measured reading this page cites was taken on the dedicated-server path with one real client, one fixture, and one character or one item per arm, and none of them speaks for single player.
- No arm was taken with more than one client attached, so nothing here says what a second client's copy holds, or whether a push reaches every client or only the one it concerns.

Not covered: the transport beneath every packet, the save and load round trip that an item's serialised blob and every modData table travel on, global modData's own transmit, every packet outside the food, nutrition, item-fields and player-modData set, and anything a listen server or a second attached client would change.

## Open
<a id="open"></a>

- Whether item modData moves server to client through the item-fields sync — settled by a run in which the writing mod's `server/` file is guarded so only the server's Lua state writes, a pre-sync client read that must miss, then a forced sync and a census of both sides; until then a server-owned per-item value in item modData is an unmeasured direction; -> X14 ([#0885/M/n=1/open, #1040/M/one-side/open, #1280/C/open], [open-questions.md#x14](open-questions.md#x14)).
- Whether the per-body net-id reallocation of an item whose script body several mods append ever puts a stale id on the wire — settled by reading the item id on both sides after a multi-bodied redefinition, the single-bodied item being the control; until then the id-keyed bus round trip is read for a single-bodied item only; -> X27 ([#1063/C/C-only/open, #1293/C/open], [open-questions.md#x27](open-questions.md#x27)).
- Whether modData survives a save and reload — settled by a boot, a write, a teardown and a second boot on the same run directory, against a control boot of the golden fixture that must miss the key, read in both the player and the item scope; the durability every route above leans on is a code reading until then; -> X28 ([#1294/C/open], [open-questions.md#x28](open-questions.md#x28)).
- Whether the weight-band traits reach a multiplayer client at all — settled by driving a character into a band on the server and reading the client's trait list; until then a band is an input a client-side derivation cannot trust; -> X4 ([#0968/C/C-only/open, #1275/C/superseded, #0595/C/C-only/open, #1161/C/C-only/open], [open-questions.md#x4](open-questions.md#x4)).
- Whether a mod may call the latent client-to-server eat route, a route for the vanilla store that no caller uses — settled by calling the game client's eat-food method from a mod and reading both sides; no `X` id ([#0145/C/snapshot/open], [mp-model.md#open](../platform/mp-model.md#open)).
- What the server validates on an incoming nutrition write — settled by a probe that separates rejection from overwrite; each probe in the library shows the next push overwriting a client write, which is the ownership this page reads rather than a validation; no `X` id ([#0191/M/n=1/open], [mp-model.md#open](../platform/mp-model.md#open)).
- Whether a relog or a save round trip repairs a client's copy of the uncarried item fields — settled by a relog read of a cooked item on both sides; no `X` id ([#1434/C/inference/open], [wire-packets.md#open](../facts/wire-packets.md#open)).
- The wall that a mod cannot trust a live item field's client copy to tick is unverified: its reading rests on a restricted artifact key and one item in one window, and the multiplayer page's open list states the restriction ([#1148/M/n=1/unverified], [mp-model.md#open](../platform/mp-model.md#open)).
- Decision: which route each quantity this mod owns travels on — forced by the three routes failing three different ways: the transmit replaces a whole table on another mod's call, a script value is fixed per type at load and checksummed at the join, and the bus stores nothing [#1151/M/n=2, #1182/C/C-only, #1153/C/C-only].
- Decision: where the authoritative copy of the mod's per-player store lives — a server-side table or global modData mirrored down over the bus, or player modData kept complete on the client before any transmit — forced by one client transmit making the server's copy exactly the client's [#1042/M/n=2, #1088/M/n=1].
- Decision: whether any value the client displays is derived on the client or always sent from the server — forced by the band traits being in no traced packet and by the cooked-thirst halving [#1161/C/C-only/open, #1038/M/n=2].
- Decision: whether a per-item mod value is fixed per type in the script or carried per instance — forced by a script value being identical on both sides for free while the item-modData route is measured in one direction only [#1124/M/n=1, #1241/M/one-side].
- Decision: whether the design leans on modData surviving a restart before the persistence run lands — forced by persistence being read from the code and never measured [#1122/C/C-only].
- Decision: whether item round trips are keyed on the item id before the net-id run lands — forced by the per-body reallocation being unread for an item several mods append to [#1063/C/C-only/open].

## See also

- [`../platform/mp-model.md`](../platform/mp-model.md) — the ownership rows, the routes, the packets, the cached packet object, the wipe and the command bus that every reading here cites.
- [`../facts/wire-packets.md`](../facts/wire-packets.md) — the field contract of each packet, the measured desyncs, the staircase and the cooked-thirst halving.
- [`../platform/lessons.md`](../platform/lessons.md) — the sync rules this page copies, and the authority filters that come with them.
- [`../platform/lua-platform.md`](../platform/lua-platform.md) — which side each hook fires on, and what an unguarded raise inside a bus handler aborts.
- [`../platform/harness.md`](../platform/harness.md) — the paired client-first read, the only way a silent sync failure is ever seen.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) — the client-only mod whose input handlers fire the transmit that wipes a neighbour's keys.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) — the mod that never transmits and has its table carried to the server anyway.
- [`new-nutrients.md`](new-nutrients.md) — where the mod's nutrient store is chosen; this page supplies the route it travels.
- [`item-pass.md`](item-pass.md) — script data as the item route, and the checksum it ships under.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md) — the server-side seats the intake math sits in.
- [`ui-and-moodles.md`](ui-and-moodles.md) — what a client-side reader may draw from the mirrors this page describes.
- [`testing-your-mod.md`](testing-your-mod.md) — how a cross-side comparison of this mod's own values is graded.
- [`open-questions.md`](open-questions.md) — the experiments this page's open rows point at.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows cited above by register id.
- [`../reference/experiments.md`](../reference/experiments.md) — the specs of the named experiments.
