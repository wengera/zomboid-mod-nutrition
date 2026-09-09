# The approved modlist — inventory & tiering

Scan of the full locally-installed workshop set (= the server-approved
corpus), 2026-09-13, via [tools/mod_inventory.py](../../tools/mod_inventory.py)
→ dataset [data/mod-inventory.json](../../data/mod-inventory.json).

**230 mods across 179 workshop items.** Class distribution:
173 light-lua systems · 33 asset/map packs · 15 heavy-lua systems ·
5 scripts-only content · 4 3D-content mods.

## Curation quality — the bar our mod must meet

- **Zero `loadstring` users.** The whole corpus survived the 42.20.x security
  purge. (Any technique or dependency using it is disqualified outright.)
- **Zero stale B41 flat layouts** — everything resolves a proper `42.x`/
  `common` tree. Version-folder discipline is table stakes.
- The server runs its own integrated stack by author "Girth": QuestSystem,
  Economy, BaseQuests, **SDQuests** (Sunday-Drivers-specific content),
  GirthsTweaks, ItemQuality. Practical consequences: (a) a direct channel for
  getting fixes/features landed server-side, (b) our mod must coexist with a
  net-heavy resident framework (110+ client/server command call sites).

## Domain overlap — mods already touching nutrition/food APIs

These are compatibility constraints AND priority teardowns:

| Mod | Signal hits | Why it matters to us |
|---|---|---|
| **simpleStatus** | 12 | Displays nutrition stats — UI overlap; users already watch these numbers |
| **CleanUI** | 11 | Full UI overhaul touching food/status surfaces; 1MB lua; must not fight it |
| SkillRecoveryJournal | 8 | Reads nutrition (why? investigate) |
| **AutoCook** | 4 | Automates cooking pipeline — hooks the actions we'll extend |
| **LongTermPreservation4220** | 4 | Food preservation — the closest DOMAIN neighbor on the list |
| BeyondTen | 4 | Uses Nutrition.getWeight in bonus math (teardown done) |
| SomewhatTraitsCore | 3 | Traits interacting with nutrition |
| **MoodleFramework** | 1 | **Already server-approved** — our leading candidate for new-nutrient moodle UI |

## Teardown queue (updated)

Done: [ItemQuality](teardowns/itemquality.md) · [BeyondTen](teardowns/beyondten.md).

| Next | Angle |
|---|---|
| LongTermPreservation4220 | Domain twin: how it models spoilage/preservation, item overrides, MP |
| simpleStatus | How nutrition values are read/refreshed for UI; update cadence |
| MoodleFramework | Dependency evaluation: API, MP behavior, cost of adoption |
| AutoCook | Cooking-pipeline hook points (what it wraps = what we must not break) |
| CleanUI | Error-hygiene exemplar (101 pcall sites) + where food UI lives |

## Heavy-lua landscape (top by code size)

KnoxBuildworks 1.4MB (modData 66 — definition-driven JSON architecture,
already deeply known) · CleanUI 1.0MB · QuestSystem 718KB (net 68) ·
Economy 497KB (net 42, pcall 58) · HorseMod 476KB (patch 22 — wrapper-heavy)
· BaseQuests 423KB (pure lua-table content, zero API calls — data-as-lua
pattern) · GirthsTweaks 269KB · ZVirusVaccine 240KB · ElyonLib 211KB ·
damnlib 185KB · SDQuests 181KB · BeyondTen 170KB · DataLogger 83KB
(server telemetry patterns).

## Event usage across the corpus (hooks / distinct mods)

```
OnGameStart 71/25 · OnTick 69/14 · OnPlayerUpdate 54/38 · OnClientCommand 53/20
OnServerCommand 41/14 · OnGameBoot 38/16 · OnInitGlobalModData 33/14
OnFillWorldObjectContextMenu 28/12 · OnFillInventoryObjectContextMenu 23/14
EveryOneMinute 22/10 · OnCreatePlayer 18/15 · OnServerStarted 11/6
```

Read: `OnPlayerUpdate` is the most *widely* used hook (38 mods — it's the
default heartbeat, and therefore the shared perf hotspot); `OnTick`'s 69
hooks concentrate in 14 mods (the expensive tier); `OnInitGlobalModData` +
`OnClientCommand`/`OnServerCommand` form the standard MP state/command bus
that everything sophisticated uses. Patterns doc:
[../modding/patterns.md](../modding/patterns.md).
