"""Slice 12, session 3 (`x123`): the folder-drift counterfactual and the requested-id
discriminator -- LIVE, SERVER ONLY, TWO boots.

**What is under test is the loader's LOOKUP, not its merge rule.** Session 2 (`x122`,
`x122-20260911-032326`) asked which physical bytes ran once a mod was found: the answer was
`TKX_LoaderWhich == "version"` with BOTH unique tree markers resolving, i.e. the two `media`
trees merge and the version tree wins a same-relative-path collision. It could not ask how the
engine FOUND the mod in the first place, because `harness.install` had copied the probe to
`mods/TKX_LoaderVersion` -- a folder whose name equals the id in `Mods=`, so folder-name lookup
and `mod.info` lookup predict the same thing and neither is under test.

Two boots take that degeneracy apart, and they are the two halves of the same question:

  (a) `drift` -- **the folder-drift counterfactual.** The installed folder is renamed
      `mods/TKX_LoaderVersion` -> `mods/TKX_DriftedFolder` and `Mods=` is left naming
      `TKX_LoaderVersion`. A name differing by MORE than case is what NTFS's case-insensitive
      lookup makes necessary: a case-only rename would be answered by the filesystem, not by the
      loader, and would measure nothing. **P16:** if the mod still loads, the loader resolves
      through `mod.info` -- which is what the 52 installed workshop folders that drift from their
      declared id and load in normal play have always implied -- and `harness.install`'s rename to
      `<mods_dir>/<mod id>` is a convenience. If it does not load, the rename is REQUIRED and
      `docs/testing/profiles.md` § Open questions 6 closes the other way. Either answer closes
      that question **M**; it has been **C, and explicitly an inference**, since slice 09
      (`td1-20260910-192457` recorded `source_folder_present: false`, i.e. no run had produced the
      counterfactual at all).

  (b) `common_id` -- **the requested-id discriminator** (controller ruling R3), the reading that
      settles § Open questions 1 for the dedicated-server path. The folder is renamed to
      `mods/TKX_DriftedFolder2` -- a name matching NEITHER id -- and `Mods=` is edited to request
      `TKX_LoaderCommon`, the id in `common/mod.info`, in the same position `TKX_LoaderVersion`
      held. Both manipulations are needed: with the folder left as installed it would still be
      named one of the two ids and a `found` would not separate "the common id is registered" from
      "the folder answered". **P17:** the mod loads under the `common/mod.info` id too --
      `searchForModInfo` registers EVERY `mod.info` it meets into `modIdToDir` and returns the
      first whose id MATCHES the request -- and, because the `media` mapping is by FOLDER and not
      by which `mod.info` answered, `TKX_LoaderWhich` still reads `"version"` and the loader's
      `overrides` line still prints under the id the engine was ASKED for. A
      `required mod "TKX_LoaderCommon" not found` falsifies it and vindicates `mod_lint`'s
      "version folder first" model, in which only one id per folder is ever registered.

**Why a driver can do what a `--profile` run cannot.** `harness.install` copies every profile
source to `<mods_dir>/<mod id>` (`testing/pzt/harness.py:27-32`) and the name-keeping fallback
(`mods.install`) is unreachable on the `--profile` path, so no profile can express either
manipulation -- profiles.md records exactly this as out of reach. A driver can: `make_server`
installs the mods inside `s.seed()` (`session.py:143`, `server.py:181-185`) and RETURNS before
`s.start()`, so the window between the two calls is where the folder is renamed and the ini's
`Mods=` line rewritten (`server.update_ini`, the same function `seed` itself uses).

**Read the two boots TOGETHER** (`joint` in the artifact). Alone, each is ambiguous; the four
combinations are not:

  | (a) found | (b) found | what it means |
  |---|---|---|
  | yes | yes  | resolution is by `mod.info` id, and EVERY `mod.info` met is registered (P17) |
  | yes | no   | only ONE id per folder is registered -- `mod_lint`'s version-folder-first model |
  | no  | yes  | unforeseen; nothing in this design predicts it -- record it and stop |
  | no  | no   | resolution is by FOLDER NAME (P16 the other way), and (b) says NOTHING about ids |

The last row is the one a careless reader gets wrong: if (a) is not found, (b)'s not-found is
already explained by the rename and is not evidence against P17. The artifact says so in words.

**Server only, and no `verify()`.** Every `[[verify]]` row of profile `x12-loader` is
`side = "client"`, and `session.verify` on a session with no client records `no client attached`
-- a row that is neither pass nor fail and is not evidence. So `verify` is deliberately NOT called
and the artifact carries `verify_skipped` saying why, rather than a silently missing key. With no
client the bus still answers: `PZTestKit_Server.lua` polls `pzt-cmd.txt` on `OnTick`, and the
fixture's own ini carries `PauseEmpty=false`, so a player-less server keeps ticking. That claim is
load-bearing for every reading below, so each boot's FIRST bus call is a `ping` with its latency
recorded -- the server-only bus is itself a reading here, not an assumption.

**One live session program-wide.** `pzt doctor` is run as a GATE before each boot, not as a memo:
a boot whose gate is not clean (a FAIL row, or any PZ java process alive) is SKIPPED and says so.
Boot (a) is torn down completely -- `teardown` then `hard_kill` -- and the gate is then polled
until the ports come back before boot (b) is allowed to start. The two boots take separate run
directories and share nothing but this file.

**World changes: none.** Only `ping` and `lua.global` are ever sent -- no RCON, no `moddata.set`,
no sandbox write, no `settimespeed`. `lua.reload` is NEVER sent: re-executing the probe's files
would run both copies of `TKX_Loader_Which.lua` again in the reloader's own order and overwrite
the very global P17's second clause reads. The load-order reading exists only in the state the
boot left behind. The manipulations touch a RUN's copy of `mods/` and its own `Server/pzt.ini`
under `testing/runs/`, which the fixture rebuilds from scratch on every run; the game install, the
workshop folder and the fixture blob are untouched.

If boot (a) wedges, its rows are kept and boot (b) still runs: they are independent manipulations
in separate run directories, and a session that cannot answer P16 can still answer P17. Never
raises through teardown; the artifact is written after every reading and copied byte-for-byte into
`testing/artifacts/<run-id>/`.
"""
import json
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, save          # noqa: E402
from pzt import fixture as fx, profile                                        # noqa: E402
from pzt.paths import new_run_dir                                             # noqa: E402
from pzt.server import MOD_MISSING_RX, update_ini                             # noqa: E402
from pzt.session import (Timeline, check_mods_loaded, make_server,            # noqa: E402
                         teardown)

PROFILE = "x12-loader"
MODS = ("PZTestKit", "TKX_LoaderVersion", "TKX_CommonOnly")
# The name `harness.install` copies the probe to: `<mods_dir>/<mod id>`, the id the profile
# declares. Both boots rename AWAY from it, which is the whole manipulation.
INSTALLED_ID = "TKX_LoaderVersion"     # 42.20/mod.info's id, and the profile's [[mods]] id
COMMON_ID = "TKX_LoaderCommon"         # common/mod.info's id -- what boot (b) asks for
# Session 2's run, whose readings these two boots are the counterfactuals of (amendment 9):
# TKX_LoaderWhich == "version" with BOTH tree markers resolving (merge rule, n = 2);
# TKX_CommonOnly.version == 1; and ZERO server log lines naming TKX_LoaderCommon -- so the
# engine is NOT expected to announce the passed-over id, and the wide grep below is there to
# record that count rather than to find something.
SESSION_2_RUN = "x122-20260911-032326"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
# The subjects are OURS, so "which commit are these bytes" is a provenance question about them
# exactly as it is about the harness Lua: a probe edited but not committed would make the artifact
# cite a tree that is not the tree that ran.
SUBJECT_DIRS = {"TKX_LoaderVersion": "testing/experiments/tkx-loader-probe",
                "TKX_CommonOnly": "testing/experiments/TKX_CommonOnly"}

