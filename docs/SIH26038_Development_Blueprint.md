# SIH26038 (NETRA-DR) — Four-Phase Development Blueprint

| Field | Value |
|---|---|
| Document | Development Blueprint v1.0 |
| Date | 23 September 2026 |
| Derived from | `SIH26038_Final_PRD.md` v2.0 (the only requirements authority; this blueprint adds no requirements) |
| Scope of this document | Phase architecture, ownership, contracts, pipelines, testing, workflow, and fresh-context prompts. **No code. No implementation.** |
| Intended location | `docs/BLUEPRINT.md` in the project repository (prompts reference it by that path) |

## 0. How to read this document

### 0.1 Labels

| Label | Meaning in this blueprint |
|---|---|
| `[VERIFIED]` | Recorded as verified in PRD v2.0 (checked by the team on 23 Sep 2026). **Not re-checked by this blueprint.** |
| `[PS REQUIREMENT]` | Stated in the problem statement (PRD §3). |
| `[ENGINEERING DECISION]` | Proposed here with a rationale. Reversible only through a decision record (`docs/decisions/`) at a phase gate. |
| `[NEEDS VERIFICATION]` | Must be checked before anything relies on it. |
| `[OPEN QUESTION]` | Undecided. PRD questions keep their IDs (OQ-xx); new ones raised here are BQ-xx (Section R). |
| `[BLOCKER]` | Work downstream of this item cannot start or finish until it is resolved. |
| `[MOCK — TEMPORARY ONLY]` | Placeholder that must not exist in the final system; each one states what replaces it and when. |

### 0.2 Three items to resolve before Phase 1 is planned in time

1. **BQ-01 `[BLOCKER]` — What is the 30 Sep 2026 deadline?** PRD §1 records "PS deadline shown: 30 September 2026" from an unofficial mirror. That is 7 days after this blueprint's date. If it is an idea/proposal submission deadline, the four phases run after it. If a working prototype must exist by then, only a reduced L1 is realistic and this blueprint must be re-scoped. **Verify on sih.gov.in together with OQ-01.** This blueprint deliberately assigns no durations to phases; the team sets time-boxes once BQ-01 is answered.
2. **OQ-02 `[BLOCKER for Phase 2 training]` — Is training outside MATLAB acceptable to MathWorks?** Until answered, every training plan in this blueprint assumes MATLAB Deep Learning Toolbox (PRD MAT-002 default).
3. **BQ-03 `[BLOCKER for Phase 1 exit]` — Licences and compute.** Each of the three people needs MATLAB with the PS toolboxes and Simulink; discrete-event blocks (SimEvents) are not in the PS tool list (SIM-002); GPU availability is unverified (A-07). None of these are assumed.

### 0.3 Principles this blueprint applies

- **Contracts before code.** Every module talks to others only through the documented contracts in Section I. This is what lets three people work in parallel inside a phase.
- **Baseline before learned model** (PRD MLR-001/002, DEC-01). No model architecture is locked here (DEC-06); Section K lists candidates and the evidence that decides between them.
- **External test sets are sealed until Phase 4** (MLR-003, EVAL-005). They are physically and programmatically inaccessible to Phases 1–3.
- **Fail closed.** An undetermined threshold is stored as `null` in configuration, and the stage that needs it refuses to run rather than using a default.
- **Everything the next phase needs is written down in the repository.** No decision lives only in a chat.

---

# SECTION A — FINAL FOUR-PHASE ARCHITECTURE

## A.1 Why this structure and not the generic one

The generic example (Foundation/Core ML → CV → Application → Simulation) was tested against the PRD and changed in four places:

1. **No models in Phase 1.** Model design is blocked by questions only Phase 1 can answer: whether training may happen outside MATLAB (OQ-02), what "sub-pixel MA detection" means (OQ-04), what "hemorrhage classification" means (OQ-05), whether Messidor-2 grade labels are obtainable (OQ-15), and whether any NV-labelled data exists (OQ-16). Training before splits are deduplicated and contamination-checked (DAT-003…005) would also produce results that later have to be thrown away.
2. **Explainability is split across two phases.** Grad-CAM is a property of the grading model (MLR-009 requires the grader to support it; MAT-004 requires MATLAB computation), so it is built and checked with the grader in Phase 2. The clinical-criteria panel, lesion-evidence mapping, and heatmap–lesion overlap need all model outputs together, so they are Phase 3.
3. **Simulink is split across two phases.** The queuing model needs no ML (DEC-04) and can be built and validated against M/M/c theory (SIM-010) in Phase 3. It can only be *parameterised* with measured processing times (BE-003) and review times (PERF-003) once the integrated system exists, so parameterisation and optimisation are Phase 4.
4. **All external evaluation is concentrated in Phase 4.** MLR-003 allows external test sets to be used once, after the operating point is frozen. That can only happen after the whole system is frozen.

## A.2 The four phases

| | PHASE 1 | PHASE 2 | PHASE 3 | PHASE 4 |
|---|---|---|---|---|
| **Name** | Foundation: Verified Data, Frozen Contracts, Walking Skeleton | Core Image Intelligence | Clinical Workflow Product | Validation, District Simulation & Final System |
| **Objective** | Make it possible to develop models and product components in parallel without rework: verified data, leak-free splits, pinned environment, configuration, interface contracts, metric library, and a pipeline skeleton that runs end-to-end on mock stages. | Deliver a functioning, contract-conformant, MATLAB-executable model or algorithm for **every** PS analysis module (L1, mandatory), then improve modules where evidence supports it (L2, time-boxed). | Turn the models into a usable human-in-the-loop system: orchestrated pipeline, explainability layer, uncertainty flags, routing, storage, audit, reports, the technician and ophthalmologist screens, and a validated Simulink model structure. | Freeze the system, measure it honestly, and finish it: one-shot external evaluation, ablation, benchmark comparison, rating study, timed review, parameterised simulation and optimisation, hardening, packaging, and the SIH demonstration. |
| **Why it exists** | PRD DAT-001…015, OPS-001, NFR-003, BE-002; blocking OQs. | PS-02…PS-15 analysis modules; MLR-001…010. | PS-14, PS-16, PS-17, PS-18 (structure); FR-013…016; BE-001…005; UX-001…005. | PS-12, PS-19, PS-20, PS-23, PS-24; AC-014…021; DEP-001…005. |
| **Inputs** | PRD v2.0; PS text; dataset sources; licences; mentor access. | Phase 1 output bundle (Section E.9). | Phase 2 output bundle (Section F.9). | Phase 3 output bundle (Section G.9). |
| **Outputs** | Repo, env record, config system, contracts, validators, skeleton with mocks, dataset register, master metadata table, frozen splits, contamination registry, datastores, metric library, evaluation protocol, resolved/escalated OQs. | Versioned model artifacts + model cards + stage wrappers + internal-validation results + baseline-vs-learned comparisons + Grad-CAM + calibration + frozen-for-now operating point proposal. | Integrated prototype running end-to-end on internal data; evidence bundle; reports; review workstation; audit log; per-stage timing logs; Simulink model passing M/M/c check with provisional parameters. | Frozen release; external results with CIs; ablation and benchmark tables; XAI overlap + rating results; timed-review results; parameterised scenarios and optimised configuration with ranges; packaged demo; final documentation. |
| **Major components** | M10 skeleton, M12 metric core, data layer | M1–M5, M6 (Grad-CAM part), M7 (calibration part) | M6 (criteria/overlap), M7 (flags), M8, M9 (SCR-01…05), M10, M11 (structure) | M11 (parameters/optimisation), M9 (SCR-06), M12 (full), deployment |
| **Depends on** | Nothing internal | Phase 1 gate | Phase 2 gate | Phase 3 gate |
| **Person 1** | Data pipeline | Preprocessing, image quality, enhancement, OD/fovea | Orchestration, storage, routing, errors, auth, reports | Freeze, hardening, packaging, final integration, demo |
| **Person 2** | Platform: repo, env, config, contracts, skeleton, tests | Vessels and all lesion modules | Explainability layer; Simulink model structure | Simulation parameterisation, sweeps, optimisation, SCR-06 |
| **Person 3** | Metric library, evaluation protocol, open-question resolution | Grading, operating point, calibration, Grad-CAM, uncertainty candidate | All technician and ophthalmologist screens; review timing | External evaluation, ablation, benchmarks, rating study, timed review |
| **Integration point** | Skeleton pipeline runs a synthetic fixture through all mock stages and writes a valid case record. | Skeleton runs internal-test images through all real Phase 2 stages (no UI). | End-to-end: upload → verdict → analysis → evidence → report → queue → review decision → audit, on internal images. | Frozen release runs the demo scenario; simulation consumes measured timings. |
| **Testing** | Config, contract, data-integrity, metric-correctness tests. | Per-model unit/ML tests; contract conformance; determinism; import equivalence if applicable. | Integration, failure injection, gating, consistency, UI tests. | E2E, performance, security/dependency audit, simulation validation, demo rehearsal. |
| **Documentation** | Phase 1 report; dataset cards; contracts; evaluation protocol; decision records. | Model cards; Phase 2 report; baseline-comparison tables. | Workflow docs; routing policy doc; evidence/criteria mapping doc; Simulink model doc. | Results dossier; toolbox usage map; setup guide; demo script; final report. |
| **Definition of Done** | Section E.7 | Section F.7 | Section G.7 | Section H.7 |
| **Exit criteria** | Phase Gate 1 (E.8) | Phase Gate 2 (F.8) | Phase Gate 3 (G.8) | Phase Gate 4 (H.8) |

## A.3 Mapping to PRD delivery levels (§12.2)

| PRD level | Where it is produced |
|---|---|
| **L1 — minimum complete prototype** | Phase 2 must end with an L1 form of every PS analysis module. Phase 3 must end with the L1 product (report, single-screen review, Simulink model). Phase 4 completes L1 evaluation on at least one external set. **L1 is non-negotiable at every gate** (DEC-11). |
| **L2 — target SIH version** | Phase 2 time-boxed improvements; Phase 3 uncertainty/OOD flag and overlap computation; Phase 4 rating study, ablation, benchmark comparison, measured-latency simulation with optimisation. |
| **L3 — stretch** | Only after the Phase 4 gate items for L2 are stable. Not planned in detail here. |

---

# SECTION B — PHASE DEPENDENCY GRAPH

## B.1 Phase chain

```
 PRD v2.0 + PS + dataset sources + mentor access
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 1  Foundation                                          │
│  P2 platform ─┐                                              │
│  P1 data ─────┼──► skeleton runs synthetic case (mock stages)│
│  P3 metrics + OQ resolution ─┘                               │
└──────────────┬───────────────────────────────────────────────┘
               │  GATE 1: frozen splits · contracts v1 · metric lib · OQ-02/04/05/15/16 answered or escalated
               ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 2  Core Image Intelligence                             │
│  P1 preprocess(FOV) ──► used by P2 and P3                    │
│  P1 IQA/enhance/OD-fovea   P2 vessels+lesions   P3 grading   │
│            └───────────────┴──────► P3 Grad-CAM, calibration │
│  all ──► L1 checkpoint ──► L2 time-box ──► skeleton runs real│
└──────────────┬───────────────────────────────────────────────┘
               │  GATE 2: every PS analysis module has an L1 artifact + model card + contract tests
               ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 3  Clinical Workflow Product                           │
│  P1 orchestration/storage/routing/report ◄── P2 evidence     │
│  P3 screens ◄── P1 service API                               │
│  P2 Simulink structure (independent) ──► M/M/c check         │
└──────────────┬───────────────────────────────────────────────┘
               │  GATE 3: E2E on internal data · timing logs · audit · Simulink validated
               ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 4  Validation, Simulation, Final System                │
│  P1 freeze + timing benchmark ──► P3 external eval / studies │
│                               └─► P2 simulation parameters   │
│  P3 timed review times ──► P2 final simulation + optimise    │
│  all ──► P1 final integration ──► demo                       │
└──────────────┬───────────────────────────────────────────────┘
               │  GATE 4
               ▼
        FINAL INTEGRATED SYSTEM (tag v1.0-sih)
```

## B.2 Critical path (longest dependency chain)

Dataset access verified (P1, Ph1) → splits frozen (P1, Ph1) → preprocessing/FOV (P1, Ph2) → grading baseline + Grad-CAM + calibration (P3, Ph2) → operating point proposal (P3, Ph2) → evidence bundle (P2, Ph3) → review workstation (P3, Ph3) → freeze (P1, Ph4) → external evaluation + timed review (P3, Ph4) → simulation parameterised with measured review time (P2, Ph4) → demo (all).

The two external-human dependencies that sit on or near this path — **clinician raters/reviewers (R-05)** and **Messidor-2 labels (OQ-15)** — are started in Phase 1 precisely because they cannot be accelerated later.

---

# SECTION C — REPOSITORY STRUCTURE

`[ENGINEERING DECISION]` Single repository, MATLAB Project (`.prj`) for path management, MATLAB package namespace `+netra`. Rationale: PS-01/MAT-001 require a MATLAB runtime; one repo keeps contracts, code, and docs versioned together; a package namespace prevents name collisions across three people's code.

`[ENGINEERING DECISION]` The UI is built **programmatically** (`uifigure`-based classes in `.m` files) rather than in App Designer `.mlapp` files. Rationale: `.mlapp` files are binary-like and effectively unmergeable in Git; `.m` classes can be reviewed, diffed, and tested with `matlab.uitest`. UX-006 prefers MATLAB-native UI; this choice satisfies it. Reversible via decision record if the team prefers App Designer, in which case one owner per `.mlapp` file becomes mandatory.

```
netra-dr/
├── NetraDR.prj                    MATLAB Project (path, startup/shutdown)
├── README.md
├── .gitignore  .gitattributes     data/, artifacts/, configs/local/ ignored; *.slx *.mat marked binary
├── configs/
│   ├── default/                   pipeline, iqa, enhancement, routing, report, ui, auth, logging (JSON)
│   ├── thresholds/                derived thresholds WITH provenance; null until derived
│   ├── models/model_registry.json which artifact serves each stage
│   ├── simulation/                parameter sets with per-parameter source tags
│   ├── experiments/               training/eval run configs
│   ├── schema/                    JSON schemas for every config file
│   └── local/  (git-ignored)      machine-specific overrides; template committed as local.example.json
├── src/+netra/
│   ├── +config/                   load, merge, validate, hash
│   ├── +contracts/                validators for every contract in Section I
│   ├── +data/                     manifests, datastores, split access guard, dedup
│   ├── +preprocess/               FOV detection, crop, canonical image space
│   ├── +iqa/                      adequacy assessment
│   ├── +enhance/                  CLAHE, illumination normalisation, denoising
│   ├── +anatomy/                  OD, fovea, vessels
│   ├── +lesions/                  MA, EX, HE, SE, NV
│   ├── +grading/                  grading inference, decision rule
│   ├── +calibration/              calibration fit/apply
│   ├── +uncertainty/              low-confidence, OOD, inconsistency, NV-priority flags
│   ├── +explain/                  Grad-CAM, overlays, criteria panel, overlap metrics
│   ├── +report/                   deterministic report template + export
│   ├── +pipeline/                 orchestrator, stage registry, timing
│   ├── +routing/                  review routing policy engine
│   ├── +storage/                  case store, audit log (append-only)
│   ├── +auth/                     local authentication, roles
│   ├── +service/                  functions the UI calls (Section I.13)
│   ├── +ui/                       screen classes SCR-01…06
│   ├── +eval/                     metric library, CI methods, calibration metrics
│   ├── +logging/
│   └── +mock/                     [MOCK — TEMPORARY ONLY] stubs; forbidden in release config
├── training/<task>/               training scripts + README per model task
├── evaluation/                    experiment runners: internal, external, ablation, benchmark, overlap, rating analysis
├── simulink/
│   ├── models/                    .slx files
│   ├── params/                    parameter builders (read configs/simulation)
│   ├── validation/                M/M/c analytical comparison
│   └── optimisation/
├── scripts/                       setup, dataset fetch helpers (manual-download aware), dependency audit, demo runner
├── tests/
│   ├── unit/ integration/ data/ ml/ ui/ e2e/ perf/ failure/ security/ simulation/
│   └── fixtures/                  SYNTHETIC images and small JSON fixtures only (no dataset images unless licence verified)
├── data_manifests/                committed: dataset register, master metadata table, split files, hashes, contamination registry
├── docs/
│   ├── BLUEPRINT.md  prd/  context/PROJECT_CONTEXT.md
│   ├── contracts/  decisions/  phases/  model_cards/  dataset_cards/
│   ├── protocols/                 evaluation protocol, rating-study protocol, timed-review protocol
│   ├── results/                   generated tables/plots (from committed runs only)
│   └── demo/
├── data/        (git-ignored)     raw + processed images; root supplied via environment variable
└── artifacts/   (git-ignored)     model artifacts, run outputs, case store; root supplied via environment variable
```

Conditional, only if OQ-02 is answered "yes": `training_external/` (quarantined; non-MATLAB training code; its outputs enter `+netra` only through import + MAT-006 equivalence test).

| Directory | Purpose | Owner | Allowed contents | Must not contain | Depends on |
|---|---|---|---|---|---|
| `configs/` | All tunable values | P2 (schema); each module owner for their file | JSON + schemas | Secrets, absolute paths, patient data | — |
| `configs/thresholds/` | Derived thresholds | Owner of the deriving module | Value + provenance (split, run id, commit, date) | Hand-typed numbers without provenance | Evaluation runs |
| `src/+netra/+config, +contracts, +pipeline, +logging` | Platform | P2 (Ph1), P1 (Ph3+) | Platform code | Model logic | — |
| `src/+netra/+data` | Data access | P1 | Loaders, guards, dedup | Hardcoded dataset paths | configs, data_manifests |
| `+preprocess +iqa +enhance` + OD/fovea in `+anatomy` | Quality & anatomy | P1 | Stage code | — | +contracts |
| vessels in `+anatomy`, `+lesions` | Segmentation | P2 | Stage code | — | +preprocess |
| `+grading +calibration` | Grading | P3 | Stage code | — | +preprocess |
| `+uncertainty +explain` | Evidence | P3 (Grad-CAM, Ph2), P2 (rest, Ph3) | Stage code | — | grading, lesions, anatomy |
| `+report +routing +storage +auth +service` | Product backend | P1 | Service code | Direct UI code | all stages |
| `+ui` | Screens | P3 (SCR-01…05), P2 (SCR-06) | UI classes | Business logic (must call `+service`) | +service |
| `+eval` | Metrics | P3 | Pure functions | Dataset-specific logic | — |
| `+mock` | Stubs | P2 | Marked stubs | Anything reachable in release config | +contracts |
| `training/` | Model training | Model owner | Scripts, READMEs | Hardcoded hyperparameters (use experiment configs) | +data |
| `evaluation/` | Experiments | P3 | Runners | External-set access outside Phase 4 | +eval, +data |
| `simulink/` | Simulation | P2 | Models, params, validation | Unsourced parameter values | configs/simulation |
| `tests/` | Tests | Each module owner for their module; P2 owns runner | Tests, synthetic fixtures | Real patient data | — |
| `data_manifests/` | Data versioning | P1 | Manifests, hashes, registers | Images | — |
| `docs/` | Documentation | Each owner for own docs; P3 owns protocols; P1 owns final report assembly | Markdown, figures | Fabricated results | — |

---

# SECTION D — TEAM OWNERSHIP MODEL

## D.1 Stable tracks

Each person keeps a coherent track across phases so context carries over, but every phase contains work for all three.

| Track | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|
| **Person 1 — Data, Quality & Systems** | Data pipeline (acquisition → splits → datastores) | Preprocessing/FOV, IQA, enhancement, OD/fovea | Orchestration, storage, routing, errors, auth, reports, service API | Freeze, timing benchmark, hardening, packaging, final integration, demo |
| **Person 2 — Platform, Vision & Simulation** | Repo, environment, config, contracts, skeleton, test runner | Vessels, MA, EX, HE, SE, NV | Explainability layer (criteria panel, overlays, overlap, flags); Simulink structure + M/M/c | Simulation parameterisation, sweeps, optimisation, SCR-06 console |
| **Person 3 — Grading, Evaluation & Clinical Interface** | Metric library, evaluation protocol, open-question resolution, clinician outreach | Grading, operating point, calibration, Grad-CAM, uncertainty candidate | Screens SCR-01…05, review timing, pilot timed review | External evaluation, ablation, benchmarks, rating study, timed review, results dossier |

**BQ-02 `[OPEN QUESTION]`** — Which team member is Person 1, 2, 3? This blueprint does not know your skills. Suggested fit: P1 comfortable with data engineering and MATLAB services; P2 comfortable with image segmentation and Simulink; P3 comfortable with deep-learning classification, statistics, and UI. Re-balance before Phase 1 if needed; the tracks, not the names, are the contract.

## D.2 Ownership rules

1. **One owner per file.** The owner merges changes to it; others propose via PR. Binary files (`.slx`, `.mat`) are never edited by two people concurrently.
2. **Primary ownership** = deliverable you are accountable for at the gate. **Secondary ownership** = a smaller, named deliverable plus a named review duty. No one "helps" without a deliverable.
3. **Review rotation:** P1 reviews P2, P2 reviews P3, P3 reviews P1 (default); contract changes need all three.
4. **Contract changes** (Section I) require a decision record and a version bump; a contract may not change silently mid-phase.
5. **The gate is owned jointly.** Each person signs the gate checklist for their deliverables; the gate passes only when all three sign.

---

# SECTION E — PHASE 1: FOUNDATION — VERIFIED DATA, FROZEN CONTRACTS, WALKING SKELETON

## E.1 Objective
Create everything that parallel model and product development depends on, so that Phase 2 work cannot leak test data, cannot drift from interfaces, and cannot rely on unverified facts.

## E.2 Start condition
- PRD v2.0 approved (it is, per PRD §1, subject to blocking OQs).
- BQ-01 (deadline meaning) answered, so the team can set a Phase 1 time-box.
- BQ-02 (person-to-track assignment) decided.
- Git hosting chosen (BQ-09).

## E.3 Inputs
PRD v2.0 · PS text (mirror; OQ-01 pending) · dataset sources listed in PRD §16.1 · MATLAB licences · mentor contact (MathWorks) · this blueprint.

## E.4 Workstreams

