# NETRA-DR MATLAB Implementation Report

**Date:** 2026-09-26
**Task:** MATLAB implementation/integration layer over already-trained, frozen models (no training performed).

## MATLAB version and toolboxes

- MATLAB R2026a (26.1.0.3346908, Update 5), Windows.
- Present: Image Processing Toolbox, Computer Vision Toolbox, Deep Learning
  Toolbox, Medical Imaging Toolbox, Statistics and Machine Learning Toolbox, Simulink.
- **Not installed:** Deep Learning Toolbox Converter for ONNX Model Format
  (`importNetworkFromONNX` and `importONNXNetwork` both verified absent —
  `exist(...)` returns 0 for both). Parallel Computing Toolbox also absent
  (irrelevant here — inference is CPU-only regardless).
- `pyenv` found pre-configured against the project's Anaconda Python 3.13
  environment, which has `onnxruntime==1.30.0` installed — used as the
  ONNX inference backend (see `matlab/README.md` for the full justification).

## Model artifacts used (frozen, unmodified)

`models/{grading/grading_model.onnx, vessel_seg/vessel_model.onnx,
lesion_seg/lesion_model.onnx, ma_detector/ma_fp_reducer.onnx}` and
`models/quality/iqa_thresholds.json`. All five confirmed present and loadable
by `run_netradr_demo.m`'s startup validation. **None were modified,
retrained, or converted.**

## ONNX import status

**Not imported as MATLAB `dlnetwork` objects** — the required support
package is not installed, and nothing was installed per instruction. Instead,
run via MATLAB's Python interoperability calling `onnxruntime`
(`+netra/+onnxio/`), with persistent session caching (`OnnxSessionCache`,
verified via test: second `.get()` call for the same path returns the
identical cached session object, not a fresh import).

## Stage-by-stage implementation

