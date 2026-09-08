"""Implemented commands only; argparse keeps the core installation small."""

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from importlib.metadata import version
from pathlib import Path

import yaml
from pydantic import ValidationError

from ree import __version__
from ree.config import ProjectConfig, initialize, load_config
from ree.exporters import file_hashes, write_json
from ree.models import digest
from ree.pipeline import run
from ree.review import apply_event_links, apply_review, load_replay, validate_run
from ree.sources import asset, discover
from ree.storage import connect, schema_sql


def reference_config():
    return ProjectConfig(project={"name": "flagship"}, export_policy="public")


def print_run(root, manifest):
    print(f"{manifest['status'].upper()}: {root}")
    print(json.dumps(manifest["record_counts"], indent=2))
    print(f"Report: {root / 'summary/run_report.html'}")
    return 0 if manifest["status"] == "succeeded" else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description="REE: traceable evidence, uncertainty, review and GIS")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a ready-to-run offline project YAML")
    init.add_argument("project", type=Path)
    for name, help_text in [("demo", "Run the bundled real-facts/excerpts reference offline"),
                            ("reproduce", "Verify the frozen reference dataset")]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--output", type=Path)
        if name == "reproduce":
            command.add_argument("reference", choices=["flagship"])
    execute = commands.add_parser("run", help="Run a configured offline, local, live or hybrid study")
    execute.add_argument("--config", type=Path, required=True)
    execute.add_argument("--live", action="store_true")
    execute.add_argument("--output", type=Path)
    ingest = commands.add_parser("ingest", help="Process one local file privately")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--output", type=Path)
    commands.add_parser("sources", help="Show curated source metadata and implementation status")
    search = commands.add_parser("discover", help="Match registered sources to a study")
    search.add_argument("--config", type=Path, required=True)
    validate = commands.add_parser("validate", help="Validate configuration or run data/file integrity")
    group = validate.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path)
    group.add_argument("--run", type=Path)
    review = commands.add_parser("review", help="Inspect queues or apply a decision CSV into a new run")
    review.add_argument("run_dir", type=Path)
    review_options = review.add_mutually_exclusive_group()
    review_options.add_argument("--decisions", type=Path)
    review_options.add_argument("--links", type=Path)
    review.add_argument("--output", type=Path)
    export = commands.add_parser("export", help="Re-export a validated saved run into a new run")
    export.add_argument("--run", type=Path, required=True)
    export.add_argument("--format", dest="formats", action="append", choices=["csv", "json", "geojson", "parquet", "gpkg"], required=True)
    export.add_argument("--output", type=Path)
    report = commands.add_parser("report", help="Locate an existing run report")
    report.add_argument("--run", type=Path, required=True)
    doctor = commands.add_parser("doctor", help="Diagnose local dependencies, schema, config and output access")
    doctor.add_argument("--config", type=Path)
    commands.add_parser("schema", help="Print the normalized relational schema")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            target = initialize(args.project)
            print(f"Created {target}\nNext: ree run --config {target}")
        elif args.command == "run":
            config = load_config(args.config)
            return print_run(*run(config, base=args.config.resolve().parent, output=args.output, live=args.live))
        elif args.command in {"demo", "reproduce"}:
            root, manifest = run(reference_config(), output=args.output)
            if args.command == "reproduce":
                expected = asset("expected.json")
                comparison = {"expected_version": expected["ree_version"], "actual_version": __version__,
                              "fixture_matches": expected["fixture_hash"] == digest(asset("frozen.json")),
                              "dataset_matches": expected["dataset_hash"] == manifest["dataset_hash"],
                              "counts_match": expected["record_counts"] == manifest["record_counts"]}
                passed = comparison["expected_version"] == __version__ and all(
                    comparison[k] for k in ["fixture_matches", "dataset_matches", "counts_match"])
                write_json(root / "provenance/reproduction_check.json", {**comparison, "passed": passed})
                manifest["reproduction_passed"] = passed
                manifest["export_files"] = file_hashes(root)
                if not passed:
                    manifest["status"] = "failed"
                write_json(root / "provenance/run_manifest.json", manifest)
                print("Reproduction: " + ("PASS" if passed else "FAIL — reference drift"))
                if not passed:
                    return 4
            return print_run(root, manifest)
        elif args.command == "ingest":
            config = ProjectConfig(project={"name": "local-evidence"}, mode="local",
                                   inputs=[{"path": str(args.file.resolve())}],
                                   topics=list(asset("event_taxonomy.json")))
            return print_run(*run(config, output=args.output))
        elif args.command == "sources":
            print(json.dumps(asset("source_registry.json"), ensure_ascii=False, indent=2))
        elif args.command == "discover":
            print(json.dumps(discover(load_config(args.config)), indent=2))
        elif args.command == "review":
            if args.links:
                return print_run(*apply_event_links(args.run_dir, args.links, args.output))
            if args.decisions:
                return print_run(*apply_review(args.run_dir, args.decisions, args.output))
            manifest, _ = load_replay(args.run_dir)
            print(f"Pending reviews: {manifest['record_counts']['pending_reviews']}")
            print(f"Copy and edit: {args.run_dir / 'review/decisions_template.csv'}")
        elif args.command == "export":
            manifest, snapshot = load_replay(args.run)
            config = ProjectConfig.model_validate({**snapshot["config"], "exports": args.formats})
            return print_run(*run(config, output=args.output, replay=snapshot,
                                  decisions=snapshot.get("decisions"), parent_run=manifest["run_id"],
                                  link_decisions=snapshot.get("link_decisions")))
        elif args.command in {"validate", "report"}:
            if args.command == "validate" and args.config:
                config = load_config(args.config)
                from ree.pipeline import processing_assets
                processing_assets(config, args.config.resolve().parent)
                print(f"PASS: configuration; sha256={config.fingerprint()}")
            else:
                _, problems = validate_run(args.run)
                if problems:
                    raise ValueError("; ".join(problems))
                print(f"PASS: run integrity\nReport: {args.run / 'summary/run_report.html'}")
        elif args.command == "schema":
            print(schema_sql())
        elif args.command == "doctor":
            config = load_config(args.config) if args.config else reference_config()
            base = args.config.resolve().parent if args.config else Path.cwd()
            from ree.pipeline import processing_assets
            processing_assets(config, base)
            db = connect()
            try:
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                db.close()
            destination = (base / config.output_dir).resolve()
            while not destination.exists():
                destination = destination.parent
            print(json.dumps({"ree": __version__, "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version, "sqlite_integrity": integrity,
                "dependencies": {x: version(x) for x in ("pydantic", "PyYAML")},
                "optional_modules": {x: importlib.util.find_spec(x) is not None for x in ["openpyxl", "pyarrow", "geopandas"]},
                "output_parent_writable": os.access(destination, os.W_OK),
                "network_tested": False, "paid_credentials_required": False,
                "scope": "local checks only; live access and desktop GIS are separate gates"}, indent=2))
        return 0
    except (OSError, ValueError, ValidationError, yaml.YAMLError, sqlite3.Error) as error:
        message = str(error)
        if isinstance(error, ValidationError):
            message = "; ".join(".".join(map(str, x["loc"])) + ": " + x["msg"]
                                for x in error.errors(include_input=False))
        print(f"REE error: {message}", file=sys.stderr)
        return 2
