"""Validated recovery and comparison: every operation creates a new child run."""
import json
import sqlite3
from collections import Counter
from pathlib import Path

from ree import __version__
from ree.config import ProjectConfig
from ree.integrity import validate_files, validate_run
from ree.models import digest
from ree.pipeline import run, validate_assets
from ree.review import load_replay


def resume_run(root, output=None, live=False, cache=None):
    root = root.resolve()
    manifest = json.loads((root / 'provenance/run_manifest.json').read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('Run manifest must be a JSON object')
    if manifest.get('status') in {'succeeded', 'partial'}:
        manifest, replay = load_replay(root)
        return run(ProjectConfig.model_validate(replay['config']), output=output, replay=replay,
                   decisions=replay.get('decisions'), link_decisions=replay.get('link_decisions'),
                   parent_run=manifest['run_id'])
    problems = validate_files(root, manifest)
    if problems:
        raise ValueError('; '.join(problems))
    cp = json.loads((root / 'provenance/acquisition_checkpoint.json').read_text(encoding='utf-8'))
    if cp['ree_version'] != __version__ or manifest.get('ree_version') != __version__:
        raise ValueError('Resume requires the original REE version')
    config = ProjectConfig.model_validate(cp['config'])
    if digest(cp) != manifest.get('checkpoint_hash') or config.fingerprint() != cp['config_hash'] \
            or config.fingerprint() != manifest.get('config_hash'):
        raise ValueError('Acquisition checkpoint/configuration hash mismatch')
    validate_assets(cp['processing_assets'])
    if any(type(i) is not int or not 0 <= i < len(config.inputs) for i in cp['completed_inputs']) \
            or set(cp['completed_sources']) - set(config.collection.sources):
        raise ValueError('Invalid completed acquisition stages')
    if set(config.collection.sources) - set(cp['completed_sources']) \
            and config.mode in {'live', 'hybrid'} and not live:
        raise ValueError('Unfinished live acquisition requires --live to resume')
    base = cp.get('config_base')
    if base is None and len(cp['completed_inputs']) < len(config.inputs):
        raise ValueError('Checkpoint lacks config base for unfinished local inputs')
    return run(config, base=Path(base) if base else root, output=output, live=live,
               resume_checkpoint=cp, cache=cache, parent_run=manifest['run_id'])


def compare_runs(left, right):
    def inspect(root):
        manifest, problems = validate_run(root)
        if problems:
            raise ValueError('; '.join(problems))
        db = sqlite3.connect((root.resolve() / 'data/evidence.sqlite').as_uri() + '?mode=ro', uri=True)
        try:
            return {'run_id': manifest['run_id'], 'mode': manifest['mode'],
                    'counts': manifest['record_counts'], 'dataset_hash': manifest['dataset_hash'],
                    'sources': sorted(r[0] for r in db.execute('SELECT source_id FROM source')),
                    'grades': dict(Counter(r[0] for r in db.execute('SELECT grade FROM assessment'))),
                    'locations': dict(Counter(r[0] for r in db.execute('SELECT precision FROM location'))),
                    'collection_outcomes': manifest.get('collections', []),
                    'failed_record_count': len(manifest.get('failed_records', []))}
        finally:
            db.close()
    a, b = inspect(left), inspect(right)
    return {'left': a, 'right': b, 'same_dataset': a['dataset_hash'] == b['dataset_hash'],
            'count_delta_right_minus_left': {k: b['counts'].get(k, 0) - a['counts'].get(k, 0)
                                            for k in a['counts'].keys() | b['counts'].keys()},
            'sources_added': sorted(set(b['sources']) - set(a['sources'])),
            'sources_removed': sorted(set(a['sources']) - set(b['sources'])),
            'note': 'Frozen replay and new live collection have different reproducibility guarantees'}
