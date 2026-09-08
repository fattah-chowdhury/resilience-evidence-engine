"""Run acquisition, evidence processing and export with explicit failure manifests."""

import json
import platform
import subprocess
import uuid
from datetime import UTC, datetime
from difflib import SequenceMatcher
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path

import yaml

from ree import __version__
from ree.config import UniqueKeyLoader
from ree.evidence import assess
from ree.exporters import export_all, file_hashes, preflight_exports, write_json
from ree.ingestion import ingest_file
from ree.linkage import group_claims
from ree.models import Record, canonical, digest
from ree.resolution import LocalGazetteer, extract, extract_quantities, resolve_time
from ree.sources import USGSAdapter, asset
from ree.storage import PRIMARY_KEYS, TABLES, save_tables, stable_id


class RunFailure(ValueError):
    def __init__(self, message, output):
        super().__init__(f"{message}. Failure manifest: {output / 'provenance/run_manifest.json'}")
        self.output = output


def timestamp():
    return datetime.now(UTC).isoformat()


def read_rules(path, fallback, base):
    if path is None:
        return asset(fallback)
    target = (base / path).resolve()
    if target.stat().st_size > 1000000:
        raise ValueError("Rules/gazetteer file exceeds 1 MB")
    return yaml.load(target.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def processing_assets(config, base):
    settings = config.processing
    bundle = {"taxonomy": read_rules(settings.taxonomy, "event_taxonomy.json", base),
              "gazetteer": read_rules(settings.gazetteer, "gazetteer.json", base),
              "evidence_rules": read_rules(settings.evidence_rules, "evidence_rules.json", base)}
    validate_assets(bundle)
    return bundle


def validate_assets(bundle):
    taxonomy, rules = bundle["taxonomy"], bundle["evidence_rules"]
    if not isinstance(taxonomy, dict) or not taxonomy or any(
            not isinstance(k, str) or not isinstance(v, list) or not v or
            any(not isinstance(x, str) or not x.strip() for x in v) for k, v in taxonomy.items()):
        raise ValueError("Taxonomy must map category names to nonempty keyword lists")
    if not isinstance(rules, dict) or set(rules) != {
            "version", "auto_accept_min_extraction", "grade_a_min_independent_groups",
            "allow_auto_accept_relative", "description"}:
        raise ValueError("Evidence rules have missing or unsupported fields")
    if not isinstance(rules["auto_accept_min_extraction"], (int, float)) or not (
            0 <= rules["auto_accept_min_extraction"] <= 1):
        raise ValueError("Extraction threshold must be between zero and one")
    if type(rules["grade_a_min_independent_groups"]) is not int or rules["grade_a_min_independent_groups"] < 2:
        raise ValueError("Grade A requires at least two independent groups")
    if type(rules["allow_auto_accept_relative"]) is not bool:
        raise ValueError("allow_auto_accept_relative must be Boolean")
    LocalGazetteer(bundle["gazetteer"])


def code_metadata():
    root = Path(str(files("ree")))
    payload = {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
               for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in {".py", ".sql", ".json"}}
    commit = None
    dirty = None
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=3, check=False)
        if result.returncode == 0:
            commit = result.stdout.strip()
            result = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                                    capture_output=True, text=True, timeout=3, check=False)
            dirty = bool(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"code_commit": commit, "code_dirty": dirty, "package_code_hash": digest(payload)}


