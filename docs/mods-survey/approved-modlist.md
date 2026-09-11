# The approved modlist — inventory & tiering

Scan of the full locally-installed workshop set (= the server-approved
corpus), **regenerated 2026-09-10 17:47**, via
[tools/mod_inventory.py](../../tools/mod_inventory.py) → dataset
[data/mod-inventory.json](../../data/mod-inventory.json). Column definitions
and every caveat: [data/README.md](../../data/README.md) § mod-inventory. The
nutrition reading of this corpus — what each signalled mod actually does, with
`file:line` — is [nutrition-mods.md](nutrition-mods.md).

**230 mod folders across 179 workshop items; 229 declare an id** the engine can
index (`3782784855/Skill Recovery Journal` ships no `mod.info` anywhere). Class
distribution, 2026-09-10: **175** light-lua systems · **31** other · **15**
heavy-lua systems · **5** scripts-only content · **4** 3D+lua content. The old
173/33 pair predates the `42.20.1` resolution fix and Steam's mid-slice rewrite
of item `3490370700`; `other` is not "ships nothing" — 24 of the 31 have no
`media/` under the LIVE folder at all, so nothing was scanned rather than nothing
shipped. All 24 ship a `common/media`, 12 also ship a B41 root `media/`, and
`STA_PryOpen` ships `42.18/media` and `42.19/media` beside a live `42.20/`
holding none.

## Curation quality — the bar our mod must meet

- **Zero `loadstring` users.** The whole corpus survived the 42.20.x security
  purge. (Any technique or dependency using it is disqualified outright.)
- **Zero stale B41 flat layouts** — all 230 rows resolve a `42[.x[.y]]/` or
  `common/` folder; no row's `layout` is `flat(b41?)`. Version-folder discipline
  is table stakes. (A mod may still *ship* a bare root `media/` beside its live
  version folder — **153 rows do** — and that copy is not what the scan reads.
  `3041122351/63Type2Van` is where it matters: its only nutrition keys are in
  the root copy, so its B42 script signal is 0 and its B41 one is 7.)
- The server runs its own integrated stack by author "Girth": QuestSystem,
  Economy, BaseQuests, **SDQuests** (Sunday-Drivers-specific content),
  GirthsTweaks, ItemQuality. Practical consequences: (a) a direct channel for
  getting fixes/features landed server-side, (b) our mod must coexist with a
  net-heavy resident framework — **228** `sendClientCommand` / `OnClientCommand`
  / `sendServerCommand` sites across those six mods, 96 of them in QuestSystem
  alone (2026-09-10).

## Domain overlap — mods already touching nutrition/food APIs

These are compatibility constraints AND the teardown shortlist. **Ids are the
engine-resolved `mod_id`** (20 of the 230 rows changed when that rule replaced
the folder-name fallback — Long Term Preservation really declares
`SKITTLE_LongTermPreservation4220`). Two independent signals, both counted over
the **live version folder only**: `Lua` is `signals.food_nutrition` (calls in
`.lua`), `Script` is `signals.script_nutrition` (nutrition keys at the start of
a line in a `.txt` under `scripts/`). **19 mods carry at least one; exactly one
carries both.** Measured 2026-09-10 17:47.

| Mod id | Item | Lua | Script | Why it matters to us |
|---|---|---:|---:|---|
| **`simpleStatus`** | 2867431511 | 12 | 0 | Displays nutrition stats — UI overlap; users already watch these numbers. All 12 reads client-side, in one file. **[Teardown 10](teardowns/simplestatus.md) — done** |
| `CleanUI` | 3437629766 | 11 | 0 | Full UI overhaul over food/status surfaces; 1 064 KB of Lua. All 11 hits are `getHungerChange` in copied vanilla tooltip files — territory, not mechanism |
| `SkillRecoveryJournal` | 2503622437 | 8 | 0 | **Answered:** gates fitness XP on `canAddFitnessXp()` and scales the exercise multiplier by `getProteins()`. In `lua/shared`, so it runs on both sides |
| **`AutoCook`** | 3388721641 | 4 | 0 | Automates the cooking pipeline — hooks the actions we will extend. **Teardown 11** |
| `BeyondTen` | 3765241705 | 4 | 0 | Four getter/setter *names* in a reflection table, not four calls (teardown done) |
| `Economy` | 3624538051 | 4 | 0 | Same shape: a shop-item serializer field map naming the four macro accessors |
| **`SKITTLE_LongTermPreservation4220`** | 3774789651 | 4 | 117 | The closest domain neighbour, and the only mod on both signals: 14 new food items **and** a server-side `OnCooked` hook multiplying all four macros by 0.70. **[Teardown 09](teardowns/longtermpreservation4220.md) — done** |
| `SomewhatTraitsCore` | 3498347699 | 3 | 0 | The corpus's only **player** macro write — an `OnTick` server-side calorie adjustment behind a trait |
| `CustomGamepadUI` | 3001154607 | 1 | 0 | The hit is inside a commented-out vanilla line |
| **`MoodleFramework`** | 3396446795 | 1 | 0 | **Already server-approved** — our leading candidate for new-nutrient moodle UI. The hit is a debug `print`; the real question is whether its `42.20` folder is whole |
| `QuestSystem` | 3624538051 | 1 | 0 | A developer item-dump exporter |
| `Horse` | 3661336777 | 0 | 116 | 288 item blocks and the corpus's **only** vanilla-name collision (`Base.Rope`) |
| `OCsPacking` | 3626823538 | 0 | 76 | 308 item blocks, freshness keys only |
| `ZVirusVaccine42BETA` | 3615135168 | 0 | 36 | Thirst-heavy lab items; splits media across `42.20` and `common` |
| `GirthsTweaks` | 3745960616 | 0 | 26 | Part of the resident Girth stack |
| `JadePackingSD` | 3779653231 | 0 | 18 | 125 item blocks, `module Packing` — new items only |
| `69mini` | 2937786633 | 0 | 7 | One food item; keeps models and UI in `common/media` |
| `SDQuests` | 3745960616 | 0 | 6 | Quest content in the Girth stack |
| `biogas` | 2925657627 | 0 | 1 | A single `ThirstChange` |

