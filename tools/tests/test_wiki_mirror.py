import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import wiki_mirror

SAMPLE = "{{LangSwitch}}\n{{Page version|42.11.0}}\n'''Nutrition''' is a mechanic."

def test_render_has_header_and_fence():
    md = wiki_mirror.render("Nutrition", "https://pzwiki.net/wiki/Nutrition", SAMPLE, "2026-09-09")
    assert "**Wiki page version:** 42.11.0" in md
    assert "**License:** CC BY-NC-SA 3.0" in md
    assert "```wikitext" in md and SAMPLE in md

def test_slug():
    assert wiki_mirror.slug("Nutritional values") == "nutritional-values"

def test_mirror_writes_file(monkeypatch):
    monkeypatch.setattr(wiki_mirror, "fetch_raw", lambda page: SAMPLE)
    with tempfile.TemporaryDirectory() as d:
        p = wiki_mirror.mirror("Nutrition", d)
        assert p.endswith("nutrition.md") and os.path.exists(p)
