from fastapi import FastAPI

from app.core.config import settings
from app.db.base import Base, engine
from app import models  # noqa: F401  # ensures models are registered on Base.metadata
from app.routers import auth

app = FastAPI(title="Auth Service", version="0.1.0")
app.include_router(auth.router)


@app.on_event("startup")
def on_startup() -> None:
    # Safety net for first run; Alembic migrations remain the source of truth for schema changes
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
