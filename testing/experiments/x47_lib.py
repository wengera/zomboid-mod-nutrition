"""x47_lib -- the session engine of Plan 16 Task 12's two pre-upload boots, x471 and x472: the exact bytes Angus uploads,
booted on fixture `two` (admin -debug, role admin; bob release, role user), build 42.21.0.

Built on testing/experiments/xlib.py (the session state, the wall budget, the grade recorder, the abort, teardown and copy
skeleton) and, like x46_lib.py (the latest lib), on the frozen x45g_lib.py, imported unchanged for its staged gate, its
log patterns and its Z grade. x46_lib itself is session-specific (fixture default, rings, a prerun) and is not imported.

THE STAGED COPY. Both profiles boot release/NutritionRevamp/Contents/mods/NutritionRevamp, the upload copy itself, staged
from HEAD before the boots (`python tools/release_pack.py stage mod/NutritionRevamp --out release`); the staged gate checks
it against release_pack.manifest() of mod/ at STAGED_FROM (a git archive) and refuses on a mismatch, and preboot refuses
when STAGED_FROM is not mod/'s last commit. mod/ is never booted (CLAUDE.md s5).

THE SESSIONS (each one boot, under 10 wall minutes, in a foreground call):
  x471 options  (x47-options)  the profile's [sandbox.NR] VisibilityMode = 3 (the declared default 2) merged into the
                server's own options file (Server/pzt_SandboxVars.lua) at seed. admin attaches (session.attach_clients),
                then bob is started and watched by the driver (a never-ready bob is a reading, not a raise). Once bob is
                ready and READ_SETTLE_S has passed: the reads (`after_ready`) on the server, admin and bob, the verify rows,
                HOLD_S held, the reads again (`end`), the players read.
  x472 checksum (x47-checksum) bob alone gets release/x472-bob (gitignored): a copy of the staged folder made by this lib
                before the boot whose common/media/lua/shared/NR_Core.lua differs by ONE byte inside its first comment
                line (EDIT_OLD -> EDIT_NEW, same length, LF kept), through the profile's [client_overrides.bob]. admin
                attaches; bob is started and watched to OBS_S (or HOLD_AFTER_READY_S past a ready); the players read and
                admin's TK.version at the end. mod/ and release/NutritionRevamp are never edited.
After teardown both sessions read the server's user and connections logs and bob's connections log (the game's own
millisecond stamps; copied byte-identical to the artifact folder with a `server-` or `bob-` prefix), the server stdout and
console, and every client console, with the harness echo dropped.

THE GRADES (pure; each has a failing case in testing/tests/test_x47_lib.py; a grade on no valid sample is unmeasured):
  x471  INI        (precondition) the seeded options file's NR block holds VisibilityMode = 3.
        OPT_SERVER, OPT_ADMIN, OPT_BOB  SandboxVars.NR.VisibilityMode reads OPTION_SET on that side in every read set.
        MOD_READ   the mod's own reads: the server's NutritionRevamp.server.options.visibilityMode and each client's
                   NutritionRevamp.client.view.optionLevel read OPTION_SET in every read set.
        JOIN       the clean release join: admin and bob ready; NutritionRevamp.version the staged version on the server,
                   admin and bob at the end; the players read at the end both users; the user log a `fully connected`
                   line for bob and no Anti-cheat line; no checksum-mismatch line in the server's logs.
        Z          x45g_lib's: no mod error line in the server log, admin not parked.
  x472  COPY       (precondition) bob's tree differs from the staged tree in exactly one file, CHANGED_REL, by exactly one
                   byte, inside a `--` comment line, the CR-dropped MD5 differing (the join checksum sees it).
        DEPLOYED   (precondition) the server's and admin's deployed CHANGED_REL carry the staged sha256, bob's the copy's.
        KICK       bob never ready, and the kick on the record: the user log's `Anti-cheat="ChecksumUpdate"` line for bob,
                   the stdout's `user bob will be kicked`, or bob's connections log's checksum `force-disconnect` (each
                   recorded). Falsified: bob ready and answering the version after HOLD_AFTER_READY_S with no such line.
        ADMIN_STAYS admin answers TK.version at the end and the players read at the end is admin without bob.
        Z          as x471.

FROZEN WITH ITS FIRST RUN: once a driver that imports this file has run, this file is never edited (CLAUDE.md s5).
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                                   # testing/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import xlib as X                                                              # noqa: E402
import x45g_lib as G                                                          # noqa: E402

REPO = X.REPO
SRV = X.SRV
NR = G.NR
ADMIN, BOB = "admin", "bob"
LIB_FILE = "x47_lib.py"
MOD_DIR = G.MOD_DIR
STAGE_OUT = "release"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_FROM = "1c02d0e9"                 # mod/'s last commit (Plan 16 close fix: README, CHANGELOG, COMPATIBILITY)
BOB_ROOT = "release/x472-bob/NutritionRevamp"
BOB_MOD = BOB_ROOT + "/Contents/mods/NutritionRevamp"
CHANGED_REL = "common/media/lua/shared/NR_Core.lua"
EDIT_OLD = b"its version"                # in NR_Core.lua's first comment line (x223a's edit, on the final tree)
EDIT_NEW = b"its versiom"
OPTION = "VisibilityMode"
OPTION_SET = 3                           # Numbers
OPTION_DEFAULT = 2                       # Bands, the declared default (media/sandbox-options.txt)
SANDBOX_REL = ("server", "Server", "pzt_SandboxVars.lua")
MIN_FREE_GB = 12.0
MOD_DAY_LENGTH = 1
READ_SETTLE_S = 5.0                      # x471: after bob's ready, before the first read set
HOLD_S = 20.0                            # x471: held between the two read sets
OBS_S = 180.0                            # x472: bob watched at most this long from its start when never ready (x223)
HOLD_AFTER_READY_S = 90.0                # x472: a ready bob held past the 60 s server grace (#1231) plus margin (x223)
POLL_S = 0.25
CLICK_GAP_S = 2.0
LINE_CAP = 300
TAIL_LINES = 120
SESSIONS = {
    "x471": {"profile": "x47-options", "driver": "x471_options.py", "artifact": "options.json"},
    "x472": {"profile": "x47-checksum", "driver": "x472_checksum.py", "artifact": "checksum.json"},
}
SERVER_OPT_G = "SandboxVars.NR." + OPTION
SERVER_MOD_G = "NutritionRevamp.server.options.visibilityMode"
CLIENT_MOD_G = "NutritionRevamp.client.view.optionLevel"
CLIENT_READINGS_G = ("NutritionRevamp.client.view.level", "NutritionRevamp.client.view.hasTrait")
SERVER_READINGS_G = ("NutritionRevamp.server.options.readAt",)
VERSION_G = "NutritionRevamp.version"
ECHO_RX = G.ECHO_RX
NEVER_RX = G.NEVER_RX
LOG_RX = G.LOG_RX
MOD_ERR_RX = G.MOD_ERR_RX
# x223b's grade defect: `LuaChecksum` matched the server's `luaChecksum: <hash>` boot line and the clients'
# `DoLuaChecksum start/end`, none a mismatch; the pattern names the mismatch lines only.
MISMATCH_RX = re.compile(r"will be kicked|checksums do not match|ChecksumUpdate|File doesn't match|File doesn't exist|"
                         r"File status unknown|Timed out connection because checksum", re.I)
ANTICHEAT_BOB_RX = re.compile(r'Anti-cheat="ChecksumUpdate" is triggered for connection="bob"')
ANTICHEAT_RX = re.compile(r"Anti-cheat=")
FULLY_RX = re.compile(r'"(\w+)" fully connected')
KICKED_BOB_RX = re.compile(r"user bob will be kicked .*checksums do not match")
FORCE_CHECKSUM_RX = re.compile(r'event="force-disconnect" message="checksum-')
def _const(v):
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return v.pattern if hasattr(v, "pattern") else v


CONSTANTS = {k: _const(v) for k, v in dict(globals()).items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
             and k not in ("HERE", "REPO")
             and (isinstance(v, (int, float, str, tuple, dict, bytes)) or hasattr(v, "pattern"))}


def g(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def same_number(v, want):
    n = X.num(v)
    return n is not None and abs(n - want) < 1e-9


# ================================================================ bob's copy (pure over two folders)
def file_facts(p):
    try:
        with open(p, "rb") as fh:
            b = fh.read()
    except OSError as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {"size": len(b), "cr": b.count(b"\r"), "sha256": hashlib.sha256(b).hexdigest(),
            "md5_cr_dropped": hashlib.md5(b.replace(b"\r", b"")).hexdigest()}


def tree_files(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if os.path.isfile(p):
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def make_bob_copy(stage_root, bob_root, rel=CHANGED_REL, old=EDIT_OLD, new=EDIT_NEW):
    """bob's folder: the staged folder copied whole (bob_root removed first), then `old` replaced by `new` ONCE in the
    mod's `rel`; refuses (ValueError) unless `old` occurs exactly once and the two differ by one byte at equal length."""
    if len(old) != len(new) or sum(1 for a, b in zip(old, new) if a != b) != 1:
        raise ValueError("the edit must change exactly one byte at equal length")
    if os.path.isdir(bob_root):
        shutil.rmtree(bob_root)
    shutil.copytree(stage_root, bob_root)
    p = os.path.join(bob_root, "Contents", "mods", "NutritionRevamp", *rel.split("/"))
    with open(p, "rb") as fh:
        b = fh.read()
    if b.count(old) != 1:
        raise ValueError(f"{rel}: the edit's old text occurs {b.count(old)} times, not once")
    with open(p, "wb") as fh:
        fh.write(b.replace(old, new, 1))
    return file_facts(p)


