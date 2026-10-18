"""The record backup bench (Plan 16 Task 3; Rule 6): the cost NR_Server_Backup adds to a store save.

On test_offline_freeze.py's host (the golden trace's decorated player after 4 h of play) it times BK.write (the cut,
the sum, one modData assignment, one send) against the save's own encode (K.json.encode of the record's inputs, which
F.save already runs), for the 4 h record's text and that text padded to the 30-day and the 60-monotony-entry sizes;
the median of 7 runs of 200 calls each, and the Java calls a save adds (getModData and sendServerCommand, counted).

    python tools/bench_backup.py
"""
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "testing", "tests"))
from kernel import test_offline_freeze as F  # noqa: E402

h = F.host()
p, dep = F.play(h)
r = h.record(F.NAME)
BENCH = r"""
function(BK, K, r, reps, pad)
    local calls = { md = 0, send = 0 }
    local md = {}
    local player = { getModData = function(s) calls.md = calls.md + 1; return md end }
    sendServerCommand = function(p, m, c, a) calls.send = calls.send + 1 end
    local inputs = K.store.inputsOnly(r)
    local text = K.json.encode({ gen = 1, rec = inputs, done = true }, tostring) .. pad
    local t0 = os.clock()
    for i = 1, reps do
        K.json.encode({ gen = i, rec = K.store.inputsOnly(r), done = true }, tostring)
    end
    local t1 = os.clock()
    for i = 1, reps do
        BK.write(player, text, 100 + i)
    end
    local t2 = os.clock()
    return (t1 - t0) / reps * 1000, (t2 - t1) / reps * 1000, string.len(text), calls.md / reps, calls.send / reps
end
"""
fn = h.rt.eval(BENCH)
for pad in (0, 2000, 5000):
    enc, bk = [], []
    for _ in range(7):
        e, b, n, md, sends = fn(h.NR.server.backup, h.K, r, 200, "x" * pad)
        enc.append(e); bk.append(b)
    print("text %5d chars: save encode %.3f ms, BK.write %.3f ms (%.0f %% of the encode); Java calls a save: getModData %d, sendServerCommand %d"
          % (n, statistics.median(enc), statistics.median(bk), 100 * statistics.median(bk) / statistics.median(enc), md, sends))
