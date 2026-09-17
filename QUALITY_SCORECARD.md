# REE quality scorecard

2026-09-09 · v0.2.0 experimental candidate. Scores are engineering judgments, not benchmark results.
Scale: 0 absent; 1 scaffold; 2 partial/unverified; 3 tested in a bounded environment; 4 strong evidence
across relevant paths; 5 broad independent validation. No average is used to conceal a blocking gate.

| Dimension | Score / 5 | Evidence and limit |
| --- | ---: | --- |
| Installability | 2 | Wheel runs using existing dependencies; pristine bootstrap blocked |
| Reliability | 3 | 28 current operational tests; current full pytest suite unverified |
| Reproducibility | 4 | Original input/expectation files retained; narrow version tolerance and claim-drift test |
| Test coverage | 2 | Critical cases exercised; no measured line/branch coverage and current full suite unavailable |
| Modularity | 3 | Separate pipeline, adapters, cache, integrity, review and exports; stable long-term API not promised |
| Data integrity | 3 | Current inventory/schema/count/category/geometry/link/provenance checks; no signed integrity |
| Provenance | 3 | Input/config/rule/field hashes, acquisition records and child lineage; some whole-batch lineage remains |
| Uncertainty | 3 | No forced centroid/date, conflicting updates retained; tiny gazetteer and uncalibrated scores |
| Documentation | 3 | Core walkthrough and complete manual; optional/platform-specific commands have explicit gaps |
| User experience | 3 | No-attachment demo, contextual review, immutable resume; no usability study |
| Extensibility | 3 | External synthetic source adapter executes without core edits; no automatic plugin loading |
| Security | 2 | Static checks, endpoint/cache restrictions and privacy canaries; advisory service blocked |
| Licensing | 3 | Narrow provider scope, attributed excerpt/facts, synthetic examples; no blanket clearance for new sources |

Clear strengths: working offline core, preserved uncertainty, traceable outputs and practical recovery.
Release blockers: pristine/current full-suite verification and actual live/GIS/desktop/container/CI gates.
The project remains experimental software, with no prediction, risk-warning or funding-outcome claim.
