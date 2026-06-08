# Source Document Inventory

This directory contains the local evidence copies used by the report.

## Local Files

| File | Issuer | Report use |
| --- | --- | --- |
| `eutelsat_hotbird_13e_brochure.pdf` | Eutelsat | HOTBIRD 13F/13G slot, service context, and 40--53 dBW Ku-band widebeam contours |
| `intelsat_39_fact_sheet.pdf` | Intelsat | Intelsat 39 slot, C/Ku-band service regions, frequencies, EIRP, and beam G/T data |
| `ses_2025_fleet_map.pdf` | SES | Orbital-slot cross-check for IS-39 at 62E and ASTRA 1P at 19.2E |
| `andrew_type243_ku_band_datasheet.pdf` | Andrew Corporation | GS1 2.4 m antenna aperture, frequency range, gain, beamwidth, and cross-polarization data |
| `ATOMBKU016-020-Spec-Sheet.pdf` | Norsat | GS1 20 W-class Ku-band BUC/SSPA power and frequency specifications |
| `triax_td88_official_product_sheet.pdf` | Triax | GS2 reflector dimensions, gain, frequency range, beamwidth, and G/T data |

## Online Sources

- Eutelsat HOTBIRD brochure: <https://www.eutelsat.com/system/files/2026-01/DOC_GEOFLEET_Satellite_Brochure_HOTBIRD-13-EAST.pdf>
- Eutelsat 13E fleet page: <https://www.eutelsat.com/satellite-network/GEO-fleet/eutelsat-13-east>
- SES ASTRA 1P release: <https://www.ses.com/press-release/astra-1p-starts-delivering-content-across-europe>
- Intelsat 39 fact sheet: <https://www.intelsat.com/wp-content/uploads/2020/05/intelsat-39-fact-sheet.pdf>
- SES fleet map: <https://www.ses.com/sites/ses_v2/files/network_map/SES_2025_FleetMap_Refresh_v3.pdf>
- Andrew Type 243 datasheet: <https://www.tvcinc.com/shared-downloads/SEG-5214860405-Type243_Kuband.pdf>
- Norsat ATOM 20W product page: <https://www.norsat.com/products/atom-20w-ku-band-buc>
- Triax TD88 mirror: <https://www.bombeeck-digital.nl/amfile/file/download/file/693/product/8146/>

## Source Notes

- HOTBIRD 46 dBW is a conservative reading from the official 40--53 dBW contour
  map, not a guaranteed transponder value.
- HOTBIRD uplink receive G/T is an explicit project assumption.
- The Norsat 20 W value follows the ATOMBKU020 minimum P1dB rating of 43 dBm.
- The Triax reflector is 95 cm by 85 cm; the model uses a 0.9 m
  area-equivalent circular aperture.
- Andrew Type 243 specifies 48.9 dBi at 14.3 GHz; the model computes
  48.86 dBi at 14.0 GHz with 0.62 aperture efficiency.
- SES Fleet Map is used only for orbital-slot cross-checking.
