# Source Document Inventory

This directory keeps local copies of the external documents used as evidence in
the report. Only original operator, manufacturer, standards, or clearly labelled
mirror documents should live here.

## Retained Source Files

| File | Issuer | Use in the report |
| --- | --- | --- |
| `eutelsat_hotbird_13e_brochure.pdf` | Eutelsat | HOTBIRD 13F/13G orbital slot, service context, and 40--53 dBW Ku-band widebeam EIRP contours |
| `intelsat_39_fact_sheet.pdf` | Intelsat | Intelsat 39 at 62E, Ku-band service regions, frequencies, EIRP, and beam G/T data |
| `ses_2025_fleet_map.pdf` | SES | Fleet-position cross-check for IS-39 at 62E and ASTRA 1P at 19.2E |
| `andrew_type243_ku_band_datasheet.pdf` | Andrew Corporation | GS1 2.4 m antenna aperture, frequency range, gain, beamwidth, and cross-polarization data |
| `ATOMBKU016-020-Spec-Sheet.pdf` | Norsat | GS1 20 W-class Ku-band BUC/SSPA power and frequency specifications |
| `triax_td88_official_product_sheet.pdf` | Triax | GS2 reflector dimensions, gain, frequency range, beamwidth, and G/T data |

## Removed Legacy Files

The old `prodelin_1244_datasheet.*` and `triax_td88_datasheet.*` files were
project-prepared summaries, not primary manufacturer-issued datasheets. They
were removed because the report now cites the primary Andrew and Triax evidence
listed above.

## Web-Only Source

The ASTRA 1P comparison uses the official SES release:
<https://www.ses.com/press-release/astra-1p-starts-delivering-content-across-europe>.
It confirms commercial operation at 19.2E, European broadcast service, and the
80-transponder payload. It is cited as a web source because no public ASTRA 1P
technical fact sheet with an Ankara-specific EIRP contour was available in the
material reviewed for this project.

## Audit Notes

- The HOTBIRD 46 dBW downlink EIRP is a conservative reading from the official
  40--53 dBW contour map, not a transponder guarantee.
- The HOTBIRD uplink receive G/T value of 3 dB/K is an explicit project
  assumption; it is not present in the operator brochure.
- The Norsat 20 W value corresponds to the ATOMBKU020 minimum P1dB rating of
  43 dBm. The baseline therefore represents a rated boundary point and does not
  claim additional linear-output back-off.
- The Triax reflector is 95 cm by 85 cm. The model's 0.9 m circular aperture is
  the area-equivalent diameter, approximately sqrt(0.95 x 0.85) = 0.899 m.
- The Andrew Type 243 sheet specifies 48.9 dBi at 14.3 GHz. The model computes
  48.86 dBi at 14.0 GHz with the stated 0.62 aperture-efficiency assumption.
- The ASTRA 1P row is a geometry-and-service preselection comparison. It is not
  assigned a footprint EIRP or used as a third complete link-budget case.

## Standards

The bibliography links to the exact ITU-R and ETSI versions implemented by the
software. P.618-13, P.837-7, P.676-12, and P.840-8 have newer successor
editions; the code is version-locked for reproducibility, so a successor
recommendation is not assumed to be numerically interchangeable without code
and regression review.
