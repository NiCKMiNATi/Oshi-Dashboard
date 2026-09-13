"""Small local discovery catalog. No provider calls or update/demo seeding."""

from sqlalchemy import Engine, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.models import CatalogEntity, CatalogTracking, EntityAlias, Oshi
from app.text import normalize

# Stable local identifiers are seed identities, not external service IDs.
LOCAL_ENTITIES = [
    ("higedan", "Official髭男dism", "ARTIST", "Japanese band", ["Higedan", "ヒゲダン", "髭男"]),
    ("itzy", "ITZY", "ARTIST", "Korean girl group", ["있지"]),
    ("aot", "進撃の巨人", "ANIME", "Attack on Titan", ["Attack on Titan", "AOT", "進撃"]),
    ("genshin", "原神", "GAME", "Genshin Impact", ["Genshin", "Genshin Impact"]),
    ("jjk", "呪術廻戦", "ANIME", "Jujutsu Kaisen", ["JJK", "Jujutsu Kaisen"]),
    ("gojo", "五条悟", "CHARACTER", "Character from 呪術廻戦", ["Gojo", "Gojo Satoru", "五条"]),
    ("hyouka", "氷菓", "ANIME", "Hyouka", ["Hyouka"]),
    ("yuma-uchida", "内田雄馬", "SEIYUU", "Japanese voice actor", ["Yuma Uchida", "Uchida Yuma"]),
]


def search_key(value: str) -> str:
    """NFKC/case folding plus whitespace removal, including full-width spaces."""
    return "".join(normalize(value).split())


def seed_catalog(engine: Engine) -> None:
    """Insert only missing catalog metadata; never read or write personal Oshi/updates."""
    with Session(engine) as session, session.begin():
        for external_id, name, kind, description, aliases in LOCAL_ENTITIES:
            session.execute(
                insert(CatalogEntity)
                .values(
                    provider="local",
                    external_id=external_id,
                    name=name,
                    type=kind,
                    description=description,
                )
                .on_conflict_do_nothing(index_elements=["provider", "external_id"])
            )
            entity_id = session.scalar(
                select(CatalogEntity.id).where(
                    CatalogEntity.provider == "local", CatalogEntity.external_id == external_id
                )
            )
            for alias in aliases:
                session.execute(
                    insert(EntityAlias)
                    .values(entity_id=entity_id, alias=alias, normalized_alias=search_key(alias))
                    .on_conflict_do_nothing(index_elements=["entity_id", "normalized_alias"])
                )


def match_rank(entity: CatalogEntity, query: str) -> int | None:
    canonical = search_key(entity.name)
    aliases = [alias.normalized_alias for alias in entity.aliases]
    if canonical == query:
        return 0
    if query in aliases:
        return 1
    if canonical.startswith(query):
        return 2
    if any(alias.startswith(query) for alias in aliases):
        return 3
    if query in canonical:
        return 4
    if any(query in alias for alias in aliases):
        return 5
    return None


def tracked_entities(session: Session, entities: list[CatalogEntity]) -> dict[int, Oshi]:
    """Explicit identity survives edits; legacy/manual rows match name or alias + type."""
    oshi = session.scalars(select(Oshi).order_by(Oshi.id)).all()
    by_id = {item.id: item for item in oshi}
    links = session.scalars(select(CatalogTracking)).all()
    linked_ids = {link.oshi_id for link in links}
    tracked = {link.entity_id: by_id[link.oshi_id] for link in links}
    for entity in entities:
        if entity.id in tracked:
            continue
        names = {search_key(entity.name), *(alias.normalized_alias for alias in entity.aliases)}
        existing = next(
            (
                item
                for item in oshi
                if item.id not in linked_ids
                and item.type == entity.type
                and search_key(item.name) in names
            ),
            None,
        )
        if existing is not None:
            tracked[entity.id] = existing
    return tracked
