## NETRA-DR Demo Set — Image Selection Documentation

Rewritten after real models were trained (TASK-023). Every result on this
page was measured by actually running `pipeline.report.run_full_pipeline()`
on the listed file — nothing here is predicted or aspirational.

### Selection method (anti-cherry-picking, per the Development Blueprint)

The three graded cases below were selected **by ground-truth ICDR label**,
from `data/splits/grading_val.csv` (the model's own held-out validation
split), **before** looking at what the trained model would predict:

1. Scan the validation split in file order for the first APTOS image at each
   target grade (0, 2, 4) whose ground-truth label matches.
2. Filter only by whether the **quality gate** (an independent, non-grading
   criterion) passes GOOD/BORDERLINE — several first-choice candidates at
   grade 0 and grade 2 were rejected by the quality gate and skipped for that
   reason alone, not because of their grade or the model's prediction on them.
3. Whatever the grading model then outputs is reported as-is below, **including
   the one case where it is wrong** (grade 2 → predicted 0).

No image was swapped out because its prediction looked bad.

---

### Current demo set (5 images)

| File | Source | Ground truth | Quality (measured) | Predicted grade | Referral | Notes |
|---|---|---|---|---|---|---|
| `good_sample.jpg` | Real fundus photo, not from a labelled split (no ICDR ground truth available) | — | **GOOD** | 0 | NO REFER | Baseline "all clear" path |
| `reject_sample.jpg` | `good_sample.jpg`, synthetically degraded (×0.08 brightness, heavy Gaussian blur, JPEG-recompressed) — **quality-degradation demo only, no disease severity was fabricated** | — | **REJECT** | N/A (halts at Phase 1) | N/A | Demonstrates the safety gate |
| `aptos_grade0_0d0b8fc9ab5c.png` | APTOS 2019 validation split, real label | **Grade 0** | BORDERLINE | **0** ✅ | NO REFER | Correct |
| `aptos_grade2_025a169a0bb0.png` | APTOS 2019 validation split, real label | **Grade 2** | BORDERLINE | **0** ❌ | NO REFER | **Misclassified** — an honest, real model error. Matches the model card's documented weak point (Grade 2 sensitivity 77.1%, adjacent-grade confusion). Kept in the demo set deliberately: this is what "do not hide technical limitations" means in practice. |
| `aptos_grade4_875a2fc5fe23.png` | APTOS 2019 validation split, real label | **Grade 4** | BORDERLINE | **4** ✅ | **REFER** | Correct — good case for showing model attention on a clearly pathological image |

Measured end-to-end pipeline time per case: 3.2–8.6 seconds on this machine
(CPU onnxruntime inference; MA detection's per-candidate ONNX calls dominate
— see `docs/checkpoints/ml_training_report.md` Section 9). This is inference
latency, not the PS's 30-second *ophthalmologist review* budget — the UI
displays both concepts separately.

**Why so many real APTOS validation images fail the quality gate:** the
rule-based IQA baseline (`pipeline/quality.py`, `docs/model_cards/` — no
learned model, no dataset needed) measures focus via Laplacian variance in a
canonical 512×512 space. Kaggle's APTOS images are pre-compressed/resized by
the competition, which measurably lowers this signal relative to a genuinely
sharp clinical capture. This is a real, measured behavior of the current
baseline, not a demo bug — see `docs/model_cards/quality.md` if present, or
`pipeline/quality.py`'s module docstring, for the honest limitation.

---

### Presenter narration suggestions

- **Good sample:** "Quality gate passes immediately, full pipeline runs, no
  DR detected, confidence is high after calibration."
- **Reject sample:** "Severely degraded image — the gate stops the pipeline
  before any downstream stage can produce a misleading result. This is a
  deliberate safety property, not a missing feature."
- **Grade 0 (real, labelled):** "A real APTOS validation image with a known
  ground-truth label of no DR — the model agrees."
- **Grade 2 (real, labelled):** "This one is instructive: ground truth is
  Moderate NPDR, and the model predicts No DR — a real miss. We show this
  deliberately. It's the exact grade-1/2 boundary confusion documented in the
  model card, and it's why the referral decision layer and human review exist
  — a screening aid, not a diagnostic replacement."
- **Grade 4 (real, labelled):** "Proliferative DR, correctly identified and
  correctly routed to REFER. Model attention concentrates on the pathological
  regions — reported as an attention map, never as clinical proof."

### Provenance / integrity rules followed

- No sealed test-set image (`IDRiD` grading-test, Messidor-2) appears here.
- No demo image's disease severity was ever edited or fabricated — only the
  REJECT sample's *quality* was synthetically degraded, and that is disclosed
  above, not hidden.
- Selection order is reproducible from `data/splits/grading_val.csv` and the
  procedure in "Selection method" above.
