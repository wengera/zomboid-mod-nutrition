# New nutrients
Verified against 42.20.4 (b0bbce05d5) · 2026-10-05 · scope: where a mod nutrient can live, which wire route each store forces, what each store survives and where the nutrient's effect can attach; the ownership, routes and packets are `platform/mp-model.md` and `facts/wire-packets.md`, the vanilla stores `facts/nutrition-core.md`, the registries `platform/lua-platform.md`, and the verdicts `reference/wall-map.md`.

## Rules
<a id="rules"></a>

- Keep every durable mod value in character, item or global modData: live Java fields are unsynced cache, and only modData saves and syncs on engine paths [#1064/C/snapshot].
- Store inputs in modData and derive the values on read: a derived-on-read model needs no migration when a formula changes [#1068/C/snapshot].
- Keep a mod nutrient out of the vanilla macro stores: every setter clamps its store silently and the hard-coded drain moves it every tick, so a value parked there is cut and moved by vanilla rather than held [#0023/M/n=2, #1193/C/C-only, #2056/C/inference].
- Initialise world-scoped shared tables in `OnInitGlobalModData`: it is the sanctioned init point and it runs before players exist [#1066/C/snapshot].
- Reach a new nutrient on an item through an unrecognised key inside the vanilla `item` block, and on a drink's fluid through a Lua table keyed by the fluid's type string: the parser's default arm rawsets the key into the item's default modData and every instance receives a deep copy, while a `fluid` block has no default arm and stores no unrecognised key [#1089, #1187/C/C-only, #2676/C/C-only, #2682/C/C-only, #2684/C/C-only].
- Put a per-type value in the item script, or in a Lua table keyed by full type where no script key reaches, rather than in per-instance Lua state: script data loads per side and never crosses the wire, so the two sides agree for free [#1058/M/n=2, #2682/C/C-only].
- Keep server-authoritative per-player state out of player modData, or guarantee the client's copy is complete before anything on that client transmits: one client transmit makes the server's copy of that player's table exactly the client's [#1042/M/n=2, #1496/M/n=1].
- Batch every key one side owns into a single transmit: the call moves the whole table rather than the changed key, so a second transmit cannot repair what the first one dropped [#1638/M/n=1, #1091].
- Own every key on an item whose modData carries a mod nutrient: the item-field sync wipes the receiver's whole table before it copies the sender's keys, so a key the syncing side lacks is gone — a wipe measured in the client-to-server direction only [#1126/M/one-side, #2057/C/inference].
- Route every mod-owned mutation through the command bus: a client send, a server-side handler that validates and mutates, and a server send back is the one route a mod controls end to end [#0932].
- Run the mod's intake math where the eat completes: a multiplayer client never reaches the eat action's completion step, so nothing a mod hangs off the client side of that path ever runs [#0109, #0110].
- Write every player stat on the server: a client-side write to hunger, thirst, endurance, fatigue, calories, the macros or weight is erased by the next player-stats packet, so every one of them has exactly one owner [#0568/M/n=2].
- Give every mod nutrient a consumer the mod writes itself: the protein store has one vanilla consumer, the Strength experience grant, which raises Strength experience while the store is strictly between 50 and 300 and lowers it below −300, so a parallel protein store that leaves the vanilla store on its drain leaves that bonus and that penalty on vanilla's number, while the carbohydrate store as an energy pool and any notion of diet quality stay dead space [#2112/C/C-only, #1136/C/C-only, #1193/C/C-only, #2696/C/inference].
- Set the `Nutrition` sandbox option in the server's sandbox config: the nutrition update reads the option live every tick, a runtime flip from Lua is untried, and the Lua mirror of the option goes stale [#1127/C/C-only, #2058/C/inference].
- Reproduce in Lua on the server every arm of the nutrition update the mod still wants once that option is off: the option takes the macro drain, the calorie burn and the weight update together, three option-off scenario runs reading all three frozen, and vanilla's coupling of weight to the band traits goes with them [#1136/C/C-only, #1277/M/n=1, #2059/C/inference].
- Never register a moodle type of your own through the vanilla registry: a registered type reaches every character and is driven back to its lowest level every tick, and a duplicate id corrupts the registry before the call throws [#1140/C/C-only, #2060/C/inference].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or push the trait list after you write it as [the trait-push rule](../areas/mp-sync.md#rules) says: the band traits are not in the player-stats packet; they reach the affected player's client on the player-fields packet's trait block and on the timed experience packet, each as fresh as its last push, and no player-addressed push refreshes another client's copy [#2727/C/inference] [#2595/C/C-only] [#2606/C/C-only] [#2603/C/C-only] [#2612/C/C-only].
- Put slow simulation such as nutrient decay on `EveryOneMinute` or `EveryTenMinutes`, use `OnPlayerUpdate` only for per-frame needs behind a cheap early-out, and avoid `OnTick`: 38 mods already share `OnPlayerUpdate` and `OnTick` is the expensive tier [#1071/C/snapshot].
- Let every number a nutrient record carries rest on a settled row of the science register, on an open row the mod labels at the number, or on a game choice a plan ruling names and labels at the number, and ship none that has none of the three: the records built this way crossed their grades at the hours an offline replay of their kernel gives and ran three boots without a mod error [#3004/C/inference, #2978/M/n=1, #2976/M/n=1, #2975/M/n=1, #2993/M/n=1].
- Recompute every grade on the slow minute from the stored value, and rebuild a consumer's derived state only when the record's `epoch` counter has moved: the counter rises by one per minute in which a grade or an excess output changes, so a consumer that holds the last epoch it saw rebuilds on every change and on no other minute [#3005/C/inference, #1071/C/snapshot, #2978/M/n=1, #2979/M/n=1, #2991/M/n=1].
- Write THIRST on the server every tick as the water pool's view, as hunger is written, and make every route that puts water into a character reach the pool: a drink-action wrapper sees the container drink only, `autoDrink` and the no-item world-water drink run on the server under no wrapper, and a drink queued on a container the server has never seen raises in the action's `new` and drinks nothing [#3006/C/inference, #2925/C/C-only, #2931/C/C-only, #2939/M/n=1, #2940/M/n=1, #2942/M/n=1, #2943/M/n=1, #2962/M/n=1, #2966/M/n=1].
- Bracket `autoDrink` rather than switching it off: skip the handler's own call while a drop in THIRST is pending and land the litres that drop stands for, because the server's flag does not hold a Lua `setAutoDrink(false)` and every call that clears its gates with THIRST above 0.1 drinks `min(amount, 2 x thirst)` litres with no cooldown [#3007/C/inference, #2927/C/C-only, #2928/C/arith., #2929/C/C-only, #2939/M/n=1, #2941/M/n=1, #2965/M/n=1].
- Cap a world-water drink at the litres its action planned, counting what landed on the action itself: `ISTakeWaterAction` plans `min(2 x THIRST, source litres)` once, and each step transfers its target share less what it counts as already drunk from the fall in THIRST, so a THIRST the mod writes for itself misleads that count [#3008/C/inference, #2930/C/C-only, #2931/C/C-only, #2970/M/n=1].
- Freeze the sleep state at rested unless `SleepAllowed` and `SleepNeeded` are both true: on a server where either is false vanilla resets FATIGUE to its default on every update before the stat hook, a fatigue write made outside the hook was erased at the next update in the measured session, and a sleep state that went on moving would drift from the stat it is meant to drive [#3009/C/inference, #2723/C/C-only, #2793/C/C-only, #2947/M/n=1, #2948/M/n=1].
- Read the thermoregulator's getters on the server only, and guard against `getThermoregulator()` answering nil: the server's body-damage tick is what updates it, and a client's copy read an air temperature of 27.0 and an energy multiplier of 1.0 at every paired poll against the server's computed values [#3010/C/inference, #2933/C/C-only, #2934/C/C-only, #2935/M/n=1, #2936/M/n=1].
- Hold the THIRST view at 0.83, which reads as moodle level 3, with the mod's deficiencies-can-kill dial on or off: the level-4 health term is compiled into the body-damage tick and costs 11.88 health per game hour on the default day whatever a mod dial says [#3011/C/inference, #3123/C/inference, #0518/C/arith., #0519/M/arith., #2969/M/n=1, #2971/M/n=1].

## How it works

A mod nutrient is a number the engine has no slot for.
The `Nutrition` object is closed: it carries no mod-data table, no generic accessor and no registration call, and its save and load are a fixed list of floats [#1121/C/C-only].
It cannot be swapped for an object of the mod's own either, because no class anywhere in the jar names a setter for it [#1185/C/C-only].
Every mod nutrient therefore lives beside the vanilla stores rather than inside them, and two questions decide it: where the number lives, and what it does once it is there.
The two options tables below lay out the choices for each question; this section reads what each store choice then forces.

The vanilla stores are no host for it.
Every one of the four intake stores passes a clamp inside its setter, so a write outside the range lands on the limit and nothing reports it ([#0022/M/n=2, #0023/M/n=2], [nutrition-core.md#clamps](../facts/nutrition-core.md#clamps)).
The three macro stores are also drained on every tick at rates compiled into the update rather than read from anywhere a mod can reach [#1193/C/C-only].
A value a mod parks in a vanilla macro store is therefore cut by the clamp on the way in and moved by the drain afterwards, which is why the rules above keep a mod nutrient out of those stores.
The clamps are two-sided and the negative side is a working range: nothing holds the calorie store at zero, so a negative store is an ordinary state rather than an error [#0901/M/n=1].
A parallel store passes through none of these setters, so it has no range at all until the mod gives it one, and that range is a decision under [Open](#open).

Nor does vanilla leave anything for a mod nutrient to plug into.
Calories are the only driver of weight, and carbohydrates and lipids act on it only as multipliers of the gain rate [#0180].
Proteins never touch weight, and of their two readers outside the weight model one sits behind thresholds the clamps make unreachable while the other, the Strength experience grant, is live [#2648/M/n=2].
Everything past weight and that grant is therefore dead space, a reading stated with its row at [the effect-path options](#effect-paths).
The same fact cuts the other way: nothing in vanilla will act on a mod nutrient, so every consequence it is to have is a path the mod writes, and [the effect-path options](#effect-paths) are the places such a path can attach.
Hunger and calories do not feed each other in either direction, so a mod store can be driven from calories, from hunger or from neither without disturbing a vanilla coupling [#0500, #0501, #0503].

The two sections below take the stores one at a time.
The first reads the wire route each store forces, which is where most of a store's cost lives.
The second reads what each store survives, which is where the evidence is thinnest.

<a id="sync-route"></a>
### Which route each store forces

No vanilla packet carries a mod nutrient, so every store's route is one the mod chooses or none at all.
The player-stats packet's nutrition payload is the `Nutrition` object's own floats and nothing else ([#1481], [wire-packets.md#player-stats-packet](../facts/wire-packets.md#player-stats-packet)).
A client-side write to a vanilla store is erased by that packet, while the same kind of write to a mod's own field is never corrected and desyncs from what the server keeps computing — the erasure measured on vanilla calories, the custom-field half read off the packet's field list rather than measured [#0129/M/n=1].
The item-stats packet cannot be taught a new field either, because the class has no registry, no callback and no per-field opt-in [#1144/M/n=1].
What is left are the shapes [mp-model.md](../platform/mp-model.md#shapes) names: an explicit transmit, the item-field sync, the command bus, and script data that needs no route.
Anything that alters what an eat delivers has to run where `Eat` runs, on the server, which leaves three viable shapes: mutating on the server over the command bus, keeping a parallel store in player modData and transmitting it on change, or accepting client-only semantics [#0128/C/inference].
The third shape holds only while every input the client derives from is packet-carried, so its dependency list is written down wherever it is used [#1508].

Character modData travels only when somebody transmits it.
Both sides hold a copy of a character's mod-data table, and nothing moves between the two until a transmit is called [#0913/M/n=1].
The transmit serialises the whole table and the receiver wipes its own copy before it writes, so an empty sender's table wipes the receiver outright [#1091].
Both directions have that shape, client to server measured on two subjects and server to client on one [#0914/M/n=2, #0915/M/n=1].
The call is not the owning mod's to schedule.
Any mod on the same client that transmits replaces the server's copy of that player's table, and a mod that never transmits at all still had its whole table carried across the first time something else on that client did ([#1151/M/n=2], [#1088/M/n=1]).
One corpus viewer fires that transmit from its panel's mouse and key handlers, none of which knows anything about another mod's keys ([#1482], [simplestatus.md#mp](../facts/other-mods/simplestatus.md#mp)).
Part of the table cannot be sent, so a mod that transmits its own keys sends everyone else's with them [#1152/M/n=2].
What survives the crossing is decided by a type byte: strings, numbers, booleans and nested tables travel, while functions and Java objects are dropped without an error ([#1495], [wire-packets.md#moddata-packet](../facts/wire-packets.md#moddata-packet)).
The route this store forces on a server-authoritative nutrient therefore has two parts: the authoritative copy lives in a server-side table or in global modData, and the client's copy arrives as a server command rather than as a transmit [#1151/M/n=2].
A value the client owns outright loses nothing when a client transmit replaces the server's copy, but a server-to-client transmit replaces the client's copy in turn, client-only keys included, so even that value is exposed to any server-side transmit for that player [#0915/M/n=1, #1123/M/n=2].

Item modData travels with the item-field sync, and it moves whole.
An item's mod-data table is Lua-shaped on both sides and both sides hold a copy of it [#0909/C/C-only].
The sync's modData step wipes the receiver's table and copies the sender's keys, so the table moves wholesale in whichever direction the call runs [#1241/M/one-side].
The direction measured is client to server only: the write and the call both ran in the client's Lua state, the item-write counter reading one there and zero on the server [#0910/M/n=1].
That measurement does establish that the route works, a mod key reading back beyond vanilla's on both sides of one item [#1039/M/one-side].
The server-to-client direction has never been run, and that line sits under [Open](#open) [#1040/M/one-side/open].
`Eat` closes with an item-field sync of its own on the item it ate from, and on the real eat path `Eat` runs on the server, so that sync leaves in the unmeasured server-to-client direction and a per-item nutrient on a partly eaten food rides a crossing nobody has measured [#0124/M/n=1, #0110].
A census of the table is not empty even for a mod that writes nothing, because vanilla itself puts a custom-name key into item modData, which a vanilla control item also carried [#1415/M/n=1].
And the two sides' tables for one item need not match: one apple read an empty table on the server while its client copy held that key [#1639/M/n=1].
The route this store forces is a single owner per item: every key on the item has to be held on whichever side calls the sync, or the next sync from that side removes it, which is the item rule above.
Where a per-item value is the same for every instance of a type, the script carries it with no route at all, and where it varies per instance and must reach a client, the bus keyed on the item's id addresses the same instance on both sides [#1145/M/n=1].

Global modData is the store this library has read least.
It is saved like the other two modData scopes [#1122/C/C-only], and its init hook is one of the pair that survives a dedicated server, where `OnCreatePlayer`, `OnGameStart` and `OnLoad` never fire [#0895/C/one-side].
A new character still has a server-side hook: `OnNewGame` fires on a dedicated server when a client creates a character, with the new player as its argument [#2387/C/C-only].
No run here has moved a global table between sides.
The one corpus instance read kept its config in a global table through a create-or-get call and the global transmit, with an init handler and a receive handler beside them, and later versions of the same mod moved that config into per-player modData [#1479/C/snapshot].
A census of such a table cannot tell a populated store from an absent one, because the create-or-get call makes the very table the census then reads [#1480].
Its route is therefore a reading of one mod's code rather than a measurement, and what its transmit does to the receiver's copy is unread.

A parallel Lua store has one route, and it is the command bus.
A plain table in the server's Lua state is not modData, so no transmit and no item sync ever touches it; the sanctioned protocol — a client send, a server-side handler that validates and mutates, a server send back — is the only way its contents reach a client [#0932].
The bus carries only what the mod puts on it, so it wipes no table the mod did not name.
Its module names share one namespace with every other mod's command sites [#1153/C/C-only].
A round trip moves a value and keeps no copy of it, so the store's durability has to come from somewhere else, which is the reading under [what each store survives](#persistence).

A script key needs no route at all.
Item scripts load per side and never sync, so a value a script declares is identical on both sides for free [#1058/M/n=2].
An unrecognised key inside an item block is neither dropped nor rejected: the default arm writes it into the item's default modData and every instance receives a copy [#1089].
That is what lets a script-declared nutrient be read back off an instance's modData on either side [#1125/C/C-only].
The script object is a poor witness even for the vanilla macro keys it declares, so a per-item value is read off an instance rather than off the script [#1124/M/n=1].
The price of the route is the checksum: every loaded script file, a mod's included, feeds one hash the server compares, and a mismatch is a disconnect rather than a silent degrade [#1182/C/C-only].
A script key is load-time state on each side with no runtime reconciliation, so it can carry what a food contains and never what one instance has become [#0648/C/inference].

Read together, the routes say which owner each store can serve, and at what price.
The script serves a value fixed per type and needs no workaround at all [#1124/M/n=1].
Item modData serves a per-instance value under its direction bound, a workaround verdict of its own [#1126/M/one-side].
A server-side table or global modData mirrored down over the bus serves a per-player value the server owns [#1151/M/n=2].
Character modData serves a value only the client owns, and even that only with a workaround, because a server-to-client transmit replaces the client's copy, client-only keys included [#0915/M/n=1, #1123/M/n=2].
That is a reading of the route rows above, and [the store options](#store-options) set a cost and a wall beside each choice.

<a id="persistence"></a>
### What each store survives

Four events test a store: a save, a rejoin, a foreign transmit and an item that changes type.
One run has restarted a world and re-read modData keys: a key in a player's modData and one in a global table both survived a clean save and reload, while a fixture boot missed them [#1294/M/n=1].
The save is the boundary: with the world autosave off a global value written a game-minute before a hard kill was lost, because the server writes the file only on a console save or a clean quit [#2098/M/n=1] [#2097/M/n=1].
Item modData across a save, and every scope across a rejoin, remain a code reading backed by the corpus [#1122/C/C-only].

A save keeps modData and nothing else a mod writes.
Character, item and global modData are the only durable mod state the engine saves [#1122/C/C-only].
A live Java field a mod sets is unsynced cache, so a durable value belongs in modData and anything live has to be derivable from it [#1064/C/snapshot].
A parallel Lua store is therefore gone at every boot unless the mod rebuilds it from a modData copy, which makes it a cache in front of a durable store rather than a store of its own.
A script key survives by being re-read rather than saved: the default table is rebuilt from the script at every load, while an instance's copy was made when the instance was created and rides that instance's item modData [#1089].
What a saved instance holds after the mod changes a script value — its saved copy or the new default — is read nowhere in this library.
The corpus's parallel-stat blueprint banks its value in character modData and derives everything else from it on read, which is the shape that needs no migration when a formula changes ([#1526/C/C-only], [#1068/C/snapshot]).
That blueprint's own persistence is a reading of its code: on a dedicated server its authoritative copy is a global modData table and the character's table a mirror the server re-publishes every tick, and no run evidences it ([#2855/C/C-only], [beyondten.md#mp](../facts/other-mods/beyondten.md#mp)).

A rejoin starts the server's copy of a player's table empty.
The server's copy of a player's modData is empty at join and gains even the vanilla keys only some seconds after the session is ready, while the client's copy already holds its keys [#1432/M/n=1].
A server-side reader of a nutrient kept in character modData therefore cannot assume the key is present early in a session.
Early in a session the client's copy is the fuller of the two, and a client transmit then makes the server's copy exactly the client's [#1042/M/n=2, #1496/M/n=1].
Whether a rejoining player's value comes back through the server's save or through the client's copy is the save-and-reload question, and it is not measured.
Item modData and global modData have no rejoin reading at all, and a parallel Lua store is untouched by a rejoin because it never left the server.

A foreign transmit hits character modData, and the item-field sync plays the same part for item modData.
Any transmit from a client replaces the server's whole copy of that player's table, and the mod that loses data is never the one that called it [#1151/M/n=2].
A server-to-client transmit replaces the client's copy the same way, a mod's client-only keys going with it [#0915/M/n=1].
Item modData carries the same exposure to the item-field sync, from whichever side calls it, with only the client-to-server half measured [#1241/M/one-side].
A parallel Lua store is out of reach of both, because the player transmit serialises the player's modData table and the item-field sync moves item modData and condition, so neither reaches a table the mod keeps in its own Lua state ([#1091], [#1241/M/one-side]).
A script key's default is out of reach too, since script data crosses no wire, but an instance's copy of it is an item-modData key and shares that table's exposure [#1243/M/n=1].
Global modData is a table of its own rather than the player's, so a player transmit does not reach it, and what its own transmit does is unread [#1091].

A type change replaces the item, and the per-item stores stay with the old one.
A cook transition with a cooked-replacement link adds each named item with the condition states copied over and removes the original [#0266].
A rotten-replacement link does the same on rotting, copying the age and the condition states onto the new item before destroying the old one [#0243].
Neither swap names item modData among what it copies, so a nutrient held in the original's item modData is not shown to reach the replacement, and the library has not read whether it does.
The replacement is a new instance built from its own script, so it receives its own type's default modData, which is where a script-key nutrient on the new type comes from [#1089].
Both swaps run on the server only: a client never runs the method that creates a rotten replacement [#0757], and the cook transition is driven by server-owned state [#0758].
Cooking that does not change the type leaves the instance where it was, and one cook and one burn left an item's stored nutrition untouched [#0277/M/n=1].
Every non-zero craft delta in the recipe data is a recipe that changes what the item is, so a craft that moves nutrition does it by producing a different item [#0742/C/snapshot].
The per-player stores and the parallel Lua store are untouched by any of this.

Set side by side, the stores trade the four events against each other.
Character modData survives a save on the code's reading and loses to a foreign transmit.
Item modData survives a save on the same reading and is not shown to cross a type change.
A parallel Lua store survives every transmit and no boot.
A script key survives everything by being re-read, at the price of carrying one value per type.
None of those survivals is measured across a restart, which is why the store decision and the save-and-reload experiment sit side by side under [Open](#open).

<a id="record-engine"></a>
### The record engine

A record kept in modData and stepped on the slow minute is a number the engine never reads, so a live session can hold it to an offline replay of the arithmetic that steps it.
What the mod's record engine measured on itself is a reading of the mod, [testing-your-mod.md](testing-your-mod.md#scenario-inputs).

<a id="fluids"></a>
### The fluids

The thermoregulator's getters answer live on the server and read defaults on a client [#2935/M/n=1, #2936/M/n=1].
A server-written THIRST reaches the client within 0.00085 [#2962/M/n=1].
`autoDrink` fired under a stat handler's call and no drink wrapper saw a sip [#2939/M/n=1, #2940/M/n=1], and the server's `setAutoDrink(false)` did not hold [#2941/M/n=1].
A world-water drink ran on the server under no drink wrapper [#2942/M/n=1].
A drink queued on a container the server had never seen raised in the action's `new` [#2943/M/n=1].
The THIRST moodle read level 3 at 0.83 and level 4 at 1 [#2971/M/n=1].
What the mod's fluids measured on themselves is a reading of the mod, [testing-your-mod.md](testing-your-mod.md#scenario-inputs).

<a id="acute-states"></a>
### The acute states

With sleep not both allowed and needed the fatigue reset erased each of three server writes at the next update, and with both true a write held [#2947/M/n=1, #2948/M/n=1].
A held sleep on a server that allows and needs sleep ran the world clock about twenty times its waking rate [#2956/M/n=1].
A beer drunk through the drink action raised INTOXICATION as the can emptied [#2950/M/n=1], and the value decays on a server at 7.5599 per game hour [#2951/M/n=1].
`BodyDamage.JustTookPill` adds the item's fatigue and stress terms [#2954/C/C-only] and ends by calling the pill's `OnEat` [#2955/C/C-only], and whether a script `OnEat` a mod gives the pill runs on the server is unmeasured [#2960/C/C-only/open].
What the mod's acute states measured on themselves is a reading of the mod, [testing-your-mod.md](testing-your-mod.md#scenario-inputs).

## Options

<a id="store-options"></a>
### Where a mod nutrient can live

Five stores can hold a mod nutrient, each priced by the route it forces and the events it survives, which the two readings above give in full.
The table orders them by the wall map rows their tags cite.

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| character modData | per player and saved with the character, measured across one clean reload; both sides hold a copy and nothing crosses until a transmit, which moves the whole table and wipes the receiver first | the transmit is anybody's: one client transmit replaces the server's copy of the player's table, so a server-authoritative value needs a copy the transmit cannot reach, and the table cannot be sent in part | [#1122/C/C-only, #1294/M/n=1, #1123/M/n=2, #1151/M/n=2, #1152/M/n=2] |
| global modData | world-scoped and saved with the world, measured across one clean reload, while a write since the last save is lost to a hard kill; initialised on the global init hook, which survives a dedicated server; a per-player value is keyed by hand | its crossing is read off one corpus mod's code and never measured, and a census cannot tell a populated table from an absent one | [#1122/C/C-only, #1294/M/n=1, #2098/M/n=1, #1151/M/n=2, #0895/C/one-side, #1066/C/snapshot, #1479/C/snapshot, #1480] |
| a script key | free on both sides: scripts load per side and never sync, and an unrecognised key lands in default modData on every instance; one value per type, fixed at load | every script file must match byte for byte or a joining client is disconnected; the value cannot vary per instance; a second mod's partial block against an already-populated table is a code reading | [#1124/M/n=1, #1125/C/C-only, #1182/C/C-only] |
| item modData | per instance and saved with the item on the code's reading; moves with the item-field sync, which wipes the receiver and copies the sender's keys | the sync is measured client to server only; a key the syncing side lacks is gone; a type change builds a new instance from its own script | [#1126/M/one-side, #1145/M/n=1, #0266] |
| a parallel Lua store | a server-side table the mod owns outright, out of reach of every transmit and every item sync, mirrored to the client over the bus | not durable: only modData is saved, so the table is rebuilt from a modData copy at every boot, and the bus's module names share one namespace with every other mod | [#1151/M/n=2, #1153/C/C-only, #1064/C/snapshot] |

Which store holds each mod nutrient's authoritative value, and which store, if any, carries its copy to the client?

<a id="effect-paths"></a>
### Where a mod nutrient's effect can attach

The protein store has one live vanilla consumer, the Strength experience grant, so a parallel protein store that leaves the vanilla store on its drain leaves that grant's bonus and penalty on vanilla's number, while the carbohydrate store as an energy pool and any notion of diet quality stay dead space ([#2112/C/C-only, #1136/C/C-only, #1193/C/C-only, #2696/C/inference], [perks-and-strength.md#xp-grants](../facts/perks-and-strength.md#xp-grants)).
Nothing in vanilla reads a mod nutrient either, so its effect is a path the mod attaches to a vanilla surface.
The corpus shows why the maths behind that path sits in a tick of the mod's own: a value injected into a vanilla function's local variable breaks silently on a game update [#1078/C/snapshot, #1532/C/C-only].

An effect that scales with exertion has an activity input in the engine already: the thermoregulator's metabolic target, set from a fixed enum of activity classes in MET [#2631/C/C-only].
Each class is a floor rather than an assignment, the highest class that applies setting it [#2633/C/C-only].
The target is then raised again by tiredness and by carried load, so it can sit above the class the character's activity names [#2649/C/C-only].
The character declares no getter for it, so it is read through the body damage's thermoregulator [#2635/C/C-only].
The classes, their values and both raises are stated at [body-and-weight.md#metabolic-rate](../facts/body-and-weight.md#metabolic-rate), read from the bytecode and never measured, and whether the server classifies a connected player's activity at all is open there [#2633/C/C-only].

A script key is not the only per-type home a nutrient value can have.
The copy of a script key each instance receives, stated under [what each store survives](#persistence), is a deep one, so a write to one instance's key reaches neither the type's default nor a sibling instance [#2676/C/C-only].
A drink's fluid cannot carry one at all, because a `fluid` block has no default arm and stores no unrecognised key [#2682/C/C-only].
A Lua table keyed by full type puts no key on any instance, and a table keyed by the fluid's type string, which is never null, reaches a drink's fluid where no script key can [#2682/C/C-only, #2684/C/C-only].
The vanilla macros such a table is built against come off a fresh instance, because the script item answers no macro getter ([#2679/C/C-only], [item-pass.md#minimal-block](item-pass.md#minimal-block)).

Four surfaces can take an effect, and the table orders them by the wall map rows their tags cite.

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| the weight model | a vanilla surface with live consumers, the other being the Strength grant on the protein store: a mod nutrient moves it by writing weight or the calorie store on the server, and the band traits it drives apply at once when forced from Lua; owning the model means switching vanilla nutrition off at the sandbox and reproducing every arm the mod still wants | the thresholds and rates are compiled in; the switch takes the drain, the burn and the weight arm together; a client never computes weight, and a band trait reaches it only on the server's pushes to that player, which no run has measured | [#1127/C/C-only, #1135/C/C-only, #1136/C/C-only, #1137/M/n=1, #1138/M/n=1, #2112/C/C-only, #2595/C/C-only], [wall-map.md#g4](../reference/wall-map.md#g4) |
| the eat hooks | the intake math runs where the eat completes, on the server; a server-side wrapper of the completion sees the item before `Eat`, and `OnEat` can correct the numbers after vanilla has written them | the wrapper can stop `Eat` only by skipping it; `OnEat` fires on both sides with no numbers on the client's call, so one handler runs on each side; a cancelled eat under the partial-eat guard applies nothing | [#1128/M/n=1, #1129/M/n=1, #1130/M/n=1, #1131/M/n=1, #1132/C/C-only] |
| the moodle surface | each side recomputes moodles from its own stats, so a moodle needs no sync; the one route to a new moodle is adopting `MoodleFramework` and registering through its API | a moodle type a mod registers on the engine is held at its lowest level every tick; an existing moodle's thresholds are unreachable from Lua; none of `MoodleFramework`'s legs is measured on this build | [#1140/C/C-only, #1141/C/C-only, #1143/C/C-only], [wall-map.md#d4](../reference/wall-map.md#d4) |
| the item pass | the effect is expressed through the values a food already delivers: one minimal `module Base` block per item merges per key and leaves every untouched key to upstream | every shipped script file must match byte for byte on both sides; rewriting hunger is not weight-neutral and can land under the partial-eat guard; mod-added foods fall outside the pass | [#1180/M/n=1, #1181/M/n=1, #1182/C/C-only] |

Which surface does each mod nutrient's effect attach to, and which vanilla quantity, if any, does that effect move?

## Walls and bounds
<a id="walls"></a>

- A mod cannot add a field to the `Nutrition` object nor substitute an object of its own: the object is closed with a fixed save list, and no class in the jar names a setter for it [#1121/C/C-only, #1185/C/C-only].
- No vanilla packet can carry a mod nutrient: the player packet's nutrition payload is fixed and the item packet takes no new field ([#1481], [#1144/M/n=1], [wire-packets.md#item-stats-packet](../facts/wire-packets.md#item-stats-packet)).
- A mod cannot change the thresholds or rates inside the weight update, and the one nutrition-side lever switches the whole update off rather than tuning it [#1135/C/C-only, #1127/C/C-only].
- The drain cannot be stopped one store at a time: registering a stat-tick handler skips the seven stat updaters whatever the handler returns, and the nutrition update is not among them [#2744/C/C-only, #2238/C/C-only].
- A moodle type a mod registers on the engine reaches every character and is never driven above its lowest level, so registration gives a mod nutrient no moodle ([#1140/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- An existing moodle's thresholds cannot be reached from Lua, because the class that holds them is not exposed and no exposed method returns one ([#1141/C/C-only, #2040/C/C-only], [lua-platform.md#registries](../platform/lua-platform.md#registries)).
- A mod nutrient's moodle is a Lua-drawn widget, `MoodleFramework`'s or the mod's own, whose framework API and missing multiplayer surface are read from its live tree while no run has drawn either on a client, as [the wall map's moodle verdict](../reference/wall-map.md#d4) records.
- A band trait or a new mod trait reaches only its own player's client, on two server pushes — the once-a-second experience packet and the player-fields packet's trait block — and with no push a server trait write reached that client within about half a second, a registered trait the same way on a client loading the same mod, so a nutrient effect expressed through a trait reaches that client's list within the experience push's second ([#2595/C/C-only, #2603/C/C-only, #1158/C/C-only] [#2759/M/n=3] [#2760/M/n=1], [wall-map.md#g4](../reference/wall-map.md#g4), [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)).
- A client's copy of a mod nutrient is the last value that reached it and never a simulation of the server's: a client write to a mod field is corrected by no packet and simply desyncs, a reading of the packet's field list rather than a measurement ([#0129/M/n=1], [mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is)).
- A client derives a weight direction and never a weight: it discards the weight it computes and never applies a band trait, while the direction flags are written ahead of that skip [#1138/M/n=1, #1139/M/n=1].
- No nutrient formula can be generated at runtime: the dynamic string compiler is unreachable from Lua, so every code path exists as a file on disk at load time [#1172/C/C-only].
- Persistence is measured for one clean reload and one hard kill, in the player and global scopes, on one fixture with the world autosave off; item modData and every other survival on this page rest on the code and the corpus [#1294/M/n=1] [#2098/M/n=1] [#1122/C/C-only].
- Item modData's crossing is measured in the client-to-server direction only [#1126/M/one-side].
- Every verdict this page leans on is bounded to one build on a dedicated server with one client, one fixture and one admin character, and single player is never claimed [#1256/C/one-fixture].

Not covered: the save and load path beyond one clean reload and one hard kill of the player and global scopes; the global store's own transmit and receive path, read only off one corpus mod's code; the mod file writer as a store of last resort; any session with more than one client attached; and what a second nutrition mod writing the same modData scopes would do beside this one.

## Open
<a id="open"></a>

- Whether item modData moves from server to client — settled by a server-only key write, a client-first census that must miss it, a forced item push and a second census; -> X14 ([#1040/M/one-side/open, #0885/M/n=1/open, #1280/C/open], [open-questions.md#x14](open-questions.md#x14)).
- Whether Lua can flip the nutrition option at runtime, whether the flip replicates and whether the drain stops — settled by a harness route to the option's config setter and a session reading the Java option, the Lua mirror and the drain beside a no-flip control; -> X17 ([#1283/C/open, #0139/M/n=1/open, #0140/C/C-only/open], [open-questions.md#x17](open-questions.md#x17)).
- Whether `MoodleFramework` loads whole and renders a registered moodle at a non-zero level — settled by one session that drives a registered moodle past a threshold on the client and reads its level and draw through the framework's access call, beside a value that must leave it undrawn; -> X29 ([#1295/C/open, #0884/C/C-only/open, #2742/M/n=1/open], [open-questions.md#x29](open-questions.md#x29)).
- Decision: which store holds each mod nutrient's authoritative value — forced by modData being the only durable mod state while any client's transmit replaces the server's copy of a player's table [#1122/C/C-only, #1151/M/n=2].
- Decision: what range each mod nutrient store is held to, and whether it runs negative — forced by vanilla's clamps living inside the `Nutrition` setters that a parallel store never passes through, and by negative vanilla stores being an ordinary state [#0022/M/n=2, #0023/M/n=2, #0901/M/n=1].
- Decision: whether each mod nutrient decays, and on which clock — forced by vanilla's drain being compiled into the nutrition update and reaching no store but its own macro stores [#1193/C/C-only].
- Decision: whether a per-item nutrient is a per-type script value, an entry in a per-type Lua table or per-instance state — forced by a script key agreeing on both sides for free while every instance takes a deep copy of it, by a `fluid` block storing no script key at all, and by item modData moving whole and being measured in one direction [#1124/M/n=1, #2676/C/C-only, #2682/C/C-only, #1126/M/one-side].
- Decision: whether a per-item nutrient must follow an item through a type change — forced by the replacement being built from its own script, with the swap naming the condition states and the age, and not item modData, as what it copies [#0266, #0243].
- Decision: whether any mod nutrient acts through vanilla's weight model or through a model of the mod's own — forced by the model's one switch taking the drain, the burn and the weight arm together [#1136/C/C-only], and by the Strength grant on the protein store being the one other vanilla consumer, with the carbohydrate store and diet quality dead space [#2112/C/C-only, #2696/C/inference].

## See also

- [`../platform/mp-model.md`](../platform/mp-model.md) — ownership, the shapes mod state travels in, wipe-and-replace and the command bus, which the route reading above is taken from.
- [`../facts/wire-packets.md`](../facts/wire-packets.md) — what each packet carries and omits, and every desync measured per field.
- [`../facts/nutrition-core.md`](../facts/nutrition-core.md#clamps) — the vanilla stores, their clamps and the weight model a nutrient's effect can reach.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#weight-traits) — the band traits the weight model drives, the metabolic-rate classes, and the vanilla moodles.
- [`../facts/perks-and-strength.md`](../facts/perks-and-strength.md#xp-grants) — the Strength experience grant, the protein store's one live vanilla consumer.
- [`../facts/food-item-model.md`](../facts/food-item-model.md#fluid-blocks) — the per-instance modData copy and the fluid block that stores no mod key.
- [`../platform/lua-platform.md`](../platform/lua-platform.md#registries) — the moodle and trait registries, and what a registration does not give.
- [`../platform/loader-and-scripts.md`](../platform/loader-and-scripts.md#default-moddata) — the default modData arm a script key rides, and the per-side script load.
- [`../facts/other-mods/beyondten.md`](../facts/other-mods/beyondten.md#architecture) — the parallel-stat blueprint banked in character modData and derived on read.
- [`../facts/other-mods/simplestatus.md`](../facts/other-mods/simplestatus.md#mp) — the corpus viewer whose transmit replaces a neighbour's keys.
- [`mp-sync.md`](mp-sync.md) — what this mod decides about each route and each owner.
- [`ui-and-moodles.md`](ui-and-moodles.md) — the display surfaces, and the moodle route in full.
- [`item-pass.md`](item-pass.md) — the item pass as an effect path, and its risks.
- [`eat-and-cook-hooks.md`](eat-and-cook-hooks.md) — the hook sites an intake effect attaches to.
- [`open-questions.md`](open-questions.md) — every open row and experiment named above.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows the two options tables cite.
- [`../reference/experiments.md`](../reference/experiments.md) — the full spec of each named experiment.
