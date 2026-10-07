#!/usr/bin/env python3
"""Release tool: check a mod folder against the packaging rules, stage it in the in-game
uploader layout and hash it for the server-event discipline.

    python tools/release_pack.py check <mod_dir>
    python tools/release_pack.py stage <mod_dir> [--out release/] [--previous <MANIFEST.json>]
    python tools/release_pack.py manifest <mod_dir>

`check` prints `release: LEVEL: rule: detail` per finding, then `N ERROR, M WARN`, and exits 1
on any ERROR. `stage` refuses with the same output, else copies the mod to
`<out>/<item>/Contents/mods/<item>/`, writes `<out>/<item>/workshop.txt` (and copies a
`preview.png` that sits beside the mod folder) and `<out>/<item>/MANIFEST.json` (beside
`Contents/`, so the manifest is kept locally and never uploaded), and with `--previous` prints
the diff against the previous release manifest, flagging a changed script file as a SERVER
EVENT. The manifest `gate_sha256` is the sha256 over the file bytes with every CR byte dropped
(the join checksum's one tolerance, #1182).

| rule | check |
|---|---|
| `one-mod-info` | exactly one `mod.info` under the folder |
| `version-min-only` | `versionMin=` present and no `versionMax=` |
| `no-require` | no `require=` key |
| `version-dir-contents` | a version dir holds `mod.info` and `media/sandbox-options.txt` only |
| `no-shadow` | no `common/` relative path also exists under the version dir |
| `no-vanilla-path` | no `media/` path equals one in `data/vanilla-relative-paths.txt`, except under `lua/shared/Translate/` (merged, #1318) |
| `lf-no-bom` | no CR byte and no byte-order mark in a text file |
| `version-agree` | `NR_Core.lua` `version = "x"` equals `modversion=x` (skipped without that file) |
| `png-binary` | every `.png` starts with the PNG signature |
| mod_lint rules | every ERROR and WARN `mod_lint.lint` returns is carried through |

Stdlib only.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mod_lint  # noqa: E402

Finding = collections.namedtuple("Finding", "level rule detail")
ERROR, WARN = "ERROR", "WARN"
TEXT_EXT = {".lua", ".txt", ".json", ".info", ".md", ".toml"}
VERSION_RX = re.compile(r"^42(\.\d+){0,2}$")
VANILLA_LIST = HERE.parent / "data" / "vanilla-relative-paths.txt"
VERSION_DIR_ALLOWED = {"mod.info", "media/sandbox-options.txt"}
CORE_VERSION_RX = re.compile(r'\bversion\s*=\s*"([^"]*)"')
# A .json file at a vanilla Translate path is merged key by key (#1318), never a shadow;
# any other file there, a .lua file above all, is an ordinary vanilla-path shadow.
TRANSLATE_MERGED = "lua/shared/Translate/"
TAGS = "Build 42;Multiplayer;Realistic;Food"

last_findings = []  # the findings of the most recent check() or stage(), warnings included


class ReleaseError(Exception):
    """stage() refused: the check found an ERROR."""


def _files(root):
    """Every file under root as (posix relative path, Path), sorted."""
    root = Path(root)
    return sorted((p.relative_to(root).as_posix(), p) for p in root.rglob("*") if p.is_file())


def _is_text(rel):
    return Path(rel).suffix.lower() in TEXT_EXT


def _vanilla():
    try:
        return set(VANILLA_LIST.read_text(encoding="utf-8").split("\n")) - {""}
    except OSError:
        return set()


def _info_value(text, key):
    for line in text.splitlines():
        k, sep, v = line.partition("=")
        if sep and k.strip().lower() == key.lower():
            return v.strip()
    return None


def check(mod_dir):
    mod = Path(mod_dir)
    out = []
    files = _files(mod)
    vdirs = sorted(d.name for d in mod.iterdir() if d.is_dir() and VERSION_RX.match(d.name))

    infos = [(rel, p) for rel, p in files if Path(rel).name == "mod.info"]
    if len(infos) > 1:
        out.append(Finding(ERROR, "one-mod-info", "more than one mod.info: " + ", ".join(r for r, _ in infos)))

    for rel, p in infos:
        text = p.read_text(encoding="utf-8", errors="replace")
        if _info_value(text, "versionMax") is not None:
            out.append(Finding(ERROR, "version-min-only", "%s declares versionMax" % rel))
        if not _info_value(text, "versionMin"):
            out.append(Finding(ERROR, "version-min-only", "%s declares no versionMin" % rel))
        if _info_value(text, "require") is not None:
            out.append(Finding(ERROR, "no-require", "%s declares require=" % rel))

    common = {rel[len("common/"):] for rel, _ in files if rel.startswith("common/")}
    for v in vdirs:
        pre = v + "/"
        inside = {rel[len(pre):] for rel, _ in files if rel.startswith(pre)}
        for rel in sorted(inside - VERSION_DIR_ALLOWED):
            out.append(Finding(ERROR, "version-dir-contents",
                               "%s%s: a version dir holds mod.info and media/sandbox-options.txt only" % (pre, rel)))
        for rel in sorted(inside & common):
            out.append(Finding(ERROR, "no-shadow", "%s exists under common/ and %s" % (rel, v)))

    vanilla = _vanilla()
    for rel, _ in files:
        parts = rel.split("/", 1)
        if len(parts) == 2 and (parts[0] == "common" or parts[0] in vdirs) and parts[1].startswith("media/"):
            media_rel = parts[1][len("media/"):]
            if media_rel in vanilla and not (media_rel.startswith(TRANSLATE_MERGED) and media_rel.endswith(".json")):
                out.append(Finding(ERROR, "no-vanilla-path", "%s sits at the vanilla path media/%s" % (rel, media_rel)))

    for rel, p in files:
        data = p.read_bytes()
        if _is_text(rel):
            if data.startswith(b"\xef\xbb\xbf"):
                out.append(Finding(ERROR, "lf-no-bom", "%s starts with a byte-order mark" % rel))
            if b"\r" in data:
                out.append(Finding(ERROR, "lf-no-bom", "%s contains a CR byte" % rel))
        if rel.lower().endswith(".png") and not data.startswith(b"\x89PNG"):
            out.append(Finding(ERROR, "png-binary", "%s does not start with the PNG signature" % rel))

    core = mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua"
    if core.is_file() and infos:
        m = CORE_VERSION_RX.search(core.read_text(encoding="utf-8", errors="replace"))
        lua_v = m.group(1) if m else None
        for rel, p in infos:
            info_v = _info_value(p.read_text(encoding="utf-8", errors="replace"), "modversion")
            if lua_v != info_v:
                out.append(Finding(ERROR, "version-agree",
                                   "NR_Core.lua version=%r but %s modversion=%r" % (lua_v, rel, info_v)))

    for f in mod_lint.lint([str(mod)]):
        if f.level in (mod_lint.ERROR, mod_lint.WARN):
            out.append(Finding(f.level, f.rule, f.detail))

    last_findings[:] = out
    return out


def _hash_file(rel, path):
    data = Path(path).read_bytes()
    entry = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    if rel.endswith(".txt") and "media/scripts/" in rel:
        entry["gate_sha256"] = hashlib.sha256(data.replace(b"\r", b"")).hexdigest()
    return entry


def manifest(mod_dir):
    return {rel: _hash_file(rel, p) for rel, p in _files(mod_dir)}


def diff(old_manifest, new_manifest):
    old, new = old_manifest, new_manifest
    changed = sorted(k for k in new if k in old and old[k]["sha256"] != new[k]["sha256"])
    script = [k for k in changed
              if ("gate_sha256" in new[k] or "gate_sha256" in old[k])
              and old[k].get("gate_sha256") != new[k].get("gate_sha256")]
    added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    # A script file that appears or disappears moves the join checksum as surely as an edit.
    script += [k for k in added if "gate_sha256" in new[k]] + [k for k in removed if "gate_sha256" in old[k]]
    return {"added": added, "removed": removed, "changed": changed, "script_changed": sorted(script)}


def _workshop_txt(mod, item_name):
    info = next((p for rel, p in _files(mod) if Path(rel).name == "mod.info"), None)
    text = info.read_text(encoding="utf-8") if info else ""
    title = _info_value(text, "name") or item_name
    desc = " ".join((_info_value(text, "description") or "").split())
    return "\n".join(["version=1", "id=", "title=" + title, "description=" + desc,
                      "tags=" + TAGS, "visibility=public", ""])


def stage(mod_dir, out_dir, item_name="NutritionRevamp"):
    mod = Path(mod_dir)
    findings = check(mod)
    if any(f.level == ERROR for f in findings):
        raise ReleaseError("check found an ERROR; nothing staged")
    item = Path(out_dir) / item_name
    if item.exists():
        shutil.rmtree(item)
    dest = item / "Contents" / "mods" / item_name
    shutil.copytree(mod, dest)
    man = manifest(mod)
    (item / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8", newline="\n")
    (item / "workshop.txt").write_text(_workshop_txt(mod, item_name), encoding="utf-8", newline="\n")
    preview = mod.resolve().parent / "preview.png"
    if preview.is_file():
        shutil.copyfile(preview, item / "preview.png")
    else:
        findings = findings + [Finding(WARN, "preview", "no preview.png beside the mod folder; "
                                       "the uploader needs a 256x256 8-bit png")]
    last_findings[:] = findings
    return man


def _print(findings):
    for f in findings:
        print("release: %s: %s: %s" % (f.level, f.rule, f.detail))
    print("%d ERROR, %d WARN" % (sum(f.level == ERROR for f in findings),
                                 sum(f.level == WARN for f in findings)))


def main(argv):
    ap = argparse.ArgumentParser(description="Release tool: check, stage, manifest.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").add_argument("mod_dir")
    sp = sub.add_parser("stage")
    sp.add_argument("mod_dir")
    sp.add_argument("--out", default="release")
    sp.add_argument("--previous", metavar="MANIFEST.json")
    sub.add_parser("manifest").add_argument("mod_dir")
    ns = ap.parse_args(argv)

    if ns.cmd == "manifest":
        print(json.dumps(manifest(ns.mod_dir), indent=2, sort_keys=True))
        return 0
    if ns.cmd == "check":
        findings = check(ns.mod_dir)
        _print(findings)
        return 1 if any(f.level == ERROR for f in findings) else 0
    try:
        man = stage(ns.mod_dir, ns.out)
    except ReleaseError:
        _print(last_findings)
        return 1
    _print(last_findings)
    print("staged %d file(s) under %s" % (len(man), Path(ns.out) / "NutritionRevamp"))
    if ns.previous:
        d = diff(json.loads(Path(ns.previous).read_text(encoding="utf-8")), man)
        for k in ("added", "removed", "changed", "script_changed"):
            print("%s: %s" % (k, ", ".join(d[k]) if d[k] else "none"))
        if d["script_changed"]:
            print("SERVER EVENT: %d script file(s) changed" % len(d["script_changed"]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    sys.exit(main(sys.argv[1:]))
