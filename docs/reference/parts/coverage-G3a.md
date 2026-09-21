# Coverage part — G3a, the five teardowns

Sub-block `#1301–#1550`; rows written `#1301–#1543` (243), contiguous. Candidates: 228, generated
2026-09-21 by `python tools/claims_harvest.py candidates docs/mods-survey/teardowns/{autocook,
longtermpreservation4220,simplestatus,beyondten,itemquality}.md`. Every candidate is accounted for
below as harvested, collapsed into a `table` row, superseded, dropped or unverified.

Conventions used here: **collapsed** means the candidate's evidence-table row is carried verbatim
by a single `table` row (grain rule, procedure § 3); **dropped: legend** is the "Evidence grades:
**C** = …" line the paragraph matcher reports as a candidate; **dropped: provenance** is a
`## Sources` paragraph whose content is a run, artifact, driver or file list rather than a claim.

## docs/mods-survey/teardowns/autocook.md

- § Teardown: Auto Cook (`AutoCook`) — candidates 2 → rows #1301–#1303 (from the section's header
  bullets); dropped: 2 (`:42`, `:43` legend).
- § What it does (player-facing) — candidates 0 → rows #1304–#1305.
- § Architecture — candidates 0 → rows: none (the section is a heading; its content is the three
  sub-sections below).
- § The census — two media trees, and the mod is only whole across both — candidates 6 → rows
  #1306–#1309; collapsed into #1306: 5 (`:79`–`:83`, the two-media-tree census table); `:95` → #1309.
- § The merge rule — the headline, and it is now measured — candidates 8 → rows #1310–#1319;
  `:99` → #1310, `:155` → #1315, `:157` → #1340, `:158`/`:159` → #1316, `:194` → #1318,
  `:201` → #1319; dropped: 1 (`:156`, the M2 reading — it names neither merge direction, and the
  join-time modData fact it does carry is harvested at #1333).
- § Entry points — three, all client, and the two that matter live in `common/` — candidates 3 →
  rows #1320–#1324 (#1323 also serves § Techniques worth stealing, #1324 is the spawn-chain `order`
  row).
- § Data model — one nested modData key, and on a fresh character it is empty — candidates 8 →
  rows #1325–#1329; collapsed into #1325: 8 (`:254`–`:261`, the store/key table), with the four
  facts the prose singles out as #1326–#1329.
- § Client / server / shared split — no server presence is now measured — candidates 0 → rows
  #1330–#1331.
- § Version history — what `42.13/` actually changed — candidates 0 → row #1332.
- § MP handling — candidates 11 → rows #1333–#1340; `:331` → #1333, `:332` → #1334, `:333` → #1327,
  `:334` → #1338, `:335` → #1335, `:336` → #1336 + #1339, `:337` → #1337, `:338` → #1340,
  `:339` → #1331, `:340` → #1347 (§ The flags), `:341` → #1342 (§ The carrier).
- § The transmit, and what it means for a mod that never transmits — candidates 0 → row #1341.
- § The carrier — pass 1's freeze and pass 2's moving copy, reconciled — candidates 3 → rows
  #1342–#1346 and #1507; `:388`/`:389` (the two-side read pair) → #1342, `:394` → #1343.
- § The flags AutoCook actually gates on — agreement under the trivial arm, unsettled —
  candidates 0 → rows #1347–#1348 (#1348 `open`).
- § What else it reads that the server owns — candidates 7 → rows #1349–#1352; collapsed into
  #1349: 7 (`:440`–`:446`, the site/reads/owner table), with the two exceptions the prose singles
  out as #1350–#1351.
- § Techniques worth stealing — candidates 0 → rows #1353–#1357 (and #1323, shared with § Entry
  points).
- § Pitfalls / anti-patterns — candidates 2 → rows #1358–#1364; `:512` → #1358, `:555` → #1362.
  The eight numbered pitfalls are one row each; their **Rule:** imperatives are not written as
  separate `rule` rows here, because the same imperatives are the KEEP/FILTER entries of
  `docs/modding/patterns.md`, which is another group's source.
- § Compatibility notes — candidates 1 → rows #1365–#1377; `:648` → #1373 + #1374 + #1375 (open)
  + #1376 (superseded).
- § Verdict for our mod — candidates 1 → row #1378; `:689` → #1378.
- § Sources — candidates 3 → rows: none (provenance); dropped: 3 (`:752`, `:754`, `:762`).

Superseded in this file: #1370 (-> #1369), #1376 (-> #1373).
Open in this file: #1348, #1375. Unverified: none.

## docs/mods-survey/teardowns/longtermpreservation4220.md

- § Teardown: Long Term Preservation [42.20] (`SKITTLE_LongTermPreservation4220`) — candidates 2 →
  rows #1379–#1381 (from the section's header bullets); dropped: 2 (`:36`, `:37` legend).
