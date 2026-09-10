"""Locating mods outside a cachedir (Steam workshop content) for the copy strategy.

Under -nosteam the game searches only <cachedir>/mods (ZomboidFileSystem.getAllModFolders:
the 'workshop' and 'steam' roots require SteamUtils.isSteamModeEnabled — spike S3), so
anything a profile needs is copied in from here.
"""
import functools
import glob
import os
import re
import shutil

from .paths import WORKSHOP_DIR

# `42`, `42.20`, `42.20.1` -- the shapes the engine's version folders take. Anything else the
# `42*` glob catches (`42-old/`, `42beta/`) is still a candidate, just the last one.
VERSION_RX = re.compile(r"^42(\.\d+){0,2}$")


def _version_key(info_path):
    """Sort key for one `42*/mod.info` candidate: real versions above the rest, then the
    parsed version tuple, so `sorted(..., reverse=True)` yields newest first.

    A plain string sort gets this wrong twice: `42.9` outranks `42.20`, and because the glob
    yields full paths, `42\\mod.info` outranks `42.20\\mod.info` (the separator sorts above
    `.`). It picked an older folder's file on 6 of the 230 installed mods (the six that
    `tools/mod_lint.info_chain` documents; a set disjoint from the `mod-info-place` WARNs, which
    fire only when the newest folder has no `mod.info` at all) -- and all 6 happen to declare the same
    id in both files, which is what `id-agree` is there to stop being luck.
    """
    name = os.path.basename(os.path.dirname(info_path))
    if not VERSION_RX.match(name):
        return (0, (), name)
    return (1, tuple(int(x) for x in name.split(".")[1:]), name)


def mod_id_of(mod_dir):
    """B42 reads mod.info from inside the *newest* version folder first; fall back to common/,
    root. Version folders are ordered by parsed tuple, agreeing with `mod_lint.info_chain`
    (`testing/tests/test_mods_resolution.py` asserts the two pick the same file)."""
    candidates = sorted(glob.glob(os.path.join(mod_dir, "42*", "mod.info")),
                        key=_version_key, reverse=True)
    candidates += [os.path.join(mod_dir, "common", "mod.info"), os.path.join(mod_dir, "mod.info")]
    for p in candidates:
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip().lower().startswith("id="):
                        return line.split("=", 1)[1].strip()
    return None


@functools.lru_cache(maxsize=None)
def workshop_index():
    """{mod_id: (mod_dir, workshop_item_id)} for every mod under the Steam workshop folder."""
    index = {}
    for mod_dir in glob.glob(os.path.join(WORKSHOP_DIR, "*", "mods", "*")):
        if not os.path.isdir(mod_dir):
            continue
        mid = mod_id_of(mod_dir)
        if mid and mid not in index:
            item = os.path.basename(os.path.dirname(os.path.dirname(mod_dir)))
            index[mid] = (mod_dir, item)
    return index


def find(mod_id):
    return workshop_index().get(mod_id)


def install(mods_dir, mod_id):
    """Copy a workshop mod into mods_dir (folder name kept: the game keys on mod.info,
    not the folder). Returns the destination or None when the mod is not installed."""
    hit = find(mod_id)
    if not hit:
        return None
    src, _ = hit
    dst = os.path.join(mods_dir, os.path.basename(src))
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst
