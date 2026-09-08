"""End-to-end invariants; additional local evidence here is explicitly synthetic."""

import csv
import json
import sqlite3
from hashlib import sha256

import pytest

from ree.cli import main, reference_config
from ree.config import ProjectConfig
from ree.exporters import csv_cell
from ree.models import Record
from ree.pipeline import RunFailure, dataset_digest, process_records, processing_assets, run
from ree.review import apply_review, validate_run
from ree.sources import USGSAdapter, asset
from ree.storage import validate_database


@pytest.fixture
def demo_run(tmp_path):
    return run(reference_config(), output=tmp_path / 'runs')


def test_offline_demo_is_deterministic_and_retains_uncertainty(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: pytest.fail('Offline demo attempted network'))
    config = reference_config()
    records = [Record.model_validate(r) for r in asset('frozen.json')]
    args = (asset('source_registry.json'), config, processing_assets(config, tmp_path))
    a = process_records(records, *args)
    b = process_records(list(reversed(records)), *args)
    assert dataset_digest(a[0]) == dataset_digest(b[0]) == asset('expected.json')['dataset_hash']
    assert a[3]['claims'] == 5 and a[3]['events'] == 4 and a[3]['pending_reviews'] == 12
    flood = next(c for c in a[0]['claim'] if c['category'] == 'flood')
    assert flood['start_date'] is None
    assert len(json.loads(flood['metadata_json'])['locations']) == 2
    noto = next(e for e in a[1] if e['label'].startswith('Noto'))
    assert noto['claim_count'] == 2 and noto['independent_source_groups'] == 1
    assert noto['representational']


def test_exported_geojson_provenance_and_integrity(demo_run):
    root, manifest = demo_run
    assert not validate_run(root)[1]
    geo = json.loads((root / 'gis/events.geojson').read_text())
    assert geo['type'] == 'FeatureCollection' and len(geo['features']) == 4
    assert sum(f['geometry'] is not None for f in geo['features']) == 2
    assert manifest['source_identifiers'] == ['nasa_excerpt', 'usgs_pages']
    db = sqlite3.connect(root / 'data/evidence.sqlite')
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT count(*) FROM provenance').fetchone()[0] > 100
    db.execute('DELETE FROM provenance WHERE rowid=(SELECT min(rowid) FROM provenance)')
    assert 'Missing field provenance' in validate_database(db)
    db.close()


def test_mutated_export_is_detected(demo_run):
    root, _ = demo_run
    (root / 'data/claims.csv').write_text('tampered')
    assert any('Changed output: data/claims.csv' in x for x in validate_run(root)[1])


def test_review_round_trip_preserves_original_and_records_decision(demo_run, tmp_path):
    root, original_manifest = demo_run
    original_hash = sha256((root / 'data/evidence.sqlite').read_bytes()).hexdigest()
    rows = list(csv.DictReader((root / 'review/decisions_template.csv').open()))
    row = next(r for r in rows if r['reason'] == 'curated_source_transcription')
    row.update(decision='accepted', reviewer='Synthetic test reviewer', note='Test-only acceptance workflow')
    path = tmp_path / 'decisions.csv'
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    new_root, new_manifest = apply_review(root, path, tmp_path / 'reviewed')
    assert new_manifest['parent_run'] == original_manifest['run_id']
    assert new_manifest['record_counts']['pending_reviews'] == 11
    assert sha256((root / 'data/evidence.sqlite').read_bytes()).hexdigest() == original_hash
    assert not validate_run(new_root)[1]
    db = sqlite3.connect(new_root / 'data/evidence.sqlite')
    assert db.execute('SELECT count(*) FROM review_decision').fetchone()[0] == 1
    db.close()


def test_review_rejects_unknown_ids_before_creating_new_run(demo_run, tmp_path):
    root, _ = demo_run
    path = tmp_path / 'decisions.csv'
    path.write_text('review_id,decision,reviewer,note\nmissing,accepted,test,test\n')
    with pytest.raises(ValueError, match='unknown review_id'):
        apply_review(root, path, tmp_path / 'should-not-exist')
    assert not (tmp_path / 'should-not-exist').exists()


