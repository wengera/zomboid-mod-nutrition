"""x485-smoke -- Plan 17 Task 7b (live): the smoke boot of the FINAL upload copy. The copy changed after x483/x484 (the
close fix wave's comments, N1, N4; revision R2's kernel and its panel keys; 4ff68475's comment), so one boot proves the
final bytes load and join: the two Plan 17 options set in the server's options file read back on the server, admin and
bob; both clients join cleanly at 1.0.0; no mod error; and the R2 panel translation keys load on the client.

x483's design (Plan 17 Task 7, testing/experiments/x483_options.py on x48b_lib.py; x471's before it), on this file's own
constants: x48b_lib is frozen with x483's run and never edited, so this file reuses its helpers by import (take_reads,
_provenance, _summary, READ_PLAN and the x483 wall constants) and names its own staged commit, session, profile,
option values and grades. One boot of profile x48-smoke (fixture two: admin -debug, role admin; bob release, role user;
PZTestKit and the STAGED upload copy release/NutritionRevamp/Contents/mods/NutritionRevamp, re-staged from STAGED_FROM;
Nutrition false, DayLength 1, sleep off), build 42.21.0. The profile's [sandbox.NR] DeathPace = 1 (Vanilla) and
HealthCombine = 1 (Worst) are merged into Server/pzt_SandboxVars.lua at seed: each off its declared default (3, 2) and
off x483's (2, 3), so a stale options file from either cannot pass.

THE SESSION (one boot, under 10 wall minutes, in a foreground call): the server, admin attached (session.attach_clients),
then bob started and watched (x47_lib.watch_bob: a never-ready bob is a reading, not a raise). Once bob is ready and
READ_SETTLE_S has passed: the read set `after_ready` (x48b_lib.READ_PLAN's lua.global reads on the server, admin and
bob), the text set `after_ready` (lua.call getText <key> for each of KEYS on admin and bob), the verify rows; HOLD_S
held; the read and text sets `end`; the players read. After teardown the server's user and connections logs and bob's
connections log are read and copied (x471's). The wall guard (x483's F1): bob is started only by BUDGET_S - OBS_S -
CLOSE_RESERVE_S; the profile's [server] timeout bounds the boot wait at 240 s.

THE TRANSLATION READ. lua.global never calls, so a key's text is read with the harness's lua.call (shared, both sides),
calling the global getText with the key: {ok, side, path, nargs, r1}. The jar (42.21, Translator.getTextInternal
L481-L495) returns the key itself for a missing key, after a `!` when the debug translation prefix is on, and a found
UI_ key's text after a `*` under the same debug option; text_state strips one such marker before comparing. A missing
key reading as its own name is graded `missing`, never `present`.

THE GRADES (pure; each has a failing case in testing/tests/test_x485.py; a grade on no valid sample is unmeasured):
  INI         (precondition) the seeded options file's NR block holds DeathPace = PACE_SET and HealthCombine =
              COMBINE_SET.
  OPT_SERVER, OPT_ADMIN, OPT_BOB  SandboxVars.NR.DeathPace PACE_SET and SandboxVars.NR.HealthCombine COMBINE_SET on
              that side in every read set (a client's copy is the one the server sends at the join).
  MOD_READ    on the server: NutritionRevamp.server.options.deathPace and .healthCombine (the options poll) and
              NutritionRevamp.kernel.drain.OPT.pace and .combine (the players' minute) read PACE_SET and COMBINE_SET in
              every read set. The clients' server.options copies are a reading (the poll is server-gated; x483).
  JOIN        x47_lib's: admin and bob ready, NutritionRevamp.version STAGED_VERSION on all three sides at the end,
              players [admin, bob], bob `fully connected` in the user log, no Anti-cheat line, no checksum-mismatch line.
  Z           x45g_lib's: no mod error line in the server log, admin not parked in the debugger.
  NEWKEYS     the server's NutritionRevamp.version reads STAGED_VERSION at the end, and on admin every key of KEYS
              reads its text in every text set (`present`); falsified on a key reading as its own name (`missing`) or
              any other text, or the server's version off; unmeasured when a read went unanswered. bob's texts are a
              reading.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.

WALL: about 3.5 min (x483 took 184.4 s); BUDGET_S 540.
"""
import json
import os
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
import x47_lib as L47                                                         # noqa: E402
import x48b_lib as L                                                          # noqa: E402

