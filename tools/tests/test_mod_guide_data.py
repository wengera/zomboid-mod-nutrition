"""Tests for tools/mod_guide_data.py (Plan 14 Task 3): the series schema, the provenance validators with
the do-not-cite guard, the deterministic writer and the --check/--write CLI.

Every case but the `RealRepo` ones runs on a fixture tree in a temporary folder (its own do-not-cite list,
aliases, registers and artifacts); the kernel-commit case builds a temporary git repository and never reads
this repository's history.
"""
import io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mod_guide_data as g

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = "x900-20261015-000000"
ALIAS = "x900b-20261015-000001"

DNC = (
    "run,key,value,why,read_instead\n"
    "%(run)s,readings.day.peak,1,a restricted leaf,\n"
    "%(run)s,phases.*.watch.raw,1,a wildcard row,\n"
    "%(run)s,\"arms.{left,right}.wall\",1,braces,\n"
    "%(run)s,rows_list[0..1].HUNGER_replay,1,an index range,\n"
    "%(run)s,*,everything,a whole-run prose restriction,\n"
    "%(run)s,\"multi.a, multi.b\",1,two keys in one cell,\n"
    "%(run)s,\"multi.d, *\",1,a key beside a prose star,\n"
    "%(run)s,rows_list[2].stomach.liquid,1,a flat ring key,\n"
    "%(run)s,ack.*.lastCookMinute,1,a glob over scalar siblings,\n"
    "%(alias)s,ok.aliased,1,a row filed under the alias,\n"
    "%(run)s,steps[set_x].v,1,a named bracket,\n"
    "x999-other,ok.leaf,1,another run,\n"
) % {"run": RUN, "alias": ALIAS}

ARTIFACT = {
    "readings": {"day": {"peak": 3.5, "trough": 1.25, "peak_at": 4}, "night": {"peak": 2.0}},
    "phases": {"A": {"watch": {"raw": 9, "mean": 4}}, "B": {"watch": {"raw": 8, "mean": 5}}},
    "arms": {"left": {"wall": 1, "kcal": 10}, "right": {"wall": 2, "kcal": 20}, "mid": {"wall": 3}},
    "multi": {"a": 1, "b": 2, "c": 3, "d": 4},
    "ok": {"leaf": 7, "aliased": 8},
    "ack": {"perk": "Cooking", "c1": {"lastCookMinute": 5, "x": 1}},
    "steps": [{"v": 1, "w": 2}, {"v": 3, "w": 4}],
    "rows_list": [
        {"age": 0, "HUNGER": 0.1, "HUNGER_replay": 0.1, "stomach.liquid": 250.0, "stomach": {"liquid": -1}},
        {"age": 1, "HUNGER": 0.2, "HUNGER_replay": 0.2, "stomach.liquid": 240.5, "stomach": {"liquid": -1}},
        {"age": 2, "HUNGER": 0.3, "HUNGER_replay": 0.3, "stomach.liquid": 230.25},
    ],
    "nested": {"stomach": {"fill": 0.5}},
    "items": [{"pz_id": "Base.Apple", "kcal": 95}, {"pz_id": "Base.Bread", "kcal": 250},
              {"pz_id": "Base.Toast", "kcal": 250}],
}

SCRIPT = """module Other
{
    item Apple
    {
        Calories = 1,
    }
}
module Base
{
    /* a comment item Apple { Calories = 1, } */
    item Apple
    {
        DisplayName = Apple,
        Calories = 95,
        HungerChange = -15,
        Carbohydrates = 25.13,
    }
    item Bread
    {
        Calories = 250,
        component FluidContainer
        {
            Capacity = 2,
        }
    }
    item Water
    {
        component FluidContainer
        {
            Capacity = 3,
        }
        Capacity = 1,
    }
}
"""

