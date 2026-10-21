"""Tests for the player guide's page (Plan 14 Task 9): docs/mod-guide/index.html and docs/mod-guide/charts.js
against docs/mod-guide/data.json.

The page is checked headless, by parsing its HTML:
- every chart id and every series id it references exists in data.json, and every data-fill's pick resolves;
- no digit run in the prose outside a fill target or a <details> box (ALLOWED_DIGITS lists the exceptions);
- no plain-language-forbidden term outside a <details> box (spec section 4.2), in the page's own text and in the
  chart titles, axis strings and series labels data.json renders on it; a series' note and provenance show only in
  its source popover, whose run ids, claim ids and S-ids are its job, and are exempt;
- the artifact page contract: no document wrapper, the title first, the three :root token blocks, Chart.js from
  cdnjs at a pinned version before the inline scripts, charts.js and data.json loaded relatively;
- each system section's block order, the scenario anchors, and the references list;
- the six scenarios (Task 10): each draws its own charts S<n><x> from data.json, sets vanilla beside the mod in a
  fixed block order, links into the systems sections, and keeps the digit and plain-language rules; every facet in
  charts.js shows only its chart's own series, the facets together covering every series the chart lists.

The pick grammar is defined in charts.js's header comment. `evaluate_pick` below mirrors charts.js's evalPick; the
grammar cases assert both the selector set charts.js accepts and the values the mirror computes.
"""
import json
import os
import re
import sys
import unittest
from html.parser import HTMLParser

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUIDE = os.path.join(REPO, "docs", "mod-guide")
INDEX = os.path.join(GUIDE, "index.html")
CHARTS_JS = os.path.join(GUIDE, "charts.js")
DATA = os.path.join(GUIDE, "data.json")
sys.path.insert(0, os.path.join(REPO, "tools"))
from mod_guide_series import PENDING_LIVE  # noqa: E402

# Prose text that may carry a digit outside a fill target or a <details> box: a heading that names a level
# ("Strength 10") or a list's own numbering. Each entry is an exact text run.
ALLOWED_DIGITS = ()

FORBIDDEN = [
    (r"\bMET\b", "MET"),
    (r"(?i)\bFMI\b", "FMI"),
    (r"(?i)\bkernel", "kernel"),
    (r"(?i)fatDep", "fatDep"),
    (r"(?i)\bpartition", "partition"),
    (r"(?i)\boracle", "oracle"),
    (r"\bS\d{3,4}\b", "an S-id"),
    (r"#\d{3,4}\b", "a #-id"),
]

SYSTEMS = [
    "sys-nutrients", "sys-eating", "sys-hunger", "sys-thirst", "sys-monotony", "sys-body", "sys-exercise",
    "sys-strength", "sys-traits", "sys-deficiency", "sys-acute", "sys-screen", "sys-offline",
]
BLOCK_ORDER = ["vanilla", "mod", "charts", "can", "no-longer", "science"]
SCENARIO_ANCHORS = ["s1", "s2", "s3", "s4", "s5", "s6"]
SCENE_ORDER = ["vanilla", "mod", "charts", "links", "science"]
SCENARIO_CHART = re.compile(r"S(\d)[a-z]")
BACK_MATTER = ["options", "compatibility", "limitations", "references"]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


# ---------------------------------------------------------------------------------------------- the pick grammar

class PickError(ValueError):
    pass


NUM = r"-?[0-9.]+(?:e-?[0-9]+)?"


def parse_pick(pick):
    parts = [p.strip() for p in str(pick).split("|")]
    sel, ops = parts[0], parts[1:]
    m = None
    if re.fullmatch(r"(first|last|min|max)\.(x|y)", sel):
        m = re.fullmatch(r"(first|last|min|max)\.(x|y)", sel)
        out = {"kind": m.group(1), "axis": m.group(2)}
    elif re.fullmatch(r"(argmax|argmin)\.x", sel):
        out = {"kind": sel.split(".")[0]}
    elif re.fullmatch(r"delta\.(x|y)", sel):
        out = {"kind": "delta", "axis": sel[-1]}
    elif sel == "n":
        out = {"kind": "n"}
    elif re.fullmatch(r"y@x=(.+)", sel):
        out = {"kind": "yat", "x": sel[4:]}
    elif re.fullmatch(r"x@y(>=|<=|>|<)(%s)" % NUM, sel):
        m = re.fullmatch(r"x@y(>=|<=|>|<)(%s)" % NUM, sel)
        out = {"kind": "xwhere", "cmp": m.group(1), "v": float(m.group(2))}
    else:
        raise PickError("bad pick selector: %s" % sel)
    parsed_ops = []
    for op in ops:
        if op in ("abs", "neg"):
            parsed_ops.append((op, None))
        elif re.fullmatch(r"(add|sub|mul|div):(%s)" % NUM, op):
            k, v = op.split(":")
            parsed_ops.append((k, float(v)))
        elif re.fullmatch(r"r[0-3]", op):
            parsed_ops.append(("r", int(op[1])))
        elif re.fullmatch(r"pct[0-3]", op):
            parsed_ops.append(("pct", int(op[3])))
        else:
            raise PickError("bad pick op: %s" % op)
    return out, parsed_ops


def _select(points, sel):
    if not points:
        raise PickError("no points")
    k = sel["kind"]
    if k in ("first", "last"):
        p = points[0] if k == "first" else points[-1]
        return p[0] if sel["axis"] == "x" else p[1]
    if k in ("min", "max"):
        ax = 0 if sel["axis"] == "x" else 1
        vals = [p[ax] for p in points]
        return min(vals) if k == "min" else max(vals)
    if k in ("argmax", "argmin"):
        best = 0
        for i in range(1, len(points)):
            if (points[i][1] > points[best][1]) if k == "argmax" else (points[i][1] < points[best][1]):
                best = i
        return points[best][0]
    if k == "delta":
        ax = 0 if sel["axis"] == "x" else 1
        return points[-1][ax] - points[0][ax]
    if k == "n":
        return len(points)
    if k == "yat":
        if isinstance(points[0][0], str):
            for p in points:
                if str(p[0]) == sel["x"]:
                    return p[1]
            raise PickError("no category %s" % sel["x"])
        x = float(sel["x"])
        for i, p in enumerate(points):
            if p[0] == x:
                return p[1]
            if i > 0 and points[i - 1][0] < x < p[0]:
                x0, y0 = points[i - 1]
                x1, y1 = p
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        raise PickError("x %s outside the series" % sel["x"])
    if k == "xwhere":
        for p in points:
            y, c, v = p[1], sel["cmp"], sel["v"]
            if (c == ">=" and y >= v) or (c == "<=" and y <= v) or (c == ">" and y > v) or (c == "<" and y < v):
                return p[0]
        raise PickError("no point meets y%s%s" % (sel["cmp"], sel["v"]))
    raise PickError("bad selector")


