"""El repositorio traduce los errores de MongoDB a errores del núcleo."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import DuplicateKeyError

from app.application.errors import DuplicateChecksum
from app.application.ports import DocumentStore
from app.infrastructure.database.repository import DocumentRepository


def test_el_repositorio_cumple_el_puerto():
    assert isinstance(DocumentRepository, DocumentStore)


async def test_un_checksum_repetido_es_un_error_del_nucleo_y_no_de_pymongo():
    collection = MagicMock()
    collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("E11000 duplicate key"))

    with patch.object(DocumentRepository, "_collection", return_value=collection):
        with pytest.raises(DuplicateChecksum):
            await DocumentRepository.create({"checksum": "a" * 64})
