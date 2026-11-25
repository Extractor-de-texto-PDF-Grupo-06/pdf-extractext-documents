"""
Contrato HTTP del microservicio documents (ver SPEC.md de pdf-extractext-orchestration).

Las rutas viven en la raíz: Traefik quita el prefijo /documents antes de reenviar.
El almacén de documentos se reemplaza por un doble a través de la inyección de dependencias
de FastAPI; la base real la cubren los tests de integración.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from app.api.v1.dependencies import get_document_store
from app.application.errors import DuplicateChecksum
from app.main import app

client = TestClient(app)

CHECKSUM = "a" * 64
VALID_ID = "65f1c2a9e4b0a1b2c3d4e5f6"


def _new_document(**overrides):
    body = {
        "filename": "informe.pdf",
        "checksum": CHECKSUM,
        "text": "# Título\n\nTexto",
        "page_count": 3,
        "metadata": {"author": "Ana"},
    }
    body.update(overrides)
    return body


@pytest.fixture
def repo():
    store = MagicMock()
    app.dependency_overrides[get_document_store] = lambda: store
    yield store
    app.dependency_overrides.clear()


# ── Alta ─────────────────────────────────────────────────────────


def test_create_returns_201_with_the_saved_document(repo):
    repo.create = AsyncMock(side_effect=lambda data: {**data, "id": VALID_ID})

    response = client.post("/", json=_new_document())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == VALID_ID
    assert body["checksum"] == CHECKSUM
    assert body["page_count"] == 3


def test_create_stamps_the_creation_date_on_the_server(repo):
    repo.create = AsyncMock(side_effect=lambda data: {**data, "id": VALID_ID})

    client.post("/", json=_new_document())

    saved = repo.create.await_args.args[0]
    assert isinstance(saved["created_at"], datetime)
    assert saved["created_at"].tzinfo is not None


def test_create_without_metadata_saves_an_empty_dict(repo):
    repo.create = AsyncMock(side_effect=lambda data: {**data, "id": VALID_ID})
    body = _new_document()
    del body["metadata"]

    response = client.post("/", json=body)

    assert response.status_code == 201
    assert repo.create.await_args.args[0]["metadata"] == {}


def test_create_with_a_repeated_checksum_returns_409(repo):
    repo.create = AsyncMock(side_effect=DuplicateChecksum())

    response = client.post("/", json=_new_document())

    assert response.status_code == 409
    assert "detail" in response.json()


@pytest.mark.parametrize(
    "overrides",
    [
        {"checksum": "abc"},                 # no son 64 caracteres
        {"checksum": "g" * 64},              # no es hexadecimal
        {"page_count": 0},                   # al menos una página
        {"filename": ""},                    # nombre vacío
        {"filename": "x" * 256},             # nombre demasiado largo
        {"text": None},                      # el texto es obligatorio
        {"created_at": "2026-01-01"},        # la fecha la pone el servidor
    ],
)
def test_create_rejects_invalid_documents_with_422(repo, overrides):
    repo.create = AsyncMock()

    response = client.post("/", json=_new_document(**overrides))

    assert response.status_code == 422
    repo.create.assert_not_called()


# ── Listado y búsqueda por checksum ──────────────────────────────


def test_list_returns_the_documents_page(repo):
    repo.get_all = AsyncMock(return_value=[{"id": VALID_ID, "filename": "informe.pdf"}])

    response = client.get("/?skip=10&limit=5")

    assert response.status_code == 200
    assert response.json() == {"data": [{"id": VALID_ID, "filename": "informe.pdf"}]}
    repo.get_all.assert_awaited_once_with(skip=10, limit=5)


@pytest.mark.parametrize("query", ["?skip=-1", "?limit=0", "?limit=501"])
def test_list_rejects_invalid_pagination(repo, query):
    repo.get_all = AsyncMock()

    response = client.get(f"/{query}")

    assert response.status_code == 422


def test_search_by_checksum_returns_the_match(repo):
    repo.get_by_checksum = AsyncMock(return_value={"id": VALID_ID, "checksum": CHECKSUM})

    response = client.get(f"/?checksum={CHECKSUM}")

    assert response.status_code == 200
    assert response.json() == {"data": [{"id": VALID_ID, "checksum": CHECKSUM}]}
    repo.get_by_checksum.assert_awaited_once_with(CHECKSUM)


def test_search_by_checksum_without_match_returns_an_empty_list(repo):
    repo.get_by_checksum = AsyncMock(return_value=None)

    response = client.get(f"/?checksum={CHECKSUM}")

    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_search_rejects_a_malformed_checksum(repo):
    repo.get_by_checksum = AsyncMock()

    response = client.get("/?checksum=abc")

    assert response.status_code == 422
    repo.get_by_checksum.assert_not_called()


# ── Lectura, edición y borrado por ID ────────────────────────────


def test_get_returns_the_document(repo):
    repo.get_by_id = AsyncMock(return_value={"id": VALID_ID, "text": "Hola"})

    response = client.get(f"/{VALID_ID}")

    assert response.status_code == 200
    assert response.json() == {"id": VALID_ID, "text": "Hola"}


def test_get_unknown_document_returns_404(repo):
    repo.get_by_id = AsyncMock(return_value=None)

    response = client.get(f"/{VALID_ID}")

    assert response.status_code == 404


def test_update_returns_the_updated_document(repo):
    repo.update = AsyncMock(return_value={"id": VALID_ID, "text": "Corregido"})

    response = client.put(f"/{VALID_ID}", json={"text": "Corregido"})

    assert response.status_code == 200
    assert response.json() == {"id": VALID_ID, "text": "Corregido"}
    repo.update.assert_awaited_once_with(VALID_ID, {"text": "Corregido"})


def test_update_without_fields_returns_400(repo):
    repo.update = AsyncMock()

    response = client.put(f"/{VALID_ID}", json={})

    assert response.status_code == 400
    repo.update.assert_not_called()


@pytest.mark.parametrize("field", ["checksum", "page_count", "created_at", "borrar_todo"])
def test_update_rejects_fields_that_cannot_change(repo, field):
    repo.update = AsyncMock()

    response = client.put(f"/{VALID_ID}", json={field: "x"})

    assert response.status_code == 422
    repo.update.assert_not_called()


def test_update_unknown_document_returns_404(repo):
    repo.update = AsyncMock(return_value=None)

    response = client.put(f"/{VALID_ID}", json={"text": "Corregido"})

    assert response.status_code == 404


def test_delete_returns_204_without_body(repo):
    repo.delete = AsyncMock(return_value=True)

    response = client.delete(f"/{VALID_ID}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_unknown_document_returns_404(repo):
    repo.delete = AsyncMock(return_value=False)

    response = client.delete(f"/{VALID_ID}")

    assert response.status_code == 404
