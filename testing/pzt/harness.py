"""Installing mods into a server or client cachedir."""
import os
import shutil

from . import mods
from .paths import HARNESS_MODS, TESTING, WORKSHOP_DIR

# ZomboidFileSystem.resetDefaultModsForNewRelease: if this marker is missing the game
# writes it AND wipes mods/default.txt on first launch (spike S2). Per major release.
RESET_MARKER = "reset-mods-42_00.txt"
RESET_TEXT = "If this file does not exist, default.txt will be reset to empty (no mods active)."


def install(mods_dir, mod_ids, workshop=True, sources=None, skip=()):
    """Harness mods are copied fresh from the repo; other ids are copied from the Steam
    workshop folder (the game does not look there under -nosteam, spike S3) unless
    workshop=False. `sources` maps a mod id to a folder copied verbatim (a profile's workshop
    or local mod) and wins over HARNESS_MODS and the workshop index; `skip` ids are named in
    Mods= on purpose but NOT placed -- the game's missing-mod path (S3-A) -- and are not
    reported missing. Returns the ids that were not placed."""
    os.makedirs(mods_dir, exist_ok=True)
    sources = sources or {}
    missing = []
    for mod_id in mod_ids:
        if mod_id in skip:
            continue
        src = sources.get(mod_id) or HARNESS_MODS.get(mod_id)
        if src:
            dst = os.path.join(mods_dir, mod_id)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif not workshop or not mods.install(mods_dir, mod_id):
            missing.append(mod_id)
    return missing


def enable_client_mods(mods_dir, mod_ids):
    """Client-side enabled list (ScriptParser block format read by ActiveModsFile).
    Only matters until the first join: the client then reloads with the server's Mods=."""
    os.makedirs(mods_dir, exist_ok=True)
    body = "".join(f"    mod = {m},\n" for m in mod_ids)
    with open(os.path.join(mods_dir, "default.txt"), "w") as fh:
        fh.write("VERSION = 1,\n\nmods\n{\n" + body + "}\n\nmaps\n{\n}\n")
    with open(os.path.join(mods_dir, RESET_MARKER), "w") as fh:
        fh.write(RESET_TEXT)


def _mod_lint():
    """tools/mod_lint.py loaded by path (the tools folder is not a package on sys.path)."""
    import importlib.util
    path = os.path.join(os.path.dirname(TESTING), "tools", "mod_lint.py")
    spec = importlib.util.spec_from_file_location("pzt_mod_lint", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lint_paths(sources):
    """Layout-lint every mod folder in `sources` (id -> folder, as a profile resolves it) with
    tools/mod_lint.py and return the ERROR lines, formatted as the lint prints them
    (`<mod>: ERROR: <rule>: <detail>`). WARN and INFO are not a stop. Workshop-installed folders
    are skipped: the lint gates the folders a profile points at, not the Steam corpus."""
    lint = _mod_lint()
    out = []
    for mod_id, src in (sources or {}).items():
        if os.path.normcase(os.path.abspath(src)).startswith(os.path.normcase(WORKSHOP_DIR)):
            continue
        out.extend("%s: %s: %s: %s" % (f.path, f.level, f.rule, f.detail)
                   for f in lint.lint([src]) if f.level == lint.ERROR)
    return out
