# Slice 07 — T1 Profile builder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put a mod under test on the golden fixture from one declarative file: `testing/profiles/<name>.toml` names the base fixture, the mods (workshop id or local path) and the sandbox overrides; `pzt run --profile <name>` and `pzt scenario --profile <name>` boot that combination, prove the mods actually loaded, and fail fast (before the hold) when one did not — plus `tools/mod_lint.py`, the L0 layout check that says whether a mod is even shaped for B42.

**Architecture:** `testing/pzt/profile.py` parses the TOML with `tomllib`, resolves every `[[mods]]` entry to `(mod_id, source_dir)` against `paths.HARNESS_MODS` and `mods.workshop_index()`, and hands `cli.cmd_run` / `scenario.run` a `Mods=` list, a source map, sandbox overrides and post-join bus probes. Placement stays where it already is: `harness.install` gains a `sources`/`skip` pair so a profile mod is copied from an arbitrary folder (`-nosteam` searches only `<cachedir>/mods`, spike S3). Sandbox overrides are **merged** into the fixture's own `SandboxVars.lua` instead of replacing it. `tools/mod_lint.py` is standalone (paths and/or workshop ids), stdlib, in `doc_lint.py`'s shape.

**Tech Stack:** Python 3.13 stdlib (`tomllib`), `pzt`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades C/M/W; brief commits without attribution (`Slice 07: …`); **one live server+client session at a time**; never `-safemode`; the game install and the workshop folder are **read-only**; defaults + `docs/decisions.md`; stdlib only; `cd` into the repo in every shell call (the cwd resets between calls).

---

## Header

