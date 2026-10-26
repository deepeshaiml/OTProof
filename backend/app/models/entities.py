from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    vendor: Mapped[str] = mapped_column(String(160))
    product: Mapped[str] = mapped_column(String(220))
    model: Mapped[str] = mapped_column(String(220), default="")
    firmware_version: Mapped[str] = mapped_column(String(100), default="")
    equipment_type: Mapped[str] = mapped_column(String(100), default="")
    site: Mapped[str] = mapped_column(String(160), default="")
    criticality: Mapped[str] = mapped_column(String(32), default="Medium")
    review_owner: Mapped[str] = mapped_column(String(160), default="Unassigned")
    last_verified: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    findings: Mapped[list["Finding"]] = relationship(back_populates="asset")


class Advisory(Base):
    __tablename__ = "advisories"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str] = mapped_column(Text)
    vendor: Mapped[str] = mapped_column(String(180), default="")
    product: Mapped[str] = mapped_column(String(220), default="")
    cves: Mapped[list] = mapped_column(JSON, default=list)
    affected_products: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_updated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    keV_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    findings: Mapped[list["Finding"]] = relationship(back_populates="advisory")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("asset_id", "advisory_id", name="uq_finding_asset_advisory"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    advisory_id: Mapped[int] = mapped_column(ForeignKey("advisories.id"), index=True)
    applicability: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(48), default="requires_review", index=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(32), default="pending")
    decision_rationale: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(160), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    asset: Mapped[Asset] = relationship(back_populates="findings")
    advisory: Mapped[Advisory] = relationship(back_populates="findings")
    tickets: Mapped[list["RemediationTicket"]] = relationship(back_populates="finding")
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(back_populates="finding")


class RemediationTicket(Base):
    __tablename__ = "remediation_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
    title: Mapped[str] = mapped_column(String(260))
    proposed_action: Mapped[str] = mapped_column(Text)
    assigned_to: Mapped[str] = mapped_column(String(160), default="Unassigned")
    planned_mitigation: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    decision_rationale: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(160), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finding: Mapped[Finding] = relationship(back_populates="tickets")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("remediation_tickets.id"), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(240))
    reference: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    recorded_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    verified_by: Mapped[str] = mapped_column(String(160), default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finding: Mapped[Finding] = relationship(back_populates="evidence_records")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(160))
    actor_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    source_name: Mapped[str] = mapped_column(String(120))
    etag: Mapped[str] = mapped_column(String(500), default="")
    last_modified: Mapped[str] = mapped_column(String(120), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="success")
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text, default="")
