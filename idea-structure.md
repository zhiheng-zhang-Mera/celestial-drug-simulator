# Parama-Simulator — idea-structure.md

> **Working title:** Parama-Simulator  
> **Project class:** Evidence-governed mechanistic pharmacology simulator  
> **Primary use case:** For medically literate users who already know which compound(s) and regimen(s) they want to examine, but need a structured, auditable simulation of expected single-drug and multi-drug effects, interaction mechanisms, exposure changes, and interaction-specific adverse effects.  
> **Explicit non-goal:** The system does **not** diagnose disease, recommend a drug, choose an “optimal stack,” prescribe treatment, or replace clinician judgment.

---

## 1. Product thesis

Parama-Simulator answers one constrained question:

> **Given a physiological baseline and a fixed set of compounds, doses, administration routes, formulations, timing, and duration, what does the available pharmacological evidence imply about the expected exposure, mechanism-level activity, physiological effects, adverse effects, and drug-drug interactions?**

The simulator should separate five concepts that are often incorrectly collapsed:

1. **Administered dose** — the nominal amount delivered.
2. **Systemic exposure** — the concentration-time profile reaching circulation.
3. **Site-of-action exposure** — exposure at the relevant tissue or compartment.
4. **Mechanistic activity** — receptor/enzyme/transporter/gene-pathway activity.
5. **Observed or inferred physiological effect** — downstream endpoint changes and adverse-effect burden.

This separation is mandatory because:

- route changes bioavailability and absorption kinetics;
- formulation changes release and concentration profile;
- patient physiology changes distribution, metabolism, and clearance;
- co-administered compounds may alter another drug's exposure;
- receptor/pathway response is usually nonlinear;
- two drugs may interact at PK, PD, tissue, or system-physiology level;
- the absence of a documented interaction is **not** evidence of no interaction.

---

## 2. System boundaries

### 2.1 In scope

- Single-compound simulation.
- Multi-compound simulation.
- Route-aware administration.
- Dose-aware exposure calculation.
- Formulation-aware absorption model.
- Schedule/timing-aware simulation.
- Repeated dosing and steady-state simulation.
- Active metabolites.
- Enzyme/transporter competition, inhibition, and induction.
- Receptor/target competition and occupancy.
- Shared downstream pathway interaction.
- Additive, synergistic, antagonistic, ceiling-limited, and competitive effects.
- Baseline physiology modifiers.
- Optional genetics/pharmacogenomics modifiers.
- Evidence provenance and confidence.
- Uncertainty propagation.
- Monotherapy vs combination comparison.
- Interaction-specific adverse-effect attribution.
- Failure-closed behavior when essential inputs/evidence are missing.

### 2.2 Out of scope

- Drug recommendation.
- Treatment optimization.
- Diagnosis.
- Prescription generation.
- “Best drug” ranking.
- Automatic substitution of one drug for another.
- Unbounded LLM-generated pharmacology.
- Inventing numeric PK/PD parameters from text when no trustworthy source exists.
- Treating observational association as causal mechanism without explicit qualification.
- Predicting a specific person's guaranteed clinical outcome.

---

## 3. Conceptual model

The system is built around a state transition:

```text
S0 = physiological baseline

R = administration regimen set
E = pharmacological evidence graph
M = mechanistic model
U = uncertainty model

Simulation:
S1 = F(S0, R, E, M, U)
```

For each compound `Di`:

```text
AdministeredDose_i
    -> route/formulation adjustment
    -> absorption
    -> systemic exposure C_i(t)
    -> metabolism / transport / elimination
    -> active metabolite exposure
    -> site-of-action exposure
    -> target occupancy/activity
    -> pathway propagation
    -> physiological endpoints
    -> adverse effects
```

For combination therapy, every compound is simulated both independently and jointly:

```text
mono_i = Simulate(S0, {Di})
combo  = Simulate(S0, {D1, D2, ..., Dn})
```

Then compute interaction deltas:

```text
interaction_delta =
    combo_effect
    - expected_noninteractive_combination(mono_1 ... mono_n)
```

`expected_noninteractive_combination()` must be endpoint-specific and must **not** default to simple arithmetic addition.

---

## 4. Top-level architecture

```text
┌─────────────────────────────────────────────┐
│            User / API Input Layer           │
│ physiology + drugs + dose + route + timing │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│         Canonicalization / Validation       │
│ compound identity / unit / route / schema  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│          Pharmacology Evidence KB           │
│ PK / PD / enzymes / targets / pathways / AE │
│ source provenance / evidence strength       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              Simulation Kernel              │
│                                             │
│  1. Administration Model                   │
│  2. PK / Exposure Engine                   │
│  3. Interaction Resolver                   │
│  4. PD / Mechanism Engine                  │
│  5. Physiology Endpoint Engine             │
│  6. Adverse-Effect Engine                  │
│  7. Uncertainty Propagation                │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│         Evidence / Governance Layer         │
│ confidence / gaps / conflicts / blocking   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              Reporting Layer                │
│ mono / combo / interaction delta / trace   │
└─────────────────────────────────────────────┘
```

---

## 5. Repository layout

Recommended repository layout:

