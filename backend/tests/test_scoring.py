from datetime import UTC, datetime

import pytest

from app.models import Keyword, Oshi, OshiType, Update, UpdateCategory
from app.scoring import calculate_relevance


def example_update(**overrides):
    return Update(
        title="Announcement",
        summary="",
        category=UpdateCategory.NEWS,
        oshi=[],
        deadline=None,
        location=None,
        **overrides,
    )


def followed_oshi(*, active=True, weight=25):
    return Oshi(
        name="Ryujin",
        type=OshiType.IDOL,
        active=active,
        keywords=[Keyword(value="Ryujin", weight=weight)],
    )


@pytest.mark.parametrize(
    ("signal", "expected"),
    [
        ("none", 0),
        ("followed_oshi", 40),
        ("priority_keyword", 65),
        ("japan_event", 20),
        ("action_deadline", 20),
        ("merchandise", 10),
        ("irrelevant_editorial", 0),
    ],
)
def test_individual_scoring_signals(signal, expected):
    update = example_update()
    if signal in {"followed_oshi", "priority_keyword"}:
        update.oshi = [followed_oshi()]
    if signal == "priority_keyword":
        update.summary = "ＲＹＵＪＩＮ interview"
    if signal == "japan_event":
        update.category = UpdateCategory.EVENT
        update.location = "東京・日本"
    if signal == "action_deadline":
        update.deadline = datetime(2020, 1, 1, tzinfo=UTC)
    if signal == "merchandise":
        update.category = UpdateCategory.MERCH
    if signal == "irrelevant_editorial":
        update.title = "Opinion: market trends"
        update.deadline = datetime(2026, 10, 1, tzinfo=UTC)
        update.category = UpdateCategory.MERCH
    assert calculate_relevance(update) == expected


def test_signals_do_not_stack_and_clamp_at_100():
    update = example_update()
    update.oshi = [followed_oshi(), followed_oshi()]
    update.oshi[0].keywords.append(Keyword(value="interview", weight=100))
    update.title = "Ryujin interview Ryujin"
    assert calculate_relevance(update) == 65
    update.category = UpdateCategory.EVENT
    update.location = "Tokyo, Japan"
    update.deadline = datetime(2026, 10, 1, tzinfo=UTC)
    assert calculate_relevance(update) == 100


def test_inactive_oshi_and_zero_weight_keywords_do_not_score():
    update = example_update()
    update.oshi = [followed_oshi(active=False)]
    update.title = "Ryujin"
    assert calculate_relevance(update) == 0
    update.oshi = [followed_oshi(weight=0)]
    assert calculate_relevance(update) == 40


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("大阪", 20),
        ("TOKYO, JAPAN", 20),
        ("JP", 20),
        ("Seoul, South Korea", 0),
        ("Online", 0),
        ("Japanology Center, London", 0),
        (None, 0),
    ],
)
def test_japan_event_location_boundaries(location, expected):
    update = example_update()
    update.category = UpdateCategory.EVENT
    update.location = location
    assert calculate_relevance(update) == expected


def test_non_events_and_relevant_editorials():
    update = example_update()
    update.location = "Tokyo"
    assert calculate_relevance(update) == 0
    update.title = "Editorial: Ryujin"
    update.oshi = [followed_oshi()]
    assert calculate_relevance(update) == 65
