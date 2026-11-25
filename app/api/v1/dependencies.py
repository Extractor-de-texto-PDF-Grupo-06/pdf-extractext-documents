"""
Cómo llega el almacén de documentos a los endpoints.

Los endpoints piden un DocumentStore y no saben cuál es: app.main guarda la
implementación en el estado de la aplicación, y los tests la reemplazan por un doble.
"""

from fastapi import Request

from app.application.ports import DocumentStore


def get_document_store(request: Request) -> DocumentStore:
    return request.app.state.document_store
