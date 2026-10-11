"""x34_regrade -- the committed re-grade of Plan 11f Task 9r (x30_regrade's precedent): x34_grade.py (da63c4ae) run as
committed, with three grade defects found on its first output (x34-grade-20261011) corrected here; x34_grade.py itself
is left as committed. Its output is a second DERIVED artifact folder testing/artifacts/x34-regrade-<date>/.

    python testing/experiments/x34_regrade.py [--out testing/artifacts/x34-regrade-YYYYMMDD]

The defects (each a grade bug, never a reading):
  R1. CLIENT_DAYEND read `abs(x or 99)`, so an exact 0.0 client-minus-server difference read 99 (falsy zero): every
      day read false although UNHAPPINESS matched exactly. Here: None only when the difference is absent.
  R2. reconnect() took the LAST offline row of the session as the end of the away span; the phase-D quit at the
      session's end is also offline, so the first online row after the join was never found (ring_first_online
      null). Here: the first contiguous offline block that starts at or after the reconnect's quit age.
  R3. release() graded the first drain after the join (a 60-game-minute step, the writer's dtS clamp maxStepS) like
      any other row; that row subtracts the target's whole fall over the away span by design (Task 9b fix 2), so it is
      graded by the reconnect reading instead and excluded from the per-row bound here (named, its s listed). It also
      emits the number of rows whose twin fell beside the rows whose stat was written (Rule 6: FLOOR_EPS).
Everything else is x34_grade's.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x34_grade as G  # noqa: E402

L = G.L
num = G.num


def away_block(S, quit_age):
    """R2: (i0, i1) of the first contiguous run of offline rows starting at or after quit_age - 0.1."""
    ring = S.ring
    i0 = next((i for i, r in enumerate(ring) if r.get("on") is False and r["age"] >= (quit_age or 0) - 0.1), None)
    if i0 is None:
        return None
    i1 = i0
    while i1 + 1 < len(ring) and ring[i1 + 1].get("on") is False:
        i1 += 1
    return i0, i1


def reconnect(sessions, K):
    eps = float(K.hybrid.FLOOR_EPS)
    out = G.reconnect(sessions, K)
    if out.get("measured") is False:
        return out
    S = next(S for S in sessions if S.pre == out["session"])
    blk = away_block(S, out.get("quit_age"))
    out.pop("ring_first_online", None)
    out.pop("ring_after_first_drain", None)
    out.pop("landed_on_target", None)
    out.pop("U_minus_twin", None)
    if blk is None:
        out["block"] = None
        return out
    i0, i1 = blk
    ring = S.ring
    out["block"] = {"first_offline_s": ring[i0]["s"], "last_offline_s": ring[i1]["s"], "rows": i1 - i0 + 1,
                    "from_age": ring[i0]["age"], "to_age": ring[i1]["age"]}
    out["offline_rows_in_block"] = i1 - i0 + 1
    before = ring[i0 - 1] if i0 > 0 else None
    on = ring[i1 + 1] if i1 + 1 < len(ring) else None
    after = ring[i1 + 2] if i1 + 2 < len(ring) else None
    keys = ("s", "age", "UNHAPPINESS", "BOREDOM", L.MOOD_U, L.MOOD_B, L.IN_UT, L.SAT_T, "norec")
    out["ring_last_online"] = {k: before.get(k) for k in keys} if before else None
    out["ring_first_online"] = {k: on.get(k) for k in keys} if on else None
    if after is not None:
        lv, tu, tb = G.twin(K, after)
        u = num(after.get("UNHAPPINESS"))
        out["ring_after_first_drain"] = {k: after.get(k) for k in keys} | {"twin_u": tu, "twin_b": tb, "level": lv}
        out["U_minus_twin"] = (u - tu) if u is not None else None
        out["U_minus_moodLast"] = (u - num(after.get(L.MOOD_U))) if u is not None and num(after.get(L.MOOD_U)) is not None else None
        out["landed_on_target"] = u is not None and abs(u - tu) <= eps + G.F32
        if on is not None and before is not None and num(on.get("UNHAPPINESS")) is not None:
            out["U_held_while_away"] = on["UNHAPPINESS"] - (num(before.get("UNHAPPINESS")) or 0)
            out["moodLast_u_held_while_away"] = (num(on.get(L.MOOD_U)) or 0) - (num(before.get(L.MOOD_U)) or 0)
            out["fall_landed"] = on["UNHAPPINESS"] - u if u is not None else None
            out["twin_fall_while_away"] = (num(before.get(L.MOOD_U)) or 0) - tu
            out["first_drain_dtM"] = ((num(after.get(L.SAT_T)) or 0) - (num(on.get(L.SAT_T)) or 0)) * 60.0
        out["landing_s"] = after["s"]
    return out


def release(sessions, rows_all, K, eats, skip_s):
    """R3: x34_grade.release with the reconnect's landing row excluded, plus the twin's falling rows."""
    keep = [x for x in rows_all if not (x["s"] in skip_s.get("s", ()) and abs(x["age"] - skip_s["age"]) < 0.5)]
    out = G.release(sessions, keep, K, eats)
    out["excluded"] = {"why": "the reconnect's landing row (graded by the reconnect reading)", "s": sorted(skip_s.get("s", ())),
                       "age": skip_s.get("age")}
    if out.get("measured"):
        rs = [x for x in keep if x["age"] >= out["from_age"]]
        prev = None
        n_fall = 0
        for x in rs:
            if prev is not None and x["twin_u"] < prev - 1e-12:
                n_fall += 1
            prev = x["twin_u"]
        out["twin_u_falling_rows"] = n_fall
        out["U_written_rows"] = sum(1 for x in rs if x["U"] != x["U_prev"])
        out["B_written_down_rows"] = sum(1 for x in rs if x["B"] < x["B_prev"] and not x["near_b_set"])
    return out


def client_dayend(days):
    """R1: per day, both client-minus-server differences within 0.05 (None when either is absent)."""
    out = {}
    for d, v in days.items():
        du, db = v.get("client_minus_server_U"), v.get("client_minus_server_B")
        out[d] = None if du is None or db is None else (abs(du) <= 0.05 and abs(db) <= 0.05)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(G.ART, "x34-regrade-%s" % datetime.date.today().strftime("%Y%m%d"))
    tmp = out + "-base"
    G.main(["--out", tmp])
    K = G.kernel()
    sessions = []
    for pre, doc in G.CHAIN:
        try:
            sessions.append(G.Sess(pre, doc))
        except SystemExit as e:
            print("skip %s: %s" % (pre, e))
    with open(os.path.join(tmp, "rows.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    with open(os.path.join(tmp, "summary.json"), encoding="utf-8") as fh:
        summ = json.load(fh)
    rows_all = []
    for S in sessions:
        rows_all += G.row_table(S, K)
    r13 = rows["row13"]
    rc = reconnect(sessions, K)
    r13["reconnect"] = rc
    skip = {"s": {rc["landing_s"]} if rc.get("landing_s") is not None else set(),
            "age": num((rc.get("ring_after_first_drain") or {}).get("age")) or -1.0}
    r13["release"] = release(sessions, rows_all, K, r13["eats"], skip)
    V = summ["verdicts"]
    V["CLIENT_DAYEND"] = client_dayend(r13["days"]["days"])
    V["RECONNECT_LANDED"] = rc.get("landed_on_target")
    V["D_RELEASE"] = ({k: r13["release"][k]["over"] == 0 for k in ("U", "B")} if r13["release"].get("measured") else None)
    summ["regrade"] = {"commit": G._git("log", "-1", "--format=%h", "--", "testing/experiments/x34_regrade.py"),
                       "base_grade_commit": summ.get("grade_commit"), "fixed": ["R1 CLIENT_DAYEND", "R2 reconnect",
                                                                                 "R3 release"]}
    os.makedirs(out, exist_ok=True)
    for name, obj in (("rows.json", rows), ("summary.json", summ)):
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True, default=str)
    for f in os.listdir(tmp):
        if f not in ("rows.json", "summary.json"):
            with open(os.path.join(tmp, f), encoding="utf-8") as src, \
                    open(os.path.join(out, f), "w", encoding="utf-8", newline="\n") as dst:
                dst.write(src.read())
    import shutil
    shutil.rmtree(tmp)
    print(json.dumps({k: V[k] for k in ("CLIENT_DAYEND", "RECONNECT_LANDED", "D_RELEASE")}, indent=1, default=str))


if __name__ == "__main__":
    main()
