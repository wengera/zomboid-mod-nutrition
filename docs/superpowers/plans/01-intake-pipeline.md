# Slice 01 — P1a Intake pipeline (food → body) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document every path by which eating and drinking change a character's hunger, thirst and nutrition stores in PZ 42.20.4 — with each modifier cited to code and the main ones measured on the live server — and build the three tools later slices need (wiki mirror, doc lint, `pzt doctor`).

**Architecture:** Read the jar (`IsoGameCharacter.Eat`, `Food`, `Nutrition`, `EatFoodPacket`) and the shared Lua action, then confirm the numbers by eating real items through new harness commands on the fixture session; write `docs/vanilla/eating-pipeline.md` in the house skeleton; mirror the wiki pages cited.

**Tech Stack:** Python 3.13 (stdlib only), `pzdis` via `./pz.sh`, Kahlua Lua in the `PZTestKit` harness mod, the `pzt` orchestrator, `curl`.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Verified-against build: **42.20.4 (`b0bbce05d5`)** — stamp every doc header.
- Every claim carries an evidence grade: **C** (code), **M** (measured, with run id + results path), **W** (wiki/community).
- Commit style: brief message naming the slice, **no attribution trailer**. Push after the slice.
- One live server+client session on this PC at a time; never modify the game install or the workshop folder.
- Judgment calls: take the default, append a row to `docs/decisions.md`.
- Doc skeleton: summary → model → code map → **MP behaviour** → discrepancies → open questions → sources.

---

## Header

- Slice: **01** · Phase P1a · Status: see `docs/progress.md` · Depends on: — · Estimate: 3 h.

## Cold-start context (read before anything else)

- Repo: `C:\Users\Angus\repos\project_zomboid` (docs library + `testing/` pipeline). Charter: `STRATEGY.md`. Board: `docs/progress.md`. Ledger: `docs/decisions.md`.
- Jar reading: `cd C:\Users\Angus\pz-b42 && ./pz.sh grep <literal> | methods <class> | refs <class> <method> | dump <class> <method> [--desc "(sig)"]`. Class names are internal (`zombie/characters/IsoGameCharacter`).
- Game files: `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\{lua,scripts}`. B42 item scripts are generated files: `scripts/generated/items/food.txt` (722 items, `ItemType = base:food`), `drainable.txt`.
- Live server: `python testing/pzt run --hold N` boots the golden fixture (server ≈ 14 s, admin client in-world ≈ 33 s, zero-zombie world). Harness command bus: `Server.send(cmd, args)` / `Client.send(cmd, args)` in `testing/pzt/bus.py`; commands live in `testing/PZTestKit/PZTestKit/42/media/lua/{shared,client,server}/`. Harness Lua edits need **no** re-provision.
- For ad-hoc experiments write a short Python script that imports `testing/pzt` (`sys.path.insert(0, "testing"); from pzt.session import make_server, make_client, teardown; from pzt import fixture as fx`) — `testing/pzt/spikes.py` shows the pattern (boot → attach → `send` → `bus.wait_result`).
- Prior findings to reuse: `docs/vanilla/nutrition-core.md` (weight model), `docs/testing/spikes.md` (S5 time acceleration, S6 sync facts: nutrition is client-computed and mirrored by the server; no client→server item-field API).
- Wiki: `curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0" "https://pzwiki.net/w/index.php?title=<Page>&action=raw"` (plain fetchers get 403).

## Questions (done when each has a cited answer)

1. What does `IsoGameCharacter.Eat(item, fraction, useUtensil)` do, step by step: which `Food` getters feed which `Stats`/`Nutrition` setters, in what order, with what clamps?
2. What are `getBaseHunger`, `getHungChange`, `getHungerChange` and `getThirstChange` / `getThirstChangeUnmodified` and how do cooked, burnt, rotten, frozen, poison and `RemoveNegativeEffectOnCooked` states modify them and the four nutrition values?
3. How does partial eating (fraction) scale hunger, thirst and the four nutrition values? Is the remainder's nutrition reduced proportionally on the item?
4. What do drinks do: `DrinkFluid` (fluid containers) vs food-type drinks with `ThirstChange`; is thirst ever coupled to nutrition?
5. What does the sandbox option `Nutrition` (`SandboxOptions`) switch off — the stores, the weight update, or both?
6. What do `OnEat` script hooks and `EatType`/`Eattime` change about the pipeline?
7. **MP**: which side runs `Eat` for a player — client (`EatOnClient`?), server (`EatFoodPacket.processServer`), or both — and what does the server's copy of `Nutrition` show right after a client eats?
8. What eating-time formula does `ISEatFoodAction` use (lines 205–253) and does it matter for accelerated tests?

