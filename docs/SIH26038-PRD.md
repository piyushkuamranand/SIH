# Product Requirements Document
## SIH 26038 — Explainable AI System for Diabetic Retinopathy Screening at Rural/PHC Scale

---

## 1. Document Control

| Field | Value |
|---|---|
| Document | PRD — SIH 26038 |
| Problem ID | SIH26038 |
| Sponsor | MathWorks |
| Theme | MedTech / BioTech / HealthTech (Software) |
| Team size assumed | 3 engineers |
| Status | Draft v1.0 — for technical design handoff |
| Source of truth for PS facts | Official PS page, fetched earlier in this working session — **not re-verified at time of writing this PRD; re-check before final submission** |

**Legend used throughout this document:**
`[PS REQUIREMENT]` — directly stated by the official problem statement.
`[VERIFIED FACT]` — supported by a reliable, checked external source.
`[ENGINEERING DECISION]` — a design choice made by this team.
`[ASSUMPTION]` — not yet verified; treat as provisional.
`[OPEN QUESTION]` — must be resolved before or during implementation.

---

## 2. Executive Summary

**Problem.** `[PS REQUIREMENT]` Rural and PHC-level diabetic retinopathy (DR) screening in India is constrained by scarce ophthalmologist availability, variable-quality fundus imaging (often from portable/handheld cameras), and — per the PS's own framing — a lack of clinically validated, explainable screening tools.

**Proposed product.** A software system (with a MATLAB/Simulink-based deployment-planning component) that: (1) assesses and, where possible, improves the usability of a captured fundus image; (2) segments retinal structures and DR-relevant lesions; (3) grades DR severity on the ICDR 0–4 scale and flags referable cases; (4) produces clinician-checkable explanations (heatmaps, lesion evidence, calibrated confidence, structured report) within a 30-second review budget; and (5) simulates district-scale staffing/equipment/bandwidth needs for 100,000+ patients/year.

**Target users.** PHC technicians (capture/retake), ophthalmologists (review/confirm/override), district health administrators (capacity planning).

**Core capabilities.** Quality gating, structure/lesion segmentation, severity grading with calibrated uncertainty, explainability validated against lesion ground truth (not just displayed), and a queuing-theory-based resource simulation.

**Expected impact.** `[ENGINEERING DECISION — framing]` A screening *aid* that reduces unnecessary referrals and flags likely-referable cases faster than manual triage alone, for use in a supervised (human-in-the-loop) workflow. This PRD makes **no claim of clinical validation or regulatory approval** — see Section 24 and Section 28.

**Major constraints.** No external LLM/inference APIs `[our own project constraint, not PS-stated]`; must use MATLAB/Simulink where justified (`[PS REQUIREMENT]` for named toolboxes, `[ASSUMPTION]` that MATLAB is a strong expectation rather than a confirmed hard grading rule); must hit sensitivity >90% / specificity >85% for referable DR (Grade ≥2) `[PS REQUIREMENT]`; must support <30s ophthalmologist review time per case `[PS REQUIREMENT]`; must scale to 100,000+ patients/year at district level `[PS REQUIREMENT]`.

---

## 3. Problem Definition

### 3.1 PS facts (verbatim scope, as extracted earlier — re-verify before submission)
`[PS REQUIREMENT]`
- Explainable AI system for DR screening, rural/PHC-level deployment, India.
- Must address image-quality variability, produce clinically interpretable outputs, include a deployment-resource simulation.
- Named toolboxes: Image Processing, Computer Vision, Deep Learning, Medical Imaging, Statistics & ML Toolbox, Simulink.
- Numeric targets: sensitivity >90%, specificity >85% (referable DR, Grade ≥2); <30s ophthalmologist review; 100,000+ patients/year district-scale throughput.

### 3.2 Our interpretation (not PS text)
`[ENGINEERING DECISION]`
- "Explainable" is treated as *validated* explainability (attribution evidence checked against real lesion ground truth), not merely a heatmap feature — justified by the PS's own complaint about prior solutions' lack of "clinical validation rigor."
- Portable/handheld camera image quality is treated as the **default** condition, not an edge case, because the PS's rural-PHC framing implies non-ideal capture is normal.
- A recapture/feedback loop is implied by "quality assessment": rejecting a bad image is only actionable if the technician is told what to fix.

### 3.3 Current problem
`[ENGINEERING DECISION — problem framing, not independently verified]` Existing DR-screening prototypes in the literature we reviewed are typically validated only on curated clinic-grade datasets, report accuracy on imbalanced data (masking clinically important sensitivity failures), and treat explainability as a cosmetic add-on rather than a checked property of the model's reasoning.

### 3.4 Why it matters
`[PS REQUIREMENT — implied]` Diabetes-driven vision loss is preventable with timely screening; ophthalmologist scarcity at PHC level is the operational bottleneck the PS is targeting.

### 3.5 Existing limitations (of prior approaches, per our reading list — not independently re-verified in this session)
`[ASSUMPTION]` Domain shift from clinic-grade to portable-camera images is untested in the papers we reviewed; inter-grader disagreement (a `[VERIFIED FACT]` — documented in DR-grading literature) is often not acknowledged as a source of "model error."

### 3.6 Target environment
`[ENGINEERING DECISION, inferred from PS]` Low-bandwidth, low-connectivity rural PHCs; likely split edge-capture / district-server-inference architecture. The PS does not mandate a specific topology — this is our inference, not a stated requirement.

### 3.7 Target users / operational context
See Section 7 (Personas).

---

## 4. Product Vision

```
INPUT                         PROCESS                                    OUTPUT
─────                         ───────                                    ──────
Fundus photo            →     Quality gate → (retake if rejected)   →    Usable image or
(portable/handheld,           Enhancement (conditional)                  structured rejection
variable quality)             Structure/lesion segmentation               feedback
                               Severity grading (0–4 + referable flag)
                               Uncertainty estimation
                               Explainability generation + validation
                                                                     →    Grade, confidence,
                                                                           lesion evidence,
                                                                           structured report,
                                                                           referral flag
                                                                     →    (district level)
                                                                           Resource-planning
                                                                           simulation output
```