### Person 1 — Data pipeline
- **Primary:** dataset acquisition and verification; dataset register (DAT-001); master metadata table (DAT-002); duplicate and near-duplicate detection (DAT-004); contamination registry (DAT-005); patient/exam-level, source-stratified splits (DAT-003); sealed external sets (DAT-006, DAT-011); datastore interface; dataset analysis report.
- **Secondary:** dataset cards (one per dataset); reviews P3's metric-library PRs.
- **Inputs:** PRD §16; dataset download pages and licences; P2's config loader and contract for the manifest schema.
- **Outputs:** `data_manifests/*` (register, metadata table, hashes, splits, contamination registry); `+netra/+data` datastores and split guard; `docs/dataset_cards/*`; `docs/phases/PH1_data_report.md`.
- **Dependencies:** P2's config loader (for the data-root environment variable) — can start acquisition and verification immediately without it.
- **Can start immediately:** yes (downloads, licence reading, register). **Blocks:** everyone's Phase 2 training.

### Person 2 — Platform
- **Primary:** repository and MATLAB Project; environment record (MATLAB release and toolbox versions, MAT-007); configuration system; contracts v1 (Section I) and validators; pipeline walking skeleton with mock stages; test runner and test layout; Git workflow setup.
- **Secondary:** synthetic test-fixture generator (programmatic, clearly labelled synthetic); reviews P1's data-layer PRs.
- **Inputs:** PRD; Section C and Section I of this blueprint.
- **Outputs:** runnable repo skeleton; `configs/` with schemas; `docs/contracts/*.md` v1; `+netra/+contracts`; `+netra/+pipeline` skeleton; `+netra/+mock`; `tests/` structure; `docs/context/PROJECT_CONTEXT.md`.
- **Dependencies:** none to start. **Blocks:** P1's datastores (config), all Phase 2 stage wrappers (contracts).

### Person 3 — Evaluation core and open questions
- **Primary:** metric library (`+netra/+eval`) with correctness tests against hand-computed values; evaluation protocol document (pre-registration of EVAL-001…012 procedures, CI methods, operating-point procedure, OQ-13 pass statistic); resolution or escalation of OQ-01, 02, 03, 04, 05, 13, 15, 16 and licence/compute checks (BQ-03); start clinician outreach for rating study and timed review (R-05, OQ-06).
- **Secondary:** decision records for every resolved question; reviews P2's contract PRs.
- **Inputs:** PRD §33, §35, §43; mentor; dataset documentation.
- **Outputs:** `+netra/+eval`; `docs/protocols/evaluation_protocol.md`; `docs/decisions/DEC-B*.md`; `docs/phases/PH1_open_questions.md`; outreach log (no personal data beyond what the raters consent to).
- **Dependencies:** none to start. **Blocks:** Phase 2 model selection (needs metrics + protocol); Phase 2 MA and HE design (OQ-04, OQ-05); Phase 2 training stack (OQ-02).

## E.5 Internal dependencies and integration

```
P2 repo + config ──► P1 datastores ──► P1 split guard
P2 contracts v1 ──► P2 skeleton (mock stages) ──► INTEGRATION: synthetic case → valid CaseRecord
P3 metric lib ──► P1 dataset analysis uses it for label statistics (optional)
P3 OQ answers ──► decision records ──► Phase 2 inputs
```

**Phase 1 integration test:** a synthetic fixture image enters the skeleton, passes through every mock stage, produces a CaseRecord that passes all contract validators, is written to a temporary case store path from configuration, and every stage output is marked `status = "mock"`.

## E.6 Components

| ID | Component | Purpose | Owner | Input | Output | Depends on | Technology | Testing | Definition of Done |
|---|---|---|---|---|---|---|---|---|---|
| C1.1 | Repository & MATLAB Project | Shared, path-managed codebase | P2 | Section C | Repo with `.prj`, README, ignore rules | Git host (BQ-09) | Git, MATLAB Project | Fresh clone opens project and runs `runtests` with zero failures | Clone-to-green documented in README |
| C1.2 | Environment record | Reproducibility (NFR-003, MAT-007) | P2 | Each person's installation | `docs/phases/PH1_environment.md`: release, toolbox list + versions, GPU/driver, OS per machine | Licences (BQ-03) | `ver`, `gpuDevice` output captured | Script prints environment; diff across 3 machines reviewed | All three machines recorded; mismatches resolved or documented |
| C1.3 | Configuration system | Externalised values (FR-020) | P2 | Section I.15 | `+netra/+config` loader, merge, schema validation, hash; `configs/default`, `configs/schema` | C1.1 | JSON (`jsondecode`), env vars | Unit tests: precedence, missing keys, null-threshold fail-closed, hash stability | No module reads a path or threshold except via config |
| C1.4 | Contracts v1 | Stable interfaces (BE-002) | P2 | Section I | `docs/contracts/*.md`, `+netra/+contracts` validators | C1.3 | MATLAB structs + validators | Valid/invalid fixture per contract | All Section I contracts documented and validated |
| C1.5 | Walking skeleton | Prove orchestration shape | P2 | C1.4 | `+netra/+pipeline` orchestrator; `+netra/+mock` stages | C1.4 | MATLAB | Integration test (E.5) | Synthetic case end-to-end; all outputs `mock` |
| C1.6 | Test framework | Continuous testing | P2 | — | `tests/` layout, runner script, tagging convention | C1.1 | `matlab.unittest` | Runner itself tested | One command runs each test category |
| C1.7 | Dataset acquisition & register | DAT-001, DAT-015, SEC-005 | P1 | PRD §16.1 | `data_manifests/dataset_register.json`; downloaded data under env-var root | Licences | Manual/official download | Checksums recorded; register schema validation | Each dataset: status ∈ {acquired, access-pending, unavailable}, licence recorded, facts re-verified or marked |
| C1.8 | Master metadata table | DAT-002 | P1 | C1.7 | `data_manifests/master_metadata.csv` + schema | C1.3 | MATLAB tables | Schema, uniqueness, label-range tests | Every acquired image has one row |
| C1.9 | Dedup & contamination | DAT-004, DAT-005, DAT-011 | P1 | C1.8 | Hash columns; duplicate groups; `contamination_registry.json` | C1.8 | Exact hash; perceptual hash; SSIM (Image Processing Toolbox) | Tests with synthetic duplicates; known-overlap checks (Messidor/Messidor-2) | Duplicate groups assigned; PRD-known overlaps registered; perceptual-hash thresholds recorded with how they were chosen |
| C1.10 | Splits & sealed sets | DAT-003, DAT-006, MLR-003 | P1 | C1.9 | `data_manifests/splits/*.csv`; split guard | C1.9 | MATLAB | Leakage tests (TST-006): no patient/exam or duplicate group crosses splits | Splits frozen, hashed, tagged; external sets unreadable without Phase 4 unlock |
| C1.11 | Datastores | Uniform data access | P1 | C1.10 | `+netra/+data` functions returning datastores by (dataset, split, task) | C1.3, C1.10 | `imageDatastore`, `combine`, `transform` | Returns correct counts per split; refuses sealed sets | All Phase 2 tasks can obtain train/val data through one interface |
| C1.12 | Dataset analysis | Know the data before modelling | P1 | C1.8 | `PH1_data_report.md`: counts, grade distribution per split, resolutions, cameras where known, lesion-mask availability, quality-label availability | C1.8 | MATLAB | Numbers regenerated by script | Every number is script-generated and reproducible |
| C1.13 | Metric library | Consistent evaluation | P3 | Section K.9 | `+netra/+eval` | C1.3 | Statistics & ML Toolbox | Hand-computed reference cases for every metric | All metrics in K.9 implemented and tested |
| C1.14 | Evaluation protocol | Pre-registration (MLR-003, EVAL-005) | P3 | PRD §35 | `docs/protocols/evaluation_protocol.md` | — | Markdown | Peer review by P1, P2 | Protocol fixes CI methods, operating-point procedure, external-run rules, OQ-13 statistic |
| C1.15 | Open-question resolution | Unblock Phase 2 | P3 | PRD §43 | Decision records; escalation list | Mentor | — | Each answer cites its source | Every Phase-2-blocking question answered or escalated with a fallback plan |
| C1.16 | Synthetic fixtures | Tests without licensed data | P2 | — | Generator + fixtures in `tests/fixtures` | C1.1 | MATLAB | Deterministic generation | Fixtures labelled SYNTHETIC in file metadata and names |

## E.7 Definition of Done (Phase 1)
Every component in E.6 meets its DoD; all tests in categories unit, data, and integration pass; contracts v1 are published; no absolute path or credential exists in the repo (grep audit); the Phase 1 report exists.

## E.8 Phase Gate 1
1. **Required outputs exist:** E.6 artifacts, register, metadata table, frozen splits (tag `phase-1-splits`), contracts v1, metric library, protocol, skeleton.
2. **Tests pass:** unit, data (TST-006), integration (skeleton).
3. **Interfaces stable:** contracts v1 tagged; any change after the gate needs a decision record.
4. **Documentation exists:** Phase 1 report, dataset cards, environment record, evaluation protocol, decision records.
5. **No unresolved blocker:** OQ-02, OQ-04, OQ-05, OQ-15, OQ-16, BQ-03 each **resolved or escalated with an adopted fallback** (e.g., OQ-02 unresolved → MATLAB-only training plan adopted).
6. **Known limitations recorded:** datasets not accessible; unverifiable facts.
7. **Next-phase inputs ready:** E.9 bundle complete.

## E.9 Next-phase input (handoff bundle to Phase 2)
Frozen split files + hashes · datastore API · config system · contracts v1 · model-artifact contract · metric library · evaluation protocol · decision records for OQ-02/04/05/15/16 · dataset analysis report · environment record · skeleton pipeline with mock stages.

---

# SECTION F — PHASE 2: CORE IMAGE INTELLIGENCE

## F.1 Objective
Deliver a functioning, contract-conformant, MATLAB-executable implementation for every PS analysis module (L1, mandatory), selected by evidence against a baseline, then improve modules within a fixed time-box (L2) where evidence supports it. Internal validation only.

## F.2 Start condition
Phase Gate 1 passed. OQ-02 decided or MATLAB-only fallback adopted. OQ-04/OQ-05 decided or a documented provisional interpretation adopted and flagged for mentor confirmation.

## F.3 Inputs
E.9 bundle.

## F.4 Workstreams

### Person 1 — Preprocessing, image quality, enhancement, OD/fovea
- **Primary:**
  1. Preprocessing (CVR-001): FOV detection, crop, canonical image space with transform record. **Delivered first; blocks P2 and P3.**
  2. IQA rule-based baseline (IQR-001, IQR-003): separate focus, illumination, FOV scores; reason codes; thresholds derived from labelled data (IQR-004) and stored with provenance.
  3. Optional learned IQA, adopted only if it lowers the false-"Gradable" rate (MLR-002, IQR-005).
  4. Enhancement set (ENH-001): CLAHE, illumination normalisation, denoising, applied adaptively from measured properties; ENH-005 enforced.
  5. OD and fovea localisation (SEG-001, SEG-002).
- **Secondary:** non-fundus detection (IQR-006, ERR-009); enhancement effect evaluation (ENH-004) on internal validation.
- **Outputs:** stage wrappers `+preprocess`, `+iqa`, `+enhance`, OD/fovea in `+anatomy`; threshold files; model cards; comparison tables.
- **Depends on:** Phase 1 datastores; quality-labelled data availability (DAT-010).
- **Can start immediately:** yes. **Blocks:** P2 and P3 (preprocessing); Phase 3 routing (IQA verdicts).

### Person 2 — Vessels and lesions
- **Primary:** vessel segmentation (SEG-003); MA detection at resolvable resolution with tiling (SEG-004, CVR-002, CVR-003 per OQ-04); hard exudate segmentation (SEG-006); hemorrhage output per OQ-05 (SEG-005); NV detection at whatever label level exists, with validation level disclosed (SEG-008, SEG-011).
- **Secondary:** soft exudate segmentation (SEG-007, P1 priority → L2); shared tiling/patch infrastructure used by all segmentation tasks.
- **Outputs:** vessel and `+lesions` stage wrappers; model artifacts + cards; per-class internal metrics; baseline comparisons.
- **Depends on:** P1 preprocessing; pixel-mask datasets (IDRiD, DDR, DRIVE); OQ-04, OQ-05, OQ-16 decisions.
- **Can start immediately:** classical baselines and tiling infrastructure on Phase 1 canonical crops (temporary: until P1's preprocessing lands, use the Phase 1 datastore's un-cropped images and switch the moment the wrapper exists; metrics computed before the switch are not reported).
- **Blocks:** Phase 3 explainability layer; optional lesion-informed grading (L2).

### Person 3 — Grading, calibration, Grad-CAM
- **Primary:** grading baseline (MATLAB-native CNN; the MathWorks DR example is a recorded candidate `[VERIFIED exists]`); candidate comparison; decision rule guaranteeing Referable ⇔ displayed grade ≥ 2 (DEC-12) while honouring the operating point (MLR-004) — see I.7; operating-point proposal on internal validation; calibration fit (UNC-001); Grad-CAM in MATLAB on the grade-determining model (MLR-009, MAT-004).
- **Secondary:** uncertainty/OOD candidate (UNC-003, L2); running every model owner's internal-validation evaluation through the metric library so all numbers come from one harness; model-card template.
- **Outputs:** `+grading`, `+calibration`, Grad-CAM in `+explain`; artifacts + cards; operating-point and calibration files with provenance; internal results.
- **Depends on:** P1 preprocessing; grading datasets (APTOS, DDR, optionally EyePACS with contamination noted); OQ-02.
- **Can start immediately:** data loading and baseline training on un-cropped images (same switch rule as P2).
- **Blocks:** Phase 3 evidence bundle, routing (confidence), reports.

## F.5 Internal dependencies and integration

```
P1 preprocess ──► P2 vessels/lesions ──┐
            └──► P3 grading ─► Grad-CAM, calibration ─┤
P1 IQA/enhance/OD-fovea ──────────────────────────────┤
                                                       ▼
            L1 CHECKPOINT: every PS module has an artifact + wrapper + card
                                                       ▼
            L2 TIME-BOX (improvements only through MLR-002 evidence)
                                                       ▼
   INTEGRATION: skeleton orchestrator runs real stages on internal-test images
```

**L1 checkpoint (inside Phase 2):** no L2 work starts on any module until all modules have an L1 artifact. This enforces DEC-11 and risk R-11.

**Phase 2 integration test:** the Phase 1 orchestrator, with mocks replaced by real stages via the model registry, processes a fixed internal-test image list; every CaseRecord validates; no `mock` status remains; Ungradable cases never reach grading (TST-004); referable flag consistency holds (TST-005).

## F.6 Per-model definition
Each model is fully specified in **Section K**. The Phase 2 rule for every model: training script + experiment config + dataset interface + validation + evaluation via `+netra/+eval` + saved artifact per I.14 + inference wrapper + input/output validation + tests + model card. **Training that runs is not a finished model.**

## F.7 Definition of Done (Phase 2)
- Every PS analysis module (PS-02…PS-11, PS-13, PS-15) has an L1 implementation served by the model registry.
- Every learned component has a baseline comparison on the same split (MLR-001); adoption decisions recorded (MLR-002).
- Every artifact carries metadata per I.14, including pretraining corpus (MLR-005).
- Inference is deterministic (MLR-007) — test proves identical outputs on repeat.
- If any model was trained outside MATLAB: import equivalence test passes (MAT-006, TST-007).
- Operating point, calibration, and IQA thresholds exist as provenance-tagged config files derived from internal validation only.
- No external set has been read (split guard logs prove it).

## F.8 Phase Gate 2
1. Outputs: all artifacts, wrappers, cards, internal results, comparison tables.
2. Tests: unit, ML (determinism, shape/range, contract), regression baseline recorded (TST-003).
3. Interfaces: stage contracts unchanged since v1, or changed via decision record.
4. Docs: model cards, Phase 2 report with internal results **clearly labelled internal**.
5. Blockers: none open for Phase 3; any module below its baseline or with undisclosed validation level is a blocker.
6. Limitations: data gaps (NV, portable domain), unmet internal targets, resolution trade-offs documented.
7. Next inputs: F.9 bundle.

## F.9 Next-phase input
Model registry pointing at every stage artifact · stage wrappers · threshold/operating-point/calibration configs with provenance · model cards · internal results · Grad-CAM function · regression reference outputs for a fixed internal image list.

---

# SECTION G — PHASE 3: CLINICAL WORKFLOW PRODUCT

## G.1 Objective
Build the human-in-the-loop system around the Phase 2 models so a technician, an ophthalmologist, and (structurally) an administrator can use it end-to-end on internal data, with every decision logged, every stage timed, and a Simulink model whose structure is validated against queuing theory.

## G.2 Start condition
Phase Gate 2 passed. Routing-related thresholds that are data-driven (OQ-09) have a proposed value with provenance, or the stage fails closed and all cases route to mandatory review.

## G.3 Inputs
F.9 bundle; PRD §21.1 (routing), §24 (report), §25 (screens), §26–28, §38 (errors).

## G.4 Workstreams

### Person 1 — Orchestration, storage, routing, errors, auth, reports, service API
- **Primary:** real orchestrator executing BE-001 order with per-stage timing (BE-003) and explicit failure states (BE-004, §38); case store and append-only audit log (STO-001, STO-004); routing policy engine reading `configs/default/routing.json` (FR-016, §21.1 default policy); local authentication and roles (SEC-001, SEC-002); report generation from a deterministic template with export (FR-013, FR-022, RPT-001…005); service API (I.13).
- **Secondary:** failure-injection tests for every ERR-001…009 (TST-009); batch processing without intervention (SCL-002).
- **Outputs:** `+pipeline`, `+storage`, `+routing`, `+auth`, `+report`, `+service`; routing policy doc; report template doc.
- **Depends on:** Phase 2 wrappers; P2's evidence bundle contract (I.10) for the report; report format decision (FR-022, BQ-06).
- **Can start immediately:** yes (orchestrator, storage, auth, routing on Phase 2 outputs). **Blocks:** P3 screens (service API).

### Person 2 — Explainability layer; Simulink structure
- **Primary (A) — Explainability layer:** overlay rendering registered to canonical image space (CVR-004); lesion summary by location relative to OD/fovea; clinical-criteria panel mapping lesion evidence to ICDR criteria with `supported / not supported / cannot assess` (XAI-003) from a criteria-mapping config whose source must be the primary ICDR publication `[NEEDS VERIFICATION]`; heatmap–lesion overlap metrics where lesion outputs exist (XAI-005 computation, XAI-008 flag); attention disclaimer text (XAI-007); uncertainty flag rules — inconsistent evidence (FR-009), NV priority (GRD-007), OOD if Phase 2 delivered a method.
- **Primary (B) — Simulink structure:** model of SIM-001 flow; discrete-event implementation per the licence decision (SimEvents or fallback, R-10); parameter struct from `configs/simulation` (SIM-003) with every value source-tagged; outputs SIM-005; M/M/c analytical validation scenario (SIM-010, TST-010); seeded, stored runs (SIM-011).
- **Secondary:** evidence-bundle contract tests; Simulink model documentation.
- **Depends on:** Phase 2 outputs (A); nothing from Phase 2 for (B).
- **Can start immediately:** both. **Blocks:** P1 report content, P3 review screen content.

### Person 3 — Screens and review timing
- **Primary:** SCR-01 Capture/Upload, SCR-02 Quality Verdict (non-diagnostic language, UX-002), SCR-05 Review Queue, SCR-03 Review Workstation (all UX-001 elements on one screen at the target display `[OPEN: display spec]`), SCR-04 Report view; explicit "evidence unavailable" state (UX-003); colour never the only carrier of meaning (UX-004); automatic review timing from open to decision (UX-005).
- **Secondary:** pilot timed review with the dev team as **proxy reviewers** to find UI bottlenecks (disclosed as proxy; not a PERF-003 result); UI tests.
- **Depends on:** P1 service API; P2 evidence bundle. Can build against I.13 signatures with contract-valid fixtures `[MOCK — TEMPORARY ONLY]` (see G.6).
- **Blocks:** Phase 4 timed review and rating study (need SCR-03).

## G.5 Internal dependencies and integration

```
P1 orchestrator + storage ──► P1 service API ──► P3 screens
P2 evidence bundle ─────────► P1 report
                  └─────────► P3 SCR-03
P2 Simulink structure ──► M/M/c validation   (independent)
INTEGRATION: technician uploads → verdict → (retake|enhance|analyse) → evidence → report → queue
             → ophthalmologist opens → confirm/override → audit entry → report finalised
```

## G.6 Temporary mocks permitted in Phase 3

| Mock | Why necessary | What it represents | Replaced by | Removal deadline |
|---|---|---|---|---|
| `[MOCK — TEMPORARY ONLY]` UI fixture case records | Lets P3 build screens before the service API lands | A contract-valid CaseRecord whose every stage has `status="mock"` and **no grade, probability, or lesion values** — the screen shows "evidence unavailable" | Real service API responses | Before Phase 3 integration test; enforced by Phase 4 mock purge |
| `[MOCK — TEMPORARY ONLY]` Simulink provisional parameters | Simulink structure must run before measured timings exist | Placeholder values each tagged `[PARAMETER TO BE DETERMINED]` in `configs/simulation/provisional.json` | Measured values (Phase 4) | Phase 4 gate; any provisional value remaining must be shown as such in outputs |

No mock may contain a DR grade, probability, lesion detection, or patient-like data.

## G.7 Definition of Done (Phase 3)
- End-to-end workflow runs on a fixed internal-test image list without manual intervention (SCL-002).
- TST-002 (integration), TST-004 (gating), TST-005 (consistency), TST-009 (failure injection) pass.
- Every report contains all RPT-002 fields or states which are missing (RPT-005).
- Every human decision is logged append-only, separate from model output (FR-015).
- Per-stage timings logged for every case (BE-003) on documented hardware (DEP-002).
- SCR-03 shows all UX-001 elements without scrolling on the documented display.
- Simulink model runs with provisional parameters and passes the M/M/c check (or discrepancies explained).
- Authentication and roles enforced; no credential in repo.

## G.8 Phase Gate 3
1. Outputs: integrated prototype, service API, screens, reports, audit log, timing logs, Simulink model.
2. Tests: as G.7.
3. Interfaces: service API (I.13) and evidence bundle (I.10) versioned.
4. Docs: workflow guide, routing policy, criteria mapping with source, Simulink model doc, Phase 3 report.
5. Blockers: none open for Phase 4, specifically: rating-study protocol (OQ-06) approved; timed-review protocol and pass statistic (OQ-13) fixed; optimisation objective and constraints (OQ-11) decided or a documented provisional objective adopted.
6. Limitations: proxy pilot results labelled; display assumptions.
7. Next inputs: G.9.

