"""The server's vanilla-noise baseline (testing/pzt/server.py BASELINE_NOISE): a line it matches is not
counted as a server error, so it does not fail a run. Pure Python: no game."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pzt import server

# The one line both 42.21.0 provisions logged on 2026-10-08 (prov-20261008-073315, prov-20261008-073547),
# with only PZTestKit loaded: vanilla IsoMetaGrid refusing an empty-named Nav zone from the map data.
NAV_ZONE = ('LOG  : General      f:0 st:1,801,979,961> 111ERROR: not adding suspicious zone "" "Nav" '
            '8343,12316,0 2244x18')


def noise(line):
    return any(p.search(line) for p in server.BASELINE_NOISE)


def test_the_42_21_nav_zone_line_is_baseline_noise():
    assert server.ERROR_RX.search(NAV_ZONE)
    assert noise(NAV_ZONE)


def test_a_named_zone_or_another_error_is_not_noise():
    assert not noise(NAV_ZONE.replace('zone "" "Nav"', 'zone "MyZone" "Nav"'))
    assert not noise("LOG  : General      f:0> ERROR: something else entirely")
