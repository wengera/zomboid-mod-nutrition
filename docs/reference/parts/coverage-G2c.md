# Coverage — G2c (the wall map and the named experiments)

Sources: `docs/modding/wall-map.md` (79 candidates), `docs/reference/experiments.md` (no candidate rows — its
tables carry no `Ev` header, so the generator emits none; harvested in full by reading). Ids `#1121–#1299`
of the `G2c` sub-block `#1121–#1300` (one id spare), plus the continuation slice `#2004–#2011` the controller
minted for fix round 1 (R22).

Pointer layer, after fix round 1: no `repo:` pointer reaches a tree the Phase 4 cut deletes (R20). The only
`repo:docs/` paths left are `docs/modding/wall-map.md` — exempt under R21, because the cut moves it verbatim to
`docs/reference/wall-map.md` — and `docs/reference/experiments.md` / `docs/reference/harness-commands.md`,
which survive. Every fact previously cited to `docs/vanilla`, `docs/modding` (bar the map), `docs/mods-survey`
or `docs/superpowers` now carries the underlying `jar:`, `lua:`, `run:`, `data:` or harness `repo:` evidence,
and no claim states a bytecode offset — the pointer cell carries them.

### docs/modding/wall-map.md

- § (header stamp and grade legend, L3–L6) — candidates 2 → rows: none (legend, no rows: the two lines are the
  `C` / `M` / `W` grade key)
- § Summary — candidates 0 → rows: none (narrative: the five numbered paragraphs restate the 64 rows, the three
  biggest walls and the three biggest doors; the tally 25 CANNOT · 22 CAN · 14 CAN WITH A WORKAROUND · 3 UNKNOWN
  is the verdict rows' own claims and statuses, and paragraph 5's bound is `#1256`)
- § How to read this map — candidates 2 → rows #1256–#1257. The two candidates (L52, L56) are the branch-1 and
  branch-3 halves of the slice-12 dependency rule and are **collapsed into** `#1257`, owned by
  `platform/overview.md#coverage` per the controller's amendment (the wall map keeps exactly its 64 row anchors).
  The `Ev` grammar, the `+`-fuses-two-rows convention and the CANNOT/CAN/UNKNOWN definitions are page conventions,
  not claims: rows: none.
- § The map → § A — New nutrient fields — candidates 7 → rows #1121–#1127 (verdicts), #1185–#1188, #1234
  (cell facts). Cited elsewhere, no row here: A2+A7's whole mechanism (`nutrition-core.md § Macro effects`,
  `patterns.md KEEP 1`, harvested by G1/G2 — carried here only as `#1122`'s claim and bound); A5's
  `InstanceItem` copy is folded into `#1125`'s claim; A6's `processModData` wipe-and-copy is `#1241`
  (one row, two sources).
- § The map → § B — Eat hooks — candidates 7 → rows #1128–#1134, #1189–#1192. Cited elsewhere, no row here:
  B1's client-to-server action chain and B3's whole mechanism (`eating-pipeline.md § MP behaviour`,
  `§ OnEat`, `item-overrides.md § R4`, harvested by G1/G2); B4+B5's `EatOnClient` and `LuaTimedActionNew.complete`
  sites are `#2004` and `#2005` (fix round 1, I1 — folds in the first pass); B7's 8-declared/6-fired hook
  inventory is folded into `#1133`'s claim, which is `#1273`'s successor.
- § The map → § C — The weight formula — candidates 5 → rows #1135–#1139, #1193–#1197. Cited elsewhere, no row
  here: the weight bands and their edges (`body-stats.md § Weight bands`, harvested by G1/G2); C1's carbs-or-lipids
  > 400 threshold is folded into `#1135`'s claim; C5's four flag-write sites are `#2006` (fix round 1, I1).
- § The map → § D — Moodles — candidates 4 → rows #1140–#1143, #1198–#1199. Cited elsewhere, no row here:
  D4's three unmeasured MoodleFramework legs (`patterns.md § Open pattern questions`,
  `anatomy.md § Inputs for the wall map`, harvested by G1/G2) — carried as `#1142`'s bound; D1's registration
  arm and D2+D3's `UpdateStrength` site are folded into their verdict claims.
