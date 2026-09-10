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
facts (id, title, size, posted, updated) rather than mirrored. A fetch that fails is retried
once after 5 s and then recorded on the row as `error` -- it never raises, so a sweep that loses
one page still writes the rest.

**A 200 is not a page, and item pages are rationed.** Steam answers a throttled
`filedetails/?id=N` with the generic Workshop landing page -- 310 185 bytes,
`<title>Steam Workshop</title>`, no `workshopItemTitle` and no `detailsStatRight` anywhere --
at HTTP 200, so curl reports success and the parser silently yields four `null`s that look
exactly like an item shipping no stats. The first run of this tool recorded 177 such rows.
Every fetch is therefore checked for the marker its parser needs (`browsesort` on a browse
page, `workshopItemTitle` / `detailsStatRight` on an item page); a body without it is an
`error`, retried once, then recorded. A missing template is a finding, never an empty value.

**The budget is about 13 item pages, not a rate.** Measured 2026-09-10 16:20-16:26: eight
requests 4 s apart all returned the real page, five more 8 s apart did too, and every request
after the thirteenth returned the landing page -- slowing down does not buy more. The size of
the allowance is not fixed and this tool does not model it: the 15:45 run got 3 item pages
after its 8 browse pages, the 15:58 run started already throttled, and the 16:25 run read its
8 browse pages and then all 9 item pages it asked for. Sweeping 180 item pages is therefore
not available to this repo at any polite spacing, so `--details-ids` fetches a **declared
subset** -- the rows the slice actually quotes -- and every other row records `error` saying
it was not attempted. `--details` with no subset still tries all of them and will mostly fail;
`meta.details_ids` says which rows were asked for either way. `--fill` is the repair pass for
a window that was lost: it re-fetches only the rows carrying a real failure and rewrites the
pair, leaving the row set and `meta.fetched` alone so the stamp still describes the browse
pass it came from.

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
# a browse page always renders the sort control, an item page always renders its title block.
BROWSE_MARKER = "browsesort"
ITEM_MARKERS = ("workshopItemTitle", "detailsStatRight")
BROWSE_TEMPLATE_ERR = "unrecognised browse-page template (no browsesort control)"
ITEM_TEMPLATE_ERR = "unrecognised item-page template (no workshopItemTitle / detailsStatRight)"

BUILD = "42.20.4 (b0bbce05d5)"
PAUSE = 1.0          # seconds between browse requests -- one page a second, politely
DETAIL_PAUSE = 4.0   # item pages are rationed, not rate-limited; 4 s is the measured-safe floor
RETRY_PAUSE = 5.0    # one retry, then the failure is recorded on the row
NOT_FETCHED = ("details not fetched: outside --details-ids, and Steam rations item pages "
               "(~13 per window) -- see meta.notes")
HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(os.path.dirname(HERE), "data", "mod-inventory.json")
OUT_DIR = os.path.join(os.path.dirname(HERE), "data")

CSV_COLUMNS = ["workshop_id", "title", "terms", "installed", "mod_ids",
               "size", "posted", "updated", "error"]

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
    return BROWSE_MARKER in (body or "")


def usable_item_page(body):
    return any(marker in (body or "") for marker in ITEM_MARKERS)


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
                     "size": None, "posted": None, "updated": None, "error": None,
                     "grade": "C" if installed else "W",
                     "unblock": None if installed else UNBLOCK.format(id=wid)})
    rows.sort(key=lambda r: int(r["workshop_id"]))
    return rows


def select_detail_ids(rows, spec):
    """Which rows the details pass may spend the item-page budget on. `spec` is None for every
    row, or a list of ids in which the token `installed` expands to every row that joined to the
    corpus -- so one command line can say "the three installed hits plus these named ids"
    without knowing in advance which three the browse pages returned."""
    if spec is None:
        return {r["workshop_id"] for r in rows}
    want = set()
    for token in spec:
        if token == "installed":
            want |= {r["workshop_id"] for r in rows if r["installed"]}
        else:
            want.add(token)
    return want


def sweep(terms=TERMS, with_details=False, detail_ids=None, corpus_path=CORPUS, sleep=time.sleep,
          searcher=search, detailer=details, detail_pause=DETAIL_PAUSE, log=lambda *a: None):
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

    rows = join(hits, load_corpus(corpus_path))

    detail_ok = detail_err = detail_skipped = 0
    wanted = set()
    if with_details:
        wanted = select_detail_ids(rows, detail_ids)
        log(f"\ndetails over {len(wanted)} of {len(rows)} id(s), {detail_pause}s apart:")
        for row in rows:
            if row["workshop_id"] not in wanted:
                row["error"] = NOT_FETCHED
                detail_skipped += 1
                continue
            if detail_ok or detail_err:
                sleep(detail_pause)
            d = detailer(row["workshop_id"])
            row["size"], row["posted"], row["updated"] = d["size"], d["posted"], d["updated"]
            row["error"] = d["error"]
            if d["error"]:
                detail_err += 1
                log(f"  ERROR {row['workshop_id']}: {d['error']}")
            else:
                detail_ok += 1
                log(f"  {row['workshop_id']}  {d['size']}  posted {d['posted']}"
                    f"  updated {d['updated']}")

    installed = [r for r in rows if r["installed"]]
    counts = {"terms": len(terms),
              "results_total": sum(t["results"] for t in per_term.values()),
              "term_failures": sum(1 for t in per_term.values() if t["error"]),
              "distinct_ids": len(rows),
              "installed": len(installed),
              "not_installed": len(rows) - len(installed),
              "details_requested": len(wanted),
              "details_fetched": detail_ok,
              "detail_failures": detail_err,
              "details_not_fetched": detail_skipped,
              # Must stay 0: a details pass that reports no error owes the row a file size.
              # It read 177 on the first run, which is how Steam's rationing was found.
              "details_incomplete": sum(1 for r in rows
                                        if with_details and not r["error"] and not r["size"])}
    return rows, per_term, counts


