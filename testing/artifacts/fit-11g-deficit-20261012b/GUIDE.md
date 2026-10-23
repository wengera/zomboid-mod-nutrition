# `fit-11g-deficit-20261012b` reading guide

The reading of a compact fit, shared by the six Plan 11g fit folders, opens [`fit-11g-20261012/GUIDE.md`](../fit-11g-20261012/GUIDE.md).

**`fit-11g-deficit-20261012b/fit-compact.json`** and **`grid.json`** — `fit-compact.json` 2875 bytes, sha256 `517eecf9…3f81f8a6`; `grid.json` 277 bytes, `cad8cc89…b4bcf4fb`; the full `fit.json` 19003 bytes, sha256 `525cfedfc22ce42e…`, in `testing/runs/fit-11g-deficit-20261012b/`. **Plan 11g Task 7, the EX_BYPASS_HI plateau scan.** `tools/fit_deficit_drive.py` at `9b9db095`, the same kernel and `deficit_oracles.py`, a grid scan with no refinement (`spec.refine.rounds` 0) of 11 candidates: EX_BYPASS_HI at 0.3693, 0.372, 0.374759, 0.38, 0.39, 0.4, 0.41, 0.42, 0.43, 0.44 and 0.45, the other three at the main fit's chosen values (span 3970.55, floor 0, LO 0.282).

How to read it. `profile.deficit.EX_BYPASS_HI` is the scan itself (one candidate per value): every HI from 0.3693 to 0.44 reads the same loss, −0.4920501878561623, and 0.45 reads −0.4193135845485357; the binding margin across the plateau is Karl's DEF arm billed ClimbRope (`chosen.margins.karl_def` 0.4920501878561623). The chosen point, HI 0.44 (`chosen.params`; `chosen.phase` grid), is the tie rule's nearest to the old 0.575, not a better score: it shipped in `5af809b5` and was moved to mid-plateau 0.405 in `e3ad1197` (ruling T7-6), a value the grid brackets (0.40 and 0.41 read alike) but does not contain (the fix round's own three-point run is a scratch run, not committed). At 0.44 King reads −2.29177244433975 (`chosen.values.king`, margin 0.6944764982847728), against the main fit's −1.7222968333681328 at 0.374759.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `chosen.params.deficit.EX_BYPASS_HI`, as the mod's constant | 0.44 | Superseded by ruling T7-6's 0.405 (`e3ad1197`); 0.44 is the tie rule's pick on a flat plateau. |
| everything here, as a study reading | — | As the main fit's. |
