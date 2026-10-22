"""tools/dials.py (Plan 19 Task 2): the registry's list, check, diff and set, on a scratch tree and on the shipped one."""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import dials  # noqa: E402

HEAD = """local NR = NutritionRevamp
NR.data = NR.data or {}
NR.data.dials = {}
local D = NR.data.dials
"""

GOOD = {
    "dom.A": "D['dom.A'] = { value = 4.3, unit = 'pts', min = 0, max = 20, src = 'game choice S0001 #0001', note = 'a' } -- the long provenance of A",
    "dom.B": "D['dom.B'] = { value = 10 / 60, unit = 'h', min = 0, max = 1, src = 'fitted', fit = 'fit-x', note = 'b' }",
    "dom.T": "D['dom.T'] = { value = { 20, 45 }, unit = 'pts', min = 0, max = 100, src = 'vanilla #0002', note = 't' }",
    "dom.F": "D['dom.F'] = { value = 50, unit = 'pts', min = 50, max = 50, src = 'vanilla #0002', note = 'f', fixed = true }",
    "dom.S": "D['dom.S'] = { same = 'dom.A', unit = 'pts', src = 'game choice', note = 's' }",
    "dom.O": "D['dom.O'] = { value = 1.0, unit = 'x', min = 0, max = 3, src = 'game choice', note = 'o', opt = 'Scale' }",
    "dom.I": "D['dom.I'] = { value = 2, unit = 'n', min = 1, max = 3, src = 'game choice', note = 'i', opt = 'Pace', int = true }",
    "dom.Q": "D['dom.Q'] = { value = true, unit = 'flag', src = 'inference', note = 'q', opt = 'Flag' }",
}

SANDBOX = """option NR.Scale
{
    type = double, min = 0.0, max = 3.0, default = 1.0,
    page = NutritionRevamp, translation = NR_Scale,
}
option NR.Pace
{
    type = enum, numValues = 3, default = 2,
    page = NutritionRevamp, translation = NR_Pace,
}
option NR.Flag
{
    type = boolean, default = true,
    page = NutritionRevamp, translation = NR_Flag,
}
"""


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def registry(rows):
    return HEAD + "\n".join(rows) + "\n"


@pytest.fixture
def tree(tmp_path):
    root = str(tmp_path)
    _write(root, dials.SCIENCE_REL, "id\ttopic\nS0001\tx\n")
    _write(root, dials.CLAIMS_REL, "id\tclaim\n#0001\tx\n#0002\ty\n")
    _write(root, dials.SANDBOX_REL, SANDBOX)
    gets = "\n".join('K.%s = K.dials.get("%s")' % (i, i) for i in GOOD)
    _write(root, dials.LUA_REL + "/shared/NR_Kernel_Dom.lua", "local K = NutritionRevamp.kernel\n" + gets + "\n")
    _write(root, dials.REGISTRY_REL, registry(GOOD.values()))
    return root


def _check(root, rows):
    return dials.check(root, registry(rows))


def test_the_scratch_registry_is_green(tree):
    assert dials.check(tree) == []


def test_the_shipped_registry_is_green():
    assert dials.check() == []


def test_the_shipped_registry_holds_the_monotony_domain():
    rows = dials.load_rows(dials._read(dials._path(dials.REPO, dials.REGISTRY_REL)))
    assert {i for i in rows if i.startswith("monotony.")} == {
        "monotony." + n for n in ("WINDOW_H", "HALF_LIFE_H", "SLOPE", "CAP", "STAPLE", "MEAL_KCAL", "BORED_MAX",
                                  "DEAD_ZONE", "HOLD_EPS")}


