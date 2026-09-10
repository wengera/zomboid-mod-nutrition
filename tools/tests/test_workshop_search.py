"""Tests for the Workshop nutrition sweep.

**Parse-only: nothing here touches the network.** Every fixture is the markup shape the live
pages served on 2026-09-10 (the browse page's obfuscated-class anchor/img pair, the item page's
server-rendered `detailsStatRight` block), trimmed to the bytes the regexes actually read;
`fetch` is exercised with a stubbed `subprocess.run` and the sweep with stub fetchers, so a
failing test means a parser or join regression, never a Steam outage.
"""
import json, os, sys, unittest.mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import workshop_search as ws

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      "data", "mod-inventory.json")

# Three consecutive results off the `nutrition` browse page, 2026-09-10 15:41. The class names
# are obfuscated and change per deploy -- RESULT_RX must not depend on them.
BROWSE_FRAGMENT = (
    '<div class="_7-YnTYBrWGM- aspectratio_square">'
    '<a href="https://steamcommunity.com/sharedfiles/filedetails/?id=3796753621" class="tK5agp5sRy8-">'
    '<img src="https://images.steamusercontent.com/ugc/124/E1BB/?ima=fit&amp;imw=288" '
    'alt="Nutrition Makes Sense Immersive Addon" loading="lazy" class=""/></a></div>'
    '<div class="_7-YnTYBrWGM- aspectratio_square">'
    '<a href="https://steamcommunity.com/sharedfiles/filedetails/?id=3796408146" class="tK5agp5sRy8-">'
    '<img src="https://images.steamusercontent.com/ugc/126/A2DF/?ima=fit&amp;imw=288" '
    'alt="SideWinder&#x27;s Easy Cooking" loading="lazy" class=""/></a></div>'
    '<div class="_7-YnTYBrWGM- aspectratio_square">'
    '<a href="https://steamcommunity.com/sharedfiles/filedetails/?id=3736275816" class="tK5agp5sRy8-">'
    '<img src="https://images.steamusercontent.com/ugc/127/9C11/?ima=fit&amp;imw=288" '
    'alt="ApocalipseBR - Nutrition Sync Fix" loading="lazy" class=""/></a></div>')

# A whole browse page carries the sort control whether or not anything matched -- that marker is
# how `search` tells a real browse page from whatever else answered 200.
BROWSE_PAGE = '<div class="Ktq6"><a href="?browsesort=trend">Most Popular</a></div>' + BROWSE_FRAGMENT
EMPTY_BROWSE_PAGE = ('<div class="Ktq6"><a href="?browsesort=trend">Most Popular</a></div>'
                     '<div>There are no items matching filters.</div>')

# What Steam actually served for 177 of 180 `--details` requests between 15:46 and 15:52 on
# 2026-09-10: a 200, a 310 KB body, and not one byte the item parser can use.
SSR_ITEM_PAGE = ('<!DOCTYPE html><html lang="en" class="responsive DesktopUI"><head>'
                 '<title>Steam Workshop</title></head><body><div class="Ktq6">Workshop</div>'
                 '</body></html>')

# Item page stats block. Two stats = never updated since posting (3774789651, Long Term
# Preservation); three = updated at least once (3736275816, Nutrition Sync Fix).
TWO_STAT_ITEM = (
    '<div class="workshopItemTitle">Long Term Preservation [42.20]</div>'
    '<div class="detailsStatsContainerLeft">'
    '<div class="detailsStatLeft">File Size </div><div class="detailsStatLeft">Posted </div></div>'
    '<div class="detailsStatsContainerRight">'
    '<div class="detailsStatRight">239.131 KB</div>'
    '<div class="detailsStatRight">Jul 30 @ 6:31pm</div></div>')
THREE_STAT_ITEM = (
    '<div class="workshopItemTitle">ApocalipseBR - Nutrition Sync Fix</div>'
    '<div class="detailsStatsContainerLeft">'
    '<div class="detailsStatLeft">File Size </div><div class="detailsStatLeft">Posted </div>'
    '<div class="detailsStatLeft">Updated </div></div>'
    '<div class="detailsStatsContainerRight">'
    '<div class="detailsStatRight">453.434 KB</div>'
    '<div class="detailsStatRight">May 31 @ 7:55am</div>'
    '<div class="detailsStatRight">May 31 @ 11:18am</div></div>')


