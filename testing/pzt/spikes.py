"""Spikes S3–S7: scripted experiments against a real session. Each returns a findings
dict; `pzt spike ...` writes them to runs/<id>/findings.json and prints them.

S3 mods under -nosteam     S4 result channel     S5 time acceleration
S6 sync witness            S7 reloadlua
"""
import json
import os
import re
import time

from . import fixture as fx
from .bus import parse_ack
from .paths import new_run_dir
from .session import (Timeline, grep_file, make_client, make_server, say, teardown,
                      write_report)

S3_MOD = "KeenPerception"      # 1 KB shared-lua workshop mod (item 3685392864), no dependencies
S3_MOD_RX = re.compile(r"KeenPerception|mod .*not found|missing mod|required mod|workshop", re.I)

# grep_file lives in session.py (the run's missing-mod fail-fast greps the server log with it)
# and is re-exported here for the spikes' own use: one definition, two callers.


def ack(result):
    return parse_ack(result)[1]


# ---- S3 ---------------------------------------------------------------------
def s3(a):
    """Does a mod that exists only in the Steam workshop folder load under -nosteam?
    Bytecode says no (both workshop roots need SteamUtils.isSteamModeEnabled); measure."""
    rec = fx.load(a.fixture)
    mods = rec["server"]["mods"] + [S3_MOD]
    out = {"static": "ZomboidFileSystem.getAllModFolders: the 'workshop' (staged) and 'steam' "
                     "(installed items) roots both require SteamUtils.isSteamModeEnabled, so under "
                     "-nosteam only <cachedir>/mods is searched"}
    for label, workshop in (("A_workshop_only", False), ("B_copied_into_mods", True)):
        run_id, run_dir = new_run_dir("s3")
        tl = Timeline()
        say(f"\nS3 {label}: run {run_dir}")
        v = {"run": run_id, "copied": workshop}
        clients = []
        server = make_server(run_dir, rec, mods=mods, workshop=workshop)
        v["server_mods_dir"] = sorted(os.listdir(os.path.join(server.cache, "mods")))
        try:
            server.start(timeout=a.server_timeout)
            tl.mark("server_started", t=server.t_started)
            v["server_trait_check"] = ack(server.send("trait.check"))
            c, _ = make_client(run_dir, "admin", server, rec, workshop=workshop)
            c.start()
            clients.append(c)
            try:
                v["client_ready_t"] = c.wait_ready(timeout=a.s3_client_timeout)
                v["client_trait_check"] = ack(c.send("trait.check"))
            except (TimeoutError, RuntimeError) as e:
                v["client_ready_t"] = None
                v["client_error"] = str(e)[:300]
            v["client_log"] = grep_file(c.console, S3_MOD_RX)
        except (TimeoutError, RuntimeError) as e:
            v["server_error"] = str(e)[:300]
        finally:
            teardown(tl, server, clients)
            for c in clients:
                c.kill()
        v["server_log"] = grep_file(server.log_path, S3_MOD_RX)
        v["server_errors"] = server.errors[:6]
        out[label] = v
    return out


# ---- S4 ---------------------------------------------------------------------
def s4(a, server, client, tl):
    """Result channel: harness writes JSON into Lua/pzt-results/ on both sides."""
    out = {}
    for side, node in (("client", client), ("server", server)):
        t = time.time()
        r = node.send("result", f"s4_{side} hello")
        doc = node.bus.wait_result(f"s4_{side}", timeout=15, after=t - 0.2)
        out[side] = {"ack": r, "latency_s": round(time.time() - t, 2),
                     "path": os.path.join(node.bus.results_dir, f"s4_{side}.json"), "doc": doc}
    out["note"] = ("getFileWriter accepts a subfolder under <cachedir>/Lua and 'json' is in "
                   "LuaManager.ALLOWED_FILE_EXTENSIONS; a complete JSON object is the ready "
                   "signal (no marker file: '.ready' is not an allowed extension)")
    return out


# ---- S5 ---------------------------------------------------------------------
def _snap(server, client):
    return {"wall": time.time(), "server": ack(server.send("time.snapshot")),
            "client": ack(client.send("time.snapshot")), "stats": ack(client.send("player.stats"))}


