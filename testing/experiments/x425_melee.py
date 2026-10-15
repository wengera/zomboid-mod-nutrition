"""x425-melee -- Plan 13 Task 1 (live): check 7's melee source with a weapon the server owns, after x424.

x423-20261015-040740 swung a client-only bat (every PlayerHitZombie packet "not consistent", "weapon": null, no AddXP
event of any perk); x424-20261015-041802 never swung (the server's inventory.add did not reach the client's inventory,
so weapon.equip found no bat, and no zombie came within 2 tiles in 60 s). This session adds the bat through RCON
additem (the route whose item reaches the client), asks weapon.equip until it answers ok, swings only once the
server's primary hand reads the bat, and searches 120 s for a zombie. One boot of profile x42-calib (fixture default,
admin -debug, PZTestKit and TKX_TraitLevers by its path, no mod/ file, Nutrition false, DayLength 1, build 42.21.0).
The engine is testing/experiments/x42e_melee_lib.py (frozen with this run) on x42d_melee_lib.py and x42c_calib_lib.py
(both frozen). Written BEFORE the boot and never edited after the run (CLAUDE.md s5).

THE ORDER: S (x42c's setting reads), E (the weapon: RCON additem, client equip, the server's hand read), M2 (the melee
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
import x42e_melee_lib as L   # noqa: E402

PROFILE = "x42-calib"
PREFIX = "x425"
ARTIFACT = "melee.json"
BUDGET_S = 600.0
SESSION = ("Plan 13 Task 1: check 7's melee source with an RCON-added, client-equipped bat the server's hand reads "
           "(after x423's client-only bat and x424's unsynced add); one boot of " + PROFILE + ", fixture default, "
           "admin the subject")
PRED = {
    "7_melee": {"melee hit, server-known bat": "at least one positive Strength AddXP event (#2880)"},
}


if __name__ == "__main__":
    L.main(PROFILE, PREFIX, ARTIFACT, SESSION, PRED, BUDGET_S, "x425_melee.py")
