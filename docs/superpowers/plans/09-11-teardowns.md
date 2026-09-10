# Slices 09–11 — P3b–d Teardowns ×3 — Implementation Plan (one template, run three times)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three mod teardowns whose **MP section is measured, not inferred**: install the mod on the golden fixture through a profile, lint it, read every line of its Lua and scripts, then probe the *same* state on the server and on the client around the mod's own key action with the wave-3 witness commands — and write `docs/mods-survey/teardowns/<mod>.md` with every section of the shipped template filled, stamped, graded and sourced.

**Architecture:** One template executed three times. Slice 08 supplies the picks; Task 1 resolves the subject and reads it cold; Task 2 writes `testing/profiles/teardown-<mod>.toml` (the mod under test on `default`, `[[verify]]` probes that read the mod's *own* effect); Task 3 boots that profile from a Python driver on `testing/experiments/_common.py` and takes paired server/client witness snapshots around the action, writing one artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json`; Task 4 writes the doc; Task 5 lints, updates the ledgers and commits. Nothing here modifies the game install or the workshop folder — profiles copy.

**Tech Stack:** Python 3.13 stdlib, `pzt` (`profile`, `session`, `bus`), `PZTestKit` harness Lua, `tools/mod_lint.py`, `tools/doc_lint.py`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W on every claim row; brief commits without attribution (`Slice 09: …`); **one live server+client session at a time**; never `-safemode`; the game install and the workshop folder are **read-only**; take the default at every decision point and log it in `docs/decisions.md`; stdlib only; `cd` into the repo in every shell call (the cwd resets between calls).

---

## Header

- Slices **09 / 10 / 11** · Phase P3b–d · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: 07 (profiles, `mod_lint`), 08 (the picks + the witness commands) · Estimate: 2 h each, 6 h total.
- **This file is a template.** Run Tasks 1–5 once per mod: slice 09 = pass 1 (`N` = 1), slice 10 = pass 2, slice 11 = pass 3. One commit, one progress row and one artifact per pass.
- **Naming, fixed:** `<MOD>` = the id the mod's `mod.info` **declares**; `<ITEM>` = its workshop item id; `<mod>` = `<MOD>` lowercased with any vendor prefix dropped and non-alphanumerics stripped (`SKITTLE_LongTermPreservation4220` → `longtermpreservation4220`, `simpleStatus` → `simplestatus`). Files: `testing/profiles/teardown-<mod>.toml`, `testing/experiments/td<N>_<mod>.py`, `docs/mods-survey/teardowns/<mod>.md`, artifact `testing/artifacts/td<N>-<stamp>/`.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. Jar toolchain (rarely needed here): `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump`.
- **Profiles (slice 07).** `testing/profiles/<name>.toml`: `fixture`, `[[mods]]` (`id` / `workshop_id` / `path` / `copy = false`), `[sandbox]` (merged into the fixture's 189-key `SandboxVars.lua`, never replaced), `[server]`/`[client]`/`[run]`, and `verify` — bus probes run between `session_ready` and the hold, `expect` matched as a **substring of `json.dumps(parsed ack)`** (`testing/pzt/session.py:162-183`). Everything is resolved and validated before a process starts (`testing/pzt/profile.py`). Run: `python testing/pzt run --profile <name> [--hold N]`; a mod named in `Mods=` that never reaches `<cachedir>/mods` fails the run right after `server_started` (`mods_not_found` + `mod_missing_line` marks). Read `testing/profiles/mod-under-test.toml` — this plan's profiles are that file with the subject swapped.
- **Mod ids are not folder names.** `pzt/mods.workshop_index()` keys on the id in `mod.info` (229 mods indexed). Measured now: item `3774789651`'s folder is `LongTermPreservation4220` while its `42.20/mod.info` declares `id=SKITTLE_LongTermPreservation4220`, so `index["LongTermPreservation4220"]` is `None` and only the declared id works in `Mods=`. `data/mod-inventory.json` is **not** authoritative for ids: `tools/mod_inventory.py:99-106` reads only `<folder>/mod.info` and falls back to the folder basename, which is why that row also reads `name: "?"`, `author: "?"`.
- **Harness.** Global `TK` in `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`; `TK.register(name, fn(argv, kv))`, `TK.result(name, tbl)` → `<cachedir>/Lua/pzt-results/<name>.json`, and **every Java member goes through `TK.call(obj, "method", …)` → `(present, value)`** because Kahlua's "tried to call nil" escapes `pcall` and kills the whole event handler. No `goto`; never `%d` on a Lua number. Command inventory: `docs/testing/README.md`.
- **Wave-3 witness (slice 08's deliverable, consumed here by name):** `witness.fields <player|item> <id> <getter,…>` and `witness.moddata <keys…>`, on both sides, documented in `docs/testing/README.md`. Existing neighbours that show the shape: client `witness.moddata <key>` / `witness.nutrition` / `witness.item` ack `"sent"`, `sendClientCommand` the question, and the server's reply lands in `Events.OnServerCommand` where the client compares and writes `TK.result("witness_<kind>…")` (`client/PZTestKit_Client.lua:94-107,472-521`; `server/PZTestKit_Server.lua:394-430`). The Task-3 driver's `probe()` handles **both** shapes (inline reply or ack-then-result-doc), so slice 08's exact choice does not block this plan.
- **Actions available on the bus** (all in `docs/testing/README.md`): client `eat.action <type>` (queues the real timed action; completes server-side), `moddata.set <k> <v>` + `moddata.transmit`, `item.spawn`, `stats.get`; server `stats.get <user>`, `nutrition.get/set <user> …`, `item.get/set <user> <type> …`, `item.use`, `drink`, `items.count`, `item.script <type>`, `fluid.script <id>`, `recipes.count`, `recipes.craft <name>`, `recipes.evolved <name>`, `sandbox.set`, `trait.set`, `perk.set`. Items are spawned **server-side** with RCON `additem "<user>" "<fullType>" 1` (a client-side `AddItem` is invisible to the server — spike S6).
- **MP facts the teardown measures against** (`docs/modding/patterns.md` § Measured MP sync facts): the **server** owns `Nutrition`, hunger/thirst, weight and item aging; a client write to any of them is overwritten inside ~1.5 s by the 1 Hz `PlayerStatsPacket`; `player:getModData()` reaches the server **only** after `player:transmitModData()`; a client's `sendItemStats` is a no-op; `ItemStatsPacket` carries 39 item-state fields and reuses cached packets, so a zero-valued field can arrive carrying the previous packet's value.
- **Cadence ceiling.** `Events.EveryOneMinute` ceilings around 10 dispatches/wall-second: keep **`24 × speed / day_minutes ≲ 8`**. The fixture's `DayLength = 4` is 90 game-minutes/day, so `--speed 30` sits exactly at 8.0; `DayLength = 1` (15 min) at `--speed 30` measured `ticks_per_world_min: 0.22`, `cadence_suspect: true` (`testing/artifacts/scenario-20260910-134012/scenario-smoke_clock.json`). **Teardown profiles therefore ship no `[sandbox]` block.**
- **Lint gates.** `python tools/mod_lint.py <path|workshop-id>` (L0 layout; ERROR fails); `python tools/doc_lint.py <dirs>` — `docs/mods-survey/teardowns` is a **stamped dir** (`tools/doc_lint.py:8`), so each teardown needs `Verified against: 42.20.4` in the text, a non-empty `## Sources`, no `TODO`/`TBD`, and a C/M/W grade in every row of any table with an `Ev` header column. `python tools/doc_lint.py docs/mods-survey` reports **4 findings today** — the two seeded teardowns (`beyondten.md`, `itemquality.md`) have neither stamp nor `## Sources`; pass 1 backfills them.
- **Evidence.** Measured JSON is committed byte-for-byte under `testing/artifacts/<run-id>/` with a row in `testing/artifacts/README.md`; full run dirs stay in gitignored `testing/runs/`.

## Questions (per mod; the teardown is done when each has a cited answer)

1. **Identity & build**: declared id vs folder name, workshop item, every version dir and the one B42 actually loads, `require=` dependencies, file mtimes, `mod_lint` verdict.
2. **What it does**, player-facing, in five lines.
3. **Architecture**: entry points (`Events.*`, timed-action derivations, context-menu hooks), data model (modData keys / sandbox options / item scripts / recipes), the client/server/shared split, and the files that matter.
4. **Overrides**: which vanilla functions it monkey-patches and which vanilla script blocks it redefines (name collisions against `media/scripts/`), and whether the patches are idempotent.
5. **Storage & wire**: exactly which modData keys on which object, and every `transmitModData` / `sendClientCommand` / `sendServerCommand` / `sendItemStats` site.
6. **MP, measured**: around the mod's key action, which side's copy of each field and modData key changes, whether the other side sees it, and within what window — plus where authority lives and whether the mod depends on an unsynced field (the ItemQuality failure mode).
7. **Compatibility**: load-order sensitivity, the API surface it patches, and collisions with the resident stack (the Girth mods' 110+ command sites, CleanUI's UI surfaces) and with our nutrition mod.
8. **Verdict**: what we adopt, what we avoid, dependency candidate or not.

## Method

### Task 1: Fix the subject and read it cold (no live server)

**Files:** Create `.superpowers/sdd/09-11-teardowns/<mod>-notes.md`.

- [ ] **Step 1: Resolve the subject.** Read `docs/mods-survey/nutrition-mods.md` § the pick and the slice-08 rows of `docs/decisions.md`; take the **first pick in slice 08's stated order that has no `docs/mods-survey/teardowns/<mod>.md` yet**. Default when that list is missing, shorter than three, or ambiguous: the queue in `docs/mods-survey/approved-modlist.md` § Teardown queue, which is also the three open questions in `docs/modding/patterns.md` § Open pattern questions — **`SKITTLE_LongTermPreservation4220`** (item `3774789651`), **`simpleStatus`** (item `2867431511`), **`MoodleFramework`** (item `3396446795`). Write the resolved order into `docs/decisions.md` once (pass 1), then follow it.
- [ ] **Step 2: Identity (C).**

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/mod_lint.py <ITEM>
ls "D:/SteamLibrary/steamapps/workshop/content/108600/<ITEM>/mods"
python -c "import sys; sys.path.insert(0,'testing'); from pzt import mods; \
  print(mods.mod_id_of(r'D:\SteamLibrary\steamapps\workshop\content\108600\<ITEM>\mods\<FOLDER>'))"
```

  Expected: `mod_lint` exits 0 with at most INFO/WARN rows (measured today: `2867431511` → 1 INFO `folder-id`; `3774789651` → 1 INFO `folder-id`; `3396446795` → 1 WARN `mod-info-place: mod.info is 42.0/mod.info, not 42.20/mod.info`). `mod_id_of` prints the id that goes in the profile. An **ERROR** row is a stop: record it and go to the next pick (decision points).
- [ ] **Step 3: Census and read (C).** `find <mod folder> -type f | sort`, `wc -l` on every `.lua`, then one sweep for the architecture signals:

```bash
grep -rnE "Events\.[A-Za-z]+\.Add|sendClientCommand|sendServerCommand|OnClientCommand|OnServerCommand|\
getModData|transmitModData|ModData\.|getNutrition|setCalories|setProteins|setLipids|setCarbohydrates|\
HungerChange|SandboxVars\.|ISBaseTimedAction:derive|^\s*function IS" "<live version dir>"
```

  Read **every** Lua file the sweep touches, end to end, plus every `media/scripts/**/*.txt` block. For each script block, check the name against vanilla: `grep -rl "item <BlockName>" "D:/SteamLibrary/steamapps/common/ProjectZomboid/media/scripts"` — a hit means an override, and its vanilla values come from `data/food-items.json` / `data/recipes.json` rather than a re-read.
- [ ] **Step 4: Cross-check the inventory row.** `python -c "import json;print([m for m in json.load(open('data/mod-inventory.json',encoding='utf-8')) if m['workshop_id']=='<ITEM>'])"` — record `signals`, `top_events`, `lua_kb`, `class`, and any disagreement with Step 3 (the row's `layout` comes from `mod_inventory.pick_version_dir`, whose regex misses three-part version folders and sorts as strings; `tools/mod_lint.py`'s `version_dirs` is the correct answer).
- [ ] **Step 5: Notes.** Write `<mod>-notes.md` with one section per question 1–5 and 7, every claim carrying `mod-relative/path.lua:line`, plus a **Probe plan**: the getters the mod reads (question 5 → `FIELDS`), the modData keys it writes (→ `KEYS`), and the **one key action** Task 3 will trigger, chosen from this menu:

| What Task 1 found | Action Task 3 triggers | Read back |
|---|---|---|
| hooks eating / reads `Nutrition` | client `eat.action Base.Apple` (completes server-side) | fields on both sides at t0 and t+3 s |
| recipes / new items / script overrides | RCON `additem "<user>" "<Base.ModItem>" 1`, then server `recipes.craft <ModRecipe>` and `item.get <user> <type>` | server `item.get` vs client `witness.fields item <id> …` |
| writes player modData | client `moddata.set <key> <v>` then `moddata.transmit` | `witness.moddata <KEYS>` on both sides, before and after the transmit |
| `OnPlayerUpdate` / `EveryOneMinute` simulation | RCON `settimespeed 30`, hold ≥ 60 s wall, restore `settimespeed 1` | snapshots each 20 s; `24 × 30 / 90 = 8.0`, at the ceiling |
| pure client UI, no state of its own | server `nutrition.set <user> calories 2000` | the fields the mod renders, on both sides, at t0 and t+3 s — the mirror it depends on |

- [ ] **Step 6: Commit** — `git commit -m "Slice 0N: <MOD> static read"`.

### Task 2: The profile (no live server)

**Files:** Create `testing/profiles/teardown-<mod>.toml`.

- [ ] **Step 1: Write the profile** (this is `mod-under-test.toml` with the subject swapped; bare keys must precede the first table header):

```toml
# testing/profiles/teardown-<mod>.toml — slice 09-11 pass N: <MOD> under test on the golden
# fixture. No [sandbox] block: DayLength stays the fixture's 4 (90 game-min/day), which is what
# keeps 24 x speed / day_minutes <= 8 if the session accelerates time.
fixture = "default"
description = "PZTestKit + <MOD> (workshop <ITEM>) — teardown N."
run = { hold = 20 }
verify = [
  { side = "server", cmd = "<probe>", args = "<args>", expect = '<substring of the JSON reply>' },
  { side = "client", cmd = "<probe>", args = "<args>", expect = '<substring of the JSON reply>' },
]

[[mods]]
id = "PZTestKit"              # harness, copied from the repo (paths.HARNESS_MODS)

[[mods]]
id = "<MOD>"                  # the id mod.info DECLARES — never the folder name
workshop_id = "<ITEM>"
```

- [ ] **Step 2: Choose the `[[verify]]` probes**, in this order — a clean boot is *not* evidence the mod loaded (spike S3-A): (a) a bus probe that reads the mod's own state — `recipes.craft <ModRecipe>`, `item.script <Base.ModItem>`, `items.count` (a `byType` delta), `witness.moddata <key>`; (b) if the mod has no readable state, leave `verify = []` and prove it in Task 3 by grepping the mod's own boot print out of the run's `clients/<user>/console.txt` / `server-stdout.log` with `session.grep_file`; (c) if it prints nothing either, the evidence is the copied folder under `<run>/server/mods/<FOLDER>` plus an empty `mods_not_found`, and the doc says "loaded; effect not directly readable" as an open question. Log (b) or (c) in `docs/decisions.md`.
- [ ] **Step 3: Validate offline** — `cd /c/Users/Angus/repos/project_zomboid && python -c "import sys;sys.path.insert(0,'testing');from pzt import profile;print(profile.load('teardown-<mod>'))"` → Expected `<Profile teardown-<mod> fixture=default mods=PZTestKit;<MOD> sandbox={}>`, **no java process started**. A wrong id raises `ProfileError` naming the 229 indexed mods; a mod with a `require=` dependency needs that dependency as its own `[[mods]]` entry **before** the subject (`Mods=` order is load order).
- [ ] **Step 4: Commit** — `git commit -m "Slice 0N: teardown-<mod> profile"`.

### Task 3: The measured MP session (LIVE — one session at a time)

**Files:** Create `testing/experiments/td<N>_<mod>.py`.

- [ ] **Step 1: Pre-flight** — `python testing/pzt doctor` → Expected: no PZ java processes, ports 27261/27262/27015 free, fixture `default` present and build-matched, workshop index ~229, exit 0. Do **not** boot on a FAIL.
- [ ] **Step 2: Acceptance run** — `python testing/pzt run --profile teardown-<mod> --hold 5` → Expected: a `profile name=teardown-<mod> fixture=default mods=PZTestKit;<MOD>` mark first, `server_started` ≈ 15 s, `client_ready` ≈ 35 s, every `verify … ok=True`, `RESULT: PASS`, exit 0, ≈ 1 min 15 s. Record the run id for the doc's Sources. A `verify` miss means the mod did not take effect: check `testing/runs/<run-id>/server/mods/` for the copied folder and grep `server-stdout.log` for `<MOD>` before changing anything.
- [ ] **Step 3: Write the driver** — the s05 shape (`testing/experiments/s05_food_scan.py`), boot through the profile:

```python
"""Teardown N: <MOD> measured on a live dedicated server + a real client (slices 09-11).

Paired snapshots of the SAME state on both sides around the mod's one key action, so the
teardown's MP section is measured. Never raises through teardown; the artifact is copied
byte-for-byte after the session."""
import json, os, re, shutil, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
from _common import ask, git_say, hard_kill, save
from pzt import fixture as fx, profile
from pzt.paths import new_run_dir
from pzt.session import Timeline, grep_file, make_client, make_server, teardown, verify

MOD, USER, MIRROR_WAIT = "<MOD>", "admin", 3.0    # 3 s > the 1 Hz PlayerStatsPacket window
FIELDS = "<getter,getter,...>"                     # what Task 1 found the mod READING
KEYS   = "<modDataKey,modDataKey>"                 # what Task 1 found it WRITING
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

prof = profile.load("teardown-<mod>")
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("td<N>")
path = os.path.join(run_dir, "teardown-<mod>.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)
out = {"run_id": run_id, "mod": MOD, "workshop_item": prof.items.get(MOD),
       "profile": prof.report(), "commit": git_say("rev-parse", "--short", "HEAD"),
       "fields": FIELDS, "moddata_keys": KEYS, "snapshots": [], "notes": []}

def probe(side, cmd, args):
    """One witness read. Slice 08's commands answer inline OR in the existing client-witness
    shape (ack 'sent', reply written by OnServerCommand into a result doc) -- take both."""
    t = time.time()
    val = ask(side, cmd, args)
    if isinstance(val, str) and val.strip().startswith("sent"):
        name = "witness_fields" if cmd == "witness.fields" else "witness_moddata"
        try:
            return side.bus.wait_result(name, timeout=20, after=t)
        except (RuntimeError, TimeoutError, OSError) as e:
            return {"error": f"{type(e).__name__}: {e}", "ack": val}
    return val

def snapshot(tag, c):
    row = {"tag": tag, "wall": round(time.time() - t0, 2)}
    for name, side in (("server", server), ("client", c)):
        row[name] = {"fields": probe(side, "witness.fields", f"player {USER} {FIELDS}"),
                     "moddata": probe(side, "witness.moddata", KEYS),
                     "stats": ask(side, "stats.get", USER if name == "server" else "")}
    out["snapshots"].append(row)
    tl.mark("snapshot", tag=tag)
    save(path, out, tl, server)          # evidence on disk before the next phase can wedge
    return row

try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start(); clients.append(c); c.wait_ready()
    tl.mark("session_ready")
    out["build"], out["verify"] = server.build, verify(prof, server, clients, tl)
    out["mod_log_lines"] = grep_file(server.log_path, re.compile(re.escape(MOD)), limit=5)
    snapshot("baseline", c)
    out["action"] = <the one action from Task 1's menu>      # e.g. ask(c, "eat.action", "Base.Apple")
    snapshot("t0", c)
    time.sleep(MIRROR_WAIT)
    snapshot("t+3s", c)
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    save(path, out, tl, server)
    try:
        teardown(tl, server, clients)
    finally:
        hard_kill(server, clients)
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "teardown-<mod>.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.copyfile(path, dest)
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("snapshots", out.get("error")), indent=1)[:6000])
```

- [ ] **Step 4: Run it** — `python testing/experiments/td<N>_<mod>.py` → Expected: ≈ 3 min, three snapshots each carrying a `server` and a `client` block, `wrote …/teardown-<mod>.json`, the artifact copied. Any world change the action made (`settimespeed`) is restored in the same `try` before teardown. Record the run id.
- [ ] **Step 5: Read the result into claims.** For every field and key: which side moved, whether the other followed, and by when (`baseline` → `t0` → `t+3s`). A field that moved on the client and never on the server is an **unsynced-field authority** hazard (`docs/modding/patterns.md` FILTER 1) — say so. Do not re-run to make a number prettier; a surprising reading is the finding.
- [ ] **Step 6: Commit** — `git commit -m "Slice 0N: <MOD> measured MP session"` (driver + artifact).

### Task 4: The teardown doc

**Files:** Create `docs/mods-survey/teardowns/<mod>.md`; Modify `docs/mods-survey/README.md`, `docs/mods-survey/approved-modlist.md`, `docs/modding/patterns.md`, `testing/artifacts/README.md`.

- [ ] **Step 1: Fill the template.** `docs/mods-survey/teardown-template.md` is the fenced block to copy; every one of its parts is required — the three header bullets **Workshop ID / mod ID(s)**, **Build examined (date + version folder used)**, **Author · dependencies · license/permissions posture**, then `## What it does (player-facing)`, `## Architecture` (entry points, data model, client/server split, files that matter), `## MP handling` (what syncs, how, where authority lives, observed or latent desync risks), `## Techniques worth stealing` (with `file:line`), `## Pitfalls / anti-patterns` (and the rule we derive), `## Compatibility notes` (load order, patched API surface, conflicts), `## Verdict for our mod`. Add the two the template predates and `doc_lint` requires here: a **`**Verified against: 42.20.4 (`b0bbce05d5`)**`** line under the title with the date, and a final **`## Sources`** (the run ids and `testing/artifacts/<run-id>/…` paths, the mod files by path:line, the `data/mod-inventory.json` row, the workshop item id, any wiki mirror). Cite mod files as `mod-relative/path.lua:line` and pin the build (workshop id + folder mtime), as the template says.
- [ ] **Step 2: Grade `## MP handling` as a table** with an `Ev` column — one row per field/key measured, `M` with the run id for anything the session read, `C` for anything only read off the code, `W` for workshop/wiki claims. `doc_lint` enforces a C/M/W in every row of a table whose header contains `Ev`.
- [ ] **Step 3: Survey updates** — `docs/mods-survey/README.md`: move the mod from *queued* to a `[<Mod>](teardowns/<mod>.md)` row with why-chosen and status **done**; `approved-modlist.md`: drop it from § Teardown queue and add it to the *Done* line; `docs/modding/patterns.md`: close the § Open pattern question this mod answers (or restate it sharper), and add a KEEP/FILTER row if the teardown earned one; `testing/artifacts/README.md`: a Contents row `td<N>-<stamp>` / `teardown-<mod>.json` / `testing/experiments/td<N>_<mod>.py` / cited-by the new doc, plus a skew note if any fix round followed the run.
- [ ] **Step 4 (pass 1 only): Backfill the seeded teardowns.** Add the stamp line and a `## Sources` section to `docs/mods-survey/teardowns/beyondten.md` and `itemquality.md` — sources are the mod folders (`3765241705/BeyondTen`, `3624538051/ItemQuality`), `data/mod-inventory.json`, and for ItemQuality the pz-b42 `findings/crafted-weapon-quality.md` its own text already names. Do not restate their findings; those two were read, not measured, and stay C.
- [ ] **Step 5: Commit** — `git commit -m "Slice 0N: <MOD> teardown"`.

### Task 5: Lint, ledgers, push

- [ ] **Step 1: Gates** — `cd /c/Users/Angus/repos/project_zomboid && python tools/doc_lint.py docs/mods-survey docs/modding` → Expected `0 finding(s)` (4 today, all in `teardowns/`, cleared by Task 4 Step 4); `python tools/mod_lint.py <ITEM>` → 0 ERROR; `python -m pytest tools/tests testing/tests -q` → green.
- [ ] **Step 2: Ledgers** — `docs/progress.md`: row 09/10/11 → `done` with date, commit range and a one-line outcome naming the run id; add ripples for anything a later slice must know (a technique for 12/13, a compat constraint for 14). `docs/decisions.md`: the pick order, the `[[verify]]` tier used, any scoping ruling, any witness fallback.
- [ ] **Step 3: Push** — `git push`. Then return to Task 1 for the next mod, or, after pass 3, hand off to wave 4 (slices 12–14 plans).

## Worked example — the template applied to `simpleStatus` (verified 2026-09-10, no live run)

The values below were read from the installed corpus while this plan was written; they are what Tasks 1–2 produce for this subject.

- **Task 1 Step 2.** `python tools/mod_lint.py 2867431511` → `2867431511/SimpleStatus: INFO: folder-id: folder 'SimpleStatus' != id 'simpleStatus'`, `1 finding(s): 0 ERROR, 0 WARN, 1 INFO`, exit 0. `mod_id_of` → `simpleStatus`. Version dirs `42`, `42.14`, `42.15`, `42.16`, `common`; B42 loads **`42.16`**, whose `mod.info` reads `id=simpleStatus`, `name=Simple Status`, `modversion=2.260406.1`, no `require=`.
- **Task 1 Step 3.** `42.16` ships **7 client Lua files, 1 580 lines**, no server and no shared code (the `42/` tree still had `server/ss.save.config.lua`; 42.16 dropped it — the split moved). Reads `player:getNutrition():getCalories/getCarbohydrates/getLipids/getProteins/getWeight` at `ss.stats.lua:280,294,308,238,381` and the weight-direction flags `isIncWeight`/`isIncWeightLot`/`isDecWeight` at `ss.stats.lua:404-411`; hooks only `Events.OnCreatePlayer` and `Events.OnKeyPressed` (`ss.main.lua:82-83`); stores its UI config under **one** modData key, `player:getModData()["SimpleStatusConfig"]`, written by `savePlayerData` followed by `player:transmitModData()` (`ISSSBar.lua:17-36`) and read back at `ss.main.lua:15`; zero `sendClientCommand`, zero monkey-patching. Cadence answer for `docs/modding/patterns.md` § Open pattern questions: `SSBar:prerender()` calls `prepareBarInfo()` **every UI frame**, which calls `bar.valueFn(self.player)` (`ISSSBar.lua:451-469,171`) — per-frame, uncached, client-side only.
- **Task 1 Step 4.** Inventory row (item `2867431511`): `signals` `food_nutrition: 12`, `mod_data: 4`, `transmit_mod_data: 1`, `ui_panel: 1`, `events_add: 2`, `require_line: 2`; `lua_kb: 46`; `class: systems(light-lua)`; `layout: 42.16` — agrees with the census.
- **Task 2.** `verify` falls to tier (b): the mod has no state a bus command can read at join (`SimpleStatusConfig` exists only after a player changes the bar), so `verify = []` and the took-effect evidence is its own print, `[SimpleStatus] Showing status bar for player: admin` (`ss.main.lua:62`), grepped out of `testing/runs/<run-id>/clients/admin/console.txt`.

```toml
# testing/profiles/teardown-simplestatus.toml
fixture = "default"
description = "PZTestKit + simpleStatus (workshop 2867431511) — teardown 2."
run = { hold = 20 }
verify = []                   # tier (b): proof is the mod's own console line (ss.main.lua:62)

[[mods]]
id = "PZTestKit"

[[mods]]
id = "simpleStatus"           # declared id; the folder is 'SimpleStatus'
workshop_id = "2867431511"
```

- **Task 3.** Action menu row 5 (pure client UI): `FIELDS = "getCalories,getCarbohydrates,getLipids,getProteins,getWeight"`, `KEYS = "SimpleStatusConfig"`, action `ask(server, "nutrition.set", f"{USER} calories 2000")`. What it measures is the mirror the mod is built on — the server-owned store arriving on the client inside the 1 Hz push — plus, as a second phase, `moddata.set SimpleStatusConfig …` + `moddata.transmit` on the client with `witness.moddata` on both sides on either side of the transmit, which is the boundary `ISSSBar.lua:35` depends on.
- **Expected verdict shape.** Adopt: nothing structural. Avoid: a per-frame uncached read of a server-owned store as *our* update path. Compatibility: it renders the same six numbers our mod will change, so an item-pass balance change is visible to users through this bar; it is a UI neighbour, not a dependency.

## Deliverables (per mod)

- `testing/profiles/teardown-<mod>.toml`
- `testing/experiments/td<N>_<mod>.py` + artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json` + its `testing/artifacts/README.md` row
- `docs/mods-survey/teardowns/<mod>.md` (stamped, graded, every template section filled, `## Sources`)
- Updates: `docs/mods-survey/README.md`, `docs/mods-survey/approved-modlist.md`, `docs/modding/patterns.md`, both ledgers
- `.superpowers/sdd/09-11-teardowns/<mod>-notes.md` (the working read; not a deliverable doc)

## Acceptance checks

1. `python testing/pzt run --profile teardown-<mod> --hold 5` → `RESULT: PASS`, exit 0, every `[[verify]]` probe `ok=True` (or the tier-(b)/(c) substitute recorded in `docs/decisions.md`).
2. `python tools/mod_lint.py <ITEM>` → 0 ERROR.
3. The artifact `testing/artifacts/td<N>-<stamp>/teardown-<mod>.json` exists and holds ≥ 3 snapshots, each with a `server` **and** a `client` block for the same fields and keys.
4. Every section of `docs/mods-survey/teardown-template.md` is filled in `docs/mods-survey/teardowns/<mod>.md`, and its `## MP handling` table has an `Ev` column with at least one **M** row citing the run id.
5. `python tools/doc_lint.py docs/mods-survey docs/modding` → `0 finding(s)` (from 4 today); `python -m pytest tools/tests testing/tests -q` green.
6. Questions 1–8 each have a cited answer in the doc.

## Expected decision points (defaults)

- **Slice 08's picks are missing, fewer than three, or ambiguous** → the `approved-modlist.md` queue order: `SKITTLE_LongTermPreservation4220` (3774789651) → `simpleStatus` (2867431511) → `MoodleFramework` (3396446795). Log it once.
- **A pick fails `mod_lint` with an ERROR, or is not installed** → skip to the next pick, record why in the catalog doc and `docs/decisions.md`; only if the queue runs out does the slice go `blocked` with the exact workshop id to subscribe.
- **The mod declares `require=`** → add each dependency as its own `[[mods]]` entry **before** the subject and lint it too. A dependency that is not installed blocks that pick, not the slice: move to the next pick.
- **Sandbox** → no `[sandbox]` block. `DayLength` stays the fixture's 4; if a teardown must run game-hours, use `--speed ≤ 30` and keep `24 × speed / day_minutes ≲ 8`.
- **Slice 08's witness commands answer in a different shape, or are absent** → `probe()` already takes both shapes; if the commands do not exist, fall back to server `stats.get`/`nutrition.get`/`item.get` and the shipped client `witness.moddata <key>` / `witness.item` / `witness.nutrition`, keep the rows **M**, and record the substitution in `docs/decisions.md` (do **not** add commands to the harness in this slice — that is slice 08's file).
- **The mod's action has no bus route** → measure its *read* path instead (menu row 5): a server-side write, then both sides' copies of the fields the mod renders. The MP claim is then about the mirror the mod depends on, which is the fact our mod needs.
- **The session logs non-baseline server errors caused by the mod** → that is the finding: keep the run, quote the lines in `## Pitfalls / anti-patterns`, and do not tune the profile to hide them.
- **The mod is too big for the 2 h box** (CleanUI is 1 MB of Lua) → read only the files the Task-1 sweep flags on the nutrition/food surface, say exactly that in `## Architecture`, and log the scoping. Never deliver a thin doc silently; a slice past twice its estimate is split into a new catalog entry.
- **A modData key holds a table** → the witness compares stringified values; record the shape from the code and the presence/equality from the run, and note the limitation rather than claiming a deep diff.
- **The mod overrides vanilla script blocks** → the vanilla side of the diff comes from `data/food-items.json` / `data/recipes.json`, not from re-parsing `media/scripts/`.

## Done protocol

- `docs/progress.md`: rows 09 / 10 / 11 → `done` (date, commit range, one-line outcome naming the mod and the run id); resume note while a pass is open; **ripples** for slices 12–14 — a technique the platform reference should prove (12), a jar-locked or unsynced surface for the wall map (13), a compatibility constraint for the feasibility notes (14).
- `docs/decisions.md`: the resolved pick order, each `[[verify]]` tier used, any witness fallback, any scoping ruling, any skipped pick.
- `docs/testing/README.md`: only if a pass adds or changes a harness command (it should not — the witness is slice 08's).
- `testing/artifacts/README.md`: one Contents row per pass, plus a skew note when a fix round followed that pass's live run.
- Commit per slice (`Slice 09: <MOD> teardown`) and `git push`. Wave 3 is complete when 08–11 are all `done`; the next session writes the wave-4 plans (12–14) before continuing.
