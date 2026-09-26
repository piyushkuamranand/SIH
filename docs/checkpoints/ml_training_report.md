# NETRA-DR ML Training Report

**Date:** 2026-09-26
**GPU:** NVIDIA GeForce RTX 3050 Laptop (6GB), driver 592.27, CUDA 12.6
**Framework:** PyTorch 2.14.0+cu126, torchvision 0.29.0+cu126
**Scope:** all four Phase 2/3 model-training tasks (grading, vessel, lesion, MA)
completed in one session, per `docs/TASKS.md` TASK-023.

This report is the human-readable summary. Every number below is sourced
from a `models/<stage>/metadata.json` or `training_history.json` file written
directly by the training script that produced it — nothing here is
hand-typed from memory. Re-run the relevant `training/train_*.py` script and
re-read its outputs if these numbers look stale.

---

## 1. Environment

| | Before this session | After |
|---|---|---|
| torch | 2.14.0+cpu | **2.14.0+cu126** |
| torchvision | 0.29.0+cpu | **0.29.0+cu126** |
| CUDA available | False | **True** |
| GPU | (unused) | NVIDIA RTX 3050 Laptop, 6GB |

Full before/after package snapshots: `docs/env_snapshots/`. Verified with a
live GPU tensor computation (4096×4096 matmul, `cuda:0`, no NaNs) before any
training began.

MATLAB (R2026a, this machine) was evaluated as the training platform first
per project convention, and found not viable for this run: no Parallel
Computing Toolbox (no `gpuDevice`, CPU-only), and no ONNX-export support
package installed (`exportONNXNetwork`/`exportNetworkToONNX` both absent) —
so even a MATLAB-trained model could not reach this project's
onnxruntime-based serving contract without an additional package install.
PyTorch+CUDA was the viable path on this hardware.

## 2. Datasets used

| Dataset | Used for | Images used | Excluded |
|---|---|---|---|
| APTOS 2019 | Grading | 3,662 (all) | — |
| IDRiD grading-train | Grading | 413 (all, non-sealed) | IDRiD grading-**test** (103) — sealed, untouched |
| IDRiD segmentation | Lesion (HE/EX/SE), MA | 54 train + 27 test (81 total, all) | — |
| DRIVE | Vessel | 20 training images (16 train / 4 val) | DRIVE "test" folder — no public vessel GT in this download |
| DDR | — | **0** | Not downloaded, excluded per explicit instruction |
| Messidor-2 | — | **0** | Sealed external test — not opened |

`external/EyeQ` and `external/FGR-NET` were inspected and confirmed to
contain **0 files** (`training/audit_datasets.py`) — nothing usable existed
there; this is why Phase 1 uses a rule-based IQA baseline instead of a
learned EyeQ model.

Full audit: `docs/dataset_cards/audit_summary.md` /
`docs/dataset_cards/audit_report.json`.

## 3. Splits

| Model | Split method | Train | Val/Test |
|---|---|---|---|
| Grading | `training/prepare_grading_splits.py` — cross-dataset (APTOS+IDRiD) near-duplicate-aware (aHash, Hamming≤4), class-stratified, **image-level** (neither source exposes patient/exam id — documented limitation) | 3,741 | 334 |
| Vessel | Random 16/4 split of DRIVE's 20 training images — **image-level here IS patient-level** (DRIVE = one eye per subject) | 16 | 4 |
| Lesion | IDRiD's own published segmentation train/test split (not re-split) | 54 | 27 |
| MA | Candidates generated from IDRiD's 54 train images (patch-level, image-independent by construction); evaluated on IDRiD's 27 test images (lesion-level FROC) | 54 imgs → 4,267 patches | 27 imgs |

All splits are seed=42 and reproducible from the committed CSV/JSON split
files under `data/splits/`.

## 4. Preprocessing

Every model consumes the **same canonical preprocessing** the live app uses
at inference — `pipeline.preprocessing.preprocess()` (FOV crop → resize
512×512 → CLAHE → normalize), via `training/preprocessing_cache.py` (grading)
or inlined identically (vessel/lesion/MA, image+mask cropped/resized
jointly to stay pixel-aligned). This fixed a real bug in the previous
version of `train_grading.py`, which used raw-PIL-resize with no FOV crop or
CLAHE — a genuine train/serve mismatch.

