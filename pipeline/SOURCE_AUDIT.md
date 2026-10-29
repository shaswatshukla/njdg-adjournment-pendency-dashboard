# Source and coverage review — 29 October 2026

This is a source/implementation review, not a complete functional, security or commercial-rights audit. No reporting date or count was advanced by this review.

| Dataset | Loaded coverage | Primary evidence | What remains missing |
| --- | --- | --- | --- |
| National pending stock | 13 March 2026; Supreme Court, 25 High Courts, 36 State/UT district/subordinate aggregates | [DoJ reply to Rajya Sabha Q3113](https://www.doj.gov.in/static/uploads/2026/04/b7b4da487543be9a9f1d1558d06d76d2.pdf), Annex I PDF p.53, Annex II p.54. The annexes are accessible; SC 92,621 and HC total 64,00,890 match loaded controls. | Individual districts; all-India monthly flows and trends; hearings and adjournments. Shared High Courts counted once. |
| Supreme Court monthly series | January–August 2025; Civil, Criminal and Total separately | [Supreme Court annual report 2024–25 Vol.I](https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/uploads/2026/01/2026011698.pdf), PDF p.223. Official PDF accessible at the start of review; subsequent text requests timed out. Existing transcribed controls and historical fixture remain pinned. | No claim of a freshly reverified full transcription or a newer reporting period. No national extrapolation. |
| District monthly series | Kokrajhar, Assam, September 2026 only | [Official district statistical-report archive](https://kokrajhar.dcourts.gov.in/document-category/statistical-reports/) lists the statement dated 7 October 2026. The direct PDF could not be independently opened by the review tool in this session; existing validated rows were retained. | Nationwide district completeness; multi-month trend for this district; a successful fresh PDF check. Archive presence alone does not verify all values. |
| Registered crime | 2023 annual IPC/SLL registrations; 36 States/UTs | Existing MHA/NCRB source and control totals; no new crime-source audit in this pass. | Population-adjusted incidence, safety scores, court outcomes, or comparable post-BNS series. |

The generated homepage exposes dated figures before JavaScript runs. Primary JSON loading no longer waits for secondary datasets; requests time out explicitly and retain the published summary on failure. Tests cover request failure paths and concentration denominators. Automated checks do not establish that every visitor's browser, network or chart CDN works.

Source download, build, availability check and reporting dates are distinct. The source registry displays download dates as downloads. Daily maintenance is scheduled separately and must record genuine successful checks rather than infer freshness from a deploy.

Browser controls were unavailable during this change: no fresh visual checks at 375px/1280px, theme interaction, chart rendering or keyboard walkthrough are claimed. Prior visual verification is not re-labelled as a test of this release.
