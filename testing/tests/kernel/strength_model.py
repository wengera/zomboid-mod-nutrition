"""The strength fit's daily-step model, tracked as a kernel-test oracle (Plan 13 Task 2).

Copied on 2026-10-14 from docs/superpowers/research/2026-10-14-strength-redesign/refit/model.py (tracked at
5987ac7a; sha256 d5cfd05e5427bd0940edcd1647ed4885485d1821f515518de0285e0a3082df24), byte for byte, then extended:
POINT_T (DEFAULT updated with compact_T.json's "chosen") is appended, and Body.day gains ruling 13-2's flag
`exact` (default off). With P['exact'] falsy the step is the fit's verbatim, so it reproduces compact_T.json. With it
on, the four forms the spec states and the fit did not run apply: detraining integrated exactly over the day; the
labile lean decaying on every day with no surplus left after growth; growth's energy charged at grow / ts (ruling
13-3); and the biology clock P['ts'] (default 1.0) scaling growth, regain, detraining and the peak decay and dividing
the grace days. Task 11c (Task 11 review I-2) adds a fifth: the regain integrated exactly over the day. Plan 16
Task 5 adds a sixth: the deficit arm reads no fat ceiling (Alpert's 69 kcal/kg/d stays in the fit's step only),
and its fix 1 a seventh: the fat draw past the 0.5 kg floor is paid by lean, energy for energy.
"""
# Proposed lean-mass Strength model with the two partitions (review of the 2026-10-14 spec).
# Daily step. Muscle lean F (the level), labile lean X (water, glycogen, organ: weight, not level), fat M.
# Pure Python, no packages.
import math

H = 1.70
H2 = H * H
RHO_L = 1816.0   # kcal/kg lean (K.partition.RHO_LEAN)
RHO_F = 9441.0   # kcal/kg fat (K.partition.RHO_FAT)
FAT_CEIL = 69.0  # kcal/kg fat/day (Alpert, S0056)


def F_of(L):
    return (18.0 + (L - 5.0) * 0.5) * H2


def L_of(F):
    return 5.0 + (F / H2 - 18.0) / 0.5


DEFAULT = dict(
    k=0.00874,        # per week, refitted for the hard anchor
    beta=2.5,         # threshold rise
    Sg0=1.0,          # sets/wk novice threshold
    Sref=12.0,        # G = 1 normaliser (Pelland mean)
    Smax=30.0,        # sets/wk cap at s = 0
    Smax1=30.0,       # sets/wk cap at s = 1 (linear in s; H.3/H.5/H.6 trained plateau)
    # protein gate (growth), g/kg/d knots
    fp_knots=((0.4, 0.0), (0.8, 0.5), (1.3, 0.92), (1.6, 1.0)),
    # energy gate
    E0=-500.0,        # kcal/d zero point at s = 0 (Murphy & Koehler)
    E0_drop=0.5,      # E0(s) = E0*(1 - E0_drop*s): -250 at s = 1 (Moro 2016 S3.1)
    fbal0=1.0,        # gate at balance, s = 0
    fbal_drop=0.5,    # f_bal(s) = fbal0*(1 - fbal_drop*s): 0.5 at s = 1
    surplus_full=0.10,  # fraction of TDEE where the gate reaches 1 at s = 0
    full_drop=0.5,    # E_full(s) = surplus_full*(1 - full_drop*s)*TDEE: +10 % untrained, +5 % at the cap (surplus harvest, refit 2)
    a_nov=1.4,        # novice high-protein deepening of E0 (Longland)
    trained_need=0.0,  # option B: gate at balance falls as fe_bal*(1-trained_need*s)
    # deficit partition
    forbes_c=10.4,    # Forbes: lean weight share = c/(c+M)
    wT=0.35,          # training protection weight (T = min(1, S/S_def))
    S_def=10.0,       # sets/wk that spare lean in a cut (H.47)
    wP=0.45,          # protein protection weight (ramp 0.8 -> 2.4 g/kg)
    pdef_lo=0.8, pdef_hi=2.4,
    prot_floor=0.15,
    # labile lean X (overfeeding lean, Bray)
    x_max_frac=0.05,  # cap as a fraction of F
    x_tau_d=28.0,     # decay toward 0 at balance or deficit-free days with no surplus
    # maintenance, detraining, regain
    m=1.0 / 3.0,
    grace_d=14,
    detrain_hl_wk=6.0,
    regain_hl_wk=6.0,
    peak_hl_yr=2.0,
    regain_gated=True,   # report form: regain carries f_p*f_e
    regain_sum=False,
    detrain_status=0.0,  # detraining half-life x (1 + detrain_status * s): S1.24 loss follows the build time course    # False: max(growth, regain) as the spec; True: growth + regain
)


