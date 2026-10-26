from __future__ import annotations

from datetime import date
from hashlib import sha256

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.auth import Principal, require_roles
from app.core.config import get_settings
from app.core.db import get_db
from app.models.entities import (
    Advisory,
    Asset,
    AuditEvent,
    EvidenceRecord,
    Finding,
    RemediationTicket,
    utcnow,
)
from app.schemas.domain import DecisionIn, EvidenceCreate, TicketCreate, TicketDecision, VerificationIn
from app.services import sources
from app.services.audit import record
from app.services.inventory import read_inventory, to_asset
from app.services.llm import extract as llm_extract
from app.services.matching import assess, canonical_product, canonical_vendor
from app.services.reporting import assurance_data, build_pdf

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "mode": "passive-offline-demo", "ot_network_access": False}


@router.get("/meta")
def meta():
    settings = get_settings()
    return {
        "name": "OTProof",
        "demo_mode": settings.demo_mode,
        "roles": ["engineer", "reviewer", "approver", "admin"],
        "demo_tokens": settings.configured_tokens if settings.demo_mode else {},
        "source_urls": {"cisa_ics": sources.CISA_ICS_RSS, "cisa_kev": sources.CISA_KEV_JSON},
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    assets = db.query(Asset).count()
    advisories = db.query(Advisory).count()
    findings = db.query(Finding).all()
    tickets = db.query(RemediationTicket).all()
    today = date.today()
    return {
        "assets_reviewed": sum(
            bool(a.last_verified) and (today - a.last_verified).days <= 180 for a in db.query(Asset).all()
        ),
        "asset_count": assets,
        "advisory_count": advisories,
        "finding_count": len(findings),
        "applicable": sum(f.applicability == "applicable" for f in findings),
        "requires_manual_verification": sum(
            f.applicability == "requires_manual_verification" for f in findings
        ),
        "not_applicable": sum(f.applicability == "not_applicable" for f in findings),
        "findings_requiring_engineering_review": sum(f.status == "requires_review" for f in findings),
        "evidence_completeness": round(sum(bool(f.evidence_records) for f in findings) / len(findings) * 100)
        if findings
        else 0,
        "verified_remediated": sum(f.status == "verified_remediated" for f in findings),
        "open_findings": sum(
            f.status not in {"not_applicable", "verified_remediated", "closed"} for f in findings
        ),
        "overdue": sum(
            bool(
                t.due_date
                and t.due_date < today
                and t.status in {"approved", "in_progress", "mitigated_pending_verification"}
            )
            for t in tickets
        ),
    }


@router.get("/assets")
def list_assets(
    limit: int = Query(250, ge=1, le=1000), offset: int = Query(0, ge=0), db: Session = Depends(get_db)
):
    rows = db.query(Asset).order_by(Asset.asset_id).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": a.id,
                "asset_id": a.asset_id,
                "vendor": a.vendor,
                "product": a.product,
                "model": a.model,
                "firmware_version": a.firmware_version,
                "equipment_type": a.equipment_type,
                "site": a.site,
                "criticality": a.criticality,
                "review_owner": a.review_owner,
                "last_verified": a.last_verified.isoformat() if a.last_verified else None,
            }
            for a in rows
        ],
        "total": db.query(Asset).count(),
    }


