PHASE RESULT — PHASE 1
Date: 2026-09-25
Task: TASK-005 | PHASE 1 CHECKPOINT

Input: good_sample.jpg, reject_sample.jpg  (data/demo/)
  - good_sample.jpg   : 1024x1024 px colour fundus image (source: tests/fixtures/sample_fundus.jpg)
  - reject_sample.jpg : synthetically degraded version (underexposed x0.08, heavy Gaussian blur s=20,
                        JPEG quality 40) -- used to represent a Reject-quality image for demo purposes
                        pending a real Reject image from the DDR ungradable subset

Output (preprocessing only -- quality gate blocked, see below):
  good_sample.jpg
    quality_label       : NOT AVAILABLE -- quality_gate ONNX artifact missing (see below)
    quality_score       : NOT AVAILABLE
    preprocessed_image  : float32 array, shape (512, 512, 3), min=0.0000, max=1.0000 OK

  reject_sample.jpg
    quality_label       : NOT AVAILABLE -- quality_gate ONNX artifact missing (see below)
    quality_score       : NOT AVAILABLE
    preprocessed_image  : float32 array, shape (512, 512, 3), min=0.0000, max=0.1490 OK
                          (dark image correctly normalised without error)

Model: quality_gate
  Contract location : models/quality/metadata.json  -- FILE MISSING (ONNX not yet exported)
  ONNX file         : models/quality/quality_model.onnx -- FILE MISSING
  Status            : model artifact missing -- Phase 1 cannot run
                      Error type: FileNotFoundError with message
                      "model artifact missing -- Phase 1 cannot run: metadata.json not found in
                      'models/quality'. ..."
                      This is the CONTRACT WORKING AS INTENDED (per HANDOFF.md Error-Handling Rules
                      and TASK-004 done-when). No fabricated label was produced.

Dataset: DDR ungradable subset (per contract -- model not yet trained/exported)

Metric: not yet measured -- no eval_metrics recorded until TASK for formal evaluation

Files: pipeline/quality.py, pipeline/preprocessing.py

Visualization:
  tests/fixtures/output/good_sample_before.jpg   (original 1024x1024, raw)
  tests/fixtures/output/good_sample_after.jpg    (512x512, FOV-cropped + CLAHE + normalised)
  tests/fixtures/output/reject_sample_before.jpg (original 1024x1024, severely degraded)
  tests/fixtures/output/reject_sample_after.jpg  (512x512, processed -- visibly dark, low contrast)

What works:
  - pipeline/preprocessing.py: FOV crop -> resize -> CLAHE -> normalize runs correctly on both images
    with no runtime error. Output shape (512, 512, 3), dtype float32, values in [0, 1].
  - pipeline/quality.py: contract loading, ONNX path resolution, and error-handling paths all
    confirmed via 22 passed / 2 skipped tests (test_quality.py + test_preprocessing.py).
  - Missing-model error path: raises a clear, specific FileNotFoundError naming the missing file
    and phase -- never fabricates a quality label.
  - The reject_sample image is visually distinguishable from the good_sample image in both the
    before and after visualisations (max pixel value 0.149 vs 1.000 after normalisation).

What does not work:
  - Quality gate ONNX inference cannot run: models/quality/metadata.json and
    models/quality/quality_model.onnx have not been exported from MATLAB yet.
    This blocks quality_label and quality_score output for both demo images.
  - The reject_sample.jpg in data/demo/ is a synthetically degraded image, not a real DDR
    ungradable-class image. It correctly exercises the preprocessing path but cannot be used to
    validate quality_label accuracy until the ONNX model is present.

Limitations:
  - Quality model has not been formally evaluated on a held-out set yet.
  - Integration tests (test_inference_returns_expected_keys,
    test_preprocessed_image_returned_for_reject_and_good) are skipped pending MATLAB ONNX export.
  - reject_sample.jpg is synthetic -- replace with a real DDR ungradable image when available.

Blocker for Ready for next phase: YES:
  Deliver models/quality/quality_model.onnx + models/quality/metadata.json
  (MATLAB exportONNXNetwork output) and re-run:
    python -m pytest tests/test_quality.py tests/test_preprocessing.py -v
  Both previously-skipped integration tests must pass before this checkpoint can be updated.

Ready for next phase: NO
  Reason: quality gate ONNX artifact is missing -- run_quality_gate() raises
  "model artifact missing -- Phase 1 cannot run" on both demo images.
  Preprocessing and all error-handling paths are fully verified.
  Phase 2 work MUST NOT start until this blocker is resolved and this checkpoint is
  updated to "Ready for next phase: YES".

Test suite result (2026-09-25):
  22 passed, 2 skipped in 0.88s
  Passed : all unit + API-contract tests for quality.py and preprocessing.py
  Skipped: 2 integration tests (skipped because ONNX artifact is absent -- expected)
