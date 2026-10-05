"""The state multipliers (NR_Kernel_Retention.lua): cooked/burnt/rotten/frozen per nutrient class.

NR_Kernel_Retention.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture
loads it through its glob and already has NutritionRevamp.kernel.retention. Retention touches only
the mod nutrients; the four vanilla macros pass through unscaled -- the eat wrapper owns the burnt
divisor of 5 on the macros, not this kernel (spec § 4.2, data-pipeline report § B, #0036/#0019).
Every factor is a design-phase judgement or a USDA R6 basis, not a settled science row.
"""


# --- the class map and the factor table (module constants) ---

def test_classes_tag_each_mod_nutrient(host):
    c = host.py(host.K.retention.CLASSES)
    expect = {"vitC": "watersol", "fibre": "stable", "water": "stable",
              "iron": "mineral", "phytate": "heatlabile"}
    # Plan 4: the B vitamins and choline lose to cooking water and heat (watersol, S0252's 20-80 %
    # thiamine band); carotene is stable (cooking raises its availability, never a loss); the minerals
    # leach slightly; caffeine and ethanol are carried as stable.
    for k in ("thiamine", "riboflavin", "niacin", "vitB6", "folate", "vitB12", "choline"):
        expect[k] = "watersol"
    for k in ("zinc", "calcium", "magnesium", "sodium", "potassium"):
        expect[k] = "mineral"
    for k in ("carotene", "caffeine", "ethanol"):
        expect[k] = "stable"
    assert c == expect


def test_every_class_named_has_a_factor_row(host):
    c = host.py(host.K.retention.CLASSES)
    f = host.py(host.K.retention.FACTORS)
    assert set(c.values()) <= set(f)


def test_the_unclassified_kinetics_keys_pass_unscaled(host):
    # No retention row for retinol, D, E, K, iodine, selenium or efa: unscaled until one settles.
    meal = host.table({"retinol": 10, "vitD": 5, "vitE": 2, "vitK": 50, "iodine": 20, "selenium": 30, "efa": 1})
    out = host.py(host.K.retention.apply(meal, host.table({"cooked": True, "burnt": True, "rotten": True})))
    assert (out["retinol"], out["vitD"], out["vitE"], out["vitK"], out["iodine"], out["selenium"], out["efa"]) == \
        (10, 5, 2, 50, 20, 30, 1)


def test_cooking_scales_the_new_keys_by_their_class(host):
    meal = host.table({"thiamine": 1.0, "folate": 100.0, "zinc": 5.0, "carotene": 5000.0, "caffeine": 96.0})
    out = host.py(host.K.retention.apply(meal, host.table({"cooked": True})))
    assert abs(out["thiamine"] - 0.60) < 1e-9       # watersol cooked
    assert abs(out["folate"] - 60.0) < 1e-9         # watersol cooked
    assert abs(out["zinc"] - 4.75) < 1e-9           # mineral cooked
    assert abs(out["carotene"] - 5000.0) < 1e-9     # stable
    assert abs(out["caffeine"] - 96.0) < 1e-9       # stable


def test_no_macro_is_classified(host):
    c = host.py(host.K.retention.CLASSES)
    for macro in list(host.K.vector.MACROS.values()):
        assert macro not in c


def test_factor_table_values(host):
    f = host.py(host.K.retention.FACTORS)
    assert f["watersol"] == {"cooked": 0.60, "burnt": 0.36, "rotten": 0.50, "frozen": 0.95}
    assert f["mineral"] == {"cooked": 0.95, "burnt": 0.90, "rotten": 1.0, "frozen": 1.0}
    assert f["stable"] == {"cooked": 1.0, "burnt": 1.0, "rotten": 1.0, "frozen": 1.0}
    assert f["heatlabile"] == {"cooked": 0.70, "burnt": 0.49, "rotten": 1.0, "frozen": 1.0}


def test_every_factor_is_in_the_unit_interval(host):
    f = host.py(host.K.retention.FACTORS)
    for cls, states in f.items():
        for state, value in states.items():
            assert 0.0 < value <= 1.0


# --- apply(vector, flags): a new vector with per-class state factors on the mod nutrients ---

def _meal(host):
    # vitC watersol, fibre/water stable, iron mineral, phytate heatlabile; calories a macro.
    return host.table({"calories": 100, "vitC": 10, "fibre": 5, "iron": 2, "phytate": 1})


