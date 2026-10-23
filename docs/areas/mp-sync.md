# MP sync — the routes this mod's state travels
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: which side this mod owns each quantity on, the three routes its own state can travel between a dedicated server and its clients, how each route fails on a live server, the pushes server Lua can cause and which client each reaches, global modData as the world's store, and what no route offers; the packet mechanisms are `platform/mp-model.md` and the field contracts `facts/wire-packets.md`

## Rules
<a id="rules"></a>

- Never push an item stat field from a client: the Lua item-stats send is the server's own call, so on a client it does nothing at all, and the game's one client-side item-stats sender is Java's own, called only by the recipe manager — the one client-to-server item route a mod has is the item-fields sync, a different packet carrying modData and condition [#3504/C/C-only, #3503/C/C-only].
- Run anything that changes what eating delivers where `Eat` runs, on the server, and carry its state by server mutation over the command bus, a parallel player-modData store transmitted on change, or client-only semantics: a multiplayer client never reaches `Eat`, so nothing it computes lands in the vanilla store the eat writes [#0128/C/inference, #0109].
- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or push the trait list after you write it as [the trait-push rule](../areas/mp-sync.md#rules) says: the band traits are not in the player-stats packet; they reach the affected player's client on the player-fields packet's trait block and on the timed experience packet, each as fresh as its last push, and no player-addressed push refreshes another client's copy [#2727/C/inference] [#2595/C/C-only] [#2606/C/C-only] [#2603/C/C-only] [#2612/C/C-only].
- Keep every durable mod value in character, item or global modData, or in a server-local file the server's own Lua writes: live Java fields are unsynced cache, and only modData saves and syncs on engine paths, while such a file is saved by the mod's own writes and synced by none [#1064/C/snapshot].
- Route every mod mutation through the command bus, from `sendClientCommand` to the server's `OnClientCommand` to validation to the mutation and back on `sendServerCommand`: the server validates and the client may at most predict [#1065/C/snapshot].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Poll the server over the bus for a live item field rather than reading the client's copy: whether that copy advances is answered per arm and never once, and the three sessions that read one read it in three different arms of the same gate [#1423/M/n=1, #1111].
- Derive a client-side value from packet-carried inputs only with its dependency list written down and each input checked against the packet's field list: a derived value is desync-free only while every input is carried faithfully, a cooked food's thirst change and a zero-valued conditionally-written item field are not, and the weight-band traits arrive only on the experience and trait-block pushes, as of the last push [#1508, #2731/C/inference] [#0567] [#2595/C/C-only] [#1146/M/n=1] [#1147/M/n=1].
- Overwrite every client-side prediction of a mod-owned value with the server's next answer: a client write to a vanilla store is erased by the next snapshot, but a write to a field no packet carries is never erased and drifts from the server's value instead [#0129/M/n=1, #2053/C/inference].
- Address an item in a bus round trip by its id and never by its display name: the id names the same instance on both sides of a single-bodied item, while a dedicated server resolves no mod item's display name and reads a vanilla item's name in vanilla's strings, not the mod's [#1145/M/n=1, #3208/C/inference].
- Give the mod's command-bus module a name no other mod on the server uses: the bus is one namespace shared with every other mod's command sites on that server [#1153/C/C-only, #2055/C/inference].
- Guard every `media/lua/server/` file with a runtime `isServer()` test rather than trusting the folder: a mod's `server/` files execute in the multiplayer client's Lua state too, so "only my server file writes this" is false until the guard is there, and the side test is itself nil-checked because the global may be absent [#0855/M/n=1, #1075/M/n=1].
- Push the trait block with `sendSyncPlayerFields(player, 2)` after any server-side trait write, and expect only the affected player's own client to receive it: a trait write fires no event and sends no packet, the once-a-second experience push also refreshes that client's trait list, measured carrying a server trait write within about half a second with no push at all, so the mod's own push buys freshness within that second rather than being the only route, and every player-addressed server send reaches that player's connection alone [#2693/C/inference] [#2759/M/n=3] [#2601/C/C-only] [#2595/C/C-only] [#2608/C/C-only] [#2603/C/C-only] [#3291/M/n=1].
- Re-read a client's copy of a server-written value only after the push that carries it has landed: the engine refreshes the stats, the experience object, the body-part health, and the injuries and damage on timed pushes of their own, the experience object on the stats snapshot's cadence, the body-part health on a faster one and injuries and damage on a slower one, while `syncPlayerStats`, `syncBodyPart` and `sendSyncPlayerFields` push now to that player's own client, a value no timed push carries arrives only on such a call, and a call is no proof of delivery, so a read taken before the carrying push sees the previous value [#2743/C/inference] [#2608/C/C-only] [#2609/C/C-only] [#2405/C/C-only] [#2607/C/C-only] [#2602/C/C-only] [#2603/C/C-only].
- Send a mod-owned value to the client over the mod's own command bus, never through a framework that has no transport: a client-side library such as `MoodleFramework` sends, receives and transmits nothing and keeps its values in a per-client table, so a server-authoritative value reaches it only when the mod's own `sendServerCommand` delivers it to a client handler that hands it over [#2695/C/inference] [#2540/C/inference] [#2537/C/C-only] [#2538/C/C-only] [#1153/C/C-only].
- Address a mod's player-addressed server send to the player whose client must show it, and expect the engine's own pushes to reach that player's client alone: the mirror and the effects push the mod sent to one player were received by that player's client and not by the other attached client, and a trait-block push to one player reached that player's list while the other client's own list and view did not move, so a value another client must show needs a send addressed to that client [#3300/C/inference] [#3288/M/n=1] [#3289/M/n=1] [#3291/M/n=1] [#2603/C/C-only].
- Keep the mod's world-scoped per-player table on the server and never transmit it: a server-side table made with `getOrCreate` and not transmitted existed on the server alone, `ModData.exists` answering false on both attached clients, so what a client holds of a player's values is what the mod's own send gave it [#3301/C/inference] [#3290/M/n=1] [#2416/C/inference].

## How it works

Every quantity this mod touches gets three answers: which side computes it, which route carries it, and what the other side holds between arrivals.
The mechanisms are [`../platform/mp-model.md`](../platform/mp-model.md) and the packet payloads [`../facts/wire-packets.md`](../facts/wire-packets.md); this page gives this mod's reading of them.
Every measured row here was read on the dedicated-server path, some with one real client and some, the x193 readings among them [#3288/M/n=1, #3298/M/n=1], with a debug client and a release client attached; single player is never claimed.

<a id="authority"></a>
### Which side this mod owns each quantity on

The eat event fires on both sides while the client applies no numbers, so a handler that writes tests its side first [#1131/M/n=1], and a mod runs its intake math where the eat completes, on the server [#1128/M/n=1].
Every nutrient this mod adds is therefore computed on the server, whatever store keeps it and whatever route shows it.
The vanilla stores' single server owner, the drain the client skips and what a client copy is are [mp-model.md#ownership](../platform/mp-model.md#ownership) and [mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is).

| quantity | owner | what the other side holds | tags |
|---|---|---|---|
| the intake: an eat and a cancelled eat | server | a notification that applies no numbers | [#0110, #0111, #0116] |
| the vanilla nutrition store and the player stats | server | a mirror the next player-stats snapshot overwrites | [#0125/M/one-fixture, #0568/M/n=2] |
| weight | server | the three direction flags, computed on each side, and never a weight of its own | [#1238/M/n=1, #0900/M/n=1] |
| the weight-band traits | server | the trait list as of the last experience push or trait-block push, the experience push measured landing within about half a second of a server write | [#2595/C/C-only] [#2759/M/n=3] |
| item state in the item packet | server, except an item outside the player's inventory that the recipe manager uses: the client's own Java sends that item's values and the server applies them unchecked | the last push, stale in any zero-valued conditional field | [#3503/C/C-only, #0343] |
| item aging | server | nothing: the fields never cross | [#1242/M/n=1] |
| a per-item mod value in the item script | neither: both sides load it | the same value | [#1124/M/n=1] |
| a per-item mod value in item modData | the last writer | a wholesale copy, measured client to server only | [#1241/M/one-side] |
| the mod's per-player store | server, by this mod's design | a mirror on the route the options choose | [#1122/C/C-only, #0913/M/n=1] |
| moodles | neither: each side recomputes | its own recompute from its own mirror | [#1245/C/C-only] |
| mod item display names | client | nothing on a dedicated server | [#0848/M/n=1, #3206/M/n=2] |

The client may show which way the weight is moving and never a weight of its own [#1139/M/n=1, #1138/M/n=1].
A server-side table is set up on the global-mod-data init or server-started hook, and a new character's row on `OnNewGame` ([#2387/C/C-only], [server-lifecycle.md#creation](../platform/server-lifecycle.md#creation)).
The mod's server cache is an in-memory table of the records seen in the server's uptime, persisted per player to two alternating JSON slot files under the server's Lua cache folder through `getFileWriter`, so no per-player record is kept under a global modData name. [#3647/C/snapshot]
The client's copy is a display mirror: refreshed on the mod's own command it is late by one round trip, and any transmit from that client writes its copy back over the server's [#1042/M/n=2].
The mod's server answers the first of two back-to-back mirror requests from one client and denies the second: two `requestMirror` calls from the release client `bob` moved the server's answered count from 0 to 1 and its denied count from 0 to 1, and bob's received count from 3 to 4. [#3775/M/n=1]
A `server/` file also runs in the client's Lua state, so a server-side write needs a runtime side test [#1174/M/n=1].

<a id="failure-modes"></a>
### How each route fails on a live server

The transmit and the engine's own pushes fail silently, so a failure is found only by a paired read of both sides ([#1495], [harness.md#probes](../platform/harness.md#probes)).
The three routes fail at three different moments: the transmit whenever any mod on the client calls it, script data at the join, and the bus wherever the mod's own handler does.

The transmit moves too much: it serialises the whole player-modData table and the receiver wipes its copy first, so an empty sender wipes the receiver outright [#1091] ([mp-model.md#wipe-and-replace](../platform/mp-model.md#wipe-and-replace)).
The mod that loses a key is not the one that transmitted: a client-only interface mod fires the call from its input handlers ([#1482], [simplestatus.md#mp](../facts/other-mods/simplestatus.md#mp)), so a server-only key in player modData lives only with a workaround [#1151/M/n=2].
Strings, numbers, booleans and nested tables cross; functions and Java objects are dropped with no error ([#1495], [wire-packets.md#moddata-packet](../facts/wire-packets.md#moddata-packet)).

Script data fails at the join: every loaded script file feeds one checksum compared at the join, carriage returns dropped, so a mismatch disconnects the client [#1182/C/C-only].
A script fixes a type's default at load, so a cook, a spoil or a per-player change rides another route, and a Lua write to a field the item packet omits stays on the server [#1074/M/n=1].

The command bus fails only where the mod's own code does: it has no wipe and no packet dependency [#1153/C/C-only].
Its costs are structural: both ends are written, a round trip stores nothing, and the module name shares one namespace ([mp-model.md#command-bus](../platform/mp-model.md#command-bus)).
A client that joins after the mod's last answer holds no copy until the mod sends one, so a bus mirror needs a send on arrival as well as on change.
An unguarded raise in a handler half-applies the mutation while the handlers behind it keep running ([#0948/M/n=1], [#3506/C/C-only], [lua-platform.md#raises](../platform/lua-platform.md#raises)).
A client-side prediction beside a bus value is corrected by nothing when its field is outside the player packet [#0129/M/n=1].
An item round trip keyed on the id holds for a single-bodied item [#1145/M/n=1]; a multi-bodied one is under [Open](#open) [#1063/C/C-only/open].

Client-only semantics rides the routes above and fails the moment one input is not carried, so the dependency list is the technique [#1508] ([simplestatus.md#techniques](../facts/other-mods/simplestatus.md#techniques)).
The engine's own pushes underneath — the staircase, the zero-valued item field the cached packet supplies [#0343], the cooked-thirst halving [#1038/M/n=2] and the cook desyncs — are [wire-packets.md#staircase](../facts/wire-packets.md#staircase), [mp-model.md#cached-packet](../platform/mp-model.md#cached-packet), [wire-packets.md#cooked-thirst](../facts/wire-packets.md#cooked-thirst) and [wire-packets.md#desyncs](../facts/wire-packets.md#desyncs); item modData's own differences are [mp-model.md#item-moddata](../platform/mp-model.md#item-moddata).
The item-fields sync is measured client to server only, so a server-owned per-item value in item modData is under [Open](#open) [#1241/M/one-side].

<a id="server-pushes"></a>
### Pushes server Lua can cause

`sendSyncPlayerFields`, `syncPlayerStats` and `syncBodyPart` push a player's state when called, each only on a server, and a call is no proof of delivery [#2602/C/C-only, #2607/C/C-only]; the masks are [wire-packets.md](../facts/wire-packets.md#player-fields-packet)'s and the gates [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)'s.
Every player-addressed server send, these three, the timed pushes and the eat packet included, reaches that player's own connection only [#2603/C/C-only].
On a live server with two clients attached, this mod's own mirror reached each player's own client carrying that player's username [#3288/M/n=1], a clinical state forced on one player's record reached that player's client on the effects push while the other client received nothing [#3289/M/n=1], and a server trait add with its trait-block push reached the owner's list while the other client's own list and view did not move [#3291/M/n=1].
What the second client holds of the other player's character was not read [#3292/C/C-only].
A `SyncXp` from a connection with the stats-panel capability is relayed to every other client [#2612/C/C-only], and a transmitted global table reaches every connection.

A trait write fires no event and sends no packet [#2601/C/C-only]; the experience push refreshes the owning client's whole trait list on the stats snapshot's cadence ([#2608/C/C-only], [#2595/C/C-only]), measured landing a server-written trait within about half a second in three trials with no push, a removal the same way [#2759/M/n=3].
The mod writes the five band traits from its own axes with the trait push, and a thin pick's trait read on the server and the client from creation [#3873/M/n=1].
A server's per-minute `Stats.set` of HUNGER, THIRST and FATIGUE reaches the owning client: measured live, five client-first pairs on each of two players read the client's values equal to the server's for all three stats. [#3370/M/n=1]
The weight-trend flags arrive with the weight on the stats packet, but with `Nutrition` on they are vanilla's `updateWeight` values, so a server mod's flag write does not reach the client as written [#2884/M/n=1][#2644/C/C-only]; with it off, they did not reach the client at all ([#2911/M/n=1], [body-and-weight.md#weight-bands](../facts/body-and-weight.md#weight-bands)).
The mod's first-sight mirror carries the body [#2910/M/n=1].
An ordinary player's client cannot push its own experience or traits, so every authoritative write this mod makes is made on the server and announced by a push or the mod's own bus [#2612/C/C-only].

<a id="global-moddata"></a>
### Global modData as a per-world store

The store's mechanism and events are [server-lifecycle.md#global-moddata](../platform/server-lifecycle.md#global-moddata): one file per world [#2397/C/C-only], a new-game flag that is not "table is new" [#2396/C/C-only], `ModData.transmit` to every connection [#2398/C/C-only], and a request event that names no player [#2406/C/C-only].
A per-player mirror therefore never rides a transmitted global table; with two clients attached, this mod's untransmitted table existed on the server alone: neither client held a table of that name [#3290/M/n=1].
On the release, `ModData.exists` of the earlier builds' table name `NutritionRevamp.players` read false on the server and on the release client `bob`, and bob's one request of that name drew one `OnReceiveGlobalModData` firing while the server logged `GlobalModData -> received request for non-existing table, table: NutritionRevamp.players`; the one firing was the reply to that request. [#3773/M/n=1] [#3647/C/snapshot]
A key in a player's modData and one in a global table both survived a clean save and reload [#1294/M/n=1]; with autosave off the file is written only on a console save and a clean quit [#2097/M/n=1], and a value written a game-minute before a hard kill was gone after the restart [#2098/M/n=1].

The mod's own store is slot files, not global modData [#3647/C/snapshot].
The load runs in place on the stored record, keeping the inputs and dropping every other field, once per record table in an uptime, a record held in memory being only resumed at a return [#3963/C/snapshot].
The mod's slot files carry a number exactly across a server restart: eight values the store's probe wrote under the username `tkprobeéü中文` before a clean stop, among them `0.1+0.2`, `5e-324`, `-1e-300`, `2^53+2` and `99999999999999.5`, each compared equal with `==` after the restart, the username too, and the probe's clear then emptied both of its slot files and dropped its index entry, the index going from 3 keys to 2. [#3783/M/n=1]
An eat's landing survived a clean server stop that came before its slot's next regular write: admin's `TKX.Mixed400` landed and his slot was written again before the stop, its generation 4 at the read that found the landing and 5 at the read before the stop, the stop came 18645.5 ms after his last regular write, and after the restart the newest slot line held the eat, its stomach buffer at 799.13 kcal against 420.38 before the eat and the type's monotony count at 1 against 0. [#3785/M/n=1]
A mod's file store can survive a host killed mid-write, and in the worked example, each player's record is a pair of alternating slot files of which the writer never opens the one holding the newest complete copy, because `getFileWriter` empties a file when it is obtained, a file that does not decode to an object carrying its completion flag and generation loses to the other of its pair, and the real-time last-seen index is a pair of files for the same reason. [#3800/C/inference] [#3559/C/C-only]
A mod's file store outlives the world it was written for, and in the worked example, the store's folder is keyed by the server name, so a world wiped under the same name finds the old files and every returning player's record, its reset count included, carries over until an operator deletes the folder by hand, and no record is ever pruned, so neither a long absence nor long server down time resets a character. [#3965/C/inference]
A mod's file store and the world it serves can roll back apart, and in the worked example, a player's slot is written at most once a real minute and at once after an eat, a drink or a respawn's reset, so a clean stop loses at most a minute of digestion drift, while a hard kill takes the world back to its last save and leaves the slot files at their last write. [#3802/C/inference] [#2098/M/n=1]
A mod can keep a validated copy of a player's record on the character itself, and in the worked example, each save of this mod's store slot also writes the slot's own text into the character's modData, cut into parts of at most 8000 characters with a sum over the text and the world age of the save, never per minute and never sent to the client, and the store reads it only to restore a record, rejecting a copy that is absent, whose parts or text do not decode to this username's finished document, or whose sum does not match. [#3967/C/inference]
A mod whose file store and world can roll back apart can restore the record that matches the character, and in the worked example, at the read of a record not in memory this mod's store loads the character's copy when the store file is missing or unreadable, or when the store record's latest stamp is past the world clock, a hard kill having rolled the world back under it, and keeps the store otherwise; a restore sets the next write's generation past both copies, marks the slot to be rewritten and is resumed like any load, a record past the world moving back onto the clock, and a store record past the world with no valid copy is kept, moved back the same way and logged. [#3968/C/inference]
In the worked example played live, after a world save, an eat and a kill of the server, the restarted world at 4.5425825119018555 and the record's first sight at 5.468774795532227 sat behind the store file's latest stamp 12.556371688842773, and the load rule restored the record from the copy on the character, 1 restore and 0 kept ahead, resumed forward by 2.3842554092407227 game hours, the restored record holding no eat of the banana with both bananas back in the inventory. [#3985/M/n=1]
In that session the player store's blob of the character read 10145 bytes holding the copy's key after the kill, against 4086 bytes holding none in the fixture's. [#3986/M/n=1]

## Options

<a id="sync-options"></a>
### The three routes this mod's own state can travel

Anything that alters what eating delivers to a multiplayer player has to run where `Eat` runs, on the server, so the three viable shapes are mutating on the server over the command bus, keeping a parallel store in player modData and calling `transmitModData()` on change, or accepting client-only semantics [#0128/C/inference].
The engine's own packets are not a route: a mod can cause one to fire and cannot change what it carries ([mp-model.md#packets](../platform/mp-model.md#packets)).

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| `transmitModData` on player modData | no protocol to write and a store the engine saves, at the price of moving the whole table in both directions on a call any mod on that client can make; only strings, numbers, booleans and tables cross | no part of the table can be sent alone, and server-authoritative state survives there only with a workaround, because the transmit that replaces it is another mod's call | [#1123/M/n=2, #1151/M/n=2, #1152/M/n=2, #1495] |
| script data loaded per side | nothing at run time, since both sides load the same file; the value is a type's default fixed at load, so no per-instance or per-player change can ride it, and every shipped script file must match byte for byte on both sides apart from its line endings | a script mismatch disconnects the joining client rather than degrading; a per-instance value falls back to item modData or the bus | [#1124/M/n=1, #1145/M/n=1, #1182/C/C-only] |
| the command bus | both ends written by the mod, a store beside it for anything durable, and one namespace shared with every other mod's command sites; the one route whose payload, timing and direction the mod chooses | none of its own; it inherits the two push walls — no player stat and no item stat field can be pushed from a client — so every authoritative write it carries is made on the server | [#1153/C/C-only, #0932, #1149/M/n=1, #1150/C/C-only] |

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
- No push server Lua can cause reaches a second client's copy of a player: every player-addressed server send goes to that player's own connection [#2603/C/C-only], and the mod's own mirror and effects push were received by their owner's client and not by the other attached client [#3288/M/n=1, #3289/M/n=1], the trait push reaching the owner's list while the other client's own list and view did not move [#3291/M/n=1].
- The engine has no trait-change event: a trait write fires nothing and sends nothing, so a trait reaches a client only on a push [#2601/C/C-only].
- No ordinary player's client can push its own experience or traits to the server: the one route is capability-gated [#2612/C/C-only, #2595/C/C-only].
- Every measured reading this page cites was taken on the dedicated-server path with one real client, one fixture, and one character or one item per arm, and none of them speaks for single player; the exceptions are the two-client readings, taken once with a debug client and a release client attached [#3288/M/n=1, #3298/M/n=1].
- The two-client arms read each client's own mirror, the effects push, the global table and the trait push on the owning client; what a second client's copy of another player holds was not read, because the harness reads only its own player on a client [#3292/C/C-only], so which client every other engine push reaches stays a code reading, under [Pushes server Lua can cause](#server-pushes).

Not covered: the transport beneath every packet, the save and load round trip that an item's serialised blob and item modData travel on, the player and global modData scopes beyond one clean reload and one hard kill each, the mod's own table included [#3275/M/n=1, #3280/M/n=1], the contents of the engine's timed health push, every packet outside the food, nutrition, item-fields, player-modData, player-fields, experience, body-part and global-modData set, the engine pushes no two-client arm exercised, what a second attached client's copy of another player holds, and anything a listen server would change.

## Open
<a id="open"></a>

- Whether item modData moves server to client through the item-fields sync — settled by a run in which the writing mod's `server/` file is guarded so only the server's Lua state writes, a pre-sync client read that must miss, then a forced sync and a census of both sides; until then a server-owned per-item value in item modData is an unmeasured direction; -> X14 ([#0885/M/n=1/open, #1040/M/one-side/open, #1280/C/open], [open-questions.md#x14](open-questions.md#x14)).
- Whether the per-body net-id reallocation of an item whose script body several mods append ever puts a stale id on the wire — settled by reading the item id on both sides after a multi-bodied redefinition, the single-bodied item being the control; until then the id-keyed bus round trip is read for a single-bodied item only; -> X27 ([#1063/C/C-only/open, #1293/C/open], [open-questions.md#x27](open-questions.md#x27)).
- Whether a mod may call the latent client-to-server eat route, a route for the vanilla store that no caller uses — settled by calling the game client's eat-food method from a mod and reading both sides; no `X` id ([#0145/C/snapshot/open], [mp-model.md#open](../platform/mp-model.md#open)).
- What the server validates on an incoming nutrition write — settled by a probe that separates rejection from overwrite; each probe in the library shows the next push overwriting a client write, which is the ownership this page reads rather than a validation; no `X` id ([#0191/M/n=1/open], [mp-model.md#open](../platform/mp-model.md#open)).
- Whether a relog or a save round trip repairs a client's copy of the uncarried item fields — settled by a relog read of a cooked item on both sides; no `X` id ([#1434/C/inference/open], [wire-packets.md#open](../facts/wire-packets.md#open)).
- The wall that a mod cannot trust a live item field's client copy to tick is unverified: its reading rests on a restricted artifact key and one item in one window, and the multiplayer page's open list states the restriction ([#1148/M/n=1/unverified], [mp-model.md#open](../platform/mp-model.md#open)).
- Whether a second client's copy of another player moves with a push is unmeasured — settled by a harness read of a remote player's object on a client, which the harness's local-player subject cannot make today; no `X` id ([#3292/C/C-only], [harness.md#walls](../platform/harness.md#walls)).
- Decision: which route each quantity this mod owns travels on — forced by the three routes failing three different ways: the transmit replaces a whole table on another mod's call, a script value is fixed per type at load and checksummed at the join, and the bus stores nothing [#1151/M/n=2, #1182/C/C-only, #1153/C/C-only].
- Decision: whether any value the client displays is derived on the client or always sent from the server — forced by the band traits reaching the client only on server pushes, the experience push measured landing within about half a second, and by the cooked-thirst halving [#2595/C/C-only] [#2759/M/n=3] [#1038/M/n=2].
- Decision: whether a per-item mod value is fixed per type in the script or carried per instance — forced by a script value being identical on both sides for free while the item-modData route is measured in one direction only [#1124/M/n=1, #1241/M/one-side].
- Decision: whether item round trips are keyed on the item id before the net-id run lands — forced by the per-body reallocation being unread for an item several mods append to [#1063/C/C-only/open].

## See also

- [`../platform/mp-model.md`](../platform/mp-model.md) — ownership, routes, packets, the cached packet, the wipe and the command bus.
- [`../platform/server-lifecycle.md`](../platform/server-lifecycle.md) — global modData, its file, its events and its store rules.
- [`../facts/wire-packets.md`](../facts/wire-packets.md) — each packet's fields, the desyncs, the staircase and the cooked-thirst halving.
- [`../platform/lessons.md`](../platform/lessons.md) — the sync rules and their authority filters.
- [`../platform/lua-platform.md`](../platform/lua-platform.md) — which side each hook fires on, and what a raise in a bus handler aborts.
- [`../platform/harness.md`](../platform/harness.md) — the paired client-first read.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) and [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) — a client mod whose transmit wipes neighbours' keys, and one that never transmits and is carried anyway.
- [`new-nutrients.md`](new-nutrients.md), [`item-pass.md`](item-pass.md), [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md), [`ui-and-moodles.md`](ui-and-moodles.md), [`testing-your-mod.md`](testing-your-mod.md) — the store choice, the script route, the intake seats, the client reader and the cross-side grading.
- [`open-questions.md`](open-questions.md), [`../reference/wall-map.md`](../reference/wall-map.md), [`../reference/experiments.md`](../reference/experiments.md) — the experiments, the verdict rows and their specs.