- § The map → § E — Sync — candidates 10 → rows #1144–#1153, #1200–#1207. Cited elsewhere, no row here:
  E3's whole mechanism (`patterns.md KEEP 11`, harvested by G1/G2); E8's measured "waiting 60 s changes nothing"
  (spike S6, cited through `patterns.md § Measured MP sync facts row 2`, which owns its prose and has no artifact
  folder — recorded in `#1150`'s bound, which is why that row is graded C); E11's bus shape and the Girth stack's
  228 command sites (`patterns.md KEEP 2`, `lua-api.md § 4`); E4's zero-field case study
  (`food-item-model.md`, harvested by G1/G2 — `#1146`, `#1202`–`#1205` are this map's own jar and run reads);
  E10's `KahluaTableImpl.load` wipe and the empty-table arm are folded into `#1152`'s claim. `#1148` (E6) is
  `unverified` after fix round 1 (I3): its headline arm rests on td3-20260911-001948's `carrier` keys, which
  are on the do-not-cite list, so the row carries the jar gate as well and its bound quotes that run's
  whole-run restriction.
- § The map → § F — The cooking pipeline — candidates 4 → rows #1154–#1157, #1208–#1211. Cited elsewhere, no
  row here: F1's registration prose (`lua-api.md § 3`); F5's whole mechanism
  (`food-item-model.md § Key reference`, `recipes-dataset-notes.md`, harvested by G1/G2), including the 2 522-row
  spice dataset and the `useSpice` hole, carried as `#1157`'s bound and `#1278`.
- § The map → § G — Traits — candidates 5 → rows #1158–#1162, #1212–#1213. Cited elsewhere, no row here:
  G3's Lua surface (`lua-api.md § 2`); G4's whole mechanism (`body-stats.md § Open questions 10`, harvested by
  G1/G2 — `#1161` is the map's UNKNOWN verdict and `#1239` the MP-placement row); G2's jar-wide field census is
  folded into `#1159`'s bound.
- § The map → § H — Translations — candidates 5 → rows #1163–#1167, #1215. Cited elsewhere, no row here:
  H1's walk and merge sites (`anatomy.md § 5`, harvested by G1/G2 — carried as `#1163`'s claim); H4's
  `CustomWeight` rule is folded into `#1166`'s bound and `#1214` carries the derived-weight mechanism (sourced
  to § J, where the map states it with its offsets).
- § The map → § I — The merge rules and loading — candidates 12 → rows #1168–#1179, #1216–#1226. Cited
  elsewhere, no row here: I1+I6 and I11 (`anatomy.md § 6`), I8 and I10 (`item-overrides.md § Load order (a)`),
  I4+I5's id chain prose (`anatomy.md § 2`), I3's AutoCook census numbers
  (`autocook.md § Architecture → The census`) — all harvested by G1/G2; the census numbers are re-stated here
  only inside `#1218`, the dataset bound the map addresses to `data/README.md` as a ripple. I9's three witnesses
  are folded into `#1174`'s claim; I13's `pcall` try-coverage is `#2008` (fix round 1, I1). I14's file-scope
  arm, `#1226`, is `superseded` (fix round 1, C1): the rule has no jar site in this map, is **cited to
  `lua-api.md` § 5, harvested by G2a**, and its successor is written as `#1179`, the in-part row carrying the
  same rule, because the checker rejects a cross-part successor under `--register-only`; **the merge should
  retarget it to G2a's `#0948`** ("An unguarded nil call aborts the rest of the handler body it fires in"),
  whose pointer `#1226` already copies.
- § The map → § J — The item pass — candidates 5 → rows #1180–#1184, #1214, #1227–#1233. Cited elsewhere, no
  row here: J2's route prose (`item-overrides.md § R2`, harvested by G1/G2); J3's checksum chain is folded into
  `#1182`'s verdict claim. J1's append-and-inert-reset chain is `#2007` and J4's `searchFolders` lower-cased
  store is `#2009` (fix round 1, I1 — both were folds in the first pass). Vanilla's own 13 `module Base`
  redefinitions are **dropped**: the map offers no pointer for the count and the row would have rested on the
  claim sentence alone.
- § MP behaviour — candidates 10 → rows #1236–#1245, one per surface, placed on `platform/mp-model.md`,
  `platform/loader-and-scripts.md`, `platform/mod-anatomy.md` and `facts/wire-packets.md` by the sync placement.
  `#1236` carries both of its runs as two pointers (`exp03-20260910-045523 r13_mp_regression.clientPolls` for the
  0.51 s / 1.42 s reads and `exp01-20260910-003929 probe_stats_authority` for the coarser 3 s arm). The three
  viable shapes for mod state (the numbered list after the table) are readings, not mechanisms: rows: none —
  they belong to `areas/mp-sync.md#sync-options` and each hazard already has its row (E7/E8, E9/E10, E11, G4,
  E4, E5).
- § Named experiments — candidates 0 → rows #1274–#1299 (one `open` row per surviving id, same rows as
  `docs/reference/experiments.md § Named experiments`) and #1235 (the live bus registration count from the
  standing contract). The "highest consequence per minute" block (X16, X33, X29, runner-up X4) is a priority
  reading, not a claim: rows: none. The roll-up (26 rows · 24 boot-wanting · 21 live sessions · ≈ 113.5 min ·
  4 desk reads · 6 harness changes, and the by-owner subtotals) is arithmetic over the 26 rows already in the
  register, each of which carries its own cost and owner in its bound: rows: none.
