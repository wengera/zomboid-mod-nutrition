# Nutrition core — weight, calories, macros

**Verified:** 42.20.4 jar, `zombie.characters.BodyDamage.Nutrition` (pzdis),
2026-09-04. Migrated from pz-b42 `findings/nutrition-weight.md`.

## Weight model (`Nutrition.updateWeight`)

```
gainThreshold = 1000 + (weight - 80) × 40        # w70: 600 · w80: 1000 · w90: 1400
    trait Weight Gain  (weight < 90): base 700
    trait Weight Loss  (weight > 70): base 1800
loseThreshold = min(0, (weight - 70) × 30)       # ≥70: any negative calories
                                                 # w60: needs < −300 to keep losing
if calories > gainThreshold:
    rate = 1.3e-5 /game-sec × min(1, calories/4000)     # ≈1.12 kg/day at 4000
    if carbs > 700 OR lipids > 700:   rate ×3           # ≈3.4 kg/day
    elif carbs > 400 OR lipids > 400: rate ×2
elif calories < loseThreshold:
    rate = 8.5e-6 × min(1, |calories|/2500)             # ≤ 0.73 kg/day
```

Weight bands (`applyTraitFromWeight`, re-checked every ~2000 updates):
Emaciated <50 · Very Underweight 50–65 · Underweight 65–75 · **normal 75–85** ·
Overweight 85–100 · Obese >100.

## Macro effects — the complete list (vanilla)

- **Calories**: the only driver of weight (above).
- **Carbs / lipids**: weight-gain *rate multipliers* only (thresholds above).
- **Proteins**: never touch weight. Sole verified effect —
  `IsoGameCharacter.getRecoveryMod` (endurance/muscle recovery): base 0.7→1.6
  by Fitness, ×trait mods, then **lipids < −1000 → ×0.5, < −1500 → ×0.2;
  proteins identically**. Deficit penalties only; surplus does nothing.
- Fitness/Strength XP gating (`canAddFitnessXp`) is weight-trait based
  (Emaciated/Obese/Very Underweight block at Fitness ≥6/≥9) — NOT protein.

**Design-relevant emptiness:** protein surplus, carb store as energy, and any
notion of diet *quality* are dead space in vanilla — prime territory for the
mod, and why parallel nutrient stats have no vanilla collision.

## Open questions for P1 (next passes)

- [ ] `updateCalories`: passive burn model — exertion, temperature, trait
      terms; how hunger maps to calorie intake per food.
- [ ] Where macro stores clamp (observed range ≈ −2200..3700? verify in code).
- [ ] `characterHaveWeightTrouble` exact composition.
- [ ] Nutritionist trait: display-only? confirm.
- [ ] Sandbox options touching nutrition (`SandboxOptions` fields).

## MP behavior

- Weight/nutrition update runs **client-side for the local player**
  (`updateWeight` guarded by `GameClient.client` checks; server skips setting
  weight for remote clients — verify exact ownership in P1).
- Nutrition values persist via character save; no per-tick server echo
  observed. TODO: confirm what (if anything) the server validates — matters
  for anti-cheat posture of modded nutrient stats.
