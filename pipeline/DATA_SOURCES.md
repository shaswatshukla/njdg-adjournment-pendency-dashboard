# Data sources and provenance

The repository contains separate synthetic demo inputs and verified manually transcribed official aggregate reports. Source-specific provenance and limitations are recorded below and in sources.csv. No website is scraped. Before adding a real file, manually download it, review its current terms, record its provenance in `pipeline/sources.csv`, and note its definitions and coverage. No values should be inferred from these pointers.

## 1. Official court data

The current official snapshot is a manual transcription of the Department of Justice reply to Rajya Sabha Unstarred Question 3113, answered 19 March 2026, with data as of 13 March 2026. The cited PDF is [available here](https://www.doj.gov.in/static/uploads/2026/04/b7b4da487543be9a9f1d1558d06d76d2.pdf); Annex I is PDF page 53 and Annex II is page 54. Reuse and commercial publication terms have not been verified. No PDF bytes are bundled and no PDF hash is claimed. The CSV transcription has a calculated SHA-256 digest in generated snapshot metadata.

| Source | Provides | Access | Specific limitation |
|---|---|---|---|
| [National Judicial Data Grid (NJDG)](https://njdg.ecourts.gov.in/) | Aggregate case institution, disposal, pendency, and age snapshots across participating courts | Manual download | Dashboards, refresh dates, definitions, and historical coverage can vary by court and measure. |
| [eCourts Services](https://ecourts.gov.in/) | Court services, case status, and links to court systems | Manual download | A service portal; comparable bulk historical aggregates may not be available for every court. Do not collect person-level records. |
| [Supreme Court of India](https://www.sci.gov.in/) | Court annual reports, statistics, and administrative publications | Manual download | Publication periods and definitions may differ from NJDG and other courts. |
| [High Court reports - Allahabad High Court (example)](https://allahabadhighcourt.in/) | Example High Court annual reports and administrative statistics | Manual download | One High Court is not representative of other High Courts; report metrics may not align across years. Check each court's own publication. |

## 2. Government statistics and justice context

| Source | Provides | Access | Specific limitation |
|---|---|---|---|
| [NCRB Crime in India](https://www.ncrb.mha.gov.in/crime-in-india.html) | Official crime and police statistics by reporting year and category | Manual download | Definitions and categories can change; IPC/BNS transition requires a documented mapping and comparability treatment. |
| [NCRB Prison Statistics India](https://www.ncrb.mha.gov.in/prison-statistics-india.html) | Prison population, occupancy, and related annual statistics | Manual download | Annual snapshots and administrative definitions do not directly match court case cohorts. |
| [National Legal Services Authority (NALSA)](https://nalsa.gov.in/) | Legal aid, lok adalat, and access-to-justice reports | Manual download | Program reach and reporting units differ from court case-flow counts. |
| [Parliament questions and answers - Sansad](https://sansad.in/) | Published answers, reports, and government statements | Manual download | Responses may be one-off, use varying periods, and require careful source-page citation. |
| [Open Government Data Platform - data.gov.in](https://www.data.gov.in/) | Government datasets and metadata | Manual download | Dataset licences, completeness, refresh cadence, and column meanings must be checked individually. |

## 3. Research and civil-society publications

| Source | Provides | Access | Specific limitation |
|---|---|---|---|
| [India Justice Report](https://indiajusticereport.org/) | Comparative justice-system capacity and state-level indicators | Manual download | Composite indicators and publication rounds have their own methods; not a direct administrative case-flow series. |
| [Vidhi Centre for Legal Policy](https://vidhilegalpolicy.in/) | Legal policy research, datasets, and analysis | Manual download | Project-specific scope and sampling; read the underlying report methodology before comparison. |
| [Centre for Policy Research (CPR)](https://cprindia.org/) | Policy research and analysis | Manual download | Publications vary in topic, period, and method; not a harmonized court dataset. |
| [Common Cause](https://commoncause.in/) | Governance and justice-sector research | Manual download | Study-specific methods and dates; check whether data can be compared with administrative records. |
| [Law Commission of India](https://lawcommissionofindia.nic.in/) | Reports and legal reform recommendations | Manual download | Reports are issue-specific and do not necessarily contain regularly updated statistics. |

## 4. Optional contextual indicators

| Source | Provides | Access | Specific limitation |
|---|---|---|---|
| [Census of India](https://censusindia.gov.in/) | Official population and census tables | Manual download | Census reference years are infrequent; population denominators may not match court-report periods or boundaries. |
| [Department of Justice vacancy dashboard](https://www.dashboard.doj.gov.in/vacancy/) | Judge sanctioned strength, working strength, and vacancies | Manual download | Snapshot dates and court-level granularity vary; vacancies are descriptive context, not causal evidence. |
| [Union Budget of India](https://www.indiabudget.gov.in/) | Union ministry and program budget documents | Manual download | Allocations and spending are not necessarily available at district/court level or aligned to the court reporting period. |
| [State budget documents](https://www.indiabudget.gov.in/) | Starting point for official state finance portals and budget documents | Manual download | There is no single harmonized state budget series here; classification, scope, and district detail vary by state. |

Optional context columns are `population`, `judge_strength`, and `budget`. They must be documented in the provenance registry and joined only on `(state, district)`. The pipeline derives pending per lakh from population; it does not treat context as a cause of case outcomes.

## Crime-series boundary

This project includes no crime time series. India transitioned from the Indian Penal Code (IPC) to the Bharatiya Nyaya Sanhita (BNS) from July 2024. Any future crime comparison must document a defensible IPC-to-BNS category crosswalk and a break in comparability before inclusion. NCRB's [Sankalan portal](https://www.ncrb.mha.gov.in/uploads/SankalanPortal/Index.html) provides official correspondence material; this project does not apply it.
## Added registered-crime aggregate source

Government statistics: Ministry of Home Affairs, Rajya Sabha Unstarred Question 407, answered 3 December 2025, Annexure I, PDF page 3. URL: https://sansad.in/getFile/annex/269/AU407_UbEvYl.pdf?source=pqars

Provides: State/UT registered cognizable IPC, SLL and combined counts for 2021–2023; this project manually transcribes 2023 only. Access method: manual download/inspection of the published report, no scraping. Source table visually checked; 36 row sums and three national published control totals reconcile. Reuse terms remain unverified. Limitations: police registrations reflect reporting and enforcement practices; no safety inference or comparison to court stocks; no matching population denominator; predates the July 2024 IPC/BNS transition. Dataset-specific schema and normalization notes are in `crime_schema.md`. The series-level transition mapping explicitly withholds direct IPC/BNS comparison.

## Verified periodic court publications

- Supreme Court: https://www.sci.gov.in/indian-judiciary-annual-report/ publishes annual volumes for the Supreme Court and High Courts. The ingested Volume I PDF is https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/uploads/2026/01/2026011698.pdf ; PDF page 223 (printed 213) reports Civil/Criminal/Total monthly institutions, disposals and pending for January–August 2025. Access: manual published-report inspection. Opening, hearings and adjournments are not supplied in this table. The report reserves reproduction rights. No commercial clearance is claimed.
- Kokrajhar District Judiciary: https://kokrajhar.dcourts.gov.in/document-category/statistical-reports/ publishes monthly pendency statements. The ingested September 2026 report, published 7 October 2026, is https://cdnbbsr.s3waas.gov.in/s3ec05cdd0500dc0ef6682fa6ec6d2e6b5/uploads/2026/10/2026100717.pdf ; PDF page 3 contains the district summary. Access: manual published-report inspection. One district only; no nationwide extrapolation. Reuse terms unverified. Only aggregate summary cells are transcribed, with no officer/case details.

These reports' dates and scope remain separate from the March 2026 national snapshot. See `periodic_schema.md` for counts, validation and limitations.

