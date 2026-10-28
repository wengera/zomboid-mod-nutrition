"""Golden replays of the four committed live runs' `state.log` through `World` (spec § 10; the whole-pass review's I3).

Each log is streamed through `agent.base.replay.replay` (FileTransport's own tailing, delta frames merged as live); the
test asserts no bad line, no seq gap, the frame count the run's guide states, and the sha256 of the final World's
`to_json()` against a golden recorded on the first GREEN run of this test (Plan 22 fix wave P4, on top of commit
19ee80ca). A `World` or decoder change that alters what the guides read changes a hash: re-record it only under a
named behaviour change. Before recording, each streamed replay's JSON was checked equal to the whole-file replay
of `world.replay` at 19ee80ca (the function this module's replay replaced).

The frame counts, from each guide (the driver's `frames.n` plus the frames after its last read):
- x4_link-20261027-171916/GUIDE.md:13: "The driver read 7505 frames ... the 28 frames seq 8034-8061 came after its
  last read" -> 7533.
- x5_combat-20261027-173248/GUIDE.md:15 "The driver read 968 frames ... the 25 frames seq 1277-1301 came after", and
  GUIDE.md:58 "(`state.log`, all 993 frames)" -> 993.
- d_survive-20261027-173724/GUIDE.md:15: "The driver read 5028 frames ... the 5 frames seq 6410-6414 came after its
  last read" -> 5033.
- d_survive-20261027-175917/GUIDE.md:15: "The driver read 2556 frames ... the 12 frames seq 4825-..." -> 2568.
"""
import hashlib
import os
import time

import pytest

from agent.base import replay as R
from agent.base import world as W

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "testing", "artifacts")

LIVE = {
    # run id: (frames the guide states, sha256 of the final World's to_json()). All four re-recorded under the PZA/1.1
    # field additions of 1d2e2d24 (Plan 22 X4 fix pass 1: me's zombiesSeen and zombiesListed, cost's pollMs .. maxStartMs),
    # which the X4 fix pass 1b decoder reads as None in these logs written before them: the final World carries the ten
    # keys as null, and with them removed each JSON hashed to its previous golden (checked before re-recording).
    "x4_link-20261027-171916": (7533, "d000a505f694068c66227b384fec61629c4a1283f6b1793cff26507a14e2dc0a"),
    "x5_combat-20261027-173248": (993, "bc4a9295264516031a3a3672a72f7e719a57bf736240b905eb15205c511dc19d"),
    "d_survive-20261027-173724": (5033, "8503532354f48785af2524b508adb1b08b803ff2152a90b71f23450bd760b8a4"),
    "d_survive-20261027-175917": (2568, "68d84488a1c7da8b94c1ef142d9c3d0c0ec1aa7cd54e6b592da0e9e5f3de0a99"),
}


@pytest.mark.parametrize("run", sorted(LIVE))
def test_a_live_run_replays_clean_to_its_golden(run):
    frames, sha = LIVE[run]
    t0 = time.perf_counter()
    s = R.replay(os.path.join(ART, run, "state.log"))
    took = time.perf_counter() - t0
    assert s.bad == 0 and s.gaps == 0 and s.gap_list == []
    assert s.frames == frames
    assert s.lines >= s.frames
    assert s.sha256 == hashlib.sha256(s.world_json.encode("utf-8")).hexdigest()
    assert s.sha256 == sha, (run, s.sha256)
    assert took < 10.0, took


def test_the_summary_is_byte_stable():
    p = os.path.join(ART, "x5_combat-20261027-173248", "state.log")
    a, b = R.replay(p), R.replay(p)
    assert a.world_json == b.world_json and a.sha256 == b.sha256 and (a.lines, a.frames) == (b.lines, b.frames)


def test_the_replay_streams_in_chunks_smaller_than_the_file():
    p = os.path.join(ART, "x4_link-20261027-171916", "state.log")
    assert os.path.getsize(p) > 4 * R.CHUNK_BYTES


def test_replay_lives_outside_the_world_module():
    assert not hasattr(W, "replay") and not hasattr(W, "FileTransport")
    src = open(W.__file__, encoding="utf-8").read()
    assert "transport" not in src.split('"""', 2)[2]          # no import of a transport below the docstring
    assert not hasattr(W.World(), "replay_bad")


def test_a_bad_line_and_a_gap_are_counted(tmp_path):
    src = os.path.join(os.path.dirname(__file__), "fixtures", "pza1-synthetic-1.log")
    lines = open(src, encoding="utf-8", newline="").read().split("\n")
    del lines[5]                                              # one seq missing: a gap
    lines.insert(3, "{not json")                              # one bad line
    p = tmp_path / "other.log"
    p.write_text("\n".join(lines), encoding="utf-8", newline="")
    s = R.replay(str(p))
    assert s.bad == 1 and s.gaps == 1 and len(s.gap_list) == 1
