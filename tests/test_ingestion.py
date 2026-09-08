"""Generated inputs in these tests are synthetic software fixtures only."""

import json

import pytest

from ree.config import InputSpec
from ree.ingestion import ingest_file, raw_rows


@pytest.mark.parametrize('extension,content', [
    ('json', '[{"text":"Synthetic flood in 2024-01-01"}]'),
    ('jsonl', '{"text":"Synthetic flood in 2024-01-01"}\n'),
    ('csv', 'text\nSynthetic flood in 2024-01-01\n'),
    ('tsv', 'text\nSynthetic flood in 2024-01-01\n'),
    ('txt', 'Synthetic flood in 2024-01-01'),
    ('html', '<script>secret()</script><p>Synthetic flood in 2024-01-01</p>'),
    ('geojson', '{"type":"FeatureCollection","features":[{"type":"Feature","id":"synthetic-1","properties":{"text":"Synthetic flood in 2024-01-01"},"geometry":{"type":"Point","coordinates":[90,24]}}]}'),
    ('rss', '<rss><channel><item><guid>synthetic-1</guid><description>Synthetic flood in 2024-01-01</description></item></channel></rss>'),
])
def test_local_formats(tmp_path, extension, content):
    path = tmp_path / ('synthetic.' + extension)
    path.write_text(content)
    records, source, meta, errors = ingest_file(InputSpec(path=path.name), tmp_path, 100, 100000)
    assert len(records) == 1 and not errors
    assert 'Synthetic flood' in records[0].text
    assert 'secret()' not in records[0].text
    assert records[0].sensitive and source['redistribution_allowed'] is False
    assert len(meta['hash']) == 64


def test_xlsx(tmp_path):
    openpyxl = pytest.importorskip('openpyxl')
    book = openpyxl.Workbook()
    book.active.append(['text', 'source_record_id'])
    book.active.append(['Synthetic flood', 'synthetic-1'])
    path = tmp_path / 'synthetic.xlsx'
    book.save(path)
    records, _, _, errors = ingest_file(InputSpec(path=path.name), tmp_path, 100, 100000)
    assert len(records) == 1 and not errors


def test_multiline_csv_and_mapping(tmp_path):
    path = tmp_path / 'synthetic.csv'
    path.write_text('narrative\n"Synthetic flood\ncontinued"\n')
    records, _, _, errors = ingest_file(InputSpec(path=path.name, columns={'narrative': 'text'}), tmp_path, 10, 10000)
    assert records[0].text == 'Synthetic flood\ncontinued' and not errors


def test_bad_record_is_quarantined_and_raw_values_are_not_in_error(tmp_path):
    path = tmp_path / 'synthetic.jsonl'
    path.write_text('{"text":"Synthetic flood"}\n{broken}\n{"unknown_secret":"SECRET_CANARY"}\n')
    records, _, _, errors = ingest_file(InputSpec(path=path.name), tmp_path, 10, 10000)
    assert len(records) == 1 and len(errors) == 2
    assert 'SECRET_CANARY' not in json.dumps(errors)


def test_record_and_byte_budgets(tmp_path):
    path = tmp_path / 'synthetic.json'
    path.write_text(json.dumps([{'text': 'Synthetic flood ' + str(i)} for i in range(3)]))
    records, _, _, errors = ingest_file(InputSpec(path=path.name), tmp_path, 2, 10000)
    assert len(records) == 2 and errors[0]['reason'] == 'record_budget_exceeded'
    with pytest.raises(ValueError):
        list(raw_rows(path, 2))


def test_local_file_cannot_impersonate_an_official_source(tmp_path):
    path = tmp_path / 'synthetic.json'
    path.write_text('[{"text":"Synthetic flood","source_id":"usgs_catalog","sensitive":false}]')
    records, source, _, _ = ingest_file(InputSpec(path=path.name), tmp_path, 10, 10000)
    assert records[0].source_id.startswith('local_')
    assert records[0].sensitive and source['origin_group'] is None


@pytest.mark.parametrize('extension,content', [
    ('xml', '<!DOCTYPE rss [<!ENTITY x "bomb">]><rss/>'),
    ('csv', 'text,text\na,b\n'),
    ('geojson', '{"type":"FeatureCollection","crs":{"name":"EPSG:3857"},"features":[]}'),
    ('pkl', 'untrusted binary format')
])
def test_disallowed_inputs(tmp_path, extension, content):
    path = tmp_path / ('synthetic.' + extension)
    path.write_text(content)
    with pytest.raises(ValueError):
        list(raw_rows(path, 10000))
