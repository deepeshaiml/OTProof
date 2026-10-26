from __future__ import annotations

import re
from datetime import date
from typing import Any

VENDOR_ALIASES = {
    "rockwel automation": "rockwell automation",
    "rockwell auto": "rockwell automation",
    "allen bradley": "rockwell automation",
    "schneider electric": "schneider electric",
    "siemens ag": "siemens",
}
PRODUCT_ALIASES = {
    "factorytalk view se": "factorytalk view site edition",
    "factorytalk view site edition": "factorytalk view site edition",
    "factorytalk view me": "factorytalk view machine edition",
    "factorytalk view machine edition": "factorytalk view machine edition",
}


def normalize(value: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).split())


def canonical_vendor(value: str | None) -> str:
    key = normalize(value)
    return VENDOR_ALIASES.get(key, key)


def canonical_product(value: str | None) -> str:
    key = normalize(value)
    return PRODUCT_ALIASES.get(key, key)


def version_parts(value: str | None) -> tuple[int, ...] | None:
    """Parse conservative numeric dotted versions; suffixes are intentionally unsupported."""
    if not value:
        return None
    text = value.strip().casefold()
    text = re.sub(r"^(?:version|ver\.?|v)\s*", "", text)
    if not re.fullmatch(r"\d+(?:\.\d+){0,5}", text):
        return None
    return tuple(int(part) for part in text.split("."))


def _compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    a = left + (0,) * (width - len(left))
    b = right + (0,) * (width - len(right))
    return (a > b) - (a < b)


def evaluate_constraint(version: str, constraint: dict[str, Any]) -> tuple[bool | None, str]:
    actual = version_parts(version)
    boundary = version_parts(str(constraint.get("version", "")))
    operator = constraint.get("operator")
    raw = str(constraint.get("raw", ""))
    if actual is None or boundary is None:
        return None, "Version format is not supported by the deterministic parser."
    comparison = _compare_versions(actual, boundary)
    matches = {
        "eq": comparison == 0,
        "lt": comparison < 0,
        "lte": comparison <= 0,
        "gt": comparison > 0,
        "gte": comparison >= 0,
    }.get(operator)
    if matches is None:
        return None, "Advisory version statement has no supported deterministic operator."
    return (
        matches,
        f"{version} {'matches' if matches else 'does not match'} {raw or operator + ' ' + str(constraint.get('version'))}.",
    )


def _product_relation(asset_product: str, advisory_product: str) -> str:
    a = canonical_product(asset_product)
    b = canonical_product(advisory_product)
    if not a or not b:
        return "unknown"
    if a == b:
        return "same"
    if a.startswith("factorytalk view ") and b.startswith("factorytalk view "):
        return "different"
    if a in b or b in a:
        return "ambiguous"
    at = set(a.split())
    bt = set(b.split())
    if len(at & bt) >= 2:
        return "ambiguous"
    return "different"