def evaluate_pick(points, pick):
    """(value, text): the value after the arithmetic ops at full precision, the text as charts.js displays it."""
    sel, ops = parse_pick(pick)
    v = _select(points, sel)
    digits, pct = None, False
    for op, k in ops:
        if not isinstance(v, (int, float)):
            raise PickError("arithmetic on a category")
        if op == "abs":
            v = abs(v)
        elif op == "neg":
            v = -v
        elif op == "add":
            v += k
        elif op == "sub":
            v -= k
        elif op == "mul":
            v *= k
        elif op == "div":
            v /= k
        elif op == "r":
            digits = k
        elif op == "pct":
            pct, digits = True, k
    if not isinstance(v, (int, float)):
        return v, str(v)
    shown = v * 100 if pct else v
    if digits is None:
        digits = 0 if abs(shown) >= 100 else 1 if abs(shown) >= 10 else 2
    return v, "{:,.{}f}".format(shown, digits)


# ---------------------------------------------------------------------------------------------- the page parser

class PageParser(HTMLParser):
    """Walks the page once, recording prose text with its context, the ids, the fills, the charts and the
    system sections' block order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, attrs dict)
        self.prose = []          # (text, in_details, in_fill, in_heading)
        self.ids = []
        self.fills = []          # (series, pick)
        self.charts = []
        self.blocks = {}         # system id -> [block names in order]
        self.scene_blocks = {}   # scenario id -> [data-scene names in order]
        self.chart_owner = {}    # chart id -> the scenario or system section it sits in
        self.scene_hrefs = {}    # scenario id -> [hrefs]
        self.scene_prose = {}    # scenario id -> [(text, in_details, in_fill)]
        self.details = []        # attrs of each <details>
        self.hrefs = []
        self.scripts = []        # (src or None, inline text)
        self.links = []
        self.tags_seen = set()
        self._script_text = None

    def _inside(self, pred):
        return any(pred(t, a) for t, a in self.stack)

    def _section(self, id_re):
        for t, sa in reversed(self.stack):
            if t == "section" and re.fullmatch(id_re, sa.get("id", "")):
                return sa["id"]
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags_seen.add(tag)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "link":
            self.links.append(a)
        if tag == "details":
            self.details.append(a)
        if "data-fill" in a:
            self.fills.append((a["data-fill"], a.get("data-pick", "last.y")))
        if "data-chart" in a:
            self.charts.append(a["data-chart"])
            self.chart_owner[a["data-chart"]] = self._section(r"s\d|sys-[\w-]+") or self._section(r"[\w-]+")
        scene = self._section(r"s\d")
        if scene and "data-scene" in a:
            self.scene_blocks.setdefault(scene, []).append(a["data-scene"])
        if scene and tag == "a" and "href" in a:
            self.scene_hrefs.setdefault(scene, []).append(a["href"])
        if "data-block" in a:
            sysid = None
            for t, sa in reversed(self.stack):
                if t == "section" and sa.get("id", "").startswith("sys-"):
                    sysid = sa["id"]
                    break
            self.blocks.setdefault(sysid, []).append(a["data-block"])
        if tag == "script":
            self._script_text = []
            self.scripts.append([a.get("src"), None])
        if tag not in VOID:
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag == "script" and self._script_text is not None:
            self.scripts[-1][1] = "".join(self._script_text)
            self._script_text = None
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self._script_text is not None:
            self._script_text.append(data)
            return
        if self._inside(lambda t, a: t in ("style", "script", "title")):
            return
        if not data.strip():
            return
        in_details = self._inside(lambda t, a: t == "details")
        in_fill = self._inside(lambda t, a: "data-fill" in a)
        in_heading = self._inside(lambda t, a: t in ("h1", "h2", "h3", "h4", "li"))
        self.prose.append((data, in_details, in_fill, in_heading))
        scene = self._section(r"s\d")
        if scene:
            self.scene_prose.setdefault(scene, []).append((data, in_details, in_fill))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _visible_prose(page):
    """Text outside <details> and outside fill targets."""
    return [t for t, in_details, in_fill, _ in page.prose if not in_details and not in_fill]


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = _read(INDEX)
        cls.js = _read(CHARTS_JS)
        with open(DATA, encoding="utf-8") as f:
            cls.data = json.load(f)
        cls.series = {s["id"]: s for s in cls.data["series"]}
        cls.page = PageParser()
        cls.page.feed(cls.html)
        cls.page.close()


# ---------------------------------------------------------------------------------------------- the cases

class PickGrammar(unittest.TestCase):
    NUMERIC = [[0.0, 0.5], [1.0, 0.25], [2.0, 0.75], [4.0, 1.0]]
    CATEGORY = [["Apple", 95.0], ["Bread", 532.0], ["day 2", 1.1445]]

    def test_selectors(self):
        cases = [
            ("first.y", 0.5), ("last.y", 1.0), ("first.x", 0.0), ("last.x", 4.0),
            ("min.y", 0.25), ("max.y", 1.0), ("max.x", 4.0), ("argmin.x", 1.0), ("argmax.x", 4.0),
            ("delta.y", 0.5), ("delta.x", 4.0), ("n", 4),
            ("y@x=1", 0.25), ("y@x=3", 0.875), ("x@y>=0.75", 2.0), ("x@y<0.3", 1.0), ("x@y>0.75", 4.0),
        ]
        for pick, want in cases:
            with self.subTest(pick=pick):
                self.assertAlmostEqual(evaluate_pick(self.NUMERIC, pick)[0], want)

    def test_category_lookup(self):
        self.assertEqual(evaluate_pick(self.CATEGORY, "y@x=Bread|r0"), (532.0, "532"))
        self.assertEqual(evaluate_pick(self.CATEGORY, "y@x=day 2|sub:1|pct0")[1], "14")
        self.assertEqual(evaluate_pick(self.CATEGORY, "argmax.x")[0], "Bread")

    def test_ops_and_display(self):
        self.assertEqual(evaluate_pick(self.NUMERIC, "delta.y|neg|abs|r3")[1], "0.500")
        self.assertEqual(evaluate_pick(self.NUMERIC, "last.y|mul:1500|r0")[1], "1,500")
        self.assertEqual(evaluate_pick(self.NUMERIC, "min.y|pct1")[1], "25.0")
        self.assertEqual(evaluate_pick(self.NUMERIC, "last.x|div:8|add:0.5")[1], "1.00")
        self.assertEqual(evaluate_pick([[0, 123.4]], "first.y")[1], "123")
        self.assertEqual(evaluate_pick([[0, 12.34]], "first.y")[1], "12.3")

    def test_bad_picks_fail(self):
        for pick in ("last", "y@x=9", "x@y>=2", "first.y|r7", "first.y|round", "y@x=Pear", "mid.y"):
            with self.subTest(pick=pick):
                with self.assertRaises(PickError):
                    evaluate_pick(self.NUMERIC if "Pear" not in pick else self.CATEGORY, pick)
        with self.assertRaises(PickError):
            evaluate_pick(self.CATEGORY, "first.x|abs")

    def test_charts_js_carries_the_same_grammar(self):
        js = _read(CHARTS_JS)
        for frag in ("(first|last|min|max)\\.(x|y)", "(argmax|argmin)\\.x", "delta\\.(x|y)", "y@x=", "x@y(>=|<=|>|<)",
                     "(add|sub|mul|div):", "r([0-3])", "pct([0-3])", '"abs"', '"neg"'):
            self.assertIn(frag, js, frag)
        for name in ("function renderChart(el, chartId, data)", "function fill(el, seriesId, pick, data)",
                     "function evalPick(points, pick)"):
            self.assertIn(name, js)


class References(_Base):
    def test_every_chart_exists(self):
        self.assertTrue(self.page.charts)
        for cid in self.page.charts:
            self.assertIn(cid, self.data["charts"], cid)

    def test_charts_drawn(self):
        self.assertEqual(set(self.page.charts), set(self.data["charts"]), "every chart in data.json is drawn")
        self.assertEqual(len(self.page.charts), len(set(self.page.charts)))

    def test_every_fill_resolves(self):
        self.assertTrue(self.page.fills)
        for sid, pick in self.page.fills:
            with self.subTest(fill=sid, pick=pick):
                self.assertIn(sid, self.series, "%s is not a built series" % sid)
                value, text = evaluate_pick(self.series[sid]["points"], pick)
                self.assertTrue(text)

    def test_missing_series_are_only_pending_live(self):
        for cid in set(self.page.charts):
            missing = [i for i in self.data["charts"][cid]["series"] if i not in self.series]
            self.assertTrue(set(missing) <= set(PENDING_LIVE), (cid, missing))

    def test_charts_js_ids_exist(self):
        listed = {i for c in self.data["charts"].values() for i in c["series"]}
        opts = self.js[self.js.index("var CHART_OPTS"):self.js.index("var SIDE_NAMES")]
        pending_views = _pending_views(self.js)
        self.assertLessEqual(pending_views, {"S6a-m-tolerance"}, "a pending view is a Task 8 carry, named here")
        for sid in set(re.findall(r'"((?:H|S)[A-Z0-9]*\d?[a-z]?-[a-z][\w-]*)"', opts)):
            self.assertIn(sid, listed | pending_views, sid)
        for cid in set(re.findall(r'^\s{4}"([A-Z]+\d[a-z]?)":', opts, re.M)):
            self.assertIn(cid, self.data["charts"], cid)

    def test_anchors_resolve(self):
        ids = set(self.page.ids)
        self.assertEqual(len(self.page.ids), len(ids), "duplicate ids")
        for href in self.page.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], ids, href)
                self.assertRegex(href[1:], r"^[A-Za-z0-9._~-]+$")


def _opts_block(js, cid):
    """The text of one chart's entry in charts.js's CHART_OPTS, or None."""
    opts = js[js.index("var CHART_OPTS"):js.index("var SIDE_NAMES")]
    m = re.search(r'\n    "%s": \{(.*?)(?=\n    "[A-Z]+\d?[a-z]?\d?": |\n  \};)' % re.escape(cid), opts, re.S)
    return m.group(1) if m else None


def _pending_views(js):
    """Series ids charts.js draws as a view the data file does not hold yet (CHART_OPTS pendingViews)."""
    opts = js[js.index("var CHART_OPTS"):js.index("var SIDE_NAMES")]
    return {i for b in re.findall(r"pendingViews: \{([^}]*)\}", opts) for i in re.findall(r'"([^"]+)":', b)}


def _views(block):
    """(label, unit, yMin or None) for each facet of a CHART_OPTS block; one chart-level view when it has none."""
    facets = re.findall(r'\{ label: "([^"]+)", series: \[[^\]]*\], unit: "([^"]+)"([^\n]*)', block or "")
    if facets:
        out = []
        for label, unit, rest in facets:
            m = re.search(r"yMin: (-?[0-9.]+)", rest)
            if not m:
                m = re.search(r"^      yMin: (-?[0-9.]+)", block, re.M)
            out.append((label, unit, float(m.group(1)) if m else None))
        return out
    m = re.search(r"yMin: (-?[0-9.]+)", block or "")
    return [(None, None, float(m.group(1)) if m else None)]


class Scenarios(_Base):
    def scenario_charts(self):
        return sorted(c for c in self.data["charts"] if SCENARIO_CHART.fullmatch(c))

    def test_every_scenario_chart_appears_in_its_scenario(self):
        charts = self.scenario_charts()
        self.assertEqual(len(charts), 19)
        for cid in charts:
            with self.subTest(chart=cid):
                self.assertIn(cid, self.page.charts)
                self.assertEqual(self.page.chart_owner[cid], "s" + SCENARIO_CHART.fullmatch(cid).group(1))

    def test_scenario_sections_and_block_order(self):
        self.assertEqual(sorted(self.page.scene_blocks), SCENARIO_ANCHORS)
        for sid in SCENARIO_ANCHORS:
            with self.subTest(scenario=sid):
                self.assertEqual(self.page.scene_blocks[sid], SCENE_ORDER)
                self.assertIn(sid + "-h", self.page.ids)

    def test_scenarios_link_into_the_systems(self):
        ids = set(self.page.ids)
        for sid in SCENARIO_ANCHORS:
            with self.subTest(scenario=sid):
                hrefs = self.page.scene_hrefs.get(sid, [])
                self.assertGreaterEqual(len([h for h in hrefs if h.startswith("#sys-")]), 2)
                for h in hrefs:
                    self.assertTrue(h.startswith("#"), h)
                    self.assertIn(h[1:], ids, h)

    def test_scenario_index_links_every_scenario(self):
        for sid in SCENARIO_ANCHORS:
            self.assertIn("#" + sid, self.page.hrefs)

    def test_scenario_text_keeps_the_digit_and_plain_language_rules(self):
        for sid in SCENARIO_ANCHORS:
            with self.subTest(scenario=sid):
                prose = self.page.scene_prose[sid]
                visible = [t for t, in_details, in_fill in prose if not in_details and not in_fill]
                self.assertTrue(visible)
                self.assertEqual([t for t in visible if re.search(r"\d", t)], [])
                text = "\n".join(visible)
                for pat, name in FORBIDDEN:
                    self.assertIsNone(re.search(pat, text), "%s in %s" % (name, sid))
                self.assertEqual([t for t, d, f in prose if f], [], "fill targets are written empty")

    def test_scenario_fills_draw_on_built_series(self):
        html = self.html[self.html.index('id="s1"'):self.html.index('id="systems"')]
        fills = re.findall(r'data-fill="([^"]+)"', html)
        self.assertGreaterEqual(len(fills), 60)
        for sid in fills:
            self.assertIn(sid, self.series, sid)
            self.assertNotIn(sid, PENDING_LIVE, "a pending series cannot fill a number: %s" % sid)

    def test_facets_cover_their_chart(self):
        seen = 0
        for cid, chart in self.data["charts"].items():
            block = _opts_block(self.js, cid)
            if not block or "facets" not in block:
                continue
            seen += 1
            with self.subTest(chart=cid):
                # Plan 17 Task 5: a zoom facet (zoom: true) repeats series another facet shows on a narrower x
                facets = re.findall(r"series: \[([^\]]*)\]([^\n]*)", block)
                ids = [re.findall(r'"([^"]+)"', f) for f, rest in facets if "zoom: true" not in rest]
                zooms = [re.findall(r'"([^"]+)"', f) for f, rest in facets if "zoom: true" in rest]
                extra = [i for i in _pending_views(self.js) if i not in chart["series"] and i in block]
                self.assertEqual(sorted(i for f in ids for i in f), sorted(chart["series"] + extra),
                                 "the facets show each of the chart's series exactly once")
                for z in zooms:
                    self.assertTrue(z and set(z) <= {i for f in ids for i in f}, "a zoom repeats shown series: %s" % z)
                for f in ids:
                    if set(f) <= set(extra):
                        continue
                    self.assertTrue([i for i in f if i in self.series], "a facet with no built series: %s" % f)
        self.assertGreaterEqual(seen, 10)

    def test_facet_reader_finds_every_chart(self):
        opts = self.js[self.js.index("var CHART_OPTS"):self.js.index("var SIDE_NAMES")]
        keys = re.findall(r'^\s{4}"([A-Z]+\d?[a-z]?\d?)":', opts, re.M)
        self.assertGreaterEqual(len(keys), 30)
        for cid in keys:
            self.assertIsNotNone(_opts_block(self.js, cid), cid)

    def test_endpoints_name_series_that_end_at_a_death(self):
        seen = 0
        for cid, chart in self.data["charts"].items():
            m = re.search(r"endpoints: \{([^}]*)\}", _opts_block(self.js, cid) or "")
            if not m:
                continue
            for sid, label in re.findall(r'"([^"]+)": "([^"]+)"', m.group(1)):
                seen += 1
                with self.subTest(series=sid):
                    self.assertIn(sid, chart["series"])
                    self.assertIn(sid, self.series)
                    self.assertTrue(label.startswith("Death: "), label)
                    note = self.series[sid].get("note", "") + " " + self.series[sid].get("label", "")
                    self.assertRegex(note, r"(?i)death|lethal|health is gone")
                    # the cause the label names is the series' own (SD1's note names the drain, its chart the scurvy)
                    self.assertIn(label[7:].lower(), (note + " " + chart["title"]).lower())
                    lethal = re.search(r"(?i)lethal state is ([^(;.]+)", note)
                    if lethal:
                        self.assertIn(label[7:].lower(), lethal.group(1).lower(), "the note's own lethal state")
                    self.assertRegex(note, r"(?i)lines? ends?|ends the line|death \d|death at", "the line ends at the death")
        self.assertGreaterEqual(seen, 5)

    def test_plan17_s2d_health_tab_draws_vanilla_beside_the_mod(self):
        """Plan 17 Task 5: the fast chart opens on Health, the mod's line with vanilla's model and live health on the
        same axes; a first-week zoom repeats them; Pace and Combining are their own tabs."""
        block = _opts_block(self.js, "S2d")
        labels = re.findall(r'\{ label: "([^"]+)", series: \[([^\]]*)\]([^\n]*)', block)
        self.assertEqual(labels[0][0], "Health")
        tabs = {lab: (re.findall(r'"([^"]+)"', ids), rest) for lab, ids, rest in labels}
        for sid in ("S2d-m-drain", "S2d-v-model-health", "S2d-v-live-health"):
            self.assertIn(sid, tabs["Health"][0])
        zoom = [lab for lab, (ids, rest) in tabs.items() if "zoom: true" in rest]
        self.assertEqual(len(zoom), 1)
        self.assertLessEqual(set(tabs["Health"][0]), set(tabs[zoom[0]][0]))
        self.assertEqual(tabs["Pace"][0][:3], ["S2d-m-pace-vanilla", "S2d-m-pace-short", "S2d-m-pace-real"])
        self.assertEqual(tabs["Combining"][0], ["S2d-m-comb-worst", "S2d-m-comb-mult", "S2d-m-comb-add"])
        self.assertNotIn("Vanilla health", tabs)
        # every line ends at a death: each new line is named in the endpoints
        ends = re.search(r"endpoints: \{([^}]*)\}", block).group(1)
        for sid in ("S2d-m-pace-vanilla", "S2d-m-pace-short", "S2d-m-pace-real", "S2d-m-comb-worst",
                    "S2d-m-comb-mult", "S2d-m-comb-add"):
            self.assertIn('"%s"' % sid, ends)

    def test_level_health_and_unit_views_start_at_zero(self):
        """A view of a Strength level, health or a 0-1 stat draws from zero (S3a's grade view, 1 to 4, is named)."""
        unit_re = re.compile(r"(?i)strength level|health|\(0-1\)|0\u20131|\bhunger\b|\bthirst\b|moodle level")
        checked = 0
        for cid, chart in self.data["charts"].items():
            if not SCENARIO_CHART.fullmatch(cid):
                continue
            for label, unit, ymin in _views(_opts_block(self.js, cid)):
                text = unit or chart["y"]
                if not unit_re.search(text) or (cid, label) == ("S3a", "Grade"):
                    continue
                checked += 1
                with self.subTest(chart=cid, view=label):
                    self.assertEqual(ymin, 0.0, "%s %s: %s" % (cid, label, text))
        self.assertGreaterEqual(checked, 14)

    def test_a_facet_drawing_only_its_own_runs_shows_every_point(self):
        """Task 11 M1 and M14: a facet whose series are all of one x span (S6a's Tolerance in days, S6c's Sleep
        debt to day 4.13) sets x bounds that hold every point; S2d's views clip by design and name it in xTitle."""
        cases = [("S6a", "Tolerance"), ("S6c", "Sleep debt")]
        for cid, label in cases:
            with self.subTest(chart=cid, view=label):
                block = _opts_block(self.js, cid)
                m = re.search(r'\{ label: "%s", series: \[([^\]]*)\]([^\n]*)' % re.escape(label), block)
                self.assertIsNotNone(m)
                rest = m.group(2)

                def bound(key):
                    b = (re.search(r"\b%s: (-?[0-9.]+)" % key, rest)
                         or re.search(r"^      [^\n{]*\b%s: (-?[0-9.]+)" % key, block, re.M))
                    return float(b.group(1)) if b else None
                lo, hi = bound("xMin"), bound("xMax")
                for sid in re.findall(r'"([^"]+)"', m.group(1)):
                    xs = [p[0] for p in self.series[sid]["points"]]
                    if lo is not None:
                        self.assertGreaterEqual(min(xs), lo, sid)
                    self.assertIsNotNone(hi)
                    self.assertLessEqual(max(xs), hi, sid)
                    self.assertLessEqual(hi, 1.25 * max(xs), "%s: the axis runs well past its points" % sid)
        self.assertNotIn("S6a-m-tolerance", _pending_views(self.js), "a built series is no pending view")
        self.assertIn('xTitle: "game days"', _opts_block(self.js, "S6a"))

    STALE = [
        # Task 11 I1: the mod's own severe-dehydration drain kills; only the game's drains are capped away
        r"never reach their top moodle and never kill", r"so thirst never kills",
        # I2 and I3: the hangover's start has a live row (#3891); caffeine and blood alcohol of x447 have none
        r"promises neither", r"hangover start, caffeine and blood alcohol",
        # I4, I5, I6: vanilla Weak starts at 0; rust's step comes near day 49; exertion does not speed vanilla hunger
        r"keep their vanilla costs and start levels", r"rust takes a year", r"faster when you exert yourself",
        # M1, M2, M9: the tolerance view is drawn; the health view's dots died; the live beer decay is measured
        r"blunts each cup is not drawn yet", r"The dots are an older live vanilla run",
        r"Read from the game's code, at the default day length", r"which fades over hours",
        # M8, M10, M11, M12 and the FFMI fragment
        r"the week is a game choice", r"Push-ups alone", r"a food with no calories no longer fills you",
        r"Vitamin C, water, caffeine, alcohol and sleep are never sped up", r"; FFMI, the lean mass",
        # Plan 15 Task 13: the caps lift at the mod's own crises, the Energy and Hydration moodles are gone, starvation
        # and the deficiencies drain to floors with no off switch, Overfull's top level refuses the menu's eat
        r"Energy moodle (?:shows|reaches)", r"Managed(?:-mode)? cap", r"beriberi kills", r"never blocks an eat",
        r"NR\.DeficienciesCanKill", r"when the server lets deficiencies kill", r"Hydration \(Slightly dry",
        r"hunger itself never kills", r"never reach(?:es)? the top (?:Hungry|Thirsty)", r"Hunger never reaches zero",
        # Plan 16 Task 11: no rhythm with sleep off (x467 saw breakfast wear off first), the tooltip hide measured live
        # (x462), the server refusal (x466), the fast's wet beriberi death (#4022), the offline freeze (x463a), the
        # drink sip by sip, the superseded hunger, satiety and starvation rows
        r"dinner wore off soonest", r"dinner wears off sooner", r"has not been seen (?:live|in a live game)",
        r"can still land", r"so a heavier (?:body lives|survivor lasts) longer", r"starvation kills on day",
        r"Time offline is not simulated", r"lands whole", r"with water, about two months",
        r"#3905\b", r"#3910\b", r"#3948\b", r"#3952\b", r"#3953\b",
        # Plan 17 Task 5: the floors are gone; health follows each state's remaining fraction
        r"(?i)first floor", r"(?i)floor of (?:50|half)", r"25 a game day", r"(?i)50 in about", r"(?i)lowest floor",
        r"(?i)down to a floor", r"(?i)drains? (?:health )?to (?:a|its|the) floor", r"(?i)the floor (?:then )?sinks",
        r"(?i)floor stands in its place", r"(?i)rests at the floor", r"(?i)held three days", r"41\.14",
        # Plan 17 Task 5b (revision R1): every lethal state falls on a straight line on its clock; the curve, its
        # opening at vanilla's rate, its flattening and dehydration's final stage are retired, and x481 (the curve's
        # live run) proves nothing at HEAD
        r"(?i)logarithm", r"(?i)flatten", r"(?i)\btaper", r"(?i)\bon (?:a|the) (?:logarithmic )?curve",
        r"(?i)same curve", r"(?i)curve over", r"(?i)open(?:s|ing)(?: the damage)? at vanilla's",
        r"(?i)opening slope", r"(?i)open(?:s|ing)? (?:more )?gently", r"(?i)more gently",
        r"(?i)as fast as vanilla's(?: drain)?,? (?:at first|then)", r"(?i)first falls exactly as fast",
        r"(?i)then slows?\b", r"(?i)more slowly as (?:your body|you dry)", r"(?i)final stage",
        r"(?i)x481 at Realistic", r"(?i)fifteen per cent deficit", r"(?i)opened on (?:the curve|its own line)",
        # Plan 17 Task 5c (revision R2): each target is a ceiling that rises only as the body recovers, so ending a
        # state stops its damage but returns no health at once, and Vanilla pace is vanilla's own line only while a
        # state runs unbroken (the close review's I3)
        r"Vanilla is vanilla's own line", r"plays starving and thirst like the unmodded game", r"While any drain runs",
        r"which ends the scurvy damage, and its", r"the damage stops once its store climbs out of Clinical\.",
        r"(?i)drain's last minute", r"(?i)returns? to full", r"(?i)back to full health",
        r"(?i)resets? (?:it|its ceiling|the ceiling|its line|the line) to full",
        # Plan 18 Task 5: x495 lifted a hand-set ceiling with a snack and health healed up to it, so a recovering
        # ceiling is no longer wholly unread live; Severity now also scales the deadly dangers' symptoms
        r"No live run has read a recovering ceiling yet", r"No live game has shown a cap recovering yet",
        r"or an excess brings\. The excess option",
    ]

    def test_task_11_stale_sentences_stay_gone(self):
        for pat in self.STALE:
            with self.subTest(pattern=pat):
                self.assertIsNone(re.search(pat, self.html), pat)

    def test_the_hangover_is_promised_on_both_sides_with_its_row(self):
        """Task 11 I2 and I3: S6 and the Systems section both promise the hangover, and its science cites #3891."""
        self.assertGreaterEqual(len(re.findall(r"leaves a hangover once the alcohol has (?:gone|cleared)", self.html)), 3)
        self.assertGreaterEqual(self.html.count("(#3891)"), 2)
        self.assertEqual(self.series["S6b-m-hangover"]["provenance"]["proof_run"], "x447-regrade-20261015")

    PINNED = [
        ("S2d-m-drain", "last.x|r0", "77"),     # Plan 16 Task 5: beriberi at day 77 (starvation at 62 under the ceiling)
        ("S4a-v-model-x1", "last.y|r0", "9"),
        ("H3-v-model-x15", "x@y>=10|r0", "292"),
        ("S5a-v-model-level", "y@x=Weak + Overweight|r0", "0"),
        ("S5a-m-live-level", "y@x=Weak + Overweight|r0", "1"),
        ("S4b-m-level", "x@y>=10|r1", None),
        ("S4a-m-deficit", "last.x|r0", "301"),  # Plan 16 Task 11: the deficit year's starvation death (BMI 12)
        ("SH3-m-live", "y@x=breakfast|r1", "3.9"),  # Plan 16 Task 11: x467, breakfast wears off first (#3990)
        ("S2d-m-drain", "x@y<=10|r1", "62.7"),  # Plan 17 Task 5b: under a tenth from day 62.7 (the row laid in)
        ("S2d-m-pace-real", "x@y<=10|r1", "82.0"),  # Realistic starvation alone: its last 7.72 days
        ("S2d-m-pace-short", "x@y<=10|r1", "14.0"),  # Shortened: its last 1.40 days
        ("S2d-m-dry", "x@y<=10|mul:24|r0", "125"),  # without water: from hour 125 to the death at 136
    ]

    def test_pinned_fills(self):
        """Eight fills the claims rest on: on the page with this pick, and reading what the notes say."""
        fills = set(self.page.fills)
        for sid, pick, want in self.PINNED:
            with self.subTest(fill=sid, pick=pick):
                self.assertIn((sid, pick), fills)
                value, text = evaluate_pick(self.series[sid]["points"], pick)
                if want is not None:
                    self.assertEqual(text, want)
        # S4b: the year the body first reaches the top level, inside the chart and before its end
        years, _ = evaluate_pick(self.series["S4b-m-level"]["points"], "x@y>=10")
        self.assertTrue(0 < years < evaluate_pick(self.series["S4b-m-level"]["points"], "last.x")[0])
        # S6b: the hangover starts after the blood alcohol is back to zero
        self.assertIn(("S6b-m-hangover", "x@y>=1|r1"), fills)
        bac = self.series["S6b-m-bac"]["points"]
        peak = max(range(len(bac)), key=lambda i: bac[i][1])
        cleared = next(p[0] for p in bac[peak:] if p[1] <= 0)
        start, _ = evaluate_pick(self.series["S6b-m-hangover"]["points"], "x@y>=1")
        self.assertGreaterEqual(start, cleared)

    def test_every_cited_claim_is_live_in_the_register(self):
        """Plan 16 Task 11: every #-id the page and data.json's series cite is a claims-register row not superseded."""
        status = {}
        with open(os.path.join(REPO, "docs", "reference", "claims.tsv"), encoding="utf-8") as fh:
            head = fh.readline().rstrip("\n").split("\t")
            for line in fh:
                cells = dict(zip(head, line.rstrip("\n").split("\t")))
                status[cells["id"]] = cells["status"]
        cited = set(re.findall(r"#\d{4}\b", self.html))
        self.assertGreaterEqual(len(cited), 100)
        # review M7: the data file's notes, which the source popovers show, and its provenance cells
        noted = set()
        for s in self.data["series"]:
            noted |= set(re.findall(r"#\d{4}\b", s.get("note", "") + " " + json.dumps(s["provenance"])))
        self.assertGreaterEqual(len(noted), 40)
        for cid in sorted(cited | noted):
            with self.subTest(claim=cid):
                self.assertIn(cid, status)
                self.assertIn(status[cid], ("settled", "open"), cid)

    def test_plan16_the_new_mechanics_are_on_the_page(self):
        """Plan 16 Task 11: the offline freeze and the backup, the body clock and the two sleep setups, the server
        refusal and the corrected limitations, each with its register row in a science box."""
        self.assertIn("sys-offline", self.page.ids)
        for frag in ("Nothing about your survivor changes while you are logged off", "a backup copy on your character",
                     "Records are kept for good", "your body also keeps a clock of its own",
                     "the server refuses an eat that gets past the menus", "A drink with no food value, such as water",
                     "A drink arrives sip by sip", "in the server's language", "QualityCooking",
                     "In Overlay mode the game's own fullness decides", "caught up in hour-long steps"):
            self.assertIn(frag, self.html, frag)
        for cid in ("#3955", "#3958", "#3961", "#3965", "#3967", "#3968", "#3972", "#3973", "#3977", "#4022",
                    "#3979", "#3982", "#3983", "#3985", "#3987", "#3988", "#3989", "#3990"):
            self.assertIn(cid, self.html, cid)
        for frag in ("not established physiology (#3996)", "NR.RecordKeepDays"):
            self.assertEqual(self.html.count(frag), 1 if frag.startswith("not") else 0, frag)

    def test_plan17_the_options_and_limitations_name_the_new_health_model(self):
        """Plan 17 Task 5: both drain options on the options list with their defaults, the four corners, and the new
        limitations."""
        opts = self.html[self.html.index('id="options"'):self.html.index('id="compatibility"')]
        for frag in ("NR.DeathPace", "NR.HealthCombine", "Realistic, the default", "Multiply, the default",
                     "Vanilla", "Shortened", "Worst only", "Add",
                     # Task 5b (revision R1): each pace a straight line, a switch's gap closed at vanilla's rate
                     "Every pace takes health down in a straight line",
                     # the close fix wave (M2): at least vanilla's rate, the cap summing every active rate
                     "falls at least at vanilla's rate until it reaches it"):
            self.assertIn(frag, opts, frag)
        lim = self.html[self.html.index('id="limitations"'):self.html.index('id="references"')]
        for frag in ("wakes a sleeper", "Add, health can run out before", "first day's close",
                     "every line spends its last tenth there", "the same game days at any day length",
                     "lands in one game minute"):
            self.assertIn(frag, lim, frag)

    def test_plan17_r2_the_ceiling_recovers_with_the_body(self):
        """Plan 17 Task 5c (revision R2): the options, the limitations and the science name the recovering ceiling, and
        the S3c note's recovery runs about as long as Clinical did (its clock counts back down 1:1)."""
        opts = self.html[self.html.index('id="options"'):self.html.index('id="compatibility"')]
        for frag in ("rises back only as your body recovers", "picks its line up where it left off",
                     "plays unbroken starving and thirst like the unmodded game"):
            self.assertIn(frag, opts, frag)
        lim = self.html[self.html.index('id="limitations"'):self.html.index('id="references"')]
        for frag in ("takes about as long as the decline did", "until the day's weight update books your true weight",
                     "the panel says Recovering from it", "No live game has shown a cap recovering with the body yet"):
            self.assertIn(frag, lim, frag)
        for frag in ("The target is a ceiling", "The ceiling rises only as the body recovers",
                     "resumes its line where its clock stands", "recovering from starvation"):
            self.assertIn(frag, self.html, frag)
        note = self.series["S3c-m-pool"]["note"]
        m = re.search(r"Clinical \(grade 4\) on day ([0-9.]+).*out of Clinical on day ([0-9.]+).*holds to day ([0-9.]+)",
                      note)
        self.assertIsNotNone(m, note)
        on, off, end = (float(x) for x in m.groups())
        self.assertLess(on, off)
        self.assertLess(off, end)
        self.assertAlmostEqual(end - off, off - on, delta=0.05)

    def test_plan18_the_symptoms_are_on_the_page(self):
        """Plan 18 Task 5: each deadly danger's section, the fast's chart note, the screen, the options and the
        limitations name the symptoms on vanilla's own moodles, and the progress points and the fast's days are fills
        off the S2d symptom series, which read the kernel's own knots."""
        s2 = self.html[self.html.index('id="s2"'):self.html.index('id="s3"')]
        for frag in ("Exertion shows from the moment a danger starts", "A low ache shows on the Pain moodle",
                     "in your legs with scurvy or beriberi", "the unhappiness lifts at once",
                     "the exhaustion eases only as your body recovers", "With sleep on, deep exhaustion",
                     "On the Symptoms view", "Symptoms by progress view", "never lowered",
                     "the snack's pool read before the minute digests it"):
            self.assertIn(frag, s2, frag)
        for sid, pick, want in (("S2d-m-rule-exertion", "x@y>=2|r0", "31"), ("S2d-m-rule-exertion", "x@y>=3|r0", "64"),
                                ("S2d-m-rule-exertion", "x@y>=4|r0", "96"), ("S2d-m-rule-unhappy", "x@y>=1|r0", "40"),
                                ("S2d-m-rule-stress", "x@y>=1|r0", "42"), ("S2d-m-rule-stress", "x@y>=2|r0", "82")):
            with self.subTest(fill=(sid, pick)):
                self.assertIn('data-fill="%s" data-pick="%s"' % (sid, pick), s2)
                self.assertEqual(evaluate_pick(self.series[sid]["points"], pick)[1], want)
        for sid in ("S2d-m-sym-exertion", "S2d-m-sym-pain", "S2d-m-sym-stress", "S2d-m-sym-unhappy"):
            self.assertIn('data-fill="%s"' % sid, s2, sid)
        sections = {"sys-hunger": "makes your stomach ache", "sys-thirst": "gives you a headache",
                    "sys-deficiency": "make your legs ache", "sys-screen": "Exertion, Pain, Stress and Unhappy moodles"}
        for sec, frag in sections.items():
            body = self.html[self.html.index('id="%s"' % sec):]
            body = body[:body.index("</section>")]
            self.assertIn(frag, body, sec)
        opts = self.html[self.html.index('id="options"'):self.html.index('id="compatibility"')]
        self.assertIn("In Overlay starving and thirst bring none of the mod's exhaustion", opts)
        self.assertIn("though not how fast your health falls", opts)
        lim = self.html[self.html.index('id="limitations"'):self.html.index('id="references"')]
        for frag in ("a stand-in until research gives it a shape", "A painkiller stops a danger's ache",
                     "about a minute of real time to show", "On the longest day lengths"):
            self.assertIn(frag, lim, frag)

    def test_plan17_the_end_mark_skips_a_line_ending_off_the_view(self):
        """Plan 17 Task 5 fix 1 (F1): a zoom facet draws no end mark for a line that ends past its x range."""
        self.assertRegex(self.js, r"pt\.x > chart\.chartArea\.right")

    def test_plan17_no_health_floor_word_remains(self):
        """Plan 17 Task 5: the only floors left on the page are the mood floor and Strength's own floor."""
        for m in re.finditer(r"(?i)\bfloors?\b", self.html):
            ctx = self.html[max(0, m.start() - 12):m.start()]
            self.assertRegex(ctx, r"(?:mood |own )$", ctx + m.group(0))

    def test_plan17_the_gaunt_body_s_weeks_hold(self):
        """The page says the Gaunt body starves in about six weeks: its replay's death (VALIDATION j_s2d_gaunt) is
        within half a week of it."""
        v = next(r for r in self.data["validation"] if r.get("kind") == "viability" and r.get("job") == "j_s2d_gaunt")
        self.assertEqual(v["death_name"], "starvation")
        self.assertLess(abs(v["death_age"] / 24.0 / 7.0 - 6.0), 0.5)
        self.assertIn("in about six weeks", self.html)

    def test_the_scenario_guard_catches_a_typed_number(self):
        p = PageParser()
        p.feed('<section id="s2"><p>Vanilla dies at 63 hours <span data-fill="S2d-m-mass"></span></p>'
               '<details><p>VM10 at 34.84 h</p></details></section>')
        visible = [t for t, d, f in p.scene_prose["s2"] if not d and not f]
        self.assertEqual([t for t in visible if re.search(r"\d", t)], ["Vanilla dies at 63 hours "])


class PlainLanguage(_Base):
    def test_no_digit_in_prose(self):
        bad = [t.strip() for t in _visible_prose(self.page) if re.search(r"\d", t) and t.strip() not in ALLOWED_DIGITS]
        self.assertEqual(bad, [])

    def test_no_forbidden_term_outside_details(self):
        text = "\n".join(_visible_prose(self.page))
        for pat, name in FORBIDDEN:
            with self.subTest(term=name):
                self.assertIsNone(re.search(pat, text), "%s outside a science box: %r" % (
                    name, (re.search(pat, text) or [None])[0]))

    def test_rendered_chart_text_is_plain(self):
        for cid in set(self.page.charts):
            chart = self.data["charts"][cid]
            texts = [chart["title"], chart["x"], chart["y"]]
            texts += [self.series[i]["label"] for i in chart["series"] if i in self.series]
            for text in texts:
                for pat, name in FORBIDDEN:
                    with self.subTest(chart=cid, term=name):
                        self.assertIsNone(re.search(pat, text), "%s in %s: %r" % (name, cid, text))

    def test_aria_labels_are_plain(self):
        for pat, name in FORBIDDEN:
            for m in re.finditer(r'aria-label="([^"]*)"', self.html):
                self.assertIsNone(re.search(pat, m.group(1)), name)

    def test_the_guard_catches_a_typed_number(self):
        p = PageParser()
        p.feed('<p>Hunger falls to 0.25 <span data-fill="H1-v-model">x</span></p><details><p>40 days</p></details>')
        self.assertEqual([t for t in _visible_prose(p) if re.search(r"\d", t)], ["Hunger falls to 0.25 "])
        p = PageParser()
        p.feed("<p>the kernel at #3123</p><details><p>the kernel at #3123</p></details>")
        text = "\n".join(_visible_prose(p))
        self.assertIsNotNone(re.search(r"(?i)\bkernel", text))
        self.assertEqual(text.count("#3123"), 1)


class PageContract(_Base):
    def test_no_document_wrapper(self):
        self.assertNotRegex(self.html, r"(?i)<!doctype")
        for tag in ("html", "head", "body"):
            self.assertNotIn(tag, self.page.tags_seen, tag)
            self.assertNotRegex(self.html, r"(?i)<%s[\s>]" % tag)

    def test_title_first(self):
        self.assertTrue(self.html.startswith("<title>Nutrition Revamp Guide</title>"))
        self.assertLess(self.html.index("<title>"), self.html.index("<style>"))

    def test_token_blocks(self):
        css = self.html[self.html.index("<style>"):self.html.index("</style>")]
        bare = re.search(r"\n:root \{(.*?)\n\}", css, re.S)
        media = re.search(r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\}\s*\}', css, re.S)
        explicit = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', css, re.S)
        self.assertTrue(bare and media and explicit)
        def colours(block):
            return {m.group(1) for m in re.finditer(r"(--[\w-]+):\s*#", block)}
        light = colours(bare.group(1))
        self.assertGreaterEqual(len(light), 6)
        self.assertEqual(colours(media.group(1)), light)
        self.assertEqual(colours(explicit.group(1)), light)
        for block in (media.group(1), explicit.group(1)):
            self.assertIn("color-scheme: dark", block)
        def values(block):
            return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", block))
        self.assertEqual(values(media.group(1)), values(explicit.group(1)))
        self.assertEqual(set(values(media.group(1))), set(values(bare.group(1))) - {
            k for k in values(bare.group(1)) if k.startswith("--font") or k in ("--measure", "--wide")})
        self.assertRegex(css, r"body \{[^}]*background: var\(--paper\)")
        # no literal colour outside the token blocks
        rest = css.replace(bare.group(0), "").replace(media.group(0), "").replace(explicit.group(0), "")
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,6}\b|rgba?\(|hsla?\(", rest), [])

    def test_popover_is_anchored_to_the_chip_row(self):
        css = self.html[self.html.index("<style>"):self.html.index("</style>")]
        wrap = re.search(r"\.badge-wrap \{([^}]*)\}", css).group(1)
        self.assertNotIn("position: relative", wrap)
        self.assertRegex(re.search(r"\.badges \{([^}]*)\}", css).group(1), r"position: relative")
        self.assertRegex(re.search(r"\.popover \{([^}]*)\}", css).group(1), r"width: min\(30rem, 100%\)")

    def test_scripts(self):
        srcs = [s for s, _ in self.page.scripts]
        chartjs = [s for s in srcs if s and "Chart.js" in s]
        self.assertEqual(len(chartjs), 1)
        self.assertRegex(chartjs[0], r"^https://cdnjs\.cloudflare\.com/ajax/libs/Chart\.js/\d+\.\d+\.\d+/chart\.umd(\.min)?\.js$")
        self.assertEqual(srcs.index(chartjs[0]), 0, "Chart.js loads before every other script")
        self.assertIn("charts.js", srcs)
        self.assertLess(srcs.index(chartjs[0]), srcs.index("charts.js"))
        for s in srcs:
            if s and s.startswith("http"):
                self.assertTrue(s.startswith("https://cdnjs.cloudflare.com/"), s)
        inline = [t for s, t in self.page.scripts if s is None]
        self.assertTrue(inline and 'fetch("data.json")' in inline[-1])
        self.assertIn("python -m http.server", self.html[:600])

    def test_only_google_fonts_stylesheets(self):
        for link in self.page.links:
            if link.get("rel") == "stylesheet":
                self.assertTrue(link["href"].startswith("https://fonts.googleapis.com/"), link["href"])

    def test_no_forbidden_browser_calls(self):
        for name in (r"\balert\(", r"\bprint\(", r"<iframe", r"\bdownload=", r"window\.open\("):
            self.assertNotRegex(self.html, name)
            self.assertNotRegex(self.js, name)
        for store in re.finditer(r"localStorage", self.js):
            window = self.js[max(0, store.start() - 40):store.start()]
            self.assertIn("try", window)

    def test_sticky_toc_and_gutter(self):
        self.assertIn("top: env(safe-area-inset-top, 0px)", self.html)
        self.assertIn("padding-inline: 16px", self.html)
        self.assertIn("prefers-reduced-motion", self.html)
        self.assertIn(":focus-visible", self.html)


class Structure(_Base):
    def test_systems_and_block_order(self):
        for sysid in SYSTEMS:
            with self.subTest(system=sysid):
                self.assertIn(sysid, self.page.ids)
                self.assertEqual(self.page.blocks.get(sysid), BLOCK_ORDER)
        self.assertEqual(set(k for k in self.page.blocks), set(SYSTEMS))

    def test_science_boxes_start_closed(self):
        sci = [d for d in self.page.details if "science" in d.get("class", "") and "refs" not in d.get("class", "")]
        self.assertEqual(len(sci), len(SYSTEMS) + len(SCENARIO_ANCHORS))
        for d in self.page.details:
            self.assertNotIn("open", d, "every <details>, the references included, starts closed")

    def test_scenario_anchors_and_back_matter(self):
        for a in SCENARIO_ANCHORS + BACK_MATTER + ["glance", "scenarios"]:
            self.assertIn(a, self.page.ids, a)
            self.assertIn("#" + a, self.page.hrefs if a not in SCENARIO_ANCHORS else self.page.hrefs + ["#" + a])

    def test_operator_readme_linked(self):
        self.assertIn("https://github.com/wengera/zomboid-mod-nutrition", self.html)

    def test_references_cover_every_cited_study(self):
        refs = self.html[self.html.index('id="references"'):]
        body = self.html[:self.html.index('id="references"')]
        cited = set(re.findall(r"\bS\d{4}\b", body))
        listed = set(re.findall(r"<b>([^<]*)</b>", refs))
        listed = {s for b in listed for s in re.findall(r"S\d{4}", b)}
        self.assertTrue(cited)
        self.assertEqual(cited - listed, set())
        self.assertEqual(listed - cited, set(), "a reference the page never cites")


if __name__ == "__main__":
    unittest.main()
