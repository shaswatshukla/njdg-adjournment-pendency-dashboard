# Official dated snapshot schema

The active official snapshot is the single CSV named by `source_file` in [`official_snapshot_controls.json`](official_snapshot_controls.json). The current file is a manual transcription of the Department of Justice reply to Rajya Sabha Unstarred Question 3113, answered 19 March 2026, reporting data as of 13 March 2026. Annex I is PDF page 53; Annex II is page 54. The controls manifest stores the published control totals and identity lists used for reconciliation.

| Field | Meaning |
|---|---|
| state | State/UT label for district and subordinate court aggregate rows; blank for Supreme and High Court rows |
| court_level | `supreme_court`, `high_court`, or `district_subordinate_aggregate` |
| court_id | Stable local identifier for the published reporting unit |
| court_label | Court label or explicit state/UT aggregate label |
| snapshot_date | Source snapshot date (`YYYY-MM-DD`) |
| cases_pending | Reported pending case stock |
| cases_pending_over_5y | Reported nested age-band count |
| source_table | `Annex I` or `Annex II` |

The current CSV contains 1 Supreme Court, 25 High Courts, and 36 state/UT district-and-subordinate-court aggregates. It does not identify individual district courts or tribunals. Do not treat a state/UT aggregate as a district record. The Jammu and Kashmir High Court label is normalized to "High Court of Jammu and Kashmir and Ladakh"; the source's original label is documented in the controls manifest.

The source does not report institutions, disposals, hearings, adjournments, opening stocks, over-three-year pendency, or a monthly series. Those metrics remain unavailable; the build does not infer or fill them with zero. The over-five-year share is derived only by dividing the reported over-five-year count by reported pending stock.

Reuse and commercial publication terms for the source have not been verified. The software MIT license does not grant rights to the source data. This is a dated report snapshot, not a live feed.

## Updating the active snapshot

Keep exactly one active official CSV selected by the controls manifest's `source_file`. A verified update changes the active CSV, its `sources.csv` provenance row, `official_snapshot_controls.json`, and `refresh_status.json` together in one reviewed change. Update all row dates, source coverage, control totals, state/court identity lists, and source details for that same publication. Do not mix rows from different report dates or silently replace a file while leaving its controls/provenance unchanged. Preserve the previous version in Git history; the checked-in historical regression fixture under `pipeline/tests/fixtures/` remains pinned to its original transcription. The active-data test reconciles to whichever date and published totals the current controls declare. The build rejects disagreements among the CSV, source registry, controls, and refresh status.
