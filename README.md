# OTProof

**Evidence-first vulnerability applicability and remediation assurance for industrial asset inventories.**

OTProof is an offline-capable, read-only MVP for reconciling an operator-provided asset list with public industrial security advisories. It produces deterministic, source-linked candidate findings and routes uncertain cases to engineering review. It does not scan OT networks, exploit systems, change device configurations, or decide remediation completion automatically.

## MVP status

- 80 fictional Cedar Valley Water Utility assets and three real, source-linked CISA ICS advisories are included as reproducible fixtures.
- CSV/XLSX inventory validation, CISA ICS / CISA KEV / NVD 2.0 / approved vendor-source ingestion, deterministic matching, role-gated review and remediation workflow, audit trail, and JSON/PDF assurance exports are implemented.
- Optional local Ollama extraction is isolated from the deterministic matching and workflow state.
- The labeled fixture evaluation scored 14/14 expected classifications (4 applicable, 4 not applicable, 6 manual verification). This is a small synthetic correctness check, not a real-world accuracy estimate. LLM extraction was not run.
- `pytest`, Ruff, and the frontend production build pass. Docker Compose could not be started because no Docker daemon was available in the build environment.

## Quick start

Requirements: Python 3.12, Node 26/npm, and optionally Docker Compose.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Open [http://localhost:5173](http://localhost:5173). On first API startup, demo mode initializes the local SQLite database with fictional data. The role selector uses demo-only tokens that are deliberately visible to the browser. Never use demo tokens in a real deployment.

For PostgreSQL and a containerized UI/API, copy `.env.example` to `.env`, set a local-only `OTPROOF_DB_PASSWORD`, and run:

```bash
docker compose up --build
```

## Demo in a few minutes

1. Open the dashboard and review the demo assets and source-linked advisories.
2. Choose **Advisory sources** and load current official data, or keep the offline fixtures.
3. Choose **Findings** and run applicability analysis.
4. Inspect an exact match, a different-version result, and a manual-review case. Each finding retains its source URL and the inventory/advisory fields used by the matcher.
5. Record an engineering decision with a rationale, propose a remediation ticket, and switch to the approver role to approve it.
6. Attach the clearly simulated evidence record and complete verification with an approver rationale.
7. Download the PDF or JSON assurance report.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for roles, endpoints, and a scripted workflow.
An API-generated fictional assurance export is included at [reports/demo-assurance-smoke.pdf](reports/demo-assurance-smoke.pdf).

## Local checks

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts
PYTHONPATH=backend .venv/bin/python scripts/evaluate.py
cd frontend && npm run build
```

The evaluation writes `reports/evaluation_metrics.json`. The script times the in-process matcher over all 80 × 3 asset/advisory pairs; it does not measure human review time or whole-service performance.

## Design and safety

- Applicability uses deterministic vendor/product normalization and explicit numeric version constraints. Unrecognized versions, missing data, stale inventory, duplicates, unknown models, and unsupported compound NVD configurations abstain for a human review.
- AI is optional, local, schema-constrained, and checked against source text. It can draft extraction and summaries only. It cannot set applicability decisions, approve tickets, or mark findings remediated.
- Engineering decisions, ticket approval, evidence attachment, and remediation verification are role-gated and audited.
- CISA / NVD ingestion is cached, retries transient rate limits, preserves source timestamps, and uses stale data when refresh is unavailable.
- All fixture assets and demo evidence are fictional. The application has no OT connectivity.

## Repository map

- `backend/app/` — API, data models, source ingestion, matching, AI adapter, reporting
- `backend/migrations/` — Alembic schema migration
- `backend/tests/` — matching, ingestion/input safety, prompt-injection, workflow/RBAC tests
- `frontend/` — React / TypeScript dashboard
- `data/fixtures/` — fictional 80-asset inventory, public advisory snapshots, labeled cases, provenance
- `scripts/` — reproducible data generator and evaluator
- `docs/` — technical design, technology decisions, and research notes
- `OTProof_*` — submission documents and pitch assets

Read [OTProof_Technical_Design.md](OTProof_Technical_Design.md), [PLAN.md](PLAN.md), and [PROGRESS.md](PROGRESS.md) before extending the MVP.