KEY = "x485"
PREFIX = "x485"
PROFILE = "x48-smoke"
ARTIFACT = "smoke.json"
BUDGET_S = 540.0
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"

REPO = X.REPO
SRV = X.SRV
NR = G.NR
ADMIN, BOB = L47.ADMIN, L47.BOB
MOD_DIR = G.MOD_DIR
STAGE_ROOT = L.STAGE_ROOT                # release/NutritionRevamp, the upload copy
STAGE_MOD = L.STAGE_MOD
STAGED_FROM = "4ff68475"                 # mod/'s last commit (Plan 17 Task 6c fix 1), the final upload bytes
STAGED_VERSION = "1.0.0"
MIN_FREE_GB = 12.0
FIXTURE = "two"
CLIENTS = [ADMIN, BOB]
DAY_LENGTH = 1
PACE_SET = 1                             # Vanilla; the declared default 3, x483's 2
COMBINE_SET = 1                          # Worst; the declared default 2, x483's 3
PACE_DEFAULT, COMBINE_DEFAULT = L.PACE_DEFAULT, L.COMBINE_DEFAULT
X483_SET = (L.PACE_SET, L.COMBINE_SET)
SERVER_TIMEOUT_S = L.SERVER_TIMEOUT_S    # 240: the profile's [server] timeout
READ_PLAN = L.READ_PLAN
READ_SETTLE_S, HOLD_S, OBS_S, CLOSE_RESERVE_S = L.READ_SETTLE_S, L.HOLD_S, L.OBS_S, L.CLOSE_RESERVE_S
SANDBOX_REL = L.SANDBOX_REL
TRANSLATE_REL = "common/media/lua/shared/Translate/EN/UI.json"
KEYS = {                                  # two of revision R2's panel keys (UI_NR_DrainRec_<name>), with their EN text
    "UI_NR_DrainRec_starvation": "Recovering from starvation",
    "UI_NR_DrainRec_iron": "Recovering from iron poisoning",
}
TEXT_SIDES = (ADMIN, BOB)                 # admin graded, bob a reading
TEXT_MARKERS = "*!"                       # the debug translation prefix's markers (Translator.getTextInternal)
CALL_TIMEOUT_S = 15

SERVER_PACE_G, SERVER_COMBINE_G = L.SERVER_PACE_G, L.SERVER_COMBINE_G
MOD_PACE_G, MOD_COMBINE_G = L.MOD_PACE_G, L.MOD_COMBINE_G
OPT_PACE_G, OPT_COMBINE_G, OPT_DAYMIN_G = L.OPT_PACE_G, L.OPT_COMBINE_G, L.OPT_DAYMIN_G
VERSION_G = L.VERSION_G
READAT_G = "NutritionRevamp.server.options.readAt"

SESSION = ("Plan 17 Task 7b x485: the final upload copy's smoke boot: NR.DeathPace 1 and NR.HealthCombine 1 read back "
           "on the server, admin and bob; the clean 1.0.0 join; no mod error; the R2 panel keys load; one boot of "
           + PROFILE)
PRED = {
    "INI": "the seeded NR block holds DeathPace = 1 and HealthCombine = 1",
    "OPT_SERVER": "SandboxVars.NR.DeathPace 1 and HealthCombine 1 on the server", "OPT_ADMIN": "1 and 1 on admin",
    "OPT_BOB": "1 and 1 on bob",
    "MOD_READ": "server options.deathPace 1 and healthCombine 1, K.drain.OPT.pace 1 and combine 1",
    "JOIN": "both ready, 1.0.0 on three sides, players [admin, bob], bob fully connected, no Anti-cheat or mismatch line",
    "Z": "no mod error line, admin not parked",
    "NEWKEYS": "server version 1.0.0; on admin getText reads 'Recovering from starvation' and 'Recovering from iron "
               "poisoning' in both text sets",
}
CONSTANTS = {k: v for k, v in dict(globals()).items() if k.isupper() and k not in ("HERE", "REPO", "PRED", "SESSION")
             and isinstance(v, (int, float, str, bool, tuple, dict, list))}

g = L47.g


