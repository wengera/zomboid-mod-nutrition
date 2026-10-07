# H6: the global store's size in the save's own format

Scenario: golden_trace.run, final records at minute 240; golden sha256 df7806d8974c614b1cc53f3280ca4af7367b4ed8ca8f61513e9e5f50daa9e8b3; key `NutritionRevamp.players`; synthetic usernames of 10 characters.

| record | full bytes | full leaves | full tables | inputsOnly bytes | inputsOnly leaves |
|---|---|---|---|---|---|
| g1 | 10849 | 624 | 60 | 8778 | 508 |
| g2 | 10849 | 624 | 60 | 8778 | 508 |
| g3 | 10684 | 619 | 56 | 8755 | 507 |
| g4 | 10707 | 620 | 56 | 8778 | 508 |
| g5 | 10875 | 625 | 60 | 8778 | 508 |
| g6 | 10883 | 625 | 60 | 8778 | 508 |

Mean record: full 10807.8 bytes (10821.8 with its store entry), inputsOnly 8774.2 (8788.2).

| records | full file bytes | full first-save restarts | inputsOnly file bytes | inputsOnly restarts |
|---|---|---|---|---|
| 1 | 10904 | 0 | 8833 | 0 |
| 6 | 64972 | 0 | 52770 | 0 |
| 60 | 649351 | 0 | 527331 | 0 |
| 100 | 1082082 | 1 | 878850 | 0 |
| 500 | 5411040 | 9 | 4394132 | 7 |
| 2000 | 21643790 | 40 | 17576382 | 32 |

Decision 3 size rule: 500 full records = 5411040 bytes against 1000000: exceeds.
