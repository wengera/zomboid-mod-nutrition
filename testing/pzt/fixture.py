"""Golden fixtures: a provisioned server world + client cachedirs, restored per run.

Layout: testing/fixtures/<name>/fixture.json (tracked record of how it was built)
        testing/fixtures/<name>/cache/server/            (gitignored blobs)
        testing/fixtures/<name>/cache/clients/<user>/
"""
import json
import os
import shutil

from .paths import FIXTURES

# Top-level entries not worth freezing. mods/ is re-installed at boot/attach so the
# fixture never pins a stale harness (or the mod under test).
SERVER_SKIP = {"backups", "Crafting", "ItemTracker.log", "Logs", "messaging", "mods",
               "Recording", "server-console.txt"}
CLIENT_SKIP = {"console.txt", "Crafting", "Logs", "logs.zip", "messaging", "mods",
               "Recording", "Workshop"}


def fixture_dir(name):
    return os.path.join(FIXTURES, name)


def record_path(name):
    return os.path.join(fixture_dir(name), "fixture.json")


def _copy_tree(src, dst, skip):
    src = os.path.abspath(src)

    def ignore(d, names):
        return [n for n in names if os.path.abspath(d) == src and n in skip]
    shutil.copytree(src, dst, ignore=ignore)


def _size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


def snapshot(name, server_cache, client_caches, record):
    root = fixture_dir(name)
    cache = os.path.join(root, "cache")
    if os.path.isdir(cache):
        shutil.rmtree(cache)
    _copy_tree(server_cache, os.path.join(cache, "server"), SERVER_SKIP)
    for user, c in client_caches.items():
        _copy_tree(c, os.path.join(cache, "clients", user), CLIENT_SKIP)
    record = dict(record, name=name, size_mb=round(_size(cache) / 1e6, 1))
    with open(record_path(name), "w") as fh:
        json.dump(record, fh, indent=1)
    return record


def load(name):
    p = record_path(name)
    if not os.path.exists(p):
        raise SystemExit(f"fixture '{name}' not found ({p}); build it with: pzt provision --name {name}")
    with open(p) as fh:
        rec = json.load(fh)
    if not os.path.isdir(os.path.join(fixture_dir(name), "cache", "server")):
        raise SystemExit(f"fixture '{name}' has a record but no cache/ blob on this machine; "
                         f"re-run: pzt provision --name {name}")
    return rec


def restore_server(name, run_dir):
    dst = os.path.join(run_dir, "server")
    shutil.copytree(os.path.join(fixture_dir(name), "cache", "server"), dst)
    return dst


def restore_client(name, user, run_dir):
    """Returns (cache_dir, restored). A user without a snapshot gets an empty dir (the
    client will then go through character creation)."""
    src = os.path.join(fixture_dir(name), "cache", "clients", user)
    dst = os.path.join(run_dir, "clients", user)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
        return dst, True
    os.makedirs(dst, exist_ok=True)
    return dst, False
