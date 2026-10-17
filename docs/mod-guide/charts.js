/* Nutrition Revamp guide: the chart and number layer.
 *
 * renderChart(el, chartId, data)  draws every series data.json lists for a chart, with a vanilla/mod toggle where
 *                                 both sides exist, full-precision hover, and source badges that open a provenance
 *                                 popover. A series a chart lists that data.json does not hold yet is a pending live
 *                                 reading: it shows as a "live reading coming" chip, and a chart whose series are all
 *                                 pending shows a placeholder instead of a canvas.
 * fill(el, seriesId, pick, data)  writes one prose number from a series (the pick grammar below).
 * fillAll(root, data)             fills every [data-fill] element under root.
 *
 * The pick grammar (evalPick):
 *   pick := sel ( "|" op )*
 *   sel  := (first|last|min|max).(x|y)       the first or last point, or the smallest or largest x or y
 *         | argmax.x | argmin.x              the x where y is largest or smallest (the first such point)
 *         | delta.y | delta.x                last minus first
 *         | n                                the number of points
 *         | y@x=V                            y at x = V: linear interpolation on a numeric x inside the
 *                                            series' range, an exact match on a category x
 *         | x@y>=V | x@y<=V | x@y>V | x@y<V  the x of the first point whose y meets the test
 *   op   := abs | neg | add:K | sub:K | mul:K | div:K
 *         | rN                               round to N decimals for display (N 0-3)
 *         | pctN                             multiply by 100, round to N decimals
 *   With no rN or pctN the display rounds by size: 0 decimals from 100, 1 from 10, else 2.
 *   The element's title carries the stored value at full precision.
 *
 * Theme: every colour is read from the page's CSS tokens at render time, and charts re-render when the theme changes.
 */
