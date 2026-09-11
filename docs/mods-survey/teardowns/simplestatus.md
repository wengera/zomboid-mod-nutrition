# Teardown: Simple Status (`simpleStatus`)

**Verified against: 42.20.4 (`b0bbce05d5`)** — mod read cold 2026-09-10 (no server), then
measured the same day on one dedicated-MP session with a real client:
`td2-20260910-231655` (acceptance `run-20260910-230752`).

- **Workshop ID / mod ID(s):** item **`2867431511`**, one mod, declared id **`simpleStatus`**
  (`42.16/mod.info:2`). The **folder** is `SimpleStatus` — a **case-only** drift from the id,
  which `mod_lint` reports as `folder-id` INFO (exit 0, `0 ERROR / 0 WARN / 1 INFO`,
  2026-09-10). Use the declared id in `Mods=`; `index["SimpleStatus"]` resolves on Windows only
  because path lookup is case-insensitive, which is exactly why this subject **cannot** settle
  the folder-rename question ([`../../testing/profiles.md`](../../testing/profiles.md)
  § Open questions 6). Workshop page (W): *[B41|B42] Simple Status*, 1.132 MB, posted
  Sep 25, 2022 @ 12:57am, **updated Apr 5 @ 5:37pm** —
  <https://steamcommunity.com/sharedfiles/filedetails/?id=2867431511>, fetched 2026-09-10 17:46
  into [`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json).
- **Build examined (date + version folder used):** **`42.16/`**, the newest of **four** version
  folders (`42.16`, `42.15`, `42.14`, `42`) and the one `mod_lint.media_root` resolves. Beside
  them the item ships an **empty** `common/` (the directory exists and holds **zero** files, so
  `info_chain` skips it) and a **root-level `media/`** — the flat B41 layout, 47 files, which
  42.20.4 never reads. `42.16/` itself is **62** files: 1 `mod.info`, **7** client Lua, **13**
  translation JSON, 41 PNG. Every one of the item's **298** files carries the mtime
  **2026-08-12 00:02** and the item directory **2026-08-12 00:03** — a single Steam *download*
  stamp, not an update history (`workshop_item_mtime 2026-08-12T00:03:07`); **1 132 005 B**
  total. Inventory figures below are `data/mod-inventory.json` at commit `9f551f6`, swept
  **2026-09-10 17:47**: `layout 42.16`, `lua_client 7`, `lua_kb 46`, **`script_item_blocks 0`**,
  `script_modules []`, `script_nutrition_keys {}`, `sandbox_options false`, and the six signals
  `food_nutrition 12`, `mod_data 4`, `transmit_mod_data 1`, `ui_panel 1`, `events_add 2`,
  `require_line 2`.
- **Author · dependencies · license/permissions posture:** **no author is declared** — there is
  no `author=` key in any of the five reachable `mod.info` files, and the inventory row reads
  `author: "?"`. `modversion=2.260406.1` (`42.16/mod.info:7`), the same string the mod carries
  in Lua at `42.16/media/lua/client/SimpleStatus.lua:4`; **no `versionMin`, no `pzversion`** (the
  file is 7 lines). **No `require=` line exists anywhere in the info chain** → empty dependency
  list, nothing to install beside it. The mod ships **no licence or readme file**, and the
  fetched Workshop record carries no licence field, so the posture is default Steam Workshop
  terms: **read it, do not vendor it.** Nothing here is copied into our mod; only patterns are
  taken.

Grades: **C** = code/script/jar reading (every one carries `path:line` or a jar dump), **M** =
measured on the run named in the cell, **W** = Workshop page. Mod-relative paths are relative to
`2867431511/mods/SimpleStatus/`; vanilla Java is cited as `Class.method @offset L<source line>`
from the 42.20.4 jar; vanilla Lua and scripts are relative to the game install.

## What it does (player-facing)

1. **A draggable bar panel of the player's status numbers**, one row per stat, built on
   `Events.OnCreatePlayer` and added to the UI manager (`42.16/media/lua/client/ss.main.lua:56-80,82`).
2. **36 stats on offer** (`ss.stats.lua`, 36 `table.insert(stats._values, …)` lines) — health,
   endurance, hunger, thirst, fatigue/rest, happy/unhappy, boredom, pain, panic, stress,
   sickness, anger, sanity, **proteins, calories, carbohydrates, lipids**, dirtiness/cleanliness,
   **weight**, weight capacity, body temperature, body heat generation, wetness, intoxication,
   poison, food sickness, zombie infection, zombie fever, nicotine withdrawal, fitness, morale,
   discomfort, idleness — of which **18 render by default** (18 explicit `shown = true`, 15
   explicit `false`; the 3 reversibles inherit their partner's at `ss.stats.lua:89,119,350` and
   are skipped as primaries by `ISSSBar.lua:146`).
3. **A right-click menu** toggling each bar's visibility, the three reversible pairs
   (fatigue↔rest, happy↔unhappy, dirtiness↔cleanliness), vertical/horizontal layout, the ruler
   ticks and the font size (`ISSSBar.lua:479-515`); two key binds (default `\` show/hide, `L`
   lock) come from `PZAPI.ModOptions` (`ss.options.lua:6-9`, `ISSSBar.lua:527-542`).
4. **Every choice is persisted into one player-modData key and transmitted**
   (`ISSSBar.lua:18-36`), so the panel returns where the player left it after a relog.
5. **It writes nothing else and owns nothing.** Every number it draws is read live off vanilla
   getters at render time. It is a viewer — and that is the whole reason it was picked: it is the
   read side of the same store [`longtermpreservation4220.md`](longtermpreservation4220.md)
   attacked from the write side.

## Architecture

**Files that matter** (`42.16/`, whole census 62 files, 2026-09-10). Unlike pass 1's subject
**every one of the seven Lua files ends with a newline**, so `wc -l` equals the last line number
and every citation below is a real line.

| File | Lines | Side | Role | Ev |
|---|---:|---|---|---|
| `42.16/media/lua/client/ss.stats.lua` | **708** | client | the 36 stat definitions; **all 12** nutrition reads | C |
| `42.16/media/lua/client/ISSSBar.lua` | **583** | client | the `SSBar` panel (an `ISPanel` derive, `:53`), the context menu, `savePlayerData` — the mod's only write | C |
| `42.16/media/lua/client/ss.utils.lua` | **122** | client | colours, fonts, text measurement | C |
| `42.16/media/lua/client/ss.main.lua` | **87** | client | config load, the two `Events.*.Add`, the three prints | C |
| `42.16/media/lua/client/SimpleStatus.lua` | **34** | client | the mod's **only** `_G` name: `SimpleStatus` (`:3`), with `isNewer` and `addStat` | C |
| `42.16/media/lua/client/ss.mods.compatible.lua` | **33** | client | **entirely commented out** — a returned no-op (`:5-33`) | C |
| `42.16/media/lua/client/ss.options.lua` | **13** | client | `PZAPI.ModOptions` key binds, `setup()` run at require time (`:11`) | C |
| `42.16/media/lua/shared/Translate/<13 langs>/IG_UI.json` | — | **shared** | the mod's only non-client files: **52** keys per language — 40 `IGUI_SS_BARTITLE_*`, 12 `IGUI_SS_OPT_*`, counted 2026-09-10 | C |

**Lua total: 1 580 lines over 7 files, all under `client/`** — `lua_client: 7` is the whole
`stats` block on the inventory row. **The mod is 100 % client.** There is no `lua/server/` file
in the live tree at all, so on a dedicated server it registers **nothing** and runs **no code**;
the only thing the server loads is the shared translation tree (measured — § MP handling, the
server-log census).

**No `media/scripts/` in any of the five media trees**, so `script_item_blocks: 0` is
structurally true rather than "not scanned": the mod ships no item, no recipe and no script block
of any kind, and there is no vanilla definition anywhere for it to collide with.

**Entry points — two, both client-only.**
`Events.OnCreatePlayer.Add(onCreatePlayer)` (`ss.main.lua:82`) builds the panel;
`Events.OnKeyPressed.Add(…)` (`ss.main.lua:83-87`) forwards keys to `SSBar:handleKey`.
`top_events` on the inventory row is exactly `[["OnCreatePlayer",1],["OnKeyPressed",1]]`.
`OnCreatePlayer` is client-only per
[`../nutrition-mods.md`](../nutrition-mods.md)`:411` (wiki-mirrored, W+C); `OnKeyPressed` appears
nowhere in [`references/wiki-mirrors/lua-event.md`](../../../references/wiki-mirrors/lua-event.md)
and is **not** covered by that row. The structural argument does not need it — there is no server
Lua to run under either event.

**Nothing is patched.** Every `function X:` in the tree is on the mod's own `SSBar` class (21
methods at `ISSSBar.lua:68,82,109,140,245,272,280,288,295,301,313,342,368,403,451,472,479,517,527,547,577`);
every `X.Y = function` is on its own `stats` table (`ss.stats.lua`, 59 sites) or on `utils.fn`
(`ss.utils.lua:109`). The four vanilla methods it calls — `ISPanel.prerender` (`:452`),
`ISPanel.onMouseUp` (`:474`), `ISPanel.onRightMouseUp` (`:519`), `ISPanel.initialise` (`:578`) —
are super-calls from overrides on the derived class, the sanctioned `ISPanel` idiom. **`_G`
footprint: one name**, `SimpleStatus` (`SimpleStatus.lua:3`); grepped across the whole installed
230-mod workshop corpus, the only files assigning it are this mod's own five copies of that file,
and **no other installed mod so much as mentions the name** (C, 2026-09-10).

**The render loop — per frame, uncached.** `SSBar:prerender()` (`ISSSBar.lua:451-470`) runs every
UI frame and calls `self:prepareBarInfo()` **unconditionally** at `:464`. `prepareBarInfo`
(`:140-243`) calls `bar.valueFn(self.player)` at `:171`, then `percentFn` / `textFn` / `colorFn`
at `:236-238` — and for the nutrition bars those closures call `valueFn` **again**
(`ss.stats.lua:241,252,266,387,401`), so a single frame issues **up to four**
`player:getNutrition()` round trips per visible nutrition bar. Nothing is cached: the only timer
in the file (`:453-457`) throttles `adjustWindowSize` to one frame in 60, never the value read.
This is the answer to [`../../modding/patterns.md`](../../modding/patterns.md) § Open pattern
questions' cadence question, and it is an **anti-pattern**, not a technique (§ Pitfalls 1).

**Data model — one modData key and nothing else.** `player:getModData()["SimpleStatusConfig"]`
holds a **flat table of scalars** built in `savePlayerData` (`ISSSBar.lua:18-36`):

| Leaf | Type | Written at | Read at | Ev |
|---|---|---|---|---|
| `SS_pos_x`, `SS_pos_y` | number | `ISSSBar.lua:20-21` | `ss.main.lua:27-29` | C |
| `SS_locked` | boolean | `:22` | `ss.main.lua:30` | C |
| `SS_fontSize` | string (`Small`/`Medium`/`Large`) | `:23` | `ss.main.lua:20` | C |
| `SS_isVertical`, `SS_isRulerOn` | boolean | `:24-25` | `ss.main.lua:23-24` | C |
| `SS_shown_<stat>` ×36 | boolean | `:26-28` | `ss.main.lua:34-41` | C |
| `SS_tog_fatigue`, `SS_tog_happy`, `SS_tog_dirtiness` | boolean | `:29-31` | `ss.main.lua:45-47` | C |

A fully-populated `SimpleStatusConfig` is **45 leaves** (6 + 36 + 3), every one of a type the
wire carries (§ MP handling). Beyond it: **no sandbox options** (no `sandbox-options.txt`
anywhere in the item, 0 `SandboxVars.` hits), **no command bus** (0 `sendClientCommand` /
`sendServerCommand` / `OnClientCommand` / `OnServerCommand`), and **no global ModData in the live
tree**. Mod options exist but are client-local: `PZAPI.ModOptions:create("simpleStatus", …)` with
two `addKeyBind`s (`ss.options.lua:6-9`), called at **require** time (`:11`) with no
`getActivatedMods():contains` guard and no `pcall` (§ Pitfalls 4).

**Version history — the architecture moved, and `42.15` is where.**

| Folder | Lua files | Lua lines | Config store | Ev |
|---|---:|---:|---|---|
| root `media/` (B41 flat) | 7 (incl. `ss.json.lua`, 388 lines) | 1 820 | — (B41 tree, not read this pass) | C |
| `42/`, `42.14/` | 9 (incl. `client/ss.events.lua` **and `server/ss.save.config.lua`**) | 1 671 | **global** `ModData.getOrCreate("SimpleStatusConfig")` + `ModData.transmit`, with an `OnInitGlobalModData` / `OnReceiveGlobalModData` pair at `42.14/media/lua/server/ss.save.config.lua:30-53` and the client half at `42.14/media/lua/client/ss.events.lua:1-15`, `42.14/media/lua/client/ISSSBar.lua:33-38` | C |
| `42.15/` | 7 | 1 582 | **per-player** `player:getModData()` — the server file and `ss.events.lua` both gone | C |
| **`42.16/` (live)** | 7 | **1 580** | per-player; adds a 13th (`PT`) translation tree | C |

The drop of `lua/server/ss.save.config.lua` happened at **`42.15`**, not at `42.16` as the
template plan's worked example says (`42.15/` has no `lua/server/` directory at all). The
consequence matters for anyone probing this mod: the name `SimpleStatusConfig` exists in **two
incompatible stores** across its history — a *global* table keyed by username (42 / 42.14) and a
*per-player* modData key (42.15 / 42.16) — and a census of the global one is
**non-discriminating in both directions**, because `ModData.getOrCreate` creates the table for
the census itself and the old server half only ever created it **empty**
(`42.14/media/lua/server/ss.save.config.lua:43-49`). Measured and recorded as metadata, not as a
control: `keyCount 0` on both sides (M — `td2-20260910-231655`,
`snapshots[0].{client,server}.moddata_global`).

## MP handling

**Where authority lives: entirely on the server, and the mod knows it.** simpleStatus has **no
networking of its own** — 0 command-bus sites, 0 `sendItemStats`, and no server Lua to run any.
Its whole MP contract is two vanilla mechanisms it consumes:

1. **Inbound:** the 1 Hz `PlayerStatsPacket`, which carries `Nutrition.save`'s **five floats and
   nothing else** — `@0-@8 L209` calories, `@9-@17 L210` proteins, `@18-@26 L211` lipids,
   `@27-@35 L212` carbohydrates, `@36-@45 L213` weight (as a **`d2f`-narrowed float**, widened
   back by `load @32-@38 L221`'s `f2d`). There is **no flag byte** (C). `PlayerStatsPacket.write
   @19-@32 L34` is the `Nutrition.save` call; `@33` already belongs to `L35`.
2. **Outbound:** one `player:transmitModData()` (`ISSSBar.lua:35`), fired from **seven**
   UI-input-driven call sites (`ISSSBar.lua:274,282,290,297,307,476,540`), each of which rewrites
   the server's **whole** copy of that player's modData from the client's.

Everything below is one live dedicated server plus one real client, same character (`getUsername`
`admin` on both sides at every snapshot), run **`td2-20260910-231655`** — 167.8 s wall,
`server_error_count 0`, `client_lua_error false`, no `error` key, `session_ready` at 75.4 s.

**How a cross-side row is graded here, and why it is not pass 1's rule.** The two sides of a
snapshot are separate bus round trips ~1–3 s apart and **the server's copy is moving between
them**: `Nutrition.update @42-@45 L75` jumps past all four decays and `updateCalories` on a
client, so the client is a **staircase** that steps only when a packet lands while the server is
a **ramp**. The gap is therefore a **timing** reading, not float noise, and "equal" is the wrong
verdict to look for. Each snapshot is graded against a band computed from **its own** signed read
skew — `δ_min = t_srv_before − t_cli_after`, `δ_max = t_srv_after − t_cli_before`, band
`[r·δ_min, r·(δ_max + 1 s)]` for a decaying macro, the sorted `[−ρ·(δ_max + 1 s), −ρ·δ_min]`
widened by one float32 ulp (7.63e-6 kg at 80 kg) for weight — with the driver reading the
**client half first** at every tag so `δ ≥ 0`. A reading outside its band is a finding, not a
re-run. `r` is derived from the fixture's own clock (`DayLength 4` = 90 **real** minutes per game
day → 16.0 game-seconds per real second) and corroborated by the session's own slope (below).

| tag | client read (wall) | server read (wall) | δ_min | δ_max | since last write | graded | Ev |
|---|---|---|---:|---:|---:|---|---|
| `baseline` | 75.638–76.146 | 78.431–78.687 | 2.285 | 3.049 | — | **band** | M — `td2-20260910-231655`, `grades[0]` |
| `t0` | 87.525–88.035 | 89.556–89.813 | 1.521 | 2.288 | 1.278 | latency, **not** a band test | M — `grades[1]` |
| `t+3s` | 93.597–94.108 | 95.642–97.154 | 1.534 | 3.557 | 7.350 | **band** | M — `grades[2]` |
| `t2+0s` | 104.475–104.982 | 106.506–107.265 | 1.524 | 2.790 | 1.275 | latency, **not** a band test | M — `grades[3]` |
| `t2+3s` | 111.054–111.563 | 113.095–115.106 | 1.532 | 4.052 | 7.854 | **band** | M — `grades[4]` |
| `final` | 150.008–150.769 | 152.042–153.051 | 1.273 | 3.043 | 46.808 | **band** | M — `grades[5]` |

A snapshot taken inside a write's push window is an **arrival-latency** reading by rule
(`tolerance.settle_rule`, 1.5 s), so `t0` and `t2+0s` are reported but **ungraded**; both landed
inside their bands anyway. `t+3s` / `t2+3s` are nominal names — the settle sleep is
`max(0, 3 s − elapsed)` and the poll plus the snapshot already exceed it, so they sit at +7.35 s
and +7.85 s; the grading uses each snapshot's own `since_last_write`.

### The five numbers the mod draws, both sides, every snapshot

Gap is **client − server**. `r` is the field's decay rate per real second at this fixture; for
weight it is the signed `ρ` computed from that snapshot's own arm and calories, never a ceiling.

| tag | field | server | client | gap | band | in band | Ev |
|---|---|---|---|---|---|---|---|
| `baseline` | calories | 798.3768920898438 | 799.2306518554688 | 0.853759765625 | [0.58496, 1.036544] (r 0.256) | **yes** | M — `td2-20260910-231655`, `grades[0].macros` |
| | carbs | −0.35502830147743225 | −0.16830335557460785 | 0.1867249459028244 | [0.12796, 0.226744] (r 0.056) | **yes** | M — same key |
| | lipids | −0.11462342739105225 | −0.054337941110134125 | 0.06028548628091812 | [0.0413128, 0.0732059] (r 0.01808) | **yes** | M — same key |
| | proteins | −0.08723551779985428 | −0.04135453701019287 | 0.04588098078966141 | [0.0314416, 0.0557142] (r 0.01376) | **yes** | M — same key |
| | weight | 80 | 80 | 0 | [−7.63e-06, +7.63e-06] (ρ 0, neither arm) | **yes**, bit-identical | M — same key |
| `t0` | calories | 1999.052978515625 | 1999.7698974609375 | 0.7169189453125 | [0.389378, 0.841732] | yes (ungraded: latency) | M — `grades[1].macros` |
| | carbs | −0.9847724437713623 | −0.8281469941139221 | 0.15662544965744019 | [0.085176, 0.184128] | yes (ungraded) | M — same key |
| | lipids | −0.3179408013820648 | −0.26737314462661743 | 0.05056765675544739 | [0.0274997, 0.059447] | yes (ungraded) | M — same key |
| | proteins | −0.24197259545326233 | −0.20348750054836273 | 0.0384850949048996 | [0.020929, 0.0452429] | yes (ungraded) | M — same key |
| | weight | 80.00038421184581 | 80.00009155273438 | **−0.00029265911143738776** | [−0.00034942, −0.00015048] (ρ +1.0395e-4, gain ×1) | yes (ungraded) | M — same key |
| `t+3s` | calories | 1997.18310546875 | 1998.2333984375 | 1.05029296875 | [0.39271, 1.16661] | **yes** | M — `grades[2].macros` |
| | carbs | −1.3930763006210327 | −1.16377592086792 | 0.2293003797531128 | [0.085904, 0.255192] | **yes** | M — same key |
| | lipids | −0.449764609336853 | −0.37573328614234924 | 0.07403132319450378 | [0.0277347, 0.0823906] | **yes** | M — same key |
| | proteins | −0.3422987163066864 | −0.28595632314682007 | 0.05634239315986633 | [0.0211078, 0.0627043] | **yes** | M — same key |
| | weight | 80.00114177246815 | 80.00071716308594 | **−0.0004246093822075636** | [−0.00048089, −0.00015168] (ρ +1.0385e-4, gain ×1) | **yes** | M — same key |
| `t2+0s` | calories | 1994.6201171875 | 1995.414794921875 | 0.794677734375 | [0.390159, 0.970276] | yes (ungraded) | M — `grades[3].macros` |
| | carbs | 799.7754516601562 | 799.9495239257812 | 0.174072265625 | [0.085344, 0.21224] | yes (ungraded) | M — same key |
| | lipids | −0.6303383708000183 | −0.574343204498291 | 0.055995166301727295 | [0.0275539, 0.0685232] | yes (ungraded) | M — same key |
| | proteins | −0.4797268807888031 | −0.4371109902858734 | 0.04261589050292969 | [0.0209702, 0.0521504] | yes (ungraded) | M — same key |
| | weight | 80.0030074610022 | 80.00204467773438 | **−0.0009627832678233972** | [−0.00118693, −0.00046658] (ρ +3.1116e-4, gain ×3) | yes (ungraded) | M — same key |
| `t2+3s` | calories | 1992.5694580078125 | 1993.6204833984375 | 1.051025390625 | [0.392219, 1.2934] | **yes** | M — `grades[4].macros` |
| | carbs | 799.3273315429688 | 799.5572509765625 | 0.22991943359375 | [0.085792, 0.282912] | **yes** | M — same key |
| | lipids | −0.7747547030448914 | −0.7007291913032532 | 0.07402551174163818 | [0.0276986, 0.0913402] | **yes** | M — same key |
| | proteins | −0.5896369814872742 | −0.5332988500595093 | 0.05633813142776489 | [0.0210803, 0.0695155] | **yes** | M — same key |
| | weight | 80.0054916049794 | 80.00421905517578 | **−0.0012725498036161298** | [−0.001578, −0.00046858] (ρ +3.1084e-4, gain ×3) | **yes** | M — same key |
| `final` | calories | 1982.8211669921875 | 1983.617431640625 | 0.7962646484375 | [0.325958, 1.03523] | **yes** | M — `grades[5].macros` |
| | carbs | 797.1956176757812 | 797.3696899414062 | 0.174072265625 | [0.071288, 0.226408] | **yes** | M — same key |
| | lipids | −1.4610061645507812 | −1.4050037860870361 | 0.05600237846374512 | [0.0230158, 0.0730974] | **yes** | M — same key |
| | proteins | −1.111916422843933 | −1.0692952871322632 | 0.04262113571166992 | [0.0175165, 0.0556317] | **yes** | M — same key |
| | weight | 80.01726107890681 | 80.01630401611328 | **−0.0009570627935318043** | [−0.00125821, −0.00038614] (ρ +3.0932e-4, gain ×3) | **yes** | M — same key |

**Reading.** On all four macros and on **all six** snapshots — including the two the settle rule
declined to grade — the client is a staircase behind a ramp by **exactly** the amount one read
skew plus one push window explains. Nothing is out of band (`summary.out_of_band` is four empty
lists), so **the five numbers simpleStatus draws are the server's, late by under a second, and
there is no unsynced-field authority hazard in this mod at all.** The contrast with pass 1 is the
point of the pair: LTP writes fields the packet does not carry and its client is permanently
wrong; simpleStatus reads only fields the packet does carry and its client is merely *behind*.

**Weight's gap is NEGATIVE at every post-action snapshot** — the opposite sign to the macros' —
and that is `updateWeight`'s `GameClient.client` skip (`@317-@320 L198`) **measured** rather than
read: the client never recomputes weight, so its staircase sits *below* a rising server. Two
readings fall out of the widened float rendering (§ Sources, the `291f977` note): the **client's**
mirrored weight is exactly float32-representable at **6 / 6** snapshots (`80`,
`80.00009155273438`, `80.00071716308594`, `80.00204467773438`, `80.00421905517578`,
`80.01630401611328`) while the **server's** is not at **5 / 5** drifted readings — the `d2f`/`f2d`
narrowing on the wire, visible directly. `Nutrition.getWeight()` is a `D`; the wire is an `F`
(M — `td2-20260910-231655`, `grades[].macros.weight`; C for the two bytecode sites).

### The three weight-direction flags — the sharpest claim this mod supports

The mod's `+` / `++` / `-` suffix on the weight bar (`ss.stats.lua:404-411`, **7**
`getNutrition()` calls over four lines) is drawn from `isIncWeight` / `isIncWeightLot` /
`isDecWeight` — and **none of the three is in `PlayerStatsPacket`**. They agree anyway, because
the client recomputes them: `IsoPlayer.updateInternal2 @392-@402 L2306-L2307` calls
`nutrition.update()` gated **only** on `SystemDisabler.doCharacterStats`, `Nutrition.update
@106-@107 L81` calls `updateWeight()` on the client arm, and `updateWeight` sets all three flags
(`@129-@131 L167`, `@186-@188 L178`, `@222-@224 L181`, `@260-@262 L186`) **before** the
`GameClient.client` skip at `@317-@320 L198` reaches `setWeight` (C, jar).

| tag | server | client | arm the server's own macros predict | agree | Ev |
|---|---|---|---|---|---|
| `baseline` | F / F / F | F / F / F | neither (calories 798 ≤ gain 1000.0) | **yes** | M — `td2-20260910-231655`, `grades[0].flags` |
| `t0` | **T** / F / F | **T** / F / F | gain ×1 (calories 1999 > 1000.0154; carbs −0.98) | **yes** | M — `grades[1].flags` |
| `t+3s` | T / F / F | T / F / F | gain ×1 | **yes** | M — `grades[2].flags` |
| `t2+0s` | T / **T** / F | T / **T** / F | gain ×3 (carbs 799.8 > 700) | **yes** | M — `grades[3].flags` |
| `t2+3s` | T / T / F | T / T / F | gain ×3 | **yes** | M — `grades[4].flags` |
| `final` | T / T / F | T / T / F | gain ×3 | **yes** | M — `grades[5].flags` |

(`incWeight` / `incWeightLot` / `decWeight`; thresholds recomputed **per snapshot** from that
snapshot's own measured weight — `gainThreshold` climbed 1000.0 → 1000.69, `lossThreshold` 0.)
**So the mod's suffix is correct on an MP client**, which was the sharpest open claim in this
teardown and is now **M**. One caveat the run does not remove: both sides' `traitList` came back
**empty** at every snapshot (`traitRoute: getKnownTraits`, `traits_agree_across_sides` true 6/6),
so the agreement is measured on a character with **no weight-band traits**. The flag prediction
rests on both sides computing the same `gainThreshold`, which needs
`hasTrait(WEIGHT_GAIN)` / `hasTrait(WEIGHT_LOSS)` to agree — and **that** is body-stats open
question 10 ([`../../vanilla/body-stats.md`](../../vanilla/body-stats.md) § MP behaviour), which
this session advances only to "no disagreement on a character with no band traits", not to an
answer.

**Threshold correction, jar-dumped this pass:** `setIncWeightLot(true)` is set on **both** the ×3
arm (`updateWeight @156-@191 L176-L178`, carbs or lipids > 700) **and** the ×2 arm (`@194-@226
L179-L181`, > 400). The `++` suffix therefore appears from **400**, not from 700 — a correction
to the library wherever 700 is quoted alone (C, jar). This session exercised the 700 side only
(carbs 800); a probe at carbs 500 would measure the ×2 arm directly.

One reading worth keeping for anyone writing a probe: `nutrition.set`'s **own ack** carries the
flags **one tick stale** — the `calories 2000` ack reads `incWeight: false` beside
`calories: 2000`, because `updateWeight` has not run again yet (M — `t_action1.ack`).

### Arrival latency, and the decay slope

The driver polls the **client** between each write and the following snapshot, so these are
arrival bounds rather than artefacts of a snapshot's eight bus calls:

| write | ack at | client still old at | client shows new at | latency (upper bound) | Ev |
|---|---:|---|---:|---:|---|
| `nutrition.set admin calories 2000` | 86.247 | 86.248→86.507 and 86.507→87.013, both 796.4688720703125 | 87.013 (1999.7698974609375) | **0.766 s** | M — `td2-20260910-231655`, `arrivals[0]` |
| `nutrition.set admin carbs 800` | 103.200 | 103.202→103.458 and 103.458→103.965, both −1.7230076789855957 | 103.965 (799.9495239257812) | **0.765 s** | M — `arrivals[1]` |

Both bracket the 1 Hz `PlayerStatsPacket` window from above, and the "still old" reading at
+0.26 s brackets it from below. Over the session's longest write-free window (**38.947 s**,
`t2+3s` → `final`) the server's calories fell at **0.250296 kcal/real-s** against a derived
**0.2560552** — ratio **0.9775**, inside 10 %, so the derived `r` was used for every band and
`Thermoregulator.getEnergyMultiplier() ≈ 1` is corroborated to about 2 % (M —
`empirical_slope.longest`). Short windows scatter ±20 % and should not be quoted: ~6 s at
0.25 kcal/s is ~1.5 kcal against a quantised float32 store.

### The `transmitModData()` boundary — wipe-and-replace, measured

`savePlayerData` sends **every key in that player's modData**, not `SimpleStatusConfig`, and the
receiving side's table becomes **exactly** the sender's. The mechanism is vanilla, read off the
jar (C): `ObjectModDataPacket.write @8-@52 L42-L44` serialises the **whole** table;
`KahluaTableImpl.save @60-@123 L268-L275` silently drops any pair whose type byte is −1
(`getValueByte @0-@37 L430-L442`: String 0, Double 1, `KahluaTableImpl` **2**, Boolean 3 — so
nested tables *do* travel, functions and Java objects do not); `KahluaTableImpl.load @0-@6
L332-L333` **wipes before it rawsets**; `parse @126-@139 L76-L77` wipes the receiver outright if
the sender's table was empty; `IsoObject.transmitModData @0-@7 L4850-L4851` returns **silently**
if the player's square is null. Phase 2 turned the wipe half from C into M by planting a
server-only key first — which needed a new server-side `moddata.set` (§ Sources, `291f977`),
because the vanilla difference set is empty in the only direction that matters:

| moment | client keys | server keys | server-only | client-only | Ev |
|---|---|---|---|---|---|
| `p2a_baseline` (119.9 s) | 5: `fitnessMod`, `fitnessUpTimer`, **`hotbar`**, `strengthMod`, `strengthUpTimer` | 4: the same minus `hotbar` | — | `hotbar` | M — `td2-20260910-231655`, `phase2[0]` |
| `p2c` after the server plant (123.2 s) | same 5 | 5 (+ **`pzt_ss_server`**) | `pzt_ss_server` | `hotbar` | M — `phase2[1]` |
| `p2e` after the client plant (125.2 s) | 6 (+ **`pzt_ss_client`**) | 5 | `pzt_ss_server` | `hotbar`, `pzt_ss_client` | M — `phase2[2]` |
| `p2g0` after `moddata.transmit` (127.2 s) | 6 | **6 — identical to the client's** | — | — | M — `phase2[3]`, `wipe_reading` |
| `p2g3` +3 s (131.3 s) | 6 | 6 — identical | — | — | M — `phase2[4]` |

**`pzt_ss_server`, planted only on the server, is gone** from the server's census after the
client's `transmitModData()`, while `pzt_ss_client` **and** `hotbar` arrived
(`wipe_reading.server_key_wiped true`, `client_key_arrived true`,
`server_census_equals_client true`). So **any player-modData key the server holds and the
client's copy does not is destroyed the moment the player drags the SimpleStatus bar** — seven UI
actions, each a whole-table replacement. That is the mod's one real MP hazard, and it is now
**M** rather than inferred. It is the same failure shape as
`SyncItemFieldsPacket.processModData()` ([`../nutrition-mods.md`](../nutrition-mods.md)`:409`),
restated for the *player* object, and it generalises: the rule is in
[`../../modding/patterns.md`](../../modding/patterns.md) as FILTER 10.

**A census finding the static read did not predict, and it corrects a pass-1 number.** The
**server's** player modData is **empty at join**: `keyCount 0` at wall **79.194**, **91.074** and
**97.411** s, then **4** at **108.773** s — so the four vanilla fitness/strength keys are written
server-side **lazily**, between 97.4 and 108.8 s (22–33 s after `session_ready` at 75.4 s). Pass
1's "server 4 / client 5" is a *late-session* reading; early in a session it is **server 0 /
client 5** (M — `td2-20260910-231655`, `snapshots[].{client,server}.census_player`). The
conclusion it was used for is unaffected — the client is the superset either way, so the
difference set the wipe needs is empty without a planted key.

**`SimpleStatusConfig` was absent on both sides at every snapshot** — in `missing`, never in
`values`, for the top-level key and for all six dotted leaves (`SS_pos_x`, `SS_locked`,
`SS_fontSize`, `SS_isVertical`, `SS_isRulerOn`, `SS_shown_calories`) (M —
`snapshots[].{client,server}.config_key` / `config_leaves`). That is a positive statement, not a
gap in the probe: **a pure client-UI mod's persistent state is invisible to the command bus until
a human clicks**, because all seven writers are UI-input handlers
(`ISSSBar.lua:274,282,290,297,307,476,540`) and no bus command can synthesise a click or a key
press. Establishing that by construction is what let the `[[verify]]` tier question be answered
honestly (below).

### Controls carried on the same session

| Reading | Server | Client | Reading | Ev |
|---|---|---|---|---|
| `getInventoryWeight` | 1.1125000715255737 (2.1125001907348633 at `final`) | identical at every snapshot | the `weight_capacity` bar's numerator **does** cross, exactly — nothing in the library had recorded it | M — `td2-20260910-231655`, `grades[].fields` |
| `getMaxWeight` | 12 | 12 | its denominator; an `I`, so no band applies. `witness.fields` 12 = `bodySnapshot.maxWeight` 12 on both sides at all six snapshots, which is what proves the `TK.call` wrapper sound | M — `grades[].maxWeight_cross_check` |
| `isDead` / `isGodMod` | false / false | false / false | `Nutrition.update`'s two gates (`@13-@30 L68-L69`, `@31-@41 L71-L72`) recorded rather than assumed — **neither was exercised in its blocking state** | M — `grades[].fields` |
| `getUsername` | `admin` | `admin` | identity control: both sides are reading the same character | M — `grades[].fields` |
| trait list | `{}` route `getKnownTraits` | `{}` route `getKnownTraits` | agree at all six snapshots — see the flags caveat above | M — `grades[].traits` |
| `worldAge` | 2.3667 game-days at `baseline` | 2.3536 | the two world clocks have not diverged (each side's own clock, so it is a check, not a skew) | M — `grades[0].worldAge` |

### Did the mod load, and what does the server see of it?

**Tier (a), on the bus:** client `text.get IGUI_SS_BARTITLE_HAPPY` → `"Happiness"`,
`miss: false` — the mod's own value (`42.16/media/lua/shared/Translate/EN/IG_UI.json:7`). Vanilla
defines **zero** `IGUI_SS_` keys, and a translation **miss returns the key itself**
(`Translator.getTextInternal`, the `IGUI_` branch `@116-@138 L434-L435` → `@684-@685 L478` →
`@749-@750 L491`), of which `Happiness` is not a substring — so a mod-absent run cannot pass this
probe by echoing the key back (M — `td2-20260910-231655`, `verify[0]`; also
`run-20260910-230752`, provenance only).

**Tier (b), beside it:** the mod's three prints, in execution order, from the **client** console
(`testing/runs/td2-20260910-231655/clients/admin/console.txt`, gitignored; the committed reading
is `mod_log_lines`): `[SimpleStatus] Showing status bar for player: admin` (`ss.main.lua:62`,
line 3019), `[SimpleStatus] Loading config for player: admin` (`ss.main.lua:13`, reached from
`:72`, line 3020), `[SimpleStatus] Status bar created for player: admin` (`ss.main.lua:79`, line
3021). All three ⇒ the bar was built (`mod_log_reading.all_three true`,
`impossible_combination false`) (M).

**What the server loads.** The server log's mod grep returned **five** lines: `loading
simpleStatus`, then four `mod "simpleStatus" overrides media/lua/shared/translate/<lang>/ig_ui.json`
(`ch`, `cn`, `de`, `en`) (M — `mod_log_lines_server`). So the server **does** install and load
the mod's **shared translate tree** — the one part of it that is not client-only. The engine's
word "overrides" here is **file-level** (one line per shadowed file), not a key collision, and it
does **not** contradict the tier-(a) argument above: the client's `text.get` still answers the
mod's own value, and vanilla has no `IGUI_SS_` key to collide with. No mod Lua runs on the
server, because there is none to run.

**Folder metadata, and what it is not.** `<run>/server/mods/` is `["PZTestKit", "simpleStatus"]`
and `<run>/clients/admin/mods/` the same plus the two vanilla `*.txt` files; `mod.info` is at
`simpleStatus/42.16/mod.info` (M — `folder_check`). This is **not** an answer to the
folder-rename question: on NTFS `simpleStatus` and `SimpleStatus` are the same directory, and no
profile can reach `mods.install`'s name-keeping branch at all (every profile mod carries a
non-empty `src` — `testing/pzt/profile.py:190-196`, `:267-274`, `testing/pzt/harness.py:27-32`;
the fallback belongs to the plain non-`--profile` path, `testing/pzt/session.py:104`,
`testing/pzt/mods.py:71-82`). [`../../testing/profiles.md`](../../testing/profiles.md)
§ Open questions 6 stays **first half M, second half C**.

### Two pass-1 follow-up controls carried on this session — NOT simpleStatus findings

Both ride on the same run because it was cheap; neither is about this mod, which owns no item and
reads no item field. They are cited into
[`longtermpreservation4220.md`](longtermpreservation4220.md) and
[`../../modding/patterns.md`](../../modding/patterns.md) as dated cross-references, 2026-09-10.

**A1 — the vanilla display-name control.** `Base.FruitSaladClay` (absent from
`media/lua/shared/Translate/EN/ItemName.json`) and `Base.Steak` (present at `ItemName.json:4218`),
both spawned by RCON `additem`, read with the same six getters on both sides:

| item | side | `getDisplayName` | `getFullType` | `getActualWeight` | `getActualWeightUnmodded` | `isCustomWeight` | `getWeight` | Ev |
|---|---|---|---|---|---|---|---|---|
| FruitSaladClay | client | **`Base.FruitSaladClay`** | `Base.FruitSaladClay` | 0.7000000476837158 | **0** | false | 0.7000000476837158 | M — `td2-20260910-231655`, `appendix.A1.reads[0]` |
| FruitSaladClay | server | **`Base.FruitSaladClay`** | `Base.FruitSaladClay` | 0.7000000476837158 | **0** | false | 0.7000000476837158 | M — `appendix.A1.reads[1]` |
| Steak | client | `Steak` | `Base.Steak` | 0.30000001192092896 | 0.30000001192092896 | false | 0.30000001192092896 | M — `appendix.A1.reads[2]` |
| Steak | server | `Steak` | `Base.Steak` | 0.30000001192092896 | 0.30000001192092896 | false | 0.30000001192092896 | M — `appendix.A1.reads[3]` |

**Answer: hypothesis 1, inside vanilla.** An item with no `ItemName.json` entry reads
`getDisplayName() == getFullType()` and `getActualWeightUnmodded() == 0` (its guarded arm) on
**both** sides identically — exactly the symptom pass 1 saw on `Skittles.CuredPork`. So that
symptom needs no mod-specific explanation; hypothesis 2 ("mod translations not consulted on a
dedicated server") is **not required**, and both sides agreeing also rules out a sync
explanation. Hypothesis 3 — whether 42.20.4 ever loads a B41-layout `ItemName_EN.txt`
(`3774789651/mods/LongTermPreservation4220/42.20/media/lua/shared/Translate/EN/ItemName_EN.txt:3`)
— **stays open by design**: separating it needs a mod-tree write, which is out of scope here.
(The numbering here is the session's own, `appendix.A1.hypotheses`;
[`longtermpreservation4220.md`](longtermpreservation4220.md) lists the same three as (i) / (ii) /
(iii) in a different order, so match them by name, not by number.)

**A2 — does a server-spawned item's client copy tick?** Server `item.set admin Base.Steak heat
2.0`, then two client reads 10.5 s apart with a server read after each:

| read | wall | `getHeat` | `getCookingTime` | Ev |
|---|---:|---|---|---|
| client 1 | 138.729 | 2 | 0 | M — `td2-20260910-231655`, `appendix.A2.client_read_1` |
| server 1 | 138.984 | 2 | 0 | M — `appendix.A2.server_read_1` |
| client 2 | 149.242 | **1.697029948234558** | **0.1182333305478096** | M — `appendix.A2.client_read_2` |
| server 2 | 149.749 | **1.697029948234558** | **0.1182333305478096** | M — `appendix.A2.server_read_2` |

**The client's copy did NOT stay frozen** — both fields moved — and the two sides are
**bit-identical across a 0.5 s read offset**, during which an independently ticking copy would
have decayed further (heat falls ≈0.029/s here, in ≈0.01 quanta every ≈0.35 s). This **reopens**
pass 1's freeze row, and the session does **not** close it: two mechanisms remain, a
server→client push landing inside the window versus two copies ticking independently and
converging on the same float32. The reconciliation below is a **hypothesis with a named probe**,
not a finding:

> **Hypothesis (C, from the jar).** `Food.update` has no client guard and `updateTemperature`
> runs unconditionally, so a client copy *can* tick; and the push is
> `Food.update @86-@103 L377-L379` — `if (GameTime.getMinutes() != lastCookMinute) { if
> (GameServer.server != null) GameServer.sendItemStats(this); … }` — a server→client push once
> per **game minute** (≈3.75 real s at `DayLength 4`) **while the cooking branch is live**, gated
> at `@49-@71 L372-L373` on `isCookable && !isFrozen() && heat > 1.6f`. Pass 2's Steak never left
> that gate (2.0 → 1.697), so the push kept the sides bit-identical; pass 1's CuredPork **crossed**
> it (server 1.79561 → 1.39397 while the client pinned at 1.84703, same instance `#562521975`).
> Both readings are right and the discriminator is the **1.6 gate**.
> **The probe that separates them:** pin `heat 1.2` — below the gate — and read both sides twice
> 10 s apart. Carried as slice 11's session item; nothing here settles it.

`getContainer`, graded as **presence + within-side stability only**: present on both sides,
stable across both reads on both sides, type token `ItemContainer:[type:none,` on both. The full
strings differ exactly where the jar says they must (`parent:IsoPlayer{ … ID:5 }` on the client
against `ID:1` on the server), because `ItemContainer.toString() @0-@16 L3513` ends in
`IsoObject.toString() @42 L5982`'s per-JVM identity hash — so they must **never** be compared
across sides (M for presence/stability — `appendix.A2.container`; C for the two `toString`
routes).

## Techniques worth stealing

- **Derive a client-side indicator from packet-carried inputs instead of syncing it.** The `+` /
  `++` / `-` suffix (`ss.stats.lua:404-411`) draws three flags that are **not** on the wire, and
  it is right anyway because the engine recomputes them on the client from values that *are*
  (`Nutrition.update @106-@107 L81` → `updateWeight`, whose flag half sits **before** the
  `GameClient.client` skip at `@317-@320 L198`). Measured to agree on both sides at all six
  snapshots. **The technique is the dependency check, not the trick:** it holds only while every
  input is packet-carried, and here one of them — the weight-band traits — is **not** (body-stats
  open question 10). Write the dependency list down when you use this.
- **One modData key holding a flat table of scalars** (`ISSSBar.lua:18-36`), all four value types
  (string, number, boolean, nested table) chosen from the four `KahluaTableImpl.getValueByte`
  carries. Nothing in the mod's own payload is silently dropped on the wire — a property worth
  checking deliberately rather than discovering later.
- **Consume extension points; patch nothing.** `ISPanel:derive` plus super-calls, two vanilla
  event dispatchers, `PZAPI.ModOptions` for key binds — **zero** vanilla tables touched, zero
  script blocks, one `_G` name in the whole mod. The same clean shape pass 1's subject has, for a
  different reason: LTP adds content without redefining, simpleStatus renders without patching.
- **A registration API for third-party stats** (`SimpleStatus:addStat`, `SimpleStatus.lua:26-33`)
  — the right instinct for a UI mod, though this implementation has a defect (§ Pitfalls 5).
- **Translation keys as a load probe.** 52 keys in 13 language trees with a vendor prefix
  (`IGUI_SS_*`) that vanilla never uses gave this teardown its tier-(a) `[[verify]]` row when the
  mod had no other bus-readable state at all. A prefixed translation key is cheap, and it is
  evidence the mod loaded.

## Pitfalls / anti-patterns

1. **Per-frame, uncached reads of a server-owned store.** `prerender` → `prepareBarInfo`
   unconditionally (`ISSSBar.lua:464`), `valueFn` at `:171` and up to three more times per bar at
   `:236-238`, so **up to four `getNutrition()` round trips per visible nutrition bar per frame**
   against a store that only changes **once a second** (the `PlayerStatsPacket` cadence, measured
   here at 0.766 / 0.765 s arrival). **Rule: cache anything read from a pushed store at the push
   cadence, not the frame cadence — a 1 Hz source read at 60 Hz is 59 wasted reads out of 60.**
   The cost is client-side only and this mod is small, but our own UI will draw more numbers than
   36 and must not copy the shape. (C — a code reading; no shipped command measures frame time or
   Lua call counts, and adding one was out of scope.)
2. **`transmitModData()` from UI input, seven times over.** Each of the seven `savePlayerData`
   sites (`ISSSBar.lua:274,282,290,297,307,476,540`) replaces the server's **whole** copy of that
   player's modData with the client's, because `KahluaTableImpl.load` wipes before it rawsets —
   **measured** (§ MP handling). **Rule: never keep server-authoritative state in player modData
   on a server that also runs a client-side transmitter; and if you must transmit from a client,
   pull the server's copy first.** This is the FILTER row this teardown earns
   ([`../../modding/patterns.md`](../../modding/patterns.md) FILTER 10), and it is a *neighbour*
   hazard: the mod that loses data is not the one that called `transmitModData`.
3. **Hard-coded display bands that encode vanilla's balance.** Calories `{-2000, 1000, 3500}`
   (`ss.stats.lua:275`), carbs and lipids `{-500, 0, 1000}` (`:289`, `:303`), proteins' colour
   breaks at −300 / 50 / 300 / 700 (`:253-263`) and its `(x1.5)` / `(x0.7)` captions at 50…300 /
   ≤ −300 (`:243-247`). **Rule: a reader mod's thresholds are a copy of someone else's balance —
   if the numbers move, the colours lie, silently.** See § Compatibility notes: this one is
   pointed straight at us.
4. **A hard dependency executed at `require` time, unguarded.** `ss.options.lua:11` calls
   `setup()` — hence `PZAPI.ModOptions:create` — while `ISSSBar.lua:5` is still being resolved,
   with no `pcall` and no `PZAPI` nil-check. On a build without `PZAPI` the whole `require` chain
   (`ss.main.lua:3` → `ISSSBar.lua:5`) would take the mod down and **no events would register at
   all**. `PZAPI` is vanilla on 42.20.4, so this is latent, not live. **Rule: never do
   environment-dependent work at file-load time; do it on an event, behind a guard.**
5. **An extension API that silently breaks its caller.** `addStat(name, stat, reverse_stat)`
   writes `stats._reverse[name]` (`SimpleStatus.lua:30-32`), but `_reverse._values` was already
   built at file-load time (`ss.stats.lua:700-705`). A reverse registered later never reaches it,
   gets no context-menu toggle (`ISSSBar.lua:500`) and no `toggleStats` entry
   (`ss.main.lua:45`) — and worse, `prepareBarInfo:146` skips any name present as a key in
   `stats._reverse`, so the **primary** stat the extender paired it with **disappears from the
   bar**. Nothing in the 230-mod corpus calls `addStat`, so it has never fired. **Rule: if you
   ship a registration API, build the derived indexes lazily or rebuild them on registration —
   an API that only works before your own file finished loading is not an API.**
6. **Dead branches that look live.** `ISSSBar.lua:508` indexes `toggleStats` by
   `getReverseStat(name)` while `:148` and `:512` key it by the **primary** name, so `:508-510`
   never fires and the settings menu always labels the option with the primary name;
   `ss.main.lua:59-60` assigns a local from modData and never reads it (the real read is
   `loadPlayerConfig`'s own at `:15`, reached from `:72`); `ss.mods.compatible.lua:5-33` is a
   wholly commented-out function still called at `ss.main.lua:52`. All cosmetic, all recorded
   because they read like defects. A seventh oddity, **not** a defect: `sanity.type` is
   `"simple,positive"` (`ss.stats.lua:218`) while **seven** other positive bars carry the
   misspelling `"simple,postive"` (`:18,32,46,60,88,103,662`; 7 hits, grepped 2026-09-10) — inert, because the only test is
   `string.sub(_type, -8) == "negative"` (`ISSSBar.lua:182`).
7. **One global with no Lua definition.** `toInt(…)` (`ISSSBar.lua:352-353`) exists nowhere in
   the game's `media/lua/` — it is a Java-exposed global, reached only from `getHoverBar`, i.e.
   only in vertical mode with the mouse over the panel. Present on every B42 build this library
   has touched; it is the one name in the file with no Lua source to point at. **Rule: a global
   you cannot find a definition for is a version dependency you have not written down.**

## Compatibility notes

- **Load order is irrelevant to simpleStatus itself.** No `require=` in `mod.info`, no vanilla
  monkey-patching, no script blocks, no `_G` collision in the 230-mod corpus, and both its events
  are vanilla dispatchers. The only order-sensitive surface is **outbound**: a mod extending it
  must call `SimpleStatus:addStat` *after* `SimpleStatus.lua` has run and *before*
  `OnCreatePlayer`, because `ss.main.lua:34` snapshots `stats._values` at player creation — and
  even then, see Pitfalls 5.
- **API surface patched: zero.** It consumes four extension points (`Events.OnCreatePlayer`,
  `Events.OnKeyPressed`, `ISPanel:derive`, `PZAPI.ModOptions`) and replaces nothing. The server's
  own loader census agrees in the narrowest possible way: the only files it reports this mod
  shadowing are **its own** translation JSONs (four `overrides` lines, M — `mod_log_lines_server`).
- **The `transmitModData` blast radius is the real compatibility risk**, and it is measured
  (§ MP handling). Any mod keeping authoritative per-player state in `player:getModData()` on the
  **server** without pushing it to the client first loses it to the next SimpleStatus bar drag.
  That is a constraint on *our* design, not on this mod's: if our per-player nutrient state lives
  in player modData, it must exist on the client too, or a neighbour's UI will delete it.
- **CleanUI.** simpleStatus is the one teardown pick with a UI surface, and it does **not**
  replace any vanilla UI file — it adds an `ISPanel` of its own to the UI manager
  (`ss.main.lua:77`) — so CleanUI's replaced vanilla UI files have nothing to fight over. The
  only shared resources are screen space and the two default key binds (`\` and `L`), both
  user-rebindable through `PZAPI.ModOptions`.
- **The Girth stack.** 0 `sendClientCommand` / `sendServerCommand`, so no collision with its 228
  command sites (slice-08 catalog, 2026-09-10).
- **Collision with our own nutrition mod — it is a *viewer of exactly our numbers*.** The five
  getters at `ss.stats.lua:238,280,294,308,381` are the five fields an item-pass rebalance moves.
  Two consequences: (a) any change we make to the vanilla macro numbers is **immediately visible**
  to users through this bar, with no cooperation needed and no way to annotate it; and (b) its
  display bands are hard-coded (§ Pitfalls 3), so if we re-base the macro scale, this bar's
  colours and its two multiplier captions go wrong **silently**, on every client that has it
  installed. It is a UI neighbour whose calibration our mod can invalidate.
- **What a client-side reader gets right and wrong, from the pair of teardowns.** On *player*
  nutrition (this mod): everything it draws is right, late by under a second. On a *cooked item*
  (pass 1): `offAge`, `offAgeMax`, `isCookable`, `isCustomWeight` and `getThirstChange` are wrong
  on a client — see [`longtermpreservation4220.md`](longtermpreservation4220.md)
  § Compatibility notes. The split is the packet's field list, both times.
- **Not a dependency candidate.** `SimpleStatus:addStat` is a real extension point, but it has a
  defect (§ Pitfalls 5), no consumer exists in the corpus, the mod declares no author and no
  licence, and depending on a client-only viewer would give our mod nothing it cannot do itself.

## Verdict for our mod

**Not a dependency, not a conflict — the read side of our own problem, and a neighbour whose
calibration we can break without touching it.**

**Adopt:**

- **Derive client-side indicators from packet-carried inputs, with the dependency list written
  down.** The flags are the model: three values that never cross the wire and agree anyway
  because the engine recomputes them client-side from values that do. Our own UI can do the same
  for anything whose inputs are in `PlayerStatsPacket` — and must not, for anything whose inputs
  are not (the band traits are the live counter-example).
- **A prefixed translation key as a load probe.** Cheap, it survives having no scripts and no
  server state, and it is the only thing that gave this subject a tier-(a) `[[verify]]` row.
- **One flat modData key per concern, of wire-safe types.** Not the transmit style — the payload
  discipline.

**Avoid:**

- **Per-frame uncached reads of a 1 Hz store** (Pitfall 1). Cache at the push cadence.
- **Client-side `transmitModData()` on player modData holding anything but our own keys**
  (Pitfall 2). Either keep server-authoritative per-player state out of player modData, or make
  sure the client's copy is complete before any client transmits. Our own state must be safe
  against *someone else's* transmit, which is the half the measurement makes concrete.
- **Hard-coding thresholds that encode vanilla's balance** (Pitfall 3) — the failure we would
  inflict on this mod is the failure we would inflict on ourselves if our UI hard-codes the
  numbers our item pass moves.
- **Environment-dependent work at `require` time** (Pitfall 4), and **registration APIs whose
  derived indexes are built once at load** (Pitfall 5).

**Carry forward:** if we re-base the macro scale, simpleStatus's bands and its `(x1.5)` /
`(x0.7)` captions become wrong for every user running both. Decide explicitly whether that is
acceptable, document it, or ship values inside vanilla's existing bands — do not discover it from
a bug report. And the flags' hidden dependency (weight-band traits agreeing across sides) is
still open: body-stats open question 10 is the row to watch before anything of ours keys on a
weight band.

## Sources

**Measured run** (the `default` fixture, build 42.20.4, one dedicated server + one real client;
the full run directory stays local under the gitignored `testing/runs/`):

- **`run-20260910-230752`** — acceptance, `pzt run --profile teardown-simplestatus --hold 5`,
  `RESULT: PASS`, exit 0, the tier-(a) `text.get` probe `ok=True`, 95 s. **Provenance, not
  evidence:** its `report.json` is under the gitignored `testing/runs/`, so it is not checkable
  from a clone ([`../../decisions.md`](../../decisions.md), the slice-01 row: an **M** must be).
  The session re-ran the same probe itself, and that reading — `verify[0]` — is what this doc
  cites.
- **`td2-20260910-231655`** — the session. Artifact
  [`testing/artifacts/td2-20260910-231655/teardown-simplestatus.json`](../../../testing/artifacts/td2-20260910-231655/teardown-simplestatus.json)
  (105 267 B; 167.8 s wall; `server_error_count 0`, `client_lua_error false`), driver
  `testing/experiments/td2_simplestatus.py` at commit `7453580`, harness Lua at `291f977`
  (`harness_lua_dirty false`, `doctor_clean true`). Keys cited: `grades[]` (per-snapshot
  `macros` / `flags` / `fields` / `traits` / `weight_model` / `maxWeight_cross_check` /
  `worldAge`), `snapshots[]` (`census_player`, `config_key`, `config_leaves`, `moddata_global`),
  `steps[]`, `t_action1` / `t_action2` / `t_action3`, `arrivals[]`, `empirical_slope`,
  `phase2[]`, `wipe_reading`, `appendix.A1` / `appendix.A2`, `verify`, `mod_log_lines`,
  `mod_log_lines_server`, `mod_log_reading`, `folder_check`, `timeline`, `summary`.
- **`td2-20260910-231655` is the first artifact written under the widened float rendering.**
  Harness commit `291f977` replaced `TK.json`'s `string.format("%.6f", v)` with `tostring(v)`
  (Kahlua's `KahluaUtil.numberToString` → `Double.toString` for a non-integral double, an exact
  round trip; integers untouched), verified on this artifact's own bytes: **1 292 numbers
  scanned, 0 non-round-tripping**. **Every artifact before `291f977` — `td1`, `td1b` and the
  seventeen older runs — renders floats at six decimals** and supports no bit-level claim; the
  D→F→D weight evidence in § MP handling is obtainable only under the new rendering. Provenance,
  reading guides and the *do not cite* list:
  [`../../../testing/artifacts/README.md`](../../../testing/artifacts/README.md).
- **Profile:** `testing/profiles/teardown-simplestatus.toml` (harness + `[[mods]] id =
  "simpleStatus", workshop_id = "2867431511"`, **no `[sandbox]` block**). Committed at `a42c8b4`
  with `verify = []` (tier (b) — no tier-(a) probe existed **on the shipped bus**); the tier moved
  to **(a)** in `291f977`, which added the `text.get` row.
- **Harness commands this session depends on**, all added in **`291f977`** with
  [`../../testing/README.md`](../../testing/README.md) § Command bus updated in the same commit:
  the `tostring` float rendering; the three weight-direction flags in `TK.nutritionSnapshot`
  (`incWeight` / `incWeightLot` / `decWeight`, read through `TK.call`, so they appear in every
  `nutrition.get` and `stats.get` reply on both sides); a **server** `moddata.set <user> <key>
  <value>`; and a client `text.get <key>`. Earlier commands used here came from `37e411e` and
  `903ccaa` (slice 09).

**The mod itself** (read-only; `2867431511/mods/SimpleStatus/`, all 298 files stamped
2026-08-12 00:02): `42.16/mod.info`; `42.16/media/lua/client/{ss.main,ss.stats,ISSSBar,ss.utils,
SimpleStatus,ss.options,ss.mods.compatible}.lua`;
`42.16/media/lua/shared/Translate/EN/IG_UI.json` (and 12 more language trees); and for the
version history `42.14/media/lua/server/ss.save.config.lua`,
`42.14/media/lua/client/{ss.events,ISSSBar}.lua`, `42.15/`, `42/`, the root `media/`.

**Datasets:** [`data/mod-inventory.json`](../../../data/mod-inventory.json) — the `simpleStatus`
row (230 mod folders swept 2026-09-10 17:47, at `9f551f6`);
[`data/workshop-catalog-details.json`](../../../data/workshop-catalog-details.json) — the
`2867431511` result (fetched 2026-09-10 17:46, **W**).

**Vanilla (C, read 2026-09-10):** `media/lua/shared/Translate/EN/ItemName.json` (the A1 control
set — `Base.Steak` at `:4218`, `Base.FruitSaladClay` absent);
`media/scripts/generated/items/food.txt` (`Base.FruitSaladClay` at `:5702`, `Base.Steak` at
`:9774-9796`); `media/lua/client/PZAPI/ModOptions.lua`, `media/lua/shared/env.lua:1` (`round`)
for the vanilla globals the mod leans on.

**Engine (C, 42.20.4 jar dumps taken 2026-09-10):** `Nutrition.update @0-@107 L65-L81` (the three
gates and the client arm), `Nutrition.updateWeight @0-@320 L138-L198` (the thresholds, the ×3 and
×2 arms, the three flag writes and the `GameClient.client` skip), `Nutrition.save @0-@46
L209-L214` and `load @32-@38 L221` (the five floats and the `d2f`/`f2d` narrowing),
`PlayerStatsPacket.write @19-@32 L34`, `IsoPlayer.updateInternal2 @392-@402 L2306-L2307`,
`IsoObject.transmitModData @0-@41 L4850-L4859`, `ObjectModDataPacket.write @8-@52 L42-L44` /
`.parse @55-@139 L63-L77` / `.processServer @0-@25 L101`, `KahluaTableImpl.save @60-@123
L268-L275` / `.load @0-@6 L332-L333` / `.getValueByte @0-@37 L430-L442`,
`KahluaUtil.numberToString`, `Translator.getTextInternal @116-@138 L434-L435` and `@684-@750
L478-L491`, `Food.update @49-@103 L372-L379` (the cooking gate and the per-game-minute
`sendItemStats` push), `Food.updateTemperature`, `ItemContainer.toString @0-@16 L3513`,
`IsoObject.toString @42 L5982`, `InventoryItem.getActualWeightUnmodded`, `getDisplayName`,
`getContainer`.

**Neighbouring library docs:** [`../../modding/patterns.md`](../../modding/patterns.md)
(§ Measured MP sync facts — the `updateWeight` row this teardown extends, the contested
client-copy row, and FILTER 10, the transmit rule this teardown adds; § Open pattern questions —
the cadence question it closes), [`longtermpreservation4220.md`](longtermpreservation4220.md)
(the write side of the same store, and the two open questions this session's appendix touched),
[`../../vanilla/body-stats.md`](../../vanilla/body-stats.md) § MP behaviour (open question 10 —
the flags' unresolved dependency), [`../../vanilla/nutrition-core.md`](../../vanilla/nutrition-core.md)
(the decay rates the bands are derived from),
[`../nutrition-mods.md`](../nutrition-mods.md) (the catalog row for this mod),
[`../approved-modlist.md`](../approved-modlist.md) (the corpus and the queue),
[`../../testing/profiles.md`](../../testing/profiles.md) § Open questions 6 (the folder→id
rename — first half M, second half C; this subject cannot settle the second half),
[`../../testing/README.md`](../../testing/README.md) § Command bus (the four slice-10 harness
additions).
