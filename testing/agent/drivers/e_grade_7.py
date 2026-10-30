"""e_grade_7 -- the chain sessions' report, pass 7 (Plan 24 Task 33: grade_e6's readings plus the seven readings of survival
iteration 11: the pull, the doorway stand, the wounded fight, the fallen target, the care tick, the transparent solid and
the shot taker's index): e_grade_6.py's command line (that script frozen with the E8 and E9 artifacts' grade_e6 output; CLAUDE.md
section 5) over grade_e7, gate_e7 and report_lines_e7: prints the report
lines (the first reads `kills <n> (engine <e>, planner <p>); <survived|died at m>; <game minutes>`) one finding a line,
then the grade (or the gate) as strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifacts were read,
2 on a bad call or an unreadable artifact.

Two files are read beside an artifact when they are there: the `decision.log` (the care yield, the dead skip, the engage
and the iteration 11 readings; else the grade says so) and the `state*.log` files and the `shots/shots.jsonl` index (state.log, then the Lua's rotations state.1.log ...;
every frame of the session, the destinations and the doors; else the grade reads the kept last_frames and its
`frames_source` says so).

    python testing/agent/drivers/e_grade_7.py <artifact.json> [<prev artifact.json>]
    python testing/agent/drivers/e_grade_7.py --chain <a1.json> <a2.json> [...]      # gate_e7 over the chain
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_e import gate_e7, grade_e7, report_lines_e7    # noqa: E402


def finite(v):
    """d_grade.py finite, copied: the value with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dir(path):
    """The directory beside the artifact `path`: where its state*.log files and decision.log sit."""
    return os.path.dirname(os.path.abspath(path))


def load_log(path):
    """The decision.log lines beside the artifact `path` (dicts), else None when the file is absent or unreadable."""
    p = os.path.join(os.path.dirname(os.path.abspath(path)), "decision.log")
    try:
        with open(p, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        return None
    return [r for r in rows if isinstance(r, dict)]


def main(argv):
    chain = bool(argv) and argv[0] == "--chain"
    paths = argv[1:] if chain else argv
    if not paths or (not chain and len(paths) > 2):
        print("usage: e_grade_7.py <artifact.json> [<prev artifact.json>] | --chain <a1.json> <a2.json> ...")
        return 2
    try:
        outs = [load(p) for p in paths]
    except (OSError, ValueError) as e:
        print(f"cannot read an artifact: {type(e).__name__}: {e}")
        return 2
    logs = [load_log(p) for p in paths]
    if chain:
        res = gate_e7(outs)
        grades = [grade_e7(o, outs[i - 1] if i else None, logs[i], state_dir=_dir(paths[i])) for i, o in enumerate(outs)]
        for line in report_lines_e7(dict(grades[-1], gate=res)):
            print(line)
    else:
        res = grade_e7(outs[0], outs[1] if len(outs) > 1 else None, logs[0], state_dir=_dir(paths[0]))
        for line in report_lines_e7(res):
            print(line)
    print(json.dumps(finite(res), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
