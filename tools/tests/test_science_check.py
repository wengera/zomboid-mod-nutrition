import os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import science_check as sc

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "science_check.py")
ROW = dict(id="S0001", topic="iron", parameter="p", value="1", range="", population="adults", grade="MA",
           citation="A 2020, J, doi:10.1/x", source="docs/superpowers/research/r.md § 1", status="settled", successor="")


def _tree(tmp_path, rows, files=None):
    root = tmp_path / "repo"
    (root / "docs" / "reference").mkdir(parents=True)
    sl.write_register(str(root / "docs" / "reference" / "science.tsv"), rows)
    for rel, text in (files or {}).items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8", newline="\n")
    return root


def _rules(findings):
    return sorted(f.rule for f in findings)


def test_clean_register_has_no_findings(tmp_path):
    root = _tree(tmp_path, [ROW, dict(ROW, id="S0002"), dict(ROW, id="S0003", topic="", grade="", value="", citation="", status="open")])
    assert sc.check(str(root)) == []


def test_schema_findings(tmp_path):
    rows = [ROW, dict(ROW, id="S0003"), dict(ROW, id="S0003", grade="X"), dict(ROW, id="S0004", topic="nope"),
            dict(ROW, id="S0005", status="superseded", successor="S0009")]
    root = _tree(tmp_path, rows)
    details = [f.detail for f in sc.check(str(root))]
    assert any("contiguous" in d for d in details)
    assert any("duplicate" in d for d in details)
    assert any("grade" in d for d in details)
    assert any("topic" in d for d in details)
    assert any("successor S0009" in d for d in details)


def test_scan_resolves_tokens_and_skips_the_register_and_its_page(tmp_path):
    rows = [ROW, dict(ROW, id="S0002", status="superseded", successor="S0003"), dict(ROW, id="S0003")]
    root = _tree(tmp_path, rows, {"mod/a.lua": "local x = 1.62 -- S0001\nlocal y = 2 -- S0002\nlocal z = 3 -- S0042\n",
                                  "docs/reference/science.md": "the mod cites the bare id, `S0000`\n"})
    f = sc.check(str(root), scan=[str(root / "mod"), str(root / "docs")])
    assert _rules(f) == ["scan", "scan"]
    assert any("S0042" in x.detail for x in f) and any("S0002" in x.detail and "superseded" in x.detail for x in f)
    assert all(x.line in (2, 3) for x in f)


def test_part_mode_accepts_provisional_ids_and_skips_contiguity(tmp_path):
    part = tmp_path / "part.tsv"
    sl.write_register(str(part), [dict(ROW, id="S16.1"), dict(ROW, id="S16.7", citation="none")])
    f = sc.check_part(str(part))
    assert _rules(f) == ["schema"] and "citation" in f[0].detail and f[0].line == 3


def test_cli_exit_codes(tmp_path):
    root = _tree(tmp_path, [ROW])
    assert subprocess.run([sys.executable, CLI, "--root", str(root)], capture_output=True).returncode == 0
    root2 = _tree(tmp_path / "b", [dict(ROW, grade="nope")])
    r = subprocess.run([sys.executable, CLI, "--root", str(root2)], capture_output=True, text=True)
    assert r.returncode == 1 and "schema" in r.stdout


def test_a_short_row_in_a_part_is_one_finding_at_its_line(tmp_path):
    part = tmp_path / "part.tsv"
    good = "\t".join(ROW[c] for c in sl.COLUMNS).replace("S0001", "S1.1")
    part.write_text("\t".join(sl.COLUMNS) + "\n" + good + "\n" + "S1.2\tiron\n", encoding="utf-8")
    f = sc.check_part(str(part))
    assert len(f) == 1 and f[0].line == 3


def test_scan_of_a_missing_path_is_a_finding(tmp_path):
    root = _tree(tmp_path, [ROW])
    f = sc.check(str(root), scan=[str(root / "nope")])
    assert _rules(f) == ["scan"] and "nope" in f[0].detail


def test_a_mixed_citation_fails_the_schema(tmp_path):
    root = _tree(tmp_path, [dict(ROW, citation="A 2020, J, doi:10.1/x, PMID 5")])
    assert any("citation" in f.detail for f in sc.check(str(root)))


def test_staged_reads_the_index_blob(tmp_path):
    root = _tree(tmp_path, [ROW])
    git = lambda *a: subprocess.run(["git", *a], cwd=str(root), capture_output=True, text=True)
    git("init", "-q")
    sl.write_register(str(root / "docs" / "reference" / "science.tsv"), [dict(ROW, grade="nope")])
    git("add", "docs/reference/science.tsv")
    sl.write_register(str(root / "docs" / "reference" / "science.tsv"), [ROW])
    r = subprocess.run([sys.executable, CLI, "--root", str(root), "--staged"], capture_output=True, text=True)
    assert r.returncode == 1 and "grade" in r.stdout
