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
├── api/v1/            presentación: rutas (endpoints/documents.py) y esquemas
├── infrastructure/    datos: conexión y repositorio de MongoDB
├── admin/             procesos de administración (create_indexes)
├── core/config/       Settings (variables de entorno)
└── main.py            arma la aplicación y el /health
tests/
├── unit/              contrato HTTP, health y proceso de índices
└── integration/       repositorio contra MongoDB real
```
