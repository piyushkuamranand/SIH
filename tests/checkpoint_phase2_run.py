"""
Phase 2 checkpoint runner for TASK-009.
Runs vessel segmentation, lesion segmentation, and MA detection on demo images.
"""
from pathlib import Path
from pipeline.preprocessing import preprocess
from pipeline.structure import (
    run_vessel_segmentation,
    run_lesion_segmentation,
    run_ma_detection,
)
from pipeline.contract import ModelArtifactNotFoundError

DEMO_IMAGES = [
    ("good_sample.jpg", Path("data/demo/good_sample.jpg")),
    ("reject_sample.jpg", Path("data/demo/reject_sample.jpg")),
]

print("=== PHASE 2 STRUCTURE ANALYSIS EXECUTION ===")
for label, p in DEMO_IMAGES:
    print(f"\nImage: {label} ({p})")
    img = preprocess(str(p))
    print(f"  Preprocessed: shape={img.shape}, dtype={img.dtype}, min={img.min():.4f}, max={img.max():.4f}")

    # 1. Vessel Segmentation
    try:
        res_vessel = run_vessel_segmentation(img)
        print("  Vessel Segmentation: SUCCESS")
        print(f"    vessel_mask: shape={res_vessel['vessel_mask'].shape}, dtype={res_vessel['vessel_mask'].dtype}")
        print(f"    vessel_overlay: shape={res_vessel['vessel_overlay'].shape}, dtype={res_vessel['vessel_overlay'].dtype}")
    except (ModelArtifactNotFoundError, FileNotFoundError) as e:
        print(f"  Vessel Segmentation: {type(e).__name__} (expected -- ONNX artifact pending)")
        print(f"    {str(e)[:120]}")
    except Exception as e:
        print(f"  Vessel Segmentation: UNEXPECTED {type(e).__name__}: {e}")

    # 2. Lesion Segmentation
    try:
        res_lesion = run_lesion_segmentation(img)
        print("  Lesion Segmentation: SUCCESS")
        print(f"    he_mask: shape={res_lesion['he_mask'].shape}, he_presence={res_lesion['he_presence']}")
        print(f"    ex_mask: shape={res_lesion['ex_mask'].shape}, ex_area={res_lesion['ex_area']:.4f}")
        print(f"    se_mask: shape={res_lesion['se_mask'].shape}, se_presence={res_lesion['se_presence']}")
        print(f"    lesion_overlay: shape={res_lesion['lesion_overlay'].shape}")
    except (ModelArtifactNotFoundError, FileNotFoundError) as e:
        print(f"  Lesion Segmentation: {type(e).__name__} (expected -- ONNX artifact pending)")
        print(f"    {str(e)[:120]}")
    except Exception as e:
        print(f"  Lesion Segmentation: UNEXPECTED {type(e).__name__}: {e}")

    # 3. MA Detection
    try:
        res_ma = run_ma_detection(img)
        print("  MA Detection: SUCCESS")
        print(f"    ma_count: {res_ma['ma_count']}")
        print(f"    ma_locations: {len(res_ma.get('ma_locations', []))} candidates")
        print(f"    ma_overlay: shape={res_ma['ma_overlay'].shape}")
    except (ModelArtifactNotFoundError, FileNotFoundError) as e:
        print(f"  MA Detection: {type(e).__name__} (expected -- ONNX artifact pending)")
        print(f"    {str(e)[:120]}")
    except Exception as e:
        print(f"  MA Detection: UNEXPECTED {type(e).__name__}: {e}")
