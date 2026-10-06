"""x182-translate -- Plan 7 Task 4, gate X5, LIVE. Does a mod JSON DISPLACE a vanilla translation key, or does
the Translator's merge keep vanilla's? ONE boot of profile `x18-translate` (PZTestKit + TKX_TranslateOverride,
the probe of ff0e50f: 42.20/media/lua/shared/Translate/EN/ItemName.json redefines `Base.Apple` -> "TKX Apple";
IG_UI.json redefines the vanilla `IGUI_invpanel_Type` -> "TKX Type" and adds the new `IGUI_TKX_Probe` ->
"tkx-hit"). The run id prefix is `x182`; ONE artifact `translate.json`. Shape: x172_itempass.py (step,
persist, run_phase, both logs grepped, the artifact copied by the driver).

READINGS (experiments.md X5; the amendments' order):
  P  the positive control, MANDATORY: client `text.get IGUI_TKX_Probe` must HIT "tkx-hit" -- a hit proves the
     mod's translation tree loaded on the client; a miss makes every other miss in the run unreadable, and the
     run is written as such (#1720: gate a translation-only mod on an interface key). Server twin read too.
  K  the redefined interface key: client `text.get IGUI_invpanel_Type` -- "TKX Type" = the override wins;
     the vanilla string ("Item" on this install's EN IG_UI.json, read at import into out.vanilla) = the merge keeps vanilla's.
  N  the redefined item name: client `item.spawn Base.Apple` (client-only, S6), then client
     `witness.fields item admin/Base.Apple getDisplayName,getFullType` -- "TKX Apple" = the override wins;
     "Apple" = vanilla kept. The server cannot see a client-spawned item, so a server-instantiated apple is
     added by RCON `additem` (x172's route, synced to the client) and BOTH sides then read
     `witness.fields item admin/Base.Apple getDisplayName,getFullType`, client first.
  S  the server arm is a CONTROL, not a second sample (#1026): a dedicated server resolves no display name, so
     its getDisplayName reads the full type by construction; if it reads anything else, the session has found
     something bigger than H2 and says so loudly. Server `text.get IGUI_invpanel_Type` is the control read.
  L  lua.call (2f0d3d7's second smoke): `lua.call getText IGUI_TKX_Probe` and
     `lua.call getItemNameFromFullType Base.Apple` on both sides; their raw replies recorded.

PREDICTION (written before the boot) -- THE OVERRIDE WINS on the client for both keys. Basis, read in the jar
on 2026-10-06 (`pz.sh dump zombie/core/Translator`): `loadFiles`' lambda$loadFiles$1 fills the map from the
install's base folder first (L235, tryFillMapFromFile) and from the mods after it (L236,
tryFillMapFromMods, which walks every mod's common dir then version dir, L376-L391); the per-key lambda
lambda$tryFillMapFromFile$0 PUTs the value unless the key is already present AND the new value is empty
(L365-L366: `containsKey` then `StringUtils.isNullOrEmpty`). A non-empty mod value for an existing key
therefore overwrites vanilla's. Whether ItemName display names go through the same map on this build (the
item's name may be resolved at script load, before or apart from that map) is NOT read: leg N is the
reading. Predicted: P client hit "tkx-hit"; K client "TKX Type"; N client getDisplayName "TKX Apple";
S server getDisplayName == getFullType "Base.Apple" and the server text.get misses (key returned).

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. The experiments.md X5 row names
x13-translate.toml / x131_translate.py; the shipped names are x18-translate.toml / x182_translate.py.
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

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x18-translate"
SESSION = ("Plan 7 Task 4, gate X5: a mod JSON redefining one vanilla ItemName key and one vanilla IGUI key, with "
           "a new IGUI key as the mandatory positive control, read on the client, the server arm the control; "
           "one boot of x18-translate")
ARTIFACT = "translate.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
PROBE_DIR = "testing/experiments/TKX_TranslateOverride"
VANILLA_IGUI = "D:/SteamLibrary/steamapps/common/ProjectZomboid/media/lua/shared/Translate/EN/IG_UI.json"
VANILLA_ITEMNAME = "D:/SteamLibrary/steamapps/common/ProjectZomboid/media/lua/shared/Translate/EN/ItemName.json"
APPLE = "Base.Apple"
PROBE_KEY = "IGUI_TKX_Probe"
PROBE_TEXT = "tkx-hit"
OVR_KEY = "IGUI_invpanel_Type"
OVR_TEXT = "TKX Type"
OVR_NAME = "TKX Apple"
FIELDS = "getDisplayName,getFullType"
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
LOG_RX = re.compile(r"TKX|Translate|translation|IG_UI|ItemName|LuaError|STACK TRACE|lua error|Exception", re.I)
LOG_LIMIT = 80
LOAD_RX = re.compile(r"loading TKX_TranslateOverride")
LOAD_LIMIT = 8

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x182")
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []


def wall():
    return round(time.time() - t0, 3)


def vanilla_value(fname, key):
    """The install's own EN value for a key (read-only), so the 'vanilla kept' outcome is a string, not a guess."""
    try:
        with open(fname, encoding="utf-8") as fh:
            return json.load(fh).get(key)
    except Exception as e:                     # noqa: BLE001
        return f"unread: {type(e).__name__}: {e}"


