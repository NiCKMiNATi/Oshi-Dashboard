from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import SessionDep
from app.models import Oshi, Update
from app.schemas import StatusPatch, UpdateCreate, UpdateFilters, UpdatePatch, UpdateRead
from app.scoring import calculate_relevance

router = APIRouter(prefix="/api/updates", tags=["updates"])


def require_update(session: Session, update_id: int) -> Update:
    update = session.get(Update, update_id)
    if update is None:
        raise HTTPException(404, "Update not found")
    return update


def resolve_oshi(session: Session, ids: list[int]) -> list[Oshi]:
    if not ids:
        return []
    items = list(
        session.scalars(
            select(Oshi).where(Oshi.id.in_(ids)).options(selectinload(Oshi.keywords))
        ).all()
    )
    missing = sorted(set(ids) - {item.id for item in items})
    if missing:
        raise HTTPException(422, {"message": "Unknown oshi_ids", "ids": missing})
    return items


def build_update(payload: UpdateCreate, oshi: list[Oshi]) -> Update:
    update = Update(**payload.model_dump(exclude={"oshi_ids"}), oshi=oshi)
    update.relevance_score = calculate_relevance(update)
    return update


@router.get("", response_model=list[UpdateRead])
def list_updates(filters: Annotated[UpdateFilters, Query()], session: SessionDep):
    query = select(Update).options(selectinload(Update.oshi))
    if filters.oshi is not None:
        query = query.where(Update.oshi.any(Oshi.id == filters.oshi))
    if filters.category is not None:
        query = query.where(Update.category == filters.category)
    if filters.status is not None:
        query = query.where(Update.status == filters.status)
    if filters.min_score is not None:
        query = query.where(Update.relevance_score >= filters.min_score)
    return session.scalars(
        query.order_by(Update.relevance_score.desc(), Update.created_at.desc(), Update.id.desc())
        .offset(filters.offset)
        .limit(filters.limit)
    ).all()


@router.get("/{update_id}", response_model=UpdateRead)
def get_update(update_id: int, session: SessionDep):
    return require_update(session, update_id)


@router.post("", response_model=UpdateRead, status_code=201)
def create_update(payload: UpdateCreate, session: SessionDep):
    update = build_update(payload, resolve_oshi(session, payload.oshi_ids))
    session.add(update)
    session.commit()
    session.refresh(update)
    return update


@router.patch("/{update_id}", response_model=UpdateRead)
def patch_update(update_id: int, payload: UpdatePatch, session: SessionDep):
    update = require_update(session, update_id)
    changes = payload.model_dump(exclude_unset=True)
    current = {field: getattr(update, field) for field in UpdateCreate.model_fields}
    try:
        # Validate dates against the stored record, not just the supplied fields.
        merged = UpdateCreate.model_validate(current | changes)
    except ValidationError as error:
        raise HTTPException(422, jsonable_encoder(error.errors(include_context=False))) from error
    linked_oshi = resolve_oshi(session, merged.oshi_ids)
    for field, value in merged.model_dump(exclude={"oshi_ids"}).items():
        setattr(update, field, value)
    update.oshi = linked_oshi
    update.relevance_score = calculate_relevance(update)
    session.commit()
    session.refresh(update)
    return update


@router.patch("/{update_id}/status", response_model=UpdateRead)
def patch_status(update_id: int, payload: StatusPatch, session: SessionDep):
    update = require_update(session, update_id)
    update.status = payload.status
    session.commit()
    session.refresh(update)
    return update
