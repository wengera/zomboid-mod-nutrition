# Eat and cook hooks
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the nutrition-design reading of where a hook on the intake or cooking path sits — which side its writes survive on, which seat in the order of writes it takes, what it can still change and which wall it meets; how each hook resolves and which side calls it are `platform/lua-platform.md`'s, the order of writes and the drink path `facts/eating-pipeline.md`'s, and the cook block, the craft split and the evolved dish `facts/cooking-and-recipes.md`'s.

## Rules
<a id="rules"></a>

- Run the mod's intake math where the eat completes: a multiplayer client never reaches the eat action's completion step, so nothing a mod hangs off the client side of that path ever runs [#0109, #0110].
- Name a script hook's target as a global function or a function one level inside a global table, never a local or a deeper path: the eat path resolves the script's name through the Lua manager's function-object lookup, which walks a dotted name through global tables and never finds a local, and the cook path looks a dotted name up exactly two levels, so a bare global or a one-level table member resolves on every path and a deeper path resolves only on the eat path [#3501/C/C-only, #3502/C/C-only].
- Define that global in a `shared/` file and branch on the side inside it: the folder decides nothing, and the eat hook fires on both sides [#0922/M/n=1, #1031/M/n=1].
- Nil-check `isServer` and `isClient` before the protected call that reads them: a protected call on a nil comes back as a failure that names nothing, which turns absence into an error string instead of a branch [#0937/M/n=1].
- Keep every write an `OnEat` handler makes on its server arm: the client arm is the packet twin's notification, and the store it would write belongs to the server [#1131/M/n=1, #2061/C/inference].
- Sit in a server-side wrapper of the eat action's completion when the mod needs the item before `Eat` touches it: the wrapper must hold its sentinel outside any table the shared file re-creates, guard on a nil-checked `isServer()` because the mod's `server/` file also runs in the client VM, and call the original unless it means to skip `Eat` entirely [#1190/M/n=1, #1033/M/n=1].
- Hold a wrapper's sentinel in a global of its own: the shared file re-creates its state table by plain assignment on every load, so a sentinel kept inside it is wiped while the old wrapper is still installed and the next install wraps the wrapper [#0943/C/C-only].
- Monkey-patch idempotently and keep the original, testing for your own wrapper before you replace the target: that shape is safe under a Lua reload, unwindable, and it composes when two mods wrap the same function [#1067/C/snapshot].
- Expect a later mod's non-chaining replacement of a method you wrapped to remove your capture silently: a replaced function value drops the earlier closure, no sentinel can see it, and only your own per-eat counters standing still reveal it — so a wrapper keeps a call counter and the next boot beside a new eat-wrapping mod reads it [#2842/C/inference, #1067/C/snapshot, #2562/C/snapshot, #2817/C/C-only].
- Never put mod logic in a client-side wrapper of a timed action's completion: the Lua complete is skipped on a client, so the wrapper installs and then stays silent [#2005/C/C-only].
- Write an `OnEat` correction as a delta on the store the eat has already filled, never as a second intake: the hook fires after every stat and nutrient write, so vanilla's numbers are already in [#0008, #2062/C/inference].
- Expect an eat-hook correction to reach the client one push late: the server's eat packet has already left when the hook runs, so the correction rides the next once-a-second player-stats push [#0006, #0114, #2063/C/inference].
- Never count on the completion wrapper to see a cancelled eat: a cancel reaches `Eat` through the net action's stop and the eat action's server-stop step, which does not pass through the completion step [#0111, #2064/C/inference].
- Expect no eat-side seat to see a drink from a fluid container: the fluid path has no eat hook and no eat packet, and a container drink from the drink action reaches a mod through a server-side wrapper of the action's `updateEat`, which a direct `DrinkFluid` call and the world-water route bypass [#0084/C/C-only, #1133/M/n=1, #2690/C/C-only, #2827/M/n=1, #2828/C/inference].
- Branch on the side inside a cook hook as inside an eat hook: the cook dispatch is not side-gated, so a client copy that reaches the cook transition makes the same call in the client's state [#1394/C/C-only, #2066/C/inference].
- Write a `ReplaceOnCooked` item's cooked nutrition into the replacement's script, never into a cook hook on the item it replaces: the cook block swaps the item and returns before it sets the cooked flag or calls the hook [#0266, #0257, #2067/C/inference].
- Put item data in scripts and reach for a Lua field write only when the field is in `ItemStatsPacket` or the value may stay server-only: a script value is identical on both sides for free, while a Lua write to a live item never leaves the server [#1074/M/n=1].
- Scale an eaten item's mod nutrients to the calories `Eat` delivered: the item's `getCalories()` read before the eat times `Eat`'s own fraction, over the table's calories, and fall back to the hunger ratio against the script only when the table's or the item's calories are zero or absent, because fish, cut fish, small-animal cuts and foraged wild food scale their macros and their hunger by independent factors while a partial eat scales calories and `hungChange` together [#3326/C/C-only, #3329/C/arith., #3330/C/C-only, #3331/C/C-only, #3332/C/C-only, #3333/C/C-only, #3340/C/inference].

## How it works

This page owns no mechanism and no number: it reads the hook dispatch of the Lua platform page against the order of writes on the eating page and the cook block on the cooking page, and asks where a nutrition mod's correction can sit.
Four sites sit on the eat and cook paths — the eat hook, a server-side wrapper of the eat action's completion, the cook hook and the item-block creation hook — three more carry a drink, a craft and an evolved dish, and [the options table](#hook-options) sets them side by side.
Three readings decide between them: which side a hook's writes survive on, which seat in the order of writes it takes, and where the cook hook sits against a type change.

<a id="side-choice"></a>
### Which side a hook must sit on

The side is settled before any hook is chosen, because the server owns every store an eat writes.
The eat completes on the server: the client's timed action hands the server a net action, and the server drives it into the eat action's completion and on into the eat call ([#0110], [mp-model.md#ownership](../platform/mp-model.md#ownership)).
A multiplayer client never reaches that completion step at all [#0109].
A client-side write to hunger, thirst, calories or the macros is erased by the next player-stats push, so each of those stores has one owner, the server ([#0568/M/n=2], [mp-model.md#routes-client-to-server](../platform/mp-model.md#routes-client-to-server)).
A mod can therefore run its intake math where the eat runs, on the server, and a number any hook writes into those stores on the client does not outlive the next push [#1128/M/n=1, #0568/M/n=2].

Which side calls each of the four hooks is the Lua platform page's reading, and the design needs only its consequence ([lua-platform.md#script-hooks](../platform/lua-platform.md#script-hooks)).
The eat hook runs on both sides, and its client arm is a notification rather than a second intake [#2004/C/C-only].
One handler therefore cannot fire once in multiplayer, and a client-side wrapper of the completion cannot run at all, which makes both a wall rather than a choice [#1131/M/n=1].
The eat packet goes through the player-addressed send, which reaches the eater's own connection only, so the client arm fires on the eater's own client and on no other ([#0130], [#2603/C/C-only], [mp-model.md#sync-globals](../platform/mp-model.md#sync-globals)).
The completion wrapper installed from a `server/` file acts on the server only, and it installs on the client too, where it stays silent [#0928/M/n=1].
Where the wrapper installs is the platform page's reading, and why its sentinel lives in a global of its own is the rule above ([lua-platform.md#script-hooks](../platform/lua-platform.md#script-hooks), [lua-platform.md#dev-loop](../platform/lua-platform.md#dev-loop)).
Two lessons rules fix a wrapper's install and re-wrap discipline ([#2844/C/inference], [#2845/C/inference], [lessons.md#rules](../platform/lessons.md#rules)).
The completion already carries a corpus mod's sentinel-free save-and-replace on the server, so a wrapper beside it must call the saved original on every path that does not mean to skip the eat, which is [the idempotent-patch rule](../platform/lessons.md#rules) applied to this seat [#2562/C/snapshot] [#2566/C/snapshot] [#1067/C/snapshot].
The cook hook is reached only by the side that runs the cook transition, which on the measured path is the server [#0925/M/n=1].
The creation hook runs on whichever side instantiates the item, read from the bytecode and never fired [#0926/C/C-only].

No file's folder decides any of this.
A mod's `server/` Lua runs in the multiplayer client's state as well as the server's, so a hook's side is a branch inside the hook rather than a place in the tree ([#0854/M/n=1], [overview.md#two-lua-states](../platform/overview.md#two-lua-states)).
That branch is a side test that is itself nil-checked, for the reason [the dialect's limits](../platform/lua-platform.md#kahlua-limits) give [#0937/M/n=1].
A cook hook needs the branch as much as an eat hook does: the cook dispatch is not side-gated, so a client copy that did reach the cook transition would make the call in the client's state, and no session has reached that state [#1394/C/C-only].

A client arm is read-only in effect, and it is not useless.
It reads the same post-intake numbers the server's arm reads, because the eat packet's parse has loaded the server's store into the client before the twin fires the hook ([#1034/M/n=1], [#0116], [wire-packets.md#eat-food-packet](../facts/wire-packets.md#eat-food-packet)).
It can drive a display or a prediction from that mirror.
Keeping the mod's own fields there breaks the server-arm rule, and the cost is drift rather than loss: the player-stats push, by its field list, never overwrites those fields, and they drift from the vanilla numbers the server keeps recomputing [#0129/M/n=1].
It cannot change what an eat delivers, because the packet's handlers apply no numbers of their own [#0116].
It cannot push an item field to the server either, because every arm of the item-stats send runs from server to client [#1150/C/C-only].
A mod that needs the client's input on an intake therefore sends it over the command bus and lets the server's arm act on it ([#0932], [mp-model.md#command-bus](../platform/mp-model.md#command-bus)).

A consumable spawned on the client is a mistake whatever its creation hook does: an eat of a client-spawned food ends in a sync error on the server ([#0124/M/n=1], [mp-model.md#packets](../platform/mp-model.md#packets)).
Whatever a creation hook or a cook hook writes into an item field reaches the other side only if the item-stats packet carries that field ([#1036], [wire-packets.md#item-stats-packet](../facts/wire-packets.md#item-stats-packet)).

For every hook on this page the side reading comes to one sentence: the numbers go on the server arm, and the client arm, where one exists, reads.

<a id="seat-in-the-order"></a>
### Which seat sees which values

The eat path writes in one fixed order, and the order block on the eating page places every seat in it ([#0006], [eating-pipeline.md#eat](../facts/eating-pipeline.md#eat)).
The block is cited here by its tag and never carried; what follows is where each seat falls in it.

The completion wrapper, ahead of its call of the original, is the one seat that sees pre-intake values: the store as it stood before the eat, and the item before `Eat` reads or changes it ([#1033/M/n=1], [#1129/M/n=1]).
Whatever it writes into the item or the store before that call is what `Eat` then reads, a reading of the order that no session has exercised [#0006, #1129/M/n=1].
It cannot stop the eat except by not calling the original, which skips the whole eat rather than any part of it [#1129/M/n=1].
The share the eat will actually take is not yet known there, because the rescale of the menu's share of the whole item into a share of what is left happens inside `Eat` ([#0014/M/one-fixture], [eating-pipeline.md#modifiers](../facts/eating-pipeline.md#modifiers)).
A wrapper that needs that share has to reproduce the rescale, and the same arithmetic is already duplicated in Lua twice, so a wrapper's copy is one more site to keep in step, and the rule that copy follows is the two fractions, a live-read quantity scaled by the share of what is left and a whole-instance quantity by the share of the whole ([#0082], [#2843/C/inference], [eating-pipeline.md#partial](../facts/eating-pipeline.md#partial), [lessons.md#rules](../platform/lessons.md#rules)).

Between the wrapper and the eat hook there is no Lua seat at all.
The stats, the nutrients, the pain and cold reductions, the sickness cure, the mood writes and the server's packet sends all land with no hook between them, the eat hook being the only vanilla hook on the intake path [#0006, #0130].

The eat hook is the post-intake seat: when it fires every stat and every nutrient has been written and the item has not yet been consumed ([#0008], [#0093]).
The item it is handed is therefore still the one the eat read, and the store already holds the eat [#0008].
A correction written there is a second write on top of vanilla's and never a replacement of it [#1130/M/n=1].
What it reads off that item depends on the getter: the state-modified pair gives what the player received and the raw pair what the item still stores ([#0102/M/one-fixture], [eating-pipeline.md#getters](../facts/eating-pipeline.md#getters)).
A correction that recomputes an eat from the item's own macros has to apply the burnt divisor the eat applied, the one nutrition modifier in the game, or it overstates a burnt item ([#0019/M/one-fixture], [#0036/M/one-fixture]).
A utensil changes nothing a seat corrects, because its flag reaches only the mood and sickness call inside `Eat` [#0009].
The eat hook fires for any character that eats, while the nutrient block is skipped for one that is not a player and the nutrition object is declared on the player class alone, so a nutrient correction tests for a player first ([#0006], [#0020], [#0897/C/C-only]).
It is handed the rescaled share rather than the menu fraction, which is the number a proportional correction wants [#0093].
Its return value is ignored, so it cannot veto or shorten the eat it reports [#0093].
It can still reach the leftover: a mutation of the item's remaining hunger or calories is what the leftover scaling then multiplies, read off the order of the two calls and never measured [#0094/C/inference].
The eat hook can therefore change what is left of the item and correct the store after the fact, and it cannot change what the eat itself delivered.
The server's packet sends have already left when it fires, so a correction written there reaches the client on the next once-a-second player-stats push rather than in the eat packet ([#0006], [#0114], [wire-packets.md#player-stats-packet](../facts/wire-packets.md#player-stats-packet)).
The eat packet carries the whole nutrition store the eat wrote, so a nutrition write made in the wrapper ahead of the original rides that packet with the eat itself, while a post-intake write waits for the push ([#0113], [#0114]).
Every post-intake seat also sees the stores after their clamps have discarded any overshoot, so the part of an eat a clamp threw away shows only against a pre-intake reading, which the wrapper is the one seat to take ([#0021/M/one-fixture], [#0022/M/n=2], [#0023/M/n=2], [nutrition-core.md#clamps](../facts/nutrition-core.md#clamps)).

A wrapper that calls the original and then acts again takes a third seat, later than the eat hook.
There the stores are written, the eat hook has run and the item has been consumed or scaled down and synced, all on the server, the only side the wrapper acts on [#0006, #1032/M/n=1].
It is a post-intake seat like the eat hook, with the same push of lag for anything it writes.
Where a mod uses both the wrapper and the eat hook, the server runs them in that order and the client runs the eat hook alone [#1033/M/n=1].
The client's eat-hook call is later still, after the eat packet has replaced the client's store, and it reads the post-intake values the server's arm read [#1034/M/n=1].

So one seat sees pre-intake values — the wrapper ahead of its call of the original — and every other seat sees post-intake ones.
A correction that must change what an eat delivers can only sit in the wrapper; one that may correct afterwards can sit in the eat hook or behind the original, and pays a second write and a push of lag.

A partial eat reaches the same seats: the menu offers fractions below a whole item, and the eat hook receives the rescaled share of each ([#0078], [#0093]).
The eat hook fires once per portion, not once per eat: four completed quarter eats of one item fired it four times on each side and a whole eat once more, each call handed `Eat`'s rescaled fraction of what was left [#0929/M/n=1, #2830/M/n=1].
A wrapper that reads the item after calling the original sees the drop of that portion, but a finishing eat divides 0 by 0 in the consume step by the jar's reading, so a share computed from the raw hunger after the eat reads NaN, not 1 [#2832/M/n=1].

A cancelled eat is a different route into the same method.
It resolves on the server through the net action's stop and the eat action's server-stop step, whose fraction is the net action's progress ([#0111], [mp-model.md#ownership](../platform/mp-model.md#ownership)).
The eat hook on a cancelled eat is therefore handed a share derived from how far the action ran, rescaled like any other [#0111, #0093].
That route never passes through the completion step, so a completion wrapper does not see a cancel, while the eat hook, which fires inside `Eat`, sits on both routes [#0111, #0006].
A mod can handle a partial or cancelled eat on that server-side route [#1132/C/C-only].
Two guards on the server-stop step make a cancelled eat apply nothing at all — no stats, no nutrition, no leftover scaling and no consumption — for one named item and for any item whose state-modified hunger change sits at or under the magnitude the guard tests [#0112].
Under either guard no eat-side seat fires, because `Eat` is never called, and whether the guard really applies nothing is [open](#open): the harness's stop never cancelled a started eat, so no live cancel has reached the server-stop step [#0112, #1299/C/open, #2834/M/n=2].

A drink from a fluid container sits outside all of these seats.
`DrinkFluid` has no eat hook, no eat packet and no fraction rescale ([#0084/C/C-only], [eating-pipeline.md#fluid-path](../facts/eating-pipeline.md#fluid-path)).
Its action calls it incrementally from the update and the animation event rather than from a completion step [#0085/C/C-only].
The action's one call sits in its `updateEat`, which the completion reaches as well, so that method is the seat a drink wrapper takes, and a wrapper there sees each sip once ([#2689/C/C-only], [eating-pipeline.md#fluid-path](../facts/eating-pipeline.md#fluid-path)).
That seat is measured once on a live server: a wrapper there fired on the server and the client's counters stayed at 0, its install there not witnessed, and a second save-and-call-original wrapper stacked on the same method counted every call the first counted and landed the drink in its own store ([#2825/M/n=1], [#2826/M/n=1]).
A drink straight from a world water source goes through a second action, with its own call on a temporary container, which a wrapper of the drink action never sees [#2690/C/C-only].
The called method's body holds no Lua call, so a wrapper of one of those two actions is the only Lua seat on either route [#2687/C/C-only] [#0084/C/C-only].
No live version folder in the corpus names `updateEat`, so a drink wrapper there has no other wrap to chain onto, a reading of one sweep of a corpus that drifts [#2567/C/snapshot].
Drinking completes on the server and sends only the player-stats sync, so a drink's calories reach a client only on the once-a-second push [#0649].
A food item that carries a thirst change and the drink menu option is another matter: it goes through `Eat` like solid food, and every seat above applies to it [#0083/M/one-fixture].

The sandbox nutrition switch gates the update tick and never the intake, so no seat above moves when a server turns vanilla nutrition off ([#0067], [eating-pipeline.md#sandbox](../facts/eating-pipeline.md#sandbox)).

<a id="cook-seat"></a>
### Where a cooking-side hook sits

Cooking has one hook of its own, and it sits on a different path from the eat seats: inside the item's own update, on the transition to cooked, rather than inside an action a player queues ([#0257], [cooking-and-recipes.md#cook-block](../facts/cooking-and-recipes.md#cook-block)).
The cook block that places it is cited by its tag and never carried here.
The hook fires on that transition, after the block has set the cooked flag and made its own clean-ups of the item's mood and age fields, and before the block's microwave penalty ([#0257], [#0045], [#0268]).
A hook that writes the mood fields of an item that is bad in a microwave and was cooked in one is therefore followed by the block's own penalty on those fields [#0269].
The transition is entered only while the item is neither cooked nor burnt, so the hook does not fire again on an item it has already cooked, and a multiplying rewrite there does not compound on that side [#0257].

The transition itself moves no stored nutrition: cooking and burning leave an item's calories and raw hunger untouched, and only the read-time hunger ladder moves ([#0277/M/n=1], [cooking-and-recipes.md#type-change](../facts/cooking-and-recipes.md#type-change)).
Cooking as such moves no calories anywhere in the recipe data either [#0742/C/snapshot].
A mod that wants cooking to change what an item delivers therefore has two places to say it: the cook hook, rewriting the instance at the transition, or a script that turns the item into a different one when it cooks.
A mod can rewrite a crafted instance from the cook hook, whose registration and firing are read rather than driven end to end [#1154/M/n=1].
One corpus mod's server-side cook hook does exactly that at the transition, printing in the server console ([#1208/M/n=1], [the teardown](../facts/other-mods/longtermpreservation.md#architecture)).
What the client then learns is the packet's field list: the calories, the proteins, the lipids and the raw hunger field that hook scales arrive intact, while the age-window bounds and the cookable flag never arrive ([#1105/M/n=1], [#1037/M/n=1], [wire-packets.md#desyncs](../facts/wire-packets.md#desyncs)).
The carbohydrates are in that packet by a read of its fields rather than by measurement, because the measured item carries zero carbohydrates on both sides of the rewrite [#1105/M/n=1].
A cook hook can therefore change a cooked item's nutrition on both sides, and anything else it writes has to be a field the packet carries or a value the design leaves on the server [#1074/M/n=1].

A type change is the one thing the cook transition itself does to nutrition, and it happens ahead of the hook rather than under it.
An item with a `ReplaceOnCooked` link that is not rotten is swapped for the named item on the transition, and the block returns before it sets the cooked flag and before it calls the hook, so the original's cook hook never runs for that transition ([#0266], [#0257]).
A rotten item carrying the link is not swapped, and takes the ordinary path through the cooked flag and the hook [#0266].
What the player gets from a swap is the replacement's own script values, and none of vanilla's three `ReplaceOnCooked` links moves a macro [#0752/C/arith.].
A mod that wants a cooked replacement to carry different nutrition says so in the replacement's script, which both sides load without a packet ([#1058/M/n=2], [loader-and-scripts.md#per-side-load](../platform/loader-and-scripts.md#per-side-load)).
The transition, and every such swap with it, is driven by server-owned state ([#0758], [mp-model.md#ownership](../platform/mp-model.md#ownership)).
The measured transition ran on the server, with the hook's prints in the server console and the client's console empty [#1417/M/n=1].

The cook hook resolves its name by a different route from the eat hook: a dotted name is looked up there exactly two levels, a global table's own member, while the eat hook's lookup walks a dotted name through global tables to any depth ([#3502/C/C-only, #3501/C/C-only], [lua-platform.md#script-hooks](../platform/lua-platform.md#script-hooks)).
No session has fired a dotted cook-hook name, so that half of the dispatch is a bytecode reading [#3502/C/C-only].

The cook hook changes what an item is after it cooks and never when it cooks.
The heat gate, the once-a-minute tick and the evolved recipe's perk scaling are all Java, with no hook in them [#1155/M/n=1].
Per-item cook times are the script's to set instead [#1156/M/n=1].
Spice behaviour is a script bool rather than a hook, routing an ingredient down the evolved summation's spice branch [#1157/C/C-only].
What that branch does beyond the herbal-tea sums is unread, and it is [open](#open) [#0381/C/C-only/open].

Crafting is the other way an item's nutrition changes, and it has no seat this library has fired.
Nothing on the command bus executes a craft, so a recipe's creation and test hooks and the item-block creation hook stay bytecode readings ([#1248/C/C-only], [harness.md#walls](../platform/harness.md#walls)).
A set of output-less recipes mutate an input through a creation hook instead of yielding an item, and what those hooks do to nutrition is unread ([#0686/C/snapshot], [#0784/C/snapshot/open]).
A craft recipe's own creation hook is handed the recipe data and the character only after the outputs exist, inside a stop that returns at once on a client, and a client cannot create craft outputs for real at all, so by the code that hook is a server seat ([#2665/C/C-only], [#2664/C/C-only], [#2667/C/C-only], [cooking-and-recipes.md#craft-split](../facts/cooking-and-recipes.md#craft-split)).
It reads the consumed instances and writes onto the created ones through the recipe data, and it is the one place a mod value crosses a craft, because no vanilla craft arm copies an input's modData to an output ([#2666/C/C-only], [#2660/C/C-only]).
The evolved summation has no Lua seat inside it: the timed action's call of the recipe's add-item method is the only bridge from Lua into it ([#0325], [cooking-and-recipes.md#evolved](../facts/cooking-and-recipes.md#evolved)).
The summation calls no Lua and fires no event, and a server-side wrapper of the add-item action's completion holds the ingredient instance, the base and the chef before its call of the original and the finished dish after it [#2657/C/C-only, #2658/C/C-only].
The dish keeps a list of its ingredients' full types, one entry per add and none for a spice, with no amount and no hunger share beside them, so a reader at eat time rebuilds only a nominal share per type ([#2650/C/C-only], [#2652/C/C-only], [#2653/C/C-only]).
A dish also starts from its result type's default modData, so nothing the mod wrote on an ingredient reaches it unless that wrapper carries it across [#2656/C/C-only].
The Cooking level that scales it is the server's, whatever a client shows [#0759/M/n=1].
What a multiplayer server stores after a real add-item action has not been measured, the measured summation being a client-side reading [#0360/M/one-side].
A mod that drives the evolved path queues the vanilla add-item action rather than hooking the summation, and so inherits everything that action already guarantees, which is how the one corpus mod that automates it works ([#1354], [autocook.md#techniques](../facts/other-mods/autocook.md#techniques)).
That mod is also a downstream reader a nutrition mod must not starve: it ranks ingredients on the vanilla macros and the weight flags, and new mod nutrients are invisible to its diets ([#1377/C/snapshot], [autocook.md#compat](../facts/other-mods/autocook.md#compat)).

## Options

<a id="hook-options"></a>
### Hook sites

| option | what it costs | which wall it hits | tags |
|---|---|---|---|
| a `server/` wrapper of `ISEatFoodAction.complete` — acts on the server only, ahead of `Eat`, so it sees the store and the item before any intake and can still change what `Eat` then reads, or skip the eat whole | a sentinel held outside the shared table, a nil-checked side guard and the original called every time; its own copy of the fraction rescale if it needs the share the eat will take; it never sees a cancelled eat | cannot stop part of an eat, only skip the original; one eat at full fraction measured | [#1129/M/n=1, #1033/M/n=1] |
| `OnEat` — fires on both sides, the client arm a notification; runs after every stat and nutrient write and before the item is consumed, so it can correct the store after the fact and change the leftover, never the intake | a second write on top of vanilla's, a side branch inside the handler, and a correction that reaches the client one push late; it sits on both the completed and the cancelled route | cannot fire once in multiplayer, and its return value is ignored; it fires once per portion, not once per eat | [#1130/M/n=1, #1131/M/n=1, #2830/M/n=1] |
| `OnCooked` — reached by the side that runs the cook transition, the server on the measured path; fires after the cooked flag is set, so it can rewrite the cooked instance's nutrition | only the fields the item packet carries reach the client; a side branch inside, since the dispatch is not side-gated; a swapped item never reaches it | the pipeline has never been driven end to end, and the heat gate, the tick and the perk scaling around it are Java | [#1154/M/n=1, #1155/M/n=1] |
| `OnCreate` — runs once, at instantiation, on whichever side instantiates, so it can seed an item before anything reads it | a bare global like the eat hook's target; what it seeds into an item field crosses only as the item packet carries it | never fired in any session, and nothing on the bus executes a craft to reach it | [#0926/C/C-only, #0967/C/C-only/open] |
| a `server/` wrapper of `ISDrinkFluidAction:updateEat` — the drink action's one `DrinkFluid` call, which the update, the animation event and the completion all reach; sampling the container's litres and mix before calling through and its litres after sees each sip once | a sentinel and the original called every time; the mix sampled before the call, since the removal returns an aggregate with no per-fluid breakdown; a second wrap of `ISTakeWaterAction`, whose world-source drink calls `DrinkFluid` on a temporary container the drink action never sees | it fires on the server only and misses a direct `DrinkFluid` call, one session measured, and `DrinkFluid` itself calls no Lua and touches no modData | [#2689/C/C-only, #0085/C/C-only, #2690/C/C-only, #2688/C/C-only, #2687/C/C-only, #1133/M/n=1, #2827/M/n=1] |
| a craft recipe's `OnCreate` — handed the recipe data and the character after the outputs exist, on the server only by the code, so it can read the consumed instances and write the mod's own keys onto the created ones | a mod value crosses a craft only where this hook writes it, since no vanilla craft arm copies an input's modData; the hand-craft action writes its own consumed-type map into a lone output's modData after the hook | never fired in any session, and nothing on the bus executes a craft | [#2665/C/C-only, #2666/C/C-only, #2667/C/C-only, #2660/C/C-only, #1248/C/C-only, #2664/C/C-only] |
| the evolved dish's ingredient list — `extraItems` keeps each ingredient's full type once per add and survives a save, so a reader at eat time can rebuild a nominal share per type from the recipe's `use` values | the join strips the module from each entry; the share is nominal, not what the chef's level, the ingredient's remaining hunger and the clamp produced; spices sit in a separate list; anything per ingredient beyond its type is written by a server-side wrapper of the add-item completion, the one place holding the ingredient and the dish side by side | no amount and no hunger per ingredient, no Lua inside the summation, and the dish carries none of its ingredients' modData | [#2650/C/C-only, #2653/C/C-only, #2654/C/C-only, #2673/C/C-only, #2658/C/C-only, #2656/C/C-only, #2652/C/C-only] |

Which seat carries the mod's intake correction and which carries its cooking rewrite, given that only the wrapper sees pre-intake values, only the eat hook sits on both the completed and the cancelled route, and only the cook hook sits on the cook transition?
Which seat carries a drink, a craft and a dish, given that a drink reaches the mod only through a wrapper of one of two actions, a craft only through the recipe's own creation hook, and a dish's ingredients only as types or through the add-item wrapper?

## Walls and bounds
<a id="walls"></a>

- The drink path's one intake seat is a server-side wrapper of the drink action, measured in one session: the fluid path has no eat-hook twin, the wrapper fires on the server and the client's counters stayed at 0, and it misses a direct `DrinkFluid` call ([#1133/M/n=1], [#1279/M/n=1], [#2827/M/n=1]).
- A drink-action wrapper never sees a drink from a world water source: that drink goes through `ISTakeWaterAction` and its own `DrinkFluid` call on a temporary container [#2690/C/C-only].
- No client arm fires for another player's eat: the eat packet goes through the player-addressed send, which reaches the eater's own connection only [#2603/C/C-only].
- No vanilla hook runs ahead of the eat's writes: the eat hook is the only hook on the intake path and fires after them, so pre-intake work needs the completion wrapper, a workaround rather than a hook ([#0130], [#1129/M/n=1]).
- No eat hook fires once in multiplayer and no client-side completion wrapper runs: the hook fires on both sides and a client skips the Lua completion ([#1131/M/n=1], [lua-platform.md#script-hooks](../platform/lua-platform.md#script-hooks)).
- No seat vetoes part of an eat: the eat hook's return value is ignored, and the wrapper stops an eat only by skipping the original whole ([#0093], [#1129/M/n=1]).
- The declared named-hook roster carries no eat, drink, consume, digest or nutrition hook, and the one named hook near intake that replaces vanilla work is the stat tick's, which is all or nothing and not an intake seat ([#1133/M/n=1], [#2238/C/C-only], [lua-platform.md#hooks](../platform/lua-platform.md#hooks)).
- No hook on the drink side is an intake seat: the named auto-drink hook fires on the thirst-relief path and not on intake ([#0482/C/C-only], [#1133/M/n=1], [lua-platform.md#hooks](../platform/lua-platform.md#hooks)).
- No hook reaches the cook block's gates and timers or the evolved summation's perk scaling, all of which are Java [#1155/M/n=1].
- No hook runs inside the evolved summation and no vanilla craft arm carries modData from an input to an output, so a dish or a craft output carries a mod value only where the mod writes it ([#2657/C/C-only], [#2656/C/C-only], [#2660/C/C-only], [cooking-and-recipes.md#walls](../facts/cooking-and-recipes.md#walls)).
- No cook hook runs on a swapped item's transition, because the swap returns before the hook ([#0266], [cooking-and-recipes.md#cook-block](../facts/cooking-and-recipes.md#cook-block)).
- The cooking pipeline has never been driven end to end: the cook hook's registration and firing are read, the measured side is one mod's single transition per session, and nothing on the bus executes a craft ([#1154/M/n=1], [#0925/M/n=1], [#1248/C/C-only]).
- The eat-hook and wrapper readings on this page are single sessions on the dedicated-server path: one whole eat in one, four quarter eats and four whole eats of one fixture in another ([#1031/M/n=1], [#1033/M/n=1], [#2830/M/n=1]).
- Two save-and-replace wrappers of the eat completion can form a call cycle that blocks every eat: a wrapper that re-installs itself at a later boot event over a later-loading wrapper, while its first closure calls its saved original through a global the re-install overwrote, recursed on every completed eat until it overflowed the stack, so no eat ran in eight of eight [#2835/M/n=1].
- A non-finite number an intake wrapper lands is not stopped by the stat clamp: a NaN share from a finishing eat, carried into a hunger stat written from the wrapper's store, read as non-finite on both sides [#2833/M/n=1].
- Single player is never claimed here: there a cancelled eat action calls its own server-stop step, and the server arm and the client arm are one process ([#0103], [mp-model.md#ownership](../platform/mp-model.md#ownership)).

Not covered: the thirst-relief path beyond its named hook, the context-menu and crafting timed actions that lead into cooking, hooks a third-party framework layers over these sites, animal feeding beyond the eat call's player guard, and single player — none of them was read for a hook seat.

## Open
<a id="open"></a>

- Whether a dotted cook-hook name fires, on which side, and whether the cooking pipeline can be driven end to end — settled by a cook-transition session with a dotted target and by a harness craft command that reaches a crafted instance; it decides whether cook-side code may live in a table and whether any cooking-side seat is more than a reading; -> X31 ([#1297/C/open], [open-questions.md#x31](open-questions.md#x31)).
- Whether the item-block creation hook fires as the bytecode reads, and what it can seed at instantiation — settled by the same craft session with the hook registered; it decides whether per-item nutrient values are seeded at instantiation or read from the script on demand; -> X31 ([#0967/C/C-only/open], [lua-platform.md#open](../platform/lua-platform.md#open), [open-questions.md#x31](open-questions.md#x31)).
- What the creation hooks of the output-less recipes do to nutrition — settled by executing one of them on the game's own craft path; it decides whether those recipes need a nutrition delta of their own; -> X31 ([#0784/C/snapshot/open], [cooking-and-recipes.md#open](../facts/cooking-and-recipes.md#open), [open-questions.md#x31](open-questions.md#x31)).
- Whether a cancelled eat of an item under the server-stop guard really applies nothing at all — settled by cancelling such an eat partway with store and stat reads on both sides, through a client command that stops a started action, since the harness's stop clears only actions not yet started; it decides whether a correction ever needs the cancel route for those items, and whether an item pass may land a hunger value under the guard; -> X33 ([#1299/C/open], [#2834/M/n=2], [open-questions.md#x33](open-questions.md#x33)).
- What the spice branch does beyond the herbal-tea sums — settled by a desk read of the spice method and the ingredient usability check; it decides whether spice stays a script bool or needs a cooking-side seat; -> X9b ([#0381/C/C-only/open], [#1278/C/open], [open-questions.md#x9b](open-questions.md#x9b)).
- Decision: whether the intake correction sits in the completion wrapper, before `Eat` writes, or in the eat hook, after it — only the wrapper sees pre-intake values, while the eat hook's store already holds the eat ([#1033/M/n=1], [#0008]).
- Decision: whether the correction must also cover a cancelled eat — a cancel reaches `Eat` through the server-stop step and never through the completion step [#0111].
- Decision: whether a cooked item's nutrition comes from a cook hook on the instance or from a replacement item's script — the swap returns before the hook runs, and a hook's item-field writes reach the client only where the item packet carries them ([#0266], [#1036]).
- Decision: whether the intake correction also wraps the world-source drink action — a drink-action wrapper never sees a drink from a world water source [#2690/C/C-only].

## See also

- [`../platform/lua-platform.md`](../platform/lua-platform.md#script-hooks) — how each hook resolves its name and which side calls it, the dispatch this page cites and never restates.
- [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md#eat) — the order of writes that places every eat-side seat, with partial eating and the drink path beside it.
- [`../facts/cooking-and-recipes.md`](../facts/cooking-and-recipes.md#cook-block) — the cook block that places the cook hook, and what a type change moves.
- [`../platform/mp-model.md`](../platform/mp-model.md#ownership) — who owns the stores, and where a completed and a cancelled eat resolve.
- [`../facts/wire-packets.md`](../facts/wire-packets.md#item-stats-packet) — the item fields a hook's writes can reach the other side through.
- [`../facts/other-mods/longtermpreservation.md`](../facts/other-mods/longtermpreservation.md#architecture) — the worked cook hook, and what its writes did on each side.
- [`../facts/other-mods/autocook.md`](../facts/other-mods/autocook.md#techniques) — a mod that drives the evolved-recipe path through vanilla's own action.
- [`mp-sync.md`](mp-sync.md) — where the mod's corrected numbers travel once a seat has written them.
- [`item-pass.md`](item-pass.md) — the script route a replacement item's nutrition takes, and the hunger values the cancel guard tests.
- [`open-questions.md`](open-questions.md) — the experiments behind the open lines.
- [`../reference/wall-map.md`](../reference/wall-map.md) — the eat-hook and cooking-pipeline verdicts cited above.
