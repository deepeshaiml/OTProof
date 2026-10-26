# OTProof Progress

Updated: 2026-10-26

## Completed

1. **Workspace and guardrails:** inspected an empty workspace; established `AGENTS.md`, `PLAN.md`, this log, and safety scope. OT interaction remains passive/read-only/offline.
2. **Research and technology:** checked final NIST SP 800-82 Rev. 3 status, CISA ICS/KEV, NVD API 2.0, competitor positioning, direct dependency versions/licenses, and compatibility. NIST Rev. 4 is identified as an initial public draft, not final.
3. **Fixtures:** generated 80 fictional water utility assets with a fixed random seed; included three public CISA advisory snapshots with source URLs, publication/update dates, and 14 labeled applicability cases.
4. **Backend:** implemented inventory CSV/XLSX validation, public-source cache/ingestion, advisory normalization, deterministic match/abstain, optional local LLM adapter, SQLAlchemy/Alembic persistence, role-gated review/ticket/evidence lifecycle, audit events, and JSON/PDF assurance exports.
5. **Frontend and packaging:** implemented React/TypeScript dashboard, source controls, inventory upload, finding/review workflow, role selector/token entry, reports, Dockerfiles, and Compose definition.
6. **Evaluation:** 14/14 synthetic labels matched expected results (4 applicable, 4 not applicable, 6 manual verification); applicable precision/recall 100% and labeled false-negative rate 0% on four positives; abstention 6/6; traceability 14/14. One matcher-only 240-pair pass measured 1.008 ms on this development machine. LLM extraction and human review time were not measured.
7. **Submission files:** generated an eight-page DOCX/PDF idea document, 14-slide PPTX/PDF pitch deck with 70+ words of speaker notes on every slide, business case PDF, evaluation report PDF, and architecture SVG. Rendered the actual DOCX/PPTX with LibreOffice, verified page counts, and visually inspected every PDF page and the SVG.
8. **API smoke:** ran the local FastAPI service. Health/meta/dashboard succeeded; analysis covered 80 assets and 3 advisories (13 findings: 4 applicable, 6 manual review, 3 not applicable, with 227 clear cross-product nonmatches skipped); JSON and PDF assurance exports returned successfully. Full reviewer/engineer/approver/evidence-verification sequence is covered by an API integration test.
9. **Final report hardening:** escaped inventory, advisory, source URL, and audit content in generated PDF markup; exercised a query-string source URL and markup-like source label; refreshed and visually inspected the 4-page sample assurance PDF.

## Verification results

- `pytest`: 14 passed; one upstream Starlette warning notes that the current TestClient/HTTPX integration is deprecated.
- Ruff: passed.
- Frontend TypeScript/Vite production build: passed.
- `npm audit`: 0 vulnerabilities reported.
- Alembic migration upgrade: succeeded against local SQLite.
- `docker compose config --quiet`: passed; container build/startup remains unverified because the Docker daemon was unavailable.
- CISA ICS/CSAF, CISA KEV JSON, and NVD CVE 2.0 imports: exercised against public endpoints on 2026-10-26; fixed offline fixtures remain available.
- PDF exports: 8-page idea, 14-page deck, 3-page business case, and 3-page evaluation report; actual Office exports were rendered and inspected.

## Remaining constraints

- Docker CLI is available but the Docker daemon was not running; Compose startup/container builds were not verified.
- Ollama and model weights were not installed or run; AI extraction accuracy is not measured.
- Dataset is small, synthetic, and Rockwell-focused. Results are not field accuracy, a customer study, a penetration test, a safety case, or proof of cost/risk reduction.
- Production identity integration, immutable audit storage, binary evidence attachments, broader source/vendor coverage, security review, and operator pilot remain future work.
