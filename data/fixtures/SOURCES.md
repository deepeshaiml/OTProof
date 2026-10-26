# Advisory fixture provenance

The offline demonstration inventory is fictional. The three advisory records below are public CISA ICS advisories; their normalized content is stored in `advisories.json` so the demo works without feed access. The original CISA pages remain the source of truth.

| Fixture ID | Public source | CISA publication date | CISA update date | Normalized affected statement |
|---|---|---:|---:|---|
| ICSA-24-226-06 | [Rockwell Automation FactoryTalk View Site Edition](https://www.cisa.gov/news-events/ics-advisories/icsa-24-226-06) | 2024-08-13 | 2024-08-29 | FactoryTalk View SE version 13.0 |
| ICSA-24-256-24 | [Rockwell Automation Pavilion8](https://www.cisa.gov/news-events/ics-advisories/icsa-24-256-24) | 2024-09-12 | 2024-09-12 | Pavilion8 versions prior to V5.20 |
| ICSA-24-284-15 | [Rockwell Automation DataMosaix Private Cloud](https://www.cisa.gov/news-events/ics-advisories/icsa-24-284-15) | 2024-10-10 | 2024-10-10 | DataMosaix Private Cloud version 7.07 and prior |

All three records identify Rockwell Automation. CVEs and affected-version statements are retained in the fixture with source URLs, publication/update dates, and source excerpts. The demo does not assert that the fictional Cedar Valley utility owns the referenced equipment.

The ingestion service uses the official [CISA ICS RSS feed](https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml), [CISA KEV JSON catalog](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json), and documented [NVD CVE API 2.0](https://nvd.nist.gov/developers/vulnerabilities). When a CISA advisory page links to CSAF, OTProof follows only validated links to the official `cisagov/CSAF` repository. Vendor bulletin imports are restricted to HTTPS pages on the configured approved vendor domains.

## Evidence checked for the demonstration

- CISA RSS and linked CSAF advisory import were exercised against public endpoints on 2026-10-26. The live ICS import succeeded after resolving advisory links through the CISA page's explicit “View CSAF” link.
- CISA KEV JSON import was exercised on 2026-10-26. The returned catalog release date was 2026-10-23.
- NVD API 2.0 lookup for CVE-2024-7513 was exercised on 2026-10-26 and returned one affected-product constraint.
- Public feeds can change; each imported record stores the fetched timestamp and source update timestamp where provided. A fixed copy is included for offline repeatability.
