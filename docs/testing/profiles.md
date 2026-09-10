# Test profiles — one file per named combination under test

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 07 (T1).
Evidence grades: **C** read from code (`file:line`, or `Class.method @addr Lline` for the jar),
**M** measured on the live dedicated server (run id + artifact link), **W** wiki mirror (none is
used here).
A **profile** is `testing/profiles/<name>.toml`: which golden fixture to restore, which mods go
into `Mods=` and where each is copied from, which `SandboxVars` to override, and which bus probes
have to answer before the session counts as the session that was asked for.
`pzt run --profile <name>` and `pzt scenario <test> --profile <name>` are the two entry
points ([README.md](README.md) § `pzt`). The **implementation authority is
`testing/pzt/profile.py`** — this document explains the model and what was measured, and does not
restate the module's error strings. The pipeline's layers, fragility budget and roadmap are
[pipeline-design.md](pipeline-design.md); the spike findings this stands on are
[spikes.md](spikes.md) § S1 / § S3.

## Summary

1. **One declarative file replaces every hand-edit.** A profile names the fixture, the mods (by
   workshop id, by bare id, or by an explicit folder), the sandbox overrides, the client accounts
   and the post-join probes; everything it asks for is resolved and validated **before a single
   process starts**, so a bad mod id or a misspelt sandbox key costs a second instead of a boot.
2. **Placement is a copy, because `-nosteam` searches nothing else.** Under `-nosteam` only
   `<cachedir>/mods` is read (S3), so every mod a profile names is copied into the per-run cache
   on **both** sides from one source map; `WorkshopItems=` is written empty and the numeric
   workshop id survives only as provenance.
3. **A profile never mutates the fixture.** Mods overlay a *restored per-run copy*, and
   `[sandbox]` is **merged** into that copy's own `SandboxVars.lua` rather than replacing it.
   Measured: after the server's own boot-time rewrite the run's file still read `DayLength = 1`
   (the profile's) **and** `Zombies = 6` (the fixture's), at the fixture's own 189 four-space
   assignments / 184 settable options, `diff` = the one seeded line.
4. **A green run is not evidence that a mod loaded.** The game's reaction to a mod it cannot find
   is a WARN and a clean boot (S3-A), so the run fails fast at `server_started` — 23 s, no client
   ever launched — and `[[verify]]` bus probes are what prove *effect*: both `trait.check` probes
   returned `keenPerceptionLoaded: true`, on the server and on the client.
5. **L0 is `tools/mod_lint.py`.** Eight static rules over a mod folder; the 230-folder installed
   corpus scores 84 findings (3 ERROR, 30 WARN, 51 INFO) and the acceptance subject scores 0.

---

## The TOML schema

Every key is optional and every default is the CLI's own, so a profile only says what differs.
Bare keys must precede the first table header (TOML), which is why `run` / `verify` are written as
inline tables in the shipped files. **Any key not in this table is a pre-boot error** naming the
known set (`profile.py:93-96`) — a profile cannot typo its way into a silent no-op.

