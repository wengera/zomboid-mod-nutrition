# Facing trials

The log of Plan 32's facing trials (ruling P31-T, CLAUDE.md § 5 "Trials"): one row per `probe` act that ended done in a boot of `testing/agent/drivers/x_facing.py`, appended by `python tools/facing_score.py <run> --seen "..."`. A trial is not evidence: no row, page or brief cites a line of this table; its run folder stays in `testing/runs/`, a row names the commit the run booted (`-dirty` for a working tree) and is never cited. The probe holds the character still in the arena and applies one facing mechanism toward a target for N client ticks, standing (`still`) or back-pedalling away from the cursor's bearing (`back`), reading the engine's own body angle before every write. The columns: the run id; the booted commit; the mode (`read`, `snap_aimed`, `unaimed_face`, `unaimed_snap`, `block_aim`, `ignore_aim`, `turn_k`); the movement; turn_k's turn delta (`-` for the others); the ring ticks; the median and the 90th percentile of the absolute error of the body angle against the bearing to the target, in degrees; the same for the look angle; the share of the ticks whose body error held within 30 degrees; the share of the ticks the character read as aiming; whether the mode pressed an attack at a zombie (`--zombie`); the health before and after that press; up to three lines of what was seen.

| run | commit | mode | move | k | ticks | body med | body p90 | look med | look p90 | hold30 | aiming | pressed | hp0 -> hp1 | seen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x_facing-20261108-205938 | 5538b21b | read | still | - | 30 | 74.9 | 74.9 | 89.9 | 90.0 | 0.00 | 0.97 | - | - | smoke boot: two modes at 30 ticks, standing and back-pedalling; the boot, the sequencer and the scorer work end to end |
| x_facing-20261108-205938 | 5538b21b | snap_aimed | still | - | 30 | 2.8 | 3.4 | 18.2 | 26.4 | 0.97 | 0.97 | - | - | smoke boot: two modes at 30 ticks, standing and back-pedalling; the boot, the sequencer and the scorer work end to end |
| x_facing-20261108-205938 | 5538b21b | read | back | - | 30 | 88.6 | 88.9 | 88.5 | 88.8 | 0.00 | 0.97 | - | - | smoke boot: two modes at 30 ticks, standing and back-pedalling; the boot, the sequencer and the scorer work end to end |
| x_facing-20261108-205938 | 5538b21b | snap_aimed | back | - | 30 | 3.4 | 3.4 | 18.3 | 18.4 | 0.97 | 0.97 | - | - | smoke boot: two modes at 30 ticks, standing and back-pedalling; the boot, the sequencer and the scorer work end to end |
| x_facing-20261108-210314 | 5538b21b | read | still | - | 60 | 75.0 | 75.0 | 90.0 | 90.0 | 0.00 | 0.98 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | snap_aimed | still | - | 60 | 2.1 | 3.3 | 42.7 | 46.9 | 0.98 | 0.98 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | unaimed_face | still | - | 60 | 15.1 | 75.9 | 10.1 | 69.9 | 0.58 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | unaimed_snap | still | - | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | block_aim | still | - | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.98 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | ignore_aim | still | - | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | turn_k | still | 3 | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | turn_k | still | 5 | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | read | back | - | 60 | 82.1 | 85.9 | 83.1 | 86.7 | 0.15 | 0.98 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | snap_aimed | back | - | 60 | 3.3 | 3.4 | 18.3 | 18.4 | 0.98 | 0.98 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | unaimed_face | back | - | 60 | 112.4 | 119.3 | 112.4 | 119.3 | 0.10 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210314 | 5538b21b | unaimed_snap | back | - | 60 | 6.8 | 9.2 | 11.8 | 14.2 | 0.98 | 0.00 | - | - | round one boot 1: every mode at 60 ticks, standing and back-pedalling, no zombie |
| x_facing-20261108-210704 | 5538b21b | read | still | - | 60 | 74.9 | 74.9 | 90.0 | 90.0 | 0.00 | 0.98 | - | - | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | snap_aimed | still | - | 60 | 2.1 | 3.3 | 42.7 | 46.8 | 0.98 | 0.98 | yes | 1.00 -> 1.00 | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | unaimed_face | still | - | 60 | 15.0 | 75.7 | 10.0 | 69.8 | 0.58 | 0.00 | - | - | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | unaimed_snap | still | - | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 1.00 | 0.00 | yes | 1.00 -> 1.00 | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | read | back | - | 60 | 82.4 | 86.2 | 83.3 | 87.0 | 0.13 | 0.98 | - | - | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | snap_aimed | back | - | 60 | 3.3 | 3.4 | 18.3 | 18.4 | 0.98 | 0.98 | yes | 1.00 -> 1.00 | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | unaimed_face | back | - | 60 | 114.1 | 121.0 | 114.1 | 121.0 | 0.10 | 0.00 | - | - | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-210704 | 5538b21b | unaimed_snap | back | - | 60 | 6.8 | 9.2 | 11.8 | 14.2 | 0.98 | 0.00 | yes | 1.00 -> 1.00 | round one boot 2: the press modes against one zombie at the target bearing, 60 ticks, standing and back-pedalling |
| x_facing-20261108-211140 | 1cc4c36f | snap_aimed | still | - | 60 | 3.1 | 4.8 | 46.9 | 49.6 | 0.98 | 0.98 | yes | 1.00 -> 1.00 | round one boot 3: the two press modes against one zombie at 1.1 tiles, 60 ticks, standing and back-pedalling |
| x_facing-20261108-211140 | 1cc4c36f | unaimed_snap | still | - | 60 | 0.0 | 0.0 | 0.0 | 0.0 | 0.98 | 0.00 | yes | 1.00 -> 1.00 | round one boot 3: the two press modes against one zombie at 1.1 tiles, 60 ticks, standing and back-pedalling |
| x_facing-20261108-211140 | 1cc4c36f | snap_aimed | back | - | 60 | 0.0 | 4.4 | 0.0 | 19.4 | 1.00 | 0.38 | yes | 1.00 -> 1.00 | round one boot 3: the two press modes against one zombie at 1.1 tiles, 60 ticks, standing and back-pedalling |
| x_facing-20261108-211140 | 1cc4c36f | unaimed_snap | back | - | 60 | 0.0 | 0.1 | 0.0 | 0.1 | 0.98 | 0.00 | yes | 1.00 -> 1.00 | round one boot 3: the two press modes against one zombie at 1.1 tiles, 60 ticks, standing and back-pedalling |

