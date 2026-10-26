# OTProof Implementation Plan

1. [x] Inspect workspace and establish safety/product constraints, plan, progress log, and technology decisions.
2. [x] Research authoritative OT, advisory, KEV, NVD, competitor, and technology sources; record citations and access dates.
3. [x] Build a reproducible fictional water utility inventory and real, source-linked advisory fixtures.
4. [x] Implement a modular FastAPI + SQLAlchemy backend: ingestion, normalization, deterministic applicability, human review, evidence, RBAC, audit, and reports.
5. [x] Implement a React + TypeScript dashboard and review workflow.
6. [x] Add labeled evaluation cases, prompt-injection and malformed-input checks, API tests, and offline mode measurements.
7. [x] Generate architecture SVG, technical design, idea document/PDF, business case PDF, evaluation PDF, and 14-slide pitch deck/PDF with notes.
8. [x] Run software/API verification, render and inspect documents, update documentation, and package the demo.

Environment limits: Docker daemon unavailable for Compose startup; no local LLM inference was run, so extraction accuracy remains unmeasured. See `PROGRESS.md`.