**Complete user journey.** Technician captures → system gates quality (retake loop if rejected) → system grades + explains → ophthalmologist reviews the evidence in <30s and confirms/overrides → case outcome (and aggregate system load) feeds the district resource simulation used by administrators for planning.

---

## 5. Goals & Objectives

`[ENGINEERING DECISION]`
- G1: Meet PS numeric targets (sensitivity/specificity/latency/throughput) on the held-out validation protocol defined in Section 11.
- G2: Make explainability *falsifiable* — every attribution output has a measurable overlap score against ground-truth lesion masks, not just a rendered image.
- G3: Ship a working Level-1 baseline early (Section 26 — MVP), then layer Level-2/3 differentiation.
- G4: Produce a Simulink simulation grounded in real, benchmarked latency numbers from the team's own trained models, not invented placeholders.

---

## 6. Non-Goals

`[ENGINEERING DECISION]`
- Not building a regulatory-cleared diagnostic device.
- Not fusing OCT or other imaging modalities (scope explicitly narrowed to 2D fundus photography — mirrors a limitation openly flagged in our reading-list papers).
- Not building a full hospital EMR/patient-management system — only the screening workflow and its data footprint.
- Not using external LLM or inference APIs for any module.

---

## 7. Users & Personas

### 7.1 PHC Technician
- **Goals:** capture a usable image quickly, know immediately if a retake is needed and why.
- **Responsibilities:** device operation, patient positioning, initiating capture, acting on the quality-gate verdict.
- **Technical skill level:** `[ASSUMPTION]` variable, not assumed to be clinically trained; UI must not require diagnostic knowledge.
- **Environment:** PHC, possibly low/intermittent connectivity, portable camera hardware.
- **Pain points (inferred from PS framing, not independently surveyed):** `[ASSUMPTION]` uncertainty about whether a capture is good enough; no local feedback loop today.
- **Actions:** capture, review quality verdict, retake, submit.
- **Expected outputs:** accept/reject verdict, specific failure reason (blur / illumination / field-of-view / occlusion) when rejected.
- **Failure scenarios:** repeated rejections with no actionable guidance, device/connectivity failure mid-capture.

### 7.2 Ophthalmologist
- **Goals:** confirm or override the system's grade within the PS's <30s budget.
- **Responsibilities:** final clinical call, especially for low-confidence/uncertain cases routed to mandatory review (Section 16).
- **Information required:** original + enhanced image, segmentation overlay, grade, confidence, lesion evidence, structured report.
- **Review workflow:** view evidence bundle → confirm or override grade → optionally annotate reason for override.
- **Time constraints:** `[PS REQUIREMENT]` <30 seconds per case — this bounds how much content the UI can present, not just how fast the model runs.

### 7.3 District Health Administrator
- **Goals:** plan staffing, device count, and bandwidth for 100,000+ patients/year.
- **Resource/capacity planning:** consumes Module 5 (Simulink) outputs — queue lengths, wait times, required reviewer/device counts.
- **Operational metrics:** throughput, referral rate, review backlog.
- **Simulation requirements:** parameter-driven, range outputs (best/worst case), not single-point estimates (Section 22).

`[ENGINEERING DECISION]` No demographic characteristics are invented for any persona; only role, environment, and task-relevant needs are specified, consistent with PS framing.

---

## 8. User Stories (representative set, with acceptance criteria)

| ID | Story | Acceptance Criteria |
|---|---|---|
| US-01 | As a technician, I want to capture/upload a fundus image, so that it can be screened. | Image accepted in supported format; upload confirmation shown; failure states surfaced (Section 23). |
| US-02 | As a technician, I want an immediate quality verdict, so that I know whether to retake. | Verdict returned before any grading proceeds; verdict is one of gradable/borderline/ungradable. |
| US-03 | As a technician, I want a specific retake reason, so that I can fix the actual problem. | Rejection reason maps to a specific quality-gate failure mode (blur, illumination, FOV, occlusion). |
| US-04 | As the system, I must attempt conditional enhancement on borderline images, so that unnecessary retakes are avoided. | Borderline images are re-scored post-enhancement before a final accept/reject decision. |
| US-05 | As an ophthalmologist, I want to see a DR severity grade and referable flag, so that I can triage. | Grade (0–4) and binary referable flag both shown; binary flag threshold tied to Grade ≥2 `[PS REQUIREMENT]`. |
| US-06 | As an ophthalmologist, I want lesion-level evidence overlaid on the image, so that I can verify the grade quickly. | Segmentation/attribution overlay renders within the same view as the grade; overlap/validation score visible. |
| US-07 | As an ophthalmologist, I want a calibrated confidence score, so that I know when to trust the system more or less. | Confidence value shown; low-confidence cases are visibly flagged for mandatory review (Section 16). |
| US-08 | As an ophthalmologist, I want a structured report, so that I don't have to reconstruct findings manually. | Report includes fields listed in Section 19; generated automatically per case. |
| US-09 | As an administrator, I want to run a resource simulation, so that I can plan staffing/equipment. | Simulation accepts arrival-rate/service-time/bandwidth parameters and returns queue/staffing outputs (Section 22). |
| US-10 | As an administrator, I want best/worst-case ranges, not single numbers, so that I can plan conservatively. | Output includes a range, not a single point estimate. |

`[OPEN QUESTION]` Exact UI copy/wording for retake reasons and report fields — to be finalized with a technically literate (not necessarily clinical) reviewer during design.

---

## 9. End-to-End Workflows