- Slice: **07** · Phase T1 · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: — (no dependency on 05/06; unblocks 08–13) · Estimate: 3 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`. Jar toolchain (not needed here): `cd C:\Users\Angus\pz-b42 && ./pz.sh …`.
- `pzt` package (`testing/pzt/`), signatures this slice edits, verbatim:
  - `harness.install(mods_dir, mod_ids, workshop=True)` — harness ids from `paths.HARNESS_MODS = {"PZTestKit": …}`, everything else via `mods.install(mods_dir, mod_id)`; returns the ids it could not place.
  - `mods.mod_id_of(mod_dir)` (reads `42*/mod.info` first, then `common/`, then root), `mods.workshop_index()` → `{mod_id: (mod_dir, workshop_item_id)}` over `WORKSHOP_DIR/*/mods/*`, `mods.find(mod_id)`.
  - `Server(cache, name="pzt", port=27261, rcon_port=27015, mods=("PZTestKit",), admin_pw=…, rcon_pw=…, log_path=None, echo=None, workshop=True, workshop_items=())`; `Server.seed(sandbox=None)` calls `harness.install(...)` then `update_ini(self.ini, {... "Mods": ";".join(self.mods) ...})` and, if `sandbox`, `write_sandbox_vars(self.sandbox_path, sandbox)`.
  - `MOD_MISSING_RX = re.compile(r'required mod "([^"]+)" not found')` in `server.py`; `Server._reader` appends every hit to `server.mods_not_found` (echoed as `[server] mod not found at load: X`). `Client` has the same regex and list.
  - `session.make_server(run_dir, rec=None, port=None, rcon_port=None, mods=None, name="pzt", sandbox=None, workshop=True, workshop_items=())`, `session.make_client(run_dir, user, server, rec=None, debug=None, safemode=False, launcher="java", workshop=True)`, `Timeline.mark(phase, **kw)`, `hold`, `teardown`, `write_report`.
  - `cli.cmd_run(a)` builds server → clients → `ping` → `session_ready` → `hold` → teardown, then fails on `mods_not_found`, non-baseline `server.errors` or client `lua_error`. `scenario.run(a)` (slice 04) takes `--fixture/--side/--user/--speed/--timeout`.
  - `bus.parse_ack(result)` → `(ok, value)`, JSON bodies decoded; `fx.load(name)`, `fx.fixture_dir(name)`; `paths.new_run_dir(prefix)`, `paths.WORKSHOP_DIR = D:\SteamLibrary\steamapps\workshop\content\108600`, `paths.TESTING`, `paths.ADMIN_USER = "admin"`.
- Spike **S3** (`docs/testing/spikes.md`): under `-nosteam` `ZomboidFileSystem.getAllModFolders`' `workshop`/`steam` roots are both gated on `SteamUtils.isSteamModeEnabled`, so only `<cachedir>/mods` is searched; there is no server `-modfolders`; **a mod the game cannot find is a WARN, not a failure** — the server boots and clients join without it. The S3 subject is the mod this slice reuses.
- The fixture excludes `mods/` (`fixture.SERVER_SKIP`/`CLIENT_SKIP`), so a profile overlays mods on a restored copy **per run and never re-provisions**; the fixture record's own mod list is untouched. Harness `trait.check` (shared, `PZTestKit_Core.lua:426`) returns `{keenHearingExcludesDeaf, keenHearingExcludesHardOfHearing, keenPerceptionLoaded}` — the ready-made probe that a mod took effect.
- `data/mod-inventory.json` (230 mod folders, `tools/mod_inventory.py`) is the corpus for the lint sweep and for slice 08's catalog.

## Questions

1. What does a test profile have to declare so a mod under test is reproducibly installed on the golden fixture — mods by workshop id **and** by local path, sandbox overrides, client/server flags — and what is the smallest schema that covers slices 08–13?
2. How does a profile's sandbox override compose with the fixture's own SandboxVars without silently resetting the fixture's settings?
3. What exactly happens when a profile names a mod the game cannot find, how early can the run detect it, and does the server's own line reach the report?
4. L0: which properties of a B42 mod folder are checkable statically, and how does the installed 230-mod corpus score against them (how many would a profile silently mis-resolve)?
5. Does a two-mod profile (harness + one real workshop mod) actually boot, join and run the mod's code — proven by state, not by absence of errors?

## Method

### Task 1: `tools/mod_lint.py` + tests (no live server)

**Files:** Create `tools/mod_lint.py`, `tools/tests/test_mod_lint.py`; Modify `tools/README.md`.

**Interfaces (produces):** `python tools/mod_lint.py <path|workshop-id> …` (no args = every mod under `WORKSHOP_DIR`), prints `path: LEVEL: rule: detail`, then a count; exit 1 if any `ERROR`. Module API mirrors `doc_lint.py`: `Finding = namedtuple("Finding", "path level rule detail")`, `lint_mod(mod_dir) -> [Finding]`, `lint(targets) -> [Finding]`.

Rules (L0), with the corpus result each was verified against **now** (230 folders, 42.20.4):

| Rule | Level | Check | Corpus |
|---|---|---|---|
| `version-dir` | ERROR | at least one folder matching `^42(\.\d+){0,2}$` | 230/230 pass |
| `mod-info` | ERROR | a `mod.info` exists in the newest version dir **or** in `common/` or the root | 229 pass; `3782784855/Skill Recovery Journal` has only `42.20.1/media` → no `mod.info` anywhere → invisible to `mods.workshop_index()` (index size 229 vs 230) |
| `mod-info-place` | WARN | `mod.info` is inside the version dir (B42 reads that one first) | 224 pass; 6 fall back: AutoCook (3388721641), RemoveAllItems (3413255058), EN_Newburbs (3520263838), gasmask (3701820916), WorkingKnowledge (3717099183), Skill Recovery Journal (3782784855) |
| `id` | ERROR | `id=` present and non-empty | 229 pass (same one fails) |
| `id-agree` | ERROR | every `mod.info` under the folder declares the same `id` | 0 failures |
| `media` | WARN | `media/` exists inside the chosen version dir | run and record |
| `loadstring` | ERROR | no `loadstring(` in any `.lua` under the folder (removed in 42.20.x — `docs/modding/patterns.md:69`) | **0 users** across the corpus (matches `docs/mods-survey/approved-modlist.md:13`) |
| `folder-id` | INFO | folder name == `id` | 51 differ — informational only: `mods.install` keeps the folder name because "the game keys on mod.info, not the folder" |

- [x] **Step 1: Write `tools/mod_lint.py`.** Version dirs sort by parsed tuple, not by string:

```python
VERSION_RX = re.compile(r"^42(\.\d+){0,2}$")

def version_dirs(mod_dir):
    """Newest first. Tuple-parsed: a string sort puts '42.9' above '42.20', and three-part
    names ('42.20.1', shipped by Skill Recovery Journal 2503622437) are real."""
    hits = [(tuple(int(x) for x in e.split(".")[1:]), e) for e in sorted(os.listdir(mod_dir))
            if VERSION_RX.match(e) and os.path.isdir(os.path.join(mod_dir, e))]
    return [e for _, e in sorted(hits, reverse=True)]
```

  `read_info(path)` parses `key=value` lines (shape of `mod_inventory.parse_modinfo`, keys lowercased, last wins); `lint_mod` walks `*.lua` once for `loadstring`; an all-digits target is a workshop item id and expands to `WORKSHOP_DIR/<id>/mods/*`.
- [x] **Step 2: Tests** (`tools/tests/test_mod_lint.py`, style of `test_doc_lint.py`: `sys.path.insert` + `tempfile.TemporaryDirectory`) — a good synthetic mod (`42/mod.info` with `id=Good`, `42/media/lua/shared/x.lua`) lints clean; the **synthetic bad layout** (`bad/media/lua/shared/x.lua` containing `loadstring("return 1")`, `mod.info` only at the root, no version dir) raises exactly `{version-dir, loadstring}` and exits 1; `mod.info` in `common/` only → `mod-info-place` WARN and exit 0; disagreeing ids in `42/` and `42.20/` → `id-agree`; `version_dirs` orders `["42", "42.9", "42.20", "42.20.1"]` as `["42.20.1", "42.20", "42.9", "42"]`.
- [x] **Step 3: Corpus sweep** — `cd /c/Users/Angus/repos/project_zomboid && python tools/mod_lint.py > /tmp/modlint.txt; python tools/mod_lint.py 3685392864` → Expected: the whole-corpus run reports the 1 ERROR and 6 WARN rows above (exit 1); the KeenPerception run reports **0 findings, exit 0**. Paste both counts into the Task-5 doc.
- [x] **Step 4: Commit** — `git commit -m "Slice 07: mod layout lint (L0)"`

### Task 2: `testing/pzt/profile.py` + the placement plumbing (no live server)

**Files:** Create `testing/pzt/profile.py`, `testing/tests/test_profile.py`; Modify `testing/pzt/{harness.py,server.py,client.py,session.py}`.

**Interfaces (produces):** `profile.load(name) -> Profile` with `.name .path .fixture .mods .sources .skip .sandbox .users .verify .hold .safemode .launcher .server_timeout .client_timeout`; `profile.ProfileError` (a `SystemExit` subclass, like `fx.load`'s, so the CLI prints and exits without a traceback).

- [x] **Step 1: Placement plumbing.** `harness.install` gains two keyword-only-in-spirit params (default behaviour byte-identical for every existing caller):

```python
def install(mods_dir, mod_ids, workshop=True, sources=None, skip=()):
    """... `sources` maps a mod id to a folder copied verbatim (a profile's workshop or local
    mod) and wins over HARNESS_MODS and the workshop index; `skip` ids are named in Mods= on
    purpose but NOT placed -- the game's missing-mod path (S3-A) -- and are not reported missing."""
    sources = sources or {}
    for mod_id in mod_ids:
        if mod_id in skip:
            continue
        src = sources.get(mod_id) or HARNESS_MODS.get(mod_id)   # rest of the loop unchanged
```

  `Server.__init__` and `Client.__init__` take `mod_sources=None, mod_skip=()`, store `self.mod_sources = dict(mod_sources or {})` / `self.mod_skip = tuple(mod_skip)` and pass them through their `harness.install(...)` call in `seed()` / `prepare()`. `make_server` gains `mod_sources=None, mod_skip=()` and forwards them; `make_client` gains the same two defaulting to the server's (`server.mod_sources if mod_sources is None else mod_sources`) — the client's `Mods=` already comes from `server.mods`, so no other call site changes. `cmd_attach`'s bare `Server(...)` stub keeps the defaults.
- [x] **Step 2: Sandbox merge** (`server.py`). `write_sandbox_vars` writes a *partial* table — applied to a restored fixture it would replace the server's 1020-line file (verified: `testing/fixtures/default/cache/server/Server/pzt_SandboxVars.lua`, 189 top-level keys, 86 nested, 5 nested tables, CRLF) and silently reset the fixture's own `Zombies = 6` to the default. Add beside it:

```python
# Top-level options sit at exactly four spaces; the five nested tables (Basement, Map,
# ZombieLore, ZombieConfig, MultiplierConfig) open with `= {` at that same indent and hold
# their options at eight, so the lookahead both protects a table opener and keeps `Map` out
# of sandbox_keys() -- a profile naming it fails validation instead of no-op'ing.
SANDBOX_KEY_RX = re.compile(r"^ {4}(\w+) = (?!\{)")

def sandbox_keys(path):          # the settable options of an existing file, for validation
    with open(path, encoding="utf-8", errors="replace") as fh:
        return [m.group(1) for m in map(SANDBOX_KEY_RX.match, fh) if m]

def merge_sandbox_vars(path, overrides):
    """Rewrite only the named top-level keys, keeping every other option (and the server's
    comments) as the fixture had them. -> (applied, appended); CRLF preserved."""
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    pending = {k: ("true" if v is True else "false" if v is False else str(v))
               for k, v in overrides.items()}
    out = []
    for line in text.splitlines():
        m = SANDBOX_KEY_RX.match(line)
        hit = m and m.group(1) in pending
        out.append(f"    {m.group(1)} = {pending.pop(m.group(1))}," if hit else line)
    applied, appended = [k for k in overrides if k not in pending], sorted(pending)
    if appended:                       # before the file's own closing brace (col 0)
        close = max(i for i, l in enumerate(out) if l.strip() == "}")
        out[close:close] = [f"    {k} = {pending[k]}," for k in appended]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nl.join(out) + nl)
    return applied, appended
```

  `Server.seed` chooses: `merge_sandbox_vars` when `os.path.exists(self.sandbox_path)` (restored fixture), `write_sandbox_vars` when not (fresh `provision` cache — unchanged). Echo the applied/appended lists.
- [x] **Step 3: Write `profile.py`.** Resolution and validation happen entirely before any process starts:

```python
"""Test profiles (testing/profiles/<name>.toml): fixture + mods under test + sandbox
overrides. A profile never mutates the fixture -- the fixture excludes mods/, so the overlay
is rebuilt per run (S3: under -nosteam only <cachedir>/mods is searched; everything named
here is copied in)."""
import difflib, glob, os, tomllib
from . import fixture as fx, mods as modindex
from .paths import ADMIN_USER, HARNESS_MODS, TESTING, WORKSHOP_DIR
from .server import sandbox_keys

PROFILES, REPO = os.path.join(TESTING, "profiles"), os.path.dirname(TESTING)

class ProfileError(SystemExit):
    """Anything wrong with a profile, raised before a single process starts."""

def resolve_mod(entry, index):   # index = modindex.workshop_index()
    """One [[mods]] table -> (mod_id, source_dir|None, workshop_item|None)."""
```

  Its branches, in order — each raising `ProfileError` naming the paths it looked at, nothing skipped silently:

| Entry | Source | Errors on |
|---|---|---|
| `copy = false` | `None` — named in `Mods=`, deliberately not placed | no explicit `id` |
| `path = "…"` | absolute, or relative to `REPO` | not a directory |
| `workshop_id = "…"` | the single `WORKSHOP_DIR/<id>/mods/*` folder | item not installed; item ships >1 mod and no `id` to pick with (e.g. `3621968227` ships 3); no folder with that `id` |
| `id` in `HARNESS_MODS` | the repo path (`testing/PZTestKit/PZTestKit`) | — |
| `id` alone | `index[id][0]`, item id from `index[id][1]` | not a harness mod and not installed (message carries `len(index)`) |
| neither | — | "needs one of: id, workshop_id, path" |

  For the `path`/`workshop_id` branches the id comes from `modindex.mod_id_of(src)`: `None` → error pointing at `python tools/mod_lint.py <src>`; a declared `id` that disagrees with it → error quoting both.

  `load(name)` then: resolve the path (`<PROFILES>/<name>.toml`, or the name as given if it ends in `.toml`; a miss lists the profiles that do exist); `tomllib.load` in **binary** mode; `fixture = doc.get("fixture", "default")`; `rec = fx.load(fixture)` (its own `SystemExit` covers a missing fixture); resolve every `[[mods]]` in order, dropping duplicate ids; **prepend `PZTestKit`** if absent (no harness = no bus = no ready marker); validate `[sandbox]` keys against `sandbox_keys(<fixture>/cache/server/Server/<rec["server"]["name"]>_SandboxVars.lua)` and raise `ProfileError` naming the unknown key plus the three closest known keys (`difflib.get_close_matches`); read `[server]`/`[client]`/`[run]`/`[[verify]]` with the CLI's own defaults (`server_timeout=420`, `client_timeout=300`, `users=[ADMIN_USER]`, `hold=5`, `launcher="java"`, `safemode=False`); reject unknown top-level tables.
- [x] **Step 4: Tests** (`testing/tests/test_profile.py`; `sys.path.insert(0, <repo>/testing)` then `from pzt import profile, server`) — all pure-Python, no game: resolution by `workshop_id` **3685392864** → `("KeenPerception", <…/3685392864/mods/KeenPerception>, "3685392864")`; by `id = "PZTestKit"` → the repo path from `HARNESS_MODS`; by `path` pointing at `testing/PZTestKit/PZTestKit`; `copy = false` without `id` → `ProfileError`; a bogus `workshop_id = "1"` → `ProfileError` mentioning the workshop dir; an unknown sandbox key (`Zombiess = 6`) → `ProfileError` suggesting `Zombies`; a profile without `PZTestKit` gets it prepended at index 0; `merge_sandbox_vars` on a 4-line fixture copy rewrites `Zombies = 6` → `4`, appends an unlisted key before the final `}`, leaves a nested `        ZombiesDragDown = true,` and the `    Map = {` opener untouched, and keeps CRLF.
- [x] **Step 5: Run** — `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests testing/tests -q` → Expected: all green (14 pre-existing + the new ones).
- [x] **Step 6: Commit** — `git commit -m "Slice 07: profile loader and mod placement sources"`

### Task 3: `pzt run --profile` / `pzt scenario --profile` (no live server)

**Files:** Modify `testing/pzt/cli.py`, `testing/pzt/scenario.py`; Create nothing.

- [x] **Step 1: CLI wiring.** Add `p.add_argument("--profile", default=None, help="testing/profiles/<name>.toml: mods under test + sandbox overrides")` to the `run` and `scenario` subparsers (both keep `--fixture`; the profile's `fixture` wins and the run prints which). In `cmd_run`, before `fx.load`:

```python
prof = profile.load(a.profile) if a.profile else None
rec = fx.load(prof.fixture if prof else a.fixture)
users = a.clients or (prof.users if prof else None) or list(rec["clients"])
server = make_server(run_dir, rec, port=a.port, rcon_port=a.rcon_port,
                     mods=prof.mods if prof else None,
                     mod_sources=prof.sources if prof else None,
                     mod_skip=prof.skip if prof else (),
                     sandbox=prof.sandbox if prof else None)
```

  then, when `prof`, a `tl.mark("profile", name=…, fixture=…, mods=";".join(prof.mods), sandbox=…)` so the first printed line of the run says exactly which combination is under test, and `report.json` gains a `"profile"` block (name, path, resolved sources, sandbox).

- [x] **Step 2: Fail fast.** Immediately after `tl.mark("server_started", …)`, before any client is launched:

```python
if server.mods_not_found:
    tl.mark("mods_not_found", mods=",".join(server.mods_not_found))
    for line in grep_file(server.log_path, MOD_MISSING_RX, limit=5):
        tl.mark("mod_missing_line", detail=line)
    raise RuntimeError(f"mods not found at load: {','.join(server.mods_not_found)}")
```

  (`grep_file` moves from `spikes.py` to `session.py` and `spikes.py` imports it from there — one definition, two callers.) The existing end-of-run `mods_not_found` check stays as the client-side net. The raise lands in `cmd_run`'s existing `except (RuntimeError, TimeoutError)` → `error` mark → teardown → `RESULT: FAIL`, and the report carries the server's own line verbatim. Cost of a broken profile drops from ~1 min + hold to ~20 s.
- [x] **Step 3: Verify probes.** Between `session_ready` and `hold`, run the profile's `[[verify]]` list:

```python
def verify(prof, server, clients, tl):
    """Bus probes proving the mods took EFFECT, not merely that the server did not complain:
    a mod can be absent (S3-A) and the run still look clean. `expect` is matched as a
    substring of json.dumps(parsed ack)."""
    out = []
    for v in prof.verify:
        side = v.get("side", "server")
        ok, val = parse_ack((server if side == "server" else clients[0]).send(v["cmd"], v.get("args", "")))
        passed = bool(ok) and v.get("expect", "") in json.dumps(val)
        tl.mark("verify", side=side, cmd=v["cmd"], ok=passed, got=json.dumps(val)[:100])
        out.append({**v, "ok": passed, "got": val})
    return out
```

  A failed probe sets `result = f"FAIL: verify {cmd}"`; the list goes into `report.json` under `"verify"`.
- [x] **Step 4: `scenario.run`** — same three lines for `prof`/`rec`/`make_server` (plus `mod_sources`/`mod_skip`/`sandbox`), the same post-`server_started` fail-fast, and `a.user` defaults to `prof.users[0]` when a profile is given. The scenario artifact gains `"profile": a.profile`.
- [x] **Step 5: Smoke without the game** — `python testing/pzt run --profile nope` → Expected: `profile 'nope' not found (…\testing\profiles\nope.toml); have: missing-mod, mod-under-test`, exit 1, **no java process started** (`python testing/pzt doctor` still reports `PZ java processes: none`).
- [x] **Step 6: Commit** — `git commit -m "Slice 07: pzt run/scenario --profile"`

### Task 4: The two profiles and the live acceptance (LIVE — one session at a time)

**Files:** Create `testing/profiles/mod-under-test.toml`, `testing/profiles/missing-mod.toml`, `testing/profiles/README.md`.

The mod under test is **KeenPerception, workshop item `3685392864`** — 15 KB total, `42/mod.info` (`id=KeenPerception`, no `require=`, no sandbox options), one shared Lua file that removes the Keen Hearing ↔ Deaf/Hard-of-Hearing trait exclusivity, already proven to load under `-nosteam` by spike S3, and readable back through the shipped `trait.check` command. `mod_lint` gives it 0 findings (Task 1 Step 3).

- [x] **Step 1: Write the profiles** (verbatim):

```toml
# testing/profiles/mod-under-test.toml — the T1 acceptance profile: harness + one real
# workshop mod on the golden fixture. Doubles as the template for slices 09-11.
fixture = "default"
description = "PZTestKit + KeenPerception (spike S3's subject), DayLength forced to 15 min."
run = { hold = 5 }
verify = [                    # inline tables: the same array-of-tables as [[verify]] would be
  { side = "server", cmd = "trait.check", expect = '"keenPerceptionLoaded": true' },
  { side = "client", cmd = "trait.check", expect = '"keenPerceptionLoaded": true' },
]                             # bare keys must precede the first table header (TOML)

[[mods]]
id = "PZTestKit"              # harness, copied from the repo (paths.HARNESS_MODS)

[[mods]]
id = "KeenPerception"
workshop_id = "3685392864"

[sandbox]
DayLength = 1                 # 1 = 15 minutes (fixture default 4 = 1 h 30 m)
```

```toml
# testing/profiles/missing-mod.toml — the failure mode: a mod named in Mods= that the game
# cannot find. copy = false places nothing, so this needs nothing installed (spike S3-A).
fixture = "default"
description = "Regression: a profile whose mod never reaches <cachedir>/mods must fail fast."

[[mods]]
id = "PZTestKit"

[[mods]]
id = "NoSuchModHere"
copy = false
```

- [x] **Step 2: Pre-flight** — `python testing/pzt doctor` → Expected: ports free, no PZ java processes, fixture `default` present and build-matched (`42.20.4`), workshop index ~229 mods, pytest available; exit 0. Do not boot if it FAILs.
- [x] **Step 3: The two-mod run** — `python testing/pzt run --profile mod-under-test --hold 5` → Expected: `profile name=mod-under-test fixture=default mods=PZTestKit;KeenPerception sandbox=DayLength=1`, `[server] loading KeenPerception`, `server_started` in ~15 s, `client_ready` in ~35 s, two `verify … ok=True` marks, `RESULT: PASS`, exit 0, ~1 min 15 s total. Record the run id. If a probe returns `keenPerceptionLoaded: false` the mod did not take effect: check `<run>/server/mods/` for the copied folder and grep `server-stdout.log` for `KeenPerception` before changing anything.
- [x] **Step 4: Sandbox proof (M)** — after the run, read `testing/runs/<run-id>/server/Server/pzt_SandboxVars.lua`: `DayLength` must still be `1` and `Zombies` still `6` after the server's own boot-time rewrite (spike S1: the server rewrites the file with defaults and keeps seeded values). Also diff the top-level key count against the fixture's 189 — it must be unchanged. This is the measured evidence that the merge composes rather than replaces.
- [x] **Step 5: The missing-mod run** — `python testing/pzt run --profile missing-mod` → Expected: exit 1, `RESULT: FAIL`, a `mods_not_found mods=NoSuchModHere` mark and a `mod_missing_line` mark carrying `WARN … ZomboidFileSystem.loadModAndRequired> required mod "NoSuchModHere" not found`, **no client launched**, ≈20 s.
- [x] **Step 6: Scenario path** — `python testing/pzt scenario smoke_clock --profile mod-under-test --speed 30` → Expected: PASS, the artifact's `profile` field set. (`smoke_clock` exists — slice 04 shipped it in `server/scenarios/PZTestKit_Scenario_Smoke.lua`, commit 3b1ac80, and `pzt scenario` in `testing/pzt/scenario.py`; a PASS here also proves the profile path through `scenario.run`.)
- [x] **Step 7: Artifacts** — copy the two `report.json` files to `testing/artifacts/<run-id>/report.json` (tracked evidence for the doc's M rows) and add their rows to `testing/artifacts/README.md`; write `testing/profiles/README.md` (one paragraph: what lives here, that blobs never do, the two profiles).
- [x] **Step 8: Commit** — `git commit -m "Slice 07: acceptance profiles and live runs"`

### Task 5: Docs and ledgers

**Files:** Create `docs/testing/profiles.md`; Modify `docs/testing/README.md`, `docs/testing/pipeline-design.md`, `tools/README.md`, `docs/progress.md`, `docs/decisions.md`.

- [x] **Step 1: `docs/testing/profiles.md`** — house skeleton, header `Verified against: 42.20.4 (b0bbce05d5)` + date. Sections: five-line summary; **the TOML schema** (one table: key, type, default, meaning — `fixture`, `[[mods]]` `id`/`workshop_id`/`path`/`copy`, `[sandbox]`, `[server]`, `[client]`, `[run]`, `[[verify]]`), each row graded; **how `-nosteam` mod loading works** (S3: only `<cachedir>/mods`; no `-modfolders`; `WorkshopItems=` needs Steam and stays empty — the numeric id is kept for provenance only); **what a profile changes and what it does not** (overlays `Mods=` and sandbox on a restored copy per run; the fixture record and its world are untouched; options read per boot take effect on a restored world, options baked at world gen do not — list which of the fixture's 189 keys the mod work actually cares about: `Nutrition`, `FoodRotSpeed`, `FridgeFactor`, `StatsDecrease`, `DayLength`); **the missing-mod failure mode** (WARN not error — S3; where it is caught now, what the report shows, and why a clean run is not evidence a mod loaded, hence `[[verify]]`); the L0 lint and its corpus results from Task 1 Step 3; **MP behaviour** (mods are placed on both sides from the same source map; the client reloads Lua with the server's `Mods=` on join, so the server's list is authoritative — `docs/testing/README.md` § How a driven client is controlled); open questions; Sources.
- [x] **Step 2: Inventory updates** — `docs/testing/README.md`: add `--profile <name>` to the `run` and `scenario` rows of the command table, a `testing/profiles/` line in the layout paragraph, and a pointer to `profiles.md`; `docs/testing/pipeline-design.md`: mark **T1 ✅** with the run ids and the measured wall times, and update the `-nosteam ignores the workshop folder` row of the fragility budget to name the profile builder (drop the `-modfolders` alternative — S3 proved it does not exist server-side); `tools/README.md`: add `mod_lint.py` beside `doc_lint.py` with its rules and exit code.
- [x] **Step 3: Lint + tests** — `python tools/doc_lint.py docs/testing tools` → Expected `0 finding(s)` (measured clean today; the 4 open findings live in `docs/mods-survey/teardowns/`, which slices 09–11 own — per the slice-01 decision a slice lints the dirs it touches); `python -m pytest tools/tests testing/tests -q` → green.
- [x] **Step 4a: Commit** — `git commit -m "Slice 07: profiles doc and command inventory"`.
- [ ] **Step 4b: Push** — `git push`. The controller's, at slice close, together with `docs/progress.md`; see § Acceptance results.

## Deliverables

- `testing/pzt/profile.py`; `testing/pzt/{harness,server,client,session,cli,scenario}.py` edits (`sources`/`skip` placement, `merge_sandbox_vars`, `--profile`, fail-fast, `[[verify]]`)
- `testing/profiles/{mod-under-test,missing-mod}.toml` + `testing/profiles/README.md`
- `tools/mod_lint.py` + `tools/tests/test_mod_lint.py`; `testing/tests/test_profile.py`
- `docs/testing/profiles.md`; updates to `docs/testing/{README,pipeline-design}.md`, `tools/README.md`; artifacts under `testing/artifacts/<run-id>/`

## Acceptance checks

1. `python testing/pzt run --profile mod-under-test --hold 5` → `RESULT: PASS`, exit 0, both `trait.check` probes `ok=True` (the two-mod profile: PZTestKit + KeenPerception `3685392864`).
2. `python testing/pzt run --profile missing-mod` → exit 1 with `required mod "NoSuchModHere" not found` in `report.json`, before any client launches.
3. The post-run `pzt_SandboxVars.lua` still has `DayLength = 1`, `Zombies = 6` and 189 top-level keys.
4. `python tools/mod_lint.py` on the corpus: 1 ERROR + 6 WARN (the rows in Task 1) and exit 1; on `3685392864`: 0 findings, exit 0; on the synthetic bad layout: `version-dir` + `loadstring`, exit 1.
5. `python -m pytest tools/tests testing/tests -q` green (14 pre-existing + the new ones); `python tools/doc_lint.py docs/testing tools` → `0 finding(s)`.

## Expected decision points (defaults)

- A profile that does not list `PZTestKit` → **prepend it** (first in `Mods=`): without the harness there is no bus, no ready marker and no `pzt run`. Log it; a profile that genuinely must run harness-free is a later, explicit `harness = false` key.
- Two installed workshop items ship the same mod id → `workshop_index()` keeps whichever it globs first. Default: resolve by `workshop_id` in the profile (never by bare id) whenever `mod_lint` reports a duplicate, and record the pair in the doc.
- A `[sandbox]` key is not a top-level key of the fixture's file (e.g. a nested `ZombiesDragDown`) → **hard error before boot**, not a silent no-op. Nested overrides are out of scope for slice 07; a profile needing one re-provisions a fixture with `pzt provision --sandbox`.
- The two-mod run FAILs on non-baseline server errors caused by the mod itself → that is a finding about the mod, not the profile builder: keep the profile, record the errors in the doc, and swap the subject to `FasterResting` (item `3634568288`, 141 KB, `42/mod.info`, one server-side Lua file, no deps) whose probe is `player.stats` endurance rather than `trait.check`.
- `pzt attach --profile` is **not** implemented (attach builds a `Server` stub and never installs mods); say so in the doc rather than half-wiring it.
- `docs/testing` is not in `doc_lint.STAMPED_DIRS`, so `profiles.md`'s stamp and grades are not machine-enforced. Default: write them anyway, do not widen `STAMPED_DIRS` in this slice (it would flag `pipeline-design.md` and `spikes.md` — 4 findings; `README.md` is in `SKIP_FILES` — that is its own slice-sized cleanup).

## Done protocol

- `docs/progress.md`: 07 → `done` (date, commit range, one-line outcome); **ripples**: (a) profiles exist — slices 08–13 install mods through `testing/profiles/<name>.toml` and never edit the fixture; (b) `tools/mod_inventory.py`'s `pick_version_dir` regex `42(?:\.(\d+))?` misses three-part version folders (`42.20.1`) and sorts by string, so `data/mod-inventory.json` reports the wrong live folder for at least `Skill Recovery Journal` (2503622437) — slice 08 regenerates the inventory with `mod_lint.version_dirs` before picking teardown targets; (c) `pzt/mods.py:mod_id_of` has the same string-sort ordering on `42*/mod.info`; (d) one installed mod (`3782784855/Skill Recovery Journal`) has no `mod.info` at all and is therefore invisible to the workshop index — slice 08's catalog must count 229, not 230.
- `docs/decisions.md` rows: the acceptance subject (KeenPerception `3685392864`, because S3 already proved it loads and `trait.check` reads its effect); `copy = false` as the one knob that reproduces the missing-mod path hermetically; sandbox overrides **merge** rather than replace; `PZTestKit` auto-prepended; `mod_lint` kept standalone (no `--profile` mode) so `tools/` never imports `testing/pzt`; `WorkshopItems=` left empty under `-nosteam`.
- Push. Wave 2 is complete when 05, 06 and 07 are all `done`; the next session takes wave 3's plans (08–11) before continuing.

## Acceptance results (2026-09-10)

Every step above ran and is ticked, with one exception noted at the end. Five tasks, six
commits: `aa61080` (`tools/mod_lint.py` + 19 tests), `da43d4f` (`testing/pzt/profile.py`, the
`sources`/`skip` placement and `merge_sandbox_vars`, + 28 tests), `556e01e`
(`pzt run/scenario --profile`, the fail-fast and `[[verify]]`, + 21 tests), `3cf885b` (the
`profile` mark names the skipped mods), `10581d0` (the two profiles, the three live runs and
their artifacts), plus this task's doc commit. Three live runs produced committed evidence:
`run-20260910-133657`, `run-20260910-133916` and `scenario-20260910-134012`.

1. `python testing/pzt run --profile mod-under-test --hold 5` → **`RESULT: PASS`, exit 0, 93 s**
   (`run-20260910-133657`). Both `trait.check` probes `ok=true`, on the **server and the client**,
   each returning `{"keenHearingExcludesDeaf": false, "keenHearingExcludesHardOfHearing": false,
   "keenPerceptionLoaded": true}` — the mod's effect, not merely its presence. `faults: []`,
   `server_errors: []`, `server_stopped rc=0`. The first console line is the `profile` mark
   verbatim (`profile name=mod-under-test fixture=default mods=PZTestKit;KeenPerception
   sandbox=DayLength=1 skip=none`), and `report.json["profile"]` records what it resolved to: the
   repo kit plus `…\3685392864\mods\KeenPerception`. Artifact:
   [`run-20260910-133657/report.json`](../../../testing/artifacts/run-20260910-133657/report.json).
   Two expectations in the step text were met differently and neither is a failure: there is **no
   `[server] loading KeenPerception` console line** (`Server` echoes only the sandbox merge,
   missing-mod WARNs and error lines — the game's own line is `server-stdout.log:94`), and
   `server_started` came at **36.6 s**, not ~15 s. The two later boots took 13.7 s and 14.0 s,
   which is T0's warm figure for a restored fixture (13.4 s); the 36.6 s gap is **measured, its
   cause is not** — the first boot of the session is the suspected reason and no spike measured
   it. (S1's 57.2 s is a first-*ever* cold start including world/db creation, so it is not the
   comparison either.)
2. `python testing/pzt run --profile missing-mod` → **exit 1, `RESULT: FAIL`, 23 s**
   (`run-20260910-133916`), and it stopped **before any client**: the `timeline` phase list is
   exactly `profile → server_launch → server_started → mods_not_found → mod_missing_line → error →
   server_stopped → faults`, `report.json["clients"]` is `{}` and the run directory has no
   `clients/` folder at all. `mod_missing_line` carries the server's own line verbatim —
   `WARN : Mod  f:0 st:779,293,313 at ZomboidFileSystem.loadModAndRequired> required mod
   "NoSuchModHere" not found` — and one reason is printed once (`faults`:
   `mods not found at load: NoSuchModHere`, `result`: the bare `FAIL`). `server_errors: 0`, which
   is the whole point: to this game a missing mod is a WARN and a clean boot. Artifact:
   [`run-20260910-133916/report.json`](../../../testing/artifacts/run-20260910-133916/report.json).
3. **The post-run `pzt_SandboxVars.lua` kept both values.** Read off
   `testing/runs/run-20260910-133657/server/Server/pzt_SandboxVars.lua` *after* the server's own
   boot-time rewrite (its mtime is 33 s into the boot, so the rewrite really happened):
   `DayLength = 1` (the profile's) and `Zombies = 6` (the fixture's), **189** four-space
   assignments, 45 533 bytes, 1 020 CRLF endings — the fixture's numbers exactly — and `diff`
   against the fixture file is **one hunk, one line**, the seeded one. The scenario run's copy
   reads the same. **Count correction:** 189 is the number of four-space `key = ` lines, five of
   which are the nested-table openers; `server.sandbox_keys()` — the list a profile is validated
   against — therefore returns **184** settable options (184 + 5 = 189, plus 86 nested at eight
   spaces). Both counts are stable across the merge, and the step's "189 top-level keys" is the
   first of them.
4. **`mod_lint` on the corpus: the plan's figures were superseded by the sweep** (its own decision
   point — a different number is a finding, not a failure). Measured `python tools/mod_lint.py`,
   230 folders, ~13 s, **exit 1**: Task 1's sweep this morning reported **85 finding(s): 3 ERROR,
   31 WARN, 51 INFO**, and this task's re-run reports **84: 3 ERROR, 30 WARN, 51 INFO**. Against
   the plan's predicted "1 ERROR + 6 WARN": the ERRORs are `3782784855/Skill Recovery Journal`
   (`mod-info` + `id`: no `mod.info` anywhere) **and** `3774052732/SD_CC_TEST` (`id-agree`:
   `sd_cc_test` in `42/mod.info` and the root vs `SD_CC_TEST_42` in `common/mod.info`) — the plan
   expected `id-agree` to be 0 because it compared only the *resolved* `mod.info` per folder; the
   WARNs are 6 `mod-info-place` (a different 6: MoodleFramework `3396446795` in, Skill Recovery
   Journal out, which the plan counted as passing because `mods.mod_id_of`'s glob accepts any
   `42*` folder) plus 24–25 `media` (all shipping `common/media`, which the plan asked to "run and
   record"). The one-WARN difference between the two sweeps is `3490370700/73fordFalconPS`, whose
   `media/` moved from `common/` into its `42.0/` folder when Steam rewrote that item at 13:47
   today — the corpus is a live tree, and both numbers are recorded with their dates in
   [`docs/testing/profiles.md`](../../testing/profiles.md) § L0. The other two halves of the check
   pass exactly as written: `python tools/mod_lint.py 3685392864` → **`0 finding(s): 0 ERROR,
   0 WARN, 0 INFO across 1 mod(s)`, exit 0**, and the synthetic bad layout (root `mod.info`, no
   version folder, a `loadstring(` in `media/lua/shared/x.lua`) → exactly **`version-dir` +
   `loadstring`, 2 ERROR, exit 1** (re-run in this task, not only cited).
5. `python -m pytest tools/tests testing/tests -q` → **`188 passed in 4.29s`** (119 pre-existing in
   `tools/tests` + 19 `test_mod_lint.py` + 28 `test_profile.py` + 21 `test_cli_profile.py`, plus
   the one slice 06 added after Task 3 measured 187). `python tools/doc_lint.py docs/vanilla
   docs/modding docs/testing references` → **`0 finding(s)`** with `docs/testing/profiles.md` in
   place; the 4 pre-existing findings under `docs/mods-survey/teardowns/` stay deferred by the
   standing ruling in [`docs/decisions.md`](../../decisions.md). `docs/testing` is **not** in
   `doc_lint.STAMPED_DIRS`, so the new doc's stamp and its C/M/W grades are written by hand and
   are not machine-enforced — the plan's decision point, taken as defaulted. Widening
   `STAMPED_DIRS` to `docs/testing` would flag **2 files / 4 findings** — `pipeline-design.md`
   and `spikes.md`, each missing a `Verified against:` stamp and a `## Sources` section; the
   `README.md` the decision point named is skipped by `doc_lint.SKIP_FILES` — and is still its
   own cleanup.

**Two plan expectations moved.** (a) The corpus figures above. (b) A finding that belongs to the
*combination* rather than to the builder: `scenario-20260910-134012` (`smoke_clock --profile
mod-under-test --speed 30`) **PASSed** with the artifact's `profile` field set, but was flagged
`cadence_suspect: true` at `ticks_per_world_min: 0.22` — `DayLength = 1` is a 15-minute day, so
`--speed 30` demands `24 × 30 / 15 = 48` game-minutes of world clock per wall second and the
harness's `EveryOneMinute` ceiling is ~8–10 Hz. Keep `24 × speed / day_minutes ≲ 8`; on
`DayLength = 1` that is `--speed 5`. `smoke_clock`'s own verdict is unaffected (every assertion it
makes is counted in ticks), but nothing fitted against the game clock on that run may be cited,
and slices 09–11 must not template a *timed* scenario off `mod-under-test.toml` without re-reading
`cadence`. Two decision points did **not** fire: KeenPerception loaded and both probes passed on
the first attempt (no swap to `FasterResting`), and the corpus has no duplicate mod ids (229
distinct ids over 230 folders — the gap is Skill Recovery Journal's missing `mod.info`, not a
collision).

