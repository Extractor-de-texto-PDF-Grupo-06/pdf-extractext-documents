"""
pdf-extractext-documents — Servidor FastAPI.

Levantar con:
    python -m app.main
"""
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status

from app.api.v1 import router as documents_router
from app.core.config import settings
from app.infrastructure.database.connection import (
    close_mongo_connection,
    connect_to_mongo,
    ping_database,
)

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
    """
    Abre la conexión a MongoDB al arrancar y la cierra al apagarse (factor IX).

    Los índices no se crean acá: los crea el proceso de administración
    ``python -m app.admin.create_indexes``, antes del arranque (factor XII).
    """
    await connect_to_mongo()
    try:
        yield
    finally:
        await close_mongo_connection()

# ── Aplicación FastAPI ────────────────────────────────────────────
app = FastAPI(
    title="pdf-extractext-documents",
    description="CRUD de los documentos extraídos de archivos PDF.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health():
    """
    Responde 200 solo si MongoDB contesta: sin base, documents no puede atender nada.
    Se declara antes del CRUD para que ``/{doc_id}`` no capture ``/health``.
    """
    if not await ping_database():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB no responde.",
        )
    return {"status": "ok"}


# El CRUD vive en la raíz: Traefik quita el prefijo /documents antes de reenviar.
app.include_router(documents_router)


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