@pytest.mark.parametrize("dial_id,mutant,want", [
    ("dom.A", "value = 25,", "outside [0, 20]"),
    ("dom.A", "unit = '',", "no unit"),
    ("dom.A", "src = 'S0009',", "S0009 is not a row of"),
    ("dom.A", "src = '#0009',", "#0009 is not a row of"),
    ("dom.A", "src = 'guess',", "src token 'guess'"),
    ("dom.A", "src = '',", "no src"),
    ("dom.A", "note = '',", "no note"),
    ("dom.A", "min = 30,", "min 30 over max 20"),
    ("dom.A", "colour = 'red',", "fields outside the row shape: colour"),
    ("dom.T", "src = 'vanilla',", "a vanilla src names no # row"),
    ("dom.T", "value = { 20, 145 },", "value 145 outside"),
    ("dom.F", "value = 49,", "min == max == value"),
    ("dom.F", "opt = 'Scale',", "a fixed dial is never sandbox-backed"),
    ("dom.S", "value = 4.3,", "a same row carries no value"),
    ("dom.S", "unit = 'h',", "unit 'h' differs from dom.A"),
    ("dom.S", "same = 'dom.Z',", "names an unknown dial dom.Z"),
    ("dom.O", "opt = 'Missing',", "option NR.Missing is not in"),
    ("dom.O", "max = 2,", "option NR.Scale max 3.0 differs"),
    ("dom.O", "value = 1.5,", "option NR.Scale default 1.0 differs"),
    ("dom.I", "int = false,", "int must be true"),
    ("dom.I", "value = 2.5,", "an int dial holds a non-integer"),
    ("dom.Q", "value = false,", "option NR.Flag default true differs"),
    ("dom.Q", "min = 0,", "a boolean dial carries no range"),
    ("dom.B", "fit = '',", "an empty fit"),
    ("dom.A", "max = 1/0,", "no finite numeric min and max"),
])
def test_each_check_rule_fails_its_mutant(tree, dial_id, mutant, want):
    rows = dict(GOOD)
    rows[dial_id] = mutate(rows[dial_id], mutant.rstrip(","))
    assert rows[dial_id] != GOOD[dial_id]
    found = _check(tree, rows.values())
    assert any(want in f for f in found), found


def mutate(line, field_text):
    """line with the field `name = value` of field_text replacing that field, or added when the row has none."""
    body = line[line.index("{ ") + 2:line.rindex(" }")]
    parts, depth, cur = [], 0, ""
    for c in body:
        if c == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        cur += c
    parts.append(cur.strip())
    name = field_text.split(" = ")[0]
    hit = [i for i, p in enumerate(parts) if p.split(" = ")[0] == name]
    if hit:
        parts[hit[0]] = field_text
    else:
        parts.append(field_text)
    return line[:line.index("{ ") + 2] + ", ".join(parts) + line[line.rindex(" }"):]


def test_a_same_on_a_sandbox_backed_dial_is_refused(tree):
    # Plan 19 Task 2 fix 1 (F1): K.dials.apply writes only the option row's own field, so a same dependent would not follow
    rows = dict(GOOD)
    rows["dom.S2"] = "D['dom.S2'] = { same = 'dom.O', unit = 'x', src = 'game choice', note = 's' }"
    _write(tree, dials.LUA_REL + "/shared/NR_Kernel_Dom2.lua", 'K.dom.S2 = K.dials.get("dom.S2")\n')
    found = _check(tree, rows.values())
    assert any("dom.S2: same dom.O, a sandbox-backed dial" in f for f in found), found
    assert not any("dom.S:" in f for f in found)                   # a same on a plain dial stays green


def test_a_sandbox_backed_dial_must_resolve_into_its_kernel_field(tree):
    # Plan 19 Task 2 fix 1 (F3): K.dials.bind writes K.<id>, so a get site on an adapter table or a renamed field is refused
    _write(tree, dials.LUA_REL + "/server/NR_Server_X.lua", 'EFF.SCALE = K.dials.get("dom.O")\n')
    found = dials.check(tree)
    assert any("dom.O: a sandbox-backed dial must resolve as K.dom.O" in f for f in found), found
    _write(tree, dials.LUA_REL + "/server/NR_Server_X.lua", 'EFF.SCALE = K.dials.get("dom.A")\n')
    assert dials.check(tree) == []                                  # a plain dial may resolve anywhere


