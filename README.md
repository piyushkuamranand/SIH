# NETRA-DR

Explainable AI diabetic retinopathy screening prototype for **SIH26038**
(MathWorks). Processes fundus retinal photographs through a four-phase
pipeline: quality gate → retinal structure analysis → ICDR 0–4 grading with
calibrated confidence → model-attention explainability and referral decision.

**Screening/triage research prototype — not clinically validated, not a
regulated medical device.** For architecture, contracts, and engineering
conventions see [docs/HANDOFF.md](docs/HANDOFF.md).

## Quick Start

```bash
pip install -r requirements.txt
python app/app.py
```

Then open **http://127.0.0.1:5000** in a browser. No cloud API, database,
Docker, or continuously-running MATLAB is required — the app loads frozen
ONNX artifacts from `models/` and runs entirely offline on CPU
(`onnxruntime`, `CPUExecutionProvider`).

Windows/Unix one-command launchers (`run_demo.bat` / `bash run_demo.sh`) do
the same `pip install` + `python app/app.py` steps.

## Model status (as of the latest training run)

All 5 model directories under `models/` currently hold real, trained,
contract-conformant artifacts — `GET /api/status` reports `all_ready: true`
and no pipeline stage shows "unavailable". If you replace or remove a
`models/<stage>/` artifact, that stage will honestly show "unavailable" in
the UI rather than crash or fabricate a result — this is the contract
working as intended (see `pipeline/contract.py`).

| Stage | Model | Trained on | Model card |
|---|---|---|---|
| Quality (Phase 1) | Rule-based baseline (no training needed) | — | `docs/model_cards/` (see `pipeline/quality.py` docstring) |
| Vessels (Phase 2) | Compact U-Net | DRIVE | `docs/model_cards/vessel_seg.md` |
| Lesions HE/EX/SE (Phase 2) | Compact U-Net, 3-channel | IDRiD segmentation | `docs/model_cards/lesion_seg.md` |
| Microaneurysms (Phase 2) | Classical top-hat + CNN FP-reducer | IDRiD segmentation | `docs/model_cards/ma_detector.md` |
| Grading (Phase 3) | ResNet-50, ImageNet-pretrained | APTOS 2019 + IDRiD grading-train | `docs/model_cards/grading.md` |
| Explainability (Phase 4) | Exact class activation map (Zhou et al.) on the grading model | — | `pipeline/explain.py` |

**Not built / out of scope, honestly disclosed rather than hidden:**
neovascularization (FGADR-only per spec, FGADR not downloaded), a learned
decision-fusion model (currently a documented quality-tier fallback — see
`pipeline/decision.py`), and a deterministic uncertainty ensemble (single
model per stage — never presented as an ensemble).

## Datasets

| Dataset | Location | Used for | Status |
|---|---|---|---|
| APTOS 2019 | `data/raw/aptos2019/` | Grading | ✅ downloaded |
| IDRiD | `data/raw/idrid/` | Grading, lesions, MA | ✅ downloaded |
| DRIVE | `data/raw/drive/` | Vessels | ✅ downloaded |
| DDR | `data/raw/ddr/` | — | ❌ not downloaded (excluded per project decision) |
| Messidor-2 / IDRiD grading-test | — | Sealed external evaluation | **Never opened** — reserved until the full system is frozen |

`data/raw/` and `data/processed/` are gitignored (large files); only the
folder skeleton and small manifests (`data/splits/*.csv`) are tracked. Full
dataset audit: `docs/dataset_cards/audit_summary.md`.

## Training a model

Training never happens inside the website process — it lives entirely under
`training/` (PyTorch/GPU) or `matlab/` (MATLAB), per the train/serve
separation in `docs/HANDOFF.md`.

```bash
pip install -r training/requirements-train.txt   # separate from requirements.txt

# Grading (ResNet-50, ImageNet-pretrained, GPU)
python training/prepare_grading_splits.py --val-fraction 0.15
python training/train_grading.py --epochs 25 --backbone resnet50

# Vessel segmentation (DRIVE)
python training/train_vessel.py --epochs 150

# Lesion segmentation HE/EX/SE (IDRiD)
python training/train_lesion.py --epochs 150

# MA hybrid detector (IDRiD)
python training/train_ma_detector.py --epochs 30

# Dataset audit (re-run any time)
python training/audit_datasets.py
```

Each script writes its own `models/<stage>/{*.onnx, metadata.json,
training_history.json}` and (grading only) fits `configs/calibration.json`.
**Requires an NVIDIA GPU with CUDA** (`torch.cuda.is_available()` — these
scripts refuse to silently fall back to CPU or a smaller architecture; see
each model card for exact measured metrics and known limitations).

## Model artifact locations

