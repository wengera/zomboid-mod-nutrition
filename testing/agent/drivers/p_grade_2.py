"""p_grade_2 -- the regrade of the stance probe p_stance-20261029-135919 (Plan 24 Task 19), written after the run and
before its output was staged: an ANALYSIS script, not a driver (it boots nothing; named p_grade_2, so the p_stance
prefix stays the driver's alone). `p_stance.py` and its `grade_p1` stay as committed with the run (CLAUDE.md section 5:
a grade whose output an artifact carries is never edited); this script reads the same record and prints a derived
reading beside it.

    python testing/agent/drivers/p_grade_2.py <p_stance.json>

THE DEFECT. `grade_p1` reads an aim leg from LEG_SETTLE_MS (1000 ms) after the leg's ack to its end
(`p_stance.leg_frames`), so that the stance has a second to take hold. On the backpedal leg (`aim_strafe`) the
character moved for about the first second and then stood against the living room's west wall, so the grade's window
opened after almost all of the movement and read 0.09375 tiles (`grade_p1.strafe_tiles`, `strafe_ok` false): the
last step of the walk, not the leg's movement.

THE REGRADE. The same record's `probe.frames` (every frame the loop read, compact) and `probe.steps` (each step's
ackedMs and endMs on the one host's epoch clock), with no settle: a leg's frames are those with wallMs from its
ackedMs to its endMs. Per aim leg: the frame count, and `aiming` and `forceAim` true counts. For the backpedal leg:
  - the displacement along its vector (STRAFE_VEC, the leg's own args) from the frame before the leg's first frame
    (the last frame read before the ack, the leg's start position) to its last frame;
  - the movement run: from the first leg frame whose position differs from the frame before it to the last such frame;
    its tiles along the vector, its span (the difference of the start position's frame's wallMs and the run's last
    frame's wallMs, a span on one clock, never a reading of the clock), the speed over it, and the modal
    frame-to-frame step inside it;
  - the stand after it: the frames from the run's last frame to the leg's end, their position, and how many read
    `moving` true and `pace` 0;
  - the grade's window (ackedMs + LEG_SETTLE_MS to endMs): its frame count and its tiles along the vector, which
    reproduce `grade_p1.strafe_tiles`, so the defect is shown, not asserted.
Prints one line a finding, then the reading as strict JSON. 0 when the record was read, 2 on a bad call or an
unreadable record. stdlib only; refuses any argument but the one path.
"""
import collections
import json
import math
import sys

LEG_SETTLE_MS = 1000.0            # p_stance.LEG_SETTLE_MS, copied: the grade's window opens this long after the ack
AIM_LEGS = ("aim_stand", "aim_strafe")
STRAFE = "aim_strafe"


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def window(frames, lo, hi):
    """The frames whose wallMs lies in [lo, hi]."""
    return [f for f in frames if _num(f.get("wallMs")) is not None and lo <= f["wallMs"] <= hi]


def along(a, b, vec):
    """The displacement from frame a to frame b along `vec` (normalised)."""
    n = math.hypot(*vec) or 1.0
    return ((b["x"] - a["x"]) * vec[0] + (b["y"] - a["y"]) * vec[1]) / n


def leg_reading(frames, step):
    fr = window(frames, step["ackedMs"], step["endMs"])
    return {"n": len(fr), "aiming": sum(1 for f in fr if f.get("aiming") is True),
            "forceAim": sum(1 for f in fr if f.get("forceAim") is True),
            "first_seq": fr[0]["seq"] if fr else None, "last_seq": fr[-1]["seq"] if fr else None}


