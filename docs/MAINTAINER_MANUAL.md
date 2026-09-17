# Maintainer manual

Version 0.2.0 · 2026-09-09

## Resume safely

Read PROJECT_STATE.md, RELEASE_READINESS.md and DECISION_LOG.md. Inspect Git status before changing
anything. The recovered Stage 0–1 archive was preserved separately; this repository is the continued
implementation. Do not import another scratch checkout or regenerate frozen expected outputs to mask drift.
Tests with a `PYTHONPATH=src` setting exercise source code; installation gates must use the wheel from
outside the repository without that setting. Avoid mistaking a stale installed wheel for current source.

## Develop and verify

```bash
python -m pip install -e '.[dev,excel,columnar,gis]'
python -m ruff check src tests
python -m pytest -q
ree reproduce flagship
```

Optional tests skip when readers are absent. The release test installs all runtime extras and runs them.
CI has core Python 3.11/3.12 jobs and a separate optional-format job, without live network or secrets in
the actual demo/tests. Workflow execution still needs a remote repository; a YAML file is not a CI run.

Build source and wheel using `python -m build` after installing the build frontend. With an existing
setuptools/wheel environment, the audited equivalent is:

```bash
python -c "import setuptools.build_meta as b; b.build_sdist('dist'); b.build_wheel('dist')"
```

Install the wheel in a new venv without system-site-packages and execute README commands from another
directory. Inspect the sdist/wheel for SQL and all assets. Keep `audit/` evidence and TEST_REPORT.md
consistent with actual commands. Only broaden tests to resolve a concrete risk or release gate.

## Module contracts

| Module | Responsibility |
| --- | --- |
| config / models | Strict safe configuration and canonical record/geometry validation |
| sources / ingestion | Registry selection, bounded USGS transport, local-format normalization |
| resolution | Hierarchical local gazetteer, explicit time uncertainty, rule extraction |
| linkage | Document-copy-aware independent support, provider identity and reviewed merges |
| evidence | Separate rule-based indicators, grades and routing |
| pipeline | Acquisition, immutable run orchestration, normalized tables, replay and provenance |
| storage / schema.sql | SQLite constraints, stable IDs, sorted tables and integrity checks |
| review | Validate existing run; validate decision files; produce child run |
| exporters | Relational CSV/JSON/Parquet, GeoJSON/GPKG, escaped offline report |
| cli | Only implemented commands and honest exit statuses |

SourceAdapter defines discover, collect, normalize, validate and provenance. Add a provider by creating
an implementation, adding rights/access metadata to the registry, registering it explicitly through `run(..., adapters={id: factory}, source_registry=[metadata])` and adding transport/normalization/failure tests. Never enable an arbitrary URL or install-time
code discovery by default. Provider identity is distinct from publication/channel identity.

The current HTTP client uses a fixed HTTPS host/path, public DNS checks and redirect refusal. It does
not pin resolved addresses across the separate urllib connection; retain HTTPS verification and treat
strong adversarial DNS-rebinding hardening as future work. Response-size and record budgets are bounded;
this is a small-data engine, not an exhaustive catalog crawler. Acquisition checkpoints can resume completed input/source batches.

## Configurable assets

Taxonomy is an object mapping category name to nonempty keyword strings. Extraction is heuristic;
adding keywords does not demonstrate measured precision/recall. Evidence rules accept exactly
version, auto_accept_min_extraction, grade_a_min_independent_groups (>=2),
allow_auto_accept_relative and description. Keep versioned semantics and test reasons, not just grades.

Gazetteer is a list of records with id, name, aliases, country, level, parent_id and optional geometry,
representational, source_url and rights. IDs and parents must be valid; cycles/cross-country parents
fail. Geometry uses WGS84. Source-reported points are not interchangeable with administrative centroids.
Never assign an unmarked centroid to a vague name. Inspect `assets/gazetteer.json` for the exact
reference schema. It is a tiny demonstrator, not an authoritative global administrative service.

