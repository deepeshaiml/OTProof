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
        "deck": "Check which public security notices may affect industrial equipment, then keep the human review and evidence together.",
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
        "title": "OTProof in plain language",
        "deck": "It connects an equipment list to public security notices. It points people to records worth checking; it does not touch equipment or make operational decisions.",
        "sections": [
            {
                "heading": "A simple example",
                "body": "A real CISA notice says FactoryTalk View Site Edition version 13.0 is affected. In our fictional water utility, asset CV-HMI-001 is version 13.0.0, so OTProof shows a possible match and links the notice. CV-HMI-002 is version 14.0, which is outside that notice's version statement. CV-HMI-005 has no recorded version, so OTProof asks an engineer to check. None of these results means equipment was changed or fixed.",
            },
            {
                "heading": "People make the important calls",
                "body": "A reviewer decides whether the notice fits the asset and records why. An engineer proposes any work and its timing. An approver accepts or rejects that plan. After work, the team adds evidence and an approver verifies it. AI can help read the notice, but it cannot make those decisions.",
            },
            {
                "heading": "Quick translations",
                "body": "OT means operational technology: computers and controllers that monitor or run physical processes such as water pumps. A vulnerability notice describes a software or product weakness. A CVE is the public ID assigned to a specific vulnerability. Evidence is a record that supports a human decision, such as a change reference or test result.",
            },
        ],
        "callout": "OTProof is a careful checklist and record keeper: it highlights what may need attention, while authorized people decide what to do.",
        "sources": ["Worked example source: CISA ICSA-24-226-06 · https://www.cisa.gov/news-events/ics-advisories/icsa-24-226-06"],
    },
    {
        "title": "The inventory and the security notice speak different languages",
        "deck": "A public vulnerability notice alone does not say which equipment at a particular site needs engineering attention.",
        "sections": [
            {
                "heading": "Three records that rarely line up cleanly",
                "body": "Operators track equipment names, models, software versions, locations, importance, and owners in spreadsheets and maintenance systems. Security notices may use different product names and list affected versions in a different format. Security and engineering teams have to compare the records and keep track of their reasoning.",
            },
            {
                "heading": "False certainty has a cost",
                "body": "A loose name match can create false alarms. Missing or old version details can hide a real concern. Before changing industrial equipment, the team must consider process impact, vendor guidance, maintenance schedules, and safety.",
            },
            {
                "heading": "Why now",
                "body": "NIST's final OT security guide recommends keeping accurate records of equipment, vendors, software versions, locations, and responsible roles. OTProof starts from a file the operator provides and does not connect to industrial equipment.",
                "source": "NIST SP 800-82 Rev. 3 final (2023-09-28): https://csrc.nist.gov/pubs/sp/800/82/r3/final",
            },
        ],
        "callout": "The product shows a possible match with its source. It does not decide whether a change is safe or whether work is complete.",
    },
    {
        "title": "From security notice to reviewed evidence",
        "deck": "Every finding preserves the records and decisions needed to explain what happened.",
        "sections": [
            {
                "heading": "1 · Load and validate inventory",
                "body": "Load an inventory spreadsheet with each asset's ID, maker, product/model, software version, type, site, importance, owner, and last check date. OTProof checks required fields and rejects duplicate IDs, very large uploads, and macro-enabled workbooks.",
            },
            {
                "heading": "2 · Import approved advisory data",
                "body": "Load public security notices from CISA, the CISA list of known exploited vulnerabilities, NIST's vulnerability database, or an approved vendor website. OTProof saves when and where each record came from so the team can check it later.",
            },
            {
                "heading": "3–6 · Compare, review, and assure",
                "body": "The comparison returns one of three results: likely affected, does not match this notice, or needs a human check. A reviewer records the decision and reason. An engineer proposes work, an approver reviews it, and later an approver checks the supporting evidence. Reports preserve the sources and action history.",
            },
        ],
        "callout": "A proposed fix or AI-written summary cannot count as proof that work is complete. An authorized person must check evidence.",
    },
    {
        "title": "How the application is built",
        "deck": "One maintainable service keeps source ingestion, comparison, workflow, and evidence close together.",
        "sections": [
            {
                "heading": "Built for the demo and a controlled pilot",
                "body": "A web dashboard sends requests to one service that validates data, applies matching rules, and records decisions in a database. The implementation uses React/TypeScript, FastAPI/Pydantic, and PostgreSQL; SQLite supports a quick local demo. ReportLab creates PDF reports, and Docker Compose packages the components.",
            },
            {
                "heading": "Public sources only",
                "body": "The source service uses documented public CISA and NIST feeds, CISA-linked advisory files, and approved vendor websites. It avoids unnecessary repeat downloads, retries temporary rate limits, and can use a saved older copy when a source is unavailable.",
            },
            {
                "heading": "What the system can and cannot do",
                "body": "There is no connection to industrial devices, no network scanner, no exploit tool, and no way to change equipment. The optional local AI helper can read notice text and draft fields, but it cannot decide whether a vulnerability applies or mark work complete.",
            },
        ],
        "callout": "Before a real operator uses it: add company login, protect and rotate secrets, limit internet access, test backup and restore, and complete an independent security review.",
    },
    {
        "title": "The matching rules show their work",
        "deck": "OTProof compares product identity and published version limits. If it cannot tell, it asks a person to check.",
        "sections": [
            {
                "heading": "Supported comparisons",
                "body": "A small reviewed list handles known spelling variations. The product name must match, then the installed version is compared with the affected version or range stated by the publisher. Every required condition must match; separate affected products are checked as separate possibilities.",
            },
            {
                "heading": "Abstain when evidence is incomplete",
                "body": "Missing software version, unknown model, a possible duplicate asset, inventory older than 180 days, unfamiliar version format, unclear product identity, or complicated source conditions all require an engineering review. A similar-sounding name is never enough to call a vulnerability applicable.",
            },
            {
                "heading": "AI assists with reading, not deciding",
                "body": "An optional AI model running on the user's computer can suggest product, version, vulnerability ID, mitigation, and summary fields. Required fields are checked and quoted details are compared with the original notice. The AI suggestion does not affect the matching result or workflow status.",
            },
        ],
        "callout": "No AI model was run during evaluation. Its accuracy has not been measured; a person must check every suggestion.",
    },
    {
        "title": "People review work and verify evidence",
        "deck": "Separate technical applicability, remediation planning, approval, and evidence verification.",
        "sections": [
            {
                "heading": "Role-gated lifecycle",
                "body": "The reviewer checks whether the notice applies and records the reason. The engineer proposes a safe action, an owner, and a due date. A different person approves or rejects the plan. After the work, the team adds a change or test record; an approver checks it and records why it is sufficient.",
            },
            {
                "heading": "Audit and exports",
                "body": "The system records who did what and when. The report includes the source publication and update dates, matching reasons, human decisions, work status, evidence references, and action history. Evidence records include a digital fingerprint so later changes can be detected when compared with the original.",
            },
            {
                "heading": "What the MVP does not claim",
                "body": "The demo passwords are visible and unsafe for real use. A database administrator could change stored audit records. Evidence is a text record or reference, not an uploaded file. OTProof does not certify compliance or prove that operational risk was reduced.",
            },
        ],
        "callout": "Demo evidence is fictional. Marking it verified changes the demo record only; it does not prove a real plant change occurred.",
    },
    {
        "title": "Potential customers and business model",
        "deck": "Potential users span operators, contractors, and service providers with different inventory systems.",
        "sections": [
            {
                "heading": "Interview targets",
                "body": "Water and wastewater utilities; energy operators; oil and gas infrastructure; industrial maintenance contractors; managed OT security service providers; and defense-support facilities. Likely champions are OT security leads, plant engineering managers, asset owners, CISOs, and service-practice owners.",
            },
            {
                "heading": "Competitive landscape",
                "body": "Claroty, Tenable, and Nozomi publicly describe broad industrial equipment visibility, vulnerability management, monitoring, and remediation workflows. ServiceNow and similar risk and compliance systems manage controls, audits, and work records. OTProof may offer a local, source-linked review workflow that complements them; this is a hypothesis, not a proven advantage. Better evidence handover may help audit preparation, but compliance outcomes and risk reduction have not been measured.",
            },
            {
                "heading": "Illustrative annual revenue model",
                "body": "For illustration only, assume 3 sites per customer at $36,000 per site each year, $25,000 one-time setup for each new customer, and assumed profit margins of 78% on software and 40% on setup services. These are arithmetic examples, not sales, market size, or a forecast.",
                "table": [
                    ["Customers", "Sites", "Recurring ARR", "Year-1 revenue", "Year-1 gross profit"],
                    ["1", "3", "$108k", "$133k", "$94k"],
                    ["5", "15", "$540k", "$665k", "$471k"],
                    ["10", "30", "$1.08m", "$1.33m", "$942k"],
                    ["25", "75", "$2.70m", "$3.33m", "$2.36m"],
                ],
            },
        ],
        "callout": "ARR means yearly subscription income. Gross margin is the share left after direct delivery costs; gross profit is that amount in dollars. Prices and margins need buyer interviews and cost validation.",
    },
    {
        "title": "Measured MVP, open questions, and the next proof points",
        "deck": "The first test is repeatable behavior against labeled edge cases—not a broad product claim.",
        "sections": [
            {
                "heading": "Fixture baseline (26 Oct 2026)",
                "body": "The test set has 14 hand-labeled asset/notice examples: 4 likely affected, 4 outside the published affected details, and 6 that should go to human review. The matcher returned the expected result on all 14. It found all 4 affected examples and missed none in this small test set. It also sent all 6 uncertain examples to review. Each result kept the source ID, link, and relevant source text.",
            },
            {
                "heading": "Performance and security checks",
                "body": "A single local software-only run compared 80 fictional assets with 3 notices (240 comparisons) in about 1.05 ms. This does not include internet, database, or human review time. Tests cover unavailable sources, duplicate IDs, unsafe spreadsheets, unsupported AI claims, role permissions, and evidence review.",
            },
            {
                "heading": "Roadmap and pilot ask",
                "body": "Next, invite 3–5 operators and service providers to test the workflow. Ask engineers to label examples before seeing OTProof's results, then compare disagreements. Measure missed cases, human-review cases, time per review, and setup effort across several vendors. Add company login, protected audit export, and maintenance/risk-system connections only after users confirm the need. Ask a water or energy operator and its engineers to join this evaluation.",
            },
        ],
        "callout": "Not measured yet: operator accuracy, human review time, AI quality, savings, or production performance.",
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
        "subtitle": "Check which public security notices may affect industrial equipment, then keep the human review and evidence together.",
        "bullets": [
            "Compare the equipment list with public industrial security notices",
            "Show what matched, what did not, and what is unknown",
            "People decide and approve any work",
        ],
        "metric": "READ-ONLY",
        "metric_label": "No contact with industrial equipment",
        "right_items": ["80 fictional assets", "3 real CISA advisories", "Offline-ready demo"],
        "kind": "cover",
        "source": "Eureka Hackathon · MVP snapshot 26 Oct 2026",
        "notes": "Introduce OTProof as a record-checking tool for industrial security work. An operator provides an equipment spreadsheet, and OTProof compares it with public security notices. The screen shows what appears to match, which source it used, and when a person should check missing or unclear details. Engineers and approvers make the consequential decisions. The equipment in the demo is fictional; the CISA notices are real. The application never scans, exploits, queries, or changes industrial equipment. This pitch asks whether operators need a focused review tool alongside the security and audit products they already use.",
    },
    {
        "title": "Why matching is harder than it looks",
        "subtitle": "The security notice and the equipment list often describe the same product in different ways.",
        "bullets": [
            "Inventory identifiers and advisory product language often differ",
            "A version match can be exact, excluded, or impossible to confirm",
            "Teams must preserve the source and explain what they decided",
        ],
        "metric": "3 RECORDS",
        "metric_label": "Inventory · advisory · remediation evidence",
        "right_items": ["Asset inventory", "Public advisory", "Engineering record"],
        "source": "NIST SP 800-82 Rev. 3 final · https://csrc.nist.gov/pubs/sp/800/82/r3/final",
        "notes": "The challenge is connecting one installed asset to one public notice and keeping the reason for the decision. The equipment list may be old, spell the maker differently, or omit the software version. The notice may describe the same product family with different wording. A loose name match creates false alarms; missing version details make a confident conclusion impossible. NIST, the U.S. National Institute of Standards and Technology, recommends accurate equipment records in its published OT security guide, Revision 3. OTProof starts from the operator's existing files and leaves the industrial network alone.",
    },
    {
        "title": "Essential services need careful decisions",
        "subtitle": "Industrial control technology helps run water, energy, and other services, so changes need engineering review.",
        "bullets": [
            "A vulnerability label alone does not prove local applicability",
            "A patch suggestion is not an approved operational change",
            "Human review and source traceability belong in the workflow",
        ],
        "metric": "NO DEVICE",
        "metric_label": "Discovery or configuration change",
        "right_items": ["Operator's inventory file", "Approved public websites", "Human-led review"],
        "source": "NIST SP 800-82 Rev. 3 final; Rev. 4 remains an initial public draft as of 26 Oct 2026.",
        "notes": "Water, power, and other essential services depend on equipment that must keep running reliably and safely. A public notice does not automatically mean a local device should be patched. OTProof does not discover equipment, send network queries, or change controllers, gateway computers, operator screens, or supervisory systems. The operator supplies the equipment list, and OTProof retrieves public notices. NIST's Revision 3 is the published final OT guide. Revision 4 is a draft, so this project does not describe it as final. Authorized staff decide what applies, what work is safe, and whether evidence is sufficient.",
    },
    {
        "title": "From import to report: six clear steps",
        "subtitle": "Follow the notice, compare the equipment, record the people’s decisions, and save the evidence.",
        "bullets": [
            "Check the equipment file and load public security notices",
            "Compare maker, product, model, and installed version",
            "Record decisions, work approval, and supporting evidence",
        ],
        "metric": "6 STEPS",
        "metric_label": "Import → compare → review → plan → evidence → verify",
        "right_items": ["Sources shown", "People approve", "Reports downloadable"],
        "kind": "workflow",
        "source": "End-to-end journey is implemented in the MVP dashboard and API.",
        "notes": "Walk through the six steps. First, load an equipment spreadsheet and check its required fields. Second, load a public notice from CISA or NIST, or an approved vendor website; the fixed demo examples work without internet access. Third, compare maker, product, model, and version details and open the source link. Fourth, a reviewer records whether the notice fits and explains why. Fifth, an engineer proposes a work plan and a separate approver accepts or rejects it. Sixth, the team attaches a change or test record and an approver checks it. The report saves this history. A generated summary or attached note cannot close the finding by itself.",
    },
    {
        "title": "Demo: three assets, three distinct outcomes",
        "subtitle": "A CISA FactoryTalk View advisory exposes why version and inventory quality matter.",
        "bullets": [
            "FactoryTalk View SE 13.0.0 → possible match",
            "FactoryTalk View SE 14.0 → outside the exact affected version",
            "Same product with missing firmware → engineering review",
        ],
        "metric": "ICSA-24-226-06",
        "metric_label": "CISA notice · published 13 Aug 2024 · updated 29 Aug 2024",
        "right_items": ["CVE-2024-7513", "Source statement: version 13.0", "Source URL retained"],
        "source": "https://www.cisa.gov/news-events/ics-advisories/icsa-24-226-06",
        "notes": "Use the three fictional assets to explain the outcomes. CV-HMI-001 lists FactoryTalk View Site Edition version 13.0.0. The CISA notice names version 13.0, so OTProof shows a possible match and links the original notice. CV-HMI-002 lists version 14.0, which is outside that exact statement. CV-HMI-005 does not list a version, so OTProof asks an engineer to check instead of guessing. The notice is real, and its publication and update dates are retained. The utility, assets, and work records are fictional. A possible match is a screening result, not an engineering decision or a claim that a device is vulnerable in practice.",
    },
    {
        "title": "No unsupported guesses: show the matching rules",
        "subtitle": "Compare exact product and version details. If the records are incomplete, ask a person to check.",
        "bullets": [
            "Correct only known spelling variations",
            "Compare the installed version with the notice’s affected version or range",
            "Send missing, old, duplicate, or unclear records to human review",
        ],
        "metric": "3 OUTCOMES",
        "metric_label": "Applicable · not applicable · manual verification",
        "right_items": ["Product names match", "Version fits the notice", "Reason and source link shown"],
        "source": "Matcher implementation: backend/app/services/matching.py",
        "notes": "The matching rules are designed to avoid guesses. OTProof recognizes only a small, reviewed list of spelling variations. It then compares the inventory version with the version or range printed in the notice. It does not decide from a similar-sounding product name. If the version is missing, the inventory is old, two records may describe the same device, or the source uses a format the software cannot read, the result goes to an engineer. Every result keeps the values and source text used to reach it. The current product and model list is narrow and needs testing with more operators and equipment families.",
    },
    {
        "title": "AI can read; people make the decisions",
        "subtitle": "An optional local AI helper suggests details from a notice. It cannot decide whether equipment is affected.",
        "bullets": [
            "Suggest product, version, vulnerability ID, and mitigation details",
            "Check suggested quotes and details against the original notice",
            "Never let AI approve work or mark equipment fixed",
        ],
        "metric": "OPTIONAL",
        "metric_label": "Optional local AI · not run in evaluation",
        "right_items": ["Required fields checked", "Source details compared", "Suggestion only"],
        "source": "Optional local model; no model weights included and no inference run in evaluation.",
        "notes": "AI is optional and helps with reading, not deciding. A local model can suggest product names, versions, vulnerability IDs, mitigations, and a short summary from a notice. The output has required fields, and quoted details are checked against the original text. This catches some unsupported claims, but it cannot prove that a summary is complete or correct. The application labels AI text as a suggestion and never lets it set applicability, approve a work plan, or close a finding. No model was installed or run for this evaluation, so AI quality has not been measured. A later test should compare its suggestions with source excerpts labeled by engineers.",
    },
    {
        "title": "How the software is put together",
        "subtitle": "A web page, one service, and a database keep the process simple to inspect and run.",
        "bullets": [
            "Web dashboard and a service that checks and compares records",
            "Database for decisions; PDF and JSON reports for handoff",
            "Optional AI helper runs locally and only drafts suggestions",
        ],
        "metric": "NO OT PATH",
        "metric_label": "The service has no device scanner or connection",
        "right_items": ["Inventory / sources", "API + database", "Review / reports"],
        "kind": "architecture",
        "source": "Full technical design: OTProof_Technical_Design.md",
        "notes": "Explain the drawing from left to right. The operator supplies an equipment spreadsheet, and the application retrieves public notices. One service checks the inputs, compares product and version details, and saves each result in a database. The dashboard shows the results; a report carries the source and human decisions. The implementation uses React for the web screen, FastAPI for the service, and PostgreSQL or SQLite for saved records. These are implementation choices, not a production certification. Docker packaging is included, but the Docker service was unavailable here, so a container startup was not verified. There is no connection to an industrial network.",
    },
    {
        "title": "People own every decision",
        "subtitle": "A review, a work plan, approval, and proof of completed work are separate steps.",
        "bullets": [
            "Reviewer records applicability with a rationale",
            "Engineer proposes action; approver accepts or rejects",
            "Approver verifies evidence before the workflow closes",
        ],
        "metric": "4 ROLES",
        "metric_label": "Engineer · reviewer · approver · admin",
        "right_items": ["Decision", "Ticket", "Evidence", "Verification"],
        "source": "Demo passwords are visible; company login is needed before real use.",
        "notes": "Show that the people do different jobs. The reviewer records whether the notice fits the equipment and why. The engineer proposes a plan; an approver accepts or rejects it. After work, the engineer adds a record or reference, and an approver checks that evidence. The application saves who did what and when. It also calculates a digital fingerprint from evidence text so a later copy can be compared. A fingerprint does not prove the original record is true or prevent a database administrator from changing it. Demo passwords are visible and only for this fictional demo. Real use needs company login and protected records.",
    },
    {
        "title": "Where OTProof could fit",
        "subtitle": "Existing security platforms may already help. OTProof’s possible role is a focused review and evidence workflow.",
        "bullets": [
            "OT security platforms offer asset visibility and vulnerability management",
            "Risk and compliance tools track controls, reviews, and audit records",
            "Test whether this focused workflow fills a real gap or connects to them",
        ],
        "metric": "HYPOTHESIS",
        "metric_label": "Focused assurance is not yet a proven advantage",
        "right_items": ["OT security platforms", "Risk / audit tools", "Possible connection point"],
        "kind": "competition",
        "source": "Claroty · Tenable · Nozomi · ServiceNow public product documentation; see notes.",
        "notes": "Existing products may already cover this need. Claroty, Tenable, and Nozomi publicly describe broader industrial security products that include equipment inventory and vulnerability management. ServiceNow and other governance, risk, and compliance tools track organizational reviews, controls, and audit work. OTProof has not been compared head-to-head and has not proved an advantage. The idea to test is whether a small, file-based workflow that keeps source links and engineering decisions together helps a team that does not want another broad platform. Interviews and integration tests with operators should decide whether it fills a real gap. The full product references are listed in the research notes.",
    },
    {
        "title": "A possible per-site subscription model",
        "subtitle": "The example prices below are assumptions to test with buyers, not sales or a forecast.",
        "bullets": [
            "Example annual license: $36,000 per site",
            "Example one-time setup: $25,000 per new customer",
            "Other options: enterprise plans, integrations, and review services",
        ],
        "metric": "$2.70M",
        "metric_label": "Example annual subscription income at 25 customers × 3 sites",
        "right_items": ["1 customer · $108k / year", "5 customers · $540k / year", "10 customers · $1.08m / year", "25 customers · $2.70m / year"],
        "kind": "business",
        "source": "Illustrative arithmetic only; assumptions in OTProof_Business_Case.pdf.",
        "notes": "These prices are examples to discuss with buyers, not signed orders or a forecast. The model assumes three sites for each customer, a $36,000 annual subscription for each site, and $25,000 one-time setup for each new customer. Annual recurring revenue means the value of subscriptions over a year. Gross margin means the share left after direct costs to deliver the software or setup service. The 25-customer example covers 75 sites and totals $2.70 million in annual subscription income before costs. Sales, hosting, support, data setup, and integration costs are not known yet. Validate prices and costs with operators before making a business forecast.",
    },
    {
        "title": "What the test shows—and what it does not",
        "subtitle": "The software matched this small set of prepared examples; the result does not predict field accuracy.",
        "bullets": [
            "All 14 labeled test cases matched their expected outcome",
            "All 4 affected examples were found; none were missed in this set",
            "All 6 uncertain examples went to human review; all results link to sources",
        ],
        "metric": "~1.05 ms",
        "metric_label": "One software-only run over 240 comparisons",
        "right_items": ["80 fictional assets", "3 advisory fixtures", "LLM extraction not run"],
        "kind": "validation",
        "source": "reports/evaluation_metrics.json · run dated 26 Oct 2026",
        "notes": "This test uses only 14 prepared examples: four that should match, four that should not match, and six that lack enough information and should go to review. OTProof returned the expected outcome for all 14. It found all four matching examples and missed none in this small test. These counts do not predict how it will perform on equipment it has never seen. The reported time is one software-only pass over 240 combinations on the development computer; it excludes the database, internet, and people. The AI model was not run, and no review-time or savings study was done.",
    },
    {
        "title": "Safety and trust boundaries",
        "subtitle": "The app reads files and public notices. It never contacts or changes industrial equipment.",
        "bullets": [
            "No device scan, remote query, exploit, or configuration change",
            "Uploaded files and notice text are treated as untrusted input",
            "People approve work and check evidence before closing a finding",
        ],
        "metric": "HUMAN",
        "metric_label": "Owns applicability and remediation decisions",
        "right_items": ["Public sources only", "Evidence and action history", "Company login needed for real use"],
        "source": "Security review, company login, and protected action records remain future work.",
        "notes": "Restate the safety rules clearly. OTProof reads the spreadsheet an operator uploads and public web pages. It does not send requests to equipment or install fixes. Uploaded spreadsheets and notice text are treated as untrusted; embedded instructions cannot tell the AI or application what to do. Only the right human role can record a review, approve a plan, or verify evidence. Still, the demo login is not safe for production, and a database administrator could alter stored history. These tests are not an independent security assessment. Before a real pilot, add company login, plan how records will be protected, review likely attack paths, test backups, and get operator approval.",
    },
    {
        "title": "Next: test with operators and engineers",
        "subtitle": "The next step is to learn whether this helps real teams and fits their existing process.",
        "bullets": [
            "Invite 3–5 operators or service providers to try a controlled pilot",
            "Ask engineers to label cases before seeing the software’s result",
            "Measure missed cases, human-review rate, time, and setup effort",
        ],
        "metric": "PILOT ASK",
        "metric_label": "Water / energy operator + OT engineering reviewers",
        "right_items": ["Add more vendors and sources", "Add company sign-in and protected audit records", "Connect to maintenance and risk systems if users need it"],
        "source": "No customer interviews, paid pilots, or measured savings are claimed yet.",
        "notes": "Close by asking a water or energy operator and its engineers to review a controlled pilot using approved sample inventory. Include several vendors and equipment families. Ask engineers to label whether each notice applies before showing them OTProof's results, then compare any disagreements. Measure how often OTProof finds a relevant affected product, how often it misses one, how often it asks for human review, how long each review takes, and the effort needed to prepare the data. Later work could add company sign-in, stronger protection for action records, and connections to maintenance or risk tools. No customers, savings, or risk reduction are claimed today; the pilot should test those ideas.",
    },
    {
        "title": "Plain-language glossary",
        "subtitle": "A quick translation of the terms used in this presentation.",
        "bullets": [
            "Asset: a device or software record in the operator’s equipment list",
            "Advisory: a public security notice about a product weakness",
            "Candidate match: a possible link that still needs an engineer’s review",
            "Evidence: a record that supports a human decision",
        ],
        "metric": "KEY TERMS",
        "metric_label": "Read the source and inventory record together",
        "right_items": [
            "OT · computers and controllers for physical processes",
            "CISA · U.S. Cybersecurity and Infrastructure Security Agency",
            "CVE · public ID assigned to a specific vulnerability",
            "KEV · CISA list of vulnerabilities known to be exploited",
        ],
        "source": "More terms and examples: README.md and OTProof_Technical_Design.md",
        "notes": "Use this glossary whenever a term is unfamiliar. Operational technology, or OT, means computers and controllers used to monitor or control physical processes such as water pumping or electricity generation. CISA is the US Cybersecurity and Infrastructure Security Agency, which publishes the advisories used in the demo. CVE is the public identifier assigned to a specific vulnerability. CISA KEV is a public list of vulnerabilities CISA knows have been exploited. A candidate match is a possible link produced by comparing records; it is not an engineering decision. Evidence is a work record, test result, or other reference that supports a human decision. Annual recurring revenue means the yearly value of recurring subscriptions, not profit or guaranteed sales.",
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
        canvas.drawRightString(w - 15 * mm, 8 * mm, f"{doc.page:02d}  /  {len(IDEA_PAGES):02d}")
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
        labels = ["INVENTORY + NOTICES", "CHECK + SAVE", "MATCH + REVIEW", "DASHBOARD + REPORT"]
        for i, label in enumerate(labels):
            bx = x + .42 + (i % 2) * 2.25
            by = y + .92 + (i // 2) * 1.35
            ppt_box(slide, bx, by, 1.88, .72, "2C4955")
            make_ppt_text(slide, bx + .12, by + .19, 1.64, .36, label, size=9, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        for ax, ay, bx, by in [(x + 2.3, y + 1.28, x + 2.86, y + 1.28), (x + 2.3, y + 2.63, x + 2.86, y + 2.63)]:
            connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, PptInches(ax), PptInches(ay), PptInches(bx), PptInches(by))
            connector.line.color.rgb = PPTColor.from_string(TEAL)
            connector.line.width = PptPt(2)
        make_ppt_text(slide, x + .55, y + 3.83, w - 1.1, .46, "OPTIONAL LOCAL AI · suggestion only", size=10, color="C4DBD8", align=PP_ALIGN.CENTER)
    elif kind == "workflow":
        steps = ["IMPORT", "MATCH", "REVIEW", "PLAN", "EVIDENCE", "VERIFY"]
        for i, label in enumerate(steps):
            cy = y + .85 + i * .56
            ppt_box(slide, x + .4, cy, .48, .42, TEAL)
            make_ppt_text(slide, x + .4, cy + .08, .48, .25, str(i + 1), size=11, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
            make_ppt_text(slide, x + 1.1, cy + .08, 3.6, .25, label, size=11, color=WHITE, bold=True)
    elif kind == "competition":
        labels = ["CLAROTY", "TENABLE", "NOZOMI", "RISK / AUDIT"]
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
        metric_cards = [("14/14", "tests passed"), ("4/4", "affected cases found"), ("6/6", "sent to review"), ("14/14", "sources linked")]
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
                labels = ["INVENTORY + NOTICES", "CHECK + SAVE", "MATCH + REVIEW", "DASHBOARD + REPORT"]
                for i, label in enumerate(labels):
                    bx = x + (.42 + (i % 2) * 2.25) * 72
                    by = y + (3.0 - (i // 2) * 1.35) * 72
                    c.setFillColor(hex_color("2C4955"))
                    c.roundRect(bx, by, 1.88 * 72, .72 * 72, 5, fill=1, stroke=0)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 8)
                    c.drawCentredString(bx + .94 * 72, by + .29 * 72, label)
                wrap_canvas_text(c, "OPTIONAL LOCAL AI / suggestion only", x + .5 * 72, y + .48 * 72, w - 1 * 72, size=8.5, leading=10, color="C4DBD8")
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
                cards = [("14/14", "tests passed"), ("4/4", "affected cases found"), ("6/6", "sent to review"), ("14/14", "sources linked")]
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
                labels = ["CLAROTY", "TENABLE", "NOZOMI", "RISK / AUDIT"]
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
        para("BUSINESS MODEL TO TEST", styles["eyebrow"]),
        para("Could focused review software help industrial operators?", styles["title"]),
        para("Potential users span small operators, contractors, and managed OT security providers. This is a customer discovery plan, not a market-size estimate.", styles["deck"]),
        para("Who may buy or champion", styles["h2"]),
        para("Municipal water and wastewater utilities; power and energy operators; oil and gas infrastructure; industrial maintenance contractors; managed OT security providers; and defense-support facilities. Likely champions include an OT security lead, plant engineering manager, asset owner, CISO, or managed-service practice owner.", styles["body"]),
        para("Position relative to existing products", styles["h2"]),
        para("Public product pages describe established industrial security platforms and risk, compliance, and audit tools. OTProof is not positioned as a proven replacement. Its hypothesis is a small source-linked review workflow that may connect equipment records with existing security, maintenance, and audit systems.", styles["body"]),
    ]
    competitor_rows = [
        ["Category", "Publicly described capability", "OTProof implication"],
        ["Claroty", "Industrial equipment inventory, security risk management, network protection, secure access, and threat detection.", "Competes for broad industrial security budgets; possible data/workflow integration."],
        ["Tenable", "Industrial equipment inventory, risk prioritization, remediation guidance, integrations, and compliance reporting.", "Broad incumbent; MVP has no coverage or accuracy advantage claim."],
        ["Nozomi", "Asset discovery, firmware details, vulnerability assessment, network visibility.", "Potential integration target; no comparative test run."],
        ["Risk / audit tools", "Risk assessment, controls, compliance, and audit workflow, e.g. ServiceNow.", "Potential downstream record system; integration is future work."],
    ]
    p1.extend([styled_table(competitor_rows, [width * .15, width * .47, width * .38], font_size=7), Spacer(1, 3 * mm)])
    p1.extend([
        para("The idea to test", styles["h2"]),
        para("The product idea is to put exact equipment/notice evidence, careful handling of missing information, and a record of human decisions in one focused workflow. Existing products may already solve the problem. Interviews and integration trials must show whether an additional tool helps.", styles["body"]),
        callout_table("Evidence to test: product coverage, agreement with engineer decisions, missed affected assets, quality of cases sent to review, review minutes, setup effort, integration demand, willingness to pay, and renewal interest.", width),
    ])

    scenarios = [
        ["Customers", "Sites", "Recurring ARR", "Year-1 revenue", "Year-1 gross profit"],
        ["1", "3", "$108,000", "$133,000", "$94,240"],
        ["5", "15", "$540,000", "$665,000", "$471,200"],
        ["10", "30", "$1,080,000", "$1,330,000", "$942,400"],
        ["25", "75", "$2,700,000", "$3,325,000", "$2,356,000"],
    ]
    p2 = [
        para("EXAMPLE PRICES AND COSTS", styles["eyebrow"]),
        para("A possible site subscription and setup fee", styles["title"]),
        para("A transparent first model makes the assumptions easy to challenge before a commercial forecast is attempted.", styles["deck"]),
        para("Scenario inputs", styles["h2"]),
        para("Assumptions: 3 licensed sites per customer; $36,000 annual license per site; and $25,000 one-time setup per new customer. Annual recurring revenue (ARR) is the yearly subscription income. Gross margin is the share left after direct delivery costs; the example assumes 78% for software and 40% for setup services. First-year revenue adds the subscription and setup income. Estimated gross profit applies those margins to each income source.", styles["body"]),
        styled_table(scenarios, [width * .12, width * .1, width * .22, width * .25, width * .31], font_size=7.5),
        Spacer(1, 3 * mm),
        callout_table("Illustrative arithmetic only. The scenarios are not customer commitments, an addressable-market calculation, bookings, or a revenue forecast. No revenue has been generated by this MVP.", width),
        para("Potential contract structure", styles["h2"]),
        para("Possible contracts include a yearly site subscription, a multi-site enterprise plan, setup and connection fees, and optional ongoing review services. Some operators may prefer software installed inside their own environment to protect sensitive equipment lists. Each option needs cost and procurement validation.", styles["body"]),
    ]
    labor_hours = 80 * 12 * (0.5 - 0.25)
    labor_savings = labor_hours * 80
    p2.extend([
        para("Illustrative labor sensitivity, not measured savings", styles["h2"]),
        para(f"Assume 80 assets, 12 relevant equipment/notice pairs per year, and a reduction in the initial review from 30 to 15 minutes per pair. That yields {labor_hours:.0f} theoretical hours, or ${labor_savings:,.0f} at an assumed $80 staff cost per hour. This excludes engineering work after review and assumes every pair realizes the time reduction. The MVP has no human time study, so this is not measured savings.", styles["body"]),
    ])

    p3 = [
        para("FINDING CUSTOMERS AND TESTING VALUE", styles["eyebrow"]),
        para("Sell a measurable workflow improvement, not an AI promise", styles["title"]),
        para("A controlled design-partner pilot should prove that the tool fits plant roles, records, and approval practices before product expansion.", styles["deck"]),
        para("Commercial route", styles["h2"]),
        para("Begin with 3–5 pilot partners from water, energy, industrial maintenance, or managed OT security. Offer a local installation or isolated IT setup for approved sample inventories. Start with spreadsheets, then connect to a maintenance or risk-management system only if pilot users show a recurring need. Sell setup as help preparing inventory records and configuring the workflow, not as automatic risk removal.", styles["body"]),
        para("Customer value to measure", styles["h2"]),
        para("Measure review minutes per equipment/notice pair, data gaps found, agreement with engineers, cases where an affected asset was missed, cases sent to human review, evidence completeness, time to export an audit package, setup hours, and continued use after the pilot. Potential benefits include less repeated source lookup, clearer audit evidence, and earlier engineering assessment. Those benefits remain hypotheses until measured; OTProof does not itself establish compliance or reduce operational risk.", styles["body"]),
        para("Key risks and response", styles["h2"]),
        para("Weak inventory quality can limit results; expose stale/missing data and assign owners. Advisory parsing can miss vendor nuance; preserve source excerpts and abstain. Established products may duplicate capabilities; position as complement and integrate. Sensitive asset information limits cloud adoption; test local deployment. Human review still costs time; quantify actual time saved and false-positive burden. Buyers may reject price; test paid pilots and renewal intent.", styles["body"]),
        para("Sources and market context", styles["h2"]),
        para("Competitor summaries are based on public vendor pages, not independent product tests: Claroty (claroty.com/platform), Tenable (tenable.com/products/ot-security), Nozomi (technicaldocs.nozominetworks.com/guardian), and ServiceNow risk tools (servicenow.com/docs). Full links are in docs/RESEARCH_NOTES.md. Pricing, margins, customer conversion, and savings assumptions are illustrative.", styles["body"]),
        callout_table("Before expanding: confirm that engineers agree with results across several vendors, uncertain cases are sent to review, local deployment is acceptable, sources are traceable, review time improves, and buyers are willing to pay.", width),
    ]
    build_narrative_pdf(ROOT / "OTProof_Business_Case.pdf", "Business Case", [p1, p2, p3])


def evaluation_pdf(metrics: dict) -> None:
    styles = pdf_styles()
    width = A4[0] - 28 * mm
    det = metrics["deterministic_applicability"]
    data = metrics["dataset"]
    true_affected = det["confusion_matrix"]["applicable"]["applicable"]
    expected_affected = data["labels"]["applicable"]
    traceable_count = det["source_traceability"]["pairs_with_advisory_id_url_and_excerpt"]
    total_labeled = det["source_traceability"]["pairs_total"]
    p1 = [
        para("SMALL PREPARED TEST SET · 26 OCT 2026", styles["eyebrow"]),
        para("A small rule-based test, measured honestly", styles["title"]),
        para("The evaluation checks whether the software returns the outcomes prepared in advance for these examples. It does not estimate real-world accuracy.", styles["deck"]),
        para("Test setup and results", styles["h2"]),
        para(f"The test compares {data['assets']} fictional equipment records with {data['advisories']} real CISA notices ({data['full_cross_product_pairs_benchmarked']} software-only comparisons). Fourteen asset/notice examples were labeled ahead of time: 4 likely affected, 4 outside the notice conditions, and 6 that need a human check.", styles["body"]),
        styled_table([
            ["Measure", "Result", "Scope"],
            ["Prepared examples with expected result", f"{sum(case['correct'] for case in metrics['cases'])} of {data['labeled_pairs']}", "Hand-labeled synthetic examples"],
            ["Affected examples correctly flagged", f"{true_affected} of {expected_affected}", "Only four in this small test"],
            ["Missed affected examples", f"{expected_affected - true_affected} of {expected_affected}", "In this fixture only"],
            ["Uncertain examples sent to review", f"{det['uncertainty']['manual_review_cases_abstained_correctly']}/{det['uncertainty']['manual_review_cases_expected']}", "Missing/old/unclear records"],
            ["Results with source ID, link, and excerpt", f"{traceable_count} of {total_labeled}", "All labeled examples"],
            ["Time for software-only comparison", f"{det['timing']['elapsed_ms']:.2f} ms total", "One pass over 240 pairs"],
        ], [width * .32, width * .22, width * .46]),
        para("How to read this: an affected example is a case labeled in advance as matching the notice. “Sent to review” means the software lacked enough support to give a firm result, so a person must check. A missed affected example is a false negative. These counts describe only the prepared test cases.", styles["small"]),
        Spacer(1, 3 * mm),
        callout_table("Interpretation: these results show that OTProof passed this small, prepared test set. Four affected examples are far too few to predict how it will perform on a real operator's equipment list.", width),
        para("AI suggestions", styles["h2"]),
        para("No local AI model was run. Its ability to extract details or summarize notices has not been measured. The public-notice importer has software tests, but no diverse set of notices has been labeled by experts for comparison.", styles["body"]),
    ]
    case_rows = [["Asset", "Advisory", "Expected", "Observed", "Source linked"]]
    for case in metrics["cases"]:
        case_rows.append([
            case["asset_id"], case["advisory_id"], case["expected"].replace("_", " "),
            case["actual"].replace("_", " "), "Yes" if case["source_traceable"] else "No",
        ])
    cm = det["confusion_matrix"]
    conf_rows = [["Expected \\ Actual", "Likely affected", "Outside notice", "Human review"]]
    for expected in ["applicable", "not_applicable", "requires_manual_verification"]:
        conf_rows.append([
            expected.replace("_", " "),
            str(cm[expected]["applicable"]),
            str(cm[expected]["not_applicable"]),
            str(cm[expected]["requires_manual_verification"]),
        ])
    p2 = [
        para("EXAMPLE REGISTER", styles["eyebrow"]),
        para("The test cases and what OTProof returned", styles["title"]),
        para("The examples cover exact and outside version matches, spelling differences, a similar but different product, missing details, unknown model, old inventory, and duplicate assets. The table compares the expected result with OTProof's observed result.", styles["deck"]),
        styled_table(case_rows, [width * .2, width * .22, width * .2, width * .2, width * .18], font_size=6.5),
        Spacer(1, 4 * mm),
        para("Expected results compared with actual results", styles["h2"]),
        styled_table(conf_rows, [width * .33, width * .21, width * .23, width * .23], font_size=7),
        Spacer(1, 3 * mm),
        callout_table("The software does not guess based on similar-sounding product names. Human review is the intended result when equipment or notice details are unclear.", width),
    ]
    timing = det["timing"]
    p3 = [
        para("TESTS, LIMITATIONS, AND NEXT EVALUATION", styles["eyebrow"]),
        para("Security and availability checks", styles["title"]),
        para("The test suite checks local software behavior and known edge cases. It does not certify the system or validate real OT outcomes.", styles["deck"]),
        para("Checks included", styles["h2"]),
        para("Tests include security instructions embedded in advisory text; the AI helper is told to treat them as untrusted, and unsupported extracted details or quotes are rejected. Duplicate equipment IDs and macro-enabled spreadsheets are rejected. When a source refresh fails, OTProof can use a saved older copy and mark it stale. Permission tests check that users cannot approve or verify work outside their role. The workflow test records a human decision, approved plan, simulated evidence, and a separate evidence check.", styles["body"]),
        para("Performance scope", styles["h2"]),
        para(f"{timing['elapsed_ms']:.3f} ms elapsed for one in-process pass over {timing['full_cross_product_pairs']} pairs ({timing['milliseconds_per_pair']:.4f} ms/pair on this developer machine). The measurement excludes database queries, HTTP ingestion, browser rendering, concurrency, cold starts, and human review. Operator review time was not instrumented or measured.", styles["body"]),
        para("Limits", styles["h2"]),
        para("Small synthetic sample; three Rockwell CISA fixtures; no blinded ground truth; no live local model evaluation; no industrial vendor/model breadth study; no penetration test; no production load test; and no human time study. The test client emits a Starlette warning that the installed HTTPX integration is deprecated, though tests pass. Docker Compose could not be run because a daemon was unavailable.", styles["body"]),
        para("Next evaluation protocol", styles["h2"]),
        para("Recruit engineers from several operators. Ask them to label source-reviewed examples across vendors and versions before they see OTProof's results. Compare disagreements and report how often the system finds a relevant affected product, how often it misses one, how often it asks for human review, whether each result links to its source, and minutes spent per review. Test the rule-based matcher first. Evaluate AI extraction separately by comparing its suggested fields with the source and human labels. Also test unavailable sources, large spreadsheets, hostile text, permissions, and deployment security.", styles["body"]),
        callout_table("The current result is a build check, not a customer study, security certification, safety case, or verified reduction in operational risk.", width),
    ]
    build_narrative_pdf(ROOT / "OTProof_Evaluation_Report.pdf", "Evaluation Report", [p1, p2, p3])


def architecture_svg() -> None:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="920" viewBox="0 0 1440 920" role="img" aria-labelledby="title desc">
<title id="title">OTProof: plain-language architecture</title><desc id="desc">An operator uploads an equipment list. OTProof reads public security notices, compares product and version details, and records human review in a database. People check evidence. Optional AI can draft text but cannot decide or change equipment.</desc>
<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto"><path d="M1 1L10 6L1 11" fill="none" stroke="#25A99A" stroke-width="2"/></marker><style>text{font-family:Inter,Arial,sans-serif;fill:#18313A}.h{font-size:32px;font-weight:700}.sub{font-size:16px;fill:#63777C}.box{fill:#fff;stroke:#D4E2E0;stroke-width:2}.dark{fill:#1C3441;stroke:#1C3441}.teal{fill:#25A99A}.label{font-size:13px;font-weight:700;letter-spacing:1.5px;fill:#25A99A}.boxt{font-size:20px;font-weight:700}.small{font-size:15px;fill:#63777C}.darkt{fill:#fff;font-size:20px;font-weight:700}.darksmall{fill:#D0E0DF;font-size:15px}.line{stroke:#25A99A;stroke-width:3;fill:none;marker-end:url(#arrow)}.dash{stroke:#E08B62;stroke-width:2;stroke-dasharray:8 7;fill:none}</style></defs>
<rect width="1440" height="920" fill="#F3F7F6"/><rect x="0" y="0" width="1440" height="14" fill="#25A99A"/>
<text x="72" y="78" class="label">PUBLIC NOTICES · HUMAN REVIEW · NO DEVICE CONNECTION</text><text x="72" y="124" class="h">How OTProof works</text><text x="72" y="158" class="sub">It compares records, explains a possible match, and saves the team's decisions and evidence.</text>
<rect x="72" y="218" width="300" height="170" rx="18" class="box"/><text x="98" y="253" class="label">START WITH A FILE</text><text x="98" y="292" class="boxt">Equipment list</text><text x="98" y="324" class="small">Product and software version</text><text x="98" y="352" class="small">Site, owner, and last check date</text>
<rect x="72" y="444" width="300" height="222" rx="18" class="box"/><text x="98" y="480" class="label">PUBLIC NOTICES</text><text x="98" y="520" class="boxt">CISA and NIST</text><text x="98" y="551" class="boxt">Approved vendor websites</text><text x="98" y="585" class="small">Save source link and dates</text><text x="98" y="615" class="small">Use an older copy if a feed is down</text>
<rect x="470" y="268" width="340" height="350" rx="20" class="dark"/><text x="502" y="309" class="label" fill="#8FC7BE">OTPROOF SERVICE</text><text x="502" y="358" class="darkt" fill="#FFFFFF">Check records</text><text x="502" y="394" class="darksmall" fill="#D0E0DF">Compare maker, product, and version</text><text x="502" y="425" class="darksmall" fill="#D0E0DF">Explain what matched or is missing</text><text x="502" y="456" class="darksmall" fill="#D0E0DF">Record review and work history</text><rect x="502" y="496" width="275" height="82" rx="12" fill="#25A99A"/><text x="522" y="531" class="darkt" fill="#FFFFFF">Matching rules</text><text x="522" y="557" class="darksmall" fill="#D0E0DF">Product identity + version evidence</text>
<rect x="910" y="218" width="265" height="170" rx="18" class="box"/><text x="938" y="253" class="label">SAVED RECORDS</text><text x="938" y="294" class="boxt">Equipment and notices</text><text x="938" y="325" class="small">Reviews and work plans</text><text x="938" y="353" class="small">Evidence and source dates</text>
<rect x="910" y="444" width="265" height="222" rx="18" class="box"/><text x="938" y="480" class="label">PEOPLE CHECK THE RESULT</text><text x="938" y="520" class="boxt">Reviewer checks match</text><text x="938" y="551" class="boxt">Engineer proposes work</text><text x="938" y="585" class="small">Approver checks plan and evidence</text><text x="938" y="615" class="small">A person is required to close</text>
<rect x="1250" y="300" width="120" height="285" rx="18" class="box"/><text x="1270" y="339" class="label">RESULTS</text><text x="1270" y="388" class="boxt">Dashboard</text><text x="1270" y="419" class="small">Findings</text><text x="1270" y="460" class="boxt">PDF</text><text x="1270" y="491" class="small">Report</text><text x="1270" y="535" class="small">Action history</text>
<path d="M372 302H455" class="line"/><path d="M372 555H435Q455 555 455 535V475" class="line"/><path d="M810 344H895" class="line"/><path d="M810 512H895" class="line"/><path d="M1175 520H1235" class="line"/>
<rect x="484" y="704" width="690" height="115" rx="18" fill="#DDF3EF" stroke="#9CD8CE" stroke-width="2"/><text x="514" y="743" class="label">OPTIONAL · LOCAL AI HELPER</text><text x="514" y="779" class="boxt">Can draft text fields and summaries from a notice</text><text x="514" y="804" class="small">Cannot decide a match, approve work, or change equipment.</text><path d="M645 704V635" class="dash"/>
<text x="72" y="870" class="small">No device scan · no exploit · no remote query · no configuration changes</text>
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
    print(f"Generated idea document, business/evaluation PDFs, {len(SLIDES)}-slide deck, and architecture SVG.")


if __name__ == "__main__":
    main()


