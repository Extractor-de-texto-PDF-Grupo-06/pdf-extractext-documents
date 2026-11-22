"""
Endpoints del CRUD de documentos.

Las rutas viven en la raíz: Traefik quita el prefijo /documents antes de reenviar,
así el servicio no sabe en qué ruta pública está publicado.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo.errors import DuplicateKeyError

from app.api.v1.schemas import CHECKSUM_PATTERN, DocumentCreate, DocumentUpdate
from app.infrastructure.database.repository import DocumentRepository

router = APIRouter()

_NOT_FOUND = "Documento no encontrado."


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Guardar un documento extraído",
    response_description="El documento guardado, con su ID.",
)
async def create_document(document: DocumentCreate):
    """
    Guarda un documento. El índice único sobre ``checksum`` es la garantía contra
    duplicados, también cuando dos altas del mismo PDF llegan a la vez.
    """
    data = document.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    try:
        return await DocumentRepository.create(data)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un documento con ese checksum.",
        ) from exc


@router.get(
    "/",
    summary="Listar documentos o buscar por checksum",
    response_description="Lista de documentos, sin el texto.",
)
async def list_documents(
    skip: int = Query(default=0, ge=0, description="Documentos a omitir."),
    limit: int = Query(default=100, ge=1, le=500, description="Máximo de documentos a devolver."),
    checksum: Optional[str] = Query(
        default=None,
        pattern=CHECKSUM_PATTERN,
        description="Si se indica, devuelve solo el documento con ese checksum (0 o 1).",
    ),
):
    """Lista paginada, o búsqueda exacta por checksum para detectar duplicados."""
    if checksum is not None:
        doc = await DocumentRepository.get_by_checksum(checksum)
        return {"data": [doc] if doc else []}
    docs = await DocumentRepository.get_all(skip=skip, limit=limit)
    return {"data": docs}


@router.get(
    "/{doc_id}",
    summary="Obtener un documento por ID",
    response_description="El documento completo, con su texto.",
)
async def get_document(doc_id: str):
    doc = await DocumentRepository.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return doc


@router.put(
    "/{doc_id}",
    summary="Actualizar un documento",
    response_description="El documento actualizado.",
)
async def update_document(doc_id: str, data: DocumentUpdate):
    """Actualización parcial: solo ``filename``, ``text`` y ``metadata`` son editables."""
    changes = data.to_changes()
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviarse al menos un campo para actualizar.",
        )
    doc = await DocumentRepository.update(doc_id, changes)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return doc


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un documento",
)
async def delete_document(doc_id: str):
    if not await DocumentRepository.delete(doc_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
