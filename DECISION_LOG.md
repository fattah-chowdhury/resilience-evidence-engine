# Decision log
Date: 2026-09-07; version: 0.1.0.dev0

| Choice | Alternatives | Reason / tradeoff |
| --- | --- | --- |
| Software controller supersedes old manual | Manuscript intake | Latest supplied instruction explicitly requires zero attachments and software |
| SQLite first | DuckDB/PostgreSQL | Built-in transactional relations; analytical scale deferred |
| argparse CLI | Click/Typer | Standard-library bootstrap keeps optional installation small; migration possible |
| Pydantic + safe YAML | Hand-built validation | Clear errors and typed schema; two dependencies |
| No heavy NLP/GIS dependency yet | Full requested stack | Add only with tested features; current package cannot perform extraction |
| Synthetic test fixtures only | Synthetic public demo | Avoid fabricated empirical evidence |
| USGS structured source candidate | ReliefWeb-only default | Useful separate transport reference; not a substitute for narrative climate use case |
| Unknown rights disable operations | Assume public means open | Conservative provider/item-level permission handling |
| No publication | Auto-create public repository | Public release needs user authorization and rights audit |

## v0.1.0 implementation decisions — 2026-09-07

- Preserve the recovered Stage 0–1 snapshot; develop a new working release from it.
- Build a deliberately small vertical slice before expanding: SQLite, stdlib CLI/HTTP,
  Pydantic and YAML. Optional GIS/columnar/Excel dependencies remain extras.
- Freeze a curated public-facts sample and short attributed excerpts. This is an
  editorial extraction from official pages/search-indexed official fields, NOT a
  captured API response. The API fetch was unavailable through the research tool.
  Keep acquisition method, source URL, reviewed date and sample hashes explicit.
- Include a Bangladesh flood excerpt with unresolved time and ambiguous Sylhet
  geography. Do not add fabricated administrative centroids to make a prettier map.
- Noto's rounded finite-fault starting hypocenter is a model reference, marked
  representational; it is not the final epicenter or an uncertainty radius.
- Auto-link only a shared provider event key with matching category and origin group.
  Identical text alone is copy evidence; other nearby claims are proposals for review.
  Source-independence groups and copied text constrain corroboration.
- Review decisions create a new run; original outputs and decision history survive.
- Scope the first release as experimental v0.1.0, with explicit stage limitations.
  No production readiness, multilingual accuracy, successful live API collection,
  desktop GIS QA or public release will be claimed without executing those gates.

## Verification and release decisions — 2026-09-07

- Completed fields in the recovered baseline were preserved; bootstrap statements were changed only
  where actual implementation/verification proved them stale. The original source ZIP remains historical.
- Claim decisions and accepted/rejected event-link proposals produce new immutable child runs. Sequential
  merges preserve provider/original identities and earlier decisions. No in-place rewriting of past runs.
- Parquet uses explicit SQL-derived types; GeoPackage has two WGS84 layers and retains null geometry.
  Python reader checks are executed separately from uninstalled QGIS/R desktop environments.
- Export reports link to a format actually present. Live failures now retain attempted adapter provenance;
  the earlier real DNS-failure manifest remains unchanged as historical evidence of the actual attempt.
- Keep a maximum of 1,000 records and mark truncation partial; full pagination/caching/resume is deferred.
  This bounds an intentionally simple quadratic duplicate/link implementation without implying scale.
- Installation uses a new venv without system-site-packages. Existing interpreter dependencies must not
  be mistaken for a complete dependency-isolated installation test.
- Advisory lookup was interrupted by network approval cancellation; inventory and code-boundary checks
  remain useful, but zero known vulnerabilities cannot be claimed. No blocked audit route was bypassed.
- Configuration paths may be present in public metadata. Whole-record suppression is implemented;
  automatic PII detection, anonymization and spatial masking are deferred and documented.
- Deliver a source/wheel archive and final manual with truthful release gates. Local Git history records
  this continued implementation; the earlier archive supplies its historical baseline. No remote, owner
  identity or earlier Git commits are invented.
- Remain experimental v0.1.0. Full master-controller acceptance cannot be claimed while real live access,
  online advisory review and actual QGIS/R verification remain open. MASTER PROMPT 2 can audit/extend this
  concrete checkpoint; it should not assume those gates passed.
