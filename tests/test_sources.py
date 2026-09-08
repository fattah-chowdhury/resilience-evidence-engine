"""Transport doubles are synthetic; no network is used by this test suite."""

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from ree.config import ProjectConfig
from ree.sources import NoRedirect, USGSAdapter, discover, fetch_catalog, safe_catalog_url


def config(**changes):
    return ProjectConfig.model_validate({'project': {'name': 'synthetic-live'}, 'mode': 'live',
        'topics': ['earthquake'], 'collection': {'public_sources': True}, **changes})


def feature(i=1):
    return {'id': f'synthetic-{i}', 'properties': {'net': 'us', 'type': 'earthquake',
        'time': 1704067200000, 'mag': 5, 'magType': 'mb', 'title': 'Synthetic earthquake'},
        'geometry': {'type': 'Point', 'coordinates': [90, 24, 10]}}


def test_source_discovery_rejects_flood_topic_and_unapproved_provider():
    result = {x['id']: x for x in discover(config(topics=['flood']))}
    assert not result['usgs_catalog']['live_eligible']
    assert 'topic_mismatch' in result['usgs_catalog']['reasons']
    assert not result['reliefweb']['live_eligible']


def test_usgs_normalization_and_budget():
    adapter = USGSAdapter(fetcher=lambda url, c: {'type': 'FeatureCollection', 'features': [feature(1), feature(2)]})
    records, errors = adapter.collect(config(collection={'public_sources': True, 'max_records': 1}))
    assert len(records) == 1 and errors
    assert records[0].date_text.startswith('2024-01-01')
    assert records[0].geometry['coordinates'] == [90, 24]
    assert 'contributor=us' in adapter.provenance()['request_url']


def test_country_requires_explicit_geometry_filter():
    adapter = USGSAdapter(fetcher=lambda *_: pytest.fail('Must not call transport'))
    with pytest.raises(ValueError, match='bbox'):
        adapter.collect(config(study_area={'country': 'Bangladesh'}))


@pytest.mark.parametrize('url', ['http://earthquake.usgs.gov/fdsnws/event/1/query',
    'https://127.0.0.1/fdsnws/event/1/query', 'https://earthquake.usgs.gov.evil.example/fdsnws/event/1/query',
    'https://user:password@earthquake.usgs.gov/fdsnws/event/1/query',
    'https://earthquake.usgs.gov:444/fdsnws/event/1/query', 'https://earthquake.usgs.gov/other'])
def test_url_allowlist(url):
    with pytest.raises(ValueError):
        safe_catalog_url(url)


def test_private_dns_and_redirects_are_refused():
    with pytest.raises(ValueError, match='public addresses'):
        fetch_catalog('https://earthquake.usgs.gov/fdsnws/event/1/query', config(),
                      resolver=lambda *a, **k: [(None, None, None, None, ('127.0.0.1', 443))])
    with pytest.raises(ValueError, match='redirect'):
        NoRedirect().redirect_request(None, None, 302, '', {}, 'http://127.0.0.1')


class Response(BytesIO):
    status = 200


def test_retry_after_then_success_and_response_limit():
    calls, delays = [], []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 429, '', {'Retry-After': '2'}, None)
            return Response(json.dumps({'type': 'FeatureCollection', 'features': []}).encode())
    resolver = lambda *a, **k: [(None, None, None, None, ('8.8.8.8', 443))]
    result = fetch_catalog('https://earthquake.usgs.gov/fdsnws/event/1/query', config(),
                           opener=Opener(), resolver=resolver, pause=delays.append)
    assert result['features'] == [] and delays == [2] and len(calls) == 2
    class Huge:
        def open(self, *a, **k):
            return Response(b'x' * 1025)
    with pytest.raises(ValueError, match='max_bytes'):
        fetch_catalog('https://earthquake.usgs.gov/fdsnws/event/1/query',
                      config(collection={'public_sources': True, 'max_bytes': 1024}),
                      opener=Huge(), resolver=resolver)
