"""The control fork (Plan 31 Task 1): which decider answers `Survive.assess`.

`Survive(control=name)` takes one of two shapes. `"ladder"` (the default) is today's ordered branches, `Survive`'s own
`_assess_ladder`. Any other name is a package (or module) found by name under `agent.base.planner.<name>` whose
module-level `assess(survive, frame)` returns the `Decision` `Survive._apply` takes; a variant keeps its own state on
`survive.control_state` (a dict, empty at construction) and reuses the planner's reads and sends (`_read`, `_apply`,
`_care`, `_goal`, `_night`) for whatever it does not replace.

A package may also expose a module-level `prepare(survive)`, called once at construction before any read, where it sets
the instance switches it turns off (`DOOR_HELD`, `GOAL_CONTINUE`): `Survive.__init__` calls it last, once the
instance is whole and `control_state` a dict, so no driver or variant needs a hook of its own. The ladder has none.

The decision line is the contract a variant keeps: `branch == "threat"` on a fight tick, `inputs.branches.threat.flee`
holding the reason when fleeing, and `inputs.x`/`inputs.y`. The fork adds no field to the ladder's line (the six
decision goldens pin it byte for byte), so a variant names itself in its trial record, never on the line.

The name is resolved at construction (`load`), never at the first tick: an unknown name is a `ControlError` there."""
import importlib

LADDER = "ladder"
CONTROLS = (LADDER,)   # the built-in; any other name is a package found by name under `agent.base.planner`
PACKAGE = __package__   # "agent.base.planner"


class ControlError(ValueError):
    """An unknown control name, or a package that exposes no `assess(survive, frame)`."""


def _module(name):
    """The control's package or module (not for the ladder). A name that is no identifier or no package under
    `agent.base.planner` is a ControlError."""
    if not isinstance(name, str) or not name.isidentifier():
        raise ControlError(f"unknown control {name!r}: expected one of {CONTROLS} or a package name under {PACKAGE}")
    qualified = f"{PACKAGE}.{name}"
    try:
        return importlib.import_module(qualified)
    except ModuleNotFoundError as e:
        if e.name != qualified:   # the variant's own missing import is its bug, never an unknown name
            raise
        raise ControlError(f"unknown control {name!r}: expected one of {CONTROLS} or a package under {PACKAGE}") from e


def load(name):
    """The control's `assess` function, or None for the ladder (the caller runs its own body). A name that is no
    identifier, no package under `agent.base.planner`, or a package without a callable `assess` is a ControlError."""
    if name == LADDER:
        return None
    module = _module(name)
    qualified = f"{PACKAGE}.{name}"
    assess = getattr(module, "assess", None)
    if not callable(assess):
        raise ControlError(f"control {name!r} ({qualified}) exposes no assess(survive, frame)")
    return assess


def prepare_of(name):
    """The control's optional `prepare(survive)` function, or None (the ladder, or a package without one). Called by
    `Survive.__init__` once, after `control_state` is created and before any read. A `prepare` that is not callable
    is a ControlError. Call after `load(name)`, which has already vetted the name."""
    if name == LADDER:
        return None
    prepare = getattr(_module(name), "prepare", None)
    if prepare is not None and not callable(prepare):
        raise ControlError(f"control {name!r} ({PACKAGE}.{name}) has a prepare that is not callable")
    return prepare
