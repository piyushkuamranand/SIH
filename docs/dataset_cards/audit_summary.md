# Dataset Audit Summary

Machine-generated facts in `docs/dataset_cards/audit_report.json` (via
`training/audit_datasets.py`); this file is the human-readable summary.
Re-run the script and re-read the JSON if these numbers look stale.

## APTOS 2019
- 3,662 labelled images, 0 corrupt/missing. No patient/exam id in the Kaggle
  CSV — split in `data/splits/aptos2019_{train,val}.csv` is a **near-duplicate-
  aware, class-stratified image-level split** (not patient-level; documented
  limitation, see `data/splits/aptos2019_dedup_report.json`).
- Train 3,348 / Val 314. Class distribution imbalanced (grade 0 ≈ 51%, grade 3
  ≈ 5% of train) — handled with class-weighted loss in training.

## IDRiD
- **Grading:** 413 train / 103 test images, both CSVs and all image files
  present, 0 missing. **The 103-image test split is the project's SEALED
  external test set** (Final Model Stack Step 1) — must not be opened for
  training, validation, or threshold tuning until the grading model is frozen.
- **Segmentation:** 54 train / 27 test images. Masks: MA 54/27, Haemorrhage
  53/27, Hard Exudate 54/27, Soft Exudate 26/14, Optic Disc 54/27 (Soft
  Exudate has fewer positive cases — expected, matches the published IDRiD
  documentation). Image↔mask dimension alignment spot-checked: **aligned**
  (4288×2848 native resolution, no resampling on disk).
- IDRiD segmentation images are ~4288×2848 — an order of magnitude larger
  than APTOS. Lesion/vessel training must be patch-based at or near native
  resolution (blueprint K.6) rather than a single global resize, or
  microaneurysm-scale signal is lost.

## DRIVE
- 20 train images + vessel masks (`1st_manual`) + FOV masks; 20 test images +
  FOV masks only (no public vessel ground truth in this download — matches
  the standard DRIVE distribution). All at 565×584, image↔mask alignment
  confirmed for all 20 training pairs.
- Vessel model validation therefore uses a held-out split of the 20 training
  images (e.g. patch-level or image-level k-fold), not the "test" folder.

## external/ (EyeQ, FGR-NET)
- Both directories exist but contain **0 files** — no checkpoint, no code.
  `models/quality/metadata.json`'s old reference to an EyeQ `.pth` checkpoint
  pointed at nothing real (this is what caused Phase 1 to be permanently
  broken until the rule-based IQA baseline replaced it). There is nothing to
  integrate from `external/` — confirmed, not assumed.

## DDR
- Not downloaded. Intentionally excluded from this training run per explicit
  instruction. `models/*/metadata.json` and code do not require it.
