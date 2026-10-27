# OTProof Technical Design

**Version:** MVP 0.1 · **Research checked:** 2026-10-26  
**Purpose:** passive OT inventory-to-advisory applicability and remediation assurance.  
**Operating boundary:** no OT network connection, active scan, exploitation, or equipment modification.

## 1. Product scope

OTProof joins an operator-maintained inventory with public vulnerability advisory records. It answers a narrower question than an OT discovery or vulnerability scanner: “Does this advisory's published vendor, product, model/configuration, and version evidence match this inventory record, and what evidence supports that conclusion?”

The output is a triage result, not proof of exploitability, operational safety, or remediation. A match becomes a human-reviewed decision only after an authorized reviewer records a rationale. A proposed fix becomes verified remediation only after an authorized approver records a verification decision linked to evidence.

### Plain-language walkthrough

1. An operator uploads an equipment spreadsheet and imports a public security notice.
2. OTProof compares the maker, product, and software version listed for each asset with the affected product and version in the notice.
3. It shows its work: which values matched, which source line it used, and why it chose a result.
4. A person reviews the result. If work is needed, an engineer proposes it, an approver reviews it, and later an approver checks the evidence.

**Example:** the CISA notice for FactoryTalk View Site Edition names version 13.0. The fictional asset `CV-HMI-001` is recorded as version `13.0.0`. OTProof normalizes a known product-name variation and treats the trailing zero as equivalent, so it labels the pair `applicable` while leaving the workflow status `requires_review`. A reviewer still needs to confirm it. Asset `CV-HMI-002` is version `14.0`, outside this notice's exact version statement, so it is `not_applicable` for this advisory. Asset `CV-HMI-005` has no version, so it is `requires_manual_verification`. See [the CISA source record](data/fixtures/SOURCES.md).

### Quick glossary

| Term | Plain meaning in OTProof |
|---|---|
| Asset | A device or software record in the operator's inventory. |
| Advisory | A public security notice that identifies a product weakness and affected versions. |
| CISA | The U.S. Cybersecurity and Infrastructure Security Agency, which publishes the industrial security notices used here. |
| CVE | A public identifier for one reported vulnerability. |
| KEV | CISA's list of vulnerabilities known to have been exploited. Membership informs priority; it does not prove a specific asset is affected. |
| Candidate finding | A possible link between one asset and one advisory. The finding still needs human review. |
| Applicable | The recorded vendor, product, and version fit the supported published conditions. This is still a screening result. |
| Not applicable | The available records rule out this asset for this advisory candidate. It does not mean the asset is free of every vulnerability. |
| Manual verification | The available information is missing, old, ambiguous, or outside supported rules, so the system deliberately does not guess. |
| Evidence | A record, reference, or test result used by a person to support a decision. |

### Technical abbreviations

| Term | Plain meaning |
|---|---|
| API | A defined way for one software program to request information or an action from another. |
| ICS | Industrial control systems: computers and controllers used to monitor or operate industrial processes. |
| NVD | The National Vulnerability Database, maintained by NIST, which publishes machine-readable vulnerability records. |
| CPE | A standardized way to name a computer product in vulnerability databases. |
| CSAF | Common Security Advisory Framework, a structured format for sharing security advisories. |
| LLM | Large language model; the kind of generative AI that can summarize or extract text. |
| RBAC | Role-based access control: permissions depend on whether the user is an engineer, reviewer, or approver. |
| SSO | Single sign-on: using an organization's existing login to access the service. |
| WORM | Write once, read many storage: a system designed to prevent stored records from being changed after they are written. |
| ETag / Last-Modified | Web-server labels that tell a client whether a downloaded source has changed. |
| TTL | Time to live: how long OTProof waits before refreshing a saved source copy. |

In implementation sections, **deterministic** means the same inputs follow the same explicit rules and produce the same output. **Abstain** means the system refuses to guess and sends the case for human review.

For coding assistants, see [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md), which includes a safe example output and repository map.

NIST SP 800-82 Rev. 3 is the published final OT security guide used as design context. NIST's publication list reports Rev. 4 as an initial public draft dated 2026-09-21; this MVP does not present that draft as final. Rev. 3 highlights accurate vendor, model, firmware/software, location, criticality, and accountable-role inventory data as important for OT risk management. [NIST SP 800-82 Rev. 3](https://csrc.nist.gov/pubs/sp/800/82/r3/final) · [NIST OT publication index](https://csrc.nist.gov/Projects/operational-technology-security/publications)

## 2. System architecture

The MVP is a modular monolith with a React client and one FastAPI service. PostgreSQL is the Compose deployment target; SQLite supports zero-configuration local use. The API has no route or dependency that reaches into an OT network.

