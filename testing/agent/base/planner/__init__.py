"""The planner (spec § 3): scripted policies now, an LLM tool-caller later; both read World and call Actions.

A `Planner` is ticked by its driver after the driver pumped the transport's lines into the World and Actions:
`tick(world, actions)` decides from the World, sends at most one typed command through `actions.send`, and returns
the `Action` it sent or None; `log_path` is the file its one decision line a tick goes to. A planner never reads
`cmd.txt` or the state lines itself. `survive.Survive` is the scripted one; `policies` holds its multi-step machines.
"""
from typing import Optional, Protocol, runtime_checkable

from agent.base.actions import Action


@runtime_checkable
class Planner(Protocol):
    log_path: str

    def tick(self, world, actions) -> Optional[Action]:
        ...
