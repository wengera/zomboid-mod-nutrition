# Slice 08 — P3a Nutrition-mod catalog — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer "which mods touch nutrition, on what build, through which APIs" from three independent sweeps — the installed corpus's Lua signals, the same corpus's *script* files (which `mod_inventory.py` has never read), and a Steam Workshop search — grade every row, and pick three installed mods for the slice 09–11 teardowns with stated criteria; plus the Wave-3 tooling the teardowns will measure with: the generic reflective witness `witness.fields` / `witness.moddata` on both harness sides, proven live.

**Architecture:** `tools/mod_inventory.py` gains correct id resolution (via `mod_lint.version_dirs` + `info_chain`) and a `script_nutrition` signal, and regenerates `data/mod-inventory.json`; `tools/workshop_search.py` is a new stdlib+`curl` sweep writing `data/workshop-search.{json,csv}`; the witness pair is registered in `PZTestKit_Core.lua` (shared → both sides) and driven once by `testing/experiments/s08_witness.py` on `_common.py`; everything lands in `docs/mods-survey/nutrition-mods.md`.

**Tech Stack:** Python 3.13 (stdlib only) + `curl`, harness Lua (Kahlua), `pzt`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md`

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; evidence grades **C/M/W** on every claim row; brief commits (`Slice 08: …`) without attribution; **one live server+client session at a time**; never `-safemode`; the game install **and the workshop folder are read-only** (never subscribe, never write there); every judgment call takes the default and gets a `docs/decisions.md` row; house doc skeleton with an **MP behaviour** section; `cd` into the repo in every shell call (the cwd resets between calls).

---

## Header

- Slice: **08** · Phase P3a · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: 07 (profiles + `mod_lint`) · Unblocks: 09–11 · Estimate: 2 h.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; board `docs/progress.md`; ledger `docs/decisions.md`; source rules `docs/references.md` (+ `tools/wiki_mirror.py`, mirrors in `references/wiki-mirrors/`, CC BY-NC-SA). Jar toolchain (rarely needed here) `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump`. Live server `python testing/pzt {run,scenario,doctor}`.
- **The corpus, counted today (2026-09-10):** `D:\SteamLibrary\steamapps\workshop\content\108600` holds **179 workshop item folders** containing **230 mod folders**. `data/mod-inventory.json` has 230 rows. `pzt.mods.workshop_index()` returns **229** — `3782784855/Skill Recovery Journal` ships only `42.20.1/media` + `common/ChangeLog.txt` and has no `mod.info` anywhere (slice-07 ripple (d)). `python tools/mod_lint.py` over the corpus: **85 findings — 3 ERROR, 31 WARN, 51 INFO across 230 mods**, 0 `loadstring`.
- **`data/mod-inventory.json` is wrong about ids.** `mod_inventory.scan_mod` reads only `<mod_dir>/mod.info` and falls back to the folder name, but B42 (and `mod_lint.info_chain`) reads the *newest version folder* first. **20 of the 230 rows carry a folder name, not the id the game resolves** — including the top nutrition candidate: `LongTermPreservation4220` really declares `id=SKITTLE_LongTermPreservation4220`. Others: `EN_Newburbs`→`ThermoNewburbs`, `HorseMod`→`Horse`, `YetAnotherPZLib`→`YAPZLib`, `Big Bottles`→`BigBottles`, five `PALSJs *` folders, three `Spongie*`. A profile's `[[mods]] id` must be the resolved id, so this is fixed here (slice-07 ripple (b)).
- **`mod_inventory.py` never reads script files.** Its `food_nutrition` regex runs on `.lua` only; `.txt` under `/scripts` is merely counted. A separate sweep of `media/scripts/**/*.txt` for `Calories|Carbohydrates|Lipids|Proteins|HungerChange|ThirstChange|DaysFresh|DaysTotallyRotten|FoodType|EvolvedRecipe` finds **10 mods**, of which only **LongTermPreservation4220** also shows a Lua signal. Both sweeps are needed; neither alone is the catalog.
- **Harness facts.** `TK.register(name, fn(argv, kv))`, `TK.result`, `TK.call(obj,"m",…) -> (present, value)`; Kahlua has no `goto`, `%d` on a float is fatal, and **`pcall` does not catch "tried to call nil"** — index before calling, always (`PZTestKit_Core.lua:96-114`). `shared/` loads before `client/`/`server/`, so a name registered in both files resolves to the side-specific one. `TK.json` stringifies Java objects via `toString()`. Results are `<cachedir>/Lua/pzt-results/<name>.json`; the server bus polls every 20 ticks (~1.5 s, spike S4).
- **A name is already taken.** `PZTestKit_Client.lua:94` registers `witness.moddata` as the **S6 sync round-trip** (`sendClientCommand` → server `OnClientCommand` → `sendServerCommand` → the client writes `witness_moddata_<key>.json`). Its callers are `testing/pzt/spikes.py:154,157` only; `witness.nutrition` / `witness.item` have no collision and are also used by `s01_eat_matrix.py:108` and `s02_lifecycle.py:116`. See Task 3 Step 1.
- **MP ownership already established** (slices 01–03, S6): the **server** owns `Nutrition`, hunger/thirst, weight, traits, item aging and the Cooking perk; the 1 Hz `PlayerStatsPacket` overwrites client writes; `ItemStatsPacket` reuses cached packets so zero-valued fields inherit stale values; player modData is **not** auto-synced (`transmitModData()` pushes it, measured in S6); script data is parsed identically on both sides and never synced.
- **Baselines to preserve:** `python -m pytest tools/tests testing/tests -q` → **188 passed**; `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references` → **0 findings** (the repo-wide run has **4** pre-existing findings, both teardowns' missing stamp/Sources, owned by slices 09–11 — leave them). `docs/mods-survey/` is **not** in `doc_lint.STAMPED_DIRS` (only `docs/mods-survey/teardowns` is), so the catalog is written to the standard by hand and checked with Acceptance check 5's one-liner.

## Questions

1. Which installed mods touch nutrition at all — through **Lua** (`getNutrition()`, the four `set*` macro setters, `HungerChange`) and through **script item/recipe definitions** — and how big is each signal?
2. Which nutrition/food mods exist on the Workshop for Build 42 that are **not** installed here, and what does that mean for a corpus scoped to the approved modlist?
3. What is each candidate's real **B42 status**: the version folders it ships, which one the game reads, the id it actually declares, its `mod_lint` level counts, its `require=` chain (installed or not) and its Workshop last-update date?
4. Which **APIs** does each candidate use — `Events.*`, `sendClientCommand`/`OnClientCommand`, `sendServerCommand`/`OnServerCommand`, `getModData`/`transmitModData`, monkey-patching (`function IS…:`), item/recipe script overrides, sandbox options — and what does that predict about its MP behaviour?
5. Which **3** are worth a teardown, by criteria stated before the picks, and in what order does the executor fall through if one fails?
6. Can a generic reflective probe read arbitrary getters and arbitrary modData keys on **both** sides, on a player and on an item, without a per-mod command — and what does it report for a member the build does not expose?
7. **MP:** for the catalogued API classes, which side is authoritative and what does a client-only use of each one actually achieve? (Existing measurements answer most of it; the witness must be able to re-measure it per mod in 09–11.)

## Method

### Task 1: Fix and extend `tools/mod_inventory.py`; regenerate the dataset (no live server)

**Files:** Modify `tools/mod_inventory.py`, `data/mod-inventory.json`, `data/README.md`, `tools/README.md`; Create `tools/tests/test_mod_inventory.py`.

- [ ] **Step 1: Correct id resolution.** `mod_inventory.py` must not keep its own answer to a question `mod_lint` already answers. Import it (both live in `tools/`, so a plain `import mod_lint` works when run as `python tools/mod_inventory.py`; add `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` first so it also works from another cwd) and replace `pick_version_dir` + the `mod.info` read:

```python
import mod_lint                       # version_dirs / info_chain / read_info / media_root