CHARTS = {"C1": {"section": "s", "title": "t", "x": "x", "y": "y",
                 "series": ["a-live", "b-kernel", "c-model", "d-study", "e-vdata", "f-mdata"]}}


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mgd-")
        self.install = tempfile.mkdtemp(prefix="mgd-install-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(shutil.rmtree, self.install, True)
        r = self.root
        _write(os.path.join(r, "docs/reference/do-not-cite.csv"), DNC)
        _write(os.path.join(r, "docs/reference/run-aliases.csv"), "alias,run,file,key\n%s,%s,,\n" % (ALIAS, RUN))
        _write(os.path.join(r, "docs/reference/claims.tsv"), "id\tclaim\n#0470\tx\n#0474\ty\n")
        _write(os.path.join(r, "docs/reference/science.tsv"), "id\ttopic\nS0224\tvitC\n")
        _write(os.path.join(r, "testing/artifacts", RUN, "ring.json"), json.dumps(ARTIFACT))
        _write(os.path.join(r, "testing/artifacts", "x434-proof", "a.json"), "{}")
        _write(os.path.join(r, "tools/replay_live.py"), "# the kernel script\n")
        _write(os.path.join(r, "data/food.json"), json.dumps({"items": ARTIFACT["items"]}))
        _write(os.path.join(r, "notdata/food.json"), "{}")
        self.script = os.path.join(self.install, "media", "scripts", "items_food.txt")
        _write(self.script, SCRIPT)

    def series(self, **over):
        s = {"id": "a-live", "chart": "C1", "label": "Hunger", "units": {"x": "h", "y": "hunger"},
             "badge": "live", "points": [[0, 0.1], [1, 0.2]],
             "provenance": {"kind": "artifact", "run": RUN, "file": "ring.json", "path": "rows_list[*].HUNGER"}}
        s.update(over)
        return s

    def validate(self, s, commit="abc1234"):
        return g.validate_series(s, self.root, self.install, commit, CHARTS)

    def read(self, path, run=RUN):
        return g.read_artifact(run, "ring.json", path, self.root)


class Schema(Fixture):
    def test_valid_series_passes(self):
        self.validate(self.series())

    def test_missing_badge_rejected(self):
        s = self.series()
        del s["badge"]
        with self.assertRaisesRegex(g.ProvenanceError, "missing badge"):
            self.validate(s)

    def test_missing_provenance_rejected(self):
        s = self.series()
        del s["provenance"]
        with self.assertRaisesRegex(g.ProvenanceError, "missing provenance"):
            self.validate(s)

    def test_unknown_badge_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "badge 'measured' is not one of"):
            self.validate(self.series(badge="measured"))

    def test_unknown_kind_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "provenance kind"):
            self.validate(self.series(provenance={"kind": "hearsay"}))

    def test_provenance_missing_field_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "missing path"):
            self.validate(self.series(provenance={"kind": "artifact", "run": RUN, "file": "ring.json"}))

    def test_unknown_series_key_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "unknown key"):
            self.validate(self.series(colour="red"))

    def test_badge_kind_pairing(self):
        with self.assertRaisesRegex(g.ProvenanceError, "does not go with"):
            self.validate(self.series(badge="kernel"))
        self.validate(self.series(badge="vanilla-live"))

    def test_provenance_empty_path_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "must be a non-empty str"):
            self.validate(self.series(provenance={"kind": "artifact", "run": RUN, "file": "ring.json", "path": ""}))

    def test_units_extra_key_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "unknown key z"):
            self.validate(self.series(units={"x": "h", "y": "y", "z": "q"}))

    def test_vanilla_model_needs_formulas_and_claims(self):
        for p in ({"kind": "vanilla-model", "formulas": [], "claims": ["#0470"]},
                  {"kind": "vanilla-model", "formulas": ["VM1"], "claims": []}):
            with self.assertRaisesRegex(g.ProvenanceError, "names its formulas"):
                self.validate(self.series(id="c-model", badge="vanilla-model", provenance=p))

    def test_kernel_inputs_must_be_plain_json(self):
        prov = {"kind": "kernel", "script": "tools/replay_live.py", "inputs": {"a": float("nan")}, "proof_run": "x434-proof"}
        with self.assertRaisesRegex(g.ProvenanceError, "not plain JSON"):
            self.validate(self.series(id="b-kernel", badge="kernel", provenance=prov))

    def test_points_shape(self):
        for bad in ([], [[1]], [[1, "y"]], [[1, float("nan")]], [[None, 1]], [[1, True]], [(1, 2)]):
            with self.assertRaises(g.ProvenanceError, msg=repr(bad)):
                self.validate(self.series(points=bad))
        self.validate(self.series(points=[["Apple", 95], ["Bread", 250.5]]))

    def test_chart_membership(self):
        with self.assertRaisesRegex(g.ProvenanceError, "not in the charts table"):
            self.validate(self.series(chart="C9"))
        with self.assertRaisesRegex(g.ProvenanceError, "does not list it"):
            self.validate(self.series(id="z-other"))

    def test_kernel_provenance(self):
        prov = {"kind": "kernel", "script": "tools/replay_live.py", "inputs": {"minutes": 360}, "proof_run": "x434-proof"}
        s = self.validate(self.series(id="b-kernel", badge="kernel", provenance=dict(prov)))
        self.assertEqual(s["provenance"]["commit"], "abc1234")                     # filled
        with self.assertRaisesRegex(g.ProvenanceError, "not mod/'s last commit"):
            self.validate(self.series(id="b-kernel", badge="kernel", provenance=dict(prov, commit="0000000")))
        with self.assertRaisesRegex(g.ProvenanceError, "proof run"):
            self.validate(self.series(id="b-kernel", badge="kernel", provenance=dict(prov, proof_run="x0-none")))
        with self.assertRaisesRegex(g.ProvenanceError, "script"):
            self.validate(self.series(id="b-kernel", badge="kernel", provenance=dict(prov, script="tools/none.py")))

    def test_vanilla_model_provenance(self):
        ok = {"kind": "vanilla-model", "formulas": ["VM1"], "claims": ["#0470"]}
        self.validate(self.series(id="c-model", badge="vanilla-model", provenance=ok))
        with self.assertRaisesRegex(g.ProvenanceError, "unknown formulas"):
            self.validate(self.series(id="c-model", badge="vanilla-model", provenance=dict(ok, formulas=["VM99"])))
        with self.assertRaisesRegex(g.ProvenanceError, "not in the register"):
            self.validate(self.series(id="c-model", badge="vanilla-model", provenance=dict(ok, claims=["#9999"])))

    def test_study_provenance(self):
        self.validate(self.series(id="d-study", badge="study", provenance={"kind": "study", "science": "S0224"}))
        with self.assertRaisesRegex(g.ProvenanceError, "science register"):
            self.validate(self.series(id="d-study", badge="study", provenance={"kind": "study", "science": "S9999"}))

    def test_artifact_provenance_refuses_do_not_cite(self):
        with self.assertRaises(g.DoNotCite):
            self.validate(self.series(provenance={"kind": "artifact", "run": RUN, "file": "ring.json", "path": "readings.day"}))


