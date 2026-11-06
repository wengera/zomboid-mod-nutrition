"""The composition mix_2 (Plan 31 Task 13; `task-13-composition-read.md` section 7): the doctrine's arbiter (one intent
at a time under six priorities, the resume slot, the goal running) with the tactician's guards fighting to the kill, its
re-pin, its dress-waits rule, the crawler as a threat, and the ladder's lone-idle seek; no string, no Strike, no
tactical model call. Read by the fork (`planner/control.py`, `Survive(control="mix_2")`). `README.md` beside this file
is the design; `assess.py` the tick, `situation.py` the wants, `intents.py` the Fight and the Dress, `seek.py` the
seek's reachability, `constants.py` the numbers with their sources."""
from agent.base.planner.mix_2.assess import assess, line_switches, prepare

__all__ = ["assess", "line_switches", "prepare"]
