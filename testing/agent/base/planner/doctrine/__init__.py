"""The doctrine variant (Plan 31 Task 11, D): one intent at a time under six hard priorities, read by the fork
(`planner/control.py`, `Survive(control="doctrine")`). `README.md` beside this file is the design; `assess.py` the
tick, `situation.py` the wants, `arbiter.py` the priorities and the resume slot, `intents.py` the intents,
`source.py` the goal source's resume and prefetch, `constants.py` the numbers with their sources."""
from agent.base.planner.doctrine.assess import assess

__all__ = ["assess"]
