"""Serve the real backend with a disposable seed DB for frontend verification."""

from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from app.database import make_engine
from app.main import create_app
from app.seed import seed_database

if __name__ == "__main__":
    with TemporaryDirectory(prefix="oshi-frontend-test-") as directory:
        path = Path(directory) / "integration.db"
        engine = make_engine(path)
        try:
            seed_database(engine)
        finally:
            engine.dispose()
        uvicorn.run(create_app(path), host="127.0.0.1", port=8000)
