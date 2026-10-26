import csv
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.services.matching import assess, evaluate_constraint

ROOT = Path(__file__).resolve().parents[2]


def fixture_rows():
    with (ROOT / "data/fixtures/cedar_valley_inventory.csv").open(encoding="utf-8", newline="") as handle:
        assets = list(csv.DictReader(handle))
    advisories = json.loads((ROOT / "data/fixtures/advisories.json").read_text(encoding="utf-8"))
    return {
        a["asset_id"]: SimpleNamespace(**{**a, "last_verified": date.fromisoformat(a["last_verified"])})
        for a in assets
    }, {a["external_id"]: SimpleNamespace(**a) for a in advisories}


def test_labeled_applicability_cases():
    assets, advisories = fixture_rows()
    actual = {}
    with (ROOT / "data/fixtures/labeled_cases.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            actual[(row["asset_id"], row["advisory_id"])] = assess(
                assets[row["asset_id"]],
                advisories[row["advisory_id"]],
                duplicate_candidate=row["asset_id"] in {"CV-HMI-008", "CV-HMI-009"},
                today=date(2026, 10, 26),
            )["applicability"]
    assert len(actual) == 14
    assert actual == {
        ("CV-HMI-001", "ICSA-24-226-06"): "applicable",
        ("CV-HMI-002", "ICSA-24-226-06"): "not_applicable",
        ("CV-HMI-003", "ICSA-24-226-06"): "applicable",
        ("CV-HMI-004", "ICSA-24-226-06"): "not_applicable",
        ("CV-HMI-005", "ICSA-24-226-06"): "requires_manual_verification",
        ("CV-HMI-006", "ICSA-24-226-06"): "requires_manual_verification",
        ("CV-HMI-007", "ICSA-24-226-06"): "requires_manual_verification",
        ("CV-HMI-008", "ICSA-24-226-06"): "requires_manual_verification",
        ("CV-HMI-009", "ICSA-24-226-06"): "requires_manual_verification",
        ("CV-OPT-010", "ICSA-24-256-24"): "applicable",
        ("CV-OPT-011", "ICSA-24-256-24"): "not_applicable",
        ("CV-APP-012", "ICSA-24-284-15"): "applicable",
        ("CV-APP-013", "ICSA-24-284-15"): "not_applicable",
        ("CV-OPT-014", "ICSA-24-256-24"): "requires_manual_verification",
    }


def test_nvd_range_constraints_are_conjunctive():
    assets, advisories = fixture_rows()
    advisory = SimpleNamespace(
        **{
            "external_id": "NVD:CVE-2026-1111",
            "vendor": "Rockwell Automation",
            "product": "Pavilion8",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2026-1111",
            "source_excerpt": "versions 5.10 to 5.20",
            "affected_products": [
                {
                    "product": "Pavilion8",
                    "constraints": [
                        {"operator": "gte", "version": "5.10", "raw": "version >= 5.10"},
                        {"operator": "lt", "version": "5.20", "raw": "version < 5.20"},
                    ],
                }
            ],
        }
    )
    match = assess(assets["CV-OPT-010"], advisory, today=date(2026, 10, 26))
    assert match["applicability"] == "applicable"
    outside = SimpleNamespace(**{**assets["CV-OPT-011"].__dict__, "firmware_version": "5.20"})
    assert assess(outside, advisory, today=date(2026, 10, 26))["applicability"] == "not_applicable"


def test_version_parser_abstains_on_suffix_and_respects_boundaries():
    assert (
        evaluate_constraint("5.20", {"operator": "lt", "version": "5.20", "raw": "prior to V5.20"})[0]
        is False
    )
    assert (
        evaluate_constraint("5.19", {"operator": "lt", "version": "5.20", "raw": "prior to V5.20"})[0] is True
    )
    assert evaluate_constraint("release-5.19-hotfix", {"operator": "lt", "version": "5.20"})[0] is None


def test_compound_nvd_configuration_abstains_for_engineering_review():
    assets, _ = fixture_rows()
    advisory = SimpleNamespace(
        **{
            "external_id": "NVD:CVE-2026-2222",
            "vendor": "Rockwell Automation",
            "product": "FactoryTalk View Site Edition",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2026-2222",
            "source_excerpt": "compound configuration",
            "affected_products": [
                {
                    "product": "FactoryTalk View SE",
                    "constraints": [{"operator": "eq", "version": "13.0", "raw": "version 13.0"}],
                    "configuration_supported": False,
                }
            ],
        }
    )
    result = assess(assets["CV-HMI-001"], advisory, today=date(2026, 10, 26))
    assert result["applicability"] == "requires_manual_verification"
    assert "compound or negated" in result["reasons"][0]


def test_missing_model_abstains_even_when_version_is_known():
    assets, advisories = fixture_rows()
    asset = SimpleNamespace(**{**assets["CV-HMI-001"].__dict__, "model": ""})
    result = assess(asset, advisories["ICSA-24-226-06"], today=date(2026, 10, 26))
    assert result["applicability"] == "requires_manual_verification"
    assert "model is missing" in result["reasons"][0]
