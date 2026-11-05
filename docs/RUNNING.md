# Running the multi-drug research module

Run `python -m src.app` from this repository using Python with tkinter (tested Python 3.14). No third-party packages or network services are required.

Add 1–32 distinct entries, or select an entry to update/remove it. `synthetic` means an explicitly synthetic fixture. `custom` accepts a chosen name, numeric assumptions and source notes; it does not inherit an approved identity from its name. `catalog` selects a stable identity from the bundled source candidates. The editor does not automatically import real PK values. The listed regimens are the simulation input; apply editor changes with Update selected.

IV-bolus one-compartment curves are available for synthetic and custom what-if parameters. Oral/infusion inputs produce an unsupported-route gap, never an IV substitute. Custom curves are unverified assumptions, not predictions of actual drug behavior. The time grid includes dose boundaries up to 2048 display samples; larger grids are downsampled and cannot be used to locate peaks.

Every unordered drug pair is listed. Source-backed study observations, route mismatches and missing provenance are visible. A reported AUC increase is converted as `1 + percent / 100`, not treated as the ratio itself. Ratios are never multiplied across pairs or applied to the current regimen. Real candidates and auto-extracted facts remain PENDING_REVIEW; licensing, conflict review, individual applicability and the independent validation forest are incomplete. No real combination prediction is admitted in version 0.2.

The JSON report includes entered parameters, gaps, all pairs, source records, snapshot and input hashes, model version and validation status. Export is local. Changing an editor field or regimen invalidates the prior export. This is not a comprehensive interaction database. Absence of an entry means insufficient evidence.

## Throne entry

The integration branch adds 药物模拟器 to both sidebar and galaxy through the shared navigation collection. The twelve existing destinations are preserved. The integration opens an independent local Python window; it is not an embedded or packaged Python runtime.

Provide absolute paths in the Throne panel, or initialize them using `CELESTIAL_DRUG_PYTHON` and `CELESTIAL_DRUG_ROOT`. The launcher uses an argument list without a shell and Python isolated mode. No regimen or private data is sent to Throne, network services or an external model. The module remains open if Throne closes. No installer or executable distribution is included.

For local developer verification, existing `CELESTIAL_FINANCE_OFFLINE=1` now also allows this local module destination. It still suppresses runtime/device services; the UI retains its legacy finance-mode wording. A normal startup retains the original twelve enabled destinations plus the new one.

## Validation

DEV-09 default anatomy rendering embeds the user-provided HTML using local Three.js and the already-installed Windows PySide6/WebEngine6.12 runtime. No CDN/network or package install occurs on launch. Missing graphics/runtime exposes a status message and explicit Simplified View fallback. See [HTML embedding and dependency contract](HTML_EMBEDDING.md). Existing Tk workflows remain available.

`python -m unittest discover -s tests` covers numerical oracle comparison, 32 entries/496 pairs, source gaps, custom identity isolation, invalid input and route refusal. These are engineering tests, not clinical validation. See Mission CEL-DRUG-20261105 for recorded GUI observations and pending independent verification.

## Physiology and generalized substances (0.3)

Use 生理与基因 for optional height (cm), weight (kg), body fat (%), age, physiological sex and measurement provenance. Gene records require gene, result and source. Blank remains unknown; no phenotype is inferred. Inputs remain in memory until a local report is exported; exports include these fields, so inspect before sharing.

The five categories are medicine, supplement, botanical, food_beverage and other. Category does not establish identity or resolve ingredients. Unresolved composition is flagged. These inputs change the report fingerprint and invalidate previous output, but do not change exposure: no personal metabolic modifiers are validated. Mayo and CPIC are declared candidate sources, not connected services. See CONTEXT_EXTENSION.md for the remaining calibrated-model, authorized-source and mixture requirements.