@router.post("/assets/import")
async def import_assets(
    file: UploadFile = File(...),
    replace_existing: bool = False,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("reviewer")),
):
    content = await file.read(get_settings().max_upload_bytes + 1)
    try:
        rows = read_inventory(file.filename or "", content, get_settings().max_upload_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = {
        row.asset_id: row
        for row in db.query(Asset).filter(Asset.asset_id.in_([x.asset_id for x in rows])).all()
    }
    collisions = [row.asset_id for row in rows if row.asset_id in existing]
    if collisions and not replace_existing:
        raise HTTPException(
            status_code=409,
            detail=f"Asset identifiers already exist; re-import with replace_existing=true to update: {collisions[:20]}",
        )
    for row in rows:
        candidate = to_asset(row)
        if row.asset_id in existing:
            target = existing[row.asset_id]
            for key in (
                "vendor",
                "product",
                "model",
                "firmware_version",
                "equipment_type",
                "site",
                "criticality",
                "review_owner",
                "last_verified",
            ):
                setattr(target, key, getattr(candidate, key))
        else:
            db.add(candidate)
    db.flush()
    record(
        db,
        principal,
        "inventory.import",
        "asset_batch",
        len(rows),
        {
            "filename": file.filename,
            "rows": len(rows),
            "replaced": len(collisions),
            "sha256": sha256(content).hexdigest(),
        },
    )
    db.commit()
    return {"imported": len(rows), "updated": len(collisions), "sha256": sha256(content).hexdigest()}


@router.get("/advisories")
def list_advisories(limit: int = Query(250, ge=1, le=1000), db: Session = Depends(get_db)):
    rows = (
        db.query(Advisory)
        .order_by(Advisory.published_at.desc().nullslast(), Advisory.external_id)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": a.id,
                "external_id": a.external_id,
                "title": a.title,
                "source": a.source,
                "source_url": a.source_url,
                "vendor": a.vendor,
                "product": a.product,
                "cves": a.cves,
                "affected_products": a.affected_products,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "source_updated_at": a.source_updated_at.isoformat() if a.source_updated_at else None,
                "imported_at": a.imported_at.isoformat(),
            }
            for a in rows
        ],
        "total": db.query(Advisory).count(),
    }


@router.post("/ingest/cisa-ics")
def ingest_ics(
    limit: int = Query(10, ge=1, le=20),
    force: bool = False,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("reviewer")),
):
    try:
        result = sources.ingest_cisa_ics(db, limit, force)
        record(db, principal, "advisory.ingest.cisa_ics", "source", sources.CISA_ICS_RSS, result)
        db.commit()
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CISA ICS ingestion failed: {exc}") from exc


@router.post("/ingest/cisa-kev")
def ingest_kev(
    limit: int = Query(100, ge=1, le=1000),
    force: bool = False,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("reviewer")),
):
    try:
        result = sources.ingest_kev(db, limit, force)
        record(db, principal, "advisory.ingest.cisa_kev", "source", sources.CISA_KEV_JSON, result)
        db.commit()
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CISA KEV ingestion failed: {exc}") from exc


@router.post("/ingest/nvd/{cve}")
def ingest_nvd(
    cve: str,
    force: bool = False,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("reviewer")),
):
    try:
        result = sources.ingest_nvd_cve(db, cve, force)
        record(db, principal, "advisory.ingest.nvd", "cve", cve.upper(), result)
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NVD ingestion failed: {exc}") from exc


@router.post("/ingest/vendor")
def ingest_vendor(
    url: str, db: Session = Depends(get_db), principal: Principal = Depends(require_roles("reviewer"))
):
    try:
        result = sources.ingest_vendor_bulletin(db, url)
        record(db, principal, "advisory.ingest.vendor", "advisory", result["external_id"], {"url": url})
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vendor bulletin ingestion failed: {exc}") from exc


def _is_duplicate(a: Asset, candidates: list[Asset]) -> bool:
    def fingerprint(item: Asset):
        return (
            canonical_vendor(item.vendor),
            canonical_product(item.product),
            (item.model or "").casefold().strip(),
            (item.firmware_version or "").casefold().strip(),
            (item.site or "").casefold().strip(),
        )

    return sum(fingerprint(other) == fingerprint(a) for other in candidates) > 1


