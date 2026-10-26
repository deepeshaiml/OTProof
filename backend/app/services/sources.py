from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from datetime import datetime as _datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Advisory, SourceSnapshot, utcnow

CISA_ICS_RSS = "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml"
CISA_KEV_JSON = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD_CVE_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
VENDOR_HOSTS = {
    "rockwellautomation.com": "Rockwell Automation",
    "se.com": "Schneider Electric",
    "schneider-electric.com": "Schneider Electric",
    "siemens.com": "Siemens",
    "cisco.com": "Cisco",
    "security.cisco.com": "Cisco",
}


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4", "br", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4", "br", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


def visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return re.sub(r"\n\s*\n+", "\n", "\n".join(parser.parts))


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.current: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = (dict(attrs).get("href", ""), [])

    def handle_data(self, data):
        if self.current is not None:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append((self.current[0], " ".join(self.current[1]).strip()))
            self.current = None


def _cisa_csaf_download(html: str) -> str | None:
    parser = _Links()
    parser.feed(html)
    pattern = re.compile(
        r"/cisagov/CSAF/blob/(develop|main)/csaf_files/OT/white/(\d{4})/(icsa-\d{2}-\d{3}-\d{2,3})(?:_test)?\.json"
    )
    for href, label in parser.links:
        parsed = urlparse(href)
        match = pattern.fullmatch(parsed.path)
        if parsed.hostname == "github.com" and label.casefold() == "view csaf" and match:
            branch, year, slug = match.groups()
            return f"https://raw.githubusercontent.com/cisagov/CSAF/{branch}/csaf_files/OT/white/{year}/{slug}.json"
    return None


def _csaf_constraint(statement: str) -> dict | None:
    match = re.search(r"(?:vers:[^/]+/)?(>=|<=|>|<|=)\s*[vV]?([0-9]+(?:\.[0-9]+){0,5})", statement)
    if not match:
        return None
    operator = {">=": "gte", "<=": "lte", ">": "gt", "<": "lt", "=": "eq"}[match.group(1)]
    return {"operator": operator, "version": match.group(2), "raw": statement.strip()}


def parse_cisa_csaf(url: str, document: dict, published_at: date | None = None) -> dict:
    doc = document.get("document", {})
    tracking = doc.get("tracking", {})
    advisory_id = tracking.get("id", "").upper()
    product_map: dict[str, dict] = {}

    def visit(nodes: list[dict], ancestors: list[dict]) -> None:
        for node in nodes:
            path = ancestors + [node]
            product = node.get("product")
            if product and product.get("product_id"):
                vendor = next((x.get("name", "") for x in path if x.get("category") == "vendor"), "")
                product_branch = next(
                    (x.get("name", "") for x in reversed(path) if x.get("category") == "product_name"), ""
                )
                range_branch = next(
                    (
                        x.get("name", "")
                        for x in reversed(path)
                        if x.get("category") == "product_version_range"
                    ),
                    "",
                )
                helper = product.get("product_identification_helper", {})
                model_numbers = helper.get("model_numbers", [])
                product_map[product["product_id"]] = {
                    "vendor": vendor,
                    "product": product_branch or product.get("name", ""),
                    "model": model_numbers[0] if len(model_numbers) == 1 else "",
                    "version_range": range_branch,
                    "product_name": product.get("name", ""),
                }
            visit(node.get("branches", []), path)

    visit(document.get("product_tree", {}).get("branches", []), [])
    affected_ids: set[str] = set()
    cves: list[str] = []
    descriptions: list[str] = []
    for vulnerability in document.get("vulnerabilities", []):
        if vulnerability.get("cve"):
            cves.append(vulnerability["cve"].upper())
        affected_ids.update(vulnerability.get("product_status", {}).get("known_affected", []))
        for note in vulnerability.get("notes", []):
            if note.get("category") in {"summary", "description", "general"} and note.get("text"):
                descriptions.append(note["text"])

    affected_products = []
    for product_id in sorted(affected_ids):
        item = product_map.get(product_id)
        if not item:
            continue
        statement = item["version_range"] or item["product_name"]
        constraint = _csaf_constraint(statement)
        affected_products.append(
            {
                "product": item["product"],
                "model": item["model"],
                "constraints": [constraint] if constraint else [],
                "source_statement": f"{item['product_name']} — {statement}".strip(" —"),
                "product_id": product_id,
            }
        )
    vendor = next(
        (
            product_map[x]["vendor"]
            for x in sorted(affected_ids)
            if x in product_map and product_map[x]["vendor"]
        ),
        "",
    )
    products = list(dict.fromkeys(item["product"] for item in affected_products if item["product"]))
    initial_release = _as_date(tracking.get("initial_release_date"))
    current_release = _as_date(tracking.get("current_release_date"))
    notes = doc.get("notes", [])
    summary = next(
        (note.get("text", "") for note in notes if note.get("category") in {"summary", "description"}), ""
    )
    excerpt = "\n".join(dict.fromkeys(item["source_statement"] for item in affected_products))
    if descriptions:
        excerpt = f"{excerpt}\n" + "\n".join(descriptions[:8])
    title = doc.get("title", advisory_id)
    return {
        "external_id": advisory_id,
        "title": title,
        "source": "CISA ICS",
        "source_url": url,
        "vendor": vendor,
        "product": products[0] if len(products) == 1 else title,
        "cves": sorted(set(cves)),
        "affected_products": affected_products,
        "description": summary or " ".join(descriptions[:4]),
        "source_excerpt": excerpt[:20000],
        "published_at": published_at or initial_release,
        "source_updated_at": current_release,
    }


