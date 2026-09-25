# NETRA-DR — AI HANDOFF DOCUMENT
# READ THIS FIRST

This file is persistent project memory. A fresh Claude coding context should be able to read **only this file + the current task in IMPLEMENTATION_SCHEMA.md + the relevant existing files** and understand exactly what to do, without asking clarifying questions.

---

## PROJECT

- **Name:** NETRA-DR
- **Problem statement ID:** SIH26038 (Smart India Hackathon)
- **Sponsor:** MathWorks
- **Theme:** Explainable AI system for diabetic retinopathy (DR) screening at rural/PHC scale, India
- **Source documents:** SIH26038 PRD, NETRA-DR Final Model Stack (build order + model list), NETRA-DR Master Build Prompt

## WHAT IS NETRA-DR?

A software prototype that takes a fundus (retinal) photo, checks whether it's usable, extracts retinal structure/lesion evidence, grades diabetic retinopathy severity (ICDR 0–4), decides whether the case is referable, and shows a clinician-checkable explanation — all inside a 30-second review budget concept. Target: sensitivity ≥90% / specificity ≥85% for referable DR (Grade ≥2), measured once on a sealed external test set.

## PROTOTYPE OBJECTIVE

Build a **simple, real, working, presentation-ready prototype** — NOT a production platform.

```text
upload retinal image
        ↓
run pipeline
        ↓
see each stage
        ↓
see final result
```

No authentication, no databases, no microservices, no cloud infra, no Kubernetes, no production APIs, no mobile app — unless the PRD explicitly requires it for the prototype (it does not).

## ARCHITECTURE

```text
Retinal Image
      ↓
PHASE 1 — Intake & Quality Gate
      ↓
PHASE 2 — Retinal Structure Analysis
      ↓
PHASE 3 — DR Grading & Referral Decision
      ↓
PHASE 4 — Explainability & Final Report
      ↓
Single Results Screen
```

Plus a **separate, independent** track: Simulink district-scale workflow simulation (not wired into the per-image pipeline — see SIMULINK section below).

## END-TO-END PIPELINE

```text
Raw image
  → [Phase 1] preprocess + quality gate → quality_label, quality_score, preprocessed_image
      (Reject → STOP, ask for recapture)
  → [Phase 2] structure analysis → vessel_mask, lesion_masks (HE/EX/SE), ma_count
  → [Phase 3] grading → severity_class, probabilities, calibrated confidence
             → decision fusion → referable_decision
  → [Phase 4] Grad-CAM → heatmap_overlay
  → Final report → single results page
```

## PHASES (exact four, do not rename or reorder)

### PHASE 1 — Intake & Quality Gate
- IQA model: Good / Borderline / Reject
- Deterministic preprocessing: FOV crop → resize → CLAHE → normalize
- A Reject-quality image stops the pipeline — never reaches Phase 2

### PHASE 2 — Retinal Structure Analysis
- Vessel segmentation (MATLAB U-Net, trained on DRIVE)
- Lesion segmentation: HE / EX / SE, one binary mask each (MATLAB U-Net, IDRiD+DDR)
- Microaneurysm (MA) detection: classical candidate extraction (top-hat/matched filter) + small CNN false-positive reducer (IDRiD)
- NV (neovascularization) is OPTIONAL, FGADR-only scope — nothing downstream depends on it
- This phase produces **evidence**, it does not decide severity

### PHASE 3 — DR Grading & Referral Decision
- Grading model: ResNet-50 (backup: EfficientNet-B0), ICDR 0–4, softmax, trained on APTOS+DDR
- Calibration: temperature scaling on the validation fold
- Decision fusion: simple logistic regression combining calibrated grade probability + MA count + HE presence + EX area + quality tier → final refer/no-refer
- 3–5 member ensemble (Stage 10 in the full spec) is OPTIONAL for the prototype — if skipped, this must be stated as a documented limitation, never faked
- Report BOTH numbers side by side when evaluated: grade-alone threshold vs. fused decision

### PHASE 4 — Explainability & Final Report
- Grad-CAM (primary) on the frozen grading model
- UI label MUST read **"model attention"** — never "clinical proof"
- Assembles all phase outputs into one single-scroll results page

## ML / MATLAB STRATEGY

Training and inference are strictly separated. Models are trained once in MATLAB, exported, and the website only ever loads a frozen model + reads its contract. The website/prototype **never retrains** and never runs MATLAB training code at launch.

```text
TRAINING SIDE (MATLAB)                  PROTOTYPE SIDE (website)
Dataset                                 Retinal image
  ↓                                       ↓
preprocessing                           preprocessing
  ↓                                       ↓
training                                load frozen model (via contract)
  ↓                                       ↓
validation                              inference
  ↓                                       ↓
test evaluation                         visualization
  ↓                                       ↓
export (ONNX preferred)                 next module
  ↓
model artifact + metadata.json
```

