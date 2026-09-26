"""
tests/test_report.py — NETRA-DR TASK-015: Final Report Assembly Tests

Validates run_full_pipeline() for:
1. Full-pipeline case: Good-quality image — all four phase keys populated.
2. Stopped-at-Phase-1 case: Reject quality — stopped_at_phase1=True, phases 2-4 absent/null.
3. Stopped-at-Phase-1 case due to missing model: Phase 1 raises clear error, pipeline stops.
4. Phase labels are correct (label == "model attention" in phase4).
5. Image-not-found raises FileNotFoundError before any phase runs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.report import run_full_pipeline

# ── Shared fixtures ───────────────────────────────────────────────────────────

DEMO_IMAGE = ROOT / "data" / "demo" / "good_sample.jpg"
DUMMY_IMAGE = ROOT / "data" / "demo" / "reject_sample.jpg"


def _fake_preprocessed() -> np.ndarray:
    """Return a small synthetic preprocessed image (HWC float32)."""
    return np.random.rand(64, 64, 3).astype(np.float32)


def _make_quality_result(label: str) -> dict:
    return {
        "quality_label": label,
        "quality_score": 0.9 if label == "Good" else 0.1,
        "preprocessed_image": _fake_preprocessed(),
    }


def _make_vessel_result() -> dict:
    mask = np.zeros((64, 64), dtype=np.uint8)
    overlay = np.zeros((64, 64, 3), dtype=np.uint8)
    return {"vessel_mask": mask, "vessel_overlay": overlay}


def _make_lesion_result() -> dict:
    mask = np.zeros((64, 64), dtype=np.uint8)
    overlay = np.zeros((64, 64, 3), dtype=np.uint8)
    return {
        "lesion_overlay": overlay,
        "he_mask": mask,
        "ex_mask": mask,
        "se_mask": mask,
        "he_presence": True,
        "ex_area": 0.002,
    }


def _make_ma_result() -> dict:
    return {"ma_count": 3, "ma_overlay": np.zeros((64, 64, 3), dtype=np.uint8)}


def _make_grading_result() -> dict:
    probs = [0.7, 0.1, 0.1, 0.05, 0.05]
    return {
        "severity_class": 0,
        "probabilities": probs,
        "model_name": "test_grading_model",
        "model_version": "1.0",
        "class_labels": ["0", "1", "2", "3", "4"],
        "metadata": {},
    }


def _make_calibration_result() -> dict:
    probs = [0.7, 0.1, 0.1, 0.05, 0.05]
    return {
        "calibrated_probabilities": probs,
        "confidence": 0.7,
        "temperature": 1.0,
        "fitted": False,
    }


def _make_decision_result() -> dict:
    return {
        "referable_decision": "NO REFER",
        "grade_alone_decision": "NO REFER",
        "is_referable": False,
        "grade_alone_referable": False,
        "predicted_grade": 0,
        "calibrated_probabilities": [0.7, 0.1, 0.1, 0.05, 0.05],
        "referable_probability": 0.2,
        "quality_tier": "Good",
        "threshold_applied": 0.5,
        "evidence": {"ma_count": 3, "he_presence": True, "ex_area": 0.002},
        "fusion_status": "using grade-alone fallback, fusion model not yet trained",
        "fitted": False,
        "reason": "No referral needed",
    }


def _make_gradcam_result() -> dict:
    return {
        "heatmap_overlay": np.zeros((64, 64, 3), dtype=np.uint8),
        "heatmap_raw": np.zeros((8, 8), dtype=np.float32),
        "label": "model attention",
        "severity_class": 0,
        "model_name": "test_grading_model",
        "model_version": "1.0",
        "alpha": 0.5,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Image not found raises FileNotFoundError before any phase
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_image_raises_before_pipeline():
    """Non-existent image_path must raise FileNotFoundError immediately."""
    with pytest.raises(FileNotFoundError, match="Input image not found"):
        run_full_pipeline("/nonexistent/fundus.jpg")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Reject quality — stopped_at_phase1=True, phases 2-4 are empty
# ─────────────────────────────────────────────────────────────────────────────

def test_reject_quality_stops_pipeline(tmp_path):
    """A Reject-quality result sets stopped_at_phase1=True and keeps phases 2-4 null."""
    # Create a dummy image file so path check passes
    img_file = tmp_path / "test_reject.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")  # minimal JPEG header

    with patch("pipeline.report.run_quality_gate", return_value=_make_quality_result("Reject")):
        result = run_full_pipeline(str(img_file))

    assert result["stopped_at_phase1"] is True, "stopped_at_phase1 must be True for Reject"

    # Phase 1 should be populated
    assert result["phase1"] is not None
    assert result["phase1"]["quality_label"] == "Reject"

    # Phases 2-4 should be empty/null (not absent, but all values None/falsy)
    for phase in ("phase2", "phase3", "phase4"):
        assert result[phase] is not None, f"{phase} key must be present"

    # Phase 2 values should be None or default (not missing keys)
    assert "vessel_mask" in result["phase2"]
    assert result["phase2"]["vessel_mask"] is None
    assert result["phase2"]["ma_count"] == 0

    # Phase 3 should have None values
    assert result["phase3"]["severity_class"] is None
    assert result["phase3"]["referable_decision"] is None

    # Phase 4 heatmap should be None
    assert result["phase4"]["heatmap_overlay"] is None
    # label is always "model attention" even when empty
    assert result["phase4"]["label"] == "model attention"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: Good quality — all four phase keys populated
# ─────────────────────────────────────────────────────────────────────────────

def test_good_quality_full_pipeline(tmp_path):
    """Good-quality image must produce populated results for all four phases."""
    img_file = tmp_path / "test_good.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")  # minimal JPEG header

    with (
        patch("pipeline.report.run_quality_gate", return_value=_make_quality_result("Good")),
        patch("pipeline.report.run_vessel_segmentation", return_value=_make_vessel_result()),
        patch("pipeline.report.run_lesion_segmentation", return_value=_make_lesion_result()),
        patch("pipeline.report.run_ma_detection", return_value=_make_ma_result()),
        patch("pipeline.report.run_grading", return_value=_make_grading_result()),
        patch("pipeline.report.apply_calibration", return_value=_make_calibration_result()),
        patch("pipeline.report.run_decision_fusion", return_value=_make_decision_result()),
        patch("pipeline.report.run_gradcam", return_value=_make_gradcam_result()),
    ):
        result = run_full_pipeline(str(img_file))

    assert result["stopped_at_phase1"] is False

    # Phase 1
    assert result["phase1"]["quality_label"] == "Good"
    assert result["phase1"]["quality_score"] == pytest.approx(0.9)
    assert isinstance(result["phase1"]["preprocessed_image"], np.ndarray)

    # Phase 2
    assert isinstance(result["phase2"]["vessel_mask"], np.ndarray)
    assert isinstance(result["phase2"]["vessel_overlay"], np.ndarray)
    assert result["phase2"]["ma_count"] == 3
    assert result["phase2"]["he_presence"] is True
    assert result["phase2"]["ex_area"] == pytest.approx(0.002)

    # Phase 3
    assert result["phase3"]["severity_class"] == 0
    assert isinstance(result["phase3"]["probabilities"], list)
    assert isinstance(result["phase3"]["calibrated_probabilities"], list)
    assert result["phase3"]["confidence"] == pytest.approx(0.7)
    assert result["phase3"]["referable_decision"] in ("REFER", "NO REFER")
    assert result["phase3"]["grade_alone_decision"] in ("REFER", "NO REFER")
    assert "fusion_status" in result["phase3"]
    assert "fitted" in result["phase3"]

    # Phase 4
    assert isinstance(result["phase4"]["heatmap_overlay"], np.ndarray)
    assert isinstance(result["phase4"]["heatmap_raw"], np.ndarray)
    # Mandatory label invariant
    assert result["phase4"]["label"] == "model attention", (
        "Phase 4 heatmap label must always be 'model attention'"
    )

    # No error
    assert result["error"] is None


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: Phase 1 model missing — stops with clear error, doesn't fabricate
# ─────────────────────────────────────────────────────────────────────────────

def test_phase1_model_missing_stops_pipeline(tmp_path):
    """If Phase 1 raises an artifact error, pipeline stops and error is surfaced."""
    img_file = tmp_path / "test_img.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")

    from pipeline.contract import ModelArtifactNotFoundError

    with patch(
        "pipeline.report.run_quality_gate",
        side_effect=ModelArtifactNotFoundError("model artifact missing — Phase 1 cannot run"),
    ):
        result = run_full_pipeline(str(img_file))

    assert result["stopped_at_phase1"] is True
    assert result["error"] is not None
    assert "Phase 1" in result["error"]
    # Phase 1 result is present but with None values
    assert result["phase1"]["quality_label"] is None
    assert result["phase3"]["severity_class"] is None
    assert result["phase4"]["heatmap_overlay"] is None


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: Phase 2/3/4 model missing — pipeline continues with error logged
# ─────────────────────────────────────────────────────────────────────────────

def test_phase2_model_missing_continues(tmp_path):
    """Phase 2 model missing should log an error but not crash the whole pipeline."""
    img_file = tmp_path / "test_img.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")

    from pipeline.contract import ModelArtifactNotFoundError

    with (
        patch("pipeline.report.run_quality_gate", return_value=_make_quality_result("Good")),
        patch(
            "pipeline.report.run_vessel_segmentation",
            side_effect=ModelArtifactNotFoundError("vessel artifact missing"),
        ),
        patch(
            "pipeline.report.run_lesion_segmentation",
            side_effect=ModelArtifactNotFoundError("lesion artifact missing"),
        ),
        patch(
            "pipeline.report.run_ma_detection",
            side_effect=ModelArtifactNotFoundError("ma artifact missing"),
        ),
        patch("pipeline.report.run_grading", return_value=_make_grading_result()),
        patch("pipeline.report.apply_calibration", return_value=_make_calibration_result()),
        patch("pipeline.report.run_decision_fusion", return_value=_make_decision_result()),
        patch("pipeline.report.run_gradcam", return_value=_make_gradcam_result()),
    ):
        result = run_full_pipeline(str(img_file))

    assert result["stopped_at_phase1"] is False
    # Phase 2 values should all be None/default (no fabricated results)
    assert result["phase2"]["vessel_mask"] is None
    assert result["phase2"]["ma_count"] == 0
    # Phase 3 should still be populated (uses default Phase 2 values of 0/False/0.0)
    assert result["phase3"]["severity_class"] == 0
    # Error string should mention Phase 2
    assert result["error"] is not None
    assert "Phase 2" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: Borderline quality — pipeline does NOT stop at Phase 1
# ─────────────────────────────────────────────────────────────────────────────

def test_borderline_quality_continues(tmp_path):
    """Borderline-quality images must proceed through the pipeline (not stopped)."""
    img_file = tmp_path / "test_img.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")

    with (
        patch("pipeline.report.run_quality_gate", return_value=_make_quality_result("Borderline")),
        patch("pipeline.report.run_vessel_segmentation", return_value=_make_vessel_result()),
        patch("pipeline.report.run_lesion_segmentation", return_value=_make_lesion_result()),
        patch("pipeline.report.run_ma_detection", return_value=_make_ma_result()),
        patch("pipeline.report.run_grading", return_value=_make_grading_result()),
        patch("pipeline.report.apply_calibration", return_value=_make_calibration_result()),
        patch("pipeline.report.run_decision_fusion", return_value=_make_decision_result()),
        patch("pipeline.report.run_gradcam", return_value=_make_gradcam_result()),
    ):
        result = run_full_pipeline(str(img_file))

    assert result["stopped_at_phase1"] is False
    assert result["phase3"]["severity_class"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: Result dict always contains all expected top-level keys
# ─────────────────────────────────────────────────────────────────────────────

def test_result_always_has_all_keys(tmp_path):
    """run_full_pipeline() must always return the full key set."""
    img_file = tmp_path / "test_img.jpg"
    img_file.write_bytes(b"\xff\xd8\xff")

    with patch("pipeline.report.run_quality_gate", return_value=_make_quality_result("Reject")):
        result = run_full_pipeline(str(img_file))

    expected_keys = {"phase1", "phase2", "phase3", "phase4", "stopped_at_phase1", "error", "timings"}
    assert set(result.keys()) == expected_keys

    # Phase 4 must always have "label" == "model attention"
    assert result["phase4"]["label"] == "model attention"
