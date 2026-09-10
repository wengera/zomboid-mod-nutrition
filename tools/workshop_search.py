#!/usr/bin/env python3
"""Sweep the public Steam Workshop for nutrition-relevant B42 mods and join to the corpus.

Eight search terms against the `Build 42`-tagged, ready-to-use section of the Workshop browse
page, one page per term (Steam serves 30 results a page and this tool does not paginate), then
one optional `--details` pass over the union of ids for size/posted/updated. Output:
data/workshop-search.json + data/workshop-search.csv + a console census.

**This is a catalog of what exists, not of what can be measured here.** A result that is not
installed under the workshop root cannot be linted, profiled, booted or measured: the workshop
folder is read-only to this repo and subscribing needs Steam and a human. Every not-installed
row is therefore graded **W** and carries the exact `unblock` action; an installed row is graded
**C** because it joins to a record in data/mod-inventory.json, which is read off shipped files.
Teardown picks come only from the installed corpus.

**The join key is `workshop_id`, never `mod_id`.** A Workshop page knows its item id and nothing
about the id a mod declares in `mod.info`; slice 08 task 1 moved 20 of the 230 corpus `mod_id`s
onto the engine-resolved value and one is `""`, so a name-shaped join would be wrong on both
sides. One workshop item can hold several mods (230 records across 179 items), so `mod_ids` is
a list.

**`--compressed` is mandatory.** Without it curl hands back gzip bytes and every regex misses
(5 876 unreadable bytes vs ~686 000 readable, verified 2026-09-10). The browse page is
React-rendered with obfuscated class names, but every result still ships as an
`<a href=...filedetails/?id=N">` wrapping an `<img alt="<title>">`, and that pair is all this
tool reads off it. The item page is the old server-rendered template: `workshopItemTitle` plus
two or three `detailsStatRight` divs -- size, posted, and updated only when the item has ever
been updated, so `updated is None` is a fact about the item, not a parse failure.

Steam is a live site and `browsesort=trend` reorders hourly: **quote a count from this dataset
with the `meta.fetched` stamp**, never bare. Nothing here is subscribed, downloaded or written
under the workshop root; pages are read once, at one request a second, and recorded as extracted
facts (id, title, size, posted, updated) rather than mirrored. A fetch that fails is retried once
after 5 s **per failure mode** -- once for a transport error or an empty body in
`fetch_once_retried`, once more for an unreadable template in `fetch_usable`, so a URL that fails
both ways costs at most 3 curls and 10 s of sleeping -- and is then recorded on the row as
`error`. It never raises, so a sweep that loses one page still writes the rest.

**A 200 is not a page.** Steam sometimes answers a `filedetails/?id=N` read with the generic
Workshop landing page -- 310 185 bytes, `<title>Steam Workshop</title>`, no `workshopItemTitle`
and no `detailsStatRight` anywhere -- at HTTP 200, so curl reports success and the parser
silently yields four `null`s that look exactly like an item shipping no stats. The first run of
this tool recorded 177 such rows (2026-09-10 15:52, output discarded). Every fetch is therefore
checked for the marker its parser needs (`browsesort` or a result anchor on a browse page, both
`workshopItemTitle` and `detailsStatRight` on an item page); a body without them is retried once
and then recorded as `details_status: "failed"` with the reason in `error`. A missing template is
a finding, never an empty value.

**How many item pages that leaves is NOT modelled here.** What is on record is four dated
observations, all 2026-09-10, and no rule fitted to them: 15:45 -- 8 browse pages then 3 item
pages read, then the alternate template; 15:58 -- the alternate template from the very first
request; 16:25 (the committed sweep) -- 8 browse pages then all 9 item pages it asked for, none
throttled; 16:55 (`--fill --include-not-requested`, 30 minutes later) -- 6 more item pages read
4 s apart in 24 s, none throttled, for 15 item pages read in the same half hour. This tool
claims no budget, no rate and no window, and it will not tell you in advance whether a read will
land. Because a read may not land, `--details-ids` spends the pass on a **declared
subset** -- the rows the slice actually quotes -- and every other row is recorded
`details_status: "not_requested"`, which is a decision about this run and says nothing about the
item. `--details` with no subset asks for all of them; `meta.details_ids` says which rows were
asked for either way. `--fill` is the second chance: on its own it re-fetches only the rows
carrying a real failure, and with `--include-not-requested [--fill-ids <ids|N>]` it tops up rows
that were never asked for -- either way the row set, the terms and `meta.fetched` are left alone,
so the stamp still describes the browse pass the rows came from, and each pass appends an entry
to `meta.fill`.

**Three row states, one field.** `details_status` is `fetched` (an item page was read: `size` and
`posted` are real, `updated` is real or genuinely absent), `failed` (an item page was requested
and could not be read: `error` says why) or `not_requested` (no item page was asked for: `error`
is `null`, and nothing about the item is claimed). `error` is a fetch failure and nothing else --
never a decision.

Stdlib + `subprocess` curl, in tools/wiki_mirror.py's shape. No import of testing/pzt.
"""
import argparse, csv, datetime, html, json, os, re, subprocess, sys, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"
BROWSE = ("https://steamcommunity.com/workshop/browse/?appid=108600&searchtext={term}"
          "&browsesort=trend&section=readytouseitems&requiredtags%5B%5D=Build+42")