**Export priority order:**
1. Direct ONNX export from MATLAB (`exportONNXNetwork`) — preferred
2. Standard interoperable format
3. MATLAB Compiler SDK / Production Server inference
4. Thin MATLAB Engine API wrapper (last resort — adds a MATLAB runtime dependency to the demo machine)

If export compatibility for a specific model is uncertain, a dedicated validation task must run BEFORE the integration task for that model (see IMPLEMENTATION_SCHEMA.md).

## MODEL CONTRACT

Every MATLAB-trained model ships as two files:

```text
models/<stage_name>/
    <model_artifact>          (e.g. quality_model.onnx)
    metadata.json
```

The inference code reads `metadata.json` and derives preprocessing/postprocessing from it. It never hardcodes image size, normalization, class order, or thresholds.

**Mandatory fields for every model type:**
`model_name, model_version, input_size, channels, normalization, model_file, framework, training_dataset, preprocessing, eval_metrics`

**Additional mandatory fields by model type:**

| Model type | Extra mandatory fields |
|---|---|
| Classifier (quality, grading) | `class_labels`, `output_format` (e.g. `softmax_probs`), `threshold` |
| Segmentation (vessel, HE/EX/SE) | `mask_labels`, `output_format` (`binary_mask` / `multi_channel_mask`), `mask_resolution` |
| MA detector (hybrid) | `candidate_extraction_method`, `fp_reducer_model_file`, `output_format` (`candidate_list_with_scores`) |

No task may hardcode a value that belongs in `metadata.json`.

## DATASETS

```text
data/
├── raw/            MATLAB side only
├── processed/      MATLAB side only
├── train/          MATLAB side only
├── validation/     MATLAB side only
├── test/           SEALED — opened exactly once, after everything is frozen; website never touches it
└── demo/           the ONLY folder the live website ever reads
```

Reference datasets per model (from the Final Model Stack spec):
- IQA: DDR ungradable class (+ EyeQ if available)
- Vessel segmentation: DRIVE (train/test), cross-checked on STARE/CHASE_DB1
- MA detection: IDRiD (81 MA-masked images), FROC-scored
- HE/EX/SE segmentation: IDRiD + DDR (reported separately, never pooled)
- NV (optional): FGADR Seg-set only
- Grading: APTOS 2019 + DDR grading set
- Sealed test: Messidor-2 (Krause grades) + IDRiD grading test split (103 images)

## DATA FLOW

`data/demo/` (5–8 hand-picked images: one Good-quality, one Borderline/Reject-quality, one Grade-0, one or two other severities, one visually "hard" case for the heatmap) is the only dataset the running website reads. Training/validation/sealed-test data never enter the website's code path.

## REPOSITORY STRUCTURE

```text
netra-dr/
├── data/
│   └── demo/
├── models/
│   ├── quality/
│   ├── vessel_seg/
│   ├── lesion_seg/
│   ├── ma_detector/
│   └── grading/
├── matlab/               training scripts, one per stage — never imported by the website
├── pipeline/
│   ├── contract.py       reads/validates metadata.json, shared by all phases
│   ├── preprocessing.py  Phase 1 deterministic preprocessing
│   ├── quality.py        Phase 1 model inference
│   ├── structure.py      Phase 2 (vessel + lesion + MA)
│   ├── grading.py        Phase 3 (grading + calibration)
│   ├── decision.py       Phase 3 (decision fusion)
│   ├── explain.py        Phase 4 (Grad-CAM)
│   └── report.py         assembles final result object
├── app/
│   ├── app.py             web server, one command to launch
│   └── templates/
│       └── index.html     single results page
├── tests/
├── docs/
│   ├── HANDOFF.md
│   ├── IMPLEMENTATION_SCHEMA.md
│   └── TASKS.md
├── configs/
└── README.md
```

## PROTOTYPE STACK

Small Python backend (Flask or FastAPI) calling `pipeline/` functions in phase order, rendering one HTML template. No login, no database, no queues — each upload runs the pipeline in memory. One launch command: `python app/app.py` → browser → upload → results.

## DEMO REQUIREMENTS

- One command to launch the full prototype
- The demo must run start-to-finish on every image in `data/demo/` without crashing
- Every phase must produce a visible, demonstrable result (score, overlay, or heatmap) — not just numbers in a log
- Training commands are always separate from the demo launch command

## ENGINEERING RULES

