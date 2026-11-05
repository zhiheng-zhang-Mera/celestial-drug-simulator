# Body-region UI design — 2026-11-05

Figma editable design: https://www.figma.com/design/LrxztS8daKuloZAMiinlfY?node-id=2-740

Five1440x1024frames: overview2:740, liver2:828, brain2:916, cardiovascular2:1004, excretion2:1092. Native editable text, anatomy vectors and SDS button instances; source ThroneTheme palette, Noto Sans SC font as Chinese Figma fallback for platform typography. Organ hit areas and label cards navigate among detail frames; map title returns to overview. Source cards link to primary documents. Not a runnable simulation or desktop implementation; form/estimate controls are design representations.

Layout: left regimen/physiology/genotype, center body diagram, right selected-region evidence. Categories distinguish mechanism, metabolism, label concerns and excretion. No invented organ concentration, damage severity heatmap, personal probability or therapeutic effect. Single atomoxetine synthetic scenario mirrors existing bounded research module; not main multi-drug inference. The21.6h card is labeled group half-life and not duration of organ damage. Anatomy is a simplified front-view locator, not clinical imaging.

Sources checked2026-11-05: Mayo atomoxetine Description https://www.mayoclinic.org/drugs-supplements/atomoxetine-oral-route/description/drg-20066904 ; CPIC mapping existing runtime source; DailyMed STRATTERA https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=309de576-c318-404a-bc15-660c2b1876fb for metabolism/excretion and cardiovascular label concerns. Text is condensed paraphrase. Source associations are not individual-effect validation. Design requests future source-backed region metadata instead of deriving organ effects directly from AUC.

Visual review: liver detail screenshot inspected for alignment/readability. Structural check overview50editable text nodes and6vectors;20direct organ hit areas created across five states plus label navigation. No desktop functional acceptance or new medical model claimed.

## DEV-05 desktop implementation

Implemented the approved three-column layout in the external Tk desktop module with 20 organ, muscle and system navigation targets, explicit front/back and reproductive layers, neutral stippled tissue masks and source-category highlights. Clicks and keyboard list selection resolve to the same evidence detail and related-region navigation. Original multi-substance regimen, export, physiology and source/PGx workspace remain in the second tab.

The anatomy is an original 2D schematic projection, not a realistic tissue mesh or tissue dynamics model. Initial source-linked coverage is five atomoxetine regions only; other identities and unlisted regions show insufficient evidence. System membership does not propagate effects. Brightness is not dose, intensity, damage or an individualized prediction. Sources remain pending human scientific review.

Validation: 32 unit tests pass; independent code review found no important actionable issues. Developer actual-window checks covered atomoxetine liver/brain, stomach absence, testes/uterus, triceps/back, urinary-to-kidney navigation, deselection clearing and legacy synthetic calculation. DEV-05 recording is local-only and does not establish formal remote acceptance. Figma fresh context was blocked by Starter quota; prior inspected design and committed layout contract used.

## DEV-06 compact layout

Owner requested input consolidation and reduced body whitespace. Drug choice/regimen actions and physiology/PGx controls now share a compact top toolbar. The region directory is190px and body column390px, with remaining width assigned to evidence. The body uses tighter fitted bounds, preserves aspect ratio and existing hit regions. Header is a single row. Regimen numeric inputs are grouped into substance name, dose/interval/count, and model volume/half-life; values and handlers unchanged.

32tests pass. Native window528572: catalog atomoxetine selection, liver hit/evidence and synthetic add/calculate checked. Local60s recording DEV-06; no new clinical/data behavior. Independent body_review read-only Tk inspection at1160x780 found no overflow in either tab and complete435px-high drawing within bounds; no actionable findings. This is bounded layout review, not formal full runtime acceptance.

## DEV-07 volumetric anatomy and navigation

Original parameterized meshes replace flat polygons: paired brain hemispheres with surface folds, tapered lungs/heart, sloped liver, indented kidneys, stomach and explicit reproductive layers; anterior biceps/quadriceps and posterior triceps retain separate depths. A sparse body wire envelope and stippled neutral masks remain the default. This is an anatomical approximation, not a clinical atlas, realistic tissue dynamics or individualized anatomy.

Drag horizontally/vertically to orbit, wheel or +/- to zoom (65–240%), reset to the chosen front/back preset. Picking follows rendered surfaces; a drag does not select; evidence selection preserves the current orbit unless a different front/back preset is required. Drug highlights still use the existing identity-based source associations, not effect strength. All 20 directory entries and legacy workspace remain.

36 unit tests pass. Native window70454 verifies orbit/tilt, button and wheel zoom, brain/kidney picking after transforms, triceps/back, reset and None clearing. Local DEV-07 recordings preserve bounded developer evidence. Independent body_review identified excessive drawing cost; mesh/culling/sparse envelope optimization reduced withdrawn Tk draw benchmark from169ms/~5953items to57–61ms/~1490items. This is not measured displayed FPS or formal independent runtime acceptance. No new dependencies or medical/model data changes.
