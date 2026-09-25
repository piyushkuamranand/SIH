FINAL DRY RUN CHECKPOINT
Date: 2026-09-25
Task: TASK-020 | Final demo hardening / dry run checkpoint

=============================================================================
DRY RUN SUMMARY
=============================================================================

Command: python app/app.py  (or run_demo.bat / bash run_demo.sh)
Result:  Flask server starts successfully at http://127.0.0.1:5000

Startup check output (printed to console on launch):
  [MISS]  Phase 1 - Quality Gate (IQA)
          metadata.json not found in 'models/quality' - ONNX not yet exported from MATLAB.
  [MISS]  Phase 2 - Vessel Segmentation
          metadata.json not found in 'models/vessel_seg' - ONNX not yet exported from MATLAB.
  [MISS]  Phase 2 - Lesion Segmentation (HE/EX/SE)
          metadata.json not found in 'models/lesion_seg' - ONNX not yet exported from MATLAB.
  [MISS]  Phase 2 - MA Detector
          metadata.json not found in 'models/ma_detector' - ONNX not yet exported from MATLAB.
  [MISS]  Phase 3/4 - DR Grading + Grad-CAM
          metadata.json not found in 'models/grading' - ONNX not yet exported from MATLAB.
  [WARN] 5 model(s) missing. Affected phases will show 'unavailable' in the web UI.

=============================================================================
DRY RUN — IMAGE-BY-IMAGE RESULTS
=============================================================================

Image 1: good_sample.jpg (664 KB, real fundus photograph)
  Upload:          Accepted (JPG, within 32 MB limit)
  Phase 1 result:  "Phase 1 error: FileNotFoundError: model artifact missing — 
                    Phase 1 cannot run: metadata.json not found in 'models/quality'."
  stopped_at_phase1: True (Phase 1 exception triggers safe stop)
  Page rendered:   Upload form + error detail in Phase 1 card
  Timing:          ~0.3 s (no model inference — all model-missing paths)
  Broken sections: None — all phases show "unavailable" or "model artifact missing" text.
  Crashes:         None.
  Fabricated data: None. (Contract working as intended.)

Image 2: reject_sample.jpg (~19 KB, synthetically degraded)
  Upload:          Accepted
  Phase 1 result:  Same missing-artifact error path as above
  Page rendered:   Same as Image 1 (cannot distinguish Reject vs Good without the model)
  Timing:          ~0.2 s
  Crashes:         None.

Flask app verification (import + routes):
  Routes confirmed: GET / (upload form) + POST / (pipeline + render) + /static/<path>
  App import:       Clean, no errors.
  startup_check:    Runs at import time, prints summary, sets _STARTUP_REPORT for template.

Pipeline unit test suite (run before dry run):
  Command:  python -m pytest tests/ -v --tb=no -q
  Result:   114 passed, 22 skipped in ~17 s
  22 skips: All integration tests awaiting MATLAB ONNX exports — intentional, not hiding failures.

=============================================================================
ISSUES FOUND AND FIXED DURING DRY RUN
=============================================================================

Issue 1: UnicodeEncodeError in startup_check._print_startup_report
  Root cause: Emoji characters (checkmarks, warning) cannot be encoded by Windows
              cp1252 console codec.
  Fix:        Replaced all emoji with ASCII-safe tokens ([OK], [MISS], [WARN]).
  Status:     Fixed. Startup check prints cleanly on Windows.
  Files changed: pipeline/startup_check.py

Issue 2: Mock patch targets failed in test_report.py
  Root cause: pipeline/report.py used lazy local imports inside functions; mock.patch
              targets "pipeline.report.<name>" but the name didn't exist at module level.
  Fix:        Moved all pipeline function imports to top-level in report.py so they
              are patchable as module attributes.
  Status:     Fixed. 7/7 tests pass.
  Files changed: pipeline/report.py

No other issues found.

