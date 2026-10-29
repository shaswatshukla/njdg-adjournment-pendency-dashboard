# Justice Metrics — NJDG Pendency Dashboard

A free, static research website for verified aggregate court reports and registered-crime statistics in India. Plain HTML, CSS and JavaScript modules; locally hosted, pinned Chart.js 4.4.8. Python 3.11+ and pandas validate manually downloaded aggregate inputs. No backend, paid API, analytics or cookies.

## Current coverage and limits

- National court snapshot: 13 March 2026; Supreme Court, 25 High Courts and 36 State/UT district/subordinate aggregates. These are not individual district observations.
- Periodic reports: Supreme Court monthly Civil/Criminal/Total statistics for January–August 2025, and Kokrajhar district for July-August 2026 (excluding JJB). Nationwide district coverage remains incomplete.
- Crime map: 2023 NCRB/MHA registered cognizable IPC/SLL counts for all 36 States/UTs. Crime registrations are not convictions, true incidence, population-adjusted rates or safety scores. They are never combined with pending court stocks.
- Geographic boundaries: 2024 LGD state/UT polygons, distributed by Bharatlas and simplified for display. Source, licence statement, transformations and download checksum are bundled with the geometry. Small UT dots are enlarged click targets, not areas. Refer to Survey of India for authoritative boundaries.

The website publishes official report data only. The synthetic selector, demo views, demo requests and public demo JSON files have been removed. Offline test fixtures remain in the repository, labelled **SYNTHETIC - FOR DEMO**; they are not published as website data.

## Use the website

The homepage answers pending volume, backlog concentration and whether a national direction can be established. It explicitly leaves the national trend unavailable: a single national reporting date is not a time series. A dated summary is generated into HTML by the pipeline, so headline facts and source downloads remain available without JavaScript or when JSON requests fail. Requests time out after 12 seconds; secondary data cannot hold back the national figures.

Four primary destinations cover the overview, State/UT totals, partial district detail and sources/status. Court reports and further analysis sit in expandable groups. Registered crime is a separate context dataset, never a court-pendency measure. State views link to the loaded district reports; a missing district report means missing coverage, not zero cases. See [source audit](pipeline/SOURCE_AUDIT.md) for evidence and verification limits.

The grouped sidebar opens all court and research views. On mobile use the menu button; Escape closes the drawer. The header theme toggle defaults to the system preference and saves a light/dark choice in localStorage. Charts re-theme with the page.

Static evidence pages at `/states/`, `/sources/`, `/methodology/`, `/high-courts/`, `/supreme-court/`, `/district-reports/` and `/crime/` expose dated tables without JavaScript. The interactive app keeps hash routing for filters. Canonicals, sitemap, provenance JSON-LD, social preview and source corrections are generated from validated data, with no backend or frontend framework.

The crime map supports clickable, keyboard-focusable State/UT regions, exact figures, shareable State/UT links, zoom buttons, drag-to-pan when zoomed, reset, and an expanded modal view. Escape or Close returns to the normal view. The dropdown and exact-count table provide alternatives for small regions and map-loading failures. Expanding works without a browser full-screen permission. All geometry is served locally: no map tile service or external API is called by the map.

The national state chart shows the ten largest aggregates by default; choose All 36 for every published aggregate. Research briefs use browser print / Save as PDF and preserve source dates, scope and limitations.

## Run and validate

```sh
python -m pip install -r requirements-dev.txt
python pipeline/build.py
python -m pytest pipeline/tests -q
node pipeline/tests/map_logic.mjs
node pipeline/tests/evidence_logic.mjs
python pipeline/smoke.py
python -m http.server 8000 --directory site
```

Open http://localhost:8000 . There is no frontend build step. The homepage loads national data and the small refresh record; other datasets load only when opened. Theme changes re-theme charts without replacing the view.

Six JSON contracts in `site/data/` contain official reports and build metadata; a separate geographic asset lives in `site/assets/maps/india-states.json`. Smoke checks reject any of the former public synthetic summary/series files. Fixture JSON is generated only under `pipeline/output/synthetic_fixture_outputs/`, outside the hosted directory.

## Add or update a report

1. Manually download a published aggregate report. Do not scrape websites, collect case/party data or use undocumented endpoints.
2. Transcribe the relevant aggregate table into `pipeline/raw/`, following `schema.md`, `official_schema.md`, `periodic_schema.md` or `crime_schema.md` as applicable. Do not invent missing values.
3. Add a matching `pipeline/sources.csv` row with file_name, source_name, source_url, download_date, licence, coverage_start, coverage_end and notes. Record the source in `DATA_SOURCES.md` with its access method and limitations.
4. Update reviewed control totals, identities, dates and page citations in the appropriate controls manifest. National snapshots have exactly one active CSV; historical snapshots are preserved in `pipeline/archive/`. Different dates and scopes remain separate. Crime categories require the documented July 2024 IPC/BNS transition treatment.
5. Update truthful refresh metadata, run all checks, review generated output and publish. Validation failures stop the build and write reasons to `pipeline/output/rejected_rows.csv`; privacy-sensitive headers are refused before row values are parsed.

