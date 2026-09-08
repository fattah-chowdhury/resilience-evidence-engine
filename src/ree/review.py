"""Review creates a new immutable run and carries forward the decision history."""

import csv
import json
import sqlite3
from hashlib import sha256

from ree import __version__
from ree.config import ProjectConfig
from ree.pipeline import run, timestamp
from ree.storage import validate_database


def validate_run(root):
    root = root.resolve()
    manifest = json.loads((root / "provenance/run_manifest.json").read_text(encoding="utf-8"))
    problems = []
    if manifest.get("status") not in {"succeeded", "partial"}:
        problems.append("Run is not a completed evidence dataset")
    for relative, expected in manifest.get("export_files", {}).items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            problems.append(f"Missing or unsafe output: {relative}")
        elif sha256(path.read_bytes()).hexdigest() != expected:
            problems.append(f"Changed output: {relative}")
    database = root / "data/evidence.sqlite"
    if database.exists():
        db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            problems.extend(validate_database(db))
        finally:
            db.close()
    else:
        problems.append("Missing SQLite evidence database")
    return manifest, problems


def load_replay(root):
    manifest, problems = validate_run(root)
    if problems:
        raise ValueError("; ".join(problems))
    snapshot = json.loads((root / "provenance/replay.json").read_text(encoding="utf-8"))
    if snapshot["ree_version"] != __version__:
        raise ValueError("Replay requires the original REE version")
    return manifest, snapshot


def apply_review(root, decisions_path, output=None):
    manifest, snapshot = load_replay(root)
    db = sqlite3.connect((root.resolve() / "data/evidence.sqlite").as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        reviews = {r["review_id"]: dict(r) for r in db.execute("SELECT * FROM review")}
        candidates = {}
        for row in db.execute("SELECT claim_id,location_id FROM claim_location"):
            candidates.setdefault(row["claim_id"], set()).add(row["location_id"])
    finally:
        db.close()
    if decisions_path.stat().st_size > 1000000:
        raise ValueError("Decision file exceeds 1 MB")
    decision_hash = sha256(decisions_path.read_bytes()).hexdigest()
    decisions = snapshot.get("decisions", {}).copy()
    seen = set()
    added = 0
    with decisions_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"review_id", "decision", "reviewer", "note"} <= set(reader.fieldnames or []):
            raise ValueError("Review CSV requires review_id, decision, reviewer, note")
        for row in reader:
            action = (row.get("decision") or "").strip().lower()
            if not action:
                continue
            rid = row["review_id"]
            if rid in seen or rid not in reviews:
                raise ValueError("Duplicate or unknown review_id")
            seen.add(rid)
            if rid in decisions:
                raise ValueError("A decision already exists. Start from its parent run to revise it.")
            if action not in {"accepted", "rejected"}:
                raise ValueError("decision must be accepted or rejected")
            if not row["reviewer"].strip() or not row["note"].strip():
                raise ValueError("Every decision requires a reviewer and explanatory note")
            cid = reviews[rid]["claim_id"]
            loc = (row.get("location_id") or "").strip()
            if loc and loc not in candidates.get(cid, set()):
                raise ValueError("location_id is not a candidate for this claim")
            if action == "accepted" and reviews[rid]["reason"] == "ambiguous_or_unknown_location" and not loc:
                raise ValueError("Accepting an ambiguous location requires a candidate location_id")
            decisions[rid] = {**reviews[rid], "decision": action, "reviewer": row["reviewer"].strip(),
                              "note": row["note"].strip(), "location_id": loc,
                              "decided_at": timestamp(), "decision_file_hash": decision_hash}
            added += 1
    if not added:
        raise ValueError("No new completed decisions were supplied")
    config = ProjectConfig.model_validate(snapshot["config"])
    return run(config, output=output, replay=snapshot, decisions=decisions, parent_run=manifest["run_id"],
               link_decisions=snapshot.get("link_decisions"))


def apply_event_links(root, links_path, output=None):
    manifest, snapshot = load_replay(root)
    if links_path.stat().st_size > 1000000:
        raise ValueError("Event-link decision file exceeds 1 MB")
    with (root / "review/possible_event_links.csv").open(encoding="utf-8", newline="") as f:
        proposals = {frozenset((r["left_event_id"], r["right_event_id"])) for r in csv.DictReader(f)}
    decisions = snapshot.get("link_decisions", []).copy()
    seen = {frozenset((d["left_event_id"], d["right_event_id"])) for d in decisions}
    file_hash = sha256(links_path.read_bytes()).hexdigest()
    added = 0
    with links_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"left_event_id", "right_event_id", "decision", "reviewer", "note"} <= set(reader.fieldnames or []):
            raise ValueError("Event links require left_event_id,right_event_id,decision,reviewer,note")
        for row in reader:
            action = (row.get("decision") or "").strip().lower()
            if not action:
                continue
            pair = frozenset((row["left_event_id"], row["right_event_id"]))
            if pair in seen or pair not in proposals:
                raise ValueError("Unknown or already decided event-link proposal")
            if action not in {"accepted", "rejected"} or not row["reviewer"].strip() or not row["note"].strip():
                raise ValueError("Each event link needs accepted/rejected, reviewer and a note")
            decisions.append({"left_event_id": row["left_event_id"], "right_event_id": row["right_event_id"],
                              "decision": action, "reviewer": row["reviewer"].strip(), "note": row["note"].strip(),
                              "decided_at": timestamp(), "decision_file_hash": file_hash,
                              "parent_run": manifest["run_id"]})
            seen.add(pair)
            added += 1
    if not added:
        raise ValueError("No completed event-link decisions supplied")
    config = ProjectConfig.model_validate(snapshot["config"])
    return run(config, output=output, replay=snapshot, decisions=snapshot.get("decisions"),
               parent_run=manifest["run_id"], link_decisions=decisions)
