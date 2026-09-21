# Coverage — G2a (`docs/modding/anatomy.md`, `docs/modding/lua-api.md`)

Sub-block `#0801–#1000`; written `#0801–#0970` (170 rows, contiguous). Candidates: 158
(`.superpowers/sdd/restructure-1-register/candidates-G2a.tsv`, 87 in `anatomy.md`, 71 in
`lua-api.md`). A row whose `source` names more than one section is listed under each of them —
a claim that appears in several places is one row with several sources, never a second row.
`§ header` is the prose above the first `##` heading.

### docs/modding/anatomy.md

- § header — candidates 2 → rows: none of their own; dropped: 2 (both are the evidence-grade legend line, `legend, no rows`). The section's supersession note (the re-derived chain replacing the `searchForModInfo` reading) is not a graded candidate and is harvested as superseded: #0801 (-> #0802).
- § 1. `mod.info` — the keys, and who acts on them — candidates 17 → rows #0804–#0817; collapsed into #0805 (the key census `table` row): 5 (`description`, `icon`, `category`, `pack`/`tiledef` and `url`, all display-only cells whose only content is the census count and the display note).
- § 2. Where a `mod.info` may live, and which one supplies the id — candidates 6 → rows #0802, #0818–#0824; also #0801 (superseded, -> #0802) and #0803.
- § 3. Version dirs and `common/` — candidates 7 → rows #0825–#0835; also #0827 (shared with § 6 and § Code map) and #0878 (the two-Lua-states row, shared with § MP behaviour).
- § 4. `Mods=` and the folder name — candidates 1 → rows #0836–#0838; the candidate itself (the drifted-folder counterfactual) is collapsed into #0818, which § 2 states first — one row, two sources.
- § 5. Translations — candidates 7 → rows #0839–#0849.
- § 6. `require` and Lua load order — candidates 2 → rows #0850–#0856; also #0827 (the file-map row, shared with § 3 and § Code map).
- § 7. What `mod_lint` checks, and why — candidates 10 → rows #0857–#0867 and #0960 (the `loadstring` row, shared with `lua-api.md` § 6); collapsed: 2 (the `mod-info` rule, whose engine half is #0802's jar chain, into #0857; the unchanged `id-drift` rule into #0857).
- § The eight experiment mods — candidates 8 → rows #0868 (the roster `table` row) and #0869 (the do-not-cite bound the prose singles out); collapsed into #0868: 8 — each mod's "what it measured" cell points at the measured row that owns it (#0818, #0828, #0831, #0854, #0886, #0922, #0928, #0944, #0948).
- § Code map — the `Mods=` chain, re-derived — candidates 0 → rows #0870–#0875; also #0801 (superseded), #0802, #0803 and #0827.
- § MP behaviour — candidates 5 → rows #0876–#0878; also #0854 and #0919; collapsed: 1 (the "scripts and translations load per side" row — its script half is `patterns.md`'s measured KEEP 11, cited there and not re-graded, and its translation half is § 5's, so the row is #0919 with this section as a second source).
- § Discrepancies — candidates 5 → rows #0879–#0881; also #0801 (superseded, -> #0802), #0803 and #0824.
- § Open questions — candidates 2 → rows #0823, #0835, #0856, #0877, #0882, #0883 (one `open` row per question; questions 1–4 are also stated in §§ 2–6 and carry both sources).
- § Inputs for the wall map (slice 13) — candidates 15 → rows #0884, #0885, #0886, and #0900, #0901, #0917, #0928 with their owning section as first source; collapsed: 6 (new nutrient fields into #0913–#0915; eat hooks into #0922 and #0928; sync — player stats into #0898; sync — modData into #0914; translations into #0842/#0844/#0845; the nil-call guard into #0944/#0949/#0950); dropped: 4 — the item-stats sync row (`patterns.md`'s measured table, cited here and explicitly not re-graded), the cooking-pipeline row (a `C` verdict resting on a harness bound owned by `docs/testing/README.md`), the frozen `x12-overrides.toml` `Mods=` comment (a dated-correction site whose successor is `item-overrides.md`'s sorted-replay row, so no in-part successor id can be named), and the CleanUI × `triggerEvent` two-order check (carried verbatim from `mods-survey/teardowns/autocook.md`). The weight-formula row's client-skip half is re-quoted from `vanilla/body-stats.md` and not re-dumped here, so only its two measured halves (#0900, #0901) are rows.
- § Sources — candidates 0 → rows: none (provenance narrative; the "not committed" note on the three empty `overrides` tails is carried in #0832's bound, and the note that the session-6 claims file's key names were superseded by the artifact's is a claims-file correction, which `source` may never name).

### docs/modding/lua-api.md

- § header — candidates 0 → rows #0887 (the coverage bound: the full event roster is the wiki's, the full command inventory is the testing reference's). The three framing rules restate §§ 2, 5 and MP behaviour and add nothing of their own.
- § Model — the four surfaces — candidates 0 → rows #0888, #0889.
- § 1. Events — candidates 15 → rows #0890–#0896; collapsed into #0890 (the curated event `table` row): 10 (the ten events whose cells state only side, cadence, this library's use and the corpus count). The events with a measured cadence or a measured side (`EveryOneMinute`) are #0892 and #0893; the two hooks that survive a dedicated server are #0895; the install-site row is #0894; the `Event.trigger` mechanism the raise paragraph states is #0896, whose measured halves are #0948 and #0949.
- § 2. Java members by owner — candidates 0 (the heading carries no cells; its three sub-tables are below).
- § `Nutrition` — server-authoritative, per `IsoPlayer` — candidates 6 → rows #0897–#0902; also #0889. The store clamp constants named in the `setCalories` cell are `facts/nutrition-core.md#clamps`' and are harvested from `vanilla/nutrition-core.md`, not here.
- § `Food` / `InventoryItem` — the `TK.ITEM_STATE` set and what the packet carries — candidates 9 → rows #0903–#0912; unverified: #0912 (the item-stats push, graded measured in the source off a spike with no committed artifact folder).
- § `IsoPlayer` / `IsoGameCharacter` — candidates 7 → rows #0913–#0918; collapsed: 1 (the `server/`-file mod-data write into #0854, which `anatomy.md` § 6 states first).
- § `ScriptManager` and the script `Item` — candidates 2 → rows #0919, #0920.
- § 3. Script-side hooks — candidates 3 → rows #0921–#0929.
- § 4. The command bus — the harness's own API, and the model for ours — candidates 0 → rows #0930–#0933. The command inventory itself is `docs/testing/README.md`'s and is not restated.
- § 5. What Kahlua cannot do — candidates 21 → rows #0934–#0958; collapsed: 1 (the loader fact listed in the limits table, into #0854); unverified: #0953 (the slice-08 outage explanation — the run has no committed JSON). The nil-call block is split per independently falsifiable statement: the two catches (#0944, #0945), the two jar readings behind them (#0946, #0947), the body abort and the surviving chain (#0948, #0949), the three log readings (#0950–#0952), the outage explanation (#0953) and the four debug-break rows (#0954–#0957), with the rewritten guard rule at #0935 and the release-client open at #0958.
- § 6. Removed or absent on 42.20.4 — candidates 7 → rows #0960–#0964; also #0843, #0845, #0849 and #0920; collapsed: 2 (the script `Item`'s macro getters into #0920 and the B41 translation layout into #0843, both stated first in their owning sections). The `getText` paragraph below the table is #0845, #0846 and #0849 with this section as a second source.
- § MP behaviour — candidates 1 → rows #0854, #0855 (both stated first in `anatomy.md` § 6; this section is their second source).
- § Discrepancies — candidates 0 → rows #0965 (superseded, -> #0944, #0949) and #0966 (superseded, -> #0845).
- § Open questions — candidates 0 → rows #0856, #0885, #0958, #0959, #0967, #0968, #0969, #0970.
- § Sources — candidates 0 → rows: none (provenance narrative; the per-run do-not-cite restrictions it repeats are carried in the bounds of the rows citing those runs).

## Anchors proposed

None. Every `owner` written here is a `page#slug` already listed in
`docs/superpowers/plans/restructure-anchors.md` (64 distinct owners used, all checked against
the plan).

## Totals

Candidates 158 → harvested 112, collapsed into another row 38, dropped 6, unverified 2
(counted at the candidate, not at the row; the two `unverified` candidates are #0912 and #0953).

Rows 170 (#0801–#0970).

By kind: mechanism 122 · open 15 · rule 8 · bound 7 · table 6 · count 4 · tool 4 · order 3 ·
contradiction 1.

By grade: C 97 · M 70 · W 3.

By status: settled 150 · open 15 · superseded 3 (#0801 -> #0802; #0965 -> #0944, #0949;
#0966 -> #0845) · unverified 2 (#0912, #0953).