=============================================================================
TIMING (approximate, no ONNX inference — CPU only)
=============================================================================

  Server startup:           ~2 s (startup check + Flask initialization)
  Upload + preprocessing:   ~0.3 s (preprocessing runs; model inference fails fast)
  Page render:              <0.1 s
  Total per image:          ~0.5 s (with all models missing)

When ONNX models are present, expected end-to-end time per image:
  Phase 1 (IQA inference):  1-3 s
  Phase 2 (3 models):       3-8 s (segmentation is the bottleneck)
  Phase 3 (grading):        1-2 s
  Phase 4 (Grad-CAM):       1-3 s
  Total:                    6-16 s (CPU; ONNX with CPUExecutionProvider)

=============================================================================
CONSOLIDATED KNOWN LIMITATIONS
=============================================================================

From all previous checkpoints, carried forward:

1. ONNX MODEL ARTIFACTS MISSING (Blocker — MATLAB delivery required)
   - models/quality/  : metadata.json + quality_model.onnx
   - models/vessel_seg/: metadata.json + vessel_seg.onnx
   - models/lesion_seg/: metadata.json + lesion_seg.onnx
   - models/ma_detector/: metadata.json + ma_detector.onnx + fp_reducer.onnx
   - models/grading/  : metadata.json + grading_model.onnx
   Until these are delivered, every ML phase reports "model artifact missing"
   rather than a fabricated result. This is the contract working as intended.

2. TEMPERATURE CALIBRATION (Unfitted)
   configs/calibration.json: temperature=1.0, fitted=false
   Cannot be fitted until the grading model ONNX is available (needs a
   validation fold inference run). Until then, calibration is a mathematical
   no-op (identity transform on probabilities).

3. DECISION FUSION (Fallback mode)
   No trained logistic regression coefficients in models/decision_fusion/.
   System runs in grade-alone fallback mode with quality-tier-aware thresholds.
   Clearly reported in the web UI and pipeline output (fusion_status field).

4. ENSEMBLE GRADING (Not implemented — OPTIONAL per architecture)
   ResNet-50 + EfficientNet-B0 ensemble (Stage 10) is documented as OPTIONAL
   in the architecture. Current implementation uses a single backbone.

5. NEOVASCULARIZATION DETECTION (Not implemented — OPTIONAL per architecture)
   Stage 6 NV detection is documented as OPTIONAL. Not implemented.

6. REJECT DEMO IMAGE IS SYNTHETIC
   reject_sample.jpg is a synthetically degraded version of good_sample.jpg.
   Should be replaced with a real DDR ungradable image before the final
   presentation. See docs/demo_set.md for guidance.

7. SIMULINK WORKFLOW SIMULATION (Separate track — TASK-021)
   Not blocked by the website. Can be built independently. See
   docs/checkpoints/simulink_results.md when complete.

=============================================================================
PRESENTATION READINESS ASSESSMENT
=============================================================================

Prototype is presentation-ready for the following narrative:
  a) Full four-phase pipeline architecture implemented and documented.
  b) Every pipeline module raises clear, specific errors rather than fabricating
     results when model artifacts are missing — demonstrating engineering rigour.
  c) Website launches with one command (run_demo.bat / bash run_demo.sh).
  d) Startup check banner shows judges exactly which models are ready.
  e) Quality gate, calibration, decision fusion all implemented honestly.
  f) Grad-CAM labeled "model attention" throughout — never "clinical evidence".
  g) 114 unit tests pass; 22 integration tests correctly skipped pending ONNX.

Prototype is NOT ready for live ML inference until MATLAB ONNX artifacts are
delivered. The presenter should frame this as "pipeline infrastructure complete,
awaiting MATLAB model exports" — an honest and technically credible position.

Prototype IS presentation-ready: YES (with the caveat above)

=============================================================================
TEST SUITE RESULT (2026-09-25, final dry run)
=============================================================================

python -m pytest tests/ --tb=no -q
  114 passed, 22 skipped in 16.71s (full project test suite)

bash run_demo.sh / run_demo.bat
  Server starts: YES
  Routes respond: YES (verified via app import test)
  Crashes on missing models: NO (clear error messages displayed)
