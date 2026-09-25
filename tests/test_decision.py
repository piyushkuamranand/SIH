"""
tests/test_decision.py — Tests for Phase 3 Decision Fusion & Referral Logic

Validates:
1. High-grade input returns "REFER" for both referable_decision and grade_alone_decision.
2. Grade-0 (No DR) input returns "NO REFER" for both decisions.
3. Quality-tier-aware thresholds: Borderline-quality threshold (0.35) is measurably stricter
   than Good-quality threshold (0.50).
4. Side-by-side presence: Both grade_alone_decision and referable_decision are present in every result.
5. Fallback state: Honestly reports fitted=False and fallback fusion_status when no trained model exists.
6. Quality safety gate: Reject-quality images raise ValueError and are never processed.
7. Input validation & robust error handling.
8. Compatibility with dictionary output from apply_calibration().
9. Mocked fitted logistic regression model path.
"""

import json
import pytest
import numpy as np

from pipeline.decision import run_decision_fusion, make_referral_decision


def test_grade_0_no_refer():
    """Grade 0 (No DR) input produces NO REFER for both decisions."""
    # [Grade 0, Grade 1, Grade 2, Grade 3, Grade 4]
    grade_0_probs = [0.92, 0.06, 0.01, 0.005, 0.005]
    result = run_decision_fusion(
        calibrated_probabilities=grade_0_probs,
        ma_count=0,
        he_presence=False,
        ex_area=0.0,
        quality_label="Good",
    )

    assert result["referable_decision"] == "NO REFER"
    assert result["grade_alone_decision"] == "NO REFER"
    assert result["is_referable"] is False
    assert result["grade_alone_referable"] is False
    assert result["predicted_grade"] == 0
    assert result["referable_probability"] < 0.10
    assert result["quality_tier"] == "Good"
    assert result["fitted"] is False
    assert "fallback" in result["fusion_status"]


def test_high_grade_refer():
    """High-grade input (Severe / Proliferative DR) produces REFER for both decisions."""
    # Grade 3 (Severe NPDR)
    grade_3_probs = [0.01, 0.04, 0.15, 0.70, 0.10]
    result = run_decision_fusion(
        calibrated_probabilities=grade_3_probs,
        ma_count=18,
        he_presence=True,
        ex_area=0.0125,
        quality_label="Good",
    )

    assert result["referable_decision"] == "REFER"
    assert result["grade_alone_decision"] == "REFER"
    assert result["is_referable"] is True
    assert result["grade_alone_referable"] is True
    assert result["predicted_grade"] == 3
    assert result["referable_probability"] == pytest.approx(0.95, rel=1e-3)
    assert result["evidence"]["ma_count"] == 18
    assert result["evidence"]["he_presence"] is True
    assert result["evidence"]["ex_area"] == pytest.approx(0.0125, rel=1e-3)


def test_borderline_quality_stricter_threshold():
    """
    Validate that Borderline-quality threshold (0.35) is measurably stricter than
    Good-quality threshold (0.50).

    A constructed case with referable probability = 0.40 (and argmax Grade 1):
    - On Good quality (threshold 0.50): NO REFER
    - On Borderline quality (threshold 0.35): REFER (higher sensitivity safety threshold)
    """
    # Referable probability = 0.15 + 0.15 + 0.10 = 0.40. Argmax is Grade 1 (0.45).
    borderline_probs = [0.15, 0.45, 0.15, 0.15, 0.10]

    # 1. Good quality evaluation
    res_good = run_decision_fusion(
        calibrated_probabilities=borderline_probs,
        ma_count=3,
        he_presence=False,
        ex_area=0.0,
        quality_label="Good",
    )
    assert res_good["threshold_applied"] == 0.50
    assert res_good["grade_alone_decision"] == "NO REFER"
    assert res_good["referable_decision"] == "NO REFER"
    assert res_good["is_referable"] is False

    # 2. Borderline quality evaluation with identical probabilities
    res_borderline = run_decision_fusion(
        calibrated_probabilities=borderline_probs,
        ma_count=3,
        he_presence=False,
        ex_area=0.0,
        quality_label="Borderline",
    )
    assert res_borderline["threshold_applied"] == 0.35
    assert res_borderline["grade_alone_decision"] == "NO REFER"  # Naive threshold still NO REFER
    assert res_borderline["referable_decision"] == "REFER"       # Quality-aware stricter threshold triggers REFER
    assert res_borderline["is_referable"] is True


