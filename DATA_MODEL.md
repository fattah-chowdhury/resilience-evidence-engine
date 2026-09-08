# Data model

Version 0.1.0 · schema version 1

Stable identifiers use SHA-256 over canonical JSON arrays with an entity namespace and immutable inputs.
Identity is not evidence of truth or independent corroboration. See src/ree/schema.sql for exact columns.

| Entity | Relationship | Semantics |
| --- | --- | --- |
| source | source_id | Provider, origin group and rights/access metadata |
| document | document_id → source | Versioned source record, content hash, normalized text and input metadata |
| claim | claim_id → document | Statement/category, time interval/precision, normalized span and method |
| location | location_id → parent location | Name/hierarchy, optional geometry, precision and representational flag |
| claim_location | claim + location | Multiple candidate/selected interpretations; composite primary key |
| event | event_id | Candidate interpretation and aggregate uncertainty, never ground truth |
| event_claim | event + claim | Membership method and review state; composite primary key |
| assessment | assessment_id → claim | Separate indicators, grade, processing decision and rule version |
| review | review_id → claim | Reason and pending/accepted/rejected status |
| review_decision | decision_id → review | Reviewer, decision, note, selected location, timestamp and decision-file hash |
| document_duplicate | document + document | Identical/near-copy label and similarity; distinct from event identity |
| provenance | provenance_id | Target entity/key/field, transformation input/config/rule and value hashes |

Event-link decisions also live in the replay and provenance/event_link_reviews.json. Relevant histories
are attached to event metadata; no separate claim review ID is invented for event merges. Decisions and
new event groups are persisted in a new child run, preserving original files and parent linkage.

## Enforced invariants
Primary keys and child references resolve; parent location hierarchies cannot cycle or contradict country.
Nonexcluded claims link to events; events are not orphaned; claims have assessments. Geometry must be
valid 2D Point/Polygon/MultiPolygon in WGS84, longitude first. Points and quantities require finite numeric
values and plausible coordinate bounds. Polygons need the optional GIS validator. Missing geometry stays null.

Unknown dates remain null; month/week/range/relative precision is explicit. Invalid or conflicting dates
are unresolved rather than converted to publication dates. Centroids/model references are representational.
Time overlap or spatial proximity alone does not establish event identity. Near copies do not create
independent source support. Seven evidence dimensions remain separate; grades are not probabilities.

Field provenance coverage, target existence, composite keys and output-value hashes are validated in
addition to SQL integrity/foreign keys. Record metadata captures admitted input representations and
file/record hashes. Original external source files remain user-owned; REE does not copy arbitrary files
into public outputs or guarantee preservation of every original container byte.

## Exports and evolution
SQL JSON-valued columns stay JSON strings in CSV/Parquet. JSON exports retain the normalized table schema;
GeoJSON has nested properties and null geometry, while GeoPackage stores nested values as JSON text.
No binary equality of SQLite/Parquet/GPKG is promised. Frozen regression compares canonical sorted tables.
Each run uses a fresh schema; production migration machinery and stable public Python APIs are deferred.
