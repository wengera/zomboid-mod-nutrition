"""Test profiles (testing/profiles/<name>.toml): fixture + mods under test + sandbox
overrides. A profile never mutates the fixture -- the fixture excludes mods/, so the overlay
is rebuilt per run (S3: under -nosteam only <cachedir>/mods is searched; everything named
here is copied in).

Everything a profile asks for is resolved and validated HERE, before a single process
starts: a bad mod id, an uninstalled workshop item or a misspelt sandbox option costs one
second instead of a minute of boot and a run that looked clean because the game only WARNs
about a mod it cannot find (spike S3-A).

The schema, in full (every key optional; the defaults are the CLI's own):

    fixture     = "default"                  # golden fixture to restore
    description = "..."                      # free text, carried into report.json
    run    = { hold = 5 }                    # seconds to hold the session open (0 = Ctrl-C)
    server = { timeout = 420 }               # seconds to wait for SERVER STARTED
    client = { timeout = 300, users = ["admin"], safemode = false, launcher = "java" }
    verify = [ { side = "server", cmd = "trait.check", expect = '"loaded": true' } ]

    [[mods]]                                 # in Mods= order; see resolve_mod
    id = "PZTestKit"                         # harness mod, copied from the repo
    [[mods]]
    id = "KeenPerception"                    # + workshop_id / path / copy = false
    workshop_id = "3685392864"

    [sandbox]                                # validated against the fixture's own file
    DayLength = 1

`[[verify]]` is read here and run by the caller (cli/scenario), which owns the bus.
"""
import difflib
import glob
import os
import tomllib

from . import fixture as fx
from . import mods as modindex
from .paths import ADMIN_USER, HARNESS_MODS, TESTING, WORKSHOP_DIR
from .server import sandbox_keys

PROFILES, REPO = os.path.join(TESTING, "profiles"), os.path.dirname(TESTING)

# No harness = no command bus = no ready marker and no probes: every profile gets it,
# first in Mods= (load order is the ini's order).
HARNESS_ID = "PZTestKit"

TOP_KEYS = {"fixture", "description", "mods", "sandbox", "server", "client", "run", "verify"}
MOD_KEYS = {"id", "workshop_id", "path", "copy"}
SERVER_KEYS = {"timeout"}
CLIENT_KEYS = {"timeout", "users", "safemode", "launcher"}
RUN_KEYS = {"hold"}
VERIFY_KEYS = {"side", "cmd", "args", "expect"}

DEFAULTS = {"server_timeout": 420, "client_timeout": 300, "hold": 5,
            "launcher": "java", "safemode": False}


class ProfileError(SystemExit):
    """Anything wrong with a profile, raised before a single process starts."""


class Profile:
    """A resolved profile: exactly the arguments a run needs, already checked.

    `mods` is the Mods= list; `sources` maps the ids that get copied to the folder they are
    copied from; `skip` is the ids named in Mods= that are deliberately NOT placed; `items`
    records the workshop item each resolved mod came from (evidence for the report).
    """

    def __init__(self, name, path, fixture, mods, sources, skip, items, sandbox, users, verify,
                 hold, safemode, launcher, server_timeout, client_timeout, description=""):
        self.name, self.path, self.fixture = name, path, fixture
        self.description = description
        self.mods, self.sources, self.skip, self.items = mods, sources, skip, items
        self.sandbox, self.users, self.verify = sandbox, users, verify
        self.hold, self.safemode, self.launcher = hold, safemode, launcher
        self.server_timeout, self.client_timeout = server_timeout, client_timeout

    def report(self):
        """The block a run puts in report.json: what was asked for AND what it resolved to,
        so the artifact says which folders actually reached <cachedir>/mods."""
        return {"name": self.name, "path": self.path, "fixture": self.fixture,
                "description": self.description, "mods": list(self.mods),
                "sources": dict(self.sources), "skip": list(self.skip),
                "workshop_items": dict(self.items), "sandbox": dict(self.sandbox),
                "users": list(self.users)}


