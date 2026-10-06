"""Download the four FoodData Central source files into a gitignored scratch dir.

    python tools/fdc_fetch.py [--dir tools/.fdc] [--verify]

Stdlib only. Writes <dir>/manifest.json (name, url, filename, bytes, sha256, fetched), skips a
file whose sha256 already matches the manifest, and downloads to <name>.part then renames. A 404
is never guessed around: the run fails naming the URL.
"""
import argparse, copy, datetime, hashlib, json, os, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, ".fdc")
# a long Chrome UA gets a 202 empty challenge from figshare; the short token gets the file
UA = "Mozilla/5.0"
CHUNK = 1 << 20

SOURCES = [
    {"name": "FoodData Central SR Legacy",
     "url": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
     "filename": "FoodData_Central_sr_legacy_food_csv_2018-04.zip",
     "release": "2018-04", "licence": "CC0-1.0",
     "citation": "U.S. Department of Agriculture, Agricultural Research Service. "
                 "FoodData Central, SR Legacy, April 2018. fdc.nal.usda.gov"},
    {"name": "FoodData Central Foundation Foods",
     "url": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip",
     "filename": "FoodData_Central_foundation_food_csv_2026-04-30.zip",
     "release": "2026-04-30", "licence": "CC0-1.0",
     "citation": "U.S. Department of Agriculture, Agricultural Research Service. "
                 "FoodData Central, Foundation Foods, 2026-04-30. fdc.nal.usda.gov"},
    {"name": "USDA Table of Nutrient Retention Factors R6",
     "url": "https://ndownloader.figshare.com/files/44488754",
     "filename": "NutrientRetention.csv",
     "release": "2007", "licence": "CC0-1.0",
     "citation": "USDA Table of Nutrient Retention Factors, Release 6 (2007), "
                 "NutrientRetention.csv, figshare file 44488754"},
    {"name": "USDA/FDA/ODS-NIH Iodine Database",
     "url": "https://www.ars.usda.gov/ARSUserFiles/80400535/Data/Iodine/IODINE_DATABASE_RELEASE_4_PER_100G.pdf",
     "filename": "IODINE_DATABASE_RELEASE_4_PER_100G.pdf",
     "release": "4.0 (2024-10)", "licence": "public-domain-US",
     "citation": "USDA, FDA and NIH ODS Iodine Database, Release 4.0 (2024-10), "
                 "per 100 g table. ars.usda.gov"},
]


def sources():
    """A deep copy of SOURCES (the pipeline copies it into meta.sources and adds sha256/bytes)."""
    return copy.deepcopy(SOURCES)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def download(url, dest):
    """Stream url to dest.part in 1 MiB chunks, rename to dest; return (bytes, sha256)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    part = dest + ".part"
    h = hashlib.sha256()
    n = 0
    try:
        with urllib.request.urlopen(req) as resp, open(part, "wb") as out:
            while True:
                b = resp.read(CHUNK)
                if not b:
                    break
                out.write(b)
                h.update(b)
                n += len(b)
        if n == 0:
            raise urllib.error.URLError("empty response body")
        os.replace(part, dest)
    except BaseException:
        if os.path.exists(part):
            os.remove(part)
        raise
    return n, h.hexdigest()


def load_manifest(d):
    p = os.path.join(d, "manifest.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_manifest(d, rows):
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, indent=1, sort_keys=True)
        f.write("\n")


def verify(d):
    bad = 0
    for row in load_manifest(d):
        path = os.path.join(d, row["filename"])
        if not os.path.exists(path):
            print("MISSING  %s" % row["name"])
            continue
        if sha256_file(path) != row["sha256"]:
            print("MISMATCH %s" % row["name"])
            bad += 1
        else:
            print("ok       %s" % row["name"])
    return 1 if bad else 0


def fetch(d):
    os.makedirs(d, exist_ok=True)
    old = {r["url"]: r for r in load_manifest(d)}
    rows, rc = [], 0
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    for src in SOURCES:
        dest = os.path.join(d, src["filename"])
        prev = old.get(src["url"])
        if prev and os.path.exists(dest) and sha256_file(dest) == prev["sha256"]:
            print("skip     %s (sha256 matches)" % src["name"])
            rows.append(prev)
            continue
        try:
            n, digest = download(src["url"], dest)
        except urllib.error.HTTPError as e:
            print("FAIL     %s: HTTP %s for %s" % (src["name"], e.code, src["url"]), file=sys.stderr)
            rc = 1
            continue
        except urllib.error.URLError as e:
            print("FAIL     %s: %s for %s" % (src["name"], e.reason, src["url"]), file=sys.stderr)
            rc = 1
            continue
        print("fetched  %s  %d B  %s" % (src["name"], n, digest))
        rows.append({"name": src["name"], "url": src["url"], "filename": src["filename"],
                     "bytes": n, "sha256": digest, "fetched": today})
    save_manifest(d, rows)
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch the FoodData Central pipeline sources")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--verify", action="store_true", help="re-hash every file against the manifest")
    a = ap.parse_args(argv)
    return verify(a.dir) if a.verify else fetch(a.dir)


if __name__ == "__main__":
    sys.exit(main())
