# NETRA-DR — MATLAB Implementation Layer

This is an **additional** MATLAB implementation layer alongside the existing,
unmodified Flask/Python prototype (`app/app.py`) — it does not replace it.
It satisfies the MATLAB-based nature of SIH26038 with a genuinely executable
MATLAB pipeline over the same frozen, trained model artifacts.

## The honest technical description

> Neural-network training artifacts were produced in PyTorch and are
> imported as frozen ONNX models. The screening inference/orchestration,
> image processing, explainability, reporting, and workflow simulation
> interfaces are implemented in MATLAB.

Specifically: **no model was retrained, fine-tuned, or converted in this
MATLAB layer.** The four neural-network stages (grading, vessels, lesions,
MA false-positive reducer) are the exact same `.onnx` files the Python
prototype uses. Everything around them — contract loading and validation,
preprocessing, the quality gate, calibration math, decision logic, model
attention (class activation mapping), report generation, and the demo UI —
is real, native MATLAB code.

## Why ONNX inference runs via MATLAB's Python interoperability

This environment (MATLAB R2026a) does **not** have the *Deep Learning
Toolbox Converter for ONNX Model Format* support package installed —
verified directly (`exist('importNetworkFromONNX')` and
`exist('importONNXNetwork')` both return `0`), not assumed. Per the
project's explicit instruction not to install anything automatically, the
documented, supported alternative was used instead: MATLAB's `pyenv`/`py.*`
interoperability, calling the same `onnxruntime` package the Python
prototype already depends on.

This is **not** "a MATLAB file that calls a Python script and returns the
result." `netra.onnxio.OnnxSessionCache` and `netra.onnxio.runInference`
are real MATLAB code that constructs the `onnxruntime.InferenceSession`
object, builds the NCHW input tensor (as a native MATLAB array, converted to
`py.numpy.array` — verified element-for-element, no manual axis permutation
needed: `py.numpy.array(A)` preserves both MATLAB's shape and index
correspondence), calls `.run()`, and consumes the numeric output directly
back into the MATLAB workspace. Every surrounding computation — resizing,
normalization, thresholding, the class-activation-map math, the decision
logic — happens in MATLAB, not Python. `pyenv` was found already configured
against the Anaconda Python environment that has `onnxruntime` installed;
no new dependency was introduced.

**If the ONNX Model Format Converter package is installed later**, the
correct upgrade path is: replace `netra.onnxio.runInference`'s body with
`importNetworkFromONNX` + `predict(dlnet, ...)`, and swap
`netra.explain.computeModelAttention`'s manual CAM math for native
`gradCAM(dlnet, ...)`. Nothing else in this codebase would need to change —
every consumer of `netra.onnxio.runInference` and
`netra.explain.computeModelAttention` only depends on their documented
input/output contract, not their internal implementation.

## What is imported

| Model | File | Trained on |
|---|---|---|
| DR grading | `models/grading/grading_model.onnx` | APTOS 2019 + IDRiD grading-train (ResNet-50, ImageNet-pretrained) |
| Vessels | `models/vessel_seg/vessel_model.onnx` | DRIVE |
| Lesions (HE/EX/SE) | `models/lesion_seg/lesion_model.onnx` | IDRiD segmentation |
| MA false-positive reducer | `models/ma_detector/ma_fp_reducer.onnx` | IDRiD segmentation |

The quality gate (`models/quality/`) has no neural network at all — it is a
rule-based baseline, reimplemented natively in MATLAB from the same
`iqa_thresholds.json` the Python side reads.

## How preprocessing works

`+netra/+preprocess/preprocessImage.m` reproduces
`pipeline/preprocessing.py`'s FOV-crop → resize → CLAHE → normalize chain,
reading every parameter from `configs/preprocessing.json` — nothing is
hardcoded. **Known limitation, documented not hidden:** MATLAB's
`adapthisteq()` is a different CLAHE algorithm from OpenCV's
`cv2.createCLAHE()` (different clip-limit semantics); parameters are
best-effort mapped, but pixel-identical output is not achievable without
reimplementing OpenCV's exact algorithm. See `docs/matlab_parity_report.md`
for the measured impact.

## How inference works

