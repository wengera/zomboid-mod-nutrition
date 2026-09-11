"""Slice 12, session 2 (`x122`): the loader session -- LIVE.

**What is under test is the LOADER, not a mod.** Sessions before this one asked what a mod's
Lua did once it ran; this one asks which physical bytes the engine chose to run in the first
place, for a mod laid out the way half the workshop lays mods out -- a `common/` tree and a
version tree, both carrying `media/`. Slice 11 could only ask that question of a mod somebody
else shipped (`AutoCook`, whose two copies of `AutoCook.lua` differ by two functions); the two
subjects here were built in Task 1 to answer it by construction:

  D  `tkx-loader-probe`, installed as `TKX_LoaderVersion`. TWO `mod.info` files with DIFFERENT
     ids -- `common/mod.info` says `id=TKX_LoaderCommon`, `42.20/mod.info` says
     `id=TKX_LoaderVersion` -- and THREE Lua files across the two trees:
       * `common/.../TKX_Loader_Common.lua`  -> `TKX_LoaderCommonTree = 1`   (unique to common/)
       * `42.20/.../TKX_Loader_Version.lua`  -> `TKX_LoaderVersionTree = 1`  (unique to 42.20/)
       * `.../TKX_Loader_Which.lua`          -> `TKX_LoaderWhich = "common"` / `"version"`
         (the SAME relative path in BOTH trees -- the collision)
     The two unique globals and the one colliding global are three independent readings, and
     that is the whole point: `TKX_LoaderWhich` alone cannot tell "common/ lost the collision"
     from "common/ never ran at all". The pair of unique globals is what separates them.
  E  `TKX_CommonOnly`. A version dir (`42.20/`) holding a `mod.info` and NOTHING else -- no
     `media/` -- with the mod's entire payload (`TKX_CommonOnly = { version = 1 }`) under
     `common/`. Does an empty version dir suppress `common/`, or cost the mod nothing?

Four readings (the plan's L1-L4; the controller's amendments 3-5 govern how they are graded):

  L1  the id read. Which id does the engine ANNOUNCE for mod D -- the one it was asked for, or
      the one in the `mod.info` it happened to read first? **Amendment 3 is explicit that this
      is weak here and it is graded honestly:** `searchForModInfo` returns the first `mod.info`
      whose id MATCHES the request, so with `Mods=TKX_LoaderVersion` the mod loads under either
      read order and P12 holds TRIVIALLY. The discriminating boot -- asking for the `common/`
      id -- is Task 6's second boot, not this one. So L1 grades `trivial` when the log holds
      nothing but the expected lines, and the only thing that lifts it off `trivial` is the log
      itself: a `loading TKX_LoaderCommon` line (falsifier), or some OTHER line naming
      `TKX_LoaderCommon` (which would be positive evidence for P12's second half -- that the
      common id is registered into `modIdToDir` on the way past). Hence the WIDE grep for the
      bare id on both logs, and every hit recorded with its line number.

  L2  **the reading that matters** (amendment 4). Two halves that have to agree:
        a) the loader's own `mod "TKX_LoaderVersion" overrides <rel>` line -- one server-side,
           two on the client console (one per Lua state), tail
           `media/lua/shared/tkx_loader_which.lua`, lower-cased the way the loader prints
           relative paths, so it is matched CASE-INSENSITIVELY;
        b) `lua.global TKX_LoaderWhich` on BOTH sides -- and, beside it,
           `TKX_LoaderCommonTree` and `TKX_LoaderVersionTree`, which must BOTH resolve. Both
           resolving is what makes a `"version"` answer mean "the version tree won a collision
           the common tree was present for" instead of "the common tree was never there".

  L3  the empty-version-dir arm. `lua.global TKX_CommonOnly.version` on both sides. P15:
      resolves -- pass A maps `common/media` into `activeFileMap` and pass B adds nothing, so a
      version dir that ships only a `mod.info` costs the mod nothing. A `resolved: false` is the
      OPPOSITE finding and equally citable; it is deliberately not a `[[verify]]` gate, because
      a measurement must never be a gate. Amendment 9's arm is wired in too: if the engine
      answers `required mod "TKX_CommonOnly" not found`, `check_mods_loaded` raises, and THAT
      RAISE IS THE READING -- it is caught here, recorded under `l3`, and the session continues
      for L1/L2/L4. Any OTHER missing mod re-raises: that is a broken profile, not a finding.

  L4  the control. `lua.global TK.version` -> `1` on both sides. `TK` is a global on purpose
      (`PZTestKit_Core.lua:2`), so a `resolved: false` here says the `_G` walk is broken rather
      than that a mod global is absent -- which is why it is SENT FIRST, before any reading that
      could be read as an absence, even though the plan lists it last.

**Why every bus read is wall-bracketed and the CLIENT is read first** (`docs/decisions.md:158`):
the two sides of a reading are separate bus round trips ~0.5 s apart. Nothing measured here
decays -- these are load-time globals -- but the bracket is kept because a driver that drops it
on the run where it does not matter is a driver that has dropped it.

**`witness.fields`' `count` reconciliation has no analogue on `lua.global`, so this driver
checks the reply's own echo instead** (amendment 6's spirit: every reply CHECKED, not merely
recorded): every `lua.global` answer must echo back the `name` that was asked for and the `side`
it was asked on. A reply that names a different global is a bus crossing, and a reading taken
from a crossed reply is worth nothing.

**World changes: none.** This driver sends `lua.global` and nothing else -- no RCON, no
`moddata.set`, no sandbox write, no `settimespeed`. There is nothing to restore.

**`lua.reload` is NEVER sent**, and here that is not a precaution but the experiment's own
integrity: re-executing the mod's files would run BOTH copies of `TKX_Loader_Which.lua` again in
whatever order the reloader walks them and overwrite the very global L2 reads. The load-order
reading exists only in the state the boot left behind.

Never raises through teardown; the artifact is written before and after teardown and copied
byte-for-byte into `testing/artifacts/<run-id>/`.
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
from pzt.server import MOD_MISSING_RX                                         # noqa: E402
from pzt.session import (Timeline, check_mods_loaded, make_client,            # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x12-loader"
USER = "admin"
MODS = ("PZTestKit", "TKX_LoaderVersion", "TKX_CommonOnly")
# Step 1's acceptance run: RESULT PASS, the one [[verify]] row ok=True (client `lua.global
# TKX_LoaderVersionTree` -> resolved true, value 1), `faults: []`, 0 server error lines. It is
# also where the grep limits below were sized: it printed ONE `loading TKX_LoaderVersion`, ONE
# `mod "TKX_LoaderVersion" overrides …tkx_loader_which.lua` and ONE `loading TKX_CommonOnly` on
# the server, each twice on the client console, and -- the reading amendment 9 was hedging
# against -- NO `required mod "TKX_CommonOnly" not found`.
ACCEPTANCE_RUN = "run-20260911-031417"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
# The two subjects are OURS, so "which commit are these bytes" is a provenance question about
# them exactly as it is about the harness Lua -- a probe edited but not committed would make the
# artifact cite a tree that is not the tree that ran.
SUBJECT_DIRS = {"TKX_LoaderVersion": "testing/experiments/tkx-loader-probe",
                "TKX_CommonOnly": "testing/experiments/TKX_CommonOnly"}

# ---- the greps ------------------------------------------------------------------------------
# `grep_numbered` takes a COMPILED regex and the escaping is the caller's job (pass-2 lesson,
# session.py:51). **A limit is a BREAK, not a window** (docs/testing/README.md § Observation): a
# result of exactly `limit` is SATURATION, never a census, so every limit below is >= 2x the
# acceptance run's count with headroom on top, and the client's is larger again because a client
# console runs two Lua states and prints engine load output once per state.
LOAD_VERSION_RX = re.compile(re.escape("loading TKX_LoaderVersion"))
LOAD_COMMON_RX = re.compile(re.escape("loading TKX_LoaderCommon"))
# Amendment 3: "grep the server log for TKX_LoaderCommon with a wide limit and record every
# hit". Widened once more to the shared prefix so a scan line naming EITHER id is caught, and
# case-insensitively so a lower-cased path mention cannot hide from it.
LOADER_WIDE_RX = re.compile(r"TKX_Loader", re.IGNORECASE)
# The same wide read for mod E. Not asked for by any amendment, and it earns its place: the
# acceptance run's logs carry `NoSuchFileException … mods\TKX_CommonOnly\42.20\media\AnimSets`
# beside the `…\common\media\…` one, i.e. the engine ENUMERATING both trees' media folders. That
# is the closest thing to a direct observation of the two-pass walk that a log can give, and it
# is L3's supporting evidence: the version dir with no media/ was visited and found empty.
COMMONONLY_WIDE_RX = re.compile(r"TKX_CommonOnly", re.IGNORECASE)
# `…mods\<mod id>\<tree>\media…` out of such a line, either slash flavour.
TREE_WALK_RX = re.compile(r"mods[\\/](TKX_[A-Za-z_]+)[\\/]([^\\/]+)[\\/]media", re.IGNORECASE)
OVERRIDE_VERSION_RX = re.compile(re.escape('mod "TKX_LoaderVersion" overrides'))
# Every TKX `overrides` line, whichever mod printed it: TKX_CommonOnly printing one at all is
# part of L3's evidence, and x121 (`x121-20260911-030023`, greps.overrides) recorded an
# EMPTY-TAIL `mod "TKX_ItemOverride" overrides ` line beside its real one, so a tail-less line is
# a known shape of this print and must be counted separately rather than mistaken for a reading.
OVERRIDE_ANY_RX = re.compile(r'mod "TKX_[A-Za-z_]+" overrides')
LOADING_ANY_RX = re.compile(r"loading TKX_")
NILCALL_RX = re.compile(r"tried to call nil|stack traceback|attempted to index")
# `mod "<id>" overrides <tail>`; the tail may be EMPTY (see above), which is why the group is
# `.*` and not `\S+` -- an empty tail must parse to "" and be recorded, not fail to match.
TAIL_RX = re.compile(r'mod "(TKX_[A-Za-z_]+)" overrides ?(.*)$')

GREPS = (
    # name,              regex,                srv limit, cli limit
    ("loading_version",  LOAD_VERSION_RX,      6,  12),   # plan's L1 limits, verbatim
    ("loading_common",   LOAD_COMMON_RX,       6,  12),   # plan's L1 limits, verbatim
    ("loader_wide",      LOADER_WIDE_RX,      40,  60),   # amendment 3's wide read
    ("commononly_wide",  COMMONONLY_WIDE_RX,  40,  60),   # the same, for mod E (L3's evidence)
    ("overrides_version", OVERRIDE_VERSION_RX, 6,  12),   # amendment 4: limit >= 2x1 + headroom
    ("overrides_any",    OVERRIDE_ANY_RX,     20,  40),
    ("loading_any",      LOADING_ANY_RX,      12,  24),
    ("lua_errors",       NILCALL_RX,          12,  12),
    ("mod_missing",      MOD_MISSING_RX,      10,  10),   # amendment 9's line, verbatim if it fires
)

# The tail the loader is predicted to print, LOWER-CASED the way it prints relative paths
# (`td3-20260911-001948`: `media/lua/client/autocook.lua` for a file shipped as `AutoCook.lua`).
# Compared case-insensitively -- the case is the loader's business, the path is the reading.
WHICH_REL = "media/lua/shared/tkx_loader_which.lua"

# ---- the globals, why each one is asked for, and which tree defines it -----------------------
# Read CLIENT FIRST at every name, and `TK.version` first of all (amendment 5: the control has to
# pass before any `resolved: false` below is read as a finding rather than as a broken walk).
GLOBALS = (
    ("TK.version", "L4", "control",
     "TK is a global on purpose (PZTestKit_Core.lua:2). MUST be 1 on BOTH sides: a "
     "resolved=false here says the _G walk is broken, not that a mod global is absent."),
    ("TKX_LoaderWhich", "L2", "BOTH trees (the collision)",
     "media/lua/shared/TKX_Loader_Which.lua exists in common/ AND 42.20/; the copy that ran "
     "last owns the global. 'version' = the version tree won, 'common' = it lost. Meaningless "
     "on its own -- it is only a collision reading if both unique globals below resolve."),
    ("TKX_LoaderCommonTree", "L2", "common/ only",
     "common/.../TKX_Loader_Common.lua:4. No file of that relative path exists under 42.20/, so "
     "nothing can override it: absent => the common/ tree never ran AT ALL, which is a "
     "different fact from 'common/ lost the collision'."),
    ("TKX_LoaderVersionTree", "L2", "42.20/ only",
     "42.20/.../TKX_Loader_Version.lua:4, the mirror of the above. It is also the profile's one "
     "[[verify]] row -- a gate precisely BECAUSE it loads under either merge direction and so "
     "discriminates nothing."),
    ("TKX_CommonOnly", "L3", "mod E, common/ only",
     "the table itself, so keyCount separates 'the global is a table with something in it' from "
     "'the dotted read found a leaf on an empty table'."),
    ("TKX_CommonOnly.version", "L3", "mod E, common/ only",
     "common/.../TKX_CommonOnly.lua:4 -- the whole payload of a mod whose 42.20/ folder holds a "
     "mod.info and no media/ at all. THE L3 reading."),
)

# The dormant `sent` branch's routing table (slice-11 driver note). This driver sends ONLY
# `lua.global`, which answers INLINE, so the branch can never fire; the map is left EMPTY on
# purpose, which makes `probe` record any such ack raw instead of blocking on a result doc that
# would never be written.
RESULT_DOC = {}

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x122")
path = os.path.join(run_dir, "platform-loader.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)


def tree_census(src):
    """Every file under a subject's source folder, as a sorted list of forward-slashed relative
    paths. The artifact has to be readable without the repo beside it, and "which files were in
    which tree" is the premise of every prediction here -- a reader who cannot see the layout
    cannot check the reasoning."""
    try:
        out_ = []
        for root, _dirs, files in os.walk(src):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), src)
                out_.append(rel.replace("\\", "/"))
        return sorted(out_)
    except OSError as e:                          # noqa: BLE001 - provenance, never fatal
        return [f"{type(e).__name__}: {e}"]


out = {
    "run_id": run_id,
    "session": "x122 -- slice 12 session 2: the loader session (common/ vs version dir)",
    "user": USER,
    "profile": prof.report(),
    "mods": list(MODS),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "subjects": {
        mid: {"source": rel,
              "commit": git_say("log", "-1", "--format=%h", "--", rel),
              "dirty": git_dirty(rel)[0], "dirty_note": git_dirty(rel)[1],
              "files": tree_census(os.path.join(REPO, rel.replace("/", os.sep)))}
        for mid, rel in SUBJECT_DIRS.items()
    },
    "installed_as_note": (
        "harness.install copies a profile source folder to mods/<mod id> (harness.py:29-31), so "
        "on disk BOTH probes sit in a folder named exactly the id the server asks for -- "
        "mods/TKX_LoaderVersion and mods/TKX_CommonOnly. Mod D's own mod.info description says "
        "'folder name matches neither id', and that is true of the SOURCE folder "
        "(tkx-loader-probe) and NOT of the installed one. Nothing here rests on the folder name "
        "-- D's discriminator is the two mod.info ids inside it -- but a later reader comparing "
        "this artifact against a workshop mod, where the folder name is a numeric item id, must "
        "know which of the two names the engine saw."),
    "reading_order": (
        "L4's control global is sent FIRST (amendment 5), then L2's three, then L3's two; the "
        "greps are file reads taken before any of them and cost no bus time. The grading below "
        "is written in the plan's L1..L4 order regardless of when each read was taken."),
    "world_changes": {
        "restored": "nothing -- this driver writes no world state at all.",
        "left_in_place": [],
        "why": "the only bus command sent is `lua.global`, which READS _G and never calls what "
               "it finds (PZTestKit_Core.lua:782-784). No RCON, no moddata.set, no sandbox "
               "write, no settimespeed.",
        "lua_reload": "NEVER sent -- and here that is the experiment's integrity, not a "
                      "precaution: reloading would re-execute BOTH copies of "
                      "TKX_Loader_Which.lua in the reloader's own order and overwrite the very "
                      "global L2 reads. The load-order reading exists only in the state the "
                      "boot left behind.",
    },
    "steps": [], "notes": [], "phases": {}, "verdicts": {},
}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). `lua.global` answers INLINE, so it is DORMANT here
        and `RESULT_DOC` is empty: an ack in that shape is recorded raw rather than blocked on.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A
        string where a table belongs is re-asked ONCE and BOTH readings are kept.
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
    save(path, out, tl, server)


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


def tails_of(hits):
    """The `<rel>` half of every `mod "<id>" overrides <rel>` hit, with its line number and the
    mod that printed it. An EMPTY tail is a real shape of this print (x121) and is kept as `""`
    rather than dropped -- a reading that silently discarded it would miscount."""
    out_ = []
    for h in hits:
        m = TAIL_RX.search(h.get("text", "")) if isinstance(h, dict) else None
        if m:
            out_.append({"line": h["line"], "mod": m.group(1), "tail": m.group(2).strip()})
    return out_


def tree_walk_of(grep_row, mod_id):
    """Which TREES of `mod_id` the engine was seen touching, from the
    `…mods\\<id>\\<tree>\\media…` paths its own file-walk exceptions quote. `{"42.20", "common"}` on both sides is a direct
    observation that BOTH media trees were enumerated -- the two-pass walk, in the engine's own
    words rather than inferred from which global survived."""
    seen = {}
    for side in ("server", "client"):
        trees = set()
        for h in grep_row[side]["hits"]:
            if not isinstance(h, dict):
                continue
            for m in TREE_WALK_RX.finditer(h.get("text", "")):
                if m.group(1).lower() == mod_id.lower():
                    trees.add(m.group(2))
        seen[side] = sorted(trees)
    return seen


def side_grep(name, rx, srv_limit, cli_limit, client):
    """One regex over BOTH logs, with the saturation test written down rather than left to the
    reader, and the per-side limits kept separate: the client console prints engine load output
    once per Lua state, so its expected count is 2x the server's and its limit has to be too."""
    s = grep_numbered(server.log_path, rx, srv_limit)
    k = grep_numbered(client.console, rx, cli_limit)
    row = {"name": name, "pattern": rx.pattern,
           "server": {"limit": srv_limit, "count": len(s), "saturated": len(s) >= srv_limit,
                      "hits": s},
           "client": {"limit": cli_limit, "count": len(k), "saturated": len(k) >= cli_limit,
                      "hits": k}}
    if name.startswith("overrides"):
        row["server"]["tails"] = tails_of(s)
        row["client"]["tails"] = tails_of(k)
    return row


