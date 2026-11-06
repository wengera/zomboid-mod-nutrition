"""The composition mix_1 (Plan 31 Task 13): the tactician whole, plus the ladder's lone-idle seek as the doctrine rule
`clear` and the crawler as a threat at the dressing. `assess(survive, inputs)` is the fork's entry
(`planner/control.py`); the design record is this package's README.md, `decide.py` the decider, `rules.py` the rules."""


def prepare(survive):
    """The fork's construction hook (`control.prepare_of`): the tactician's instance switches (`tactician.decide.
    prepare`: DOOR_HELD and GOAL_CONTINUE off on the instance)."""
    from agent.base.planner.tactician.decide import prepare as _prepare
    _prepare(survive)


def assess(survive, inputs):
    """The tick's Decision under mix_1 (`decide.Mix1`, kept on `survive.control_state["mix_1"]`)."""
    from agent.base.planner.mix_1.decide import mix
    return mix(survive).assess(inputs)
