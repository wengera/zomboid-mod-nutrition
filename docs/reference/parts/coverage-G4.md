# Coverage — G4 (testing, data, tools, ledgers and the working reads)

Sub-block `#1701–#2000`; **276 rows written, `#1701`–`#1976`**, contiguous, 24 ids unused (see
§ Handed to other groups). Candidates file: `.superpowers/sdd/restructure-1-register/candidates-G4.tsv`
(**101 candidates**: `CLAUDE.md` 1, `data/README.md` 33, `docs/testing/README.md` 2,
`docs/testing/profiles.md` 65; `pipeline-design.md`, `spikes.md`, `tools/README.md` and
`jar-method-notes.md` yield none — the tool under-counts this group, so the sources read in full are
the checklist and every section below is accounted for whether or not it had a candidate).

---

### docs/testing/README.md

- § `pzt` — the orchestrator — candidates 1 → rows #1701–#1709; dropped: 1 (the M-row artifact
  sentence is the source of #1706, harvested, not dropped); the driven-client cost table is
  collapsed into #1701 as one `table` row.
- § How a driven client is controlled — candidates 1 → rows #1710–#1716; dropped: 1 (the logo-skip
  sentence is restated in `spikes.md` § S2 and harvested there as #1854). The `-safemode` ratio is
  **not** dropped: it is #1711, whose 17 s / 120 s numbers come from `pipeline-design.md`
  § Confirmed facts (this section states only "7× slower"), so that row names both sources.
- § Command bus — candidates 0 → rows #1717–#1760. This is the group's densest section: the bus
  protocol, the four translation shapes, the per-command probe rules, the whole reflective-witness
  contract and the eight reply-reading rules. dropped: 6 (statements that only restate measured
  game facts owned elsewhere — the server owning nutrition and hunger/thirst `duplicate of
  docs/vanilla/eating-pipeline.md § MP behaviour` (#1094); item aging not reaching the client
  `duplicate of #1107`; the two-call perk-experience chain `duplicate of #0918`; script data loading
  per side `duplicate of #0919`; the macro getters absent on the script object `duplicate of #0920`;
  the item-use scaling measurement `duplicate of docs/vanilla/recipes-dataset-notes.md`).
- § Results — candidates 0 → rows #1761.
- § Observation — candidates 0 → rows #1762–#1769 (the doubled client grep, the limit-is-a-break
  rule, the two error-classifier over-counts, the deliberate-raise rule, the client-timeout rule and
  the client-side verify gate).
- § Harness layout — candidates 0 → rows #1770 (open), #1771 (eight files: six core plus the two
  scenario files the loader walks recursively).
- § Scenarios and the test layer — candidates 0 → rows #1772–#1787, #1974 (the scheduler hooks the
  once-a-minute event once, split out of #1775 in fix round 1).
- § Server side — candidates 0 → rows #1788.
- superseded: none minted here (see § Handed to other groups). unverified: none.

### docs/testing/profiles.md

- § Test profiles (header) — candidates 2 → rows: none (legend, no rows — the two candidates are the
  `Evidence grades:` legend lines).