| Key | Type | Default | What it does | Ev |
|---|---|---|---|---|
| `fixture` | string | `"default"` | The golden fixture restored for the run. It **wins over a typed `--fixture`** (it is the fixture the `[sandbox]` keys were validated against); the conflict is printed, not swallowed | C — `profile.py:216`, `session.py:77-79` |
| `description` | string | `""` | Free text, carried into `report.json["profile"]` so an artifact says what the run was for | C — `profile.py:261`; M — [`run-20260910-133657`](../../testing/artifacts/run-20260910-133657/report.json) |
| `[[mods]]` `id` | string | — | The name that goes in `Mods=`. A harness id resolves to the repo folder; any other bare id is looked up in the workshop index | C — `profile.py:151-159` |
| `[[mods]]` `workshop_id` | string | — | Resolve from `<WORKSHOP_DIR>/<item>/mods/*`. An item shipping more than one mod needs `id` as well, and the error lists what it ships | C — `profile.py:134-150` |
| `[[mods]]` `path` | string | — | An explicit folder — absolute, or relative to the repo root. This is how a mod that is not on the workshop (ours, once it exists) goes under test | C — `profile.py:126-133` |
| `[[mods]]` `copy` | bool | `true` | `false` = named in `Mods=` and placed **nowhere**: the missing-mod path, reproducible with nothing installed. Needs an explicit `id`, since there is no `mod.info` to read the name from | C — `profile.py:121-125`; M — [`run-20260910-133916`](../../testing/artifacts/run-20260910-133916/report.json) |
| `[sandbox]` | table | `{}` | Top-level `SandboxVars` options merged into the restored fixture's file. A key that is not a settable option of *that* file is a hard error before boot, with the three closest names | C — `profile.py:181-195`, `server.py:101-119`; M — § What a profile changes |
| `[server]` `timeout` | int | `420` | Seconds to wait for `*** SERVER STARTED ****` | C — `profile.py:259` |
| `[client]` `timeout` | int | `300` | Seconds to wait for a client to reach in-world | C — `profile.py:260` |
| `[client]` `users` | list | `["admin"]` | The accounts to attach. `pzt run` launches all of them; `pzt scenario` attaches the first as the test subject | C — `profile.py:256`, `cli.py:139`, `scenario.py:112` |
| `[client]` `safemode` | bool | `false` | Never set it: `-safemode` turns a 17 s world load into ~120 s (S2) | C — `profile.py:258` |
| `[client]` `launcher` | `"java"` / `"exe"` | `"java"` | Validated against argparse's own choices, which a profile would otherwise bypass | C — `profile.py:250-252` |
| `[run]` `hold` | int | `5` | Seconds to hold the session open after `session_ready` — the test slot of `pzt run` | C — `profile.py:257` |
| `[[verify]]` `side` / `cmd` / `args` / `expect` | array of tables | `[]` | Bus probes run between `session_ready` and `hold`. `side` is `server` (default) or `client`; `expect` is matched as a **substring of `json.dumps(parsed ack)`**, so a JSON fragment like `'"keenPerceptionLoaded": true'` matches at any nesting. A failed probe makes the result `FAIL: verify <cmd>` | C — `profile.py:241-248`, `session.py:162-183`; M — [`run-20260910-133657`](../../testing/artifacts/run-20260910-133657/report.json) |

An explicit CLI flag beats the profile, which beats the default (`session.py:56-67`). argparse
cannot report whether a flag was typed, so "explicit" means "differs from the default" — and the
profile module's `DEFAULTS` hold exactly the `run`/`scenario` argparse defaults, with a test that
fails if the two ever drift (`testing/tests/test_cli_profile.py`).

### How a `[[mods]]` entry becomes a folder

`resolve_mod` takes the branches in this order and every miss raises before a process starts,
naming the paths it looked at (`profile.py:111-160`).

| Entry | Source folder | Fails when | Ev |
|---|---|---|---|
| `copy = false` | none — named in `Mods=`, deliberately unplaced | no explicit `id` | C — `profile.py:121-125` |
| `path = "…"` | the folder, absolute or repo-relative | not a directory (the error quotes the raw *and* resolved path) | C — `profile.py:126-133` |
| `workshop_id = "…"` | the item's single `mods/*` folder | the item is not installed; it ships >1 mod and no `id` picks one; no folder under it declares that `id` | C — `profile.py:134-150` |
| `id` in `HARNESS_MODS` | `testing/PZTestKit/PZTestKit` | — | C — `profile.py:151-152` |
| `id` alone | the workshop index entry | not a harness mod and not installed (the error carries the index size and the workshop root) | C — `profile.py:153-159` |
| none of the above | — | always: "needs one of: id, workshop_id, path" | C — `profile.py:160` |

For the `path` and `workshop_id` branches the id comes from the folder's own `mod.info`
(`mods.mod_id_of`): no id at all points the reader at `python tools/mod_lint.py <src>`, and an id
that disagrees with the profile's is quoted both ways rather than picked between
(`profile.py:99-108`). Duplicate ids across two entries collapse to one `Mods=` name
(`profile.py:225-226`), and **`PZTestKit` is prepended when a profile does not list it**
(`profile.py:234-236`): without the harness there is no command bus, no ready marker and no probes.

### What a profiled run prints first

```
[    0.0s] profile name=mod-under-test fixture=default mods=PZTestKit;KeenPerception sandbox=DayLength=1 skip=none
  [server] sandbox merged into the fixture's file: applied ['DayLength'], appended none
```