VANILLA = {"IG_UI.json": {OVR_KEY: vanilla_value(VANILLA_IGUI, OVR_KEY)},
           "ItemName.json": {APPLE: vanilla_value(VANILLA_ITEMNAME, APPLE)}}
PRED = {
    "P": {"client": PROBE_TEXT, "server": "miss (key returned)"},
    "K": {"client": OVR_TEXT, "vanilla_kept_would_read": VANILLA["IG_UI.json"][OVR_KEY]},
    "N": {"client_getDisplayName": OVR_NAME, "vanilla_kept_would_read": VANILLA["ItemName.json"][APPLE]},
    "S": {"server_getDisplayName": "== getFullType (Base.Apple)", "server_text_get": "miss (key returned)"},
    "basis": "jar Translator lambda$loadFiles$1 L235-L236 (base then mods); lambda$tryFillMapFromFile$0 "
             "L365-L366 (put unless present and the new value empty)",
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "probe_commit": git_say("log", "-1", "--format=%h", "--", PROBE_DIR),
    "probe_dirty": git_dirty(PROBE_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "vanilla": VANILLA,
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str))
                  and k not in ("REPO", "LUA_DIR")},
    "predictions": PRED,
    "deviations": [
        "The experiments.md X5 row names x13-translate.toml and x131_translate.py; the shipped names are "
        "x18-translate.toml and x182_translate.py (the plan's naming).",
        "The redefined IGUI key ships in IG_UI.json (the B42 JSON twin), not IGUI_EN.txt.",
        "The server arm reads an apple added by RCON additem: a client item.spawn never reaches the server (S6).",
        "lua.call getText / getItemNameFromFullType reads are added as the harness smoke of 2f0d3d7.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["one client-only Base.Apple (item.spawn)", "one Base.Apple added by RCON"]},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
}


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def text(side, key, tag):
    r = step(tag, side, "text.get", key)
    a = ack(r)
    return {"key": key, "reply": r["ack"], "text": a.get("text"), "miss": a.get("miss"), "null": a.get("null"),
            "error": a.get("error"), "wall": r["wall_before"]}


def fields(side, tag):
    r = step(tag, side, "witness.fields", f"item {USER}/{APPLE} {FIELDS}")
    a = ack(r)
    return {"reply": r["ack"], "resolved": a.get("resolved"), "fields": a.get("fields"), "nils": a.get("nils"),
            "missing": a.get("missing"), "count": a.get("count"), "error": a.get("error"), "wall": r["wall_before"]}


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def run_phase(name, fn):
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def parked():
    return bool(clients) and "lua_error" in getattr(clients[0], "seen", {})


# ---------------------------------------------------------------- phases
def phase_P():
    P = out["phases"]["P"] = {}
    P["tk_version"] = ack(step("P_tkv", client, "lua.global", "TK.version"))
    P["client"] = text(client, PROBE_KEY, "P_c")
    P["server"] = text(server, PROBE_KEY, "P_s")


def phase_K():
    P = out["phases"]["K"] = {}
    P["client"] = text(client, OVR_KEY, "K_c")


def phase_N():
    P = out["phases"]["N"] = {}
    P["client_pre"] = fields(client, "N_c_pre")
    P["server_pre"] = fields(server, "N_s_pre")
    P["spawn_reply"] = step("N_spawn", client, "item.spawn", APPLE)["ack"]
    P["client_after_spawn"] = fields(client, "N_c_spawn")
    P["server_after_spawn"] = fields(server, "N_s_spawn")
    ok, reply = server.rcon(f'additem "{USER}" "{APPLE}" 1')
    P["rcon"] = {"ok": ok, "reply": str(reply)[:200], "wall": wall()}
    tries = []
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        s = fields(server, f"N_s_rcon_{attempt}")
        tries.append({"attempt": attempt + 1, "resolved": s.get("resolved"), "wall": s.get("wall")})
        if s.get("resolved"):
            break
    P["server_tries"] = tries
    P["client_final"] = fields(client, "N_c_final")
    P["server_final"] = fields(server, "N_s_final")


def phase_S():
    P = out["phases"]["S"] = {}
    P["server"] = text(server, OVR_KEY, "S_s")


