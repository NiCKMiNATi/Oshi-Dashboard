from fastapi import APIRouter
from sqlalchemy import func, select

from app.database import SessionDep
from app.models import Oshi, Update, UpdateCategory, UpdateStatus
from app.schemas import StatsRead

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsRead)
def get_stats(session: SessionDep):
    by_category = dict(
        session.execute(select(Update.category, func.count()).group_by(Update.category)).all()
    )
    by_status = dict(
        session.execute(select(Update.status, func.count()).group_by(Update.status)).all()
    )
    return StatsRead(
        total_oshi=session.scalar(select(func.count()).select_from(Oshi)),
        active_oshi=session.scalar(
            select(func.count()).select_from(Oshi).where(Oshi.active.is_(True))
        ),
        total_updates=session.scalar(select(func.count()).select_from(Update)),
        by_category={category: by_category.get(category, 0) for category in UpdateCategory},
        by_status={status: by_status.get(status, 0) for status in UpdateStatus},
    )