def test_result_rx_reads_id_and_alt_title():
    """The only two things the browse page reliably ships: the item id in the href and the
    title in the thumbnail's `alt`. HTML entities come back unescaped."""
    assert ws.parse_results(BROWSE_FRAGMENT) == [
        ("3796753621", "Nutrition Makes Sense Immersive Addon"),
        ("3796408146", "SideWinder's Easy Cooking"),
        ("3736275816", "ApocalipseBR - Nutrition Sync Fix")]


def test_results_are_deduplicated_in_page_order():
    """Steam renders the same card twice in some layouts; the id keeps its first position."""
    assert ws.parse_results(BROWSE_FRAGMENT + BROWSE_FRAGMENT) == ws.parse_results(BROWSE_FRAGMENT)


def test_no_results_parses_to_empty_not_an_error():
    assert ws.parse_results("<div>No items matched your search.</div>") == []


def test_two_stats_means_never_updated():
    """`updated is None` is a fact about the item, not a parse failure."""
    d = ws.parse_details(TWO_STAT_ITEM)
    assert d == {"title": "Long Term Preservation [42.20]", "size": "239.131 KB",
                 "posted": "Jul 30 @ 6:31pm", "updated": None}


def test_three_stats_carries_the_update_date():
    d = ws.parse_details(THREE_STAT_ITEM)
    assert d == {"title": "ApocalipseBR - Nutrition Sync Fix", "size": "453.434 KB",
                 "posted": "May 31 @ 7:55am", "updated": "May 31 @ 11:18am"}


def test_join_marks_an_installed_id_with_its_mod_ids():
    """Synthetic corpus: the join is on `workshop_id`, and one item may hold several mods."""
    hits = {"3774789651": {"title": "Long Term Preservation [42.20]", "terms": ["nutrition"]},
            "3690404044": {"title": "Nutrition Makes Sense", "terms": ["nutrition", "diet"]}}
    rows = ws.join(hits, {"3774789651": ["SKITTLE_LongTermPreservation4220", "OtherMod"]})
    by_id = {r["workshop_id"]: r for r in rows}
    assert by_id["3774789651"]["installed"] is True
    assert by_id["3774789651"]["mod_ids"] == ["OtherMod", "SKITTLE_LongTermPreservation4220"]
    assert by_id["3774789651"]["grade"] == "C" and by_id["3774789651"]["unblock"] is None
    assert by_id["3690404044"]["installed"] is False
    assert by_id["3690404044"]["mod_ids"] == []
    assert by_id["3690404044"]["terms"] == ["nutrition", "diet"]


def test_not_installed_rows_are_graded_w_with_the_unblocking_action():
    """The hard constraint: a result nobody subscribed to cannot be linted, profiled, booted or
    measured here, so the row says exactly what would change that."""
    rows = ws.join({"3736275816": {"title": "ApocalipseBR - Nutrition Sync Fix",
                                   "terms": ["nutrition"]}}, {})
    assert rows[0]["grade"] == "W"
    assert rows[0]["unblock"] == ("subscribe to 3736275816 in Steam, let it download, "
                                  "re-run tools/mod_inventory.py")


def test_real_corpus_join_resolves_the_installed_preservation_mod():
    """The one installed mod that writes both nutrition signals. Its id moved in slice 08 task 1
    (folder `LongTermPreservation4220`, declared `SKITTLE_LongTermPreservation4220`), which is
    why the join key is the workshop id and the mod id is only carried."""
    corpus = ws.load_corpus(CORPUS)
    assert "3774789651" in corpus
    assert "SKITTLE_LongTermPreservation4220" in corpus["3774789651"]
    rows = ws.join({"3774789651": {"title": "Long Term Preservation [42.20]",
                                   "terms": ["nutrition"]}}, corpus)
    assert rows[0]["installed"] is True
    assert "SKITTLE_LongTermPreservation4220" in rows[0]["mod_ids"]


def test_corpus_index_keys_are_strings_and_cover_every_record():
    """230 records across 179 workshop items -- the index must not lose the second mod of an
    item that ships two."""
    with open(CORPUS, encoding="utf-8") as fh:
        records = json.load(fh)
    corpus = ws.load_corpus(CORPUS)
    assert all(isinstance(k, str) for k in corpus)
    assert sum(len(v) for v in corpus.values()) == len(records)


