from datetime import date, datetime
from typing import Annotated, ClassVar, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    field_validator,
    model_validator,
)

from app.models import OshiType, UpdateCategory, UpdateStatus
from app.text import normalize

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
Title = Annotated[str, Field(min_length=1, max_length=500)]
Summary = Annotated[str, Field(max_length=20000)]
Location = Annotated[str, Field(min_length=1, max_length=300)]
Score = Annotated[int, Field(ge=0, le=100, strict=True)]
PositiveID = Annotated[int, Field(gt=0, strict=True)]


def validate_source_url(value: str) -> str:
    TypeAdapter(HttpUrl).validate_python(value)
    return value


SourceURL = Annotated[
    str, Field(min_length=1, max_length=2048), AfterValidator(validate_source_url)
]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


class PatchSchema(Schema):
    non_nullable: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for name in self.model_fields_set & self.non_nullable:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class KeywordInput(Schema):
    value: ShortText
    weight: Score = 1


class KeywordRead(KeywordInput):
    id: int
    oshi_id: int


def unique_keywords(values: list[KeywordInput]) -> list[KeywordInput]:
    normalized = [normalize(item.value) for item in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Keywords must be unique after Unicode/case normalization")
    return values


Keywords = Annotated[list[KeywordInput], Field(max_length=100), AfterValidator(unique_keywords)]


class OshiCreate(Schema):
    name: ShortText
    type: OshiType
    priority: Score = 50
    active: bool = True
    keywords: Keywords = Field(default_factory=list)


class OshiPatch(PatchSchema):
    non_nullable = {"name", "type", "priority", "active", "keywords"}
    name: ShortText | None = None
    type: OshiType | None = None
    priority: Score | None = None
    active: bool | None = None
    keywords: Keywords | None = None


class OshiRead(Schema):
    id: int
    name: str
    type: OshiType
    priority: int
    active: bool
    created_at: datetime
    keywords: list[KeywordRead]


class DiscoverRead(Schema):
    id: int
    name: str
    type: OshiType
    description: str | None
    aliases: list[str]
    provider: str
    is_tracked: bool


def unique_ids(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise ValueError("oshi_ids must not contain duplicates")
    return values


OshiIDs = Annotated[list[PositiveID], Field(max_length=100), AfterValidator(unique_ids)]


class UpdateCreate(Schema):
    title: Title
    summary: Summary = ""
    category: UpdateCategory
    source: ShortText
    source_url: SourceURL
    published_at: AwareDatetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    deadline: AwareDatetime | None = None
    location: Location | None = None
    status: UpdateStatus = UpdateStatus.NEW
    oshi_ids: OshiIDs = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class UpdatePatch(PatchSchema):
    non_nullable = {"title", "summary", "category", "source", "source_url", "status", "oshi_ids"}
    title: Title | None = None
    summary: Summary | None = None
    category: UpdateCategory | None = None
    source: ShortText | None = None
    source_url: SourceURL | None = None
    published_at: AwareDatetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    deadline: AwareDatetime | None = None
    location: Location | None = None
    status: UpdateStatus | None = None
    oshi_ids: OshiIDs | None = None


class UpdateRead(Schema):
    id: int
    title: str
    summary: str
    category: UpdateCategory
    source: str
    source_url: str
    published_at: datetime | None
    start_date: date | None
    end_date: date | None
    deadline: datetime | None
    location: str | None
    relevance_score: int
    status: UpdateStatus
    created_at: datetime
    oshi_ids: list[int]


class StatusPatch(Schema):
    status: UpdateStatus


class StatsRead(Schema):
    total_oshi: int
    active_oshi: int
    total_updates: int
    by_category: dict[UpdateCategory, int]
    by_status: dict[UpdateStatus, int]


class UpdateFilters(Schema):
    oshi: Annotated[int, Field(gt=0)] | None = None
    category: UpdateCategory | None = None
    status: UpdateStatus | None = None
    min_score: Annotated[int, Field(ge=0, le=100)] | None = None
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    offset: Annotated[int, Field(ge=0)] = 0

    @field_validator("oshi", "min_score", "limit", "offset", mode="before")
    @classmethod
    def reject_decimal_query_values(cls, value):
        # Query values are strings; only integer spellings are accepted.
        if isinstance(value, str) and not value.isdecimal():
            raise ValueError("Must be a non-negative integer")
        return value
