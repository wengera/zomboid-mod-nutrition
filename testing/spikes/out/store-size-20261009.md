# H6: the global store's size in the save's own format

Scenario: golden_trace.run, final records at minute 240; golden sha256 c53794a2cfe27b20f7d1f0390e20a7554a63adf40723b20fb6cf0f7076f66946; key `NutritionRevamp.players`; synthetic usernames of 10 characters.

| record | full bytes | full leaves | full tables | inputsOnly bytes | inputsOnly leaves |
|---|---|---|---|---|---|
| g1 | 13537 | 768 | 71 | 11442 | 651 |
| g2 | 13490 | 766 | 70 | 11395 | 649 |
| g3 | 13253 | 759 | 63 | 11300 | 646 |
| g4 | 13348 | 762 | 66 | 11395 | 649 |
| g5 | 13535 | 768 | 70 | 11414 | 650 |
| g6 | 13530 | 767 | 70 | 11401 | 649 |

Mean record: full 13448.8 bytes (13462.8 with its store entry), inputsOnly 11391.2 (11405.2).

| records | full file bytes | full first-save restarts | inputsOnly file bytes | inputsOnly restarts |
|---|---|---|---|---|
| 1 | 13592 | 0 | 11497 | 0 |
| 6 | 80818 | 0 | 68472 | 0 |
| 60 | 807811 | 0 | 684351 | 0 |
| 100 | 1346157 | 1 | 1140525 | 1 |
| 500 | 6731587 | 11 | 5702679 | 9 |
| 2000 | 26925837 | 50 | 22810429 | 42 |

Decision 3 size rule: 500 full records = 6731587 bytes against 1000000: exceeds.

Slot file (the store since Plan 11 Task 11): one JSON line per record, gen 1, lupa tostring.

| record | slot-file line bytes |
|---|---|
| g1 | 7675 |
| g2 | 7561 |
| g3 | 5973 |
| g4 | 7644 |
| g5 | 7765 |
| g6 | 6892 |

Mean slot-file line: 7251.7 bytes (range 5973 to 7765).