def _check_keys(what, table, known):
    unknown = sorted(set(table) - known)
    if unknown:
        raise ProfileError(f"{what}: unknown key(s) {', '.join(unknown)}; known: {', '.join(sorted(known))}")


def _int(name, what, value):
    """A profile's number, or a ProfileError. Bare `int(v)` turns `timeout = "soon"` into a
    ValueError traceback out of the loader -- the one place in this module that would report a
    bad profile as a crash instead of a sentence."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ProfileError(f"profile '{name}': {what} must be a whole number, got {value!r}")
    try:
        return int(value)
    except ValueError:
        raise ProfileError(f"profile '{name}': {what} must be a whole number, got {value!r}") from None


def _bool(name, what, value):
    """Same, for a flag: TOML has real booleans, so anything else here is a mistake worth
    naming rather than a truthiness test to fall through."""
    if not isinstance(value, bool):
        raise ProfileError(f"profile '{name}': {what} must be true or false, got {value!r}")
    return value


def _mod_id_of(src, declared):
    """The id the folder itself declares, cross-checked against the profile's own."""
    found = modindex.mod_id_of(src)
    if not found:
        raise ProfileError(f"[[mods]] no id= in any mod.info under {src}; "
                           f"check the layout with: python tools/mod_lint.py {src}")
    if declared and declared != found:
        raise ProfileError(f"[[mods]] id mismatch: the profile says '{declared}', "
                           f"but {src} declares '{found}'")
    return found


def resolve_mod(entry, index):   # index = modindex.workshop_index()
    """One [[mods]] table -> (mod_id, source_dir|None, workshop_item|None).

    Branches in order: `copy = false` (named in Mods=, placed nowhere), an explicit `path`,
    a `workshop_id`, a harness id, a bare id looked up in the workshop index. Every miss
    raises ProfileError naming the paths it looked at -- nothing is skipped silently,
    because the game's own reaction to a mod it cannot find is a WARN and a clean boot.
    """
    _check_keys(f"[[mods]] entry {entry}", entry, MOD_KEYS)
    mod_id = entry.get("id")
    if "copy" in entry and not isinstance(entry["copy"], bool):
        # `copy = 0` / `copy = "false"` would sail past the `is False` test below and be placed
        # after all -- the one branch where a silent misread produces the WRONG session rather
        # than an error.
        raise ProfileError(f"[[mods]] copy must be a bool (true/false), got {entry['copy']!r}")
    if entry.get("path") and entry.get("workshop_id"):
        # Two sources for one mod: the branch order below would pick `path` and ignore the
        # workshop id, so the profile would name a provenance the run did not use.
        raise ProfileError(f"[[mods]] entry {entry} names both path and workshop_id; "
                           "they are alternative sources -- keep one")
    if entry.get("copy") is False:
        if not mod_id:
            raise ProfileError("[[mods]] copy = false needs an explicit id: nothing is placed, "
                               "so there is no mod.info to read the Mods= name from")
        if mod_id in HARNESS_MODS:
            # Without the harness there is no command bus, no ready marker and no probes; the
            # loader prepends it for exactly that reason, so letting a profile un-place it would
            # produce a run that hangs on a ready marker nothing will ever write.
            raise ProfileError(f"[[mods]] '{mod_id}' is the harness and cannot be copy = false: "
                               "no harness means no command bus, no ready marker and no probes")
        return mod_id, None, None
    if entry.get("path"):
        src = entry["path"]
        if not os.path.isabs(src):
            src = os.path.normpath(os.path.join(REPO, src))
        if not os.path.isdir(src):
            raise ProfileError(f"[[mods]] path '{entry['path']}' is not a directory "
                               f"(resolved to {src}; relative paths are from {REPO})")
        return _mod_id_of(src, mod_id), src, None
    if entry.get("workshop_id"):
        item = str(entry["workshop_id"])
        mods_dir = os.path.join(WORKSHOP_DIR, item, "mods")
        folders = sorted(p for p in glob.glob(os.path.join(mods_dir, "*")) if os.path.isdir(p))
        if not folders:
            raise ProfileError(f"[[mods]] workshop item {item} is not installed: no mod folders "
                               f"under {mods_dir} (subscribe in Steam and let it download)")
        if len(folders) > 1:
            names = ", ".join(os.path.basename(f) for f in folders)
            if not mod_id:
                raise ProfileError(f"[[mods]] workshop item {item} ships {len(folders)} mods "
                                   f"({names}); add id = \"...\" to pick one")
            folders = [f for f in folders if modindex.mod_id_of(f) == mod_id]
            if not folders:
                raise ProfileError(f"[[mods]] workshop item {item} has no mod with id '{mod_id}' "
                                   f"under {mods_dir} (it ships: {names})")
        return _mod_id_of(folders[0], mod_id), folders[0], item
    if mod_id in HARNESS_MODS:
        return mod_id, HARNESS_MODS[mod_id], None
    if mod_id:
        hit = index.get(mod_id)
        if not hit:
            raise ProfileError(f"[[mods]] id '{mod_id}' is not a harness mod and is not installed "
                               f"({len(index)} mods indexed under {WORKSHOP_DIR}); subscribe to it, "
                               f"or name it with workshop_id = / path =")
        return mod_id, hit[0], hit[1]
    raise ProfileError(f"[[mods]] entry {entry} needs one of: id, workshop_id, path")


