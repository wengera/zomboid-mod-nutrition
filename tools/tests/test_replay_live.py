"""Tests for tools/replay_live.py's pure parts and its command line (Plan 11f Task 2).

The replay's oracle and its end-to-end check against the harness's own ring are kernel tests
(testing/tests/kernel/test_replay_live_oracle.py, test_replay_live_ring.py); these pin the path grammar, the start
record's forms, the ring pages' merge, the clock offset, the event engine's due rules and phase, the diff and the
readings, and the command line on the oracle backend.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import replay_live as RL  # noqa: E402

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "replay_live.py")


class FakeBackend(RL._Backend):
    """Records the order of applies, feeds and steps; its row is the step count."""

    def __init__(self):
        super().__init__()
        self.log = []
        self.n = 0

    def begin(self, age):
        self.log.append(("begin", age))

    def ev_eat(self, ev, at):
        self.log.append(("eat", ev.get("tag"), at))

    def feed(self, row, names):
        self.log.append(("feed", tuple(names), row.get("NICOTINE_WITHDRAWAL")))

    def step(self, age):
        self.n += 1
        self.log.append(("step", age))

    def row(self, paths):
        return {"n": self.n}

    def maint(self):
        return 3000.0

    def request_kcal(self, at):
        return 650.0


class TestPaths(unittest.TestCase):
    def test_plain_bracketed_and_global_segments(self):
        self.assertEqual(RL.parse_path("body.trail.kcal.3"), ([(False, "body"), (False, "trail"), (False, "kcal"),
                                                               (False, "3")], False))
        self.assertEqual(RL.parse_path("monotony.t.[Base.Bread].n"),
                         ([(False, "monotony"), (False, "t"), (True, "Base.Bread"), (False, "n")], False))
        self.assertEqual(RL.parse_path("_G.NutritionRevamp.x")[1], True)

    def test_bad_paths_raise(self):
        for bad in ("", "a..b", "[unclosed", "a.", "[a]b"):
            with self.assertRaises(ValueError, msg=bad):
                RL.parse_path(bad)

    def test_nest_builds_a_record_from_an_h1_reply(self):
        rec = RL.nest({"satiety.P": 6.5, "body.trail.kcal.3": 12.0, "monotony.t.[TKX.Mono450].n": 2.0})
        self.assertEqual(rec, {"satiety": {"P": 6.5}, "body": {"trail": {"kcal": {3: 12.0}}},
                               "monotony": {"t": {"TKX.Mono450": {"n": 2.0}}}})


class TestRing(unittest.TestCase):
    def test_pages_merge_by_s_sorted_and_paths_kept_in_order(self):
        p1 = {"paths": ["satiety.P"], "rows_list": [{"s": 3, "age": 1.05}, {"s": 1, "age": 1.0}]}
        p2 = {"paths": ["satiety.P", "body.met"], "rows_list": [{"s": 2, "age": 1.02}, {"s": 3, "age": 1.05}]}
        rows, paths = RL.load_ring([p2, p1])
        self.assertEqual([r["s"] for r in rows], [1, 2, 3])
        self.assertEqual(paths, ["satiety.P", "body.met"])

    def test_pages_load_from_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "minute-ring-admin-1.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"paths": [], "rows_list": [{"s": 1, "age": 2.0}]}, fh)
            self.assertEqual(RL.load_ring([p])[0], [{"s": 1, "age": 2.0}])

    def test_the_offset_is_the_whole_hour_inside_the_rows_range(self):
        rows = []
        for i in range(200):
            age = 30.0 + i * 0.0731
            tod = (age + 7.0) % 24
            rows.append({"s": i + 1, "age": age, "hour": int(tod), "min": int((tod - int(tod)) * 60)})
        self.assertEqual(RL.estimate_offset(rows), 7.0)
        # an offset off the whole hour: the range's low end, within a minute of it
        rows2 = [dict(r, hour=int((r["age"] + 7.5) % 24), min=int((((r["age"] + 7.5) % 24) % 1) * 60))
                 for r in rows]
        self.assertAlmostEqual(RL.estimate_offset(rows2), 7.5, delta=1 / 60)
        self.assertEqual(RL.estimate_offset([{"s": 1, "age": 1.0}]), 0.0)


class TestEngine(unittest.TestCase):
    def test_events_fall_due_by_age_s_or_minute_before_their_drain(self):
        be = FakeBackend()
        ages = [1.0, 1.5, 2.0]
        ev = [{"age": 1.2, "kind": "eat", "tag": "a"}, {"age": 2.0, "kind": "eat", "tag": "edge"},
              {"s": 11, "kind": "eat", "tag": "s"}, {"minute": 0, "kind": "eat", "tag": "m"}]
        rows = RL.run(be, ages, ev, start_age=0.9, seqs=[10, 11, 12])
        self.assertEqual([r["events"] for r in rows], [1, 2, 1])
        self.assertEqual(be.log, [("begin", 1.0), ("eat", "m", 0.9), ("step", 1.0),
                                  ("begin", 1.5), ("eat", "a", 1.2), ("eat", "s", 1.5), ("step", 1.5),
                                  ("begin", 2.0), ("eat", "edge", 2.0), ("step", 2.0)])
        self.assertEqual([r["dtM"] for r in rows], [(1.0 - 0.9) * 60, 30.0, 30.0])

    def test_an_event_at_the_start_records_age_or_before_never_falls_due(self):
        with self.assertRaises(ValueError):
            RL.run(FakeBackend(), [1.0, 2.0], [{"age": 0.5, "kind": "eat"}], start_age=0.9)
        with self.assertRaises(ValueError):
            RL.run(FakeBackend(), [1.0], [{"kind": "eat"}])

    def test_the_feed_follows_the_events_and_precedes_the_drain(self):
        be = FakeBackend()
        RL.run(be, [1.0], [{"age": 1.0, "kind": "eat", "tag": "x"}], ring_rows=[{"NICOTINE_WITHDRAWAL": 0.3}],
               feed=("NICOTINE_WITHDRAWAL",))
        self.assertEqual([x[0] for x in be.log], ["begin", "eat", "feed", "step"])

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            RL.run(FakeBackend(), [1.0], [{"age": 1.0, "kind": "teleport"}])

    def test_synthetic_ages_are_the_oracles_minute_ends(self):
        self.assertEqual(RL.synthetic_ages(3, 9.0), [9.0 + 1 / 60.0, 9.0 + 2 / 60.0, 9.0 + 3 / 60.0])
        self.assertEqual(RL.synthetic_ages(2, 0.0, 2.0), [2 / 60.0, 4 / 60.0])


class TestReadings(unittest.TestCase):
    def test_the_diff_grades_abs_and_rel_and_skips_rows_an_event_landed_before(self):
        ring = [{"s": 2, "HUNGER": 0.30, "satiety.L": 100.0}, {"s": 3, "HUNGER": 0.30, "satiety.L": 100.0},
                {"s": 4, "HUNGER": 0.30}]
        rep = [{"s": 2, "HUNGER": 0.3019, "satiety.L": 100.4}, {"s": 3, "HUNGER": 0.3021, "satiety.L": 100.6},
               {"s": 4, "HUNGER": 0.9, "between": True}, {"s": 5, "HUNGER": 0.9}]
        d = RL.diff(rep, ring)
        self.assertFalse(d["ok"])
        self.assertEqual(d["skipped"], [4])
        self.assertEqual(sorted((f["s"], f["field"]) for f in d["findings"]), [(3, "HUNGER"), (3, "satiety.L")])
        self.assertEqual(d["fields"]["HUNGER"]["n"], 2)
        self.assertEqual(d["fields"]["body.energyState"]["n"], 0)
        self.assertTrue(RL.diff(rep[:1], ring)["ok"])

    def test_the_tolerances_are_the_plans(self):
        self.assertEqual(RL.DEFAULT_TOL, {"HUNGER": ("abs", 0.002), "body.energyState": ("abs", 0.005),
                                          "satiety.L": ("rel", 0.005)})

    def test_the_request_minute_and_its_fasted_form(self):
        rows = [{"age": 10 + i / 60, "HUNGER": h} for i, h in enumerate([0.25, 0.2, 0.22, 0.24, 0.25, 0.3])]
        self.assertAlmostEqual(RL.request_minute(rows, 10.0), 4.0)
        fasted = [{"age": 10 + i / 60, "HUNGER": h} for i, h in enumerate([0.3, 0.26, 0.2, 0.26])]
        self.assertAlmostEqual(RL.request_minute(fasted, 10.0, fasted=True), 3.0)
        self.assertIsNone(RL.request_minute(rows[:2], 10.0))

    def test_intake_by_day(self):
        eats = [{"age": 8.0, "kcal": 600.0}, {"age": 23.99, "kcal": 100.0}, {"age": 24.0, "kcal": 50.0},
                {"age": 30.0, "kcal": None}]
        self.assertEqual(RL.intake_by_day(eats), {0: 700.0, 1: 50.0})

    def test_the_request_and_maint_meal_sizes(self):
        be = FakeBackend()
        self.assertEqual(be.meal_kcal({"size": "maint"}, 0), 1000.0)
        self.assertEqual(be.meal_kcal({"size": "request"}, 0), 650.0)
        self.assertEqual(be.meal_kcal({"size": 420}, 0), 420.0)


class TestStudyFoods(unittest.TestCase):
    def test_the_script_parses_and_a_declared_vector_reads_its_string(self):
        foods = RL.study_foods()
        m = foods["TKX.Mixed650"]
        self.assertEqual((m["cal"], m["carb"], m["pro"]), (650.0, 81.25, 24.375))
        self.assertEqual(m["lip"], RL.float32(25.277778))
        self.assertEqual(RL.declared_vector(m)["water"], 300.0)
        self.assertEqual(RL.declared_vector(foods["TKX.Water600"]), {"calories": 0.0, "carbs": 0.0, "lipids": 0.0,
                                                                     "proteins": 0.0, "water": 600.0})


class TestCli(unittest.TestCase):
    def test_arm_on_the_oracle_backend_writes_rows_and_eats(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev.json")
            out = os.path.join(d, "out.json")
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump([{"minute": 0, "kind": "eat", "vec": {"calories": 650.0, "proteins": 24.375,
                                                                  "carbs": 81.25, "lipids": 25.2777, "water": 300.0,
                                                                  "fibre": 6.0}}], fh)
            r = subprocess.run([sys.executable, CLI, "arm", "--events", ev, "--minutes", "30", "--backend", "oracle",
                                "--paths", "satiety.P", "--out", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(doc["mode"], "arm")
            self.assertEqual(len(doc["rows"]), 30)
            self.assertEqual(doc["eats"][0]["kcal"], 650.0)
            self.assertGreater(doc["rows"][0]["satiety.P"], doc["rows"][-1]["satiety.P"])
            self.assertIsNone(doc["diff"])

    def test_live_needs_a_ring(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev.json")
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump([], fh)
            r = subprocess.run([sys.executable, CLI, "live", "--events", ev], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