def test_fetch_records_a_curl_failure_instead_of_raising():
    """A failed page is a recorded row, never an exception: a sweep that loses one page still
    writes the other seven."""
    fake = unittest.mock.Mock(returncode=1, stdout="", stderr="curl: (6) Could not resolve host")
    with unittest.mock.patch.object(ws.subprocess, "run", return_value=fake) as run:
        body, err = ws.fetch("https://steamcommunity.com/workshop/browse/?appid=108600")
    assert body is None
    assert err == "curl rc=1: curl: (6) Could not resolve host"
    argv = run.call_args[0][0]
    assert "--compressed" in argv, "without --compressed curl returns gzip bytes and every regex misses"
    assert argv[argv.index("-A") + 1] == ws.UA


def test_fetch_returns_the_body_on_success():
    fake = unittest.mock.Mock(returncode=0, stdout=BROWSE_FRAGMENT, stderr="")
    with unittest.mock.patch.object(ws.subprocess, "run", return_value=fake):
        body, err = ws.fetch("https://steamcommunity.com/")
    assert err is None and body == BROWSE_FRAGMENT


def test_retry_runs_once_after_a_failure_then_gives_up():
    calls, slept = [], []
    def flaky(url):
        calls.append(url)
        return (None, "curl rc=28: timeout")
    with unittest.mock.patch.object(ws, "fetch", flaky):
        body, err = ws.fetch_once_retried("https://x/", pause=5.0, sleep=slept.append)
    assert body is None and len(calls) == 2 and slept == [5.0]
    assert err == "curl rc=28: timeout (retry: curl rc=28: timeout)"


def test_empty_body_counts_as_a_failure():
    """A 200 with no HTML parses to zero results, which would read as `this term matched
    nothing` -- so it is recorded as an error instead."""
    with unittest.mock.patch.object(ws, "fetch", lambda url: ("   ", None)):
        body, err = ws.fetch_once_retried("https://x/", pause=0, sleep=lambda s: None)
    assert body is None and err.startswith("empty response body")


def test_search_encodes_a_two_word_term_and_records_a_failure():
    seen = []
    def ok(url):
        seen.append(url)
        return BROWSE_PAGE, None
    results, err = ws.search("food overhaul", fetcher=ok)
    assert err is None and len(results) == 3
    assert "searchtext=food+overhaul" in seen[0] and "requiredtags%5B%5D=Build+42" in seen[0]

    results, err = ws.search("nutrition", fetcher=lambda url: (None, "curl rc=7: refused"))
    assert results == [] and err == "curl rc=7: refused"


def test_a_term_that_matches_nothing_is_zero_results_not_an_error():
    """`malnutrition` returned 2 on 2026-09-10; a term returning 0 is a real answer, and the
    sort control is what proves the page rendered at all."""
    results, err = ws.search("zzqqxx", fetcher=lambda url: (EMPTY_BROWSE_PAGE, None))
    assert results == [] and err is None


def test_details_records_a_failed_item_page_on_the_row():
    d = ws.details("3690404044", fetcher=lambda url: (None, "curl rc=28: timeout"))
    assert d == {"title": None, "size": None, "posted": None, "updated": None,
                 "error": "curl rc=28: timeout"}


def test_an_unreadable_item_template_is_an_error_not_a_row_of_nulls():
    """The 2026-09-10 15:46-15:52 regression, pinned. Steam answered 200 with a 310 KB page that
    has no `workshopItemTitle` and no `detailsStatRight`; recording that as an item with no
    stats is indistinguishable from a real item that ships none."""
    calls, slept = [], []
    def ssr(url):
        calls.append(url)
        return SSR_ITEM_PAGE, None
    d = ws.details("3690404044", fetcher=ssr, sleep=slept.append)
    assert d["error"] == ws.ITEM_TEMPLATE_ERR
    assert d["size"] is None and d["title"] is None
    assert len(calls) == 2 and slept == [ws.RETRY_PAUSE], "one retry, then recorded"
    row = ws.apply_details(ws.join({"3690404044": {"title": "x", "terms": ["nutrition"]}}, {})[0],
                           d)
    assert row["details_status"] == "failed" and row["error"] == ws.ITEM_TEMPLATE_ERR, (
        "a page that was asked for and could not be read is `failed`, never `not_requested`")


