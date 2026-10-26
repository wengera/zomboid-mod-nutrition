"""c_survive_2 -- Plan 21b Stage C pass 2 (spec § 4.3's one fix pass): c_survive.py's session on the same fixture
`agent` (testing/profiles/agent.toml), run after the threat fixes to agent/policy.py.

Run 1 (c_survive-20261026-183905) died at loop wall 407 s, game minute 670, on Zombies 5. Its decision.log showed four
mechanism defects of the policy's threat branch, each fixed in policy.py before this driver:
1. engage without disengage: a fight sent at 5.9 tiles was superseded by a loot once the zombie stepped past
   DANGER_R, and the bot lost 26 health looting with its back turned (now DISENGAGE_R holds a running fight or flee);
2. fight/flee flapping at the MAX_FIGHT boundary, threats reading 3, 2, 3, 2 on consecutive ticks (now a running flee
   turns to fight only with one threat and a health margin, a running fight to flee only on the flee conditions);
3. a fight that never closed: 210 s with the zombie standing 2.74 tiles away, inside the Lua's FIGHT_R 3 but beyond
   the bat's reach, the fight swinging without approaching (endurance 0.95 to 0.32) (now a fight that runs
   FIGHT_MAX_S with its nearest threat beyond FIGHT_REACH flees);
4. the last fight, two threats taking health from 74.8 to 39.7 in 33 s before a cornered flee (now two threats under
   FLEE_HEALTH_PAIR are fled).

Everything but the key, the file, the profile and the artifact is imported from c_survive.py, which the pre-boot
checks require committed clean beside this file (c_survive's docstring is this driver's).

RULES: never edited after its run; takes no argument; one live session at a time; free memory gated at MIN_FREE_GB
before the boot; never -safemode; launched detached by the controller and polled through the persisted artifact.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent.drivers import c_survive as CS             # noqa: E402

KEY = "c_survive_2"
DRIVER = "c_survive_2.py"
PROFILE = "testing/profiles/agent.toml"
ARTIFACT = "c_survive_2.json"
RUN1 = "c_survive-20261026-183905"
BUDGET_S = CS.BUDGET_S
USER = CS.USER
MIN_FREE_GB = CS.MIN_FREE_GB
REPO = CS.REPO
_ME = os.path.basename(os.path.abspath(__file__))

SPEC = CS.Spec(KEY, DRIVER, PROFILE, ARTIFACT)
parse_argv = CS.parse_argv
Survive = CS.Survive
new_out = CS.new_out


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    return CS.driver_checks(driver_file, SPEC, repo, git_say=git_say, git_dirty=git_dirty)


def preboot(driver_file, repo=REPO):
    return CS.preboot(driver_file, SPEC, repo)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    CS.main(SPEC, _ME)