## G.9 Next-phase input
Release-candidate build · service API · timing logs + hardware record · Simulink model + validation report · protocols (evaluation, rating, timed review) · regression reference outputs · list of all mocks still present (must be empty except Simulink provisional parameters).

---

# SECTION H — PHASE 4: VALIDATION, DISTRICT SIMULATION & FINAL SYSTEM

## H.1 Objective
Freeze the system, evaluate it once on sealed external data, run the human studies, parameterise and optimise the district simulation with measured values, harden and package the system, and rehearse the demonstration — reporting unmet targets as unmet (EVAL-012, NFR-009).

## H.2 Start condition
Phase Gate 3 passed; freeze criteria agreed.

## H.3 Inputs
G.9 bundle; sealed external sets; raters and reviewers available (or proxies, disclosed).

## H.4 Workstreams

### Person 1 — Freeze, hardening, packaging, final integration, demo
- **Primary:** release freeze (tag `v1.0-rc`, freeze manifest = code commit + config hash + model registry hashes + threshold files); timing benchmark on the documented demo host (feeds simulation); mock purge and release-config check; dependency audit — no external AI/LLM/inference calls, no hardcoded paths/credentials/thresholds (TST-011, AC-019); security checks (roles, audit-log append-only, de-identified case IDs); packaging (DEP-004 decision); setup guide reproduced on a clean machine (DEP-005); final integration run; demo runner.
- **Secondary:** final report assembly (`docs/phases/FINAL_REPORT.md`); toolbox usage map (MAT-003).
- **Blocks:** everyone (freeze first).

### Person 2 — Simulation parameterisation, scenarios, optimisation, SCR-06
- **Primary:** replace provisional parameters with measured processing times (from P1's benchmark) and measured review times (from P3's timed review); source-tag every other parameter or mark `[PARAMETER TO BE DETERMINED]` (SIM-004); 100k/year baseline and SIM-006 sweeps showing upload-, AI-, and review-bound regimes; optimisation per OQ-11 decision with ranges (SIM-007, SIM-008); visualisations (SIM-012); SCR-06 console (run, compare, export; ERR-008 validation).
- **Secondary:** routing-policy comparison in simulation only, every workload claim labelled "simulated" (§21.1).
- **Depends on:** P1 benchmark; P3 timed-review results (can run with provisional review times first and re-run).

### Person 3 — External validation and human studies
- **Primary:** one-shot external evaluation per the evaluation protocol (EVAL-001…006) with CIs, domain notes, contamination status; ablation of pre-registered variants (EVAL-007); published-benchmark comparison stating protocol differences (EVAL-008); XAI overlap summary (XAI-005) and clinician rating study (XAI-006); timed review test (TST-008, PERF-003); error analysis (EVAL-010).
- **Secondary:** results dossier (`docs/results/`) and the honest-reporting checklist (NFR-009).
- **Depends on:** freeze; raters (R-05).

## H.5 Internal dependencies and integration

```
P1 freeze ──► P1 timing benchmark ──► P2 simulation (processing times)
     └──────► P3 external eval, ablation, benchmark, overlap
     └──────► P3 timed review ──► P2 simulation (review times) ──► P2 optimisation
     └──────► P3 rating study
all results ──► P1 final report + demo runner ──► DEMO REHEARSAL
```

**Freeze rule:** after `v1.0-rc`, any change to code, config, or models invalidates the external results; if a change is unavoidable, the external evaluation is re-run **and both results are reported** (no silent replacement).

**Ablation on external data:** allowed only for variants pre-registered in the evaluation protocol before the freeze, each evaluated once, with no selection made on the external results.

## H.6 Deliverables
Frozen release · external results table with CIs · ablation table · benchmark-comparison table · calibration results per set · XAI overlap + rating results · timed-review results · simulation scenario outputs + optimised configuration with ranges · SCR-06 · packaged demo + setup guide · dependency audit report · final report.

## H.7 Definition of Done (Phase 4)
All AC-001…AC-021 have a recorded result (met, unmet with explanation, or not assessable with reason); no mock remains in the release; setup guide reproduced on a clean machine; demo rehearsed end-to-end on held-out data.

## H.8 Phase Gate 4
1. Outputs: H.6.
2. Tests: full suite incl. e2e, performance, security/dependency audit, simulation validation, demo rehearsal.
3. Interfaces: final versions tagged.
4. Docs: final report, results dossier, setup guide, demo script, toolbox usage map.
5. Blockers: none.
6. Limitations: complete, including domain shift (R-01), NV validation level (R-03), proxy raters if used.
7. Output: tag `v1.0-sih`.

---

# SECTION I — CROSS-PHASE INTERFACE CONTRACTS

Field names below are `[ENGINEERING DECISION]` (contracts v1, published in Phase 1 by P2). **Numeric values are not set here**: image sizes, normalisation constants, and thresholds are produced by Phase 2 evidence and stored in artifact metadata or provenance-tagged config. Where a value is undecided, the contract states where it will come from.

## I.1 Stage output envelope (every stage)

| Field | Type | Meaning |
|---|---|---|
| `stage` | string | Stage name from the stage registry |
| `status` | enum | `ok` · `failed` · `skipped` (e.g., grading for Ungradable) · `unavailable` (component not implemented / no validated output) · `mock` |
| `version` | string | Code version (commit) |
| `model_id` | string or empty | Registry ID of the artifact used |
| `started_utc`, `duration_ms` | datetime, double | Timing (BE-003) |
| `error` | struct or empty | `code` (from error catalogue, §38 IDs), `message` |
| `payload` | struct | Stage-specific, below |

Rule: a consumer must check `status` before reading `payload`. `mock`, `failed`, `unavailable` are rendered as "evidence unavailable" (UX-003) and force mandatory review (ERR-005).

## I.2 Images and coordinate spaces

| Item | Contract |
|---|---|
| Input image | RGB colour fundus image; accepted formats from `configs/default/pipeline.json` `[OPEN: OQ-14]`; stored unmodified as the original (ENH-002). |
| Canonical image space | The FOV-cropped image at native resolution produced by `+preprocess` (CVR-001). **All** spatial outputs (centres, masks, detections, heatmaps) are expressed in canonical space. |
| Transform record | Stored per case: crop box, any resize, orientation change — enough to map canonical ↔ original. |
| Model input | Each model's input size, channel order, colour space, normalisation, and resize/tiling policy are **fields of that model's artifact metadata (I.14)**, not global constants. The wrapper reads them and performs the resize; outputs are mapped back to canonical space before leaving the stage. |
| Masks | Logical arrays in canonical space, or references to files in the case store. |
| Image references | Case-store relative references, never absolute paths. |

## I.3 IQA payload (M1)

| Field | Type |
|---|---|
| `verdict` | enum `Gradable` · `Borderline` · `Ungradable` |
| `reasons` | array of codes from enum: `FOCUS`, `ILLUMINATION`, `FIELD_OF_VIEW`, `NON_FUNDUS` (+ optional `CONTRAST`, `ARTEFACT` per IQR-002) |
| `guidance_keys` | keys into technician guidance text in config (text not hardcoded) |
| `scores` | struct: `focus`, `illumination`, `fov` (each numeric, with the threshold IDs applied) |
| `pass` | `initial` or `recheck` (FR-005: exactly one recheck) |

## I.4 Enhancement payload (M2)
`operations` (ordered list: name + parameters actually applied + the measured property that triggered it) · `enhanced_image_ref` · `input_verdict` (must be `Borderline`; ENH-005 enforced by validator).

## I.5 Anatomy payload (M3)
`od_center` [x y] canonical px · `od_mask_ref` or empty · `fovea_center` [x y] · `vessel_mask_ref` · `od_diameter_px` (if a mask exists; used for normalised distances) · per-output `score` where the method provides one.

## I.6 Lesion payload (M4)

| Sub-field | Contents |
|---|---|
| `ma` | `detections` (N×k: x, y, score, optional radius), `count`, `mask_ref` or empty, `localisation_precision` note per OQ-04 |
| `ex` | `mask_ref`, `area_px`, `score_map_ref` optional |
| `he` | `mask_ref`, plus `classification` whose structure follows OQ-05: either per-region presence/extent or per-lesion morphological type |
| `se` | as `ex`; `status=unavailable` allowed at L1 |
| `nv` | `level` (`image` or `region`), `score`, `detected` (via threshold ID), `regions` or empty, `validation_level` ∈ `pixel` · `region` · `image_proxy` · `not_validated` (SEG-011) |

## I.7 Grading payload (M5)

| Field | Contract |
|---|---|
| `probs_raw` | 1×5 vector for ICDR 0…4 (index *k*+1 ↔ grade *k*; mapping fixed and tested) |
| `grade` | integer 0…4 (the displayed grade) |
| `referable` | logical, **always equal to `grade >= 2`** (DEC-12) |
| `decision_rule_id` | ID of the rule in config |
| `components_disagree` | logical (feeds inconsistent-evidence flag, FR-009) |

**`[ENGINEERING DECISION — proposed, confirm at Phase 2 gate]` Decision rule.** MLR-004 requires the referable operating point to be tuned on validation, while DEC-12 requires the referable flag to equal "grade ≥ 2". A plain argmax cannot do both. Proposed rule: compute P(referable) = p2 + p3 + p4 (calibrated); if P(referable) ≥ t_ref (from `configs/thresholds/referable_operating_point.json`), displayed grade = argmax over grades 2–4, else argmax over grades 0–1. This guarantees consistency by construction and lets t_ref be chosen for sensitivity. Alternatives (ordinal cut-points, separate referable head with disagreement flag) are evaluated in Phase 2 by P3; the chosen rule is recorded in a decision record.

## I.8 Calibration payload (M7, part 1)
`probs_calibrated` (1×5) · `p_referable` · `confidence_referable_decision` (calibrated probability of the side chosen) · `confidence_grade` (calibrated probability of the displayed grade within its side) · `calibration_id` (fit on internal validation; provenance in config). UI shows calibrated values with plain-language interpretation (UNC-004); wording lives in config.

## I.9 Uncertainty flags (M7, part 2)
`low_confidence` (threshold ID, OQ-09) · `ood` (method ID or `unavailable`) · `inconsistent_evidence` (rule IDs that fired) · `nv_priority` (GRD-007) · `incomplete` (any required stage not `ok`). Each flag carries a human-readable reason key. Flag rules are config, documented in `docs/contracts/uncertainty_flags.md`.

## I.10 Evidence bundle (M6 → report and SCR-03)

| Field | Contents |
|---|---|
| `gradcam` | `map_ref` (canonical space), `target` (grade or referable), `layer`, `model_id`, `method="Grad-CAM"` (other methods labelled distinctly, XAI-002) |
| `overlays` | available overlay layers with refs (MA, EX, HE, SE, NV, OD, fovea, vessels) |
| `lesion_summary` | per type: count/area; location relative to OD/fovea (quadrant or zone definition documented) |
| `criteria_panel` | list of {`criterion_id`, `grade_context`, `status` ∈ supported · not_supported · cannot_assess, `evidence_refs`}; criteria definitions from a config file citing the ICDR source `[NEEDS VERIFICATION]` |
| `explanation_agreement` | overlap metrics where lesion outputs exist; `low_agreement` flag (XAI-008) |
| `disclaimer_key` | key to XAI-007 text |

## I.11 Report (M8)
All RPT-002 fields; `missing_components` list (RPT-005); `pipeline_version`, `config_hash` (OPS-003); deterministic template ID (RPT-003); export format per FR-022 `[OPEN: BQ-06]`. Candidate: HTML + PNG images (no extra licence) vs PDF via MATLAB Report Generator (licence not in PS list, `[NEEDS VERIFICATION]`).

## I.12 Human decision record (FR-015, STO-004)
`decision_id` · `case_id` · `reviewer_id` (pseudonymous) · `role` · `action` ∈ confirm · override · `override_grade` · `override_referable` · `reason_code` + optional text (required on override) · `explanation_unhelpful` (logical) · `opened_utc` · `decided_utc` · `review_duration_ms` (UX-005). Append-only; never overwrites model output.

## I.13 Service API (backend ↔ frontend)

`[ENGINEERING DECISION]` The prototype is a single-host MATLAB application (DEP-001), so the backend interface is a set of MATLAB functions in `+netra/+service`, **not HTTP endpoints**. If a web deployment is chosen later (DEP-004), each function maps one-to-one to an endpoint; no endpoint URLs are defined now.

| Function | Caller role | Request | Response | Errors |
|---|---|---|---|---|
| `login` | all | username, secret (entered, never stored in code) | session with role | invalid credentials; locked |
| `submitImage` | Technician | session, file ref | `case_id`, IQA payload | ERR-001, ERR-007, ERR-009 |
| `recordRecapture` | Technician | session, case_id, new file ref | IQA payload, attempt count | ERR-003 at retry limit (OQ-07) |
| `getCaseStatus` | Technician | session, case_id | non-diagnostic status only (UX-002) | not found; forbidden |
| `listReviewQueue` | Ophthalmologist | session, queue ID, paging | ordered case summaries + priority reason | forbidden |
| `openCase` | Ophthalmologist | session, case_id | full CaseRecord view + evidence bundle; starts timer | ERR-004, ERR-005 shown as states |
| `recordDecision` | Ophthalmologist | session, decision fields (I.12) | stored decision, finalised report ref | validation error (reason missing on override) |
| `getReport` / `exportReport` | Ophthalmologist | session, case_id, format | report / exported file ref | generation failure |
| `runScenario` | Administrator | session, parameter-set ref or struct | run ID + SIM-005 outputs | ERR-008 |
| `runOptimisation` | Administrator | session, objective/constraints ref | configuration + ranges | ERR-008; infeasible |

## I.14 Model artifact contract (STO-002, MLR-005, MLR-008)
One `.mat` per artifact containing the network/algorithm object and `metadata`: `model_id`, `task`, `version`, `input_spec` (size, channels, colour space, normalisation, tiling), `output_spec` (class map or mask semantics), `training_manifest_hash`, `split_hashes`, `experiment_config_ref`, `seed`, `pretrained_from` + `pretraining_corpus` (or `none`), `matlab_release`, `toolboxes`, `git_commit`, `created_utc`, `metrics_ref`, `model_card_ref`, `import_equivalence_ref` (if imported). Registry `configs/models/model_registry.json` maps stage → artifact ID + checksum; the loader verifies the checksum.

## I.15 Configuration contract (FR-020)
Precedence: `configs/default` < selected profile (e.g., `experiments/<run>.json`) < `configs/local/local.json` (git-ignored) < environment variables for machine roots (`NETRA_DATA_ROOT`, `NETRA_ARTIFACT_ROOT`, `NETRA_CASE_STORE`) — names are `[ENGINEERING DECISION]`. Every file validated against `configs/schema`. `config_hash` recorded per case and per run. Threshold entries: `{value, derived_from_split, run_id, commit, date, method}`; `value: null` ⇒ dependent stage fails closed. Secrets are never in config files; authentication user store is created by a setup script prompting for secrets.

## I.16 Timing log → simulation
Per case per stage: `case_id, stage, started_utc, duration_ms, host_id, pipeline_version`. Host record (DEP-002) stored separately. P2 derives distributions (not single means) for SIM-003.

## I.17 Simulation parameter contract (SIM-003, SIM-004)

| Parameter | Unit | Source rule |
|---|---|---|
| Annual volume | patients/year | PS: ≥100,000 baseline; sweep values `[PARAMETER TO BE DETERMINED]` |
| Operating days/year; hours/day | days; hours | `[PARAMETER TO BE DETERMINED]` |
| Arrival pattern | distribution | `[PARAMETER TO BE DETERMINED]` |
| Cameras per site; capture time; recapture time | count; s | `[PARAMETER TO BE DETERMINED]` |
| Recapture probability | fraction | measured IQA rejection rate on internal data, labelled "not field-measured" |
| Image size; compression | MB; ratio | measured from datasets/pipeline, labelled by source |
| Bandwidth per site | Mbps | `[PARAMETER TO BE DETERMINED]` (PRD §31 illustrative ranges only) |
| Per-stage processing time | s (distribution) | I.16 measurements on documented host |
| AI servers | count | decision variable |
| Routing policy; mandatory-review fraction | policy ID; fraction | config + measured on internal data |
| Review time | s (distribution) | Phase 4 timed review (PERF-003) |
| Reviewers; reviewer hours | count; h/day | decision variable; hours `[PARAMETER TO BE DETERMINED]` |

Outputs (SIM-005): throughput per day and year, mean and P95 wait per queue, queue lengths, utilisation per resource, backlog growth, recapture load, bottleneck ID. Every output file carries the parameter set and the source tag of each parameter.

## I.18 Frontend components

| Component | Input | Output | State | API dependency |
|---|---|---|---|---|
| SCR-01 Upload | file | submission | idle/uploading/error | `submitImage` |
| SCR-02 Verdict | IQA payload | retake/proceed | verdict shown | `submitImage`, `recordRecapture` |
| SCR-05 Queue | queue list | selected case | paging, filter | `listReviewQueue` |
| SCR-03 Workstation | CaseRecord + evidence | decision | overlay toggles, original/enhanced toggle, timer | `openCase`, `recordDecision` |
| SCR-04 Report | report | export | — | `getReport`, `exportReport` |
| SCR-06 Simulation | parameter set | run results, plan | scenario list | `runScenario`, `runOptimisation` |

## I.19 Dataset manifest (DAT-002)
Columns: `image_id`, `dataset`, `dataset_version`, `source_file` (relative to data root), `patient_or_exam_id` (if available; else `unknown` + note), `eye`, `sha256`, `phash`, `dup_group`, `split`, `grade_icdr`, `quality_label` (+ mapping source), `has_lesion_masks` (per type), `has_od_fovea`, `camera` (if documented), `licence_id`, `notes`. Split files list `image_id` only and are hashed.

---

# SECTION J — DATA PIPELINE

| Stage | Owner | Phase | Input | Output | Test | Definition of Done |
|---|---|---|---|---|---|---|
| Acquisition | P1 | 1 | Official dataset sources (PRD §16.1) | Raw files under `NETRA_DATA_ROOT`; register entry with licence + access status | Checksum of every archive recorded | Every dataset has status acquired / access-pending / unavailable; nothing downloaded from unofficial mirrors without a note |
| Verification | P1 | 1 | Raw files, PRD facts | Register facts marked re-verified or `[NEEDS VERIFICATION]`; discrepancies logged | Counts computed by script vs documented counts | Every PRD dataset figure re-checked against the official source (DAT-015) or marked |
| Organisation | P1 | 1 | Raw files | Master metadata table (I.19) | Schema + uniqueness tests | One row per image; IDs stable across re-runs |
| Cleaning | P1 | 1 | Metadata table | Corrupt/unreadable files flagged; label harmonisation map (e.g., EyeQ Good/Usable/Reject → Gradable/Borderline/Ungradable is assumption A-04 and must be documented as a mapping, not a fact) | Decode test on every file; label-range tests | No silent drops; every exclusion listed with reason |
| Deduplication | P1 | 1 | Cleaned table | `sha256`, `phash`, `dup_group`; contamination registry | Synthetic duplicate tests; known overlaps detected | Duplicate groups exist; thresholds for near-duplicates documented with how chosen |
| Analysis | P1 | 1 | Table | Data report (distributions, resolutions, label availability per task) | Script regenerates report | All figures script-generated |
| Splitting | P1 | 1 | Deduplicated table | Patient/exam-level, source-stratified splits; sealed external sets | TST-006 leakage tests | Splits frozen, hashed, tagged `phase-1-splits` |
| Preprocessing | P1 | 2 | Images | Canonical-space images + transform record | FOV detection on synthetic + sample images; transform round-trip test | Every stage consumes canonical space |
| Augmentation | Each model owner | 2 | Training images | On-the-fly transforms defined in experiment config | Augmentation never applied to val/test (test) | Augmentations documented in model card; none alter labels' meaning (e.g., no transform that could hide MAs without justification) |
| Training | Each model owner | 2 | Train split via datastore | Artifacts (I.14) | ML tests (F.6) | Model card complete |
| Evaluation | P3 harness; owners run | 2 (internal), 4 (external) | Val/test splits | Metrics via `+netra/+eval` | Metric correctness tests | Numbers traceable to run IDs |
| Versioning | P1 | 1–4 | All manifests, artifacts | Hashes in manifests and artifact metadata; git tags at gates | Checksum verification on load | Any result can be traced to data hash + code commit + config hash |

**Data storage `[ENGINEERING DECISION]`:** images never enter Git. Manifests, hashes, and split files are committed. Model artifacts live under `NETRA_ARTIFACT_ROOT`, referenced by registry checksum. How artifacts are shared among three people (shared drive, Git LFS, cloud storage) is **BQ-07 `[OPEN QUESTION]`**; whichever is chosen, the checksum in the registry is the source of truth.

---

# SECTION K — ML PIPELINE

## K.0 Rules applying to every model
- Baseline first; learned model adopted only if it beats the baseline on the primary metric on the same internal split (MLR-001/002).
- Selection on training/internal validation only (MLR-003). External sets unreadable until Phase 4.
- Pretraining corpus recorded; any evaluation set overlapping it cannot be called independent (MLR-005). Known: RETFound ⊃ Kaggle-EyePACS; EyeQ ⊂ EyePACS `[VERIFIED]`. ImageNet-pretrained weights: record as ImageNet (no fundus overlap expected, but record regardless).
- Class imbalance handled and reported; accuracy never a headline metric (MLR-006).
- Deterministic inference (MLR-007).
- MATLAB-executable at inference (MLR-010). Training in MATLAB unless OQ-02 allows otherwise and MAT-006 passes.
- Compute requirements are stated only after measurement; "fits on available GPU" is `[NEEDS VERIFICATION]` until BQ-03 is answered.
- Hyperparameters (learning rate, epochs, batch size, loss weights, input size) are **experiment-config values chosen during Phase 2**, never fixed in this blueprint.

## K.1 Preprocessing / FOV (CVR-001) — P1, Phase 2
- **Task:** find circular FOV, crop, record transform. **Data:** all datasets (no labels needed); quality-labelled sets for failure checks.
- **Candidates:** (a) intensity threshold + morphology + circle fit (Image Processing Toolbox); (b) learned FOV segmentation. **Choice:** (a) as baseline `[ENGINEERING DECISION]` — the FOV boundary is a high-contrast, near-circular structure; no labels exist for (b). **Failure modes:** very dark images, non-circular masks, non-fundus inputs (route to IQA `NON_FUNDUS`). **Artifact:** algorithm + parameters in config.