def test_half_an_item_template_is_not_a_page():
    """Both markers are required. A title block with no stats block would otherwise pass the
    check and hand back the three nulls the check exists to catch."""
    title_only = '<div class="workshopItemTitle">Long Term Preservation</div>'
    assert ws.usable_item_page(TWO_STAT_ITEM) is True
    assert ws.usable_item_page(title_only) is False
    assert ws.usable_item_page(SSR_ITEM_PAGE) is False


def test_a_browse_page_is_readable_from_its_results_when_the_sort_control_moves():
    """The sort control is the marker, but the anchor/img pair is what the parser actually reads:
    a deploy that renames the control must not turn 30 results into a template error."""
    assert ws.usable_browse_page(BROWSE_PAGE) is True
    assert ws.usable_browse_page(BROWSE_FRAGMENT) is True, "results are a page too"
    assert ws.usable_browse_page(SSR_ITEM_PAGE) is False


def test_an_unreadable_browse_template_is_an_error_not_zero_results():
    results, err = ws.search("nutrition", fetcher=lambda url: (SSR_ITEM_PAGE, None),
                             sleep=lambda s: None)
    assert results == [] and err == ws.BROWSE_TEMPLATE_ERR


def test_a_recovered_retry_is_used():
    """The retry is real: a template miss followed by a good page yields the good page."""
    bodies = iter([(SSR_ITEM_PAGE, None), (THREE_STAT_ITEM, None)])
    d = ws.details("3736275816", fetcher=lambda url: next(bodies), sleep=lambda s: None)
    assert d["error"] is None and d["size"] == "453.434 KB"


def test_sweep_counts_terms_results_and_the_join_without_network(tmp_path):
    """The whole run with stub fetchers: two terms sharing one id, one term failing, one
    installed hit. Counts are what the doc quotes, so they are asserted exactly. With no details
    pass every row is `not_requested` -- no item page was asked for, which is exactly what
    `details_not_fetched` counts."""
    pages = {"nutrition": ([("3774789651", "Long Term Preservation [42.20]"),
                            ("3690404044", "Nutrition Makes Sense")], None),
             "diet": ([("3690404044", "Nutrition Makes Sense")], None),
             "spoilage": ([], "curl rc=28: timeout")}
    corpus = tmp_path / "mod-inventory.json"
    corpus.write_text(json.dumps([{"workshop_id": "3774789651",
                                   "mod_id": "SKITTLE_LongTermPreservation4220"}]), "utf-8")

    rows, per_term, counts = ws.sweep(terms=["nutrition", "diet", "spoilage"],
                                      corpus_path=str(corpus), sleep=lambda s: None,
                                      searcher=lambda t: pages[t])
    assert counts == {"terms": 3, "results_total": 3, "term_failures": 1, "distinct_ids": 2,
                      "installed": 1, "not_installed": 1, "details_requested": 0,
                      "details_fetched": 0, "detail_failures": 0, "details_not_fetched": 2,
                      "details_incomplete": 0}
    assert per_term["spoilage"] == {"results": 0, "error": "curl rc=28: timeout"}
    by_id = {r["workshop_id"]: r for r in rows}
    assert by_id["3690404044"]["terms"] == ["nutrition", "diet"]
    assert by_id["3774789651"]["mod_ids"] == ["SKITTLE_LongTermPreservation4220"]
    assert all(r["details_status"] == "not_requested" and r["error"] is None for r in rows)