## 5. Grading model (headline model)

- **Architecture:** ResNet-50, ImageNet-pretrained (`IMAGENET1K_V2`), GAP→FC
  head (CAM-compatible by construction).
- **Optimizer:** AdamW, **lr=3e-4**, weight_decay=1e-4, cosine annealing.
- **Batch size:** 48 (empirically found safe for 6GB VRAM — 64 fit at 5.70GB,
  backed off one step for headroom on a multi-hour-capable job).
- **Epochs:** 30 configured, early-stopped at **27** (patience=6 on QWK),
  best at **epoch 21**.
- **Seed:** 42.
- **GPU:** RTX 3050 6GB. **Total training time: 27.3 minutes.**

**Validation metrics (334 images, internal — NOT the sealed test):**

| Metric | Value |
|---|---|
| QWK | **0.888** |
| Referable (Grade≥2) sensitivity | **89.4%** |
| Referable (Grade≥2) specificity | **89.0%** |
| Macro F1 | 0.715 |

Grade-wise sensitivity/specificity:

| Grade | Sens | Spec |
|---|---|---|
| 0 | 88.4% | 98.7% |
| 1 | 70.0% | 89.8% |
| 2 | 77.1% | 86.0% |
| 3 | 50.0% | 97.3% |
| 4 | 68.4% | 95.9% |

**Calibration (temperature scaling, same val split):** T=2.80. ECE 0.166→**0.046**,
Brier 0.420→0.374, NLL 1.167→0.720 — all improve.

**Checkpoints/artifacts:** `models/grading/{grading_model.onnx, gradcam_fc_weights.npy,
metadata.json, training_history.json}`, `configs/calibration.json`.
**ONNX export:** validated, logits max abs diff `4.5e-7`, features max abs
diff `1.5e-5` vs PyTorch.

Full detail: `docs/model_cards/grading.md`.

## 6. Vessel segmentation

- U-Net (7.77M params), sigmoid output. AdamW lr=1e-3, batch 4, seed 42.
- 150 epochs configured, early-stopped at 140 (patience=25), best at 115.
- **GPU time: 5.6 minutes.**
- **Dice: 0.807. Thin-vessel sensitivity: 0.742** (4-image held-out val).
- ONNX parity: max abs diff `1e-6`.
- `models/vessel_seg/{vessel_model.onnx, metadata.json, training_history.json}`.
- Full detail incl. a real bug found and fixed (DRIVE `.tif` files crash
  Pillow natively on this machine — worked around with `cv2.imread`):
  `docs/model_cards/vessel_seg.md`.

## 7. Lesion segmentation (HE/EX/SE)

- U-Net (7.77M params), 3-channel sigmoid (multi-label). AdamW lr=1e-3,
  batch 4, seed 42. 150 epochs, best at 137. **GPU time: 75.1 minutes.**
