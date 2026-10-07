"""The Intake helper guard (Plan 10 Task R0 fix round 2, for R1): NR_Server_Intake.lua's local num(v) answers a
number unchanged -- a NaN included -- and 0 only for a non-number, so a NaN macro getter reaches the before-snapshot
as NaN and the landing guard rejects the vector (#2833) rather than landing a 0. num is local; the public routes that
reach it are IN.readBefore (the instance's base hunger and four macros) and IN.foodInfo (carbohydrates, lipids,
proteins). An R1 move of the helper that kept NaN finite (num returning 0 for it) fails here.
"""
import math

import pytest

from . import server_host

STAND_IN = r"""
function(nanGetter)
    local item = {}
    item.getFullType = function(s) return "NRTrace.Guard" end
    item.getHungChange = function(s) return -0.2 end
    item.getThirstChangeUnmodified = function(s) return 0 end
    item.getBaseHunger = function(s) return -0.2 end
    item.getCalories = function(s) return 100 end
    item.getCarbohydrates = function(s) return 10 end
    item.getLipids = function(s) return 5 end
    item.getProteins = function(s) return 3 end
    item.getFoodType = function(s) return "Seed" end
    item.getModData = function(s) return {} end
    if nanGetter ~= nil then item[nanGetter] = function(s) return 0 / 0 end end
    local character = { getUsername = function(s) return "guard" end }
    return { item = item, character = character }
end
"""


@pytest.fixture(scope="module")
def h():
    return server_host.Host()


def _action(h, nan_getter=None):
    return h.rt.eval(STAND_IN)(nan_getter)


@pytest.mark.parametrize("getter,field", [
    ("getBaseHunger", "instBase"),
    ("getCalories", "cal"),
    ("getCarbohydrates", "carb"),
    ("getLipids", "lip"),
    ("getProteins", "pro"),
])
def test_read_before_keeps_a_nan_reading(h, getter, field):
    b = h.NR.server.intake.readBefore(_action(h, getter))
    assert math.isnan(b[field])


def test_read_before_reads_a_finite_reading_unchanged(h):
    b = h.NR.server.intake.readBefore(_action(h))
    assert (b["instBase"], b["cal"], b["carb"], b["lip"], b["pro"]) == (-0.2, 100, 10, 5, 3)


def test_read_before_reads_a_missing_getter_as_zero(h):
    a = _action(h)
    a["item"]["getProteins"] = None
    b = h.NR.server.intake.readBefore(a)
    assert b["pro"] == 0


@pytest.mark.parametrize("getter,key", [
    ("getCarbohydrates", "carbs"),
    ("getLipids", "lipids"),
    ("getProteins", "proteins"),
])
def test_food_info_keeps_a_nan_macro(h, getter, key):
    info = h.NR.server.intake.foodInfo(_action(h, getter)["item"])
    assert math.isnan(info["macros"][key])