## K.2 Image quality assessment (M1) — P1, Phase 2
- **Task:** 3-state verdict + reason codes. **Data/labels:** EyeQ (Good/Usable/Reject; mapping to 3 states is assumption A-04), DDR ungradable class, mBRSET quality labels if accessible; **not** IDRiD (DAT-010).
- **Candidates:**

| Approach | For | Against |
|---|---|---|
| Rule-based features (focus: Laplacian-variance/gradient energy in FOV; illumination: luminance level, uniformity, clipped fractions; FOV: area fraction, circularity, centring) with thresholds learned on labels | Directly yields the PS-required per-criterion reasons (IQR-001); explainable; tiny compute | May miss artefact types |
| Same features + interpretable classifier (e.g., shallow tree/logistic, Statistics & ML Toolbox) | Data-driven thresholds; still gives reasons | Needs care to keep per-criterion reasons |
| Small CNN on EyeQ | May capture artefacts | Reasons not native; EyePACS-derived domain; needs reason-mapping |

- **Choice:** rule-based baseline mandatory (IQR-003, DEC-01); learned only via MLR-002. **Loss (learned):** class-weighted cross-entropy candidate. **Metrics and why:** false-"Gradable" rate (primary; a bad image passed downstream is the critical failure), false-"Ungradable" rate (technician burden), per-reason agreement where labels allow. **Validation:** internal split of quality-labelled data. **Inference:** feature extraction + thresholds from `configs/thresholds/iqa.json`. **Failure modes:** domain shift to portable cameras (R-01), label-mapping mismatch.

## K.3 Enhancement (M2) — P1, Phase 2
- **Task:** adaptive CLAHE, illumination normalisation, denoising on Borderline images (ENH-001). **Candidates:** CLAHE on luminance or green channel (`adapthisteq`); illumination normalisation by background estimation (large-kernel smoothing, divide/subtract); denoising (e.g., non-local means, wavelet) — selection rules triggered by measured properties. **Choice:** classical only (PRD M2). **Evaluation (ENH-004):** verdict change rate on internal Borderline cases; downstream metric change on paired original/enhanced images. **Failure modes:** amplifying noise into MA-like spots (must be checked against MA false positives), colour shifts affecting exudate detection.

## K.4 OD and fovea localisation (M3) — P1, Phase 2
- **Data/labels:** IDRiD OD/fovea centres and OD masks `[VERIFIED exists; subset sizes to be re-verified]`; other sources `[NEEDS VERIFICATION]`.
- **Candidates:** (a) classical — OD as brightest/vessel-convergence region, fovea as darkest region at an anatomically constrained offset; (b) heatmap-regression CNN; (c) detector. **Selection:** (a) baseline; (b)/(c) only if localisation error improves (MLR-002). **Metric and why:** Euclidean distance normalised by a documented reference (OD diameter or FOV diameter — choice recorded in protocol), because the macula reference drives criteria (PRD §15.1 critical failure). **Failure modes:** peripapillary atrophy, bright exudates mistaken for OD, off-centre fields.

## K.5 Vessel segmentation (M3) — P2, Phase 2
- **Data:** DRIVE (40 images, 20/20) `[VERIFIED]`; others `[NEEDS VERIFICATION]`. **Candidates:** (a) classical vesselness/matched filtering (e.g., `fibermetric`) + threshold; (b) U-Net-family on patches. **Consideration:** very small labelled set → strong augmentation, patch training, risk of overfitting; (a) is a credible baseline. **Metrics:** Dice/IoU and sensitivity (thin-vessel recall matters); per-image reporting. **Failure modes:** lesions (haemorrhages) segmented as vessels; resolution mismatch between DRIVE and other datasets.

## K.6 Microaneurysm detection (M4) — P2, Phase 2 `[BLOCKED by OQ-04 for the "sub-pixel" definition]`
- **Data:** IDRiD 81 (54/27) and DDR 757 pixel masks `[VERIFIED]`. **Resolution:** native or near-native with tiling (CVR-002); any downsampling justified by measured MA recall.
- **Candidates:**

| Approach | For | Against |
|---|---|---|
| Classical candidate extraction (morphological top-hat / matched filtering on green channel) + candidate classifier | Interpretable; data-efficient | Many false positives near vessels |
| Tile-based U-Net-family segmentation, loss tuned for tiny-object recall | Learns context | Class imbalance extreme; few annotations |
| Detection network on tiles | Lesion-level output natural | Tiny objects hard; box labels must be derived from masks |

- **Metric and why:** lesion-level sensitivity at fixed false positives per image (FROC-style) as primary — pixel Dice is unstable for objects a few pixels wide; Dice secondary; MA centroid localisation error in pixels at native resolution until OQ-04 is resolved (CVR-003). **Failure modes:** missed MAs → under-grading (critical); vessel crossings and noise as false positives; enhancement-induced artefacts.

## K.7 Exudates, hemorrhages, soft exudates (M4) — P2, Phase 2
- **Data:** IDRiD and DDR masks for EX, HE, SE `[VERIFIED]`; FGADR `[NEEDS VERIFICATION]`. **Candidates:** classical baselines (EX: bright-lesion thresholding after background normalisation with OD masked; HE: dark-lesion detection with vessels masked) vs U-Net-family multi-class or per-class models. **Hemorrhage "classification":** output structure depends on OQ-05; if morphological type is required, check whether any dataset has type labels — if none, **disclose** that type classification cannot be validated (do not invent labels). **Metrics:** per-class Dice/IoU on official test partitions (SEG-010), compared with published results on the same partitions (EVAL-008, done in Phase 4). **Failure modes:** OD confused with exudates; vessel fragments as hemorrhages; drusen vs exudates.

## K.8 Neovascularization (M4) — P2, Phase 2 `[BLOCKED by OQ-16; R-03]`
- **Data:** no NV pixel masks in IDRiD/DDR `[VERIFIED]`; FGADR `[NEEDS VERIFICATION]`; DRAC22 excluded (DEC-10).
- **Options by data outcome:** (a) region/pixel labels exist and are licensable → segmentation/detection model, validated at that level; (b) only image-level labels → image-level classifier; (c) neither → image-level **proxy** using ICDR grade 4 as a stand-in, which is imperfect because grade 4 also covers vitreous/preretinal hemorrhage — must be labelled `image_proxy` in UI and report (SEG-011, DAT-012). **Metric:** sensitivity/specificity at the available label level; missed PDR is the critical failure, so sensitivity is primary. GRD-007 priority flag threshold derived from validation.

## K.9 DR grading (M5) — P3, Phase 2
- **Data/labels:** APTOS 2019 (3,662, India, ICDR) `[VERIFIED]` — PS-attached; DDR grading set; EyePACS optional (single-grader labels, contamination noted); never original Messidor (DAT-011); Messidor-2, IDRiD grading test, APTOS held-out reserved as tests.
- **Candidates:**

| Approach | For | Against |
|---|---|---|
| MATLAB-native CNN baseline (MathWorks DR example `[VERIFIED exists]`) | PS-aligned; Grad-CAM native (MLR-009); no import risk | May underperform newer backbones |
| Other CNN families (ResNet/EfficientNet/ConvNeXt-type) pretrained on ImageNet | Stronger features; Grad-CAM applicable to conv layers | Availability in pinned MATLAB release `[NEEDS VERIFICATION]`; import needed if trained elsewhere (OQ-02) |
| Foundation model (RETFound, ViT-L) | Strong reported results | EyePACS in pretraining (contamination); Grad-CAM applicability and MATLAB import unverified; heavy compute |
| Lesion-informed fusion (image features + M4 lesion features) — L2 | Ties grade to lesion evidence; likely helps ablation story (PS-24) | Depends on lesion model quality; more integration |
| Head: softmax vs ordinal (e.g., CORAL) | Ordinal respects grade order | Must still produce per-grade probabilities (GRD-003) and fit the decision rule (I.7) |

- **Loss candidates:** class-weighted cross-entropy; ordinal losses; (evaluate, do not assume). **Metrics and why:** referable sensitivity and specificity at the frozen operating point (PS-12, the PS test); AUROC (threshold-free ranking quality, lets operating point be chosen transparently); AUPRC (informative under imbalance); QWK (agreement on an ordinal scale, GRD-005); per-class sensitivity/specificity; confusion matrix; macro-F1 (EVAL-006). **Validation:** internal val for model selection and operating point (MLR-004: meet sensitivity target, maximise specificity). **Failure modes:** grade 1 vs 2 boundary (MAs only vs more) drives referable errors; image-quality confounding; dataset-specific label noise.

## K.10 Calibration and uncertainty (M7) — P3, Phase 2
- **Calibration candidates:** temperature scaling (1 parameter, preserves ranking) vs Platt/vector scaling vs isotonic (needs more data). Fit on internal val only. **Metrics and why:** ECE (average miscalibration), Brier (joint calibration + sharpness), reliability diagrams (visual check) — PS-15 requires calibrated confidence and UNC-001 requires measuring it. **OOD candidates (L2):** embedding-distance scores (e.g., Mahalanobis on penultimate features), energy/max-softmax baselines; adopted only if it separates held-out domain shift better than max-softmax on internal data. **Failure mode:** calibration degrades out of domain (R-13) → measured again on every external set (UNC-005).

## K.11 Grad-CAM (M6, part 1) — P3, Phase 2
Computed in MATLAB on the grade-determining model (MAT-004), target = displayed grade (optionally referable decision); layer choice documented. MATLAB Deep Learning Toolbox provides a `gradCAM` function `[NEEDS VERIFICATION in pinned release]`. **Honesty rule:** Grad-CAM shows model attention, not clinical proof (XAI-007). Heatmaps registered to canonical space.

## K.12 Metric library contents (C1.13)
Sensitivity, specificity, PPV, NPV with CIs; AUROC, AUPRC with CIs; QWK; confusion matrix; macro-F1; ECE, Brier, reliability bins; Dice, IoU (per class, per image, aggregate); lesion-level sensitivity vs FP/image; localisation distance (raw and normalised); Grad-CAM overlap (IoU at a heatmap threshold, pointing-type hit, coverage — exact definitions fixed in protocol). **CI methods `[ENGINEERING DECISION — fixed in evaluation protocol]`:** exact or Wilson intervals for proportions; patient/exam-level bootstrap for AUROC, QWK, and any metric on correlated eyes.

## K.13 Ablation design (EVAL-007) — pre-registered in Phase 1 protocol, finalised before freeze
Rows (candidates, final list in protocol): classical-only pipeline; single CNN classifier (no IQA, no enhancement); pipeline without enhancement; grader without lesion information; pipeline without calibration (calibration metrics only); full integrated pipeline. Each evaluated on the same splits. The PS-24 claim ("integrated pipeline outperforms any single-technique approach") is reported **as found**, including if it does not hold.

---

# SECTION L — TESTING STRATEGY

`[ENGINEERING DECISION]` Framework: `matlab.unittest` (+ `matlab.uitest` for screens). Tests tagged by category; one runner script runs any category. Automated CI depends on licence terms for CI runners **(BQ-04 `[NEEDS VERIFICATION]`)**; if CI is not possible, the rule is: the PR author attaches the local test-run summary and the reviewer re-runs the affected categories.

| Category | What it proves | Phase introduced | Owner | Gate use |
|---|---|---|---|---|
| Unit | Each function on fixed inputs incl. edge cases (TST-001) | 1 | Module owner | Every gate |
| Config | Precedence, schema validation, null-threshold fail-closed, hash stability | 1 | P2 | Every gate |
| Contract | Every stage output validates against Section I | 1 | P2 (validators), owners (conformance) | Every gate |
| Data | No leakage across splits; duplicates co-located; contamination registry honoured; sealed sets unreadable (TST-006) | 1 | P1 | Every gate |
| Metric correctness | Metric library vs hand-computed cases | 1 | P3 | Gate 1 onward |
| ML | Output shapes/ranges; determinism (MLR-007); class-map integrity; regression vs frozen internal reference (TST-003); import equivalence (TST-007) | 2 | Model owner | Gate 2 onward |
| Integration | Pipeline end-to-end vs stored expected results on a fixed image list (TST-002) | 1 (mocks), 2 (real), 3 (full) | P1 (Ph3+) | Every gate |
| Gating | Zero grades on Ungradable (TST-004) | 2 | P1 | Gate 2 onward |
| Consistency | Referable ⇔ grade ≥ 2 on all outputs (TST-005) | 2 | P3 | Gate 2 onward |
| Failure | Each ERR-001…009 produces its specified behaviour (TST-009) | 3 | P1 | Gate 3 onward |
| API/service | Each I.13 function: success, validation errors, role enforcement | 3 | P1 | Gate 3 onward |
| Frontend | Screens render required elements; missing evidence state; role visibility; timer | 3 | P3 (P2 for SCR-06) | Gate 3 onward |
| Security | Auth required; roles enforced; audit append-only; no credentials/paths in repo; case IDs contain no personal identifiers | 3 | P1 | Gate 3, 4 |
| Dependency audit | No external AI/LLM/inference calls (TST-011); no network calls from inference | 3 (script), 4 (final) | P1 | Gate 4 |
| Simulation | M/M/c analytical agreement (TST-010); parameter validation (ERR-008); seeded reproducibility | 3 | P2 | Gate 3, 4 |
| Performance | Per-stage and end-to-end timing on documented host (PERF-005) | 3 (logged), 4 (benchmark) | P1 | Gate 4 |
| E2E / demo | Demo scenario executes on held-out images (AC-020) | 4 | P1 | Gate 4 |
| Human studies | Timed review (TST-008), rating study (XAI-006) per protocol | 4 | P3 | Gate 4 |

**Test data rule:** unit and integration fixtures are **synthetic** (C1.16) unless a dataset's licence explicitly permits redistribution inside the repo (verify per licence). Tests never read sealed external sets.

---

# SECTION M — GIT WORKFLOW

| Item | Rule |
|---|---|
| Branches | `main` (always passes all tests of the current phase; protected) · short-lived `ph<N>/<person>-<topic>` (e.g., `ph2/p1-iqa-baseline`) · no long-lived personal branches |
| Commits | Small, one purpose; message `<area>: <imperative summary>` (e.g., `iqa: add focus score`); reference requirement IDs where relevant (`[IQR-001]`) |
| Pull requests | Template: what changed, requirement IDs, tests run + summary, files changed outside own area (should be none), contract changes (needs decision record) |
| Reviews | ≥1 reviewer (rotation D.2); contract, config-schema, and split changes need all three |
| Merge | Squash merge after green tests; author merges; no direct pushes to `main` |
| Binary files | `.slx`, `.mat` marked binary in `.gitattributes`; one owner per binary file; artifacts not committed (BQ-07) |
| Tags | `phase-1-splits` · `phase-1-gate` · `phase-2-L1` · `phase-2-gate` · `phase-3-gate` · `v1.0-rc` (freeze) · `v1.0-sih` |
| Release points | Each gate tag; freeze tag; final tag. Results in `docs/results/` must cite the tag they were produced from. |
| Secrets | Never committed; `.gitignore` covers `configs/local/`, data and artifact roots; a pre-commit or PR check greps for absolute paths and credential-like strings |

---

# SECTION N — DOCUMENTATION STRATEGY

| Document | Location | Owner | When |
|---|---|---|---|
| Project context (one page, for fresh sessions) | `docs/context/PROJECT_CONTEXT.md` | P2 | Ph1; updated at each gate |
| PRD (copy) + this blueprint | `docs/prd/`, `docs/BLUEPRINT.md` | P2 | Ph1 |
| Contracts | `docs/contracts/` | P2 (v1), then owner of each contract | Ph1; versioned |
| Decision records | `docs/decisions/DEC-Bnn-<slug>.md` (context, decision, alternatives, evidence, status) | Whoever decides | Continuous |
| Dataset cards | `docs/dataset_cards/` | P1 | Ph1 |
| Model cards (MLR-008) | `docs/model_cards/` | Model owner | Ph2 |
| Protocols | `docs/protocols/` (evaluation, timed review, rating study) | P3 | Ph1 (evaluation), Ph3 (human studies) |
| Phase reports | `docs/phases/PH<N>_REPORT.md` | All; assembled by phase lead for that gate (Ph1: P2, Ph2: P3, Ph3: P1, Ph4: P1) | Each gate |
| Results | `docs/results/` (generated tables/plots with run IDs) | P3 | Ph2 internal, Ph4 external |
| Setup guide | `docs/SETUP.md` | P1 | Ph4 |
| Demo script | `docs/demo/` | P1 | Ph4 |
| Toolbox usage map (MAT-003) | `docs/TOOLBOX_MAP.md` | P1 | Ph4 |

**Phase report template:** What was built · Why · How it works · Inputs/outputs · Configuration · Tests (and results) · Results (labelled internal/external, with dataset, CI, domain note, contamination status) · Known limitations · How the next phase should use it · Open items carried forward.

---

# SECTION O — FINAL INTEGRATION

Performed in Phase 4 by P1, with P2 and P3 verifying their parts.

1. **Freeze:** tag `v1.0-rc`; freeze manifest (commit, config hash, registry checksums, threshold files, split hashes).
2. **Mock purge:** release config must resolve no `+netra/+mock` function; test fails if any stage can return `status="mock"`.
3. **Clean-machine build:** follow `docs/SETUP.md` on a machine not used for development (or a fresh user account) — record every deviation and fix the guide.
4. **Test ladder:** unit → contract → data → ML regression → integration → gating/consistency → failure injection → service/API → UI → security + dependency audit → simulation validation → performance benchmark → E2E demo run.
5. **Component checks:** ML (registry checksums verified at load) · backend (all ERR paths) · explainability (evidence bundle complete or explicitly marked) · storage (case store + append-only audit) · simulation (runs from measured parameters; provisional values visibly tagged) · deployment (offline run, NFR-010: disconnect network and repeat demo).
6. **Sign-off:** each person signs Gate 4 items for their deliverables; tag `v1.0-sih`.

---

# SECTION P — SIH DEMONSTRATION

**Data rule:** only public-dataset **test** images (held-out), labelled on screen as "public dataset test image — not patient data". No real patient data (SEC-008).

**Anti-cherry-picking rule `[ENGINEERING DECISION]`:** the four demo cases (PRD §12.3) are selected **by their ground-truth labels before running the frozen system** (one ICDR 0 gradable, one referable-labelled, one quality-Borderline-labelled, one Ungradable-labelled), and whatever the system outputs is shown, including errors. Selection is recorded in `docs/demo/case_selection.md` with image IDs and the selection time.

**Flow (maps to PS-22 / AC-020):**

| Step | Screen | What is shown | Requirement |
|---|---|---|---|
| 1 | Login (technician) | Role-based access | SEC-001/002 |
| 2 | SCR-01 | Upload test image | FR-001 |
| 3 | SCR-02 | Verdict + reasons + guidance (ungradable case: rejected with reason; borderline case: enhanced and re-checked) | PS-02…04 |
| 4 | Backend (log view or status) | Stages executing with per-stage timing | BE-003 |
| 5 | Login (ophthalmologist) → SCR-05 | Case in queue with priority reason | FR-016 |
| 6 | SCR-03 | Original/enhanced, Grad-CAM, lesion overlays, grade, referable flag, calibrated confidence, flags, criteria panel, disclaimer; confirm or override; timer | PS-13…17 |
| 7 | SCR-04 | Annotated report; export | PS-16 |
| 8 | Evaluation dashboard (static results from `docs/results/`) | External metrics with CIs, ablation, benchmark comparison, calibration, overlap, rating and timed-review results — each labelled with dataset and domain note | PS-12, 20, 23, 24 |
| 9 | Login (administrator) → SCR-06 | 100k/year baseline; sweeps showing upload-, AI-, review-bound regimes; optimised configuration with ranges; which parameters are measured vs provisional | PS-18, 19 |

**Positioning line on every results slide:** screening/triage aid; no clinical validation, regulatory, or diagnostic claim (PRD §2).

---

# SECTION Q — RISKS & BLOCKERS

| ID | Risk / blocker | Phase affected | Owner | Mitigation in this plan |
|---|---|---|---|---|
| BQ-01 | `[BLOCKER]` Deadline meaning unknown (30 Sep 2026) | All | P3 | Verify before Phase 1 time-box; re-scope to L1 if a build is due |
| OQ-02 | `[BLOCKER]` External training acceptability | 2 | P3 | MATLAB-only fallback adopted if unresolved at Gate 1 |
| BQ-03 | `[BLOCKER]` Licences (3 seats, toolboxes, Simulink, SimEvents) and GPU | 1–4 | P2 | Inventory at C1.2; fallback Simulink/Stateflow queue if no SimEvents (R-10); smaller models if no GPU |
| R-01 | Domain shift clinic → portable | 4 | P3 | mBRSET if accessible; disclosure (DAT-014) |
| R-02 | Scarce pixel-level lesion data | 2 | P2 | Classical baselines; combine IDRiD+DDR; augmentation |
| R-03 | No NV pixel labels | 2 | P2 | K.8 options; disclosure |
| R-04 | External training judged non-compliant | 2 | P3 | MATLAB-native baseline always kept runnable |
| R-05 | Clinician raters unavailable | 4 | P3 | Outreach starts Phase 1; proxies disclosed as proxies |
| R-06 | Leakage/contamination | 1–4 | P1 | Dedup, registry, split guard, tests |
| R-07 | PS sens/spec not met | 4 | P3 | Operating point from validation; honest report |
| R-08 | Spurious Grad-CAM | 3–4 | P2/P3 | Overlap scoring, low-agreement flag, lesion overlays beside heatmap |
| R-09 | "Sub-pixel" / "hemorrhage classification" misread | 2 | P3 | OQ-04/05 resolved at Gate 1 or provisional + flagged |
| R-10 | SimEvents unavailable | 3 | P2 | Licence check Phase 1; fallback design |
| R-11 | Scope too large | All | All | L1 checkpoint inside Phase 2; L2 time-boxed |
| R-12 | Messidor-2 labels unobtainable | 4 | P3 | IDRiD + APTOS held-out as fallback, disclosed |
| R-13 | Calibration degrades out of domain | 4 | P3 | Re-measure per set; conservative routing |
| BR-01 | Binary file conflicts (`.slx`, `.mat`) | 3–4 | P2 | One owner per binary; programmatic UI |
| BR-02 | Context loss between fresh sessions | All | All | Prompts reference repo docs; decisions only valid once written |
| BR-03 | Phase gate slippage cascades | All | All | Gate items are binary; unfinished L2 work becomes a documented limitation, not a gate blocker |
| BR-04 | Large dataset downloads/storage | 1 | P1 | Download only what roles in PRD §16.1 require; record sizes |
| BR-05 | Tests needing licensed images in repo | 1–4 | P2 | Synthetic fixtures |

