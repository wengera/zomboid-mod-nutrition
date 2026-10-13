"""The ghost run restores its carrier's macros (Plan 11b Task 2 fix 1), offline: with the real player's record seeded
with intake, a ghost load of the mod's queue marks the real player's slot dirty 0 times and lands 0 ghost reconciles
in the reconcile counters, because H0.work reads the carrier's four macro stores before the run and sets them back."""
from .test_harness_modq import boot, cmd

MINUTES = 120
TPM = 6


def test_seeded_ghost_load_gives_no_real_player_marks_and_no_reconcile_landings():
    h = boot()
    NR, K, T = h.NR, h.K, h.T
    marks = h.rt.eval("""function(S)
        local c = { admin = 0 }
        local base = S.mark
        S.mark = function(u) if u == 'admin' then c.admin = c.admin + 1 end return base(u) end
        return c end""")(NR.server.store)

    def step_minute():
        h.minute()
        for _ in range(TPM):
            T.age = T.age + 1.0 / 60 / TPM
            h.tick(1)

    for _ in range(5):
        step_minute()
    rec = h.record("admin")
    for _ in range(5):
        v = K.vector.new()
        v.calories = 450.0
        v.carbs = 60.0
        v.lipids = 15.0
        v.proteins = 20.0
        NR.server.intake.land(rec, "admin", v)
    for _ in range(3):
        step_minute()
    RC = NR.server.reconcile
    r = cmd(h, "ghost.load", "9", "mod", "feed")
    assert r.ok, r.reason
    cmd(h, "ghost.modq", "on")
    landed0, marks0 = RC.stats.landed, marks.admin
    for _ in range(MINUTES):
        step_minute()
    assert h.H0.g.runs > 0 and h.H0.g.failures == 0
    assert marks.admin - marks0 == 0
    assert RC.stats.landed - landed0 == 0