def assess(
    asset: Any, advisory: Any, *, duplicate_candidate: bool = False, today: date | None = None
) -> dict[str, Any]:
    """Return a traceable deterministic result. Never use embedding/similarity scores as a verdict."""
    today = today or date.today()
    base_evidence = {
        "asset_id": asset.asset_id,
        "inventory_vendor": asset.vendor,
        "inventory_product": asset.product,
        "inventory_model": asset.model,
        "inventory_version": asset.firmware_version,
        "advisory_id": advisory.external_id,
        "advisory_vendor": advisory.vendor,
        "advisory_product": advisory.product,
        "source_url": advisory.source_url,
        "source_excerpt": advisory.source_excerpt,
    }
    reasons: list[str] = []

    if (
        canonical_vendor(asset.vendor)
        and canonical_vendor(advisory.vendor)
        and canonical_vendor(asset.vendor) != canonical_vendor(advisory.vendor)
    ):
        reasons.append(f"Vendor mismatch: inventory '{asset.vendor}' vs advisory '{advisory.vendor}'.")
        return {
            "applicability": "not_applicable",
            "status": "not_applicable",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    affected_products = advisory.affected_products or []
    candidate_products = [
        item
        for item in affected_products
        if _product_relation(asset.product, str(item.get("product", advisory.product))) == "same"
    ]
    product_relations = [
        _product_relation(asset.product, str(item.get("product", advisory.product)))
        for item in affected_products
    ]
    relation = (
        "same"
        if candidate_products
        else "ambiguous"
        if "ambiguous" in product_relations
        else _product_relation(asset.product, advisory.product)
    )
    if relation == "different":
        reasons.append(
            f"Product mismatch: inventory '{asset.product}' is distinct from advisory product '{advisory.product}'."
        )
        return {
            "applicability": "not_applicable",
            "status": "not_applicable",
            "reasons": reasons,
            "evidence": base_evidence,
        }
    if (
        not canonical_vendor(asset.vendor)
        or not canonical_product(asset.product)
        or relation in {"unknown", "ambiguous"}
    ):
        reasons.append(
            "Vendor or product identity is missing or ambiguous; engineering verification is required."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    if duplicate_candidate:
        reasons.append(
            "Possible duplicate inventory identity detected; confirm whether this is a separate physical asset."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    if not normalize(asset.model) or normalize(asset.model) in {"unknown", "unverified", "not known"}:
        reasons.append(
            "Asset model is missing or explicitly marked unknown; confirm the installed equipment identity before relying on this result."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    if asset.last_verified and (today - asset.last_verified).days > 180:
        reasons.append(
            f"Inventory was last verified {(today - asset.last_verified).days} days ago; confirm the installed version before relying on this result."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }
    if not asset.firmware_version:
        reasons.append(
            "Firmware/software version is missing; a product match alone cannot establish applicability."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    candidates = candidate_products
    if not candidates:
        reasons.append(
            "No structured affected-version constraint is available for this product; manual verification is required."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    if any(candidate.get("configuration_supported") is False for candidate in candidates):
        reasons.append(
            "The advisory has a compound or negated affected configuration that this MVP does not evaluate; engineering verification is required."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }

    outcomes: list[tuple[bool | None, str, dict[str, Any]]] = []
    for candidate in candidates:
        model_constraint = normalize(str(candidate.get("model", "")))
        if model_constraint and model_constraint not in normalize(asset.model):
            outcomes.append(
                (
                    False,
                    f"Inventory model '{asset.model}' does not match advisory model constraint '{candidate['model']}'.",
                    candidate,
                )
            )
            continue
        constraint_results: list[tuple[bool | None, str]] = []
        for constraint in candidate.get("constraints", []):
            result, explanation = evaluate_constraint(asset.firmware_version, constraint)
            constraint_results.append((result, explanation))
        if not constraint_results:
            outcomes.append(
                (
                    None,
                    "Affected product has no supported version statement; manual verification is required.",
                    candidate,
                )
            )
        elif any(result is False for result, _ in constraint_results):
            outcomes.append(
                (False, " and ".join(explanation for _, explanation in constraint_results), candidate)
            )
        elif all(result is True for result, _ in constraint_results):
            outcomes.append(
                (True, " and ".join(explanation for _, explanation in constraint_results), candidate)
            )
        else:
            outcomes.append(
                (None, " and ".join(explanation for _, explanation in constraint_results), candidate)
            )
    if not outcomes:
        reasons.append(
            "Affected product has no supported version statement; manual verification is required."
        )
        return {
            "applicability": "requires_manual_verification",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": base_evidence,
        }
    if any(result is True for result, _, _ in outcomes):
        selected = next(item for item in outcomes if item[0] is True)
        reasons.append(selected[1])
        evidence = {
            **base_evidence,
            "matched_constraint": selected[2],
            "matching_source_statement": selected[2].get("source_statement", ""),
        }
        return {
            "applicability": "applicable",
            "status": "requires_review",
            "reasons": reasons,
            "evidence": evidence,
        }
    if all(result is False for result, _, _ in outcomes):
        reasons.extend(explanation for _, explanation, _ in outcomes)
        return {
            "applicability": "not_applicable",
            "status": "not_applicable",
            "reasons": reasons,
            "evidence": base_evidence,
        }
    reasons.extend(explanation for _, explanation, _ in outcomes)
    reasons.append(
        "At least one version constraint could not be interpreted; engineering verification is required."
    )
    return {
        "applicability": "requires_manual_verification",
        "status": "requires_review",
        "reasons": reasons,
        "evidence": base_evidence,
    }
