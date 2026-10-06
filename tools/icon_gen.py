#!/usr/bin/env python3
"""icon_gen.py -- the six symptom-class moodle icons of the nutrition mod (Plan 7 Task 9), deterministic.

    python tools/icon_gen.py --out <dir>      write energy.png, hydration.png, deficiency.png, excess.png,
                                              stimulant.png and sleep.png into <dir> (created if absent)
    python tools/icon_gen.py --check <dir>    compare the sha256 of each file in <dir> with the generator's
                                              output; exit 1 on a missing or different file, else 0

Each icon is 32 x 32 RGBA: a fixed class colour (energy amber, hydration blue, deficiency red, excess purple,
stimulant yellow, sleep indigo) and one glyph per class (a filled circle, a drop, a down-arrow, an up-arrow, a
bolt, a crescent) on a transparent ground, drawn by integer arithmetic on the doubled pixel centre (dx = 2x - 31,
dy = 2y - 31, so there is no float and no rounding). The PNG is written by hand: signature, IHDR, one IDAT of
filter-0 scanlines through zlib level 9, IEND, no ancillary chunk, so the bytes are the same on every run (the
sha256 pin holds for one zlib implementation; a different zlib may emit other bytes for the same pixels).

The mod loads them as media/ui/NutritionRevamp/<class>.png through setPicture and getTexture
(NR_Client_Moodles.lua). MoodleFramework's own icon lookup is media/ui/<size>/NR_<class>.png then
media/ui/NR_<class>.png (MF_ISMoodle.lua:432-437, :595, read in the x181 run); it is not used, because setPicture
overrides it, so no sized folder is shipped.
"""
import argparse
import hashlib
import os
import struct
import sys
import zlib

SIZE = 32
PALETTE = {
    "energy": (245, 166, 35),
    "hydration": (52, 152, 219),
    "deficiency": (214, 48, 49),
    "excess": (142, 68, 173),
    "stimulant": (241, 196, 15),
    "sleep": (63, 81, 181),
}
CLASSES = ("energy", "hydration", "deficiency", "excess", "stimulant", "sleep")
BOLT = ((18, 3), (8, 18), (15, 18), (12, 29), (24, 13), (17, 13), (21, 3))


def inside(poly, px, py):
    """Even-odd ray cast of the doubled point (px, py) against a polygon in pixel units, integers only."""
    n = len(poly)
    hit = False
    for i in range(n):
        x1, y1 = poly[i][0] * 2, poly[i][1] * 2
        x2, y2 = poly[(i + 1) % n][0] * 2, poly[(i + 1) % n][1] * 2
        if (y1 > py) != (y2 > py):
            # px < x1 + (py - y1) * (x2 - x1) / (y2 - y1), cross-multiplied with the sign of (y2 - y1)
            lhs = (px - x1) * (y2 - y1)
            rhs = (py - y1) * (x2 - x1)
            if (y2 - y1 > 0 and lhs < rhs) or (y2 - y1 < 0 and lhs > rhs):
                hit = not hit
    return hit


def circle(x, y):
    dx, dy = 2 * x - 31, 2 * y - 31
    return dx * dx + dy * dy <= 20 * 20


def drop(x, y):
    dx, dy = 2 * x - 31, 2 * y - 31
    if 4 <= y <= 18 and 12 * abs(dx) <= 16 * (y - 4):
        return True
    return dx * dx + (2 * y - 40) ** 2 <= 18 * 18


def down_arrow(x, y):
    dx = 2 * x - 31
    if 4 <= y <= 17 and abs(dx) <= 7:
        return True
    return 16 <= y <= 27 and 11 * abs(dx) <= 20 * (27 - y) + 10


def up_arrow(x, y):
    return down_arrow(x, SIZE - 1 - y)


def bolt(x, y):
    return inside(BOLT, 2 * x + 1, 2 * y + 1)


def crescent(x, y):
    dx, dy = 2 * x - 31, 2 * y - 31
    return dx * dx + dy * dy <= 22 * 22 and (dx - 9) ** 2 + (dy + 3) ** 2 > 18 * 18


GLYPH = {
    "energy": circle, "hydration": drop, "deficiency": down_arrow,
    "excess": up_arrow, "stimulant": bolt, "sleep": crescent,
}


def pixels(cls):
    r, g, b = PALETTE[cls]
    glyph = GLYPH[cls]
    rows = []
    for y in range(SIZE):
        row = bytearray([0])  # filter type 0 (None)
        for x in range(SIZE):
            row += bytes((r, g, b, 255)) if glyph(x, y) else bytes((0, 0, 0, 0))
        rows.append(bytes(row))
    return b"".join(rows)


def chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(cls):
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(pixels(cls), 9)) + chunk(b"IEND", b""))


def generate():
    return {cls + ".png": png(cls) for cls in CLASSES}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--out", metavar="DIR")
    g.add_argument("--check", metavar="DIR")
    a = ap.parse_args(argv)
    files = generate()
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        for name, data in files.items():
            with open(os.path.join(a.out, name), "wb") as f:
                f.write(data)
            print("%s  %s" % (hashlib.sha256(data).hexdigest(), name))
        return 0
    bad = 0
    for name, data in files.items():
        p = os.path.join(a.check, name)
        if not os.path.isfile(p):
            print("MISSING  " + p)
            bad += 1
            continue
        with open(p, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != hashlib.sha256(data).hexdigest():
                print("DIFFERS  " + p)
                bad += 1
    print("icon_gen --check: %d finding(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