The `profile` mark is the run's first timeline entry, before anything is launched
(`session.py:70-85`, `cli.py:138`, `scenario.py:118`), and `skip=` is the only place the log says
that a later `mods_not_found` was *intended*. `report.json` grows a `profile` block (what was
asked for **and** what it resolved to — the folders that actually reached `<cachedir>/mods`) and a
`verify` block; a profile-less run's report has exactly its old keys (`cli.py:199-201`).

## How `-nosteam` mod loading works

`ZomboidFileSystem.getAllModFolders` walks `workshop`, `steam` and `mods`, and the first two are
resolved through `getStagedItemModsFolders` / `getInstalledItemModsFolders`, **both gated on
`SteamUtils.isSteamModeEnabled`**. Under `-nosteam` — which every `pzt` process uses, because it
is what allows several instances on one machine — that leaves exactly one root:
`<cachedir>/mods`. There is no server `-modfolders` (the string exists only in
`MainScreenState`), and `WorkshopItems=` needs Steam too ([spikes.md](spikes.md) § S3).

Three consequences the profile builder is built around:

- **Copying is the only mechanism.** `harness.install` copies each source folder to
  `<cachedir>/mods/<mod id>`, harness mods from the repo and everything else from the profile's
  source map, which wins over both the harness map and the workshop index
  (`testing/pzt/harness.py:14-35`). The workshop tree is never written to: the acceptance runs
  left item `3685392864`'s mtime untouched.
