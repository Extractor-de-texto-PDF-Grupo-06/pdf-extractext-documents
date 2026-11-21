"""
Proceso de administración: crea los índices de la colección de documentos.

Se corre una vez por despliegue, antes de que documents reciba tráfico (12-Factor XII):

    python -m app.admin.create_indexes

Termina con código 0 si los índices quedaron creados, y con 1 si no. El índice único
sobre ``checksum`` es la garantía contra duplicados: sin él, documents no debe arrancar.
"""
import asyncio
import logging
import sys

from pymongo.errors import PyMongoError

from app.core.config import settings
from app.infrastructure.database.connection import (
    DatabaseConnectionError,
    close_mongo_connection,
    connect_to_mongo,
)
from app.infrastructure.database.repository import DocumentRepository

logger = logging.getLogger(__name__)


async def run() -> int:
    """Crea los índices y devuelve el código de salida del proceso."""
    try:
        await connect_to_mongo()
        await DocumentRepository.ensure_indexes()
    except (DatabaseConnectionError, PyMongoError) as exc:
        logger.error("No se pudieron crear los índices: %s", exc)
        return 1
    finally:
        await close_mongo_connection()
    logger.info("Índices de documentos creados.")
    return 0


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
