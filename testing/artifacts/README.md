# testing/artifacts

Tracked, immutable copies of the measured evidence the reference cites as `M` rows: one folder per run id (`<experiment>-<UTC timestamp>`), holding the result JSON the run wrote and, where a claim rests on it, a run file that JSON does not contain.
Every file is committed byte-identical to the run copy (verify with `sha256sum`) and is never hand-edited.
The local `.gitattributes` sets `* -text`, so `core.autocrlf` cannot rewrite the CRLF newlines and the committed blob stays byte-identical to what the experiment wrote.
The register of runs (one row per committed run, its reading guide and its do-not-cite keys) is [`docs/reference/artifacts.md`](../../docs/reference/artifacts.md).
