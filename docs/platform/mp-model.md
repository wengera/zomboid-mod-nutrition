# The multiplayer model
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: which side owns each quantity a nutrition mod touches, the routes state can travel between them, when each packet fires, what the receiver holds between sends, and what a client's copy of a server-owned object is and is not; the packets' field lists and the measured per-field desyncs are `facts/wire-packets.md`.

## Rules

- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Run the mod's intake math where the eat completes: a multiplayer client never reaches the eat action's completion step, so nothing a mod hangs off the client side of that path ever runs [#0109, #0110].
- Route every mod-owned mutation through the command bus: a client send, a server-side handler that validates and mutates, and a server send back is the one route a mod controls end to end [#0932].
- Rewrite the hunger and thirst constants on the side that runs the updater, the server: the constants come from the Lua globals table and the updater that reads them is server-gated [#0569/C/C-only].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or feed it an explicitly transmitted value: the band traits are not in the player-stats packet and no other packet was traced carrying the trait list [#1104/C/inference].
- Never push an item stat field from a client: the item-stats send is the server's own call with no client-side counterpart, so on a client it does nothing at all — the one client-to-server item route is the item-fields sync, a different packet carrying modData and condition [#0330/C/C-only, #1240/C/C-only].
- Spawn every item a probe or a mod will consume on the server: an eat of a client-spawned food ends in a sync error on the server, because the closing item-field sync runs against an instance the server never heard of [#0124/M/n=1].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Poll the server over the bus for a live item field rather than reading the client's copy: whether that copy advances is answered per arm and never once, and the three sessions that read one read it in three different arms of the same gate [#1423/M/n=1, #1111].
- Treat a client's freshness display as arbitrarily stale: it is whatever the last full serialisation of the item said, and nothing re-sends the age until the item is serialised whole again [#0357/C/inference].
- Take a client-side moodle read at least one push after a server-side stat write: the moodle recompute has no side guard, so the client recomputes from a mirror that can lag by a push [#0570/C/C-only].
- Read a server-side modData key count beside its wall offset, never on its own: the four vanilla fitness and strength keys are written server-side lazily, so an early census and a late one disagree without anything having changed [#1338/M/n=2].
- Test a modData census for emptiness with the key count rather than the key list: even an item whose mod writes no keys at all reads a custom-name key on the side that deserialised it [#1415/M/n=1].
- Assume both copies of a mod's `server/` file run: a value written there lands in the client's own player-modData table as well, so a census that expects one writer reads two [#0910/M/n=1].

## How it works

A multiplayer session on this build is one dedicated server process and one or more client processes, each running its own Lua state over its own copy of the world.
Nothing a mod writes crosses between them by itself.
Every quantity below has exactly one side that computes it, and the other side holds a copy that arrives on a route this page names, at a cadence this page names, carrying the fields `facts/wire-packets.md` names.
The four questions that decide any design are therefore always the same: who owns the value, which route can move it, when that route fires, and what the receiving side is holding in between.

<a id="ownership"></a>
### Who owns what

The server owns the whole intake path and every store it writes into.
The client's job on that path is to queue an action and to draw the numbers it is sent.

The eat completes on the server: the client's timed-action start creates a net timed action and sends its packet, and the server's action manager drives the net action's perform step into the eat action's completion and on into the character's eat call [#0110].
A multiplayer client never runs that completion step and so never calls the character's eat at all, because the Lua completion is skipped when the game-client handle is set and the eat line inside the action's perform step is commented out [#0109].
In single player the same action calls its server-stop step itself, because the guard there tests for neither client nor server [#0103].
A cancelled eat also resolves on the server: the net action's stop call reaches the eat action's server-stop step, whose fraction comes from the net action's own progress, and that net action is injected by the packet parse and exists only server-side [#0111].
That server-stop step applies nothing at all — no stats, no nutrition, no food-value multiplication and no consumption — when the item is `Base.Cigarettes` or when the magnitude of the hunger change times 100 is 1 or less [#0112].

The server owns the nutrition object and a multiplayer client holds a mirror of it [#0125/M/one-fixture].
Nutrition is server-authoritative in both directions: a client `setCalories(3000)` never reached the server and was back to the server's value inside 3 s, while a server-side write reached the client inside 3 s, the server pushing the whole object at eat time and once a second [#1094/M/n=1].
The same reading taken on the store as a whole is that the server owns the five `Nutrition` floats, a client `setCalories` being gone inside about 1 s and a server write reaching the client inside 3 s [#1237/M/n=1].
The calorie store and the three macro stores are pushed server to client in the player-stats packet at about 1 Hz and in the eat packet at eat time: a client-side write to them is erased inside about a second and a server-side write reaches the client inside 3 s [#0898/M/n=1].
A multiplayer client does not simulate the drain at all: the nutrition update skips the macro decay and the calorie update when the game-client handle is set [#0117].
The macro drain and the calorie update are server-only for that same reason, a not-a-game-client check inside the nutrition update gating both [#0557].

Hunger and thirst are owned the same way.
The hunger and thirst stats are server-owned in the same way as nutrition: a client `stats.set hunger 0.9` read back 0.9 while the server stayed at 0.0005 and the client fell back to 0.00098 within 3 s, and a server-side 0.4 reached the client as 0.400293 [#0123/M/n=1].
A client write to either stat never reaches the server: a client write to 0.9 was gone within 3 s while a server-side write to 0.4 reached the client [#1095/M/n=1].
The server owns the player stats outright: a client write of hunger 0.9 against a server pinned to 0.3 read back 0.9 at t = 0.51 s and 0.300419 at t = 1.42 s, the once-a-second unconditional full snapshot overwriting it [#1236/M/n=1].
Both stats tick on the server only in multiplayer, and in single player only for the local player instance, the wake-state updater and the thirst updater carrying the identical guard and the thirst one adding a ghost-mode skip [#0560/M/n=1].
Automatic drinking runs on the server only, additionally needs the character's own auto-drink flag and the game's auto-drink option, and is skipped while asleep, grappling, knocked down, falling, aiming or climbing [#0481/C/C-only].
Endurance ticks on the server only, its updater returning immediately on a game client unless the character is an animal [#0561].
Fatigue is the server's too: it resets that stat unless sleep is both allowed and needed [#0562/C/C-only].

Weight splits in a way that matters to any mod reading it.
The weight computation itself runs on both sides, because there is no side guard at the weight update's entry [#0558].
The write and the band-trait refresh are server-only: the game-client check sits before the weight setter, before the refresh counter's increment and before the trait application, so a client computes a weight and throws it away [#0559/M/n=1].
A client can therefore neither set nor derive body weight: `Nutrition.updateWeight` runs on the client but a `GameClient.client` skip sits before `setWeight` and before `applyTraitFromWeight`, so the client computes a weight delta, discards it and never applies the weight-band traits [#1097/M/n=1].
Anything a mod keys on the Obese, Overweight, Underweight or Emaciated band must be evaluated server-side or fed an explicitly transmitted value, because the band traits are not in the player-stats packet and no other packet was traced carrying the trait list [#1104/C/inference].
Traits are applied server-side and no packet has been traced carrying the character trait list to a client [#1239/C/C-only].

Two quantities have no owner at all.
Moodles are recomputed on both sides as a pure function of the local stats, the moodle update carrying no side guard [#0563].
They are therefore owned by neither side, each recomputing them, and they are absent from the player-stats packet [#1245/C/C-only].

On the item side the server owns the whole lifecycle.
The container hooks that fire when an item is added to or removed from a container are gated on the process being a server too, so the server owns a food item's entire lifecycle [#0327].
The server flag those gates read is written in only two places, the server's own entry point and the game window's main-thread init when the server launch argument is true, so it is true only in a dedicated or host server process [#0328].
The server also runs the cook transition: an item update read the cooked flag already true with the sentinel and the two flags already written, while the hook's four prints are in the server console in one frame 1.71 s earlier and the client console is empty [#1417/M/n=1].

Two quantities cross by a route that is neither of the item packets.
A Cooking perk level set on the server is visible to the very next client read with no wait, the reverse write at the session's end was too, and the client-side call was a no-op both times, the perk travelling by character sync rather than by the item packet [#0353/M/n=1].
The inventory weight a client-side capacity bar draws does cross the wire exactly, both sides reading it identically at every snapshot, including the one-kilogram step two spawned control items caused inside the same window [#1499/M/n=1].

One consequence of ownership reaches into a mod's own constants.
Because the hunger and thirst constants come from the Lua globals table, a mod that rewrites them must do so on the side that runs the updater, which is the server [#0569/C/C-only].

<a id="shapes"></a>
### The shapes mod state can travel in

There are four shapes, and each costs something different.

A **packet field** is free at the point of use and closed at the point of design: the field lists are fixed in the jar, the sender fills them from the item or the character, and a mod cannot add to them — the lists themselves, and what each receiver applies, are [`../facts/wire-packets.md#item-stats-packet`](../facts/wire-packets.md#item-stats-packet) and [`#player-stats-packet`](../facts/wire-packets.md#player-stats-packet).
A **modData table** is the one payload a mod chooses, at the price of moving whole: item modData rides the item-fields sync and player modData rides an explicit transmit, and both wipe the receiver before they write ([`#item-moddata`](#item-moddata), [`#wipe-and-replace`](#wipe-and-replace)).
A **command payload** is the only shape whose contents, timing and direction the mod decides outright, at the price of writing both ends ([`#command-bus`](#command-bus)).
Script data is the fourth and the cheapest where it fits: item scripts load per side and never sync, so a value written in a script is identical on both sides without any route at all, and the routes above are only for what a script cannot hold.

The item's own serialised blob is a fifth shape, but it is not addressable by a mod.
An item's save and load write the age, the last-aged stamp, the two off-age bounds, the freezing time, the last frozen update, the rotten time and the compost time under a bit-flag scheme [#0331/C/C-only].
That blob travels only when the whole item is retransmitted, which is why the aging fields behave as they do under [`#routes-server-to-client`](#routes-server-to-client).

<a id="routes-client-to-server"></a>
### The routes from a client, and what each will not carry

There are two routes out of a client that a mod can use — the command bus and a player-modData transmit — and one latent engine route with no callers.
Everything else a client writes stays on the client.

The eat packet's client-to-server direction exists in the jar and is unused: the game client's eat-food call builds and sends that packet from client to server and has no callers anywhere in the jar or in the game's own Lua [#0104/C/snapshot].
There is no client-to-server item-stats push at all: the send is server-originated and has no client-side counterpart, so a client cannot send an item stat field back to the server — the absence is of an item-stats push and does not cover the item-fields sync, a separate client-to-server route carrying its own item fields [#0330/C/C-only].
A client-side `setCalories(3000)` never reached the server and was gone within 3 s: the server read 887.920 at that instant and the client read the server's 887.331 three seconds later [#0119/M/n=1].
A client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner: the server [#0568/M/n=2].
The tightest bound on that erasure is the hunger arm: a client-side write of 0.9 against a server pinned to 0.3 read back as 0.9 at 0.51 s and as 0.3004 at 1.42 s while the server never left 0.3007, so the revert lands inside 1.5 s [#0572/M/n=1].

<a id="routes-server-to-client"></a>
### The routes from a server, and the cadence of each

The server has three pushes that matter to a nutrition mod: the player-stats snapshot on a fixed timer, the eat packet on an eat, and the item-stats push from inside the item update's cooking block.

The player-stats packet is pushed once a second, unconditionally, from `NetworkPlayerAI.syncStats` under an `UpdateLimit(1000)` [#1207/C/C-only].
A server-side `setCalories(2500)` propagated to the client within 3 s, which read 2499.436 [#0120/M/n=1].
The real eat path lands on the client about 5.5 s after queuing, in one step of 94.741 kcal — 95 less the 0.259 burned that second — against 95 for a direct eat call [#0121/M/n=2].
Measured tightly, a nutrition write reaches the client within an upper bound of 0.766 and 0.765 seconds on two writes, with a still-old client read 0.26 s after the acknowledgement bracketing the 1 Hz push window from below [#1493/M/n=1].

On the item side the pushes are narrower than they look.
Both item-stats sends inside the cooking block are gated on the process being a server [#0329].
The item update carries two server-guarded item-stats pushes inside its cooking block, one before the cook transition and one after it, and a third outside that block at the end of the tainted-water boiling branch where a cooking time past 10 clears the tainted flag [#1395].
The server owns the item-state packet values: that packet is push-only, server to client, and there is no client-to-server item-stats route [#1240/C/C-only].
What no push carries at all is the item's stored blob: its multiplayer carriers are the client's item-list and inventory-get receivers, the server's inventory-update receiver, the world inventory object's load, the equip packet, the trading add-item packet and the identical-item compressor, so the age travels only when the whole item is retransmitted and never when its stats change [#0332/C/C-only].

<a id="packets"></a>
### The packets, and when each fires

Four packets carry food and nutrition state, and a mod's relationship with all four is the same: it can cause one to fire and it can read what arrived, and it can change neither the field list nor the cadence.
The field lists and the measured per-field desyncs are [`../facts/wire-packets.md`](../facts/wire-packets.md); what follows is the mechanism only.

The player stats snapshot is pushed at 1 Hz, from a network player manager update limit of 1000 ms driving the stats sync [#0565/C/C-only].
`ItemStatsPacket` and `SyncItemFieldsPacket` are different packets, and confusing them is the commonest error here: the first declares 7 members and carries the item's stat fields, the second declares 15 members and carries condition and item modData wholesale [#1258/C/C-only].
The stat field list is the item packet's contract on [wire-packets.md](../facts/wire-packets.md#item-stats-packet).
A send is fire-and-forget and leaves no trace a probe can read: the eat call and its packet produce no lines in the server stdout log, the client console or the client debug log, even with the network debug log enabled [#0131/M/n=1].
The one visible failure is a packet arriving about an item the receiver does not have: food spawned client-side makes the server log an item-fields sync error, because the eat call's closing sync runs against an item the server never heard of [#0124/M/n=1].

<a id="cached-packet"></a>
### The cached packet object, and what a stale field reads as

The receiving side does not allocate a packet per arrival, and that is the mechanism behind every stale item read in this library.

The receiver reuses one packet object per type: the client packet dispatcher fetches the instance from the connection's packet cache and allocates a fresh one only when the packet says it is postponed or asks to be instantiated, and both default to false while the item-stats packet overrides neither [#0341].
The item-stats packet has no reset: its whole method list is the constructor, the data setter, the write, the parse, the two process methods and the apply step, and nothing zeroes it between uses [#0340/C/C-only].
That is the same reading taken from the wall map's side: the packet reuses one cached object per type with no reset, a fresh instance being made only when the postponed or instantiate test says so, neither of which it overrides [#1202/C/C-only].
The sender is clean: the data setter refreshes every field off the item and clears its two lists, so a stale value can only live on the receiving object [#0342].
Any conditionally-written packet field that is zero on the sender therefore arrives carrying whatever the last packet that did set it left behind, and the receiver writes that value onto the item [#0343].

Which fields are written conditionally, and which one has been seen to carry over, is [`../facts/wire-packets.md#item-stats-packet`](../facts/wire-packets.md#item-stats-packet).

<a id="item-moddata"></a>
### Item modData: whole-table, and measured in one direction

An item's mod-data accessor returns a Kahlua table, so item mod data is Lua-shaped on both sides, and it is in the sync set with both sides holding a copy [#0909/C/C-only].
Item modData and condition move wholesale in either direction, the item-fields sync packet's modData step wiping the receiver and copying the sender's keys [#1241/M/one-side].
That reading is one-sided: the item-field sync call is measured in the client-to-server direction only, because a mod wrote a key into an item's mod data and called it, both sides read the key three seconds after the spawn, and the write came from the client VM — the item-write counter read one on the client and zero on the server [#0910/M/n=1].
What the measurement does establish is that the route works: a `Base.Cheese` item-modData census read the mod's own key beyond vanilla on the client and on the server, so a per-item custom nutrient is not closed to a mod [#1039/M/one-side].

Two census facts travel with the route, and both bite a probe that does not know them.
An item modData census is not empty even for a mod that writes none: the mod item read 1 key on the server and 2 on the client, the extra being a custom-name key that a vanilla control item also carried on the client only, so the baseline is to exclude the custom-name key always and the tooltip key for any item whose script declares one [#1415/M/n=1].
And an item's modData is not the same table on the two sides: on one apple the server read an empty table while the client read a custom-name key, on the same instance [#1639/M/n=1].

<a id="player-moddata"></a>
### Player modData: the durable store, and what is in it when

A character's mod-data accessor returns a Kahlua table that both sides hold a copy of and that does not cross until someone transmits it: it is the durable per-character store and the only one a mod can add keys to [#0913/M/n=1].
Player modData does not cross sides until `transmitModData` is called, which is why `simpleStatus`'s config key reaches the server and `AutoCook`'s settings never leave the client that set them [#1637].

What the two copies hold differs by more than a mod's own keys, and a census is only a reading beside its wall offset.
The server's copy of a player's modData is empty at join and gains the four vanilla fitness and strength keys 22 to 33 s after session ready, so early in a session the pair is 0 keys on the server against 5 on the client [#1432/M/n=1].
Those four keys are written lazily — a key count of 0 at 3.073 s after session ready and 4 at 42.102 s — so a server key count is only a reading beside its wall offset [#1338/M/n=2].
The census is per scope for the same reason: the exclusion set that makes an item-scope census legible is not the one that makes a player-scope census legible, and neither transfers.

The hazard the store carries is not about the mod that owns the key.
One corpus mod holds 9 `getModData()` sites and no `transmitModData` call at all, and its whole nested table still crossed to the server the first time something else on that client transmitted, the server's census becoming exactly the client's, hotbar included [#1088/M/n=1].

<a id="wipe-and-replace"></a>
### `transmitModData`: whole-table, both directions

The transmit is not a merge and it is not a diff.
The call serialises the whole player modData table and the receiver wipes before it writes, so an empty sender's table wipes the receiver outright, and the call returns silently if the player's square is null [#1091].
The routing itself is symmetric: the transmit returns silently when the object's square is null, and otherwise sends the object mod-data packet on a client and calls the server's own object mod-data send on a server, so both directions are real and neither is a merge [#0916/C/C-only].

Client to server is the better-measured direction.
A client-to-server transmit is a whole-table wipe and replace: a key planted on the server was gone 1.27 seconds after the client transmitted while the client's keys arrived, and the server's key set became exactly the client's [#0914/M/n=2].
The same reading stated as the wipe alone is that the call wipes the server's copy of that player's modData, a key planted server-side only being gone from the server's census 1.27 s after the client transmitted [#1042/M/n=2].
A second subject reproduces the replace half: one transmit from the client made the server's copy exactly the client's, the planted probe key and the mod's nested table both crossing, the client-only hotbar key included, and the server census 2.04 s after the transmit already showing all seven keys [#1336/M/n=2].
A third reading states the two halves together: a key planted only on the server is gone from the server's census after the client transmits, while the client's planted key and a client-only vanilla key both arrive and the server's census becomes identical to the client's [#1496/M/n=1].
The call moves the whole table rather than the changed key, which is what the key counts show: the server's key count went from 4 to 6 after the client transmitted one key, a hotbar table riding along [#1638/M/n=1].

Server to client has the same shape with a thinner bound.
A server-to-client transmit is wipe-and-replace in the other direction too: after a server-driven transmit the client lost two keys, gained the server's key and left an empty server-only residual [#0915/M/n=1].
Stated per key, the call made on the server replaces the client's whole player-modData table: the client lost `hotbar` and its own `TKX_eat_onEat_client` and gained the server's `TKX_eat_onEat_server`, with the residual difference set empty [#1041/M/n=1].

Which value types survive the crossing — and which are dropped silently — is [`../facts/wire-packets.md#moddata-packet`](../facts/wire-packets.md#moddata-packet).

<a id="command-bus"></a>
### The command bus: the one route a mod fully controls

The sanctioned mod protocol is a client send, a server-side client-command handler that validates and mutates, and a server send back: the server validates and the client predicts at most, and for a nutrition mod this is forced rather than stylistic, because the eat completes on the server, so any nutrient maths has to run there and be pushed [#0932].

It is the only shape on this page whose payload, timing and direction the mod chooses.
Its costs are that both ends must be written, that the module name shares a namespace with every other mod on the server, and that nothing on it is durable — a bus round trip moves a value and stores nothing.
The harness in this repository is the smallest working example of the shape, and the worked examples below point at its three sites.

<a id="what-a-client-copy-is"></a>
### What a client's copy of a server object is, and is not

A client's copy of a server-owned object is the result of the last push that reached it.
It is not a simulation of the server's object, and where the client does run the same code it usually throws the result away.

The clearest case is weight.
A multiplayer client computes a weight and discards it: the `GameClient.client` early-out inside `updateWeight` sits before `setWeight`, before the trait counter and before `applyTraitFromWeight`, so client weight comes only from `Nutrition.load` and the weight-band traits never apply client-side [#0118/M/n=1].
Measured, a client-side weight write of 105 read back as 105 immediately with the Obese trait still false, reverted to 80 within 3 s and at least three packets, and the server read 80 throughout — so the write survives only until the next packet and the trait application never fires client-side [#0571/M/n=1].
The same probe stated shortest: a client `setWeight(105)` read back 105 with `hasTrait(Obese)` false and then reverted to the server's 80 within 3 s [#1195/M/n=1].
And the ownership reading of it: the server owns weight and the client never computes one, the weight update skipping before the setter, while the direction flags are written ahead of the skip and stay readable client-side [#1238/M/n=1].
Those three direction flags are not packet fields — each side computes its own — and they agree on both non-trivial arms, reading true, false, false at 1500 calories and false, false, true after a write of minus 100, because all three are written ahead of the client early-out inside the weight update [#0900/M/n=1].
So a client can derive a weight direction it cannot derive a weight.

The moodle case is the same shape without the discard.
Because the moodle recompute has no side guard, a client-side moodle read taken immediately after a server stat write can lag by up to one push [#0570/C/C-only].

On the item side the answer is decided per arm by a gate the reader cannot see.
`Food.update` has no client guard and `updateTemperature` runs unconditionally, while the push to a client is a `sendItemStats` fired once per game minute from inside the cooking branch, which is gated on the item being cookable and not frozen and on its heat being above 1.6 [#1111].
Above that gate the client's copy did move: on a server-pinned vanilla item held above the cooking gate, heat went 2 to 1.697029948234558 and cooking time 0 to 0.1182333305478096 over 10.5 s, bit-identical to the server across a 0.5 s read offset during which an independently ticking copy would have decayed further [#1109/M/n=1].
Past the gate it froze: on a server-spawned cooked item that had crossed the cooking gate, the client's copy of heat and cooking time was frozen across 11.1 s while the server's heat fell from 1.79561 to 1.39397 on the same instance [#1108/M/n=1].
Read as the carrier rather than the field, heat is carried but the client's copy does not simulate it: over those 11.1 s the server fell from 1.79561 to 1.39397 while the client stayed at 1.84703, holding the value the post-transition push had carried [#1411/M/n=1].
And the client's copy of that item did not reach the item update at all: over the same 11.1 s its heat, cooking time and age never moved while the server's ran two or three ticks, and the client arm of the time multiplier would have accumulated on any tick at all [#1421/M/n=1].
Whether a client's copy of an item advances is therefore answered per arm and never once: the three sessions that read one read it in three different arms of the same gate, and no single verdict covers all three [#1423/M/n=1].

Two fields behave as the shape predicts without any measurement of their own.
A client-side age write moves only the client's copy, is never pushed to the server and is never corrected, because nothing re-sends the age until the item is serialised whole [#0354/C/C-only].
A client's displayed freshness is therefore whatever the last full serialisation said, and can be arbitrarily stale [#0357/C/inference].

## Walls and bounds
<a id="walls"></a>

- A mod cannot add a field to the item-stats packet, nor depend on a field it omits: the class has no reset, no registry, no callback and no per-field opt-in [#1144/M/n=1].
- A mod cannot trust a zero-valued packet field, because the cached receiving object is what supplies the value the sender skipped [#1146/M/n=1].
- A mod cannot push a player stat from the client, nor observe or suppress the player-stats write, because the snapshot is unconditional and carries no filter [#1149/M/n=1].
- A mod cannot push an item stat field from the client either, because every arm of the item-stats send is a server-to-client fan-out; the one client-to-server item route is the item-fields sync, a different packet carrying modData and condition [#1150/C/C-only].
- A mod cannot transmit part of player modData: the packet sends the table and the receiver wipes before it writes [#1152/M/n=2].
- A mod can hold server-authoritative state in player modData only with a workaround, because the transmit that destroys it is somebody else's call [#1151/M/n=2].
- A mod can get a per-item mod value to the client anyway, by script, by item modData or by a bus round trip keyed on the item id [#1145/M/n=1].
- A mod can move mod state over the command bus, which is the one route with no wipe and no packet dependency [#1153/C/C-only].
- The item-field sync route is measured in the client-to-server direction only, and the server-to-client direction of it is untested [#1241/M/one-side, #1039/M/one-side].
- The server-to-client transmit rests on a single session against the client-to-server wipe's two, and it was graded after setting aside the one key the client's own handler rewrites each tick [#0915/M/n=1].
- Every reading on this page is taken on the dedicated-server path with one real client, one fixture and one character or one item per arm; single player is never claimed, and on that path the server arm and the client arm are the same process.
- No arm on this page was taken with more than one client attached, so nothing here speaks to what a second client's copy holds, or to whether a packet reaches every client or only the one it is about.
- Floats arrive over the command bus rounded to six decimal places, so no reading here supports a bit-for-bit claim except the two arms whose rows state one.
- Several of the code-read rows carry no bytecode offset, because the source they were taken from gives none for the method: the class and method names are the whole of the pointer [#0330/C/C-only, #0331/C/C-only, #0332/C/C-only].

Not covered: the transport layer beneath every packet on this page, the save and load round trip that the item's serialised blob travels on, every packet outside the food, nutrition, item-fields and player-modData set, the zombie and animal paths that share the same character updaters, and what any of this does with more than one client attached.

## Open
<a id="open"></a>

- Whether the eat packet is broadcast to every client or sent only to the eater — settled by dumping the packet send overload that takes a player, a packet type and an argument array; the receiver writes into the addressed player's nutrition either way, but the traffic cost differs; no `X` id [#0144/C/open].
- Whether a mod may call the latent client-to-server eat route — settled by calling the game client's eat-food method from a mod and reading both sides; its caller scan found none in the jar or in the game's own Lua; no `X` id [#0145/C/snapshot/open].
- What the server validates on an incoming nutrition write — settled by a probe that distinguishes rejection from overwrite; every probe so far shows a client write being overwritten by the next push, which is a different mechanism from validation; no `X` id [#0191/M/n=1/open].
- How often a multiplayer server re-sends inventory items, and therefore how often a client's freshness display refreshes — settled by tracing the cadence of the item-list receiver, whose carrier exists but whose cadence was not read; no `X` id [#0376/C/C-only/open].
- Whether the weight-band traits reach a multiplayer client at all — settled by driving a character into a band on the server and reading the client's trait list; the trait application never runs client-side and the player-stats packet does not carry the trait list, which has its own write and read methods, so some other packet presumably carries them; -> X4 [#0595/C/C-only/open].
- Why a client's copy does not run the item update for every field but cooking — settled by tracing what stops it; the call path from the character update through the recursive item updater to the item update carries no side guard, and the only guard on that path is an is-zombie test a player character fails; no `X` id [#1422/C/C-only/open].
- That the item-stats push is server-only, a silent no-op on a client with no client-to-server API for pushing an item's fields, is unverified: it is graded as measured in its source off a spike that predates the artifact convention and committed no JSON, so only the jar half is re-checkable; re-measure by re-running the spike's item arm under a committed artifact [#0912/C/uncommitted/unverified].
- That a client-side write to a player's modData does not reach the server until the client transmits, after which it does, is unverified: the two spike sessions wrote only to the gitignored run directory and left no artifact folder; re-measure by the plant-then-transmit census pair in a run whose artifact is committed [#1090/M/uncommitted/unverified].
- That there is no client-to-server push-my-item-fields API — a condition write, a condition-max write and an item modData write followed by the item-stats send never reaching the server, and a 60 s wait changing nothing — is unverified for the same reason: both spike sessions are uncommitted; re-measure by the same three writes and the long re-look under a committed artifact [#1092/M/uncommitted/unverified].
- That an item added to a player's inventory client-side never reaches the server, whose own copy of that inventory never gains the item, is unverified for the same reason; re-measure by a client-side add and a server-side inventory census in a committed run [#1093/M/uncommitted/unverified].
- That a client's write into player modData does not reach the server on its own — a planted client key leaving the server census at a key count of 4 in a bracket opening 0.51 s and closing 1.77 s after the write's acknowledgement — is unverified: its measured reading rests on a restricted artifact key, and the bracket rather than its far end is what the reading supports; re-measure by the same plant and census pair in a run whose key carries no restriction [#1335/M/n=1/unverified].
- That an item-scope modData census under a custom-name and tooltip exclusion set reads a key count of 1 on the client and 0 on the server, with nothing beyond vanilla on either, reproducing that the custom-name setter writes its key from the item's load as a deserialisation side effect on the side that deserialised — is unverified: its reading rests on a restricted artifact key, and the exclusion set is item-scope and applies nowhere else; re-measure by the same census on a vanilla item in a run whose key carries no restriction [#1346/M/n=1/unverified].
- That a server-pinned vanilla item held below the cooking gate at heat 1.2 has its client copy frozen to the bit at both reads 12.54 seconds apart while the server's decays to the 1.0 floor, making the gate the measured discriminator, is unverified: the reading rests on a restricted artifact key, and the temperature step runs unconditionally inside the item update, so the defensible statement is that the item update did not advance the client's held copy in that window; re-measure by the same pin and paired reads in a run whose key carries no restriction [#1110/M/n=1/unverified].
- That the pin's own push did arrive — the server-side setter firing the item-stats send on its way out and both sides reading the identical 1.2000000476837158 at the first read, so the freeze is not the client never seeing the value — is unverified for the same reason; re-measure with the same pin under an unrestricted key [#1345/M/n=1/unverified].
- That the below-gate arm supports only the narrower statement, that the item update did not advance the client's held copy in that window rather than that a client copy cannot tick, is unverified for the same reason, and frozen and non-cookable items and every other push path are untested; re-measure by adding a frozen arm and a non-cookable arm under an unrestricted key [#1344/M/n=1/unverified].
- The wall that a mod cannot trust a live item field's client copy to tick is unverified for the same reason: it rests on one cookable item in one window on one fixture, pinned below the cooking gate, while the temperature step runs unconditionally inside the item update; re-measure by the same pin with a frozen arm and a non-cookable arm beside it [#1148/M/n=1/unverified].
- The rule that a client-side read of a live item field is to be treated as a push rather than a simulation, and neither assumed, is unverified: each of the three arms is a single reading in its own session, the mechanism stays a code reading, and one item over one window on one fixture is what each arm rests on; re-measure by re-running all three arms in one session under an unrestricted key [#1112/M/n=1/unverified].
- The rule that a skill level and any item state be pinned on the server bus, because a client-only write reads back correct locally and is then overwritten by the server's copy, so an evolved recipe built at Cooking 10 can silently run at level 0, is unverified: the overwrite was seen only in an uncommitted shakedown run; re-measure by setting a perk client-side and reading both sides in a committed run [#0355/M/uncommitted/unverified].
- Decision: whether each mod-owned per-player quantity lives in a server-side table pushed with the bus or in player modData with an explicit transmit — a transmit by any other mod on that client replaces the server's whole table [#1042/M/n=2, #1088/M/n=1].
- Decision: whether each mod-owned per-item quantity rides item modData or the bus keyed on the item id — the item-field sync route is measured in one direction only [#1241/M/one-side].
- Decision: whether the mod ever reads a live item field on the client, or always asks the server — whether the client's copy advances is answered per arm [#1423/M/n=1].
- Decision: which side the mod's own nutrient maths runs on — the eat completes on the server, so a client-side implementation has no path to run on [#0110, #0109].
- Decision: whether the mod's client-side display reads the vanilla stores or a mod-owned mirror — a client write to a vanilla store is erased by the next snapshot while a write to a mod-owned field is not erased and drifts instead [#0568/M/n=2, #1637].

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| a server-owned value pushed with `transmitModData` | `testing/experiments/TKX_Nutrient/42.20/media/lua/server/TKX_Nutrient_Server.lua:47-57` | the server-to-client arm: a per-tick write into the player's modData, then a transmit armed by a key the driver plants and the handler clears, so the push is caused rather than waited for |
| the client control for that arm | `testing/experiments/TKX_Nutrient/42.20/media/lua/client/TKX_Nutrient_Client.lua:17-27` | the same event and the same table with a different key and no transmit, which is what lets a census say which side wrote which key |
| per-side state, one global per Lua state | `testing/experiments/TKX_Nutrient/42.20/media/lua/shared/TKX_Nutrient.lua:20` | the plain assignment each VM runs its own copy of: the counters and the `side` field are how a probe tells the two states apart |
| an item modData write pushed with the item-field sync | `testing/experiments/TKX_Nutrient/42.20/media/lua/server/TKX_Nutrient_Server.lua:22-31` | the item route end to end: the key's own presence as the already-done flag, the write, the sync call, and the counter that says which VM ran it |
| the bus dispatch | `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua:511-532` | registration into one command table and the poll that reads a sequence number, guards the handler with `pcall`, and writes the acknowledgement back — the shape both sides share |
| the server half of a bus round trip | `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua:578-587` | the sanctioned protocol's middle and end: a client-command handler that guards its work and answers with a server command to the asking player |
| the client half of a bus round trip | `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua:513-525` | the receiver that takes the server's authoritative view and compares it with the client's own, which is what makes a paired reading a reading rather than two |
| client-first paired reads around a transmit | `testing/experiments/s08_witness.py:385-394` | the plant, the client read, the server read, the transmit and the server read again, in that order, with the client half taken first |
| a paired snapshot helper | `testing/experiments/td2_simplestatus.py:365-377` | the client half read first at every tag, so the cross-side skew has a known sign and a band can be stated on it |
| a census pair with difference sets | `testing/experiments/td3_autocook.py:347-359` | both sides' player-modData census at one moment with the server-only and client-only sets, which is the reading a transmit's wipe half is graded on |

## See also

- [`../facts/wire-packets.md`](../facts/wire-packets.md) — the field contract of each packet on this page, and every measured per-field desync.
- [`../facts/nutrition-core.md`](../facts/nutrition-core.md) — the store the player packet carries, and its clamps.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md) — the stats and the weight bands whose ownership this page states.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md) — the order of writes inside the character's eat call, which runs on the server.
- [`../facts/food-item-model.md`](../facts/food-item-model.md) — the item's state axes, which decide what there is to own.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md) — the client-only mod whose UI handlers fire the transmit that wipes somebody else's keys.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md) — the mod that never transmits and loses its privacy anyway.
- [`overview.md`](overview.md) — the two Lua states and the process model this page's routes run inside.
- [`lua-platform.md`](lua-platform.md) — the Lua surface a mod reaches these routes through, and which side each script hook fires on.
- [`harness.md`](harness.md) — the command bus as an instrument, the witness contract and the probe rules the readings here were taken under.
- [`mod-anatomy.md`](mod-anatomy.md) — the folder layout and the checksum gate a one-sided mod has to satisfy first.
- [`../areas/mp-sync.md`](../areas/mp-sync.md) — what this mod decides to do about the routes and the ownership rows above.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiment an open row points at.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows this page cites by id.
