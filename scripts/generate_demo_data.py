from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fixtures" / "cedar_valley_inventory.csv"
LABELS = ROOT / "data" / "fixtures" / "labeled_cases.csv"
TODAY = date(2026, 10, 26)

FIELDS = [
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
]


def main() -> None:
    rows = [
        [
            "CV-HMI-001",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "13.0.0",
            "HMI",
            "Cedar Valley WTP",
            "Critical",
            "A. Rahman",
            (TODAY - timedelta(days=20)).isoformat(),
        ],
        [
            "CV-HMI-002",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "14.0",
            "HMI",
            "Cedar Valley WTP",
            "High",
            "A. Rahman",
            (TODAY - timedelta(days=10)).isoformat(),
        ],
        [
            "CV-HMI-003",
            "Rockwel Automation",
            "FactoryTalk View SE",
            "SE Operator Station",
            "13.0",
            "HMI",
            "Cedar Valley WTP",
            "High",
            "A. Rahman",
            (TODAY - timedelta(days=33)).isoformat(),
        ],
        [
            "CV-HMI-004",
            "Rockwell Automation",
            "FactoryTalk View Machine Edition",
            "PanelView Plus 7",
            "13.0",
            "HMI",
            "East Pump Station",
            "Medium",
            "M. Patel",
            (TODAY - timedelta(days=14)).isoformat(),
        ],
        [
            "CV-HMI-005",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "",
            "HMI",
            "North Reservoir",
            "High",
            "A. Rahman",
            (TODAY - timedelta(days=14)).isoformat(),
        ],
        [
            "CV-HMI-006",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "Unknown",
            "13.0",
            "HMI",
            "North Reservoir",
            "High",
            "A. Rahman",
            (TODAY - timedelta(days=12)).isoformat(),
        ],
        [
            "CV-HMI-007",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "13.0",
            "HMI",
            "East Pump Station",
            "High",
            "M. Patel",
            "2024-08-01",
        ],
        [
            "CV-HMI-008",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "13.0",
            "HMI",
            "South Booster Station",
            "High",
            "M. Patel",
            (TODAY - timedelta(days=22)).isoformat(),
        ],
        [
            "CV-HMI-009",
            "Rockwell Automation",
            "FactoryTalk View Site Edition",
            "SE Operator Station",
            "13.0",
            "HMI",
            "South Booster Station",
            "High",
            "M. Patel",
            (TODAY - timedelta(days=22)).isoformat(),
        ],
        [
            "CV-OPT-010",
            "Rockwell Automation",
            "Pavilion8",
            "Pavilion8 MPC",
            "5.19",
            "Optimization server",
            "Cedar Valley WTP",
            "High",
            "S. Khan",
            (TODAY - timedelta(days=15)).isoformat(),
        ],
        [
            "CV-OPT-011",
            "Rockwell Automation",
            "Pavilion8",
            "Pavilion8 MPC",
            "5.20",
            "Optimization server",
            "East Pump Station",
            "Medium",
            "S. Khan",
            (TODAY - timedelta(days=15)).isoformat(),
        ],
        [
            "CV-APP-012",
            "Rockwell Automation",
            "DataMosaix Private Cloud",
            "DataMosaix node",
            "7.07",
            "Application server",
            "Cedar Valley WTP",
            "High",
            "S. Khan",
            (TODAY - timedelta(days=18)).isoformat(),
        ],
        [
            "CV-APP-013",
            "Rockwell Automation",
            "DataMosaix Private Cloud",
            "DataMosaix node",
            "7.08",
            "Application server",
            "Cedar Valley WTP",
            "Medium",
            "S. Khan",
            (TODAY - timedelta(days=18)).isoformat(),
        ],
        [
            "CV-OPT-014",
            "Rockwell Automation",
            "Pavilion8",
            "Pavilion8 MPC",
            "release-5.19-hotfix",
            "Optimization server",
            "North Reservoir",
            "Medium",
            "S. Khan",
            (TODAY - timedelta(days=12)).isoformat(),
        ],
        [
            "CV-PLC-015",
            "Siemens",
            "SIMATIC S7-1500",
            "CPU 1515-2 PN",
            "2.9.4",
            "PLC",
            "Cedar Valley WTP",
            "Critical",
            "J. Lee",
            (TODAY - timedelta(days=8)).isoformat(),
        ],
    ]
    randomizer = random.Random(20261026)
    vendors = [
        "Siemens",
        "Schneider Electric",
        "Rockwell Automation",
        "Phoenix Contact",
        "Mitsubishi Electric",
        "Emerson",
    ]
    products = {
        "Siemens": [
            ("SIMATIC S7-1500", "CPU 1515-2 PN", "PLC"),
            ("SCALANCE XC", "XC208 switch", "Network gateway"),
            ("WinCC Unified", "Unified PC Runtime", "SCADA/HMI"),
        ],
        "Schneider Electric": [
            ("Modicon M340", "BMX P34 CPU", "PLC"),
            ("EcoStruxure Control Expert", "Engineering workstation", "Engineering station"),
        ],
        "Rockwell Automation": [
            ("CompactLogix 5380", "5069-L320ER", "PLC"),
            ("FactoryTalk Historian", "SE Historian", "Historian"),
        ],
        "Phoenix Contact": [("PLCnext Control", "AXC F 2152", "PLC")],
        "Mitsubishi Electric": [("MELSEC iQ-R", "R04CPU", "PLC")],
        "Emerson": [("DeltaV", "PK Controller", "DCS controller")],
    }
    versions = ["1.2.3", "2.9.4", "3.1", "4.12", "12.0", "14.2.1", "V2.4.7", "R1.8"]
    sites = [
        "Cedar Valley WTP",
        "East Pump Station",
        "North Reservoir",
        "South Booster Station",
        "West Wellfield",
    ]
    owners = ["A. Rahman", "M. Patel", "J. Lee", "S. Khan", "K. Hassan"]
    criticalities = ["Critical", "High", "Medium", "Low"]
    while len(rows) < 80:
        idx = len(rows) + 1
        vendor = randomizer.choice(vendors)
        product, model, equipment_type = randomizer.choice(products[vendor])
        days_old = randomizer.choice([7, 22, 63, 120, 240, 390])
        rows.append(
            [
                f"CV-OT-{idx:03d}",
                vendor,
                product,
                model,
                "" if idx % 23 == 0 else randomizer.choice(versions),
                equipment_type,
                randomizer.choice(sites),
                randomizer.choice(criticalities),
                randomizer.choice(owners),
                (TODAY - timedelta(days=days_old)).isoformat(),
            ]
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(rows)

    labels = [
        (
            "CV-HMI-001",
            "ICSA-24-226-06",
            "applicable",
            "Exact affected product and version (13.0.0 normalizes to 13.0).",
        ),
        (
            "CV-HMI-002",
            "ICSA-24-226-06",
            "not_applicable",
            "Same product, version outside the advisory's exact 13.0 statement.",
        ),
        (
            "CV-HMI-003",
            "ICSA-24-226-06",
            "applicable",
            "Curated deterministic vendor alias maps Rockwel Automation to Rockwell Automation.",
        ),
        (
            "CV-HMI-004",
            "ICSA-24-226-06",
            "not_applicable",
            "Same vendor but explicitly different FactoryTalk product.",
        ),
        (
            "CV-HMI-005",
            "ICSA-24-226-06",
            "requires_manual_verification",
            "Firmware missing; product identity alone cannot establish applicability.",
        ),
        (
            "CV-HMI-006",
            "ICSA-24-226-06",
            "requires_manual_verification",
            "Model explicitly recorded as Unknown.",
        ),
        (
            "CV-HMI-007",
            "ICSA-24-226-06",
            "requires_manual_verification",
            "Inventory verification date is older than 180 days.",
        ),
        (
            "CV-HMI-008",
            "ICSA-24-226-06",
            "requires_manual_verification",
            "Possible duplicate physical asset with CV-HMI-009.",
        ),
        (
            "CV-HMI-009",
            "ICSA-24-226-06",
            "requires_manual_verification",
            "Possible duplicate physical asset with CV-HMI-008.",
        ),
        (
            "CV-OPT-010",
            "ICSA-24-256-24",
            "applicable",
            "Version 5.19 is below the published 5.20 upper boundary.",
        ),
        (
            "CV-OPT-011",
            "ICSA-24-256-24",
            "not_applicable",
            "Version 5.20 is excluded by the strict prior-to boundary.",
        ),
        (
            "CV-APP-012",
            "ICSA-24-284-15",
            "applicable",
            "Version 7.07 is included by the published and-prior boundary.",
        ),
        (
            "CV-APP-013",
            "ICSA-24-284-15",
            "not_applicable",
            "Version 7.08 is beyond the published 7.07 upper boundary.",
        ),
        (
            "CV-OPT-014",
            "ICSA-24-256-24",
            "requires_manual_verification",
            "Firmware text contains an unsupported hotfix suffix.",
        ),
    ]
    with LABELS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["asset_id", "advisory_id", "expected", "label_rationale"])
        writer.writerows(labels)


if __name__ == "__main__":
    main()
