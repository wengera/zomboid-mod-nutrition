# Coverage — G3b (the mod catalog)

Sources: `docs/mods-survey/nutrition-mods.md`, `docs/mods-survey/approved-modlist.md`,
`docs/mods-survey/README.md`. Candidates: 152 (all on `nutrition-mods.md`; the other two files
carry no `Ev` table and no inline grade idiom, so `claims_harvest.py candidates` yields none for
them — they are still read in full and harvested below). Rows written: 125, `#1551`–`#1675`.

Ids appear under every section that states the claim; a row whose `source` names two sections is
listed under both and is one row, not two.

### docs/mods-survey/nutrition-mods.md

- § Nutrition mods — the catalog, and the three teardown picks (the page preamble) — candidates 3
  → rows: none (legend, no rows: the three candidates are the `Evidence grades: **C** … **M** …
  **W** …` legend lines). The preamble's dataset stamps are carried in the `bound` of every row
  that quotes a sweep, and its corpus-drift sentence is `#1551`'s bound.
- § Summary — candidates 6 → rows #1555, #1581, #1634; dropped: 3 (summary item 3 is restated in
  full by § MP behaviour and is harvested there as #1632–#1640, summary item 4 by § Sweep 3
  (#1597–#1607), summary item 5 by § The three picks (#1641–#1643) — one row, several sources,
  never a second row).
- § Method and scope — candidates 4 → rows #1551, #1552, #1553, #1554, #1556, #1557, #1558,
  #1559, #1560, #1561, #1562, #1564.
- § Sweep 1 — Lua nutrition signals (live version folder, 2026-09-10 17:47) — candidates 22 →
  rows #1573, #1574 (the two 11-row tables, collapsed one `table` row each), #1575, #1576, #1577,
  #1578, #1579, #1580 (the exceptions the prose singles out), #1582, #1583, #1584, #1585, #1586,
  #1587, #1588, #1589, #1590 (the per-mod nutrition-handling verdicts). Collapsed into #1573:
  candidates at L116–126 (11). Collapsed into #1574: candidates at L136–146 (11). BeyondTen's and
  Economy's reflection-table rows and CustomGamepadUI's commented-out hit are stated as counts by
  #1579 and carry no separate row.
- § Sweep 2 — script nutrition definitions (live version folder, 2026-09-10 17:47) — candidates 12
  → rows #1563, #1572, #1591 (the 9-row table collapsed), #1592, #1593, #1594, #1595, #1596.
  Collapsed into #1591: candidates at L173–181 (9).
- § Sweep 3 — the public Workshop (fetched 2026-09-10 16:26, commit `ce7cd72`) — candidates 22 →
  rows #1597 (the 8-term table collapsed), #1598, #1599, #1600, #1601 (the 9-row load-bearing
  table collapsed), #1602, #1603, #1604, #1605, #1606, #1607. Collapsed into #1597: candidates at
  L217–224 (8). Collapsed into #1601: candidates at L238–246 (9).
- § B42 status per candidate — candidates 18 → rows #1570, #1571, #1609 (the 9-row status table
  collapsed), #1610, #1611, #1612, #1613, #1614, #1615, #1616 (the 6-row readiness table
  collapsed), #1617, #1618. Collapsed into #1609: candidates at L296–304 (9). Collapsed into
  #1616: candidates at L341–346 (6).
- § API surface — candidates 24 → rows #1621 (the whole 24-row table collapsed), #1578, #1622,
  #1623, #1624, #1625, #1626, #1627, #1628, #1629, #1630, #1631 (the exceptions the § API surface
  prose, § The three picks and § Open questions single out). Collapsed into #1621: all 24
  candidates at L363–386.