class Dataset(Fixture):
    def vdata(self, **prov):
        p = {"kind": "dataset", "file": "<install>/media/scripts/items_food.txt", "key": "Base.Apple.Calories", "build": "42.21"}
        p.update(prov)
        return self.series(id="e-vdata", badge="vanilla-model", provenance=p)

    def test_install_file_is_vanilla(self):
        self.validate(self.vdata())
        with self.assertRaisesRegex(g.ProvenanceError, "takes the badge vanilla-model"):
            self.validate(dict(self.vdata(), badge="kernel"))

    def test_install_file_records_the_build(self):
        p = self.vdata()["provenance"]
        del p["build"]
        with self.assertRaisesRegex(g.ProvenanceError, "records its build 42.21"):
            self.validate(self.series(id="e-vdata", badge="vanilla-model", provenance=p))
        with self.assertRaisesRegex(g.ProvenanceError, "records its build"):
            self.validate(self.vdata(build="42.20"))

    def test_repo_file_is_the_mods(self):
        p = {"kind": "dataset", "file": "data/food.json", "key": "items[pz_id=Base.Apple].kcal"}
        self.validate(self.series(id="f-mdata", badge="kernel", provenance=p))
        with self.assertRaisesRegex(g.ProvenanceError, "takes the badge kernel"):
            self.validate(self.series(id="f-mdata", badge="vanilla-model", provenance=p))
        with self.assertRaisesRegex(g.ProvenanceError, "no install build"):
            self.validate(self.series(id="f-mdata", badge="kernel", provenance=dict(p, build="42.21")))

    def test_local_absolute_path_refused(self):
        for f in (self.script, os.path.join(self.root, "data", "food.json"), "/abs/x.json"):
            with self.assertRaisesRegex(g.ProvenanceError, "local absolute path"):
                g.dataset_side(f, self.root, self.install)
        with self.assertRaisesRegex(g.ProvenanceError, "local absolute path"):
            self.validate(self.vdata(file=self.script))
        with self.assertRaisesRegex(g.ProvenanceError, "leaves its tree"):
            g.dataset_side("<install>/../x.txt", self.root, self.install)

    def test_install_path_joins_the_install(self):
        self.assertEqual(g.dataset_path("<install>/media/scripts/items_food.txt", self.root, self.install),
                         os.path.join(self.install, "media", "scripts", "items_food.txt"))

    def test_repo_file_outside_data_and_mod_refused(self):
        with self.assertRaisesRegex(g.ProvenanceError, "under data/ or mod/"):
            g.dataset_side("notdata/food.json", self.root, self.install)
        with self.assertRaisesRegex(g.ProvenanceError, "leaves its tree"):
            g.dataset_side("data/../notdata/food.json", self.root, self.install)

    def test_script_reader(self):
        rd = lambda k: g.read_dataset("<install>/media/scripts/items_food.txt", k, self.root, self.install)
        self.assertEqual(rd("Base.Apple.Calories"), 95)
        self.assertEqual(rd("Base.Apple.Carbohydrates"), 25.13)
        self.assertEqual(rd("Base.Apple.HungerChange"), -15)
        self.assertEqual(rd("Base.Bread.Calories"), 250)
        with self.assertRaises(g.ProvenanceError):
            rd("Base.Bread.HungerChange")
        with self.assertRaises(g.ProvenanceError):
            rd("Base.Cake.Calories")
        self.assertEqual(rd("Other.Apple.Calories"), 1)                     # scoped to its module
        with self.assertRaisesRegex(g.ProvenanceError, "no item Bread in module Other"):
            rd("Other.Bread.Calories")
        with self.assertRaisesRegex(g.ProvenanceError, "no field Capacity"):
            rd("Base.Bread.Capacity")                                       # a nested block's field is not the item's
        self.assertEqual(rd("Base.Water.Capacity"), 1)
        with self.assertRaisesRegex(g.ProvenanceError, "no module Nope"):
            rd("Nope.Apple.Calories")

    def test_json_selector(self):
        self.assertEqual(g.read_dataset("data/food.json", "items[pz_id = Base.Bread].kcal", self.root, self.install), 250)
        with self.assertRaisesRegex(g.ProvenanceError, "matches 0"):
            g.read_dataset("data/food.json", "items[pz_id=Base.Cake].kcal", self.root, self.install)