def resolve(mod_dir):
    """(info, version_dirs, chosen_rel, live_dir) exactly as B42 resolves them: the newest
    version folder's mod.info first, then common/, then the root. The old local
    pick_version_dir matched only `42[.N]` (three-part `42.20.1` folders are real) and read
    only <mod_dir>/mod.info, which is why 20 of 230 rows carried a folder name as the id."""
    vers = mod_lint.version_dirs(mod_dir)
    chosen = next((c for c in mod_lint.info_chain(vers)
                   if os.path.isfile(os.path.join(mod_dir, c))), None)
    info = mod_lint.read_info(os.path.join(mod_dir, chosen)) if chosen else {}
    root = mod_lint.media_root(mod_dir, vers)
    return info, vers, chosen, os.path.join(mod_dir, root) if root else mod_dir
```

  `scan_mod` then sets `"mod_id": info.get("id") or ""` (**empty, not the folder name** — an unidentifiable mod is a finding, and `""` is what `workshop_index()` effectively sees), and adds `"mod_id_fallback": os.path.basename(mod_dir)`, `"version_dirs": vers`, `"mod_info_at": chosen`, `"layout": vers[0] if vers else ("common"/"flat(b41?)")`. Keep `parse_modinfo`'s key whitelist for `require` (it strips the leading `\`).
- [ ] **Step 2: The script-nutrition signal.** In the walk, `.txt` files under `/scripts` are currently only counted. Read them too:

```python
SCRIPT_KEYS = re.compile(r"^\s*(Calories|Carbohydrates|Lipids|Proteins|HungerChange|ThirstChange"
                         r"|DaysFresh|DaysTotallyRotten|FoodType|EvolvedRecipe)\s*=", re.M)
SCRIPT_ITEM = re.compile(r"^\s*item\s+(\S+)", re.M)
SCRIPT_MODULE = re.compile(r"^\s*module\s+(\S+)", re.M)
```

  Per mod record `signals["script_nutrition"]` (total key hits), `script_nutrition_keys` (per-key counts), `script_item_blocks`, and `script_modules` (a mod writing `module Base` **overrides vanilla items**; `module <Own>` only adds new ones — LongTermPreservation4220 declares `module Skittles`, so it adds 17 items and overrides none). Also add `bytes` (whole-folder size) and `workshop_item_mtime` (`os.path.getmtime` of the item folder, ISO date) — the offline half of the B42-status answer.
- [ ] **Step 3: Report.** Extend `main()`'s final section to print both signal classes side by side and add a "mods whose folder name != declared id" block. Keep the existing output format otherwise.
- [ ] **Step 4: Tests** (`tools/tests/test_mod_inventory.py`, style of `test_mod_lint.py`: `sys.path.insert` + `tempfile.TemporaryDirectory`) — a synthetic mod with `mod.info` in `42.20/` and a *different* stale `mod.info` at the root resolves to the version-folder id; a mod with no `mod.info` resolves to `""` and keeps `mod_id_fallback`; `42.20.1` beats `42.9`; a `media/scripts/items/x.txt` with two `item` blocks and six nutrition keys yields `script_nutrition == 6`, `script_item_blocks == 2`, `script_modules == ["Base"]`; a `.lua` with `getNutrition()` still yields `food_nutrition == 1`.
- [ ] **Step 5: Regenerate and diff** — `cd /c/Users/Angus/repos/project_zomboid && python tools/mod_inventory.py` → Expected: `230 mods across 179 workshop items`, the class histogram unchanged (173 light-lua · 33 map/tiles · 15 heavy-lua · 5 scripts-only · 4 3d+lua), **20 mod_id values change** (incl. `LongTermPreservation4220` → `SKITTLE_LongTermPreservation4220`), one row's `mod_id` becomes `""` (`3782784855/Skill Recovery Journal`), and the new `script_nutrition` signal fires on exactly these 10 mods:

| mod folder | item | script hits | item blocks | Lua `food_nutrition` |
|---|---|---|---|---|
| LongTermPreservation4220 | 3774789651 | 135 | 17 | 4 |
| HorseMod | 3661336777 | 116 | 56 | 0 |
| OCsPacking | 3626823538 | 76 | 144 | 0 |
| ZVirusVaccine42BETA | 3615135168 | 72 | 162 | 0 |
| GirthsTweaks | 3745960616 | 26 | 6 | 0 |
| 69mini | 2937786633 | 21 | 97 | 0 |
| JadePackingSD | 3779653231 | 18 | 42 | 0 |

  …then `63Type2Van` (3041122351) 7 · `SDQuests` (3745960616) 6 · `biogas` (2925657627) 1, none with a Lua signal. If a count differs, the workshop folder changed since 2026-09-10 — record the new number in the doc and say so; do **not** edit the workshop folder.
- [ ] **Step 6: Docs + commit** — add a `## mod-inventory` section to `data/README.md` (every field, incl. the three new ones and the `mod_id` semantics change) and an entry to `tools/README.md`; `python -m pytest tools/tests testing/tests -q` → **188 + the new tests**, green; `git commit -m "Slice 08: mod inventory reads real ids and script nutrition"`.

