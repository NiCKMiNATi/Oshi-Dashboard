from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.catalog import seed_catalog
from app.config import resolve_database_path
from app.database import create_schema, make_engine
from app.routes import discover, oshi, stats, updates


def create_app(database_path: Path | str | None = None) -> FastAPI:
    engine = make_engine(resolve_database_path(database_path))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            create_schema(engine)
            seed_catalog(engine)
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Oshi Dashboard API",
        version="0.1.0",
        description="Private local development API. Demo data is fictional.",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(oshi.router)
    app.include_router(updates.router)
    app.include_router(stats.router)
    app.include_router(discover.router)
    return app


app = create_app()
