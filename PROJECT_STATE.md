# Project state

Version: 0.1.0 (experimental) · checkpoint date: 2026-09-07

## Continuity

The durable REE_Stage0_Stage1_Source.zip checkpoint was recovered and its Stage 0–1 foundation verified.
The archive was preserved. This continuation expanded the existing modules and corrected bootstrap
statements only where tests/code proved them obsolete. Frozen inputs and expected semantic output hashes
were retained across verification; no duplicate reference dataset or new architectural restart was introduced.

## Completed in this continuation

- Real-source curated offline demo, normalized ingestion and typed records.
- Explicit location/time uncertainty, rule extraction and transparent evidence indicators.
- Duplicate/corroboration separation, conservative linkage and immutable claim/event-link review.
- Curated source discovery and bounded USGS adapter, including failure manifests.
- Relational/GIS exports, offline report and field provenance with validation.
- Frozen version/input/count/dataset regression from both source and installed wheel.
- 93 passing tests with all runtime extras installed; clean Ruff result.
- Clean virtual environment with six pinned core dependencies installed; current wheel installed and
  run outside the source tree with system-site-packages disabled and no PYTHONPATH override.
- Final user/maintainer manuals, source-rights policy, CI, governance, packaging and release audit.

## Failed or blocked operations

- Real historical USGS request: temporary DNS resolution failure, exit 2. Original failure manifest
  retained in audit/live-attempt-manifest.json. No successful live response or fallback data is claimed.
- Dependency advisory scan: network approval cancellation before a decision; no advisory results.
  audit/dependency-audit-status.json records the blocker and exact command.
- QGIS, R/sf, Docker and remote GitHub Actions execution: unavailable in this environment, not run.

## Technical debt and limits

Small curated factual sample; basic English/Bangla keywords rather than evaluated multilingual NLP;
tiny name-only gazetteer; no general web crawler, exhaustive API pagination, remote geocoder, LLM,
automatic plugin loading, in-place database migrations, PII classifier or spatial anonymization.
Configuration paths can remain in metadata. Dependency pins are Linux/Python 3.12 snapshots, not
hash-locked universal environments. Manifests are unsigned. Maximum 1,000 records with quadratic matching.

## Last safe checkpoint and next action

The offline v0.1.0 implementation is saved with build/test evidence, a wheel and a verified example.
Read RELEASE_READINESS.md before continuing. Close the three external acceptance gaps: actual live API,
actual QGIS/R interoperability and online dependency advisories. A reviewed correction should preserve
old runs and use a new child/retry run. Do not rerun completed stages or refresh expected.json by default.

MASTER PROMPT 1 has an auditable working implementation and final deliverables, but its full acceptance
workflow is **not completely passed**. MASTER PROMPT 2 may continue from this checkpoint with these
blockers explicitly carried forward; it must not assume a fully verified production/public release.