The monthly synthetic CSV and context fixture remain for offline regression tests. Context joins use state/district keys only in metrics.py; per-lakh measures must be labelled derived. Real data is never substituted with fixtures when a report is unavailable.

## Update map boundaries

The map asset is a manually reviewed geographic reference, not a court/crime count input. Its separate provenance is in the asset's `source` object and `pipeline/DATA_SOURCES.md`.

Manually download the published LGD States GeoJSON from the documented source, then run:

```sh
python pipeline/build_map.py path/to/LGD_States.geojson
python -m pytest pipeline/tests/test_map_asset.py -q
```

The builder performs no network requests. It requires the exact 36 geographic identities, retains LGD codes, checks coordinates, simplifies polygons using standard-library Python and embeds the original file's SHA-256. Review the result and attribution before publication. The source download is not bundled; the self-contained derived geometry is committed.

## Refresh and hosting

Daily source review is scheduled separately from website hosting. It looks for newer published reports and validates candidate changes; it is not a live NJDG feed and does not guarantee a new release. Last checked dates never replace reporting dates. A failed or uncertain check retains the last verified counts and records its status.

For GitHub Pages, enable GitHub Actions under repository Settings → Pages. The included workflow validates reports and tests before uploading only `/site`. Commit source changes and generated official JSON to `main`. Pipeline fixtures and private fixture outputs stay outside the uploaded directory. Other static hosts can serve `/site` directly for free.

Vercel production: https://justice-metrics.vercel.app . The `njdg-dashboard` project is linked to this repository's `main` branch, with Root Directory `site`, Framework `Other`, empty Install/Build commands and Output Directory `.`. Git pushes automatically create deployments; no backend, Vercel Cron, runtime secret or paid API is needed. The existing daily source-review task runs at 8:00 AM Asia/Kolkata, validates changes before publishing and checks the production deployment, public JSON and map asset afterward. It retains verified data if a source is unavailable and flags failures for review. Hosting automation does not guarantee source availability, instant updates or unattended recovery from every upstream change. GitHub Pages remains available as an alternate host.

## Disclaimer and data rights

Independent analysis and information only. Not legal advice. Does not predict verdicts, recommend bail, judge cases or provide case-level lookup. Figures may differ from current [official NJDG](https://njdg.ecourts.gov.in/) numbers because reporting dates, scopes and definitions differ.

The MIT licence covers project code, not third-party data. Government report commercial reuse terms remain unverified; the Supreme Court annual report reserves reproduction rights. Geometry is attributed to LGD via Bharatlas with the publisher's CC0 / CC-BY-4.0 statement; this is not a claim of government approval or blanket commercial clearance. Confirm applicable source-specific terms and attribution requirements before commercial use.

## Suggested next steps

- Add further districts only after verifying published monthly reports and coverage controls.
- Add verified reporting dates to the archive without interpolating missing periods.
- Establish dependable permitted data access and source-specific commercial reuse terms.
- Review an offence-level IPC/BNS crosswalk before adding a post-transition crime year.
- Verify newly published boundary revisions against authoritative sources before replacing the fixed map asset.

## Correction published 30 October 2026

The former September Kokrajhar figures did not match the cited PDF page and have been withdrawn. The source table also has inconsistent category/flow totals. The original CSV/provenance remain under `pipeline/quarantine/` for audit history, outside all published datasets and raw inputs. No September value is inferred. July and August PDF page-2 summaries were visually verified, reconcile, and explicitly exclude Juvenile Justice Board data. National and crime reporting dates are unchanged. See `pipeline/quarantine/README.md` and `pipeline/refresh_status.json` periodic_check.

## Security, accessibility and publication

Chart.js is served from `/site/vendor/`; its MIT licence is retained. The Vercel project uses `/site/vercel.json`: scripts and fetches stay on the same origin, object embedding is blocked, framing is denied, MIME sniffing is disabled and a referrer/permissions policy is set. Inline styles remain permitted for dynamic chart sizing. Version-named vendor assets are cached immutably; JSON revalidates. GitHub Pages cannot apply Vercel response-header rules; its static content remains an alternate host.

The pipeline regenerates the homepage, 36 State/UT evidence pages and supporting source/report pages, `robots.txt` and `sitemap.xml`. Commit generated HTML as well as JSON on verified data updates. JSON-LD deliberately omits source licences that have not been verified. Review field/date changes; do not claim commercial clearance.

Text sizes, table regions/captions, chart-value alternatives, focus handling, control targets and map boundaries have been improved. Browser automation was unavailable during this release. Static/contrast checks and CI are not a WCAG certificate, a real-device layout test, a screen-reader walkthrough, Core Web Vitals measurement or penetration test.
