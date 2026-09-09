"""Installing the PZTestKit harness mods into a server or client cachedir."""
import os
import shutil

from .paths import HARNESS_MODS

# ZomboidFileSystem.resetDefaultModsForNewRelease: if this marker is missing the game
# writes it AND wipes mods/default.txt on first launch (spike S2). Per major release.
RESET_MARKER = "reset-mods-42_00.txt"
RESET_TEXT = "If this file does not exist, default.txt will be reset to empty (no mods active)."


def install(mods_dir, mod_ids):
    """Copy harness mods fresh from the repo. Non-harness ids are left to the profile
    builder (they are expected to already be in mods_dir or the workshop folder)."""
    os.makedirs(mods_dir, exist_ok=True)
    for mod_id in mod_ids:
        src = HARNESS_MODS.get(mod_id)
        if not src:
            continue
        dst = os.path.join(mods_dir, mod_id)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def enable_client_mods(mods_dir, mod_ids):
    """Client-side enabled list (ScriptParser block format read by ActiveModsFile).
    Only matters until the first join: the client then reloads with the server's Mods=."""
    os.makedirs(mods_dir, exist_ok=True)
    body = "".join(f"    mod = {m},\n" for m in mod_ids)
    with open(os.path.join(mods_dir, "default.txt"), "w") as fh:
        fh.write("VERSION = 1,\n\nmods\n{\n" + body + "}\n\nmaps\n{\n}\n")
    with open(os.path.join(mods_dir, RESET_MARKER), "w") as fh:
        fh.write(RESET_TEXT)