- § What the library cannot yet measure — candidates 0 → rows #1246–#1255, one `bound` row per bullet, all owned
  by `platform/harness.md#walls` (the controller's slug for the brief's `#walls-and-bounds`). The `text.get`
  null guard, "never fired (untriggered, not confirmed)", is `#1251`. Bullet 10's three legs (`#1255`) are also
  the bounds of `#1122` (A2+A7), `#1133` (B7) and `#1182` (J3), and their experiments are `#1294`, `#1279`
  and `#1282`.
- § Discrepancies — candidates 0 → rows #1258–#1273, #2010–#2011. The two-packet comparison table is `#1258`
  (the mechanism) plus `#1259` (the `docs/modding/README.md` § Hard-won platform facts bullet as `superseded`,
  successor `#1258`); its per-cell numbers are `#1200` and `#1241`. The twelve "previously predicted → now" lines
  are `#1262–#1273`, one `superseded` row each, pointer = that line in `docs/modding/wall-map.md` § Discrepancies
  under R21, successor = the current statement's row. The H3 · I4+I5 · F5 line is **split** (fix round 1, I2):
  `#1269` keeps H3's prediction (successor `#1165`), `#2010` carries I4+I5's (successor `#1171`) and `#2011`
  F5's (successor `#1157`), each pointing at its own clause of line 357; `#1267` still carries two successors
  for the G5 split. The wiki-mirror
  bullets: `trait.md`'s String `hasTrait` is `#1260`, the one `contradiction` row; `mod-structure.md` agrees with
  the jar and is now M at n = 2 (`#1170`) — a grade history, rows: none; `mod-data.md`'s silence on
  `transmitModData` and `SyncItemFieldsPacket` is a partial-map note carried by `#1123`, `#1126` and `#1152` —
  rows: none. The library residual is `#1261` (`testing/artifacts/README.md`'s x121 `phases.M7` side tag,
  successor `#1174`). The simpleStatus `42.20/` tree drift (Steam added it 2026-09-13) is **dropped here**:
  it is a bound on `docs/mods-survey/teardowns/simplestatus.md`, harvested by that teardown's group.
- § Open questions — candidates 0 → rows: none. Each bullet is explicitly assigned to the document that owns it
  (`nutrition-core.md § Open questions`, `body-stats.md`, `food-item-model.md § Open questions`, the LTP teardown,
  `anatomy.md § Open questions 1`) and carries no `X` id — harvested by G1/G2/G3. The single exception, X9b, is
  `#1278`; the harness bullet that gates I14's client half is `#1246` and `#1289`.
- § Sources — candidates 1 (L458, the wiki-mirror fetch-date parenthesis) → dropped: legend, no rows. The class
  list, artifact list and mirror list are provenance for the rows above, not claims.

### docs/reference/experiments.md

- § The standing spec contract — rows #1235 (the live bus registration set, 56 distinct names over 64
  `TK.register` calls, re-counted 2026-09-17). The six clauses themselves are the experiment contract, owned by
  `platform/harness.md#experiment-contract`: rows: none (a contract, not a claim). The driver constants the
  contract names have rows where the map states them as facts — the per-scope item exclusion set is `#1234`,
  the doubled console grep limit and the two Lua states are `#1174`, the `-debug` break is `#1246`.
- § X bookkeeping — § Struck — rows: none (bookkeeping; each struck id's settling evidence is already the
  verdict row it settled: X1 → `#1165`, X3 → `#1140`, X6 → `#1125`, X8 → `#1131`, X9a → `#1196`,
  X11 and X12 → `#1171`).
- § X bookkeeping — § Re-scoped — rows: none (narrative on how X2, X9b, X10 and X13 changed; the surviving
  questions are `#1274`, `#1278`, `#1275` and `#1279`).
