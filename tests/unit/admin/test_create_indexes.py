"""
Los índices se crean con un proceso de administración de una sola vez (factor XII),
no en cada arranque del servicio.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import OperationFailure

from app.admin import create_indexes
from app.infrastructure.database.connection import DatabaseConnectionError
from app.infrastructure.database.repository import DocumentRepository
from app.main import app, lifespan


@pytest.fixture
def mongo():
    with (
        patch.object(create_indexes, "connect_to_mongo", new_callable=AsyncMock) as connect,
        patch.object(create_indexes, "close_mongo_connection", new_callable=AsyncMock) as close,
        patch.object(
            create_indexes.DocumentRepository, "ensure_indexes", new_callable=AsyncMock
        ) as ensure,
    ):
        yield connect, close, ensure


async def test_creates_the_indexes_and_exits_with_0(mongo):
    connect, close, ensure = mongo

    assert await create_indexes.run() == 0

    connect.assert_awaited_once()
    ensure.assert_awaited_once()
    close.assert_awaited_once()


async def test_failing_index_exits_with_1_and_still_closes_the_connection(mongo):
    _, close, ensure = mongo
    ensure.side_effect = OperationFailure("hay checksums duplicados")

    assert await create_indexes.run() == 1

    close.assert_awaited_once()


async def test_unreachable_mongodb_exits_with_1(mongo):
    connect, _, ensure = mongo
    connect.side_effect = DatabaseConnectionError("sin MongoDB")

    assert await create_indexes.run() == 1

    ensure.assert_not_awaited()


async def test_checksum_index_is_unique():
    collection = MagicMock()
    collection.create_index = AsyncMock()
    with patch.object(DocumentRepository, "_collection", return_value=collection):
        await DocumentRepository.ensure_indexes()

    collection.create_index.assert_any_await("checksum", unique=True, name="uq_checksum")


async def test_service_startup_does_not_create_indexes():
    with (
        patch("app.main.connect_to_mongo", new_callable=AsyncMock),
        patch("app.main.close_mongo_connection", new_callable=AsyncMock) as close,
        patch.object(DocumentRepository, "ensure_indexes", new_callable=AsyncMock) as ensure,
    ):
        async with lifespan(app):
            pass

    ensure.assert_not_awaited()
    close.assert_awaited_once()