# ================================================================ the options (pure)
def grade_ini(seeded):
    """INI: the seeded file's NR block holds DeathPace = PACE_SET and HealthCombine = COMBINE_SET."""
    obs = {"seeded_nr_block": seeded}
    if not isinstance(seeded, dict):
        return "unmeasured", obs
    ok = L47.same_number(seeded.get("DeathPace"), PACE_SET) and L47.same_number(seeded.get("HealthCombine"),
                                                                                 COMBINE_SET)
    return ("as_predicted" if ok else "falsified"), obs


def grade_pair(read_sets, side, pace_name, combine_name):
    """Both leaves on one side in every read set: falsified on any answered off value, unmeasured unless every read
    answered, else as_predicted."""
    vp, op = L47.grade_option(L47.collect(read_sets, side, pace_name), PACE_SET)
    vc, oc = L47.grade_option(L47.collect(read_sets, side, combine_name), COMBINE_SET)
    obs = {"side": side, pace_name: op, combine_name: oc}
    if "falsified" in (vp, vc):
        return "falsified", obs
    if "unmeasured" in (vp, vc) or not op["n"] or not oc["n"]:
        return "unmeasured", obs
    return "as_predicted", obs


def grade_mod_read(read_sets):
    """MOD_READ: the server's polled options and K.drain.OPT read PACE_SET and COMBINE_SET in every read set."""
    v1, o1 = grade_pair(read_sets, SRV, MOD_PACE_G, MOD_COMBINE_G)
    v2, o2 = grade_pair(read_sets, SRV, OPT_PACE_G, OPT_COMBINE_G)
    obs = {"options": o1, "opt": o2}
    if "falsified" in (v1, v2):
        return "falsified", obs
    if "unmeasured" in (v1, v2):
        return "unmeasured", obs
    return "as_predicted", obs


# ================================================================ the translation keys (pure)
def take_texts(ask, nodes, tag, text_sets, keys=None, sides=TEXT_SIDES):
    """One text set: lua.call getText <key> for each key on each side, at text_sets[tag][side][key]; a side whose call
    timed out is not asked again in this set (its later calls record `skipped`, unanswered like the timeout)."""
    rs = text_sets.setdefault(tag, {})
    for side in sides:
        node = nodes.get(side)
        row = rs.setdefault(side, {})
        wedged = None
        for k in (keys or KEYS):
            if node is None:
                row[k] = {"error": "no node"}
            elif wedged is not None:
                row[k] = {"error": f"skipped: {wedged}"}
            else:
                try:
                    row[k] = ask(node, "lua.call", f"getText {k}", timeout=CALL_TIMEOUT_S)
                except Exception as e:             # noqa: BLE001 - recorded
                    row[k] = {"error": f"{type(e).__name__}: {e}"}
                err = row[k].get("error") if isinstance(row[k], dict) else None
                if err and "Timeout" in str(err):
                    wedged = f"the side timed out on {k} earlier in this set"
    return rs


def text_state(reply, key, want):
    """(state, text) of one getText reply: `present` when r1 is the key's text, `missing` when r1 is the key itself
    (getText's answer for a key no file declares), `other` for any other string, `unanswered` otherwise. One leading
    debug-prefix marker (TEXT_MARKERS) is stripped first."""
    if not (isinstance(reply, dict) and reply.get("ok") is True and isinstance(reply.get("r1"), str)):
        return "unanswered", None
    text = reply["r1"]
    bare = text[1:] if text[:1] and text[:1] in TEXT_MARKERS else text
    if bare == want:
        return "present", text
    if bare == key:
        return "missing", text
    return "other", text


def grade_newkeys(text_sets, read_sets, side=ADMIN, keys=None):
    """NEWKEYS: the server's NutritionRevamp.version STAGED_VERSION at the end, and every key's text present on `side`
    in every text set."""
    keys = keys or KEYS
    ans, ver = L47.read_value(g(read_sets, "end", SRV, VERSION_G))
    states = {}
    for tag, rs in (text_sets or {}).items():
        for k, want in keys.items():
            states[f"{tag}:{k}"] = text_state(g(rs, side, k), k, want)
    obs = {"side": side, "server_version": ver, "server_version_answered": ans,
           "states": {k: {"state": s, "text": t} for k, (s, t) in states.items()}, "n_sets": len(text_sets or {})}
    bad = [k for k, (s, _) in states.items() if s in ("missing", "other")]
    if bad or (ans and ver != STAGED_VERSION):
        return "falsified", dict(obs, off=bad)
    if not ans or not states or any(s == "unanswered" for s, _ in states.values()):
        return "unmeasured", obs
    return "as_predicted", obs


