# Technology Decisions

Checked 2026-10-26. Direct dependency versions were installed in the project virtual environment and frontend lockfile and exercised with the current Python 3.12.13 / Node 26.9.0 toolchain. License values are package metadata or project license files; a production release still needs a generated SBOM and review of all transitive packages and model distribution terms.

## In everyday terms

The dashboard is the screen people use. The API is the service that checks requests and applies the rules. The database keeps the equipment, notices, decisions, and evidence records. The source adapters retrieve and cache public notices. The optional AI helper can suggest fields from a notice but does not make a match decision. The PDF and JSON exports package the record for review. The technology names in the tables below identify the open-source tools used to build each part.

## Architecture choices

| Area | Selection | Reason and boundary |
|---|---|---|
| API and domain | Python 3.12, FastAPI, Pydantic 2 | Typed request validation and OpenAPI. The backend is a modular monolith. |
| Persistence | SQLAlchemy 2.0, Alembic; PostgreSQL 16 in Compose; SQLite for quick local demo | Relational workflow and portable local setup. SQLAlchemy 2.1 was available, but the supported 2.0 line is pinned for conservative compatibility. |
| Web UI | React 19, TypeScript 7, Vite 8 | Common component stack and static production build. |
| Inventory files | pandas 3 + openpyxl 3 | CSV/XLSX parsing. Macro-enabled workbooks are rejected, formulas are not evaluated, and upload size/row limits apply. |
| Applicability | Curated aliases plus explicit numeric version bounds | Exact explainable matching. Unsupported version syntax and complex NVD configuration logic abstain. No embeddings or semantic similarity verdicts. |
| Optional AI | Local Ollama-compatible HTTP adapter, default model label `qwen2.5:7b-instruct` | Structured extraction/summaries only. Schema and source-string checks run after generation; output never controls applicability or state. Model installation/inference was not part of this evaluation. |
| Reports | ReportLab, python-docx, python-pptx | Open formats and reproducible PDF/DOCX/PPTX generation. |
| Quality | pytest 9, Ruff 0.17, TypeScript compiler/Vite production build | Unit/API checks, static lint, and frontend compile/bundle. |
| Packaging | Docker Compose | PostgreSQL + API + UI for demo. The source environment had no active Docker daemon, so container startup was not verified. |

## Direct runtime and generation packages

| Package | Pinned version | Observed license | Role |
|---|---:|---|---|
| FastAPI | 0.162.0 | MIT | API framework |
| Uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| Pydantic | 2.14.1 | MIT | Data validation |
| pydantic-settings | 2.16.1 | MIT | Environment configuration |
| SQLAlchemy | 2.0.55 | MIT | ORM and database layer |
| Alembic | 1.20.1 | MIT | Schema migration |
| Psycopg 3 | 3.3.6 | LGPL-3.0-only | PostgreSQL driver (binary extra pinned) |
| PostgreSQL | 16 (Alpine image in Compose) | PostgreSQL License | Relational database |
| pandas | 3.1.0 | BSD-3-Clause | Inventory table parsing |
| openpyxl | 3.1.5 | MIT | XLSX reader |
| HTTPX | 0.28.1 | BSD-3-Clause | Source retrieval and API tests |
| python-multipart | 0.0.32 | Apache-2.0 | Multipart inventory uploads |
| pytest | 9.1.1 | MIT | Tests |
| Ruff | 0.17.2 | MIT | Lint/format tooling |
| ReportLab | 5.1.0 | BSD-style | PDF reports and submission PDFs |
| python-docx | 1.2.0 | MIT | Idea document generation |
| python-pptx | 1.0.2 | MIT | Pitch deck generation |
| React / React DOM | 19.3.1 | MIT | Browser UI |
| Vite | 8.3.5 | MIT | Frontend build server |
| TypeScript | 7.0.2 | Apache-2.0 | Static type checking |
| lucide-react | 1.61.0 | ISC | UI icons |
| Prettier | 3.9.10 | MIT | Frontend formatting |

