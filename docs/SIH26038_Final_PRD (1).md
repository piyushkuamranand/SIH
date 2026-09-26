# Product Requirements Document — SIH26038
## Explainable AI for Diabetic Retinopathy Screening in Rural India
### Final Consolidated PRD — Single Source of Truth for Requirements

---

## 1. Document Control

| Field | Value |
|---|---|
| Document | Final PRD — SIH26038 (consolidated) |
| Version | 2.0 (supersedes "SIH26038-PRD v1.0" and "NETRA-DR Final Technical Blueprint" as the requirements authority) |
| Date | 23 September 2026 |
| Problem ID / Sponsor | SIH26038 / MathWorks |
| Category / Theme | Software / MedTech-BioTech-HealthTech |
| Team | 3 engineers |
| PS source | Retrieved 23 Sep 2026 from the community mirror `sih2026.vuce.in/ps/SIH26038` (unofficial; links to `sih.gov.in`). **Reconfirm against sih.gov.in (OQ-01).** |
| PS deadline shown | 30 September 2026 |
| Companion documents | `SIH26038_PRD_Consolidation_Analysis.md` (rationale for every retain/modify/remove decision); Technical Design (to be written) |
| Status | Approved for technical-design handoff, subject to blocking open questions (§43) |

### 1.1 Evidence tags
| Tag | Meaning |
|---|---|
| `[PS]` | Stated in the official problem statement. |
| `[VERIFIED]` | Checked against an authoritative external source on 23 Sep 2026. |
| `[ENG]` | Engineering decision by the team, with stated rationale. |
| `[ASSUMPTION]` | Reasonable but unverified; provisional. |
| `[NEEDS VERIFICATION]` | Must be verified before being relied upon. |
| `[OPEN]` | Value/decision not yet made; see §43. |
| `[MOVE TO TECHNICAL DESIGN]` | Belongs in the technical design, recorded here only as context. |
| `[PARAMETER TO BE DETERMINED]` | Simulation/threshold value not yet established. |

### 1.2 Requirement ID scheme
FR (functional) · MLR (machine learning) · DAT (data — "DR" is avoided because it denotes diabetic retinopathy) · CVR (computer vision) · IQR (image quality) · ENH (enhancement) · SEG (segmentation/detection) · GRD (grading) · XAI (explainability) · UNC (confidence/uncertainty) · RPT (reporting) · UX (frontend) · BE (backend) · STO (storage) · SEC (security/privacy) · MAT (MATLAB) · SIM (Simulink/simulation) · NFR · PERF · SCL (scalability) · EVAL · TST (testing) · AC (acceptance) · ERR · DEP (deployment) · OPS (MLOps/maintainability).
Priority: **P0** = PS-mandated or required for the pipeline to function end-to-end; **P1** = materially improves safety/trust/reliability; **P2** = deferrable enhancement.
"Shall" = mandatory; "should" = recommended.

---

## 2. Executive Summary

**Problem.** `[PS]` DR screening in rural India is limited by ophthalmologist scarcity and by AI tools that are black boxes, lack validation rigor, and fail on variable-quality images from portable fundus cameras.

**Product.** A MATLAB-based screening pipeline with a Simulink planning model that:
1. assesses fundus image adequacy and enhances borderline images or requests recapture with a reason;
2. localizes/segments retinal anatomy and DR lesions (optic disc/fovea, vessels, microaneurysms, exudates, hemorrhages, neovascularization);
3. grades DR on the ICDR 0–4 scale and flags referable DR (Level 2+);
4. presents Grad-CAM maps, lesion evidence mapped to ICDR criteria, calibrated confidence and an annotated report so an ophthalmologist can validate a case in under 30 seconds (human-in-the-loop);
5. simulates and optimizes district-level resources (acquisition, bandwidth, processing, review capacity) for 100,000+ patients/year.

**Users.** PHC technician, ophthalmologist (reviewer), district health administrator.

**Key targets `[PS]`.** Referable-DR sensitivity **>90%** and specificity **>85%**; ophthalmologist validation **<30 s**; district scale **100,000+ patients/year**; Grad-CAM outputs **rated clinically useful**; **integrated pipeline outperforms any single-technique approach** against published benchmarks.

**Positioning.** A **screening/triage aid** in a supervised workflow. This PRD makes **no claim** of clinical validation, regulatory approval, or diagnostic autonomy. The PS targets are engineering targets measured by a pre-specified protocol (§35), not guarantees.

**Major constraints.** MATLAB-based runtime pipeline `[PS]`; no external AI/LLM/inference APIs `[ENG]`; no invented thresholds — undetermined values are listed as open decisions.

---

## 3. Problem Statement (PS, faithful restatement)

`[PS]` Design a MATLAB-based retinal image analysis pipeline for automated DR screening addressing real-world deployment challenges:

| PS-ID | Requirement |
|---|---|
| PS-01 | MATLAB-based retinal image analysis pipeline for automated DR screening. |
| PS-02 | Automatically evaluate fundus image adequacy (focus, illumination, field of view). |
| PS-03 | Adaptive enhancement (CLAHE, illumination normalization, denoising) for borderline images. |
| PS-04 | Reject ungradeable images with recapture feedback. |
| PS-05 | Optic disc / fovea localization. |
| PS-06 | Vessel segmentation. |
| PS-07 | Microaneurysm detection. |
| PS-08 | Exudate segmentation. |
| PS-09 | Hemorrhage classification. |
| PS-10 | Neovascularization detection. |
| PS-11 | Classification on the International Clinical DR severity scale, Levels 0–4. |
| PS-12 | Referable DR (Level 2+): sensitivity >90%, specificity >85%. |
| PS-13 | Grad-CAM attention maps. |
| PS-14 | Lesion-level evidence correlated with clinical criteria. |
| PS-15 | Calibrated confidence scores. |
| PS-16 | Automated annotated reports. |
| PS-17 | Ophthalmologist validation in under 30 seconds; human-in-the-loop workflow. |
| PS-18 | Simulink model of the telemedicine pipeline: image acquisition rates, bandwidth constraints, processing throughput, review capacity. |
| PS-19 | Optimize resource allocation for district-level programs serving 100,000+ patients annually. |
| PS-20 | Clinical validation rigor; clinically meaningful explainability; sub-pixel microaneurysm detection. |
| PS-21 | Tools: Image Processing, Computer Vision, Deep Learning, Medical Imaging, Statistics & Machine Learning Toolboxes; Simulink. |
| PS-22 | Expected: working prototype. |
| PS-23 | Expected: explainable Grad-CAM outputs rated as clinically useful. |
| PS-24 | Expected: validation against published benchmarks showing the integrated pipeline outperforms any single-technique approach. |
| PS-25 | Context: portable fundus cameras in field conditions; primary healthcare centres across rural India. |
| PS-26 | Attached dataset: APTOS `[VERIFIED via mirror; reconfirm]`. |

---

## 4. Problem Context

### 4.1 PS-stated background `[PS — not independently re-verified]`
India has over 77 million diabetic adults; DR affects ~18% of them; early screening can prevent 90% of vision loss; there is ~1 ophthalmologist per 100,000 rural population, making mass manual screening infeasible.

### 4.2 Interpretation `[ENG]`
- **Explainability must be checkable, not decorative.** Justified by PS-20/PS-23: the product must both *show* evidence and *measure* whether that evidence is meaningful (overlap with lesion ground truth + clinician rating).
- **Non-ideal capture is the default condition.** Justified by PS-25.
- **Rejection is useful only with a reason.** PS-04 requires recapture feedback.
- **Review capacity is a design variable.** PS-19 asks to optimize review capacity, so the case-routing policy must be configurable and evaluated, not hard-coded.

### 4.3 Known evidence gaps `[VERIFIED]`
- Most large public DR datasets are clinic-camera images. **mBRSET** (handheld cameras; 5,164 images, 1,291 patients; ICDR + quality labels) is a portable-domain exception (non-Indian population).
- Public pixel-level lesion datasets **IDRiD (81 images)** and **DDR (757 images)** provide MA/HE/EX/SE masks but **no neovascularization masks**.
- The RETFound foundation model's colour-fundus pretraining corpus includes **88,702 Kaggle-EyePACS images**, so EyePACS cannot serve as independent validation for models initialised from it.

### 4.4 Target environment
PHC capture with portable cameras, variable connectivity, telemedicine review by remote ophthalmologists `[PS]`. Specific network topology (edge vs. district server) is **not** a requirement; it is a simulation scenario `[ASSUMPTION]`.

---

## 5. Product Vision

```
INPUT                      PIPELINE (MATLAB)                                   OUTPUT
Fundus image  ──►  Adequacy check ─► (ungradable) recapture feedback ──► Technician
(portable,           │ (borderline) enhance ─► re-check once
 variable quality)   ▼ (gradable)
                 Anatomy + lesion analysis
                     ▼
                 ICDR grade 0–4 + referable flag + calibrated confidence + uncertainty
                     ▼
                 Grad-CAM + lesion evidence ↔ ICDR criteria + annotated report ──► Ophthalmologist
                     ▼                                                       (<30 s validate)
                 Case & timing logs ──► Simulink model ──► resource plan ──► District administrator
```

**Vision statement.** Every screening decision arrives with evidence a specialist can verify in seconds, and every deployment decision is backed by a simulation parameterised with the system's own measured performance.

---

## 6. Goals