class DoNotCiteGuard(Fixture):
    def test_exact_key_refused(self):
        with self.assertRaisesRegex(g.DoNotCite, "equals"):
            self.read("readings.day.peak")

    def test_parent_refused(self):
        with self.assertRaisesRegex(g.DoNotCite, "contains"):
            self.read("readings.day")
        with self.assertRaisesRegex(g.DoNotCite, "contains"):
            self.read("readings")

    def test_child_refused(self):
        with self.assertRaisesRegex(g.DoNotCite, "is inside"):
            g.check_citable(RUN, "readings.day.peak.raw", self.root)

    def test_root_read_refused(self):
        with self.assertRaises(g.DoNotCite):
            self.read("")

    def test_flat_ring_key_listed(self):
        with self.assertRaises(g.DoNotCite):
            self.read("rows_list[2].stomach.liquid")
        with self.assertRaises(g.DoNotCite):
            self.read('rows_list[2]["stomach.liquid"]')
        with self.assertRaises(g.DoNotCite):
            self.read("rows_list[*].stomach.liquid")
        self.assertEqual(self.read("rows_list[0].stomach.liquid"), 250.0)

    def test_scalar_leaf_beside_a_glob_key(self):
        self.assertEqual(self.read("ack.perk"), "Cooking")                  # a scalar holds no listed child
        self.assertEqual(self.read("ack.c1.x"), 1)
        with self.assertRaises(g.DoNotCite):
            self.read("ack.c1.lastCookMinute")
        with self.assertRaises(g.DoNotCite):
            self.read("ack.c1")
        with self.assertRaises(g.DoNotCite):
            self.read("ack")
        with self.assertRaises(g.DoNotCite):
            g.check_citable(RUN, "ack.perk", self.root)                      # without a document: conservative

    def test_siblings_allowed(self):
        self.assertEqual(self.read("readings.day.peak_at"), 4)              # the glob is anchored
        self.assertEqual(self.read("readings.day.trough"), 1.25)
        self.assertEqual(self.read("readings.night.peak"), 2.0)
        self.assertEqual(self.read("phases.A.watch.mean"), 4)

    def test_wildcard_row(self):
        with self.assertRaises(g.DoNotCite):
            self.read("phases.B.watch.raw")
        with self.assertRaises(g.DoNotCite):
            self.read("phases.A.watch")
        with self.assertRaises(g.DoNotCite):
            self.read("phases")

    def test_brace_alternatives(self):
        with self.assertRaises(g.DoNotCite):
            self.read("arms.left.wall")
        with self.assertRaises(g.DoNotCite):
            self.read("arms.right.wall")
        self.assertEqual(self.read("arms.mid.wall"), 3)
        self.assertEqual(self.read("arms.left.kcal"), 10)

    def test_index_range_and_star_reads(self):
        with self.assertRaises(g.DoNotCite):
            self.read("rows_list[1].HUNGER_replay")
        self.assertEqual(self.read("rows_list[2].HUNGER_replay"), 0.3)
        with self.assertRaises(g.DoNotCite):
            self.read("rows_list[*].HUNGER_replay")            # a whole-column read touches rows 0 and 1
        with self.assertRaises(g.DoNotCite):
            self.read("rows_list[0]")                            # a row is a parent
        self.assertEqual(self.read("rows_list[*].HUNGER"), [0.1, 0.2, 0.3])

    def test_comma_cell_is_several_keys(self):
        with self.assertRaises(g.DoNotCite):
            self.read("multi.a")
        with self.assertRaises(g.DoNotCite):
            self.read("multi.b")
        self.assertEqual(self.read("multi.c"), 3)
        with self.assertRaises(g.DoNotCite):
            self.read("multi.d")

    def test_star_row_is_prose_not_a_key(self):
        self.assertEqual(self.read("nested.stomach.fill"), 0.5)

    def test_other_runs_rows_do_not_apply(self):
        self.assertEqual(self.read("ok.leaf"), 7)

    def test_named_bracket_pattern(self):
        with self.assertRaises(g.DoNotCite):
            self.read("steps[*].v")                                         # any row may be the named one
        self.assertEqual(self.read("steps[0].v"), 1)                         # an index is not the name
        self.assertEqual(self.read("steps[*].w"), [2, 4])

    def test_a_row_filed_under_the_alias(self):
        with self.assertRaises(g.DoNotCite):
            self.read("ok.aliased", run=ALIAS)
        self.assertEqual(self.read("ok.aliased"), 8)

    def test_alias_reads_the_real_run_and_its_rows(self):
        self.assertEqual(self.read("readings.day.trough", run=ALIAS), 1.25)
        with self.assertRaises(g.DoNotCite):
            self.read("readings.day.peak", run=ALIAS)

    def test_missing_file_and_key(self):
        with self.assertRaisesRegex(g.ProvenanceError, "has no file"):
            g.read_artifact(RUN, "none.json", "a", self.root)
        with self.assertRaisesRegex(g.ProvenanceError, "no key"):
            self.read("readings.dusk")


