"""tools/comment_id_lint.py (Plan 20 Task 1, ruling P20-T1-8): each rule on a synthetic tree, with the near-misses
it must leave alone."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import comment_id_lint as cil  # noqa: E402

REGISTRY = (
    "NutritionRevamp = NutritionRevamp or {}\n"
    "NutritionRevamp.data = NutritionRevamp.data or {}\n"
    "local D = {}\n"
    "NutritionRevamp.data.dials = D\n"
    "D['x.A'] = { value = 1, unit = 'u', min = 0, max = 2, src = 'game choice S1592 #0042', note = 'a' } -- a\n"
    "D['x.B'] = { value = 1, unit = 'u', min = 0, max = 2, src = 'S1600', note = 'b' } -- b\n"
    "D['x.C'] = { same = 'x.B', unit = 'u', src = 'inference #0100', note = 'c' } -- c\n"
)


def _tree(tmp_path, kernel):
    d = tmp_path / "lua"
    (d / "shared").mkdir(parents=True, exist_ok=True)
    (d / "shared" / "NR_Data_Dials.lua").write_text(REGISTRY, encoding="utf-8")
    (d / "shared" / "NR_Kernel_X.lua").write_text(kernel, encoding="utf-8")
    return str(d)


def _rules(tmp_path, kernel):
    return [(f.rule, f.line, f.detail) for f in cil.lint(_tree(tmp_path, kernel))]


def test_a_comment_id_in_the_row_src_passes(tmp_path):
    assert _rules(tmp_path, 'K.x.A = K.dials.get("x.A") -- game choice (S1592, #0042)\n') == []


def test_a_comment_id_missing_from_src_is_a_finding(tmp_path):
    f = _rules(tmp_path, 'K.x.A = K.dials.get("x.A") -- S1592 #0043 S1599\n')
    assert f == [("ID", 1, "#0043 is not in the src of x.A"), ("ID", 1, "S1599 is not in the src of x.A")]


def test_game_choice_comment_needs_a_game_choice_src(tmp_path):
    assert _rules(tmp_path, 'K.x.B = K.dials.get("x.B") -- game choice, S1600\n') == [
        ("GC", 1, "the comment says game choice; the src of x.B does not")]


def test_several_gets_pool_their_srcs_and_same_adds_its_target(tmp_path):
    assert _rules(tmp_path, 'T = { K.dials.get("x.A"), K.dials.get("x.B") } -- S1600 #0042\n') == []
    assert _rules(tmp_path, 'K.x.C = K.dials.get("x.C") -- #0100 S1600\n') == []


def test_lines_left_alone(tmp_path):
    kernel = ('K.x.A = K.dials.get("x.A")\n'                       # no comment
              '-- #9999 on a comment line, no get\n'
              'K.x.Z = K.dials.get("x.Z") -- #9999 (an unknown dial: dials.py check reports it)\n'
              'local s = "-- #9999" -- plain\n')
    assert _rules(tmp_path, kernel) == []


def test_cli_exit_codes(tmp_path, capsys):
    d = _tree(tmp_path, 'K.x.A = K.dials.get("x.A") -- #0001\n')
    assert cil.main([d]) == 1 and "1 findings" in capsys.readouterr().out
    (tmp_path / "lua" / "shared" / "NR_Kernel_X.lua").write_text('K.x.A = K.dials.get("x.A") -- #0042\n', encoding="utf-8")
    assert cil.main([d]) == 0
    assert cil.main([str(tmp_path / "nope")]) == 2
