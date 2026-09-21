import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bus_inventory as bi

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bus_inventory.py")

SHARED = """function TK.register(name, fn) TK.commands[name] = fn end

-- an older comment line
-- @args (none)
-- @reply {ok, side}
-- @purpose Liveness check; answers on both sides.
TK.register("ping", function() return { ok = true } end)
"""
SERVER = """-- @purpose Read the player's Nutrition object.
-- @args <user>
-- @reply {calories, carbs, lipids, proteins, weight}
TK.register("nutrition.get", function(argv) return TK.nutritionSnapshot(findPlayer(argv[1])) end)

-- @args <user> <field> <value>
-- @purpose Server-side stats write.
TK.register("stats.set", function(argv) return 1 end)
"""
CLIENT = """-- @args (none)
-- @reply {calories, carbs, lipids, proteins, weight}
-- @purpose Read the local player's Nutrition copy.
TK.register("nutrition.get", function() return TK.nutritionSnapshot(getPlayer()) end)
"""

def _tree(d, server=SERVER):
    for side, text in (("shared", SHARED), ("server", server), ("client", CLIENT)):
        os.makedirs(os.path.join(d, side), exist_ok=True)
        open(os.path.join(d, side, "PZTestKit_%s.lua" % side.title()), "w", encoding="utf-8").write(text)
    return d

def test_scan_reads_blocks_and_reports_missing_keys():
    with tempfile.TemporaryDirectory() as d:
        sites = bi.scan(_tree(d))
        by = {(s["name"], s["side"]): s for s in sites}
        assert len(sites) == 4 and by[("ping", "shared")]["purpose"] == "Liveness check; answers on both sides."
        assert by[("nutrition.get", "server")]["args"] == "<user>" and by[("nutrition.get", "client")]["args"] == "(none)"
        assert by[("stats.set", "server")]["missing"] == ["reply"]
        assert by[("ping", "shared")]["file"] == "shared/PZTestKit_Shared.lua" and by[("ping", "shared")]["line"] == 7

def test_render_is_sorted_and_escapes_pipes():
    with tempfile.TemporaryDirectory() as d:
        sites = [s for s in bi.scan(_tree(d)) if not s["missing"]]
        sites[0]["purpose"] = "a | b"
        text = bi.render(sites, "lua")
        lines = [l for l in text.splitlines() if l.startswith("| `")]
        assert [l.split("|")[1].strip() for l in lines] == ["`nutrition.get`", "`nutrition.get`", "`ping`"]
        assert "server" in lines[0] and "client" in lines[1] and "a \\| b" in text
        assert "3 sites, 2 names" in text

def test_cli_fails_on_missing_key_and_checks_drift():
    with tempfile.TemporaryDirectory() as d:
        _tree(d); out = os.path.join(d, "harness-commands.md")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True)
        assert r.returncode == 1 and "stats.set" in r.stderr and "reply" in r.stderr
        good = SERVER.replace("-- @purpose Server-side stats write.", "-- @reply string\n-- @purpose Server-side stats write.")
        _tree(d, server=good)
        assert subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True).returncode == 0
        assert subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True).returncode == 0
        open(out, "a", encoding="utf-8").write("| `zzz` | server | `x:1` | a | b | c |\n")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True)
        assert r.returncode == 1 and "drift" in (r.stdout + r.stderr)
