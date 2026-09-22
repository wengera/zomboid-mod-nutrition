import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl
import claims_delta as cd
import pytest

HEADER = "\t".join(cd.DELTA_COLUMNS)


def _register(tmp_path):
    rows = [
        {"id": "#0001", "claim": "One.", "grade": "C", "pointer": "jar:A.b @1 L2", "bound": "", "status": "settled",
         "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Y", "owner": "facts/x.md#a"},
        {"id": "#0002", "claim": "Two.", "grade": "M", "pointer": "run:exp01-20260910-003929 f.json k", "bound": "n=1",
         "status": "settled", "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Y", "owner": "facts/x.md#b"},
        {"id": "#0003", "claim": "Three.", "grade": "C", "pointer": "jar:A.c @1 L3", "bound": "", "status": "settled",
         "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Z", "owner": "facts/x.md#c"},
    ]
    p = tmp_path / "claims.tsv"
    cl.write_register(str(p), rows)
    return str(p)


def _delta(tmp_path, lines):
    p = tmp_path / "delta.tsv"
    p.write_text(HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def _page(tmp_path, text):
    p = tmp_path / "x.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def _add(pid, claim="Added.", owner="facts/x.md#a", grade="C", pointer="jar:A.d @4 L5", bound="", status="settled", kind="mechanism"):
    return "\t".join(["add", pid, claim, grade, pointer, bound, status, "", kind, "docs/vanilla/x.md § Y", owner, "why"])


def test_add_mints_next_id_and_rewrites_the_provisional_tag(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1] and [#0002/M/n=1, T7.1].\n")
    changes, pages = cd.apply(_delta(tmp_path, [_add("T7.1")]), [page], register=reg)
    assert changes == ["T7.1 -> #0004"] and pages == [page]
    rows = cl.read_register(reg)
    assert rows[-1]["id"] == "#0004" and rows[-1]["claim"] == "Added."
    assert open(page, encoding="utf-8").read() == "Text [#0004] and [#0002/M/n=1, #0004].\n"


def test_add_gets_the_canonical_suffix(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1].\n")
    cd.apply(_delta(tmp_path, [_add("T7.1", grade="M", pointer="run:exp01-20260910-003929 f.json k", bound="n=1", status="open")]), [page], register=reg)
    assert open(page, encoding="utf-8").read() == "Text [#0004/M/n=1/open].\n"


def test_split_supersedes_the_parent_and_rewrites_its_tag(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Parent [#0003]. Kids [T7.1] [T7.2].\n")
    lines = ["\t".join(["split", "#0003", "", "", "", "", "", "", "", "", "", "two claims"]), _add("T7.1", "Three a."), _add("T7.2", "Three b.")]
    changes, _ = cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0003"]["status"] == "superseded" and rows["#0003"]["successor"] == "#0004, #0005"
    assert open(page, encoding="utf-8").read() == "Parent [#0004, #0005]. Kids [#0004] [#0005].\n"
    assert "#0003 superseded -> #0004, #0005" in changes


def test_retarget_and_status(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [#0001] [#0002/M/n=1].\n")
    lines = ["\t".join(["retarget", "#0001", "", "", "", "", "", "", "", "", "facts/x.md#z", "moved"]),
             "\t".join(["status", "#0002", "", "", "", "n=1; unsettled", "open", "", "", "", "", "unsettled"])]
    changes, _ = cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0001"]["owner"] == "facts/x.md#z"
    assert rows["#0002"]["status"] == "open" and rows["#0002"]["bound"] == "n=1; unsettled"
    assert open(page, encoding="utf-8").read() == "Text [#0001] [#0002/M/n=1/open].\n"
    assert changes == ["#0001 owner facts/x.md#a -> facts/x.md#z", "#0002 status -> open"]


def test_an_invalid_add_writes_nothing(tmp_path):
    reg = _register(tmp_path)
    before = open(reg, encoding="utf-8").read()
    page = _page(tmp_path, "Text [T7.1].\n")
    with pytest.raises(cd.DeltaError):
        cd.apply(_delta(tmp_path, [_add("T7.1", claim="")]), [page], register=reg)
    assert open(reg, encoding="utf-8").read() == before
    assert open(page, encoding="utf-8").read() == "Text [T7.1].\n"


def test_dry_run_writes_nothing_and_reports(tmp_path):
    reg = _register(tmp_path)
    before = open(reg, encoding="utf-8").read()
    page = _page(tmp_path, "Text [T7.1].\n")
    changes, pages = cd.apply(_delta(tmp_path, [_add("T7.1")]), [page], register=reg, dry_run=True)
    assert changes == ["T7.1 -> #0004"] and pages == [page]
    assert open(reg, encoding="utf-8").read() == before


def test_unknown_op_and_bad_header_fail(tmp_path):
    p = tmp_path / "d.tsv"
    p.write_text("op\tid\n", encoding="utf-8")
    with pytest.raises(cd.DeltaError):
        cd.read_delta(str(p))
    p.write_text(HEADER + "\n" + "\t".join(["drop", "#0001"] + [""] * 10) + "\n", encoding="utf-8")
    with pytest.raises(cd.DeltaError):
        cd.read_delta(str(p))


def test_leftover_provisional_tags_are_reported(tmp_path, capsys):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1] and [T7.9].\n")
    rc = cd.main(["apply", _delta(tmp_path, [_add("T7.1")]), "--pages", page, "--register", reg])
    out = capsys.readouterr().out
    assert rc == 0 and "T7.1 -> #0004" in out and "WARNING: provisional tags left" in out and "T7.9" in out
