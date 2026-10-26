import json
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app
from app.models.entities import Advisory, Asset, SourceSnapshot

ROOT = Path(__file__).resolve().parents[2]


def test_human_review_ticket_evidence_and_approver_verification(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    fixtures = json.loads((ROOT / "data/fixtures/advisories.json").read_text(encoding="utf-8"))
    with TestSession() as db:
        db.add(
            Asset(
                asset_id="API-HMI-1",
                vendor="Rockwell Automation",
                product="FactoryTalk View Site Edition",
                model="SE HMI",
                firmware_version="13.0",
                equipment_type="HMI",
                site="Synthetic site",
                criticality="High",
                review_owner="Engineer",
                last_verified=date(2026, 10, 20),
            )
        )
        item = fixtures[0]
        item["published_at"] = date.fromisoformat(item["published_at"])
        item["source_updated_at"] = date.fromisoformat(item["source_updated_at"])
        db.add(Advisory(**item))
        db.add(
            SourceSnapshot(
                source_url=f'{item["source_url"]}?view=1&label=%3Cscript%3E',
                source_name="CISA <b>ICS</b> test snapshot",
                etag='"demo-etag"',
                last_modified="Wed, 28 Aug 2024 00:00:00 GMT",
                fetched_at=datetime.now(UTC),
                sha256="a" * 64,
                status="success",
                payload="source payload intentionally omitted from report",
            )
        )
        db.commit()

    def override_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        assert client.post("/api/analyze").status_code == 401
        reviewer = {"Authorization": "Bearer demo-reviewer-token"}
        response = client.post("/api/analyze", headers=reviewer)
        assert response.status_code == 200, response.text
        finding = client.get("/api/findings").json()["items"][0]
        assert finding["applicability"] == "applicable"
        response = client.post(
            f"/api/findings/{finding['id']}/decision",
            headers=reviewer,
            json={
                "decision": "applicable",
                "rationale": "Confirmed the exact product and firmware against the source range.",
            },
        )
        assert response.status_code == 200
        engineer = {"Authorization": "Bearer demo-engineer-token"}
        response = client.post(
            f"/api/findings/{finding['id']}/tickets",
            headers=engineer,
            json={
                "proposed_action": "Schedule a vendor-approved software update after change review.",
                "assigned_to": "OT Engineer",
                "planned_mitigation": "Validate failover and process impact.",
                "due_date": "2026-12-01",
            },
        )
        assert response.status_code == 200
        ticket_id = response.json()["id"]
        approver = {"Authorization": "Bearer demo-approver-token"}
        assert (
            client.post(
                f"/api/tickets/{ticket_id}/decision",
                headers=engineer,
                json={
                    "decision": "approved",
                    "rationale": "Approved after safety and maintenance-window review.",
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/tickets/{ticket_id}/decision",
                headers=approver,
                json={
                    "decision": "approved",
                    "rationale": "Approved after safety and maintenance-window review.",
                },
            ).status_code
            == 200
        )
        response = client.post(
            f"/api/findings/{finding['id']}/evidence",
            headers=engineer,
            json={
                "evidence_type": "Change record",
                "label": "Simulated update record",
                "reference": "CHG-TEST-1",
                "notes": "Evidence simulated for test.",
                "content": "fictional evidence",
                "ticket_id": ticket_id,
            },
        )
        assert response.status_code == 200
        evidence_id = response.json()["id"]
        assert (
            client.post(
                f"/api/findings/{finding['id']}/verify",
                headers=engineer,
                json={"evidence_id": evidence_id, "rationale": "Evidence matches approved change record."},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/findings/{finding['id']}/verify",
                headers=approver,
                json={
                    "evidence_id": evidence_id,
                    "rationale": "Evidence matches approved change record and verification checks.",
                },
            ).status_code
            == 200
        )
        refreshed = client.get("/api/findings").json()["items"][0]
        assert refreshed["status"] == "verified_remediated"
        report = client.get("/api/report/assurance.json").json()
        assert report["summary"]["verified_remediated"] == 1
        assert len(report["audit_events"]) >= 5
        assert report["findings"][0]["source_published_at"] == "2024-08-13"
        assert report["findings"][0]["source_updated_at"] == "2024-08-29"
        assert report["findings"][0]["advisory_imported_at"]
        assert report["source_snapshots"][0]["sha256"] == "a" * 64
        assert "payload" not in report["source_snapshots"][0]
        exported_pdf = client.get("/api/report/assurance.pdf")
        assert exported_pdf.status_code == 200
        assert exported_pdf.content.startswith(b"%PDF")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
