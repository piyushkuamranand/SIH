import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("ISOLATED BACKEND AUDIT (STEP 3 & STEP 2)")
print("=" * 60)

demo_good = PROJECT_ROOT / "data" / "demo" / "good_sample.jpg"
print(f"Testing with demo good image: {demo_good} (exists: {demo_good.is_file()})")

# Stage 1: Preprocessing & Quality Gate
print("\n--- Testing Phase 1: Preprocessing & Quality Gate ---")
from pipeline.preprocessing import preprocess
from pipeline.quality import run_quality_gate

try:
    p1_res = run_quality_gate(str(demo_good))
    print("run_quality_gate output keys:", list(p1_res.keys()))
    print("quality_label:", p1_res.get("quality_label"))
    print("quality_score:", p1_res.get("quality_score"))
    prep_img = p1_res.get("preprocessed_image")
    if prep_img is None:
        prep_img = preprocess(str(demo_good))
    print(f"Preprocessed image shape: {prep_img.shape}, dtype: {prep_img.dtype}, min: {prep_img.min()}, max: {prep_img.max()}")
except Exception as e:
    import traceback
    print("Phase 1 FAILED:")
    traceback.print_exc()
    prep_img = preprocess(str(demo_good))

# Stage 2: Vessel Segmentation
print("\n--- Testing Phase 2: Vessel Segmentation ---")
try:
    from pipeline.structure import run_vessel_segmentation
    v_res = run_vessel_segmentation(prep_img)
    print("run_vessel_segmentation keys:", list(v_res.keys()))
    v_mask = v_res.get("vessel_mask")
    if v_mask is not None:
        print(f"vessel_mask shape: {v_mask.shape}, dtype: {v_mask.dtype}, unique: {np.unique(v_mask)}, sum: {np.sum(v_mask)}")
        is_degen = (np.sum(v_mask == 0) == 0 or np.sum(v_mask > 0) == 0)
        print(f"Degenerate mask: {is_degen}")
    else:
        print("vessel_mask is None!")
except Exception as e:
    import traceback
    print("run_vessel_segmentation FAILED:")
    traceback.print_exc()

# Stage 2: Lesion Segmentation & MA Detection
print("\n--- Testing Phase 2: Lesion Segmentation ---")
try:
    from pipeline.structure import run_lesion_segmentation, run_ma_detection
    l_res = run_lesion_segmentation(prep_img)
    print("run_lesion_segmentation keys:", list(l_res.keys()))
    for k in ["he_mask", "ex_mask", "se_mask", "ma_mask"]:
        arr = l_res.get(k)
        if arr is not None:
            print(f"  {k}: shape={arr.shape}, dtype={arr.dtype}, sum={np.sum(arr > 0)}")
        else:
            print(f"  {k}: is None")
    
    ma_res = run_ma_detection(prep_img)
    print("run_ma_detection keys:", list(ma_res.keys()))
    print("ma_count:", ma_res.get("ma_count"))
except Exception as e:
    import traceback
    print("run_lesion_segmentation / ma_detection FAILED:")
    traceback.print_exc()

# Stage 3: Grading & Calibration
print("\n--- Testing Phase 3: Grading & Calibration ---")
try:
    from pipeline.grading import run_grading, apply_calibration
    g_res = run_grading(prep_img)
    print("run_grading keys:", list(g_res.keys()))
    print("raw probabilities:", g_res.get("probabilities"))
    print("severity_class:", g_res.get("severity_class"))
    
    cal_res = apply_calibration(g_res.get("probabilities"))
    print("apply_calibration keys:", list(cal_res.keys()))
    print("calibrated_probabilities:", cal_res.get("calibrated_probabilities"))
    print("confidence:", cal_res.get("confidence"))
except Exception as e:
    import traceback
    print("run_grading / apply_calibration FAILED:")
    traceback.print_exc()

# Stage 3: Decision Fusion
print("\n--- Testing Phase 3: Decision Fusion ---")
try:
    from pipeline.decision import run_decision_fusion
    from pipeline.orchestrator import _run_decision_fusion, _run_lesion_detection, NetraConfig
    cfg = NetraConfig()
    s2_les = _run_lesion_detection(prep_img, cfg)
    
    # Test pipeline.decision.run_decision_fusion
    dec_direct = run_decision_fusion(
        calibrated_probabilities=cal_res.get("calibrated_probabilities"),
        ma_count=int(s2_les.get("ma_count", 0)),
        he_presence=bool(s2_les.get("he_presence", False)),
        ex_area=float(s2_les.get("ex_area", 0.0)),
        quality_label="Good"
    )
    print("pipeline.decision.run_decision_fusion output:")
    print("  referable_decision:", dec_direct.get("referable_decision"))
    print("  grade_alone_decision:", dec_direct.get("grade_alone_decision"))
    print("  threshold_applied:", dec_direct.get("threshold_applied"))
    print("  reason:", dec_direct.get("reason"))
    print("  fusion_status:", dec_direct.get("fusion_status"))

    # Test pipeline.orchestrator._run_decision_fusion
    dec_orch = _run_decision_fusion(
        calibrated_probabilities=cal_res.get("calibrated_probabilities"),
        s2_lesion=s2_les,
        quality_tier="Good",
        config=cfg
    )
    print("pipeline.orchestrator._run_decision_fusion output:")
    print("  referable_decision:", dec_orch.get("referable_decision"))
    print("  grade_alone_decision:", dec_orch.get("grade_alone_decision"))
    print("  threshold_applied:", dec_orch.get("threshold_applied"))
    print("  reason:", dec_orch.get("reason"))
    print("  fusion_status:", dec_orch.get("fusion_status"))
except Exception as e:
    import traceback
    print("run_decision_fusion FAILED:")
    traceback.print_exc()

# Stage 4: Explainability (Grad-CAM) & Consistency
print("\n--- Testing Phase 4: Grad-CAM Explainability & Consistency ---")
try:
    from pipeline.explain import run_gradcam, generate_heatmap_overlay
    from pipeline.orchestrator import _run_explainability, _check_consistency_flag
    
    cam_res = run_gradcam(prep_img, severity_class=int(g_res.get("severity_class", 0)))
    print("run_gradcam keys:", list(cam_res.keys()))
    heatmap = cam_res.get("heatmap_raw")
    if heatmap is not None:
        print(f"heatmap_raw shape: {heatmap.shape}, dtype: {heatmap.dtype}, min: {heatmap.min()}, max: {heatmap.max()}")
    overlay = cam_res.get("heatmap_overlay")
    if overlay is not None:
        print(f"heatmap_overlay shape: {overlay.shape}, dtype: {overlay.dtype}")
    
    s8 = _run_explainability(prep_img, int(g_res.get("severity_class", 0)), s2_les, cfg)
    print("_run_explainability keys:", list(s8.keys()))
    print("iou_vs_he:", s8.get("iou_vs_he"))
    print("iou_vs_ex:", s8.get("iou_vs_ex"))
    
    s10 = _check_consistency_flag(s8, cfg)
    print("_check_consistency_flag keys:", list(s10.keys()))
    print("priority_human_review:", s10.get("priority_human_review"))
    print("consistency_flag_reason:", s10.get("consistency_flag_reason"))
except Exception as e:
    import traceback
    print("Phase 4 FAILED:")
    traceback.print_exc()