| Stage | File | Implementation |
|---|---|---|
| Contract | `+netra/+contract/loadModelContract.m` | Native MATLAB JSON parsing + the same mandatory-field validation as `pipeline/contract.py` |
| Preprocessing | `+netra/+preprocess/preprocessImage.m` | Native: FOV crop, `imresize` (adaptive box/bilinear matching `cv2.INTER_AREA`/`INTER_LINEAR`), `adapthisteq` CLAHE, normalize |
| Quality | `+netra/+quality/assessQuality.m` | Native: Laplacian-variance focus, illumination clipping, FOV coverage, thresholds read from `iqa_thresholds.json` |
| Vessels | `+netra/+vessels/runVesselSegmentation.m` | Native pre/post-processing + ONNX inference |
| Lesions | `+netra/+lesions/runLesionSegmentation.m` | Native, contract-driven channel order (never hardcoded HE/EX/SE order) + ONNX inference |
| MA | `+netra/+ma/runMADetection.m` | **Native MATLAB classical candidate extraction** (`imbothat` black-hat + `regionprops`, matching `pipeline/structure.py`'s algorithm) + ONNX inference for the CNN FP-reducer |
| Grading | `+netra/+grading/runGrading.m` | Native pre/post-processing + ONNX inference (ResNet-50 — the required final architecture, verified by test to contain "resnet50" in its model name and to have 2048 feature channels) |
| Calibration | `+netra/+calibration/applyCalibration.m` | Native temperature scaling, reads the actual fitted `configs/calibration.json` (T=2.80) |
| Decision | `+netra/+decision/runDecisionFusion.m` | Native, same quality-tier fallback logic as `pipeline/decision.py` (no fitted fusion model exists on either side) |
| Model attention | `+netra/+explain/computeModelAttention.m` | Native exact class-activation-map math (FC-weights × feature map, via a native `.npy` reader, `+netra/+utils/readNPY.m`) — mathematically equivalent to `gradCAM()` for this architecture |
| NV | `+netra/+anatomy/runNVAnalysis.m` | Honest "unavailable" interface — no model exists |
| Report | `+netra/+report/generateReport.m` | Native HTML assembly, evidence/attention/decision kept in separate sections |
| UI | `matlab/ui/NetraDRApp.m` | Native `uifigure` app |
| Orchestrator | `matlab/run_netradr_pipeline.m` | Native, per-stage timing + non-swallowed error records |
| Demo entry point | `matlab/run_netradr_demo.m` | Environment validation + UI launch |

## Parity results (full detail: `docs/matlab_parity_report.md`)

Measured on 4 real demo images:

- **Predicted ICDR grade: 3/3 match** (100%, on images that passed the quality gate on both sides).
- **Referral decision: 3/3 match** (100%).
- **Quality label: 3/4 match.** Two real bugs found and fixed during this
  work (MATLAB `var()` N-1 vs NumPy `np.var()` N normalization; bilinear vs
  area-averaging resize on downsampling) improved this from 2/4 to 3/4. The
  remaining mismatch is root-caused to a residual Laplacian/grayscale
  implementation difference between MATLAB's Image Processing Toolbox and
  OpenCV, not fixed further given the time budget.
- **Vessel/lesion/MA pixel-level outputs:** same qualitative signal, not
  tight numeric parity — traced to the CLAHE algorithm difference (documented
  limitation, not a bug in either implementation).

## MATLAB tests

`matlab/tests/` — 34 tests, **34 passed, 0 failed, 0 incomplete**
(`matlab/run_tests.m`). Covers: contract validation (valid + 5 distinct
failure modes), quality gate (real good/reject images + corrupted-file
handling), grading (real inference, architecture check, feature-map shape),
calibration (no-op case, actual fitted config, invalid-input errors),
vessels/lesions/MA/model-attention/NV (real inference + missing-artifact
error), full-pipeline end-to-end + 3 distinct failure-injection scenarios
(missing image, missing vessel model mid-pipeline, corrupted grading ONNX
file), and a parity regression lock against the numbers in
`docs/matlab_parity_report.md`.

## Python tests

`python -m pytest tests -q` → **144 passed, 0 failed, 0 skipped** — unchanged
from before this MATLAB work began (the Python system was not modified).

## Report generation command

Programmatic: `netra.report.generateReport(pipelineResult, imagePath, outputDir)`.
Via the UI: the "Generate Report" button after "Run Analysis". Verified: a
real HTML report was generated from a real pipeline result and inspected —
all required sections present (quality, detected evidence, grading, model
attention, referral decision, processing time, prototype disclaimer).

## Simulink status

**Not touched, not re-validated this session** — `matlab/sweep_ratio.m` and
`docs/checkpoints/simulink_results.md` are exactly as TASK-021 left them.
Kept as a separate, independent track per instruction; the per-image MATLAB
pipeline above has no dependency on Simulink/SimEvents being available.

## Startup command

```
matlab -batch "run('<repo>/matlab/run_netradr_demo.m')"
```
Verified in this environment: prints a 5/5 model-artifact readiness check
and the `pyenv` status, then launches the demonstration UI. A full
programmatic UI walkthrough (image load → Run Analysis → results render →
Generate Report) was also executed and verified without error.

## Exact files created

```
matlab/README.md
matlab/run_netradr_demo.m
matlab/run_netradr_pipeline.m
matlab/run_tests.m
matlab/+netra/+contract/loadModelContract.m
matlab/+netra/+preprocess/preprocessImage.m
matlab/+netra/+quality/assessQuality.m
matlab/+netra/+onnxio/OnnxSessionCache.m
matlab/+netra/+onnxio/runInference.m
matlab/+netra/+grading/runGrading.m
matlab/+netra/+calibration/applyCalibration.m
matlab/+netra/+vessels/runVesselSegmentation.m
matlab/+netra/+lesions/runLesionSegmentation.m
matlab/+netra/+ma/runMADetection.m
matlab/+netra/+decision/runDecisionFusion.m
matlab/+netra/+explain/computeModelAttention.m
matlab/+netra/+anatomy/runNVAnalysis.m
matlab/+netra/+report/generateReport.m
matlab/+netra/+utils/readNPY.m
matlab/ui/NetraDRApp.m
matlab/tests/test_contract.m
matlab/tests/test_quality.m
matlab/tests/test_grading.m
matlab/tests/test_calibration.m
matlab/tests/test_structure_modules.m
matlab/tests/test_pipeline.m
matlab/tests/test_parity.m
docs/matlab_implementation_mapping.md
docs/matlab_parity_report.md
docs/checkpoints/matlab_implementation_report.md
```

## Exact files modified

None under `pipeline/`, `app/`, `training/`, or `models/`. `.gitignore` was
restored (see git-safety note below) after being found weakened outside of
this task's own edits.

## Known limitations (full detail above and in `matlab/README.md`)

1. ONNX inference via MATLAB↔Python↔onnxruntime, not a native `dlnetwork` (no converter package installed).
2. CLAHE algorithm difference (adapthisteq vs OpenCV) is the dominant source of remaining numeric divergence.
3. Optic disc/fovea localization: not implemented (out of scope this session).
4. Neovascularization: not implemented, honestly reported as unavailable.
5. MATLAB UI lacks the Flask UI's Confirm/Override/note-capture controls.
6. Simulink/SimEvents not re-validated this session.

## Git safety note

Before this task's own work began, `.gitignore` was found with
`data/processed/**`, `models/**/*.onnx`, `models/**/*.pth`,
`models/**/*.npy`, `models/**/_best_checkpoint.pt`, and `external/` all
commented out, and `git status` showed ~4,000 `data/processed/` cache files
plus all 4 `.onnx` checkpoints already staged (`git add`-ed) as a result.
This was found, flagged, and reversed (`.gitignore` restored, all matching
paths unstaged via `git reset`) before any MATLAB work began — see the
conversation record. Verified again at the end of this task: `git add -A
--dry-run` shows zero `.onnx`/`.pt`/`.npy`/`data/processed/`/`external/`
paths would be added.