def process_records(records, registry, config, bundle, decisions=None, link_decisions=None):
    decisions = decisions or {}
    link_decisions = link_decisions or []
    source_by_id = {r["id"]: r for r in registry}
    gazetteer = LocalGazetteer(bundle["gazetteer"])
    tables = {t: [] for t in TABLES}
    docs, claims, locations = {}, [], {}
    record_hashes = {}
    notices, failed = [], []
    used_sources = set()
    filtered = suppressed = repeated = 0
    by_country = config.study_area.country.casefold()

    def add_location(location):
        key = location["id"]
        if key in locations:
            return
        parent = location.get("parent_id")
        if parent:
            add_location(next(r for r in gazetteer.rows if r["id"] == parent))
        locations[key] = {"location_id": key, "name": location["name"], "parent_id": parent,
                          "geometry_json": canonical(location["geometry"]) if location.get("geometry") else None,
                          "precision": location.get("level", "unknown"),
                          "representational": int(location.get("representational", False))}

    for record in sorted(records, key=lambda r: (r.source_id, r.source_record_id, digest(r.model_dump()))):
        source = source_by_id.get(record.source_id)
        if source is None:
            raise ValueError("Record has an unregistered source")
        if config.export_policy == "public" and (
                record.sensitive or source.get("redistribution_allowed") is not True):
            suppressed += 1
            continue
        if record.language not in config.languages or (by_country != "global" and record.country
                                                       and record.country.casefold() != by_country):
            filtered += 1
            continue
        scope_warnings = []
        if config.study_area.bbox:
            geometry = record.geometry
            if geometry and geometry["type"] == "Point":
                w, s, e, n = config.study_area.bbox
                lon, lat = geometry["coordinates"]
                if not (w <= lon <= e and s <= lat <= n):
                    filtered += 1
                    continue
            else:
                scope_warnings.append("bbox_membership_unresolved")
        if by_country != "global" and not record.country and not config.study_area.bbox:
            scope_warnings.append("country_membership_unresolved")
        if config.study_area.admin_units and not any(
                u.casefold() in record.location_text.casefold() for u in config.study_area.admin_units):
            scope_warnings.append("admin_membership_unresolved")
        raw = record.model_dump(mode="json")
        content_hash = digest(raw)
        document_id = stable_id("document", record.source_id, record.source_record_id, content_hash)
        if document_id in docs:
            repeated += 1
            continue
        used_sources.add(record.source_id)
        try:
            text, extracted = extract(record, bundle["taxonomy"])
        except ValueError as error:
            failed.append({"record_hash": content_hash, "reason": str(error)})
            continue
        docs[document_id] = {"document_id": document_id, "source_id": record.source_id,
                             "source_record_id": record.source_record_id, "content_hash": content_hash,
                             "text": text, "metadata_json": canonical({"input_record": raw,
                                                                        "text_offsets": "normalized text"})}
        record_hashes[document_id] = content_hash
        if not extracted:
            notices.append({"document_id": document_id, "reason": "no_matching_claim"})
        for candidate in extracted:
            if candidate["category"] not in config.topics:
                continue
            claim_id = stable_id("claim", document_id, str(candidate["span_start"]), candidate["category"])
            time = resolve_time(record.date_text or candidate["statement"], record.published_at)
            if config.time.start and time["end"] and time["end"] < str(config.time.start):
                filtered += 1
                continue
            if config.time.end and time["start"] and time["start"] > str(config.time.end):
                filtered += 1
                continue
            places = gazetteer.resolve(record, candidate["statement"])
            choices = [d.get("location_id") for d in decisions.values()
                       if d["claim_id"] == claim_id and d.get("location_id") and d["decision"] == "accepted"]
            if len(set(choices)) > 1:
                raise ValueError("Review decisions select conflicting locations")
            if choices:
                if choices[0] not in {p["id"] for p in places}:
                    raise ValueError("Review location must be an existing candidate")
                places = [{**p, "selected": p["id"] == choices[0], "method": "human-selection-v1"}
                          for p in places]
            for place in places:
                add_location(place)
            selected = next((p for p in places if p["selected"]), None)
            claims.append({**candidate, "claim_id": claim_id, "document_id": document_id,
                           "source_id": record.source_id, "time": time, "locations": places,
                           "selected_location": selected, "provider_event_id": record.provider_event_id,
                           "quantities": record.quantities or extract_quantities(candidate["statement"]),
                           "acquisition_kind": record.acquisition.get("kind"),
                           "scope_warnings": scope_warnings.copy()})

    for source_id in sorted(used_sources):
        s = source_by_id[source_id]
        tables["source"].append({"source_id": source_id, "provider": s["provider"],
                                  "origin_group": s.get("origin_group"), "rights_json": canonical(s)})
    tables["document"] = list(docs.values())
    # Parent-before-child order is retained for database insertion.
    tables["location"] = list(locations.values())
    ds = sorted(docs.values(), key=lambda x: x["document_id"])
    for i, a in enumerate(ds):
        for b in ds[i + 1:]:
            if a["text"].casefold() == b["text"].casefold():
                similarity = 1.0
            elif min(len(a["text"]), len(b["text"])) >= 50:
                similarity = SequenceMatcher(None, a["text"].casefold(), b["text"].casefold()).ratio()
            else:
                continue
            if similarity >= 0.95:
                tables["document_duplicate"].append({"left_document_id": a["document_id"],
                    "right_document_id": b["document_id"],
                    "kind": "identical_text" if similarity == 1 else "possible_near_duplicate",
                    "similarity": round(similarity, 6)})
    rejected_ids = {d["claim_id"] for d in decisions.values() if d["decision"] == "rejected"}
    eligible = [c for c in claims if c["polarity"] != "negated"]
    groups, proposals = group_claims(eligible, source_by_id, config.processing.link_days,
                                    config.processing.link_km, link_decisions, rejected_ids)
    for c in claims:
        c.setdefault("conflicts", [])
        c["conflicts"].extend(c["scope_warnings"])
        selected = c["selected_location"]
        assessment = assess(c, source_by_id[c["source_id"]], selected, c["time"],
                            c.get("independent_groups", 0), bundle["evidence_rules"],
                            rejected=c["claim_id"] in rejected_ids)
        reasons = set(assessment["reasons"])
        previous = [d for d in decisions.values() if d["claim_id"] == c["claim_id"]]
        reasons.update(d["reason"] for d in previous)
        reviews = []
        for reason in sorted(reasons):
            review_id = stable_id("review", c["claim_id"], reason)
            decision = decisions.get(review_id)
            reviews.append({"review_id": review_id, "claim_id": c["claim_id"], "reason": reason,
                            "status": decision["decision"] if decision else "pending"})
        verified = bool(reviews) and all(r["status"] == "accepted" for r in reviews)
        assessment = assess(c, source_by_id[c["source_id"]], selected, c["time"],
                            c.get("independent_groups", 0), bundle["evidence_rules"], verified=verified,
                            rejected=c["claim_id"] in rejected_ids)
        c["assessment"] = assessment
        tables["review"].extend(reviews)
        tables["assessment"].append({"assessment_id": stable_id("assessment", c["claim_id"],
                                                                  bundle["evidence_rules"]["version"]),
                                      "claim_id": c["claim_id"], "indicators_json": canonical(assessment["indicators"]),
                                      "grade": assessment["grade"], "decision": assessment["decision"],
                                      "rule_version": bundle["evidence_rules"]["version"]})
        tables["claim"].append({"claim_id": c["claim_id"], "document_id": c["document_id"],
                                 "statement": c["statement"], "category": c["category"],
                                 "start_date": c["time"]["start"], "end_date": c["time"]["end"],
                                 "temporal_precision": c["time"]["precision"],
                                 "metadata_json": canonical({k: c[k] for k in ["time", "locations", "span_start",
                                     "span_end", "method", "extraction_confidence", "quantities", "polarity", "conflicts"]})})
        for loc in c["locations"]:
            tables["claim_location"].append({"claim_id": c["claim_id"], "location_id": loc["id"],
                                              "status": "selected" if loc["selected"] else "candidate"})
    review_by_id = {r["review_id"]: r for r in tables["review"]}
    for review_id, decision in decisions.items():
        if review_id not in review_by_id:
            raise ValueError("Review refers to a claim outside this run")
        tables["review_decision"].append({"decision_id": stable_id("decision", review_id, digest(decision)),
            "review_id": review_id, "reviewer": decision["reviewer"], "decision": decision["decision"],
            "note": decision["note"], "location_id": decision.get("location_id") or None,
            "decided_at": decision["decided_at"], "decision_file_hash": decision["decision_file_hash"]})
    events = []
    for event_id, group in sorted(groups.items()):
        starts = [c["time"]["start"] for c in group if c["time"]["start"]]
        ends = [c["time"]["end"] for c in group if c["time"]["end"]]
        located = [c["selected_location"] for c in group if c["selected_location"]]
        geo = {canonical(x["geometry"]): x for x in located if x.get("geometry")}
        selected = next(iter(geo.values())) if len(geo) == 1 else None
        label = selected["name"] if selected else (located[0]["name"] if located else "Unresolved place")
        state = "human_accepted" if all(c["assessment"]["indicators"]["verification_state"] == "human_accepted"
                                         for c in group) else "candidate"
        event = {"event_id": event_id, "category": group[0]["category"],
                 "start_date": min(starts) if starts else None, "end_date": max(ends) if ends else None,
                 "geometry": selected.get("geometry") if selected else None,
                 "spatial_precision": selected["level"] if selected else "unresolved",
                 "representational": bool(selected and selected.get("representational")),
                 "label": label, "state": state, "claim_count": len(group),
                 "independent_source_groups": group[0]["independent_groups"],
                 "geometry_conflict": len(geo) > 1,
                 "unknown_time_claims": sum(c["time"]["start"] is None for c in group)}
        relevant_links = group[0].get("link_decisions", [])
        if relevant_links:
            event["link_decisions"] = relevant_links
        events.append(event)
        tables["event"].append({k: event[k] for k in ["event_id", "category", "start_date", "end_date"]}
                               | {"metadata_json": canonical(event)})
        for c in group:
            tables["event_claim"].append({"event_id": event_id, "claim_id": c["claim_id"],
                                          "method": c["link_method"], "review_status": state})
    # Record every field's creating stage and its input/config/rule fingerprints.
    all_hashes = sorted(set(record_hashes.values()))
    modules = {"source": "registry", "document": "normalization", "claim": "extraction-and-time",
               "location": "gazetteer-and-source-geometry", "claim_location": "geocoding",
               "event": "linkage", "event_claim": "linkage", "assessment": "evidence",
               "review": "review-routing", "review_decision": "human-review", "document_duplicate": "deduplication"}
    config_hash = config.fingerprint()
    for table in TABLES:
        if table == "provenance":
            continue
        for row in tables[table]:
            target_key = {k: row[k] for k in PRIMARY_KEYS[table]}
            entity_id = str(next(iter(target_key.values()))) if len(target_key) == 1 else canonical(target_key)
            doc_id = row.get("document_id")
            if table == "claim":
                inputs = [record_hashes[doc_id]]
            elif table == "document":
                inputs = [row["content_hash"]]
            else:
                inputs = all_hashes
            for field in row:
                identity = canonical([table, row, field])
                tables["provenance"].append({"provenance_id": stable_id("provenance", identity),
                    "entity": table, "entity_id": entity_id, "field": field,
                    "transformation_json": canonical({"module": modules[table], "ree_version": __version__,
                        "input_hashes": inputs, "config_hash": config_hash, "rules_hash": digest(bundle),
                        "target_key": target_key,
                        "output_value_hash": digest(row[field]),
                        "method_note": "Candidate interpretations; source and original input are retained in document metadata."})})
    summary = {"documents": len(tables["document"]), "claims": len(claims), "events": len(events),
               "pending_reviews": sum(r["status"] == "pending" for r in tables["review"]),
               "filtered_records_or_claims": filtered, "privacy_suppressed_records": suppressed,
               "repeated_identical_input_records": repeated, "document_duplicate_pairs": len(tables["document_duplicate"]),
               "event_link_proposals": len(proposals)}
    return tables, events, proposals, summary, failed, notices


