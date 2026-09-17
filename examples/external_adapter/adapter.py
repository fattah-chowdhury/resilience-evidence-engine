"""External adapter demonstration: synthetic fixture, no network or credentials."""
from ree.models import Record

SOURCE = {'id': 'synthetic_external', 'provider': 'REE synthetic adapter example',
          'origin_group': None, 'status': 'synthetic_fixture', 'license': 'MIT',
          'raw_content_storage_allowed': True, 'redistribution_allowed': True}


class FixtureAdapter:
    def discover(self, config):
        return {'live_eligible': 'earthquake' in config.topics, 'synthetic': True}

    def normalize(self, raw):
        return {'source_record_id': raw['id'], 'source_id': SOURCE['id'],
                'text': 'Synthetic extension test: earthquake report.', 'category': 'earthquake',
                'date_text': '2024-01-01', 'location_text': 'Synthetic source point',
                'geometry': {'type': 'Point', 'coordinates': [90, 24]},
                'geometry_role': 'source_point', 'sensitive': False,
                'acquisition': {'kind': 'synthetic_adapter_fixture', 'network_used': False}}

    def validate(self, record):
        return Record.model_validate(record)

    def collect(self, config):
        return [self.validate(self.normalize({'id': 'synthetic-external-1'}))], []

    def provenance(self):
        return {'adapter': 'synthetic-external-v1', 'network_used': False,
                'scope': 'Extension demonstration; not a live source acceptance test'}
