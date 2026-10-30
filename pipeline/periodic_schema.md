# Periodic court reports

Separate from both the synthetic monthly schema and the March 2026 national snapshot. Inputs are manually downloaded published reports under `raw/periodic/`, with one sources.csv entry per file and matching `periodic_controls.json` identity, URL, PDF page, periods and published control totals. No website tables are scraped.

Columns in order: `court_level,state,district,court_label,month,category,opening,instituted,disposed,pending,source_page`. Required counts are nonnegative integers. Opening may be blank only when unreported; it is never back-calculated. Civil + Criminal must equal Total for each reported count. Duplicate month/category rows, changed identities/pages/periods, missing required counts, personal-data headers and inconsistent opening + instituted - disposed are refused. Validation stops the build and records a reason in rejected_rows.csv.

Monthly clearance = reported disposed / instituted, unavailable for zero instituted. Pendency rate = reported pending / reported opening, unavailable for zero or unreported opening. Adjournments remain unavailable. Do not sum stocks across months or add Total to its Civil/Criminal components. Three-month metrics are not supplied for this separate report view.

Loaded sources:

- Supreme Court Indian Judiciary Annual Report 2024–25 Volume I, PDF page 223 (printed 213), January–August 2025 monthly Civil/Criminal/Total. Page visually verified. Aggregate monthly totals: institutions 49,671, disposals 43,986; August stock 88,181. The report reserves reproduction rights; no commercial clearance is claimed.
- Kokrajhar district monthly statements for July and August 2026, PDF page 2 summaries, excluding Juvenile Justice Board data. July: opening 5,103, instituted 331, disposed 296, pending 5,138. August: opening 5,138, instituted 405, disposed 291, pending 5,252. Civil/Criminal components and published totals are controlled separately in `periodic_controls.json`; source PDF checksums are recorded there. Reuse terms unverified.
- The formerly published September 2026 input is withdrawn and retained only in `pipeline/quarantine` with its provenance and source review. Its cited PDF page 3 also contains inconsistent category/flow totals. It is not an active source; do not infer replacement counts or restore it without explicit source-correction review.

This is **one district in Assam**, not all Assam districts or nationwide district coverage. Report months differ from the national snapshot and are never blended into it. Add further districts and periods only after reviewing the primary reports and their definitions, controls and provenance. Link official publication archives in the controls manifest so recurring checks can discover new releases manually.
