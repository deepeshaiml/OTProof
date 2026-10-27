# OTProof Progress

Updated: 2026-10-27

## Plain-language summary

OTProof compares an operator's equipment spreadsheet with public security notices. It shows possible matches and the evidence behind them, then records the people who review and approve any work. It does not connect to or change industrial equipment. The 80 demo assets and all work evidence are fictional.

## Completed

1. **Project and safety rules:** established this plan, the repository instructions, technology decisions, and passive/read-only operating boundary.
2. **Research:** reviewed NIST OT guidance, CISA notices and exploited-vulnerability catalog, NVD records, competitors, and software choices. NIST SP 800-82 Revision 3 is treated as the published final guide; Revision 4 is identified as a draft.
3. **Examples:** created a repeatable inventory of 80 fictional water utility assets, three real source-linked CISA security notices, and 14 hand-labeled asset/notice examples.
4. **Application:** built spreadsheet import and checks, public-source retrieval and caching, product/version comparison, a human review and approval flow, action history, evidence records, and JSON/PDF exports.
5. **Dashboard and packaging:** built the React/TypeScript dashboard, local database setup, Docker Compose files, and demo walkthrough.
6. **Software evaluation:** all 14 prepared examples returned their expected results: 4 possible affected matches, 4 outside the notice conditions, and 6 sent to human review. Every labeled result retained its source ID, link, and text excerpt. The 1.008 ms measurement covers only one local comparison function pass over 240 pairs. It does not measure human review, internet access, or full application speed.
7. **Submission package:** generated and rendered a 9-page idea document, 15-slide PowerPoint with 70+ words of notes per slide, matching PDFs, business case, evaluation report, and architecture SVG. All pages and slides were visually checked.
8. **Plain-language review:** added a worked example and glossary to the reader materials, simplified slide wording, and added [docs/AI_AGENT_GUIDE.md](docs/AI_AGENT_GUIDE.md) with a safe example for coding assistants.
9. **API workflow check:** exercised the demo dashboard and report endpoints and tested the reviewer → engineer → approver → evidence verification sequence.

## Verification results

- Earlier repository verification: 14 pytest tests passed; Ruff, frontend production build, dependency check, migration, and `npm audit` passed. The test run includes one upstream Starlette deprecation warning.
- This document refresh: submission generator passed Ruff and Python compilation; DOCX/PPTX and PDFs regenerated successfully.
- Output counts: 9-page idea PDF, 15-page deck PDF, 3-page business case PDF, and 3-page evaluation PDF. PowerPoint has 15 slides; every slide retains substantial speaker notes.
- Visual review: all pages of the regenerated documents and deck were inspected, as was the updated architecture SVG.
- `docker compose config --quiet` passed, but the Docker daemon was unavailable, so container build and startup were not verified.
- CISA ICS/CSAF, CISA KEV, and NVD imports were previously exercised against public sources on 2026-10-26; fixed offline fixtures remain available.

## Remaining limits

- The inventory and evaluation set are small, fictional, and focused on a few Rockwell products. The results are not field accuracy or an operator study.
- No local AI model was run; its extraction quality and time savings are unknown.
- No measured human review-time reduction, customer revenue, compliance outcome, or operational-risk reduction is claimed.
- Production use still needs company identity, stronger audit retention, file-based evidence attachments, broader source/vendor support, a security review, and an operator pilot.