**What is not in this task's commit.** Step 4b's `git push` and the `docs/progress.md` half of the
Done protocol — the board row, its commit range and the four ripples — are the controller's
close-out. The `docs/decisions.md` half landed here: eleven slice-07 rows.

**A seventh commit: the final fix wave.** The five task reviews and the whole-branch review closed
in one consolidated commit after the five above. It changed no measured number and re-ran nothing
live; what it did change is disclosed as script skew in
[`testing/artifacts/README.md`](../../../testing/artifacts/README.md) § Script/artifact skew and
as eight further rows in [`docs/decisions.md`](../../decisions.md). Two acceptance checks read
slightly differently at HEAD, neither in its verdict: **check 2**'s console line now names the mod
(`RESULT: FAIL: mods not found at load: NoSuchModHere`, where the committed artifact records the
bare `FAIL`), and the `[[verify]]` probes the wave added to `scenario.run` are evidenced by
`scenario-20260910-151753` — `scenario-20260910-134012` predates them. The wave's own acceptance is
`pzt run --profile mod-under-test --hold 5` and
`pzt scenario smoke_clock --profile mod-under-test --speed 5` (note the speed: `--speed 30` on
this profile's `DayLength = 1` is the cadence finding above). Both ran after the wave committed, on `a6b0b54`:
`run-20260910-151642` **PASS** (70.7 s; both probes true; `took` beside an elapsed `t`) and
`scenario-20260910-151753` **PASS** (66.4 s; both probes ran and passed on the scenario path;
`cadence` 1.018 ticks per game-minute at `24 × 5 / 15 = 8`, the ceiling's own edge). Both are
committed under `testing/artifacts/` with README blocks.
