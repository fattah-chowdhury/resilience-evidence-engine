# Verification report

Executed 2026-09-07, Linux x86_64, Python 3.12.13. Machine-readable evidence is in audit/.

## Executed checks

| Check | Result and scope |
| --- | --- |
| Full source suite | PASS — 93 passed, 0 failed, 0 skipped; 2.57 seconds with runtime extras |
| Ruff 0.16.6 | PASS — all checks passed |
| Core dependency installation | PASS — six pinned runtime dependencies installed into a new venv |
| Current wheel installation | PASS — no-index/no-deps install into that venv; no system-site-packages |
| Installed CLI outside source tree | PASS — version, doctor, demo, validate run/config, init/run, reproduce and JSON-only export |
| Frozen comparison | PASS — original version, fixture hash, canonical dataset hash and counts match |
| GIS/Parquet/Excel interoperability | PASS — actual Python readers, typed Parquet, both GPKG layers, null/empty GIS outputs and Excel ingestion |
| Review continuity | PASS — original run hashes preserved, claim decisions validated, sequential event merges and rejected links retained |
| Privacy/output injection | PASS — sensitive canary suppression across output files, local source identity separation, HTML escaping and CSV formula protection |
| Live mocked transport | PASS — allowlisted endpoint, DNS/redirect refusal, bounded retries/size, invalid records, truncated query and explicit flag |
| Real live query | BLOCKED — DNS resolution failure, exit 2; failure manifest preserved |
| Dependency advisory service | BLOCKED — network approval cancellation; vulnerability status unknown |

One full-suite warning: a generic GeoPackage ingestion/read check chooses the first layer (`locations`)
when two layers exist. This is documented reader behavior, not an omitted format test. Explicit event
and location export checks select each layer separately. No warning was silently reclassified as an API result.

## Important coverage

Tests cover strict/unsafe/duplicate YAML, stable IDs, foreign keys and orphan records; point/polygon/date
validation; ambiguous place candidates and hierarchy conflicts; exact/month/range/relative/unknown time;
small Bangla digit/keyword cases; malformed JSONL/CSV/XML, budgets and optional file readers; determinism
under input order; reference expectations; provenance coverage/value targets; accidental output tampering;
review IDs/history, source independence, copy handling, conflicting quantities and no silent live fallback.
Synthetic edge cases are labelled tests, not empirical demonstration data.

## Frozen expectations retained

- REE version: 0.1.0
- Fixture hash: fe448abfb48081e8335d778715881da9857c8669b53addc7decf4b3df883a93c
- Dataset hash: 30ab2d817c01197c3bc2b83c9b8e3bdd0531c3422deb70cc9977704b615032de
- Counts: acquired 4, documents 4, claims 5, candidate events 4, pending reviews 12.
- Four grade C claims and one D; two point representations, two null geometries.

The reference was inspected during its original creation and retained across later runs. It is not an
independently annotated scientific benchmark. Dataset equality excludes incidental run times/IDs and
binary container bytes; GIS semantics have separate tests. Configuration-specific exports can produce
different provenance/config hashes even when their core evidence is unchanged.

## Reproduce these checks

```bash
python -m pip install -e '.[dev,excel,columnar,gis]'
python -m ruff check src tests
python -m pytest -q
ree reproduce flagship
```

For the isolated install, the build used `python -m venv CLEAN_ENV`, installed requirements-core.lock,
installed the wheel with `--no-index --no-deps`, unset PYTHONPATH and ran commands from a different
directory. audit/installation-smoke.json records command exits, outputs and installed-module location.

## Unexecuted environments / residual risk

Python 3.11, Windows/macOS, R/sf, QGIS desktop, Docker and hosted CI were not run. CI and Docker assets
are supplied, not claimed successful. Online vulnerability findings remain unknown. No performance,
multilingual accuracy, scientific completeness, independent annotation or operational hazard-safety
benchmark was performed. The earlier bootstrap tests/install evidence remains historical, not a substitute
for the current isolated-wheel gate. See RELEASE_READINESS.md for acceptance status.
