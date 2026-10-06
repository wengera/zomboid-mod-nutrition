"""Tests for tools/fdc_fetch.py. urlopen is mocked; no network."""
import hashlib, io, json, os, sys, tempfile, unittest
import urllib.error
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fdc_fetch

BODY = b"tiny fdc payload" * 10


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def fake_urlopen(req, *a, **k):
    return FakeResponse(BODY)


class FetchTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def test_sources_four_with_licence(self):
        s = fdc_fetch.sources()
        self.assertEqual(len(s), 4)
        for row in s:
            for key in ("name", "url", "filename", "release", "licence", "citation"):
                self.assertTrue(row[key], key)
        self.assertEqual(s[0]["licence"], "CC0-1.0")
        self.assertEqual(s[3]["licence"], "public-domain-US")
        self.assertIn("NutrientRetention.csv", [r["filename"] for r in s])
        s[0]["name"] = "changed"
        self.assertNotEqual(fdc_fetch.sources()[0]["name"], "changed")

    def test_manifest_row_and_part_rename(self):
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            rc = fdc_fetch.main(["--dir", self.dir])
        self.assertEqual(rc, 0)
        with open(os.path.join(self.dir, "manifest.json")) as f:
            man = json.load(f)
        self.assertEqual(len(man), 4)
        row = man[0]
        self.assertEqual(row["sha256"], hashlib.sha256(BODY).hexdigest())
        self.assertEqual(row["bytes"], len(BODY))
        for key in ("name", "url", "bytes", "sha256", "fetched"):
            self.assertIn(key, row)
        names = os.listdir(self.dir)
        self.assertFalse([n for n in names if n.endswith(".part")])
        for src in fdc_fetch.sources():
            self.assertIn(src["filename"], names)

    def test_skip_on_matching_hash(self):
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            fdc_fetch.main(["--dir", self.dir])
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen) as m:
            rc = fdc_fetch.main(["--dir", self.dir])
        self.assertEqual(rc, 0)
        self.assertEqual(m.call_count, 0)

    def test_verify(self):
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            fdc_fetch.main(["--dir", self.dir])
        self.assertEqual(fdc_fetch.main(["--dir", self.dir, "--verify"]), 0)
        with open(os.path.join(self.dir, fdc_fetch.sources()[1]["filename"]), "ab") as f:
            f.write(b"x")
        self.assertEqual(fdc_fetch.main(["--dir", self.dir, "--verify"]), 1)

    def test_404_fails_with_url(self):
        def boom(req, *a, **k):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        with mock.patch("urllib.request.urlopen", side_effect=boom):
            rc = fdc_fetch.main(["--dir", self.dir])
        self.assertEqual(rc, 1)
        self.assertFalse([n for n in os.listdir(self.dir) if n.endswith(".part")])

    def test_empty_body_fails(self):
        with mock.patch("urllib.request.urlopen", side_effect=lambda *a, **k: FakeResponse(b"")):
            rc = fdc_fetch.main(["--dir", self.dir])
        self.assertEqual(rc, 1)
        self.assertEqual([n for n in os.listdir(self.dir) if n != "manifest.json"], [])


if __name__ == "__main__":
    unittest.main()
