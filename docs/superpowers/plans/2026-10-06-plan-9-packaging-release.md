# Plan 9 — Packaging and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the mod as a Workshop item an operator can run on a dedicated server: a release build staged in the in-game uploader's layout from one command, a manifest the checksum discipline can be audited against, the boot self-report the spec promised, the operator guide, the release notes naming every incompatible, inert and redundant neighbour, the layout lint running before every harness boot, and the packed build booted on the two-client fixture with its release client — each reading on a dedicated server.

**Architecture:** One tool, `tools/release_pack.py`, checks the mod folder against the packaging rules the library states (one `mod.info` in the version dir, `versionMin` only, no `require=`, `common/` holding every Lua and data file with no version-dir twin, no file at a vanilla relative path, LF endings and no byte-order mark, the Lua version string equal to `modversion`) and stages the item under `release/` as `NutritionRevamp/workshop.txt` + `Contents/mods/NutritionRevamp/` with a `MANIFEST.json` of per-file hashes (the gate's CR-dropped hash for script files), diffable against the previous release's manifest so a script change is flagged as a server event. The mod's server self-report gains the item-pass and legacy-mirror flags and the client's names the framework it detected. The harness lints every `path=` mod before a boot. The shipped docs sit at the mod folder's root (`README.md` the operator guide, `CHANGELOG.md` the release notes, `COMPATIBILITY.md` the neighbour table). Two live sessions: the staged build on fixture `two` with the release client `bob` joining and both self-reports read, and X23, the release client's behaviour on an unguarded raise. The five subscribe-and-read code reads are one task gated on the Workshop folders being present.

**Tech Stack:** Python 3 (`tools/`, pytest under `tools/tests` and `testing/tests`), the mod's Lua (Kahlua subset), the harness (`pzt`), the claims register and its delta tools.

**Spec:** `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` — § 4.9 (default: the id, prefix and bus module; the layout; `versionMin` only with the failure mode documented; no `require=`; MoodleFramework detected never required; every script-changing Workshop update a server event; the layout lint before every boot; the compatibility table and its stances; the five subscribe-and-read code reads; the one-line self-report), § 5 row 9 (layout, manifest, Workshop discipline, compatibility pages, the operator guide, the release notes naming every incompatible, inert and redundant neighbour; X20 and X22 if `common/` shapes are questioned), § 7 item 26 (`common/` for all Lua and data, the version dir for the manifest and the options file; `versionMin` only), § 4.10 tier 1 (the layout lint).

## Global Constraints

Everything in Plan 8's Global Constraints holds (`docs/superpowers/plans/2026-10-06-plan-8-sync-persistence.md`), and through it Plans 2–7's. Plan 9 adds:

- **The shipped layout is the measured one**: `42.20.4/` holds `mod.info` and `media/sandbox-options.txt` and nothing else; `common/` holds every Lua file, translation, script file and image; no `common/` file has a version-dir twin (#1086, #1318) and no file sits at a vanilla relative path (#1173); the version dir is named for the verified build and no later (#0825, #0826).
- **The manifest declares `versionMin=42.20.4` and no `versionMax`, no `require=`, and `incompatible=` is not a compatibility tool** (#0813): the incompatible neighbours are named in the description and the release notes, never gated.
- **Byte-identical script files on both sides** (#1182, #1231): the staged build is the repository's bytes with LF endings and no byte-order mark, the generated pass file is never edited by hand (`food_nutrients.py --check` in sync), and a release whose manifest differs from the previous one on any script file is documented as a server event.
- **A `mod/` edit never overlaps a live boot**, and the two live tasks run after every `mod/` task has landed.
- **A raising probe is gated on the server side with the profile's client timeout low and `pzt run` expected to fail** (CLAUDE.md § 5): X23's grade comes off its artifact.
- **The install, the workshop folder and the jar toolchain are read-only**: a code read of a Workshop mod is a read of its files, never a copy into the fixture, and an absent Workshop folder blocks its read, not the plan.
- **Pytest floor 2506**; the close writes the new count into CLAUDE.md § 3.
- **Rulings this plan takes** (each a ledger line and a `Ruling:` row at the close; 2–12 are controller defaults listed for Angus's § 7 re-review):
  1. **One plan for § 5 row 9**: Task 1 (the release tool) ∥ Task 2 (the self-report, the manifest, the shipped docs) ∥ Task 3 (the harness lint) → Task 4 (live: the staged build on fixture `two`) → Task 5 (live: X23) → Task 6 (the five code reads, gated) → Task 7 (docs) → Task 8 (close).
  2. **The release is `1.0.0`**: `NR.version` and `modversion` both read `1.0.0`, and the tool fails a release whose two strings differ.
  3. **The staging layout is the in-game uploader's** (`references/wiki-mirrors/mod-structure.md`): `release/NutritionRevamp/workshop.txt`, `preview.png` when one exists beside the mod folder (its absence is a WARN naming the 256×256 requirement, never an error), and `Contents/mods/NutritionRevamp/{42.20.4,common,README.md,CHANGELOG.md,COMPATIBILITY.md}`; `release/` is gitignored; the upload itself is Angus's, by hand, from that folder.
  4. **The shipped docs live at the mod folder's root** and travel with the item; the library's pages state what the game does and point at them, never restate them.
  5. **The self-report's item-pass flag is a read of one sentinel food**: the server compares the script manager's `Base.Acorn` calories against the pass file's `109.71` (the first item of the generated file; the implementer reads the script-item API and names the method in the comment); `legacyMirror=` reads the option; the client's `frameworks=` names MoodleFramework when its type test at `OnGameBoot` or later finds it (the type-test rule #2547, #2717), else `none`; the server's reads `n/a` because the framework is client-side.
  6. **The harness lints every `path=` mod before seeding** in `pzt run` and `pzt provision`, failing on an ERROR with the lint's own lines; workshop-id mods are not linted (not this project's); `pzt doctor` is unchanged.
  7. **The five code reads are one task gated on the Workshop folders**: at dispatch the controller lists `D:\SteamLibrary\steamapps\workshop\content\108600\{3690404044,2997722072,3415375593,3736275816,3694097672}`; a folder absent at dispatch defers its read with a ledger line, the release notes word that neighbour's stance "as designed, its code unread", and the deferred reads are the first task of the next plan or of a standalone slice — never a reason to hold this plan.
  8. **X20 and X22 are not run**: the shipped layout has no shadowed `common/` copy and no vanilla-path file, the tool enforces both, and the one `common/`-colliding shape this mod could take is the measured one (#2746).
  9. **X23 runs on the release client `bob`**: a probe mod whose client handler raises on a harness-triggered custom event (the x127 shape, triggered through `event.trigger` on `client:bob`), the server-side gate reading whether `bob` stayed connected and what its console wrote; a parked or disconnected client is the reading, written as such.
  10. **The release notes and the compatibility table are the spec's § 4.9 table** carried into the mod's own files, with each unread neighbour marked unread; the three free live experiments' readings (Plan 1) and the resident code reads (QualityCooking, BeyondTen, Evolving Traits World, Tooltiplib — whichever landed) are cited by run id in the table.
  11. **Not this plan:** a patch mod for QualityCooking (its own item, decided when it ships); the Workshop upload; poster and preview art; a localisation beyond EN; a `versionMax`; a second version dir.
  12. **The lint tool's rules and the release tool's checks are disjoint**: `mod_lint` keeps the layout rules the corpus sweep uses; `release_pack --check` adds this mod's own release rules and calls `mod_lint.lint` for the rest, so one folder has one layout verdict.

## Execution order

Task 0 → Task 1 (Sonnet) ∥ Task 2 (Opus) ∥ Task 3 (Sonnet) → Task 4 (Opus, live; needs 1, 2, 3) → Task 5 (Opus, live; needs 4's profile) → Task 6 (Opus; gated) → Task 7 (Sonnet; Opus review) → Task 8. Reviews are read-only. Tasks 1 and 3 never touch `mod/`; Task 2 is the only `mod/` writer before the live tasks.

## File structure

| path | responsibility | task |
|---|---|---|
| `tools/release_pack.py`, `tools/tests/test_release_pack.py`, `tools/README.md`, `docs/reference/tools.md`, `.gitignore` (`release/`) | the release check, the staging, the manifest and its diff | 1 |
| `mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua` (the self-report), `common/media/lua/client/NR_Client_Options.lua` (the client self-report), `common/media/lua/shared/NR_Core.lua` (`version = "1.0.0"`), `42.20.4/mod.info` (`modversion=1.0.0`, the final description), `mod/NutritionRevamp/README.md`, `CHANGELOG.md`, `COMPATIBILITY.md`; `testing/tests/test_mod_shipped_docs.py` | the self-report, the manifest, the shipped docs | 2 |
| `testing/pzt/cli.py`, `testing/pzt/harness.py` (the lint before seeding), `testing/tests/test_pzt_lint_gate.py` | the layout lint before every boot | 3 |
| `testing/profiles/x20-release.toml`, `testing/experiments/x201_release.py`, `testing/artifacts/x201-*/` | the staged build on fixture `two` | 4 |
| `testing/experiments/TKX_ClientRaise/`, `testing/profiles/x20-raise.toml`, `testing/experiments/x202_client_raise.py`, `testing/artifacts/x202-*/` | X23 | 5 |
| `docs/facts/other-mods/<five pages>.md` (new, one per neighbour read), `docs/facts/other-mods/catalog.md` | the five code reads | 6 |
| `docs/areas/packaging.md`, `docs/platform/mod-anatomy.md`, `docs/platform/harness.md`, `docs/areas/testing-your-mod.md`, `docs/areas/open-questions.md`, `docs/reference/experiments.md`, `docs/reference/artifacts.md`, the skills `nutrition-packaging`, `pz-mod-testing`, CLAUDE.md | the documentation delta | 7 |

---

### Task 0: The workspace — controller

- [ ] `scripts/sdd-workspace docs/superpowers/plans/2026-10-06-plan-9-packaging-release.md`; the ledger's first line names the plan; the Workshop folder listing for ruling 7 is taken now and ledgered.

---

### Task 1: The release tool — Sonnet implementer, Sonnet reviewer

**Files:** create `tools/release_pack.py`, `tools/tests/test_release_pack.py`; modify `tools/README.md`, `docs/reference/tools.md` (its `## Tools` table and a `<a id="release-pack"></a>` section under the reference profile), `.gitignore` (`release/`).

**Interfaces:** `check(mod_dir) -> list[Finding(level, rule, detail)]`; `stage(mod_dir, out_dir, item_name="NutritionRevamp") -> Manifest`; `manifest(mod_dir) -> dict` (`{relative_path: {"sha256": …, "gate_sha256": … (script files only; the content with every CR byte dropped), "bytes": n}}`); `diff(old_manifest, new_manifest) -> {"added", "removed", "changed", "script_changed"}`. CLI: `python tools/release_pack.py check <mod_dir>`; `stage <mod_dir> [--out release/] [--previous <MANIFEST.json>]` (prints the diff and `SERVER EVENT: <n> script file(s) changed` when any); `manifest <mod_dir>`.

- [ ] **Write the failing tests** (a temp mod folder fixture built in the test; one test per rule): `one-mod-info` (a second `mod.info` under `common/` → ERROR), `version-min-only` (`versionMax=` present → ERROR; `versionMin` absent → ERROR), `no-require` (`require=` → ERROR), `version-dir-contents` (anything under `42.20.4/` other than `mod.info` and `media/sandbox-options.txt` → ERROR), `no-shadow` (a `common/` relative path that also exists under the version dir → ERROR), `no-vanilla-path` (a `media/scripts/` or `media/lua/` relative path equal to one in `data/vanilla-relative-paths.txt`, a list the implementer writes from the install's `media/scripts` and `media/lua` trees — read-only — committed under `data/`; ERROR), `lf-no-bom` (a CR byte or a leading BOM in any text file → ERROR), `version-agree` (`NR_Core.lua`'s `version = "x"` ≠ `modversion` → ERROR), `png-binary` (a `.png` whose header is not `\x89PNG` → ERROR), `mod-lint` (an ERROR from `mod_lint.lint` is carried through); `test_manifest_gate_hash` (a script file with CRLF has `gate_sha256` equal to its LF twin's); `test_stage_layout` (`workshop.txt` with `version=1`, `title=Nutrition Revamp`, `description=` from `mod.info`, `tags=Build 42;Multiplayer;Realistic;Food` and `visibility=public`; `Contents/mods/NutritionRevamp/42.20.4/mod.info` present; `MANIFEST.json` written; a `preview.png` absent → a WARN naming 256×256); `test_diff_server_event` (a changed `.txt` under `media/scripts` lands in `script_changed`; a changed `.lua` lands in `changed` only); `test_check_real_mod` (`check("mod/NutritionRevamp")` → 0 ERROR).
- [ ] Run: `python -m pytest tools/tests/test_release_pack.py -q` → FAIL (no module).
- [ ] **Implement** `tools/release_pack.py` (stdlib only; imports `mod_lint.lint`; text files are `.lua .txt .json .info .md .toml`; `stage` copies with `shutil.copytree` after `check` returns 0 ERROR and writes every text file with LF, refusing when `check` finds an ERROR).
- [ ] Run the tests → PASS; `python tools/release_pack.py check mod/NutritionRevamp` → `0 ERROR` (if it finds one, STOP and report: the fix is Task 2's or the controller's).
- [ ] `tools/README.md` entry (CRLF file: edit with `newline=''`); `docs/reference/tools.md` section under its reference profile; `page_lint docs/reference/tools.md` 0.
- [ ] Commit `Release tool: release_pack.py check/stage/manifest/diff with the gate hash, the uploader layout and the server-event diff` -- `tools/release_pack.py tools/tests/test_release_pack.py tools/README.md docs/reference/tools.md .gitignore data/vanilla-relative-paths.txt`.

---

### Task 2: The self-report, the manifest and the shipped docs — Opus implementer, Opus reviewer

**Files:** modify `mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua` (`NR.selfReport`), `common/media/lua/client/NR_Client_Options.lua` (the client line), `common/media/lua/shared/NR_Core.lua` (`version = "1.0.0"`), `42.20.4/mod.info`; create `mod/NutritionRevamp/README.md`, `CHANGELOG.md`, `COMPATIBILITY.md`, `testing/tests/test_mod_shipped_docs.py`.

- [ ] **The self-report** (ruling 5): the server line becomes `NutritionRevamp v<version> build <build> side=server mode=<name> itemPass=<true|false|unread> legacyMirror=<on|off> hook=<bool> limitations=<n> nutritionOn=<bool> log=<n>`; `itemPass` is the sentinel read (`Base.Acorn`'s script calories against `109.71`, read through the script-item API the implementer names in the comment; `unread` when the script manager or the item is absent); the client line gains `frameworks=MoodleFramework` or `frameworks=none` from the existing type test and `itemPass=` from the same sentinel read on the client; `kahlua_lint`, `hotpath_lint`, `mod_lint`, `science_check --scan mod` 0; the full `claims_check` 0 after the edit (a line shift re-anchors every `repo:` pointer into the touched files — the implementer lists the shifted rows for the controller; a `mod/` edit never edits the register).
- [ ] **The manifest**: `modversion=1.0.0`; the description rewritten as the release text (≤ 1000 characters; names Nutrition Makes Sense as incompatible, the hunger/thirst/fatigue/weight tweaks as incompatible, the endurance tweaks and Nutrition Tweaker Enhanced as inert, ApocalipseBR Nutrition Sync Fix as redundant, MoodleFramework as optional; no key token inside a value (#0807)); `NR_Core.lua` `version = "1.0.0"`.
- [ ] **`README.md` (the operator guide)**: install (`Mods=NutritionRevamp` by id, the Workshop item, the server's list wins over a client's); the sandbox options with their defaults (read `media/sandbox-options.txt` and name each key once); the precondition `Nutrition = false` and what happens with it on (vanilla only subtracts: #0453's reading as the README states it); the self-report line and how to paste it into a bug report; the version gate's failure mode (a gated mod prints the not-found line an absent folder prints; read `mod.info` not the log); the checksum discipline (every update that changes a script file is a server event: update the server first, then clients; a bypass role is never the answer); the mode (overlay vs takeover) in one paragraph; what a release client does on an error (the X23 line, "unmeasured" until Task 5 lands — Task 7 rewrites it).
- [ ] **`CHANGELOG.md` (the release notes)**: `## 1.0.0 — 2026-10-06` with one line per plan's deliverable (Plans 1–8) and a `### Compatibility` block naming every incompatible, inert and redundant neighbour from the spec's table, each unread neighbour worded "as designed; its code unread".
- [ ] **`COMPATIBILITY.md`**: the spec § 4.9 table as a shipped table (neighbour · stance · what the mod does · evidence: a run id or "unread"), with the resident code reads cited by their library page's run ids (`docs/facts/other-mods/*.md`).
- [ ] **The test** `testing/tests/test_mod_shipped_docs.py`: the three files exist; `CHANGELOG.md` names every neighbour the spec table lists (a list in the test); `mod.info`'s description ≤ 1000 characters and names "Nutrition Makes Sense"; `modversion` equals `NR_Core.lua`'s version.
- [ ] Gates (the `mod/` set); commit `Release 1.0.0: the self-report's item-pass, legacy-mirror and framework flags, the manifest, the operator guide, the release notes and the compatibility table` -- the files.

---

### Task 3: The layout lint before every boot — Sonnet implementer, Sonnet reviewer

**Files:** modify `testing/pzt/harness.py` (a `lint_paths(sources) -> list[str]` that runs `tools.mod_lint.lint` on every `path=` mod and returns its ERROR lines), `testing/pzt/cli.py` (`run` and `provision` call it before seeding and exit 2 printing the lines); create `testing/tests/test_pzt_lint_gate.py`.

- [ ] **Write the failing tests**: a temp mod folder with no version dir → `lint_paths` returns one ERROR line; the real `mod/NutritionRevamp` → `[]`; the CLI path: `run` with a profile whose `path=` mod fails the lint exits 2 before any fixture copy (mock `seed`).
- [ ] Run → FAIL; **implement** (import `tools.mod_lint` by path, the way `testing/pzt/mods.py` already references it); run → PASS; `python -m pytest testing/tests -q` green.
- [ ] `docs/platform/harness.md`: one sentence under `## Procedure` ("`pzt run` and `pzt provision` lint every `path=` mod before seeding and stop on an ERROR") tagged with a C row the delta mints on the new function (`repo:testing/pzt/harness.py:<line> "def lint_paths"`); the skill `pz-mod-testing` re-synced if it quotes the procedure; `page_lint` 0.
- [ ] Commit `Harness: the layout lint before every boot (lint_paths; run and provision stop on an ERROR)` -- the files.

---

### Task 4: Live 1 — the staged build on fixture `two` — Opus implementer (live), Opus reviewer

**Files:** create `testing/profiles/x20-release.toml` (fixture `two`; `clients = ["admin", "bob"]`; `[[mods]]` PZTestKit and the STAGED copy `release/Contents/mods/NutritionRevamp` by path; `[sandbox] Nutrition = false`; verify rows: `NutritionRevamp.version` on both clients reads `"1.0.0"`), `testing/experiments/x201_release.py`; the artifact `testing/artifacts/x201-<stamp>/release.json`.

- [ ] `python tools/release_pack.py stage mod/NutritionRevamp --out release` (the staged folder is the boot's mod; its `MANIFEST.json` is copied into the artifact); `python testing/pzt doctor`; one session: the server boots with the staged build; `admin` (debug) and `bob` (release) join; phases: A the server self-report line read from the server console (`side=server … itemPass=true legacyMirror=<the option> …`), B each client's self-report line from its console (`frameworks=none` on this fixture; `itemPass=true`), C `bob`'s join (no checksum disconnect; the server log's connection lines), D the manifest check (the staged files' sha256 against the repo's, by the driver, all equal), E a paired read of `NutritionRevamp.version` on all three sides. Every reading has a path; the server-log pattern excludes the probe names.
- [ ] The artifact JSON under `testing/artifacts/x201-<stamp>/`; its row in `docs/reference/artifacts.md`; its keys in `do-not-cite.csv`; the delta rows (M, n=1) for each phase on their owner pages (`packaging.md` the self-report and the staged build; `harness.md` the two-client staged boot); the experiments row.
- [ ] Commit the driver and profile BEFORE the run (`Harness: x20-release profile and the x201 driver`), the artifact after (`x201: the staged 1.0.0 build on fixture two — self-reports, bob's join, the manifest`).

---

### Task 5: Live 2 — X23, the release client's raise — Opus implementer (live), Opus reviewer

**Files:** create `testing/experiments/TKX_ClientRaise/42.20/mod.info` and `media/lua/client/TKX_ClientRaise.lua` (registers a custom event `TKX_ClientRaise` through `LuaEventManager.AddEvent`, a handler that increments `TKX_CR.before`, a handler that calls an undefined global, a handler behind it that increments `TKX_CR.behind`; every field a string, the x127 shape), `testing/profiles/x20-raise.toml` (fixture `two`; `clients = ["admin", "bob"]`; `[client] timeout = 60`; PZTestKit + TKX_ClientRaise + the staged mod; verify on the SERVER side only), `testing/experiments/x202_client_raise.py`; the artifact under `testing/artifacts/x202-<stamp>/`.

- [ ] Read `testing/experiments/x127_raise.py`, `TKX_RaiseProbe`, `x12-raise.toml`, the X23 row in `docs/reference/experiments.md`, #0958 and the raising-probe rule on `lessons.md`. Phases: A `bob` reads `TKX_CR.version` (the mod loaded), B `event.trigger TKX_ClientRaise` on `client:bob`, then `TKX_CR.before/raw_tail/behind` read every 2 s for 30 s on `bob` and on `admin` (the control: `admin` is `-debug`, so its raise is expected to park the debugger — the comparison is the reading), C `bob`'s connection (the server's player list after the trigger; its console tail), D what sets `showLuaDebuggerOnError` on a release client (a `lua.global` read of `getCore():getDebug()` or the field the implementer finds — read, never set). `pzt run` is expected to fail on the parked `admin`; the grade is off the artifact.
- [ ] The artifact; its register rows (`#0958` goes `open -> settled` or stays open with the run named in `bound`, per CLAUDE.md § 4.3); the X23 row in `experiments.md` and the wall map marked `run x202-<stamp>`; the owner sentences on `lessons.md#rules` (the raising-probe rule gains the release-client reading) and `testing-your-mod.md`.
- [ ] Commit the probe mod, profile and driver before the run; the artifact after.

---

### Task 6: The five subscribe-and-read code reads — Opus implementer, Opus reviewer (GATED on the Workshop folders; ruling 7)

**Files:** create `docs/facts/other-mods/nutritionmakessense.md`, `statsapi.md`, `stattweakslib.md`, `apocalipsebrsyncfix.md`, `tooltiplib.md` (one page per neighbour read; the catalog's page shape, `page_lint` profile `facts`); modify `docs/facts/other-mods/catalog.md` (the five rows' build status and the "not installed" lines).

- [ ] At dispatch the controller lists the five folders under the workshop root; an absent folder's page is NOT written and its line in the ledger reads `deferred: <id> absent on 2026-10-06`. For each present folder: the one question the spec asks (Nutrition Makes Sense: does it claim the stat hook; StatsAPI and Stat Tweaks Lib: does either claim the hook or publish a stat registration interface; ApocalipseBR: which desync it fixed and by which mechanism; Tooltiplib: does it own the tooltip height arithmetic), answered as C rows with `repo:`-style pointers into the Workshop files (`ws:<id>/<path>:<line> "<quote>"` if the pointer grammar has the form — read `tools/claimslib.py`; else the page quotes the line and the row's pointer is the page), the mod's version folder named, the read dated.
- [ ] `page_lint` 0; the delta; commit per page.

---

### Task 7: The documentation delta — Sonnet implementer, Opus reviewer

`docs/areas/packaging.md` (the shipped shape as 1.0.0's; the staged layout and the manifest as what a mod can do (C rows on the tool); the self-report as measured (x201); the `## Open` decisions this plan settles leave the list with their rows — which files in the version dir, the checksum discipline, `versionMin` — and the ones still blocked stay, each naming the Workshop id it waits on; new `## Rules` lines as rule rows: stage from one command and never edit the staged bytes; diff the manifest before every update and treat a script change as a server event; print the self-report; lint before every boot), `docs/platform/mod-anatomy.md` (its three decision lines settled or narrowed), `docs/platform/harness.md` (the lint gate; the two-client staged boot), `docs/areas/testing-your-mod.md` (the release profile; X23's reading), `docs/platform/lessons.md#rules` (the raising-probe rule's release-client half), `docs/areas/open-questions.md` (X23 settled or re-bounded; the five reads' Open lines for the deferred ones), `docs/reference/experiments.md`, `docs/reference/artifacts.md`, the skills `nutrition-packaging` (re-synced to the rule lines) and `pz-mod-testing`, CLAUDE.md § 3 (the pytest count) and § 5 (the lint-before-boot line; the staging command).

- [ ] `page_lint` 0 on every touched page; `doc_lint` 0; `claims_delta --dry-run` clean. Commit `Docs: packaging and release as shipped (packaging, mod-anatomy, harness, testing-your-mod, lessons; the staged build, the self-report, the lint gate, X23; the skills)`.

---

### Task 8: The close — Opus whole-pass review, fix wave, gates, memory, push

- [ ] The whole-pass review against spec § 4.9 and § 5 row 9 sentence by sentence; every § 3 gate; one consolidated fix wave and its re-review; CLAUDE.md § 3's count; the memory block in both scopes; `git push origin main`; the Rulings block and the § 7 list in the ledger; `Plan 9: complete`.

## Self-Review

- **Spec coverage:** layout (Task 1's checks, Task 2's manifest); manifest (Task 2); Workshop discipline (Task 1's staging and server-event diff, the README's update procedure); compatibility pages (Task 6, gated; Task 2's COMPATIBILITY.md); the operator guide (Task 2); the release notes naming every neighbour (Task 2 + its test); X20/X22 (ruling 8); the five code reads (Task 6); the self-report (Task 2, measured in Task 4); the lint before every boot (Task 3); MoodleFramework detected never required (Task 2's `frameworks=`); the failure mode documented (the README).
- **Placeholders:** none; ruling 5's type-test rule is #2547 and #2717 on `packaging.md#rules`.
- **Type consistency:** `check`/`stage`/`manifest`/`diff` named once (Task 1) and used by Task 4; `lint_paths` named once (Task 3); `TKX_CR` fields named once (Task 5).
