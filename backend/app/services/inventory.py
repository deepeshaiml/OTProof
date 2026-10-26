from __future__ import annotations

from datetime import date
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

from app.models.entities import Asset


class InventoryRow(BaseModel):
    asset_id: str
    vendor: str = ""
    product: str = ""
    model: str = ""
    firmware_version: str = ""
    equipment_type: str = ""
    site: str = ""
    criticality: str = "Medium"
    review_owner: str = "Unassigned"
    last_verified: date | None = None

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 100:
            raise ValueError("asset_id must contain 1–100 characters")
        return value

    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, value: str) -> str:
        value = value.strip().title()
        if value not in {"Low", "Medium", "High", "Critical"}:
            raise ValueError("criticality must be Low, Medium, High, or Critical")
        return value


HEADER_ALIASES = {
    "asset identifier": "asset_id",
    "asset id": "asset_id",
    "asset_id": "asset_id",
    "vendor": "vendor",
    "manufacturer": "vendor",
    "product": "product",
    "product name": "product",
    "model": "model",
    "product model": "model",
    "firmware": "firmware_version",
    "firmware version": "firmware_version",
    "software version": "firmware_version",
    "version": "firmware_version",
    "equipment type": "equipment_type",
    "equipment_type": "equipment_type",
    "type": "equipment_type",
    "site": "site",
    "facility": "site",
    "location": "site",
    "business criticality": "criticality",
    "criticality": "criticality",
    "review owner": "review_owner",
    "owner": "review_owner",
    "last inventory verification date": "last_verified",
    "last verified": "last_verified",
    "last_verified": "last_verified",
}


def read_inventory(filename: str, content: bytes, max_bytes: int) -> list[InventoryRow]:
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)} MB upload limit")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        frame = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, nrows=10001)
    elif suffix in {"xlsx", "xlsm"}:
        if suffix == "xlsm":
            raise ValueError("Macro-enabled workbooks are not accepted")
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 5000 or sum(x.file_size for x in entries) > 50 * 1024 * 1024:
                    raise ValueError("Workbook expands beyond the inventory import limits")
                if any("vbaproject.bin" in x.filename.casefold() for x in entries):
                    raise ValueError("Macro-enabled workbooks are not accepted")
        except BadZipFile as exc:
            raise ValueError("The .xlsx file is not a valid Office workbook") from exc
        frame = pd.read_excel(
            BytesIO(content), engine="openpyxl", dtype=str, keep_default_na=False, nrows=10001
        )
    else:
        raise ValueError("Upload a .csv or .xlsx inventory")
    if len(frame) > 10000:
        raise ValueError("Inventory exceeds the 10,000-row MVP limit")
    normalized = {str(column).strip().casefold(): column for column in frame.columns}
    rename = {column: HEADER_ALIASES[key] for key, column in normalized.items() if key in HEADER_ALIASES}
    mapped = list(rename.values())
    duplicate_fields = sorted({field for field in mapped if mapped.count(field) > 1})
    if duplicate_fields:
        raise ValueError(f"Multiple upload columns map to the same field: {', '.join(duplicate_fields)}")
    frame = frame.rename(columns=rename)
    required_columns = {
        "asset_id",
        "vendor",
        "product",
        "model",
        "firmware_version",
        "equipment_type",
        "site",
        "criticality",
        "review_owner",
        "last_verified",
    }
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Required inventory columns missing: {', '.join(missing_columns)}")
    output: list[InventoryRow] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(frame.to_dict(orient="records"), start=2):
        values = {key: value for key, value in raw.items() if key in InventoryRow.model_fields}
        if isinstance(values.get("last_verified"), str):
            value = values["last_verified"].strip()
            values["last_verified"] = value or None
        try:
            row = InventoryRow.model_validate(values)
            if row.asset_id.casefold() in seen:
                raise ValueError(f"duplicate asset_id '{row.asset_id}' in upload")
            seen.add(row.asset_id.casefold())
            output.append(row)
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(f"row {index}: {exc}")
    if errors:
        raise ValueError("Inventory validation failed: " + "; ".join(errors[:20]))
    return output


def to_asset(row: InventoryRow) -> Asset:
    return Asset(
        asset_id=row.asset_id,
        vendor=row.vendor.strip(),
        product=row.product.strip(),
        model=row.model.strip(),
        firmware_version=row.firmware_version.strip(),
        equipment_type=row.equipment_type.strip(),
        site=row.site.strip(),
        criticality=row.criticality,
        review_owner=row.review_owner.strip() or "Unassigned",
        last_verified=row.last_verified,
    )