def bob_copy_check(staged_mod, bob_mod, rel=CHANGED_REL):
    """COPY: exactly one file differs, `rel`, by exactly one byte at equal size, inside a `--` comment line, and the
    CR-dropped MD5 differs (the checksummer drops byte 13 only, #1182)."""
    fa, fb = tree_files(staged_mod), tree_files(bob_mod)
    differ = []
    for r in sorted(set(fa) | set(fb)):
        if r not in fa or r not in fb:
            differ.append({"path": r, "only_in": "staged" if r in fa else "bob"})
            continue
        with open(fa[r], "rb") as x, open(fb[r], "rb") as y:
            if x.read() != y.read():
                differ.append({"path": r})
    c = {"files_staged": len(fa), "files_bob": len(fb), "differ": differ,
         "one_file": [d.get("path") for d in differ] == [rel] and "only_in" not in differ[0] if differ else False}
    if c["one_file"]:
        with open(fa[rel], "rb") as x, open(fb[rel], "rb") as y:
            a, b = x.read(), y.read()
        c["same_size"] = len(a) == len(b)
        offs = [i for i, (p, q) in enumerate(zip(a, b)) if p != q]
        c["bytes_differ"] = len(offs) + abs(len(a) - len(b))
        if offs:
            o = offs[0]
            start = a.rfind(b"\n", 0, o) + 1
            end = a.find(b"\n", o)
            line = a[start:end if end >= 0 else len(a)]
            c["offset"] = o
            c["line_no"] = a.count(b"\n", 0, o) + 1
            c["line_staged"] = line.decode("utf-8", "replace")[:200]
            c["in_comment"] = line.lstrip().startswith(b"--")
        c["staged_file"] = file_facts(fa[rel])
        c["bob_file"] = file_facts(fb[rel])
        c["md5_cr_dropped_differ"] = c["staged_file"].get("md5_cr_dropped") != c["bob_file"].get("md5_cr_dropped")
    c["ok"] = (c["one_file"] is True and c.get("same_size") is True and c.get("bytes_differ") == 1
               and c.get("in_comment") is True and c.get("md5_cr_dropped_differ") is True)
    return c


