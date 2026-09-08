# REE product specification

Version 0.1.0 · 2026-09-07

## Purpose and boundary
A local Python application converts permitted public or optional local evidence into separate documents,
claims, uncertain place/time interpretations, candidate events, review queues and GIS exports. Source
software and a usable manual are the deliverables. No manuscript, private dataset, paid model, database
server or cloud deployment is required. The default demonstration works offline after installation.

The application organizes evidence; it does not establish hazard risk, coverage, causality or ground truth.
Synthetic records are tests only. The real reference is explicitly a curated factual transcription and
short attributed excerpts, not a raw API capture or independently annotated scientific benchmark.

## Implemented increment
Initialize and validate YAML, run the reference, ingest documented local formats, process deterministic
rules, retain unresolved records, inspect HTML and GIS outputs, apply review CSVs to new child runs and
verify a frozen regression. Discovery is a curated registry; one bounded USGS live adapter is implemented,
with actual connectivity blocked in the build environment. Only functional commands are advertised.

## Acceptance gates
1. Install the wheel in an isolated environment outside the source tree and execute CLI/resources.
2. Produce real-source offline evidence and explicit uncertainty without network calls or invented geocodes.
3. Compare new frozen output with the retained fixture/version/counts/canonical dataset expectations.
4. Validate live collection against the actual provider; transport mocks are a separate gate.
5. Validate geometry, relationships, field provenance, immutable review and optional file interoperability.
6. Audit dependencies, data rights, privacy, beginner documentation and release packaging honestly.

See TEST_REPORT.md and RELEASE_READINESS.md for results. Failed/blocked gates are not converted into
success by generating files. This is experimental v0.1.0, not an accelerated claim of stable v1.0.

## Defaults and scale
No network/LLM execution by default. Maximum 1,000 acquired records; default 100. Each local file/HTTP
response is capped at 10 MB by default (20 MB maximum), with a 15-second default HTTP timeout (30 maximum).
Live acquisition uses one bounded query, not exhaustive pagination. Deduplication/link proposals are
quadratic and intended for small studies. Local languages are declared; English/Bangla keywords are
not robust automatic language detection. No scheduled jobs, remote publication or paid calls are enabled.
