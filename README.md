# pdf-extractext-documents

Microservicio **documents** de pdf-extractext: el CRUD de los documentos extraídos de
archivos PDF. Es el único servicio que toca MongoDB.

**Universidad Tecnológica Nacional — Facultad Regional San Rafael**
**Ingeniería en Sistemas | Desarrollo de Software 2026**
**Integrantes: Mansalve Augusto, Praderio Valentín, Quiroga Constanza**

El sistema completo se levanta desde
[`pdf-extractext-orchestration`](https://github.com/Extractor-de-texto-PDF-Grupo-06/pdf-extractext-orchestration),
donde están la especificación y las decisiones de arquitectura. Este repositorio
conserva el historial desde el monolito de la Etapa 1.

## Qué hace y qué no

- **Hace:** guarda, lista, busca por checksum, edita y borra documentos.
- **No hace:** recibir PDFs, extraer texto ni calcular el checksum. Eso lo coordina
  `pdf-extractext-web`, que le pide a documents que guarde el resultado.

La garantía contra duplicados es el **índice único sobre `checksum`**: si dos altas del
mismo PDF llegan a la vez, la segunda recibe 409.

## Contrato HTTP

Las rutas viven en la raíz: Traefik publica el servicio en `/documents` y quita el
prefijo antes de reenviar. Los errores se responden como `{"detail": "…"}`.

| Método y ruta | Entrada | Respuesta |
|---|---|---|
| `POST /` | JSON `{filename, checksum, text, page_count, metadata?}` | `201` documento con `id` y `created_at` · `409` checksum repetido · `422` |
| `GET /?skip=&limit=` | `skip` ≥ 0, `limit` entre 1 y 500 | `200` `{"data": [...]}` sin `text`, del más nuevo al más viejo |
| `GET /?checksum=` | SHA-256 en hexadecimal (64 caracteres) | `200` `{"data": [...]}` con 0 o 1 documento |
| `GET /{id}` | — | `200` documento completo · `404` |
| `PUT /{id}` | JSON parcial `{filename?, text?, metadata?}` | `200` · `400` sin campos · `404` · `422` |
| `DELETE /{id}` | — | `204` · `404` |
| `GET /health` | — | `200` si MongoDB responde · `503` si no |

`checksum`, `page_count` y `created_at` no se pueden modificar: derivan del PDF original.

## Configuración

Por variables de entorno (ver [`.env.example`](.env.example)):

| Variable | Por defecto | Para qué |
|---|---|---|
| `PORT` | `8000` | Puerto HTTP (factor VII) |
| `MONGODB_URI` | `mongodb://localhost:27017` | Conexión a MongoDB, con credenciales si las tiene |
| `MONGODB_DB_NAME` | `pdf_extractext` | Base de datos |
| `MONGODB_TEST_DB_NAME` | `pdf_extractext_test` | Base de los tests de integración |
| `LOG_LEVEL` | `INFO` | Nivel de los logs, que van a stdout (factor XI) |

## Desarrollo

```bash
uv sync                                  # dependencias, incluidas las de desarrollo
uv run pytest                            # tests unitarios: sin red ni base
uv run pytest -m integration             # contra MongoDB (MONGODB_URI); se saltan si no responde
uv run python -m app.admin.create_indexes  # crear los índices (una vez por base)
uv run uvicorn app.main:app --reload     # servidor con recarga automática
```

### Índices: proceso de administración (factor XII)

El servicio **no** crea los índices al arrancar. Los crea
`python -m app.admin.create_indexes`, que termina con código 0 si quedaron creados y con 1
si no. En el sistema completo corre una vez antes de que documents arranque.

## Docker

```bash
docker build -t pdf-extractext-documents .
docker run --rm -e MONGODB_URI=mongodb://host.docker.internal:27017 -p 8000:8000 pdf-extractext-documents
docker run --rm -e MONGODB_URI=... pdf-extractext-documents python -m app.admin.create_indexes
```

La imagen es multi-stage: la final tiene solo el entorno virtual y el código, corre con
el usuario sin privilegios 10001 y declara un `HEALTHCHECK` sobre `/health`.

## Estructura

```
app/
├── application/       núcleo: el puerto DocumentStore y DuplicateChecksum (solo biblioteca estándar)
├── api/v1/            presentación: rutas, esquemas y la inyección del almacén
├── infrastructure/    MongoDB: conexión y DocumentRepository, que implementa DocumentStore
├── admin/             procesos de administración (create_indexes)
├── core/config/       Settings (variables de entorno)
└── main.py            raíz de composición: une la API con el repositorio y expone /health
tests/
├── unit/              contrato HTTP, health, índices, errores del repositorio y arquitectura
└── integration/       repositorio contra MongoDB real
```

**Regla de dependencias:** las dependencias apuntan hacia `application`. La API pide un
`DocumentStore` y recibe la implementación por inyección, así que no conoce MongoDB; el
repositorio traduce `DuplicateKeyError` de pymongo a `DuplicateChecksum`. Solo `main.py`
conoce todas las capas. `tests/unit/test_architecture.py` falla si alguien rompe la regla.

## Seguridad de la imagen

El escaneo Trivy 0.76.2 del 22/11/2026 sobre Debian 13.8 encontró 12 CVE de severidad alta
sin versión corregida disponible en Debian y ninguna crítica: CVE-2025-69720,
CVE-2026-119373, CVE-2026-119374, CVE-2026-119379, CVE-2026-124709, CVE-2026-16742,
CVE-2026-54369, CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 y
CVE-2026-9538. Afectan paquetes del sistema base (ncurses, SQLite, OpenSSL, systemd,
acl, util-linux y Perl), no dependencias Python de la aplicación. La imagen ejecuta como
UID 10001 y, en orchestration, Compose aplica `read_only`, `cap_drop: [ALL]` y
`no-new-privileges:true`. La CI ignora solo hallazgos sin corrección publicada; cuando
Trivy detecte una versión corregida, el hallazgo vuelve a bloquearla.
