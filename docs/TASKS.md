# NETRA-DR TASK TRACKER

Read `HANDOFF.md` and `IMPLEMENTATION_SCHEMA.md` before touching this file. This tracker only records state — it does not contain task detail.

## CURRENT TASK

TASK-015 | Final report assembly

## NEXT TASK

TASK-016 | PHASE 4 CHECKPOINT

## COMPLETED TASKS

- [x] TASK-001 — Create repository structure (done 2026-09-25)
- [x] TASK-002 — Define and implement the model contract (done 2026-09-25)
- [x] TASK-003 — Preprocessing function (no model) (done 2026-09-25)
- [x] TASK-004 — Integrate the IQA (quality) model (done 2026-09-25)
- [x] TASK-005 — PHASE 1 CHECKPOINT (done 2026-09-25)
- [x] TASK-006 — Integrate vessel segmentation model (done 2026-09-25)
- [x] TASK-007 — Integrate lesion segmentation models (HE/EX/SE) (done 2026-09-25)
- [x] TASK-008 — Integrate MA (microaneurysm) detector (done 2026-09-25)
- [x] TASK-009 — PHASE 2 CHECKPOINT (done 2026-09-25)
- [x] TASK-010 — Integrate DR grading model (done 2026-09-25)
- [x] TASK-011 — Add calibration (temperature scaling) (done 2026-09-25)
- [x] TASK-012 — Decision fusion (referral decision) (done 2026-09-25)
- [x] TASK-013 — PHASE 3 CHECKPOINT (done 2026-09-25)
- [x] TASK-014 — Grad-CAM explainability (done 2026-09-25)
- [ ] TASK-015 — Final report assembly
- [ ] TASK-016 — PHASE 4 CHECKPOINT
- [ ] TASK-017 — Single-page website skeleton
- [ ] TASK-018 — End-to-end demo wiring with the full demo set
- [ ] TASK-019 — One-command launch hardening
- [ ] TASK-020 — Final demo hardening / dry run checkpoint
- [ ] TASK-021 — Simulink workflow simulation (separate track, no ordering dependency)

## BLOCKED TASKS

None

## NOTES & DECISIONS LOG

