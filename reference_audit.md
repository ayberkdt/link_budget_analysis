# Reference and URL Audit

Report: Geostationary Bent-Pipe Satellite Link Budget Analysis & Atmospheric Propagation Study

Audit date: 2026-06-08

Second pass: 2026-06-08. The bibliography links were opened again during the final text pass. No new broken link was found.

Third pass: 2026-06-08. Online bibliography entries were opened again, then reformatted with explicit `url` and `urldate` fields. Legacy locally prepared datasheet summaries were removed from `sources/`.

## Reference-by-reference audit table

| Reference Number | Source Title | URL Status | Correct Target? | Supports Cited Claim? | Issue Found | Recommended Action |
| --- | --- | --- | --- | --- | --- | --- |
| [1] | Eutelsat HOTBIRD 13 East brochure | OK | Yes | Yes | Dated PDF path may change over time | Keep; added stable Eutelsat 13 East fleet-page backup and local source-file note |
| [2] | SES ASTRA 1P Starts Delivering Content Across Europe | OK | Yes | Yes | None | Keep |
| [3] | Intelsat 39 at 62 Degrees East fact sheet | OK | Yes | Yes | Direct operator PDF is public but should be locally retained | Keep with local source-file note |
| [4] | SES Satellite Fleet Map | OK | Yes | Partly | Supports orbital slots only; does not support Intelsat 39 payload/service properties | Keep only as orbital-slot cross-check; citation wording updated |
| [5] | Andrew Type 243 2.4 m Ku-band antenna datasheet | OK but third-party hosted | Yes | Yes | Datasheet is manufacturer material hosted by a distributor | Keep; label as manufacturer datasheet distributed by third-party host and retain local copy |
| [6] | Norsat ATOMBKU020 / ATOM 20W Ku-band BUC | OK | Yes | Yes | Product page is stable and public; exact PDF is linked from page and retained locally | Keep product page as main URL and local PDF note |
| [7] | Triax TD88 technical specification sheet | OK but mirror | Yes | Yes | Original Triax product URL printed in the sheet is no longer live | Keep only with explicit mirror wording and local source-file note |
| [8] | Pratt, Bostian, and Allnutt textbook | OK | Yes | Yes | No URL needed | Keep complete book metadata |
| [9] | ITU-R P.618-13 | OK | Yes | Yes | Superseded by P.618-14 | Keep exact implemented PDF URL for reproducibility |
| [10] | ITU-R P.837-7 | OK | Yes | Yes | Superseded by P.837-8 | Keep exact implemented PDF URL for reproducibility |
| [11] | ITU-R P.839-4 | OK | Yes | Yes | None | Keep exact PDF URL |
| [12] | ITU-R P.838-3 | OK | Yes | Yes | None | Keep exact PDF URL |
| [13] | ITU-R P.676-12 | OK | Yes | Yes | Superseded by P.676-13 | Keep exact implemented PDF URL for reproducibility |
| [14] | ITU-R P.840-8 | OK | Yes | Yes | Superseded by P.840-9 | Keep exact implemented PDF URL for reproducibility |
| [15] | ITU-R P.453-14 | OK | Yes | Yes | None | Keep exact PDF URL |
| [16] | ETSI EN 302 307-1 V1.4.1 DVB-S2 | OK | Yes | Yes | Original wording did not explicitly say Table 13 thresholds are ideal AWGN values with model margin applied separately | Keep; bibliography note and report wording updated |

## Links that work correctly

- https://www.eutelsat.com/system/files/2026-01/DOC_GEOFLEET_Satellite_Brochure_HOTBIRD-13-EAST.pdf
- https://www.eutelsat.com/satellite-network/GEO-fleet/eutelsat-13-east
- https://www.ses.com/press-release/astra-1p-starts-delivering-content-across-europe
- https://www.intelsat.com/wp-content/uploads/2020/05/intelsat-39-fact-sheet.pdf
- https://www.ses.com/sites/ses_v2/files/network_map/SES_2025_FleetMap_Refresh_v3.pdf
- https://www.tvcinc.com/shared-downloads/SEG-5214860405-Type243_Kuband.pdf
- https://www.norsat.com/products/atom-20w-ku-band-buc
- https://www.bombeeck-digital.nl/amfile/file/download/file/693/product/8146/
- https://www.etsi.org/deliver/etsi_en/302300_302399/30230701/01.04.01_60/en_30230701v010401p.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.618-13-201712-S!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.837-7-201706-S!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.839-4-201309-I!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.838-3-200503-I!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-12-201908-S!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.840-8-201908-S!!PDF-E.pdf
- https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.453-14-201908-I!!PDF-E.pdf

