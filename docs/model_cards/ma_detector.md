# Model Card — Microaneurysm (MA) Hybrid Detector

Generated from `models/ma_detector/metadata.json` and `training_history.json`
after `training/train_ma_detector.py`.

## Architecture (Final Model Stack Stage 4 — two-stage hybrid)
- **Stage A (classical):** morphological top-hat on the green channel —
  `pipeline.structure._extract_candidates_tophat()`, **imported directly, not
  reimplemented**, so candidate generation is byte-identical between training
  and inference. Parameters (`tophat_disk_radius=6`, `tophat_threshold_factor=2.0`)
  are written into `metadata.json` and read by the contract at inference —
  never hardcoded twice.
- **Stage B (CNN false-positive reducer):** small 3-conv-layer CNN, 32×32
  patches, softmax baked into the exported ONNX graph (matches contract
  `output_format: "softmax"`). Patch extraction also reuses
  `pipeline.structure._prepare_patch_input()` directly.

## Data & labelling
- IDRiD Segmentation MA masks: **54 train images** (1,263 positive / capped
  negative candidate patches after running the real classical extractor on
  each) for training the FP-reducer; **27 test images** (IDRiD's own
  published segmentation test split, **not** the sealed grading-test split)
  for lesion-level evaluation. 54+27=81 total MA-masked images, matching the
  Final Model Stack's stated "IDRiD (81 MA-masked images)".
- A candidate is labelled TRUE MA if it falls within the ground-truth mask
  dilated by 3px (tolerance for the classical extractor's centroid not
  landing exactly on the annotated pixel), else FALSE POSITIVE.

## Training
- AdamW, lr=1e-3, class-weighted NLL loss (patches are ~72%
  negative/28% positive after the per-image negative cap of 60).
- Best epoch 13/30 by validation patch accuracy: **88.6%** patch-level
  train/val accuracy (held-out 15% of patches, not held-out images — this
  is a patch classification sanity check, not the headline metric).
- Training time: **0.2 minutes** (patch classifier is tiny; most of the
  script's wall time — several minutes — is spent on classical candidate
  extraction and patch preparation across 81 images, not the CNN training).

## Results — lesion-level FROC on 27 held-out IDRiD test images (headline metric)

| FP/image (target) | Sensitivity | Actual FP/image | Threshold |
|---|---|---|---|
| 1/8 | 0.065 | 0.11 | 0.998 |
| 1/4 | 0.097 | 0.22 | 0.997 |
| 1/2 | 0.137 | 0.48 | 0.995 |
| 1 | 0.167 | 1.00 | 0.992 |
| 2 | 0.225 | 2.00 | 0.982 |
| 4 | 0.272 | 4.00 | 0.967 |
| **8** | **0.334** | 8.00 | 0.921 |

## Honest gap analysis vs. the literature

`docs/NETRA-DR Model-Selection Evidence Review...pdf` cites classical+CNN
approaches on IDRiD reaching roughly **FROC ≈ 0.5 at similar FP/image rates**
(Porwal et al. 2020 IDRiD challenge, Du et al. classical baseline). This
model measured **0.334 at 8 FP/image** — meaningfully below that reference
point. Per project ML rules, this is reported as measured, not adjusted to
look better. The most likely cause, in order of suspected impact:

1. **Resolution.** This pipeline resizes every image to 512×512 (the shared
   canonical space used across all NETRA-DR models) before candidate
   extraction. IDRiD's native resolution is 4288×2848 — an **~8.4x
   downsampling**. Microaneurysms are a few pixels wide even at native
   resolution; after this downsampling many are sub-pixel or destroyed
   entirely by the CLAHE/resize chain before the top-hat filter ever sees
   them. Blueprint K.6 explicitly calls for "native or near-native
   resolution with tiling" for MA detection specifically — this run does not
   do that, and this is very likely the dominant cause of the gap. **No
   "sub-pixel" detection claim is made anywhere in this project** — this
   result is direct evidence for why (blueprint OQ-04 concern, confirmed).
2. Small training set for the FP-reducer (1,263 positive patches from 54
   images) — the reducer may be under-trained relative to more MA-typical
   texture variation than can be represented at this scale.
3. The GT-matching dilation radius (3px, at 512px scale) is itself a design
   choice that affects the measured FROC curve — a different fixed
   connected-component protocol would give different absolute numbers,
   though the qualitative gap vs. literature would likely persist given (1).

## ONNX export
Single input (32×32×3 patch), single 2-class softmax-probability output.
Parity vs PyTorch: max abs diff `0.0` (below float32 display precision).
Fresh-process validation (contract load → real image →
`pipeline.preprocessing.preprocess()` → `pipeline.structure.run_ma_detection()`)
confirmed working end-to-end (145 MAs detected on the demo image, plausible
non-zero, non-absurd count).

## Known limitations
1. **Resolution mismatch is the primary known limitation** — see gap analysis
   above. A native-resolution, patch-tiled retrain (matching blueprint K.6)
   is the highest-priority next step for this model specifically, ahead of
   any other tuning.
2. No cross-check against e-ophtha-MA or other MA-labelled datasets (not
   downloaded).
3. FROC measured against a specific fixed protocol (this script's connected-
   component + dilation choices) — not directly comparable number-for-number
   to other papers' protocols, only qualitatively.

## Artifact paths
- `models/ma_detector/ma_fp_reducer.onnx`
- `models/ma_detector/metadata.json`
- `models/ma_detector/training_history.json`