@router.post("/analyze")
def analyze(db: Session = Depends(get_db), principal: Principal = Depends(require_roles("reviewer"))):
    assets = db.query(Asset).order_by(Asset.id).all()
    advisories = db.query(Advisory).order_by(Advisory.id).all()
    created = updated = skipped = 0
    for asset in assets:
        duplicate = _is_duplicate(asset, assets)
        for advisory in advisories:
            result = assess(asset, advisory, duplicate_candidate=duplicate)
            same_vendor = canonical_vendor(asset.vendor) == canonical_vendor(advisory.vendor) and bool(
                canonical_vendor(asset.vendor)
            )
            same_product = canonical_product(asset.product) == canonical_product(advisory.product) and bool(
                canonical_product(asset.product)
            )
            if result["applicability"] == "not_applicable" and not (same_vendor and same_product):
                skipped += 1
                continue
            finding = db.query(Finding).filter_by(asset_id=asset.id, advisory_id=advisory.id).one_or_none()
            if finding is None:
                finding = Finding(asset_id=asset.id, advisory_id=advisory.id, **result)
                db.add(finding)
                created += 1
            elif finding.decision == "pending":
                finding.applicability = result["applicability"]
                finding.status = result["status"]
                finding.reasons = result["reasons"]
                finding.evidence = result["evidence"]
                finding.updated_at = utcnow()
                updated += 1
    record(
        db,
        principal,
        "applicability.analyze",
        "analysis",
        f"{len(assets)}x{len(advisories)}",
        {
            "assets": len(assets),
            "advisories": len(advisories),
            "created": created,
            "updated": updated,
            "skipped_clear_nonmatches": skipped,
            "method": "deterministic curated aliases and numeric dotted version constraints",
        },
    )
    db.commit()
    rows = db.query(Finding).all()
    return {
        "assets_scanned": len(assets),
        "advisories_compared": len(advisories),
        "findings_created": created,
        "findings_refreshed": updated,
        "clear_nonmatches_skipped": skipped,
        "applicable_candidates": sum(f.applicability == "applicable" for f in rows),
        "requires_manual_verification": sum(f.applicability == "requires_manual_verification" for f in rows),
        "not_applicable": sum(f.applicability == "not_applicable" for f in rows),
    }


@router.get("/findings")
def list_findings(
    status: str | None = None,
    applicability: str | None = None,
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Finding)
        .options(joinedload(Finding.asset), joinedload(Finding.advisory))
        .order_by(Finding.id)
    )
    if status:
        query = query.filter(Finding.status == status)
    if applicability:
        query = query.filter(Finding.applicability == applicability)
    rows = query.limit(limit).all()
    items = []
    for f in rows:
        items.append(
            {
                "id": f.id,
                "applicability": f.applicability,
                "status": f.status,
                "reasons": f.reasons,
                "evidence": f.evidence,
                "decision": f.decision,
                "decision_rationale": f.decision_rationale,
                "decided_by": f.decided_by,
                "asset": {
                    "id": f.asset.id,
                    "asset_id": f.asset.asset_id,
                    "vendor": f.asset.vendor,
                    "product": f.asset.product,
                    "model": f.asset.model,
                    "firmware_version": f.asset.firmware_version,
                    "equipment_type": f.asset.equipment_type,
                    "site": f.asset.site,
                    "criticality": f.asset.criticality,
                    "review_owner": f.asset.review_owner,
                    "last_verified": f.asset.last_verified.isoformat() if f.asset.last_verified else None,
                },
                "advisory": {
                    "id": f.advisory.id,
                    "external_id": f.advisory.external_id,
                    "title": f.advisory.title,
                    "source": f.advisory.source,
                    "source_url": f.advisory.source_url,
                    "vendor": f.advisory.vendor,
                    "product": f.advisory.product,
                    "cves": f.advisory.cves,
                    "affected_products": f.advisory.affected_products,
                    "published_at": f.advisory.published_at.isoformat() if f.advisory.published_at else None,
                },
                "tickets": [
                    {
                        "id": t.id,
                        "status": t.status,
                        "title": t.title,
                        "proposed_action": t.proposed_action,
                        "assigned_to": t.assigned_to,
                        "planned_mitigation": t.planned_mitigation,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "decision_rationale": t.decision_rationale,
                    }
                    for t in f.tickets
                ],
                "evidence_records": [
                    {
                        "id": e.id,
                        "ticket_id": e.ticket_id,
                        "evidence_type": e.evidence_type,
                        "label": e.label,
                        "reference": e.reference,
                        "notes": e.notes,
                        "sha256": e.sha256,
                        "recorded_by": e.recorded_by,
                        "verified_by": e.verified_by,
                        "verified_at": e.verified_at.isoformat() if e.verified_at else None,
                    }
                    for e in f.evidence_records
                ],
            }
        )
    return {"items": items, "total": query.count()}