```text
CSV / XLSX             CISA ICS RSS + CISA-linked CSAF
operator inventory     CISA KEV JSON · NVD CVE API 2.0 · vendor HTTPS bulletins
      │                                │
      └──────────────┬─────────────────┘
                     ▼
      FastAPI validation + source cache / normalization
                     │
          SQLAlchemy · PostgreSQL / SQLite
                     │
      deterministic applicability matcher
       exact identity · version bounds · abstention
                     │
      finding review → ticket approval → evidence → verification
                     │
      React dashboard · audit events · JSON/PDF assurance export

Optional local Ollama adapter: source-text extraction and draft summary only.
```

`OTProof_Architecture.svg` is the standalone vector architecture figure. API routes, persistence models, source adapters, matcher, and reporting service are separated within `backend/app/` to keep a future extraction straightforward without adding unnecessary services now.

## 3. Asset inventory

Fields: asset identifier, vendor, product, model, firmware/software version, equipment type, site, business criticality, review owner, and last inventory verification date.

CSV and XLSX are parsed with pandas/openpyxl. The importer maps documented column aliases, rejects duplicate asset IDs, enforces upload size and row limits, and rejects macro-enabled `.xlsm` workbooks. It does not run spreadsheet formulas or macros. Asset imports preserve the submitted values; aliases are used at comparison time rather than rewriting the source inventory.

The reproducible `Cedar Valley Water Utility` dataset has 80 fictional assets. It intentionally contains inconsistent vendor spelling, missing firmware, unknown model, duplicate identity, stale inventory timestamps, a similar but distinct product, and exact affected/unaffected version cases. Run `scripts/generate_demo_data.py` to regenerate it with fixed seed `20261026`.

## 4. Sources and controlled ingestion

Configured inputs are:

