"""Opt-in, bounded public USGS response cache. Local/private data never enters it."""

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ree.models import canonical, digest
from ree.sources import fetch_catalog, safe_catalog_url


class CatalogCache:
    def __init__(self, directory, mode='reuse', ttl=3600, fetcher=fetch_catalog):
        if mode not in {'reuse', 'refresh', 'only'} or ttl < 0:
            raise ValueError('Invalid cache mode or TTL')
        self.root = Path(directory).resolve() / 'usgs-v1'
        if self.root.is_symlink():
            raise ValueError('Cache namespace must not be a symlink')
        self.mode, self.ttl, self.fetcher = mode, ttl, fetcher
        self.access = None

    @staticmethod
    def valid_body(body, budget):
        return isinstance(body, dict) and body.get('type') == 'FeatureCollection' \
            and isinstance(body.get('features'), list) and len(canonical(body).encode()) <= budget \
            and all(isinstance(f, dict) and isinstance(f.get('properties'), dict)
                    and f['properties'].get('net') == 'us'
                    and f['properties'].get('type') == 'earthquake' for f in body['features'])

    def read_entry(self, path, max_bytes=20000000):
        if path.is_symlink() or path.stat().st_size > max_bytes * 2 + 4096:
            raise ValueError('Unsafe or oversized cache entry')
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
            safe_catalog_url(entry['request_url'])
            if entry['schema'] != 1 or path.stem != digest(entry['request_url']) \
                    or entry['body_hash'] != digest(entry['body']) \
                    or not self.valid_body(entry['body'], max_bytes):
                raise ValueError('Invalid cache metadata')
            fetched = datetime.fromisoformat(entry['fetched_at'])
            if fetched.tzinfo is None or fetched > datetime.now(UTC):
                raise ValueError('Invalid cache timestamp')
            return entry
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise ValueError('Corrupt cache; inspect or use ree cache clear') from error

    def __call__(self, url, config):
        safe_catalog_url(url)
        path = self.root / (digest(url) + '.json')
        entry = self.read_entry(path, config.collection.max_bytes) if path.exists() else None
        fresh = entry and (datetime.now(UTC) - datetime.fromisoformat(entry['fetched_at'])).total_seconds() <= self.ttl
        if self.mode != 'refresh' and fresh:
            self.access = {k: entry[k] for k in ('request_url', 'body_hash', 'fetched_at')}
            self.access['status'] = 'cache_hit'
            return entry['body']
        if self.mode == 'only':
            raise ValueError('No fresh cached response; cache-only mode makes no network request')
        body = self.fetcher(url, config)
        if not self.valid_body(body, config.collection.max_bytes):
            raise ValueError('Invalid response cannot enter public USGS cache')
        entry = {'schema': 1, 'request_url': url, 'body': body, 'body_hash': digest(body),
                 'fetched_at': datetime.now(UTC).isoformat()}
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(canonical(entry))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        self.access = {k: entry[k] for k in ('request_url', 'body_hash', 'fetched_at')}
        self.access['status'] = 'network_fetch'
        return body

    def entries(self):
        return [p for p in sorted(self.root.glob('*.json')) if re.fullmatch(r'[a-f0-9]{64}\.json', p.name)]

    def status(self):
        rows = []
        for path in self.entries():
            try:
                entry = self.read_entry(path)
                rows.append({'key': path.stem, 'valid': True, 'bytes': path.stat().st_size,
                             'fetched_at': entry['fetched_at'], 'body_hash': entry['body_hash']})
            except (OSError, ValueError):
                rows.append({'key': path.stem, 'valid': False})
        return {'entries': rows, 'count': len(rows), 'ttl_seconds': self.ttl}

    def clear(self):
        count = 0
        for path in self.entries():
            if path.is_symlink():
                raise ValueError('Refusing symlink in cache')
            path.unlink()
            count += 1
        return {'removed_entries': count}