## Method

### Task 1: `tools/wiki_mirror.py` + `tools/doc_lint.py` (with tests)

**Files:**
- Create: `tools/wiki_mirror.py`, `tools/doc_lint.py`, `tools/tests/test_wiki_mirror.py`, `tools/tests/test_doc_lint.py`
- Modify: `tools/README.md` (add both tools)

**Interfaces:**
- Produces: `python tools/wiki_mirror.py <Page> [<Page> ...]` → writes `references/wiki-mirrors/<slug>.md` (slug = page name lower-cased, spaces→`-`), returns exit 0; module function `mirror(page: str, out_dir: str) -> str` (path written). Mirror header (exact keys the lint checks): `**Source:** <url>`, `**Fetched:** YYYY-MM-DD`, `**Wiki page version:** <from {{Page version|X}} or "unstamped">`, `**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors`. Then `## Digest` (3–8 lines written by the agent afterwards; the tool writes `_digest pending_`) and `## Wikitext` with the raw text in a ```` ```wikitext ```` fence.
- Produces: `python tools/doc_lint.py [paths...]` (default: `docs/ references/`) → prints one line per finding `path:line: rule: detail`, exit 1 if any. Rules: `stamp` (docs under `docs/vanilla`, `docs/modding`, `docs/feasibility`, `docs/mods-survey/teardowns` must contain `Verified against: 42.20.4`), `placeholder` (`TODO`, `TBD`, `_digest pending_` anywhere under `docs/` and `references/`, except `docs/superpowers/` and `docs/progress.md`), `sources` (a `## Sources` heading followed by at least one non-blank line), `grades` (every markdown table in the stamped docs has a column header named `Ev` or a cell matching `\b[CMW]\b` in each row — implement as: if a table's header row contains `Ev`, every body row must have `C`, `M` or `W` in that column), `mirror-header` (every file in `references/wiki-mirrors/` except `README.md` has the four header keys above).

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_wiki_mirror.py
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import wiki_mirror

SAMPLE = "{{LangSwitch}}\n{{Page version|42.11.0}}\n'''Nutrition''' is a mechanic."

def test_render_has_header_and_fence():
    md = wiki_mirror.render("Nutrition", "https://pzwiki.net/wiki/Nutrition", SAMPLE, "2026-09-09")
    assert "**Wiki page version:** 42.11.0" in md
    assert "**License:** CC BY-NC-SA 3.0" in md
    assert "```wikitext" in md and SAMPLE in md

def test_slug():
    assert wiki_mirror.slug("Nutritional values") == "nutritional-values"

def test_mirror_writes_file(monkeypatch):
    monkeypatch.setattr(wiki_mirror, "fetch_raw", lambda page: SAMPLE)
    with tempfile.TemporaryDirectory() as d:
        p = wiki_mirror.mirror("Nutrition", d)
        assert p.endswith("nutrition.md") and os.path.exists(p)
```

```python
# tools/tests/test_doc_lint.py
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import doc_lint

def _write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text); return p

def test_stamp_and_sources_required():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nbody TODO\n")
        rules = {f.rule for f in doc_lint.lint([d])}
        assert {"stamp", "placeholder", "sources"} <= rules

def test_clean_doc_passes():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5), 2026-09-09\n\n| Item | Ev |\n|---|---|\n| a | C |\n\n## Sources\n\n- jar\n")
        assert doc_lint.lint([d]) == []