def test_a_sandbox_backed_core_dial_is_refused(tree):
    # Plan 19 Task 3b fix 1 (M8): a core dial is K's top level (core.HEIGHT_M is K.HEIGHT_M), which K.dials.bind cannot
    # write, so an option on one is refused with that reason, not the K.core.<name> resolve the generic rule would ask for
    rows = dict(GOOD)
    rows["core.H"] = "D['core.H'] = { value = 1.0, unit = 'x', min = 0, max = 3, src = 'game choice', note = 'h', opt = 'Scale' }"
    _write(tree, dials.LUA_REL + "/shared/NR_Kernel.lua", 'K.H = K.dials.get("core.H")\n')
    found = _check(tree, rows.values())
    assert any("core.H: a core dial is K's top level (K.H), which K.dials.bind cannot write" in f for f in found), found
    assert not any("core.H: a sandbox-backed dial must resolve as" in f for f in found), found
    rows["core.H"] = "D['core.H'] = { value = 1.0, unit = 'x', min = 0, max = 3, src = 'game choice', note = 'h' }"
    assert _check(tree, rows.values()) == []                        # a core dial without an option stays green


def test_a_param_option_resolves_anywhere_and_its_links_follow_no_option(tree):
    # Plan 19 Task 3f: a param row's option is read into its domain's own table (K.strength.params), never into the
    # field, so its get site may sit in a constructor and a same on it is one dial whatever the option reads; param
    # needs an option and a number, and the option file declares a double's default at three decimal places
    rows = dict(GOOD)
    rows["dom.P"] = "D['dom.P'] = { value = 0.3333333333333333, unit = 'x', min = 0, max = 3, src = 'game choice', opt = 'Third', param = true, note = 'p' }"
    rows["dom.S3"] = "D['dom.S3'] = { same = 'dom.P', unit = 'x', src = 'game choice', note = 's' }"
    sandbox = SANDBOX + "\n".join(["option NR.Third", "{", "    type = double, min = 0.0, max = 3.0, default = 0.333,",
                                   "    page = NutritionRevamp, translation = NR_Third,", "}", ""])
    _write(tree, dials.SANDBOX_REL, sandbox)
    _write(tree, dials.LUA_REL + "/shared/NR_Kernel_Dom2.lua",
           'K.dom.T = { p = K.dials.get("dom.P"), s = K.dials.get("dom.S3") }' + "\n")
    assert _check(tree, rows.values()) == []
    for mutant, want in (("param = false", "param is true on a numeric row with an option"),
                         ("opt = 'Fourth'", "option NR.Fourth is not in")):
        bad = dict(rows)
        bad["dom.P"] = mutate(rows["dom.P"], mutant)
        assert any(want in f for f in _check(tree, bad.values())), mutant
    bad = dict(rows)
    bad["dom.A"] = rows["dom.A"].replace("{ ", "{ param = true, ", 1)
    assert any("dom.A: param is true on a numeric row with an option" in f for f in _check(tree, bad.values()))
    bad = dict(rows)
    bad["dom.S3"] = rows["dom.S3"].replace("{ ", "{ param = true, ", 1)
    assert any("dom.S3: a same row carries no param" in f for f in _check(tree, bad.values()))
    # without param the same row is refused (K.dials.apply would write only dom.P), the site must be K.dom.P, and the
    # value must be exact at the file's three places
    bad = dict(rows)
    bad["dom.P"] = rows["dom.P"].replace(", param = true", "")
    found = _check(tree, bad.values())
    assert any("dom.S3: same dom.P, a sandbox-backed dial" in f for f in found), found
    assert any("dom.P: a sandbox-backed dial must resolve as K.dom.P" in f for f in found), found
    assert any("dom.P: K.dials.apply writes the option's read into the field" in f for f in found), found
    assert dials.written(1 / 3) == 0.333 and dials.written(-650.0) == -650.0 and dials.written(0.35) == 0.35


