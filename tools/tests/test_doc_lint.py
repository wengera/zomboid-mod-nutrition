import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import doc_lint

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "doc_lint.py")

def _write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text); return p

def test_stamp_and_sources_required():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nbody TODO\n")
        rules = {f.rule for f in doc_lint.lint([d])}
        assert {"stamp", "placeholder", "sources"} <= rules

def test_clean_doc_passes():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5), 2026-09-09\n\n| Item | Ev |\n|---|---|\n| a | C |\n\n## Sources\n\n- jar\n")
        assert doc_lint.lint([d]) == []

def test_grade_missing_flagged():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5)\n\n| Item | Ev |\n|---|---|\n| a | |\n\n## Sources\n\n- jar\n")
        assert any(f.rule == "grades" for f in doc_lint.lint([d]))

def test_cli_reports_findings_quoting_non_ascii_text():
    """Real docs contain arrows/em dashes; a legacy console encoding must not abort the run."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nTODO: hunger → calories — check\n")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        r = subprocess.run([sys.executable, CLI, d], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        assert "Traceback" not in r.stderr, r.stderr
        assert "docs/vanilla/x.md:3: placeholder:" in r.stdout, r.stdout
        assert r.returncode == 1