- § What it does (player-facing) — candidates 0 → rows #1382–#1384.
- § Architecture — candidates 17 → rows #1385–#1394; collapsed into #1385: 6 (`:68`–`:73`, the
  file table); collapsed into #1390: 10 (`:102`–`:110`, the setter-versus-packet table);
  `:126` → #1393, `:130` → #1394.
- § MP handling — candidates 34 → rows #1395–#1435; the 22 field rows `:172`–`:193` become the
  per-field measured rows #1399–#1413 (offAge and offAgeMax are one row, #1401, being one reading
  off one comparison key), plus #1414–#1417 for the census and the who-ran-it readings beside them;
  `:225` → #1418, `:232` → #1419 + #1420, `:263` → #1421 + #1422, `:288` → #1423,
  `:303` → #1424 + #1425, `:306` → #1426, `:310` → #1428 (superseded) + #1429 + #1430 + #1431
  (superseded), `:369` → #1408 + #1409, `:377` → #1415, `:382`/`:383` (the modData census pair) →
  #1415, `:387` → #1432 + #1433 (superseded). #1434 and #1435 carry the section's closing latent-
  risk and instrument-limit paragraphs, which the matcher did not report as candidates.
- § Techniques worth stealing — candidates 4 → rows #1436–#1441; `:431` → #1436, `:438` → #1438,
  `:449`/`:451` → #1440.
- § Pitfalls / anti-patterns — candidates 1 → rows #1442–#1448; `:497` → #1446. Seven numbered
  pitfalls, one row each; their **Rule:** imperatives are left to `docs/modding/patterns.md`'s
  KEEP/FILTER rows as above.
- § Compatibility notes — candidates 7 → rows #1449–#1464; `:527` → #1450 + #1451 (superseded),
  `:543`/`:544` → #1450 + #1452, `:557` → #1457 + #1459, `:583` → #1453 + #1454,
  `:592`/`:593` → #1455 + #1456.
- § Verdict for our mod — candidates 0 → rows: none (the section restates § Techniques and
  § Pitfalls with no fact of its own).
- § Sources — candidates 7 → rows: none (provenance); dropped: 7 (`:637`, `:638`, `:681`, `:687`,
  `:693`, `:711`, `:712`).

Superseded in this file: #1428 (-> #1427), #1431 (-> #1430), #1433 (-> #1432), #1451 (-> #1450),
#1458 (-> #1457), #1460 (-> #1459) — the six dated corrections the brief names.
Open in this file: #1422, #1429, #1434, #1464. Unverified: none.

## docs/mods-survey/teardowns/simplestatus.md

- § Teardown: Simple Status (`simpleStatus`) — candidates 2 → rows #1465–#1468 (from the section's
  header bullets and the 2026-09-17 tree-drift note, #1466); dropped: 2 (`:55`, `:56` legend).
- § What it does (player-facing) — candidates 0 → rows #1469–#1472.
- § Architecture — candidates 21 → rows #1473–#1480; collapsed into #1473: 8 (`:93`–`:100`, the
  file table); collapsed into #1478: 6 (`:151`–`:156`, the config-leaf table); collapsed into
  #1479: 4 (`:170`–`:173`, the version-history table); `:89` → the bound of #1473, `:130` → #1476,
  `:141` → #1477.
- § MP handling — candidates 6 → rows #1481–#1482; collapsed into #1485: 6 (`:221`–`:226`, the
  per-tag read-skew table, which is the grading half of the band table below).
- § The five numbers the mod draws, both sides, every snapshot — candidates 30 → rows
  #1483–#1488; collapsed into #1485: 30 (`:241`–`:270`, the six-snapshot by five-field band
  table), with the two mechanism sentences it establishes as #1483 (the staircase against the
  ramp) and #1484 (weight's negative gap and the measured client skip).
- § The three weight-direction flags — the sharpest claim this mod supports — candidates 9 → rows
  #1489–#1492; collapsed into #1490: 6 (`:303`–`:308`, the per-tag flag table); `:299` → #1489,
  `:313` → the bound of #1490, `:325` → #1491.
- § Arrival latency, and the decay slope — candidates 2 → rows #1493–#1494; `:339`/`:340` → #1493.
- § The `transmitModData()` boundary — wipe-and-replace, measured — candidates 6 → rows
  #1495–#1498 and #1432; collapsed into #1496: 5 (`:368`–`:372`, the five-moment census table);
  `:380` → #1497.
- § Controls carried on the same session — candidates 6 → rows #1499–#1501; `:410` → #1499,
  `:411` → #1500, `:412`/`:415` → #1501; dropped: 2 (`:413` the username identity control and
  `:414` the trait-list control — both are carried as the bounds of #1490 and #1501 rather than as
  rows, since neither states a fact about the game).
