from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PPTColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as PptInches
from pptx.util import Pt as PptPt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
NAVY = "122430"
NAVY_2 = "1C3441"
TEAL = "25A99A"
MINT = "DDF3EF"
CORAL = "E08B62"
GOLD = "F1B85B"
PAPER = "F3F7F6"
INK = "18313A"
MUTED = "63777C"
WHITE = "FFFFFF"


IDEA_PAGES = [
    {
        "title": "OTProof",
        "deck": "AI-powered industrial vulnerability applicability and remediation assurance",
        "cover": True,
        "sections": [
            {
                "heading": "The idea",
                "body": "Turn public industrial security advisories and operator-maintained asset lists into a reviewable, evidence-backed workflow. Deterministic rules identify exact product and version candidates; people resolve uncertainty and verify remediation.",
            },
            {
                "heading": "A practical, safety-conscious MVP",
                "body": "A local dashboard, validated CSV/XLSX inventory import, official public-source ingestion, explainable applicability, engineer/reviewer/approver workflow, audit trail, and assurance report. No OT network interaction is required.",
            },
        ],
        "tiles": [("80", "fictional assets"), ("3", "real CISA advisories"), ("0", "OT device actions")],
        "callout": "Eureka Hackathon · Product concept and working MVP · 26 October 2026",
    },
    {
        "title": "The problem sits between the inventory and the advisory",
        "deck": "A published CVE is not enough to know which operational asset needs engineering attention.",
        "sections": [
            {
                "heading": "Three records that rarely line up cleanly",
                "body": "Operators track asset names, models, software/firmware, site, criticality, and owners across maintenance records and spreadsheets. Advisory publishers use product families, version ranges, configuration conditions, and vendor terminology. Security and engineering teams reconcile them under time pressure.",
            },
            {
                "heading": "False certainty has a cost",
                "body": "A superficial product-name match can create noise; a missing or stale version can hide a relevant case. OT teams must also assess process impact, approved change windows, vendor support, and operational safety before acting.",
            },
            {
                "heading": "Why now",
                "body": "NIST SP 800-82 Rev. 3 identifies accurate inventory details such as vendor, model, software/firmware version, location, and roles as useful to OT risk management. It also recognizes that active collection methods may affect OT and need careful consideration. OTProof begins with an operator-supplied inventory and stays out of the control network.",
                "source": "NIST SP 800-82 Rev. 3 final (2023-09-28): https://csrc.nist.gov/pubs/sp/800/82/r3/final",
            },
        ],
        "callout": "The product produces a source-backed triage candidate, not a safety, exploitability, or remediation verdict.",
    },
    {
        "title": "A single workflow from source to verified evidence",
        "deck": "Every finding preserves the records and decisions needed to explain what happened.",
        "sections": [
            {
                "heading": "1 · Load and validate inventory",
                "body": "Import a CSV or XLSX file with asset identity, vendor, product/model, version, type, site, criticality, owner, and last verification date. Reject duplicate identifiers, oversized uploads, and macro-enabled workbooks.",
            },
            {
                "heading": "2 · Import approved advisory data",
                "body": "Fetch CISA ICS RSS/advisory/CSAF, CISA KEV JSON, NVD CVE API 2.0, or a bulletin on an approved vendor HTTPS domain. Cache payloads and preserve source URLs and timestamps.",
            },
            {
                "heading": "3–6 · Compare, review, and assure",
                "body": "The deterministic matcher returns applicable, not applicable, or manual verification. An engineer records the applicability decision and rationale; an approver accepts or rejects a proposed ticket; evidence is attached and separately verified by an approver; JSON/PDF reports retain sources and audit history.",
            },
        ],
        "callout": "A ticket or generated narrative cannot mark a finding remediated. Only an approver verification tied to evidence can.",
    },
    {
        "title": "A modular, offline-capable architecture",
        "deck": "One maintainable service keeps source ingestion, comparison, workflow, and evidence close together.",
        "sections": [
            {
                "heading": "Built for the demo and a controlled pilot",
                "body": "React + TypeScript dashboard → FastAPI/Pydantic API → SQLAlchemy and PostgreSQL. SQLite supports a quick local run. Alembic manages schema changes. ReportLab exports assurance reports. Docker Compose packages the database, API, and frontend.",
            },
            {
                "heading": "Public sources only",
                "body": "The ingestion service uses documented CISA RSS/JSON, NVD CVE API 2.0, CISA-linked CSAF documents, and an allowlist of vendor bulletin domains. Conditional cache headers, a configurable TTL, bounded retries, and stale-copy fallback support outages.",
            },
            {
                "heading": "Explicit trust boundaries",
                "body": "There is no OT interface, protocol client, scanner, exploit capability, or control action. The optional local LLM adapter receives advisory text only and cannot write applicability decisions or workflow status.",
            },
        ],
        "callout": "Deployment for real operators requires managed identity, secret rotation, allowlisted egress, backup/restore, and independent security review.",
    },
    {
        "title": "Deterministic matching earns each conclusion",
        "deck": "Product identity and version evidence are more useful than an unexplained similarity score.",
        "sections": [
            {
                "heading": "Supported comparisons",
                "body": "A curated alias map normalizes a small set of known vendor/product variants. Exact normalized product identity is followed by conservative dotted-numeric version comparison against published equality or inclusive/exclusive bounds. Constraints in one NVD CPE match are conjunctive; alternatives remain separate candidate products.",
            },
            {
                "heading": "Abstain when evidence is incomplete",
                "body": "Missing firmware, unknown model, possible duplicate asset, inventory older than 180 days, unsupported suffix/version syntax, ambiguous product identity, and compound or negated NVD configurations require an engineering review. Semantic similarity never decides applicability.",
            },
            {
                "heading": "AI assists with reading, not deciding",
                "body": "An optional local Ollama-compatible model can draft structured product/version/CVE extraction, summaries, uncertainty explanations, and review suggestions. Pydantic validates the response and extracted identifiers/quotes are checked against the source text. The LLM is not used by the matcher or state machine.",
            },
        ],
        "callout": "Default model name: Qwen2.5 7B Instruct via Ollama (Apache-2.0 model repository, MIT runtime). No inference was run for this MVP evaluation.",
    },
    {
        "title": "Human decisions create the assurance record",
        "deck": "Separate technical applicability, remediation planning, approval, and evidence verification.",
        "sections": [
            {
                "heading": "Role-gated lifecycle",
                "body": "A reviewer can run analysis and record an applicable/not-applicable decision with a rationale. An engineer can propose a mitigation, owner, and due date. An approver independently accepts/rejects the ticket. Evidence is then attached with a hash and reference; an approver verifies a selected record and supplies a rationale.",
            },
            {
                "heading": "Audit and exports",
                "body": "Application actions create append-only audit events with actor, role, timestamp, entity, and details. The report includes source publication/update dates, matching reasons, human decisions, remediation state, evidence references/hashes, and audit history.",
            },
            {
                "heading": "What the MVP does not claim",
                "body": "Demo bearer tokens are intentionally visible and unsafe for production. The audit database is not WORM or cryptographically immutable. Evidence is text/metadata rather than binary attachments. No certification, compliance determination, or verified operational-risk reduction is claimed.",
            },
        ],
        "callout": "The demo evidence is simulated. Verification changes application workflow status; it does not attest to a real plant modification.",
    },
    {
        "title": "Commercial opportunity: focused assurance around OT data",
        "deck": "Potential users span operators, contractors, and service providers with different inventory systems.",
        "sections": [
            {
                "heading": "Interview targets",
                "body": "Water and wastewater utilities; energy operators; oil and gas infrastructure; industrial maintenance contractors; managed OT security service providers; and defense-support facilities. Likely champions are OT security leads, plant engineering managers, asset owners, CISOs, and service-practice owners.",
            },
            {
                "heading": "Competitive landscape",
                "body": "Claroty, Tenable, and Nozomi publicly describe broad OT asset visibility, vulnerability/exposure management, monitoring, and remediation workflows. ServiceNow and other GRC/IRM suites manage enterprise risk, controls, audit, and work processes. OTProof's possible wedge is a local, source-linked and conservative review workflow that may complement existing products; this is a hypothesis, not a demonstrated product advantage. Better evidence handover may support audit preparation and help operators review exposure sooner, but neither compliance outcomes nor risk reduction have been measured.",
            },
            {
                "heading": "Illustrative annual revenue model",
                "body": "Assume 3 licensed sites per customer at $36,000/site/year; $25,000 onboarding per new customer; 78% recurring software gross margin; and 40% onboarding-services gross margin. The scenarios below are arithmetic examples only—not bookings, market sizing, or a forecast.",
                "table": [
                    ["Customers", "Sites", "Recurring ARR", "Year-1 revenue", "Year-1 gross profit"],
                    ["1", "3", "$108k", "$133k", "$94k"],
                    ["5", "15", "$540k", "$665k", "$471k"],
                    ["10", "30", "$1.08m", "$1.33m", "$942k"],
                    ["25", "75", "$2.70m", "$3.33m", "$2.36m"],
                ],
            },
        ],
        "callout": "Other revenue paths: enterprise license, integrations, deployment, and ongoing assurance services. Price and margin assumptions need buyer interviews and cost validation.",
    },
    {
        "title": "Measured MVP, open questions, and the next proof points",
        "deck": "The first test is repeatable behavior against labeled edge cases—not a broad product claim.",
        "sections": [
            {
                "heading": "Fixture baseline (26 Oct 2026)",
                "body": "14 labeled asset/advisory pairs: 4 applicable, 4 not applicable, and 6 expected manual verification. The deterministic matcher produced 14/14 expected labels, 100% precision/recall on four positive fixture examples, 0 labeled false negatives, and 6/6 expected abstentions. Every labeled result retained source ID, URL, and excerpt.",
            },
            {
                "heading": "Performance and security checks",
                "body": "One in-process pass over 80 assets × 3 advisories (240 pairs) measured about 1.05 ms on the development machine; this excludes network, database, and human review. Tests cover stale-cache fallback, duplicate IDs, macro-enabled workbook rejection, source quote validation, prompt injection as untrusted data, role authorization, and remediation evidence verification.",
            },
            {
                "heading": "Roadmap and pilot ask",
                "body": "Next: (1) invite 3–5 operator design partners, (2) label a diverse, source-reviewed multi-vendor dataset, (3) run blinded engineering adjudication and measure false negatives/abstentions, (4) add SSO, durable audit export, and CMMS/GRC connectors, (5) conduct a threat model and deployment review. Ask: a water/energy operator and OT engineers to validate the workflow, data fields, and trust boundaries.",
            },
        ],
        "callout": "Human review time, AI extraction accuracy, field accuracy, cost savings, and production performance remain unmeasured.",
        "sources": [
            "NIST SP 800-82 Rev. 3 final: https://csrc.nist.gov/pubs/sp/800/82/r3/final",
            "CISA advisory fixture provenance: data/fixtures/SOURCES.md",
            "Technology and competitive references: docs/TECHNOLOGY_DECISIONS.md and docs/RESEARCH_NOTES.md",
        ],
    },
]