| ID | Goal | Source | Measured by |
|---|---|---|---|
| G1 | Meet referable-DR sensitivity >90% and specificity >85% under the pre-specified external protocol. | PS-12 | EVAL-001…006 |
| G2 | Deliver every PS module (quality, enhancement, six structure/lesion outputs, grading, explainability, report, simulation) in a working prototype. | PS-02…PS-22 | AC-001…AC-020 |
| G3 | Make explainability measurable: overlap with lesion ground truth **and** clinician usefulness rating. | PS-20, PS-23 | XAI-005, XAI-006 |
| G4 | Demonstrate, via ablation and published-benchmark comparison, whether the integrated pipeline outperforms single-technique approaches. | PS-24 | EVAL-007, EVAL-008 |
| G5 | Enable ophthalmologist validation in <30 s per case. | PS-17 | PERF-003 |
| G6 | Produce a Simulink model that optimizes resource allocation for 100,000+ patients/year using measured latencies. | PS-18, PS-19 | SIM-001…012 |
| G7 | Report honestly: domain shift, data gaps, contamination, and unmet targets are disclosed. | PS-20 | NFR-009 |

---

## 7. Non-Goals

- Regulatory-cleared medical device or formal prospective clinical trial.
- Autonomous diagnosis or treatment recommendation beyond screening/referral.
- OCT, OCT-angiography, or other non-colour-fundus modalities.
- Diabetic macular edema grading (not in PS; may be future scope).
- Full EMR / patient-management system.
- Use of any external AI, LLM, or hosted inference API.
- Demographic-specific model tuning without verified population data.

---

## 8. Target Users

| User | Role in workflow | Primary need |
|---|---|---|
| PHC technician | Captures images, acts on quality verdict | Know immediately whether the image is usable and how to fix it |
| Ophthalmologist | Reviews AI output, confirms/overrides | Verify a case in <30 s with trustworthy evidence |
| District health administrator | Plans staff, devices, bandwidth, servers | Evidence-based resource allocation for 100k+/year |
| Secondary: Evaluator/judge, development team | Assess validity | Reproducible metrics, traceability |

---

## 9. Personas

No demographic attributes are invented; personas are defined by role, environment, and task.

### 9.1 PHC Technician
- **Goals:** capture a gradable image quickly; minimise patient retakes.
- **Skill level:** `[ASSUMPTION]` not clinically trained; UI must not require diagnostic knowledge.
- **Environment:** PHC or field camp; portable camera; intermittent connectivity `[PS-25]`.
- **Pain points `[ASSUMPTION]`:** cannot judge adequacy on the spot; no feedback loop.
- **Actions:** capture/upload, read verdict, retake, submit.
- **Outputs needed:** verdict + specific reason + retake guidance.
- **Failure scenarios:** repeated rejections without actionable guidance; device or network failure mid-capture.

### 9.2 Ophthalmologist
- **Goals:** confirm or override within <30 s `[PS-17]`.
- **Needs in one view:** original and enhanced image, Grad-CAM, lesion overlays, grade, referable flag, confidence, uncertainty flags, criteria evidence, quality verdict.
- **Actions:** confirm, override grade and/or referral (with reason), mark evidence as unhelpful.
- **Failure scenarios:** missing evidence component; misleading heatmap; low-confidence flood.

### 9.3 District Health Administrator
- **Goals:** decide number of cameras, AI servers, reviewers, and bandwidth to meet service targets for 100,000+ patients/year.
- **Needs:** parameterised scenarios, bottleneck identification, ranges not single points, optimized configuration.
- **Failure scenarios:** simulation driven by invented parameters; single-point outputs presented as certainties.

---

## 10. User Journeys

### Journey A — PHC screening
```
Capture/upload → validate file → adequacy check
  ├─ Ungradable → reason + guidance → recapture (repeat up to N [OPEN]) → if still ungradable: "Ungradable – refer for manual examination" [OPEN policy]
  ├─ Borderline → enhancement → re-check once → Gradable ➜ continue | Ungradable ➜ recapture branch
  └─ Gradable → anatomy + lesions → grade + flag + confidence + uncertainty
        → Grad-CAM + criteria evidence + report → routed to review queue per routing policy (§21.1)
```

### Journey B — Ophthalmologist review
Open case from priority-ordered queue → single screen with complete evidence bundle → confirm or override (reason required on override; optional "explanation not useful" flag) → decision logged → report finalized.

### Journey C — District planning
Enter/choose parameters (acquisition rate, operating days/hours, bandwidth, image size/compression, per-stage processing times from benchmarks, reviewer time, resource counts, referral/recapture rates, routing policy) → run scenarios → view queue lengths, waits, utilization, throughput, bottleneck → run optimization → export recommended configuration with ranges.

---

## 11. User Stories

| ID | Story | Acceptance |
|---|---|---|
| US-01 | As a technician, I upload a fundus image so it can be screened. | Supported formats accepted; unsupported rejected with specific error (FR-001). |
| US-02 | As a technician, I receive an adequacy verdict before any grading. | Verdict ∈ {Gradable, Borderline, Ungradable}; no grade for Ungradable (FR-003). |
| US-03 | As a technician, I receive a specific recapture reason. | Reason from enumerated set incl. focus, illumination, FOV (FR-004). |
| US-04 | As a technician, borderline images are enhanced automatically so I retake less. | Enhanced once and re-checked (FR-005). |
| US-05 | As an ophthalmologist, I see the ICDR grade and referable flag. | Grade ∈ {0..4}; flag consistent with grade (FR-008, FR-009). |
| US-06 | As an ophthalmologist, I see Grad-CAM and lesion overlays with the grade. | Same screen (FR-011, FR-014). |
| US-07 | As an ophthalmologist, I see which ICDR criteria the lesions support. | Criteria panel present (FR-012). |
| US-08 | As an ophthalmologist, I see calibrated confidence and uncertainty warnings. | Present on every graded case (FR-010, FR-021). |
| US-09 | As an ophthalmologist, I receive an annotated report automatically. | Report generated per case (FR-013). |
| US-10 | As an ophthalmologist, I confirm/override in <30 s. | Timed test (PERF-003). |
| US-11 | As an administrator, I simulate the district pipeline under different parameters. | Scenario run returns metrics (FR-017). |
| US-12 | As an administrator, I get an optimized resource configuration with ranges. | Optimization output (FR-018). |
| US-13 | As an evaluator, I see ablation and published-benchmark comparisons. | Tables produced (FR-023). |

---

## 12. Product Scope

### 12.1 In scope
All PS modules (PS-01…PS-24) for colour fundus photographs; prototype-grade UI for three roles; retrospective evaluation on public datasets; Simulink simulation and optimization.

### 12.2 Delivery levels `[ENG]`
| Level | Content | Rule |
|---|---|---|
| **L1 — Minimum complete prototype** | Rule-based adequacy check + PS enhancement methods; baseline OD/fovea localization, vessel segmentation, MA detection, exudate segmentation, hemorrhage output, NV detection (may be image-level/proxy with disclosure); baseline ICDR grader + referable flag; Grad-CAM; calibrated confidence; criteria panel (rule-based); annotated report; single-screen review; Simulink model with provisional parameters; external evaluation on at least one external set. | **Must contain a functioning form of every PS module.** No PS requirement may be dropped — only its refinement deferred. |
| **L2 — Target SIH version** | Learned IQA if it beats baseline; improved lesion models incl. soft exudates; lesion-informed grading; uncertainty/OOD flag; overlap validation; clinician rating study; ablation + published-benchmark comparison; Simulink with measured latencies and optimization. | Target for final demonstration. |
| **L3 — Stretch** | IRMA/VH outputs; conformal/advanced uncertainty; cross-dataset robustness study; additional explanation methods. | Only after L2 is stable. |

### 12.3 SIH demonstration scope
A live, end-to-end run on held-out images covering: one gradable non-referable, one referable, one borderline-enhanced, one ungradable-rejected case; the review screen with timing; the evaluation dashboard (external metrics with CIs, ablation, benchmark comparison, calibration); and Simulink scenarios showing each bottleneck regime and the optimized configuration (AC-020).

---

## 13. Product Modules

| # | Module | Purpose | Learned model? | Key outputs | Depends on |
|---|---|---|---|---|---|
| M1 | Intake & Image Quality Assessment | Validate file; judge adequacy | Rule-based baseline mandatory; learned optional | Verdict, reasons, quality scores | — |
| M2 | Enhancement | Improve borderline images | No (classical) | Enhanced image, log of methods | M1 |
| M3 | Anatomy | OD/fovea localization; vessel segmentation | Method open | OD mask/centre, fovea centre, vessel mask | M1/M2 |
| M4 | Lesion Analysis | MA detection, exudate segmentation, hemorrhage classification, NV detection (+ optional SE, IRMA, VH) | Method open | Per-lesion masks/detections/probabilities | M1/M2, M3 |
| M5 | DR Grading | ICDR 0–4 and referable decision | Yes (method open) | Grade, per-class probability, referable flag | M1/M2 (+ optionally M3/M4) |
| M6 | Explainability | Grad-CAM; lesion evidence ↔ ICDR criteria; overlap scoring | Post-hoc | Heatmap, criteria panel, overlap scores | M4, M5 |
| M7 | Confidence & Uncertainty | Calibrated confidence; uncertainty/OOD/inconsistency flags; routing input | Post-hoc/method open | Confidence, flags | M5 |
| M8 | Report Generation | Annotated report | No (deterministic template) | Report (screen + export) | M1–M7 |
| M9 | User Interface | Technician, ophthalmologist, administrator views | No | Screens SCR-01…06 | All |
| M10 | Orchestration, Storage & Logging | Run pipeline, persist cases, audit | No | Case records, logs | All |
| M11 | Simulink Simulation & Optimization | District pipeline model; resource optimization | No (discrete-event/queuing) | Queue metrics, optimized configuration | M10 benchmarks |
| M12 | Evaluation & Benchmark Harness | External validation, ablation, benchmark comparison, calibration, rating study analysis | No | Metric tables, plots | M1–M7, data |

