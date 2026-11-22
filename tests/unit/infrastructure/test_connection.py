"""
La contraseña de MongoDB nunca aparece en los logs ni en los mensajes de error.

MONGODB_URI trae usuario y contraseña (el compose de orchestration la arma así), y lo que
se escribe en stdout termina en los logs de Docker, que cualquiera con acceso al host lee.
"""
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.infrastructure.database import connection
from app.infrastructure.database.connection import (
    DatabaseConnectionError,
    connect_to_mongo,
    mask_uri,
)

URI_CON_CLAVE = "mongodb://admin:Secreta123@mongodb:27017/?authSource=admin"


@pytest.mark.parametrize(
    ("uri", "esperada"),
    [
        (
            "mongodb://admin:Secreta123@mongodb:27017/?authSource=admin",
            "mongodb://admin:***@mongodb:27017/?authSource=admin",
        ),
        (
            "mongodb+srv://lector:otra-clave@cluster0.ejemplo.net/base",
            "mongodb+srv://lector:***@cluster0.ejemplo.net/base",
        ),
        (
            "mongodb://admin:Secreta123@mongo1:27017,mongo2:27017/?replicaSet=rs0",
            "mongodb://admin:***@mongo1:27017,mongo2:27017/?replicaSet=rs0",
        ),
        # Una contraseña con caracteres reservados va codificada en la URI.
        (
            "mongodb://admin:a%40b%3Ac@mongodb:27017",
            "mongodb://admin:***@mongodb:27017",
        ),
    ],
)
def test_mask_uri_hides_the_password(uri, esperada):
    assert mask_uri(uri) == esperada


@pytest.mark.parametrize(
    "uri",
    [
        "mongodb://localhost:27017",
        "mongodb://mongodb:27017/?authSource=admin",
        # Solo usuario, sin contraseña (por ejemplo, autenticación con certificado).
        "mongodb://usuario@mongodb:27017",
        "no es una uri",
    ],
)
def test_mask_uri_leaves_uris_without_password_as_they_are(uri):
    assert mask_uri(uri) == uri


@pytest.fixture
def uri_con_clave(monkeypatch):
    monkeypatch.setattr(settings, "MONGODB_URI", URI_CON_CLAVE)


def _cliente_falso(ping: AsyncMock) -> MagicMock:
    cliente = MagicMock()
    cliente.admin.command = ping
    return cliente


async def test_connecting_does_not_log_the_password(uri_con_clave, caplog):
    cliente = _cliente_falso(AsyncMock(return_value={"ok": 1}))
    caplog.set_level(logging.DEBUG)

    with patch.object(connection, "AsyncIOMotorClient", return_value=cliente):
        await connect_to_mongo()

    assert "Secreta123" not in caplog.text
    assert "mongodb://admin:***@mongodb:27017" in caplog.text
    await connection.close_mongo_connection()


async def test_a_failed_connection_hides_the_password_in_logs_and_error(uri_con_clave, caplog):
    cliente = _cliente_falso(AsyncMock(side_effect=ServerSelectionTimeoutError("sin respuesta")))
    caplog.set_level(logging.DEBUG)

    with patch.object(connection, "AsyncIOMotorClient", return_value=cliente):
        with pytest.raises(DatabaseConnectionError) as error:
            await connect_to_mongo()

    assert "Secreta123" not in caplog.text
    assert "Secreta123" not in str(error.value)
    assert "mongodb://admin:***@mongodb:27017" in str(error.value)
