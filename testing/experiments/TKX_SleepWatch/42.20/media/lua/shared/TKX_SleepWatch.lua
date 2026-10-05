-- TKX_SleepWatch -- marker table. Shared so lua.global reads the version on either side; the
-- samples and histograms live in the GLOBAL modData table of the same name (server file), read
-- with witness.moddata global:TKX_SleepWatch.
TKX_SleepWatch = { version = 1 }
