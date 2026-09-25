# NETRA-DR — IMPLEMENTATION SCHEMA
## Atomic, executable task specification

This document is the complete build plan for the NETRA-DR prototype. It complements `HANDOFF.md` (persistent project memory) and `TASKS.md` (live progress tracker).

**Core principle:** every task below is atomic, independent, self-contained, testable, and small enough for one fresh Claude coding context to complete without confusion. A task never spans more than one phase. A task never silently prepares future work.

**Fresh-context rule for every task:** a new Claude context reading only `HANDOFF.md` + one task block below + the files that task names should never need to ask what the project is, what phase this is, what the input/output is, which files to touch, which model is used, what command to run, or how to know it's done. If a task fails this test, it is not atomic enough.

**Master prompts:** every task below now ends with a **MASTER PROMPT** block — a single, ready-to-paste prompt for a fresh Claude coding context. It restates that task's objective, input, output, files, implementation steps, commands, validation, done-when condition, and do-nots in one self-contained block, plus a reminder to read `docs/HANDOFF.md` first, a failure-handling rule, a git checkpoint command, and an explicit "update TASKS.md and stop" instruction. To hand off work: copy everything inside one task's master-prompt fence into a new Claude context, along with `docs/HANDOFF.md` and any files that task's "Files to modify" section names.

---

## Phase-to-Task Map

```text
PHASE 0 — PROJECT FOUNDATION           TASK-001, TASK-002
PHASE 1 — INTAKE & QUALITY GATE        TASK-003, TASK-004, TASK-005
PHASE 2 — RETINAL STRUCTURE ANALYSIS   TASK-006, TASK-007, TASK-008, TASK-009
PHASE 3 — DR GRADING & REFERRAL        TASK-010, TASK-011, TASK-012, TASK-013
PHASE 4 — EXPLAINABILITY & REPORT      TASK-014, TASK-015, TASK-016
INTEGRATION — WEBSITE & DEMO           TASK-017, TASK-018, TASK-019, TASK-020
SIMULINK — SEPARATE TRACK              TASK-021
```

---

### TASK-001 | Create repository structure

**Layer/Phase:** Phase 0 — Project Foundation

**What:** Create the full minimal repository skeleton (empty folders + placeholder `.gitkeep` files where needed) with no logic yet.

**Why:** Every later task assumes these paths exist. Doing this first avoids each task re-deciding project layout.

**Context:** First task of the whole project. Nothing exists yet.

**Input:**
- None (fresh repository)

**Output:**
- Full directory tree, committed, empty apart from placeholders

**Files to create:**
```text
netra-dr/
├── data/demo/.gitkeep
├── models/quality/.gitkeep
├── models/vessel_seg/.gitkeep
├── models/lesion_seg/.gitkeep
├── models/ma_detector/.gitkeep
├── models/grading/.gitkeep
├── matlab/.gitkeep
├── pipeline/__init__.py
├── app/__init__.py
├── app/templates/.gitkeep
├── tests/__init__.py
├── docs/.gitkeep
├── configs/.gitkeep
├── requirements.txt   (empty for now)
└── README.md          (project name + one-paragraph description only)
```

**Files to modify:**
- None

**Needs:**
- None

**Implementation:**
1. Create the directory tree exactly as listed above.
2. Add a one-paragraph `README.md` describing NETRA-DR and pointing to `docs/HANDOFF.md` as the entry point for contributors.
3. Leave `requirements.txt` empty — later tasks append to it as dependencies are actually needed.

**Commands:**
```bash
mkdir -p data/demo models/quality models/vessel_seg models/lesion_seg models/ma_detector models/grading matlab pipeline app/templates tests docs configs
touch data/demo/.gitkeep models/quality/.gitkeep models/vessel_seg/.gitkeep models/lesion_seg/.gitkeep models/ma_detector/.gitkeep models/grading/.gitkeep matlab/.gitkeep app/templates/.gitkeep docs/.gitkeep configs/.gitkeep
touch pipeline/__init__.py app/__init__.py tests/__init__.py requirements.txt README.md
```

**Validation:**
1. `find netra-dr -type d` shows every directory listed above.
2. No file contains any logic yet — this task is structure only.

**Expected result:** An empty, correctly-shaped repository that every later task can build into without restructuring.

**Done when:** Directory tree matches exactly, `README.md` exists with a short description, repository is committed.

**Do NOT:**
- Write any pipeline logic.
- Add dependencies to `requirements.txt` yet.
- Create model files or metadata — that happens per-model, later.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-001 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: This is the first task of the project. Nothing has been built yet.

TASK: TASK-001 | Create repository structure
LAYER/PHASE: Phase 0 — Project Foundation

OBJECTIVE:
Create the full minimal repository skeleton (empty folders + placeholder `.gitkeep` files where needed) with no logic yet. Every later task assumes these paths exist. Doing this first avoids each task re-deciding project layout.

CONTEXT — where this fits:
First task of the whole project. Nothing exists yet.

INPUT:
- None (fresh repository)

EXPECTED OUTPUT:
- Full directory tree, committed, empty apart from placeholders

FILES TO CREATE:
```text
netra-dr/
├── data/demo/.gitkeep
├── models/quality/.gitkeep
├── models/vessel_seg/.gitkeep
├── models/lesion_seg/.gitkeep
├── models/ma_detector/.gitkeep
├── models/grading/.gitkeep
├── matlab/.gitkeep
├── pipeline/__init__.py
├── app/__init__.py
├── app/templates/.gitkeep
├── tests/__init__.py
├── docs/.gitkeep
├── configs/.gitkeep
├── requirements.txt   (empty for now)
└── README.md          (project name + one-paragraph description only)
```

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- None

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Create the directory tree exactly as listed above.
2. Add a one-paragraph `README.md` describing NETRA-DR and pointing to `docs/HANDOFF.md` as the entry point for contributors.
3. Leave `requirements.txt` empty — later tasks append to it as dependencies are actually needed.

COMMANDS:
```bash
mkdir -p data/demo models/quality models/vessel_seg models/lesion_seg models/ma_detector models/grading matlab pipeline app/templates tests docs configs
touch data/demo/.gitkeep models/quality/.gitkeep models/vessel_seg/.gitkeep models/lesion_seg/.gitkeep models/ma_detector/.gitkeep models/grading/.gitkeep matlab/.gitkeep app/templates/.gitkeep docs/.gitkeep configs/.gitkeep
touch pipeline/__init__.py app/__init__.py tests/__init__.py requirements.txt README.md
```

VALIDATION / TEST PROCEDURE:
1. `find netra-dr -type d` shows every directory listed above.
2. No file contains any logic yet — this task is structure only.

EXPECTED RESULT:
An empty, correctly-shaped repository that every later task can build into without restructuring.

DONE WHEN:
Directory tree matches exactly, `README.md` exists with a short description, repository is committed.

DO NOT:
- Write any pipeline logic.
- Add dependencies to `requirements.txt` yet.
- Create model files or metadata — that happens per-model, later.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-001: Create repository structure"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-002 | Define and implement the model contract

**Layer/Phase:** Phase 0 — Project Foundation

**What:** Implement `pipeline/contract.py`: a small module that loads and validates a model's `metadata.json`, so every later phase reads models the same way instead of hardcoding assumptions.

**Why:** This is the single mechanism that lets MATLAB-trained models plug into the website without scattered, inconsistent preprocessing code. Must exist before any model integration task.

**Context:** Sits under `pipeline/`, imported by every phase module from Phase 1 onward.

**Input:**
- A path to a model directory, e.g. `models/quality/`

**Output:**
- A validated Python object/dict with all contract fields, or a clear error if the contract is invalid or incomplete

**Files to create:**
- `pipeline/contract.py`
- `tests/test_contract.py`
- `docs/model_contract_spec.md` (copy of the mandatory-fields table from HANDOFF.md, kept next to the code)

**Files to modify:**
- `requirements.txt` (add whatever JSON-schema/validation library, if any, is actually needed — plain `json` + manual checks is sufficient and preferred)

**Needs:**
- TASK-001

**Implementation:**
1. Define the mandatory core fields (from HANDOFF.md): `model_name, model_version, input_size, channels, normalization, model_file, framework, training_dataset, preprocessing, eval_metrics`.
2. Define per-type extra mandatory fields: classifier → `class_labels, output_format, threshold`; segmentation → `mask_labels, output_format, mask_resolution`; MA detector → `candidate_extraction_method, fp_reducer_model_file, output_format`.
3. Implement `load_contract(model_dir: str, model_type: str) -> dict` that reads `metadata.json`, checks all required fields for that type are present, and raises a clear, specific error naming the missing field(s) if not.
4. Implement `resolve_model_path(model_dir, contract) -> str` that joins `model_dir` with `contract["model_file"]` and confirms the file exists (raise a clear error if not — do not silently continue).
5. No inference logic here — this module only loads and validates the contract.

**Commands:**
```bash
pip install -r requirements.txt
python -m pytest tests/test_contract.py
```

**Validation:**
1. Create one dummy `metadata.json` (classifier type, missing one required field on purpose) under a temp/test model directory.
2. `load_contract` raises a clear error naming exactly the missing field.
3. Create a second, complete dummy `metadata.json` — `load_contract` returns the parsed dict successfully.
4. `resolve_model_path` on a directory with no actual model file raises a clear "model artifact not found" error.

**Expected result:** A small, well-tested module that every later phase imports; no phase task will need to write its own metadata-parsing logic.

**Done when:** `pytest tests/test_contract.py` passes, covering: valid contract loads, missing-field contract fails with a named field, missing model file fails clearly.

**Do NOT:**
- Implement any actual model inference here.
- Hardcode any specific model's field values into this generic module.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-002 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure).

TASK: TASK-002 | Define and implement the model contract
LAYER/PHASE: Phase 0 — Project Foundation

OBJECTIVE:
Implement `pipeline/contract.py`: a small module that loads and validates a model's `metadata.json`, so every later phase reads models the same way instead of hardcoding assumptions. This is the single mechanism that lets MATLAB-trained models plug into the website without scattered, inconsistent preprocessing code. Must exist before any model integration task.

CONTEXT — where this fits:
Sits under `pipeline/`, imported by every phase module from Phase 1 onward.

INPUT:
- A path to a model directory, e.g. `models/quality/`

EXPECTED OUTPUT:
- A validated Python object/dict with all contract fields, or a clear error if the contract is invalid or incomplete

FILES TO CREATE:
- `pipeline/contract.py`
- `tests/test_contract.py`
- `docs/model_contract_spec.md` (copy of the mandatory-fields table from HANDOFF.md, kept next to the code)

FILES TO MODIFY:
- `requirements.txt` (add whatever JSON-schema/validation library, if any, is actually needed — plain `json` + manual checks is sufficient and preferred)

DEPENDENCIES (must already be done):
- TASK-001

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Define the mandatory core fields (from HANDOFF.md): `model_name, model_version, input_size, channels, normalization, model_file, framework, training_dataset, preprocessing, eval_metrics`.
2. Define per-type extra mandatory fields: classifier → `class_labels, output_format, threshold`; segmentation → `mask_labels, output_format, mask_resolution`; MA detector → `candidate_extraction_method, fp_reducer_model_file, output_format`.
3. Implement `load_contract(model_dir: str, model_type: str) -> dict` that reads `metadata.json`, checks all required fields for that type are present, and raises a clear, specific error naming the missing field(s) if not.
4. Implement `resolve_model_path(model_dir, contract) -> str` that joins `model_dir` with `contract["model_file"]` and confirms the file exists (raise a clear error if not — do not silently continue).
5. No inference logic here — this module only loads and validates the contract.

COMMANDS:
```bash
pip install -r requirements.txt
python -m pytest tests/test_contract.py
```

VALIDATION / TEST PROCEDURE:
1. Create one dummy `metadata.json` (classifier type, missing one required field on purpose) under a temp/test model directory.
2. `load_contract` raises a clear error naming exactly the missing field.
3. Create a second, complete dummy `metadata.json` — `load_contract` returns the parsed dict successfully.
4. `resolve_model_path` on a directory with no actual model file raises a clear "model artifact not found" error.

EXPECTED RESULT:
A small, well-tested module that every later phase imports; no phase task will need to write its own metadata-parsing logic.

DONE WHEN:
`pytest tests/test_contract.py` passes, covering: valid contract loads, missing-field contract fails with a named field, missing model file fails clearly.

DO NOT:
- Implement any actual model inference here.
- Hardcode any specific model's field values into this generic module.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-002: Define and implement the model contract"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-003 | Preprocessing function (no model)

**Layer/Phase:** Phase 1 — Intake & Quality Gate

