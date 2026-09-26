"""
tests/test_calibration.py — Tests for Phase 3 Calibration (Temperature Scaling)

Tests cover:
1. Sanity check (T=1.0): Calibrated probabilities equal raw input (no-op case).
2. Softening check (T > 1.0): Distribution flattens, max probability / confidence decreases.
3. Sharpening check (T < 1.0): Distribution sharpens, max probability / confidence increases.
4. Default behavior: Reads configs/calibration.json and reflects fitted=false honestly.
5. Custom config reading: Correctly loads fitted temperature from config.
6. Validation errors: Rejects temperature <= 0, empty probabilities, and negative probabilities.
7. Probabilities sum to 1.0 after temperature scaling across multiple distributions.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from pipeline.grading import apply_calibration


def test_calibration_noop_t1():
    """With temperature=1.0, calibrated output equals raw input (no-op sanity check)."""
    raw_probs = [0.05, 0.70, 0.15, 0.08, 0.02]
    result = apply_calibration(raw_probs, temperature=1.0)

    assert "calibrated_probabilities" in result
    assert "confidence" in result
    assert "temperature" in result
    assert "fitted" in result

    assert len(result["calibrated_probabilities"]) == 5
    assert np.allclose(result["calibrated_probabilities"], raw_probs, atol=1e-5)
    assert np.isclose(result["confidence"], 0.70, atol=1e-5)
    assert np.isclose(result["temperature"], 1.0)


def test_calibration_flattening_t_greater_than_1():
    """With temperature > 1.0, distribution flattens and max probability decreases."""
    raw_probs = [0.02, 0.80, 0.10, 0.05, 0.03]
    result = apply_calibration(raw_probs, temperature=1.5)

    calibrated = result["calibrated_probabilities"]
    # Max probability (class 1) must decrease
    assert result["confidence"] < 0.80
    assert calibrated[1] < 0.80
    # Lower probability classes should relatively increase
    assert calibrated[0] > raw_probs[0]
    # Sum must still be 1.0
    assert np.isclose(np.sum(calibrated), 1.0, atol=1e-5)


def test_calibration_sharpening_t_less_than_1():
    """With temperature < 1.0, distribution sharpens and max probability increases."""
    raw_probs = [0.05, 0.70, 0.15, 0.08, 0.02]
    result = apply_calibration(raw_probs, temperature=0.7)

    assert result["confidence"] > 0.70
    assert result["calibrated_probabilities"][1] > 0.70
    assert np.isclose(np.sum(result["calibrated_probabilities"]), 1.0, atol=1e-5)


def test_calibration_default_config_when_no_file_exists(tmp_path):
    """apply_calibration() falls back to temperature=1.0 / fitted=False (no-op) when the
    given config path does not exist — this is the code's default behavior, tested in
    isolation from whatever configs/calibration.json currently holds in the repo (that
    file legitimately becomes fitted=True once a real model has been trained and
    calibrated — see test_calibration_config_file_integrity below)."""
    raw_probs = [0.1, 0.6, 0.2, 0.05, 0.05]
    missing_path = tmp_path / "does_not_exist.json"
    result = apply_calibration(raw_probs, config_path=missing_path)

    assert np.isclose(result["temperature"], 1.0)
    assert result["fitted"] is False
    assert np.allclose(result["calibrated_probabilities"], raw_probs, atol=1e-5)
    assert np.isclose(result["confidence"], 0.6, atol=1e-5)


def test_calibration_custom_fitted_config(tmp_path):
    """Reading from a config file with a fitted temperature."""
    cfg_file = tmp_path / "custom_calibration.json"
    cfg_data = {
        "temperature": 1.35,
        "fitted": True,
        "method": "temperature_scaling",
        "dataset": "eyepacs_val_fold",
    }
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg_data, f)

    raw_probs = [0.05, 0.75, 0.10, 0.05, 0.05]
    result = apply_calibration(raw_probs, config_path=cfg_file)

    assert np.isclose(result["temperature"], 1.35)
    assert result["fitted"] is True
    assert result["confidence"] < 0.75
    assert np.isclose(np.sum(result["calibrated_probabilities"]), 1.0, atol=1e-5)


def test_calibration_numpy_input():
    """Supports 1D numpy array inputs."""
    raw_probs = np.array([0.05, 0.15, 0.60, 0.15, 0.05], dtype=np.float32)
    result = apply_calibration(raw_probs, temperature=1.2)

    assert isinstance(result["calibrated_probabilities"], list)
    assert isinstance(result["confidence"], float)
    assert len(result["calibrated_probabilities"]) == 5
    assert result["confidence"] < 0.60


def test_calibration_invalid_temperature():
    """Temperature <= 0 must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        apply_calibration([0.2, 0.8], temperature=0.0)

    with pytest.raises(ValueError, match="strictly positive"):
        apply_calibration([0.2, 0.8], temperature=-1.5)


def test_calibration_invalid_probabilities():
    """Empty or negative probabilities must raise ValueError."""
    with pytest.raises(ValueError):
        apply_calibration([])

    with pytest.raises(ValueError, match="non-negative"):
        apply_calibration([-0.1, 1.1], temperature=1.0)


def test_calibration_config_file_integrity():
    """
    Verify configs/calibration.json exists, is valid JSON, and is internally honest:
    - unfitted (fitted=False) must mean temperature=1.0 exactly (no-op, nothing invented).
    - fitted (fitted=True) must be traceable to a real fit: a positive temperature and a
      recorded dataset/method (never an invented value — see training/train_grading.py's
      fit_temperature(), which is the only place that may legitimately set fitted=True).
    Does not hardcode which state the repo is in — a from-scratch clone before any
    training run is unfitted; a repo with a trained grading model is fitted.
    """
    config_path = Path("configs/calibration.json")
    assert config_path.is_file(), "configs/calibration.json must exist"

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    assert "temperature" in cfg
    assert "fitted" in cfg
    assert isinstance(cfg["fitted"], bool)

    if cfg["fitted"] is False:
        assert cfg["temperature"] == 1.0, "An unfitted config must be the exact no-op default (T=1.0)."
    else:
        assert cfg["temperature"] > 0, "A fitted temperature must be a positive, real fitted value."
        assert cfg.get("method") == "temperature_scaling"
        assert cfg.get("dataset"), "A fitted config must record which split it was fitted on."