ITEM = "https://steamcommunity.com/sharedfiles/filedetails/?id={id}"
RESULT_RX = re.compile(r'sharedfiles/filedetails/\?id=(\d+)"[^>]*>\s*<img[^>]*alt="([^"]+)"')
STAT_RX = re.compile(r'detailsStatRight">([^<]*)')   # [size, posted, updated?] in that order
TITLE_RX = re.compile(r'workshopItemTitle">([^<]*)')
TERMS = ["nutrition", "vitamin", "malnutrition", "diet", "hydration",
         "food overhaul", "cooking overhaul", "spoilage"]

# The marker each parser needs, present on a page that matched nothing as well as on a full one:
# a browse page always renders the sort control, an item page always renders its title block and
# its stats block. Both item markers are required: half a template is not a page this parser can
# read, and an item page that renders a title with no `detailsStatRight` would otherwise pass the
# check and then hand back the three nulls the check exists to catch.
BROWSE_MARKER = "browsesort"
ITEM_MARKERS = ("workshopItemTitle", "detailsStatRight")
BROWSE_TEMPLATE_ERR = "unrecognised browse-page template (no browsesort control)"
ITEM_TEMPLATE_ERR = "unrecognised item-page template (no workshopItemTitle / detailsStatRight)"

BUILD = "42.20.4 (b0bbce05d5)"
PAUSE = 1.0          # seconds between browse requests -- one page a second, politely
DETAIL_PAUSE = 4.0   # item pages are the scarce read; 4 s is the spacing every observation used
RETRY_PAUSE = 5.0    # one retry per failure mode, then the failure is recorded on the row
FETCHED, NOT_REQUESTED, FAILED = "fetched", "not_requested", "failed"   # every row is one of these
NOT_FETCHED = ("details_status=not_requested: no item page was requested for this row -- it was "
               "outside --details-ids. A decision about the run, not a fact about the item, and "
               "not a fetch failure: `error` is null. See meta.notes and --fill.")
HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(os.path.dirname(HERE), "data", "mod-inventory.json")
OUT_DIR = os.path.join(os.path.dirname(HERE), "data")

CSV_COLUMNS = ["workshop_id", "title", "terms", "installed", "mod_ids",
               "size", "posted", "updated", "details_status", "error"]

UNBLOCK = ("subscribe to {id} in Steam, let it download, re-run tools/mod_inventory.py")


