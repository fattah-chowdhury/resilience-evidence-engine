# Roadmap and stage gates

Version 0.1.0 · 2026-09-07. This table replaces stale bootstrap status after checking actual code and outputs.

| Stage | Status | Implemented and verified / remaining gate |
| --- | --- | --- |
| 0 Architecture | PASS | Seven original architecture/state documents retained and corrected to current behavior |
| 1 Bootstrap | PASS | Package, argparse CLI, strict config and normalized SQLite; current wheel installs independently |
| 2 Offline demo | PASS WITH LIMITATIONS | Real-source curated facts/excerpts, 4 records → 5 claims / 4 events; not raw API or an accuracy benchmark |
| 3 Ingestion | PASS WITH LIMITATIONS | Ten format families plus JSONL/TSV/Atom; Excel active sheet, GPKG first layer; small-data contract |
| 4 Location/time | PASS WITH LIMITATIONS | Ambiguity, hierarchy, unknowns, ranges and anchored relative dates; tiny gazetteer, bounded parser |
| 5 Extraction | PASS WITH LIMITATIONS | Deterministic structured/keyword rules, negation, quantities; no measured multilingual accuracy |
| 6 Evidence | PASS WITH LIMITATIONS | Separate indicators, configurable grades/routing; heuristics are not calibrated probabilities |
| 7 Linkage | PASS WITH LIMITATIONS | Copy detection, provider grouping, independent-origin support, reviewed merges; no validated fuzzy event identity |
| 8 Review | PASS | Claim decisions and sequential accepted/rejected event links create child runs with provenance |
| 9 Live sources | BLOCKED | Registry, bounded USGS adapter and mock transport pass; actual API request failed DNS resolution |
| 10 Export/GIS | PASS WITH LIMITATIONS | CSV/JSON/Parquet/GeoJSON/GPKG; Python/OGR-backed reads pass; actual QGIS and R unavailable |
| 11 Frozen reproduction | PASS | Retained version/fixture/counts/dataset digest match source and installed-wheel runs |
| 12 Documentation | PASS WITH LIMITATIONS | Final manuals and isolated Linux wheel/CLI walkthrough; other OS instructions unexecuted |
| 13 Release audit | PASS WITH LIMITATIONS | Packaging/tests/install/privacy/rights audits completed; advisory lookup and external release gates remain blocked |

## Next work in dependency order

1. On a permitted network, execute the small historical USGS acceptance query and inspect the resulting
   real response/provenance. Keep this distinct from frozen reproduction and mock transport checks.
2. Rerun the pinned dependency advisory audit when service access is available. Review findings, make
   targeted updates and rerun only affected gates; do not report zero vulnerabilities without results.
3. Execute real QGIS and R/sf imports and record feature counts, CRS, null geometry and representation flags.
4. Validate Docker, other Python/OS combinations and hosted CI when those environments exist.
5. Establish owner/author/repository metadata and publication destination if public release is desired.

Longer term: richer authoritative gazetteers, independently annotated NLP evaluation, stronger multilingual
resolution, adapter registration, stable plugin/public API contracts, migration/resume machinery and
scale-appropriate matching. The version progression (0.1 foundation, 0.3 discovery, 0.5 evidence,
0.8 research tooling, 1.0 stable contracts) remains a roadmap, not an assertion that all versions shipped.
No automatic publication or admission/funding outcome is promised.
