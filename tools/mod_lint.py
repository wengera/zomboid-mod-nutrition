#!/usr/bin/env python3
"""Static layout lint (L0) for B42 mod folders -- what a profile can check before a server boots.

    python tools/mod_lint.py                    # every mod under the Steam workshop root
    python tools/mod_lint.py 3685392864         # one workshop item (every mod it ships)
    python tools/mod_lint.py path/to/MyMod      # one mod folder

Prints `mod: LEVEL: rule: detail` per finding, then a count line, and exits 1 if any ERROR
fired. WARN and INFO never fail a run: a third of the installed corpus warns and still loads.

| rule | level | check |
|---|---|---|
| `version-dir`    | ERROR | at least one `42[.x[.y]]/` folder |
| `mod-info`       | ERROR | a `mod.info` in some version folder, in `common/`, or at the mod root |
| `mod-info-place` | WARN  | that `mod.info` is in the *newest* version folder, the one B42 runs |
| `id`             | ERROR | the resolved `mod.info` declares a non-empty `id=` |
| `id-agree`       | ERROR | every `mod.info` in the folder declares the same `id` |
| `media`          | WARN  | `media/` exists inside the chosen version folder |
| `loadstring`     | ERROR | no `loadstring(` in any `.lua` (engine removed it in 42.20.x -- `docs/modding/patterns.md:69`) |
| `folder-id`      | INFO  | folder name == `id` (informational only: the game keys on mod.info, not the folder) |

Sweep of the 230 installed mod folders (42.20.4, 2026-09-10): 85 findings -- 3 ERROR, 31 WARN,
51 INFO. Every folder has a version dir. The 3 errors sit on 2 mods: `3782784855/Skill Recovery
Journal` ships only `42.20.1/media`, so `mod-info` and `id` both fail (and `workshop_index()`
cannot see it -- 229 entries for 230 folders), and `3774052732/SD_CC_TEST` fails `id-agree`
(`sd_cc_test` in `42/mod.info` and the root, `SD_CC_TEST_42` in `common/mod.info`). 6 warn on
`mod-info-place`, 25 on `media` (all of them ship `common/media` instead), 0 use `loadstring`,
51 folder names differ from the id.

Stdlib only. The workshop tree is read, never written.
"""
import argparse, collections, glob, os, re, sys

Finding = collections.namedtuple("Finding", "path level rule detail")

WORKSHOP_DIR = r"D:\SteamLibrary\steamapps\workshop\content\108600"
VERSION_RX = re.compile(r"^42(\.\d+){0,2}$")
LOADSTRING_RX = re.compile(r"\bloadstring\s*\(")
ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
LEVELS = (ERROR, WARN, INFO)


def _slash(path):
    return path.replace("\\", "/")


def version_dirs(mod_dir):
    """Newest first. Tuple-parsed: a string sort puts '42.9' above '42.20', and three-part
    names ('42.20.1', shipped by Skill Recovery Journal 2503622437) are real."""
    hits = [(tuple(int(x) for x in e.split(".")[1:]), e) for e in sorted(os.listdir(mod_dir))
            if VERSION_RX.match(e) and os.path.isdir(os.path.join(mod_dir, e))]
    return [e for _, e in sorted(hits, reverse=True)]


def read_info(path):
    """`key=value` lines -> dict, keys lowercased and stripped, last wins (the shape of
    `mod_inventory.parse_modinfo`, minus its key whitelist -- a lint reads what is there).

    utf-8-sig, not utf-8: a BOM would hide the first key, and `id=` is a first line in the
    wild. (No installed mod.info carries one today; the fallback costs nothing.)"""
    info = {}
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.strip().lower()] = v.strip()
    except OSError:
        pass
    return info


def info_chain(vers):
    """Where a mod.info may live, in the order the game and `pzt.mods.mod_id_of` resolve it:
    version folders newest first, then `common/`, then the mod root."""
    return [v + "/mod.info" for v in vers] + ["common/mod.info", "mod.info"]


def media_root(mod_dir, vers):
    """The folder whose `media/` the running build reads: newest version folder, else
    `common/`, else the mod root (the flat b41 layout). Mirrors `mod_inventory.pick_version_dir`."""
    if vers:
        return vers[0]
    return "common" if os.path.isdir(os.path.join(mod_dir, "common")) else ""


def _scan(mod_dir):
    """One walk of the mod tree: every `mod.info` parsed, every `media/` folder noted, every
    `.lua` checked for loadstring.

    Returns ({rel mod.info path: info dict}, [rel media path], [(rel lua path, line, hits)])."""
    infos, medias, hits = {}, [], []
    for dirpath, dirs, files in os.walk(mod_dir):
        dirs.sort()
        rel_dir = _slash(os.path.relpath(dirpath, mod_dir))
        # `<mod>/media`, `<mod>/42.20/media`, `<mod>/common/media` -- deeper ones are content.
        if os.path.basename(dirpath).lower() == "media" and rel_dir.count("/") < 2:
            medias.append(rel_dir)
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            rel = _slash(os.path.relpath(full, mod_dir))
            low = fn.lower()
            if low == "mod.info":
                infos[rel] = read_info(full)
            elif low.endswith(".lua"):
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        found = [n for n, line in enumerate(fh, 1) if LOADSTRING_RX.search(line)]
                except OSError:
                    continue
                if found:
                    hits.append((rel, found[0], len(found)))
    return infos, sorted(medias), hits