**What:** Implement `pipeline/preprocessing.py`: FOV crop → resize → CLAHE → normalize, applied deterministically to any input image. No ML model involved.

**Why:** This step runs identically for every image regardless of quality outcome, and is a dependency of both the quality model input and everything downstream.

**Context:** First half of Phase 1. Runs before the quality-gate model exists in the code path (order matters conceptually — the raw image is fed to the quality model, but the *cleaned* image is what proceeds to Phase 2 onward — see TASK-004 for how the two connect).

**Input:**
- Raw fundus image (jpg/png), arbitrary resolution and aspect ratio

**Output:**
- `preprocessed_image`: a normalized image array of the target size (target size itself should come from configuration, not be hardcoded — see `configs/`)

**Files to create:**
- `pipeline/preprocessing.py`
- `tests/test_preprocessing.py`
- `configs/preprocessing.json` (target size, CLAHE clip limit, etc. — no magic numbers in code)

**Files to modify:**
- `requirements.txt` (add image-processing library, e.g. `opencv-python`, `numpy`, `Pillow`)

**Needs:**
- TASK-001

**Implementation:**
1. Implement `crop_fov(image) -> image`: crop to the circular field-of-view bounding box (remove black border).
2. Implement `resize(image, target_size) -> image`.
3. Implement `apply_clahe(image) -> image`: contrast-limited adaptive histogram equalization on the appropriate channel.
4. Implement `normalize(image) -> image`: scale to the range specified in `configs/preprocessing.json`.
5. Implement `preprocess(image, config_path="configs/preprocessing.json") -> image` that chains the above in order.
6. Handle unsupported formats and unreadable files with a clear error — do not silently return a blank image.

**Commands:**
```bash
pip install opencv-python numpy Pillow
python -m pytest tests/test_preprocessing.py
```

**Validation:**
1. Run `preprocess()` on one real demo image (place a single sample under `tests/fixtures/` for this test only — not the final demo set) — confirm output shape matches `target_size` from config.
2. Run on a corrupted/non-image file — confirm a clear error is raised, not a crash with an unrelated stack trace.
3. Visually inspect one before/after pair (save both to `tests/fixtures/output/` and view them) — confirm the FOV crop and CLAHE visibly improved contrast without distorting the image.

**Expected result:** A pure function that turns any raw fundus photo into a standardized array ready for model input, with no ML involved.

**Done when:** Tests pass and a visual before/after pair confirms correct behavior.

**Do NOT:**
- Call any model here.
- Hardcode target size or CLAHE parameters directly in code — they belong in `configs/preprocessing.json`.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-003 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract).

TASK: TASK-003 | Preprocessing function (no model)
LAYER/PHASE: Phase 1 — Intake & Quality Gate

OBJECTIVE:
Implement `pipeline/preprocessing.py`: FOV crop → resize → CLAHE → normalize, applied deterministically to any input image. No ML model involved. This step runs identically for every image regardless of quality outcome, and is a dependency of both the quality model input and everything downstream.

CONTEXT — where this fits:
First half of Phase 1. Runs before the quality-gate model exists in the code path (order matters conceptually — the raw image is fed to the quality model, but the *cleaned* image is what proceeds to Phase 2 onward — see TASK-004 for how the two connect).

INPUT:
- Raw fundus image (jpg/png), arbitrary resolution and aspect ratio

EXPECTED OUTPUT:
- `preprocessed_image`: a normalized image array of the target size (target size itself should come from configuration, not be hardcoded — see `configs/`)

FILES TO CREATE:
- `pipeline/preprocessing.py`
- `tests/test_preprocessing.py`
- `configs/preprocessing.json` (target size, CLAHE clip limit, etc. — no magic numbers in code)

FILES TO MODIFY:
- `requirements.txt` (add image-processing library, e.g. `opencv-python`, `numpy`, `Pillow`)

DEPENDENCIES (must already be done):
- TASK-001

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Implement `crop_fov(image) -> image`: crop to the circular field-of-view bounding box (remove black border).
2. Implement `resize(image, target_size) -> image`.
3. Implement `apply_clahe(image) -> image`: contrast-limited adaptive histogram equalization on the appropriate channel.
4. Implement `normalize(image) -> image`: scale to the range specified in `configs/preprocessing.json`.
5. Implement `preprocess(image, config_path="configs/preprocessing.json") -> image` that chains the above in order.
6. Handle unsupported formats and unreadable files with a clear error — do not silently return a blank image.

COMMANDS:
```bash
pip install opencv-python numpy Pillow
python -m pytest tests/test_preprocessing.py
```

VALIDATION / TEST PROCEDURE:
1. Run `preprocess()` on one real demo image (place a single sample under `tests/fixtures/` for this test only — not the final demo set) — confirm output shape matches `target_size` from config.
2. Run on a corrupted/non-image file — confirm a clear error is raised, not a crash with an unrelated stack trace.
3. Visually inspect one before/after pair (save both to `tests/fixtures/output/` and view them) — confirm the FOV crop and CLAHE visibly improved contrast without distorting the image.

EXPECTED RESULT:
A pure function that turns any raw fundus photo into a standardized array ready for model input, with no ML involved.

DONE WHEN:
Tests pass and a visual before/after pair confirms correct behavior.

DO NOT:
- Call any model here.
- Hardcode target size or CLAHE parameters directly in code — they belong in `configs/preprocessing.json`.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-003: Preprocessing function (no model)"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-004 | Integrate the IQA (quality) model

**Layer/Phase:** Phase 1 — Intake & Quality Gate

**What:** Implement `pipeline/quality.py`: load the quality-gate model via the contract (TASK-002), run inference on a raw image, and return the quality decision.

**Why:** This is the first ML step in the live pipeline and the gate that decides whether an image proceeds at all.

**Context:** Second half of Phase 1. Depends on both the contract module and the preprocessing module.

**Input:**
- Raw fundus image
- `models/quality/quality_model.onnx` + `models/quality/metadata.json` (must already exist — if not, this task's validation will surface that clearly rather than pretending it works)

**Output:**
- `quality_label` (one of the contract's `class_labels`, e.g. Reject/Borderline/Good)
- `quality_score` (confidence float)
- `preprocessed_image` (from TASK-003, only computed if not Reject — still return it for display even on Reject, since the UI shows both)

**Files to create:**
- `pipeline/quality.py`
- `tests/test_quality.py`

**Files to modify:**
- `requirements.txt` (add ONNX runtime, e.g. `onnxruntime`)

**Needs:**
- TASK-002, TASK-003

**Implementation:**
1. `run_quality_gate(image_path, model_dir="models/quality") -> dict` with keys `quality_label, quality_score, preprocessed_image`.
2. Load contract via `pipeline.contract.load_contract(model_dir, "classifier")`.
3. Resize/normalize the raw image according to the contract's own `input_size`/`normalization` (this may differ from the general preprocessing target size — the contract is authoritative for what the model itself expects).
4. Run ONNX inference, map output indices to `class_labels` from the contract.
5. Separately call `pipeline.preprocessing.preprocess()` (TASK-003) to produce the `preprocessed_image` that downstream phases will use.
6. If `model_dir` has no model file yet, raise a clear "model artifact missing — Phase 1 cannot run" error rather than fabricating a result.

**Commands:**
```bash
pip install onnxruntime
python -m pytest tests/test_quality.py
```

**Validation:**
1. With no model file present: confirm the clear "model artifact missing" error appears (this is expected until the MATLAB team delivers the exported model — this task does NOT include training or exporting the model).
2. Once a model file is placed (by whoever finishes MATLAB export — tracked separately, not in this task): run on one Good demo image and one Reject demo image, confirm correct labels and that `preprocessed_image` is returned for both.

**Expected result:** A single function that returns everything Phase 1 needs to display, failing loudly and specifically if the model isn't there yet.

**Done when:** The missing-model error path is verified, and (once a real model artifact exists) inference runs correctly on at least one Good and one Reject sample image.

**Do NOT:**
- Fabricate a quality label if the model is missing.
- Retrain or fine-tune anything here — this task only performs inference.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-004 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)).

TASK: TASK-004 | Integrate the IQA (quality) model
LAYER/PHASE: Phase 1 — Intake & Quality Gate

OBJECTIVE:
Implement `pipeline/quality.py`: load the quality-gate model via the contract (TASK-002), run inference on a raw image, and return the quality decision. This is the first ML step in the live pipeline and the gate that decides whether an image proceeds at all.

CONTEXT — where this fits:
Second half of Phase 1. Depends on both the contract module and the preprocessing module.