### Workflow A — PHC Screening
```
Technician → capture image → upload → quality gate
   → ungradable → feedback (specific reason) → recapture (loop)
   → borderline → enhancement → re-score
       → still ungradable → feedback → recapture (loop)
       → now gradable → proceed
   → gradable → segmentation → grading → uncertainty check
       → low confidence → mandatory ophthalmologist review (flagged)
       → sufficient confidence → result + explanation delivered, still visible to ophthalmologist for confirmation
   → result + explanation → referral recommendation → (case logged for Module 5 aggregate stats)
```
`[ENGINEERING DECISION]` This flow was validated against, and modified from, the PS's own implied structure: the PS does not mandate a mandatory-review branch, but the <30s review requirement and the "clinical validation rigor" complaint together imply human-in-the-loop confirmation is expected, not optional — so the flow always surfaces the case to the ophthalmologist, with low-confidence cases flagged as higher priority rather than being the *only* cases reviewed.

### Workflow B — Ophthalmologist Review
Shown per case: patient/case ID (de-identified, Section 22), original image, enhanced image (if applied), segmentation overlay, lesion evidence with validation score, DR grade, confidence, referral recommendation, structured report. `[ENGINEERING DECISION]` All of these are shown together in one view specifically to fit the <30s budget — no multi-screen drill-down required to reach a decision.

### Workflow C — District Resource Planning
```
Input parameters (arrival rate, service time, bandwidth, device/reviewer counts)
   → Simulink queuing simulation
   → resource utilization / queue length / wait time curves
   → bottleneck identification
   → staffing/device/bandwidth recommendation (as a range)
```

---

## 10. Product Modules

| # | Module | ML Required? | Purpose |
|---|---|---|---|
| 1 | Image Quality Assessment & Enhancement | Partial — rule-based baseline first, ML only if it measurably wins (Section 12) | Gate + improve usability of captured images |
| 2 | Retinal Structure Segmentation | Yes | Localize structures/lesions pixel-wise |
| 3 | DR Severity Grading | Yes | ICDR 0–4 grade + referable flag |
| 4 | Explainability | Mostly post-hoc, not a separately trained model | Clinician-checkable evidence for the grade |
| 5 | Confidence/Uncertainty | Bundled with Module 3's output | Calibrated confidence, routes low-confidence cases to review |
| 6 | Report Generation | No (engineering decision: deterministic template preferred over a trained generator, for reliability on a hackathon timeline) | Structured, human-readable case summary |
| 7 | User Interface | No | Technician + ophthalmologist + administrator workflows |
| 8 | Backend | No | Orchestration, storage, inference serving |
| 9 | Data Storage | No | Case data, model artifacts, audit logs |
| 10 | Simulink Resource Simulation | No — queuing theory, not ML | District-scale capacity planning |

Each module's detailed purpose/inputs/outputs/dependencies/success criteria/failure states is carried through Sections 12–17 below (Quality, Segmentation, Grading, Explainability, Confidence, Reporting) plus Sections 18–20 (Backend/Frontend/Simulink).

---

## 11. Functional Requirements

Priority basis `[ENGINEERING DECISION — reasoning stated per item]`: **P0** = required to meet an explicit PS numeric target or to make the pipeline function end-to-end; **P1** = materially improves reliability/trust but pipeline still functions without it; **P2** = enhances the product but is deferrable past MVP.

| ID | Requirement | Priority | Source | Acceptance Criteria |
|---|---|---|---|---|
| FR-001 | System shall accept a supported retinal image as input. | P0 | Pipeline entry point | Upload succeeds for defined supported formats; rejects unsupported formats with a clear error. |
| FR-002 | System shall classify image quality as gradable/borderline/ungradable before any grading proceeds. | P0 | PS (image-quality variability requirement) | No grade is ever produced for an ungradable image. |
| FR-003 | System shall provide a specific, actionable rejection reason for ungradable images. | P1 | Our interpretation of "quality assessment" implying feedback | Rejection reason is one of a defined enumerated set, not a generic error. |
| FR-004 | System shall attempt conditional enhancement on borderline images and re-score before finalizing rejection. | P1 | Engineering decision (reduces unnecessary recapture burden) | Borderline images pass through enhancement + re-score exactly once before final verdict. |
| FR-005 | System shall segment optic disc, fovea, vessels, microaneurysms, hemorrhages, exudates, and neovascularization. | P0 | PS (explicit structure/lesion list) | Segmentation output produced for each named structure/lesion class on a gradable image. |
| FR-006 | System shall assign an ICDR grade (0–4) to every gradable image. | P0 | PS | Grade output is one of {0,1,2,3,4} for every gradable input. |
| FR-007 | System shall output a binary referable/non-referable flag, referable = Grade ≥2. | P0 | PS | Flag matches grade-derived threshold on 100% of test cases. |
| FR-008 | System shall meet ≥90% sensitivity / ≥85% specificity for the referable-DR binary decision on the defined external validation set. | P0 | PS numeric target | Measured on EyePACS cold holdout (Section 14.7), reported with confidence interval. |
| FR-009 | System shall output a calibrated confidence score per case. | P0 | PS ("clinically interpretable outputs") | Confidence value present on every graded case; calibration checked (Section 16). |
| FR-010 | System shall route low-confidence cases to mandatory ophthalmologist review. | P1 | Inferred from PS's review requirement + validation-rigor complaint | Cases below the confidence threshold are flagged distinctly in the review queue. |
| FR-011 | System shall generate a heatmap/attribution overlay for every graded case. | P0 | PS explainability requirement | Overlay renders alongside grade for 100% of graded cases. |
| FR-012 | System shall compute and display an overlap/validation score between attribution and ground-truth lesion masks during development/evaluation. | P1 | Our interpretation of "explainable" as validated, not just visualized | Score computed and logged for every case in the evaluation set. |
| FR-013 | System shall generate a structured case report. | P0 | PS ("clinically interpretable outputs") | Report contains all fields in Section 19; auto-generated per case. |
| FR-014 | Ophthalmologist review view shall present all evidence needed for a decision within a single screen. | P0 | PS <30s review-time requirement | No required navigation beyond one view to reach confirm/override. |
| FR-015 | System shall log every review confirm/override decision. | P1 | Traceability / future audit needs | Every case has a recorded final human decision distinct from the model's initial output. |
| FR-016 | Simulink module shall accept arrival-rate, service-time, bandwidth, and resource-count parameters and output queue/staffing metrics. | P0 | PS (deployment-resource simulation requirement) | Simulation runs end-to-end and returns the metrics in Section 22 for a given parameter set. |
| FR-017 | Simulink module shall use real benchmarked latency numbers from the team's own trained models for at least the inference-latency parameter. | P1 | Engineering decision (credibility of simulation) | Documented source of each latency parameter used in a simulation run. |
| FR-018 | System shall not call any external AI/LLM/inference API for any prediction. | P0 | Our project constraint | Codebase/dependency audit confirms no such calls. |
| FR-019 | System shall keep configuration (paths, thresholds, credentials) separate from application logic. | P0 | Our project constraint | No hardcoded paths/credentials/thresholds found in code review. |