def lint_mod(mod_dir, name=None):
    """Every L0 rule against one mod folder. `name` is what findings are reported as."""
    name = name or display_name(mod_dir)
    out = []
    vers = version_dirs(mod_dir)
    if not vers:
        out.append(Finding(name, ERROR, "version-dir",
                           "no 42[.x[.y]] folder (b41-flat or unversioned; B42 loads <mod>/42*/media)"))
    infos, medias, hits = _scan(mod_dir)

    chain = info_chain(vers)
    chosen = next((c for c in chain if c in infos), None)
    if chosen is None:
        out.append(Finding(name, ERROR, "mod-info",
                           "no mod.info in any version folder, common/ or the mod root"))
    elif vers and chain[0] not in infos:
        # The newest version folder is the one the running build reads; anything else is a
        # fallback, and the id it resolves to is whatever that older/shared file happens to say.
        out.append(Finding(name, WARN, "mod-info-place",
                           "mod.info is %s, not %s (B42 reads the version folder first)"
                           % (chosen, chain[0])))

    mod_id = (infos.get(chosen) or {}).get("id", "") if chosen else ""
    if not mod_id:
        out.append(Finding(name, ERROR, "id", "no non-empty id= in %s" % (chosen or "any mod.info")))

    declared = sorted({info.get("id", "") for info in infos.values() if info.get("id")})
    if len(declared) > 1:
        out.append(Finding(name, ERROR, "id-agree", "%d mod.info files, %d ids: %s"
                           % (len(infos), len(declared),
                              ", ".join("%s (%s)" % (rel, infos[rel]["id"])
                                        for rel in sorted(infos) if infos[rel].get("id")))))

    root = media_root(mod_dir, vers)
    want = root + "/media" if root else "media"
    if want not in medias:
        # Not fatal: `common/media` is a shipped layout (25 of the installed 230 use it, and the
        # game reads it), but a copy or a Mods= entry that only carries the version folder loses
        # the content, so the finding names where the media really is.
        out.append(Finding(name, WARN, "media", "no %s (media/ at: %s)"
                           % (want, ", ".join(medias) if medias else "nowhere in this mod")))

    for rel, line, count in hits:
        out.append(Finding(name, ERROR, "loadstring", "%s:%d%s (removed from the engine in 42.20.x)"
                           % (rel, line, "" if count == 1 else " and %d more" % (count - 1))))

    folder = os.path.basename(os.path.normpath(mod_dir))
    if mod_id and folder != mod_id:
        out.append(Finding(name, INFO, "folder-id", "folder %r != id %r" % (folder, mod_id)))
    return out


def display_name(mod_dir, workshop_dir=None):
    """`<workshop-id>/<folder>` for anything under the workshop root -- the constant `mods/`
    segment is dropped, and `<workshop-id>` is what you re-run this tool with. Any other mod
    folder reports as given."""
    root = os.path.abspath(workshop_dir or WORKSHOP_DIR)
    full = os.path.abspath(mod_dir)
    if os.path.normcase(full).startswith(os.path.normcase(root) + os.sep):
        parts = _slash(os.path.relpath(full, root)).split("/")
        if len(parts) == 3 and parts[1] == "mods":
            return parts[0] + "/" + parts[2]
        return _slash(os.path.relpath(full, root))
    return _slash(os.path.normpath(mod_dir))


def mod_dirs(targets, workshop_dir=None):
    """Expand CLI targets to mod folders. A target is an existing folder (one mod), or a
    workshop item id (all-digits: every mod folder the item ships). No targets = the whole
    installed corpus."""
    workshop_dir = workshop_dir or WORKSHOP_DIR
    if not targets:
        return sorted(d for d in glob.glob(os.path.join(workshop_dir, "*", "mods", "*"))
                      if os.path.isdir(d))
    out = []
    for target in targets:
        if os.path.isdir(target):
            out.append(target)
        elif str(target).isdigit():
            hits = sorted(d for d in glob.glob(os.path.join(workshop_dir, str(target), "mods", "*"))
                          if os.path.isdir(d))
            if not hits:
                raise SystemExit("mod_lint: workshop item %s has no mods/ folder under %s"
                                 % (target, workshop_dir))
            out += hits
        else:
            raise SystemExit("mod_lint: no such mod folder: %s" % target)
    return out


def lint(targets, workshop_dir=None):
    """Lint every mod folder the targets expand to, in order."""
    return [f for d in mod_dirs(targets, workshop_dir)
            for f in lint_mod(d, display_name(d, workshop_dir))]


def main(argv):
    ap = argparse.ArgumentParser(description="Static layout lint (L0) for B42 mod folders.")
    ap.add_argument("targets", nargs="*", metavar="target",
                    help="mod folders and/or workshop item ids (default: every installed mod)")
    ap.add_argument("--workshop-dir", default=WORKSHOP_DIR, metavar="DIR",
                    help="Steam workshop root that ids expand under (default: %(default)s)")
    ns = ap.parse_args(argv)
    count = len(mod_dirs(ns.targets, ns.workshop_dir))
    findings = lint(ns.targets, ns.workshop_dir)
    for f in findings:
        print("%s: %s: %s: %s" % (f.path, f.level, f.rule, f.detail))
    by_level = collections.Counter(f.level for f in findings)
    print("%d finding(s): %s across %d mod(s)"
          % (len(findings), ", ".join("%d %s" % (by_level[lv], lv) for lv in LEVELS), count))
    return 1 if by_level[ERROR] else 0


if __name__ == "__main__":
    # Mod folder names and mod.info values are author-supplied; the default Windows console
    # encoding (cp1252) cannot encode all of them and would abort the sweep. Same guard as doc_lint.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    sys.exit(main(sys.argv[1:]))