def fetch_source(
    db: Session, url: str, source_name: str, *, force: bool = False
) -> tuple[str, dict[str, str]]:
    """Conditional HTTP cache with bounded retries; stale source payload survives outages."""
    row = db.query(SourceSnapshot).filter_by(source_url=url).one_or_none()
    ttl = get_settings().source_cache_ttl_seconds
    if row and not force and (utcnow() - _aware(row.fetched_at)).total_seconds() < ttl and row.payload:
        return row.payload, {
            "cache": "hit",
            "fetched_at": row.fetched_at.isoformat(),
            "last_modified": row.last_modified,
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OTProof/0.1; +https://localhost/)",
        "Accept": "application/rss+xml, application/json, text/html;q=0.9, */*;q=0.8",
    }
    if row and row.etag:
        headers["If-None-Match"] = row.etag
    if row and row.last_modified:
        headers["If-Modified-Since"] = row.last_modified
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
            initial = urlparse(url)
            final = urlparse(str(response.url))
            initial_vendor = _vendor_name(initial.hostname or "")
            if initial_vendor and _vendor_name(final.hostname or "") != initial_vendor:
                raise ValueError("Vendor bulletin redirect left the approved vendor domain")
            if response.status_code == 304 and row and row.payload:
                row.fetched_at = utcnow()
                db.commit()
                return row.payload, {
                    "cache": "not_modified",
                    "fetched_at": row.fetched_at.isoformat(),
                    "last_modified": row.last_modified,
                }
            if response.status_code in {429, 503}:
                retry = response.headers.get("Retry-After", "")
                delay = min(float(retry), 5) if retry.isdigit() else 1.5 * (attempt + 1)
                if attempt < 2:
                    time.sleep(delay)
                    continue
            response.raise_for_status()
            if len(response.content) > 20 * 1024 * 1024:
                raise ValueError("Source response exceeds 20 MB limit")
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                payload = response.text
            else:
                payload = response.text
            if row:
                row.etag = response.headers.get("ETag", "")
                row.last_modified = response.headers.get("Last-Modified", "")
                row.fetched_at = utcnow()
                row.sha256 = sha256(response.content).hexdigest()
                row.status = "success"
                row.payload = payload
            else:
                row = SourceSnapshot(
                    source_url=url,
                    source_name=source_name,
                    etag=response.headers.get("ETag", ""),
                    last_modified=response.headers.get("Last-Modified", ""),
                    fetched_at=utcnow(),
                    sha256=sha256(response.content).hexdigest(),
                    status="success",
                    payload=payload,
                )
                db.add(row)
            db.commit()
            return payload, {
                "cache": "refreshed",
                "fetched_at": row.fetched_at.isoformat(),
                "last_modified": row.last_modified,
            }
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    if row and row.payload:
        row.status = "stale_fallback"
        db.commit()
        return row.payload, {
            "cache": "stale_fallback",
            "fetched_at": row.fetched_at.isoformat(),
            "error": str(last_error),
        }
    raise RuntimeError(f"Source unavailable and no cached copy exists: {last_error}")


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError, OverflowError):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _version_constraint(statement: str) -> dict | None:
    text = statement.strip()
    patterns = [
        (r"\b(?:all\s+)?versions?\s+prior\s+to\s+[vV]?([\d.]+)", "lt"),
        (r"\bprior\s+to\s+[vV]?([\d.]+)", "lt"),
        (r"\b(?:versions?\s+)?[vV]?([\d.]+)\s+and\s+prior\b", "lte"),
        (r"\bversion\s+[vV]?([\d.]+)\s+and\s+prior\b", "lte"),
        (r"\bversion\s+[vV]?([\d.]+)\b", "eq"),
        (r"\bversions?\s+[vV]?([\d.]+)\s+and\s+earlier\b", "lte"),
    ]
    for pattern, operator in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            version = match.group(1).rstrip(".")
            return {"operator": operator, "version": version, "raw": text}
    return None