def text_readings(text_sets, side=BOB, keys=None):
    keys = keys or KEYS
    return {f"{tag}:{k}": text_state(g(rs, side, k), k, want)[0]
            for tag, rs in (text_sets or {}).items() for k, want in keys.items()}


def grade_x485(xs, out, read_sets, text_sets):
    bob_started = g(out, "bob", "start_wall") is not None
    xs.grade("Z", *G.grade_z(out), "a mod error line in the server log, or admin parked in the debugger")
    xs.grade("INI", *grade_ini(out.get("sandbox_seeded")),
             "the seeded options file lacks NR.DeathPace = 1 or NR.HealthCombine = 1")
    for name, side in (("OPT_SERVER", SRV), ("OPT_ADMIN", ADMIN), ("OPT_BOB", BOB)):
        xs.grade(name, *grade_pair(read_sets, side, SERVER_PACE_G, SERVER_COMBINE_G),
                 f"SandboxVars.NR.DeathPace or HealthCombine reads another value on {side}")
    xs.grade("MOD_READ", *grade_mod_read(read_sets), "the server's polled options or K.drain.OPT read another value")
    xs.grade("JOIN", *L47.grade_join(L47.join_obs(out, read_sets, bob_started)),
             "bob or admin not ready, a version or players read off, an Anti-cheat or mismatch line")
    xs.grade("NEWKEYS", *grade_newkeys(text_sets, read_sets),
             "a panel key reads as its own name or another text on admin, or the server's version off")
    rd = out.setdefault("readings", {})
    rd["client_server_options"] = {"predicted": {MOD_PACE_G: PACE_DEFAULT, MOD_COMBINE_G: COMBINE_DEFAULT}}
    for s in (ADMIN, BOB):
        rd["client_server_options"][s] = {n: L47.read_value(g(read_sets, "end", s, n))[1]
                                          for n in (MOD_PACE_G, MOD_COMBINE_G)}
    rd["server_opt_dayMin"] = L47.read_value(g(read_sets, "end", SRV, OPT_DAYMIN_G))[1]
    rd["server_readAt"] = L47.read_value(g(read_sets, "end", SRV, READAT_G))[1]
    rd["bob_texts"] = text_readings(text_sets)


# ================================================================ the pre-boot checks (offline; tested)
def profile_doc_checks(doc, text=""):
    """The profile's TOML: its header naming its own file, fixture two with admin and bob, sleep off, PZTestKit and the
    staged upload copy, Nutrition false, DayLength 1, the [sandbox.NR] block of DeathPace and HealthCombine alone at
    PACE_SET and COMBINE_SET, a version verify row on every side, no client override, the 240 s boot wait."""
    mods = [m.get("id") for m in doc.get("mods") or []]
    paths = {m.get("id"): m.get("path") for m in doc.get("mods") or []}
    sb = doc.get("sandbox") or {}
    srv = doc.get("server") or {}
    vr = sorted(v.get("side") for v in doc.get("verify") or [] if v.get("args") == f"{NR}.version"
                and v.get("expect") == f'"value": "{STAGED_VERSION}"')
    return {"header_names_file": text.startswith(f"# testing/profiles/{PROFILE}.toml"),
            "fixture": doc.get("fixture") == FIXTURE,
            "clients": doc.get("clients", [ADMIN]) == CLIENTS,
            "sleep_off": srv.get("SleepAllowed") is False and srv.get("SleepNeeded") is False,
            "mods_staged": mods == ["PZTestKit", NR] and paths.get(NR) == STAGE_MOD,
            "nutrition_false": sb.get("Nutrition") is False,
            "day_length": sb.get("DayLength") == DAY_LENGTH,
            "nr_block": sb.get("NR") == {"DeathPace": PACE_SET, "HealthCombine": COMBINE_SET},
            "verify_version": vr == ["client", "client:bob", "server"],
            "no_override": "client_overrides" not in doc,
            "server_timeout": srv.get("timeout") == SERVER_TIMEOUT_S}


def values_distinct():
    """Each set value off its declared default and off x483's, so neither a default nor x483's file can pass."""
    return PACE_SET not in (PACE_DEFAULT, X483_SET[0]) and COMBINE_SET not in (COMBINE_DEFAULT, X483_SET[1])


