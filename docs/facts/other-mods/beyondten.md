# Beyond Ten
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: how the Beyond Ten skill mod layers a stat the Java engine does not know about on character modData, the techniques a nutrition mod lifts from it, and what its three delivery mechanisms cost; the modData and wire mechanisms it rides are handed off to the packet and model pages.

## Key facts
<a id="techniques"></a>

- Guard a monkey-patch with a sentinel that returns early when the target is already your own wrapper and store the original on your own namespace: it makes the patch safe under a Lua hot reload [#1529/C/C-only].
- Store the experience and derive the level on read rather than storing the level, so a change to the cost curve needs no migration; and keep per-item or per-player transient state in a weak-keyed cache so nothing leaks across a long multiplayer session [#1530/C/C-only].
- Detect a cooperating framework and register with it instead of taking last-write-wins on a contested field such as maximum carry weight, and ship explicit third-party shims rather than assuming [#1531/C/C-only].

## How it works

<a id="what-it-does"></a>
### What it does

Beyond Ten extends every trainable skill to level 15 with mastery levels on top of the native 10 cap, a 15-slot skills UI and per-skill bonuses for ranks 11 to 15 [#1525/C/C-only].

Nothing it does touches food, hunger or nutrition.
It is on this shelf because the thing it extends is a capped engine stat, and the way it extends one without touching the engine is the shape a mod-side nutrient needs.

<a id="architecture"></a>
### The parallel-stat blueprint

Beyond Ten is workshop item `3765241705`, mod id `BeyondTen` by Patryk, examined in its `42` tree on 2026-09-04, whose Lua is eight files of which this reading covers the four shared ones plus one client compatibility file, with a `B41` root tree and a `common` tree beside the version one [#1524/C/C-only].

Beyond Ten leaves the native cap untouched and layers a parallel stat the Java engine does not know about: mastery experience is banked in character modData once native experience is full, and levels are derived on read from stored experience against per-level costs of the level-10 cost plus the level-9-to-10 step times the ranks above 10 [#1526/C/C-only].
The engine is therefore never told that a skill went past its cap, and nothing on the Java side has to be patched to make room for the extension.
Only two things exist at rest: a number banked in a table the engine already saves, and a pure function that turns that number into a level ([#1528/C/C-only], [`#mp`](#mp)).
Everything else the mod shows the player is computed from those two on demand.

Beyond Ten delivers its effects three ways: idempotent wrappers on two vanilla action methods, injection of an effective level into the local variable that a vanilla Lua function reads so that vanilla's own formulas scale for free, and event-time maths for wear negation and carry weight, the last of which registers as a modifier provider with a carry-weight framework when that framework is present rather than clobbering the field [#1527/C/C-only].
The three rest on different things: a wrapped method, a vanilla function's local variable, and an event [#1527/C/C-only].
The injection is the fragile one: it survives only while the vanilla function it targets keeps the local-variable pattern it writes into ([#1532/C/C-only], [`#pitfalls`](#pitfalls)).
The guard that lets the wrappers be installed a second time without stacking is the first of the techniques above ([#1529/C/C-only], [`#techniques`](#techniques)).

The part of this blueprint a nutrition mod takes whole is the resting shape: a reservoir in character modData, values derived on read from that reservoir, wrappers written so that a reload cannot double them, and compatibility by handshake rather than by last write.
The part it cannot take is the delivery mechanism the mod leans on hardest, for the reason the pitfall below gives.

<a id="mp"></a>
### Multiplayer behaviour

Beyond Ten keeps all of its state in character modData, so it is saved and synced by the engine's own character path and needs no custom packet for persistence, and its bonuses are recomputed locally from that modData on both sides because the server loads the same shared files [#1528/C/C-only].

That is a reading of the mod's Lua rather than an observation of a session: no run in the artifact tree evidences its multiplayer behaviour, and no desync was looked for under measurement.
The rules the reading rests on belong to other pages and are not restated here — what a modData payload may carry and what the packet does to the receiver's table ([#1495], [`../wire-packets.md#moddata-packet`](../wire-packets.md#moddata-packet)), and when a player's table crosses sides at all ([#1637], [`../../platform/mp-model.md#player-moddata`](../../platform/mp-model.md#player-moddata)).
Read against those rows, "synced by the engine's own character path" is a statement about surviving a save and a rejoin, not a promise that a mid-session write on one side appears on the other by itself.
A nutrition mod that banks its nutrients the same way inherits both halves of that: the persistence for free, and the crossing as its own problem.

## Walls and bounds

Every line on this page is a reading of the installed mod's Lua, and no run in the artifact tree evidences any of it.
The reading covers the mod's shared files and one client compatibility file, so this page says nothing about the rest of its tree.
The mod has been updated since the reading was taken, and each of its code pointers was re-located by content rather than by line number before being carried here.

<a id="pitfalls"></a>
### Pitfalls

Effective-level injection is inherently brittle, because each injection point pins a vanilla local-variable pattern and a game update silently breaks individual bonuses: it is acceptable for bonuses and not for core nutrient maths, which must own its own event tick instead [#1532/C/C-only].
The failure mode is what makes it unacceptable for a core loop rather than the failure rate: the injected value simply stops arriving, the mod raises nothing, and the only symptom is a number that is quietly lower than it should be.
A nutrient model whose totals drift that way is indistinguishable, from the player's side, from a nutrient model that is merely balanced badly.

<a id="compat"></a>
### Compatibility

The one field Beyond Ten contests with another mod is maximum carry weight, and it shares that field by registering with the carry-weight framework when the framework is loaded rather than by writing last ([#1531/C/C-only], [`#techniques`](#techniques)).
Its remaining third-party work is explicit rather than defensive: a shim for the skill-recovery journal mod, the carry-weight handshake, and a separate compatibility file for a skill-tooltip mod.
A nutrition mod meets Beyond Ten in one place only, the character modData table both would write into, so the obligation this mod creates for the design is to namespace every key and never to replace that table wholesale ([#1091], [`../../platform/mp-model.md#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace)).

Not covered: the mod's client-side UI, its `common` tree and its `B41` root tree, and any live reading of it at all — the skills UI, the tooltip compatibility file and the mod's behaviour in a running session were neither read nor measured, and no run in the artifact tree touches this mod.

## Open
<a id="open"></a>

- Whether the mastery state survives a dedicated-server round trip, and whether the two sides ever disagree about it — settled by a session that plants mastery experience on one side and censuses the character modData on both; no `X` id.
- What the unread part of the mod's Lua does, its client tree and its `common` tree in particular — settled by finishing the read that the architecture line above bounds; no `X` id.
- Whether the derived-on-read cost curve is stable across the mod's own updates — settled by re-locating the cost function by content at the next read and comparing it with the one stated above; no `X` id.
- Decision: whether the design's nutrient effects attach through wrappers and event ticks only, or whether any of them may lean on an injected vanilla local — the injection mechanism fails silently and the wrapper and event mechanisms do not.

## See also

- [`../wire-packets.md#moddata-packet`](../wire-packets.md#moddata-packet) — what a modData payload may carry and what the packet does to the receiver's table.
- [`../../platform/mp-model.md#player-moddata`](../../platform/mp-model.md#player-moddata) — when a player's modData table crosses sides, and [`#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace) for what a transmit does to the other side's copy.
- [`../../platform/lua-platform.md#dev-loop`](../../platform/lua-platform.md#dev-loop) — the in-session reload the idempotent-wrapper guard is written against.
- [`../../areas/new-nutrients.md#store-options`](../../areas/new-nutrients.md#store-options) — the store options a mod nutrient can take, of which this mod's character-modData reservoir is one.
- [`../../reference/wall-map.md`](../../reference/wall-map.md) — the CAN and CANNOT rows for a parallel per-player store and for keeping a mod nutrient in player modData.
- [`catalog.md#api-surface`](catalog.md#api-surface) — the corpus-wide reading of which APIs the surveyed mods use.