# ---- the greps -------------------------------------------------------------------------------
# `grep_numbered` takes a COMPILED regex and the escaping is the caller's job (pass-2 lesson,
# session.py:51). **A limit is a BREAK, not a window** (docs/testing/README.md § Observation): a
# result of exactly `limit` is SATURATION, never a census. The limits are session 2's server-side
# ones, which were sized at >= 2x its acceptance counts (1 `loading TKX_LoaderVersion`, 1
# `overrides`, 6 wide `TKX_Loader` hits) with headroom on top. There is no client here, so the
# client limits are gone rather than halved.
LOAD_VERSION_RX = re.compile(re.escape("loading " + INSTALLED_ID))
LOAD_COMMON_RX = re.compile(re.escape("loading " + COMMON_ID))
# Amendment 9's wide read, kept at limit 40: session 2 saw ZERO lines naming the common id, so
# this records a count rather than expecting a hit. Case-insensitive so a lower-cased path
# mention cannot hide from it.
LOADER_WIDE_RX = re.compile(r"TKX_Loader", re.IGNORECASE)
# **The reading the rename makes possible.** `TKX_Loader` does NOT match `TKX_DriftedFolder`, so
# without this grep the engine's own mentions of the renamed directory would be invisible. A
# `…mods\TKX_DriftedFolder\42.20\media\AnimSets` line (the loader probing optional media folders
# and logging the misses -- baselined noise, see server.BASELINE_NOISE) is the engine saying in
# its own words that it walked a folder whose name is in no `Mods=` line anywhere: direct evidence
# for P16 rather than an inference from which global survived.
DRIFT_WIDE_RX = re.compile(r"TKX_Drifted", re.IGNORECASE)
COMMONONLY_WIDE_RX = re.compile(r"TKX_CommonOnly", re.IGNORECASE)
# `…mods\<folder>\<tree>\media…` out of such a line, either slash flavour. The character class
# takes DIGITS as well as letters -- boot (b)'s folder is `TKX_DriftedFolder2`, and session 2's
# `[A-Za-z_]+` would have captured `TKX_DriftedFolder` and then failed on the `2`, silently
# reporting no walked trees for the very boot that needs them.
TREE_WALK_RX = re.compile(r"mods[\\/](TKX_[A-Za-z0-9_]+)[\\/]([^\\/]+)[\\/]media", re.IGNORECASE)
# Every TKX `overrides` line, whichever id printed it -- P17's third clause is about WHICH id the
# loader names in it. Digits in the class for the same reason as above.
OVERRIDE_ANY_RX = re.compile(r'mod "(TKX_[A-Za-z0-9_]+)" overrides')
# The same print with NO assumption about the name inside the quotes. `overrides_any` asks "which
# TKX id printed one"; this asks "did the loader print one at all, and under WHAT name" -- and
# the second question is the one a session that renamed the folder has to ask, because what the
# loader puts in those quotes when the directory name is in no `Mods=` line anywhere is precisely
# what is unknown. A restricted grep can only ever confirm the shape it already assumed.
OVERRIDE_WIDE_RX = re.compile(r"\boverrides\b")
LOADING_ANY_RX = re.compile(r"loading TKX_")
NILCALL_RX = re.compile(r"tried to call nil|stack traceback|attempted to index")
# `mod "<id>" overrides <tail>`; the id group is `[^"]+` for the reason above, and the tail may be
# EMPTY -- x121 (`x121-20260911-030023`, greps.overrides) recorded an empty-tail
# `mod "TKX_ItemOverride" overrides ` line beside a real one -- which is why that group is `.*`
# and not `\S+`: an empty tail must parse to "" and be recorded, not fail to match.
TAIL_RX = re.compile(r'mod "([^"]+)" overrides ?(.*)$')

# name, regex, limit. The two per-boot greps (the exact `loading <requested id>` and
# `required mod "<requested id>" not found` the brief names) are built per boot and prepended.
GREPS = (
    ("loading_version",  LOAD_VERSION_RX,      6),
    ("loading_common",   LOAD_COMMON_RX,       6),
    ("loader_wide",      LOADER_WIDE_RX,      40),   # amendment 9's wide read, limit verbatim
    ("drift_wide",       DRIFT_WIDE_RX,       40),   # the renamed folder in the engine's words
    ("commononly_wide",  COMMONONLY_WIDE_RX,  40),   # the untouched second mod (the control)
    ("overrides_any",    OVERRIDE_ANY_RX,     20),
    ("overrides_wide",   OVERRIDE_WIDE_RX,    20),   # every `overrides` print, name unassumed
    ("loading_any",      LOADING_ANY_RX,      12),
    ("lua_errors",       NILCALL_RX,          12),
    ("mod_missing",      MOD_MISSING_RX,      10),   # the generic line, verbatim if it fires
)

# The tail session 2 measured, LOWER-CASED the way the loader prints relative paths
# (`td3-20260911-001948`: `media/lua/client/autocook.lua` for a file shipped as `AutoCook.lua`).
# Compared case-insensitively -- the case is the loader's business, the path is the reading.
WHICH_REL = "media/lua/shared/tkx_loader_which.lua"

# ---- the globals, and what each one separates ------------------------------------------------
# `TK.version` FIRST on every boot (session 2's amendment 5): a `resolved: false` below is only a
# finding once the control has passed -- otherwise it says the `_G` walk is broken.
GLOBALS = (
    ("TK.version", "control",
     "TK is a global on purpose (PZTestKit_Core.lua:2). MUST be 1: a resolved=false here says "
     "the _G walk is broken, not that a mod global is absent -- and with no client attached it "
     "also re-proves that the SERVER side of the bus is executing at all."),
    ("TKX_LoaderWhich", "the collision (both trees)",
     "media/lua/shared/TKX_Loader_Which.lua exists in common/ AND 42.20/; the copy that ran last "
     "owns the global. Session 2 read 'version'. P17's second clause says the media mapping is by "
     "FOLDER, so asking for the common id must not change this answer."),
    ("TKX_LoaderCommonTree", "common/ only",
     "common/.../TKX_Loader_Common.lua:4. No file of that relative path exists under 42.20/, so "
     "nothing can override it: absent => the common/ tree never ran AT ALL, a different fact from "
     "'common/ lost the collision'."),
    ("TKX_LoaderVersionTree", "42.20/ only",
     "42.20/.../TKX_Loader_Version.lua:4, the mirror of the above. Together the two say whether "
     "BOTH trees of the drifted folder were walked."),
    ("TKX_CommonOnly.version", "the untouched second mod",
     "mod E is installed under its own id and is NOT manipulated in either boot, so this is the "
     "within-boot control: 1 here means the session, the profile and the loader were fine and "
     "the only thing that changed is the folder/id under test. Session 2 read 1."),
)

