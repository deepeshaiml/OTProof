from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AssetOut(ORMModel):
    id: int
    asset_id: str
    vendor: str
    product: str
    model: str
    firmware_version: str
    equipment_type: str
    site: str
    criticality: str
    review_owner: str
    last_verified: date | None


class AdvisoryOut(ORMModel):
    id: int
    external_id: str
    title: str
    source: str
    source_url: str
    vendor: str
    product: str
    cves: list
    affected_products: list
    description: str
    published_at: date | None
    source_updated_at: date | None
    imported_at: datetime


class FindingOut(ORMModel):
    id: int
    applicability: str
    status: str
    reasons: list
    evidence: dict
    decision: str
    decision_rationale: str
    decided_by: str
    created_at: datetime
    asset: AssetOut
    advisory: AdvisoryOut


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(applicable|not_applicable)$")
    rationale: str = Field(min_length=12, max_length=2000)


class TicketCreate(BaseModel):
    proposed_action: str = Field(min_length=5, max_length=4000)
    assigned_to: str = Field(min_length=2, max_length=160)
    planned_mitigation: str = Field(default="", max_length=2000)
    due_date: date | None = None


class TicketDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    rationale: str = Field(min_length=12, max_length=2000)


class EvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=2, max_length=240)
    reference: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=4000)
    content: str = Field(default="", max_length=20000)
    ticket_id: int | None = None


class VerificationIn(BaseModel):
    evidence_id: int
    rationale: str = Field(min_length=12, max_length=2000)


ExtractedLabel = Annotated[str, Field(min_length=1, max_length=600)]
ExtractedDetail = Annotated[str, Field(min_length=1, max_length=1500)]
ExtractedCVE = Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,8}$")]


class AIExtraction(BaseModel):
    vendor: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    products: list[ExtractedLabel] = Field(default_factory=list, max_length=100)
    cves: list[ExtractedCVE] = Field(default_factory=list, max_length=100)
    affected_version_statements: list[ExtractedDetail] = Field(default_factory=list, max_length=100)
    mitigations: list[ExtractedDetail] = Field(default_factory=list, max_length=50)
    summary: str = Field(default="", max_length=3000)
    source_quotes: list[ExtractedDetail] = Field(default_factory=list, max_length=50)