def profile_path(name):
    """<PROFILES>/<name>.toml, or the name as given when it already ends in .toml."""
    if name.endswith(".toml"):
        return os.path.abspath(name)
    return os.path.join(PROFILES, f"{name}.toml")


def available():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(PROFILES, "*.toml")))


def sandbox_file(fixture, rec):
    """The fixture's own SandboxVars.lua -- the list of options a profile may set."""
    return os.path.join(fx.fixture_dir(fixture), "cache", "server", "Server",
                        f"{rec.get('server', {}).get('name', 'pzt')}_SandboxVars.lua")


def check_sandbox(name, sandbox, path):
    """Every key must be a settable top-level option of the fixture's file. A typo here is
    otherwise invisible: the merge would append it, the server would drop it on the boot
    rewrite, and the run would report the option as applied.

    It checks nothing when the fixture's `SandboxVars.lua` is not on this machine -- the
    fixture caches are gitignored per-machine blobs, so on a fresh clone this validation is
    simply absent and a misspelt key survives to the run (documented in
    `docs/testing/profiles.md` § The TOML schema). The fixture is unprovisioned at that point,
    so the run would not start either way.
    """
    if not sandbox or not os.path.exists(path):
        return                       # nothing to check, or no file to check against
    known = sandbox_keys(path)
    for key in sandbox:
        if key not in known:
            near = difflib.get_close_matches(key, known, n=3)
            raise ProfileError(f"profile '{name}': [sandbox] '{key}' is not a settable option in "
                               f"{path}" + (f" -- did you mean {', '.join(near)}?" if near else
                                            f" ({len(known)} options there; nested tables such as "
                                            "Map/ZombieLore are not settable from a profile)"))