- § MP behaviour — candidates 12 (10 table rows, 2 paragraphs) → rows #1619, #1620, #1627,
  #1632, #1633, #1634, #1635, #1636, #1637, #1638, #1639, #1640. The table is not collapsed: its
  ten rows carry ten different mechanisms on ten different pointers and four different grades, so
  it is not dataset-shaped. Dropped: 2 (the "item modData moves wholesale" row and the
  "`SyncItemFieldsPacket` carries condition and modData but not `conditionMax`" row are restated
  here from `docs/vanilla/food-item-model.md` § MP behaviour and
  `docs/mods-survey/teardowns/itemquality.md`, which own them — this page adds no pointer of its
  own to either).
- § The three picks — candidates 8 → rows #1641, #1642, #1643 (the 3-row picks table, one
  `verdict` row each), #1644, #1645; dropped: 4 (the domain-relevance ranking paragraph and the
  three fall-through entries are selection process; the "script data is parsed identically on
  both sides and never synced" clause inside criterion (4) is restated from the vanilla loader
  docs and is owned by `platform/loader-and-scripts.md#per-side-load`).
- § Discrepancies — candidates 9 (each a dated-correction site, so the table is not collapsed) →
  rows #1646 (-> #1647), #1650 (-> #1555), #1651 (-> #1591),
  #1652 (-> #1623), #1654 (-> #1594), #1655 (-> #1657), #1658 (-> #1571), #1661 (-> #1552,
  #1568) as the eight `superseded` old statements, plus their current statements and the facts
  each correction carries: #1647, #1648, #1649, #1653, #1656, #1657, #1659 (the `C vs W`
  three-part-folder cell as one `contradiction` row), #1660, #1571, #1594, #1623.
- § Open questions — candidates 12 → rows #1610, #1647, #1649, #1662, #1663, #1664, #1665, #1666,
  #1667, #1668, #1669, #1670, #1671, #1672, #1673, #1674; unverified: none; open: #1664, #1668,
  #1671; dropped: 0. Q1's `Translator` exception and Q4's 43/39 packet-field reconciliation are
  restated inside candidates that are harvested for their other clauses; both are owned by
  `docs/mods-survey/teardowns/autocook.md` § Architecture and
  `docs/vanilla/food-item-model.md` § MP behaviour and carry no row of their own here.
- § Sources — candidates 0 → rows: none (the section is a source list; its stamps are carried in
  the `bound` of the rows that quote each dataset and run).

### docs/mods-survey/approved-modlist.md

- § The approved modlist — inventory & tiering (the page preamble) — candidates 0 → rows #1551,
  #1552, #1553, #1554, #1661 (the old class distribution, `superseded`).
- § Curation quality — the bar our mod must meet — candidates 0 → rows #1565, #1566, #1567.
- § Domain overlap — mods already touching nutrition/food APIs — candidates 0 → rows #1555,
  #1556, #1557, #1563, #1582, #1583, #1584, #1585, #1587, #1588, #1589, #1590. The 19-row overlap
  table is the join of the two sweep tables `nutrition-mods.md` carries, so it adds no `table`
  row of its own; its `Why it matters to us` column is the per-mod verdict set above.
- § Teardown queue (updated) — candidates 0 → rows #1617; dropped: the queue state ("the queue is
  empty as of 2026-09-11", the future-picks order, the done list) is process bookkeeping.
- § Heavy-lua landscape (top by `lua_kb`, 2026-09-10) — candidates 0 → rows #1569.
- § Event usage across the corpus (hooks / distinct mods, 2026-09-10) — candidates 0 → rows
  #1568 (the top-12 census as one `count` row, its `top_events` floor in the bound), #1620. The
  "Read:" paragraph's three readings restate the same census and carry no separate row.

### docs/mods-survey/README.md

- § Mod survey (the page preamble) — candidates 0 → rows: none (a two-tier description of the
  survey, narrative).
- § Teardowns — candidates 0 → rows #1617, #1641, #1642, #1643; dropped: the five-row queue table
  and the queue-exhausted paragraph are process text, and each teardown's measured outcome is
  owned by its own page under `docs/mods-survey/teardowns/`.
