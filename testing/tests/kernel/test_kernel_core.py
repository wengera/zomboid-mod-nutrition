def test_kernel_version_is_the_mod_version(host):
    assert host.K.version == host.G.NutritionRevamp.version == "1.0.0"


def test_clamp_min_max(host):
    assert host.call("clamp", 0.5, 0.0, 1.0) == 0.5
    assert host.call("clamp", -1.0, 0.0, 1.0) == 0.0
    assert host.call("clamp", 2.0, 0.0, 1.0) == 1.0
    assert host.call("max", 1, 2) == 2 and host.call("max", 3, 2) == 3
    assert host.call("min", 1, 2) == 1 and host.call("min", 3, 2) == 2


def test_the_core_side_tests_are_false_offline(host):
    # isServer/isClient are nil in the host, so the nil-checked side test answers false on both.
    assert host.G.NutritionRevamp.isServer() is False
    assert host.G.NutritionRevamp.isClient() is False


def test_the_guard_reports_absence_without_raising(host):
    present, value = host.G.NutritionRevamp.call(None, "getX")
    assert (present, value) == (False, None)
    present, value = host.G.NutritionRevamp.call(host.table({}), "getX")
    assert (present, value) == (False, None)