- **The folder is renamed to the id.** A workshop folder whose name differs from its `mod.info`
  `id` lands under the id, because the game keys on `mod.info` — 51 of the 230 installed folders
  differ (the lint's `folder-id` INFO).
- **`WorkshopItems=` stays empty.** The seeded ini writes `WorkshopItems=` from a list no profile
  fills (`server.py:172-173`), and the acceptance run's `Server/pzt.ini` reads
  `Mods=PZTestKit;KeenPerception` beside a bare `WorkshopItems=`. The numeric id lives in the
  profile and in `report.json["profile"]["workshop_items"]` as **provenance only** — it is what
  makes a run re-subscribable, not what makes it load. Clients log
  `WARN:MISSING in SettingsTable: WorkshopItems` for the empty value; it is baselined noise (S3).

## What a profile changes, and what it does not

**Per run, on a restored copy.** The fixture excludes `mods/` from its snapshot, so the mod
overlay is rebuilt from the profile on every run and the fixture is never re-provisioned. The
fixture blob itself was byte-identical (sha256) before and after the three acceptance runs, and so
was the workshop folder — **M**, `.superpowers/sdd/07-profile-builder/task-4-report.md` § 4.

**The sandbox merges; it does not replace.** `write_sandbox_vars` writes a *partial* table, which
on a restored fixture would silently reset every option the world was provisioned with.
`merge_sandbox_vars` (`server.py:101-119`) rewrites only the named four-space keys in place,
keeping the server's comments, the five nested tables and the file's CRLF endings; `Server.seed`
picks it whenever the restored cache already has the file (`server.py:175-187`). Measured on
`run-20260910-133657`, reading the run's copy *after* the server's own boot-time rewrite (S1) —
the file's mtime is 33 s into the boot, so the rewrite really happened:

| Measure | Fixture (before) | Run copy (after seed **and** the server's rewrite) | Ev |
|---|---|---|---|
| `DayLength` | `4` | **`1`** — the profile's value | M — [`run-20260910-133657`](../../testing/artifacts/run-20260910-133657/report.json) |
| `Zombies` | `6` | **`6`** — the fixture's value, untouched | M — same run |
| Four-space assignments | 189 | 189 | M — same run |
| `sandbox_keys()` settable options | 184 | 184 | M — same run |
| Bytes / CRLF endings | 45 533 / 1 020 | 45 533 / 1 020 | M — same run |
| `diff` against the fixture | — | **one hunk, one line** (the seeded one) | M — same run |

189 is the count of four-space `key = ` lines; five of them are the nested-table openers
(`Basement`, `Map`, `ZombieLore`, `ZombieConfig`, `MultiplierConfig`), which is why
`sandbox_keys()` — the list a profile is validated against — returns **184** (184 + 5 = 189, plus
86 nested options at eight spaces). Both counts are stable across the merge. A profile naming a
nested option (`ZombiesDragDown`) or a table opener (`Map`) is rejected rather than silently
no-op'ing: nested overrides are out of scope for this slice.

**Which of the 189 the mod work actually cares about.** All five are settable from a profile; only
`DayLength` has been exercised by one. Line numbers are in the fixture's own
`testing/fixtures/default/cache/server/Server/pzt_SandboxVars.lua` — a gitignored per-machine
blob, of which `testing/fixtures/default/fixture.json` is the tracked record.

| Key | Fixture value | Why it matters | Where it is documented | Ev |
|---|---|---|---|---|
| `Nutrition` | `true` | The one sandbox option gating nutrition at all, and it gates only `Nutrition.update()` | [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md) § The sandbox `Nutrition` option | C — fixture file :273 |
| `FoodRotSpeed` | `3` | Enum 1–5 scaling `age += ΔgameHours × FoodRotSpeed / 24` (3 = ×1.0, the default) | [../vanilla/food-item-model.md](../vanilla/food-item-model.md) § Key reference | C — :280 |
| `FridgeFactor` | `3` | Enum 1–6 scaling aging inside a *powered* fridge or freezer (3 = ×0.2, the default) | [../vanilla/food-item-model.md](../vanilla/food-item-model.md) § Key reference | C — :288 |
| `StatsDecrease` | `3` | Enum 1–5 on hunger and thirst drain (3 = ×1.0, the default) | [../vanilla/body-stats.md](../vanilla/body-stats.md) | C — :246 |
| `DayLength` | `4` | How long a game day lasts in real minutes (`1` = 15 min, `4` = 1 h 30 m) — the clock every timed scenario is fitted against | § The cadence ceiling below | C — :53; **M** set to `1` by a profile |

**What a profile cannot do.** An option the world generator consumed once is not retroactive: the
zombie population that was distributed, the spawn regions and the start date belong to the world,
not to the boot that loads it. Only `DayLength` has been measured on a restored world here, so
treat the rest as unproven and re-provision when a world-gen option has to change —
`pzt provision --name <n> --sandbox K=V` builds a fresh fixture ([README.md](README.md) § `pzt`).
`pzt attach --profile` does **not** exist and is not half-wired: `attach` builds a `Server` stub
and never installs mods, so a profile would be accepted and ignored (`cli.py`'s `attach`
subparser rejects `--profile` with argparse's exit 2).

### The cadence ceiling — `DayLength` × `--speed`

`DayLength = 1` (a 15-minute day) at `--speed 30` **overruns the harness's game-minute
scheduler**: `scenario-20260910-134012` recorded `ticks_per_world_min: 0.22` and
`cadence_suspect: true` — `Events.EveryOneMinute` fired 20 times while the world advanced ~92
game-minutes. The event's ceiling is ~8–10 Hz (`ticks_per_wall_s: 10.08` here), and the three
slice-04 scenario runs at the fixture's default `DayLength = 4` recorded exactly `1.0`
ticks per game-minute at the same `--speed 30`. The rule of thumb is
**`24 × speed / day_minutes ≲ 8`** game-minutes per wall-second — on `DayLength = 1` that is
`--speed 5`, not 30 (**M**,
[`scenario-20260910-134012`](../../testing/artifacts/scenario-20260910-134012/scenario-smoke_clock.json)).
`smoke_clock` still PASSed, because every assertion it makes is counted in *ticks* and it
therefore measures the scheduler against itself — but nothing fitted against the **game clock** on
that run may be cited, and slices 09–11 must not template a timed scenario off
`mod-under-test.toml` without re-reading `cadence` first.

## The missing-mod failure mode

**The game does not fail on a mod it cannot find.** S3 variant A measured it in both directions:
the server logs `WARN … ZomboidFileSystem.loadModAndRequired> required mod "X" not found` and
**boots normally with 0 errors**, and the client joins and spawns normally with the same WARN and
the mod simply inactive. That is what makes a mod-testing pipeline dangerous by default: a
profile whose mod never arrived produces a session where every probe answers, the report is clean
and the run is green.

Three things close it, in cost order:

1. **Pre-boot resolution.** Almost every way to get this wrong — an uninstalled workshop item, a
   folder that is not there, an id nothing declares — is a `ProfileError` before a process starts
   (`profile.py`). Cost: a second.
2. **The fail-fast**, immediately after the `server_started` mark and before any client is
   launched (`session.py:140-159`, called from `cli.py:151` and `scenario.py:129`). It marks
   `mods_not_found`, copies up to five of the server's own WARN lines into the timeline as
   `mod_missing_line`, and raises — which every caller's existing `except` turns into an `error`
   mark, the normal teardown and `RESULT: FAIL`.
3. **`[[verify]]`**, the only one of the three that proves the mod took *effect* rather than
   merely arrived (§ The TOML schema).

Measured on `run-20260910-133916` (`pzt run --profile missing-mod`) — **M**,
[`report.json`](../../testing/artifacts/run-20260910-133916/report.json):

- **23 s wall, exit 1**, against the two-mod run's 93 s: the ~37 s client boot and the hold were
  never paid for.
- The `timeline` phase list is exactly `profile → server_launch → server_started →
  mods_not_found → mod_missing_line → error → server_stopped → faults`. There is **no
  `client_launch`**, and the run directory has no `clients/` folder at all.
- `mod_missing_line` carries the server's own words verbatim: `WARN : Mod … at
  ZomboidFileSystem.loadModAndRequired> required mod "NoSuchModHere" not found` — the finding in
  the game's voice, not the harness's.
- `server_errors` is **0** and that is not a contradiction: to this game a missing mod is a WARN
  and a clean boot. Never read `server_errors: 0` as "the mod loaded".
- One reason, printed once: the `error` mark (why the run stopped early) and the `faults` mark
  (the end-of-run verdict) both name `NoSuchModHere`, and the `RESULT:` line is the bare `FAIL`.

`copy = false` is what makes this reproducible on any machine: the mod is named in `Mods=` and
placed nowhere, so nothing has to be installed — or uninstalled — to exercise the path. The
client side is deliberately not spared it either: `enable_client_mods` still names a skipped id in
`default.txt` (`harness.py:38-46`), so both sides walk the same road.

## L0 — `tools/mod_lint.py`

The static half of layer L0: is this folder even shaped like a B42 mod? It is deliberately
**standalone** — paths and/or workshop ids on the command line, stdlib only, no import of
`testing/pzt` — so `tools/` stays runnable in CI without the game. `python tools/mod_lint.py`
with no arguments sweeps every mod under the workshop root; exit 1 iff an ERROR fired.

| Rule | Level | Check as coded | Ev |
|---|---|---|---|
| `version-dir` | ERROR | at least one child folder matching `^42(\.\d+){0,2}$` (b41-flat and unversioned mods fail here) | C — `tools/mod_lint.py:122` |
| `mod-info` | ERROR | a `mod.info` exists in **some** version folder, in `common/`, or at the mod root | C — `mod_lint.py:129` |
| `mod-info-place` | WARN | there is a version folder and the **newest** one holds the `mod.info`; the detail names where it actually is | C — `mod_lint.py:134` |
| `id` | ERROR | the resolved `mod.info` declares a non-empty `id=` | C — `mod_lint.py:140` |
| `id-agree` | ERROR | every `mod.info` anywhere under the folder declares the same `id` | C — `mod_lint.py:144` |
| `media` | WARN | `media/` exists inside the chosen version folder | C — `mod_lint.py:155` |
| `loadstring` | ERROR | no `\bloadstring\s*\(` in any `.lua` under the folder (removed from the engine in 42.20.x) | C — `mod_lint.py:159` |
| `folder-id` | INFO | folder name == the resolved `id` | C — `mod_lint.py:164` |

Version folders sort by **parsed tuple, not by string** (`42.20.1 > 42.20 > 42.9 > 42`); the
resolution order for the `mod.info` is newest version folder → older ones → `common/` → root
(`mod_lint.py:47-78`).

### The installed corpus, swept

230 mod folders under `D:\SteamLibrary\steamapps\workshop\content\108600`, 42.20.4, ~13 s
(it reads every `.lua` in the corpus):

```
python tools/mod_lint.py     -> 84 finding(s): 3 ERROR, 30 WARN, 51 INFO across 230 mod(s)   exit 1
python tools/mod_lint.py 3685392864
                             -> 0 finding(s): 0 ERROR, 0 WARN, 0 INFO across 1 mod(s)        exit 0
```

| Rule | Findings | What they are | Ev |
|---|---|---|---|
| `version-dir` | 0 | 230/230 ship a `42*` folder | M — sweep, 2026-09-10 |
| `mod-info` + `id` | 2 ERROR | both on `3782784855/Skill Recovery Journal`, which has **no `mod.info` anywhere** — so it is invisible to the workshop index, which holds 229 entries for 230 folders | M — sweep |
| `id-agree` | 1 ERROR | `3774052732/SD_CC_TEST` declares `sd_cc_test` in `42/mod.info` and the root `mod.info` but `SD_CC_TEST_42` in `common/mod.info`: whichever file a reader opens first decides the id | M — sweep |
| `mod-info-place` | 6 WARN | AutoCook `3388721641`, MoodleFramework `3396446795`, RemoveAllItems `3413255058`, EN_Newburbs `3520263838`, gasmask `3701820916`, WorkingKnowledge `3717099183` — `mod.info` in `common/` or an older version folder than the live one | M — sweep |
| `media` | 24 WARN | all ship `common/media` with an empty newest version folder: copying that folder alone would lose the content. 25 at the Task-1 sweep — see the drift note below | M — sweep |
| `loadstring` | 0 | no user in the corpus, matching `docs/mods-survey/approved-modlist.md:13` | M — sweep |
| `folder-id` | 51 INFO | folder name ≠ id, informational: `harness.install` places by id anyway | M — sweep |

**229 distinct ids over 230 folders, and no duplicates** — the one gap is Skill Recovery
Journal's missing `mod.info`, so the workshop index's 229 entries are a *missing* mod, not a
collision. If a duplicate ever appears, `workshop_index()` keeps whichever it globs first: resolve
that mod by `workshop_id` in the profile, never by bare id.

**The corpus is a live tree and it moved during this slice.** The Task-1 sweep this morning
reported **85 findings (3 ERROR, 31 WARN, 51 INFO)**; the re-run quoted above, hours later, reports
84 / 3 / 30 / 51. The single difference is `3490370700/73fordFalconPS`, whose `media/` was in
`common/` at the first sweep and is inside its `42.0/` folder now (both that item's folders were
rewritten at 13:47 today, i.e. by a Steam update, not by anything here — every `pzt` path treats
the workshop tree as read-only). Quote a sweep with its date, and re-run it rather than citing
this one.

Two figures in the plan were superseded by the sweep itself: it predicted 1 ERROR + 6 WARN and
"`id-agree` 0 failures", where the measurement finds 3 ERRORs (`id-agree` among them) and 30 WARNs.
The plan's count treated a `mod.info` in *any* `42*` folder as correctly placed — which is what
`mods.mod_id_of`'s glob does — and compared only the *resolved* `mod.info` per folder rather than
every one in the tree.

## MP behaviour

A profile is a **server-side** decision that the client inherits.

- **Both sides are seeded from one source map.** `make_client` defaults its `mod_sources` and
  `mod_skip` to the server's — `None` means "the server's", not "none" — so the two cannot drift
  (`session.py:109-118`), and the client's `Mods=` already comes from `server.mods`. Measured:
  after `run-20260910-133657` both `<run>/server/mods/` and `<run>/clients/admin/mods/` held
  exactly `KeenPerception` and `PZTestKit`, and the client's `default.txt` named both in the same
  order (**M**).
- **The server's list is authoritative.** The client reloads its Lua with the server's `Mods=` on
  join, so its own enabled list matters only until the first join
  ([README.md](README.md) § How a driven client is controlled, `harness.py:38-40`). A client-side
  mod the server does not name is not in the session.
- **A probe is worth running on both sides.** The acceptance profile asks `trait.check` of the
  server *and* of the client, and both returned
  `{"keenHearingExcludesDeaf": false, "keenHearingExcludesHardOfHearing": false,
  "keenPerceptionLoaded": true}` — the mod's effect is present in both Lua states, not merely in
  the server's (**M**,
  [`run-20260910-133657`](../../testing/artifacts/run-20260910-133657/report.json)). For anything
  the server *owns* (nutrition, hunger and thirst, item aging, perks) the server's reading is the
  measurement and the client's is a 1 Hz mirror — [README.md](README.md) § How a driven client is
  controlled, [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md) § MP behaviour.
- **Every copied mod adds baselined noise.** Each one logs `AdvancedAnimator …
  NoSuchFileException` for the optional `AnimSets` / `actiongroups` folders it does not ship (S3);
  the acceptance runs recorded `server_errors: 0` with those lines present.

## Open questions

1. **Does B42 read the newest version folder's `mod.info` first, or any `42*` folder?**
   `pzt/mods.py:mod_id_of` globs any and takes the first; `mod_lint`'s `mod-info-place` assumes
   the newest. The two disagree on 6 installed mods today, and on `3774052732/SD_CC_TEST` they
   would disagree about the mod's *id*. Slice 12's mod-anatomy doc settles it from the engine.
2. **`pzt scenario --profile` does not run the profile's `[[verify]]` probes** (`scenario.py`
   stops at the fail-fast). A scenario artifact therefore evidences that the profile's mods
   *loaded* — the log line, and `profile` in the artifact — but not that they took effect; the
   `pzt run` path is the evidence for the latter. One line after `client_ready` would close it,
   and slices 09–11 will want it if a scenario is ever a slice's only run.
3. **Which sandbox options survive a restore.** Only `DayLength` has been set by a profile on a
   restored world and measured to apply; the other four keys the mod work cares about
   (`Nutrition`, `FoodRotSpeed`, `FridgeFactor`, `StatsDecrease`) are unexercised, and world-gen
   options are assumed non-retroactive rather than measured.
4. **Nested sandbox options** (`Map.*`, `ZombieLore.*`, `ZombiesDragDown`) are out of scope: a
   profile naming one fails validation. If a slice needs one, the answer today is a re-provisioned
   fixture, not a wider merge.
5. **`[[verify]]` matches `expect` as a substring of the dumped JSON**, which is deliberately
   forgiving (it matches at any nesting) and therefore cannot express "not present" or a numeric
   comparison. A probe that needs either belongs in a scenario with a Python evaluator.

## Sources

- Code: `testing/pzt/profile.py` (schema, resolution, validation), `testing/pzt/server.py:93-119`
  (`sandbox_keys`, `merge_sandbox_vars`) and `:162-187` (`Server.seed`'s merge-vs-write choice),
  `testing/pzt/session.py:56-183` (`opt`, `mark_profile`, `make_client`, `check_mods_loaded`,
  `verify`), `testing/pzt/harness.py:14-46` (placement, client enabled list),
  `testing/pzt/cli.py:127-201,249` and `testing/pzt/scenario.py:95,106-136,247` (the two entry
  points), `tools/mod_lint.py` (the L0 rules).
- Profiles: `testing/profiles/mod-under-test.toml`, `testing/profiles/missing-mod.toml`,
  `testing/profiles/README.md`.
- Measured runs (slice 07, 2026-09-10):
  [`run-20260910-133657`](../../testing/artifacts/run-20260910-133657/report.json) —
  `pzt run --profile mod-under-test --hold 5`, PASS in 93 s, both probes `ok=true`, the sandbox
  numbers; [`run-20260910-133916`](../../testing/artifacts/run-20260910-133916/report.json) —
  `pzt run --profile missing-mod`, FAIL in 23 s with no client;
  [`scenario-20260910-134012`](../../testing/artifacts/scenario-20260910-134012/scenario-smoke_clock.json)
  — `pzt scenario smoke_clock --profile mod-under-test --speed 30`, PASS with the cadence finding.
  Provenance and the "do not cite" notes for all three:
  [`../../testing/artifacts/README.md`](../../testing/artifacts/README.md).
- Spikes: [spikes.md](spikes.md) § S1 (the server's boot-time `SandboxVars` rewrite, the ~15 s warm
  boot and the cold-start effect), § S2 (`-safemode` costs ~100 s of world load), § S3 (mods under
  `-nosteam`, the missing-mod WARN, the copy strategy).
- Neighbouring docs: [README.md](README.md) (the command inventory, the bus, the harness layout,
  the scenario layer), [pipeline-design.md](pipeline-design.md) (layers, fragility budget, T0–T4),
  [../vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md),
  [../vanilla/food-item-model.md](../vanilla/food-item-model.md),
  [../vanilla/body-stats.md](../vanilla/body-stats.md) (what the five sandbox keys do).
- Task reports (slice 07, not tracked evidence — working notes):
  `.superpowers/sdd/07-profile-builder/task-{1,2,3,4}-report.md`.
