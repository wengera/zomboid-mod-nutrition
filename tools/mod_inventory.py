#!/usr/bin/env python3
"""Inventory + architecture-signal scan of all installed workshop mods.

Per workshop item -> per mod: identity (the `mod.info` the *game* resolves), B42 layout
quality, content footprint (lua/scripts/models/maps), lua architecture signals (events,
networking, modData, monkey-patching, error hygiene, red flags like loadstring) and script
signals (nutrition keys, item blocks, the module a mod writes into). Output:
data/mod-inventory.json + console summary.

**Identity is not this tool's question to answer.** `mod_lint` already resolves it -- newest
`42[.x[.y]]/` folder first, then `common/`, then the mod root -- so `resolve()` below imports
`version_dirs` / `info_chain` / `read_info` / `media_root` and adds nothing of its own. The
local `pick_version_dir` this replaced matched only `42[.N]` (three-part `42.20.1` folders are
real -- Skill Recovery Journal 2503622437 ships one) and read only `<mod_dir>/mod.info`, which
is why 20 of the 230 installed rows used to carry a folder name as the id. `mod_id` is now the
declared id or **`""`**: a mod the game cannot identify is a finding, and `""` is what
`pzt.mods.workshop_index()` effectively sees (229 entries for 230 folders). The folder name is
kept beside it as `mod_id_fallback`.

Two independent nutrition signals, because neither alone is the catalog: `signals.food_nutrition`
greps `.lua` for the runtime API, `signals.script_nutrition` greps `<live>/media/scripts/**/*.txt`
for the item-definition keys. On the corpus at 2026-09-10 they overlap on exactly one mod
(LongTermPreservation4220). A mod writing `module Base` **overrides vanilla items**; a mod
writing `module <Own>` only adds new ones -- LongTermPreservation4220 declares `module Skittles`
alone, so the 17 items its item script defines all add and none override. `script_item_blocks`
reads exactly those 17: `SCRIPT_ITEM` anchors the name to the end of its line, so a
craftRecipe's 30 `item 1 [Base.X]` input lines drop out. The field is a count, not a bound.

**Scope: the newest version folder only** -- the `layout` folder, which is the de-duplication
the record needs (ZVirusVaccine42BETA ships the same scripts in `42.14/`, `42.20/` and
`common/`; counting all three would treble it). `common/media` is a shipped layout the running
build ALSO loads (`docs/modding/README.md:22`, `mod_lint.media_root`) and its content is simply
not counted here; this module asserts no merge rule between the two folders. **`media_at` is
the guard, not `live_media`**: a zero in `stats`/`signals` is only trustworthy when `media_at`
does not include `common/media`, and 177 of the 230 rows do include it (2026-09-10) -- on 111
of them a bucket already reads 0 while `common/media` holds that kind of file (HayesCustoms
1268 models, MorePlushies 154). `live_media: false` marks only the total-blackout subset, the
24 rows with no live `media/` at all. Measured impact on the nutrition question specifically:
none -- no `common/media` in the corpus carries a single nutrition key (swept 2026-09-10).

Stdlib only, no import of `testing/pzt`. Ground truth:
D:/SteamLibrary/steamapps/workshop/content/108600, read and never written. It is a live tree
(Steam rewrote item 3490370700 mid-slice on 2026-09-10) -- quote a count with its date.
"""
import collections, datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mod_lint  # version_dirs / info_chain / read_info / media_root

ROOT = r"D:/SteamLibrary/steamapps/workshop/content/108600"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "mod-inventory.json")

SIGNALS = {
    "events_add":      re.compile(r"Events\.(\w+)\.Add"),
    "send_client_cmd": re.compile(r"sendClientCommand"),
    "on_client_cmd":   re.compile(r"OnClientCommand"),
    "send_server_cmd": re.compile(r"sendServerCommand"),
    "mod_data":        re.compile(r"getModData|ModData\.(?:get|add|create|transmit)"),
    "transmit_mod_data": re.compile(r"transmitModData"),
    "monkey_patch":    re.compile(r"local\s+\w*[Oo]riginal\w*\s*=\s*\w+[.:]\w+|local\s+old_?\w+\s*=\s*IS\w+[.:]"),
    "pcall":           re.compile(r"\bpcall\s*\("),
    "loadstring":      re.compile(r"\bloadstring\s*\("),
    "getfilewriter":   re.compile(r"getFileWriter|getModFileWriter"),
    "sandbox_vars":    re.compile(r"SandboxVars\."),
    "timed_action_new": re.compile(r"ISBaseTimedAction:derive"),
    "ui_panel":        re.compile(r"ISPanel:derive|ISCollapsableWindow:derive"),
    "require_line":    re.compile(r'^\s*require\s*[("]', re.M),
    "global_write_vanilla": re.compile(r"^\s*function\s+IS\w+[.:]", re.M),
    "onplayerupdate":  re.compile(r"Events\.OnPlayerUpdate\.Add"),
    "everyoneminute":  re.compile(r"Events\.EveryOneMinute\.Add|Events\.EveryTenMinutes\.Add"),
    "food_nutrition":  re.compile(r"getNutrition\(\)|setCalories|setProteins|setLipids|setCarbohydrates|HungerChange"),
}

