# Wiki mirror — Modding (hub page) — archived excerpt

**Source:** https://pzwiki.net/wiki/Modding
**Fetched:** 2026-09-13 as stated in the original excerpt (page last edited 2026-09-03); archived 2026-09-09
**Wiki page version:** 42.20.4 (the page's own "revised for the current stable version" note at the time)
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

_Archived, not live: superseded by [modding.md](modding.md) (verbatim wikitext mirror, 2026-09-09). Kept because the page's "42.20.x modding news" section (loadstring removal and the security fixes behind it, sync-API additions) is no longer on the live page — the drift this mirror set exists to preserve._

## Digest

Excerpt-style mirror (not verbatim) of the hub page as it read in early September 2026; the value is the 42.20.x news section below, which the live page has since dropped.

## 42.20.x modding news (as reported on the page)

- **`loadstring` REMOVED** following a public security report (Rasmus Moorats):
  three vulnerabilities — lua injection via `loadstring` (server→client
  arbitrary code), sandbox escape via `ZomboidFileSystem.updateScript`, and a
  `normalizeToPath` flaw allowing writes outside game directories. Mods/servers
  that shipped lua strings to clients must migrate.
- `getFileWriter` limited to extensions: ini, cfg, txt, log (+ json as of
  42.20.1); `getModFileWriter` NOT limited (noted on page as curious).
- New sync methods: `sendHitZombie` (immediately deprecated), faction ops
  (create/disband/invite/change-owner/tag/title/remove-member), foraging
  (`sendForageRequestZone`, `sendForagePool`, `sendForageSpot`).
- Two new Lua events: `RequestMedicalCheck`, `AcceptedMedicalCheck`.
- Newly exposed classes: `CraftRecipe.XpAward`, `StreetPoints`, `Transform`,
  `VirtualVehicle`, `WorldMapStreet`.
- `language.txt` → JSON (`language.json`); `%` must now be escaped (`%%`) in
  translations; new WorldGen lua under `media/lua/server/WorldGen`;
  `LuaTableUtil:insertAllUniqueElementsFromJavaList`; `drawTextWithBackground`
  for UI; ActionGroup modding appears to be landing (modded files load).
- **B42 MP unstable released with modding-migration instructions** ("applying
  the new networking changes to existing mods") — via *TIS Modding Guides*
  main article; copies hosted off-forum for those without TIS accounts.
  Last-updated stamp on that notice: 2025-12-11.

## Policy highlights

- TIS may implement any feature regardless of existing mods.
- Modders warrant their work is original/licensed; no paywalled mods or
  donor-exclusive content; commissions allowed (access can't be sold per-user).

## Hub structure — the sub-pages that matter to us

General: **Mod structure · Game files · File formats · Debug mode · Startup
parameters · Mod optimization · Procedural distributions · PZ API
Documentation** · Getting started with modding.

Fields → key pages:
- **Scripts** (no-code item defs): ZedScripts (VSCode ext), ScriptsDocs in PZ
  API Documentation. Script types listed: craftRecipe, Evolvedrecipe, Fixing,
  Fluid, Item, Model, Multistagebuild, Recipe, Sandbox options, Sound,
  TimedAction, Vehicle.
- **Lua (API)**: VSCode + **Umbrella** (typestubs); Lua object · **Lua event** ·
  Java object · **JavaDocs** · LuaDocs · **Mod data** · Decompiling game code ·
  Remote debugging · Game time · Procedural distributions ·
  PersistentOutfitID.
- **Java**: Decompiling game code, IntelliJ IDEA (deep edits = manual java
  swaps; not workshop-distributable in the normal way).
- Mapping/Modeling/Animation/Translation: not our pillars (indexed on page).
- Modding resources row: App ID · **Food types** · **item tag** · **mod.info**
  · **Networking** · Startup parameters · Translation · workshop.txt ·
  Workshop ID · BBCode · Animation.

## Modding projects named on the page (candidate sources/tools)

Umbrella · **Unofficial JavaDocs (Build 42)** · LuaDocs · **PZEventDoc** ·
PZEventStubs · Starlit Library · TchernoLib · Elyon Lib (KBW's lib!) ·
DebugMenu · Easy Distributions API · Moodle Framework · Moodles in lua ·
Doggy's Library · FrameworkZ · Zomboid Decompiler · Beautiful Java ·
Project Zomboid Loot Analyzer · Zed Script · Community Modding template ·
Modix · Mod Update and Alert System · pzmap2dzi · LootZed · Pythoid · DOME ·
Leaf · Magazine API · SpawnerAPI · isoRangeScan (utility) · Wiki That!.

## External tutorials table (page-listed, with page's own dates)

- Sit-Down Sunday — modding presentations (PZ Modding Community, 2026-08).
- PZ Modding Video Guides — SimKDT (2026-03).
- PZ Modding Guides — Albion (2025-05).
- B42 "How to Create a Mod" — Rainmaker (2025-04, item creation).
- PZ Mod Documentation — MrBounty (2023-08).
- FWolfe's Modding Guide — inactive/partly outdated; good-practices section
  noted as still ahead of the wiki.
- Full start-to-finish item mod video — W. Patrick (2022-12).
- Vehicle modding tutorial — tubetarakan (2020, dated).

## Communities

Official TIS Discord (#mod_portal, Workshop category) · PZ Modding Community
Discord · Unofficial PZ Mapping Discord · Unofficial Cinematic Animation
Discord. Discord "Mod Resources" mega-thread (Glytch3r et al., 2025-07).