LLM calls and installable plugin discovery are deliberately absent; configuration rejects LLM enablement.
Third-party packages can later implement stable source/geocoder/NLP/exporter interfaces. Do not advertise
entry-point installation or alternative-model registration before implementing and testing it.

## Frozen reference and schema changes

`assets/frozen.json` stores the only canonical reference input. `assets/expected.json` records its
independently retained regression expectations. A semantic change requires inspecting the resulting
claims/events, recording why the previous behavior was wrong, and versioning the reference deliberately.
Do not count synthetic unit fixtures as empirical data or accuracy results. Store source URLs, rights
basis and transcription method for every new record. The source-specific accuracy of curated facts
should be checked again before a scientific use; this build is not an independently annotated benchmark.

Each run owns a fresh SQLite schema. Review/export operates through a validated replay and writes a
child run; never migrate an old evidence database in place. Long-lived database migrations and stable
public API contracts are deferred. Review revisions branch from an earlier parent, preserving history.
Code_commit may be null in installed wheels; package_code_hash fingerprints source and assets.

## Privacy, dependency and release checks

Public-mode suppression happens before storage/replay/export. Test canaries across the entire output
folder, not only the main table. Do not automatically treat public web access as redistribution rights.
Never put credentials or private records into fixtures, exceptions, logs or archives. .env.example
contains documentation only; no connector needs a secret for the current default workflow.

Version pins cover the actual project dependency graph and runtime extras, not every unrelated package
in the build machine. `pip-audit -r requirements-all.lock --no-deps --disable-pip --strict` checks those
pins against its advisory service; record failures and scope. A clean audit is not a security guarantee.

Docker assets are a convenience and remain unexecuted until a Docker host is available. Before claiming
all master-controller gates passed, close live USGS acceptance and actual QGIS/R interoperability,
then rerun release gates only where needed. This operations run did not publish to GitHub, PyPI or a DOI service. A public
release needs a real owner/repository identity, approved author/citation metadata and destination.


## v0.2.0 operational contracts

`cache.py` owns only public USGS response cache entries. `integrity.py` validates complete inventories,
relational schema/counts, semantic dataset fingerprints, categories, event links, geometry and provenance.
`operations.py` exposes resume_run and compare_runs. Saved-run replay is version-strict.
New run(config, ..., adapters={id: factory}, source_registry=[source]) allows explicit trusted Python
extensions without core edits. Each adapter supplies discover, collect, normalize, validate and provenance.
Collect returns (Record-compatible objects, structured errors); the boundary revalidates source IDs,
storage rights, suitability, budgets and JSON provenance. No automatic executable imports from YAML.
The complete external example is under examples/external_adapter. It is synthetic and never proves live access.

Run the standard-library tests with `python -m unittest discover -s tests -p test_operations.py -v`.
The existing pytest suite also discovers this unittest class when dev dependencies are installed.
No line-coverage percentage is claimed. CI definitions are configured but have not been run remotely here.

Reference reproduction keeps expected.json and frozen.json byte-for-byte unchanged. The original dataset
hash includes the provenance software version. v0.2.0 stores truthful current-version provenance and checks
a comparison copy with only transformation.ree_version set to the original version; raw hashes remain visible.
No other hash tolerance is permitted. New duplicate-pair provenance records cite just their two documents;
the reference has zero duplicate pairs, so that correction does not change reference evidence values.

For release verification, distinguish a completely fresh dependency install from an installed-wheel test
using preinstalled runtime dependencies. Current fresh network bootstrap and the restored pytest/GIS/Ruff
packages were blocked by network approval cancellation after workspace maintenance. Historical v0.1.0
93-test and clean-install evidence remains in audit/; current evidence belongs in audit/operations/.
Do not report those earlier results as a current full-suite pass. Build paths in the historical audit copy
are sanitized for distribution; the original v0.1.0 archive remains unchanged.