```text
Parama-Simulator/
├── README.md
├── idea-structure.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── config/
│   ├── default.yaml
│   ├── evidence_policy.yaml
│   ├── simulation_limits.yaml
│   └── units.yaml
│
├── parama/
│   ├── __init__.py
│   │
│   ├── contracts/
│   │   ├── physiology.py
│   │   ├── compound.py
│   │   ├── regimen.py
│   │   ├── evidence.py
│   │   ├── exposure.py
│   │   ├── mechanism.py
│   │   ├── endpoint.py
│   │   ├── adverse_effect.py
│   │   └── simulation.py
│   │
│   ├── canonicalization/
│   │   ├── compound_resolver.py
│   │   ├── route_resolver.py
│   │   ├── formulation_resolver.py
│   │   ├── unit_normalizer.py
│   │   └── validators.py
│   │
│   ├── knowledge/
│   │   ├── source_registry.py
│   │   ├── compound_registry.py
│   │   ├── mechanism_graph.py
│   │   ├── pk_parameter_store.py
│   │   ├── pd_parameter_store.py
│   │   ├── adverse_effect_store.py
│   │   └── evidence_ranker.py
│   │
│   ├── simulation/
│   │   ├── administration.py
│   │   ├── absorption.py
│   │   ├── distribution.py
│   │   ├── metabolism.py
│   │   ├── elimination.py
│   │   ├── exposure.py
│   │   ├── interaction.py
│   │   ├── pd.py
│   │   ├── pathways.py
│   │   ├── physiology.py
│   │   ├── adverse_effects.py
│   │   ├── uncertainty.py
│   │   └── kernel.py
│   │
│   ├── governance/
│   │   ├── evidence_gate.py
│   │   ├── conflict_detector.py
│   │   ├── simulation_gate.py
│   │   ├── audit.py
│   │   └── statuses.py
│   │
│   ├── reporting/
│   │   ├── monotherapy_report.py
│   │   ├── combination_report.py
│   │   ├── graph_export.py
│   │   ├── markdown_report.py
│   │   └── json_report.py
│   │
│   ├── api/
│   │   ├── schemas.py
│   │   ├── routes.py
│   │   └── app.py
│   │
│   └── cli/
│       ├── run.py
│       ├── inspect_compound.py
│       └── inspect_evidence.py
│
├── data/
│   ├── canonical/
│   ├── raw/
│   ├── fixtures/
│   └── schemas/
│
├── examples/
│   ├── single_drug.yaml
│   ├── two_drug_pk_interaction.yaml
│   ├── two_drug_pd_interaction.yaml
│   ├── route_comparison.yaml
│   └── missing_data_fail_closed.yaml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   ├── property/
│   └── fixtures/
│
└── reports/
    └── .gitkeep
```

---

## 6. Core data contracts

Use typed immutable models where possible. Pydantic/dataclasses are both acceptable; Pydantic is convenient for API validation.

### 6.1 PhysiologicalBaseline

```yaml
patient_id: optional-local-id
age_years: 35
sex_at_birth: optional
height_cm: optional
weight_kg: optional
body_fat_pct: optional

renal:
  egfr: optional
  creatinine: optional

hepatic:
  alt: optional
  ast: optional
  bilirubin: optional
  albumin: optional

cardiovascular:
  resting_hr: optional
  systolic_bp: optional
  diastolic_bp: optional

metabolic:
  fasting_glucose: optional
  fasting_insulin: optional
  hba1c: optional

genetics:
  cyp2d6_phenotype: optional
  cyp2c19_phenotype: optional

custom_biomarkers:
  - name: string
    value: number
    unit: string
```

Rules:

- no diagnostic label is inferred unless explicitly needed for a mechanistic modifier;
- missing values stay missing;
- default population values must be clearly tagged as defaults;
- every inferred modifier must record its source and uncertainty.

### 6.2 DrugRegimen

```yaml
compound: canonical_name_or_id
dose:
  value: 100
  unit: mg
route: oral
formulation: immediate_release
schedule:
  interval_hours: 24
  start_time: "08:00"
duration:
  value: 14
  unit: day
```

Optional:

```yaml
meal_relation: fed|fasted|unknown
administration_site: optional
infusion_duration_min: optional
```

### 6.3 CompoundProfile

```yaml
compound_id: string
canonical_name: string
synonyms: []
active_moiety: string

pk:
  bioavailability:
  absorption:
  distribution:
  metabolism:
  transporters:
  elimination:
  active_metabolites:

pd:
  targets:
  receptor_affinity:
  enzyme_activity:
  gene_regulation:
  dose_response:
  physiological_endpoints:

adverse_effects:
  - endpoint:
    exposure_relationship:
    evidence_ids: []

evidence_ids: []
```

### 6.4 EvidenceRecord

```yaml
evidence_id: EV-XXXX
source_type: label|clinical_ddi|human_pk|pop_pk|rct|observational|in_vitro|animal|mechanistic
citation:
  title:
  url:
  publication:
  year:
population:
route:
dose_range:
finding:
parameters:
quality:
  directness:
  consistency:
  sample_size:
  model_fit:
  recency:
confidence:
```

### 6.5 SimulationResult

```yaml
status: PASS|HOLD_FOR_REVIEW|INSUFFICIENT_EVIDENCE|INVALID_INPUT

monotherapy:
  drug_a:
    exposure:
    mechanisms:
    effects:
    adverse_effects:
    uncertainty:

combination:
  exposure:
  mechanisms:
  effects:
  adverse_effects:
  interaction_deltas:

interaction_summary:
  pk:
  pd:
  coupled_pk_pd:
  physiology_convergence:

evidence:
  coverage:
  conflicts:
  gaps:
  directness:

audit:
  input_hash:
  evidence_hash:
  model_version:
  timestamp:
```

---

## 7. Administration model

The administration layer converts nominal dosing instructions into a dosing event stream.

### Inputs

- dose
- unit
- route
- formulation
- interval
- administration time
- duration
- infusion time
- food state if relevant

### Output

```text
DoseEvent[]
```

Example:

```text
t = 0h    +100 mg oral
t = 24h   +100 mg oral
t = 48h   +100 mg oral
...
```

### Route abstraction

Each route maps to a route model:

```text
oral
  -> bioavailability F
  -> absorption-rate Ka
  -> first-pass metabolism
  -> food effects
  -> formulation-release model

IV bolus
  -> F = 1
  -> immediate systemic input

IV infusion
  -> infusion-rate input

SC / IM
  -> depot absorption
  -> route-specific Ka
  -> local degradation if known

transdermal
  -> quasi-zero-order input when supported

inhaled / intranasal
  -> local + systemic compartments

topical
  -> local exposure model
  -> limited systemic absorption
```

Do not hard-code route assumptions globally. Store route/formulation parameters per compound/evidence set.

---

## 8. PK / exposure engine