def test_sweep_details_pass_fills_rows_and_counts_a_failure(tmp_path):
    """One item read, one item unreadable. `details_incomplete` stays 0 because the unreadable
    one carries an error -- it is the count that would have caught the first run."""
    corpus = tmp_path / "mod-inventory.json"
    corpus.write_text("[]", "utf-8")
    detail = {"3690404044": {"title": "Nutrition Makes Sense", "size": "1.042 MB",
                             "posted": "Mar 22 @ 4:57pm", "updated": "Aug 18 @ 5:01pm",
                             "error": None},
              "3736275816": {"title": None, "size": None, "posted": None, "updated": None,
                             "error": ws.ITEM_TEMPLATE_ERR}}
    rows, _, counts = ws.sweep(
        terms=["nutrition"], with_details=True, corpus_path=str(corpus), sleep=lambda s: None,
        searcher=lambda t: ([("3690404044", "Nutrition Makes Sense"),
                             ("3736275816", "ApocalipseBR - Nutrition Sync Fix")], None),
        detailer=lambda wid: detail[wid])
    assert counts["details_fetched"] == 1 and counts["detail_failures"] == 1
    assert counts["details_incomplete"] == 0
    by_id = {r["workshop_id"]: r for r in rows}
    assert by_id["3690404044"]["updated"] == "Aug 18 @ 5:01pm"
    assert by_id["3690404044"]["details_status"] == "fetched"
    assert by_id["3736275816"]["error"] == ws.ITEM_TEMPLATE_ERR
    assert by_id["3736275816"]["details_status"] == "failed", (
        "an item page that was asked for and could not be read is a fault, not a decision")


def test_details_ids_asks_only_for_the_declared_subset(tmp_path):
    """An item page can answer 200 with a template the parser cannot read, so the details pass is
    a declared subset; every row outside it says `not_requested` -- not an empty value, and not
    an `error`, which is reserved for a fetch that was tried and failed."""
    corpus = tmp_path / "mod-inventory.json"
    corpus.write_text(json.dumps([{"workshop_id": "3774789651",
                                   "mod_id": "SKITTLE_LongTermPreservation4220"}]), "utf-8")
    asked = []
    def detailer(wid):
        asked.append(wid)
        return {"title": "x", "size": "1.0 MB", "posted": "Jan 1 @ 1:00am", "updated": None,
                "error": None}
    rows, _, counts = ws.sweep(
        terms=["nutrition"], with_details=True, detail_ids=["installed", "3736275816"],
        corpus_path=str(corpus), sleep=lambda s: None, detailer=detailer,
        searcher=lambda t: ([("3774789651", "Long Term Preservation [42.20]"),
                             ("3736275816", "ApocalipseBR - Nutrition Sync Fix"),
                             ("3690404044", "Nutrition Makes Sense")], None))
    assert sorted(asked) == ["3736275816", "3774789651"], "`installed` expanded to the corpus hit"
    assert counts["details_requested"] == 2 and counts["details_fetched"] == 2
    assert counts["details_not_fetched"] == 1 and counts["details_incomplete"] == 0
    by_id = {r["workshop_id"]: r for r in rows}
    assert by_id["3690404044"]["size"] is None
    assert by_id["3690404044"]["details_status"] == "not_requested"
    assert by_id["3690404044"]["error"] is None, "a row nobody asked for did not fail"
    assert by_id["3774789651"]["details_status"] == "fetched"
    assert by_id["3774789651"]["error"] is None and by_id["3774789651"]["size"] == "1.0 MB"


def test_details_ids_rejects_an_id_this_sweep_never_returned(tmp_path):
    """A typo would otherwise be counted in `details_requested`, fetched for nobody, and break
    `requested == fetched + failures` with no row recording it."""
    rows = ws.join({"3690404044": {"title": "Nutrition Makes Sense", "terms": ["nutrition"]}}, {})
    assert ws.select_detail_ids(rows, ["3690404044"]) == {"3690404044"}
    try:
        ws.select_detail_ids(rows, ["3690404044", "369040404"])
    except ValueError as exc:
        assert "'369040404'" in str(exc), "the rejected token is named"
    else:
        raise AssertionError("an unknown --details-ids token must raise")


def test_meta_records_which_rows_were_asked_for():
    assert ws.describe_detail_ids(False, None) == "none"
    assert ws.describe_detail_ids(True, None) == "all"
    assert ws.describe_detail_ids(True, ["installed", "3736275816"]) == ["installed", "3736275816"]