def test_grade_missing_flagged():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5)\n\n| Item | Ev |\n|---|---|\n| a | |\n\n## Sources\n\n- jar\n")
        assert any(f.rule == "grades" for f in doc_lint.lint([d]))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd C:\Users\Angus\repos\project_zomboid && python -m pytest tools/tests -q`
Expected: import errors / failures (modules do not exist yet). If pytest is missing: `pip install pytest`.

- [ ] **Step 3: Implement `tools/wiki_mirror.py`**

```python
#!/usr/bin/env python3
"""Mirror PZwiki pages as raw wikitext with provenance (method rule 3 in STRATEGY.md)."""
import datetime, os, re, subprocess, sys

RAW = "https://pzwiki.net/w/index.php?title={page}&action=raw"
VIEW = "https://pzwiki.net/wiki/{page}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "references", "wiki-mirrors")

def slug(page):
    return re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")

def fetch_raw(page):
    url = RAW.format(page=page.replace(" ", "_"))
    r = subprocess.run(["curl", "-sS", "-A", UA, "--max-time", "30", url], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"fetch failed for {page}: {r.stderr.strip()[:200]}")
    return r.stdout

def page_version(wikitext):
    m = re.search(r"\{\{Page version\|([^}|]+)", wikitext)
    return m.group(1).strip() if m else "unstamped"

def render(page, url, wikitext, date):
    return (f"# Wiki mirror — {page}\n\n**Source:** {url}\n**Fetched:** {date}\n"
            f"**Wiki page version:** {page_version(wikitext)}\n"
            f"**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors\n\n"
            f"## Digest\n\n_digest pending_\n\n## Wikitext\n\n```wikitext\n{wikitext.rstrip()}\n```\n")

def mirror(page, out_dir=OUT):
    text = fetch_raw(page)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug(page) + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(page, VIEW.format(page=page.replace(" ", "_")), text, datetime.date.today().isoformat()))
    return path

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(mirror(p))
```

- [ ] **Step 4: Implement `tools/doc_lint.py`**

```python
#!/usr/bin/env python3
"""House-style lint for the reference library (spec: evidence & documentation standard)."""
import collections, os, re, sys

Finding = collections.namedtuple("Finding", "path line rule detail")
STAMP_RX = re.compile(r"Verified against: 42\.20\.4")
PLACEHOLDER_RX = re.compile(r"\bTODO\b|\bTBD\b|_digest pending_")
STAMPED_DIRS = ("docs/vanilla", "docs/modding", "docs/feasibility", "docs/mods-survey/teardowns")
SKIP_DIRS = ("docs/superpowers",)
SKIP_FILES = ("docs/progress.md", "README.md")
MIRROR_KEYS = ("**Source:**", "**Fetched:**", "**Wiki page version:**", "**License:**")

def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")

def _tables(lines):
    """Yield (start_line, header_cells, body_rows) for each markdown table."""
    i = 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append((j, [c.strip() for c in lines[j].strip("|").split("|")]))
                j += 1
            yield i, header, rows
            i = j
        else:
            i += 1

def lint_file(path, root):
    rel = _rel(path, root)
    if any(rel.startswith(s) for s in SKIP_DIRS) or any(rel.endswith(s) for s in SKIP_FILES):
        return []
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    out = []
    stamped = any(rel.startswith(d) for d in STAMPED_DIRS)
    if stamped and not STAMP_RX.search(text):
        out.append(Finding(rel, 1, "stamp", "missing 'Verified against: 42.20.4'"))
    for n, line in enumerate(lines, 1):
        if PLACEHOLDER_RX.search(line):
            out.append(Finding(rel, n, "placeholder", line.strip()[:80]))
    if stamped:
        m = re.search(r"^## Sources\s*$", text, re.M)
        body = text[m.end():].strip() if m else ""
        if not m or not body:
            out.append(Finding(rel, len(lines), "sources", "missing or empty '## Sources'"))
        for start, header, rows in _tables(lines):
            if "Ev" in header:
                col = header.index("Ev")
                for ln, cells in rows:
                    if col >= len(cells) or not re.search(r"\b[CMW]\b", cells[col]):
                        out.append(Finding(rel, ln + 1, "grades", "row without C/M/W evidence grade"))
    if "references/wiki-mirrors/" in rel:
        for key in MIRROR_KEYS:
            if key not in text:
                out.append(Finding(rel, 1, "mirror-header", f"missing {key}"))
    return out

