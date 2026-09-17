# REE user manual

Version 0.2.0 · operational audit 2026-09-09

REE is software for organizing source evidence. Documents can contain several claims; claims may
support one candidate event. A map point, a grade or a human decision does not establish ground truth.
No source upload is required to try the software.

## 1. Installation

You need Python 3.11 or later and a terminal. Python 3.12.13 on Linux was the executed release test;
Windows/macOS and Python 3.11 have not been executed here. The 0.2.0 wheel was tested outside
the source tree with preinstalled runtime dependencies; a completely fresh dependency installation
was blocked by network approval cancellation. See RELEASE_READINESS.md for the exact test scope. Extract the release ZIP. The source folder
is `resilience-evidence-engine`; open your terminal there.

```bash
python --version
python -m venv .venv
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell activation is restricted, run `.venv\Scripts\python.exe -m pip install .` and
`.venv\Scripts\python.exe -m ree demo` directly. Changing the machine execution policy is unnecessary.
On systems exposing Python only as `python3` or `py`, use that command to create the environment.
After activation:

```bash
python -m pip install .
ree --version
ree doctor
```

The distribution also includes a wheel under `artifacts/`. From the extracted release root:

```bash
python -m pip install artifacts/resilience_evidence_engine-0.2.0-py3-none-any.whl
```

Choose either source or wheel installation. Use the supplied artifacts; this operations run did not
publish a PyPI package. Dependencies usually need internet the first time. The supplied
`requirements-core.lock` records the earlier Linux/Python 3.12 installation: install it before the
source or wheel with `--no-deps` when those pins suit your environment. A fresh bootstrap of those
dependencies was not verified for 0.2.0. Other platforms may need different compatible wheels.

Optional readers and exporters are installed from the source folder:

```bash
python -m pip install '.[excel,columnar,gis]'
```

Excel requires `excel`; Parquet requires `columnar`; GeoPackage and polygon validation require `gis`.
CSV, JSON, text and point GeoJSON need only core dependencies. `ree doctor` reports local dependency
availability, SQLite integrity and output-parent access. It does not prove live API connectivity.

## 2. Your first five minutes

```bash
ree demo
ree reproduce flagship
ree init my-project
ree run --config my-project/project.yml
```

`demo` writes `outputs/flagship/<run_id>/` beneath the current directory and prints the exact path.
Open `summary/run_report.html` in that run. `reproduce` makes another run and compares the frozen
fixture, table counts and canonical dataset digest with the saved reference. The sole version
compatibility tolerance is the ree_version string inside field provenance. Raw current-version
provenance remains intact and its unadjusted hash is also reported.

`init` creates a ready-to-run offline `project.yml`. It refuses to overwrite an existing configuration.
For this initialized project, relative outputs are beneath the configuration's folder:
`my-project/outputs/my-project/<run_id>/`. Every run gets a new directory. Do not overwrite older runs.
Use `--output /your/chosen/directory` to choose an output base. REE adds project and run identifiers.

The reference result is 4 documents, 5 claims, 4 candidate events and 12 pending review items.
These are software regression expectations, not measured extraction accuracy. There are 2 point
representations and 2 null geometries. All reference claims require review; 4 are grade C and 1 is D.
The small sample is a curated transcription of official facts plus short excerpts, not a raw API capture.

## 3. Configuration

Edit `project.yml` in a text editor, then validate it:

```bash
ree validate --config my-project/project.yml
```

Unknown or duplicate keys, unsafe YAML, invalid bounds and unsupported values fail with an error.
Files are UTF-8; configuration is limited to 64 KiB. Relative inputs, processing assets and output_dir
are resolved relative to the configuration file. CLI `--output` is resolved from the current directory.

| Setting | Meaning |
| --- | --- |
| `schema_version: 1` | Configuration contract version |
| `project.name` | 1–64 letters, digits, underscores or hyphens; first character alphanumeric |
| `mode` | `demo`, `local`, `live`, or `hybrid` (local + live) |
| `study_area.country` | Exact configured name, or `global`; unknown membership is flagged |
| `study_area.admin_units` | Textual scope hints; not authoritative boundary containment |
| `study_area.bbox` | `[west, south, east, north]` in WGS84; no antimeridian-crossing box |
| `time.start`, `time.end` | Inclusive dates or null; unknown event dates remain unresolved |
| `topics`, `languages` | Category and declared-language filters; no robust automatic language identification |
| `collection.public_sources` | Must be true for live/hybrid; CLI `--live` is also required |
| `collection.sources` | Only `usgs_catalog` currently collects live data |
| `collection.max_records` | Default 100, maximum 1,000; truncation produces partial status |
| `collection.max_bytes` | Default 10,000,000, maximum 20,000,000 per local file/response |
| `collection.timeout_seconds` | Default 15; maximum 30 seconds per HTTP attempt |
| `collection.min_magnitude` | USGS filter; default 5 |
| `processing.human_review` | Advisory flag; false does not bypass uncertainty queues |
| `processing.llm_enabled` | Must be false; no LLM execution is implemented |
| `processing.gazetteer`, `taxonomy`, `evidence_rules` | Optional JSON/YAML asset paths; null uses bundled assets |
| `processing.link_days`, `link_km` | Proposal window, default 3 days / 30 km; not automatic fuzzy merge thresholds |
| `exports` | Nonempty list drawn from csv, json, geojson, parquet, gpkg |
| `export_policy` | `private` (default), or `public` with record suppression |

Examples are in `configs/examples/`. `bangladesh_excerpt.yml` filters the frozen reference to a
single flood excerpt. It does not collect live Bangladesh flood reports.

## 4. Ingest your own permitted evidence

The fastest private workflow is:

```bash
ree ingest /path/to/records.json
```

For column mapping, declared rights and repeat runs, edit a project config:

```yaml
project:
  name: local-study
