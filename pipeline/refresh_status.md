# Refresh-status contract

`refresh_status.json` is the canonical manual/daily-verification state. The builder validates it and copies it unchanged to `site/data/refresh_status.json`; it never substitutes the build timestamp for `last_checked_at_utc`.

| Field | Rule |
|---|---|
| `last_checked_at_utc` | ISO 8601 timestamp with UTC offset (`Z` accepted) for the latest source check |
| `status` | `verified_snapshot`, `no_change`, `updated`, `needs_review`, or `error` |
| `data_as_of` | Date of the last verified snapshot, independent of the source-check time |
| `sources` | One or more HTTPS primary-source URLs checked |
| `note` | Plain-language check result and limitations |

The initial value records a manual check on 29 October 2026 for the official snapshot dated 13 March 2026. Daily source verification has been scheduled but has not yet run. No automatic public data API is connected. If an update is uncertain or a check fails, retain the previous verified data and use `needs_review` or `error`; do not relabel old data as current. A verified update must replace the CSV and source control manifest, preserve provenance and source licence notes, update the data-as-of date, and pass the tests/build before publishing.
