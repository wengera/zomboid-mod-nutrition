#!/usr/bin/env python3
"""Inventory + architecture-signal scan of all installed workshop mods.

Per workshop item -> per mod: identity (mod.info), B42 layout quality, content
footprint (lua/scripts/models/maps), and lua architecture signals (events,
networking, modData, monkey-patching, error hygiene, red flags like
loadstring). Output: data/mod-inventory.json + console summary.

Stdlib only. Ground truth: D:/SteamLibrary/steamapps/workshop/content/108600.
"""
import os, re, json, collections

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

def parse_modinfo(path):
    d = {}
    try:
        for ln in open(path, encoding="utf-8", errors="replace"):
            if "=" in ln:
                k, v = ln.split("=", 1)
                k = k.strip().lower()
                if k in ("name", "id", "author", "require", "versionmin", "versionmax"):
                    if k == "require":
                        d[k] = [x.strip().lstrip("\\") for x in v.strip().split(",") if x.strip()]
                    else:
                        d[k] = v.strip()
    except OSError:
        pass
    return d

def pick_version_dir(mod_dir):
    """Live tree: highest 42.x <= build, else 42, else common, else flat."""
    entries = [e for e in os.listdir(mod_dir) if os.path.isdir(os.path.join(mod_dir, e))]
    versioned = []
    for e in entries:
        m = re.fullmatch(r"42(?:\.(\d+))?", e)
        if m:
            versioned.append((int(m.group(1) or 0), e))
    if versioned:
        return os.path.join(mod_dir, max(versioned)[1]), max(versioned)[1]
    if "common" in entries:
        return os.path.join(mod_dir, "common"), "common"
    return mod_dir, "flat(b41?)"

def scan_mod(mod_dir):
    info = parse_modinfo(os.path.join(mod_dir, "mod.info"))
    live, layout = pick_version_dir(mod_dir)
    media = os.path.join(live, "media")
    stats = collections.Counter()
    sig = collections.Counter()
    events = collections.Counter()
    lua_bytes = 0
    for dirpath, dirs, files in os.walk(media):
        p = dirpath.replace("\\", "/").lower()
        for fn in files:
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
            elif fl.endswith((".fbx", ".x")):
                stats["models"] += 1
            elif fl.endswith((".pack", ".tiles")):
                stats["tile_packs"] += 1
            elif fl.endswith(".lotheader") or "/maps/" in p:
                stats["map_files"] += 1
            elif fl.endswith((".ogg", ".wav", ".bank")):
                stats["sounds"] += 1
    has_sandbox = os.path.isfile(os.path.join(live, "media", "sandbox-options.txt")) or \
                  os.path.isfile(os.path.join(mod_dir, "media", "sandbox-options.txt"))
    return {
        "mod_id": info.get("id", os.path.basename(mod_dir)),
        "name": info.get("name", "?"),
        "author": info.get("author", "?"),
        "require": info.get("require", []),
        "layout": layout,
        "stats": dict(stats),
        "signals": dict(sig),
        "top_events": events.most_common(8),
        "lua_kb": round(lua_bytes / 1024),
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
        for modname in os.listdir(wdir):
            mdir = os.path.join(wdir, modname)
            if not os.path.isdir(mdir):
                continue
            m = scan_mod(mdir)
            m["workshop_id"] = wid
            m["folder"] = modname
            m["class"] = classify(m)
            out.append(m)

    with open(OUT, "w") as fh:
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
    print("\nMods touching nutrition/food APIs:")
    for m in sorted(out, key=lambda x: -x["signals"].get("food_nutrition", 0)):
        if m["signals"].get("food_nutrition"):
            print(f"  {m['signals']['food_nutrition']:>4} {m['mod_id']} ({m['name']})")

if __name__ == "__main__":
    main()
