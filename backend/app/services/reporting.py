from __future__ import annotations

import html
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Advisory, Asset, AuditEvent, Finding, SourceSnapshot

INK = colors.HexColor("#142630")
TEAL = colors.HexColor("#087E83")
PALE = colors.HexColor("#EAF4F2")
MUTED = colors.HexColor("#56666E")


def _markup(value: object) -> str:
    return html.escape(str(value), quote=True)


def assurance_data(db: Session) -> dict:
    findings = (
        db.query(Finding)
        .options(
            joinedload(Finding.asset),
            joinedload(Finding.advisory),
            joinedload(Finding.evidence_records),
            joinedload(Finding.tickets),
        )
        .order_by(Finding.id)
        .all()
    )
    assets = db.query(Asset).count()
    advisories = db.query(Advisory).count()
    unresolved = sum(f.status not in {"not_applicable", "verified_remediated", "closed"} for f in findings)
    verified = sum(f.status == "verified_remediated" for f in findings)
    evidence_complete = sum(bool(f.evidence_records) for f in findings)
    today = date.today()
    overdue = sum(
        1
        for f in findings
        for ticket in f.tickets
        if ticket.due_date
        and ticket.due_date < today
        and ticket.status in {"approved", "in_progress", "mitigated_pending_verification"}
    )
    rows = []
    for finding in findings:
        rows.append(
            {
                "finding_id": finding.id,
                "asset_id": finding.asset.asset_id,
                "vendor": finding.asset.vendor,
                "product": finding.asset.product,
                "version": finding.asset.firmware_version,
                "advisory_id": finding.advisory.external_id,
                "title": finding.advisory.title,
                "source_url": finding.advisory.source_url,
                "cves": finding.advisory.cves,
                "applicability": finding.applicability,
                "workflow_status": finding.status,
                "engineering_decision": finding.decision,
                "decision_rationale": finding.decision_rationale,
                "reasons": finding.reasons,
                "evidence": finding.evidence,
                "evidence_records": [
                    {
                        "id": e.id,
                        "type": e.evidence_type,
                        "label": e.label,
                        "reference": e.reference,
                        "sha256": e.sha256,
                        "recorded_by": e.recorded_by,
                        "verified_by": e.verified_by,
                        "verified_at": e.verified_at.isoformat() if e.verified_at else None,
                    }
                    for e in finding.evidence_records
                ],
                "tickets": [
                    {
                        "id": t.id,
                        "status": t.status,
                        "assigned_to": t.assigned_to,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "proposed_action": t.proposed_action,
                    }
                    for t in finding.tickets
                ],
                "source_published_at": finding.advisory.published_at.isoformat()
                if finding.advisory.published_at
                else None,
                "source_updated_at": finding.advisory.source_updated_at.isoformat()
                if finding.advisory.source_updated_at
                else None,
                "advisory_imported_at": finding.advisory.imported_at.isoformat(),
            }
        )
    audits = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(1000).all()
    source_snapshots = db.query(SourceSnapshot).order_by(SourceSnapshot.fetched_at.desc()).limit(500).all()
    return {
        "report_title": "OTProof Remediation Assurance Report",
        "generated_at": date.today().isoformat(),
        "inventory_label": "Fictional Cedar Valley Water Utility (synthetic demonstration data)",
        "summary": {
            "asset_count": assets,
            "advisory_count": advisories,
            "finding_count": len(findings),
            "applicable": sum(f.applicability == "applicable" for f in findings),
            "requires_manual_verification": sum(
                f.applicability == "requires_manual_verification" for f in findings
            ),
            "not_applicable": sum(f.applicability == "not_applicable" for f in findings),
            "unresolved": unresolved,
            "verified_remediated": verified,
            "with_evidence": evidence_complete,
            "overdue": overdue,
        },
        "findings": rows,
        "source_snapshots": [
            {
                "source_name": snapshot.source_name,
                "source_url": snapshot.source_url,
                "fetched_at": snapshot.fetched_at.isoformat(),
                "status": snapshot.status,
                "etag": snapshot.etag,
                "last_modified": snapshot.last_modified,
                "sha256": snapshot.sha256,
            }
            for snapshot in source_snapshots
        ],
        "audit_events": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "actor": a.actor,
                "role": a.actor_role,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "details": a.details,
            }
            for a in audits
        ],
        "assurance_limits": [
            "Applicability results are deterministic screening outputs, not proof of exploitation or safety impact.",
            "Only an authorized engineering decision changes a candidate into a reviewed applicability decision.",
            "A remediation ticket, narrative, or evidence attachment does not by itself mark a finding remediated.",
            "Verified remediation requires an approver decision referencing evidence and rationale.",
            "All demonstration assets and operational workflow records are fictional.",
        ],
    }


