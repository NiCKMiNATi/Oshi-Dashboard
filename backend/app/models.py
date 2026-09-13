from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class OshiType(StrEnum):
    ANIME = "ANIME"
    CHARACTER = "CHARACTER"
    GAME = "GAME"
    IDOL = "IDOL"
    SEIYUU = "SEIYUU"
    ARTIST = "ARTIST"
    MANGA = "MANGA"
    OTHER = "OTHER"


class UpdateCategory(StrEnum):
    NEWS = "NEWS"
    EVENT = "EVENT"
    MERCH = "MERCH"
    COLLAB = "COLLAB"
    MOVIE = "MOVIE"
    RELEASE = "RELEASE"
    OTHER = "OTHER"


class UpdateStatus(StrEnum):
    NEW = "NEW"
    SAVED = "SAVED"
    INTERESTED = "INTERESTED"
    GOING = "GOING"
    BOUGHT = "BOUGHT"
    IGNORED = "IGNORED"


class UTCDateTime(TypeDecorator):
    """SQLite stores naive UTC; Python/API values always have a UTC offset."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamps require a timezone offset")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


def enum_column(enum: type[StrEnum]) -> Enum:
    return Enum(enum, native_enum=False, create_constraint=True, validate_strings=True)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Oshi(Base):
    __tablename__ = "oshi"
    __table_args__ = (CheckConstraint("priority BETWEEN 0 AND 100", name="oshi_priority_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[OshiType] = mapped_column(enum_column(OshiType))
    priority: Mapped[int] = mapped_column(Integer, default=50)
    active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    keywords: Mapped[list["Keyword"]] = relationship(
        back_populates="oshi",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Keyword.id",
    )
    updates: Mapped[list["Update"]] = relationship(
        secondary="update_oshi",
        back_populates="oshi",
        passive_deletes=True,
    )


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("oshi_id", "value", name="keyword_per_oshi"),
        CheckConstraint("weight BETWEEN 0 AND 100", name="keyword_weight_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    oshi_id: Mapped[int] = mapped_column(ForeignKey("oshi.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(String(200))
    weight: Mapped[int] = mapped_column(Integer, default=1)
    oshi: Mapped[Oshi] = relationship(back_populates="keywords")


class Update(Base):
    __tablename__ = "updates"
    __table_args__ = (
        CheckConstraint("relevance_score BETWEEN 0 AND 100", name="update_score_range"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="update_date_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[UpdateCategory] = mapped_column(enum_column(UpdateCategory), index=True)
    source: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2048), index=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    location: Mapped[str | None] = mapped_column(String(300))
    relevance_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[UpdateStatus] = mapped_column(
        enum_column(UpdateStatus),
        default=UpdateStatus.NEW,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    oshi: Mapped[list[Oshi]] = relationship(
        secondary="update_oshi",
        back_populates="updates",
        order_by="Oshi.id",
    )

    @property
    def oshi_ids(self) -> list[int]:
        return sorted(item.id for item in self.oshi)


class UpdateOshi(Base):
    __tablename__ = "update_oshi"

    update_id: Mapped[int] = mapped_column(
        ForeignKey("updates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    oshi_id: Mapped[int] = mapped_column(
        ForeignKey("oshi.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class CatalogEntity(Base):
    __tablename__ = "catalog_entities"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[OshiType] = mapped_column(enum_column(OshiType))
    provider: Mapped[str] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    aliases: Mapped[list["EntityAlias"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="EntityAlias.id"
    )


class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (UniqueConstraint("entity_id", "normalized_alias"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(200))
    normalized_alias: Mapped[str] = mapped_column(String(200), index=True)


class CatalogTracking(Base):
    """Optional identity link; deleting an Oshi removes only this link, not the catalog."""

    __tablename__ = "catalog_tracking"

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), primary_key=True
    )
    oshi_id: Mapped[int] = mapped_column(ForeignKey("oshi.id", ondelete="CASCADE"), unique=True)
