"""
tests/test_explain.py — Unit and Validation Tests for Phase 4 Grad-CAM Explainability

Validates:
1. generate_heatmap_overlay() produces valid (H, W, 3) uint8 RGB images with proper blending.
2. Alpha blending bounds (alpha=0.0 vs alpha=1.0 vs alpha=0.5).
3. Missing grading model artifact raises ModelArtifactNotFoundError / FileNotFoundError.
4. Input validation for severity_class range [0, 4] and image format.
5. Strict labeling invariant: label must be 'model attention' (never 'clinical proof' or 'evidence').
6. Mocked contract execution produces complete explainability output.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from pipeline.contract import ModelArtifactNotFoundError
from pipeline.explain import generate_heatmap_overlay, run_gradcam


def test_generate_heatmap_overlay_basic():
    """Verify generate_heatmap_overlay creates valid (H, W, 3) uint8 image."""
    base_img = np.zeros((512, 512, 3), dtype=np.uint8)
    base_img[:, :] = [100, 50, 30]  # Dark background
    
    # Gaussian blob in center as activation heatmap
    y, x = np.ogrid[:14, :14]
    dist = (x - 7)**2 + (y - 7)**2
    heatmap = np.exp(-dist / 10.0).astype(np.float32)

    overlay = generate_heatmap_overlay(base_img, heatmap, alpha=0.5)

    assert isinstance(overlay, np.ndarray)
    assert overlay.shape == (512, 512, 3)
    assert overlay.dtype == np.uint8
    assert overlay.min() >= 0
    assert overlay.max() <= 255


def test_generate_heatmap_overlay_alpha_extremes():
    """Verify alpha=0.0 gives exact base image and alpha=1.0 gives colored heatmap."""
    base_img = np.full((100, 100, 3), 150, dtype=np.uint8)
    heatmap = np.ones((10, 10), dtype=np.float32)

    # Alpha = 0.0 -> identical to base image
    overlay_0 = generate_heatmap_overlay(base_img, heatmap, alpha=0.0)
    np.testing.assert_array_equal(overlay_0, base_img)

    # Alpha = 1.0 -> different from base image (pure colormap)
    overlay_1 = generate_heatmap_overlay(base_img, heatmap, alpha=1.0)
    assert not np.array_equal(overlay_1, base_img)


def test_missing_model_raises_error():
    """Missing model artifact raises ModelArtifactNotFoundError or FileNotFoundError."""
    dummy_img = np.zeros((512, 512, 3), dtype=np.uint8)
    with pytest.raises((ModelArtifactNotFoundError, FileNotFoundError)):
        run_gradcam(dummy_img, severity_class=2, model_dir="non_existent_model_dir")


def test_invalid_severity_class_raises_value_error():
    """severity_class outside [0, 4] raises ValueError."""
    dummy_img = np.zeros((512, 512, 3), dtype=np.uint8)
    for invalid_class in [-1, 5, 10, "high"]:
        with pytest.raises(ValueError, match="severity_class must be an integer in range"):
            run_gradcam(dummy_img, severity_class=invalid_class)


def test_invalid_image_dimension_raises_value_error():
    """Invalid 2D or 4D image raises ValueError."""
    heatmap = np.ones((10, 10), dtype=np.float32)
    
    # 2D image
    with pytest.raises(ValueError, match="Base image must be 3D"):
        generate_heatmap_overlay(np.zeros((100, 100), dtype=np.uint8), heatmap)
    
    # 4-channel image
    with pytest.raises(ValueError, match="Base image must be 3D"):
        generate_heatmap_overlay(np.zeros((100, 100, 4), dtype=np.uint8), heatmap)


def test_label_strictly_model_attention():
    """Verify output label is strictly 'model attention' and never 'clinical proof' or 'evidence'."""
    # Test on mocked contract environment
    contract = {
        "model_name": "resnet50_dr_grader",
        "model_version": "1.0.0",
        "model_type": "classifier",
        "input_size": [512, 512],
        "channels": 3,
        "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "model_file": "grading_model.onnx",
        "framework": "onnx",
        "training_dataset": "APTOS2019+DDR",
        "preprocessing": "FOV-crop -> resize(512,512) -> CLAHE",
        "eval_metrics": {"QWK": 0.89},
        "class_labels": ["No DR", "Mild", "Moderate", "Severe", "PDR"],
        "output_format": "softmax_probs",
        "threshold": 0.5,
    }

    dummy_img = np.ones((512, 512, 3), dtype=np.uint8) * 128

    with patch("pipeline.explain.load_contract", return_value=contract), \
         patch("pipeline.explain.resolve_model_path", return_value="fake_model.onnx"), \
         patch("pathlib.Path.is_file", return_value=True), \
         patch("pipeline.explain._compute_gradcam_from_onnx", return_value=np.ones((14, 14), dtype=np.float32)):

        res = run_gradcam(dummy_img, severity_class=3)

        assert "label" in res
        assert res["label"] == "model attention"
        assert "evidence" not in res["label"].lower()
        assert "proof" not in res["label"].lower()
        assert "heatmap_overlay" in res
        assert "heatmap_raw" in res
        assert res["severity_class"] == 3
        assert res["model_name"] == "resnet50_dr_grader"
        assert res["heatmap_overlay"].shape == (512, 512, 3)
        assert res["heatmap_overlay"].dtype == np.uint8


def test_demo_image_heatmap_overlay_generation():
    """Verify heatmap overlay generation on real demo image and check visual output."""
    demo_path = Path("data/demo/good_sample.jpg")
    if not demo_path.is_file():
        pytest.skip("good_sample.jpg not found in data/demo/")

    # Generate synthetic attention heatmap concentrated around macula / vascular arcades
    h_map = np.zeros((32, 32), dtype=np.float32)
    # Focal activations
    h_map[12:16, 14:18] = 0.8
    h_map[20:24, 18:22] = 1.0
    h_map = cv2.GaussianBlur(h_map, (5, 5), 1.0)

    overlay = generate_heatmap_overlay(str(demo_path), h_map, alpha=0.45)
    assert overlay.shape == (1024, 1024, 3) or overlay.ndim == 3
    assert overlay.dtype == np.uint8

    out_dir = Path("tests/fixtures/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "demo_model_attention_overlay.jpg"), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    assert (out_dir / "demo_model_attention_overlay.jpg").is_file()

