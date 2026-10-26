from __future__ import annotations

import csv
import json
import time
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.services.matching import assess, canonical_product, canonical_vendor

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 26)
LABELS = ("applicable", "not_applicable", "requires_manual_verification")


def load_fixtures():
    with (ROOT / "data/fixtures/cedar_valley_inventory.csv").open(encoding="utf-8", newline="") as handle:
        assets = list(csv.DictReader(handle))
    advisories = json.loads((ROOT / "data/fixtures/advisories.json").read_text(encoding="utf-8"))
    asset_map = {
        item["asset_id"]: SimpleNamespace(
            **{
                **item,
                "last_verified": date.fromisoformat(item["last_verified"]) if item["last_verified"] else None,
            }
        )
        for item in assets
    }
    advisory_map = {item["external_id"]: SimpleNamespace(**item) for item in advisories}
    return assets, asset_map, advisory_map


def duplicate_fingerprints(assets: list[dict]) -> set[tuple[str, ...]]:
    fingerprints = [
        (
            canonical_vendor(a["vendor"]),
            canonical_product(a["product"]),
            a["model"].casefold().strip(),
            a["firmware_version"].casefold().strip(),
            a["site"].casefold().strip(),
        )
        for a in assets
    ]
    counts = Counter(fingerprints)
    return {fingerprint for fingerprint, count in counts.items() if count > 1}


def main() -> None:
    assets, asset_map, advisory_map = load_fixtures()
    duplicate_keys = duplicate_fingerprints(assets)
    expected_rows = list(csv.DictReader((ROOT / "data/fixtures/labeled_cases.csv").open(encoding="utf-8")))
    measured_cases = []
    for row in expected_rows:
        asset = asset_map[row["asset_id"]]
        fingerprint = (
            canonical_vendor(asset.vendor),
            canonical_product(asset.product),
            asset.model.casefold().strip(),
            asset.firmware_version.casefold().strip(),
            asset.site.casefold().strip(),
        )
        result = assess(
            asset,
            advisory_map[row["advisory_id"]],
            duplicate_candidate=fingerprint in duplicate_keys,
            today=TODAY,
        )
        measured_cases.append(
            {
                "asset_id": row["asset_id"],
                "advisory_id": row["advisory_id"],
                "expected": row["expected"],
                "actual": result["applicability"],
                "correct": result["applicability"] == row["expected"],
                "source_traceable": bool(
                    result["evidence"].get("source_url")
                    and result["evidence"].get("source_excerpt")
                    and result["evidence"].get("advisory_id")
                ),
                "reason": result["reasons"],
                "source_url": result["evidence"].get("source_url"),
            }
        )

    tp = sum(c["expected"] == c["actual"] == "applicable" for c in measured_cases)
    fp = sum(c["expected"] != "applicable" and c["actual"] == "applicable" for c in measured_cases)
    fn = sum(c["expected"] == "applicable" and c["actual"] != "applicable" for c in measured_cases)
    positives = sum(c["expected"] == "applicable" for c in measured_cases)
    manual_expected = sum(c["expected"] == "requires_manual_verification" for c in measured_cases)
    manual_correct = sum(
        c["expected"] == c["actual"] == "requires_manual_verification" for c in measured_cases
    )
    definite_expected = len(measured_cases) - manual_expected
    correct_labels = sum(c["correct"] for c in measured_cases)

    full_start = time.perf_counter()
    pairs = 0
    for asset_row in assets:
        asset = asset_map[asset_row["asset_id"]]
        fingerprint = (
            canonical_vendor(asset.vendor),
            canonical_product(asset.product),
            asset.model.casefold().strip(),
            asset.firmware_version.casefold().strip(),
            asset.site.casefold().strip(),
        )
        for advisory in advisory_map.values():
            assess(
                asset,
                advisory,
                duplicate_candidate=fingerprint in duplicate_keys,
                today=TODAY,
            )
            pairs += 1
    elapsed_ms = (time.perf_counter() - full_start) * 1000

    result = {
        "evaluation_date": TODAY.isoformat(),
        "dataset": {
            "inventory": "Fictional Cedar Valley Water Utility",
            "assets": len(assets),
            "advisories": len(advisory_map),
            "labeled_pairs": len(measured_cases),
            "full_cross_product_pairs_benchmarked": pairs,
            "labels": dict(Counter(row["expected"] for row in measured_cases)),
        },
        "deterministic_applicability": {
            "applicable_precision": tp / (tp + fp) if tp + fp else None,
            "applicable_recall": tp / positives if positives else None,
            "applicable_false_negative_rate": fn / positives if positives else None,
            "labeled_case_accuracy": correct_labels / len(measured_cases) if measured_cases else None,
            "confusion_matrix": {
                expected: {
                    actual: sum(
                        row["expected"] == expected and row["actual"] == actual for row in measured_cases
                    )
                    for actual in LABELS
                }
                for expected in LABELS
            },
            "uncertainty": {
                "manual_review_cases_expected": manual_expected,
                "manual_review_cases_abstained_correctly": manual_correct,
                "uncertainty_recall": manual_correct / manual_expected if manual_expected else None,
                "definitive_cases_not_abstained": sum(
                    row["expected"] != "requires_manual_verification"
                    and row["actual"] != "requires_manual_verification"
                    for row in measured_cases
                ),
                "definitive_case_coverage": (
                    sum(
                        row["expected"] != "requires_manual_verification"
                        and row["actual"] != "requires_manual_verification"
                        for row in measured_cases
                    )
                    / definite_expected
                    if definite_expected
                    else None
                ),
            },
            "source_traceability": {
                "pairs_with_advisory_id_url_and_excerpt": sum(row["source_traceable"] for row in measured_cases),
                "pairs_total": len(measured_cases),
            },
            "timing": {
                "method": "Single in-process pass using time.perf_counter; includes Python assess calls only.",
                "full_cross_product_pairs": pairs,
                "elapsed_ms": round(elapsed_ms, 3),
                "milliseconds_per_pair": round(elapsed_ms / pairs, 4) if pairs else None,
                "human_review_time": "Not measured; no operator time study was run.",
            },
        },
        "ai_extraction": {
            "status": "not_run",
            "reason": "No local Ollama model inference was run; no extraction accuracy claim is made.",
            "baseline": "CISA HTML/CSAF deterministic normalization is covered by parser unit tests and source-linked fixtures.",
        },
        "security_and_availability": {
            "prompt_injection": "Tested: advisory instructions remain untrusted and unsupported extracted values are rejected.",
            "upload_validation": "Tested: duplicate asset IDs and macro-enabled workbook inputs are rejected.",
            "feed_outage": "Tested: stale persisted source snapshot is served when refresh fails.",
            "scope": "Local unit/API tests and in-process timing only; not a penetration test or production performance study.",
        },
        "cases": measured_cases,
    }
    output = ROOT / "reports/evaluation_metrics.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    main()
