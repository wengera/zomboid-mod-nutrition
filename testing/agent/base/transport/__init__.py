"""The transport seam of the agent base (spec § 8): the one boundary between the PZA/1 lines and the Python that reads
them. A transport moves lines and nothing else; it knows no actions, no world and no policy.

`FileTransport` (transport/files.py) is the built one: it tails the files the Lua writes and writes `cmd.txt`.
The sidecar behind the same seam is designed here and not built:
  - a `SocketTransport` with the same two methods, `send(cmd)` and `lines()`, and the same `gaps`, `bad`, `cmd_seq`;
  - one PZA/1 line per UDP datagram, or newline-framed over TCP, the bytes unchanged from the file channel;
  - every line decoded through `pza1.decode` and its delta frames merged exactly as `FileTransport` does;
  - the seq guard unchanged: lines sorted by `seq`, a missing seq recorded in `gaps`, a malformed line counted in `bad`;
  - commands as the same one JSON line per command, `cmd_seq` rising;
  - built only if X4 fires its trigger (spec § 8 (6)); until then nothing imports a socket.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class Transport(Protocol):
    """A channel to one PZAgent client: commands out, decoded PZA/1 lines in."""

    gaps: list          # (expected seq, got seq) for every seq skipped
    bad: int            # lines dropped: malformed, outside the schema, or a delta frame without a base
    cmd_seq: int        # the seq of the last command sent

    def send(self, cmd: dict) -> None:
        """Send one command `{seq, aid, type, args}`; `seq` must be above `cmd_seq`."""
        ...

    def lines(self) -> list:
        """The lines that arrived since the last call, seq-ordered, keyed dicts, every frame full."""
        ...
