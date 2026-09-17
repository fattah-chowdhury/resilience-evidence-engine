"""Run inventory, relational, semantic and provenance integrity checks."""

import json
import sqlite3
from hashlib import sha256

from ree.config import ProjectConfig
from ree.models import check_geometry, digest
from ree.pipeline import dataset_digest, validate_assets
from ree.storage import PRIMARY_KEYS, TABLES, connect, validate_database


def validate_files(root, manifest):
    problems = []
    if not isinstance(manifest, dict):
        raise ValueError('Run manifest must be a JSON object')
    exports = manifest.get('export_files')
    if not isinstance(exports, dict) or not exports:
        return ['Missing output hash inventory']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
              if p.is_file() and p != root / 'provenance/run_manifest.json'}
    if actual != set(exports):
        problems.append('Output file inventory differs from manifest')
    for relative, expected in exports.items():
        original = root / relative
        path = original.resolve()
        if not path.is_relative_to(root) or not path.is_file() or original.is_symlink() \
                or any(p.is_symlink() for p in original.parents if p != root and p.is_relative_to(root)):
            problems.append(f'Missing or unsafe output: {relative}')
        elif sha256(path.read_bytes()).hexdigest() != expected:
            problems.append(f'Changed output: {relative}')
    return problems


def validate_run(root):
    root = root.resolve()
    manifest = json.loads((root / 'provenance/run_manifest.json').read_text(encoding='utf-8'))
    problems = validate_files(root, manifest)
    if manifest.get('status') not in {'succeeded', 'partial'}:
        problems.append('Run is not a completed evidence dataset')
    database = root / 'data/evidence.sqlite'
    if not database.is_file() or database.is_symlink() or database.parent.is_symlink():
        return manifest, problems + ['Missing or unsafe SQLite database']
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        reference = connect()
        try:
            for table in TABLES:
                if db.execute(f'PRAGMA table_info({table})').fetchall() != reference.execute(f'PRAGMA table_info({table})').fetchall():
                    raise ValueError('Evidence schema differs from supported schema')
        finally:
            reference.close()
        problems.extend(validate_database(db))
        db.row_factory = sqlite3.Row
        tables = {t: [dict(r) for r in db.execute(f'SELECT * FROM {t}')] for t in TABLES}
        if dataset_digest(tables) != manifest.get('dataset_hash'):
            problems.append('Dataset hash differs from manifest')
        counts = {t: len(r) for t, r in tables.items()}
        if counts != manifest.get('processing_counts'):
            problems.append('Table counts differ from manifest')
        for name, table in (('documents', 'document'), ('claims', 'claim'), ('events', 'event')):
            if manifest.get('record_counts', {}).get(name) != counts[table]:
                problems.append('Record counts differ from database')
        if manifest.get('record_counts', {}).get('pending_reviews') != sum(r['status'] == 'pending' for r in tables['review']):
            problems.append('Pending review count mismatch')
        for table, keys in PRIMARY_KEYS.items():
            if any(not str(r[k]).strip() for r in tables[table] for k in keys):
                problems.append('Blank entity identifier')
        replay = json.loads((root / 'provenance/replay.json').read_text(encoding='utf-8'))
        config = ProjectConfig.model_validate(manifest['config'])
        if config.fingerprint() != manifest.get('config_hash') or replay['config'] != manifest['config']:
            problems.append('Configuration provenance mismatch')
        validate_assets(replay['processing_assets'])
        if digest(replay['processing_assets']) != manifest.get('processing_assets_hash'):
            problems.append('Processing asset provenance mismatch')
        taxonomy = replay['processing_assets']['taxonomy']
        if any(r['category'] not in taxonomy for t in ('claim', 'event') for r in tables[t]):
            problems.append('Unrecognized taxonomy value')
        categories = {c['claim_id']: c['category'] for c in tables['claim']}
        events = {e['event_id']: e['category'] for e in tables['event']}
        if any(categories.get(r['claim_id']) != events.get(r['event_id']) for r in tables['event_claim']):
            problems.append('Event links mismatch claim category')
        for event in tables['event']:
            data = json.loads(event['metadata_json'])
            try:
                check_geometry(data.get('geometry'))
                if any(data[k] != event[k] for k in ('event_id', 'category', 'start_date', 'end_date')):
                    problems.append('Event metadata disagrees with event row')
                if data['claim_count'] != sum(r['event_id'] == event['event_id'] for r in tables['event_claim']):
                    problems.append('Event claim count mismatch')
                if data.get('geometry') and data.get('spatial_precision') in {'admin_centroid', 'model_reference', 'unknown'} and not data.get('representational'):
                    problems.append('Unmarked representational event geometry')
            except (ValueError, KeyError, TypeError, AttributeError):
                problems.append('Invalid event geometry or metadata')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error) as error:
        problems.append('Evidence validation failed: ' + type(error).__name__)
    finally:
        db.close()
    return manifest, sorted(set(problems))