mode: local
inputs:
  - path: evidence.csv
    columns:
      narrative: text
      place_name: location_text
    sensitive: true
    redistribution_allowed: false
    license: unknown
export_policy: private
topics: [flood, earthquake, tsunami]
languages: [en, bn]
exports: [csv, json, geojson]
```

The mapping direction is **input column → canonical field**. Each record requires nonblank `text`;
a stable `source_record_id` is recommended and otherwise derived from content. Optional fields:
`title`, `url`, `language`, `country`, `location_text`, `date_text`, `published_at`, `category`,
`provider_event_id`, `geometry`, `geometry_role`, `quantities`, `sensitive`, and `acquisition`.
Unknown fields are rejected. The local adapter assigns its own source identity; a supplied source_id
cannot impersonate an official provider. URLs are metadata and are never automatically downloaded.

Use ISO strings for dates/timestamps. CSV `geometry`, `quantities` and `acquisition` values must be
JSON strings. Alternatively use numeric `longitude` and `latitude` columns. WGS84 is longitude first.
Point roles are `source_point`, `admin_centroid`, `model_reference` or `unknown`; polygons require
`area`. A missing point role is unknown, not exact. Quantities require `kind`, numeric `value`, and `unit`.

| Format | Reader behavior |
| --- | --- |
| JSON | Array of record objects; GeoJSON FeatureCollection also accepted |
| JSONL / NDJSON | One object per line; bad lines are quarantined independently |
| CSV / TSV | Headers required; quoted multiline fields accepted |
| TXT | One narrative record per file |
| HTML | One visible-text record; scripts/styles discarded; no browser execution |
| RSS / Atom XML | item/entry title, description/content, link, identifier; DTD/entities refused |
| GeoJSON | Feature properties must follow record schema; null geometries allowed; no legacy crs member |
| XLSX / XLSM | Active worksheet, string headers, cached values; macros not executed; no legacy XLS reader |
| Parquet | Canonical record columns, read in batches |
| GeoPackage | First layer, declared CRS required, converted to WGS84; canonical record properties required |

General XML schemas, PDF, legacy XLS, nested arbitrary API JSON and every spreadsheet are not supported.
Convert them to the documented record schema first. REE's exported normalized tables are not the same
schema as input records; use a deliberate mapping rather than feeding every exported table back in.
RSS publication-date fields are not currently promoted to anchors; supply a canonical published_at
when resolving relative dates in local records.

Invalid records appear by row/hash and reason in `logs/processing.json`; no raw quarantined text is
written. A partially valid file can produce a partial run (exit 3). Fatal input/export failures produce
a failure manifest (exit 2). Configuration/argument errors happen before a run exists.

## 5. Places, time and evidence grades

The bundled gazetteer is deliberately tiny and name-only: Japan, Bangladesh, Sylhet city and an
unresolved surrounding-area interpretation. It is not an authoritative administrative boundary set.
A custom gazetteer can supply hierarchies and valid geometry. Ambiguous matches stay as candidates;
unknown places get no fabricated coordinates. The local resolver checks hierarchy and country consistency.

Dates support exact ISO dates/timestamps, months, ranges, relative weekdays/yesterday/last week and
unknown. Relative expressions require a valid publication anchor; publication is not silently used
as occurrence. Conflicting or invalid dates remain unresolved. Bangla digits and a small keyword
vocabulary are supported. The current rule backend explicitly refuses other languages; there is no benchmarked multilingual NER or general temporal parser.

Extraction uses deterministic keywords and structured fields. Heuristic confidence values are not
probabilities. Negated claims are excluded; hypothetical/forecast claims require review. Quantity
mentions preserve spans/approximation but do not establish affected-person roles or unit conversions.

Seven separate indicators describe source characteristics, spatial precision, temporal precision,
claim specificity, extraction confidence, independent corroboration and verification state.

| Grade | Default rule summary |
| --- | --- |
| A | Human verified, precise geometry, exact time and at least two independent origin groups |
| B | Precise geometry and exact time; verified or no remaining automatic review reasons |
| C | Some time and a selected location, with unresolved support/precision concerns |
| D | Missing or unresolved support; retain for inspection |
| X | Negated or explicitly rejected claim |

`AUTO_ACCEPT`, `REVIEW`, and `REJECT` are processing decisions. Human acceptance is separately
recorded in verification_state. Accepting an uncertainty explanation does not invent a date, boundary
or precision. Copied text does not increase corroboration. Same provider-event/category/origin can
join automatically; other nearby events are proposed for review. Different categories stay distinct.

## 6. Human review without editing Python

Replace `RUN` below with the exact run directory printed by REE. Do not type the word RUN literally.

```bash
ree review RUN
```

Open `RUN/review/context.html` first: it shows original text, source URL, date interpretation,
candidate places, parent geography and uncalibrated (null) confidence. Event-link pairs with
both events and their claims are in `RUN/review/event_link_context.json`.

Copy `RUN/review/decisions_template.csv` **outside the run**, for example to `my-decisions.csv`.
Do not edit generated files in place: their hashes are part of integrity validation.
Complete only rows you can justify; leave `decision` blank to defer. Set `decision` to `accepted` or
`rejected`, and supply `reviewer` and an explanatory `note`. Keep review_id unchanged. For an accepted
ambiguous-location item, supply one existing candidate location_id from `claim_location`/claim metadata.

```bash
ree review RUN --decisions my-decisions.csv
```

REE validates IDs, decisions and candidate membership, then creates a new child run carrying history.
A rejected item excludes its claim from event support. All review reasons for a claim must be accepted
before its verification state becomes human_accepted. Some claims still retain C/D and REVIEW because
uncertainty remains. Already recorded decisions cannot be overwritten; start from the parent run to
make a deliberate alternative branch.

For event links, copy `review/possible_event_links.csv` outside the run. Keep both event IDs, complete
accepted/rejected, reviewer and note, then:

```bash
ree review RUN --links my-event-links.csv
```

Accepted same-category proposals merge events into a new identity and reassess corroboration.
Rejected proposals stay separate and leave the pending proposal queue. Sequential reviewed merges
retain earlier decisions. Use the child run for subsequent work. An empty proposals CSV is valid.

## 7. Source discovery and live collection

```bash
ree sources
ree discover --config configs/examples/usgs_live.yml
ree run --config configs/examples/usgs_live.yml --live
```

Discovery matches curated metadata; it is not web search and makes no network request. `live_eligible`
means the configured adapter/policy permits a request, not that connectivity has been verified.
Only the USGS catalog adapter collects data. ReliefWeb remains disabled pending provider approval
and item-level rights review. No arbitrary URL crawler or remote HTML collector is enabled.

Live/hybrid mode also requires `collection.public_sources: true`. A named country requires an explicit
bbox for the USGS adapter; it cannot filter named administrative units. Default null live dates mean
the latest 30 days through the current UTC date. The adapter requests USGS-contributed earthquakes,
checks host/DNS, refuses redirects, limits response size and uses bounded retries for transient HTTP
errors. It fetches at most the configured budget plus one sentinel and reports truncation. It does
not paginate the entire catalog or claim completeness. A bbox is not a national boundary.

The real acceptance request in this build failed DNS resolution. Mocked HTTP tests pass, but a successful
external response remains unverified. A failed live request is not replaced by demo data. Inspect the
printed failure manifest. `usgs_historical_check.yml` is the small explicit acceptance query to rerun
in a network-enabled environment. No credentials are needed for that adapter.

## 8. Outputs and GIS

Each run contains:

```text
RUN/
  data/          evidence.sqlite and requested normalized CSV/JSON/Parquet tables
  gis/           requested locations/events GeoJSON and two-layer evidence.gpkg
  review/        decision template, ambiguity/uncertainty queues, event-link proposals
  maps/          event_coordinates.svg
  logs/          run log and quarantined-record reasons
  provenance/    replay, sources, transformations, input/code hashes, decisions, manifest
  summary/       run_report.html