def build_pdf(data: dict) -> bytes:
    target = BytesIO()
    page = landscape(A4)
    document = SimpleDocTemplate(
        target,
        pagesize=page,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=17 * mm,
        bottomMargin=15 * mm,
        title=data["report_title"],
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="OTTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            textColor=INK,
            alignment=0,
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(name="OTBody", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=INK)
    )
    styles.add(
        ParagraphStyle(name="OTSmall", parent=styles["BodyText"], fontSize=7, leading=9, textColor=MUTED)
    )
    styles.add(ParagraphStyle(name="OTCell", parent=styles["BodyText"], fontSize=7, leading=9, textColor=INK))
    story = [
        Paragraph(data["report_title"], styles["OTTitle"]),
        Paragraph(f"Generated {data['generated_at']} · {data['inventory_label']}", styles["OTBody"]),
        Spacer(1, 4 * mm),
    ]
    summary = data["summary"]
    metric_rows = [
        ["Assets", "Advisories", "Findings", "Applicable", "Manual review", "Verified", "Overdue"],
        [
            str(summary[k])
            for k in [
                "asset_count",
                "advisory_count",
                "finding_count",
                "applicable",
                "requires_manual_verification",
                "verified_remediated",
                "overdue",
            ]
        ],
    ]
    metric_table = Table(metric_rows, colWidths=[36 * mm] * 7)
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), PALE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([metric_table, Spacer(1, 5 * mm), Paragraph("Finding register", styles["Heading2"])])
    data_rows = [["Asset / version", "Advisory", "Applicability", "Workflow", "Reason / evidence", "Source"]]
    for row in data["findings"]:
        reason = "; ".join(row["reasons"][:2])
        if row["decision_rationale"]:
            reason += f" | Decision: {row['decision_rationale']}"
        source_url = _markup(row["source_url"])
        src = f'<link href="{source_url}" color="#087E83">{_markup(row["advisory_id"])}</link>'
        data_rows.append(
            [
                Paragraph(
                    f"{_markup(row['asset_id'])}<br/>{_markup(row['vendor'])} {_markup(row['product'])} {_markup(row['version'])}",
                    styles["OTCell"],
                ),
                Paragraph(
                    f"{_markup(row['advisory_id'])}<br/>{_markup(', '.join(row['cves']))}"
                    f"<br/>Published: {_markup(row['source_published_at'] or 'unknown')}"
                    f"<br/>Updated: {_markup(row['source_updated_at'] or 'unknown')}"
                    f"<br/>Imported: {_markup(row['advisory_imported_at'][:10])}",
                    styles["OTCell"],
                ),
                Paragraph(_markup(row["applicability"].replace("_", " ")), styles["OTCell"]),
                Paragraph(
                    f"{_markup(row['workflow_status'])}<br/>Decision: {_markup(row['engineering_decision'])}",
                    styles["OTCell"],
                ),
                Paragraph(_markup((reason or "No rationale recorded")[:500]), styles["OTCell"]),
                Paragraph(src, styles["OTCell"]),
            ]
        )
    findings_table = Table(
        data_rows, colWidths=[48 * mm, 36 * mm, 34 * mm, 34 * mm, 89 * mm, 27 * mm], repeatRows=1
    )
    findings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D4D7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8F8")]),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            findings_table,
            Spacer(1, 5 * mm),
            Paragraph("Audit trail (most recent 1,000 events)", styles["Heading2"]),
        ]
    )
    audit_rows = [["Time", "Actor / role", "Action", "Record", "Details"]]
    for event in data["audit_events"]:
        audit_rows.append(
            [
                event["created_at"][:19].replace("T", " "),
                event["actor"],
                event["action"],
                f"{event['entity_type']} {event['entity_id']}",
                Paragraph(_markup(str(event["details"])[:400]), styles["OTSmall"]),
            ]
        )
    if len(audit_rows) > 1:
        audit_table = Table(
            audit_rows, colWidths=[35 * mm, 38 * mm, 36 * mm, 38 * mm, 121 * mm], repeatRows=1
        )
        audit_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D4D7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(audit_table)
    story.extend([PageBreak(), Paragraph("Assurance scope and limits", styles["Heading2"])])
    story.extend(Paragraph(f"• {limit}", styles["OTBody"]) for limit in data["assurance_limits"])
    if data["source_snapshots"]:
        story.append(PageBreak())
    story.append(Paragraph("Source snapshot register", styles["Heading2"]))
    story.append(
        Paragraph(
            "Cached public-source records used by this application database. Payloads are excluded; source URLs, timestamps, validators, status, and hashes are retained.",
            styles["OTBody"],
        )
    )
    if data["source_snapshots"]:
        snapshot_rows = [["Source", "State", "Fetched (UTC)", "Source URL", "SHA-256"]]
        for snapshot in data["source_snapshots"]:
            snapshot_rows.append(
                [
                    Paragraph(_markup(snapshot["source_name"]), styles["OTCell"]),
                    Paragraph(_markup(snapshot["status"]), styles["OTCell"]),
                    Paragraph(_markup(snapshot["fetched_at"][:19].replace("T", " ")), styles["OTCell"]),
                    Paragraph(
                        f'<link href="{_markup(snapshot["source_url"])}" color="#087E83">{_markup(snapshot["source_url"])}</link>',
                        styles["OTCell"],
                    ),
                    Paragraph(_markup(snapshot["sha256"]), styles["OTCell"]),
                ]
            )
        snapshot_table = Table(
            snapshot_rows,
            colWidths=[40 * mm, 24 * mm, 43 * mm, 116 * mm, 44 * mm],
            repeatRows=1,
        )
        snapshot_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D4D7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(snapshot_table)
    else:
        story.append(
            Paragraph(
                "No network source snapshot is stored in this database. Offline fixture records retain their public source URLs, publication/update dates, and import times.",
                styles["OTBody"],
            )
        )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E1E2"))
        canvas.line(15 * mm, 11 * mm, page[0] - 15 * mm, 11 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            15 * mm,
            7 * mm,
            "OTProof · Fictional demonstration data · Source-linked screening and human decisions",
        )
        canvas.drawRightString(page[0] - 15 * mm, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return target.getvalue()
