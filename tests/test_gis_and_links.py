"""Independent file readers and synthetic manual linkage cases."""

import csv
import json

import pytest

from ree.cli import reference_config
from ree.config import ProjectConfig
from ree.ingestion import raw_rows
from ree.models import Record
from ree.pipeline import processing_assets, run
from ree.review import apply_event_links, validate_run


def test_parquet_and_geopackage_round_trip(tmp_path):
    gpd = pytest.importorskip('geopandas')
    pq = pytest.importorskip('pyarrow.parquet')
    pyogrio = pytest.importorskip('pyogrio')
    config = reference_config().model_copy(update={'exports':['csv','json','geojson','parquet','gpkg']})
    root, _ = run(config, output=tmp_path)
    assert set(pyogrio.list_layers(root/'gis/evidence.gpkg')[:,0]) == {'events','locations'}
    for path in [root/'gis/events.geojson', root/'gis/evidence.gpkg']:
        frame = gpd.read_file(path, layer='events') if path.suffix == '.gpkg' else gpd.read_file(path)
        assert len(frame) == 4 and frame.crs.to_epsg() == 4326
        assert frame.geometry.notna().sum() == 2
        assert all(frame[frame.geometry.notna()].geometry.is_valid)
    claims = pq.read_table(root/'data/claims.parquet')
    assert claims.num_rows == 5 and claims['start_date'].null_count == 1
    assert str(pq.read_schema(root/'data/locations.parquet').field('representational').type) == 'int64'
    assert len(list(raw_rows(root/'data/claims.parquet', 10000000))) == 5
    assert len(list(raw_rows(root/'gis/evidence.gpkg', 10000000))) > 0
    assert not validate_run(root)[1]


def test_empty_gis_exports_are_readable(tmp_path):
    gpd = pytest.importorskip('geopandas')
    config = ProjectConfig(project={'name':'empty'}, study_area={'country':'Unmatched test country'}, exports=['gpkg','geojson','parquet'])
    root, _ = run(config, output=tmp_path)
    assert (root/'gis/evidence.gpkg').exists()
    assert len(gpd.read_file(root/'gis/evidence.gpkg', layer='events')) == 0


def synthetic_link_run(tmp_path):
    config = reference_config()
    records = []
    registry = []
    for index, text in enumerate(['Synthetic water covering cropland in the delta.',
                                   'Synthetic river overflow impacted a settlement.',
                                   'Synthetic transport access was lost during inundation.']):
        source_id = f'synthetic-source-{index}'
        registry.append({'id':source_id,'provider':source_id,'origin_group':source_id,
                         'redistribution_allowed':True,'status':'synthetic-test-only'})
        records.append(Record(source_record_id=f'synthetic-{index}', source_id=source_id, text=text,
                              category='flood', date_text='2024-01-01', country='Synthetic country',
                              location_text='Synthetic delta', geometry={'type':'Point','coordinates':[90,24]},
                              geometry_role='source_point', sensitive=False).model_dump(mode='json'))
    replay = {'registry':registry,'records':records,'processing_assets':processing_assets(config,tmp_path)}
    return run(config, output=tmp_path, replay=replay)


def decide_first(root, tmp_path, index, decision='accepted'):
    with (root/'review/possible_event_links.csv').open() as f:
        row = next(csv.DictReader(f))
    row.update(decision=decision,reviewer='Synthetic test reviewer',note='Synthetic linkage workflow test')
    path = tmp_path/f'link-decision-{index}.csv'
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return apply_event_links(root,path,tmp_path/'linked')


def test_sequential_human_merges_preserve_independence_and_history(tmp_path):
    root, manifest = synthetic_link_run(tmp_path)
    assert manifest['record_counts']['events'] == 3
    root2, second = decide_first(root,tmp_path,1)
    assert second['record_counts']['events'] == 2
    root3, third = decide_first(root2,tmp_path,2)
    assert third['record_counts']['events'] == 1
    events=json.loads((root3/'gis/events.geojson').read_text())['features']
    assert events[0]['properties']['independent_source_groups'] == 3
    assert len(events[0]['properties']['link_decisions']) == 2
    assert not validate_run(root3)[1]
    assert not validate_run(root)[1]


def test_rejected_event_link_is_logged_and_removed_from_pending(tmp_path):
    root,_=synthetic_link_run(tmp_path)
    reviewed,manifest=decide_first(root,tmp_path,1,'rejected')
    assert manifest['record_counts']['events'] == 3
    assert manifest['record_counts']['event_link_proposals'] == 2
    history=json.loads((reviewed/'provenance/event_link_reviews.json').read_text())
    assert history[0]['decision'] == 'rejected'
