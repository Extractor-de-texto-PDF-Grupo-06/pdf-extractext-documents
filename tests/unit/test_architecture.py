"""
Regla de dependencias (Arquitectura Limpia): las dependencias apuntan hacia el núcleo.

application (el puerto DocumentStore y los errores) no conoce a nadie; la API depende de
application y no de MongoDB; la infraestructura implementa el puerto. Solo main.py, la raíz
de composición, conoce todas las capas.
"""

from pathlib import Path

from tests.architecture import imports_of, non_stdlib_imports

APP = Path(__file__).resolve().parents[2] / "app"


def test_application_solo_usa_la_biblioteca_estandar():
    assert (APP / "application").is_dir()
    assert non_stdlib_imports(APP / "application", own_package="app.application") == set()


def test_application_no_conoce_las_otras_capas():
    for layer in ("app.api", "app.infrastructure", "app.core", "app.admin", "app.main"):
        assert imports_of(APP / "application", layer) == set()


def test_la_api_no_conoce_la_base_de_datos():
    assert imports_of(APP / "api", "app.infrastructure") == set()
    assert imports_of(APP / "api", "pymongo") == set()
    assert imports_of(APP / "api", "motor") == set()


def test_la_infraestructura_no_conoce_la_api():
    assert imports_of(APP / "infrastructure", "app.api") == set()


def test_la_regla_detecta_un_import_de_otra_capa(tmp_path):
    (tmp_path / "documents.py").write_text(
        "from app.infrastructure.database.repository import DocumentRepository\n",
        encoding="utf-8",
    )

    assert imports_of(tmp_path, "app.infrastructure") == {
        "app.infrastructure.database.repository"
    }
