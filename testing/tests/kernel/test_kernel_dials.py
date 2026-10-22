"""The tuning-dial resolver and its sandbox re-resolve (Plan 19 Task 2; spec Part A; ruling T1-1).

K.dials.row, K.dials.get and K.dials.copy (NR_Kernel.lua) resolve a dial from NR.data.dials (NR_Data_Dials.lua) at a
kernel's load; K.dials.apply (NR_Kernel_Dials.lua) re-resolves the rows that name a sandbox option, writing a field
only when the option's read changed against the last value seen. These run on the session host, so the coverage gate
sees every branch; each test lays its own rows under a dialtest domain and removes them after.
"""
import pytest

SETUP = r"""
NutritionRevamp.kernel.dialtest = { X = 1.5, Y = 2, FLAG = false, derived = 0, nested = { Z = 3 } }
function NutritionRevamp.kernel.dialtest.derive()
    local d = NutritionRevamp.kernel.dialtest
    d.derived = d.derived + 1
end
NutritionRevamp.kernel.dialbare = { W = 7 }
local D = NutritionRevamp.data.dials
D['dialtest.X'] = { value = 1.5, unit = 'u', min = 0, max = 4, src = 'game choice', note = 'n', opt = 'DialTestX' }
D['dialtest.Y'] = { value = 2, unit = 'u', min = 1, max = 5, src = 'game choice', note = 'n', opt = 'DialTestY', int = true }
D['dialtest.FLAG'] = { value = false, unit = 'flag', src = 'game choice', note = 'n', opt = 'DialTestFlag' }
D['dialtest.nested.Z'] = { value = 3, unit = 'u', min = 0, max = 9, src = 'game choice', note = 'n', opt = 'DialTestZ' }
D['dialbare.W'] = { value = 7, unit = 'u', min = 0, max = 9, src = 'game choice', note = 'n', opt = 'DialBareW' }
D['dialtest.T'] = { value = { 1, { 2, 3 } }, unit = 'u', min = 0, max = 9, src = 'game choice', note = 'n' }
D['dialtest.S'] = { same = 'dialtest.T', unit = 'u', src = 'game choice', note = 'n' }
D['dialtest.S2'] = { same = 'dialtest.S', unit = 'u', src = 'game choice', note = 'n' }
D['dialtest.C1'] = { same = 'dialtest.C2', unit = 'u', src = 'game choice', note = 'n' }
D['dialtest.C2'] = { same = 'dialtest.C1', unit = 'u', src = 'game choice', note = 'n' }
"""

TEARDOWN = r"""
local D = NutritionRevamp.data.dials
for _, id in ipairs({ 'dialtest.X', 'dialtest.Y', 'dialtest.FLAG', 'dialtest.nested.Z', 'dialbare.W', 'dialtest.T',
                      'dialtest.S', 'dialtest.S2', 'dialtest.C1', 'dialtest.C2' }) do
    D[id] = nil
end
NutritionRevamp.kernel.dialtest = nil
NutritionRevamp.kernel.dialbare = nil
"""


@pytest.fixture
def dk(host):
    host.rt.execute(SETUP)
    saved = host.K.dials.OPT_IDS
    host.K.dials.OPT_IDS = host.K.dials.optIds(host.G.NutritionRevamp.data.dials)
    try:
        yield host
    finally:
        host.K.dials.OPT_IDS = saved
        host.rt.execute(TEARDOWN)


def test_the_registry_loads_before_the_kernels_and_shipped_rows_name_no_option(host):
    assert host.G.NutritionRevamp.data.dials["monotony.SLOPE"].value == 4.3
    assert len(host.K.dials.OPT_IDS) == 0                       # W1 adds no sandbox option


def test_row_returns_the_row_and_an_unknown_id_raises(dk):
    assert dk.K.dials.row("dialtest.X").unit == "u"
    with pytest.raises(Exception, match="no dial dialtest.nope"):
        dk.K.dials.row("dialtest.nope")


def test_row_raises_when_the_host_never_loaded_the_registry(host):
    nr = host.G.NutritionRevamp
    saved = nr.data
    nr.data = None
    try:
        with pytest.raises(Exception, match="no dial monotony.SLOPE"):
            host.K.dials.row("monotony.SLOPE")
    finally:
        nr.data = saved


def test_get_returns_a_scalar_as_it_is(dk):
    assert dk.K.dials.get("dialtest.X") == 1.5 and dk.K.dials.get("dialtest.FLAG") is False


def test_get_copies_a_table_so_a_field_write_never_moves_the_registry(dk):
    t = dk.K.dials.get("dialtest.T")
    assert dk.py(t) == {1: 1, 2: {1: 2, 2: 3}}
    t[2][1] = 99
    assert dk.G.NutritionRevamp.data.dials["dialtest.T"].value[2][1] == 2
    assert dk.K.dials.get("dialtest.T") is not dk.K.dials.get("dialtest.T")


def test_get_follows_same_links_to_the_value(dk):
    assert dk.py(dk.K.dials.get("dialtest.S2")) == {1: 1, 2: {1: 2, 2: 3}}


def test_get_raises_on_a_same_cycle(dk):
    with pytest.raises(Exception, match="dial cycle at dialtest.C1"):
        dk.K.dials.get("dialtest.C1")


def test_opt_ids_are_the_rows_naming_an_option_sorted(dk):
    ids = dk.K.dials.OPT_IDS
    assert [ids[i] for i in range(1, len(ids) + 1)] == ["dialbare.W", "dialtest.FLAG", "dialtest.X", "dialtest.Y",
                                                        "dialtest.nested.Z"]


def test_apply_with_no_sandbox_table_or_default_reads_writes_nothing(dk):
    seen = dk.rt.table()
    assert dk.K.dials.apply(None, seen) == 0
    assert dk.K.dials.apply(dk.table({"DialTestX": 1.5, "DialTestY": 2}), seen) == 0
    assert dk.K.dialtest.derived == 0


def test_apply_writes_a_changed_option_into_its_field_and_runs_derive(dk):
    seen = dk.rt.table()
    sv = dk.table({"DialTestX": 3.0, "DialTestFlag": True, "DialTestZ": 4, "DialBareW": 8})
    assert dk.K.dials.apply(sv, seen) == 4
    assert (dk.K.dialtest.X, dk.K.dialtest.FLAG, dk.K.dialtest.nested.Z, dk.K.dialbare.W) == (3.0, True, 4, 8)
    assert dk.K.dialtest.derived == 3                           # X, FLAG and nested.Z; dialbare has no derive
    assert seen["dialtest.X"] == 3.0


def test_apply_never_rewrites_an_unchanged_read_so_a_patch_survives_the_poll(dk):
    seen = dk.rt.table()
    sv = dk.table({"DialTestX": 3.0})
    dk.K.dials.apply(sv, seen)
    dk.K.dialtest.X = 0.25                                      # a replay or fit patch on the field
    assert dk.K.dials.apply(sv, seen) == 0
    assert dk.K.dialtest.X == 0.25
    assert dk.K.dials.apply(dk.table({"DialTestX": 1.5}), seen) == 1   # back to the default is a change
    assert dk.K.dialtest.X == 1.5


def test_apply_clamps_a_double_option_and_an_int_option_out_of_range_reads_the_default(dk):
    seen = dk.rt.table()
    dk.K.dials.apply(dk.table({"DialTestX": 40.0, "DialTestY": 9}), seen)
    assert dk.K.dialtest.X == 4 and dk.K.dialtest.Y == 2
    dk.K.dials.apply(dk.table({"DialTestY": 4}), seen)
    assert dk.K.dialtest.Y == 4
