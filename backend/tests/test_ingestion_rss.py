from datetime import UTC, datetime

import pytest

from app.ingestion import rss
from app.ingestion.config import SourceConfig
from app.ingestion.contracts import FetchState, SourceError
from app.ingestion.rss import RSSAdapter, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Fixture publisher</title>
<link>https://example.invalid/</link><description>Fictional test feed</description>
<item><guid isPermaLink="false">article-123</guid>
<title>[DEMO] 原神 &amp; ナヒーダ</title>
<description><![CDATA[<p>Fictional <b>announcement</b>.</p>]]></description>
<link>https://example.invalid/article?x=1&amp;y=2</link>
<pubDate>Sat, 19 Sep 2026 10:00:00 +0900</pubDate>
<category>EVENT</category></item></channel></rss>""".encode()

ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://example.invalid/news/">
<title>Fictional publisher</title><id>urn:feed</id><updated>2026-09-19T01:00:00Z</updated>
<entry><id>urn:entry:1</id><title>[DEMO] Higedan announcement</title>
<link rel="self" href="entry.xml"/><link rel="alternate" href="entry.html"/>
<content type="html">&lt;p&gt;Fictional announcement&lt;/p&gt;</content>
<published>2026-09-19T10:00:00+09:00</published></entry></feed>"""


def config(url="https://example.invalid/feed", **changes):
    return SourceConfig(key="rss-test", url=url, **changes)


def test_rss2_parsing_dates_html_guid_and_untrusted_category():
    fetched = parse_feed(RSS, config(), "https://example.invalid/feed")
    assert len(fetched) == 1
    article = fetched[0]
    assert article.title == "[DEMO] 原神 & ナヒーダ"
    assert article.summary == "Fictional announcement."
    assert article.external_key == "article-123"
    assert article.published_at == datetime(2026, 9, 19, 1, tzinfo=UTC)
    assert article.source_url == "https://example.invalid/article?x=1&y=2"
    assert article.category_hint is None


def test_atom_content_alternate_link_and_explicit_category_hint():
    article = parse_feed(ATOM, config(category_hint="RELEASE"), "https://example.invalid/feed")[0]
    assert article.external_key == "urn:entry:1"
    assert article.source_url == "https://example.invalid/news/entry.html"
    assert article.summary == "Fictional announcement"
    assert article.published_at == datetime(2026, 9, 19, 1, tzinfo=UTC)
    assert article.category_hint == "RELEASE"


def test_rss_without_optional_fields_and_invalid_date():
    body = (
        b'<rss version="2.0"><channel><title>Feed</title><item><title>Article</title>'
        b"<link>/article</link><pubDate>unknown</pubDate></item></channel></rss>"
    )
    article = parse_feed(body, config(), "https://example.invalid/feed")[0]
    assert article.summary == ""
    assert article.external_key is None
    assert article.published_at is None
    assert article.source_url == "https://example.invalid/article"


@pytest.mark.parametrize(
    "body", [b"", b"<html>Not a feed</html>", b'<rss version="2.0"><channel><item>']
)
def test_invalid_xml_is_a_source_failure(body):
    with pytest.raises(SourceError):
        parse_feed(body, config(), "https://example.invalid/feed")


def test_valid_empty_feed():
    assert (
        parse_feed(
            b'<rss version="2.0"><channel><title>Empty</title></channel></rss>',
            config(),
            "https://example.invalid/feed",
        )
        == ()
    )


def test_http_conditional_metadata_user_agent_and_redirect(rss_server):
    rss_server.responses["/redirect"] = (302, {"Location": "/feed"}, b"")
    rss_server.responses["/feed"] = (
        200,
        {"ETag": '"v1"', "Last-Modified": "Sat, 19 Sep 2026 01:00:00 GMT"},
        RSS,
    )
    adapter = RSSAdapter(config(rss_server.url + "/redirect"))
    first = adapter.fetch(FetchState())
    assert len(first.items) == 1
    assert first.etag == '"v1"'
    assert first.last_modified == "Sat, 19 Sep 2026 01:00:00 GMT"
    second = adapter.fetch(FetchState(first.etag, first.last_modified))
    assert second.not_modified
    assert second.items == ()
    headers = rss_server.requests[-1][1]
    assert headers["User-Agent"] == rss.USER_AGENT
    assert headers["If-None-Match"] == first.etag
    assert headers["If-Modified-Since"] == first.last_modified
    assert headers["Accept-Encoding"] == "identity"


@pytest.mark.parametrize("status", [403, 404, 429, 500, 503])
def test_http_errors_do_not_retry(rss_server, status):
    rss_server.responses["/feed"] = (status, {}, b"Failure")
    with pytest.raises(SourceError, match=f"HTTP {status}"):
        RSSAdapter(config(rss_server.url + "/feed")).fetch(FetchState())
    assert len(rss_server.requests) == 1


def test_redirect_limit_and_response_size_limit(rss_server, monkeypatch):
    rss_server.responses["/loop"] = (302, {"Location": "/loop"}, b"")
    with pytest.raises(SourceError, match="redirect limit"):
        RSSAdapter(config(rss_server.url + "/loop")).fetch(FetchState())
    assert len(rss_server.requests) == 4
    monkeypatch.setattr(rss, "MAX_BYTES", 10)
    rss_server.responses["/large"] = (200, {}, b"x" * 11)
    with pytest.raises(SourceError, match="limit"):
        RSSAdapter(config(rss_server.url + "/large")).fetch(FetchState())


def test_network_timeout_is_reported_without_feed_url(monkeypatch):
    def unavailable(*args, **kwargs):
        raise TimeoutError("secret URL")

    monkeypatch.setattr(rss.http.client.HTTPConnection, "request", unavailable)
    with pytest.raises(SourceError, match="failed or timed out") as error:
        RSSAdapter(config("http://127.0.0.1:9/feed?token=secret")).fetch(FetchState())
    assert "secret" not in str(error.value)