`[OPEN QUESTION]` Exact supported image formats/resolutions for FR-001 — to be defined against the actual capture-device specification once chosen.

---

## 12. ML Requirements (WHAT, not architecture — see Section 10 of source brief)

### 12.1 Image Quality Assessment
- **Problem:** classify capture usability; optionally explain *why* it failed.
- **Input:** raw fundus image.
- **Output:** gradable / borderline / ungradable + (if ML) failure-region indication.
- **Target/labels:** quality class per image.
- **Training data:** fundus images spanning the quality spectrum, ideally from portable devices `[ASSUMPTION on availability — flagged in Section 13]`.
- **Evaluation metric:** false-negative rate on "gradable" classification is primary (a bad image passed through as good is the dangerous failure), not raw accuracy.
- **Failure cases:** over-rejection (technician burden) vs. under-rejection (propagates bad data downstream).
- **Acceptance criteria:** false-negative "gradable" rate below an agreed threshold `[OPEN DECISION — no PS-stated number]`; rule-based baseline numbers must be reported for comparison before any learned model is adopted.

### 12.2 Retinal Structure Segmentation
- **Problem:** pixel-level localization of OD/fovea, vessels, and DR lesions (MA, HE, EX, NV).
- **Input:** accepted/enhanced image.
- **Output:** per-class segmentation mask.
- **Target/labels:** pixel-level masks.
- **Training data:** pixel-annotated fundus sets (data-scarce — see Section 13).
- **Evaluation metric:** Dice/IoU per class; sensitivity weighted higher than specificity for lesion detection specifically.
- **Failure cases:** missed small/faint microaneurysms (most common failure per our reading-list meta-analysis), false positives from vessel crossings/artifacts.
- **Acceptance criteria:** per-class Dice/IoU reported against IDRiD/DDR test partitions; no single blended "pixel accuracy" number used as the headline metric.