### 8.1 MVP model hierarchy

Use the simplest valid model supported by evidence.

Priority:

1. Published population PK or compartment model.
2. Compound-specific one/two-compartment model.
3. Noncompartmental parameter reconstruction.
4. Relative-exposure approximation.
5. If none are supported: qualitative-only simulation.

### 8.2 One-compartment oral model

For a simple first-order absorption / elimination case:

```text
dA_gut/dt = -Ka * A_gut
dA_central/dt = F * Ka * A_gut - Ke * A_central
C(t) = A_central / Vd
Ke = CL / Vd
```

### 8.3 IV infusion

```text
dA_central/dt = infusion_rate - Ke * A_central
```

### 8.4 Repeated dosing

Simulate over time to obtain:

- concentration-time curve `C(t)`
- Cmax
- Tmax
- Cmin
- AUC
- accumulation ratio
- time to steady state
- steady-state average concentration
- active-metabolite exposure

### 8.5 Free drug / protein binding

When supported:

```text
C_free(t) = fu * C_total(t)
```

Use `C_free` for target activity when the evidence/model requires unbound concentration.

### 8.6 EffectiveExposureState

```yaml
compound:
systemic:
  cmax:
  tmax:
  cmin:
  auc:
  css_avg:
  half_life:
  free_fraction:
site_of_action:
  exposure_metric:
active_metabolites:
  - name:
    cmax:
    auc:
uncertainty:
```

This object replaces the vague concept of “physiological effective dose.”

---

## 9. Physiology modifiers

Physiology modifies PK parameters, not the administered dose.

Example abstraction:

```text
CL_individual =
    CL_population
    * renal_modifier
    * hepatic_modifier
    * genotype_modifier
    * interaction_modifier
    * other_covariates
```

Potential modifiers:

- body size / allometric scaling
- body composition
- kidney function
- liver function
- age
- protein binding
- relevant genotype/phenotype
- disease-state covariates only when explicitly modeled
- concurrent inhibitors/inducers
- route-specific physiology

Every modifier must emit:

```yaml
modifier:
  target_parameter: clearance
  value: 0.72
  source: evidence_id
  uncertainty:
  reason:
```

If a required modifier is missing and sensitivity is high, mark:

```text
HOLD_FOR_REVIEW
```

instead of silently assuming a normal value.

---

## 10. Interaction resolver

The resolver operates on a multi-layer directed graph.

### 10.1 Interaction classes

#### A. Absorption interaction

Examples:

- altered gastric pH
- altered gastric emptying
- chelation
- food-dependent absorption
- transporter competition

#### B. Distribution interaction

Examples:

- protein-binding displacement
- tissue transporter competition
- distribution-volume changes

#### C. Metabolic interaction

Examples:

- CYP inhibition
- CYP induction
- UGT interaction
- competition for metabolic pathway

#### D. Elimination interaction

Examples:

- renal transporter inhibition
- tubular secretion competition
- clearance impairment

#### E. Target-level PD interaction

Examples:

- same receptor agonism
- agonist vs antagonist
- partial agonist competition
- enzyme substrate/inhibitor competition

#### F. Pathway-level PD interaction

Different targets converge on the same pathway.

#### G. Physiological convergence

Different pathways converge on the same endpoint.

### 10.2 Interaction graph

Graph node types:

```text
Compound
Metabolite
Route
Compartment
Enzyme
Transporter
Target
Gene regulator
Pathway
Physiological endpoint
Adverse-effect endpoint
```

Graph edge types:

```text
absorbed_by
metabolized_by
inhibits
induces
substrate_of
transported_by
agonizes
antagonizes
partially_agonizes
activates
suppresses
increases
decreases
converges_on
causes
associated_with
```

Every edge has:

```yaml
mechanism:
direction:
magnitude:
dose_range:
exposure_range:
time_dependence:
evidence_ids:
confidence:
```

---

## 11. DDI calculation strategy

### 11.1 PK interaction

A co-administered drug can modify another compound's PK parameters:

```text
CL'_A = CL_A * M_clearance(B)
F'_A  = F_A  * M_bioavailability(B)
Ka'_A = Ka_A * M_absorption(B)
```

More complex models can directly use published exposure ratios:

```text
AUC_ratio = AUC_combination / AUC_monotherapy
Cmax_ratio = Cmax_combination / Cmax_monotherapy
```

Prefer direct human DDI evidence over mechanistic estimates when applicable.

### 11.2 Enzyme competition

When two substrates compete:

```text
v_i = Vmax_i * C_i /
      (Km_i * (1 + C_competitor / Ki_competitor) + C_i)
```

Use only if the required kinetic parameters exist. Otherwise use qualitative interaction class or evidence-derived modifier.

### 11.3 Enzyme inhibition

Support:

- competitive inhibition
- noncompetitive inhibition
- mechanism-based/time-dependent inhibition

MVP can begin with evidence-derived multiplicative modifiers and later add mechanistic kinetics.

### 11.4 Enzyme induction

Induction is time-dependent and must not be modeled as an instantaneous modifier.

Represent:

```text
enzyme_activity(t) -> delayed rise -> delayed return after discontinuation
```

---

## 12. PD / mechanism engine

### 12.1 Target occupancy

Simple occupancy:

```text
Occupancy = C_free / (Kd + C_free)
```

### 12.2 Emax response

```text
Effect(C) = E0 + Emax * C / (EC50 + C)
```

### 12.3 Hill model

```text
Effect(C) =
    E0 + Emax * C^h / (EC50^h + C^h)
```

Use endpoint-specific parameters.

### 12.4 Antagonism / competition

For shared targets, compute occupancy jointly where supported rather than independently summing effects.

### 12.5 Partial agonism

Represent intrinsic efficacy separately from occupancy.

### 12.6 Pathway propagation

A pathway node aggregates upstream signals:

```text
pathway_state =
    aggregator(
      weighted_target_states,
      feedback_state,
      saturation,
      inhibition
    )
```

MVP aggregators:

- weighted sum + clamp
- Hill-like saturation
- competitive normalization
- Boolean / logic gate for hard mechanistic rules

Future:

- ODE pathway models
- Bayesian networks
- probabilistic graphical models

---

## 13. Combination-effect logic

Do not assume one universal definition of synergy.

Each endpoint defines a null/noninteraction model.

Possible models:

### Additive baseline

```text
E_expected = E_A + E_B
```

Only for endpoints where linear addition is justified.

### Bliss independence

Useful when effects can be represented as independent fractional probabilities:

```text
E_expected = E_A + E_B - E_A * E_B
```

### Loewe-like additivity

Useful for compounds acting through similar mechanisms when dose-equivalence assumptions are valid.

### Ceiling-limited combination

```text
E_combined = min(E_max, E_A + E_B)
```

### Mechanism-defined composition

Preferred when known pathways specify the relationship.

Interaction classification:

```text
synergistic
additive
sub_additive
antagonistic
competitive
ceiling_limited
unknown
```

Every classification must state **which null model was used**.

---

## 14. Adverse-effect engine

### 14.1 Monotherapy adverse effects

For each compound:

```yaml
adverse_effect:
  name:
  mechanism:
  exposure_relationship:
  baseline_frequency_if_known:
  severity:
  evidence:
  confidence:
```

### 14.2 Combination adverse effects

Combination AEs are not just merged lists.

Classify each final AE as:

```text
1. inherited
   already present in monotherapy

2. exposure_amplified
   same drug AE intensified because exposure increased

3. shared_endpoint_additive
   multiple drugs push the same physiological endpoint

4. mechanistic_synergy
   interaction produces more-than-null-model risk

5. antagonized
   one drug reduces another's AE mechanism

6. emergent
   new risk appears only in combination

7. uncertain
   plausible mechanism but insufficient evidence
```

### 14.3 Attribution

Each AE report should contain:

```text
AE X
├── contributors: Drug A, Drug B
├── dominant mechanism
├── PK contribution
├── PD contribution
├── exposure change
├── confidence
└── evidence trace
```

---

## 15. Monotherapy vs combination reporting

For `N` compounds, always produce:

1. `N` monotherapy reports.
2. One combination report.
3. One interaction delta report.

### Example report shape

```text
Drug A — monotherapy
  exposure
  main effects
  adverse effects
  uncertainty

Drug B — monotherapy
  exposure
  main effects
  adverse effects
  uncertainty

A + B — combination
  modified exposure of A
  modified exposure of B
  final physiological effects
  final adverse-effect profile
  PK interactions
  PD interactions
  coupled PK/PD interactions

Interaction delta
  what changed relative to noninteractive expectation
  why it changed
  which evidence supports it
```

---

## 16. Evidence system

### 16.1 Evidence hierarchy

Suggested default ranking:

```text
Tier 1
  direct human DDI study
  regulatory label with quantified interaction

Tier 2
  human PK/PD study
  validated population PK model
  controlled clinical study

Tier 3
  observational human evidence
  validated pharmacogenomic annotation

Tier 4
  in-vitro mechanistic evidence
  animal model

Tier 5
  mechanistic inference
  computational prediction
```

This hierarchy is configurable and should not imply that a lower tier is always invalid; it controls confidence and directness.

### 16.2 Conflict preservation

Never silently merge contradictory evidence.

Store:

```yaml
conflict:
  claim:
  evidence_a:
  evidence_b:
  reason:
  resolution:
    status: unresolved|contextualized|superseded
```

### 16.3 Evidence coverage

Compute:

```text
coverage =
    supported_required_edges /
    total_required_edges
```

Also report:

- direct evidence coverage
- mechanistic evidence coverage
- parameter completeness
- unresolved conflict count

---

## 17. Uncertainty model

Keep at least three uncertainty classes:

```text
parameter uncertainty
  uncertainty in numeric PK/PD values

structural uncertainty
  uncertainty in model form

evidence uncertainty
  uncertainty from weak/conflicting sources
```

### MVP propagation

- parameter ranges / distributions
- Monte Carlo sampling
- report median + interval
- sensitivity ranking

### Example

```yaml
effect:
  estimate: 0.58
  interval: [0.42, 0.71]
  main_uncertainty_drivers:
    - clearance estimate
    - EC50
    - DDI inhibition magnitude
```

---

## 18. Governance / fail-closed rules

The simulator should block or downgrade results when needed.

Statuses:

```text
PASS
  sufficient evidence and valid model

RESEARCH_ONLY
  model runs but evidence is incomplete

MECHANISTIC_INFERENCE_ONLY
  no direct combination evidence

HOLD_FOR_REVIEW
  critical ambiguity or missing required field

INSUFFICIENT_EVIDENCE
  cannot support useful prediction

INVALID_INPUT
  invalid dose/unit/route/compound
```

Hard fail examples:

- unresolved compound identity
- missing route when route materially changes exposure
- impossible or unsupported units
- no PK representation and exposure is required
- a required renal/hepatic parameter is missing for a highly sensitive model
- contradictory high-quality evidence cannot be contextualized
- numeric result would require inventing unsupported parameters

---

## 19. Explainability and auditability

Every numeric or categorical output should be traceable:

```text
Final endpoint
    ↓
Pathway node
    ↓
Target / enzyme / transporter
    ↓
Exposure state
    ↓
PK parameter / interaction modifier
    ↓
Evidence record
    ↓
Source
```

Create immutable run artifacts:

```text
reports/<run-id>/
├── input.json
├── normalized_input.json
├── evidence_snapshot.json
├── mechanism_graph.json
├── monotherapy/
│   ├── drug-a.json
│   └── drug-b.json
├── combination.json
├── interaction_delta.json
├── uncertainty.json
├── audit.json
└── report.md
```

Each report should contain:

- input hash
- normalized evidence hash
- model version
- timestamp
- source list
- warnings
- reproducibility metadata

---

## 20. LLM role

LLMs may assist with:

- source discovery
- document extraction
- evidence normalization suggestions
- entity synonym resolution
- human-readable explanation
- mechanism graph proposal
- conflict summarization

LLMs must **not** have authority to:

- invent PK/PD parameters
- override evidence gates
- convert missing evidence into numeric estimates without policy
- silently resolve source conflicts
- label a combination safe
- recommend a regimen

Recommended pipeline:

```text
LLM proposes
    ↓
schema validation
    ↓
deterministic evidence resolver
    ↓
simulation kernel
    ↓
deterministic governance
    ↓
LLM explanation of already-approved result
```

---

## 21. API design

### POST /simulate

Input:

```json
{
  "physiology": {},
  "regimens": [],
  "options": {
    "time_horizon_hours": 336,
    "monte_carlo_samples": 1000,
    "include_monotherapy": true
  }
}
```

Output:

```json
{
  "status": "PASS",
  "run_id": "...",
  "monotherapy": {},
  "combination": {},
  "interaction_delta": {},
  "evidence": {},
  "warnings": []
}
```

### GET /compounds/{id}

Returns canonical profile and available evidence coverage.

### GET /runs/{run_id}

Returns reproducible simulation snapshot.

---

## 22. CLI design

```bash
parama simulate examples/two_drug_pk_interaction.yaml
parama inspect-compound COMPOUND_ID
parama inspect-evidence COMPOUND_ID
parama replay RUN_ID
```

---

## 23. MVP scope

A strong interview/demo MVP should **not** attempt thousands of compounds.

Recommended MVP:

### Compounds

10–20 compounds selected to cover distinct mechanisms:

- CYP substrate
- CYP inhibitor
- CYP inducer
- transporter substrate/inhibitor
- renal clearance-sensitive compound
- receptor agonist
- receptor antagonist
- partial agonist
- active-metabolite case
- route-sensitive compound
- long half-life compound
- depot/slow-release case

Use only compounds with well-documented public evidence.

### Routes

Initial:

```text
oral
IV bolus
IV infusion
SC
IM
transdermal
```

### PK

Initial:

- one-compartment
- first-order absorption
- IV infusion
- repeated dosing
- simple active-metabolite support

### PD

Initial:

- Emax
- Hill
- receptor competition
- weighted pathway propagation

### Interactions

Initial:

- CYP inhibition
- CYP induction
- transporter interaction
- shared target competition
- shared physiological endpoint

### Reports

Initial:

- monotherapy exposure curves
- combination exposure curves
- interaction mechanism graph
- effect comparison
- adverse-effect attribution
- evidence trace
- uncertainty summary

---

## 24. Demonstration scenarios

### Scenario A — route changes exposure

Same compound, same nominal dose, different route.

Goal:

```text
administered dose equal
systemic exposure different
downstream effect different
```

### Scenario B — PK interaction

Drug B reduces clearance of Drug A.

Goal:

```text
A dose unchanged
A exposure increases
A effect and AE burden change
```

### Scenario C — PD convergence

A and B do not change each other's PK but push the same endpoint.

Goal:

```text
PK interaction = none
PD interaction = meaningful
```

### Scenario D — coupled PK/PD

B increases A exposure and independently pushes the same endpoint.

Goal:

```text
combined risk > either mechanism alone
```

### Scenario E — fail closed

Required physiology value missing.

Goal:

```text
no hallucinated assumption
HOLD_FOR_REVIEW
```

---

## 25. Testing strategy

### Unit tests

- unit conversion
- route normalization
- dosing-event generation
- one-compartment PK
- repeated-dose accumulation
- Emax/Hill response
- interaction modifier
- evidence ranking
- status gating

### Integration tests

- input -> normalization -> evidence -> simulation -> report
- monotherapy vs combination
- route comparison
- missing-data blocking

### Property tests

Examples:

```text
For IV bolus:
F must equal 1 unless the model explicitly defines otherwise.

With no interaction edges:
combo exposure of each drug should match monotherapy exposure.

With zero dose:
exposure and drug-mediated effect should be zero.

Increasing clearance:
AUC should not increase in the basic linear PK model.

Adding a pure inhibitor:
target enzyme activity should not increase.
```

### Regression tests

Store golden runs:

```text
fixtures/golden/<scenario>/
```

Compare:

- Cmax
- AUC
- pathway states
- interaction class
- status
- report hashes where deterministic

---

## 26. Performance strategy

For MVP:

- NumPy/SciPy ODE integration.
- Vectorize repeated simulations.
- Cache compound profiles and evidence.
- Monte Carlo in batches.
- Deterministic seed support.
- Avoid LLM calls in the hot simulation loop.

Later:

- JAX for differentiable/vectorized simulation.
- sparse graph propagation.
- parallel uncertainty runs.

---

## 27. Security / privacy

- Physiological data stays local by default.
- No patient-identifying information required.
- Explicitly reject unnecessary PII fields.
- Redact secrets from reports.
- Hash run inputs.
- Separate evidence cache from user data.
- Make cloud/remote model usage opt-in.

---

## 28. Relationship to Quant-Ultra / Research OS

Parama-Simulator can be framed as a second domain kernel under a domain-independent research governance layer.

```text
Research OS
├── Evidence contracts
├── Provenance
├── Reproduction
├── Conflict handling
├── Deterministic governance
│
├── Quant Kernel
│   └── markets / factors / portfolios
│
└── Parama Kernel
    └── compounds / exposure / pathways
```

Shared concepts:

| Research OS concept | Quant domain | Parama domain |
|---|---|---|
| state | market state | physiological state |
| entity | asset/factor | compound/target |
| exposure | portfolio exposure | PK/PD exposure |
| interaction | cross-asset/risk | drug-drug |
| constraints | risk limits | physiology limits |
| evidence | PIT market data | pharmacology evidence |
| validation | backtest/reproduction | PK/PD validation |
| gate | hold/reject | research-only/hold |

The strategic point is to demonstrate that the governance architecture is not domain-specific.

---

## 29. Development phases

### Phase 0 — contracts and scaffolding

Deliver:

