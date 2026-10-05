---
name: nutrition-eat-and-cook-hooks
description: Hooking eating, drinking or cooking — an `OnEat`, `OnCooked` or `OnCreate` script hook as a bare global in a `shared/` file, a server-side wrapper of `ISEatFoodAction.complete` that runs before `Eat`, `isServer` and `isClient` side branches, an intake correction written after the eat, a cancelled eat, `DrinkFluid` and fluid containers, a drink wrap of `ISDrinkFluidAction:updateEat` beside `ISTakeWaterAction`, a craft recipe's `OnCreate`, an evolved dish's `extraItems` ingredient list, a `ReplaceOnCooked` item, the order of writes in the eat, and what a hook's writes can reach the client through.
---
## Read first
- docs/areas/eat-and-cook-hooks.md
- docs/platform/lua-platform.md
- docs/facts/eating-pipeline.md

## Rules quoted
- Run the mod's intake math where the eat completes: a multiplayer client never reaches the eat action's completion step, so nothing a mod hangs off the client side of that path ever runs [#0109, #0110].
- Name a script hook's target as a bare global function: the eat path resolves the script's name through the Lua manager's function-object lookup, which never finds a local or a table member [#0921/C/C-only].
- Define that global in a `shared/` file and branch on the side inside it: the folder decides nothing, and the eat hook fires on both sides [#0922/M/n=1, #1031/M/n=1].
- Sit in a server-side wrapper of the eat action's completion when the mod needs the item before `Eat` touches it: the wrapper must hold its sentinel outside any table the shared file re-creates, guard on a nil-checked `isServer()` because the mod's `server/` file also runs in the client VM, and call the original unless it means to skip `Eat` entirely [#1190/M/n=1, #1033/M/n=1].
- Monkey-patch idempotently and keep the original, testing for your own wrapper before you replace the target: that shape is safe under a Lua reload, unwindable, and it composes when two mods wrap the same function [#1067/C/snapshot].
- Never put mod logic in a client-side wrapper of a timed action's completion: the Lua complete is skipped on a client, so the wrapper installs and then stays silent [#2005/C/C-only].
- Write an `OnEat` correction as a delta on the store the eat has already filled, never as a second intake: the hook fires after every stat and nutrient write, so vanilla's numbers are already in [#0008, #2062/C/inference].
- Expect no eat-side seat to see a drink from a fluid container: the fluid path has no eat hook and no eat packet, so a container drink reaches the mod only through a server-side wrapper of the drink action's `updateEat` [#0084/C/C-only, #1133/M/n=1, #2828/C/inference].
- Write a `ReplaceOnCooked` item's cooked nutrition into the replacement's script, never into a cook hook on the item it replaces: the cook block swaps the item and returns before it sets the cooked flag or calls the hook [#0266, #0257, #2067/C/inference].

## Also
- docs/facts/cooking-and-recipes.md#cook-block — the cook block that places the cook hook, and what a type change moves.
- docs/areas/mp-sync.md — where the corrected numbers travel once a seat has written them (skill `nutrition-mp-sync`).
- docs/areas/item-pass.md — the script route a replacement item's nutrition takes (skill `nutrition-item-pass`).
