# Registered crime snapshot

`raw/crime/registered_crime_2023.csv` is a manual transcription of MHA Rajya Sabha Question 407, answered 3 December 2025, Annexure I, PDF page 3. Underlying source: NCRB Crime in India. Access method: manual published-report inspection, not scraping. Source URL is recorded in sources.csv.

Required columns: `state,year,ipc,sll,total`. Exactly one row for every current State/UT, year 2023 only. Counts must be nonnegative integers, IPC + SLL must equal total in every row. National controls: IPC 3,763,102; SLL 2,478,467; combined 6,241,569. Personal-data headers are refused before values are read. Validation failure stops the build and records a file-level rejection reason without exposing refused data.

Source label aliases are normalized: A&N Islands → Andaman and Nicobar Islands; D&N Haveli and Daman & Diu → Dadra and Nagar Haveli and Daman and Diu; Jammu & Kashmir → Jammu and Kashmir.

These are annual police registrations, not pending court stocks, convictions, unique victims, crime incidence or safety scores. Reporting practices and population differ. No population denominator is loaded, so no per-lakh metric is claimed. No crime/court linkage is performed.

`ipc_bns_mapping.csv` documents series-level treatment of the 1 July 2024 IPC-to-BNS break. It does not claim an offence-level equivalence: IPC/BNS totals are not directly comparable, SLL requires scope review. This build accepts no post-transition year; an offence-level reviewed crosswalk and revised validation are required before adding one.

Commercial reuse terms have not been verified. The MIT code license does not grant source-data rights.