def test_side_by_side_reporting_always_present():
    """Confirm both grade_alone_decision and referable_decision are present in every result."""
    probs_list = [
        [0.8, 0.1, 0.05, 0.03, 0.02],
        [0.1, 0.7, 0.1, 0.05, 0.05],
        [0.05, 0.1, 0.6, 0.15, 0.1],
    ]
    for p in probs_list:
        for q in ["Good", "Borderline"]:
            res = run_decision_fusion(p, quality_label=q)
            assert "grade_alone_decision" in res
            assert "referable_decision" in res
            assert "is_referable" in res
            assert "grade_alone_referable" in res
            assert res["grade_alone_decision"] in ("REFER", "NO REFER")
            assert res["referable_decision"] in ("REFER", "NO REFER")


def test_reject_quality_raises_error():
    """Reject-quality images must never receive an automated decision."""
    grade_0_probs = [0.9, 0.05, 0.03, 0.01, 0.01]
    with pytest.raises(ValueError, match="Reject-quality image cannot receive an automated referral decision"):
        run_decision_fusion(grade_0_probs, quality_label="Reject")

    with pytest.raises(ValueError, match="Reject-quality image cannot receive an automated referral decision"):
        run_decision_fusion(grade_0_probs, quality_label="reject")


def test_invalid_quality_label_raises_error():
    """Invalid quality label raises ValueError."""
    grade_0_probs = [0.9, 0.05, 0.03, 0.01, 0.01]
    with pytest.raises(ValueError, match="Invalid quality_label"):
        run_decision_fusion(grade_0_probs, quality_label="UnknownQuality")


def test_dict_input_from_apply_calibration():
    """Accepts dict input directly from apply_calibration()."""
    calibration_output = {
        "calibrated_probabilities": [0.02, 0.08, 0.60, 0.20, 0.10],
        "confidence": 0.60,
        "temperature": 1.0,
        "fitted": False,
    }
    result = run_decision_fusion(
        calibrated_probabilities=calibration_output,
        ma_count=8,
        he_presence=True,
        quality_label="Good",
    )
    assert result["referable_decision"] == "REFER"
    assert result["predicted_grade"] == 2
    assert result["referable_probability"] == pytest.approx(0.90, rel=1e-3)


def test_input_validation_errors():
    """Test validation errors for invalid probability inputs."""
    # Wrong length
    with pytest.raises(ValueError, match="must be a 5-element array"):
        run_decision_fusion([0.5, 0.5])

    # Negative probabilities
    with pytest.raises(ValueError, match="valid non-negative numbers"):
        run_decision_fusion([-0.1, 0.5, 0.2, 0.2, 0.2])

    # Sum zero
    with pytest.raises(ValueError, match="Sum of probabilities must be strictly positive"):
        run_decision_fusion([0.0, 0.0, 0.0, 0.0, 0.0])


def test_alias_function_identical():
    """make_referral_decision is an alias to run_decision_fusion."""
    probs = [0.9, 0.05, 0.03, 0.01, 0.01]
    r1 = run_decision_fusion(probs)
    r2 = make_referral_decision(probs)
    assert r1 == r2


def test_fitted_fusion_model_path(tmp_path):
    """Test that when a fitted logistic regression model is present, fitted=True and fused logit are computed."""
    model_dir = tmp_path / "models" / "decision_fusion"
    model_dir.mkdir(parents=True)
    metadata = {
        "fitted": True,
        "model_name": "decision_fusion_logistic_regression",
        "model_version": "1.0.0",
        "threshold": 0.50,
        "intercept": -1.5,
        "weights": [3.0, 0.1, 0.8, 2.5, 0.5],  # [P(Grade>=2), ma_count, he_presence, ex_area, is_borderline]
    }
    with open(model_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    # Moderate probabilities with heavy lesion evidence
    probs = [0.2, 0.5, 0.2, 0.05, 0.05]  # P(Grade>=2) = 0.30
    result = run_decision_fusion(
        calibrated_probabilities=probs,
        ma_count=15,
        he_presence=True,
        ex_area=0.02,
        quality_label="Borderline",
        model_dir=str(model_dir),
    )

    assert result["fitted"] is True
    assert result["fusion_status"] == "fitted_logistic_regression"
    assert "Fitted logistic regression decision" in result["reason"]
    assert result["referable_decision"] == "REFER"