# The dormant `sent` branch's routing table (slice-11 driver note). This driver sends only `ping`
# and `lua.global`, both of which answer INLINE, so the branch can never fire; the map is left
# EMPTY on purpose, which makes `probe` record any such ack raw instead of blocking on a result
# doc that would never be written.
RESULT_DOC = {}

# The joint reading, written down BEFORE the run so it cannot be composed to fit the answer
# (amendment 8's matrix, verbatim in substance).
JOINT = {
    (True, True): "(a) found AND (b) found: mod resolution is by mod.info ID, not by folder "
                  "name, AND the common/mod.info id is registered and addressable -- every "
                  "mod.info the loader meets is registered (searchForModInfo's modIdToDir "
                  "write), which is P16 and P17 together.",
    (True, False): "(a) found but (b) NOT found: the folder resolves through mod.info, but only "
                   "ONE id per folder is registered -- mod_lint's 'version folder first' model "
                   "is vindicated for the requested-id lookup and P17 is falsified.",
    (False, True): "(a) NOT found while (b) IS: unforeseen. The version id did not resolve out "
                   "of a drifted folder but the common id did. Nothing in this design predicts "
                   "it; it is recorded as the finding and not explained away.",
    (False, False): "BOTH not found: resolution is by FOLDER NAME (P16 closes the other way, "
                    "and harness.install's rename is REQUIRED). Boot (b) is then UNINFORMATIVE "
                    "about the id question -- its not-found is already explained by its own "
                    "rename -- and must NOT be read as evidence against P17.",
}

# ---- the two boots ---------------------------------------------------------------------------
# `ini_mods` None = leave `Mods=` exactly as `Server.seed` wrote it. `ini_absent` is the id that
# must NOT survive the edit: a `Mods=` line still naming TKX_LoaderVersion would make boot (b) a
# repeat of boot (a) with a longer folder name.
BOOTS = (
    {"key": "drift", "prefix": "x123", "folder": "TKX_DriftedFolder",
     "requested": INSTALLED_ID, "ini_mods": None, "ini_absent": None, "phase": "P16",
     "title": "the folder-drift counterfactual"},
    {"key": "common_id", "prefix": "x123b", "folder": "TKX_DriftedFolder2",
     "requested": COMMON_ID, "ini_mods": "PZTestKit;TKX_LoaderCommon;TKX_CommonOnly",
     "ini_absent": INSTALLED_ID, "phase": "P17",
     "title": "the requested-id discriminator (controller ruling R3)"},
)

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
# Boot (a)'s prefix owns the ARTIFACT id: one artifact, both boots, keys `drift` and `common_id`.
run_id, run_dir = new_run_dir("x123")
path = os.path.join(run_dir, "platform-folder.json")
tl, t0 = Timeline(), time.time()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)


class _NoServer:
    """`save` snapshots `server.errors`; between the boots there is no live server, and a stub is
    honest where a stale reference would be misleading."""
    errors = []


CURRENT = [_NoServer()]          # the server `save` snapshots; per-boot lists are authoritative


def rel(p):
    try:
        return os.path.relpath(p, REPO).replace("\\", "/")
    except ValueError:                            # different drive -- absolute is still readable
        return p.replace("\\", "/")


def tree_census(src):
    """Every file under a subject's source folder, as a sorted list of forward-slashed relative
    paths. The artifact has to be readable without the repo beside it, and "which files were in
    which tree" is the premise of every prediction here."""
    try:
        out_ = []
        for root, _dirs, files in os.walk(src):
            for f in files:
                out_.append(os.path.relpath(os.path.join(root, f), src).replace("\\", "/"))
        return sorted(out_)
    except OSError as e:                          # noqa: BLE001 - provenance, never fatal
        return [f"{type(e).__name__}: {e}"]


out = {
    "run_id": run_id,
    "session": "x123 -- slice 12 session 3: the folder-drift counterfactual (a) and the "
               "requested-id discriminator (b). SERVER ONLY, two boots, one artifact.",
    "user": None,
    "profile": prof.report(),
    "mods": list(MODS),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "session_2_run": SESSION_2_RUN,
    "subjects": {
        mid: {"source": r,
              "commit": git_say("log", "-1", "--format=%h", "--", r),
              "dirty": git_dirty(r)[0], "dirty_note": git_dirty(r)[1],
              "files": tree_census(os.path.join(REPO, r.replace("/", os.sep)))}
        for mid, r in SUBJECT_DIRS.items()
    },
    "why_a_driver": (
        "harness.install copies every profile source to <mods_dir>/<mod id> (harness.py:27-32) "
        "and mods.install's name-keeping fallback is unreachable on the --profile path, so "
        "NEITHER manipulation here can be expressed as a profile -- profiles.md records exactly "
        "this as out of reach. make_server installs the mods inside s.seed() (session.py:143, "
        "server.py:181-185) and returns BEFORE s.start(), and that window is where this driver "
        "renames the folder and rewrites the ini's Mods= line (server.update_ini, the same "
        "function seed itself uses)."),
    "why_more_than_case": (
        "both renames differ from the installed name by MORE than case. NTFS looks up names "
        "case-insensitively, so a case-only rename would be answered by the filesystem before "
        "the loader ever saw it and would measure nothing about mod resolution."),
    "verify_skipped": (
        "session.verify is deliberately NOT called. Every [[verify]] row of profile x12-loader "
        "is side = \"client\" and this session attaches no client, so each row would record "
        "`no client attached` -- neither a pass nor a fail, and not evidence. The bus readings "
        "below carry the equivalent weight on the side that exists."),
    "server_only_note": (
        "no client is attached in either boot, so the session costs ~40 s instead of ~90 s. The "
        "bus still answers: PZTestKit_Server.lua polls pzt-cmd.txt on OnTick and the fixture's "
        "ini carries PauseEmpty=false, so a player-less server keeps ticking. Each boot's first "
        "bus call is a `ping` with its latency recorded, so that claim is a reading here and not "
        "an assumption."),
    "world_changes": {
        "restored": "nothing -- this driver writes no world state at all.",
        "left_in_place": [],
        "why": "the only bus commands sent are `ping` and `lua.global`, which READ and never call "
               "what they find (PZTestKit_Core.lua:782-784). No RCON, no moddata.set, no sandbox "
               "write, no settimespeed.",
        "lua_reload": "NEVER sent -- reloading would re-execute BOTH copies of "
                      "TKX_Loader_Which.lua in the reloader's own order and overwrite the very "
                      "global P17's second clause reads.",
        "files_touched": "a RUN's own copy of mods/ and Server/pzt.ini under testing/runs/, which "
                         "the fixture rebuilds from scratch every run. The game install, the "
                         "workshop folder and the fixture blob are untouched.",
    },
    "joint_matrix_stated_in_advance": {" / ".join(str(x) for x in k): v
                                       for k, v in JOINT.items()},
    "boots": {}, "notes": [], "phases": {}, "verdicts": {},
}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def snap():
    save(path, out, tl, CURRENT[0])