SLIDES = [
    {
        "title": "OTProof",
        "subtitle": "Evidence-first vulnerability applicability and remediation assurance for industrial assets",
        "bullets": [
            "Reconcile an operator inventory with public ICS advisories",
            "Show exact product/version evidence and uncertainty",
            "Keep engineering and approval decisions human-owned",
        ],
        "metric": "READ-ONLY",
        "metric_label": "No OT interaction in this MVP",
        "right_items": ["80 fictional assets", "3 real CISA advisories", "Offline-ready demo"],
        "kind": "cover",
        "source": "Eureka Hackathon · MVP snapshot 26 Oct 2026",
        "notes": "Introduce OTProof as a small, evidence-first assurance workflow for vulnerability applicability and remediation review. It starts with an operator-provided CSV or spreadsheet and compares it with approved public advisory information. Deterministic rules make the first applicability classification; a person handles uncertainty, remediation approval, and evidence verification. The demonstration dataset is fictional and the advisory records are real public CISA examples. The application never scans, exploits, or modifies industrial equipment. The aim of this pitch is to validate whether operators need a focused workflow alongside their existing OT security and GRC systems.",
    },
    {
        "title": "The review gap lives between two records",
        "subtitle": "An advisory lists products and versions. An operator owns assets, maintenance context, and change decisions.",
        "bullets": [
            "Inventory identifiers and advisory product language often differ",
            "A version match can be exact, excluded, or impossible to confirm",
            "Teams must preserve the source and explain what they decided",
        ],
        "metric": "3 RECORDS",
        "metric_label": "Inventory · advisory · remediation evidence",
        "right_items": ["Asset inventory", "Public advisory", "Engineering record"],
        "source": "NIST SP 800-82 Rev. 3 final · https://csrc.nist.gov/pubs/sp/800/82/r3/final",
        "notes": "The workflow problem is not merely a lack of vulnerability data. Teams need to connect a specific installed asset to a specific published affected product/version and keep the basis for their decision. Inventory records may have old timestamps, vendor spelling differences, or missing firmware. Advisories may use a different product family name or a nuanced version boundary. A loose name match can create noise, while a missing version can block a safe conclusion. NIST SP 800-82 Revision 3, the current published final guide used here, emphasizes accurate inventory details and careful evaluation of automated OT collection methods. OTProof begins from records operators already have.",
    },
    {
        "title": "Critical infrastructure needs cautious handling",
        "subtitle": "Water, energy, oil and gas, and industrial operators balance security with continuity, safety, and maintenance constraints.",
        "bullets": [
            "A vulnerability label alone does not prove local applicability",
            "A patch suggestion is not an approved operational change",
            "Human review and source traceability belong in the workflow",
        ],
        "metric": "NO DEVICE",
        "metric_label": "Discovery or configuration change",
        "right_items": ["File-based inventory", "Public source egress", "Human-led review"],
        "source": "NIST SP 800-82 Rev. 3 final; Rev. 4 remains an initial public draft as of 26 Oct 2026.",
        "notes": "OT environments have availability, reliability, and safety requirements that shape how security work is performed. OTProof is deliberately not an asset discovery product and does not ask an operator to scan or modify controllers, gateways, HMIs, or supervisory systems. The user supplies the inventory, and the service retrieves public advisory information. NIST lists Revision 3 as final and Revision 4 as a draft from September 2026, so these materials cite Revision 3 as final. The product's role is narrower: produce an explainable candidate and leave technical applicability, change planning, approval, and verification with authorized staff.",
    },
    {
        "title": "One auditable workflow from import to assurance",
        "subtitle": "A repeatable sequence connects a source statement to an engineering decision and evidence record.",
        "bullets": [
            "Validate inventory and import approved public advisory data",
            "Compare vendor, product, configuration, and version constraints",
            "Record review, ticket approval, evidence, and verification",
        ],
        "metric": "6 STEPS",
        "metric_label": "Import → compare → review → plan → evidence → verify",
        "right_items": ["Source linked", "Role gated", "Exportable"],
        "kind": "workflow",
        "source": "End-to-end journey is implemented in the MVP dashboard and API.",
        "notes": "Walk through the six steps. First, load a CSV or XLSX inventory and validate required fields, identifiers, and workbook type. Second, import CISA ICS or KEV data, an NVD CVE record, or an approved vendor bulletin; offline fixtures remain available. Third, run deterministic matching and inspect every source and inventory field. Fourth, an engineer or reviewer records an applicability decision and rationale. Fifth, a remediation action can be proposed and approved by a separate approver. Sixth, evidence is attached and verified against a selected record. The assurance report exports that chain. A generated summary or an attached evidence note cannot independently close a finding.",
    },
    {
        "title": "Demo: three assets, three distinct outcomes",
        "subtitle": "A CISA FactoryTalk View advisory exposes why version and inventory quality matter.",
        "bullets": [
            "FactoryTalk View SE 13.0.0 → applicable candidate",
            "FactoryTalk View SE 14.0 → outside the exact affected version",
            "Same product with missing firmware → engineering review",
        ],
        "metric": "ICSA-24-226-06",
        "metric_label": "CISA · published 13 Aug 2024 · updated 29 Aug 2024",
        "right_items": ["CVE-2024-7513", "Source statement: version 13.0", "Source URL retained"],
        "source": "https://www.cisa.gov/news-events/ics-advisories/icsa-24-226-06",
        "notes": "Use the fixture example to show the three labels. CV-HMI-001 records FactoryTalk View Site Edition version 13.0.0. The matcher normalizes a curated product alias and numeric trailing zero, then compares the installed version to CISA's affected statement for FactoryTalk View SE version 13.0. CV-HMI-002 uses the same product at 14.0, which is outside the exact version statement. CV-HMI-005 has no firmware version; the correct result is manual verification because product identity alone is insufficient. The advisory is genuine and its CISA URL and publication/update dates are included. The utility and asset records are fictional.",
    },
    {
        "title": "Deterministic matching earns each conclusion",
        "subtitle": "A small ruleset handles explicit source evidence; unsupported cases abstain.",
        "bullets": [
            "Normalize only curated vendor and product aliases",
            "Apply explicit equality and inclusive/exclusive version bounds",
            "Route ambiguity, stale data, duplicates, and unknown syntax to review",
        ],
        "metric": "3 OUTCOMES",
        "metric_label": "Applicable · not applicable · manual verification",
        "right_items": ["Exact identity", "Published constraint", "Traceable rationale"],
        "source": "Matcher implementation: backend/app/services/matching.py",
        "notes": "The matcher is intentionally conservative. It normalizes case and punctuation and applies a short, curated alias map. It does not use Sentence Transformers or an embedding score as a vulnerability verdict. Numeric dotted versions are compared against supported operators. Constraints within one CPE match are conjunctive; alternate product candidates remain alternatives. Missing firmware, a stale inventory verification date, unknown model, duplicate identity, unsupported suffixes, or compound NVD configuration logic produce a manual-review outcome. Every result keeps the inventory values, advisory identifier, source URL, excerpt, and explanation. Product and model catalogs still need wider field validation.",
    },
    {
        "title": "AI reads advisory text; people decide",
        "subtitle": "The local model is an optional extraction assistant behind schema and source checks.",
        "bullets": [
            "Draft structured vendor, product, CVE, version, and mitigation fields",
            "Treat embedded advisory instructions as untrusted text",
            "Keep model output out of applicability and remediation state",
        ],
        "metric": "OPTIONAL",
        "metric_label": "Local Ollama adapter · no inference run in evaluation",
        "right_items": ["Pydantic schema", "Verbatim source evidence", "Suggestion only"],
        "source": "Optional Qwen2.5 7B Instruct model; Apache-2.0 model repo. No weights included.",
        "notes": "AI is a small, optional component, not the core decision maker. A local Ollama-compatible server can propose structured extraction and a plain-language summary. The prompt identifies advisory content as untrusted and says to ignore embedded commands. Pydantic validates output shape, and cited identifiers, product/version/mitigation strings, and quotes are checked against the source. These checks reduce unsupported output but cannot prove summary completeness or correctness. The application labels the result suggestion-only. The model was not installed or run during this MVP validation, and no extraction accuracy benefit is claimed. A future evaluation should compare blinded model outputs against engineer-labeled source excerpts and deterministic extraction baselines.",
    },
    {
        "title": "A compact architecture keeps evidence close to the decision",
        "subtitle": "A modular monolith is easier to inspect and package for a controlled first pilot.",
        "bullets": [
            "React + TypeScript dashboard, FastAPI + Pydantic service",
            "PostgreSQL deployment; SQLite for local offline demonstration",
            "Cached public sources, deterministic matcher, audit and report services",
        ],
        "metric": "NO OT PATH",
        "metric_label": "The API has no device protocol client or scanner",
        "right_items": ["Inventory / sources", "API + database", "Review / reports"],
        "kind": "architecture",
        "source": "Full technical design: OTProof_Technical_Design.md",
        "notes": "Describe the technology choices as an implementation, not a production certification. The UI is React and TypeScript. FastAPI validates routes and Pydantic schemas. SQLAlchemy sits over PostgreSQL for deployment and SQLite for quick local use. Alembic tracks schema migrations. Source adapters store cached payloads and metadata; the matcher produces traceable findings; workflow services record decisions; ReportLab exports PDF. Docker Compose packages the services, although a Docker daemon was unavailable in the build environment, so startup was not verified. The optional LLM calls a local inference endpoint. No service connects to an OT address range or equipment protocol.",
    },
    {
        "title": "From finding to verified evidence",
        "subtitle": "Role separation prevents generated text or a proposed ticket from becoming a remediation claim.",
        "bullets": [
            "Reviewer records applicability with a rationale",
            "Engineer proposes action; approver accepts or rejects",
            "Approver verifies evidence before the workflow closes",
        ],
        "metric": "4 ROLES",
        "metric_label": "Engineer · reviewer · approver · admin",
        "right_items": ["Decision", "Ticket", "Evidence", "Verification"],
        "source": "Demo bearer tokens are public; production identity integration is required.",
        "notes": "Show that decisions are distinct records. A reviewer records whether the advisory applies and why. An engineer proposes a mitigation with an owner and date, and a separate approver can approve or reject that plan. The engineer attaches evidence; the approver verifies a selected evidence record and explains the decision. The application hashes evidence text content and records the actor and role. Hashing only preserves a comparison value; it does not make the database immutable or prove the source document is authentic. The demo workflow uses visible local tokens for convenience and is not a production authentication setup. In a real deployment, use managed identities and protected audit storage.",
    },
    {
        "title": "Positioning: complement an established OT security landscape",
        "subtitle": "Broad platforms already offer inventory and exposure workflows; the proposed wedge is narrower.",
        "bullets": [
            "Claroty, Tenable, and Nozomi describe broad OT visibility and risk products",
            "GRC / IRM platforms manage enterprise risk, controls, and audit workflow",
            "Test if source-linked review fills a process gap or integrates cleanly",
        ],
        "metric": "HYPOTHESIS",
        "metric_label": "Focused assurance is not yet a proven advantage",
        "right_items": ["OT platforms", "GRC / ITSM", "OTProof integration target"],
        "kind": "competition",
        "source": "Claroty · Tenable · Nozomi · ServiceNow public product documentation; see notes.",
        "notes": "Treat competitors respectfully and accurately. Claroty describes a broad CPS platform across inventory, exposure, protection, and secure access (https://claroty.com/platform). Tenable describes OT asset inventory, vulnerability prioritization, remediation and compliance integrations, and a combination of passive monitoring with vendor-approved active queries (https://www.tenable.com/products/ot-security). Nozomi documentation describes asset discovery, firmware information, and vulnerability assessment (https://technicaldocs.nozominetworks.com/guardian/latest/products/guardian/topics/intro/c_guardian.html). ServiceNow describes risk assessment and issue workflows within its GRC/IRM products (https://www.servicenow.com/docs/r/governance-risk-compliance/grc-risk-management-workspace/grc-risk-overview.html). OTProof has not outperformed these products and may not replace them. The hypothesis to validate is whether a file-first, evidence-centric reconciliation flow is useful in a small team or as a data/workflow connector to existing platforms. Pilot interviews and integration testing will decide.",
    },
    {
        "title": "A site license plus deployment and assurance services",
        "subtitle": "Start with a transparent per-site hypothesis, then validate effort and willingness to pay.",
        "bullets": [
            "Illustrative license: $36,000 per site per year",
            "Illustrative onboarding: $25,000 per new customer",
            "Enterprise tiers, integrations, and ongoing review services are options",
        ],
        "metric": "$2.70M",
        "metric_label": "Illustrative ARR at 25 customers × 3 sites each",
        "right_items": ["1 customer · $108k ARR", "5 customers · $540k ARR", "10 customers · $1.08m ARR", "25 customers · $2.70m ARR"],
        "kind": "business",
        "source": "Illustrative arithmetic only; assumptions in OTProof_Business_Case.pdf.",
        "notes": "These are illustrative scenarios, not market research, signed orders, or a revenue forecast. The model assumes three licensed sites per customer at $36,000 per site per year, $25,000 onboarding revenue per new customer, a 78% software gross margin, and 40% services gross margin. The 25-customer case implies 75 licensed sites and $2.70 million recurring ARR. First-year revenue includes onboarding; recurring gross profit excludes services. Sales cycle, procurement, hosting, support, data onboarding and integration costs are not yet measured. Validate the price with target operators and service providers, and derive gross margin from observed deployment and support costs.",
    },
    {
        "title": "MVP baseline: correct on a small, explicit fixture set",
        "subtitle": "The results show the code follows the labels supplied; they do not estimate field accuracy.",
        "bullets": [
            "14/14 labeled cases matched expected outcomes",
            "4 applicable cases: 100% fixture precision/recall, 0 fixture false negatives",
            "6/6 uncertainty cases abstained; 14/14 outputs had source traceability",
        ],
        "metric": "~1.05 ms",
        "metric_label": "One matcher pass across 240 in-process pairs",
        "right_items": ["80 fictional assets", "3 advisory fixtures", "LLM extraction not run"],
        "kind": "validation",
        "source": "reports/evaluation_metrics.json · run dated 26 Oct 2026",
        "notes": "This is a deliberately small synthetic fixture evaluation. It has 14 labeled pairs: four applicable, four not applicable, and six manual verification. All expected outcomes were produced, including every expected abstention, and each output carried source identifiers, URL, and excerpt. The 100% values are not statistically meaningful estimates for unseen products; four positives are too few for that. The approximately 1.05 millisecond benchmark is a single in-process matcher pass over 240 combinations on the development machine. It excludes database and network time. The local model was not run, extraction accuracy is not measured, and no operator time study or savings estimate has been validated.",
    },
    {
        "title": "Trust boundaries are product requirements",
        "subtitle": "Keep OT interactions passive and offline in the MVP, and reserve consequential decisions for people.",
        "bullets": [
            "No scan, exploit, device query, or configuration modification",
            "Treat uploads and advisory text as untrusted content",
            "Approval and verification require role-gated human action",
        ],
        "metric": "HUMAN",
        "metric_label": "Owns applicability and remediation decisions",
        "right_items": ["Public sources only", "Evidence and audit trail", "Production auth still required"],
        "source": "Threat model, identity, immutable audit, and security testing remain pilot work.",
        "notes": "Restate the safety boundary in practical terms. OTProof reads operator-uploaded files and public web sources only. It does not send packets to controllers or install fixes. Uploaded data and advisory pages are treated as untrusted. The optional model is explicitly told not to follow content instructions; structured output is validated against schema and source text. Role checks guard engineering decisions, ticket approvals, and verification. However, the demo token system is not production-grade, the database audit trail can be changed by a privileged database operator, and the tests are not a penetration test. A production pilot requires identity integration, threat modeling, security review, backup and retention controls, and operator approval.",
    },
    {
        "title": "Next: validate with OT engineers and real workflow constraints",
        "subtitle": "The next milestone is evidence of usefulness, not a larger feature checklist.",
        "bullets": [
            "Recruit 3–5 operator or managed-service design partners",
            "Build a blinded, multi-vendor adjudication set with engineers",
            "Measure false negatives, abstentions, review time, and onboarding effort",
        ],
        "metric": "PILOT ASK",
        "metric_label": "Water / energy operator + OT engineering reviewers",
        "right_items": ["Broaden source/vendor coverage", "Add SSO and durable audit", "Test CMMS / GRC connectors"],
        "source": "No customer interviews, paid pilots, or measured savings are claimed yet.",
        "notes": "Close with a concrete ask: access to an OT security and engineering team willing to evaluate a controlled pilot using non-sensitive or approved inventory data. The pilot should use multiple vendors, equipment families, and source formats. Engineers should create expected labels before seeing the matcher output, then adjudicate disagreements. Measure missing-data abstention quality, false negatives, false positives, source traceability, minutes per asset/advisory review, onboarding hours, integration requirements, and willingness to pay. Later work includes SSO, stronger audit retention, packaging hardening, and CMMS/GRC integration. This pitch makes no claim of customers, market sizing, savings, or improved risk outcomes. Those are the hypotheses the pilot should test.",
    },
]