def dataset_digest(tables):
    return digest({t: sorted(rows, key=canonical) for t, rows in sorted(tables.items())})


def run(config, base=None, output=None, live=False, replay=None, decisions=None, parent_run=None,
        link_decisions=None):
    base = (base or Path.cwd()).resolve()
    output_base = Path(output).resolve() if output else (base / config.output_dir).resolve()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:10]
    root = output_base / config.project.name / run_id
    root.mkdir(parents=True, exist_ok=False)
    for directory in ["data", "gis", "review", "maps", "logs", "provenance", "summary"]:
        (root / directory).mkdir()
    deps = {}
    for package in ["pydantic", "PyYAML", "openpyxl", "pyarrow", "geopandas", "shapely", "pyproj"]:
        try:
            deps[package] = version(package)
        except PackageNotFoundError:
            deps[package] = None
    manifest = {"ree_version": __version__, "run_id": run_id, "started_at": timestamp(),
                "status": "running", "mode": config.mode, "live_requested": live,
                "config": config.model_dump(mode="json"), "config_hash": config.fingerprint(),
                "python": platform.python_version(), "dependencies": deps, "enabled_adapters": [],
                "input_files": [], "failed_records": [], "warnings": [], "record_counts": {},
                "export_files": {}, "parent_run": parent_run, **code_metadata()}
    manifest_path = root / "provenance" / "run_manifest.json"
    write_json(manifest_path, manifest)
    try:
        preflight_exports(config.exports)
        if not replay and (config.mode in {"live", "hybrid"}) != bool(live):
            raise ValueError("live/hybrid mode requires --live; --live cannot be used in demo/local mode")
        bundle = replay["processing_assets"] if replay else processing_assets(config, base)
        validate_assets(bundle)
        if set(config.topics) - set(bundle["taxonomy"]):
            raise ValueError("Some configured topics are absent from the taxonomy")
        registry = replay["registry"] if replay else asset("source_registry.json")
        records = []
        if replay:
            records = [Record.model_validate(r) for r in replay["records"]]
            manifest["enabled_adapters"].append("saved-run-replay")
        elif config.mode == "demo":
            fixture = asset("frozen.json")
            records = [Record.model_validate(r) for r in fixture]
            manifest["enabled_adapters"].append("bundled-curated-reference-v1")
            manifest["input_files"].append({"name": "frozen.json", "hash": digest(fixture),
                "kind": "curated_real_facts_and_short_excerpts; not an API response snapshot"})
        else:
            for spec in config.inputs:
                remaining = config.collection.max_records - len(records)
                if remaining <= 0:
                    manifest["failed_records"].append({"reason": "record_budget_exceeded"})
                    break
                loaded, source, meta, errors = ingest_file(spec, base, remaining, config.collection.max_bytes)
                registry = [s for s in registry if s["id"] != source["id"]] + [source]
                records.extend(loaded)
                manifest["input_files"].append(meta)
                manifest["failed_records"].extend(errors)
                manifest["enabled_adapters"].append("local-file-v1")
            if live:
                if config.collection.sources != ["usgs_catalog"]:
                    raise ValueError("Only usgs_catalog is implemented for live collection")
                adapter = USGSAdapter()
                manifest["enabled_adapters"].append("usgs-catalog-v1")
                try:
                    loaded, errors = adapter.collect(config)
                finally:
                    manifest["collection_provenance"] = adapter.provenance()
                remaining = config.collection.max_records - len(records)
                if len(loaded) > remaining:
                    errors.append({"reason": "combined_record_budget_exceeded"})
                records.extend(loaded[:max(0, remaining)])
                manifest["failed_records"].extend(errors)
        manifest["record_counts"]["acquired"] = len(records)
        if len(records) > config.collection.max_records:
            manifest["failed_records"].append({"reason": "record_budget_exceeded"})
            records = records[:config.collection.max_records]
        tables, events, proposals, summary, errors, notices = process_records(
            records, registry, config, bundle, decisions, link_decisions)
        manifest["record_counts"].update(summary)
        manifest["source_identifiers"] = [s["source_id"] for s in tables["source"]]
        manifest["processing_counts"] = {t: len(rows) for t, rows in tables.items()}
        manifest["failed_records"].extend(errors)
        manifest["warnings"].extend(notices)
        if not config.processing.human_review:
            manifest["warnings"].append({"reason": "human_review false does not bypass uncertainty queues"})
        if manifest["failed_records"] and not summary["documents"]:
            raise ValueError("No usable records remain; inspect failed_records")
        if not summary["claims"]:
            manifest["warnings"].append({"reason": "no_claims_in_scope; absence is not evidence of no events"})
        save_tables(root / "data" / "evidence.sqlite", tables)
        # Public mode retains only records actually admitted to storage, preventing raw-data leakage.
        kept_records = [json.loads(d["metadata_json"])["input_record"] for d in tables["document"]]
        snapshot = {"ree_version": __version__, "records": kept_records,
                    "registry": [s for s in registry if s["id"] in {r["source_id"] for r in kept_records}],
                    "processing_assets": bundle, "config": config.model_dump(mode="json"),
                    "decisions": decisions or {}, "link_decisions": link_decisions or []}
        write_json(root / "provenance" / "replay.json", snapshot)
        write_json(root / "provenance" / "event_link_reviews.json", link_decisions or [])
        export_all(root, tables, events, proposals, config.exports, summary)
        write_json(root / "logs" / "processing.json", {"failed_records": manifest["failed_records"],
                                                       "warnings": manifest["warnings"]})
        manifest.update(status="partial" if manifest["failed_records"] else "succeeded",
                        completed_at=timestamp(), dataset_hash=dataset_digest(tables),
                        processing_assets_hash=digest(bundle), export_files=file_hashes(root))
        write_json(manifest_path, manifest)
        return root, manifest
    except Exception as error:
        manifest.update(status="failed", completed_at=timestamp(), error={"type": type(error).__name__,
                        "message": str(error)}, export_files=file_hashes(root))
        write_json(manifest_path, manifest)
        raise RunFailure(str(error), root) from error
