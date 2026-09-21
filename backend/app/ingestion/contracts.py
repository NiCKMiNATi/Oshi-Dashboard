"""Adapter data contracts; adapters return data and never persist ORM objects."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class FetchedItem:
    source_key: str
    title: str
    source_url: str
    external_key: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    category_hint: str | None = None
    deadline: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = None


@dataclass(frozen=True)
class FetchState:
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class FetchResult:
    items: tuple[FetchedItem, ...] = ()
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


class SourceError(Exception):
    """A fetch/parse failure safe to display without credentials or feed contents."""


class SourceAdapter(Protocol):
    source_key: str
    name: str
    cache_key: str

    def fetch(self, state: FetchState) -> FetchResult: ...


@dataclass(frozen=True)
class FixtureAdapter:
    """Deterministic local adapter for tests; never enabled by production config."""

    source_key: str
    items: tuple[FetchedItem, ...]
    name: str = "Fixture source (fictional)"
    cache_key: str = "fixture"

    def fetch(self, state: FetchState) -> FetchResult:
        return FetchResult(items=self.items)