@router.post("/findings/{finding_id}/decision")
def decide_finding(
    finding_id: int,
    body: DecisionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("reviewer")),
):
    finding = db.query(Finding).filter_by(id=finding_id).one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    if finding.status == "verified_remediated":
        raise HTTPException(status_code=409, detail="Verified remediation is immutable in this MVP")
    if body.decision == "applicable":
        finding.decision = "applicable"
        finding.status = "open"
    else:
        finding.decision = "not_applicable"
        finding.status = "not_applicable"
    finding.decision_rationale = body.rationale
    finding.decided_by = principal.actor
    finding.decided_at = utcnow()
    record(
        db,
        principal,
        "finding.engineering_decision",
        "finding",
        finding.id,
        {"decision": body.decision, "rationale": body.rationale},
    )
    db.commit()
    return {
        "id": finding.id,
        "decision": finding.decision,
        "status": finding.status,
        "decided_by": finding.decided_by,
    }


@router.post("/findings/{finding_id}/tickets")
def create_ticket(
    finding_id: int,
    body: TicketCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("engineer", "reviewer")),
):
    finding = db.query(Finding).filter_by(id=finding_id).one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    if finding.decision != "applicable" or finding.status not in {"open", "in_progress"}:
        raise HTTPException(
            status_code=409,
            detail="An approved engineering applicability decision is required before a remediation proposal",
        )
    ticket = RemediationTicket(
        finding_id=finding.id,
        title=f"Review remediation for finding #{finding.id}",
        proposed_action=body.proposed_action,
        assigned_to=body.assigned_to,
        planned_mitigation=body.planned_mitigation,
        due_date=body.due_date,
        status="proposed",
    )
    db.add(ticket)
    db.flush()
    record(
        db,
        principal,
        "ticket.proposed",
        "ticket",
        ticket.id,
        {
            "finding_id": finding.id,
            "assigned_to": ticket.assigned_to,
            "due_date": ticket.due_date.isoformat() if ticket.due_date else None,
        },
    )
    db.commit()
    return {
        "id": ticket.id,
        "finding_id": ticket.finding_id,
        "status": ticket.status,
        "title": ticket.title,
        "proposed_action": ticket.proposed_action,
        "assigned_to": ticket.assigned_to,
        "due_date": ticket.due_date.isoformat() if ticket.due_date else None,
    }


@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db)):
    return {
        "items": [
            {
                "id": t.id,
                "finding_id": t.finding_id,
                "status": t.status,
                "title": t.title,
                "proposed_action": t.proposed_action,
                "assigned_to": t.assigned_to,
                "planned_mitigation": t.planned_mitigation,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "decision_rationale": t.decision_rationale,
            }
            for t in db.query(RemediationTicket).order_by(RemediationTicket.id.desc()).all()
        ]
    }


@router.post("/tickets/{ticket_id}/decision")
def decide_ticket(
    ticket_id: int,
    body: TicketDecision,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("approver")),
):
    ticket = db.query(RemediationTicket).filter_by(id=ticket_id).one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != "proposed":
        raise HTTPException(status_code=409, detail="Only proposed tickets can be approved or rejected")
    ticket.status = body.decision
    ticket.decision_rationale = body.rationale
    ticket.decided_by = principal.actor
    ticket.decided_at = utcnow()
    finding = db.query(Finding).filter_by(id=ticket.finding_id).one()
    finding.status = "in_progress" if body.decision == "approved" else "open"
    record(
        db,
        principal,
        f"ticket.{body.decision}",
        "ticket",
        ticket.id,
        {"finding_id": finding.id, "rationale": body.rationale},
    )
    db.commit()
    return {"id": ticket.id, "status": ticket.status, "finding_status": finding.status}