## Links that redirect or are unstable

- No main bibliography URL was found broken during this audit.
- The Eutelsat brochure uses a dated PDF path, so a stable Eutelsat fleet-page backup was added.
- The Andrew antenna PDF is distributor-hosted rather than manufacturer-hosted.
- The Triax source is a mirror of a manufacturer-generated sheet; this is now explicit.
- The Norsat product page is preferred over a direct CDN PDF URL because the page exposes public specs and links the exact PDF.

## Links to archive or replace

- Archive or retain local copies for Eutelsat, Intelsat, SES Fleet Map, Andrew, Norsat, and Triax sources. The required local files already exist under `sources/`.
- No reference needs immediate replacement.

## Claims needing stronger citation support

- SES Fleet Map should not support Intelsat 39 payload claims. The report now cites the Intelsat fact sheet for payload/service claims and uses SES Fleet Map only for orbital-slot cross-checking.
- DVB-S2 thresholds are supported by ETSI EN 302 307-1 Table 13 as ideal QEF AWGN values. The report now states that the model applies a separate 1.0 dB implementation margin.
- The ASI/off-axis envelope is now described as a simplified internal sensitivity model, not an ITU-R regulatory mask.

## Second-pass source-to-claim check

- Eutelsat HOTBIRD source: supports HOTBIRD 13F/13G, 13 degrees East, Ku-band widebeam downlink, Europe/Middle East/North Africa service context, and 40--53 dBW contour values. The 46 dBW Ankara value remains a conservative map-reading assumption, not a guaranteed transponder value.
- SES ASTRA 1P source: supports ASTRA 1P, 19.2 degrees East, European broadcast/content delivery context, and 80 transponders.
- Intelsat 39 source: supports Intelsat 39 at 62 degrees East, C/Ku-band capabilities, and service coverage across Africa, Asia-Pacific, Europe, and the Middle East.
- SES Fleet Map source: supports A1P at 19.2 degrees East and IS-39 at 62 degrees East. It is not used for Intelsat payload or service claims.
- Andrew Type 243 source: supports the 2.4 m Ku-band antenna, 48.9 dBi gain at 14.3 GHz, 13.75--14.50 GHz Tx range, and 30 dB on-axis cross-polarization statement.
- Norsat ATOMBKU020 source: supports the ATOM 20 W Ku-band product page and 14.0--14.5 GHz standard option. The local PDF is retained for the detailed `P_{1dB}` rating used in the model.
- Triax TD88 mirror: supports the TD88 product sheet claim but remains a mirror, so the report should not describe it as a live official Triax page.

## Updated bibliography entries

The following entries were updated directly in `LaTeX Rapor/references.bib`:

- `itu618`, `itu837`, `itu838`, `itu839`, `itu676`, `itu840`, `itu453`: retained exact direct ITU PDF URLs, added `urldate = {2026-06-08}`, and kept reproducibility/version-lock notes.
- `dvbs2`: retained the corrected ETSI title, added `urldate = {2026-06-08}`, and clarified that Table 13 ideal QEF AWGN `Es/N0` values are used before model implementation margin.
- `eutelsat`: added `url`/`urldate` fields and retained the stable fleet-page backup.
- `ses_fleet_map`: clarified A1P/IS-39 abbreviation and limited use to orbital-slot cross-checking.
- `skyware_24m`: clarified third-party hosted manufacturer datasheet.
- `norsat_atombku`: clarified product page plus linked PDF/local source-file relationship.
- `ses_astra1p`, `intelsat39`, and `triax_td88`: added `url`/`urldate` fields and retained concise source-quality notes.

## Local source-file check

All required local source files exist:

- `sources/eutelsat_hotbird_13e_brochure.pdf`
- `sources/intelsat_39_fact_sheet.pdf`
- `sources/ses_2025_fleet_map.pdf`
- `sources/andrew_type243_ku_band_datasheet.pdf`
- `sources/ATOMBKU016-020-Spec-Sheet.pdf`
- `sources/triax_td88_official_product_sheet.pdf`

Removed non-primary local summaries:

- `sources/prodelin_1244_datasheet.*`
- `sources/triax_td88_datasheet.*`

## Submission summary

The bibliography is acceptable for final submission after the applied edits. The remaining non-official hosted sources are clearly labelled, local copies exist, online entries have `urldate = {2026-06-08}`, and source-to-claim mapping is conservative.
