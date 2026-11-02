"""grades -- the session grades from Plan 26 on, one module per grade (`e14` carries `grade_e14`, `f7` carries
`grade_f7`). Each module is frozen per artifact as the passes appended to `gates_e` and `gates_f` were: once an
artifact carries a grade's output its module is never edited, and a later pass is a new module.

A new grade imports the previous grade function and the readers it needs, never copies them: the shared readers
(`_Lines`, `session_lines`, `_MapView`, `_outside`, `_d`, `_l`, `_n` and the rest) stay in `gates_e` and `gates_f`."""
