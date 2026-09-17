#!/usr/bin/env python3
"""Static layout lint (L0) for B42 mod folders -- what a profile can check before a server boots.

    python tools/mod_lint.py                    # every mod under the Steam workshop root
    python tools/mod_lint.py 3685392864         # one workshop item (every mod it ships)
    python tools/mod_lint.py path/to/MyMod      # one mod folder

Prints `mod: LEVEL: rule: detail` per finding, then a count line, and exits 1 if any ERROR
fired. WARN and INFO never fail a run, and most of the corpus that carries one loads fine: of
the 230 installed folders, 29 (13 %) carry a WARN and 67 (29 %) a WARN or an INFO.

| rule | level | check |
|---|---|---|
| `version-dir`    | ERROR | at least one `42[.x[.y]]/` folder |
| `mod-info`       | ERROR | a `mod.info` in some version folder, in `common/`, or at the mod root |
| `mod-info-place` | WARN  | that `mod.info` is in the *newest* version folder -- this lint's model; the engine reads the build's version folder, then `common/` (measured, `x123b-20260911-034500`) |
| `id`             | ERROR | the resolved `mod.info` declares a non-empty `id=` |
| `id-agree`       | ERROR | every `mod.info` a resolver can reach declares the same `id` (`info_chain`, plus any `42*/mod.info`) |
| `id-drift`       | WARN  | a `mod.info` OUTSIDE that chain (`LEGACY/42.12/mod.info`, a vendored copy) declares a different `id` |
| `media`          | WARN  | `media/` exists inside the chosen version folder |
| `loadstring`     | ERROR | no `loadstring(` in any `.lua` (engine removed it in 42.20.x -- `docs/modding/patterns.md:69`) |
| `folder-id`      | INFO  | folder name == `id` (informational only: the game keys on mod.info, not the folder) |

Sweep of the 230 installed mod folders (42.20.4): **84 findings -- 3 ERROR, 30 WARN, 51 INFO**
at 2026-09-10 13:47, reproduced at 14:40 and 15:09 the same day. Quote a sweep with its date --
the workshop tree is live and moved twice mid-slice (85: 3/31/51 that morning, one `media` WARN
more before Steam rewrote item `3490370700`; then 2026-09-11 04:47: 83 findings after the
workshop change; the inventory dataset is a 2026-09-10 17:47 snapshot). Every folder has a
version dir. The 3 errors sit on 2 mods: `3782784855/Skill Recovery Journal` ships only
`42.20.1/media`, so `mod-info` and `id` both fail (and `workshop_index()` cannot see it -- 229
entries for 230 folders), and `3774052732/SD_CC_TEST` fails `id-agree` (`sd_cc_test` in
`42/mod.info` and the root, `SD_CC_TEST_42` in `common/mod.info` -- all three are in the chain).
6 warn on `mod-info-place`, 24 on `media` (all of them ship `common/media` instead), 0 use
`loadstring`, 0 drift (the only out-of-chain files in the corpus are the five Frockin Splendor
mods' `LEGACY/42.1x/mod.info`, and they agree), 51 folder names differ from the id.

"Skill Recovery Journal" is **two** workshop items and only one of them is broken:
`2503622437` ships `42.20.1/mod.info` and lints clean; `3782784855` carries no `mod.info`
anywhere. A finding names the item id first for exactly this reason.

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
    """Where a mod.info may live, in the order this lint resolves it: version folders newest
    first, then `common/`, then the mod root. A SUPERSET of the engine's chain, deliberately.

    The engine opens exactly TWO candidates and never the mod root (C + M, 2026-09-11, slice
    12 -- `docs/modding/anatomy.md` sections 2 and Code map, which closed `profiles.md` open
    question 1): `ChooseGameInfo.readModInfoAux @32-@120 L184-L195` takes
    `<mod>/<getModVersionDirName(mod)>/mod.info` if it exists and `<mod>/common/mod.info`
    otherwise, and parses that ONE file -- so a folder answers to one id, the version folder's.
    Measured on the dedicated-server `Mods=` path, run `x123b-20260911-034500`: a folder
    carrying both files did NOT answer to its `common/mod.info` id. `mod-info-place` stays a
    WARN because this lint's chain is wider than the engine's, not because the order is open;
    the two pick the same file on 229 of the 230 installed folders (the exception is
    `3396446795/MoodleFramework`, and both of its files declare the same id).

    Earlier readings this replaces: `getAllModFoldersAux`'s `common/mod.info`-first test
    (`@124-151 L602`) is DISCOVERY -- a gate on whether the directory is a mod at all, not the
    id read; and `searchForModInfo` (`@0-@173 L708-L735`), whose "first mod.info whose id
    matches, in `File.list()` order" was correctly read, is referenced by nothing but its own
    recursive call anywhere in the 42.20.4 jar, i.e. it describes no live call site.

    `pzt.mods.mod_id_of` resolves in this same order. It has not always: until slice 07's final
    fix wave it string-sorted its `42*/mod.info` glob, which puts `42/mod.info` above
    `42.20/mod.info` (the path separator sorts above `.`) and `42.9` above `42.20`, so it read a
    different FILE from the one named here on 6 installed mods -- `2769706949/P4TidyUpMeister`,
    `2867431511/SimpleStatus`, `3455571945/KWRR_Security`, `3461263912/CleanHotBar`,
    `3502080466/Neat_Crafting`, `3618557184/HereGoesTheSun`. All 6 declare the same id in both
    files, so no id ever moved; `id-agree` is the net that keeps that a fact rather than luck.
    """
    return [v + "/mod.info" for v in vers] + ["common/mod.info", "mod.info"]


def media_root(mod_dir, vers):
    """The folder whose `media/` the running build reads: newest version folder present, else
    `common/`, else the mod root (the flat b41 layout).

    "Newest present" and the engine's "best `42[.x]/` that is <= the running build"
    (`docs/testing/spikes.md:64`) are the same folder on today's corpus, because nothing
    installed ships a version folder above `42.20[.1]` and the build is 42.20.4. On a mod that
    ships ahead of the running build they would differ, and this rule would name a folder the
    game does not read.

    `tools/mod_inventory.py:resolve()` calls this rather than keeping a second opinion: its old
    local `pick_version_dir` used a `42(?:\\.(\\d+))?` regex that missed three-part names, so
    `42.20.1` (Skill Recovery Journal `2503622437`) was invisible to it and it fell back to an
    older folder. `version_dirs` here is the correct reading, and now the only one.

    Scope, measured (slice 11, 2026-09-11, run `td3-20260911-001948` -- 42.20.4, n = 1, bounded
    to a version dir that ships files colliding with common/): this names ONE folder, but the
    engine loads `common/` too and the version folder's file merely WINS a same-relative-path
    collision -- so for a mod shipping both, every count taken over this folder alone is a
    partial view of the mod (`docs/mods-survey/teardowns/autocook.md`).
    """
    if vers:
        return vers[0]
    return "common" if os.path.isdir(os.path.join(mod_dir, "common")) else ""


def _scan(mod_dir):
    """One walk of the mod tree: every `mod.info` parsed, every `media/` folder noted, every
    `.lua` checked for loadstring.

    The `loadstring` scan is deliberately the WIDEST of the three -- every `.lua` anywhere under
    the folder, including files outside the version folder the running build actually loads
    (an older `42.x/`, `LEGACY/`, a vendored library, an author's scratch copy). A hit in one of
    those is dead code today and still worth an ERROR: it is a file the author will move into a
    live folder sooner than they will remember the engine dropped `loadstring` in 42.20.x.

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
    """Every L0 rule against one mod folder. `name` is what findings are reported as.

    Two rules rest on a model of the engine rather than a reading of it -- `mod-info-place`'s
    resolution order (`info_chain`) and `media_root`'s "newest present" -- which is why both
    are WARNs. Their docstrings say what is read and what is assumed."""
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
        # The newest version folder is where THIS LINT expects the file; anything else is a
        # fallback, and the id it resolves to is whatever that older/shared file happens to say.
        # The engine's own chain is narrower -- the build's version folder, then `common/`,
        # never the mod root -- and is now measured, not modelled: see `info_chain` below and
        # `docs/modding/anatomy.md` section 2.
        out.append(Finding(name, WARN, "mod-info-place",
                           "mod.info is %s, not %s (this lint's model: newest version folder "
                           "first; the engine reads the build's version folder then common/ "
                           "-- measured on the dedicated-server Mods= path, "
                           "run x123b-20260911-034500)"
                           % (chosen, chain[0])))

    mod_id = (infos.get(chosen) or {}).get("id", "") if chosen else ""
    if not mod_id:
        out.append(Finding(name, ERROR, "id", "no non-empty id= in %s" % (chosen or "any mod.info")))

    # Scope: a resolver only ever OPENS the chain above, plus anything `pzt.mods.mod_id_of`'s
    # wider `42*` glob catches that VERSION_RX does not (`42-old/`). A disagreement in there
    # decides the mod's id by which file was opened first, so it is an ERROR. A copy filed away
    # somewhere no resolver can reach (`LEGACY/42.12/mod.info`, a vendored dependency) cannot
    # change anyone's answer, so a disagreement there is drift worth reporting, not a defect.
    reach = set(chain) | {rel for rel in infos
                          if rel.count("/") == 1 and rel.lower().startswith("42")}
    resolvable = [rel for rel in sorted(infos) if rel in reach and infos[rel].get("id")]
    ids = {infos[rel]["id"] for rel in resolvable}
    if len(ids) > 1:
        out.append(Finding(name, ERROR, "id-agree", "%d resolvable mod.info file(s), %d ids: %s"
                           % (len(resolvable), len(ids),
                              ", ".join("%s (%s)" % (rel, infos[rel]["id"]) for rel in resolvable))))
    # Only meaningful against a resolved id; with none, the `id` ERROR above is the finding.
    drifted = [rel for rel in sorted(infos)
               if rel not in reach and infos[rel].get("id") and mod_id
               and infos[rel]["id"] != mod_id]
    if drifted:
        out.append(Finding(name, WARN, "id-drift", "out of the resolution chain and disagreeing "
                           "with %s (%s): %s" % (chosen, mod_id,
                                                 ", ".join("%s (%s)" % (rel, infos[rel]["id"])
                                                           for rel in drifted))))

    root = media_root(mod_dir, vers)
    want = root + "/media" if root else "media"
    if want not in medias:
        # Not fatal: `common/media` is a shipped layout (24 of the installed 230 at the sweep
        # dated in the module docstring, and the
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
    installed corpus.

    The folder branch is tried FIRST, so a directory in the working tree whose name is all
    digits shadows the workshop item with that id -- `cd` next to a folder called `3685392864`
    and the tool lints that folder instead of the subscribed item. Pass an explicit path
    (`./3685392864`) or run from elsewhere; the `--help` text says so."""
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
                    help="mod folders and/or workshop item ids (default: every installed mod). "
                         "An existing folder wins over an id, so a local directory named like a "
                         "workshop id shadows that item")
    ap.add_argument("--workshop-dir", default=WORKSHOP_DIR, metavar="DIR",
                    help="Steam workshop root that ids expand under (default: %(default)s)")
    ns = ap.parse_args(argv)
    # One expansion, one walk: `mod_dirs` globs the whole corpus, and calling it again for the
    # count would re-stat 230 folders (and could disagree with the linted set if the tree moved
    # under us mid-run, which this one demonstrably does).
    dirs = mod_dirs(ns.targets, ns.workshop_dir)
    count = len(dirs)
    findings = [f for d in dirs for f in lint_mod(d, display_name(d, ns.workshop_dir))]
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
