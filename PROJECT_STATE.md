# REE project state — 2026-09-09

Version **0.2.0**, experimental operations candidate. Fully verified public release: **HOLD**.

## Continuity

Original v0.1.0 commit f25280b and its architecture remain the baseline. Workspace maintenance
removed an intermediate checkout; the saved original archive/Git bundle restored its history.
The operations changes were recovered, then checked on the current source and installed wheel.
No frozen inputs or expected hashes/counts were regenerated. The original release remains intact.

## Completed in this continuation

- [x] Audit actual code and separate historical from current evidence.
- [x] Preserve source/document/claim/location/event separation and existing architecture.
- [x] Add contextual claim/event-link review, stricter inventory/database/provenance validation.
- [x] Add acquisition checkpoints, immutable resume, opt-in public USGS cache and run comparison.
- [x] Validate an explicit external adapter example without core edits.
- [x] Run flood, cyclone, mapped CSV and alternate-country configurations without duplicating real data.
- [x] Exercise malformed input, source failure, uncertainty, duplicates, privacy and recovery cases.
- [x] Preserve changed provider geometry and reduce redundant duplicate-pair provenance allocation.
- [x] Pass 28 current operational unittest checks on the installed wheel outside the source tree.
- [x] Execute CLI help, doctor, schema, demo, init/run, validation, discovery, review, export,
  report, resume, comparison, cache inspection and example commands.
- [x] Pass frozen comparison with only the declared provenance software-version tolerance.
- [x] Attempt a real bounded USGS query and retain its DNS failure manifest.
- [x] Complete the operational audit, reproducibility report, data sources, quality scorecard,
  release readiness, user manual and maintainer manual.

The final distribution groups source, build artifacts and one unchanged verified example.
Current verification evidence is under audit/operations/. Files directly under audit/ preserve
historical v0.1.0 evidence and must not be counted as current full-suite passes.

## Current verification scope

The installed wheel uses a venv with preinstalled system dependencies. It is not a pristine
installation proof. The original 93-test pytest suite and Ruff/GIS results are historical.
The current full pytest suite, Ruff, optional Parquet/GeoPackage, QGIS/R, Docker and hosted CI
remain unverified. Online dependency bootstrap/advisory work was cancelled before network approval
returned. The new actual USGS request failed DNS resolution; no successful live records are claimed.

Reference counts remain 4 documents, 5 claims, 4 candidate events and 12 pending reviews.
The current raw dataset hash differs because truthful 0.2.0 provenance is stored. A comparison
copy normalizes only transformation.ree_version to 0.1.0; all other reference values must match.

## Next safe checkpoint

Continue from this candidate, not from bootstrap. In an environment supporting the blocked tools,
complete the remaining gates in RELEASE_READINESS.md: pristine installation, full pytest/Ruff and
optional GIS readers, actual live USGS, dependency advisories, QGIS/R, Docker and hosted CI.
Review real owner/citation/destination metadata before any public release or DOI registration.
No external publication was performed by this operations run.

MASTER PROMPT 2's available operational work is complete, but neither master's full acceptance
criteria can be certified complete until those recorded gates pass. No scientific accuracy,
operational hazard safety, production scale or comprehensive live hazard coverage is claimed.
