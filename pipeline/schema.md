# Dataset schema

The demonstration pipeline accepts aggregate court-month CSV files only. One row represents one `state × district × court_type × case_category × month` cell. Dates use `YYYY-MM`; counts are non-negative whole numbers.

| Column | Meaning |
|---|---|
| state | State or union territory label |
| district | District label |
| court_type | Court grouping |
| case_category | Case grouping |
| month | Calendar month (`YYYY-MM`) |
| cases_pending_start | Pending stock at month opening |
| cases_instituted | Cases instituted during month |
| cases_disposed | Cases disposed during month |
| hearings_listed | Hearings listed during month |
| hearings_adjourned | Hearings adjourned during month |
| cases_pending_over_3y | Age snapshot at month end, over three years |
| cases_pending_over_5y | Age snapshot at month end, over five years |

The computed month-end stock is `start + instituted - disposed`. Inputs are rejected if values are missing, non-numeric, negative, non-integer, or violate `disposed ≤ start + instituted`, `over_5y ≤ over_3y ≤ month_end`, or `adjourned ≤ listed`. Duplicate aggregate keys across files are rejected. Any individual-name, phone, Aadhaar, address, party, or accused column causes the entire file to be refused before values are recorded. Rejection logs include only source, row number, and reason.

This monthly flow schema applies only to the synthetic demo dataset. The official historical snapshot uses the separate [`official_schema.md`](official_schema.md) schema and never enters these monthly flow calculations.

## Source registry schema (`pipeline/sources.csv`)

Every CSV loaded from `pipeline/raw/`, including files under `raw/context/` and `raw/official/`, must have exactly one provenance row. `file_name` is relative to `pipeline/raw/`.

| Column | Meaning |
|---|---|
| file_name | Raw-relative CSV path, such as `official/pendency_2026-03-13.csv` |
| source_name | Publishing body or dataset name |
| source_url | Primary source URL |
| download_date | Date the source was checked/transcribed (`YYYY-MM-DD`) |
| licence | Licence or explicit note that reuse terms are unverified |
| coverage_start | First covered month (`YYYY-MM`) |
| coverage_end | Last covered month (`YYYY-MM`) |
| notes | Scope, transcription, date, and normalization notes |