---

## 14. Functional Requirements

| ID | Requirement | Pri | Source | Acceptance |
|---|---|---|---|---|
| FR-001 | The system shall accept a colour fundus image in the configured set of formats and reject other files with a specific error. | P0 | Pipeline | AC-001 |
| FR-002 | The system shall assign each case a unique, de-identified case ID. | P0 | SEC | AC-001 |
| FR-003 | The system shall produce an adequacy verdict ∈ {Gradable, Borderline, Ungradable} before any anatomy, lesion, or grading step, and shall never output a DR grade for an Ungradable image. | P0 | PS-02, PS-04 | AC-002 |
| FR-004 | For Ungradable images the system shall return ≥1 reason code from an enumerated set that includes at minimum *focus*, *illumination*, *field of view*, plus technician-readable recapture guidance. | P0 | PS-04 | AC-003 |
| FR-005 | For Borderline images the system shall apply the enhancement set (ENH-001) and re-run the adequacy check exactly once before final verdict. | P0 | PS-03 | AC-004 |
| FR-006 | For Gradable images the system shall output OD location, fovea location, and a vessel segmentation. | P0 | PS-05, PS-06 | AC-005 |
| FR-007 | For Gradable images the system shall output MA detections, exudate segmentation, hemorrhage output (per SEG-005), and an NV detection result. | P0 | PS-07…PS-10 | AC-006 |
| FR-008 | The system shall assign exactly one ICDR grade ∈ {0,1,2,3,4} to every Gradable image. | P0 | PS-11 | AC-007 |
| FR-009 | The system shall output a referable flag, where Referable ⇔ displayed grade ≥ 2. Internal disagreement between components shall trigger an "inconsistent evidence" flag. | P0 | PS-12 | AC-007 |
| FR-010 | The system shall output a calibrated confidence for every graded case. | P0 | PS-15 | AC-010 |
| FR-011 | The system shall generate a Grad-CAM map for every graded case, computed on the model(s) that determine the displayed grade. | P0 | PS-13 | AC-008 |
| FR-012 | The system shall present lesion-level evidence mapped to the ICDR criteria relevant to the assigned grade (XAI-003). | P0 | PS-14 | AC-009 |
| FR-013 | The system shall auto-generate an annotated report per case (RPT-001…004). | P0 | PS-16 | AC-011 |
| FR-014 | The ophthalmologist review view shall present all decision evidence on a single screen and allow confirm/override without further navigation. | P0 | PS-17 | AC-012 |
| FR-015 | The system shall record every human decision (confirm/override, reason, timestamp, reviewer role) separately from the model output. | P1 | PS-17, audit | AC-013 |
| FR-016 | The system shall route cases to review queues according to a configurable, logged routing policy (§21.1). | P0 | PS-17, PS-19 | AC-013 |
| FR-017 | The Simulink model shall accept the parameter set in SIM-003 and output the metrics in SIM-005. | P0 | PS-18 | AC-016 |
| FR-018 | The simulation shall provide a resource-allocation optimization per SIM-007…SIM-009. | P0 | PS-19 | AC-017 |
| FR-019 | No prediction, explanation, or report shall depend on any external AI/LLM/inference API. | P0 | [ENG] | AC-019 |
| FR-020 | Paths, thresholds, credentials, and routing policy shall be externalised configuration, not code constants. | P1 | [ENG] | AC-019 |
| FR-021 | The system shall flag cases with high uncertainty, out-of-distribution input, or inconsistent evidence. | P1 | PS-20 | AC-010 |
| FR-022 | Reports and simulation results shall be exportable in at least one portable format `[OPEN: format]`. | P1 | [ENG] | AC-011 |
| FR-023 | The evaluation harness shall produce external-validation, ablation, published-benchmark, and calibration outputs (§35). | P0 | PS-12, PS-24 | AC-014, AC-015 |

---

## 15. ML Requirements

Architecture is **not** prescribed in this PRD. Candidate models are recorded in §46 as `[MOVE TO TECHNICAL DESIGN]`.

| ID | Requirement | Pri | Source |
|---|---|---|---|
| MLR-001 | Every learned component shall be compared against a simpler baseline (classical or single-model) on the same split before adoption; the comparison shall be reported. | P0 | PS-24, [ENG] |
| MLR-002 | Any component whose learned version does not measurably improve its primary metric over its baseline shall use the baseline. | P1 | [ENG] |
| MLR-003 | Model selection shall use only training/internal-validation data; external test sets shall be used once, after the operating point is frozen. | P0 | PS-20 |
| MLR-004 | The referable-DR operating point shall be selected on internal validation to meet the sensitivity target with maximum specificity; default 0.5 thresholds shall not be assumed. | P0 | PS-12 |
| MLR-005 | Every pretrained weight used shall be recorded with its pretraining corpus; any evaluation set overlapping that corpus shall not be reported as independent external validation. | P0 | [VERIFIED] risk |
| MLR-006 | Class imbalance shall be addressed and reported; accuracy shall not be a headline metric. | P0 | PS-12 |
| MLR-007 | Models shall be deterministic at inference for a given version and configuration. | P1 | Reproducibility |
| MLR-008 | Each learned model shall have a model card: task, data, splits, metrics with CIs, known limitations, version. | P1 | PS-20 |
| MLR-009 | The grading model(s) determining the displayed grade shall support Grad-CAM (convolutional feature maps on the decision path, or a documented, validated equivalent approved in TD). | P0 | PS-13 |
| MLR-010 | Models shall be importable/executable in MATLAB at inference (MAT-002). | P0 | PS-01 |

### 15.1 Per-task ML definitions
| Task | Input | Output | Labels | Primary metric | Critical failure |
|---|---|---|---|---|---|
| IQA | Raw image | 3-state verdict + reasons | Quality labels | False-"Gradable" rate (ungradable passed as gradable) | Bad image passed downstream |
| OD/fovea | Accepted image | Centres (+ OD mask) | Coordinates, masks | Localization error (distance, normalised) | Wrong macula reference for criteria |
| Vessels | Accepted image | Binary mask | Vessel masks | Dice/IoU, sensitivity | — |
| MA detection | Full-resolution image | Detections/mask | MA masks | Lesion-level sensitivity at fixed false positives per image; pixel Dice secondary | Missed MAs → under-grading |
| Exudates | Accepted image | Mask | EX masks | Dice/IoU per class | — |
| Hemorrhage | Accepted image | Mask (+ class per SEG-005) | HE masks | Dice/IoU; class metrics if applicable | — |
| NV | Accepted image | Detection result | NV labels (§16 gap) | Sensitivity (image or lesion level) | Missed PDR |
| Grading | Accepted image (+ optional lesion features) | Grade, probabilities, flag | ICDR 0–4 | Referable Sens/Spec; QWK | False negative on referable |

---

## 16. Data Requirements

| ID | Requirement | Pri |
|---|---|---|
| DAT-001 | A dataset register shall record, per dataset: source, version/date, licence/access terms, modality, camera(s), population, label types, label provenance, size, known limitations, and permitted use (train/val/test). | P0 |
| DAT-002 | A master metadata table shall hold per image: image ID, patient/exam ID (if available), eye, dataset, split, exact hash, perceptual hash, labels (grade, quality, lesions, OD/fovea). Schema `[MOVE TO TECHNICAL DESIGN]`. | P0 |
| DAT-003 | Splits shall be at patient/exam level (eye pairs kept together), stratified by source. | P0 |
| DAT-004 | Before any training run, duplicate and near-duplicate detection (exact hash, perceptual hash, structural similarity) shall run across the combined pool; duplicates shall be placed in the same split. | P0 |
| DAT-005 | A contamination registry shall list overlaps between training data, pretraining corpora, derived datasets and test sets (known: RETFound ⊃ Kaggle-EyePACS; EyeQ ⊂ EyePACS; Messidor-2 ⊃ 1,058 original-Messidor images). | P0 |
| DAT-006 | At least one fully external grading test set never used in training or model selection shall be reserved (primary: Messidor-2, §35). | P0 |
| DAT-007 | APTOS 2019 (PS-attached) shall be used and results on its held-out split reported. | P0 |
| DAT-008 | Segmentation training/evaluation shall use pixel-level masks (IDRiD 81-image set; DDR 757-image set) with their official test partitions where defined. | P0 |
| DAT-009 | Vessel segmentation shall use vessel-annotated data (DRIVE; others after verification). | P0 |
| DAT-010 | IQA shall use quality-labelled data (e.g., EyeQ, DDR "ungradable" class, mBRSET quality labels after access verification); IDRiD shall not be used as a source of ungradable examples (all curated as adequate quality). | P0 |
| DAT-011 | If Messidor-2 is a test set, original Messidor images shall not be used in training. | P0 |
| DAT-012 | NV-labelled colour-fundus data shall be sought (candidates `[NEEDS VERIFICATION]`: FGADR, others); if unavailable, NV validation shall be disclosed as image-level proxy only. DRAC22 (UW-OCTA) shall not be used. | P0 |
| DAT-013 | A portable-camera evaluation set shall be used if accessible (mBRSET `[NEEDS VERIFICATION: access]`); otherwise domain shift shall be disclosed as untested. | P1 |
| DAT-014 | Every reported metric shall state the dataset, camera type, and population, with a domain-shift note relative to PS-25. | P0 |
| DAT-015 | Dataset figures shall be re-verified against the official source before submission. | P1 |