def test_a_same_cycle_is_refused(tree):
    rows = dict(GOOD)
    rows["dom.C1"] = "D['dom.C1'] = { same = 'dom.C2', unit = 'pts', src = 'game choice', note = 'c' }"
    rows["dom.C2"] = "D['dom.C2'] = { same = 'dom.C1', unit = 'pts', src = 'game choice', note = 'c' }"
    found = _check(tree, rows.values())
    assert any("cycle" in f for f in found)


def test_int_without_an_option_is_refused(tree):
    rows = dict(GOOD)
    rows["dom.A"] = rows["dom.A"].replace("{ ", "{ int = true, ", 1)
    assert any("int describes an option" in f for f in _check(tree, rows.values()))


def test_an_id_on_two_lines_an_orphan_and_an_unknown_get_are_refused(tree):
    rows = list(GOOD.values()) + [GOOD["dom.A"], "D['dom.Z'] = { value = 1, unit = 'u', min = 0, max = 2, src = 'game choice', note = 'z' }"]
    _write(tree, dials.LUA_REL + "/server/NR_Server_X.lua", 'X.Y = K.dials.get("dom.nope")\n')
    found = _check(tree, rows)
    assert any("dom.A: on more than one line" in f for f in found)
    assert any("dom.Z: an orphan" in f for f in found)
    assert any("dom.nope: K.dials.get at NR_Server_X.lua:1" in f for f in found)


def test_a_row_split_over_two_lines_and_text_lua_cannot_run_are_refused(tree):
    split = "D['dom.A'] = {\n value = 1, unit = 'u', min = 0, max = 2, src = 'game choice', note = 'a' }"
    assert any("dom.A: a row spans more than its one line" in f for f in _check(tree, [split] + list(GOOD.values())[1:]))
    assert "does not evaluate" in _check(tree, ["D['dom.A'] = { value = "])[0]


def test_a_get_in_a_comment_is_not_a_read(tree):
    _write(tree, dials.LUA_REL + "/server/NR_Server_X.lua", '-- K.dials.get("dom.nope")\n')
    assert dials.check(tree) == []


def test_source_line_and_provenance_read_the_line_as_written():
    text = registry(GOOD.values())
    assert dials.source_line("dom.A", text) == GOOD["dom.A"]
    assert dials.provenance("dom.A", text) == "the long provenance of A"
    assert dials.provenance("dom.B", text) == ""
    with pytest.raises(KeyError):
        dials.source_line("dom.nope", text)


def test_the_shipped_provenance_is_the_kernel_comment_verbatim():
    assert dials.provenance("monotony.SLOPE").startswith("game choice, Plan 11e (ruling 11e-1): the level per recent portion")


def test_list_filters_by_domain_and_by_src_token():
    text = registry(list(GOOD.values()) + ["D['other.X'] = { value = 1, unit = 'u', min = 0, max = 2, src = 'S0001', note = 'x' }"])
    assert [r[0] for r in dials.table(text, domain="other")] == ["other.X"]
    assert [r[0] for r in dials.table(text, src="game choice")] == ["dom.A", "dom.I", "dom.O", "dom.S"]
    assert [r[0] for r in dials.table(text, src="S0001")] == ["dom.A", "other.X"]
    b = [r for r in dials.table(text) if r[0] == "dom.B"][0]
    assert b[1] == "10 / 60" and "fit=fit-x" in b[6]
    assert [r for r in dials.table(text) if r[0] == "dom.F"][0][6] == "fixed"


def test_diff_names_added_removed_and_changed_dials():
    a = registry([GOOD["dom.A"], GOOD["dom.B"]])
    b = registry([GOOD["dom.A"].replace("value = 4.3", "value = 4.5"), GOOD["dom.T"]])
    assert dials.diff(a, b) == ["+ dom.T", "- dom.B", "~ dom.A value: '4.3' -> '4.5'"]
    assert dials.diff("", a) == ["+ dom.A", "+ dom.B"]
    assert dials.diff(a, a) == []


