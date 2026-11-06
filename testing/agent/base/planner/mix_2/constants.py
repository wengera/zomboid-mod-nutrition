"""The composition mix_2's constants (Plan 31 Task 13; `task-13-composition-read.md` section 7, mix_2): the doctrine's
own (`planner/doctrine/constants.py`, read there as `DK`, every value unchanged, its sources on its own lines), with the
tactician's two guard radii and the ladder's seek radius brought in by import. None is changed from its package (the
read: "None is changed from its package"); none asserts an engine mechanism without a row."""
from agent.base.planner.doctrine import constants as DK
from agent.base.planner.policies import ENGAGE_R as SEEK_R  # 9.0 tiles: the ladder's seek radius (`engage._sought`,
#                    ruling P24-X, Plan 24 Task 18 fix 1): the lone idle zombie listed this near is sought
from agent.base.planner.policies import FIGHT_REACH  # 2.0 tiles: the tactician's `fallen` guard radius
#                    (`Tactician._guard`: a fallen zombie this near is finished once nothing stands within KEEP_R)
from agent.base.planner.policies import KEEP_R  # 2.5 tiles: the tactician's `second_standing` radius
#                    (`FightExec.bound`), its `reach` rule's (`fallback._tests`), and the dress's clear radius (D's
#                    DRESS_CLEAR_R is KEEP_R)
from agent.base.planner.policies import MELEE_RELEASE_R  # 2.75 tiles: the tactician's `hit` guard radius (`_guard`:
#                    a hit reaction with a standing zombie this near takes the melee at the nearest)
from agent.base.planner.tactician.executors import SWING_GUARD_R  # 1.0 tiles: the tactician's `swing` guard (a
#                    standing zombie this near takes the melee in any play; P30-A's SWING_CLOSE_R)
from agent.base.planner.policies import HANDBACK_R  # 2.0 tiles: the meet's `handbackR` (Task 2), inside which a
#                    standing zombie ends a finish `handback`: the crawler's guard yields while one stands this near
#                    (fix 1, review-t13-mix2 F2a), so the guard asks only what the meet can execute
from agent.base.planner.policies import DANGER_R  # 6.0 tiles: a seek Fight whose idle pin is beyond this ends `done
#                    lapsed` once the seek's own predicate no longer holds (fix 1, review-t13-mix2 F1); inside it the
#                    Fight runs on (trial 2's 245-251 s)

HANDBACK_MAX = 3     # handbacks in a row by Fights at one pin before the pin is held out of every Fight's want for
#                    SKIP_S and the Fight ends `failed handback`, the arbiter's next answer taking the tick (fix 1,
#                    review-t13-mix2 F2b: the crowd within the meet's STAND_R 0.6 handed back before every press,
#                    probe 4's five in a row); a first guess for the trials

P_GUARD = DK.P_STRIKE   # 0: the top priority, T's guards in place of D's one-press Strike (the read's item 1)
P_DRESS, P_AVOID, P_FIGHT, P_DOOR, P_ORDER = DK.P_DRESS, DK.P_AVOID, DK.P_FIGHT, DK.P_DOOR, DK.P_ORDER   # D's
PRIORITY_NAMES = ("guard",) + DK.PRIORITY_NAMES[1:]   # ("guard", "dress", "avoid", "fight", "door", "order")

# The pieces (the decision line's `inputs.mix_2.piece`): the rule that started the running intent, so round two's rows
# can be read by piece (Task 13's build amendments, item 4).
GUARD_PIECES = ("hit", "swing", "crawler", "fallen")   # P0: the tactician's three guards and the crawler's finish
FIGHT_PIECES = ("reach", "fight", "stand", "seek", "downed")   # P3: T's `reach` rule (the re-pin's next), D's aware
#                    fight and its stand, the ladder's lone-idle seek, D's finish of a fallen zombie
PIECES = GUARD_PIECES + ("dress", "avoid") + FIGHT_PIECES + ("door", "order")

__all__ = ["DK", "SEEK_R", "FIGHT_REACH", "KEEP_R", "MELEE_RELEASE_R", "SWING_GUARD_R", "HANDBACK_R", "DANGER_R",
           "HANDBACK_MAX", "P_GUARD", "P_DRESS", "P_AVOID",
           "P_FIGHT", "P_DOOR", "P_ORDER", "PRIORITY_NAMES", "GUARD_PIECES", "FIGHT_PIECES", "PIECES"]
