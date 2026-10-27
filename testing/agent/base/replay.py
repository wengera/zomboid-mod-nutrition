"""Replay a PZA/1 `state.log` through the World (spec § 10): the golden replays of the live runs read this.

`replay(path) -> ReplaySummary` streams the file through `FileTransport`'s own tailing, so delta frames merge, partial
lines wait and seq gaps count exactly as they do live: the file is copied `CHUNK_BYTES` at a time into a temporary
directory's `state.log`, the transport's `lines()` is read after each chunk, and every line is applied to one `World`;
no list of the whole file's lines is ever held. A replay reads the one file it is given (a live run's rotations and
chunk files are not followed; the committed artifacts hold a single `state.log` each).

The summary: `lines` (every line the transport returned), `frames` (the full frames among them), `bad` (the
transport's dropped lines), `gaps` (the number of seq gaps) and `gap_list` (each `(expected, got)`), `world` (the final
World), `world_json` (its `to_json()`: sorted keys, byte-stable) and `sha256` (of that JSON's UTF-8 bytes).

Moved out of `world.py` (the whole-pass review's M6) so the World depends on no transport.
"""
import dataclasses
import hashlib
import os
import tempfile

from agent.base.transport.files import FileTransport
from agent.base.world import World

CHUNK_BYTES = 256 * 1024   # bytes copied into the temporary state.log between two reads of the transport


@dataclasses.dataclass(frozen=True)
class ReplaySummary:
    lines: int
    frames: int
    bad: int
    gaps: int
    gap_list: list
    world: World
    world_json: str
    sha256: str


def replay(path):
    """The ReplaySummary of one state.log (any file name) streamed through FileTransport into a World."""
    w = World()
    n_lines = n_frames = 0
    with tempfile.TemporaryDirectory() as d:
        tr = FileTransport(d)
        with open(path, "rb") as src, open(os.path.join(d, "state.log"), "wb") as dst:
            while True:
                chunk = src.read(CHUNK_BYTES)
                if chunk:
                    dst.write(chunk)
                    dst.flush()
                for line in tr.lines():
                    n_lines += 1
                    n_frames += line["kind"] == "frame"
                    w.apply(line)
                if not chunk:
                    break
        bad, gap_list = tr.bad, list(tr.gaps)
    text = w.to_json()
    return ReplaySummary(lines=n_lines, frames=n_frames, bad=bad, gaps=len(gap_list), gap_list=gap_list, world=w,
                         world_json=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