def doctor_gate(attempts=1, wait=6.0):
    """`pzt doctor` as a GATE before a boot, not as a memo after one.

    Two conditions, and BOTH are the binding rule "one live session program-wide": the exit code
    (a FAIL row -- ports held, or a fixture/build mismatch) and the `PZ java processes: none`
    line, which doctor reports as a WARN and therefore does NOT fold into its exit code. A stray
    PZ java process is exactly the thing that must stop a boot, so it is checked here explicitly.

    Returns `(ok, tries)` and never raises; every attempt is kept, so a gate that had to wait for
    the previous boot's ports says how long it waited.
    """
    tries = []
    ok = False
    for i in range(attempts):
        clean, text = doctor()
        lines = text.strip().splitlines()
        java_none = any("PZ java processes: none" in ln for ln in lines)
        ok = bool(clean) and java_none
        tries.append({"attempt": i + 1, "wall": wall(), "exit_clean": bool(clean),
                      "java_none": java_none, "ok": ok, "lines": lines})
        if ok:
            break
        if i < attempts - 1:
            time.sleep(wait)
    return ok, tries


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). `ping` and `lua.global` answer INLINE, so it is
        DORMANT here and `RESULT_DOC` is empty: an ack in that shape is recorded raw rather than
        blocked on.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A string
        where a table belongs is re-asked ONCE and BOTH readings are kept.
    """
    t, t_epoch = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if isinstance(val, str) and val.strip().startswith("sent"):
        name = RESULT_DOC.get(cmd)
        out["notes"].append({"dormant_sent_branch": cmd, "routed_to": name})
        if name is None:
            meta["route"] = "unmapped -- ack kept raw rather than waiting on a result doc"
        else:
            try:
                val = side.bus.wait_result(name, timeout=20, after=t_epoch)
            except (RuntimeError, TimeoutError, OSError) as e:
                val = {"error": f"{type(e).__name__}: {e}", "ack": val}
            meta["route"] = "result-doc"
    elif not isinstance(val, dict):
        meta["reasked"] = True
        meta["first_reply"] = val
        val = ask(side, cmd, args, timeout=timeout)
        meta["wall_done"] = wall()
    if isinstance(val, dict):
        val = dict(val)
        val["_probe"] = meta
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    """The prediction, the falsifier, the reading and the verdict, in one place and beside each
    other. `verdict` is one of as_predicted / falsified / trivial / unmeasured -- a reading that
    comes back trivial or unmeasured is RECORDED as such and never re-run into a prettier one."""
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    # `name=`, NOT `phase=`: Timeline.mark's first POSITIONAL parameter is called `phase`
    # (session.py:31), so a `phase=` keyword here is a TypeError, not a detail field.
    tl.mark("verdict", name=phase, verdict=verdict)
    snap()


def grep_numbered(path_, rx, limit):
    """`session.grep_file` with the LINE NUMBER kept: which loader lines arrived, and in what
    order, is part of the evidence, and order is unreadable without the numbers."""
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:200]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def srv_grep(name, rx, limit, log_path):
    """One regex over the server log, with the saturation test written down rather than left to
    the reader. Server only -- there is no client console in this session."""
    hits = grep_numbered(log_path, rx, limit)
    row = {"name": name, "pattern": rx.pattern, "limit": limit, "count": len(hits),
           "saturated": len(hits) >= limit, "hits": hits}
    if name.startswith("overrides"):
        row["tails"] = tails_of(hits)
    return row


def tails_of(hits):
    """The `<id>` and `<rel>` halves of every `mod "<id>" overrides <rel>` hit, with its line
    number. P17's third clause is about the ID; session 2's reading was about the TAIL; an EMPTY
    tail is a real shape of this print (x121) and is kept as `""` rather than dropped."""
    out_ = []
    for h in hits:
        m = TAIL_RX.search(h.get("text", "")) if isinstance(h, dict) else None
        if m:
            out_.append({"line": h["line"], "mod": m.group(1), "tail": m.group(2).strip()})
    return out_


def tree_walk_of(grep_row, folder):
    """Which TREES of `folder` the engine was seen touching, from the `…mods\\<folder>\\<tree>\\
    media…` paths its own file-walk exceptions quote. `["42.20", "common"]` is a direct
    observation that BOTH media trees under the RENAMED directory were enumerated -- the engine's
    own words, rather than an inference from which global survived."""
    trees = set()
    for h in grep_row.get("hits", []):
        if not isinstance(h, dict):
            continue
        for m in TREE_WALK_RX.finditer(h.get("text", "")):
            if m.group(1).lower() == folder.lower():
                trees.add(m.group(2))
    return sorted(trees)


def listing(mods_dir):
    """The directory listing of `<run>/server/mods/`, verbatim and sorted, the way td1's
    `folder_check` recorded it (`td1-20260910-192457`). Recorded for BOTH boots (amendment 8):
    what is on disk is the premise of every verdict below, and a reader who cannot see it cannot
    check the reasoning."""
    try:
        return sorted(os.listdir(mods_dir))
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return [f"{type(e).__name__}: {e}"]


def ini_mods_line(ini_path):
    """The `Mods=` line of a server ini, verbatim. Read off the FILE and never reconstructed from
    `server.mods`: this driver rewrites the file behind the Server object's back, so the Python
    attribute and the bytes the engine reads deliberately disagree in boot (b)."""
    try:
        with open(ini_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.split("=", 1)[0].strip() == "Mods":
                    return line.rstrip("\r\n")
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return f"{type(e).__name__}: {e}"
    return None


def read_global(srv, name, sink):
    """One `lua.global`, with its reply CHECKED and not merely recorded.

    `witness.fields` has a `count` to reconcile against the names sent; `lua.global` has no such
    field, so the integrity check is the reply's own echo: it must name the global that was asked
    for and the side it was asked on. A reply that names a different global is a bus crossing, and
    a reading taken from a crossed reply is worth nothing -- so the check travels with every row
    and is summarised per boot."""
    r = probe(srv, "lua.global", name)
    d = r if isinstance(r, dict) else {}
    echo_ok = d.get("name") == name and d.get("side") == "server"
    sink.append({"name": name, "echo_ok": echo_ok,
                 "echo_name": d.get("name"), "echo_side": d.get("side")})
    return {"side": "server", "name": name,
            "resolved": d.get("resolved"), "type": d.get("type"), "value": d.get("value"),
            "keyCount": d.get("keyCount"), "failedAt": d.get("failedAt"),
            "stoppedOn": d.get("stoppedOn"),
            "echo_name": d.get("name"), "echo_side": d.get("side"), "echo_ok": echo_ok,
            "error": d.get("error") if isinstance(r, dict) else r,
            "wall": (d.get("_probe") or {}).get("wall"),
            "reply": r}


def res_of(g, name):
    return ((g.get(name) or {}).get("resolved"))


def val_of(g, name):
    return ((g.get(name) or {}).get("value"))


def found_state(b):
    """Did the mod the boot ASKED for load? True / False / **None for a mixed reading**.

    Graded on the ENGINE'S OWN two announcements and nothing else -- the `loading <id>` line and
    the `required mod "<id>" not found` line -- because they are what "found" means. What the mod's
    Lua then did is CORROBORATION and is graded separately (`probe_ran` / `bus_alive`): folding a
    silent bus into this answer would turn a harness fault into a loader finding, which is exactly
    the inversion this session is here to avoid.

    `None` is a real answer, not a fallback: a boot where the engine printed BOTH lines, or
    NEITHER, is a surprising reading and must not be flattened into a tidy True or False.
    """
    if not b.get("started") or "greps" not in b:
        return None
    loading = b["greps"]["loading_requested"]["count"] > 0
    missing = (b["requested_id"] in b.get("mods_not_found", [])
               or b["greps"]["missing_requested"]["count"] > 0)
    if loading and not missing:
        return True
    if missing and not loading:
        return False
    return None


def bus_alive(b):
    """Did the SERVER half of the bus execute at all? `TK.version` is a global on purpose
    (PZTestKit_Core.lua:2), so a 1 here says the `_G` walk ran; anything else says the reading
    below it is unavailable rather than negative."""
    return val_of(b.get("globals") or {}, "TK.version") == 1


def probe_ran(b):
    """Did the mod under test's own Lua run? Either unique tree marker resolving is enough --
    which of the two is the merge question session 2 already answered, not this one's."""
    g = b.get("globals") or {}
    return res_of(g, "TKX_LoaderVersionTree") is True or res_of(g, "TKX_LoaderCommonTree") is True


