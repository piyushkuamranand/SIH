# NETRA-DR — Pipeline Architecture & Checkpoint Map

Explainable AI Diabetic Retinopathy Screening — SIH-26038 (MathWorks)

---

## Quick Start

```bat
# Windows
pip install -r requirements.txt
python app/app.py
```

The pipeline entry point for programmatic use:

```python
from pipeline.orchestrator import run_netra_pipeline, NetraConfig

config = NetraConfig(GRADER_BACKEND="resnet50")  # or "efficientnet_b0"
result = run_netra_pipeline(preprocessed_image, quality_tier="Good", config=config)
```

Stages 1 (IQA) and 2 (preprocessing) hand you `preprocessed_image` and `quality_tier`
via `pipeline/quality.py` and `pipeline/preprocessing.py` (already built — do not modify).

---

## Stage → Repo / Checkpoint Map

| Stage | Description | Repo / Checkpoint Path | Pretrained On |
|-------|-------------|------------------------|---------------|
| **S1** | Vessel segmentation | `./models/vessel_seg/` ← ONNX exported from `./models/FR-UNet` | DRIVE, STARE, CHASE_DB1 |
| **S2a** | Lesion segmentation (HE/EX/SE) | `./models/lesion_seg/` ← ONNX from `./models/fundus-lesions-toolkit` | IDRiD, FGADR, DDR, MESSIDOR |
| **S2b** | Microaneurysm detection | `./models/ma_detector/` (two-stage: top-hat + CNN FP-reducer) | IDRiD, FGADR |
| **S3** | Neovascularisation | *Stub — no model available* | — |
| **S4** | DR grading (primary) | `./models/grading/` ← ONNX from HF `sakshamkr1/ResNet50-APTOS-DR` | APTOS-2019 (ICDR 0–4) |
| **S4** | DR grading (backup) | `./models/grading_backup/` ← ONNX from HF `adarshcod30/drdetect-dr-screening` | EfficientNet-B0 |
| **S5** | Decision fusion | `./models/decision_fusion/metadata.json` (scikit-learn LR; trained offline on calibration split) | Calibration split only |
| **S6** | Temperature calibration | `./models/temperature_scaling/` + `configs/calibration.json` | Validation fold |
| **S7** | Ensemble | 3–5 ONNX checkpoints listed in `NetraConfig.ensemble_checkpoint_paths` | Independently seeded runs |
| **S8** | Explainability | Grad-CAM via `onnxruntime`; HiResCAM via `pytorch-grad-cam` (needs `models/grading/model.pt`) | — |
| **S9** | Quality thresholds | Applied inside S5 (`configs/decision_rule.json`) | — |
| **S10** | Consistency flag | Derived from S8 IoU vs S2 lesion masks | — |

> **Backend toggle:** set `NetraConfig.GRADER_BACKEND = "efficientnet_b0"` to swap S4 to the EfficientNet-B0 backup grader.

---

## Directory Layout

