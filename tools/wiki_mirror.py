#!/usr/bin/env python3
"""Mirror PZwiki pages as raw wikitext with provenance (method rule 3 in STRATEGY.md)."""
import datetime, os, re, subprocess, sys

RAW = "https://pzwiki.net/w/index.php?title={page}&action=raw"
VIEW = "https://pzwiki.net/wiki/{page}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "references", "wiki-mirrors")

def slug(page):
    return re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")

def fetch_raw(page):
    url = RAW.format(page=page.replace(" ", "_"))
    r = subprocess.run(["curl", "-sS", "-A", UA, "--max-time", "30", url], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"fetch failed for {page}: {r.stderr.strip()[:200]}")
    return r.stdout

def page_version(wikitext):
    m = re.search(r"\{\{Page version\|([^}|]+)", wikitext)
    return m.group(1).strip() if m else "unstamped"

def render(page, url, wikitext, date):
    return (f"# Wiki mirror — {page}\n\n**Source:** {url}\n**Fetched:** {date}\n"
            f"**Wiki page version:** {page_version(wikitext)}\n"
            f"**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors\n\n"
            f"## Digest\n\n_digest pending_\n\n## Wikitext\n\n```wikitext\n{wikitext.rstrip()}\n```\n")

def mirror(page, out_dir=OUT):
    text = fetch_raw(page)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug(page) + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(page, VIEW.format(page=page.replace(" ", "_")), text, datetime.date.today().isoformat()))
    return path

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(mirror(p))
