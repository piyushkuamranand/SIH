# Model Card — Lesion Segmentation (HE / EX / SE)

Generated from `models/lesion_seg/metadata.json` and `training_history.json`
after `training/train_lesion.py`.

## Architecture
- Same compact U-Net family as the vessel model, 3-channel sigmoid output
  (multi-label — HE/EX/SE are independent per-pixel probabilities, never
  merged into one map). **7.77M params.**
- Channel order fixed as `["HE", "EX", "SE"]`, written into
  `metadata.json["mask_labels"]` — `pipeline/structure.py` reads this order
  from the contract, never assumes it.

## Data
- **IDRiD Segmentation (folder A)**, the dataset's own published train/test
  split: **54 train / 27 val**. This is a *different* IDRiD split from the
  grading train/test split — **the 27-image segmentation test set here is
  NOT the project's sealed grading-test set** (that is IDRiD folder B's
  103-image test split, untouched by this or any other training run so far).
- Mask availability: HE 53/54 train, 27/27 val; EX 54/54 train, 27/27 val;
  **SE only 26/54 train, 14/27 val** (soft exudates are genuinely rare in
  IDRiD — matches the published dataset documentation). Images without a
  mask file for a given class are treated as an all-zero mask for that
  class, never dropped from training.
- Preprocessing: FOV crop → resize(512×512) → CLAHE, image and all 3 masks
  cropped/resized jointly to stay pixel-aligned (same canonical space as the
  rest of the pipeline).
- **Deviation from blueprint K.7** (native-resolution preference): trained at
  512×512 vs. IDRiD's native 4288×2848 (~8x downsampling) — a time-budget
  trade-off, documented not hidden. This materially affects fine lesion
  boundaries; microaneurysms specifically are handled by a separate model
  (`training/train_ma_detector.py`), not this one.

## Training
- Loss: BCE + per-channel Dice (averaged across the 3 independent channels).
- AdamW, lr=1e-3, cosine schedule, batch size 4, seed 42.
- Augmentation: flips + 90°-multiple rotations (image and all 3 masks
  together).
- Early stopping: patience=25 on mean Dice; ran the full 150 epochs
  configured (best at epoch 137). **Total training time: 75.1 minutes.**

## Results — IDRiD's own 27-image test split (Dice)

| Class | Dice |
|---|---|
| HE (Haemorrhages) | 0.363 |
| EX (Hard Exudates) | **0.598** |
| SE (Soft Exudates) | 0.248 |

EX (larger, brighter lesions) segments best, consistent with the literature.
HE and SE are harder — smaller/subtler lesions, and 512px downsampling loses
detail that would help at native resolution. SE Dice is measured on a
smaller effective sample (only 14/27 val images actually contain soft
exudates). Dice is computed only over images where ground truth or
prediction is non-empty for that class (both-empty images are excluded, not
counted as a perfect score, to avoid inflating SE's low-prevalence Dice).

## ONNX export
Single input, single 3-channel sigmoid-probability output (`lesion_probs`).
Parity vs PyTorch: max abs diff `1e-6`. Fresh-process validation (contract
load → real image → `pipeline.preprocessing.preprocess()` →
`pipeline.structure.run_lesion_segmentation()`) confirmed working: three
separate binary masks, `he_presence`/`ex_area` scalar features computed
correctly, no lesion subtypes invented.

## Known limitations
1. HE and SE Dice are modest (0.36, 0.25) — reflects both the 512px
   downsampling trade-off and the very small training set (54 images, 26 with
   SE masks). A future native-resolution patch-based retrain would likely
   improve both meaningfully.
2. No cross-check against DDR's lesion masks (DDR not downloaded).
3. `he_presence` and `ex_area` (consumed by Phase 3 decision fusion) are only
   as reliable as the underlying HE/EX Dice above — flagged for whoever fits
   the decision-fusion logistic regression next.

## Artifact paths
- `models/lesion_seg/lesion_model.onnx`
- `models/lesion_seg/metadata.json`
- `models/lesion_seg/training_history.json`