NOTES = [
    "Steam is live and browsesort=trend reorders hourly: quote any count here with meta.fetched.",
    "Item pages are rationed, not rate-limited: measured 2026-09-10 16:20-16:26, about 13 "
    "filedetails reads succeed per window and every later one returns the generic Workshop "
    "landing page at HTTP 200, at 4 s spacing and at 8 s alike. size/posted/updated therefore "
    "exist only for the meta.details_ids subset; every other row says so in its error column.",
    "A not-installed row cannot be linted, profiled, booted or measured from this repo: it is "
    "graded W and carries the subscribe-and-rescan action that would change that.",
]


def describe_detail_ids(with_details, detail_ids):
    """What meta.details_ids records: which rows were allowed to spend the item-page budget."""
    if not with_details:
        return "none"
    return "all" if detail_ids is None else list(detail_ids)


def build_meta(per_term, counts, corpus_path=CORPUS, now=None, detail_ids="none"):
    now = now or datetime.datetime.now()
    with open(corpus_path, encoding="utf-8") as fh:
        records = json.load(fh)
    return {"build": BUILD,
            "generated": now.strftime("%Y-%m-%d"),
            "fetched": now.strftime("%Y-%m-%d %H:%M"),
            "tool": "tools/workshop_search.py",
            "terms": list(per_term),
            "source_url_pattern": {"browse": BROWSE, "item": ITEM},
            "details_ids": detail_ids,
            "corpus": {"path": "data/mod-inventory.json",
                       "records": len(records),
                       "workshop_items": len({str(r.get("workshop_id", "")) for r in records})},
            "per_term": per_term,
            "counts": counts,
            "notes": NOTES}


def recount_details(rows, counts):
    """Refresh the four details counters off the rows themselves, after a fill pass moved some."""
    counts["details_fetched"] = sum(1 for r in rows if r["error"] is None and r["size"])
    counts["detail_failures"] = sum(1 for r in rows
                                    if r["error"] and r["error"] != NOT_FETCHED)
    counts["details_not_fetched"] = sum(1 for r in rows if r["error"] == NOT_FETCHED)
    counts["details_incomplete"] = sum(1 for r in rows if not r["error"] and not r["size"])
    return counts


def fill(payload, detailer=details, sleep=time.sleep, detail_pause=DETAIL_PAUSE, now=None,
         log=lambda *a: None):
    """Second chance for the rows a rationed window lost, without re-sweeping.

    Re-fetches only rows whose `error` is a real failure -- never the not-attempted note, which
    is a decision rather than a fault. The row set, the terms and `meta.fetched` are left alone:
    this fills columns in the sweep that was captured, so the stamp on the rows stays true.
    """
    rows = payload["results"]
    todo = [r for r in rows if r["error"] and r["error"] != NOT_FETCHED]
    log(f"fill: {len(todo)} row(s) carry a details failure, {detail_pause}s apart")
    for i, row in enumerate(todo):
        if i:
            sleep(detail_pause)
        d = detailer(row["workshop_id"])
        row["size"], row["posted"], row["updated"] = d["size"], d["posted"], d["updated"]
        row["error"] = d["error"]
        log(f"  {row['workshop_id']}  " + (f"ERROR {d['error']}" if d["error"] else
                                           f"{d['size']}  posted {d['posted']}  "
                                           f"updated {d['updated']}"))
    recount_details(rows, payload["meta"]["counts"])
    payload["meta"]["details_filled"] = (now or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
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
                        r["size"] or "", r["posted"] or "", r["updated"] or "", r["error"] or ""])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--details", action="store_true",
                    help="second pass for size/posted/updated (see --details-ids: asking for "
                         "every id spends an item-page budget Steam will not grant)")
    ap.add_argument("--details-ids", default=None,
                    help="comma-separated workshop ids to spend the details budget on; the "
                         "token `installed` expands to every row that joined to the corpus. "
                         "Omit to try every id.")
    ap.add_argument("--details-pause", type=float, default=DETAIL_PAUSE,
                    help=f"seconds between item-page requests (default {DETAIL_PAUSE})")
    ap.add_argument("--fill", action="store_true",
                    help="re-fetch only the rows of the written dataset that carry a details "
                         "failure, and rewrite it; no browse pages, no new rows")
    ap.add_argument("--out-dir", default=OUT_DIR, help="where the json/csv pair is written")
    ap.add_argument("--corpus", default=CORPUS, help="data/mod-inventory.json to join against")
    args = ap.parse_args(argv)
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
        fill(payload, detail_pause=args.details_pause, log=print)
        write_json(jpath, payload["meta"], payload["results"])
        write_csv(cpath, payload["results"])
        c = payload["meta"]["counts"]
        print(f"\n{c['details_fetched']} read / {c['detail_failures']} still failing / "
              f"{c['details_not_fetched']} not attempted\n-> {jpath}\n-> {cpath}")
        return 0

    print(f"Workshop sweep: {len(TERMS)} term(s), Build 42 tag, browsesort=trend")
    rows, per_term, counts = sweep(with_details=args.details, detail_ids=detail_ids,
                                   corpus_path=args.corpus, detail_pause=args.details_pause,
                                   log=print)
    meta = build_meta(per_term, counts, corpus_path=args.corpus,
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
        print(f"  details: {counts['details_fetched']} read, "
              f"{counts['detail_failures']} failed, "
              f"{counts['details_not_fetched']} not attempted (item pages are rationed)")
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