def grade_copy(c):
    if not isinstance(c, dict) or "ok" not in c:
        return "unmeasured", {"why": "no copy check"}
    obs = {k: c.get(k) for k in ("one_file", "same_size", "bytes_differ", "in_comment", "md5_cr_dropped_differ",
                                 "line_no", "differ")}
    return ("as_predicted" if c["ok"] else "falsified"), obs


def deployed_copies(run_dir, rel=CHANGED_REL):
    """Every deployed copy of `rel` under the run (the server's and each client's mods/NutritionRevamp)."""
    rows = {}
    pat = os.path.join(run_dir, "**", "mods", NR, *rel.split("/"))
    for p in sorted(glob.glob(pat, recursive=True)):
        rows[os.path.relpath(p, run_dir).replace(os.sep, "/")] = file_facts(p)
    return rows


def grade_deployed(rows, staged_sha, bob_sha):
    """DEPLOYED: the server's and admin's copies carry the staged sha256, bob's the copy's."""
    side = {"server": None, "admin": None, "bob": None}
    for k, v in (rows or {}).items():
        if k.startswith("server/"):
            side["server"] = v.get("sha256")
        elif k.startswith("clients/admin/"):
            side["admin"] = v.get("sha256")
        elif k.startswith("clients/bob/"):
            side["bob"] = v.get("sha256")
    obs = {"sides": side, "staged_sha256": staged_sha, "bob_sha256": bob_sha}
    if any(v is None for v in side.values()) or not staged_sha or not bob_sha:
        return "unmeasured", obs
    ok = side["server"] == staged_sha and side["admin"] == staged_sha and side["bob"] == bob_sha and staged_sha != bob_sha
    return ("as_predicted" if ok else "falsified"), obs