### 12.3 DR Severity Grading
- **Problem:** ICDR 0–4 grading + referable/non-referable binary decision.
- **Input:** image (+ optionally segmentation output as auxiliary features — `[ENGINEERING DECISION]`, not a given).
- **Output:** grade, referable flag, per-class probability, confidence.
- **Target/labels:** ICDR grade per image.
- **Training data:** combined labeled grading datasets (Section 13).
- **Evaluation metric:** sensitivity/specificity for the binary referable decision (PS's explicit metric); quadratic weighted kappa for the 5-class grade (standard, ordinal-aware, used in the original Kaggle DR competition).
- **Failure cases:** false negative on referable DR (worst clinical failure), Mild/Moderate NPDR boundary confusion (documented as the hardest distinction in the literature we reviewed).
- **Acceptance criteria:** FR-008 threshold met on the defined external holdout; kappa reported alongside.

### 12.4 Explainability
- **Problem:** produce and *validate* evidence for the grade.
- **Input:** trained Module 3 model + Module 2 masks.
- **Output:** attribution heatmap, overlap/validation score, structured text.
- **Target/labels:** none for the heatmap itself (post-hoc); pixel masks required for the validation step.
- **Evaluation metric:** IoU between attribution map and ground-truth lesion mask.
- **Failure cases:** plausible-looking but spurious attribution (a documented, not fully solvable, limitation of Grad-CAM-family methods) — must be disclosed to reviewers/judges, not overclaimed.
- **Acceptance criteria:** overlap score computed and reported for every evaluation case; low-overlap cases flagged as low-trust.

`[ENGINEERING DECISION]` Architecture selection for each of the above (CNN/U-Net family/transformer/hybrid) is deferred to technical design; the earlier working session's model bake-off notes should inform, not substitute for, that phase's formal comparison.

---

## 13. Data Requirements

| ID | Requirement |
|---|---|
| DR-001 | Segmentation training data must include pixel-level masks per lesion/structure class. `[PS-implied via Module 2 need]` |
| DR-002 | Grading training data must include an ICDR grade (0–4) per image. |
| DR-003 | Quality-assessment training data must include a gradable/borderline/ungradable (or equivalent) label — `[ASSUMPTION]` this label type is the weakest-covered publicly; a dedicated dataset check is required before committing to a learned quality model. |
| DR-004 | Dataset splits must be performed at the **patient** level, not the image level, to avoid leakage (multiple images per patient in several public datasets). `[VERIFIED FACT — standard, documented pitfall in medical imaging ML]` |
| DR-005 | A cold, fully external validation set (not used in any training) must be reserved to test the PS's sensitivity/specificity targets under realistic distribution shift. |
| DR-006 | Combined training pools drawn from multiple public datasets must be checked for cross-dataset image overlap/near-duplicates (e.g., via perceptual hashing) before training. `[ASSUMPTION — overlap risk pattern documented in the DR-dataset ecosystem generally, not confirmed for our specific combination]` |
| DR-007 | No dataset property, size, or label coverage stated in this PRD should be treated as final without re-verification against the dataset's current official page — several figures carried over from the earlier working session are `[ASSUMPTION]`-tagged widely-cited numbers, not freshly re-checked. |
| DR-008 | Domain-shift disclosure: all major public DR datasets used here were collected on clinic-grade cameras, not portable/handheld devices implied by the PS's rural deployment framing. Any reported accuracy must carry this caveat. |

`[OPEN QUESTION]` Exact dataset(s) attached to the official PS page — believed to be APTOS2019 but unverified at time of writing; must be re-confirmed on the live portal.

---

## 14. Image Quality Requirements

- **Clinically established vs. engineering:** blur, illumination, contrast, occlusion, and field-of-view issues are `[VERIFIED FACT]` well-documented sources of ungradable fundus images in the general ophthalmic-imaging literature; the exact thresholds separating gradable/borderline/ungradable are `[OPEN DECISION]` — not invented here.
- **When is an image unsuitable?** Operationally: when the quality-gate model (or, pre-ML, the rule-based baseline) outputs "ungradable," including after a failed enhancement attempt on a borderline case.
- **How does the technician know what went wrong?** FR-003 — a specific, enumerated rejection reason, not a generic failure.
- **What happens next?** Recapture loop (Workflow A); the loop has no PS-defined maximum retry count — `[OPEN QUESTION]`.

---

## 15. Segmentation Requirements

| Structure/Lesion | Input | Output | Purpose | Display Requirement | Evaluation Requirement |
|---|---|---|---|---|---|
| Optic disc / fovea | Gradable image | Mask/coordinates | Anatomical reference for grading & report | Optional overlay | Localization accuracy (metric TBD in technical design) |
| Vessels | Gradable image | Binary mask | Supports grading context, vessel-pattern review | Optional overlay | Dice/IoU |
| Microaneurysms | Gradable image | Binary mask | Early DR marker | Overlay in ophthalmologist view | Dice/IoU, sensitivity weighted |
| Hemorrhages | Gradable image | Binary mask | Severity marker | Overlay in ophthalmologist view | Dice/IoU |
| Hard/soft exudates | Gradable image | Binary mask | Severity marker | Overlay in ophthalmologist view | Dice/IoU |
| Neovascularization | Gradable image | Binary mask | PDR marker (severe) | Overlay, flagged prominently | Dice/IoU, sensitivity weighted (highest clinical cost of miss) |

`[ENGINEERING DECISION]` Architecture not decided here per Section 10 of the governing brief.

---

## 16. DR Grading Requirements

- **Grading scheme:** ICDR 0–4. `[PS REQUIREMENT]`
- **Referable DR definition:** Grade ≥2. `[PS REQUIREMENT]`
- **Required outputs:** grade, referable flag, per-class probability, confidence.
- **Screening vs. diagnosis:** this system performs **screening/triage classification**, not a standalone diagnostic determination — final clinical decision remains with the ophthalmologist (Workflow B). No diagnostic claim beyond this is made.
- **Confidence & explainability:** see Sections 16(below)/17.
- **Referral workflow:** referable flag routes the case into the ophthalmologist review queue; non-referable cases are still visible to the ophthalmologist but not prioritized, consistent with the human-in-the-loop design decision in Section 9.

---

## 16. Confidence & Uncertainty

- **Requirement:** every graded case carries a calibrated confidence score.
- **Low-confidence handling:** routed to mandatory review (FR-010); exact threshold is `[OPEN DECISION]` — not invented in this PRD, to be selected during technical design using validation-set calibration curves.
- **Calibration:** must be checked empirically (e.g., reliability diagram / expected calibration error) before any threshold is finalized — `[OPEN QUESTION]` for the technical design phase.

---

## 17. Reporting

Structured case report fields:
- Case/patient identifier (de-identified per Section 22)
- Image quality verdict
- DR grade (0–4)
- Referable status (yes/no)
- Lesion evidence summary (which classes detected, where)
- Confidence score
- Segmentation overlay reference
- Referral recommendation
- Model/version identifier `[ENGINEERING DECISION — needed for auditability, not PS-stated]`

`[ENGINEERING DECISION]` No unnecessary patient information (e.g., full demographic history) is included — only what's needed for the screening decision and traceability.

---

## 18. Backend Requirements

- **Data flow:** capture → quality gate → (enhancement) → segmentation → grading → explainability → report → storage → (aggregate stats feed Module 5).
- **Model inference:** served locally/on-prem (district server tier) — no external inference API (FR-018).
- **API requirements:** internal service boundaries between modules; exact protocol `[OPEN QUESTION — technical design]`.
- **Storage:** case records, model artifacts, audit logs; schema `[OPEN QUESTION — technical design]`.
- **Authentication/authorization:** required for technician/ophthalmologist/administrator roles; specifics deferred — `[OPEN QUESTION]`.
- **Logging:** every review decision (FR-015), every quality-gate verdict, every simulation run's input parameters.
- **Error handling:** see Section 23.

`[ENGINEERING DECISION]` No specific implementation technology (language/framework) is locked here — that belongs to technical design, except where MATLAB/Simulink is the named requirement (Module 10 / Section 20).

---

## 19. Frontend Requirements

| Screen ID | Purpose | User | Inputs | Outputs | Actions | Failure States |
|---|---|---|---|---|---|---|
| SCR-01 Capture/Upload | Get image into the system | Technician | Image file/capture stream | Upload confirmation | Capture, upload, retry | Unsupported format, upload failure |
| SCR-02 Quality Verdict | Show accept/reject + reason | Technician | Quality-gate output | Verdict + reason | Retake, proceed | Model/service unavailable |
| SCR-03 Ophthalmologist Review | Single-screen evidence + decision | Ophthalmologist | Full case bundle (Section 9, Workflow B) | Confirm/override recorded | Confirm, override (with reason) | Missing evidence component, low-confidence case flag |
| SCR-04 Case Report | Structured summary | Ophthalmologist / records | Case data | Rendered/exportable report | View, export | Report generation failure |
| SCR-05 Simulation Console | Run/view district resource simulation | Administrator | Parameters (Section 22) | Queue/staffing outputs, ranges | Run, adjust parameters, export | Invalid parameters, simulation failure |

`[OPEN QUESTION]` Exact export format(s) for reports/simulation results — not specified by PS.

---

## 20. Simulink Requirements

- **Inputs/parameters:** patient arrival rate, reviewer service time, device count, bandwidth profile, inference latency (from real benchmarks per FR-017). Any parameter not explicitly specified by the PS is marked `[PARAMETER TO BE DETERMINED]`.
- **Outputs:** queue-length/wait-time curves, required reviewer count, required device count, bandwidth requirement.
- **Simulation scenarios:** at minimum, a baseline scenario at the PS's stated 100,000+ patients/year scale, plus best/worst-case bandwidth and staffing variants.
- **Method:** `[ENGINEERING DECISION]` discrete-event/queuing-theory simulation (e.g., SimEvents), not ML — forcing ML into this module was explicitly rejected as unjustified.
- **Validation:** simulation outputs should be sanity-checked against a simplified analytical queuing approximation (e.g., M/M/1) before being trusted for the full model.
- **Visualization requirements:** queue length over time, utilization by resource type, bottleneck indicator.

---

## 21. Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Performance | Ophthalmologist review supportable within <30s per case | `[PS REQUIREMENT]` |
| Scalability | Must support 100,000+ patients/year at district scale | `[PS REQUIREMENT]` |
| Availability | `[OPEN QUESTION]` — no PS-stated uptime target |  |
| Security | See Section 22 |  |
| Privacy | See Section 22 |  |
| Reproducibility | No hardcoded paths/credentials/dataset locations; configuration separated from logic | Our project constraint |
| Maintainability | Modules independently testable per Section 10 breakdown | Engineering decision |
| Usability | Technician workflow must not require diagnostic knowledge | Engineering decision, inferred from persona |
| Observability | All review decisions and simulation runs logged (Section 18) | Engineering decision |
| Portability | `[OPEN QUESTION]` — target OS/hardware for PHC-side and district-server-side components not yet specified |  |

---

## 22. Security & Privacy

- **Patient data:** minimize collection to what's needed for screening + traceability (Section 19); no unnecessary demographic data stored.
- **De-identification:** case identifiers must not directly expose patient-identifying information in the ophthalmologist/administrator views beyond what's clinically necessary — exact de-identification scheme `[OPEN QUESTION]`.
- **Authentication/authorization/encryption/access control/logs:** required at a basic level for a 3-role system (technician/ophthalmologist/administrator); specific mechanisms deferred to technical design.
- **Regulatory requirements:** `[I cannot confirm applicable Indian medical-software/health-data regulatory requirements without a dedicated, current legal/regulatory search — this must not be fabricated and should be verified with an authoritative current source before any real deployment claim is made.]`

---

## 23. Error & Failure Handling

| Scenario | Trigger | System Behavior | User Message | Recovery | Logging |
|---|---|---|---|---|---|
| Invalid/unsupported image | Wrong format/corrupted file | Reject at upload | Specific format error | Re-upload | Yes |
| Poor-quality image | Quality gate = ungradable | Block grading | Specific rejection reason (FR-003) | Recapture | Yes |
| Model unavailable/timeout | Inference service down | No grade produced | "Screening unavailable, try again" | Retry / escalate to manual | Yes |
| Low-confidence prediction | Confidence below threshold | Route to mandatory review | Flag shown to ophthalmologist | Human review | Yes |
| Missing evidence component | Segmentation/explainability failure | Case marked incomplete | Explicit "evidence unavailable" note, not a silently blank overlay | Manual review fallback | Yes |
| Backend unavailable | Service/network failure | Queue or block submission | Connectivity error | Retry when available | Yes |
| Simulation failure | Invalid/out-of-range parameters | Reject run | Parameter validation error | Correct inputs, re-run | Yes |

---

## 24. Performance Requirements

| Metric | Definition | Target | Source | Measurement Method |
|---|---|---|---|---|
| Sensitivity (referable DR) | True positive rate, Grade ≥2 | >90% | `[PS REQUIREMENT]` | On defined external cold-holdout set |
| Specificity (referable DR) | True negative rate, Grade ≥2 | >85% | `[PS REQUIREMENT]` | Same as above |
| Review time | Time for ophthalmologist to reach a decision | <30s | `[PS REQUIREMENT]` | Timed user testing on SCR-03 |
| Throughput | Patients screenable per year at district scale | 100,000+ | `[PS REQUIREMENT]` | Derived from Module 5 simulation using benchmarked per-case latency |
| Segmentation quality | Dice/IoU per lesion class | `[OPEN DECISION — no PS-stated number]` | — | Against IDRiD/DDR test partitions |
| Grading agreement (5-class) | Quadratic weighted kappa | `[OPEN DECISION — no PS-stated number]` | Standard field metric, not PS-mandated | Against combined grading test set |
| Quality-gate false-negative rate | "Gradable" verdict on actually-ungradable images | `[OPEN DECISION]` | — | Against quality-labeled validation set |

No target above is invented where the PS is silent — such cells are explicitly marked open.

---

## 25. Acceptance Criteria (module-level, representative)

- **AC-IQA-001:** Quality gate produces a verdict for 100% of submitted images before any downstream module runs.
- **AC-SEG-001:** Segmentation module produces per-class Dice/IoU scores on the IDRiD/DDR test partition, reported per class (not a single blended number).
- **AC-GRADE-001:** Binary referable-DR decision meets FR-008 on the defined external holdout.
- **AC-XAI-001:** Every graded case has an attribution overlay and a computed overlap-with-ground-truth score in the evaluation pipeline.
- **AC-SIM-001:** Simulation produces queue/staffing outputs for the PS's stated 100,000+/year scale using at least one real benchmarked latency input.
- **AC-REVIEW-001:** SCR-03 presents all Workflow-B evidence components on a single screen with no required additional navigation.

---

## 26. MVP Definition

**Included (Level 1):**
- Rule-based (or simplest defensible) quality gate — FR-002/003.
- Basic segmentation for at least microaneurysms, hemorrhages, exudates (core DR lesions) via a single baseline model.
- Single-backbone DR grading (baseline, no ensemble/GCN) meeting a *demonstrable*, even if not yet target-level, sensitivity/specificity.
- Heatmap-only explainability (overlap-validation scoring can follow in Level 2).
- Minimal structured report.
- Single-screen ophthalmologist review.
- Simulink simulation using placeholder-marked `[PARAMETER TO BE DETERMINED]` values where real benchmarks aren't yet available, clearly labeled as provisional.

**Excluded from MVP (deferred to Level 2/3):** ensemble fusion, ordinal-loss refinements, CBAM/attention additions, multi-task shared backbones, full overlap-validation gating, conditional enhancement re-scoring loop refinements.

**Dependencies:** at minimum one pixel-annotated dataset (IDRiD) and one grading dataset (APTOS or equivalent) confirmed accessible.

**Acceptance criteria:** all mandatory PS requirements (FR-002, FR-005, FR-006, FR-007, FR-011, FR-013, FR-016) are present in some functioning form, even if not yet at full target performance — MVP scope is not permitted to drop a mandatory PS requirement outright, only to defer its refinement.

---

## 27. Future Scope

- **MVP** — Section 26.
- **SIH final prototype (Level 2/3):** bake-off-selected grading backbone(s), CBAM-enhanced segmentation, calibrated uncertainty with tuned review-routing threshold, full explainability validation loop, refined Simulink model with fully benchmarked parameters.
- **Future production system (explicitly out of current scope):** OCT/multimodal fusion, regulatory-grade validation, EMR integration, multi-site federated deployment.

---

## 28. Out of Scope

- Regulatory clearance / formal clinical trial validation.
- Any diagnosis beyond screening/triage classification.
- OCT or other non-fundus-photo modalities.
- Full patient-management/EMR system.
- Any external LLM/inference API dependency.
- Demographic-specific model tuning without verified population data.

---

## 29. Technical Dependencies

| Item | Status |
|---|---|
| MATLAB + named toolboxes (Image Processing, Computer Vision, Deep Learning, Medical Imaging, Statistics & ML, Simulink) | To verify (hard requirement vs. strong preference — `[ASSUMPTION]`) |
| IDRiD dataset | Verified as publicly available for research (per earlier session); exact current counts to verify |
| DDR dataset | Verified as publicly available via GitHub; lesion-mask subset coverage to verify |
| APTOS2019, Messidor-2, EyePACS | Verified as publicly available under competition/registration terms; exact current counts to verify |
| DRIVE/STARE/CHASE_DB1 (vessel GT) | Verified as publicly available for research use |
| GPU compute for training | To verify (team's actual hardware access) |
| District-server-class hardware for inference | To verify |
| PHC-side edge hardware for quality gate | To verify |

---

## 30. Traceability Matrix (representative rows — full matrix to be maintained as a living artifact)

| PS Requirement | PRD Requirement | Module | Implementation Task | Test | Acceptance Criterion |
|---|---|---|---|---|---|
| Image-quality variability handling | FR-002, FR-003, FR-004 | Module 1 | Quality-gate baseline + enhancement | Quality-gate eval on held-out quality-labeled set | AC-IQA-001 |
| Structure/lesion segmentation | FR-005 | Module 2 | Segmentation model training | Dice/IoU on IDRiD/DDR | AC-SEG-001 |
| ICDR grading + sensitivity/specificity targets | FR-006–FR-009 | Module 3 | Grading model training + threshold tuning | External cold-holdout eval | AC-GRADE-001 |
| Explainable outputs | FR-011, FR-012 | Module 4 | Attribution generation + overlap scoring | Overlap-score computation on evaluation set | AC-XAI-001 |
| <30s review | FR-014 | UI (SCR-03) | Single-screen review design | Timed user test | AC-REVIEW-001 |
| District-scale simulation | FR-016, FR-017 | Module 10 | Simulink model build | Simulation run at target scale | AC-SIM-001 |

---

## 31. Risk Register

| Risk ID | Risk | Probability | Impact | Detection | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-01 | No public dataset reflects portable-camera image quality; field performance unverified | `[cannot assign a numeric probability without a defined estimation method — qualitatively: likely]` | High — undermines the PS's own rural-deployment premise | Domain-shift gap flagged explicitly in reporting | Disclose limitation openly; treat EyePACS heterogeneity as the closest available proxy | Team | Open |
| R-02 | Pixel-annotated data is scarce (IDRiD ~516 images) | Likely | Medium-High — limits segmentation model ceiling | Track Dice/IoU trends during training | Heavy augmentation; combine IDRiD+DDR; defer complex architectures until baseline validated | Team | Open |
| R-03 | MATLAB/Simulink hard-requirement status unclear | Unclear | Medium — affects tooling choice | Re-check PS page live | Build core pipeline framework-agnostic where possible; commit to Simulink specifically for Module 10 regardless | Team | Open |
| R-04 | Cross-dataset image overlap/leakage | Unclear | High — inflates reported performance | Perceptual-hash dedup check pre-training | Run dedup check before finalizing training pool (DR-006) | Team | Open |
| R-05 | Confidence threshold for mandatory review not empirically grounded | Certain until resolved | Medium — affects review-routing safety | Calibration curve analysis | Set threshold from validation-set calibration data, not intuition | Team | Open |

`[ENGINEERING DECISION]` Probability values are qualitative, not numeric, because no probability-estimation method has been defined for this project — assigning invented numeric probabilities would misrepresent certainty.

---

## 32. Open Questions

| Question | Why it matters | Who must answer | How to verify | Blocking? |
|---|---|---|---|---|
| Is MATLAB/Simulink mandatory for the whole pipeline, or only clearly justified for Module 5? | Affects entire tech stack choice | Team, against live PS page | Re-fetch/re-read official PS page | Blocking for architecture |
| What is the PS's actual attached dataset? | Determines primary grading fine-tune data | Team | Re-check live PS portal | Blocking for data pipeline start |
| What confidence threshold routes a case to mandatory review? | Safety-critical routing decision | Team (data-driven) | Calibration analysis on validation set | Blocking for Module 3/5 UI integration |
| What quality-gate thresholds (blur/illumination/FOV) define gradable vs. borderline vs. ungradable? | Defines Module 1 behavior | Team (data-driven) | Baseline rule-based model tuning against labeled quality data | Blocking for Module 1 |
| What regulatory/data-privacy requirements apply even to a prototype handling patient images? | Legal/ethical exposure | Team, with authoritative current source | Dedicated regulatory search — not fabricated here | Non-blocking for hackathon prototype, blocking for any real deployment |
| Exact supported image formats/resolutions | Defines FR-001 scope | Team | Target capture-device spec | Non-blocking for MVP if a reasonable default is chosen |
| Max retry count for recapture loop | UX completeness | Team | Design decision | Non-blocking |

---

## 33. Decision Log

| Decision ID | Decision | Reason | Alternatives Considered | Evidence | Status |
|---|---|---|---|---|---|
| DEC-01 | Build rule-based quality-gate baseline before any learned model | Avoids unjustified ML use; gives a defensible comparison point | Jump straight to CNN | Module 1 analysis (Section 12.1) | Accepted |
| DEC-02 | Treat "explainability" as requiring overlap validation against ground truth, not just a rendered heatmap | PS's own complaint about "lack of clinical validation rigor" | Heatmap-only explainability | PS text interpretation | Accepted |
| DEC-03 | Patient-level (not image-level) dataset splitting | Standard, documented leakage-prevention practice in medical imaging ML | Image-level random split | General medical-ML methodology | Accepted |
| DEC-04 | No ML in the Simulink resource-planning module | Task is a queuing/discrete-event problem, not a learning problem; forcing ML in would be a red flag to a technically literate reviewer | ML-based demand forecasting | Module 5 analysis (Section 20) | Accepted |
| DEC-05 | Human-in-the-loop review on every case, not only low-confidence ones | <30s review requirement + validation-rigor complaint together imply expected clinician confirmation, not full automation | Fully automated triage with review only on low-confidence cases | Workflow A validation (Section 9) | Accepted, revisit if PS intent is clarified |
| DEC-06 | Architecture selection (CNN/U-Net/transformer/hybrid) deferred to technical design phase | PRD should specify WHAT, not lock in HOW, per project brief | Locking architecture now | Section 12 framing | Accepted |

---

## 34. Technical Design Handoff

**Requirements:** Sections 11–20 (Functional, ML, Data, Quality, Segmentation, Grading, Explainability, Confidence, Reporting, Backend, Frontend, Simulink).
**Interfaces:** module boundaries per Section 10 table; exact protocols are open (Section 18).
**Data requirements:** Section 13 (DR-001–DR-008).
**Acceptance criteria:** Section 25, keyed to Section 30 traceability.
**Constraints:** no external AI/inference APIs, no hardcoded paths/credentials/thresholds, MATLAB/Simulink where justified (Section 29).
**Open questions:** Section 32 — treat the "blocking" ones as pre-requisites for starting the corresponding module's implementation.
**Dependencies:** Section 29.
**Non-functional requirements:** Section 21.

No implementation code is included in this document, per instruction.

---

## 35. Final PRD Consistency Audit

- [x] Every PS requirement (image-quality handling, structure/lesion segmentation, ICDR grading, explainability, Simulink resource simulation, sensitivity/specificity targets, <30s review, 100,000+/year scale, named toolboxes) appears in the PRD.
- [x] Every functional requirement (Section 11) has an acceptance criterion.
- [x] No assumption is presented as a confirmed requirement — all tagged.
- [x] No dataset property is claimed without an `[ASSUMPTION]`/`[VERIFIED FACT]` tag; several are explicitly flagged for re-verification.
- [x] No clinical claim beyond "screening aid, not diagnosis, not clinically validated" is made.
- [x] No architecture is locked (Section 12, DEC-06).
- [x] No external API required (FR-018).
- [x] No hardcoded implementation required (FR-019).
- [x] All unknowns are listed in Section 32.
- [x] Acceptance criteria exist (Section 25) and trace to requirements (Section 30).
- [x] Traceability exists (Section 30, representative — living document).
- [x] MVP is defined (Section 26) without dropping mandatory PS requirements.
- [x] Out-of-scope is defined (Section 28).
- [x] Risks are documented (Section 31) with qualitative, non-fabricated probability language.
- [x] Open questions are documented (Section 32).
- [x] A 3-person team can derive an implementation plan from module boundaries (Section 10) + requirements (Sections 11–20) + handoff (Section 34).

**Known limitation of this PRD itself:** several dataset figures and the "MATLAB mandatory vs. preferred" question were carried over from an earlier working session's fetch that could not be re-verified live at the time this document was written. These are flagged inline and in Section 32 — they should be re-checked against the live PS portal before this PRD is finalized for submission.
