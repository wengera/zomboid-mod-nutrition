# MP sync — the routes this mod's state travels
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: which side this mod owns each quantity on, the three routes its own state can travel between a dedicated server and its clients, how each route fails on a live server, the pushes server Lua can cause and which client each reaches, global modData as the world's store, and what no route offers; the packet mechanisms are `platform/mp-model.md` and the field contracts `facts/wire-packets.md`

## Rules
<a id="rules"></a>

- Run anything that changes what eating delivers where `Eat` runs, on the server, and carry its state by server mutation over the command bus, a parallel player-modData store transmitted on change, or client-only semantics: a multiplayer client never reaches `Eat`, so nothing it computes lands in the vanilla store the eat writes [#0128/C/inference, #0109].
- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or push the trait list after you write it as [the trait-push rule](../areas/mp-sync.md#rules) says: the band traits are not in the player-stats packet; they reach the affected player's client on the player-fields packet's trait block and on the timed experience packet, each as fresh as its last push, and no player-addressed push refreshes another client's copy [#2727/C/inference] [#2595/C/C-only] [#2606/C/C-only] [#2603/C/C-only] [#2612/C/C-only].
- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Never push an item stat field from a client: the item-stats send is the server's own call with no client-side counterpart, so on a client it does nothing at all — the one client-to-server item route is the item-fields sync, a different packet carrying modData and condition [#0330/C/C-only, #1240/C/C-only].
- Poll the server over the bus for a live item field rather than reading the client's copy: whether that copy advances is answered per arm and never once, and the three sessions that read one read it in three different arms of the same gate [#1423/M/n=1, #1111].
- Derive a client-side value from packet-carried inputs only with its dependency list written down and each input checked against the packet's field list: a derived value is desync-free only while every input is carried faithfully, a cooked food's thirst change and a zero-valued conditionally-written item field are not, and the weight-band traits arrive only on the experience and trait-block pushes, as of the last push [#1508, #2731/C/inference] [#0567] [#2595/C/C-only] [#1146/M/n=1] [#1147/M/n=1].
- Overwrite every client-side prediction of a mod-owned value with the server's next answer: a client write to a vanilla store is erased by the next snapshot, but a write to a field no packet carries is never erased and drifts from the server's value instead [#0129/M/n=1, #2053/C/inference].
- Address an item in a bus round trip by its id and never by its display name: the id names the same instance on both sides of a single-bodied item, while a dedicated server resolves no display name at all [#1145/M/n=1, #2054/C/inference].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Push the trait block with `sendSyncPlayerFields(player, 2)` after any server-side trait write, and expect only the affected player's own client to receive it: a trait write fires no event and sends no packet, the once-a-second experience push also refreshes that client's trait list, measured carrying a server trait write within about half a second with no push at all, so the mod's own push buys freshness within that second rather than being the only route, and every player-addressed server send reaches that player's connection alone [#2693/C/inference] [#2759/M/n=3] [#2601/C/C-only] [#2595/C/C-only] [#2608/C/C-only] [#2603/C/C-only].
- Re-read a client's copy of a server-written value only after the push that carries it has landed: the engine refreshes the stats, the experience object, the body-part health, and the injuries and damage on timed pushes of their own, the experience object on the stats snapshot's cadence, the body-part health on a faster one and injuries and damage on a slower one, while `syncPlayerStats`, `syncBodyPart` and `sendSyncPlayerFields` push now to that player's own client, a value no timed push carries arrives only on such a call, and a call is no proof of delivery, so a read taken before the carrying push sees the previous value [#2743/C/inference] [#2608/C/C-only] [#2609/C/C-only] [#2405/C/C-only] [#2607/C/C-only] [#2602/C/C-only] [#2603/C/C-only].
- Send a mod-owned value to the client over the mod's own command bus, never through a framework that has no transport: a client-side library such as `MoodleFramework` sends, receives and transmits nothing and keeps its values in a per-client table, so a server-authoritative value reaches it only when the mod's own `sendServerCommand` delivers it to a client handler that hands it over [#2695/C/inference] [#2540/C/inference] [#2537/C/C-only] [#2538/C/C-only] [#1153/C/C-only].

## How it works

A nutrition overhaul on a dedicated server asks the same question of every quantity it touches: which side computes it, which route carries it to the other side, and what the other side holds between arrivals.
The mechanisms that answer it are [`../platform/mp-model.md`](../platform/mp-model.md), and the payload of every packet involved is [`../facts/wire-packets.md`](../facts/wire-packets.md); this page restates neither.
What it adds is the reading for this mod: where each quantity has to live, which of the three routes a mod can choose each of its own values rides, and how each route fails once real clients and other mods share the server.
The page owns its rules and no fact: every claim below is cited to the row that owns it, and the untagged sentences are this mod's reading of those rows.
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
Hunger and thirst tick on the server only, and endurance and fatigue are the server's in the same way [#0560/M/n=1, #2596/C/C-only, #0562/C/C-only].
A client-side write to any of those stores is erased by the next player-stats snapshot, which is what gives each of them exactly one owner ([#0568/M/n=2], [mp-model.md#routes-client-to-server](../platform/mp-model.md#routes-client-to-server)).
A mod that retunes the hunger and thirst constants has to do it on the server for the same reason: the updater that reads them runs there [#0569/C/C-only].
Each eat's own packet overwrites the receiver's whole nutrition object as well, so a client-side change to that store survives no eat [#0113].
Two further values cross by a route that is neither item packet, the Cooking perk level and the inventory weight a capacity bar draws, and both read identically on the two sides [#0353/M/n=1, #1499/M/n=1].
What the client holds of all of these is the result of the last push that reached it, never a simulation of the server's object ([mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is)).

Weight is the one vanilla quantity whose ownership splits by field, and a nutrition overhaul reads every one of its fields.
The server owns the value and the client never computes it: the weight update skips before the setter on a client, while the three direction flags are written ahead of that skip and stay readable client-side [#1238/M/n=1].
Those flags are not packet fields, and each side's own computation of them agreed with the other's on both non-trivial arms [#0900/M/n=1].
The client may therefore show which way the weight is moving, and may never show a weight of its own [#1139/M/n=1, #1138/M/n=1].
The band traits are applied on the server, and the trait list reaches that player's own client on two server pushes, the once-a-second experience packet and the player-fields packet's trait block [#2595/C/C-only].
Anything this mod keys on a band is therefore evaluated on the server, or the mod pushes the trait list after each server-side write, and a client's copy of a band is as fresh as the last of those pushes [#2727/C/inference].
Measured, a client-side read sees a trait the server has just written within about half a second with no push of the mod's own, and a removal the same way [#2759/M/n=3]; a server-side trait-block push in the same tick brings the arrival to 17-32 ms after the push stamp, against no-push lower bounds of 53-370 ms [#2099/M/n=6] ([wall map](../reference/wall-map.md#g4)).

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
A server-side table or global modData is set up on the global-mod-data init hook or the server-started hook, the pair read as surviving a dedicated server where `OnCreatePlayer`, `OnGameStart` and `OnLoad` never fire [#0895/C/one-side].
`OnNewGame` does fire on a dedicated server, with the new `IsoPlayer`, for every character a client creates, so a new character's row can be seeded there, and a row missing for an older character is created when first needed ([#2387/C/C-only], [server-lifecycle.md#creation](../platform/server-lifecycle.md#creation)).
A world-scoped table is created whenever it is missing rather than only when the world is new, as [Global modData](#global-moddata) states.
The client's copy is then a display mirror, and how that mirror is refreshed is exactly the choice the options table puts.
This mod's own global-modData store attaches on the global-mod-data init hook and a mirror of its record reaches the client's server-command handler within the session: in the acceptance re-run the server's store held the player's record at version 1 and the client's mirror read that player's name, version 1 and mode 1, one mirror received, though the run does not say whether the first-sight send or the answer to the client's own request carried it [#2748/M/n=1].
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
| the weight-band traits | server | the trait list as of the last experience push or trait-block push, the experience push measured landing within about half a second of a server write | [#2595/C/C-only] [#2759/M/n=3] |
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
The table survives a clean save and reload, both a server-written and a client-transmitted key read back on the server after a second boot [#1294/M/n=1].

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

<a id="server-pushes"></a>
### Pushes server Lua can cause

A mod's server code does not have to wait for the engine's timers to refresh a player's client: the Lua globals below push a player's state at the moment they are called, and how each is gated is [mp-model.md](../platform/mp-model.md#sync-globals)'s.
`sendSyncPlayerFields(player, mask)` sends the player-fields packet, does nothing off a server, and returns silently for a player with no online id, so a call is no proof that the client received anything [#2602/C/C-only].
`syncPlayerStats(player, mask)` sends the player-stats sync packet and `syncBodyPart(part, mask)` the body-part packet, each only on a server [#2607/C/C-only].
What each bit of each mask selects is the field contract of [the player-fields packet](../facts/wire-packets.md#player-fields-packet), [the player-stats packet](../facts/wire-packets.md#player-stats-packet) and [the body-part packet](../facts/wire-packets.md#body-part-packet), and this mod reads it there.

All three reach one client.
A server send addressed to a player reaches that player's own connection only, and the three globals, the engine's timed per-player pushes and the eat packet all send that way, so each refreshes the affected player's own client and no other client's copy of that player [#2603/C/C-only].
A value this mod shows on another player's character therefore needs a send the mod addresses to each client that draws it, because none of these pushes reaches a second client.
The injury diff a watching player asks for is a server channel that does reach a second client, and its send is triggered by a change in health, pain or infection only [#2610/C/C-only].
A `SyncXp` from a connection holding the stats-panel capability is relayed to every other fully connected client [#2612/C/C-only], and a global modData table the server transmits reaches every connection, as [Global modData](#global-moddata) states.

The trait bit is the push a nutrition mod is most likely to need, because the band traits are the server's.
No Java code sends it: the server's player-fields send has no Java caller that sets the trait bit, its callers being the Lua global, the eat with mask `8` and the exercise repetition with mask `32` [#2604/C/C-only].
Among vanilla Lua's callers of the global, a finished book read sends the trait bit, with recipes and read books, in mask `0x07` [#2606/C/C-only].
A trait write itself fires no event and sends no packet, so a trait the server adds or removes reaches the client only on the next push that carries the list [#2601/C/C-only].
The experience push is one such push, refreshing the owning client's whole trait list on the stats snapshot's cadence, so a mod's own trait-bit push buys freshness inside that interval and is not the only route ([#2608/C/C-only], [#2595/C/C-only]).
Measured on a live server with no push sent, a server-written trait reached the owning client within about half a second in three trials, and a removal left it the same way, the arrival the once-a-second experience push predicts [#2759/M/n=3].
A trait the mod registers arrived the same way on a client loading the same mod [#2760/M/n=1], and its list name is the path of its id alone, so a test of the list matches that path and never the full id [#2761/M/n=1].
A server-side trait-block push (`sendSyncPlayerFields(player, 2)`) in the same tick as the trait write arrives sooner, within tens of milliseconds against up to about half a second with no push (measured through the harness's `trait.add.push`) ([mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)) [#2099/M/n=6].
A model-driven band crossing's trait reached the client 61 ms after the boundary estimate [#2912/M/n=1].

The weight-trend flags arrive with the weight on the stats packet, but with `Nutrition` on they are vanilla's `updateWeight` values, so a server mod's flag write does not reach the client as written [#2884/M/n=1][#2644/C/C-only].
The stats packet's nutrition save carries the weight [#2628/C/C-only] and the update that writes the flags returns with the option off [#0555], so the flags a server write sets did not reach the client at any read across a session [#2911/M/n=1].

Beside the globals the server runs timed pushes of its own, which a mod can read and can neither retime nor reshape.
The experience object goes to each fully connected player's own connection on the stats snapshot's cadence [#2608/C/C-only].
Injuries and damage go together on a slower limit of their own [#2609/C/C-only].
A client-side reader of any of these values therefore holds the last push's copy, and a read taken straight after a server-side write sees the value before it until the carrying push lands.

The client-to-server direction is narrower.
The one client route for experience, and with it the trait list, is `SyncXp`, which the server accepts only from a connection whose role holds the `CanModifyPlayerStatsInThePlayerStatsUI` capability, so an ordinary player's client cannot push its own traits [#2612/C/C-only, #2595/C/C-only].
Every authoritative write this mod makes to a player's state is therefore made on the server and announced by one of the pushes above or by the mod's own bus.

<a id="global-moddata"></a>
### Global modData as a per-world store

Global modData is the one durable store this mod can key on the world rather than on a character or an item, and its mechanism is [server-lifecycle.md](../platform/server-lifecycle.md#global-moddata)'s.
It lives in one file per save, and on a dedicated server one save is one world, so a table there outlives every connection [#2397/C/C-only].
`OnInitGlobalModData` passes whether the world is new, not whether the table is, and fires after the file has loaded, so a mod added to an existing world finds its own table absent [#2396/C/C-only].
The store's rules are [server-lifecycle.md](../platform/server-lifecycle.md)'s; the one that decides where this mod's table comes from creates it whenever it is missing, with `ModData.getOrCreate`, and never only when the world is new [#2417/C/inference].

`ModData.transmit(name)` on the server sends the whole named table to every connection, with no per-player target, so a table keyed by username and transmitted is every player's values on every client [#2398/C/C-only].
A per-player mirror of this mod's nutrient store cannot ride a transmitted global table without reaching every client, and the per-player push a mod controls is the bus's server send ([mp-model.md#command-bus](../platform/mp-model.md#command-bus)).
On the receiving side `OnReceiveGlobalModData` hands over a freshly loaded table, or `false` when the packet carries none, and installs nothing itself, so a client copy exists only where the mod's own handler installs it [#2399/C/C-only].
A client's request for a table fires a server event that names no player, so a server handler cannot tell which client asked [#2406/C/C-only].
A key in a player's modData and one in a global table both survived a clean save and reload on a live server [#1294/M/n=1].
With the world autosave off the server wrote the file only on a console save and a clean quit, never on a write or a transmit [#2097/M/n=1], and a value written a game-minute before a hard kill was gone after the restart [#2098/M/n=1].
A world-scoped value is therefore as durable as the last save, and a write between saves is lost to a crash [#2097/M/n=1] [#2098/M/n=1].

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
- No push server Lua can cause reaches a second client's copy of a player: every player-addressed server send goes to that player's own connection [#2603/C/C-only].
- The engine has no trait-change event: a trait write fires nothing and sends nothing, so a trait reaches a client only on a push [#2601/C/C-only].
- No ordinary player's client can push its own experience or traits to the server: the one route is capability-gated [#2612/C/C-only, #2595/C/C-only].
- Every measured reading this page cites was taken on the dedicated-server path with one real client, one fixture, and one character or one item per arm, and none of them speaks for single player.
- No arm was taken with more than one client attached, so nothing here measures what a second client's copy holds; which client each push reaches is a code reading, under [Pushes server Lua can cause](#server-pushes).

Not covered: the transport beneath every packet, the save and load round trip that an item's serialised blob and item modData travel on, the player and global modData scopes beyond one clean reload and one hard kill, the contents of the engine's timed health push, every packet outside the food, nutrition, item-fields, player-modData, player-fields, experience, body-part and global-modData set, and anything a listen server or a second attached client would change.

## Open
<a id="open"></a>

- Whether item modData moves server to client through the item-fields sync — settled by a run in which the writing mod's `server/` file is guarded so only the server's Lua state writes, a pre-sync client read that must miss, then a forced sync and a census of both sides; until then a server-owned per-item value in item modData is an unmeasured direction; -> X14 ([#0885/M/n=1/open, #1040/M/one-side/open, #1280/C/open], [open-questions.md#x14](open-questions.md#x14)).
- Whether the per-body net-id reallocation of an item whose script body several mods append ever puts a stale id on the wire — settled by reading the item id on both sides after a multi-bodied redefinition, the single-bodied item being the control; until then the id-keyed bus round trip is read for a single-bodied item only; -> X27 ([#1063/C/C-only/open, #1293/C/open], [open-questions.md#x27](open-questions.md#x27)).
- Whether a mod may call the latent client-to-server eat route, a route for the vanilla store that no caller uses — settled by calling the game client's eat-food method from a mod and reading both sides; no `X` id ([#0145/C/snapshot/open], [mp-model.md#open](../platform/mp-model.md#open)).
- What the server validates on an incoming nutrition write — settled by a probe that separates rejection from overwrite; each probe in the library shows the next push overwriting a client write, which is the ownership this page reads rather than a validation; no `X` id ([#0191/M/n=1/open], [mp-model.md#open](../platform/mp-model.md#open)).
- Whether a relog or a save round trip repairs a client's copy of the uncarried item fields — settled by a relog read of a cooked item on both sides; no `X` id ([#1434/C/inference/open], [wire-packets.md#open](../facts/wire-packets.md#open)).
- The wall that a mod cannot trust a live item field's client copy to tick is unverified: its reading rests on a restricted artifact key and one item in one window, and the multiplayer page's open list states the restriction ([#1148/M/n=1/unverified], [mp-model.md#open](../platform/mp-model.md#open)).
- Decision: which route each quantity this mod owns travels on — forced by the three routes failing three different ways: the transmit replaces a whole table on another mod's call, a script value is fixed per type at load and checksummed at the join, and the bus stores nothing [#1151/M/n=2, #1182/C/C-only, #1153/C/C-only].
- Decision: where the authoritative copy of the mod's per-player store lives — a server-side table or global modData mirrored down over the bus, or player modData kept complete on the client before any transmit — forced by one client transmit making the server's copy exactly the client's [#1042/M/n=2, #1088/M/n=1].
- Decision: whether any value the client displays is derived on the client or always sent from the server — forced by the band traits reaching the client only on server pushes, the experience push measured landing within about half a second, and by the cooked-thirst halving [#2595/C/C-only] [#2759/M/n=3] [#1038/M/n=2].
- Decision: whether any of this mod's state lives in global modData, and whether such a table is ever transmitted — forced by a server-side transmit sending the whole named table to every connection with no per-player target [#2398/C/C-only].
- Decision: whether a per-item mod value is fixed per type in the script or carried per instance — forced by a script value being identical on both sides for free while the item-modData route is measured in one direction only [#1124/M/n=1, #1241/M/one-side].
- Decision: how far the design leans on modData surviving a restart — settled by run `x131p-20261004-192310`: both scopes survived a clean quit and reload, a quit with no console save carried them, and a hard kill lost a minute-old global write along with the world's progress since the last save [#1294/M/n=1, #2756/M/n=1, #2098/M/n=1, #2758/M/n=1].
- Decision: whether item round trips are keyed on the item id before the net-id run lands — forced by the per-body reallocation being unread for an item several mods append to [#1063/C/C-only/open].

## See also

- [`../platform/mp-model.md`](../platform/mp-model.md) — the ownership rows, the routes, the packets, the cached packet object, the wipe and the command bus that every reading here cites.
- [`../platform/server-lifecycle.md`](../platform/server-lifecycle.md) — global modData, its file, its events and the store rules this page links rather than restates.
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