`3041122351/63Type2Van` is **not** on this list: its 7 nutrition keys live only
in a B41 flat root `media/` the 42.20.4 build never reads.

## Teardown queue (updated)

Set by slice 08 — criteria, evidence and fall-through in
[nutrition-mods.md](nutrition-mods.md) § The three picks; queue itself in
[README.md](README.md).

Done: [ItemQuality](teardowns/itemquality.md) · [BeyondTen](teardowns/beyondten.md) ·
[SKITTLE_LongTermPreservation4220](teardowns/longtermpreservation4220.md) (slice 09,
2026-09-10; measured on `td1-20260910-192457` and `td1b-20260910-202029`) ·
[simpleStatus](teardowns/simplestatus.md) (slice 10, 2026-09-10; measured on
`td2-20260910-231655`).

| Slice | Mod id | Angle |
|---|---|---|
| 11 | `AutoCook` | Cooking-pipeline hook points (what it wraps = what we must not break), and the `common/` vs `42.x/` question |

Fall-through: `SkillRecoveryJournal` → `MoodleFramework` → `SomewhatTraitsCore`
(item 3498347699 ships 3 mods; a profile must name the `id`). `CleanUI` is
dropped from the queue as too large for a 2 h teardown.

## Heavy-lua landscape (top by `lua_kb`, 2026-09-10)

`net` is `sendClientCommand` + `OnClientCommand` + `sendServerCommand` sites.

KnoxBuildworks 1389KB (modData 66 — definition-driven JSON architecture,
already deeply known) · CleanUI 1064KB (pcall 101) · QuestSystem 718KB (net 96)
· Economy 503KB (net 46, pcall 63) · Horse 476KB (patch 22 — wrapper-heavy;
`mod_id` is `Horse`, folder `HorseMod`) · BaseQuests 423KB (pure lua-table
content, zero API calls — data-as-lua pattern) · GirthsTweaks 280KB (net 45) ·
ZVirusVaccine42BETA 240KB · ElyonLib 211KB · QualityEnhancements 201KB ·
damnlib 185KB · SDQuests 181KB · VVR 171KB · BeyondTen 170KB (pcall 47).

## Event usage across the corpus (hooks / distinct mods, 2026-09-10)

```
OnGameStart 70/25 · OnTick 70/15 · OnPlayerUpdate 55/39 · OnClientCommand 54/20
OnServerCommand 43/14 · OnGameBoot 38/16 · OnInitGlobalModData 33/14
OnFillWorldObjectContextMenu 28/12 · OnFillInventoryObjectContextMenu 23/14
EveryOneMinute 22/10 · OnCreatePlayer 17/14 · OnServerStarted 11/6
```

**This is a floor, not a total**: it is summed over each record's `top_events`,
which keeps only a mod's 8 most-used events.

Read: `OnPlayerUpdate` is the most *widely* used hook (39 mods — it's the
default heartbeat, and therefore the shared perf hotspot); `OnTick`'s 70
hooks concentrate in 15 mods (the expensive tier); `OnInitGlobalModData` +
`OnClientCommand`/`OnServerCommand` form the standard MP state/command bus
that everything sophisticated uses. The three post-Click-to-Start events
(`OnGameStart`, `OnCreatePlayer`, `OnLoad`) are **client only** and never fire
on a dedicated server ([Lua_event mirror](../../references/wiki-mirrors/lua-event.md),
page version 42.20.4), which is what makes that pair the server-side half.
Patterns doc: [../modding/patterns.md](../modding/patterns.md).
