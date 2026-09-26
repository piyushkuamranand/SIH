# NETRA-DR Final System Verification

**Date:** 2026-09-26
**Scope:** Full audit of the Python localhost application and all AI/ML stages. No training performed. No architecture changed. No dataset downloaded.

---

## 1. Environment

| Component | Value |
|---|---|
| Python executable | `C:\Users\hp\anaconda3\python.exe` (used identically by Flask, direct CLI inference, `pytest`, and MATLAB's `pyenv`) |
| Python version | 3.13.5 |
| pip version | 25.1 |
| PyTorch | 2.14.0+cu126 (training only — never imported by `app/` or `pipeline/`) |
| torchvision | 0.29.0+cu126 (training only) |
| CUDA available | True (training machine has an RTX 3050 6GB) — **irrelevant to serving**: all inference explicitly uses `onnxruntime`'s `CPUExecutionProvider` only (verified: no `CUDAExecutionProvider` reference anywhere in `pipeline/*.py`) |
| ONNX Runtime | 1.30.0 |
| NumPy | 2.1.3 |
| OpenCV (`opencv-python`) | 5.0.0 |
| Flask | 3.1.0 |
| scikit-learn | 1.6.1 (available, not used by the serving path) |
| Pillow | 11.1.0 |
| scikit-image | 0.25.0 (available, not used by the serving path) |
| MATLAB Python interoperability | `pyenv.Executable = C:\Users\hp\anaconda3\python.EXE` — **confirmed identical to the app/CLI/test environment**. The concern that MATLAB might point at a different, onnxruntime-less `Python313` install does not apply to this repository's actual current state. |

No environment mismatch found. No package was installed into any environment during this audit.

---

## 2. Model Inventory

| Model | Artifact | Architecture (verified) | Dataset role | Input shape | Output shape(s) | Load status |
|---|---|---|---|---|---|---|
| Grading | `models/grading/grading_model.onnx` (89.6 MB) | ResNet-50 — **confirmed**: `features` output has 2048 channels (ResNet-50's final block; ResNet-18 would be 512). No substitution. | APTOS 2019 + IDRiD grading-train | `[1,3,224,224]` float32 | `logits [1,5]`, `features [1,2048,7,7]` | **PASS** |
| Vessel segmentation | `models/vessel_seg/vessel_model.onnx` (29.6 MB) | U-Net | DRIVE | `[1,3,512,512]` float32 | `vessel_prob [1,1,512,512]` float32, sigmoid-activated | **PASS** |
| Lesion segmentation | `models/lesion_seg/lesion_model.onnx` (29.6 MB) | U-Net, 3-channel | IDRiD segmentation | `[1,3,512,512]` float32 | `lesion_probs [1,3,512,512]` float32, channel order = `metadata.json["mask_labels"]` = `["HE","EX","SE"]` | **PASS** |
| MA detector (FP-reducer) | `models/ma_detector/ma_fp_reducer.onnx` (0.3 MB) | Small CNN, softmax-activated | IDRiD segmentation (patches, via classical top-hat candidates) | `[1,3,32,32]` float32 (patch, not the 512×512 canonical space — `input_size` in metadata refers to the canonical image space candidates are extracted from, `patch_size=32` is the classifier's own tensor size — verified, not a bug) | `probs [1,2]` float32 | **PASS** |
| Quality | `models/quality/iqa_thresholds.json` | Rule-based (no neural network) — confirmed via `contract["framework"]=="rule_based"` | None (heuristic) | N/A | `GOOD`/`BORDERLINE`/`REJECT` + measured reasons | **PASS** |
| Calibration | `configs/calibration.json` | Temperature scaling | Fitted on the grading validation split (334 images) | N/A | `temperature=2.80, fitted=true` | **PASS** — verified numerically (0.9612→0.9411-scale softening direction correct on real inference) |
| NV | none | — | FGADR (not downloaded) | — | — | **UNAVAILABLE** (honest, no fabrication) |
| Decision fusion (learned) | none (`models/decision_fusion/` does not exist) | — | — | — | — | **fallback active** (`fitted=false`), never mislabeled as learned |

For every neural model: file exists, non-empty, ONNX graph loads via `onnxruntime.InferenceSession`, input/output names and shapes match what `pipeline/*.py` code expects exactly (cross-checked line-by-line against `pipeline/grading.py`, `pipeline/structure.py`), preprocessing/postprocessing agree with `metadata.json` contracts, no hardcoded class order/threshold/mask order found anywhere in the inference code (all read from contract). No silent fallback producing fake predictions was found in any stage.

---

## 3. Pipeline Verification

Traced end-to-end through the real code (`pipeline/report.py:run_full_pipeline`), not documentation:

| Stage | Verified behavior |
|---|---|
| Quality | Real rule-based measurement (Laplacian variance in canonical 512×512 space, illumination clipping, FOV coverage) against `models/quality/iqa_thresholds.json`. REJECT correctly halts the pipeline before any downstream stage runs (`stopped_at_phase1=True`, `phase2`/`phase3`/`phase4` are `None`, not fabricated). |
| Preprocessing | FOV crop → resize → CLAHE (LAB L-channel) → normalize, `configs/preprocessing.json`-driven. Same function (`pipeline.preprocessing.preprocess`) called by both the quality gate and, indirectly, every downstream stage via its output. No double-preprocessing, no skipped stage, identical whether invoked from Flask, direct CLI, or `pytest` (all call the same `pipeline.report.run_full_pipeline`). |
| Vessels | Real ONNX inference, per-contract normalization, sigmoid threshold at `contract["threshold"]`, binary mask resized to source resolution. |
| Lesions | Real ONNX inference, `mask_labels` order read from contract (never assumed `["HE","EX","SE"]` in code), `he_presence`/`ex_area` computed from real mask pixel counts. |
| MA | Classical top-hat candidate extraction (real morphology, contract-configured radius/threshold) → real CNN FP-reducer ONNX inference per candidate. |
| NV | Correctly returns "unavailable" — no fabricated mask or score. |
| Grading | Real ONNX inference → softmax (or pass-through if already normalized, verified) → argmax → `severity_class`. |
| Calibration | Real temperature scaling against the actual fitted `configs/calibration.json` — never refit during this audit. |
| Attention (Grad-CAM) | Real, exact class-activation map (FC-weights × last-conv feature map from the SAME grading inference call — no separate/inconsistent forward pass). Verified: heatmap changes with input image (different `severity_class` → different class weight row → different map), label is always the literal string `"model attention"`. |
| Decision | Grade-alone and fused decisions computed side by side; fused decision correctly uses the quality-tier fallback (`fitted=false`) since no learned fusion model exists — never mislabeled as learned. |
| Report/UI | Flask template renders every field from the same `run_full_pipeline()` dict the direct CLI path returns — verified identical values for `severity_class` and `referable_decision` on the same image via both paths (Section 12 below). |

---

## 4. Localhost Verification

**Launch command:** `python app/app.py` → `http://127.0.0.1:5000`.

Verified this session, from a state with **zero prior Flask processes running** (all accumulated stray processes from earlier work were identified via `netstat`/`tasklist` and terminated first):

| Check | Result |
|---|---|
| `GET /api/status` | 200, `startup_report.all_ready: true` |
| `GET /` (landing page) | 200, no traceback |
| `POST /` image upload (real file) | 200, full pipeline runs |
| `POST /` demo image selection | 200, all 5 demo cases (`good`, `reject`, `grade0`, `grade2`, `grade4`) work |
| Report/UI sections render | Quality, preprocessing before/after, vessel/HE/EX/SE/MA evidence cards, grade + probability bars, calibrated confidence, model attention heatmap, referral decision — all present with real values |
| `POST /` invalid extension (.txt) | 200, clean "Unsupported file format" message |
| `POST /` corrupted image bytes | 200, clean "Invalid image file" message |
| `POST /` missing model artifact (vessel model temporarily renamed away, then restored) | 200, "Vessel analysis unavailable: model artifact not found." — verified restored afterward, byte-identical |
| `POST /` corrupted ONNX file (grading model overwritten with garbage, then restored from backup) | 200, all downstream sections show "unavailable", zero traceback — verified restored afterward |
| `POST /` tiny image (10×10) | 200, "too small" validation message |
| Repeated/sequential requests | No stale result from a previous image, no file collision (each upload uses a fresh `tempfile.NamedTemporaryFile`, deleted in a `finally` block) |
| Direct-pipeline vs Flask consistency | **Confirmed identical** on `aptos_grade4_875a2fc5fe23.png`: both report `severity_class=4`, `referable_decision=REFER` |

No traceback, no hidden 500, no silent prediction failure observed in any of the above.

---

## 5. Test Results

| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Python (`pytest tests -q`) | **144** | 0 | 0 |
| MATLAB (`matlab/run_tests.m`) | **34** | 0 | 0 |

Covers: contract validation (valid + malformed + missing-artifact cases), preprocessing, quality gate (good/reject/corrupted), grading (real inference + architecture check), calibration (no-op, real fitted config, invalid input), vessels/lesions/MA/model-attention/NV, decision fusion, report assembly, full-pipeline end-to-end, and explicit failure-injection (missing/corrupted model artifacts).

---

## 6. Performance

Measured on this machine, CPU-only inference (`CPUExecutionProvider`), 4 real images through the full production pipeline:

| Stage | Mean latency |
|---|---|
| Quality gate | 217 ms |
| Vessel segmentation | 486 ms |
| Lesion segmentation | 420 ms |
| MA detection | 1,894 ms (dominant, variable — proportional to classical-candidate count per image; each candidate is a separate ONNX call) |
| Grading | 206 ms |
| Calibration | 0.6 ms |
| Decision fusion | 0.9 ms |
| Grad-CAM / model attention | 221 ms |
| **Total (end-to-end)** | **mean 3,446 ms · median 2,925 ms · min 2,208 ms · max 5,724 ms** |

No GPU path exists for serving (by design — `onnxruntime` `CPUExecutionProvider` only). This is real measured inference latency, not the PS's 30-second *ophthalmologist review* budget — the two are different concepts and are labelled separately in the UI.

---

## 7. Evaluation Dataset

**Exact dataset/split:** IDRiD grading-test (`B. Disease Grading`, `"b. Testing Set"`), 103 images with real ICDR ground-truth labels.
**Ground-truth source:** `b. IDRiD_Disease Grading_Testing Labels.csv` (official IDRiD release).
**Unseen during training?** Formally yes — `training/prepare_grading_splits.py` only ever reads `"a. Training Set"`; this file was never referenced anywhere in the training pipeline.
**Unseen during calibration/threshold fitting?** Formally yes, same reason — the 334-image calibration/validation split is drawn exclusively from `"a. Training Set"`.

**However — and this is the critical finding of this audit:**

A rigorous independence check (`training/verify_sealed_test_independence.py`: perceptual average-hash near-duplicate search against the full 4,075-image training pool, followed by `training/investigate_sealed_test_duplicates.py`: direct visual inspection of the closest matches) found:

- **95 of 103 (92%)** sealed test images have a near-duplicate (Hamming distance ≤ 4 on a 16×16 average hash) in the training pool.
- Direct visual inspection of 3 sampled high-similarity pairs (e.g., `IDRiD_007` test vs `IDRiD_073` train) shows **matching optic disc position, matching major vessel arcade branching geometry, and an identical camera FOV notch artifact** — strong evidence these are the **same eye photographed at a different visit**, not a hashing coincidence. File MD5/sizes differ (not literal duplicate files), consistent with a re-capture rather than a copy-paste error in the dataset release.
- Only **8 of 103** images show no near-duplicate: `IDRiD_005, 010, 044, 071, 075, 076, 092, 098`.

**This means the IDRiD grading-test split — assumed throughout this project's prior documentation (blueprint, PRD, model cards) to be a valid independent "sealed" set — is very likely NOT patient-independent from the training pool.** This was never previously verified before this audit; it is a genuine, newly-discovered data-governance defect, not a code bug. IDRiD publishes no patient ID field, so this could not have been checked by ID lookup — only by content-based comparison, which had not been done until now.

**What labelled data exists and eligibility:**

| Candidate | Images | Eligible as unbiased final test? |
|---|---|---|
| APTOS 2019 (all) | 3,662 | ❌ used for training |
| IDRiD grading-train | 413 | ❌ used for training |
| APTOS+IDRiD combined validation split | 334 | ❌ used for model selection (best-epoch checkpoint) and calibration fitting |
| **IDRiD grading-test ("sealed")** | 103 | ⚠️ **formally unseen by the pipeline code, but found NOT reliably patient-independent** (92% flagged, visually confirmed) |
| IDRiD grading-test, hash-clean subset | 8 (6 gradable) | ⚠️ Technically the cleanest candidate, but **statistically powerless** (n=6 gradable, 3 referable/3 non-referable) |
| Messidor-2 | 0 | ❌ not downloaded |

---

## 8. Final Confusion Matrix

Computed by running the **exact frozen production code path** (`pipeline.quality.run_quality_gate` → `pipeline.grading.run_grading` → `pipeline.grading.apply_calibration` → `pipeline.decision.run_decision_fusion`) on all 103 images, using the **fused decision** (the actual production referral decision), no threshold tuning performed against this data.

**(A) Full 103-image nominally-sealed set — flagged as likely contaminated, reported for completeness only:**

Gradable: 99/103 (4 REJECT by the quality gate).

| | Predicted REFER | Predicted NO REFER |
|---|---|---|
| **Actual referable (grade≥2)** | TP = 57 | FN = 5 |
| **Actual non-referable** | FP = 14 | TN = 23 |

**(B) 8-image hash-clean subset — the best-effort "less contaminated" candidate, but n is far too small to be informative:**

Gradable: 6/8 (2 REJECT by the quality gate).

| | Predicted REFER | Predicted NO REFER |
|---|---|---|
| **Actual referable** | TP = 2 | FN = 1 |
| **Actual non-referable** | FP = 0 | TN = 3 |

Raw per-image results: `docs/checkpoints/sealed_test_raw_results.json`. Full aggregated report incl. grade-alone-vs-fused comparison and the "including ungradable as auto-referred" variant: `docs/checkpoints/sealed_test_evaluation.json`.

---

## 9. Final Metrics

**(A) Full 103-image set (likely contaminated — descriptive only, NOT the certified final metric):**

| Metric | Gradable-only (n=99) | Including ungradable, auto-referred (n=103) |
|---|---|---|
| Sensitivity | 91.9% | 92.2% |
| Specificity | 62.2% | 59.0% |
| Precision | 80.3% | 78.7% |
| NPV | 82.1% | 82.1% |
| Accuracy | 80.8% | 79.6% |
| F1 | 0.857 | 0.849 |
| ROC-AUC (referable probability) | see `sealed_test_evaluation.json` | — |
| PR-AUC | see `sealed_test_evaluation.json` | — |
| QWK (5-class, gradable) | see `sealed_test_evaluation.json` | — |

**(B) 8-image hash-clean subset (n=6 gradable — far below any usable statistical power):**

Sensitivity = 2/3 = 66.7%, Specificity = 3/3 = 100.0%. A single flipped prediction changes sensitivity by 33 percentage points. **This number carries essentially no statistical information** and must not be quoted as a result.

## FINAL METRIC STATUS: **NOT VALIDLY COMPUTABLE AS A CERTIFIED UNBIASED FINAL METRIC**

Per the explicit instruction governing this audit: *"If no valid unseen labeled evaluation set is present: DO NOT INVENT A FINAL SCORE... report exactly [that it cannot be validly computed] and list what labeled data is available and why it is ineligible."*

That is exactly the situation found here:
- The full 103-image set is the only one with adequate sample size, but is **not reliably independent** of training (92% flagged, visually confirmed) — using it as "final" would very likely overstate real-world performance via the same eyes appearing (at a different visit) in training.
- The hash-clean 8-image subset is the only genuinely defensible-independence candidate, but at n=6 gradable images it is **statistically meaningless** as a final claim.
- No other eligible labelled, unseen set exists in this repository (Messidor-2 not downloaded; DDR excluded by explicit instruction).

The numbers in Section 9(A) are reported **transparently, with full raw confusion counts**, exactly as measured — because refusing to compute and report them would itself violate the "do not hide errors" and "show the raw confusion counts" instructions. But they must be read as **descriptive results on a compromised test set**, not as NETRA-DR's certified final sensitivity/specificity for referable DR. **No PS-target claim ("achieves >90%/>85%") can be honestly made from this data.**

---

## 10. Known Limitations

- **IDRiD grading-test independence compromised** (Section 7-9 above) — the single most important open item from this audit. Recommended remediation (not performed here, requires a decision from the team, not a code fix): either (a) obtain Messidor-2 (never downloaded, would need a new, explicitly-approved acquisition step — not performed per "do not download datasets"), or (b) manually adjudicate the 95 flagged pairs to determine which, if any, are genuinely independent despite the hash/visual similarity, or (c) explicitly reclassify NETRA-DR's evaluation claim as "internal validation only, no valid external test currently available" in all public-facing materials.
- NV: unavailable, no validated model artifact exists (FGADR not downloaded) — honestly reported everywhere, never fabricated.
- Uncertainty ensemble: unavailable — single model per stage, never presented as an ensemble.
- Decision fusion: fallback/rule-based (quality-tier threshold), not a fitted model — explicitly labelled as such in every output (`fitted: false`, `fusion_status: "using grade-alone fallback, fusion model not yet trained"`).
- Rule-based IQA: heuristic thresholds (blueprint K.2 baseline), not fitted on a labelled quality dataset — documented in the quality module's own docstring.
- OD/fovea localization: not implemented (out of scope for the ML-training and MATLAB-integration work performed in prior sessions).
- MATLAB/Python interoperability: ONNX inference in MATLAB runs via `pyenv`/`py.*` calling `onnxruntime` (no `dlnetwork`/native import — the ONNX Model Format Converter support package is not installed) — documented extensively in `matlab/README.md`; not re-touched this session.
- External validation: not performed with a valid unseen set (Section 7-9).

---

## 11. Exact Demo Instructions

**Start the application:**
```bash
cd D:\SIH-1
python app/app.py
```
Then open `http://127.0.0.1:5000`.

**Run inference (programmatic, no UI):**
```python
from pipeline.report import run_full_pipeline
result = run_full_pipeline("path/to/fundus_image.jpg")
```

**Run tests:**
```bash
python -m pytest tests -q                                    # Python, 144 tests
matlab -batch "run('matlab/run_tests.m')"                     # MATLAB, 34 tests
```

**Reproduce the sealed-test findings:**
```bash
python training/verify_sealed_test_independence.py            # near-duplicate check
python training/investigate_sealed_test_duplicates.py         # visual-match evidence
python training/evaluate_sealed_test.py                       # full evaluation + metrics
```

---

## 12. Final Status Table

| Component | Status | Evidence |
|---|---|---|
| Quality | PASS | Real measurement, correct REJECT/BORDERLINE/GOOD gating, halts pipeline correctly |
| Preprocessing | PASS | FOV crop→resize→CLAHE→normalize, config-driven, identical across all call sites |
| Vessel | PASS | Real ONNX inference, correct mask shape/values |
| Lesion | PASS | Real ONNX inference, contract-driven channel order, no invented subtypes |
| MA | PASS | Real classical+CNN hybrid, non-negative integer count |
| NV | UNAVAILABLE | Honest stub, no fabrication (by design — no model exists) |
| Grading | PASS | Real ResNet-50 ONNX inference, correct 5-class output, architecture verified |
| Calibration | PASS | Real fitted temperature (2.80) applied correctly, numerically verified |
| Grad-CAM | PASS | Real exact class-activation map, changes with input, correctly labelled "model attention" |
| Decision | PASS | Correct grade-alone + fused decisions, fallback status honestly reported |
| Report | PASS | All sections render from real pipeline output, no fabricated content |
| Localhost | PASS | Fresh clean-process launch, all routes verified, no traceback |
| **Final sealed-test metric** | **NOT VALIDLY COMPUTABLE (certified)** | Section 7-9: dataset independence compromised, discovered this audit |