def parse_cisa_advisory_page(url: str, html: str, published_at: date | None = None) -> dict:
    text = visible_text(html)
    external = re.search(r"ICSA-\d{2}-\d{3}-\d{2,3}", text, re.I)
    advisory_id = external.group(0).upper() if external else url.rstrip("/").split("/")[-1].upper()
    vendor_match = re.search(r"\bVendor\s*:?\s*([^\n]+)", text, re.I)
    product_match = re.search(r"\bEquipment\s*:?\s*([^\n]+)", text, re.I)
    title_match = re.search(r"ICS Advisory\s+([^\n]+)", text, re.I)
    revised_match = re.search(r"(?:Last Revised|Release Date)\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", text, re.I)
    vendor = vendor_match.group(1).strip(" :") if vendor_match else ""
    product = product_match.group(1).strip(" :") if product_match else ""
    title = title_match.group(1).strip() if title_match else product or advisory_id
    section_match = re.search(
        r"3\.1\s+AFFECTED PRODUCTS(.*?)(?:3\.2\s+VULNERABILITY|3\.2\s+Vulnerability|BACKGROUND)",
        text,
        re.I | re.S,
    )
    section = section_match.group(1).strip() if section_match else ""
    affected: list[dict] = []
    if section:
        for line in section.splitlines():
            line = line.strip(" •\t")
            if not line:
                continue
            if ":" in line:
                product_name, statement = line.split(":", 1)
            else:
                product_name, statement = product, line
            constraint = _version_constraint(statement)
            if product_name.strip() and constraint:
                affected.append(
                    {"product": product_name.strip(), "constraints": [constraint], "source_statement": line}
                )
    cves = sorted(set(re.findall(r"\bCVE-\d{4}-\d{4,8}\b", text, re.I)))
    if not product and affected:
        product = affected[0]["product"]
    excerpt = section[:10000] or text[:10000]
    try:
        source_updated = (
            _datetime.strptime(revised_match.group(1), "%B %d, %Y").date() if revised_match else None
        )
    except ValueError:
        source_updated = None
    return {
        "external_id": advisory_id,
        "title": title,
        "source": "CISA ICS",
        "source_url": url,
        "vendor": vendor,
        "product": product,
        "cves": cves,
        "affected_products": affected,
        "description": " ".join(text.split())[:2000],
        "source_excerpt": excerpt,
        "published_at": published_at,
        "source_updated_at": source_updated,
    }


def cisa_feed_items(xml_text: str, limit: int = 20) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", default="").strip()
        url = item.findtext("link", default="").strip()
        if not url:
            continue
        items.append({"title": title, "url": url, "published_at": _as_date(item.findtext("pubDate"))})
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//a:entry", ns)[:limit]:
            link = item.find("a:link", ns)
            url = link.attrib.get("href", "") if link is not None else ""
            items.append(
                {
                    "title": item.findtext("a:title", default="", namespaces=ns),
                    "url": url,
                    "published_at": _as_date(item.findtext("a:published", default="", namespaces=ns)),
                }
            )
    return items


def upsert_advisory(db: Session, data: dict) -> tuple[Advisory, bool]:
    row = db.query(Advisory).filter_by(external_id=data["external_id"]).one_or_none()
    if row:
        for key in (
            "title",
            "source",
            "source_url",
            "vendor",
            "product",
            "cves",
            "affected_products",
            "description",
            "source_excerpt",
            "published_at",
            "source_updated_at",
            "keV_due_date",
        ):
            if key in data and data[key] is not None:
                setattr(row, key, data[key])
        row.imported_at = utcnow()
        return row, False
    row = Advisory(**{key: value for key, value in data.items() if hasattr(Advisory, key)})
    db.add(row)
    return row, True


