import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import pytest

GOOD = {"id": "S0001", "topic": "protein", "parameter": "protein intake at which fat-free-mass gains plateau", "value": "1.62 g/kg/day",
        "range": "95% CI 1.03-2.20", "population": "adults under resistance training, 49 studies n=1863", "grade": "MA",
        "citation": "Morton RW et al 2018, Br J Sports Med 52:376-384, doi:10.1136/bjsports-2017-097608, pmid:28698222",
        "source": "docs/superpowers/research/wave2-science-strength-training.md § 2", "status": "settled", "successor": ""}


def test_round_trip(tmp_path):
    p = tmp_path / "science.tsv"
    sl.write_register(str(p), [GOOD])
    assert p.read_text(encoding="utf-8").split("\n")[0] == "\t".join(sl.COLUMNS)
    assert sl.read_register(str(p)) == [GOOD]


def test_a_bad_header_raises(tmp_path):
    p = tmp_path / "science.tsv"
    p.write_text("id\tparameter\n", encoding="utf-8")
    with pytest.raises(sl.RegisterError):
        sl.read_register(str(p))


def test_a_cell_with_a_tab_or_newline_is_refused(tmp_path):
    p = tmp_path / "science.tsv"
    with pytest.raises(sl.RegisterError):
        sl.write_register(str(p), [dict(GOOD, citation="a\tb")])
    with pytest.raises(sl.RegisterError):
        sl.write_register(str(p), [dict(GOOD, parameter="a\nb")])


def test_validate_good_row():
    assert sl.validate_row(GOOD) == []


def test_validate_catches_each_field():
    assert any("id" in e for e in sl.validate_row(dict(GOOD, id="#0001")))
    assert sl.validate_row(dict(GOOD, id="S16.3"), provisional=True) == []
    assert any("topic" in e for e in sl.validate_row(dict(GOOD, topic="proteins")))
    assert any("grade" in e for e in sl.validate_row(dict(GOOD, grade="RCTs")))
    assert sl.validate_row(dict(GOOD, grade="MODEL")) == [] and sl.validate_row(dict(GOOD, grade="EXP")) == []
    assert any("status" in e for e in sl.validate_row(dict(GOOD, status="done")))
    assert any("citation" in e for e in sl.validate_row(dict(GOOD, citation="Morton 2018, Br J Sports Med")))
    assert any("value" in e for e in sl.validate_row(dict(GOOD, value="")))
    assert any("source" in e for e in sl.validate_row(dict(GOOD, source="somewhere")))
    assert any("source" in e for e in sl.validate_row(dict(GOOD, source="a.md §2")))
    assert any("successor" in e for e in sl.validate_row(dict(GOOD, status="superseded")))
    assert any("successor" in e for e in sl.validate_row(dict(GOOD, successor="S0002")))
    assert any("parameter" in e for e in sl.validate_row(dict(GOOD, parameter=" ")))


def test_an_open_row_may_be_empty_and_ungraded():
    assert sl.validate_row(dict(GOOD, value="", range="", citation="", grade="", topic="", status="open")) == []
    assert sl.validate_row(dict(GOOD, value="", range="", citation="", status="open")) == []
    assert any("grade" in e for e in sl.validate_row(dict(GOOD, grade="")))


def test_rank_resolves_a_slashed_pair():
    assert sl.resolve_grade("MA/TXT") == "MA" and sl.resolve_grade("TXT/AUTH") == "AUTH" and sl.resolve_grade("AUTH/COH") == "COH"
    assert sl.resolve_grade("CASE") == "COH" and sl.resolve_grade("RCT") == "RCT"
    with pytest.raises(ValueError):
        sl.resolve_grade("MODEL/RCT")
    with pytest.raises(ValueError):
        sl.resolve_grade("GAME")


def test_citation_forms():
    for c in ("doi:10.1/x", "PMID:12345", "pmid:12345 and doi:10.1/x", "(doi:10.1/x)", "url:https://lpi.oregonstate.edu/mic/vitamins/vitamin-A", "isbn:978-0-12-802928-2"):
        assert sl.CITATION_RX.search("Someone 2020, Journal, " + c), c
    assert not sl.CITATION_RX.search("Someone 2020, Journal, DOI 10.1/x")
    assert not sl.CITATION_RX.search("Someone 2020, Journal, PMID 12345")


def test_a_superseded_gap_may_be_empty_but_names_a_successor():
    gap = dict(GOOD, topic="", grade="", value="", range="", citation="", status="superseded", successor="S0002")
    assert sl.validate_row(gap) == []
    assert any("successor" in e for e in sl.validate_row(dict(gap, successor="")))
    assert any("grade" in e for e in sl.validate_row(dict(gap, topic="protein")))


def test_an_unrewritten_record_beside_a_good_one_is_flagged():
    for c in ("A 2020, J, doi:10.1/x, PMID 123", "A 2020, J, pmid:1, DOI 10.1/x", "A 2020, J, doi:10.1/x, PMC1234", "A 2020, J, doi:10.1/x, PMID123"):
        assert any("citation" in e for e in sl.validate_row(dict(GOOD, citation=c))), c
    assert sl.validate_row(dict(GOOD, citation="A 2020, J, doi:10.1/x; pmid:123")) == []


def test_a_short_row_names_its_line(tmp_path):
    p = tmp_path / "s.tsv"
    p.write_text("\t".join(sl.COLUMNS) + "\n" + "\t".join(GOOD[c] for c in sl.COLUMNS) + "\n" + "S0002\tx\n", encoding="utf-8")
    with pytest.raises(sl.RegisterError) as e:
        sl.read_register(str(p))
    assert e.value.line == 3 and "trailing empty cells" in str(e.value)
