# Physiology, substances and mechanism extension

User scope 2026-11-05: height, weight, body fat, physiological sex, supplements/other substances, Mayo references, gene pathways and justified extensions. This extends the existing design, not clinical approval.

Implementation slice: optional local physiology form; stable substance category separate from evidence identity; normalized context and missing-model gates in hashed reports. Blank values stay unknown. No automatic sex/genotype inference or population surrogate. No profile data is used for online lookup. Derived body descriptors and allometric coefficients are deferred until their purpose and model domain are defined.

Mechanism graph target: substance → enzyme/transporter/receptor/ion channel → exposure or response → endpoint. Gene → allele/diplotype → measured/reviewed phenotype → mechanism activity is a separate, provenance-bearing branch. Genotype is not an ion channel; gene-associated toxicity is not necessarily metabolism. Inhibitors/inducers may cause phenoconversion; substrate competition and shared pathways must be jointly modeled instead of multiplying pair ratios. Preserve uncertain calls, copy number, reference assembly, assay coverage, time and source.

Sources: Mayo Clinic Drugs and Supplements https://www.mayoclinic.org/drugs-supplements is a candidate educational/mechanism source, not automatically a PK coefficient API. Access/redistribution terms and an authorized feed must be established before remote ingestion. CPIC https://cpicpgx.org/ and https://api.cpicpgx.org/ are candidate versioned gene–drug/phenotype sources; no credential or live patient-query integration is enabled. Local reviewed snapshots are the planned adapter boundary. These are provider registrations, not completed connectors.

Broader requirements:
- Physiological measurements with units, date, method and provenance; age, renal/hepatic function, pregnancy/lactation and relevant hormonal context, missingness and measurement uncertainty. Sex alone must not imply organ function, pregnancy or hormone status.
- Medicines, supplements, botanicals, food/beverages and other substances share an active-ingredient model. Mixtures need ingredient amount/unit, batch, formulation, purity/standardization and unknown constituents. Supplement mass is not automatically active-compound mass; IU cannot be generically converted to mg.
- Food timing, alcohol/smoking, formulation, active metabolites, nonlinear clearance, time-dependent enzyme inhibition/induction, washout and route-specific bioavailability.
- Renal measures must distinguish eGFR normalized to 1.73 m² from absolute clearance; do not silently substitute one for another. Genotype-derived and measured phenotype remain separate.
- Provenance version/hash, conflict records, applicability checks, explicit uncertainty and independent validation for every applied modifier. Personalized model unavailable means HOLD_FOR_REVIEW, never “normal metabolism.”

Plan: (1) local input/normalization and categories; (2) context/hash/report gates and tests; (3) actual UI smoke; (4) Mission sync. Subsequent calibrated models, authorized Mayo import, CPIC snapshot adapters, component mixture resolution and independent validation remain pending and must not be reported as implemented.
