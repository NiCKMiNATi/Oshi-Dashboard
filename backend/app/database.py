from collections.abc import Generator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def make_engine(path: Path) -> Engine:
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(path)),
        connect_args={"check_same_thread": False, "autocommit": False, "timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        previous = connection.autocommit
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        connection.autocommit = previous

    return engine


def create_schema(engine: Engine) -> None:
    # Import all mappings before create_all; this only creates missing tables.
    from app import models  # noqa: F401

    Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_session(request: Request) -> Generator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