# ================================================================ the options file (pure over its text)
NR_OPEN_RX = re.compile(r"^ {4}NR = \{\s*$")
LEAF_RX = re.compile(r"^ {8}(\w+) = ([^,]*),")


def sandbox_nr_block(text):
    """The NR block's leaves of a SandboxVars file as {leaf: raw text}; None when the file holds no NR block."""
    if text is None:
        return None
    leaves, inside, found = {}, False, False
    for line in text.splitlines():
        if not inside:
            if NR_OPEN_RX.match(line):
                inside, found = True, True
            continue
        if line.strip().startswith("}"):
            break
        m = LEAF_RX.match(line)
        if m:
            leaves[m.group(1)] = m.group(2).strip()
    return leaves if found else None


def read_text(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def grade_ini(seeded):
    """INI: the seeded file's NR block holds OPTION = OPTION_SET (the precondition of every x471 option grade)."""
    obs = {"seeded_nr_block": seeded}
    if not isinstance(seeded, dict):
        return "unmeasured", obs
    return ("as_predicted" if same_number(seeded.get(OPTION), OPTION_SET) else "falsified"), obs


# ================================================================ the reads (pure over the replies)
def read_value(reply):
    """(answered, value) of a lua.global reply: answered when it resolved; the value as given."""
    if isinstance(reply, dict) and reply.get("resolved") is True and "value" in reply:
        return True, reply.get("value")
    return False, None


def grade_option(rows, want=OPTION_SET):
    """Every row a lua.global reply of the read; as_predicted when every row answered `want`, falsified when any
    answered row reads another value, else unmeasured (none, or some unanswered)."""
    vals = [read_value(r) for r in rows]
    answered = [v for ok, v in vals if ok]
    obs = {"n": len(rows), "answered": len(answered), "values": answered[:10]}
    if any(not same_number(v, want) for v in answered):
        return "falsified", obs
    if not rows or len(answered) != len(rows):
        return "unmeasured", obs
    return X.grade_verdict("as_predicted", answered), obs


def collect(read_sets, side, name):
    """The replies of one side's read of `name` across the read sets ({tag: {side: {name: reply}}})."""
    return [g(rs, side, name) for rs in (read_sets or {}).values() if g(rs, side, name) is not None]


def take_reads(ask, nodes, tag, read_sets):
    """One read set: every side's reads, each a lua.global reply, stored at read_sets[tag][side][name]."""
    plan = {SRV: (SERVER_OPT_G, SERVER_MOD_G, VERSION_G) + SERVER_READINGS_G,
            ADMIN: (SERVER_OPT_G, CLIENT_MOD_G, VERSION_G) + CLIENT_READINGS_G,
            BOB: (SERVER_OPT_G, CLIENT_MOD_G, VERSION_G) + CLIENT_READINGS_G}
    rs = read_sets.setdefault(tag, {})
    for side, names in plan.items():
        node = nodes.get(side)
        row = rs.setdefault(side, {})
        for nm in names:
            try:
                row[nm] = ask(node, "lua.global", nm, timeout=15) if node is not None else {"error": "no node"}
            except Exception as e:             # noqa: BLE001 - recorded
                row[nm] = {"error": f"{type(e).__name__}: {e}"}
    return rs


def grade_mod_read(read_sets):
    rows = collect(read_sets, SRV, SERVER_MOD_G) + collect(read_sets, ADMIN, CLIENT_MOD_G) + \
        collect(read_sets, BOB, CLIENT_MOD_G)
    v, obs = grade_option(rows)
    sides = {s: len(collect(read_sets, s, n)) for s, n in ((SRV, SERVER_MOD_G), (ADMIN, CLIENT_MOD_G),
                                                            (BOB, CLIENT_MOD_G))}
    obs["per_side"] = sides
    if v == "as_predicted" and not all(sides.values()):
        v = "unmeasured"
    return v, obs


# ================================================================ the logs (pure over their text)
def user_log_facts(text):
    lines = (text or "").splitlines()
    return {"anticheat_bob": [ln[:400] for ln in lines if ANTICHEAT_BOB_RX.search(ln)][:10],
            "anticheat_any": [ln[:400] for ln in lines if ANTICHEAT_RX.search(ln)][:10],
            "fully_connected": [m.group(1) for m in map(FULLY_RX.search, lines) if m],
            "read": text is not None}


def conn_facts(text):
    """bob's connections log: the checksum force-disconnect line (with its following path lines) and every
    force-disconnect line."""
    lines = (text or "").splitlines()
    chk, force = [], []
    for i, ln in enumerate(lines):
        if 'event="force-disconnect"' in ln:
            force.append(ln[:400])
            if FORCE_CHECKSUM_RX.search(ln):
                chk.append(" | ".join(x[:300] for x in lines[i:i + 3]))
    return {"force_checksum": chk[:5], "force_any": force[:10], "read": text is not None}


def find_logs(run_dir):
    """The game's own log files of the run: {key: path} for the server's user and connections logs and bob's
    connections log (the latest of each)."""
    def last(pat):
        hits = sorted(glob.glob(os.path.join(run_dir, *pat)))
        return hits[-1] if hits else None
    return {"server_user": last(("server", "Logs", "*_user.txt")),
            "server_connections": last(("server", "Logs", "*_connections.txt")),
            "bob_connections": last(("clients", BOB, "Logs", "*_connections.txt"))}


def grep_lines(paths, rx, limit=LINE_CAP):
    hits, skipped = [], 0
    for p in paths:
        if p is None:
            continue
        h, s = X.grep_noecho(p, rx, limit, ECHO_RX, NEVER_RX)
        hits += h
        skipped += s
    return hits[:limit], skipped


# ================================================================ the session grades (pure)
def grade_join(o):
    """JOIN: the clean release join (x471). `o` is join_obs's dict."""
    if not o.get("bob_started"):
        return "unmeasured", o
    vers = o.get("versions") or {}
    want = o.get("staged_version")
    ok = (o.get("admin_ready") is True and o.get("bob_ready") is True
          and want is not None and all(vers.get(s) == want for s in (SRV, ADMIN, BOB))
          and sorted(o.get("players_end") or []) == [ADMIN, BOB]
          and BOB in (o.get("fully_connected") or []) and not o.get("anticheat_any")
          and not o.get("server_mismatch") and o.get("user_log_read") is True)
    return ("as_predicted" if ok else "falsified"), o


def grade_kick(o):
    """KICK (x472). `o` is kick_obs's dict."""
    if not o.get("bob_started"):
        return "unmeasured", o
    on_record = bool(o.get("anticheat_bob") or o.get("kicked_bob") or o.get("force_checksum"))
    if not o.get("bob_ready") and on_record:
        return "as_predicted", o
    if o.get("bob_ready") and o.get("bob_answered_end") and not on_record and not o.get("server_mismatch"):
        return "falsified", o
    return "unmeasured", o


def grade_admin_stays(players_end, admin_tk):
    obs = {"players_end": players_end, "admin_tk_at_end": admin_tk}
    if not isinstance(players_end, list) or admin_tk is None:
        return "unmeasured", obs
    ok = players_end == [ADMIN] and admin_tk is not None
    return ("as_predicted" if ok else "falsified"), obs


# ================================================================ pre-boot (on the repository)
def profile_doc_checks(name, doc, text=""):
    """A profile's TOML: its header names its own file; fixture two, admin then bob; PZTestKit and the staged copy;
    Nutrition false, DayLength 1; sleep off; x47-options the [sandbox.NR] block of VisibilityMode alone; x47-checksum
    no NR block and the override naming bob's copy alone; version verify rows on the sides the session attaches."""
    if name not in ("x47-options", "x47-checksum"):
        return {"known_profile": False}
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = [v for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version"]
    c = {"known_profile": True,
         "header_names_file": text.startswith(f"# testing/profiles/{name}.toml"),
         "fixture_two": doc.get("fixture") == "two",
         "clients": doc.get("clients") == [ADMIN, BOB],
         "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
         "mods_staged": mods == ["PZTestKit", NR] and paths.get(NR) == STAGE_MOD,
         "nutrition_false": sb.get("Nutrition") is False,
         "day_length": sb.get("DayLength") == MOD_DAY_LENGTH}
    if name == "x47-options":
        c["nr_block"] = sb.get("NR") == {OPTION: OPTION_SET}
        c["no_override"] = "client_overrides" not in doc
        c["verify_version"] = sorted(v.get("side") for v in vr) == ["client", "client:bob", "server"]
    else:
        c["nr_block"] = "NR" not in sb
        c["no_override"] = doc.get("client_overrides") == {BOB: {NR: BOB_MOD}}
        c["verify_version"] = sorted(v.get("side") for v in vr) == ["client", "server"]
    return c


def mod_head(repo=REPO):
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", MOD_DIR], cwd=repo, capture_output=True, text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def preboot(key, driver_file, repo=REPO):
    """The driver's prefix, profile and file name its session (CLAUDE.md s5); no artifact of the prefix committed; the
    profile's TOML; STAGED_FROM mod/'s last commit; x472 bob's copy one byte off the staged copy. Returns (checks, ok)."""
    import tomllib
    s = SESSIONS.get(key) or {}
    c = {"key": key in SESSIONS, "driver_file": os.path.basename(driver_file) == s.get("driver"),
         "driver_prefix": os.path.basename(driver_file).startswith(key + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", key + "-*"))
    head = mod_head(repo)
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", s.get("profile", "?") + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(s.get("profile"), tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    if key == "x472":
        cc = bob_copy_check(os.path.join(repo, STAGE_MOD), os.path.join(repo, BOB_MOD))
        c["copy"] = cc
        c["copy_ok"] = cc["ok"]
    skip = ("profile_checks", "copy")
    good = all(v is True for k, v in c.items() if k not in skip) and \
        all(v is True for k, v in prof.items() if k != "error")
    return c, good


def staged_gate(repo=REPO):
    """x45g_lib's gate at this lib's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


# ================================================================ the session
def watch_bob(xs, bob, on_ready, until_s, clock=time.time, sleep=time.sleep):
    """Start bob and watch it on the driver's clock: click through Click to Start once in game, stamp every alive
    change, call on_ready() once at ready (it returns the seconds to hold past ready), stop at the hold's end or at
    until_s from the start. Never raises on bob's failure: a never-ready bob is the reading."""
    ph = xs.out.setdefault("bob", {})
    bob.start()
    ph["start_wall"] = xs.wall()
    if xs.tl is not None:
        xs.tl.mark("client_launch", user=BOB)
    deadline = clock() + until_s
    last_click, alive_prev, ready = 0.0, True, False
    while clock() < deadline:
        alive = bob.alive
        if alive != alive_prev:
            ph.setdefault("alive_changes", []).append({"wall": xs.wall(), "alive": alive})
            alive_prev = alive
        if not ready and "ready" in bob.seen:
            ready = True
            ph["ready_wall"] = xs.wall()
            ph["ready_took"] = bob.seen["ready"]
            if xs.tl is not None:
                xs.tl.mark("client_ready", user=BOB, took=bob.seen["ready"])
            deadline = clock() + float(on_ready() or 0.0)
            continue
        if alive and not ready and "in_game" in bob.seen and clock() - last_click > CLICK_GAP_S:
            last_click = clock()
            try:
                bob.click_to_start()
            except Exception as e:             # noqa: BLE001
                ph.setdefault("click_errors", []).append(str(e)[:120])
        sleep(POLL_S)
    ph["window_end_wall"] = xs.wall()
    ph["alive_at_end"] = bob.alive
    ph["seen"] = dict(bob.seen)
    ph["events"] = list(bob.events)[:200]
    return ready


def main(key, driver_file, session_text, pred, budget_s):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import (Timeline, attach_clients, make_client, make_server,   # noqa: E402
                             override_kw, teardown, verify)

    s = SESSIONS[key]
    copy_facts = None
    if key == "x472":
        copy_facts = make_bob_copy(os.path.join(REPO, STAGE_ROOT), os.path.join(REPO, BOB_ROOT))
    pre, ok = preboot(key, driver_file)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(s["profile"])
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(key)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user=ADMIN)
    xs.path = os.path.join(run_dir, s["artifact"])
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": key, "session": session_text, "driver": os.path.basename(driver_file),
        "lib": LIB_FILE, "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", G.LUA_DIR),
        "harness_lua_dirty": git_dirty(G.LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": pred, "constants": CONSTANTS, "meta": {"budget_s": budget_s, "bob_copy": copy_facts},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = staged_gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the pinned commit or the verify rows: {mg!r}; not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(profile.lint_sources(prof, prof.sources))
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server, bob = None, None
    read_sets = out.setdefault("read_sets", {})
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        sbp = os.path.join(run_dir, *SANDBOX_REL)
        out["sandbox_seeded"] = sandbox_nr_block(read_text(sbp))
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        out["build"] = server.build
        tl.mark("server_started", pid=server.proc.pid)
        out["sandbox_after_start"] = sandbox_nr_block(read_text(sbp))
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[ADMIN], started=started))
        out["admin_ready_wall"] = xs.wall()
        bob, restored = make_client(run_dir, BOB, server, rec_fx, safemode=prof.safemode, launcher=prof.launcher,
                                    **override_kw(prof, BOB, server))
        started.append(bob)
        out["bob_restored"] = restored
        out["bob_debug"] = bob.debug
        out["bob_mod_source"] = os.path.relpath(bob.mod_sources.get(NR, ""), REPO).replace(os.sep, "/")
        out["deployed"] = deployed_copies(run_dir)
        xs.mem("before_bob")
        xs.persist()

        def on_ready():
            clients[BOB] = bob
            if key == "x471":
                time.sleep(READ_SETTLE_S)
                take_reads(ask, {SRV: server, ADMIN: clients.get(ADMIN), BOB: bob}, "after_ready", read_sets)
                out["verify"] = verify(prof, server, clients, tl)
                xs.persist()
                return HOLD_S
            out["bob_version_at_ready"] = ask(bob, "lua.global", VERSION_G, timeout=15)
            out["players_at_bob_ready"] = ask(server, "players", "", timeout=15)
            return HOLD_AFTER_READY_S

        if key == "x472":
            out["verify"] = verify(prof, server, clients, tl)
        xs.cur_phase = "bob"
        ready = watch_bob(xs, bob, on_ready, OBS_S)
        if key == "x471" and ready and bob.alive:
            take_reads(ask, {SRV: server, ADMIN: clients.get(ADMIN), BOB: bob}, "end", read_sets)
        if key == "x472" and ready and bob.alive:
            out["bob_version_at_end"] = ask(bob, "lua.global", VERSION_G, timeout=15)
        out["players_end"] = ask(server, "players", "", timeout=15)
        out["admin_tk_at_end"] = ask(clients.get(ADMIN), "lua.global", "TK.version", timeout=15)
        xs.mem("end")
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)
        log_copies = {}

        def read_logs():
            L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "mismatch": MISMATCH_RX.pattern}}
            if server is None:
                return
            outs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
            L["server"], L["server_echo_excluded"] = grep_lines(outs, LOG_RX)
            L["mod_error"] = [ln for ln in L["server"] if MOD_ERR_RX.search(ln)][:40]
            L["server_mismatch"], _ = grep_lines(outs, MISMATCH_RX)
            L["server_kicked_bob"] = [ln for ln in L["server_mismatch"] if KICKED_BOB_RX.search(ln)][:5]
            files = find_logs(run_dir)
            L["files"] = {k: (os.path.relpath(v, run_dir).replace(os.sep, "/") if v else None) for k, v in files.items()}
            L["user"] = user_log_facts(read_text(files["server_user"]) if files["server_user"] else None)
            L["bob_connections"] = conn_facts(read_text(files["bob_connections"]) if files["bob_connections"] else None)
            for k, v in files.items():
                if v:
                    log_copies[("bob-" if k.startswith("bob") else "server-") + os.path.basename(v)] = v
            for c in every:
                lines, _ = X.grep_noecho(c.console, LOG_RX, 80, ECHO_RX, NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines
                L.setdefault("client_mismatch", {})[getattr(c, "username", "?")] = \
                    X.grep_noecho(c.console, MISMATCH_RX, 40, ECHO_RX, NEVER_RX)[0]
            if bob is not None:
                try:
                    with open(bob.console, encoding="utf-8", errors="replace") as fh:
                        tail = fh.read().splitlines()
                    L["bob_console_tail"] = [ln[:400] for ln in tail[-TAIL_LINES:]]
                except OSError as e:
                    L["bob_console_tail"] = f"{type(e).__name__}: {e}"
            out["log_copies"] = {k: {"from": os.path.relpath(v, run_dir).replace(os.sep, "/"),
                                     "sha256": X.sha256_file(v)} for k, v in log_copies.items()}

        def grade_all():
            grade(key, xs, out, read_sets, server, bob)

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        dest = xs.copy_artifacts(REPO, run_id, run_dir, s["artifact"])
        if dest:
            for nm, src in log_copies.items():
                try:
                    shutil.copyfile(src, os.path.join(dest, nm))
                except OSError as e:
                    print(f"could not copy {nm}: {type(e).__name__}: {e}")
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "error": out.get("error"), "summary_error": out.get("summary_error"),
                      "logs_error": out.get("logs_error"), "run_id": run_id, "run_dir": run_dir,
                      "memory": out.get("memory"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str)[:8000])
    return out


