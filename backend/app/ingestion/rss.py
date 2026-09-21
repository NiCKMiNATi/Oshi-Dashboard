"""Bounded HTTP transport and RSS/Atom parsing. No database or scheduler access."""

import calendar
import http.client
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import feedparser

from app.ingestion.config import SourceConfig
from app.ingestion.contracts import FetchedItem, FetchResult, FetchState, SourceError

MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 10
TOTAL_TIMEOUT = 30
USER_AGENT = "OshiDashboard/0.1 (personal RSS/Atom reader)"


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        self.handle_starttag(tag, [])


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join("".join(parser.parts).split())


def download(url: str, state: FetchState) -> tuple[bytes, dict[str, str], str, bool]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/atom+xml, application/rss+xml, */*"}
    if state.etag:
        headers["If-None-Match"] = state.etag
    if state.last_modified:
        headers["If-Modified-Since"] = state.last_modified
    started = time.monotonic()
    for _ in range(4):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
            raise SourceError("Feed URL must be HTTP(S), without embedded credentials.")
        remaining = TOTAL_TIMEOUT - (time.monotonic() - started)
        if remaining <= 0:
            raise SourceError("Feed request timed out.")
        connection_type = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        connection = connection_type(parsed.hostname, parsed.port, timeout=min(TIMEOUT, remaining))
        try:
            target = parsed.path or "/"
            if parsed.query:
                target += "?" + parsed.query
            connection.request("GET", target, headers=headers)
            with connection.getresponse() as response:
                metadata = {key.lower(): value for key, value in response.getheaders()}
                if response.status == 304:
                    return b"", metadata, url, True
                if response.status in (301, 302, 303, 307, 308):
                    if "location" not in metadata:
                        raise SourceError("Feed redirect has no destination.")
                    next_url = urljoin(url, metadata["location"])
                    if parsed.scheme == "https" and urlsplit(next_url).scheme != "https":
                        raise SourceError("Refusing a feed redirect from HTTPS to HTTP.")
                    url = next_url
                    continue
                if response.status != 200:
                    raise SourceError(f"Feed returned HTTP {response.status}.")
                if metadata.get("content-encoding", "identity").lower() != "identity":
                    raise SourceError("Feed ignored the identity encoding request.")
                chunks: list[bytes] = []
                size = 0
                while chunk := response.read1(min(65536, MAX_BYTES + 1 - size)):
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise SourceError("Feed exceeds the 2 MiB limit.")
                    if time.monotonic() - started > TOTAL_TIMEOUT:
                        raise SourceError("Feed request timed out.")
                return b"".join(chunks), metadata, url, False
        except (OSError, http.client.HTTPException, ValueError):
            raise SourceError("Feed network request failed or timed out.") from None
        finally:
            connection.close()
    raise SourceError("Feed exceeded the redirect limit.")


def parse_feed(body: bytes, source: SourceConfig, url: str) -> tuple[FetchedItem, ...]:
    parsed = feedparser.parse(
        body, response_headers={"content-location": url, "content-type": "application/xml"}
    )
    if not parsed.get("version", "").startswith(("rss", "atom")):
        raise SourceError("Response is not a recognized RSS/Atom feed.")
    if parsed.get("bozo") and not isinstance(
        parsed.get("bozo_exception"), feedparser.CharacterEncodingOverride
    ):
        raise SourceError("RSS/Atom feed is malformed.")
    items = []
    for entry in parsed.entries:
        published = entry.get("published_parsed")
        published_at = None
        if published:
            try:
                published_at = datetime.fromtimestamp(calendar.timegm(published), UTC)
            except (OverflowError, ValueError):
                pass
        summary = entry.get("summary")
        if not summary and entry.get("content"):
            summary = entry.content[0].get("value", "")
        items.append(
            FetchedItem(
                source_key=source.key,
                external_key=entry.get("id") or None,
                title=plain_text(entry.get("title", ""))[:500],
                summary=plain_text(summary or "")[:20000],
                source_url=urljoin(url, entry.get("link", "")) if entry.get("link") else "",
                published_at=published_at,
                category_hint=source.category_hint,
            )
        )
    return tuple(items)


class RSSAdapter:
    def __init__(self, source: SourceConfig):
        self.source = source
        self.source_key = source.key
        self.name = source.name or source.key
        self.cache_key = source.model_dump_json()

    def fetch(self, state: FetchState) -> FetchResult:
        body, headers, url, not_modified = download(self.source.url, state)
        return FetchResult(
            items=() if not_modified else parse_feed(body, self.source, url),
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            not_modified=not_modified,
        )
