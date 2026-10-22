"""tools/sandbox_options.py (Plan 19 Task 3f): the option file is rendered from the dial registry and the non-dial HEAD."""
import io
import os
import re
import sys
from contextlib import redirect_stdout

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dials  # noqa: E402
import sandbox_options as SO  # noqa: E402


def registry_text():
    return dials._read(dials._path(dials.REPO, dials.REGISTRY_REL))


def shipped():
    with open(SO.OUT, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_the_shipped_file_is_the_render():
    assert SO.render() == shipped()
    with redirect_stdout(io.StringIO()) as out:
        assert SO.main(["--check"]) == 0
    assert "in sync" in out.getvalue()


def test_every_option_line_is_the_one_before_generation():
    # a pin: a later option tune through `set` and `--write` fails it by design, and its pinned list is then re-based by name
    # the names, types, ranges, defaults, translation keys and order are byte-identical to 3f8ab5a8's hand-written file
    # (only two comments changed): each option block's three lines, in order
    import subprocess
    try:
        old = subprocess.run(["git", "-C", dials.REPO, "show", "3f8ab5a8:" + dials.SANDBOX_REL], capture_output=True,
                             check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("needs the repository history (3f8ab5a8): the migration proof")
    blocks = lambda t: re.findall(r"option NR\.\w+\n\{\n[^}]*\}", t)
    assert blocks(old) == blocks(shipped()) and len(blocks(old)) == 46


def test_each_dial_option_is_its_row():
    rows = dials.load_rows(registry_text())
    opts = dials.sandbox_options(shipped())
    backed = {r["opt"]: (i, r) for i, r in rows.items() if "opt" in r}
    assert len(backed) == 34 and set(backed) <= set(opts)
    for name, (dial_id, row) in backed.items():
        o = opts[name]
        assert o["type"] == ("integer" if row.get("int") else "double"), name
        assert float(o["min"]) == row["min"] and float(o["max"]) == row["max"], name
        assert float(o["default"]) == dials.written(row["value"]), name
        assert o["translation"] == "NR_" + name, name
    assert opts["StrengthMaintainShare"]["default"] == "0.333"


def test_the_options_follow_the_registry_line_order():
    order = [n for n in re.findall(r"option NR\.(\w+)", shipped())]
    lines = dials.row_lines(registry_text())
    rows = dials.load_rows(registry_text())
    by_line = [rows[i]["opt"] for i in sorted((i for i in rows if "opt" in rows[i]), key=lambda i: lines[i][0])]
    assert order[len(SO.HEAD):] == by_line
    assert order[:len(SO.HEAD)] == [h[1] for h in SO.HEAD]


def _edit(text, dial_id, old, new):
    line = dials.source_line(dial_id, text)
    assert line.count(old) == 1, (line, old)
    return text.replace(line, line.replace(old, new))


def test_a_row_edit_moves_the_render_and_fails_check(monkeypatch):
    text = registry_text()
    moved = SO.render(_edit(text, "strength.DEFAULTS.ts", "max = 30,", "max = 40,"))
    assert "type = double, min = 0.25, max = 40.0, default = 1.0," in moved and moved != shipped()
    moved = SO.render(_edit(text, "strength.DEFAULTS.grace_d", "value = 14,", "value = 20,"))
    assert "type = integer, min = 0, max = 60, default = 20," in moved
    monkeypatch.setattr(SO, "render", lambda text=None: moved)
    with redirect_stdout(io.StringIO()) as out:
        assert SO.main(["--check"]) == 1
    assert "out of sync" in out.getvalue()


def test_a_new_option_row_joins_after_its_domain_and_a_bad_bound_is_refused():
    text = registry_text() + ("D['monotony.SCALE_X'] = { value = true, unit = 'flag', src = 'game choice', opt = 'MonoFlag',"
                              " note = 'x' }\n")
    out = SO.render(text)
    assert out.endswith("option NR.MonoFlag\n{\n    type = boolean, default = true,\n"
                        "    page = NutritionRevamp, translation = NR_MonoFlag,\n}\n")
    bad = _edit(registry_text(), "strength.DEFAULTS.ts", "min = 0.25,", "min = 0.2501,")
    with pytest.raises(ValueError, match="three decimal places"):
        SO.render(bad)


def test_the_cli_takes_exactly_one_mode():
    for argv in ([], ["--check", "--write"]):
        with pytest.raises(SystemExit):
            SO.main(argv)
