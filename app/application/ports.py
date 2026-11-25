"""
Lo que la API necesita de un almacén de documentos.

La API depende de este puerto, no de MongoDB: DocumentRepository lo implementa, y la
raíz de composición (app.main) los une.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DocumentStore(Protocol):
    async def create(self, data: dict) -> dict:
        """Guarda un documento. Lanza DuplicateChecksum si el checksum ya existe."""
        ...

    async def get_by_checksum(self, checksum: str) -> Optional[dict]: ...

    async def get_by_id(self, doc_id: str) -> Optional[dict]: ...

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]: ...

    async def update(self, doc_id: str, data: dict) -> Optional[dict]: ...

    async def delete(self, doc_id: str) -> bool: ...
