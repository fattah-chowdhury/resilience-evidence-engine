CREATE TABLE IF NOT EXISTS source (
 source_id TEXT PRIMARY KEY NOT NULL, provider TEXT NOT NULL,
 origin_group TEXT, rights_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS document (
 document_id TEXT PRIMARY KEY NOT NULL,
 source_id TEXT NOT NULL REFERENCES source(source_id),
 source_record_id TEXT NOT NULL, content_hash TEXT NOT NULL,
 text TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS claim (
 claim_id TEXT PRIMARY KEY NOT NULL,
 document_id TEXT NOT NULL REFERENCES document(document_id),
 statement TEXT NOT NULL, category TEXT, start_date TEXT, end_date TEXT,
 temporal_precision TEXT NOT NULL DEFAULT 'unknown'
 CHECK(temporal_precision IN ('exact','month','week','range','relative','unknown')),
 metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS location (
 location_id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL,
 parent_id TEXT REFERENCES location(location_id), geometry_json TEXT,
 precision TEXT NOT NULL DEFAULT 'unknown',
 representational INTEGER NOT NULL DEFAULT 0 CHECK(representational IN (0,1))
);
CREATE TABLE IF NOT EXISTS claim_location (
 claim_id TEXT NOT NULL REFERENCES claim(claim_id),
 location_id TEXT NOT NULL REFERENCES location(location_id),
 status TEXT NOT NULL CHECK(status IN ('candidate','selected','rejected')),
 PRIMARY KEY(claim_id, location_id)
);
CREATE TABLE IF NOT EXISTS event (
 event_id TEXT PRIMARY KEY NOT NULL, category TEXT,
 start_date TEXT, end_date TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS event_claim (
 event_id TEXT NOT NULL REFERENCES event(event_id),
 claim_id TEXT NOT NULL REFERENCES claim(claim_id),
 method TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 PRIMARY KEY(event_id, claim_id)
);
CREATE TABLE IF NOT EXISTS assessment (
 assessment_id TEXT PRIMARY KEY NOT NULL,
 claim_id TEXT NOT NULL REFERENCES claim(claim_id), indicators_json TEXT NOT NULL,
 grade TEXT CHECK(grade IN ('A','B','C','D','X')),
 decision TEXT NOT NULL CHECK(decision IN ('AUTO_ACCEPT','REVIEW','REJECT')),
 rule_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance (
 provenance_id TEXT PRIMARY KEY NOT NULL, entity TEXT NOT NULL,
 entity_id TEXT NOT NULL, field TEXT NOT NULL, transformation_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review (
 review_id TEXT PRIMARY KEY NOT NULL, claim_id TEXT NOT NULL REFERENCES claim(claim_id),
 reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected'))
);
CREATE INDEX IF NOT EXISTS idx_document_source ON document(source_id);
CREATE INDEX IF NOT EXISTS idx_claim_document ON claim(document_id);
CREATE INDEX IF NOT EXISTS idx_event_claim_claim ON event_claim(claim_id);
CREATE TABLE IF NOT EXISTS document_duplicate (
 left_document_id TEXT NOT NULL REFERENCES document(document_id),
 right_document_id TEXT NOT NULL REFERENCES document(document_id),
 kind TEXT NOT NULL, similarity REAL NOT NULL,
 PRIMARY KEY(left_document_id, right_document_id)
);
CREATE TABLE IF NOT EXISTS review_decision (
 decision_id TEXT PRIMARY KEY NOT NULL, review_id TEXT NOT NULL REFERENCES review(review_id),
 reviewer TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('accepted','rejected')),
 note TEXT NOT NULL, location_id TEXT REFERENCES location(location_id),
 decided_at TEXT NOT NULL, decision_file_hash TEXT NOT NULL
);
