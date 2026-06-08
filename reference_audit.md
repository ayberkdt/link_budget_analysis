# Reference and URL Audit

Report: Geostationary Bent-Pipe Satellite Link Budget Analysis & Atmospheric Propagation Study

Audit date: 2026-06-08

## Summary

The report bibliography uses explicit `url` and `urldate = {2026-06-08}`
fields for online sources. Entries that rely on mirrors or distributor-hosted
documents are labelled in `LaTeX Rapor/references.bib`. The source documents
needed for local evidence are listed in `sources/README.md`.

## Reference Status

| Ref. | Source | URL status | Report use |
| --- | --- | --- | --- |
| [1] | Eutelsat HOTBIRD 13 East brochure | OK; dated PDF path | HOTBIRD 13F/13G slot, service context, and Ku-band widebeam contour |
| [2] | SES ASTRA 1P release | OK | ASTRA 1P 19.2E service context and 80-transponder payload |
| [3] | Intelsat 39 fact sheet | OK | Intelsat 39 slot, C/Ku-band service regions, and payload data |
| [4] | SES Satellite Fleet Map | OK | Orbital-slot cross-check only |
| [5] | Andrew Type 243 antenna datasheet | OK; distributor-hosted manufacturer datasheet | GS1 2.4 m antenna dimensions, gain, band, and cross-polarization data |
| [6] | Norsat ATOMBKU020 product page and spec sheet | OK | GS1 20 W-class Ku-band BUC/SSPA power and band data |
| [7] | Triax TD88 technical sheet | OK; mirror of manufacturer sheet | GS2 reflector dimensions, gain, band, beamwidth, and G/T data |
| [8] | Pratt, Bostian, and Allnutt textbook | Book reference | Link-budget equations and satellite communication background |
| [9] | ITU-R P.618-13 | OK | Earth-space attenuation combination and rain fade methods |
| [10] | ITU-R P.837-7 | OK | Rain-rate climatology model input basis |
| [11] | ITU-R P.839-4 | OK | Rain-height model |
| [12] | ITU-R P.838-3 | OK | Specific rain attenuation model |
| [13] | ITU-R P.676-12 | OK | Atmospheric gas attenuation |
| [14] | ITU-R P.840-8 | OK | Cloud and fog attenuation |
| [15] | ITU-R P.453-14 | OK | Wet refractivity input |
| [16] | ETSI EN 302 307-1 V1.4.1 | OK | DVB-S2 framing, MODCOD definitions, roll-off options, and Table 13 AWGN thresholds |

## Source-To-Claim Notes

- HOTBIRD 46 dBW is a conservative reading from the official 40--53 dBW
  contour map, not a guaranteed transponder value.
- SES Fleet Map is used only for orbital-slot cross-checking. It is not used
  as payload evidence for Intelsat 39.
- Andrew Type 243 data supports the 2.4 m aperture, 48.9 dBi gain at
  14.3 GHz, 13.75--14.50 GHz transmit range, and 30 dB on-axis
  cross-polarization statement.
- Norsat ATOMBKU020 data supports the 20 W-class Ku-band BUC setting through
  the product page and local specification sheet.
- Triax TD88 data comes from a mirror of a manufacturer-generated product
  sheet. The report and bibliography identify it as a mirrored source.
- DVB-S2 thresholds are ETSI ideal QEF AWGN values; the model applies a
  separate 1.0 dB implementation margin during MODCOD selection.
- The ASI/off-axis envelope is an internal sensitivity model, not an ITU-R
  regulatory mask.

## Online URLs

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

## Local Source Files

- `sources/eutelsat_hotbird_13e_brochure.pdf`
- `sources/intelsat_39_fact_sheet.pdf`
- `sources/ses_2025_fleet_map.pdf`
- `sources/andrew_type243_ku_band_datasheet.pdf`
- `sources/ATOMBKU016-020-Spec-Sheet.pdf`
- `sources/triax_td88_official_product_sheet.pdf`
