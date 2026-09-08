# Resilience Evidence Engine

REE turns permitted source records into traceable claims, uncertain place/time interpretations,
candidate events, review queues and GIS files. It is a local Python application: no private dataset,
API key, server or paid AI subscription is required for the bundled offline demo.

**Experimental v0.1.0.** The offline workflow works; this is not a validated hazard-monitoring service.
See [release readiness](RELEASE_READINESS.md) for executed checks and remaining external gates.

## Try it

With Python 3.11+ installed, extract the release and open a terminal in `resilience-evidence-engine`:

```bash
python -m venv .venv
```

Activate on macOS/Linux with `source .venv/bin/activate`, or Windows PowerShell with
`.venv\Scripts\Activate.ps1`. Then:

```bash
python -m pip install .
ree demo
ree reproduce flagship
ree init my-project
ree run --config my-project/project.yml
```

Each processing command prints its new run directory and HTML report path. Open the report in a browser.
Dependencies need internet on first installation; the demo and frozen reproduction do not.
REE has **not been published to PyPI**. Install this source directory or the supplied wheel, not its package name alone.

## What works

- Strict YAML studies; offline, local, explicit live and hybrid modes.
- JSON/JSONL, CSV/TSV, text, HTML, RSS/Atom, GeoJSON; optional Excel, Parquet and GeoPackage ingestion.
- Deterministic rules, configurable taxonomy/gazetteer/evidence indicators, explicit unknowns and review queues.
- Separate source/document/claim/location/event records in SQLite; hashes and field-level transformation records.
- Document duplicate detection, conservative provider event grouping, reviewable event-link proposals.
- Claim and event-link review creates a new run with decision history.
- CSV, JSON, GeoJSON, optional Parquet/GeoPackage; offline coordinate plot and searchable HTML report.
- Curated discovery and one bounded USGS API adapter. Actual live verification was blocked by DNS here.
- Frozen regression, integrity validation, installable wheel, automated tests and CI configuration.

The reference contains **four real-source records, five claims, four candidate events and twelve pending
review items**. It combines curated official earthquake facts and short attributed USGS/NASA excerpts.
It is not a captured API dataset, a multilingual accuracy benchmark, or an inventory of Bangladesh floods.
Two events have point representations; two retain null geometry. The Noto point is a representational
model reference. See [source strategy](SOURCE_STRATEGY.md) and [the user manual](docs/USER_MANUAL.md).

## Optional formats and development

```bash
python -m pip install '.[excel,columnar,gis]'
python -m pip install -e '.[dev,excel,columnar,gis]'
python -m pytest -q
python -m ruff check src tests
```

`requirements-core.lock` and `requirements-all.lock` record tested Linux/Python 3.12 dependency versions;
they are not universal cross-platform or cryptographic locks. For the tested core versions:

```bash
python -m pip install -r requirements-core.lock
python -m pip install --no-deps .
```

## Documentation and rights

Start with [USER_MANUAL.md](docs/USER_MANUAL.md). Architecture, data model, source policy, project state,
test evidence and a maintainer guide are included. New code is MIT licensed; external facts/excerpts
retain their stated source rights. Sensitive or unapproved local records are suppressed in public mode.
Private mode keeps permitted local content: review its outputs before sharing. No remote repository,
DOI, public release, authorship or affiliation is invented by this build.
