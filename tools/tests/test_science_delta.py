import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import science_delta as sd
import pytest

ROW = dict(id="S0001", topic="iron", parameter="p", value="1", range="", population="adults", grade="MA",
           citation="A 2020, J, doi:10.1/x", source="docs/superpowers/research/r.md § 1", status="settled", successor="")


def _register(tmp_path, rows):
    p = tmp_path / "science.tsv"; sl.write_register(str(p), rows); return str(p)


def _part(tmp_path, rows):
    p = tmp_path / "part.tsv"; sl.write_register(str(p), rows); return str(p)


def test_apply_mints_in_file_order(tmp_path):
    reg = _register(tmp_path, [ROW])
    part = _part(tmp_path, [dict(ROW, id="S16.1", parameter="a"), dict(ROW, id="S16.2", parameter="b")])
    changes = sd.apply(part, register=reg)
    assert changes == ["S16.1 -> S0002", "S16.2 -> S0003"]
    rows = sl.read_register(reg)
    assert [r["id"] for r in rows] == ["S0001", "S0002", "S0003"] and rows[2]["parameter"] == "b"


def test_apply_on_an_empty_register_starts_at_one(tmp_path):
    reg = _register(tmp_path, [])
    assert sd.apply(_part(tmp_path, [dict(ROW, id="S1.1")]), register=reg) == ["S1.1 -> S0001"]


def test_a_bad_row_aborts_before_any_write(tmp_path):
    reg = _register(tmp_path, [ROW])
    before = open(reg, encoding="utf-8").read()
    part = _part(tmp_path, [dict(ROW, id="S16.1", parameter="a"), dict(ROW, id="S16.2", parameter="b", grade="bad")])
    with pytest.raises(sd.DeltaError) as e:
        sd.apply(part, register=reg)
    assert "line 3" in str(e.value) and open(reg, encoding="utf-8").read() == before


def test_a_real_id_in_a_part_is_refused(tmp_path):
    reg = _register(tmp_path, [ROW])
    with pytest.raises(sd.DeltaError):
        sd.apply(_part(tmp_path, [dict(ROW, id="S0007")]), register=reg)


def test_status_supersedes_and_refuses_a_closed_lineage(tmp_path):
    reg = _register(tmp_path, [ROW, dict(ROW, id="S0002")])
    assert sd.status("S0001", "superseded", successor="S0002", register=reg) == "S0001 status -> superseded (successor S0002)"
    rows = {r["id"]: r for r in sl.read_register(reg)}
    assert rows["S0001"]["successor"] == "S0002"
    with pytest.raises(sd.DeltaError):
        sd.status("S0001", "open", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.status("S0002", "superseded", register=reg)


GAP = dict(ROW, id="S0002", topic="", value="", range="", grade="", citation="", status="open", parameter="gap")


def test_an_open_row_closes_onto_a_successor(tmp_path):
    reg = _register(tmp_path, [ROW, GAP])
    assert sd.status("S0002", "superseded", successor="S0001", register=reg) == "S0002 status -> superseded (successor S0001)"


def test_settle_fills_an_open_row(tmp_path):
    reg = _register(tmp_path, [ROW, GAP])
    assert sd.settle("S0002", topic="iron", grade="RCT", value="2 mg", citation="B 2021, J, pmid:5", register=reg) == "S0002 settled"
    r = sl.read_register(reg)[1]
    assert r["status"] == "settled" and r["value"] == "2 mg" and r["parameter"] == "gap" and r["source"] == ROW["source"]
    with pytest.raises(sd.DeltaError):
        sd.settle("S0002", topic="iron", grade="RCT", value="3", citation="B, pmid:5", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.settle("S0001", topic="iron", grade="RCT", value="3", citation="B, pmid:5", register=reg)


def test_settle_validates_the_result_and_can_leave_it_unverified(tmp_path):
    reg = _register(tmp_path, [GAP])
    before = open(reg, encoding="utf-8").read()
    with pytest.raises(sd.DeltaError):
        sd.settle("S0002", topic="nope", grade="RCT", value="2", citation="B, pmid:5", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.settle("S0002", topic="iron", grade="RCT", value="2", citation="no record", register=reg)
    assert open(reg, encoding="utf-8").read() == before


def test_settle_as_unverified(tmp_path):
    reg = _register(tmp_path, [dict(GAP, id="S0001")])
    assert sd.settle("S0001", topic="iron", grade="COH", value="2", citation="B, pmid:5", new_status="unverified", register=reg) == "S0001 unverified"


def test_apply_refuses_a_reapplied_part(tmp_path):
    reg = _register(tmp_path, [ROW])
    part = _part(tmp_path, [dict(ROW, id="S1.1")])
    with pytest.raises(sd.DeltaError) as e:
        sd.apply(part, register=reg)
    assert "S1.1" in str(e.value) and "S0001" in str(e.value) and len(sl.read_register(reg)) == 1
    assert sd.apply(part, register=reg, allow_duplicate=True) == ["S1.1 -> S0002"]


def test_status_guards(tmp_path):
    reg = _register(tmp_path, [ROW, dict(ROW, id="S0002"), dict(ROW, id="S0003"), dict(ROW, id="S0004")])
    with pytest.raises(sd.DeltaError):
        sd.status("S0001", "superseded", successor="S0001", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.status("S0001", "unverified", successor="S0002", register=reg)
    sd.status("S0002", "superseded", successor="S0003", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.status("S0001", "superseded", successor="S0002", register=reg)
    assert sl.read_register(reg)[0]["status"] == "settled"
    assert sd.status("S0001", "superseded", successor="S0003, S0004", register=reg).endswith("(successor S0003, S0004)")
    with pytest.raises(sd.DeltaError):
        sd.status("S0003", "superseded", successor="S0003, S0009", register=reg)
