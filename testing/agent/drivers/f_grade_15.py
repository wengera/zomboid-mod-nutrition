"""f_grade_15 -- the LLM session's report, pass 15 (Plan 33 Task 4: grade_x3 over an LLM session, the fourteenth pass's
readings under its `base` plus the group readings: the finish's head_ticks, the crawler stomped first, the group-leave
legs, the drag guard's shoves and clear steers, and the body between presses, clipped at the loop's stop, off the
record, the state log, the decision log and the goals log): the previous pass's script copied under its own key (that
script frozen; CLAUDE.md section 5) over an f_goals artifact (graded by grade_x3 of agent.base.grades.x3, `kind` "f"):
prints the grade's report_lines one finding a line, then grade_x3 as strict JSON (inf and NaN as null). d_grade.py's
form: 0 whenever the artifact was read, 2 on a bad call or an unreadable artifact.

Files read beside the artifact when they are there: `decision.log` and the `state*.log` files with
`shots/shots.jsonl` (grade_e7's readings) and `goals.log` (the model's prompts and answers, one JSON line each, read by
the eleventh pass's `load_goals`; the readings that need it say so when it is absent).

    python testing/agent/drivers/f_grade_15.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.grades.x3 import grade_x3    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402
from agent.drivers.e_grade_7 import _dir, load_log   # noqa: E402
from agent.drivers.f_grade_11 import load_goals   # noqa: E402

KIND = "f"             # the session's kind grade_x3 reads: an LLM session's base is grade_x1 over grade_f12


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade_15.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_x3(out, load_log(argv[0]), state_dir=_dir(argv[0]), goal_lines=load_goals(argv[0]), kind=KIND)
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