def test_cooked_scales_mod_nutrients_and_leaves_the_macro(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"cooked": True})))
    assert abs(out["vitC"] - 6.0) < 1e-9        # watersol cooked 0.60
    assert abs(out["fibre"] - 5.0) < 1e-9       # stable cooked 1.0
    assert abs(out["iron"] - 1.9) < 1e-9        # mineral cooked 0.95
    assert abs(out["phytate"] - 0.7) < 1e-9     # heatlabile cooked 0.70
    assert abs(out["calories"] - 100.0) < 1e-9  # macro untouched (eat wrapper owns the burnt /5)


def test_burnt_scales_mod_nutrients_and_does_not_divide_the_macro(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"burnt": True})))
    assert abs(out["vitC"] - 3.6) < 1e-9        # watersol burnt 0.36
    assert abs(out["iron"] - 1.8) < 1e-9        # mineral burnt 0.90
    assert abs(out["phytate"] - 0.49) < 1e-9    # heatlabile burnt 0.49
    assert abs(out["calories"] - 100.0) < 1e-9  # NOT /5 -- the caller owns that


def test_burnt_replaces_cooked_on_the_cook_axis(host):
    # burnt and cooked both set: burnt wins (vanilla clears cooked when burnt).
    out = host.py(host.K.retention.apply(_meal(host), host.table({"cooked": True, "burnt": True})))
    assert abs(out["vitC"] - 3.6) < 1e-9


def test_rotten_scales_the_water_soluble_term(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"rotten": True})))
    assert abs(out["vitC"] - 5.0) < 1e-9        # watersol rotten 0.50
    assert abs(out["fibre"] - 5.0) < 1e-9       # stable rotten 1.0
    assert abs(out["iron"] - 2.0) < 1e-9        # mineral rotten 1.0
    assert abs(out["phytate"] - 1.0) < 1e-9     # heatlabile rotten 1.0


def test_frozen_is_a_small_vitc_term(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"frozen": True})))
    assert abs(out["vitC"] - 9.5) < 1e-9        # watersol frozen 0.95
    assert abs(out["fibre"] - 5.0) < 1e-9
    assert abs(out["iron"] - 2.0) < 1e-9
    assert abs(out["phytate"] - 1.0) < 1e-9


def test_cooked_and_frozen_compose_independently(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"cooked": True, "frozen": True})))
    assert abs(out["vitC"] - 5.7) < 1e-9        # 0.60 * 0.95
    assert abs(out["phytate"] - 0.7) < 1e-9     # 0.70 * 1.0
    assert abs(out["iron"] - 1.9) < 1e-9        # 0.95 * 1.0


def test_no_flag_is_identity(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({})))
    assert abs(out["vitC"] - 10.0) < 1e-9
    assert abs(out["fibre"] - 5.0) < 1e-9
    assert abs(out["iron"] - 2.0) < 1e-9
    assert abs(out["phytate"] - 1.0) < 1e-9
    assert abs(out["calories"] - 100.0) < 1e-9


def test_apply_returns_a_new_vector_not_the_input(host):
    src = _meal(host)
    host.K.retention.apply(src, host.table({"cooked": True}))
    assert src["vitC"] == 10        # the caller's vector is untouched


def test_output_carries_every_declared_key(host):
    out = host.py(host.K.retention.apply(_meal(host), host.table({"cooked": True})))
    keys = list(host.K.vector["keys"]().values())
    assert set(out.keys()) == set(keys)


def test_an_unknown_key_is_outside_the_fixed_schema_and_is_not_scaled(host):
    # The vector shape is fixed (K.vector.add copies only declared keys), so an out-of-schema key is
    # dropped rather than carried -- it is never scaled, and the classified keys still compute.
    meal = host.table({"calories": 100, "vitC": 10, "mystery": 42})
    out = host.py(host.K.retention.apply(meal, host.table({"cooked": True})))
    assert "mystery" not in out
    assert abs(out["vitC"] - 6.0) < 1e-9


# --- the factor helper (the combined per-class multiplier) ---

def test_factor_combines_the_axes_and_clamps_to_one(host):
    f = host.K.retention["factor"]
    assert abs(f("watersol", host.table({"cooked": True})) - 0.60) < 1e-9
    assert abs(f("watersol", host.table({"burnt": True})) - 0.36) < 1e-9
    assert abs(f("watersol", host.table({"cooked": True, "frozen": True})) - 0.57) < 1e-9
    assert abs(f("stable", host.table({"cooked": True, "frozen": True, "rotten": True})) - 1.0) < 1e-9
    assert abs(f("watersol", host.table({})) - 1.0) < 1e-9
