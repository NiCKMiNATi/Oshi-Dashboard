from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.catalog import match_rank, search_key, tracked_entities
from app.database import SessionDep
from app.models import CatalogEntity, CatalogTracking, Keyword, Oshi
from app.schemas import DiscoverRead, OshiRead

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.get("", response_model=list[DiscoverRead])
def discover(
    session: SessionDep,
    q: Annotated[str, Query(max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    query = search_key(q)
    if not query:
        return []
    entities = session.scalars(
        select(CatalogEntity).options(selectinload(CatalogEntity.aliases))
    ).all()
    ranked = [
        (rank, entity) for entity in entities if (rank := match_rank(entity, query)) is not None
    ]
    ranked.sort(key=lambda item: (item[0], search_key(item[1].name), item[1].id))
    candidates = [entity for _, entity in ranked[:limit]]
    tracked = tracked_entities(session, candidates)
    return [
        DiscoverRead(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            description=entity.description,
            aliases=[item.alias for item in entity.aliases],
            provider=entity.provider,
            is_tracked=entity.id in tracked,
        )
        for entity in candidates
    ]


@router.post("/{entity_id}/track", response_model=OshiRead, status_code=201)
def track(entity_id: int, session: SessionDep, response: Response):
    # Acquire SQLite's write reservation BEFORE reading tracking state. Concurrent
    # requests then see the committed link instead of creating two personal rows.
    session.execute(
        update(CatalogEntity).where(CatalogEntity.id == entity_id).values(id=CatalogEntity.id)
    )
    entity = session.get(CatalogEntity, entity_id)
    if entity is None:
        raise HTTPException(404, "Catalog entity not found")
    existing = tracked_entities(session, [entity]).get(entity_id)
    if existing is not None:
        oshi = existing
        response.status_code = 200
    else:
        values = {
            search_key(value): value
            for value in [entity.name, *(item.alias for item in entity.aliases)]
        }
        oshi = Oshi(
            name=entity.name,
            type=entity.type,
            priority=50,
            active=True,
            keywords=[Keyword(value=value, weight=1) for value in values.values()],
        )
        session.add(oshi)
        session.flush()
    if session.get(CatalogTracking, entity_id) is None:
        session.add(CatalogTracking(entity_id=entity_id, oshi_id=oshi.id))
    session.commit()
    session.refresh(oshi)
    return oshi
