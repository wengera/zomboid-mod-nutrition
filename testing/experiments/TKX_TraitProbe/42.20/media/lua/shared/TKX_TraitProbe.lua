-- TKX_TraitProbe -- shared state for the trait experiments (X4 registered-trait arm, X42 grant).
-- TKX_TraitProbe is a GLOBAL on purpose: the harness lua.global witness reads it on each side.
-- Plain assignment, so a reloadlua resets the counters. Only plain values go in the table.
TKX_TraitProbe = { version = 1, grants = 0, removes = 0, lastId = "" }