```
models/
├── quality/       iqa_thresholds.json, metadata.json          (rule-based, no training)
├── vessel_seg/    vessel_model.onnx, metadata.json
├── lesion_seg/    lesion_model.onnx, metadata.json
├── ma_detector/   ma_fp_reducer.onnx, metadata.json
└── grading/       grading_model.onnx, gradcam_fc_weights.npy, metadata.json
configs/calibration.json                                        (fitted temperature scaling)
```

All model artifacts (`.onnx`, `.pt`, `.npy`, `metadata.json`,
`training_history.json`) are tracked in Git — only raw/cached datasets under
`data/raw/` and `data/processed/` are excluded (see `.gitignore`). Largest
tracked artifact is ~90MB (`models/grading/grading_model.onnx` and its
`_best_checkpoint.pt`), safely under GitHub's 100MB hard limit.

## Demo cases

`data/demo/` — see `docs/demo_set.md` for full provenance and selection
method (all real files, selected by ground-truth label before running the
system, never edited to fabricate severity):

- `good_sample.jpg` — passes quality gate, Grade 0
- `reject_sample.jpg` — synthetically degraded for a **quality** demo only (disclosed)
- `aptos_grade0_0d0b8fc9ab5c.png` — real, labelled Grade 0 (correctly predicted)
- `aptos_grade2_025a169a0bb0.png` — real, labelled Grade 2 (**misclassified as 0** — kept deliberately, an honest documented model limitation)
- `aptos_grade4_875a2fc5fe23.png` — real, labelled Grade 4, PDR (correctly predicted, REFER)

## Project structure

```
netra-dr/
├── pipeline/            Core pipeline (Phase 1–4 + report orchestrator + startup check)
├── app/                 Flask web app (app.py + templates/ + static/)
├── training/             PyTorch/GPU training scripts (never imported by app/ or pipeline/)
├── matlab/                MATLAB scripts + Simulink workflow model (independent track)
├── models/                Model directories: ONNX artifacts + metadata.json contracts
├── configs/               preprocessing.json, calibration.json, decision_rule.json
├── data/raw/               Downloaded datasets (gitignored)
├── data/splits/            Train/val split manifests (tracked, small)
├── data/demo/              Demo fundus images for the live presentation
├── tests/                  pytest suite (144 tests)
├── docs/
│   ├── HANDOFF.md            primary entry point for contributors
│   ├── TASKS.md               live task tracker
│   ├── model_cards/            per-model architecture + measured metrics + limitations
│   ├── dataset_cards/           dataset audit
│   ├── checkpoints/              phase checkpoints + ml_training_report.md + final_demo.md
│   └── env_snapshots/             before/after pip freeze (CUDA environment change)
├── run_demo.bat / run_demo.sh   one-command launchers
```

## Known limitations (see model cards for full detail)

1. Metrics reported anywhere in this repo are **internal validation
   numbers**, never the sealed/external test claim required by the problem
   statement — Messidor-2 and IDRiD's grading-test split (103 images) remain
   untouched, reserved for a one-time evaluation after everything is frozen.
2. Decision fusion is a documented fallback (quality-tier + grade
   probability threshold), not a fitted logistic-regression model — real
   MA/HE/EX evidence now exists to fit one, but that fit has not been done.
3. MA detector's lesion-level FROC (0.334 at 8 FP/image) is below the
   published literature reference (~0.5), root-caused to this pipeline's
   512×512 canonical resolution vs. IDRiD's native ~4288×2848 — see
   `docs/model_cards/ma_detector.md`.
4. No uncertainty ensemble, no neovascularization module, no DDR data —
   all disclosed above, none fabricated or silently mocked.
5. The rule-based IQA baseline rejects a meaningful fraction of real Kaggle
   APTOS images (pre-compression lowers the measured focus signal) — see
   `docs/demo_set.md` for a worked example.

## Architecture overview

```
Raw image
  → Phase 1: Quality Gate (rule-based IQA) — REJECT halts here, never fabricated downstream
  → Phase 2: Retinal Structure Analysis (vessels, HE/EX/SE, MA) — separate evidence, never merged
  → Phase 3: DR Grading (ResNet-50) → temperature calibration → referral decision (grade-alone vs. fused, both reported)
  → Phase 4: Explainability (exact class activation map — "model attention", never "clinical proof")
  → Single results page + printable report + prototype-only doctor-review actions
```

Simulink district-workflow simulation (`matlab/sweep_ratio.m`,
`docs/checkpoints/simulink_results.md`) is a **separate, independent track**
— never wired into per-image inference; normal screening never depends on
MATLAB being open.

Full training methodology and measured results:
`docs/checkpoints/ml_training_report.md`. Final demo verification:
`docs/checkpoints/final_demo.md`.