def ingest_cisa_ics(db: Session, limit: int = 10, force: bool = False) -> dict:
    limit = min(max(limit, 1), 20)
    xml, metadata = fetch_source(db, CISA_ICS_RSS, "CISA ICS RSS", force=force)
    items = cisa_feed_items(xml, limit)
    inserted = updated = unavailable = 0
    for item in items:
        try:
            parsed_url = urlparse(item["url"])
            host = (parsed_url.hostname or "").casefold()
            if parsed_url.scheme != "https" or not (host == "cisa.gov" or host.endswith(".cisa.gov")):
                unavailable += 1
                continue
            html, _ = fetch_source(db, item["url"], "CISA ICS advisory", force=force)
            csaf_url = _cisa_csaf_download(html)
            if csaf_url:
                try:
                    csaf_text, _ = fetch_source(db, csaf_url, "CISA ICS CSAF", force=force)
                    data = parse_cisa_csaf(item["url"], json.loads(csaf_text), item["published_at"])
                except Exception:
                    data = parse_cisa_advisory_page(item["url"], html, item["published_at"])
            else:
                data = parse_cisa_advisory_page(item["url"], html, item["published_at"])
            if item["published_at"]:
                data["published_at"] = item["published_at"]
            row, created = upsert_advisory(db, data)
            inserted += int(created)
            updated += int(not created)
        except Exception:
            unavailable += 1
    db.commit()
    return {
        "source": "CISA ICS",
        "items_seen": len(items),
        "inserted": inserted,
        "updated": updated,
        "unavailable": unavailable,
        "source_metadata": metadata,
    }


def ingest_kev(db: Session, limit: int = 100, force: bool = False) -> dict:
    payload, metadata = fetch_source(db, CISA_KEV_JSON, "CISA KEV JSON", force=force)
    document = json.loads(payload)
    entries = document.get("vulnerabilities", [])[: max(1, min(limit, 1000))]
    inserted = updated = 0
    for entry in entries:
        cve = entry.get("cveID")
        if not cve:
            continue
        data = {
            "external_id": f"CISA-KEV:{cve}",
            "title": f"{entry.get('vendorProject', 'Unknown')} {entry.get('product', 'product')} — {entry.get('vulnerabilityName', cve)}",
            "source": "CISA KEV",
            "source_url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            "vendor": entry.get("vendorProject", ""),
            "product": entry.get("product", ""),
            "cves": [cve],
            "affected_products": [],
            "description": entry.get("shortDescription", ""),
            "source_excerpt": json.dumps(entry, ensure_ascii=False),
            "published_at": _as_date(entry.get("dateAdded")),
            "keV_due_date": _as_date(entry.get("dueDate")),
        }
        _, created = upsert_advisory(db, data)
        inserted += int(created)
        updated += int(not created)
    snapshot = db.query(SourceSnapshot).filter_by(source_url=CISA_KEV_JSON).one_or_none()
    if snapshot:
        snapshot.item_count = len(entries)
    db.commit()
    return {
        "source": "CISA KEV",
        "catalog_version": document.get("catalogVersion"),
        "date_released": document.get("dateReleased"),
        "items_seen": len(entries),
        "inserted": inserted,
        "updated": updated,
        "source_metadata": metadata,
    }


def _vendor_name(host: str) -> str | None:
    host = host.casefold().split(":", 1)[0]
    return next(
        (vendor for suffix, vendor in VENDOR_HOSTS.items() if host == suffix or host.endswith("." + suffix)),
        None,
    )


def parse_vendor_bulletin(url: str, html: str, vendor: str) -> dict:
    text = visible_text(html)
    title = next(
        (line.strip() for line in text.splitlines() if len(line.strip()) > 10),
        urlparse(url).path.rsplit("/", 1)[-1],
    )
    affected_match = re.search(
        r"(?:Affected Products?|Products? Affected|Vulnerable Products?)(.*?)(?:Fixed Versions?|Mitigation|Remediation|Resolution|References|Revision History|$)",
        text,
        re.I | re.S,
    )
    section = affected_match.group(1).strip() if affected_match else text
    affected = []
    for line in section.splitlines():
        line = line.strip(" •\t-")
        if not line:
            continue
        constraint = _version_constraint(line)
        if not constraint:
            continue
        product_name = line.split(":", 1)[0].strip() if ":" in line else line[:120]
        if product_name:
            affected.append({"product": product_name, "constraints": [constraint], "source_statement": line})
    cves = sorted(set(re.findall(r"\bCVE-\d{4}-\d{4,8}\b", text, re.I)))
    identifiers = cves or [
        re.sub(r"[^A-Za-z0-9-]+", "-", urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])[:120]
    ]
    return {
        "external_id": f"VENDOR:{identifiers[0]}",
        "title": title,
        "source": "Vendor bulletin",
        "source_url": url,
        "vendor": vendor,
        "product": affected[0]["product"] if affected else "",
        "cves": cves,
        "affected_products": affected,
        "description": " ".join(text.split())[:2000],
        "source_excerpt": section[:10000],
        "published_at": None,
        "source_updated_at": None,
    }