def run_boot(plan):
    """One boot, start to hard_kill. Never raises: an exception anywhere inside is recorded on the
    boot's own row and the OTHER boot still runs (amendment 5 -- independent manipulations in
    separate run directories)."""
    b = {"key": plan["key"], "title": plan["title"], "phase": plan["phase"],
         "requested_id": plan["requested"], "folder_renamed_to": plan["folder"],
         "folder_matches_an_id": plan["folder"] in (INSTALLED_ID, COMMON_ID),
         "ini_mods_planned": plan["ini_mods"], "wall_start": wall(),
         "started": False, "echo_checks": []}
    out["boots"][plan["key"]] = b
    srv, mods_dir = None, None
    try:
        ok, tries = doctor_gate(attempts=plan.get("gate_attempts", 1),
                                wait=plan.get("gate_wait", 6.0))
        b["doctor"] = tries
        b["doctor_ok"] = ok
        if not ok:
            b["skipped"] = ("doctor gate not clean -- refusing to boot. One live session "
                            "program-wide is a binding rule, and a run booted onto a dirty "
                            "machine is not evidence.")
            note(f"boot {plan['key']} SKIPPED: doctor gate not clean")
            return b

        # Boot (a) is handed the run dir created at import time, so the ARTIFACT id and boot (a)'s
        # run id are the same string by construction. Calling `new_run_dir` twice with the same
        # prefix would return the same path only while the second hand of the clock had not
        # turned, which is not something an artifact's identity may depend on.
        if plan.get("run_dir"):
            b["run_id"], rd = plan["run_id"], plan["run_dir"]
        else:
            b["run_id"], rd = new_run_dir(plan["prefix"])
        b["run_dir"] = rel(rd)
        tl.mark("boot_seed", key=plan["key"], run=b["run_id"])
        srv = make_server(rd, rec, mods=prof.mods, mod_sources=prof.sources,
                          mod_skip=prof.skip, sandbox=prof.sandbox or None)
        CURRENT[0] = srv
        mods_dir = os.path.join(srv.cache, "mods")
        b["mods_dir"] = rel(mods_dir)
        b["missing_mods_at_install"] = list(srv.missing_mods)
        b["listing_as_installed"] = listing(mods_dir)
        b["server_mods_attribute"] = list(srv.mods)

        # ---- manipulation 1: the rename ------------------------------------------------------
        src = os.path.join(mods_dir, INSTALLED_ID)
        dst = os.path.join(mods_dir, plan["folder"])
        b["rename"] = {"from": INSTALLED_ID, "to": plan["folder"],
                       "src_existed": os.path.isdir(src), "ok": False}
        try:
            os.rename(src, dst)
            b["rename"]["ok"] = True
        except OSError as e:                      # noqa: BLE001 - recorded, aborts the boot
            b["rename"]["error"] = f"{type(e).__name__}: {e}"
        b["listing_after_rename"] = listing(mods_dir)
        tl.mark("rename", key=plan["key"], to=plan["folder"], ok=b["rename"]["ok"])

        # ---- manipulation 2: the ini ---------------------------------------------------------
        b["ini_path"] = rel(srv.ini)
        b["ini_mods_as_seeded"] = ini_mods_line(srv.ini)
        if plan["ini_mods"]:
            update_ini(srv.ini, {"Mods": plan["ini_mods"]})
        b["ini_mods_before_start"] = ini_mods_line(srv.ini)

        line = b["ini_mods_before_start"] or ""
        b["manipulation_check"] = {
            "rename_ok": b["rename"]["ok"],
            "requested_id_in_ini": plan["requested"] in line,
            "absent_id_out_of_ini": (plan["ini_absent"] not in line) if plan["ini_absent"]
            else None,
            "installed_id_folder_gone": INSTALLED_ID not in b["listing_after_rename"],
            "drifted_folder_present": plan["folder"] in b["listing_after_rename"],
        }
        mc = b["manipulation_check"]
        manip_ok = (mc["rename_ok"] and mc["requested_id_in_ini"]
                    and mc["installed_id_folder_gone"] and mc["drifted_folder_present"]
                    and mc["absent_id_out_of_ini"] is not False)
        b["manipulation_ok"] = manip_ok
        if not manip_ok:
            b["skipped"] = ("the manipulation did not take -- refusing to pay for a boot that "
                            "could not answer the question. A session booted with the folder or "
                            "the Mods= line in any other state is a DIFFERENT experiment and "
                            "would pollute the artifact rather than fill it.")
            note(f"boot {plan['key']} SKIPPED: manipulation_check {mc}")
            return b

        # ---- the boot ------------------------------------------------------------------------
        b["start_wall"] = wall()
        b["start_seconds"] = srv.start()
        b["started"] = True
        b["build"] = srv.build
        tl.mark("server_started", key=plan["key"], took=b["start_seconds"])
        snap()

        # The guarded boot check. `check_mods_loaded` raises the moment the server says a mod is
        # missing; for the id THIS boot manipulated that raise IS the reading (P16's falsifier /
        # P17's falsifier), so it is caught, recorded verbatim and the boot continues. Any OTHER
        # missing mod means a broken session rather than a finding -- the boot is abandoned at
        # that point, but it is NOT re-raised: raising here would take the other boot down with
        # it, and the other boot is an independent manipulation.
        mods_check = {"raised": False, "missing": [], "log_lines": []}
        try:
            check_mods_loaded(tl, srv)
        except RuntimeError as e:
            missing = sorted(set(srv.mods_not_found))
            mods_check = {"raised": True, "error": str(e), "missing": missing,
                          "log_lines": grep_numbered(srv.log_path, MOD_MISSING_RX, 10)}
            note(f"boot {plan['key']}: check_mods_loaded raised: {e}")
            unexpected = sorted(set(missing) - {plan["requested"]})
            mods_check["unexpected"] = unexpected
            if unexpected:
                b["mods_loaded_check"] = mods_check
                b["fatal"] = ("a mod OTHER than the one under test is missing "
                              f"({', '.join(unexpected)}): a broken session, not a finding.")
                return b
            note(f"boot {plan['key']}: the missing set is exactly "
                 f"{{{plan['requested']}}} -- that FAIL is the reading this boot exists to take.")
        b["mods_loaded_check"] = mods_check
        b["mods_not_found"] = sorted(set(srv.mods_not_found))

        # ---- the loader's own lines, from the log --------------------------------------------
        # Taken before any bus read: they cost no bus time and cannot delay a reading. The two
        # per-boot greps the brief names go first, exact and escaped.
        req = plan["requested"]
        per_boot = (
            ("loading_requested", re.compile(re.escape(f"loading {req}")), 6),
            ("missing_requested", re.compile(re.escape(f'required mod "{req}" not found')), 6),
        )
        b["greps"] = {n: srv_grep(n, rx, lim, srv.log_path) for n, rx, lim in per_boot + GREPS}
        tl.mark("greps", key=plan["key"],
                loading=b["greps"]["loading_requested"]["count"],
                missing=b["greps"]["missing_requested"]["count"],
                overrides=b["greps"]["overrides_any"]["count"])
        b["media_trees_walked"] = {
            plan["folder"]: tree_walk_of(b["greps"]["drift_wide"], plan["folder"]),
            "TKX_CommonOnly": tree_walk_of(b["greps"]["commononly_wide"], "TKX_CommonOnly"),
        }
        snap()

        # ---- the bus, with no client attached ------------------------------------------------
        # `ping` FIRST and with a generous timeout: that the server half of the bus answers at
        # all with no player on the server is this session's own novel condition, so its latency
        # is a recorded reading rather than an assumption. Then the globals, control first.
        t_ping = time.time()
        b["ping"] = {"reply": ask(srv, "ping", "", timeout=60),
                     "seconds": round(time.time() - t_ping, 2), "wall": wall()}
        tl.mark("ping", key=plan["key"], took=b["ping"]["seconds"])
        g = {}
        for name, tree, why in GLOBALS:
            g[name] = read_global(srv, name, b["echo_checks"])
            g[name]["tree"] = tree
            g[name]["why"] = why
            snap()
        b["globals"] = g
        b["echo_ok"] = all(x["echo_ok"] for x in b["echo_checks"]) if b["echo_checks"] else None
        tl.mark("globals", key=plan["key"], read=len(g), echo_ok=b["echo_ok"])

        # ---- folder_check, td1's shape, verbatim ---------------------------------------------
        # ONE `os.listdir`, reused by every flag below it: four separate reads could in principle
        # disagree, and a reader checking `installed_id_folder_present` against `listing` must be
        # looking at the same read of the directory.
        now = listing(mods_dir)
        b["folder_check"] = {
            "mods_dir": rel(mods_dir),
            "listing": now,
            "installed_id_folder_present": INSTALLED_ID in now,
            "common_id_folder_present": COMMON_ID in now,
            "drifted_folder_present": plan["folder"] in now,
            "mod_info_under_drifted_folder": {
                "42.20": os.path.isfile(os.path.join(mods_dir, plan["folder"], "42.20",
                                                     "mod.info")),
                "common": os.path.isfile(os.path.join(mods_dir, plan["folder"], "common",
                                                      "mod.info")),
            },
            "ini_mods_line": ini_mods_line(srv.ini),
            "requested_id": plan["requested"],
            "folder_matches_requested_id": plan["folder"] == plan["requested"],
            "predicted": ("the folder keeps the name this driver gave it -- harness.install's "
                          "copy already happened inside make_server, and nothing the engine does "
                          "renames a mods/ folder back. The reading that matters is not the "
                          "listing but whether a mod in a folder of THIS name, requested under "
                          "THAT id, loaded at all."),
        }
        tl.mark("folder_check", key=plan["key"],
                listing=",".join(b["folder_check"]["listing"])[:80])
        snap()
    except Exception as e:                        # noqa: BLE001 - keep the rows already collected
        b["error"] = f"{type(e).__name__}: {e}"
        b["traceback"] = traceback.format_exc()[-3000:]
        tl.mark("boot_error", key=plan["key"], detail=str(e)[:160])
    finally:
        b["wall_readings_done"] = wall()
        if srv is not None:
            b["server_errors"] = srv.errors[:20]
            b["server_error_count"] = len(srv.errors)
            snap()
            try:
                teardown(tl, srv, [])
            except Exception as e:                # noqa: BLE001 - never raise through teardown
                b["teardown_error"] = f"{type(e).__name__}: {e}"
            finally:
                hard_kill(srv, [])
                b["server_errors"] = srv.errors[:20]
                b["server_error_count"] = len(srv.errors)
                b["listing_after_teardown"] = listing(mods_dir) if mods_dir else None
                b["ini_mods_after_teardown"] = ini_mods_line(srv.ini)
                b["log_path"] = rel(srv.log_path)
        b["wall_end"] = wall()
        b["found_state"] = found_state(b)
        snap()
    return b