### Task 2: `tools/workshop_search.py` — the Workshop sweep (network, no live server)

**Files:** Create `tools/workshop_search.py`, `tools/tests/test_workshop_search.py`, `data/workshop-search.json`, `data/workshop-search.csv`; Modify `data/README.md`, `tools/README.md`.

The Workshop browse page is React-rendered with obfuscated class names, but every result still ships as an `<a href=…filedetails/?id=N">` wrapping an `<img alt="<title>">`. **`--compressed` is mandatory** — without it `curl` returns gzip bytes and every regex misses (verified: 5 876 unreadable bytes vs 679 403 readable).

- [ ] **Step 1: Write the tool.** Stdlib + `subprocess` `curl`, in `wiki_mirror.py`'s shape:

```python
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"
BROWSE = ("https://steamcommunity.com/workshop/browse/?appid=108600&searchtext={term}"
          "&browsesort=trend&section=readytouseitems&requiredtags%5B%5D=Build+42")
ITEM = "https://steamcommunity.com/sharedfiles/filedetails/?id={id}"
RESULT_RX = re.compile(r'sharedfiles/filedetails/\?id=(\d+)"[^>]*>\s*<img[^>]*alt="([^"]+)"')
STAT_RX = re.compile(r'detailsStatRight">([^<]*)')   # [size, posted, updated?] in that order
TITLE_RX = re.compile(r'workshopItemTitle">([^<]*)')
TERMS = ["nutrition", "vitamin", "malnutrition", "diet", "hydration",
         "food overhaul", "cooking overhaul", "spoilage"]

def fetch(url):
    r = subprocess.run(["curl", "-sS", "--compressed", "-A", UA, "--max-time", "40", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None, f"curl rc={r.returncode}: {r.stderr.strip()[:200]}"
    return r.stdout, None
```

  `search(term)` → de-duplicated `[(id, html.unescape(title))]` in page order; `details(item_id)` → `{title, size, posted, updated}` from `STAT_RX`/`TITLE_RX` (`updated` is `None` when only two stats are present, i.e. never updated since posting). One `--details` pass over the union of ids, `time.sleep(1.0)` between requests. Every fetch failure is recorded per row (`"error": …`) and **never raises** — a sweep that loses one page still writes the rest.
- [ ] **Step 2: Join to the corpus.** Load `data/mod-inventory.json`; mark each result `installed: true` with its mod ids when `workshop_id` matches, else `false`. Write `data/workshop-search.json` with the house `meta` block (`build`, `generated`, `tool`, `terms`, `source_url_pattern`, `counts`) and a flat `data/workshop-search.csv` (`workshop_id,title,terms,installed,mod_ids,size,posted,updated,error`).
- [ ] **Step 3: Tests** — parse-only, no network: `RESULT_RX` against a captured 3-result fragment (id + `alt` title, `&#x27;` unescaped to `'`); `STAT_RX` against a two-stat fragment (`updated is None`) and a three-stat one; the corpus join marks a known installed id (`3774789651`) `installed: true` with `SKITTLE_LongTermPreservation4220`; `fetch` with a stubbed `subprocess.run` returning rc=1 yields `(None, "curl rc=1: …")`.
- [ ] **Step 4: Run it** — `python tools/workshop_search.py --details` → Expected: 8 terms, ~30 results each, ≈120–200 distinct ids. The `nutrition` term alone returned these on 2026-09-10 with the `Build 42` tag — quote the B42-relevant ones in the doc and check each against the corpus:

| id | Title | Installed? |
|---|---|---|
| 3690404044 | Nutrition Makes Sense | no |
| 3785515388 | Reasonable Nutrition | no |
| 3782835400 | Realistic Nutrition | no |
| 3078272807 | Nutrition Tweaker Enhanced | no |
| 3736275816 | ApocalipseBR - Nutrition Sync Fix | no |
| 3796644824 | [NUTRITION LAUNDERING PATCH + FEATURES] Long Term Preservation | no |

  …plus `3796753621` (Immersive Addon), `3492090092`, `3426165280` (Fix NaN Nutrition Stats), `3388844542` and ~20 more. **Not one of the 30 is installed here.** Two are load-bearing and must be named in the doc: **`3736275816` "Nutrition Sync Fix"** (someone else hit the MP-sync problem this library exists to characterise) and **`3796644824`**, a third-party patch to our own top teardown pick.