- repository skeleton
- typed contracts
- example YAML
- unit normalization
- status enums
- deterministic run ID

### Phase 1 — evidence KB

Deliver:

- canonical compound schema
- source registry
- evidence record
- manually curated first 10–20 compounds
- mechanism graph format

### Phase 2 — PK engine

Deliver:

- oral one-compartment
- IV bolus
- IV infusion
- repeated dosing
- exposure metrics
- physiology modifiers

### Phase 3 — interaction engine

Deliver:

- inhibitor/inducer modifiers
- transporter modifier
- active metabolites
- PK interaction report

### Phase 4 — PD engine

Deliver:

- occupancy
- Emax
- Hill
- receptor competition
- pathway propagation

### Phase 5 — adverse-effect engine

Deliver:

- monotherapy AE model
- exposure-amplified AE
- shared-endpoint AE
- combination attribution

### Phase 6 — uncertainty and governance

Deliver:

- parameter distributions
- Monte Carlo
- coverage/conflict gates
- hold/research-only statuses

### Phase 7 — reporting and demo

Deliver:

- Markdown
- JSON
- Mermaid graph export
- plots
- five canonical demo scenarios

---

## 30. Definition of done for interview MVP

The MVP is ready when one command can:

```bash
parama simulate examples/demo.yaml
```

and generate a report that answers, for every supplied compound:

1. What happens when used alone?
2. What exposure results from the stated dose + route + formulation + schedule?
3. What mechanisms are activated?
4. What expected physiological effects are produced?
5. What adverse effects are supported by evidence?
6. What changes when all supplied compounds are simulated together?
7. Which exposure values changed because of interactions?
8. Which effects are additive, synergistic, antagonistic, competitive, or uncertain?
9. Which adverse effects are inherited vs interaction-specific?
10. What evidence supports each conclusion?
11. What information is missing?
12. How uncertain is the result?
13. Can the entire result be reproduced from the saved run artifact?

That is the core product contract.

---

## 31. Timeline / Regimen-Horizon Engine

The time axis should be treated as an independent architectural stage rather than hidden inside the PK implementation.

### Responsibilities

```text
TimelineEngine
├── ingest DoseEvent[]
├── normalize event time
├── establish simulation horizon
├── classify regimen mode
├── detect overlapping administration windows
├── identify add / stop / dose-change events
├── expose historical vs future boundary
└── generate deterministic time grid
```

### Supported regimen modes

```text
single_dose
acute_course
chronic_maintenance
loading_plus_maintenance
intermittent
taper
prn_event_stream
```

The engine should not contain treatment-success semantics such as “cure.” It models only dosing duration and pharmacological state evolution.

### Suggested contract

```yaml
timeline:
  mode: chronic_maintenance
  start:
  now:
  horizon:
  resolution:
  historical_boundary:
  dose_events:
  regimen_events:
```

### Historical vs future state

The timeline must expose a canonical `now` boundary:

```text
t < now  -> historical / realized
t = now  -> current state
t > now  -> simulated / hypothetical
```

This distinction is required both for simulation provenance and desktop visualization.

---

## 32. Repeated Dosing, Half-Life, Accumulation, and Steady State

Steady-state behavior must be part of the core simulation path.

### Required parameters

```text
dose
route
formulation
bioavailability
absorption rate
dosing interval τ
clearance
distribution volume
effective half-life
active metabolites
interaction modifiers
physiology modifiers
```

### Basic relationships

```text
Ke = ln(2) / t1/2
t1/2 = ln(2) / Ke
```

For basic linear repeated dosing, the engine should derive or numerically estimate:

```text
Cmax_ss
Cmin_ss
Css_avg
AUC_tau_ss
accumulation_ratio
time_to_steady_state
washout_time
```

Do not assume “5 half-lives” as a universal exact steady-state rule. It may be used as a rough explanatory heuristic only when the underlying model is first-order and no important active metabolite, nonlinear kinetics, induction, or time-varying clearance invalidates the simplification.

### Recompute steady state after interaction changes

When a co-administered compound alters:

```text
CL
F
Ka
Vd
metabolite formation
enzyme activity
transporter activity
```

the simulator must recompute the future concentration-time trajectory and, where applicable, the new steady state.

Do not apply only a static “interaction multiplier” to the final endpoint.

---

## 33. Acute-Course vs Chronic-Maintenance Execution

Both regimen classes use the same simulation kernel but different output priorities.

### Acute-course priorities

```text
first-dose Cmax
Tmax
early AUC
time-to-effect
short-term accumulation
course-end exposure
peak interaction window
post-final-dose washout
```

### Chronic-maintenance priorities

```text
time-to-steady-state
steady-state Cmax
steady-state Cmin
Css_avg
AUC_tau_ss
accumulation ratio
active-metabolite accumulation
persistent inhibition / induction
pathway adaptation where modeled
new steady state after regimen change
post-discontinuation recovery
```

### State transitions

Support transitions such as:

```text
maintenance A
    -> add drug B
    -> transitional PK state
    -> new steady state
    -> remove B
    -> washout / enzyme recovery
    -> recovered A-only steady state
```

This transition model is more important than a single static steady-state snapshot.

---

## 34. Time-Dependent Interaction Contract

Interaction edges should explicitly support time dependence.

```yaml
interaction_edge:
  type:
  source:
  target:
  onset_model:
  offset_model:
  reversibility:
  time_constant:
  dose_dependency:
  exposure_dependency:
  evidence_ids:
  confidence:
```

### Example categories

```text
competitive inhibition
  fast onset / fast offset

mechanism-based inhibition
  onset linked to exposure
  recovery linked to enzyme turnover

enzyme induction
  delayed onset
  delayed offset

long-half-life parent drug
  persistent residual exposure

active metabolite
  delayed / extended downstream activity
```

The interaction resolver should return functions or time-indexed modifiers whenever a static scalar is insufficient.

---

## 35. Visualization Architecture

Desktop visualization should be treated as a first-class reporting contract rather than UI-only decoration.