The optional `Qwen2.5-7B-Instruct` model repository declares Apache-2.0. The Ollama runtime project declares MIT. Users must review model files and applicable licenses in the actual serving/distribution package before commercial deployment; the model is not bundled with this repository.

## Compatibility and maintenance check

The direct pinned Python dependencies installed successfully together on Python 3.12.13. The direct frontend packages installed from the lockfile and passed the production TypeScript/Vite build on Node 26.9.0. This verified the selected versions against each other rather than relying on package version claims alone. Python metadata and npm registry metadata were queried on 2026-10-26. The projects publish versioned releases, documentation, or changelogs at the linked upstream locations below; license and release status should be rechecked at each product release.

| Project | Maintenance / compatibility evidence checked |
|---|---|
| FastAPI + Pydantic | Upstream release notes and typed-schema docs; installed FastAPI 0.162.0 / Pydantic 2.14.1. [FastAPI releases](https://github.com/fastapi/fastapi/releases) · [Pydantic changelog](https://pydantic.dev/docs/validation/latest/get-started/changelog/) |
| SQLAlchemy + Alembic | Supported SQLAlchemy 2.0 line installed with Alembic 1.20.1; SQLite migration and test database worked. [SQLAlchemy changelog](https://docs.sqlalchemy.org/en/20/changelog/) · [Alembic changelog](https://alembic.sqlalchemy.org/en/latest/changelog.html) |
| pandas + openpyxl | CSV/XLSX import worked with pandas 3.1.0 and openpyxl 3.1.5. [pandas what's new](https://pandas.pydata.org/docs/whatsnew/index.html) · [openpyxl documentation](https://openpyxl.readthedocs.io/en/stable/) |
| React + Vite + TypeScript | React 19.3.1, Vite 8.3.5, and TypeScript 7.0.2 compiled and bundled the dashboard. [React releases](https://github.com/facebook/react/releases) · [Vite releases](https://github.com/vitejs/vite/releases) · [TypeScript releases](https://github.com/microsoft/TypeScript/releases) |
| Ollama / Qwen2.5 | Optional only; adapter contract is implemented, but no serving runtime/model inference was installed or evaluated. [Ollama releases](https://github.com/ollama/ollama/releases) · [Qwen2.5-7B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) |

The project avoids Sentence Transformers because semantic similarity is not a suitable applicability authority for similar industrial product names. A supported local model adapter is kept optional until a labeled extraction benchmark justifies its operational and licensing cost.

## Source and deployment boundaries

- CISA ICS RSS and advisory pages, CISA KEV JSON, documented NVD CVE API 2.0, CISA-linked CSAF, and approved vendor HTTPS pages are the only configured public source routes.
- HTTP cache validators, a configurable TTL, retry/backoff for 429/503, and stale-copy fallback support controlled refresh and offline use.
- The MVP has no OT interface, device protocol client, network scanner, exploit module, or control action.
- Demo bearer tokens are intentionally public and only suitable for the fictional local demo. Configure role token mappings or an organization IdP before any real use.
- Postgres auditing is append-only through the application API, but is not cryptographically immutable or WORM storage.

## Why no semantic matching dependency

Vendor and model terminology can be close while representing materially different equipment. The current use case can be handled with curated aliases, exact normalized product identity, conservative numeric version comparison, and a manual-review outcome. Sentence Transformers would add model hosting, version drift, and semantic false-positive risk without a demonstrated need. A future normalization model may propose aliases for human curation, but cannot issue a vulnerability verdict.

## Primary references

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy documentation](https://docs.sqlalchemy.org/)
- [React documentation](https://react.dev/)
- [Pandas documentation](https://pandas.pydata.org/docs/)
- [PostgreSQL license](https://www.postgresql.org/about/licence/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [NVD API 2.0 documentation](https://nvd.nist.gov/developers/vulnerabilities)
- [NIST SP 800-82 Rev. 3 final](https://csrc.nist.gov/pubs/sp/800/82/r3/final)

