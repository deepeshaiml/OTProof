# OTProof

**Check which public security notices may affect industrial equipment, then keep the human review and evidence together.**

OTProof is an offline-capable, read-only MVP for comparing an operator-provided equipment list with public industrial security notices. It shows possible matches, links the source, and sends uncertain cases to engineering review. It does not scan equipment, exploit systems, change device settings, or decide that a repair is complete.

### In plain language

Think of OTProof as a careful bridge between two records: the operator's equipment list and a public security notice. It compares the product and installed software version, shows the notice it used, and asks a person to check when information is missing or unclear. The application never connects to industrial equipment.

**Example:** a real CISA notice names FactoryTalk View Site Edition version 13.0 as affected. In the fictional Cedar Valley inventory, CV-HMI-001 is version 13.0.0, so OTProof shows a possible match and links the notice. CV-HMI-002 is version 14.0, outside the exact version stated in that notice. CV-HMI-005 has no recorded software version, so OTProof asks an engineer to review it. These results do not mean equipment was changed or fixed.

**Who does what:** OTProof compares records and explains the result. A reviewer decides whether the notice fits. An engineer proposes work. An approver reviews the plan and later checks the evidence. Optional AI may help read a notice, but people own decisions.

**Quick terms:** OT (operational technology) means computers and controllers used to monitor or control physical processes, such as water pumps. An advisory is a public security notice. A CVE is a public ID for one vulnerability. CISA is the U.S. Cybersecurity and Infrastructure Security Agency. KEV is its list of vulnerabilities known to have been exploited. A candidate match is a possible link to review, not a final engineering decision.

For a machine-readable working guide for coding assistants and other AI agents, see [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md).

## MVP status

- 80 fictional Cedar Valley Water Utility assets and three real, source-linked CISA security notices are included as repeatable examples.
- Spreadsheet checks, public CISA/NIST/vendor notice import, explicit product/version comparison, human review and approval, action history, and JSON/PDF exports are implemented.
- An optional local AI helper can suggest fields from a notice. It does not affect the comparison or approvals.
- All 14 prepared examples returned the expected outcome: 4 possible affected matches, 4 outside the notice conditions, and 6 sent for human review. This small synthetic check is not a real-world accuracy estimate. The AI model was not run.
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

Open [http://localhost:5173](http://localhost:5173). On first API startup, demo mode initializes the local SQLite database with fictional data. The role selector uses demo-only tokens that are deliberately visible to the browser. Never use demo tokens in a real deployment. For role definitions and the human approval sequence, see the [Demo Guide](DEMO_GUIDE.md).

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

- Product and version checks follow explicit rules. Missing or old data, duplicates, unknown models, and unsupported source details go to human review.
- AI is optional and can draft fields or summaries only. Its suggestions are checked against source text and cannot decide whether equipment is affected, approve work, or mark work complete.
- Engineering decisions, ticket approval, evidence attachment, and remediation verification are role-gated and audited.
- CISA / NVD ingestion is cached, retries transient rate limits, preserves source timestamps, and uses stale data when refresh is unavailable.
- All fixture assets and demo evidence are fictional. The application has no OT connectivity.

## Repository map

- `backend/app/` — API, data models, source ingestion, matching, AI adapter, reporting
- `backend/migrations/` — Alembic schema migration
- `backend/tests/` — matching, input safety, source behavior, permissions, and human workflow tests
- `frontend/` — React / TypeScript dashboard
- `data/fixtures/` — fictional 80-asset inventory, public advisory snapshots, labeled cases, provenance
- `scripts/` — reproducible data generator and evaluator
- `docs/` — technical design, technology decisions, and research notes
- `OTProof_*` — submission documents and pitch assets

For deeper technical details, read [OTProof_Technical_Design.md](OTProof_Technical_Design.md). For AI coding assistants, use [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md). See [PLAN.md](PLAN.md) and [PROGRESS.md](PROGRESS.md) for project status.