1. [CISA ICS advisory RSS](https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml), with CISA advisory pages and an explicit validated “View CSAF” link to the official [CISA CSAF repository](https://github.com/cisagov/CSAF).
2. [CISA KEV JSON catalog](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json).
3. [NVD CVE API 2.0](https://nvd.nist.gov/developers/vulnerabilities), queried by CVE identifier.
4. Public vendor bulletins restricted to HTTPS pages on approved Rockwell, Schneider Electric, Siemens, and Cisco domains.

Source payloads are cached in `source_snapshots` with source URL, fetched timestamp, ETag, Last-Modified, hash, status, and payload. A configurable TTL avoids unnecessary downloads. HTTP 429/503 responses honor numeric Retry-After values or use bounded retry delays. If all refresh attempts fail, a prior payload is returned as a stale fallback and its state is surfaced. Imports record source publication/current-release dates where provided. NVD and CISA schemas change over time; unrecognized fields must remain visible for review rather than silently being interpreted.

CSAF `known_affected` products and version range strings are normalized. NVD start/end version bounds are combined conjunctively for one CPE match. Compound, nested, negated, or otherwise unsupported NVD configuration logic is preserved in source text and sent to manual review. Simple alternatives remain separate candidate products. The MVP does not resolve every CPE configuration expression, hardware subcomponent, platform dependency, or vendor-specific suffix.

Offline fixtures retain three genuinely public CISA advisories and fixed publication/update dates. Sources and provenance are described in `data/fixtures/SOURCES.md`.

## 5. Applicability engine

The engine returns `applicable`, `not_applicable`, or `requires_manual_verification` with a status, reasons, source identifiers, a source URL, and the actual inventory/advisory values used.

### Deterministic steps

1. Normalize punctuation/case and apply a small curated alias map (for example, `Rockwel Automation` → `Rockwell Automation`, and `FactoryTalk View SE` → `FactoryTalk View Site Edition`). Aliases are inspectable in `backend/app/services/matching.py`.
2. If vendor or product is explicitly different, return not applicable for that advisory candidate.
3. Require a known product match; similar product names remain ambiguous or distinct, never a semantic similarity verdict.
4. Route duplicate possible assets, `Unknown` model, stale (>180-day) inventory, missing firmware, unsupported version syntax, absent bounds, and unsupported compound NVD configurations to manual verification.
5. Parse conservative numeric dotted versions and compare explicit `eq`, `lt`, `lte`, `gt`, and `gte` constraints. Suffix-bearing identifiers such as `release-5.19-hotfix` abstain instead of being coerced.
6. Evaluate every constraint within one candidate as AND; separate affected-product candidates are alternatives. The relevant source statement appears in the rationale/evidence.

No embeddings or sentence-level semantic similarity scores participate in the verdict. The matching engine is purposely conservative; a `not_applicable` result means the available published and inventory constraints exclude the asset for this candidate, not that all product configurations or other advisories are safe.

## 6. Optional AI extraction

`backend/app/services/llm.py` uses an Ollama-compatible local `/api/chat` endpoint and JSON schema output. The prompt describes advisory text and titles as untrusted input, explicitly disallows following embedded commands, and disallows applicability or remediation decisions. The response must validate as a Pydantic schema. Extracted CVEs, product/version/mitigation strings, and source quotations must appear in the advisory text after whitespace normalization. Unsupported values are rejected.

This check is a minimum guard against unsupported extraction; it is not a proof that an LLM summary is complete or correct. AI output is advisory text for a human. It does not feed the matcher, decision fields, approval workflow, or verified-remediation state. `qwen2.5:7b-instruct` is the default model name but no model is included, installed, or evaluated in the MVP. The evaluation report marks extraction accuracy as not measured.

## 7. Remediation assurance and state control

Roles are `engineer`, `reviewer`, `approver`, and `admin`, mapped from bearer tokens. Demo tokens are public and only appropriate for a local fictional demonstration. Non-demo deployments must supply controlled role tokens through `OTPROOF_ROLE_TOKENS` or integrate an enterprise identity provider before real use.

```text
candidate finding
    ├─ reviewer records applicable / not applicable + rationale
    └─ engineer proposes action, owner, due date, and planned mitigation
             ↓
        approver approves or rejects the ticket
             ↓
        engineer attaches a typed evidence record (reference + content hash)
             ↓
        approver verifies against a selected evidence record + rationale
             ↓
        verified_remediated (explicit human verification only)
```

Each user action creates an audit event with actor, role, time, entity, action, and details. Evidence is hashed when recorded. The assurance JSON/PDF includes advisory publication/update/import dates and a source-snapshot register with fetched time, status, ETag/Last-Modified values, source URL, and payload hash; raw cached payloads are not copied into the report. The MVP application has no audit update/delete endpoint, but a database owner can still alter records; this is not immutable storage, a digital-signature service, or WORM retention. Evidence attachments are text/metadata records rather than binary uploads. Demo evidence is labeled simulated.

## 8. API surface

- `GET /api/health`, `/api/meta`, `/api/dashboard`
- `GET /api/assets`, `POST /api/assets/import`
- `GET /api/advisories`; source-specific `POST /api/ingest/cisa-ics`, `/cisa-kev`, `/nvd/{cve}`, and `/vendor`
- `POST /api/analyze`, `GET /api/findings`, reviewer `POST /api/findings/{id}/decision`
- `POST /api/findings/{id}/tickets`, `GET /api/tickets`, approver ticket decision
- `POST /api/findings/{id}/evidence`, approver evidence verification
- `POST /api/advisories/{id}/ai-extract`, `GET /api/audit`
- `GET /api/report/assurance.json`, `GET /api/report/assurance.pdf`

The API schema is available at `/docs` when the service is running locally. Write operations check role dependencies; read routes support the local demo dashboard.

## 9. Security and deployment considerations

- **Network boundary:** official public feeds are outbound source connections. There is no OT-facing interface. Deploy the service in an IT/DMZ zone with an explicit egress allowlist if used beyond local demo.
- **Untrusted inputs:** inventory data and advisory text are treated as content; no macros, shell, scripts, or prompts are executed. CSV/XLSX size/row constraints and vendor URL allowlists reduce parsing/SSRF exposure.
- **Authentication:** demo tokens are insecure by design. Production needs SSO/OIDC or managed secrets, rotation, least-privilege roles, session/token monitoring, and stronger rate limiting.
- **Secrets:** do not commit `.env`; configure database credentials and role tokens in a secret manager. Demo Compose password is for local-only use.
- **Database:** apply Alembic migrations in deployment, run PostgreSQL with backups, TLS and least privilege. The API currently creates schema on startup for the local demo.
- **Audit/evidence:** hash recorded text evidence and protect the database using external backup, access controls, retention, and optionally immutable audit export. Hashing proves byte consistency only if a trusted original is retained.
- **Operations:** monitor source age, parser errors, rejected records, stale cache indicators, and disk growth. Review vendor domain allowlists and source schemas.
- **Validation limits:** passing unit tests is not a penetration test, safety case, certification, or production assurance. Threat modeling, dependency SBOM/license review, security review, backup-restore tests, and independent OT engineering trials remain.

## 10. Evaluation snapshot

The fixed 14-case synthetic label set produced 100% precision and recall for applicable labels, 0 false negatives, 6/6 expected manual-review abstentions, and 14/14 source-traceable output records. In plain terms, all 14 prepared examples got their expected result, including all four affected examples and all six cases that should go to review. This is an in-sample fixture result with only four affected examples, not field accuracy. One in-process 240-pair benchmark measured approximately 1.01 ms total on this development environment; it includes matcher function execution only. Human review time and end-to-end latency were not measured. The local LLM was not run. See [OTProof_Evaluation_Report.pdf](OTProof_Evaluation_Report.pdf) and `reports/evaluation_metrics.json`.

## 11. Primary references

- [NIST SP 800-82 Rev. 3 final](https://csrc.nist.gov/pubs/sp/800/82/r3/final)
- [CISA ICS advisories](https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml)
- [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- [NVD CVE API](https://nvd.nist.gov/developers/vulnerabilities)
- [CISA advisory fixture provenance](data/fixtures/SOURCES.md)
- [Technology decisions and dependency licenses](docs/TECHNOLOGY_DECISIONS.md)