- § Lint gate for this directory — candidates 0 → rows #1675.
- § Leads still open after the slice-08 catalog pass — candidates 0 → rows #1605, #1606, #1608,
  #1674; dropped: the "known adjacent from our sessions" list (damnlib, ChuckleberryFinn mods,
  Elyon Lib, MoodleFramework) names no measurement and no count.

## Pointer forms used

`data:` for a whole-file corpus count off `data/mod-inventory.json` · `mod:` for a shipped
workshop file, tree-qualified and with each space written `%20` (R19; `#1584` is the only row
that needs it) · `repo:` for this repository's tools and datasets · `jar:` for the five jar sites
the source names under § Open questions 1 and the two `searchForModInfo` readings · `run:` for
the five cited runs · **`web:`** for the two fetched Steam metadata snapshots
(`data/workshop-search.json` 2026-09-10, `data/workshop-catalog-details.json` 2026-09-10 — 16
pointers, grade W, R18) · `wiki:` for the two true mirrors only (`lua-event.md` on `#1620`,
`mod-structure.md` on `#1659`).

## Anchors proposed

None. Every `owner` this part writes is a `page#slug` already in
`docs/superpowers/plans/restructure-anchors.md`: `facts/other-mods/catalog.md#{sweep, status,
api-surface, corpus-facts, walls, open}`, `reference/datasets.md#{mod-inventory, counts,
workshop-rows}`, `reference/tools.md#doc-lint`, `platform/harness.md#{profiles, probes, pzt}`,
`platform/mp-model.md#{ownership, player-moddata, wipe-and-replace, item-moddata}`,
`platform/mod-anatomy.md#{version-dirs, walls, open}`, `platform/lua-platform.md#events`,
`platform/loader-and-scripts.md#script-dsl`, `facts/wire-packets.md#{item-stats-packet, desyncs}`
and `areas/item-pass.md#walls`.

## Totals

125 rows, `#1551`–`#1675`, contiguous.

By kind: `mechanism` 46 · `count` 38 · `verdict` 10 · `table` 9 · `rule` 6 · `tool` 6 · `bound` 6
· `open` 3 · `contradiction` 1.

By grade: `C` 104 · `W` 12 · `M` 9.

By status: `settled` 114 · `superseded` 8 · `open` 3 · `unverified` 0.

By owner page: `facts/other-mods/catalog.md` 85 · `reference/datasets.md` 12 ·
`platform/mod-anatomy.md` 5 · `platform/harness.md` 5 · `platform/mp-model.md` 4 ·
`facts/wire-packets.md` 2 · `areas/item-pass.md` 1 · `platform/loader-and-scripts.md` 1 ·
`platform/lua-platform.md` 1 · `reference/tools.md` 1 · (blank, the 8 `superseded` rows) 8.

Candidates accounted for: **152 = 87 collapsed + 53 harvested + 12 dropped + 0 unverified.**

- **Collapsed into a `table` row, 87**: § Sweep 1 22 (into #1573 and #1574) · § Sweep 2 9 (into
  #1591) · § Sweep 3 17 (into #1597 and #1601) · § B42 status 15 (into #1609 and #1616) ·
  § API surface 24 (into #1621). That is the brief's "sweep and status tables (87 rows)", of
  which the 24-row API-surface table is one.
- **Harvested directly, 53**: § Summary 3 · § Method and scope 4 · § Sweep 2 3 · § Sweep 3 5 ·
  § B42 status 3 · § MP behaviour 10 · § The three picks 4 · § Discrepancies 9 · § Open
  questions 12.
- **Dropped, 12**: the 3 page-preamble legend lines (legend, no rows) · 3 § Summary items that
  § MP behaviour, § Sweep 3 and § The three picks restate in full · 2 § MP behaviour rows whose
  mechanism is owned by `docs/vanilla/food-item-model.md` § MP behaviour and
  `docs/mods-survey/teardowns/itemquality.md` · 4 § The three picks selection-process paragraphs.

Rows minted beyond one per harvested candidate are the named exceptions the prose singles out on
a collapsed table (procedure § 3) and the current statements the eight `superseded` rows point
at; no `table` was exploded into rows.