def test_diff_reads_two_commits_of_this_repository():
    out = subprocess.run([sys.executable, os.path.join(dials.REPO, "tools", "dials.py"), "diff", "0ac21a9f", "0ac21a9f"],
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout == ""
    assert dials._show(dials.REPO, "0ac21a9f") == ""            # the registry is younger than Plan 19's plan commit


def test_set_rewrites_only_the_value_and_keeps_the_line(tree):
    text = registry(GOOD.values())
    out, notes = dials.set_value(text, "dom.A", "5.5", tree)
    assert dials.source_line("dom.A", out) == GOOD["dom.A"].replace("value = 4.3,", "value = 5.5,")
    assert out.replace("value = 5.5,", "value = 4.3,", 1) == text
    assert "python tools/mod_guide_data.py --write" in notes and not any("food_fills" in n for n in notes)
    out, _ = dials.set_value(text, "dom.T", "{ 21, 46 }", tree)
    assert "value = { 21, 46 }, unit" in dials.source_line("dom.T", out)


@pytest.mark.parametrize("dial_id,value,want", [
    ("dom.A", "25", "outside"),
    ("dom.A", "5 +", "does not evaluate"),
    ("dom.A", "{", "not one Lua value"),
    ("dom.S", "1", "resolves to dom.A"),
    ("dom.F", "50", "is fixed"),
    ("dom.nope", "1", "no dial dom.nope"),
    ("dom.A", "5, min = -100", "not one Lua value"),
])
def test_set_refuses(tree, dial_id, value, want):
    with pytest.raises(ValueError, match=want):
        dials.set_value(registry(GOOD.values()), dial_id, value, tree)


def test_set_names_the_regeneration_a_domain_needs():
    assert "python tools/food_fills.py --write" in dials.regenerate_notes("satiety.W_FAT", {"fit": "fit-11g"})
    assert any("fit fit-11g" in n for n in dials.regenerate_notes("satiety.W_FAT", {"fit": "fit-11g"}))
    assert any("NR.Scale" in n for n in dials.regenerate_notes("monotony.SLOPE", {"opt": "Scale"}))
    assert not any("food_fills" in n for n in dials.regenerate_notes("monotony.SLOPE", {}))


def test_the_cli_sets_and_checks_a_scratch_tree(tree):
    tool = os.path.join(dials.REPO, "tools", "dials.py")
    run = lambda *a: subprocess.run([sys.executable, tool, "--root", tree] + list(a), capture_output=True, text=True)
    assert run("check").returncode == 0
    r = run("set", "dom.A", "6")
    assert r.returncode == 0 and "then: python tools/mod_guide_data.py --write" in r.stdout
    assert "value = 6," in dials.source_line("dom.A", dials._read(os.path.join(tree, *dials.REGISTRY_REL.split("/"))))
    r = run("set", "dom.A", "99")
    assert r.returncode == 1 and r.stdout.startswith("refused:")
    r = run("list", "--domain", "dom")
    assert r.returncode == 0 and r.stdout.strip().endswith("8 dials")
    _write(tree, dials.SCIENCE_REL, "id\ttopic\n")
    r = run("check")
    assert r.returncode == 1 and "S0001 is not a row of" in r.stdout


def test_linked_lists_the_ids_that_are_one_dial_the_canonical_first():
    # Plan 19 Task 3d: the fit tools write every kernel field of a patched dial's same group
    assert dials.linked("satiety.MEAL_REQ") == ["hungerCurve.FED_M", "satiety.MEAL_REQ"]
    assert dials.linked("hungerCurve.FED_M") == ["hungerCurve.FED_M", "satiety.MEAL_REQ"]
    group = dials.linked("training.BAND1_MET")
    assert group[0] == "energy.CLASS_MET.Fitness" and "energy.BAND_MET.3" in group and "training.BAND1_MET" in group
    assert dials.linked("satiety.FULL_WEIGHT") == ["satiety.FULL_WEIGHT"]
    assert dials.linked("no.SUCH_DIAL") == ["no.SUCH_DIAL"]
    a = dials.linked("satiety.MEAL_REQ")
    a.append("x")
    assert dials.linked("satiety.MEAL_REQ") == ["hungerCurve.FED_M", "satiety.MEAL_REQ"]   # a fresh list each call