def publish():
    """Write the artifact and copy it into `testing/artifacts/<run-id>/`. Called once as soon as
    BOTH boots are done and again after the grading: the live half of this session is the
    expensive, unrepeatable half, so its rows reach the artifact before any pure-Python grading
    gets a chance to raise on the way there."""
    snap()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-folder.json")
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                        # noqa: BLE001 - final path, never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")


# ================= boot (a): the folder-drift counterfactual ==================================
run_boot({**BOOTS[0], "run_id": run_id, "run_dir": run_dir})
a = out["boots"]["drift"]

# ================= boot (b): the requested-id discriminator ===================================
# Both boots run BEFORE any grading. Boot (b) does not depend on boot (a)'s verdict -- only on
# `a["found_state"]`, which `run_boot`'s own finally computed -- so there is nothing to gain by
# interleaving them and a whole live boot to lose if a grading expression were to raise.
# `gate_attempts` > 1 is the between-boots wait: boot (a)'s teardown already ran `teardown` +
# `hard_kill`, and the gate then POLLS until the ports come back, so the two cannot overlap even
# if a shutdown is slow.
run_boot({**BOOTS[1], "gate_attempts": 10, "gate_wait": 6.0})
bb = out["boots"]["common_id"]
publish()

# ================= P16: boot (a) read =========================================================
grep_a = a.get("greps") or {}
a_globals = a.get("globals") or {}
a_obs = {
    "run_id": a.get("run_id"),
    "started": a.get("started"),
    "folder_on_disk": a.get("folder_renamed_to"),
    "ini_mods_line": (a.get("folder_check") or {}).get("ini_mods_line")
    or a.get("ini_mods_before_start"),
    "listing": (a.get("folder_check") or {}).get("listing") or a.get("listing_after_rename"),
    "mods_not_found": a.get("mods_not_found"),
    "loading_requested": {"count": (grep_a.get("loading_requested") or {}).get("count"),
                          "hits": (grep_a.get("loading_requested") or {}).get("hits")},
    "missing_requested": {"count": (grep_a.get("missing_requested") or {}).get("count"),
                          "hits": (grep_a.get("missing_requested") or {}).get("hits")},
    "loading_common_id": {"count": (grep_a.get("loading_common") or {}).get("count"),
                          "hits": (grep_a.get("loading_common") or {}).get("hits")},
    "loader_wide_count": (grep_a.get("loader_wide") or {}).get("count"),
    "drift_wide_count": (grep_a.get("drift_wide") or {}).get("count"),
    "drift_wide_hits": (grep_a.get("drift_wide") or {}).get("hits"),
    "media_trees_walked": a.get("media_trees_walked"),
    "overrides": (grep_a.get("overrides_wide") or {}).get("tails"),
    "overrides_by_the_probe": [t for t in ((grep_a.get("overrides_wide") or {}).get("tails") or [])
                               if t.get("mod") not in ("PZTestKit", "TKX_CommonOnly")],
    "ping": a.get("ping"),
    "TK.version": val_of(a_globals, "TK.version"),
    "TKX_LoaderWhich": val_of(a_globals, "TKX_LoaderWhich"),
    "TKX_LoaderCommonTree": res_of(a_globals, "TKX_LoaderCommonTree"),
    "TKX_LoaderVersionTree": res_of(a_globals, "TKX_LoaderVersionTree"),
    "TKX_CommonOnly.version": val_of(a_globals, "TKX_CommonOnly.version"),
    "echo_ok": a.get("echo_ok"),
    "found_state": a.get("found_state"),
    "corroboration": {"bus_alive": bus_alive(a), "probe_globals_ran": probe_ran(a)},
}
a_found = a.get("found_state")
if not a.get("started"):
    a_verdict = "unmeasured"