- Control files (HANDOFF.md, IMPLEMENTATION_SCHEMA.md, TASKS.md) generated from the SIH26038 PRD, the NETRA-DR Final Model Stack, and the NETRA-DR Master Build Prompt. No architecture component was dropped; Stage 10 (ensemble) and Stage 6 (NV) are marked OPTIONAL per the source documents' own framing, and Simulink (Stage 12) is kept as an independent, non-blocking track — see "KNOWN CONFLICTS / DECISIONS RECORDED" in HANDOFF.md for the full reasoning.
- TASK-001: Initialized Git repository and created complete repository skeleton with directory structure and placeholder .gitkeep / __init__.py files.
- TASK-002: Implemented pipeline/contract.py with zero external dependencies (standard library json used per prompt preference). Tested via unittest with 13/13 passing tests.
- TASK-003: Implemented deterministic Phase 1 preprocessing in pipeline/preprocessing.py (FOV crop, resize, CLAHE on L channel in LAB color space, normalization) configured via configs/preprocessing.json without hardcoded magic numbers. Validated with 16/16 tests passing, including visual inspection outputs in tests/fixtures/output/.
- TASK-004: Implemented pipeline/quality.py with run_quality_gate() loading contract via pipeline.contract, resolving ONNX path, running onnxruntime inference (contract-driven input_size/normalization), and returning quality_label/quality_score/preprocessed_image. All missing-artifact error paths verified (no fabricated results). onnxruntime>=1.17.0 added to requirements.txt. Integration tests correctly skipped pending MATLAB ONNX export.
- TASK-005: Populated data/demo/ with good_sample.jpg (real fundus, 664 KB) and reject_sample.jpg (synthetically degraded: underexposed x0.08 + heavy blur). Preprocessing confirmed end-to-end on both demo images (shape 512x512x3 float32, no error). Quality gate raises clear FileNotFoundError ("model artifact missing -- Phase 1 cannot run") on both images -- contract is working as intended; ONNX not yet exported from MATLAB. Checkpoint written to docs/checkpoints/phase1.md. Ready for next phase: NO (blocker: ONNX artifact delivery). reject_sample.jpg is synthetic; replace with a real DDR ungradable image when available.
- TASK-006: Implemented pipeline/structure.py with run_vessel_segmentation() — loads vessel U-Net via model contract (segmentation type), prepares NCHW input from contract input_size/normalization, runs ONNX inference, thresholds output into binary mask, draws green semi-transparent overlay. _draw_vessel_overlay, _prepare_segmentation_input, _threshold_to_binary_mask, and _run_onnx_inference are internal helpers designed for reuse by TASK-007/008. Missing-model error paths confirmed: 7/7 unit tests pass, 5 integration tests correctly skipped pending MATLAB ONNX export.
- TASK-007: Added run_lesion_segmentation() to pipeline/structure.py and _draw_lesion_overlay() helper. Reads mask_labels channel order from contract (never hardcoded); produces he_mask/ex_mask/se_mask as separate binary uint8 arrays. he_presence uses contract field 'he_presence_threshold' (default 50 px). ex_area is normalised pixel fraction [0,1], scale-invariant. No lesion subtypes (flame/dot-blot/deep) referenced in code. 9/9 unit tests pass, 9 integration tests correctly skipped pending MATLAB ONNX export.
- TASK-008: Added run_ma_detection() to pipeline/structure.py with two-stage hybrid approach: Stage A classical candidate extraction (top-hat or matched-filter, selected strictly from contract["candidate_extraction_method"]) followed by Stage B CNN FP-reducer (contract["fp_reducer_model_file"]). Parameters (disk_radius, sigma, threshold_factor, patch_size, ma_positive_class_index) all read from contract — no magic numbers. Internal helpers: _extract_candidates_tophat, _extract_candidates_matched_filter, _prepare_patch_input, _draw_ma_overlay. Tests: 19 passed / 5 skipped (integration skipped -- ma_detector ONNX artifact pending MATLAB export).
- TASK-009: Verified Phase 2 structure analysis modules (vessel segmentation, lesion segmentation, MA detection) end-to-end on demo images via checkpoint runner. Functions correctly raise explicit missing artifact errors without fabrication. Full Phase 2 test suite passes (35 passed, 19 skipped pending ONNX exports; 70 passed across full repo test suite). Written docs/checkpoints/phase2.md. Ready for next phase: NO (blocker: Phase 2 ONNX model deliveries).
- TASK-010: Implemented pipeline/grading.py with run_grading() loading contract (classifier type), preparing NCHW input from contract input_size/normalization, running ONNX inference, converting logits to softmax probabilities (or preserving normalized probabilities), returning severity_class (argmax), probabilities (5-length array), and backbone metadata. Tested with mocked ResNet-50 and backup EfficientNet-B0 contracts, missing artifact error paths, input validation, and signature verification. 11/11 tests pass in tests/test_grading.py (1 integration test skipped pending MATLAB export). Full suite passing (81 passed, 22 skipped).
- TASK-011: Added apply_calibration(probabilities, temperature=None, config_path="configs/calibration.json") to pipeline/grading.py. Created configs/calibration.json initialized honestly with temperature=1.0 and fitted=false. Implemented 9 unit tests in tests/test_calibration.py covering no-op scaling (T=1.0), flattening (T>1.0), sharpening (T<1.0), custom/default config loading, input validation, and probability sum invariants. All 9 tests pass (full suite: 90 passed, 22 skipped).
- TASK-012: Implemented pipeline/decision.py with run_decision_fusion() (and make_referral_decision alias) and configs/decision_rule.json. Evaluates referable_decision alongside grade_alone_decision with quality-tier-aware thresholds (0.50 for Good, 0.35 for Borderline for high sensitivity safety). Strictly rejects Reject-quality images from receiving automated decisions. Transparently reports fitted=False and fallback fusion status when logistic regression model is not yet trained offline. Tested with 10 unit tests in tests/test_decision.py (10/10 passed; 100 passed across project suite).
- TASK-013: Executed Phase 3 checkpoint verification on demo images and simulated representative severity profiles. Confirmed temperature calibration and quality-tier-aware decision fusion functioning end-to-end with side-by-side agreement/differ reporting. Missing grading model artifact handled cleanly without fabrication. All 30 Phase 3 unit tests pass (1 integration test skipped pending model export). Checkpoint report written to docs/checkpoints/phase3.md.
- TASK-014: Implemented pipeline/explain.py with run_gradcam() and generate_heatmap_overlay(). Strictly enforces 'model attention' labeling invariant (never clinical proof/evidence), maintains complete separation from Phase 2 lesion masks, supports contract-driven normalization and intermediate layer feature extraction with colormap blending. Tested via tests/test_explain.py with 7/7 passed unit and visual validation tests (107 passed across full project suite).

## LAST VALIDATED RESULT

TASK-014 validated: Tested run_gradcam() and generate_heatmap_overlay() via tests/test_explain.py with 7 passed tests verifying correct (H, W, 3) uint8 RGB output, alpha blending bounds, mandatory 'model attention' label enforcement, missing model error handling, and visual overlay generation on demo image (saved to tests/fixtures/output/demo_model_attention_overlay.jpg). Full test suite passing (107 passed, 22 skipped).

---

### Update procedure (for whichever Claude context completes a task)

1. Move the completed task from the checklist above into a new dated line under a "Completed" sub-list, e.g. `- [x] TASK-001 — Create repository structure (done <date>)`.
2. Update **CURRENT TASK** to the task that was previously **NEXT TASK**.
3. Update **NEXT TASK** to the task after that, per the Phase-to-Task Map in `IMPLEMENTATION_SCHEMA.md`.
4. Add one line to **NOTES & DECISIONS LOG** if any decision was made (e.g. "used EfficientNet-B0 fallback instead of ResNet-50 because...").
5. Update **LAST VALIDATED RESULT** with a one-line summary of what the task's Validation step confirmed.
6. Stop. Do not start the next task in the same session.
