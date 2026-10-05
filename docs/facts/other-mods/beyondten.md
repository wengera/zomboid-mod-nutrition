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
Only two things exist at rest: a number banked in a table the engine already saves, and a pure function that turns that number into a level ([#2855/C/C-only], [`#mp`](#mp)).
Everything else the mod shows the player is computed from those two on demand.

Beyond Ten delivers its effects three ways: idempotent wrappers on two vanilla action methods, injection of an effective level into the local variable that a vanilla Lua function reads so that vanilla's own formulas scale for free, and event-time maths for wear negation and carry weight, the last of which registers as a modifier provider with a carry-weight framework when that framework is present rather than clobbering the field [#1527/C/C-only].
The three rest on different things: a wrapped method, a vanilla function's local variable, and an event [#1527/C/C-only].
The injection is the fragile one: it survives only while the vanilla function it targets keeps the local-variable pattern it writes into ([#1532/C/C-only], [`#pitfalls`](#pitfalls)).
The guard that lets the wrappers be installed a second time without stacking is the first of the techniques above ([#1529/C/C-only], [`#techniques`](#techniques)).

Beyond Ten never writes a Java perk level: it calls no `setPerkLevelDebug`, `LevelPerk`, `LoseLevel` or `level0`, and its only Java experience writes are `setXPToLevel` and the six-argument `AddXP`, made on a dedicated server by its server file alone [#2849/C/C-only].
On a dedicated server it parks the experience of every perk at Java level 10 at the level-9 cumulative total, 337500 for Strength and Fitness against a level-10 total of 487500 [#2102/C/arith.], and banks each tick's rise above it as mastery experience, so while it runs a level-10 Strength or Fitness reads one level's worth of experience below its level [#2850/C/C-only].
Before a world save it writes the level-10 total back and parks the experience again on the next tick [#2851/C/C-only], and a negative amount larger than the banked mastery is passed on from the level-10 total to the six-argument `AddXP` [#2852/C/C-only].
Its effective level is the Java level below 10 and the mastery level from 10 to 15 only at 10, so levels 11 to 15 never reach `getPerkLevel` [#2853/C/C-only], and the Java ladder has no rung past 10 to hold them [#2859/C/C-only].
On Strength and Fitness its mastery costs for levels 11 to 15 are 180000, 210000, 240000, 270000 and 300000 experience [#2854/C/arith.].

The part of this blueprint a nutrition mod takes whole is the resting shape: a reservoir in character modData, values derived on read from that reservoir, wrappers written so that a reload cannot double them, and compatibility by handshake rather than by last write.
The part it cannot take is the delivery mechanism the mod leans on hardest, for the reason the pitfall below gives.

<a id="mp"></a>
### Multiplayer behaviour

On a dedicated server Beyond Ten's authoritative mastery store is the global modData table `BeyondTen_ServerMastery_v1`, keyed by a digest of the account name and player index; the character modData key `BeyondTen` is only a mirror the server imports once as a migration and overwrites every tick, the client's copy is filled by the server commands `Sync` and `SyncPerk`, and the bonuses are recomputed from that store on both sides because both load the same shared files [#2855/C/C-only].

That is a reading of the mod's Lua rather than an observation of a session: no run in the artifact tree evidences its multiplayer behaviour, and no desync was looked for under measurement.
The rules the reading rests on belong to other pages and are not restated here — what a modData payload may carry and what the packet does to the receiver's table ([#1495], [`../wire-packets.md#moddata-packet`](../wire-packets.md#moddata-packet)), and when a player's table crosses sides at all ([#1637], [`../../platform/mp-model.md#player-moddata`](../../platform/mp-model.md#player-moddata)).
Read against those rows, the per-tick overwrite is what keeps the character's table honest: a whole-table replace from either side lasts until the server's next tick, and the client never authors mastery experience.
A nutrition mod that keeps a per-player store the same way takes on the same three parts: a copy the server owns, a mirror it re-publishes, and a command that fills the client's copy.

## Walls and bounds

Every line on this page is a reading of the installed mod's Lua, and no run in the artifact tree evidences any of it.
The reading covers all eight files of the mod's `42` tree as of 2026-10-05, the server, client and shared core read whole for their experience, carry and endurance writes and the rest grepped for every writer [#2849/C/C-only].
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
Beyond Ten wraps vanilla's ten-minute level check on the server so that a Strength or Fitness at Java level 10 with a parked reservoir never loses its level to rust [#2856/C/C-only].
Without the carry-weight framework it runs the vanilla carry recompute for every online player every tick and adds one unit per Strength mastery rank through `setMaxWeight`, and it never calls `setMaxWeightBase` or `setMaxWeightDelta` [#2857/C/C-only].
It also rescales each tick's endurance change on the server for a player holding mastery ranks in Fitness, Sprinting, Nimble, Sneak or Lightfoot, and writes nothing at zero ranks [#2858/C/C-only].
A nutrition mod therefore meets Beyond Ten in four places: the character modData table both write into, which obliges it to namespace every key and never to replace that table wholesale ([#1091], [`../../platform/mp-model.md#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace)); the experience of a level-10 Strength or Fitness, held one level low; the carry field; and the endurance stat.

Not covered: its `B41` root tree, which this build does not load, the skills UI and the tooltip compatibility file beyond a grep for writes, and any live reading of its behaviour — the mod's behaviour in a running session was not measured, and the one run that touches this mod is a co-boot in which its version marker resolved on both sides and nothing more was read [#2837/M/n=2].

## Open
<a id="open"></a>

- Whether the mastery state survives a dedicated-server round trip, and whether the two sides ever disagree about it — settled by a session that plants mastery experience on one side and censuses the character modData on both; no `X` id.
- Whether the derived-on-read cost curve is stable across the mod's own updates — settled by re-locating the cost function by content at the next read and comparing it with the one stated above; no `X` id.
- Decision: whether the design's nutrient effects attach through wrappers and event ticks only, or whether any of them may lean on an injected vanilla local — the injection mechanism fails silently and the wrapper and event mechanisms do not.

## See also

- [`../wire-packets.md#moddata-packet`](../wire-packets.md#moddata-packet) — what a modData payload may carry and what the packet does to the receiver's table.
- [`../../platform/mp-model.md#player-moddata`](../../platform/mp-model.md#player-moddata) — when a player's modData table crosses sides, and [`#wipe-and-replace`](../../platform/mp-model.md#wipe-and-replace) for what a transmit does to the other side's copy.
- [`../../platform/lua-platform.md#dev-loop`](../../platform/lua-platform.md#dev-loop) — the in-session reload the idempotent-wrapper guard is written against.
- [`../../areas/new-nutrients.md#store-options`](../../areas/new-nutrients.md#store-options) — the store options a mod nutrient can take, of which this mod's character-modData reservoir is one.
- [`../../reference/wall-map.md`](../../reference/wall-map.md) — the CAN and CANNOT rows for a parallel per-player store and for keeping a mod nutrient in player modData.
- [`catalog.md#api-surface`](catalog.md#api-surface) — the corpus-wide reading of which APIs the surveyed mods use.