elif a_found is True:
    # The engine announced a load. The mod's own Lua should corroborate it -- but only if the bus
    # answered at all: a dead bus makes the corroboration UNAVAILABLE, not negative, and the log
    # evidence then stands alone (and says so in `corroboration`).
    a_verdict = "as_predicted" if (probe_ran(a) or not bus_alive(a)) else "falsified"
else:
    a_verdict = "falsified"                        # False, or a MIXED reading -- both are findings
out["phases"]["P16"] = {
    "question": "does a mod whose installed folder name differs from the id in Mods= still load?",
    "boot": "drift",
    "reading": a_obs,
    "closes": "docs/testing/profiles.md Open questions 6, second half -- C and explicitly an "
              "inference since slice 09, because td1-20260910-192457 recorded "
              "source_folder_present: false, i.e. no run had produced the counterfactual. Either "
              "answer closes it M.",
    "both_answers_are_findings": "an `as_predicted` says the loader resolves through mod.info and "
                                 "harness.install's rename is a CONVENIENCE; a `falsified` says "
                                 "the rename is REQUIRED and profiles.md closes the other way. "
                                 "Neither is the good news and neither is the bad.",
    "mixed_reading_rule": "found_state is None when the engine's announcements disagree with what "
                          "actually ran (a `loading` line beside a `not found` line, or neither). "
                          "That is graded `falsified` -- the prediction was a clean load -- and "
                          "flagged, never flattened into a tidy True or False.",
    "corroboration": "the two tree markers say whether BOTH media trees of the RENAMED folder "
                     "ran, and media_trees_walked quotes the engine's own file-walk paths under "
                     "that name. TKX_CommonOnly.version is the within-boot control: it is "
                     "installed under its own id and is not manipulated in either boot.",
}
grade("P16",
      "the mod still loads: `loading TKX_LoaderVersion` on the server, NO "
      "`required mod \"TKX_LoaderVersion\" not found`, an empty mods_not_found, and the probe's "
      "globals resolving -- i.e. the loader resolves through mod.info, consistent with the 52 "
      "installed workshop folders that drift from their declared id and load in normal play, and "
      "harness.install's rename to <mods_dir>/<mod id> is a convenience.",
      a_obs, a_verdict,
      "`required mod \"TKX_LoaderVersion\" not found` with no `loading` line: the rename is "
      "REQUIRED, the loader keys on the DIRECTORY name, and profiles.md OQ 6 closes the other "
      "way -- an equally citable M and the more surprising of the two.",
      {"grading_rule": "found_state is read off the ENGINE'S two announcements alone. "
                       "as_predicted = found (and, when the bus answered, corroborated by the "
                       "probe's own globals); falsified = not found, a MIXED reading, or a load "
                       "the running Lua contradicts; unmeasured = the boot never started."})

# ================= P17: boot (b) read =========================================================
grep_b = bb.get("greps") or {}
b_globals = bb.get("globals") or {}
# Read off the WIDE grep and subtracted rather than matched: "the probe's overrides line" is
# every such line NOT printed by the two mods this boot did not touch. Filtering for a name that
# starts with `TKX_Loader` would have assumed the answer to clause 3 -- a loader printing the
# FOLDER name (`TKX_DriftedFolder2`) would have vanished from the reading instead of falsifying it.
over_tails = (grep_b.get("overrides_wide") or {}).get("tails") or []
probe_tails = [t for t in over_tails if t.get("mod") not in ("PZTestKit", "TKX_CommonOnly")]
over_ids = sorted({t["mod"] for t in probe_tails})
over_paths = [t["tail"].lower() for t in probe_tails if t.get("tail")]
b_found = bb.get("found_state")
b_which = val_of(b_globals, "TKX_LoaderWhich")
b_trees = (res_of(b_globals, "TKX_LoaderCommonTree") is True
           and res_of(b_globals, "TKX_LoaderVersionTree") is True)
b_parts = {
    "loads_under_common_id": b_found,
    "which_still_version": (b_which == "version") if b_which is not None else None,
    "both_trees_ran": b_trees if b_found else None,
    "overrides_printed_under_requested_id": (over_ids == [COMMON_ID]) if over_ids else
    (False if b_found else None),
    "overrides_tail_unchanged": (over_paths == [WHICH_REL]) if over_paths else None,
}
b_obs = {
    "run_id": bb.get("run_id"),
    "started": bb.get("started"),
    "folder_on_disk": bb.get("folder_renamed_to"),
    "ini_mods_as_seeded": bb.get("ini_mods_as_seeded"),
    "ini_mods_line": (bb.get("folder_check") or {}).get("ini_mods_line")
    or bb.get("ini_mods_before_start"),
    "listing": (bb.get("folder_check") or {}).get("listing") or bb.get("listing_after_rename"),
    "mods_not_found": bb.get("mods_not_found"),
    "loading_requested": {"count": (grep_b.get("loading_requested") or {}).get("count"),
                          "hits": (grep_b.get("loading_requested") or {}).get("hits")},
    "missing_requested": {"count": (grep_b.get("missing_requested") or {}).get("count"),
                          "hits": (grep_b.get("missing_requested") or {}).get("hits")},
    "loading_version_id": {"count": (grep_b.get("loading_version") or {}).get("count"),
                           "hits": (grep_b.get("loading_version") or {}).get("hits")},
    "loader_wide_count": (grep_b.get("loader_wide") or {}).get("count"),
    "drift_wide_count": (grep_b.get("drift_wide") or {}).get("count"),
    "drift_wide_hits": (grep_b.get("drift_wide") or {}).get("hits"),
    "media_trees_walked": bb.get("media_trees_walked"),
    "overrides": over_tails,
    "overrides_by_the_probe": probe_tails,
    "overrides_ids": over_ids,
    "ping": bb.get("ping"),
    "TK.version": val_of(b_globals, "TK.version"),
    "TKX_LoaderWhich": b_which,
    "TKX_LoaderCommonTree": res_of(b_globals, "TKX_LoaderCommonTree"),
    "TKX_LoaderVersionTree": res_of(b_globals, "TKX_LoaderVersionTree"),
    "TKX_CommonOnly.version": val_of(b_globals, "TKX_CommonOnly.version"),
    "echo_ok": bb.get("echo_ok"),
    "found_state": b_found,
    "parts": b_parts,
    "corroboration": {"bus_alive": bus_alive(bb), "probe_globals_ran": probe_ran(bb)},
}
if not bb.get("started"):
    b_verdict = "unmeasured"
elif a_found is False and b_found is False:
    # Amendment 8's fourth row: with (a) not found, (b)'s not-found is already explained by its
    # own rename and says NOTHING about ids. Grading it `falsified` would be reading a fact about
    # folder-name lookup as a fact about id registration.
    b_verdict = "unmeasured"
elif b_found is True and not bus_alive(bb):
    # The load half held, but clauses 2 and 3 are read off the bus and the bus did not answer.
    # Unreadable is not falsified.
    b_verdict = "unmeasured"
