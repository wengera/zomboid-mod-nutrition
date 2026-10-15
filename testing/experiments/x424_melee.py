"""x424-melee -- Plan 13 Task 1 (live): check 7's melee source, re-measured with a weapon the server owns.

x423-20261015-040740's melee window swung a client-only bat: the server logged every PlayerHitZombie packet "not
consistent" with "weapon": null and no AddXP event of any perk fired, so the source was not measured (x423's own grade,
which read the client's dead target as a hit, stays as recorded). This session adds the bat on the server, equips it
through vanilla's ISEquipWeaponAction (the harness's weapon.equip, c92ffdd7) and swings only once the server's primary
hand reads it. One boot of profile x42-calib (fixture default, admin -debug, PZTestKit and TKX_TraitLevers by its
path, no mod/ file, Nutrition false, DayLength 1, build 42.21.0). The engine is testing/experiments/x42d_melee_lib.py
(frozen with this run); its docstring names the window, the reply shapes and the grade. Written BEFORE the boot and
never edited after the run (CLAUDE.md s5).

THE ORDER: S (x42c's setting reads), E (the weapon: server add, client equip, the server's hand read), M2 (the melee
window).

PREDICTION: 7_melee -- a melee hit with a server-known weapon fires at least one positive Strength AddXP event (#2880:
OnWeaponHitXp on the server; vanilla-strength-rate s3b: + the hit count per hit, +2 when the target survives a
knockback weapon such as the bat).

RULES: 1. NEVER edited after its run. 2. A trivial, unmeasured or falsified reading is written as such, never re-run.
3. One live session at a time. 4. Free memory read before the boot, refused under 12 GB. 5. Never -safemode.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x42d_melee_lib as L   # noqa: E402

PROFILE = "x42-calib"
PREFIX = "x424"
ARTIFACT = "melee.json"
BUDGET_S = 600.0
SESSION = ("Plan 13 Task 1: check 7's melee source with a server-added, server-equipped bat (after x423's client-only "
           "bat); one boot of " + PROFILE + ", fixture default, admin the subject")
PRED = {
    "7_melee": {"melee hit, server-known bat": "at least one positive Strength AddXP event (#2880)"},
}


if __name__ == "__main__":
    L.main(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, "x424_melee.py")
