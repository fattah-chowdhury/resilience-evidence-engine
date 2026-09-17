# REE release readiness — 0.2.0

2026-09-09 · **HOLD for a fully verified public release.** An experimental offline candidate is packaged.
MASTER PROMPT 2's operational work has been performed in the available environment, but all acceptance
gates have not passed. MASTER PROMPT 1's outstanding external gates are carried forward.

| Required gate | Result | Exact scope |
| --- | --- | --- |
| INSTALLATION | PARTIAL / BLOCKED | Current wheel installs/runs outside source with preinstalled system dependencies. Pristine dependency bootstrap was cancelled |
| CLI | PASS | Installed entry point, help, demo, reproduce and core workflow executed |
| DEMO | PASS | 4 documents, 5 claims, 4 events, 12 reviews; no user data, keys or network |
| FROZEN REPRODUCTION | PASS WITH DECLARED TOLERANCE | Original reference inputs/expectations unchanged; only provenance software-version string normalized for comparison |
| UNIT TESTS | PARTIAL / UNVERIFIED | 28 current unittest operational checks pass; current full pytest suite unavailable |
| INTEGRATION TESTS | PASS WITH LIMITS | Core recovery/cache/config/review/adapter paths pass; real live and optional readers unverified |
| DATA INTEGRITY | PASS | File inventory, database/schema/counts, taxonomy/links, geometry and hashes |
| PROVENANCE | PASS WITH LIMITS | Current input/config/rule/field hashes and child lineage; unsigned manifests |
| EXPORTS | PARTIAL / UNVERIFIED | Current CSV/JSON/point GeoJSON checks pass; current Parquet/GPKG/QGIS/R not executed |
| DOCUMENTATION | PASS WITH LIMITS | Core walkthrough checked; Windows/macOS and optional/environment-blocked commands labeled |
| SECRET SCAN | PASS WITH LIMITS | Current distributable source static patterns and local-path checks; no claim of exhaustive forensic scanning |
| LICENSING REVIEW | PASS WITH LIMITS | Narrow USGS/NASA facts/excerpt, original URLs, synthetic MIT fixtures; ReliefWeb disabled |
| Dependency advisories | BLOCKED | Online pip-audit did not return findings after network approval cancellation |
| Ruff | UNVERIFIED | Missing in current runtime; source syntax and whitespace checks pass |
| Actual live USGS | BLOCKED | DNS resolution failure in engine environment; no substitute records presented as live |
| Docker / hosted CI | UNVERIFIED | Configuration prepared; runtimes/hosted connection not exercised |
| External publication / DOI | NOT PERFORMED | No public publication or DOI action by this operations run |

## Practical installation

Extract the archive, open a terminal in resilience-evidence-engine, and run with Python 3.11+:

```bash
python -m venv .venv
```

Activate: macOS/Linux `source .venv/bin/activate`; Windows PowerShell `.venv\Scripts\Activate.ps1`.
Then:

```bash
python -m pip install .
ree demo
ree reproduce flagship
ree init my-project
ree run --config my-project/project.yml
```

If dependencies already exist, the supplied wheel can be installed without network using
`python -m pip install --no-index --no-deps artifacts/resilience_evidence_engine-0.2.0-py3-none-any.whl`
from the extracted release root. This does not install missing dependencies. No registry publication is
required; use the supplied source or wheel. Complete instructions: docs/USER_MANUAL.md.

## Actions needed before upgrading this status

1. In a permitted network environment, install into a pristine venv, then run the README commands.
2. Install development/runtime extras and execute `python -m pytest -q` and `python -m ruff check src tests`.
   Historical 93-test results are not a substitute for this current-code gate.
3. Run `ree run --config configs/examples/usgs_historical_check.yml --live`; inspect actual source
   records, request provenance, review queues and exports. Do not replace the frozen fixture.
4. Execute the Parquet/GPKG tests and import the exports with actual QGIS and R/sf.
5. Run dependency advisories, Docker and hosted CI. Review actual author/repository/release metadata
   before any public release or DOI registration. No invented author or DOI is included.

Known scope limits: tiny gazetteer; English/Bangla heuristics; bounded quadratic matching/proposal work;
no complete flood/cyclone live collector; no automatic PII anonymization; source-batch rather than
mid-processing resume; version-strict saved-run mutation; unsigned manifests and platform-specific pins.
