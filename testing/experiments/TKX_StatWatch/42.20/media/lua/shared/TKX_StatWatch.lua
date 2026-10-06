-- TKX_StatWatch -- marker table. Shared so lua.global reads the version on either side; the
-- samples, histograms and tag counters live in the GLOBAL modData table of the same name (server
-- file), read with witness.moddata global:TKX_StatWatch.
TKX_StatWatch = { version = 1 }