- § X bookkeeping — § Minted by Task 3 — rows: none (provenance for X20–X33, whose rows are `#1286`–`#1299`).
- § X bookkeeping — § Amendment 3's fifteen, mapped — rows: none (a mapping table between an amendment's letters
  and the X ids).
- § Named experiments — rows #1274–#1299, one `open` row per surviving id. The condensed table in the map and
  the full spec here are the same claim: one row, both sources. Each row's claim is the question, its pointer is
  `repo:docs/reference/experiments.md:<line> "<the row's first cell>"`, and its bound carries the cost and owner
  cells in words. The 26 ids are X2, X4, X5, X7, X9b, X13, X14, X15, X16, X17, X18, X19, X20, X21, X22, X23,
  X24, X25, X26, X27, X28, X29, X30, X31, X32, X33 — the struck and split tables name other ids, which have no
  anchor and no row.
- § Merged sessions — rows: none (S-A, S-B and S-D and their ordering constraints are scheduling, carried in the
  affected rows' bounds and owned by `platform/harness.md#experiment-contract`).
- § Splits — rows: none (how X29, X31, X20, X25, X7 and X26 break into arms; X31's two arms and their owners are
  in `#1297`'s bound).
- § Riders — rows: none (standing obligations: the `IGUI_` control, the doubled grep limit, naming and dating a
  workshop mod's live tree, restoring what a session writes — the first is `#1250`, the rest are the harness
  contract).
- § Holes deliberately given NO X id, and why — rows: none (each is a bound on its wall-map row, already written
  into that row's `bound` cell).
- § Owners and the cost roll-up — rows: none (the per-row cost and owner are each open row's bound; the totals
  are arithmetic over them).

## Anchors proposed

None. Every `owner` written by this part is an anchor that already exists in
`docs/superpowers/plans/restructure-anchors.md`, the eight continuation rows included (checked
programmatically against the plan after fix round 1).

Two controller amendments were applied and are worth restating for the merge:

- `platform/harness.md#walls` is used for § What the library cannot yet measure (the brief's
  `#walls-and-bounds` does not exist).
- The slice-12 dependency rule bound (`#1257`) and the map-wide evidence bound (`#1256`) are owned by
  `platform/overview.md#coverage`, not by `reference/wall-map.md#how-to-read`, so `reference/wall-map.md`
  keeps exactly its 64 row anchors. A merged row id is hyphenated and lower-cased (`#a2-a7`, `#b4-b5`,
  `#c3-c6`, `#d2-d3`, `#e1-e2`, `#e7-e12`, `#f2-f3`, `#g1-g6`, `#h5-h6`, `#i1-i6`, `#i4-i5`).

## Totals

187 rows: `#1121`–`#1299` contiguous, plus the continuation slice `#2004`–`#2011`, also contiguous.

By kind: `verdict` 73 (64 wall-map rows + 9 superseded predictions written as verdicts) · `mechanism` 61 ·
`bound` 15 · `count` 9 · `open` 26 · `rule` 2 · `contradiction` 1.

By grade: `C` 121 · `M` 66 · `W` 0 (the one mirror row, `#1260`, carries a `wiki:` pointer beside a `jar:` one
and is graded by the strongest, C).

By status: `settled` 140 · `open` 29 (26 named experiments + the three UNKNOWN verdicts `#1133`, `#1161`,
`#1164`) · `superseded` 17 (12 from § Discrepancies' predictions table, its two splits `#2010` and `#2011`,
`#1259`, `#1261` and `#1226`) · `unverified` 1 (`#1148`, E6).

Candidates accounted for: 79 = 74 harvested (64 verdict rows + 10 MP-behaviour rows) + 2 collapsed into `#1257`
+ 3 dropped (2 grade-legend lines at L5–L6, 1 wiki-mirror fetch-date legend at L458) + 0 superseded + 0 unverified.
`docs/reference/experiments.md` yields no generator candidates and was harvested by reading: 26 `open` rows and
one `count` row, with every other section accounted for above as `rows: none` and its reason.

Owner spread: `reference/wall-map.md` 64 · `platform/` 66 · `facts/` 29 · `areas/open-questions.md` 26 ·
`reference/datasets.md` 2 (the superseded rows carry the owner of the current statement's page, which rule 1
never checks).

Fix round 1 (2026-09-21) changed the pointer layer, not the row set: 58 pointer cells replaced, 8 rows added
(`#2004`–`#2011`), 18 claims re-worded after the offsets came out, `#1148` re-graded `unverified` and `#1226`
`superseded`. No row was deleted or renumbered.
