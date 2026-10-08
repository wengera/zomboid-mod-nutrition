# Strategy — PZ Nutrition Revamp

This file is the charter; change it deliberately.

## The mod (context for the research — NOT designed yet)

A **realism-oriented nutrition/food overhaul** for Project Zomboid B42:

- **New tracked nutrients** beyond the vanilla four (calories/carbs/protein/fat) —
  vitamins/minerals-class stats tracked mod-side.
- **Full item pass**: rebalanced nutrition values across vanilla food items.
- **MP-first**: must work on a dedicated multiplayer server. Sync correctness is
  a design constraint, not an afterthought.

## The deliverable

The library is built, and it is the reference this repository now is: [`README.md`](README.md) is its map and [`CLAUDE.md`](CLAUDE.md) routes a task into it.
The mod's design comes next and is not in this tree.
The reference states what the research established and never what the mod should be: a page lists the options the evidence allows and the walls it rules out, and the choice between options belongs to the design.

## Method rules

1. **Ground truth is the local install and its jar.** A claim about game behaviour is read from the jar, the Lua or the script files of the local install — `42.21` (jar `4a0e9546ec`) since 2026-10-08, `42.20.4` (jar `b0bbce05d5`) before it, each claim on the build its row names, or measured on a dedicated server running it.
   Where the wiki and the code disagree, the code wins and the page states the disagreement.
2. **Every claim carries a register tag** naming its row of [`docs/reference/claims.tsv`](docs/reference/claims.tsv), with its grade and the pointer to its evidence; the grammar is [`README.md` § Tags](README.md#tags).
3. **The wiki is a mirror and a digest, never the authority.** The pages the reference depends on are mirrored in [`references/wiki-mirrors/`](references/wiki-mirrors/README.md), attributed and dated, each with a hand-written digest, except where [`README.md` § Sources](README.md#sources) marks a page not mirrored; a claim resting on the wiki alone is graded `W` and only corroborates.
4. **External sources live in [`README.md` § Sources](README.md#sources)**: the mirrored wiki pages, the ecosystem projects and the internal sources.
5. **The pz-b42 workspace is reused, never duplicated.** The jar is read through its disassembler at `C:\Users\Angus\pz-b42` (`pz.sh`), and no second toolchain lives here.

Standing warnings are rules on [`docs/platform/lessons.md`](docs/platform/lessons.md).