---

# SECTION R — OPEN QUESTIONS

## R.1 PRD open questions — when each must be resolved

| ID | Question (short) | Must be resolved by | Owner | Fallback if not |
|---|---|---|---|---|
| OQ-01 | Official PS text matches mirror | Gate 1 | P3 | Blocking for submission |
| OQ-02 | Training outside MATLAB acceptable | Gate 1 | P3 | MATLAB-only |
| OQ-03 | Must all six toolboxes be used | Gate 3 | P3 | Use only where genuine (MAT-003) |
| OQ-04 | Meaning of sub-pixel MA detection | Gate 1 | P3 | Report centroid error in px (CVR-003); flag |
| OQ-05 | Meaning of hemorrhage classification | Gate 1 | P3 | Provisional: presence/extent by region; flag |
| OQ-06 | Rating-study protocol | Gate 3 | P3 | Blocks AC-018 |
| OQ-07 | Max recaptures, terminal action | Gate 3 | P1 | Configurable; value documented as provisional |
| OQ-08 | Review bypass outside simulation | Only if proposed | P3 | Not adopted |
| OQ-09 | Low-confidence threshold | Gate 2 (derived) | P3 | Fail closed → all mandatory review |
| OQ-10 | Retention policy | Gate 4 | P1 | Demo-only policy documented |
| OQ-11 | Optimisation objective and constraints | Gate 3 | P2 | Blocks AC-017 |
| OQ-12 | Target hardware/OS | Gate 3 | P1 | Documented demo host |
| OQ-13 | <30 s pass statistic | Gate 1 (protocol) | P3 | Must be stated before the test |
| OQ-14 | Supported formats/resolutions | Gate 2 | P1 | Config list from dataset formats |
| OQ-15 | Messidor-2 labels; IDRiD subset overlap | Gate 1 | P1/P3 | R-12 fallback |
| OQ-16 | mBRSET, NV-labelled data access | Gate 1 | P1 | Disclosure; K.8 option (c) |
| OQ-17 | Indian regulatory/privacy requirements | Only for real deployment | P3 | No claim made |

## R.2 New questions raised by this blueprint

| ID | Question | Why it matters | How to verify | Blocking? |
|---|---|---|---|---|
| BQ-01 | What does the 30 Sep 2026 deadline require? | Sets all time-boxes and scope | sih.gov.in, college SPOC | **Yes** |
| BQ-02 | Which team member is P1/P2/P3? | Skill fit | Team decision | Yes, before Phase 1 |
| BQ-03 | MATLAB release, licences per person, SimEvents, GPU | Environment, training feasibility | Licence portal; `ver`; `gpuDevice` | Yes, Gate 1 |
| BQ-04 | Can MATLAB run in CI for this repo? | Automated testing | MathWorks CI licensing terms for your licence type | No (manual fallback) |
| BQ-05 | Target review display spec (resolution/size) | UX-001 "without scrolling" | Ask intended reviewer setup; else document demo display | No |
| BQ-06 | Report export format (FR-022) and whether MATLAB Report Generator is licensed | Report implementation | Licence check | No |
| BQ-07 | Where model artifacts are shared | Reproducibility across 3 machines | Team decision | No |
| BQ-08 | Confirm programmatic UI vs App Designer | Merge safety | Team decision | No |
| BQ-09 | Git hosting and whether repo is private | Workflow, CI | Team decision | Yes, before Phase 1 |
| BQ-10 | Phase time-boxes | Planning | After BQ-01 | Yes |

---

# SECTION S — MASTER PROJECT CHECKLIST

**Before Phase 1**
- [ ] BQ-01 deadline verified · [ ] BQ-02 roles assigned · [ ] BQ-09 repo host · [ ] BQ-10 time-boxes set

**Phase 1**
- [ ] Repo + MATLAB Project + README (C1.1) · [ ] Environment record (C1.2) · [ ] Config system + schemas (C1.3)
- [ ] Contracts v1 + validators (C1.4) · [ ] Skeleton with mocks (C1.5) · [ ] Test runner (C1.6) · [ ] Synthetic fixtures (C1.16)
- [ ] Dataset register (C1.7) · [ ] Metadata table (C1.8) · [ ] Dedup + contamination registry (C1.9) · [ ] Frozen splits + sealed sets (C1.10) · [ ] Datastores (C1.11) · [ ] Data report (C1.12)
- [ ] Metric library (C1.13) · [ ] Evaluation protocol (C1.14) · [ ] OQ decisions (C1.15) · [ ] Clinician outreach started
- [ ] Gate 1 signed · [ ] tag `phase-1-gate`

**Phase 2**
- [ ] Preprocessing/FOV · [ ] IQA baseline (+ learned decision) · [ ] Enhancement + ENH-004 evaluation · [ ] OD/fovea
- [ ] Vessels · [ ] MA · [ ] EX · [ ] HE (per OQ-05) · [ ] NV (validation level disclosed) · [ ] SE (L2)
- [ ] Grading baseline + candidates · [ ] Decision rule · [ ] Operating point · [ ] Calibration · [ ] Grad-CAM · [ ] OOD (L2)
- [ ] L1 checkpoint · [ ] Model cards for all · [ ] Skeleton runs real stages · [ ] Gate 2 signed · [ ] tag `phase-2-gate`

**Phase 3**
- [ ] Orchestrator + timing · [ ] Case store + audit · [ ] Routing engine · [ ] Error handling (ERR-001…009) · [ ] Auth/roles · [ ] Report + export · [ ] Service API
- [ ] Evidence bundle · [ ] Criteria panel with cited ICDR source · [ ] Overlap metrics · [ ] Uncertainty flag rules
- [ ] SCR-01 · [ ] SCR-02 · [ ] SCR-05 · [ ] SCR-03 · [ ] SCR-04 · [ ] Review timer · [ ] Proxy pilot (labelled)
- [ ] Simulink structure · [ ] M/M/c validation · [ ] Protocols for rating + timed review · [ ] OQ-11 decided
- [ ] Gate 3 signed · [ ] tag `phase-3-gate`

**Phase 4**
- [ ] Freeze `v1.0-rc` · [ ] Timing benchmark · [ ] External evaluation (once) · [ ] Ablation · [ ] Benchmark comparison · [ ] Calibration per set · [ ] Overlap summary · [ ] Rating study · [ ] Timed review · [ ] Error analysis
- [ ] Simulation parameterised · [ ] Sweeps · [ ] Optimisation with ranges · [ ] SCR-06
- [ ] Mock purge · [ ] Dependency + security audit · [ ] Packaging · [ ] Clean-machine setup · [ ] Offline demo run · [ ] Demo rehearsal
- [ ] Final report · [ ] Toolbox map · [ ] Gate 4 signed · [ ] tag `v1.0-sih`

---

# SECTION T — FRESH-CONTEXT PROMPTS

## T.1 How to use these prompts

1. Open a fresh Claude session. 2. Paste one prompt in full. 3. Provide the repository (or the files listed under FILES TO INSPECT). 4. Let the session inspect, implement, and run tests. 5. Review its final response against the Definition of Done. 6. Merge through a pull request (Section M). 7. Update `docs/context/PROJECT_CONTEXT.md` if the handoff note changes the project state.

Every prompt is self-contained: it restates the project context, the problem statement, and the three rules, and it points only to files that exist in the repository by the time that prompt runs. **PH1-P2-A runs first**, because it creates the repository and places the PRD and this blueprint where every later prompt expects them. Each prompt is also provided as a separate file (`prompts/<ID>.md`) for copy-paste.

If a prompt's STOP condition fires, the session reports and stops. Resolve the missing item (usually a decision record), then re-run the same prompt in a new session.

## T.2 Prompt index and order

| ID | Workstream | Can start | Needs first |
|---|---|---|---|
| PH1-P2-A | Repository, environment record, configuration system, project context (bootstrap) | Immediately | Nothing (bootstrap) |
| PH1-P1-A | Dataset acquisition, verification and register | Immediately (downloads); register after PH1-P2-A | Licence texts, downloads |
| PH1-P3-A | Metric library and evaluation protocol | After PH1-P2-A | Repo + config |
| PH1-P3-B | Open-question resolution, licence and compute inventory, clinician outreach plan | Immediately | Mentor/portal access |
| PH1-P2-B | Contracts v1, validators, walking skeleton with mocks, test runner, synthetic fixtures | After PH1-P2-A | Repo + config |
| PH1-P1-B | Metadata table, deduplication, contamination registry, splits, datastores | After PH1-P1-A, PH1-P2-B | Register, contracts |
| PH2-P1-A | Preprocessing (FOV and canonical space) and image quality assessment | Gate 1 | Phase 1 bundle |
| PH2-P2-A | Vessel segmentation and microaneurysm detection | Gate 1 (switch to canonical crops when PH2-P1-A lands) | OQ-04 decision |
| PH2-P3-A | DR grading, decision rule and operating point | Gate 1 (same switch rule) | OQ-02 decision |
| PH2-P1-B | Adaptive enhancement and optic disc / fovea localisation | After PH2-P1-A | Preprocessing, IQA |
| PH2-P2-B | Exudates, hemorrhages, soft exudates, neovascularization | After PH2-P2-A, PH2-P1-B (OD) | OQ-05, OQ-16 decisions |
| PH2-P3-B | Calibration, Grad-CAM, uncertainty candidate, Phase 2 integration run | After PH2-P3-A; integration run last | All Phase 2 stages |
| PH3-P1-A | Orchestrator, case store, audit log, routing engine, error handling | Gate 2 | Phase 2 bundle |
| PH3-P2-A | Explainability layer and uncertainty flags (evidence bundle) | Gate 2 | ICDR source citation |
| PH3-P2-B | Simulink telemedicine pipeline model and M/M/c validation | Gate 2 (independent of ML) | SimEvents decision |
| PH3-P1-B | Authentication and roles, report generation and export, service API | After PH3-P1-A | BQ-06 export format |
| PH3-P3-A | UI foundation and technician screens (SCR-01, SCR-02) | Gate 2 (fixtures until service API lands) | Service API contract |
| PH3-P3-B | Review queue, review workstation, report view, review timing, proxy pilot | After PH3-P3-A, PH3-P1-B, PH3-P2-A | Display spec (BQ-05) |
| PH4-P1-A | Freeze, timing benchmark, mock purge, dependency and security audit | Gate 3 — runs first | Phase 3 bundle |
| PH4-P3-A | External evaluation, ablation, benchmark comparison, calibration, explanation overlap | After freeze | Freeze manifest, benchmark citations |
| PH4-P3-B | Timed review test, clinician rating study, error analysis, results dossier | After freeze | Participants, protocols |
| PH4-P2-A | Simulation parameterisation, scenarios, optimisation | After PH4-P1-A benchmark; re-run after PH4-P3-B | OQ-11 decision |
| PH4-P2-B | Simulation and optimisation console (SCR-06) | After PH4-P2-A | Simulation service functions |
| PH4-P1-B | Packaging, setup guide, final integration, demo runner, final report | After freeze; final report last | All results |

## T.3 Prompts

### PH1-P1-A — Dataset acquisition, verification and register

```text
FRESH-CONTEXT PROMPT PH1-P1-A: Dataset acquisition, verification and register

ROLE
Senior data engineer for medical imaging datasets, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 1: Foundation (verified data, frozen contracts, walking skeleton).

CURRENT PERSON/WORKSTREAM
Person 1, data pipeline, part A.

OBJECTIVE
Produce a verified dataset register and verification scripts for every dataset named in PRD Section 16.1, so later work relies only on checked facts and permitted uses.

RELEVANT PRD REQUIREMENTS
DAT-001 (register fields), DAT-005 (known overlaps), DAT-010, DAT-011, DAT-012, DAT-013, DAT-015 (re-verify figures), SEC-005 (licences), OQ-15, OQ-16, DEC-10 (DRAC22 excluded).

WHAT ALREADY EXISTS
Expected: repository skeleton and config loader from PH1-P2-A. Verify; if the config loader is absent, write scripts that take the data root as a function argument and mark the integration with the loader as a follow-up.

INPUTS
Official dataset pages and licence texts (provided by the human; you may not have internet access); downloaded archives placed by the human under the data root; PRD Section 16.1.

EXPECTED OUTPUTS
- data_manifests/dataset_register.json with, per dataset: source URL as given by the human, version/date, licence/access terms (quoted or summarised with source), modality, camera(s), population, label types, label provenance, documented size, script-computed size, known limitations, permitted use (train/val/test/none), status (acquired / access-pending / unavailable).
- configs/schema/dataset_register.schema.json.
- scripts/data/verify_dataset_*.m: checksum archives, count files, count labels per class from the dataset's own label files.
- docs/dataset_cards/<dataset>.md for each dataset.

INTERFACES
Blueprint Section I.19 (manifest columns that later depend on this register), Section J (acquisition and verification rows).

DEPENDENCIES
Human performs downloads under each dataset's terms. Config loader (PH1-P2-A) if present.

FILES TO INSPECT
docs/prd/SIH26038_Final_PRD.md (Sections 16, 41, 43), docs/BLUEPRINT.md (Sections I.19, J), configs/, src/+netra/+config/, data_manifests/.

FILES ALLOWED TO MODIFY
data_manifests/dataset_register.json, configs/schema/dataset_register.schema.json, scripts/data/, docs/dataset_cards/, tests/data/ (new tests only).

FILES NOT TO MODIFY
src/+netra/+config/, docs/contracts/, docs/prd/, any other person's area.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Every figure in the register has two fields: documented (with source) and computed (by script). Mismatches are recorded, not "fixed".
- A dataset whose licence you cannot read is status access-pending with permitted use "none".
- Record the PRD's known overlaps (RETFound pretraining includes Kaggle-EyePACS; EyeQ is derived from EyePACS; Messidor-2 contains original-Messidor images) as registry notes for PH1-P1-B.
- Do not download anything yourself from unofficial mirrors; list what the human must fetch.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Register validates against its schema; verification scripts run on a synthetic miniature dataset in tests/fixtures and produce the expected counts; no absolute path appears in any file.

VALIDATION REQUIREMENTS
For each acquired dataset, computed counts are reported next to documented counts.

DOCUMENTATION REQUIREMENTS
Dataset card per dataset: facts (documented vs computed), licence, permitted use, limitations, contamination notes.

DEFINITION OF DONE
Every dataset in PRD 16.1 has a register entry and card; every acquired dataset has passing verification output; mismatches and unknowns are labelled.

STOP CONDITIONS
- The human has not provided licence text or download location for a dataset: mark it and stop for that dataset.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH1-P1-B — Metadata table, deduplication, contamination registry, splits, datastores

```text
FRESH-CONTEXT PROMPT PH1-P1-B: Metadata table, deduplication, contamination registry, splits, datastores

ROLE
Senior data engineer for medical imaging, specialising in leakage-free dataset construction in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 1: Foundation.

CURRENT PERSON/WORKSTREAM
Person 1, data pipeline, part B.

OBJECTIVE
Build the master metadata table, duplicate groups, contamination registry, frozen patient/exam-level splits with sealed external test sets, a split-guarded datastore API, and a script-generated data report.

RELEVANT PRD REQUIREMENTS
DAT-002, DAT-003, DAT-004, DAT-005, DAT-006, DAT-007, DAT-008, DAT-009, DAT-011, DAT-014, MLR-003, TST-006, EVAL-001/002/003 (which sets are tests).

WHAT ALREADY EXISTS
Expected: dataset register (PH1-P1-A); config loader and contracts v1 (PH1-P2-A/B). Verify all three.

INPUTS
data_manifests/dataset_register.json; downloaded data under the data root; manifest contract (Blueprint I.19).

EXPECTED OUTPUTS
- data_manifests/master_metadata.csv + schema.
- Duplicate groups (exact hash, perceptual hash, structural similarity) and data_manifests/contamination_registry.json.
- data_manifests/splits/<dataset>_<split>.csv plus a hash file; external test sets marked sealed.
- src/+netra/+data/: functions returning datastores by (dataset, split, task) that refuse sealed splits unless a Phase 4 unlock configured through the config system is present together with a freeze manifest.
- docs/phases/PH1_data_report.md generated by a script.

INTERFACES
Blueprint I.19 (manifest), I.15 (config), J (pipeline stages).

DEPENDENCIES
PH1-P1-A register; PH1-P2-A config; PH1-P2-B contracts.

FILES TO INSPECT
docs/BLUEPRINT.md (I.15, I.19, J, K.0), docs/contracts/, data_manifests/, src/+netra/+config/, docs/decisions/.

FILES ALLOWED TO MODIFY
data_manifests/, src/+netra/+data/, scripts/data/, tests/data/, docs/phases/PH1_data_report.md, configs/default/data.json (create if absent; keys only for data settings).

FILES NOT TO MODIFY
src/+netra/+config/, docs/contracts/ (propose changes via a decision record instead), other persons' areas.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Splits at patient/exam level where IDs exist, eye pairs together, stratified by source (DAT-003). Where a dataset lacks patient IDs, record this and document the fallback used.
- Duplicate groups are always placed in one split (DAT-004).
- Near-duplicate thresholds for perceptual hash and structural similarity are chosen empirically on the data (document how) and stored in config with provenance; do not pick an unexplained number.
- Original Messidor images must not enter any training split if Messidor-2 is a test set (DAT-011).
- Seeds for any randomised step live in config and are recorded in the split hash file.
- Report numbers are computed by the script, never typed.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Leakage tests (no patient/exam ID or duplicate group crosses splits); sealed-split refusal test; synthetic duplicate detection test; schema tests; re-running split generation with the same seed reproduces identical hashes.

VALIDATION REQUIREMENTS
Counts per dataset per split per grade (and per label type) in the data report; known overlaps from the register are detected.

DOCUMENTATION REQUIREMENTS
Data report; a section in docs/phases/PH1_REPORT.md draft describing splits, sealing, and how Phase 2 obtains data.

DEFINITION OF DONE
Splits frozen and hashed (ready for tag phase-1-splits); datastore API usable by Phase 2 for every task in Blueprint K; all data tests pass.

STOP CONDITIONS
- A dataset's patient/exam identity cannot be determined and the choice of fallback materially changes leakage risk: stop and ask.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH1-P2-A — Repository, environment record, configuration system, project context (bootstrap)

```text
FRESH-CONTEXT PROMPT PH1-P2-A: Repository, environment record, configuration system, project context (bootstrap)

ROLE
Senior MATLAB software architect.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

NOTE: This is the first prompt of the project. The repository may be empty. The human must provide SIH26038_Final_PRD.md and BLUEPRINT.md in this session; if they are not provided, STOP.

CURRENT PHASE
Phase 1: Foundation.

CURRENT PERSON/WORKSTREAM
Person 2, platform, part A.

OBJECTIVE
Create the repository structure, MATLAB Project, environment record, configuration system, and the one-page project context document that every later fresh session reads.

RELEVANT PRD REQUIREMENTS
FR-020, NFR-003, MAT-007, OPS-001, DEP-005 (later), SEC-008.

WHAT ALREADY EXISTS
Possibly nothing. Inspect the working directory first.

INPUTS
PRD and blueprint (provided by the human); Blueprint Sections C, I.15, M; output of `ver` and GPU query from each team member (provided by the human).

EXPECTED OUTPUTS
- Directory structure of Blueprint Section C, MATLAB Project file, README with clone-to-green steps, .gitignore, .gitattributes (.slx and .mat binary).
- docs/prd/ (PRD copy), docs/BLUEPRINT.md (copy), docs/context/PROJECT_CONTEXT.md (current state, phase, owners, where things live).
- src/+netra/+config/: load, merge by precedence (default < profile < local < environment variables for roots), JSON-schema validation, config hash, threshold fail-closed helper.
- configs/default/*.json skeletons with only keys that are already decided; configs/schema/; configs/local/local.example.json.
- docs/phases/PH1_environment.md: MATLAB release, toolboxes with versions, GPU/driver, OS per machine, as provided; unknowns marked.

INTERFACES
Blueprint I.15 (configuration contract).

DEPENDENCIES
None.

FILES TO INSPECT
Everything present in the working directory; the provided PRD and blueprint.

FILES ALLOWED TO MODIFY
All files needed to create the structure above.

FILES NOT TO MODIFY
The PRD content (copy verbatim).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Environment variable names for roots are an engineering decision: record them in docs/contracts/configuration.md and in a decision record.
- Schema validation: use the simplest approach available in the pinned MATLAB release (e.g., hand-written validators) and do not add third-party dependencies without recording a decision.
- The threshold helper returns an error (not a default) when a threshold value is null.
- Record the environment as provided; do not fill blanks.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Unit tests for precedence, missing-key errors, schema violations, null-threshold fail-closed, config hash stability (same inputs, same hash; changed value, changed hash).

VALIDATION REQUIREMENTS
A fresh clone opens the project and runs the test suite with zero failures.

DOCUMENTATION REQUIREMENTS
README; PROJECT_CONTEXT.md; configuration contract; decision record for root variable names.

DEFINITION OF DONE
Structure exists; config system tested; environment recorded; context doc exists and is accurate.

STOP CONDITIONS
- PRD or blueprint not provided.
- Team members' environment outputs not provided: create the record with fields marked [NEEDS VERIFICATION] and report it as incomplete.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH1-P2-B — Contracts v1, validators, walking skeleton with mocks, test runner, synthetic fixtures

```text
FRESH-CONTEXT PROMPT PH1-P2-B: Contracts v1, validators, walking skeleton with mocks, test runner, synthetic fixtures

ROLE
Senior MATLAB software architect and test engineer.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 1: Foundation.

CURRENT PERSON/WORKSTREAM
Person 2, platform, part B.

OBJECTIVE
Publish interface contracts v1, implement validators, build an orchestrator skeleton that runs mock stages end-to-end on a synthetic image, and set up the test runner and synthetic fixtures.

RELEVANT PRD REQUIREMENTS
BE-001 (stage order), BE-002, BE-004, NFR-004, TST-001, TST-002, FR-003 (no grade for Ungradable must be enforceable), FR-009 (referable consistency must be checkable).

