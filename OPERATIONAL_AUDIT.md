# REE operational audit

2026-09-09 · Version 0.2.0 experimental candidate · MASTER PROMPT 2

The current offline core works in executed checks. This candidate does **not** pass every release gate.
The audit distinguishes current executable evidence from historical v0.1.0 results. It does not claim
live flood/cyclone collection, production-scale processing, or scientific validation.

## Continuity and verification scope

The original repository was clean at f25280b. Its installed v0.1.0 package reproduced the saved reference
exactly before new work. The prior 93-test suite also passed on the first operations implementation.
Workspace maintenance later removed the scratch checkout, environments and unfinished test process.
The saved v0.1.0 archive/Git bundle restored that baseline; recorded operations edits were recovered
without restarting architecture. A durable interim 0.2.0 checkpoint was saved. Reference inputs and
expected values remain byte-for-byte unchanged.

Current verification uses 28 standard-library unittest tests, including an installed-wheel run outside
the source tree, and an executed CLI walkthrough plus four configuration examples. The full pytest suite, Ruff and
optional GIS libraries could not be restored after network approval cancellation. Earlier 93-test and
GIS success records in audit/ are historical, not proof that the current full suite passed. Current
records are in audit/operations/. Wheel smoke testing uses a venv with preinstalled system dependencies;
that is separate from a pristine dependency installation, which remains blocked.

## Capability classification

| Capability | Current classification | Evidence and practical limit |
| --- | --- | --- |
| Package, CLI and resource loading | WORKING | Wheel built and installed; actual entry point and bundled assets executed |
| Fresh dependency installation | UNVERIFIED | Network bootstrap cancelled; no pristine-environment pass claimed |
| Offline demo | WORKING | No attachments, credentials, paid model or network needed after dependencies exist |
| Frozen reproduction | WORKING | 4 documents, 5 claims, 4 events, 12 reviews; only provenance software-version string tolerance |
| Config validation | WORKING | Strict YAML, keys, bounds, time ranges and processing assets |
| Config-only flood/cyclone/Kenya/CSV examples | WORKING | One existing real excerpt and one shared synthetic CSV; no corpus duplication |
| Local ingestion | PARTIALLY WORKING | Current CSV/JSONL/JSON checks; retained TXT/HTML/RSS implementations; optional readers await current extras |
| Source discovery | WORKING | Registry metadata, rights/access, coverage, credentials, suitability and reasons; no web search |
| USGS live collection | UNVERIFIED | Real request fails DNS in engine environment; mocked transport and recovery pass |
| Flood/cyclone live collection | NOT IMPLEMENTED | Demo/local evidence only; no eligible built-in live adapter for these hazards |
| ReliefWeb adapter | NOT IMPLEMENTED | Disabled/planned; provider approval and item-specific rights needed |
| Normalization and extraction | PARTIALLY WORKING | Typed records and deterministic rules; English/Bangla only, no accuracy benchmark |
| Time uncertainty | WORKING | Reference unknown occurrence remains unknown; publication date is not substituted |
| Location uncertainty | WORKING | Candidate/parent context retained; null confidence remains uncalibrated; no invented coordinates |
| Gazetteer coverage | PARTIALLY WORKING | Tiny configurable reference vocabulary; no authoritative global boundaries |
| Provider updates | WORKING | Changed geometry under reused source record ID gets a distinct location interpretation |
| Duplicate handling | WORKING | Document-copy relations remain separate from event identity and corroboration |
| Evidence grades | PARTIALLY WORKING | Transparent rule indicators; grades are not validated reliability probabilities |
| Human claim and event-link review | WORKING | Context pages/JSON, original source text, candidates and both event sides; new immutable child runs |
| Data integrity/provenance | WORKING | Inventory, schema, counts, categories, links, geometry, config/rules and field-value hashes checked |
| Privacy suppression | PARTIALLY WORKING | Public checkpoints and exports suppress declared private/unshareable records; no automatic PII detector |
| Failure recovery | WORKING | Completed input/source acquisition survives downstream failure; failed parent preserved |
| Fine-grained NLP/database resume | NOT IMPLEMENTED | Processing restarts from acquisition; corrupted/partially written inventories require manual recovery |
| Public response cache | WORKING | Opt-in USGS-only cache, one-hour TTL, hashes/retrieval time, corruption refusal, safe clearing |
| Run comparison | WORKING | Validated counts, grade/place distributions, source changes and collection outcomes |
| CSV/JSON/point GeoJSON | WORKING | Current programmatic read/geometry/count checks |
| Parquet/GeoPackage | UNVERIFIED | Implemented and historically tested; current optional dependencies unavailable |
| QGIS/R desktop workflows | UNVERIFIED | Programs unavailable; no successful desktop import claimed |
| Logging/timing | WORKING | INFO/WARNING/ERROR/DEBUG, manifest timings and structured reasons |
| Memory and performance | PARTIALLY WORKING | CSV/JSONL streaming and smaller pair provenance; processing/linkage still bounded and quadratic |
| External source interface | WORKING | Complete synthetic adapter runs via explicit Python registration with source/budget/rights validation |
| Automatic plugin discovery / LLM backend | NOT IMPLEMENTED | No executable YAML imports or paid service assumptions |
| Documentation | PARTIALLY WORKING | Core command walkthrough executed; platform/optional/live exceptions identified |
| Docker | UNVERIFIED | Dockerfile exists; Docker runtime unavailable |
| GitHub Actions | UNVERIFIED | Install/lint/test/demo matrix configured; no hosted run inspected here |
| Secret/data-rights audit | PARTIALLY WORKING | Current source/archive static scope and provider terms; no advisory-service or forensic guarantee |
| Public release / DOI | NOT IMPLEMENTED | Assets prepared; no external publication by this operation; owner/citation metadata still needs review |