- Use project-relative paths only. Never hardcode `C:\Users\...` or any machine-specific path.
- Never assume a package is installed, a model path exists, an image shape, class indices, or GPU availability. Provide a CPU-compatible path.
- Never overwrite an existing file blindly — inspect before modifying.
- Minimize dependencies: before adding one, confirm the existing stack cannot do it.
- Never build production infrastructure (auth, DB, microservices, cloud, K8s) unless the PRD explicitly requires it for the prototype — it does not.

## ML RULES

- Do not report a metric that was not actually measured.
- Do not hardcode convincing-looking predictions.
- Do not claim an ensemble exists if only one model is implemented — state it as a limitation instead.
- Do not claim NV detection outside FGADR scope.
- Do not invent hemorrhage subtypes (flame/dot-blot/deep) — presence, count, area, quadrant only.
- Do not use MC-dropout at inference — use the fixed deterministic ensemble if one is built at all.
- Never present Grad-CAM/model attention as clinical proof.
- Report sensitivity/specificity only as: *"At the operating point selected on the validation fold, the frozen system measured X% sensitivity / Y% specificity on the sealed test set, 95% CI [..]."* Report it twice: gradable-only and including auto-referred ungradable images.

## DATA-LEAKAGE RULES

- Verify train/validation/test separation before training any model.
- Run a perceptual-hash near-duplicate check across APTOS/IDRiD/DDR before building splits.
- Use patient-level (not image-level) splitting where metadata supports it.
- Never tune on the sealed test set. Open it exactly once, after architecture, threshold, and ablations are frozen.

## ERROR-HANDLING RULES

Every model-integration task must explicitly handle: missing model artifact, corrupted model file, wrong image dimensions, unsupported image format, preprocessing mismatch (image doesn't match `metadata.json`), class-index mismatch, ONNX incompatibility, missing dependency, missing MATLAB runtime, CPU/GPU differences, empty prediction, invalid segmentation mask. Pattern: **detect → produce an understandable error → do not silently continue with invalid output.**

## WHAT HAS BEEN COMPLETED

_(update this section after each completed task — see TASKS.md for the live tracker)_

- Nothing implemented yet. Control files (HANDOFF.md, IMPLEMENTATION_SCHEMA.md, TASKS.md) have just been generated.

## CURRENT TASK

TASK-001 (see IMPLEMENTATION_SCHEMA.md and TASKS.md)

## NEXT TASK

TASK-002

## HOW TO WORK ON A TASK

1. Read this file (HANDOFF.md) in full.
2. Read ONLY the current task block in IMPLEMENTATION_SCHEMA.md.
3. Read ONLY the existing files that task names under "Files to modify" or "Needs".
4. Do ONLY that task. Do not start the next task. Do not "prepare" future phases.
5. Run the task's Validation steps.
6. Confirm the Done-when condition is met.
7. Update TASKS.md: mark current task completed, move to Completed Tasks, set the next task as Current Task, and the one after that as Next Task. Record any decision made.
8. Update the "WHAT HAS BEEN COMPLETED" section of this file with one line.
9. Stop.

## WHAT TO DO AFTER COMPLETING A TASK

Stop. Do not automatically continue to the next task, even if it looks trivial. A new Claude context will pick up the next task using this same handoff procedure.

## THINGS YOU MUST NEVER DO

- Never redesign the architecture without a documented, genuine technical blocker.
- Never merge two phases or two major tasks into one coding session.
- Never retrain a model inside the website/inference code path.
- Never touch the sealed test set before it's explicitly time to (see DATA-LEAKAGE RULES).
- Never fabricate metrics, predictions, or ensemble behavior.
- Never add production infrastructure not required by the PRD.
- Never hardcode machine-specific paths.
- Never call Grad-CAM output "clinical proof."
- Never start the next task automatically after finishing the current one.

## OUTPUT FILE MAP

See the "Output File Map" section at the end of IMPLEMENTATION_SCHEMA.md for the full task → file mapping.

## KNOWN CONFLICTS / DECISIONS RECORDED

- The Master Build Prompt's 36-section template lists many optional production-grade practices (advanced logging, exhaustive per-step prompts). Resolved by: keeping this handoff and the schema focused on what the PRD actually requires for a hackathon prototype, per that same prompt's own Section 4 ("aggressively avoid production complexity"). No architecture component was dropped — only unnecessary process overhead.
- The Final Model Stack's Stage 10 (3–5 member ensemble) and Stage 6 (NV, FGADR-only) are both explicitly marked OPTIONAL in this schema, consistent with the source document's own framing of NV as scope-limited and the ensemble as something to state as a limitation rather than fake. This is not a silent removal — it is documented here and in IMPLEMENTATION_SCHEMA.md.
- Simulink workflow simulation (Stage 12) is kept as a separate, non-blocking track, per the Final Model Stack's own step ordering (Step 13, after the per-image pipeline is frozen) and the Master Build Prompt's Section 9 instruction not to wire it into per-image inference.
