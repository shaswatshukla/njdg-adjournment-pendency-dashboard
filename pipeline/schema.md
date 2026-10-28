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
