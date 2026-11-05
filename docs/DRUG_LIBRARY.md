# Public label library

`src/drug_library.py` provides source-backed display defaults and qualitative label
analysis. It is a **partial, on-demand collection**, not a complete pharmacopoeia.
No dose recommendation, individual concentration curve or numerical combination
prediction is admitted by this service.

## API and identity

- `resolve_name(name)` resolves only exact curated Chinese/English aliases,
  ignoring surrounding whitespace and English case. It never equates estradiol
  with ethinyl estradiol, estradiol esters, brand guesses or combination products.
- `profile_for(compound_id, route='oral')` returns an independent dictionary, or
  `None` for an unknown id. A known id with another route retains its identity
  but returns no half-life, no mechanism facts and a route-mismatch note.
- `analyze_labels(items, online=True)` accepts 1–32 dictionaries and returns
  `records`, every unordered `pairs` combination, and a Chinese explanatory
  `note`. Only `kind='catalog'` plus a recognized `compound_id` can use evidence.
  Custom/synthetic rows keep `compound_id=None` in results and never become
  recognized drugs simply because their display name resembles an ingredient.
  `input_index` identifies the original row; pair `ids` may include `None`.

The current identities are estradiol, bicalutamide, fluconazole, midazolam and
tofacitinib. The last two have no independent curated PK defaults. Their existing
catalog citations describe studies in the DIFLUCAN label; they are not falsely
presented as those drugs' standalone label seeds.

## Curated parameters

The profile source and population remain attached to every value. Online label
refresh does not silently replace these curated numeric defaults.

| Ingredient / oral formulation | Half-life | Source context |
| --- | --- | --- |
| Estradiol / micronized tablet | Unknown (`null`) | The cited [oral tablet label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=bfc1beb9-1ade-446e-97dd-55b41c2fa851) describes PK but supplies no numeric half-life to adopt. Other routes and esters are not substituted. |
| Bicalutamide / tablet | 5.8 days = 139.2 h | [Section 12.3, table 3](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=7a08d88b-051a-4c16-9560-12685c500c58): active R-enantiomer, normal males n=30, mean 5.8 days, SD 2.29 days. The table includes single-dose peak parameters. This is not a universal patient value. |
| Fluconazole / DIFLUCAN oral | Approximately 30 h | Existing [DIFLUCAN source](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f694c617-3383-416c-91b6-b94fda371204), Clinical Pharmacology: fasted normal volunteers, reported range 20–50 h; not a confidence interval. |

## Online lookup and local fallback

The adapter queries the official [openFDA label endpoint](https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/)
using the exact public English ingredient and `ORAL` route, sorted by label
effective date with `limit=1`. The resulting DailyMed set-id URL identifies the
label actually inspected. Only the single latest candidate returned is examined;
a rejected or oversized candidate is reported as a lookup failure, not proof
that no official label exists. The route scope currently supports oral tablets.

Each HTTPS request has an eight-second socket timeout and a 1,000,000-byte body
limit. Redirects must remain on the official API endpoint and are checked before
following them. The transport takes only the internally constructed public URL.
Names typed into custom rows, dose schedules, profiles and genetic information
are never transmitted or cached. Repeated ids in one analysis share a lookup.

Online mode always attempts a fresh lookup. It validates the exact single active
ingredient, single oral route, tablet description, UUID and effective date before
writing. Failure uses an integrity-checked cache, then a marked curated seed (if
available). Refresh failure never overwrites the last valid cache.

Cache files live in ignored `data/cache/drug_labels/<id>-oral.json`. Atomic replace
uses a unique temporary file. Reading checks the size, schema, exact fields,
identity, route, source URL, timestamp, SHA-256, fact id, supported section and
short supporting phrase. Corrupt/future-dated cache entries fail closed and show
`cache_error`; they do not supply facts. SHA-256 detects accidental corruption;
it is not a signature against an attacker who can rewrite both content and hash.

Records distinguish `online`, `cache`, `seed`, `unavailable`, `unknown`, and
`unsupported_route`. They expose `retrieved_at`, `age_days`, `stale`,
`content_sha256`, `response_sha256`, `fact_evidence`, and an optional `error` or
`cache_error`. Records older than 30 days are explicitly historical (`stale`),
never made current by offline reading. Seed retrieval time reflects the reviewed
source-fact snapshot with `timestamp_precision='day'` (midnight UTC is the date
marker, not an asserted HTTP request time); seeds have no fabricated response
hash or effective date. A mechanism pair depending on any historical record also
sets `stale=true` and explicitly identifies historical sources in its summary.

Only minimal facts, metadata and short supporting phrases are persisted. Full
label bodies and copyrighted Mayo articles are not stored by this library.

## Evidence boundary

The estradiol–bicalutamide pair yields `MECHANISM_INFERENCE` only if **both**
sources contain the respective facts: partial CYP3A4 metabolism of estrogens in
estradiol's Clinical Pharmacology / Drug Interactions section, and CYP3A4
inhibition by R-bicalutamide in bicalutamide's Drug Interactions section.
Online/cache records retain the actual section name, a short matched phrase and
a section hash. Seeds contain reviewed paraphrases with section locations.

Missing sections in a successfully retrieved label stay missing: seed facts are
not silently added to that online record. Similar words in unrelated sections
are ignored. This join is a qualitative mechanism inference; it does not prove a
clinical interaction for this exact pair or quantify an AUC/dose change. Every
pair has `prediction_admitted=false`. Other pairs remain
`INSUFFICIENT_EVIDENCE`; absence is not a finding of safety. Existing separate
catalog study observations are not multiplied into combination estimates.

## Validation

Run `python -m unittest tests.test_drug_library` for identity, route, provenance,
privacy, cache integrity, refresh failure, missing-section, stale/future-time,
body-limit and all-pair behavior. Tests substitute only the network boundary and
exercise the real parser and filesystem. `python -m unittest discover -s tests`
runs the application regressions.

The 2026-11-05 live smoke retrieved both requested ingredients from openFDA and
validated their actual supporting sections. Returned DailyMed set ids were
`5718f042-e8c0-b721-e063-6294a90a5bef` (estradiol) and
`26e30155-a50b-df14-e063-6394a90a9be4` (bicalutamide). Both records were `online`
and their pair remained a qualitative `MECHANISM_INFERENCE`.