ECHO_CHECKS = []


def read_global(side, side_name, name):
    """One `lua.global`, with its reply CHECKED and not merely recorded.

    `witness.fields` has a `count` to reconcile against the names sent; `lua.global` has no such
    field, so the integrity check here is the reply's own echo: it must name the global that was
    asked for and the side it was asked on. A reply that names a different global is a bus
    crossing, and a reading taken from a crossed reply is worth nothing -- so the check travels
    with every row and is summarised at the end, exactly as the field counts are."""
    r = probe(side, "lua.global", name)
    d = r if isinstance(r, dict) else {}
    echo_ok = d.get("name") == name and d.get("side") == side_name
    row = {"side": side_name, "name": name,
           "resolved": d.get("resolved"), "type": d.get("type"), "value": d.get("value"),
           "keyCount": d.get("keyCount"), "failedAt": d.get("failedAt"),
           "stoppedOn": d.get("stoppedOn"),
           "echo_name": d.get("name"), "echo_side": d.get("side"), "echo_ok": echo_ok,
           "error": d.get("error") if isinstance(r, dict) else r,
           "wall": (d.get("_probe") or {}).get("wall"),
           "reply": r}
    ECHO_CHECKS.append({"name": name, "side": side_name, "echo_ok": echo_ok,
                        "echo_name": d.get("name"), "echo_side": d.get("side")})
    return row


