# External sources — annotated map

Status legend: ☐ not yet reviewed · ◐ skimmed · ● digested into docs (linked).
Every source gets a one-line "why we care" — delete rows that turn out empty.

## PZwiki — priority pages (hub mirrored: [modding-hub](../references/wiki-mirrors/modding-hub.md))

| Page | Why | Status |
|---|---|---|
| /wiki/Mod_structure | Mod anatomy → docs/modding | ☐ |
| /wiki/Game_files | Where everything lives on disk | ☐ (we know much of this empirically) |
| /wiki/File_formats | Script/tiles/bin formats | ☐ |
| /wiki/Lua_event | Full event list → hook inventory for nutrient ticks | ☐ |
| /wiki/Lua_object · /wiki/Java_object | API surface | ☐ |
| /wiki/Mod_data | modData = our parallel-stat store; sync semantics | ☐ HIGH |
| /wiki/Networking | MP model → every doc's "MP behavior" section | ☐ HIGH |
| /wiki/Item_(scripts) | Item script fields incl. food | ☐ |
| /wiki/Evolvedrecipe | Evolved recipe scripts (soups/salads pipeline) | ☐ HIGH |
| /wiki/Food_types | FoodType taxonomy | ☐ |
| /wiki/Item_tag | Tag system (we've mapped much of it in pz-b42) | ◐ |
| /wiki/Sandbox_options_(scripts) | Mod sandbox options (config surface) | ☐ |
| /wiki/TimedAction_(scripts) | Script-defined timed actions | ☐ |
| /wiki/Startup_parameters | **The automation surface** (+connect, -cachedir, -nosteam, server args) | ● [mirrored](../references/wiki-mirrors/startup-parameters.md) → testing design |
| /wiki/Debug_mode | Dev loop | ◐ (used -debug already) |
| /wiki/Testing_mods_in_multiplayer | Manual two-instance MP test procedure (B41-era page) — what we automate | ● digested into testing design |
| RCON: jar `zombie/network/RCONServer` + ServerOptions RCONPort/RCONPassword | Orchestrator's admin channel | ◐ protocol details in spike S1 |
| /wiki/Mod_optimization | Perf good-practices | ☐ |
| /wiki/Decompiling_game_code | Their approach vs our pzdis | ☐ |
| /wiki/Testing_mods_in_multiplayer | MP test loop | ☐ HIGH |
| /wiki/Uploading_mods · /wiki/workshop.txt · /wiki/mod.info | Packaging | ◐ (mod.info known) |
| /wiki/Getting_started_with_modding | Onboarding for collaborators | ☐ |
| TIS Modding Guides (MP networking migration) | **B42 MP changes for mods — mandatory for us** | ☐ HIGH |

## Ecosystem projects (wiki-referenced; locate exact URLs during P2)

| Project | Why | Status |
|---|---|---|
| **Umbrella** | Lua typestubs for VSCode — collaborator dev environment | ☐ HIGH |
| **Unofficial JavaDocs (Build 42)** | Browsable java API — complements pzdis | ☐ HIGH |
| **PZEventDoc / PZEventStubs** | Event documentation beyond the wiki | ☐ HIGH |
| LuaDocs | Lua-side API docs | ☐ |
| Starlit Library · TchernoLib · Doggy's Library | Common-lib patterns; possible deps | ☐ |
| Elyon Lib | KBW's lib (author El1oN) — networking/UI patterns we've seen in the wild | ◐ |
| Moodle Framework · "Moodles in lua" | **New-nutrient UI needs moodles — direct dependency candidates** | ☐ HIGH |
| Easy Distributions API · SpawnerAPI | Loot/distribution injection for the item pass | ☐ |
| Zomboid Decompiler · Beautiful Java | Alternative decompile paths | ◐ (pzdis covers us) |
| Community Modding template | Repo/build conventions | ☐ |
| ZedScripts (VSCode) · Zed Script | Script-file tooling | ☐ |
| PZ Loot Analyzer · LootZed | Distribution inspection | ☐ |

## Tutorials/guides (from hub; triage during P2)

- Albion's PZ Modding Guides (2025) — reportedly solid general docs. ☐
- MrBounty's PZ Mod Documentation (2023) — cross-check age. ☐
- SimKDT video guides (2026) — B42-current. ☐
- Rainmaker B42 item-mod video (2025) — quick item-pipeline sanity check. ☐
- FWolfe guide — only the good-practices chapter. ☐

## Communities

- TIS Discord `#mod_portal` + "Mod Resources" thread (2025-07) — where new
  getter/setter requests go; where 42.20 changes get discussed first. ☐
- PZ Modding Community Discord. ☐

## Already-digested internal sources

- `C:\Users\Angus\pz-b42\findings\*` — nutrition-weight (●, migrated to
  [vanilla/nutrition-core](vanilla/nutrition-core.md)), crafting-speed (●),
  metalwelding/blacksmith (●), foraging categories (◐), ItemQuality
  investigation (●, → teardown), BeyondTen analysis (●, → teardown).
- Local install `D:\SteamLibrary\...\ProjectZomboid` 42.20.4 + 159 workshop
  mods — the standing evidence base.