def keys_at_commit(repo=REPO, commit=STAGED_FROM):
    """The KEYS texts as mod/'s UI.json at the staged commit declares them ({key: text or None})."""
    p = subprocess.run(["git", "show", f"{commit}:{MOD_DIR}/{TRANSLATE_REL}"], cwd=repo, capture_output=True)
    try:
        doc = json.loads(p.stdout.decode("utf-8"))
    except ValueError:
        return {k: None for k in KEYS}
    return {k: doc.get(k) for k in KEYS}


def staged_gate(repo=REPO):
    """x45g_lib's gate at this session's paths and commit."""
    return G.staged_gate(repo=repo, commit=STAGED_FROM, stage_root=STAGE_ROOT, stage_mod=STAGE_MOD)


def preboot(driver_file, repo=REPO):
    """The driver's file names its session (CLAUDE.md s5); no artifact of the prefix committed; STAGED_FROM mod/'s
    last commit; the profile's TOML; the values off both defaults and x483's; the keys' texts at STAGED_FROM.
    Returns (checks, ok)."""
    import glob
    import tomllib
    c = {"driver_file": os.path.basename(driver_file) == _ME,
         "driver_prefix": os.path.basename(driver_file).startswith(KEY + "_")}
    c["no_prior_artifact"] = not glob.glob(os.path.join(repo, "testing", "artifacts", KEY + "-*"))
    head = L.mod_head(repo)
    c["mod_head"] = head
    c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM) or STAGED_FROM.startswith(head))
    try:
        with open(os.path.join(repo, "testing", "profiles", PROFILE + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        prof = profile_doc_checks(tomllib.loads(text), text)
    except (OSError, ValueError) as e:
        prof = {"profile_read": False, "error": f"{type(e).__name__}: {e}"}
    c["profile_checks"] = prof
    c["values_distinct"] = values_distinct()
    c["keys_at_commit"] = keys_at_commit(repo)
    c["keys_texts_match"] = c["keys_at_commit"] == KEYS
    skip = ("profile_checks", "mod_head", "keys_at_commit")
    good = all(v is True for k, v in c.items() if k not in skip) and all(v is True for k, v in prof.items()
                                                                           if k != "error")
    return c, good


# ================================================================ the boot
def _gates(xs, out, prof, run_dir, lint_paths, lint_list, gate=staged_gate):
    """The refusals before the boot (x48b_lib._gates at this session's commit): doctor, a dirty harness, the staged
    gate and its verify rows, free memory, the layout lint."""
    if not out["doctor_clean"]:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"]:
        xs.refuse("the harness Lua is dirty; commit before the boot (CLAUDE.md s5)")
    mg = out["manifest_gate"] = gate()
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    mg["version_is_release"] = mg.get("staged_version") == STAGED_VERSION
    if not (mg["ok"] and mg["verify_rows_match"] and mg["version_is_release"]):
        xs.refuse(f"the staged copy does not match {STAGED_FROM}, the verify rows or {STAGED_VERSION}: {mg!r}; "
                  "not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, G.MANIFEST_NAME), os.path.join(run_dir, G.MANIFEST_NAME))
        xs.copied.append(G.MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(lint_list)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")


def main(budget_s=BUDGET_S):
    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import (Timeline, attach_clients, make_client, make_server,   # noqa: E402
                             override_kw, teardown, verify)

    prof = profile.load(PROFILE)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"restored": f"fixture {prof.fixture} restored into the run dir", "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=PRED, user=ADMIN)
    xs.path = os.path.join(run_dir, ARTIFACT)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session_key": KEY, "session": SESSION, "driver": _ME, "lib": L.LIB_FILE, "user": ADMIN,
        "profile": prof.report(), "preboot": pre,
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "predictions": PRED, "constants": CONSTANTS, "meta": {"budget_s": budget_s},
    })
    L._provenance(out, git_say, git_dirty)
    out["driver_commit"] = git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + _ME)
    _gates(xs, out, prof, run_dir, lint_paths, profile.lint_sources(prof, prof.sources))
    server, bob = None, None
    read_sets = out.setdefault("read_sets", {})
    text_sets = out.setdefault("text_sets", {})
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        sbp = os.path.join(run_dir, *SANDBOX_REL)
        out["sandbox_seeded"] = L47.sandbox_nr_block(L47.read_text(sbp))
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        out["server_pid"] = server.proc.pid
        out["build"] = server.build
        tl.mark("server_started", pid=server.proc.pid)
        out["sandbox_after_start"] = L47.sandbox_nr_block(L47.read_text(sbp))
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, users=[ADMIN], started=started))
        out["admin_ready_wall"] = xs.wall()
        if xs.wall() > budget_s - OBS_S - CLOSE_RESERVE_S:
            out["budget_stop"] = {"phase": "bob", "wall": xs.wall(),
                                  "why": f"admin ready at {xs.wall()} s: bob's {OBS_S} s watch would end past the budget"}
            raise RuntimeError("bob not started: " + out["budget_stop"]["why"])
        bob, restored = make_client(run_dir, BOB, server, rec_fx, safemode=prof.safemode, launcher=prof.launcher,
                                    **override_kw(prof, BOB, server))
        started.append(bob)
        out["bob_restored"] = restored
        out["bob_debug"] = bob.debug
        out["bob_mod_source"] = os.path.relpath(bob.mod_sources.get(NR, ""), REPO).replace(os.sep, "/")
        out["deployed"] = L47.deployed_copies(run_dir, "common/media/lua/server/NR_Server_Options.lua")
        xs.mem("before_bob")
        xs.persist()

        def reads(tag):
            nodes = {SRV: server, ADMIN: clients.get(ADMIN), BOB: bob}
            L.take_reads(ask, nodes, tag, read_sets, plan=READ_PLAN)
            take_texts(ask, nodes, tag, text_sets)

        def on_ready():
            clients[BOB] = bob
            time.sleep(READ_SETTLE_S)
            reads("after_ready")
            out["verify"] = verify(prof, server, clients, tl)
            xs.persist()
            return HOLD_S

        xs.cur_phase = "bob"
        ready = L47.watch_bob(xs, bob, on_ready, OBS_S)
        if ready and bob.alive:
            reads("end")
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
            Lg = out["logs"] = {"patterns": {"log": L47.LOG_RX.pattern, "mismatch": L47.MISMATCH_RX.pattern}}
            if server is None:
                return
            outs = sorted(set([os.path.join(run_dir, "server-stdout.log"), server.log_path]))
            Lg["server"], Lg["server_echo_excluded"] = L47.grep_lines(outs, L47.LOG_RX)
            Lg["mod_error"] = [ln for ln in Lg["server"] if L47.MOD_ERR_RX.search(ln)][:40]
            Lg["server_mismatch"], _ = L47.grep_lines(outs, L47.MISMATCH_RX)
            files = L47.find_logs(run_dir)
            Lg["files"] = {k: (os.path.relpath(v, run_dir).replace(os.sep, "/") if v else None) for k, v in files.items()}
            Lg["user"] = L47.user_log_facts(L47.read_text(files["server_user"]) if files["server_user"] else None)
            Lg["bob_connections"] = L47.conn_facts(L47.read_text(files["bob_connections"])
                                                   if files["bob_connections"] else None)
            for k, v in files.items():
                if v:
                    log_copies[("bob-" if k.startswith("bob") else "server-") + os.path.basename(v)] = v
            for c in every:
                lines, _ = X.grep_noecho(c.console, L47.LOG_RX, 80, L47.ECHO_RX, L47.NEVER_RX)
                Lg.setdefault("clients", {})[getattr(c, "username", "?")] = lines
                Lg.setdefault("client_mismatch", {})[getattr(c, "username", "?")] = \
                    X.grep_noecho(c.console, L47.MISMATCH_RX, 40, L47.ECHO_RX, L47.NEVER_RX)[0]
            out["log_copies"] = {k: {"from": os.path.relpath(v, run_dir).replace(os.sep, "/"),
                                     "sha256": X.sha256_file(v)} for k, v in log_copies.items()}

        xs.finish(teardown, hard_kill, every, read_logs=read_logs,
                  grade_all=lambda: grade_x485(xs, out, read_sets, text_sets))
        xs.mem("after")
        xs.persist()
        dest = xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
        if dest:
            for nm, src in log_copies.items():
                try:
                    shutil.copyfile(src, os.path.join(dest, nm))
                except OSError as e:
                    print(f"could not copy {nm}: {type(e).__name__}: {e}")
    L._summary(out, run_id, run_dir)
    return out


if __name__ == "__main__":
    main()
