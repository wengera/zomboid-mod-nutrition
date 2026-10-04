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
    part = _part(tmp_path, [dict(ROW, id="S16.1"), dict(ROW, id="S16.2", grade="bad")])
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
