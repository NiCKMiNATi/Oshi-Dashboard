"""Strict, small JSON source configuration. No personal URLs in source code."""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import ROOT_DIR
from app.models import UpdateCategory
from app.schemas import SourceURL


class ConfigError(Exception):
    pass


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$")
    type: Literal["rss"] = "rss"
    url: SourceURL
    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool = True
    category_hint: UpdateCategory | None = None


class SourcesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[SourceConfig] = Field(default_factory=list, max_length=100)


def config_path() -> Path:
    path = Path(os.environ.get("OSHI_SOURCES_PATH", "local/sources.json")).expanduser()
    return (ROOT_DIR / path).resolve()


def load_sources(path: Path, source_key: str | None = None) -> list[SourceConfig]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if source_key:
            raise ConfigError(f"Source {source_key!r} is not configured; missing {path}") from None
        return []
    except (OSError, UnicodeError):
        raise ConfigError(f"Cannot read source configuration: {path}") from None
    try:
        config = SourcesConfig.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        # Validation exceptions can contain secret feed URLs; show the schema location instead.
        raise ConfigError(f"Invalid source configuration: {path}. See docs/ingestion.md.") from None
    keys = [source.key for source in config.sources]
    if len(keys) != len(set(keys)):
        raise ConfigError("Source keys must be unique, including disabled sources.")
    selected = [source for source in config.sources if source.enabled]
    if source_key:
        selected = [source for source in selected if source.key == source_key]
        if not selected:
            raise ConfigError(f"Source {source_key!r} is unknown or disabled.")
    return selected