def hex_color(value: str) -> colors.Color:
    return colors.HexColor(f"#{value}")


def safe_pdf(text: str) -> str:
    return (
        text.replace("→", "to")
        .replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("×", "x")
        .replace("·", " / ")
        .replace("≤", "<=")
        .replace("≥", ">=")
        .replace("é", "e")
    )


def idea_docx() -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.68)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)
    section.header_distance = Inches(0.32)
    section.footer_distance = Inches(0.3)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    for style_name, size, color in [("Title", 34, NAVY), ("Heading 1", 24, NAVY), ("Heading 2", 12, TEAL)]:
        style = doc.styles[style_name]
        style.font.name = "Aptos Display" if style_name != "Heading 2" else "Aptos"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
    header = section.header.paragraphs[0]
    header.text = "OTPROOF   /   EUREKA HACKATHON"
    header.runs[0].font.name = "Aptos"
    header.runs[0].font.size = Pt(8)
    header.runs[0].font.bold = True
    header.runs[0].font.color.rgb = RGBColor.from_string(TEAL)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.text = "PRODUCT IDEA   •   26 OCT 2026"
    footer.runs[0].font.size = Pt(7)
    footer.runs[0].font.color.rgb = RGBColor.from_string(MUTED)

    for page_index, page in enumerate(IDEA_PAGES):
        if page_index:
            doc.add_page_break()
        if page.get("cover"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(55)
            run = p.add_run("OTPROOF")
            run.font.name = "Aptos Display"
            run.font.size = Pt(40)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string(NAVY)
            sub = doc.add_paragraph()
            sub.paragraph_format.space_after = Pt(22)
            run = sub.add_run(page["deck"])
            run.font.size = Pt(17)
            run.font.color.rgb = RGBColor.from_string(TEAL)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(5)
            run = p.add_run("PROJECT IDEA  /  OT CYBERSECURITY")
            run.font.size = Pt(8)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string(TEAL)
            doc.add_heading(page["title"], level=1)
            p = doc.add_paragraph(page["deck"])
            p.paragraph_format.space_after = Pt(13)
            p.runs[0].font.size = Pt(11)
            p.runs[0].font.color.rgb = RGBColor.from_string(MUTED)
        if page.get("tiles"):
            table = doc.add_table(rows=1, cols=len(page["tiles"]))
            table.autofit = True
            for cell, (value, label) in zip(table.rows[0].cells, page["tiles"], strict=True):
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                cell.text = ""
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(value + "\n")
                run.font.size = Pt(22)
                run.font.bold = True
                run.font.color.rgb = RGBColor.from_string(TEAL)
                run = p.add_run(label)
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor.from_string(MUTED)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        for content in page["sections"]:
            doc.add_heading(content["heading"], level=2)
            if content.get("body"):
                para = doc.add_paragraph(content["body"])
                para.paragraph_format.keep_together = True
            if content.get("bullets"):
                for bullet in content["bullets"]:
                    para = doc.add_paragraph(bullet, style="List Bullet")
                    para.paragraph_format.space_after = Pt(2)
            if content.get("table"):
                table = doc.add_table(rows=len(content["table"]), cols=len(content["table"][0]))
                table.style = "Light Shading Accent 1"
                for r, row in enumerate(content["table"]):
                    for c, value in enumerate(row):
                        cell = table.cell(r, c)
                        cell.text = str(value)
                        for run in cell.paragraphs[0].runs:
                            run.font.size = Pt(7.5)
                            if r == 0:
                                run.font.bold = True
        if page.get("callout"):
            table = doc.add_table(rows=1, cols=1)
            cell = table.cell(0, 0)
            cell.text = page["callout"]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                for run in p.runs:
                    run.font.size = Pt(8)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor.from_string(NAVY)
        for source in page.get("sources", []):
            para = doc.add_paragraph(source)
            para.paragraph_format.space_after = Pt(1)
            for run in para.runs:
                run.font.size = Pt(7)
                run.font.color.rgb = RGBColor.from_string(MUTED)
    doc.save(ROOT / "OTProof_Idea_Document.docx")


def pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "OTeyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9,
            textColor=hex_color(TEAL), spaceAfter=2 * mm, uppercase=True
        ),
        "title": ParagraphStyle(
            "OTtitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27,
            textColor=hex_color(NAVY), alignment=TA_LEFT, spaceAfter=3 * mm
        ),
        "cover": ParagraphStyle(
            "OTcover", parent=base["Title"], fontName="Helvetica-Bold", fontSize=34, leading=39,
            textColor=hex_color(NAVY), alignment=TA_LEFT, spaceAfter=6 * mm
        ),
        "deck": ParagraphStyle(
            "OTdeck", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=14,
            textColor=hex_color(MUTED), spaceAfter=6 * mm
        ),
        "h2": ParagraphStyle(
            "OTh2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13,
            textColor=hex_color(TEAL), spaceBefore=2 * mm, spaceAfter=1.3 * mm, keepWithNext=True
        ),
        "body": ParagraphStyle(
            "OTbody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.7, leading=12,
            textColor=hex_color(INK), spaceAfter=2.5 * mm
        ),
        "small": ParagraphStyle(
            "OTsmall", parent=base["BodyText"], fontName="Helvetica", fontSize=7, leading=9,
            textColor=hex_color(MUTED), spaceAfter=1 * mm
        ),
        "cell": ParagraphStyle(
            "OTcell", parent=base["BodyText"], fontName="Helvetica", fontSize=7, leading=8.5,
            textColor=hex_color(INK), spaceAfter=0
        ),
        "bullet": ParagraphStyle(
            "OTbullet", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11,
            leftIndent=11, firstLineIndent=-7, bulletIndent=0, textColor=hex_color(INK), spaceAfter=1.5 * mm
        ),
    }


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(safe_pdf(text)).replace("\n", "<br/>"), style)


