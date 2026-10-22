"""tools/dial_lint.py (Plan 19 Task 2; dial-inventory section 3.5): each rule on a synthetic file, each with the
near-miss it must leave alone, and the migrated monotony kernel clean."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import dial_lint  # noqa: E402

KER = "mod/x/NR_Kernel_X.lua"
SRV = "mod/x/NR_Server_X.lua"


def rules(text, path=KER):
    return [(f.rule, f.line) for f in dial_lint.lint_text(path, text)]


@pytest.mark.parametrize("line", [
    "K.x.A = 4.3 -- game choice, Plan 11e",
    "K.x.A = 4.3 -- S1592: the slope",
    "K.x.A = 4.3 -- #0042 stale",
    "K.x.A = 10 / 60 -- fitted (fit-11g)",
    "K.x.A = { 20, 45 } -- inference from S0001",
    "K.x.A = -0.5 -- design-phase-v1",
    "local SLOT = 3 -- game choice",
])
def test_e1_flags_a_magnitude_with_a_provenance_comment(line):
    assert rules(line) == [("E1", 1)]


@pytest.mark.parametrize("line", [
    "K.x.A = { 20, 45 } -- VANILLA #2369",
    "K.x.A = 17 -- no row needed: the body parts",
    "K.x.A = 3 -- @fixed S0001",
    "K.x.A = K.dials.get(\"x.A\") -- game choice",
    "K.x.NAME = \"S1234\" -- game choice",
    "K.x.ON = true -- game choice",
    "K.x.A = K.x.B * 2 -- S0001",
    "    K.x.A = 4.3 -- game choice (indented: not top level)",
])
def test_e1_leaves_vanilla_structural_registry_and_non_numeric_lines(line):
    assert [r for r in rules(line) if r[0] == "E1"] == []


def test_e1_flags_an_element_line_of_a_top_level_table():
    text = "K.x.KNOTS = {\n    { 0, 1 }, -- S0001\n    { 2, 3 },\n}\nK.x.V = {\n    { 0, 1 }, -- S0001\n} -- tail\n"
    assert rules(text) == [("E1", 2), ("E1", 6)]


def test_e1_leaves_the_elements_of_a_vanilla_table():
    text = "K.x.KNOTS = { -- VANILLA #2369\n    { 0, 1 }, -- S0001\n}\n"
    assert rules(text) == []


def test_e1_scans_the_element_lines_of_a_table_whose_opening_line_reads_numeric():
    # the Task 3a review's I2 probe: a state table opened as { a = {}, b = 1, ... reads numeric once its keys are
    # stripped, so it took the E2 branch and its element lines went unscanned
    head = "P = { online = {}, queueHead = 1, -- the state, no row needed\n"
    assert rules(head + "      budgetMs = 15, runCap = 1 } -- #3489 game choice\n", SRV) == [("E1", 2)]
    assert rules(head + "      budgetMs = 15, runCap = 1 }\n", SRV) == []


def test_e2_flags_an_unlabelled_numeric_constant_only():
    assert rules("K.x.A = 4") == [("E2", 1)]
    assert rules("-- the step\nK.x.A = 4") == []
    assert rules("K.x.A = 4 -- the step") == []
    assert rules("K.x.A = \"text\"") == []


def test_e3_flags_a_field_reading_another_dial():
    assert rules('K.x.A = K.dials.get("x.B")') == [("E3", 1)]
    assert rules('K.x.A = K.dials.get("x.A")') == []
    assert rules('NutritionRevamp.kernel.x.A = K.dials.get("x.A")') == []


def test_e3_flags_a_dial_resolved_into_a_local():
    # Plan 19 Task 2 fix 1 (F4): ruling T1-1 resolves a dial into its kernel field, never a local
    assert rules('local SLOPE = K.dials.get("monotony.SLOPE")') == [("E3", 1)]
    assert rules('K.monotony.SLOPE = K.dials.get("monotony.SLOPE")') == []


def test_e3_on_an_adapter_reads_the_name_and_keeps_one_domain_a_table():
    assert rules('EFF.SOL_H = K.dials.get("eff.SOL_H")', SRV) == []
    assert rules('EFF.SOL_H = K.dials.get("eff.OTHER")', SRV) == [("E3", 1)]
    assert rules('EFF.A = K.dials.get("eff.A")\nEFF.B = K.dials.get("nut.B")', SRV) == [("E3", 2)]


def test_e4_flags_a_lookup_in_a_function_body():
    text = 'function K.x.f(a)\n    local v = K.dials.get("x.A")\n    return v\nend\n'
    assert rules(text) == [("E4", 2)]
    anon = 'Events.Add(function()\n    if a then\n        K.dials.row("x.A")\n    end\nend)\n'
    assert rules(anon, SRV) == [("E4", 3)]


def test_e4_allows_the_resolver_and_a_load_time_read():
    text = ('function K.dials.get(id)\n    local row = K.dials.row(id)\n    while row.same ~= nil do\n'
            '        row = K.dials.row(row.same)\n    end\n    return row.value\nend\nK.x.A = K.dials.get("x.A")\n')
    assert rules(text) == []


def test_e4_resumes_after_the_resolver_closes():
    text = 'function K.dials.f()\n    return 1\nend\nfunction K.x.g()\n    return K.dials.get("x.A")\nend\n'
    assert rules(text) == [("E4", 5)]


def test_w1_warns_on_an_inline_dial_and_ignores_the_trivial_literals():
    body = "function K.x.f(a)\n    local y = a * %s -- game choice\n    return y\nend\n"
    assert rules(body % "1.37") == [("W1", 2)]
    for trivial in ("60", "0.5", "24", "0.6931471805599453"):
        assert rules(body % trivial) == [], trivial
    assert rules("function K.x.f(a)\n    return a * 1.37 -- a plain comment\nend\n") == []


def test_scope_skips_the_data_files_and_the_bench():
    assert dial_lint.in_scope("x/NR_Kernel_Monotony.lua") and dial_lint.in_scope("x/NR_Server_Effects.lua")
    assert dial_lint.in_scope("x/NR_Client_View.lua")
    assert not dial_lint.in_scope("x/NR_Data_Dials.lua") and not dial_lint.in_scope("x/NR_Server_Bench.lua")
    assert not dial_lint.in_scope("x/NR_Core.lua")


def test_the_migrated_monotony_kernel_and_the_dial_files_are_clean():
    shared = os.path.join(dial_lint.DEFAULT, "shared")
    for name in ("NR_Kernel_Monotony.lua", "NR_Kernel_Dials.lua"):
        assert dial_lint.lint([os.path.join(shared, name)]) == [], name
    assert dial_lint.lint([os.path.join(shared, "NR_Kernel.lua")]) == []    # W4 (Plan 19 Task 3b) moved K.HEIGHT_M (core)


@pytest.mark.parametrize("line,flagged", [
    ("K.x.A = 50 -- VANILLA #2112", False),
    ("K.x.A = 0.3 -- VANILLA #2270: the endDef floor", False),
    ("K.x.A = 0.005 -- VANILLA BodyPart.DamageUpdate L500-L503", False),
    ("K.x.A = 50 -- #2112 VANILLA", True),                       # the old trailing forms (Plan 19 Task 3g: one form)
    ("K.x.A = 0.3 -- the endDef floor, VANILLA #2270", True),
    ("K.x.A = 10 -- vanilla #2354", True),
    ("K.x.A = 4.3 -- VANILLA: game choice S1234", True),
    ("K.x.A = 4.3 -- VANILLA S1234 tuned", True),
    ("K.x.A = 4.3 -- VANILLA the mod floor, #2112", True),
])
def test_e1_takes_the_vanilla_marker_only_where_it_opens_the_comment(line, flagged):
    found = [f for f in dial_lint.lint_text(KER, line) if f.rule == "E1"]
    assert bool(found) == flagged, line
    if flagged and "VANILLA" in line:
        assert "a VANILLA marker opens its comment" in found[0].detail


def test_e1_leaves_the_elements_of_a_table_opened_by_the_vanilla_marker_only():
    assert rules("K.x.T = { -- VANILLA #2354: the tiers\n    0.002, -- #2354\n}\n") == []
    assert rules("K.x.T = { -- the tiers, VANILLA #2354\n    0.002, -- #2354\n}\n") == [("E1", 2)]


def test_the_whole_mod_is_clean_the_section_3_gate():
    # Plan 19 Task 3g: after the last migration wave the lint reads 0 errors and 0 warnings on the whole mod
    assert dial_lint.lint([dial_lint.DEFAULT]) == []


def test_the_cli_exits_1_on_an_error_and_0_on_warnings_only(tmp_path, capsys):
    bad = tmp_path / "NR_Kernel_X.lua"
    bad.write_text("K.x.A = 4.3 -- game choice\n", encoding="utf-8")
    assert dial_lint.main([str(tmp_path)]) == 1
    bad.write_text("function K.x.f(a)\n    return a * 1.37 -- game choice\nend\n", encoding="utf-8")
    assert dial_lint.main([str(tmp_path)]) == 0
    assert "0 errors, 1 warnings" in capsys.readouterr().out