def both_globals(client, name):
    """CLIENT FIRST, then the server -- the read order is what fixes the sign of any cross-side
    comparison, so it is never left to chance even where nothing can decay between the two."""
    return {"client": read_global(client, "client", name),
            "server": read_global(server, "server", name)}


def val_of(pair, side):
    return (pair.get(side) or {}).get("value")


def res_of(pair, side):
    return (pair.get(side) or {}).get("resolved")


def both_resolved(pair):
    """True only when BOTH sides answered `resolved: true`. `resolved` is a tri-state in
    practice -- True, False, or None when the read itself errored -- so this is an identity test
    against True and never a truthiness test."""
    return res_of(pair, "client") is True and res_of(pair, "server") is True


try:
    server.start()

    # Amendment 9, wired in as an ARM rather than a hope. `check_mods_loaded` raises the moment
    # the server says a mod is missing; for TKX_CommonOnly that raise IS L3's reading (a version
    # dir holding only a mod.info is NOT accepted), so it is caught, recorded verbatim and the
    # session continues. Any OTHER missing mod re-raises: that is a broken profile, not a
    # finding, and a session booted without the mod under test is not evidence.
    mods_check = {"raised": False, "missing": [], "log_lines": []}
    try:
        check_mods_loaded(tl, server)
    except RuntimeError as e:
        mods_check = {"raised": True, "error": str(e),
                      "missing": sorted(set(server.mods_not_found)),
                      "log_lines": grep_numbered(server.log_path, MOD_MISSING_RX, 10)}
        unexpected = set(mods_check["missing"]) - {"TKX_CommonOnly"}
        note(f"check_mods_loaded raised: {mods_check['error']}")
        if unexpected:
            out["mods_loaded_check"] = mods_check
            raise
        note("the missing set is exactly {TKX_CommonOnly} -- amendment 9's arm: that FAIL is "
             "L3's reading, not a profile defect. Continuing for L1/L2/L4.")
    out["mods_loaded_check"] = mods_check

    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact. `pzt run`
    # checks this and the artifact never recorded it, so "no mod failed to load" was unsayable.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ================= the loader's own lines, from FILES ================================
    # Taken before any bus read: they cost no bus time and cannot delay a reading.
    out["greps"] = {name: side_grep(name, rx, sl, cl, c) for name, rx, sl, cl in GREPS}
    tl.mark("greps",
            loading_version=out["greps"]["loading_version"]["server"]["count"],
            loading_common=out["greps"]["loading_common"]["server"]["count"],
            overrides=out["greps"]["overrides_version"]["server"]["count"])

    # ================= the globals, control first ========================================
    globals_read = {}
    for name, reading, tree, why in GLOBALS:
        globals_read[name] = both_globals(c, name)
        globals_read[name]["reading"] = reading
        globals_read[name]["tree"] = tree
        globals_read[name]["why"] = why
        save(path, out, tl, server)
    out["globals"] = globals_read
    tl.mark("globals", read=len(globals_read))

    # ================= L1 -- the id read =================================================
    lv, lc = out["greps"]["loading_version"], out["greps"]["loading_common"]
    wide = out["greps"]["loader_wide"]
    # Every wide hit that is NOT one of the two expected shapes for the VERSION id -- i.e. every
    # line that mentions the mod outside `loading TKX_LoaderVersion` / the `overrides` line. The
    # common id showing up in one of them is what would lift L1 off `trivial`.
    # `PZTK:` lines are the HARNESS echoing a bus command back into the console, not the engine
    # speaking. They are excluded so that a `lua.global TKX_LoaderCommon…` read of our own can
    # never be counted as the engine naming the id. Nothing here reads that global and the greps
    # are taken before every bus read anyway, so this guard is belt-and-braces -- but a grader
    # that can be fooled by its own traffic is not a grader.
    common_mentions = {
        side: [h for h in wide[side]["hits"]
               if isinstance(h, dict) and "tkx_loadercommon" in h.get("text", "").lower()
               and "PZTK:" not in h.get("text", "")]
        for side in ("server", "client")}
    l1_counts = {"loading_version": {"server": lv["server"]["count"],
                                     "client": lv["client"]["count"]},
                 "loading_common": {"server": lc["server"]["count"],
                                    "client": lc["client"]["count"]},
                 "wide_TKX_Loader": {"server": wide["server"]["count"],
                                     "client": wide["client"]["count"]},
                 "common_id_mentions": {"server": len(common_mentions["server"]),
                                        "client": len(common_mentions["client"])}}
    version_shape_ok = (lv["server"]["count"] == 1 and lv["client"]["count"] == 2
                        and not lv["server"]["saturated"] and not lv["client"]["saturated"])
    saw_loading_common = lc["server"]["count"] > 0 or lc["client"]["count"] > 0
    other_common_mention = (len(common_mentions["server"]) + len(common_mentions["client"])) > 0
    if lv["server"]["count"] == 0 and lv["client"]["count"] == 0:
        l1v = "unmeasured"
    elif saw_loading_common or not version_shape_ok:
        l1v = "falsified"
    elif other_common_mention:
        # P12's SECOND half made visible: the engine names the common id somewhere without
        # loading it. That is positive evidence for the registration claim, so it is not trivial.
        l1v = "as_predicted"
    else:
        l1v = "trivial"                            # amendment 3's default, and the honest one
    out["phases"]["L1"] = {
        "question": "which id does the engine ANNOUNCE for a mod whose two mod.info files carry "
                    "two different ids?",
        "counts": l1_counts,
        # Kept per SIDE: the line numbers belong to two different files, and a merged list
        # would read as one log.
        "loading_version_hits": {"server": lv["server"]["hits"], "client": lv["client"]["hits"]},
        "loading_common_hits": {"server": lc["server"]["hits"], "client": lc["client"]["hits"]},
        "common_id_mentions": common_mentions,
        "wide_hits": {"server": wide["server"]["hits"], "client": wide["client"]["hits"]},
        "weakness": "amendment 3: searchForModInfo returns the first mod.info whose id MATCHES "
                    "the requested id, so with Mods=TKX_LoaderVersion the mod loads under "
                    "EITHER read order and P12 holds trivially. The discriminating boot -- "
                    "asking for TKX_LoaderCommon -- is Task 6's second boot, not this one.",
    }
    grade("L1",
          "P12: the engine announces the id it was asked for -- `loading TKX_LoaderVersion` "
          "once on the server and twice on the client console, and NO `loading "
          "TKX_LoaderCommon`. The common id is registered into modIdToDir on the way past but "
          "is not the mod that loaded.",
          l1_counts, l1v,
          "a `loading TKX_LoaderCommon` line -- or a version-id count other than 1 server / 2 "
          "client -- falsifies it and rewrites mod_lint.info_chain's model. Any OTHER line "
          "naming TKX_LoaderCommon is positive evidence for the registration half and lifts the "
          "verdict off `trivial`.",
          {"grading_rule": "trivial unless the log shows something unexpected (amendment 3)"})

    # ================= L2 -- the merge rule ==============================================
    ov = out["greps"]["overrides_version"]
    srv_tails = [t["tail"] for t in ov["server"].get("tails", [])]
    cli_tails = [t["tail"] for t in ov["client"].get("tails", [])]
    # The empty-tail line x121 recorded for three TKX mods is a KNOWN shape of this print, so it
    # is split out here rather than counted as a path: a reading that lumped the two together
    # would report two overridden files where the loader named one.
    srv_paths = [t for t in srv_tails if t]
    cli_paths = [t for t in cli_tails if t]
    tail_ok = ([t.lower() for t in srv_paths] == [WHICH_REL]
               and [t.lower() for t in cli_paths] == [WHICH_REL, WHICH_REL])
    which = {"client": val_of(globals_read["TKX_LoaderWhich"], "client"),
             "server": val_of(globals_read["TKX_LoaderWhich"], "server")}
    common_tree = globals_read["TKX_LoaderCommonTree"]
    version_tree = globals_read["TKX_LoaderVersionTree"]
    trees_both_ran = both_resolved(common_tree) and both_resolved(version_tree)
    which_agree = which["client"] == which["server"] and which["client"] is not None
    l2_observed = {
        "overrides_lines": {"server": ov["server"]["count"], "client": ov["client"]["count"],
                            "server_saturated": ov["server"]["saturated"],
                            "client_saturated": ov["client"]["saturated"]},
        "overrides_tails": {"server": ov["server"].get("tails"),
                            "client": ov["client"].get("tails")},
        "empty_tails": {"server": len(srv_tails) - len(srv_paths),
                        "client": len(cli_tails) - len(cli_paths)},
        "tail_matches_prediction": tail_ok,
        "TKX_LoaderWhich": which,
        "TKX_LoaderWhich_sides_agree": which_agree,
        "TKX_LoaderCommonTree": {"client": res_of(common_tree, "client"),
                                 "server": res_of(common_tree, "server"),
                                 "value": {"client": val_of(common_tree, "client"),
                                           "server": val_of(common_tree, "server")}},
        "TKX_LoaderVersionTree": {"client": res_of(version_tree, "client"),
                                  "server": res_of(version_tree, "server"),
                                  "value": {"client": val_of(version_tree, "client"),
                                            "server": val_of(version_tree, "server")}},
        "both_trees_ran": trees_both_ran,
        # The engine's own file-walk, quoted from its NoSuchFileException paths: which of the
        # mod's trees it enumerated `media/` under. Corroborates the globals from a completely
        # independent direction -- one is what survived, the other is what was looked at.
        "media_trees_walked": tree_walk_of(wide, "TKX_LoaderVersion"),
    }
    if which["client"] is None and which["server"] is None:
        l2v = "unmeasured"
    elif tail_ok and which_agree and which["client"] == "version" and trees_both_ran:
        l2v = "as_predicted"
    else:
        l2v = "falsified"
    out["phases"]["L2"] = {
        "question": "when common/ and a version dir ship the SAME relative path, which copy "
                    "does the engine run -- and did the losing tree run at all?",
        "reading": l2_observed,
        "why_both_unique_globals": "TKX_LoaderWhich alone cannot separate 'common/ lost the "
                                   "collision' from 'common/ never ran'. The two unique globals "
                                   "can: TKX_LoaderCommonTree exists only under common/ and "
                                   "TKX_LoaderVersionTree only under 42.20/, and neither has a "
                                   "counterpart that could override it.",
        "case_rule": "the loader lower-cases the relative paths it prints "
                     "(td3-20260911-001948: `media/lua/client/autocook.lua` for a file shipped "
                     "as AutoCook.lua), so the tail is compared case-INSENSITIVELY.",
    }
    grade("L2",
          "P13: exactly ONE `mod \"TKX_LoaderVersion\" overrides` line on the server with tail "
          f"`{WHICH_REL}`, and TWO on the client console (one per Lua state). "
          "P14: `TKX_LoaderWhich` == \"version\" on BOTH sides, with TKX_LoaderCommonTree and "
          "TKX_LoaderVersionTree BOTH resolving.",
          l2_observed, l2v,
          "`common` for TKX_LoaderWhich = the version dir LOST the collision (pass order is "
          "version-then-common). An unresolved TKX_LoaderCommonTree beside a `version` answer "
          "means common/ never ran and the `overrides` line is about VANILLA, not about the "
          "common tree -- a different rule entirely. A second tail, or a tail that is not "
          f"`{WHICH_REL}`, means the two trees were merged by something other than relative "
          "path.")

    # ================= L3 -- the empty-version-dir arm ===================================
    co_table = globals_read["TKX_CommonOnly"]
    co_ver = globals_read["TKX_CommonOnly.version"]
    missing_e = ("TKX_CommonOnly" in out["mods_not_found"]["server"]
                 or "TKX_CommonOnly" in out["mods_not_found"]["client"]
                 or "TKX_CommonOnly" in mods_check.get("missing", []))
    l3_observed = {
        "boot_check": {"mods_not_found": out["mods_not_found"],
                       "check_mods_loaded_raised": mods_check["raised"],
                       "log_lines": mods_check.get("log_lines")
                       or out["greps"]["mod_missing"]["server"]["hits"]},
        "TKX_CommonOnly": {"client": res_of(co_table, "client"),
                           "server": res_of(co_table, "server"),
                           "type": {"client": (co_table["client"] or {}).get("type"),
                                    "server": (co_table["server"] or {}).get("type")},
                           "keyCount": {"client": (co_table["client"] or {}).get("keyCount"),
                                        "server": (co_table["server"] or {}).get("keyCount")}},
        "TKX_CommonOnly.version": {"client": res_of(co_ver, "client"),
                                   "server": res_of(co_ver, "server"),
                                   "value": {"client": val_of(co_ver, "client"),
                                             "server": val_of(co_ver, "server")},
                                   "failedAt": {
                                       "client": (co_ver["client"] or {}).get("failedAt"),
                                       "server": (co_ver["server"] or {}).get("failedAt")}},
        # The version dir holds a mod.info and no media/ at all -- so seeing `42.20` here means
        # the engine WALKED a media folder that does not exist and carried on, which is the
        # mechanism behind P15 rather than merely its outcome.
        "media_trees_walked": tree_walk_of(out["greps"]["commononly_wide"], "TKX_CommonOnly"),
        "wide_hits": {"server": out["greps"]["commononly_wide"]["server"]["hits"],
                      "client": out["greps"]["commononly_wide"]["client"]["hits"]},
    }
    if missing_e:
        l3v = "falsified"                          # amendment 9's arm: the FAIL is the reading
        l3_note = "not found"
    elif res_of(co_ver, "client") is None and res_of(co_ver, "server") is None:
        l3v, l3_note = "unmeasured", "no reply from either side"
    elif both_resolved(co_ver) and val_of(co_ver, "client") == 1 \
            and val_of(co_ver, "server") == 1:
        l3v, l3_note = "as_predicted", "resolved on both sides"
    else:
        l3v, l3_note = "falsified", "did not resolve on both sides"
    l3_observed["observed"] = l3_note
    out["phases"]["L3"] = {
        "question": "does a version folder holding a mod.info and NO media/ suppress the mod's "
                    "common/ tree, or cost it nothing?",
        "reading": l3_observed,
        "not_a_gate": "deliberately NOT a [[verify]] row (the profile says so in its own "
                      "comment): a measurement must never be a gate, and `resolved: false` here "
                      "is the opposite finding rather than a failure.",
        "amendment_9": "if the engine had answered `required mod \"TKX_CommonOnly\" not found`, "
                       "check_mods_loaded's raise would itself have been the reading; the arm "
                       "is wired into this driver and `boot_check` above records whether it "
                       "fired.",
    }
    grade("L3",
          "P15: `TKX_CommonOnly.version` resolves to 1 on BOTH sides -- pass A maps "
          "common/media into activeFileMap and pass B adds nothing, so a version dir that ships "
          "only a mod.info costs the mod nothing.",
          l3_observed, l3v,
          "`resolved: false` (failedAt TKX_CommonOnly = the global never existed), or a "
          "`required mod \"TKX_CommonOnly\" not found` line at boot, is the opposite finding and "
          "is equally citable.")

    # ================= L4 -- the control =================================================
    tkv = globals_read["TK.version"]
    l4_observed = {"client": {"resolved": res_of(tkv, "client"), "value": val_of(tkv, "client")},
                   "server": {"resolved": res_of(tkv, "server"), "value": val_of(tkv, "server")},
                   "echo_ok": all(x["echo_ok"] for x in ECHO_CHECKS) if ECHO_CHECKS else None}
    if res_of(tkv, "client") is None and res_of(tkv, "server") is None:
        l4v = "unmeasured"
    elif val_of(tkv, "client") == 1 and val_of(tkv, "server") == 1 and both_resolved(tkv):
        l4v = "as_predicted"
    else:
        l4v = "falsified"
    out["phases"]["L4"] = {
        "question": "is the _G walk itself sound on both sides?",
        "reading": l4_observed,
        "why_first": "sent before every other global (amendment 5): a `resolved: false` "
                     "anywhere above is only a finding once this has passed.",
    }
    grade("L4",
          "TK.version == 1 on BOTH sides. TK is a global on purpose "
          "(PZTestKit_Core.lua:2).",
          l4_observed, l4v,
          "a resolved=false or a value other than 1 means the _G walk is broken, and every "
          "`resolved: false` above becomes unreadable rather than a finding.")

    # ================= the readings, stated as verdicts ==================================
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "echo_ok": all(x["echo_ok"] for x in ECHO_CHECKS) if ECHO_CHECKS else None,
        "echo_checks": len(ECHO_CHECKS),
        "echo_failures": [x for x in ECHO_CHECKS if not x["echo_ok"]],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "L1_loading": l1_counts,
        "L2_overrides": {"server": ov["server"]["count"], "client": ov["client"]["count"],
                         "server_tails": srv_paths, "client_tails": cli_paths},
        "L2_which": which,
        "L2_trees": {"common": {"client": res_of(common_tree, "client"),
                                "server": res_of(common_tree, "server")},
                     "version": {"client": res_of(version_tree, "client"),
                                 "server": res_of(version_tree, "server")}},
        "L3_common_only_version": {"client": val_of(co_ver, "client"),
                                   "server": val_of(co_ver, "server"),
                                   "resolved": {"client": res_of(co_ver, "client"),
                                                "server": res_of(co_ver, "server")}},
        "L4_TK_version": {"client": val_of(tkv, "client"), "server": val_of(tkv, "server")},
        "lua_error_hits": {"server": out["greps"]["lua_errors"]["server"]["count"],
                           "client": out["greps"]["lua_errors"]["client"]["count"]},
        "mod_missing_hits": {"server": out["greps"]["mod_missing"]["server"]["count"],
                             "client": out["greps"]["mod_missing"]["client"]["count"]},
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    save(path, out, tl, server)
    try:
        teardown(tl, server, clients)
    finally:
        hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["server_error_count"] = len(server.errors)
        out["client_lua_error"] = "lua_error" in getattr(clients[0], "seen", ()) if clients else None
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-loader.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
