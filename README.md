# NJDG Adjournment & Pendency Dashboard

**Live dashboard:** [shaswatshukla.github.io/njdg-adjournment-pendency-dashboard](https://shaswatshukla.github.io/njdg-adjournment-pendency-dashboard/)  
**Repository:** [github.com/shaswatshukla/njdg-adjournment-pendency-dashboard](https://github.com/shaswatshukla/njdg-adjournment-pendency-dashboard)

**SYNTHETIC - FOR DEMO.** This repository demonstrates a transparent pipeline and static dashboard for Indian court case-flow metrics. Its included court and context data are invented. They are not official statistics, must not be cited as real-world facts, and do not describe real people, courts, or districts.

The dashboard is a plain HTML/CSS/vanilla JavaScript single-page site with hash routes. It uses Chart.js 4.4.8 from a pinned CDN. The data pipeline uses Python 3.11 and pandas; pytest is a development dependency. No scraping or build tool is used.

## Run locally

Install Python 3.11, then run:

```powershell
python -m pip install -r requirements.txt
python pipeline/build.py
python pipeline/smoke.py
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. Serve the `site/` folder over HTTP so the browser can fetch the JSON files. `pipeline/build.py` validates every registered CSV, writes the six data JSON files, and parses all six required output files before reporting success.

## Tests

Install development tools and run pytest:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest pipeline/tests -v
```

The test classes also run using Python's standard library `unittest`:

```powershell
python -m unittest discover -s pipeline/tests -v
```

Coverage includes formulas, zero/missing/negative counts, input validation, personal-data refusal, source provenance, duplicate keys, context joins, rolling-window completeness and aggregation, stock handling, and JSON smoke validation.

Verification: GitHub Actions run [40778423236](https://github.com/shaswatshukla/njdg-adjournment-pendency-dashboard/actions/runs/40778423236) passed on Python 3.11 with 20 pytest checks, the build, and JSON smoke validation. Desktop (1280px) and mobile (375px) views were inspected; all five routes, state/rolling views, district filters and CSV download, theme persistence, and browser console checks passed.

## Input data and provenance

Place aggregate monthly CSV files in `pipeline/raw/`. Optional aggregate context CSVs can live in `pipeline/raw/context/`. Register **every** file in `pipeline/sources.csv` with file name, source name, URL, download date, licence, coverage start/end, and notes. Context joins use only state and district. Never add personal-level rows. See [`pipeline/schema.md`](pipeline/schema.md) for the schema and [`pipeline/DATA_SOURCES.md`](pipeline/DATA_SOURCES.md) for source guidance.

The build stops if any row or provenance check fails and writes safe row locators, aggregate field values, and reasons to `pipeline/output/rejected_rows.csv`. Files with personal-data column names are refused before their row values are parsed or logged.

## Measures and limitations

- Ending pending = opening pending + instituted - disposed.
- Pendency = ending pending / opening pending.
- Clearance = disposed / instituted.
- Adjournment = adjourned hearings / listed hearings.
- Long-pending shares divide the latest month-end age snapshot by ending pending.
- Three-month flow ratios use ratios of aggregate counts, never averages of monthly ratios. Stock measures use the first opening and final ending; age measures use the final snapshot. A missing month or changing contributing-grain coverage makes a rolling measure unavailable.

These are descriptive measures. They do not explain delay or adjournments, assess judicial quality, predict outcomes, or establish cause. Reporting definitions and coverage can vary. Consult the current [National Judicial Data Grid (NJDG)](https://njdg.ecourts.gov.in/) for authoritative data and definitions. This project is not legal advice. Figures may differ from current official NJDG figures.

No crime series is included. India transitioned from IPC to BNS from July 2024. Any future crime comparison must document an appropriate category mapping and the comparability break before introducing a series.

## GitHub Pages

The GitHub Actions workflow runs pytest and rebuilds the JSON data before publishing the static `site/` directory. In repository settings, enable **Pages > Build and deployment > GitHub Actions**, then push to `main` or run the workflow manually.

## Suggested next steps

1. Manually obtain a public aggregate source file and record its exact provenance and applicable terms.
2. Confirm the source definitions, coverage, refresh date, and dimensions before mapping it to the schema.
3. Run the validator, review every rejection, and compare calculated totals with source documentation.
4. Keep context data separate and avoid causal claims from descriptive comparisons.
5. For any future crime series, document the IPC-to-BNS category crosswalk and July 2024 discontinuity before analysis.

## License

MIT. See [`LICENSE`](LICENSE).