def interp(knots, x):
    if x <= knots[0][0]:
        return knots[0][1]
    for i in range(1, len(knots)):
        x0, y0 = knots[i - 1]
        x1, y1 = knots[i]
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


def clip(x, a, b):
    return a if x < a else (b if x > b else x)


def fp(P, p):
    return interp(P['fp_knots'], p)


def fe(P, E, s, p, tdee):
    # status-dependent gate (advanced-recomp-report section 9): E0(s) = E0*(1 - E0_drop*s)*(protein term),
    # f_bal(s) = fbal0*(1 - fbal_drop*s), saturation at surplus_full*TDEE at every status
    E0 = P['E0'] * (1.0 - P['E0_drop'] * s) * (1.0 + P['a_nov'] * (1.0 - s) ** 2 * clip((p - 1.6) / 0.8, 0.0, 1.0))
    bal = P['fbal0'] * (1.0 - P['fbal_drop'] * s) * (1.0 - P['trained_need'] * s)
    if E <= E0:
        return 0.0
    if E < 0:
        return bal * (1.0 - E / E0)
    return bal + (1.0 - bal) * min(1.0, E / (P['surplus_full'] * (1.0 - P['full_drop'] * s) * tdee))


def Gsig(P, S, s):
    Sg = P['Sg0'] * math.exp(P['beta'] * s)
    Sx = P['Smax'] + (P['Smax1'] - P['Smax']) * s
    return max(0.0, math.sqrt(min(S, Sx)) - math.sqrt(Sg)) / (math.sqrt(P['Sref']) - math.sqrt(P['Sg0']))