### 16.1 Dataset roles (verified facts; roles are `[ENG]`)
| Dataset | Verified facts | Planned role | Status |
|---|---|---|---|
| APTOS 2019 | 3,662 labelled images, Aravind Eye Hospital (India), ICDR | Train/val + internal held-out test | PS-attached; licence NEEDS VERIFICATION |
| EyePACS (Kaggle) | 88,702 images, single-grader ICDR | Training (optional); internal only | Contaminated for RETFound-based models |
| Messidor-2 | 874 exams / 1,748 images; used in published RDR benchmarks | **Primary external test** | Label provenance NEEDS VERIFICATION |
| IDRiD | 516 graded (413/103); 81 pixel-level (54/27; MA/HE/EX/SE + OD); OD/fovea centres; Kowa camera 50°; India | Lesion/OD/fovea train+test; secondary external grading test | Overlap between lesion subset and grading set NEEDS VERIFICATION |
| DDR | 13,673 images/9,598 patients; 5 grades + ungradable; 757 pixel-level (MA/HE/EX/SE) | Lesion train; grading train; IQA (ungradable class) | Verified |
| EyeQ | 28,792 EyePACS images; Good/Usable/Reject | IQA train/test | EyePACS-derived |
| DRIVE | 40 images (20/20) vessel masks | Vessels | Verified |
| mBRSET | 5,164 handheld-camera images; ICDR, quality | Portable-domain external test | Access NEEDS VERIFICATION |
| FGADR | 1,842 pixel-annotated images incl. additional lesion types | NV/IRMA candidate | NEEDS VERIFICATION |

---

## 17. Computer Vision Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| CVR-001 | Preprocessing shall detect the circular field-of-view region and normalise orientation/cropping before analysis. | P0 | PS-02 |
| CVR-002 | MA analysis shall operate at a resolution at which annotated MAs remain resolvable; any downsampling shall be justified by a measured MA-recall comparison. | P0 | PS-07, PS-20 |
| CVR-003 | "Sub-pixel microaneurysm detection" shall be implemented per the definition agreed in OQ-04; until resolved, the team shall report MA localization error in pixels (centroid-to-GT) at native resolution. | P0 | PS-20 |
| CVR-004 | All overlays shall be registered to the displayed image coordinates. | P0 | PS-17 |
| CVR-005 | Classical image processing (Image Processing / Computer Vision Toolboxes) shall be used where it meets the requirement (e.g., FOV mask, enhancement, quality features). | P1 | PS-21 |

---

## 18. Image Quality Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| IQR-001 | The adequacy check shall evaluate focus, illumination, and field of view as separate scored criteria. | P0 | PS-02 |
| IQR-002 | Additional reason codes (e.g., contrast, occlusion/artefact, non-fundus image) may be added. | P2 | [ENG] |
| IQR-003 | A rule-based baseline shall be built and evaluated first; a learned IQA model is adopted only under MLR-002. | P0 | [ENG] |
| IQR-004 | Thresholds separating Gradable/Borderline/Ungradable shall be derived from labelled data and recorded in configuration `[OPEN]`. | P0 | — |
| IQR-005 | The primary IQA metric is the false-"Gradable" rate; the false-"Ungradable" rate (technician burden) shall also be reported. | P0 | [ENG] |
| IQR-006 | Non-fundus images shall be classified Ungradable. | P1 | [ENG] |
| IQR-007 | Maximum recapture attempts and the terminal action are configurable `[OPEN: OQ-07]`. | P1 | — |

---

## 19. Enhancement Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| ENH-001 | The enhancement set shall include CLAHE, illumination normalization, and denoising, applied adaptively (selection/parameters based on measured image properties). | P0 | PS-03 |
| ENH-002 | Enhancement shall be applied to Borderline images; the original image shall always be retained and viewable. | P0 | PS-03 |
| ENH-003 | The report shall state which enhancement operations were applied. | P1 | Transparency |
| ENH-004 | The effect of enhancement shall be evaluated (verdict change rate; downstream metric change on paired original/enhanced images). | P1 | PS-24 |
| ENH-005 | Enhancement shall not be used to upgrade an image the IQA judged Ungradable on first pass. | P0 | Safety |

---

## 20. Segmentation & Detection Requirements

| ID | Structure/lesion | PS verb | Output | Evaluation | Display | Pri |
|---|---|---|---|---|---|---|
| SEG-001 | Optic disc | localization | Centre (+ mask) | Normalised distance error; Dice for mask | Optional overlay | P0 |
| SEG-002 | Fovea | localization | Centre | Normalised distance error | Marker (macula reference) | P0 |
| SEG-003 | Vessels | segmentation | Binary mask | Dice/IoU, sensitivity | Optional overlay | P0 |
| SEG-004 | Microaneurysms | detection | Detections / mask + count | Lesion-level sensitivity vs FPs/image; Dice secondary | Overlay + count | P0 |
| SEG-005 | Hemorrhages | classification | Mask + (i) presence/extent per region **or** (ii) morphological type — per OQ-05 | Dice/IoU; class metrics as applicable | Overlay | P0 |
| SEG-006 | Exudates (hard) | segmentation | Mask | Dice/IoU | Overlay | P0 |
| SEG-007 | Soft exudates (cotton-wool) | — | Mask | Dice/IoU | Overlay | P1 |
| SEG-008 | Neovascularization | detection | Detection result (image or region) | Sensitivity/specificity at available label level | Prominent flag | P0 |
| SEG-009 | IRMA, vitreous hemorrhage | — | Detection | If labelled data exists | Flag | P2 |

Additional:
- **SEG-010** Metrics shall be reported per class; no blended "pixel accuracy" headline. (P0)
- **SEG-011** Where no ground truth exists for a class (e.g., NV pixel masks), the output shall be labelled "not validated at pixel level" in UI and report. (P0)
- **SEG-012** Per-class numeric targets are `[OPEN]`; results shall be compared with published results on the same public test partitions (EVAL-008). (P1)

---

## 21. DR Grading Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| GRD-001 | Grading scale: ICDR 0 (no DR), 1 (mild NPDR), 2 (moderate NPDR), 3 (severe NPDR), 4 (PDR). | P0 | PS-11 |
| GRD-002 | Referable DR = grade ≥ 2. | P0 | PS-12 |
| GRD-003 | Outputs: grade, per-grade probabilities, referable flag, calibrated confidence. | P0 | PS-11, PS-15 |
| GRD-004 | Referable sensitivity >90% and specificity >85% on the primary external set (EVAL-001). | P0 | PS-12 |
| GRD-005 | Five-class agreement shall be reported with quadratic weighted kappa and per-class sensitivity/specificity. | P0 | [ENG] |
| GRD-006 | The system performs screening/triage classification only; the ophthalmologist's decision is final. | P0 | Scope |
| GRD-007 | If NV is detected with confidence above a configured level, the case shall be flagged for priority review regardless of grade. | P1 | Safety [ENG] |

### 21.1 Review routing policy (FR-016)
- Default prototype policy `[ENG]`: **all graded cases are available for review**; **mandatory** review for Referable, low-confidence, OOD/uncertain, inconsistent-evidence, NV-flagged, and ungradable-after-retries cases; non-referable confident cases in a lower-priority queue.
- Alternative policies (e.g., review only mandatory categories) shall be configurable and evaluated **in simulation only**; any workload-reduction claim shall be labelled "simulated".
- Adoption of any bypass policy beyond simulation requires clinical-advisor sign-off (OQ-08).

---

## 22. Explainability Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| XAI-001 | Grad-CAM maps shall be generated for the predicted grade (and, optionally, for the referable decision) on every graded case. | P0 | PS-13 |
| XAI-002 | Additional methods (e.g., Grad-CAM++, occlusion) are optional and shall be labelled distinctly from Grad-CAM. | P2 | [ENG] |
| XAI-003 | A clinical-criteria panel shall list, for the assigned grade, the ICDR criteria considered and the lesion evidence supporting or not supporting each (e.g., presence of MAs only; hemorrhages/MAs by quadrant; venous beading; IRMA; NV/vitreous hemorrhage), marking criteria the system cannot assess (e.g., venous beading if not modelled). Criteria mapping source: ICDR scale definitions `[NEEDS VERIFICATION: cite primary ICDR publication in TD]`. | P0 | PS-14 |
| XAI-004 | Lesion overlays and counts shall be shown alongside the heatmap. | P0 | PS-14 |
| XAI-005 | On evaluation sets with lesion masks, the overlap between Grad-CAM and lesion ground truth (IoU and coverage/pointing-type metric, defined in TD) shall be computed per case and summarised. | P1 | PS-20 |
| XAI-006 | A clinician usefulness rating study shall be conducted on a sample of cases: raters score each explanation on a predefined scale; protocol, sample size, and rater count `[OPEN: OQ-06]`. | P0 | PS-23 |
| XAI-007 | The UI and report shall state that heatmaps indicate model attention and may highlight non-causal regions. | P0 | Honesty |
| XAI-008 | Cases with low heatmap–lesion agreement shall be marked "low explanation agreement" when lesion outputs exist. | P1 | [ENG] |

---

## 23. Confidence & Uncertainty