def doc_callout(text: str, width: float) -> Table:
    t = Table([[para(text, ParagraphStyle("callouttext", parent=pdf_styles()["body"], fontName="Helvetica-Bold", textColor=hex_color(NAVY), spaceAfter=0))]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), hex_color(MINT)),
        ("BOX", (0, 0), (-1, -1), 0.5, hex_color(TEAL)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def idea_pdf() -> None:
    styles = pdf_styles()
    target = ROOT / "OTProof_Idea_Document.pdf"

    def on_page(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(hex_color(TEAL))
        canvas.rect(0, h - 7 * mm, w, 7 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(hex_color(MUTED))
        canvas.drawString(15 * mm, 8 * mm, "OTPROOF  /  EUREKA HACKATHON  /  26 OCT 2026")
        canvas.drawRightString(w - 15 * mm, 8 * mm, f"{doc.page:02d}  /  08")
        canvas.restoreState()

    story = []
    width = A4[0] - 30 * mm
    for index, page in enumerate(IDEA_PAGES):
        if index:
            story.append(PageBreak())
        if page.get("cover"):
            story.extend([Spacer(1, 28 * mm), para(page["title"], styles["cover"]), para(page["deck"], styles["deck"])])
        else:
            story.extend([para("PROJECT IDEA  /  OT CYBERSECURITY", styles["eyebrow"]), para(page["title"], styles["title"]), para(page["deck"], styles["deck"])])
        if page.get("tiles"):
            cells = []
            big_tile = ParagraphStyle(
                "big_tile", parent=styles["cell"], fontName="Helvetica-Bold", fontSize=20,
                leading=22, textColor=hex_color(TEAL), alignment=1,
            )
            small_tile = ParagraphStyle(
                "small_tile", parent=styles["cell"], fontSize=7.5, leading=9,
                textColor=hex_color(MUTED), alignment=1,
            )
            for value, label in page["tiles"]:
                cells.append([Paragraph(escape(value), big_tile), para(label, small_tile)])
            t = Table([cells], colWidths=[width / len(cells)] * len(cells), rowHeights=[19 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), hex_color(PAPER)),
                ("BOX", (0, 0), (-1, -1), 0.5, hex_color("D3E2E0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, hex_color("D3E2E0")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.extend([t, Spacer(1, 6 * mm)])
        for content in page["sections"]:
            block = [para(content["heading"], styles["h2"])]
            if content.get("body"):
                block.append(para(content["body"], styles["body"]))
            if content.get("bullets"):
                block.extend(para("•  " + item, styles["bullet"]) for item in content["bullets"])
            if content.get("table"):
                header_cell = ParagraphStyle(
                    "ideatablehead", parent=styles["cell"], textColor=colors.white,
                    fontName="Helvetica-Bold",
                )
                table_data = [
                    [para(str(value), header_cell if row_index == 0 else styles["cell"]) for value in row]
                    for row_index, row in enumerate(content["table"])
                ]
                col_widths = [width * .12, width * .09, width * .25, width * .25, width * .29]
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), hex_color(NAVY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), hex_color(PAPER)),
                    ("GRID", (0, 0), (-1, -1), 0.35, hex_color("D0DDDC")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                block.extend([table, Spacer(1, 2 * mm)])
            story.append(KeepTogether(block))
        if page.get("callout"):
            story.extend([Spacer(1, 3 * mm), doc_callout(page["callout"], width)])
        if page.get("sources"):
            story.extend([Spacer(1, 3 * mm)])
            story.extend(para(text, styles["small"]) for text in page["sources"])
    document = SimpleDocTemplate(
        str(target), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=16 * mm, title="OTProof Idea Document",
        author="OTProof",
    )
    document.build(story, onFirstPage=on_page, onLaterPages=on_page)


def make_ppt_text(slide, x, y, w, h, text, *, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, font="Aptos"):
    shape = slide.shapes.add_textbox(PptInches(x), PptInches(y), PptInches(w), PptInches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = PptInches(0)
    frame.margin_right = PptInches(0)
    frame.margin_top = PptInches(0)
    frame.margin_bottom = PptInches(0)
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    paragraph.font.name = font
    paragraph.font.size = PptPt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = PPTColor.from_string(color)
    return shape


def ppt_box(slide, x, y, w, h, fill, *, radius=True, line=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, PptInches(x), PptInches(y), PptInches(w), PptInches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = PPTColor.from_string(fill)
    if line:
        shape.line.color.rgb = PPTColor.from_string(line)
        shape.line.width = PptPt(1)
    else:
        shape.line.fill.background()
    return shape


def ppt_diagram(slide, kind: str, item: dict) -> None:
    items = item.get("right_items", [])
    x, y, w, h = 7.45, 1.82, 5.25, 4.68
    ppt_box(slide, x, y, w, h, NAVY_2)
    make_ppt_text(slide, x + .3, y + .28, w - .6, .3, "OTPROOF / FIELD VIEW", size=8, color="8FC7BE", bold=True)
    if kind == "architecture":
        labels = ["INVENTORY + SOURCES", "VALIDATION + CACHE", "MATCH + WORKFLOW", "REPORT + AUDIT"]
        for i, label in enumerate(labels):
            bx = x + .42 + (i % 2) * 2.25
            by = y + .92 + (i // 2) * 1.35
            ppt_box(slide, bx, by, 1.88, .72, "2C4955")
            make_ppt_text(slide, bx + .12, by + .19, 1.64, .36, label, size=9, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        for ax, ay, bx, by in [(x + 2.3, y + 1.28, x + 2.86, y + 1.28), (x + 2.3, y + 2.63, x + 2.86, y + 2.63)]:
            connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, PptInches(ax), PptInches(ay), PptInches(bx), PptInches(by))
            connector.line.color.rgb = PPTColor.from_string(TEAL)
            connector.line.width = PptPt(2)
        make_ppt_text(slide, x + .55, y + 3.83, w - 1.1, .46, "OPTIONAL LOCAL LLM · suggestion only", size=10, color="C4DBD8", align=PP_ALIGN.CENTER)
    elif kind == "workflow":
        steps = ["IMPORT", "MATCH", "REVIEW", "PLAN", "EVIDENCE", "VERIFY"]
        for i, label in enumerate(steps):
            cy = y + .85 + i * .56
            ppt_box(slide, x + .4, cy, .48, .42, TEAL)
            make_ppt_text(slide, x + .4, cy + .08, .48, .25, str(i + 1), size=11, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
            make_ppt_text(slide, x + 1.1, cy + .08, 3.6, .25, label, size=11, color=WHITE, bold=True)
    elif kind == "competition":
        labels = ["CLAROTY", "TENABLE", "NOZOMI", "SERVICE / GRC"]
        for i, label in enumerate(labels):
            by = y + .86 + i * .74
            ppt_box(slide, x + .35, by, 1.6, .5, "2C4955")
            make_ppt_text(slide, x + .43, by + .13, 1.43, .2, label, size=8, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
            make_ppt_text(slide, x + 2.18, by + .09, 2.64, .31, "Broader platform / workflow", size=9, color="C4DBD8")
        make_ppt_text(slide, x + .55, y + 4.1, w - 1.1, .3, "OTProof: focused evidence workflow hypothesis", size=9, color="8FC7BE", bold=True, align=PP_ALIGN.CENTER)
    elif kind == "business":
        rows = items[:4]
        for i, row in enumerate(rows):
            by = y + .9 + i * .78
            make_ppt_text(slide, x + .42, by, 2.48, .32, row.split(" · ")[0], size=10, color=WHITE, bold=True)
            make_ppt_text(slide, x + 3.05, by, 1.75, .32, row.split(" · ")[-1], size=11, color="8FE0CE", bold=True, align=PP_ALIGN.RIGHT)
            if i < len(rows) - 1:
                ppt_box(slide, x + .4, by + .43, w - .8, .01, "48606A", radius=False)
    elif kind == "validation":
        metric_cards = [("14/14", "labels"), ("4/4", "applicable recall"), ("6/6", "abstain"), ("14/14", "traceable")]
        for i, (value, label) in enumerate(metric_cards):
            bx = x + .4 + (i % 2) * 2.3
            by = y + .95 + (i // 2) * 1.24
            ppt_box(slide, bx, by, 1.98, .96, "2C4955")
            make_ppt_text(slide, bx + .1, by + .13, 1.78, .34, value, size=20, color="8FE0CE", bold=True, align=PP_ALIGN.CENTER)
            make_ppt_text(slide, bx + .1, by + .56, 1.78, .22, label, size=8, color="D0E0DF", align=PP_ALIGN.CENTER)
        make_ppt_text(slide, x + .45, y + 3.8, w - .9, .4, "Small synthetic test set · not field accuracy", size=9, color="F4C273", align=PP_ALIGN.CENTER)
    else:
        make_ppt_text(slide, x + .37, y + .82, w - .74, .78, item["metric"], size=29, color="8FE0CE", bold=True)
        make_ppt_text(slide, x + .37, y + 1.61, w - .74, .6, item["metric_label"], size=12, color="D0E0DF")
        for i, item in enumerate(items):
            cy = y + 2.52 + i * .54
            ppt_box(slide, x + .4, cy + .05, .12, .12, TEAL, radius=False)
            make_ppt_text(slide, x + .66, cy, w - .98, .36, item, size=10, color=WHITE)


def deck_pptx() -> None:
    prs = Presentation()
    prs.slide_width = PptInches(13.333)
    prs.slide_height = PptInches(7.5)
    blank = prs.slide_layouts[6]
    for idx, item in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        is_cover = item.get("kind") == "cover"
        bg = NAVY if is_cover else PAPER
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = PPTColor.from_string(bg)
        if is_cover:
            ppt_box(slide, .0, .0, .18, 7.5, TEAL, radius=False)
            ppt_box(slide, 7.25, .0, 6.083, 7.5, NAVY_2, radius=False)
            make_ppt_text(slide, .83, .63, 4.0, .3, "EUREKA HACKATHON  /  OT CYBERSECURITY", size=9, color="8FC7BE", bold=True)
            make_ppt_text(slide, .83, 1.45, 5.9, .82, "OTProof", size=40, color=WHITE, bold=True, font="Aptos Display")
            make_ppt_text(slide, .85, 2.38, 5.55, 1.0, item["subtitle"], size=20, color="D7E5E4")
            for i, bullet in enumerate(item["bullets"]):
                make_ppt_text(slide, .88, 4.08 + i * .55, 5.85, .4, "•  " + bullet, size=12, color=WHITE)
            make_ppt_text(slide, .86, 6.79, 5.8, .25, item["source"], size=8, color="9BB3B5")
            ppt_diagram(slide, "default", item)
        else:
            make_ppt_text(slide, .72, .34, 5.0, .22, "OTPROOF  /  EUREKA HACKATHON", size=8, color=TEAL, bold=True)
            make_ppt_text(slide, 12.12, .34, .45, .22, f"{idx:02d}", size=8, color=MUTED, bold=True, align=PP_ALIGN.RIGHT)
            make_ppt_text(slide, .72, .77, 11.9, .55, item["title"], size=25, color=NAVY, bold=True, font="Aptos Display")
            make_ppt_text(slide, .74, 1.38, 11.85, .36, item["subtitle"], size=11, color=MUTED)
            for i, bullet in enumerate(item["bullets"]):
                yy = 2.11 + i * 1.12
                ppt_box(slide, .77, yy + .04, .37, .37, TEAL)
                make_ppt_text(slide, .77, yy + .1, .37, .2, f"{i + 1:02d}", size=8, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
                make_ppt_text(slide, 1.36, yy, 5.55, .85, bullet, size=15, color=INK, bold=i == 0)
            ppt_diagram(slide, item.get("kind", "default"), item)
            make_ppt_text(slide, .74, 6.92, 11.75, .22, item.get("source", ""), size=7, color=MUTED)
        notes = item["notes"].strip()
        if len(notes.split()) < 70:
            raise ValueError(f"Slide {idx} speaker notes are too short ({len(notes.split())} words)")
        slide.notes_slide.notes_text_frame.text = notes
    prs.save(ROOT / "OTProof_Pitch_Deck.pptx")


def wrap_canvas_text(canvas, text: str, x: float, y_top: float, width: float, *, font="Helvetica", size=10, leading=14, color=INK):
    lines: list[str] = []
    current = ""
    for word in safe_pdf(text).split():
        trial = (current + " " + word).strip()
        if current and canvas.stringWidth(trial, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    canvas.setFillColor(hex_color(color))
    canvas.setFont(font, size)
    y = y_top
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def deck_pdf() -> None:
    target = ROOT / "OTProof_Pitch_Deck.pdf"
    page_size = (13.333 * 72, 7.5 * 72)
    c = __import__("reportlab.pdfgen.canvas", fromlist=["Canvas"]).Canvas(str(target), pagesize=page_size)
    for idx, item in enumerate(SLIDES, start=1):
        is_cover = item.get("kind") == "cover"
        bg = NAVY if is_cover else PAPER
        c.setFillColor(hex_color(bg))
        c.rect(0, 0, *page_size, fill=1, stroke=0)
        if is_cover:
            c.setFillColor(hex_color(TEAL))
            c.rect(0, 0, 13, page_size[1], fill=1, stroke=0)
            c.setFillColor(hex_color(NAVY_2))
            c.rect(7.25 * 72, 0, 6.083 * 72, page_size[1], fill=1, stroke=0)
            wrap_canvas_text(c, "EUREKA HACKATHON  /  OT CYBERSECURITY", 0.83 * 72, 6.75 * 72, 5.6 * 72, font="Helvetica-Bold", size=8, leading=10, color="8FC7BE")
            wrap_canvas_text(c, "OTProof", 0.83 * 72, 5.75 * 72, 5.8 * 72, font="Helvetica-Bold", size=38, leading=43, color=WHITE)
            wrap_canvas_text(c, item["subtitle"], 0.85 * 72, 4.78 * 72, 5.55 * 72, size=18, leading=23, color="D7E5E4")
            yy = 3.65 * 72
            for bullet in item["bullets"]:
                yy = wrap_canvas_text(c, "•  " + bullet, 0.9 * 72, yy, 5.7 * 72, size=10.5, leading=15, color=WHITE) - 9
            c.setFillColor(hex_color(NAVY_2))
            c.roundRect(7.65 * 72, 1.36 * 72, 4.85 * 72, 4.9 * 72, 12, fill=1, stroke=0)
            wrap_canvas_text(c, "OTPROOF / FIELD VIEW", 7.95 * 72, 5.95 * 72, 4.1 * 72, font="Helvetica-Bold", size=8, leading=10, color="8FC7BE")
            wrap_canvas_text(c, item["metric"], 7.95 * 72, 5.15 * 72, 4.2 * 72, font="Helvetica-Bold", size=28, leading=32, color="8FE0CE")
            wrap_canvas_text(c, item["metric_label"], 7.95 * 72, 4.65 * 72, 4.2 * 72, size=11, leading=14, color="D0E0DF")
            yy = 3.78 * 72
            for point in item["right_items"]:
                wrap_canvas_text(c, "•  " + point, 8.02 * 72, yy, 4.1 * 72, size=10, leading=14, color=WHITE)
                yy -= 0.5 * 72
            wrap_canvas_text(c, item["source"], 0.85 * 72, .43 * 72, 5.7 * 72, size=7, leading=9, color="9BB3B5")
        else:
            c.setFillColor(hex_color(TEAL))
            c.setFont("Helvetica-Bold", 8)
            c.drawString(.72 * 72, 7.14 * 72, "OTPROOF  /  EUREKA HACKATHON")
            c.setFillColor(hex_color(MUTED))
            c.drawRightString(12.63 * 72, 7.14 * 72, f"{idx:02d}")
            yy = wrap_canvas_text(c, item["title"], .72 * 72, 6.55 * 72, 11.9 * 72, font="Helvetica-Bold", size=23, leading=27, color=NAVY)
            wrap_canvas_text(c, item["subtitle"], .74 * 72, yy - 5, 11.8 * 72, size=10.5, leading=13, color=MUTED)
            yy = 4.9 * 72
            for bi, bullet in enumerate(item["bullets"]):
                c.setFillColor(hex_color(TEAL))
                c.roundRect(.77 * 72, (yy - 4) - bi * 1.06 * 72, .37 * 72, .37 * 72, 6, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 8)
                c.drawCentredString(.955 * 72, yy + 4 - bi * 1.06 * 72, f"{bi + 1:02d}")
                wrap_canvas_text(c, bullet, 1.36 * 72, yy + 10 - bi * 1.06 * 72, 5.55 * 72, size=13, leading=17, color=INK)
            x, y, w, h = 7.45 * 72, 1.82 * 72, 5.25 * 72, 4.68 * 72
            c.setFillColor(hex_color(NAVY_2))
            c.roundRect(x, y, w, h, 11, fill=1, stroke=0)
            wrap_canvas_text(c, "OTPROOF / FIELD VIEW", x + .3 * 72, y + h - .47 * 72, w - .6 * 72, font="Helvetica-Bold", size=8, leading=10, color="8FC7BE")
            if item.get("kind") == "architecture":
                labels = ["INVENTORY + SOURCES", "VALIDATION + CACHE", "MATCH + WORKFLOW", "REPORT + AUDIT"]
                for i, label in enumerate(labels):
                    bx = x + (.42 + (i % 2) * 2.25) * 72
                    by = y + (3.0 - (i // 2) * 1.35) * 72
                    c.setFillColor(hex_color("2C4955"))
                    c.roundRect(bx, by, 1.88 * 72, .72 * 72, 5, fill=1, stroke=0)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 8)
                    c.drawCentredString(bx + .94 * 72, by + .29 * 72, label)
                wrap_canvas_text(c, "OPTIONAL LOCAL LLM / suggestion only", x + .5 * 72, y + .48 * 72, w - 1 * 72, size=8.5, leading=10, color="C4DBD8")
            elif item.get("kind") == "workflow":
                steps = ["IMPORT", "MATCH", "REVIEW", "PLAN", "EVIDENCE", "VERIFY"]
                yy2 = y + h - .95 * 72
                for i, label in enumerate(steps):
                    c.setFillColor(hex_color(TEAL))
                    c.roundRect(x + .42 * 72, yy2 - i * .56 * 72, .48 * 72, .42 * 72, 4, fill=1, stroke=0)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 10)
                    c.drawCentredString(x + .66 * 72, yy2 + .13 * 72 - i * .56 * 72, str(i + 1))
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(x + 1.1 * 72, yy2 + .12 * 72 - i * .56 * 72, label)
            elif item.get("kind") == "validation":
                cards = [("14/14", "labels"), ("4/4", "applicable recall"), ("6/6", "abstain"), ("14/14", "traceable")]
                for i, (value, label) in enumerate(cards):
                    bx = x + (.4 + (i % 2) * 2.3) * 72
                    by = y + (2.75 - (i // 2) * 1.24) * 72
                    c.setFillColor(hex_color("2C4955"))
                    c.roundRect(bx, by, 1.98 * 72, .96 * 72, 6, fill=1, stroke=0)
                    c.setFillColor(hex_color("8FE0CE"))
                    c.setFont("Helvetica-Bold", 18)
                    c.drawCentredString(bx + .99 * 72, by + .53 * 72, value)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica", 8)
                    c.drawCentredString(bx + .99 * 72, by + .2 * 72, label)
                wrap_canvas_text(c, "Small synthetic set / not field accuracy", x + .45 * 72, y + .45 * 72, w - .9 * 72, size=8, leading=10, color="F4C273")
            elif item.get("kind") == "business":
                rows = item["right_items"][:4]
                yy2 = y + h - .9 * 72
                for i, row in enumerate(rows):
                    parts = row.split(" · ")
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(x + .42 * 72, yy2 - i * .78 * 72, parts[0])
                    c.setFillColor(hex_color("8FE0CE"))
                    c.drawRightString(x + 4.83 * 72, yy2 - i * .78 * 72, parts[-1])
                    if i < len(rows) - 1:
                        c.setStrokeColor(hex_color("48606A"))
                        c.line(x + .4 * 72, yy2 - .23 * 72 - i * .78 * 72, x + 4.85 * 72, yy2 - .23 * 72 - i * .78 * 72)
            elif item.get("kind") == "competition":
                labels = ["CLAROTY", "TENABLE", "NOZOMI", "SERVICE / GRC"]
                yy2 = y + h - .9 * 72
                for i, label in enumerate(labels):
                    by = yy2 - i * .74 * 72
                    c.setFillColor(hex_color("2C4955"))
                    c.roundRect(x + .35 * 72, by - .37 * 72, 1.6 * 72, .5 * 72, 4, fill=1, stroke=0)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 7.5)
                    c.drawCentredString(x + 1.15 * 72, by - .16 * 72, label)
                    c.setFillColor(hex_color("C4DBD8"))
                    c.setFont("Helvetica", 8)
                    c.drawString(x + 2.18 * 72, by - .18 * 72, "Broader platform / workflow")
            else:
                wrap_canvas_text(c, item["metric"], x + .37 * 72, y + h - .95 * 72, w - .74 * 72, font="Helvetica-Bold", size=27, leading=31, color="8FE0CE")
                yy2 = wrap_canvas_text(c, item["metric_label"], x + .37 * 72, y + h - 1.65 * 72, w - .74 * 72, size=11, leading=14, color="D0E0DF") - .25 * 72
                for point in item["right_items"]:
                    c.setFillColor(hex_color(TEAL))
                    c.rect(x + .4 * 72, yy2 - 3, .12 * 72, .12 * 72, fill=1, stroke=0)
                    yy2 = wrap_canvas_text(c, point, x + .66 * 72, yy2, w - .98 * 72, size=9.5, leading=12, color=WHITE) - .22 * 72
            wrap_canvas_text(c, item.get("source", ""), .74 * 72, .45 * 72, 11.8 * 72, size=6.5, leading=8, color=MUTED)
        c.showPage()
    c.save()


def callout_table(text: str, width: float) -> Table:
    styles = pdf_styles()
    t = Table([[para(text, ParagraphStyle("bizcallout", parent=styles["body"], fontName="Helvetica-Bold", spaceAfter=0))]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), hex_color(MINT)),
        ("BOX", (0, 0), (-1, -1), .5, hex_color(TEAL)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def styled_table(rows: list[list[str]], widths: list[float], *, font_size=7.5) -> Table:
    styles = pdf_styles()
    cell_style = ParagraphStyle("tablecell", parent=styles["cell"], fontSize=font_size, leading=font_size + 1.5)
    head_style = ParagraphStyle("tablehead", parent=cell_style, textColor=colors.white, fontName="Helvetica-Bold")
    data = []
    for r, row in enumerate(rows):
        data.append([para(str(value), head_style if r == 0 else cell_style) for value in row])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), hex_color(NAVY)),
        ("BACKGROUND", (0, 1), (-1, -1), hex_color(PAPER)),
        ("GRID", (0, 0), (-1, -1), .35, hex_color("D0DDDC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build_narrative_pdf(path: Path, title: str, pages: list[list]) -> None:
    def on_page(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(hex_color(TEAL))
        canvas.rect(0, height - 6 * mm, width, 6 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(hex_color(MUTED))
        canvas.drawString(14 * mm, 8 * mm, "OTPROOF  /  " + title.upper())
        canvas.drawRightString(width - 14 * mm, 8 * mm, f"{doc.page:02d}")
        canvas.restoreState()

    story = []
    for page_index, items in enumerate(pages):
        if page_index:
            story.append(PageBreak())
        story.extend(items)
    document = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=15 * mm, title=title, author="OTProof",
    )
    document.build(story, onFirstPage=on_page, onLaterPages=on_page)


def business_pdf(metrics: dict) -> None:
    styles = pdf_styles()
    width = A4[0] - 28 * mm
    p1 = [
        para("COMMERCIAL HYPOTHESES", styles["eyebrow"]),
        para("A focused layer for OT vulnerability assurance", styles["title"]),
        para("Potential users span small operators, contractors, and managed OT security providers. This is a customer discovery plan, not a market-size estimate.", styles["deck"]),
        para("Who may buy or champion", styles["h2"]),
        para("Municipal water and wastewater utilities; power and energy operators; oil and gas infrastructure; industrial maintenance contractors; managed OT security providers; and defense-support facilities. Likely champions include an OT security lead, plant engineering manager, asset owner, CISO, or managed-service practice owner.", styles["body"]),
        para("Position relative to existing products", styles["h2"]),
        para("Public product pages describe mature OT platforms and GRC/IRM workflows. OTProof is not positioned as a proven replacement. Its hypothesis is a small source-linked reconciliation workflow that may complement existing discovery, vulnerability, CMMS, and audit systems.", styles["body"]),
    ]
    competitor_rows = [
        ["Category", "Publicly described capability", "OTProof implication"],
        ["Claroty", "CPS asset inventory, exposure management, network protection, secure access, threat detection.", "Competes for broad OT platform budgets; possible data/workflow integration."],
        ["Tenable", "OT inventory, exposure prioritization, remediation guidance, integrations, compliance reporting.", "Broad incumbent; MVP has no coverage or accuracy advantage claim."],
        ["Nozomi", "Asset discovery, firmware details, vulnerability assessment, network visibility.", "Potential integration target; no comparative test run."],
        ["GRC / IRM", "Risk assessment, control, compliance, and audit workflow, e.g. ServiceNow.", "Potential downstream system of record; integration is future work."],
    ]
    p1.extend([styled_table(competitor_rows, [width * .15, width * .47, width * .38], font_size=7), Spacer(1, 3 * mm)])
    p1.extend([
        para("Differentiation hypothesis", styles["h2"]),
        para("OTProof emphasizes exact inventory/advisory evidence, conservative abstention when the source or inventory is incomplete, and a human assurance trail in one narrow workflow. Existing platforms may already solve the buyer's problem. Interviews and integration trials must establish whether a distinct product is useful.", styles["body"]),
        callout_table("Evidence to test: product coverage, engineer agreement, false negatives, abstention quality, review minutes per pair, onboarding effort, integration demand, willingness to pay, and renewal interest.", width),
    ])

    scenarios = [
        ["Customers", "Sites", "Recurring ARR", "Year-1 revenue", "Year-1 gross profit"],
        ["1", "3", "$108,000", "$133,000", "$94,240"],
        ["5", "15", "$540,000", "$665,000", "$471,200"],
        ["10", "30", "$1,080,000", "$1,330,000", "$942,400"],
        ["25", "75", "$2,700,000", "$3,325,000", "$2,356,000"],
    ]
    p2 = [
        para("ILLUSTRATIVE UNIT ECONOMICS", styles["eyebrow"]),
        para("Recurring site license with paid implementation", styles["title"]),
        para("A transparent first model makes the assumptions easy to challenge before a commercial forecast is attempted.", styles["deck"]),
        para("Scenario inputs", styles["h2"]),
        para("3 licensed sites per customer; $36,000 annual license per site; $25,000 one-time onboarding per new customer; 78% software gross margin; 40% onboarding-services gross margin. Year-1 revenue equals recurring ARR plus onboarding. Gross profit equals recurring ARR × 78% plus onboarding × 40%.", styles["body"]),
        styled_table(scenarios, [width * .12, width * .1, width * .22, width * .25, width * .31], font_size=7.5),
        Spacer(1, 3 * mm),
        callout_table("Illustrative arithmetic only. The scenarios are not customer commitments, an addressable-market calculation, bookings, or a revenue forecast. No revenue has been generated by this MVP.", width),
        para("Potential contract structure", styles["h2"]),
        para("Annual per-site subscription; enterprise tier for multi-site operators; integration and deployment fees; and optional ongoing assurance services. A local/on-premises deployment option may matter for sensitive inventories. Each component needs cost and procurement validation.", styles["body"]),
    ]
    labor_hours = 80 * 12 * (0.5 - 0.25)
    labor_savings = labor_hours * 80
    p2.extend([
        para("Illustrative labor sensitivity, not measured savings", styles["h2"]),
        para(f"Assume 80 assets, 12 relevant asset/advisory pairs per year, and a reduction from 30 to 15 minutes of initial triage per pair. That yields {labor_hours:.0f} theoretical hours, or ${labor_savings:,.0f} at an assumed $80 loaded hourly rate. This excludes engineering remediation effort and assumes every pair realizes the time reduction; the MVP has no human time study.", styles["body"]),
    ])

    p3 = [
        para("GO-TO-MARKET AND VALIDATION", styles["eyebrow"]),
        para("Sell a measurable workflow improvement, not an AI promise", styles["title"]),
        para("A controlled design-partner pilot should prove that the tool fits plant roles, records, and approval practices before product expansion.", styles["deck"]),
        para("Commercial route", styles["h2"]),
        para("Begin with 3–5 design partners from water, energy, industrial maintenance, or managed OT security. Offer an on-premises or isolated IT deployment for approved sample inventories. Integrate first with CSV/XLSX, then with a CMMS/GRC system only where pilot users show a recurring need. Sell onboarding as inventory normalization and workflow configuration, not a promise of automated risk removal.", styles["body"]),
        para("Customer value to measure", styles["h2"]),
        para("Measure review minutes per advisory/asset pair, the number of data gaps found, engineer agreement, false-negative adjudications, abstention rate, evidence completeness, time to export an audit package, onboarding hours, and continued use after the pilot. Potential benefits include less repeated source lookup, clearer audit evidence, and earlier engineering assessment of exposure. Those benefits remain hypotheses until measured; OTProof does not itself establish compliance or reduce operational risk.", styles["body"]),
        para("Key risks and response", styles["h2"]),
        para("Weak inventory quality can limit results; expose stale/missing data and assign owners. Advisory parsing can miss vendor nuance; preserve source excerpts and abstain. Established products may duplicate capabilities; position as complement and integrate. Sensitive asset information limits cloud adoption; test local deployment. Human review still costs time; quantify actual time saved and false-positive burden. Buyers may reject price; test paid pilots and renewal intent.", styles["body"]),
        para("Sources and market context", styles["h2"]),
        para("Competitor summaries are based on public vendor pages, not independent product tests: Claroty (claroty.com/platform), Tenable (tenable.com/products/ot-security), Nozomi (technicaldocs.nozominetworks.com/guardian), ServiceNow GRC (servicenow.com/docs). Full linked citations are in docs/RESEARCH_NOTES.md. Pricing, headcount, gross margin, customer conversion, and savings assumptions are illustrative.", styles["body"]),
        callout_table("Pilot success gate: verified engineering agreement and useful abstentions across multiple vendors, safe deployment acceptance, source traceability, measurable review-time change, and willingness to pay.", width),
    ]
    build_narrative_pdf(ROOT / "OTProof_Business_Case.pdf", "Business Case", [p1, p2, p3])


def evaluation_pdf(metrics: dict) -> None:
    styles = pdf_styles()
    width = A4[0] - 28 * mm
    det = metrics["deterministic_applicability"]
    data = metrics["dataset"]
    p1 = [
        para("FIXTURE EVALUATION · 26 OCT 2026", styles["eyebrow"]),
        para("A small deterministic baseline, measured honestly", styles["title"]),
        para("The evaluation checks whether the implementation follows an explicit, reproducible synthetic label set. It does not estimate real-world accuracy.", styles["deck"]),
        para("Dataset and measured result", styles["h2"]),
        para(f"{data['assets']} fictional assets × {data['advisories']} real public CISA advisory fixtures = {data['full_cross_product_pairs_benchmarked']} in-process comparison pairs. The labeled set has {data['labeled_pairs']} asset/advisory cases: 4 applicable, 4 not applicable, 6 manual verification.", styles["body"]),
        styled_table([
            ["Measure", "Result", "Scope"],
            ["Labeled classification accuracy", f"{det['labeled_case_accuracy']:.0%}", "14 authored synthetic cases"],
            ["Applicable precision / recall", f"{det['applicable_precision']:.0%} / {det['applicable_recall']:.0%}", "4 positive examples"],
            ["Applicable false-negative rate", f"{det['applicable_false_negative_rate']:.0%}", "In this fixture only"],
            ["Expected uncertainty abstention", f"{det['uncertainty']['manual_review_cases_abstained_correctly']}/{det['uncertainty']['manual_review_cases_expected']}", "Missing/stale/ambiguous cases"],
            ["Source traceability", f"{det['source_traceability']['pairs_with_advisory_id_url_and_excerpt']}/{det['source_traceability']['pairs_total']}", "ID + URL + excerpt present"],
            ["Matcher benchmark", f"{det['timing']['elapsed_ms']:.2f} ms total", "One 240-pair in-process pass"],
        ], [width * .32, width * .22, width * .46]),
        Spacer(1, 3 * mm),
        callout_table("Interpretation: 14/14 is evidence that this fixed test set passes, not that OTProof will achieve 100% precision or recall on operator inventories. Four positive labels are far too few for a field performance claim.", width),
        para("AI extraction", styles["h2"]),
        para("Local Ollama inference was not run. No advisory extraction accuracy, summary quality, or AI productivity benefit is claimed. Deterministic CISA HTML/CSAF parsing is covered by unit tests, but no independent multi-vendor extraction gold set has been labeled.", styles["body"]),
    ]
    case_rows = [["Asset", "Advisory", "Expected", "Observed", "Source linked"]]
    for case in metrics["cases"]:
        case_rows.append([
            case["asset_id"], case["advisory_id"], case["expected"].replace("_", " "),
            case["actual"].replace("_", " "), "Yes" if case["source_traceable"] else "No",
        ])
    cm = det["confusion_matrix"]
    conf_rows = [["Expected \\ Observed", "Applicable", "Not applicable", "Manual review"]]
    for expected in ["applicable", "not_applicable", "requires_manual_verification"]:
        conf_rows.append([
            expected.replace("_", " "),
            str(cm[expected]["applicable"]),
            str(cm[expected]["not_applicable"]),
            str(cm[expected]["requires_manual_verification"]),
        ])
    p2 = [
        para("CASE REGISTER", styles["eyebrow"]),
        para("All labeled examples and confusion counts", styles["title"]),
        para("The examples exercise exact affected product/version, outside-bound versions, a curated spelling alias, a similar but different product, missing/unsupported details, unknown model, stale inventory, and duplicate assets.", styles["deck"]),
        styled_table(case_rows, [width * .2, width * .22, width * .2, width * .2, width * .18], font_size=6.5),
        Spacer(1, 4 * mm),
        para("Three-class confusion matrix", styles["h2"]),
        styled_table(conf_rows, [width * .33, width * .21, width * .23, width * .23], font_size=7),
        Spacer(1, 3 * mm),
        callout_table("No semantic similarity model was used. Manual review is an intentional output for uncertain inventory and configuration cases.", width),
    ]
    timing = det["timing"]
    p3 = [
        para("TESTS, LIMITATIONS, AND NEXT EVALUATION", styles["eyebrow"]),
        para("Security and availability checks", styles["title"]),
        para("The test suite checks local software behavior and known edge cases. It does not certify the system or validate real OT outcomes.", styles["deck"]),
        para("Checks included", styles["h2"]),
        para("Prompt-injection-like instructions are retained as untrusted advisory content; the extraction adapter rejects unsupported source values and quotations. Duplicate inventory IDs and macro-enabled workbooks are rejected. A failed source refresh serves a persisted stale snapshot. Role tests cover unauthorized remediation approval/verification, and the workflow API test records a human applicability decision, ticket approval, simulated evidence, and approver verification.", styles["body"]),
        para("Performance scope", styles["h2"]),
        para(f"{timing['elapsed_ms']:.3f} ms elapsed for one in-process pass over {timing['full_cross_product_pairs']} pairs ({timing['milliseconds_per_pair']:.4f} ms/pair on this developer machine). The measurement excludes database queries, HTTP ingestion, browser rendering, concurrency, cold starts, and human review. Operator review time was not instrumented or measured.", styles["body"]),
        para("Limits", styles["h2"]),
        para("Small synthetic sample; three Rockwell CISA fixtures; no blinded ground truth; no live local model evaluation; no industrial vendor/model breadth study; no penetration test; no production load test; and no human time study. The test client emits a Starlette warning that the installed HTTPX integration is deprecated, though tests pass. Docker Compose could not be run because a daemon was unavailable.", styles["body"]),
        para("Next evaluation protocol", styles["h2"]),
        para("Recruit OT engineers from multiple operators; pre-label a larger, source-reviewed corpus across vendors and versions; blind reviewers to system decisions; adjudicate disagreements; report precision, recall, false-negative rate, abstention coverage, calibration only if statistically supported, source traceability, and review minutes. Run the deterministic baseline first. Evaluate the LLM separately against gold spans and exact field values. Test stale/offline feeds, large inventory imports, model-output injection, RBAC, and deployment security.", styles["body"]),
        callout_table("The current result is a build check, not a customer study, security certification, safety case, or verified reduction in operational risk.", width),
    ]
    build_narrative_pdf(ROOT / "OTProof_Evaluation_Report.pdf", "Evaluation Report", [p1, p2, p3])


def architecture_svg() -> None:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="920" viewBox="0 0 1440 920" role="img" aria-labelledby="title desc">
<title id="title">OTProof MVP architecture</title><desc id="desc">Passive architecture showing operator inventory and public sources entering an API and database, deterministic matcher and human workflow, and dashboard and report outputs. Optional local LLM is suggestion-only.</desc>
<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto"><path d="M1 1L10 6L1 11" fill="none" stroke="#25A99A" stroke-width="2"/></marker><style>text{font-family:Inter,Arial,sans-serif;fill:#18313A}.h{font-size:32px;font-weight:700}.sub{font-size:16px;fill:#63777C}.box{fill:#fff;stroke:#D4E2E0;stroke-width:2}.dark{fill:#1C3441;stroke:#1C3441}.teal{fill:#25A99A}.label{font-size:13px;font-weight:700;letter-spacing:1.5px;fill:#25A99A}.boxt{font-size:20px;font-weight:700}.small{font-size:15px;fill:#63777C}.darkt{fill:#fff;font-size:20px;font-weight:700}.darksmall{fill:#D0E0DF;font-size:15px}.line{stroke:#25A99A;stroke-width:3;fill:none;marker-end:url(#arrow)}.dash{stroke:#E08B62;stroke-width:2;stroke-dasharray:8 7;fill:none}</style></defs>
<rect width="1440" height="920" fill="#F3F7F6"/><rect x="0" y="0" width="1440" height="14" fill="#25A99A"/>
<text x="72" y="78" class="label">PASSIVE · SOURCE-TRACEABLE · HUMAN-APPROVED</text><text x="72" y="124" class="h">OTProof MVP Architecture</text><text x="72" y="158" class="sub">A modular monolith. No route or service reaches an OT device or network.</text>
<rect x="72" y="218" width="300" height="170" rx="18" class="box"/><text x="98" y="253" class="label">INPUTS</text><text x="98" y="292" class="boxt">Operator inventory</text><text x="98" y="324" class="small">CSV / XLSX · field validation</text><text x="98" y="352" class="small">Asset identity · version · owner</text>
<rect x="72" y="444" width="300" height="222" rx="18" class="box"/><text x="98" y="480" class="label">PUBLIC ADVISORIES</text><text x="98" y="520" class="boxt">CISA ICS / CSAF</text><text x="98" y="551" class="boxt">CISA KEV · NVD 2.0</text><text x="98" y="585" class="small">Approved vendor HTTPS sources</text><text x="98" y="615" class="small">Cache · timestamps · stale fallback</text>
<rect x="470" y="268" width="340" height="350" rx="20" class="dark"/><text x="502" y="309" class="label" fill="#8FC7BE">MODULAR API SERVICE</text><text x="502" y="358" class="darkt" fill="#FFFFFF">FastAPI + Pydantic</text><text x="502" y="394" class="darksmall" fill="#D0E0DF">Inventory &amp; advisory validation</text><text x="502" y="425" class="darksmall" fill="#D0E0DF">Source adapters and normalization</text><text x="502" y="456" class="darksmall" fill="#D0E0DF">RBAC · workflow · audit services</text><rect x="502" y="496" width="275" height="82" rx="12" fill="#25A99A"/><text x="522" y="531" class="darkt" fill="#FFFFFF">Deterministic matcher</text><text x="522" y="557" class="darksmall" fill="#D0E0DF">Identity + published constraints</text>
<rect x="910" y="218" width="265" height="170" rx="18" class="box"/><text x="938" y="253" class="label">PERSISTENCE</text><text x="938" y="294" class="boxt">PostgreSQL</text><text x="938" y="325" class="small">SQLAlchemy · Alembic</text><text x="938" y="353" class="small">SQLite for local demo</text>
<rect x="910" y="444" width="265" height="222" rx="18" class="box"/><text x="938" y="480" class="label">HUMAN WORKFLOW</text><text x="938" y="520" class="boxt">Review → ticket</text><text x="938" y="551" class="boxt">Evidence → verify</text><text x="938" y="585" class="small">Engineer · reviewer · approver</text><text x="938" y="615" class="small">Human action required to close</text>
<rect x="1250" y="300" width="120" height="285" rx="18" class="box"/><text x="1270" y="339" class="label">OUTPUT</text><text x="1270" y="388" class="boxt">React</text><text x="1270" y="419" class="small">Dashboard</text><text x="1270" y="460" class="boxt">JSON</text><text x="1270" y="491" class="small">PDF report</text><text x="1270" y="535" class="small">Audit trail</text>
<path d="M372 302H455" class="line"/><path d="M372 555H435Q455 555 455 535V475" class="line"/><path d="M810 344H895" class="line"/><path d="M810 512H895" class="line"/><path d="M1175 520H1235" class="line"/>
<rect x="484" y="704" width="690" height="115" rx="18" fill="#DDF3EF" stroke="#9CD8CE" stroke-width="2"/><text x="514" y="743" class="label">OPTIONAL · LOCAL ONLY</text><text x="514" y="779" class="boxt">Ollama-compatible LLM → schema-checked extraction / draft summary</text><text x="514" y="804" class="small">Suggestion only; no effect on applicability, approval, or remediation state.</text><path d="M645 704V635" class="dash"/>
<text x="72" y="870" class="small">Public source egress only · no scanning · no exploitation · no equipment modification</text>
</svg>'''
    (ROOT / "OTProof_Architecture.svg").write_text(svg, encoding="utf-8")


def update_measured_claims(metrics: dict) -> None:
    elapsed = metrics["deterministic_applicability"]["timing"]["elapsed_ms"]
    measured = f"{elapsed:.2f}"

    def replace(value):
        if isinstance(value, str):
            return value.replace("1.05", measured)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    for idx, page in enumerate(IDEA_PAGES):
        IDEA_PAGES[idx] = replace(page)
    for idx, slide in enumerate(SLIDES):
        SLIDES[idx] = replace(slide)


def main() -> None:
    metrics_path = ROOT / "reports/evaluation_metrics.json"
    if not metrics_path.exists():
        raise SystemExit("Run scripts/evaluate.py before generating measured submission documents.")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    update_measured_claims(metrics)
    idea_docx()
    idea_pdf()
    deck_pptx()
    deck_pdf()
    business_pdf(metrics)
    evaluation_pdf(metrics)
    architecture_svg()
    office_converter = shutil.which("soffice")
    if office_converter:
        with tempfile.TemporaryDirectory(prefix="otproof-office-", dir=ROOT / "reports") as tmp:
            converted = subprocess.run(
                [
                    office_converter,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmp,
                    str(ROOT / "OTProof_Idea_Document.docx"),
                    str(ROOT / "OTProof_Pitch_Deck.pptx"),
                ],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if converted.returncode == 0:
                for stem in ("OTProof_Idea_Document", "OTProof_Pitch_Deck"):
                    pdf = Path(tmp) / f"{stem}.pdf"
                    if pdf.exists():
                        shutil.copy2(pdf, ROOT / f"{stem}.pdf")
            else:
                print(f"Office PDF rendering failed; retained the ReportLab PDF mirrors: {converted.stderr.strip()}")
    print("Generated idea document, business/evaluation PDFs, 14-slide deck, and architecture SVG.")


if __name__ == "__main__":
    main()


