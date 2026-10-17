"""x45i_lib -- the session engine of x452b (Plan 15 Task 14b): x452's three-meal day re-run on the mod tree that slows the
stomach's liquid lane only by drink-borne kcal and carries the hunger curve's re-fit (fit-hunger-curve-20261017c), so
the hunger lines x452 proved until that change have a live proof on this build again.

x45g_lib.py is frozen with x452-x457, so this lib imports it unchanged and only:
- adds x452b to the session table and maps it onto x452's phases, ring paths and grades (Sess keeps the frozen key
  "x452" inside, so every phase and grade runs exactly as x452's; the session key, the run prefix, the driver and the
  artifact are x452b's);
- names x452b's cadence bands, CAD_P_TARGETS_B and CAD_H_TARGET_B, read off the HEAD replay of exactly x452's schedule
  after the re-fit (`python testing/experiments/x45g_prerun.py x452` on 390636fe; PRERUN_B below, the whole reading);
- pins the staged copy to STAGED_FROM_B (390636fe, mod/'s last commit), checked by the frozen staged gate with that
  commit, and adds three pre-boot checks: the bands named, the bands the ones installed, and mod/'s last commit the
  pinned one.
Its main installs these into the frozen module in the driver's process only (x45h_lib's precedent, x453b): nothing is
patched at import, so the frozen tests and the other drivers see x45g_lib as it was.

THE SESSION (x452b, profile x45g-mod, the staged copy release/plan15-x45g re-staged from STAGED_FROM_B before the boot:
`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan15-x45g`): x452's S, H, W, F, X, C, R, T
(x45g_lib's docstring): lunch at the next 12:30, dinner 6 h later, breakfast 13 h after that, each a can of bolognese and
a banana eaten at speed 1 with no foodtimer.set, 0.5 L of water 2.5 h after each meal through x44's drink route.

THE GRADES are x452's (x45g_lib.Sess.grade_x452), against this lib's bands.

FROZEN WITH ITS FIRST RUN: once x452b has run, this file is never edited (CLAUDE.md s5).
"""
import functools
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x45g_lib as G                                                          # noqa: E402

LIB_FILE = "x45i_lib.py"
KEY_B = "x452b"
BASE_KEY = "x452"
SESSIONS = {KEY_B: {"driver": "x452b_day.py", "artifact": "day.json"}}
STAGED_FROM_B = "390636fe"                # mod/'s last commit: the liquid lane (8a34a7de) and the curve's re-fit
# The HEAD replay of x452's schedule on 390636fe (x45g_prerun.py x452; G.EAT_CAN_GM and G.EAT_BAN_GM after each planned
# minute, each return from the banana's minute, 0.5 L of Water 150 minutes after the planned minute): x452's were
# lunch 3.533, dinner 3.583, breakfast 4.033 and Hungry 9.550 on a97fec05
CAD_P_TARGETS_B = {"lunch": 3.483, "dinner": 3.533, "breakfast": 4.083}
CAD_H_TARGET_B = 9.550
PRERUN_B = {"max_dehydPct": 1.452, "dehydrated_rows": 0, "max_THIRST": 0.2667, "max_stomach_g": 790, "max_overfull": 1,
            "well_fed_h": 0.367, "eat0_max": 0}
CONSTANTS = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, (int, float, str))}

_FROZEN_PREBOOT = G.preboot
_FROZEN_STAGED_GATE = G.staged_gate


class Sess(G.Sess):
    """x452b on x45g_lib.Sess: x452's phases and grades under the frozen key, the session recorded as x452b."""

    def __init__(self, xs, key, run_dir=None):
        super().__init__(xs, BASE_KEY if key in SESSIONS else key, run_dir=run_dir)
        if key in SESSIONS:
            self.spec = SESSIONS[key]
            self.out["session_key_b"] = key
        self.out["constants_x45i"] = dict(CONSTANTS)
        self.out["prerun_x45i"] = dict(PRERUN_B)
        self.out["lib_x45i"] = LIB_FILE


def mod_head(repo=G.REPO):
    """mod/'s last commit, short; None when git cannot answer."""
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%h", "--", G.MOD_DIR], cwd=repo, capture_output=True,
                           text=True)
    except OSError:
        return None
    return p.stdout.strip() or None


def preboot(key, profile_name, prefix, driver_file, repo=G.REPO):
    """The frozen pre-boot checks, and for x452b the bands named, the bands installed and the pinned commit mod/'s last."""
    c, ok = _FROZEN_PREBOOT(key, profile_name, prefix, driver_file, repo=repo)
    if key in SESSIONS:
        head = mod_head(repo)
        c["cadence_bands_named"] = G.predictions_named()
        c["bands_installed"] = G.CAD_P_TARGETS == CAD_P_TARGETS_B and G.CAD_H_TARGET == CAD_H_TARGET_B
        c["staged_from_is_mod_head"] = head is not None and (head.startswith(STAGED_FROM_B) or
                                                             STAGED_FROM_B.startswith(head))
        ok = ok and c["cadence_bands_named"] is True and c["bands_installed"] is True and \
            c["staged_from_is_mod_head"] is True
    return c, ok


def install(setattr_=setattr, setitem=None):
    """Put x452b into the frozen module: the session table, the session class, the lib name, the bands, the pinned
    commit, its staged gate and the pre-boot checks. `setattr_` and `setitem` let a test install through monkeypatch."""
    if setitem is None:
        G.SESSIONS.update(SESSIONS)
    else:
        for k, v in SESSIONS.items():
            setitem(G.SESSIONS, k, v)
    setattr_(G, "Sess", Sess)
    setattr_(G, "LIB_FILE", LIB_FILE)
    setattr_(G, "CAD_P_TARGETS", dict(CAD_P_TARGETS_B))
    setattr_(G, "CAD_H_TARGET", CAD_H_TARGET_B)
    setattr_(G, "STAGED_FROM", STAGED_FROM_B)
    setattr_(G, "staged_gate", functools.partial(_FROZEN_STAGED_GATE, commit=STAGED_FROM_B))
    setattr_(G, "preboot", preboot)


def main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file):
    install()                                                                  # this process only: preboot and main
    return G.main(key, prefix, profile_name, artifact, session_text, pred, budget_s, driver_file)
