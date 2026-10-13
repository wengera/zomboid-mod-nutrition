"""x38_dialogs -- the smoke run of the harness change bdaf000c (cleanup 9a567d6b): the test clients open no helper
dialogs. pzt's Client.prepare() writes showSurvivalGuide, showFirstTimeSearchTutorial and showFirstAnimalZoneInfo false
into each client's options.ini at every prepare, and Server.seed() blanks ServerWelcomeMessage. Under CLAUDE.md s5 the
next acceptance run is the change's smoke test; this is it (brief .superpowers/sdd/harness-dialogs/smoke-brief.md).

One boot of profile x38-dialogs (fixture two: admin -debug, then bob release, each ready before the next; PZTestKit +
the STAGED copy of the tree at HEAD, release/x38-dialogs, staged before the boot; Nutrition false, DayLength 1, sleep
off). Build 42.21.0. Self-contained (the x37 engine's boot and teardown plumbing, copied, not imported). Written BEFORE
the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2).

THE PHASES:
  A  per client (bob, then admin): the Survival Guide (SurvivalGuide.instance's type, isVisible and getIsVisible through
     lua.callm, and its tick box `showGuideTickBox:isSelected(1)`, which SurvivalGuide:createChildren sets from
     getCore():getOptionShowSurvivalGuide() -- the in-game option read through the guide's own widget, since lua.call
     cannot chain getCore():getter()); the character info window (ISCharacterInfoWindow.instance getIsVisible); the
     chat (ISChat.instance: chatText.text and tabs 1-4's text in one lua.read, searched for the vanilla welcome text's
     marker phrases); the client's game speed (lua.call getGameSpeed: UIManager.getSpeedControls():getCurrentGameSpeed(),
     the state SurvivalGuide:setVisible writes); the debug flags (lua.call isDebugEnabled, getDebug,
     getLuaDebuggerErrorCount, UIManager.isShowLuaDebuggerOnError -- the #3297 and #3319 shapes); the cache options.ini
     on disk (the three keys and its mtime).
  B  tick.rate 20 s x 3, the server, admin and bob armed in the same windows, against x183b's server 10.003 / 10.053 /
     10.002 (and its client 60.02 / 60.02 / 60.02, world minutes per second 1.600 / 1.599 / 1.599; x191's the same).
  C  the mod's UI on each client (admin, then bob): the panel through x191's key-39 route (event.trigger OnKeyPressed
     39 twice: getIsVisible before, after the first press, after the second; stats.opens and keyPresses), and the
     moodles (route, stats.renders read twice SETTLE_S apart, stats.errors, probe energy).
  W  the watch window: WATCH_S of wall clock with the session up (Angus watches the game), then A's guide, speed and
     debugger reads again on both clients.
  Z  after teardown: each client's options.ini (the three keys, its mtime against the launch: a write after the launch
     is the game's own save of its Core values), the server ini's ServerWelcomeMessage line, the client consoles grepped
     for the welcome text, fault_reasons (pzt's own run verdict).

PREDICTIONS (graded in `verdicts`: as_predicted / falsified / unmeasured):
  GUIDE     on both clients SurvivalGuide.instance exists, isVisible false, and its tick box reads false (the option).
  TUTORIALS the cache options.ini holds showFirstTimeSearchTutorial=false and showFirstAnimalZoneInfo=false on both
            clients at session ready and after the run.
  CHARINFO  ISCharacterInfoWindow.instance getIsVisible true on both clients (layout.ini untouched; Angus kept it).
  CHAT      no welcome marker phrase in any chat tab's text on either client, nor in either console.
  ADMIN_DBG admin: isDebugEnabled and getDebug true; UIManager.isShowLuaDebuggerOnError true (#3319, unchanged).
  BOB_DBG   bob: isDebugEnabled and getDebug false; getLuaDebuggerErrorCount 0 (#3297's shape).
  SPEED     a reading: getGameSpeed on each client (1 predicted, the guide closed; every earlier run had 0 after
            OnGameStart), and the three tick.rate windows against x183b: does any reading move past x183b's own spread
            (server tps within 0.2 of 10.0, client tps within 0.5 of 60.0, world minutes per second within 0.01 of 1.6).
  PANEL     on each client the first key-39 press opens the panel (getIsVisible false -> true) and the second closes it.
  MOODLES   on each client the route is set (not "none"), stats.renders rises over SETTLE_S, stats.errors 0.
  OPTIONS   after the run each client's options.ini still holds the three keys false.
  WELCOME   the run's server ini holds ServerWelcomeMessage= blank.
  EXIT      verify all ok, fault_reasons empty, no lua_error marker on admin: the driver exits 0.

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, fault_reasons,  # noqa: E402
                         make_server, teardown, verify)

REPO = os.path.dirname(os.path.dirname(HERE))
PROFILE = "x38-dialogs"
PREFIX = "x381"
ARTIFACT = "dialogs.json"
DRIVER = "x38_dialogs.py"
STAGE_ROOT = "release/x38-dialogs/NutritionRevamp"
MANIFEST_NAME = "MANIFEST.json"
MOD_DIR = "mod/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
GAME_JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
APP_MANIFEST = r"D:\SteamLibrary\steamapps\appmanifest_108600.acf"
MEM_MIN_GB = 12.0
USERS = ("bob", "admin")                  # the read order: the release client first (x193's order)
SIDE = {"admin": "client", "bob": "client:bob"}
SRV = "server"
NR = "NutritionRevamp"
HELPER_KEYS = ("showSurvivalGuide", "showFirstTimeSearchTutorial", "showFirstAnimalZoneInfo")
WELCOME_RX = re.compile(r"Welcome to Project Zomboid|To interact with the Chat panel|Global Streams", re.I)
CHAT_PATHS = ("chatText.text", "tabs.1.text", "tabs.2.text", "tabs.3.text", "tabs.4.text", "chatText.chatMessages",
              "tabs")
GUIDE = "SurvivalGuide.instance"
CHARINFO = "ISCharacterInfoWindow.instance"
INST = f"{NR}.client.panel.instances.0"
KEY = 39                                  # Keyboard.KEY_SEMICOLON, the panel's default bind (ruling T5-1)
SETTLE_S = 5.0
TICK_S = 20
TICK_N = 3
WATCH_S = 60.0
X183B = {"server_tps": (10.003483800328473, 10.052752065293122, 10.002488181139586),
         "client_tps": (60.022989654655404, 60.01699065513967, 60.0199900049975),
         "client_wmps": (1.5996763019751463, 1.5990703480395352, 1.5991902959042938),
         "source": "testing/artifacts/x183b-20261006-175149/interface.json phases.H.windows[*].result_{server,client}"}
BAND = {"server_tps": (10.0, 0.2), "client_tps": (60.0, 0.5), "wmps": (1.6, 0.01)}
PRED = {
    "GUIDE": {"both clients": "SurvivalGuide.instance exists, isVisible false, tick box (the option) false"},
    "TUTORIALS": {"both clients": "options.ini search-tutorial and animal-zone keys false at ready and after the run"},
    "CHARINFO": {"both clients": "ISCharacterInfoWindow.instance getIsVisible true"},
    "CHAT": {"both clients": "no welcome marker in any chat tab, nor in the console"},
    "ADMIN_DBG": {"admin": "isDebugEnabled true, getDebug true, isShowLuaDebuggerOnError true (#3319)"},
    "BOB_DBG": {"bob": "isDebugEnabled false, getDebug false, getLuaDebuggerErrorCount 0 (#3297)"},
    "SPEED": {"getGameSpeed": 1, "tick.rate": "within x183b's band: server 10.0+-0.2, client 60.0+-0.5, wmps 1.6+-0.01"},
    "PANEL": {"both clients": "first key-39 press opens the panel, second closes it"},
    "MOODLES": {"both clients": "route set, stats.renders rises over 5 s, stats.errors 0"},
    "OPTIONS": {"after the run": "each client's options.ini holds the three keys false"},
    "WELCOME": {"server ini": "ServerWelcomeMessage= blank"},
    "EXIT": {"exit": 0, "verify": "all ok", "fault_reasons": []},
}


def free_gb():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip().splitlines()[-1])
    except Exception as e:                     # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def stray_clients():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ProjectZomboid64.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=60)
        return [ln for ln in r.stdout.splitlines() if "ProjectZomboid64" in ln]
    except Exception as e:                     # noqa: BLE001
        return [f"{type(e).__name__}: {e}"]


def sha256_file(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def read_options(path):
    """The three helper keys, the termsOfServiceVersion key, the line count, CRLF count and mtime of an options.ini."""
    out = {"path": path}
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        out["mtime"] = os.path.getmtime(path)
        out["bytes"] = len(raw)
        out["crlf"] = raw.count(b"\r\n")
        out["lines"] = raw.count(b"\n")
        text = raw.decode("utf-8", errors="replace")
        keys = {}
        for ln in text.splitlines():
            k, sep, v = ln.partition("=")
            if sep and k.strip() in HELPER_KEYS:
                keys.setdefault(k.strip(), []).append(v.strip())
        out["keys"] = keys
    except OSError as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def options_false(o):
    k = (o or {}).get("keys") or {}
    return all(k.get(h) == ["false"] for h in HELPER_KEYS)


class Run:
    def __init__(self):
        self.prof = profile.load(PROFILE)
        self.rec_fx = fx.load(self.prof.fixture)
        self.run_id, self.run_dir = new_run_dir(PREFIX)
        self.path = os.path.join(self.run_dir, ARTIFACT)
        self.tl, self.t0 = Timeline(), time.time()
        self.server, self.clients, self.started = None, {}, []
        self.cur = "pre"
        doctor_clean, doctor_text = doctor()
        self.doctor_clean = doctor_clean
        self.out = {
            "run_id": self.run_id, "driver": DRIVER, "users": list(self.prof.users), "profile": self.prof.report(),
            "fixture": {"name": self.rec_fx.get("name"), "provision_run": self.rec_fx.get("provision_run"),
                        "build": self.rec_fx.get("build")},
            "commit": git_say("rev-parse", "--short", "HEAD"),
            "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
            "mod_dirty_not_booted": git_dirty(MOD_DIR)[0],
            "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
            "harness_lua_dirty": git_dirty(LUA_DIR)[0],
            "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
            "harness_py_dirty": git_dirty("testing/pzt")[0],
            "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
            "host": {"free_gb_before_boot": free_gb(), "mem_min_gb": MEM_MIN_GB, "stray_clients": stray_clients()},
            "meta": {"staged_mod": STAGE_ROOT + "/Contents/mods/NutritionRevamp",
                     "baseline": X183B, "band": BAND, "x183b_build": "42.20.4 (x183b and x191 ran before 42.21)"},
            "predictions": PRED, "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "verdicts": {},
            "readings": {},
        }
        try:
            self.out["meta"]["staged_manifest_sha256"] = sha256_file(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME))
            self.out["meta"]["jar_bytes"] = os.path.getsize(GAME_JAR)
            with open(APP_MANIFEST, encoding="utf-8", errors="replace") as fh:
                m = re.search(r'"buildid"\s+"(\d+)"', fh.read())
            self.out["meta"]["steam_buildid"] = m.group(1) if m else None
        except OSError as e:
            self.out["meta"]["read_error"] = f"{type(e).__name__}: {e}"

    def wall(self):
        return round(time.time() - self.t0, 3)

    def note(self, msg):
        self.out["notes"].append({"wall": self.wall(), "phase": self.cur, "note": msg})

    def persist(self):
        try:
            self.out["timeline"] = list(self.tl.items)
            if self.server is not None:
                self.out["server_errors"] = self.server.errors[:30]
                self.out["server_error_count"] = len(self.server.errors)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.out, fh, indent=1, default=str)
            os.replace(tmp, self.path)
        except Exception as e:                     # noqa: BLE001
            print(f"could not write {self.path}: {type(e).__name__}: {e}")

    def step(self, name, side, cmd, args="", timeout=30):
        t_before = self.wall()
        try:
            v = ask(resolve_side(side, self.server, self.clients), cmd, args, timeout=timeout)
        except Exception as e:                     # noqa: BLE001
            v = {"error": f"{type(e).__name__}: {e}"}
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": self.cur, "wall_before": t_before,
               "wall_after": self.wall(), "ack": v}
        self.out["steps"].append(row)
        return v if isinstance(v, dict) else {"raw": v}

    def parked(self, user="admin"):
        c = self.clients.get(user) if isinstance(self.clients, dict) else None
        return c is not None and "lua_error" in getattr(c, "seen", {})

    def run_phase(self, name, fn):
        self.cur = name
        try:
            fn()
        except Exception as e:                     # noqa: BLE001
            self.out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
            self.tl.mark("error", failed_phase=name, detail=str(e)[:200])
        self.persist()

    # -- reads
    def guide(self, u, tag):
        s = SIDE[u]
        return {"instance": self.step(f"{tag}_{u}_guide", s, "lua.global", GUIDE),
                "isVisible": self.step(f"{tag}_{u}_guide_vis", s, "lua.callm", f"{GUIDE} isVisible"),
                "getIsVisible": self.step(f"{tag}_{u}_guide_gvis", s, "lua.callm", f"{GUIDE} getIsVisible"),
                "option_tickbox": self.step(f"{tag}_{u}_guide_tick", s, "lua.callm",
                                            f"{GUIDE}.showGuideTickBox isSelected 1")}

    def speed(self, u, tag):
        return self.step(f"{tag}_{u}_speed", SIDE[u], "lua.call", "getGameSpeed")

    def debug(self, u, tag):
        s = SIDE[u]
        return {"isDebugEnabled": self.step(f"{tag}_{u}_isdbg", s, "lua.call", "isDebugEnabled"),
                "getDebug": self.step(f"{tag}_{u}_getdbg", s, "lua.call", "getDebug"),
                "luaErrorCount": self.step(f"{tag}_{u}_errc", s, "lua.call", "getLuaDebuggerErrorCount"),
                "showLuaDebuggerOnError": self.step(f"{tag}_{u}_show", s, "lua.call",
                                                    "UIManager.isShowLuaDebuggerOnError")}

    def phase_A(self):
        P = self.out["phases"]["A"] = {}
        for u in USERS:
            s = SIDE[u]
            c = self.clients.get(u)
            P[u] = {
                "guide": self.guide(u, "A"),
                "charinfo": {"instance": self.step(f"A_{u}_ci", s, "lua.global", CHARINFO),
                             "getIsVisible": self.step(f"A_{u}_ci_vis", s, "lua.callm", f"{CHARINFO} getIsVisible")},
                "chat": self.step(f"A_{u}_chat", s, "lua.read", "ISChat.instance " + " ".join(CHAT_PATHS)),
                "speed": self.speed(u, "A"),
                "debug": self.debug(u, "A"),
                "options_at_ready": read_options(os.path.join(c.cache, "options.ini")) if c is not None else None,
                "layout_charinfo": self.layout_line(c),
            }

    def layout_line(self, c):
        if c is None:
            return None
        try:
            with open(os.path.join(c.cache, "Lua", "layout.ini"), encoding="utf-8", errors="replace") as fh:
                return [ln.strip() for ln in fh if "charinfowindow" in ln][:3]
        except OSError as e:
            return f"{type(e).__name__}: {e}"

    def phase_B(self):
        P = self.out["phases"]["B"] = {"windows": []}
        nodes = (("server", SRV), ("admin", "client"), ("bob", "client:bob"))
        for i in range(TICK_N):
            after = time.time()
            arms = {k: self.step(f"B{i}_arm_{k}", side, "tick.rate", str(TICK_S)) for k, side in nodes}
            w = {"i": i, "arms": arms}
            for k, side in nodes:
                res = None
                if arms[k].get("armed"):
                    try:
                        node = resolve_side(side, self.server, self.clients)
                        res = node.bus.wait_result(arms[k].get("result") or "tick-rate", timeout=TICK_S + 25,
                                                   after=after)
                    except Exception as e:         # noqa: BLE001
                        res = {"error": f"{type(e).__name__}: {e}"}
                w["result_" + k] = res
            P["windows"].append(w)
            self.persist()

    def phase_C(self):
        P = self.out["phases"]["C"] = {}
        for u in ("admin", "bob"):
            s = SIDE[u]
            R = P[u] = {}
            R["panel_stats0"] = self.step(f"C_{u}_ps0", s, "lua.read", f"{NR}.client.panel.stats opens closes keyPresses "
                                                                       "errors creates")
            R["vis0"] = self.step(f"C_{u}_vis0", s, "lua.callm", f"{INST} getIsVisible")
            R["press1"] = self.step(f"C_{u}_press1", s, "event.trigger", f"OnKeyPressed {KEY}")
            time.sleep(1.0)
            R["vis1"] = self.step(f"C_{u}_vis1", s, "lua.callm", f"{INST} getIsVisible")
            time.sleep(2.0)
            R["press2"] = self.step(f"C_{u}_press2", s, "event.trigger", f"OnKeyPressed {KEY}")
            time.sleep(1.0)
            R["vis2"] = self.step(f"C_{u}_vis2", s, "lua.callm", f"{INST} getIsVisible")
            R["panel_stats2"] = self.step(f"C_{u}_ps2", s, "lua.read", f"{NR}.client.panel.stats opens closes keyPresses "
                                                                       "errors creates")
            R["moodles0"] = self.step(f"C_{u}_m0", s, "lua.read", f"{NR}.client.moodles route stats.renders stats.errors "
                                                                  "stats.sets stats.columns stats.created")
            time.sleep(SETTLE_S)
            R["moodles1"] = self.step(f"C_{u}_m1", s, "lua.read", f"{NR}.client.moodles route stats.renders stats.errors "
                                                                  "stats.sets stats.columns stats.created")
            R["probe_energy"] = self.step(f"C_{u}_probe", s, "lua.call", f"{NR}.client.moodles.probe energy")
            if self.parked():
                return

    def phase_W(self):
        P = self.out["phases"]["W"] = {"watch_s": WATCH_S, "start": self.wall()}
        self.tl.mark("watch", seconds=WATCH_S)
        end = time.time() + WATCH_S
        while time.time() < end:
            if self.server is None or not self.server.alive or any(not c.alive for c in self.clients.values()):
                P["died"] = True
                break
            time.sleep(1.0)
        P["end"] = self.wall()
        for u in USERS:
            P[u] = {"guide": self.guide(u, "W"), "speed": self.speed(u, "W"), "debug": self.debug(u, "W")}

    # -- grading
    def grade(self):
        V, R = self.out["verdicts"], self.out["readings"]
        A = self.out["phases"].get("A") or {}
        W = self.out["phases"].get("W") or {}
        Z = self.out["phases"].get("Z") or {}

        def vd(ok, measured=True):
            return "unmeasured" if not measured else ("as_predicted" if ok else "falsified")

        # GUIDE
        g_obs, g_ok, g_meas = {}, True, True
        for u in USERS:
            for ph, src in (("A", A), ("W", W)):
                gd = (src.get(u) or {}).get("guide") or {}
                obs = {"type": (gd.get("instance") or {}).get("type"),
                       "isVisible": (gd.get("isVisible") or {}).get("r1"),
                       "getIsVisible": (gd.get("getIsVisible") or {}).get("r1"),
                       "option_tickbox": (gd.get("option_tickbox") or {}).get("r1")}
                g_obs[f"{u}_{ph}"] = obs
                if obs["type"] is None:
                    g_meas = False
                g_ok = g_ok and obs["type"] == "table" and obs["isVisible"] is False and obs["option_tickbox"] is False
        V["GUIDE"] = {"predicted": PRED["GUIDE"], "observed": g_obs, "verdict": vd(g_ok, g_meas)}
        # TUTORIALS and OPTIONS
        t_obs, t_ok = {}, True
        for u in USERS:
            for when, o in (("ready", (A.get(u) or {}).get("options_at_ready")), ("after", (Z.get("options") or {}).get(u))):
                k = (o or {}).get("keys") or {}
                t_obs[f"{u}_{when}"] = {h: k.get(h) for h in HELPER_KEYS[1:]}
                t_ok = t_ok and all(k.get(h) == ["false"] for h in HELPER_KEYS[1:])
        V["TUTORIALS"] = {"predicted": PRED["TUTORIALS"], "observed": t_obs, "verdict": vd(t_ok)}
        o_obs = {u: {"keys": ((Z.get("options") or {}).get(u) or {}).get("keys"),
                     "written_after_launch": ((Z.get("options") or {}).get(u) or {}).get("written_after_launch"),
                     "crlf": ((Z.get("options") or {}).get(u) or {}).get("crlf"),
                     "lines": ((Z.get("options") or {}).get(u) or {}).get("lines")} for u in USERS}
        V["OPTIONS"] = {"predicted": PRED["OPTIONS"], "observed": o_obs,
                        "verdict": vd(all(options_false((Z.get("options") or {}).get(u)) for u in USERS),
                                      bool(Z.get("options")))}
        # CHARINFO
        c_obs = {u: {"type": (((A.get(u) or {}).get("charinfo") or {}).get("instance") or {}).get("type"),
                     "getIsVisible": (((A.get(u) or {}).get("charinfo") or {}).get("getIsVisible") or {}).get("r1"),
                     "layout": (A.get(u) or {}).get("layout_charinfo")} for u in USERS}
        V["CHARINFO"] = {"predicted": PRED["CHARINFO"], "observed": c_obs,
                         "verdict": vd(all(c_obs[u]["getIsVisible"] is True for u in USERS),
                                       all(c_obs[u]["type"] == "table" for u in USERS))}
        # CHAT
        ch_obs, ch_ok, ch_meas = {}, True, True
        for u in USERS:
            ch = (A.get(u) or {}).get("chat") or {}
            vals = ch.get("values") or {}
            texts = {p: vals.get(p) for p in CHAT_PATHS if isinstance(vals.get(p), str)}
            hits = [p for p, t in texts.items() if WELCOME_RX.search(t)]
            con = (Z.get("console_welcome") or {}).get(u)
            ch_obs[u] = {"ok": ch.get("ok"), "texts_len": {p: len(t) for p, t in texts.items()}, "hits": hits,
                         "tables": ch.get("tables"), "missing": ch.get("missing"), "console_hits": con}
            if ch.get("ok") is not True:
                ch_meas = False
            ch_ok = ch_ok and not hits and not con
        V["CHAT"] = {"predicted": PRED["CHAT"], "observed": ch_obs, "verdict": vd(ch_ok, ch_meas)}
        # debug flags
        def dbg(u, ph="A"):
            src = A if ph == "A" else W
            d = (src.get(u) or {}).get("debug") or {}
            return {k: (d.get(k) or {}).get("r1") for k in ("isDebugEnabled", "getDebug", "luaErrorCount",
                                                            "showLuaDebuggerOnError")}
        ad, adw = dbg("admin"), dbg("admin", "W")
        V["ADMIN_DBG"] = {"predicted": PRED["ADMIN_DBG"], "observed": {"A": ad, "W": adw},
                          "verdict": vd(all(x["isDebugEnabled"] is True and x["getDebug"] is True
                                            and x["showLuaDebuggerOnError"] is True for x in (ad, adw)))}
        bd, bdw = dbg("bob"), dbg("bob", "W")
        V["BOB_DBG"] = {"predicted": PRED["BOB_DBG"], "observed": {"A": bd, "W": bdw},
                        "verdict": vd(all(x["isDebugEnabled"] is False and x["getDebug"] is False
                                          and x["luaErrorCount"] == 0 for x in (bd, bdw)))}
        # SPEED
        B = self.out["phases"].get("B") or {}
        rows = []
        for w in B.get("windows") or []:
            row = {"i": w.get("i")}
            for k in ("server", "admin", "bob"):
                r = w.get("result_" + k) or {}
                row[k] = {"tps": r.get("ticksPerSecond"), "wmps": r.get("worldMinutesPerSecond")}
            rows.append(row)
        speeds = {f"{u}_{ph}": (((src.get(u) or {}).get("speed") or {}).get("r1"))
                  for u in USERS for ph, src in (("A", A), ("W", W))}
        moved = []
        for row in rows:
            for k in ("server", "admin", "bob"):
                tps, wm = num(row[k]["tps"]), num(row[k]["wmps"])
                c, b = BAND["server_tps"] if k == "server" else BAND["client_tps"]
                if tps is None or abs(tps - c) > b:
                    moved.append({"i": row["i"], "side": k, "tps": tps})
                if wm is None or abs(wm - BAND["wmps"][0]) > BAND["wmps"][1]:
                    moved.append({"i": row["i"], "side": k, "wmps": wm})
        R["tick_rate"] = rows
        R["game_speed"] = speeds
        V["SPEED"] = {"predicted": PRED["SPEED"], "observed": {"getGameSpeed": speeds, "windows": rows,
                                                               "outside_band": moved, "x183b": X183B},
                      "verdict": vd(not moved and all(v == 1 for v in speeds.values()), bool(rows))}
        # PANEL
        C = self.out["phases"].get("C") or {}
        p_obs, p_ok = {}, bool(C)
        for u in ("admin", "bob"):
            c = C.get(u) or {}
            p_obs[u] = {"vis0": (c.get("vis0") or {}).get("r1"), "vis1": (c.get("vis1") or {}).get("r1"),
                        "vis2": (c.get("vis2") or {}).get("r1"),
                        "stats0": (c.get("panel_stats0") or {}).get("values"),
                        "stats2": (c.get("panel_stats2") or {}).get("values")}
            p_ok = p_ok and p_obs[u]["vis0"] is False and p_obs[u]["vis1"] is True and p_obs[u]["vis2"] is False
        V["PANEL"] = {"predicted": PRED["PANEL"], "observed": p_obs, "verdict": vd(p_ok, bool(C))}
        # MOODLES
        m_obs, m_ok = {}, bool(C)
        for u in ("admin", "bob"):
            c = C.get(u) or {}
            m0, m1 = (c.get("moodles0") or {}).get("values") or {}, (c.get("moodles1") or {}).get("values") or {}
            pr = c.get("probe_energy") or {}
            m_obs[u] = {"route": m1.get("route"), "renders0": m0.get("stats.renders"), "renders1": m1.get("stats.renders"),
                        "errors": m1.get("stats.errors"), "columns": m1.get("stats.columns"),
                        "created": m1.get("stats.created"), "probe": {k: pr.get(k) for k in ("r1", "r2", "r3")}}
            r0, r1 = num(m0.get("stats.renders")), num(m1.get("stats.renders"))
            m_ok = (m_ok and m1.get("route") not in (None, "none") and r0 is not None and r1 is not None and r1 > r0
                    and m1.get("stats.errors") == 0)
        V["MOODLES"] = {"predicted": PRED["MOODLES"], "observed": m_obs, "verdict": vd(m_ok, bool(C))}
        # WELCOME
        wl = Z.get("server_welcome_lines")
        V["WELCOME"] = {"predicted": PRED["WELCOME"], "observed": wl,
                        "verdict": vd(wl == ["ServerWelcomeMessage="], wl is not None)}

    def phase_Z(self, every, launch_epoch):
        P = self.out["phases"]["Z"] = {"options": {}, "console_welcome": {}}
        for c in every:
            u = getattr(c, "username", "?")
            o = read_options(os.path.join(c.cache, "options.ini"))
            o["written_after_launch"] = (o.get("mtime") or 0) > launch_epoch
            P["options"][u] = o
            hits = []
            try:
                with open(c.console, encoding="utf-8", errors="replace") as fh:
                    for ln in fh:
                        if WELCOME_RX.search(ln) and "PZTK" not in ln:
                            hits.append(ln.strip()[:300])
            except OSError as e:
                hits = [f"{type(e).__name__}: {e}"]
            P["console_welcome"][u] = hits[:10]
        lines = None
        if self.server is not None:
            try:
                with open(self.server.ini, encoding="utf-8", errors="replace") as fh:
                    lines = [ln.rstrip("\r\n") for ln in fh if ln.startswith("ServerWelcomeMessage")]
            except OSError as e:
                lines = [f"{type(e).__name__}: {e}"]
        P["server_welcome_lines"] = lines

    def run(self):
        if not self.doctor_clean:
            self.out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
            self.persist()
            print("\n".join(self.out["doctor"]))
            return 1
        fg = self.out["host"]["free_gb_before_boot"]
        if not isinstance(fg, float) or fg < MEM_MIN_GB:
            self.out["error"] = f"free host memory {fg} GB under {MEM_MIN_GB}: not booted (CLAUDE.md s5)"
            self.persist()
            print(self.out["error"])
            return 1
        lint_errors = lint_paths(self.prof.sources)
        self.out["lint_errors"] = lint_errors
        if lint_errors:
            self.out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
            self.persist()
            return 1
        copied = []
        try:
            shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(self.run_dir, MANIFEST_NAME))
            copied.append(MANIFEST_NAME)
        except OSError as e:
            self.out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
        launch_epoch = time.time()
        faults = None
        try:
            self.server = make_server(self.run_dir, self.rec_fx, mods=self.prof.mods, mod_sources=self.prof.sources,
                                      mod_skip=self.prof.skip, sandbox=self.prof.sandbox or None, ini=self.prof.ini)
            self.server.start(timeout=self.prof.server_timeout)
            self.out["server_started_wall"] = self.wall()
            self.tl.mark("server_started")
            self.clients = attach_clients(self.run_dir, self.prof, self.server, self.rec_fx, self.tl,
                                          started=self.started)
            self.tl.mark("session_ready")
            self.out["session_ready_wall"] = self.wall()
            self.out["build"] = self.server.build
            self.out["verify"] = verify(self.prof, self.server, self.clients, self.tl)
            self.persist()
            for name, fn in (("A", self.phase_A), ("B", self.phase_B), ("C", self.phase_C), ("W", self.phase_W)):
                if self.parked():
                    self.out["abort"] = f"admin parked in the debugger before phase {name}"
                    break
                self.run_phase(name, fn)
        except Exception as e:                     # noqa: BLE001
            self.out["error"], self.out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
            self.tl.mark("error", detail=str(e)[:200])
        finally:
            every = list(self.started)
            try:
                if self.server is not None:
                    teardown(self.tl, self.server, [c for c in every if c.alive])
            except Exception as e:                 # noqa: BLE001
                self.out["teardown_error"] = f"{type(e).__name__}: {e}"
            finally:
                if self.server is not None:
                    hard_kill(self.server, every)
                self.out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                                           for i, c in enumerate(every)]
                self.out["host"]["free_gb_after"] = free_gb()
                try:
                    if self.server is not None:
                        faults = fault_reasons(self.server, every)
                        self.out["fault_reasons"] = faults
                        self.out["server_errors"] = self.server.errors[:30]
                        self.out["server_error_count"] = len(self.server.errors)
                except Exception as e:             # noqa: BLE001
                    self.out["fault_reasons_error"] = f"{type(e).__name__}: {e}"
                self.cur = "Z"
                try:
                    self.phase_Z(every, launch_epoch)
                except Exception as e:             # noqa: BLE001
                    self.out["phase_errors"]["Z"] = {"error": f"{type(e).__name__}: {e}"}
                vr = self.out.get("verify") or []
                exit_ok = (bool(vr) and all(v.get("ok") for v in vr) and faults == [] and not self.parked()
                           and not self.out.get("error") and not self.out["phase_errors"])
                self.out["exit_code"] = 0 if exit_ok else 1
                try:
                    self.grade()
                except Exception as e:             # noqa: BLE001
                    self.out["grade_error"] = f"{type(e).__name__}: {e}"
                    self.out["grade_traceback"] = traceback.format_exc()[-3000:]
                self.out["verdicts"]["EXIT"] = {"predicted": PRED["EXIT"],
                                                "observed": {"exit_code": self.out["exit_code"],
                                                             "verify_ok": [v.get("ok") for v in vr],
                                                             "fault_reasons": faults,
                                                             "phase_errors": list(self.out["phase_errors"])},
                                                "verdict": "as_predicted" if exit_ok else "falsified"}
                self.out["copied"] = copied
                self.out["wall_seconds"] = round(time.time() - self.t0, 1)
                self.persist()
                dest = os.path.join(REPO, "testing", "artifacts", self.run_id)
                try:
                    os.makedirs(dest, exist_ok=True)
                    shutil.copyfile(self.path, os.path.join(dest, ARTIFACT))
                    for f in copied:
                        shutil.copyfile(os.path.join(self.run_dir, f), os.path.join(dest, f))
                    print(f"copied to {dest}")
                except Exception as e:             # noqa: BLE001
                    print(f"could not copy to {dest}: {type(e).__name__}: {e}")
        print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in self.out["verdicts"].items()},
                          "exit_code": self.out.get("exit_code"), "error": self.out.get("error"),
                          "grade_error": self.out.get("grade_error"), "phase_errors": list(self.out["phase_errors"]),
                          "wall_seconds": self.out.get("wall_seconds"), "run_id": self.run_id,
                          "run_dir": self.run_dir}, indent=1, default=str))
        return self.out.get("exit_code", 1)


if __name__ == "__main__":
    sys.exit(Run().run())