- § Did the mod load, and what does the server see of it? — candidates 0 → rows #1502–#1506
  (#1505 superseded).
- § Two pass-1 follow-up controls carried on this session — NOT simpleStatus findings —
  candidates 10 → rows #1423, #1427 and #1507 (all three carry both this file and the file they
  are cited into as `source`); collapsed into #1427: 4 (`:480`–`:483`, the A1 display-name table);
  collapsed into #1423: 4 (`:502`–`:505`, the A2 two-read table); `:515` → #1423, `:537` → #1423.
- § Techniques worth stealing — candidates 0 → rows #1508–#1511.
- § Pitfalls / anti-patterns — candidates 0 → rows #1512–#1518, one row per numbered pitfall.
- § Compatibility notes — candidates 0 → rows #1519–#1523.
- § Verdict for our mod — candidates 0 → rows: none (the section restates § Techniques and
  § Pitfalls with no fact of its own).
- § Sources — candidates 4 → rows: none (provenance); dropped: 4 (`:727`, `:780`, `:782`, `:788`).

Superseded in this file: #1505 (-> #1504). Open: none. Unverified: none.

## docs/mods-survey/teardowns/beyondten.md

- § Teardown: Beyond Ten — Level 15 Skills — candidates 1 → row #1524; `:5` (every claim is a code
  reading, no run evidences any of it) is folded into the `C-only` bound carried by every row from
  this file.
- § What it does — candidates 0 → row #1525.
- § Architecture — the parallel-stat blueprint — candidates 0 → rows #1526–#1527.
- § MP handling — candidates 0 → row #1528.
- § Techniques worth stealing — candidates 0 → rows #1529–#1531.
- § Pitfalls — candidates 0 → row #1532.
- § Verdict — candidates 0 → rows: none (a summary of § Architecture and § Techniques).
- § Sources — candidates 1 → rows: none (provenance); dropped: 1 (`:72`).

Superseded: none. Open: none. Unverified: none.

## docs/mods-survey/teardowns/itemquality.md

- § Teardown: ItemQuality (Girth's Quest System module) — candidates 1 → row #1533; `:5` (every
  claim is a code reading plus an investigation in a separate repository) is folded into the
  `C-only` bound carried by every row from this file.
- § What it does — candidates 0 → row #1534.
- § Architecture — candidates 0 → rows #1535–#1536.
- § MP handling — the case study — candidates 0 → rows #1537–#1539.
- § Techniques worth stealing — candidates 0 → row #1540.
- § Pitfalls → rules for our mod — candidates 0 → rows #1541–#1542.
- § Verdict — candidates 0 → rows: none (a summary of § Techniques and § Pitfalls).
- § Sources — candidates 2 → row #1543; `:93` (the five mod folders the sweep finds against the
  header bullet's four) → #1543; dropped: 1 (`:78`, provenance).

Superseded: none. Open: none. Unverified: none.

## Candidate reconciliation

| file | candidates | harvested or collapsed | dropped |
|---|---:|---:|---:|
| `autocook.md` | 55 | 49 | 6 |
| `longtermpreservation4220.md` | 72 | 63 | 9 |
| `simplestatus.md` | 96 | 88 | 8 |
| `beyondten.md` | 2 | 1 | 1 |
| `itemquality.md` | 3 | 2 | 1 |
| **total** | **228** | **203** | **25** |

Dropped, by reason: 6 legend lines (two per big teardown; the short pair's stamp paragraphs are
folded into bounds instead of dropped), 16 `## Sources` provenance paragraphs, 1 reading that
names neither side of its own question (`autocook.md:156`), and 2 identity/trait controls carried
as bounds rather than as rows (`simplestatus.md:413`, `:414`). Unverified: 0 — every `run:`
pointer names a run with a folder under `testing/artifacts/`.

## Anchors proposed

None. All 81 distinct `page#anchor` owners used by this part already exist in
`docs/superpowers/plans/restructure-anchors.md`.

## Totals

By kind: `mechanism` 181 · `rule` 25 · `bound` 10 · `table` 10 · `count` 8 · `open` 6 · `tool` 2 ·
`order` 1 · `verdict` 0 · `contradiction` 0 — 243.

By grade: `C` 162 · `M` 78 · `W` 3 — 243.

By status: `settled` 228 · `superseded` 9 · `open` 6 · `unverified` 0 — 243.

By owner layer: `facts/` 174 (of which `facts/other-mods/` 132) · `platform/` 57 ·
`reference/` 3 · `areas/` 0 · none (superseded rows) 9 — 243. No row is owned by an `areas/`
page: a teardown states mechanisms and mod facts, and the nutrition-design reading of them is
Phase 3's.