def test_public_mode_suppresses_sensitive_raw_data_everywhere(tmp_path):
    path = tmp_path / 'synthetic.json'
    path.write_text('[{"text":"CANARY_PRIVATE_SENTENCE flood","location_text":"PRIVATE_ADDRESS"}]')
    config = ProjectConfig(project={'name': 'private-test'}, mode='local',
                           inputs=[{'path': path.name}], export_policy='public')
    root, manifest = run(config, base=tmp_path)
    assert manifest['record_counts']['privacy_suppressed_records'] == 1
    assert manifest['record_counts']['documents'] == 0
    for artifact in root.rglob('*'):
        if artifact.is_file():
            assert b'CANARY_PRIVATE_SENTENCE' not in artifact.read_bytes()
            assert b'PRIVATE_ADDRESS' not in artifact.read_bytes()


def test_partial_ingestion_is_reported(tmp_path):
    path = tmp_path / 'synthetic.jsonl'
    path.write_text('{"text":"Synthetic flood in Japan on 2024-01-01"}\n{broken}\n')
    config = ProjectConfig(project={'name': 'partial'}, mode='local', inputs=[{'path': path.name}])
    root, manifest = run(config, base=tmp_path)
    assert manifest['status'] == 'partial' and len(manifest['failed_records']) == 1
    assert not validate_run(root)[1]


def test_failed_live_collection_creates_manifest_without_demo_fallback(tmp_path, monkeypatch):
    def unavailable(self, config):
        raise OSError('Simulated blocked connection')
    monkeypatch.setattr(USGSAdapter, 'collect', unavailable)
    config = ProjectConfig(project={'name': 'blocked'}, mode='live', topics=['earthquake'],
                           collection={'public_sources': True})
    with pytest.raises(RunFailure) as error:
        run(config, output=tmp_path, live=True)
    root = error.value.output
    manifest = json.loads((root / 'provenance/run_manifest.json').read_text())
    assert manifest['status'] == 'failed' and manifest['record_counts'] == {}
    assert manifest['enabled_adapters'] == ['usgs-catalog-v1']
    assert manifest['collection_provenance']['adapter'] == 'usgs-catalog-v1'
    assert not (root / 'data/evidence.sqlite').exists()


def test_live_requires_explicit_flag(tmp_path):
    config = ProjectConfig(project={'name': 'blocked'}, mode='live', topics=['earthquake'],
                           collection={'public_sources': True})
    with pytest.raises(RunFailure, match='requires --live'):
        run(config, output=tmp_path)


def test_copies_do_not_become_independent_corroboration(tmp_path):
    records = [Record(source_record_id=str(i), source_id='usgs_pages', text='Synthetic flood in Japan on 2024-01-01',
                      country='Japan', provider_event_id='synthetic-event', sensitive=False) for i in range(2)]
    config = reference_config()
    tables, events, _, summary, _, _ = process_records(records, asset('source_registry.json'), config,
                                                       processing_assets(config, tmp_path))
    assert summary['document_duplicate_pairs'] == 1
    assert len(events) == 1 and events[0]['independent_source_groups'] == 1
    assert len(tables['document']) == 2


def test_conflicting_quantities_remain_reviewable(tmp_path):
    records = [Record(source_record_id=str(i), source_id='usgs_pages', text=f'Synthetic flood report {i}',
                      country='Japan', location_text='Japan', date_text='2024-01-01', category='flood',
                      provider_event_id='synthetic-event', sensitive=False,
                      quantities=[{'kind':'count','value':i,'unit':'houses'}]) for i in (1, 2)]
    config = reference_config()
    tables, _, _, _, _, _ = process_records(records, asset('source_registry.json'), config,
                                            processing_assets(config, tmp_path))
    assert sum(r['reason'] == 'conflicting_quantities' for r in tables['review']) == 2


def test_csv_formula_protection_and_html_escaping(tmp_path):
    assert csv_cell('=HYPERLINK("evil")').startswith("'")
    assert csv_cell(-3.5) == -3.5
    path = tmp_path / 'synthetic.json'
    path.write_text(json.dumps([{'text':'Synthetic flood','location_text':'<script>alert(1)</script>',
                                'geometry':{'type':'Point','coordinates':[90,24]}}]))
    config = ProjectConfig(project={'name':'escaped'}, mode='local', inputs=[{'path':path.name}])
    root, _ = run(config, base=tmp_path)
    html = (root / 'summary/run_report.html').read_text()
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_init_run_and_reproduction_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(['init', 'my-study']) == 0
    assert main(['run', '--config', 'my-study/project.yml']) == 0
    assert main(['reproduce', 'flagship', '--output', str(tmp_path/'reproduced')]) == 0
