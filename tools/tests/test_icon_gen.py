"""icon_gen.py (Plan 7 Task 9; Plan 11c Task 7 adds overfull): the seven class icons are valid, deterministic and
match the committed files."""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import icon_gen

REPO = os.path.dirname(os.path.dirname(HERE))
COMMITTED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "ui", "NutritionRevamp")
CLI = os.path.join(HERE, "..", "icon_gen.py")


class IconGenTests(unittest.TestCase):
    def test_signature_and_dimensions(self):
        files = icon_gen.generate()
        self.assertEqual(sorted(files), sorted(c + ".png" for c in icon_gen.CLASSES))
        for name, data in files.items():
            self.assertEqual(data[:8], bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), name)
            self.assertEqual(data[12:16], b"IHDR", name)
            self.assertEqual(struct.unpack(">II", data[16:24]), (32, 32), name)
            self.assertEqual(data[24:29], bytes((8, 6, 0, 0, 0)), name)

    def test_no_ancillary_chunks(self):
        for name, data in icon_gen.generate().items():
            tags, i = [], 8
            while i < len(data):
                n = struct.unpack(">I", data[i:i + 4])[0]
                tags.append(data[i + 4:i + 8])
                i += 12 + n
            self.assertEqual(tags, [b"IHDR", b"IDAT", b"IEND"], name)

    def test_two_generations_identical(self):
        self.assertEqual(icon_gen.generate(), icon_gen.generate())

    def test_glyphs_distinct(self):
        seen = set(hashlib.sha256(d).hexdigest() for d in icon_gen.generate().values())
        self.assertEqual(len(seen), 7)
        self.assertEqual(icon_gen.CLASSES[-1], "overfull")

    def test_committed_files_match(self):
        """The committed PNGs carry the generator's pixels: the IHDR and the inflated IDAT are compared, not the
        compressed bytes, because another zlib build can emit a different stream for the same pixels (the
        byte-exact pin stays on the --check CLI for the maintainer's machine)."""
        for cls in icon_gen.CLASSES:
            with open(os.path.join(COMMITTED, cls + ".png"), "rb") as f:
                data = f.read()
            self.assertEqual(data[:8], bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), cls)
            pos, idat = 8, b""
            while pos < len(data):
                (length,) = struct.unpack(">I", data[pos:pos + 4])
                tag = data[pos + 4:pos + 8]
                body = data[pos + 8:pos + 8 + length]
                if tag == b"IHDR":
                    self.assertEqual(body, struct.pack(">IIBBBBB", icon_gen.SIZE, icon_gen.SIZE, 8, 6, 0, 0, 0), cls)
                elif tag == b"IDAT":
                    idat += body
                pos += 12 + length
            self.assertEqual(zlib.decompress(idat), icon_gen.pixels(cls), cls)

    def test_cli_out_and_check(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, CLI, "--out", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run([sys.executable, CLI, "--check", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)
            with open(os.path.join(d, "sleep.png"), "ab") as f:
                f.write(b"x")
            r = subprocess.run([sys.executable, CLI, "--check", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            os.remove(os.path.join(d, "energy.png"))
            r = subprocess.run([sys.executable, CLI, "--check", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("MISSING", r.stdout)


if __name__ == "__main__":
    unittest.main()