| ID | Requirement | Pri | Source |
|---|---|---|---|
| UNC-001 | Confidence values shall be calibrated on internal validation and calibration shall be measured (reliability diagram, ECE, Brier score) on internal and external sets. | P0 | PS-15 |
| UNC-002 | A low-confidence threshold for mandatory review shall be set from validation calibration data `[OPEN: OQ-09]`. | P0 | PS-17 |
| UNC-003 | An uncertainty/OOD indicator beyond softmax probability shall be provided (method TD). | P1 | PS-20 |
| UNC-004 | The UI shall show confidence as a calibrated value with plain-language interpretation, not a raw score. | P1 | PS-17 |
| UNC-005 | Calibration shall be re-measured on every external set; degradation shall be reported. | P1 | PS-20 |

---

## 24. Reporting Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| RPT-001 | Every graded or rejected case shall produce a report automatically. | P0 | PS-16 |
| RPT-002 | Report fields: case ID; capture timestamp; quality verdict & reasons; enhancement applied; ICDR grade; referable status; per-grade probabilities; calibrated confidence; uncertainty/OOD/inconsistency flags; lesion summary (types, counts, locations relative to OD/fovea); criteria panel; **annotated image(s)** (Grad-CAM + lesion overlays); referral recommendation; model/pipeline version; reviewer decision & reason (after review); disclaimer. | P0 | PS-16, PS-14 |
| RPT-003 | Reports shall be generated by a deterministic template (no generative text model). | P0 | [ENG], FR-019 |
| RPT-004 | Reports shall contain no patient data beyond what screening and traceability require. | P0 | SEC |
| RPT-005 | A report for a case with missing components shall state which components are missing. | P0 | ERR |

---

## 25. Frontend Requirements

| Screen | User | Purpose | Inputs | Outputs / actions | Failure states |
|---|---|---|---|---|---|
| SCR-01 Capture/Upload | Technician | Submit image | File/capture | Upload confirmation; retry | Unsupported/corrupt file; upload failure |
| SCR-02 Quality Verdict | Technician | Verdict + reason + guidance | IQA output | Retake / proceed | Service unavailable |
| SCR-03 Review Workstation | Ophthalmologist | Single-screen validation | Evidence bundle | Confirm / override (reason) / flag unhelpful explanation | Missing component shown explicitly; flags visible |
| SCR-04 Report | Ophthalmologist, records | Annotated report | Case data | View / export | Generation failure |
| SCR-05 Review Queue | Ophthalmologist | Prioritised worklist | Routing output | Open case | Empty/overloaded queue indication |
| SCR-06 Simulation & Optimization Console | Administrator | Scenarios & optimized plan | Parameters | Run, compare, export | Invalid parameters; run failure |

| ID | Requirement | Pri |
|---|---|---|
| UX-001 | SCR-03 shall display without scrolling on the target review display `[OPEN: display spec]`: original/enhanced toggle, Grad-CAM, lesion overlay toggles, grade, referable flag, confidence, flags, criteria panel, quality verdict, confirm/override controls. | P0 |
| UX-002 | Technician screens shall use non-diagnostic language and never display a DR grade. `[ENG — avoids untrained interpretation]` | P1 |
| UX-003 | Missing evidence shall be shown as an explicit "evidence unavailable" state, never a blank overlay. | P0 |
| UX-004 | Colour shall not be the sole carrier of meaning (flags carry text/icons). | P1 |
| UX-005 | Review time shall be measured automatically from case open to decision. | P0 |
| UX-006 | UI implementation technology `[MOVE TO TECHNICAL DESIGN]`; MATLAB-native UI is preferred for PS-01 alignment (MAT-001). | — |

---

## 26. Backend Requirements

| ID | Requirement | Pri |
|---|---|---|
| BE-001 | Orchestration shall execute stages in order: intake → IQA → (enhance → re-IQA) → anatomy → lesions → grading → confidence/uncertainty → explainability → report → routing → storage. | P0 |
| BE-002 | Each stage shall be independently invocable and testable with defined inputs/outputs (interfaces TD). | P0 |
| BE-003 | Per-stage processing time shall be measured and logged for every case (feeds SIM-004). | P0 |
| BE-004 | A stage failure shall not produce partial outputs presented as complete (ERR table). | P0 |
| BE-005 | Inference shall run locally/on-premise; no external inference service (FR-019). | P0 |
| BE-006 | Service framework, API protocol, and process model `[MOVE TO TECHNICAL DESIGN]`. | — |

---

## 27. Storage Requirements

| ID | Requirement | Pri |
|---|---|---|
| STO-001 | Store per case: original image, enhanced image (if any), all module outputs, report, routing decision, human decision, timings, pipeline/model versions, configuration hash. | P0 |
| STO-002 | Store model artifacts with version, training-data manifest, and model card. | P1 |
| STO-003 | Store simulation runs with full parameter sets, parameter sources, and outputs. | P0 |
| STO-004 | Audit logs shall be append-only for human decisions. | P1 |
| STO-005 | Retention and deletion policy `[OPEN: OQ-10]`. | P1 |
| STO-006 | Schema and storage engine `[MOVE TO TECHNICAL DESIGN]`. | — |

---

## 28. Security & Privacy

| ID | Requirement | Pri |
|---|---|---|
| SEC-001 | Role-based access for Technician, Ophthalmologist, Administrator; each role sees only what its tasks require. | P0 |
| SEC-002 | Authentication required for all roles (mechanism TD). | P0 |
| SEC-003 | Case identifiers shall not embed personal identifiers; de-identification scheme `[OPEN]`. | P0 |
| SEC-004 | Collect only data needed for screening and traceability; no demographic data unless a requirement needs it. | P0 |
| SEC-005 | Public dataset images shall be used only under their licence terms; licence register (DAT-001). | P0 |
| SEC-006 | Data at rest and in transit shall be protected (mechanisms TD) for any deployment beyond the local demo. | P1 |
| SEC-007 | Applicable Indian legal/regulatory requirements (candidates to check: Digital Personal Data Protection Act 2023; medical-device/SaMD rules) `[NEEDS VERIFICATION — no applicability claim is made]`. | P1 (blocking for any real deployment) |
| SEC-008 | No real patient data shall be used in the prototype without appropriate approval. | P0 |

---

## 29. MATLAB Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| MAT-001 | The runtime pipeline (preprocessing, IQA, enhancement, anatomy, lesions, grading inference, Grad-CAM, calibration application, report generation) shall execute in MATLAB. | P0 | PS-01 |
| MAT-002 | Model training in MATLAB (Deep Learning Toolbox) is the default. Training outside MATLAB with import is permitted only after OQ-02 is resolved in favour and only for models passing MAT-006. | P0 | PS-01 |
| MAT-003 | A toolbox-usage map shall show where each PS-listed toolbox is used and why: Image Processing, Computer Vision, Deep Learning, Medical Imaging, Statistics & Machine Learning, Simulink. Whether *all six* must be used `[NEEDS VERIFICATION: OQ-03]`; none shall be used without a genuine function. | P0 | PS-21 |
| MAT-004 | Grad-CAM shall be computed in MATLAB. | P0 | PS-13, PS-01 |
| MAT-005 | Statistical evaluation (CIs, calibration) should use Statistics & Machine Learning Toolbox. | P1 | PS-21 |
| MAT-006 | Any imported model shall show numerical equivalence with its source framework on a fixed test batch within a tolerance defined in TD. | P0 | Reliability |
| MAT-007 | MATLAB release and toolbox versions shall be pinned and recorded. | P1 | Reproducibility |

---

## 30. Simulink Requirements

| ID | Requirement | Pri | Source |
|---|---|---|---|
| SIM-001 | A Simulink model shall represent: patient arrival → capture (incl. recapture loop) → compression/upload over constrained bandwidth → IQA/enhancement → AI processing → routing → ophthalmologist review queue → outcome. | P0 | PS-18 |
| SIM-002 | The model shall be discrete-event/queuing-based; no ML in this module. Discrete-event blocks (e.g., SimEvents) `[NEEDS VERIFICATION: license availability — not in PS tool list]`. | P0 | [ENG] |
| SIM-003 | Parameters: annual volume; operating days/year and hours/day; arrival pattern; cameras per site; capture and recapture times; recapture probability; image size and compression; bandwidth per site; per-stage processing times; number of AI processing servers; routing policy; referable/mandatory-review fraction; review time distribution; number of reviewers and hours. | P0 | PS-18 |
| SIM-004 | Processing-time parameters shall come from BE-003 measurements; review-time parameters from PERF-003 measurements; every other parameter shall carry a source tag or `[PARAMETER TO BE DETERMINED]`. | P0 | [ENG] |
| SIM-005 | Outputs: throughput (patients/day, /year); mean and 95th-percentile waiting time per queue; queue lengths; utilization per resource; backlog growth; recapture load; bottleneck identification. | P0 | PS-18 |
| SIM-006 | Scenarios shall include the 100,000/year baseline and sweeps over bandwidth, volume, AI servers, reviewers, and routing policy, demonstrating upload-, AI-, and review-bound regimes. | P0 | PS-18, PS-19 |
| SIM-007 | Optimization: find resource configurations (cameras, bandwidth, servers, reviewers) that minimise a stated resource objective subject to service constraints (e.g., max waiting time, backlog not growing). Objective form and constraint values `[OPEN: OQ-11]`. | P0 | PS-19 |
| SIM-008 | Optimization outputs shall be ranges (sensitivity to uncertain parameters), not single points. | P1 | [ENG] |
| SIM-009 | Optimization method (sweep, response surface, optimizer) `[MOVE TO TECHNICAL DESIGN]`. | — | — |
| SIM-010 | At least one scenario shall be validated against the analytical M/M/c queue (λ, μ, c, ρ = λ/(cμ)); discrepancies shall be explained. | P0 | Validity |
| SIM-011 | Simulation runs shall be reproducible (seeded) and stored with parameters (STO-003). | P1 | Reproducibility |
| SIM-012 | Visualizations: queue length over time, utilization by resource, waiting-time distributions, bottleneck indicator, optimization frontier. | P1 | PS-19 |

