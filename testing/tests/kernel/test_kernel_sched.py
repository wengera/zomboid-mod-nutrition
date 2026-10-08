import pytest


def lst(host, *xs):
    return host.rt.table(*xs)


def tolist(t):
    return [t[i] for i in range(1, len(t) + 1)]


def test_merge_keeps_pending_first_never_doubles_and_drops_the_departed(host):
    out = host.call("sched.merge", lst(host, "a", "b", "c"), 2, lst(host, "a", "c", "d"))
    assert tolist(out) == ["c", "a", "d"]        # b left; c still pending stays first; a re-queued once; d new


def test_merge_with_an_empty_pending_queue_is_the_roster(host):
    assert tolist(host.call("sched.merge", lst(host), 1, lst(host, "x", "y"))) == ["x", "y"]


def test_ticks_per_minute_takes_the_smaller_of_the_last_two(host):
    assert host.call("sched.ticksPerMinute", 7, 6) == 6
    assert host.call("sched.ticksPerMinute", 6, 7) == 6
    assert host.call("sched.ticksPerMinute", 1, 1) == 1            # a fast clock: one tick a minute event (#3348)
    assert host.call("sched.ticksPerMinute", None, None) == 6      # before two minutes are counted
    assert host.call("sched.ticksPerMinute", 0, None) == 6         # the boot's first minute event: no count yet
    assert host.call("sched.ticksPerMinute", 1, 0) == 1
    assert host.call("sched.ticksPerMinute", 37, None) == 37


def test_the_budget_has_a_15_ms_floor_and_grows_with_the_queue(host):
    assert host.call("sched.budgetMs", 1.6, 6, 25) == 15
    assert host.call("sched.budgetMs", 2.0, 60, 6) == pytest.approx(30.0)    # 2 x 60 / 6 x 1.5
    assert host.call("sched.budgetMs", 1.2, 58, 1) == pytest.approx(104.4)   # a fast clock runs the whole queue


def test_the_run_cap_is_at_least_one(host):
    assert host.call("sched.runCap", 15, 1.6) == 9
    assert host.call("sched.runCap", 15, 40) == 1


def test_the_mean_is_an_ema_with_a_floor(host):
    assert host.call("sched.ema", None, 2.0) == 2.0
    assert host.call("sched.ema", 2.0, 1.0) == pytest.approx(1.8)
    assert host.call("sched.ema", 0.1, 0.0) == pytest.approx(0.1)
