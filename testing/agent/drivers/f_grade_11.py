"""f_grade_11 -- the LLM session's report, pass 11 (Plan 29 Task 3: grade_f11's readings, the tenth pass's plus cut 2
of the maneuver layer's reads, ruling P29-J (the kills read whole off the ladder's `targetDead` and the melee's done
`kill`, the facing over every press, the melee's swings by the arms' pain), one reading per rule of survival
iteration 23 and the views' `stall` line, read by grades.e20's readers and grades.f11's off the state log, the frames,
the artifact's actions, the decision log and the goals log): `f_grade_10.py` copied under its own key (that script
frozen; CLAUDE.md section 5) over an f_goals artifact (graded by grade_f11 of agent.base.grades.f11): prints the
grade's report_lines one finding a line, then grade_f11 as strict JSON (inf and NaN as null). d_grade.py's form: 0
whenever the artifact was read, 2 on a bad call or an unreadable artifact.

Files read beside the artifact when they are there: `decision.log` and the `state*.log` files with
`shots/shots.jsonl` (grade_e7's readings) and `goals.log` (the model's prompts and answers, one JSON line each; the
readings that need it say so when it is absent).

    python testing/agent/drivers/f_grade_11.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.grades.f11 import grade_f11    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402
from agent.drivers.e_grade_7 import _dir, load_log   # noqa: E402


def load_goals(path):
    """The goals.log rows (dicts) beside the artifact `path`, a line that does not parse skipped, else None when the
    file is absent or unreadable."""
    p = os.path.join(_dir(path), "goals.log")
    rows = []
    try:
        with open(p, encoding="utf-8") as fh:
            for ln in fh:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    rows.append(r)
    except OSError:
        return None
    return rows


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade_11.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_f11(out, None, load_log(argv[0]), state_dir=_dir(argv[0]), goal_lines=load_goals(argv[0]))
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
