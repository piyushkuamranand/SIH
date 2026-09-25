"""
Phase 1 checkpoint runner for TASK-005.
Runs preprocessing and quality gate on both demo images, prints results.
"""
from pathlib import Path
from pipeline.preprocessing import preprocess
from pipeline.quality import run_quality_gate
from pipeline.contract import ModelArtifactNotFoundError

DEMO_IMAGES = [
    ("good_sample.jpg", Path("data/demo/good_sample.jpg")),
    ("reject_sample.jpg", Path("data/demo/reject_sample.jpg")),
]

print("=== PREPROCESSING RESULTS ===")
for label, p in DEMO_IMAGES:
    arr = preprocess(str(p))
    print(
        f"  {label}: shape={arr.shape}, dtype={arr.dtype}, "
        f"min={arr.min():.4f}, max={arr.max():.4f}"
    )

print()
print("=== QUALITY GATE ATTEMPT ===")
for label, p in DEMO_IMAGES:
    try:
        result = run_quality_gate(str(p))
        ql = result["quality_label"]
        qs = result["quality_score"]
        print(f"  {label}: quality_label={ql}, quality_score={qs:.4f}")
    except (ModelArtifactNotFoundError, FileNotFoundError) as e:
        msg = str(e)
        print(f"  {label}: {type(e).__name__} (expected — ONNX artifact pending)")
        print(f"           {msg[:140]}")
    except Exception as e:
        print(f"  {label}: UNEXPECTED {type(e).__name__}: {e}")
