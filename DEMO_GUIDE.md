# OTProof Demo Guide

The demo uses the fictional **Cedar Valley Water Utility** inventory and public CISA advisory data. The plant, assets, owners, work items, and evidence are synthetic. No OT device is contacted or changed.

## Explain OTProof in 30 seconds

“OTProof compares the equipment list a utility already has with public security notices. It shows the product and version details behind a possible match, asks an engineer to check when information is missing, and keeps the human decision and evidence together. It does not connect to or change equipment.”

For example, a real CISA notice names FactoryTalk View Site Edition version 13.0. The fictional asset `CV-HMI-001` is version `13.0.0`, so OTProof shows a possible match and links the notice. `CV-HMI-002` is version `14.0`, outside the version stated in that notice. `CV-HMI-005` has no recorded version, so it needs an engineer to check. A possible match is not yet a human decision or proof of remediation.

## Start the demo

### Local Python + Vite

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend python -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Browse to `http://localhost:5173`. API docs: `http://localhost:8000/docs`. On a new local database, the API seeds 80 inventory assets and three offline advisories. Repeated startup does not clear existing records.

### Docker Compose

Copy `.env.example` to `.env`, set a local-only password, then run `docker compose up --build`. The API is on `http://localhost:8000`, the dashboard on `http://localhost:5173`. Do not use the default Compose password outside a local demonstration.

## Judge workflow

1. **Overview:** show asset count, advisory count, findings by applicability, unresolved work, and evidence completeness.
2. **Sources:** review the three imported CISA advisories and their publication/update dates. Choose **Sync CISA ICS** or **Sync KEV** only when public internet access is available. The fixed sources are sufficient offline.
3. **Inventory:** inspect the uploaded synthetic inventory or use the included one. CSV and XLSX import validates fields, duplicate IDs, upload size, and workbook type.
4. **Findings:** run analysis. Inspect `CV-HMI-001` against ICSA-24-226-06: product and version 13.0 are an exact published match. `CV-HMI-002` is version 14.0 and is excluded by the exact version statement. `CV-HMI-005` has no firmware and must remain unresolved for engineering review.
5. **Human review:** open an applicable candidate, record an engineering applicability decision with rationale, and propose a ticket with owner and planned mitigation.
6. **Approval:** switch the role selector to **Approver**, inspect and approve/reject the proposed ticket with rationale.
7. **Evidence:** switch to **Engineer** or **Reviewer**, attach the clearly labeled simulated change record. The evidence SHA-256 is recorded; an evidence attachment alone does not complete remediation.
8. **Verification:** switch back to **Approver** and verify against the selected evidence with a rationale. This is the only route to `verified_remediated`.
9. **Export:** use the report control to download JSON or PDF. The report includes source links, applicability rationale, evidence metadata/hashes, workflow decisions, and audit events.

## Deliberate test cases

| Asset | Expected result | Why |
|---|---|---|
| CV-HMI-001 | Applicable | FactoryTalk View SE 13.0.0 normalizes to 13.0 and matches the CISA statement. |
| CV-HMI-002 | Not applicable | Same product, version 14.0 outside the exact affected version. |
| CV-HMI-003 | Applicable | Curated `Rockwel Automation` alias, matching product alias, and version 13.0. |
| CV-HMI-004 | Not applicable | FactoryTalk View Machine Edition is a distinct product from Site Edition. |
| CV-HMI-005 | Manual verification | Firmware is missing. |
| CV-HMI-006 | Manual verification | Model is explicitly unknown. |
| CV-HMI-007 | Manual verification | Inventory verification date is more than 180 days old. |
| CV-HMI-008 / 009 | Manual verification | Duplicate inventory fingerprints require a person to confirm physical identity. |
| CV-OPT-010 / 011 | Applicable / not applicable | Pavilion8 version 5.19 is prior to 5.20; 5.20 is not. |
| CV-APP-012 / 013 | Applicable / not applicable | DataMosaix 7.07 and prior; 7.08 is outside the published bound. |
| CV-OPT-014 | Manual verification | Suffix-bearing version syntax is not coerced to a numeric version. |

## Optional source and AI paths

- Source ingestion is on-demand and cached. On failure, a prior saved payload is used and reported as stale; the demo remains usable from fixtures with no external connectivity.
- Optional extraction requires a separately installed and running Ollama-compatible service at `OTPROOF_OLLAMA_URL` and the configured local model. The default demo works without a model. AI text is suggestion-only and must be checked against the advisory.
- Public CISA fixture provenance and dates: [data/fixtures/SOURCES.md](data/fixtures/SOURCES.md).

## Demo API roles

| Role | Demo bearer token | Allowed actions |
|---|---|---|
| Engineer | `demo-engineer-token` | Propose remediation, attach evidence |
| Reviewer | `demo-reviewer-token` | Run analysis, decide applicability, propose work, attach evidence, trigger source imports |
| Approver | `demo-approver-token` | Approve/reject tickets and verify remediation evidence |
| Admin | `demo-admin-token` | Administrative review role |

Example:

```bash
curl -H 'Authorization: Bearer demo-reviewer-token' http://localhost:8000/api/findings
```

Demo tokens are intentionally exposed by `/api/meta` when demo mode is on; they are not an authentication design for a real operator. In non-demo mode the UI accepts an API token configured by the operator. Replace static tokens with a managed identity provider and secrets process before deployment.

## Reset synthetic data

The seed command is deliberately non-destructive and returns existing record counts if any inventory/advisories already exist. To start over, stop the service and delete local `otproof.db`, then restart the API. Do not reset a database containing records you need.

## Known constraints for a live presentation

- Docker Compose was not run in the build environment because Docker Desktop/daemon was unavailable; use the local Python/Vite path if needed.
- Internet source synchronization depends on CISA/NVD availability and may return throttling or stale cache messages. Offline fixture workflow is deterministic.
- No local LLM run is required to complete the judge flow.
- Evaluation cases are synthetic and small; they do not show field precision, labor savings, security certification, or operational risk reduction.

For plain-language definitions and a step-by-step example, see [OTProof_Technical_Design.md](OTProof_Technical_Design.md#quick-glossary). Coding assistants can use [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md) for repository context, safety boundaries, and an example output.
