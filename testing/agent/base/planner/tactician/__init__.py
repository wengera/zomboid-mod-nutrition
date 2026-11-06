"""The tactician variant (Plan 31 Task 11, T): `assess(survive, inputs)`, the fork's entry (`planner/control.py`).
The design record is this package's README.md; `decide.py` holds the decider."""


def assess(survive, inputs):
    """The tick's Decision under the tactician (`decide.Tactician`, kept on `survive.control_state["tactician"]`)."""
    from agent.base.planner.tactician.decide import tactician
    return tactician(survive).assess(inputs)