def ingest_vendor_bulletin(db: Session, url: str) -> dict:
    parsed = urlparse(url)
    vendor = _vendor_name(parsed.hostname or "")
    if parsed.scheme != "https" or not vendor:
        raise ValueError(
            "Vendor bulletin must use HTTPS on an approved Rockwell, Schneider Electric, Siemens, or Cisco domain"
        )
    html, metadata = fetch_source(db, url, f"{vendor} vendor bulletin")
    data = parse_vendor_bulletin(url, html, vendor)
    if not data["affected_products"]:
        raise ValueError(
            "Bulletin could not be normalized to a structured affected-version constraint; retain it for manual review"
        )
    row, created = upsert_advisory(db, data)
    db.commit()
    return {"external_id": row.external_id, "inserted": created, "source_metadata": metadata}


def ingest_nvd_cve(db: Session, cve: str, force: bool = False) -> dict:
    cve = cve.upper()
    if not re.fullmatch(r"CVE-\d{4}-\d{4,8}", cve):
        raise ValueError("CVE identifier format is invalid")
    url = f"{NVD_CVE_API}?cveId={cve}"
    payload, metadata = fetch_source(db, url, "NVD CVE API", force=force)
    document = json.loads(payload)
    entries = document.get("vulnerabilities", [])
    if not entries:
        raise ValueError(f"NVD returned no record for {cve}")
    record = entries[0]["cve"]
    descriptions = record.get("descriptions", [])
    description = next((x["value"] for x in descriptions if x.get("lang") == "en"), "")
    affected: list[dict] = []
    vendors: set[str] = set()
    products: set[str] = set()
    for config in record.get("configurations", []):
        nodes = config.get("nodes", [])
        simple_alternatives = (
            config.get("operator", "OR") == "OR"
            and len(nodes) == 1
            and nodes[0].get("operator", "OR") == "OR"
            and not nodes[0].get("negate", False)
            and not nodes[0].get("children")
            and bool(nodes[0].get("cpeMatch"))
            and all(item.get("vulnerable", False) for item in nodes[0]["cpeMatch"])
        )
        for node in nodes:
            for match in node.get("cpeMatch", []):
                if not match.get("vulnerable"):
                    continue
                parts = str(match.get("criteria", "")).split(":")
                if len(parts) > 4:
                    vendors.add(parts[3].replace("_", " "))
                    products.add(parts[4].replace("_", " "))
                constraints = []
                if match.get("versionStartIncluding"):
                    constraints.append(
                        {
                            "operator": "gte",
                            "version": match["versionStartIncluding"],
                            "raw": f"version >= {match['versionStartIncluding']}",
                        }
                    )
                if match.get("versionStartExcluding"):
                    constraints.append(
                        {
                            "operator": "gt",
                            "version": match["versionStartExcluding"],
                            "raw": f"version > {match['versionStartExcluding']}",
                        }
                    )
                if match.get("versionEndIncluding"):
                    constraints.append(
                        {
                            "operator": "lte",
                            "version": match["versionEndIncluding"],
                            "raw": f"version <= {match['versionEndIncluding']}",
                        }
                    )
                if match.get("versionEndExcluding"):
                    constraints.append(
                        {
                            "operator": "lt",
                            "version": match["versionEndExcluding"],
                            "raw": f"version < {match['versionEndExcluding']}",
                        }
                    )
                if match.get("version") not in (None, "*") and not constraints:
                    constraints.append(
                        {"operator": "eq", "version": match["version"], "raw": f"version {match['version']}"}
                    )
                affected.append(
                    {
                        "product": parts[4].replace("_", " ") if len(parts) > 4 else "",
                        "constraints": constraints,
                        "source_statement": match.get("criteria", ""),
                        "configuration_supported": simple_alternatives,
                    }
                )
    data = {
        "external_id": f"NVD:{cve}",
        "title": record.get("id", cve),
        "source": "NVD",
        "source_url": f"https://nvd.nist.gov/vuln/detail/{cve}",
        "vendor": next(iter(vendors), ""),
        "product": next(iter(products), ""),
        "cves": [cve],
        "affected_products": affected,
        "description": description,
        "source_excerpt": json.dumps(record.get("configurations", []), ensure_ascii=False)[:10000],
        "published_at": _as_date(record.get("published")),
        "source_updated_at": _as_date(record.get("lastModified")),
    }
    row, created = upsert_advisory(db, data)
    db.commit()
    return {
        "external_id": row.external_id,
        "inserted": created,
        "affected_product_constraints": len(affected),
        "source_metadata": metadata,
    }