class RingKeys(Fixture):
    def test_longest_literal_key_first(self):
        self.assertEqual(self.read("rows_list[0].stomach.liquid"), 250.0)
        self.assertEqual(self.read("rows_list[1][\"stomach.liquid\"]"), 240.5)
        self.assertEqual(self.read("rows_list[1].stomach.liquid"), 240.5)

    def test_nested_keys_still_split(self):
        self.assertEqual(self.read("nested.stomach.fill"), 0.5)

    def test_selector(self):
        self.assertEqual(self.read("items[pz_id=Base.Bread].kcal"), 250)
        self.assertEqual(self.read('items[pz_id="Base.Bread"].kcal'), 250)   # quotes stripped
        with self.assertRaisesRegex(g.ProvenanceError, "matches 2"):
            self.read("items[kcal=250].pz_id")

    def test_negative_index(self):
        self.assertEqual(self.read("rows_list[-1].HUNGER"), 0.3)


def _defs(n=3, reverse=False):
    """Series definitions with shuffled key order and unrounded floats."""
    out = []
    for i in range(n):
        def fn(i=i):
            prov = {"path": "rows_list[*].HUNGER", "file": "ring.json", "run": RUN, "kind": "artifact"}
            return {"provenance": prov, "points": [[i, 0.1 + 0.2], [i + 1, 1 / 3]], "badge": "live",
                    "units": {"y": "hunger", "x": "h"}, "label": "L%d" % i, "chart": "C1", "id": "s%d" % i}
        out.append(fn)
    return out[::-1] if reverse else out


