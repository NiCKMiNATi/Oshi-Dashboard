from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionDep
from app.models import Keyword, Oshi
from app.schemas import OshiCreate, OshiPatch, OshiRead
from app.scoring import rescore

router = APIRouter(prefix="/api/oshi", tags=["oshi"])


def require_oshi(session: SessionDep, oshi_id: int) -> Oshi:
    oshi = session.get(Oshi, oshi_id)
    if oshi is None:
        raise HTTPException(404, "Oshi not found")
    return oshi


@router.get("", response_model=list[OshiRead])
def list_oshi(session: SessionDep):
    return session.scalars(
        select(Oshi).options(selectinload(Oshi.keywords)).order_by(Oshi.priority.desc(), Oshi.id)
    ).all()


@router.post("", response_model=OshiRead, status_code=201)
def create_oshi(payload: OshiCreate, session: SessionDep):
    oshi = Oshi(**payload.model_dump(exclude={"keywords"}))
    oshi.keywords = [Keyword(**keyword.model_dump()) for keyword in payload.keywords]
    session.add(oshi)
    session.commit()
    session.refresh(oshi)
    return oshi


@router.patch("/{oshi_id}", response_model=OshiRead)
def patch_oshi(oshi_id: int, payload: OshiPatch, session: SessionDep):
    oshi = require_oshi(session, oshi_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"keywords"})
    for field, value in changes.items():
        setattr(oshi, field, value)
    if "keywords" in payload.model_fields_set:
        # Reuse exact matches to preserve IDs and avoid transient unique-key conflicts.
        existing = {keyword.value: keyword for keyword in oshi.keywords}
        replacement = []
        for item in payload.keywords:
            keyword = existing.get(item.value) or Keyword(value=item.value)
            keyword.weight = item.weight
            replacement.append(keyword)
        oshi.keywords = replacement
    rescore(list(oshi.updates))
    session.commit()
    session.refresh(oshi)
    return oshi


@router.delete("/{oshi_id}", status_code=204)
def delete_oshi(oshi_id: int, session: SessionDep):
    oshi = require_oshi(session, oshi_id)
    updates = list(oshi.updates)
    for update in updates:
        update.oshi.remove(oshi)
    rescore(updates)
    session.delete(oshi)
    session.commit()
    return Response(status_code=204)
