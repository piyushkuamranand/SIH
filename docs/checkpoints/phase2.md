PHASE RESULT — PHASE 2
Date: 2026-09-25
Task: TASK-009 | PHASE 2 CHECKPOINT

Input: good_sample.jpg, reject_sample.jpg (data/demo/)
  - good_sample.jpg   : 1024x1024 px colour fundus image (source: tests/fixtures/sample_fundus.jpg), preprocessed to (512, 512, 3) float32
  - reject_sample.jpg : synthetically degraded version (underexposed x0.08, heavy Gaussian blur s=20, JPEG quality 40), preprocessed to (512, 512, 3) float32

Output (Structure analysis blocked pending ONNX artifacts, see below):
  good_sample.jpg
    vessel_segmentation : NOT AVAILABLE -- vessel_seg ONNX artifact missing (see below)
    lesion_segmentation : NOT AVAILABLE -- lesion_seg ONNX artifact missing (see below)
    ma_detection        : NOT AVAILABLE -- ma_detector ONNX artifact missing (see below)

  reject_sample.jpg
    vessel_segmentation : NOT AVAILABLE -- vessel_seg ONNX artifact missing (see below)
    lesion_segmentation : NOT AVAILABLE -- lesion_seg ONNX artifact missing (see below)
    ma_detection        : NOT AVAILABLE -- ma_detector ONNX artifact missing (see below)

Models:
  1. vessel_segmentation (U-Net)
     Contract location : models/vessel_seg/metadata.json -- FILE MISSING (ONNX not yet exported)
     ONNX file         : models/vessel_seg/vessel_unet.onnx -- FILE MISSING
     Status            : model artifact missing -- Phase 2 vessel segmentation cannot run
                         Error type: FileNotFoundError with message
                         "model artifact missing — Phase 2 vessel segmentation cannot run: metadata.json not found in 'models/vessel_seg'. ..."
                         This is the CONTRACT WORKING AS INTENDED (per HANDOFF.md Error-Handling Rules). No fabricated mask or overlay was produced.
     Dataset           : DRIVE, STARE, CHASE-DB1 (per contract/architecture -- model not yet exported from MATLAB)
     Metric            : not yet measured -- no eval_metrics recorded until TASK for formal evaluation (Dice/IoU not yet measured; never invent numbers)

  2. lesion_segmentation (Multi-head U-Net for HE, EX, SE)
     Contract location : models/lesion_seg/metadata.json -- FILE MISSING (ONNX not yet exported)
     ONNX file         : models/lesion_seg/lesion_unet.onnx -- FILE MISSING
     Status            : model artifact missing -- Phase 2 lesion segmentation cannot run
                         Error type: FileNotFoundError with message
                         "model artifact missing — Phase 2 lesion segmentation cannot run: metadata.json not found in 'models/lesion_seg'. ..."
                         This is the CONTRACT WORKING AS INTENDED. No fabricated lesion masks or subtype features were produced.
     Dataset           : IDRiD, DDR, FGADR (per contract/architecture -- model not yet exported from MATLAB)
     Metric            : not yet measured -- no eval_metrics recorded until TASK for formal evaluation (Dice/IoU not yet measured; never invent numbers)

  3. ma_detector (Two-stage detector: classical candidate extraction + ONNX false positive reducer)
     Contract location : models/ma_detector/metadata.json -- FILE MISSING (ONNX not yet exported)
     ONNX file         : models/ma_detector/ma_fp_reducer.onnx -- FILE MISSING
     Status            : model artifact missing -- Phase 2 MA detection cannot run
                         Error type: FileNotFoundError with message
                         "model artifact missing — Phase 2 MA detection cannot run: metadata.json not found in 'models/ma_detector'. ..."
                         This is the CONTRACT WORKING AS INTENDED. No fabricated counts or detections were produced.
     Dataset           : E-Ophtha, IDRiD, DDR (per contract/architecture -- model not yet exported from MATLAB)
     Metric            : not yet measured -- no eval_metrics recorded until TASK for formal evaluation (FROC / sensitivity at FPs/image not yet measured; never invent numbers)

Files:
  - pipeline/structure.py
  - pipeline/contract.py
  - pipeline/preprocessing.py

Visualization:
  - Vessel overlay helper (_draw_vessel_overlay): applies semi-transparent green mask (0, 255, 0) over preprocessed retinal background.
  - Lesion overlay helper (_draw_lesion_overlay): applies multi-class color masks (HE=red, EX=yellow, SE=cyan) over retinal background.
  - MA overlay helper (_draw_ma_overlay): draws red circular annotations at detected MA candidate coordinates. Verified via TestDrawMAOverlay.
  - Overlay images on full demo images will be rendered and saved to tests/fixtures/output/ upon ONNX model delivery.

What works:
  - pipeline/structure.py: full implementation of run_vessel_segmentation(), run_lesion_segmentation(), and run_ma_detection() reading strictly from contract metadata (no hardcoded input dimensions, normalizations, thresholds, or mask labels).
  - Classical candidate extraction: both morphological top-hat (_extract_ma_candidates_tophat) and matched filtering (_extract_ma_candidates_matched_filter) verified on synthetic and real test fixtures.
  - Contract validation and missing-model error handling: all functions raise clear, specific FileNotFoundError / ModelArtifactNotFoundError without fabricating masks, lesion counts, or bounding locations.
  - Overlay drawing utilities: _draw_vessel_overlay, _draw_lesion_overlay, and _draw_ma_overlay produce valid HWC uint8 BGR visualizations matching input image spatial dimensions.
  - Test suite: 35 unit and schema tests pass across test_structure_vessel.py, test_structure_lesion.py, and test_structure_ma.py (70 passed across the entire project test suite).

What does not work:
  - Live ONNX inference for vessel segmentation, lesion segmentation, and MA false-positive reduction cannot run because MATLAB-exported model artifacts (metadata.json and .onnx files) have not yet been placed in models/vessel_seg/, models/lesion_seg/, and models/ma_detector/.
  - This blocks vessel_mask, lesion masks (HE/EX/SE), lesion area calculations, and final MA count on data/demo/ images until models are delivered.

Limitations:
  - Segmentation models and MA classifier have not been formally evaluated on held-out test benchmarks yet.
  - 19 integration tests in tests/test_structure_*.py are skipped pending MATLAB ONNX artifact exports.

Blocker for Ready for next phase: YES:
  Deliver MATLAB ONNX exports to:
    - models/vessel_seg/ (metadata.json + vessel_unet.onnx)
    - models/lesion_seg/ (metadata.json + lesion_unet.onnx)
    - models/ma_detector/ (metadata.json + ma_fp_reducer.onnx)
  and re-run:
    python -m pytest tests/test_structure_vessel.py tests/test_structure_lesion.py tests/test_structure_ma.py -v
  All 19 skipped integration tests must pass before this checkpoint can be updated.

Ready for next phase: NO
  Reason: Phase 2 ONNX model artifacts are missing -- run_vessel_segmentation(), run_lesion_segmentation(), and run_ma_detection() raise expected missing artifact errors.
  All pipeline functions, classical candidate extractors, contract validation routines, and visualization helpers are fully implemented and verified.
  Phase 3 work MUST NOT start until this blocker is resolved and this checkpoint is updated to "Ready for next phase: YES".

Test suite result (2026-09-25):
  35 passed, 19 skipped in 0.58s (Phase 2 tests)
  70 passed, 21 skipped in 1.44s (Full project test suite)
