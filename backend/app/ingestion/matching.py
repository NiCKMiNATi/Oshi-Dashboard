"""Deterministic identity matching; relevance scoring remains in app.scoring."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CatalogEntity, CatalogTracking, Oshi
from app.text import normalize


def normalized_text(value: str) -> str:
    return " ".join(normalize(value).split())


def identities(session: Session) -> list[tuple[Oshi, list[str]]]:
    active = session.scalars(
        select(Oshi)
        .where(Oshi.active.is_(True))
        .options(selectinload(Oshi.keywords))
        .order_by(Oshi.id)
    ).all()
    catalog = dict(
        session.execute(
            select(CatalogTracking.oshi_id, CatalogEntity)
            .join(CatalogEntity, CatalogEntity.id == CatalogTracking.entity_id)
            .options(selectinload(CatalogEntity.aliases))
        ).all()
    )
    result = []
    for oshi in active:
        terms = [oshi.name, *(keyword.value for keyword in oshi.keywords if keyword.weight > 0)]
        if entity := catalog.get(oshi.id):
            terms.extend([entity.name, *(alias.alias for alias in entity.aliases)])
        result.append((oshi, sorted({normalized_text(term) for term in terms})))
    return result


def term_matches(term: str, text: str) -> bool:
    significant = "".join(character for character in term if character.isalnum())
    if significant.isdecimal() or len(significant) < (3 if term.isascii() else 2):
        return False
    if term.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None
    return term in text


def match_oshi(known: list[tuple[Oshi, list[str]]], title: str, summary: str) -> list[Oshi]:
    text = normalized_text(f"{title}\n{summary}")
    return [oshi for oshi, terms in known if any(term_matches(term, text) for term in terms)]