CHARTS3 = {"C1": {"section": "s", "title": "t", "x": "x", "y": "y", "series": ["s0", "s1", "s2"]}}


class Determinism(Fixture):
    def dump(self, defs):
        return g.dumps(g.build(defs, self.root, CHARTS3, [], self.install))

    def test_stable_bytes_whatever_the_order(self):
        a = self.dump(_defs())
        b = self.dump(_defs(reverse=True))
        self.assertEqual(a, b)
        data = json.loads(a)
        self.assertEqual([s["id"] for s in data["series"]], ["s0", "s1", "s2"])

    def test_format(self):
        text = self.dump(_defs())
        self.assertTrue(text.endswith("}\n"))
        self.assertTrue(text.startswith('{\n "charts": {'))                 # indent 1, keys sorted
        self.assertIn("0.30000000000000004", text)                         # repr-exact, never rounded
        self.assertIn("0.3333333333333333", text)
        self.assertEqual(text, json.dumps(json.loads(text), sort_keys=True, indent=1, ensure_ascii=False) + "\n")

    def test_floats_round_trip(self):
        data = json.loads(self.dump(_defs()))
        self.assertEqual(data["series"][0]["points"][0][1], 0.1 + 0.2)

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(g.ProvenanceError, "duplicate"):
            g.build(_defs(1) + _defs(1), self.root, CHARTS3, [], self.install)

    def test_validation_must_be_a_list(self):
        with self.assertRaisesRegex(g.ProvenanceError, "validation is a list"):
            g.build(_defs(), self.root, CHARTS3, {}, self.install)

    def test_writer_keeps_utf8_and_refuses_nan(self):
        text = g.dumps({"a": "0–6"})
        self.assertIn("0–6", text)
        with self.assertRaises(ValueError):
            g.dumps({"a": float("nan")})

    def test_def_may_return_a_list(self):
        defs = [lambda: [f() for f in _defs()]]
        self.assertEqual(self.dump(defs), self.dump(_defs()))