# The script-DSL half of the nutrition question: what an item *definition* writes, which the
# `.lua` regexes above can never see. Keyed line-start so a key named inside a comment or a
# longer identifier (`ExtraCalories = `) does not count.
SCRIPT_KEYS = re.compile(r"^\s*(Calories|Carbohydrates|Lipids|Proteins|HungerChange|ThirstChange"
                         r"|DaysFresh|DaysTotallyRotten|FoodType|EvolvedRecipe)\s*=", re.M)
# An item DEFINITION header: `item <name>` alone on its line, brace optional (`item Foo` with
# the `{` on the next line, or `item Foo {`). The name is anchored to end-of-line, which is what
# makes the count exact rather than an upper bound: a craftRecipe's input/output lines read
# `item 1 [Base.Bowl]` / `item 1 Base.DriedApple` and carry a count and a bracketed/dotted
# reference after `item`, so they never match. `\w` leads because ids may start with a digit,
# and the class holds `-` because item ids may contain one: `\w[\w.]*` dropped all 492 of
# KATTAJ1 Military Pack's `item Military_ArmsProtectionLower_Patriot_Light-Black` but the first
# (3470426196, 2026-09-10). A wider `\S+` finds no name shape beyond `[\w.-]` in either corpus,
# and vanilla 42.20.4 ships no hyphenated id at all -- 5105 definitions before and after -- so
# the widening recovers 491 real items and adds no false positive anywhere.
SCRIPT_ITEM = re.compile(r"^[ \t]*item[ \t]+(\w[\w.-]*)[ \t]*\{?[ \t]*$", re.M)
SCRIPT_MODULE = re.compile(r"^\s*module\s+(\S+)", re.M)


def resolve(mod_dir):
    """(info, version_dirs, chosen_rel, media_root, live_dir) exactly as B42 resolves them: the
    newest version folder's mod.info first, then common/, then the root.

    `media_root` is the branch the live folder IS -- `"42.20.1"`, `"common"`, or `""` for a
    b41-flat mod -- and it is returned rather than thrown away so `layout` can be derived from
    it once instead of a caller re-deriving the same branch a second way. Every part of the
    answer comes from `mod_lint`; see this module's docstring for why an inventory must not keep
    a second opinion about a mod's identity."""
    vers = mod_lint.version_dirs(mod_dir)
    chosen = next((c for c in mod_lint.info_chain(vers)
                   if os.path.isfile(os.path.join(mod_dir, c))), None)
    info = mod_lint.read_info(os.path.join(mod_dir, chosen)) if chosen else {}
    root = mod_lint.media_root(mod_dir, vers)
    return info, vers, chosen, root, os.path.join(mod_dir, root) if root else mod_dir


def media_locations(mod_dir):
    """Every `media/` a resolver could pick, relative to the mod folder and sorted: `media`,
    `<version>/media`, `common/media`.

    The same depth-<2 list `mod_lint._scan` builds, without its whole-tree walk (that walk also
    reads every `.lua` for `loadstring`; this is one `listdir`). Checked identical to `_scan`'s
    on all 230 installed mods, 2026-09-10 -- nothing in the corpus hides a `media/` deeper than
    one level, which is also the only depth either tool treats as a layout root."""
    out = ["media"] if os.path.isdir(os.path.join(mod_dir, "media")) else []
    try:
        entries = sorted(os.listdir(mod_dir))
    except OSError:
        entries = []
    out += [e + "/media" for e in entries if os.path.isdir(os.path.join(mod_dir, e, "media"))]
    return sorted(out)


def require_list(info):
    r"""`require=` is a comma list of mod ids, each optionally `\`-prefixed (`\ModA,\ModB`).

    `mod_lint.read_info` keeps every value as the raw string a lint needs; this is the one
    mod.info key whose value is not a scalar, and the split+`lstrip("\\")` is what the old
    local `parse_modinfo` whitelist did with it."""
    return [x.strip().lstrip("\\") for x in str(info.get("require", "")).split(",") if x.strip()]


def folder_bytes(mod_dir):
    """Every byte the mod folder occupies on disk -- all version folders, not just the live
    one, because that is what a subscriber downloads and what a teardown has to read."""
    total = 0
    for dirpath, _dirs, files in os.walk(mod_dir):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total