INPUT:
- Raw fundus image
- `models/quality/quality_model.onnx` + `models/quality/metadata.json` (must already exist — if not, this task's validation will surface that clearly rather than pretending it works)

EXPECTED OUTPUT:
- `quality_label` (one of the contract's `class_labels`, e.g. Reject/Borderline/Good)
- `quality_score` (confidence float)
- `preprocessed_image` (from TASK-003, only computed if not Reject — still return it for display even on Reject, since the UI shows both)

FILES TO CREATE:
- `pipeline/quality.py`
- `tests/test_quality.py`

FILES TO MODIFY:
- `requirements.txt` (add ONNX runtime, e.g. `onnxruntime`)

DEPENDENCIES (must already be done):
- TASK-002, TASK-003

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_quality_gate(image_path, model_dir="models/quality") -> dict` with keys `quality_label, quality_score, preprocessed_image`.
2. Load contract via `pipeline.contract.load_contract(model_dir, "classifier")`.
3. Resize/normalize the raw image according to the contract's own `input_size`/`normalization` (this may differ from the general preprocessing target size — the contract is authoritative for what the model itself expects).
4. Run ONNX inference, map output indices to `class_labels` from the contract.
5. Separately call `pipeline.preprocessing.preprocess()` (TASK-003) to produce the `preprocessed_image` that downstream phases will use.
6. If `model_dir` has no model file yet, raise a clear "model artifact missing — Phase 1 cannot run" error rather than fabricating a result.

COMMANDS:
```bash
pip install onnxruntime
python -m pytest tests/test_quality.py
```

VALIDATION / TEST PROCEDURE:
1. With no model file present: confirm the clear "model artifact missing" error appears (this is expected until the MATLAB team delivers the exported model — this task does NOT include training or exporting the model).
2. Once a model file is placed (by whoever finishes MATLAB export — tracked separately, not in this task): run on one Good demo image and one Reject demo image, confirm correct labels and that `preprocessed_image` is returned for both.

EXPECTED RESULT:
A single function that returns everything Phase 1 needs to display, failing loudly and specifically if the model isn't there yet.

DONE WHEN:
The missing-model error path is verified, and (once a real model artifact exists) inference runs correctly on at least one Good and one Reject sample image.

DO NOT:
- Fabricate a quality label if the model is missing.
- Retrain or fine-tune anything here — this task only performs inference.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-004: Integrate the IQA (quality) model"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-005 | PHASE 1 CHECKPOINT

**Layer/Phase:** Phase 1 — checkpoint/validation

**What:** Verify Phase 1 end-to-end on real demo images, and stop downstream flow correctly on Reject.

**Why:** Every phase must be demonstrable before the next phase begins.

**Context:** Closes out Phase 1 before Phase 2 work starts.

**Input:**
- At least 2 images in `data/demo/`: one expected Good/Borderline, one expected Reject

**Output:**
- A short written checkpoint result (see format below), saved to `docs/checkpoints/phase1.md`

**Files to create:**
- `docs/checkpoints/phase1.md`
- `data/demo/` populated with the first 2 real images for this checkpoint (more images are added in later checkpoints/tasks as needed)

**Files to modify:**
- None

**Needs:**
- TASK-004

**Implementation:**
1. Run `run_quality_gate()` on each demo image.
2. Confirm the Reject-labeled image's result is one that a caller (the future website) would correctly stop on — i.e., the returned `quality_label` clearly signals "do not proceed."
3. Write the checkpoint file using this format:
```text
PHASE RESULT — PHASE 1
Input: <image filenames>
Output: quality_label, quality_score, preprocessed_image (per image)
Model: quality_gate (see models/quality/metadata.json for version)
Dataset: DDR ungradable subset (per contract)
Metric: not yet measured — no eval_metrics recorded until TASK for formal evaluation
Files: pipeline/quality.py, pipeline/preprocessing.py
Visualization: <path to saved before/after images>
What works: <describe>
What does not work: <describe, or "none observed">
Limitations: quality model has not been formally evaluated on a held-out set yet
Ready for next phase: YES/NO
```

**Commands:**
```bash
python -m pytest tests/test_quality.py tests/test_preprocessing.py
```

**Validation:**
1. Both demo images produce a result with no runtime error.
2. The Reject image is distinguishable in the output from the Good image.
3. Checkpoint file is written and readable by a non-developer.

**Expected result:** Confirmed, demonstrable Phase 1 behavior on real (not synthetic test) images.

**Done when:** `docs/checkpoints/phase1.md` exists, states "Ready for next phase: YES", and both demo images process without error.

**Do NOT:**
- Proceed to any Phase 2 task in this same session.
- Mark "Ready for next phase: YES" if either demo image fails.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-005 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model).

TASK: TASK-005 | PHASE 1 CHECKPOINT
LAYER/PHASE: Phase 1 — checkpoint/validation

OBJECTIVE:
Verify Phase 1 end-to-end on real demo images, and stop downstream flow correctly on Reject. Every phase must be demonstrable before the next phase begins.

CONTEXT — where this fits:
Closes out Phase 1 before Phase 2 work starts.

INPUT:
- At least 2 images in `data/demo/`: one expected Good/Borderline, one expected Reject

EXPECTED OUTPUT:
- A short written checkpoint result (see format below), saved to `docs/checkpoints/phase1.md`

FILES TO CREATE:
- `docs/checkpoints/phase1.md`
- `data/demo/` populated with the first 2 real images for this checkpoint (more images are added in later checkpoints/tasks as needed)

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-004

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Run `run_quality_gate()` on each demo image.
2. Confirm the Reject-labeled image's result is one that a caller (the future website) would correctly stop on — i.e., the returned `quality_label` clearly signals "do not proceed."
3. Write the checkpoint file using this format:
```text
PHASE RESULT — PHASE 1
Input: <image filenames>
Output: quality_label, quality_score, preprocessed_image (per image)
Model: quality_gate (see models/quality/metadata.json for version)
Dataset: DDR ungradable subset (per contract)
Metric: not yet measured — no eval_metrics recorded until TASK for formal evaluation
Files: pipeline/quality.py, pipeline/preprocessing.py
Visualization: <path to saved before/after images>
What works: <describe>
What does not work: <describe, or "none observed">
Limitations: quality model has not been formally evaluated on a held-out set yet
Ready for next phase: YES/NO
```

COMMANDS:
```bash
python -m pytest tests/test_quality.py tests/test_preprocessing.py
```

VALIDATION / TEST PROCEDURE:
1. Both demo images produce a result with no runtime error.
2. The Reject image is distinguishable in the output from the Good image.
3. Checkpoint file is written and readable by a non-developer.

EXPECTED RESULT:
Confirmed, demonstrable Phase 1 behavior on real (not synthetic test) images.

DONE WHEN:
`docs/checkpoints/phase1.md` exists, states "Ready for next phase: YES", and both demo images process without error.

DO NOT:
- Proceed to any Phase 2 task in this same session.
- Mark "Ready for next phase: YES" if either demo image fails.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-005: PHASE 1 CHECKPOINT"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-006 | Integrate vessel segmentation model

**Layer/Phase:** Phase 2 — Retinal Structure Analysis

**What:** Implement the vessel-segmentation part of `pipeline/structure.py`: load the vessel U-Net via the contract, run it on the preprocessed image, produce a vessel mask and overlay.

**Why:** First piece of structural evidence used later in Phase 3's decision fusion is not vessel-based directly, but the vessel overlay is required demo output per the architecture, and the module pattern here is reused by TASK-007/008.

**Context:** First task of Phase 2. Independent of lesion/MA integration (they can be built in any order relative to each other, but all three feed the same Phase 2 checkpoint).

**Input:**
- `preprocessed_image` from Phase 1
- `models/vessel_seg/*.onnx` + `metadata.json`

**Output:**
- `vessel_mask` (binary mask array)
- `vessel_overlay` (preprocessed image with mask drawn on top, for display)

**Files to create:**
- `pipeline/structure.py` (start this file here; TASK-007 and TASK-008 add to it)
- `tests/test_structure_vessel.py`

**Files to modify:**
- `requirements.txt` (if a new library is needed for mask overlay drawing)

**Needs:**
- TASK-002, TASK-005

**Implementation:**
1. `run_vessel_segmentation(preprocessed_image, model_dir="models/vessel_seg") -> dict` with keys `vessel_mask, vessel_overlay`.
2. Load contract via `pipeline.contract.load_contract(model_dir, "segmentation")`.
3. Run inference, threshold output into a binary mask per contract's `output_format`.
4. Draw the mask onto a copy of the image (e.g. colored outline) to produce `vessel_overlay`.
5. Missing-model handling identical in spirit to TASK-004: clear error, no fabricated mask.

**Commands:**
```bash
python -m pytest tests/test_structure_vessel.py
```

**Validation:**
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image, confirm mask shape matches image dimensions and overlay is visually a vessel-like structure (manual visual check, saved to `tests/fixtures/output/`).

**Expected result:** A working vessel-mask function, isolated and independently testable from lesion/MA work.

**Done when:** Tests pass and one demo image produces a plausible vessel overlay.

**Do NOT:**
- Add lesion or MA logic to this task — those are TASK-007 and TASK-008.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-006 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT).

TASK: TASK-006 | Integrate vessel segmentation model
LAYER/PHASE: Phase 2 — Retinal Structure Analysis

OBJECTIVE:
Implement the vessel-segmentation part of `pipeline/structure.py`: load the vessel U-Net via the contract, run it on the preprocessed image, produce a vessel mask and overlay. First piece of structural evidence used later in Phase 3's decision fusion is not vessel-based directly, but the vessel overlay is required demo output per the architecture, and the module pattern here is reused by TASK-007/008.

CONTEXT — where this fits:
First task of Phase 2. Independent of lesion/MA integration (they can be built in any order relative to each other, but all three feed the same Phase 2 checkpoint).

INPUT:
- `preprocessed_image` from Phase 1
- `models/vessel_seg/*.onnx` + `metadata.json`

EXPECTED OUTPUT:
- `vessel_mask` (binary mask array)
- `vessel_overlay` (preprocessed image with mask drawn on top, for display)

FILES TO CREATE:
- `pipeline/structure.py` (start this file here; TASK-007 and TASK-008 add to it)
- `tests/test_structure_vessel.py`

FILES TO MODIFY:
- `requirements.txt` (if a new library is needed for mask overlay drawing)

DEPENDENCIES (must already be done):
- TASK-002, TASK-005

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_vessel_segmentation(preprocessed_image, model_dir="models/vessel_seg") -> dict` with keys `vessel_mask, vessel_overlay`.
2. Load contract via `pipeline.contract.load_contract(model_dir, "segmentation")`.
3. Run inference, threshold output into a binary mask per contract's `output_format`.
4. Draw the mask onto a copy of the image (e.g. colored outline) to produce `vessel_overlay`.
5. Missing-model handling identical in spirit to TASK-004: clear error, no fabricated mask.

COMMANDS:
```bash
python -m pytest tests/test_structure_vessel.py
```

VALIDATION / TEST PROCEDURE:
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image, confirm mask shape matches image dimensions and overlay is visually a vessel-like structure (manual visual check, saved to `tests/fixtures/output/`).

EXPECTED RESULT:
A working vessel-mask function, isolated and independently testable from lesion/MA work.

DONE WHEN:
Tests pass and one demo image produces a plausible vessel overlay.

DO NOT:
- Add lesion or MA logic to this task — those are TASK-007 and TASK-008.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-006: Integrate vessel segmentation model"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-007 | Integrate lesion segmentation models (HE/EX/SE)

**Layer/Phase:** Phase 2 — Retinal Structure Analysis

**What:** Add lesion-segmentation functions to `pipeline/structure.py`: load the HE/EX/SE U-Net, produce three separate binary masks and an overlay.

**Why:** EX area near the fovea and HE presence are direct inputs to the Phase 3 decision fusion — this is not just a display feature.

**Context:** Second task of Phase 2, added to the same file as TASK-006 but functionally independent of it.

**Input:**
- `preprocessed_image` from Phase 1
- `models/lesion_seg/*.onnx` + `metadata.json`

**Output:**
- `he_mask`, `ex_mask`, `se_mask` (three separate binary masks)
- `he_presence` (boolean), `ex_area` (numeric, pixel or normalized area)
- `lesion_overlay` (all three masks composited for display, distinctly colored)

**Files to create:**
- `tests/test_structure_lesion.py`

**Files to modify:**
- `pipeline/structure.py` (add `run_lesion_segmentation(...)`)

**Needs:**
- TASK-002, TASK-005

**Implementation:**
1. `run_lesion_segmentation(preprocessed_image, model_dir="models/lesion_seg") -> dict` with the keys listed in Output above.
2. Load contract (`segmentation` type, `mask_labels` should list `["HE","EX","SE"]` or similar — read this from the contract, don't hardcode the label order).
3. Compute `he_presence` as "mask has any positive pixels above a small noise threshold" (threshold value from contract or config — not a magic number in code).
4. Compute `ex_area` as the EX mask's positive-pixel count (or normalized fraction of image area — pick one and document it in the docstring).
5. Report HE/EX/SE per the source spec's rule: presence, count/area, quadrant only — do not invent subtypes.

**Commands:**
```bash
python -m pytest tests/test_structure_lesion.py
```

**Validation:**
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image with visible lesions if available; confirm three masks are returned with correct shapes and `he_presence`/`ex_area` are sensible (not NaN, not negative).

**Expected result:** Lesion evidence ready to feed Phase 3's decision fusion (TASK-012).

**Done when:** Tests pass and lesion overlay is visually plausible on at least one demo image.

**Do NOT:**
- Invent hemorrhage subtypes (flame/dot-blot/deep) — spec explicitly forbids this.
- Merge HE/EX/SE into a single combined mask — keep them separate per the contract.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-007 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model).

TASK: TASK-007 | Integrate lesion segmentation models (HE/EX/SE)
LAYER/PHASE: Phase 2 — Retinal Structure Analysis

OBJECTIVE:
Add lesion-segmentation functions to `pipeline/structure.py`: load the HE/EX/SE U-Net, produce three separate binary masks and an overlay. EX area near the fovea and HE presence are direct inputs to the Phase 3 decision fusion — this is not just a display feature.

CONTEXT — where this fits:
Second task of Phase 2, added to the same file as TASK-006 but functionally independent of it.

INPUT:
- `preprocessed_image` from Phase 1
- `models/lesion_seg/*.onnx` + `metadata.json`

EXPECTED OUTPUT:
- `he_mask`, `ex_mask`, `se_mask` (three separate binary masks)
- `he_presence` (boolean), `ex_area` (numeric, pixel or normalized area)
- `lesion_overlay` (all three masks composited for display, distinctly colored)

FILES TO CREATE:
- `tests/test_structure_lesion.py`

FILES TO MODIFY:
- `pipeline/structure.py` (add `run_lesion_segmentation(...)`)

DEPENDENCIES (must already be done):
- TASK-002, TASK-005

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_lesion_segmentation(preprocessed_image, model_dir="models/lesion_seg") -> dict` with the keys listed in Output above.
2. Load contract (`segmentation` type, `mask_labels` should list `["HE","EX","SE"]` or similar — read this from the contract, don't hardcode the label order).
3. Compute `he_presence` as "mask has any positive pixels above a small noise threshold" (threshold value from contract or config — not a magic number in code).
4. Compute `ex_area` as the EX mask's positive-pixel count (or normalized fraction of image area — pick one and document it in the docstring).
5. Report HE/EX/SE per the source spec's rule: presence, count/area, quadrant only — do not invent subtypes.

COMMANDS:
```bash
python -m pytest tests/test_structure_lesion.py
```

VALIDATION / TEST PROCEDURE:
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image with visible lesions if available; confirm three masks are returned with correct shapes and `he_presence`/`ex_area` are sensible (not NaN, not negative).

EXPECTED RESULT:
Lesion evidence ready to feed Phase 3's decision fusion (TASK-012).

DONE WHEN:
Tests pass and lesion overlay is visually plausible on at least one demo image.

DO NOT:
- Invent hemorrhage subtypes (flame/dot-blot/deep) — spec explicitly forbids this.
- Merge HE/EX/SE into a single combined mask — keep them separate per the contract.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-007: Integrate lesion segmentation models (HE/EX/SE)"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-008 | Integrate MA (microaneurysm) detector

**Layer/Phase:** Phase 2 — Retinal Structure Analysis

**What:** Add MA detection to `pipeline/structure.py`: classical candidate extraction (top-hat/matched filter) followed by a small CNN false-positive reducer, producing an MA count.

**Why:** MA count (including near-macula count) is a direct input to Phase 3's decision fusion.

**Context:** Third task of Phase 2, independent of TASK-006/007 but completes the evidence set the Phase 2 checkpoint validates.

**Input:**
- `preprocessed_image` from Phase 1
- `models/ma_detector/*` (CNN false-positive reducer) + `metadata.json` (contract type: MA detector, with `candidate_extraction_method` and `fp_reducer_model_file`)

**Output:**
- `ma_count` (integer)
- `ma_overlay` (candidate locations marked on the image)

**Files to create:**
- `tests/test_structure_ma.py`

**Files to modify:**
- `pipeline/structure.py` (add `run_ma_detection(...)`)

**Needs:**
- TASK-002, TASK-005

**Implementation:**
1. `run_ma_detection(preprocessed_image, model_dir="models/ma_detector") -> dict` with keys `ma_count, ma_overlay`.
2. Load contract (MA-detector type).
3. Step A — classical candidate extraction: implement the method named in `candidate_extraction_method` from the contract (top-hat or matched filter — implement whichever is specified, do not silently pick the other).
4. Step B — run the CNN false-positive reducer (`fp_reducer_model_file`) on each candidate patch, keep only candidates classified as true MAs.
5. `ma_count` is the count of surviving candidates. `ma_overlay` marks their locations.

**Commands:**
```bash
python -m pytest tests/test_structure_ma.py
```

**Validation:**
1. Missing-model error path confirmed.
2. Once real components exist: run on one demo image, confirm `ma_count` is a non-negative integer and overlay shows marked points.

**Expected result:** MA evidence ready for Phase 3.

**Done when:** Tests pass and overlay is visually plausible on at least one demo image.

**Do NOT:**
- Skip the classical candidate-extraction step and run the CNN on the whole image directly — the architecture specifically calls for the two-stage hybrid approach.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-008 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)).

TASK: TASK-008 | Integrate MA (microaneurysm) detector
LAYER/PHASE: Phase 2 — Retinal Structure Analysis

OBJECTIVE:
Add MA detection to `pipeline/structure.py`: classical candidate extraction (top-hat/matched filter) followed by a small CNN false-positive reducer, producing an MA count. MA count (including near-macula count) is a direct input to Phase 3's decision fusion.

CONTEXT — where this fits:
Third task of Phase 2, independent of TASK-006/007 but completes the evidence set the Phase 2 checkpoint validates.

INPUT:
- `preprocessed_image` from Phase 1
- `models/ma_detector/*` (CNN false-positive reducer) + `metadata.json` (contract type: MA detector, with `candidate_extraction_method` and `fp_reducer_model_file`)

EXPECTED OUTPUT:
- `ma_count` (integer)
- `ma_overlay` (candidate locations marked on the image)

FILES TO CREATE:
- `tests/test_structure_ma.py`

FILES TO MODIFY:
- `pipeline/structure.py` (add `run_ma_detection(...)`)

DEPENDENCIES (must already be done):
- TASK-002, TASK-005

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_ma_detection(preprocessed_image, model_dir="models/ma_detector") -> dict` with keys `ma_count, ma_overlay`.
2. Load contract (MA-detector type).
3. Step A — classical candidate extraction: implement the method named in `candidate_extraction_method` from the contract (top-hat or matched filter — implement whichever is specified, do not silently pick the other).
4. Step B — run the CNN false-positive reducer (`fp_reducer_model_file`) on each candidate patch, keep only candidates classified as true MAs.
5. `ma_count` is the count of surviving candidates. `ma_overlay` marks their locations.

COMMANDS:
```bash
python -m pytest tests/test_structure_ma.py
```

VALIDATION / TEST PROCEDURE:
1. Missing-model error path confirmed.
2. Once real components exist: run on one demo image, confirm `ma_count` is a non-negative integer and overlay shows marked points.

EXPECTED RESULT:
MA evidence ready for Phase 3.

DONE WHEN:
Tests pass and overlay is visually plausible on at least one demo image.

DO NOT:
- Skip the classical candidate-extraction step and run the CNN on the whole image directly — the architecture specifically calls for the two-stage hybrid approach.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-008: Integrate MA (microaneurysm) detector"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-009 | PHASE 2 CHECKPOINT

**Layer/Phase:** Phase 2 — checkpoint/validation

**What:** Verify all of Phase 2 (vessel, lesion, MA) together on the same demo images used in TASK-005.

**Why:** Confirms the three independently-built modules combine correctly before Phase 3 depends on their combined output.

**Context:** Closes out Phase 2.

**Input:**
- The same demo images from `data/demo/` (Phase 1 checkpoint), now run through all of Phase 2

**Output:**
- `docs/checkpoints/phase2.md` (same format as Phase 1's checkpoint)
- Saved overlay images for visual proof

**Files to create:**
- `docs/checkpoints/phase2.md`

**Files to modify:**
- None

**Needs:**
- TASK-006, TASK-007, TASK-008

**Implementation:**
1. For each demo image (that passed the Phase 1 quality gate), run `run_vessel_segmentation`, `run_lesion_segmentation`, `run_ma_detection` in sequence.
2. Confirm no runtime error across all three for every image.
3. Write the checkpoint file in the same format as `phase1.md`, listing all three models, their datasets, and noting evaluation metrics (Dice/IoU/FROC) are "not yet measured" if formal evaluation hasn't happened yet — never invent numbers.

**Commands:**
```bash
python -m pytest tests/test_structure_vessel.py tests/test_structure_lesion.py tests/test_structure_ma.py
```

**Validation:**
1. All three modules run on all qualifying demo images with no error.
2. Checkpoint file exists and is readable by a non-developer.

**Expected result:** Confirmed, demonstrable Phase 2 behavior.

**Done when:** `docs/checkpoints/phase2.md` states "Ready for next phase: YES" and every demo image processes cleanly through all three modules.

**Do NOT:**
- Proceed to any Phase 3 task in this same session.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-009 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector).

TASK: TASK-009 | PHASE 2 CHECKPOINT
LAYER/PHASE: Phase 2 — checkpoint/validation

OBJECTIVE:
Verify all of Phase 2 (vessel, lesion, MA) together on the same demo images used in TASK-005. Confirms the three independently-built modules combine correctly before Phase 3 depends on their combined output.

CONTEXT — where this fits:
Closes out Phase 2.

INPUT:
- The same demo images from `data/demo/` (Phase 1 checkpoint), now run through all of Phase 2

EXPECTED OUTPUT:
- `docs/checkpoints/phase2.md` (same format as Phase 1's checkpoint)
- Saved overlay images for visual proof

FILES TO CREATE:
- `docs/checkpoints/phase2.md`

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-006, TASK-007, TASK-008

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. For each demo image (that passed the Phase 1 quality gate), run `run_vessel_segmentation`, `run_lesion_segmentation`, `run_ma_detection` in sequence.
2. Confirm no runtime error across all three for every image.
3. Write the checkpoint file in the same format as `phase1.md`, listing all three models, their datasets, and noting evaluation metrics (Dice/IoU/FROC) are "not yet measured" if formal evaluation hasn't happened yet — never invent numbers.

COMMANDS:
```bash
python -m pytest tests/test_structure_vessel.py tests/test_structure_lesion.py tests/test_structure_ma.py
```

VALIDATION / TEST PROCEDURE:
1. All three modules run on all qualifying demo images with no error.
2. Checkpoint file exists and is readable by a non-developer.

EXPECTED RESULT:
Confirmed, demonstrable Phase 2 behavior.

DONE WHEN:
`docs/checkpoints/phase2.md` states "Ready for next phase: YES" and every demo image processes cleanly through all three modules.

DO NOT:
- Proceed to any Phase 3 task in this same session.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-009: PHASE 2 CHECKPOINT"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-010 | Integrate DR grading model

**Layer/Phase:** Phase 3 — DR Grading & Referral Decision

**What:** Implement `pipeline/grading.py`: load the grading model (ResNet-50, backup EfficientNet-B0) via the contract, run inference, return ICDR 0–4 class probabilities.

**Why:** Core severity prediction — everything in Phase 3 downstream depends on this.

**Context:** First task of Phase 3.

**Input:**
- `preprocessed_image` from Phase 1
- `models/grading/*.onnx` + `metadata.json`

**Output:**
- `severity_class` (0–4)
- `probabilities` (5-length array)

**Files to create:**
- `pipeline/grading.py`
- `tests/test_grading.py`

**Files to modify:**
- None (dependencies already added)

**Needs:**
- TASK-002, TASK-005

**Implementation:**
1. `run_grading(preprocessed_image, model_dir="models/grading") -> dict` with keys `severity_class, probabilities`.
2. Load contract (classifier type, `class_labels` should be `["0","1","2","3","4"]` or equivalent — read from contract).
3. Run inference, softmax if not already applied, return raw (uncalibrated) probabilities — calibration is a separate step (TASK-011), do not conflate them here.
4. If the contract's `model_name` indicates the backup (EfficientNet-B0) is in use instead of ResNet-50, this must be visible in the returned result's metadata for later reporting — do not hide which backbone actually ran.

**Commands:**
```bash
python -m pytest tests/test_grading.py
```

**Validation:**
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image per available severity level, confirm `probabilities` sums to ~1.0 and `severity_class` is the argmax.

**Expected result:** Raw grading output, ready for calibration.

**Done when:** Tests pass on at least one demo image.

**Do NOT:**
- Apply temperature scaling here — that's TASK-011.
- Silently run both ResNet-50 and EfficientNet-B0 "just in case" — only one production grader per the architecture (Section 5 of the Final Model Stack).

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-010 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT).

TASK: TASK-010 | Integrate DR grading model
LAYER/PHASE: Phase 3 — DR Grading & Referral Decision

OBJECTIVE:
Implement `pipeline/grading.py`: load the grading model (ResNet-50, backup EfficientNet-B0) via the contract, run inference, return ICDR 0–4 class probabilities. Core severity prediction — everything in Phase 3 downstream depends on this.

CONTEXT — where this fits:
First task of Phase 3.

INPUT:
- `preprocessed_image` from Phase 1
- `models/grading/*.onnx` + `metadata.json`

EXPECTED OUTPUT:
- `severity_class` (0–4)
- `probabilities` (5-length array)

FILES TO CREATE:
- `pipeline/grading.py`
- `tests/test_grading.py`

FILES TO MODIFY:
- None (dependencies already added)

DEPENDENCIES (must already be done):
- TASK-002, TASK-005

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_grading(preprocessed_image, model_dir="models/grading") -> dict` with keys `severity_class, probabilities`.
2. Load contract (classifier type, `class_labels` should be `["0","1","2","3","4"]` or equivalent — read from contract).
3. Run inference, softmax if not already applied, return raw (uncalibrated) probabilities — calibration is a separate step (TASK-011), do not conflate them here.
4. If the contract's `model_name` indicates the backup (EfficientNet-B0) is in use instead of ResNet-50, this must be visible in the returned result's metadata for later reporting — do not hide which backbone actually ran.

COMMANDS:
```bash
python -m pytest tests/test_grading.py
```

VALIDATION / TEST PROCEDURE:
1. Missing-model error path confirmed.
2. Once a real model exists: run on one demo image per available severity level, confirm `probabilities` sums to ~1.0 and `severity_class` is the argmax.

EXPECTED RESULT:
Raw grading output, ready for calibration.

DONE WHEN:
Tests pass on at least one demo image.

DO NOT:
- Apply temperature scaling here — that's TASK-011.
- Silently run both ResNet-50 and EfficientNet-B0 "just in case" — only one production grader per the architecture (Section 5 of the Final Model Stack).

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-010: Integrate DR grading model"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-011 | Add calibration (temperature scaling)

**Layer/Phase:** Phase 3 — DR Grading & Referral Decision

**What:** Apply temperature scaling to the raw grading probabilities from TASK-010, producing calibrated confidence.

**Why:** Calibrated confidence, not raw softmax output, is what feeds the decision fusion (TASK-012) and what should be displayed to the user as "confidence."

**Context:** Second task of Phase 3, directly extends TASK-010's output.

**Input:**
- `probabilities` from `run_grading()`
- A temperature value (a single scalar, fit once on the validation fold — see Implementation step 1)

**Output:**
- `calibrated_probabilities`
- `confidence` (max of calibrated probabilities)

**Files to create:**
- `tests/test_calibration.py`
- `configs/calibration.json` (stores the fitted temperature value — a number, not a model file)

**Files to modify:**
- `pipeline/grading.py` (add `apply_calibration(probabilities, temperature) -> dict`)

**Needs:**
- TASK-010

**Implementation:**
1. The temperature value itself must be fit on the validation fold (this fitting happens on the MATLAB/training side, or in a short offline script — NOT inside the live inference path). This task only implements *applying* a given temperature value at inference time. If no fitted temperature exists yet, use `1.0` (no-op) and clearly mark this in `configs/calibration.json` as `"fitted": false` — never fabricate a fitted value.
2. Implement `apply_calibration(probabilities, temperature) -> dict` returning `calibrated_probabilities` and `confidence`.
3. Read the temperature from `configs/calibration.json` by default.

**Commands:**
```bash
python -m pytest tests/test_calibration.py
```

**Validation:**
1. With `temperature=1.0`, calibrated output equals the raw input (sanity check — no-op case).
2. With a temperature > 1.0, confirm the resulting distribution is flatter (max probability decreases) — this is the expected direction of temperature scaling.

**Expected result:** A clearly separated, honestly-labeled calibration step.

**Done when:** Tests pass and `configs/calibration.json` correctly reflects whether a real fitted value is in use.

**Do NOT:**
- Fit the temperature value inside this task using the sealed test set, or any test-set data at all.
- Claim `"fitted": true` without an actual validation-fold fitting procedure having been run.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-011 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model).

TASK: TASK-011 | Add calibration (temperature scaling)
LAYER/PHASE: Phase 3 — DR Grading & Referral Decision

OBJECTIVE:
Apply temperature scaling to the raw grading probabilities from TASK-010, producing calibrated confidence. Calibrated confidence, not raw softmax output, is what feeds the decision fusion (TASK-012) and what should be displayed to the user as "confidence."

CONTEXT — where this fits:
Second task of Phase 3, directly extends TASK-010's output.

INPUT:
- `probabilities` from `run_grading()`
- A temperature value (a single scalar, fit once on the validation fold — see Implementation step 1)

EXPECTED OUTPUT:
- `calibrated_probabilities`
- `confidence` (max of calibrated probabilities)

FILES TO CREATE:
- `tests/test_calibration.py`
- `configs/calibration.json` (stores the fitted temperature value — a number, not a model file)

FILES TO MODIFY:
- `pipeline/grading.py` (add `apply_calibration(probabilities, temperature) -> dict`)

DEPENDENCIES (must already be done):
- TASK-010

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. The temperature value itself must be fit on the validation fold (this fitting happens on the MATLAB/training side, or in a short offline script — NOT inside the live inference path). This task only implements *applying* a given temperature value at inference time. If no fitted temperature exists yet, use `1.0` (no-op) and clearly mark this in `configs/calibration.json` as `"fitted": false` — never fabricate a fitted value.
2. Implement `apply_calibration(probabilities, temperature) -> dict` returning `calibrated_probabilities` and `confidence`.
3. Read the temperature from `configs/calibration.json` by default.

COMMANDS:
```bash
python -m pytest tests/test_calibration.py
```

VALIDATION / TEST PROCEDURE:
1. With `temperature=1.0`, calibrated output equals the raw input (sanity check — no-op case).
2. With a temperature > 1.0, confirm the resulting distribution is flatter (max probability decreases) — this is the expected direction of temperature scaling.

EXPECTED RESULT:
A clearly separated, honestly-labeled calibration step.

DONE WHEN:
Tests pass and `configs/calibration.json` correctly reflects whether a real fitted value is in use.

DO NOT:
- Fit the temperature value inside this task using the sealed test set, or any test-set data at all.
- Claim `"fitted": true` without an actual validation-fold fitting procedure having been run.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-011: Add calibration (temperature scaling)"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-012 | Decision fusion (referral decision)

**Layer/Phase:** Phase 3 — DR Grading & Referral Decision

**What:** Implement `pipeline/decision.py`: a simple logistic regression (or explicit rule, if no trained fusion model exists yet) combining calibrated grade probability + MA count + HE presence + EX area + quality tier into a final refer/no-refer decision.

**Why:** This is the architecture's stated main differentiator over a naive single-threshold approach — must not be skipped or replaced with just thresholding the grade.

**Context:** Third task of Phase 3, consumes outputs from Phase 1 (quality tier), Phase 2 (MA/HE/EX evidence), and Phase 3 (calibrated grade).

**Input:**
- `calibrated_probabilities` (TASK-011)
- `ma_count`, `he_presence`, `ex_area` (Phase 2 outputs)
- `quality_label`/tier (Phase 1 output)

**Output:**
- `referable_decision` (boolean or "REFER"/"NO REFER")
- `grade_alone_decision` (the naive single-threshold-on-grade result, computed side by side for comparison/reporting)

**Files to create:**
- `pipeline/decision.py`
- `tests/test_decision.py`
- `models/decision_fusion/metadata.json` + fitted coefficients file, OR `configs/decision_rule.json` if using an explicit rule instead of a trained model — pick ONE approach and document which in the file itself

**Files to modify:**
- None

**Needs:**
- TASK-007, TASK-008, TASK-011

**Implementation:**
1. If a fitted logistic regression exists (trained offline on a held-out calibration split, never the sealed test set), load its coefficients from `models/decision_fusion/`.
2. If none exists yet, implement `grade_alone_decision` only (threshold calibrated grade probability at Grade ≥2) and clearly mark `referable_decision` as "using grade-alone fallback, fusion model not yet trained" rather than fabricating fusion weights.
3. Implement quality-tier-aware thresholds: a stricter (higher-sensitivity) cut-off for Borderline-quality images than Good-quality images, per the architecture. Reject-quality images never get an automated decision at all (they were already stopped in Phase 1).
4. Return both `referable_decision` and `grade_alone_decision` so they can be reported side by side later.

**Commands:**
```bash
python -m pytest tests/test_decision.py
```

**Validation:**
1. With the grade-alone fallback active: confirm a high-grade demo image returns REFER and a Grade-0 image returns NO REFER.
2. Confirm the Borderline-quality threshold is measurably stricter than the Good-quality threshold (test with a constructed borderline example).
3. Confirm `grade_alone_decision` and `referable_decision` are both present in every result, even when they're currently equal (fallback case).

**Expected result:** A transparent, inspectable decision step — never a black box, and never silently pretending a trained fusion model exists when it doesn't.

**Done when:** Tests pass and the fallback-vs-fitted state is clearly recorded in the output.

**Do NOT:**
- Present the grade-alone fallback as if it were the trained fusion model.
- Fit the fusion model on the sealed test set.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-012 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)).

TASK: TASK-012 | Decision fusion (referral decision)
LAYER/PHASE: Phase 3 — DR Grading & Referral Decision

OBJECTIVE:
Implement `pipeline/decision.py`: a simple logistic regression (or explicit rule, if no trained fusion model exists yet) combining calibrated grade probability + MA count + HE presence + EX area + quality tier into a final refer/no-refer decision. This is the architecture's stated main differentiator over a naive single-threshold approach — must not be skipped or replaced with just thresholding the grade.

CONTEXT — where this fits:
Third task of Phase 3, consumes outputs from Phase 1 (quality tier), Phase 2 (MA/HE/EX evidence), and Phase 3 (calibrated grade).

INPUT:
- `calibrated_probabilities` (TASK-011)
- `ma_count`, `he_presence`, `ex_area` (Phase 2 outputs)
- `quality_label`/tier (Phase 1 output)

EXPECTED OUTPUT:
- `referable_decision` (boolean or "REFER"/"NO REFER")
- `grade_alone_decision` (the naive single-threshold-on-grade result, computed side by side for comparison/reporting)

FILES TO CREATE:
- `pipeline/decision.py`
- `tests/test_decision.py`
- `models/decision_fusion/metadata.json` + fitted coefficients file, OR `configs/decision_rule.json` if using an explicit rule instead of a trained model — pick ONE approach and document which in the file itself

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-007, TASK-008, TASK-011

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. If a fitted logistic regression exists (trained offline on a held-out calibration split, never the sealed test set), load its coefficients from `models/decision_fusion/`.
2. If none exists yet, implement `grade_alone_decision` only (threshold calibrated grade probability at Grade ≥2) and clearly mark `referable_decision` as "using grade-alone fallback, fusion model not yet trained" rather than fabricating fusion weights.
3. Implement quality-tier-aware thresholds: a stricter (higher-sensitivity) cut-off for Borderline-quality images than Good-quality images, per the architecture. Reject-quality images never get an automated decision at all (they were already stopped in Phase 1).
4. Return both `referable_decision` and `grade_alone_decision` so they can be reported side by side later.

COMMANDS:
```bash
python -m pytest tests/test_decision.py
```

VALIDATION / TEST PROCEDURE:
1. With the grade-alone fallback active: confirm a high-grade demo image returns REFER and a Grade-0 image returns NO REFER.
2. Confirm the Borderline-quality threshold is measurably stricter than the Good-quality threshold (test with a constructed borderline example).
3. Confirm `grade_alone_decision` and `referable_decision` are both present in every result, even when they're currently equal (fallback case).

EXPECTED RESULT:
A transparent, inspectable decision step — never a black box, and never silently pretending a trained fusion model exists when it doesn't.

DONE WHEN:
Tests pass and the fallback-vs-fitted state is clearly recorded in the output.

DO NOT:
- Present the grade-alone fallback as if it were the trained fusion model.
- Fit the fusion model on the sealed test set.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-012: Decision fusion (referral decision)"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-013 | PHASE 3 CHECKPOINT

**Layer/Phase:** Phase 3 — checkpoint/validation

**What:** Verify grading + calibration + decision fusion together, end-to-end, on the demo set.

**Why:** Confirms the safety-critical decision step works correctly before explainability (Phase 4) is layered on top.

**Context:** Closes out Phase 3.

**Input:**
- Demo images that passed Phase 1 and Phase 2

**Output:**
- `docs/checkpoints/phase3.md`

**Files to create:**
- `docs/checkpoints/phase3.md`

**Files to modify:**
- None

**Needs:**
- TASK-010, TASK-011, TASK-012

**Implementation:**
1. Run the full Phase 1 → Phase 2 → Phase 3 chain on every demo image.
2. Record, per image: severity class, calibrated confidence, `grade_alone_decision`, `referable_decision`, and whether they agree or differ.
3. Write the checkpoint file in the standard format, explicitly noting whether the decision-fusion model is fitted or in fallback mode (per TASK-012).

**Commands:**
```bash
python -m pytest tests/test_grading.py tests/test_calibration.py tests/test_decision.py
```

**Validation:**
1. All demo images process end-to-end with no runtime error.
2. Checkpoint file clearly states fusion-vs-fallback status — this must never be silently glossed over.

**Expected result:** Confirmed, demonstrable, and honestly-labeled Phase 3 behavior.

**Done when:** `docs/checkpoints/phase3.md` states "Ready for next phase: YES."

**Do NOT:**
- Proceed to Phase 4 in the same session.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-013 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)).

TASK: TASK-013 | PHASE 3 CHECKPOINT
LAYER/PHASE: Phase 3 — checkpoint/validation

OBJECTIVE:
Verify grading + calibration + decision fusion together, end-to-end, on the demo set. Confirms the safety-critical decision step works correctly before explainability (Phase 4) is layered on top.

CONTEXT — where this fits:
Closes out Phase 3.

INPUT:
- Demo images that passed Phase 1 and Phase 2

EXPECTED OUTPUT:
- `docs/checkpoints/phase3.md`

FILES TO CREATE:
- `docs/checkpoints/phase3.md`

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-010, TASK-011, TASK-012

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Run the full Phase 1 → Phase 2 → Phase 3 chain on every demo image.
2. Record, per image: severity class, calibrated confidence, `grade_alone_decision`, `referable_decision`, and whether they agree or differ.
3. Write the checkpoint file in the standard format, explicitly noting whether the decision-fusion model is fitted or in fallback mode (per TASK-012).

COMMANDS:
```bash
python -m pytest tests/test_grading.py tests/test_calibration.py tests/test_decision.py
```

VALIDATION / TEST PROCEDURE:
1. All demo images process end-to-end with no runtime error.
2. Checkpoint file clearly states fusion-vs-fallback status — this must never be silently glossed over.

EXPECTED RESULT:
Confirmed, demonstrable, and honestly-labeled Phase 3 behavior.

DONE WHEN:
`docs/checkpoints/phase3.md` states "Ready for next phase: YES."

DO NOT:
- Proceed to Phase 4 in the same session.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-013: PHASE 3 CHECKPOINT"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-014 | Grad-CAM explainability

**Layer/Phase:** Phase 4 — Explainability & Final Report

**What:** Implement `pipeline/explain.py`: run Grad-CAM on the frozen grading model for the predicted class, produce a heatmap overlay.

**Why:** Required explainability output; must be clearly separated from and never confused with the Phase 2 lesion-detector evidence.

**Context:** First task of Phase 4. Runs on the same grading model as Phase 3 but needs access to intermediate activations, which the plain ONNX inference in TASK-010 doesn't expose — this task handles that separately.

**Input:**
- `preprocessed_image`
- `severity_class` (the predicted class to explain)
- Grading model (same artifact as TASK-010)

**Output:**
- `heatmap_overlay` (image)

**Files to create:**
- `pipeline/explain.py`
- `tests/test_explain.py`

**Files to modify:**
- `requirements.txt` (add a Grad-CAM library, or implement directly if the ONNX runtime exposes the needed layer outputs — pick the simpler reliable option per the Master Prompt's decision rule)

**Needs:**
- TASK-010

**Implementation:**
1. `run_gradcam(preprocessed_image, severity_class, model_dir="models/grading") -> dict` with key `heatmap_overlay`.
2. If the exported ONNX model doesn't expose intermediate layers needed for Grad-CAM, document this as a blocker and use the simplest supported alternative (e.g. a HiResCAM-compatible export, or running Grad-CAM against the pre-export MATLAB/framework model if that's more reliable than fighting the ONNX export — this is exactly the kind of "genuine technical blocker" HANDOFF.md allows documenting rather than silently working around).
3. Overlay the heatmap on the preprocessed image with a clear colormap.
4. **UI-facing labeling requirement:** whatever caller uses this output must label it "model attention" — enforce this by naming the returned image key `heatmap_overlay` (not `evidence` or `proof`) so downstream UI code can't accidentally mislabel it.

**Commands:**
```bash
python -m pytest tests/test_explain.py
```

**Validation:**
1. Run on one demo image, confirm heatmap is generated and roughly concentrated over regions with actual visible lesions where lesion masks exist (rough visual sanity check, not a formal IoU score — that's a separate evaluation task, not part of the prototype build).

**Expected result:** A working, honestly-labeled heatmap generator.

**Done when:** Tests pass and one demo image produces a visually sensible heatmap.

**Do NOT:**
- Merge the heatmap with the Phase 2 lesion masks into a single "evidence" image — they must stay visually and conceptually distinct per the architecture.
- Call this output "clinical evidence" anywhere in code, comments, or UI.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-014 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT).

TASK: TASK-014 | Grad-CAM explainability
LAYER/PHASE: Phase 4 — Explainability & Final Report

OBJECTIVE:
Implement `pipeline/explain.py`: run Grad-CAM on the frozen grading model for the predicted class, produce a heatmap overlay. Required explainability output; must be clearly separated from and never confused with the Phase 2 lesion-detector evidence.

CONTEXT — where this fits:
First task of Phase 4. Runs on the same grading model as Phase 3 but needs access to intermediate activations, which the plain ONNX inference in TASK-010 doesn't expose — this task handles that separately.

INPUT:
- `preprocessed_image`
- `severity_class` (the predicted class to explain)
- Grading model (same artifact as TASK-010)

EXPECTED OUTPUT:
- `heatmap_overlay` (image)

FILES TO CREATE:
- `pipeline/explain.py`
- `tests/test_explain.py`

FILES TO MODIFY:
- `requirements.txt` (add a Grad-CAM library, or implement directly if the ONNX runtime exposes the needed layer outputs — pick the simpler reliable option per the Master Prompt's decision rule)

DEPENDENCIES (must already be done):
- TASK-010

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_gradcam(preprocessed_image, severity_class, model_dir="models/grading") -> dict` with key `heatmap_overlay`.
2. If the exported ONNX model doesn't expose intermediate layers needed for Grad-CAM, document this as a blocker and use the simplest supported alternative (e.g. a HiResCAM-compatible export, or running Grad-CAM against the pre-export MATLAB/framework model if that's more reliable than fighting the ONNX export — this is exactly the kind of "genuine technical blocker" HANDOFF.md allows documenting rather than silently working around).
3. Overlay the heatmap on the preprocessed image with a clear colormap.
4. **UI-facing labeling requirement:** whatever caller uses this output must label it "model attention" — enforce this by naming the returned image key `heatmap_overlay` (not `evidence` or `proof`) so downstream UI code can't accidentally mislabel it.

COMMANDS:
```bash
python -m pytest tests/test_explain.py
```

VALIDATION / TEST PROCEDURE:
1. Run on one demo image, confirm heatmap is generated and roughly concentrated over regions with actual visible lesions where lesion masks exist (rough visual sanity check, not a formal IoU score — that's a separate evaluation task, not part of the prototype build).

EXPECTED RESULT:
A working, honestly-labeled heatmap generator.

DONE WHEN:
Tests pass and one demo image produces a visually sensible heatmap.

DO NOT:
- Merge the heatmap with the Phase 2 lesion masks into a single "evidence" image — they must stay visually and conceptually distinct per the architecture.
- Call this output "clinical evidence" anywhere in code, comments, or UI.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-014: Grad-CAM explainability"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-015 | Final report assembly

**Layer/Phase:** Phase 4 — Explainability & Final Report

**What:** Implement `pipeline/report.py`: a single function that runs all four phases in order and assembles one structured result object for the website to render.

**Why:** The website (TASK-017) should call one function, not orchestrate four phase modules itself — keeps the web layer thin and the pipeline logic testable independent of any web framework.

**Context:** Closes the pipeline logic side of Phase 4, immediately before the website is built.

**Input:**
- Raw fundus image path

**Output:**
- One structured dict containing every phase's output, e.g.:
```json
{
  "phase1": {"quality_label": "...", "quality_score": 0.0, "preprocessed_image": "..."},
  "phase2": {"vessel_overlay": "...", "lesion_overlay": "...", "ma_count": 0},
  "phase3": {"severity_class": 0, "confidence": 0.0, "referable_decision": "...", "grade_alone_decision": "..."},
  "phase4": {"heatmap_overlay": "..."},
  "stopped_at_phase1": false
}
```

**Files to create:**
- `pipeline/report.py`
- `tests/test_report.py`

**Files to modify:**
- None

**Needs:**
- TASK-005, TASK-009, TASK-013, TASK-014

**Implementation:**
1. `run_full_pipeline(image_path) -> dict` calling, in order: `quality.run_quality_gate`, then (if not Reject) `structure.run_vessel_segmentation`/`run_lesion_segmentation`/`run_ma_detection`, then `grading.run_grading` + `apply_calibration`, then `decision.decide`, then `explain.run_gradcam`.
2. If Phase 1 returns Reject, set `stopped_at_phase1: true` and skip all later phases — return the partial result cleanly, not an error.
3. Wrap each phase call so that a failure in one phase produces a clear, phase-labeled error rather than an unlabeled stack trace (per HANDOFF.md's error-handling rules).

**Commands:**
```bash
python -m pytest tests/test_report.py
```

**Validation:**
1. Run on a Good-quality demo image — confirm all four phase keys are populated.
2. Run on a Reject-quality demo image — confirm `stopped_at_phase1: true` and phases 2–4 are absent or null, with no error.

**Expected result:** One clean entry point for the website.

**Done when:** Tests pass for both the full-pipeline and stopped-at-Phase-1 cases.

**Do NOT:**
- Build any web/HTTP code here — that's TASK-017.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-015 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability).

TASK: TASK-015 | Final report assembly
LAYER/PHASE: Phase 4 — Explainability & Final Report

OBJECTIVE:
Implement `pipeline/report.py`: a single function that runs all four phases in order and assembles one structured result object for the website to render. The website (TASK-017) should call one function, not orchestrate four phase modules itself — keeps the web layer thin and the pipeline logic testable independent of any web framework.

CONTEXT — where this fits:
Closes the pipeline logic side of Phase 4, immediately before the website is built.

INPUT:
- Raw fundus image path

EXPECTED OUTPUT:
- One structured dict containing every phase's output, e.g.:
```json
{
  "phase1": {"quality_label": "...", "quality_score": 0.0, "preprocessed_image": "..."},
  "phase2": {"vessel_overlay": "...", "lesion_overlay": "...", "ma_count": 0},
  "phase3": {"severity_class": 0, "confidence": 0.0, "referable_decision": "...", "grade_alone_decision": "..."},
  "phase4": {"heatmap_overlay": "..."},
  "stopped_at_phase1": false
}
```

FILES TO CREATE:
- `pipeline/report.py`
- `tests/test_report.py`

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-005, TASK-009, TASK-013, TASK-014

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `run_full_pipeline(image_path) -> dict` calling, in order: `quality.run_quality_gate`, then (if not Reject) `structure.run_vessel_segmentation`/`run_lesion_segmentation`/`run_ma_detection`, then `grading.run_grading` + `apply_calibration`, then `decision.decide`, then `explain.run_gradcam`.
2. If Phase 1 returns Reject, set `stopped_at_phase1: true` and skip all later phases — return the partial result cleanly, not an error.
3. Wrap each phase call so that a failure in one phase produces a clear, phase-labeled error rather than an unlabeled stack trace (per HANDOFF.md's error-handling rules).

COMMANDS:
```bash
python -m pytest tests/test_report.py
```

VALIDATION / TEST PROCEDURE:
1. Run on a Good-quality demo image — confirm all four phase keys are populated.
2. Run on a Reject-quality demo image — confirm `stopped_at_phase1: true` and phases 2–4 are absent or null, with no error.

EXPECTED RESULT:
One clean entry point for the website.

DONE WHEN:
Tests pass for both the full-pipeline and stopped-at-Phase-1 cases.

DO NOT:
- Build any web/HTTP code here — that's TASK-017.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-015: Final report assembly"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-016 | PHASE 4 CHECKPOINT

**Layer/Phase:** Phase 4 — checkpoint/validation

**What:** Verify the complete four-phase pipeline (via `run_full_pipeline`) on the full demo set.

**Why:** Last checkpoint before the website is wired up — confirms the pipeline itself is solid, independent of any UI bugs that might otherwise mask pipeline issues.

**Context:** Closes out all pipeline-logic phases.

**Input:**
- Full `data/demo/` set

**Output:**
- `docs/checkpoints/phase4.md`

**Files to create:**
- `docs/checkpoints/phase4.md`

**Files to modify:**
- None

**Needs:**
- TASK-015

**Implementation:**
1. Run `run_full_pipeline()` on every image in `data/demo/`.
2. Record per-image results in the checkpoint file, plus overall pass/fail.
3. Explicitly list every known limitation carried forward (fallback decision fusion, unfitted calibration temperature, skipped ensemble, skipped NV, etc.) in one place.

**Commands:**
```bash
python -m pytest tests/
```

**Validation:**
1. Every demo image completes without an unhandled error.
2. All documented limitations from earlier checkpoints are consolidated here.

**Expected result:** A single, trustworthy checkpoint document a judge or teammate could read to understand exactly what works and what's simplified.

**Done when:** `docs/checkpoints/phase4.md` states "Ready for next phase: YES."

**Do NOT:**
- Start website work in this task.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-016 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly).

TASK: TASK-016 | PHASE 4 CHECKPOINT
LAYER/PHASE: Phase 4 — checkpoint/validation

OBJECTIVE:
Verify the complete four-phase pipeline (via `run_full_pipeline`) on the full demo set. Last checkpoint before the website is wired up — confirms the pipeline itself is solid, independent of any UI bugs that might otherwise mask pipeline issues.

CONTEXT — where this fits:
Closes out all pipeline-logic phases.

INPUT:
- Full `data/demo/` set

EXPECTED OUTPUT:
- `docs/checkpoints/phase4.md`

FILES TO CREATE:
- `docs/checkpoints/phase4.md`

FILES TO MODIFY:
- None

DEPENDENCIES (must already be done):
- TASK-015

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Run `run_full_pipeline()` on every image in `data/demo/`.
2. Record per-image results in the checkpoint file, plus overall pass/fail.
3. Explicitly list every known limitation carried forward (fallback decision fusion, unfitted calibration temperature, skipped ensemble, skipped NV, etc.) in one place.

COMMANDS:
```bash
python -m pytest tests/
```

VALIDATION / TEST PROCEDURE:
1. Every demo image completes without an unhandled error.
2. All documented limitations from earlier checkpoints are consolidated here.

EXPECTED RESULT:
A single, trustworthy checkpoint document a judge or teammate could read to understand exactly what works and what's simplified.

DONE WHEN:
`docs/checkpoints/phase4.md` states "Ready for next phase: YES."

DO NOT:
- Start website work in this task.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-016: PHASE 4 CHECKPOINT"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-017 | Single-page website skeleton

**Layer/Phase:** Integration — Website & Demo

**What:** Build `app/app.py` (Flask or FastAPI) and `app/templates/index.html`: an upload form and a single results page that calls `run_full_pipeline()` and renders every phase's output top to bottom.

**Why:** This is the actual demo interface judges will see.

**Context:** First integration task, depends on the entire pipeline being checkpointed.

**Input:**
- User-uploaded image via a web form

**Output:**
- Rendered HTML page showing: original image → Phase 1 (quality + preprocessed image) → Phase 2 (vessel/lesion overlays, MA count) → Phase 3 (severity, probabilities, confidence, referral decision) → Phase 4 (heatmap, clearly labeled "model attention")

**Files to create:**
- `app/app.py`
- `app/templates/index.html`
- `app/static/` (for any CSS, kept minimal)

**Files to modify:**
- `requirements.txt` (add Flask or FastAPI + a template engine if not built in)

**Needs:**
- TASK-016

**Implementation:**
1. One route: `/` (GET shows upload form, POST accepts an image, runs `run_full_pipeline()`, renders results on the same page).
2. No authentication, no session/database — process the upload in memory or a temp file, discard after rendering.
3. If `stopped_at_phase1` is true, render a clear "image rejected, please recapture" message instead of empty Phase 2–4 sections.
4. Heatmap section must display the label "model attention" directly in the HTML, not just in a code comment.
5. Keep CSS minimal — a single stylesheet, no framework needed.

**Commands:**
```bash
pip install flask
python app/app.py
```

**Validation:**
1. Start the server, open in a browser, upload one Good demo image — confirm every phase section renders with real data.
2. Upload a Reject demo image — confirm the "please recapture" message appears and no broken/empty sections are shown.

**Expected result:** A working, browsable demo interface.

**Done when:** Both validation cases render correctly in an actual browser.

**Do NOT:**
- Add login, database, or multi-page navigation — one page, per HANDOFF.md's UI requirement.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-017 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly); TASK-016 (PHASE 4 CHECKPOINT).

TASK: TASK-017 | Single-page website skeleton
LAYER/PHASE: Integration — Website & Demo

OBJECTIVE:
Build `app/app.py` (Flask or FastAPI) and `app/templates/index.html`: an upload form and a single results page that calls `run_full_pipeline()` and renders every phase's output top to bottom. This is the actual demo interface judges will see.

CONTEXT — where this fits:
First integration task, depends on the entire pipeline being checkpointed.

INPUT:
- User-uploaded image via a web form

EXPECTED OUTPUT:
- Rendered HTML page showing: original image → Phase 1 (quality + preprocessed image) → Phase 2 (vessel/lesion overlays, MA count) → Phase 3 (severity, probabilities, confidence, referral decision) → Phase 4 (heatmap, clearly labeled "model attention")

FILES TO CREATE:
- `app/app.py`
- `app/templates/index.html`
- `app/static/` (for any CSS, kept minimal)

FILES TO MODIFY:
- `requirements.txt` (add Flask or FastAPI + a template engine if not built in)

DEPENDENCIES (must already be done):
- TASK-016

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. One route: `/` (GET shows upload form, POST accepts an image, runs `run_full_pipeline()`, renders results on the same page).
2. No authentication, no session/database — process the upload in memory or a temp file, discard after rendering.
3. If `stopped_at_phase1` is true, render a clear "image rejected, please recapture" message instead of empty Phase 2–4 sections.
4. Heatmap section must display the label "model attention" directly in the HTML, not just in a code comment.
5. Keep CSS minimal — a single stylesheet, no framework needed.

COMMANDS:
```bash
pip install flask
python app/app.py
```

VALIDATION / TEST PROCEDURE:
1. Start the server, open in a browser, upload one Good demo image — confirm every phase section renders with real data.
2. Upload a Reject demo image — confirm the "please recapture" message appears and no broken/empty sections are shown.

EXPECTED RESULT:
A working, browsable demo interface.

DONE WHEN:
Both validation cases render correctly in an actual browser.

DO NOT:
- Add login, database, or multi-page navigation — one page, per HANDOFF.md's UI requirement.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-017: Single-page website skeleton"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-018 | End-to-end demo wiring with the full demo set

**Layer/Phase:** Integration — Website & Demo

**What:** Populate `data/demo/` with the complete hand-picked set (5–8 images per HANDOFF.md's Data Flow section) and confirm every one of them renders correctly through the website.

**Why:** The final demo set must be deliberately chosen to showcase every phase, not just whatever images happened to be used during development.

**Context:** Second integration task, after the website itself works.

**Input:**
- Candidate fundus images to select from (from whatever source datasets are available, respecting that training/validation/test data itself is never copied into `data/demo/` — only a small number of individual images are hand-selected for demo purposes)

**Output:**
- Final `data/demo/` set: one Good-quality, one Borderline/Reject-quality, one Grade-0, one or two other severities if available, one visually "hard" case for the heatmap
- `docs/demo_set.md` describing why each image was chosen

**Files to create:**
- `docs/demo_set.md`

**Files to modify:**
- `data/demo/` (final contents)

**Needs:**
- TASK-017

**Implementation:**
1. Select images per the criteria above.
2. Run each through the live website manually, confirm each phase renders sensibly for each image.
3. Document the selection reasoning and expected result per image in `docs/demo_set.md`, so a teammate presenting the demo knows what to expect from each one.

**Commands:**
```bash
python app/app.py
```

**Validation:**
1. Every image in the final `data/demo/` set renders end-to-end through the actual website with no error.
2. `docs/demo_set.md` accurately describes each image's expected outcome.

**Expected result:** A curated, presentation-ready demo set.

**Done when:** All demo images pass through the live website correctly and are documented.

**Do NOT:**
- Include any image from the sealed test set in `data/demo/`.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-018 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly); TASK-016 (PHASE 4 CHECKPOINT); TASK-017 (Single-page website skeleton).

TASK: TASK-018 | End-to-end demo wiring with the full demo set
LAYER/PHASE: Integration — Website & Demo

OBJECTIVE:
Populate `data/demo/` with the complete hand-picked set (5–8 images per HANDOFF.md's Data Flow section) and confirm every one of them renders correctly through the website. The final demo set must be deliberately chosen to showcase every phase, not just whatever images happened to be used during development.

CONTEXT — where this fits:
Second integration task, after the website itself works.

INPUT:
- Candidate fundus images to select from (from whatever source datasets are available, respecting that training/validation/test data itself is never copied into `data/demo/` — only a small number of individual images are hand-selected for demo purposes)

EXPECTED OUTPUT:
- Final `data/demo/` set: one Good-quality, one Borderline/Reject-quality, one Grade-0, one or two other severities if available, one visually "hard" case for the heatmap
- `docs/demo_set.md` describing why each image was chosen

FILES TO CREATE:
- `docs/demo_set.md`

FILES TO MODIFY:
- `data/demo/` (final contents)

DEPENDENCIES (must already be done):
- TASK-017

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Select images per the criteria above.
2. Run each through the live website manually, confirm each phase renders sensibly for each image.
3. Document the selection reasoning and expected result per image in `docs/demo_set.md`, so a teammate presenting the demo knows what to expect from each one.

COMMANDS:
```bash
python app/app.py
```

VALIDATION / TEST PROCEDURE:
1. Every image in the final `data/demo/` set renders end-to-end through the actual website with no error.
2. `docs/demo_set.md` accurately describes each image's expected outcome.

EXPECTED RESULT:
A curated, presentation-ready demo set.

DONE WHEN:
All demo images pass through the live website correctly and are documented.

DO NOT:
- Include any image from the sealed test set in `data/demo/`.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-018: End-to-end demo wiring with the full demo set"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-019 | One-command launch hardening

**Layer/Phase:** Integration — Website & Demo

**What:** Make the whole prototype startable with a single command, with clear error messages if any model artifact is missing.

**Why:** A hackathon demo cannot afford a multi-step manual startup or a cryptic crash mid-presentation.

**Context:** Third integration task.

**Input:**
- A clean checkout of the repository plus the models directory populated (or intentionally not populated, to test the error path)

**Output:**
- A single launch script/command and a startup check that reports exactly which models are missing, if any, before attempting to serve requests

**Files to create:**
- `run_demo.sh` (or `.bat` equivalent) — a one-command launcher wrapping `python app/app.py`
- `pipeline/startup_check.py`: verifies every expected model directory has both an artifact and a valid `metadata.json` before the server starts accepting requests

**Files to modify:**
- `app/app.py` (call the startup check before serving)
- `README.md` (add the exact one-command launch instructions)

**Needs:**
- TASK-018

**Implementation:**
1. `startup_check.py` iterates over all five model directories, calls `contract.load_contract` on each, and prints a clear summary: which models are ready, which are missing, and what to do about it.
2. If any required model is missing, the server can still start (for demoing partially-built phases during development) but must clearly show, on the results page, which phase couldn't run and why — never silently skip a phase.
3. Update `README.md` with the exact commands to install dependencies and launch.

**Commands:**
```bash
pip install -r requirements.txt
bash run_demo.sh
```

**Validation:**
1. With all models present: one command launches the server and it's immediately usable.
2. With one model directory deliberately emptied: startup check clearly reports which one is missing, and the website surfaces that specific phase as unavailable rather than crashing.

**Expected result:** A reliable, presentation-safe launch procedure.

**Done when:** Both validation cases behave as described.

**Do NOT:**
- Make the startup check silently continue with a fabricated result for a missing model.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-019 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly); TASK-016 (PHASE 4 CHECKPOINT); TASK-017 (Single-page website skeleton); TASK-018 (End-to-end demo wiring with the full demo set).

TASK: TASK-019 | One-command launch hardening
LAYER/PHASE: Integration — Website & Demo

OBJECTIVE:
Make the whole prototype startable with a single command, with clear error messages if any model artifact is missing. A hackathon demo cannot afford a multi-step manual startup or a cryptic crash mid-presentation.

CONTEXT — where this fits:
Third integration task.

INPUT:
- A clean checkout of the repository plus the models directory populated (or intentionally not populated, to test the error path)

EXPECTED OUTPUT:
- A single launch script/command and a startup check that reports exactly which models are missing, if any, before attempting to serve requests

FILES TO CREATE:
- `run_demo.sh` (or `.bat` equivalent) — a one-command launcher wrapping `python app/app.py`
- `pipeline/startup_check.py`: verifies every expected model directory has both an artifact and a valid `metadata.json` before the server starts accepting requests

FILES TO MODIFY:
- `app/app.py` (call the startup check before serving)
- `README.md` (add the exact one-command launch instructions)

DEPENDENCIES (must already be done):
- TASK-018

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. `startup_check.py` iterates over all five model directories, calls `contract.load_contract` on each, and prints a clear summary: which models are ready, which are missing, and what to do about it.
2. If any required model is missing, the server can still start (for demoing partially-built phases during development) but must clearly show, on the results page, which phase couldn't run and why — never silently skip a phase.
3. Update `README.md` with the exact commands to install dependencies and launch.

COMMANDS:
```bash
pip install -r requirements.txt
bash run_demo.sh
```

VALIDATION / TEST PROCEDURE:
1. With all models present: one command launches the server and it's immediately usable.
2. With one model directory deliberately emptied: startup check clearly reports which one is missing, and the website surfaces that specific phase as unavailable rather than crashing.

EXPECTED RESULT:
A reliable, presentation-safe launch procedure.

DONE WHEN:
Both validation cases behave as described.

DO NOT:
- Make the startup check silently continue with a fabricated result for a missing model.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-019: One-command launch hardening"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-020 | Final demo hardening / dry run checkpoint

**Layer/Phase:** Integration — Website & Demo

**What:** Perform one full, uninterrupted dry run of the entire demo as if presenting to judges, and fix anything that breaks the flow.

**Why:** Final quality gate before the prototype is considered complete.

**Context:** Last integration task.

**Input:**
- The complete, launched application and the final `data/demo/` set

**Output:**
- `docs/checkpoints/final_dry_run.md`

**Files to create:**
- `docs/checkpoints/final_dry_run.md`

**Files to modify:**
- Whatever files are needed to fix issues found during the dry run (list them explicitly in the checkpoint doc)

**Needs:**
- TASK-019

**Implementation:**
1. Simulate an actual presentation: launch with one command, upload each demo image in sequence, narrate what a presenter would say at each phase.
2. Note timing (how long each image takes end-to-end) and anything visually confusing or slow.
3. Fix any issues found, then re-run the full dry run once more to confirm.
4. Record final status, all known limitations (consolidated from every earlier checkpoint), and confirm the prototype is presentation-ready.

**Commands:**
```bash
bash run_demo.sh
python -m pytest tests/
```

**Validation:**
1. Full dry run completes with no crashes, confusing states, or silently wrong results.
2. All tests still pass.

**Expected result:** A prototype confirmed ready for the actual hackathon presentation.

**Done when:** `docs/checkpoints/final_dry_run.md` states the prototype is presentation-ready, with a consolidated limitations list.

**Do NOT:**
- Add new features during this task — only fix what breaks the existing, agreed scope.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-020 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly); TASK-016 (PHASE 4 CHECKPOINT); TASK-017 (Single-page website skeleton); TASK-018 (End-to-end demo wiring with the full demo set); TASK-019 (One-command launch hardening).

TASK: TASK-020 | Final demo hardening / dry run checkpoint
LAYER/PHASE: Integration — Website & Demo

OBJECTIVE:
Perform one full, uninterrupted dry run of the entire demo as if presenting to judges, and fix anything that breaks the flow. Final quality gate before the prototype is considered complete.

CONTEXT — where this fits:
Last integration task.

INPUT:
- The complete, launched application and the final `data/demo/` set

EXPECTED OUTPUT:
- `docs/checkpoints/final_dry_run.md`

FILES TO CREATE:
- `docs/checkpoints/final_dry_run.md`

FILES TO MODIFY:
- Whatever files are needed to fix issues found during the dry run (list them explicitly in the checkpoint doc)

DEPENDENCIES (must already be done):
- TASK-019

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Simulate an actual presentation: launch with one command, upload each demo image in sequence, narrate what a presenter would say at each phase.
2. Note timing (how long each image takes end-to-end) and anything visually confusing or slow.
3. Fix any issues found, then re-run the full dry run once more to confirm.
4. Record final status, all known limitations (consolidated from every earlier checkpoint), and confirm the prototype is presentation-ready.

COMMANDS:
```bash
bash run_demo.sh
python -m pytest tests/
```

VALIDATION / TEST PROCEDURE:
1. Full dry run completes with no crashes, confusing states, or silently wrong results.
2. All tests still pass.

EXPECTED RESULT:
A prototype confirmed ready for the actual hackathon presentation.

DONE WHEN:
`docs/checkpoints/final_dry_run.md` states the prototype is presentation-ready, with a consolidated limitations list.

DO NOT:
- Add new features during this task — only fix what breaks the existing, agreed scope.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-020: Final demo hardening / dry run checkpoint"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

### TASK-021 | Simulink workflow simulation (separate track)

**Layer/Phase:** Simulink — Separate Track (not part of the per-image website pipeline)

**What:** Build a standalone MATLAB/Simulink SimEvents model simulating district-scale patient flow: image arrival → capture/recapture → AI → human review → referral.

**Why:** Required by the PRD (district-scale resource planning), but architecturally and operationally independent of the per-image demo pipeline.

**Context:** Can be built in parallel with any of the tasks above by a different team member — has no dependency on the website.

**Input:**
- Measured (not assumed) referral rate, ungradable rate, and review time from the team's own pipeline testing (e.g. from the Phase checkpoints above)

**Output:**
- A Simulink model file
- A results export (e.g. a chart showing technician-to-ophthalmologist ratio vs. bottleneck) saved as a standalone artifact — image or short report, not wired into the website

**Files to create:**
- `matlab/workflow_simulation.slx`
- `docs/checkpoints/simulink_results.md`

**Files to modify:**
- None (fully independent of `pipeline/` and `app/`)

**Needs:**
- None (can start anytime; benefits from real rates once TASK-005/009/013/016 checkpoints exist, but is not blocked by them)

**Implementation:**
1. Build the SimEvents queueing model per the Final Model Stack's Stage 12 description: arrival → capture/recapture → AI → review → referral.
2. Parameterize with the team's own measured rates once available (use placeholder/assumed rates only if real ones aren't ready yet, and label them explicitly as placeholders in the results doc).
3. Sweep technician-to-ophthalmologist ratio to find the bottleneck; export the resulting chart.
4. Write up the result in `docs/checkpoints/simulink_results.md`.

**Commands:**
_(MATLAB/Simulink GUI-driven — no CLI commands required beyond opening the `.slx` file in MATLAB)_

**Validation:**
1. Model runs without error in Simulink.
2. The bottleneck sweep produces a sensible chart (e.g. review time growing as ophthalmologist count drops).

**Expected result:** A second, standalone demo artifact for district-scale planning, shown separately from the live website.

**Done when:** `docs/checkpoints/simulink_results.md` documents the model, its parameters (real or placeholder, clearly labeled), and the resulting chart.

**Do NOT:**
- Wire this into the live per-image website.
- Present placeholder rates as measured data.

**MASTER PROMPT (paste into a fresh Claude context):**

`````text
YOU ARE IMPLEMENTING TASK-021 OF THE NETRA-DR PROTOTYPE.

PROJECT: NETRA-DR — explainable AI diabetic retinopathy screening prototype for SIH26038 (MathWorks). This is a hackathon prototype, not production software: no authentication, no database, no cloud infrastructure, no microservices, unless a task explicitly says otherwise.

BEFORE ANYTHING ELSE: read docs/HANDOFF.md in full. It contains the four-phase architecture, the model contract, the MATLAB/inference separation strategy, and the engineering/ML/data-leakage/error-handling rules that apply to every task, including this one. Do not skip it, even if this prompt looks self-contained.

CURRENT PROJECT STATE: The following tasks are assumed already complete (do not redo them, only use what they produced): TASK-001 (Create repository structure); TASK-002 (Define and implement the model contract); TASK-003 (Preprocessing function (no model)); TASK-004 (Integrate the IQA (quality) model); TASK-005 (PHASE 1 CHECKPOINT); TASK-006 (Integrate vessel segmentation model); TASK-007 (Integrate lesion segmentation models (HE/EX/SE)); TASK-008 (Integrate MA (microaneurysm) detector); TASK-009 (PHASE 2 CHECKPOINT); TASK-010 (Integrate DR grading model); TASK-011 (Add calibration (temperature scaling)); TASK-012 (Decision fusion (referral decision)); TASK-013 (PHASE 3 CHECKPOINT); TASK-014 (Grad-CAM explainability); TASK-015 (Final report assembly); TASK-016 (PHASE 4 CHECKPOINT); TASK-017 (Single-page website skeleton); TASK-018 (End-to-end demo wiring with the full demo set); TASK-019 (One-command launch hardening); TASK-020 (Final demo hardening / dry run checkpoint).

TASK: TASK-021 | Simulink workflow simulation (separate track)
LAYER/PHASE: Simulink — Separate Track (not part of the per-image website pipeline)

OBJECTIVE:
Build a standalone MATLAB/Simulink SimEvents model simulating district-scale patient flow: image arrival → capture/recapture → AI → human review → referral. Required by the PRD (district-scale resource planning), but architecturally and operationally independent of the per-image demo pipeline.

CONTEXT — where this fits:
Can be built in parallel with any of the tasks above by a different team member — has no dependency on the website.

INPUT:
- Measured (not assumed) referral rate, ungradable rate, and review time from the team's own pipeline testing (e.g. from the Phase checkpoints above)

EXPECTED OUTPUT:
- A Simulink model file
- A results export (e.g. a chart showing technician-to-ophthalmologist ratio vs. bottleneck) saved as a standalone artifact — image or short report, not wired into the website

FILES TO CREATE:
- `matlab/workflow_simulation.slx`
- `docs/checkpoints/simulink_results.md`

FILES TO MODIFY:
- None (fully independent of `pipeline/` and `app/`)

DEPENDENCIES (must already be done):
- None (can start anytime; benefits from real rates once TASK-005/009/013/016 checkpoints exist, but is not blocked by them)

IMPLEMENTATION INSTRUCTIONS — follow exactly, do not add scope:
1. Build the SimEvents queueing model per the Final Model Stack's Stage 12 description: arrival → capture/recapture → AI → review → referral.
2. Parameterize with the team's own measured rates once available (use placeholder/assumed rates only if real ones aren't ready yet, and label them explicitly as placeholders in the results doc).
3. Sweep technician-to-ophthalmologist ratio to find the bottleneck; export the resulting chart.
4. Write up the result in `docs/checkpoints/simulink_results.md`.

COMMANDS:
_(MATLAB/Simulink GUI-driven — no CLI commands required beyond opening the `.slx` file in MATLAB)_

VALIDATION / TEST PROCEDURE:
1. Model runs without error in Simulink.
2. The bottleneck sweep produces a sensible chart (e.g. review time growing as ophthalmologist count drops).

EXPECTED RESULT:
A second, standalone demo artifact for district-scale planning, shown separately from the live website.

DONE WHEN:
`docs/checkpoints/simulink_results.md` documents the model, its parameters (real or placeholder, clearly labeled), and the resulting chart.

DO NOT:
- Wire this into the live per-image website.
- Present placeholder rates as measured data.

FAILURE HANDLING: if something fails, apply docs/HANDOFF.md's Error-Handling Rules — detect the failure, produce a clear and specific error, and do not silently continue with an invalid or fabricated result. A "missing model artifact" error is an expected, correct outcome if the MATLAB-exported model for this stage isn't in place yet — that is not a bug to work around, it is the contract working as intended.

GIT CHECKPOINT (only after Done-when is verified):
git add .
git commit -m "TASK-021: Simulink workflow simulation (separate track)"

AFTER COMPLETING THIS TASK:
Update docs/TASKS.md using its own update procedure (move this task to Completed, advance Current/Next task, log any decision made, record the validated result). Do NOT start the next task. Stop.
`````
---

## Dependency Graph

```text
TASK-001 (repo structure)
   └─→ TASK-002 (model contract)
          ├─→ TASK-004 (IQA model)     ←── TASK-003 (preprocessing) ─┘
          │        └─→ TASK-005 (PHASE 1 CHECKPOINT)
          │                ├─→ TASK-006 (vessel seg)
          │                ├─→ TASK-007 (lesion seg)
          │                ├─→ TASK-008 (MA detection)
          │                │        └─→ TASK-009 (PHASE 2 CHECKPOINT)
          │                │                ├─→ TASK-010 (grading)
          │                │                │      └─→ TASK-011 (calibration)
          │                │                │             └─→ TASK-012 (decision fusion) ←── needs TASK-007, TASK-008
          │                │                │                    └─→ TASK-013 (PHASE 3 CHECKPOINT)
          │                │                │                            └─→ TASK-014 (Grad-CAM)
          │                │                │                                    └─→ TASK-015 (report assembly) ←── needs TASK-005, TASK-009, TASK-013
          │                │                │                                            └─→ TASK-016 (PHASE 4 CHECKPOINT)
          │                │                │                                                    └─→ TASK-017 (website skeleton)
          │                │                │                                                            └─→ TASK-018 (demo set wiring)
          │                │                │                                                                    └─→ TASK-019 (launch hardening)
          │                │                │                                                                            └─→ TASK-020 (final dry run)

TASK-021 (Simulink) — independent, no incoming dependency, may run in parallel with any of the above
```

No circular dependencies. Execution order is TASK-001 through TASK-020 sequentially (with TASK-006/007/008 and TASK-010's prerequisite chain as the only tasks that could, in principle, be split across parallel team members within their phase); TASK-021 may be done by a separate person at any time.

---

## Output File Map

```text
TASK-001 → netra-dr/ full directory skeleton, README.md
TASK-002 → pipeline/contract.py, tests/test_contract.py, docs/model_contract_spec.md
TASK-003 → pipeline/preprocessing.py, tests/test_preprocessing.py, configs/preprocessing.json
TASK-004 → pipeline/quality.py, tests/test_quality.py
TASK-005 → docs/checkpoints/phase1.md, data/demo/ (first 2 images)
TASK-006 → pipeline/structure.py (vessel fns), tests/test_structure_vessel.py
TASK-007 → pipeline/structure.py (+lesion fns), tests/test_structure_lesion.py
TASK-008 → pipeline/structure.py (+MA fns), tests/test_structure_ma.py
TASK-009 → docs/checkpoints/phase2.md
TASK-010 → pipeline/grading.py, tests/test_grading.py
TASK-011 → pipeline/grading.py (+calibration fn), tests/test_calibration.py, configs/calibration.json
TASK-012 → pipeline/decision.py, tests/test_decision.py, models/decision_fusion/ or configs/decision_rule.json
TASK-013 → docs/checkpoints/phase3.md
TASK-014 → pipeline/explain.py, tests/test_explain.py
TASK-015 → pipeline/report.py, tests/test_report.py
TASK-016 → docs/checkpoints/phase4.md
TASK-017 → app/app.py, app/templates/index.html, app/static/
TASK-018 → data/demo/ (final set), docs/demo_set.md
TASK-019 → run_demo.sh, pipeline/startup_check.py, README.md (updated)
TASK-020 → docs/checkpoints/final_dry_run.md
TASK-021 → matlab/workflow_simulation.slx, docs/checkpoints/simulink_results.md
```