def fetch(url):
    """One curl. Returns (body, None) or (None, reason) -- never raises, never retries."""
    r = subprocess.run(["curl", "-sS", "--compressed", "-A", UA, "--max-time", "40", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None, f"curl rc={r.returncode}: {r.stderr.strip()[:200]}"
    return r.stdout, None


def fetch_once_retried(url, pause=RETRY_PAUSE, sleep=time.sleep):
    """`fetch` plus the one allowed retry. An empty body counts as a failure: a 200 with no
    HTML parses to zero results, which would otherwise be indistinguishable from a term that
    genuinely matched nothing."""
    body, err = fetch(url)
    if err is None and not (body or "").strip():
        err = "empty response body"
        body = None
    if err is None:
        return body, None
    sleep(pause)
    body, err2 = fetch(url)
    if err2 is None and not (body or "").strip():
        err2 = "empty response body"
        body = None
    if err2 is None:
        return body, None
    return None, f"{err} (retry: {err2})"


def usable_browse_page(body):
    """The sort control, or failing that a result anchor: a deploy that renames the control still
    serves the `filedetails/?id=N` + `alt` pair, which is the only thing this parser reads."""
    return BROWSE_MARKER in (body or "") or RESULT_RX.search(body or "") is not None


def usable_item_page(body):
    return all(marker in (body or "") for marker in ITEM_MARKERS)


def fetch_usable(url, usable, template_err, fetcher=fetch_once_retried, sleep=time.sleep,
                 retry_pause=RETRY_PAUSE):
    """(body, None) or (None, reason). A body the parser cannot read is a failure with one
    retry of its own -- Steam's alternate template answers 200 and would otherwise be recorded
    as an item with no stats. A transport error is not retried again here: `fetch_once_retried`
    has already spent the one allowed retry on it."""
    for attempt in (0, 1):
        if attempt:
            sleep(retry_pause)
        body, err = fetcher(url)
        if err is not None:
            return None, err
        if usable(body):
            return body, None
    return None, template_err


def parse_results(body):
    """De-duplicated [(id, title)] in page order, `alt` entities unescaped."""
    out, seen = [], set()
    for wid, title in RESULT_RX.findall(body or ""):
        if wid in seen:
            continue
        seen.add(wid)
        out.append((wid, html.unescape(title)))
    return out


def parse_details(body):
    """{title, size, posted, updated} off an item page. `updated` is None when the page shows
    only two stats -- the item has never been updated since it was posted."""
    stats = [s.strip() for s in STAT_RX.findall(body or "")]
    titles = TITLE_RX.findall(body or "")
    return {"title": html.unescape(titles[0].strip()) if titles else None,
            "size": stats[0] if len(stats) > 0 else None,
            "posted": stats[1] if len(stats) > 1 else None,
            "updated": stats[2] if len(stats) > 2 else None}


def search(term, fetcher=fetch_once_retried, sleep=time.sleep):
    """(results, error) for one term. The error is the term's, not a row's: on a failed fetch
    the results are empty and the reason is recorded in meta.per_term. An empty list from a
    page that *is* a browse page is a real answer -- `malnutrition` returned 2 results on
    2026-09-10, and a term can legitimately return none."""
    body, err = fetch_usable(BROWSE.format(term=term.replace(" ", "+")), usable_browse_page,
                             BROWSE_TEMPLATE_ERR, fetcher=fetcher, sleep=sleep)
    if err is not None:
        return [], err
    return parse_results(body), None


def details(item_id, fetcher=fetch_once_retried, sleep=time.sleep):
    """{title, size, posted, updated} for one item, plus `error` when the page could not be
    read. Never raises: the row keeps whatever the sweep already knows about it."""
    body, err = fetch_usable(ITEM.format(id=item_id), usable_item_page, ITEM_TEMPLATE_ERR,
                             fetcher=fetcher, sleep=sleep)
    if err is not None:
        return {"title": None, "size": None, "posted": None, "updated": None, "error": err}
    d = parse_details(body)
    d["error"] = None
    return d


def load_corpus(path=CORPUS):
    """{workshop_id: [mod_id, ...]} off data/mod-inventory.json -- a bare JSON array of records,
    keyed on the string `workshop_id`. `mod_id` is kept as declared, `""` included."""
    with open(path, encoding="utf-8") as fh:
        records = json.load(fh)
    index = {}
    for rec in records:
        index.setdefault(str(rec.get("workshop_id", "")), []).append(rec.get("mod_id", ""))
    return index


def join(hits, corpus):
    """Rows for every distinct id, joined to the installed corpus on `workshop_id`.

    `hits` is {workshop_id: {"title": t, "terms": [...]}} in first-seen order.
    """
    rows = []
    for wid, hit in hits.items():
        mod_ids = corpus.get(wid)
        installed = mod_ids is not None
        rows.append({"workshop_id": wid,
                     "title": hit["title"],
                     "terms": hit["terms"],
                     "installed": installed,
                     "mod_ids": sorted(mod_ids) if installed else [],
                     "size": None, "posted": None, "updated": None,
                     "details_status": NOT_REQUESTED, "error": None,
                     "grade": "C" if installed else "W",
                     "unblock": None if installed else UNBLOCK.format(id=wid)})
    rows.sort(key=lambda r: int(r["workshop_id"]))
    return rows


def select_detail_ids(rows, spec):
    """Which rows the details pass may spend an item-page read on. `spec` is None for every row,
    or a list of ids in which the token `installed` expands to every row that joined to the
    corpus -- so one command line can say "the three installed hits plus these named ids"
    without knowing in advance which three the browse pages returned.

    An id that is not in this sweep's results raises: a typo would otherwise be counted in
    `details_requested`, fetched for nobody, and break `requested == fetched + failures` in a way
    no row records.
    """
    if spec is None:
        return {r["workshop_id"] for r in rows}
    known = {r["workshop_id"] for r in rows}
    want = set()
    for token in spec:
        if token == "installed":
            want |= {r["workshop_id"] for r in rows if r["installed"]}
        elif token in known:
            want.add(token)
        else:
            raise ValueError(f"--details-ids: {token!r} is neither `installed` nor an id in this "
                             f"sweep's {len(known)} result(s)")
    return want


def apply_details(row, d):
    """Write one item-page read onto a row: the three stats, `details_status` and `error`.
    `error` carries the fetch failure and nothing else -- a row that was never asked for keeps
    `details_status: not_requested` and a null error, and never passes through here."""
    row["size"], row["posted"], row["updated"] = d["size"], d["posted"], d["updated"]
    row["error"] = d["error"]
    row["details_status"] = FAILED if d["error"] else FETCHED
    return row


def sweep(terms=TERMS, with_details=False, detail_ids=None, corpus_path=CORPUS, corpus=None,
          sleep=time.sleep, searcher=search, detailer=details, detail_pause=DETAIL_PAUSE,
          log=lambda *a: None):
    """The whole run: 8 browse pages, an optional details pass over a subset, then the join."""
    hits, per_term = {}, {}
    for i, term in enumerate(terms):
        if i:
            sleep(PAUSE)
        results, err = searcher(term)
        per_term[term] = {"results": len(results), "error": err}
        log(f"  {term:<16} {len(results):>3} result(s)" + (f"  ERROR {err}" if err else ""))
        for wid, title in results:
            hit = hits.setdefault(wid, {"title": title, "terms": []})
            if term not in hit["terms"]:
                hit["terms"].append(term)

    rows = join(hits, corpus if corpus is not None else load_corpus(corpus_path))

    asked = 0
    wanted = set()
    if with_details:
        wanted = select_detail_ids(rows, detail_ids)
        log(f"\ndetails over {len(wanted)} of {len(rows)} id(s), {detail_pause}s apart:")
        if len(wanted) < len(rows):
            log(f"  the other {len(rows) - len(wanted)}: {NOT_FETCHED}")
        for row in rows:
            if row["workshop_id"] not in wanted:
                continue                      # stays `not_requested`, with a null error
            if asked:
                sleep(detail_pause)
            asked += 1
            d = apply_details(row, detailer(row["workshop_id"]))
            if d["error"]:
                log(f"  ERROR {row['workshop_id']}: {d['error']}")
            else:
                log(f"  {row['workshop_id']}  {d['size']}  posted {d['posted']}"
                    f"  updated {d['updated']}")

    installed = [r for r in rows if r["installed"]]
    counts = {"terms": len(terms),
              "results_total": sum(t["results"] for t in per_term.values()),
              "term_failures": sum(1 for t in per_term.values() if t["error"]),
              "distinct_ids": len(rows),
              "installed": len(installed),
              "not_installed": len(rows) - len(installed),
              "details_requested": len(wanted)}
    recount_details(rows, counts)             # one definition of fetched/failed/not-requested
    return rows, per_term, counts


NOTES = [
    "Steam is live and browsesort=trend reorders hourly: quote any count here with meta.fetched.",
    "An item page can answer HTTP 200 with an alternate template that carries no "
    "workshopItemTitle and no detailsStatRight -- the generic Workshop landing page. That is "
    "measured and the parser rejects it (details_status=failed), but how many item pages a "
    "session may read is NOT modelled here: the observations on 2026-09-10 are 15:45 (8 browse "
    "pages, then 3 item pages, then the alternate template), 15:58 (the alternate template from "
    "the first request), 16:25 (8 browse pages then all 9 item pages asked for, none throttled) "
    "and 16:55 (a --fill --include-not-requested pass, 6 more item pages read in 24 s, none "
    "throttled). No rate, window or budget is claimed from them.",
    "details_status is the row's own answer: fetched (an item page was read), failed (asked for "
    "and unreadable -- error says why), not_requested (never asked for; error is null and "
    "nothing about the item is claimed). size/posted/updated exist only on fetched rows.",
    "A not-installed row cannot be linted, profiled, booted or measured from this repo: it is "
    "graded W and carries the subscribe-and-rescan action that would change that.",
]


def describe_detail_ids(with_details, detail_ids):
    """What meta.details_ids records: which rows the details pass was allowed to ask for.
    The tokens are kept as passed -- `installed` expands at run time, so the list in `meta` can
    be shorter than `counts.details_requested`."""
    if not with_details:
        return "none"
    return "all" if detail_ids is None else list(detail_ids)


def build_meta(per_term, counts, corpus, now=None, detail_ids="none"):
    """`corpus` is the loaded index from `load_corpus` -- the same object the join used, so the
    record and item counts in `meta` describe exactly what the rows were joined against and the
    file is not read a second time (it is a live tree; a re-read can disagree with the join)."""
    now = now or datetime.datetime.now()
    records = [mod_id for mod_ids in corpus.values() for mod_id in mod_ids]
    return {"build": BUILD,
            "generated": now.strftime("%Y-%m-%d"),
            "fetched": now.strftime("%Y-%m-%d %H:%M"),
            "tool": "tools/workshop_search.py",
            "terms": list(per_term),
            "source_url_pattern": {"browse": BROWSE, "item": ITEM},
            "details_ids": detail_ids,
            "corpus": {"path": "data/mod-inventory.json",
                       "records": len(records),
                       "workshop_items": len(corpus)},
            "per_term": per_term,
            "counts": counts,
            "notes": NOTES}


def recount_details(rows, counts):
    """The four details counters off `details_status` -- the row's own answer, and the only
    definition of "fetched" in this module. `details_incomplete` must stay 0: a read that
    reported no error owes the row a file size, and it read 177 on the first run."""
    counts["details_fetched"] = sum(1 for r in rows if r["details_status"] == FETCHED)
    counts["detail_failures"] = sum(1 for r in rows if r["details_status"] == FAILED)
    counts["details_not_fetched"] = sum(1 for r in rows if r["details_status"] == NOT_REQUESTED)
    counts["details_incomplete"] = sum(1 for r in rows
                                       if r["details_status"] == FETCHED and not r["size"])
    return counts


def parse_fill_ids(spec):
    """`--fill-ids` is either a count -- a bare number of fewer than 7 digits, where a workshop id
    is 9 or 10 -- or a comma-separated list of ids. `None` when the flag was not passed."""
    if spec is None:
        return None
    tokens = [t.strip() for t in str(spec).split(",") if t.strip()]
    if len(tokens) == 1 and tokens[0].isdigit() and len(tokens[0]) < 7:
        return int(tokens[0])
    return tokens


def select_fill_rows(rows, include_not_requested=False, fill_ids=None):
    """Which rows a fill pass re-fetches, in dataset order.

    Always every `failed` row -- a fault is always worth another try. `not_requested` rows are a
    decision, not a fault, so they are topped up only when asked for: `--include-not-requested`
    with either a list of ids or a count N (the first N in dataset order), or with neither, which
    means all of them. An id naming no `not_requested` row raises rather than being ignored.
    """
    todo = [r for r in rows if r["details_status"] == FAILED]
    pending = [r for r in rows if r["details_status"] == NOT_REQUESTED]
    extra = []
    if include_not_requested:
        if fill_ids is None:
            extra = pending
        elif isinstance(fill_ids, int):
            extra = pending[:fill_ids]
        else:
            by_id = {r["workshop_id"]: r for r in pending}
            missing = [t for t in fill_ids if t not in by_id]
            if missing:
                raise ValueError("--fill-ids: no not_requested row for " + ", ".join(missing))
            extra = [by_id[t] for t in fill_ids]
    wanted = {r["workshop_id"] for r in todo} | {r["workshop_id"] for r in extra}
    return [r for r in rows if r["workshop_id"] in wanted]


def fill(payload, detailer=details, sleep=time.sleep, detail_pause=DETAIL_PAUSE, now=None,
         include_not_requested=False, fill_ids=None, log=lambda *a: None):
    """Second chance for the rows a lost window cost, and top-up for rows never asked for.

    Re-fetches every `failed` row, plus -- with `include_not_requested` -- the `not_requested`
    rows named by `fill_ids` (a list of ids, a count N, or None for all of them). The row set,
    the terms and `meta.fetched` are left alone: this fills columns in the sweep that was
    captured, so the stamp on the rows stays true, and each pass appends
    `{at, ids, fetched, failed}` to `meta.fill` so the file says when each column was read.
    """
    rows = payload["results"]
    todo = select_fill_rows(rows, include_not_requested, fill_ids)
    newly_asked = sum(1 for r in todo if r["details_status"] == NOT_REQUESTED)
    log(f"fill: {len(todo)} row(s) ({len(todo) - newly_asked} failed, {newly_asked} "
        f"not_requested), {detail_pause}s apart")
    fetched = failed = 0
    for i, row in enumerate(todo):
        if i:
            sleep(detail_pause)
        d = apply_details(row, detailer(row["workshop_id"]))
        fetched, failed = fetched + (d["error"] is None), failed + (d["error"] is not None)
        log(f"  {row['workshop_id']}  " + (f"ERROR {d['error']}" if d["error"] else
                                           f"{d['size']}  posted {d['posted']}  "
                                           f"updated {d['updated']}"))
    counts = payload["meta"]["counts"]
    # A row asked for the first time joins `details_requested`, so it keeps meaning "item pages
    # this dataset asked for" and `requested == fetched + failures` still holds after a fill.
    counts["details_requested"] = counts.get("details_requested", 0) + newly_asked
    recount_details(rows, counts)
    payload["meta"].setdefault("fill", []).append(
        {"at": (now or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"),
         "ids": [r["workshop_id"] for r in todo], "fetched": fetched, "failed": failed})
    return payload


def write_json(path, meta, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"meta": meta, "results": rows}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(CSV_COLUMNS)
        for r in rows:
            w.writerow([r["workshop_id"], r["title"], ";".join(r["terms"]),
                        "true" if r["installed"] else "false", ";".join(r["mod_ids"]),
                        r["size"] or "", r["posted"] or "", r["updated"] or "",
                        r["details_status"], r["error"] or ""])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--details", action="store_true",
                    help="second pass for size/posted/updated (see --details-ids: an item page "
                         "can answer 200 with an unreadable template, so asking for all 180 "
                         "buys mostly `failed` rows)")
    ap.add_argument("--details-ids", default=None,
                    help="comma-separated workshop ids to spend the details pass on; the token "
                         "`installed` expands to every row that joined to the corpus, and an id "
                         "this sweep did not return is an error. Omit to try every id.")
    ap.add_argument("--details-pause", type=float, default=DETAIL_PAUSE,
                    help=f"seconds between item-page requests (default {DETAIL_PAUSE})")
    ap.add_argument("--fill", action="store_true",
                    help="re-fetch the rows of the written dataset that carry a details failure "
                         "and rewrite it; no browse pages, no new rows, meta.fetched unchanged")
    ap.add_argument("--include-not-requested", action="store_true",
                    help="with --fill: also top up rows that were never asked for (see "
                         "--fill-ids); without it a fill only repairs real failures")
    ap.add_argument("--fill-ids", default=None,
                    help="with --fill --include-not-requested: comma-separated workshop ids, or "
                         "a bare count N for the first N not_requested rows in dataset order. "
                         "Omit to top up every not_requested row.")
    ap.add_argument("--out-dir", default=OUT_DIR, help="where the json/csv pair is written")
    ap.add_argument("--corpus", default=CORPUS, help="data/mod-inventory.json to join against")
    args = ap.parse_args(argv)
    if args.include_not_requested and not args.fill:
        ap.error("--include-not-requested only means anything with --fill")
    detail_ids = ([t.strip() for t in args.details_ids.split(",") if t.strip()]
                  if args.details_ids else None)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                   # pragma: no cover - console-dependent
        pass

    jpath = os.path.join(args.out_dir, "workshop-search.json")
    cpath = os.path.join(args.out_dir, "workshop-search.csv")

    if args.fill:
        with open(jpath, encoding="utf-8") as fh:
            payload = json.load(fh)
        fill(payload, detail_pause=args.details_pause,
             include_not_requested=args.include_not_requested,
             fill_ids=parse_fill_ids(args.fill_ids), log=print)
        write_json(jpath, payload["meta"], payload["results"])
        write_csv(cpath, payload["results"])
        c, last = payload["meta"]["counts"], payload["meta"]["fill"][-1]
        print(f"\nthis pass: {last['fetched']} read / {last['failed']} failed at {last['at']}")
        print(f"dataset: {c['details_fetched']} fetched / {c['detail_failures']} failed / "
              f"{c['details_not_fetched']} not requested\n-> {jpath}\n-> {cpath}")
        return 0

    print(f"Workshop sweep: {len(TERMS)} term(s), Build 42 tag, browsesort=trend")
    corpus = load_corpus(args.corpus)
    rows, per_term, counts = sweep(with_details=args.details, detail_ids=detail_ids,
                                   corpus=corpus, detail_pause=args.details_pause, log=print)
    meta = build_meta(per_term, counts, corpus,
                      detail_ids=describe_detail_ids(args.details, detail_ids))

    os.makedirs(args.out_dir, exist_ok=True)
    write_json(jpath, meta, rows)
    write_csv(cpath, rows)

    print(f"\n{counts['results_total']} result(s) over {counts['terms']} term(s) -> "
          f"{counts['distinct_ids']} distinct id(s), fetched {meta['fetched']}")
    print(f"  installed {counts['installed']} / not installed {counts['not_installed']} "
          f"(corpus {meta['corpus']['records']} records, "
          f"{meta['corpus']['workshop_items']} items)")
    if args.details:
        print(f"  details: {counts['details_fetched']} fetched, "
              f"{counts['detail_failures']} failed, "
              f"{counts['details_not_fetched']} not requested "
              f"(top up with --fill --include-not-requested)")
    if counts["term_failures"] or counts["detail_failures"]:
        print(f"  failures: {counts['term_failures']} term(s), "
              f"{counts['detail_failures']} detail page(s)")
    if counts["details_incomplete"]:
        print(f"  WARNING: {counts['details_incomplete']} row(s) reported no error and no size "
              f"-- the item template changed under the parser, do not quote this run")
    print("\nInstalled hits (the only rows a teardown can be picked from):")
    for r in rows:
        if r["installed"]:
            print(f"  {r['workshop_id']}  {','.join(r['mod_ids']):<34.34} {r['title']}")
    print(f"\n-> {jpath}\n-> {cpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