def phase_L():
    P = out["phases"]["L"] = {}
    for side, node in (("client", client), ("server", server)):
        P[f"{side}_getText_probe"] = step(f"L_{side}_gt", node, "lua.call", f"getText {PROBE_KEY}")["ack"]
        P[f"{side}_getText_ovr"] = step(f"L_{side}_gto", node, "lua.call", f"getText {OVR_KEY}")["ack"]
        P[f"{side}_itemName"] = step(f"L_{side}_in", node, "lua.call", f"getItemNameFromFullType {APPLE}")["ack"]


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["client_probe_again"] = text(client, PROBE_KEY, "Z_c")
    P["client_seen"] = dict(getattr(client, "seen", {}))


def body():
    run_phase("P", phase_P)
    run_phase("K", phase_K)
    run_phase("N", phase_N)
    run_phase("S", phase_S)
    run_phase("L", phase_L)
    run_phase("Z", phase_Z)


# ---------------------------------------------------------------- grading
def grade_all():
    ph = out["phases"]
    P = ph.get("P") or {}
    pc = (P.get("client") or {})
    hit = pc.get("text") == PROBE_TEXT and pc.get("miss") is False
    out["positive_control_hit"] = hit
    if not P:
        grade("P", PRED["P"], None, "unmeasured", "the positive control was not read")
    else:
        grade("P", PRED["P"], {"client": pc.get("text"), "client_miss": pc.get("miss"),
                               "server": (P.get("server") or {}).get("text"),
                               "server_miss": (P.get("server") or {}).get("miss")},
              "as_predicted" if hit else "falsified", "the client misses IGUI_TKX_Probe")
    K = ph.get("K") or {}
    kc = K.get("client") or {}
    if not K or not hit:
        grade("K", PRED["K"], kc.get("text") if K else None, "unmeasured",
              "the positive control missed (every other miss unreadable)" if K else "not read")
    else:
        t = kc.get("text")
        verdict = "as_predicted" if t == OVR_TEXT else "falsified"
        grade("K", PRED["K"], {"client": t, "miss": kc.get("miss")}, verdict,
              "the client reads the vanilla string (the merge keeps vanilla's)",
              {"outcome": "override wins" if t == OVR_TEXT else
               ("vanilla kept" if t == VANILLA["IG_UI.json"][OVR_KEY] else "other")})
    N = ph.get("N") or {}
    cf = ((N.get("client_final") or {}).get("fields") or {})
    sf = ((N.get("server_final") or {}).get("fields") or {})
    if not N or not hit or not cf:
        grade("N", PRED["N"], cf or None, "unmeasured",
              "no client apple read, or the positive control missed")
    else:
        dn = cf.get("getDisplayName")
        grade("N", PRED["N"], {"client_getDisplayName": dn, "client_getFullType": cf.get("getFullType"),
                               "client_after_spawn": ((N.get("client_after_spawn") or {}).get("fields"))},
              "as_predicted" if dn == OVR_NAME else "falsified",
              "the client reads vanilla's Apple name",
              {"outcome": "override wins" if dn == OVR_NAME else
               ("vanilla kept" if dn == VANILLA["ItemName.json"][APPLE] else "other")})
    S = ph.get("S") or {}
    if not sf and not S:
        grade("S", PRED["S"], None, "unmeasured", "no server reads")
    else:
        sdn, sft = sf.get("getDisplayName"), sf.get("getFullType")
        st = (S.get("server") or {})
        ok = sdn is not None and sdn == sft and st.get("miss") is True
        grade("S", PRED["S"], {"server_getDisplayName": sdn, "server_getFullType": sft,
                               "server_text": st.get("text"), "server_miss": st.get("miss")},
              "as_predicted" if ok else "falsified",
              "the server getDisplayName reads anything but the full type, or the server text.get hits",
              {"LOUD": None if (sdn is None or sdn == sft) else "server getDisplayName is not the full type"})


if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    client, _ = make_client(run_dir, USER, server, rec_fx)
    out["client_start_wall"] = wall()
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                   "client_markers_s": dict(getattr(client, "seen", {})),
                   "server_started_wall": out.get("server_started_wall"),
                   "client_start_wall": out.get("client_start_wall"),
                   "session_ready_wall": out.get("session_ready_wall")}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)), "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        out["client_seen"] = dict(getattr(clients[0], "seen", {})) if clients else None
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
            out["logs"] = {"server": grep_file(server.log_path, LOG_RX, LOG_LIMIT),
                           "server_load": grep_file(server.log_path, LOAD_RX, LOAD_LIMIT),
                           "limits": {"log": LOG_LIMIT, "load": LOAD_LIMIT},
                           "patterns": {"log": LOG_RX.pattern, "load": LOAD_RX.pattern}}
            if clients:
                out["logs"]["client"] = grep_file(clients[0].console, LOG_RX, LOG_LIMIT)
                out["logs"]["client_load"] = grep_file(clients[0].console, LOAD_RX, LOAD_LIMIT)
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "positive_control_hit": out.get("positive_control_hit"),
                  "error": out.get("error"), "body_error": out.get("body_error"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
