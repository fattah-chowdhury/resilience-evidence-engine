"""Curated discovery and a bounded, allowlisted USGS catalog adapter."""

import ipaddress
import json
import socket
import time
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ree.models import Record


def asset(name):
    return json.loads(files("ree").joinpath("assets", name).read_text(encoding="utf-8"))


class SourceAdapter(Protocol):
    def discover(self, config): ...
    def collect(self, config): ...
    def normalize(self, raw): ...
    def validate(self, record): ...
    def provenance(self): ...


def discover(config, registry=None):
    found = []
    for source in registry or asset("source_registry.json"):
        reasons = []
        if not set(config.topics) & set(source["topics"]):
            reasons.append("topic_mismatch")
        if not set(config.languages) & set(source["languages"]):
            reasons.append("language_mismatch")
        if config.study_area.country != "global" and "global" not in source["geographic_coverage"] \
                and config.study_area.country not in source["geographic_coverage"]:
            reasons.append("geography_mismatch")
        start = source["temporal_coverage"].get("start")
        end = source["temporal_coverage"].get("end")
        if (start and config.time.end and str(config.time.end) < start) or (
                end and config.time.start and str(config.time.start) > end):
            reasons.append("date_mismatch")
        relevant = not reasons
        if source["status"] != "implemented_unverified_live":
            reasons.append(source["status"])
        if source["raw_content_storage_allowed"] is not True:
            reasons.append("storage_rights_unresolved")
        if source["authentication_required"]:
            reasons.append("credentials_or_provider_approval_required")
        found.append({"id": source["id"], "relevant": relevant,
                      "live_eligible": not reasons, "reasons": reasons})
    return found


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Source redirect refused; review the registered endpoint")


def safe_catalog_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "earthquake.usgs.gov" \
            or parts.port not in (None, 443) or parts.username or parts.password \
            or parts.path != "/fdsnws/event/1/query" or parts.fragment:
        raise ValueError("Only the registered HTTPS USGS catalog query endpoint is permitted")


def fetch_catalog(url, config, opener=None, resolver=None, pause=time.sleep):
    safe_catalog_url(url)
    resolver = resolver or socket.getaddrinfo
    addresses = resolver("earthquake.usgs.gov", 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Source DNS did not resolve exclusively to public addresses")
    opener = opener or build_opener(NoRedirect())
    request = Request(url, headers={"User-Agent": "ResilienceEvidenceEngine/0.1.0",
                                    "Accept": "application/geo+json,application/json"})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=config.collection.timeout_seconds) as response:
                if response.status == 204:
                    return {"type": "FeatureCollection", "features": []}
                if response.status != 200:
                    raise ValueError(f"Unexpected source status: {response.status}")
                body = response.read(config.collection.max_bytes + 1)
                if len(body) > config.collection.max_bytes:
                    raise ValueError("Source response exceeds max_bytes")
                return json.loads(body)
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise ValueError(f"Source HTTP failure: {error.code}") from error
            retry = error.headers.get("Retry-After", "") if error.headers else ""
            if retry and not retry.isdigit():
                raise ValueError("Source requests a deferred retry; rerun later") from error
            delay = int(retry) if retry else 2 ** attempt
            if delay > 30:
                raise ValueError("Source requests a long retry; rerun later") from error
            pause(max(1, delay))


class USGSAdapter:
    def __init__(self, fetcher=fetch_catalog):
        self.fetcher = fetcher
        self.request_url = None

    def discover(self, config):
        return next(x for x in discover(config) if x["id"] == "usgs_catalog")

    def collect(self, config):
        if not self.discover(config)["live_eligible"]:
            raise ValueError("USGS catalog is not suitable for this topic/language/date selection")
        if config.study_area.admin_units:
            raise ValueError("USGS adapter cannot filter named administrative units; use bbox")
        if config.study_area.country != "global" and not config.study_area.bbox:
            raise ValueError("For a named country the USGS adapter requires a study_area.bbox")
        end = config.time.end or datetime.now(UTC).date()
        start = config.time.start or end - timedelta(days=30)
        if start > end:
            raise ValueError("Effective live start date exceeds end date")
        params = {"format": "geojson", "starttime": str(start),
                  "endtime": str(end) + "T23:59:59.999", "eventtype": "earthquake",
                  "contributor": "us", "minmagnitude": config.collection.min_magnitude,
                  "orderby": "time-asc", "limit": config.collection.max_records + 1}
        if config.study_area.bbox:
            w, s, e, n = config.study_area.bbox
            params.update(minlongitude=w, minlatitude=s, maxlongitude=e, maxlatitude=n)
        self.request_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode(params)
        body = self.fetcher(self.request_url, config)
        if not isinstance(body, dict) or body.get("type") != "FeatureCollection" \
                or not isinstance(body.get("features"), list):
            raise ValueError("USGS response is not a GeoJSON FeatureCollection")
        records, errors = [], []
        features = body["features"]
        if len(features) > config.collection.max_records:
            errors.append({"reason": "record_budget_exceeded; query is incomplete"})
        for index, raw in enumerate(features[:config.collection.max_records], 1):
            try:
                records.append(self.validate(self.normalize(raw)))
            except (ValueError, KeyError, TypeError, OverflowError):
                errors.append({"row": index, "reason": "invalid_USGS_feature"})
        return records, errors

    def normalize(self, raw):
        props, geom = raw["properties"], raw["geometry"]
        if props.get("net") != "us" or props.get("type") != "earthquake":
            raise ValueError("Only USGS-produced earthquake records are enabled")
        if geom["type"] != "Point" or len(geom["coordinates"]) < 2:
            raise ValueError("Unexpected USGS geometry")
        moment = datetime.fromtimestamp(props["time"] / 1000, UTC).isoformat()
        return {"source_id": "usgs_catalog", "source_record_id": str(raw["id"]),
                "provider_event_id": str(raw["id"]), "title": props.get("title") or str(raw["id"]),
                "text": props.get("title") or f"Earthquake catalog record {raw['id']}",
                "url": props.get("url") or "", "date_text": moment,
                "location_text": props.get("place") or "", "category": "earthquake",
                "geometry": {"type": "Point", "coordinates": geom["coordinates"][:2]},
                "geometry_role": "source_point", "sensitive": False,
                "quantities": [] if props.get("mag") is None else [
                    {"kind": "magnitude", "value": props["mag"], "unit": props.get("magType") or "unknown"}],
                "acquisition": {"kind": "live_api", "request_url": self.request_url,
                                "provider_status": props.get("status"), "original_feature": raw}}

    def validate(self, record):
        return Record.model_validate(record)

    def provenance(self):
        return {"adapter": "usgs-catalog-v1", "request_url": self.request_url,
                "scope": "USGS contributor only; bounded sample, no completeness assertion"}
