# ItemQuality
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: how the ItemQuality crafting mod puts per-item mod values on crafted items, the hook and config shapes a nutrition mod lifts from it, and why the stat buffs it writes into live Java fields do not survive a dedicated server; the packet and modData mechanisms it fails against belong to the wire and model pages.

## Key facts
<a id="techniques"></a>

- Intercepting the add-or-drop function during a wrapped craft gives a clean per-output-item hook without touching Java [#1540/C/C-only].
- A salvage marker in an intermediate's modData carries stat continuity across a multi-recipe chain [#1540/C/C-only].
- A config-table-driven stat system with fields, per-point values and eligibility predicates is declarative and extensible [#1540/C/C-only].

## How it works

ItemQuality is a crafted-item quality system, and it is on this shelf for one reason: it is a per-item mod-value system running on a live dedicated server, which is the problem a nutrition mod has to solve for food.
Its creation hook and its config table are shapes to copy.
Its state model is a shape to copy only halfway, and the half that fails is the half a per-item nutrient would be most tempted to reuse.

<a id="what-it-does"></a>
### What it does

ItemQuality rolls a quality tier on eligible crafted weapons and clothing, applies point-bought stat buffs including a raised condition maximum, shows the tier in tooltips and preserves it through a dismantle and reforge using salvage markers [#1534/C/C-only].

Nothing on the engine side knows that a tier exists.
The tier is a mod value the mod itself stores and renders, and every buff the player feels is an ordinary item field that the mod has raised ([`#architecture`](#architecture)).

<a id="architecture"></a>
### Where its logic and its state live

ItemQuality is one of the mod ids inside workshop item `3624538051`, examined in `mods/ItemQuality/` with `42/` as its only version folder from files dated 2026-09-04, and the teardown of it rests on a code read plus a live bug investigation whose write-up lives in a separate repository and is therefore not checkable from a clone of this one [#1533/C/C-only].

ItemQuality's entry is a monkey-patch of the handcraft action's recipe method in its server tree which, during the wrapped call, replaces the add-or-drop function so every output item is intercepted at creation and then restores it [#1535/C/C-only].
The wrap is narrow in both the senses that matter: the patch is one Lua method, and the replaced add-or-drop function lives only for the duration of that call, so nothing outside a craft ever sees it.
That is why the hook costs the mod no Java contact at all ([`#techniques`](#techniques)).

ItemQuality rolls its tier from the average of the recipe's required skill levels with a carry-over chance from the consumed ingredients' tiers, stores salvage markers in the modData of non-eligible intermediates so a multi-step chain survives, keeps the tier, the modifiers, the crafter and a known condition in item modData, and restores non-persistent fields from that modData on equip and on player events [#1536/C/C-only].
Two stores are in play in that sentence, and the split between them is the whole of the mod's design.
Item modData holds what the mod owns, the live Java item fields hold what the mod has computed from it, and the reapply layer exists because the second store does not keep what is put in it.
That last point is a statement about the engine rather than about this mod, and it is what the multiplayer subsection is about ([`#mp`](#mp)).

<a id="mp"></a>
### What a dedicated server does to it

ItemQuality's root problem is that its buffs write Java item fields the engine does not serialise or sync: the item-field sync packet carries condition, head condition, sharpness and modData but not the condition maximum, and the condition setter clamps to the receiver's maximum, so a server copy on the script maximum clamps a buffed 18 down to 13 and echoes it back [#1537/C/C-only].
Which of the two item packets carries which fields, and what each of them does to the receiver, is not restated here ([#1119], [`../wire-packets.md#item-stats-packet`](../wire-packets.md#item-stats-packet)); nor is the one thing the mod's state has going for it, that item modData moves wholesale in either direction ([#1241/M/one-side], [`../../platform/mp-model.md#item-moddata`](../../platform/mp-model.md#item-moddata)).
Read against those rows the failure is not a bug in the mod at all: a value the packet has no field for cannot cross, and a value the receiver clamps cannot stay.

ItemQuality's mitigation is to mark the affected fields non-persistent and reapply them client-side on events, which works for fields only the client reads, such as damage and reach where combat resolves client-side, and fails for server-echoed fields such as condition; the durability case holds for headed weapons because the head condition maximum is a persisted attribute [#1538/C/C-only].
The line that mitigation draws is the useful part of this teardown.
A client-side reapply wins exactly where the server holds no competing value, and loses everywhere the server holds one and pushes it — which makes "does the server own a number for this field?" the question to ask of every per-item value a nutrition mod invents.

## Walls and bounds

Every line on this page is read from the installed mod's Lua and from an investigation held in another repository, and no run in the artifact tree evidences any of it.
The mod updates roughly daily, so each line is a reading of the files as they stood on the day they were read, and each of its code pointers was re-located by content rather than by line number before being carried here.

<a id="pitfalls"></a>
### Pitfalls

ItemQuality's salvage-restore path passes a preserve-condition flag into the apply function, which skips the refill, so a reforged weapon sits permanently at its script or buffed maximum, and the known-condition write runs unconditionally, poisoning the one-shot recovery guard so its known-greater-than-current test is never true [#1539/C/C-only].
Two independent defects meet in that one path: a flag that suppresses the repair, and a tracker that records the clamped value as if it were the intended one, after which the guard that would have repaired the item can never fire again.

Never store authoritative mod state in unsynced Java fields: modData is synced and saved, and live fields are a cache derived from it [#1541/C/C-only].
A reapply layer must be idempotent and continuous rather than one-shot, and a tracker must never overwrite the source of truth with a clamped observation; and on a dedicated server assume the server echoes item numerics, so test every stat with a relog and a second client before shipping [#1542/C/C-only].
The mechanism under both of those rules belongs to other pages — the item packet's field list and the wholesale movement of item modData — and neither is particular to this mod ([#1119], [#1241/M/one-side]).

<a id="compat"></a>
### Compatibility

ItemQuality is not a dependency for a nutrition mod: what it offers is two shapes, a config-driven stat table and a creation hook, that map directly onto per-item nutrient metadata on food ([`#techniques`](#techniques)).
Its collision surface is narrow and nameable — the handcraft recipe method it wraps and the item-modData keys it owns ([`#architecture`](#architecture)) — so another mod that wraps the same method, or that writes the same keys, is the only place the two would meet.
Its sync failures are the checklist a nutrition mod's own multiplayer test has to clear, and they are why that test needs a relog and a second client rather than one client's reading ([`#pitfalls`](#pitfalls)).

Not covered: the other mod ids inside the same workshop item, which this library has not torn down; this mod's tooltip, quest and economy surfaces; and any live reading of the mod at all, since no session in this library loads it.

## Open
<a id="open"></a>

- Which of the mod's buffed fields survive a dedicated-server round trip beyond the ones the case study names, and whether any of them desyncs silently rather than reverting — settled by a session that crafts a buffed item, reads every buffed field on both sides, and re-reads after a relog; no `X` id.
- Decision: whether a per-item mod value in the design rides item modData or a live Java field — a live field the item packet omits is clamped back by the server's own echo [#1537/C/C-only].
- Decision: whether the design's per-item values are reapplied continuously or behind a guard that fires once — the one-shot guard this mod ships is poisoned by its own tracker write [#1539/C/C-only].

## See also

- [`../wire-packets.md#item-stats-packet`](../wire-packets.md#item-stats-packet) — which item fields cross and which do not, which is what decides whether a per-item mod value is reachable on a client at all.
- [`../../platform/mp-model.md#item-moddata`](../../platform/mp-model.md#item-moddata) — how item modData moves, and the routes a mod can use instead of a live Java field.
- [`../food-item-model.md`](../food-item-model.md) — the item state axes and script keys a per-item nutrient value would sit beside.
- [`../../platform/lessons.md#rules`](../../platform/lessons.md#rules) — the durable-state rule this mod's failure is the worked case for.
- [`../../reference/wall-map.md`](../../reference/wall-map.md) — the CAN and CANNOT rows for per-item mod values and for the item packet.
- [`catalog.md#api-surface`](catalog.md#api-surface) — where this mod sits in the surveyed corpus and which APIs that corpus uses.
