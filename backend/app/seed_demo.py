from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from app.core.db import Base, SessionLocal, engine
from app.models.entities import Advisory, Asset

ROOT = Path(__file__).resolve().parents[2]


def seed() -> tuple[int, int]:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        existing_assets = db.query(Asset).count()
        existing_advisories = db.query(Advisory).count()
        if existing_assets or existing_advisories:
            # Seeding is an initialization operation, never a reset operation.
            return existing_assets, existing_advisories
        with (ROOT / "data/fixtures/cedar_valley_inventory.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                db.add(
                    Asset(
                        asset_id=row["asset_id"],
                        vendor=row["vendor"],
                        product=row["product"],
                        model=row["model"],
                        firmware_version=row["firmware_version"],
                        equipment_type=row["equipment_type"],
                        site=row["site"],
                        criticality=row["criticality"],
                        review_owner=row["review_owner"],
                        last_verified=date.fromisoformat(row["last_verified"]),
                    )
                )
        fixtures = json.loads((ROOT / "data/fixtures/advisories.json").read_text(encoding="utf-8"))
        for item in fixtures:
            item["published_at"] = date.fromisoformat(item["published_at"])
            item["source_updated_at"] = date.fromisoformat(item["source_updated_at"])
            db.add(Advisory(**item))
        db.commit()
        return db.query(Asset).count(), db.query(Advisory).count()
    finally:
        db.close()


if __name__ == "__main__":
    asset_count, advisory_count = seed()
    print(f"Seeded fictional demo: {asset_count} assets and {advisory_count} source-linked advisories")
