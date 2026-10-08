# Tooltiplib
Verified against 42.21.0 (4a0e9546ec) · 2026-10-08 · scope: how the TooltipLib tooltip framework hooks the inventory tooltip, the two guards it carries, its world-object server command, and how it composes with a mod that wraps the same render; the tooltip render chain and its walls are handed off to the client-UI page.

## Key facts
<a id="techniques"></a>

- Disable a failing tooltip contributor after a run of errors instead of calling it under `pcall` every frame forever [T1101.34].
- Guard a render wrapper against re-entry on its own call stack and fall back to a saved render, keeping the depth counter outside the protected body [T1101.35].
- Add rows inside vanilla's own tooltip box through a per-render `DoTooltip` swap and `DoTooltipEmbedded`: a C-only route that composes poorly with a framework that owns `DoTooltip` [T1101.33].

## How it works

<a id="what-it-does"></a>
### What it does

TooltipLib is a client framework through which mods add rows to item, crafting-slot, skill, vehicle, recipe and world-object tooltips.
Workshop item `3694097672` ships the mod id `TooltipLib`, modversion 1.7.0 by Dark Sauce, as a `42/mod.info` that sets `versionMin=42.15.0`, so Build 42.21 loads it; its Lua is 14 files, 13 under `client/` and one under `server/` [T1101.31].
It touches no player stat, no rate, no `ZomboidGlobals` field, no food item, no `Hook.CalculateStats` and no global modData [T1101.38].

<a id="architecture"></a>
### The render hook

At `OnGameStart` it replaces `ISToolTipInv.render` with a depth-guarded wrapper over the render it captured then, so a mod that wrapped the render at file load runs inside it [T1101.32].
With a provider active on the hovered item it swaps `DoTooltip` on the item's class metatable for the one render, calls the captured render under `pcall` and always restores the original afterwards, so its rows land inside vanilla's own layout through `DoTooltipEmbedded`; with no active provider and no panel dress it calls the captured render and returns [T1101.33].
When another framework's `DoTooltip` displaces its swap, it falls to a deferred mode that appends its rows below the foreign content from the previous frame's height and then sets the panel's height and width itself [T1101.36].
The in-box route answers the placement and background questions a band drawn below the box raises, at the price of mutating a shared class table on every render; it is recorded here as a route read off the code, not one this library has run ([#3244/M/n=2/open], [`../../platform/client-ui.md#tooltip`](../../platform/client-ui.md#tooltip)).

<a id="guards"></a>
### The two guards

It disables a provider for the session after 10 consecutive errors [T1101.34].
A render re-entered on its own call stack falls back to the render captured at boot instead of chaining again, and the depth counter is decremented after a `pcall`, so a body error cannot leave it raised [T1101.35].
Both are cheap to carry in any tooltip wrapper: the first bounds the cost of a contributor that keeps failing, the second bounds a wrap chain two mods have looped.

<a id="mp"></a>
### The world-object server command

Its server file answers a `readObject` client command by calling, on the object at the client's coordinates, any requested method whose name starts `get`, `has`, `is` or `check`, or the whitelisted `Activated`, and replies through `sendServerCommand` with no rate limit and no distance check; the sandbox option `TooltipLib.EnableMPSync`, default true, switches it off [T1101.37].
It does nothing until some mod registers a world-object provider that asks for server fields, and each request costs one `sendServerCommand` on the server's main thread ([#3437/C/C-only], [`../../platform/performance.md#budget`](../../platform/performance.md#budget)).

<a id="collisions"></a>
### How it composes

With this repository's tooltip, which wraps the same render at file load, TooltipLib is the outer wrapper and both draw; only a third framework owning `DoTooltip` while a TooltipLib food provider runs in deferred mode lets its appended rows and its height write overdraw the band below the box [T1101.39].

## Walls and bounds

Every line on this page is a reading of the installed 1.7.0 copy's code on 2026-10-08; the copy updated at 06:35 that day, after the neighbour report read 1.6.3, so its line cites were re-read here and drift again with the next update [T1101.37].

<a id="licence"></a>
### Licence

None of its 21 files carries a licence text, and its `mod.info` names the author only [T1101.40].
With no grant the default is all rights reserved, which leaves any other mod free to call its public API at runtime but not to copy its code.

Not covered: its skill, vehicle, recipe and world-object surfaces beyond a grep for writes; its Starlit and Eury adapters; its client cost per frame, which no run here measured; and the three-framework overlap, which is untested.

## Open
<a id="open"></a>

- Whether the engine honours the per-render metatable `DoTooltip` write on this build — settled by a hover synthesiser on a client with a TooltipLib provider active; no `X` id.

## See also

- [`../../platform/client-ui.md#tooltip`](../../platform/client-ui.md#tooltip) — the tooltip render chain and the band's open placement questions.
- [`catalog.md#api-surface`](catalog.md#api-surface) — the corpus's other tooltip wraps.
- [`catalog.md#status`](catalog.md#status) — the Workshop page reading and the code-read status of this and the other neighbours.