class Body:
    def __init__(self, P, L0, cap, fat_kg, F0L=None, peakL=None):
        self.P = P
        self.F = F_of(L0)
        self.F0 = F_of(L0 if F0L is None else F0L)
        self.Fc = F_of(cap)
        self.Pk = self.F if peakL is None else F_of(peakL)
        self.M = fat_kg
        self.X = 0.0
        self.grace = 0

    def s(self):
        return clip((self.F - self.F0) / (self.Fc - self.F0), 0.0, 1.0)

    def W(self):
        return self.F + self.X + self.M

    def day(self, S, p, E, tdee=2600.0):
        """One closed day: S weekly hard sets (ring), p g/kg/d protein, E kcal/d balance."""
        P = self.P
        s = self.s()
        G = Gsig(P, S, s)
        gp = fp(P, p)
        ge = fe(P, E, s, p, tdee)
        grow = P['k'] * (self.Fc - self.F) * G * gp * ge / 7.0
        exact = bool(P.get('exact'))
        ts = 1.0
        if exact:
            # ruling 13-2: the biology clock P['ts'] scales growth and regain. Task 11c (Task 11 review I-2): the
            # growth arm keeps its Euler step, times ts; the regain is the day's whole regain integrated exactly,
            # (Pk - F) (1 - exp(-lr min(1, G) gate ts / 7)), so no clock or half-life carries F past Pk
            ts = P.get('ts', 1.0)
            grow = max(0.0, grow) * ts
            if self.F < self.Pk:
                lr = math.log(2) / P['regain_hl_wk']
                gate = gp * ge if P['regain_gated'] else 1.0
                rg = (self.Pk - self.F) * (1.0 - math.exp(-lr * min(1.0, G) * gate * ts / 7.0))
                grow = grow + rg if P['regain_sum'] else max(grow, rg)
        else:
            if self.F < self.Pk:
                lr = math.log(2) / P['regain_hl_wk']
                gate = gp * ge if P['regain_gated'] else 1.0
                rg = lr * (self.Pk - self.F) * min(1.0, G) * gate / 7.0
                grow = grow + rg if P['regain_sum'] else max(grow, rg)
            grow = max(0.0, grow)
        # maintenance and detraining
        Sm = P['m'] * P['Sg0'] * math.exp(P['beta'] * s)
        detr = 0.0
        if S < Sm:
            self.grace += 1
        else:
            self.grace = 0
        if exact:
            # ruling 13-2: the grace days divided by ts, the detraining integrated exactly over the day
            if self.grace > P['grace_d'] / ts and self.F > self.F0:
                lam = math.log(2) / (P['detrain_hl_wk'] * (1.0 + P['detrain_status'] * s))
                detr = (self.F - self.F0) * (1.0 - math.exp(-lam * ts * (1.0 - S / Sm) / 7.0))
        elif self.grace > P['grace_d'] and self.F > self.F0:
            lam = math.log(2) / (P['detrain_hl_wk'] * (1.0 + P['detrain_status'] * s))
            detr = lam * (self.F - self.F0) * (1.0 - S / Sm) / 7.0
        dF = grow - detr
        dX = 0.0
        dM = 0.0
        if E >= 0:
            # surplus: muscle growth paid first, the rest split labile lean / fat
            if exact:
                # ruling 13-3: growth's energy charged at grow / ts
                rest = E - grow / ts * RHO_L
            else:
                rest = E - grow * RHO_L
            if rest < 0:
                # growth capped by the surplus? the partition caps lean at the surplus; keep the
                # cap but fund the excess from fat as in the deficit arm (recomposition)
                dM += rest / RHO_F
                rest = 0.0
            share = P['forbes_c'] / (P['forbes_c'] + self.M)
            xroom = max(0.0, P['x_max_frac'] * self.F - self.X)
            xs = share * clip((p - 0.8) / 0.8, 0.0, 1.0) * (1.0 - min(1.0, S / P['S_def']))   # 0 at 0.8 g/kg, full at 1.6 (Bray 5 % vs 15 %)
            dWr = rest / (xs * RHO_L + (1 - xs) * RHO_F) if rest > 0 else 0.0
            dXg = min(xs * dWr, xroom)
            dX += dXg
            dM += (rest - dXg * RHO_L) / RHO_F
            if exact:
                # ruling 13-2: the labile lean decays on every day with no surplus left after growth (rest is 0
                # here exactly when E - grow / ts * RHO_L was <= 0; a negative rest was zeroed above)
                if rest <= 0:
                    dX -= self.X / P['x_tau_d']
            elif E == 0:
                dX -= self.X / P['x_tau_d']
        else:
            D = -E
            T = min(1.0, S / P['S_def'])
            gP = clip((p - P['pdef_lo']) / (P['pdef_hi'] - P['pdef_lo']), 0.0, 1.0)
            prot = clip(1.0 - P['wT'] * T - P['wP'] * gP, P['prot_floor'], 1.0)
            share = P['forbes_c'] / (P['forbes_c'] + self.M) * prot
            dW = D / (share * RHO_L + (1 - share) * RHO_F)
            leanLoss = share * dW
            fatLoss = (1 - share) * dW
            cap = FAT_CEIL * self.M / RHO_F
            # Plan 16 Task 5: the exact mode (the kernel's forms) drops the ceiling from the deficit arm, so the
            # Forbes share times the protection splits the whole deficit (S2278-S2283); the fit's step keeps it
            if fatLoss > cap and not exact:
                # the existing K.partition overflow: lean pays the overflow times the protection, fat pays the spared share beyond the ceiling
                over = (fatLoss - cap) * RHO_F
                fatLoss = cap + over * (1 - prot) / RHO_F
                leanLoss += over * prot / RHO_L
            if exact:
                # Plan 16 Task 5 fix 1: the fat draw (the deficit's and growth's recomposition, grow / ts) past the fat
                # floor 0.5 kg is paid by lean, energy for energy, so the floor drops no energy
                over = max(0.0, fatLoss + grow / ts * RHO_L / RHO_F - max(0.0, self.M - 0.5))
                fatLoss -= over
                leanLoss += over * RHO_F / RHO_L
            # labile lean pays first
            fromX = min(self.X, leanLoss)
            dX -= fromX
            dF -= (leanLoss - fromX)
            dM -= fatLoss
            if exact:
                # ruling 13-2: a deficit day decays the remaining labile store
                dX -= (self.X - fromX) / P['x_tau_d']
                # recomposition: growth funded from fat, charged at grow / ts (ruling 13-3)
                dM -= grow / ts * RHO_L / RHO_F
            else:
                # recomposition: growth funded from fat
                dM -= grow * RHO_L / RHO_F
        self.F = max(self.F + dF, 0.35 * self.F0)
        self.X = max(0.0, self.X + dX)
        self.M = max(0.5, self.M + dM)
        # peak
        self.Pk = max(self.Pk, self.F)
        dec = math.log(2) / (P['peak_hl_yr'] * 365.0)
        if exact:
            # ruling 13-2: the biology clock scales the peak decay
            self.Pk = self.F + (self.Pk - self.F) * math.exp(-dec * ts)
        else:
            self.Pk = self.F + (self.Pk - self.F) * math.exp(-dec)
        return self


