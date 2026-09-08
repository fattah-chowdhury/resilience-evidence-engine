"""Strict, non-executable project configuration."""

import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("Configuration keys must be strings")  # noqa: TRY004 - invalid user config
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Project(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class StudyArea(StrictModel):
    country: str = Field(default="global", min_length=1)
    admin_units: list[str] = Field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None

    @model_validator(mode="after")
    def bounds(self):
        if self.bbox:
            w, s, e, n = self.bbox
            if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
                raise ValueError("bbox must be [west, south, east, north] in WGS84")
        return self


class TimeRange(StrictModel):
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("time.start must be on or before time.end")
        return self


class Collection(StrictModel):
    public_sources: bool = False
    max_records: int = Field(default=100, ge=1, le=1000, strict=True)
    sources: list[str] = Field(default_factory=lambda: ["usgs_catalog"])
    min_magnitude: float = Field(default=5, ge=-2, le=10)
    timeout_seconds: int = Field(default=15, ge=1, le=30)
    max_bytes: int = Field(default=10000000, ge=1024, le=20000000)


class Processing(StrictModel):
    human_review: bool = True
    llm_enabled: bool = False
    gazetteer: str | None = None
    taxonomy: str | None = None
    evidence_rules: str | None = None
    link_days: int = Field(default=3, ge=0, le=30)
    link_km: float = Field(default=30, ge=0, le=500)


class InputSpec(StrictModel):
    path: str = Field(min_length=1)
    columns: dict[str, str] = Field(default_factory=dict)
    sensitive: bool = True
    redistribution_allowed: bool = False
    license: str = "unknown"

    @model_validator(mode="after")
    def rights_declared(self):
        if self.redistribution_allowed and self.license.strip().casefold() in {"", "unknown"}:
            raise ValueError("A redistribution declaration requires a named license or rights basis")
        return self


class ProjectConfig(StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1, strict=True)
    project: Project
    study_area: StudyArea = Field(default_factory=StudyArea)
    time: TimeRange = Field(default_factory=TimeRange)
    mode: Literal["demo", "local", "live", "hybrid"] = "demo"
    inputs: list[InputSpec] = Field(default_factory=list)
    output_dir: str = "outputs"
    export_policy: Literal["private", "public"] = "private"
    topics: list[str] = Field(default_factory=lambda: ["flood", "earthquake", "tsunami"])
    languages: list[str] = Field(default_factory=lambda: ["en", "bn"])
    collection: Collection = Field(default_factory=Collection)
    processing: Processing = Field(default_factory=Processing)
    exports: list[str] = Field(default_factory=lambda: ["csv", "json", "geojson"])

    @model_validator(mode="after")
    def supported(self):
        if not self.topics or any(not x.strip() for x in self.topics):
            raise ValueError("topics must contain nonempty values")
        if not self.languages or any(not x.strip() for x in self.languages):
            raise ValueError("languages must contain nonempty codes")
        if not self.exports or set(self.exports) - {"csv", "json", "geojson", "parquet", "gpkg"}:
            raise ValueError("export targets: csv, json, geojson, parquet, gpkg")
        if self.processing.llm_enabled:
            raise ValueError("LLM execution is not implemented; set llm_enabled: false")
        if self.mode in {"local", "hybrid"} and not self.inputs:
            raise ValueError("local/hybrid mode requires at least one inputs entry")
        if self.mode == "demo" and self.inputs:
            raise ValueError("demo mode uses only the bundled fixture; use local or hybrid")
        if self.mode in {"live", "hybrid"} and not self.collection.public_sources:
            raise ValueError("live/hybrid mode requires collection.public_sources: true")
        return self

    def fingerprint(self):
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()


def load_config(path: Path) -> ProjectConfig:
    if path.stat().st_size > 65536:
        raise ValueError("Configuration exceeds 64 KiB limit")
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a YAML mapping")  # noqa: TRY004 - invalid user config
    return ProjectConfig.model_validate(data)


def initialize(path: Path) -> Path:
    config = ProjectConfig(project=Project(name=path.name))
    path.mkdir(parents=True, exist_ok=True)
    target = path / "project.yml"
    # Exclusive creation also refuses symlinks and protects existing projects.
    with target.open("x", encoding="utf-8") as stream:
        yaml.safe_dump(config.model_dump(mode="json"), stream, sort_keys=False)
    return target
