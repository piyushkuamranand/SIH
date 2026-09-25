PHASE RESULT — PHASE 4
Date: 2026-09-25
Task: TASK-016 | PHASE 4 CHECKPOINT

Input: data/demo/ — good_sample.jpg, reject_sample.jpg
  - good_sample.jpg   : real fundus colour image, preprocessed to (512, 512, 3) float32
  - reject_sample.jpg : synthetically degraded (underexposed x0.08, heavy blur, JPEG quality 40)

Output — run_full_pipeline() on every demo image:

  good_sample.jpg
    Phase 1 — quality_label     : NOT AVAILABLE (grading/quality ONNX artifact missing)
    Phase 1 — quality_score     : NOT AVAILABLE (same)
    Phase 2 — vessel_mask       : NOT AVAILABLE (vessel_seg ONNX artifact missing)
    Phase 2 — lesion_overlay    : NOT AVAILABLE (lesion_seg ONNX artifact missing)
    Phase 2 — ma_count          : NOT AVAILABLE (ma_detector ONNX artifact missing)
    Phase 3 — severity_class    : NOT AVAILABLE (grading ONNX artifact missing)
    Phase 3 — referable_decision: NOT AVAILABLE (depends on Phase 3)
    Phase 4 — heatmap_overlay   : NOT AVAILABLE (depends on Phase 3)
    stopped_at_phase1           : True (triggered by Phase 1 missing-artifact error)
    error                       : "Phase 1 error: FileNotFoundError: model artifact missing
                                   — Phase 1 cannot run: metadata.json not found in 'models/quality'."

    Note: This is the CONTRACT WORKING AS INTENDED (HANDOFF.md Error-Handling Rules).
    No fabricated quality label, grade, or referral decision was produced.

  reject_sample.jpg
    Same missing-model error path as above — Phase 1 cannot run because
    models/quality/metadata.json has not been exported from MATLAB.

Pipeline Function Verification (via unit tests with mocked phases):

  run_full_pipeline() has been verified against all cases by 7 unit tests
  in tests/test_report.py (114 passed, 22 skipped in the full suite):

  Case A: Good quality, all phases mocked → all four phase keys populated.
    - stopped_at_phase1 = False
    - phase1: quality_label="Good", quality_score=0.9, preprocessed_image populated
    - phase2: vessel_mask (ndarray), ma_count=3, he_presence=True, ex_area=0.002
    - phase3: severity_class=0, confidence=0.7, referable_decision="NO REFER",
              grade_alone_decision="NO REFER", fusion_status documented
    - phase4: heatmap_overlay (ndarray), label="model attention" (invariant enforced)
    - error = None

  Case B: Reject quality → stopped_at_phase1=True, phases 2-4 empty/null.
    - stopped_at_phase1 = True
    - phase2/3/4 values are None/default (not missing keys)
    - phase4["label"] == "model attention" (even when heatmap is None)

  Case C: Phase 1 model missing → stopped_at_phase1=True, error surfaced.
    - error key contains "Phase 1 error: ModelArtifactNotFoundError: ..."
    - No fabricated result in any phase

  Case D: Phase 2 models missing → pipeline continues, error logged.
    - Phase 2 values default to None/0 (not fabricated)
    - Phase 3 and 4 still proceed with default Phase 2 inputs

  Case E: Borderline quality → pipeline does NOT stop (continues through all phases).

  Case F: Image not found → FileNotFoundError raised before any phase (correct).

  Case G: All top-level keys always present in result dict.

Models:
  1. Quality Gate (IQA): models/quality/ — ONNX artifact MISSING (not exported from MATLAB)
  2. Vessel Segmentation: models/vessel_seg/ — ONNX artifact MISSING
  3. Lesion Segmentation: models/lesion_seg/ — ONNX artifact MISSING
  4. MA Detector: models/ma_detector/ — ONNX artifact MISSING
  5. DR Grading: models/grading/ — ONNX artifact MISSING
  6. Calibration: configs/calibration.json — OPERATIONAL (unfitted: temperature=1.0, fitted=false)
  7. Decision Fusion: configs/decision_rule.json — OPERATIONAL in fallback/unfitted mode
  8. Grad-CAM: uses same grading ONNX — MISSING (blocked by same artifact)

Files:
  - pipeline/report.py (TASK-015 — run_full_pipeline())
  - tests/test_report.py (TASK-015 — 7 tests)
  - pipeline/quality.py
  - pipeline/structure.py
  - pipeline/grading.py
  - pipeline/decision.py
  - pipeline/explain.py

What works:
  - run_full_pipeline() correctly chains all four phases in sequence.
  - Reject-quality gate halts the pipeline cleanly at Phase 1 with stopped_at_phase1=True.
  - Per-phase exception handling: each phase failure produces a phase-labelled error string
    rather than an unhandled stack trace reaching the caller.
  - Phase 2 failures (e.g. any individual model missing) do not crash Phase 3 or 4;
    the pipeline continues with default zero-values for Phase 2 evidence inputs.
  - "model attention" label invariant is enforced: phase4["label"] is always exactly
    "model attention" regardless of whether an actual heatmap was generated.
  - All function signatures, input/output contracts, and error-handling rules follow HANDOFF.md.
  - Full test suite: 114 passed, 22 skipped (22 skips are integration tests awaiting
    MATLAB ONNX exports — all intentional, none hiding failures).

What does not work:
  - Live end-to-end inference on real demo images is blocked for every ML phase because
    no MATLAB-exported ONNX artifacts exist yet in the models/ directories.
  - The 22 skipped integration tests cover live ONNX inference paths; they cannot pass
    until the MATLAB team delivers the model artifacts.

Known limitations carried forward from all previous checkpoints:
  1. ONNX model artifacts: All five model directories (quality, vessel_seg, lesion_seg,
     ma_detector, grading) are missing their .onnx files and metadata.json — delivery
     blocked on MATLAB side.
  2. Temperature calibration: configs/calibration.json has temperature=1.0, fitted=false.
     Fitting requires a validation fold run, which cannot proceed without the grading model.
  3. Decision fusion: pipeline/decision.py runs in fallback/unfitted mode (no trained
     logistic regression coefficients). Grade-alone fallback is explicitly documented.
  4. Ensemble grading (ResNet-50 + EfficientNet-B0): Stage 10 ensemble is
     documented as OPTIONAL in the architecture. Not implemented in this prototype.
  5. NV (neovascularization) detection: Stage 6 is documented as OPTIONAL. Not implemented.
  6. Simulink (TASK-021): Independent track — can be built by a separate team member
     without blocking the website pipeline.
  7. reject_sample.jpg is synthetically degraded; should be replaced with a real
     DDR ungradable image when available.

Ready for next phase: YES
  Reason: run_full_pipeline() is fully implemented, tested, and correctly handles all
  pipeline states (full-run, stopped-at-Phase-1, partial-model-missing). The website
  (TASK-017) can now call this single function and render the structured output.
  The known limitation that live ONNX inference is blocked does not prevent the website
  from being built and tested end-to-end — the website will display clear "model artifact
  missing" messages for phases that cannot run, exactly as the contract requires.

Test suite result (2026-09-25):
  114 passed, 22 skipped in 16.71s (full project test suite)
  7 passed in 6.06s (tests/test_report.py)
