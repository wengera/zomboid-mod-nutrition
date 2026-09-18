import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import luabalance

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "luabalance.py")

def _write(d, name, text):
    p = os.path.join(d, name); open(p, "w", encoding="utf-8").write(text); return p

def test_balanced_file_reports_balanced():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "ok.lua", "-- a comment with an unmatched ( and a [[\nlocal t = { a = 1, s = \"}\" }\nfunction f(x) if x then return { } end end\n")
        assert luabalance.report(p)[6] == "BALANCED"

def test_missing_function_line_is_unbalanced():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "bad.lua", "local x = 1\n  if x then return x end\nend\n")
        name, b, par, s, depth, neg, verdict = luabalance.report(p)
        assert verdict == "UNBALANCED" and depth == -1 and neg == 1

def test_cli_exit_code_follows_verdict():
    with tempfile.TemporaryDirectory() as d:
        ok = _write(d, "ok.lua", "function f() end\n")
        bad = _write(d, "bad.lua", "end\n")
        assert subprocess.run([sys.executable, CLI, ok], capture_output=True).returncode == 0
        assert subprocess.run([sys.executable, CLI, ok, bad], capture_output=True).returncode == 1