### 35.1 Stable visual grammar

Use orthogonal encodings:

```text
compound identity -> color
historical/future -> line style + marker fill
uncertainty       -> shaded interval
regimen events    -> vertical markers
thresholds        -> reference line / band
selection         -> emphasis / outline
```

Do not encode multiple independent meanings with the same visual channel.

### 35.2 Historical vs future convention

Canonical rule:

```text
historical / realized
  solid line
  filled markers

future / simulated
  dashed line
  hollow markers

alternative what-if branch
  dash-dot or secondary dashed style
```

The simulation result should therefore expose the provenance of every plotted point or segment:

```yaml
point:
  time:
  value:
  state: historical|future|what_if
  source: observed|reconstructed|simulated
  uncertainty:
```

### 35.3 Compound colors

Assign colors deterministically from a stable compound identity mapping.

Requirements:

- same compound retains the same color across all views;
- active metabolites use related secondary shades;
- no critical meaning depends only on color;
- support dark/light mode;
- support color-vision deficiency;
- allow user override at the presentation layer without changing simulation artifacts.

### 35.4 Concentration-time plot contract

The reporting layer should expose plot-ready data rather than making the UI reconstruct pharmacology from prose.

```yaml
concentration_series:
  compound_id:
  parent_compound_id:
  unit:
  points:
    - t:
      concentration:
      state:
      uncertainty_low:
      uncertainty_high:
  events:
    - t:
      type: dose|start|stop|dose_change|route_change
      label:
  references:
    - type: therapeutic_window|risk_threshold|target_range
      low:
      high:
      evidence_ids:
```

### 35.5 Steady-state transition view

Expose explicit steady-state segments:

```yaml
steady_state_segments:
  - start:
    end:
    regimen_hash:
    cmax_ss:
    cmin_ss:
    css_avg:
    auc_tau:
    status: approaching|stable|transition|washout
```

This supports visualization of:

```text
old steady state
-> interaction transition
-> new steady state
-> withdrawal transition
-> recovered state
```

### 35.6 Mechanism graph visualization

Graph nodes should expose:

```text
node type
compound ownership
confidence
evidence coverage
historical/future state
```

Graph edges should expose:

```text
activation / inhibition semantics
strength
confidence
time dependence
evidence links
```

Future or hypothetical mechanism edges should be visually distinguishable from evidence-backed historical or observed state transitions.

### 35.7 Adverse-effect contribution view

Expose attribution data:

```yaml
ae_contribution:
  endpoint:
  contributors:
    - compound:
      contribution_type:
      magnitude:
  pk_component:
  pd_component:
  interaction_component:
  uncertainty:
```

The UI may then render stacked contribution bars, mechanism traces, or endpoint-specific timelines.

---

## 36. Desktop Application View Model

The UI should consume a stable view-model layer derived from simulation artifacts.

Recommended separation:

```text
SimulationResult
      ↓
ReportModel
      ↓
VisualizationModel
      ↓
Desktop UI
```

The desktop application should never directly infer missing pharmacology from raw evidence records.

### Core views

```text
1. Regimen Timeline
2. Concentration-Time Explorer
3. Steady-State Transition View
4. Monotherapy vs Combination Comparator
5. Interaction Mechanism Graph
6. Physiological Endpoint View
7. Adverse-Effect Contribution View
8. Evidence / Uncertainty Inspector
```

### Selection synchronization

Selecting a compound in one view should synchronize:

```text
compound highlight
mechanism edges
exposure curve
endpoint contribution
AE contribution
evidence records
```

This requires a stable `compound_id` and graph node identity across all artifacts.

---

## 37. Updated Recommended Repository Layout

The repository layout should explicitly include timeline and visualization-model layers:

```text
Parama-Simulator/
├── README.md
├── idea-structure.md
│
├── parama/
│   ├── contracts/
│   ├── canonicalization/
│   ├── knowledge/
│   ├── timeline/
│   │   ├── dose_events.py
│   │   ├── regimen_modes.py
│   │   ├── horizon.py
│   │   └── state_boundary.py
│   │
│   ├── simulation/
│   │   ├── administration.py
│   │   ├── pk.py
│   │   ├── steady_state.py
│   │   ├── exposure.py
│   │   ├── interaction.py
│   │   ├── pd.py
│   │   ├── pathways.py
│   │   ├── physiology.py
│   │   └── adverse_effects.py
│   │
│   ├── uncertainty/
│   ├── governance/
│   ├── reporting/
│   │   ├── report_model.py
│   │   ├── visualization_model.py
│   │   ├── graph_export.py
│   │   ├── markdown_report.py
│   │   └── json_report.py
│   │
│   ├── desktop/
│   │   ├── view_models/
│   │   └── adapters/
│   │
│   ├── api/
│   └── cli/
│
├── examples/
├── tests/
└── reports/
```

The desktop UI itself may live in a separate frontend package or application repository if the chosen technology stack makes that cleaner.

---

## 38. Updated MVP Definition

The interview/demo MVP should now prove four independent capabilities:

```text
A. mechanistic PK/PD simulation
B. time-aware repeated-dose / steady-state behavior
C. interaction-aware monotherapy vs combination analysis
D. auditable desktop visualization
```

Minimum demo set:

```text
1. same nominal dose, different route
2. acute finite-course regimen
3. chronic maintenance reaching steady state
4. add-on inhibitor causing a new steady state
5. PD convergence without meaningful PK change
6. withdrawal / washout transition
7. fail-closed missing-data case
```

The concentration-time view should visibly demonstrate:

```text
historical = solid + filled
future     = dashed + hollow
compound   = stable color
uncertainty = shaded interval
events      = vertical markers
```

This visual grammar should be treated as part of the product contract and regression-tested at the view-model level.

---

## 39. Project Status and Release Baseline

This specification is a **design baseline only**. It does not establish that a simulator, curated compound database, calibrated population model, desktop application, or clinically valid result already exists.

Proposed design-to-MVP release sequence:

```text
v0.1-contracts       schemas, units, provenance, governance states
v0.2-pk-timeline     oral/IV exposure and repeated-dose fixtures
v0.3-interactions    one quantified PK interaction and steady-state transition
v0.4-pd              target, endpoint, and attribution fixtures
v0.5-governance      uncertainty, evidence coverage, and fail-closed reports
v0.6-demo            bounded end-to-end research demonstration
```

No version should be described as medically validated without a separate, predeclared validation program and appropriate expert/regulatory review.

---

## 40. Data and Evidence Admission Contract

Every parameter admitted to the curated knowledge layer must include:

```yaml
parameter_id:
compound_id:
parameter_type:
value_or_distribution:
unit:
route:
formulation:
dose_context:
population:
time_context:
source_id:
source_location:
extraction_method:
evidence_tier:
review_status:
uncertainty:
valid_from:
supersedes:
```

Admission rules:

- reject values without units or source location;
- preserve population and route specificity;
- never average conflicting values without an explicit model and rationale;
- keep extracted, normalized, and derived values distinguishable;
- retain licensing and redistribution constraints;
- require human review for values proposed through automated extraction;
- version parameter sets independently from simulator code.

Synthetic fixtures must be explicitly labeled and must not be presented as real compound profiles.

---

## 41. Initial Compound and Scenario Selection

The first dataset should be selected for **mechanistic coverage and evidence quality**, not drug count.

Selection scorecard:

| Criterion | Required question |
|---|---|
| Evidence availability | Are route-specific human PK parameters traceable? |
| Mechanistic clarity | Is the relevant enzyme, transporter, target, or endpoint explicit? |
| Quantified interaction | Is effect magnitude reported with conditions and uncertainty? |
| Model fit | Can the behavior be represented by the declared MVP model? |
| Licensing | May the necessary data be stored or redistributed? |
| Safety of presentation | Can the example avoid patient-specific recommendation? |

The initial public fixtures should include:

```text
one synthetic route-comparison profile
one synthetic repeated-dose profile
one evidence-linked PK interaction pair
one bounded PD convergence pair
one deliberately incomplete profile for fail-closed testing
```

Candidate real compounds must remain `PENDING_REVIEW` until sources, licenses, units, population scope, and parameter conflicts are reviewed.

---

## 42. Acceptance Evidence Matrix

| Capability | Required evidence | Stop condition |
|---|---|---|
| Unit normalization | dimensional tests and round-trip fixtures | silent unit coercion |
| Oral/IV PK | analytic reference cases within declared tolerance | unexplained solver drift |
| Repeated dosing | accumulation and steady-state property tests | dose events lost or reordered |
| Interaction onset/offset | transition fixture with trace-linked mechanism | instantaneous effect assumed without declaration |
| Evidence resolution | source, tier, context, and conflict fixture | missing source treated as zero effect |
| Uncertainty | sensitivity or sampled interval with fixed seed | false precision from point-only output |
| Monotherapy comparison | common baseline and attributable deltas | incomparable scenarios silently compared |
| Fail-closed behavior | missing critical input yields governed status | report emits safety-like conclusion |
| Visualization model | snapshot tests for line, marker, event, and interval semantics | critical meaning encoded only by color |
| Reproducibility | clean run with version/hash manifest | result cannot identify inputs and evidence snapshot |

Clinical accuracy, population transportability, and adverse-event incidence are outside the MVP acceptance matrix.

---

## 43. Initial Development Backlog

### P0 — safe computational foundation

- Freeze identifiers, units, route enums, and provenance fields.
- Implement contract and dimensional validation.
- Implement deterministic dose-event ordering.
- Add analytic PK reference fixtures.
- Implement immutable run manifests and trace records.
- Add fail-closed behavior for missing critical parameters.

### P1 — bounded mechanistic demonstration

- Implement repeated dosing and steady-state transitions.
- Add one evidence-linked inhibition example.
- Add one target occupancy/Emax example.
- Implement monotherapy vs combination comparison.
- Add uncertainty and sensitivity output.
- Generate JSON and Markdown reports.

### P2 — research interface

- Export concentration-time and mechanism-graph view models.
- Add evidence/conflict inspection views.
- Add parent/alternative scenario comparison.
- Add a small curated compound registry after evidence review.
- Produce a reproducible demonstration package.

No P2 interface work should mask missing P0 validation or provenance.

---

## 44. Run Manifest and Reproducibility Contract

Every run must emit:

```yaml
run_id:
simulator_version:
contract_version:
knowledge_snapshot_id:
compound_profile_ids: []
physiology_profile_id:
regimen_hash:
solver:
solver_version:
solver_tolerances:
seed:
started_at:
completed_at:
status:
warnings: []
missing_inputs: []
output_hashes: {}
```

Comparative reports may only compare runs when their baseline, units, population assumptions, evidence snapshots, and solver semantics are compatible or explicitly reconciled.

---

## 45. Architecture and Scientific Decision Records

Record an ADR or scientific decision record when changing:

- a PK/PD equation or solver;
- an interaction composition rule;
- an evidence tier or conflict policy;
- a critical parameter source;
- a population or physiology assumption;
- a governance status or claim template;
- a visualization encoding with scientific meaning.

Each record should state context, alternatives, evidence, decision, uncertainty, compatibility impact, and revisit trigger.

---

## 46. Project Kickoff Checklist

- [ ] Select implementation language, numeric libraries, and supported runtime.
- [ ] Freeze the `v0.1` contract, unit, and provenance schemas.
- [ ] Create synthetic oral, IV, and repeated-dose reference fixtures.
- [ ] Define solver tolerances and analytic comparison cases.
- [ ] Select one candidate quantified interaction and complete evidence review.
- [ ] Define knowledge snapshot and run-manifest hashing.
- [ ] Implement fail-closed missing-input fixtures before adding more compounds.
- [ ] Add clean-environment CI for contracts, math, reports, and deterministic replay.
- [ ] Produce the first bounded report with explicit non-claims.
- [ ] Review public documentation for medical-safety wording before the first tag.