def backpedal(frames, step):
    """The backpedal leg's movement (the module docstring), or {"error": ...} when the leg has no frames."""
    args = step.get("args") or {}
    vec = (float(args.get("vx", 0.0)), float(args.get("vy", 0.0)))
    fr = window(frames, step["ackedMs"], step["endMs"])
    if not fr:
        return {"error": "no frames in the leg"}
    before = [f for f in frames if _num(f.get("wallMs")) is not None and f["wallMs"] < step["ackedMs"]]
    start = before[-1] if before else fr[0]
    seq = [start] + fr
    moved = [i for i in range(1, len(seq)) if (seq[i]["x"], seq[i]["y"]) != (seq[i - 1]["x"], seq[i - 1]["y"])]
    out = {"vector": list(vec), "start": {"seq": start["seq"], "x": start["x"], "y": start["y"]},
           "end": {"seq": fr[-1]["seq"], "x": fr[-1]["x"], "y": fr[-1]["y"]},
           "leg_tiles": along(start, fr[-1], vec),
           "leg_s": (fr[-1]["wallMs"] - start["wallMs"]) / 1000.0,
           "moving_true": sum(1 for f in fr if f.get("moving") is True), "n": len(fr),
           "dirs": sorted({str(f.get("dir")) for f in fr})}
    if not moved:
        out.update(run=None, stand=None)
    else:
        last = seq[moved[-1]]
        steps = [round(math.hypot(seq[i]["x"] - seq[i - 1]["x"], seq[i]["y"] - seq[i - 1]["y"]), 9) for i in moved]
        span = (last["wallMs"] - start["wallMs"]) / 1000.0
        tiles = along(start, last, vec)
        out["run"] = {"first_seq": seq[moved[0]]["seq"], "last_seq": last["seq"], "frames": len(moved),
                      "tiles": tiles, "span_s": span, "tiles_per_s": (tiles / span) if span > 0 else None,
                      "modal_step": collections.Counter(steps).most_common(1)[0][0],
                      "steps": steps}
        rest = [f for f in fr if f["wallMs"] > last["wallMs"]]
        out["stand"] = {"frames": len(rest), "first_seq": rest[0]["seq"] if rest else None,
                        "last_seq": rest[-1]["seq"] if rest else None,
                        "positions": sorted({(f["x"], f["y"]) for f in rest}),
                        "span_s": ((rest[-1]["wallMs"] - last["wallMs"]) / 1000.0) if rest else 0.0,
                        "moving_true": sum(1 for f in rest if f.get("moving") is True),
                        "pace_zero": sum(1 for f in rest if f.get("pace") == 0)}
    gw = window(frames, step["ackedMs"] + LEG_SETTLE_MS, step["endMs"])
    out["grade_window"] = {"n": len(gw), "first_seq": gw[0]["seq"] if gw else None,
                           "tiles": along(gw[0], gw[-1], vec) if len(gw) >= 2 else None,
                           "opens_after_run": bool(gw) and out.get("run") is not None
                           and gw[0]["wallMs"] > seq[moved[0]]["wallMs"]}
    return out


def regrade(record):
    probe = record.get("probe") or {}
    frames = probe.get("frames") or []
    steps = {s.get("step"): s for s in probe.get("steps") or []}
    legs = {}
    for name in AIM_LEGS:
        s = steps.get(name)
        legs[name] = leg_reading(frames, s) if s and _num(s.get("ackedMs")) is not None else None
    bp = backpedal(frames, steps[STRAFE]) if STRAFE in steps and _num(steps[STRAFE].get("ackedMs")) is not None \
        else {"error": "no backpedal leg"}
    return {"regrade": "p_grade_2", "run_id": record.get("run_id"), "frames": len(frames), "legs": legs,
            "backpedal": bp, "grade_p1_strafe_tiles": (record.get("grade_p1") or {}).get("strafe_tiles")}


def report_lines(r):
    lines = []
    for name, leg in r["legs"].items():
        if leg is None:
            lines.append("%s: no leg" % name)
        else:
            lines.append("%s: %d frames (ack to end, no settle), aiming %d, forceAim %d (seq %s-%s)"
                         % (name, leg["n"], leg["aiming"], leg["forceAim"], leg["first_seq"], leg["last_seq"]))
    bp = r["backpedal"]
    if "error" in bp:
        lines.append("backpedal: %s" % bp["error"])
        return lines
    lines.append("backpedal: %r tiles along %r over the leg (seq %s to %s, %r s), moving on %d of %d frames, dirs %s"
                 % (bp["leg_tiles"], bp["vector"], bp["start"]["seq"], bp["end"]["seq"], bp["leg_s"],
                    bp["moving_true"], bp["n"], bp["dirs"]))
    run = bp["run"]
    if run is None:
        lines.append("backpedal: the position never changed")
    else:
        lines.append("movement: seq %s to %s, %d frame steps, %r tiles in %r s = %r tiles/s, modal step %r"
                     % (run["first_seq"], run["last_seq"], run["frames"], run["tiles"], run["span_s"],
                        run["tiles_per_s"], run["modal_step"]))
        st = bp["stand"]
        lines.append("then stood: %d frames (seq %s to %s, %r s) at %s, moving true on %d, pace 0 on %d"
                     % (st["frames"], st["first_seq"], st["last_seq"], st["span_s"], st["positions"],
                        st["moving_true"], st["pace_zero"]))
    gw = bp["grade_window"]
    lines.append("grade_p1's window (ack + %r ms): %d frames from seq %s, %r tiles (grade_p1.strafe_tiles %r); "
                 "opens after the movement began: %s"
                 % (LEG_SETTLE_MS, gw["n"], gw["first_seq"], gw["tiles"], r["grade_p1_strafe_tiles"],
                    gw["opens_after_run"]))
    return lines


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        print("usage: p_grade_2.py <p_stance.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError) as e:
        print("cannot read the record: %s: %s" % (type(e).__name__, e))
        return 2
    r = regrade(record)
    for line in report_lines(r):
        print(line)
    print(json.dumps(r, indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
