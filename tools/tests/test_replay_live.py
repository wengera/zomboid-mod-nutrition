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
        rec = RL.nest({"satiety.M": 6.5, "body.trail.kcal.3": 12.0, "monotony.t.[TKX.Mono450].n": 2.0})
        self.assertEqual(rec, {"satiety": {"M": 6.5}, "body": {"trail": {"kcal": {3: 12.0}}},
                               "monotony": {"t": {"TKX.Mono450": {"n": 2.0}}}})


class TestRing(unittest.TestCase):
    def test_pages_merge_by_s_sorted_and_paths_kept_in_order(self):
        p1 = {"paths": ["satiety.M"], "rows_list": [{"s": 3, "age": 1.05}, {"s": 1, "age": 1.0}]}
        p2 = {"paths": ["satiety.M", "body.met"], "rows_list": [{"s": 2, "age": 1.02}, {"s": 3, "age": 1.05}]}
        rows, paths = RL.load_ring([p2, p1])
        self.assertEqual([r["s"] for r in rows], [1, 2, 3])
        self.assertEqual(paths, ["satiety.M", "body.met"])

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
        self.assertEqual(sorted((f["s"], f["field"]) for f in d["findings"] if "s" in f),
                         [(3, "HUNGER"), (3, "satiety.L")])
        self.assertEqual([f["field"] for f in d["findings"] if "s" not in f], ["body.energyState"])
        self.assertEqual(d["fields"]["HUNGER"]["n"], 2)
        self.assertTrue(RL.diff(rep[:1], ring, {"HUNGER": ("abs", 0.002), "satiety.L": ("rel", 0.005)})["ok"])

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