```
NETRA-DR/
├── pipeline/
│   ├── orchestrator.py      ← NEW: full 10-stage orchestrator (this PR)
│   ├── report.py            ← existing 4-phase pipeline (Stages 1-4 simple wiring)
│   ├── quality.py           ← Stage 1 IQA (do not modify)
│   ├── preprocessing.py     ← Stage 2 preprocessing (do not modify)
│   ├── structure.py         ← vessel seg + lesion seg + MA detection
│   ├── grading.py           ← DR grading + temperature calibration
│   ├── decision.py          ← decision fusion (rule-based fallback)
│   ├── explain.py           ← Grad-CAM explainability
│   └── contract.py          ← model contract loader & validator
│
├── models/
│   ├── vessel_seg/          ← FR-UNet ONNX artifact + metadata.json
│   ├── lesion_seg/          ← fundus-lesions-toolkit ONNX + metadata.json
│   ├── ma_detector/         ← MA FP-reducer ONNX + metadata.json
│   ├── grading/             ← ResNet-50 ONNX + metadata.json  [+ model.pt for HiResCAM]
│   ├── grading_backup/      ← EfficientNet-B0 ONNX + metadata.json
│   ├── temperature_scaling/ ← calibration artifacts
│   └── decision_fusion/     ← LR metadata.json (populated by train_decision_fusion_model())
│
├── configs/
│   ├── calibration.json     ← temperature T (fitted on validation fold)
│   ├── decision_rule.json   ← Good/Borderline thresholds
│   └── preprocessing.json   ← preprocessing parameters
│
├── eval/                    ← (create) validation + sealed-test evaluation scripts
│   ├── validate.py          ← run on validation fold; writes calibration.json
│   └── test_performance.py  ← opened exactly once for Messidor-2 / IDRiD sealed split
│
├── app/                     ← Flask web app
├── tests/                   ← pytest suite
├── requirements.txt
└── README.md                ← this file
```

---

## Constraint Audit (enforced in `pipeline/orchestrator.py`)

| Constraint | Enforcement |
|-----------|-------------|
| Lesion features NOT fused into grading network | `s4_grading["lesion_fusion_in_grader"] = False` audit field |
| No RETFound/DINOv2 as production grader | `s4_grading["foundation_model_used"] = False` audit field |
| No hemorrhage subtypes (flame/dot-blot/deep) | HE output: presence + count + area_fraction + quadrant_counts only |
| NV stub distinct from ICDR Grade-4 | S3 carries explicit `icdr_grade4_equivalence_disclaimer` |
| MC-dropout not used | `s7_ensemble["mc_dropout_used"] = False` always |
| Sensitivity/specificity two-sided CI phrasing | `_format_performance_report()` enforces PRD wording |
| Gradable-only AND gradable+ungradable reported | `performance_report["gradable_and_ungradable_reported"]` |
| Sealed test sets never opened here | `pipeline_meta["sealed_test_touched"] = False`; sealed split opened only by `eval/test_performance.py` |
| Reject images never get automated clearance | Hard `ValueError` raised in `run_netra_pipeline()` |
| "model attention" ≠ "detected evidence" | S8 carries `label="model attention"`, S2 carries `evidence_label="detected evidence"` |

---

## Training the Decision Fusion Model (offline)

```python
from pipeline.orchestrator import train_decision_fusion_model
import numpy as np

# X: (n_samples, 5) — build from calibration split using _build_fusion_feature_vector
# y: (n_samples,)  — binary labels: 1 = referable (Grade >= 2), 0 = non-referable
# DO NOT pass Messidor-2 or the sealed IDRiD split here.

metadata = train_decision_fusion_model(
    X=X_calib,
    y=y_calib,
    output_dir="models/decision_fusion",
    quality_tier_threshold_good=0.50,
    quality_tier_threshold_borderline=0.35,
)
# Coefficients are logged at INFO level automatically.
# metadata.json is written to models/decision_fusion/ with fitted=True.
```

After training, `run_netra_pipeline()` automatically picks up the fitted model.

---

## Performance Reporting

After running `eval/validate.py` on the validation fold, populate `NetraConfig`:

```python
config = NetraConfig(
    validation_sensitivity_pct=92.5,
    validation_specificity_pct=87.3,
    validation_ci_lower=89.1,
    validation_ci_upper=95.4,
)
result = run_netra_pipeline(img, "Good", config)
print(result["performance_report"]["performance_report"])
# "At the operating point selected on validation, the system measured
#  92.5% sensitivity / 87.3% specificity on the sealed test set, with
#  95% CI [89.1%, 95.4%].  Gradable-only and gradable+ungradable numbers
#  are reported side-by-side in eval/test_performance.py."
```

> The system never claims it "achieves" the target as a bare fact — the two-sided
> phrasing is enforced in code, not just documentation.