(function (root) {
  "use strict";

  var BADGES = {
    "live": "Measured live",
    "kernel": "Simulated by the mod's code",
    "vanilla-live": "Vanilla, measured",
    "vanilla-model": "Vanilla, from the game's code",
    "study": "Study",
    "dataset": "The mod's food table"
  };
  var BADGE_ORDER = ["live", "vanilla-live", "kernel", "dataset", "vanilla-model", "study"];
  var STUDY_STYLES = ["rectRot", "triangle", "rect"];

  /* Per-chart display choices. Every number still comes from data.json; this table only says how to draw. */
  var CHART_OPTS = {
    "H1": { xMin: 0, xMax: 6, yMin: 0, yMax: 1 },
    "H2": {
      facets: [
        { label: "Body mass", series: ["H2-v-model", "H2-v-live", "H2-m-total"], unit: "kg", yMin: 0 },
        { label: "Fat and lean", series: ["H2-m-fat", "H2-m-lean"], unit: "kg" }
      ],
      emphasis: { "H2-m-lean": 0, "H2-m-fat": 1 }
    },
    "H3": { xMax: 365, yMin: 0, yMax: 10, stepped: ["H3-v-model-x1", "H3-v-model-x15", "H3-m-written"] },
    "H4": {
      facets: [
        { label: "Calories", series: ["H4-v-kcal", "H4-m-kcal"], unit: "kcal" },
        { label: "Carbohydrate", series: ["H4-v-carb", "H4-m-carb"], unit: "g" },
        { label: "Fat", series: ["H4-v-fat", "H4-m-fat"], unit: "g" },
        { label: "Protein", series: ["H4-v-pro", "H4-m-pro"], unit: "g" }
      ]
    },
    "SN1": {
      facets: [
        { label: "Vitamin C", series: ["SN1-m-vitC"], unit: "mg" },
        { label: "Fibre", series: ["SN1-m-fibre"], unit: "g" },
        { label: "Iron", series: ["SN1-m-iron"], unit: "mg" },
        { label: "Sodium", series: ["SN1-m-sodium"], unit: "mg" }
      ]
    },
    "SE1": { yMin: 0, xMax: 480 },
    "SH1": { yMin: 0 },
    "SH2": { yMin: 0 },
    "SH3": {
      facets: [
        { label: "Peckish", series: ["SH3-v-model", "SH3-m-kernel", "SH3-m-live"], unit: "game hours until Peckish", yMin: 0 },
        { label: "Hungry", series: ["SH3-v-model-hungry", "SH3-m-kernel-hungry", "SH3-m-live-hungry"], unit: "game hours until Hungry", yMin: 0 }
      ]
    },
    "ST1": { yMin: 0, yMax: 1 },
    "ST2": { yMin: -10, yMax: 0, yTitle: "body sodium, mmol a day" },
    "SM1": { yMin: 0 },
    "SB1": {},
    "SB2": {
      yMin: -3, yMax: 2,
      yNames: { "-3": "Emaciated", "-2": "Very Underweight / Gaunt", "-1": "Underweight / Overly Lean", "0": "none", "1": "Overweight / Overfat", "2": "Obese" }
    },
    "SX1": { yMin: 0 },
    "SX2": { yMin: 0 },
    "SS1": { yMin: 0, yMax: 10 },
    "SD1": { yMin: 0, yMax: 100, endpoints: { "SD1-m-kernel": "Death: scurvy" } },
    "SD2": {
      yMin: 0, yTitle: "days",
      xNames: {
        vitC: "vitamin C", thiamine: "thiamine", riboflavin: "riboflavin", niacin: "niacin", vitB6: "vitamin B6",
        folate: "folate", choline: "choline", vitD: "vitamin D", vitK: "vitamin K", zinc: "zinc",
        magnesium: "magnesium", iodine: "iodine", efa: "essential fats"
      }
    },
    "SC1": {
      yMin: 0,
      emphasis: { "SC1-m-live-booked": 1, "SC1-m-live-debt": 0, "SC1-m-kernel": 0 },
      xNames: { N0: "night 1", N1: "night 2", N2: "night 3", N3: "night 4" }
    },
    "SV1": { yMin: 0, yMax: 4, stepped: ["SV1-m-kernel"] },

    /* The scenarios (Task 10). A facet may carry its own x and y bounds, xTitle and yNames. */
    "S1a": { xMin: 0, xMax: 24, yMin: 0 },
    "S1b": { xMin: 0, xMax: 36, yMin: 0, yMax: 4, stepped: ["S1b-v-model", "S1b-m-kernel"] },
    "S1c": { xMin: 0, xMax: 24, yMin: 0, yMax: 1 },
    "S2a": { xMin: -12, xMax: 60, yMin: 0, yMax: 1 },
    "S2b": { yMin: 0 },
    "S2c": {},
    "S2d": {
      facets: [
        { label: "Health", series: ["S2d-m-drain"], unit: "health", yMin: 0, yMax: 100, xMin: 0, xTitle: "game days, with water" },
        { label: "Without water", series: ["S2d-m-dry"], unit: "health", yMin: 0, yMax: 100, xMin: 0, xTitle: "game days, no food and no water" },
        { label: "Body mass", series: ["S2d-m-mass"], unit: "kg", yMin: 0, xMin: 0, xTitle: "game days, with water" },
        { label: "Vanilla weight", series: ["S2d-v-model-weight", "S2d-v-live-weight"], unit: "kg", yMin: 0, xMin: 0, xMax: 4,
          xTitle: "game days (the first four)" },
        { label: "Vanilla health", series: ["S2d-v-model-health", "S2d-v-live-health"], unit: "health", yMin: 0, yMax: 100, xMin: 0, xMax: 4,
          xTitle: "game days (the first four)" }
      ],
      endpoints: { "S2d-v-model-health": "Death: hunger", "S2d-v-model-weight": "Death: hunger", "S2d-m-mass": "Death: starvation",
                   "S2d-m-drain": "Death: starvation", "S2d-m-dry": "Death: dehydration" }
    },
    "S3a": {
      facets: [
        { label: "Vitamin C store", series: ["S3a-m-pool", "S3a-study-0224", "S3a-study-0225"], unit: "store (0-1)", yMin: 0, yMax: 1, xMin: 0 },
        { label: "Grade", series: ["S3a-m-grade"], unit: "grade", yMin: 1, yMax: 4, xMin: 0,
          yNames: { "1": "Replete", "2": "Marginal", "3": "Depleted", "4": "Clinical" } }
      ],
      stepped: ["S3a-m-grade"],
      endpoints: { "S3a-m-pool": "Death: scurvy", "S3a-m-grade": "Death: scurvy" }
    },
    "S3b": { xMin: 0, yMin: 0 },
    "S3c": { xMin: 40, xMax: 80, yMin: 0, yMax: 1 },
    "S4a": { xMin: 0, xMax: 365, yMin: 0, yMax: 10, stepped: ["S4a-v-model-x1", "S4a-v-model-x07"] },
    "S4b": { xMin: 0, xMax: 10, yMin: 0, yMax: 12, stepped: ["S4b-v-model"] },
    "S4c": { xMin: 0, xMax: 910, yMin: 0, yMax: 10, stepped: ["S4c-v-model"] },
    "S5a": {
      facets: [
        { label: "Body mass", series: ["S5a-m-live-weight", "S5a-v-model-weight"], unit: "kg", yMin: 0 },
        { label: "Fat and lean", series: ["S5a-m-live-lean", "S5a-m-live-fat"], unit: "kg", yMin: 0 },
        { label: "Strength", series: ["S5a-m-live-level", "S5a-v-model-level"], unit: "Strength level", yMin: 0, yMax: 10 }
      ]
    },
    "S5b": {
      facets: [
        { label: "Strength", series: ["S5b-m-strong-level", "S5b-m-weak-level", "S5b-m-none-level", "S5b-v-model-level"], unit: "Strength level", yMin: 0, yMax: 10 },
        { label: "Body mass", series: ["S5b-m-gaunt-weight", "S5b-m-overfat-weight", "S5b-m-none-weight"], unit: "kg", yMin: 0 }
      ],
      xMin: 0, xMax: 90,
      stepped: ["S5b-m-strong-level", "S5b-m-weak-level", "S5b-m-none-level", "S5b-v-model-level"]
    },
    "S5c": { xMin: 0, xMax: 30, yMin: 0 },
    "S6a": {
      facets: [
        { label: "Caffeine", series: ["S6a-m-day1", "S6a-m-day14"], unit: "caffeine, mg", yMin: 0 },
        { label: "Tolerance", series: ["S6a-m-tolerance"], unit: "tolerance (0-1)", yMin: 0, yMax: 1, xMin: 0, xMax: 14, xTitle: "game days" },
        { label: "Fatigue relief", series: ["S6a-m-offset", "S6a-m-offset-real", "S6a-v-model"], unit: "fatigue change", yMin: -0.16, yMax: 0 }
      ],
      xMin: 0, xMax: 24
    },
    "S6b": {
      facets: [
        { label: "Drunkenness", series: ["S6b-v-model", "S6b-v-live", "S6b-m-intox", "S6b-m-intox-real"], unit: "intoxication (0-100)", yMin: 0 },
        { label: "Blood alcohol", series: ["S6b-m-bac"], unit: "blood alcohol, %", yMin: 0 },
        { label: "Hangover", series: ["S6b-m-hangover"], unit: "hangover (off or on)", yMin: 0, yMax: 1,
          yNames: { "0": "off", "1": "on" } }
      ],
      xMin: 0, xMax: 24,
      stepped: ["S6b-m-hangover"]
    },
    "S6c": {
      facets: [
        { label: "Hunger", series: ["S6c-m-kernel", "S6c-v-model", "S6c-study"], unit: "hunger factor", yMin: 0 },
        { label: "Sleep debt", series: ["S6c-m-live"], unit: "sleep debt, hours", yMin: 0, xMax: 4.5, xTitle: "game days" }
      ],
      xMin: 0, xMax: 4
    }
  };

  var SIDE_NAMES = { both: "Both", vanilla: "Vanilla", mod: "This mod" };
  var STORE_KEY = "nr-guide-side";

  /* ---------------------------------------------------------------- the pick grammar */

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  function parsePick(pick) {
    var parts = String(pick).split("|");
    var sel = parts[0].trim();
    var ops = parts.slice(1).map(function (s) { return s.trim(); });
    var m;
    var out = { sel: null, ops: [] };
    if ((m = /^(first|last|min|max)\.(x|y)$/.exec(sel))) out.sel = { kind: m[1], axis: m[2] };
    else if ((m = /^(argmax|argmin)\.x$/.exec(sel))) out.sel = { kind: m[1] };
    else if ((m = /^delta\.(x|y)$/.exec(sel))) out.sel = { kind: "delta", axis: m[1] };
    else if (sel === "n") out.sel = { kind: "n" };
    else if ((m = /^y@x=(.+)$/.exec(sel))) out.sel = { kind: "yat", x: m[1] };
    else if ((m = /^x@y(>=|<=|>|<)(-?[0-9.]+(?:e-?[0-9]+)?)$/.exec(sel))) out.sel = { kind: "xwhere", cmp: m[1], v: parseFloat(m[2]) };
    else throw new Error("bad pick selector: " + sel);
    ops.forEach(function (op) {
      var k;
      if (op === "abs" || op === "neg") out.ops.push({ op: op });
      else if ((k = /^(add|sub|mul|div):(-?[0-9.]+(?:e-?[0-9]+)?)$/.exec(op))) out.ops.push({ op: k[1], k: parseFloat(k[2]) });
      else if ((k = /^r([0-3])$/.exec(op))) out.ops.push({ op: "r", n: +k[1] });
      else if ((k = /^pct([0-3])$/.exec(op))) out.ops.push({ op: "pct", n: +k[1] });
      else throw new Error("bad pick op: " + op);
    });
    return out;
  }

  function selectValue(points, sel) {
    if (!points || !points.length) throw new Error("no points");
    var i, best;
    switch (sel.kind) {
      case "first": return points[0][sel.axis === "x" ? 0 : 1];
      case "last": return points[points.length - 1][sel.axis === "x" ? 0 : 1];
      case "min":
      case "max":
        var ax = sel.axis === "x" ? 0 : 1;
        best = points[0][ax];
        for (i = 1; i < points.length; i++) {
          if (sel.kind === "min" ? points[i][ax] < best : points[i][ax] > best) best = points[i][ax];
        }
        return best;
      case "argmax":
      case "argmin":
        best = 0;
        for (i = 1; i < points.length; i++) {
          if (sel.kind === "argmax" ? points[i][1] > points[best][1] : points[i][1] < points[best][1]) best = i;
        }
        return points[best][0];
      case "delta":
        var a = sel.axis === "x" ? 0 : 1;
        return points[points.length - 1][a] - points[0][a];
      case "n": return points.length;
      case "yat":
        if (!isNum(points[0][0])) {
          for (i = 0; i < points.length; i++) if (String(points[i][0]) === sel.x) return points[i][1];
          throw new Error("no category " + sel.x);
        }
        var x = parseFloat(sel.x);
        for (i = 0; i < points.length; i++) {
          if (points[i][0] === x) return points[i][1];
          if (i > 0 && points[i - 1][0] < x && x < points[i][0]) {
            var x0 = points[i - 1][0], x1 = points[i][0], y0 = points[i - 1][1], y1 = points[i][1];
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
          }
        }
        throw new Error("x " + sel.x + " outside the series");
      case "xwhere":
        for (i = 0; i < points.length; i++) {
          var y = points[i][1];
          var ok = sel.cmp === ">=" ? y >= sel.v : sel.cmp === "<=" ? y <= sel.v : sel.cmp === ">" ? y > sel.v : y < sel.v;
          if (ok) return points[i][0];
        }
        throw new Error("no point meets y" + sel.cmp + sel.v);
    }
    throw new Error("bad selector");
  }

  /* Returns {value, text}: value at full precision after the arithmetic ops, text rounded for display. */
  function evalPick(points, pick) {
    var p = parsePick(pick);
    var v = selectValue(points, p.sel);
    var digits = null, pct = false;
    p.ops.forEach(function (o) {
      if (!isNum(v)) throw new Error("arithmetic on a category");
      if (o.op === "abs") v = Math.abs(v);
      else if (o.op === "neg") v = -v;
      else if (o.op === "add") v = v + o.k;
      else if (o.op === "sub") v = v - o.k;
      else if (o.op === "mul") v = v * o.k;
      else if (o.op === "div") v = v / o.k;
      else if (o.op === "r") digits = o.n;
      else if (o.op === "pct") { pct = true; digits = o.n; }
    });
    if (!isNum(v)) return { value: v, text: String(v) };
    var shown = pct ? v * 100 : v;
    if (digits === null) digits = Math.abs(shown) >= 100 ? 0 : Math.abs(shown) >= 10 ? 1 : 2;
    var text = shown.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    if (text === "-0" || /^-0\.0*$/.test(text)) text = text.slice(1);
    return { value: v, text: text };
  }

  /* ---------------------------------------------------------------- data access */

  function seriesIndex(data) {
    if (!data._index) {
      var idx = {};
      data.series.forEach(function (s) { idx[s.id] = s; });
      Object.defineProperty(data, "_index", { value: idx, enumerable: false });
    }
    return data._index;
  }

  function fill(el, seriesId, pick, data) {
    var s = seriesIndex(data)[seriesId];
    if (!s) {
      el.textContent = "(live reading coming)";
      el.classList.add("fill-pending");
      return null;
    }
    var r = evalPick(s.points, pick);
    el.textContent = r.text;
    el.title = s.label + ": " + String(r.value);
    el.classList.add("filled");
    return r.value;
  }

  function fillAll(rootEl, data) {
    var bad = [];
    rootEl.querySelectorAll("[data-fill]").forEach(function (el) {
      try { fill(el, el.getAttribute("data-fill"), el.getAttribute("data-pick") || "last.y", data); }
      catch (e) { bad.push(el.getAttribute("data-fill") + " " + e.message); el.textContent = "?"; }
    });
    if (bad.length && root.console) root.console.warn("fill failed:", bad);
    return bad;
  }

  /* ---------------------------------------------------------------- styling helpers */

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
  }

  function sideOf(id) {
    if (/-study/.test(id)) return "study";
    if (/-v-/.test(id)) return "vanilla";
    return "mod";
  }

  function badgeOfPending(id) {
    return /-v-/.test(id) ? "vanilla-live" : "live";
  }

  /* The mod's food-table values (provenance kind "dataset") take their own chip; the game's own item scripts keep
     the "from the game's code" chip their series carries. */
  function badgeOf(s) {
    return s.provenance && s.provenance.kind === "dataset" && sideOf(s.id) === "mod" ? "dataset" : s.badge;
  }

  function isMeasured(s) { return s.badge === "live" || s.badge === "vanilla-live"; }

  var DASHES = [[], [7, 4], [2, 3], [10, 3, 2, 3]];

  function styleFor(s, variant) {
    var side = sideOf(s.id);
    var base = side === "vanilla" ? (variant % 2 ? "--vanilla-2" : "--vanilla")
      : side === "mod" ? (variant % 2 ? "--mod-2" : "--mod") : "--study";
    return { color: token(base), dash: DASHES[variant % DASHES.length], side: side };
  }

  function fmtFull(v) { return typeof v === "number" ? String(Number(v.toPrecision(12))) : v; }

  function niceUnit(s) { return (s.units && s.units.y) || ""; }

  /* ---------------------------------------------------------------- plugins */

  var endpointPlugin = {
    id: "nrEndpoints",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      chart.data.datasets.forEach(function (ds, i) {
        if (!ds._endLabel || !chart.isDatasetVisible(i)) return;
        var meta = chart.getDatasetMeta(i);
        var pt = meta.data[meta.data.length - 1];
        if (!pt) return;
        var x = pt.x, y = pt.y, r = 6;
        ctx.save();
        ctx.strokeStyle = ds.borderColor;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(x - r, y - r); ctx.lineTo(x + r, y + r);
        ctx.moveTo(x + r, y - r); ctx.lineTo(x - r, y + r);
        ctx.stroke();
        ctx.fillStyle = token("--ink");
        ctx.font = "600 12px " + token("--font-data");
        var w = ctx.measureText(ds._endLabel).width;
        var tx = Math.min(Math.max(x - w / 2, chart.chartArea.left), chart.chartArea.right - w);
        var ty = y - 12 < chart.chartArea.top + 12 ? y + 22 : y - 12;
        ctx.fillText(ds._endLabel, tx, ty);
        ctx.restore();
      });
    }
  };

  /* ---------------------------------------------------------------- DOM helpers */

  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") el.textContent = attrs[k];
      else if (k === "class") el.className = attrs[k];
      else el.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) el.appendChild(c); });
    return el;
  }

  function readSide() {
    try { var v = root.localStorage.getItem(STORE_KEY); return SIDE_NAMES[v] ? v : "both"; } catch (e) { return "both"; }
  }
  function writeSide(v) {
    try { root.localStorage.setItem(STORE_KEY, v); } catch (e) { /* storage is a convenience */ }
  }

  var PROV_NAMES = {
    kind: "Source", run: "Run", file: "File", path: "Path", commit: "Commit", script: "Script",
    proof_run: "Live run it matches", inputs: "Inputs", formulas: "Formulas", claims: "Register rows",
    science: "Science row", key: "Key", build: "Game build"
  };

  function provenanceBlock(s) {
    var dl = h("dl", { class: "prov-list" });
    var p = s.provenance || {};
    Object.keys(p).forEach(function (k) {
      var v = p[k];
      var dd;
      if (k === "inputs") {
        dd = h("dd", {}, [h("pre", { class: "prov-pre", text: JSON.stringify(v, null, 1) })]);
      } else {
        dd = h("dd", { text: Array.isArray(v) ? v.join(", ") : String(v) });
      }
      dl.appendChild(h("dt", { text: PROV_NAMES[k] || k }));
      dl.appendChild(dd);
    });
    var block = h("div", { class: "prov-item" }, [h("p", { class: "prov-label", text: s.label }), dl]);
    if (s.note) block.appendChild(h("p", { class: "prov-note", text: s.note }));
    return block;
  }

  var openPop = null;
  function closePop(returnFocus) {
    if (!openPop) return;
    openPop.pop.hidden = true;
    openPop.btn.setAttribute("aria-expanded", "false");
    var btn = openPop.btn;
    openPop = null;
    if (returnFocus) btn.focus();
  }
  if (typeof document !== "undefined") {
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closePop(true); });
    document.addEventListener("click", function (e) {
      if (openPop && !openPop.pop.contains(e.target) && !openPop.btn.contains(e.target)) closePop(false);
    });
  }

  var popSeq = 0;
  function badgeRow(chartId, present, pending, pendingKinds) {
    var row = h("div", { class: "badges", role: "list", "aria-label": "Sources" });
    var byBadge = {};
    present.forEach(function (s) { var b = badgeOf(s); (byBadge[b] = byBadge[b] || []).push(s); });
    BADGE_ORDER.forEach(function (b) {
      if (!byBadge[b]) return;
      var id = "pop-" + chartId + "-" + (++popSeq);
      var btn = h("button", { type: "button", class: "badge badge-" + b, "aria-expanded": "false", "aria-controls": id },
        [h("span", { class: "badge-dot", "aria-hidden": "true" }), h("span", { text: BADGES[b] })]);
      var pop = h("div", { class: "popover", id: id, "aria-label": BADGES[b] + " sources" });
      pop.hidden = true;
      pop.appendChild(h("p", { class: "pop-head", text: BADGES[b] }));
      byBadge[b].forEach(function (s) { pop.appendChild(provenanceBlock(s)); });
      var close = h("button", { type: "button", class: "pop-close", text: "Close" });
      close.addEventListener("click", function () { closePop(true); });
      pop.appendChild(close);
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var wasOpen = openPop && openPop.pop === pop;
        closePop(false);
        if (!wasOpen) {
          pop.hidden = false;
          btn.setAttribute("aria-expanded", "true");
          openPop = { pop: pop, btn: btn };
          close.focus();
        }
      });
      row.appendChild(h("div", { class: "badge-wrap", role: "listitem" }, [btn, pop]));
    });
    pending.forEach(function (id) {
      row.appendChild(h("div", { class: "badge-wrap", role: "listitem" }, [
        h("span", { class: "badge badge-pending" }, [
          h("span", { class: "badge-dot", "aria-hidden": "true" }),
          h("span", { text: pendingKinds && pendingKinds[id]
            ? BADGES[pendingKinds[id]] + ": coming in a data update"
            : BADGES[badgeOfPending(id)] + ": live reading coming" })
        ])
      ]));
    });
    return row;
  }

  function legendSwatch(ds) {
    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "26"); svg.setAttribute("height", "12"); svg.setAttribute("aria-hidden", "true");
    if (ds._dots) {
      var shape = ds._study ? ds.pointStyle : "circle";
      var c = document.createElementNS(svgNS, shape === "triangle" ? "polygon" : shape === "circle" ? "circle" : "rect");
      if (shape === "triangle") {
        c.setAttribute("points", "13,1 19,11 7,11");
      } else if (shape === "rect") {
        c.setAttribute("x", "8.5"); c.setAttribute("y", "1.5"); c.setAttribute("width", "9"); c.setAttribute("height", "9");
      } else if (shape === "rectRot") {
        c.setAttribute("x", "8"); c.setAttribute("y", "1"); c.setAttribute("width", "10"); c.setAttribute("height", "10");
        c.setAttribute("transform", "rotate(45 13 6)");
      } else { c.setAttribute("cx", "13"); c.setAttribute("cy", "6"); c.setAttribute("r", "4.5"); }
      c.setAttribute("fill", ds._study ? "none" : ds.borderColor);
      c.setAttribute("stroke", ds.borderColor); c.setAttribute("stroke-width", "1.6");
      svg.appendChild(c);
    } else if (ds._bar) {
      var r = document.createElementNS(svgNS, "rect");
      r.setAttribute("x", "4"); r.setAttribute("y", "1"); r.setAttribute("width", "18"); r.setAttribute("height", "10");
      r.setAttribute("rx", "2"); r.setAttribute("fill", ds.backgroundColor);
      svg.appendChild(r);
    } else {
      var l = document.createElementNS(svgNS, "line");
      l.setAttribute("x1", "1"); l.setAttribute("x2", "25"); l.setAttribute("y1", "6"); l.setAttribute("y2", "6");
      l.setAttribute("stroke", ds.borderColor); l.setAttribute("stroke-width", "2.5");
      if (ds.borderDash && ds.borderDash.length) l.setAttribute("stroke-dasharray", ds.borderDash.join(" "));
      svg.appendChild(l);
    }
    return svg;
  }

  /* ---------------------------------------------------------------- the chart */

  var live = [];

  function buildDatasets(chartId, list, isCat, opts) {
    var counters = { vanilla: 0, mod: 0, study: 0, shape: 0 };
    var emph = opts.emphasis || {};
    var stepped = opts.stepped || [];
    return list.map(function (s) {
      var side = sideOf(s.id);
      var variant = emph.hasOwnProperty(s.id) ? emph[s.id] : counters[side]++;
      var studyStyle = s.badge === "study" ? STUDY_STYLES[counters.shape++ % STUDY_STYLES.length] : null;
      var st = styleFor(s, variant);
      var dots = isMeasured(s) || s.badge === "study";
      var data = s.points.map(function (p) { return { x: p[0], y: p[1] }; });
      var ds = {
        label: s.label, data: data, _id: s.id, _side: side, _unit: niceUnit(s), _xunit: (s.units && s.units.x) || "",
        borderColor: st.color, backgroundColor: st.color, borderWidth: 2, borderDash: st.dash,
        _dots: dots, _study: s.badge === "study"
      };
      if (isCat && !dots) {
        ds.type = "bar";
        ds._bar = true;
        ds.borderWidth = 0;
        ds.borderRadius = 3;
        ds.borderSkipped = "start";
        ds.maxBarThickness = 34;
        ds.minBarLength = 2;
        ds.order = 2;
      } else if (dots) {
        ds.type = "line";
        ds.showLine = false;
        ds.pointRadius = s.badge === "study" ? 6 : 4.5;
        ds.pointHoverRadius = ds.pointRadius + 2;
        ds.pointStyle = studyStyle || "circle";
        ds.pointBackgroundColor = s.badge === "study" ? "transparent" : st.color;
        ds.pointBorderColor = s.badge === "study" ? st.color : token("--paper");
        ds.pointBorderWidth = s.badge === "study" ? 2 : 1.5;
        ds.order = 0;
      } else {
        ds.type = "line";
        ds.pointRadius = s.points.length <= 8 ? 3 : 0;
        ds.pointHoverRadius = 4;
        ds.pointBackgroundColor = st.color;
        ds.tension = 0;
        ds.fill = false;
        ds.order = 1;
        if (stepped.indexOf(s.id) >= 0) ds.stepped = "before";
      }
      if (opts.endpoints && opts.endpoints[s.id]) ds._endLabel = opts.endpoints[s.id];
      return ds;
    });
  }

  function axisTitle(text) {
    return { display: true, text: text, color: token("--ink-2"), font: { family: token("--font-data"), size: 12 } };
  }

  function draw(state) {
    if (state.chart) { state.chart.destroy(); state.chart = null; }
    var opts = state.opts;
    var list = state.present.filter(function (s) { return state.facetSeries ? state.facetSeries.indexOf(s.id) >= 0 : true; });
    if (!list.length) {
      /* A view whose series are all pending: a placeholder in place of the canvas. */
      state.scroller.hidden = true;
      state.empty.hidden = false;
      state.legend.textContent = "";
      return;
    }
    state.scroller.hidden = false;
    state.empty.hidden = true;
    var isCat = !isNum(list[0].points[0][0]);
    var datasets = buildDatasets(state.chartId, list, isCat, opts);
    var labels = null;
    if (isCat) {
      labels = [];
      list.forEach(function (s) { s.points.forEach(function (p) { if (labels.indexOf(p[0]) < 0) labels.push(p[0]); }); });
    }
    var grid = token("--rule"), ink2 = token("--ink-2"), dataFont = token("--font-data");
    var f = state.facet || {};
    function pickOpt(k) { return f.hasOwnProperty(k) ? f[k] : opts[k]; }
    var yNames = pickOpt("yNames"), xNames = opts.xNames;
    var config = {
      type: "line",
      data: { labels: labels || undefined, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: state.reduced ? false : { duration: 350 },
        parsing: true, normalized: true,
        interaction: isCat ? { mode: "index", intersect: false } : { mode: "nearest", intersect: false, axis: "x" },
        scales: {
          x: isCat ? {
            type: "category", grid: { display: false }, border: { color: grid },
            ticks: { color: ink2, font: { family: dataFont, size: 11 }, callback: function (v) {
              var name = this.getLabelForValue(v); return xNames && xNames[name] ? xNames[name] : name; } },
            title: axisTitle(state.chart_x)
          } : {
            type: "linear", grid: { color: grid, lineWidth: 0.6 }, border: { color: grid },
            min: pickOpt("xMin"), max: pickOpt("xMax"),
            ticks: { color: ink2, font: { family: dataFont, size: 11 }, maxTicksLimit: 8 },
            title: axisTitle(pickOpt("xTitle") || state.chart_x)
          },
          y: {
            type: "linear", grid: { color: grid, lineWidth: 0.6 }, border: { display: false },
            min: pickOpt("yMin"), max: pickOpt("yMax"),
            ticks: { color: ink2, font: { family: dataFont, size: 11 }, maxTicksLimit: 7,
              stepSize: yNames ? 1 : undefined,
              callback: function (v) { return yNames ? (yNames[String(v)] || "") : Number(v).toLocaleString("en-US", { maximumFractionDigits: 3 }); } },
            title: axisTitle(f.unit || opts.yTitle || state.chart_y)
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: token("--paper-2"), titleColor: token("--ink"), bodyColor: token("--ink"),
            borderColor: token("--rule-strong"), borderWidth: 1, padding: 10, cornerRadius: 3,
            titleFont: { family: dataFont, size: 12, weight: "700" }, bodyFont: { family: dataFont, size: 12 },
            usePointStyle: true,
            callbacks: {
              title: function (items) {
                if (!items.length) return "";
                var it = items[0], ds = it.dataset;
                var raw = it.raw && it.raw.x !== undefined ? it.raw.x : it.label;
                var shown = xNames && xNames[raw] ? xNames[raw] : fmtFull(raw);
                return ds._xunit ? ds._xunit + ": " + shown : String(shown);
              },
              label: function (it) {
                var ds = it.dataset, y = it.raw && it.raw.y !== undefined ? it.raw.y : it.parsed.y;
                var yName = yNames && yNames[String(y)] ? " (" + yNames[String(y)] + ")" : "";
                return ds.label + ": " + fmtFull(y) + yName + (ds._unit ? "  [" + ds._unit + "]" : "");
              }
            }
          }
        }
      },
      plugins: [endpointPlugin]
    };
    state.chart = new root.Chart(state.canvas.getContext("2d"), config);
    applySide(state);
    renderLegend(state);
  }

  function applySide(state) {
    if (!state.chart) return;
    state.chart.data.datasets.forEach(function (ds, i) {
      var vis = state.side === "both" || ds._side === "study" || ds._side === state.side;
      state.chart.setDatasetVisibility(i, vis);
    });
    state.chart.update(state.reduced ? "none" : undefined);
  }

  /* The vanilla/mod choice is one setting for the whole page: a click on any chart's toggle moves every chart. */
  function setSideEverywhere(k) {
    writeSide(k);
    live.forEach(function (st) {
      if (!st.sideGroup) return;
      st.side = k;
      st.sideGroup.querySelectorAll("button").forEach(function (x) {
        x.setAttribute("aria-pressed", String(x.classList.contains("seg-" + k)));
      });
      applySide(st); renderLegend(st);
    });
  }

  function renderLegend(state) {
    state.legend.textContent = "";
    if (!state.chart) return;
    state.chart.data.datasets.forEach(function (ds, i) {
      var li = h("li", { class: "legend-item" + (state.chart.isDatasetVisible(i) ? "" : " is-off") },
        [legendSwatch(ds), h("span", { text: ds.label })]);
      state.legend.appendChild(li);
    });
  }

  function renderChart(el, chartId, data) {
    var chart = data.charts[chartId];
    if (!chart) throw new Error("no chart " + chartId);
    var idx = seriesIndex(data);
    var present = [], pending = [];
    chart.series.forEach(function (id) { if (idx[id]) present.push(idx[id]); else pending.push(id); });
    var optsEarly = CHART_OPTS[chartId] || {};
    var pendingKinds = optsEarly.pendingViews || {};
    (optsEarly.facets || []).forEach(function (f) {
      f.series.forEach(function (id) { if (!idx[id] && pending.indexOf(id) < 0) pending.push(id); });
    });
    var opts = CHART_OPTS[chartId] || {};

    var body = h("div", { class: "chart-body" });
    var head = h("div", { class: "chart-head" }, [
      h("p", { class: "chart-title", text: chart.title }),
      h("p", { class: "chart-axes", text: chart.y + "  /  " + chart.x })
    ]);
    body.appendChild(head);

    if (!present.length) {
      body.appendChild(h("div", { class: "chart-placeholder" }, [
        h("p", { class: "ph-big", text: "Live reading coming" }),
        h("p", { text: "This chart waits on a live session. It fills in when the run is recorded." })
      ]));
      body.appendChild(badgeRow(chartId, present, pending, pendingKinds));
      el.insertBefore(body, el.firstChild);
      return null;
    }

    var state = {
      chartId: chartId, opts: opts, present: present, side: readSide(), chart: null,
      chart_x: chart.x, chart_y: chart.y, facetSeries: null, facet: null,
      reduced: root.matchMedia ? root.matchMedia("(prefers-reduced-motion: reduce)").matches : false
    };
    var controls = h("div", { class: "chart-controls" });
    var sides = {};
    present.forEach(function (s) { sides[sideOf(s.id)] = true; });
    pending.forEach(function (id) { sides[sideOf(id)] = true; });
    if (sides.vanilla && sides.mod) {
      var grp = h("div", { class: "seg", role: "group", "aria-label": "Show" });
      ["both", "vanilla", "mod"].forEach(function (k) {
        var b = h("button", { type: "button", class: "seg-btn seg-" + k, "aria-pressed": String(state.side === k), text: SIDE_NAMES[k] });
        b.addEventListener("click", function () { setSideEverywhere(k); });
        grp.appendChild(b);
      });
      state.sideGroup = grp;
      controls.appendChild(grp);
    } else {
      state.side = "both";
    }
    if (opts.facets) {
      var tabs = h("div", { class: "seg seg-facets", role: "group", "aria-label": "Measure" });
      opts.facets.forEach(function (f, i) {
        var b = h("button", { type: "button", class: "seg-btn", "aria-pressed": String(i === 0), text: f.label });
        b.addEventListener("click", function () {
          state.facetSeries = f.series; state.facet = f;
          tabs.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          draw(state);
        });
        tabs.appendChild(b);
      });
      state.facetSeries = opts.facets[0].series; state.facet = opts.facets[0];
      controls.appendChild(tabs);
    }
    if (controls.childNodes.length) body.appendChild(controls);

    var scroller = h("div", { class: "chart-scroll" });
    state.scroller = scroller;
    state.empty = h("div", { class: "chart-placeholder" }, [
      h("p", { class: "ph-big", text: "Coming in a data update" }),
      h("p", { text: "This view waits on a series the guide's data does not hold yet." })
    ]);
    state.empty.hidden = true;
    var frame = h("div", { class: "chart-frame" });
    state.canvas = h("canvas", { role: "img", "aria-label": chart.title });
    frame.appendChild(state.canvas);
    scroller.appendChild(frame);
    body.appendChild(scroller);
    body.appendChild(state.empty);
    state.legend = h("ul", { class: "legend" });
    body.appendChild(state.legend);
    body.appendChild(badgeRow(chartId, present, pending, pendingKinds));
    el.insertBefore(body, el.firstChild);

    draw(state);
    live.push(state);
    return state;
  }

  /* Re-render every chart when the theme changes, so text, grid and series colours follow the tokens. */
  function redrawAll() { live.forEach(function (st) { draw(st); }); }
  if (typeof document !== "undefined" && root.matchMedia) {
    var mq = root.matchMedia("(prefers-color-scheme: dark)");
    if (mq.addEventListener) mq.addEventListener("change", redrawAll);
    else if (mq.addListener) mq.addListener(redrawAll);
    if (root.MutationObserver) {
      new root.MutationObserver(redrawAll).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    }
  }

  root.NRGuide = {
    renderChart: renderChart, fill: fill, fillAll: fillAll, evalPick: evalPick, parsePick: parsePick,
    BADGES: BADGES, CHART_OPTS: CHART_OPTS
  };
})(typeof window !== "undefined" ? window : this);