- **Dice — HE: 0.363, EX: 0.598, SE: 0.248** (IDRiD's 27-image test split).
- ONNX parity: max abs diff `1e-6`.
- `models/lesion_seg/{lesion_model.onnx, metadata.json, training_history.json}`.
- Full detail: `docs/model_cards/lesion_seg.md`.

## 8. Microaneurysm hybrid detector

- Stage A: classical top-hat (reused directly from `pipeline.structure`, not
  reimplemented). Stage B: small CNN FP-reducer (patch accuracy 88.6% on
  held-out patches). AdamW lr=1e-3, 30 epochs, best at 13. **Training time: 0.2 min**
  (candidate generation across 81 images dominates wall time, not GPU training).
- **Lesion-level FROC (27-image IDRiD test set):** sensitivity **0.334 at 8
  FP/image** (full curve in the model card).
- **Honestly below the ~0.5 literature reference** for classical+CNN MA
  detectors on IDRiD — root-caused to this pipeline's 512×512 canonical
  resolution (~8.4x downsampling from IDRiD's native 4288×2848), which
  likely destroys much of the few-pixel-wide MA signal before the top-hat
  filter sees it. Not adjusted or hidden — see gap analysis in
  `docs/model_cards/ma_detector.md`.
- ONNX parity: max abs diff `0.0`.
- `models/ma_detector/{ma_fp_reducer.onnx, metadata.json, training_history.json}`.

## 9. Total GPU training time (this session)

27.3 + 5.6 + 75.1 + 0.2 ≈ **108 minutes** of GPU training across all four
models, plus dataset audit/split/patch-generation overhead.

## 10. Artifact validation performed (every model)

For each of the 4 trained models: fresh-Python-process contract load
(`pipeline.contract.load_contract` + `resolve_model_path`) → real demo image
→ the actual `pipeline/*.py` inference function → finite/shape/value checks
→ ONNX-vs-PyTorch parity check. All passed. The full `pipeline.report.run_full_pipeline()`
was then run end-to-end on both demo images (good passes all 4 phases with
zero errors; reject halts correctly at Phase 1), and via the live Flask app
(`GET /api/status` → `all_ready: true`, zero "unavailable" placeholders).

**Test suite: `python -m pytest tests -q` → 144 passed, 0 skipped, 0 failed**
(up from 122 passed / 22 skipped at the start of this session — every
previously-skipped integration test now exercises a real artifact).

## 11. Known limitations / unavailable components

1. **Decision fusion is still fallback-only** (`models/decision_fusion/`
   does not exist) — real MA/HE/EX evidence now exists to fit it, but that
   fit was not performed this session (explicitly out of scope per the
   directive: "Implement this only when the required evidence models
   actually exist... never create fake lesion features merely to make
   fusion run"). `referable_decision` currently reduces to the quality-tier
   grade-probability threshold, honestly reported as `fitted: false` in the UI.
2. **No sealed/external evaluation yet.** Messidor-2 and IDRiD's
   grading-test (103 images) remain untouched. The 89.4%/89.0% referable
   sensitivity/specificity above is an **internal validation number**, not
   the PS claim — that requires opening the sealed set exactly once after
   everything is frozen (MLR-003).
3. **MA detector underperforms the literature reference** — see Section 8.
   Highest-priority next step if this model is revisited: native-resolution,
   patch-tiled candidate extraction (blueprint K.6), not further CNN tuning.
4. **Uncertainty ensemble (Stage 10) not built** — single model per stage,
   reported as a limitation, never faked as an ensemble.
5. **Neovascularization module: not built, not claimed.** FGADR (its only
   viable data source) is out of scope for this training run.
6. **DDR unused** everywhere — intentional, per instruction.
7. A real, non-obvious bug was found and fixed during this work: DRIVE's
   `.tif` images crash Pillow's `convert('RGB')` **natively** (silent
   process death, no Python exception) on this machine's Pillow/libtiff
   build. Worked around with `cv2.imread` in the training scripts only —
   `pipeline/preprocessing.py`'s shared `load_image()` was not modified
   (out of scope; the live app only accepts jpg/png uploads, so this does
   not affect the demo).

## 12. Files changed/added this session (for review)

- `training/`: `prepare_grading_splits.py`, `preprocessing_cache.py`,
  `audit_datasets.py`, `metrics.py`, `train_grading.py` (rewritten),
  `train_vessel.py`, `train_lesion.py`, `train_ma_detector.py`.
- `models/{grading,vessel_seg,lesion_seg,ma_detector}/`: real artifacts +
  `metadata.json` + `training_history.json` for all four.
- `configs/calibration.json`: real fitted values (T=2.80).
- `docs/model_cards/`: `grading.md`, `vessel_seg.md`, `lesion_seg.md`,
  `ma_detector.md` (all rewritten with real measured numbers).
- `docs/dataset_cards/`: `audit_summary.md`, `audit_report.json`.
- `docs/env_snapshots/`: before/after pip freeze snapshots.
- `tests/test_calibration.py`, `tests/test_quality.py`: fixed two stale
  test assumptions (hardcoded "must always be unfitted" / "must always be
  `.onnx`") that were invalidated by real, intended training outcomes — not
  regressions, and not silenced by skipping.
- `docs/TASKS.md`, `docs/HANDOFF.md`: updated to match actual repo state.

**Explicitly not done, per the directive's stop condition:** no website/UI
redesign, no new architecture beyond what's listed above. Stopping here per
Section 26.