---

## 31. Resource Simulation (scenario definition)

- **Baseline arithmetic (illustrative):** 100,000 patients/year ÷ operating days. At 365 days ≈ 274/day; operating days are a **parameter**, not a fact.
- **Illustrative sweep ranges** (all `[PARAMETER TO BE DETERMINED]` until sourced): bandwidth per site {0.25, 0.5, 1, 2 Mbps}; annual volume {25k, 50k, 100k, 250k}; AI servers {1, 2, 4, 8}; reviewers {1, 2, 4, 8}.
- **Routing policies to compare:** default conservative policy (§21.1) vs. mandatory-only review.
- **Key questions answered:** Which resource binds first at 100k/year? How many reviewers are needed at the measured review time? What bandwidth avoids upload backlog at measured image sizes? How sensitive is the plan to recapture rate?

---

## 32. Non-Functional Requirements

| ID | Category | Requirement | Pri |
|---|---|---|---|
| NFR-001 | Usability | Technician workflow requires no diagnostic knowledge. | P1 |
| NFR-002 | Usability | Review supports PS <30 s (PERF-003). | P0 |
| NFR-003 | Reproducibility | Fixed seeds, pinned versions, data manifests, configuration hashes. | P0 |
| NFR-004 | Maintainability | Modules independently testable (BE-002). | P1 |
| NFR-005 | Observability | All decisions, verdicts, timings and simulation runs logged. | P1 |
| NFR-006 | Reliability | Failure of any stage results in an explicit, logged state (§38). | P0 |
| NFR-007 | Portability | Target OS/hardware for demo and for simulated deployment `[OPEN: OQ-12]`. | P2 |
| NFR-008 | Availability | No PS target; not specified for prototype. | — |
| NFR-009 | Honesty | All reported results include dataset, CI, domain note, and contamination status; unmet targets reported as unmet. | P0 |
| NFR-010 | Offline operation | Inference shall not require internet access. | P1 |

---

## 33. Performance Requirements

| ID | Metric | Definition | Target | Source | Measurement |
|---|---|---|---|---|---|
| PERF-001 | Referable sensitivity | TP/(TP+FN), Referable = ICDR ≥2 | **>90%** | PS-12 | EVAL-001, 95% CI |
| PERF-002 | Referable specificity | TN/(TN+FP) | **>85%** | PS-12 | EVAL-001, 95% CI |
| PERF-003 | Review time | Case open → decision on SCR-03 | **<30 s** | PS-17 | Timed test (TST-008); report median, P90, max; pass statistic `[OPEN: OQ-13]` |
| PERF-004 | Throughput | Patients/year supported by configuration | **≥100,000** | PS-19 | Simulation (SIM-005) |
| PERF-005 | Per-case processing time | Wall-clock per stage and end-to-end on stated hardware | Report; no target `[OPEN]` | [ENG] | BE-003 |
| PERF-006 | QWK (5-class) | Quadratic weighted kappa | Report `[OPEN]` | [ENG] | EVAL |
| PERF-007 | Segmentation | Per-class Dice/IoU; MA lesion-level sensitivity | Report; compare to published `[OPEN]` | [ENG] | EVAL-008 |
| PERF-008 | IQA | False-Gradable, false-Ungradable rates | `[OPEN]` | [ENG] | IQR-005 |
| PERF-009 | Calibration | ECE, Brier | Report `[OPEN]` | PS-15 | UNC-001 |

No numeric target is invented where the PS is silent.

---

## 34. Scalability

