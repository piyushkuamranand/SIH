# Model Card — DR Severity Grading (ICDR 0–4)

Generated from `models/grading/metadata.json` and `models/grading/training_history.json`
(the machine-generated source of truth) after `training/train_grading.py`.
Re-run the training script and re-read those files if these numbers look stale.

## Architecture (current — v2.0.0)

- **ResNet-50, ImageNet-pretrained** (`torchvision.models.ResNet50_Weights.IMAGENET1K_V2`),
  matching the Final Model Stack Stage 7 target.
- Body (conv1…layer4) → global average pool → single `Linear(2048, 5)` head.
  This GAP→FC structure makes the class activation mapping in
  `pipeline/explain.py` **exact** (Zhou et al. 2016 CAM), not an approximation:
  the FC layer's weight row for the predicted class is exported alongside the
  model (`gradcam_fc_weights.npy`, shape `(5, 2048)`) and used directly against
  the last conv block's feature map — no backward pass needed at inference.
- Trained on **GPU** (NVIDIA RTX 3050 Laptop, 6GB, CUDA 12.6) — see
  "Environment history" below for why this took two attempts.

## Environment history (why there was an earlier ResNet-18-from-scratch version)

An earlier session attempt trained ResNet-18 from scratch on CPU, because at
that time this machine had CPU-only PyTorch and no verified CUDA path. That
model was explicitly superseded, never shipped as final, and its checkpoint
was discarded before this run. The CUDA environment was then verified
end-to-end (`torch 2.14.0+cu126`, `torch.cuda.is_available()==True`,
`RTX 3050 6GB`, live GPU tensor test) before this ResNet-50 run — see
`docs/env_snapshots/` for the before/after package snapshots.

## Data

- **Combined split** (`training/prepare_grading_splits.py`): APTOS 2019
  (3,662 images) + IDRiD grading-**train** (413 images, non-sealed) = 4,075
  images. **DDR excluded** (not downloaded, per instruction). **IDRiD
  grading-test (103 images) excluded — that is the project's sealed external
  test set** and was never read by the split script or this training run.
- Cross-dataset near-duplicate check (average-hash, Hamming ≤ 4): 4,075 images
  → 1,647 dedup groups, **0 groups span both datasets** (expected — different
  source clinics/countries). Every dedup group kept entirely in one split.
- Split: **3,741 train / 334 val** (image-level — neither Kaggle's nor
  IDRiD's grading CSV exposes a patient/exam id; documented limitation, not
  claimed as patient-level). See `data/splits/grading_dedup_report.json`.
- Preprocessing: every image passes through `pipeline.preprocessing.preprocess()`
  (FOV crop → resize 512×512 → CLAHE → normalize) — **the exact function the
  live app calls at inference** — via `training/preprocessing_cache.py`, then
  resized to 224×224 and ImageNet-normalized for the model. This fixes a real
  train/serve mismatch bug in the previous version of this script (which used
  raw PIL resize with no FOV crop or CLAHE).

## Training

- Optimizer: AdamW, lr=3e-4, weight_decay=1e-4, cosine annealing schedule.
- Loss: class-weighted cross-entropy (inverse frequency: `[0.41, 2.27, 0.73, 3.24, 2.45]`
  for classes 0–4 — grade 0 is ~49% of the combined train set, grade 3 ~6%).
- Batch size: **48**, chosen empirically (`find_safe_batch_size()` — tried 64
  first, fit at 5.70GB peak, backed off one safety step to 48 for a 6GB card
  rather than run a multi-hour job at 95% VRAM).