```

The report contains a searchable candidate-event table and a coordinate plot without a basemap.
Green points are source-reported; amber points are representational references. Missing locations
stay unmapped. No plotted point is an impact footprint or quantified error estimate.

```bash
ree validate --run RUN
ree report --run RUN
ree export --run RUN --format csv --format parquet --format geojson --format gpkg
```

Export replays the validated snapshot into a **new run**, preserving review history. Source files and
API access are unnecessary. Keep CSV/JSON alongside GIS if you want all relational evidence and
provenance: GeoPackage contains event/location layers, not the entire database.

Python example, with `gis` installed:

```python
from pathlib import Path
import geopandas as gpd
run = Path('REPLACE_WITH_RUN_DIRECTORY')
events = gpd.read_file(run / 'gis/evidence.gpkg', layer='events')
print(events.crs, len(events), events.geometry.isna().sum())
```

QGIS: add `gis/evidence.gpkg` as a vector source, choose `events` and `locations`, inspect
representational/spatial_precision properties and the attribute table for null geometry.
R with sf: `sf::st_read('RUN/gis/evidence.gpkg', layer='events')`. Python file interoperability was
executed; QGIS desktop and R were not installed in the build environment, so those instructions remain
external verification steps. GeoJSON may keep nested metadata; GeoPackage encodes nested values as JSON text.
CSV text beginning with spreadsheet formula markers is prefixed with an apostrophe for safety.
SQLite/JSON retain the original normalized values. Parquet SQL JSON columns remain JSON strings.

## 9. Frozen reproduction and provenance

`ree reproduce flagship` compares the committed expected.json with a new run. Do not regenerate the
expected file merely to make a failing test pass. Investigate input, rule, software and dependency drift.
The reference digest excludes run IDs, wall-clock timestamps and incidental SQLite binary bytes, and
includes stable sorted normalized tables and field transformation records. Tests separately check GIS
geometry/counts; reproduction does not promise byte-identical HTML, GeoPackage, Parquet or SQLite files.

`ree validate --run RUN` checks the complete file inventory, schema, output hashes, database
relationships, counts, taxonomy, event geometry and links, config/rule fingerprints and field provenance. Manifests are not cryptographically signed; integrity checks
are for accidental changes, not a hostile party able to rewrite both data and manifest.

Replay captures allowed input records, config and rule assets. Field transformations link target keys
and output value hashes to contributing input/config/rule hashes. Some stages record the contributing
input set rather than a single semantic span; claim offsets explicitly refer to normalized document text.
Wheel installs may report code_commit null because Git history is absent; package_code_hash still
identifies the bundled code/assets. Keep the release's checksums with your archive.

Live reruns can differ because sources change. Preserve the entire resulting run for offline replay;
a live rerun is not the frozen benchmark. Invalid configurations and read-only helper commands do not
create processing manifests; every started processing run does, including failures.

## 10. Privacy and data rights

Private local inputs default to sensitive and redistribution disallowed. In public mode, entire sensitive
or unapproved records are removed before persistence, replay, reports or exports. Configuration metadata can still contain local file paths; inspect it before sharing.
To permit public output, declare a named license
or rights basis, redistribution_allowed true and sensitive false only for records you have reviewed.
These declarations are your assertions; REE cannot automatically establish copyright or detect every
person/address. There is no automatic PII classifier, spatial masking or disclosure-proof aggregation.

Private outputs retain text and metadata. Keep them in an appropriate private location. Do not commit
private output folders. Optional LLM execution is rejected; no user content is sent to an AI service.
The demo includes facts and short attributed excerpts, not source imagery, logos or third-party basemaps.
Read SOURCE_STRATEGY.md before broadening a source or redistributing outputs.

## 11. Extension points

Change JSON/YAML gazetteer, taxonomy and rule files through configuration; see MAINTAINER_MANUAL.md
for their schemas. SourceAdapter and separate processing/export modules provide internal interfaces.
Source adapters can be registered through the public `run(..., adapters=..., source_registry=...)`
Python interface without editing core code. Run `python examples/external_adapter/run_example.py`
from the repository root to test the complete synthetic adapter. That demonstration uses no network
and is not a live-source acceptance test. NLP/exporter extensions still require explicit integration
and tests. Third-party entry-point packages, remote geocoders and LLM execution are future work;
installing an arbitrary `ree-source-*` package does not automatically activate it.

## 12. Troubleshooting and FAQ

| Symptom | Action |
| --- | --- |
| `ree` not found | Activate the environment, or use `python -m ree` with the same interpreter |
| Existing project config | Edit it intentionally, or choose another directory; init will not overwrite |
| Missing optional dependency | Install the corresponding extra in the active environment |
| No claims/events | Inspect topics, language/country/time filters, suppression counts and no-match notices |
| Partial result, exit 3 | Read quarantine reasons; correct only invalid rows or narrow an over-budget input/query |
| Changed output / failed validation | Restore original hashed files; copy review templates outside the run before editing |
| Live DNS/HTTP failure | Preserve failure manifest; verify connectivity/provider availability; no demo fallback occurs |
| Relative dates unresolved | Supply a supported publication anchor and date expression; do not infer one silently |
| Point not shown | It may have null geometry; inspect candidates and review rather than invent coordinates |
| Frozen drift, exit 4 | Inspect reproduction_check.json and code/config/dependency changes; keep original reference |

Exit codes: 0 success, 2 fatal/configuration error, 3 partial run, 4 frozen reference mismatch.
No warning service, event completeness, independent scientific validation or funding/admission outcome
is promised. The software can organize evidence; users remain responsible for interpreting it.


## 13. Recovery, caching and comparison (v0.2.0)

Copy the printed run path in place of RUN. A resumed run always receives a new child directory:

```bash
ree run --resume RUN
```

For unfinished network acquisition, an explicit flag is still required:

```bash
ree run --resume RUN --live
```

Completed local files and source batches are saved in a hashed acquisition checkpoint. If a later
input or exporter fails, recovery reuses those records without requiring the completed input files.
Unfinished relative inputs are resolved from the original config directory. Processing restarts from
the acquisition checkpoint; this is not per-record or mid-NLP continuation. Preflight failures before
a checkpoint cannot resume. Complete/partial runs replay their saved admitted records. Partial-run
failures stay visible: replay does not repair malformed records. Fix input and make a fresh run to
correct them. Interrupted writes use atomic JSON replacement; a hard process kill that leaves an
untracked partial output is rejected by integrity validation and may need manual recovery.

Resume/review/export requires the run's original software version. Keep the old v0.1.0 environment
for modifying its runs; v0.2.0 can validate them and reproduce the unchanged flagship reference.

Optional public USGS caching:

```bash
ree run --config configs/examples/usgs_historical_check.yml --live --cache-dir ree-cache
ree cache status --cache-dir ree-cache
ree run --config configs/examples/usgs_historical_check.yml --live --cache-dir ree-cache --cache-mode only
ree cache clear --cache-dir ree-cache
```

The default cache TTL is one hour. `reuse` uses a fresh hit; `refresh` requests new content; `only`
refuses network fallback and fails without a fresh hit. The CLI has no custom TTL flag. Retrieved
URL, original retrieval time and body hash remain in provenance. Cache corruption fails visibly;
inspect or clear it. Clear deletes only named REE catalog entries, not runs or unrelated files.
Cache is opt-in and never stores local private inputs. Cache-only use requires a previously successful
permitted acquisition. It is not the permanent frozen archive: preserve a completed run for that.

```bash
ree compare RUN_A RUN_B
ree --log-level INFO demo
ree --log-level DEBUG run --config my-project/project.yml
```

Comparison validates both runs and reports count differences, source additions/removals, grade and
location distributions, and collection outcomes. Use complete saved runs. It does not establish
live-source completeness. Logging supports DEBUG, INFO, WARNING and ERROR; run timing and reasons
are also recorded in manifests/logs. Keep private run files private when collecting diagnostics.

## 14. Examples and paths for different users

| User | First path |
| --- | --- |
| Graduate student | Install → demo → read report → reproduce → init a project |
| GIS researcher | Install gis/columnar extras → export a run → inspect CRS, null geometry and precision |
| NGO analyst | Run the shared synthetic CSV example → inspect contextual review → apply justified decisions |
| Adapter developer | Read MAINTAINER_MANUAL.md → run external_adapter/run_example.py → add contract tests |

The flood example reuses `configs/examples/bangladesh_excerpt.yml`. Additional configuration-only
examples are `examples/cyclone_monitoring/project.yml`, `examples/custom_csv/project.yml` and
`examples/custom_csv/kenya.yml`. They share one explicitly synthetic CSV; no real corpus upload is needed.
The Kenya example deliberately leaves Mombasa unresolved rather than inventing a point.

## 15. Performance and current verification limits

Default budget is 100 records; maximum is 1,000. Text matching and event proposals remain quadratic.
CSV/JSONL use streaming reads; Parquet reads batches. JSON, XML, GeoPackage and normalized processing
still use bounded in-memory objects. A 100-record synthetic stress profile found avoidable repeated
provenance: duplicate decisions now reference just their two contributing documents. This lowered
traced peak allocation from about 174 MB to 44 MB in that test. Profiling includes overhead and
is not a production throughput or large-data guarantee. Keep studies small and split large corpora.

The current dependency-free test runner (after core installation) is:

```bash
python -m unittest discover -s tests -p test_operations.py -v
```

It uses Python's standard unittest library. The full existing pytest suite, Ruff and optional-format
checks are separate gates; do not infer their current results from the operational test count.
See OPERATIONAL_AUDIT.md, REPRODUCIBILITY_REPORT.md and RELEASE_READINESS.md before publishing results.
