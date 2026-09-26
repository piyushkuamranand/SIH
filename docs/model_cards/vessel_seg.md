# Model Card — Vessel Segmentation

Generated from `models/vessel_seg/metadata.json` and `training_history.json`
after `training/train_vessel.py`.

## Architecture
- Compact U-Net, 4 encoder/decoder levels, base width 32, **7.77M params**
  (small by design — 20 total DRIVE images cannot support a large network).
- Sigmoid baked into the model's forward pass, so the ONNX output is already
  a probability map, matching `pipeline/structure.py`'s
  `_threshold_to_binary_mask()` contract (threshold=0.5 from metadata).
- Trained on GPU (RTX 3050 6GB, CUDA 12.6).

## Data
- **DRIVE**: 20 training images with 1st-observer manual vessel masks.
  Split **16 train / 4 val**, image-level — this **is** a patient-level split
  for DRIVE specifically (one eye per subject, unlike APTOS/IDRiD grading).
- DRIVE's "test" folder (20 images) has **no publicly distributed vessel
  ground truth** in this download (only FOV masks) — confirmed by
  `training/audit_datasets.py`, so it cannot be used for validation.
- Images run through the same FOV-crop → resize(512×512) → CLAHE pipeline as
  `pipeline.preprocessing.preprocess()` (image and mask cropped/resized jointly
  to keep them pixel-aligned).
- No cross-check against STARE/CHASE_DB1 (not downloaded — deviation from the
  Final Model Stack's "cross-check: STARE, CHASE_DB1", documented not hidden).

## Known engineering issue found and fixed
Loading DRIVE's `.tif` files via `pipeline.preprocessing.load_image()`
(Pillow's `Image.open().convert('RGB')`) **crashes the Python process natively**
on this machine's Pillow/libtiff build — no exception, no traceback, silent
process death. Root-caused via step-by-step isolation (see training/train_vessel.py's
comment). Worked around by loading DRIVE images with `cv2.imread()` instead,
inside `training/train_vessel.py` only. **This does not affect the live app**
(`app/app.py` only accepts `.jpg/.jpeg/.png` uploads), but is worth knowing if
TIFF upload support is ever added — `pipeline/preprocessing.py`'s `load_image()`
was not modified (out of scope for this training task; flagging for awareness).

## Training
- Loss: BCE + Dice (foreground/background pixel imbalance).
- AdamW, lr=1e-3, cosine schedule, batch size 4, seed 42.
- Heavy augmentation given only 16 training images: flips + 90°-multiple
  rotations.
- Early stopping: patience=25 on val Dice. Stopped at epoch 140 (best at 115).
  **Total training time: 5.6 minutes.**

## Results — 4-image held-out validation (DRIVE training-set subset)
| Metric | Value |
|---|---|
| Dice | **0.807** |
| Thin-vessel sensitivity | **0.742** |

Thin-vessel sensitivity is measured separately from Dice (erosion-based
thin-pixel proxy, not a full skeletonization) because average Dice hides
thin-vessel failure (blueprint K.5) — reported here rather than only Dice.

## ONNX export
Single input, single sigmoid-probability output (`vessel_prob`). Parity vs
PyTorch: max abs diff `1e-6`. Fresh-process validation (contract load → real
image → `pipeline.preprocessing.preprocess()` → `pipeline.structure.run_vessel_segmentation()`)
confirmed working, binary mask values strictly `{0, 255}`.

## Known limitations
1. Validated on only 4 held-out images — a very small validation set;
   metrics have wide uncertainty.
2. No cross-dataset validation (STARE/CHASE_DB1 not downloaded).
3. Global resize to 512×512 rather than a full patch-based native-resolution
   pipeline (DRIVE's native 565×584 is close to 512×512, so this is a modest
   deviation, but it is a deviation from blueprint K.5's stated preference —
   documented, not hidden, and driven by the time budget for this run).

## Artifact paths
- `models/vessel_seg/vessel_model.onnx`
- `models/vessel_seg/metadata.json`
- `models/vessel_seg/training_history.json`
