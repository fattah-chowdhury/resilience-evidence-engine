# Architecture

## Local modular pipeline
CLI → strict configuration → acquisition → normalized records → extraction/place/time resolution →
copy detection and candidate linkage → evidence assessment → review → relational/GIS/report exports.

SQLite remains the authoritative relational representation, with foreign keys enabled and separate
source, document, claim, location, event, assessment, review and provenance entities. CSV/JSON/Parquet
are views. Pydantic/YAML are core dependencies; GIS, columnar and Excel libraries are optional extras.
The existing argparse decision is preserved. No web server, proprietary AI or external database is needed.

Modules are config, models, sources, ingestion, resolution, linkage, evidence, pipeline, storage, review
and exporters. SourceAdapter is an internal Python protocol. LocalGazetteer is the reference resolver;
configurable assets substitute names/hierarchies/geometry, taxonomies and evidence rules. Third-party
entry-point packaging, automatic plugin discovery and LLMProvider execution are deferred.

## Run lifecycle and continuity
A processing command creates one new directory exclusively, records a running manifest, executes the
pipeline, validates/saves the SQLite tables and exports files, then records succeeded/partial/failed.
Malformed rows are quarantined by reason; fatal errors retain a manifest. Pre-run config errors and
read-only helper commands do not create evidence runs. Each run owns a fresh schema.

Review/export validates an existing run and reprocesses its captured input/config/assets into a child
run. Old databases are read-only. Completed runs never change in place. This is replay, not a resumable
multi-stage job engine: a failed run remains evidence of failure and a corrected retry gets a new ID.
Live pagination checkpoints, cross-run mutable stores and migrations remain future work.

## Identity and provenance
Stable IDs use namespaced canonical SHA-256 inputs. Input versions/content hashes are distinct from
provider event identity. Source origin groups and copy similarity constrain independent corroboration.
Automatic event grouping requires a common provider key/category/origin; spatial/time similarity only
proposes links. Reviewed merges preserve decision history and establish new event identities.

Every stored non-provenance field has a transformation record with full target primary key, value hash,
module/version and input/config/rule fingerprints. Some fields use the whole contributing input set;
claim offsets explicitly refer to normalized text. Operational run IDs/timestamps/paths and incidental
SQLite binary bytes are outside the stable dataset comparison. All output files are separately hashed.
Manifests are unsigned and are an integrity aid, not protection from a hostile rewrite of data and manifest.

## Security and privacy
Local HTML is stripped, never executed; DTD/entities and unsafe YAML are refused. HTTP only targets the
registered USGS HTTPS catalog endpoint, checks public DNS, refuses redirects, enforces size/time/retry
limits and never follows arbitrary record URLs. Address pinning across DNS check and connection is a
future hardening task; do not describe this as a general-purpose secure scraper.

Private mode retains permitted local content. Public mode suppresses sensitive/unapproved records before
all persistence and replay; config metadata may still contain local paths and must be inspected before
sharing. There is no automatic PII classifier or disclosure-proof masking. HTML is escaped; CSV strings
that could execute spreadsheet formulas are neutralized. No downloaded model/code or pickle is loaded.

## Deployment
Local source/wheel first. Docker files are supplied but unexecuted here. No hosting configuration, remote
repository or PyPI publication is created implicitly. CI jobs are defined separately from local evidence.
