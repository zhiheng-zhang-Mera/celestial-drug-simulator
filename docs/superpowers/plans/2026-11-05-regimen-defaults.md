# Regimen defaults and online mechanism repair

Goal: enter estradiol + bicalutamide without invented PK inputs; online-first label evidence with offline fallback; stable click-selected pages.
Spec: Owner's DEV-10 request, existing idea-structure.md identity/model boundaries.
Architecture: existing Tk editor and simulate boundary retained. Evidence-mode rows need only identity, optional dose/timing, route; advanced synthetic IV remains separate. Library owns curated route-specific defaults and online label caching. Explicit names resolve only exact known aliases; custom names never silently inherit evidence. Public ingredient lookup only, no profile transmission. No dependency/install or external mounting changes.

- [ ] Reproduce missing input/library and selected tab padding problems; regression tests.
- [ ] Add label library service, exact Chinese aliases, formulation-aware defaults, online-first bounded public-label fetch + validated cache/seed fallback, evidence-backed CYP3A4 inference for requested pair distinguished from direct pair evidence. No universal estradiol half-life or invented numerical interaction.
- [ ] Editor: drug search/name, route/formulation and optional dose/schedule; read-only source defaults. Advanced synthetic settings collapsed. Name-only evidence rows accepted, unknown/custom supported. Async analysis with snapshot generation token prevents stale results. All pairs up to32.
- [ ] Stable notebook tab margins/padding and explicit clicked-tab select; result page opens on analyse, context/source controls navigate visibly.
- [ ] Full regressions, read-only independent review, scoped desktop video, GitHub + Book receipts. Formal media archival limits retained.

Ruling: online-first scoped official label cache instead of immediate tens-of-GB complete SPL mirror; owner permits full download but does not require it. Cache is a partial corpus, labelled honestly. Retain original mathematical simulator for deliberate advanced synthetic experiments, not required ordinary data entry.
Review focus: Chinese alias identity versus custom; oral/transdermal mismatch; absent/NaN optional parameters; failed/expired/corrupt online cache; late worker result after input changes.