def lint(roots):
    out = []
    for root in roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".md"):
                    out += lint_file(os.path.join(dirpath, f), root)
    return out

if __name__ == "__main__":
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = sys.argv[1:] or [repo]
    findings = lint(roots)
    for f in findings:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(findings)} finding(s)")
    sys.exit(1 if findings else 0)
```

Note: `lint([repo])` walks the whole repo; `_rel` paths are relative to the root passed, so run it as `python tools/doc_lint.py` (repo root default) or with the repo path.

- [ ] **Step 5: Run the tests; fix until green**

Run: `python -m pytest tools/tests -q` — Expected: 6 passed.

- [ ] **Step 6: Run the lint on the real library and record the baseline**

Run: `python tools/doc_lint.py`. Expected: findings in the existing docs (nutrition-core.md has `TODO`s and no `Ev` column yet; the two existing mirrors lack the new header keys). Fix the mirrors by re-mirroring them in Task 6 (`Modding hub`? check `references/wiki-mirrors/README.md` for their page names) and fix `nutrition-core.md` in Task 7. Do not silence rules.

- [ ] **Step 7: Commit**

```bash
git add tools/wiki_mirror.py tools/doc_lint.py tools/tests tools/README.md
git commit -m "Slice 01: wiki mirror and doc lint tools"
```

### Task 2: `pzt doctor`

**Files:**
- Create: `testing/pzt/doctor.py`
- Modify: `testing/pzt/cli.py` (add the `doctor` subparser → `doctor.run`)

**Interfaces:**
- Produces: `python testing/pzt doctor` → prints one line per check with `ok` / `WARN` / `FAIL`, exit 1 on any FAIL. Checks: (1) PZ processes: any `java.exe` whose command line contains `ProjectZomboid` (`tasklist /V` is not enough; use `wmic process where "name='java.exe'" get ProcessId,CommandLine` or `powershell -Command "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | Select ProcessId,CommandLine"`) → WARN listing pids (never kill); (2) ports 27261, 27262, 27015 free (`netstat -ano`) → FAIL if bound; (3) fixture `default` present (`fixture.load`) and its `build` equals the installed build (read `version=` from the newest `testing/runs/*/server-stdout.log` if any, else "unknown" → WARN); (4) workshop index reachable (`pzt.mods.workshop_index()` non-empty) → WARN if empty; (5) `pytest` importable → WARN.

- [ ] **Step 1: Write `testing/pzt/doctor.py`**

```python
"""Cold-start hygiene: what a fresh session must know before booting anything. Reports only."""
import os, re, subprocess, glob
from . import fixture as fx, mods
from .paths import RUNS

def _pz_java_pids():
    cmd = ["powershell", "-NoProfile", "-Command",
           "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [ln.split("|", 1)[0] for ln in out.splitlines() if "ProjectZomboid" in ln]

def _ports_in_use(ports):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return [p for p in ports if re.search(rf"[:.]{p}\s", out)]

def _installed_build():
    logs = sorted(glob.glob(os.path.join(RUNS, "*", "server-stdout.log")), key=os.path.getmtime)
    for log in reversed(logs):
        m = re.search(r"\bversion=(\d+\.\d+\.\d+)", open(log, encoding="utf-8", errors="replace").read())
        if m:
            return m.group(1)
    return None

def run(a):
    status = 0
    def report(level, msg):
        nonlocal status
        print(f"{level:4} {msg}")
        if level == "FAIL":
            status = 1
    pids = _pz_java_pids()
    report("WARN" if pids else "ok", f"PZ java processes: {pids or 'none'}" + (" — a previous session may still be running; do not boot until they exit" if pids else ""))
    busy = _ports_in_use([27261, 27262, 27015])
    report("FAIL" if busy else "ok", f"ports 27261/27262/27015: {'in use ' + str(busy) if busy else 'free'}")
    try:
        rec = fx.load("default")
        build = _installed_build()
        if build and build != rec.get("build"):
            report("FAIL", f"fixture build {rec.get('build')} != installed {build}: re-provision")
        else:
            report("ok", f"fixture 'default' present (build {rec.get('build')}, {rec.get('size_mb')} MB)")
    except SystemExit as e:
        report("FAIL", str(e))
    idx = mods.workshop_index()
    report("WARN" if not idx else "ok", f"workshop index: {len(idx)} mods")
    try:
        import pytest  # noqa: F401
        report("ok", "pytest available")
    except ImportError:
        report("WARN", "pytest missing (pip install pytest)")
    return status
```

- [ ] **Step 2: Register it in `cli.py`**

In `main()`, after the `spike` parser: `p = sub.add_parser("doctor", help="cold-start checks; reports, never kills"); p.set_defaults(fn=doctor.run)` and `from . import doctor` at the top.

- [ ] **Step 3: Run it**

Run: `python testing/pzt doctor` — Expected: all `ok` on an idle machine (WARN for pytest if not installed).

- [ ] **Step 4: Commit** — `git add testing/pzt/doctor.py testing/pzt/cli.py && git commit -m "Slice 01: pzt doctor"`

### Task 3: Harness experiment commands (client)

**Files:**
- Modify: `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua` (add commands after `item.tamper`)

**Interfaces:**
- Produces (all via the bus, JSON in the ack):
  - `nutrition.get` → `{calories, carbs, lipids, proteins, weight, hunger, thirst}` (hunger/thirst from `p:getStats():getHunger()` / `getThirst()` — if those getters do not exist, read the public fields `p:getStats().hunger`; record which works in the doc).
  - `nutrition.set <calories|carbs|lipids|proteins|weight> <value>` → the new value read back (setters: `setCalories/setCarbohydrates/setLipids/setProteins/setWeight`).
  - `item.script <FullType>` → script-level values of the item type via `getScriptManager():getItem(type)`: `{HungerChange, ThirstChange, Calories, Carbohydrates, Lipids, Proteins, DaysFresh, DaysTotallyRotten, IsCookable, MinutesToCook, MinutesToBurn}` read with `script:getHungerChange()` … (use `pcall` per getter; missing getters → `null`).
  - `item.state <FullType> <cooked|burnt|rotten|frozen|fresh> ` → applies to the first inventory item of that type: `item:setCooked(true)`, `item:setBurnt(true)`, `item:setRotten(true)` / `item:setAge(item:getOffAgeMax()+1)` if `setRotten` has no effect, `item:setFrozen(true)`, `fresh` = `setAge(0)`; returns `{cooked, burnt, rotten, frozen, age, hungChange, calories}`.
  - `eat <FullType> [fraction=1.0]` → finds the item (spawning it with `AddItem` if absent — note S6: client-spawned items are invisible to the server, fine for a client-side pipeline test), snapshots `nutrition.get`, calls `p:Eat(item, fraction, false)`, snapshots again, returns `{before, after, delta, item: item.script values, itemAfter: {hungChange, calories, carbs, lipids, proteins}}`.

- [ ] **Step 1: Add the commands**

```lua
local function nutritionSnapshot(p)
    local n, s = p:getNutrition(), p:getStats()
    local hunger = (s.getHunger and s:getHunger()) or s.hunger
    local thirst = (s.getThirst and s:getThirst()) or s.thirst
    return { calories = n:getCalories(), carbs = n:getCarbohydrates(), lipids = n:getLipids(),
             proteins = n:getProteins(), weight = n:getWeight(), hunger = hunger, thirst = thirst }
end
TK.register("nutrition.get", function() return nutritionSnapshot(getPlayer()) end)
TK.register("nutrition.set", function(argv)
    local n, v = getPlayer():getNutrition(), tonumber(argv[2])
    local setters = { calories = "setCalories", carbs = "setCarbohydrates", lipids = "setLipids",
                      proteins = "setProteins", weight = "setWeight" }
    local m = setters[argv[1]]
    if not m or v == nil then return "usage: nutrition.set <calories|carbs|lipids|proteins|weight> <value>" end
    n[m](n, v)
    return nutritionSnapshot(getPlayer())
end)
local SCRIPT_GETTERS = { "HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids", "Proteins",
                         "DaysFresh", "DaysTotallyRotten", "IsCookable", "MinutesToCook", "MinutesToBurn" }
local function scriptValues(fullType)
    local s = getScriptManager():getItem(fullType)
    if not s then return nil end
    local out = { fullType = fullType }
    for _, g in ipairs(SCRIPT_GETTERS) do
        local ok, v = pcall(function() return s["get" .. g](s) end)
        if not ok then ok, v = pcall(function() return s["is" .. g](s) end) end
        if ok then out[g] = v end
    end
    return out
end
TK.register("item.script", function(argv) return scriptValues(argv[1]) or ("no script item " .. tostring(argv[1])) end)
local function itemState(it)
    return { cooked = it:isCooked(), burnt = it:isBurnt(), rotten = it:isRotten(), frozen = it:isFrozen(),
             age = it:getAge(), hungChange = it:getHungChange(), baseHunger = it:getBaseHunger(),
             calories = it:getCalories(), carbs = it:getCarbohydrates(), lipids = it:getLipids(), proteins = it:getProteins() }
end
local function findOrSpawn(fullType)
    local inv = getPlayer():getInventory()
    return inv:getFirstTypeRecurse(fullType) or inv:AddItem(fullType)
end
TK.register("item.state", function(argv)
    local it = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local s = argv[2]
    if s == "cooked" then it:setCooked(true)
    elseif s == "burnt" then it:setBurnt(true)
    elseif s == "rotten" then it:setRotten(true); if not it:isRotten() then it:setAge(it:getOffAgeMax() + 1) end
    elseif s == "frozen" then it:setFrozen(true)
    elseif s == "fresh" then it:setAge(0) end
    return itemState(it)
end)
TK.register("eat", function(argv)
    local p = getPlayer()
    local it = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local fraction = tonumber(argv[2]) or 1.0
    local before, script, stateBefore = nutritionSnapshot(p), scriptValues(argv[1]), itemState(it)
    local ok, err = pcall(function() p:Eat(it, fraction, false) end)
    if not ok then return "Eat failed: " .. tostring(err) end
    local after = nutritionSnapshot(p)
    local delta = {}
    for k, v in pairs(after) do delta[k] = v - before[k] end
    local remaining = p:getInventory():getFirstTypeRecurse(argv[1])
    return { fraction = fraction, before = before, after = after, delta = delta, script = script,
             itemBefore = stateBefore, itemAfter = remaining and itemState(remaining) or "consumed" }
end)
```

If `Eat` is not exposed to Lua with three arguments, try `p:Eat(it, fraction)` and record which signature works (decision ledger).

- [ ] **Step 2: Smoke-test on the live session**

Write `testing/experiments/s01_eat_smoke.py` (keep it; later slices reuse the pattern):

```python
import json, sys, time
sys.path.insert(0, "testing")
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown
from pzt.bus import parse_ack

rec = fx.load("default"); run_id, run_dir = new_run_dir("exp01"); tl = Timeline()
server = make_server(run_dir, rec); clients = []
try:
    server.start(); c, _ = make_client(run_dir, "admin", server, rec); c.start(); clients.append(c); c.wait_ready()
    out = {}
    for cmd, args in [("nutrition.get", ""), ("item.script", "Base.Apple"), ("eat", "Base.Apple 1.0"),
                      ("eat", "Base.Apple 0.5"), ("item.state", "Base.Steak cooked"), ("eat", "Base.Steak 1.0"),
                      ("item.state", "Base.Bread rotten"), ("eat", "Base.Bread 1.0")]:
        out[f"{cmd} {args}"] = parse_ack(c.send(cmd, args, timeout=20))[1]
    json.dump(out, open(f"{run_dir}/eat-smoke.json", "w"), indent=1)
    print(json.dumps(out, indent=1)[:4000])
finally:
    teardown(tl, server, clients)
```

Run: `python testing/experiments/s01_eat_smoke.py` — Expected: `eat Base.Apple 1.0` shows `delta.hunger` ≈ the script `HungerChange` (sign per the game's convention) and `delta.calories` ≈ `Calories`; the `0.5` call shows half. Anything else is a finding for the doc, not a reason to stop.

- [ ] **Step 3: Commit** — `git add testing/PZTestKit testing/experiments/s01_eat_smoke.py && git commit -m "Slice 01: harness eat/nutrition/item.script commands"`

### Task 4: Code map — the jar

**Files:** notes only (`docs/superpowers/plans/01-notes.md`, scratch, deleted at the end or kept as an appendix).

- [ ] **Step 1: Dump and read, in this order** (`cd C:\Users\Angus\pz-b42`):

```
./pz.sh dump zombie/characters/IsoGameCharacter Eat --desc "(Lzombie/inventory/InventoryItem;FZ)"
./pz.sh dump zombie/characters/IsoGameCharacter EatOnClient
./pz.sh dump zombie/characters/IsoGameCharacter DrinkFluid --desc "(Lzombie/inventory/InventoryItem;FZ)"
./pz.sh dump zombie/inventory/types/Food getHungChange
./pz.sh dump zombie/inventory/types/Food getHungerChange
./pz.sh dump zombie/inventory/types/Food getThirstChange
./pz.sh dump zombie/inventory/types/Food getCalories      # and getCarbohydrates/getLipids/getProteins: rotten/cooked scaling?
./pz.sh dump zombie/characters/BodyDamage/Nutrition setCalories   # clamps (also setCarbohydrates/setLipids/setProteins)
./pz.sh dump zombie/network/packets/actions/EatFoodPacket processServer
./pz.sh dump zombie/network/packets/actions/EatFoodPacket processClient
./pz.sh grep "Nutrition" --max 30   # find the sandbox option class/field; then dump its reads in Nutrition.update / IsoGameCharacter.Eat
./pz.sh refs zombie/characters/IsoGameCharacter Eat
```

For each `Eat` branch record: the getter used, the multiplier constant (pzdis resolves numeric literals inline), the setter it feeds, and the guard (cooked/rotten/frozen/poison/`RemoveNegativeEffectOnCooked`/utensil).

- [ ] **Step 2: Read the Lua**

`media/lua/shared/TimedActions/ISEatFoodAction.lua` (lines 14, 24–60, 136–200, 205–253), `ISDrinkFluidAction.lua`, and `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua` (search `ISEatFoodAction:new` for the fraction menu: eat all / half / quarter). Note the `isClient()` / `isServer()` branches — who calls `Eat`.

- [ ] **Step 3: Answer Q1–Q6 and Q8 in the notes file** with citations in the house form (`zombie/characters/IsoGameCharacter.Eat(InventoryItem,float,boolean)` @ offset, `ISEatFoodAction.lua:174`).

### Task 5: Measured rows (live experiments)

- [ ] **Step 1: Run the experiment matrix** — extend `s01_eat_smoke.py` into `testing/experiments/s01_eat_matrix.py` covering: fresh / cooked / burnt / rotten / frozen × one representative item each (`Base.Apple`, `Base.Steak`, `Base.Bread`, `Base.Carrots`), fractions 1.0 and 0.25, one drink item with `ThirstChange` (`Base.WaterBottleFull` is drainable — use `Base.OrangeSoda` or the `TestHotDrink`-style food drinks: pick one from `food.txt` with `ThirstChange` and no `HungerChange`), plus the sandbox toggle if it can be flipped at runtime (`getSandboxOptions():set("Nutrition", false)` — try; else document as untested).
- [ ] **Step 2: MP row** — after one `eat`, immediately `witness.nutrition` (existing command) and again after 5 s: does the server mirror move by the same delta? Also grep the server log of the run for `EatFood` / `EatFoodPacket` lines (`-debuglog=Network` is on for clients; the server log is `runs/<id>/server-stdout.log`).
- [ ] **Step 3: Save results** to `testing/runs/<run>/eat-matrix.json` and copy the table into the notes; each row becomes an **M** row in the doc with the run id.

### Task 6: Wiki mirrors

- [ ] **Step 1:** `python tools/wiki_mirror.py Nutrition "Nutritional values" Food Cooking` — then open each mirror and replace `_digest pending_` with a 3–8 line digest (what the page claims that the doc uses or contradicts). Also re-mirror the two existing mirrors so they carry the new header (page names are in `references/wiki-mirrors/README.md`; keep their old digests).
- [ ] **Step 2:** `python tools/doc_lint.py` → the mirror findings must be gone.
- [ ] **Step 3: Commit** — `git add references && git commit -m "Slice 01: wiki mirrors (nutrition, food, cooking)"`

### Task 7: Write `docs/vanilla/eating-pipeline.md`

**Files:** Create `docs/vanilla/eating-pipeline.md`; Modify `docs/vanilla/README.md` (row: eating-pipeline.md — done; `eating-cooking.md` row → point at it), `docs/vanilla/nutrition-core.md` (remove the `TODO`s that slice 01 resolves, add an `Ev` column to its tables or an evidence line per section; leave the `updateCalories` open question for slice 03).

- [ ] **Step 1: Write the doc** in the skeleton. Required content:
  - Summary (5 lines).
  - Model: the full `Eat` algorithm as pseudo-code with constants; **one table of every modifier** (columns: Modifier · Applies to · Effect · Source · Ev); partial-eating rule; drinks; sandbox toggle; `OnEat`/`EatType`/`Eattime`; eating-time formula (`ISEatFoodAction:getDuration`, lines 205–253) and its irrelevance to accelerated tests (timed actions run on real frames).
  - Code map: classes/methods and who calls whom (`ISEatFoodAction:perform` → `IsoGameCharacter.Eat` → `Food` getters → `Nutrition` setters / `Stats`), packets.
  - **MP behaviour**: which side computes (from `EatOnClient` / `EatFoodPacket.processServer` reading + the measured witness row), what the server's `Nutrition` copy does, what a mod must do to change intake for MP players.
  - Discrepancies vs the wiki mirrors (page version 42.11.0 vs 42.20.4).
  - **Predictions for slice 04**: a short section "Inputs for the 3-day scenario": how many calories `setCalories(+X)` per game-day adds (trivially X — but state the clamps found in `setCalories`), and the weight-model summary from nutrition-core.md restated with the clamp bounds, so slice 04 can compute expected weight from calorie samples.
  - Open questions; Sources.
- [ ] **Step 2: Lint** — `python tools/doc_lint.py` → 0 findings (fix the docs, not the lint).
- [ ] **Step 3: Commit** — `git add docs/vanilla && git commit -m "Slice 01: eating pipeline map"`

## Deliverables

- `tools/wiki_mirror.py`, `tools/doc_lint.py`, `tools/tests/*`, `tools/README.md` (updated)
- `testing/pzt/doctor.py`, `testing/pzt/cli.py` (doctor subcommand)
- harness commands `nutrition.get`, `nutrition.set`, `item.script`, `item.state`, `eat` in `PZTestKit_Client.lua`; `testing/experiments/s01_eat_smoke.py`, `s01_eat_matrix.py`
- `references/wiki-mirrors/{nutrition,nutritional-values,food,cooking}.md` (+ re-headed existing mirrors)
- `docs/vanilla/eating-pipeline.md`; `docs/vanilla/README.md` and `nutrition-core.md` updated

## Acceptance checks

1. `python -m pytest tools/tests -q` → all pass.
2. `python tools/doc_lint.py` → `0 finding(s)`.
3. `docs/vanilla/eating-pipeline.md` answers Q1–Q8; the modifier table has an `Ev` column and at least 6 **M** rows citing `exp01-*` run ids; the MP section has at least one **M** row.
4. `python testing/pzt doctor` exits 0 on the idle machine.
5. `python testing/pzt run --hold 5` still passes (harness edits did not break the join).

## Expected decision points (defaults)

- `Eat` Lua signature (3-arg vs 2-arg): default — use whichever works, record it.
- Which drink item to test: default — the first `food.txt` item with `ThirstChange` and no `HungerChange` that is not `Test*`.
- Sandbox `Nutrition` toggle at runtime: default — if `getSandboxOptions():set(...)` has no effect mid-session, document "requires a re-provision with `--sandbox Nutrition=false`" as an open experiment for slice 03 rather than re-provisioning now.

## Done protocol

- `docs/progress.md`: slice 01 → `done`, date, commit hash, one-line outcome; add ripples (e.g. "Eat runs on the client only → slice 04 scenario must be client-side"; "setCalories clamps at N").
- `docs/decisions.md`: one row per default taken.
- Push: `git push origin HEAD`.