def join_obs(out, read_sets, bob_started):
    L = out.get("logs") or {}
    vers = {s: read_value(g(read_sets, "end", s, VERSION_G))[1] for s in (SRV, ADMIN, BOB)}
    return {"bob_started": bob_started, "admin_ready": out.get("admin_ready_wall") is not None,
            "bob_ready": g(out, "bob", "ready_wall") is not None,
            "staged_version": g(out, "manifest_gate", "staged_version"), "versions": vers,
            "players_end": out.get("players_end"), "fully_connected": g(L, "user", "fully_connected"),
            "anticheat_any": g(L, "user", "anticheat_any"), "server_mismatch": L.get("server_mismatch"),
            "user_log_read": g(L, "user", "read")}


def kick_obs(out, bob_started):
    L = out.get("logs") or {}
    return {"bob_started": bob_started, "bob_ready": g(out, "bob", "ready_wall") is not None,
            "bob_answered_end": read_value(out.get("bob_version_at_end"))[1] is not None,
            "anticheat_bob": g(L, "user", "anticheat_bob"), "kicked_bob": L.get("server_kicked_bob"),
            "force_checksum": g(L, "bob_connections", "force_checksum"), "server_mismatch": L.get("server_mismatch"),
            "alive_at_end": g(out, "bob", "alive_at_end")}


