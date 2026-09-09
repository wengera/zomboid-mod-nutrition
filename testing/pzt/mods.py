"""Locating mods outside a cachedir (Steam workshop content) for the copy strategy.

Under -nosteam the game searches only <cachedir>/mods (ZomboidFileSystem.getAllModFolders:
the 'workshop' and 'steam' roots require SteamUtils.isSteamModeEnabled — spike S3), so
anything a profile needs is copied in from here.
"""
import functools
import glob
import os
import shutil

from .paths import WORKSHOP_DIR


def mod_id_of(mod_dir):
    """B42 reads mod.info from inside the version folder first; fall back to common/, root."""
    candidates = sorted(glob.glob(os.path.join(mod_dir, "42*", "mod.info")), reverse=True)
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
