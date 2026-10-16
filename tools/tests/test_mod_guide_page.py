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
- each system section's block order, the scenario anchors Task 10 fills, and the references list.

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
    "sys-strength", "sys-traits", "sys-deficiency", "sys-acute", "sys-screen",
]
BLOCK_ORDER = ["vanilla", "mod", "charts", "can", "no-longer", "science"]
SCENARIO_ANCHORS = ["s1", "s2", "s3", "s4", "s5", "s6"]
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
        self.details = []        # attrs of each <details>
        self.hrefs = []
        self.scripts = []        # (src or None, inline text)
        self.links = []
        self.tags_seen = set()
        self._script_text = None

    def _inside(self, pred):
        return any(pred(t, a) for t, a in self.stack)

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

    def test_this_page_draws_no_scenario_chart(self):
        for cid in self.page.charts:
            self.assertFalse(re.fullmatch(r"S\d[a-z]", cid), "%s is Task 10's" % cid)

    def test_charts_drawn(self):
        want = {"H1", "H2", "H3", "H4"} | {c for c, v in self.data["charts"].items()
                                           if not re.fullmatch(r"S\d[a-z]", c) and v["section"] != "At a glance"}
        self.assertEqual(set(self.page.charts), want)
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
        for sid in set(re.findall(r'"((?:H|S)[A-Z0-9]*\d?[a-z]?-[a-z][\w-]*)"', opts)):
            self.assertIn(sid, listed, sid)
        for cid in set(re.findall(r'^\s{4}"([A-Z]+\d[a-z]?)":', opts, re.M)):
            self.assertIn(cid, self.data["charts"], cid)

    def test_anchors_resolve(self):
        ids = set(self.page.ids)
        self.assertEqual(len(self.page.ids), len(ids), "duplicate ids")
        for href in self.page.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], ids, href)
                self.assertRegex(href[1:], r"^[A-Za-z0-9._~-]+$")


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
        self.assertEqual(len(sci), len(SYSTEMS))
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
