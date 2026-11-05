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