WHAT ALREADY EXISTS
Expected: repository and config system (PH1-P2-A). Verify.

INPUTS
Blueprint Section I (all subsections).

EXPECTED OUTPUTS
- docs/contracts/*.md, one per contract in Blueprint Section I, versioned v1.
- src/+netra/+contracts/: one validator per contract.
- src/+netra/+pipeline/: orchestrator skeleton, stage registry (stage name -> function handle, from config), timing capture.
- src/+netra/+mock/: [MOCK — TEMPORARY ONLY] stages returning contract-valid envelopes with status "mock" and empty payload values (no grades, probabilities, or lesions).
- tests/ layout per Blueprint Section L with tags; a runner script that runs any category.
- tests/fixtures/: generator for SYNTHETIC fundus-like images (e.g., a disc on a dark background) clearly labelled synthetic in names and metadata.

INTERFACES
Blueprint Section I.

DEPENDENCIES
PH1-P2-A.

FILES TO INSPECT
docs/BLUEPRINT.md (C, I, L), src/+netra/, configs/, tests/.

FILES ALLOWED TO MODIFY
docs/contracts/, src/+netra/+contracts/, src/+netra/+pipeline/, src/+netra/+mock/, tests/ (runner, fixtures, platform tests), configs/default/pipeline.json.

FILES NOT TO MODIFY
src/+netra/+config/ except bug fixes recorded in the response; other persons' areas.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Each mock states in its header: why needed, what it represents, what replaces it (the Phase 2 stage), removal deadline (Phase 4 mock purge).
- Stage registry is read from config so Phase 2 can swap mocks for real stages without code edits.
- Validators reject: a grade on an Ungradable case; referable not equal to grade >= 2; enhancement applied to a first-pass Ungradable image; absolute paths in image references.
- Values not fixed by the blueprint (image sizes, thresholds) are not given defaults in contracts; they are declared as coming from artifact metadata or threshold config.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Valid and invalid fixture for every contract; integration test: synthetic image -> all mock stages -> CaseRecord validates, all statuses "mock", written to a temporary case-store location from config.

VALIDATION REQUIREMENTS
Runner executes each category independently and all together.

DOCUMENTATION REQUIREMENTS
Contract docs; update PROJECT_CONTEXT.md; section of PH1_REPORT.md on platform.

DEFINITION OF DONE
All Section I contracts documented and validated; skeleton integration test passes; runner works.

STOP CONDITIONS
- Two blueprint contract definitions conflict: stop and describe both.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH1-P3-A — Metric library and evaluation protocol

```text
FRESH-CONTEXT PROMPT PH1-P3-A: Metric library and evaluation protocol

ROLE
Biostatistician and medical-AI evaluation engineer working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 1: Foundation.

CURRENT PERSON/WORKSTREAM
Person 3, evaluation core, part A.

OBJECTIVE
Implement and verify every metric the project reports, and write the pre-registered evaluation protocol that fixes procedures before any model exists.

RELEVANT PRD REQUIREMENTS
PERF-001...009, EVAL-001...012, UNC-001, XAI-005, SEG-010, MLR-003, MLR-004, MLR-006, NFR-009, OQ-13, MAT-005.

WHAT ALREADY EXISTS
Expected: repository and config system. Verify.

INPUTS
Blueprint Sections K.9, K.10, K.12, K.13; PRD Sections 33 and 35.

EXPECTED OUTPUTS
- src/+netra/+eval/: sensitivity, specificity, PPV, NPV with CIs; AUROC, AUPRC with CIs; QWK; confusion matrix; macro-F1; ECE, Brier, reliability bins; Dice, IoU (per class, per image, aggregate); lesion-level sensitivity vs false positives per image; localisation distance (raw and normalised); Grad-CAM overlap metrics.
- docs/protocols/evaluation_protocol.md: datasets and roles; CI methods; operating-point procedure (meet sensitivity target on internal validation, maximise specificity); freeze rules; one-shot external use; pre-registered ablation variants; published-benchmark comparison rules; the pass statistic for the <30 s review time (OQ-13) stated before any test; honest-reporting checklist.

INTERFACES
Metric functions take plain arrays and return structs with value, CI, method, n. No dataset logic inside.

DEPENDENCIES
PH1-P2-A.

FILES TO INSPECT
docs/prd/SIH26038_Final_PRD.md (33, 35, 36, 37), docs/BLUEPRINT.md (K), src/+netra/.

FILES ALLOWED TO MODIFY
src/+netra/+eval/, tests/unit/eval/, docs/protocols/evaluation_protocol.md, docs/decisions/ (new records).

FILES NOT TO MODIFY
Other persons' areas; docs/contracts/.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- CI methods are an engineering decision recorded in the protocol and a decision record (Blueprint K.12 proposes exact/Wilson for proportions and exam-level bootstrap for AUROC/QWK; confirm or change with reasons).
- Where a metric definition has variants (e.g., ECE binning, Grad-CAM overlap threshold, localisation normaliser), fix the variant in the protocol and cite the source of the definition; do not invent a citation.
- Prefer Statistics and Machine Learning Toolbox functions where they exist; test them anyway.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Every metric tested against hand-computed small cases, including edge cases (no positives, all positives, perfect and worst predictions, empty masks).

VALIDATION REQUIREMENTS
Protocol reviewed by Person 1 and Person 2 (record reviewers in the doc).

DOCUMENTATION REQUIREMENTS
Protocol; metric reference (definition, formula, source) per metric.

DEFINITION OF DONE
All listed metrics implemented and tested; protocol complete, including OQ-13 statistic and ablation variants.

STOP CONDITIONS
- A metric definition required by the PRD is ambiguous and the choice changes reported results materially: stop and present the options.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH1-P3-B — Open-question resolution, licence and compute inventory, clinician outreach plan

```text
FRESH-CONTEXT PROMPT PH1-P3-B: Open-question resolution, licence and compute inventory, clinician outreach plan

ROLE
Technical project manager and medical-AI researcher. This is a research and decision-recording task, not a coding task.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 1: Foundation.

CURRENT PERSON/WORKSTREAM
Person 3, open questions, part B.

OBJECTIVE
Resolve, or escalate with an adopted fallback, every question that blocks Phase 2, and start the long-lead human dependencies.

RELEVANT PRD REQUIREMENTS
OQ-01, OQ-02, OQ-03, OQ-04, OQ-05, OQ-06 (start), OQ-13 (with PH1-P3-A), OQ-15, OQ-16; Blueprint BQ-01, BQ-03, BQ-04, BQ-06; R-04, R-05, R-10.

WHAT ALREADY EXISTS
Blueprint Sections Q and R list the questions. Check docs/decisions/ for any already resolved.

INPUTS
Answers the human obtains from sih.gov.in, the MathWorks mentor, licence portals, dataset documentation, and team members. You may not have internet access; when you need a fact, write the exact question the human should ask and where.

EXPECTED OUTPUTS
- docs/phases/PH1_open_questions.md: per question, the question, why it matters, the source consulted (supplied by the human), the answer or "unresolved", and the adopted fallback.
- One decision record per resolved question in docs/decisions/.
- Mentor question list (ready to send) for OQ-02, OQ-03, OQ-04, OQ-05.
- Licence and compute inventory (MATLAB seats, toolboxes, Simulink, SimEvents, Report Generator, GPU) as provided.
- Clinician outreach plan for the rating study and timed review (roles needed, what is asked of them, consent notes); no personal data stored beyond what participants agree to.

INTERFACES
Decision record format: context, decision, alternatives, evidence/source, status.

DEPENDENCIES
Human access to mentor and portals.

FILES TO INSPECT
docs/prd/SIH26038_Final_PRD.md (41-43), docs/BLUEPRINT.md (Q, R), docs/decisions/.

FILES ALLOWED TO MODIFY
docs/phases/PH1_open_questions.md, docs/decisions/, docs/protocols/outreach_plan.md.

FILES NOT TO MODIFY
Code; contracts; PRD.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Never record an answer that the human did not provide from a named source.
- For OQ-04 and OQ-05, list plausible interpretations with their data and design consequences, recommend one provisional interpretation, and mark it pending mentor confirmation.
- For BQ-01, state the scope consequence of each possible answer.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Not a coding task. Consistency check: every Phase-2-blocking question in Blueprint R.1 has a status.

VALIDATION REQUIREMENTS
Each answer cites its source.

DOCUMENTATION REQUIREMENTS
As outputs.

DEFINITION OF DONE
OQ-02, OQ-04, OQ-05, OQ-15, OQ-16, BQ-01, BQ-03 each resolved or escalated with an adopted fallback; mentor questions sent (recorded by the human); outreach started.

STOP CONDITIONS
- The human asks you to record an answer without a source: record it as unverified and flag it.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P1-A — Preprocessing (FOV and canonical space) and image quality assessment

```text
FRESH-CONTEXT PROMPT PH2-P1-A: Preprocessing (FOV and canonical space) and image quality assessment

ROLE
Senior computer vision engineer for retinal image quality, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 1, preprocessing and IQA.

OBJECTIVE
Deliver (1) FOV detection, crop and canonical image space with a transform record, first, because Person 2 and Person 3 depend on it; then (2) a rule-based IQA baseline producing a 3-state verdict with focus, illumination and FOV scores and reason codes; then (3) optionally a learned IQA adopted only if it lowers the false-"Gradable" rate.

RELEVANT PRD REQUIREMENTS
CVR-001, CVR-005, FR-003, FR-004, IQR-001...007, ERR-002, ERR-009, DAT-010, MLR-001, MLR-002, MLR-007, MLR-008.

WHAT ALREADY EXISTS
Phase 1 gate outputs: datastore API, frozen splits, contracts v1 (I.1-I.3), metric library, skeleton with mock stages, decision records. Verify each.

INPUTS
Quality-labelled data per DAT-010 via the datastore API (IDRiD must not be used as a source of ungradable examples); Blueprint K.1, K.2.

EXPECTED OUTPUTS
- src/+netra/+preprocess/ stage + transform record; src/+netra/+iqa/ stage conforming to I.3.
- configs/thresholds/iqa.json with provenance; configs/default/iqa.json (reason codes, guidance text keys and text).
- training/iqa/ (if a learned model is attempted) with experiment configs.
- Artifacts per I.14 for any learned model; model card docs/model_cards/iqa.md.
- Internal-validation comparison table: baseline vs learned (false-Gradable and false-Ungradable rates, per-reason agreement where labels allow).
- Model registry entries replacing the mock preprocess and IQA stages.

INTERFACES
Blueprint I.1, I.2, I.3, I.14, I.15.

DEPENDENCIES
Phase 1 gate. Blocks Person 2 and Person 3: land preprocessing first and announce it.

FILES TO INSPECT
docs/BLUEPRINT.md (F, I.1-I.3, I.14, K.0-K.2), docs/contracts/, docs/decisions/, src/+netra/+data/, src/+netra/+pipeline/, src/+netra/+mock/, configs/.

FILES ALLOWED TO MODIFY
src/+netra/+preprocess/, src/+netra/+iqa/, training/iqa/, configs/default/iqa.json, configs/thresholds/iqa.json, configs/models/model_registry.json (your entries only), tests/unit/iqa/, tests/ml/iqa/, docs/model_cards/iqa.md.

FILES NOT TO MODIFY
src/+netra/+data/, +contracts/, +pipeline/, other persons' stages.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Focus, illumination and FOV are separate scored criteria; each Ungradable verdict carries at least one reason code and guidance key.
- The label mapping from each dataset's quality labels to Gradable/Borderline/Ungradable (e.g., EyeQ Good/Usable/Reject) is documented as an assumption (PRD A-04) with its source.
- Thresholds are derived on the internal training/validation split and written to configs/thresholds with provenance; never typed by hand.
- Non-fundus images must yield Ungradable with NON_FUNDUS.
- Inference is deterministic.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Unit tests on synthetic fixtures (blurred, dark, cropped-FOV, non-fundus); contract conformance; determinism; transform round-trip (canonical to original and back); regression reference outputs stored for a fixed internal image list.

VALIDATION REQUIREMENTS
Internal validation metrics via +netra/+eval only; labelled "internal".

DOCUMENTATION REQUIREMENTS
Model card; preprocessing note in docs/contracts/ if the transform record needs clarification (via decision record); section of PH2_REPORT.md draft.

DEFINITION OF DONE
Preprocessing and IQA served from the registry; baseline comparison recorded; threshold provenance complete; tests pass.

STOP CONDITIONS
- No quality-labelled data is accessible: stop and report; do not fabricate labels.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P1-B — Adaptive enhancement and optic disc / fovea localisation

```text
FRESH-CONTEXT PROMPT PH2-P1-B: Adaptive enhancement and optic disc / fovea localisation

ROLE
Senior computer vision engineer for fundus image enhancement and anatomy localisation, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 1, enhancement and OD/fovea.

OBJECTIVE
Deliver the adaptive enhancement set applied to Borderline images, its effect evaluation, and OD/fovea localisation selected by evidence against a classical baseline.

RELEVANT PRD REQUIREMENTS
ENH-001...005, FR-005, FR-006, SEG-001, SEG-002, CVR-004, MLR-001, MLR-002, MLR-008.

WHAT ALREADY EXISTS
Preprocessing and IQA stages from PH2-P1-A; Phase 1 outputs. Verify.

INPUTS
Borderline cases from internal data; OD/fovea labels (IDRiD localisation data; sizes to be re-verified from the dataset register); Blueprint K.3, K.4.

EXPECTED OUTPUTS
- src/+netra/+enhance/ (I.4) with a documented selection rule based on measured image properties; parameters in configs/default/enhancement.json.
- OD/fovea in src/+netra/+anatomy/ (I.5); artifacts and model card if learned.
- ENH-004 evaluation: verdict change rate on internal Borderline cases; downstream change on paired original/enhanced images (with whichever downstream stages exist; list which).
- Localisation results: distance error raw and normalised using the normaliser fixed in the evaluation protocol.

INTERFACES
Blueprint I.4, I.5, I.14.

DEPENDENCIES
PH2-P1-A.

FILES TO INSPECT
docs/BLUEPRINT.md (I.4, I.5, K.3, K.4), docs/protocols/evaluation_protocol.md, src/+netra/+preprocess/, src/+netra/+iqa/, data_manifests/dataset_register.json.

FILES ALLOWED TO MODIFY
src/+netra/+enhance/, OD/fovea files in src/+netra/+anatomy/ (not vessel files), training/od_fovea/, configs/default/enhancement.json, configs/thresholds/ (your files), configs/models/model_registry.json (your entries), tests for these modules, docs/model_cards/.

FILES NOT TO MODIFY
Vessel segmentation files (Person 2); other persons' stages; contracts.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Always retain the original image; enhancement never runs on a first-pass Ungradable image (validator enforces).
- Log the operations actually applied with parameters and the measured property that triggered each.
- Check whether enhancement increases MA-like false positives if Person 2's MA stage exists; otherwise record as a pending check.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Enhancement unit tests on synthetic fixtures; ENH-005 guard test; OD/fovea contract and determinism tests; regression references.

VALIDATION REQUIREMENTS
Internal results via +netra/+eval, labelled internal.

DOCUMENTATION REQUIREMENTS
Enhancement method note; model card for OD/fovea; PH2_REPORT.md section.

DEFINITION OF DONE
Both stages in the registry; ENH-004 evaluation recorded; baseline comparison for OD/fovea recorded.

STOP CONDITIONS
- OD/fovea label counts in the register disagree with files on disk: stop and report.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P2-A — Vessel segmentation and microaneurysm detection

```text
FRESH-CONTEXT PROMPT PH2-P2-A: Vessel segmentation and microaneurysm detection

ROLE
Senior computer vision engineer for retinal segmentation and small-lesion detection, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 2, vessels and microaneurysms, plus shared tiling infrastructure.

OBJECTIVE
Deliver vessel segmentation and MA detection (at a resolution where MAs remain resolvable), each selected against a classical baseline, plus reusable tiling/patch infrastructure for all segmentation tasks.

RELEVANT PRD REQUIREMENTS
SEG-003, SEG-004, CVR-002, CVR-003, FR-006, FR-007, SEG-010, DAT-008, DAT-009, MLR-001, MLR-002, MLR-007, MLR-008, OQ-04.

WHAT ALREADY EXISTS
Preprocessing (PH2-P1-A); Phase 1 outputs; decision record for OQ-04 (or a provisional interpretation). Verify all.

INPUTS
DRIVE vessel masks; IDRiD and DDR MA masks via the datastore API; Blueprint K.5, K.6.

EXPECTED OUTPUTS
- Tiling infrastructure (tile extraction with overlap, stitching back to canonical space) with tests.
- Vessel files in src/+netra/+anatomy/ (I.5 vessel fields); MA in src/+netra/+lesions/ (I.6 ma).
- training/vessels/, training/ma/ with experiment configs; artifacts per I.14; model cards.
- Internal results: vessels (Dice, IoU, sensitivity); MA (lesion-level sensitivity vs false positives per image, Dice secondary, centroid localisation error in pixels at native resolution per CVR-003).
- Resolution study: MA recall at candidate resolutions, justifying the chosen one (CVR-002).

INTERFACES
Blueprint I.2, I.5, I.6, I.14.

DEPENDENCIES
PH2-P1-A preprocessing; OQ-04 decision.

FILES TO INSPECT
docs/BLUEPRINT.md (I.2, I.5, I.6, K.5, K.6), docs/decisions/ (OQ-04), docs/protocols/evaluation_protocol.md, src/+netra/+preprocess/, src/+netra/+data/.

FILES ALLOWED TO MODIFY
Vessel files in src/+netra/+anatomy/, src/+netra/+lesions/ (MA and shared tiling), training/vessels/, training/ma/, configs for these modules, registry entries, their tests, model cards.

FILES NOT TO MODIFY
OD/fovea files (Person 1); grading; contracts.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Official test partitions (where defined) are used for testing only; model selection on validation carved from training data.
- Do not claim "sub-pixel" detection unless the OQ-04 decision defines it and your method meets that definition.
- Document class-imbalance handling for MA.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Tiling round-trip test (tile then stitch reproduces the input); contract conformance; determinism; regression references.

VALIDATION REQUIREMENTS
Internal metrics via +netra/+eval, per class, labelled internal.

DOCUMENTATION REQUIREMENTS
Model cards; resolution study; PH2_REPORT.md section.

DEFINITION OF DONE
Both stages in registry at L1; baseline comparisons recorded; tests pass.

STOP CONDITIONS
- OQ-04 has neither a decision nor a provisional interpretation recorded.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P2-B — Exudates, hemorrhages, soft exudates, neovascularization

```text
FRESH-CONTEXT PROMPT PH2-P2-B: Exudates, hemorrhages, soft exudates, neovascularization

ROLE
Senior computer vision engineer for retinal lesion segmentation, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 2, EX/HE/SE/NV.

OBJECTIVE
Deliver hard exudate segmentation, hemorrhage output per the OQ-05 decision, NV detection at the label level that actually exists with its validation level disclosed, and (L2) soft exudate segmentation.

RELEVANT PRD REQUIREMENTS
SEG-005, SEG-006, SEG-007, SEG-008, SEG-010, SEG-011, FR-007, DAT-008, DAT-012, GRD-007, MLR-001, MLR-002, OQ-05, OQ-16, R-03, DEC-10.

WHAT ALREADY EXISTS
Preprocessing, tiling infrastructure (PH2-P2-A), OD mask/centre (PH2-P1-B) for OD exclusion. Verify.

INPUTS
IDRiD and DDR masks (EX, HE, SE); NV data per the OQ-16 decision; Blueprint K.7, K.8.

EXPECTED OUTPUTS
- src/+netra/+lesions/ stages for ex, he, se, nv (I.6), with nv.validation_level set truthfully.
- training/<lesion>/; artifacts; model cards.
- Internal per-class Dice/IoU; NV sensitivity/specificity at available label level; NV priority threshold (GRD-007) derived on validation with provenance, or null (fail closed) if no NV data.

INTERFACES
Blueprint I.6, I.14.

DEPENDENCIES
PH2-P2-A; PH2-P1-B (OD); OQ-05 and OQ-16 decisions.

FILES TO INSPECT
docs/BLUEPRINT.md (I.6, K.7, K.8), docs/decisions/ (OQ-05, OQ-16), src/+netra/+lesions/, src/+netra/+anatomy/, data_manifests/.

FILES ALLOWED TO MODIFY
src/+netra/+lesions/ (ex, he, se, nv), training for these, their configs/thresholds, registry entries, tests, model cards.

FILES NOT TO MODIFY
MA and tiling code except through a PR to their owner (yourself, but record the change); other persons' areas; contracts.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- DRAC22 must not be used (UW-OCTA modality).
- If hemorrhage type labels do not exist, do not create them; implement what OQ-05 allows and disclose what cannot be validated.
- If NV uses an ICDR-grade-4 proxy, label it image_proxy and document why grade 4 is an imperfect proxy (it also covers vitreous/preretinal hemorrhage).
- Soft exudates may be status "unavailable" at L1.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Contract conformance incl. nv.validation_level; determinism; regression references; OD-exclusion test for exudates.

VALIDATION REQUIREMENTS
Per-class internal metrics via +netra/+eval; no blended pixel-accuracy headline.

DOCUMENTATION REQUIREMENTS
Model cards stating validation level per output; PH2_REPORT.md section.

DEFINITION OF DONE
EX, HE, NV in registry at L1; SE at L1 or documented as L2; disclosures present.

STOP CONDITIONS
- OQ-05 or OQ-16 has no recorded decision or fallback.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P3-A — DR grading, decision rule and operating point

```text
FRESH-CONTEXT PROMPT PH2-P3-A: DR grading, decision rule and operating point

ROLE
Senior deep-learning engineer for medical image classification, working in MATLAB Deep Learning Toolbox.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 3, grading.

OBJECTIVE
Train a MATLAB-native grading baseline, compare candidates on the same split, implement a decision rule guaranteeing referable = (displayed grade >= 2) while honouring a referable operating point chosen on internal validation, and deliver the grading stage.

RELEVANT PRD REQUIREMENTS
GRD-001...006, FR-008, FR-009, MLR-001...010, DAT-007, DAT-011, DEC-12, DEC-13, OQ-02, EVAL-005.

WHAT ALREADY EXISTS
Preprocessing (PH2-P1-A), datastore API, metric library, protocol, OQ-02 decision. Verify.

INPUTS
Grading datasets via datastore (APTOS training split, DDR grading, optionally EyePACS with contamination noted); never original Messidor; Blueprint I.7, K.9.

EXPECTED OUTPUTS
- training/grading/ with experiment configs per candidate; artifacts per I.14 with pretraining corpus recorded.
- src/+netra/+grading/ stage (I.7) with decision rule in config.
- Decision record for the chosen decision rule (Blueprint I.7 proposal or an alternative, with evidence).
- configs/thresholds/referable_operating_point.json derived on internal validation (sensitivity target met with maximum specificity) with provenance.
- Internal results: referable sensitivity/specificity at the operating point, AUROC, AUPRC, QWK, per-class metrics, confusion matrix, macro-F1; comparison table across candidates and baseline.
- Model card.

INTERFACES
Blueprint I.2, I.7, I.14.

DEPENDENCIES
PH2-P1-A; OQ-02 decision; if training outside MATLAB is allowed and used, an import equivalence test (MAT-006) is required.

FILES TO INSPECT
docs/BLUEPRINT.md (I.7, K.0, K.9), docs/decisions/ (OQ-02), docs/protocols/evaluation_protocol.md, src/+netra/+data/, src/+netra/+eval/, src/+netra/+preprocess/.

FILES ALLOWED TO MODIFY
src/+netra/+grading/, training/grading/, configs for grading, configs/thresholds/referable_operating_point.json, registry entries, tests, docs/model_cards/grading.md, docs/decisions/ (new).

FILES NOT TO MODIFY
Other stages; contracts (the decision rule is a config/decision-record matter, not a contract change, unless the payload must change: then STOP).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- The grade-determining model must support Grad-CAM (convolutional feature maps on the decision path), or you must STOP before adopting it.
- Default 0.5 thresholds are not assumed.
- Accuracy is never a headline metric; class imbalance handling is documented.
- Check availability of candidate pretrained networks in the pinned MATLAB release; do not assume.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Class-map integrity (index to grade); consistency test (referable equals grade >= 2 for every output); determinism; contract conformance; regression references; import equivalence if applicable.

VALIDATION REQUIREMENTS
Internal results only, via +netra/+eval, labelled internal. External sets must remain unread.

DOCUMENTATION REQUIREMENTS
Model card; decision record; PH2_REPORT.md section.

DEFINITION OF DONE
Grading stage in registry; baseline comparison recorded; operating point file with provenance; tests pass.

STOP CONDITIONS
- The best candidate cannot support Grad-CAM in MATLAB.
- OQ-02 unresolved and the plan requires external training.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH2-P3-B — Calibration, Grad-CAM, uncertainty candidate, Phase 2 integration run

```text
FRESH-CONTEXT PROMPT PH2-P3-B: Calibration, Grad-CAM, uncertainty candidate, Phase 2 integration run

ROLE
Senior medical-AI engineer for calibration and explainability, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 2: Core Image Intelligence (internal validation only).

CURRENT PERSON/WORKSTREAM
Person 3, calibration, Grad-CAM, uncertainty, and the Phase 2 integration run.

OBJECTIVE
Fit and apply calibration, compute Grad-CAM in MATLAB on the grade-determining model, evaluate an OOD candidate (L2), derive the low-confidence threshold, and run the skeleton orchestrator with all real Phase 2 stages.

RELEVANT PRD REQUIREMENTS
UNC-001...003, UNC-005 (later), FR-010, FR-011, XAI-001, XAI-002, XAI-007, MLR-009, MAT-004, OQ-09, TST-002, TST-004, TST-005.

WHAT ALREADY EXISTS
Grading stage and operating point (PH2-P3-A); all other Phase 2 stages (verify which are in the registry).

INPUTS
Internal validation data; grading artifact; Blueprint I.8, I.9 (OOD field), I.10 (gradcam field), K.10, K.11.

EXPECTED OUTPUTS
- src/+netra/+calibration/ (fit, apply) and calibration file with provenance.
- Grad-CAM in src/+netra/+explain/ producing maps in canonical space with target, layer, model_id.
- OOD candidate evaluated vs max-softmax; adopted only if better (record decision); else status unavailable.
- configs/thresholds/low_confidence.json derived from validation calibration data, or null with explanation.
- Integration run: registry switched to real stages; fixed internal-test image list processed; all CaseRecords validate; no mock status remains.

INTERFACES
Blueprint I.7-I.10, I.14.

DEPENDENCIES
PH2-P3-A; other Phase 2 stages for the integration run.

FILES TO INSPECT
docs/BLUEPRINT.md (F.5, I.7-I.10, K.10, K.11), src/+netra/+grading/, src/+netra/+pipeline/, configs/models/model_registry.json.

FILES ALLOWED TO MODIFY
src/+netra/+calibration/, Grad-CAM files in src/+netra/+explain/, OOD code in src/+netra/+uncertainty/, threshold files you derive, configs/default/pipeline.json (stage registry switch only), tests, docs.

FILES NOT TO MODIFY
Other stages' code; contracts; +pipeline code (report orchestrator bugs to Person 2/Person 1).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Calibration fitted on internal validation only.
- Verify that the Grad-CAM function exists in the pinned MATLAB release before using it.
- Grad-CAM output is described as model attention, not clinical proof.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Calibration apply is monotone and deterministic; Grad-CAM map size/registration test; integration test with gating (no grade for Ungradable) and consistency checks.

VALIDATION REQUIREMENTS
ECE, Brier, reliability diagram on internal validation, before and after calibration.

DOCUMENTATION REQUIREMENTS
Update grading model card; PH2_REPORT.md assembly (Person 3 leads the Phase 2 report).

DEFINITION OF DONE
Calibration, Grad-CAM in registry; OOD decision recorded; integration run passes; Phase 2 report drafted.

STOP CONDITIONS
- Any PS analysis module lacks an L1 stage in the registry at integration time: report which, do not mock it.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P1-A — Orchestrator, case store, audit log, routing engine, error handling

```text
FRESH-CONTEXT PROMPT PH3-P1-A: Orchestrator, case store, audit log, routing engine, error handling

ROLE
Senior backend engineer for MATLAB-based clinical workflow systems.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 1, backend, part A.

OBJECTIVE
Turn the skeleton into the production orchestrator with per-stage timing and explicit failure states, persist cases and an append-only audit log, and route cases to review queues by a configurable policy.

RELEVANT PRD REQUIREMENTS
BE-001...005, FR-015, FR-016, Section 21.1 routing policy, STO-001, STO-004, ERR-001...009, SCL-002, NFR-005, NFR-006, OQ-07.

WHAT ALREADY EXISTS
Phase 2 gate: all stages in the registry; skeleton orchestrator; contracts. Verify.

INPUTS
Blueprint I.1, I.9, I.12, I.16; PRD Sections 21.1, 26, 27, 38.

EXPECTED OUTPUTS
- src/+netra/+pipeline/: orchestrator in BE-001 order; recheck-once logic for Borderline (FR-005); recapture attempts with limit from config (OQ-07 value marked provisional); per-stage timing logs (I.16).
- src/+netra/+storage/: case store rooted at the configured case-store root; append-only audit log.
- src/+netra/+routing/: policy engine reading configs/default/routing.json; default = PRD 21.1 conservative policy; every routing decision logged with reason.
- Error catalogue mapping ERR-001...009 to behaviour.
- docs/contracts/routing_policy.md.

INTERFACES
Blueprint I.1, I.9, I.12, I.16.

DEPENDENCIES
Phase 2 gate.

FILES TO INSPECT
docs/BLUEPRINT.md (G, I), docs/contracts/, src/+netra/+pipeline/, src/+netra/+mock/, configs/.

FILES ALLOWED TO MODIFY
src/+netra/+pipeline/, +storage/, +routing/, configs/default/routing.json, configs/default/pipeline.json, tests/integration/, tests/failure/, docs/contracts/routing_policy.md.

FILES NOT TO MODIFY
Model stages; +explain/; +ui/; +service/ (PH3-P1-B).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- A stage failure never produces partial outputs presented as complete; failed/unavailable stages mark the case incomplete and force mandatory review.
- Audit log cannot be edited through any code path; human decisions never overwrite model outputs.
- Case IDs contain no personal identifiers.
- Routing thresholds come only from configs/thresholds; if null, route to mandatory review.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Failure injection for each ERR scenario (TST-009); gating (TST-004); consistency (TST-005); audit append-only test; routing policy tests per case category; batch run without manual intervention.

VALIDATION REQUIREMENTS
Integration run on a fixed internal-test list; timings logged for every case with host ID.

DOCUMENTATION REQUIREMENTS
Routing policy doc; error catalogue doc; PH3_REPORT.md section (Person 1 leads Phase 3 report).

DEFINITION OF DONE
All tests above pass; timing logs produced; routing documented.

STOP CONDITIONS
- OQ-07 (max recaptures) has no provisional value recorded anywhere: ask the team for one rather than choosing.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P1-B — Authentication and roles, report generation and export, service API

```text
FRESH-CONTEXT PROMPT PH3-P1-B: Authentication and roles, report generation and export, service API

ROLE
Senior backend engineer (MATLAB) for secure clinical applications.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 1, backend, part B.

OBJECTIVE
Implement local authentication with three roles, the deterministic annotated report with export, and the service API the screens call.

RELEVANT PRD REQUIREMENTS
SEC-001...004, SEC-008, FR-013, FR-022, RPT-001...005, OPS-003, UX-002, Blueprint I.11, I.13, BQ-06.

WHAT ALREADY EXISTS
PH3-P1-A orchestrator/storage/routing; Person 2's evidence bundle (PH3-P2-A) may be in progress: check its contract version.

INPUTS
Blueprint I.10, I.11, I.12, I.13; BQ-06 decision on export format.

EXPECTED OUTPUTS
- src/+netra/+auth/: user store created by a setup script that prompts for secrets; salted, iterated password hashing using a primitive available in MATLAB's runtime (document which); sessions with role.
- src/+netra/+report/: deterministic template producing every RPT-002 field, a missing_components list, annotated images, pipeline version and config hash, disclaimer; export in the decided format.
- src/+netra/+service/: every function in Blueprint I.13 with role checks and documented errors.

INTERFACES
Blueprint I.10-I.13.

DEPENDENCIES
PH3-P1-A; PH3-P2-A for evidence content (use the contract; if unavailable, report sections render "evidence unavailable").

FILES TO INSPECT
docs/BLUEPRINT.md (I.10-I.13), docs/contracts/, docs/decisions/ (BQ-06), src/+netra/+pipeline/, +storage/, +explain/.

FILES ALLOWED TO MODIFY
src/+netra/+auth/, +report/, +service/, scripts/setup_users.m, configs/default/auth.json, configs/default/report.json, tests/unit and tests/security for these, docs/contracts/service_api.md.

FILES NOT TO MODIFY
+pipeline/ (except via PR noted), +explain/, +ui/, model stages.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- No credential, default password, or user in the repository or config; secrets entered at setup time only.
- Technician-facing service responses never contain a DR grade (UX-002).
- Report text comes from a template and config text; no generated text.
- If the report export format is undecided (BQ-06), STOP for that part and implement the rest.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Role enforcement per service function; login failure paths; report completeness test (all RPT-002 fields or listed as missing); export test; grep test for credentials.

VALIDATION REQUIREMENTS
Reports generated for gradable, borderline-enhanced, ungradable, and incomplete cases.

DOCUMENTATION REQUIREMENTS
Service API doc; report template doc; security notes (prototype-grade, not production hardening).

DEFINITION OF DONE
Service API complete and tested; reports complete; auth enforced.

STOP CONDITIONS
- A service function needed by the screens is not in Blueprint I.13: stop and propose it via decision record.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P2-A — Explainability layer and uncertainty flags (evidence bundle)

```text
FRESH-CONTEXT PROMPT PH3-P2-A: Explainability layer and uncertainty flags (evidence bundle)

ROLE
Senior medical computer vision engineer for explainable AI, working in MATLAB.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 2, explainability layer.

OBJECTIVE
Build the evidence bundle: registered overlays, lesion summary by location relative to OD/fovea, the clinical-criteria panel, heatmap-lesion agreement metrics and flag, disclaimer, and the uncertainty flag rules.

RELEVANT PRD REQUIREMENTS
FR-012, FR-021, FR-009 (inconsistency), XAI-003, XAI-004, XAI-005 (computation), XAI-007, XAI-008, GRD-007, CVR-004, UX-003, UX-004, SEG-011.

WHAT ALREADY EXISTS
Phase 2 stages including Grad-CAM, calibration, OOD decision; contracts I.9, I.10. Verify.

INPUTS
Stage outputs; the ICDR criteria definitions from the primary ICDR publication (the human must supply the citation and text; you may not have internet access).

EXPECTED OUTPUTS
- src/+netra/+explain/: overlay renderer (canonical space), lesion summary (zone/quadrant definition documented), criteria-panel builder reading configs/default/icdr_criteria.json, agreement metrics and low-agreement flag.
- configs/default/icdr_criteria.json with a citation field; criteria the system cannot assess (e.g., venous beading if not modelled) marked cannot_assess.
- src/+netra/+uncertainty/ flag rules (inconsistent evidence, NV priority, low confidence, OOD, incomplete) documented in docs/contracts/uncertainty_flags.md.
- Evidence bundle conforming to I.10.

INTERFACES
Blueprint I.5, I.6, I.8, I.9, I.10.

DEPENDENCIES
Phase 2 gate; ICDR source from the human.

FILES TO INSPECT
docs/BLUEPRINT.md (I.5-I.10, K.11), docs/contracts/, src/+netra/+explain/ (Grad-CAM from Phase 2), src/+netra/+uncertainty/, src/+netra/+lesions/, src/+netra/+anatomy/.

FILES ALLOWED TO MODIFY
src/+netra/+explain/ (except Grad-CAM computation, which is Person 3's; call it), src/+netra/+uncertainty/ (flag rules), configs/default/icdr_criteria.json, configs/default/uncertainty.json, tests for these, docs/contracts/uncertainty_flags.md, docs/contracts/evidence_bundle.md.

FILES NOT TO MODIFY
Model stages; +report/; +ui/; Grad-CAM computation.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Every criteria-panel entry is traceable to a cited ICDR definition; no criterion text is invented.
- Outputs with validation_level other than pixel are labelled accordingly (SEG-011).
- Colour is never the only carrier of meaning: every overlay and flag has a text label.
- Inconsistency rules are explicit, configurable, and each has a documented clinical rationale or is marked [NEEDS VERIFICATION] for clinical-advisor review.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Overlay registration test (known synthetic lesion lands at the right canonical coordinates); criteria-panel tests per grade; flag rule tests; evidence bundle contract tests including missing-component cases.

VALIDATION REQUIREMENTS
Agreement metrics computed on internal images with lesion masks (internal only).

DOCUMENTATION REQUIREMENTS
Evidence bundle doc; criteria mapping with citation; flag rules doc.

DEFINITION OF DONE
Evidence bundle produced for every graded case; all tests pass; citation present.

STOP CONDITIONS
- The ICDR primary source has not been provided: stop the criteria panel part.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P2-B — Simulink telemedicine pipeline model and M/M/c validation

```text
FRESH-CONTEXT PROMPT PH3-P2-B: Simulink telemedicine pipeline model and M/M/c validation

ROLE
Senior MATLAB/Simulink engineer for discrete-event and queuing models.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 2, Simulink structure.

OBJECTIVE
Build the Simulink model of the district telemedicine pipeline, parameterised entirely from configuration, producing the SIM-005 outputs, and validate it against the analytical M/M/c queue.

RELEVANT PRD REQUIREMENTS
SIM-001...006, SIM-010, SIM-011, SIM-012, FR-017, DEC-04, DEC-15, R-10, TST-010.

WHAT ALREADY EXISTS
Licence decision on SimEvents from Phase 1 (docs/decisions/). Verify; if absent, STOP.

INPUTS
Blueprint I.16, I.17; PRD Sections 30, 31.

EXPECTED OUTPUTS
- simulink/models/ model: arrival, capture with recapture loop, upload over constrained bandwidth, IQA/enhancement, AI processing, routing, review queue, outcome.
- simulink/params/: builder reading configs/simulation/*.json; each parameter carries a source tag.
- configs/simulation/provisional.json: [MOCK — TEMPORARY ONLY] provisional values, every one tagged [PARAMETER TO BE DETERMINED]; replaced in Phase 4.
- simulink/validation/: M/M/c scenario comparing simulated vs analytical mean wait and utilisation; discrepancies explained.
- Output files carrying the parameter set, source tags, seed, and SIM-005 metrics.

INTERFACES
Blueprint I.16, I.17.

DEPENDENCIES
SimEvents licence decision; none on ML.

FILES TO INSPECT
docs/BLUEPRINT.md (I.16, I.17), docs/decisions/ (SimEvents), docs/prd/SIH26038_Final_PRD.md (30, 31), simulink/, configs/simulation/.

FILES ALLOWED TO MODIFY
simulink/, configs/simulation/, tests/simulation/, docs/simulation/.

FILES NOT TO MODIFY
Everything outside the above.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- No ML in the simulation.
- No parameter value inside the model file; all from config.
- The PRD's illustrative sweep ranges (Section 31) are not facts; keep them tagged [PARAMETER TO BE DETERMINED].
- Runs are seeded and stored with full parameters.
- If SimEvents is unavailable, use the fallback approach recorded in the decision (e.g., Simulink with Stateflow queue logic) and document its limits.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
M/M/c agreement within a tolerance stated and justified in the validation doc; parameter validation rejects invalid inputs (ERR-008); same seed reproduces identical outputs.

VALIDATION REQUIREMENTS
Validation report with analytical formulas cited and results compared.

DOCUMENTATION REQUIREMENTS
docs/simulation/model.md (structure, assumptions, parameters and sources), validation report.

DEFINITION OF DONE
Model runs with provisional parameters; M/M/c check passes or discrepancies are explained; outputs contain all SIM-005 metrics.

STOP CONDITIONS
- No SimEvents licence decision recorded.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P3-A — UI foundation and technician screens (SCR-01, SCR-02)

```text
FRESH-CONTEXT PROMPT PH3-P3-A: UI foundation and technician screens (SCR-01, SCR-02)

ROLE
Senior MATLAB UI engineer for clinical field applications.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 3, screens, part A.

OBJECTIVE
Build the programmatic UI foundation (uifigure-based classes in .m files, per the blueprint decision; confirm BQ-08) and the technician screens: upload and quality verdict with reasons, guidance, retake flow.

RELEVANT PRD REQUIREMENTS
FR-001, FR-004, UX-002, UX-003, UX-004, NFR-001, ERR-001, ERR-002, ERR-003, ERR-007, ERR-009, SCR-01, SCR-02.

WHAT ALREADY EXISTS
Service API (PH3-P1-B) may be partial; check docs/contracts/service_api.md.

INPUTS
Blueprint I.13, I.18; guidance text keys from configs/default/iqa.json.

EXPECTED OUTPUTS
- src/+netra/+ui/: app shell (login, role-based navigation), SCR-01, SCR-02.
- If the service API is not yet available: [MOCK — TEMPORARY ONLY] UI fixture case records under tests/fixtures/ui/ that validate against contracts, with every stage status "mock" and no grades, probabilities, or lesions; removed before the Phase 3 integration test.

INTERFACES
Blueprint I.13 (calls only +netra/+service), I.18.

DEPENDENCIES
PH3-P1-B.

FILES TO INSPECT
docs/BLUEPRINT.md (C, I.13, I.18, G.6), docs/contracts/service_api.md, src/+netra/+service/, configs/default/ui.json.

FILES ALLOWED TO MODIFY
src/+netra/+ui/ (shell, SCR-01, SCR-02), configs/default/ui.json, tests/ui/, tests/fixtures/ui/.

FILES NOT TO MODIFY
+service/, +pipeline/, model stages.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- UI contains no business logic; all actions go through +service.
- Technician screens never show a DR grade.
- All user-facing strings come from config.
- Every flag/status has text, not colour alone.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
matlab.uitest tests: upload success, invalid file error, verdict display for each verdict type, retake flow up to the configured limit, service-unavailable state.

VALIDATION REQUIREMENTS
Walk-through with each ERR scenario relevant to technicians.

DOCUMENTATION REQUIREMENTS
Technician workflow guide (docs/workflows/technician.md).

DEFINITION OF DONE
SCR-01/02 working against the real service API; mocks removed or listed with removal deadline.

STOP CONDITIONS
- A needed service function is missing from the contract.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH3-P3-B — Review queue, review workstation, report view, review timing, proxy pilot

```text
FRESH-CONTEXT PROMPT PH3-P3-B: Review queue, review workstation, report view, review timing, proxy pilot

ROLE
Senior MATLAB UI engineer for clinician decision-support interfaces.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 3: Clinical Workflow Product.

CURRENT PERSON/WORKSTREAM
Person 3, screens, part B.

OBJECTIVE
Build SCR-05 (priority queue), SCR-03 (single-screen review with every UX-001 element and confirm/override), SCR-04 (report view/export), automatic review timing, and run a disclosed proxy pilot with the team to find UI bottlenecks.

RELEVANT PRD REQUIREMENTS
FR-014, FR-015, UX-001, UX-003, UX-004, UX-005, UNC-004, XAI-007, PS-17, PERF-003 (measurement mechanism only), BQ-05.

WHAT ALREADY EXISTS
UI shell (PH3-P3-A), service API (PH3-P1-B), evidence bundle (PH3-P2-A). Verify.

INPUTS
Blueprint I.10, I.12, I.13, I.18; target display specification (BQ-05; if undecided, document the display used and mark it).

EXPECTED OUTPUTS
- src/+netra/+ui/: SCR-05, SCR-03 (original/enhanced toggle, Grad-CAM, lesion overlay toggles, grade, referable flag, calibrated confidence with plain-language wording from config, flags, criteria panel, quality verdict, disclaimer, confirm/override with required reason, "explanation not useful" flag), SCR-04.
- Timer from case open to decision stored in the decision record.
- docs/results/pilot_review_proxy.md: pilot with team members as proxies, clearly labelled "proxy — not a PERF-003 result".

INTERFACES
Blueprint I.10, I.12, I.13, I.18.

DEPENDENCIES
PH3-P1-B, PH3-P2-A.

FILES TO INSPECT
docs/BLUEPRINT.md (G, I.10-I.13, I.18), docs/contracts/, src/+netra/+ui/, src/+netra/+service/.

FILES ALLOWED TO MODIFY
src/+netra/+ui/ (SCR-03, 04, 05), configs/default/ui.json, tests/ui/, docs/workflows/ophthalmologist.md, docs/results/pilot_review_proxy.md.

FILES NOT TO MODIFY
+service/, +explain/, +report/, model stages.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- All UX-001 elements visible without scrolling on the documented display.
- Missing components render "evidence unavailable: <component>", never a blank overlay.
- Override requires a reason; decision goes through recordDecision.
- The disclaimer that heatmaps show model attention is always visible with Grad-CAM.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
UI tests: element presence on the documented display size, missing-evidence rendering, override validation, timer start/stop, role restrictions.

VALIDATION REQUIREMENTS
Pilot results reported as proxy with median, P90, max, n.

DOCUMENTATION REQUIREMENTS
Ophthalmologist workflow guide; pilot note.

DEFINITION OF DONE
SCR-03/04/05 working end-to-end with real data; timing recorded; pilot documented.

STOP CONDITIONS
- UX-001 cannot fit on the documented display: stop and propose layout options rather than dropping elements.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P1-A — Freeze, timing benchmark, mock purge, dependency and security audit

```text
FRESH-CONTEXT PROMPT PH4-P1-A: Freeze, timing benchmark, mock purge, dependency and security audit

ROLE
Senior release and QA engineer for MATLAB systems.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System.

CURRENT PERSON/WORKSTREAM
Person 1, release, part A. This work runs first in Phase 4; others depend on the freeze.

OBJECTIVE
Freeze the system reproducibly, produce the timing benchmark on the documented demo host, remove all mocks from the release, and prove no external AI calls, no hardcoded paths/credentials/thresholds, and correct security behaviour.

RELEVANT PRD REQUIREMENTS
MLR-003, EVAL-005, BE-003, DEP-002, PERF-005, TST-011, AC-019, FR-019, FR-020, SEC-001...004, NFR-010, OPS-001...004.

WHAT ALREADY EXISTS
Phase 3 gate outputs. Verify.

INPUTS
Current main branch; all configs; registry; host hardware (documented by the human).

EXPECTED OUTPUTS
- Freeze manifest (commit, config hash, registry checksums, threshold files, split hashes) and tag v1.0-rc (the human creates the tag).
- Timing benchmark: per-stage and end-to-end distributions on a fixed internal image list on the documented host, in the I.16 format.
- Mock purge: release config resolves no +netra/+mock function; test proving no stage can return status "mock".
- scripts/audit/: dependency audit (search for network/web calls and external AI endpoints in code paths), hardcoding audit (absolute paths, credential-like strings, numeric thresholds in code), security checks.
- docs/results/audit_report.md.

INTERFACES
Blueprint I.14, I.15, I.16.

DEPENDENCIES
Phase 3 gate.

FILES TO INSPECT
Entire repository (read-only first pass), docs/BLUEPRINT.md (H, L, O).

FILES ALLOWED TO MODIFY
scripts/audit/, scripts/benchmark/, docs/results/audit_report.md, docs/results/timing_benchmark.md, configs/release/ (new release profile), tests/security/, tests/perf/, removal of +netra/+mock usage from release config.

FILES NOT TO MODIFY
Model artifacts, thresholds, model code (any finding goes to its owner; changes after freeze trigger re-evaluation rules).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Any audit finding that requires changing code/config after the freeze is reported, not silently fixed; the fix must go through the owner and re-freeze.
- Benchmark reports distributions and host details; no single-number claims.
- Run the demo path with the network disconnected (NFR-010) and record the result.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Full test ladder (Blueprint O step 4) up to security and dependency audit; results recorded.

VALIDATION REQUIREMENTS
Freeze manifest re-computed on a second checkout matches.

DOCUMENTATION REQUIREMENTS
Audit report; timing benchmark; freeze manifest doc.

DEFINITION OF DONE
Freeze manifest exists; audits clean or findings resolved via re-freeze; benchmark delivered to Person 2.

STOP CONDITIONS
- Any external AI/LLM/inference call is found: blocker, stop and report.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P1-B — Packaging, setup guide, final integration, demo runner, final report

```text
FRESH-CONTEXT PROMPT PH4-P1-B: Packaging, setup guide, final integration, demo runner, final report

ROLE
Senior deployment engineer and technical lead for final integration.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System.

CURRENT PERSON/WORKSTREAM
Person 1, release, part B.

OBJECTIVE
Package the frozen system for the single documented demo host, write a setup guide reproduced on a clean machine, run final integration, build the demo runner with pre-registered case selection, and assemble the final report and toolbox usage map.

RELEVANT PRD REQUIREMENTS
DEP-001...005, AC-020, SEC-008, MAT-003, NFR-009, Section 12.3 demo scope, Blueprint O and P.

WHAT ALREADY EXISTS
Freeze and audits (PH4-P1-A); results from Person 2 and Person 3 (may be in progress).

INPUTS
Freeze manifest; DEP-004 packaging decision (record it if missing: MATLAB app, compiled app, or run from MATLAB); results in docs/results/.

EXPECTED OUTPUTS
- Packaging per the decision; docs/SETUP.md verified on a clean machine (record deviations).
- scripts/demo/: demo runner that loads pre-selected case IDs from docs/demo/case_selection.md.
- docs/demo/case_selection.md: four cases selected by ground-truth labels before running the system, with selection time.
- docs/TOOLBOX_MAP.md: where each PS toolbox is genuinely used.
- docs/phases/FINAL_REPORT.md assembling all phase reports and results with honest-reporting checklist.

INTERFACES
All.

DEPENDENCIES
PH4-P1-A; PH4-P2-A/B and PH4-P3-A/B results for the final report.

FILES TO INSPECT
docs/BLUEPRINT.md (H, O, P), docs/phases/, docs/results/, docs/decisions/.

FILES ALLOWED TO MODIFY
Packaging files, scripts/demo/, docs/SETUP.md, docs/demo/, docs/TOOLBOX_MAP.md, docs/phases/FINAL_REPORT.md.

FILES NOT TO MODIFY
Frozen code, configs, artifacts; results files (only cite them).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Demo uses only public-dataset held-out images labelled on screen as test data; shows whatever the system outputs.
- Final report copies numbers from docs/results/ with run IDs; never retypes or rounds differently from the source without saying so.
- Unmet targets are reported as unmet with likely causes.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
E2E demo run on the packaged build; offline run; clean-machine setup.

VALIDATION REQUIREMENTS
Each PRD acceptance criterion AC-001...AC-021 has a recorded status in the final report.

DOCUMENTATION REQUIREMENTS
As outputs.

DEFINITION OF DONE
Gate 4 checklist items owned by Person 1 signed.

STOP CONDITIONS
- A results file needed by the final report is missing: list it; do not fill it.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P2-A — Simulation parameterisation, scenarios, optimisation

```text
FRESH-CONTEXT PROMPT PH4-P2-A: Simulation parameterisation, scenarios, optimisation

ROLE
Senior operations-research and Simulink engineer for public-health resource planning.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System.

CURRENT PERSON/WORKSTREAM
Person 2, simulation, part A.

OBJECTIVE
Replace provisional simulation parameters with measured values, run the 100,000/year baseline and all SIM-006 sweeps showing upload-, AI-, and review-bound regimes, and optimise resource allocation under the OQ-11 objective and constraints, reporting ranges.

RELEVANT PRD REQUIREMENTS
SIM-003...012, FR-018, PERF-004, SCL-001, Section 21.1 (policy comparison simulation-only), OQ-11, A-05.

WHAT ALREADY EXISTS
Validated Simulink model (PH3-P2-B); timing benchmark (PH4-P1-A); timed-review results (PH4-P3-B; may arrive later: run with provisional review times first, then re-run).

INPUTS
docs/results/timing_benchmark.md; docs/results/timed_review.md; OQ-11 decision; measured recapture and mandatory-review fractions from internal data.

EXPECTED OUTPUTS
- configs/simulation/measured.json: each parameter with value/distribution and source tag (measured, sourced with citation, or [PARAMETER TO BE DETERMINED]).
- Scenario outputs for baseline and sweeps; bottleneck regime identification.
- Optimisation per the recorded method (SIM-009 decision) with sensitivity ranges to uncertain parameters.
- Visualisations (SIM-012); routing-policy comparison labelled "simulated".
- docs/results/simulation.md.

INTERFACES
Blueprint I.16, I.17.

DEPENDENCIES
PH4-P1-A benchmark; PH4-P3-B review times; OQ-11.

FILES TO INSPECT
docs/BLUEPRINT.md (I.16, I.17, H), docs/simulation/, docs/decisions/ (OQ-11, SIM-009), simulink/, configs/simulation/, docs/results/.

FILES ALLOWED TO MODIFY
configs/simulation/, simulink/optimisation/, simulink/params/, docs/results/simulation.md, tests/simulation/.

FILES NOT TO MODIFY
Frozen pipeline code/configs; simulink/models/ structure (unless a defect is found: report it first).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Every output lists which parameters are measured and which are still provisional.
- Workload-reduction results are labelled "simulated".
- Report ranges, not single points, for the recommended configuration.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Re-run M/M/c validation with measured parameters where applicable; seeded reproducibility; parameter validation.

VALIDATION REQUIREMENTS
Sanity check: baseline utilisation consistent with arithmetic (arrival rate vs capacity) per resource.

DOCUMENTATION REQUIREMENTS
Simulation results doc with parameter source table.

DEFINITION OF DONE
Baseline + sweeps + optimisation complete; AC-016 and AC-017 statuses recorded.

STOP CONDITIONS
- OQ-11 has no recorded objective/constraints.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P2-B — Simulation and optimisation console (SCR-06)

```text
FRESH-CONTEXT PROMPT PH4-P2-B: Simulation and optimisation console (SCR-06)

ROLE
Senior MATLAB UI engineer for planning dashboards.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System.

CURRENT PERSON/WORKSTREAM
Person 2, simulation, part B.

OBJECTIVE
Build SCR-06 for the administrator: choose or edit parameter sets, validate them, run scenarios and optimisation, compare runs, view SIM-012 visualisations, and export results.

RELEVANT PRD REQUIREMENTS
SCR-06, FR-017, FR-018, FR-022, ERR-008, SIM-012, SEC-001, UX-004.

WHAT ALREADY EXISTS
Service functions runScenario and runOptimisation (check +service; if missing, coordinate with Person 1 via decision record); simulation from PH4-P2-A; UI shell.

INPUTS
Blueprint I.13, I.17, I.18.

EXPECTED OUTPUTS
- src/+netra/+ui/ SCR-06 (administrator role only); parameter editor showing each parameter's source tag; run comparison; export.

INTERFACES
Blueprint I.13, I.17, I.18.

DEPENDENCIES
PH4-P2-A; UI shell from Phase 3.

FILES TO INSPECT
docs/BLUEPRINT.md (I.13, I.17, I.18), src/+netra/+ui/, src/+netra/+service/, simulink/params/.

FILES ALLOWED TO MODIFY
SCR-06 files in src/+netra/+ui/, configs/default/ui.json (SCR-06 keys), tests/ui/scr06.

FILES NOT TO MODIFY
Other screens; +service/ (request changes from Person 1); simulink/models/.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Provisional parameters are visibly marked in the UI and in exports.
- Invalid parameters are rejected with specific messages (ERR-008).

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
UI tests: role restriction, invalid parameter rejection, run and export.

VALIDATION REQUIREMENTS
Console reproduces a stored scenario result exactly (same seed).

DOCUMENTATION REQUIREMENTS
Administrator workflow guide.

DEFINITION OF DONE
SCR-06 usable in the demo flow step 9.

STOP CONDITIONS
- Service functions for simulation are absent and no decision record exists.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P3-A — External evaluation, ablation, benchmark comparison, calibration, explanation overlap

```text
FRESH-CONTEXT PROMPT PH4-P3-A: External evaluation, ablation, benchmark comparison, calibration, explanation overlap

ROLE
Senior medical-AI evaluation scientist.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System. This is the ONLY workstream permitted to read sealed external test sets, and only after the freeze.

CURRENT PERSON/WORKSTREAM
Person 3, validation, part A.

OBJECTIVE
Run the pre-registered evaluation protocol once on the frozen system: external results with CIs, ablation, published-benchmark comparison, calibration per set, and heatmap-lesion overlap; report unmet targets as unmet.

RELEVANT PRD REQUIREMENTS
EVAL-001...012, PERF-001, PERF-002, PERF-006...009, UNC-005, XAI-005, DAT-014, MLR-005, NFR-009, AC-014, AC-015, R-01, R-12.

WHAT ALREADY EXISTS
Freeze manifest and tag v1.0-rc (PH4-P1-A); evaluation protocol (Phase 1, possibly amended before freeze via decision records). Verify both; the protocol version used must predate the freeze.

INPUTS
Sealed external sets via the datastore unlock (configured through the config system with the freeze manifest); published benchmark numbers supplied by the human with full citations.

EXPECTED OUTPUTS
- docs/results/external_evaluation.md: per dataset — QWK, referable sensitivity/specificity with CIs (point estimate is the PS comparison, strict ">"), AUROC, AUPRC, macro-F1, ECE, Brier; dataset, camera, population, domain note, contamination status.
- docs/results/ablation.md (pre-registered variants only, each run once).
- docs/results/benchmark_comparison.md with protocol differences stated.
- docs/results/xai_overlap.md (sets with lesion masks).
- Run IDs linking every number to the freeze manifest.

INTERFACES
Blueprint K.12, K.13.

DEPENDENCIES
PH4-P1-A freeze.

FILES TO INSPECT
docs/protocols/evaluation_protocol.md, docs/results/, docs/decisions/, data_manifests/contamination_registry.json, freeze manifest.

FILES ALLOWED TO MODIFY
evaluation/, docs/results/ (the files above), tests/ml/eval_runs/.

FILES NOT TO MODIFY
Any code, config, threshold, or artifact of the frozen system.

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Operating point and calibration are not changed after seeing external data. If any change is made, re-run and report both results.
- Benchmark numbers come only from citations the human supplies; never recall them from memory.
- Models initialised from a corpus overlapping an evaluation set: that set is not reported as independent.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Harness tests on synthetic data before touching external sets; verify loaded counts match the register.

VALIDATION REQUIREMENTS
A second person re-runs one external result from its run ID and gets the same numbers.

DOCUMENTATION REQUIREMENTS
Results files; error analysis handoff to PH4-P3-B.

DEFINITION OF DONE
All protocol analyses run once and documented; AC-014, AC-015 statuses recorded.

STOP CONDITIONS
- No freeze manifest, or the protocol was modified after the freeze.
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```

### PH4-P3-B — Timed review test, clinician rating study, error analysis, results dossier

```text
FRESH-CONTEXT PROMPT PH4-P3-B: Timed review test, clinician rating study, error analysis, results dossier

ROLE
Clinical-study coordinator and medical-AI evaluation scientist.

PROJECT CONTEXT
You are working on NETRA-DR, the team's solution to Smart India Hackathon problem SIH26038 (sponsor: MathWorks): an explainable-AI diabetic retinopathy (DR) screening pipeline for rural India. Three engineers (Person 1, Person 2, Person 3) build it in four sequential phases; each phase has work for all three people and ends with a formal gate. You are a fresh session working on ONE workstream. You have no memory of earlier sessions: everything you need is in this prompt or in the repository. A decision exists only if it is written in the repository.

Authoritative documents in the repository (read those listed under FILES TO INSPECT; if one is missing, STOP and say so):
- docs/prd/SIH26038_Final_PRD.md: requirements, single source of truth. IDs such as FR-003, SEG-004, MLR-003 refer to it.
- docs/BLUEPRINT.md: phases, ownership, interface contracts (Section I), data pipeline (J), ML pipeline (K), testing (L), Git workflow (M).
- docs/context/PROJECT_CONTEXT.md: one-page current-state summary.
- docs/contracts/: versioned interface contracts.
- docs/decisions/: decision records.

Hard project constraints: MATLAB runtime pipeline (PS-01); MATLAB package namespace +netra under src/; configuration separate from logic; reproducible (fixed seeds, pinned versions, data manifests, config hashes); external test sets are sealed until Phase 4 and used once after the system is frozen (MLR-003).

PROBLEM STATEMENT
Build a MATLAB-based retinal image analysis pipeline that: checks fundus image adequacy (focus, illumination, field of view) and gives recapture feedback; enhances borderline images (CLAHE, illumination normalisation, denoising); localises optic disc and fovea, segments vessels, detects microaneurysms, segments exudates, classifies hemorrhages, detects neovascularization; grades DR on the ICDR 0-4 scale and flags referable DR (grade >= 2) targeting sensitivity >90% and specificity >85%; provides Grad-CAM maps, lesion evidence mapped to clinical criteria, calibrated confidence and annotated reports so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop); and models district telemedicine resources in Simulink to optimise allocation for 100,000+ patients per year. The product is a screening/triage aid: no clinical-validation, regulatory, or diagnostic claim is made.

CURRENT PHASE
Phase 4: Validation, District Simulation and Final System.

CURRENT PERSON/WORKSTREAM
Person 3, validation, part B.

OBJECTIVE
Run the timed review test and the clinician usefulness rating study exactly per their protocols on the frozen system, perform error analysis, and assemble the results dossier.

RELEVANT PRD REQUIREMENTS
TST-008, PERF-003, AC-018, AC-021, XAI-006, EVAL-009, EVAL-010, EVAL-012, OQ-06, OQ-13, R-05, SEC-004.

WHAT ALREADY EXISTS
Protocols in docs/protocols/ (timed review, rating study) approved at Gate 3; frozen system; external results (PH4-P3-A).

INPUTS
Participants (ophthalmologists preferred; proxies disclosed as proxies); fixed case set defined in the protocol.

EXPECTED OUTPUTS
- docs/results/timed_review.md: participant profile (role, not identity), n, median, P90, max, the pre-stated pass statistic, pass/fail.
- docs/results/rating_study.md: scale, cases, raters, summary statistics, limitations.
- docs/results/error_analysis.md: confusion matrix, individual review of false-negative referable cases, failure categories.
- docs/results/README.md dossier index with honest-reporting checklist.
- Review-time distribution handed to Person 2 (I.17).

INTERFACES
Blueprint I.12 (decision records hold timings), I.17.

DEPENDENCIES
Freeze; participants; PH4-P3-A.

FILES TO INSPECT
docs/protocols/, docs/results/, audit log export from the frozen system.

FILES ALLOWED TO MODIFY
docs/results/ (files above), evaluation/studies/.

FILES NOT TO MODIFY
Frozen system; protocols (a change requires a decision record and disclosure).

IMPLEMENTATION REQUIREMENTS
"Before modifying anything, inspect the existing files relevant to this task."
Then, in order:
1. Inspect the existing implementation.
2. Identify conflicts between this prompt, the contracts, and the code.
3. Identify missing dependencies.
4. Do not overwrite unrelated work.
5. Do not invent missing interfaces: if an interface you need is not in docs/contracts, STOP.
6. Do not create duplicate functionality.
7. Follow existing contracts and code conventions.
8. Run the relevant tests before and after your change.
9. Report exactly what changed.
- Store no participant personal data beyond what they consented to; use pseudonymous IDs.
- Proxy raters/reviewers are always labelled as proxies in every table and slide.
- Report results as found, including failures.

NO-ASSUMPTION RULE
- Do not invent dataset facts (sizes, labels, splits), model performance, thresholds, image sizes, normalisation constants, clinical claims, API URLs, file paths, credentials, hardware specifications, simulation parameters, or evaluation results.
- If something you need is missing or ambiguous: identify it, explain why it matters, say how to verify it, mark it [NEEDS VERIFICATION] or [OPEN QUESTION], and STOP for that item instead of guessing. Never silently choose between conflicting requirements.
- Values you must pick to make progress (e.g., an initial learning rate) go in an experiment config file labelled as an initial choice, never presented as a finding.
- Label statements: [VERIFIED] (checked in this session; cite where), [PS REQUIREMENT], [ENGINEERING DECISION], [NEEDS VERIFICATION], [OPEN QUESTION], [BLOCKER], [MOCK — TEMPORARY ONLY].

NO-HARDCODING RULE
Never hardcode dataset paths, model paths, absolute or machine-specific paths, credentials, API URLs, patient data, predictions, thresholds, hardware assumptions, or evaluation results. Use the project configuration system (+netra/+config, configs/, and the root environment variables defined in docs/contracts; confirm their exact names there before use). Thresholds live in configs/thresholds/ with provenance (value, split it was derived from, run ID, commit, date, method); a null threshold means the dependent stage fails closed. Choose the simplest configuration that works.

NO-EXTERNAL-API RULE
No external AI, LLM, ML-inference, or prediction APIs, and no network calls from any inference or reporting path. Every prediction comes from a model or algorithm implemented and stored in this project. Reports use a deterministic template, never generated text. If a mock is unavoidable, label it [MOCK — TEMPORARY ONLY] and state why it is needed, what it represents, what replaces it, and when it is removed. A mock must never contain a DR grade, probability, lesion result, or patient-like data.

TEST REQUIREMENTS
Analysis scripts tested on synthetic study data first.

VALIDATION REQUIREMENTS
Timing values recomputed from raw decision records match the reported summary.

DOCUMENTATION REQUIREMENTS
As outputs.

DEFINITION OF DONE
AC-018 and AC-021 have recorded statuses; dossier complete; review times delivered to Person 2.

STOP CONDITIONS
- Protocol lacks the pre-stated pass statistic (OQ-13) or rating scale (OQ-06).
Also STOP and ask (do not proceed on a guess) if:
- a file or document listed under FILES TO INSPECT is missing;
- a contract you need does not exist or conflicts with another;
- a decision this task depends on has no decision record;
- completing the task requires modifying a file outside FILES ALLOWED TO MODIFY;
- the task would read sealed external test data (only permitted in PH4-P3-A after freeze);
- tests fail for reasons outside your scope.

FINAL RESPONSE FORMAT
1. Summary (3-5 lines).
2. Files inspected.
3. Files created / modified / deleted (path + one-line purpose each).
4. Contracts: conformed to / changed (any change needs a decision record; name it).
5. Tests: commands run; pass/fail counts before and after.
6. Results produced, each labelled with dataset, split, run ID and "internal" or "external"; or "none".
7. Assumptions, mocks, and [NEEDS VERIFICATION] / [OPEN QUESTION] / [BLOCKER] items.
8. Definition-of-Done checklist, each item marked done / not done.
9. Handoff note: what the next workstream can now use, and how.
```


---

*End of blueprint. Awaiting further instructions; no implementation has been started.*
