# NETRA-DR — Final Demo Verification

**Tested:** 2026-09-26, ~05:30–05:50 IST
**Machine:** Windows 11, Python 3.13.5, NVIDIA RTX 3050 Laptop 6GB (training only — the live app runs CPU-only, `onnxruntime` `CPUExecutionProvider`, no GPU dependency at inference)
**Environment:** torch 2.14.0+cu126 (training env only; not a runtime dependency of `app/`), onnxruntime 1.30.0, opencv-python 5.0.0, Flask 3.1.0

## Launch

```bash
cd D:\SIH-1
python app/app.py
```

**URL:** http://127.0.0.1:5000

Verified from a **stripped/fresh shell environment** (`env -i`, no inherited
`NETRA_*` vars, no stale process) — the server starts and serves correctly
with zero special setup beyond `pip install -r requirements.txt`.

## Models actually available (all real, none mocked)

| Stage | Artifact | Dataset trained on |
|---|---|---|
| Quality | `models/quality/iqa_thresholds.json` (rule-based) | none needed |
| Vessels | `models/vessel_seg/vessel_model.onnx` | DRIVE (16 train / 4 val) |
| Lesions HE/EX/SE | `models/lesion_seg/lesion_model.onnx` | IDRiD segmentation (54 train / 27 val) |
| MA detector | `models/ma_detector/ma_fp_reducer.onnx` | IDRiD segmentation (54 train / 27 val) |
| Grading | `models/grading/grading_model.onnx` | APTOS 2019 + IDRiD grading-train (3,741 train / 334 val) |

`GET /api/status` → `startup_report.all_ready: true`.

## Demo cases exercised (see docs/demo_set.md for full provenance)

| Case | Quality | Predicted Grade | Referral | Pipeline time |
|---|---|---|---|---|
| `good_sample.jpg` | GOOD | 0 — No DR | NO REFER | ~5.6–6.9 s |
| `reject_sample.jpg` | REJECT | halts at Phase 1 | — | ~0.1 s |
| `aptos_grade0_...` (real, labelled Grade 0) | BORDERLINE | 0 ✅ | NO REFER | ~3.8 s |
| `aptos_grade2_...` (real, labelled Grade 2) | BORDERLINE | 0 ❌ (misclassified — disclosed) | NO REFER | ~8.4 s |
| `aptos_grade4_...` (real, labelled Grade 4, PDR) | BORDERLINE | 4 ✅ | **REFER** | ~3.3–4.2 s |

Pipeline time is measured CPU inference latency (dominated by the MA
detector's per-candidate ONNX calls — see `ml_training_report.md` Section 9),
**not** the PS's 30-second ophthalmologist-review-budget concept; the UI
labels these as two distinct things.

## Two full end-to-end walkthroughs (repeatability check)

Both runs: upload/demo-select → Run AI → quality → preprocessing before/after
→ vessel/HE/EX/SE/MA evidence cards → grade + probability bars → calibrated
confidence → model attention heatmap → referral decision → uncertainty
status → doctor-review actions → print-report button. Identical inputs
produced identical grades/decisions both times (reproducible — deterministic
inference, no randomness at serving time). Zero raw tracebacks across either
run or across the failure-mode tests below.

## Failure-mode tests performed

| Scenario | Result |
|---|---|
| Valid image | ✅ full pipeline, all sections render |
| Reject-quality image | ✅ halts cleanly at Phase 1, no downstream fabrication |
| Invalid extension (.txt) | ✅ "Unsupported file format" message, no crash |
| Corrupted image bytes (.jpg) | ✅ "Invalid image file" message, no crash |
| Missing model artifact (vessel model renamed away, then restored) | ✅ "Vessel analysis unavailable: model artifact not found." — verified restored afterward |
| Corrupted model artifact (grading .onnx overwritten with garbage, then restored from backup) | ✅ all downstream sections show "unavailable", zero traceback — verified byte-identical restore afterward |
| Unexpected dimensions (10×10 image) | ✅ "too small" validation message |
| CUDA unavailable at inference | N/A by design — serving never uses CUDA (confirmed: only `CPUExecutionProvider` referenced in `pipeline/*.py`) |
| Backend exception (triggered by the corrupted-artifact test above) | ✅ caught, clean message, no traceback |

## Tests

```
python -m pytest tests -q
144 passed in ~40-46s
```

(Up from 122 passed / 22 skipped before this session's model training — every
test now exercises a real artifact, none are skipped.)

## Artifact paths (for reference)

```
models/quality/{iqa_thresholds.json, metadata.json}
models/vessel_seg/{vessel_model.onnx, metadata.json, training_history.json}
models/lesion_seg/{lesion_model.onnx, metadata.json, training_history.json}
models/ma_detector/{ma_fp_reducer.onnx, metadata.json, training_history.json}
models/grading/{grading_model.onnx, gradcam_fc_weights.npy, metadata.json, training_history.json}
configs/calibration.json
```

## Known limitations (unchanged from the training report, restated for the demo context)

1. All metrics are internal-validation numbers, not the sealed-test PS claim.
2. Decision fusion is a documented fallback, not a fitted model.
3. MA detector's FROC is below the literature reference (resolution trade-off, documented).
4. No uncertainty ensemble, no NV module, no DDR data.
5. The rule-based IQA baseline rejects some real APTOS images — an honest, measured behavior (see `docs/demo_set.md`).
6. `window.print()`-based report generation was verified by code path and manual DOM inspection (button + `@media print` CSS present and correct); a literal browser click-through was not automatable from this shell session — recommend a manual click-check before presenting.
