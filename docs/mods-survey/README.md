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
| 09 | [`SKITTLE_LongTermPreservation4220`](teardowns/longtermpreservation4220.md) | 3774789651 | Domain twin. The only nutrition candidate whose **only** version folder is `42.20`, and both mechanisms in one 239 KB mod: 14 new food items with full macro sets, plus a **server-side** `OnCooked` hook that multiplies all four macros and hunger by 0.70 on the crafted instance | **done** — measured on `td1-20260910-192457` + `td1b-20260910-202029`: the five packet-carried macros sync, `offAge` / `offAgeMax` / `isCookable` / `isCustomWeight` do not, and the mod's own weight write is discarded server-side |
| 10 | [`simpleStatus`](teardowns/simplestatus.md) | 2867431511 | The read side: 12 nutrition reads, all client-side, in one 20 KB file. What a pure client mirror can and cannot see while the server owns the store — and the UI our own mod would overlap | **done** — measured on `td2-20260910-231655`: all five macros mirror inside a signed per-snapshot band on all six snapshots (arrival 0.766 s), the three weight-direction flags agree on both sides although no packet carries them, and `transmitModData()` is a whole-table **wipe-and-replace** — a server-only player-modData key was destroyed by one client transmit |
| 11 | `AutoCook` | 3388721641 | Cooking-pipeline hook points: what it wraps is what we must not break. Also the corpus's sharpest `common/` vs `42.x/` case — its live folder registers no event and `require`s two files only `common/` ships | **next** |
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
folders across 179 workshop items, swept 2026-09-10 17:47),
`data/workshop-search.json` (8 terms, 212 results, 180 distinct ids, 3
installed, fetched 2026-09-10 16:26) and `data/workshop-catalog-details.json`
(the nine catalogued mods' item pages, 9 fetched / 0 failed, 2026-09-10 17:46).

## Lint gate for this directory

**`docs/mods-survey/` is deliberately NOT in `doc_lint.STAMPED_DIRS`** — only
`docs/mods-survey/teardowns` is (`tools/doc_lint.py`), a slice-08 ruling in
[`../decisions.md`](../decisions.md) because widening it would add findings on
`approved-modlist.md` and `teardown-template.md`, which slice 08 did not own.
`nutrition-mods.md` is written to the stamped standard by hand instead, and the
check that enforces it is this one-liner — **run it after any edit to that
file**, alongside the ordinary `python tools/doc_lint.py docs/vanilla
docs/modding docs/testing references docs/mods-survey/nutrition-mods.md`:

```bash
python -c "import sys;sys.path.insert(0,'tools');import doc_lint as d;d.STAMPED_DIRS=('docs/mods-survey',);f=d.lint(['docs/mods-survey/nutrition-mods.md']);[print(x) for x in f];sys.exit(1 if f else 0)"
```

Exit 0 (verified 2026-09-10). It requires the `Verified against: 42.20.4` stamp,
a non-empty `## Sources`, no `TODO`/`TBD`, and a C/M/W grade in every row of
every table carrying an `Ev` header.

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