def test_details_incomplete_counts_a_silent_null_row(tmp_path):
    """The regression itself: a detailer that reports success and returns nothing must not pass
    unnoticed."""
    corpus = tmp_path / "mod-inventory.json"
    corpus.write_text("[]", "utf-8")
    _, _, counts = ws.sweep(
        terms=["nutrition"], with_details=True, corpus_path=str(corpus), sleep=lambda s: None,
        searcher=lambda t: ([("3690404044", "Nutrition Makes Sense")], None),
        detailer=lambda wid: {"title": None, "size": None, "posted": None, "updated": None,
                              "error": None})
    assert counts["details_incomplete"] == 1
    assert counts["details_fetched"] == 1, (
        "one definition: the row reported no error, so it is `fetched` -- and `details_incomplete`"
        " is the guard that says the read was empty anyway")


def test_csv_has_the_ten_columns_and_semicolon_lists(tmp_path):
    """`details_status` sits after `updated`, so the CSV says why a row has no stats without the
    JSON-only `grade`/`unblock` columns and without an `error` string on every quiet row."""
    rows = ws.join({"3690404044": {"title": "Nutrition Makes Sense",
                                   "terms": ["nutrition", "diet"]}}, {})
    path = tmp_path / "workshop-search.csv"
    ws.write_csv(str(path), rows)
    lines = path.read_text("utf-8").splitlines()
    assert lines[0] == ("workshop_id,title,terms,installed,mod_ids,size,posted,updated,"
                        "details_status,error")
    assert lines[1] == '3690404044,Nutrition Makes Sense,nutrition;diet,false,,,,,not_requested,'

    ws.apply_details(rows[0], {"title": "x", "size": "1.234 MB", "posted": "Apr 1 @ 1:00pm",
                               "updated": None, "error": None})
    ws.write_csv(str(path), rows)
    assert path.read_text("utf-8").splitlines()[1] == (
        '3690404044,Nutrition Makes Sense,nutrition;diet,false,,1.234 MB,Apr 1 @ 1:00pm,,'
        'fetched,')


def test_meta_carries_the_build_terms_url_patterns_and_a_fetch_stamp(tmp_path):
    """A count off this dataset is meaningless without the minute it was fetched: Steam is live
    and `browsesort=trend` reorders hourly."""
    import datetime
    meta = ws.build_meta({"nutrition": {"results": 30, "error": None}}, {"terms": 1},
                         {"1": ["A", "B"]},        # the index the join used, not a second read
                         now=datetime.datetime(2026, 9, 10, 15, 41))
    assert meta["build"] == "42.20.4 (b0bbce05d5)"
    assert meta["tool"] == "tools/workshop_search.py"
    assert meta["generated"] == "2026-09-10" and meta["fetched"] == "2026-09-10 15:41"
    assert meta["terms"] == ["nutrition"]
    assert "requiredtags%5B%5D=Build+42" in meta["source_url_pattern"]["browse"]
    assert meta["corpus"] == {"path": "data/mod-inventory.json", "records": 2,
                              "workshop_items": 1}
    assert meta["details_ids"] == "none"
    assert any("details_status" in n for n in meta["notes"]), "the three row states are a caveat"
    allowance = " ".join(meta["notes"] + [ws.__doc__, ws.NOT_FETCHED])
    assert "about 13" not in allowance and "~13" not in allowance and "13 item" not in allowance, (
        "the per-window figure was never measured: the record is dated observations, not a rule")
    assert "15:45" in allowance and "15:58" in allowance and "16:25" in allowance


def fill_payload():
    """Three rows of a captured sweep: two that were asked for and failed, one never asked for."""
    return {"meta": {"fetched": "2026-09-10 16:25",
                     "counts": {"details_requested": 2, "details_fetched": 0,
                                "detail_failures": 2, "details_not_fetched": 1,
                                "details_incomplete": 0}},
            "results": [
                {"workshop_id": "3078272807", "size": None, "posted": None, "updated": None,
                 "details_status": "failed", "error": ws.ITEM_TEMPLATE_ERR},
                {"workshop_id": "2932547723", "size": None, "posted": None, "updated": None,
                 "details_status": "failed", "error": "curl rc=28: timeout"},
                {"workshop_id": "3690404044", "size": None, "posted": None, "updated": None,
                 "details_status": "not_requested", "error": None}]}