class TestFix1(unittest.TestCase):
    """Plan 11f Task 2 fix round 1: the empty comparison, the feed guard, the link classes and the contracts."""

    def test_a_field_compared_on_no_row_is_a_finding(self):
        ring = [{"s": 2, "HUNGER": 0.30}]
        rep = [{"s": 2, "HUNGER": 0.30}]
        d = RL.diff(rep, ring)
        self.assertFalse(d["ok"])
        self.assertEqual(sorted(f["field"] for f in d["findings"]), ["body.energyState", "satiety.L"])
        self.assertTrue(all(f["n"] == 0 for f in d["findings"]))
        d2 = RL.diff([], [], {"HUNGER": ("abs", 0.002)})
        self.assertFalse(d2["ok"])
        self.assertEqual(d2["findings"], [{"field": "HUNGER", "n": 0, "why": "compared on 0 rows"}])

    def test_the_feed_takes_only_the_exogenous_inputs(self):
        self.assertEqual(RL.ALLOWED_FEED, ("NICOTINE_WITHDRAWAL",))
        for bad in ("HUNGER", "M", "S", "L", "es", "satiety.M", "satiety.S", "satiety.L", "body.energyState",
                    "FATIGUE", "THIRST", "BOREDOM", "UNHAPPINESS", "STRESS", "nonsense"):
            with self.assertRaises(ValueError, msg=bad):
                RL.run(FakeBackend(), [1.0], [], ring_rows=[{bad: 0.3}], feed=(bad,))
            with self.assertRaisesRegex(ValueError, "graded" if bad in RL.GRADED_FEED else "exogenous", msg=bad):
                RL.check_feed((bad,))
        self.assertEqual(set(RL.GRADED_FEED), {"HUNGER", "M", "S", "L", "es", "satiety.M", "satiety.S", "satiety.L",
                                               "body.energyState", "FATIGUE", "THIRST", "BOREDOM", "UNHAPPINESS"})
        be = FakeBackend()
        RL.run(be, [1.0], [], ring_rows=[{"NICOTINE_WITHDRAWAL": 0.3}], feed=RL.ALLOWED_FEED)
        self.assertIn(("feed", ("NICOTINE_WITHDRAWAL",), 0.3), be.log)

    def test_the_links_mark_gaps_suspects_and_offline_rows(self):
        use = [{"s": 1, "ev": 1, "drained": 1, "age": 1.0, "on": True},
               {"s": 2, "ev": 2, "drained": 2, "age": 1.0 + 1 / 60, "dtM": 1.0, "on": True},
               {"s": 4, "ev": 4, "drained": 4, "age": 1.0 + 3 / 60, "dtM": 2.0, "on": True},      # s jump, dtM
               {"s": 5, "ev": 6, "drained": 5, "age": 1.0 + 4 / 60, "dtM": 1.0, "on": True},      # ev jump
               {"s": 6, "ev": 7, "drained": 5, "age": 1.0 + 5 / 60, "dtM": 1.0, "on": True},      # not drained
               {"s": 7, "ev": 8, "drained": 6, "age": 1.0 + 6 / 60, "dtM": 1.03, "on": True},
               {"s": 8, "ev": 9, "drained": 7, "age": 1.0 + 7 / 60, "dtM": 1.0, "on": False},
               {"s": 9, "ev": 10, "drained": 7, "age": 1.0 + 8 / 60, "dtM": 1.0, "on": True, "norec": True},
               {"s": 10, "ev": 11, "drained": 8, "age": 1.0 + 9 / 60, "dtM": 1.0, "on": True}]
        m = RL.link_marks(use)
        # a lost row with no ev and a one-minute dtM is still a gap: s alone shows it
        only_s = RL.link_marks([{"s": 1, "age": 1.0}, {"s": 3, "age": 1.0 + 1 / 60, "dtM": 1.0}])
        self.assertEqual(only_s[0]["gap"], True)
        self.assertEqual([x["gap"] for x in m], [False, True, True, False, False, False, False, False, False])
        self.assertEqual([x["suspect"] for x in m], [False, False, False, True, False, False, False, False, False])
        self.assertEqual([x["offline"] for x in m], [False, False, False, False, False, True, True, False, False])
        self.assertEqual(RL.offline_row(use[6]), True)
        self.assertEqual(RL.offline_row(use[7]), False)         # online with no record: the first sight drains
        self.assertEqual(RL.offline_row(use[8]), False)

    def test_quantized_dtm_is_not_a_gap_and_a_long_minute_is(self):
        # ruling S0-1: the server's ticks alternate dtM 0.8 / 1.6 at speed 5 and 0.94-1.11 at speed 1
        def rows(dtms):
            return [{"s": i + 1, "ev": i + 1, "drained": i + 1, "age": 1.0 + i / 60, "dtM": d, "on": True}
                    for i, d in enumerate(dtms)]
        quant = RL.link_marks(rows([0.8, 1.6, 0.8, 1.6, 0.8, 1.6, 1.1, 0.94]))
        self.assertEqual([m["gap"] for m in quant], [False] * 8)
        long_ = RL.link_marks(rows([0.8, 1.6, 2.4, 0.8]))
        self.assertEqual([m["gap"] for m in long_], [False, True, False, False])
        edge = RL.link_marks(rows([1.0, 2.05, 2.06]))
        self.assertEqual([m["gap"] for m in edge], [False, True, False])

    def test_an_online_first_sight_row_is_drained_not_offline(self):
        ring = [{"s": 1, "age": 1.0, "on": False}, {"s": 2, "age": 1.0 + 1 / 60, "on": True, "norec": True},
                {"s": 3, "age": 1.0 + 2 / 60, "on": True}]
        be = FakeBackend()
        be.away = False
        offline = [k for k, r in enumerate(ring) if RL.offline_row(r)]
        self.assertEqual(offline, [0])
        out = RL.run(be, [r["age"] for r in ring], [], offline=offline)
        self.assertEqual([r.get("offline", False) for r in out], [True, False, False])
        self.assertEqual(be.n, 2)                               # the first-sight row stepped

    def test_the_diff_counts_each_class_grades_gaps_and_skips_suspect_and_offline_rows(self):
        ring = [{"s": s, "HUNGER": 0.3} for s in range(2, 7)]
        rep = [{"s": 2, "HUNGER": 0.3}, {"s": 3, "HUNGER": 0.9, "gap": True}, {"s": 4, "HUNGER": 0.9, "suspect": True},
               {"s": 5, "HUNGER": 0.9, "offline": True}, {"s": 6, "HUNGER": 0.9, "between": True}]
        d = RL.diff(rep, ring, {"HUNGER": ("abs", 0.002)})
        self.assertEqual(d["classes"], {"gap": 1, "suspect": 1, "offline": 1, "between": 1})
        self.assertEqual(d["suspect"], [4])
        self.assertEqual(d["offline"], [5])
        self.assertEqual(d["skipped"], [6])
        self.assertEqual(d["gap"], [3])
        self.assertEqual(d["fields"]["HUNGER"]["n"], 2)
        self.assertEqual([(f["s"], f.get("gap")) for f in d["findings"]], [(3, True)])

    def test_the_contracts_are_in_the_docstring_and_the_help(self):
        doc = " ".join(RL.__doc__.split())
        for text in ("lastIntake.frac", "never from satiety.M", "start-read-age", "no eat since the last drain",
                     "offline", "suspect", "gap"):
            self.assertIn(text, doc)
        for mode in ("live", "arm"):
            r = subprocess.run([sys.executable, CLI, mode, "--help"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            h = " ".join(r.stdout.split())
            self.assertIn("lastIntake.frac", h)
            self.assertIn("never from satiety.M", h)
        r = subprocess.run([sys.executable, CLI, "live", "--help"], capture_output=True, text=True)
        h = " ".join(r.stdout.split())
        self.assertIn("--start-read-age", h)
        self.assertIn("no eat since the last drain", h)

    def test_the_cli_exits_non_zero_on_an_empty_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev.json")
            ring = os.path.join(d, "ring.json")
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump([], fh)
            with open(ring, "w", encoding="utf-8") as fh:
                json.dump({"paths": [], "rows_list": [{"s": i + 1, "age": 1.0 + i / 60.0} for i in range(5)]}, fh)
            r = subprocess.run([sys.executable, CLI, "arm", "--events", ev, "--ring", ring, "--backend", "oracle"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn("FAIL", r.stderr)


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
                                "--paths", "satiety.M", "--out", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(doc["mode"], "arm")
            self.assertEqual(len(doc["rows"]), 30)
            self.assertEqual(doc["eats"][0]["kcal"], 650.0)
            self.assertGreater(doc["rows"][0]["satiety.M"], 500.0)                   # fed in full at the eat
            self.assertGreater(doc["rows"][0]["satiety.M"], doc["rows"][-1]["satiety.M"])   # then only cleared
            self.assertIsNone(doc["diff"])

    def test_live_needs_a_ring(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev.json")
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump([], fh)
            r = subprocess.run([sys.executable, CLI, "live", "--events", ev], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)


class TestEngineOrder(unittest.TestCase):
    # Plan 11f Task 2b: minute-keyed events are bucketed by step (a long replay need not scan every event every minute)
    def test_events_due_at_one_drain_apply_in_the_lists_order_whatever_their_key(self):
        be = FakeBackend()
        ev = [{"age": 1.5, "kind": "eat", "tag": "a1"}, {"minute": 1, "kind": "eat", "tag": "m1"},
              {"s": 11, "kind": "eat", "tag": "s1"}, {"minute": 1, "kind": "eat", "tag": "m2"},
              {"age": 1.2, "kind": "eat", "tag": "a2"}, {"minute": 2, "kind": "eat", "tag": "m3"}]
        rows = RL.run(be, [1.0, 1.5, 2.0], ev, start_age=0.9, seqs=[10, 11, 12])
        self.assertEqual([r["events"] for r in rows], [0, 5, 1])
        self.assertEqual([x[1] for x in be.log if x[0] == "eat"], ["a1", "m1", "s1", "m2", "a2", "m3"])

    def test_a_minute_event_past_the_last_step_still_never_falls_due(self):
        with self.assertRaises(ValueError):
            RL.run(FakeBackend(), [1.0, 2.0], [{"minute": 5, "kind": "eat"}], start_age=0.9)


if __name__ == "__main__":
    unittest.main()


class TestAutodrinkDetector(unittest.TestCase):
    """Plan 11f Task 4 fix round 1 (F-T4-2): the engine's auto-drink is read off the ring's liquid lane."""

    @staticmethod
    def _ring(liquid, sips=None):
        sips = sips or [0] * len(liquid)
        return [{"s": i + 1, "age": 1.0 + i / 60.0, "stomach.liquid": g,
                 RL.AUTODRINK_SIPS: sips[i], RL.AUTODRINK_EATS: 0} for i, g in enumerate(liquid)]

    def test_an_unlogged_rise_is_one_drink_of_its_mass_at_its_row(self):
        ring = self._ring([0.0, 0.0, 200.0, 191.0, 180.0, 170.0])
        out = RL.detect_autodrinks(ring, [])
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["s"], out[0]["kind"], out[0]["fluid"]), (3, "drink", "Water"))
        self.assertAlmostEqual(out[0]["litres"], 0.2)
        self.assertEqual(out[0]["label"], "autodrink")

    def test_a_logged_drink_or_a_counted_sip_is_not_injected(self):
        ring = self._ring([0.0, 0.0, 200.0, 191.0, 180.0, 170.0])
        logged = [{"s": 3, "kind": "drink", "fluid": "Water", "litres": 0.2}]
        self.assertEqual(RL.detect_autodrinks(ring, logged), [])
        counted = self._ring([0.0, 0.0, 200.0, 191.0], sips=[0, 0, 5, 5])
        self.assertEqual(RL.detect_autodrinks(counted, []), [])

    def test_decay_and_small_wobble_are_not_a_rise(self):
        self.assertEqual(RL.detect_autodrinks(self._ring([100.0, 90.0, 80.0, 82.0, 70.0]), []), [])

    def test_a_ring_without_the_liquid_lane_is_refused(self):
        with self.assertRaises(ValueError):
            RL.detect_autodrinks([{"s": 1, "age": 1.0}, {"s": 2, "age": 1.1}], [])


class TestSleepOptionCli(unittest.TestCase):
    def test_live_requires_the_sleep_option(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev.json")
            pg = os.path.join(d, "page.json")
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump([], fh)
            with open(pg, "w", encoding="utf-8") as fh:
                json.dump({"rows_list": [{"s": 1, "age": 1.0, "dtM": 1.0}], "paths": []}, fh)
            r = subprocess.run([sys.executable, CLI, "live", "--ring", pg, "--events", ev], capture_output=True,
                               text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("sleep", r.stderr)

    def test_the_option_resolves_from_the_flag_or_the_start_document(self):
        self.assertIs(RL.resolve_sleep_allowed(True, None), True)
        self.assertIs(RL.resolve_sleep_allowed(None, {"sleepAllowed": False}), False)
        self.assertIs(RL.resolve_sleep_allowed(False, {"sleepAllowed": True}), False)
        with self.assertRaises(ValueError):
            RL.resolve_sleep_allowed(None, {})
        with self.assertRaises(ValueError):
            RL.resolve_sleep_allowed(None, None)
        self.assertEqual(RL.parse_bool("true"), True)
        self.assertEqual(RL.parse_bool("false"), False)
        with self.assertRaises(ValueError):
            RL.parse_bool("maybe")


class ReplayConstantsTest(unittest.TestCase):
    """Plan 11g Task 7: a ring replays at its recording build's kernel constants (ServerReplay's `constants`)."""

    def test_the_constants_are_set_on_the_server_host_and_an_unknown_one_is_refused(self):
        be = RL.ServerReplay(constants=RL.DEFICIT_11F)
        for name, value in RL.DEFICIT_11F.items():
            mod, key = name.split(".")
            if mod != "replay":
                self.assertEqual(be.K[mod][key], value)
        self.assertNotEqual(RL.ServerReplay().K.deficit.BALANCE_SPAN_KCAL, 3100.0)      # the shipped fit moved it
        with self.assertRaises(ValueError):
            RL.ServerReplay(constants={"deficit.NO_SUCH": 1.0})
        with self.assertRaises(ValueError):
            RL.ServerReplay(constants={"nosuch.BALANCE_SPAN_KCAL": 1.0})
        with self.assertRaises(ValueError):
            RL.ServerReplay(constants={"replay.NO_SUCH": 1.0})

    def test_the_11f_rings_replay_their_deficit_floor_which_the_shipped_kernel_lacks(self):
        # Plan 11g Task 7 fix 1 (ruling T7-1): the kernel lost the deficit floor; the 11f rings were recorded with
        # 0.02 x max(0, es - 1) added to the hunger target (and taken off first by its inverse), so DEFICIT_11F carries
        # it as a replay-only constant that restores the recording build's two functions on that replay's host only
        self.assertEqual(RL.DEFICIT_11F["replay.DEFICIT_FLOOR"], 0.02)
        be = RL.ServerReplay(constants=RL.DEFICIT_11F)
        ht, un = be.K.deficit.hungerTarget, be.K.deficit.unsated
        self.assertAlmostEqual(ht(1.0, 1.5), 0.01, places=12)
        self.assertAlmostEqual(ht(0.7, 1.5), 0.3 * 1.5 + 0.01, places=12)
        self.assertEqual(ht(0.0, 1.9), 1)                                     # clamped
        self.assertAlmostEqual(ht(0.7, 0.8), 0.3 * 0.8, places=12)            # no floor in a surplus
        self.assertAlmostEqual(un(0.46, 1.5), (0.46 - 0.01) / 1.5, places=12)
        shipped = RL.ServerReplay()
        self.assertIsNone(shipped.K.deficit.DEFICIT_FLOOR)
        self.assertEqual(shipped.K.deficit.hungerTarget(1.0, 1.5), 0)       # the shipped kernel has no floor
        self.assertAlmostEqual(shipped.K.deficit.unsated(0.45, 1.5), 0.3, places=12)
