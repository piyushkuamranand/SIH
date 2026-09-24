PHASE RESULT — PHASE 3
Date: 2026-09-25
Task: TASK-013 | PHASE 3 CHECKPOINT

Input: good_sample.jpg, reject_sample.jpg (data/demo/)
  - good_sample.jpg   : 1024x1024 px colour fundus image (source: tests/fixtures/sample_fundus.jpg), preprocessed to (512, 512, 3) float32
  - reject_sample.jpg : synthetically degraded version (underexposed x0.08, heavy Gaussian blur s=20, JPEG quality 40), preprocessed to (512, 512, 3) float32

Output (Grading ONNX inference blocked pending artifact; decision fusion verified on calibrated outputs):
  good_sample.jpg
    severity_class        : NOT AVAILABLE -- grading ONNX artifact missing (see below)
    raw_probabilities     : NOT AVAILABLE -- grading ONNX artifact missing
    calibrated_confidence : NOT AVAILABLE (calibrated from raw probabilities when model is present)
    grade_alone_decision  : NOT AVAILABLE on raw image; verified via test fixtures (see below)
    referable_decision    : NOT AVAILABLE on raw image; verified via test fixtures (see below)

  reject_sample.jpg
    Phase 1 Quality Gate  : REJECT (Ungradable / Severe degradation)
    Pipeline Execution    : Halted at Phase 1 per safety protocol.
    Phase 3 Action        : Automated referral decision blocked (raises ValueError if passed to decision fusion). Recapture required.

Representative Profile Validation (Phase 3 Chain Execution):
  1. Representative Normal (ICDR Grade 0):
     - Probabilities       : [0.910, 0.060, 0.020, 0.005, 0.005]
     - Calibrated Conf.    : 0.910 (T=1.0, fitted=False)
     - Grade-alone Decision: NO REFER
     - Referable Decision  : NO REFER (Agreement: AGREE)
     - Fusion Status       : using grade-alone fallback, fusion model not yet trained

  2. Representative Moderate NPDR (ICDR Grade 2):
     - Probabilities       : [0.050, 0.150, 0.650, 0.100, 0.050]
     - Calibrated Conf.    : 0.650 (T=1.0, fitted=False)
     - Grade-alone Decision: REFER
     - Referable Decision  : REFER (Agreement: AGREE)
     - Fusion Status       : using grade-alone fallback, fusion model not yet trained
     - Evidence Logged     : 12 MAs, HE present=True, EX area=0.0040

  3. Representative Severe NPDR (ICDR Grade 3):
     - Probabilities       : [0.010, 0.040, 0.200, 0.650, 0.100]
     - Calibrated Conf.    : 0.650 (T=1.0, fitted=False)
     - Grade-alone Decision: REFER
     - Referable Decision  : REFER (Agreement: AGREE)
     - Fusion Status       : using grade-alone fallback, fusion model not yet trained
     - Evidence Logged     : 25 MAs, HE present=True, EX area=0.0150

  4. Constructed Borderline Quality Sensitivity Case (P(referable) = 0.400, predicted Grade 1):
     - Probabilities       : [0.150, 0.450, 0.150, 0.150, 0.100]
     - Calibrated Conf.    : 0.450 (T=1.0, fitted=False)
     - Grade-alone Decision: NO REFER (naive 0.50 cutoff)
     - Referable Decision  : REFER (stricter 0.35 cutoff for Borderline quality ensures higher sensitivity)
     - Agreement           : DIFFER (Quality-aware adjustment functioning as designed)
     - Fusion Status       : using grade-alone fallback, fusion model not yet trained

Models:
  1. DR Grading Model (ResNet-50 primary / EfficientNet-B0 backup)
     Contract location : models/grading/metadata.json -- FILE MISSING (ONNX not yet exported)
     ONNX file         : models/grading/grading_model.onnx -- FILE MISSING
     Status            : model artifact missing -- Phase 3 cannot run
                         Error type: FileNotFoundError with message
                         "model artifact missing — Phase 3 cannot run: metadata.json not found in 'models/grading'. ..."
                         This is the CONTRACT WORKING AS INTENDED (per HANDOFF.md Error-Handling Rules). No fabricated grade or probabilities were produced.
     Dataset           : APTOS 2019, DDR, EyePACS (per contract/architecture -- model not yet exported from MATLAB)
     Metric            : not yet measured -- no eval_metrics recorded until formal evaluation task (Quadratic Weighted Kappa not yet measured; never invent numbers)

  2. Calibration (Temperature Scaling)
     Config location   : configs/calibration.json
     Status            : OPERATIONAL (unfitted state: temperature=1.0, fitted=false)
     Behavior          : Safely preserves probability distributions in unfitted state; supports sharpening (T<1.0) and flattening (T>1.0) upon calibration fitting.

  3. Decision Fusion (Referral Decision)
     Config location   : configs/decision_rule.json
     Model location    : models/decision_fusion/metadata.json (not yet trained offline)
     Status            : OPERATIONAL in fallback mode (fitted=false, fusion_status="using grade-alone fallback, fusion model not yet trained")
     Behavior          : Combines calibrated probabilities with lesion evidence (MA count, HE presence, EX area) and intake quality tier. Implements dual-threshold sensitivity (0.50 for Good quality, 0.35 for Borderline quality). Reports both grade_alone_decision and referable_decision side by side.

Files:
  - pipeline/grading.py
  - configs/calibration.json
  - pipeline/decision.py
  - configs/decision_rule.json
  - pipeline/contract.py

What works:
  - pipeline/grading.py: run_grading() loads model via contract, validates dimensions/normalization, computes softmax probabilities, and returns structured class outputs and backbone metadata.
  - apply_calibration(): implements temperature scaling with mathematical invariants (prob sum = 1.0, non-negative, softening/sharpening), reading honestly from configs/calibration.json.
  - pipeline/decision.py: run_decision_fusion() computes both referable_decision and grade_alone_decision side by side, enforcing stricter sensitivity (threshold 0.35) for Borderline-quality images.
  - Quality safety gate: strictly halts Reject-quality images from receiving automated decisions.
  - Honest reporting: clearly sets fitted=False and documents fallback status rather than fabricating fusion coefficients.
  - Test suite: 30 unit tests pass across test_grading.py, test_calibration.py, and test_decision.py (100 passed across entire project test suite).

What does not work:
  - Live ONNX inference for DR grading cannot run because models/grading/metadata.json and models/grading/grading_model.onnx have not yet been exported from MATLAB.
  - Temperature scaling and decision fusion currently run in documented unfitted/fallback modes pending offline fitting.

Limitations:
  - Grading model has not been formally evaluated on a held-out test split yet.
  - 1 integration test (test_grading_integration_live) in tests/test_grading.py is skipped pending MATLAB ONNX export.

Blocker for Ready for next phase: YES:
  Deliver MATLAB ONNX export to:
    - models/grading/ (metadata.json + grading_model.onnx)
  and re-run:
    python -m pytest tests/test_grading.py tests/test_calibration.py tests/test_decision.py -v
  The skipped integration test must pass before this checkpoint can be updated.

Ready for next phase: NO
  Reason: DR grading ONNX artifact is missing -- run_grading() raises expected missing artifact error.
  All Phase 3 pipeline modules, temperature calibration logic, quality-tier-aware decision fusion, and contract handling are fully verified.
  Phase 4 work MUST NOT start until this blocker is resolved and this checkpoint is updated to "Ready for next phase: YES".

Test suite result (2026-09-25):
  30 passed, 1 skipped in 0.58s (Phase 3 tests)
  100 passed, 22 skipped in 1.50s (Full project test suite)
