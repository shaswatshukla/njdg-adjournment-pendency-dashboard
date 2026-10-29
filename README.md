# NJDG Adjournment & Pendency Dashboard

**Live dashboard:** [shaswatshukla.github.io/njdg-adjournment-pendency-dashboard](https://shaswatshukla.github.io/njdg-adjournment-pendency-dashboard/)  
**Repository:** [github.com/shaswatshukla/njdg-adjournment-pendency-dashboard](https://github.com/shaswatshukla/njdg-adjournment-pendency-dashboard)

The default dataset is a manually transcribed official snapshot from the Department of Justice reply to Rajya Sabha Unstarred Question 3113, answered 19 March 2026, reporting figures as of **13 March 2026**. It contains Supreme Court and High Court counts plus state/UT aggregates for district and subordinate courts. It does not provide individual district-court rows or tribunal coverage. It is a historical snapshot, not live/current data.

The dataset selector also offers a separate **SYNTHETIC - FOR DEMO** dataset. Those invented monthly examples remain useful for trying the original case-flow charts, but they are not official data. Values and coverage from the two datasets are never combined.

## Source rights and commercial use

Reuse and commercial publication terms for the official report have not been verified. Do not assume the repository's MIT license grants rights to the source data. Confirm the applicable reuse terms and attribution requirements before commercial use; this project does not claim commercial data clearance. This project has no live public data API connected.

## Source verification and freshness

A daily source-verification automation is scheduled to check for newer primary government publications, validate source tables and totals, run tests/build, and publish only a verified update. The first scheduled check has not yet run. The dashboard reports **data as of** separately from **source checked**; if verification needs review or errors, it warns and preserves the last verified snapshot. This is report-based verification, not scraping and not a live feed.

The canonical status is [`pipeline/refresh_status.json`](pipeline/refresh_status.json). It records `last_checked_at_utc`, status, data-as-of date, primary source URLs, and a note. `pipeline/build.py` validates and copies it to `site/data/refresh_status.json` without replacing the source-check time with build time. See [`pipeline/refresh_status.md`](pipeline/refresh_status.md) for the status contract.

When a newer report is verified, update the one active snapshot named by `source_file` in `pipeline/official_snapshot_controls.json`, its matching `sources.csv` row, all CSV rows, source-published controls and identities, and `refresh_status.json` together. Keep a single report date per CSV and preserve earlier versions in Git history. See [`pipeline/official_schema.md`](pipeline/official_schema.md#updating-the-active-snapshot). Fixed regression tests preserve the original transcription; a separate test validates the active snapshot against its own controls so later verified dates can pass CI.

## Run locally

Install Python 3.11, then run:

```powershell
python -m pip install -r requirements.txt
python pipeline/build.py
python pipeline/smoke.py
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. Serve `site/` over HTTP so the browser can fetch the JSON files. The build validates the synthetic monthly dataset and official snapshot as separate inputs, reconciles official rows against source control totals, writes the eight JSON contracts, and parses every required output before returning success.

## Tests

Install development tools and run pytest:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest pipeline/tests -v
```

The unittest-compatible test classes can also run with Python's standard library:

```powershell
python -m unittest discover -s pipeline/tests -v
```

Tests cover monthly metrics, official row/control-total reconciliation, reported state identities, unreported-field nulls, provenance and privacy checks, context joins, invalid snapshots, refresh-status preservation, and JSON smoke validation.

## Data and metric boundaries

See [`pipeline/official_schema.md`](pipeline/official_schema.md), [`pipeline/official_snapshot_controls.json`](pipeline/official_snapshot_controls.json), and [`pipeline/DATA_SOURCES.md`](pipeline/DATA_SOURCES.md) for the official snapshot schema, published control totals, and source limitations. The public report link and annex pages are shown on the Methodology view.

The official source reports pending stock and cases pending over five years. The dashboard derives the over-five-year share from aggregate counts. It does not calculate institution, disposal, hearing, adjournment, pendency-rate, over-three-year, or monthly measures because their source values are absent. It does not fill unknown figures with zero or backsolve them.

The separate demo pipeline uses the monthly flow formulas documented in [`pipeline/schema.md`](pipeline/schema.md). It still stops on invalid rows, incomplete provenance, duplicate keys, or personal-data column names.

No crime series is included. Any future IPC/BNS comparison would need a documented category mapping and comparability treatment for the July 2024 transition.

## GitHub Pages

GitHub Actions runs pytest and rebuilds the JSON data before publishing the static `site/` directory. In repository settings, enable **Pages > Build and deployment > GitHub Actions**, then push to `main` or run the workflow manually.

## Suggested next steps

1. Verify the reuse terms for each source before any commercial redistribution.
2. Review future official snapshots against their published totals and state/court coverage before replacing this historical data.
3. Keep source-check time distinct from snapshot date and preserve the previous verified figures if a source update is uncertain.
4. Connect an official public API only after its existence, access terms, and schema have been confirmed.

## License

MIT for the project code. The license does not grant rights to external source data. See [`LICENSE`](LICENSE).
