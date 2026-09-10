# Mod survey

Two tiers: a **broad catalog** of nutrition/food-adjacent mods (what exists,
one-line assessment, compat risk on a busy MP server), and **deep teardowns**
([template](teardown-template.md)) of the mods with the most to teach us.

## Teardowns

Queue order and the criteria behind it: [nutrition-mods.md](nutrition-mods.md)
§ The three picks (slice 08, 2026-09-10). Ids below are the **engine-resolved**
`mod_id`, never the folder name.

| # | Mod id | Workshop | Why chosen | Status |
|---|---|---|---|---|
| 09 | `SKITTLE_LongTermPreservation4220` | 3774789651 | Domain twin. The only nutrition candidate shipping a **42.20** folder, and both mechanisms in one 239 KB mod: 14 new food items with full macro sets, plus a **server-side** `OnCooked` hook that multiplies all four macros and hunger by 0.70 on the crafted instance | **next** |
| 10 | `simpleStatus` | 2867431511 | The read side: 12 nutrition reads, all client-side, in one 20 KB file. What a pure client mirror can and cannot see while the server owns the store — and the UI our own mod would overlap | queued |
| 11 | `AutoCook` | 3388721641 | Cooking-pipeline hook points: what it wraps is what we must not break. Also the corpus's sharpest `common/` vs `42.x/` case — its live folder registers no event and `require`s two files only `common/` ships | queued |
| — | [ItemQuality](teardowns/itemquality.md) (Girth's Quest System module) | 3624538051 | Per-item modded stats + the definitive MP-sync failure case study | **done** (seeded) |
| — | [BeyondTen](teardowns/beyondten.md) | 3765241705 | Parallel-stat architecture done right: modData reservoirs, wrapper patterns, reapply-on-event | **done** (seeded) |

**Fall-through**, in order, if a pick will not boot or its lint regresses — the
pass that uses one records that it did: `SkillRecoveryJournal` (2503622437) →
`MoodleFramework` (3396446795) → `SomewhatTraitsCore` (3498347699; that item
ships **3** mods, so a profile must name the `id`). `CleanUI` (3437629766) is
**dropped from the queue** — 1 064 KB of Lua over 54 files is past a 2 h
teardown; its 11 nutrition hits are all `getHungerChange` in copied vanilla
tooltip files and are catalogued in
[nutrition-mods.md](nutrition-mods.md) § Sweep 1 instead.

**Catalog:** [nutrition-mods.md](nutrition-mods.md) — the 11 Lua-signal mods,
the 9 script-signal mods, the Workshop sweep, per-candidate B42 status, the API
surface and the MP-behaviour section the picks turn on.
**Inventory of the full approved corpus:** [approved-modlist.md](approved-modlist.md)
(230 mod folders scanned; dataset in `data/mod-inventory.json`). Distilled
dos/don'ts: [../modding/patterns.md](../modding/patterns.md).

Catalog pass (P3) sources, as actually run: `data/mod-inventory.json` (230 mod
folders across 179 workshop items, swept 2026-09-10 16:20) and
`data/workshop-search.json` (8 terms, 212 results, 180 distinct ids, 3
installed, fetched 2026-09-10 16:26).

## Leads still open after the slice-08 catalog pass

Both original leads have been run: the local-install grep is now
`data/mod-inventory.json`'s two nutrition signals, and seven of the eight
Workshop terms were swept (`realistic needs` was replaced by `spoilage`). What
is left:

- **Subscribe to one Workshop nutrition mod.** The installed corpus contains
  **no vanilla food override at all** — one name collision in the whole
  nutrition-bearing script set, and it is `Base.Rope` — so the item-pass
  mechanism our own mod needs has no local precedent. The cheapest reads are
  `3785515388` Reasonable Nutrition (145 KB) and `3736275816` ApocalipseBR -
  Nutrition Sync Fix (453 KB, the only third-party attempt at the MP problem
  this library exists to characterise). Both are W until a human subscribes;
  see [nutrition-mods.md](nutrition-mods.md) § Sweep 3.
- **`3796644824`**, a third-party "nutrition laundering" patch to teardown pick
  1, is a claim about a mod we *can* read — worth the comparison once
  subscribed.
- Known adjacent from our sessions, none of them nutrition-signalled and none
  in the queue: damnlib (KI5) OnCreate patterns, ChuckleberryFinn mods
  (wrapping style, error handling — `SkillRecoveryJournal` is one), Elyon Lib
  (networking), MoodleFramework (UI for new stats; see
  [nutrition-mods.md](nutrition-mods.md) § Open questions Q3).