elif b_found is True and b_parts["which_still_version"] and b_parts["both_trees_ran"] \
        and b_parts["overrides_printed_under_requested_id"] is not False:
    b_verdict = "as_predicted"
else:
    b_verdict = "falsified"
out["phases"]["P17"] = {
    "question": "is the id in common/mod.info registered and addressable -- does Mods= naming "
                "TKX_LoaderCommon load the same folder?",
    "boot": "common_id",
    "reading": b_obs,
    "closes": "docs/testing/profiles.md Open questions 1 for the dedicated-server path: the three "
              "models (mod_lint.info_chain / pzt.mods.mod_id_of, getModVersionDirName, and "
              "searchForModInfo) have been unreconciled since slice 11, whose subject (AutoCook) "
              "ships exactly ONE mod.info and could not discriminate.",
    "three_clauses": "P17 is not one claim. (1) the mod LOADS under the common id -- "
                     "searchForModInfo registers every mod.info it meets into modIdToDir and "
                     "returns the first whose id MATCHES the request. (2) TKX_LoaderWhich still "
                     "reads \"version\" -- the media mapping is by FOLDER, not by which mod.info "
                     "answered, so which id was asked for must not change which Lua won the "
                     "collision. (3) the loader's `overrides` line prints under the id the engine "
                     "was ASKED for. They are graded separately in `parts` so a reader can see "
                     "which clause broke rather than only that something did.",
    "why_the_folder_is_renamed_too": "harness.install copies the profile source to "
                                     "mods/TKX_LoaderVersion, so a boot that only edited Mods= "
                                     "would leave the folder named one of the two ids and a "
                                     "`found` could not be told from folder-name lookup. The "
                                     "rename to a name matching NEITHER id is what makes this "
                                     "boot separate cleanly from boot (a).",
    "uninformative_rule": "if boot (a) was NOT found, this boot is UNINFORMATIVE about ids -- its "
                          "not-found is already explained by its own rename -- and is graded "
                          "`unmeasured`, never `falsified`.",
}
grade("P17",
      "the mod loads under the common/mod.info id too -- `loading TKX_LoaderCommon`, no "
      "`required mod \"TKX_LoaderCommon\" not found` -- and because the media mapping is by "
      "FOLDER, TKX_LoaderWhich still reads \"version\" with both tree markers resolving and the "
      f"`overrides` line still prints under the id the engine was asked for, tail `{WHICH_REL}`.",
      b_obs, b_verdict,
      "`required mod \"TKX_LoaderCommon\" not found` falsifies it and vindicates mod_lint's "
      "\"version folder first\" model: only ONE id per folder is registered. A load whose "
      "TKX_LoaderWhich flipped to \"common\" falsifies the second clause instead -- the media "
      "mapping would then follow the mod.info that answered, not the folder.",
      {"parts": b_parts,
       "grading_rule": "as_predicted needs all three clauses. `unmeasured` when the boot did not "
                       "start, when boot (a) was not found either (amendment 8's fourth row, "
                       "where this boot's not-found is already explained by its own rename), or "
                       "when the mod loaded but the bus never answered and clauses 2 and 3 are "
                       "therefore unreadable rather than false."})

# ================= the two boots read together ================================================
joint_key = (a_found, b_found)
out["joint"] = {
    "a_found": a_found,
    "b_found": b_found,
    "meaning": JOINT.get(joint_key,
                         "INCONCLUSIVE: at least one boot did not produce a clean found/not-found "
                         "reading (a mixed or unmeasured state), so the matrix stated in advance "
                         "does not apply. The per-boot rows stand on their own; the joint claim "
                         "does not."),
    "matrix_stated_in_advance": out["joint_matrix_stated_in_advance"],
    "how_to_read": "the four combinations are the point: each boot alone is ambiguous. The row a "
                   "careless reader gets wrong is (False, False) -- if (a) was not found, (b)'s "
                   "not-found is already explained by its own rename and is NOT evidence against "
                   "P17.",
}
tl.mark("joint", a_found=str(a_found), b_found=str(b_found))

out["summary"] = {
    "run_ids": {"drift": a.get("run_id"), "common_id": bb.get("run_id")},
    "started": {"drift": a.get("started"), "common_id": bb.get("started")},
    "skipped": {"drift": a.get("skipped"), "common_id": bb.get("skipped")},
    "errors": {"drift": a.get("error"), "common_id": bb.get("error")},
    "fatal": {"drift": a.get("fatal"), "common_id": bb.get("fatal")},
    "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    "found_state": {"drift": a_found, "common_id": b_found},
    "joint": out["joint"]["meaning"],
    "listings": {"drift": (a.get("folder_check") or {}).get("listing"),
                 "common_id": (bb.get("folder_check") or {}).get("listing")},
    "ini_mods_lines": {"drift": a_obs["ini_mods_line"], "common_id": b_obs["ini_mods_line"]},
    "mods_not_found": {"drift": a.get("mods_not_found"), "common_id": bb.get("mods_not_found")},
    "loading_requested": {"drift": a_obs["loading_requested"]["count"],
                          "common_id": b_obs["loading_requested"]["count"]},
    "missing_requested": {"drift": a_obs["missing_requested"]["count"],
                          "common_id": b_obs["missing_requested"]["count"]},
    "TKX_LoaderWhich": {"drift": a_obs["TKX_LoaderWhich"], "common_id": b_obs["TKX_LoaderWhich"]},
    "trees_resolved": {
        "drift": {"common": a_obs["TKX_LoaderCommonTree"],
                  "version": a_obs["TKX_LoaderVersionTree"]},
        "common_id": {"common": b_obs["TKX_LoaderCommonTree"],
                      "version": b_obs["TKX_LoaderVersionTree"]}},
    "TK_version": {"drift": a_obs["TK.version"], "common_id": b_obs["TK.version"]},
    "TKX_CommonOnly_version": {"drift": a_obs["TKX_CommonOnly.version"],
                               "common_id": b_obs["TKX_CommonOnly.version"]},
    "overrides_ids": {"drift": sorted({t["mod"] for t in
                                       ((grep_a.get("overrides_wide") or {}).get("tails") or [])
                                       if t.get("mod") not in ("PZTestKit", "TKX_CommonOnly")}),
                      "common_id": over_ids},
    "echo_ok": {"drift": a.get("echo_ok"), "common_id": bb.get("echo_ok")},
    "server_error_count": {"drift": a.get("server_error_count"),
                           "common_id": bb.get("server_error_count")},
    "lua_error_hits": {"drift": (grep_a.get("lua_errors") or {}).get("count"),
                       "common_id": (grep_b.get("lua_errors") or {}).get("count")},
    "wall_seconds": {
        "drift": round((a.get("wall_end") or 0) - (a.get("wall_start") or 0), 1),
        "common_id": round((bb.get("wall_end") or 0) - (bb.get("wall_start") or 0), 1)},
}
out["wall_seconds"] = round(time.time() - t0, 1)
# `server_errors` at the top level belongs to the LAST server `save` saw; the per-boot
# `server_errors` / `server_error_count` rows are the authoritative ones.
out["server_errors_note"] = ("the top-level server_errors key is whichever server was current at "
                             "the last save (boot b's). Per-boot server_errors is authoritative.")
publish()

print(json.dumps({"summary": out.get("summary")}, indent=1)[:7000])