- § Summary — candidates 0 → rows #1789–#1793 (the five numbered summary claims).
- § Reading the committed artifacts — candidates 0 → rows #1794, #1795 (both traps).
- § The TOML schema — candidates 14 → rows #1796, #1797, #1810; the fifteen-key schema table is one
  `table` row (#1796) per the grain rule, with the precedence rule (#1797) and the sandbox-key
  validation (#1810) split out because they rest on different sites.
- § How a `[[mods]]` entry becomes a folder — candidates 6 → rows #1798–#1800; the six-branch
  resolution table is one `table` row (#1799).
- § What a profiled run prints first — candidates 0 → rows #1801.
- § How `-nosteam` mod loading works — candidates 3 → rows #1802–#1805; dropped: 1 (the 52/51
  drifted-folder count is `duplicate of docs/modding/anatomy.md § 7` (#0837/#0866) and is carried
  here only inside #1840's corpus rows).
- § What a profile changes, and what it does not — candidates 12 → rows #1806–#1809, #1811, #1812;
  the six-row measure table is one `table` row (#1807), the five sandbox keys one `table` row
  (#1809).
- § The cadence ceiling — candidates 2 → rows #1813–#1816; #1815 is `open` (where the true ceiling
  sits between 8 and 10.08 is unmeasured).
- § The missing-mod failure mode — candidates 1 → rows #1817–#1822.
- § L0 — `tools/mod_lint.py` — candidates 9 → rows #1836, #1837; the nine-rule table is one `table`
  row (#1836) per the grain rule.
- § The installed corpus, swept — candidates 8 → rows #1838–#1841, #1976 (+ #1964, shared with
  CLAUDE.md § 8); dropped: 1 (the two superseded plan figures are narrative about a plan's
  prediction). unverified: #1839 (the per-rule breakdown) and #1976 (the 85 → 84 → 84 drift) — no
  committed file records a `mod_lint` sweep's findings, so both carry the bound
  `snapshot 2026-09-10 13:47; the sweep output was not committed`. #1838's 84 = 3/30/51 total **is**
  recorded in a surviving file (`tools/README.md:61`) and stays settled; #1841 keeps the
  subtree-rewrite half, which `data/README.md:647` records.
- § MP behaviour — candidates 2 → rows #1823–#1827.
- § Open questions — candidates 6 → rows #1828–#1835; OQ 1 and OQ 6 are closed in the source and
  their current statements are G2's (#0819, #0818), so only the profile-side halves are harvested
  here; OQ 3 is #1830 (`open`), OQ 4 #1831, OQ 5 #1828.
- § Sources — candidates 0 → rows: none (a citation list, no claims).
- superseded: none minted here. unverified: none.

### docs/testing/pipeline-design.md

- § Goal / Posture — rows: none (charter prose, no claims).
- § Confirmed facts the design stands on — candidates 0 → rows #1843 (the eleven-fact table
  collapsed to one `table` row).
- § Layers — candidates 0 → rows #1842.
- § Components — rows: none (superseded in the source itself by `profiles.md` and
  `README.md` § Scenarios, which this part harvests; the section says so).
- § Sync witness (L4) — candidates 0 → rows #1741 (shared source with `README.md` § Command bus);
  dropped: 1 (no client-to-server item-field API is `duplicate of #1092`).
- § Fragility budget — candidates 0 → rows #1844, #1845.
- § Spikes (the S1–S7 summaries) — rows: none (each is a one-line restatement of `spikes.md`,
  harvested there).
- § Roadmap — candidates 0 → rows #1846; dropped: 2 (the T2 weight-gain and fasting numbers are
  `duplicate of docs/vanilla/nutrition-core.md § Verified on server`; the T1 sweep figures are
  #1838).
- § Prior art to lean on — rows: none (a reading list).

### docs/testing/spikes.md

- § S1 — Boot loop — candidates 0 → rows #1847–#1851; #1848 states the section's **five**
  design-changing bullets (the `-nosteam`-works-cleanly bullet is included, not dropped); #1847,
  #1849, #1851 are `unverified` with an `uncommitted:` bound (the spike runs left no artifact
  folder, R17).
- § S2 — Auto-join — candidates 0 → rows #1852–#1859; the fifteen-fact table is one `table` row
  (#1852) plus four singled-out rows; #1856, #1858 `unverified` / `uncommitted:`.
- § T0 — provision / boot / attach split — candidates 0 → rows #1860–#1863; #1860, #1862
  `unverified` / `uncommitted:`.
- § S3 — Mods under -nosteam — candidates 0 → rows #1864 (`unverified`), #1865.
- § S4 — Result channel — candidates 0 → rows #1866, #1867.
- § S5 — Time acceleration in MP — candidates 0 → rows #1868–#1872; #1868–#1871 `unverified` /
  `uncommitted:`.
- § S6 — Witness round-trip — candidates 0 → rows #1873–#1875; dropped: 2 (the client-side item
  edits and the client-created item are `duplicate of docs/vanilla/eating-pipeline.md § MP
  behaviour` — #1092, #1093). The section's **dated correction** ("direction corrected 2026-09-10")
  is a correction site whose current statement is the G2b row #1094, so it is entry 28 under
  § Handed to other groups rather than a drop. #1873 and #1875 `unverified` / `uncommitted:`.
- § S7 — reloadlua iteration — candidates 0 → rows #1876–#1880, #1975 (the reload being server-local
  with no packet to clients, split out of #1876 in fix round 1); #1876–#1878 and #1975 `unverified`
  / `uncommitted:`.

### data/README.md

- § Data (header) — candidates 0 → rows: none (the no-stamp-row rule is #1967, harvested from
  `docs/decisions.md` where the ruling lives).
- § food-items — candidates 2 → rows #1881–#1883.
- § CSV columns — candidates 0 → rows #1884–#1890, #1904, #1911 (+ #1737, shared with
  `README.md` § Command bus); the 61-column table is one `table` row (#1885). **Per-item values
  never enter the register**: the worked can and apple examples are carried as the measured example
  in #1892 only.
- § Per litre, not per item — candidates 4 → rows #1891–#1898; #1891 is the `order` row for the
  four-step chain, #1892 the measured drink probe, #1894/#1895 the two unit traps, the third trap
  folded into #1893's claim.
- § JSON — candidates 0 → rows #1899, #1900.
- § recipes — candidates 2 → rows #1901–#1903.
- § CSV columns (recipes) — candidates 0 → rows #1904; the 37-column table is inside #1903.
- § JSON (recipes) — candidates 0 → rows #1905–#1909.
- § evolved-recipes — candidates 2 → rows #1910.
- § CSV columns (evolved) — candidates 0 → rows #1911.
- § JSON (evolved) — candidates 0 → rows #1912, #1913.
- § mod-inventory — candidates 1 → rows #1914–#1925; the twenty-field record is one `table` row
  (#1925).
- § The two nutrition signals — candidates 0 → rows #1926–#1931.
- § workshop-search — candidates 0 → rows #1932, #1933.
- § The hard constraint — candidates 2 → rows #1934.
- § Per term (2026-09-10 16:26) — candidates 0 → rows: none (the eight-term table is inside #1932's
  counts).
- § The three installed hits — candidates 3 → rows #1935, #1936 (the three-row table collapsed into
  #1935's claim; per-item Workshop rows are not separately falsifiable claims).
- § The load-bearing not-installed items — candidates 7 → rows #1937 (one `table` row for the six).
- § The six rows topped up at 16:56 — candidates 7 → rows: none (`dropped: 7` — the same six-row
  page reading as #1937's, one fetch pass later; the fill mechanism is #1942).
- § Why 165 rows have no size — candidates 0 → rows #1938–#1942.
- § workshop-catalog-details — candidates 3 → rows #1943–#1945 (the nine-row table collapsed into
  #1944/#1945; the two read-twice rows fold into #1945's bound).

### tools/README.md

- § Intake pipeline — candidates 0 → rows #1946–#1959, one block per tool: the mirror (#1946), the
  documentation lint (#1947–#1949), the layout lint (#1836, written under `profiles.md` § L0, whose
  table this section delegates to), the inventory (#1950–#1952), the workshop search
  (#1953–#1956), the food scanner (#1957, #1958) and the recipe scanner (#1959).
- § Reference tooling — candidates 0 → rows #1960, #1961; dropped: 3 (`claimslib.py`,
  `claims_harvest.py` and `claims_check.py` are the register's own tooling, whose rules the spec
  owns and not this page — `docs/superpowers/specs/2026-09-17-reference-restructure-design.md`).
- § Planned (P4) — rows: none (an unwritten tool).
- § Conventions — candidates 0 → rows #1962.

### CLAUDE.md

- § 6. Evidence standard — candidates 1 → rows: none (legend, no rows — the C/M/W definition is the
  spec's).
- § 8. Environment gotchas — candidates 0 → rows #1963, #1964 (the two platform gotchas); dropped:
  4, with the reason the brief gives — the repository gotchas are **not claims about the platform**:
  the Bash cwd reset, the heredoc-apostrophe failure, the CRLF file list and the stray client
  process are facts about this checkout and this tool harness, and belong to the repository's own
  working notes rather than to the register.
- § 10. Key measured facts — candidates 0 → rows: none. Every headline is a pointer to a row another
  group owns: the per-key merge of a partial `item` block `duplicate of docs/modding/item-overrides.md`
  (#1006/#1013); the sorted, `Mods=`-independent replay `duplicate of docs/modding/item-overrides.md`
  (#1055); the live `mod.info` chain and one id per folder `duplicate of docs/modding/anatomy.md`
  (#0802/#1116); the empty version dir costing nothing `duplicate of docs/modding/anatomy.md`
  (#0831/#1087); the dedicated server resolving no display name `duplicate of docs/modding/anatomy.md`
  (#1024); `getText` never reaching item names `duplicate of docs/modding/anatomy.md` (#0845);
  `OnEat` firing on both sides with a server-side wrapper before `Eat` `duplicate of
  docs/modding/lua-api.md` (#1031/#1033); a mod's `server/` Lua in the client VM `duplicate of
  docs/modding/lua-api.md` (#1035); `transmitModData` replacing and wiping `duplicate of
  docs/modding/patterns.md` (#1041/#1042); the weight flags agreeing on both non-trivial arms
  `duplicate of docs/modding/patterns.md` (#1100); `pcall` catching a Kahlua nil call and an
  unguarded raise aborting only its own handler `duplicate of docs/modding/lua-api.md`
  (#1178/#1179).
- Every other section — rows: none (handoff prose, process and resume notes).

### docs/decisions.md

- Bound rows only, as the brief directs: **3 rows** — #1965 (no bit-level claim may rest on an
  artifact older than the number-format change), #1966 (a modData exclusion set is per scope),
  #1967 (the flat half of a dataset pair carries no stamp row).
- dropped: the rest of the ledger (~200 rows) — **process**: which model a subagent runs on, whether
  a fix round re-runs, which file a command lands in, how tasks were parallelised, what a review
  deferred. None of them bounds a claim.
- One ledger row is a near-duplicate rather than a drop: the 2026-09-11 slice-12 ruling that
  `data/mod-inventory.json` is a dated snapshot is `duplicate of` #1964 / #0867, and is listed here
  so the ruling is accounted for.

### docs/reference/jar-method-notes.md

- § Tool note — candidates 0 → rows #1968–#1971 (`tool` rows with `tool:pz-b42/…` pointers: the byte
  scan and what it proves, the result cap, the access-flag blindness of the methods subcommand and
  the scratch parser it forced, and the refs subcommand not being a reverse-caller query).
- § A worked query — candidates 0 → rows #1972 (the `$` escape and the not-at-the-bare-name class
  path).
- The brief's bus rule **"a client-spawned item trips a server NPE"** is likewise **not in any G4
  source**: the harness's own decision about the client-side spawn fallback lives in
  `docs/decisions.md` (2026-09-10, slice 01) and is process, not a bound on a claim, and no
  `docs/testing/` section states the NPE. No row was written for it.
- § Summary — where the jar disagreed with plan 13 — candidates 0 → rows #1971 (the refs
  subcommand is not a reverse-caller query), whose source cell names this section because the
  closing method-note paragraph (`jar-method-notes.md:56`) sits under this heading; #1970's
  scratch-parser bound comes from the same paragraph, so that row names both sections. The
  section's own ten-row table yields no rows: all ten are
  jar findings whose current statement another group owns: `getNutrition` on `IsoPlayer`
  `duplicate of` #0897; 26 moodle types and the private base registrar `duplicate of` #1140; the
  moodle-level pin `duplicate of` #1140; `MoodleStat` unexposed `duplicate of` #1141; the closed
  hook inventory `duplicate of` #1133; `loadstring` `duplicate of` #1172; the unknown-key default
  modData arm `duplicate of` #1089/#1125; the script checksum gate `duplicate of` #1182; the
  nutrition sandbox option `duplicate of` #1127; the Lua-exposed trait definition `duplicate of`
  #1158; only 20 of 26 types carrying a stat `duplicate of` #1199.
- The brief's fifth tool item, "`dump` on a large class is slow", **is not in the source** — the
  notes state the `--max 60` cap and nothing about dump cost — so no row was written for it.

### .superpowers/sdd/wave-4/not-settled.md

- 13 lines, 11 bullets. **10 are superseded by a committed G2 row** and are listed in § Handed to
  other groups with their successors; **1 is dropped as process** (the plan template taking inline
  corrections three passes running, and the `## Corrections applied` section that answers it).
- rows minted here: none. See § Handed to other groups for why.

### .superpowers/sdd/13-wall-map/slice-12-bounds.md

- 16 numbered bullets. **All 16 are superseded by a committed G2 row** (several by two) and are
  listed in § Handed to other groups. rows minted here: none.

### .superpowers/sdd/14-feasibility-notes/slice-13-bounds.md

- § 1 (the wall-map bound list, 35 entries) — rows: none. Every entry names a wall-map row and cites
  *the map's own `Ev` / Residual-risk cells*, so the wall map already carries the successor and the
  brief's rule ("imported as a `bound` row **only** where the wall map … does not already carry its
  successor") excludes all 35. They are `reference/wall-map.md` rows, group G3.
- § 2 (the fuller slice-13 list) — rows: none, same reason, plus two trailing sentences: every
  corpus count is a dated snapshot `duplicate of` #1964/#0867, and the ≈ 42 h ceiling, which is
  the one bullet of this file that yields a row — **#1973**.
- **#1973's source cell names the tree file, not this workspace file.** A source cell names a file
  in the tree, and `docs/reference/experiments.md` § Owners and the cost roll-up states the ≈ 42 h
  figure at line 253, so that is the row's source and its pointer. The bounds list itself yields no
  other row, and no G4 row's source cell names anything under `.superpowers/`.

---

## Handed to other groups

Amendment § 7 rules that *a dated-correction site whose successor row lives in another group is
minted by the group that owns the successor* (the controller assigns a continuation id from
`#2001+`). **28 entries from 27 bullets and correction sites** are recorded below: 26 ledger bullets
(one of them, the `mod.info` resolution-order bullet, splitting into two entries) and the dated
correction in `spikes.md` § S6. Every one has its successor in a
**committed G2 part**, so none of them is G4's to mint: the checker's schema rule rejects a
`successor` that is not in the part under test, and `--register-only` on `claims-G4.tsv` therefore
cannot carry them. They are recorded here in full, matched by claim text against the committed
`claims-G2a/b/c.tsv`, so the controller can mint them.

**No bound is lost by this.** Each successor's own `bound` cell already carries the bullet's bound —
verified row by row; the three load-bearing cases are quoted in the report.

| # | Source bullet (old statement, abridged) | successor | G2 claim text it matched (abridged) |
|---|---|---|---|
| NS1 | Merge rule (version dir wins) bounded to a version dir that ships colliding files, n = 1 | #1048 | Inside one mod a same-relative-path collision resolves version-dir-wins: the version folder's file wins, `common/` supplies everything… |
| NS2 | MoodleFramework whole on 42.20.4 is C, derived from the rule — nothing has booted it | #0884 | Whether MoodleFramework loads whole on 42.20.4 and renders a registered moodle is unsettled: its wholeness is derived from the merge rule… |
| NS3 | The carrier: M per arm, n = 1 each, one cookable item, one 12.54 s window, one fixture | #1148 | A mod cannot trust a live item field's client copy to tick: `Food.update` did not advance the client's held copy in this window. |
| NS4 | `mod.info` resolution order open — three unreconciled models; `searchForModInfo` precision C only | #0819, #0803 | For the requested-id lookup only the version dir's `mod.info` id is addressable… / `ZomboidFileSystem.searchForModInfo` is unreachable on 42.20.4… |
| NS5 | The `mod-info-place` WARN text is contradicted only at the discovery call site | #0874 | Mod folders are discovered over a root order… a directory counts as a mod folder iff it holds `common/mod.info`, tested first… — a discovery gate, not the id read |
| NS6 | `common/` inertness bounded to the window-build path; the prerender call site stays uncovered | #0961 | The string-argument trait test does not exist on this build… the one corpus mod that still calls it does so in shadowed `common/` copies that the window-build path never executes. |
| NS7 | The weight-flag gate agreed only in the trivial arm (calories 798 → 783; thresholds 0/1000) | #0900 | The three weight-direction flags are not packet fields… they agree on both non-trivial arms (bound: an earlier slice got agreement only in the trivial arm) |
| NS8 | CleanUI's runtime half is C-inferred, deliberately not run; its live tree does ship the fork | #1292 | Does CleanUI's `pcall(triggerEvent, …)` wrapper change what an unguarded raise does inside a dispatch? |
| NS9 | The cooking pipeline stays C: nothing on the bus reaches a right-click or executes `craftRecipe` | #1248 | Nothing on the bus executes a craft: `recipes.craft` is a reader and nothing on the bus reaches a right-click… |
| NS10 | The transmit WIPE half was not re-measured in pass 3; pass 3 corroborates wipe-and-REPLACE only | #1042 | `transmitModData()` called on the client wipes the server's copy of that player's modData: a key planted server-side only was gone… |
| NS11 | `Food.update` gate is strict `heat > 1.6f`; the td3 artifact string says `>=` (frozen, do-not-cite) | #1206 | The carrier for a cooking item's client copy is `Food.update`'s cooking-branch `sendItemStats`, gated… on `isCookable && !isFrozen() && heat > 1.6f`… |
| S12-1 | Partial-block merge: n = 1 item, one float macro, `ItemType` deliberately kept | #1018 | Whether a partial item block that omits `ItemType` still merges, or fails to instantiate the item as a Food, is untested. |
| S12-2 | Replay sort key: M at two permutations + x121, not three boots; the four candidate strings confounded | #0886 | Which string orders the script-body replay is unmeasured… mod id, folder name, stored script path and `mod.info` display name all sort identically… |
| S12-3 | Two mods at one relative script path: one-path-per-relative-path is C, never run | #1047 | Two mods shipping the same relative script path do not both load: one file wins and the other's blocks are never parsed. |
| S12-4 | `syncItemFields()` server→client and item modData across that hop: unmeasured | #1040 | Whether item modData moves in the server-to-client direction through `syncItemFields()` is unmeasured. |
| S12-5 | The `mod.info` id chain: dedicated-server path only; a `common/`-only folder untested as a probe | #0877, #0823 | Everything measured about the `mod.info` chain… was measured on the dedicated-server path… / Whether a folder carrying only `common/mod.info` resolves under the requested-id lookup is un-run… |
| S12-6 | Merge rule n = 2, both arms had a collision or an empty version dir | #0835 | Whether a version dir that ships `media/` colliding with nothing loads, and whether a shadowed `common/` file is then inert, is un-run… |
| S12-7 | A mod's `server/` Lua in the client VM: M, n = 1 session, incidental, mechanism untraced | #0856 | What maps a mod's `server/` tree into the client's Lua state is unread: the outcome is measured at one session… |
| S12-8 | `transmitModData` server→client: n = 1 (the client→server wipe is n = 2) | #0915 | A server-to-client transmit of player mod data has the same wipe-and-replace shape in the other direction… |
| S12-9 | The unguarded-raise rule: server VM only; the client half and the release client are C | #0959, #0958 | The unguarded nil call's effect on a client is unmeasured: the body-abort and chain-survives halves are server-VM readings only… / What a release client does… is unmeasured… |
| S12-10 | `getText` misses: about the ROUTE, not the `ItemName` table; no positive control; the null guard never fired | #0966, #0931 | The translation readings of the first slice-12 session asked the B41-prefixed key form against a B42 table and carry no positive control… / A bus reply carrying the null flag is inconclusive rather than a miss… |
| S12-11 | `OnEat`: one eat at fraction 1 cannot separate per-eat from per-portion; `OnCreate` never fired | #0929, #0967 | Whether the eat hook fires once per eat or once per portion is unsettled… / The item-block creation hook has never been fired by any session in this library… |
| S12-12 | Weight flags: two arms only; `incWeightLot: true` never produced; the client derives direction only | #1196 | Both non-trivial weight-direction arms agree across sides… (bound: only two arms ran and `incWeightLot: true` was never produced anywhere in the artifact) |
| S12-13 | Still C / UNKNOWN: MoodleFramework, the cooking pipeline, client-side traits, CleanUI × `triggerEvent` | #1115, #0968 | Whether MoodleFramework loads whole and renders a registered moodle at a non-zero level is unread… / Whether any packet carries character traits to a client is unsettled… |
| S12-14 | Corpus numbers are dated snapshots of a live tree — quote with the stamp | #0867 | Quote a corpus sweep with its stamp: the installed workshop tree is live and changes under a running slice. |
| S12-15 | `Item.InitLoadPP`'s net-id reallocation and `fileName` re-stamp: C, unmeasured; stale net id unread | #1063 | Whether the fresh net id `Item.InitLoadPP` allocates per appended body ever puts a stale id on the wire is unread. |
| S12-16 | Do-not-cite: every client-side reading of `x127`, its `summary.sides_agree`, both runs' `server_error_count` | #0869 | Every client-side reading of the unguarded-raise session is unusable: the debug client parked in the Lua debugger… |
| S6 | `docs/testing/spikes.md` § S6, dated-correction site ("Nutrition direction, corrected 2026-09-10"): the spike read the 0.2-kcal agreement as the client computing and the server mirroring. Old evidence: `spike-20260909-143930` / `spike-20260909-144417`, the witness round-trip's nutrition row (no artifact folder committed) | #1094 | Nutrition is server-authoritative: a client `setCalories(3000)` never reached the server and was back to the server's value inside 3 s, while a server-side write reached the client inside 3 s… |

The `server_error_count`-as-a-fault-count half of S12-16 is **not** handed on: it is carried in this
part as #1764–#1766, which state the classifier rule and both of its over-counts.

---

## Anchors proposed

**None.** Every `owner` in `claims-G4.tsv` is a `page#slug` already in
`docs/superpowers/plans/restructure-anchors.md` (checked mechanically over the 350 anchor lines).

The two anchors this harvest reached for and did **not** need: `facts/cooking-and-recipes.md#recipe-io`
(the plan's `#uses` covers it) and `facts/food-item-model.md#fluids` (the plan's
`facts/eating-pipeline.md#fluid-path` covers it). Both rows were retargeted rather than proposed.

---

## Totals

**276 rows, `#1701`–`#1976`** (273 at `643bb0b`, plus #1974–#1976 minted in fix round 1).

| by kind | n |  | by grade | n |  | by status | n |
|---|---|---|---|---|---|---|---|
| `mechanism` | 137 |  | C | 214 |  | `settled` | 253 |
| `rule` | 59 |  | M | 54 |  | `unverified` | 20 |
| `table` | 24 |  | W | 8 |  | `open` | 3 |
| `tool` | 22 |  |  |  |  | `superseded` | 0 |
| `bound` | 19 |  |  |  |  |  |  |
| `count` | 11 |  |  |  |  |  |  |
| `order` | 2 |  |  |  |  |  |  |
| `open` | 2 |  |  |  |  |  |  |

`unverified` (20): #1847, #1849, #1851, #1856, #1858, #1860, #1862, #1864, #1868, #1869, #1870,
#1871, #1873, #1875, #1876, #1877, #1878, #1975 — eighteen `spikes.md` readings whose run left no
artifact folder, written with the spec's `uncommitted: <run-id>` bound (R17) — plus #1839 and #1976,
the two `mod_lint` sweep counts no committed file records, bounded
`snapshot 2026-09-10 13:47; the sweep output was not committed`.

`open`: #1770 (which `mod.info` the harness's own two copies resolve to), #1815 (where the
`EveryOneMinute` ceiling sits between 8 and 10.08), #1830 (which sandbox options survive a restore).

Owner pages: `platform/harness.md` 149 · `reference/datasets.md` 62 · `reference/tools.md` 25 ·
`platform/overview.md` 11 · `platform/lua-platform.md` 9 · `platform/lessons.md` 7 ·
`platform/mod-anatomy.md` 5 · `platform/jar-research.md` 5 · `facts/eating-pipeline.md` 2 ·
`facts/cooking-and-recipes.md` 1.