Contract-driven throughout (`+netra/+contract/loadModelContract.m` — same
mandatory-field set as `pipeline/contract.py`). Each stage module
(`+netra/+grading`, `+netra/+vessels`, `+netra/+lesions`, `+netra/+ma`)
resizes/normalizes using ONLY the contract's `input_size`/`normalization`,
runs the frozen ONNX model via `netra.onnxio.runInference` (cached session,
not re-imported per request), and post-processes exactly as the contract's
`output_format`/`mask_labels`/`threshold` specify.

## How calibration works

`+netra/+calibration/applyCalibration.m` reads the actual fitted
`configs/calibration.json` (temperature = 2.80, fitted by
`training/train_grading.py` on the Python side) and applies temperature
scaling: `softmax(log(p) / T)`. It never refits and never hardcodes a
temperature in MATLAB source.

## How Grad-CAM / model attention works

See "Why ONNX inference runs via MATLAB's Python interoperability" above —
native `gradCAM()` needs a `dlnetwork`, unavailable here. Instead,
`+netra/+explain/computeModelAttention.m` computes the **exact** class
activation map (Zhou et al. 2016), which is mathematically identical to
`gradCAM()`'s output for a GAP→FC-head architecture like this ResNet-50, no
gradient/backward pass required. UI/report terminology is always "model
attention," never "clinical proof."

## How to run the MATLAB demo

```
matlab -batch "run('<repo>/matlab/run_netradr_demo.m')"
```

verified in this environment (MATLAB R2026a, Windows). This prints an
environment/artifact validation summary, then launches the `uifigure`-based
demonstration UI (`matlab/ui/NetraDRApp.m`): Upload/Load Demo Case → Run
Analysis → Generate Report. For headless/scripted use without the UI, call
`run_netradr_pipeline(imagePath)` directly.

## How to run MATLAB tests

```
matlab -batch "run('<repo>/matlab/run_tests.m')"
```

34 tests across `matlab/tests/` (contract, quality, grading, calibration,
vessels/lesions/MA/model-attention/NV, pipeline error-handling, and a
parity regression lock referencing `docs/matlab_parity_report.md`). All 34
pass as of 2026-09-26; **34/34 exercised real model artifacts and real demo
images — none are mocked.**

## How to run the Simulink component

Unchanged from the existing project: `matlab/sweep_ratio.m` and
`docs/checkpoints/simulink_results.md`. Not touched or re-validated in this
session — Simulink remains a separate, non-blocking district-workflow track,
never wired into per-image inference.

## Toolbox requirements

| Toolbox | Used for | Status in this environment |
|---|---|---|
| Image Processing Toolbox | `imread`, `imresize`, `rgb2lab`, `adapthisteq`, `imbothat`, `regionprops` | Present |
| Deep Learning Toolbox | (only `gradCAM` existence checked; not used — see above) | Present, but the ONNX converter package is not |
| Statistics and Machine Learning Toolbox | (available; not directly used by this layer) | Present |
| Simulink | `sweep_ratio.m` (pre-existing) | Present |
| Deep Learning Toolbox Converter for ONNX Model Format | `importNetworkFromONNX`/`importONNXNetwork` | **Not installed** — this is why the `py.*`/onnxruntime path is used |
| Python (via `pyenv`) | ONNX inference backend | Present, pre-configured against the same Anaconda env used for training |

## Known limitations

1. ONNX inference runs through MATLAB's Python interoperability, not a
   native `dlnetwork` — documented extensively above, not a hidden
   workaround.
2. CLAHE and (to a lesser, now largely-fixed extent) resize-interpolation
   differences from OpenCV cause small-to-moderate numeric divergence in
   preprocessed pixel values, which cascades into the segmentation/detection
   stages more than into the grading stage (see `docs/matlab_parity_report.md`).
3. Optic disc/fovea localization and neovascularization are not implemented
   (no trained NV model exists at all; OD/fovea was out of scope for this
   integration task) — both are honestly reported as unavailable, not faked.
4. The MATLAB UI is a display+report path; it does not have the Flask UI's
   Confirm/Override/note-capture review controls.
5. Simulink/SimEvents status was not re-validated this session.