def stub_detailer(asked, fails=("2932547723",)):
    def detailer(wid):
        asked.append(wid)
        if wid in fails:
            return {"title": None, "size": None, "posted": None, "updated": None,
                    "error": ws.ITEM_TEMPLATE_ERR}
        return {"title": "Nutrition Tweaker Enhanced", "size": "503.836 KB",
                "posted": "Nov 10, 2023 @ 2:19am", "updated": "Jul 22, 2025 @ 1:35pm",
                "error": None}
    return detailer


def test_fill_retries_only_real_failures_and_leaves_the_sweep_stamp_alone():
    """A lost window costs rows; `--fill` recovers them without re-sweeping, so the row set and
    `meta.fetched` still describe the moment the browse pages were read. A row that was never
    asked for is a decision, not a fault, and a bare `--fill` leaves it alone."""
    import datetime
    asked = []
    out = ws.fill(fill_payload(), detailer=stub_detailer(asked), sleep=lambda s: None,
                  now=datetime.datetime(2026, 9, 10, 16, 40))
    assert asked == ["3078272807", "2932547723"], "the not-requested row is not re-asked"
    assert out["meta"]["fetched"] == "2026-09-10 16:25", "the sweep stamp is not overwritten"
    assert out["meta"]["fill"] == [{"at": "2026-09-10 16:40",
                                    "ids": ["3078272807", "2932547723"],
                                    "fetched": 1, "failed": 1}]
    assert out["meta"]["counts"] == {"details_requested": 2, "details_fetched": 1,
                                     "detail_failures": 1, "details_not_fetched": 1,
                                     "details_incomplete": 0}
    assert out["results"][0]["size"] == "503.836 KB"
    assert out["results"][0]["details_status"] == "fetched"
    assert out["results"][2]["details_status"] == "not_requested"


def test_fill_tops_up_named_not_requested_rows_only_when_asked():
    """The capture is extensible: a details pass that named nine ids can be topped up later
    without a re-sweep, which would change the trend-sorted row set. The top-up is opt-in and
    joins `details_requested`, so `requested == fetched + failures` still holds."""
    import datetime
    asked = []
    out = ws.fill(fill_payload(), detailer=stub_detailer(asked), sleep=lambda s: None,
                  include_not_requested=True, fill_ids=["3690404044"],
                  now=datetime.datetime(2026, 9, 10, 16, 45))
    assert asked == ["3078272807", "2932547723", "3690404044"], "dataset order, failures included"
    c = out["meta"]["counts"]
    assert c["details_requested"] == 3 and c["details_fetched"] == 2 and c["detail_failures"] == 1
    assert c["details_not_fetched"] == 0
    assert out["results"][2]["details_status"] == "fetched"
    assert out["results"][2]["size"] == "503.836 KB"
    assert out["meta"]["fill"][-1] == {"at": "2026-09-10 16:45",
                                       "ids": ["3078272807", "2932547723", "3690404044"],
                                       "fetched": 2, "failed": 1}


def test_fill_ids_takes_a_count_or_a_list_and_rejects_an_unknown_id():
    """`--fill-ids 6` is the first six not_requested rows in dataset order; `--fill-ids <id>,<id>`
    names them. A workshop id is 9-10 digits, so a bare number under seven is a count."""
    assert ws.parse_fill_ids(None) is None
    assert ws.parse_fill_ids("6") == 6
    assert ws.parse_fill_ids("3690404044") == ["3690404044"]
    assert ws.parse_fill_ids("3690404044, 3078272807") == ["3690404044", "3078272807"]

    rows = fill_payload()["results"]
    rows[0]["details_status"] = rows[1]["details_status"] = "not_requested"
    rows[0]["error"] = rows[1]["error"] = None
    assert [r["workshop_id"] for r in ws.select_fill_rows(rows, True, 2)] == ["3078272807",
                                                                              "2932547723"]
    assert ws.select_fill_rows(rows, False) == [], "without the flag a fill repairs faults only"
    try:
        ws.select_fill_rows(rows, True, ["9999999999"])
    except ValueError as exc:
        assert "9999999999" in str(exc)
    else:
        raise AssertionError("an id naming no not_requested row must raise")


def test_terms_are_the_eight_the_slice_is_written_against():
    assert ws.TERMS == ["nutrition", "vitamin", "malnutrition", "diet", "hydration",
                        "food overhaul", "cooking overhaul", "spoilage"]
