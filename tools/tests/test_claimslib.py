import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl

ROW = {"id": "#0001", "claim": "Idle burn is 0.016 x weight/80 kcal per game-second.", "grade": "M",
       "pointer": "jar:Nutrition.updateCalories @295 L118; run:exp03-20260910-045523 body.json rows.r1_baseline",
       "bound": "n=1 server-side fit; idle branch only", "status": "settled", "successor": "",
       "kind": "mechanism", "source": "docs/vanilla/body-stats.md § Passive burn", "owner": "facts/body-and-weight.md#passive-burn"}

def test_roundtrip_tsv():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "claims.tsv")
        cl.write_register(p, [ROW])
        rows = cl.read_register(p)
        assert rows == [ROW]
        assert open(p, encoding="utf-8").read().splitlines()[0] == "\t".join(cl.COLUMNS)

def test_bad_header_raises():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tsv"); open(p, "w").write("id\tclaim\n#0001\tx\n")
        try:
            cl.read_register(p); assert False, "expected RegisterError"
        except cl.RegisterError:
            pass

def test_parse_pointers_and_grade():
    ps = cl.parse_pointers(ROW["pointer"])
    assert ps == [("jar", "Nutrition.updateCalories @295 L118"), ("run", "exp03-20260910-045523 body.json rows.r1_baseline")]
    assert cl.strongest_grade([f for f, _ in ps]) == "M"
    assert cl.strongest_grade(["wiki", "jar"]) == "C" and cl.strongest_grade(["wiki"]) == "W"

def test_unknown_pointer_form_raises():
    try:
        cl.parse_pointers("book:p.12"); assert False
    except ValueError:
        pass

def test_parse_bound():
    assert cl.parse_bound("") == ("none", "")
    assert cl.parse_bound("n=2 boots; count census only") == ("n=2", "boots; count census only")
    assert cl.parse_bound("uncommitted: spike-20260909-143930") == ("uncommitted", "spike-20260909-143930")
    assert cl.parse_bound("snapshot 2026-09-10 17:47") == ("snapshot", "2026-09-10 17:47")
    try:
        cl.parse_bound("maybe n=1"); assert False
    except ValueError:
        pass

def test_canonical_suffix():
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="", status="settled")) == ""
    assert cl.canonical_suffix(ROW) == "/M/n=1"
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="inference", status="settled")) == "/C/inference"
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="", status="open")) == "/C/open"
    assert cl.canonical_suffix(dict(ROW, grade="M", bound="uncommitted: x-1", status="unverified")) == "/M/uncommitted/unverified"

def test_tags():
    text = "Burn is 0.016 [#0001/M/n=1]. Two [#0002, #0003/W]. Not a tag [#12]. Provisional [T3.7].\nSecond line [#0004]."
    assert list(cl.iter_tags(text)) == [(1, "#0001", "/M/n=1"), (1, "#0002", ""), (1, "#0003", "/W"), (2, "#0004", "")]
    assert cl.PROVISIONAL_RX.findall(text) == ["[T3.7]"]

def test_blocks_and_ids():
    assert cl.block_of("#0001") == "G1a" and cl.block_of("#0450") == "G1b" and cl.block_of("#1121") == "G2c"
    assert cl.block_of("#2001") == "post" and cl.id_str(17) == "#0017" and cl.id_int("#0017") == 17

def test_validate_row():
    assert cl.validate_row(ROW) == []
    bad = dict(ROW, grade="C", kind="fact", owner="facts/body.md", status="superseded")
    errs = cl.validate_row(bad)
    assert any("grade" in e for e in errs) and any("kind" in e for e in errs)
    assert any("owner" in e for e in errs) and any("successor" in e for e in errs)
