"""Golden replays of the four committed live runs' `state.log` through `World` (spec § 10; the whole-pass review's I3).

Each log is streamed through `agent.base.replay.replay` (FileTransport's own tailing, delta frames merged as live); the
test asserts no bad line, no seq gap, the frame count the run's guide states, and the sha256 of the final World's
`to_json()` against a golden recorded on the first GREEN run of this test (Plan 22 fix wave P4, on top of commit
19ee80ca). A `World` or decoder change that alters what the guides read changes a hash: re-record it only under a
named behaviour change. All five were re-recorded under the named change "PZA/1.2: the square's edges, me.hour, sleep,
maxWeight" (Plan 23 Task 4, ruling P23-N, as S-31 did at PZA/1.1): the 1.1 logs decode with me.hour and the square's
blockN, blockW, edgeN and edgeW null, which the World carries; with those five null keys dropped each JSON hashed to its
previous golden (checked before re-recording). All five were re-recorded again under the named change "PZA/1.4: me's
attackers, hitReaction and dragDown, the square's hopN and hopW" (Plan 24 Task 1b, ruling P24-C): the 1.1 to 1.3 logs
decode with those five fields null, which the World carries; with the null keys dropped (every frame's me three, every
kept square's two) each JSON hashed to its previous golden, checked before re-recording. All five were re-recorded
under the named change "PZA/1.5: me's aiming" (Plan 24 Task 9, ruling P24-G): the logs decode with me.aiming null,
which the World's final me carries; with that one null key dropped each JSON hashed to its previous golden, checked
before re-recording. The three whose final body lists parts (d_survive x2, x5_combat) were re-recorded again under
"PZA/1.5: the part record's care fields": each part decodes with bleeding, bleedingTime, bandaged, bandageLife,
bandageDirty, deep and infected null; with those keys dropped (91, 119 and 119) each hashed to its previous golden. All
five were re-recorded once more under "PZA/1.5: the square record's water": every kept square decodes with water null;
with those keys dropped (788, 1827, 1052, 1052 and 234) each hashed to its previous golden. All five were
re-recorded under "PZA/1.5.4: me's forceAim" (Plan 24 Task 9 fix 6, ruling P24-T): the logs decode with me.forceAim
null, which the World's final me carries; with that one null key dropped each JSON hashed to its previous golden,
checked before re-recording. All five were re-recorded under "PZA/1.6: me's worn" (Plan 24 Task 9 fix 9, review-t18
ruling 5): the logs decode with me.worn null, which the World's final me carries; with that one null key dropped each
JSON hashed to its previous golden, checked before re-recording. All five were re-recorded under "PZA/1.7: me's loadedWidth,
body's armPain and strain and the zombie's onFloor" (Plan 24 Task 9 fix 11): the logs decode with those fields null, which the World's
final me, body and zombie records carry; with the null keys dropped (loadedWidth, armPain and strain in all five, onFloor in the
three whose final World lists a zombie) and the JSON re-serialised as to_json does (sorted keys, indent 1) each hashed to its
previous golden, checked before re-recording. The three whose final body lists parts (d_survive x2, x5_combat) were
re-recorded under "PZA/1.7.2: the part record's wound" (Plan 28 Task 1): each part decodes with wound null; with that
key dropped (13, 17 and 17 parts) and the JSON re-serialised as to_json does, each hashed to its previous golden,
checked before re-recording. All five were re-recorded under "PZA/1.9: me's sneaking and sneakLevel and the zombie's
known, state and behind" (Plan 30 Task 1): the logs decode with those fields null, which the World's final me and
zombie records carry; with the null keys dropped (me's two in all five, the zombie's three in the three whose final
World lists a zombie: 2, 2 and 5 zombies) and the JSON re-serialised as to_json does, each hashed to its previous
golden, checked before re-recording. Before recording, each streamed replay's JSON was checked equal to the
whole-file replay of `world.replay` at 19ee80ca (the function this module's replay replaced).

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
    # run id: (frames the guide states, sha256 of the final World's to_json()). The first four re-recorded under the PZA/1.1
    # field additions of 1d2e2d24 (Plan 22 X4 fix pass 1: me's zombiesSeen and zombiesListed, cost's pollMs .. maxStartMs),
    # which the X4 fix pass 1b decoder reads as None in these logs written before them: the final World carries the ten
    # keys as null, and with them removed each JSON hashed to its previous golden (checked before re-recording).
    "x4_link-20261027-171916": (7533, "30b818ab36b8c12ced0bff34e48d5dcb9e696a87fea009d28077fc1524492bf1"),
    "x5_combat-20261027-173248": (993, "6539433241d9ad2e82e54eed8bede4348a4b8423d47477f8c4bc6f4899585422"),
    "d_survive-20261027-173724": (5033, "584c73be7c6e22820e64a75dba93a2f86d87cc517f8fc97975cb31d5b7f38e4f"),
    "d_survive-20261027-175917": (2568, "c6bcfa7ca1db67f2ee9025cd549078a9dfd97878336e75969bc9f25bf1b8b854"),
    # The X4 fix pass session (PZA/1.1 written natively; the fifth live run), recorded at the close on 25d8bd6f:
    # x4_link_2-20261027-210612/GUIDE.md:15 "The driver read 7505 frames" plus the 17 frames after its last read -> 7522.
    "x4_link_2-20261027-210612": (7522, "dad57543a74ee02617fb69f8dd79914960d6574945204c9e35267c6aba3167e1"),
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