class Cli(Fixture):
    def run_cli(self, args, defs):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = g.main(args, root=self.root, series_defs=defs, charts=CHARTS3, validation=[])
        return code, out.getvalue() + err.getvalue()

    def test_write_then_check(self):
        self.assertEqual(self.run_cli(["--write"], _defs())[0], 0)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "docs", "mod-guide", "data.json")))
        code, msg = self.run_cli(["--check"], _defs())
        self.assertEqual(code, 0, msg)

    def test_check_fails_when_one_point_differs(self):
        self.run_cli(["--write"], _defs())
        changed = _defs()
        orig = changed[1]

        def moved():
            s = orig()
            s["points"][1][1] += 1e-12
            return s
        changed[1] = moved
        code, msg = self.run_cli(["--check"], changed)
        self.assertEqual(code, 1)
        self.assertIn("out of date", msg)

    def test_check_fails_when_missing(self):
        self.assertEqual(self.run_cli(["--check"], _defs())[0], 1)

    def test_check_fails_on_a_hand_edit(self):
        self.run_cli(["--write"], _defs())
        p = os.path.join(self.root, "docs", "mod-guide", "data.json")
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace("0.30000000000000004", "0.3", 1))
        self.assertEqual(self.run_cli(["--check"], _defs())[0], 1)

    def test_check_accepts_a_crlf_checkout(self):
        self.run_cli(["--write"], _defs())
        p = os.path.join(self.root, "docs", "mod-guide", "data.json")
        with open(p, encoding="utf-8", newline="") as fh:
            text = fh.read()
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace("\n", "\r\n"))
        self.assertEqual(self.run_cli(["--check"], _defs())[0], 0)

    def test_invalid_series_exits_2(self):
        bad = [lambda: {"id": "s0"}]
        self.assertEqual(self.run_cli(["--write"], bad)[0], 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "docs", "mod-guide", "data.json")))


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                           "-c", "commit.gpgsign=false"] + list(args), capture_output=True, text=True, check=True).stdout.strip()


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
class KernelCommit(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="mgd-git-")
        self.addCleanup(shutil.rmtree, self.repo, True)
        _git(self.repo, "init", "-q")

    def commit(self, rel, text):
        _write(os.path.join(self.repo, rel), text)
        _git(self.repo, "add", "--", rel)
        _git(self.repo, "commit", "-q", "-m", "c", "--", rel)
        return _git(self.repo, "log", "-1", "--format=%H")[:10]

    def test_moves_with_a_mod_commit_only(self):
        with self.assertRaises(g.ProvenanceError):
            g.kernel_commit(self.repo)                                     # no commit yet
        first = self.commit("mod/a.lua", "x = 1\n")
        self.assertEqual(g.kernel_commit(self.repo), first)
        self.assertEqual(len(first), 10)
        self.commit("docs/page.md", "text\n")
        self.assertEqual(g.kernel_commit(self.repo), first)               # a docs commit leaves it
        second = self.commit("mod/a.lua", "x = 2\n")
        self.assertNotEqual(second, first)
        self.assertEqual(g.kernel_commit(self.repo), second)              # a mod commit moves it


class RealRepo(unittest.TestCase):
    def test_stub_builds_empty_series_and_the_charts(self):
        data = g.build()
        self.assertEqual(data["series"], [])
        self.assertEqual(data["validation"], [])
        self.assertEqual(len(data["charts"]), 39)
        self.assertEqual(sum(len(c["series"]) for c in data["charts"].values()), 147)
        for cid, c in data["charts"].items():
            self.assertEqual(set(c), {"section", "title", "x", "y", "series"}, cid)

    def test_real_ring_keys_read(self):
        run = "x361-20261012-200722"
        if not os.path.isdir(os.path.join(REPO, "testing", "artifacts", run)):
            self.skipTest("x361 not present")
        rows = g.read_artifact(run, "minute-ring-admin-1.json", "rows_list[*][\"satiety.M\"]")
        self.assertGreater(len(rows), 100)

    def test_real_do_not_cite_parent_refused(self):
        dnc = g.load_dnc()
        run, rows = next((r, v) for r, v in sorted(dnc.items()) if any("." in k for k, _ in v))
        key = next(k for k, _ in rows if "." in k and "*" not in k and "[" not in k and "{" not in k and "<" not in k)
        with self.assertRaises(g.DoNotCite):
            g.check_citable(run, key)
        with self.assertRaises(g.DoNotCite):
            g.check_citable(run, key.split(".")[0])


if __name__ == "__main__":
    unittest.main()