## Baseline (F17, grade_x2)

The offline read of F17 (`testing/artifacts/f_goals_17-20261108-172833/`, booted before the facing was adopted: the stance's faceThisObject under the force-aim, the meet unaimed inside faceR) by `grade_x2` (`testing/agent/base/grades/x2.py`, through `testing/agent/drivers/f_grade_14.py`; pinned by `test_grades_x2.py`): the absolute error of `me.bodyAngle` against the bearing to the act's target, in degrees, nearest rank. The presses are read at the frame at or before each press's line (82 presses; F17's leaves name no press mode); the stance ticks are the frames of every `aim` leg and every `melee` span; a break is a run of consecutive stance frames over 45 degrees. F17's log is PZA/1.10: the facing ring (`fwdAngle`, `aimAngle`) is unread.

| reading | n | body med | body p90 | hold30 |
|---|---|---|---|---|
| presses, all | 82 | 0.3 | 22.1 | 0.90 |
| presses, swing | 14 | 0.0 | 2.0 | 1.00 |
| presses, shove | 28 | 0.0 | 12.6 | 0.93 |
| presses, stomp | 39 | 1.1 | 42.0 | 0.85 |
| presses, floor | 1 | 0.0 | 0.0 | 1.00 |
| stance ticks, all | 1582 | 15.9 | 135.6 | 0.55 |
| stance ticks, aim legs | 764 | 78.2 | 164.9 | 0.18 |
| stance ticks, melee spans | 818 | 0.3 | 36.4 | 0.89 |

Breaks: 45 runs over 45 degrees, 615 frames; 36 in `aim` legs, the action sent last before each an `aim`, 0.02 to 1.30 s before the run; 9 in `melee` spans (5 at a stomp step, 2 at a shove, 1 at a head, 1 at a close), the action sent last before each a `melee`.
