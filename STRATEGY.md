# Research & Documentation Strategy — PZ Nutrition Revamp

Decided by brainstorm 2026-09-13. This file is the charter; change it deliberately.

## The mod (context for the research — NOT designed yet)

A **realism-oriented nutrition/food overhaul** for Project Zomboid B42:

- **New tracked nutrients** beyond the vanilla four (calories/carbs/protein/fat) —
  vitamins/minerals-class stats tracked mod-side.
- **Full item pass**: rebalanced nutrition values across vanilla food items.
- **MP-first**: must work on a dedicated multiplayer server. Sync correctness is
  a design constraint, not an afterthought.

## The deliverable

A **reference library** — this repository. Research concludes when the library
can answer any "how does X work / what's possible / who did it before" question
the mod design will ask. The design itself is a later, separate effort.

## Method rules

1. **Local install is ground truth** (currently 42.20.4). Claims about game
   behavior come from the jar (via pzdis), lua, and script files — cited with
   class/file and line. The wiki is secondary; where they disagree, code wins
   and the discrepancy is noted.
2. **Every system doc has an "MP behavior" section**: what syncs, which side is
   authoritative, what packets/commands are involved. (Lesson source: the
   ItemQuality conditionMax sync failure — see teardowns.)
3. **Wiki intake = mirror + digest**: key pages get a structured excerpt in
   `references/wiki-mirrors/` (attributed, dated, CC BY-NC-SA) so page drift
   can't erase our sources; our own docs digest and cite rather than copy.
4. **Follow the references**: pages/tools the wiki links out to (Umbrella,
   JavaDocs, PZEventDoc, TIS guides, Discord threads) are first-class sources,
   tracked in `docs/references.md`.
5. **Reuse the pz-b42 workspace** (`C:\Users\Angus\pz-b42`): toolchain (pzdis,
   scanners) and existing findings migrate in adapted form — no rewriting from
   scratch, no duplicate tooling.

## Pillars → directory map

| Pillar | Location | Contents |
|---|---|---|
| Vanilla systems | `docs/vanilla/` | Code-level maps: nutrition core, food item model, eat/cook pipelines, food sources, MP sync model |
| Modding platform | `docs/modding/` | Mod anatomy, lua API/events, jar-locked-vs-moddable wall map, modData/sync patterns, item override mechanics, packaging |
| Mod survey | `docs/mods-survey/` | Broad catalog + deep teardowns (template-driven) of 3–5 nutrition/food mods |
| Tooling & data | `tools/`, `data/` | Food-item scanner → dataset for the item pass; recipe mappers |
| **Testing pipeline** | `docs/testing/`, `testing/` | Automated integration tests on a real server + driven clients — L0 static → L4 sync-witness; built BEFORE the mod so the mod is born tested |
| Sources | `docs/references.md`, `references/wiki-mirrors/` | Annotated link map; mirrored excerpts |

## Phases

- **P0 — scaffold** (done): repo, charter, seed docs migrated, first mirrors.
- **P1 — vanilla nutrition core**: complete the Nutrition/hunger/food-item map.
- **P2 — modding platform**: wiki + local-mod evidence → platform reference;
  the moddability wall map (what the mod CAN'T do) is the key output.
- **P3 — mod survey**: catalog, then teardowns (ItemQuality & BeyondTen seeded
  from prior analysis; 3+ nutrition-specific mods to identify and add).
- **P4 — item dataset**: food scanner + full vanilla food/recipe dataset.
- **P5 — feasibility notes**: what the research says is/isn't possible, per
  future design area. Reference, not design.
- **T-track (parallel) — testing pipeline**: spikes S1–S7 then T1–T4 per
  `docs/testing/pipeline-design.md`; T2's accelerated-time nutrition scenario
  doubles as P1 verification of the vanilla model.

## Standing warnings

- **The game patches ~monthly and mods daily** — every doc carries the build it
  was verified against; re-verify before relying on old numbers.
- **`loadstring` is REMOVED** (42.20.x security fixes) — any mod technique or
  tutorial that depends on it is dead; watch for it in older guides/mods.
- **B42 MP is newly re-added and in flux**: TIS published networking-migration
  guides for mods; sync APIs gained methods in 42.20 and will keep moving.
