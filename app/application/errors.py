"""Errores del núcleo: la API los traduce a HTTP sin saber qué base hay detrás."""


class DuplicateChecksum(Exception):
    """Ya hay un documento guardado con ese checksum."""
