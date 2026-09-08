"""Synthetic edge cases only; these are not real-world demonstration evidence."""

import pytest

from ree.models import Record, check_geometry
from ree.resolution import LocalGazetteer, extract, extract_quantities, resolve_time
from ree.sources import asset


@pytest.mark.parametrize('text,ref,start,end,precision', [
    (None, '2024-05-07', None, None, 'unknown'),
    ('no date supplied', '2024-05-07', None, None, 'unknown'),
    ('2024-02', None, '2024-02-01', '2024-02-29', 'month'),
    ('May 2024', None, '2024-05-01', '2024-05-31', 'month'),
    ('২০২৪-০৫-০১', None, '2024-05-01', '2024-05-01', 'exact'),
    ('2024-02-30', None, None, None, 'unknown'),
    ('2024-05-01 to 2024-05-04', None, '2024-05-01', '2024-05-04', 'range'),
    ('2024-05-04 to 2024-05-01', None, None, None, 'unknown'),
    ('2024-05-01 or 2024-05-04', None, None, None, 'unknown'),
    ('Yesterday flooding occurred', None, None, None, 'unknown'),
    ('Yesterday flooding occurred', '2024-03-01', '2024-02-29', '2024-02-29', 'relative'),
    ('last week', '2024-01-10', '2024-01-01', '2024-01-07', 'week'),
    ('Monday’s quake', '2024-01-02', '2024-01-01', '2024-01-01', 'relative'),
    ('2024-04-03T00:30:00+06:00', None, '2024-04-02', '2024-04-02', 'exact'),
    ('2024-04-03T00:30:00', None, None, None, 'unknown'),
])
def test_time_uncertainty(text, ref, start, end, precision):
    result = resolve_time(text, ref)
    assert (result['start'], result['end'], result['precision']) == (start, end, precision)


@pytest.mark.parametrize('coordinates', [[181, 0], [0, 91], [float('nan'), 0], [True, 1], [1], [1, 2, 3]])
def test_bad_coordinates(coordinates):
    with pytest.raises(ValueError):
        check_geometry({'type': 'Point', 'coordinates': coordinates})


def test_sylhet_keeps_both_interpretations_without_fake_points():
    gaz = LocalGazetteer(asset('gazetteer.json'))
    record = Record(source_record_id='synthetic-1', text='Sylhet flood', country='Bangladesh')
    candidates = gaz.resolve(record, record.text)
    assert len(candidates) == 2
    assert not any(x['selected'] or x.get('geometry') for x in candidates)


@pytest.mark.parametrize('rows', [
    [{'id': 'a', 'name': 'a', 'parent_id': 'missing'}],
    [{'id': 'a', 'name': 'a', 'parent_id': 'b'}, {'id': 'b', 'name': 'b', 'parent_id': 'a'}],
    [{'id': 'a', 'name': 'a'}, {'id': 'a', 'name': 'a'}],
    [{'id': 'a', 'name': 'a', 'country': 'A'}, {'id': 'b', 'name': 'b', 'parent_id': 'a', 'country': 'B'}],
    [{'id': 'a', 'name': 'a', 'level': 'district', 'geometry': {'type': 'Point', 'coordinates': [10, 20]}}]
])
def test_gazetteer_integrity(rows):
    with pytest.raises(ValueError):
        LocalGazetteer(rows)


def test_negation_and_forecast_are_not_confirmed_occurrences():
    taxonomy = asset('event_taxonomy.json')
    record = Record(source_record_id='synthetic-1', text='No flood occurred. Flooding may occur.')
    _, claims = extract(record, taxonomy)
    assert [c['polarity'] for c in claims] == ['negated', 'hypothetical']


def test_basic_bangla_keyword_and_quantity_mentions():
    record = Record(source_record_id='synthetic-1', text='সিলেটে বন্যা হয়েছে।', language='bn')
    assert extract(record, asset('event_taxonomy.json'))[1][0]['category'] == 'flood'
    quantities = extract_quantities('Nearly 3 feet and 12 people were mentioned.')
    assert quantities[0]['approximate']
    assert quantities[1]['value'] == 12
    assert 'affected population' in quantities[1]['note']


@pytest.mark.parametrize('quantity', [{'value': 3}, {'kind': 'count', 'unit': 'people', 'value': float('nan')}])
def test_malformed_quantities(quantity):
    with pytest.raises(ValueError):
        Record(source_record_id='synthetic-1', text='Flood', quantities=[quantity])