def _rates(a, b):
    dt = b["wall"] - a["wall"]

    def hours(side):
        return float(b[side]["worldAge"]) - float(a[side]["worldAge"])
    return {"wall_s": round(dt, 1),
            "server_game_min_per_wall_s": round(hours("server") * 60 / dt, 2),
            "client_game_min_per_wall_s": round(hours("client") * 60 / dt, 2),
            "server_mult": b["server"]["mult"], "client_mult": b["client"]["mult"],
            "calories_delta": round(float(b["stats"]["calories"]) - float(a["stats"]["calories"]), 2),
            "weight_delta": round(float(b["stats"]["weight"]) - float(a["stats"]["weight"]), 4)}


def s5(a, server, client, tl):
    """Time acceleration in MP: `settimespeed <x>` (RCON) = GameTime.setMultiplier on the
    server + SetMultiplierPacket to every client. Does the client follow, does nutrition
    tick faster, do the clocks stay together? (RCON `help` is deliberately not used: its
    reply formatting throws MissingFormatArgumentException inside the server.)"""
    out = {}
    base0 = _snap(server, client)
    time.sleep(15)
    base1 = _snap(server, client)
    out["baseline_1x"] = _rates(base0, base1)
    ok, rep = server.rcon("settimespeed 30")
    out["rcon_settimespeed_30"] = (ok, rep[:120])
    tl.mark("s5_settimespeed", x=30, reply=rep[:60])
    time.sleep(1.5)
    s, c = ack(server.send("time.snapshot")), ack(client.send("time.snapshot"))
    # getMultiplier() is scaled (4.8 at 1x on the server, 0.8 on the client): compare ratios
    out["getMultiplier"] = {"server_1x": base1["server"]["mult"], "client_1x": base1["client"]["mult"],
                            "server_30x": s["mult"], "client_30x": c["mult"],
                            "server_ratio": round(float(s["mult"]) / float(base1["server"]["mult"]), 2),
                            "client_ratio": round(float(c["mult"]) / float(base1["client"]["mult"]), 2)}
    fast0 = _snap(server, client)
    time.sleep(30)
    out["accelerated_30x"] = _rates(fast0, _snap(server, client))
    ok, rep = server.rcon("settimespeed 1")
    out["rcon_settimespeed_1"] = (ok, rep[:120])
    time.sleep(1.5)
    r0 = _snap(server, client)
    time.sleep(10)
    r1 = _snap(server, client)
    out["restored_1x"] = _rates(r0, r1)
    out["clock_offset_game_h_client_minus_server"] = round(float(r1["client"]["worldAge"]) - float(r1["server"]["worldAge"]), 3)
    return out


# ---- S6 ---------------------------------------------------------------------
def _witness(client, cmd, args, name):
    t = time.time()
    r = client.send(cmd, args)
    doc = client.bus.wait_result(name, timeout=20, after=t - 0.2)
    return {"ack": r, "match": doc.get("match"), "server": doc.get("server"), "client": doc.get("client")}


def s6(a, server, client, tl):
    """Sync witness: client view vs server view for player modData, nutrition, and an item's
    condition/conditionMax/modData after the game's own item sync."""
    out = {}
    client.send("moddata.set", "pzt_probe v1")
    out["moddata_before_transmit"] = _witness(client, "witness.sync.moddata", "pzt_probe", "witness_moddata_pzt_probe")
    out["transmit_ack"] = client.send("moddata.transmit")
    time.sleep(2)
    out["moddata_after_transmit"] = _witness(client, "witness.sync.moddata", "pzt_probe", "witness_moddata_pzt_probe")
    out["nutrition"] = _witness(client, "witness.nutrition", "", "witness_nutrition")
    ok, rep = server.rcon('additem "admin" "Base.Apple" 1')
    out["rcon_additem"] = (ok, rep[:200])
    time.sleep(3)
    out["item_server_spawned"] = _witness(client, "witness.item", "Base.Apple", "witness_item")
    out["tamper_ack"] = client.send("item.tamper", "Base.Apple 5 3 tag1")
    time.sleep(3)
    out["item_after_tamper"] = _witness(client, "witness.item", "Base.Apple", "witness_item")
    out["client_spawn_ack"] = client.send("item.spawn", "Base.Carrots")
    time.sleep(3)
    out["item_client_spawned"] = _witness(client, "witness.item", "Base.Carrots", "witness_item")
    # "never" or "not yet"? give any periodic inventory sync a minute, then look again
    tl.mark("s6_wait_for_periodic_sync", seconds=60)
    time.sleep(60)
    out["item_after_tamper_60s"] = _witness(client, "witness.item", "Base.Apple", "witness_item")
    out["item_client_spawned_60s"] = _witness(client, "witness.item", "Base.Carrots", "witness_item")
    out["server_players"] = ack(server.send("players"))
    return out


