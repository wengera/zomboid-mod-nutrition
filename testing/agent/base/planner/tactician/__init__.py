"""The tactician variant (Plan 31 Task 11, T): `assess(survive, inputs)`, the fork's entry (`planner/control.py`).
The design record is this package's README.md; `decide.py` holds the decider."""


def prepare(survive):
    """The fork's construction hook (`control.prepare_of`): the instance switches this variant drops
    (`decide.prepare`)."""
    from agent.base.planner.tactician.decide import prepare as _prepare
    _prepare(survive)


def assess(survive, inputs):
    """The tick's Decision under the tactician (`decide.Tactician`, kept on `survive.control_state["tactician"]`)."""
    from agent.base.planner.tactician.decide import tactician
    return tactician(survive).assess(inputs)
