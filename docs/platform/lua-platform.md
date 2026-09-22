# The Lua platform
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: the Lua a mod runs inside on this build — the Kahlua dialect's gaps, what a protected call catches and what an unguarded raise costs on each side, how a Java member is reached, how the three script-side hooks resolve and which side calls each, the event and `Hook.*` surfaces, the moodle and trait registries, the APIs removed on this build, file IO and the in-session reload loop; which file runs at all, the packet field lists and the order of writes inside `Eat` are handed off.

## Rules

- Index a Java member before you call it: a call on a nil member raises, and the message is built from the enclosing closure's name, so an absent member and a throwing member are the same reply [#0934/C/C-only, #0952/M/n=1].
- Nil-check `isServer` and `isClient` before the protected call that reads them: a protected call on a nil comes back as a failure that names nothing, which turns absence into an error string instead of a branch [#0937/M/n=1].
- Put a protected call at every engine and third-party boundary: it keeps your own handler body running, which the survival of the handlers behind you does not give you [#0944/M/n=1, #0948/M/n=1].
- Keep a raising call out of a client launched with the debug flag: the failure helper's debug arm enters the modal break and the process never answers again, on two boots out of two [#0954/M/n=2, #0955/C/C-only].
- Name a script hook's target as a bare global function: the eat path resolves the script's name through the Lua manager's function-object lookup, which never finds a local or a table member [#0921/C/C-only].
- Define that global in a `shared/` file and branch on the side inside it: the folder decides nothing, and the eat hook fires on both sides [#0922/M/n=1, #1031/M/n=1].
- Sit in a server-side wrapper of the eat action's completion when the mod needs the item before `Eat` touches it: the wrapper must hold its sentinel outside any table the shared file re-creates, guard on a nil-checked `isServer()` because the mod's `server/` file also runs in the client VM, and call the original unless it means to skip `Eat` entirely [#1190/M/n=1, #1033/M/n=1].
- Never put mod logic in a client-side wrapper of a timed action's completion: the Lua complete is skipped on a client, so the wrapper installs and then stays silent [#2005/C/C-only].
- Walk a Java list by its size and its per-index getter from zero: the length operator does not work on one and the pairs iterator raises on any Java-backed object [#0940/C/C-only, #0941/C/C-only].
- Format a number through a fixed-point branch rather than an integer conversion, and write every file without `goto`: the dialect raises on the first and does not have the second [#0939, #0938].
- Test a Java class against the exposer's class set before you plan on it: the exposure test is a strict membership test, so a class the jar carries and the exposer does not register is unreachable [#0963/C/C-only].
- Read per-item macro values off an instance getter or out of the script text: the script object carries no macro getter, and the dialect publishes methods rather than fields [#0920/M/n=1, #1011/M/n=1].
- Hold a wrapper's sentinel in a global of its own: the shared file re-creates its state table by plain assignment on every load, so a sentinel kept inside it is wiped while the old wrapper is still installed and the next install wraps the wrapper [#0943/C/C-only].
- Guard any file you mean to reload against double registration: the reload command re-runs that one file and re-registers nothing, so a file that adds a handler on load adds a second one [#1880/C/C-only].
- Write run output through the Lua file writer rather than the mod file writer: the Lua writer is rooted at the cachedir's Lua folder and takes a five-entry extension allowlist that includes JSON, which is what lets a complete parse be the ready signal [#1866/C/C-only].
- Hang no rot logic on the container-update event in multiplayer: the aging call fires it only off a server and a client never runs the aging call, so the event never fires for a rot transition [#0358].
- Do a mod's durable boot work on the global-mod-data init hook or the server-started hook: the player-creation, game-start and load hooks never fire on a dedicated server [#0895/C/one-side].
- Compare a trait by the registry object and never by its name: the name getter answers lowercased, so a string comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].

## How it works

<a id="kahlua-limits"></a>
### The dialect and what it lacks

The dialect is Kahlua rather than PUC Lua, and the gaps below are the ones every Lua file in this library is written around.
None of them is a Lua-version difference a mod can feature-detect around: each is simply absent, and the cost of finding out at runtime is a raise.

Calling a member a Java object does not have raises a bare runtime exception carrying the text `tried to call nil`, thrown directly by the interpreter's call opcode, with the interpreter's own failure sites routing through the Kahlua utility failure helper instead [#0934/C/C-only].
The side-test globals still get a nil check before a protected call, not because the raise escapes but because a protected call on nil comes back as a failure that names nothing, so an absent global and a throwing global are the same reply [#0937/M/n=1].
Kahlua has no `goto`, so a Lua file in this library uses loops and early-outs only [#0938].
Formatting a Lua number with an integer conversion raises, so the harness formats integers through a fixed-point branch with its own cut-off at `1e15` [#0939].
The length operator does not work on a Java list, so a Java list is walked by its size and per-index getter from zero [#0940/C/C-only].
Iterating a Java-backed object with the pairs iterator raises, so the global-walk command takes a hop only when the node is a Lua table and gates its key count on the same test [#0941/C/C-only].
Kahlua's string formatter is its own reimplementation whose significant-figure conversion cannot be established from the bytecode, so it is not Java's, and the bus renders numbers with the `tostring` path instead, which round-trips a non-integral double exactly [#0942/C/C-only].
Kahlua has no JSON library, so the harness ships a forty-line encoder and Java objects fall back to their string form [#1867].

<a id="pcall"></a>
### What a protected call catches

A protected call is the guard a mod writes for itself, and both of the shapes a nil call arrives in are measured.
What it does not do is tell you which member was nil, which is why it is the second half of a guard and never the whole of one.

A protected call catches a Kahlua nil call in the argument slot on both sides, returning false and the string `tried to call nil java.lang.RuntimeException`, byte-identical per side and on both passes of one session [#0944/M/n=1].
It also catches the nested shape, where the nil call happens inside a function handed to it, returning false and the string `Object tried to call nil in pcall java.lang.RuntimeException` with the lines after it still running, read in the server VM only because the debug client froze before it answered anything [#0945/M/n=1].
The nil call is a real raise and not a false return: the call opcode loads the callee, branches on it being non-null and throws on the other arm, with no branch that returns false without raising [#0946/C/C-only].
The protected call's try covers both the call opcode and the nested interpreter loop it runs after pushing a frame, which is why both shapes are caught, and its throwable arm — the only one around that call — concatenates the message with the class name beside a false boolean, making it the single producer of the observed string [#0947/C/C-only, #2008/C/C-only].
Quote the whole string, class name included, because it is the message concatenated with the class name rather than a message in its own right [#0944/M/n=1].
A caught Kahlua nil call names nothing: no log ever prints the missing global, because the message is built from the enclosing closure's name [#1225/M/n=1].
The caught argument-slot call also leaves the engine silent: neither console carried a trace, and the probe's global name, the alternative wording and the exception logger all had zero hits, because that raise is the call opcode's direct throw and never reaches the utility failure helper [#0950/M/n=1].
That silence is a property of the caught argument-slot shape and says nothing about an unguarded raise, which is [the next section](#raises) [#0950/M/n=1].

<a id="raises"></a>
### What an unguarded raise aborts

An unguarded raise is bounded twice over: once by the dispatcher that wraps each callback, and once by the chunk a file scope runs inside.
Every measured arm below was read in the server VM over two passes of one session on one probe file, because the client parked before it reached the unguarded handler [#0948/M/n=1, #0949/M/n=1, #0951/M/n=1, #0952/M/n=1].

`Event.trigger` routes every callback through `LuaCaller.protectedCallVoid` inside a per-iteration catch of `Throwable` that logs the exception and continues the loop, so a raise in one handler cannot reach the handlers registered behind it [#0896/C/C-only].
An unguarded nil call aborts the rest of the handler body it fires in: the tail counter after the raise stayed at zero on both passes after about seventy fires, in the server VM only [#0948/M/n=1].
The handlers registered behind a raising handler still run: the behind counter advanced by seventeen in lockstep with the counter ahead of the raise [#0949/M/n=1].
Both raise shapes of that session are logged in full — 73 engine hits each for the nested-call wording and the handler-add wording — so a raise a mod caught through the nested shape is still logged [#0951/M/n=1].
That reading covers two raising handlers in one probe file on the server VM of one session, which is one probe shape rather than a survey of raise origins [#0951/M/n=1].
No log ever prints the name of the missing global: both probe globals had zero hits on both sides, because the interpreter builds the message from the enclosing closure's name before calling the failure helper and falls back to an unknown marker, naming the closure and never the missing global [#0952/M/n=1].
At file scope an unguarded raise aborts the rest of that chunk: the whole file chunk runs inside one protected call, so a raise inside it ends the chunk and the failure arm logs and returns null, read from the bytecode and never raised in a session [#1226/C/C-only].
A rim protected call therefore protects the handler's own body rather than the other handlers, which is the only half of the guard the chain's survival does not already give [#0896/C/C-only].

<a id="debug-break"></a>
### The debug client's modal break

The break is a client-only branch of the failure helper, and it ends a session rather than logging one.

A debug client does not survive an unguarded mod raise: on two independent boots the harness client reached the in-game state, printed one complete trace and then stopped — console dead, the ready line never printed, the bus never answering, the process still alive [#0954/M/n=2].
That reading is bounded to the harness's admin client, which launches with the debug flag; a release client is unmeasured [#0954/M/n=2].
The break runs through the Kahlua utility failure helper: it tests the debug flag against the UI's default thread, and on the true arm prints its failure message and calls the UI breakpoint on the current file and the previous line before the throw — and the breakpoint returns unless the debugger-on-error flag is set, returns at once on a server so no server ever breaks, and otherwise swaps to the debug thread, raises the break callback and enters the modal UI sync pump [#0955/C/C-only].
What sets the debugger-on-error flag is unread [#0955/C/C-only].
The two sides took different arms of that helper: the client's log carries the printed failure message and never the throw, and the server's carries only the throw, so the client never left the breakpoint [#0956/M/n=2].
That is two boots for the client arm and one session for the server arm, with the cause a code reading confirmed by those two log signatures [#0956/M/n=2].
It is false that any Lua error freezes a debug client: the same debug client under the caught argument-slot shape never froze, because that shape never reaches the failure helper — and catching a raise does not help either, because a caught nested raise takes the same route, so on a debug client only the index-first guard, which never raises at all, keeps the session alive [#0957/M/n=2].
Split any follow-up by raise origin — the call opcode's direct throw against the interpreter loop's failure helper — rather than by handler shape [#0957/M/n=2].

<a id="java-members"></a>
### Reaching a Java member

Kahlua publishes a Java class's methods and never its fields, so a member is reached by indexing the name on the object and then calling what comes back.
Two things decide whether a member is reachable at all: whether the exposer registered its class, and whether the member is a method rather than a field.

An argument-arity mismatch and an ambiguous overload raise the same way as a nil call, and whatever a Java member throws comes back out as a runtime exception carrying the class name — which is why the zero-argument getter witness passes nothing to the member it reads and the harness refuses a nil id before an overloaded lookup rather than paying for the dispatch [#0936/C/C-only].
That re-throw shape is a bytecode reading and is not measured here, because the practice is never to make the call [#0936/C/C-only].
The item-user class exists on the jar but is not in the exposer's constant-pool class set, where the inventory item and the item container both are, so Kahlua cannot reach it — and that membership test is the exposure test for any Java class a mod wants to call [#0963/C/C-only].
That is a constant-pool read of the exposer rather than a failed call, and no corpus mod calls the class [#0963/C/C-only].
The static the crafting code itself calls is absent for exactly that reason, so the harness reaches it by indexing the global and then the member before the protected call, not because the raise escapes but because a caught nil call names nothing, and the route that actually runs is the current-uses setter [#1740/C/C-only].
`zombie/characters/Stats` has no `getHunger` or `getThirst`: its complete method list is 34 entries whose only stat accessors are `get`, `set`, `add`, `remove`, `reset`, `isAtMinimum`, `isAtMaximum` and `isAboveMinimum`, each taking a `CharacterStat`, as of a single reading of the method list on this build [#0105/C/snapshot].
The jar-wide scan behind it found no call site for either name, so the absence is a snapshot of one build rather than a standing guarantee [#0105/C/snapshot].
Hunger and thirst are read from Lua through `getStats():get(CharacterStat.HUNGER)` and `(CharacterStat.THIRST)`, the route every live snapshot answered with; the harness tries the enum first and short-circuits, so the run proves that route works rather than that the others fail [#0106/M/one-fixture].
`getNutrition()` is declared on `IsoPlayer` and not on `IsoGameCharacter` [#0897/C/C-only].
Vanilla offers no extension point on the nutrition object itself: its whole method list is 26 members — the five stores, the three direction flags, the update, calorie and weight updaters, the two trait appliers, the weight-trouble and fitness-XP tests, and save and load — with no mod-data accessor and no generic accessor, and no class on the jar carries a nutrition setter literal, so Lua cannot substitute a different object for the one the engine constructs [#0889/C/C-only].
Reading a perk's experience takes two calls and never one: the character's experience getter is zero-argument and answers an inner experience object, and the number comes from that object's per-perk getter — which is why a zero-argument getter witness cannot read it and the harness carries a dedicated command; the level itself reaches the client within one bus round trip [#0918/M/n=1].
The round-trip half is one session and one character; the two-call shape is a method-list reading [#0918/M/n=1].
The script-level `Calories`, `Carbohydrates`, `Lipids` and `Proteins` keys are not reachable from Lua: they are public fields on `Item` with no getter, and all four came back absent through the `get`, `is` and field routes on one probed item, reached through the script manager's own lookup [#0107/M/one-fixture].
The same absence holds on both sides and on mod items as well as vanilla ones: the instantiation path reads those fields straight into the food instance, and the dialect publishes methods, so per-item macro numbers must come off an instance or out of the script text [#0920/M/n=1].
That was read over four items on two sides in one session, re-confirming two earlier ones [#0920/M/n=1].
The script object is a poor witness for macros in particular: it answers the seven shelf-life and cooking keys while reporting the four macro keys absent on both sides, so only an instance getter discriminates [#1011/M/n=1].

<a id="script-hooks"></a>
### The three script-side hooks

Three hooks can be named from inside an item block, and they do not share a resolution rule; that is the trap.

An item block's eat hook is resolved by global function name: the eat path asks the Lua manager for a function object by the name the script gives and calls it through the protected caller, so a local or a table member is simply never found [#0921/C/C-only].
An item block's cook hook resolves by a different route: the cook block does a raw get on the Lua environment for the name and calls it through the protected caller, and a name containing a dot is split and looked up two levels — so a table member works for the cook hook and does not work for the eat hook [#0924/C/C-only].
An item block's creation hook runs at instantiation, once, on whichever side instantiates: the item initialiser asks the Lua manager for the named function and calls it with the item, under the same global-name rule as the eat hook, and the instantiation path calls it only when the item is not yet initialised — and item scripts load on both sides [#0926/C/C-only].

`OnEat` fires through `LuaCaller.pcallvoid` as `fn(item, character, fraction)` at the point [the order of writes inside `Eat`](../facts/eating-pipeline.md#eat) puts it, is handed the rescaled fraction rather than the menu percentage, and has its return value ignored [#0093].
An `OnEat` hook can still mutate `hungChange` or `calories`, and `multiplyFoodValues` then operates on the mutated values, read off the order of the two calls rather than measured [#0094/C/inference].
`OnEat` is the only vanilla hook on the intake path, and in multiplayer it fires on the server inside `Eat` and separately on any receiver of `EatFoodPacket`, with no numeric effect there [#0130].
`IsoGameCharacter.EatOnClient` is that second call site: the hook-only twin the packet receiver uses, which type-checks, makes the identical `OnEat` call and returns true, writing no stats and no nutrition [#0095].
So the client's call comes from the packet twin rather than from `Eat`, and because that twin applies no numbers the second firing is a notification and not a double-apply [#0923/C/C-only, #2004/C/C-only].
An item block's eat hook fires once on each side: after a single whole-item eat the probe's call counter read one on the client and one on the server, at a consumed fraction of one [#0922/M/n=1, #1031/M/n=1].
That single full-fraction eat cannot separate once per eat from once per portion, and no session has put a partial eat beside it [#1031/M/n=1].
An `OnEat` hook reads post-intake numbers on both sides: the calories read inside the hook were 890.4 on the client and 890.4 on the server for an eat that started from 786.86 [#1034/M/n=1].

A Lua wrapper of `ISEatFoodAction:complete` installed from a mod's `server/` file runs server-only: the completion counter read 1 on the server and 0 on the client [#1032/M/n=1].
A server-side wrapper of `ISEatFoodAction:complete` runs before `Eat` dispatches `OnEat`: the order string read `complete onEat ` on the server against `onEat ` on the client [#1033/M/n=1].
The wrapper, the counter and the order reading are one eat at full fraction in one session on the default fixture, with three mods written for it [#1032/M/n=1, #1033/M/n=1, #1034/M/n=1].
`LuaTimedActionNew.complete` skips the Lua complete on a client, so a client-side wrapper of a timed action's `complete` installs and then stays silent [#2005/C/C-only].
A server-side wrapper of `ISEatFoodAction.complete` must therefore be sentinel-guarded outside any table the shared file re-creates, guarded with a nil-checked `isServer()` because the mod's `server/` file also runs in the client VM, and must call the original unless it means to skip `Eat` entirely [#1190/M/n=1].
When a mod installs such a wrapper at file scope and retries it on two boot events, the file-scope install is the one that wraps on both sides: the recorded install site read back as the file scope on the client and on the server, and neither boot event re-wrapped because the sentinel made them no-ops [#0894/M/n=1].
The retry is cover for load order rather than for the install [#0894/M/n=1].

The cook hook is not server-gated in the dispatch itself but is reached only by the side that runs the cook transition: on both teardown sessions every hook print was in the server console and the client's was empty, because the client's copy never reached the transition [#0925/M/n=1].
The dispatch there is a code reading and the side is the measurement, taken once per run over one item and one cook transition each [#0925/M/n=1].
A client that did drive its own copy of a modded item to the cook transition would call a nil Lua function, and neither session reached that state, so the behaviour stays unmeasured [#1394/C/C-only].
One corpus mod's server-side cook hook rewrote 11 fields on the crafted instance, printing in the server console — the worked case of the hook doing real work ([the teardown](../facts/other-mods/longtermpreservation.md#architecture)) [#1208/M/n=1].

<a id="events"></a>
### The events this library exercised

The curated event table carries 13 events with the side each fires on, its cadence and what this library did with it, together with corpus usage counts written as hooks over distinct mods and recomputed on 2026-09-10 across the 230-mod inventory; it is curated rather than an inventory, and the counts are a dated census whose full form is [the corpus event census](../facts/other-mods/catalog.md#corpus-facts) [#0890/C/snapshot].

| Event | Fires on | Cadence / when | What this library did with it |
|---|---|---|---|
| `OnClientCommand(module, command, player, args)` | **server** | once per `sendClientCommand` | the server arm of the harness bus; corpus 54 / 20 |
| `OnServerCommand(module, command, args)` | **client** | once per `sendServerCommand` | the client arm, which is where the witness replies land; corpus 43 / 14 |
| `EveryOneMinute` | **both** — measured | one game minute | the nutrient probe's whole drive train, one arm per tick; over one session the counter read **58 client / 38 server**, because the client VM ran the `server/` file's handler as well as the `client/` one. Also the harness's belt-and-braces server poll; corpus 22 / 10 |
| `EveryTenMinutes` | not exercised here | ten game minutes | named as the other slow tier and **never registered by this library**; it is below the corpus histogram's top-12 cut, so its absence there is a floor artifact, not a zero |
| `OnTick` | **both** | every frame | the harness's server poll, deliberately throttled `ticks % 20`; the expensive tier — corpus 70 / 15 |
| `OnPlayerUpdate` | client | per player, per frame | **never registered by this library**; recorded because it is the corpus's most *widely* shared hook (55 / 39) and therefore the shared perf hotspot to stay off |
| `OnCreatePlayer` | **client only** | after Click-to-Start | simpleStatus builds its whole panel here and has no server counterpart at all, which is why it cannot be authoritative about anything |
| `OnInitGlobalModData` | both; **the server-side init point** | during world init, before players exist | simpleStatus's global-config pair `OnInitGlobalModData` / `OnReceiveGlobalModData`; corpus 33 / 14. With `OnServerStarted` it is the pair that survives a dedicated server, because `OnCreatePlayer` / `OnGameStart` / `OnLoad` never fire there |
| `OnServerStarted` | **server only** | end of world init | the eat-hook probe retries its `ISEatFoodAction.complete` install here; the harness logs a line; corpus 11 / 6 |
| `OnGameBoot` | launch, both VMs | once at launch | the eat-hook probe's third install site; corpus 38 / 16 |
| `OnPreFillInventoryObjectContextMenu` | client | every inventory right-click | AutoCook's only real entry point, and it lives in `common/`; vanilla fires it at `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua` with `(playerNum, context, items)` |
| `OnKeyPressed` | client | per key | simpleStatus forwards keys to its bar |
| `OnFETick` / `OnPostUIDraw` | client | per UI frame — `OnFETick` stops once the client leaves `MainScreenState`, `OnPostUIDraw` fires in **every** state | the harness's client poll registers **both** for exactly that reason, throttled `ticks % 30` |

The real-time length of a game minute is a property of the fixture's day length rather than of the event, and it lives with [the harness](harness.md#time).

`EveryOneMinute` fires on both sides: one mod's per-tick counter advanced in the client VM and in the server VM within the same session, with the client's count inflated because the client VM ran the mod's `server/` file handler as well as its `client/` one [#0892/M/n=1].
The three client-only boot events `OnCreatePlayer`, `OnGameStart` and `OnLoad` never fire on a dedicated server, which is a mirror reading and corroboration only [#1620/W].
`OnInitGlobalModData` and `OnServerStarted` are therefore the pair of hooks that survives a dedicated server, read from a corpus mod that registers the first in a dedicated-server tree; no session here has registered a handler on each of the five to measure it [#0895/C/one-side].
The aging call fires the container-update event only when the process is not a server, and a client never runs the aging call, so in multiplayer that event never fires for a rot transition and a mod cannot hang rot logic on it [#0358].
Each severe-moodle health term that comes out positive also fires `OnPlayerGetDamage` with the character, the moodle label `HUNGRY` or `THIRST`, and the amount ([the moodle effects](../facts/body-and-weight.md#moodles)) [#0517/C/C-only].
That event is a bytecode reading and has not been caught on the live server [#0517/C/C-only].

<a id="hooks"></a>
### The `Hook.*` surface

The named-hook surface is the engine's own trigger table, separate from the script keys and from the event roster above, and what a hook returns can replace vanilla work rather than merely observe it.

A Lua `CalculateStats` hook that returns true skips every stat updater for that tick, read from the bytecode and not exercised on the live server [#0469/C/C-only].
The auto-drink path fires the Lua hook named `AutoDrink`, also read from the bytecode and not measured [#0482/C/C-only].
Neither of those two is an intake hook, and the nearest question — whether the drink path can be wrapped the way the eat path is — is [a wall](#walls).

<a id="registries"></a>
### The moodle and trait registries

Two registries are open to a mod on this build, and what each registration is actually worth is settled at [the walls](#walls) rather than by the method that performs it.
Both go through the same registry helper, which is the one part of either that can leave shared state broken.

Moodles are not script-registered on this build — a search of `media/scripts` for a moodle file returns nothing — and the moodle type is instead a registry of 26 Java statics whose level thresholds live in the moodle stat class, as of one scan of the install [#0504/C/snapshot].
The moodle type and moodle stat registration methods exist on the jar — a name form, a base form and a flag-and-name form for the type, and a type-plus-five-floats form for the stat — and the moodle type enumeration is exposed to Lua; nothing here has registered one [#0969/C/C-only].
`MoodleStat` declares `get(MoodleType)` together with `setLowestThreshold` and its siblings, read from the bytecode and not exercised on the live server [#2040/C/C-only].
What each of those two declarations is worth to a mod is [a wall](#walls) rather than a door.
`Registry.register` is mutate-then-validate: a duplicate id corrupts `byObject`, `byLocation` and `values` before it throws, and nothing rolls back [#1198/C/C-only].
A mod that registers the same id twice therefore leaves the registry in a state no later call repairs [#1198/C/C-only].

`CharacterTraitDefinition.addCharacterTraitDefinition(CharacterTrait, uiName, cost, description, free, disabledInMultiplayer)` is public static and Lua-exposed, alongside `addGrantedTrait`, `addGrantedRecipe`, `addXPBoost(Perk,int)`, `addMutuallyExclusive`, `setTexture` and `setDisabledInMultiplayer`; it is what the generated character-trait script drives, and the last argument is optional [#1212/C/C-only].
Registering the trait object is therefore only half of adding a trait: selectability comes from that definition call, the trait carries no Java effect of its own and its sync path is untraced [#1158/C/C-only].
Whether a mod can rely on a weight-band trait client-side is open for that same reason [#1161/C/C-only/open].
`CharacterTrait`'s `getName()` returns the trait name lowercased, so adding the Hearty Appetite trait puts `heartyappetite` into `getKnownTraits()` and a weight in the Obese band puts `obese` there: a name comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].
On this build `hasTrait` takes a `CharacterTrait` enum rather than a String, and all 71 call sites in `media/lua` pass the enum, which is a grep plus inference rather than a live call [#0551/C/C-only].

<a id="removed-apis"></a>
### Removed or absent on this build

Each absence below is a live hazard rather than trivia, for the reason [the dialect's nil call](#kahlua-limits) gives and with [the index-first guard](#java-members) as the only cover.

The dynamic string compiler is present only as a dead string constant in three jar classes and is not reachable from mod Lua; the corpus sweep counts zero users across 230 mods and the lint keeps it out with an error rule [#0960/C/snapshot].
The string-argument trait test does not exist on this build — the character class exposes only the trait-object and trait-array forms — and the one corpus mod that still calls it does so in shadowed `common/` copies that the window-build path never executes [#0961/M/n=1].
The item type-string getter is absent from both the inventory item class, which carries a plain type getter and a gun type-string getter, and the script item class; the one corpus mod that still calls it does so in a shadowed `common/` copy [#0962/M/n=1].
Both of those corpus readings are one session over one workshop mod, and the non-execution is a state reading rather than a call trace [#0961/M/n=1, #0962/M/n=1].
The character stats class carries neither a hunger getter nor a thirst getter on this build, hunger and thirst being reached through the stats collection's per-stat getter instead; no corpus user is recorded and no sweep has looked for this member, so the absence of callers is unmeasured rather than zero [#0964/C/C-only].

<a id="file-io"></a>
### What Lua may read and write

The Lua file writer is rooted at the cachedir's Lua folder, rejects relative-path escapes, accepts and creates subfolders, and checks the extension against a five-entry allowlist — so marker files are not possible and not needed, a file that parses as a complete JSON object being the ready signal; the mod file writer writes into the mod's own folder instead, which is not what run artefacts want [#1866/C/C-only].
That is a bytecode reading on this build, and the same reader and writer pair is what carries the harness's own request and acknowledgement channel on both sides ([the bus](harness.md#bus)) [#1866/C/C-only].
Whether the mod file writer carries an extension limit of its own is an unverified reading from a spike that committed no artefact, and it sits in [`## Open`](#open).

<a id="dev-loop"></a>
### The in-session dev loop

The reload surface is one file at a time, and it undoes nothing a file did on its previous load.

The fast authoring loop is a single-file reload on the server plus an absolute-path reload through the client command bus, one file at a time [#1879].
The reload command matches its argument with a suffix test against the loaded-file list and runs that file and nothing else: no events are re-registered, so a file that adds a handler on load will add a second one, and any file meant to be reloaded must guard against double registration [#1880/C/C-only].
That is a bytecode reading of the command on this build [#1880/C/C-only].
A sentinel for a wrapped vanilla method must live outside any table the shared file re-creates: the mod's shared file re-creates its own state table by plain assignment on every load, so a reload of that file would wipe an inside sentinel while the old wrapper was still installed and the next install would wrap the wrapper [#0943/C/C-only].
Four readings of what the reload itself does — the survival of globals across a server-side single-file reload, the path form the client-side reload global needs, the usability of reloading every file on a dedicated server, and whether a server reload reaches clients at all — come from a spike whose artefact was never committed, and they are stated once in [`## Open`](#open).

## Walls and bounds
<a id="walls"></a>

A mod-registered moodle type reaches every character and is never driven above its lowest level, so the registration methods the jar declares lead nowhere ([the wall map](../reference/wall-map.md)) [#0969/C/C-only, #1140/C/C-only].
The class that holds every moodle's level thresholds is absent from the exposer's class set and no exposed method returns one, so the setters the bytecode declares cannot be reached from Lua at all [#2040/C/C-only, #1141/C/C-only].
A raise at file scope is a bytecode reading with no session behind it: the chunk-abort is the one unguarded-raise arm this library never raised, and the measured arms are all handler-body arms [#1226/C/C-only].
Whether the drink path can be hooked the way the eat path is hooked is not settled: the declared hook roster carries no eat, drink, consume, digest or nutrition name, and the wrapper route by analogy with the eat action has never been tried [#1133/C/C-only/open].
Not covered: the Kahlua standard library beyond the members this library called, the UI and ISUI Lua layer, the animation, sound and vehicle bindings, the debug console and its command surface, the declared event roster beyond the events named above, coroutines and any threading behaviour, and the Lua side of the crafting and context-menu pipelines — none of them was read.

## Open
<a id="open"></a>

- Whether an unguarded nil call on a client aborts the body and spares the handlers behind it the way it does on a server — settled by a run that reaches an unguarded raise on a client that stays alive, which needs a client launched without the debug flag; -> X23 [#0959/M/n=2/open].
- Whether the item block's creation hook fires as the bytecode says, and what it can seed at instantiation — settled by a session that instantiates a modded item through the game's own craft path with the hook registered; -> X31 [#0967/C/C-only/open].
- Whether a resident mod's protected-call wrapper changes what an unguarded raise does on a client — settled by a three-mod profile booted twice with the two mod orders, reading the loader's override tail, the globals of both mods and the client console for both failure signatures; -> X26 [#1545/M/n=1/open].
- Whether the moodle stat class's absence from Kahlua can be shown live rather than read off the exposer — settled by a global read of that class beside two controls that must answer in the same call; -> X2 [#1141/C/C-only].
- The explanation of an earlier client outage as the raise aborting the bus-pump handler's body on every tick is unverified: that run predates the artifact convention and has no committed JSON, so it is reasoning from the measured abort rather than a measurement of the outage; re-measure by a session that parks a raising handler on the bus pump and reads the bus from the other side [#0953/C/uncommitted/unverified].
- That the Lua file writer is limited to `ini`, `cfg`, `txt`, `log` and `json` while the mod file writer is not, so data export from in-game tooling remains possible on `42.20.x`, is unverified: the reading exists only in a spike's gitignored findings file with no committed artefact folder; re-measure by writing one file of each allowed and disallowed extension through both writers in a session that commits its artefact [#1120/M/uncommitted/unverified].
- That a server-side single-file reload re-runs one file with globals intact is unverified, its spike having committed no artefact folder; re-measure by editing a version constant on disk and reloading with the tick counter and the bus sequence read on either side of the call [#1876/M/uncommitted/unverified].
- That the client-side reload global needs an absolute path is unverified for the same reason; re-measure by calling it with a bare file name and then with the client's own full path, reading the version constant after each [#1877/M/uncommitted/unverified].
- That reloading every Lua file on a dedicated server is not usable is unverified for the same reason; re-measure by driving the reload-all command and counting the Lua error lines in the server log against a clean baseline [#1878/M/uncommitted/unverified].
- That a server-side single-file reload is server-local with no packet to clients is unverified for the same reason; re-measure by reloading on the server and reading the client's copy of the same constant [#1975/M/uncommitted/unverified].
- The design must choose where an intake correction sits, because the server-side completion wrapper runs before `Eat` while the eat hook runs at the point [the order of writes inside `Eat`](../facts/eating-pipeline.md#eat) puts it [#1033/M/n=1, #0093].
- The design must choose whether a per-item nutrient value is seeded at instantiation or read from the script on demand, because the creation hook is unexercised while the script object answers nothing about macros [#0967/C/C-only/open, #1011/M/n=1].
- The design must choose whether mod moodles are attempted at all, because registration reaches every character while the level never rises and the thresholds cannot be reached [#1140/C/C-only, #1141/C/C-only].
- The design must choose whether a new trait carries any effect in Lua, because the definition call makes it selectable and saved while nothing in the registry gives it a Java effect [#1212/C/C-only, #1158/C/C-only].

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| the nil-checked side test | `testing/experiments/TKX_PcallProbe/42.20/media/lua/shared/TKX_PcallProbe.lua:24-25` | each side global checked against nil before the protected call that reads it, so absence becomes a branch instead of an error string |
| the caught nil call, argument slot | `testing/experiments/TKX_PcallProbe/42.20/media/lua/shared/TKX_PcallProbe.lua:29-34` | the shape every index-first guard uses: an undefined global passed as the protected call's function argument, with the lines after it recording whether the call caught |
| the ordinary-error control beside it | `testing/experiments/TKX_PcallProbe/42.20/media/lua/shared/TKX_PcallProbe.lua:36-37` | the control handler that must catch whatever the nil call does, so a silent probe is distinguishable from a broken one |
| the nested protected call | `testing/experiments/TKX_RaiseProbe/42.20/media/lua/shared/TKX_RaiseProbe.lua:31-35` | the raise one frame deeper, inside a function handed to the protected call, with its own tail counter |
| the unguarded raise and the handler behind it | `testing/experiments/TKX_RaiseProbe/42.20/media/lua/shared/TKX_RaiseProbe.lua:36-40` | the body-abort and chain-survives pair: a tail counter after the raise, and a counter registered behind the raising handler |
| the eat-hook seat | `testing/experiments/TKX_EatHook/42.20/media/lua/shared/TKX_EatHook.lua:41-59` | the hook target as a bare global in a `shared/` file, on the engine's own signature, with an index-first guard around every Java member it touches |
| the side test a hook resolves per call | `testing/experiments/TKX_EatHook/42.20/media/lua/shared/TKX_EatHook.lua:27-37` | the nil-checked side resolution written as a function, because a Lua state can load the file before the side is decided |
| the wrapper seat and its sentinel | `testing/experiments/TKX_EatHook/42.20/media/lua/server/TKX_EatHook_Server.lua:31-63` | the sentinel held outside the table the shared file re-creates, the saved original kept for the chain, and the wrapper reading the item before `Eat` consumes it |
| the install site that wins | `testing/experiments/TKX_EatHook/42.20/media/lua/server/TKX_EatHook_Server.lua:67-74` | the file-scope install with two boot-event retries behind it, each a no-op once the sentinel is set |
| how the silence reading is sized | `testing/experiments/x126_pcall.py:138-152` | the grep block behind the engine-silence reading: a limit is a break rather than a window, and client limits are doubled because the client runs two Lua states |
| how a parked client is kept a reading | `testing/experiments/x127_raise.py:655-672` | the bounded, caught wait for a client that may never answer, which is what turned the debug break into a result instead of a lost session |

## See also

- [`overview.md`](overview.md) — which page owns which mechanism, and the two Lua states a mod lands in.
- [`loader-and-scripts.md`](loader-and-scripts.md#lua-load-order) — which file runs at all, and how `require` resolves through the merged map.
- [`mod-anatomy.md`](mod-anatomy.md) — the mod folder a Lua file ships in, and which tree the live chain reads.
- [`mp-model.md`](mp-model.md#command-bus) — the routes mod state travels on, and which side owns each quantity.
- [`harness.md`](harness.md#bus) — the command bus this library reads every measurement through.
- [`lessons.md`](lessons.md#rules) — the standing rules these mechanisms feed.
- [`jar-research.md`](jar-research.md#exposed) — how the exposer dump is taken and what the exposure test does not cover.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#eat) — the order of writes inside `Eat`, which the eat hook sits in.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#moodles) — what a moodle level does once it is set.
- [`../facts/other-mods/catalog.md`](../facts/other-mods/catalog.md#corpus-facts) — the full corpus event census behind the counts above.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the verdict rows cited from the walls.
- [`../reference/experiments.md`](../reference/experiments.md) — the named experiments the open rows point at.