def grade(key, xs, out, read_sets, server, bob):
    bob_started = g(out, "bob", "start_wall") is not None
    xs.grade("Z", *G.grade_z(out), "a mod error line in the server log, or admin parked in the debugger")
    if key == "x471":
        xs.grade("INI", *grade_ini(out.get("sandbox_seeded")), "the seeded options file lacks NR.VisibilityMode = 3")
        for name, side in (("OPT_SERVER", SRV), ("OPT_ADMIN", ADMIN), ("OPT_BOB", BOB)):
            v, obs = grade_option(collect(read_sets, side, SERVER_OPT_G))
            xs.grade(name, v, obs, f"SandboxVars.NR.{OPTION} reads another value on {side}")
        xs.grade("MOD_READ", *grade_mod_read(read_sets), "the mod's own option read another value on a side")
        xs.grade("JOIN", *grade_join(join_obs(out, read_sets, bob_started)),
                 "bob or admin not ready, a version or players read off, an Anti-cheat or mismatch line")
        out["readings"]["client_view"] = {s: {n: read_value(g(read_sets, "end", s, n))[1] for n in CLIENT_READINGS_G}
                                          for s in (ADMIN, BOB)}
        out["readings"]["server_readAt"] = read_value(g(read_sets, "end", SRV, SERVER_READINGS_G[0]))[1]
    else:
        pre = out.get("preboot") or {}
        xs.grade("COPY", *grade_copy(pre.get("copy")), "bob's tree differs by more than one byte or not in a comment")
        cc = pre.get("copy") or {}
        xs.grade("DEPLOYED", *grade_deployed(out.get("deployed"), g(cc, "staged_file", "sha256"),
                                             g(cc, "bob_file", "sha256")),
                 "a deployed copy carries the wrong bytes")
        xs.grade("KICK", *grade_kick(kick_obs(out, bob_started)),
                 "bob ready and answering after the hold with no kick line")
        admin_tk = read_value(out.get("admin_tk_at_end"))[1]
        xs.grade("ADMIN_STAYS", *grade_admin_stays(out.get("players_end"), admin_tk),
                 "admin gone or bob still listed at the end")