def load(name):
    """Resolve testing/profiles/<name>.toml into a Profile, or raise ProfileError."""
    path = profile_path(name)
    if not os.path.exists(path):
        have = available()
        raise ProfileError(f"profile '{name}' not found ({path}); "
                           f"have: {', '.join(have) if have else '(none)'}")
    with open(path, "rb") as fh:          # tomllib insists on binary: it decodes UTF-8 itself
        try:
            doc = tomllib.load(fh)
        except tomllib.TOMLDecodeError as e:
            raise ProfileError(f"profile '{name}' is not valid TOML ({path}): {e}") from None
    _check_keys(f"profile '{name}' ({path})", doc, TOP_KEYS)
    srv, clt, run = doc.get("server") or {}, doc.get("client") or {}, doc.get("run") or {}
    _check_keys(f"profile '{name}' [server]", srv, SERVER_KEYS)
    _check_keys(f"profile '{name}' [client]", clt, CLIENT_KEYS)
    _check_keys(f"profile '{name}' [run]", run, RUN_KEYS)

    fixture = doc.get("fixture", "default")
    rec = fx.load(fixture)                # its own SystemExit covers a missing fixture/blob

    index = modindex.workshop_index()
    mods, sources, skip, items = [], {}, [], {}
    for entry in doc.get("mods") or []:
        if not isinstance(entry, dict):
            raise ProfileError(f"profile '{name}': [[mods]] entries are tables, got {entry!r}")
        mod_id, src, item = resolve_mod(entry, index)
        if mod_id in mods:
            continue                      # the same mod named twice: Mods= takes it once
        mods.append(mod_id)
        if src:
            sources[mod_id] = src
        else:
            skip.append(mod_id)
        if item:
            items[mod_id] = item
    if HARNESS_ID not in mods:
        mods.insert(0, HARNESS_ID)
        sources[HARNESS_ID] = HARNESS_MODS[HARNESS_ID]

    sandbox = doc.get("sandbox") or {}
    check_sandbox(name, sandbox, sandbox_file(fixture, rec))

    verify = list(doc.get("verify") or [])
    for v in verify:
        if not isinstance(v, dict) or not v.get("cmd"):
            raise ProfileError(f"profile '{name}': every verify entry needs a cmd, got {v!r}")
        _check_keys(f"profile '{name}' verify {v.get('cmd')}", v, VERIFY_KEYS)
        if v.get("side", "server") not in ("server", "client"):
            raise ProfileError(f"profile '{name}': verify {v['cmd']} side must be "
                               f"server or client, got '{v['side']}'")
        if "expect" in v:
            # Matched as a substring of json.dumps(ack), so it has to BE a string, and an
            # un-stringed one is a TypeError raised mid-run with no verdict in the report.
            # A number round-trips (`str(12)` is what json.dumps writes), so it is coerced
            # here rather than at the probe -- `report["verify"][n]["expect"]` is then the
            # string that was actually compared. A TOML boolean does NOT round-trip: it would
            # become "True" and could never match JSON's `true`, so it is a pre-boot error
            # instead of a run that fails for a reason nobody would guess.
            if isinstance(v["expect"], bool):
                raise ProfileError(f"profile '{name}': verify {v['cmd']} expect must be a string "
                                   f"(it is matched inside the dumped JSON, where a boolean is "
                                   f"`true`/`false`): write expect = '\"key\": "
                                   f"{str(v['expect']).lower()}', not a TOML boolean")
            v["expect"] = str(v["expect"])

    launcher = clt.get("launcher", DEFAULTS["launcher"])
    if launcher not in ("java", "exe"):
        raise ProfileError(f"profile '{name}': [client] launcher must be java or exe, got '{launcher}'")
    if "users" in clt and not clt["users"]:
        # `pzt run` reads `a.clients or prof.users or rec["clients"]`, so an empty list would
        # silently fall through to the FIXTURE's client list -- the opposite of what writing it
        # means -- and `pzt scenario` would take `prof.users[0]` and raise IndexError. A
        # client-less run is not wired; say so instead of picking one of the two surprises.
        raise ProfileError(f"profile '{name}': [client] users = [] is not a server-only run -- "
                           "it would fall back to the fixture's own clients. Name the accounts "
                           "to attach, or leave `users` out for the default ('" + ADMIN_USER + "')")
    return Profile(
        name=os.path.splitext(os.path.basename(path))[0], path=path, fixture=fixture,
        mods=mods, sources=sources, skip=tuple(skip), items=items, sandbox=sandbox,
        users=list(clt.get("users") or [ADMIN_USER]), verify=verify,
        hold=_int(name, "[run] hold", run.get("hold", DEFAULTS["hold"])),
        safemode=_bool(name, "[client] safemode", clt.get("safemode", DEFAULTS["safemode"])),
        launcher=launcher,
        server_timeout=_int(name, "[server] timeout", srv.get("timeout", DEFAULTS["server_timeout"])),
        client_timeout=_int(name, "[client] timeout", clt.get("timeout", DEFAULTS["client_timeout"])),
        description=doc.get("description", ""))