# ---- S7 ---------------------------------------------------------------------
CORE_REL = os.path.join("mods", "PZTestKit", "42", "media", "lua", "shared", "PZTestKit_Core.lua")


def _bump_version(cache, new):
    path = os.path.join(cache, CORE_REL)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    src = re.sub(r"TK\.version = \d+", f"TK.version = {new}", src, count=1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    return path


def s7(a, server, client, tl):
    """Hot reload: server `reloadlua <file>` (RCON) and client `reloadLuaFile(...)`;
    what state survives (TK is a global, so its counters should)."""
    out = {"server_before": ack(server.send("state")), "client_before": ack(client.send("state"))}
    _bump_version(server.cache, 2)
    ok, rep = server.rcon("reloadlua PZTestKit_Core.lua")
    out["rcon_reloadlua"] = (ok, rep[:200])
    time.sleep(2)
    out["server_after"] = ack(server.send("state"))
    out["client_after_server_reload"] = ack(client.send("state"))
    path = _bump_version(client.cache, 3)
    attempts = []
    for arg in ("PZTestKit_Core.lua", path.replace("\\", "/")):
        r = client.send("lua.reload", arg)
        time.sleep(1.5)
        st = ack(client.send("state"))
        attempts.append({"arg": arg, "ack": r, "state": st})
        if isinstance(st, dict) and st.get("version") == 3:
            break
    out["client_reload_attempts"] = attempts
    out["reloadalllua"] = None
    if a.reloadalllua:
        ok, rep = server.rcon("reloadalllua")
        time.sleep(5)
        out["reloadalllua"] = {"rcon": (ok, rep[:200]), "server_state": ack(server.send("state")),
                               "server_alive": server.alive}
    return out


# ---- runner -----------------------------------------------------------------
SESSION_SPIKES = {"S4": s4, "S5": s5, "S6": s6, "S7": s7}


def run(a):
    ids = [s.upper() for s in a.ids]
    findings = {}
    if "S3" in ids:
        findings["S3"] = s3(a)
    session_ids = [s for s in ids if s in SESSION_SPIKES]
    if session_ids:
        rec = fx.load(a.fixture)
        run_id, run_dir = new_run_dir("spike")
        tl = Timeline()
        say(f"\nsession spikes {session_ids}: run {run_dir}")
        server = make_server(run_dir, rec)
        clients = []
        try:
            server.start(timeout=a.server_timeout)
            tl.mark("server_started", t=server.t_started)
            c, _ = make_client(run_dir, "admin", server, rec)
            c.start()
            clients.append(c)
            tl.mark("client_ready", t=c.wait_ready(timeout=a.client_timeout))
            for sid in session_ids:
                tl.mark(f"{sid}_start")
                try:
                    findings[sid] = SESSION_SPIKES[sid](a, server, c, tl)
                except Exception as e:  # keep going: one spike's failure is itself a finding
                    findings[sid] = {"error": repr(e)[:400]}
                    tl.mark(f"{sid}_error", detail=str(e)[:160])
                tl.mark(f"{sid}_done")
        finally:
            teardown(tl, server, clients)
            for c in clients:
                c.kill()
        findings["_session"] = {"run": run_id, "timeline": tl.items, "server_errors": server.errors[:20],
                                "results": {"server": server.results(),
                                            "client": clients[0].results() if clients else {}}}
        write_report(run_dir, {"run_id": run_id, "findings": findings})
        with open(os.path.join(run_dir, "findings.json"), "w") as fh:
            json.dump(findings, fh, indent=1)
        say(f"\nfindings: {os.path.join(run_dir, 'findings.json')}")
    say(json.dumps({k: v for k, v in findings.items() if k != "_session"}, indent=1, default=str))
    return 0