- [ ] **Step 5: The hard constraint.** A Workshop result that is **not installed** cannot be linted, profiled, booted or measured here — the workshop folder is read-only and subscribing needs Steam and a human. Every not-installed row is graded **W** and carries the exact unblocking action ("subscribe to `<id>` in Steam, let it download, re-run `tools/mod_inventory.py`"). **Teardown picks come only from the installed corpus** (Task 5).
- [ ] **Step 6: Commit** — `git commit -m "Slice 08: workshop nutrition search sweep"`.

### Task 3: The generic reflective witness (harness Lua, no live server)

**Files:** Modify `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua`, `testing/pzt/spikes.py`.

- [ ] **Step 1: Free the name.** Rename the client's S6 round-trip `witness.moddata` → **`witness.sync.moddata`** (`PZTestKit_Client.lua:94`) and update its only two callers, `testing/pzt/spikes.py:154` and `:157`. Nothing else changes: `args.kind` stays `"moddata"`, so the result file is still `witness_moddata_pzt_probe.json` and `_witness(...)`'s third argument is untouched; `witness.nutrition` and `witness.item` keep their names (no collision) and their callers in `s01_eat_matrix.py` / `s02_lifecycle.py` are not touched. No committed artifact came from the S6 spike (`testing/artifacts/` holds only exp01/02/03/05/05b/06/06b, run-* and scenario-*), so there is no artifact skew to disclose.
- [ ] **Step 2: Write the pair into `PZTestKit_Core.lua`** (shared → both sides get it), after `trait.check`:

```lua
-- ---- generic reflective witness (both sides, slice 08) -----------------------
-- One command instead of a getter-specific one per mod: 09-11 probe fields nobody has named
-- yet. Every read goes through TK.call, so a member this build does not expose lands in
-- `missing` instead of raising Kahlua's uncatchable "tried to call nil".
TK.WITNESS_MAX = 32                -- keeps one ack line inside the bus's key=value shape

-- ModData's Lua binding is a DOT call (`ModData.getOrCreate("t")`), so TK.call's colon
-- semantics would pass ModData itself as the first argument. Index first, then call, no self.
function TK.callStatic(tbl, name, ...)
    if tbl == nil then return false, nil end
    local f = tbl[name]
    if f == nil then return false, nil end
    return true, f(...)
end

-- kind = "player"|"item"; id = username | "-" | fullType | "#<itemId>" | "<user>/<fullType>"
local function subjectOf(kind, id)
    local user, what = string.match(tostring(id or ""), "^([^/]+)/(.+)$")
    if kind == "player" then
        if TK.side ~= "server" then                        -- a client only ever has its own
            local p = getPlayer()
            if p == nil then return nil, nil, "no local player" end
            return p, tostring(p:getUsername())
        end
        local list, want = getOnlinePlayers(), (user or id)
        for i = 0, list:size() - 1 do
            local p = list:get(i)
            if want == nil or want == "-" or p:getUsername() == want then return p, tostring(p:getUsername()) end
        end
        return nil, nil, "no online player " .. tostring(want)
    end
    local owner, label, err = subjectOf("player", user or "-")   -- `local function` recurses
    if owner == nil then return nil, nil, err end
    local _, inv = TK.call(owner, "getInventory")
    local _, items = TK.call(inv, "getItems")
    if items == nil then return nil, nil, "no inventory list on " .. tostring(label) end
    local target = what or id
    local wantId = string.match(tostring(target), "^#(%d+)$")
    for i = 0, items:size() - 1 do
        local it = items:get(i)
        local _, full = TK.call(it, "getFullType")
        local _, iid = TK.call(it, "getID")
        if (wantId and tostring(iid) == wantId) or (not wantId and full == target) then
            return it, tostring(full) .. " #" .. tostring(iid)
        end
    end
    return nil, nil, "no item " .. tostring(target) .. " on " .. tostring(label)
end

-- witness.fields <player|item> <id> <getter,getter,...>   (zero-argument getters only:
-- an arity mismatch is as fatal as a nil call, so nothing here passes arguments)
TK.register("witness.fields", function(argv)
    if argv[1] ~= "player" and argv[1] ~= "item" then
        return "usage: witness.fields <player|item> <id> <getter,...>"
    end
    local subject, label, err = subjectOf(argv[1], argv[2])
    if subject == nil then return err or "no subject" end
    local out = { side = TK.side, subject = argv[1], id = argv[2], resolved = label,
                  fields = {}, missing = {}, worldAge = getGameTime():getWorldAgeHours() }
    local n = 0
    for name in string.gmatch(tostring(argv[3] or ""), "[^,]+") do
        n = n + 1
        if n > TK.WITNESS_MAX then out.truncatedAt = TK.WITNESS_MAX break end
        local ok, v = TK.call(subject, name)
        if ok then out.fields[name] = v else out.missing[#out.missing + 1] = name end
    end
    out.count = n
    return out
end)

-- witness.moddata [player[:<user>] | item:<id> | global:<name>] <key ...>  ("*"/none = census)
TK.register("witness.moddata", function(argv)
    local first = tostring(argv[1] or "")
    local scope, arg = string.match(first, "^(player):(.+)$")
    if not scope then scope, arg = string.match(first, "^(item):(.+)$") end
    if not scope then scope, arg = string.match(first, "^(global):(.+)$") end
    local from = (scope or first == "player") and 2 or 1
    scope = scope or "player"
    local out = { side = TK.side, scope = scope, arg = arg, values = {}, missing = {},
                  worldAge = getGameTime():getWorldAgeHours() }
    local tbl
    if scope == "global" then
        local ok, t = TK.callStatic(ModData, "getOrCreate", arg)
        if not ok then out.error = "no ModData.getOrCreate on this build" return out end
        tbl = t
    else
        local subject, label, err = subjectOf(scope, arg or "-")
        if subject == nil then out.error = err return out end
        out.resolved = label
        local ok, t = TK.call(subject, "getModData")
        if not ok or t == nil then out.error = "no getModData() on " .. label return out end
        tbl = t
    end
    local keys = {}                                -- the census: what a mod actually stores
    for k, v in pairs(tbl) do keys[#keys + 1] = tostring(k) .. ":" .. type(v) end
    table.sort(keys)
    out.keys, out.keyCount = keys, #keys
    local wanted = 0
    for i = from, #argv do
        if argv[i] ~= "*" then
            wanted = wanted + 1
            if wanted > TK.WITNESS_MAX then out.truncatedAt = TK.WITNESS_MAX break end
            local node = tbl
            for part in string.gmatch(argv[i], "[^%.]+") do    -- dotted paths walk nested tables
                node = (type(node) == "table") and node[part] or nil
            end
            if node == nil then out.missing[#out.missing + 1] = argv[i]
            else out.values[argv[i]] = (type(node) == "table") and node or tostring(node) end
        end
    end
    return out
end)
```

