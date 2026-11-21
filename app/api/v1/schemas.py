"""
Esquemas de entrada/salida de la API v1.

Definen el contrato HTTP y validan lo que llega desde el cliente antes de que
toque la capa de datos. Este módulo NO contiene lógica de negocio (Principio SRP).
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


# SHA-256 en hexadecimal: lo calcula web antes de pedir el alta.
CHECKSUM_PATTERN = r"^[0-9a-f]{64}$"


class DocumentCreate(BaseModel):
    """
    Alta de un documento ya extraído.

    ``created_at`` no se acepta: la fecha la pone el servidor al guardar.
    """

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255, description="Nombre del PDF subido.")
    checksum: str = Field(pattern=CHECKSUM_PATTERN, description="SHA-256 del PDF en hexadecimal.")
    text: str = Field(description="Texto extraído, en Markdown.")
    page_count: int = Field(ge=1, description="Cantidad de páginas del PDF.")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos declarados por el PDF (autor, título, fechas).",
    )


class DocumentUpdate(BaseModel):
    """
    Campos modificables de un documento (actualización parcial).

    Sólo se listan los campos que el usuario puede editar: ``checksum``,
    ``page_count`` y ``created_at`` derivan del archivo original y se omiten
    a propósito para que no puedan reescribirse desde la API.
    """

    model_config = ConfigDict(extra="forbid")

    filename: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nombre del archivo mostrado en la interfaz.",
    )
    text: Optional[str] = Field(
        default=None,
        description="Texto extraído, editable para correcciones manuales.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos del PDF (autor, título, etc.).",
    )

    def to_changes(self) -> Dict[str, Any]:
        """Devuelve sólo los campos efectivamente enviados por el cliente."""
        return self.model_dump(exclude_unset=True, exclude_none=True)