| ID | Requirement | Pri |
|---|---|---|
| SCL-001 | District-scale capacity (100,000+/year) shall be demonstrated by simulation parameterised with measured per-case times, not by load-testing the prototype. | P0 |
| SCL-002 | The prototype shall process a batch of cases sequentially without manual intervention, with per-case timing logged. | P1 |
| SCL-003 | The architecture shall not preclude parallel processing across AI servers (the simulation's server-count parameter must map to a realisable configuration). | P2 |

---

## 35. Evaluation Strategy

| ID | Requirement | Pri |
|---|---|---|
| EVAL-001 | **Primary external evaluation:** Messidor-2, exam-grouped, never used in training/selection; report referable Sens/Spec with 95% CIs, AUROC, AUPRC, QWK, per-class metrics. `[NEEDS VERIFICATION: 5-grade label source]` | P0 |
| EVAL-002 | Secondary external: IDRiD grading test (103 images; small-sample CI noted). | P0 |
| EVAL-003 | PS-attached dataset: APTOS held-out split. | P0 |
| EVAL-004 | Portable-domain external: mBRSET if accessible (DAT-013). | P1 |
| EVAL-005 | Operating point and calibration frozen on internal validation before any external run (MLR-003). | P0 |
| EVAL-006 | Results table per dataset (QWK, Sens, Spec, AUROC, Macro-F1, ECE) with CI method stated (method TD). | P0 |
| EVAL-007 | **Ablation:** compare single-technique baselines (e.g., classical-only, single CNN classifier, grader without lesion information, without enhancement, without calibration) against the integrated pipeline on the same splits; exact rows TD. | P0 |
| EVAL-008 | **Published-benchmark comparison:** compare against published results on the same public test sets (e.g., Messidor-2 referable DR; IDRiD lesion segmentation and localization challenge results), stating differences in protocol. | P0 |
| EVAL-009 | Explanation evaluation: XAI-005 overlap + XAI-006 clinician rating. | P0 |
| EVAL-010 | Error analysis: confusion matrix; false-negative referable cases reviewed individually; failure categories reported. | P1 |
| EVAL-011 | Subgroup analysis by dataset/camera where metadata permits. | P2 |
| EVAL-012 | If a PS target is not met, the gap and its likely causes shall be reported, not hidden. | P0 |

---

## 36. Testing Requirements

| ID | Test | Scope | Pri |
|---|---|---|---|
| TST-001 | Unit tests | Each module on fixed inputs incl. edge cases | P1 |
| TST-002 | Integration test | End-to-end on a fixed image set; outputs match stored expected results | P0 |
| TST-003 | Regression test | Metrics on frozen validation set after every model/config change | P1 |
| TST-004 | Gating test | No grade ever produced for Ungradable inputs | P0 |
| TST-005 | Consistency test | Referable flag ⇔ grade ≥2 on all outputs | P0 |
| TST-006 | Data integrity | Split leakage, duplicate, and contamination checks pass | P0 |
| TST-007 | Import equivalence | MAT-006 for any imported model | P0 |
| TST-008 | Timed review test | Reviewers validate a fixed case set on SCR-03; times logged; participant profile recorded (ophthalmologists preferred; proxies disclosed) | P0 |
| TST-009 | Failure injection | Each §38 scenario produces its specified behaviour | P1 |
| TST-010 | Simulation validation | SIM-010 analytical check | P0 |
| TST-011 | Dependency audit | No external AI/LLM/inference calls | P0 |

---

## 37. Acceptance Criteria

| ID | Criterion | Verifies |
|---|---|---|
| AC-001 | Valid images accepted and assigned case IDs; invalid files rejected with specific error. | FR-001, FR-002 |
| AC-002 | 100% of submitted images receive a verdict before downstream stages; 0 grades on Ungradable (TST-004). | FR-003 |
| AC-003 | Every Ungradable verdict carries ≥1 enumerated reason incl. focus/illumination/FOV codes and guidance. | FR-004 |
| AC-004 | Every Borderline image is enhanced with the ENH-001 set and re-checked exactly once. | FR-005 |
| AC-005 | OD, fovea, vessel outputs produced for 100% of Gradable images; metrics reported per SEG-001…003. | FR-006 |
| AC-006 | MA, exudate, hemorrhage, NV outputs produced for 100% of Gradable images; per-class metrics reported; NV validation level disclosed. | FR-007 |
| AC-007 | Grade ∈ {0..4} for every Gradable image; flag consistency 100% (TST-005). | FR-008, FR-009 |
| AC-008 | Grad-CAM map present for 100% of graded cases, computed in MATLAB. | FR-011 |
| AC-009 | Criteria panel present for 100% of graded cases. | FR-012 |
| AC-010 | Calibrated confidence on 100% of graded cases; ECE/Brier/reliability reported; flags shown when triggered. | FR-010, FR-021 |
| AC-011 | Annotated report with all RPT-002 fields generated for 100% of cases; export works. | FR-013, FR-022 |
| AC-012 | SCR-03 shows all UX-001 elements on one screen. | FR-014 |
| AC-013 | Routing follows configured policy; every human decision logged. | FR-015, FR-016 |
| AC-014 | Referable Sens >90% and Spec >85% on primary external set, reported with 95% CI (point estimate is the PS comparison; CI disclosed). If unmet, EVAL-012 applies. | PERF-001/002 |
| AC-015 | Ablation and published-benchmark tables produced (EVAL-007, EVAL-008). | FR-023, PS-24 |
| AC-016 | Simulink model runs the 100k/year baseline and all SIM-006 sweeps with sourced parameters. | FR-017 |
| AC-017 | Optimization returns a configuration meeting stated constraints at ≥100,000/year, with ranges. | FR-018 |
| AC-018 | Clinician rating study completed and summarised; overlap metrics reported where GT exists. | XAI-005, XAI-006 |
| AC-019 | Dependency audit shows no external AI APIs; no hardcoded paths/credentials/thresholds. | FR-019, FR-020 |
| AC-020 | SIH demonstration scenario (§12.3) executes end-to-end on held-out images. | PS-22 |
| AC-021 | Timed review test results reported against <30 s (PERF-003). | PS-17 |

---

## 38. Error Handling

| ID | Scenario | Trigger | Behaviour | User message | Recovery | Logged |
|---|---|---|---|---|---|---|
| ERR-001 | Invalid file | Unsupported/corrupt | Reject at intake | Specific format error | Re-upload | Yes |
| ERR-002 | Ungradable | IQA verdict | Block analysis | Reason + guidance | Recapture | Yes |
| ERR-003 | Ungradable after max retries | Retry limit | Terminal state per OQ-07 | "Could not obtain gradable image" | Manual pathway | Yes |
| ERR-004 | Model/inference failure | Exception/timeout | No grade | "Screening unavailable" | Retry; manual review | Yes |
| ERR-005 | Missing evidence component | Stage failure | Case marked incomplete; mandatory review | "Evidence unavailable: <component>" | Manual review | Yes |
| ERR-006 | Low confidence / OOD / inconsistency | UNC flags | Mandatory review | Flag with explanation | Human review | Yes |
| ERR-007 | Storage/backend unavailable | I/O failure | Hold submission locally or block | Connectivity/storage error | Retry | Yes |
| ERR-008 | Invalid simulation parameters | Validation | Reject run | Parameter error | Correct inputs | Yes |
| ERR-009 | Non-fundus image | IQA | Ungradable | "Not a retinal image" | Recapture | Yes |

---

## 39. Deployment Requirements

| ID | Requirement | Pri |
|---|---|---|
| DEP-001 | Prototype shall run on a single documented host for the SIH demonstration, offline-capable. | P0 |
| DEP-002 | Hardware used for timing measurements shall be documented; timings are hardware-specific. | P0 |
| DEP-003 | PHC/district topologies are modelled in simulation only; no deployment topology is a prototype requirement. | P0 |
| DEP-004 | Packaging/deployment mechanism (e.g., MATLAB app, compiled app, web app server) `[MOVE TO TECHNICAL DESIGN]`. | — |
| DEP-005 | A setup guide shall allow a new machine to reproduce the demo from versioned artifacts. | P1 |

---

## 40. MLOps / Maintainability

| ID | Requirement | Pri |
|---|---|---|
| OPS-001 | Version control for code, configuration, data manifests, and model artifacts (tools TD). | P0 |
| OPS-002 | Every experiment records data version, config, seed, metrics, and model hash. | P1 |
| OPS-003 | Pipeline version identifier appears in every report (RPT-002). | P0 |
| OPS-004 | Changing any threshold requires re-running TST-003 and documenting the result. | P1 |
| OPS-005 | Model cards maintained (MLR-008). | P1 |

---

## 41. Risks

Probabilities are qualitative because no estimation method has been defined.

| ID | Risk | Likelihood | Impact | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-01 | Domain shift: evaluation mostly on clinic-camera images; PS context is portable cameras | Likely | High | Portable-set results vs clinic-set results | mBRSET evaluation (if accessible); disclosure (DAT-014) | Open |
| R-02 | Pixel-level lesion data scarce (IDRiD 81; DDR 757) | Certain | Medium–High | Per-class metrics | Combine sources; augmentation; baseline-first | Open |
| R-03 | **No NV pixel labels** in IDRiD/DDR | Certain | High (PS-10) | Data audit | FGADR/other sources (verify); image-level proxy with disclosure | Open |
| R-04 | External training may be judged non-compliant with "MATLAB-based" | Unclear | High | OQ-02 | MATLAB-native baselines (e.g., MathWorks' ResNet-101 DR example) kept ready | Open |
| R-05 | Clinician raters unavailable for PS-23 and timed review | Likely | High | Outreach status | Early outreach; proxy raters disclosed as proxies | Open |
| R-06 | Data leakage/contamination inflates results | Possible | High | TST-006, DAT-005 | Dedup, registry, exam-level splits | Open |
| R-07 | PS sensitivity/specificity not met on primary external set | Possible | High | EVAL-001 | Operating-point tuning on validation; report honestly | Open |
| R-08 | Grad-CAM highlights spurious regions | Likely | Medium | XAI-005/006 | Disclosure; overlap scoring; lesion overlays alongside | Open |
| R-09 | "Sub-pixel" and "hemorrhage classification" misinterpreted | Possible | Medium | Mentor feedback | OQ-04, OQ-05 | Open |
| R-10 | SimEvents unavailable | Unclear | Medium | License check | Simulink/Stateflow queue implementation | Open |
| R-11 | Scope too large for 3 people and timeline | Likely | High | Level tracking | L1 complete before L2; parallel tracks | Open |
| R-12 | Messidor-2 grade labels not obtainable as needed | Possible | Medium | Download check | IDRiD + APTOS held-out as fallback, disclosed | Open |
| R-13 | Calibration degrades out of domain | Likely | Medium | UNC-005 | Report; conservative routing | Open |

---

## 42. Assumptions

| ID | Assumption | Basis | Status |
|---|---|---|---|
| A-01 | Portable-camera, field-condition capture is the default operating condition | PS-25 | Reasonable engineering assumption |
| A-02 | Technicians are not clinically trained | Persona | Reasonable engineering assumption |
| A-03 | Remote ophthalmologist review via telemedicine | PS-18 wording | Reasonable engineering assumption |
| A-04 | EyeQ "Usable" maps to Borderline | Label semantics | Reasonable; verify during label mapping |
| A-05 | Illustrative simulation ranges (§31) | Scenario design | `[PARAMETER TO BE DETERMINED]` |
| A-06 | Public datasets usable for this non-commercial prototype | Licence terms | `[NEEDS VERIFICATION]` per dataset |
| A-07 | Adequate GPU/compute available | Team | `[NEEDS VERIFICATION]` |
| A-08 | The mirror PS text equals the official PS | Mirror | `[NEEDS VERIFICATION]` (OQ-01) |

---

## 43. Open Questions

| ID | Question | Why it matters | Owner / method | Blocking? |
|---|---|---|---|---|
| OQ-01 | Does sih.gov.in text match the mirror used here? | Source of truth | Team: check portal | Blocking for submission |
| OQ-02 | Is training outside MATLAB (with ONNX/import) acceptable to MathWorks for a "MATLAB-based pipeline"? | Tooling, compliance | Ask MathWorks mentor | Blocking for training stack |
| OQ-03 | Must all six listed toolboxes be used? | MAT-003 | Mentor | Non-blocking |
| OQ-04 | What does "sub-pixel microaneurysm detection" mean operationally (sub-pixel centroid localization? detection of MAs smaller than a pixel after resampling?) | CVR-003 | Mentor + literature | Blocking for MA design |
| OQ-05 | "Hemorrhage classification": presence/extent by region, or morphological type (e.g., dot/blot/flame)? | SEG-005, data needs | Mentor | Blocking for HE design |
| OQ-06 | Clinician rating protocol: scale, number of cases, number/type of raters | PS-23 | Team + advisor | Blocking for AC-018 |
| OQ-07 | Max recapture attempts; terminal action | Workflow | Team + advisor | Non-blocking (configurable) |
| OQ-08 | Is any review-bypass policy acceptable outside simulation? | Safety | Clinical advisor | Blocking only for such a policy |
| OQ-09 | Low-confidence threshold | Routing safety | Data-driven (UNC-002) | Blocking for routing |
| OQ-10 | Data retention/deletion policy | Privacy | Team | Non-blocking for demo |
| OQ-11 | Optimization objective and service constraints (e.g., max wait) | SIM-007 | Team (+ public health input) | Blocking for AC-017 |
| OQ-12 | Target hardware/OS | Timing, deployment | Team | Non-blocking |
| OQ-13 | Pass statistic for <30 s (median? P90? all cases?) | AC-021 | Team; state choice before test | Blocking for AC-021 |
| OQ-14 | Supported image formats/resolutions | FR-001 | Team | Non-blocking |
| OQ-15 | Source of Messidor-2 5-grade labels; IDRiD lesion/grading subset overlap | EVAL-001/002 validity | Dataset documentation | Blocking for EVAL-001 |
| OQ-16 | Access to mBRSET and any NV-labelled dataset (e.g., FGADR) | DAT-012/013 | Apply/check terms | Blocking for NV validation |
| OQ-17 | Applicable Indian regulatory/privacy requirements | SEC-007 | Authoritative legal source | Blocking only for real deployment |

---

## 44. Out of Scope

Regulatory clearance; prospective clinical trials; autonomous diagnosis; DME grading; OCT/OCTA or other modalities; EMR integration; external AI/LLM APIs; generative report text; demographic tuning without verified data; multi-site federated deployment; production security hardening.

---

## 45. Future Scope

- DME assessment; IRMA/venous beading detection; vitreous hemorrhage.
- Prospective evaluation on Indian portable-camera images with ophthalmologist adjudication.
- On-device IQA at the PHC; store-and-forward sync.
- Advanced uncertainty (e.g., conformal prediction); additional explanation methods.
- Regulatory pathway assessment; EMR/telemedicine platform integration.

---

## 46. Technical Dependencies

| Dependency | Needed for | Status |
|---|---|---|
| MATLAB + Image Processing, Computer Vision, Deep Learning, Medical Imaging, Statistics & ML Toolboxes; Simulink | PS-01, PS-21 | Required; versions TD |
| Discrete-event capability (e.g., SimEvents) | SIM-002 | `[NEEDS VERIFICATION]` |
| Datasets per §16.1 | Training/evaluation | Access/licence per DAT-001 |
| GPU compute | Training | `[NEEDS VERIFICATION]` |
| Clinician raters/reviewers | PS-17, PS-23 | `[NEEDS VERIFICATION]` |

**Candidate methods recorded for the Technical Design (not requirements) `[MOVE TO TECHNICAL DESIGN]`:** rule-based QC features + small CNN for IQA; MathWorks ResNet-101/DDR/Grad-CAM example as MATLAB-native grading baseline `[VERIFIED exists]`; EfficientNet/ConvNeXt/ResNet families; RETFound (note: ViT-L, EyePACS in pretraining, Grad-CAM applicability and MATLAB import unverified); ordinal heads (e.g., CORAL) vs. softmax; U-Net-family lesion/vessel segmenters with attention modules; heatmap-regression OD/fovea localization; lesion-guided crops; feature fusion; small ensembles; temperature scaling; OOD scoring (e.g., embedding distance); full-resolution tiling for MAs; loss choices for tiny-lesion recall. Each must win on evidence (MLR-001/002, EVAL-007).

---

## 47. Requirement Traceability Matrix

| PS | Final requirements | Module | Implementation area | Test | Acceptance |
|---|---|---|---|---|---|
| PS-01 | MAT-001, MAT-002, MAT-006, MLR-010 | All | MATLAB runtime | TST-002, TST-007 | AC-008, AC-019 |
| PS-02 | FR-003, IQR-001, CVR-001 | M1 | IQA | TST-004 | AC-002 |
| PS-03 | FR-005, ENH-001…005 | M2 | Enhancement | TST-002 | AC-004 |
| PS-04 | FR-003, FR-004, IQR-007, ERR-002/003 | M1, M9 | IQA + SCR-02 | TST-004, TST-009 | AC-002, AC-003 |
| PS-05 | FR-006, SEG-001, SEG-002 | M3 | Localization | EVAL-008 | AC-005 |
| PS-06 | FR-006, SEG-003 | M3 | Vessel segmentation | EVAL-008 | AC-005 |
| PS-07 | FR-007, SEG-004, CVR-002 | M4 | MA detection | EVAL-008 | AC-006 |
| PS-08 | FR-007, SEG-006 | M4 | Exudate segmentation | EVAL-008 | AC-006 |
| PS-09 | FR-007, SEG-005 | M4 | Hemorrhage | EVAL-008 | AC-006 — **OPEN ITEM (OQ-05)** |
| PS-10 | FR-007, SEG-008, DAT-012, GRD-007 | M4 | NV detection | EVAL | AC-006 — **OPEN ITEM (OQ-16, R-03)** |
| PS-11 | FR-008, GRD-001, GRD-003 | M5 | Grading | TST-005 | AC-007 |
| PS-12 | FR-009, GRD-002, GRD-004, MLR-004, PERF-001/002, EVAL-001…006 | M5, M12 | Grading + evaluation | EVAL-001 | AC-014 |
| PS-13 | FR-011, XAI-001, MLR-009, MAT-004 | M6 | Grad-CAM | TST-002 | AC-008 |
| PS-14 | FR-012, XAI-003, XAI-004 | M6 | Criteria panel | TST-002 | AC-009 |
| PS-15 | FR-010, UNC-001, UNC-002 | M7 | Calibration | EVAL-006 | AC-010 |
| PS-16 | FR-013, RPT-001…005 | M8 | Report | TST-002 | AC-011 |
| PS-17 | FR-014, FR-015, FR-016, UX-001, PERF-003, §21.1 | M9, M10 | Review UI, routing | TST-008 | AC-012, AC-013, AC-021 |
| PS-18 | FR-017, SIM-001…006, SIM-010 | M11 | Simulink model | TST-010 | AC-016 |
| PS-19 | FR-018, SIM-007…009, PERF-004, SCL-001 | M11 | Optimization | TST-010 | AC-017 — **OPEN ITEM (OQ-11)** |
| PS-20 | CVR-003, XAI-005, MLR-003/005, DAT-003…006, NFR-009 | M3–M7, M12 | Methodology | TST-006 | AC-014, AC-018 — sub-pixel **OPEN ITEM (OQ-04)** |
| PS-21 | MAT-003, MAT-005 | All | Toolbox map | Review | AC-019 — **OPEN ITEM (OQ-03)** |
| PS-22 | §12.2 L1, §12.3 | All | Demo | TST-002 | AC-020 |
| PS-23 | XAI-006, EVAL-009 | M6, M12 | Rating study | EVAL-009 | AC-018 — **OPEN ITEM (OQ-06, R-05)** |
| PS-24 | FR-023, MLR-001, EVAL-007, EVAL-008 | M12 | Ablation + benchmarks | EVAL-007/008 | AC-015 |
| PS-25 | DAT-013, DAT-014, EVAL-004, R-01 | M12 | Domain evaluation | EVAL-004 | AC-014 (disclosure) |
| PS-26 | DAT-007, EVAL-003 | M12 | APTOS | EVAL-003 | AC-014 |

---

## 48. Decision Log

| ID | Decision | Reason | Alternatives | Evidence | Status |
|---|---|---|---|---|---|
| DEC-01 | Rule-based IQA baseline before any learned IQA | Defensible comparison; avoid unjustified ML | Learned-first | MLR-001 | Accepted |
| DEC-02 | Explainability = Grad-CAM (PS) + overlap metric + clinician rating | PS-13, PS-20, PS-23 | Heatmap only | PS text | Accepted |
| DEC-03 | Patient/exam-level, source-aware splits; exact+perceptual+structural dedup | Leakage prevention | Image-level split | Standard practice | Accepted |
| DEC-04 | No ML in Simulink module | Queuing problem, not learning | ML demand forecasting | Task analysis | Accepted |
| DEC-05 | HITL with configurable routing; conservative default; bypass policies simulation-only | PS-17 (HITL is PS-stated), PS-19 (capacity optimization) | All-review fixed; low-risk bypass fixed | PS text | Accepted |
| DEC-06 | No architecture locked in PRD; candidates evaluated in TD | PS silent; evidence not yet generated | Lock RETFound/CORAL/etc. | Consolidation rule | Accepted |
| DEC-07 | Runtime pipeline in MATLAB; external training gated on OQ-02 + import equivalence | PS-01 | Fully PyTorch; fully MATLAB | PS text | Accepted (pending OQ-02) |
| DEC-08 | Primary external set Messidor-2; IDRiD/APTOS/mBRSET secondary; EyePACS never "independent" for EyePACS-contaminated models | Contamination & label quality | EyePACS primary | RETFound paper; Messidor-2 composition | Accepted (pending OQ-15) |
| DEC-09 | Original Messidor excluded from training when Messidor-2 is a test set | 1,058 shared images | Use both | Verified composition | Accepted |
| DEC-10 | DRAC22 excluded | UW-OCTA modality | Use for NV | Verified | Accepted |
| DEC-11 | L1 must include every PS module | Never drop PS requirement | Grading-only MVP | PS | Accepted |
| DEC-12 | Referable flag ⇔ grade ≥2 at output; internal disagreement → review | PS definition; consistency | Independent head output | PS-12 | Accepted |
| DEC-13 | Strict ">" for PS thresholds | PS wording | "≥" | PS text | Accepted |
| DEC-14 | Recapture feedback is P0 | PS-04 wording | P1 | PS text | Accepted |
| DEC-15 | M/M/c analytical validation | Multi-server system | M/M/1 | Queuing theory | Accepted |
| DEC-16 | Deterministic report template | Reliability; no external generative models | Generated text | FR-019 | Accepted |
| DEC-17 | Use "DAT-" prefix for data requirements | Avoid clash with DR (diabetic retinopathy) | "DR-" | Clarity | Accepted |

---

## 49. Final Consistency Audit

- [x] Every PS requirement PS-01…PS-26 maps to ≥1 final requirement, test and acceptance criterion; unmapped aspects are marked **OPEN ITEM** (PS-09, PS-10, PS-19 objective, PS-20 sub-pixel, PS-21 scope, PS-23 protocol).
- [x] PS thresholds stated exactly (>90%, >85%, <30 s, 100,000+).
- [x] Grad-CAM, CLAHE/illumination normalization/denoising, ICDR 0–4, Level 2+, HITL, Simulink parameters, and optimization all carried verbatim in intent.
- [x] No architecture, optimizer, hyperparameter, schema, framework, or folder structure prescribed; such items tagged `[MOVE TO TECHNICAL DESIGN]`.
- [x] Every functional requirement has an acceptance criterion; every acceptance criterion traces to a requirement.
- [x] No numeric target invented where the PS is silent; all such values `[OPEN]`.
- [x] Dataset facts verified or tagged `[NEEDS VERIFICATION]`; known leakage/contamination sources registered.
- [x] No clinical-validation, regulatory, diagnostic, or outcome claims; workload-reduction claims limited to labelled simulation.
- [x] No external AI API dependency; configuration externalised.
- [x] Contradictions between the source PRDs resolved explicitly (DEC-05, 07, 08, 09, 10, 11, 12, 13, 14, 15).
- [x] Security/privacy requirements present; regulatory applicability not asserted.
- [x] Risks, assumptions, open questions, out-of-scope, future scope documented.
- [x] Document is standalone: no requirement depends on reading the source PRDs.