@router.post("/findings/{finding_id}/evidence")
def attach_evidence(
    finding_id: int,
    body: EvidenceCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("engineer", "reviewer")),
):
    finding = db.query(Finding).filter_by(id=finding_id).one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    ticket = None
    if body.ticket_id is not None:
        ticket = db.query(RemediationTicket).filter_by(id=body.ticket_id, finding_id=finding.id).one_or_none()
        if not ticket or ticket.status != "approved":
            raise HTTPException(
                status_code=409,
                detail="Evidence for remediation requires an approved ticket for this finding",
            )
    digest = sha256(body.content.encode("utf-8")).hexdigest() if body.content else ""
    evidence = EvidenceRecord(
        finding_id=finding.id,
        ticket_id=body.ticket_id,
        evidence_type=body.evidence_type,
        label=body.label,
        reference=body.reference,
        notes=body.notes,
        sha256=digest,
        recorded_by=principal.actor,
    )
    db.add(evidence)
    if ticket:
        finding.status = "mitigated_pending_verification"
        ticket.status = "mitigated_pending_verification"
    db.flush()
    record(
        db,
        principal,
        "evidence.attached",
        "evidence",
        evidence.id,
        {"finding_id": finding.id, "ticket_id": body.ticket_id, "type": body.evidence_type, "sha256": digest},
    )
    db.commit()
    return {
        "id": evidence.id,
        "finding_id": evidence.finding_id,
        "ticket_id": evidence.ticket_id,
        "sha256": evidence.sha256,
        "verified": False,
    }


@router.post("/findings/{finding_id}/verify")
def verify_remediation(
    finding_id: int,
    body: VerificationIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("approver")),
):
    finding = db.query(Finding).filter_by(id=finding_id).one_or_none()
    evidence = db.query(EvidenceRecord).filter_by(id=body.evidence_id, finding_id=finding_id).one_or_none()
    if not finding or not evidence:
        raise HTTPException(status_code=404, detail="Finding or associated evidence record not found")
    if not evidence.ticket_id:
        raise HTTPException(
            status_code=409,
            detail="Verification requires evidence attached to an approved remediation ticket",
        )
    ticket = db.query(RemediationTicket).filter_by(id=evidence.ticket_id, finding_id=finding_id).one_or_none()
    if not ticket or ticket.status != "mitigated_pending_verification":
        raise HTTPException(status_code=409, detail="Ticket is not awaiting verification")
    evidence.verified_by = principal.actor
    evidence.verified_at = utcnow()
    finding.status = "verified_remediated"
    ticket.status = "verified_remediated"
    record(
        db,
        principal,
        "remediation.verified",
        "finding",
        finding.id,
        {"evidence_id": evidence.id, "ticket_id": ticket.id, "rationale": body.rationale},
    )
    db.commit()
    return {
        "finding_id": finding.id,
        "status": finding.status,
        "evidence_id": evidence.id,
        "verified_by": principal.actor,
    }


@router.post("/advisories/{advisory_id}/ai-extract")
def ai_extract(
    advisory_id: int, db: Session = Depends(get_db), principal: Principal = Depends(require_roles("reviewer"))
):
    advisory = db.query(Advisory).filter_by(id=advisory_id).one_or_none()
    if not advisory:
        raise HTTPException(status_code=404, detail="Advisory not found")
    try:
        output = llm_extract(advisory.title, advisory.source_excerpt or advisory.description)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record(
        db,
        principal,
        "advisory.ai_extraction",
        "advisory",
        advisory.id,
        {
            "model": get_settings().ollama_model,
            "verified_quotes": len(output.source_quotes),
            "authority": "suggestion_only",
        },
    )
    db.commit()
    return {"suggestion_only": True, **output.model_dump()}


@router.get("/audit")
def list_audit(limit: int = Query(500, ge=1, le=2000), db: Session = Depends(get_db)):
    rows = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit).all()
    return {
        "items": [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat(),
                "actor": e.actor,
                "role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": e.details,
            }
            for e in rows
        ]
    }


@router.get("/report/assurance.json")
def assurance_json(db: Session = Depends(get_db)):
    return assurance_data(db)


@router.get("/report/assurance.pdf")
def assurance_pdf(db: Session = Depends(get_db)):
    content = build_pdf(assurance_data(db))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=OTProof_Assurance_Report.pdf"},
    )
