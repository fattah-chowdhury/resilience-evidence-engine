"""Validated acquisition contract. No downloaded code or model is executed."""

import json
import math
from hashlib import sha256
from typing import Literal

from pydantic import Field, model_validator

from ree.config import StrictModel


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def check_geometry(geometry):
    if geometry is None:
        return
    if geometry.get("type") == "Point":
        xy = geometry.get("coordinates", [])
        if len(xy) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float))
                               or not math.isfinite(x) for x in xy):
            raise ValueError("Point must contain two finite numeric coordinates")
        if not (-180 <= xy[0] <= 180 and -90 <= xy[1] <= 90):
            raise ValueError("Coordinates outside WGS84 longitude/latitude ranges")
    elif geometry.get("type") in {"Polygon", "MultiPolygon"}:
        try:
            from shapely.geometry import shape
        except ImportError as error:
            raise ValueError("Polygon validation needs the optional [gis] dependencies") from error
        obj = shape(geometry)
        if obj.is_empty or not obj.is_valid or obj.has_z:
            raise ValueError("Polygon must be valid, nonempty and two-dimensional")
        w, s, e, n = obj.bounds
        if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
            raise ValueError("Polygon coordinates must be WGS84")
    else:
        raise ValueError("Supported geometry types: Point, Polygon, MultiPolygon")


class Record(StrictModel):
    source_record_id: str = Field(min_length=1, max_length=500)
    source_id: str = "local"
    title: str = ""
    text: str = Field(min_length=1, max_length=200000)
    url: str = ""
    language: str = "en"
    country: str = ""
    location_text: str = ""
    date_text: str | None = None
    published_at: str | None = None
    category: str | None = None
    provider_event_id: str | None = None
    geometry: dict | None = None
    geometry_role: Literal["source_point", "admin_centroid", "model_reference", "area",
                           "unknown"] = "unknown"
    quantities: list[dict] = Field(default_factory=list)
    sensitive: bool = True
    acquisition: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_record(self):
        if not self.text.strip():
            raise ValueError("text must not be blank")
        if self.url and not self.url.startswith(("https://", "http://")):
            raise ValueError("url must be HTTP(S) metadata; it will not be fetched")
        check_geometry(self.geometry)
        if self.geometry and self.geometry.get("type") == "Point" and self.geometry_role == "area":
            raise ValueError("An area cannot be represented by an unmarked Point")
        if self.geometry and self.geometry.get("type") != "Point" and self.geometry_role != "area":
            raise ValueError("Polygon geometries require geometry_role: area")
        for quantity in self.quantities:
            if not {"kind", "unit", "value"} <= quantity.keys() or not isinstance(quantity["kind"], str) \
                    or not isinstance(quantity["unit"], str) or isinstance(quantity["value"], bool) \
                    or not isinstance(quantity["value"], (int, float)) or not math.isfinite(quantity["value"]):
                raise ValueError("Each quantity requires kind, unit and a finite numeric value")
        canonical(self.model_dump(mode="json"))
        return self
