import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import doc_lint
import wiki_mirror

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "doc_lint.py")

def _write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text); return p

def test_stamp_and_sources_required():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nbody TODO\n")
        rules = {f.rule for f in doc_lint.lint([d], d)}
        assert {"stamp", "placeholder", "sources"} <= rules

def test_clean_doc_passes():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5), 2026-09-09\n\n| Item | Ev |\n|---|---|\n| a | C |\n\n## Sources\n\n- jar\n")
        assert doc_lint.lint([d], d) == []

def test_grade_missing_flagged():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5)\n\n| Item | Ev |\n|---|---|\n| a | |\n\n## Sources\n\n- jar\n")
        assert any(f.rule == "grades" for f in doc_lint.lint([d], d))

def test_empty_sources_section_flagged():
    """A '## Sources' with nothing before the next heading is empty, however much prose follows."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5)\n\n## Sources\n\n## Notes\n\nsome prose\n")
        assert any(f.rule == "sources" for f in doc_lint.lint([d], d))

def test_subsections_keep_sources_non_empty():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4 (b0bbce05d5)\n\n## Sources\n\n### Jars\n\n- jar\n\n## Notes\n\nprose\n")
        assert doc_lint.lint([d], d) == []

def test_file_target_is_linted():
    """A file argument must lint that file, not silently pass (os.walk over a file yields nothing)."""
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "docs/vanilla/x.md", "# X\n\nbody TODO\n")
        rules = {f.rule for f in doc_lint.lint([p], d)}
        assert {"stamp", "placeholder", "sources"} <= rules

def test_paths_are_relative_to_repo_root_not_target():
    """Narrowing the target must not turn the path-scoped rules off."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nbody TODO\n")
        findings = doc_lint.lint([os.path.join(d, "docs")], d)
        assert {f.path for f in findings} == {"docs/vanilla/x.md"}
        assert {"stamp", "placeholder", "sources"} <= {f.rule for f in findings}

def test_skip_dirs_match_whole_path_segments():
    """.superpowers is SDD scratch (it quotes the placeholder markers); a lookalike dir is not."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, ".superpowers/sdd/brief.md", "# Brief\n\nthe rule flags TODO\n")
        _write(d, "docs/superpowers/plan.md", "# Plan\n\nTODO\n")
        assert doc_lint.lint([d], d) == []
        _write(d, ".superpowers-notes/n.md", "# N\n\nTODO\n")
        assert [f.path for f in doc_lint.lint([d], d)] == [".superpowers-notes/n.md"]

def test_mirror_header_contract_matches_wiki_mirror_output():
    """The header keys wiki_mirror writes are exactly the ones the lint demands."""
    with tempfile.TemporaryDirectory() as d:
        md = wiki_mirror.render("Nutrition", "https://pzwiki.net/wiki/Nutrition",
                                "{{Page version|42.11.0}}\n'''Nutrition''' is a mechanic.", "2026-09-09")
        _write(d, "references/wiki-mirrors/x.md", md)
        findings = doc_lint.lint([d], d)
        assert [f for f in findings if f.rule == "mirror-header"] == []
        # The only finding on a fresh mirror is its own '_digest pending_' stub, by design.
        assert [f.rule for f in findings] == ["placeholder"]

def test_cli_reports_findings_quoting_non_ascii_text():
    """Real docs contain arrows/em dashes; a legacy console encoding must not abort the run."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nTODO: hunger → calories — check\n")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        r = subprocess.run([sys.executable, CLI, "--root", d, d], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        assert "Traceback" not in r.stderr, r.stderr
        assert "docs/vanilla/x.md:3: placeholder:" in r.stdout, r.stdout
        assert r.returncode == 1

def test_cli_exits_zero_on_a_clean_tree():
    """--root scopes the rules to the tree under test, so a clean tree can actually pass."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/vanilla/x.md", "# X\n\nVerified against: 42.20.4\n\n## Sources\n\n- jar\n")
        r = subprocess.run([sys.executable, CLI, "--root", d, d], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.stdout.strip() == "0 finding(s)", r.stdout
        assert r.returncode == 0
