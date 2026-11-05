"""f_grade_12 -- the LLM session's report, pass 12 (Plan 30 Task 4: grade_f12's readings, the eleventh pass's plus the
hits as the union of the reaction runs and the reflex's hit steps, the kills matched to the press before each death,
one reading per rule of survival iteration 24 and the standing minutes, read by grades.e21's readers off the state log,
the frames, the artifact's actions and the decision log): the previous pass's script copied under its own key (that
script frozen; CLAUDE.md section 5) over an f_goals artifact (graded by grade_f12 of agent.base.grades.f12): prints the
grade's report_lines one finding a line, then grade_f12 as strict JSON (inf and NaN as null). d_grade.py's form: 0
whenever the artifact was read, 2 on a bad call or an unreadable artifact.

Files read beside the artifact when they are there: `decision.log` and the `state*.log` files with
`shots/shots.jsonl` (grade_e7's readings) and `goals.log` (the model's prompts and answers, one JSON line each, read by
the previous pass's `load_goals`; the readings that need it say so when it is absent).

    python testing/agent/drivers/f_grade_12.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.grades.f12 import grade_f12    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402
from agent.drivers.e_grade_7 import _dir, load_log   # noqa: E402
from agent.drivers.f_grade_11 import load_goals   # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade_12.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_f12(out, None, load_log(argv[0]), state_dir=_dir(argv[0]), goal_lines=load_goals(argv[0]))
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
