# Multi-drug evidence and Throne integration plan

Goal: expandable local regimens, custom compounds, source-linked pair evidence, and a Throne entry.
Spec: README.md and idea-structure.md sections 40–42; user instruction 2026-11-05.
Architecture: keep the existing Python/tkinter kernel/UI; add a bundled public evidence snapshot and a pure report service. Throne launches the explicitly configured local module without sending inputs over the network. No new packages.

- [ ] UI: replace two fixed rows with an editable regimen list, add/remove, catalog/custom choices, route and source fields, scrollable report and exposure table.
- [ ] Evidence: data/catalog.json contains public-source identifiers, locations, retrieval date, context and review status. Retain unresolved licensing and review explicitly. Source-linked observed study ratios are not automatically applied to arbitrary input.
- [ ] Service: src/simulation.py validates 1–32 distinct entries, computes all n(n-1)/2 pairs, rejects missing/ambiguous identities and invalid numbers, separates synthetic exposure from real pending-review inputs, returns an auditable deterministic report with input/snapshot hashes.
- [ ] Tests: three-drug coverage, custom identity isolation, duplicate/empty/oversized input, nonfinite input, pending review, unsupported route, source integrity and no unwarranted numerical interaction prediction.
- [ ] Throne: add a thirteenth destination from the shared navigation list. Launch with configured absolute Python and module paths; show missing dependency and process errors. Preserve all twelve existing entries and galaxy motion.
- [ ] Verify Python tests, desktop build and navigation tests; record actual windows with synthetic inputs; update Mission and relevant evidence/capability records. Independent medical review and independent GUI verification stay pending.

Review focus: names must not impersonate catalog identities; no pairwise multiplication into multi-drug outcomes; missing evidence is not absence of interaction; oral studies must not alter IV curves; changed inputs invalidate old output.

Ruling: use existing galaxy worktree on a new integration branch based on a5bcf8e0e6e7eaadc8f74d2f64b33209b5f4a9d9 (contains origin/main 8ce6a97b84bbc0eb44f423ae335721d45d520314). This preserves the reviewed navigation work without merging it to main.
