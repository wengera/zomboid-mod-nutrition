import os
from agent.world import replay
from agent.summary import summarize

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def test_summary_golden():
    text = summarize(replay(os.path.join(FIX, "log-synthetic-1.log")))
    with open(os.path.join(FIX, "log-synthetic-1.summary.txt"), encoding="utf-8", newline="") as f:
        assert text == f.read().rstrip("\n")


def test_summary_short_and_deterministic():
    w = replay(os.path.join(FIX, "log-synthetic-1.log"))
    assert summarize(w) == summarize(w)
    assert len(summarize(w).splitlines()) <= 25
