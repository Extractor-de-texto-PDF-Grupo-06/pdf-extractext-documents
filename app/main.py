"""
pdf-extractext-documents — Servidor FastAPI.

Levantar con:
    python -m app.main
"""
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.infrastructure.database.connection import connect_to_mongo, close_mongo_connection
from app.infrastructure.database.repository import DocumentRepository

# ── Logging ───────────────────────────────────────────────────────
# El nivel sale de la configuración (12-Factor III), no hardcodeado.
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    try:
        await DocumentRepository.ensure_indexes()
        yield
    finally:
        # También cerrar MongoDB si falla el índice durante el arranque.
        await close_mongo_connection()

# ── Aplicación FastAPI ────────────────────────────────────────────
app = FastAPI(
    title="pdf-extractext-documents",
    description="CRUD de los documentos extraídos de archivos PDF.",
    version="0.1.0",
    lifespan=lifespan,
)

# Montar rutas de la API v1 en /api/v1
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe: no toca la base a propósito."""
    return {"status": "ok"}


# ── Punto de entrada ──────────────────────────────────────────────
def main() -> None:
    """Inicia uvicorn con el puerto de la configuración (factor VII)."""
    logger.info("Iniciando %s en http://localhost:%d", settings.APP_NAME, settings.PORT)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    main()
