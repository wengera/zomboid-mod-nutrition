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


def test_ops_on_a_superseded_row_are_refused(tmp_path):
    reg = _register(tmp_path)
    rows = cl.read_register(reg)
    rows[2]["status"], rows[2]["successor"] = "superseded", "#0001, #0002"
    cl.write_register(reg, rows)
    before = open(reg, encoding="utf-8").read()
    text = "Parent [#0003]. Kids [T7.1] [T7.2].\n"
    page = _page(tmp_path, text)
    cases = [["\t".join(["split", "#0003", "", "", "", "", "", "", "", "", "", "two claims"]), _add("T7.1", "Three a."), _add("T7.2", "Three b.")],
             ["\t".join(["status", "#0003", "", "", "", "", "open", "", "", "", "", "unsettled"])],
             ["\t".join(["retarget", "#0003", "", "", "", "", "", "", "", "", "facts/x.md#z", "moved"])]]
    for lines in cases:
        with pytest.raises(cd.DeltaError) as e:
            cd.apply(_delta(tmp_path, lines), [page], register=reg)
        assert "already superseded" in str(e.value) and "#0001, #0002" in str(e.value)
        assert open(reg, encoding="utf-8").read() == before
        assert open(page, encoding="utf-8").read() == text


def test_a_retarget_off_the_named_pages_is_noted(tmp_path, capsys):
    reg = _register(tmp_path)
    owned = tmp_path / "docs" / "facts" / "x.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("Text [#0001] [#0003].\n", encoding="utf-8")
    lines = ["\t".join(["retarget", "#0001", "", "", "", "", "", "", "", "", "facts/x.md#z", "same page"]),
             "\t".join(["retarget", "#0003", "", "", "", "", "", "", "", "", "facts/other.md#z", "another page"])]
    rc = cd.main(["apply", _delta(tmp_path, lines), "--pages", str(owned), "--register", reg])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NOTE: #0003 now owned by facts/other.md, which is not among --pages" in out
    assert "#0001 now owned by" not in out


def test_supersede_replaces_the_parent_with_one_child(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Parent [#0003]. Child [T7.1].\n")
    lines = ["\t".join(["supersede", "#0003", "", "", "", "", "", "", "", "", "", "falsified"]), _add("T7.1", "Three, corrected.")]
    changes, _ = cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0003"]["status"] == "superseded" and rows["#0003"]["successor"] == "#0004"
    assert rows["#0004"]["claim"] == "Three, corrected."
    assert open(page, encoding="utf-8").read() == "Parent [#0004]. Child [#0004].\n"
    assert "#0003 superseded -> #0004" in changes


def test_supersede_needs_exactly_one_add_and_writes_nothing_otherwise(tmp_path):
    reg = _register(tmp_path)
    before = open(reg, encoding="utf-8").read()
    lines = ["\t".join(["supersede", "#0003", "", "", "", "", "", "", "", "", "", "x"]),
             "\t".join(["retarget", "#0001", "", "", "", "", "", "", "", "", "facts/x.md#z", "moved"])]
    with pytest.raises(cd.DeltaError, match="exactly one add line"):
        cd.apply(_delta(tmp_path, lines), [], register=reg)
    assert open(reg, encoding="utf-8").read() == before
    lines = ["\t".join(["supersede", "#0003", "", "", "", "", "", "", "", "", "", "x"])]
    with pytest.raises(cd.DeltaError, match="exactly one add line"):
        cd.apply(_delta(tmp_path, lines), [], register=reg)
    assert open(reg, encoding="utf-8").read() == before


def test_supersede_honours_the_successor_cell_wherever_the_add_sits(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Parent [#0003]. First [T1.1]. Named [T1.2].\n")
    lines = ["\t".join(["supersede", "#0003", "", "", "", "", "", "T1.2", "", "", "", "narrowed"]),
             _add("T1.1", "First."), _add("T1.2", "Named.")]
    cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0003"]["status"] == "superseded" and rows["#0003"]["successor"] == "#0004"
    assert rows["#0004"]["claim"] == "Named." and rows["#0005"]["claim"] == "First."
    assert open(page, encoding="utf-8").read() == "Parent [#0004]. First [#0005]. Named [#0004].\n"
    before = open(reg, encoding="utf-8").read()
    lines = ["\t".join(["supersede", "#0001", "", "", "", "", "", "T1.9", "", "", "", "x"]), _add("T1.1")]
    with pytest.raises(cd.DeltaError, match="carried by no add row"):
        cd.apply(_delta(tmp_path, lines), [], register=reg)
    assert open(reg, encoding="utf-8").read() == before


# --- The archive and the retire op (Plan 20 rulings P20-T1-1, P20-T1-4, P20-T1-5).

import subprocess
sys.path.insert(0, os.path.dirname(__file__))
import gitenv


def _git(d, *a):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(d), *a], check=True,
                          capture_output=True, text=True, env=gitenv.scrubbed_env()).stdout.strip()


def _repo(tmp_path, body="a = 1\nb = 2\n"):
    """A tmp git repo holding mod/x.lua and the register at docs/reference/claims.tsv; #0003 cites mod/x.lua:1."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "mod").mkdir()
    (tmp_path / "mod" / "x.lua").write_text(body, encoding="utf-8", newline="\n")
    _git(tmp_path, "add", "mod/x.lua")
    _git(tmp_path, "commit", "-q", "-m", "c1")
    ref = tmp_path / "docs" / "reference"; ref.mkdir(parents=True)
    rows = cl.read_register(_register(tmp_path))
    rows[2]["pointer"] = 'jar:A.c @1 L3; repo:mod/x.lua:1 "a = 1"'
    reg = str(ref / "claims.tsv")
    cl.write_register(reg, rows)
    return reg, _git(tmp_path, "rev-parse", "--short", "HEAD")


def _retire(cid, reason="no page sentence left"):
    return "\t".join(["retire", cid, "", "", "", "", "", "", "", "", "", reason])


def test_retire_pins_appends_the_reason_and_moves_the_row(tmp_path):
    reg, sha = _repo(tmp_path)
    page = _page(tmp_path, "Nothing tags it.\n")
    changes, pages = cd.apply(_delta(tmp_path, [_retire("#0003")]), [page], register=reg, today="2026-10-23")
    assert changes == ["#0003 retired -> claims-archive.tsv"] and pages == []
    assert [r["id"] for r in cl.read_register(reg)] == ["#0001", "#0002"]
    arch = cl.read_register(os.path.join(os.path.dirname(reg), "claims-archive.tsv"))
    assert len(arch) == 1 and arch[0]["id"] == "#0003" and arch[0]["status"] == "retired"
    assert arch[0]["pointer"] == 'jar:A.c @1 L3; repo:mod/x.lua@%s:1 "a = 1"' % sha
    assert arch[0]["bound"] == "none; retired 2026-10-23: no page sentence left"


def test_retire_keeps_a_bound_and_a_pin_already_there(tmp_path):
    reg, sha = _repo(tmp_path)
    rows = cl.read_register(reg)
    rows[2]["pointer"] = 'repo:mod/x.lua@%s:2 "b = 2"' % sha
    rows[2]["bound"] = "inference; a reading of #0001"
    cl.write_register(reg, rows)
    cd.apply(_delta(tmp_path, [_retire("#0003", "folded into #0001")]), [], register=reg, today="2026-10-23")
    arch = cl.read_register(os.path.join(os.path.dirname(reg), "claims-archive.tsv"))
    assert arch[0]["pointer"] == 'repo:mod/x.lua@%s:2 "b = 2"' % sha
    assert arch[0]["bound"] == "inference; a reading of #0001; retired 2026-10-23: folded into #0001"


def test_retire_refuses_an_empty_reason_and_a_quote_not_at_head(tmp_path):
    reg, _ = _repo(tmp_path)
    before = open(reg, encoding="utf-8").read()
    with pytest.raises(cd.DeltaError, match="reason cell is empty"):
        cd.apply(_delta(tmp_path, [_retire("#0003", "")]), [], register=reg)
    (tmp_path / "mod" / "x.lua").write_text("b = 2\na = 1\n", encoding="utf-8")      # edited, not committed
    rows = cl.read_register(reg)
    rows[2]["pointer"] = 'repo:mod/x.lua:2 "a = 1"'                                       # true in the working tree only
    cl.write_register(reg, rows)
    before = open(reg, encoding="utf-8").read()
    with pytest.raises(cd.DeltaError, match="does not hold at HEAD"):
        cd.apply(_delta(tmp_path, [_retire("#0003")]), [], register=reg)
    assert open(reg, encoding="utf-8").read() == before
    assert not os.path.exists(os.path.join(os.path.dirname(reg), "claims-archive.tsv"))


def test_retire_notes_a_page_that_still_tags_the_row(tmp_path, capsys):
    reg, _ = _repo(tmp_path)
    page = _page(tmp_path, "Still here [#0003].\n")
    assert cd.main(["apply", _delta(tmp_path, [_retire("#0003")]), "--pages", page, "--register", reg]) == 0
    assert "NOTE: #0003 is retired but" in capsys.readouterr().out


def test_status_never_writes_retired_and_ops_on_an_archived_row_are_refused(tmp_path):
    reg = _register(tmp_path)
    with pytest.raises(cd.DeltaError, match="only by the retire op"):
        cd.apply(_delta(tmp_path, ["\t".join(["status", "#0001", "", "", "", "", "retired", "", "", "", "", "x"])]), [], register=reg)
    arch = os.path.join(os.path.dirname(reg), "claims-archive.tsv")
    cl.write_register(arch, [{"id": "#0004", "claim": "Old.", "grade": "C", "pointer": "jar:A.e @1 L2", "bound": "",
                              "status": "superseded", "successor": "#0001", "kind": "mechanism", "source": "s", "owner": ""}])
    for line in (_retire("#0004"), "\t".join(["retarget", "#0004", "", "", "", "", "", "", "", "", "facts/x.md#a", "x"])):
        with pytest.raises(cd.DeltaError, match="row is archived"):
            cd.apply(_delta(tmp_path, [line]), [], register=reg)


def test_add_mints_past_the_highest_id_of_both_files(tmp_path):
    reg = _register(tmp_path)
    cl.write_register(os.path.join(os.path.dirname(reg), "claims-archive.tsv"),
                      [{"id": "#0009", "claim": "Old.", "grade": "C", "pointer": "jar:A.e @1 L2", "bound": "",
                        "status": "superseded", "successor": "#0001", "kind": "mechanism", "source": "s", "owner": ""}])
    changes, _ = cd.apply(_delta(tmp_path, [_add("T7.1")]), [], register=reg)
    assert changes == ["T7.1 -> #0010"]


def test_archive_superseded_moves_every_superseded_row_in_id_order(tmp_path, capsys):
    reg = _register(tmp_path)
    rows = cl.read_register(reg)
    rows[0]["status"], rows[0]["successor"] = "superseded", "#0002"
    rows[2]["status"], rows[2]["successor"] = "superseded", "#0002"
    cl.write_register(reg, rows)
    arch = os.path.join(os.path.dirname(reg), "claims-archive.tsv")
    cl.write_register(arch, [{"id": "#0001", "claim": "x", "grade": "C", "pointer": "jar:A.e @1 L2", "bound": "",
                              "status": "superseded", "successor": "#0002", "kind": "mechanism", "source": "s", "owner": ""}])
    with pytest.raises(cd.DeltaError, match="#0001 already in the archive"):
        cd.archive_superseded(reg)
    cl.write_register(arch, [])
    before = open(reg, encoding="utf-8").read()
    assert cd.main(["archive-superseded", "--register", reg, "--dry-run"]) == 0
    assert "2 superseded rows would move to" in capsys.readouterr().out
    assert open(reg, encoding="utf-8").read() == before and cl.read_register(arch) == []
    assert cd.archive_superseded(reg) == 2
    assert [r["id"] for r in cl.read_register(reg)] == ["#0002"]
    assert [r["id"] for r in cl.read_register(arch)] == ["#0001", "#0003"]
    assert cd.archive_superseded(reg) == 0


def test_archive_superseded_merges_into_an_archive_in_id_order(tmp_path):
    reg = _register(tmp_path)
    rows = cl.read_register(reg)
    rows[0]["status"], rows[0]["successor"] = "superseded", "#0002"
    rows[2]["status"], rows[2]["successor"] = "superseded", "#0002"
    cl.write_register(reg, rows)
    arch = os.path.join(os.path.dirname(reg), "claims-archive.tsv")
    cl.write_register(arch, [{"id": "#0005", "claim": "x", "grade": "C", "pointer": "jar:A.e @1 L2", "bound": "",
                              "status": "superseded", "successor": "#0002", "kind": "mechanism", "source": "s", "owner": ""}])
    assert cd.archive_superseded(reg) == 2
    assert [r["id"] for r in cl.read_register(arch)] == ["#0001", "#0003", "#0005"]


def test_retire_keeps_the_archive_in_id_order(tmp_path):
    reg, _ = _repo(tmp_path)
    arch = os.path.join(os.path.dirname(reg), "claims-archive.tsv")
    cl.write_register(arch, [{"id": "#0009", "claim": "Old.", "grade": "C", "pointer": "jar:A.e @1 L2", "bound": "",
                              "status": "superseded", "successor": "#0001", "kind": "mechanism", "source": "s", "owner": ""}])
    cd.apply(_delta(tmp_path, [_retire("#0003")]), [], register=reg, today="2026-10-23")
    assert [r["id"] for r in cl.read_register(arch)] == ["#0003", "#0009"]
