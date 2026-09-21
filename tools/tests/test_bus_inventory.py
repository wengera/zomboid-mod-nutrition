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

# --- fix round 1: the label, comment lines, nested side dirs, and the run's boundaries ----------

SERVER_OK = SERVER.replace("-- @args <user> <field> <value>", "-- @reply string\n-- @args <user> <field> <value>")

NESTED = """-- @args (none)
-- @reply {ok}
-- @purpose A scenario command, registered below the side dir.
TK.register("scenario.run", function() return { ok = true } end)
"""

COMMENTED = """-- @args <stale>
-- @reply {stale}
-- @purpose The command that used to live here.
-- TK.register("disabled.old", function() return 1 end)
-- @args <user>
-- @purpose The live one.
TK.register("live.now", function() return 1 end)
"""

EDGES = """-- @args <far>
-- @reply {far}
-- @purpose Far, behind a blank line.

-- @args <near>
-- @reply {near}
-- @purpose Near.
-- @args <nearest>
TK.register("nearest.wins", function() return 1 end)

local helper = 1
-- @args (none)
TK.register("code.ends.the.run", function() return helper end)
"""

def _one(d, side, name, text):
    os.makedirs(os.path.join(d, side), exist_ok=True)
    open(os.path.join(d, side, name), "w", encoding="utf-8").write(text)
    return d

def test_label_for_is_one_label_for_every_caller():
    """The checker renders too (rule 5): a raw relpath gives backslashes here and a false drift."""
    assert bi.label_for(bi.LUA_DIR) == "testing/PZTestKit/PZTestKit/42/media/lua"
    assert bi.label_for(bi.LUA_DIR + os.sep) == "testing/PZTestKit/PZTestKit/42/media/lua"
    here = os.getcwd()
    assert bi.label_for(os.path.join(".", "a", "b") + os.sep, root=here) == "a/b"
    assert bi.label_for(os.path.join("a", "b"), root=here) == "a/b"
    if os.name == "nt":  # relpath raises only across Windows drives; on POSIX the branch is unreachable
        other = ("E:" if os.path.splitdrive(bi.REPO_ROOT)[0].upper() == "D:" else "D:") + "\\harness\\lua"
        assert bi.label_for(other) == other.replace("\\", "/")

def test_cli_renders_the_same_bytes_from_a_relative_lua_dir():
    with tempfile.TemporaryDirectory() as d:
        _tree(d, server=SERVER_OK)
        a_out, r_out = os.path.join(d, "abs.md"), os.path.join(d, "rel.md")
        subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", a_out], check=True)
        subprocess.run([sys.executable, CLI, "--lua-dir", "." + os.sep + os.path.basename(d) + os.sep, "--out", r_out],
                       cwd=os.path.dirname(d), check=True)
        # read before asserting: a failing assert keeps the file object alive and Windows then
        # fails the tempdir cleanup, hiding the comparison
        from_abs, from_rel = open(a_out, encoding="utf-8").read(), open(r_out, encoding="utf-8").read()
        assert from_abs == from_rel

def test_a_commented_out_registration_is_not_a_site_and_its_block_does_not_leak():
    with tempfile.TemporaryDirectory() as d:
        sites = bi.scan(_one(d, "server", "PZTestKit_Server.lua", COMMENTED))
        assert [s["name"] for s in sites] == ["live.now"] and sites[0]["line"] == 7
        assert sites[0]["args"] == "<user>" and sites[0]["purpose"] == "The live one."
        assert sites[0]["missing"] == ["reply"] and "stale" not in "".join(sites[0][k] for k in ("args", "reply", "purpose"))

def test_nearest_key_wins_and_a_blank_or_code_line_ends_the_run():
    with tempfile.TemporaryDirectory() as d:
        by = {s["name"]: s for s in bi.scan(_one(d, "shared", "PZTestKit_Edges.lua", EDGES))}
        near = by["nearest.wins"]
        assert (near["args"], near["reply"], near["purpose"], near["missing"]) == ("<nearest>", "{near}", "Near.", [])
        assert "far" not in "".join(near[k] for k in ("args", "reply", "purpose"))
        ends = by["code.ends.the.run"]
        assert ends["args"] == "(none)" and ends["missing"] == ["reply", "purpose"]

def test_scan_reaches_a_nested_side_dir_and_files_are_relative_to_the_lua_dir():
    with tempfile.TemporaryDirectory() as d:
        _tree(d)
        _one(os.path.join(d, "server"), "scenarios", "PZTestKit_Scenario_X.lua", NESTED)
        by = {(s["name"], s["side"]): s for s in bi.scan(d)}
        assert len(by) == 5 and by[("scenario.run", "server")]["missing"] == []
        assert by[("scenario.run", "server")]["file"] == "server/scenarios/PZTestKit_Scenario_X.lua"
        assert by[("ping", "shared")]["file"] == "shared/PZTestKit_Shared.lua"  # a top-level file is unchanged

def test_cli_writes_nothing_on_a_missing_key_and_check_accepts_a_crlf_copy():
    with tempfile.TemporaryDirectory() as d:
        _tree(d); out = os.path.join(d, "harness-commands.md")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True)
        assert r.returncode == 1 and not os.path.exists(out)  # a failing run leaves no half-true table
        _tree(d, server=SERVER_OK)
        assert subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True).returncode == 0
        body = open(out, encoding="utf-8", newline="").read()
        assert "\r\n" not in body
        open(out, "w", encoding="utf-8", newline="\r\n").write(body)  # as core.autocrlf checks it out
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True)
        assert r.returncode == 0 and "in sync" in r.stdout
        open(out, "a", encoding="utf-8").write("| `zzz` | server | `x:1` | a | b | c |\n")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True)
        assert r.returncode == 1 and "drift" in r.stderr and r.stdout == ""  # every failure goes to stderr