def creation(P, L0=5.0, cap=16.5, bf=0.14):
    F = F_of(L0)
    M = F * bf / (1 - bf)
    return Body(P, L0, cap, M)


def k_for_anchor(P, years=5, S=20, target=15.0):
    """Bisect k so the average character reaches the target level at `years` on S sets, full gates."""
    lo, hi = 1e-4, 0.2
    for _ in range(40):
        k = 0.5 * (lo + hi)
        Q = dict(P, k=k)
        b = creation(Q)
        for _ in range(int(years * 365)):
            b.fast_grow(S)
        if L_of(b.F) < target:
            lo = k
        else:
            hi = k
    k = 0.5 * (lo + hi)
    if k > 0.19:
        return float('nan')   # the anchor is unreachable: the threshold meets the cap below level 15
    return k


def _fast_grow(self, S):
    """Full gates, growth only (the anchor's definition): fp=1, fe=1, no partition."""
    P = self.P
    s = self.s()
    G = Gsig(P, S, s)
    self.F += P['k'] * (self.Fc - self.F) * G / 7.0
    self.Pk = max(self.Pk, self.F)


Body.fast_grow = _fast_grow


# ---------------------------------------------------------------- point T (Plan 13 Task 2)
import json as _json
import os as _os

COMPACT_T = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))),
    "docs", "superpowers", "research", "2026-10-14-strength-redesign", "refit", "compact_T.json")


def _point_t():
    """DEFAULT updated with compact_T.json's "chosen"; fp_knots (not fitted) kept from DEFAULT, and the fit's own
    `infeasible` flag, which is no model parameter, left out."""
    with open(COMPACT_T, encoding="utf-8") as fh:
        chosen = _json.load(fh)["chosen"]
    P = dict(DEFAULT)
    P.update({k: v for k, v in chosen.items() if k != "infeasible"})
    return P


POINT_T = _point_t()
