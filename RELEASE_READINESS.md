# Release readiness — REE 0.1.0

2026-09-07 · **PASS WITH LIMITATIONS for an experimental offline release checkpoint.**
**Full MASTER PROMPT 1 acceptance is not complete.** This is not a production-ready or publicly published v1.0.

## Reviewable deliverable

The continued source repository, installable wheel/source distribution, complete user and maintainer
manuals, test/audit evidence and one verified frozen example are packaged together. No private source,
paid AI service or API key is required for the demo. The earlier Stage 0–1 archive remains historical.

| Gate | Result | Evidence / unresolved work |
| --- | --- | --- |
| Installation | PASS | Fresh venv, six pinned core dependencies, installed current wheel outside source tree |
| Unit/integration/regression tests | PASS | 93 passed; all runtime extras exercised; Ruff clean |
| Offline demo | PASS WITH LIMITATIONS | 4 real-source curated records, 5 claims, 4 events; limited reference scope |
| Frozen reproduction | PASS | Retained fixture/version/counts/dataset digest match installed wheel |
| Review/provenance/privacy | PASS WITH LIMITATIONS | Immutable decisions, field hashes, canary suppression; no automatic anonymization |
| Python GIS interoperability | PASS | Actual GPKG/GeoJSON/Parquet readers, CRS/null/empty handling |
| QGIS and R interoperability | BLOCKED | Applications unavailable; actual imports must still be executed |
| Real live collection | BLOCKED | Bounded historical USGS query failed DNS; mocked transport passes separately |
| Dependency advisory audit | BLOCKED | Network approval cancelled; inventory saved, advisory findings unknown |
| Data-rights audit | PASS WITH LIMITATIONS | Narrow attributed facts/short excerpts reviewed; excludes images/logos/third-party data |
| Documentation | PASS WITH LIMITATIONS | Isolated Linux wheel walkthrough; other OS commands unexecuted |
| Packaging/local repository | PASS | Source/wheel, resource checks, local Git checkpoint and archive checksums |
| Docker/hosted CI/publication | PASS WITH LIMITATIONS | Files prepared; Docker and remote CI unexecuted; no remote/PyPI/DOI publication |

## Material limitations

This is a bounded deterministic evidence organizer, not a validated risk model or warning service.
The curated sample is not a raw API capture or independent NLP benchmark. English/Bangla support is
limited keywords/digits. The tiny gazetteer has no authoritative administrative boundaries. Only the
USGS adapter collects live data; query truncation is reported, not exhaustively paginated. Matching is
quadratic with a maximum 1,000 records. Generic Excel uses its active sheet; GPKG uses its first layer.

Whole-record suppression is declaration-driven. Private content and config paths need review before
sharing. No automatic PII classifier, aggregation/masking, LLM execution, remote geocoder, installable
plugin discovery or database migration framework is claimed. Manifests are not signed. Dependency pins
are tested versions, not a universal/hash-locked supply-chain guarantee. Code and external data licenses
remain separate. Personal author metadata and the public repository destination are not established.

## Exact next acceptance actions

1. In a permitted network environment, run:
   `ree run --config configs/examples/usgs_historical_check.yml --live`.
   Confirm real USGS records/provenance, then validate that run. Do not replace the frozen sample automatically.
2. With advisory-service access, run:
   `python -m pip_audit -r requirements-all.lock --no-deps --disable-pip --strict`.
   Inspect results and update only affected dependencies/tests; do not ignore findings to pass a gate.
3. Open verified GeoJSON or a GPKG export in actual QGIS and R/sf. Check four events, EPSG:4326,
   two non-null point representations and the Noto representational flag. Instructions are in the manual.
4. Execute Docker/hosted CI and other target environments before claiming their support was verified.
   Public GitHub/PyPI publication additionally needs the owner's actual identity/destination and authorization.

## MASTER PROMPT 2 handoff

**Ready as a concrete continuation/audit checkpoint, with blockers carried forward. Not ready for a
claim that MASTER PROMPT 1 passed every acceptance gate.** Begin with this document and PROJECT_STATE.md;
preserve completed code, frozen data, decisions and existing runs. The remaining work is verification
and targeted hardening in available environments, not restarting architecture or rebuilding the project.
