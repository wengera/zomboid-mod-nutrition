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


def snapshot_from_run(name, run_dir, parent, session, run_id=None):
    """A fixture from a finished run's caches (Plan 23 spec § 4, P23-1): the world the server saved at the session's
    stop, under the parent fixture's record with its lineage. The run's `server/` and each parent client's
    `clients/<user>/` are snapshotted with the provision's skip lists. A snapshot never overwrites a fixture (spec
    section 4): `name` equal to `parent`, or a fixture folder already at `name`, is refused before anything is read or
    copied (a SystemExit naming it; `pzt snapshot` passes it through)."""
    if name == parent:
        raise SystemExit(f"refused: --name '{name}' is the parent fixture; a snapshot never overwrites its parent")
    if os.path.exists(fixture_dir(name)):
        raise SystemExit(f"refused: fixture '{name}' already exists ({fixture_dir(name)}); a snapshot never "
                         f"overwrites one: name the chain's next fixture")
    import datetime                     # function-local: a module import shifts the register's fixture.py pointers
    rec = load(parent)
    server_cache = os.path.join(run_dir, "server")
    if not os.path.isdir(server_cache):
        raise SystemExit(f"no server cache at {server_cache}: the run did not boot a server")
    client_caches = {}
    for user in rec.get("clients") or {}:
        c = os.path.join(run_dir, "clients", user)
        if not os.path.isdir(c):
            raise SystemExit(f"no client cache for {user} at {c}: the run did not attach every client of {parent}")
        client_caches[user] = c
    record = dict(rec, created=datetime.datetime.now().isoformat(timespec="seconds"), parent=rec["name"],
                  run=run_id or os.path.basename(os.path.normpath(run_dir)), session=int(session),
                  lineage=list(rec.get("lineage") or []) + [rec["name"]])
    return snapshot(name, server_cache, client_caches, record)
