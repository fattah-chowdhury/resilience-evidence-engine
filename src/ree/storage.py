"""Normalized relational storage and deterministic identity."""

import json
import sqlite3
from hashlib import sha256
from importlib.resources import files


def stable_id(namespace: str, *parts: str) -> str:
    if not namespace or any(not isinstance(x, str) for x in parts):
        raise ValueError("Identity namespace and parts must be strings")
    value = json.dumps([namespace, *parts], ensure_ascii=False, separators=(",", ":"))
    return namespace + "_" + sha256(value.encode("utf-8")).hexdigest()


def schema_sql() -> str:
    return files("ree").joinpath("schema.sql").read_text(encoding="utf-8")


def connect(path=":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema_sql())
    return connection


TABLES = ["source", "document", "claim", "location", "claim_location", "event", "event_claim",
          "assessment", "review", "review_decision", "document_duplicate", "provenance"]

PRIMARY_KEYS = {"source": ["source_id"], "document": ["document_id"], "claim": ["claim_id"],
                "location": ["location_id"], "claim_location": ["claim_id", "location_id"],
                "event": ["event_id"], "event_claim": ["event_id", "claim_id"],
                "assessment": ["assessment_id"], "review": ["review_id"],
                "review_decision": ["decision_id"],
                "document_duplicate": ["left_document_id", "right_document_id"]}


def save_tables(path, tables):
    db = connect(path)
    try:
        with db:
            for table in TABLES:
                for row in tables[table]:
                    keys = list(row)
                    db.execute(f"INSERT INTO {table} ({','.join(keys)}) VALUES "
                               f"({','.join('?' for _ in keys)})", [row[k] for k in keys])
        problems = validate_database(db)
        if problems:
            raise ValueError("; ".join(problems))
    finally:
        db.close()


def validate_database(db):
    from datetime import date

    from ree.models import canonical, check_geometry, digest

    problems = []
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        problems.append("SQLite integrity failure")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        problems.append("Broken foreign-key references")
    for table in ("claim", "event"):
        for start, end in db.execute(f"SELECT start_date,end_date FROM {table}"):
            try:
                if bool(start) != bool(end) or (start and date.fromisoformat(start) > date.fromisoformat(end)):
                    problems.append(f"Invalid interval in {table}")
            except ValueError:
                problems.append(f"Invalid date in {table}")
    for geometry, precision, representational in db.execute(
            "SELECT geometry_json,precision,representational FROM location"):
        try:
            check_geometry(json.loads(geometry) if geometry else None)
            if geometry and precision in {"admin_centroid", "model_reference", "unknown"} and not representational:
                problems.append("Unmarked representational geometry")
        except ValueError:
            problems.append("Invalid location geometry")
    covered = set()
    for entity, entity_id, field, transform in db.execute(
            "SELECT entity,entity_id,field,transformation_json FROM provenance"):
        if entity not in TABLES or entity == "provenance":
            problems.append("Invalid provenance entity")
            continue
        data = json.loads(transform)
        key = data.get("target_key", {})
        columns = {x[1] for x in db.execute(f"PRAGMA table_info({entity})")}
        if set(key) != set(PRIMARY_KEYS[entity]) or field not in columns:
            problems.append("Invalid provenance target key or field")
            continue
        found = db.execute(f"SELECT {field} FROM {entity} WHERE " +
                           " AND ".join(k + "=?" for k in key), list(key.values())).fetchone()
        if not found:
            problems.append("Broken provenance target")
        elif digest(found[0]) != data.get("output_value_hash"):
            problems.append("Provenance value hash mismatch")
        covered.add((entity, canonical(key), field))
    for entity, primary_columns in PRIMARY_KEYS.items():
        columns = [x[1] for x in db.execute(f"PRAGMA table_info({entity})")]
        for values in db.execute(f"SELECT * FROM {entity}"):
            row = dict(zip(columns, values))
            key = canonical({k: row[k] for k in primary_columns})
            if any((entity, key, c) not in covered for c in columns):
                problems.append("Missing field provenance")
    if db.execute("SELECT event_id FROM event EXCEPT SELECT event_id FROM event_claim").fetchall():
        problems.append("Orphan events")
    if db.execute("SELECT claim_id FROM claim EXCEPT SELECT claim_id FROM assessment").fetchall():
        problems.append("Claims missing evidence assessments")
    if db.execute("SELECT claim_id FROM assessment WHERE decision!='REJECT' EXCEPT "
                  "SELECT claim_id FROM event_claim").fetchall():
        problems.append("Nonexcluded claims missing candidate events")
    return sorted(set(problems))