## Repairs made

1. Review files now expose source text, date interpretation, candidate places, parent geography and event-pair context.
2. Validation checks complete file inventories and semantic dataset/config/rule/count consistency.
   A final check also fixed an extra-file bypass involving a second file named run_manifest.json;
   malformed non-object manifests now fail with a clear error.
3. Acquisition checkpoints preserve completed work; resume and export create children. Partial failures remain visible.
4. Public USGS cache validates content/hash/time/endpoint and never falls back to stale content silently.
5. A documented adapter registration boundary validates the contract without requiring core edits.
6. Provider updates retain different coordinate interpretations instead of aliasing them to the same location row.
7. Unsupported languages and malformed gazetteer records fail explicitly. CSV/JSONL ingestion streams rows.
8. Duplicate-pair provenance records reference just their two documents. The 100-record profile reduced peak
   traced allocation from 174,342,763 to 44,334,736 bytes; timings include instrumentation overhead.

## Universality decisions

| Constraint | Classification | Decision |
| --- | --- | --- |
| Bangladesh/Sylhet in bundled demo | Appropriate reference default | Preserved; Kenya synthetic configuration proves country is not fixed in orchestration |
| Flood/earthquake default topics | Appropriate reference default | Configurable taxonomy/topics; cyclone CSV also runs |
| English/Bangla rule backend | Explicit implementation limit | Reject other languages; configuration filters are not a multilingual NLP promise |
| USGS host/path allowlist | Appropriate provider boundary | Explicit adapter interface supports another source; no arbitrary network target from YAML |
| EPSG:4326 output | Appropriate interchange contract | GeoPackage input can reproject with extras; other output CRS and antimeridian boxes deferred |
| Relative config/input/output paths | Configurable behavior | Resume retains the original config base for unfinished inputs |
| Missing review context / weak inventory validation | Undesirable implementation limits | Fixed |
| Whole-batch hashes on every duplicate pair | Undesirable redundant work | Fixed without changing frozen reference evidence |

## Failure and red-team results

Current tests exercise timeout, rate limiting, malformed API body, invalid JSONL/records, absent input,
bad gazetteer, unsupported language, cache corruption/symlinks, changed checkpoint, altered manifests,
invalid event geometry, duplicate/syndicated reports, review decisions and public suppression. Original
failed/partial runs remain intact; no live failure is replaced by synthetic or demo data.

Manifests are unsigned. A person able to rewrite data and every hash can forge a run. Generic extension
code is trusted executable Python. CSV/HTML escaping and declaration-based suppression do not provide
automatic anonymization. Config paths can appear in private/local run metadata and must be reviewed
before sharing. The distributed historical audit copy redacts machine-specific build paths; the original
v0.1.0 archive is preserved unchanged.
