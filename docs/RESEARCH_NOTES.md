# Research Notes

Accessed 2026-10-26. Product descriptions below summarize vendors' current public pages and are not independent comparative tests.

## Short version for non-specialists

Industrial operators keep lists of controllers, software, and other equipment. Public security notices describe which products and versions may be affected. OTProof compares those records and saves the source and human decision. A public vulnerability ID or a match is a reason to review a record; it is not proof that a specific plant asset is exposed or that a change should be made. The [NIST OT guide](https://csrc.nist.gov/pubs/sp/800/82/r3/final) supports maintaining accurate asset details, while the MVP avoids connecting to or scanning equipment.

Terms used below: **OT** means operational technology (equipment and computers that monitor or control physical processes); **CVE** is a public vulnerability identifier; **KEV** is CISA's list of vulnerabilities known to be exploited; **GRC** means governance, risk, and compliance. A short product example is in [the AI and human-agent guide](AI_AGENT_GUIDE.md).

## OT and public-source rationale

- [NIST SP 800-82 Rev. 3](https://csrc.nist.gov/pubs/sp/800/82/r3/final) is the published final guide (2023-09-28). NIST's [OT publication list](https://csrc.nist.gov/Projects/operational-technology-security/publications) lists Rev. 4 as a draft released 2026-09-21. The product and design documents therefore cite Rev. 3 as the final guide and label Rev. 4 draft status accurately.
- NIST Rev. 3 states that OT inventory should identify assets, software/firmware versions, locations, vendor details, and roles; accurate inventory supports risk and vulnerability management. It also cautions that automated collection approaches such as active scanning can affect OT and should be considered/tested carefully. OTProof uses an operator-supplied file and does not touch devices.
- [CISA ICS advisories](https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml) publish vendor vulnerability summaries and mitigations. The three fixture records and dates are linked in [SOURCES.md](../data/fixtures/SOURCES.md).
- [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) is a public catalog of vulnerabilities CISA identifies as exploited in the wild. KEV membership can inform triage but does not establish that an operator's specific model/version is affected.
- [NVD CVE API 2.0](https://nvd.nist.gov/developers/vulnerabilities) provides machine-readable CVE records and CPE version boundaries. NVD advises API users to use version 2.0 and documents API lifecycle changes in its [developer change timeline](https://nvd.nist.gov/general/news/change-timeline). OTProof caches API calls and interprets only supported direct product constraints; compound configuration expressions abstain.

## Competitive context

| Category | Publicly described capability | OTProof implication |
|---|---|---|
| Claroty Platform | Claroty describes asset inventory, exposure management, network protection, secure access, threat detection, and multiple deployment models. [Platform](https://claroty.com/platform) · [Asset Inventory](https://claroty.com/platform/asset-inventory) | Competes in broad CPS/OT security platform budgets. OTProof should test whether a focused advisory-to-inventory assurance workflow fills a process gap or integrates with deployed tools. |
| Tenable One OT Exposure | Tenable describes OT asset inventory, exposure prioritization, remediation guidance, integrations, compliance reporting, and passive monitoring plus vendor-approved Safe Active Query. [Product page](https://www.tenable.com/products/ot-security) | Broad OT exposure-management incumbent. OTProof has not shown a coverage, accuracy, or cost advantage. Its file-first MVP is suitable for a small offline pilot or complement. |
| Nozomi Networks Guardian | Product documentation describes asset discovery and inventory, firmware details, vulnerability assessment based on NVD, monitoring, and network visualization. [Guardian overview](https://technicaldocs.nozominetworks.com/guardian/latest/products/guardian/topics/intro/c_guardian.html) | Broad OT monitoring and vulnerability assessment. Potential integration target; no performance comparison has been performed. |
| GRC / IRM workflow, e.g. ServiceNow | ServiceNow describes structured risk-assessment and risk-issue workflows, controls, compliance, and audit management. [Risk Management](https://www.servicenow.com/docs/r/governance-risk-compliance/grc-risk-management-workspace/grc-risk-overview.html) · [GRC overview](https://www.servicenow.com/docs/r/xanadu/governance-risk-compliance/r_WhatIsGRC.html) | Useful system-of-record/workflow destinations. OTProof may supply source-backed technical applicability detail to those systems; the API currently has no ServiceNow integration. |

These are public, vendor-described capabilities. The market is established and includes well-funded products. “Focused source provenance, conservative matching, and explicit human assurance in one small workflow” is a **differentiation hypothesis**, not a proven advantage. Existing platform discovery and integrations may make an additional product unnecessary for some operators.

## Potential customer groups

Segments to interview, not validated pipeline:

- Municipal and regional water/wastewater utilities with small engineering/security teams and asset lists distributed across maintenance records.
- Electric power generation/transmission/distribution operators and energy cooperatives.
- Oil and gas operators, pipelines, and terminal owners with multi-site equipment and change windows.
- Industrial maintenance / automation contractors that maintain customer inventories and evidence handover.
- Managed OT security providers seeking a repeatable, reviewable customer-advisory workflow.
- Defense-support facilities and contractors that need local deployment and traceable evidence.

Likely buyers: OT cybersecurity lead, plant engineering manager, asset owner, CISO/IT risk leader, or managed service practice owner. Likely blockers: existing OT tool coverage, poor inventory quality, procurement/security review, vendor bulletin data rights, legacy identifiers, and operator concerns about putting asset details in a cloud service. A local/on-prem deployment path and source-only outbound egress are therefore important to validate.

## Business hypotheses and measurement

- Pricing hypothesis: annual per-site license, with enterprise multi-site tier, integrations/onboarding, and ongoing assurance support.
- Buyer value hypothesis: reduce repetitive manual source-to-inventory reconciliation, make uncertainty visible rather than bury it in false precision, and produce review/evidence history reusable during assurance activities.
- Review-time sensitivity example in the business-case PDF: 80 assets × 12 relevant advisory/product pairs each year, at 30 minutes of baseline triage versus 15 minutes after source-backed pre-screening, yields 240 theoretical hours saved (at $80 loaded labor/hour = $19,200). These times and wage are illustrative assumptions, not observed OTProof results.
- Annual recurring revenue and gross-profit scenarios are arithmetic examples from assumed customer/site/license inputs. They are not bookings, market sizing, or financial forecasts.
- Validation: 3–5 paid or design-partner sites; measure inventory completeness, adjudication agreement against engineer labels, false negatives, abstention quality, source coverage, review minutes per pair, onboarding effort, integration requests, willingness to pay, and renewal interest. Use blinded adjudication and include multiple equipment families and vendors.

## Technology and model licenses checked

Direct package versions are pinned in `requirements.txt` and `frontend/package-lock.json`; metadata for installed Python direct dependencies and npm package metadata were checked on 2026-10-26. See `TECHNOLOGY_DECISIONS.md` for package licenses and limits. Optional model repo [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) declares Apache-2.0; [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE) declares MIT. No model weights are included. A full transitive SBOM and deployment-specific license review remain required before commercial distribution.
