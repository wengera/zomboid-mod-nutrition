# Coverage — harvest G2b (item overrides, patterns, the modding README)

Sub-block `#1001–#1120`, all 120 ids used, plus the continuation slice `#2001–#2003` the
controller minted in fix round 1 under R22 — 123 rows in all. Candidates file:
`.superpowers/sdd/restructure-1-register/candidates-G2b.tsv` (95 candidates: 68 from
`item-overrides.md`, 23 from `patterns.md`, 4 from `README.md`).

"Collapsed into" means the candidate states a claim another row already carries; that row's
`source` cell names this section too, so the section is reachable from the register.

### docs/modding/item-overrides.md

- § Item overrides — the five routes a mod has into a vanilla item's nutrition (preamble) — candidates 2 → rows: none; dropped: 2 (both are the `Evidence grades: **C** … **M** … **W** …` legend — legend, no rows)
- § Summary — candidates 0 → rows: none (the five numbered points restate § Model and § The routes in detail; every fact in them is a row under the section that measures it)
- § The five routes — candidates 5 → rows #1001; collapsed into #1001: 4 (the route table is an options table with uniform column meaning, so it is one `table` row; each route's own measured detail is a row under its § R\<n>)
- § What a second `item` block actually does — candidates 6 → rows #1002–#1007; collapsed into #1003: 1 (the `ScriptType.<clinit>` cell and the `LoadScripts` cell state one sentence — `Item` carries `ResetExisting` and the reset runs before every body but the first)
- § R1 — Redefine a vanilla name in `module Base` — candidates 4 → rows #1008–#1012 (#1012 is the 17-key count the prose states; #1058 also carries this section as a source)
- § R2 — The partial block, and why the trap is not where the plan put it — candidates 5 → rows #1013–#1019 (#1006 is measured here and sourced here too); the `n = 1 item, one build, one key type` bound is carried verbatim on #1006, #1013–#1017 and #1057
- § R3 — A new item in the mod's own module — candidates 9 → rows #1020–#1030
- § R4 — Lua hooks on the instance — candidates 11 → rows #1031–#1038; dropped: 3 (the `Eat` / `EatOnClient` order paragraph — the page sends it to `docs/vanilla/eating-pipeline.md` § Model, which owns the order; the `OnCooked`-is-not-server-gated paragraph — `lua-api.md` § 3 owns the three hooks' resolution and side; the LongTermPreservation `OnCooked` paragraph — the page sends it to that mod's teardown § MP handling)
- § R5 — Item modData, the new-nutrient route — candidates 6 → rows #1039–#1044 (#1040 is the X14 open row the section's prose raises); collapsed into #1039: 1 (the `itemWrites` cell is the bound on the census cell — client 1 / server 0 — and is carried as #1039's `one-side` bound)
- § Load order between two mods (intro) — candidates 0 → rows: none (it only separates the two collisions)
- § (a) Two mods ship the same relative script path — candidates 2 → rows #1045–#1050
- § (b) Two mods redefine the same item name in different files — candidates 7 → rows #1051–#1057, and in the continuation slice #2001 (the `loading <id>` lines walk `Mods=` order — folded into #1055's bound at first pass and minted as its own row in fix round 1) and #2003 (the frozen `x12-overrides.toml` `Mods=` comment, `superseded` -> #1055). The `x125` do-not-cite restriction is quoted verbatim in the bounds of #1054 and #1055, naming its three key paths `body.*.means`, `summary.O1_means` and `verdicts.P20.observed.means`
- § Code map — candidates 1 → rows: none; dropped: 1 (a navigation table — every site it lists is quoted at its use above and is already a row: #1002–#1007, #1045–#1047, #1051)
- § MP behaviour — candidates 4 → rows #1058; collapsed: 3 (the `ItemStatsPacket` row into #1036/#1037/#1038; the `Nutrition`-is-server-authoritative row into #1094; the weight-flags row into #1100)
- § Discrepancies — candidates 4 → rows: none new; superseded: #1059 (-> #1006), #1060 (-> #1055), #1061 (-> #1012); collapsed into #1026: 1 (Discrepancy 4, the `getText` prediction — the old statement carried no pointer of its own and the reading that falsified it, `phases.O5`, is do-not-cite, so the current statement is #1026 and the bound carries the restriction)
- § Open questions — candidates 2 → rows #1062, #1063; collapsed: 2 (question 2, the replay sort key, into #1056; question 3, two mods at one relative script path, into #1047). Questions 1 and 4 are #1018 and #1040; questions 5 and 6 carry no grade idiom and are #1062 and #1063
- § Sources — candidates 0 → rows: none (provenance and cross-references)

### docs/modding/patterns.md

- § (stamp and preamble) — candidates 0 → rows: none (a dated change log of the page)
- § KEEP — patterns to adopt — candidates 1 → rows #1064–#1075 (one `rule` row per KEEP 1–12) and #1087 (KEEP 10's empty-version-dir arm). KEEP 10's merge rule is #1048 and its `overrides`-line cautions are #1049; KEEP 11 is #1058; KEEP 12's measured mechanism is #1035 and its untraced-mechanism hole is #2002 (X18, in the continuation slice) — each of those five rows names this section in `source`. KEEP 10's AutoCook port sizes and the inventory's live-folder caveat are left to the AutoCook teardown § Architecture, which the entry cites
- § FILTER OUT — anti-patterns observed or implied — candidates 2 → rows #1076–#1086 (one `rule` row per FILTER 1–11) and #1088 (FILTER 10's second subject, AutoCook). FILTER 10 splits by direction into #1042 (client → server, `n=2`) and #1041 (server → client, `n=1`), by subject into #1042/#1085 (simpleStatus), #1088 (AutoCook) and #1041/#1042 (the slice-12 mod pair); FILTER 1's arm-flip corollary is #1106; FILTER 9's numbers are #1038, which that entry names as the canonical graded row; FILTER 11's `pcall` and handler corrections are left to `lua-api.md` § 5, which the entry says owns them
- § Measured MP sync facts (42.20.4, spike S6) — candidates 7 → rows #1089–#1104; unverified: #1090, #1092, #1093 (the three `M (spike S6)` readings whose runs `spike-20260909-143930` / `spike-20260909-144417` have no artifact folder — under R17 they keep the source's `M`, cite `run:<run-id> findings.json S6.<key>`, start `bound` with `uncommitted:` and are owned by `platform/mp-model.md#open`). The `setWeight` cell is split into eight rows: #1097 the discarded client weight delta, #1098 the three flags computed ahead of the skip, #1099 the trivial arm, #1100 both non-trivial arms, #1101 the `> 400` not 700 threshold, #1102 the missing clamp on a negative calorie write, #1103 `updateWeight`'s absent timer gate, #1104 the evaluate-it-server-side consequence as a `C` row with bound `inference`. The player-modData cell is split into #1090 (arrival, unverified), #1091 (the wipe-before-rawset mechanism) and #1042 (the measured wipe)
- § The other direction — server → client, on one item (slice 09) — candidates 6 → rows #1105–#1112; collapsed: 2 (the four uncarried setters into #1037; the cooked-`thirstChange` halving into #1038). The client-copy cell is three arm rows (#1108 td1, #1109 td2, #1110 td3), one mechanism row (#1111, the 1.6 gate and the per-game-minute push) and one rule row (#1112). The vanilla display-name control for #1106 is stated in the bounds of #1027 and #1106 without a pointer, because its only artifact key (`td2` `appendix.A1`) is do-not-cite
- § Two facts that cross no wire at all (slice 12) — candidates 2 → rows #1113 (the ~5 s dedicated-server item tick, taken from the section's timing paragraph, which carries no grade idiom and is not itself a candidate); collapsed: 2 (the per-key merge and replaces-not-adds fact into #1006 and #1010; the display-name fact into #1024 and #1026). The three "Consequences for the nutrition mod" bullets and the `settimespeed` bullet carry no grade idiom and are dropped as restatements of #1065, #1076, #1085 and the harness's time rules
- § Open pattern questions (feed into teardowns) — candidates 5 → rows #1114, #1115; collapsed: 1 (the id-vs-script-path item into #1055 and #1056); dropped: 2 (the CleanUI × `triggerEvent` item — its runtime half is the wall map's X26 row and its load-order half the page itself dissolves; the `-debug` freeze item — the page says `lua-api.md` § 5 owns the cause and the release-client half is the wall map's X23). The two moodle walls inside the MoodleFramework item are left to `wall-map.md` D1 and D2+D3, which the entry cites as their owner; what is harvested from it is #1115, the X29 open row
- § Sources — candidates 0 → rows: none (provenance, artifact paths and do-not-cite pointers)

### docs/modding/README.md

- § (preamble) — candidates 0 → rows: none
- § The P2 documents — candidates 1 → rows: none; dropped: 1 (a routing table plus its grading legend — every mechanism it points at is a row under the doc that owns it)
- § Hard-won platform facts (from prior sessions — now mostly owned elsewhere) — candidates 3 → rows #1116–#1120; superseded: #1118 (-> #1119); unverified: #1117, #1120; collapsed into #1048: 2 (the version-folder merge bullet, whose `n = 2` reading this README is the third source for). The item-scripts bullet carries no grade idiom and is dropped: its item half is #1005/#1006 and its recipe half is `docs/vanilla/recipes-dataset-notes.md`

## Continuation slice (#2001–#2003)

Minted by the controller in fix round 1 under R22; the sub-block `#1001`–`#1120` was already full.

- **#2001** — the `loading <id>` lines walk `Mods=` order (`item-overrides.md` § (b)), a candidate
  folded into #1055's bound at first pass. `M`, `n=3` sessions, owner
  `platform/loader-and-scripts.md#sorted-replay`; #1055's bound no longer carries it.
- **#2002** — the `open` row for X18, what maps a mod's `server/` files into the client VM
  (`patterns.md` KEEP 12 and § Open pattern questions). Owner `areas/open-questions.md#x18`;
  #1035's bound keeps the same hole as its own limit.
- **#2003** — the dated-correction site G2a could not mint: `testing/profiles/x12-overrides.toml`'s
  frozen `Mods=` comment, `status superseded`, `successor #1055`, owner
  `platform/loader-and-scripts.md#sorted-replay`. Nothing is handed on to another group.

## Anchors proposed

None. Every `owner` in `claims-G2b.tsv` is a `page#slug` that `docs/superpowers/plans/restructure-anchors.md`
already lists, `areas/open-questions.md#x18` included (checked mechanically against the plan's 32
page sections).

Three rows are parked on a page's `## Open` anchor because the spec requires it for an `M` claim
whose only run has no artifact: #1090, #1092 and #1093 on `platform/mp-model.md#open`. #1117 is on
`platform/loader-and-scripts.md#open` for the same reason (a claim the source marks not re-verified).

## Totals

Rows: 123 — `#1001`–`#1120` (the sub-block, contiguous and full) plus `#2001`–`#2003`
(the continuation slice, contiguous).

By kind: `mechanism` 78 · `rule` 32 · `open` 7 · `count` 3 · `bound` 1 · `order` 1 · `table` 1.

By grade: `M` 73 · `C` 50 · `W` 0.

By status: `settled` 106 · `open` 7 · `superseded` 5 · `unverified` 5.

Candidates accounted for (95): harvested 64 · collapsed into another row 19 · superseded 3 · dropped 9.
(#2001 harvests the candidate that was collapsed into #1055's bound at first pass; #2002 is a second
row off KEEP 12's candidate; #2003 rests on no candidate — it is a frozen profile comment.)

By owner layer: `platform/` 93 · `facts/` 17 · `areas/` 13 · `reference/` 0.
