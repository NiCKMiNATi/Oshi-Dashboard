import re

from app.models import Update, UpdateCategory
from app.text import normalize

JAPAN_LOCATIONS = re.compile(
    r"日本|東京|大阪|横浜|京都|名古屋|福岡|札幌|神戸|千葉|埼玉|仙台|広島|沖縄|"
    r"\b(japan|jp|tokyo|osaka|yokohama|kyoto|nagoya|fukuoka|sapporo|kobe|"
    r"chiba|saitama|sendai|hiroshima|okinawa)\b"
)
EDITORIAL_MARKERS = re.compile(r"\b(opinion|editorial)\b|コラム|考察")


def calculate_relevance(update: Update) -> int:
    """Apply each v0.1 signal at most once. No I/O or clock dependence."""
    followed = [oshi for oshi in update.oshi if oshi.active]
    text = normalize(f"{update.title}\n{update.summary}")
    score = 40 if followed else 0
    if any(
        keyword.weight > 0 and normalize(keyword.value) in text
        for oshi in followed
        for keyword in oshi.keywords
    ):
        score += 25
    if update.category == UpdateCategory.EVENT and JAPAN_LOCATIONS.search(
        normalize(update.location or "")
    ):
        score += 20
    if update.deadline is not None:
        score += 20
    if update.category == UpdateCategory.MERCH:
        score += 10
    if not followed and EDITORIAL_MARKERS.search(normalize(update.title)):
        score -= 30
    return max(0, min(100, score))


def rescore(updates: list[Update]) -> None:
    for update in updates:
        update.relevance_score = calculate_relevance(update)