- [ ] **Step 3: Read the file back and check the Kahlua rules** — no `goto`, no `%d`, no `#` on a Java list (`items:size()` is used), every Java member reached through `TK.call`/`TK.callStatic`/`TK.field` **except** `getGameTime():getWorldAgeHours()` and `getOnlinePlayers()`, which are deliberately direct (a build that lost them must fail loudly, matching `TK.bodySnapshot`'s note at `PZTestKit_Core.lua:238-244`).
- [ ] **Step 4: Commit** — `git commit -m "Slice 08: generic reflective witness commands"`.

### Task 4: The live probe (LIVE — one session at a time)

**Files:** Create `testing/experiments/s08_witness.py`; Modify `testing/artifacts/README.md`.

- [ ] **Step 1: Pre-flight** — `python testing/pzt doctor` → Expected: ports 27261/27015 free, no PZ `java.exe`, fixture `default` present and build-matched (42.20.4), workshop index 229, pytest available; exit 0. **Do not boot if it FAILs.**
- [ ] **Step 2: Write the driver** (skeleton, on `_common.py`, in `s05b_drink_probe.py`'s shape — `ask` never raises, `save` runs twice, `hard_kill` always):

```python
# Session setup, teardown and artifact copy are s05b_drink_probe.py's, unchanged: fx.load
# ("default") -> new_run_dir("exp08") -> Timeline/make_server/make_client -> try/except
# (RuntimeError, TimeoutError) -> finally teardown + hard_kill + save + copy into
# testing/artifacts/<run_id>/witness-probe.json. `ask` never raises; `doctor()` goes in meta.
from _common import ask, doctor, git_say, hard_kill, save        # + pzt.{fixture,paths,session}

USER, SPAWN_WAIT = "admin", 2.5
PLAYER_GETTERS = "getUsername,getNutrition,getHoursSurvived,getMaxWeight,getSlicesOfBreadEaten"
ITEM_GETTERS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange,getAge,getModData"

for side, name in ((server, "server"), (c, "client")):           # after tl.mark("session_ready")
    out[f"player_{name}"] = ask(side, "witness.fields", f"player {USER} {PLAYER_GETTERS}")
server.rcon('additem "admin" "Base.Apple" 1'); time.sleep(SPAWN_WAIT)
for side, name in ((server, "server"), (c, "client")):
    out[f"item_{name}"] = ask(side, "witness.fields", f"item Base.Apple {ITEM_GETTERS}")
item_id = (out["item_server"].get("fields") or {}).get("getID")  # never guess an id
out["item_byid"] = (ask(server, "witness.fields", f"item #{item_id} {ITEM_GETTERS}")
                    if item_id else {"skipped": "no getID in the fields reply"})
out["absent_getter"] = ask(server, "witness.fields", f"player {USER} getCalories,getNoSuchThing")
out["moddata_census_server"] = ask(server, "witness.moddata", f"player:{USER} *")
c.send("moddata.set", "pzt_witness v08")
out["moddata_client"] = ask(c, "witness.moddata", "pzt_witness")
out["moddata_server_before"] = ask(server, "witness.moddata", f"player:{USER} pzt_witness")
c.send("moddata.transmit"); time.sleep(2)
out["moddata_server_after"] = ask(server, "witness.moddata", f"player:{USER} pzt_witness")
out["moddata_global"] = ask(server, "witness.moddata", "global:pzt_probe_table *")
out["moddata_item"] = ask(server, "witness.moddata", f"item:{USER}/Base.Apple *")
```
- [ ] **Step 3: Run it** — `python testing/experiments/s08_witness.py` → Expected, in ~2 min: `server_started` ~15 s, `client_ready` ~35 s, `RESULT` written, 0 server errors, 0 client Lua errors, and the artifact showing (a) `player_server` and `player_client` both with a non-empty `fields` map, (b) `item_server` carrying real macros for `Base.Apple` (95.0 kcal / 25.13 / 0.31 / 0.47 per `data/food-items.json`) and `item_client` either matching or differing — **both are results, record which**, (c) `absent_getter.missing == ["getNoSuchThing"]` while `getCalories` is absent on a *player* too (it lives on `Nutrition`, not on `IsoPlayer`) — so `missing` may hold two names; report exactly what came back, (d) the modData triple reproducing S6: client `v08`, server `nil`/missing **before** `transmitModData`, present **after**.
- [ ] **Step 4: Grade the outcome.** These are the M rows the catalog and slices 09–11 cite. If `moddata_global` returns `"no ModData.getOrCreate on this build"`, that is a finding, not a failure: keep the route, record it in the doc, and say the teardowns read global modData through a mod-specific command. If a *player* getter that exists in the jar lands in `missing`, record it — Kahlua's visible surface is narrower than the jar's (slice 05 measured exactly that for the script `Item`'s macro fields).
- [ ] **Step 5: Artifact + commit** — the driver already copies to `testing/artifacts/<run-id>/witness-probe.json`; add its row to `testing/artifacts/README.md` (run id, file, experiment, cited by `docs/mods-survey/nutrition-mods.md` + `docs/testing/README.md`); `git commit -m "Slice 08: live witness probe"`.

### Task 5: Mirrors, the catalog, and the pick

**Files:** Create `docs/mods-survey/nutrition-mods.md`; Modify `docs/references.md`, `references/wiki-mirrors/*` (new), `docs/mods-survey/README.md`, `docs/mods-survey/approved-modlist.md`.

- [ ] **Step 1: Mirrors** — `python tools/wiki_mirror.py Mod_data Networking Lua_event Mod_structure` (all four fetch: 4 139 / 7 904 / 2 876 / 20 586 raw bytes on 2026-09-10). Replace each `_digest pending_` with a real 3–6 line digest (`doc_lint` fails on the placeholder) and flip those rows in `docs/references.md` from ☐ to ● with the mirror link. These four are the API vocabulary the catalog's signal columns are named in.
- [ ] **Step 2: Write `docs/mods-survey/nutrition-mods.md`** — house skeleton, header `Verified against: 42.20.4 (b0bbce05d5)` + date, every table with an `Ev` column carrying C/M/W on **every** row:
  - *Summary* (five lines) and *Method and scope* — the corpus is the **approved modlist** (179 items / 230 mod folders / 229 indexable ids); the Workshop sweep is breadth-only because the workshop folder is read-only.
  - *The three sweeps*, one table each: **Lua signals** (C) — the 10 `food_nutrition` mods with `mod_id`, item, hits, `lua_kb`, net (`send_client_cmd`+`on_client_cmd`+`send_server_cmd`), `mod_data`, `monkey_patch`, `pcall`, sandbox-options, class; verified today as simpleStatus 12 · CleanUI 11 · SkillRecoveryJournal 8 · AutoCook 4 · BeyondTen 4 · LongTermPreservation4220 4 · SomewhatTraitsCore 3 · CustomGamepadUI 1 · MoodleFramework 1 · QuestSystem 1. **Script definitions** (C) — Task 1 Step 5's ten rows plus a `module` column (vanilla override vs new items). **Workshop** (W) — Task 2's rows, `installed` flag, last-update date, unblocking action.
  - *B42 status per candidate* (C + W): version folders shipped / the folder the game reads / declared id / `mod_lint` counts / `require=` chain and whether each dep is installed / Workshop last update. Verified today: LongTermPreservation4220 `42.20`, id `SKITTLE_LongTermPreservation4220`, 0E/0W/1I, no deps, 239 131 bytes (Workshop says "239.131 KB") · simpleStatus `42.16,42.15,42.14,42`, 0E/0W/1I, no deps, posted 2022-09-25 / updated Apr 5 · AutoCook `42.13,42` + `common/`, mod.info **in `common/`** → `mod-info-place` WARN, no deps · MoodleFramework `42.20,42.13,42.0` with mod.info only in `42.0` → WARN, and `42.20/media` ships **only** `MF_ISMoodle.lua` while `MF_Config.lua` exists in `42.0/` and `common/` — record as an open question; do not assert B42's version-folder merge rule · CleanUI `42.19…42.12`, 0 findings, requires `NeatUI_Framework` (installed, 3508537032), 11.3 MB · SkillRecoveryJournal `42.20.1,42.19`, requires `ChuckleberryFinnAlertSystem` (3077900375) and `errorMagnifier` (2896041179), both installed.
  - *API surface* (C): a row per API class × candidate — `Events.*` (each mod's top events), `sendClientCommand`/`OnClientCommand`, `sendServerCommand`/`OnServerCommand`, `getModData`/`transmitModData`, monkey-patching (`global_write_vanilla`: CleanUI 287, SomewhatTraitsCore 56, AutoCook 21), item/recipe script overrides, sandbox options — each with the file:line of one real use.
  - **MP behaviour** (C + M, mandatory): the server owns `Nutrition`/hunger/thirst/weight/traits/aging (slices 01–03); `ItemStatsPacket` carries cooked/burnt/cookingTime/heat and the macro block but **not** age/offAge/offAgeMax/freezingTime, and reuses cached packets so a zero-valued field arrives stale (slice 02); player modData needs `transmitModData()` (S6, re-measured in Task 4 — cite `testing/artifacts/<run-id>/witness-probe.json`). Therefore a **client-only** macro write (simpleStatus's read path, AutoCook's client-side crafting) can only ever show the 1 Hz mirror, and a mod that edits an item's fields client-side desyncs silently (the ItemQuality class of bug). Name the witness commands as the per-mod instrument for 09–11.
  - *Discrepancies*, *Open questions*, *Sources* (mirrors, Workshop URLs + fetch date, artifact paths, jar/Lua citations).
- [ ] **Step 3: Pick three, criteria first.** Criteria, in order: **(1)** installed locally (only an installed mod can be linted, profiled and measured); **(2)** touches the nutrition surface directly (macro writes, script macro definitions, or nutrition reads); **(3)** B42-ready on the current build (version folder, lint, deps installed); **(4)** MP behaviour worth measuring (it writes state, or it reads state the server owns); **(5)** small enough to read whole in a 2 h teardown; **(6)** not already torn down (ItemQuality, BeyondTen are done). Default picks and order:

| # | Mod | Item | Resolved id | Why | Ev |
|---|---|---|---|---|---|
| 1 | LongTermPreservation4220 | 3774789651 | `SKITTLE_LongTermPreservation4220` | The domain twin, and the only nutrition candidate shipping a **42.20** folder. Both mechanisms in one 239 KB mod: 17 new `module Skittles` item blocks with full macro sets (135 script keys) **and** `42.20/media/lua/server/recipe_meats.lua:45-49`, which multiplies all four macros and `HungerChange` by 0.70 on the crafted instance from an `OnCooked` script hook. Server-side write → the exact `ItemStatsPacket` question slice 02 left open, now on a mod. No deps, 0E/0W. | C |
| 2 | simpleStatus | 2867431511 | `simpleStatus` | The read/refresh side: 12 nutrition reads, **all client-side** (`42.16/media/lua/client/ss.stats.lua:238,280,294,308,381,404-411`), 46 KB over 7 files, one `transmitModData`, one `ISPanel`. Measures what a pure client reader can and cannot see while the server owns the store — and it is the UI our own mod would overlap. Newest folder is `42.16`, so it also documents "works, but not shipped for this build". | C |
| 3 | AutoCook | 3388721641 | `AutoCook` | The cooking-pipeline hook points: 21 `function IS…:` redefinitions, 9 `getModData` uses, 41 KB of client Lua, and `mod.info` in `common/` (a live `mod-info-place` WARN — a B42-status finding in its own right). It automates the actions our mod must not break, and it reads `getNutrition()` client-side to choose recipes (`42.13/…/AutoCook.lua:214,329`). | C |

  **Fall-through order** if a pick's teardown profile will not boot or its lint regresses: `SkillRecoveryJournal` (2503622437 — 93 KB, a real `sendClientCommand`/`OnClientCommand` bus, 26 `SandboxVars.` reads, two installed deps) → `MoodleFramework` (3396446795 — the new-nutrient moodle dependency question) → `SomewhatTraitsCore` (3498347699 — 66 monkey-patch sites, the patching exemplar; note item 3498347699 ships **3** mods, so its profile must name `id`). Record whichever is used.
- [ ] **Step 4: Update the survey ledgers** — `docs/mods-survey/README.md`: move the three picks to the top of the teardown queue with their workshop ids and slice numbers (09/10/11) and drop the ones displaced; `docs/mods-survey/approved-modlist.md`: correct its "Domain overlap" table to the regenerated ids and add the script-signal column, and link the new catalog.
- [ ] **Step 5: Lint** — `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → `0 finding(s)`; plus the stamped-rules one-liner in Acceptance check 5. Repo-wide stays at the 4 pre-existing teardown findings. `git commit -m "Slice 08: nutrition mod catalog and teardown picks"`.

### Task 6: Command inventory, ledgers, push

**Files:** Modify `docs/testing/README.md`, `docs/testing/spikes.md`, `docs/testing/pipeline-design.md`, `tools/README.md`, `docs/progress.md`, `docs/decisions.md`.

- [ ] **Step 1: `docs/testing/README.md`** — in the command inventory (the paragraph at `:36-63`), rename the client entry `witness.moddata` → `witness.sync.moddata` and add a **Slice-08 reflective witness** block: `witness.fields <player|item> <id> <getter,…>` and `witness.moddata [player[:<user>]|item:<id>|global:<name>] <key…>`, **both sides**, the `<id>` grammar (`username` / `-` / `fullType` / `#<itemId>` / `<user>/<fullType>`), zero-argument getters only, the `missing` list and why it exists (Kahlua's uncatchable "tried to call nil"), `TK.WITNESS_MAX = 32`, the modData census (`*`) and dotted paths, and the measured results from Task 4 with the artifact path.
- [ ] **Step 2: `docs/testing/spikes.md` § S6** — one sentence noting the client round-trip is now `witness.sync.moddata` (the result file name is unchanged); `docs/testing/pipeline-design.md:97` — same rename, and note that L4 now also has a *reflective* witness that needs no per-mod command.
- [ ] **Step 3: `tools/README.md`** — rows for `workshop_search.py` (usage, terms, the `--compressed` requirement, outputs) and the `mod_inventory.py` change.
- [ ] **Step 4: Ledgers** — `docs/progress.md`: 08 → `done` (date, commit range, one-line outcome) and the **ripples** below; `docs/decisions.md`: the rows below.
- [ ] **Step 5: Push** — `git commit -m "Slice 08: witness inventory, catalog ledgers"` then `git push`.

## Deliverables

- `docs/mods-survey/nutrition-mods.md` (stamped, graded, MP section, Sources) + updates to `docs/mods-survey/{README,approved-modlist}.md`
- `tools/mod_inventory.py` (real id resolution + script-nutrition signal) and a regenerated `data/mod-inventory.json`; `tools/workshop_search.py` + `data/workshop-search.{json,csv}`; `tools/tests/test_{mod_inventory,workshop_search}.py`; `data/README.md`, `tools/README.md`
- Harness `witness.fields` / `witness.moddata` in `PZTestKit_Core.lua` (+ the `witness.sync.moddata` rename in `PZTestKit_Client.lua` and `testing/pzt/spikes.py`); `docs/testing/{README,spikes,pipeline-design}.md`
- `testing/experiments/s08_witness.py` + `testing/artifacts/<run-id>/witness-probe.json` + its `testing/artifacts/README.md` row
- 4 new wiki mirrors (`Mod_data`, `Networking`, `Lua_event`, `Mod_structure`) with digests; `docs/references.md` rows flipped
- `docs/decisions.md` rows (incl. the pick) and the `docs/progress.md` board row + ripples

## Acceptance checks

1. `python tools/mod_inventory.py` → `230 mods across 179 workshop items`; 20 `mod_id` values corrected (incl. `SKITTLE_LongTermPreservation4220`); `script_nutrition` fires on exactly the 10 mods in Task 1 Step 5.
2. `python tools/workshop_search.py --details` writes `data/workshop-search.{json,csv}` with ≥ 8 terms and ≥ 100 distinct ids, every row flagged installed / not-installed.
3. `python testing/experiments/s08_witness.py` → artifact written, 0 server errors and 0 client `lua_error`; `witness.fields` answers on **both** sides for a player **and** an item, `witness.moddata` returns a key census on both sides, and `missing` lists a getter that does not exist.
4. `python tools/mod_lint.py <item>` run for **every** candidate row in the catalog, with its level counts quoted in the doc (verified today: 3774789651 → 1 INFO; 2867431511 → 1 INFO; 3396446795 → 1 WARN; 3388721641 → 1 WARN; 3437629766 → 0; 2503622437 → 1 INFO; 3498347699 → 0 across 3 mods).
5. `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → `0 finding(s)`; and the stamped rules on the new file, mechanically: `python -c "import sys;sys.path.insert(0,'tools');import doc_lint as d;d.STAMPED_DIRS=('docs/mods-survey',);f=d.lint(['docs/mods-survey/nutrition-mods.md']);[print(x) for x in f];sys.exit(1 if f else 0)"` → exit 0.
6. `python -m pytest tools/tests testing/tests -q` → green (188 pre-existing + the new tests).
7. ≥ 3 mods picked with rationale and sources, and the fall-through order recorded.

## Expected decision points (defaults)

- **Name collision on `witness.moddata`** → rename the client's S6 round-trip to `witness.sync.moddata` (2 Python call sites, 1 Lua line, result file unchanged) rather than giving the new command a different name from the spec's. Log it.
- **`mod_inventory` id for a mod with no `mod.info`** → `""`, plus `mod_id_fallback` for the folder name. A folder name silently standing in for an id is what produced the 20 wrong rows; `""` matches what `workshop_index()` sees.
- **Widening `doc_lint.STAMPED_DIRS` to `docs/mods-survey`** → **do not** (it would add 4 more findings on `approved-modlist.md` and `teardown-template.md`, which this slice does not own). Write the stamp/grades/Sources by hand and enforce them with Acceptance check 5's one-liner. Same ruling as slice 07 took for `docs/testing`.
- **A Workshop candidate that is not installed** → catalogue it, grade W, state the unblocking action, and never pick it for a teardown. Do not subscribe; the workshop folder is read-only and Steam needs a human.
- **A Workshop fetch fails or returns no results** → record the failure per term in `data/workshop-search.json`, keep the rest, and fall back to the offline B42-status evidence (version folders, item folder mtime, `mod.info` `modversion`/`versionMin`), grading those rows C instead of W. Never block on the network. And **Steam pages are not mirrored verbatim** (90 KB of obfuscated HTML, not wikitext; `wiki_mirror.py` is a PZwiki tool) → the extracted facts plus URL and fetch date go in the dataset and the doc's Sources; log the deviation from STRATEGY rule 3's mirror-and-digest form.
- **`witness.moddata global:` does not answer** (`ModData.getOrCreate` is a dot-call binding; unverified until Task 4) → keep the route, record "not exposed on 42.20.4" in the doc, and note that 09–11 read global modData through a mod-specific command.
- **A candidate's numbers differ from this plan's** (the workshop folder updates daily) → the *current* reading wins; quote it, and note the delta against 2026-09-10 in the doc. Never edit the workshop folder to reconcile.
- **The live probe FAILs on a harness bug** → fix the Lua, re-run once; if it still fails, ship `witness.fields` alone with the `witness.moddata` failure documented as a finding and mark slice 08 `done` with a ripple, rather than blocking 09–11 (guard rail: a slice past twice its estimate is split, not delivered thin).

## Done protocol

- `docs/progress.md`: 08 → `done` (date, commit range, one-line outcome). **Ripples:** (a) the three picks and their fall-through order are the input to slices 09–11 — `<MOD>` in `09-11-teardowns.md` resolves to LongTermPreservation4220 → simpleStatus → AutoCook; (b) profiles must use the **resolved** id (`SKITTLE_LongTermPreservation4220`, not the folder name) and, for items shipping several mods (3498347699 ships 3, 3624538051 ships 5), must name `id` alongside `workshop_id`; (c) `witness.fields`/`witness.moddata` exist on both sides and are the per-mod instrument for 09–11 and for slice 12's override experiments — no new per-mod command should be written before trying them; (d) `data/mod-inventory.json`'s `mod_id` semantics changed (empty when undeclared) — anything reading it must not assume a non-empty id; (e) the Workshop holds B42 nutrition mods this machine does not have, including a "Nutrition Sync Fix" (3736275816) and a patch to pick #1 (3796644824) — slice 14's feasibility notes should mention them, and a human can unblock a deeper look by subscribing.
- `docs/decisions.md` rows: the three picks with their criteria and the fall-through order; `witness.sync.moddata` rename; `mod_id` = `""` when undeclared; `STAMPED_DIRS` left alone; teardown picks restricted to the installed corpus; Steam pages recorded as extracted facts rather than verbatim mirrors; `tools/workshop_search.py` added as a folded-in source sweep (spec § Structure) rather than as unplanned tooling.
- Push. Wave 3 continues with 09–11 (`docs/superpowers/plans/09-11-teardowns.md`), whose decision point takes this slice's pick order.