def scan_mod(mod_dir, item_dir=None):
    """One mod folder -> one inventory record. `item_dir` is the workshop *item* folder the
    mod ships in, whose mtime is Steam's last write (the offline half of "is this B42?"); with
    none given `workshop_item_mtime` is `None`, because the mod folder's own mtime answers a
    different question and must not stand in for a Steam stamp."""
    info, vers, chosen, root, live = resolve(mod_dir)
    # `media_root` returns "" only when there is neither a version folder nor common/.
    layout = root or "flat(b41?)"
    media = os.path.join(live, "media")
    stats = collections.Counter()
    sig = collections.Counter()
    events = collections.Counter()
    script_keys = collections.Counter()
    script_modules = set()
    script_items = 0
    lua_bytes = 0
    # Sorted like `mod_lint._scan`'s walk: `stats` is a total either way, but `top_events` ties
    # and `script_modules` insertion order would otherwise depend on how the filesystem
    # enumerates a folder, and the committed dataset has to be byte-reproducible.
    for dirpath, dirs, files in os.walk(media):
        dirs.sort()
        p = dirpath.replace("\\", "/").lower()
        for fn in sorted(files):
            fl = fn.lower()
            full = os.path.join(dirpath, fn)
            if fl.endswith(".lua"):
                side = "shared"
                if "/lua/client" in p: side = "client"
                elif "/lua/server" in p: side = "server"
                stats[f"lua_{side}"] += 1
                try:
                    txt = open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                lua_bytes += len(txt)
                for name, rx in SIGNALS.items():
                    hits = rx.findall(txt)
                    if hits:
                        sig[name] += len(hits)
                        if name == "events_add":
                            for ev in hits:
                                events[ev] += 1
            elif fl.endswith(".txt") and "/scripts" in p:
                stats["script_files"] += 1
                try:
                    txt = open(full, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                script_keys.update(SCRIPT_KEYS.findall(txt))
                script_items += len(SCRIPT_ITEM.findall(txt))
                script_modules.update(SCRIPT_MODULE.findall(txt))
            elif fl.endswith((".fbx", ".x")):
                stats["models"] += 1
            elif fl.endswith((".pack", ".tiles")):
                stats["tile_packs"] += 1
            elif fl.endswith(".lotheader") or "/maps/" in p:
                stats["map_files"] += 1
            elif fl.endswith((".ogg", ".wav", ".bank")):
                stats["sounds"] += 1
    if script_keys:
        sig["script_nutrition"] = sum(script_keys.values())
    has_sandbox = os.path.isfile(os.path.join(live, "media", "sandbox-options.txt")) or \
                  os.path.isfile(os.path.join(mod_dir, "media", "sandbox-options.txt"))
    mtime = os.path.getmtime(item_dir) if item_dir else None
    return {
        "mod_id": info.get("id") or "",
        "mod_id_fallback": os.path.basename(os.path.normpath(mod_dir)),
        # `name=` / `author=` present but empty is the same fact as absent -- nothing is
        # declared -- and `mod_id` already collapses the two. `.get(k, "?")` did not.
        "name": info.get("name") or "?",
        "author": info.get("author") or "?",
        "require": require_list(info),
        "layout": layout,
        "version_dirs": vers,
        "mod_info_at": chosen,
        # Everything below is counted under `<live>/media` alone, so `media_at` is what makes a
        # zero legible: a `common/media` in it means "content the build loads that this scan did
        # not count", whether or not `live_media` (the whole-record blackout) is false.
        "live_media": os.path.isdir(media),
        "media_at": media_locations(mod_dir),
        "stats": dict(stats),
        "signals": dict(sig),
        "script_nutrition_keys": dict(sorted(script_keys.items())),
        "script_item_blocks": script_items,
        "script_modules": sorted(script_modules),
        "top_events": events.most_common(8),
        "lua_kb": round(lua_bytes / 1024),
        "bytes": folder_bytes(mod_dir),
        "workshop_item_mtime": None if mtime is None else
            datetime.datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
        "sandbox_options": has_sandbox,
    }

def classify(m):
    s, g = m["stats"], m["signals"]
    lua = s.get("lua_client", 0) + s.get("lua_server", 0) + s.get("lua_shared", 0)
    if s.get("map_files", 0) > 5 or s.get("tile_packs", 0) > 0 and lua == 0:
        return "map/tiles"
    if lua == 0 and s.get("script_files", 0) > 0:
        return "content(scripts-only)"
    if s.get("models", 0) > 10 and lua < 30:
        return "content(3d+lua)"
    if lua >= 30 or g.get("send_client_cmd", 0) + g.get("on_client_cmd", 0) > 5:
        return "systems(heavy-lua)"
    if lua > 0:
        return "systems(light-lua)"
    return "other"

def main():
    out = []
    for wid in sorted(os.listdir(ROOT)):
        wdir = os.path.join(ROOT, wid, "mods")
        if not os.path.isdir(wdir):
            continue
        for modname in sorted(os.listdir(wdir)):
            mdir = os.path.join(wdir, modname)
            if not os.path.isdir(mdir):
                continue
            m = scan_mod(mdir, os.path.join(ROOT, wid))
            m["workshop_id"] = wid
            m["folder"] = modname
            m["class"] = classify(m)
            out.append(m)

    # Explicit encoding and newline: text mode would write the platform's line ending, so the
    # same tree over the same corpus produced different bytes on Windows than anywhere else.
    # LF and utf-8 make "regenerate and diff" mean the same thing on every machine.
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)

    print(f"{len(out)} mods across {len({m['workshop_id'] for m in out})} workshop items -> {OUT}\n")
    by_class = collections.Counter(m["class"] for m in out)
    for k, v in by_class.most_common():
        print(f"  {v:3} {k}")
    print("\nRED FLAG loadstring users:")
    for m in out:
        if m["signals"].get("loadstring"):
            print(f"  {m['mod_id']} ({m['name']}) x{m['signals']['loadstring']}")
    print("\nb41-flat-layout mods (stale on a b42 server?):")
    for m in out:
        if m["layout"].startswith("flat"):
            print(f"  {m['mod_id']} [{m['workshop_id']}]")
    print("\nTop 20 by lua size (heavy-systems shortlist):")
    for m in sorted(out, key=lambda x: -x["lua_kb"])[:20]:
        g = m["signals"]
        print(f"  {m['lua_kb']:>5}KB {m['mod_id']:<32.32} net:{g.get('send_client_cmd',0)+g.get('on_client_cmd',0):>3} "
              f"modData:{g.get('mod_data',0):>3} patch:{g.get('monkey_patch',0):>3} pcall:{g.get('pcall',0):>3} "
              f"food:{g.get('food_nutrition',0):>3} [{m['class']}]")
    # The two nutrition sweeps side by side: `.lua` runtime API vs `media/scripts` definitions.
    # A row with a script signal and no lua one is a pure content mod; the reverse is a systems
    # mod that never ships an item. Neither column alone is the catalog.
    print("\nMods touching nutrition/food APIs (lua) or item nutrition keys (scripts):")
    print("  lua = getNutrition/set*/HungerChange in .lua; script = nutrition keys in "
          "media/scripts/*.txt;\n  items = item definitions there (exact -- a recipe's `item 1 "
          "[Base.X]` lines are not); module Base overrides vanilla items.")
    print(f"  {'lua':>4} {'script':>6} {'items':>5}  {'mod_id':<34} module(s) / name")
    touching = [m for m in out if m["signals"].get("food_nutrition") or m["signals"].get("script_nutrition")]
    for m in sorted(touching, key=lambda x: (-x["signals"].get("script_nutrition", 0),
                                             -x["signals"].get("food_nutrition", 0))):
        g = m["signals"]
        mods = ",".join(m["script_modules"]) + " " if g.get("script_nutrition") else ""
        print(f"  {g.get('food_nutrition', 0):>4} {g.get('script_nutrition', 0):>6} "
              f"{m['script_item_blocks'] if g.get('script_nutrition') else '':>5}  "
              f"{(m['mod_id'] or '(no id)'):<34} {mods}{m['name']}")
    print(f"  {len(touching)} mod(s): "
          f"{sum(1 for m in touching if m['signals'].get('food_nutrition'))} lua, "
          f"{sum(1 for m in touching if m['signals'].get('script_nutrition'))} script, "
          f"{sum(1 for m in touching if m['signals'].get('food_nutrition') and m['signals'].get('script_nutrition'))} both")
    # The game keys on mod.info, not on the folder: a profile's `[[mods]] id` must be the
    # resolved id. An empty one means no mod.info anywhere -- the game cannot load it by id.
    drift = [m for m in out if m["mod_id"] != m["mod_id_fallback"]]
    print(f"\nMods whose folder name != declared id ({len(drift)}):")
    for m in sorted(drift, key=lambda x: x["mod_id_fallback"].lower()):
        print(f"  {m['workshop_id']}/{m['mod_id_fallback']} -> "
              f"{m['mod_id'] or '(no mod.info id -- invisible to the workshop index)'}")

if __name__ == "__main__":
    # Mod folder names and mod.info values are author-supplied; the default Windows console
    # encoding (cp1252) cannot encode all of them and would abort the sweep. Same guard as mod_lint.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    main()
