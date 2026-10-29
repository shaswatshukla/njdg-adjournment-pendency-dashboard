# Periodic court reports

Separate from both the synthetic monthly schema and the March 2026 national snapshot. Inputs are manually downloaded published reports under `raw/periodic/`, with one sources.csv entry per file and matching `periodic_controls.json` identity, URL, PDF page, periods and published control totals. No website tables are scraped.

Columns in order: `court_level,state,district,court_label,month,category,opening,instituted,disposed,pending,source_page`. Required counts are nonnegative integers. Opening may be blank only when unreported; it is never back-calculated. Civil + Criminal must equal Total for each reported count. Duplicate month/category rows, changed identities/pages/periods, missing required counts, personal-data headers and inconsistent opening + instituted - disposed are refused. Validation stops the build and records a reason in rejected_rows.csv.

Monthly clearance = reported disposed / instituted, unavailable for zero instituted. Pendency rate = reported pending / reported opening, unavailable for zero or unreported opening. Adjournments remain unavailable. Do not sum stocks across months or add Total to its Civil/Criminal components. Three-month metrics are not supplied for this separate report view.

Loaded sources:

- Supreme Court Indian Judiciary Annual Report 2024–25 Volume I, PDF page 223 (printed 213), January–August 2025 monthly Civil/Criminal/Total. Page visually verified. Aggregate monthly totals: institutions 49,671, disposals 43,986; August stock 88,181. The report reserves reproduction rights; no commercial clearance is claimed.
- Kokrajhar district monthly statement as of September 2026, published 7 October 2026; district summary PDF page 3. Civil: opening 2,504, instituted 182, disposed 135, pending 2,551. Criminal: 8,572, 570, 416, 8,726. Total: 11,076, 752, 551, 11,277. Page visually verified; no individual case or judicial-officer data collected. Reuse terms unverified.

This is **one district in Assam**, not all Assam districts or nationwide district coverage. Report months differ from the national snapshot and are never blended into it. Add further districts and periods only after reviewing the primary reports and their definitions, controls and provenance. Link official publication archives in the controls manifest so recurring checks can discover new releases manually.