- Mixed precision: not used for the shipped run (`--amp` flag exists and is
  validated-before-use if enabled; this run used fp32 and still trained a full
  epoch in ~60s, so AMP wasn't necessary).
- Seed: 42. Augmentation: horizontal/vertical flip, ±25° rotation, mild
  brightness/contrast jitter — no blur/heavy noise (would erase
  microaneurysm-scale signal relevant to the wider pipeline).
- Early stopping: patience=6 on validation QWK. **Stopped at epoch 27** (best
  at epoch 21); 30 epochs configured, 90-minute time budget configured but not
  needed. **Total training time: 27.3 minutes.**
- GPU smoke test (forward+backward+optimizer step+checkpoint write, real data,
  real pretrained weights) run and passed before the timed run.

## Results — INTERNAL VALIDATION SPLIT ONLY (334 images, not sealed/external)

Per project ML rules, these are reported as measured on the combined
APTOS+IDRiD internal validation split — **not** the PS sensitivity/specificity
claim, which requires the sealed external test (Messidor-2 / IDRiD
grading-test), run exactly once after everything is frozen.

| Metric | Value |
|---|---|
| QWK | **0.888** |
| Referable (Grade≥2) sensitivity | **89.4%** |
| Referable (Grade≥2) specificity | **89.0%** |
| Macro F1 | 0.715 |

Per-class sensitivity / specificity (support = validation count):

| Grade | Sensitivity | Specificity | Support |
|---|---|---|---|
| 0 (No DR) | 88.4% | 98.7% | 95 |
| 1 (Mild) | 70.0% | 89.8% | 60 |
| 2 (Moderate) | 77.1% | 86.0% | 105 |
| 3 (Severe) | 50.0% | 97.3% | 36 |
| 4 (Proliferative) | 68.4% | 95.9% | 38 |

Confusion matrix (rows=true, cols=predicted, order 0–4):
```
[[84 11  0  0  0]
 [ 1 42 17  0  0]
 [ 2 16 81  4  2]
 [ 0  0  8 18 10]
 [ 0  1  7  4 26]]
```
Grade 3 has the weakest per-class sensitivity (50%, n=36) — most Grade-3
errors are predicted as Grade 4 (10/36) or Grade 2 (8/36), i.e. adjacent-grade
confusion, which is the expected failure mode for ordinal grading and is
exactly why the **referable (Grade≥2) binary metric** — which does not
distinguish 2 vs 3 vs 4 — is the PS-relevant number, not per-grade accuracy.

## Calibration (temperature scaling, fit on the same validation split)

| | Before | After (T=2.80) |
|---|---|---|
| NLL | 1.167 | 0.720 |
| ECE | 0.166 | **0.046** |
| Brier | 0.420 | 0.374 |

All three metrics improve after calibration — the model was meaningfully
overconfident (T=2.8 is a substantial softening), consistent with training a
high-capacity pretrained backbone on ~3.7k images.

## ONNX export

- Two outputs: `logits` (5,) and `features` (2048×7×7, last conv block —
  consumed by `pipeline/explain.py` for exact CAM).
- Parity check (same input, PyTorch vs onnxruntime): logits max abs diff
  `4.5e-7`, features max abs diff `1.5e-5` — effectively exact (float32
  precision limit).
- Fresh-process validation (contract load → real image → `pipeline.preprocessing.preprocess()`
  → `pipeline.grading.run_grading()` → `pipeline.grading.apply_calibration()` →
  `pipeline.explain.run_gradcam()`) confirmed working end-to-end, CAM mode
  `cam_fc_weighted` (exact, class-specific — not the degraded fallback).

## Known limitations

1. **Not evaluated on the sealed external test** (Messidor-2 / IDRiD
   grading-test, 103 images) — that is intentional and reserved until the
   full system (lesion models, decision fusion) is frozen, per project policy.
   Do not read the 88.9% QWK / 89% referable sensitivity/specificity above as
   the PS claim.
2. Grade 1 and Grade 3 have the lowest per-class sensitivity (70%, 50%) —
   both are minority classes even after class weighting, and both sit at
   ordinal boundaries most prone to adjacent-grade confusion.
3. Decision fusion (`models/decision_fusion/`) is not fitted — MA/HE/EX
   features default to zero/absent until the Phase 2 lesion models exist, so
   `referable_decision` currently reduces to the quality-tier grade-probability
   threshold fallback (`fitted=False`, honestly reported in the UI).
4. Ensemble (Final Model Stack Stage 10) not built — single model only.
5. Image-level, not patient-level, split (neither source CSV exposes a
   patient/exam id).

## Artifact paths

- `models/grading/grading_model.onnx` — inference artifact
- `models/grading/gradcam_fc_weights.npy` — CAM weight matrix
- `models/grading/metadata.json` — model contract
- `models/grading/training_history.json` — full per-epoch log + run args
- `configs/calibration.json` — fitted temperature scaling

## Next steps (in priority order)

1. Train the Phase 2 evidence models (vessel, HE/EX/SE, MA) on DRIVE/IDRiD,
   then fit the decision-fusion logistic regression (Final Model Stack Section 3).
2. If DDR later becomes available: retrain and compare QWK against this
   APTOS+IDRiD baseline on the *same* validation protocol (ablation).
3. Seal Messidor-2 / IDRiD grading-test; run the external evaluation exactly
   once after everything above is frozen (blueprint MLR-003).
